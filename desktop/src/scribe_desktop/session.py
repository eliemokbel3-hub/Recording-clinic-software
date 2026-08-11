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
    SESSION_ID_PATTERN,
    SessionChunkStore,
    StoreWriteError,
    # Package-private by name, shared deliberately (the note.py convention):
    # the round-30 reserved-target guard must resolve session identity with
    # THE single definition custody verification uses, or the two could
    # disagree about which session a directory is.
    _resolve_session_identity,
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

# PLAN.md lifecycle documentation: states a crashed session may conceptually
# be recovered from. NOTE the recovery screen lists by ON-DISK custody
# (key.dpapi presence), not by state — session state is not persisted
# across a crash (round 42 LOW-012).
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
    session_id: str = Field(default_factory=_new_session_id, pattern=SESSION_ID_PATTERN)
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


class GenerationInProgressError(SessionControllerError):
    """The operation would destroy or retire custody state a live note
    generation depends on (Task 6.3). Refused while the generation lease is
    held; the caller retries after ``end_generation``."""


class GenerationLease:
    """Opaque token for ONE in-flight note-generation operation (Task 6.3).

    The lease is a TOKEN spanning the WHOLE operation, not the worker:
    acquired (``SessionController.begin_generation``) BEFORE the generation
    ``TaskThread`` starts, released (``end_generation``) only after the
    GUI-thread ``write_note`` succeeds or the failure cleanup completes. A
    worker-scoped lease released on callable return would reopen the
    custody-critical gap exactly where ``write_note`` runs — the round-2 peer
    finding this type exists to close. Compared by IDENTITY; carries no
    state, so it cannot be forged by construction of an equal value.
    """

    __slots__ = ()


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
    concurrency contract). One controller instance owns the invariant.

    CONCURRENCY CONTRACT, stated accurately after peer rounds 27-32 (the
    earlier blanket "safe from any thread" claim is deliberately NOT
    re-inflated): custody-mutating and custody-using operations — start,
    complete, discard, transcribe, generation begin/end, the recovered-path
    coordinator ops, and the sweep/recovery-list protection snapshot — are
    serialized through the controller lock PLUS the per-session custody
    reservation (``_custody_reservations``), whose consumers cover
    discard's unlocked worker-join window in BOTH orders. That is
    sufficient for the SHIPPED usage: every custody caller runs on the
    single GUI thread, with worker results returning via queued signals.

    DOCUMENTED RESIDUE (practitioner-accepted at round 32): full
    ARBITRARY-thread custody safety is deferred to a future dedicated
    holistic serialization hardening. The six MED custody races found and
    fixed across peer rounds 27-32 each required a non-GUI-thread custody
    caller that does not exist in shipped wiring, and further such
    compositions may remain undiscovered. Do NOT introduce a
    non-GUI-thread custody caller without doing that hardening first
    (candidate Phase-8 threat-model item)."""

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
        # Task 6.3: the ONE in-flight note-generation lease. While held,
        # every custody-destructive or handle-retiring operation — start()
        # (which retires the queued session a generation depends on),
        # complete(), discard(), and the recovered-path coordinator ops —
        # is refused with GenerationInProgressError. Deliberately COARSE
        # (one lease, not per-session): at most one generation runs at a
        # time in this app, and over-blocking fails toward safety.
        self._generation: GenerationLease | None = None
        # Rounds 27 + 30 PR-MED-001: TARGET-AWARE custody-transition
        # reservations, session_id -> in-flight discard count. discard()
        # is a TWO-lock operation (the worker join must stay outside the
        # lock), so its entry-time checks alone leave an unlocked window;
        # a discard reserves ITS TARGET's id here (under the lock, after
        # every refusal path) before releasing the lock, and releases it
        # in its finally. Consumers: begin_generation() and complete()
        # refuse while ANY reservation is held (coarse, safe);
        # the recovered-coordinator ops refuse a RESERVED TARGET by
        # resolved identity; and `reserved_session_ids()` feeds the
        # recovery listing exclusion and the 24 h sweep protection —
        # round 30's lesson being that the admitted concurrent start()
        # swaps `_live` mid-window, so protection must be sourced from
        # the RESERVATION SET, never the mutable live pointer. PER-ID
        # COUNTS with independent lifetime, not a global flag/count:
        # overlapping discards are legal, and one finishing must not
        # strip another target's protection.
        self._custody_reservations: dict[str, int] = {}

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
            # Task 6.3: start() on a queued session RETIRES it — dropping the
            # in-memory handle (directory, crypto) a generation worker
            # depends on — so it is refused outright while the lease is held.
            self._refuse_while_generating("start")
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
            # Round 32 PR-MED-001: the INVERSE order of the round-42 MED-003
            # guard below in discard(). Transcribe-first makes Discard refuse
            # (the `transcribing` flag); discard-first must make transcription
            # refuse — a Discard that has reserved this session's custody
            # transition is between its two locked sections, and its second
            # section will destroy the crypto this transcriber would be
            # using. IDENTITY-SCOPED, with the live snapshot and the
            # reservation map read in this same critical section, so a
            # different session Y installed by an admitted Start is never
            # transiently blocked by X's reservation. Refused BEFORE the
            # `transcribing` flag is installed and before any crypto/store
            # use; the long transcriber call stays outside the lock.
            if live.session.session_id in self._custody_reservations:
                raise SessionActivityError(
                    "a discard of this session is in flight; transcription refused"
                )
            # PR-HIGH-006 (locking/ordering only; user-ratified 2026-07-27):
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
        """processing -> queued, for a driver OTHER than ``transcribe()``.

        The production pipeline does NOT call this: ``transcribe()`` owns
        the processing -> queued transition itself (round 42 LOW-009 —
        this docstring previously claimed the Step 9 pipeline calls here).
        Kept as the explicit state-machine seam (exercised by tests, and
        by any future external processing driver); the PR-HIGH-008 guard
        below keeps it safe alongside an in-flight ``transcribe()``."""
        with self._lock:
            live = self._require_state(SessionState.PROCESSING)
            # PR-HIGH-008 (locking/ordering only; user-ratified 2026-07-27):
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
            # Task 6.3: Complete deletes the session key — the generation
            # worker's transcript would become unreadable and its note
            # unwritable mid-flight. Refused while the lease is held.
            self._refuse_while_generating("complete")
            # Round 29 PR-MED-001: an in-flight discard() owns the custody
            # transition across its unlocked worker-join window (the round-27
            # reservation). A Complete slotting into that window would let
            # BOTH terminal actions mutate one session — Complete reporting
            # WRITTEN while the resuming discard removes the artifacts —
            # and exactly one terminal action may win before either reports
            # success. Same consumer shape as begin_generation's; refuses
            # nothing else (second discards and concurrent start() stay
            # admitted, pinned by their tests).
            if self._custody_reservations:
                raise SessionActivityError(
                    "a discard is completing; the session cannot be completed"
                )
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
            # Task 6.3: Discard is key-first cryptographic deletion — refused
            # while the generation lease is held, same rationale as complete().
            self._refuse_while_generating("discard")
            live = self._require_live()
            if SessionState.DISCARDED not in LEGAL_TRANSITIONS[live.session.state]:
                raise IllegalTransitionError(
                    f"illegal transition {live.session.state} -> discarded"
                )
            # Round 42 MED-003 — same in-flight guard family as
            # transcribe()/mark_queued() (PR-HIGH-006/008, user-ratified
            # 2026-07-27): discarding here would destroy the key under a
            # live transcriber. The UI already disables Discard while
            # PROCESSING; this guard enforces it at the controller under
            # the class docstring's stated contract. This covers the
            # transcribe-FIRST order; the inverse (discard reserves, then
            # transcription tries to begin) is covered by transcribe()'s
            # reservation consumer (round 32) — mutual exclusion holds in
            # both orders.
            if live.transcribing:
                raise SessionActivityError(
                    "transcription in progress; wait for it to finish or fail"
                )
            worker = live.worker
            session_id = live.session.session_id
            # Round 27 PR-MED-001 (target-aware since round 30): RESERVE the
            # custody transition BEFORE the lock is released. The entry-time
            # checks above cannot cover the unlocked interval between this
            # section and the next — an interval that exists on EVERY
            # discard, worker or not, and spans the whole worker join when
            # there is one — during which begin_generation()/complete()
            # could otherwise act, and (round 30) the admitted concurrent
            # start() retires this session from `_live`, exposing its still-
            # recoverable on-disk custody to the recovery flow and the sweep
            # unless the reservation itself is what protects it. Set LAST,
            # after every refusal path above, so no failure can leak a
            # reservation; released in the finally on every exit (early
            # return, success, or a discard_session failure). A bare
            # post-stop recheck was rejected: refusing at that point would
            # strand a half-stopped session claiming RECORDING/PAUSED with
            # its worker gone.
            self._reserve_custody_locked(session_id)
        try:
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
        finally:
            with self._lock:
                self._release_custody_locked(session_id)

    # --- note-generation lease + custody coordination (Task 6.3) -----------
    #
    # SessionController is the ONE lease-aware custody coordinator for BOTH
    # session kinds: the live session it already owns, and recovered sessions
    # — which otherwise bypass it entirely (the recovery flow hands the UI a
    # directory + unwrapped key, and UI button state is not a guard on an
    # any-thread-safe controller). The recovered-path operations below
    # perform the SCOPED custody action themselves rather than exposing raw
    # directory/crypto accessors, so every custody-destructive path crosses
    # the same lease check under the same lock.
    #
    # Deliberately NOT lease-protected: the 24 h expiry sweep. The shipped
    # wiring already keeps the sweep away from every session a generation
    # could target — `app.sweep_protected_ids` protects the controller's
    # non-terminal session (QUEUED included; round 42 MED-001) and the
    # recovery screen's checkouts (PR round 18) — so a lease check here
    # would only re-cover the same ground while muddying which mechanism
    # owns the cap. And if that wiring ever changed, the failure direction
    # is still CLOSED: a swept session's key is destroyed, so write_note
    # and Complete refuse; the retention bound wins, nothing is written
    # wrong. Likewise the recovery screen's list-discard needs no lease: a
    # checked-out (generating) recovered session is excluded from the list
    # and all list actions are disabled while a checkout exists.

    def begin_generation(self) -> GenerationLease:
        """Acquire THE generation lease — call BEFORE the worker starts.

        At most one generation is in flight at a time; a second acquisition
        raises. State-agnostic on purpose: a recovered-session generation
        runs with no live controller session at all. Refused while a
        custody-destructive operation holds a transition reservation (round
        27 PR-MED-001) — either the discard entered first and this
        acquisition must not slip into its unlocked window, or the lease was
        first and the discard was already refused at its own entry; the lock
        serializes the two checks, so no interleaving leaves a lease held
        while ``discard_session`` deletes a key."""
        with self._lock:
            if self._generation is not None:
                raise GenerationInProgressError(
                    "a note generation is already in progress"
                )
            if self._custody_reservations:
                # SessionActivityError, not GenerationInProgressError: no
                # generation is in progress — the conflict is an in-flight
                # discard completing its custody transition.
                raise SessionActivityError(
                    "a discard is completing; retry generation after it finishes"
                )
            lease = GenerationLease()
            self._generation = lease
            return lease

    def end_generation(self, lease: GenerationLease) -> None:
        """Release the lease — call only after the GUI-thread ``write_note``
        succeeded or the failure cleanup completed.

        Idempotent for the released token (cleanup paths may run twice), but
        a token that is NOT the held one raises: silently accepting a foreign
        token would let a stale handler release someone else's lease."""
        with self._lock:
            if self._generation is None:
                return
            if self._generation is not lease:
                raise SessionControllerError(
                    "end_generation called with a lease that is not held"
                )
            self._generation = None

    @property
    def generating(self) -> bool:
        with self._lock:
            return self._generation is not None

    def reserved_session_ids(self) -> frozenset[str]:
        """Session ids an in-flight Discard has reserved (round 30) — the
        reservation-only view, for tests and diagnostics.

        External protection consumers (the recovery-list exclusion, the
        24 h sweep) must NOT compose this with separate live-session reads:
        they consume ``custody_protected_ids()``, the single-lock snapshot
        (round 31 — the split-read composition was itself a race)."""
        with self._lock:
            return frozenset(self._custody_reservations)

    def custody_protected_ids(self) -> frozenset[str]:
        """ONE atomic snapshot of every custody-protected session id: all
        in-flight Discard reservation targets (round 30) PLUS the current
        live session in ANY non-terminal state (active states included —
        this is a superset of ``active_session_ids()``).

        Read under a SINGLE ``_lock`` acquisition (round 31 PR-MED-001):
        the sweep exemption and the recovery-list exclusion consume THIS
        method, never a composition of separate public reads — a
        Discard(X)-reserve plus admitted Start(Y) interleaved BETWEEN two
        reads yields a set naming Y but omitting still-reserved X, exactly
        the exposure round 30 closed. Ids only under the lock; callers do
        their filesystem listing/sweeping AFTER this returns — the lock is
        never held across I/O."""
        with self._lock:
            ids = set(self._custody_reservations)
            live = self._live
            if live is not None and not live.session.is_terminal:
                ids.add(live.session.session_id)
            return frozenset(ids)

    def complete_recovered(self, directory: Path, crypto: SessionCrypto) -> None:
        """Complete a RECOVERED session (Flow 2 ordering via
        ``complete_session``: fsync -> verify -> delete key), through the
        lease-aware coordinator instead of a raw store-primitive call."""
        with self._lock:
            self._refuse_while_generating("complete")
            self._refuse_reserved_target_locked(directory, "complete")
            complete_session(directory, crypto)

    def discard_recovered(self, directory: Path, crypto: SessionCrypto | None) -> None:
        """Discard a RECOVERED session (key-first cryptographic deletion),
        through the lease-aware coordinator."""
        with self._lock:
            self._refuse_while_generating("discard")
            self._refuse_reserved_target_locked(directory, "discard")
            discard_session(directory, crypto)

    def destroy_recovered_crypto(self, crypto: SessionCrypto) -> None:
        """Zeroize a recovered checkout's in-memory key copy (disk custody
        untouched), through the lease-aware coordinator: while a generation
        is in flight the key it depends on must not be destroyed under it.

        Refused COARSELY while any discard reservation is held (round 30):
        this operation carries no directory, so there is no identity to
        resolve a scoped check against — and the coarse refusal is a strict
        superset of the scoped one, failing toward safety at the cost of a
        transient retry."""
        with self._lock:
            self._refuse_while_generating("recovered-key destruction")
            if self._custody_reservations:
                raise SessionActivityError(
                    "recovered-key destruction refused: a discard is in flight"
                )
            crypto.destroy()

    def _reserve_custody_locked(self, session_id: str) -> None:
        """Call under ``self._lock``."""
        self._custody_reservations[session_id] = (
            self._custody_reservations.get(session_id, 0) + 1
        )

    def _release_custody_locked(self, session_id: str) -> None:
        """Call under ``self._lock``. Per-id lifetime: releasing one
        discard's reservation never unprotects another target's."""
        count = self._custody_reservations.get(session_id, 0) - 1
        if count > 0:
            self._custody_reservations[session_id] = count
        else:
            self._custody_reservations.pop(session_id, None)

    def _refuse_reserved_target_locked(self, directory: Path, operation: str) -> None:
        """Call under ``self._lock``. Round 30: a recovered-path custody op
        must not touch a session whose id an in-flight Discard has reserved.

        Identity is RESOLVED from the directory (the store header is
        authoritative, directory name the fallback — the single
        ``_resolve_session_identity`` definition), never taken from a caller
        claim; resolution runs only while a reservation exists, and a
        resolution failure propagates typed — fail closed, never a guess."""
        if not self._custody_reservations:
            return
        if _resolve_session_identity(directory) in self._custody_reservations:
            raise SessionActivityError(
                f"{operation} refused: a discard of this session is in flight"
            )

    def _refuse_while_generating(self, operation: str) -> None:
        """Call under ``self._lock``."""
        if self._generation is not None:
            raise GenerationInProgressError(
                f"{operation} refused: a note generation is in progress"
            )

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
        # Task 6.3, defense in depth: today the only caller is start(),
        # which already refused — but retirement destroys the in-memory
        # crypto a generation worker may hold, so the guard lives HERE too
        # rather than only on the callers that exist today.
        self._refuse_while_generating("session retirement")
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
