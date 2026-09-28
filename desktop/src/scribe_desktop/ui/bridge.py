"""The app's side of the Chrome link (Cliniko workflow safeguards plan Task 4.5).

``ChromeBridge`` sits between the named pipe (``pipe_server.PipeServer``, on
its own thread) and the GUI. It owns nothing the controller owns: the app
stays the single owner of state (Constraint 3), and the bridge only turns
what Chrome reports into the app's decisions and the app's view back into
one ``state`` snapshot.

THREADS. The pipe server calls ``connected`` / ``message`` / ``disconnected``
from its thread; each only emits a signal connected with
``Qt.QueuedConnection``, so every handler below runs on the GUI thread —
the only thread allowed to touch the controller or the screens. A
verification runs on a ``TaskThread`` (holder pattern: the thread object
keeps no request once it has run) and comes back as a queued signal.

CONNECTIONS (D4). A client connecting or going away bumps the ledger's
``conn_gen`` and clears the bound report, the per-tab reports and the
per-connection snapshot, emits ``pipe_lost``, and puts the pipe loss to the
pause rule (below). So a verification answering an
earlier connection is dropped by ``VerificationLedger.accept``, Start needs
a fresh report on the new connection, and the first ``publish`` on every
connection sends the full snapshot even when nothing changed. A LINKED live
session (recording or paused) is re-verified with Cliniko on every new
connection; that result is kept for the session (``live_reverification``) and
dropped when it ends, and — D9, as for the bound report — it counts only while
its clinic is unchanged: a Replace key or Remove voids it and checks again
under the current key (codex round 29 PR-MED-150). The re-check has its own
waiting slot, so a report's check never displaces it (round 25 MED-018).

REPORTS. ``seq`` must rise on a connection (a replay is ignored). The BOUND
tab is the one whose latest report said ``focused``; only its reports feed
the ledger, and only a note page on an allow-listed host becomes a target.

THE PAUSE RULE (D5, Task 5.1). Every report — from any tab — is first put to
``context_rules.ContextEvaluator`` for the linked live session, against the
tab THAT SESSION is bound to (set at its Start, re-bound by exact ids after a
reconnect, moved to the focused tab on a Resume); pipe loss and a new client
are reasons too, and the main window adds suspend and — since 2026-09-28 —
the session locking. ``pause_for`` applies
``context_rules.pause_action``: it pauses through the Session screen's slot,
sets the resolution block for a linked session, and emits ``pause_cue`` for
the desktop cue. Nothing here ever resumes on a report alone, except a
"Resume previous" the practitioner clicked, and only once Chrome reports the
session's own note in the focused tab within
``RESUME_PREVIOUS_WINDOW_SECONDS`` — and a suspend or lock ends such a click
(``SYSTEM_REASONS``), so no report arriving behind a locked screen resumes.

RESUME (Constraint 7). ``resume_refusal`` is the one check: no session
resumes while the computer is locked (the main window's lock flag, set the
moment the lock message is dispatched and cleared by the unlock — codex
round 51 PR-MED-300; ``resume_previous`` is refused then too, and a waiting
one ends), and a linked session resumes only while a pipe client is
connected and the focused tab's current report on this connection names the
session's own note. The Session screen
runs it before EVERY Resume (its button, a Chrome command, Phase 7's
hotkey), and a successful Resume clears the block.

COMMANDS (D2, Constraint 5). ``start`` is refused unless its ``state_rev`` is
the last one sent, its target is the bound tab's report, that report's
verification is ``verified`` or ``unverified_offline``
(``VerificationLedger.start_context``), no session is active, no note
review holds the generation lease, and a microphone is selected; then the
Session screen's ``start_linked`` runs with a consent bound to the verified
note. ``resume``, ``finish``, ``discard`` and ``resume_previous`` are refused
BEFORE their slot runs unless their ``session_ref`` is the live session's;
``resume`` then needs ``resume_refusal`` to pass. ``pause`` needs no ref
(fail-safe). ``open_review`` (Task 5.5) names a RETIRED session: its ref
must still resolve in D2's registry to a session still in the main window's
reminder index — else ``session_changed`` before anything runs — and no
review may hold the lease and no session be recording, paused or
processing; then the main window's opener opens exactly that session. Every refusal travels
in ``state.last_refusal`` — never as ``error`` (Constraint 9). Commands reach
the Session screen's slots (or, for ``open_review``, the main window's
opener), never the controller directly.

THE BANNER (D6, Task 5.5). While the focused tab reports a note on an
allow-listed host whose clinic's note has recordings in the reminder index,
``state.banner`` names the newest one's reference and the count — ids only.

HANDS-FREE AND WARNINGS (D7, D8, Phase 7). The main window owns the hotkey
and the phrase rules and tells the bridge only what to SHOW: the hotkey's
status (``state.hotkey``; ``available`` with its chord only while Windows has
reserved it), whether the spoken pause works for the live recording
(``state.spoken_pause``) and the new-consultation warning, kept for the
recording it was raised on while that recording is live (``state.warnings``).
None of the three changes a session. The suspend and lock registrations'
refusals (D5 as amended 2026-09-28) are shown on the Session screen only —
they are not in ``state``.

DISPLAY. The patient's name reaches the snapshot only from a note Cliniko
verified, with two lifetimes (codex round 29 PR-LOW-151): the BOUND REPORT's
name is published while that verified report is bound (before a Start and
after one) and held by the ledger as its outcome and reuse entry; the LIVE
SESSION's name — from its Start's verification and its reconnect re-check —
is held for that session and dropped when it ends. Nothing here logs.
"""

from __future__ import annotations

import math
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC
from typing import Any, Final, Protocol

from pydantic import ValidationError
from PySide6.QtCore import QObject, Qt, QTimer, Signal

from scribe_desktop.clinics import ClinicRegistry
from scribe_desktop.context_rules import (
    RESUME_PREVIOUS_WINDOW_SECONDS,
    SYSTEM_REASONS,
    ContextEvaluator,
    PauseReason,
    ReminderIndex,
    pause_action,
)
from scribe_desktop.encounter import (
    NoteDisplay,
    NoteRefusal,
    NoteRefused,
    NoteTarget,
    StartRefused,
    UnverifiedOffline,
    VerificationLedger,
    VerificationRequest,
    VerificationResult,
    Verified,
    linked_consent,
    rate_limited_result,
    reverification_request,
    verify_note_context,
)
from scribe_desktop.hotkey import NOT_SET_UP, HotkeyStatus
from scribe_desktop.protocol import (
    LIMITS,
    CommandPayload,
    ContextPayload,
    Envelope,
    make_pipe_envelope,
    typed_payload,
)
from scribe_desktop.session import ACTIVE_STATES, SessionState
from scribe_desktop.system_events import NOT_SET_UP as SYSTEM_PAUSE_NOT_SET_UP
from scribe_desktop.system_events import SystemPauseStatus
from scribe_desktop.ui import models
from scribe_desktop.ui.session_screen import SessionScreen
from scribe_desktop.ui.tasks import TaskThread
from scribe_desktop.voice_commands import NEW_CONSULTATION_WARNING, spoken_pause_state

PUBLISH_INTERVAL_MS: Final = 500
# Cliniko's rate limit (round 57 SEC-009, practitioner decision 2026-09-28):
# after a 429 a clinic's checks are answered `unverified_offline` WITHOUT a
# call for this long (a fixed window from the 429; only a real 429 starts
# one), and no two verification calls start closer together than the
# spacing — a check inside it waits in its slot for a single-shot timer,
# coalesced like any waiting check, never blocking the GUI thread.
RATE_LIMIT_COOLDOWN_SECONDS: Final = 60.0
MIN_CALL_SPACING_SECONDS: Final = 1.0
# The main window's lock refusals (codex round 51 PR-MED-300).
_LOCK_REFUSALS: Final = frozenset({"locked", "lock_unknown"})
_PHASES: Final[dict[SessionState, str]] = {
    SessionState.RECORDING: "recording",
    SessionState.PAUSED: "paused",
    SessionState.PROCESSING: "finishing",
    SessionState.QUEUED: "queued",
}
_ACTION_CONTROL: Final[dict[str, str]] = {
    "pause": "pause",
    "resume": "resume",
    "finish": "finish",
    "discard": "discard",
}


class PipeSender(Protocol):
    """The pipe server's sending surface (``PipeServer.send``)."""

    def send(self, conn_id: int, envelope: Envelope) -> bool: ...


def _one_line(text: str, limit: int, fallback: str) -> str:
    """Display text as the protocol allows it: one line, no control
    character and no lone surrogate (a snapshot that failed validation would
    never be sent, freezing Chrome on the last one — H1 round 53 LOW-044), at
    most ``limit`` characters."""
    cleaned = "".join(
        " " if unicodedata.category(ch) in ("Cc", "Cf", "Cs", "Zl", "Zp") else ch
        for ch in text
    )
    cleaned = " ".join(cleaned.split())[:limit]
    return cleaned or fallback


@dataclass
class _LiveCheck:
    """D4's re-verification of the linked live session on a new pipe
    connection. ``request`` None: the clinic is gone (it cannot count)."""

    session_id: str
    request: VerificationRequest | None
    result: VerificationResult | None = None


@dataclass(frozen=True)
class _LiveDisplay:
    """The live session's display strings, from the verification it was
    started on. In memory only; dropped when that session ends."""

    session_id: str
    display: NoteDisplay


@dataclass(frozen=True)
class _Refusal:
    action: str
    reason: str
    message: str
    # H1 round 53 LOW-042: what was on screen when it was refused (the bound
    # tab and report, for a Start its outcome's kind, the live session and
    # its state).
    # Once any of it changes the refusal is about something no longer shown.
    situation: tuple[object, ...] = ()


@dataclass(frozen=True)
class _Block:
    """D1's resolution block for one PAUSED linked session."""

    session_id: str
    reason: PauseReason


@dataclass(frozen=True)
class _PendingResume:
    """A clicked "Resume previous", waiting for the session's own note."""

    session_id: str
    at: float


class ChromeBridge(QObject):
    """See the module docstring."""

    _connected_q = Signal(int)
    _message_q = Signal(int, object)
    _disconnected_q = Signal(int, str)
    # A client went away or a new one connected (D5's pipe-loss input).
    pipe_lost = Signal()
    # D5: the pause rule paused the recording or put up the block — the
    # desktop cue's text (plain, no name) for the main window.
    pause_cue = Signal(str)

    def __init__(
        self,
        controller: models.SessionControllerLike,
        session_screen: SessionScreen,
        clinics: ClinicRegistry,
        *,
        parent: QObject | None = None,
        publish_interval_ms: int = PUBLISH_INTERVAL_MS,
        clock: Callable[[], float] = time.monotonic,
        reminders: ReminderIndex | None = None,
        open_review: Callable[[str], str | None] | None = None,
        call_spacing_seconds: float = MIN_CALL_SPACING_SECONDS,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._screen = session_screen
        self._clinics = clinics
        self._clock = clock
        # Task 5.5 (D6): the main window's Unreviewed reminder index (read
        # only, for the banner) and its opener — given a session id, it
        # opens that session for review and returns None, or a
        # ``CHROME_REFUSALS`` code. None: no banner, and ``open_review`` is
        # refused ``not_available``.
        self._reminders = reminders
        self._open_review_handler = open_review
        # Task 5.1 (D5): the linked live session's tab binding and the rule.
        self._rules = ContextEvaluator()
        self._block: _Block | None = None
        self._pending_resume: _PendingResume | None = None
        self._ledger = VerificationLedger(clinics)
        self._sender: PipeSender | None = None
        self._link = "off"
        self._conn: int | None = None
        self._last_seq = 0
        self._tabs: dict[int, ContextPayload] = {}
        self._bound_tab: int | None = None
        self._state_rev = 0
        self._last_content: dict[str, Any] | None = None
        self._refusal: _Refusal | None = None
        self._task: TaskThread | None = None
        self._running: VerificationRequest | None = None
        self._running_live = False
        # One waiting slot per KIND (round 25 MED-018): the ledger's latest
        # report, and the live session's re-check — neither replaces the other.
        self._waiting: VerificationRequest | None = None
        self._waiting_live: VerificationRequest | None = None
        self._live_check: _LiveCheck | None = None
        self._live_check_seq = 0
        # SEC-009: per-clinic cooldown ends (clinic_id -> clock time), the
        # last call's start, and the spacing timer that starts a deferred one.
        self._cooldown_until: dict[str, float] = {}
        self._last_call_at: float | None = None
        self._call_spacing = call_spacing_seconds
        self._spacing_served = False
        self._spacing = QTimer(self)
        self._spacing.setSingleShot(True)
        # A coarse timer may fire up to 5 % early, and its firing IS the
        # spacing (``_spacing_served``): precise, so a second is a second.
        self._spacing.setTimerType(Qt.TimerType.PreciseTimer)
        self._spacing.timeout.connect(self._on_spacing_elapsed)
        self._live_display: _LiveDisplay | None = None
        # Phase 7 (D7, D8): shown only — the main window owns both.
        self._hotkey: HotkeyStatus = NOT_SET_UP
        self._system_pause: SystemPauseStatus = SYSTEM_PAUSE_NOT_SET_UP
        self._lock_refusal: Callable[[], str | None] | None = None
        self._warning_session: str | None = None
        for signal, slot in (
            (self._connected_q, self._on_connected),
            (self._message_q, self._on_message),
            (self._disconnected_q, self._on_disconnected),
        ):
            signal.connect(slot, Qt.ConnectionType.QueuedConnection)
        self._timer = QTimer(self)
        self._timer.setInterval(publish_interval_ms)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        # Constraint 7: every Resume from the Session screen's slot asks first.
        session_screen.set_resume_guard(self._resume_guard_message)
        # H1 round 54 MED-052: and every Start, the desktop's too, meets the lock.
        session_screen.set_start_guard(self._start_guard_message)
        session_screen.session_resumed.connect(self._on_resumed)

    # --- the pipe's side (called on the PIPE thread: emit only) --------------

    def connected(self, conn_id: int) -> None:
        self._connected_q.emit(conn_id)

    def message(self, conn_id: int, envelope: Envelope) -> None:
        self._message_q.emit(conn_id, envelope)

    def disconnected(self, conn_id: int, reason: str) -> None:
        self._disconnected_q.emit(conn_id, reason)

    # --- lifecycle (GUI thread) ---------------------------------------------

    def attach(self, sender: PipeSender) -> None:
        """The pipe is up and waiting for the native host."""
        self._sender = sender
        self._link = "waiting"
        self._refresh_view()

    def set_unavailable(self) -> None:
        """The pipe could not be created (its name is held elsewhere)."""
        self._sender = None
        self._link = "unavailable"
        self._refresh_view()

    @property
    def is_busy(self) -> bool:
        """A verification is running, or spaced to start within
        ``MIN_CALL_SPACING_SECONDS`` (the window must not close under it)."""
        return self._task is not None or self._spacing.isActive()

    @property
    def state_rev(self) -> int:
        return self._state_rev

    @property
    def conn_gen(self) -> int:
        return self._ledger.conn_gen

    def live_reverification(self) -> VerificationResult | None:
        """The linked live session's re-verification from the latest pipe
        connection (D4), for the session it was made for; None otherwise."""
        check = self._live_check
        session = self._controller.session
        if check is None or session is None or session.session_id != check.session_id:
            return None
        result = check.result
        if result is None or not self._rev_current(result.request):
            return None  # D9: a result under a replaced or removed key is void
        return result

    def _rev_current(self, request: VerificationRequest) -> bool:
        """D9 (codex round 29 PR-MED-150): a re-check counts only while its
        clinic still exists at the ``clinic_rev`` it was dispatched under —
        the rule ``VerificationLedger`` applies to the bound report."""
        clinic_id = request.clinic.clinic_id
        return (
            self._clinics.record(clinic_id) is not None
            and self._clinics.rev(clinic_id) == request.clinic_rev
        )

    def on_clinics_changed(self) -> None:
        """A Replace key or Remove (D9): the allow-list may have changed, and
        the bound report's clinic rev — or the live re-check's — may have
        moved: each is checked again under the clinic's current key (a
        removed clinic's re-check becomes "clinic_gone")."""
        request = self._ledger.reverify_after_clinic_change()
        if request is not None:
            self._dispatch(request)
        check = self._live_check
        if check is not None and check.request is not None and not self._rev_current(
            check.request
        ):
            self._reverify_live()  # same connection: conn_gen does not move
        self.publish()
        self._refresh_view()

    # --- connections -----------------------------------------------------------

    def _reset_connection(self) -> None:
        self._ledger.new_connection()
        self._tabs.clear()
        self._bound_tab = None
        self._last_seq = 0
        self._last_content = None
        self._refusal = None
        # A waiting report check answers the old connection: it would only be
        # dropped. A waiting re-check is NOT cleared here (round 26 LOW-022):
        # it answers its session, not the connection — a reconnect replaces
        # it (``_reverify_live``) and ``_finish_task`` skips one no longer
        # current, but a bare disconnect must not strand it on "Checking".
        self._waiting = None
        # D5: tab ids from the old connection mean nothing now — the session
        # waits unbound for a report of its own note — and a clicked "Resume
        # previous" lapses (it must be clicked again on the new connection).
        self._rules.lose_tab()
        self._pending_resume = None

    def _on_connected(self, conn_id: int) -> None:
        self._conn = conn_id
        self._reset_connection()
        if self._sender is not None:
            self._link = "connected"
        self.pipe_lost.emit()  # a NEW client is pipe loss too (D5)
        self.pause_for(PauseReason.NEW_CLIENT)
        self._reverify_live()
        self.publish()
        self._refresh_view()

    def _on_disconnected(self, conn_id: int, _reason: str) -> None:
        if conn_id != self._conn:
            return
        self._conn = None
        self._reset_connection()
        if self._sender is not None:
            self._link = "waiting"
        self.pipe_lost.emit()
        self.pause_for(PauseReason.PIPE_LOST)
        self._refresh_view()

    # --- the pause rule (D5, Task 5.1) and resume (Constraint 7) ---------------

    def pause_for(self, reason: PauseReason) -> None:
        """D5's ``pause_for``: RECORDING pauses (through the Session screen's
        slot) and, for a context reason on a linked session, sets the block;
        PAUSED only sets the block; any other state does nothing. Emits
        ``pause_cue`` when it paused or newly blocked. A suspend or lock
        also ends a clicked "Resume previous" still waiting for its note's
        report (D5 as amended 2026-09-28): nothing resumes behind it; and it
        names the block only when it starts one — a block Chrome already put
        up keeps its reason (round 49 LOW-038: "the computer was locked" must
        not hide "a different treatment note")."""
        if reason in SYSTEM_REASONS:
            self._pending_resume = None
        session = self._controller.session
        linked = session is not None and session.encounter_context is not None
        action = pause_action(self._controller.state, reason, linked=linked)
        paused = action.pause and self._screen.on_pause()
        new_block = False
        if (
            action.block
            and session is not None
            and self._controller.state is SessionState.PAUSED
        ):
            block = self._block
            new_block = block is None or block.session_id != session.session_id
            if new_block or reason not in SYSTEM_REASONS:
                self._block = _Block(session.session_id, reason)
        if paused or new_block:
            self.pause_cue.emit(models.pause_cue_text(reason.value, linked=linked))
        self.publish()
        self._refresh_view()

    def set_lock_refusal(self, check: Callable[[], str | None] | None) -> None:
        """D5 as amended 2026-09-28 (codex round 51 PR-MED-300): the main
        window's lock check — ``locked`` / ``lock_unknown`` between a lock
        and the next unlock, else None."""
        self._lock_refusal = check

    def _locked_refusal(self) -> str | None:
        check = self._lock_refusal
        return check() if check is not None else None

    def resume_refusal(self) -> str | None:
        """Constraint 7: why a Resume of the tracked session is refused now
        (a ``CHROME_REFUSALS`` code), or None. FIRST, for every session
        linked or not: the computer is locked (codex round 51 PR-MED-300 —
        every Resume path runs this one check, so a click still on its way
        when the lock arrived cannot restart the recording behind it). Then
        an unlinked session has no note to match; a linked one needs a pipe
        client and the focused tab's current report on this connection
        naming its own note."""
        locked = self._locked_refusal()
        if locked is not None:
            return locked
        session = self._controller.session
        context = session.encounter_context if session is not None else None
        if context is None:
            return None
        if self._conn is None:
            return "pipe_down"
        if self._ledger.bound_target() != context.target:
            return "report_mismatch"
        return None

    # --- hands-free and warnings (Phase 7: shown only) ------------------------

    def set_hotkey_status(self, status: HotkeyStatus) -> None:
        """Task 7.1: the main window's hotkey status, for ``state.hotkey``
        and the Session screen."""
        self._hotkey = status
        self.publish()
        self._refresh_view()

    def set_system_pause_status(self, status: SystemPauseStatus) -> None:
        """D5 as amended 2026-09-28: which of the suspend and lock
        registrations Windows refused, for the Session screen only."""
        self._system_pause = status
        self._refresh_view()

    def set_new_consultation_warning(self, session_id: str) -> None:
        """Task 7.3 (D8): the phrase rule raised its warning on this
        recording. Kept while that recording is live; it changes nothing."""
        self._warning_session = session_id
        self.publish()
        self._refresh_view()

    def _warning_live(self) -> bool:
        session = self._controller.session
        return (
            self._warning_session is not None
            and session is not None
            and session.session_id == self._warning_session
            and session.state in (SessionState.RECORDING, SessionState.PAUSED)
        )

    def _spoken_pause(self) -> str:
        return spoken_pause_state(
            self._controller.state,
            attached=self._controller.live_transcription_attached,
            failure=self._controller.live_failure,
        )

    def _resume_guard_message(self) -> str | None:
        reason = self.resume_refusal()
        return None if reason is None else models.chrome_refusal_message(reason)

    def _start_guard_message(self) -> str | None:
        locked = self._locked_refusal()
        return None if locked is None else models.chrome_refusal_message(locked)

    def _on_resumed(self) -> None:
        """A Resume succeeded (any source): the block is resolved, and the
        session is bound to the focused tab that shows its note."""
        self._block = None
        self._pending_resume = None
        session = self._controller.session
        if session is not None and session.encounter_context is not None:
            self._rules.bind(session.session_id, self._bound_tab)
        self.publish()
        self._refresh_view()

    def _apply_rule(self, report: ContextPayload) -> None:
        session = self._controller.session
        context = session.encounter_context if session is not None else None
        if (
            session is None
            or context is None
            or session.state not in (SessionState.RECORDING, SessionState.PAUSED)
        ):
            return
        reason = self._rules.evaluate(session.session_id, context.target, report)
        if reason is not None:
            self.pause_for(reason)

    def _resume_if_pending(self) -> None:
        """A clicked "Resume previous" resumes once — and only once —
        Chrome's focused tab reports the session's own note (D5)."""
        pending = self._pending_resume
        if pending is None:
            return
        session = self._controller.session
        if (
            session is None
            or session.session_id != pending.session_id
            or self._controller.state is not SessionState.PAUSED
            or not 0 <= self._clock() - pending.at <= RESUME_PREVIOUS_WINDOW_SECONDS
        ):
            self._pending_resume = None
            return
        refusal = self.resume_refusal()
        if refusal in _LOCK_REFUSALS:
            self._pending_resume = None  # the click ends; it never waits out a lock
            return
        if refusal is not None:
            return  # not yet: wait for the note's report
        self._pending_resume = None
        if not self._screen.on_resume():
            self._refuse("resume_previous", "failed")

    def _current_block(self) -> _Block | None:
        block = self._block
        session = self._controller.session
        if (
            block is None
            or session is None
            or session.session_id != block.session_id
            or session.state is not SessionState.PAUSED
            or session.encounter_context is None
        ):
            return None
        return block

    def _reverify_live(self) -> None:
        session = self._controller.session
        context = session.encounter_context if session is not None else None
        if (
            session is None
            or context is None
            or session.state not in (SessionState.RECORDING, SessionState.PAUSED)
        ):
            self._live_check = None
            return
        self._live_check_seq += 1
        request = reverification_request(
            context, self._clinics, seq=self._live_check_seq, conn_gen=self._ledger.conn_gen
        )
        self._live_check = _LiveCheck(session_id=session.session_id, request=request)
        if request is not None:
            self._dispatch(request, live=True)

    # --- messages ----------------------------------------------------------------

    def _on_message(self, conn_id: int, envelope: object) -> None:
        if conn_id != self._conn or not isinstance(envelope, Envelope):
            return
        payload = typed_payload(envelope)
        if isinstance(payload, ContextPayload):
            self._on_context(payload)
        elif isinstance(payload, CommandPayload):
            self._on_command(payload)
        self.publish()
        self._refresh_view()

    def _allow_list(self) -> list[str]:
        hosts = sorted({record.host for record in self._clinics.records})
        return hosts[: LIMITS["max_allow_list"]]

    def _target_of(self, report: ContextPayload) -> NoteTarget | None:
        host, patient_id, note_id = report.host, report.patient_id, report.note_id
        if (
            report.page != "note"
            or host is None
            or patient_id is None
            or note_id is None
            or host not in self._allow_list()
        ):
            return None
        try:
            return NoteTarget(clinic_host=host, patient_id=patient_id, note_id=note_id)
        except ValidationError:
            return None

    def _on_context(self, report: ContextPayload) -> None:
        if report.seq <= self._last_seq:
            return  # replayed or out of order
        self._last_seq = report.seq
        if report.page == "closed":
            self._tabs.pop(report.tab_id, None)
        else:
            self._tabs[report.tab_id] = report
            if report.focused:
                self._bound_tab = report.tab_id
        # D5 first, for EVERY report: the live session's own tab may change
        # while it is not the focused one.
        self._apply_rule(report)
        if report.tab_id == self._bound_tab:
            request = self._ledger.report(report.seq, self._target_of(report))
            if report.page == "closed":
                self._bound_tab = None
            if request is not None:
                self._dispatch(request)
        self._resume_if_pending()

    # --- verification (worker thread, holder pattern) ---------------------------

    def _dispatch(self, request: VerificationRequest, *, live: bool = False) -> None:
        """One check at a time. A newer request waits for the running one and
        replaces only a waiting request of its OWN kind — the ledger's
        (``live`` False) or the live session's re-check — so a report never
        drops the re-check (round 25 MED-018). A stale answer is dropped by
        the ledger (its tags) or by identity (the re-check). A request made
        while the spacing timer runs waits the same way."""
        if self._task is None and not self._spacing.isActive():
            self._run(request, live=live)
        elif live:
            self._waiting_live = request
        else:
            self._waiting = request

    def _run(self, request: VerificationRequest, *, live: bool) -> None:
        """With no check running: answer ``request`` from its clinic's
        cooldown with no call; or, inside the spacing, put it back in its
        slot and start the timer; or start the call (SEC-009)."""
        now = self._clock()
        until = self._cooldown_until.get(request.clinic.clinic_id)
        if until is not None and now < until:
            self._apply_result(rate_limited_result(request), live=live)
            return
        if self._last_call_at is not None and not self._spacing_served:
            elapsed = now - self._last_call_at
            remaining = min(self._call_spacing, self._call_spacing - elapsed)
            if remaining > 0:
                if live:
                    self._waiting_live = request
                else:
                    self._waiting = request
                self._spacing.start(max(1, math.ceil(remaining * 1000)))
                return
        self._last_call_at = now
        registry = self._clinics
        holder = [request]
        task = TaskThread(
            lambda: verify_note_context(
                holder.pop(), key_store=registry.key_store, transport=registry.transport
            ),
            self,
        )
        task.succeeded.connect(self._on_verified)
        task.failed.connect(self._on_verify_failed)
        self._task = task
        self._running = request
        self._running_live = live
        task.start()

    def _finish_task(self) -> None:
        if self._task is not None:
            self._task.finish()
            self._task = None
        self._running = None
        self._next()

    def _next(self) -> None:
        """Start the next waiting check — the bound report first: the
        practitioner is waiting on it to Start. One answered by the cooldown
        starts no call, so the loop goes on to the next (each pass empties a
        slot, starts the call or starts the spacing timer). A waiting REPORT
        check starts only while the ledger still awaits it (codex round 65
        PR-LOW-350): one whose tab closed or moved on while it waited —
        behind a running check or inside the spacing — is dropped, never
        called; the current target, if any, was dispatched on its own."""
        while self._task is None and not self._spacing.isActive():
            if self._waiting is not None:
                request, self._waiting = self._waiting, None
                if self._ledger.awaits(request):
                    self._run(request, live=False)
            elif self._waiting_live is not None:
                request, self._waiting_live = self._waiting_live, None
                check = self._live_check
                if check is not None and request is check.request:  # else: its session ended
                    self._run(request, live=True)
            else:
                return

    def _on_spacing_elapsed(self) -> None:
        # The timer's wait IS the spacing: the next call starts now, whatever
        # the injectable clock reads.
        self._spacing_served = True
        try:
            self._next()
        finally:
            self._spacing_served = False
        self.publish()
        self._refresh_view()

    def _apply_result(self, result: VerificationResult, *, live: bool) -> None:
        if live:
            # A re-check counts only for the check still current, and only
            # while its clinic's rev has not moved (D9, codex round 29
            # PR-MED-150); one replaced or dropped since never reaches the
            # ledger.
            check = self._live_check
            if (
                check is not None
                and result.request is check.request
                and self._rev_current(result.request)
            ):
                check.result = result
        else:
            self._ledger.accept(result)

    def _on_verified(self, result: object) -> None:
        if isinstance(result, VerificationResult):
            outcome = result.outcome
            if isinstance(outcome, UnverifiedOffline) and outcome.rate_limited:
                # A real 429 (the cooldown's own answers never come here):
                # this clinic's checks make no call for the next minute.
                self._cooldown_until[result.request.clinic.clinic_id] = (
                    self._clock() + RATE_LIMIT_COOLDOWN_SECONDS
                )
            self._apply_result(result, live=self._running_live)
        self._finish_task()
        self.publish()
        self._refresh_view()

    def _on_verify_failed(self, _message: str) -> None:
        # `verify_note_context` never raises; if it did, nothing is applied.
        self._finish_task()
        self.publish()
        self._refresh_view()

    # --- commands ------------------------------------------------------------------

    def _refuse(
        self, action: str, reason: str, note_refusal: NoteRefusal | None = None
    ) -> None:
        self._refusal = _Refusal(
            action,
            reason,
            models.chrome_refusal_message(reason, note_refusal),
            self._situation(action),
        )

    def _situation(self, action: str) -> tuple[object, ...]:
        # The verification's outcome is part of what a START was refused on
        # ("checking", "not verified"); a session command's refusal must not
        # vanish when a check of the same note lands (round 54 LOW-053).
        outcome = self._ledger.outcome() if action == "start" else None
        return (
            action,
            self._bound_tab,
            self._ledger.bound_target(),
            None if outcome is None else type(outcome),
            self._controller.session_ref,
            self._controller.state,
        )

    def _current_refusal(self) -> _Refusal | None:
        """The last refusal while what it was about is still on screen; one
        left behind by a change of tab, note, verification, session or state
        is dropped (H1 round 53 LOW-042: a refused Start for one patient's
        final note must not sit under the next patient's Ready panel)."""
        refusal = self._refusal
        if refusal is not None and refusal.situation != self._situation(refusal.action):
            self._refusal = refusal = None
        return refusal

    def _on_command(self, command: CommandPayload) -> None:
        self._refusal = None
        action = command.action
        if action == "open_review":
            self._open_review(command.session_ref)
            return
        if action == "start":
            self._start(command)
            return
        if action != "pause" and command.session_ref != self._controller.session_ref:
            # D2: refused BEFORE the slot runs — a stale click for a session
            # that ended can never act on a newer one.
            self._refuse(action, "session_changed")
            return
        if self._screen.is_busy:
            self._refuse(action, "busy")
            return
        if action == "resume_previous":
            self._resume_previous()
            return
        controls = models.controls_for_state(self._controller.state)
        if not getattr(controls, _ACTION_CONTROL[action]):
            self._refuse(action, "not_allowed_now")
            return
        if action == "resume":
            refusal = self.resume_refusal()
            if refusal is not None:
                self._refuse(action, refusal)
                return
        done = {
            "pause": self._screen.on_pause,
            "resume": self._screen.on_resume,
            "finish": self._screen.on_finish,
            "discard": self._screen.on_discard,
        }[action]()
        if not done:
            self._refuse(action, "failed")

    def _open_review(self, session_ref: str | None) -> None:
        """Task 5.5 (D2, D6): the banner's "Open for review". THE session
        gate for a RETIRED session: the reference must still resolve (D2's
        registry) to a session still in the reminder index — a click made
        after that entry was completed, discarded, expired or opened is
        refused ``session_changed`` BEFORE anything runs, never "the newest
        session". Then the main window opens exactly that session."""
        opener, reminders = self._open_review_handler, self._reminders
        if opener is None or reminders is None:
            self._refuse("open_review", "not_available")
            return
        session_id = (
            self._controller.resolve_session_ref(session_ref) if session_ref is not None else None
        )
        if session_id is None or session_id not in reminders:
            self._refuse("open_review", "session_changed")
            return
        if self._screen.is_busy:
            self._refuse("open_review", "busy")
            return
        if self._controller.generating:
            self._refuse("open_review", "review_in_progress")
            return
        if self._controller.state in ACTIVE_STATES:
            # ``adopt_queued`` refuses it too; named here, before the window
            # comes forward or a tab changes mid-recording (round 32 LOW-023).
            self._refuse("open_review", "session_active")
            return
        refusal = opener(session_id)
        if refusal is not None:
            self._refuse("open_review", refusal)

    def _resume_previous(self) -> None:
        """Flow 3's "Resume previous" (Task 5.2): the extension takes the tab
        back to the session's note, built from ``state.live``'s ids and the
        allow-list; the app resumes only when Chrome then reports that note
        (``_resume_if_pending``) — at once if it already does."""
        session = self._controller.session
        if (
            session is None
            or session.encounter_context is None
            or self._controller.state is not SessionState.PAUSED
        ):
            self._refuse("resume_previous", "not_allowed_now")
            return
        locked = self._locked_refusal()
        if locked is not None:
            # Codex round 51 PR-MED-300: a click still on its way when the
            # lock arrived creates nothing to complete behind the lock.
            self._refuse("resume_previous", locked)
            return
        self._pending_resume = _PendingResume(session.session_id, self._clock())
        self._resume_if_pending()

    def _start(self, command: CommandPayload) -> None:
        target = command.target
        assert target is not None  # the protocol requires it on start
        locked = self._locked_refusal()
        if locked is not None:
            # H1 round 53 MED-039, PR-MED-300's class for Start: a click
            # still on its way when the lock arrived starts nothing behind it
            # (the lock's queued pause ran at IDLE or QUEUED and did nothing).
            self._refuse("start", locked)
            return
        if command.state_rev != self._state_rev:
            self._refuse("start", "stale_state")
            return
        if target.tab_id != self._bound_tab:
            self._refuse("start", "target_mismatch")
            return
        try:
            note = NoteTarget(
                clinic_host=target.clinic_host,
                patient_id=target.patient_id,
                note_id=target.note_id,
            )
        except ValidationError:
            self._refuse("start", "target_mismatch")
            return
        context = self._ledger.start_context(note)
        if isinstance(context, StartRefused):
            self._refuse("start", context.reason.value, context.note_refusal)
            return
        if self._screen.is_busy or not models.controls_for_state(self._controller.state).start:
            self._refuse("start", "session_active")
            return
        if self._controller.generating:
            self._refuse("start", "review_open")
            return
        if not self._screen.has_input_device():
            self._refuse("start", "no_microphone")
            return
        outcome = self._ledger.outcome()
        if not self._screen.start_linked(linked_consent(context), context):
            self._refuse("start", "failed")
            return
        session = self._controller.session
        if isinstance(outcome, Verified) and session is not None:
            self._live_display = _LiveDisplay(session.session_id, outcome.display)
        self._live_check = None
        self._block = None
        self._pending_resume = None
        if session is not None:
            self._rules.bind(session.session_id, target.tab_id)  # D5: its own tab

    # --- the snapshot ------------------------------------------------------------

    def _clinic_label(self, host: str) -> str | None:
        record = next((r for r in self._clinics.records if r.host == host), None)
        if record is None:
            return None
        return _one_line(record.display_name, LIMITS["max_label_chars"], "Clinic")

    def _report_state(self) -> dict[str, Any] | None:
        report = self._tabs.get(self._bound_tab) if self._bound_tab is not None else None
        target = self._target_of(report) if report is not None else None
        if report is None or target is None or self._ledger.bound_target() != target:
            return None
        state: dict[str, Any] = {
            "tab_id": report.tab_id,
            "clinic_host": target.clinic_host,
            "patient_id": target.patient_id,
            "note_id": target.note_id,
            "verification": "checking",
        }
        label = self._clinic_label(target.clinic_host)
        if label is not None:
            state["clinic_label"] = label
        outcome = self._ledger.outcome()
        if isinstance(outcome, Verified):
            state["verification"] = "verified"
            state["patient_name"] = _one_line(
                outcome.display.patient_display_name,
                LIMITS["max_display_chars"],
                "Unnamed patient",
            )
            starts_at = outcome.display.appointment_starts_at
            if starts_at is not None:
                state["appointment_starts_at"] = starts_at.astimezone(UTC).isoformat()
        elif isinstance(outcome, UnverifiedOffline):
            state["verification"] = "unverified_offline"
        elif isinstance(outcome, NoteRefused):
            state["verification"] = "refused"
            state["refusal"] = outcome.reason.value
        return state

    def _notice(self) -> str | None:
        if self._controller.generating:
            # D1/D6: "Save or cancel <A>'s note review to start" — the panel
            # names A from ``live`` while that session is still tracked.
            return "review_open"
        report = self._tabs.get(self._bound_tab) if self._bound_tab is not None else None
        if report is None or report.page != "note":
            return "open_a_note"
        if report.host not in self._allow_list():
            return "clinic_not_set_up"
        return None

    def _live_state(self) -> dict[str, Any] | None:
        session = self._controller.session
        ref = self._controller.session_ref
        if session is None or ref is None or session.state not in _PHASES:
            return None
        context = session.encounter_context
        state: dict[str, Any] = {
            "session_ref": ref,
            "phase": _PHASES[session.state],
            "linked": context is not None,
            "recorded_seconds": min(
                max(self._controller.recorded_seconds, 0), LIMITS["max_recorded_seconds"]
            ),
            "consent_confirmed_at": session.consent.confirmed_at.astimezone(UTC).isoformat(),
        }
        if context is not None:
            state.update(
                clinic_host=context.clinic_host,
                patient_id=context.patient_id,
                note_id=context.treatment_note_id,
                verification=context.verification.value,
            )
            label = self._clinic_label(context.clinic_host)
            if label is not None:
                state["clinic_label"] = label
            display = self._live_display
            if display is not None and display.session_id == session.session_id:
                state["patient_name"] = _one_line(
                    display.display.patient_display_name,
                    LIMITS["max_display_chars"],
                    "Unnamed patient",
                )
        return state

    def _block_state(self) -> dict[str, Any] | None:
        """D1's block for the paused linked session: its OWN clinic and, when
        Cliniko verified its note at Start, its patient's name. The patient
        on screen now is the ``report``'s; the extension scopes both to each
        tab's host (D2)."""
        block = self._current_block()
        session = self._controller.session
        ref = self._controller.session_ref
        context = session.encounter_context if session is not None else None
        if block is None or session is None or context is None or ref is None:
            return None
        state: dict[str, Any] = {
            "reason": block.reason.value,
            "session_ref": ref,
            "clinic_host": context.clinic_host,
            "clinic_label": self._clinic_label(context.clinic_host) or "Clinic",
        }
        display = self._live_display
        if display is not None and display.session_id == session.session_id:
            state["patient_name"] = _one_line(
                display.display.patient_display_name,
                LIMITS["max_display_chars"],
                "Unnamed patient",
            )
        return state

    def _banner_state(self) -> dict[str, Any] | None:
        """D6's reminder for the note on the focused tab: when the main
        window's index holds recordings for that clinic's note, the newest
        one's reference (D2) and how many there are. Ids and a count only —
        no patient's name: a retired session keeps no display string."""
        reminders = self._reminders
        report = self._tabs.get(self._bound_tab) if self._bound_tab is not None else None
        target = self._target_of(report) if report is not None else None
        if reminders is None or target is None:
            return None
        record = next((r for r in self._clinics.records if r.host == target.clinic_host), None)
        if record is None:
            return None
        sessions = reminders.sessions_for(record.clinic_id, target.note_id)
        for session_id in sessions:  # newest first: the first one still referenced
            ref = self._controller.session_ref_for(session_id)
            if ref is not None:
                return {
                    "session_ref": ref,
                    "clinic_host": target.clinic_host,
                    "note_id": target.note_id,
                    "count": min(len(sessions), LIMITS["max_banner_count"]),
                }
        return None

    def build_content(self) -> dict[str, Any]:
        """The ``state`` snapshot without its ``state_rev`` (D2: one builder
        for the poll, the events and every (re)connect)."""
        hotkey = self._hotkey
        content: dict[str, Any] = {
            "app_running": True,
            "allow_list": self._allow_list(),
            "hotkey": (
                {"available": True, "chord": hotkey.chord}
                if hotkey.available
                else {"available": False}
            ),
            "spoken_pause": self._spoken_pause() == "on",
            "warnings": [NEW_CONSULTATION_WARNING] if self._warning_live() else [],
        }
        for key, value in (
            ("report", self._report_state()),
            ("live", self._live_state()),
            ("block", self._block_state()),
            ("banner", self._banner_state()),
            ("notice", self._notice()),
        ):
            if value is not None:
                content[key] = value
        refusal = self._current_refusal()
        if refusal is not None:
            content["last_refusal"] = {
                "action": refusal.action,
                "reason": refusal.reason,
                "message": _one_line(refusal.message, LIMITS["max_message_chars"], "Refused."),
            }
        return content

    def publish(self) -> None:
        """Send the snapshot when it differs from the last one sent on THIS
        connection (D2). A snapshot that fails the protocol's own validation
        is never sent."""
        sender, conn = self._sender, self._conn
        if sender is None or conn is None:
            return
        content = self.build_content()
        if content == self._last_content:
            return
        try:
            envelope = make_pipe_envelope(
                "state", payload={"state_rev": self._state_rev + 1, **content}
            )
        except ValidationError:
            return
        self._state_rev += 1
        self._last_content = content
        sender.send(conn, envelope)

    # --- the poll and the Session screen -------------------------------------------

    def _tick(self) -> None:
        session = self._controller.session

        def ended(session_id: str) -> bool:
            return session is None or session.session_id != session_id or session.is_terminal

        display = self._live_display
        if display is not None and ended(display.session_id):
            self._live_display = None  # the name goes with its session
        check = self._live_check
        if check is not None and ended(check.session_id):
            # Round 25 LOW-019: the re-check's result names the patient too.
            self._live_check = None
        if self._block is not None and self._current_block() is None:
            self._block = None  # resolved, or its session left PAUSED
        if self._warning_session is not None and not self._warning_live():
            self._warning_session = None  # its recording finished or ended
        pending = self._pending_resume
        if pending is not None and not (
            0 <= self._clock() - pending.at <= RESUME_PREVIOUS_WINDOW_SECONDS
        ):
            self._pending_resume = None  # the click lapsed
        if session is None or session.is_terminal or session.encounter_context is None:
            self._rules.forget()
        self.publish()
        self._refresh_view()

    def view(self) -> models.ChromeView:
        session = self._controller.session
        context = session.encounter_context if session is not None else None
        live = session is not None and session.state in _PHASES and context is not None
        patient = clinic = recheck = None
        recheck_reason: NoteRefusal | None = None
        if live and session is not None and context is not None:
            clinic = self._clinic_label(context.clinic_host) or "a clinic no longer set up"
            display = self._live_display
            if display is not None and display.session_id == session.session_id:
                patient = _one_line(
                    display.display.patient_display_name,
                    LIMITS["max_display_chars"],
                    "Unnamed patient",
                )
            check = self._live_check
            if check is not None and check.session_id == session.session_id:
                recheck, recheck_reason = self._recheck_line(check)
        refusal = self._current_refusal()
        return models.ChromeView(
            link=self._link,
            patient=patient,
            clinic=clinic,
            recheck=recheck,
            recheck_reason=recheck_reason,
            refusal=refusal.message if refusal is not None else None,
            phase=_PHASES[session.state] if live and session is not None else None,
            blocked=self._current_block() is not None,
            hotkey=self._hotkey.state,
            hotkey_chord=self._hotkey.chord,
            spoken_pause=self._spoken_pause(),
            new_consultation=self._warning_live(),
            system_pause_failed=self._system_pause.failed,
        )

    def _recheck_line(self, check: _LiveCheck) -> tuple[str, NoteRefusal | None]:
        if check.request is None:
            return "clinic_gone", None
        result = check.result
        # D9: never "verified" under a replaced or removed key (PR-MED-150).
        stale = result is None or not self._rev_current(result.request)
        outcome = None if stale or result is None else result.outcome
        if outcome is None:
            return "checking", None
        if isinstance(outcome, Verified):
            return "verified", None
        if isinstance(outcome, UnverifiedOffline):
            return "offline", None
        return "refused", outcome.reason

    def _refresh_view(self) -> None:
        self._screen.set_chrome_view(models.chrome_view_text(self.view()))
