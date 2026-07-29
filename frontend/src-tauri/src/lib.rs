use getrandom::fill as fill_random;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    fs,
    io::{Read, Write},
    net::{SocketAddr, TcpStream},
    path::PathBuf,
    sync::Mutex,
    time::{Duration, Instant},
};
use tauri::{AppHandle, Emitter, Manager, RunEvent, State};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};
use tauri_plugin_updater::{Update, UpdaterExt};

const READY_PREFIX: &str = "EMOVEST_READY ";
const ERROR_PREFIX: &str = "EMOVEST_ERROR ";
const DESKTOP_TOKEN_HEADER: &str = "X-Emovest-Desktop-Token";
const STARTUP_TIMEOUT: Duration = Duration::from_secs(30);
const HTTP_TIMEOUT: Duration = Duration::from_secs(5);
const LONG_HTTP_TIMEOUT: Duration = Duration::from_secs(120);
const SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(15);
const DEFAULT_UPDATER_ENDPOINT: &str =
    "https://github.com/ELROKA02/EmoVest/releases/latest/download/latest.json";

#[derive(Clone)]
struct BackendConnection {
    port: u16,
}

#[derive(Clone)]
struct UpdateSchemaMetadata {
    target_schema_revision: String,
    minimum_schema_revision: String,
}

struct PendingUpdate {
    update: Update,
    bytes: Option<Vec<u8>>,
    schema: UpdateSchemaMetadata,
}

struct RuntimeState {
    backend: Option<BackendConnection>,
    child: Option<CommandChild>,
    pending_update: Option<PendingUpdate>,
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

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct UpdateCheckResult {
    available: bool,
    can_download: bool,
    version: Option<String>,
    notes: Option<String>,
    message: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct DownloadResult {
    version: String,
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
fn wait_for_process_exit(pid: u32, timeout: Duration) {
    use windows_sys::Win32::{
        Foundation::CloseHandle,
        System::Threading::{
            OpenProcess, WaitForSingleObject, PROCESS_SYNCHRONIZE,
        },
    };

    unsafe {
        let process = OpenProcess(PROCESS_SYNCHRONIZE, 0, pid);
        if !process.is_null() {
            let timeout_ms = timeout.as_millis().min(u32::MAX as u128) as u32;
            WaitForSingleObject(process, timeout_ms);
            CloseHandle(process);
        }
    }
}

#[cfg(not(windows))]
fn wait_for_process_exit(_pid: u32, _timeout: Duration) {
    std::thread::sleep(Duration::from_millis(150));
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

fn wait_until_closed(port: u16) {
    let address = SocketAddr::from(([127, 0, 0, 1], port));
    let deadline = Instant::now() + SHUTDOWN_TIMEOUT;
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
        let child = state.runtime.lock().ok().and_then(|mut runtime| {
            if runtime.generation != generation
                || runtime.backend.is_some()
                || runtime.startup_error.is_some()
                || runtime.shutting_down
            {
                return None;
            }
            runtime.startup_error =
                Some("El servicio local agotó el tiempo de arranque. Puedes reintentarlo.".into());
            #[cfg(windows)]
            {
                runtime.job = None;
            }
            runtime.child.take()
        });
        if let Some(child) = child {
            let _ = child.kill();
            show_main_window(&app);
        }
    });
}

fn spawn_sidecar(app: &AppHandle) -> Result<(), String> {
    let state = app
        .try_state::<DesktopState>()
        .ok_or_else(|| "No se inicializó el estado de escritorio.".to_string())?;
    let parent_pid = std::process::id().to_string();
    let envs = [
        ("APP_MODE", "desktop".to_string()),
        ("EMOVEST_DESKTOP_TOKEN", state.token.clone()),
        ("EMOVEST_DESKTOP_HOST", "127.0.0.1".to_string()),
        ("EMOVEST_DESKTOP_PORT", "0".to_string()),
        ("EMOVEST_DESKTOP_PARENT_PID", parent_pid),
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
            let _ = child.kill();
            return Err(error);
        }
    };
    #[cfg(not(windows))]
    assign_kill_on_close_job(pid)?;

    let generation = {
        let mut runtime = state
            .runtime
            .lock()
            .map_err(|_| "El estado del servicio local no está disponible.".to_string())?;
        runtime.generation = runtime.generation.wrapping_add(1);
        runtime.child = Some(child);
        runtime.backend = None;
        runtime.startup_error = None;
        runtime.shutting_down = false;
        #[cfg(windows)]
        {
            runtime.job = Some(job);
        }
        runtime.generation
    };
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
                                Some((
                                    was_ready,
                                    runtime.shutting_down,
                                    runtime.startup_error.is_some(),
                                ))
                            })
                        })
                        .flatten();
                    if let Some((was_ready, false, false)) = termination {
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
    let backend = state
        .runtime
        .lock()
        .ok()
        .and_then(|mut runtime| {
            runtime.shutting_down = true;
            runtime.backend.clone()
        });

    if graceful {
        if let Some(connection) = backend {
            let _ = local_http_request(
                connection.port,
                &state.token,
                "POST",
                "/desktop/shutdown",
                Some("{}"),
            );
            wait_until_closed(connection.port);
        }
    }

    let child = state.runtime.lock().ok().and_then(|mut runtime| {
        let child = runtime.child.take();
        runtime.backend = None;
        #[cfg(windows)]
        {
            runtime.job = None;
        }
        child
    });
    if let Some(child) = child {
        let pid = child.pid();
        let _ = child.kill();
        wait_for_process_exit(pid, Duration::from_secs(2));
    }
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

fn updater_configuration() -> Result<(&'static str, &'static str), String> {
    if cfg!(debug_assertions) {
        return Err("El actualizador está desactivado en desarrollo.".into());
    }
    let public_key = option_env!("EMOVEST_UPDATER_PUBLIC_KEY")
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| "El canal de actualizaciones aún no está configurado.".to_string())?;
    let endpoint = option_env!("EMOVEST_UPDATER_ENDPOINT").unwrap_or(DEFAULT_UPDATER_ENDPOINT);
    if !endpoint.starts_with("https://") {
        return Err("El endpoint seguro de actualizaciones no está configurado.".into());
    }
    Ok((public_key, endpoint))
}

fn schema_metadata(raw: &Value) -> Option<UpdateSchemaMetadata> {
    Some(UpdateSchemaMetadata {
        target_schema_revision: raw.get("schema_revision")?.as_str()?.to_string(),
        minimum_schema_revision: raw
            .get("minimum_schema_revision")?
            .as_str()?
            .to_string(),
    })
}

#[tauri::command]
async fn check_for_update(
    app: AppHandle,
    state: State<'_, DesktopState>,
) -> Result<UpdateCheckResult, String> {
    let (public_key, endpoint) = match updater_configuration() {
        Ok(configuration) => configuration,
        Err(message) => {
            return Ok(UpdateCheckResult {
                available: false,
                can_download: false,
                version: None,
                notes: None,
                message,
            })
        }
    };

    let endpoint = endpoint
        .parse()
        .map_err(|_| "El endpoint de actualizaciones no es válido.".to_string())?;
    let updater = app
        .updater_builder()
        .pubkey(public_key)
        .endpoints(vec![endpoint])
        .map_err(|error| error.to_string())?
        .timeout(Duration::from_secs(30))
        .build()
        .map_err(|error| error.to_string())?;
    let Some(update) = updater.check().await.map_err(|error| error.to_string())? else {
        return Ok(UpdateCheckResult {
            available: false,
            can_download: false,
            version: None,
            notes: None,
            message: "EmoVest está actualizado.".into(),
        });
    };

    let version = update.version.clone();
    let notes = update.body.clone();
    let Some(schema) = schema_metadata(&update.raw_json) else {
        return Ok(UpdateCheckResult {
            available: true,
            can_download: false,
            version: Some(version),
            notes,
            message: "La versión existe, pero el canal no declara compatibilidad de datos.".into(),
        });
    };

    state
        .runtime
        .lock()
        .map_err(|_| "El estado del actualizador no está disponible.".to_string())?
        .pending_update = Some(PendingUpdate {
            update,
            bytes: None,
            schema,
        });

    Ok(UpdateCheckResult {
        available: true,
        can_download: true,
        version: Some(version),
        notes,
        message: String::new(),
    })
}

#[tauri::command]
async fn download_update(
    app: AppHandle,
    state: State<'_, DesktopState>,
) -> Result<DownloadResult, String> {
    let update = state
        .runtime
        .lock()
        .map_err(|_| "El estado del actualizador no está disponible.".to_string())?
        .pending_update
        .as_ref()
        .map(|pending| pending.update.clone())
        .ok_or_else(|| "No hay una actualización compatible pendiente.".to_string())?;
    let version = update.version.clone();
    let progress_app = app.clone();
    let mut downloaded = 0_u64;
    let bytes = update
        .download(
            move |chunk_length, content_length| {
                downloaded += chunk_length as u64;
                let percentage = content_length
                    .filter(|total| *total > 0)
                    .map(|total| ((downloaded.saturating_mul(100)) / total).min(100));
                let _ = progress_app.emit(
                    "desktop-update-progress",
                    json!({ "downloaded": downloaded, "total": content_length, "percentage": percentage }),
                );
            },
            || {},
        )
        .await
        .map_err(|error| error.to_string())?;

    let mut runtime = state
        .runtime
        .lock()
        .map_err(|_| "El estado del actualizador no está disponible.".to_string())?;
    let pending = runtime
        .pending_update
        .as_mut()
        .ok_or_else(|| "La actualización pendiente cambió durante la descarga.".to_string())?;
    pending.bytes = Some(bytes);

    Ok(DownloadResult { version })
}

#[tauri::command]
fn install_downloaded_update(app: AppHandle, state: State<'_, DesktopState>) -> Result<(), String> {
    let (update, bytes, schema) = {
        let runtime = state
            .runtime
            .lock()
            .map_err(|_| "El estado del actualizador no está disponible.".to_string())?;
        let pending = runtime
            .pending_update
            .as_ref()
            .ok_or_else(|| "No hay una actualización pendiente.".to_string())?;
        (
            pending.update.clone(),
            pending
                .bytes
                .clone()
                .ok_or_else(|| "La actualización todavía no se ha descargado.".to_string())?,
            pending.schema.clone(),
        )
    };

    let connection = current_connection(&state)?;
    let request = json!({
        "target_version": update.version,
        "target_schema_revision": schema.target_schema_revision,
        "minimum_schema_revision": schema.minimum_schema_revision,
    })
    .to_string();
    let (status, body) = local_http_request_with_timeout(
        connection.port,
        &state.token,
        "POST",
        "/desktop/update/prepare",
        Some(&request),
        LONG_HTTP_TIMEOUT,
    )?;
    if status != 200 {
        return Err(format!(
            "El backend rechazó la preparación de la actualización (HTTP {status})."
        ));
    }
    let response: ReadyResponse = serde_json::from_str(&body)
        .map_err(|_| "La comprobación previa de la actualización no es válida.".to_string())?;
    if !response.ready {
        return Err("La actualización no es compatible con los datos locales.".into());
    }

    stop_sidecar(&app, true);
    if let Err(error) = update.install(&bytes) {
        let restart_result = spawn_sidecar(&app);
        return Err(match restart_result {
            Ok(()) => format!("El instalador no pudo iniciarse: {error}"),
            Err(restart_error) => format!(
                "El instalador no pudo iniciarse ({error}) y el servicio local no se pudo recuperar ({restart_error})."
            ),
        });
    }
    app.restart()
}

pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(
            tauri_plugin_updater::Builder::new()
                .pubkey(option_env!("EMOVEST_UPDATER_PUBLIC_KEY").unwrap_or(""))
                .build(),
        )
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
                    pending_update: None,
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
            check_for_update,
            download_update,
            install_downloaded_update,
        ])
        .build(tauri::generate_context!())
        .expect("No se pudo construir EmoVest Desktop.");

    app.run(|handle, event| {
        if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
            stop_sidecar(handle, true);
        }
    });
}
