from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class EmotionJobReceipt:
    id: str
    backend: str
    idempotency_key: str
    operation_id: int
    text: str


class EmotionQueueAdapter(Protocol):
    def stage(self, db: Session, operation_id: int, text: str) -> EmotionJobReceipt:
        """Prepare a job without making it visible before the database commit."""

    def dispatch(self, receipt: EmotionJobReceipt) -> None:
        """Notify or enqueue a job after the transaction that created it commits."""
