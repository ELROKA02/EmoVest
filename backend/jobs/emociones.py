from ai.providers.base import AIJobObsolete
from database import SessionLocal
from models import Operacion
from routers.ia import guardar_registro_emocional


def process_emociones_job(
    id_operacion: int,
    texto: str,
    *,
    db=None,
    commit: bool = True,
) -> dict:
    # El runner SQLite inyecta una sesión para confirmar el registro emocional
    # y el estado `completed` en la misma transacción.
    owns_session = db is None
    db = db or SessionLocal()

    try:
        operation_exists = db.query(Operacion.id).filter(
            Operacion.id == id_operacion
        ).first()
        if operation_exists is None:
            raise AIJobObsolete(
                "La operación ya no existe; el trabajo no se procesará."
            )
        guardar_registro_emocional(texto, id_operacion, db)
        if commit:
            db.commit()
        return {
            "status": "ok",
            "operacion_id": id_operacion,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        if owns_session:
            db.close()
