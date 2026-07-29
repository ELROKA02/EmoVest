"""Fachada estable para la cola emocional SQLite de la edición de escritorio."""
from __future__ import annotations

from sqlalchemy.orm import Session

from database import SessionLocal
from queueing import EmotionJobReceipt, get_emotion_queue


def stage_emociones_job(
    db: Session, id_operacion: int, texto: str
) -> EmotionJobReceipt:
    return get_emotion_queue().stage(db, id_operacion, texto)


def dispatch_emociones_job(receipt: EmotionJobReceipt) -> None:
    get_emotion_queue().dispatch(receipt)


def enqueue_emociones_job(id_operacion: int, texto: str) -> EmotionJobReceipt:
    """Enqueue outside a request transaction.

    HTTP flows should prefer stage+dispatch so SQLite can commit the operation
    and its outbox job atomically.
    """
    db = SessionLocal()
    try:
        receipt = stage_emociones_job(db, id_operacion, texto)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    dispatch_emociones_job(receipt)
    return receipt
