"""Background task thread for long-running work (transcription, benchmark).

The GUI thread must never block on ML work; results come back through
queued signal delivery. Error strings surfaced to the UI carry exception
type + message only (structural text — never transcript content) and are
NEVER logged from here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from PySide6.QtCore import QObject, QThread, Signal

# Bounded join used by every screen when dropping a finished task
# (round 42 LOW-015: single-sourced, was a magic 2000 at three sites).
_JOIN_TIMEOUT_MS: Final = 2000


class TaskThread(QThread):
    """Run ``fn`` off the GUI thread; emit ``succeeded`` or ``failed``."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable[[], object], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._fn = fn

    def finish(self, timeout_ms: int = _JOIN_TIMEOUT_MS) -> None:
        """Bounded join of a finished/finishing task before dropping the
        reference (never blocks the GUI thread indefinitely)."""
        self.wait(timeout_ms)

    def run(self) -> None:  # QThread entry point (worker thread)
        try:
            result = self._fn()
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI, never swallowed
            self.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        self.succeeded.emit(result)
