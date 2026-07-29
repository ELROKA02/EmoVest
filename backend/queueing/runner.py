from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

import config
from ai.providers.base import AIProviderError
from database import SessionLocal
from jobs.emociones import process_emociones_job
from models import BackgroundJob
from queueing import is_desktop_mode


logger = logging.getLogger(__name__)

DEFAULT_TERMINAL_JOB_RETENTION_SECONDS = 30 * 24 * 60 * 60
DEFAULT_RUNTIME_CLEANUP_INTERVAL_SECONDS = 60 * 60
DEFAULT_RUNTIME_CLEANUP_BATCH_SIZE = 500


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _positive_int(name: str, default: int) -> int:
    try:
        return max(1, int(getattr(config, name, default)))
    except (TypeError, ValueError):
        return default


def _positive_float(name: str, default: float) -> float:
    try:
        return max(0.05, float(getattr(config, name, default)))
    except (TypeError, ValueError):
        return default


def _retry_intervals() -> list[int]:
    configured = getattr(config, "LOCAL_QUEUE_RETRY_INTERVALS", [2, 4, 8])
    if isinstance(configured, str):
        configured = configured.split(",")
    try:
        values = [max(1, int(value)) for value in configured]
    except (TypeError, ValueError):
        return [2, 4, 8]
    return values or [2, 4, 8]


@dataclass(frozen=True)
class ClaimedJob:
    id: str
    lease_token: str
    attempts: int
    max_attempts: int
    payload: dict[str, Any]


class LocalQueueRunner:
    def __init__(self) -> None:
        self.poll_seconds = _positive_float(
            "LOCAL_QUEUE_POLL_INTERVAL_SECONDS", 1
        )
        self.lease_seconds = _positive_int("LOCAL_QUEUE_LEASE_SECONDS", 240)
        self.shutdown_timeout = _positive_int(
            "LOCAL_QUEUE_SHUTDOWN_TIMEOUT_SECONDS", 10
        )
        self.claim_error_backoff_seconds = _positive_float(
            "LOCAL_QUEUE_ERROR_BACKOFF_SECONDS", 0.5
        )
        self.claim_error_max_backoff_seconds = _positive_float(
            "LOCAL_QUEUE_ERROR_MAX_BACKOFF_SECONDS", 30
        )
        self.cleanup_interval_seconds = _positive_float(
            "LOCAL_RUNTIME_CLEANUP_INTERVAL_SECONDS",
            DEFAULT_RUNTIME_CLEANUP_INTERVAL_SECONDS,
        )
        self.terminal_retention_seconds = _positive_int(
            "LOCAL_JOB_RETENTION_SECONDS",
            DEFAULT_TERMINAL_JOB_RETENTION_SECONDS,
        )
        self.cleanup_batch_size = _positive_int(
            "LOCAL_RUNTIME_CLEANUP_BATCH_SIZE",
            DEFAULT_RUNTIME_CLEANUP_BATCH_SIZE,
        )
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._lifecycle_lock = threading.Lock()
        self._lease_lock = threading.Lock()
        self._active_leases: dict[str, str] = {}
        self._health_lock = threading.Lock()
        self._consecutive_claim_errors = 0
        self._last_error_code: str | None = None
        self._last_successful_poll_at: datetime | None = None
        self._last_cleanup_at: datetime | None = None
        self._next_cleanup_at = 0.0

    def start(self) -> None:
        with self._lifecycle_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._wake.clear()
            with self._health_lock:
                self._consecutive_claim_errors = 0
                self._last_error_code = None
                self._last_successful_poll_at = None
                self._last_cleanup_at = None
            self._next_cleanup_at = 0.0
            self._thread = threading.Thread(
                target=self._run,
                name="emovest-local-queue",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout: float | None = None) -> bool:
        with self._lifecycle_lock:
            thread = self._thread
            if thread is None:
                return True
            self._stop.set()
            self._wake.set()
        thread.join(timeout if timeout is not None else self.shutdown_timeout)
        stopped = not thread.is_alive()
        if stopped:
            with self._lifecycle_lock:
                if self._thread is thread:
                    self._thread = None
        else:
            self._release_active_leases()
        return stopped

    def wake(self) -> None:
        self._wake.set()

    def is_alive(self) -> bool:
        with self._lifecycle_lock:
            return self._thread is not None and self._thread.is_alive()

    def health_snapshot(self) -> dict[str, Any]:
        alive = self.is_alive()
        with self._health_lock:
            consecutive_errors = self._consecutive_claim_errors
            last_error_code = self._last_error_code
            last_successful_poll_at = self._last_successful_poll_at
            last_cleanup_at = self._last_cleanup_at
        return {
            "enabled": True,
            "alive": alive,
            "healthy": alive and consecutive_errors == 0,
            "consecutive_claim_errors": consecutive_errors,
            "last_error_code": last_error_code,
            "last_successful_poll_at": (
                last_successful_poll_at.isoformat()
                if last_successful_poll_at is not None
                else None
            ),
            "last_cleanup_at": (
                last_cleanup_at.isoformat()
                if last_cleanup_at is not None
                else None
            ),
        }

    def _record_claim_error(self, error: Exception) -> None:
        error_code = error.__class__.__name__.lower()[:80]
        with self._health_lock:
            self._consecutive_claim_errors += 1
            self._last_error_code = error_code
        logger.warning(
            "La cola local no pudo reclamar un trabajo; se reintentará (%s).",
            error_code,
        )

    def _record_successful_poll(self) -> None:
        with self._health_lock:
            self._consecutive_claim_errors = 0
            self._last_error_code = None
            self._last_successful_poll_at = utcnow()

    def _track_claim(self, claimed: ClaimedJob) -> None:
        with self._lease_lock:
            self._active_leases[claimed.id] = claimed.lease_token

    def _untrack_claim(self, claimed: ClaimedJob) -> None:
        with self._lease_lock:
            if self._active_leases.get(claimed.id) == claimed.lease_token:
                self._active_leases.pop(claimed.id, None)

    def _release_active_leases(self) -> int:
        with self._lease_lock:
            active_leases = tuple(self._active_leases.items())
        if not active_leases:
            return 0

        now = utcnow()
        released_keys: list[tuple[str, str]] = []
        db: Session = SessionLocal()
        try:
            for job_id, lease_token in active_leases:
                released = db.query(BackgroundJob).filter(
                    BackgroundJob.id == job_id,
                    BackgroundJob.status == "running",
                    BackgroundJob.lease_token == lease_token,
                ).update(
                    {
                        BackgroundJob.status: "pending",
                        BackgroundJob.attempts: BackgroundJob.attempts - 1,
                        BackgroundJob.available_at: now,
                        BackgroundJob.lease_token: None,
                        BackgroundJob.lease_expires_at: None,
                        BackgroundJob.updated_at: now,
                    },
                    synchronize_session=False,
                )
                if released == 1:
                    released_keys.append((job_id, lease_token))
            db.commit()
        except Exception as error:
            db.rollback()
            logger.warning(
                "No se pudieron liberar los trabajos durante el apagado (%s).",
                error.__class__.__name__.lower()[:80],
            )
            return 0
        finally:
            db.close()

        with self._lease_lock:
            for job_id, lease_token in released_keys:
                if self._active_leases.get(job_id) == lease_token:
                    self._active_leases.pop(job_id, None)
        if released_keys:
            logger.info(
                "Se devolvieron %d trabajos locales a la cola durante el apagado.",
                len(released_keys),
            )
        return len(released_keys)

    def _run(self) -> None:
        backoff = self.claim_error_backoff_seconds
        while not self._stop.is_set():
            self._run_cleanup_if_due()
            try:
                claimed = self._claim_next()
            except Exception as error:
                self._record_claim_error(error)
                if self._stop.wait(backoff):
                    break
                backoff = min(
                    backoff * 2,
                    self.claim_error_max_backoff_seconds,
                )
                continue

            self._record_successful_poll()
            backoff = self.claim_error_backoff_seconds
            if claimed is None:
                self._wake.wait(self.poll_seconds)
                self._wake.clear()
                continue
            self._execute(claimed)

    def _run_cleanup_if_due(self) -> None:
        now_monotonic = time.monotonic()
        if now_monotonic < self._next_cleanup_at:
            return
        self._next_cleanup_at = now_monotonic + self.cleanup_interval_seconds

        try:
            from ai.chat_sessions import purge_expired_chat_sessions

            removed_jobs = self._purge_terminal_jobs()
            removed_sessions = purge_expired_chat_sessions(
                SessionLocal,
                batch_size=self.cleanup_batch_size,
            )
        except Exception as error:
            logger.warning(
                "No se pudo completar la limpieza local; se reintentará (%s).",
                error.__class__.__name__.lower()[:80],
            )
            return

        with self._health_lock:
            self._last_cleanup_at = utcnow()
        if removed_jobs or removed_sessions:
            logger.info(
                "Limpieza local completada (trabajos=%d, sesiones=%d).",
                removed_jobs,
                removed_sessions,
            )

    def _purge_terminal_jobs(
        self,
        *,
        retention_seconds: int | None = None,
        batch_size: int | None = None,
    ) -> int:
        retention = max(
            1,
            int(
                self.terminal_retention_seconds
                if retention_seconds is None
                else retention_seconds
            ),
        )
        limit = max(
            1,
            int(self.cleanup_batch_size if batch_size is None else batch_size),
        )
        cutoff = utcnow() - timedelta(seconds=retention)
        db: Session = SessionLocal()
        try:
            expired_ids = [
                job_id
                for (job_id,) in db.query(BackgroundJob.id).filter(
                    BackgroundJob.status.in_(("completed", "failed")),
                    or_(
                        BackgroundJob.completed_at <= cutoff,
                        and_(
                            BackgroundJob.completed_at.is_(None),
                            BackgroundJob.updated_at <= cutoff,
                        ),
                    ),
                ).order_by(
                    BackgroundJob.completed_at.asc(),
                    BackgroundJob.updated_at.asc(),
                ).limit(limit).all()
            ]
            if not expired_ids:
                return 0
            removed = db.query(BackgroundJob).filter(
                BackgroundJob.id.in_(expired_ids)
            ).delete(synchronize_session=False)
            db.commit()
            return int(removed)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _claim_next(self) -> ClaimedJob | None:
        for _ in range(5):
            now = utcnow()
            db: Session = SessionLocal()
            try:
                # An exhausted worker that died during its final attempt must not
                # remain in `running` forever.
                db.query(BackgroundJob).filter(
                    BackgroundJob.status == "running",
                    BackgroundJob.lease_expires_at <= now,
                    BackgroundJob.attempts >= BackgroundJob.max_attempts,
                ).update(
                    {
                        BackgroundJob.status: "failed",
                        BackgroundJob.payload_json: None,
                        BackgroundJob.lease_token: None,
                        BackgroundJob.lease_expires_at: None,
                        BackgroundJob.last_error_code: "lease_expired",
                        BackgroundJob.updated_at: now,
                        BackgroundJob.completed_at: now,
                    },
                    synchronize_session=False,
                )
                candidate = db.query(BackgroundJob.id).filter(
                    BackgroundJob.kind == "emotion_analysis",
                    BackgroundJob.attempts < BackgroundJob.max_attempts,
                    or_(
                        and_(
                            BackgroundJob.status == "pending",
                            BackgroundJob.available_at <= now,
                        ),
                        and_(
                            BackgroundJob.status == "running",
                            BackgroundJob.lease_expires_at <= now,
                        ),
                    ),
                ).order_by(
                    BackgroundJob.available_at.asc(),
                    BackgroundJob.created_at.asc(),
                ).first()
                if candidate is None:
                    db.commit()
                    return None

                lease_token = str(uuid.uuid4())
                updated = db.query(BackgroundJob).filter(
                    BackgroundJob.id == candidate.id,
                    BackgroundJob.attempts < BackgroundJob.max_attempts,
                    or_(
                        and_(
                            BackgroundJob.status == "pending",
                            BackgroundJob.available_at <= now,
                        ),
                        and_(
                            BackgroundJob.status == "running",
                            BackgroundJob.lease_expires_at <= now,
                        ),
                    ),
                ).update(
                    {
                        BackgroundJob.status: "running",
                        BackgroundJob.attempts: BackgroundJob.attempts + 1,
                        BackgroundJob.lease_token: lease_token,
                        BackgroundJob.lease_expires_at: (
                            now + timedelta(seconds=self.lease_seconds)
                        ),
                        BackgroundJob.started_at: now,
                        BackgroundJob.updated_at: now,
                    },
                    synchronize_session=False,
                )
                if updated != 1:
                    db.rollback()
                    continue
                db.commit()
                job = db.query(BackgroundJob).filter(
                    BackgroundJob.id == candidate.id
                ).one()
                try:
                    payload = json.loads(job.payload_json or "{}")
                except (TypeError, ValueError, json.JSONDecodeError):
                    payload = {}
                claimed = ClaimedJob(
                    id=job.id,
                    lease_token=lease_token,
                    attempts=job.attempts,
                    max_attempts=job.max_attempts,
                    payload=payload,
                )
                self._track_claim(claimed)
                return claimed
            finally:
                db.close()
        return None

    def _execute(self, claimed: ClaimedJob) -> None:
        heartbeat_stop = threading.Event()
        heartbeat = threading.Thread(
            target=self._heartbeat,
            args=(claimed, heartbeat_stop),
            name=f"emovest-job-heartbeat-{claimed.id}",
            daemon=True,
        )
        heartbeat.start()
        try:
            operation_id = int(claimed.payload["operation_id"])
            text = str(claimed.payload["text"])
            db: Session = SessionLocal()
            try:
                process_emociones_job(
                    id_operacion=operation_id,
                    texto=text,
                    db=db,
                    commit=False,
                )
                now = utcnow()
                completed = db.query(BackgroundJob).filter(
                    BackgroundJob.id == claimed.id,
                    BackgroundJob.status == "running",
                    BackgroundJob.lease_token == claimed.lease_token,
                ).update(
                    {
                        BackgroundJob.status: "completed",
                        BackgroundJob.payload_json: None,
                        BackgroundJob.lease_token: None,
                        BackgroundJob.lease_expires_at: None,
                        BackgroundJob.last_error_code: None,
                        BackgroundJob.updated_at: now,
                        BackgroundJob.completed_at: now,
                    },
                    synchronize_session=False,
                )
                if completed != 1:
                    db.rollback()
                    return
                # Registro_emocional and the completed state become visible in
                # one commit. A crash cannot leave only one of those effects.
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        except Exception as error:
            self._record_failure(claimed, error)
        finally:
            heartbeat_stop.set()
            heartbeat.join(timeout=1)
            self._untrack_claim(claimed)

    def _heartbeat(
        self, claimed: ClaimedJob, heartbeat_stop: threading.Event
    ) -> None:
        interval = max(1, self.lease_seconds // 3)
        while not heartbeat_stop.wait(interval):
            db: Session = SessionLocal()
            try:
                now = utcnow()
                updated = db.query(BackgroundJob).filter(
                    BackgroundJob.id == claimed.id,
                    BackgroundJob.status == "running",
                    BackgroundJob.lease_token == claimed.lease_token,
                ).update(
                    {
                        BackgroundJob.lease_expires_at: (
                            now + timedelta(seconds=self.lease_seconds)
                        ),
                        BackgroundJob.updated_at: now,
                    },
                    synchronize_session=False,
                )
                db.commit()
                if updated != 1:
                    return
            except Exception:
                db.rollback()
                logger.warning("No se pudo renovar el lease de un trabajo local.")
            finally:
                db.close()

    def _record_failure(self, claimed: ClaimedJob, error: Exception) -> None:
        retryable = not isinstance(error, AIProviderError) or error.retryable
        should_retry = retryable and claimed.attempts < claimed.max_attempts
        intervals = _retry_intervals()
        delay = intervals[min(max(claimed.attempts - 1, 0), len(intervals) - 1)]
        now = utcnow()
        error_code = (
            error.code if isinstance(error, AIProviderError)
            else error.__class__.__name__.lower()[:80]
        )
        db: Session = SessionLocal()
        try:
            values = {
                BackgroundJob.status: "pending" if should_retry else "failed",
                BackgroundJob.available_at: now + timedelta(seconds=delay),
                BackgroundJob.lease_token: None,
                BackgroundJob.lease_expires_at: None,
                BackgroundJob.last_error_code: error_code[:80],
                BackgroundJob.updated_at: now,
            }
            if not should_retry:
                values[BackgroundJob.completed_at] = now
                values[BackgroundJob.payload_json] = None
            db.query(BackgroundJob).filter(
                BackgroundJob.id == claimed.id,
                BackgroundJob.status == "running",
                BackgroundJob.lease_token == claimed.lease_token,
            ).update(values, synchronize_session=False)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("No se pudo actualizar el estado de un trabajo local.")
        finally:
            db.close()


_runner = LocalQueueRunner()


def start_background_services() -> None:
    if is_desktop_mode():
        _runner.start()


def stop_background_services(timeout: float | None = None) -> bool:
    if not is_desktop_mode():
        return True
    return _runner.stop(timeout)


def wake_background_services() -> None:
    if is_desktop_mode():
        _runner.wake()


def get_background_services_health() -> dict[str, Any]:
    if not is_desktop_mode():
        return {
            "enabled": False,
            "alive": False,
            "healthy": True,
            "consecutive_claim_errors": 0,
            "last_error_code": None,
            "last_successful_poll_at": None,
            "last_cleanup_at": None,
        }
    return _runner.health_snapshot()


def get_queue_snapshot(limit: int = 25) -> dict[str, Any]:
    """Return diagnostic metadata without exposing private job payloads."""
    safe_limit = min(max(int(limit), 1), 100)
    db: Session = SessionLocal()
    try:
        counts = {
            status: db.query(BackgroundJob).filter(
                BackgroundJob.status == status
            ).count()
            for status in ("pending", "running", "completed", "failed")
        }
        jobs = db.query(BackgroundJob).order_by(
            BackgroundJob.updated_at.desc()
        ).limit(safe_limit).all()
        return {
            "counts": counts,
            "jobs": [
                {
                    "id": job.id,
                    "kind": job.kind,
                    "operation_id": job.operation_id,
                    "status": job.status,
                    "attempts": job.attempts,
                    "max_attempts": job.max_attempts,
                    "available_at": job.available_at,
                    "updated_at": job.updated_at,
                    "last_error_code": job.last_error_code,
                }
                for job in jobs
            ],
        }
    finally:
        db.close()
