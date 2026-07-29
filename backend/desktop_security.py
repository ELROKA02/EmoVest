from __future__ import annotations

import os
import secrets
from http import HTTPStatus
from typing import Iterable

from starlette.types import ASGIApp, Message, Receive, Scope, Send


DESKTOP_TOKEN_HEADER = b"x-emovest-desktop-token"
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_DESKTOP_ORIGINS = {
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}


def _header(headers: Iterable[tuple[bytes, bytes]], name: bytes) -> str | None:
    for header_name, value in headers:
        if header_name.lower() == name:
            return value.decode("latin-1")
    return None


def _host_without_port(host_header: str) -> str:
    if host_header.startswith("["):
        closing_bracket = host_header.find("]")
        return host_header[1:closing_bracket] if closing_bracket >= 0 else host_header
    return host_header.rsplit(":", 1)[0] if ":" in host_header else host_header


async def _json_error(send: Send, status_code: int, detail: str) -> None:
    body = ('{"detail":"' + detail + '"}').encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(body)).encode("ascii")),
                (b"cache-control", b"no-store"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class DesktopApiSecurityMiddleware:
    """Protege la API loopback con un secreto efímero entregado por Tauri."""

    def __init__(self, app: ASGIApp, token: str | None = None) -> None:
        self.app = app
        self.token = token or os.getenv("EMOVEST_DESKTOP_TOKEN", "")
        if not self.token:
            raise RuntimeError("EMOVEST_DESKTOP_TOKEN es obligatorio en la edición de escritorio.")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = scope.get("headers", [])
        host_header = _header(headers, b"host") or ""
        if _host_without_port(host_header).lower() not in _LOOPBACK_HOSTS:
            await _json_error(send, HTTPStatus.BAD_REQUEST, "Host local no válido.")
            return

        origin = _header(headers, b"origin")
        if origin and origin not in _DESKTOP_ORIGINS:
            await _json_error(send, HTTPStatus.FORBIDDEN, "Origen no autorizado.")
            return

        # El preflight no incluye todavía el encabezado personalizado. CORS no
        # concede acceso a datos; todas las solicitudes reales exigen el token.
        if scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        supplied_token = _header(headers, DESKTOP_TOKEN_HEADER) or ""
        if not secrets.compare_digest(supplied_token, self.token):
            await _json_error(send, HTTPStatus.UNAUTHORIZED, "Cliente de escritorio no autorizado.")
            return

        await self.app(scope, receive, send)
