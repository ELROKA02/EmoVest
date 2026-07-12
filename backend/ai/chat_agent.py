"""Bucle secuencial del analista; LangChain interoperable, seguridad propia."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from ai.chat_sessions import ChatSession
from ai.chat_sessions import ChatSessionForbidden, ChatSessionStore, ChatSessionUnavailable
from ai.chat_tools import ChatExecutionContext, list_accounts, make_langchain_tools
from models import Cuenta_Trading
from sqlalchemy.orm import Session


MAX_TOOL_ROUNDS = 4
SYSTEM_POLICY = """Eres EVA la analista educativa de EmoVest. Analiza patrones, riesgos y habitos
usando solo resultados de herramientas. No des senales, recomendaciones ni ordenes de compra o venta.
Si el usuario no indica un periodo, usa los ultimos 30 dias e indicalo. Si usas datos,
explica el periodo y termina con evidencias verificables. No inventes datos."""


class ChatModelUnavailable(RuntimeError):
    public_message = "El modelo configurado no admite el chat con herramientas o no esta disponible."


class ChatUnavailableError(RuntimeError):
    """Error sin detalles internos que la ruta puede convertir a SSE/503."""

    public_message = "El chat no esta disponible en este momento."


@dataclass
class ChatAgentResult:
    text: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    history: list[dict[str, str]] = field(default_factory=list)
    tool_summaries: list[dict[str, Any]] = field(default_factory=list)


def _messages(session: ChatSession, user_message: str) -> list[Any]:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
    except ImportError as error:
        raise ChatModelUnavailable() from error
    messages: list[Any] = [SystemMessage(content=SYSTEM_POLICY)]
    for message in session.history:
        # Solo se conserva el historial compacto del usuario/asistente.
        if message.get("role") == "assistant":
            from langchain_core.messages import AIMessage
            messages.append(AIMessage(content=message.get("content", "")))
        else:
            messages.append(HumanMessage(content=message.get("content", "")))
    messages.append(HumanMessage(content=user_message))
    return messages


def _summarize_tool(name: str, result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"tool": name}
    summary = {key: value for key, value in result.items() if key in {
        "account", "account_id", "period_days", "operations", "pnl", "wins", "losses", "average_rr", "records", "averages"
    }}
    # La busqueda devuelve objetos de operaciones al modelo, pero Redis solo
    # conserva sus IDs/recuento para no duplicar resultados grandes.
    operations = summary.get("operations")
    if isinstance(operations, list):
        summary["operation_ids"] = [row.get("id") for row in operations if isinstance(row, dict) and row.get("id") is not None]
        summary["operations"] = len(operations)
    return summary | {"tool": name}


def _evidence(summaries: list[dict[str, Any]], account_id: int | None) -> list[dict[str, Any]]:
    return [{"account_id": account_id, **item} for item in summaries]


def run_chat_agent(
    *, model: Any, session: ChatSession, context: ChatExecutionContext, user_message: str,
    on_delta: Callable[[str], None] | None = None,
) -> ChatAgentResult:
    """Ejecuta el ciclo modelo/herramienta, con limite propio de cuatro rondas.

    El adaptador LangChain solo traduce mensajes/tools. No recibe credenciales,
    sesiones Redis ni una forma de acceder directamente a la base de datos.
    """
    if not context.account_id:
        text = "Antes de analizar necesito que selecciones una cuenta de trading."
        return ChatAgentResult(text=text, history=[{"role": "user", "content": user_message}, {"role": "assistant", "content": text}])
    tools = make_langchain_tools(context)
    try:
        bound_model = model.bind_tools(tools)
    except Exception as error:
        raise ChatModelUnavailable() from error
    tool_map = {tool.name: tool for tool in tools}
    messages = _messages(session, user_message)
    summaries: list[dict[str, Any]] = []

    for _round in range(MAX_TOOL_ROUNDS):
        try:
            response = bound_model.invoke(messages)
        except Exception as error:
            raise ChatModelUnavailable() from error
        calls = getattr(response, "tool_calls", None) or []
        messages.append(response)
        if not calls:
            text = str(getattr(response, "content", "")).strip()
            if on_delta and text:
                on_delta(text)
            return ChatAgentResult(
                text=text or "No he podido generar una conclusion con los datos disponibles.",
                evidence=_evidence(summaries, context.account_id),
                history=[{"role": "user", "content": user_message}, {"role": "assistant", "content": text}],
                tool_summaries=summaries,
            )
        for call in calls:
            name = call.get("name")
            tool = tool_map.get(name)
            if tool is None:
                result: Any = {"error": "Herramienta no permitida."}
            else:
                try:
                    result = tool.invoke(call.get("args", {}))
                except Exception:
                    result = {"error": "No se pudo consultar ese dato de forma segura."}
            summaries.append(_summarize_tool(name or "unknown", result))
            try:
                from langchain_core.messages import ToolMessage
                messages.append(ToolMessage(content=json.dumps(result, default=str), tool_call_id=call.get("id", name or "tool")))
            except ImportError as error:
                raise ChatModelUnavailable() from error
    # No se permite una quinta llamada aunque LangChain/modelo la solicite.
    text = "He alcanzado el limite seguro de consultas para esta pregunta. Prueba a acotarla."
    return ChatAgentResult(text=text, evidence=_evidence(summaries, context.account_id), history=[
        {"role": "user", "content": user_message}, {"role": "assistant", "content": text}
    ], tool_summaries=summaries)


class ChatAgentService:
    """Servicio de aplicacion para la ruta SSE.

    La ruta le entrega un ``user_id`` autenticado y una sesion SQLAlchemy. Este
    servicio no acepta identificadores de usuario desde el modelo y Redis no
    sustituye las comprobaciones ORM de :mod:`ai.chat_tools`.
    """

    def __init__(self, *, db: Session, session_store: ChatSessionStore | None = None):
        self.db = db
        self.session_store = session_store or ChatSessionStore()

    def stream(
        self, *, mensaje: str, user_id: int, session_id: str | None = None, account_id: int | None = None
    ):
        """Genera eventos internos ordenados: session, status, delta, evidence, done/error."""
        try:
            session = self.session_store.get(session_id, user_id) if session_id else None
            created = session is None
            if account_id is not None:
                # La seleccion llega del frontend autenticado, no de argumentos
                # del LLM. Se valida ahora y se vuelve a validar por herramienta.
                owned = self.db.query(Cuenta_Trading.id).filter(
                    Cuenta_Trading.id == account_id,
                    Cuenta_Trading.id_usuario == user_id,
                ).first()
                if owned is None:
                    raise ChatUnavailableError()
            if session is None:
                session = self.session_store.create(user_id=user_id, account_id=account_id)
            elif account_id is not None:
                # Es una seleccion de UI autenticada; las herramientas aun la
                # verifican contra ORM antes de leer cualquier dato.
                session.account_id = account_id
                self.session_store.save(session, user_id)

            yield {"event": "session", "data": {"session_id": session.id, "created": created}}
            yield {"event": "status", "data": {"status": "consultando"}}

            if session.account_id is None:
                # Sin cuenta no se inicia el agente ni se consulta ninguna tabla
                # financiera: exclusivamente se muestran las cuentas disponibles.
                accounts = list_accounts(ChatExecutionContext(db=self.db, user_id=user_id, account_id=None))
                text = "Antes de analizar necesito que selecciones una cuenta de trading."
                session.history.extend([{"role": "user", "content": mensaje}, {"role": "assistant", "content": text}])
                session.tool_summaries.append({"tool": "cuentas", "accounts": [a["id"] for a in accounts["accounts"]]})
                self.session_store.save(session, user_id)
                yield {"event": "delta", "data": {"text": text}}
                yield {"event": "evidence", "data": {"items": [{"tool": "cuentas", "accounts": accounts["accounts"]}]}}
                yield {"event": "done", "data": {"session_id": session.id}}
                return

            from ai.manager import AI_USE_CASE_CHAT, get_effective_ai_settings, get_langchain_chat_model
            model = get_langchain_chat_model(get_effective_ai_settings(AI_USE_CASE_CHAT, self.db))
            result = run_chat_agent(
                model=model,
                session=session,
                context=ChatExecutionContext(db=self.db, user_id=user_id, account_id=session.account_id),
                user_message=mensaje,
            )
            # Persistir solo historial corto y referencias compactas, nunca resultados ORM completos.
            session.history.extend(result.history)
            session.tool_summaries.extend(result.tool_summaries)
            self.session_store.save(session, user_id)
            if result.text:
                yield {"event": "delta", "data": {"text": result.text}}
            if result.evidence:
                yield {"event": "evidence", "data": {"items": result.evidence}}
            yield {"event": "done", "data": {"session_id": session.id}}
        except (ChatSessionUnavailable, ChatSessionForbidden, ChatModelUnavailable, RuntimeError) as error:
            # La ruta deliberadamente no recibe la causa, URL o detalle del proveedor.
            raise ChatUnavailableError() from error
