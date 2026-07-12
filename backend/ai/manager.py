from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ai.providers.base import AiRuntimeSettings, AIProvider
from ai.providers.llamacpp import LlamaCppProvider
from ai.providers.ollama import OllamaProvider
from ai.providers.openrouter import OpenRouterProvider
from config import (
    AI_CHAT_BASE_URL,
    AI_CHAT_MODEL,
    AI_CHAT_PROVIDER,
    AI_EMOTION_BASE_URL,
    AI_EMOTION_MODEL,
    AI_EMOTION_PROVIDER,
    AI_INSTALL_MODE,
    LLAMACPP_BASE_URL,
    OPENROUTER_BASE_URL,
)
from models import AiSetting


# Identificadores de los casos de uso soportados por el sistema de IA.
AI_USE_CASE_EMOTION = "emotion"
AI_USE_CASE_CHAT = "chat"

# Conjunto de casos de uso válidos; se usa para validar entradas.
SUPPORTED_AI_USE_CASES = {AI_USE_CASE_EMOTION, AI_USE_CASE_CHAT}


# Registro de proveedores de IA disponibles, indexados por su provider_id.
# Para añadir un nuevo proveedor basta con registrarlo aquí.
PROVIDERS: dict[str, type[AIProvider]] = {
    OllamaProvider.provider_id: OllamaProvider,
    LlamaCppProvider.provider_id: LlamaCppProvider,
    OpenRouterProvider.provider_id: OpenRouterProvider,
}


# Catálogo de modelos recomendados, organizado por caso de uso y proveedor.
# Se expone a través de la API para que el frontend pueda sugerirlos al usuario.
RECOMMENDED_MODELS = {
    "emotion": {
        "ollama": [
            {
                "id": "clasificador_emociones_gemma4:latest",
                "name": "Clasificador actual",
                "description": "Modelo especializado actual para clasificación emocional.",
            },
            {
                "id": "llama3.2:3b",
                "name": "Ligero",
                "description": "Alternativa local rápida para clasificación estructurada.",
            },
        ],
        "llamacpp": [
            {
                "id": "llama-3.2-3b-instruct-q4_k_m.gguf",
                "name": "Ligero GGUF",
                "description": "Modelo pequeño y cuantizado para clasificación con llama.cpp.",
            },
        ],
    },
    "chat": {
        "ollama": [
            {
                "id": "qwen3.5:latest",
                "name": "Qwen 3.5 (recomendado)",
                "description": "Modelo local recomendado para análisis conversacional y tool calling.",
            },
            {
                "id": "llama3.2:3b",
                "name": "Chat ligero",
                "description": "Recomendado para respuestas rápidas en equipos modestos.",
            },
            {
                "id": "qwen2.5:7b",
                "name": "Chat equilibrado",
                "description": "Mejor calidad conversacional, requiere más memoria.",
            },
            {
                "id": "llama3.1:8b",
                "name": "Chat avanzado",
                "description": "Mayor calidad local para equipos potentes.",
            },
        ],
        "llamacpp": [
            {
                "id": "llama-3.2-3b-instruct-q4_k_m.gguf",
                "name": "Chat ligero GGUF",
                "description": "Modelo pequeño y cuantizado para chat con llama.cpp.",
            },
            {
                "id": "qwen2.5-7b-instruct-q4_k_m.gguf",
                "name": "Chat equilibrado GGUF",
                "description": "Mejor calidad conversacional local, requiere más memoria.",
            },
        ],
        "openrouter": [
            {
                "id": "qwen/qwen3.5-9b",
                "name": "Qwen 3.5",
                "description": "Ejemplo de modelo externo; debe habilitarse para tools en el entorno.",
            },
        ],
    },
}


def normalize_use_case(use_case: str) -> str:
    """Normaliza y valida el caso de uso; lanza ValueError si no es soportado."""
    normalized = use_case.strip().lower()
    if normalized not in SUPPORTED_AI_USE_CASES:
        raise ValueError(f"Uso de IA no soportado: {use_case}")
    return normalized


def default_base_url_for_provider(provider: str, use_case: str = AI_USE_CASE_EMOTION) -> str:
    """Devuelve la URL base predeterminada según el proveedor y el caso de uso."""
    if provider == "llamacpp":
        return LLAMACPP_BASE_URL
    if provider == "openrouter":
        return OPENROUTER_BASE_URL
    if normalize_use_case(use_case) == AI_USE_CASE_CHAT:
        return AI_CHAT_BASE_URL
    return AI_EMOTION_BASE_URL


def get_default_ai_settings(use_case: str) -> AiRuntimeSettings:
    """
    Construye AiRuntimeSettings desde las variables de entorno (config.py).
    Se usa como fallback cuando no hay configuración guardada en base de datos.
    """
    use_case = normalize_use_case(use_case)
    if use_case == AI_USE_CASE_CHAT:
        return AiRuntimeSettings(
            use_case=use_case,
            provider=AI_CHAT_PROVIDER,
            model=AI_CHAT_MODEL,
            base_url=AI_CHAT_BASE_URL,
            install_mode=AI_INSTALL_MODE,
            source="env",
        )

    return AiRuntimeSettings(
        use_case=use_case,
        provider=AI_EMOTION_PROVIDER,
        model=AI_EMOTION_MODEL,
        base_url=AI_EMOTION_BASE_URL,
        install_mode=AI_INSTALL_MODE,
        source="env",
    )


def get_effective_ai_settings(use_case: str = AI_USE_CASE_EMOTION, db: Session | None = None) -> AiRuntimeSettings:
    """
    Resuelve la configuración de IA activa para el caso de uso indicado.

    Prioridad:
      1. Registro en base de datos (tabla AiSetting), si se provee sesión.
      2. Variables de entorno (fallback).

    En caso de error de base de datos hace rollback y cae al fallback.
    """
    use_case = normalize_use_case(use_case)
    if db is not None:
        try:
            stored = db.query(AiSetting).filter(AiSetting.use_case == use_case).first()
            if stored is not None:
                return AiRuntimeSettings(
                    use_case=stored.use_case,
                    provider=stored.provider,
                    model=stored.model,
                    base_url=stored.base_url.rstrip("/"),
                    install_mode=stored.install_mode,
                    source="database",
                )
        except SQLAlchemyError:
            db.rollback()

    # Fallback: usar valores de variables de entorno.
    return get_default_ai_settings(use_case)


def get_provider(settings: AiRuntimeSettings) -> AIProvider:
    """Instancia y devuelve el proveedor de IA correspondiente a los settings."""
    provider_class = PROVIDERS.get(settings.provider)
    if provider_class is None:
        raise ValueError(f"Proveedor de IA no soportado: {settings.provider}")
    return provider_class(settings)


def get_langchain_chat_model(settings: AiRuntimeSettings):
    """Obtiene un modelo LangChain validado para el chat con herramientas.

    LangChain es una capa de interoperabilidad. No autoriza usuarios ni accede
    a la base de datos, Redis, archivos o endpoints internos de EmoVest.
    """
    from ai.chat_models import validate_tool_calling_model

    return validate_tool_calling_model(settings)


def get_provider_catalog() -> list[dict]:
    """
    Devuelve el catálogo completo de proveedores disponibles con sus modelos
    recomendados por caso de uso. Usado por el endpoint de configuración de IA.
    """
    return [
        {
            "id": provider.provider_id,
            "name": provider.display_name,
            "description": provider.description,
            "supports_local_install": provider.supports_local_install,
            "recommended_models": {
                use_case: models_by_provider.get(provider.provider_id, [])
                for use_case, models_by_provider in RECOMMENDED_MODELS.items()
            },
        }
        for provider in PROVIDERS.values()
    ]


def list_recommended_models(provider: str, use_case: str = AI_USE_CASE_EMOTION) -> list[dict]:
    """Devuelve la lista de modelos recomendados para un proveedor y caso de uso dados."""
    use_case = normalize_use_case(use_case)
    return RECOMMENDED_MODELS.get(use_case, {}).get(provider, [])


def list_use_cases() -> list[str]:
    """Devuelve la lista ordenada de casos de uso soportados."""
    return sorted(SUPPORTED_AI_USE_CASES)
