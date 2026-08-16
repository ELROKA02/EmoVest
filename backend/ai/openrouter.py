"""Cliente mínimo del catálogo de OpenRouter usado por los ajustes de EVA."""

from __future__ import annotations

import requests


class OpenRouterUnavailable(RuntimeError):
    pass


def list_models(
    base_url: str,
    api_key: str,
    *,
    require_tools: bool = False,
) -> list[dict[str, str]]:
    if not api_key:
        raise OpenRouterUnavailable("Configura una API key de OpenRouter antes de cargar modelos.")
    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/models",
            params={
                "output_modalities": "text",
                **({"supported_parameters": "tools"} if require_tools else {}),
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        raise OpenRouterUnavailable("No se pudo consultar OpenRouter. Revisa la API key y la conexión.") from error

    models = payload.get("data", []) if isinstance(payload, dict) else []
    return sorted(
        [
            {"id": item["id"], "name": item.get("name") or item["id"]}
            for item in models
            if isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and (not require_tools or "tools" in item.get("supported_parameters", []))
        ],
        key=lambda item: item["name"].lower(),
    )


def list_tool_models(base_url: str, api_key: str) -> list[dict[str, str]]:
    return list_models(base_url, api_key, require_tools=True)


def validate_model(base_url: str, api_key: str, model: str, *, require_tools: bool = False) -> None:
    if model not in {item["id"] for item in list_models(base_url, api_key, require_tools=require_tools)}:
        raise OpenRouterUnavailable(
            (
                "El modelo seleccionado no está disponible o no admite herramientas para EVA."
                if require_tools else "El modelo seleccionado no está disponible en OpenRouter."
            )
        )


def validate_tool_model(base_url: str, api_key: str, model: str) -> None:
    validate_model(base_url, api_key, model, require_tools=True)
