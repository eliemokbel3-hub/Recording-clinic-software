"""Core recording-session types + session state machine (Phase 2 Steps 1+4).

`SessionState` is the real session lifecycle enum from PLAN.md — it
supersedes Phase 1's throwaway `ConnectionState` (now retired).

`RecordingSession` carries the PLAN.md fields: session identifier,
encounter context, consent, encryption-key reference and timestamps. The
Cliniko workflow safeguards plan (D3) types them: `encounter_context` is the
`EncounterContext` a linked Start verified (None when unlinked) and
`consent` the REQUIRED `ConsentAttestation`. `key_reference` is a REFERENCE
to the DPAPI-wrapped key blob (a filesystem path string) — never key
material.

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
import re
import secrets
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scribe_desktop import __version__
from scribe_desktop.audio_capture import (
    CHANNELS,
    CHUNK_BYTES,
    SAMPLE_RATE,
    SAMPLE_WIDTH,
    AudioCaptureError,
    CaptureBackend,
    CaptureWorker,
)
from scribe_desktop.draft_write import (
    RECORD_UNREADABLE,
    RecordUnreadable,
    WriteRecord,
    WriteRecordStatus,
    WriteRecordUnreadable,
    parse_write_record,
    record_status,
)
from scribe_desktop.encounter import (
    ConsentAttestation,
    DevelopmentConsent,
    EncounterContext,
    EncounterRecord,
    EncounterUnavailable,
    bind_consent,
    read_encounter_record,
    write_encounter_record,
)
from scribe_desktop.logging_setup import exception_type_name, log_event
from scribe_desktop.past_sessions import KeepLabel, PastSessionStore
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_mode import SessionMode
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    SESSION_ID_PATTERN,
    TRANSCRIPT_FILENAME,
    ArchiveWriteError,
    CompletionFacts,
    KeyCustodyError,
    SessionChunkStore,
    SessionStoreError,
    StoreWriteError,
    # Package-private by name, shared deliberately (the note.py convention):
    # the round-30 reserved-target guard must resolve session identity with
    # THE single definition custody verification uses, or the two could
    # disagree about which session a directory is.
    _resolve_session_identity,
    audit_created_at,
    complete_session,
    default_sessions_root,
    discard_session,
    read_write_record,
    saved_note_identity,
    unwrap_key_from_file,
    wrap_key_to_file,
    write_write_record,
)
from scribe_desktop.transcription import LiveFailure, LiveTranscriber

if TYPE_CHECKING:
    # audit.py imports THIS module (``AuditWriteError`` subclasses
    # ``SessionControllerError``, D12), so the store's type is annotation-only.
    from scribe_desktop.audit import AuditLog

# Task 4.5: the audio one stored chunk holds (1.0 s at 16 kHz mono PCM16).
_CHUNK_SECONDS: Final = CHUNK_BYTES / (SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH)

# Note-learning plan D2: how long an IN-LOCK stop of the live worker waits
# for its thread (``_fail_locked`` / retirement — paths that do NOT destroy
# the key). Short on purpose: the controller lock is the GUI's state-poll
# lock, and a worker blocked in a provider call cannot be interrupted. A
# timeout leaves the worker ATTACHED (never counted as cleared) so a later
# Discard retries with the full ``LIVE_STOP_TIMEOUT_SECONDS`` OUTSIDE the
# lock before the key is destroyed.
_LIVE_STOP_LOCKED_TIMEOUT_S: Final = 1.0


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

# The states in which a recording is under way — capture running or paused
# (H2a SIMP-012: one name for the check spelled at every such site).
CAPTURING_STATES: frozenset[SessionState] = frozenset(
    {SessionState.RECORDING, SessionState.PAUSED}
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


def _new_session_ref() -> str:
    """D2's opaque session reference: 24 url-safe characters — never the
    32-hex session id (so never the directory name), never persisted."""
    return secrets.token_urlsafe(18)


def _tee_sink(
    store: SessionChunkStore, live_worker: LiveTranscriber | None
) -> Callable[[bytes], int]:
    """The capture sink (note-learning plan D1): the store's encrypting
    write FIRST — the system of record, whose failure fails the session
    exactly as today — then the SAME plaintext chunk to the live worker.
    Two exception paths, deliberately different: the STORE's exception
    (disk full) propagates out of the sink exactly as before the tee
    existed — ``CaptureWorker._fail`` → ``_on_capture_failure`` → FAILED;
    the WORKER's never does: ``feed`` fails the worker itself on any error,
    and should it raise regardless, the worker is failed here (a chunk it
    did not see would misalign its timeline, so it must not run on) and the
    exception stops at this boundary. The store method is resolved PER CALL
    (never a method bound at Start), so a store whose ``append_chunk`` is
    replaced after Start — the disk-full test seam — still fails the
    session. Callers: only ``CaptureWorker`` (its chunk loop and its two
    flush sites)."""
    if live_worker is None:
        return lambda data: store.append_chunk(data)

    def sink(data: bytes) -> int:
        written = store.append_chunk(data)  # propagates: the session fails
        try:
            live_worker.feed(data)
        except Exception as exc:  # noqa: BLE001 - the tee boundary
            live_worker.fail(f"{type(exc).__name__}: {exc}")
        return written

    return sink


def _utc_now() -> datetime:
    return datetime.now(UTC)


def keep_label_for_mode(label: KeepLabel | None, mode: SessionMode | None) -> KeepLabel | None:
    """The label a Complete keeps, with its shadow flag forced on when the
    LIVE session is not a ``normal`` recording (pilot review round 22): the
    UI resolves the label, but the controller holds the mode fixed at Start,
    so a label resolved wrongly can never make a shadow recording's entry
    copyable. ``mode`` None (a recovered session, whose checkout record only
    the UI read) and a None label (``UNKNOWN_LABEL``, already shadow) leave
    it as given."""
    if label is None or mode is None or mode is SessionMode.NORMAL or label.shadow:
        return label
    return replace(label, shadow=True)


def load_write_record(
    session_dir: Path, crypto: SessionCrypto, session_id: str
) -> WriteRecord | None:
    """The session's ``write.enc`` decoded (draft-write Task 3.3), or None
    when there is none. A file that exists but cannot be decrypted or
    parsed raises ``WriteRecordUnreadable`` — never None, so an unreadable
    record can never read as "no write happened"."""
    try:
        plaintext = read_write_record(session_dir, crypto, session_id)
    except (SessionStoreError, RuntimeError, ValueError):
        raise WriteRecordUnreadable() from None
    return None if plaintext is None else parse_write_record(plaintext)


def store_write_record(
    session_dir: Path, crypto: SessionCrypto, session_id: str, record: WriteRecord
) -> None:
    """Writes the record encrypted under the session key (AAD
    ``write:<id>``, atomic + fsync through ``session_store``)."""
    write_write_record(session_dir, crypto, session_id, record.to_bytes())


def read_write_record_status(
    session_dir: Path, crypto: SessionCrypto, session_id: str
) -> WriteRecordStatus:
    """The content-free status of the session's write record plus whether
    it belongs to the saved note now on disk. An unreadable record is its
    own status (never "none"); an unreadable saved note leaves
    ``note_matches`` False."""
    record: WriteRecord | RecordUnreadable | None
    try:
        record = load_write_record(session_dir, crypto, session_id)
    except WriteRecordUnreadable:
        record = RECORD_UNREADABLE
    identity: str | None
    try:
        identity = saved_note_identity(session_dir, crypto)
    except (SessionStoreError, RuntimeError, ValueError):
        identity = None
    return record_status(record, identity)


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
    # Cliniko workflow safeguards plan D3: the Cliniko note this recording is
    # bound to at Start (ids only), or None for an UNLINKED recording. Frozen
    # with the session: no path re-binds a session to another note.
    encounter_context: EncounterContext | None = None
    # Constraint 4 / Task 3.1 decision: REQUIRED on the model, not only at
    # start(), so no construction path yields a session without consent.
    # ``bind_consent`` ties it to the context (an unlinked consent names no
    # note; a linked one names exactly the context's note).
    consent: ConsentAttestation
    # Opaque reference to the DPAPI-wrapped session key blob. NEVER key
    # material, and NEVER a caller-supplied path (PR-MED-003): the only legal
    # value is the literal filename "key.dpapi"; Step 2 resolves it strictly
    # as <sessions root>/<validated session_id>/key.dpapi, so a malformed
    # session can never point deletion outside its own directory.
    key_reference: str | None = Field(default=None, pattern=r"^key\.dpapi$")
    # Pilot plan Task 1.2 (D1): fixed at Start from the pilot setting and
    # frozen with the session; a rebuild takes it from ``encounter.enc``.
    mode: SessionMode = SessionMode.NORMAL
    # Development-recordings plan Task 1.5 (D2, D3): the patient's written
    # consent to the recording being kept for development, decided at Start
    # and frozen with the session; None = not kept (C3). A rebuild takes it
    # from ``encounter.enc``.
    development_consent: DevelopmentConsent | None = None
    state: SessionState = SessionState.IDLE
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def _consent_bound(self) -> RecordingSession:
        bind_consent(self.consent, self.encounter_context)
        return self

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


class LiveStopPendingError(SessionActivityError):
    """Peer round 9 PR-MED-017's refusal, by type (installation plan round 40
    LOW-002): a destructive custody step refused because the live worker
    has not stopped and may still hold plaintext. Nothing was destroyed and
    the session is kept; the same action succeeds once the worker has
    stopped. A type so the screens can say that plainly."""


class ConsentRequiredError(SessionControllerError):
    """``start()`` was called without a ``ConsentAttestation``, or with one
    that does not name the context's note (Constraint 4)."""


class GenerationInProgressError(SessionControllerError):
    """The operation would destroy or retire custody state a live note
    generation depends on (Task 6.3). Refused while the generation lease is
    held; the caller retries after ``end_generation``."""


class ReviewOpenRefused(SessionControllerError):
    """``adopt_queued`` refused the SESSION itself (Cliniko workflow
    safeguards plan Task 5.4): ``reason`` is ``no_transcript``,
    ``key_unavailable``, ``consent_unavailable`` (its ``encounter.enc`` is
    missing or unauthentic — never a fabricated consent) or ``unreadable``
    (the caller's reader raised; the cause is chained). Nothing was
    installed and the live session, if any, is untouched."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"open for review refused: {reason}")
        self.reason = reason


class WriteInFlightError(SessionActivityError):
    """The operation would complete, discard, retire, regenerate, adopt or
    otherwise change custody of the session a Cliniko draft write holds
    (cliniko-draft-write plan D9). Refused while the write reservation is
    held; the UI shows ``WRITE_LINES["write_in_flight"]`` for it (its own
    text is diagnostic, never shown). A ``SessionActivityError``, so every
    caller that already handles a custody refusal handles this one."""

    def __init__(self, operation: str) -> None:
        super().__init__(f"{operation} refused: a Cliniko draft write holds this session")


# Privacy-professional-controls plan Flow 3: the status line a refused
# archive gives (its ``Complete failed:`` prefix is the screen's).
PAST_SESSION_WRITE_FAILED_TEXT: Final = (
    "the Past-sessions copy could not be saved. No key deletion was performed "
    "— try again, or Discard."
)


class PastSessionWriteError(SessionControllerError):
    """A Complete refused BEFORE its key boundary because the Past-sessions
    entry could not be written, verified or published (privacy-professional-
    controls C1, D12): the key, the state, any lease and any reservation are
    kept, so the Complete can be retried — a retry replaces the unfinished
    entry key-first — or the session discarded, which removes it. Authored
    text only (the store's cause is never shown)."""

    def __init__(self) -> None:
        super().__init__(PAST_SESSION_WRITE_FAILED_TEXT)


class PastSessionCleanupError(SessionControllerError):
    """A Discard refused because the unfinished Past-sessions entry an
    interrupted Complete left for this session could not be removed (C1:
    the source key may only go after it). Nothing was deleted; the Discard
    can be retried."""

    def __init__(self) -> None:
        super().__init__(
            "discard refused: an unfinished Past-sessions copy of this session could "
            "not be removed. Nothing was deleted - try again."
        )


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


class EnrolmentLease:
    """Opaque token for ONE in-flight voice-enrolment activity
    (practitioner-profile plan D15): acquired by ``begin_enrolment`` before
    the capture starts and released by ``end_enrolment`` only after the
    embedding, ``save_profile`` and the caller's own result handler have run
    (success or failure), so the microphone stays the enrolment's for the
    whole sequence. Compared by IDENTITY; carries no state."""

    __slots__ = ()


class WriteReservation:
    """Token for ONE in-flight Cliniko draft write (cliniko-draft-write plan
    D9): acquired by ``SessionController.reserve_write`` on the GUI thread
    BEFORE the write's first worker is dispatched, held across both hops and
    the GUI-thread steps between them, and released by the result handler
    (``release``). Seen mode (D6) takes a SECOND, momentary token at the
    Complete click after a confirmed write: ``complete_after_write``
    consumes it, or the click releases it when completion refuses. While
    held, the session's custody reservation refuses every custody-changing
    operation (``WriteInFlightError``). Compared by IDENTITY: an equal-looking
    token built elsewhere is never the held one. ``release`` is idempotent,
    and releasing a token that is no longer held changes nothing, so a
    failure path may run it twice."""

    __slots__ = ("_controller", "_session_id")

    def __init__(self, controller: SessionController, session_id: str) -> None:
        self._controller = controller
        self._session_id = session_id

    @property
    def session_id(self) -> str:
        """The reserved session — read-only, so a holder cannot retarget the
        token."""
        return self._session_id

    def release(self) -> None:
        self._controller._release_write(self)


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
    # Note-learning plan D2: the live transcription worker, on its OWN handle
    # (never the ``transcribing`` flag). "Attached" means the controller owns
    # its cleanup: whichever path leaves it here — a failure, retirement on
    # start(), a Discard before the transcriber callable claims it — stops
    # it and confirms its buffers cleared before any key destruction. The
    # processing callable claims it through ``claim_live_transcriber`` under
    # the ``transcribing`` guard, after which the callable owns it.
    live_transcriber: LiveTranscriber | None = None
    # Cliniko workflow safeguards plan D2: this session's opaque reference in
    # the controller's reference registry (minted at start).
    session_ref: str | None = None
    # Task 4.5: the store's chunk count when Finish sealed it or a failure
    # closed it (``recorded_seconds`` reads the open store until then).
    closed_chunks: int = 0


class SessionController:
    """The Step 4 session state machine (see module docstring for the
    concurrency contract). One controller instance owns the invariant.

    CONCURRENCY CONTRACT, stated accurately after peer rounds 27-32 (the
    earlier blanket "safe from any thread" claim is deliberately NOT
    re-inflated): custody-mutating and custody-using operations — start,
    adopt_queued, complete, discard, transcribe, generation begin/end, the
    draft-write reservation and its accessor, the recovered-path
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
        live_transcriber_factory: Callable[[], LiveTranscriber | None] | None = None,
        audit: AuditLog | None = None,
        past_sessions: PastSessionStore | None = None,
        app_version: str | None = None,
    ) -> None:
        self._backend = backend
        self._root = sessions_root if sessions_root is not None else default_sessions_root()
        self._logger = logger
        # Pilot plan Task 1.3 (D7): the version each Start's audit row names —
        # a seam (None: this build's ``__version__``).
        self._app_version = app_version if app_version is not None else __version__
        # Privacy-professional-controls plan Task 1.3 (C2): the audit record.
        # None records nothing (every test construction site that does not
        # ask for it). ``begin`` at Start is the one audit write that refuses;
        # every later record is best-effort and never raises into custody.
        self._audit = audit
        # Privacy-professional-controls plan Task 2.3 (C1, D4): the Past-
        # sessions archive every Complete writes into before its key goes,
        # and every Discard clears an unfinished entry from before its key
        # goes. None keeps nothing (every test construction site that does
        # not ask for it); ``app.main`` passes the real store.
        self._past_sessions = past_sessions
        # Flow 3 step 4: whether the LAST successful Complete left its
        # Past-sessions entry for the next reconciliation (its marker could
        # not be removed after the key) — read by the screens for the
        # truthful status line.
        self._last_complete_deferred = False
        # Development-recordings plan Task 2.1: whether the LAST Complete kept
        # the recording's audio (``last_completion_kept``) — reset at each
        # attempt, so a failed Complete reads False.
        self._last_completion_kept = False
        # The clinic registry's ``user_id`` for a linked Start's clinic (D8),
        # registered after construction because the registry is the main
        # window's (``set_clinic_user_resolver``); None records no user id.
        self._clinic_user_resolver: Callable[[str], str | None] | None = None
        # Note-learning plan D1/D2: builds the live worker at start(); None
        # keeps today's batch-only behaviour, and so does a factory that
        # returns None for one Start (installation plan round 35 MED-001: the
        # ML imports are still warming up). Settable after construction
        # (``set_live_transcriber_factory``) because the live view it posts
        # to is built after the controller (``app.main`` → ``MainWindow``).
        self._live_transcriber_factory = live_transcriber_factory
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
        # reservations, session_id -> in-flight holder count (each discard,
        # and since the draft-write plan the one draft write). discard()
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
        # Cliniko draft-write plan D9: the ONE in-flight draft write. It
        # holds a counted entry in ``_custody_reservations`` for its session
        # (so the sweep and recovery list keep the session protected) PLUS
        # this marker, which is what REFUSES: start(), discard() (both of which
        # deliberately admit a concurrent DISCARD), the complete family,
        # adopt_queued, begin_generation, begin_enrolment,
        # destroy_recovered_crypto and retirement consult it ahead of the
        # discard-reservation check and raise ``WriteInFlightError`` (a held
        # generation or enrolment lease, checked first where a method checks
        # one, still refuses with its own error). complete_without_note checks
        # it too but is already excluded by its generation lease (lease and
        # write refuse each other). The recovered-path target check still
        # names "a discard" for a held id, and transcribe() refuses on its
        # PROCESSING-state guard: neither is reachable for the writing
        # session (it is the live QUEUED one, excluded from the recovery
        # list). Set and cleared together, under the lock.
        self._write_reservation: WriteReservation | None = None
        self._writing_id: str | None = None
        # Practitioner-profile plan D15: the ONE in-flight voice-enrolment
        # activity. NOT state-agnostic (unlike the generation lease): it is
        # refused while a session is active and it makes start()/resume()
        # refuse — the enrolment capture owns the microphone. The optional
        # blocker lets the app register an activity the controller cannot
        # see (the microphone screen's benchmark worker): a non-None string
        # is the reason begin_enrolment() refuses.
        self._enrolment: EnrolmentLease | None = None
        self._enrolment_blocker: Callable[[], str | None] | None = None
        # Cliniko workflow safeguards plan D2 (peer r2 PR-MED-001): THE
        # reference registry, session_ref -> session_id, in memory for the
        # controller's lifetime and never persisted. A ref is minted by
        # start(), kept through retirement (the live ref becomes the indexed
        # ref) and removed when its session is completed or discarded;
        # ``forget_session_ref`` removes an expired one. A session-bound
        # command resolves to exactly the entry its ref names.
        self._session_refs: dict[str, str] = {}

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

    @property
    def session_ref(self) -> str | None:
        """The tracked session's D2 reference (None with no session)."""
        with self._lock:
            return self._live.session_ref if self._live is not None else None

    @property
    def recorded_seconds(self) -> int:
        """Seconds of audio the tracked session has written (Task 4.5; the
        panel's and the Session screen's timer). Counted from the store's
        chunks — one second each (``CHUNK_BYTES``), the final partial chunk
        of a Finish counting as a whole one — so a pause, during which no
        chunk is written, never adds time, and audio still buffered in the
        capture worker (under a second) is not yet counted. Frozen at the
        closing count after Finish or a failure; 0 with no session."""
        with self._lock:
            live = self._live
            if live is None:
                return 0
            chunks = live.store.next_index if live.store is not None else live.closed_chunks
        return int(chunks * _CHUNK_SECONDS)

    @property
    def live_failure(self) -> LiveFailure | None:
        """Why the tracked session's live transcriber switched itself off
        (D7: "Spoken pause unavailable for this recording"), or None while
        it runs or when none is attached — ``live_transcription_attached``
        tells those two apart."""
        with self._lock:
            live = self._live
            worker = live.live_transcriber if live is not None else None
        return worker.failed_reason if worker is not None else None

    @property
    def live_transcription_attached(self) -> bool:
        """True while a live transcriber is attached to the tracked session
        (from Start until the processing run claims it at Finish)."""
        with self._lock:
            live = self._live
            return live is not None and live.live_transcriber is not None

    def resolve_session_ref(self, session_ref: str) -> str | None:
        """The session id ``session_ref`` names, or None when it no longer
        resolves (completed, discarded, expired, or minted before a restart)
        — a named refusal for the caller, never "the newest session"."""
        with self._lock:
            return self._session_refs.get(session_ref)

    def session_ref_for(self, session_id: str) -> str | None:
        """The reference ``session_id`` is registered under, or None (Task
        5.5: the Unreviewed banner names its session by this, never by id)."""
        with self._lock:
            return self._ref_for_locked(session_id)

    def register_session_ref(self, session_id: str) -> str:
        """Task 5.5 (D2, D6): the reference of a session found on disk at app
        start — its existing one, else a fresh one minted now. Refs never
        survive a restart, so an indexed session needs one for its banner."""
        if not re.fullmatch(SESSION_ID_PATTERN, session_id):
            raise SessionControllerError("not a session id")
        with self._lock:
            ref = self._ref_for_locked(session_id)
            if ref is None:
                ref = _new_session_ref()
                self._session_refs[ref] = session_id
            return ref

    def _ref_for_locked(self, session_id: str) -> str | None:
        return next((r for r, sid in self._session_refs.items() if sid == session_id), None)

    def forget_session_ref(self, session_id: str) -> None:
        """Remove every reference to ``session_id`` (its session expired or
        was removed outside the controller)."""
        with self._lock:
            self._forget_refs_locked(session_id)

    def _forget_refs_locked(self, session_id: str) -> None:
        for ref in [r for r, sid in self._session_refs.items() if sid == session_id]:
            del self._session_refs[ref]

    def active_session_ids(self) -> frozenset[str]:
        """Session ids the expiry sweep must skip (keyed off STATE — plan
        Critical Constraint: the sweep never touches recording/paused/
        processing sessions)."""
        with self._lock:
            live = self._live
            if live is not None and live.session.state in ACTIVE_STATES:
                return frozenset({live.session.session_id})
            return frozenset()

    def live_session_ids(self) -> frozenset[str]:
        """The tracked session's id in ANY state, or empty (SIMP-016: the
        reference prune keeps the live session's reference)."""
        with self._lock:
            live = self._live
            return frozenset({live.session.session_id}) if live is not None else frozenset()

    def referenced_session_ids(self) -> frozenset[str]:
        """Every session id the reference registry names (SIMP-016: what the
        reference prune may drop — ``MainWindow.prune_session_refs``)."""
        with self._lock:
            return frozenset(self._session_refs.values())

    # --- controls ----------------------------------------------------------

    def start(
        self,
        device_id: int,
        *,
        consent: ConsentAttestation,
        context: EncounterContext | None = None,
        mode: SessionMode = SessionMode.NORMAL,
        development_consent: DevelopmentConsent | None = None,
    ) -> RecordingSession:
        """Start a new recording session.

        Refused (``ConsentRequiredError``, before anything is created)
        without a ``ConsentAttestation``, or with one that does not name
        ``context``'s note (Constraint 4). ``context`` None is an UNLINKED
        recording (the desktop Start); a linked Start passes the context its
        verification produced. ``mode`` (pilot plan D1) is the Start
        funnel's read of the pilot setting at the click — fixed for this
        recording, written to ``encounter.enc`` and the audit row.
        ``development_consent`` (development-recordings plan D2) is the
        funnel's resolution of the development setting and the second tick
        at the click — None (not kept, C3) unless both were given; held on
        the session and written to ``encounter.enc`` and (its wording
        version) the audit row.

        Ordering (binding key-custody decision): the audit row (privacy-
        professional-controls Flow 1 — BEFORE the previous session is
        retired; ``AuditWriteError`` refuses Start here with nothing changed)
        -> retire the previous session -> session dir -> DPAPI-wrap
        the fresh session key to ``key.dpapi`` (atomic, durable) -> write
        ``encounter.enc`` (the consent and context, D11; atomic, durable) ->
        ONLY THEN create ``audio.enc`` -> start the capture worker (the
        single writer) -> state=recording. A crash after the key leaves no
        audio without its consent record. Any failure after the row marks
        it ``start_failed`` (best-effort)."""
        if not isinstance(consent, ConsentAttestation):
            raise ConsentRequiredError("start refused: no recording consent was given")
        if context is not None and not isinstance(context, EncounterContext):
            raise SessionControllerError("start refused: the encounter context is malformed")
        if not isinstance(mode, SessionMode):
            raise SessionControllerError("start refused: the recording mode is malformed")
        if development_consent is not None and not isinstance(
            development_consent, DevelopmentConsent
        ):
            raise SessionControllerError(
                "start refused: the development consent is malformed"
            )
        try:
            bind_consent(consent, context)
        except ValueError:
            raise ConsentRequiredError(
                "start refused: the consent does not name this note"
            ) from None
        with self._lock:
            # Task 6.3: start() on a queued session RETIRES it — dropping the
            # in-memory handle (directory, crypto) a generation worker
            # depends on — so it is refused outright while the lease is held.
            self._refuse_while_generating("start")
            self._refuse_while_enrolling("start")
            # D9: start() retires the queued session a draft write holds.
            self._refuse_while_writing("start")
            live = self._live
            if live is not None and live.session.state in ACTIVE_STATES:
                raise SessionActivityError(
                    "another session is active (single-active-session invariant)"
                )
            # Privacy-professional-controls Flow 1: the session (and so its
            # id) is built BEFORE the retire — the constructor is pure — and
            # its audit row written next. A failed row write refuses Start
            # HERE (AuditWriteError, C2), with the previous QUEUED session
            # still installed and nothing of the new session on disk.
            session = RecordingSession(  # state defaults to idle
                key_reference="key.dpapi",
                consent=consent,
                encounter_context=context,
                mode=mode,
                development_consent=development_consent,
            )
            if self._audit is not None:
                self._audit.begin(
                    session.session_id,
                    consent=consent,
                    context=context,
                    user_id=self._audit_user_id(context),
                    started_at=session.created_at,
                    mode=mode,
                    app_version=self._app_version,
                    development_consent_version=(
                        development_consent.text_version
                        if development_consent is not None
                        else None
                    ),
                )
            try:
                return self._start_locked(live, session, device_id)
            except BaseException:
                # Flow 1 step 5: EVERY failure after a successful ``begin`` —
                # the retire refusal (the previous session stays installed),
                # the directory creation, the key, the encounter record, the
                # store, the device — marks the row (best-effort, C2).
                if self._audit is not None:
                    self._audit.record_start_failed(session.session_id)
                raise

    def _start_locked(
        self, live: _LiveSession | None, session: RecordingSession, device_id: int
    ) -> RecordingSession:
        """``start()``'s body after the audit row, under ``self._lock`` (the
        caller's one hold). Every exception it raises is marked
        ``start_failed`` by the caller."""
        if live is not None:
            # Previous session is queued/failed/terminal: drop our
            # in-memory handle. Its on-disk custody (if any) remains, so
            # a recoverable session stays recoverable via the sweep and
            # recovery screen.
            self._retire_locked(live)
        directory = self._root / session.session_id
        crypto = SessionCrypto()
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StoreWriteError(f"failed creating session directory: {exc}") from exc
        store: SessionChunkStore | None = None
        live_worker: LiveTranscriber | None = None
        try:
            wrap_key_to_file(crypto, directory)  # key BEFORE first chunk
            # D11: the consent (and context) record, after the key and
            # BEFORE audio.enc; the failure cleanup below removes it.
            write_encounter_record(
                directory,
                crypto,
                session.session_id,
                EncounterRecord(
                    consent=session.consent,
                    context=session.encounter_context,
                    mode=session.mode,
                    development_consent=session.development_consent,
                ),
            )
            store = SessionChunkStore.create(
                directory / AUDIO_FILENAME, crypto, session.session_id
            )
            chunk_store = store
            if self._live_transcriber_factory is not None:
                # D1: the live worker is fed by a tee AFTER the store's
                # encrypting write; it holds no crypto and no store handle.
                # Started BEFORE the capture worker so the first chunk
                # finds it running (a feed before start fails it). None:
                # this recording runs without one (batch at Finish).
                live_worker = self._live_transcriber_factory()
                if live_worker is not None:
                    live_worker.start()
            worker = CaptureWorker(
                self._backend,
                device_id,
                _tee_sink(chunk_store, live_worker),
                on_failure=self._on_capture_failure,
            )
            worker.start()
        except Exception:
            # Nothing recoverable exists yet — clean up completely
            # (key first) rather than leaving an empty orphan.
            if live_worker is not None:
                # Under the lock: the short bound (nothing was fed yet, the
                # worker holds no plaintext; a load still in flight clears
                # itself on exit).
                live_worker.stop(timeout=_LIVE_STOP_LOCKED_TIMEOUT_S)
            if store is not None:
                store.close()
            discard_session(directory, crypto)
            raise
        if live_worker is None and self._live_transcriber_factory is not None:
            if self._logger is not None:
                # Round 35 MED-001: the factory withheld the worker (logged
                # only once the Start has succeeded).
                log_event(
                    self._logger,
                    "live_transcriber",
                    session_id=session.session_id,
                    state="not_attached",
                )
        installed = _LiveSession(session, directory, crypto, store, worker)
        installed.live_transcriber = live_worker
        installed.session_ref = _new_session_ref()
        self._session_refs[installed.session_ref] = session.session_id
        self._live = installed
        self._transition_locked(installed, SessionState.RECORDING)
        return installed.session

    def pause(self) -> RecordingSession:
        """Pause capture. When this returns, no further chunk write can
        happen until resume(): the worker barrier guarantees any in-flight
        chunk is fully written first (or was cleanly dropped)."""
        with self._lock:
            live = self._require_state(SessionState.RECORDING)
            worker = live.worker
            live_worker = live.live_transcriber
        if worker is not None:
            worker.pause()  # OUTSIDE the lock: barrier wait must not block callbacks
        if live_worker is not None:
            # D2: gate feeding only AFTER the capture barrier — every chunk
            # enqueued before the pause has passed through the tee.
            live_worker.pause()
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
            self._refuse_while_enrolling("resume")
            live = self._require_state(SessionState.PAUSED)
            if live.live_transcriber is not None:
                live.live_transcriber.resume()  # BEFORE capture resumes (D2 gate)
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
            if live.session.state not in CAPTURING_STATES:
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
                self._fail_locked(live)  # stops an attached live worker too
                return live.session
            finally:
                if live.store is not None:
                    live.closed_chunks = live.store.next_index
                live.store = None
            if live.live_transcriber is not None:
                # D2: seal only — one queue sentinel, no drain here. The tail
                # is transcribed by the worker and collected on the processing
                # thread by the transcriber callable (``claim_live_transcriber``).
                live.live_transcriber.seal()
            self._transition_locked(live, SessionState.PROCESSING)
            return live.session

    def claim_live_transcriber(self) -> LiveTranscriber | None:
        """Hand the sealed live worker to the transcriber callable (note-
        learning plan Task 1.3). Legal ONLY inside a ``transcribe()`` run —
        the session is PROCESSING with the ``transcribing`` flag set, so
        Discard is already refused for the whole run (round 42 MED-003) and
        no controller path can stop the worker underneath its owner. Detaches
        it: from here the callable owns its drain, its release and its stop.
        ``None`` when the session runs without a live worker (batch as today).
        Any other state is a misuse and raises."""
        with self._lock:
            live = self._require_state(SessionState.PROCESSING)
            if not live.transcribing:
                raise SessionActivityError(
                    "the live transcriber can be claimed only inside a transcription run"
                )
            worker = live.live_transcriber
            live.live_transcriber = None
            return worker

    def set_live_transcriber_factory(
        self, factory: Callable[[], LiveTranscriber | None] | None
    ) -> None:
        """Register (or clear) the live-worker factory ``start()`` uses. Takes
        effect from the NEXT start; an active session keeps its worker. A
        factory that returns None records that Start without a live worker."""
        with self._lock:
            self._live_transcriber_factory = factory

    def set_clinic_user_resolver(self, resolver: Callable[[str], str | None] | None) -> None:
        """Register (or clear) how a linked Start finds the clinic's Cliniko
        ``user_id`` for its audit row (privacy-professional-controls D8): the
        clinic registry, by clinic id, read at each Start."""
        with self._lock:
            self._clinic_user_resolver = resolver

    # --- the audit record (privacy-professional-controls plan Task 1.3) ------

    def _audit_user_id(self, context: EncounterContext | None) -> str | None:
        """Call under ``self._lock``. The linked clinic's user id, or None —
        never a reason to refuse Start (a lookup that fails records none)."""
        resolver = self._clinic_user_resolver
        if context is None or resolver is None:
            return None
        try:
            return resolver(context.clinic_id)
        except Exception:  # noqa: BLE001 - an absent id, never a Start failure
            return None

    def _audit_created_at(self, directory: Path) -> float | None:
        """D8: the session's creation time, read BEFORE its directory goes,
        for a ``pre_audit`` row (a session started before the audit existed).
        Never raises; None when there is no audit to feed."""
        return audit_created_at(directory) if self._audit is not None else None

    def _audit_completion(
        self,
        session_id: str,
        facts: CompletionFacts,
        deletion: Literal["completed", "completed_without_note"],
        created_at: float | None,
    ) -> None:
        """Best-effort (C2): ``AuditLog.update`` never raises."""
        if self._audit is not None:
            self._audit.record_completion(
                session_id, facts, deletion=deletion, created_at=created_at
            )

    def _audit_discarded(self, session_id: str, created_at: float | None) -> None:
        """Best-effort (C2): ``AuditLog.update`` never raises."""
        if self._audit is not None:
            self._audit.record_deletion(session_id, "discarded", created_at=created_at)

    # --- the Past-sessions archive (privacy-professional-controls Task 2.3) --

    @property
    def last_complete_deferred(self) -> bool:
        """True when the last successful Complete published its Past-sessions
        entry but could not remove the entry's ``pending`` marker after the
        key (Flow 3 step 4): the copy appears after the next reconciliation."""
        with self._lock:
            return self._last_complete_deferred

    def _complete_locked(
        self,
        directory: Path,
        crypto: SessionCrypto,
        *,
        delete_note: bool = False,
        label: KeepLabel | None = None,
        mode: SessionMode | None = None,
        kept: bool = False,
    ) -> tuple[CompletionFacts, float | None]:
        """Call under ``self._lock``, after every refusal: THE one call of
        ``complete_session`` for all five Complete paths, with the archive's
        writer when there is an archive (C1 / D4). Returns the facts and the
        pre-audit date read BEFORE the directory went. An archive failure
        before the key boundary raises ``PastSessionWriteError`` (key,
        state, lease and reservation all kept — the caller's own raise
        semantics); every other failure propagates exactly as before.
        ``mode`` is a live session's own (``keep_label_for_mode``).
        ``kept`` (development-recordings plan Task 2.1, C3): the recording
        was started under written development consent — a live path's from
        its own ``development_consent``, a recovered one's from the
        checkout's one decrypt — so its audio joins the entry; the ACTUAL
        outcome is ``last_completion_kept()``."""
        created_at = self._audit_created_at(directory)
        label = keep_label_for_mode(label, mode)
        keeper = self._past_sessions.keeper(label) if self._past_sessions is not None else None
        self._last_completion_kept = False
        try:
            facts = complete_session(
                directory, crypto, delete_note=delete_note, keep=keeper, keep_audio=kept
            )
        except ArchiveWriteError:
            raise PastSessionWriteError() from None
        self._last_complete_deferred = facts.commit_deferred
        self._last_completion_kept = facts.recording_kept
        return facts, created_at

    def last_completion_kept(self) -> bool:
        """True when the last Complete kept the recording's audio in its
        Past-sessions entry (development-recordings plan Task 2.1, round 1
        PR-MED-005) — the ACTUAL outcome, never the consent: a consented mock
        session, or a failed Complete, reads False. Content-free."""
        with self._lock:
            return self._last_completion_kept

    def _remove_unfinished_entry_locked(self, session_id: str) -> None:
        """Call under ``self._lock``, BEFORE any path other than Complete
        deletes ``session_id``'s key (C1's ordering rule): remove any Past-
        sessions entry an interrupted Complete left for it, key first.
        ``PastSessionCleanupError`` when it could not be — the key must then
        stay, or the entry could later be committed as a finished one."""
        if self._past_sessions is None:
            return
        if not self._past_sessions.remove_pending_entry(session_id):
            raise PastSessionCleanupError()

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

    def complete(self, *, label: KeepLabel | None = None) -> RecordingSession:
        """The explicit Phase-2 Complete action (distinct from Discard):
        queued -> written via the store's binding ordering primitive
        (fsync transcript -> verify decrypt round-trip -> the Past-sessions
        entry -> delete key = cryptographic deletion). Any verification or
        archive failure keeps the key and leaves the session queued.
        ``label`` is what the UI resolved for the entry (D5; None: "Name not
        available")."""
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
            # admitted, pinned by their tests). A draft write's reservation
            # is refused by name first (D9).
            self._refuse_while_writing("complete")
            if self._custody_reservations:
                raise SessionActivityError(
                    "a discard is completing; the session cannot be completed"
                )
            live = self._require_state(SessionState.QUEUED)
            # Round 7 MED-001: a live worker still attached at QUEUED (a
            # transcriber callable that never claimed it — not the shipped
            # one) holds plaintext products; stop it BEFORE the key goes —
            # and (peer round 9 PR-MED-017) refuse, staying QUEUED, when it
            # cannot be confirmed cleared.
            if not self._stop_live_locked(live):
                self._refuse_uncleared_live("complete")
            facts, created_at = self._complete_locked(  # raises -> stays queued
                live.directory,
                live.crypto,
                label=label,
                mode=live.session.mode,
                kept=live.session.development_consent is not None,
            )
            self._transition_locked(live, SessionState.WRITTEN)
            session = live.session
            self._live = None
            self._audit_completion(session.session_id, facts, "completed", created_at)
            return session

    def complete_without_note(
        self, lease: GenerationLease, *, label: KeepLabel | None = None
    ) -> RecordingSession:
        """The clinician's explicit 'complete without a note' exit (Flow 2,
        Task 7.1): complete the queued session WITHOUT its ``note.enc``
        (``delete_note=True`` — excluded from verification and from the
        Past-sessions entry, gone with the key and the directory; D6), then
        the same binding transcript ordering as ``complete()`` (fsync ->
        verify -> the entry -> delete key). Never a silent deletion — the
        Note tab's delete-note control confirms it.

        Runs UNDER the HELD generation lease and CONSUMES it only on success
        (round 35 PR-MED-001). The Note tab's abandon path holds the lease for
        the whole review; releasing it BEFORE completing was the defect — a
        completion failure then left an unleased QUEUED session mid-review. So
        this requires the exact held lease (identity, like
        ``with_generation_custody``), keeps the ``_custody_reservations``
        exclusion, runs ``complete_session`` under the lock (the same
        no-unlocked-window shape as ``complete()``), and clears
        ``self._generation`` ONLY after the WRITTEN transition. A failure
        raises with the lease still held, the session still QUEUED, and the
        key retained."""
        with self._lock:
            if self._generation is None or self._generation is not lease:
                raise GenerationInProgressError(
                    "complete-without-note requires the held generation lease"
                )
            self._refuse_while_writing("complete-without-note")
            if self._custody_reservations:
                raise SessionActivityError(
                    "a discard is completing; the session cannot be completed"
                )
            live = self._require_state(SessionState.QUEUED)
            if not self._stop_live_locked(live):  # round 7 MED-001 / round 9 PR-MED-017
                self._refuse_uncleared_live("complete-without-note")  # lease kept
            facts, created_at = self._complete_locked(  # raises -> lease kept
                live.directory,
                live.crypto,
                delete_note=True,
                label=label,
                mode=live.session.mode,
                kept=live.session.development_consent is not None,
            )
            self._transition_locked(live, SessionState.WRITTEN)
            session = live.session
            self._live = None
            self._generation = None  # consume the lease only on success
            self._audit_completion(
                session.session_id, facts, "completed_without_note", created_at
            )
            return session

    def complete_deleting_saved_note(self, *, label: KeepLabel | None = None) -> RecordingSession:
        """The POST-Save 'delete note and complete without one' exit (round 36
        PR-MED-001): the note is already committed and NO lease is held, so
        this completes the queued session WITHOUT its ``note.enc`` (excluded
        from verification and from the Past-sessions entry, gone with the key
        and the directory; D6) with the same binding ordering as
        ``complete()``.

        Guarded like ``complete()``: refused while a generation lease is held
        (a regeneration is in flight — the pre-Save leased path
        ``complete_without_note(lease)`` owns that state) or while a discard is
        completing. A failure keeps the key and leaves the session queued.
        This is the pre-round-35 no-lease shape, restored as the SEPARATE
        guarded delete-saved-note path the round-35 leased change left
        without one."""
        with self._lock:
            self._refuse_while_generating("complete")
            self._refuse_while_writing("complete")
            if self._custody_reservations:
                raise SessionActivityError(
                    "a discard is completing; the session cannot be completed"
                )
            live = self._require_state(SessionState.QUEUED)
            if not self._stop_live_locked(live):  # round 7 MED-001 / round 9 PR-MED-017
                self._refuse_uncleared_live("complete")
            facts, created_at = self._complete_locked(
                live.directory,
                live.crypto,
                delete_note=True,
                label=label,
                mode=live.session.mode,
                kept=live.session.development_consent is not None,
            )
            self._transition_locked(live, SessionState.WRITTEN)
            session = live.session
            self._live = None
            self._audit_completion(
                session.session_id, facts, "completed_without_note", created_at
            )
            return session

    def discard(self) -> RecordingSession:
        """Discard the session: key deleted FIRST (cryptographic deletion),
        then best-effort removal of the artifacts."""
        with self._lock:
            # Task 6.3: Discard is key-first cryptographic deletion — refused
            # while the generation lease is held, same rationale as complete().
            self._refuse_while_generating("discard")
            # D9: a concurrent DISCARD stays admitted (its tests pin it), a
            # draft write in flight does not — Discard destroys its key.
            self._refuse_while_writing("discard")
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
            # Note-learning plan D2 (attached-worker ownership): a live worker
            # still attached here is UNCLAIMED — RECORDING, PAUSED, FAILED, or
            # PROCESSING before the callable claimed it (the ``transcribing``
            # guard above refuses the claimed case). It is stopped and joined
            # in the unlocked window below, beside the capture worker's stop
            # and under this discard's custody reservation, and its buffers
            # are confirmed cleared BEFORE ``discard_session`` destroys the
            # key. Outside the lock deliberately: the join is bounded by
            # ``LIVE_STOP_TIMEOUT_SECONDS`` and the controller lock is the
            # GUI's state-poll lock; the worker never calls back into the
            # controller, so either placement is deadlock-free.
            live_worker = live.live_transcriber
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
            # Privacy-professional-controls C1: an unfinished Past-sessions
            # entry for this session goes BEFORE its key — here, in this
            # same hold of the lock and before the reservation, so a refusal
            # changes nothing, and from here on the reservation keeps every
            # Complete (the only publisher) away from this id.
            self._remove_unfinished_entry_locked(session_id)
            self._reserve_custody_locked(session_id)
        try:
            if worker is not None:
                worker.stop(flush=False)  # OUTSIDE the lock; buffered audio dropped
            live_cleared = True
            if live_worker is not None:
                # Plaintext buffers dropped BEFORE the key goes (C7). A join
                # timeout is REPORTED below and REFUSES the deletion (peer
                # round 9 PR-MED-017): the key stays, the session is routed to
                # FAILED (its capture worker is already stopped, so RECORDING
                # / PAUSED would be a lie; FAILED keeps key + chunks and Discard
                # legal), and the next Discard retries the idempotent stop.
                live_cleared = live_worker.stop()
            with self._lock:
                if live_worker is not None:
                    self._record_live_stop_locked(live, live_worker, live_cleared)
                    if not live_cleared and live.session.state != SessionState.DISCARDED:
                        live.worker = None
                        if live.session.state in (
                            SessionState.RECORDING,
                            SessionState.PAUSED,
                            SessionState.PROCESSING,
                        ):
                            if live.store is not None:
                                live.store.close()
                                live.store = None
                            self._transition_locked(live, SessionState.FAILED)
                        self._refuse_uncleared_live("discard")
                # PR-HIGH-001: operate on the SNAPSHOT taken under the first
                # lock. Re-fetching self._live here allowed a concurrent start()
                # (legal for a queued/failed session) to install a NEW recording
                # whose key this method would then cryptographically delete —
                # wrong-session data loss. The snapshot is the session the
                # caller asked to discard; the on-disk artifacts deleted below
                # are resolved from ITS directory and crypto only.
                live.worker = None
                if live.session.state == SessionState.DISCARDED:
                    # Concurrent discard already completed — and recorded it
                    # in the audit; this call records nothing new.
                    return live.session
                if live.store is not None:
                    live.store.close()
                    live.store = None
                created_at = self._audit_created_at(live.directory)
                discard_session(live.directory, live.crypto)  # key-first, destroys crypto
                self._transition_locked(live, SessionState.DISCARDED)
                session = live.session
                if self._live is live:
                    self._live = None
                self._audit_discarded(session_id, created_at)
                return session
        finally:
            with self._lock:
                self._release_custody_locked(session_id)

    def adopt_queued[T](
        self, directory: Path, reader: Callable[[Path, SessionCrypto], T]
    ) -> tuple[RecordingSession, T]:
        """Cliniko workflow safeguards plan Task 5.4, decided option (a):
        reinstall a RETIRED session (one a Start or crash left on disk with a
        transcript) as THE live QUEUED session, so the review, the lease,
        ``with_generation_custody``, Save and Complete are the live path that
        exists. Returns the session and ``reader(directory, crypto)``'s value
        (the caller's transcript and saved-note read), run before anything is
        installed — a reader failure (a note that fails verification, say)
        refuses the whole adoption, so a note is never silently replaced.

        Refusals mirror ``start()``: while the generation lease is held (this
        retires the session a generation depends on), while any discard holds
        a custody reservation, while a session is recording, paused or
        processing, and for a directory that is not a session of THIS root or
        is already the live one. ``ReviewOpenRefused`` names a session that
        cannot be opened. The consent and context come from ``encounter.enc``,
        decrypted HERE — adoption is a checkout (Critical Constraint 7). A
        live queued or failed session is retired exactly as ``start()``
        retires it; the adopted session keeps the reference it already had
        (D2), else one is minted. The key is unwrapped once, and destroyed
        (in memory) on every refusal after the unwrap."""
        with self._lock:
            self._refuse_while_generating("open for review")
            self._refuse_while_writing("open for review")
            if self._custody_reservations:
                raise SessionActivityError(
                    "a discard is completing; open for review after it finishes"
                )
            live = self._live
            if live is not None and live.session.state in ACTIVE_STATES:
                raise SessionActivityError(
                    "another session is active (single-active-session invariant)"
                )
            session_id = directory.name
            if directory.parent != self._root or not re.fullmatch(
                SESSION_ID_PATTERN, session_id
            ):
                raise SessionActivityError("open for review refused: not a session of this app")
            if live is not None and live.session.session_id == session_id:
                raise SessionActivityError("open for review refused: the session is already open")
            if not (directory / TRANSCRIPT_FILENAME).is_file():
                raise ReviewOpenRefused("no_transcript")
            try:
                crypto = unwrap_key_from_file(directory)
            except KeyCustodyError:
                raise ReviewOpenRefused("key_unavailable") from None
            try:
                try:
                    record = read_encounter_record(directory, crypto, session_id)
                except EncounterUnavailable:
                    raise ReviewOpenRefused("consent_unavailable") from None
                try:
                    value = reader(directory, crypto)
                except Exception as exc:
                    raise ReviewOpenRefused("unreadable") from exc
                session = RecordingSession(
                    session_id=session_id,
                    encounter_context=record.context,
                    consent=record.consent,
                    key_reference="key.dpapi",
                    # Pilot plan D1: the mode it was started in (v1: normal).
                    mode=record.mode,
                    # Development-recordings D2: as it was decided at Start
                    # (a v1 or v2 record: None, not kept).
                    development_consent=record.development_consent,
                    state=SessionState.QUEUED,
                )
                if live is not None:
                    self._retire_locked(live)  # raises -> nothing installed
            except BaseException:
                crypto.destroy()
                raise
            ref = self._ref_for_locked(session_id)
            if ref is None:
                ref = _new_session_ref()
                self._session_refs[ref] = session_id
            adopted = _LiveSession(session, directory, crypto, store=None, worker=None)
            adopted.session_ref = ref
            self._live = adopted
            if self._logger is not None:
                log_event(
                    self._logger,
                    "session_transition",
                    session_id=session_id,
                    session_state=SessionState.QUEUED.value,
                )
            return session, value

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
            self._refuse_while_writing("generation")
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

    # --- voice enrolment activity (practitioner-profile plan D15) ----------

    def set_enrolment_blocker(self, blocker: Callable[[], str | None] | None) -> None:
        """Register (or clear) the app-level activity check consulted by
        ``begin_enrolment``: return a short reason while an activity the
        controller cannot see — the microphone screen's benchmark worker —
        is running, else ``None``. Evaluated under the controller lock."""
        with self._lock:
            self._enrolment_blocker = blocker

    def begin_enrolment(self) -> EnrolmentLease:
        """Acquire THE enrolment activity — call BEFORE the capture starts.

        STATE-AWARE, unlike the generation lease: refused with
        ``SessionActivityError`` while a session is recording, paused or
        processing (transcription runs in ``processing``), while a discard
        holds a custody reservation (its worker join releases the device
        outside the lock — the enrolment capture must not open it
        underneath), while the registered blocker reports an activity, and
        while another enrolment is held. Once held, ``start()`` and
        ``resume()`` refuse until ``end_enrolment``."""
        with self._lock:
            if self._enrolment is not None:
                raise SessionActivityError("a voice enrolment is already in progress")
            live = self._live
            if live is not None and live.session.state in ACTIVE_STATES:
                raise SessionActivityError(
                    f"voice enrolment refused: a session is {live.session.state}"
                )
            self._refuse_while_writing("voice enrolment")
            if self._custody_reservations:
                raise SessionActivityError(
                    "voice enrolment refused: a discard is in flight; retry after it finishes"
                )
            if self._enrolment_blocker is not None:
                reason = self._enrolment_blocker()
                if reason is not None:
                    raise SessionActivityError(f"voice enrolment refused: {reason}")
            lease = EnrolmentLease()
            self._enrolment = lease
            return lease

    def end_enrolment(self, lease: EnrolmentLease) -> None:
        """Release the activity — after the capture, the embedding, the save
        and the caller's result handler, on every path. Idempotent for the
        released token; a token that is NOT the held one raises."""
        with self._lock:
            if self._enrolment is None:
                return
            if self._enrolment is not lease:
                raise SessionControllerError(
                    "end_enrolment called with a lease that is not held"
                )
            self._enrolment = None

    @property
    def enrolling(self) -> bool:
        with self._lock:
            return self._enrolment is not None

    def _refuse_while_enrolling(self, operation: str) -> None:
        """Call under ``self._lock``."""
        if self._enrolment is not None:
            raise SessionActivityError(
                f"{operation} refused: a voice enrolment is in progress"
            )

    def reserved_session_ids(self) -> frozenset[str]:
        """Session ids an in-flight Discard (round 30) or draft write (D9)
        has reserved — the
        reservation-only view, for tests and diagnostics.

        External protection consumers (the recovery-list exclusion, the
        24 h sweep) must NOT compose this with separate live-session reads:
        they consume ``custody_protected_ids()``, the single-lock snapshot
        (round 31 — the split-read composition was itself a race)."""
        with self._lock:
            return frozenset(self._custody_reservations)

    def custody_protected_ids(self) -> frozenset[str]:
        """ONE atomic snapshot of every custody-protected session id: all
        in-flight Discard (round 30) and draft-write (D9) reservation targets
        PLUS the current
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

    def complete_recovered(
        self,
        directory: Path,
        crypto: SessionCrypto,
        *,
        label: KeepLabel | None = None,
        kept: bool = False,
    ) -> None:
        """Complete a RECOVERED session (Flow 2 ordering via
        ``complete_session``: fsync -> verify -> the Past-sessions entry ->
        delete key), through the lease-aware coordinator instead of a raw
        store-primitive call. A recovered session that once failed IS
        archived: Complete, not the earlier failure, decides (D6).
        ``kept`` (development-recordings plan Task 2.1) is the UI's, from the
        checkout record it holds (``MainWindow.session_kept_for``) — this
        controller holds no record and never reads ``encounter.enc``
        (privacy plan C7: the one decrypt is the checkout's)."""
        with self._lock:
            self._refuse_while_generating("complete")
            self._refuse_reserved_target_locked(directory, "complete")
            facts, created_at = self._complete_locked(
                directory, crypto, label=label, kept=kept
            )
            self._forget_refs_locked(directory.name)  # D2: its ref stops resolving
            if re.fullmatch(SESSION_ID_PATTERN, directory.name):
                self._audit_completion(directory.name, facts, "completed", created_at)

    def discard_recovered(self, directory: Path, crypto: SessionCrypto | None) -> None:
        """Discard a RECOVERED session (key-first cryptographic deletion),
        through the lease-aware coordinator — any unfinished Past-sessions
        entry for it first (C1)."""
        with self._lock:
            self._refuse_while_generating("discard")
            self._refuse_reserved_target_locked(directory, "discard")
            self._remove_unfinished_entry_locked(directory.name)
            created_at = self._audit_created_at(directory)
            discard_session(directory, crypto)
            self._forget_refs_locked(directory.name)  # D2: its ref stops resolving
            if re.fullmatch(SESSION_ID_PATTERN, directory.name):
                self._audit_discarded(directory.name, created_at)

    def destroy_recovered_crypto(self, crypto: SessionCrypto) -> None:
        """Zeroize a recovered checkout's in-memory key copy (disk custody
        untouched), through the lease-aware coordinator: while a generation
        is in flight the key it depends on must not be destroyed under it.

        Refused COARSELY while any discard reservation is held (round 30),
        and by name while a draft write holds its reservation (D9):
        this operation carries no directory, so there is no identity to
        resolve a scoped check against — and the coarse refusal is a strict
        superset of the scoped one, failing toward safety at the cost of a
        transient retry."""
        with self._lock:
            self._refuse_while_generating("recovered-key destruction")
            self._refuse_while_writing("recovered-key destruction")
            if self._custody_reservations:
                raise SessionActivityError(
                    "recovered-key destruction refused: a discard is in flight"
                )
            crypto.destroy()

    def with_generation_custody[T](
        self, lease: GenerationLease, action: Callable[[Path, SessionCrypto], T]
    ) -> T:
        """Run ``action(directory, crypto)`` for the QUEUED live session under
        the HELD generation lease — the scoped custody access the live-path
        note-generation worker (compose) and the GUI-thread ``write_note``
        both need, WITHOUT exposing raw directory/crypto accessors (Task 7.2,
        round 25 LOW-002; the plan disprefers raw accessors).

        ``transcribe()``-style: snapshot ``(directory, crypto)`` under the
        lock with a lease-IDENTITY and QUEUED-state check, then run ``action``
        OUTSIDE the lock — compose (and, for 3B, a model provider) and the
        note write are not trivial and must never block observers or the
        failure callback. The lease — acquired via ``begin_generation()``
        before the worker started — is what keeps ``start()`` / ``complete()``
        / ``discard()`` / retirement from destroying this custody state for
        the WHOLE operation, so the snapshot stays valid across the unlocked
        call. A lease that is not the held one raises, so a stale caller can
        never reach another session's crypto through here."""
        with self._lock:
            if self._generation is None or self._generation is not lease:
                raise GenerationInProgressError(
                    "scoped generation access requires the held generation lease"
                )
            live = self._require_state(SessionState.QUEUED)
            directory = live.directory
            crypto = live.crypto
        return action(directory, crypto)

    # --- Cliniko draft-write custody (cliniko-draft-write plan D9) ----------

    def reserve_write(self, session_id: str) -> WriteReservation:
        """Reserve the QUEUED live session ``session_id`` for ONE Cliniko
        draft write — on the GUI thread, BEFORE the write's first worker is
        dispatched — or, momentarily, for the seen-mode Complete after a
        confirmed write (D6: ``complete_after_write`` consumes it, or the
        Complete click releases it on a refusal). The reservation is the
        existing counted custody
        reservation (``_custody_reservations``) plus the ``_writing_id``
        marker. The REFUSAL comes from the marker: while it is set, ``start``,
        ``discard``, ``complete``, ``complete_deleting_saved_note``,
        ``adopt_queued``, ``begin_generation``, ``begin_enrolment``,
        ``destroy_recovered_crypto`` and session retirement raise
        ``WriteInFlightError`` ahead of the discard-reservation check (where a
        method checks a generation or enrolment lease first, a held lease
        still refuses with its own error). ``complete_without_note``
        checks the marker too, but is already excluded by its lease: it needs
        a ``GenerationLease``, which cannot be held beside a write (each
        refuses the other). ``transcribe`` needs no check — it requires a
        PROCESSING session, and a write holds only a QUEUED one. The
        counted entry keeps the sweep and the recovery list protecting the
        session.

        Refused while a note generation holds its lease, while another write
        is reserved (``WriteInFlightError``), while a discard of the session
        is in flight, and unless ``session_id`` is the live session and it
        is QUEUED (a saved note waits for review there)."""
        with self._lock:
            self._refuse_while_generating("write")
            self._refuse_while_writing("write")
            live = self._require_state(SessionState.QUEUED)
            if live.session.session_id != session_id:
                raise SessionActivityError("write refused: that session is not the live one")
            if session_id in self._custody_reservations:
                raise SessionActivityError(
                    "write refused: a discard of this session is in flight"
                )
            reservation = WriteReservation(self, session_id)
            self._reserve_custody_locked(session_id)
            self._write_reservation = reservation
            self._writing_id = session_id
            return reservation

    def _release_write(self, reservation: WriteReservation) -> None:
        """``WriteReservation.release``: drop the held reservation's custody
        entry and marker together, under the lock. A token that is not the
        held one — already released, or never held — changes nothing."""
        with self._lock:
            if self._write_reservation is not reservation or self._writing_id is None:
                return
            self._release_write_locked()

    def _release_write_locked(self) -> None:
        """Call under ``self._lock`` with a write reservation held: drop its
        counted custody entry and its marker TOGETHER (the release and the
        completion's consumption share this one body)."""
        if self._writing_id is not None:
            self._release_custody_locked(self._writing_id)
        self._write_reservation = None
        self._writing_id = None

    def writing_session_id(self) -> str | None:
        """The session a draft write holds, or None — for the UI's
        refusals (the Clinics tab's Replace key, "Open for review")."""
        with self._lock:
            return self._writing_id

    def with_write_custody[T](
        self, reservation: WriteReservation, action: Callable[[Path, SessionCrypto], T]
    ) -> T:
        """Run ``action(directory, crypto)`` for the QUEUED live session under
        the HELD write reservation — THE accessor the draft write uses for
        its session files (``write.enc``), mirroring
        ``with_generation_custody``: the reservation's IDENTITY and the
        session's QUEUED state and id are checked under the lock, then
        ``action`` runs outside it. The reservation — taken before the first
        worker — is what keeps ``start`` / ``complete`` / ``discard`` /
        retirement from destroying this custody state for the whole write.
        A released, foreign or stale token raises, so a stale caller never
        reaches another session's crypto through here."""
        with self._lock:
            if self._write_reservation is None or self._write_reservation is not reservation:
                raise SessionActivityError(
                    "scoped write access requires the held write reservation"
                )
            live = self._require_state(SessionState.QUEUED)
            if live.session.session_id != reservation.session_id:
                raise SessionActivityError(
                    "scoped write access refused: the reserved session is not the live one"
                )
            directory = live.directory
            crypto = live.crypto
        return action(directory, crypto)

    def complete_after_write(
        self, reservation: WriteReservation, *, label: KeepLabel | None = None
    ) -> RecordingSession:
        """Complete the QUEUED live session after a CONFIRMED Cliniko draft
        write (D6, seen mode): the clinician pressed Complete once the draft
        showed in Cliniko. ``reservation`` is the one the Complete click took
        through ``reserve_write`` (the write's own was released when its
        result was recorded).

        Everything runs under ONE hold of the lock, so no other custody
        action slots in between the checks, the key's destruction and the
        release: the reservation must be the HELD one and name the live
        QUEUED session (a write held for another session refuses
        ``WriteInFlightError``); no other custody reservation may be held;
        the write record must read ``written`` AND belong to the saved note
        now on disk (its ``note_identity``, D5 — a record of an earlier note
        never completes a later one). Then ``complete_session``'s ordering
        (fsync -> decrypt-verify the transcript and note -> delete
        ``key.dpapi`` -> zero the in-memory key) and the directory removed
        best-effort after the key; the session goes WRITTEN, which forgets
        its references (D2), and the reservation is consumed.

        Any refusal or verification failure raises with the key, the record,
        the QUEUED state AND the reservation kept — the CALLER releases it
        (the Transcript screen's ``_complete_after_write``), so a failed Complete
        can be retried with a fresh reservation. A failed directory removal
        after the key is not a failure: the keyless directory is an orphan
        the recovery list skips and the sweep removes."""
        with self._lock:
            self._refuse_while_generating("complete")
            if self._write_reservation is not reservation:
                if self._writing_id is not None:
                    raise WriteInFlightError("complete")
                raise SessionActivityError(
                    "complete after a write requires the held write reservation"
                )
            session_id = reservation.session_id
            if self._custody_reservations != {session_id: 1}:
                raise SessionActivityError(
                    "a discard is completing; the session cannot be completed"
                )
            live = self._require_state(SessionState.QUEUED)
            if live.session.session_id != session_id:
                raise SessionActivityError(
                    "complete after a write refused: the reserved session is not the live one"
                )
            status = read_write_record_status(live.directory, live.crypto, session_id)
            if status.outcome != "written":
                raise SessionActivityError(
                    "complete after a write refused: the Cliniko write is not confirmed"
                )
            if not status.note_matches:
                raise SessionActivityError(
                    "complete after a write refused: the write record does not match "
                    "the saved note (or the saved note cannot be read)"
                )
            if not self._stop_live_locked(live):  # round 7 MED-001 / round 9 PR-MED-017
                self._refuse_uncleared_live("complete")
            facts, created_at = self._complete_locked(
                live.directory,
                live.crypto,
                label=label,
                mode=live.session.mode,
                kept=live.session.development_consent is not None,
            )
            self._transition_locked(live, SessionState.WRITTEN)  # forgets its refs
            self._release_write_locked()
            session = live.session
            self._live = None
            self._audit_completion(session.session_id, facts, "completed", created_at)
            return session

    def write_record_status(self, session_id: str) -> WriteRecordStatus:
        """The live session's Cliniko write record, CONTENT-FREE (D5, R22-03):
        ``none`` when it has no ``write.enc``, ``unreadable`` when it cannot
        be read, else its outcome and whether it belongs to the saved note.
        THE accessor every consumer outside the write uses (the Complete
        routing, the Write button's state on a reopen, the ``write_uncertain``
        prefix, ``record_unreadable`` and the ``write_pending`` refusal);
        read under the lock, reserving nothing. ``SessionActivityError``
        unless ``session_id`` is the live session (only it has a key here)."""
        with self._lock:
            live = self._live
            if live is None or live.session.session_id != session_id:
                raise SessionActivityError(
                    "write record status refused: that session is not the live one"
                )
            return read_write_record_status(live.directory, live.crypto, session_id)

    def _refuse_while_writing(self, operation: str) -> None:
        """Call under ``self._lock``."""
        if self._writing_id is not None:
            raise WriteInFlightError(operation)

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
        if target in TERMINAL_STATES:
            # D2: a completed or discarded session's reference stops resolving.
            self._forget_refs_locked(live.session.session_id)
        if self._logger is not None:
            log_event(
                self._logger,
                "session_transition",
                session_id=live.session.session_id,
                session_state=target.value,
            )

    def _fail_locked(self, live: _LiveSession) -> None:
        """Route to failed (RECOVERABLE): stop writing, keep key + chunks.
        An attached live worker is stopped too (D2 ownership) — the failed
        session's plaintext must not keep being transcribed; the key is NOT
        destroyed here, so the short in-lock bound is enough and a timeout
        leaves it attached for Discard to retry (the ONE caller of the stop
        helper that may ignore its verdict: no custody is destroyed here)."""
        if live.store is not None:
            live.closed_chunks = live.store.next_index
            live.store.close()
            live.store = None
        self._stop_live_locked(live)
        self._transition_locked(live, SessionState.FAILED)

    def _stop_live_locked(self, live: _LiveSession) -> bool:
        """Call under ``self._lock``: stop an attached live worker with the
        short in-lock bound; detach it only when its buffers are CONFIRMED
        cleared. Returns True when nothing uncleared remains attached (no
        worker, or cleared); False on a timeout, which keeps it attached —
        every caller that would destroy custody next REFUSES on False
        (peer round 9 PR-MED-017: fail closed, never "the key still goes")."""
        worker = live.live_transcriber
        if worker is None:
            return True
        cleared = worker.stop(timeout=_LIVE_STOP_LOCKED_TIMEOUT_S)
        self._record_live_stop_locked(live, worker, cleared)
        return cleared

    def _record_live_stop_locked(
        self, live: _LiveSession, worker: LiveTranscriber, cleared: bool
    ) -> None:
        """Call under ``self._lock``. Detach a cleared worker; keep an
        uncleared one attached and log the timeout (no clinical content —
        the session id and state only)."""
        if cleared:
            if live.live_transcriber is worker:
                live.live_transcriber = None
            return
        if self._logger is not None:
            log_event(
                self._logger,
                "live_transcriber_stop_timeout",
                session_id=live.session.session_id,
                session_state=live.session.state.value,
            )

    def _refuse_uncleared_live(self, operation: str) -> None:
        """The PR-MED-017 refusal: a destructive custody step must not run
        while a live worker may still hold plaintext. The worker is stopping
        (its stop flag is set) and clears itself when its blocked provider
        call returns; the caller keeps the key and the handle so the same
        action can be retried and then succeeds."""
        raise LiveStopPendingError(
            f"{operation} refused: the live transcriber has not stopped yet; "
            "the session is kept - try again in a moment"
        )

    def _retire_locked(self, live: _LiveSession) -> None:
        """Drop the in-memory handle to a non-active session. On-disk state
        is untouched: a queued/failed session stays recoverable through its
        DPAPI custody blob; terminal sessions have none."""
        # Task 6.3, defense in depth: today the callers are start() and
        # adopt_queued(), which already refused — but retirement destroys the
        # in-memory crypto a generation worker may hold, or that
        # with_write_custody handed to a draft write's action (D9), so both
        # guards live HERE too rather than only on the callers that exist.
        self._refuse_while_generating("session retirement")
        self._refuse_while_writing("session retirement")
        # D2 ownership: a worker still attached to a retired session (its
        # transcriber callable never ran or never claimed it) is stopped here
        # FIRST; an uncleared one REFUSES the retirement (peer round 9
        # PR-MED-017) — the handle and the in-memory crypto stay, the caller
        # (start) raises, and the next start retries the idempotent stop.
        if not self._stop_live_locked(live):
            self._refuse_uncleared_live("start")
        if live.worker is not None:
            live.worker.stop(flush=False)
            live.worker = None
        if live.store is not None:
            live.store.close()
            live.store = None
        live.crypto.destroy()  # in-memory copy only; key.dpapi (if any) remains
        self._live = None

    def _on_capture_failure(self, exc: Exception) -> None:
        """Worker-thread callback for device loss / disk-full during capture.
        The session becomes failed (recoverable). At most one failure is
        reported per worker; a session already past recording/paused (e.g.
        discarded concurrently) ignores it.

        Installation plan round 35 MED-001: the failure is logged first —
        its exception TYPE name and, for a capture error, its fixed detail
        word (``audio_capture.CAPTURE_DETAIL_CODES``); never its message,
        which may carry PortAudio's or the store's text."""
        with self._lock:
            live = self._live
            if live is None or live.session.state not in (
                SessionState.RECORDING,
                SessionState.PAUSED,
            ):
                return
            if self._logger is not None:
                detail = exc.detail_code if isinstance(exc, AudioCaptureError) else "none"
                log_event(
                    self._logger,
                    "capture_failure",
                    session_id=live.session.session_id,
                    session_state=live.session.state.value,
                    error_code=exception_type_name(type(exc)),
                    detail_code=detail,
                )
            self._fail_locked(live)
