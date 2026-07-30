from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

import uvicorn


_instance_lock_file = None
_ERROR_PREFIX = "EMOVEST_ERROR "
_parent_watchdog_lock = threading.Lock()
_watchdog_requested_shutdown = False
_parent_shutdown_callback: Callable[[], None] | None = None
_parent_shutdown_finished = threading.Event()


def _request_watchdog_shutdown() -> None:
    global _watchdog_requested_shutdown
    with _parent_watchdog_lock:
        _watchdog_requested_shutdown = True
        callback = _parent_shutdown_callback
    if callback is not None:
        try:
            callback()
        except RuntimeError:
            logging.getLogger(__name__).exception(
                "El loop local ya no aceptó la solicitud de cierre del watchdog."
            )

    # Durante migraciones todavía no existe el evento asyncio de apagado. El
    # límite evita que un hijo PyInstaller escapado permanezca huérfano.
    if not _parent_shutdown_finished.wait(5):
        os._exit(0)


def _wait_for_windows_parent(parent_handle: int) -> None:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    try:
        wait_result = kernel32.WaitForSingleObject(parent_handle, 0xFFFFFFFF)
    finally:
        kernel32.CloseHandle(parent_handle)

    if wait_result != 0:
        logging.getLogger(__name__).error(
            "El watchdog no pudo esperar al proceso de escritorio (resultado %s).",
            wait_result,
        )
        return
    _request_watchdog_shutdown()


def _wait_for_cancel_file(cancel_file: Path) -> None:
    while not _parent_shutdown_finished.wait(0.1):
        if not cancel_file.exists():
            continue
        try:
            cancel_file.unlink()
        except FileNotFoundError:
            continue
        _request_watchdog_shutdown()
        return


def _start_windows_parent_watchdog() -> None:
    if os.name != "nt":
        return

    raw_parent_pid = os.getenv("EMOVEST_DESKTOP_PARENT_PID")
    if raw_parent_pid is None:
        return
    try:
        parent_pid = int(raw_parent_pid)
    except ValueError as error:
        raise RuntimeError("EMOVEST_DESKTOP_PARENT_PID no es válido.") from error
    if parent_pid <= 0:
        raise RuntimeError("EMOVEST_DESKTOP_PARENT_PID no es válido.")

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    parent_handle = kernel32.OpenProcess(0x00100000, False, parent_pid)
    if not parent_handle:
        raise RuntimeError("El proceso de escritorio terminó antes que el servicio local.")

    threading.Thread(
        target=_wait_for_windows_parent,
        args=(parent_handle,),
        name="emovest-parent-watchdog",
        daemon=True,
    ).start()


def _start_cancel_watchdog() -> None:
    raw_cancel_file = os.getenv("EMOVEST_DESKTOP_CANCEL_FILE")
    if raw_cancel_file is None:
        return
    cancel_file = Path(raw_cancel_file).expanduser().resolve()
    threading.Thread(
        target=_wait_for_cancel_file,
        args=(cancel_file,),
        name="emovest-cancel-watchdog",
        daemon=True,
    ).start()


def _register_parent_shutdown(callback: Callable[[], None]) -> None:
    global _parent_shutdown_callback
    with _parent_watchdog_lock:
        _parent_shutdown_callback = callback
        shutdown_already_requested = _watchdog_requested_shutdown
    if shutdown_already_requested:
        callback()


def _required_path(env_name: str) -> Path:
    value = os.getenv(env_name)
    if not value:
        raise RuntimeError(f"{env_name} es obligatorio para iniciar EmoVest.")
    path = Path(value).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _acquire_instance_lock(data_dir: Path) -> None:
    """Impide migraciones/sidecars simultáneos sobre el mismo perfil local."""

    global _instance_lock_file
    lock_file = (data_dir / ".instance.lock").open("a+b")
    lock_file.seek(0, os.SEEK_END)
    if lock_file.tell() == 0:
        lock_file.write(b"\0")
        lock_file.flush()
    lock_file.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        lock_file.close()
        raise RuntimeError("EmoVest ya está abierto para este usuario.") from error
    _instance_lock_file = lock_file


def _configure_logging() -> None:
    log_dir = _required_path("EMOVEST_LOG_DIR")
    log_file = log_dir / "emovest.log"
    handler = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def _bind_loopback_socket() -> socket.socket:
    host = os.getenv("EMOVEST_DESKTOP_HOST", "127.0.0.1")
    if host != "127.0.0.1":
        raise RuntimeError("La API de escritorio solo puede escuchar en 127.0.0.1.")

    requested_port = int(os.getenv("EMOVEST_DESKTOP_PORT", "0"))
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, requested_port))
    server_socket.set_inheritable(True)
    return server_socket


async def _serve() -> int:
    os.environ["APP_MODE"] = "desktop"
    data_dir = _required_path("EMOVEST_DATA_DIR")
    _acquire_instance_lock(data_dir)
    _required_path("EMOVEST_CONFIG_DIR")
    _required_path("EMOVEST_BACKUP_DIR")
    _configure_logging()

    # Las migraciones deben terminar antes de abrir el puerto a la interfaz.
    from migration_manager import prepare_database

    prepare_database()

    server_socket = _bind_loopback_socket()
    port = int(server_socket.getsockname()[1])

    from app import app

    shutdown_requested = asyncio.Event()
    app.state.shutdown_requested = shutdown_requested
    loop = asyncio.get_running_loop()
    _register_parent_shutdown(
        lambda: loop.call_soon_threadsafe(shutdown_requested.set)
    )

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        access_log=False,
        log_config=None,
        server_header=False,
        date_header=False,
    )
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve(sockets=[server_socket]))

    while not server.started:
        if server_task.done():
            return int(server_task.exception() is not None)
        await asyncio.sleep(0.025)

    # Única salida de protocolo. Nunca contiene secretos, rutas o datos.
    sys.stdout.write("EMOVEST_READY " + json.dumps({"port": port}, separators=(",", ":")) + "\n")
    sys.stdout.flush()

    shutdown_task = asyncio.create_task(shutdown_requested.wait())
    done, _pending = await asyncio.wait(
        {server_task, shutdown_task},
        return_when=asyncio.FIRST_COMPLETED,
    )
    if shutdown_task in done and not server_task.done():
        server.should_exit = True
        await server_task
    else:
        shutdown_task.cancel()
    return 0


def main() -> None:
    try:
        _start_windows_parent_watchdog()
        _start_cancel_watchdog()
        raise SystemExit(asyncio.run(_serve()))
    except KeyboardInterrupt:
        raise SystemExit(0) from None
    except Exception as error:
        logging.getLogger(__name__).exception("No se pudo iniciar el sidecar de EmoVest.")
        payload = {
            "code": "startup_failed",
            "message": "No se pudo preparar el servicio local de EmoVest.",
            "recoverable": True,
        }
        try:
            from migration_manager import MigrationError

            if isinstance(error, MigrationError):
                payload = {
                    "code": error.code,
                    "message": str(error),
                    "recoverable": error.recoverable,
                    "backup_path": (
                        str(error.backup_path)
                        if error.backup_path is not None
                        else None
                    ),
                }
        except Exception:
            pass
        sys.stdout.write(_ERROR_PREFIX + json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()
        raise SystemExit(1) from None
    finally:
        _parent_shutdown_finished.set()


if __name__ == "__main__":
    main()
