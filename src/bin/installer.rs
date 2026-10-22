#![windows_subsystem = "windows"]

use std::env;
use std::fs;
use std::process::Command;

#[link(name = "shell32")]
extern "system" {
    fn SHChangeNotify(w_event_id: i32, w_flags: u32, dw_item1: isize, dw_item2: isize);
}

#[link(name = "user32")]
extern "system" {
    fn MessageBoxW(hwnd: isize, text: *const u16, caption: *const u16, utype: u32) -> i32;
}

const MB_OK: u32 = 0x0000_0000;
const MB_YESNO: u32 = 0x0000_0004;
const MB_ICONINFORMATION: u32 = 0x0000_0040;
const MB_ICONERROR: u32 = 0x0000_0010;
const IDYES: i32 = 6;

const PLAYER_BYTES: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/target/release/personal-video-player.exe"
));

const EXTS: &[&str] = &[
    "mp4", "m4v", "mkv", "avi", "mov", "wmv", "flv", "webm", "mpeg", "mpg", "3gp", "3g2",
    "ts", "m2ts", "mts", "m2v", "mpe", "vob", "ogv", "ogg", "divx", "xvid", "asf", "wtv",
    "rm", "rmvb", "f4v", "mxf", "tod", "rec",
];

// A native confirmation dialog so the user knows the install finished.
// Returns true when the user chose "Yes" (launch the player).
fn msgbox(text: &str, caption: &str, utype: u32) -> bool {
    let t: Vec<u16> = text.encode_utf16().chain(std::iter::once(0)).collect();
    let c: Vec<u16> = caption.encode_utf16().chain(std::iter::once(0)).collect();
    let r = unsafe { MessageBoxW(0, t.as_ptr(), c.as_ptr(), utype) };
    r == IDYES
}

// Per-user Start Menu entry so PVP is discoverable after install.
fn add_shortcut(exe: &std::path::Path) {
    let Some(dir) = exe.parent() else { return };
    let prog = env::var("APPDATA")
        .map(std::path::PathBuf::from)
        .ok()
        .map(|p| p.join("Microsoft\\Windows\\Start Menu\\Programs"))
        .filter(|p| p.is_dir());
    let Some(prog) = prog else { return };
    let lnk = prog.join("PVP.lnk");
    let esc = |p: &std::path::Path| p.display().to_string().replace('\'', "''");
    let ps = format!(
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{}');\
         $s.TargetPath='{}';$s.WorkingDirectory='{}';\
         $s.IconLocation='{},0';$s.Description='Personal Video Player';$s.Save()",
        esc(&lnk),
        esc(exe),
        esc(dir),
        esc(exe),
    );
    let _ = Command::new("powershell")
        .args(["-NoProfile", "-WindowStyle", "Hidden", "-Command", &ps])
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status();
}

fn install() -> std::io::Result<std::path::PathBuf> {
    let local = std::env::var("LOCALAPPDATA").unwrap_or_else(|_| ".".to_string());
    let install_dir = std::path::Path::new(&local).join("PVP");
    fs::create_dir_all(&install_dir)?;
    let exe_path = install_dir.join("personal-video-player.exe");
    fs::write(&exe_path, PLAYER_BYTES)?;

    let exe_str = exe_path.to_string_lossy().to_string();

    // Register application (per-user, no UAC required)
    let hkcu = winreg::RegKey::predef(winreg::enums::HKEY_CURRENT_USER);
    let (classes, _) = hkcu.create_subkey("Software\\Classes")?;
    let (app, _) = classes.create_subkey("Applications\\personal-video-player.exe")?;
    app.set_value("FriendlyAppName", &"PVP")?;
    let (icon, _) = app.create_subkey("DefaultIcon")?;
    icon.set_value("", &format!("{},0", exe_str))?;
    let (cmd, _) = app.create_subkey("shell\\open\\command")?;
    cmd.set_value("", &format!("\"{}\" \"%1\"", exe_str))?;
    let (sup, _) = app.create_subkey("SupportedTypes")?;
    for ext in EXTS {
        let _ = sup.set_value(&format!(".{}", ext), &"");
    }

    // ProgID
    let (prog, _) = classes.create_subkey("PVP.Video")?;
    prog.set_value("", &"PVP Video")?;
    let (icon, _) = prog.create_subkey("DefaultIcon")?;
    icon.set_value("", &format!("{},0", exe_str))?;
    let (pcmd, _) = prog.create_subkey("shell\\open\\command")?;
    pcmd.set_value("", &format!("\"{}\" \"%1\"", exe_str))?;

    for ext in EXTS {
        let (extkey, _) = classes.create_subkey(format!(".{}", ext))?;
        let (owp, _) = extkey.create_subkey("OpenWithProgids")?;
        let _ = owp.set_value("PVP.Video", &"");
        let _ = extkey.create_subkey("OpenWithList\\personal-video-player.exe");
    }

    // Refresh icon/association cache.
    unsafe { SHChangeNotify(0x0800_0000, 0, 0, 0) };

    // Uninstall entry (Settings > Apps)
    let (un, _) = hkcu.create_subkey("Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\PVP")?;
    un.set_value("DisplayName", &"Personal Video Player (PVP)")?;
    un.set_value("DisplayIcon", &exe_str)?;
    un.set_value("Publisher", &"PVP")?;
    un.set_value("DisplayVersion", &env!("CARGO_PKG_VERSION"))?;
    un.set_value("EstimatedSize", &((PLAYER_BYTES.len() / 1024) as u32))?;
    un.set_value("NoModify", &1u32)?;
    un.set_value("NoRepair", &1u32)?;
    un.set_value(
        "UninstallString",
        &format!("cmd /c rmdir /s /q \"{}\"", install_dir.display()),
    )?;

    add_shortcut(&exe_path);

    Ok(exe_path)
}

fn main() {
    match install() {
        Ok(exe_path) => {
            let body = format!(
                "PVP {} is installed.\n\n\
                 \u{2022} Open any video \u{2014} it plays in PVP\n\
                 \u{2022} Start Menu \u{2192} PVP\n\
                 \u{2022} Uninstall: Settings \u{2192} Apps\n\n\
                 Installed to:\n{}\n\n\
                 Launch PVP now?",
                env!("CARGO_PKG_VERSION"),
                exe_path.display()
            );
            if msgbox(&body, "PVP Setup", MB_YESNO | MB_ICONINFORMATION) {
                let _ = Command::new(&exe_path).spawn();
            }
        }
        Err(e) => {
            msgbox(
                &format!(
                    "Installation failed.\n\n{e}\n\n\
                     You can still run PVP directly \u{2014} it is portable and needs no install."
                ),
                "PVP Setup",
                MB_OK | MB_ICONERROR,
            );
        }
    }
}
