"""GUI-free view logic for the Step 10 screens (unit-testable without Qt).

Everything here is pure logic or thin composition over the real Phase-2
modules (session/session_store/speech/transcription/benchmark). Nothing
in this module may log or persist clinical text: transcript rendering
returns a string for DISPLAY ONLY.
"""

from __future__ import annotations

import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import RecordingSession, SessionState
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    KEY_FILENAME,
    RECOVERY_WINDOW,
    SessionStoreError,
    default_sessions_root,
    read_store_header,
    store_has_footer,
)
from scribe_desktop.speech import SileroVad, vad_model_available
from scribe_desktop.transcription import (
    DEFAULT_WHISPER_MODEL,
    RecoveryOutcome,
    TranscriptDocument,
    WhisperSpeechProvider,
    recover_session_transcription,
    resolve_whisper_model,
    transcribe_session,
    whisper_model_available,
)

_SESSION_ID_RE = re.compile(r"^[0-9a-f]{32}$")

# Binding Step-10 note (PR-HIGH-007 residual): shown whenever a recovered
# store carries no complete Finish footer.
UNFINISHED_STORE_WARNING = (
    "Warning: recording did not finish cleanly; the tail may be missing."
)


class SessionControllerLike(Protocol):
    """The controller surface the screens depend on (fakes in tests)."""

    @property
    def state(self) -> SessionState: ...

    @property
    def level(self) -> float: ...

    @property
    def session(self) -> RecordingSession | None: ...

    def start(self, device_id: int) -> RecordingSession: ...

    def pause(self) -> RecordingSession: ...

    def resume(self) -> RecordingSession: ...

    def finish(self) -> RecordingSession: ...

    def transcribe(
        self, transcriber: Callable[[Path, SessionCrypto], object]
    ) -> RecordingSession: ...

    def complete(self) -> RecordingSession: ...

    def discard(self) -> RecordingSession: ...

    def active_session_ids(self) -> frozenset[str]: ...


# ---------------------------------------------------------------------------
# State-driven control enablement (session screen).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ControlSet:
    start: bool = False
    pause: bool = False
    resume: bool = False
    finish: bool = False
    discard: bool = False


_CONTROLS: dict[SessionState, ControlSet] = {
    SessionState.IDLE: ControlSet(start=True),
    SessionState.RECORDING: ControlSet(pause=True, finish=True, discard=True),
    SessionState.PAUSED: ControlSet(resume=True, finish=True, discard=True),
    # While PROCESSING a transcription run is (or is about to be) in
    # flight: everything stays disabled until it queues or fails
    # (PR-HIGH-006: never race Discard against an in-flight transcribe).
    SessionState.PROCESSING: ControlSet(),
    # Complete/Discard for a queued session live on the transcript view.
    SessionState.QUEUED: ControlSet(),
    SessionState.FAILED: ControlSet(discard=True),
    SessionState.WRITTEN: ControlSet(start=True),
    SessionState.DISCARDED: ControlSet(start=True),
    SessionState.EXPIRED: ControlSet(start=True),
}


def controls_for_state(state: SessionState) -> ControlSet:
    return _CONTROLS[state]


# ---------------------------------------------------------------------------
# Recovery screen model (Flow 3: list recoverable stores on disk).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecoverableSessionInfo:
    session_id: str
    directory: Path
    created_at: float | None  # POSIX seconds; None when unreadable
    store_finished: bool  # False -> UNFINISHED_STORE_WARNING must be shown
    has_audio: bool


def list_recoverable_sessions(
    root: Path, active_session_ids: frozenset[str] = frozenset()
) -> list[RecoverableSessionInfo]:
    """Session dirs with live DPAPI custody, excluding the active session.

    Mirrors the sweep's discipline: only well-formed session-id directory
    names are considered, and nothing here deletes anything. A directory
    whose key blob cannot be statted is listed conservatively (the sweep,
    not the UI, decides orphan GC).
    """
    infos: list[RecoverableSessionInfo] = []
    if not root.is_dir():
        return infos
    now = time.time()
    for child in sorted(root.iterdir()):
        if not child.is_dir() or not _SESSION_ID_RE.fullmatch(child.name):
            continue
        if child.name in active_session_ids:
            continue
        key_path = child / KEY_FILENAME
        key_mtime: float | None = None
        try:
            key_stat = key_path.stat()
            if key_stat.st_size <= 0:
                continue  # cryptographically dead; the sweep will GC it
            key_mtime = key_stat.st_mtime
        except FileNotFoundError:
            continue  # orphan dir; sweep territory
        except OSError:
            pass  # transient stat trouble: list conservatively
        audio_path = child / AUDIO_FILENAME
        has_audio = audio_path.is_file()
        created_at: float | None = None
        store_finished = False
        if has_audio:
            try:
                created_at = read_store_header(audio_path).created_at
            except (SessionStoreError, OSError):
                created_at = None
            try:
                store_finished = store_has_footer(audio_path)
            except (SessionStoreError, OSError):
                store_finished = False
        # PR round 18: the 24 h cap applies to the LISTING too, not only the
        # sweep — never offer recovery of a session past its window. Same
        # fail-safe posture as the sweep: earliest trusted timestamp wins;
        # readable-but-untrusted values fail closed (not listed).
        readable = [t for t in (created_at, key_mtime) if t is not None]
        trusted = [t for t in readable if math.isfinite(t) and t <= now]
        if trusted:
            if now - min(trusted) >= RECOVERY_WINDOW.total_seconds():
                continue  # expired; the sweep destroys it
        elif readable:
            continue  # untrusted timestamps: fail closed, sweep decides
        infos.append(
            RecoverableSessionInfo(
                session_id=child.name,
                directory=child,
                created_at=created_at,
                store_finished=store_finished,
                has_audio=has_audio,
            )
        )
    return infos


# ---------------------------------------------------------------------------
# Transcript rendering (display only — never persisted, never logged).
# ---------------------------------------------------------------------------


def format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def format_transcript_text(document: TranscriptDocument) -> str:
    """Render a transcript for the inspection view: speaker labels visible
    on every segment, uncertain words marked as ``[word?]``."""
    lines: list[str] = []
    for segment in document.transcript_segments:
        span = (
            f"[{format_timestamp(segment.start_seconds)}"
            f"-{format_timestamp(segment.end_seconds)}]"
        )
        words = " ".join(
            f"[{word.word_text}?]" if word.uncertain else word.word_text
            for word in segment.transcript_words
        )
        lines.append(f"{span} {segment.speaker}: {words}")
    if not lines:
        return "(no speech detected)"
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Benchmark / model report panel content.
# ---------------------------------------------------------------------------


def model_report_lines() -> list[str]:
    """Model-readiness lines for the microphone screen's report panel.

    Step 13 fallback policy: when the default (medium) snapshot is absent
    but the fallback (small) is present, the pipeline degrades to the
    fallback and this report says so VISIBLY — the clinician must never
    discover the quality difference by surprise.
    """
    resolved = resolve_whisper_model()
    missing = "MISSING - run scripts/setup-models.py"
    if whisper_model_available(DEFAULT_WHISPER_MODEL):
        whisper_line = f"Whisper model ({DEFAULT_WHISPER_MODEL}): ready"
    elif resolved != DEFAULT_WHISPER_MODEL and whisper_model_available(resolved):
        whisper_line = (
            f"Whisper model ({DEFAULT_WHISPER_MODEL}): MISSING - using "
            f"fallback {resolved}; run scripts/setup-models.py for "
            f"{DEFAULT_WHISPER_MODEL}"
        )
    else:
        whisper_line = f"Whisper model ({DEFAULT_WHISPER_MODEL}): {missing}"
    vad_ready = vad_model_available()
    return [
        whisper_line,
        "VAD model (silero): " + ("ready" if vad_ready else missing),
    ]


def models_ready() -> bool:
    """True when a USABLE whisper model (default or fallback) and the VAD
    model are both locally complete."""
    return whisper_model_available(resolve_whisper_model()) and vad_model_available()


# ---------------------------------------------------------------------------
# Pipeline factories (constructed lazily, inside the worker thread).
# ---------------------------------------------------------------------------


def build_transcriber(
    model_name: str | None = None,
) -> Callable[[Path, SessionCrypto], TranscriptDocument]:
    """A ``SessionController.transcribe`` transcriber over the real ML stack.

    Models load inside the call (worker thread) so the GUI thread never
    blocks on CTranslate2/onnxruntime initialisation. ``model_name=None``
    (the default) applies the Step 13 fallback policy at call time via
    ``resolve_whisper_model``; the resolved name is recorded in the
    transcript document so the artifact says which model actually ran.
    """

    def transcriber(session_dir: Path, crypto: SessionCrypto) -> TranscriptDocument:
        name = model_name if model_name is not None else resolve_whisper_model()
        vad = SileroVad()
        provider = WhisperSpeechProvider(model_name=name)
        return transcribe_session(
            session_dir,
            crypto,
            provider,
            vad.frame_probability,
            require_footer=True,
            model_name=name,
        )

    return transcriber


def build_recovery_runner(
    model_name: str | None = None,
) -> Callable[[Path], RecoveryOutcome]:
    """Flow 3 resume-processing over the real ML stack (worker thread).

    Same Step 13 call-time model resolution as ``build_transcriber``.
    """

    def runner(session_dir: Path) -> RecoveryOutcome:
        name = model_name if model_name is not None else resolve_whisper_model()
        vad = SileroVad()
        provider = WhisperSpeechProvider(model_name=name)
        return recover_session_transcription(
            session_dir, provider, vad.frame_probability, model_name=name
        )

    return runner


__all__ = [
    "UNFINISHED_STORE_WARNING",
    "ControlSet",
    "RecoverableSessionInfo",
    "SessionControllerLike",
    "build_recovery_runner",
    "build_transcriber",
    "controls_for_state",
    "default_sessions_root",
    "format_timestamp",
    "format_transcript_text",
    "list_recoverable_sessions",
    "model_report_lines",
    "models_ready",
]
