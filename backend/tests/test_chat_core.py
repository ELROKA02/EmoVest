import unittest
from unittest.mock import patch

from ai.chat_agent import ChatAgentService, MAX_TOOL_ROUNDS, run_chat_agent
from ai.chat_sessions import ChatSessionForbidden, ChatSessionStore
from ai.chat_tools import ChatExecutionContext


class FakeRedis:
    def __init__(self):
        self.values = {}

    def setex(self, key, _ttl, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        return int(self.values.pop(key, None) is not None)


class FakeResponse:
    def __init__(self, calls):
        self.tool_calls = calls
        self.content = ""


class FakeTextChunk:
    def __init__(self, content):
        self.content = content
        self.tool_calls = []

    def __add__(self, other):
        return FakeTextChunk(self.content + other.content)


class FakeModel:
    def __init__(self):
        self.invocations = 0
        self.last_messages = []

    def bind_tools(self, _tools):
        return self

    def invoke(self, messages):
        self.invocations += 1
        self.last_messages = messages
        return FakeResponse([{
            "id": f"call-{self.invocations}",
            "name": "resumen_resultados",
            "args": {},
        }])


class FakeStreamingModel:
    def bind_tools(self, _tools):
        return self

    def stream(self, _messages):
        yield FakeTextChunk("Hola")
        yield FakeTextChunk(" Samuel")


class FakeDeferredModel:
    def __init__(self):
        self.invocations = 0

    def bind_tools(self, _tools):
        return self

    def stream(self, _messages):
        self.invocations += 1
        if self.invocations == 1:
            yield FakeTextChunk("Ahora procederé a obtener tus resultados de los últimos 30 días.")
            return
        yield FakeTextChunk("¿Qué periodo ")
        yield FakeTextChunk("quieres analizar?")


class FakeTool:
    name = "resumen_resultados"

    def invoke(self, _args):
        return {"account_id": 9, "period_days": 30, "operations": 2, "pnl": 10}


class EmptyQuery:
    def filter(self, *_args):
        return self

    def order_by(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def all(self):
        return []


class EmptyDb:
    def query(self, *_args):
        return EmptyQuery()


class ChatSessionStoreTests(unittest.TestCase):
    def test_only_owner_can_read_or_delete_a_session(self):
        store = ChatSessionStore(redis_client=FakeRedis())
        session = store.create(user_id=7)

        with self.assertRaises(ChatSessionForbidden):
            store.get(session.id, user_id=8)
        with self.assertRaises(ChatSessionForbidden):
            store.delete_owned(session.id, user_id=8)

        self.assertTrue(store.delete_owned(session.id, user_id=7))


class ChatAgentLoopTests(unittest.TestCase):
    def test_first_message_accepts_authenticated_user_name(self):
        service = ChatAgentService(
            db=EmptyDb(),
            session_store=ChatSessionStore(redis_client=FakeRedis()),
        )

        events = list(service.stream(
            mensaje="Analiza mis resultados",
            user_id=1,
            user_name="Samuel",
        ))

        self.assertEqual([event["event"] for event in events], [
            "session", "status", "delta", "evidence", "done",
        ])

    def test_tool_loop_stops_after_four_rounds(self):
        from ai.chat_sessions import ChatSession

        model = FakeModel()
        session = ChatSession(id="test", user_id=1, account_id=9)
        context = ChatExecutionContext(db=None, user_id=1, account_id=9)

        with patch("ai.chat_agent.make_langchain_tools", return_value=[FakeTool()]):
            result = run_chat_agent(
                model=model,
                session=session,
                context=context,
                user_message="Analiza mis resultados",
                user_name="Samuel",
            )

        self.assertEqual(model.invocations, MAX_TOOL_ROUNDS)
        self.assertEqual(len(result.evidence), MAX_TOOL_ROUNDS)
        self.assertIn("limite seguro", result.text)
        self.assertIn('"Samuel"', model.last_messages[0].content)

    def test_final_answer_is_forwarded_as_streaming_deltas(self):
        from ai.chat_sessions import ChatSession

        deltas = []
        with patch("ai.chat_agent.make_langchain_tools", return_value=[FakeTool()]):
            result = run_chat_agent(
                model=FakeStreamingModel(),
                session=ChatSession(id="test", user_id=1, account_id=9),
                context=ChatExecutionContext(db=None, user_id=1, account_id=9),
                user_message="Analiza mis resultados",
                user_name="Samuel",
                on_delta=deltas.append,
            )

        self.assertEqual(deltas, ["Hola", " Samuel"])
        self.assertEqual(result.text, "Hola Samuel")

    def test_future_action_promise_is_discarded_and_retried(self):
        from ai.chat_sessions import ChatSession

        model = FakeDeferredModel()
        deltas = []
        with patch("ai.chat_agent.make_langchain_tools", return_value=[FakeTool()]):
            result = run_chat_agent(
                model=model,
                session=ChatSession(id="test", user_id=1, account_id=9),
                context=ChatExecutionContext(db=None, user_id=1, account_id=9),
                user_message="¿Cómo voy?",
                user_name="Samuel",
                on_delta=deltas.append,
            )

        self.assertEqual(model.invocations, 2)
        self.assertEqual(deltas, ["¿Qué periodo ", "quieres analizar?"])
        self.assertEqual(result.text, "¿Qué periodo quieres analizar?")

    def test_missing_account_does_not_invoke_model(self):
        from ai.chat_sessions import ChatSession

        model = FakeModel()
        result = run_chat_agent(
            model=model,
            session=ChatSession(id="test", user_id=1),
            context=ChatExecutionContext(db=None, user_id=1, account_id=None),
            user_message="Analiza mis resultados",
            user_name="Samuel",
        )

        self.assertEqual(model.invocations, 0)
        self.assertIn("selecciones una cuenta", result.text)


if __name__ == "__main__":
    unittest.main()
