from pydantic import ValidationError
import requests

from ai.emotions import Emociones, construir_prompt_emociones
from ai.providers.base import AIProvider

try:
    from ollama import Client
    _OLLAMA_INSTALLED = True
except ImportError:
    Client = None
    _OLLAMA_INSTALLED = False


class OllamaProvider(AIProvider):
    provider_id = "ollama"
    display_name = "Ollama"
    description = "Proveedor local recomendado para instalaciones sencillas."
    supports_local_install = True

    def status(self) -> dict:
        if not _OLLAMA_INSTALLED:
            return {
                "available": False,
                "installed": False,
                "running": False,
                "message": "El paquete Python 'ollama' no esta instalado.",
            }

        try:
            response = requests.get(self.settings.base_url, timeout=5)
            running = response.status_code == 200
        except requests.RequestException:
            running = False

        return {
            "available": running,
            "installed": True,
            "running": running,
            "message": "Ollama esta disponible." if running else "Ollama no responde en la URL configurada.",
        }

    def clasificar_emociones(self, texto: str) -> Emociones:
        if not _OLLAMA_INSTALLED:
            raise RuntimeError("El paquete Python 'ollama' no esta instalado.")

        client = Client(host=self.settings.base_url)
        response = client.chat(
            model=self.settings.model,
            messages=[{"role": "user", "content": construir_prompt_emociones(texto)}],
            format=Emociones.model_json_schema(),
        )

        contenido = response.message.content.strip()
        if not contenido:
            raise ValueError("El modelo no devolvio JSON en message.content.")

        try:
            return Emociones.model_validate_json(contenido)
        except ValidationError as error:
            raise ValueError(f"La respuesta del modelo no cumple el formato esperado: {contenido}") from error

    def generar_respuesta_chat(self, mensaje: str) -> str:
        if not _OLLAMA_INSTALLED:
            raise RuntimeError("El paquete Python 'ollama' no esta instalado.")

        client = Client(host=self.settings.base_url)
        response = client.chat(
            model=self.settings.model,
            messages=[{"role": "user", "content": mensaje}],
        )

        contenido = response.message.content.strip()
        if not contenido:
            raise ValueError("El modelo no devolvio contenido para el chat.")

        return contenido
