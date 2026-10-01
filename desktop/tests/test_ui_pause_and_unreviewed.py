"""The Session screen and main window side of Cliniko workflow safeguards
plan Phase 5: the resume guard, the two-step Discard, Start at QUEUED under
the review lease, the retired session entering the reminder index, the
suspend pause and its desktop cue. Offscreen; fakes only — no pipe, no
socket, no model."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from scribe_desktop.context_rules import (  # noqa: E402
    PBT_APMSUSPEND,
    WM_POWERBROADCAST,
    PauseReason,
)
from scribe_desktop.encounter import linked_consent, unlinked_consent  # noqa: E402
from scribe_desktop.session import RecordingSession, SessionState  # noqa: E402
from scribe_desktop.session_store import KEY_FILENAME, TRANSCRIPT_FILENAME  # noqa: E402
from scribe_desktop.ui import models  # noqa: E402
from scribe_desktop.ui import session_screen as session_screen_module  # noqa: E402
from test_ui_screens import (  # noqa: E402
    FakeController,
    _linked_context,
    _main_window,
    _session_screen,
)


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _queued_linked() -> RecordingSession:
    context = _linked_context()
    return RecordingSession(
        consent=linked_consent(context), encounter_context=context
    ).with_state(SessionState.QUEUED)


class TestResumeGuard:
    """Task 5.1 (D5, Constraint 7): every Resume from the slot asks first."""

    def test_a_refusal_is_shown_and_nothing_is_called(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller)
        screen.on_start()
        screen.on_pause()
        screen.set_resume_guard(lambda: "Open the note first.")
        resumed: list[int] = []
        screen.session_resumed.connect(lambda: resumed.append(1))
        assert screen.on_resume() is False
        assert ("resume",) not in controller.calls
        assert screen.message_label.text() == "Open the note first."
        assert resumed == []
        screen.set_resume_guard(lambda: None)
        assert screen.on_resume() is True
        assert ("resume",) in controller.calls and resumed == [1]
        screen.deleteLater()

    def test_the_resume_button_runs_the_guard_too(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller)
        screen.on_start()
        screen.on_pause()
        screen.set_resume_guard(lambda: "No.")
        screen.resume_button.click()
        assert ("resume",) not in controller.calls
        screen.deleteLater()


class TestTwoStepDiscard:
    """Task 5.2: the Session screen's Discard button asks once more."""

    def test_the_first_click_asks_and_the_second_discards(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller)
        screen.on_start()
        screen.discard_button.click()
        assert ("discard",) not in controller.calls
        assert screen.discard_button.text() == session_screen_module.DISCARD_CONFIRM_LABEL
        assert screen.message_label.text() == models.DISCARD_CONFIRM_MESSAGE
        screen.discard_button.click()
        assert ("discard",) in controller.calls
        assert screen.discard_button.text() == "Discard"
        screen.deleteLater()

    def test_a_late_second_click_asks_again(
        self, qapp: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        now = [100.0]
        monkeypatch.setattr(session_screen_module.time, "monotonic", lambda: now[0])
        controller = FakeController()
        screen = _session_screen(controller)
        screen.on_start()
        screen.discard_button.click()
        now[0] += session_screen_module.DISCARD_CONFIRM_SECONDS + 1
        screen.discard_button.click()
        assert ("discard",) not in controller.calls  # re-armed, not discarded
        screen.discard_button.click()
        assert ("discard",) in controller.calls
        screen.deleteLater()

    def test_a_click_armed_for_another_session_asks_again(self, qapp: Any) -> None:
        controller = FakeController()
        controller.session_ref = "a" * 24
        screen = _session_screen(controller)
        screen.on_start()
        screen.discard_button.click()
        controller.session_ref = "b" * 24  # a different session is tracked now
        screen.discard_button.click()
        assert ("discard",) not in controller.calls
        screen.deleteLater()

    def test_leaving_a_discardable_state_disarms(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller)
        screen.on_start()
        screen.discard_button.click()
        controller.state_value = SessionState.PROCESSING
        screen._watch_state()
        assert screen.discard_button.text() == "Discard"
        assert screen._discard_armed is None
        screen.deleteLater()

    def test_the_confirm_label_goes_when_its_window_lapses_or_its_session_changes(
        self, qapp: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 32 LOW-026: the poll puts the plain label back, so a click
        under "Confirm discard" always discards."""
        now = [100.0]
        monkeypatch.setattr(session_screen_module.time, "monotonic", lambda: now[0])
        controller = FakeController()
        controller.session_ref = "a" * 24
        screen = _session_screen(controller)
        screen.on_start()
        screen.discard_button.click()
        screen._watch_state()
        assert screen.discard_button.text() == session_screen_module.DISCARD_CONFIRM_LABEL
        now[0] += session_screen_module.DISCARD_CONFIRM_SECONDS + 1
        screen._watch_state()
        assert screen.discard_button.text() == "Discard" and screen._discard_armed is None
        screen.discard_button.click()
        controller.session_ref = "b" * 24
        screen._watch_state()
        assert screen.discard_button.text() == "Discard" and screen._discard_armed is None
        assert ("discard",) not in controller.calls
        screen.deleteLater()


class TestStartAtQueued:
    """Task 5.3 (D6): Start for the next patient at QUEUED, unless the
    review lease is held; a Start that retires a session announces it."""

    def test_start_is_offered_at_queued_and_retires_the_previous_session(
        self, qapp: Any
    ) -> None:
        controller = FakeController()
        previous = _queued_linked()
        controller.session_value = previous
        controller.state_value = SessionState.QUEUED
        screen = _session_screen(controller)
        assert screen.start_button.isEnabled()
        retired: list[object] = []
        screen.session_retired.connect(retired.append)
        screen.on_start()
        assert ("start", 7) in controller.calls
        assert retired == [previous]
        screen.deleteLater()

    def test_the_review_lease_disables_start_with_a_hint(self, qapp: Any) -> None:
        controller = FakeController()
        controller.session_value = _queued_linked()
        controller.state_value = SessionState.QUEUED
        controller.generating = True
        screen = _session_screen(controller)
        assert not screen.start_button.isEnabled()
        assert not screen.consent_checkbox.isEnabled()
        assert screen.start_button.toolTip() == models.REVIEW_OPEN_START_HINT
        controller.generating = False
        screen._watch_state()  # the poll notices the lease went
        assert screen.start_button.isEnabled()
        assert screen.start_button.toolTip() == ""
        screen.deleteLater()

    def test_a_write_in_flight_disables_start_and_keeps_the_tick(self, qapp: Any) -> None:
        """H1 round 45 LOW-002 (draft-write D9): while a draft write holds
        the queued session, Start and the consent box are disabled with the
        write-in-flight hint — the controller would refuse the Start anyway,
        but only after the tick was spent; the poll re-enables Start when
        the write ends."""
        controller = FakeController()
        previous = _queued_linked()
        controller.session_value = previous
        controller.state_value = SessionState.QUEUED
        screen = _session_screen(controller)
        screen.consent_checkbox.setChecked(True)
        controller.writing_id = previous.session_id
        screen._watch_state()  # the poll notices the write
        assert not screen.start_button.isEnabled()
        assert not screen.consent_checkbox.isEnabled()
        assert screen.consent_checkbox.isChecked()  # not spent
        assert screen.start_button.toolTip() == models.write_line("write_in_flight")
        controller.writing_id = None
        screen._watch_state()  # the poll notices the write ended
        assert screen.start_button.isEnabled()
        assert screen.start_button.toolTip() == ""
        screen.deleteLater()

    def test_a_start_that_fails_after_retiring_still_announces_it(
        self, qapp: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """H1 round 53 LOW-040: the controller retires the queued session
        before the new device opens; a Start that then fails (the microphone
        busy) still announces the retirement, so the session reaches the
        reminder index. A failure that retired nothing announces nothing
        (the control)."""
        controller = FakeController()
        previous = _queued_linked()
        controller.session_value = previous
        controller.state_value = SessionState.QUEUED
        screen = _session_screen(controller)
        retired: list[object] = []
        screen.session_retired.connect(retired.append)

        attempts: list[str] = []

        def refused_before_retiring(*_args: Any, **_kwargs: Any) -> RecordingSession:
            attempts.append("refused")
            raise RuntimeError("refused")

        monkeypatch.setattr(controller, "start", refused_before_retiring)
        screen.on_start()
        assert attempts == ["refused"]
        assert retired == []  # still tracked: nothing was retired

        def fails_after_retiring(*_args: Any, **_kwargs: Any) -> RecordingSession:
            attempts.append("failed")
            controller.session_value = None  # retired, then the device failed
            raise RuntimeError("the microphone could not be opened")

        monkeypatch.setattr(controller, "start", fails_after_retiring)
        screen.consent_checkbox.setChecked(True)  # every Start clears the tick
        screen.on_start()
        assert attempts == ["refused", "failed"]
        assert retired == [previous]
        assert "Start failed" in screen.message_label.text()
        screen.deleteLater()

    def test_no_previous_session_retires_nothing(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller)
        retired: list[object] = []
        screen.session_retired.connect(retired.append)
        screen.on_start()
        assert retired == []
        screen.deleteLater()


# A real MainWindow on Qt's WINDOWS platform, its native window created but
# never shown; three messages sent through the real window procedure: the
# suspend broadcast, a resume broadcast (pauses nothing) and WM_NULL. Every
# store root is under the temporary directory it is given.
_REAL_DISPATCH_CHILD = """\
import ctypes, json, sys
from pathlib import Path
from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
apply_offline_env()
assert_offline_env()
from PySide6.QtWidgets import QApplication
from scribe_desktop.audio_capture import MockCaptureBackend
from scribe_desktop.clinics import ClinicRegistry
from scribe_desktop.past_sessions import PastSessionStore
from scribe_desktop.session import SessionController
from scribe_desktop.ui.main_window import MainWindow
app = QApplication([])
base = Path(sys.argv[1])
root = base / 'sessions'
backend = MockCaptureBackend()
controller = SessionController(backend, sessions_root=root)
w = MainWindow(controller, backend, sessions_root=root,
               profile_root=base / 'profile', config_root=base / 'config',
               style_root=base / 'style', language_model_available=lambda: False,
               clinic_registry=ClinicRegistry(base / 'clinics.json'),
               past_sessions=PastSessionStore(base / 'past_sessions'))
seen = []
w.pause_for = lambda reason: seen.append(str(reason))
hwnd = int(w.winId())
user32 = ctypes.WinDLL('user32')
user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t,
                                ctypes.c_ssize_t]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.SendMessageW(hwnd, 0x0218, 0x0004, 0)
user32.SendMessageW(hwnd, 0x0218, 0x0012, 0)
user32.SendMessageW(hwnd, 0x0000, 0, 0)
app.processEvents()
print('SEEN ' + json.dumps(seen), flush=True)
"""


def _msg_address(message: int, wparam: int) -> tuple[Any, int]:
    from scribe_desktop.ui.main_window import _MSG

    msg = _MSG(None, message, wparam)
    return msg, ctypes.addressof(msg)


class TestSuspendAndCue:
    """Task 5.1 (D5): suspend pauses; every pause shows the desktop cue."""

    def test_the_suspend_broadcast_is_recognised(self) -> None:
        from scribe_desktop.ui.main_window import _is_suspend_event

        keep, address = _msg_address(WM_POWERBROADCAST, PBT_APMSUSPEND)
        assert _is_suspend_event(b"windows_generic_MSG", address)
        assert not _is_suspend_event(b"xcb_generic_event_t", address)
        other, other_address = _msg_address(WM_POWERBROADCAST, 0x0012)
        assert not _is_suspend_event(b"windows_generic_MSG", other_address)
        assert not _is_suspend_event(b"windows_generic_MSG", 0)
        assert keep is not None and other is not None

    def test_suspend_pauses_a_recording_and_cues(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        controller.state_value = SessionState.RECORDING  # an unlinked recording
        keep, address = _msg_address(WM_POWERBROADCAST, PBT_APMSUSPEND)
        # "not handled": Qt's own processing of the message always goes on
        assert window.nativeEvent(b"windows_generic_MSG", address) == (False, 0)
        assert ("pause",) in controller.calls
        cue = models.pause_cue_text("suspend", linked=False)
        assert window.statusBar().currentMessage() == cue
        assert window.session_screen.message_label.text() == cue
        assert keep is not None
        window.deleteLater()

    def test_the_override_never_raises_into_qt(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = _main_window(tmp_path, FakeController())

        def broken(_reason: object) -> None:
            raise RuntimeError("boom")

        monkeypatch.setattr(window, "pause_for", broken)
        keep, address = _msg_address(WM_POWERBROADCAST, PBT_APMSUSPEND)
        assert window.nativeEvent(b"windows_generic_MSG", address) == (False, 0)
        assert window.nativeEvent(object(), object()) == (False, 0)
        assert keep is not None
        window.deleteLater()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows messages")
    @pytest.mark.skipif(
        os.environ.get("SCRIBE_SKIP_INTEGRATION") == "1",
        reason="integration explicitly skipped via SCRIBE_SKIP_INTEGRATION=1",
    )
    def test_a_real_suspend_message_through_qts_dispatch(self, tmp_path: Path) -> None:
        """The path the app really takes: Windows' window procedure → Qt's
        windows platform → the Python override, in a child process with a
        native (never shown) window. Qt prints any exception an override
        raises, or a result it cannot use, on stderr — neither may appear."""
        env = dict(os.environ)
        env["QT_QPA_PLATFORM"] = "windows"
        child = subprocess.run(
            [sys.executable, "-c", _REAL_DISPATCH_CHILD, str(tmp_path)],
            capture_output=True,
            env=env,
            timeout=120,
            check=False,
        )
        assert child.returncode == 0, child.stderr.decode(errors="replace")
        lines = child.stdout.decode().splitlines()
        # The suspend met an idle controller, so round 57 SEC-021's queued
        # re-check asks once more (the real `pause_for` does nothing at IDLE).
        assert lines[-1] == 'SEEN ["suspend", "suspend"]'
        for marker in (b"Traceback", b"TypeError", b"ValueError", b"wrong argument"):
            assert marker not in child.stderr, child.stderr.decode(errors="replace")

    def test_suspend_when_not_recording_does_nothing(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        window.pause_for(PauseReason.SUSPEND)
        assert ("pause",) not in controller.calls
        assert window.statusBar().currentMessage() == ""
        window.deleteLater()

    def test_the_bridges_cue_reaches_the_desktop(self, qapp: Any, tmp_path: Path) -> None:
        window = _main_window(tmp_path, FakeController())
        bridge = window.attach_chrome_link()
        bridge.pause_cue.emit("Paused - test.")
        assert window.statusBar().currentMessage() == "Paused - test."
        assert window.session_screen.message_label.text() == "Paused - test."
        bridge.deleteLater()
        window.deleteLater()


class TestReminderIndexWiring:
    """Task 5.3 (D6): a retired linked queued session enters the index; a
    removal takes out exactly its own entry and reference."""

    def test_a_retired_linked_queued_session_is_indexed(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _main_window(tmp_path, FakeController())
        previous = _queued_linked()
        window.session_screen.session_retired.emit(previous)
        context = previous.encounter_context
        assert context is not None
        assert window.reminders.sessions_for(
            context.clinic_id, context.treatment_note_id
        ) == (previous.session_id,)
        unlinked = RecordingSession(consent=unlinked_consent()).with_state(SessionState.QUEUED)
        window.session_screen.session_retired.emit(unlinked)
        assert len(window.reminders) == 1
        window.deleteLater()

    def test_a_recovery_list_discard_forgets_the_entry_and_its_ref(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        previous = _queued_linked()
        window.session_screen.session_retired.emit(previous)
        window.recovery_screen.session_removed.emit(previous.session_id)
        assert previous.session_id not in window.reminders
        assert controller.forgotten_refs == [previous.session_id]
        window.deleteLater()

    def test_a_sweep_prunes_only_sessions_whose_key_is_gone(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _main_window(tmp_path, FakeController())
        kept, gone = _queued_linked(), _queued_linked()
        key_dir = tmp_path / kept.session_id
        key_dir.mkdir()
        (key_dir / KEY_FILENAME).write_bytes(b"x" * 64)
        window.session_screen.session_retired.emit(kept)
        window.session_screen.session_retired.emit(gone)
        window.prune_reminders()
        assert kept.session_id in window.reminders
        assert gone.session_id not in window.reminders
        window.deleteLater()

    @staticmethod
    def _on_disk(root: Path, session: RecordingSession) -> None:
        """Stat-only stand-ins: a key blob and a transcript file are all the
        listing looks at (it never decrypts)."""
        directory = root / session.session_id
        directory.mkdir()
        (directory / KEY_FILENAME).write_bytes(b"x" * 64)
        (directory / TRANSCRIPT_FILENAME).write_bytes(b"x")

    @staticmethod
    def _unreviewed_ids(window: Any) -> list[str]:
        return [info.session_id for info in window.recovery_screen.unreviewed_infos()]

    def test_a_retired_session_is_listed_without_a_manual_refresh(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Smoke S1: the Start that retires A lists A on the Recovery tab."""
        window = _main_window(tmp_path, FakeController())
        previous = _queued_linked()
        self._on_disk(tmp_path, previous)
        assert self._unreviewed_ids(window) == []
        window.session_screen.session_retired.emit(previous)
        assert self._unreviewed_ids(window) == [previous.session_id]
        assert window.recovery_screen.unreviewed_list.count() == 1
        window.deleteLater()

    def test_a_custody_protected_session_is_still_never_listed(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        previous, live = _queued_linked(), _queued_linked()
        self._on_disk(tmp_path, previous)
        self._on_disk(tmp_path, live)
        controller.reserved_ids = frozenset({live.session_id})
        window.session_screen.session_retired.emit(previous)
        assert self._unreviewed_ids(window) == [previous.session_id]
        window.deleteLater()

    def test_opening_the_recovery_tab_relists_it(self, qapp: Any, tmp_path: Path) -> None:
        window = _main_window(tmp_path, FakeController())
        window.tabs.setCurrentWidget(window.session_screen)
        later = _queued_linked()
        self._on_disk(tmp_path, later)
        assert self._unreviewed_ids(window) == []
        window.tabs.setCurrentWidget(window.recovery_screen)
        assert self._unreviewed_ids(window) == [later.session_id]
        window.deleteLater()

    def test_a_start_clears_a_stale_post_save_review(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = _main_window(tmp_path, FakeController())
        cleared: list[int] = []
        monkeypatch.setattr(window.note_screen, "clear", lambda: cleared.append(1))
        window.session_screen.session_started.emit()
        assert cleared == [1]
        window.deleteLater()
