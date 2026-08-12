//! Oracle2PolarDB 迁移工具桌面客户端 - 主库
//!
//! 功能:
//! - 启动/停止本地 Django 后端进程(端口 8000)
//! - 检测后端健康状态
//! - 提供系统信息给前端
//! - 应用退出时自动清理后端进程

use std::process::{Child, Command, Stdio};
use std::net::ToSocketAddrs;
use std::sync::Mutex;
use std::time::{Duration, Instant};
use sysinfo::{ProcessRefreshKind, System};
use tauri::{Manager, State};

/// 后端进程句柄(全局唯一,用 Mutex 保护)
struct BackendProcess(Mutex<Option<Child>>);

/// 后端配置
const BACKEND_HOST: &str = "127.0.0.1";
const BACKEND_PORT: u16 = 8000;
const BACKEND_STARTUP_TIMEOUT_SECS: u64 = 30;

/// 查找项目根目录的 manage.py
fn find_manage_py(app: &tauri::AppHandle) -> Option<std::path::PathBuf> {
    // 1. 尝试应用资源目录(打包后)
    if let Ok(resource_dir) = app.path().resource_dir() {
        let candidate = resource_dir.join("backend").join("manage.py");
        if candidate.exists() {
            return Some(candidate);
        }
    }

    // 2. 开发模式:从 src-tauri 上一级查找
    let manifest_dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let candidates = [
        manifest_dir.join("..").join("manage.py"),
        manifest_dir.join("..").join("..").join("manage.py"),
        std::path::PathBuf::from("manage.py"),
    ];
    for c in &candidates {
        if c.exists() {
            return Some(c.clone());
        }
    }
    None
}

/// 查找 Python 解释器
fn find_python() -> Option<String> {
    let venv_candidates = [
        std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("venv")
            .join("bin")
            .join("python3"),
        std::path::PathBuf::from("venv").join("bin").join("python3"),
    ];
    for c in &venv_candidates {
        if c.exists() {
            return Some(c.to_string_lossy().into_owned());
        }
    }
    if which::which("python3").is_ok() {
        return Some("python3".into());
    }
    if which::which("python").is_ok() {
        return Some("python".into());
    }
    None
}

/// 启动 Django 后端服务
#[tauri::command]
fn start_backend(
    app: tauri::AppHandle,
    state: State<'_, BackendProcess>,
) -> Result<String, String> {
    let mut guard = state.0.lock().map_err(|e| format!("锁获取失败: {}", e))?;
    if guard.is_some() {
        if let Some(ref mut child) = *guard {
            match child.try_wait() {
                Ok(None) => {
                    return Ok(format!("后端已在运行: http://{}:{}", BACKEND_HOST, BACKEND_PORT));
                }
                _ => {
                    *guard = None;
                }
            }
        }
    }

    let manage_py = find_manage_py(&app).ok_or_else(|| {
        "找不到 manage.py,请确认后端代码已随应用分发或项目结构完整".to_string()
    })?;
    let python = find_python().ok_or_else(|| {
        "找不到 Python 解释器,请安装 Python 3.12+ 或配置虚拟环境".to_string()
    })?;

    let workdir = manage_py
        .parent()
        .ok_or_else(|| "无法定位项目目录".to_string())?;

    let is_windows = cfg!(target_os = "windows");
    let mut cmd = if !is_windows && which::which("gunicorn").is_ok() {
        let mut c = Command::new("gunicorn");
        c.args([
            "--bind",
            &format!("{}:{}", BACKEND_HOST, BACKEND_PORT),
            "--workers",
            "3",
            "--timeout",
            "120",
            "--access-logfile",
            "-",
            "--error-logfile",
            "-",
            "oracle2polardb_pg.wsgi:application",
        ]);
        c
    } else {
        let mut c = Command::new(&python);
        c.args([
            "manage.py",
            "runserver",
            &format!("{}:{}", BACKEND_HOST, BACKEND_PORT),
            "--noreload",
            "--insecure",
        ]);
        c
    };

    cmd.current_dir(workdir)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .stdin(Stdio::null());

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    let child = cmd.spawn().map_err(|e| {
        format!(
            "启动后端失败: {}。请确认 Python 环境与依赖已正确安装。",
            e
        )
    })?;

    let pid = child.id();
    *guard = Some(child);

    let start = Instant::now();
    let health_url = format!("http://{}:{}/api/health/", BACKEND_HOST, BACKEND_PORT);
    while start.elapsed() < Duration::from_secs(BACKEND_STARTUP_TIMEOUT_SECS) {
        std::thread::sleep(Duration::from_millis(500));
        if std::net::TcpStream::connect(format!("{}:{}", BACKEND_HOST, BACKEND_PORT)).is_ok() {
            let _ = reqwest_lite(&health_url);
            return Ok(format!(
                "后端已启动: http://{}:{} (PID: {})",
                BACKEND_HOST, BACKEND_PORT, pid
            ));
        }
    }

    Err(format!(
        "后端启动超时({}秒),请检查日志或手动启动: cd {} && {} manage.py runserver",
        BACKEND_STARTUP_TIMEOUT_SECS,
        workdir.display(),
        python
    ))
}

/// 极简 HTTP GET(避免引入 reqwest 重依赖)
fn reqwest_lite(url: &str) -> bool {
    use std::io::{Read, Write};
    use std::net::TcpStream;

    let parsed = match url::parse(url) {
        Ok(u) => u,
        Err(_) => return false,
    };
    let host = parsed.host_str().unwrap_or("127.0.0.1");
    let port = parsed.port().unwrap_or(80);
    let path = if parsed.path().is_empty() { "/" } else { parsed.path() };

    let addr_str = format!("{}:{}", host, port);
    let socket_addrs = match addr_str.to_socket_addrs() {
        Ok(addrs) => addrs.collect::<Vec<_>>(),
        Err(_) => return false,
    };
    if socket_addrs.is_empty() {
        return false;
    }

    let mut stream = match TcpStream::connect_timeout(&socket_addrs[0], Duration::from_secs(2)) {
        Ok(s) => s,
        Err(_) => return false,
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
    let request = format!("GET {} HTTP/1.0\r\nHost: {}\r\n\r\n", path, host);
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }
    let mut resp = Vec::with_capacity(256);
    let _ = stream.read_to_end(&mut resp);
    if let Ok(text) = String::from_utf8(resp) {
        return text.starts_with("HTTP/")
            && (text.contains(" 200 ") || text.contains(" 301 ") || text.contains(" 302 "));
    }
    false
}

/// 停止后端服务
#[tauri::command]
fn stop_backend(state: State<'_, BackendProcess>) -> Result<String, String> {
    let mut guard = state.0.lock().map_err(|e| format!("锁获取失败: {}", e))?;
    if let Some(ref mut child) = *guard {
        let pid = child.id();
        let kill_result = child.kill();
        let _ = child.wait();
        *guard = None;
        match kill_result {
            Ok(_) => Ok(format!("后端已停止 (PID: {})", pid)),
            Err(e) => Err(format!("停止后端失败: {}", e)),
        }
    } else {
        Ok("后端未运行".to_string())
    }
}

/// 查询后端状态
#[tauri::command]
fn backend_status(state: State<'_, BackendProcess>) -> Result<bool, String> {
    let mut guard = state.0.lock().map_err(|e| format!("锁获取失败: {}", e))?;
    if let Some(ref mut child) = *guard {
        match child.try_wait() {
            Ok(None) => return Ok(true),
            _ => *guard = None,
        }
    }
    Ok(false)
}

/// 获取后端服务地址
#[tauri::command]
fn backend_url() -> String {
    format!("http://{}:{}", BACKEND_HOST, BACKEND_PORT)
}

/// 获取系统信息
#[tauri::command]
fn system_info() -> serde_json::Value {
    let mut sys = System::new();
    sys.refresh_cpu_specifics(ProcessRefreshKind::everything());
    serde_json::json!({
        "os": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
        "backend_url": backend_url(),
        "version": env!("CARGO_PKG_VERSION"),
    })
}

/// 应用入口
pub fn run() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info"))
        .format_timestamp(None)
        .init();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .manage(BackendProcess(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![
            start_backend,
            stop_backend,
            backend_status,
            backend_url,
            system_info,
        ])
        .setup(|app| {
            log::info!(
                "桌面客户端启动 v{} on {}/{}",
                env!("CARGO_PKG_VERSION"),
                std::env::consts::OS,
                std::env::consts::ARCH
            );
            if let Some(window) = app.get_webview_window("main") {
                log::info!("主窗口已创建: {}", window.title().unwrap_or_default());
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let app = window.app_handle();
                if let Some(state) = app.try_state::<BackendProcess>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(ref mut child) = *guard {
                            log::info!("窗口关闭,停止后端进程 PID: {}", child.id());
                            let _ = child.kill();
                            let _ = child.wait();
                        }
                        *guard = None;
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("运行 Tauri 应用时出错");
}
