import unittest
from unittest.mock import MagicMock, patch

from ai.chat_models import ChatModelConfigurationError, validate_tool_calling_model
from ai.providers.base import AiRuntimeSettings


class OllamaChatModelValidationTests(unittest.TestCase):
    def setUp(self):
        self.settings = AiRuntimeSettings(
            use_case="chat",
            provider="ollama",
            model="nomic-embed-text:latest",
            base_url="http://127.0.0.1:11434",
        )

    @patch("ai.chat_models.requests.post")
    def test_rejects_embedding_model_without_text_generation(self, post):
        response = MagicMock()
        response.json.return_value = {"capabilities": ["embedding"]}
        post.return_value = response

        with self.assertRaisesRegex(ChatModelConfigurationError, "no es un LLM agéntico"):
            validate_tool_calling_model(self.settings)

    @patch("ai.chat_models.requests.post")
    def test_rejects_text_model_without_tool_calling(self, post):
        response = MagicMock()
        response.json.return_value = {"capabilities": ["completion"]}
        post.return_value = response

        with self.assertRaisesRegex(ChatModelConfigurationError, "no puede llamar herramientas"):
            validate_tool_calling_model(self.settings)


if __name__ == "__main__":
    unittest.main()
