"""Core recording-session types + session state machine (Phase 2 Steps 1+4).

`SessionState` is the real session lifecycle enum from PLAN.md — it
supersedes Phase 1's throwaway `ConnectionState` (now retired).

`RecordingSession` carries the PLAN.md fields: session identifier,
encounter context, encryption-key reference and timestamps. In Phase 2
there is no Chrome-side encounter context yet (that is Phase 5), so
`encounter_context` is optional. `key_reference` is a REFERENCE to the
DPAPI-wrapped key blob (a filesystem path string) — never key material.

Step 4 adds :class:`SessionController` — the state machine wiring
start/pause/resume/finish/discard/Complete across capture ↔ store ↔ key
custody under the plan's binding Concurrency model:

- the capture worker is the SINGLE writer to ``audio.enc`` (it owns the
  chunk-store handle through its sink); the controller only touches the
  store after the worker has fully stopped (Finish footer, Discard close);
- state transitions are serialized through ONE lock; blocking control
  waits (worker barriers/joins) happen OUTSIDE that lock so the worker's
  failure callback can never deadlock against a pause/finish;
- `SessionCrypto` access is guarded by the same serialization: while
  recording only the worker thread encrypts; custody operations
  (complete/discard) run only after the worker is stopped;
- single-active-session invariant: at most one session in
  recording/paused/processing; `active_session_ids` feeds the expiry
  sweep so it skips live sessions by STATE, not mtime.

Disk-full (`StoreWriteError`) and device loss (`DeviceLostError`) route
the session to ``failed`` — RECOVERABLE: the key custody blob and every
durably written chunk remain on disk. Never silent data loss.

Critical Constraint: nothing in this module may hold or log clinical
data; all logging of session events goes through `log_event` with
whitelisted keys only.
"""

from __future__ import annotations

import enum
import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from scribe_desktop.audio_capture import CaptureBackend, CaptureWorker
from scribe_desktop.logging_setup import log_event
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    SessionChunkStore,
    StoreWriteError,
    complete_session,
    default_sessions_root,
    discard_session,
    wrap_key_to_file,
)


class SessionState(enum.StrEnum):
    """PLAN.md session lifecycle states (all nine; machine lands in Step 4)."""

    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    PROCESSING = "processing"
    QUEUED = "queued"
    WRITTEN = "written"
    FAILED = "failed"
    DISCARDED = "discarded"
    EXPIRED = "expired"


# States during which the expiry sweep must never touch a session
# (plan Critical Constraint: sweep skips recording/paused/processing).
ACTIVE_STATES: frozenset[SessionState] = frozenset(
    {SessionState.RECORDING, SessionState.PAUSED, SessionState.PROCESSING}
)

# States a crashed session may be recovered from (recovery screen lists these).
RECOVERABLE_STATES: frozenset[SessionState] = frozenset(
    {SessionState.RECORDING, SessionState.PAUSED, SessionState.PROCESSING, SessionState.FAILED}
)

# Terminal states: no further transitions, key custody already destroyed
# or scheduled for destruction.
TERMINAL_STATES: frozenset[SessionState] = frozenset(
    {SessionState.WRITTEN, SessionState.DISCARDED, SessionState.EXPIRED}
)


def _new_session_id() -> str:
    return uuid.uuid4().hex


def _utc_now() -> datetime:
    return datetime.now(UTC)


class RecordingSession(BaseModel):
    """PLAN.md core type: identifier, encounter context, key reference,
    timestamps. Immutable value object — state transitions produce copies
    via `with_state` so concurrent readers never see partial mutation
    (the single transition lock arrives with the Step 4 machine)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Opaque, non-clinical identifier — exactly uuid4().hex. The strict
    # pattern keeps it safe as a single filesystem path segment
    # (sessions/<id>/) and as whitelisted log metadata (PR-MED-002).
    session_id: str = Field(default_factory=_new_session_id, pattern=r"^[0-9a-f]{32}$")
    # Phase 5 delivers the real EncounterContext from Chrome; until then an
    # opaque optional reference keeps the PLAN.md shape without inventing data.
    encounter_context: str | None = Field(default=None, max_length=256)
    # Opaque reference to the DPAPI-wrapped session key blob. NEVER key
    # material, and NEVER a caller-supplied path (PR-MED-003): the only legal
    # value is the literal filename "key.dpapi"; Step 2 resolves it strictly
    # as <sessions root>/<validated session_id>/key.dpapi, so a malformed
    # session can never point deletion outside its own directory.
    key_reference: str | None = Field(default=None, pattern=r"^key\.dpapi$")
    state: SessionState = SessionState.IDLE
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    def with_state(self, state: SessionState) -> RecordingSession:
        """Return a copy in `state` with a fresh `updated_at` timestamp.

        Transition LEGALITY is not enforced here — that is the Step 4
        state machine's job; this is a pure data operation.
        """
        return self.model_copy(update={"state": state, "updated_at": _utc_now()})

    @property
    def is_active(self) -> bool:
        return self.state in ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES


# --------------------------------------------------------------------------
# Step 4: state machine + controls + concurrency.
# --------------------------------------------------------------------------

# The COMPLETE legal-transition table (everything absent is illegal):
# - idle -> recording                       (Start)
# - recording -> paused                     (Pause)
# - recording/paused -> processing          (Finish)
# - paused -> recording                     (Resume)
# - processing -> queued                    (transcription done — Step 9)
# - queued -> written                       (Phase-2 Complete action; in Phase 4
#                                            real write-back precedes this)
# - failed -> processing                    (recovery: resume-processing, Flow 3)
# - recording/paused/processing -> failed   (device loss / disk full)
# - recording/paused/processing/queued/failed -> discarded  (Discard)
# - queued/failed -> expired                (24 h sweep)
# - written/discarded/expired -> (nothing)  (terminal)
LEGAL_TRANSITIONS: Final[dict[SessionState, frozenset[SessionState]]] = {
    SessionState.IDLE: frozenset({SessionState.RECORDING}),
    SessionState.RECORDING: frozenset(
        {SessionState.PAUSED, SessionState.PROCESSING, SessionState.FAILED,
         SessionState.DISCARDED}
    ),
    SessionState.PAUSED: frozenset(
        {SessionState.RECORDING, SessionState.PROCESSING, SessionState.FAILED,
         SessionState.DISCARDED}
    ),
    SessionState.PROCESSING: frozenset(
        {SessionState.QUEUED, SessionState.FAILED, SessionState.DISCARDED}
    ),
    SessionState.QUEUED: frozenset(
        {SessionState.WRITTEN, SessionState.DISCARDED, SessionState.EXPIRED}
    ),
    SessionState.FAILED: frozenset(
        {SessionState.PROCESSING, SessionState.DISCARDED, SessionState.EXPIRED}
    ),
    SessionState.WRITTEN: frozenset(),
    SessionState.DISCARDED: frozenset(),
    SessionState.EXPIRED: frozenset(),
}


class SessionControllerError(Exception):
    """Base class for session-controller failures."""


class IllegalTransitionError(SessionControllerError):
    """The requested state transition is not in LEGAL_TRANSITIONS."""


class SessionActivityError(SessionControllerError):
    """The operation conflicts with the single-active-session invariant, or
    there is no session in the state the operation requires."""


@dataclass
class _LiveSession:
    """Controller-private mutable record of the one tracked session."""

    session: RecordingSession
    directory: Path
    crypto: SessionCrypto
    store: SessionChunkStore | None
    worker: CaptureWorker | None
    # PR-HIGH-006: True while a transcribe() run is in flight — a second
    # concurrent transcribe on the same PROCESSING session must be refused
    # (both would race on the shared transcript temp path and a late writer
    # could mutate transcript.enc after Complete's verify).
    transcribing: bool = False


class SessionController:
    """The Step 4 session state machine (see module docstring for the
    concurrency contract). One controller instance owns the invariant; all
    control methods are safe to call from any thread."""

    def __init__(
        self,
        backend: CaptureBackend,
        *,
        sessions_root: Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._backend = backend
        self._root = sessions_root if sessions_root is not None else default_sessions_root()
        self._logger = logger
        self._lock = threading.RLock()
        self._live: _LiveSession | None = None

    # --- observers ---------------------------------------------------------

    @property
    def session(self) -> RecordingSession | None:
        with self._lock:
            return self._live.session if self._live is not None else None

    @property
    def state(self) -> SessionState:
        with self._lock:
            return self._live.session.state if self._live is not None else SessionState.IDLE

    @property
    def level(self) -> float:
        """Live input level (0.0–1.0) from the capture worker's meter."""
        with self._lock:
            live = self._live
            return live.worker.level if live is not None and live.worker is not None else 0.0

    def active_session_ids(self) -> frozenset[str]:
        """Session ids the expiry sweep must skip (keyed off STATE — plan
        Critical Constraint: the sweep never touches recording/paused/
        processing sessions)."""
        with self._lock:
            live = self._live
            if live is not None and live.session.state in ACTIVE_STATES:
                return frozenset({live.session.session_id})
            return frozenset()

    # --- controls ----------------------------------------------------------

    def start(self, device_id: int) -> RecordingSession:
        """Start a new recording session.

        Ordering (binding key-custody decision): session dir -> DPAPI-wrap
        the fresh session key to ``key.dpapi`` (atomic, durable) -> ONLY
        THEN create ``audio.enc`` -> start the capture worker (the single
        writer) -> state=recording."""
        with self._lock:
            live = self._live
            if live is not None and live.session.state in ACTIVE_STATES:
                raise SessionActivityError(
                    "another session is active (single-active-session invariant)"
                )
            if live is not None:
                # Previous session is queued/failed/terminal: drop our
                # in-memory handle. Its on-disk custody (if any) remains, so
                # a recoverable session stays recoverable via the sweep and
                # recovery screen.
                self._retire_locked(live)
            session = RecordingSession(key_reference="key.dpapi")  # state defaults to idle
            directory = self._root / session.session_id
            crypto = SessionCrypto()
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise StoreWriteError(f"failed creating session directory: {exc}") from exc
            store: SessionChunkStore | None = None
            try:
                wrap_key_to_file(crypto, directory)  # key BEFORE first chunk
                store = SessionChunkStore.create(
                    directory / AUDIO_FILENAME, crypto, session.session_id
                )
                chunk_store = store
                worker = CaptureWorker(
                    self._backend,
                    device_id,
                    lambda data: chunk_store.append_chunk(data),
                    on_failure=self._on_capture_failure,
                )
                worker.start()
            except Exception:
                # Nothing recoverable exists yet — clean up completely
                # (key first) rather than leaving an empty orphan.
                if store is not None:
                    store.close()
                discard_session(directory, crypto)
                raise
            live = _LiveSession(session, directory, crypto, store, worker)
            self._live = live
            self._transition_locked(live, SessionState.RECORDING)
            return live.session

    def pause(self) -> RecordingSession:
        """Pause capture. When this returns, no further chunk write can
        happen until resume(): the worker barrier guarantees any in-flight
        chunk is fully written first (or was cleanly dropped)."""
        with self._lock:
            live = self._require_state(SessionState.RECORDING)
            worker = live.worker
        if worker is not None:
            worker.pause()  # OUTSIDE the lock: barrier wait must not block callbacks
        with self._lock:
            # PR-HIGH-001: operate on the SNAPSHOT taken under the first
            # lock — never re-fetch self._live, which a concurrent start()
            # may have replaced with a brand-new session during the unlocked
            # window.
            if self._live is live and live.session.state == SessionState.RECORDING:
                self._transition_locked(live, SessionState.PAUSED)
            return live.session  # a concurrent failure/replacement wins

    def resume(self) -> RecordingSession:
        with self._lock:
            live = self._require_state(SessionState.PAUSED)
            if live.worker is not None:
                live.worker.resume()
            self._transition_locked(live, SessionState.RECORDING)
            return live.session

    def finish(self) -> RecordingSession:
        """Finish recording: stop the worker (flushing the buffered partial
        chunk), seal the store with its footer, state=processing.

        Disk failure at any point -> state=failed (RECOVERABLE — the key
        and all durably written chunks remain); never an exception, never
        silent loss."""
        with self._lock:
            live = self._require_live()
            if live.session.state not in (SessionState.RECORDING, SessionState.PAUSED):
                raise SessionActivityError(
                    f"cannot finish a session in state {live.session.state}"
                )
            worker = live.worker
        if worker is not None:
            worker.stop(flush=True)  # OUTSIDE the lock (thread join)
        with self._lock:
            # PR-HIGH-001: operate on the SNAPSHOT — a concurrent failure
            # can retire this session and a concurrent start() can install a
            # NEW one during the unlocked stop; re-fetching would seal the
            # wrong session's store.
            live.worker = None
            if self._live is not live:
                return live.session  # retired concurrently; on-disk state kept
            # The state may have changed while unlocked (concurrent failure);
            # widen past mypy's stale narrowing from the pre-stop check.
            state: SessionState = live.session.state
            if state == SessionState.FAILED:
                return live.session  # flush hit disk-full: already failed
            try:
                if live.store is not None:
                    live.store.finish()
            except StoreWriteError:
                self._fail_locked(live)
                return live.session
            finally:
                live.store = None
            self._transition_locked(live, SessionState.PROCESSING)
            return live.session

    def transcribe(
        self, transcriber: Callable[[Path, SessionCrypto], object]
    ) -> RecordingSession:
        """Step 9: run the transcription pipeline for the PROCESSING session.

        ``transcriber(directory, crypto)`` (typically a closure over
        ``transcription.transcribe_session``) runs OUTSIDE the lock — it is
        long-running ML work and must never block controls or the failure
        callback. Per the PR-HIGH-001 contract the method operates on the
        first-lock SNAPSHOT with identity checks: a session retired or
        replaced concurrently is never transitioned.

        Success: processing -> queued (``transcript.enc`` is durably on
        disk). Failure: the exception propagates AND the session goes to
        ``failed`` (RECOVERABLE — key + audio retained; Flow 3 offers
        resume-processing or discard). Audio is never deleted here.
        """
        with self._lock:
            live = self._require_state(SessionState.PROCESSING)
            # PR-HIGH-006 (locking/ordering only, pending user ratification):
            # exactly ONE transcription run per session may be in flight.
            # Without this guard two callers could both pass the PROCESSING
            # check, race on the shared transcript temp path, and a late
            # writer could replace transcript.enc AFTER a concurrent
            # Complete verified it — violating the fsync->verify->delete-key
            # ordering.
            if live.transcribing:
                raise SessionActivityError(
                    "transcription already in progress for this session"
                )
            live.transcribing = True
        try:
            transcriber(live.directory, live.crypto)
        except Exception:
            with self._lock:
                live.transcribing = False
                if (
                    self._live is live
                    and live.session.state == SessionState.PROCESSING
                ):
                    self._fail_locked(live)
            raise
        with self._lock:
            live.transcribing = False
            if self._live is live and live.session.state == SessionState.PROCESSING:
                self._transition_locked(live, SessionState.QUEUED)
            return live.session

    def mark_queued(self) -> RecordingSession:
        """processing -> queued. Called by the Step 9 transcription pipeline
        once ``transcript.enc`` is durably written."""
        with self._lock:
            live = self._require_state(SessionState.PROCESSING)
            # PR-HIGH-008 (locking/ordering only, pending user ratification):
            # while transcribe() is in flight it owns the processing->queued
            # transition; queueing here would let Complete verify and delete
            # the key while the transcriber is still writing — the same
            # late-writer race PR-HIGH-006 closes.
            if live.transcribing:
                raise SessionActivityError(
                    "transcription in progress; it queues the session itself"
                )
            self._transition_locked(live, SessionState.QUEUED)
            return live.session

    def complete(self) -> RecordingSession:
        """The explicit Phase-2 Complete action (distinct from Discard):
        queued -> written via the store's binding ordering primitive
        (fsync transcript -> verify decrypt round-trip -> delete key =
        cryptographic deletion). Any verification failure keeps the key
        and leaves the session queued."""
        with self._lock:
            live = self._require_state(SessionState.QUEUED)
            complete_session(live.directory, live.crypto)  # raises -> stays queued
            self._transition_locked(live, SessionState.WRITTEN)
            session = live.session
            self._live = None
            return session

    def discard(self) -> RecordingSession:
        """Discard the session: key deleted FIRST (cryptographic deletion),
        then best-effort removal of the artifacts."""
        with self._lock:
            live = self._require_live()
            if SessionState.DISCARDED not in LEGAL_TRANSITIONS[live.session.state]:
                raise IllegalTransitionError(
                    f"illegal transition {live.session.state} -> discarded"
                )
            worker = live.worker
        if worker is not None:
            worker.stop(flush=False)  # OUTSIDE the lock; buffered audio dropped
        with self._lock:
            # PR-HIGH-001: operate on the SNAPSHOT taken under the first
            # lock. Re-fetching self._live here allowed a concurrent start()
            # (legal for a queued/failed session) to install a NEW recording
            # whose key this method would then cryptographically delete —
            # wrong-session data loss. The snapshot is the session the
            # caller asked to discard; the on-disk artifacts deleted below
            # are resolved from ITS directory and crypto only.
            live.worker = None
            if live.session.state == SessionState.DISCARDED:
                return live.session  # concurrent discard already completed
            if live.store is not None:
                live.store.close()
                live.store = None
            discard_session(live.directory, live.crypto)  # key-first, destroys crypto
            self._transition_locked(live, SessionState.DISCARDED)
            session = live.session
            if self._live is live:
                self._live = None
            return session

    # --- internals ---------------------------------------------------------

    def _require_live(self) -> _LiveSession:
        if self._live is None:
            raise SessionActivityError("no session")
        return self._live

    def _require_state(self, expected: SessionState) -> _LiveSession:
        live = self._require_live()
        if live.session.state != expected:
            raise SessionActivityError(
                f"operation requires state {expected}, session is {live.session.state}"
            )
        return live

    def _transition_locked(self, live: _LiveSession, target: SessionState) -> None:
        current = live.session.state
        if target not in LEGAL_TRANSITIONS[current]:
            raise IllegalTransitionError(f"illegal transition {current} -> {target}")
        live.session = live.session.with_state(target)
        if self._logger is not None:
            log_event(
                self._logger,
                "session_transition",
                session_id=live.session.session_id,
                session_state=target.value,
            )

    def _fail_locked(self, live: _LiveSession) -> None:
        """Route to failed (RECOVERABLE): stop writing, keep key + chunks."""
        if live.store is not None:
            live.store.close()
            live.store = None
        self._transition_locked(live, SessionState.FAILED)

    def _retire_locked(self, live: _LiveSession) -> None:
        """Drop the in-memory handle to a non-active session. On-disk state
        is untouched: a queued/failed session stays recoverable through its
        DPAPI custody blob; terminal sessions have none."""
        if live.worker is not None:
            live.worker.stop(flush=False)
            live.worker = None
        if live.store is not None:
            live.store.close()
            live.store = None
        live.crypto.destroy()  # in-memory copy only; key.dpapi (if any) remains
        self._live = None

    def _on_capture_failure(self, _exc: Exception) -> None:
        """Worker-thread callback for device loss / disk-full during capture.
        The session becomes failed (recoverable). At most one failure is
        reported per worker; a session already past recording/paused (e.g.
        discarded concurrently) ignores it."""
        with self._lock:
            live = self._live
            if live is None or live.session.state not in (
                SessionState.RECORDING,
                SessionState.PAUSED,
            ):
                return
            self._fail_locked(live)
