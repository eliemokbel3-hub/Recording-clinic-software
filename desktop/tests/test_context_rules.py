"""The pause rule and the reminder index (Cliniko workflow safeguards plan
D5 and D6, Tasks 5.1-5.3): Qt-free, pure — D5's ``pause_for`` table as a
parameterised test, the tab-binding evaluator over every report shape, and
the Unreviewed reminder index."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from encounter_fakes import (
    CLINIC_ID,
    HOST,
    NOTE,
    OTHER_HOST,
    OTHER_NOTE,
    PATIENT,
    consent_for,
    context,
)
from scribe_desktop.context_rules import (
    CONTEXT_REASONS,
    LINKED_ONLY_REASONS,
    PBT_APMSUSPEND,
    WM_POWERBROADCAST,
    ContextEvaluator,
    PauseAction,
    PauseReason,
    ReminderEntry,
    ReminderIndex,
    is_suspend_message,
    names_note,
    pause_action,
    reminder_entry,
)
from scribe_desktop.encounter import NoteTarget, unlinked_consent
from scribe_desktop.protocol import ContextPayload
from scribe_desktop.session import RecordingSession, SessionState

TARGET = NoteTarget(clinic_host=HOST, patient_id=PATIENT, note_id=NOTE)
TAB = 41
OTHER_TAB = 42
SESSION = "a" * 32


def report(
    *,
    tab_id: int = TAB,
    focused: bool = True,
    page: str = "note",
    host: str = HOST,
    patient_id: str = PATIENT,
    note_id: str = NOTE,
    seq: int = 1,
) -> ContextPayload:
    fields: dict[str, Any] = {
        "seq": seq,
        "tab_id": tab_id,
        "window_id": 3,
        "focused": focused,
        "page": page,
    }
    if page in ("note", "login", "other_cliniko"):
        fields["host"] = host
    if page == "note":
        fields.update(patient_id=patient_id, note_id=note_id)
    return ContextPayload(**fields)


# --- D5's pause_for table ---------------------------------------------------

_OTHER_STATES = [
    SessionState.IDLE,
    SessionState.PROCESSING,
    SessionState.QUEUED,
    SessionState.FAILED,
    SessionState.WRITTEN,
    SessionState.DISCARDED,
    SessionState.EXPIRED,
]


class TestPauseForTable:
    @pytest.mark.parametrize("reason", list(PauseReason))
    def test_recording_pauses_and_a_context_reason_blocks_a_linked_session(
        self, reason: PauseReason
    ) -> None:
        assert pause_action(SessionState.RECORDING, reason, linked=True) == PauseAction(
            pause=True, block=reason in CONTEXT_REASONS
        )

    @pytest.mark.parametrize("reason", list(PauseReason))
    def test_paused_only_blocks(self, reason: PauseReason) -> None:
        assert pause_action(SessionState.PAUSED, reason, linked=True) == PauseAction(
            pause=False, block=reason in CONTEXT_REASONS
        )

    @pytest.mark.parametrize("state", _OTHER_STATES)
    @pytest.mark.parametrize("reason", list(PauseReason))
    @pytest.mark.parametrize("linked", [True, False])
    def test_every_other_state_is_a_no_op(
        self, state: SessionState, reason: PauseReason, linked: bool
    ) -> None:
        assert pause_action(state, reason, linked=linked) == PauseAction(False, False)

    @pytest.mark.parametrize("state", [SessionState.RECORDING, SessionState.PAUSED])
    @pytest.mark.parametrize("reason", sorted(LINKED_ONLY_REASONS))
    def test_chromes_reasons_never_touch_an_unlinked_recording(
        self, state: SessionState, reason: PauseReason
    ) -> None:
        assert pause_action(state, reason, linked=False) == PauseAction(False, False)

    def test_suspend_pauses_an_unlinked_recording_without_a_block(self) -> None:
        assert pause_action(
            SessionState.RECORDING, PauseReason.SUSPEND, linked=False
        ) == PauseAction(pause=True, block=False)

    @pytest.mark.parametrize("reason", [PauseReason.HOTKEY, PauseReason.SPOKEN])
    def test_hands_free_reasons_pause_but_never_block(self, reason: PauseReason) -> None:
        assert reason not in CONTEXT_REASONS
        for linked in (True, False):
            assert pause_action(SessionState.RECORDING, reason, linked=linked) == PauseAction(
                pause=True, block=False
            )

    def test_the_context_reasons_are_exactly_d5s(self) -> None:
        assert CONTEXT_REASONS == {
            PauseReason.NOTE_CHANGED,
            PauseReason.LEFT_NOTE,
            PauseReason.TAB_CLOSED,
            PauseReason.OTHER_NOTE,
            PauseReason.LOGIN,
            PauseReason.PIPE_LOST,
            PauseReason.NEW_CLIENT,
            PauseReason.SUSPEND,
        }


class TestSuspendMessage:
    def test_only_the_suspend_broadcast_counts(self) -> None:
        assert is_suspend_message(WM_POWERBROADCAST, PBT_APMSUSPEND)
        assert not is_suspend_message(WM_POWERBROADCAST, 0x0012)  # resume automatic
        assert not is_suspend_message(WM_POWERBROADCAST, 0x0007)  # resume suspend
        assert not is_suspend_message(0x0010, PBT_APMSUSPEND)  # WM_CLOSE


# --- the evaluator (D5's table over reports) ------------------------------------


def _bound() -> ContextEvaluator:
    rules = ContextEvaluator()
    rules.bind(SESSION, TAB)
    return rules


# D5's table over reports, shared with `test_cross_patient.py`'s context rows
# (Task 5.6 drives every row through the bridge end to end).
BOUND_TAB_CASES: list[tuple[dict[str, Any], PauseReason | None]] = [
    ({}, None),  # its own note again
    ({"note_id": OTHER_NOTE}, PauseReason.NOTE_CHANGED),
    ({"patient_id": "1002"}, PauseReason.NOTE_CHANGED),
    ({"host": OTHER_HOST}, PauseReason.NOTE_CHANGED),
    ({"page": "other_cliniko"}, PauseReason.LEFT_NOTE),
    ({"page": "login"}, PauseReason.LEFT_NOTE),
    ({"page": "not_cliniko"}, PauseReason.LEFT_NOTE),  # left the allow-list
    ({"page": "closed"}, PauseReason.TAB_CLOSED),
    # focus does not matter for the bound tab: it changed in the background
    ({"note_id": OTHER_NOTE, "focused": False}, PauseReason.NOTE_CHANGED),
    ({"page": "not_cliniko", "focused": False}, PauseReason.LEFT_NOTE),
]
OTHER_TAB_CASES: list[tuple[dict[str, Any], PauseReason | None]] = [
    ({"note_id": OTHER_NOTE}, PauseReason.OTHER_NOTE),
    ({"host": OTHER_HOST, "note_id": OTHER_NOTE}, PauseReason.OTHER_NOTE),
    ({"page": "login"}, PauseReason.LOGIN),
    # the positive controls: none of these pause
    ({"page": "not_cliniko"}, None),  # a SEPARATE non-Cliniko tab
    ({"page": "other_cliniko"}, None),  # the calendar in another tab
    ({"page": "closed"}, None),
    ({}, None),  # the same note in a second tab
    ({"note_id": OTHER_NOTE, "focused": False}, None),  # not focused
    ({"page": "login", "focused": False}, None),
]


class TestContextEvaluator:
    @pytest.mark.parametrize(("shape", "expected"), BOUND_TAB_CASES)
    def test_the_bound_tab(self, shape: dict[str, Any], expected: PauseReason | None) -> None:
        assert _bound().evaluate(SESSION, TARGET, report(**shape)) is expected

    @pytest.mark.parametrize(("shape", "expected"), OTHER_TAB_CASES)
    def test_another_tab(self, shape: dict[str, Any], expected: PauseReason | None) -> None:
        rules = _bound()
        assert rules.evaluate(SESSION, TARGET, report(tab_id=OTHER_TAB, **shape)) is expected
        assert rules.bound_tab == TAB  # another tab never takes the binding

    def test_closing_the_bound_tab_unbinds_it(self) -> None:
        rules = _bound()
        assert rules.evaluate(SESSION, TARGET, report(page="closed")) is PauseReason.TAB_CLOSED
        assert rules.bound_tab is None

    def test_after_pipe_loss_it_rebinds_only_by_exact_ids(self) -> None:
        rules = _bound()
        rules.lose_tab()
        # a stale tab id means nothing now: the old tab's other note is just
        # another focused note
        assert rules.evaluate(SESSION, TARGET, report(note_id=OTHER_NOTE)) is (
            PauseReason.OTHER_NOTE
        )
        assert rules.bound_tab is None
        # the same note under another patient id is not the session's note
        assert rules.evaluate(
            SESSION, TARGET, report(tab_id=77, patient_id="1002")
        ) is PauseReason.OTHER_NOTE
        assert rules.bound_tab is None
        assert rules.evaluate(SESSION, TARGET, report(tab_id=77, focused=False)) is None
        assert rules.bound_tab == 77  # re-bound by ids, focused or not
        assert rules.evaluate(SESSION, TARGET, report(tab_id=77, page="closed")) is (
            PauseReason.TAB_CLOSED
        )

    def test_the_binding_belongs_to_one_session(self) -> None:
        rules = _bound()
        other_session = "b" * 32
        # a new session starts unbound: TAB's other note is only a focused note
        assert rules.evaluate(other_session, TARGET, report(tab_id=TAB, page="not_cliniko")) is (
            None
        )
        assert rules.bound_tab is None

    def test_forget_drops_the_binding(self) -> None:
        rules = _bound()
        rules.forget()
        assert rules.bound_tab is None

    def test_names_note_needs_all_three_ids(self) -> None:
        assert names_note(report(), TARGET)
        assert not names_note(report(page="login"), TARGET)
        assert not names_note(report(host=OTHER_HOST), TARGET)


# --- the reminder index (D6) ------------------------------------------------------


def _session(state: SessionState, *, linked: bool = True) -> RecordingSession:
    if linked:
        ctx = context()
        return RecordingSession(consent=consent_for(ctx), encounter_context=ctx).with_state(
            state
        )
    return RecordingSession(consent=unlinked_consent()).with_state(state)


class TestReminderEntry:
    def test_a_retired_linked_queued_session_is_indexed_by_its_note(self) -> None:
        session = _session(SessionState.QUEUED)
        assert reminder_entry(session) == ReminderEntry(CLINIC_ID, NOTE, session.session_id)

    @pytest.mark.parametrize(
        "state", [SessionState.FAILED, SessionState.WRITTEN, SessionState.DISCARDED]
    )
    def test_nothing_to_review_adds_nothing(self, state: SessionState) -> None:
        assert reminder_entry(_session(state)) is None

    def test_an_unlinked_session_adds_nothing(self) -> None:
        assert reminder_entry(_session(SessionState.QUEUED, linked=False)) is None


class TestReminderIndex:
    def test_newest_first_and_one_removal_removes_one_entry(self) -> None:
        index = ReminderIndex()
        index.add(ReminderEntry(CLINIC_ID, NOTE, "s1"))
        index.add(ReminderEntry(CLINIC_ID, NOTE, "s2"))  # a second recording, one note
        index.add(ReminderEntry(CLINIC_ID, OTHER_NOTE, "s3"))
        assert index.sessions_for(CLINIC_ID, NOTE) == ("s2", "s1")
        assert len(index) == 3 and "s1" in index
        assert index.remove("s2") is True
        assert index.sessions_for(CLINIC_ID, NOTE) == ("s1",)  # the other stays
        assert index.sessions_for(CLINIC_ID, OTHER_NOTE) == ("s3",)
        assert index.remove("s2") is False
        index.remove("s1")
        assert index.sessions_for(CLINIC_ID, NOTE) == ()
        assert index.session_ids() == {"s3"}

    def test_the_same_note_in_another_clinic_is_another_key(self) -> None:
        index = ReminderIndex()
        index.add(ReminderEntry(CLINIC_ID, NOTE, "s1"))
        index.add(ReminderEntry("fedcba9876543210", NOTE, "s2"))
        assert index.sessions_for(CLINIC_ID, NOTE) == ("s1",)

    def test_adding_a_session_again_moves_it_not_duplicates_it(self) -> None:
        index = ReminderIndex()
        index.add(ReminderEntry(CLINIC_ID, NOTE, "s1"))
        index.add(ReminderEntry(CLINIC_ID, NOTE, "s2"))
        index.add(ReminderEntry(CLINIC_ID, NOTE, "s1"))
        assert index.sessions_for(CLINIC_ID, NOTE) == ("s1", "s2")
        assert len(index) == 2


def test_the_module_holds_no_qt_and_no_windows_call() -> None:
    """Qt-free by design: the rule is testable without a display or Windows
    (the suspend message is parsed in the main window)."""
    import scribe_desktop.context_rules as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "PySide6" not in source and "import ctypes" not in source
