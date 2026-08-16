from __future__ import annotations

import os
import re
import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine

from config import BACKUP_DIR, DATABASE_PATH, SQLITE_BACKUP_RETENTION
from database import Base, create_desktop_engine, engine
import models  # noqa: F401


CORE_REVISION = "0001_desktop_core"
RUNTIME_REVISION = "0005_ai_provider_profiles"
CORE_TABLES = {
    "ai_settings",
    "alerta",
    "cuenta_trading",
    "estadistica",
    "notificacion",
    "operacion",
    "registro_emocional",
    "suscripcion",
    "trofeos",
    "usuario_trofeo",
    "usuarios",
}
RUNTIME_TABLES = {"background_jobs", "chat_sessions"}
_MIGRATION_LOCK = threading.Lock()
_SAFE_LABEL = re.compile(r"[^a-zA-Z0-9_-]+")


class MigrationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "migration_failed",
        recoverable: bool = True,
        backup_path: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.recoverable = recoverable
        self.backup_path = backup_path

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "recoverable": self.recoverable,
            "backup_path": str(self.backup_path) if self.backup_path else None,
        }


@dataclass(frozen=True)
class MigrationResult:
    revision: str
    backup_path: Path | None = None
    restored_from: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {
            key: str(value) if isinstance(value, Path) else value
            for key, value in payload.items()
        }


def _alembic_config(connection: Connection | None = None) -> Config:
    config_path = Path(__file__).resolve().parent / "alembic.ini"
    config = Config(str(config_path))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def get_head_revision() -> str:
    head = ScriptDirectory.from_config(_alembic_config()).get_current_head()
    if head is None:
        raise MigrationError(
            "El paquete no contiene una revisión de base de datos válida.",
            code="migration_bundle_invalid",
            recoverable=False,
        )
    return head


def get_current_revision(database_engine: Engine = engine) -> str | None:
    with database_engine.connect() as connection:
        if "alembic_version" not in inspect(connection).get_table_names():
            return None
        return connection.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        ).scalar_one_or_none()


def _database_has_user_tables(database_engine: Engine) -> bool:
    with database_engine.connect() as connection:
        return bool(
            set(inspect(connection).get_table_names()) - {"alembic_version"}
        )


def _validate_schema_columns(
    connection: Connection,
    table_names: set[str],
) -> None:
    inspector = inspect(connection)
    for table_name in table_names:
        expected = set(Base.metadata.tables[table_name].columns.keys())
        actual = {column["name"] for column in inspector.get_columns(table_name)}
        if actual != expected:
            raise MigrationError(
                f"La tabla local '{table_name}' no coincide con el esquema esperado.",
                code="schema_incompatible",
            )


def _stamp_unversioned_schema(database_engine: Engine) -> None:
    with database_engine.connect() as connection:
        table_names = set(inspect(connection).get_table_names())

    if not table_names or "alembic_version" in table_names:
        return

    if table_names == CORE_TABLES:
        target_revision = CORE_REVISION
        expected_tables = CORE_TABLES
    elif table_names == CORE_TABLES | RUNTIME_TABLES:
        target_revision = RUNTIME_REVISION
        expected_tables = CORE_TABLES | RUNTIME_TABLES
    else:
        raise MigrationError(
            "La base de datos local existente está incompleta o pertenece a "
            "una versión no reconocida.",
            code="schema_incompatible",
        )

    with database_engine.begin() as connection:
        _validate_schema_columns(connection, expected_tables)
        command.stamp(_alembic_config(connection), target_revision)


def _upgrade_to_head(database_engine: Engine) -> None:
    with database_engine.begin() as connection:
        command.upgrade(_alembic_config(connection), "head")


def _sqlite_sidecars(database_path: Path) -> tuple[Path, Path]:
    return (
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
    )


def _remove_temporary_database(database_path: Path) -> None:
    database_path.unlink(missing_ok=True)
    for sidecar in _sqlite_sidecars(database_path):
        sidecar.unlink(missing_ok=True)


def _prepare_fresh_database_atomically(
    database_path: Path,
    database_engine: Engine,
    head_revision: str,
) -> None:
    temporary_path = database_path.with_name(
        f".{database_path.name}.{uuid4().hex}.migrating"
    )
    temporary_engine = create_desktop_engine(temporary_path)
    try:
        _upgrade_to_head(temporary_engine)
        if get_current_revision(temporary_engine) != head_revision:
            raise MigrationError(
                "La base de datos nueva no alcanzó la revisión incluida."
            )
        with temporary_engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
        temporary_engine.dispose()
        _check_sqlite_integrity(temporary_path)

        # El artefacto original se confirmó vacío antes de entrar aquí. Cerrar
        # todas sus conexiones permite a Windows reemplazarlo sin dejar un WAL
        # antiguo asociado al nuevo archivo.
        database_engine.dispose()
        for sidecar in _sqlite_sidecars(database_path):
            sidecar.unlink(missing_ok=True)
        os.replace(temporary_path, database_path)
    except Exception as error:
        temporary_engine.dispose()
        _remove_temporary_database(temporary_path)
        if isinstance(error, MigrationError):
            raise
        raise MigrationError(
            "No se pudo crear la base de datos local inicial. "
            "El siguiente arranque puede reintentarlo de forma segura.",
            code="initial_migration_failed",
        ) from error
    finally:
        temporary_engine.dispose()
        _remove_temporary_database(temporary_path)


def _check_sqlite_integrity(database_path: Path) -> None:
    connection = None
    try:
        connection = sqlite3.connect(database_path)
        result = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error as error:
        raise MigrationError(
            "No se pudo comprobar la integridad de la base de datos local.",
            code="database_unreadable",
        ) from error
    finally:
        if connection is not None:
            connection.close()
    if not result or result[0] != "ok":
        raise MigrationError(
            "La comprobación de integridad de la base de datos local ha fallado.",
            code="database_corrupt",
        )


def _backup_path(label: str) -> Path:
    safe_label = _SAFE_LABEL.sub("-", label.strip()).strip("-_") or "manual"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return BACKUP_DIR / f"{safe_label}-{timestamp}.sqlite3"


def _create_consistent_backup(source_path: Path, label: str) -> Path:
    if not source_path.exists():
        raise MigrationError(
            "Todavía no existe una base de datos local que copiar.",
            code="database_missing",
        )

    destination_path = _backup_path(label)
    source = None
    destination = None
    try:
        source = sqlite3.connect(source_path)
        destination = sqlite3.connect(destination_path)
        source.backup(destination)
        destination.commit()
    except sqlite3.Error as error:
        destination_path.unlink(missing_ok=True)
        raise MigrationError(
            "No se pudo crear una copia de seguridad consistente.",
            code="backup_failed",
        ) from error
    finally:
        if destination is not None:
            destination.close()
        if source is not None:
            source.close()

    try:
        _check_sqlite_integrity(destination_path)
    except MigrationError:
        destination_path.unlink(missing_ok=True)
        raise
    return destination_path


def create_manual_backup(label: str) -> Path:
    with _MIGRATION_LOCK:
        return _create_consistent_backup(DATABASE_PATH, f"manual-{label}")


def _prune_migration_backups() -> None:
    backups = sorted(
        BACKUP_DIR.glob("pre-migration-*.sqlite3"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for stale_backup in backups[SQLITE_BACKUP_RETENTION:]:
        stale_backup.unlink(missing_ok=True)


def _restore_backup(
    backup_path: Path,
    database_path: Path,
    database_engine: Engine,
) -> None:
    database_engine.dispose()
    source = None
    destination = None
    try:
        _remove_temporary_database(database_path)
        source = sqlite3.connect(backup_path)
        destination = sqlite3.connect(database_path)
        source.backup(destination)
        destination.commit()
        destination.close()
        destination = None
        source.close()
        source = None
        _check_sqlite_integrity(database_path)
    except (sqlite3.Error, MigrationError) as error:
        raise MigrationError(
            "La migración falló y tampoco se pudo restaurar la copia automática.",
            code="restore_failed",
            recoverable=False,
            backup_path=backup_path,
        ) from error
    finally:
        if destination is not None:
            destination.close()
        if source is not None:
            source.close()


def initialize_database(
    database_engine: Engine = engine,
    *,
    database_path: Path = DATABASE_PATH,
) -> MigrationResult:
    database_path = Path(database_path).resolve()
    with _MIGRATION_LOCK:
        head_revision = get_head_revision()
        current_revision = get_current_revision(database_engine)
        if current_revision == head_revision:
            return MigrationResult(revision=head_revision)

        has_existing_data = _database_has_user_tables(database_engine)
        if not has_existing_data:
            _prepare_fresh_database_atomically(
                database_path,
                database_engine,
                head_revision,
            )
            resulting_revision = get_current_revision(database_engine)
            if resulting_revision != head_revision:
                raise MigrationError(
                    "La base de datos nueva no está lista después del reemplazo.",
                    code="initial_migration_failed",
                )
            return MigrationResult(revision=head_revision)

        backup_path = (
            _create_consistent_backup(database_path, "pre-migration")
            if has_existing_data
            else None
        )

        try:
            _stamp_unversioned_schema(database_engine)
            _upgrade_to_head(database_engine)
            resulting_revision = get_current_revision(database_engine)
            if resulting_revision != head_revision:
                raise MigrationError(
                    "La base de datos no alcanzó la revisión incluida en la aplicación."
                )
            _check_sqlite_integrity(database_path)
        except Exception as error:
            if backup_path is not None:
                _restore_backup(backup_path, database_path, database_engine)
            if isinstance(error, MigrationError):
                raise MigrationError(
                    str(error),
                    code=error.code,
                    recoverable=error.recoverable,
                    backup_path=backup_path or error.backup_path,
                ) from error
            raise MigrationError(
                "No se pudo actualizar la base de datos local. "
                "Se ha conservado la copia previa.",
                backup_path=backup_path,
            ) from error

        if backup_path is not None:
            _prune_migration_backups()
        return MigrationResult(
            revision=head_revision,
            backup_path=backup_path,
        )


def prepare_database() -> str:
    return initialize_database().revision


def is_revision_at_least(current: str | None, minimum: str) -> bool:
    if current is None:
        return False
    try:
        revisions = ScriptDirectory.from_config(_alembic_config())
        if revisions.get_revision(current) is None or revisions.get_revision(minimum) is None:
            return False
        ancestors = {
            revision.revision
            for revision in revisions.iterate_revisions(current, "base")
        }
    except Exception:
        return False
    return minimum in ancestors


def create_isolated_engine(database_path: Path) -> Engine:
    """Test/support hook that keeps the production engine singleton untouched."""
    return create_desktop_engine(database_path)
