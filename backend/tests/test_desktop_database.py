import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from database import create_desktop_engine
from migration_manager import (
    CORE_REVISION,
    RUNTIME_REVISION,
    MigrationError,
    create_manual_backup,
    get_current_revision,
    initialize_database,
    is_revision_at_least,
)
from models import (
    BackgroundJob,
    ChatSessionRecord,
    Cuenta_Trading,
    Operacion,
    Usuario,
)


class DesktopDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "Datos con espacios ünicode"
        self.root.mkdir(parents=True)
        self.database_path = self.root / "emovest.sqlite3"
        self.backup_dir = self.root / "backups"
        self.backup_dir.mkdir()
        self.engine = create_desktop_engine(self.database_path)

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    def prepare(self):
        with patch("migration_manager.BACKUP_DIR", self.backup_dir):
            return initialize_database(
                self.engine,
                database_path=self.database_path,
            )

    def test_fresh_database_is_migrated_with_desktop_runtime_schema(self):
        result = self.prepare()

        self.assertEqual(result.revision, RUNTIME_REVISION)
        self.assertEqual(get_current_revision(self.engine), RUNTIME_REVISION)
        tables = set(inspect(self.engine).get_table_names())
        self.assertIn("background_jobs", tables)
        self.assertIn("chat_sessions", tables)
        self.assertIn("operacion", tables)
        user_columns = {
            column["name"] for column in inspect(self.engine).get_columns("usuarios")
        }
        self.assertTrue({"estrategia_trading", "plan_trading"}.issubset(user_columns))
        operation_columns = {
            column["name"] for column in inspect(self.engine).get_columns("operacion")
        }
        self.assertTrue({
            "saldo_referencia_riesgo",
            "riesgo_importe",
            "riesgo_porcentaje",
        }.issubset(operation_columns))
        self.assertTrue(is_revision_at_least(RUNTIME_REVISION, CORE_REVISION))

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.execute(text("PRAGMA foreign_keys")).scalar_one(),
                1,
            )
            self.assertEqual(
                connection.execute(text("PRAGMA journal_mode")).scalar_one().lower(),
                "wal",
            )
            self.assertEqual(
                connection.execute(text("PRAGMA busy_timeout")).scalar_one(),
                5000,
            )

    def test_decimal_enum_foreign_keys_and_runtime_defaults_round_trip(self):
        self.prepare()
        Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        with Session() as db:
            user = Usuario(
                nombre="Álex",
                correo_electronico="alex@example.test",
                contrasena="hash",
            )
            db.add(user)
            db.flush()
            account = Cuenta_Trading(
                id_usuario=user.id,
                nombre_cuenta="Principal",
                saldo_inicial=Decimal("1234.567891"),
                saldo_actual=Decimal("1234.567891"),
                divisa="EUR",
            )
            db.add(account)
            db.flush()
            operation = Operacion(
                id_cuenta=account.id,
                fecha_hora=now,
                tipo_operacion="LONG",
                cantidad=Decimal("1.123456"),
                activo="BTC",
                precio_entrada=Decimal("98765.432109"),
            )
            db.add(operation)
            db.flush()
            db.add(
                BackgroundJob(
                    id="11111111-1111-1111-1111-111111111111",
                    kind="emotion_analysis",
                    operation_id=operation.id,
                    idempotency_key=f"emotion:{operation.id}",
                    payload_json='{"text":"nota"}',
                    available_at=now,
                )
            )
            db.add(
                ChatSessionRecord(
                    id="22222222-2222-2222-2222-222222222222",
                    user_id=user.id,
                    account_id=account.id,
                    expires_at=now + timedelta(hours=8),
                )
            )
            db.commit()
            db.refresh(account)
            db.refresh(operation)

            self.assertEqual(account.saldo_inicial, Decimal("1234.567891"))
            self.assertEqual(operation.precio_entrada, Decimal("98765.432109"))
            job = db.get(
                BackgroundJob,
                "11111111-1111-1111-1111-111111111111",
            )
            chat = db.get(
                ChatSessionRecord,
                "22222222-2222-2222-2222-222222222222",
            )
            self.assertEqual(job.status, "pending")
            self.assertEqual(job.attempts, 0)
            self.assertEqual(chat.history_json, "[]")
            self.assertEqual(chat.version, 1)

        with Session() as db:
            db.add(
                Cuenta_Trading(
                    id_usuario=999999,
                    nombre_cuenta="Inválida",
                    divisa="EUR",
                )
            )
            with self.assertRaises(IntegrityError):
                db.commit()

    def test_manual_backup_is_a_consistent_snapshot(self):
        self.prepare()
        Session = sessionmaker(bind=self.engine)
        with Session() as db:
            db.add(
                Usuario(
                    nombre="Samuel",
                    correo_electronico="samuel@example.test",
                    contrasena="hash",
                )
            )
            db.commit()

        with (
            patch("migration_manager.BACKUP_DIR", self.backup_dir),
            patch("migration_manager.DATABASE_PATH", self.database_path),
        ):
            backup_path = create_manual_backup("antes-update")

        backup_engine = create_desktop_engine(backup_path)
        try:
            with backup_engine.connect() as connection:
                count = connection.execute(
                    text("SELECT count(*) FROM usuarios")
                ).scalar_one()
                integrity = connection.execute(
                    text("PRAGMA integrity_check")
                ).scalar_one()
            self.assertEqual(count, 1)
            self.assertEqual(integrity, "ok")
        finally:
            backup_engine.dispose()

    def test_failed_first_migration_leaves_retryable_empty_database(self):
        with (
            patch("migration_manager.BACKUP_DIR", self.backup_dir),
            patch(
                "migration_manager._upgrade_to_head",
                side_effect=RuntimeError("fallo inyectado"),
            ),
        ):
            with self.assertRaises(MigrationError) as raised:
                initialize_database(
                    self.engine,
                    database_path=self.database_path,
                )

        self.assertEqual(raised.exception.code, "initial_migration_failed")
        self.assertEqual(
            set(inspect(self.engine).get_table_names()),
            set(),
        )
        self.assertFalse(
            any(self.root.glob(".*.migrating*")),
            "No deben quedar bases temporales después de un fallo.",
        )

        result = self.prepare()
        self.assertEqual(result.revision, RUNTIME_REVISION)
        self.assertEqual(get_current_revision(self.engine), RUNTIME_REVISION)

    def test_failed_existing_migration_restores_valid_user_data(self):
        self.prepare()
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO usuarios "
                    "(nombre, correo_electronico, contrasena) "
                    "VALUES ('Ana', 'ana@example.test', 'hash')"
                )
            )
            connection.execute(
                text("UPDATE alembic_version SET version_num = :revision"),
                {"revision": CORE_REVISION},
            )

        with (
            patch("migration_manager.BACKUP_DIR", self.backup_dir),
            patch(
                "migration_manager._upgrade_to_head",
                side_effect=RuntimeError("fallo inyectado"),
            ),
        ):
            with self.assertRaises(MigrationError) as raised:
                initialize_database(
                    self.engine,
                    database_path=self.database_path,
                )

        self.assertIsNotNone(raised.exception.backup_path)
        with self.engine.connect() as connection:
            self.assertEqual(
                connection.execute(
                    text(
                        "SELECT correo_electronico FROM usuarios "
                        "WHERE correo_electronico = 'ana@example.test'"
                    )
                ).scalar_one(),
                "ana@example.test",
            )
            self.assertEqual(
                connection.execute(text("PRAGMA integrity_check")).scalar_one(),
                "ok",
            )
            self.assertEqual(
                connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one(),
                CORE_REVISION,
            )


if __name__ == "__main__":
    unittest.main()
