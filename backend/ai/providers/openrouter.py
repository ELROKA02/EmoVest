"""Proveedor OpenRouter para la configuración existente de IA.

Su uso conversacional real se realiza mediante el adaptador LangChain. Esta
clase conserva el contrato histórico de proveedores para la API de ajustes.
"""

from ai.providers.base import AIProvider
from ai.credentials import has_openrouter_api_key


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
                "OpenRouter está configurado; se validará al iniciar una conversación."
                if configured else "Falta la API key de OpenRouter."
            ),
        }

    def clasificar_emociones(self, texto: str):
        raise RuntimeError("OpenRouter no está habilitado para clasificación emocional.")

    def generar_respuesta_chat(self, mensaje: str) -> str:
        # El endpoint histórico conserva su contrato; la ruta nueva usará
        # LangChain y streaming en lugar de este método.
        raise RuntimeError("El chat OpenRouter requiere el flujo LangChain con herramientas.")
