from database import SessionLocal
from routers.ia import guardar_registro_emocional


def process_emociones_job(id_operacion: int, texto: str) -> dict:
    # Cada job abre su propia sesion de BD (independiente del request HTTP).
    db = SessionLocal()

    try:
        # Ejecuta la clasificacion y guarda/actualiza el registro emocional.
        guardar_registro_emocional(texto, id_operacion, db)
        db.commit()
        return {
            "status": "ok",
            "operacion_id": id_operacion,
        }
    except Exception:
        # Si algo falla, revierte cambios de este job y propaga el error a RQ.
        db.rollback()
        raise
    finally:
        # Libera siempre la conexion de BD para evitar fugas.
        db.close()
