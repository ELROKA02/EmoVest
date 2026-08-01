import os
import shutil
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from ai.emotions import Emociones, construir_prompt_emociones
from ai.providers.base import (
    AIInvalidResponse,
    AIModelMissing,
    AIProvider,
    AIProviderNotInstalled,
    AIServiceUnavailable,
)

try:
    from ollama import Client, RequestError, ResponseError
    _OLLAMA_INSTALLED = True
except ImportError:
    Client = None
    RequestError = Exception
    ResponseError = Exception
    _OLLAMA_INSTALLED = False


class OllamaProvider(AIProvider):
    provider_id = "ollama"
    display_name = "Ollama"
    description = "Proveedor local recomendado para instalaciones sencillas."
    supports_local_install = True

    def _is_loopback(self) -> bool:
        hostname = (urlparse(self.settings.base_url).hostname or "").lower()
        return hostname in {"localhost", "127.0.0.1", "::1"}

    @staticmethod
    def _local_executable() -> Path | None:
        discovered = shutil.which("ollama")
        if discovered:
            return Path(discovered)
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidate = (
                Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe"
            )
            if candidate.is_file():
                return candidate
        return None

    def status(self) -> dict:
        loopback = self._is_loopback()
        executable = self._local_executable() if loopback else None
        try:
            response = Client(host=self.settings.base_url, timeout=3).list()
            models = response.models
            installed_models = {
                model.model.strip()
                for model in models
                if isinstance(getattr(model, "model", None), str)
                and model.model.strip()
            }
        except (ConnectionError, RequestError, ResponseError, ValueError, TypeError):
            if loopback and executable is None:
                return {
                    "state": "not_installed",
                    "available": False,
                    "installed": False,
                    "running": False,
                    "model_available": None,
                    "message": "Ollama no está instalado.",
                    "models": [],
                }
            return {
                "state": "service_stopped" if loopback else "unreachable",
                "available": False,
                "installed": True if loopback else None,
                "running": False,
                "model_available": None,
                "message": (
                    "Ollama está instalado, pero el servicio está detenido."
                    if loopback
                    else "No se puede conectar con el servicio Ollama configurado."
                ),
                "models": [],
            }

        model_available = self.settings.model in installed_models
        if not model_available:
            return {
                "state": "model_missing",
                "available": False,
                "installed": True if loopback else None,
                "running": True,
                "model_available": False,
                "message": "Ollama está activo, pero falta el modelo configurado.",
                "models": sorted(installed_models),
            }
        return {
            "state": "available",
            "available": True,
            "installed": True if loopback else None,
            "running": True,
            "model_available": True,
            "message": "Ollama y el modelo configurado están disponibles.",
            "models": sorted(installed_models),
        }

    def clasificar_emociones(self, texto: str) -> Emociones:
        if not _OLLAMA_INSTALLED:
            raise AIProviderNotInstalled(
                "La integración local de Ollama no está instalada."
            )

        client = Client(host=self.settings.base_url, timeout=120)
        messages = [{"role": "user", "content": construir_prompt_emociones(texto)}]

        try:
            try:
                response = client.chat(
                    model=self.settings.model,
                    messages=messages,
                    format=Emociones.model_json_schema(),
                )
            except ResponseError as error:
                # Some Ollama runtimes intermittently reject JSON Schema
                # grammars. JSON mode remains validated by Pydantic below.
                if (
                    error.status_code != 400
                    or "failed to parse grammar" not in str(error).lower()
                ):
                    raise
                response = client.chat(
                    model=self.settings.model,
                    messages=messages,
                    format="json",
                )
        except ResponseError as error:
            if error.status_code == 404:
                raise AIModelMissing(
                    "El modelo configurado no está instalado en Ollama."
                ) from error
            if error.status_code is not None and error.status_code >= 500:
                raise AIServiceUnavailable(
                    "El servicio Ollama no está disponible temporalmente."
                ) from error
            raise AIInvalidResponse(
                "Ollama rechazó la solicitud de clasificación."
            ) from error
        except Exception as error:
            raise AIServiceUnavailable(
                "No se pudo conectar con el servicio Ollama."
            ) from error

        contenido = response.message.content.strip()
        if not contenido:
            raise AIInvalidResponse(
                "El modelo no devolvió una clasificación válida."
            )

        try:
            return Emociones.model_validate_json(contenido)
        except ValidationError as error:
            # Model output may echo a private trading note; do not include it.
            raise AIInvalidResponse(
                "La respuesta del modelo no cumple el formato esperado."
            ) from error

    def generar_respuesta_chat(self, mensaje: str) -> str:
        if not _OLLAMA_INSTALLED:
            raise AIProviderNotInstalled(
                "La integración local de Ollama no está instalada."
            )

        client = Client(host=self.settings.base_url, timeout=120)
        try:
            response = client.chat(
                model=self.settings.model,
                messages=[{"role": "user", "content": mensaje}],
            )
        except ResponseError as error:
            if error.status_code == 404:
                raise AIModelMissing(
                    "El modelo configurado no está instalado en Ollama."
                ) from error
            raise AIServiceUnavailable(
                "El servicio Ollama no está disponible."
            ) from error
        except Exception as error:
            raise AIServiceUnavailable(
                "No se pudo conectar con el servicio Ollama."
            ) from error

        contenido = response.message.content.strip()
        if not contenido:
            raise AIInvalidResponse(
                "El modelo no devolvió contenido para el chat."
            )
        return contenido
