import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ai import credentials
from ai.openrouter import OpenRouterUnavailable, list_tool_models, validate_tool_model


class CredentialVaultTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)
        self.path_patch = patch.object(credentials, "_path", side_effect=lambda name: self.path / name)
        self.path_patch.start()

    def tearDown(self):
        self.path_patch.stop()
        self.directory.cleanup()

    def test_saves_encrypted_key_without_returning_plaintext(self):
        credentials.save_openrouter_api_key("sk-or-test-secret")

        self.assertEqual(credentials.get_openrouter_api_key(), "sk-or-test-secret")
        self.assertNotIn("sk-or-test-secret", (self.path / "ai-credentials.vault").read_text())

    def test_deletes_stored_key(self):
        credentials.save_openrouter_api_key("sk-or-test-secret")
        credentials.delete_openrouter_api_key()

        with patch.object(credentials, "OPENROUTER_API_KEY", ""):
            self.assertEqual(credentials.get_openrouter_api_key(), "")


class OpenRouterModelsTests(unittest.TestCase):
    @patch("ai.openrouter.requests.get")
    def test_lists_only_tool_capable_models(self, get):
        response = MagicMock()
        response.json.return_value = {"data": [
            {"id": "vendor/text-tools", "name": "Text tools", "supported_parameters": ["tools"]},
            {"id": "vendor/no-tools", "supported_parameters": ["temperature"]},
        ]}
        get.return_value = response

        self.assertEqual(
            list_tool_models("https://openrouter.ai/api/v1", "sk-or-test"),
            [{"id": "vendor/text-tools", "name": "Text tools"}],
        )

    @patch("ai.openrouter.requests.get")
    def test_rejects_manual_model_without_tools(self, get):
        response = MagicMock()
        response.json.return_value = {"data": []}
        get.return_value = response

        with self.assertRaises(OpenRouterUnavailable):
            validate_tool_model("https://openrouter.ai/api/v1", "sk-or-test", "vendor/no-tools")
