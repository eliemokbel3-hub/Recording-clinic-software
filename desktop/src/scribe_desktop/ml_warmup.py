"""The transcription stack's imports, warmed once per process at app start
(installation plan round 35 MED-001).

The first recording after the 0.1.0 install failed at Start while the live
worker was still loading (its stop timed out a second later): that worker's
FIRST import of numpy, onnxruntime and faster-whisper (with ctranslate2,
tokenizers and av behind it) — new DLLs Windows Defender had not yet
scanned, modules read from the frozen archive — ran beside the microphone
stream. The log could not name the failure; the most likely path is that
an extension module's initialisation held the interpreter lock, which the
PortAudio callback needs to take each block, long enough for the device's
buffer to overflow — and dropped frames fail capture by design
(``CaptureOverflowError``: audio is never dropped silently).

``ImportWarmup`` takes those imports off the recording path: ``app.main``
starts it on its own daemon thread as soon as the single-instance guard is
held, long before a Start in normal use (the failing Start came ten
minutes after launch). While it runs, Start is REFUSED ("still getting
ready" — round 36 MED-001, the practitioner's option (b), 2026-10-03) on the
Session tab and from Chrome, so no recording overlaps these imports — but
only for ``START_HOLD_SECONDS`` after the warm-up began: a warm-up that
hangs never blocks recording longer than that. A Start admitted after the
bound while the warm-up still runs records WITHOUT live transcription (the
main window's live-worker factory returns None until it has finished; the
transcript is made at Finish) — the one remaining overlap, logged by type
if it fails, its audio kept for recovery. A failed warm-up is finished:
Start and the live worker are admitted as before. The warm-up's length is
logged (``ml_warmup duration_ms``). It
imports modules only: no model file is opened, no audio
or session is touched, and nothing connects (the offline kill-switches are
asserted first, exactly as before every other ML import). Every process
that transcribes imports these modules anyway — the warm-up only moves when.
"""

from __future__ import annotations

import importlib
import logging
import threading
import time
from collections.abc import Callable
from functools import partial
from types import ModuleType
from typing import Final

from scribe_desktop.benchmark import assert_offline_env
from scribe_desktop.logging_setup import exception_type_name, log_event

# What the live worker's factories import (``speech.SileroVad``,
# ``transcription.WhisperSpeechProvider``, ``speaker_embedding``) — faster-
# whisper brings ctranslate2, tokenizers and av with it.
WARMED_MODULES: Final[tuple[str, ...]] = ("numpy", "onnxruntime", "faster_whisper")

# How long Start waits on the warm-up at most, from when it began (just after
# launch). The practitioner's bound ("about a minute", round 36 MED-001). The
# frozen spike's cold Whisper load — the imports AND the model — took 5.3 s
# and the prose model's 6.9 s (Task 0.1), so a minute leaves a Defender-
# scanned first launch about ten times that; a hung warm-up costs at most it.
START_HOLD_SECONDS: Final = 60.0

Importer = Callable[[str], ModuleType]


def _import_module(name: str) -> ModuleType:
    return importlib.import_module(name)


def warm_transcription_imports(importer: Importer | None = None) -> None:
    """Import ``WARMED_MODULES`` after asserting the offline environment, and
    turn onnxruntime's telemetry events off as ``speech.SileroVad`` does.
    ``importer`` is the test seam; None is ``importlib.import_module``."""
    assert_offline_env()
    load = importer if importer is not None else _import_module
    for name in WARMED_MODULES:
        module = load(name)
        if name == "onnxruntime":
            module.disable_telemetry_events()


class ImportWarmup:
    """Runs ``warm`` once on a daemon thread. ``finished`` is True once it
    has returned or raised — a failed warm-up admits the live worker as
    before (its own model load then fails and names the batch fallback).
    The outcome is logged as metadata: the state, the duration and, on a
    failure, the exception's type name only. ``warm`` None is
    ``warm_transcription_imports`` with the module's importer as it is at
    CONSTRUCTION (so the tests' pinned importer stays in force on a thread
    that outlives its test). ``clock`` (monotonic seconds) and
    ``hold_seconds`` are the seams of ``holds_start``."""

    def __init__(
        self,
        warm: Callable[[], None] | None = None,
        *,
        logger: logging.Logger | None = None,
        clock: Callable[[], float] = time.monotonic,
        hold_seconds: float = START_HOLD_SECONDS,
    ) -> None:
        self._warm: Callable[[], None] = (
            warm if warm is not None else partial(warm_transcription_imports, _import_module)
        )
        self._logger = logger
        self._clock = clock
        self._hold_seconds = hold_seconds
        self._done = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_at: float | None = None

    def is_finished(self) -> bool:
        """The ``MainWindow(live_ready=…)`` callable: False before ``start``
        and while ``warm`` runs."""
        return self._done.is_set()

    def holds_start(self) -> bool:
        """The ``MainWindow(start_hold=…)`` callable (round 36 MED-001): True
        while the warm-up runs AND less than ``hold_seconds`` have passed
        since it began. False before ``start`` (nothing to wait for), once it
        has finished or failed, and after the bound (a hung warm-up)."""
        began = self._started_at
        if began is None or self._done.is_set():
            return False
        return self._clock() - began < self._hold_seconds

    def wait(self, timeout: float | None = None) -> bool:
        return self._done.wait(timeout)

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("the import warm-up was already started")
        self._thread = threading.Thread(target=self._run, name="scribe-ml-warmup", daemon=True)
        self._started_at = self._clock()
        self._thread.start()

    def _run(self) -> None:
        began = time.monotonic()
        fields: dict[str, str | int] = {"state": "failed"}
        try:
            self._warm()
            fields["state"] = "done"
        except Exception as exc:  # noqa: BLE001 - a warm-up never fails the app
            fields["error_code"] = exception_type_name(type(exc))
        finally:
            try:
                if self._logger is not None:
                    fields["duration_ms"] = int((time.monotonic() - began) * 1000)
                    log_event(self._logger, "ml_warmup", **fields)
            finally:
                self._done.set()
