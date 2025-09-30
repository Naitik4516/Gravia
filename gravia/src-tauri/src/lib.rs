#[tauri::command]
fn capture_screenshot_base64(window: tauri::Window) -> Result<String, String> {
    // Hide window to avoid capturing app UI
    if let Err(e) = window.hide() { eprintln!("Failed to hide window before screenshot: {e}"); }
    std::thread::sleep(std::time::Duration::from_millis(150));
    let result = capture_primary_screen_base64();
    if let Err(e) = window.show() { eprintln!("Failed to show window after screenshot: {e}"); }
    if let Err(e) = window.set_focus() { eprintln!("Failed to refocus window: {e}"); }
    result.map_err(|e| e.to_string())
}
// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
mod classifier;

use classifier::{ChatMessage, SessionManager, ClassificationResult};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::sync::{Mutex, Arc};
use tauri::{State, Manager, Listener, Emitter};
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

#[derive(Debug, Clone, Deserialize)]
pub struct FrontendChatMessage {
    pub role: String,
    pub content: String,
    pub timestamp: Option<DateTime<Utc>>, // frontend may omit; we'll fill with now if missing
    pub triggered_screenshot: Option<bool>,
}

#[derive(Debug, Serialize)]
pub struct ClassifyResponse {
    pub classification: ClassificationResult,
    pub screenshot_base64: Option<String>,
}

struct SharedSession(Mutex<SessionManager>);

fn map_frontend_messages(msgs: Vec<FrontendChatMessage>) -> Vec<ChatMessage> {
    msgs.into_iter().map(|m| ChatMessage {
        role: m.role,
        content: m.content,
        timestamp: m.timestamp.unwrap_or_else(Utc::now),
        triggered_screenshot: m.triggered_screenshot,
    }).collect()
}

#[tauri::command]
fn classify_and_maybe_capture(
    state: State<'_, Arc<SharedSession>>,
    window: tauri::Window,
    recent_messages: Vec<FrontendChatMessage>,
    query: String,
) -> Result<ClassifyResponse, String> {
    let mut session = state.0.lock().map_err(|e| e.to_string())?;
    for msg in map_frontend_messages(recent_messages) {
        session.add_message(msg);
    }

    let result = session.process_user_query(&query);

    // If the classifier says we need a screenshot, capture here.
    let mut screenshot_b64: Option<String> = None;
    if result.needs_screenshot {
        match capture_screenshot_base64(window.clone()) {
            Ok(b64) => screenshot_b64 = Some(b64),
            Err(e) => eprintln!("Auto screenshot capture failed: {e}"),
        }
    }

    Ok(ClassifyResponse { classification: result, screenshot_base64: screenshot_b64 })
}

fn capture_primary_screen_base64() -> anyhow::Result<String> {
    use screenshots::Screen;
    use image::{ImageBuffer, Rgba};
    use base64::Engine;

    let screens = Screen::all()?;
    let screen = screens
        .into_iter()
        .next()
        .ok_or_else(|| anyhow::anyhow!("No screen found"))?;
    let shot = screen.capture()?;
    let width = shot.width();
    let height = shot.height();
    let raw = shot.into_raw(); // Raw pixel buffer from crate

    // Platform-specific channel order handling.
    // Windows: buffer is BGRA. Others: already RGBA.
    #[cfg(target_os = "windows")]
    let rgba: Vec<u8> = {
        let mut out = Vec::with_capacity(raw.len());
        for px in raw.chunks_exact(4) {
            // BGRA -> RGBA swap: B=px[0], G=px[1], R=px[2], A=px[3]
            out.push(px[0]); // R (from B)
            out.push(px[1]); // G
            out.push(px[2]); // B (from R)
            out.push(px[3]); // A
        }
        out
    };

    #[cfg(not(target_os = "windows"))]
    let rgba: Vec<u8> = raw;

    let img: ImageBuffer<Rgba<u8>, _> =
        ImageBuffer::from_vec(width, height, rgba)
            .ok_or_else(|| anyhow::anyhow!("Failed to create image buffer"))?;

    let mut png_bytes: Vec<u8> = Vec::new();
    {
        let dynimg = image::DynamicImage::ImageRgba8(img);
        dynimg.write_to(
            &mut std::io::Cursor::new(&mut png_bytes),
            image::ImageFormat::Png,
        )?;
    }

    Ok(base64::engine::general_purpose::STANDARD.encode(png_bytes))
}




#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let session = Arc::new(SharedSession(Mutex::new(SessionManager::new(200))));
    tauri::Builder::default()
    .manage(session)
    .plugin(tauri_plugin_single_instance::init(|_app, _args, _cwd| {}))
    .on_window_event(|window, event| match event {
        tauri::WindowEvent::CloseRequested { api, .. } => {
            window.hide().unwrap();
            api.prevent_close();
        }
        _ => {}
    })
    .plugin(tauri_plugin_process::init())
    .plugin(tauri_plugin_global_shortcut::Builder::new().build())
    .plugin(tauri_plugin_positioner::init())
    .plugin(tauri_plugin_shell::init())
    .plugin(tauri_plugin_fs::init())
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_http::init())
    .plugin(tauri_plugin_websocket::init())
    .plugin(tauri_plugin_autostart::Builder::new().build())
    .plugin(tauri_plugin_opener::init())
    .invoke_handler(tauri::generate_handler![classify_and_maybe_capture, capture_screenshot_base64])
         .setup(|app| {
            let window = app.get_webview_window("main").unwrap();
            let shell = app.shell();

            // Check if server.exe is already running
            #[cfg(target_os = "windows")]
            let already_running = std::process::Command::new("tasklist")
                .args(["/FI", "IMAGENAME eq server.exe"])
                .output()
                .map(|o| String::from_utf8_lossy(&o.stdout).contains("server.exe"))
                .unwrap_or(false);

            if already_running {
                println!("server.exe already running, skipping sidecar startup");
                return Ok(());
            }

            // Spawn sidecar
            let sidecar = shell.sidecar("server").unwrap();
            let (mut rx, child) = sidecar.spawn().expect("Failed to spawn server.exe");
            let child = Arc::new(Mutex::new(Some(child)));

            let window_for_spawn = window.clone();

            tauri::async_runtime::spawn(async move {
                let mut server_started = false;

                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line_bytes) => {
                            let line = String::from_utf8_lossy(&line_bytes);
                            println!("server stdout: {}", line);

                            if line.contains("Server started successfully") && !server_started {
                                server_started = true;
                                window_for_spawn.emit("server-ready", true).ok();
                                println!("Server is ready!");
                            }
                        }
                        CommandEvent::Stderr(err_bytes) => {
                            eprintln!("server stderr: {}", String::from_utf8_lossy(&err_bytes));
                        }
                        CommandEvent::Terminated(code) => {
                            println!("server.exe exited with code {:?}", code);
                        }
                        _ => {}
                    }
                }
            });

            // Kill server.exe on Tauri exit
            let child_clone = Arc::clone(&child);
            app.listen("app-close", move |_event| {
                println!("Killing server.exe...");
                if let Some(c) = child_clone.lock().unwrap().take() {
                    let _ = c.kill();
                }
            });

            Ok(())
        })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
