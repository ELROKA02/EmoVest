from redis import Redis
from rq import Connection, SimpleWorker

from config import REDIS_URL, RQ_QUEUE_NAME


def main() -> None:
    # Conexion a Redis para escuchar y consumir la cola de trabajos.
    redis_conn = Redis.from_url(REDIS_URL)

    # SimpleWorker no hace fork: necesario en macOS para evitar el crash
    # del runtime de Objective-C tras fork() (signal 6).
    with Connection(redis_conn):
        worker = SimpleWorker([RQ_QUEUE_NAME])
        print(f"Worker escuchando cola: {RQ_QUEUE_NAME}")
        # Bucle bloqueante: procesa jobs continuamente hasta detener el proceso.
        # Los reintentos usan intervalos y RQ los mueve al registro programado;
        # el scheduler integrado debe estar activo para devolverlos a la cola.
        worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
