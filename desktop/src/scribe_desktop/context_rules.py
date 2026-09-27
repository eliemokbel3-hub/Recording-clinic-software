"""The pause rule and the Unreviewed reminder index (Cliniko workflow
safeguards plan D5 and D6, Tasks 5.1-5.3).

Qt-free and GUI-thread-only: the Chrome bridge (``ui/bridge.py``) feeds it
Chrome's reports and pipe events and applies what it decides through the
Session screen's slots. Nothing here touches the controller, a key or the
disk, and nothing here logs.

THE PAUSE RULE (D5). ``pause_action`` is D5's ``pause_for`` table: by
session state, whether a reason pauses and whether it sets the resolution
block. ``ContextEvaluator`` turns each context report into at most one
reason, for the LINKED live session only, against the tab that session is
bound to:

- the bound tab changes note or patient, or leaves its note (any page that
  is not a note, including ``not_cliniko``), or closes;
- the focused tab reports another note, or Cliniko's login page;
- a tab that is neither bound nor focused never pauses, and neither does a
  SEPARATE tab showing a page that is not Cliniko's (an untracked tab is
  never reported at all); the bound tab leaving its note for such a page is
  the first rule above.

Pipe loss, a new pipe client, machine suspend and — since 2026-09-28 (the
practitioner's decision after the Phase 5 smoke: a Modern Standby machine
did not pause on sleep) — the Windows session LOCKING come from the bridge
and the main window; unlock resumes nothing. The rule is a pause rule only:
nothing here resumes. A
linked session resumes only on a current report of its own note (the
bridge's ``resume_refusal``), and a tab is re-bound only to a report naming
the session's exact clinic host, patient and note (D5's re-bind by ids).

THE REMINDER INDEX (D6). ``ReminderIndex`` maps a Cliniko note to the
retired, still-unreviewed linked sessions recorded on it, newest first —
ids only, in memory only, never persisted. It is filled at retirement from
the session's in-memory ``EncounterContext`` and loses exactly one entry
when that session is completed, discarded or expires.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from scribe_desktop.encounter import NoteTarget
from scribe_desktop.protocol import ContextPayload
from scribe_desktop.session import RecordingSession, SessionState

# Windows power broadcast (the main window's ``nativeEvent``): the machine
# is about to suspend (D5). Resume-from-suspend pauses nothing. On a Modern
# Standby machine it arrives only for a window registered with
# ``RegisterSuspendResumeNotification`` (``system_events``).
WM_POWERBROADCAST: Final = 0x0218
PBT_APMSUSPEND: Final = 0x0004
# The Windows session changed (``WTSRegisterSessionNotification``): only a
# LOCK pauses (D5 as amended 2026-09-28); an unlock resumes nothing — it only
# ends the lock's refusal of every Resume (codex round 51 PR-MED-300).
WM_WTSSESSION_CHANGE: Final = 0x02B1
WTS_SESSION_LOCK: Final = 0x7
WTS_SESSION_UNLOCK: Final = 0x8
# How long a "Resume previous" waits for Chrome to report the recording's
# own note before it lapses (the click then has to be made again).
RESUME_PREVIOUS_WINDOW_SECONDS: Final = 30.0


class PauseReason(StrEnum):
    """Why a recording was paused. Every member but ``HOTKEY`` and
    ``SPOKEN`` (Phase 7) is a CONTEXT reason and sets the block."""

    NOTE_CHANGED = "note_changed"
    LEFT_NOTE = "left_note"
    TAB_CLOSED = "tab_closed"
    OTHER_NOTE = "other_note"
    LOGIN = "login"
    PIPE_LOST = "pipe_lost"
    NEW_CLIENT = "new_client"
    SUSPEND = "suspend"
    LOCKED = "locked"
    HOTKEY = "hotkey"
    SPOKEN = "spoken"


CONTEXT_REASONS: Final[frozenset[PauseReason]] = frozenset(PauseReason) - {
    PauseReason.HOTKEY,
    PauseReason.SPOKEN,
}
# The machine's own reasons: they apply to EVERY recording, linked or not,
# and — the practitioner having left or the machine sleeping — they also end
# a clicked "Resume previous" (the bridge), so nothing resumes behind them.
SYSTEM_REASONS: Final[frozenset[PauseReason]] = frozenset(
    {PauseReason.SUSPEND, PauseReason.LOCKED}
)
# Chrome's reasons. They concern a recording bound to a Cliniko note, so an
# UNLINKED (desktop) recording ignores them; the system and the hands-free
# reasons apply to every recording.
LINKED_ONLY_REASONS: Final[frozenset[PauseReason]] = CONTEXT_REASONS - SYSTEM_REASONS


@dataclass(frozen=True)
class PauseAction:
    pause: bool
    block: bool


_NOTHING: Final = PauseAction(pause=False, block=False)


def pause_action(state: SessionState, reason: PauseReason, *, linked: bool) -> PauseAction:
    """D5's ``pause_for`` by state: RECORDING pauses (and blocks for a
    context reason); PAUSED only blocks; every other state does nothing.
    The block is the resolution between two Cliniko notes, so only a LINKED
    session gets one, and a Chrome reason does nothing to an unlinked one."""
    if reason in LINKED_ONLY_REASONS and not linked:
        return _NOTHING
    block = linked and reason in CONTEXT_REASONS
    if state is SessionState.RECORDING:
        return PauseAction(pause=True, block=block)
    if state is SessionState.PAUSED:
        return PauseAction(pause=False, block=block)
    return _NOTHING


def is_suspend_message(message: int, wparam: int) -> bool:
    """A ``WM_POWERBROADCAST`` announcing suspend (``PBT_APMSUSPEND``)."""
    return message == WM_POWERBROADCAST and wparam == PBT_APMSUSPEND


def is_lock_message(message: int, wparam: int) -> bool:
    """A ``WM_WTSSESSION_CHANGE`` announcing a lock (``WTS_SESSION_LOCK``)."""
    return message == WM_WTSSESSION_CHANGE and wparam == WTS_SESSION_LOCK


def is_unlock_message(message: int, wparam: int) -> bool:
    """A ``WM_WTSSESSION_CHANGE`` announcing an unlock (``WTS_SESSION_UNLOCK``)."""
    return message == WM_WTSSESSION_CHANGE and wparam == WTS_SESSION_UNLOCK


def names_note(report: ContextPayload, target: NoteTarget) -> bool:
    """The report is a note page naming exactly ``target``."""
    return report.page == "note" and (report.host, report.patient_id, report.note_id) == (
        target.clinic_host,
        target.patient_id,
        target.note_id,
    )


class ContextEvaluator:
    """GUI thread: which tab the linked live session is bound to, and D5's
    reason (if any) for each report. The binding belongs to one session:
    asking about another session starts it unbound."""

    def __init__(self) -> None:
        self._session_id: str | None = None
        self._tab: int | None = None

    @property
    def bound_tab(self) -> int | None:
        return self._tab

    def bind(self, session_id: str, tab_id: int | None) -> None:
        """A linked Start (or Resume) from ``tab_id``."""
        self._session_id = session_id
        self._tab = tab_id

    def lose_tab(self) -> None:
        """Pipe loss or a new pipe client: tab ids no longer mean anything,
        so the session waits unbound for a report of its own note."""
        self._tab = None

    def forget(self) -> None:
        self._session_id = None
        self._tab = None

    def evaluate(
        self, session_id: str, target: NoteTarget, report: ContextPayload
    ) -> PauseReason | None:
        if session_id != self._session_id:
            self.bind(session_id, None)
        same = names_note(report, target)
        if report.tab_id == self._tab:
            if report.page == "closed":
                self._tab = None
                return PauseReason.TAB_CLOSED
            if report.page != "note":
                return PauseReason.LEFT_NOTE
            return None if same else PauseReason.NOTE_CHANGED
        if self._tab is None and same:
            self._tab = report.tab_id  # D5: re-bind by ids, never by position
            return None
        if report.focused and report.page == "note" and not same:
            return PauseReason.OTHER_NOTE
        if report.focused and report.page == "login":
            return PauseReason.LOGIN
        return None


# --- the Unreviewed reminder index (D6) ----------------------------------------


@dataclass(frozen=True)
class ReminderEntry:
    clinic_id: str
    note_id: str
    session_id: str


def reminder_entry(session: RecordingSession) -> ReminderEntry | None:
    """The index entry a RETIRED session adds: a linked session whose
    transcript is ready for review (QUEUED). An unlinked or failed one adds
    none — it has no note to remind about, or nothing to review yet."""
    context = session.encounter_context
    if context is None or session.state is not SessionState.QUEUED:
        return None
    return ReminderEntry(context.clinic_id, context.treatment_note_id, session.session_id)


class ReminderIndex:
    """``(clinic_id, note_id) -> [session_id, ...]``, newest first (D6). One
    note can own several recordings; removing one session removes only its
    own entry."""

    def __init__(self) -> None:
        self._notes: dict[tuple[str, str], list[str]] = {}

    def add(self, entry: ReminderEntry) -> None:
        self.remove(entry.session_id)
        self._notes.setdefault((entry.clinic_id, entry.note_id), []).insert(
            0, entry.session_id
        )

    def remove(self, session_id: str) -> bool:
        for key, sessions in list(self._notes.items()):
            if session_id in sessions:
                sessions.remove(session_id)
                if not sessions:
                    del self._notes[key]
                return True
        return False

    def sessions_for(self, clinic_id: str, note_id: str) -> tuple[str, ...]:
        return tuple(self._notes.get((clinic_id, note_id), ()))

    def session_ids(self) -> frozenset[str]:
        return frozenset(sid for sessions in self._notes.values() for sid in sessions)

    def __contains__(self, session_id: object) -> bool:
        return session_id in self.session_ids()

    def __len__(self) -> int:
        return sum(len(sessions) for sessions in self._notes.values())
