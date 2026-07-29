from __future__ import annotations

from functools import lru_cache

import config

from queueing.base import EmotionJobReceipt, EmotionQueueAdapter


def is_desktop_mode() -> bool:
    return str(getattr(config, "APP_MODE", "desktop")).strip().lower() == "desktop"


@lru_cache(maxsize=1)
def get_emotion_queue(mode: str | None = None) -> EmotionQueueAdapter:
    selected_mode = (mode or getattr(config, "APP_MODE", "desktop")).strip().lower()
    if selected_mode != "desktop":
        raise RuntimeError("La edición actual de EmoVest solo admite la cola SQLite.")

    from queueing.sqlite_adapter import SqliteEmotionQueue

    return SqliteEmotionQueue()


__all__ = [
    "EmotionJobReceipt",
    "get_emotion_queue",
    "is_desktop_mode",
]
