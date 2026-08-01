from __future__ import annotations

import re
from pathlib import Path

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from backup_manager import (
    create_database_backup,
    create_manual_backup_archive,
    current_schema_revision,
    prune_database_backups,
)
from config import APP_DATA_DIR, APP_LOG_DIR, BACKUP_DIR, SQLITE_BACKUP_RETENTION
from database import get_db
from migration_manager import get_head_revision
from queueing.lifecycle import get_background_services_health, get_queue_snapshot


router = APIRouter(prefix="/desktop", tags=["desktop"])
_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


class UpdatePreparation(BaseModel):
    target_version: str = Field(min_length=5, max_length=64)
    target_schema_revision: str = Field(min_length=1, max_length=128)
    minimum_schema_revision: str = Field(min_length=1, max_length=128)


def _app_version(request: Request) -> str:
    return request.app.version


def _alembic_script() -> ScriptDirectory:
    backend_dir = Path(__file__).resolve().parents[1]
    configuration = AlembicConfig(str(backend_dir / "alembic.ini"))
    configuration.set_main_option("script_location", str(backend_dir / "migrations"))
    return ScriptDirectory.from_config(configuration)


def _revision_is_at_least(current: str, minimum: str) -> bool:
    try:
        ancestors = {
            revision.revision
            for revision in _alembic_script().iterate_revisions(current, "base")
        }
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El manifiesto de actualización usa una revisión desconocida.",
        ) from error
    return minimum in ancestors


@router.get("/diagnostics")
def desktop_diagnostics(request: Request, db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    queue = get_queue_snapshot(limit=1)
    queue_health = get_background_services_health()
    schema_revision = current_schema_revision()
    return {
        "healthy": (
            queue_health["healthy"]
            and schema_revision == get_head_revision()
        ),
        "app_version": _app_version(request),
        "schema_revision": schema_revision,
        "data_dir": str(APP_DATA_DIR),
        "log_dir": str(APP_LOG_DIR),
        "backup_dir": str(BACKUP_DIR),
        "jobs": queue["counts"],
        "queue_health": queue_health,
    }


@router.post("/backup", status_code=status.HTTP_201_CREATED)
def create_backup(request: Request):
    try:
        archive = create_manual_backup_archive(_app_version(request))
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear la copia de seguridad local.",
        ) from error
    return {"created": True, "backup_path": str(archive)}


@router.post("/update/prepare")
def prepare_update(payload: UpdatePreparation):
    if not _SEMVER.fullmatch(payload.target_version):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La versión de actualización no es SemVer válida.",
        )

    current = current_schema_revision()
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo determinar la revisión del esquema local.",
        )
    if not _revision_is_at_least(current, payload.minimum_schema_revision):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La actualización no es compatible con el esquema local.",
        )

    try:
        backup = create_database_backup(f"pre-update-{payload.target_version}")
        prune_database_backups("pre-update", SQLITE_BACKUP_RETENTION)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo proteger la base de datos antes de actualizar.",
        ) from error

    return {
        "ready": True,
        "schema_revision": current,
        "target_schema_revision": payload.target_schema_revision,
        "backup_path": str(backup),
    }


@router.post("/shutdown", status_code=status.HTTP_202_ACCEPTED)
async def shutdown(request: Request):
    shutdown_event = getattr(request.app.state, "shutdown_requested", None)
    if shutdown_event is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El apagado ordenado no está disponible.",
        )
    shutdown_event.set()
    return {"accepted": True}
