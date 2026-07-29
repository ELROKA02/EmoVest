"""Public lifecycle facade used by FastAPI and desktop diagnostics."""

from queueing.runner import (
    get_background_services_health,
    get_queue_snapshot,
    start_background_services,
    stop_background_services,
    wake_background_services,
)

__all__ = [
    "get_background_services_health",
    "get_queue_snapshot",
    "start_background_services",
    "stop_background_services",
    "wake_background_services",
]
