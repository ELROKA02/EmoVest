import requests
from pydantic import ValidationError

from ai.emotions import Emociones, construir_prompt_emociones
from ai.providers.base import AIProvider


class LlamaCppProvider(AIProvider):
    provider_id = "llamacpp"
    display_name = "llama.cpp"
    description = "Proveedor local avanzado para llama-server y modelos GGUF."
    supports_local_install = True

    def status(self) -> dict:
        try:
            response = requests.get(f"{self.settings.base_url}/health", timeout=5)
            running = response.status_code == 200
        except requests.RequestException:
            running = False

        return {
            "available": running,
            "installed": None,
            "running": running,
            "message": "llama.cpp esta disponible." if running else "llama-server no responde en la URL configurada.",
        }

    def clasificar_emociones(self, texto: str) -> Emociones:
        payload = {
            "model": self.settings.model,
            "messages": [{"role": "user", "content": construir_prompt_emociones(texto)}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }

        response = requests.post(
            f"{self.settings.base_url}/v1/chat/completions",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        contenido = data["choices"][0]["message"]["content"].strip()

        try:
            return Emociones.model_validate_json(contenido)
        except (KeyError, IndexError, ValidationError) as error:
            raise ValueError(f"La respuesta de llama.cpp no cumple el formato esperado: {data}") from error

    def generar_respuesta_chat(self, mensaje: str) -> str:
        payload = {
            "model": self.settings.model,
            "messages": [{"role": "user", "content": mensaje}],
            "temperature": 0.7,
        }

        response = requests.post(
            f"{self.settings.base_url}/v1/chat/completions",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        try:
            contenido = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as error:
            raise ValueError(f"La respuesta de llama.cpp no cumple el formato esperado: {data}") from error

        if not contenido:
            raise ValueError("El modelo no devolvio contenido para el chat.")

        return contenido
