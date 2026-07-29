import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

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
        "ai.providers.ollama.requests.get",
        side_effect=requests.ConnectionError(),
    )
    def test_reports_not_installed_on_loopback(self, _get, _executable):
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
        "ai.providers.ollama.requests.get",
        side_effect=requests.ConnectionError(),
    )
    def test_reports_service_stopped_when_executable_exists(
        self, _get, _executable
    ):
        status = self.provider.status()

        self.assertEqual(status["state"], "service_stopped")
        self.assertTrue(status["installed"])
        self.assertFalse(status["running"])

    @patch.object(
        OllamaProvider,
        "_local_executable",
        return_value=Path("C:/Ollama/ollama.exe"),
    )
    @patch("ai.providers.ollama.requests.get")
    def test_reports_missing_model(self, get, _executable):
        response = MagicMock()
        response.json.return_value = {
            "models": [{"name": "otro:latest"}],
        }
        get.return_value = response

        status = self.provider.status()

        self.assertEqual(status["state"], "model_missing")
        self.assertTrue(status["running"])
        self.assertFalse(status["model_available"])

    @patch.object(
        OllamaProvider,
        "_local_executable",
        return_value=Path("C:/Ollama/ollama.exe"),
    )
    @patch("ai.providers.ollama.requests.get")
    def test_reports_available_only_when_model_exists(self, get, _executable):
        response = MagicMock()
        response.json.return_value = {
            "models": [{"name": "emociones:latest"}],
        }
        get.return_value = response

        status = self.provider.status()

        self.assertEqual(status["state"], "available")
        self.assertTrue(status["available"])
        self.assertTrue(status["model_available"])


if __name__ == "__main__":
    unittest.main()
