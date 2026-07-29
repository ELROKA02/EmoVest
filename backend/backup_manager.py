from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from config import BACKUP_DIR, DATABASE_PATH, IMAGE_STORAGE_PATH


_SAFE_LABEL = re.compile(r"[^a-z0-9-]+")
_BACKUP_LOCK = threading.RLock()
_LOGGER = logging.getLogger(__name__)


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _safe_label(label: str) -> str:
    sanitized = _SAFE_LABEL.sub("-", label.strip().lower()).strip("-")
    return sanitized[:40] or "backup"


def create_database_backup(label: str) -> Path:
    """Crea una copia consistente incluso cuando SQLite trabaja en WAL."""

    with _BACKUP_LOCK:
        if not DATABASE_PATH.exists():
            raise RuntimeError("La base de datos local todavía no existe.")

        destination = BACKUP_DIR / f"{_safe_label(label)}-{_timestamp()}.sqlite3"
        source_connection = sqlite3.connect(str(DATABASE_PATH))
        destination_connection = sqlite3.connect(str(destination))
        try:
            source_connection.backup(destination_connection)
            integrity = destination_connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise RuntimeError("La copia de seguridad no superó la validación de integridad.")
        except Exception:
            destination_connection.close()
            source_connection.close()
            destination.unlink(missing_ok=True)
            raise
        else:
            destination_connection.close()
            source_connection.close()
        return destination


def prune_database_backups(prefix: str, retention: int) -> None:
    """Limita copias automáticas de una familia sin tocar exports manuales."""

    safe_prefix = _safe_label(prefix)
    if retention < 1:
        raise ValueError("La retención debe conservar al menos una copia.")
    with _BACKUP_LOCK:
        candidates = sorted(
            BACKUP_DIR.glob(f"{safe_prefix}-*.sqlite3"),
            key=lambda path: path.name,
            reverse=True,
        )
        for stale_backup in candidates[retention:]:
            try:
                stale_backup.unlink(missing_ok=True)
            except OSError:
                _LOGGER.warning(
                    "No se pudo eliminar una copia automática antigua.",
                )


def current_schema_revision() -> str | None:
    if not DATABASE_PATH.exists():
        return None
    connection = sqlite3.connect(str(DATABASE_PATH))
    try:
        row = connection.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
    except sqlite3.Error:
        return None
    finally:
        connection.close()
    return str(row[0]) if row else None


def create_manual_backup_archive(app_version: str) -> Path:
    """Exporta DB e imágenes sin incluir logs ni secretos de configuración."""

    with _BACKUP_LOCK:
        database_backup = create_database_backup("manual-database")
        archive = BACKUP_DIR / f"EmoVest-backup-{_timestamp()}.zip"
        temporary_archive = archive.with_suffix(".zip.tmp")
        manifest = {
            "format": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "app_version": app_version,
            "schema_revision": current_schema_revision(),
            "includes": ["database", "images"],
        }

        try:
            with zipfile.ZipFile(
                temporary_archive,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
            ) as bundle:
                bundle.writestr(
                    "manifest.json",
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                )
                bundle.write(database_backup, "data/emovest.sqlite3")
                if IMAGE_STORAGE_PATH.exists():
                    image_root = IMAGE_STORAGE_PATH.resolve()
                    for image_path in sorted(IMAGE_STORAGE_PATH.rglob("*")):
                        if image_path.is_symlink() or not image_path.is_file():
                            continue
                        resolved_image = image_path.resolve()
                        if not resolved_image.is_relative_to(image_root):
                            continue
                        relative_path = resolved_image.relative_to(image_root)
                        archive_path = (Path("images") / relative_path).as_posix()
                        bundle.write(resolved_image, archive_path)
            os.replace(temporary_archive, archive)
        except Exception:
            temporary_archive.unlink(missing_ok=True)
            raise
        finally:
            database_backup.unlink(missing_ok=True)

        return archive
