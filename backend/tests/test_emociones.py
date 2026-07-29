import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ai.emotions import Emociones
from ai.providers.base import AiRuntimeSettings
from ai.providers.ollama import OllamaProvider, ResponseError
from database import Base
from models import Registro_emocional
from routers.ia import guardar_registro_emocional


class FakeEmotionProvider:
    def clasificar_emociones(self, _texto):
        return Emociones(
            confianza=Decimal("10"),
            duda=Decimal("20"),
            euforia=Decimal("30"),
            miedo=Decimal("15"),
            neutral=Decimal("25"),
        )


class GuardarRegistroEmocionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        # Reproduce una instalacion antigua: existe registro_emocional, pero no
        # la tabla ai_settings que consulta la configuracion nueva.
        Base.metadata.tables["operacion"].create(cls.engine)
        Base.metadata.tables["registro_emocional"].create(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.db = self.Session()

    def tearDown(self):
        self.db.query(Registro_emocional).delete()
        self.db.commit()
        self.db.close()

    def test_missing_ai_settings_table_does_not_discard_new_record(self):
        with patch("routers.ia.get_provider", return_value=FakeEmotionProvider()):
            guardar_registro_emocional("Entrada con dudas", 41, self.db)
            self.db.commit()

        registro = self.db.query(Registro_emocional).filter_by(id_operacion=41).one()
        self.assertEqual(registro.confianza, Decimal("0.10"))
        self.assertEqual(registro.duda, Decimal("0.20"))
        self.assertEqual(registro.euforia, Decimal("0.30"))
        self.assertEqual(registro.miedo, Decimal("0.15"))
        self.assertEqual(registro.neutral, Decimal("0.25"))

    def test_provider_error_is_propagated_without_saving_zero_record(self):
        with patch("routers.ia.clasificar_emociones", side_effect=RuntimeError("Ollama caido")):
            with self.assertRaisesRegex(RuntimeError, "Ollama caido"):
                guardar_registro_emocional("Entrada con miedo", 42, self.db)

        self.assertIsNone(
            self.db.query(Registro_emocional).filter_by(id_operacion=42).first()
        )


class WorkerConfigurationTests(unittest.TestCase):
    def test_worker_starts_scheduler_for_delayed_retries(self):
        redis_connection = MagicMock()
        worker_instance = MagicMock()
        connection_context = MagicMock()

        with (
            patch("worker.Redis.from_url", return_value=redis_connection),
            patch("worker.Connection", return_value=connection_context),
            patch("worker.SimpleWorker", return_value=worker_instance),
        ):
            from worker import main

            main()

        worker_instance.work.assert_called_once_with(with_scheduler=True)


class OllamaProviderTests(unittest.TestCase):
    def setUp(self):
        self.provider = OllamaProvider(AiRuntimeSettings(
            use_case="emotion",
            provider="ollama",
            model="clasificador_emociones_gemma4:latest",
            base_url="http://localhost:11434",
            install_mode="manual",
            source="env",
        ))

    def test_grammar_error_falls_back_to_json_mode(self):
        response = MagicMock()
        response.message.content = (
            '{"confianza":10,"duda":20,"euforia":30,"miedo":15,"neutral":25}'
        )
        client = MagicMock()
        client.chat.side_effect = [
            ResponseError("Failed to initialize samplers: failed to parse grammar", 400),
            response,
        ]

        with patch("ai.providers.ollama.Client", return_value=client):
            emociones = self.provider.clasificar_emociones("Entrada con dudas")

        self.assertEqual(emociones.duda, Decimal("20"))
        self.assertEqual(client.chat.call_count, 2)
        self.assertEqual(client.chat.call_args_list[1].kwargs["format"], "json")

    def test_other_ollama_errors_are_propagated_to_rq(self):
        client = MagicMock()
        client.chat.side_effect = ResponseError("Ollama no disponible", 503)

        with patch("ai.providers.ollama.Client", return_value=client):
            with self.assertRaises(ResponseError):
                self.provider.clasificar_emociones("Entrada con miedo")

        client.chat.assert_called_once()


if __name__ == "__main__":
    unittest.main()
