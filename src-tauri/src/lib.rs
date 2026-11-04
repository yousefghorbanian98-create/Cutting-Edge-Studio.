//! Tauri shell for Cutting Edge v2.
//!
//! The shell only starts the local Python sidecar, waits for its health probe and
//! then reveals the window. It never opens a network connection of its own
//! (OFFLINE POLICY, LOCK-05).

use std::time::Duration;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

/// Loopback port of the FastAPI sidecar (must match `app.config.Settings.port`).
const BACKEND_PORT: u16 = 8756;

/// How long the splash stays up while the sidecar boots.
const HEALTH_TIMEOUT: Duration = Duration::from_secs(60);

#[derive(Debug, thiserror::Error)]
enum ShellError {
    #[error("failed to spawn backend sidecar: {0}")]
    Spawn(String),
}

/// Spawn `backend/cutting-edge-backend.exe` as a Tauri sidecar.
fn spawn_backend(app: &tauri::AppHandle) -> Result<CommandChild, ShellError> {
    let command = app
        .shell()
        .sidecar("cutting-edge-backend")
        .map_err(|error| ShellError::Spawn(error.to_string()))?;

    let (mut _events, child) = command
        .args(["--port", &BACKEND_PORT.to_string(), "--host", "127.0.0.1"])
        .spawn()
        .map_err(|error| ShellError::Spawn(error.to_string()))?;

    Ok(child)
}

/// Block until the sidecar answers on loopback, or give up after `HEALTH_TIMEOUT`.
async fn wait_until_ready() -> bool {
    let url = format!("http://127.0.0.1:{BACKEND_PORT}/api/v1/health");
    let deadline = tokio::time::Instant::now() + HEALTH_TIMEOUT;
    while tokio::time::Instant::now() < deadline {
        if let Ok(response) = reqwest::get(&url).await {
            if response.status().is_success() {
                return true;
            }
        }
        tokio::time::sleep(Duration::from_millis(500)).await;
    }
    false
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let handle = app.handle().clone();
            match spawn_backend(&handle) {
                Ok(child) => {
                    app.manage(child);
                }
                Err(error) => {
                    // Surfaced to the UI through the health badge; never swallowed.
                    eprintln!("{error}");
                }
            }
            tauri::async_runtime::spawn(async move {
                if !wait_until_ready().await {
                    eprintln!("backend sidecar did not report healthy in time");
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Cutting Edge v2 shell");

    app.run(|_handle, event| {
        if let RunEvent::ExitRequested { .. } = event {
            // Sidecar children are killed by the shell plugin on exit.
        }
    });
}
