"""Adaptadores LangChain para el chat de EmoVest.

LangChain solo normaliza mensajes, streaming y tool calling entre proveedores.
No es una frontera de seguridad: la autorización, los límites de ejecución y
las consultas de datos siguen siendo responsabilidad del backend de EmoVest.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import requests

from ai.providers.base import AiRuntimeSettings
from config import (
    LLAMACPP_API_KEY,
    LLAMACPP_TOOL_CALLING_MODELS,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_TOOL_CALLING_MODELS,
)


class ChatModelConfigurationError(ValueError):
    """El proveedor o el modelo no cumple el contrato seguro del chat."""


class ChatModelUnavailable(RuntimeError):
    """No fue posible verificar o inicializar el proveedor de chat."""


_TOOL_CAPABILITY_PROBE = {
    "name": "consulta_segura_de_prueba",
    "description": "Herramienta interna de comprobacion de compatibilidad.",
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}


def _openai_base_url(base_url: str) -> str:
    """Normaliza una URL OpenAI-compatible sin duplicar el sufijo /v1."""
    normalized = base_url.rstrip("/")
    return normalized if normalized.endswith("/v1") else f"{normalized}/v1"


def create_langchain_chat_model(settings: AiRuntimeSettings) -> Any:
    """Devuelve el modelo LangChain para los proveedores permitidos.

    La función no ejecuta prompts ni concede acceso a recursos de EmoVest.
    """
    provider = settings.provider.strip().lower()
    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as error:  # pragma: no cover - depende de instalación
            raise ChatModelUnavailable("Falta la integración langchain-ollama.") from error
        return ChatOllama(model=settings.model, base_url=settings.base_url)

    if provider in {"llamacpp", "openrouter"}:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as error:  # pragma: no cover - depende de instalación
            raise ChatModelUnavailable("Falta la integración langchain-openai.") from error

        if provider == "openrouter":
            if not OPENROUTER_API_KEY:
                raise ChatModelConfigurationError("OPENROUTER_API_KEY no está configurada.")
            base_url = settings.base_url or OPENROUTER_BASE_URL
            api_key = OPENROUTER_API_KEY
        else:
            base_url = settings.base_url
            # llama-server suele ignorar la clave, pero ChatOpenAI exige una.
            api_key = LLAMACPP_API_KEY or "llamacpp-local"

        return ChatOpenAI(model=settings.model, base_url=_openai_base_url(base_url), api_key=api_key)

    raise ChatModelConfigurationError(f"Proveedor de chat no soportado: {settings.provider}")


def _ollama_declares_tools(settings: AiRuntimeSettings) -> bool:
    """Consulta la capacidad declarada por Ollama sin enviar un mensaje."""
    try:
        response = requests.post(
            f"{settings.base_url.rstrip('/')}/api/show",
            json={"name": settings.model},
            timeout=5,
        )
        response.raise_for_status()
        capabilities = response.json().get("capabilities", [])
    except (requests.RequestException, ValueError) as error:
        raise ChatModelUnavailable("No se pudo verificar la capacidad de herramientas de Ollama.") from error
    return "tools" in capabilities


def _configured_tool_models(provider: str) -> set[str]:
    if provider == "llamacpp":
        return LLAMACPP_TOOL_CALLING_MODELS
    if provider == "openrouter":
        return OPENROUTER_TOOL_CALLING_MODELS
    return set()


def validate_tool_calling_model(settings: AiRuntimeSettings) -> Any:
    """Crea y valida un modelo antes de iniciar una conversación.

    Para Ollama se verifica la capacidad real declarada por el servidor. Para
    proveedores OpenAI-compatible se exige que el modelo figure en la lista de
    capacidades configurada por el despliegue, además de probar ``bind_tools``.
    Esto evita asumir soporte de tools basándonos solo en el nombre del modelo.
    """
    if settings.use_case != "chat":
        raise ChatModelConfigurationError("Las herramientas solo están habilitadas para el caso de uso chat.")

    provider = settings.provider.strip().lower()
    if provider == "ollama":
        if not _ollama_declares_tools(settings):
            raise ChatModelConfigurationError(
                f"El modelo Ollama configurado no declara soporte de tools: {settings.model}"
            )
    elif settings.model not in _configured_tool_models(provider):
        raise ChatModelConfigurationError(
            f"El modelo configurado no está autorizado para tool calling en {provider}."
        )

    model = create_langchain_chat_model(settings)
    try:
        # bind_tools comprueba que el adaptador puede serializar el contrato de
        # herramientas; no ejecuta la herramienta ni da acceso a datos.
        model.bind_tools([_TOOL_CAPABILITY_PROBE])
    except Exception as error:
        raise ChatModelConfigurationError(
            f"El proveedor/modelo configurado no admite tool calling de LangChain."
        ) from error
    return model


def bind_internal_tools(model: Any, tools: Sequence[Any]) -> Any:
    """Enlaza únicamente herramientas internas ya construidas por el backend."""
    try:
        return model.bind_tools(list(tools))
    except Exception as error:
        raise ChatModelConfigurationError("No se pudieron enlazar las herramientas internas.") from error
