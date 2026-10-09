"""Optional observational trace, independent of transport and application UI."""

import logging
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class TraceEvent:
    """Host monotonic timestamp; raw bytes are wire bytes, never inferred RF timing."""

    sequence: int
    timestamp: float
    kind: str
    exchange_id: int | None = None
    command: int | None = None
    address: int | None = None
    status: int | None = None
    raw: bytes = b""
    detail: str = ""


class TraceEmitter:
    """A synchronous observer must return promptly; observer errors never affect RF I/O."""

    def __init__(self, observer: Callable[[TraceEvent], None] | None = None):
        self.observer = observer
        self.sequence = 0
        self.observer_errors = 0
        self.logger = logging.getLogger("zk_rfid.trace")

    def emit(self, kind: str, **fields) -> TraceEvent:
        self.sequence += 1
        event = TraceEvent(self.sequence, time.monotonic(), kind, **fields)
        self.logger.debug(
            "%s exchange=%s cmd=%s status=%s %s %s",
            kind,
            event.exchange_id,
            event.command,
            event.status,
            event.raw.hex(),
            event.detail,
        )
        if self.observer is not None:
            try:
                self.observer(event)
            except Exception:
                self.observer_errors += 1
                self.logger.debug("Trace observer raised; ignored to preserve I/O", exc_info=True)
        return event
