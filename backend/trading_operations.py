"""Canonical execution and aggregate calculations for trading operations."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException

from models import Operacion, OperacionEjecucion
from trading_commissions import calculate_commission, calculate_gross_result, money, to_decimal


ZERO = Decimal("0")


def _decimal(value, *, field: str, required: bool = False) -> Decimal | None:
    if value in (None, ""):
        if required:
            raise HTTPException(status_code=422, detail=f"{field} es obligatorio")
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=f"{field} no es un número válido") from error
    if not parsed.is_finite():
        raise HTTPException(status_code=422, detail=f"{field} no es un número finito")
    return parsed


def _datetime(value, *, field: str) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=f"{field} no es una fecha ISO válida") from error
    return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed


def parse_salidas_json(raw: str | None) -> list[dict] | None:
    if raw is None:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=422, detail="salidas_json no es JSON válido") from error
    if not isinstance(value, list):
        raise HTTPException(status_code=422, detail="salidas_json debe ser una lista")
    if len(value) > 1000:
        raise HTTPException(status_code=422, detail="Una operación no puede contener más de 1000 salidas")
    return value


def build_manual_executions(
    operation: Operacion,
    account,
    exits: list[dict],
    *,
    legacy_gross: Decimal | None = None,
) -> list[OperacionEjecucion]:
    operation.fecha_hora = _datetime(operation.fecha_hora, field="fecha_hora")
    entry_quantity = to_decimal(operation.cantidad)
    entry_price = to_decimal(operation.precio_entrada)
    if entry_quantity <= 0:
        raise HTTPException(status_code=422, detail="La cantidad de entrada debe ser mayor que cero")

    commission_cost = calculate_commission(
        account.tipo_comision,
        account.valor_comision,
        entry_quantity,
        entry_price,
    )
    executions = [
        OperacionEjecucion(
            rol="ENTRY",
            fecha_hora=operation.fecha_hora,
            cantidad=entry_quantity,
            precio=entry_price,
            resultado_bruto=None,
            impacto_comision=-commission_cost,
            impacto_swap=ZERO,
            impacto_tasa=ZERO,
            resultado_neto=-commission_cost,
            origen="CALCULATED",
        )
    ]

    for index, item in enumerate(exits):
        if not isinstance(item, dict):
            raise HTTPException(status_code=422, detail=f"La salida {index + 1} no es válida")
        quantity = _decimal(item.get("cantidad"), field=f"salidas[{index}].cantidad", required=True)
        price = _decimal(item.get("precio", item.get("precio_salida")), field=f"salidas[{index}].precio")
        when = _datetime(item.get("fecha_hora"), field=f"salidas[{index}].fecha_hora")
        if quantity <= 0 or (price is not None and price <= 0):
            raise HTTPException(status_code=422, detail=f"La salida {index + 1} debe tener cantidad positiva y un precio válido")
        if when < operation.fecha_hora:
            raise HTTPException(status_code=422, detail=f"La salida {index + 1} no puede ser anterior a la entrada")

        gross = _decimal(item.get("resultado_bruto"), field=f"salidas[{index}].resultado_bruto")
        if gross is None and price is not None:
            gross = calculate_gross_result(operation.tipo_operacion, quantity, entry_price, price)
        if gross is None and legacy_gross is not None and len(exits) == 1:
            gross = legacy_gross
        if gross is None:
            raise HTTPException(
                status_code=422,
                detail=f"La salida {index + 1} necesita precio o resultado bruto",
            )
        commission_cost_exit = _decimal(item.get("comision", 0), field=f"salidas[{index}].comision") or ZERO
        fee_cost = _decimal(item.get("tasa", item.get("fee", 0)), field=f"salidas[{index}].tasa") or ZERO
        swap = _decimal(item.get("swap", 0), field=f"salidas[{index}].swap") or ZERO
        if commission_cost_exit < 0 or fee_cost < 0:
            raise HTTPException(status_code=422, detail="Comisión y tasa manuales deben expresarse como costes positivos")
        gross = gross or ZERO
        net = money(gross - commission_cost_exit + swap - fee_cost)
        executions.append(
            OperacionEjecucion(
                rol="EXIT",
                fecha_hora=when,
                cantidad=quantity,
                precio=price,
                resultado_bruto=money(gross),
                impacto_comision=-money(commission_cost_exit),
                impacto_swap=money(swap),
                impacto_tasa=-money(fee_cost),
                resultado_neto=net,
                origen="MANUAL" if item.get("resultado_bruto") not in (None, "") else "CALCULATED",
            )
        )
    return executions


def legacy_exit_payload(operation: Operacion, gross: Decimal | None = None) -> list[dict]:
    if operation.precio_salida is None and gross is None:
        return []
    return [{
        "fecha_hora": operation.fecha_hora.isoformat(),
        "cantidad": str(operation.cantidad),
        "precio": str(operation.precio_salida) if operation.precio_salida is not None else None,
        "resultado_bruto": str(gross) if gross is not None else None,
        "comision": "0",
        "swap": "0",
        "tasa": "0",
    }]


def recalculate_operation(operation: Operacion) -> Decimal:
    entries = [item for item in operation.ejecuciones if item.rol == "ENTRY"]
    exits = [item for item in operation.ejecuciones if item.rol == "EXIT"]
    entered = sum((to_decimal(item.cantidad) for item in entries), ZERO)
    exited = sum((to_decimal(item.cantidad) for item in exits), ZERO)
    if entered <= 0:
        raise HTTPException(status_code=422, detail="La operación necesita al menos una entrada")
    if exited > entered:
        raise HTTPException(status_code=422, detail="Las salidas superan la cantidad abierta")

    operation.cantidad = money(entered)
    operation.cantidad_abierta = money(entered - exited)
    if entries:
        weighted_entry = sum((to_decimal(item.precio or 0) * to_decimal(item.cantidad) for item in entries), ZERO)
        operation.precio_entrada = money(weighted_entry / entered)
        operation.fecha_hora = min(item.fecha_hora for item in entries)
    if exits and all(item.precio is not None for item in exits):
        weighted_exit = sum((to_decimal(item.precio or 0) * to_decimal(item.cantidad) for item in exits), ZERO)
        operation.precio_salida = money(weighted_exit / exited)
    else:
        operation.precio_salida = None

    operation.resultado_bruto = money(sum((to_decimal(item.resultado_bruto or 0) for item in exits), ZERO)) if exits else None
    operation.comisiones = money(-sum((to_decimal(item.impacto_comision or 0) for item in operation.ejecuciones), ZERO))
    operation.swap = money(sum((to_decimal(item.impacto_swap or 0) for item in operation.ejecuciones), ZERO))
    operation.tasas = money(-sum((to_decimal(item.impacto_tasa or 0) for item in operation.ejecuciones), ZERO))
    total_net = money(sum((to_decimal(item.resultado_neto or 0) for item in operation.ejecuciones), ZERO))
    operation.resultado = total_net if exits else None

    if exited == ZERO:
        operation.estado = "OPEN"
        operation.fecha_cierre = None
    elif exited < entered:
        operation.estado = "PARTIALLY_CLOSED"
        operation.fecha_cierre = None
    else:
        operation.estado = "CLOSED"
        operation.fecha_cierre = max(item.fecha_hora for item in exits)
    return total_net


def serialize_execution(execution: OperacionEjecucion) -> dict:
    return {
        "id": execution.id,
        "rol": execution.rol,
        "fecha_hora": execution.fecha_hora.isoformat(),
        "cantidad": float(execution.cantidad),
        "precio": float(execution.precio) if execution.precio is not None else None,
        "resultado_bruto": float(execution.resultado_bruto) if execution.resultado_bruto is not None else None,
        "comision": float(-to_decimal(execution.impacto_comision or 0)),
        "swap": float(execution.impacto_swap or 0),
        "tasa": float(-to_decimal(execution.impacto_tasa or 0)),
        "resultado_neto": float(execution.resultado_neto or 0),
        "origen": execution.origen,
        "source_row_id": execution.source_row_id,
    }
