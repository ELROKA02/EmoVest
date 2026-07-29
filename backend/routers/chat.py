"""HTTP boundary for the EmoVest AI chat.

This module deliberately contains no database querying or model-provider logic.
The chat service owns those concerns; the router only authenticates the caller,
validates input and turns the service's safe events into Server-Sent Events.
"""

import inspect
import json
import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from ai.chat_agent import ChatAgentService, ChatUnavailableError
from ai.chat_sessions import ChatSessionStore
from database import get_db
from models import Usuario
from routers.auth import get_current_user


router = APIRouter(prefix="/ia/chat", tags=["chat_ia"])
logger = logging.getLogger(__name__)

_ALLOWED_EVENTS = {"session", "status", "delta", "evidence", "done", "error"}
_EVENT_ORDER = {"session": 0, "status": 2, "delta": 2, "evidence": 3, "done": 4, "error": 4}


class ChatAttachment(BaseModel):
    name: str = Field(..., min_length=1, max_length=180)
    content_type: str = Field(..., min_length=1, max_length=100)
    data: str = Field(..., min_length=1, max_length=7_000_000)

    @field_validator("content_type")
    @classmethod
    def tipo_permitido(cls, value: str) -> str:
        allowed = {"image/jpeg", "image/png", "image/webp", "text/plain", "text/csv", "application/json"}
        if value not in allowed:
            raise ValueError("El tipo de archivo no esta permitido.")
        return value

    @model_validator(mode="after")
    def contenido_valido(self):
        if self.content_type.startswith("image/"):
            prefix = f"data:{self.content_type};base64,"
            if not self.data.startswith(prefix):
                raise ValueError("La imagen adjunta no es valida.")
        return self


class ChatMessageRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=4_000)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    account_id: int | None = Field(default=None, gt=0)
    attachment: ChatAttachment | None = None

    @field_validator("mensaje")
    @classmethod
    def mensaje_no_vacio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El mensaje no puede estar vacio.")
        return value

    @field_validator("session_id")
    @classmethod
    def session_id_seguro(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value or not value.replace("-", "").replace("_", "").isalnum():
            raise ValueError("El identificador de sesion no es valido.")
        return value


def _sse(event: str, data: dict[str, Any]) -> str:
    """Encode a single SSE event without ever interpolating user/model text."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _safe_error(message: str = "El chat no esta disponible en este momento.") -> str:
    return _sse("error", {"message": message})


async def _as_async_iterator(value: Any) -> AsyncIterator[dict[str, Any]]:
    """Accept the service's async stream, and support sync iterators for adapters."""
    if inspect.isawaitable(value):
        value = await value
    if hasattr(value, "__aiter__"):
        async for item in value:
            yield item
        return
    if isinstance(value, Iterator):
        for item in value:
            yield item
        return
    raise ChatUnavailableError("El proveedor de chat no devolvio un stream valido.")


@router.post(
    "/mensajes",
    summary="Enviar un mensaje al analista IA",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
)
async def enviar_mensaje(
    payload: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Stream safe, ordered chat events for the authenticated user only."""

    async def event_stream() -> AsyncIterator[str]:
        last_order = -1
        terminal_sent = False
        error_sent = False
        try:
            service = ChatAgentService(db=db)
            stream = service.stream(
                mensaje=payload.mensaje,
                session_id=payload.session_id,
                user_id=current_user.id,
                user_name=current_user.nombre or "Usuario",
                account_id=payload.account_id,
                attachment=payload.attachment.model_dump() if payload.attachment else None,
            )
            async for item in _as_async_iterator(stream):
                if not isinstance(item, dict):
                    raise ChatUnavailableError("El servicio de chat devolvio un evento invalido.")
                event = item.get("event")
                data = item.get("data", {})
                if event not in _ALLOWED_EVENTS or not isinstance(data, dict):
                    raise ChatUnavailableError("El servicio de chat devolvio un evento invalido.")
                if _EVENT_ORDER[event] < last_order:
                    raise ChatUnavailableError("El servicio de chat devolvio eventos fuera de orden.")
                if terminal_sent:
                    raise ChatUnavailableError("El servicio de chat devolvio eventos despues del cierre.")

                last_order = _EVENT_ORDER[event]
                terminal_sent = event in {"done", "error"}
                error_sent = event == "error"
                yield _sse(event, data)

            if not terminal_sent:
                yield _sse("done", {})
        except ChatUnavailableError:
            logger.exception("El servicio de chat fallo durante el stream SSE.")
            if not error_sent:
                yield _safe_error()
        except Exception:
            # Tracebacks and provider/database details must never cross the API boundary.
            logger.exception("Error inesperado durante el stream SSE del chat.")
            if not error_sent:
                yield _safe_error()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/sesiones/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_sesion(
    session_id: str,
    current_user: Usuario = Depends(get_current_user),
):
    """Delete a temporary chat session only when it belongs to the caller."""
    if not session_id or len(session_id) > 128 or not session_id.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El identificador de sesion no es valido.")

    try:
        store = ChatSessionStore()
        deleted = store.delete_owned(session_id=session_id, user_id=current_user.id)
        if inspect.isawaitable(deleted):
            deleted = await deleted
    except ChatUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="El chat no esta disponible en este momento.") from error
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="El chat no esta disponible en este momento.") from error

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesion no encontrada.")
