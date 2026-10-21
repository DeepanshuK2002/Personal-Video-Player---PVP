// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to SpotiHi.", name)
}

#[tauri::command]
fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![greet, get_app_version])
        .setup(|app| {
            let window = app.get_webview_window("main").unwrap();
            window.set_title("SpotiHi").unwrap();
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running SpotiHi desktop application");
}