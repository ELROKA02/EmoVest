"""Provider-specific import workflows with mandatory preview and idempotent commit."""
from __future__ import annotations

import json
import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, UploadFile
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from metatrader_import import parse_mt5_report
from models import (
    Cuenta_Trading,
    Importacion,
    ImportacionFila,
    MovimientoCuenta,
    Operacion,
    OperacionEjecucion,
)
from routers.auth import get_current_user
from trading_operations import recalculate_operation


router = APIRouter(
    prefix="/cuentas/{cuenta_id_trading}/importaciones",
    tags=["importaciones"],
)


def _account(db: Session, account_id: int, user_id: int) -> Cuenta_Trading:
    account = db.query(Cuenta_Trading).filter(
        Cuenta_Trading.id == account_id,
        Cuenta_Trading.id_usuario == user_id,
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta de trading no encontrada")
    return account


def _duplicate_context(db: Session, account_id: int, report: dict) -> dict:
    existing_import = db.query(Importacion).filter(
        Importacion.id_cuenta == account_id,
        Importacion.proveedor == "METATRADER5",
        Importacion.fingerprint == report["fingerprint"],
    ).first()
    source_keys = [row["source_key"] for row in report["normalized_rows"]]
    duplicates = set()
    if source_keys:
        duplicates = {
            key for (key,) in db.query(ImportacionFila.source_key).filter(
                ImportacionFila.id_cuenta == account_id,
                ImportacionFila.source_key.in_(source_keys),
            ).all()
        }
    source_accounts = {
        value for (value,) in db.query(Importacion.cuenta_origen_hash).filter(
            Importacion.id_cuenta == account_id,
            Importacion.proveedor == "METATRADER5",
        ).distinct().all()
    }
    account_conflict = bool(source_accounts and report["account_hash"] not in source_accounts)
    return {
        "existing_import": existing_import,
        "duplicates": duplicates,
        "account_conflict": account_conflict,
    }


def _public_preview(report: dict, duplicate_context: dict) -> dict:
    preview = dict(report)
    duplicates = duplicate_context["duplicates"]
    preview["duplicate_rows"] = len(duplicates)
    preview["already_imported"] = duplicate_context["existing_import"] is not None
    if duplicate_context["account_conflict"]:
        preview["conflicts"] = [
            *preview["conflicts"],
            {"reason": "La cuenta de EmoVest ya está vinculada a otra cuenta MetaTrader"},
        ]
    consumed = {
        key
        for operation in report["proposed_operations"]
        for key in operation["source_rows"]
    } | {
        key
        for movement in report["movements"]
        for key in movement["source_rows"]
    }
    fresh_consumed = consumed - duplicates
    preview["ready_to_commit"] = bool(fresh_consumed) and not preview["errors"] and not preview["conflicts"]
    preview["summary"] = {
        "operations": len(report["proposed_operations"]),
        "movements": len(report["movements"]),
        "skipped_open": len(report["skipped_open"]),
        "duplicates": len(duplicates),
        "errors": len(preview["errors"]),
        "conflicts": len(preview["conflicts"]),
    }
    return preview


async def _read_report(
    file: UploadFile,
    timezone_name: str,
    resolution_json: str | None = None,
) -> tuple[bytes, dict]:
    raw = await file.read()
    resolutions = None
    if resolution_json:
        try:
            resolutions = json.loads(resolution_json)
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=422, detail="resolution_json no es JSON válido") from error
        if not isinstance(resolutions, list) or len(resolutions) > 1000:
            raise HTTPException(status_code=422, detail="resolution_json debe ser una lista de hasta 1000 grupos")
    report = parse_mt5_report(raw, timezone_name, resolutions=resolutions)
    resolution_contract = json.dumps(resolutions or [], sort_keys=True, separators=(",", ":"))
    report["preview_token"] = hashlib.sha256(
        f"{report['fingerprint']}|{timezone_name}|{resolution_contract}".encode()
    ).hexdigest()
    return raw, report


@router.post("/metatrader/preview")
async def preview_metatrader(
    cuenta_id_trading: Annotated[int, Path()],
    zona_horaria: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    resolution_json: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    account = _account(db, cuenta_id_trading, current_user.id)
    _, report = await _read_report(file, zona_horaria, resolution_json)
    return _public_preview(report, _duplicate_context(db, account.id, report))


def _row_record(import_record: Importacion, account_id: int, source: dict, classification: str) -> ImportacionFila:
    return ImportacionFila(
        importacion=import_record,
        id_cuenta=account_id,
        numero_fila=int(source["row"]),
        deal_ticket=source.get("deal"),
        source_key=source["source_key"],
        clasificacion=classification,
        normalized_json=json.dumps(source, ensure_ascii=False, separators=(",", ":")),
    )


@router.post("/metatrader/commit")
async def commit_metatrader(
    cuenta_id_trading: Annotated[int, Path()],
    zona_horaria: Annotated[str, Form()],
    expected_preview_token: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    resolution_json: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    account = _account(db, cuenta_id_trading, current_user.id)
    _, report = await _read_report(file, zona_horaria, resolution_json)
    if report["preview_token"] != expected_preview_token:
        raise HTTPException(
            status_code=409,
            detail="El archivo, la zona horaria o la resolución cambiaron después de la previsualización",
        )
    context = _duplicate_context(db, account.id, report)
    if context["existing_import"]:
        return {
            "created_operations": 0,
            "created_movements": 0,
            "already_imported": True,
            "import_id": context["existing_import"].id,
        }
    if context["account_conflict"]:
        raise HTTPException(status_code=409, detail="La cuenta de EmoVest ya está vinculada a otra cuenta MetaTrader")
    if report["errors"] or report["conflicts"]:
        raise HTTPException(
            status_code=422,
            detail={"message": "El informe contiene conflictos", "errors": report["errors"], "conflicts": report["conflicts"]},
        )

    duplicates = context["duplicates"]
    rows_by_key = {row["source_key"]: row for row in report["normalized_rows"]}
    imported = Importacion(
        id_cuenta=account.id,
        proveedor="METATRADER5",
        fingerprint=report["fingerprint"],
        cuenta_origen_hash=report["account_hash"],
        broker=report["broker"],
        zona_horaria=zona_horaria,
    )
    db.add(imported)
    created_operations = 0
    created_movements = 0
    balance_delta = Decimal("0")

    try:
        for proposal in report["proposed_operations"]:
            source_keys = set(proposal["source_rows"])
            if source_keys <= duplicates:
                continue
            if source_keys & duplicates:
                raise HTTPException(
                    status_code=409,
                    detail=f"La posición {proposal['position']} mezcla filas nuevas y ya importadas",
                )
            row_records = {
                key: _row_record(imported, account.id, rows_by_key[key], "TRADE")
                for key in source_keys
            }
            operation = Operacion(
                id_cuenta=account.id,
                fecha_hora=datetime.fromisoformat(proposal["fecha_hora"]),
                tipo_operacion=proposal["tipo_operacion"],
                cantidad=Decimal(proposal["cantidad"]),
                activo=proposal["activo"],
                precio_entrada=Decimal(proposal["precio_entrada"]),
                notas=f"MetaTrader 5 · Position {proposal['position']}",
            )
            for role, legs in (("ENTRY", proposal["entries"]), ("EXIT", proposal["exits"])):
                for leg in legs:
                    operation.ejecuciones.append(OperacionEjecucion(
                        source_row=row_records[leg["source_key"]],
                        source_leg=leg.get("source_leg"),
                        rol=role,
                        fecha_hora=datetime.fromisoformat(leg["fecha_hora"]),
                        cantidad=Decimal(leg["cantidad"]),
                        precio=Decimal(leg["precio"]) if leg.get("precio") not in (None, "") else None,
                        resultado_bruto=Decimal(leg.get("resultado_bruto", "0")) if role == "EXIT" else None,
                        impacto_comision=Decimal(leg.get("impacto_comision", "0")),
                        impacto_swap=Decimal(leg.get("impacto_swap", "0")),
                        impacto_tasa=Decimal(leg.get("impacto_tasa", "0")),
                        resultado_neto=Decimal(leg.get("resultado_neto", "0")),
                        origen="BROKER",
                    ))
            balance_delta += recalculate_operation(operation)
            db.add(operation)
            created_operations += 1

        for movement in report["movements"]:
            key = movement["source_rows"][0]
            if key in duplicates:
                continue
            row_record = _row_record(imported, account.id, rows_by_key[key], "MOVEMENT")
            amount = Decimal(movement["importe"])
            db.add(MovimientoCuenta(
                id_cuenta=account.id,
                source_row=row_record,
                fecha_hora=datetime.fromisoformat(movement["fecha_hora"]),
                tipo=movement["tipo"],
                importe=amount,
                descripcion=movement["descripcion"],
            ))
            balance_delta += amount
            created_movements += 1

        if created_operations == 0 and created_movements == 0:
            raise HTTPException(status_code=409, detail="El informe no contiene filas nuevas cerradas")
        if balance_delta:
            db.query(Cuenta_Trading).filter(Cuenta_Trading.id == account.id).update(
                {Cuenta_Trading.saldo_actual: func.coalesce(Cuenta_Trading.saldo_actual, 0) + balance_delta},
                synchronize_session=False,
            )
        db.commit()
        db.refresh(imported)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Alguna fila del informe ya fue importada") from error
    except SQLAlchemyError:
        db.rollback()
        raise

    return {
        "created_operations": created_operations,
        "created_movements": created_movements,
        "already_imported": False,
        "import_id": imported.id,
        "balance_delta": float(balance_delta),
        "skipped_open": len(report["skipped_open"]),
    }
