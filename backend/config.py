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
# Configuración de correo para recuperación de contraseña.
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "465"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "tu_usuario_de_email@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USERNAME)
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "EmoVest")
SIGNUP_NOTIFY_TO = os.getenv("SIGNUP_NOTIFY_TO", EMAIL_FROM)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# URL base del servicio Ollama. En Docker local apunta al host.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

# Almacenamiento local de imágenes de operaciones.
IMAGE_STORAGE_DIR = os.getenv("IMAGE_STORAGE_DIR", "images")
MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", "5"))
