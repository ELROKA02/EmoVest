use getrandom::fill as fill_random;
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeMap,
    fs,
    io::{Read, Write},
    net::{SocketAddr, TcpStream},
    path::PathBuf,
    sync::Mutex,
    time::{Duration, Instant},
};
use tauri::{AppHandle, Manager, RunEvent, State};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};

const READY_PREFIX: &str = "EMOVEST_READY ";
const ERROR_PREFIX: &str = "EMOVEST_ERROR ";
const DESKTOP_TOKEN_HEADER: &str = "X-Emovest-Desktop-Token";
const STARTUP_TIMEOUT: Duration = Duration::from_secs(30);
const HTTP_TIMEOUT: Duration = Duration::from_secs(5);
const LONG_HTTP_TIMEOUT: Duration = Duration::from_secs(120);
#[cfg(windows)]
const SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(15);

#[derive(Clone)]
struct BackendConnection {
    port: u16,
}

struct RuntimeState {
    backend: Option<BackendConnection>,
    child: Option<CommandChild>,
    cancel_file: Option<PathBuf>,
    startup_error: Option<String>,
    shutting_down: bool,
    generation: u64,
    #[cfg(windows)]
    job: Option<WindowsJob>,
}

struct DesktopState {
    runtime: Mutex<RuntimeState>,
    token: String,
    data_dir: PathBuf,
    config_dir: PathBuf,
    log_dir: PathBuf,
    backup_dir: PathBuf,
    image_dir: PathBuf,
    model_dir: PathBuf,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopBackendInfo {
    api_base_url: String,
    app_version: String,
    desktop_token: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopDiagnostics {
    healthy: bool,
    sidecar_pid: Option<u32>,
    schema_revision: Option<String>,
    jobs: BTreeMap<String, u64>,
    data_dir: String,
    config_dir: String,
    log_dir: String,
    backup_dir: String,
}

#[derive(Deserialize)]
struct ReadyMessage {
    port: u16,
}

#[derive(Deserialize)]
struct SidecarErrorMessage {
    message: String,
    code: Option<String>,
    recoverable: Option<bool>,
    backup_path: Option<String>,
}

#[derive(Deserialize)]
struct ReadyResponse {
    ready: bool,
}

#[derive(Deserialize)]
struct BackendDiagnostics {
    healthy: bool,
    schema_revision: Option<String>,
    jobs: BTreeMap<String, u64>,
}

#[derive(Deserialize)]
struct BackupResponse {
    #[serde(alias = "path")]
    backup_path: String,
}

#[cfg(windows)]
struct WindowsJob(windows_sys::Win32::Foundation::HANDLE);

#[cfg(windows)]
unsafe impl Send for WindowsJob {}
#[cfg(windows)]
unsafe impl Sync for WindowsJob {}

#[cfg(windows)]
impl Drop for WindowsJob {
    fn drop(&mut self) {
        if !self.0.is_null() {
            unsafe {
                windows_sys::Win32::Foundation::CloseHandle(self.0);
            }
        }
    }
}

#[cfg(windows)]
impl WindowsJob {
    fn terminate_and_wait(&self, timeout: Duration) -> Result<(), String> {
        use std::mem::size_of;
        use windows_sys::Win32::System::JobObjects::{
            JobObjectBasicAccountingInformation, QueryInformationJobObject, TerminateJobObject,
            JOBOBJECT_BASIC_ACCOUNTING_INFORMATION,
        };

        unsafe {
            if TerminateJobObject(self.0, 1) == 0 {
                return Err(format!(
                    "No se pudo terminar el supervisor de procesos de Windows: {}",
                    std::io::Error::last_os_error()
                ));
            }

            let deadline = Instant::now() + timeout;
            loop {
                let mut accounting = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION::default();
                if QueryInformationJobObject(
                    self.0,
                    JobObjectBasicAccountingInformation,
                    &mut accounting as *mut _ as *mut _,
                    size_of::<JOBOBJECT_BASIC_ACCOUNTING_INFORMATION>() as u32,
                    std::ptr::null_mut(),
                ) == 0
                {
                    return Err(format!(
                        "No se pudo consultar el supervisor de procesos de Windows: {}",
                        std::io::Error::last_os_error()
                    ));
                }
                if accounting.ActiveProcesses == 0 {
                    return Ok(());
                }
                if Instant::now() >= deadline {
                    return Err(
                        "El supervisor de procesos de Windows no terminó dentro del plazo.".into(),
                    );
                }
                std::thread::sleep(Duration::from_millis(50));
            }
        }
    }
}

#[cfg(windows)]
fn assign_kill_on_close_job(pid: u32) -> Result<WindowsJob, String> {
    use std::{mem::size_of, ptr};
    use windows_sys::Win32::{
        Foundation::CloseHandle,
        System::{
            JobObjects::{
                AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
                SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
                JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
            },
            Threading::{OpenProcess, PROCESS_SET_QUOTA, PROCESS_TERMINATE},
        },
    };

    unsafe {
        let job = CreateJobObjectW(ptr::null(), ptr::null());
        if job.is_null() {
            return Err("No se pudo crear el supervisor de procesos de Windows.".into());
        }

        let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        if SetInformationJobObject(
            job,
            JobObjectExtendedLimitInformation,
            &info as *const _ as *const _,
            size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
        ) == 0
        {
            CloseHandle(job);
            return Err("No se pudo configurar el supervisor de procesos de Windows.".into());
        }

        let process = OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, 0, pid);
        if process.is_null() {
            CloseHandle(job);
            return Err("No se pudo abrir el proceso local para supervisarlo.".into());
        }

        let assigned = AssignProcessToJobObject(job, process);
        CloseHandle(process);
        if assigned == 0 {
            CloseHandle(job);
            return Err("No se pudo asociar el servicio local a su supervisor.".into());
        }

        Ok(WindowsJob(job))
    }
}

#[cfg(not(windows))]
fn assign_kill_on_close_job(_pid: u32) -> Result<(), String> {
    Ok(())
}

#[cfg(windows)]
fn wait_for_process_exit(pid: u32, timeout: Duration) -> bool {
    use windows_sys::Win32::{
        Foundation::{CloseHandle, WAIT_OBJECT_0},
        System::Threading::{OpenProcess, WaitForSingleObject, PROCESS_SYNCHRONIZE},
    };

    unsafe {
        let process = OpenProcess(PROCESS_SYNCHRONIZE, 0, pid);
        if process.is_null() {
            return true;
        }
        let timeout_ms = timeout.as_millis().min(u32::MAX as u128) as u32;
        let exited = WaitForSingleObject(process, timeout_ms) == WAIT_OBJECT_0;
        CloseHandle(process);
        exited
    }
}

#[cfg(not(windows))]
fn wait_for_process_exit(_pid: u32, _timeout: Duration) -> bool {
    std::thread::sleep(Duration::from_millis(150));
    false
}

#[cfg(windows)]
fn terminate_sidecar_process(
    child: Option<CommandChild>,
    job: Option<WindowsJob>,
    cancel_file: Option<PathBuf>,
    graceful_wait: bool,
) {
    if graceful_wait {
        if let Some(child) = child.as_ref() {
            if wait_for_process_exit(child.pid(), SHUTDOWN_TIMEOUT) {
                drop(job);
                return;
            }
        }
        eprintln!(
            "EmoVest agotó el cierre normal del sidecar; se forzará solo el proceso asociado."
        );
    }

    request_sidecar_cancel(cancel_file.as_ref());
    if let Some(child) = child.as_ref() {
        if wait_for_process_exit(child.pid(), Duration::from_secs(6)) {
            drop(job);
            return;
        }
    }

    let job_finished = job
        .as_ref()
        .map(|job| match job.terminate_and_wait(Duration::from_secs(5)) {
            Ok(()) => true,
            Err(error) => {
                eprintln!("EmoVest no pudo cerrar completamente el sidecar: {error}");
                false
            }
        })
        .unwrap_or(false);

    if let Some(child) = child {
        let pid = child.pid();
        if job_finished {
            drop(child);
        } else if let Err(error) = child.kill() {
            eprintln!("EmoVest no pudo terminar el proceso local {pid}: {error}");
        }
        if !wait_for_process_exit(pid, Duration::from_secs(5)) {
            eprintln!("El proceso local {pid} no terminó dentro del plazo.");
        }
    }
    drop(job);
}

#[cfg(not(windows))]
fn terminate_sidecar_process(
    child: Option<CommandChild>,
    cancel_file: Option<PathBuf>,
    _graceful_wait: bool,
) {
    request_sidecar_cancel(cancel_file.as_ref());
    if let Some(child) = child {
        let pid = child.pid();
        if let Err(error) = child.kill() {
            eprintln!("EmoVest no pudo terminar el proceso local {pid}: {error}");
        }
        let _ = wait_for_process_exit(pid, Duration::from_secs(2));
    }
}

fn request_sidecar_cancel(cancel_file: Option<&PathBuf>) {
    let Some(cancel_file) = cancel_file else {
        return;
    };
    if let Err(error) = fs::write(cancel_file, b"stop") {
        eprintln!("No se pudo señalar el cierre del servicio local: {error}");
    }
}

fn generate_token() -> Result<String, String> {
    let mut bytes = [0_u8; 32];
    fill_random(&mut bytes).map_err(|_| "No se pudo generar la credencial local.".to_string())?;
    Ok(bytes.iter().map(|byte| format!("{byte:02x}")).collect())
}

fn show_main_window(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn set_startup_error(app: &AppHandle, message: impl Into<String>) {
    if let Some(state) = app.try_state::<DesktopState>() {
        if let Ok(mut runtime) = state.runtime.lock() {
            runtime.startup_error = Some(message.into());
        }
    }
    show_main_window(app);
}

fn set_generation_error(app: &AppHandle, generation: u64, message: impl Into<String>) {
    let mut should_show = false;
    if let Some(state) = app.try_state::<DesktopState>() {
        if let Ok(mut runtime) = state.runtime.lock() {
            if runtime.generation == generation {
                if runtime.startup_error.is_none() {
                    runtime.startup_error = Some(message.into());
                }
                should_show = true;
            }
        }
    }
    if should_show {
        show_main_window(app);
    }
}

fn parse_http_response(raw: &str) -> Result<(u16, String), String> {
    let (headers, body) = raw
        .split_once("\r\n\r\n")
        .ok_or_else(|| "Respuesta HTTP local no válida.".to_string())?;
    let status = headers
        .lines()
        .next()
        .and_then(|line| line.split_whitespace().nth(1))
        .and_then(|value| value.parse::<u16>().ok())
        .ok_or_else(|| "Estado HTTP local no válido.".to_string())?;
    Ok((status, body.to_string()))
}

fn local_http_request(
    port: u16,
    token: &str,
    method: &str,
    path: &str,
    body: Option<&str>,
) -> Result<(u16, String), String> {
    local_http_request_with_timeout(port, token, method, path, body, HTTP_TIMEOUT)
}

fn local_http_request_with_timeout(
    port: u16,
    token: &str,
    method: &str,
    path: &str,
    body: Option<&str>,
    read_timeout: Duration,
) -> Result<(u16, String), String> {
    let address = SocketAddr::from(([127, 0, 0, 1], port));
    let mut stream = TcpStream::connect_timeout(&address, HTTP_TIMEOUT)
        .map_err(|_| "El servicio local no responde.".to_string())?;
    stream
        .set_read_timeout(Some(read_timeout))
        .map_err(|_| "No se pudo configurar la lectura local.".to_string())?;
    stream
        .set_write_timeout(Some(HTTP_TIMEOUT))
        .map_err(|_| "No se pudo configurar la escritura local.".to_string())?;

    let payload = body.unwrap_or("");
    let request = format!(
        "{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n{DESKTOP_TOKEN_HEADER}: {token}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{payload}",
        payload.len()
    );
    stream
        .write_all(request.as_bytes())
        .map_err(|_| "No se pudo contactar con el servicio local.".to_string())?;

    let mut response = String::new();
    stream
        .read_to_string(&mut response)
        .map_err(|_| "No se pudo leer la respuesta del servicio local.".to_string())?;
    parse_http_response(&response)
}

fn wait_until_healthy(port: u16, token: &str) -> Result<(), String> {
    let deadline = Instant::now() + STARTUP_TIMEOUT;
    while Instant::now() < deadline {
        if let Ok((200, body)) = local_http_request(port, token, "GET", "/health/ready", None) {
            if serde_json::from_str::<ReadyResponse>(&body)
                .map(|response| response.ready)
                .unwrap_or(false)
            {
                return Ok(());
            }
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    Err("El servicio local agotó el tiempo de arranque.".into())
}

#[cfg(not(windows))]
fn wait_until_closed(port: u16) {
    let address = SocketAddr::from(([127, 0, 0, 1], port));
    let deadline = Instant::now() + Duration::from_secs(15);
    while Instant::now() < deadline {
        if TcpStream::connect_timeout(&address, Duration::from_millis(100)).is_err() {
            return;
        }
        std::thread::sleep(Duration::from_millis(100));
    }
}

fn process_ready_message(app: AppHandle, line: &str, generation: u64) {
    let Some(payload) = line.strip_prefix(READY_PREFIX) else {
        return;
    };
    let ready = match serde_json::from_str::<ReadyMessage>(payload) {
        Ok(ready) if ready.port > 0 => ready,
        _ => {
            set_generation_error(
                &app,
                generation,
                "El servicio local devolvió un puerto no válido.",
            );
            return;
        }
    };

    let token = match app.try_state::<DesktopState>() {
        Some(state) => {
            let is_current = state
                .runtime
                .lock()
                .map(|runtime| runtime.generation == generation)
                .unwrap_or(false);
            if !is_current {
                return;
            }
            state.token.clone()
        }
        None => return,
    };

    std::thread::spawn(move || match wait_until_healthy(ready.port, &token) {
        Ok(()) => {
            let mut is_current = false;
            if let Some(state) = app.try_state::<DesktopState>() {
                if let Ok(mut runtime) = state.runtime.lock() {
                    if runtime.generation == generation {
                        runtime.backend = Some(BackendConnection { port: ready.port });
                        runtime.startup_error = None;
                        is_current = true;
                    }
                }
            }
            if is_current {
                show_main_window(&app);
            }
        }
        Err(error) => set_generation_error(&app, generation, error),
    });
}

fn process_error_message(app: &AppHandle, line: &str, generation: u64) {
    let Some(payload) = line.strip_prefix(ERROR_PREFIX) else {
        return;
    };
    let message = serde_json::from_str::<SidecarErrorMessage>(payload)
        .ok()
        .map(|error| {
            let mut message = error.message.trim().to_string();
            if error.recoverable == Some(true) {
                message.push_str(" Puedes reintentar el arranque sin perder los datos.");
            }
            if let Some(backup_path) = error.backup_path.filter(|path| !path.trim().is_empty()) {
                message.push_str(&format!(" Copia protegida: {backup_path}"));
            }
            if let Some(code) = error.code.filter(|code| !code.trim().is_empty()) {
                message.push_str(&format!(" Código: {code}."));
            }
            message
        })
        .filter(|message| !message.is_empty())
        .unwrap_or_else(|| "El servicio local no pudo completar el arranque.".to_string());
    set_generation_error(app, generation, message);
}

fn start_startup_watchdog(app: AppHandle, generation: u64) {
    std::thread::spawn(move || {
        std::thread::sleep(STARTUP_TIMEOUT);
        let Some(state) = app.try_state::<DesktopState>() else {
            return;
        };
        #[cfg(windows)]
        let (child, job, cancel_file) = state
            .runtime
            .lock()
            .ok()
            .map(|mut runtime| {
                if runtime.generation != generation
                    || runtime.backend.is_some()
                    || runtime.startup_error.is_some()
                    || runtime.shutting_down
                {
                    return (None, None, None);
                }
                runtime.startup_error = Some(
                    "El servicio local agotó el tiempo de arranque. Puedes reintentarlo.".into(),
                );
                (
                    runtime.child.take(),
                    runtime.job.take(),
                    runtime.cancel_file.take(),
                )
            })
            .unwrap_or((None, None, None));
        #[cfg(not(windows))]
        let (child, cancel_file) = state
            .runtime
            .lock()
            .ok()
            .map(|mut runtime| {
                if runtime.generation != generation
                    || runtime.backend.is_some()
                    || runtime.startup_error.is_some()
                    || runtime.shutting_down
                {
                    return (None, None);
                }
                runtime.startup_error = Some(
                    "El servicio local agotó el tiempo de arranque. Puedes reintentarlo.".into(),
                );
                (runtime.child.take(), runtime.cancel_file.take())
            })
            .unwrap_or((None, None));
        #[cfg(windows)]
        terminate_sidecar_process(child, job, cancel_file, false);
        #[cfg(not(windows))]
        terminate_sidecar_process(child, cancel_file, false);
        if state
            .runtime
            .lock()
            .map(|runtime| runtime.startup_error.is_some())
            .unwrap_or(false)
        {
            show_main_window(&app);
        }
    });
}

fn spawn_sidecar(app: &AppHandle) -> Result<(), String> {
    let state = app
        .try_state::<DesktopState>()
        .ok_or_else(|| "No se inicializó el estado de escritorio.".to_string())?;
    let parent_pid = std::process::id().to_string();
    let generation = {
        let mut runtime = state
            .runtime
            .lock()
            .map_err(|_| "El estado del servicio local no está disponible.".to_string())?;
        runtime.generation = runtime.generation.wrapping_add(1);
        runtime.generation
    };
    let cancel_file = state
        .config_dir
        .join(format!(".sidecar-{parent_pid}-{generation}.stop"));
    let _ = fs::remove_file(&cancel_file);
    let envs = [
        ("APP_MODE", "desktop".to_string()),
        ("EMOVEST_DESKTOP_TOKEN", state.token.clone()),
        ("EMOVEST_DESKTOP_HOST", "127.0.0.1".to_string()),
        ("EMOVEST_DESKTOP_PORT", "0".to_string()),
        ("EMOVEST_DESKTOP_PARENT_PID", parent_pid),
        (
            "EMOVEST_DESKTOP_CANCEL_FILE",
            cancel_file.to_string_lossy().into_owned(),
        ),
        (
            "EMOVEST_DATA_DIR",
            state.data_dir.to_string_lossy().into_owned(),
        ),
        (
            "EMOVEST_CONFIG_DIR",
            state.config_dir.to_string_lossy().into_owned(),
        ),
        (
            "EMOVEST_LOG_DIR",
            state.log_dir.to_string_lossy().into_owned(),
        ),
        (
            "EMOVEST_BACKUP_DIR",
            state.backup_dir.to_string_lossy().into_owned(),
        ),
        (
            "EMOVEST_DATABASE_PATH",
            state
                .data_dir
                .join("emovest.sqlite3")
                .to_string_lossy()
                .into_owned(),
        ),
        (
            "IMAGE_STORAGE_DIR",
            state.image_dir.to_string_lossy().into_owned(),
        ),
        (
            "EMOVEST_MODEL_DIR",
            state.model_dir.to_string_lossy().into_owned(),
        ),
        // Evita heredar una clave genérica del entorno del usuario; el backend
        // genera y reutiliza su secreto dentro del directorio de configuración.
        ("SECRET_KEY", String::new()),
    ];

    let command = app
        .shell()
        .sidecar("emovest-backend")
        .map_err(|error| format!("No se encontró el servicio local empaquetado: {error}"))?
        .envs(envs);
    let (mut receiver, child) = command
        .spawn()
        .map_err(|error| format!("No se pudo iniciar el servicio local: {error}"))?;
    let pid = child.pid();

    #[cfg(windows)]
    let job = match assign_kill_on_close_job(pid) {
        Ok(job) => job,
        Err(error) => {
            terminate_sidecar_process(Some(child), None, Some(cancel_file), false);
            return Err(error);
        }
    };
    #[cfg(not(windows))]
    assign_kill_on_close_job(pid)?;

    {
        let mut runtime = state
            .runtime
            .lock()
            .map_err(|_| "El estado del servicio local no está disponible.".to_string())?;
        runtime.child = Some(child);
        runtime.cancel_file = Some(cancel_file);
        runtime.backend = None;
        runtime.startup_error = None;
        runtime.shutting_down = false;
        #[cfg(windows)]
        {
            runtime.job = Some(job);
        }
    }
    start_startup_watchdog(app.clone(), generation);

    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = receiver.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    for line in String::from_utf8_lossy(&bytes).lines() {
                        process_error_message(&handle, line.trim(), generation);
                        process_ready_message(handle.clone(), line.trim(), generation);
                    }
                }
                CommandEvent::Error(_) => {
                    set_generation_error(
                        &handle,
                        generation,
                        "El servicio local informó un error de ejecución.",
                    );
                }
                CommandEvent::Terminated(payload) => {
                    let termination = handle
                        .try_state::<DesktopState>()
                        .and_then(|state| {
                            state.runtime.lock().ok().map(|mut runtime| {
                                if runtime.generation != generation {
                                    return None;
                                }
                                let was_ready = runtime.backend.take().is_some();
                                runtime.child = None;
                                #[cfg(windows)]
                                {
                                    runtime.job = None;
                                }
                                Some((
                                    was_ready,
                                    runtime.shutting_down,
                                    runtime.startup_error.is_some(),
                                    runtime.cancel_file.take(),
                                ))
                            })
                        })
                        .flatten();
                    if let Some((was_ready, shutting_down, had_error, cancel_file)) = termination {
                        if !shutting_down {
                            request_sidecar_cancel(cancel_file.as_ref());
                            if !had_error {
                                set_generation_error(
                                    &handle,
                                    generation,
                                    if was_ready {
                                        format!(
                                            "El servicio local se detuvo inesperadamente (código {}).",
                                            payload.code.unwrap_or(-1)
                                        )
                                    } else {
                                        format!(
                                            "El servicio local terminó antes de estar listo (código {}).",
                                            payload.code.unwrap_or(-1)
                                        )
                                    },
                                );
                            }
                        }
                    }
                }
                _ => {}
            }
        }
    });
    Ok(())
}

fn stop_sidecar(app: &AppHandle, graceful: bool) {
    let Some(state) = app.try_state::<DesktopState>() else {
        return;
    };
    let backend = state.runtime.lock().ok().and_then(|mut runtime| {
        runtime.shutting_down = true;
        runtime.backend.clone()
    });

    let mut graceful_requested = false;
    if graceful {
        if let Some(connection) = backend {
            match local_http_request(
                connection.port,
                &state.token,
                "POST",
                "/desktop/shutdown",
                Some("{}"),
            ) {
                Ok((202, _)) => {
                    graceful_requested = true;
                    #[cfg(not(windows))]
                    wait_until_closed(connection.port);
                }
                Ok((status, _)) => {
                    eprintln!("El sidecar rechazó el cierre normal con HTTP {status}.");
                }
                Err(error) => {
                    eprintln!("No se pudo solicitar el cierre normal del sidecar: {error}");
                }
            }
        }
    }

    #[cfg(windows)]
    let (child, job, cancel_file) = state
        .runtime
        .lock()
        .ok()
        .map(|mut runtime| {
            runtime.backend = None;
            (
                runtime.child.take(),
                runtime.job.take(),
                runtime.cancel_file.take(),
            )
        })
        .unwrap_or((None, None, None));
    #[cfg(not(windows))]
    let (child, cancel_file) = state
        .runtime
        .lock()
        .ok()
        .map(|mut runtime| {
            runtime.backend = None;
            (runtime.child.take(), runtime.cancel_file.take())
        })
        .unwrap_or((None, None));
    #[cfg(windows)]
    terminate_sidecar_process(child, job, cancel_file, graceful_requested);
    #[cfg(not(windows))]
    terminate_sidecar_process(child, cancel_file, graceful_requested);
}

#[tauri::command]
fn restart_desktop_backend(app: AppHandle) -> Result<(), String> {
    stop_sidecar(&app, true);
    spawn_sidecar(&app)
}

fn current_connection(state: &DesktopState) -> Result<BackendConnection, String> {
    let runtime = state
        .runtime
        .lock()
        .map_err(|_| "El estado del servicio local no está disponible.".to_string())?;
    if let Some(error) = &runtime.startup_error {
        return Err(error.clone());
    }
    runtime
        .backend
        .clone()
        .ok_or_else(|| "backend_not_ready".to_string())
}

#[tauri::command]
fn desktop_backend_info(
    app: AppHandle,
    state: State<'_, DesktopState>,
) -> Result<DesktopBackendInfo, String> {
    let connection = current_connection(&state)?;
    Ok(DesktopBackendInfo {
        api_base_url: format!("http://127.0.0.1:{}", connection.port),
        app_version: app.package_info().version.to_string(),
        desktop_token: state.token.clone(),
    })
}

#[tauri::command]
fn desktop_diagnostics(state: State<'_, DesktopState>) -> Result<DesktopDiagnostics, String> {
    let connection = current_connection(&state)?;
    let (status, body) = local_http_request(
        connection.port,
        &state.token,
        "GET",
        "/desktop/diagnostics",
        None,
    )?;
    if status != 200 {
        return Err(format!("El diagnóstico local falló (HTTP {status})."));
    }
    let backend: BackendDiagnostics = serde_json::from_str(&body)
        .map_err(|_| "La respuesta de diagnóstico local no es válida.".to_string())?;
    let sidecar_pid = state
        .runtime
        .lock()
        .ok()
        .and_then(|runtime| runtime.child.as_ref().map(CommandChild::pid));

    Ok(DesktopDiagnostics {
        healthy: backend.healthy,
        sidecar_pid,
        schema_revision: backend.schema_revision,
        jobs: backend.jobs,
        data_dir: state.data_dir.to_string_lossy().into_owned(),
        config_dir: state.config_dir.to_string_lossy().into_owned(),
        log_dir: state.log_dir.to_string_lossy().into_owned(),
        backup_dir: state.backup_dir.to_string_lossy().into_owned(),
    })
}

#[tauri::command]
fn create_desktop_backup(state: State<'_, DesktopState>) -> Result<String, String> {
    let connection = current_connection(&state)?;
    let (status, body) = local_http_request_with_timeout(
        connection.port,
        &state.token,
        "POST",
        "/desktop/backup",
        Some("{}"),
        LONG_HTTP_TIMEOUT,
    )?;
    if status != 200 && status != 201 {
        return Err(format!("La copia de seguridad falló (HTTP {status})."));
    }
    let response: BackupResponse = serde_json::from_str(&body)
        .map_err(|_| "La respuesta de copia de seguridad no es válida.".to_string())?;
    Ok(response.backup_path)
}

pub fn run() -> tauri::Result<()> {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let data_dir = app.path().app_local_data_dir()?;
            let config_dir = app.path().app_config_dir()?;
            let log_dir = app.path().app_log_dir()?;
            let backup_dir = data_dir.join("backups");
            let image_dir = data_dir.join("images");
            let model_dir = data_dir.join("models");
            for directory in [
                &data_dir,
                &config_dir,
                &log_dir,
                &backup_dir,
                &image_dir,
                &model_dir,
            ] {
                fs::create_dir_all(directory)?;
            }

            app.manage(DesktopState {
                runtime: Mutex::new(RuntimeState {
                    backend: None,
                    child: None,
                    cancel_file: None,
                    startup_error: None,
                    shutting_down: false,
                    generation: 0,
                    #[cfg(windows)]
                    job: None,
                }),
                token: generate_token().map_err(std::io::Error::other)?,
                data_dir,
                config_dir,
                log_dir,
                backup_dir,
                image_dir,
                model_dir,
            });

            if let Err(error) = spawn_sidecar(app.handle()) {
                set_startup_error(app.handle(), error);
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            desktop_backend_info,
            restart_desktop_backend,
            desktop_diagnostics,
            create_desktop_backup,
        ])
        .build(tauri::generate_context!())?;

    app.run(|handle, event| {
        if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
            stop_sidecar(handle, true);
        }
    });
    Ok(())
}
