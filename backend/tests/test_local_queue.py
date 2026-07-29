import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from ai.emotions import Emociones
from ai.providers.base import AIModelMissing, AIServiceUnavailable
from database import Base, create_desktop_engine
from models import (
    BackgroundJob,
    Cuenta_Trading,
    Operacion,
    Registro_emocional,
    Usuario,
)
from queueing.runner import LocalQueueRunner
from queueing.sqlite_adapter import SqliteEmotionQueue


class LocalQueueTests(unittest.TestCase):
    @staticmethod
    def _now():
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "queue.sqlite3"
        self.engine = create_desktop_engine(database_path)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        db = self.Session()
        db.add(Usuario(
            id=1,
            nombre="Desktop",
            contrasena="not-a-real-password",
            correo_electronico="queue@example.test",
        ))
        db.add(Cuenta_Trading(
            id=1,
            id_usuario=1,
            nombre_cuenta="Local",
            saldo_inicial=Decimal("1000"),
            saldo_actual=Decimal("1000"),
            divisa="EUR",
        ))
        db.add(Operacion(
            id=1,
            id_cuenta=1,
            fecha_hora=self._now(),
            tipo_operacion="LONG",
            cantidad=Decimal("1"),
            activo="EURUSD",
            precio_entrada=Decimal("1.1"),
            notas="Tengo dudas",
        ))
        db.commit()
        db.close()
        self.queue = SqliteEmotionQueue()

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _stage(self):
        db = self.Session()
        receipt = self.queue.stage(db, 1, "Tengo dudas")
        db.commit()
        db.close()
        return receipt

    def _runner(self):
        runner = LocalQueueRunner()
        runner.lease_seconds = 30
        return runner

    def test_enqueue_is_persistent_and_idempotent(self):
        first = self._stage()
        second = self._stage()

        db = self.Session()
        jobs = db.query(BackgroundJob).all()
        db.close()
        self.assertEqual(first.id, second.id)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].status, "pending")

    def test_queue_failure_does_not_poison_operation_transaction(self):
        BackgroundJob.__table__.drop(self.engine)
        db = self.Session()
        operation = db.get(Operacion, 1)
        operation.notas = "La operación debe sobrevivir"

        with self.assertRaises(SQLAlchemyError):
            self.queue.stage(db, 1, operation.notas)
        db.commit()
        db.close()

        db = self.Session()
        self.assertEqual(
            db.get(Operacion, 1).notas,
            "La operación debe sobrevivir",
        )
        db.close()

    def test_expired_lease_is_recovered_and_stale_worker_cannot_commit(self):
        self._stage()
        with patch("queueing.runner.SessionLocal", self.Session):
            first_runner = self._runner()
            first_claim = first_runner._claim_next()
            db = self.Session()
            db.query(BackgroundJob).filter(
                BackgroundJob.id == first_claim.id
            ).update({
                BackgroundJob.lease_expires_at: (
                    self._now() - timedelta(seconds=1)
                )
            })
            db.commit()
            db.close()
            second_claim = self._runner()._claim_next()

            def successful_job(*, id_operacion, texto, db, commit):
                db.add(Registro_emocional(
                    id_operacion=id_operacion,
                    fecha_hora=self._now(),
                    texto_entrada=texto,
                    confianza=Decimal("0.20"),
                    duda=Decimal("0.20"),
                    euforia=Decimal("0.20"),
                    miedo=Decimal("0.20"),
                    neutral=Decimal("0.20"),
                ))

            with patch(
                "queueing.runner.process_emociones_job",
                side_effect=successful_job,
            ):
                first_runner._execute(first_claim)
                db = self.Session()
                self.assertEqual(db.query(Registro_emocional).count(), 0)
                db.close()
                first_runner._execute(second_claim)

        db = self.Session()
        job = db.get(BackgroundJob, second_claim.id)
        self.assertEqual(job.status, "completed")
        self.assertIsNone(job.payload_json)
        self.assertEqual(db.query(Registro_emocional).count(), 1)
        db.close()

    def test_transient_failure_retries_then_becomes_failed(self):
        receipt = self._stage()
        db = self.Session()
        job = db.get(BackgroundJob, receipt.id)
        job.max_attempts = 2
        db.commit()
        db.close()

        with (
            patch("queueing.runner.SessionLocal", self.Session),
            patch(
                "queueing.runner.process_emociones_job",
                side_effect=AIServiceUnavailable("offline"),
            ),
        ):
            runner = self._runner()
            first = runner._claim_next()
            runner._execute(first)
            db = self.Session()
            job = db.get(BackgroundJob, receipt.id)
            self.assertEqual(job.status, "pending")
            job.available_at = self._now() - timedelta(seconds=1)
            db.commit()
            db.close()

            second = runner._claim_next()
            runner._execute(second)

        db = self.Session()
        job = db.get(BackgroundJob, receipt.id)
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.attempts, 2)
        self.assertEqual(job.last_error_code, "service_unavailable")
        self.assertEqual(db.query(Operacion).count(), 1)
        self.assertEqual(db.query(Registro_emocional).count(), 0)
        db.close()

    def test_missing_model_fails_without_retry_and_preserves_operation(self):
        receipt = self._stage()
        with (
            patch("queueing.runner.SessionLocal", self.Session),
            patch(
                "queueing.runner.process_emociones_job",
                side_effect=AIModelMissing("missing"),
            ),
        ):
            runner = self._runner()
            claimed = runner._claim_next()
            runner._execute(claimed)

        db = self.Session()
        job = db.get(BackgroundJob, receipt.id)
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.attempts, 1)
        self.assertEqual(job.last_error_code, "model_missing")
        self.assertIsNone(job.payload_json)
        self.assertEqual(db.query(Operacion).count(), 1)
        self.assertEqual(db.query(Registro_emocional).count(), 0)
        db.close()

    def test_runner_recovers_from_claim_error_without_logging_private_details(self):
        runner = self._runner()
        runner.poll_seconds = 0.01
        runner.claim_error_backoff_seconds = 0.1
        runner.claim_error_max_backoff_seconds = 0.1
        runner._next_cleanup_at = float("inf")
        first_failure = threading.Event()
        recovered = threading.Event()
        calls = 0

        def claim():
            nonlocal calls
            calls += 1
            if calls == 1:
                first_failure.set()
                raise RuntimeError("nota privada que no debe aparecer")
            recovered.set()
            return None

        with (
            patch.object(runner, "_claim_next", side_effect=claim),
            self.assertLogs("queueing.runner", level="WARNING") as captured,
        ):
            runner.start()
            self.assertTrue(first_failure.wait(timeout=1))
            deadline = time.monotonic() + 1
            while (
                runner.health_snapshot()["consecutive_claim_errors"] == 0
                and time.monotonic() < deadline
            ):
                time.sleep(0.01)
            degraded = runner.health_snapshot()
            self.assertFalse(degraded["healthy"])
            self.assertEqual(degraded["last_error_code"], "runtimeerror")

            self.assertTrue(recovered.wait(timeout=1))
            deadline = time.monotonic() + 1
            while (
                runner.health_snapshot()["consecutive_claim_errors"] != 0
                and time.monotonic() < deadline
            ):
                time.sleep(0.01)
            healthy = runner.health_snapshot()
            self.assertTrue(healthy["alive"])
            self.assertTrue(healthy["healthy"])
            self.assertIsNotNone(healthy["last_successful_poll_at"])
            self.assertTrue(runner.stop(timeout=1))

        self.assertNotIn("nota privada", "\n".join(captured.output))

    def test_terminal_job_cleanup_is_bounded_and_preserves_active_jobs(self):
        old = self._now() - timedelta(days=40)
        recent = self._now() - timedelta(days=1)
        db = self.Session()
        db.add_all([
            BackgroundJob(
                id="old-completed",
                kind="emotion_analysis",
                idempotency_key="old-completed",
                payload_json=None,
                status="completed",
                attempts=1,
                max_attempts=4,
                available_at=old,
                created_at=old,
                updated_at=old,
                completed_at=old,
            ),
            BackgroundJob(
                id="old-failed",
                kind="emotion_analysis",
                idempotency_key="old-failed",
                payload_json=None,
                status="failed",
                attempts=4,
                max_attempts=4,
                available_at=old,
                created_at=old,
                updated_at=old,
                completed_at=old,
            ),
            BackgroundJob(
                id="recent-completed",
                kind="emotion_analysis",
                idempotency_key="recent-completed",
                payload_json=None,
                status="completed",
                attempts=1,
                max_attempts=4,
                available_at=recent,
                created_at=recent,
                updated_at=recent,
                completed_at=recent,
            ),
            BackgroundJob(
                id="old-pending",
                kind="emotion_analysis",
                idempotency_key="old-pending",
                payload_json='{"text":"se conserva mientras está pendiente"}',
                status="pending",
                attempts=0,
                max_attempts=4,
                available_at=old,
                created_at=old,
                updated_at=old,
            ),
        ])
        db.commit()
        db.close()

        with patch("queueing.runner.SessionLocal", self.Session):
            runner = self._runner()
            self.assertEqual(
                runner._purge_terminal_jobs(
                    retention_seconds=30 * 24 * 60 * 60,
                    batch_size=1,
                ),
                1,
            )

        db = self.Session()
        remaining_ids = {
            job_id for (job_id,) in db.query(BackgroundJob.id).all()
        }
        db.close()
        self.assertEqual(
            len({"old-completed", "old-failed"} & remaining_ids),
            1,
        )
        self.assertIn("recent-completed", remaining_ids)
        self.assertIn("old-pending", remaining_ids)

    def test_runner_starts_and_stops_cleanly_when_idle(self):
        with patch("queueing.runner.SessionLocal", self.Session):
            runner = self._runner()
            runner.start()
            self.assertTrue(runner.stop(timeout=2))

    def test_stop_timeout_requeues_own_lease_and_stale_worker_rolls_back(self):
        receipt = self._stage()
        entered_job = threading.Event()
        release_job = threading.Event()

        def blocked_success(*, id_operacion, texto, db, commit):
            entered_job.set()
            self.assertTrue(release_job.wait(timeout=2))
            db.add(Registro_emocional(
                id_operacion=id_operacion,
                fecha_hora=self._now(),
                texto_entrada=texto,
                confianza=Decimal("0.20"),
                duda=Decimal("0.20"),
                euforia=Decimal("0.20"),
                miedo=Decimal("0.20"),
                neutral=Decimal("0.20"),
            ))

        with (
            patch("queueing.runner.SessionLocal", self.Session),
            patch(
                "queueing.runner.process_emociones_job",
                side_effect=blocked_success,
            ),
        ):
            stale_runner = self._runner()
            stale_runner.poll_seconds = 0.01
            stale_runner.start()
            self.assertTrue(entered_job.wait(timeout=1))
            db = self.Session()
            stale_lease_token = db.get(BackgroundJob, receipt.id).lease_token
            db.close()
            self.assertIsNotNone(stale_lease_token)

            self.assertFalse(stale_runner.stop(timeout=0.01))
            db = self.Session()
            requeued = db.get(BackgroundJob, receipt.id)
            self.assertEqual(requeued.status, "pending")
            self.assertEqual(requeued.attempts, 0)
            self.assertIsNone(requeued.lease_token)
            self.assertIsNone(requeued.lease_expires_at)
            db.close()

            restarted_runner = self._runner()
            recovered_claim = restarted_runner._claim_next()
            self.assertIsNotNone(recovered_claim)
            self.assertNotEqual(
                recovered_claim.lease_token,
                stale_lease_token,
            )

            release_job.set()
            self.assertTrue(stale_runner.stop(timeout=2))

        db = self.Session()
        recovered_job = db.get(BackgroundJob, receipt.id)
        self.assertEqual(recovered_job.status, "running")
        self.assertEqual(recovered_job.lease_token, recovered_claim.lease_token)
        self.assertEqual(db.query(Registro_emocional).count(), 0)
        db.close()


if __name__ == "__main__":
    unittest.main()
