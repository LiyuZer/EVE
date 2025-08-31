from __future__ import annotations

import time
from typing import Optional

__all__ = ["CooldownGate"]


class CooldownGate:
    """Simple time-based cooldown gate.

    - trip(): start a cooldown window (now -> now + seconds)
    - in_cooldown(): True if now is still within the cooldown window
    - should_attempt(): inverse of in_cooldown()
    - last_error: optional string message recorded on last trip
    """

    def __init__(self, seconds: float = 3.0) -> None:
        try:
            s = float(seconds)
        except Exception:
            s = 3.0
        self.seconds: float = max(0.0, s)
        self._until: float = 0.0
        self.last_error: Optional[str] = None

    def in_cooldown(self, now: Optional[float] = None) -> bool:
        if now is None:
            now = time.time()
        return now < self._until

    def should_attempt(self, now: Optional[float] = None) -> bool:
        return not self.in_cooldown(now)

    def trip(self, now: Optional[float] = None, message: Optional[str] = None) -> None:
        if now is None:
            now = time.time()
        self._until = now + self.seconds
        if message is not None:
            # Keep only the latest error message for reference
            try:
                self.last_error = str(message)
            except Exception:
                self.last_error = "<error>"
