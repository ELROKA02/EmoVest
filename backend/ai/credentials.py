"""Almacenamiento local cifrado de credenciales de proveedores remotos."""

from __future__ import annotations

import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from config import APP_CONFIG_DIR, OPENROUTER_API_KEY


_VAULT_FILE = "ai-credentials.vault"
_KEY_FILE = "ai-credentials.key"
_OPENROUTER_KEY = "openrouter_api_key"


def _path(name: str) -> Path:
    return APP_CONFIG_DIR / name


def _read_or_create_key() -> bytes:
    path = _path(_KEY_FILE)
    try:
        return path.read_bytes().strip()
    except FileNotFoundError:
        key = Fernet.generate_key()
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as key_file:
            key_file.write(key)
        return key


def _read_vault() -> dict[str, str]:
    path = _path(_VAULT_FILE)
    try:
        encrypted = path.read_bytes()
    except FileNotFoundError:
        return {}
    try:
        data = json.loads(Fernet(_read_or_create_key()).decrypt(encrypted))
    except (InvalidToken, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("No se pudo descifrar la configuración segura de IA.") from error
    if not isinstance(data, dict):
        raise RuntimeError("La configuración segura de IA no es válida.")
    return {key: value for key, value in data.items() if isinstance(value, str)}


def _write_vault(values: dict[str, str]) -> None:
    path = _path(_VAULT_FILE)
    payload = json.dumps(values, separators=(",", ":")).encode("utf-8")
    encrypted = Fernet(_read_or_create_key()).encrypt(payload)
    temporary = path.with_suffix(".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "wb") as vault_file:
        vault_file.write(encrypted)
    os.replace(temporary, path)


def get_openrouter_api_key() -> str:
    """Obtiene la credencial guardada localmente o el fallback de entorno."""
    return _read_vault().get(_OPENROUTER_KEY, "") or OPENROUTER_API_KEY


def has_openrouter_api_key() -> bool:
    return bool(get_openrouter_api_key())


def save_openrouter_api_key(api_key: str) -> None:
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("La API key de OpenRouter no puede estar vacía.")
    vault = _read_vault()
    vault[_OPENROUTER_KEY] = api_key
    _write_vault(vault)


def delete_openrouter_api_key() -> None:
    vault = _read_vault()
    if _OPENROUTER_KEY not in vault:
        return
    del vault[_OPENROUTER_KEY]
    _write_vault(vault)
