use std::os::windows::process::CommandExt;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use std::sync::Arc;
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use windows::core::w;
use windows::Win32::Foundation::HWND;
use windows::Win32::System::Com::{
    CoCreateInstance, CoInitializeEx, CLSCTX_ALL, COINIT_APARTMENTTHREADED,
};
use windows::Win32::UI::Accessibility::{
    CUIAutomation, IUIAutomation, IUIAutomationElement, IUIAutomationInvokePattern,
    TreeScope_Descendants, UIA_InvokePatternId,
};
use windows::Win32::UI::WindowsAndMessaging::{
    FindWindowW, GetWindowLongPtrW, IsWindow, SetWindowLongPtrW, ShowWindow, GWL_EXSTYLE,
    SW_MINIMIZE, SW_RESTORE, WS_EX_TOOLWINDOW,
};

use super::{looks_final, CaptionEvent, CaptionProvider, Capability, CapState, Emit};

const TEXT_ID: &str = "CaptionsTextBlock";
const LC_UI_KEY: &str = r"HKCU\SOFTWARE\Microsoft\LiveCaptions\UI";
const BUILD_KEY: &str = r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentBuild";
const CREATE_NO_WINDOW: u32 = 0x08000000;
const TICK: Duration = Duration::from_millis(120);
const LAUNCH_TIMEOUT: Duration = Duration::from_secs(12);
const READY_TIMEOUT: Duration = Duration::from_secs(30);

static LC_PID: AtomicU32 = AtomicU32::new(0);

// Live Captions ignores WM_CLOSE (it minimizes to the tray instead), so the
// instance we spawned has to be terminated by PID or it outlives the player.
fn terminate_launched() {
    let pid = LC_PID.swap(0, Ordering::SeqCst);
    let mut cmd = std::process::Command::new("taskkill");
    if pid != 0 {
        cmd.args(["/PID", &pid.to_string()]);
    } else {
        cmd.args(["/IM", "LiveCaptions.exe"]);
    }
    cmd.arg("/F").creation_flags(CREATE_NO_WINDOW);
    let ok = cmd.output().map(|o| o.status.success()).unwrap_or(false);
    crate::lc_dbg(&format!("terminate LiveCaptions pid={pid} ok={ok}"));
}

fn lc_exe_path() -> PathBuf {
    let windir = std::env::var("WINDIR").unwrap_or_else(|_| "C:\\Windows".to_string());
    PathBuf::from(windir).join("System32").join("LiveCaptions.exe")
}

fn reg_query(key: &str, value: &str) -> Option<String> {
    let out = std::process::Command::new("reg.exe")
        .args(["query", key, "/v", value])
        .creation_flags(CREATE_NO_WINDOW)
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .output()
        .ok()?;
    if !out.status.success() {
        return None;
    }
    let s = String::from_utf8_lossy(&out.stdout);
    let line = s.lines().rev().find(|l| !l.trim().is_empty())?;
    line.split_whitespace().last().map(|t| t.to_string())
}

fn query_build() -> Option<u32> {
    reg_query(BUILD_KEY, "CurrentBuildNumber")?.parse().ok()
}

pub fn current_language() -> String {
    reg_query(LC_UI_KEY, "CaptionLanguage")
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "en-US".to_string())
}

fn write_language(lang: &str) -> bool {
    if lang.is_empty()
        || !lang
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
    {
        return false;
    }
    std::process::Command::new("reg.exe")
        .args(["add", LC_UI_KEY, "/v", "CaptionLanguage", "/t", "REG_SZ", "/d", lang, "/f"])
        .creation_flags(CREATE_NO_WINDOW)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

pub fn probe_capability() -> Capability {
    if !lc_exe_path().exists() {
        return Capability {
            supported: false,
            reason: "Live Captions is not available on this system (Windows 11 22H2 or later required)."
                .to_string(),
        };
    }
    if let Some(build) = query_build() {
        if build < 22621 {
            return Capability {
                supported: false,
                reason: format!(
                    "Live Captions requires Windows 11 22H2 or later — this system is build {build}."
                ),
            };
        }
    }
    Capability {
        supported: true,
        reason: String::new(),
    }
}

pub struct LiveCaptionsProvider {
    emit: Emit,
    running: Arc<AtomicBool>,
    stop: Arc<AtomicBool>,
    joined: Option<JoinHandle<()>>,
    launched: Arc<AtomicBool>,
}

impl LiveCaptionsProvider {
    pub fn new(emit: Emit) -> Self {
        Self {
            emit,
            running: Arc::new(AtomicBool::new(false)),
            stop: Arc::new(AtomicBool::new(false)),
            joined: None,
            launched: Arc::new(AtomicBool::new(false)),
        }
    }

    fn wind_down(&mut self) {
        self.stop.store(true, Ordering::SeqCst);
        if let Some(j) = self.joined.take() {
            let _ = j.join();
        }
        self.running.store(false, Ordering::SeqCst);
    }
}

impl CaptionProvider for LiveCaptionsProvider {
    fn start(&mut self) {
        crate::lc_dbg("provider start");
        let cap = super::probe().clone();
        if !cap.supported {
            (self.emit)(CaptionEvent::State(CapState::Unsupported, cap.reason));
            return;
        }
        if self.running.load(Ordering::SeqCst) {
            return;
        }
        self.wind_down();
        self.stop.store(false, Ordering::SeqCst);
        self.launched.store(false, Ordering::SeqCst);
        self.running.store(true, Ordering::SeqCst);
        let emit = self.emit.clone();
        let stop = self.stop.clone();
        let running = self.running.clone();
        let launched = self.launched.clone();
        match std::thread::Builder::new()
            .name("lc-captions".into())
            .spawn(move || poll_loop(emit, stop, running, launched))
        {
            Ok(h) => self.joined = Some(h),
            Err(e) => {
                self.running.store(false, Ordering::SeqCst);
                (self.emit)(CaptionEvent::State(
                    CapState::Error,
                    format!("Failed to start caption reader: {e}"),
                ));
            }
        }
    }

    fn stop(&mut self) {
        self.wind_down();
    }

    fn set_language(&mut self, lang: &str) {
        if !write_language(lang) {
            (self.emit)(CaptionEvent::State(
                CapState::Error,
                "Could not change the Live Captions language.".to_string(),
            ));
            return;
        }
        if self.is_running() {
            self.wind_down();
            self.start();
        }
    }

    fn is_running(&self) -> bool {
        self.running.load(Ordering::SeqCst)
    }
}

impl Drop for LiveCaptionsProvider {
    fn drop(&mut self) {
        self.wind_down();
    }
}

fn hide_window(hwnd: HWND) {
    unsafe {
        let ex = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
        let _ = SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex | WS_EX_TOOLWINDOW.0 as isize);
        let _ = ShowWindow(hwnd, SW_MINIMIZE);
    }
}

fn ensure_window(emit: &Emit, stop: &Arc<AtomicBool>, launched: &Arc<AtomicBool>) -> Option<HWND> {
    let deadline = Instant::now() + LAUNCH_TIMEOUT;
    let mut spawned = false;
    loop {
        if stop.load(Ordering::SeqCst) {
            return None;
        }
        if let Ok(h) = unsafe { FindWindowW(w!("LiveCaptionsDesktopWindow"), None) } {
            if !h.0.is_null() {
                crate::lc_dbg("LC window found");
                return Some(h);
            }
        }
        if !spawned {
            match std::process::Command::new(lc_exe_path())
                .creation_flags(CREATE_NO_WINDOW)
                .spawn()
            {
                Ok(child) => {
                    spawned = true;
                    launched.store(true, Ordering::SeqCst);
                    LC_PID.store(child.id(), Ordering::SeqCst);
                    crate::lc_dbg(&format!("spawned LiveCaptions pid={}", child.id()));
                }
                Err(e) => {
                    crate::lc_dbg(&format!("spawn LiveCaptions failed: {e}"));
                    (emit)(CaptionEvent::State(
                        CapState::Error,
                        format!("Could not launch Live Captions: {e}"),
                    ));
                    return None;
                }
            }
        }
        if Instant::now() >= deadline {
            return None;
        }
        std::thread::sleep(Duration::from_millis(150));
    }
}

fn find_element_by_id(
    a: &IUIAutomation,
    hwnd: HWND,
    id: &str,
) -> Option<IUIAutomationElement> {
    unsafe {
        let root = a.ElementFromHandle(hwnd).ok()?;
        let cond = a.CreateTrueCondition().ok()?;
        let arr = root.FindAll(TreeScope_Descendants, &cond).ok()?;
        let n = arr.Length().ok()?;
        for i in 0..n {
            let el = arr.GetElement(i).ok()?;
            if el.CurrentAutomationId().map(|v| v == id).unwrap_or(false) {
                return Some(el);
            }
        }
        None
    }
}

fn find_text_element(a: &IUIAutomation, hwnd: HWND) -> Option<IUIAutomationElement> {
    find_element_by_id(a, hwnd, TEXT_ID)
}

// After a language change (or on first run with a new language) Live Captions
// shows a "Getting ready to show live captions in: …" screen with a Continue
// button; click it automatically so captioning starts without user action.
fn click_button(a: &IUIAutomation, hwnd: HWND, id: &str) -> bool {
    let Some(btn) = find_element_by_id(a, hwnd, id) else {
        return false;
    };
    let ok = unsafe {
        btn.GetCurrentPatternAs::<IUIAutomationInvokePattern>(UIA_InvokePatternId)
            .and_then(|p| p.Invoke())
            .is_ok()
    };
    if ok {
        crate::lc_dbg(&format!("auto-clicked LC button {id}"));
    }
    ok
}

fn poll_loop(emit: Emit, stop: Arc<AtomicBool>, running: Arc<AtomicBool>, launched: Arc<AtomicBool>) {
    crate::lc_dbg("poll thread start");
    let _ = unsafe { CoInitializeEx(None, COINIT_APARTMENTTHREADED) };
    let automation: IUIAutomation = match unsafe { CoCreateInstance(&CUIAutomation, None, CLSCTX_ALL) }
    {
        Ok(a) => a,
        Err(e) => {
            (emit)(CaptionEvent::State(
                CapState::Error,
                format!("Accessibility service unavailable: {e}"),
            ));
            running.store(false, Ordering::SeqCst);
            return;
        }
    };

    (emit)(CaptionEvent::State(
        CapState::Setup,
        "Starting Live Captions…".to_string(),
    ));
    let mut hwnd = match ensure_window(&emit, &stop, &launched) {
        Some(h) => h,
        None => {
            if launched.load(Ordering::SeqCst) {
                terminate_launched();
            }
            if stop.load(Ordering::SeqCst) {
                (emit)(CaptionEvent::Clear);
                (emit)(CaptionEvent::State(CapState::Closed, String::new()));
            } else {
                (emit)(CaptionEvent::State(
                    CapState::Error,
                    "Could not open the Live Captions window. Open Live Captions manually once and try again."
                        .to_string(),
                ));
            }
            running.store(false, Ordering::SeqCst);
            return;
        }
    };
    if stop.load(Ordering::SeqCst) {
        if launched.load(Ordering::SeqCst) {
            terminate_launched();
        }
        (emit)(CaptionEvent::Clear);
        (emit)(CaptionEvent::State(CapState::Closed, String::new()));
        running.store(false, Ordering::SeqCst);
        return;
    }
    hide_window(hwnd);

    let mut cached: Option<IUIAutomationElement> = None;
    let mut last = String::new();
    let mut ready = false;
    let mut ready_warned = false;
    let mut last_continue: Option<Instant> = None;
    let mut downloading = false;
    let mut warmup = false;
    let started = Instant::now();

    loop {
        if stop.load(Ordering::SeqCst) {
            break;
        }

        if !unsafe { IsWindow(Some(hwnd)) }.as_bool() {
            cached = None;
            match ensure_window(&emit, &stop, &launched) {
                Some(h) => {
                    hwnd = h;
                    hide_window(hwnd);
                }
                None => {
                    if stop.load(Ordering::SeqCst) {
                        break;
                    }
                    (emit)(CaptionEvent::State(
                        CapState::Setup,
                        "Waiting for the Live Captions window…".to_string(),
                    ));
                    std::thread::sleep(TICK);
                    continue;
                }
            }
        }

        let mut text: Option<String> = None;
        if let Some(el) = &cached {
            if let Ok(name) = unsafe { el.CurrentName() } {
                text = Some(name.to_string());
            }
        }
        if text.is_none() {
            cached = find_text_element(&automation, hwnd);
            if let Some(el) = &cached {
                if let Ok(name) = unsafe { el.CurrentName() } {
                    text = Some(name.to_string());
                }
            }
        }
        if !ready && text.is_none() {
            let due = last_continue
                .map(|t| t.elapsed() >= Duration::from_secs(1))
                .unwrap_or(true);
            if due {
                last_continue = Some(Instant::now());
                if !click_button(&automation, hwnd, "ContinueButton") {
                    if !downloading && click_button(&automation, hwnd, "DownloadButton") {
                        downloading = true;
                        crate::lc_dbg("language pack download started");
                        (emit)(CaptionEvent::State(
                            CapState::Setup,
                            "Downloading the Live Captions language file… this can take a few minutes."
                                .to_string(),
                        ));
                    }
                    if !downloading
                        && find_element_by_id(&automation, hwnd, "ReadyToCaptionTextBlock").is_some()
                    {
                        if !warmup {
                            warmup = true;
                            crate::lc_dbg("LC warmup screen (ReadyToCaption)");
                            (emit)(CaptionEvent::State(
                                CapState::Setup,
                                "Getting Live Captions ready…".to_string(),
                            ));
                        }
                    }
                }
            }
        }

        if let Some(t) = text {
            if !ready {
                ready = true;
                crate::lc_dbg("ready (text element found)");
                (emit)(CaptionEvent::State(CapState::Ready, String::new()));
            }
            if t != last {
                if t.trim().is_empty() {
                    if !last.trim().is_empty() {
                        (emit)(CaptionEvent::Clear);
                    }
                } else {
                    let is_final = looks_final(&t);
                    (emit)(CaptionEvent::Update {
                        text: t.clone(),
                        is_final,
                    });
                }
                last = t;
            }
        } else if !ready
            && !ready_warned
            && started.elapsed()
                > if downloading {
                    Duration::from_secs(480)
                } else if warmup {
                    Duration::from_secs(180)
                } else {
                    READY_TIMEOUT
                }
        {
            ready_warned = true;
            (emit)(CaptionEvent::State(
                CapState::Error,
                "Live Captions is open but not producing caption text yet. Speak or play audio to test it."
                    .to_string(),
            ));
        }

        std::thread::sleep(TICK);
    }

    unsafe {
        if IsWindow(Some(hwnd)).as_bool() && !launched.load(Ordering::SeqCst) {
            let ex = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
            let _ = SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex & !(WS_EX_TOOLWINDOW.0 as isize));
            let _ = ShowWindow(hwnd, SW_RESTORE);
        }
    }
    if launched.load(Ordering::SeqCst) {
        terminate_launched();
    }
    (emit)(CaptionEvent::Clear);
    (emit)(CaptionEvent::State(CapState::Closed, String::new()));
    running.store(false, Ordering::SeqCst);
}
