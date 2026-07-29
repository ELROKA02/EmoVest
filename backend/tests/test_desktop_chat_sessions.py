import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from ai.chat_sessions import (
    ChatSessionForbidden,
    ChatSessionUnavailable,
    SqliteChatSessionStore,
    purge_expired_chat_sessions,
    utcnow,
)
from database import Base, create_desktop_engine
from models import ChatSessionRecord, Usuario


class DesktopChatSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "chat.sqlite3"
        self.engine = create_desktop_engine(database_path)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        db = self.Session()
        db.add(Usuario(
            id=7,
            nombre="Desktop",
            contrasena="not-a-real-password",
            correo_electronico="desktop@example.test",
        ))
        db.commit()
        db.close()

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_session_survives_store_restart_and_checks_owner(self):
        first_store = SqliteChatSessionStore(self.Session)
        session = first_store.create(user_id=7)
        session.history.append({"role": "user", "content": "Hola"})
        first_store.save(session, user_id=7)

        restarted_store = SqliteChatSessionStore(self.Session)
        restored = restarted_store.get(session.id, user_id=7)

        self.assertEqual(restored.history[-1]["content"], "Hola")
        with self.assertRaises(ChatSessionForbidden):
            restarted_store.get(session.id, user_id=8)

    def test_expired_session_is_deleted(self):
        store = SqliteChatSessionStore(self.Session)
        session = store.create(user_id=7)
        db = self.Session()
        db.query(ChatSessionRecord).filter(
            ChatSessionRecord.id == session.id
        ).update({
            ChatSessionRecord.expires_at: utcnow() - timedelta(seconds=1)
        })
        db.commit()
        db.close()

        self.assertIsNone(store.get(session.id, user_id=7))
        db = self.Session()
        self.assertIsNone(db.get(ChatSessionRecord, session.id))
        db.close()

    def test_periodic_purge_is_bounded_and_preserves_active_sessions(self):
        store = SqliteChatSessionStore(self.Session)
        expired_first = store.create(user_id=7)
        expired_second = store.create(user_id=7)
        active = store.create(user_id=7)
        db = self.Session()
        db.query(ChatSessionRecord).filter(
            ChatSessionRecord.id.in_((expired_first.id, expired_second.id))
        ).update(
            {ChatSessionRecord.expires_at: utcnow() - timedelta(seconds=1)},
            synchronize_session=False,
        )
        db.commit()
        db.close()

        removed = purge_expired_chat_sessions(self.Session, batch_size=1)

        self.assertEqual(removed, 1)
        db = self.Session()
        remaining_ids = {
            session_id for (session_id,) in db.query(ChatSessionRecord.id).all()
        }
        db.close()
        self.assertEqual(
            len({expired_first.id, expired_second.id} & remaining_ids),
            1,
        )
        self.assertIn(active.id, remaining_ids)

    def test_optimistic_version_rejects_stale_overwrite(self):
        store = SqliteChatSessionStore(self.Session)
        session = store.create(user_id=7)
        stale = store.get(session.id, user_id=7)
        current = store.get(session.id, user_id=7)

        stale.history.append({"role": "user", "content": "stale"})
        with self.assertRaises(ChatSessionUnavailable):
            store.save(stale, user_id=7)

        current.history.append({"role": "user", "content": "current"})
        store.save(current, user_id=7)

    def test_corrupt_payload_fails_closed(self):
        store = SqliteChatSessionStore(self.Session)
        session = store.create(user_id=7)
        db = self.Session()
        db.query(ChatSessionRecord).filter(
            ChatSessionRecord.id == session.id
        ).update({ChatSessionRecord.history_json: "not-json"})
        db.commit()
        db.close()

        with self.assertRaises(ChatSessionUnavailable):
            store.get(session.id, user_id=7)


if __name__ == "__main__":
    unittest.main()
