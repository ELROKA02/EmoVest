from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import SessionLocal
from config import APP_CONFIG_DIR
from models import Cuenta_Trading, Operacion
from trading_commissions import to_decimal
from trading_operations import build_manual_executions, recalculate_operation
from trading_risk import calculate_operation_risk


MCP_PROTOCOL_VERSION = "2025-06-18"
MCP_PORT = int(os.getenv("EMOVEST_MCP_PORT", "8000"))
MCP_HOST = "127.0.0.1"

_TOOLS = [
    {
        "name": "list_accounts",
        "description": "Lista las cuentas de trading guardadas localmente en EmoVest.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "list_operations",
        "description": "Lista las operaciones de una cuenta de trading de EmoVest.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "integer",
                    "description": "Identificador de la cuenta de trading.",
                },
            },
            "required": ["account_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_operation",
        "description": "Crea y guarda inmediatamente una operación en EmoVest.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "integer"}, "date": {"type": "string"},
                "side": {"type": "string", "enum": ["LONG", "SHORT"]}, "asset": {"type": "string"},
                "quantity": {"type": "number"}, "entry_price": {"type": "number"},
                "exits": {
                    "type": "array",
                    "description": "Cierres de la operación. Cada salida usa date, quantity y exit_price; opcionalmente commission, swap y fee.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string"}, "quantity": {"type": "number"},
                            "exit_price": {"type": "number"}, "commission": {"type": "number"},
                            "swap": {"type": "number"}, "fee": {"type": "number"},
                        },
                        "required": ["date", "quantity", "exit_price"],
                        "additionalProperties": False,
                    },
                },
                "notes": {"type": "string"}, "stop_loss": {"type": "number"}, "take_profit": {"type": "number"},
                "ratio_rr": {"type": "number"}, "confidence_level": {"type": "integer"},
            },
            "required": ["account_id", "date", "side", "asset", "quantity", "entry_price"],
            "additionalProperties": False,
        },
    },
    {
        "name": "update_operation",
        "description": "Actualiza y guarda inmediatamente una operación de EmoVest.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "integer"}, "operation_id": {"type": "integer"},
                "date": {"type": "string"}, "side": {"type": "string", "enum": ["LONG", "SHORT"]},
                "asset": {"type": "string"}, "quantity": {"type": "number"}, "entry_price": {"type": "number"},
                "exits": {"type": "array"}, "notes": {"type": "string"}, "stop_loss": {"type": "number"},
                "take_profit": {"type": "number"}, "ratio_rr": {"type": "number"}, "confidence_level": {"type": "integer"},
            },
            "required": ["account_id", "operation_id"], "additionalProperties": False,
        },
    },
    {
        "name": "delete_operation",
        "description": "Elimina inmediatamente una operación de EmoVest.",
        "inputSchema": {
            "type": "object", "properties": {"account_id": {"type": "integer"}, "operation_id": {"type": "integer"}},
            "required": ["account_id", "operation_id"], "additionalProperties": False,
        },
    },
    {
        "name": "update_account",
        "description": "Actualiza y guarda inmediatamente una cuenta de EmoVest.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "integer"}, "name": {"type": "string"}, "current_balance": {"type": "number"},
                "commission_type": {"type": "string", "enum": ["sin_comision", "fija", "porcentaje"]}, "commission_value": {"type": "number"},
            },
            "required": ["account_id"], "additionalProperties": False,
        },
    },
    {
        "name": "delete_account",
        "description": "Elimina inmediatamente una cuenta vacía de EmoVest.",
        "inputSchema": {
            "type": "object", "properties": {"account_id": {"type": "integer"}},
            "required": ["account_id"], "additionalProperties": False,
        },
    },
    {
        "name": "get_confirmation_status",
        "description": "Consulta el resultado de una acción que espera confirmación en EmoVest.",
        "inputSchema": {
            "type": "object", "properties": {"confirmation_id": {"type": "string"}},
            "required": ["confirmation_id"], "additionalProperties": False,
        },
    },
]

_MUTATING_TOOLS = {"create_operation", "update_operation", "delete_operation", "update_account", "delete_account"}
_DEFAULT_ENABLED_TOOLS = {"list_accounts", "list_operations", "get_confirmation_status"}


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _account_payload(account: Cuenta_Trading) -> dict[str, Any]:
    return {
        "id": account.id,
        "name": account.nombre_cuenta,
        "currency": account.divisa,
        "initial_balance": _json_value(account.saldo_inicial),
        "current_balance": _json_value(account.saldo_actual),
        "commission_type": account.tipo_comision,
        "commission_value": _json_value(account.valor_comision),
        "created_at": _json_value(account.fecha_creacion),
    }


def _operation_payload(operation: Operacion) -> dict[str, Any]:
    return {
        "id": operation.id,
        "account_id": operation.id_cuenta,
        "date": _json_value(operation.fecha_hora),
        "side": operation.tipo_operacion,
        "asset": operation.activo,
        "quantity": _json_value(operation.cantidad),
        "entry_price": _json_value(operation.precio_entrada),
        "exit_price": _json_value(operation.precio_salida),
        "net_result": _json_value(operation.resultado),
        "status": operation.estado,
        "notes": operation.notas,
        "stop_loss": _json_value(operation.stop_loss),
        "take_profit": _json_value(operation.take_profit),
        "ratio_rr": _json_value(operation.ratio_rr),
        "confidence_level": operation.nivel_confianza,
    }


def _integer(arguments: dict[str, Any], name: str) -> int:
    value = arguments.get(name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} debe ser un número entero.")
    return value


def _number(value: Any, name: str, *, required: bool = False) -> Decimal | None:
    if value is None:
        if required:
            raise ValueError(f"{name} es obligatorio.")
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError(f"{name} debe ser un número válido.")
    try:
        return to_decimal(value)
    except Exception as error:
        raise ValueError(f"{name} debe ser un número válido.") from error


def _datetime(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{name} debe ser una fecha ISO-8601.")
    try:
        parsed = datetime.fromisoformat(value.replace(".", "-").replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} debe ser una fecha ISO-8601.") from error
    return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed


def _normalize_exits(exits: Any) -> list[dict[str, Any]]:
    """Adapta el contrato MCP en inglés al formato canónico de ejecuciones."""
    if not isinstance(exits, list):
        raise ValueError("exits debe ser una lista.")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(exits):
        if not isinstance(item, dict):
            raise ValueError(f"La salida {index + 1} no es válida.")
        exit_date = item.get("date", item.get("fecha_hora"))
        if isinstance(exit_date, str):
            exit_date = exit_date.replace(".", "-")
        normalized.append({
            "fecha_hora": exit_date,
            "cantidad": item.get("quantity", item.get("cantidad")),
            "precio": item.get("exit_price", item.get("price", item.get("precio"))),
            "resultado_bruto": item.get("gross_result", item.get("resultado_bruto")),
            "comision": item.get("commission", item.get("comision", 0)),
            "swap": item.get("swap", 0),
            "tasa": item.get("fee", item.get("tasa", 0)),
        })
    return normalized


def _get_account(db: Session, account_id: int) -> Cuenta_Trading:
    account = db.query(Cuenta_Trading).filter(Cuenta_Trading.id == account_id).first()
    if not account:
        raise ValueError("Cuenta de trading no encontrada.")
    return account


def _get_operation(db: Session, account_id: int, operation_id: int) -> tuple[Cuenta_Trading, Operacion]:
    account = _get_account(db, account_id)
    operation = db.query(Operacion).filter(Operacion.id == operation_id, Operacion.id_cuenta == account.id).first()
    if not operation:
        raise ValueError("Operación no encontrada.")
    return account, operation


def _operation_total(operation: Operacion) -> Decimal:
    if operation.ejecuciones:
        return sum((to_decimal(item.resultado_neto or 0) for item in operation.ejecuciones), Decimal("0"))
    return to_decimal(operation.resultado or 0)


def _update_balance(account: Cuenta_Trading, difference: Decimal) -> None:
    account.saldo_actual = to_decimal(account.saldo_actual or 0) + difference


def _update_risk(operation: Operacion, account: Cuenta_Trading) -> None:
    risk_amount, risk_percent = calculate_operation_risk(
        balance=to_decimal(account.saldo_actual or 0), quantity=operation.cantidad,
        entry_price=operation.precio_entrada, stop_loss=operation.stop_loss, side=operation.tipo_operacion,
    )
    operation.saldo_referencia_riesgo = to_decimal(account.saldo_actual or 0) if risk_amount is not None else None
    operation.riesgo_importe = risk_amount
    operation.riesgo_porcentaje = risk_percent


def _commit(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise ValueError("No se pudieron guardar los cambios en EmoVest.") from error


def _create_operation(db: Session, arguments: dict[str, Any]) -> dict[str, Any]:
    account = _get_account(db, _integer(arguments, "account_id"))
    side, asset = arguments.get("side"), arguments.get("asset")
    if side not in {"LONG", "SHORT"}:
        raise ValueError("side debe ser LONG o SHORT.")
    if not isinstance(asset, str) or not asset.strip():
        raise ValueError("asset es obligatorio.")
    exits = _normalize_exits(arguments.get("exits", []))
    operation = Operacion(
        id_cuenta=account.id, fecha_hora=_datetime(arguments.get("date"), "date"), tipo_operacion=side,
        activo=asset.strip(), cantidad=_number(arguments.get("quantity"), "quantity", required=True),
        precio_entrada=_number(arguments.get("entry_price"), "entry_price", required=True), notas=arguments.get("notes"),
        stop_loss=_number(arguments.get("stop_loss"), "stop_loss"), take_profit=_number(arguments.get("take_profit"), "take_profit"),
        ratio_rr=_number(arguments.get("ratio_rr"), "ratio_rr"), nivel_confianza=arguments.get("confidence_level"),
    )
    try:
        operation.ejecuciones.extend(build_manual_executions(operation, account, exits))
        result = recalculate_operation(operation)
        _update_risk(operation, account)
        db.add(operation)
        _update_balance(account, result)
        _commit(db)
        db.refresh(operation)
    except HTTPException as error:
        db.rollback()
        raise ValueError(str(error.detail)) from error
    return {"message": "Operación creada exitosamente", "operation": _operation_payload(operation)}


def _update_operation(db: Session, arguments: dict[str, Any]) -> dict[str, Any]:
    account, operation = _get_operation(db, _integer(arguments, "account_id"), _integer(arguments, "operation_id"))
    financial_fields = {"date", "side", "quantity", "entry_price", "exits"}
    if any(item.origen == "BROKER" for item in operation.ejecuciones) and financial_fields & arguments.keys():
        raise ValueError("Los datos financieros importados deben corregirse en el origen y volver a importarse.")
    if "asset" in arguments:
        if not isinstance(arguments["asset"], str) or not arguments["asset"].strip():
            raise ValueError("asset no puede estar vacío.")
        operation.activo = arguments["asset"].strip()
    for argument, field in {"notes": "notas", "stop_loss": "stop_loss", "take_profit": "take_profit", "ratio_rr": "ratio_rr", "confidence_level": "nivel_confianza"}.items():
        if argument in arguments:
            setattr(operation, field, arguments[argument] if argument in {"notes", "confidence_level"} else _number(arguments[argument], argument))
    if financial_fields & arguments.keys():
        exits = arguments.get("exits")
        if not isinstance(exits, list):
            raise ValueError("Para cambiar datos financieros debes incluir exits completo, aunque esté vacío si la operación sigue abierta.")
        if "date" in arguments:
            operation.fecha_hora = _datetime(arguments["date"], "date")
        if "side" in arguments:
            if arguments["side"] not in {"LONG", "SHORT"}:
                raise ValueError("side debe ser LONG o SHORT.")
            operation.tipo_operacion = arguments["side"]
        if "quantity" in arguments:
            operation.cantidad = _number(arguments["quantity"], "quantity", required=True)
        if "entry_price" in arguments:
            operation.precio_entrada = _number(arguments["entry_price"], "entry_price", required=True)
        old_total = _operation_total(operation)
        try:
            operation.ejecuciones.clear()
            operation.ejecuciones.extend(build_manual_executions(operation, account, _normalize_exits(exits)))
            new_total = recalculate_operation(operation)
            _update_balance(account, new_total - old_total)
        except HTTPException as error:
            db.rollback()
            raise ValueError(str(error.detail)) from error
    _update_risk(operation, account)
    _commit(db)
    db.refresh(operation)
    return {"message": "Operación actualizada exitosamente", "operation": _operation_payload(operation)}


def _delete_operation(db: Session, arguments: dict[str, Any]) -> dict[str, Any]:
    account, operation = _get_operation(db, _integer(arguments, "account_id"), _integer(arguments, "operation_id"))
    _update_balance(account, -_operation_total(operation))
    operation_id = operation.id
    db.delete(operation)
    _commit(db)
    return {"message": "Operación eliminada exitosamente", "operation_id": operation_id, "account_id": account.id}


def _update_account(db: Session, arguments: dict[str, Any]) -> dict[str, Any]:
    account = _get_account(db, _integer(arguments, "account_id"))
    if "name" in arguments:
        if not isinstance(arguments["name"], str) or not arguments["name"].strip():
            raise ValueError("name no puede estar vacío.")
        account.nombre_cuenta = arguments["name"].strip()
    if "current_balance" in arguments:
        account.saldo_actual = _number(arguments["current_balance"], "current_balance", required=True)
    commission_type = arguments.get("commission_type", account.tipo_comision)
    commission_value = _number(arguments.get("commission_value", account.valor_comision), "commission_value", required=True)
    if commission_type not in {"sin_comision", "fija", "porcentaje"} or commission_value < 0:
        raise ValueError("La configuración de comisión no es válida.")
    account.tipo_comision = commission_type
    account.valor_comision = Decimal("0") if commission_type == "sin_comision" else commission_value
    _commit(db)
    db.refresh(account)
    return {"message": "Cuenta actualizada exitosamente", "account": _account_payload(account)}


def _delete_account(db: Session, arguments: dict[str, Any]) -> dict[str, Any]:
    account = _get_account(db, _integer(arguments, "account_id"))
    if db.query(Operacion.id).filter(Operacion.id_cuenta == account.id).first():
        raise ValueError("La cuenta tiene operaciones. Elimínalas explícitamente antes de eliminar la cuenta.")
    account_id = account.id
    db.delete(account)
    _commit(db)
    return {"message": "Cuenta eliminada exitosamente", "account_id": account_id}


def _execute_mutation(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    with SessionLocal() as db:
        if name == "create_operation":
            return _create_operation(db, arguments)
        if name == "update_operation":
            return _update_operation(db, arguments)
        if name == "delete_operation":
            return _delete_operation(db, arguments)
        if name == "update_account":
            return _update_account(db, arguments)
        if name == "delete_account":
            return _delete_account(db, arguments)
    raise ValueError(f"La herramienta MCP '{name}' no está disponible.")


def _call_read_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    with SessionLocal() as db:
        if name == "list_accounts":
            accounts = db.query(Cuenta_Trading).order_by(Cuenta_Trading.id).all()
            return {"accounts": [_account_payload(account) for account in accounts]}

        if name == "list_operations":
            account_id = arguments.get("account_id")
            if not isinstance(account_id, int) or isinstance(account_id, bool):
                raise ValueError("account_id debe ser un número entero.")
            operations = (
                db.query(Operacion)
                .filter(Operacion.id_cuenta == account_id)
                .order_by(Operacion.fecha_hora.desc(), Operacion.id.desc())
                .all()
            )
            return {
                "account_id": account_id,
                "operations": [_operation_payload(operation) for operation in operations],
            }

    raise ValueError(f"La herramienta MCP '{name}' no está disponible.")


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def create_mcp_app(controller: Any | None = None) -> FastAPI:
    controller = controller or McpServerController()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.post("/mcp")
    async def mcp(request: Request):
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return JSONResponse(_error(None, -32700, "JSON no válido."), status_code=400)

        if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
            return JSONResponse(_error(None, -32600, "Solicitud MCP no válida."), status_code=400)

        method = payload.get("method")
        request_id = payload.get("id")
        session_id = request.headers.get("mcp-session-id") or str(uuid.uuid4())

        if method == "notifications/initialized":
            return Response(status_code=202, headers={"Mcp-Session-Id": session_id})

        if method == "initialize":
            response = _result(
                request_id,
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "emovest", "version": "0.4.0"},
                },
            )
        elif method == "tools/list":
            response = _result(request_id, {"tools": await controller.available_tools()})
        elif method == "tools/call":
            params = payload.get("params")
            if not isinstance(params, dict):
                response = _error(request_id, -32602, "Parámetros de herramienta no válidos.")
            else:
                name = params.get("name")
                arguments = params.get("arguments", {})
                if not isinstance(name, str) or not isinstance(arguments, dict):
                    response = _error(request_id, -32602, "Parámetros de herramienta no válidos.")
                else:
                    try:
                        content = await controller.call_tool(name, arguments)
                    except ValueError as error:
                        response = _error(request_id, -32602, str(error))
                    except Exception:
                        response = _error(request_id, -32603, "EmoVest no pudo consultar sus datos locales.")
                    else:
                        response = _result(
                            request_id,
                            {"content": [{"type": "text", "text": json.dumps(content, ensure_ascii=False)}]},
                        )
        elif request_id is None:
            return Response(status_code=202, headers={"Mcp-Session-Id": session_id})
        else:
            response = _error(request_id, -32601, "Método MCP no encontrado.")

        return JSONResponse(response, headers={"Mcp-Session-Id": session_id})

    @app.delete("/mcp")
    async def close_mcp_session():
        return Response(status_code=204)

    return app


class McpServerController:
    """Mantiene el servidor MCP de loopback independiente de la API de escritorio."""

    def __init__(self, settings_path: Path | None = None) -> None:
        self._server: uvicorn.Server | None = None
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._confirmation_lock = asyncio.Lock()
        self._tool_settings_lock = asyncio.Lock()
        self._confirmations: dict[str, dict[str, Any]] = {}
        self._tool_settings_path = settings_path or APP_CONFIG_DIR / "mcp-tools.json"
        self._tool_states = self._load_tool_states()
        self._last_error: str | None = None

    def _load_tool_states(self) -> dict[str, bool]:
        known_tools = {tool["name"] for tool in _TOOLS}
        states = {name: name in _DEFAULT_ENABLED_TOOLS for name in known_tools}
        try:
            payload = json.loads(self._tool_settings_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return states
        configured_states = payload.get("tools") if isinstance(payload, dict) else None
        if not isinstance(configured_states, dict):
            return states
        for name, enabled in configured_states.items():
            if name in states and isinstance(enabled, bool):
                states[name] = enabled
        return states

    def _save_tool_states(self) -> None:
        self._tool_settings_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._tool_settings_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps({"tools": self._tool_states}, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary_path, self._tool_settings_path)

    async def tool_states(self) -> dict[str, Any]:
        async with self._tool_settings_lock:
            return {"tools": self._tool_states.copy()}

    async def available_tools(self) -> list[dict[str, Any]]:
        async with self._tool_settings_lock:
            return [tool for tool in _TOOLS if self._tool_states[tool["name"]]]

    async def set_tool_enabled(self, tool_name: str, enabled: bool) -> dict[str, Any]:
        if tool_name not in {tool["name"] for tool in _TOOLS}:
            raise ValueError("Herramienta MCP no encontrada.")
        async with self._tool_settings_lock:
            self._tool_states[tool_name] = enabled
            try:
                self._save_tool_states()
            except OSError as error:
                raise ValueError("No se pudo guardar la configuración de herramientas MCP.") from error
            return {"tools": self._tool_states.copy()}

    @staticmethod
    def _confirmation_summary(action: str, arguments: dict[str, Any]) -> str:
        account_id = arguments.get("account_id")
        if action == "create_operation":
            return f"Crear operación {arguments.get('side')} de {arguments.get('asset')} en la cuenta #{account_id}."
        if action == "update_operation":
            changes = ", ".join(key for key in arguments if key not in {"account_id", "operation_id"}) or "sin campos"
            return f"Actualizar la operación #{arguments.get('operation_id')} de la cuenta #{account_id}: {changes}."
        if action == "delete_operation":
            return f"Eliminar la operación #{arguments.get('operation_id')} de la cuenta #{account_id}."
        if action == "update_account":
            changes = ", ".join(key for key in arguments if key != "account_id") or "sin campos"
            return f"Actualizar la cuenta #{account_id}: {changes}."
        return f"Eliminar la cuenta #{account_id}, siempre que esté vacía."

    @staticmethod
    def _public_confirmation(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": item["id"],
            "action": item["action"],
            "arguments": item["arguments"],
            "summary": item["summary"],
            "status": item["status"],
            "created_at": item["created_at"],
            "expires_at": item["expires_at"],
            "result": item.get("result"),
            "error": item.get("error"),
        }

    def _expire_confirmations(self) -> None:
        now = time.monotonic()
        for item in self._confirmations.values():
            if item["status"] == "pending" and now >= item["deadline"]:
                item["status"] = "expired"
                item["error"] = "La confirmación caducó después de diez minutos."

    async def _propose(self, action: str, arguments: dict[str, Any]) -> dict[str, Any]:
        async with self._confirmation_lock:
            self._expire_confirmations()
            confirmation_id = str(uuid.uuid4())
            now = datetime.now()
            item = {
                "id": confirmation_id,
                "action": action,
                "arguments": arguments.copy(),
                "summary": self._confirmation_summary(action, arguments),
                "status": "pending",
                "created_at": now.isoformat(),
                "expires_at": (now.replace(microsecond=0) + timedelta(minutes=10)).isoformat(),
                "deadline": time.monotonic() + 600,
                "result": None,
                "error": None,
            }
            self._confirmations[confirmation_id] = item
            return self._public_confirmation(item)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        async with self._tool_settings_lock:
            enabled = self._tool_states.get(name)
        if enabled is not True:
            raise ValueError(f"La herramienta MCP '{name}' está desactivada en EmoVest.")
        if name in _MUTATING_TOOLS:
            # Las herramientas MCP activadas representan una autorización explícita
            # del usuario desde Ajustes. Por ello la mutación se ejecuta de forma
            # síncrona y la IA recibe el registro ya persistido, no una propuesta.
            return _execute_mutation(name, arguments)
        if name == "get_confirmation_status":
            confirmation_id = arguments.get("confirmation_id")
            if not isinstance(confirmation_id, str):
                raise ValueError("confirmation_id debe ser texto.")
            return {"confirmation": await self.confirmation_status(confirmation_id)}
        return _call_read_tool(name, arguments)

    async def pending_confirmations(self) -> dict[str, Any]:
        async with self._confirmation_lock:
            self._expire_confirmations()
            pending = [self._public_confirmation(item) for item in self._confirmations.values() if item["status"] == "pending"]
            return {"confirmations": pending}

    async def confirmation_status(self, confirmation_id: str) -> dict[str, Any]:
        async with self._confirmation_lock:
            self._expire_confirmations()
            item = self._confirmations.get(confirmation_id)
            if item is None:
                raise ValueError("Confirmación MCP no encontrada.")
            return self._public_confirmation(item)

    async def approve_confirmation(self, confirmation_id: str) -> dict[str, Any]:
        async with self._confirmation_lock:
            self._expire_confirmations()
            item = self._confirmations.get(confirmation_id)
            if item is None:
                raise ValueError("Confirmación MCP no encontrada.")
            if item["status"] != "pending":
                return self._public_confirmation(item)
            item["status"] = "executing"

        try:
            result = _execute_mutation(item["action"], item["arguments"])
        except Exception as error:
            async with self._confirmation_lock:
                item["status"] = "failed"
                item["error"] = str(error) if isinstance(error, ValueError) else "EmoVest no pudo aplicar la acción confirmada."
                return self._public_confirmation(item)

        async with self._confirmation_lock:
            item["status"] = "completed"
            item["result"] = result
            return self._public_confirmation(item)

    async def reject_confirmation(self, confirmation_id: str) -> dict[str, Any]:
        async with self._confirmation_lock:
            self._expire_confirmations()
            item = self._confirmations.get(confirmation_id)
            if item is None:
                raise ValueError("Confirmación MCP no encontrada.")
            if item["status"] == "pending":
                item["status"] = "rejected"
            return self._public_confirmation(item)

    async def status(self) -> dict[str, Any]:
        running = bool(self._server and self._server.started and self._task and not self._task.done())
        async with self._tool_settings_lock:
            tool_states = self._tool_states.copy()
        return {
            "running": running,
            "endpoint": f"http://localhost:{MCP_PORT}/mcp",
            "port": MCP_PORT,
            "last_error": self._last_error,
            "tools": [tool["name"] for tool in _TOOLS if tool_states[tool["name"]]],
            "tool_states": tool_states,
        }

    async def start(self) -> dict[str, Any]:
        async with self._lock:
            current = await self.status()
            if current["running"]:
                return current

            self._last_error = None
            server = uvicorn.Server(
                uvicorn.Config(
                    create_mcp_app(self),
                    host=MCP_HOST,
                    port=MCP_PORT,
                    access_log=False,
                    log_config=None,
                    server_header=False,
                    date_header=False,
                )
            )
            self._server = server
            self._task = asyncio.create_task(server.serve())
            deadline = asyncio.get_running_loop().time() + 5
            while not server.started and asyncio.get_running_loop().time() < deadline:
                if self._task.done():
                    try:
                        self._task.result()
                    except Exception as error:
                        self._last_error = str(error)
                    else:
                        self._last_error = "El servidor MCP terminó antes de estar listo."
                    break
                await asyncio.sleep(0.025)

            if not server.started:
                if self._last_error is None:
                    self._last_error = f"No se pudo abrir el puerto local {MCP_PORT}."
                self._server = None
                self._task = None
            return await self.status()

    async def stop(self) -> dict[str, Any]:
        async with self._lock:
            server, task = self._server, self._task
            if server is None or task is None:
                return await self.status()

            server.should_exit = True
            try:
                await asyncio.wait_for(task, timeout=5)
            except asyncio.TimeoutError:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            finally:
                self._server = None
                self._task = None
            return await self.status()
