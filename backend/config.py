import os
import secrets
from pathlib import Path

APP_MODE = os.getenv("APP_MODE", "desktop").strip().lower()
if APP_MODE != "desktop":
    raise RuntimeError(
        "Esta edición de EmoVest solo admite APP_MODE=desktop. "
        "El despliegue servidor anterior se considera legado."
    )

APP_VERSION = os.getenv("EMOVEST_APP_VERSION", "0.4.0").strip()
if not APP_VERSION:
    raise RuntimeError("EMOVEST_APP_VERSION no puede estar vacío.")


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as error:
        raise RuntimeError(f"{name} debe ser un entero.") from error
    if value <= 0:
        raise RuntimeError(f"{name} debe ser mayor que cero.")
    return value


def _positive_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError as error:
        raise RuntimeError(f"{name} debe ser un número.") from error
    if value <= 0:
        raise RuntimeError(f"{name} debe ser mayor que cero.")
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(
        f"{name} debe ser true/false, yes/no, on/off o 1/0."
    )


def _default_data_dir() -> Path:
    if os.name == "nt":
        base_dir = os.getenv("LOCALAPPDATA")
        if base_dir:
            return Path(base_dir) / "EmoVest"
    xdg_data_home = os.getenv("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "EmoVest"
    return Path.home() / ".local" / "share" / "EmoVest"


def _default_config_dir() -> Path:
    if os.name == "nt":
        base_dir = os.getenv("APPDATA")
        if base_dir:
            return Path(base_dir) / "EmoVest"
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "EmoVest"
    return Path.home() / ".config" / "EmoVest"


def _absolute_dir(env_name: str, default: Path) -> Path:
    configured = Path(os.getenv(env_name, str(default))).expanduser()
    if not configured.is_absolute():
        raise RuntimeError(f"{env_name} debe contener una ruta absoluta.")
    resolved = configured.resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


APP_DATA_DIR = _absolute_dir("EMOVEST_DATA_DIR", _default_data_dir())
APP_CONFIG_DIR = _absolute_dir("EMOVEST_CONFIG_DIR", _default_config_dir())
APP_LOG_DIR = _absolute_dir("EMOVEST_LOG_DIR", APP_DATA_DIR / "logs")
DATABASE_PATH = Path(
    os.getenv("EMOVEST_DATABASE_PATH", str(APP_DATA_DIR / "emovest.sqlite3"))
).expanduser()
if not DATABASE_PATH.is_absolute():
    raise RuntimeError("EMOVEST_DATABASE_PATH debe contener una ruta absoluta.")
DATABASE_PATH = DATABASE_PATH.resolve()
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

IMAGE_STORAGE_PATH = _absolute_dir("IMAGE_STORAGE_DIR", APP_DATA_DIR / "images")
MODEL_STORAGE_DIR = _absolute_dir("EMOVEST_MODEL_DIR", APP_DATA_DIR / "models")
BACKUP_DIR = _absolute_dir("EMOVEST_BACKUP_DIR", APP_DATA_DIR / "backups")

SQLITE_BUSY_TIMEOUT_MS = _positive_int("SQLITE_BUSY_TIMEOUT_MS", 5000)
SQLITE_BACKUP_RETENTION = _positive_int("SQLITE_BACKUP_RETENTION", 5)

LOCAL_QUEUE_POLL_INTERVAL_SECONDS = _positive_float(
    "LOCAL_QUEUE_POLL_INTERVAL_SECONDS", 0.5
)
LOCAL_QUEUE_LEASE_SECONDS = _positive_int("LOCAL_QUEUE_LEASE_SECONDS", 180)
LOCAL_QUEUE_MAX_ATTEMPTS = _positive_int("LOCAL_QUEUE_MAX_ATTEMPTS", 4)
LOCAL_QUEUE_RETRY_INTERVALS = [2, 4, 8]
LOCAL_QUEUE_SHUTDOWN_TIMEOUT_SECONDS = _positive_float(
    "LOCAL_QUEUE_SHUTDOWN_TIMEOUT_SECONDS", 10
)
LOCAL_QUEUE_ERROR_BACKOFF_SECONDS = _positive_float(
    "LOCAL_QUEUE_ERROR_BACKOFF_SECONDS", 0.5
)
LOCAL_QUEUE_ERROR_MAX_BACKOFF_SECONDS = _positive_float(
    "LOCAL_QUEUE_ERROR_MAX_BACKOFF_SECONDS", 30
)
if LOCAL_QUEUE_ERROR_MAX_BACKOFF_SECONDS < LOCAL_QUEUE_ERROR_BACKOFF_SECONDS:
    raise RuntimeError(
        "LOCAL_QUEUE_ERROR_MAX_BACKOFF_SECONDS no puede ser menor que "
        "LOCAL_QUEUE_ERROR_BACKOFF_SECONDS."
    )
LOCAL_RUNTIME_CLEANUP_INTERVAL_SECONDS = _positive_int(
    "LOCAL_RUNTIME_CLEANUP_INTERVAL_SECONDS", 3600
)
LOCAL_JOB_RETENTION_SECONDS = _positive_int(
    "LOCAL_JOB_RETENTION_SECONDS", 2592000
)
LOCAL_RUNTIME_CLEANUP_BATCH_SIZE = _positive_int(
    "LOCAL_RUNTIME_CLEANUP_BATCH_SIZE", 500
)
CHAT_SESSION_TTL_SECONDS = _positive_int("CHAT_SESSION_TTL_SECONDS", 8 * 60 * 60)

FRONTEND_URL = os.getenv("FRONTEND_URL", "tauri://localhost")
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "tauri://localhost,http://tauri.localhost,http://localhost:5173,"
        "http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").strip().lower()
AI_MODEL = os.getenv("AI_MODEL", "clasificador_emociones_gemma4:latest").strip()
AI_BASE_URL = os.getenv("AI_BASE_URL", OLLAMA_HOST).rstrip("/")
AI_INSTALL_MODE = os.getenv("AI_INSTALL_MODE", "manual").strip().lower()
AI_EMOTION_ENABLED = _env_bool("AI_EMOTION_ENABLED", True)
AI_EMOTION_PROVIDER = os.getenv("AI_EMOTION_PROVIDER", AI_PROVIDER).strip().lower()
AI_EMOTION_MODEL = os.getenv("AI_EMOTION_MODEL", AI_MODEL).strip()
AI_EMOTION_BASE_URL = os.getenv("AI_EMOTION_BASE_URL", AI_BASE_URL).rstrip("/")
LLAMACPP_BASE_URL = os.getenv("LLAMACPP_BASE_URL", "http://localhost:8080").rstrip("/")
LLAMACPP_API_KEY = os.getenv("LLAMACPP_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
).rstrip("/")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
AI_CHAT_ENABLED = _env_bool("AI_CHAT_ENABLED", True)
AI_CHAT_PROVIDER = os.getenv("AI_CHAT_PROVIDER", AI_PROVIDER).strip().lower()
AI_CHAT_MODEL = os.getenv("AI_CHAT_MODEL", "qwen3.5:latest").strip()
AI_CHAT_BASE_URL = os.getenv(
    "AI_CHAT_BASE_URL",
    OPENROUTER_BASE_URL if AI_CHAT_PROVIDER == "openrouter" else AI_BASE_URL,
).rstrip("/")
LLAMACPP_TOOL_CALLING_MODELS = {
    model.strip()
    for model in os.getenv("LLAMACPP_TOOL_CALLING_MODELS", "").split(",")
    if model.strip()
}
OPENROUTER_TOOL_CALLING_MODELS = {
    model.strip()
    for model in os.getenv("OPENROUTER_TOOL_CALLING_MODELS", "").split(",")
    if model.strip()
}

IMAGE_STORAGE_DIR = str(IMAGE_STORAGE_PATH)
MAX_IMAGE_SIZE_MB = _positive_int("MAX_IMAGE_SIZE_MB", 5)


def _load_or_create_secret_key() -> str:
    configured = os.getenv("SECRET_KEY")
    if configured:
        if len(configured) < 32:
            raise RuntimeError("SECRET_KEY debe contener al menos 32 caracteres.")
        return configured

    secret_path = APP_CONFIG_DIR / "jwt-secret"
    try:
        secret = secret_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        secret = secrets.token_urlsafe(48)
        try:
            descriptor = os.open(
                secret_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            secret = secret_path.read_text(encoding="utf-8").strip()
        else:
            with os.fdopen(descriptor, "w", encoding="utf-8") as secret_file:
                secret_file.write(secret)
                secret_file.write("\n")
    except OSError as error:
        raise RuntimeError(
            "No se pudo leer el secreto local de autenticación."
        ) from error

    if len(secret) < 32:
        raise RuntimeError(
            "El secreto local de autenticación está dañado o es demasiado corto."
        )
    return secret


SECRET_KEY = _load_or_create_secret_key()
