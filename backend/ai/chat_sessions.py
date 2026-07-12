"""Estado temporal y seguro de las conversaciones del analista.

Redis solo guarda contexto de UX; nunca se usa para decidir permisos ni para
obtener datos financieros. La autorizacion se vuelve a comprobar en ORM al
ejecutar cada herramienta.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from config import REDIS_URL


SESSION_TTL_SECONDS = 8 * 60 * 60
SESSION_PREFIX = "emovest:chat:session:"
MAX_HISTORY_MESSAGES = 12


class ChatSessionUnavailable(RuntimeError):
    """Error seguro: no se puede garantizar el contexto de la conversacion."""

    public_message = "El chat no esta disponible temporalmente. Intentalo de nuevo mas tarde."


class ChatSessionForbidden(PermissionError):
    """La sesion existe pero no pertenece al usuario autenticado."""


@dataclass
class ChatSession:
    id: str
    user_id: int
    account_id: int | None = None
    history: list[dict[str, str]] = field(default_factory=list)
    tool_summaries: list[dict[str, Any]] = field(default_factory=list)

    def compact(self) -> None:
        self.history = self.history[-MAX_HISTORY_MESSAGES:]
        # Guardar referencias/metricas, no payloads de ORM completos.
        self.tool_summaries = self.tool_summaries[-12:]


class ChatSessionStore:
    """Repositorio Redis de sesiones; todos los metodos fallan de forma cerrada."""

    def __init__(self, redis_client: Redis | None = None, ttl_seconds: int = SESSION_TTL_SECONDS):
        self.redis = redis_client or Redis.from_url(REDIS_URL, decode_responses=True)
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _key(session_id: str) -> str:
        return f"{SESSION_PREFIX}{session_id}"

    def _write(self, session: ChatSession) -> ChatSession:
        session.compact()
        try:
            self.redis.setex(self._key(session.id), self.ttl_seconds, json.dumps(asdict(session), default=str))
        except (RedisError, OSError, ValueError) as error:
            raise ChatSessionUnavailable() from error
        return session

    def create(self, user_id: int, account_id: int | None = None) -> ChatSession:
        return self._write(ChatSession(id=str(uuid.uuid4()), user_id=user_id, account_id=account_id))

    def get(self, session_id: str, user_id: int) -> ChatSession | None:
        try:
            payload = self.redis.get(self._key(session_id))
        except (RedisError, OSError) as error:
            raise ChatSessionUnavailable() from error
        if payload is None:
            return None
        try:
            session = ChatSession(**json.loads(payload))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            # Un estado corrupto no puede reutilizarse como contexto autenticado.
            raise ChatSessionUnavailable() from error
        if session.user_id != user_id:
            raise ChatSessionForbidden("La sesion no pertenece al usuario autenticado.")
        # Cada lectura renueva el TTL, pero no altera los permisos.
        return self._write(session)

    def save(self, session: ChatSession, user_id: int) -> ChatSession:
        if session.user_id != user_id:
            raise ChatSessionForbidden("La sesion no pertenece al usuario autenticado.")
        return self._write(session)

    def delete(self, session_id: str, user_id: int) -> bool:
        # Primero se verifica propiedad; no se borra por conocer un UUID ajeno.
        session = self.get(session_id, user_id)
        if session is None:
            return False
        try:
            return bool(self.redis.delete(self._key(session_id)))
        except (RedisError, OSError) as error:
            raise ChatSessionUnavailable() from error

    # Nombre explicito para los adaptadores HTTP; conserva el chequeo de dueño.
    def delete_owned(self, session_id: str, user_id: int) -> bool:
        return self.delete(session_id, user_id)
