// The Rust backend owns one Simorgh engine process. The frontend never sees a
// pipe: it calls `engine_start` / `engine_send`, and every line the engine
// prints is forwarded to the webview as an `engine-line` event. The engine and
// its data (opening book, weights) are bundled as resources and run from their
// own directory so the engine's relative `data/…` paths resolve.

use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::Mutex;

use tauri::{AppHandle, Emitter, Manager, State};

#[cfg(windows)]
use std::os::windows::process::CommandExt;
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[derive(Default)]
struct EngineState {
    stdin: Mutex<Option<ChildStdin>>,
    child: Mutex<Option<Child>>,
}

fn engine_paths(app: &AppHandle) -> Result<(std::path::PathBuf, std::path::PathBuf), String> {
    let dir = app
        .path()
        .resource_dir()
        .map_err(|e| e.to_string())?
        .join("resources")
        .join("engine");
    let exe = dir.join(if cfg!(windows) { "simorgh.exe" } else { "simorgh" });
    Ok((dir, exe))
}

#[tauri::command]
fn engine_start(app: AppHandle, state: State<EngineState>) -> Result<(), String> {
    // already running?
    if state.stdin.lock().unwrap().is_some() {
        return Ok(());
    }
    let (dir, exe) = engine_paths(&app)?;

    let mut cmd = Command::new(&exe);
    cmd.current_dir(&dir)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    #[cfg(windows)]
    cmd.creation_flags(CREATE_NO_WINDOW);

    let mut child = cmd
        .spawn()
        .map_err(|e| format!("failed to start engine at {exe:?}: {e}"))?;

    let stdout = child.stdout.take().ok_or("no engine stdout")?;
    let stdin = child.stdin.take().ok_or("no engine stdin")?;

    let handle = app.clone();
    std::thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            match line {
                Ok(l) => {
                    let _ = handle.emit("engine-line", l);
                }
                Err(_) => break,
            }
        }
        // engine exited: let the frontend know it may need a restart
        let _ = handle.emit("engine-exit", ());
    });

    *state.stdin.lock().unwrap() = Some(stdin);
    *state.child.lock().unwrap() = Some(child);
    Ok(())
}

#[tauri::command]
fn engine_send(state: State<EngineState>, line: String) -> Result<(), String> {
    let mut guard = state.stdin.lock().unwrap();
    if let Some(stdin) = guard.as_mut() {
        stdin
            .write_all(line.as_bytes())
            .and_then(|_| stdin.write_all(b"\n"))
            .and_then(|_| stdin.flush())
            .map_err(|e| e.to_string())
    } else {
        Err("engine not running".into())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(EngineState::default())
        .invoke_handler(tauri::generate_handler![engine_start, engine_send])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
