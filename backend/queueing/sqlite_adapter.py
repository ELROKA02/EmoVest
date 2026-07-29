from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

import config
from models import BackgroundJob
from queueing.base import EmotionJobReceipt


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def emotion_idempotency_key(operation_id: int, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"emotion:{operation_id}:{digest}"


class SqliteEmotionQueue:
    def stage(self, db: Session, operation_id: int, text: str) -> EmotionJobReceipt:
        idempotency_key = emotion_idempotency_key(operation_id, text)
        job_id = str(uuid.uuid4())
        max_attempts = max(
            1, int(getattr(config, "LOCAL_QUEUE_MAX_ATTEMPTS", 4))
        )
        try:
            # A savepoint lets the owning request preserve the operation even if
            # queue staging fails or races another identical enqueue.
            with db.begin_nested():
                existing = db.query(BackgroundJob).filter(
                    BackgroundJob.idempotency_key == idempotency_key
                ).first()
                if existing is not None:
                    job_id = existing.id
                else:
                    db.add(BackgroundJob(
                        id=job_id,
                        kind="emotion_analysis",
                        operation_id=operation_id,
                        idempotency_key=idempotency_key,
                        payload_json=json.dumps(
                            {"operation_id": operation_id, "text": text},
                            ensure_ascii=False,
                        ),
                        status="pending",
                        attempts=0,
                        max_attempts=max_attempts,
                        available_at=utcnow(),
                        created_at=utcnow(),
                        updated_at=utcnow(),
                    ))
                    db.flush()
        except IntegrityError:
            existing = db.query(BackgroundJob).filter(
                BackgroundJob.idempotency_key == idempotency_key
            ).one()
            job_id = existing.id
        except SQLAlchemyError:
            # The savepoint has already rolled back; the caller may still commit
            # the trading operation without emotional analysis.
            raise

        return self._receipt(job_id, idempotency_key, operation_id, text)

    @staticmethod
    def _receipt(
        job_id: str, idempotency_key: str, operation_id: int, text: str
    ) -> EmotionJobReceipt:
        return EmotionJobReceipt(
            id=job_id,
            backend="sqlite",
            idempotency_key=idempotency_key,
            operation_id=operation_id,
            text=text,
        )

    def dispatch(self, _receipt: EmotionJobReceipt) -> None:
        # The row is already durable. This only avoids waiting for the next poll.
        from queueing.runner import wake_background_services

        wake_background_services()
