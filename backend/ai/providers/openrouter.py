"""Proveedor OpenRouter para el chat EVA y clasificación emocional remota."""

import requests
from pydantic import ValidationError

from ai.emotions import Emociones, construir_prompt_emociones
from ai.providers.base import AIProvider
from ai.providers.base import AIInvalidResponse, AIServiceUnavailable
from ai.credentials import get_openrouter_api_key, has_openrouter_api_key


class OpenRouterProvider(AIProvider):
    provider_id = "openrouter"
    display_name = "OpenRouter"
    description = "Proveedor externo OpenAI-compatible para modelos de chat."
    supports_local_install = False

    def status(self) -> dict:
        # No se realiza una llamada remota aquí ni se revela si existe una clave.
        configured = has_openrouter_api_key()
        return {
            "state": "available" if configured else "unreachable",
            "available": configured,
            "installed": True,
            "running": None,
            "model_available": None,
            "api_key_configured": configured,
            "message": (
                (
                    "OpenRouter está configurado; se validará al iniciar una conversación."
                    if self.settings.use_case == "chat"
                    else "OpenRouter está configurado para el análisis emocional remoto."
                )
                if configured else "Falta la API key de OpenRouter."
            ),
        }

    def clasificar_emociones(self, texto: str):
        api_key = get_openrouter_api_key()
        if not api_key:
            raise AIServiceUnavailable("Falta la API key de OpenRouter.")

        try:
            request_payload = {
                "model": self.settings.model,
                "messages": [{"role": "user", "content": construir_prompt_emociones(texto)}],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            }
            response = requests.post(
                f"{self.settings.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=request_payload,
                timeout=120,
            )
            # Algunos modelos económicos no implementan JSON mode. El prompt
            # ya exige JSON y la respuesta se valida estrictamente después.
            if response.status_code in {400, 422}:
                request_payload.pop("response_format")
                response = requests.post(
                    f"{self.settings.base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=request_payload,
                    timeout=120,
                )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as error:
            raise AIServiceUnavailable("OpenRouter no pudo procesar el análisis emocional.") from error

        try:
            return Emociones.model_validate_json(content)
        except (ValidationError, ValueError) as error:
            raise AIInvalidResponse("La respuesta de OpenRouter no cumple el formato emocional esperado.") from error

    def generar_respuesta_chat(self, mensaje: str) -> str:
        # El endpoint histórico conserva su contrato; la ruta nueva usará
        # LangChain y streaming en lugar de este método.
        raise RuntimeError("El chat OpenRouter requiere el flujo LangChain con herramientas.")
