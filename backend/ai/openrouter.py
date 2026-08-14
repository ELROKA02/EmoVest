"""Cliente mínimo del catálogo de OpenRouter usado por los ajustes de EVA."""

from __future__ import annotations

import requests


class OpenRouterUnavailable(RuntimeError):
    pass


def list_tool_models(base_url: str, api_key: str) -> list[dict[str, str]]:
    if not api_key:
        raise OpenRouterUnavailable("Configura una API key de OpenRouter antes de cargar modelos.")
    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/models",
            params={"supported_parameters": "tools", "output_modalities": "text"},
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
            and "tools" in item.get("supported_parameters", [])
        ],
        key=lambda item: item["name"].lower(),
    )


def validate_tool_model(base_url: str, api_key: str, model: str) -> None:
    if model not in {item["id"] for item in list_tool_models(base_url, api_key)}:
        raise OpenRouterUnavailable(
            "El modelo seleccionado no está disponible o no admite herramientas para EVA."
        )
