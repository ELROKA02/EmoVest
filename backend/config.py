import os

from dotenv import load_dotenv


# Carga variables desde el archivo .env para entornos locales.
load_dotenv()

# URL de conexión a Redis (broker de la cola RQ).
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Nombre de la cola donde se encolan los trabajos de análisis emocional.
RQ_QUEUE_NAME = os.getenv("RQ_QUEUE_NAME", "emociones")

# Tiempo máximo (segundos) permitido para ejecutar un job.
RQ_DEFAULT_TIMEOUT = int(os.getenv("RQ_DEFAULT_TIMEOUT", "180"))

# Tiempo (segundos) que RQ conserva el resultado de jobs exitosos.
RQ_RESULT_TTL = int(os.getenv("RQ_RESULT_TTL", "3600"))

# Tiempo (segundos) que RQ conserva jobs fallidos para inspección.
RQ_FAILURE_TTL = int(os.getenv("RQ_FAILURE_TTL", "86400"))

# Número máximo de reintentos antes de marcar el job como fallido.
RQ_RETRY_MAX = int(os.getenv("RQ_RETRY_MAX", "3"))

# Espera entre reintentos (segundos): 2s, 4s y 8s.
RQ_RETRY_INTERVALS = [2, 4, 8]

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Orígenes permitidos para CORS, separados por comas.
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if origin.strip()
]

# URL base del servicio Ollama. En Docker local apunta al host.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

# Configuracion base de IA. Mantiene Ollama como valor por defecto para no romper
# instalaciones actuales.
AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").strip().lower()
AI_MODEL = os.getenv("AI_MODEL", "clasificador_emociones_gemma4:latest").strip()
AI_BASE_URL = os.getenv("AI_BASE_URL", OLLAMA_HOST).rstrip("/")
AI_INSTALL_MODE = os.getenv("AI_INSTALL_MODE", "manual").strip().lower()

# Configuracion especifica por uso. La clasificacion emocional y el chat pueden
# usar proveedores/modelos distintos.
AI_EMOTION_PROVIDER = os.getenv("AI_EMOTION_PROVIDER", AI_PROVIDER).strip().lower()
AI_EMOTION_MODEL = os.getenv("AI_EMOTION_MODEL", AI_MODEL).strip()
AI_EMOTION_BASE_URL = os.getenv("AI_EMOTION_BASE_URL", AI_BASE_URL).rstrip("/")

AI_CHAT_PROVIDER = os.getenv("AI_CHAT_PROVIDER", AI_PROVIDER).strip().lower()
AI_CHAT_MODEL = os.getenv("AI_CHAT_MODEL", os.getenv("AI_MODEL", "llama3.2:3b")).strip()
AI_CHAT_BASE_URL = os.getenv("AI_CHAT_BASE_URL", AI_BASE_URL).rstrip("/")

# URL por defecto para llama.cpp cuando se ejecute llama-server en local.
LLAMACPP_BASE_URL = os.getenv("LLAMACPP_BASE_URL", "http://localhost:8080").rstrip("/")

# Almacenamiento local de imágenes de operaciones.
IMAGE_STORAGE_DIR = os.getenv("IMAGE_STORAGE_DIR", "images")
MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", "5"))
