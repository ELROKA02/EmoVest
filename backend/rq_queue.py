from redis import Redis
from rq import Queue, Retry

from config import (
    REDIS_URL,
    RQ_DEFAULT_TIMEOUT,
    RQ_FAILURE_TTL,
    RQ_QUEUE_NAME,
    RQ_RESULT_TTL,
    RQ_RETRY_INTERVALS,
    RQ_RETRY_MAX,
)
from jobs.emociones import process_emociones_job


def get_redis_connection() -> Redis:
    # Crea la conexion a Redis que usara RQ como backend de cola.
    return Redis.from_url(REDIS_URL)


def get_emociones_queue() -> Queue:
    # Construye la cola de trabajos de emociones con timeout por defecto.
    return Queue(
        name=RQ_QUEUE_NAME,
        connection=get_redis_connection(),
        default_timeout=RQ_DEFAULT_TIMEOUT,
    )


def enqueue_emociones_job(id_operacion: int, texto: str):
    # Encola el trabajo de IA para ejecutarlo en background sin bloquear el endpoint.
    queue = get_emociones_queue()

    return queue.enqueue(
        # Funcion que ejecutara el worker en otro proceso.
        process_emociones_job,
        id_operacion=id_operacion,
        texto=texto,
        # Politica de reintento ante fallos transitorios (ej: Ollama no disponible).
        retry=Retry(max=RQ_RETRY_MAX, interval=RQ_RETRY_INTERVALS),
        # Tiempo de retencion de jobs exitosos para inspeccion.
        result_ttl=RQ_RESULT_TTL,
        # Tiempo de retencion de jobs fallidos para diagnostico.
        failure_ttl=RQ_FAILURE_TTL,
    )
