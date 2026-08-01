import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


from ai.providers.base import AiRuntimeSettings
from ai.providers.ollama import OllamaProvider


class OllamaStatusTests(unittest.TestCase):
    def setUp(self):
        self.provider = OllamaProvider(AiRuntimeSettings(
            use_case="emotion",
            provider="ollama",
            model="emociones:latest",
            base_url="http://127.0.0.1:11434",
        ))

    @patch.object(OllamaProvider, "_local_executable", return_value=None)
    @patch(
        "ai.providers.ollama.Client",
    )
    def test_reports_not_installed_on_loopback(self, client, _executable):
        client.return_value.list.side_effect = ConnectionError("connection failed")
        status = self.provider.status()

        self.assertEqual(status["state"], "not_installed")
        self.assertFalse(status["available"])
        self.assertFalse(status["installed"])

    @patch.object(
        OllamaProvider,
        "_local_executable",
        return_value=Path("C:/Ollama/ollama.exe"),
    )
    @patch(
        "ai.providers.ollama.Client",
    )
    def test_reports_service_stopped_when_executable_exists(self, client, _executable):
        client.return_value.list.side_effect = ConnectionError("connection failed")
        status = self.provider.status()

        self.assertEqual(status["state"], "service_stopped")
        self.assertTrue(status["installed"])
        self.assertFalse(status["running"])

    @patch.object(
        OllamaProvider,
        "_local_executable",
        return_value=Path("C:/Ollama/ollama.exe"),
    )
    @patch("ai.providers.ollama.Client")
    def test_reports_missing_model(self, client, _executable):
        client.return_value.list.return_value.models = [
            MagicMock(model="otro:latest"),
        ]

        status = self.provider.status()

        self.assertEqual(status["state"], "model_missing")
        self.assertTrue(status["running"])
        self.assertFalse(status["model_available"])
        self.assertEqual(status["models"], ["otro:latest"])

    @patch.object(
        OllamaProvider,
        "_local_executable",
        return_value=Path("C:/Ollama/ollama.exe"),
    )
    @patch("ai.providers.ollama.Client")
    def test_reports_available_only_when_model_exists(self, client, _executable):
        client.return_value.list.return_value.models = [
            MagicMock(model="emociones:latest"),
        ]

        status = self.provider.status()

        self.assertEqual(status["state"], "available")
        self.assertTrue(status["available"])
        self.assertTrue(status["model_available"])
        self.assertEqual(status["models"], ["emociones:latest"])


if __name__ == "__main__":
    unittest.main()
