#![windows_subsystem = "windows"]

use std::env;
use std::fs;
use std::process::Command;

#[link(name = "shell32")]
extern "system" {
    fn IsUserAnAdmin() -> i32;
}

const PLAYER_BYTES: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/target/release/personal-video-player.exe"
));

const EXTS: &[&str] = &[
    "mp4", "m4v", "mkv", "avi", "mov", "wmv", "flv", "webm", "mpeg", "mpg", "3gp", "3g2",
    "ts", "m2ts", "mts", "m2v", "mpe", "vob", "ogv", "ogg", "divx", "xvid", "asf", "wtv",
    "rm", "rmvb", "f4v", "mxf", "tod", "rec",
];

fn is_admin() -> bool {
    unsafe { IsUserAnAdmin() != 0 }
}

fn elevate() -> std::io::Result<()> {
    let exe = env::current_exe()?;
    Command::new("powershell")
        .args([
            "-NoProfile",
            "-Command",
            &format!("Start-Process -FilePath '{}' -Verb RunAs", exe.display()),
        ])
        .spawn()?;
    Ok(())
}

fn install() -> std::io::Result<()> {
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
    #[link(name = "shell32")]
    extern "system" {
        fn SHChangeNotify(wEventId: i32, uFlags: u32, dwItem1: *const std::ffi::c_void, dwItem2: *const std::ffi::c_void);
    }
    unsafe { SHChangeNotify(0x08000000, 0, std::ptr::null(), std::ptr::null()); }

    // Uninstall entry
    let (un, _) = hkcu.create_subkey("Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\PVP")?;
    un.set_value("DisplayName", &"Personal Video Player (PVP)")?;
    un.set_value("DisplayIcon", &exe_str)?;
    un.set_value("Publisher", &"PVP")?;
    un.set_value("UninstallString", &format!("cmd /c del \"{}\"", exe_str))?;

    Ok(())
}

fn main() {
    if let Err(e) = install() {
        // Show error via message box-ish by writing to temp file
        let _ = std::fs::write(
            "C:\\Users\\Public\\pvp_install_error.txt",
            format!("{}", e),
        );
    } else {
        let _ = std::fs::write("C:\\Users\\Public\\pvp_install_ok.txt", "installed");
    }
}
