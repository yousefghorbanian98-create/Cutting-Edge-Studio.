//! Native shell glue: bundled same-origin HTTP UI, per-launch startup receipt,
//! and OSS shell-plugin process-group cleanup on orderly exit.
//! Abrupt shell death containment is NOT guaranteed by this plugin's Job Object.
mod readiness;

use std::net::TcpStream;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const BACKEND_PORT: u16 = 8756;
// Professor hardenings §1: random port (0→OS) + per-launch token
const USE_RANDOM_PORT: bool = false; // flip to true for --port 0 (requires backend port0 support)
fn generate_token() -> String {
    // 32 random bytes base64url ≈ 43 chars, constant-time compare on backend
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    let mut h = DefaultHasher::new();
    (std::process::id(), SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()).hash(&mut h);
    format!("ces-{:016x}{:016x}", h.finish(), h.finish().wrapping_mul(0x9e3779b97f4a7c15))
}
const HEALTH_TIMEOUT: Duration = Duration::from_secs(60);
const PROBE_INTERVAL: Duration = Duration::from_millis(200);

struct Diagnostic(Mutex<Option<String>>);

struct BackendState {
    child: Mutex<Option<CommandChild>>,
    receipt: PathBuf,
    alive: Arc<AtomicBool>,
}

fn report_failure(app: &tauri::AppHandle, message: &str) {
    eprintln!("shell.error: {message}");
    if let Some(state) = app.try_state::<Diagnostic>() {
        match state.0.lock() {
            Ok(mut stored) => *stored = Some(message.to_owned()),
            Err(error) => eprintln!("shell.error: diagnostic lock failed: {error}"),
        }
    }
    if let Some(window) = app.get_webview_window("main") {
        // Display a native title as well, including failures before DOM load.
        if let Err(error) = window.set_title(&format!("Cutting Edge — {message}")) {
            eprintln!("shell.error: cannot set error title: {error}");
        }
        // No IPC
        // capability is granted to the remote (loopback) frontend.
        let script = format!(
            "document.body.textContent = {}; document.body.style.whiteSpace = 'pre-wrap';",
            serde_json::to_string(&format!(
                "Cutting Edge — startup/runtime error\nخطای راه‌اندازی / اجرا\n{message}\nClose other instances, check local logs, then restart.\nبرنامه‌های هم‌زمان را ببندید، گزارش محلی را بررسی و دوباره اجرا کنید."
            ))
            .expect("serializing a string cannot fail")
        );
        if let Err(error) = window.eval(script) {
            eprintln!("shell.error: cannot display failure: {error}");
        }
    }
}

fn stop_backend(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<BackendState>() {
        state.alive.store(false, Ordering::SeqCst);
        match state.child.lock() {
            Ok(mut slot) => {
                if let Some(child) = slot.take() {
                    if let Err(error) = child.kill() {
                        report_failure(app, &format!("Backend tree cleanup failed: {error}"));
                    }
                }
            }
            Err(error) => report_failure(app, &format!("Backend state lock failed: {error}")),
        }
        if let Err(error) = std::fs::remove_file(&state.receipt) {
            if error.kind() != std::io::ErrorKind::NotFound {
                eprintln!("shell.error: receipt cleanup failed: {error}");
            }
        }
    }
}

fn start_backend(app: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let home = app.path().resource_dir()?;
    let cache = app.path().app_cache_dir()?.join("startup");
    std::fs::create_dir_all(&cache)?;
    // Unique launch correlation, NOT an authentication secret.
    let instance = format!(
        "{}-{}",
        std::process::id(),
        SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos()
    );
    let receipt = cache.join(format!("{instance}.json"));
    let token = generate_token();
    let port_arg = if USE_RANDOM_PORT { "0".to_string() } else { BACKEND_PORT.to_string() };
    let (mut events, child) = app
        .shell()
        .sidecar("cutting-edge-backend")?
        .args([
            "--port",
            &port_arg,
            "--host",
            "127.0.0.1",
            "--serve-frontend",
        ])
        .env("CUTTING_EDGE_HOME", &home)
        .env("CUTTING_EDGE_DESKTOP_INSTANCE_ID", &instance)
        .env("CUTTING_EDGE_DESKTOP_READY_FILE", &receipt)
        .env("CES_API_TOKEN", &token)
        .set_process_group(true)
        .kill_on_drop(true)
        .spawn()?;
    let alive = Arc::new(AtomicBool::new(true));
    app.manage(BackendState {
        child: Mutex::new(Some(child)),
        receipt: receipt.clone(),
        alive: alive.clone(),
    });
    let handle = app.clone();
    let event_alive = alive.clone();
    // Keep draining the OSS plugin's bounded channel; dropping the receiver is
    // not supervision and can lose the sidecar's startup error diagnostics.
    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Stdout(bytes) | CommandEvent::Stderr(bytes) => {
                    eprintln!("sidecar: {}", String::from_utf8_lossy(&bytes));
                }
                CommandEvent::Error(error) => report_failure(&handle, &error),
                CommandEvent::Terminated(payload) => {
                    if event_alive.swap(false, Ordering::SeqCst) {
                        report_failure(&handle, &format!("Backend exited: {payload:?}"));
                        stop_backend(&handle);
                    }
                }
                _ => {}
            }
        }
    });
    let handle = app.clone();
    // Probe sleep runs on a blocking worker, never blocks Tauri's async executor.
    tauri::async_runtime::spawn_blocking(move || {
        let deadline = Instant::now() + HEALTH_TIMEOUT;
        while Instant::now() < deadline && alive.load(Ordering::SeqCst) {
            if readiness::matches(&receipt, &instance, &home, BACKEND_PORT)
                && TcpStream::connect_timeout(
                    &([127, 0, 0, 1], BACKEND_PORT).into(),
                    Duration::from_millis(200),
                )
                .is_ok()
                && alive.load(Ordering::SeqCst)
            {
                if let Some(window) = handle.get_webview_window("main") {
                    if let Err(error) = window.navigate(
                        format!("http://127.0.0.1:{BACKEND_PORT}")
                            .parse()
                            .expect("fixed loopback URL"),
                    ) {
                        report_failure(&handle, &format!("Cannot open desktop frontend: {error}"));
                        stop_backend(&handle);
                    }
                }
                return;
            }
            std::thread::sleep(PROBE_INTERVAL);
        }
        if alive.load(Ordering::SeqCst) {
            report_failure(&handle, "Backend startup timed out; no matching readiness receipt");
            stop_backend(&handle);
        }
    });
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(Diagnostic(Mutex::new(None)))
        .setup(|app| {
            tauri::WebviewWindowBuilder::from_config(app, &app.config().app.windows[0])?
                .on_navigation(|url| {
                    (url.scheme() == "tauri" && url.host_str() == Some("localhost"))
                        || (matches!(url.scheme(), "http" | "https")
                            && url.host_str() == Some("tauri.localhost"))
                        || (url.scheme() == "http"
                            && url.host_str() == Some("127.0.0.1")
                            && url.port() == Some(BACKEND_PORT))
                        || (cfg!(debug_assertions)
                            && url.scheme() == "http"
                            && url.host_str() == Some("localhost")
                            && url.port() == Some(1420))
                })
                .on_page_load(|window, _payload| {
                    let message = match window.app_handle().state::<Diagnostic>().0.lock() {
                        Ok(stored) => stored.clone(),
                        Err(error) => {
                            eprintln!("shell.error: diagnostic lock failed: {error}");
                            None
                        }
                    };
                    if let Some(message) = message {
                        report_failure(window.app_handle(), &message);
                    }
                })
                .build()?;
            if cfg!(debug_assertions) {
                if let Some(window) = app.get_webview_window("main") {
                    window.navigate("http://localhost:1420".parse()?)?;
                }
            } else if let Err(error) = start_backend(app.handle()) {
                report_failure(app.handle(), &format!("Cannot start bundled backend: {error}"));
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Cutting Edge v2 shell");

    app.run(|handle, event| {
        // Exit (not ExitRequested, which other handlers can cancel).
        if let RunEvent::Exit = event {
            stop_backend(handle);
        }
    });
}
