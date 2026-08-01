"""Herramientas de lectura para el chat.

Estas funciones son la frontera de datos: reciben un contexto creado por el
backend, no argumentos de identidad del LLM, y siempre filtran por propietario.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
import re
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from models import Cuenta_Trading, Operacion, Registro_emocional, Usuario


MAX_OPERATIONS = 20
MAX_PERIOD_DAYS = 365
EXTREME_EMOTION_THRESHOLD = Decimal("0.65")
_MAX_RISK_PATTERN = re.compile(
    r"(?:arriesgo|arriesgar|riesgo(?:\s+m[aá]ximo)?)\D{0,40}?(\d+(?:[.,]\d+)?)\s*%",
    re.IGNORECASE,
)


class ChatToolAccessError(ValueError):
    """Cuenta u operacion inexistente para el usuario autenticado."""


@dataclass(frozen=True)
class ChatExecutionContext:
    db: Session
    user_id: int
    account_id: int | None


def _number(value: Any) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def _timestamp(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _days(days: int | None) -> int:
    if days is None:
        return 30
    if not isinstance(days, int) or days < 1 or days > MAX_PERIOD_DAYS:
        raise ValueError(f"El periodo debe estar entre 1 y {MAX_PERIOD_DAYS} dias.")
    return days


def _emotion_alerts(
    averages: dict[str, float | int | None],
    peaks: dict[str, float | int | None],
) -> list[dict[str, Any]]:
    return [
        {
            "emotion": field,
            "average": averages[field],
            "peak": peaks[field],
            "message": f"{field.capitalize()} extrema detectada en el periodo analizado.",
        }
        for field in ("euforia", "miedo", "duda")
        if peaks[field] is not None and Decimal(str(peaks[field])) >= EXTREME_EMOTION_THRESHOLD
    ]


def _owned_account(context: ChatExecutionContext) -> Cuenta_Trading:
    if context.account_id is None:
        raise ChatToolAccessError("Primero se debe confirmar una cuenta de trading.")
    account = context.db.query(Cuenta_Trading).filter(
        Cuenta_Trading.id == context.account_id,
        Cuenta_Trading.id_usuario == context.user_id,
    ).first()
    if account is None:
        raise ChatToolAccessError("Cuenta de trading no encontrada.")
    return account


def list_accounts(context: ChatExecutionContext) -> dict[str, Any]:
    accounts = context.db.query(Cuenta_Trading).filter(
        Cuenta_Trading.id_usuario == context.user_id
    ).order_by(Cuenta_Trading.id.asc()).limit(30).all()
    return {"accounts": [{
        "id": account.id, "name": account.nombre_cuenta, "currency": account.divisa,
        "balance": _number(account.saldo_actual),
    } for account in accounts]}


def summarize_results(context: ChatExecutionContext, days: int = 30) -> dict[str, Any]:
    account = _owned_account(context)
    days = _days(days)
    start = datetime.utcnow() - timedelta(days=days)
    query = context.db.query(Operacion).filter(
        Operacion.id_cuenta == account.id, Operacion.fecha_hora >= start
    )
    total, pnl, wins, losses, avg_rr = query.with_entities(
        func.count(Operacion.id), func.coalesce(func.sum(Operacion.resultado), 0),
        func.sum(case((Operacion.resultado > 0, 1), else_=0)),
        func.sum(case((Operacion.resultado < 0, 1), else_=0)), func.avg(Operacion.ratio_rr),
    ).one()
    return {
        "account": {"id": account.id, "name": account.nombre_cuenta}, "period_days": days,
        "operations": int(total or 0), "pnl": _number(pnl), "wins": int(wins or 0),
        "losses": int(losses or 0), "average_rr": _number(avg_rr),
    }


def search_operations(
    context: ChatExecutionContext, days: int = 30, asset: str | None = None, limit: int = 10
) -> dict[str, Any]:
    account = _owned_account(context)
    days = _days(days)
    limit = min(max(int(limit), 1), MAX_OPERATIONS)
    query = context.db.query(Operacion).filter(
        Operacion.id_cuenta == account.id,
        Operacion.fecha_hora >= datetime.utcnow() - timedelta(days=days),
    )
    if asset:
        query = query.filter(Operacion.activo.ilike(f"%{asset.strip()[:10]}%"))
    rows = query.order_by(Operacion.fecha_hora.desc()).limit(limit).all()
    return {"account_id": account.id, "period_days": days, "operations": [{
        "id": row.id, "date": _timestamp(row.fecha_hora), "asset": row.activo,
        "side": str(row.tipo_operacion), "result": _number(row.resultado), "rr": _number(row.ratio_rr),
        "risk_percentage": _number(row.riesgo_porcentaje),
    } for row in rows]}


def get_operation_detail(context: ChatExecutionContext, operation_id: int) -> dict[str, Any]:
    account = _owned_account(context)
    # La cuenta y el propietario se incluyen en la misma consulta ORM.
    row = context.db.query(Operacion).join(Cuenta_Trading).filter(
        Operacion.id == operation_id, Operacion.id_cuenta == account.id,
        Cuenta_Trading.id_usuario == context.user_id,
    ).first()
    if row is None:
        raise ChatToolAccessError("Operacion no encontrada.")
    return {"operation": {
        "id": row.id, "date": _timestamp(row.fecha_hora), "asset": row.activo,
        "side": str(row.tipo_operacion), "result": _number(row.resultado), "rr": _number(row.ratio_rr),
        "risk_percentage": _number(row.riesgo_porcentaje),
        "risk_amount": _number(row.riesgo_importe),
        "confidence": row.nivel_confianza, "notes": (row.notas or "")[:255],
    }}


def audit_plan_discipline(context: ChatExecutionContext, days: int = 30) -> dict[str, Any]:
    """Comprueba solo reglas de riesgo explícitas y medibles del plan del usuario."""
    account = _owned_account(context)
    days = _days(days)
    user = context.db.query(Usuario).filter(Usuario.id == context.user_id).first()
    plan = user.plan_trading if user else ""
    match = _MAX_RISK_PATTERN.search(plan or "")
    if match is None:
        return {
            "account_id": account.id,
            "period_days": days,
            "status": "rule_not_measurable",
            "message": "El plan no contiene un límite de riesgo porcentual medible.",
        }

    max_risk = float(match.group(1).replace(",", "."))
    rows = context.db.query(Operacion).filter(
        Operacion.id_cuenta == account.id,
        Operacion.fecha_hora >= datetime.utcnow() - timedelta(days=days),
    ).order_by(Operacion.fecha_hora.desc()).limit(MAX_OPERATIONS).all()
    missing_risk = [row for row in rows if row.riesgo_porcentaje is None]
    violations = [
        row for row in rows
        if row.riesgo_porcentaje is not None and float(row.riesgo_porcentaje) > max_risk
    ]
    return {
        "account_id": account.id,
        "period_days": days,
        "status": "checked",
        "max_risk_percentage": max_risk,
        "checked_operations": len(rows),
        "missing_risk_operations": len(missing_risk),
        "violations": [{
            "date": _timestamp(row.fecha_hora),
            "asset": row.activo,
            "risk_percentage": _number(row.riesgo_porcentaje),
        } for row in violations],
    }


def analyze_emotions(context: ChatExecutionContext, days: int = 30) -> dict[str, Any]:
    account = _owned_account(context)
    days = _days(days)
    start = datetime.utcnow() - timedelta(days=days)
    rows = context.db.query(Registro_emocional).join(Operacion).join(Cuenta_Trading).filter(
        Operacion.id_cuenta == account.id, Cuenta_Trading.id_usuario == context.user_id,
        Registro_emocional.fecha_hora >= start,
    ).order_by(Registro_emocional.fecha_hora.desc()).limit(MAX_OPERATIONS).all()
    fields = ("confianza", "duda", "euforia", "miedo", "neutral")
    averages = {field: _number(sum((getattr(row, field) or 0) for row in rows) / len(rows)) if rows else None for field in fields}
    peaks = {field: _number(max((getattr(row, field) or 0 for row in rows), default=None)) for field in fields}
    alerts = _emotion_alerts(averages, peaks)
    return {
        "account_id": account.id,
        "period_days": days,
        "records": len(rows),
        "averages": averages,
        "peaks": peaks,
        "alerts": alerts,
    }


def make_langchain_tools(context: ChatExecutionContext) -> list[Any]:
    """Crea funciones tipadas sin parametros de identidad expuestos al modelo."""
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as error:  # la ruta convierte esto a un SSE seguro
        raise RuntimeError("La integracion LangChain no esta instalada.") from error

    # StructuredTool extrae schemas de estas funciones, sin db/user/account en JSON.
    def cuentas() -> dict[str, Any]:
        """Lista las cuentas de trading del usuario actual."""
        return list_accounts(context)

    def resumen_resultados(days: int = 30) -> dict[str, Any]:
        """Resume resultados de la cuenta confirmada para un periodo en dias."""
        return summarize_results(context, days)

    def buscar_operaciones(days: int = 30, asset: str | None = None, limit: int = 10) -> dict[str, Any]:
        """Busca operaciones recientes de la cuenta confirmada."""
        return search_operations(context, days, asset, limit)

    def detalle_operacion(operation_id: int) -> dict[str, Any]:
        """Obtiene detalle de una operacion de la cuenta confirmada."""
        return get_operation_detail(context, operation_id)

    def analizar_emociones(days: int = 30) -> dict[str, Any]:
        """Calcula medias emocionales de la cuenta confirmada."""
        return analyze_emotions(context, days)

    def auditar_disciplina(days: int = 30) -> dict[str, Any]:
        """Comprueba el límite de riesgo porcentual declarado en el plan de trading."""
        return audit_plan_discipline(context, days)

    return [StructuredTool.from_function(fn) for fn in (
        cuentas, resumen_resultados, buscar_operaciones, detalle_operacion, analizar_emociones, auditar_disciplina
    )]
