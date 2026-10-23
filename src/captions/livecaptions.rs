use std::os::windows::process::CommandExt;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use std::sync::Arc;
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use windows::core::{w, BOOL};
use windows::Win32::Foundation::{HWND, LPARAM};
use windows::Win32::System::Com::{
    CoCreateInstance, CoInitializeEx, CLSCTX_ALL, COINIT_APARTMENTTHREADED,
};
use windows::Win32::UI::Accessibility::{
    CUIAutomation, IUIAutomation, IUIAutomationElement, IUIAutomationInvokePattern,
    TreeScope_Descendants, UIA_InvokePatternId,
};
use windows::Win32::Foundation::RECT;
use windows::Win32::UI::WindowsAndMessaging::{
    EnumWindows, FindWindowW, GetSystemMetrics, GetWindowLongPtrW, GetWindowRect, GetWindowThreadProcessId,
    IsWindow, SetWindowLongPtrW, SetWindowPos, ShowWindow, GWL_EXSTYLE, HWND_BOTTOM, SM_CXSCREEN,
    SM_CYSCREEN, SW_MINIMIZE, SW_RESTORE, SWP_NOACTIVATE, SWP_NOSIZE, SWP_NOZORDER, WS_EX_LAYERED,
    WS_EX_TOOLWINDOW,
};

use super::{looks_final, CaptionEvent, CaptionProvider, Capability, CapState, Emit};

const TEXT_ID: &str = "CaptionsTextBlock";
const LC_UI_KEY: &str = r"HKCU\SOFTWARE\Microsoft\LiveCaptions\UI";
const BUILD_KEY: &str = r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentBuild";
const CREATE_NO_WINDOW: u32 = 0x08000000;
const TICK: Duration = Duration::from_millis(120);
const LAUNCH_TIMEOUT: Duration = Duration::from_secs(12);
const READY_TIMEOUT: Duration = Duration::from_secs(30);

#[link(name = "winmm")]
extern "system" {
    fn timeBeginPeriod(u_period: u32) -> u32;
    fn timeEndPeriod(u_period: u32) -> u32;
}

#[link(name = "user32")]
extern "system" {
    fn SetLayeredWindowAttributes(
        hwnd: *mut core::ffi::c_void,
        cr_key: u32,
        b_alpha: u8,
        dw_flags: u32,
    ) -> i32;
}

const LWA_ALPHA: u32 = 0x00000002;

// Make the window compose fully transparent. Unlike DWMWA_CLOAK (which this
// process is not allowed to set — DWM answers E_ACCESSDENIED for another
// app's window), WS_EX_LAYERED + LWA_ALPHA is a plain user32 attribute that
// cross-process callers may set, and Live Captions never clears it: once
// applied, every later reposition of the window paints nothing, so there is
// no timing race left to lose. The window itself stays created, shown and
// rendering — no hide/minimize, so the warmup-stall hazard is untouched.
fn make_transparent(hwnd: HWND) {
    unsafe {
        let ex = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
        if ex & (WS_EX_LAYERED.0 as isize) == 0 {
            let _ = SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED.0 as isize);
        }
        SetLayeredWindowAttributes(hwnd.0, 0, 0, LWA_ALPHA);
    }
}

// Live Captions ignores WM_CLOSE (it minimizes to the tray instead), so the
// instance we spawned has to be terminated by PID or it outlives the player.
//
// The pid lives per generation (one Arc per start()) so a zombie poll thread
// from a previous session can only ever kill its own LC — never the freshly
// spawned one. No /IM fallback: pid 0 means "nothing to kill here" and is a
// silent no-op.
fn terminate_pid(pid: &Arc<AtomicU32>) {
    let p = pid.swap(0, Ordering::SeqCst);
    if p == 0 {
        return;
    }
    crate::lc_dbg(&format!("taskkill start pid={p}"));
    let ok = std::process::Command::new("taskkill")
        .args(["/PID", &p.to_string()])
        .arg("/F")
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false);
    crate::lc_dbg(&format!("taskkill done pid={p} ok={ok}"));
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

fn run_ps(cmd: &str) -> String {
    std::process::Command::new("powershell")
        .args(["-NoProfile", "-Command", cmd])
        .creation_flags(CREATE_NO_WINDOW)
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .output()
        .map(|o| String::from_utf8_lossy(&o.stdout).into_owned())
        .unwrap_or_default()
}

/// Installed speech models, read from the per-user speech appx packages
/// (e.g. `MicrosoftWindows.Speech.en-IN.1`). No elevation needed.
pub fn speech_models_installed() -> Vec<String> {
    let out = run_ps(
        "(Get-AppxPackage -Name 'MicrosoftWindows.Speech.*' | ForEach-Object Name) -join \"`n\"",
    );
    let mut tags: Vec<String> = out
        .lines()
        .filter_map(|l| {
            let rest = l.trim().strip_prefix("MicrosoftWindows.Speech.")?;
            let tag = rest.split('.').next()?;
            if tag.contains('-') {
                Some(tag.to_string())
            } else {
                None
            }
        })
        .collect();
    tags.sort();
    tags.dedup();
    tags
}

/// Runs install/remove of a speech model through an elevated PowerShell
/// (UAC consent on first use). The script resolves the matching Windows
/// capability by language tag at run time, so it never hardcodes capability
/// names — and it only ever touches `*Speech*` capabilities, never Basic
/// (system language) features. The UI polls `speech_models_installed()`
/// until the package state changes.
pub fn start_speech_op(op: &str, lang: &str) -> std::io::Result<()> {
    let tag: String = lang
        .chars()
        .filter(|c| c.is_ascii_alphanumeric() || *c == '-')
        .take(16)
        .collect();
    let op = if op == "delete" { "delete" } else { "install" };
    let script = format!(
        r#"$ErrorActionPreference='SilentlyContinue'
$tag='{tag}'
$op='{op}'
$log="$env:TEMP\pvp_speech_op.log"
$caps=@(Get-WindowsCapability -Online | Where-Object {{ $_.Name -like '*Speech*' -and $_.Name -like ("*"+$tag+"*") }})
if($op -eq 'install'){{
  $todo=@($caps | Where-Object {{ $_.State -ne 'Installed' }})
  if($caps.Count -eq 0){{ 'nocaps' | Set-Content $log }} elseif($todo.Count -gt 0){{
    foreach($c in $todo){{ Add-WindowsCapability -Online -Name $c.Name | Out-Null }}
    'ok' | Set-Content $log
  }} else {{ 'ok' | Set-Content $log }}
}} else {{
  foreach($c in ($caps | Where-Object {{ $_.State -eq 'Installed' }})){{ Remove-WindowsCapability -Online -Name $c.Name | Out-Null }}
  Get-AppxPackage -AllUsers -Name ("MicrosoftWindows.Speech."+$tag+"*") | ForEach-Object {{ Remove-AppxPackage -Package $_.PackageFullName -AllUsers }}
  'ok' | Set-Content $log
}}
"#,
        tag = tag,
        op = op
    );
    let path = std::env::temp_dir().join("pvp_speech_op.ps1");
    std::fs::write(&path, script)?;
    std::process::Command::new("powershell")
        .args([
            "-NoProfile",
            "-Command",
            &format!(
                "Start-Process -FilePath powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','{}'",
                path.display()
            ),
        ])
        .creation_flags(CREATE_NO_WINDOW)
        .spawn()?;
    Ok(())
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
    pid: Arc<AtomicU32>,
}

impl LiveCaptionsProvider {
    pub fn new(emit: Emit) -> Self {
        Self {
            emit,
            running: Arc::new(AtomicBool::new(false)),
            stop: Arc::new(AtomicBool::new(false)),
            joined: None,
            launched: Arc::new(AtomicBool::new(false)),
            pid: Arc::new(AtomicU32::new(0)),
        }
    }

    fn wind_down(&mut self) {
        // Signal THIS generation's poll thread. start() installs a fresh Arc,
        // so a thread that was stuck in a UIA call can never resume into the
        // next session.
        self.stop.store(true, Ordering::SeqCst);
        terminate_pid(&self.pid);
        self.launched.store(false, Ordering::SeqCst);
        // Detach instead of joining: the poll loop may be blocked inside a UIA
        // call, and joining here would freeze the UI thread (close / quit /
        // toggle would hang). The thread exits on its own once the call returns;
        // LC is already terminated above so no cleanup is lost.
        self.joined = None;
        self.running.store(false, Ordering::SeqCst);
    }

    /// The player is closing. Two distinct outcomes:
    /// - Live Captions is still on → hand it back to Windows: stop reading,
    ///   restore the window to its normal on-screen state and leave the
    ///   process running, so the Quick Settings toggle stays usable for any
    ///   other app.
    /// - Live Captions was already turned off from the player → make sure the
    ///   process is gone; the user restarts it from Quick Settings.
    pub fn exit_handoff(&mut self) {
        if self.running.load(Ordering::SeqCst) {
            crate::lc_dbg("exit handoff: LC still on; restoring window, leaving process alive");
            self.stop.store(true, Ordering::SeqCst);
            // Zero the pid first: nothing on any path may terminate LC now.
            self.pid.swap(0, Ordering::SeqCst);
            // Detached window (not spawned-and-killed): the poll thread's end
            // block restores it; flag it before the thread can observe stop.
            self.launched.store(false, Ordering::SeqCst);
            // Give the poll thread a moment to exit its loop. Its end block
            // restores the window, which also guarantees the LAST operation
            // on the window is a restore — a straggler repark could otherwise
            // re-park it after our restore.
            if let Some(h) = self.joined.take() {
                let deadline = Instant::now() + Duration::from_millis(1200);
                while !h.is_finished() && Instant::now() < deadline {
                    std::thread::sleep(Duration::from_millis(20));
                }
            }
            restore_lc_window(); // idempotent belt-and-braces
            self.running.store(false, Ordering::SeqCst);
        } else {
            crate::lc_dbg("exit handoff: LC off; ensuring terminated");
            self.wind_down();
            kill_lc_by_name();
        }
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
        self.stop = Arc::new(AtomicBool::new(false));
        self.launched = Arc::new(AtomicBool::new(false));
        self.pid = Arc::new(AtomicU32::new(0));
        self.running.store(true, Ordering::SeqCst);
        let emit = self.emit.clone();
        let stop = self.stop.clone();
        let running = self.running.clone();
        let launched = self.launched.clone();
        let pid = self.pid.clone();
        match std::thread::Builder::new()
            .name("lc-captions".into())
            .spawn(move || poll_loop(emit, stop, running, launched, pid))
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
        // Turning captions OFF from the player means off everywhere: kill
        // whatever instance is captioning (ours, or one the user opened) so
        // the Quick Settings toggle lands on "off" and the user can start
        // Live Captions fresh from there.
        kill_lc_by_name();
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

// Hide from the taskbar immediately; actually minimizing is deferred until the
// caption UI has had a chance to render its first frame — minimizing too early
// can freeze Live Captions' startup and leave it stuck on the warmup screen.
//
// The window is also made transparent and parked far off-screen the moment it
// is found: Live Captions otherwise flashes in its spawn position (and again
// when it re-docks itself) until the deferred minimize fires, and a parked
// window can never float over other applications either. All of it is
// attribute/position-only (no hide/activate), so it does not risk the warmup
// stall.
fn mark_toolwindow(hwnd: HWND) {
    unsafe {
        let ex = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
        let _ = SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex | WS_EX_TOOLWINDOW.0 as isize);
    }
    make_transparent(hwnd);
    park_offscreen(hwnd);
}

// Original position of the parked window, so a window we did NOT spawn (the
// user opened Live Captions themselves) can be put back where it was when the
// player exits.
static PARKED_POS: std::sync::Mutex<Option<(i32, i32)>> = std::sync::Mutex::new(None);

fn park_offscreen(hwnd: HWND) {
    unsafe {
        let mut rc = RECT::default();
        let got = GetWindowRect(hwnd, &mut rc);
        // Only remember a real-looking main window (Live Captions also owns
        // hidden 1x1 helper windows that must never become the restore
        // target).
        if got.is_ok()
            && rc.left > -10000
            && (rc.right - rc.left) >= 100
            && (rc.bottom - rc.top) >= 20
        {
            if let Ok(mut g) = PARKED_POS.lock() {
                if g.is_none() {
                    *g = Some((rc.left, rc.top));
                }
            }
        }
        let _ = SetWindowPos(
            hwnd,
            Some(HWND_BOTTOM),
            -32000,
            -32000,
            0,
            0,
            SWP_NOSIZE | SWP_NOACTIVATE,
        );
    }
}

// Live Captions re-docks its bar to the bottom of the screen by itself after
// the initial park, so the position is re-asserted on every poll tick — the
// window can then never be seen (this is the stray box in the corner).
fn repark_if_visible(hwnd: HWND) {
    unsafe {
        let mut rc = RECT::default();
        if GetWindowRect(hwnd, &mut rc).is_ok() && rc.left > -10000 {
            let _ = SetWindowPos(
                hwnd,
                Some(HWND_BOTTOM),
                -32000,
                -32000,
                0,
                0,
                SWP_NOSIZE | SWP_NOACTIVATE,
            );
        }
    }
}

// The 120ms poll tick cannot keep up with Live Captions' own repositioning:
// the spawn flash and the later self re-dock each stayed on screen for
// 100-200ms (1-2 tick cycles) — the "subtitle splash" seen on enable. The
// watchdog closes this from two sides: it (re)applies the transparent
// layered attribute the moment any window of the spawned pid exists — before
// Live Captions ever shows it, so nothing it draws is ever composited — and
// re-parks the position every 4ms for tidiness (a re-dock that still slips
// between ticks now paints nothing, so timing no longer matters). Only runs
// for a window we spawned (pid gate); a foreign instance the user opened
// keeps the original restore semantics.
struct ParkGuard {
    go: Arc<AtomicBool>,
    handle: Option<JoinHandle<()>>,
}

impl Drop for ParkGuard {
    fn drop(&mut self) {
        self.go.store(false, Ordering::SeqCst);
        if let Some(h) = self.handle.take() {
            let _ = h.join();
        }
    }
}

// All top-level windows of the spawned Live Captions process. FindWindow
// only ever returns the first class match, and Live Captions creates several
// windows during startup — every one of them must get the treatment, or an
// un-attended secondary window is exactly what flashed in the spawn corner.
fn pid_windows(pid: u32) -> Vec<HWND> {
    let mut out: Vec<HWND> = Vec::new();
    extern "system" fn cb(h: HWND, lparam: LPARAM) -> BOOL {
        unsafe {
            let list = &mut *(lparam.0 as *mut Vec<HWND>);
            list.push(h);
        }
        BOOL::from(true)
    }
    unsafe {
        let _ = EnumWindows(Some(cb), LPARAM(&mut out as *mut _ as isize));
    }
    let mut own: Vec<HWND> = Vec::new();
    for h in out {
        let mut wpid = 0u32;
        unsafe {
            GetWindowThreadProcessId(h, Some(&mut wpid as *mut u32));
        }
        if wpid == pid {
            own.push(h);
        }
    }
    own
}

fn spawn_park_thread(pid: Arc<AtomicU32>) -> ParkGuard {
    let go = Arc::new(AtomicBool::new(true));
    let thread_go = go.clone();
    let handle = std::thread::Builder::new()
        .name("lc-park".into())
        .spawn(move || {
            // Sub-millisecond Sleep accuracy; paired on every exit path so the
            // system timer resolution is not left raised after we stop.
            unsafe { timeBeginPeriod(1); }
            while thread_go.load(Ordering::Relaxed) {
                let p = pid.load(Ordering::SeqCst);
                if p != 0 {
                    for h in pid_windows(p) {
                        if h.0.is_null() || !unsafe { IsWindow(Some(h)) }.as_bool() {
                            continue;
                        }
                        unsafe {
                            let ex = GetWindowLongPtrW(h, GWL_EXSTYLE);
                            if ex & (WS_EX_TOOLWINDOW.0 as isize) == 0 {
                                let _ =
                                    SetWindowLongPtrW(h, GWL_EXSTYLE, ex | WS_EX_TOOLWINDOW.0 as isize);
                            }
                        }
                        make_transparent(h);
                        let on_screen = unsafe {
                            let mut rc = RECT::default();
                            GetWindowRect(h, &mut rc).map(|_| rc.left > -10000).unwrap_or(false)
                        };
                        if on_screen {
                            park_offscreen(h);
                        }
                    }
                }
                std::thread::sleep(Duration::from_millis(5));
            }
            unsafe { timeEndPeriod(1); }
        })
        .ok();
    ParkGuard { go, handle }
}

// Put Live Captions back into its normal on-screen state: visible, at its
// own position, without the toolwindow flag. Used when the player exits
// while Live Captions is still on (it keeps running for other apps) and by
// the poll thread when it detaches from a window it did not spawn. Safe to
// call more than once — whoever gets PARKED_POS positions the window, the
// other call is a no-op re-assert of style/show.
fn restore_lc_window() {
    unsafe {
        let Ok(h) = FindWindowW(w!("LiveCaptionsDesktopWindow"), None) else {
            return;
        };
        if h.0.is_null() || !IsWindow(Some(h)).as_bool() {
            return;
        }
        let ex = GetWindowLongPtrW(h, GWL_EXSTYLE);
        let _ = SetWindowLongPtrW(
            h,
            GWL_EXSTYLE,
            ex & !((WS_EX_TOOLWINDOW.0 | WS_EX_LAYERED.0) as isize),
        );
        let _ = ShowWindow(h, SW_RESTORE);
        // Only re-position while the window is still parked off-screen; a
        // second (idempotent) call must never drag a window the user may
        // already have moved.
        let mut rc = RECT::default();
        if GetWindowRect(h, &mut rc).is_ok() && rc.left <= -10000 {
            let saved = PARKED_POS.lock().ok().and_then(|mut g| g.take());
            let (x, y) = match saved {
                Some(p) => p,
                None => {
                    // No remembered spot (defensive): dock bottom-center,
                    // where Live Captions normally sits.
                    let cx = GetSystemMetrics(SM_CXSCREEN);
                    let cy = GetSystemMetrics(SM_CYSCREEN);
                    ((cx - 520).max(0), (cy - 180).max(0))
                }
            };
            let _ = SetWindowPos(h, None, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE);
        }
    }
}

// Terminate Live Captions by name. Only used on terminal paths (the OFF
// button, player exit while captions are already off) — never during a
// language restart, so a freshly spawned instance can never be the victim.
fn kill_lc_by_name() {
    crate::lc_dbg("taskkill /IM LiveCaptions.exe start");
    let ok = std::process::Command::new("taskkill")
        .args(["/IM", "LiveCaptions.exe", "/F"])
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false);
    crate::lc_dbg(&format!("taskkill /IM done ok={ok}"));
}

fn minimize_window(hwnd: HWND) {
    unsafe {
        let _ = ShowWindow(hwnd, SW_MINIMIZE);
    }
}

fn ensure_window(
    emit: &Emit,
    stop: &Arc<AtomicBool>,
    launched: &Arc<AtomicBool>,
    pid: &Arc<AtomicU32>,
) -> Option<HWND> {
    let deadline = Instant::now() + LAUNCH_TIMEOUT;
    let mut spawned = false;
    let mut spawned_at: Option<Instant> = None;
    loop {
        if stop.load(Ordering::SeqCst) {
            return None;
        }
        if let Ok(h) = unsafe { FindWindowW(w!("LiveCaptionsDesktopWindow"), None) } {
            if !h.0.is_null() {
                match spawned_at {
                    Some(t) => {
                        crate::lc_dbg(&format!("LC window found {:?} after spawn", t.elapsed()))
                    }
                    None => crate::lc_dbg("LC window found"),
                }
                // Adopted an already-running window (leftover from a previous
                // run, or one the user opened): arm the park watchdog for it
                // too. Without the stored pid the watchdog gate stays 0 and
                // Live Captions re-asserts its own opaque alpha and re-docks
                // unopposed — the brief adopt flash on re-enable.
                let mut wpid = 0u32;
                unsafe { GetWindowThreadProcessId(h, Some(&mut wpid as *mut u32)); }
                if wpid != 0 {
                    pid.store(wpid, Ordering::SeqCst);
                }
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
                    spawned_at = Some(Instant::now());
                    // pid first: anyone seeing launched=true is guaranteed a
                    // valid pid to clean up.
                    pid.store(child.id(), Ordering::SeqCst);
                    launched.store(true, Ordering::SeqCst);
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
        // 1ms after the spawn: the window can be created hidden and shown by
        // LC itself at any moment — poll tight enough that mark_toolwindow
        // (cloak+park) lands within roughly one refresh interval of creation.
        std::thread::sleep(if spawned {
            Duration::from_millis(1)
        } else {
            Duration::from_millis(150)
        });
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

fn poll_loop(
    emit: Emit,
    stop: Arc<AtomicBool>,
    running: Arc<AtomicBool>,
    launched: Arc<AtomicBool>,
    pid: Arc<AtomicU32>,
) {
    crate::lc_dbg("poll thread start");
    // Cloak/park watchdog for this generation; dropped on every exit path and
    // explicitly before any window restore, so it can never re-hide a window
    // we are handing back to Windows.
    let park = spawn_park_thread(pid.clone());
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
    let mut hwnd = match ensure_window(&emit, &stop, &launched, &pid) {
        Some(h) => h,
        None => {
            terminate_pid(&pid);
            if !stop.load(Ordering::SeqCst) {
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
        terminate_pid(&pid);
        running.store(false, Ordering::SeqCst);
        return;
    }
    mark_toolwindow(hwnd);

    let mut cached: Option<IUIAutomationElement> = None;
    let mut last = String::new();
    let mut ready = false;
    let mut ready_warned = false;
    let mut last_continue: Option<Instant> = None;
    let mut downloading = false;
    let mut warmup = false;
    let mut warmup_since: Option<Instant> = None;
    let mut minimized = false;
    let mut restarted = 0u8;
    let mut started = Instant::now();

    loop {
        if stop.load(Ordering::SeqCst) {
            break;
        }

        if !unsafe { IsWindow(Some(hwnd)) }.as_bool() {
            cached = None;
            match ensure_window(&emit, &stop, &launched, &pid) {
                Some(h) => {
                    hwnd = h;
                    mark_toolwindow(hwnd);
                    minimized = false;
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
        if !stop.load(Ordering::SeqCst) {
            repark_if_visible(hwnd);
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
                            warmup_since = Some(Instant::now());
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
                if !t.trim().is_empty() {
                    let is_final = looks_final(&t);
                    (emit)(CaptionEvent::Update {
                        text: t.clone(),
                        is_final,
                    });
                    last = t;
                }
                // Empty text (silent gap): keep the last caption on screen —
                // subtitles only disappear when the user turns them off.
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

        // One-shot recovery: if the warmup screen hangs (observed after some
        // force-kills / early-minimize races), restart Live Captions once.
        if !ready
            && !downloading
            && warmup
            && restarted == 0
            && launched.load(Ordering::SeqCst)
            && warmup_since
                .map(|t| t.elapsed() >= Duration::from_secs(90))
                .unwrap_or(false)
        {
            restarted = 1;
            crate::lc_dbg("warmup stalled; restarting Live Captions once");
            (emit)(CaptionEvent::State(
                CapState::Setup,
                "Restarting Live Captions…".to_string(),
            ));
            terminate_pid(&pid);
            cached = None;
            warmup = false;
            warmup_since = None;
            downloading = false;
            last_continue = None;
            ready_warned = false;
            minimized = false;
            started = Instant::now();
            if stop.load(Ordering::SeqCst) {
                break;
            }
            continue;
        }

        // Keep the window visible just long enough to render its first frame;
        // minimize it once captions are ready (or after a grace period).
        if !minimized
            && (ready
                || warmup_since
                    .map(|t| t.elapsed() >= Duration::from_secs(20))
                    .unwrap_or(false)
                || started.elapsed() >= Duration::from_secs(30))
        {
            minimize_window(hwnd);
            minimized = true;
        }

        std::thread::sleep(TICK);
    }

    drop(park); // watchdog must stop before any restore/handoff
    if !launched.load(Ordering::SeqCst) {
        restore_lc_window();
    }
    terminate_pid(&pid);
    running.store(false, Ordering::SeqCst);
}
