"""Temporary, owner-bound conversation state persisted in local SQLite."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from sqlalchemy.exc import SQLAlchemyError

import config
from database import SessionLocal
from models import ChatSessionRecord


SESSION_TTL_SECONDS = 8 * 60 * 60
MAX_HISTORY_MESSAGES = 12
DEFAULT_EXPIRED_SESSION_PURGE_BATCH_SIZE = 500


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def configured_ttl() -> int:
    try:
        return max(
            60,
            int(getattr(config, "CHAT_SESSION_TTL_SECONDS", SESSION_TTL_SECONDS)),
        )
    except (TypeError, ValueError):
        return SESSION_TTL_SECONDS


class ChatSessionUnavailable(RuntimeError):
    public_message = (
        "El chat no está disponible temporalmente. Inténtalo de nuevo más tarde."
    )


class ChatSessionForbidden(PermissionError):
    pass


@dataclass
class ChatSession:
    id: str
    user_id: int
    account_id: int | None = None
    history: list[dict[str, str]] = field(default_factory=list)
    tool_summaries: list[dict[str, Any]] = field(default_factory=list)
    version: int = 1

    def compact(self) -> None:
        self.history = self.history[-MAX_HISTORY_MESSAGES:]
        self.tool_summaries = self.tool_summaries[-12:]


def purge_expired_chat_sessions(
    session_factory: Callable = SessionLocal,
    *,
    now: datetime | None = None,
    batch_size: int = DEFAULT_EXPIRED_SESSION_PURGE_BATCH_SIZE,
) -> int:
    """Delete a bounded batch without loading private conversation payloads."""

    cutoff = now or utcnow()
    limit = max(1, int(batch_size))
    db = session_factory()
    try:
        expired_ids = [
            session_id
            for (session_id,) in db.query(ChatSessionRecord.id).filter(
                ChatSessionRecord.expires_at <= cutoff
            ).order_by(
                ChatSessionRecord.expires_at.asc()
            ).limit(limit).all()
        ]
        if not expired_ids:
            return 0
        removed = db.query(ChatSessionRecord).filter(
            ChatSessionRecord.id.in_(expired_ids)
        ).delete(synchronize_session=False)
        db.commit()
        return int(removed)
    except (SQLAlchemyError, OSError, ValueError) as error:
        db.rollback()
        raise ChatSessionUnavailable() from error
    finally:
        db.close()


class SqliteChatSessionStore:
    def __init__(
        self,
        session_factory: Callable = SessionLocal,
        ttl_seconds: int | None = None,
    ):
        self.session_factory = session_factory
        self.ttl_seconds = ttl_seconds or configured_ttl()

    def _expires_at(self) -> datetime:
        return utcnow() + timedelta(seconds=self.ttl_seconds)

    @staticmethod
    def _decode(record: ChatSessionRecord) -> ChatSession:
        try:
            history = json.loads(record.history_json or "[]")
            summaries = json.loads(record.tool_summaries_json or "[]")
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ChatSessionUnavailable() from error
        if not isinstance(history, list) or not isinstance(summaries, list):
            raise ChatSessionUnavailable()
        return ChatSession(
            id=record.id,
            user_id=record.user_id,
            account_id=record.account_id,
            history=history,
            tool_summaries=summaries,
            version=record.version,
        )

    def create(self, user_id: int, account_id: int | None = None) -> ChatSession:
        purge_expired_chat_sessions(self.session_factory)
        session = ChatSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            account_id=account_id,
        )
        db = self.session_factory()
        try:
            db.add(ChatSessionRecord(
                id=session.id,
                user_id=user_id,
                account_id=account_id,
                history_json="[]",
                tool_summaries_json="[]",
                expires_at=self._expires_at(),
                created_at=utcnow(),
                updated_at=utcnow(),
                version=session.version,
            ))
            db.commit()
            return session
        except (SQLAlchemyError, OSError, ValueError) as error:
            db.rollback()
            raise ChatSessionUnavailable() from error
        finally:
            db.close()

    def get(self, session_id: str, user_id: int) -> ChatSession | None:
        db = self.session_factory()
        try:
            record = db.query(ChatSessionRecord).filter(
                ChatSessionRecord.id == session_id
            ).first()
            if record is None:
                return None
            if record.user_id != user_id:
                raise ChatSessionForbidden(
                    "La sesión no pertenece al usuario autenticado."
                )
            if record.expires_at <= utcnow():
                db.delete(record)
                db.commit()
                return None
            session = self._decode(record)
            updated = db.query(ChatSessionRecord).filter(
                ChatSessionRecord.id == session_id,
                ChatSessionRecord.version == record.version,
            ).update(
                {
                    ChatSessionRecord.expires_at: self._expires_at(),
                    ChatSessionRecord.updated_at: utcnow(),
                    ChatSessionRecord.version: record.version + 1,
                },
                synchronize_session=False,
            )
            if updated != 1:
                db.rollback()
                raise ChatSessionUnavailable()
            db.commit()
            session.version += 1
            return session
        except ChatSessionForbidden:
            raise
        except ChatSessionUnavailable:
            raise
        except (SQLAlchemyError, OSError, ValueError) as error:
            db.rollback()
            raise ChatSessionUnavailable() from error
        finally:
            db.close()

    def save(self, session: ChatSession, user_id: int) -> ChatSession:
        if session.user_id != user_id:
            raise ChatSessionForbidden(
                "La sesión no pertenece al usuario autenticado."
            )
        session.compact()
        db = self.session_factory()
        try:
            record = db.query(ChatSessionRecord).filter(
                ChatSessionRecord.id == session.id
            ).first()
            if record is None:
                raise ChatSessionUnavailable()
            if record.user_id != user_id:
                raise ChatSessionForbidden(
                    "La sesión no pertenece al usuario autenticado."
                )
            updated = db.query(ChatSessionRecord).filter(
                ChatSessionRecord.id == session.id,
                ChatSessionRecord.version == session.version,
            ).update(
                {
                    ChatSessionRecord.account_id: session.account_id,
                    ChatSessionRecord.history_json: json.dumps(
                        session.history, ensure_ascii=False, default=str
                    ),
                    ChatSessionRecord.tool_summaries_json: json.dumps(
                        session.tool_summaries,
                        ensure_ascii=False,
                        default=str,
                    ),
                    ChatSessionRecord.expires_at: self._expires_at(),
                    ChatSessionRecord.updated_at: utcnow(),
                    ChatSessionRecord.version: session.version + 1,
                },
                synchronize_session=False,
            )
            if updated != 1:
                db.rollback()
                raise ChatSessionUnavailable()
            db.commit()
            session.version += 1
            return session
        except ChatSessionForbidden:
            raise
        except ChatSessionUnavailable:
            raise
        except (SQLAlchemyError, OSError, ValueError) as error:
            db.rollback()
            raise ChatSessionUnavailable() from error
        finally:
            db.close()

    def delete(self, session_id: str, user_id: int) -> bool:
        db = self.session_factory()
        try:
            record = db.query(ChatSessionRecord).filter(
                ChatSessionRecord.id == session_id
            ).first()
            if record is None:
                return False
            if record.user_id != user_id:
                raise ChatSessionForbidden(
                    "La sesión no pertenece al usuario autenticado."
                )
            db.delete(record)
            db.commit()
            return True
        except ChatSessionForbidden:
            raise
        except (SQLAlchemyError, OSError, ValueError) as error:
            db.rollback()
            raise ChatSessionUnavailable() from error
        finally:
            db.close()

    def delete_owned(self, session_id: str, user_id: int) -> bool:
        return self.delete(session_id, user_id)


class ChatSessionStore(SqliteChatSessionStore):
    """Nombre estable del almacenamiento de sesiones de la edición desktop."""
