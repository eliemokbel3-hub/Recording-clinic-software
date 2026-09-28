"""D5 as amended by the practitioner on 2026-09-28 ("sleep + screen lock"),
after the Phase 5 smoke on a Modern Standby machine did not pause on sleep:
``RegisterSuspendResumeNotification`` asks Windows to deliver
``PBT_APMSUSPEND`` to the main window, and ``WTSRegisterSessionNotification``
delivers ``WM_WTSSESSION_CHANGE``, whose ``WTS_SESSION_LOCK`` pauses ANY
recording; an unlock resumes nothing.

Offscreen; every registration goes through a FAKE registrar — no test
registers for the real session or power notifications (the Win32 registrar's
arguments are checked against a stand-in for user32 / wtsapi32). One test
sends and posts synthetic messages through Qt's real Windows dispatch in a
child process. What NO automated test here can prove is that Windows
DELIVERS these messages to this window on a given machine — that is what the
Phase 5 smoke's Modern Standby failure showed a posted message cannot stand
in for; the live smoke (Win+L, and Start -> Power -> Sleep, on the
practitioner's machine) is the proof of delivery."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from scribe_desktop import system_events  # noqa: E402
from scribe_desktop.context_rules import (  # noqa: E402
    LINKED_ONLY_REASONS,
    PBT_APMSUSPEND,
    SYSTEM_REASONS,
    WM_POWERBROADCAST,
    WM_WTSSESSION_CHANGE,
    WTS_SESSION_LOCK,
    WTS_SESSION_UNLOCK,
    PauseAction,
    PauseReason,
    is_lock_message,
    is_unlock_message,
    pause_action,
)
from scribe_desktop.encounter import unlinked_consent  # noqa: E402
from scribe_desktop.session import RecordingSession, SessionState  # noqa: E402
from scribe_desktop.system_events import (  # noqa: E402
    DEVICE_NOTIFY_WINDOW_HANDLE,
    NOT_SET_UP,
    NOTIFY_FOR_THIS_SESSION,
    SystemPauseStatus,
    SystemPauseWatch,
    Win32SystemEventRegistrar,
)
from scribe_desktop.ui import models  # noqa: E402
from test_ui_screens import FakeController, _main_window  # noqa: E402

WTS_SESSION_LOGON = 0x5
PBT_APMRESUMEAUTOMATIC = 0x12
SUSPEND_HANDLE = 0x5EED
HWND = 0x1234


class FakeSystemRegistrar:
    """``SystemEventRegistrar`` that records calls and never touches Windows."""

    def __init__(
        self,
        *,
        suspend_handle: int = SUSPEND_HANDLE,
        lock_ok: bool = True,
        raises: bool = False,
        locked_answer: bool | None = True,
    ) -> None:
        self.suspend_handle = suspend_handle
        self.lock_ok = lock_ok
        self.raises = raises
        self.locked_answer = locked_answer
        self.calls: list[tuple[str, int]] = []
        self.queries = 0

    def _call(self, name: str, value: int) -> None:
        self.calls.append((name, value))
        if self.raises:
            raise OSError("boom")

    def register_suspend(self, hwnd: int) -> int:
        self._call("register_suspend", hwnd)
        return self.suspend_handle

    def unregister_suspend(self, handle: int) -> None:
        self._call("unregister_suspend", handle)

    def register_lock(self, hwnd: int) -> bool:
        self._call("register_lock", hwnd)
        return self.lock_ok

    def unregister_lock(self, hwnd: int) -> None:
        self._call("unregister_lock", hwnd)

    def query_locked(self) -> bool | None:
        self.queries += 1
        if self.raises:
            raise OSError("boom")
        return self.locked_answer


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _msg(message: int, wparam: int) -> tuple[Any, int]:
    from scribe_desktop.ui.main_window import _MSG

    msg = _MSG(None, message, wparam)
    return msg, ctypes.addressof(msg)


def _send(window: Any, message: int, wparam: int) -> object:
    keep, address = _msg(message, wparam)
    result = window.nativeEvent(b"windows_generic_MSG", address)
    assert keep is not None
    return result


def _recording(controller: FakeController) -> RecordingSession:
    session = RecordingSession(consent=unlinked_consent()).with_state(SessionState.RECORDING)
    controller.session_value = session
    controller.state_value = SessionState.RECORDING
    return session


def _pauses(controller: FakeController) -> int:
    return controller.calls.count(("pause",))


# --- the rule ------------------------------------------------------------------


class TestLockRule:
    def test_only_a_lock_counts(self) -> None:
        assert is_lock_message(WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)
        assert not is_lock_message(WM_WTSSESSION_CHANGE, WTS_SESSION_UNLOCK)
        assert not is_lock_message(WM_WTSSESSION_CHANGE, WTS_SESSION_LOGON)
        assert not is_lock_message(WM_POWERBROADCAST, WTS_SESSION_LOCK)
        assert is_unlock_message(WM_WTSSESSION_CHANGE, WTS_SESSION_UNLOCK)
        assert not is_unlock_message(WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)
        assert not is_unlock_message(WM_WTSSESSION_CHANGE, WTS_SESSION_LOGON)

    @pytest.mark.parametrize("reason", sorted(SYSTEM_REASONS))
    def test_the_system_reasons_pause_every_recording(self, reason: PauseReason) -> None:
        """Like sleep, a lock pauses linked and unlinked recordings alike; a
        linked one also gets the block (the practitioner left the note)."""
        assert SYSTEM_REASONS == {PauseReason.SUSPEND, PauseReason.LOCKED}
        assert reason not in LINKED_ONLY_REASONS
        assert pause_action(SessionState.RECORDING, reason, linked=False) == PauseAction(
            pause=True, block=False
        )
        assert pause_action(SessionState.RECORDING, reason, linked=True) == PauseAction(
            pause=True, block=True
        )

    def test_the_lock_cue(self) -> None:
        assert models.pause_cue_text("locked", linked=False) == (
            "Paused - the computer was locked. Press Resume to carry on recording."
        )


# --- the registrations (Qt-free) -------------------------------------------------


class _FakeDll:
    """Stands in for user32 / wtsapi32: records each call, answers ``result``."""

    def __init__(self, result: int) -> None:
        self.result = result
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def __getattr__(self, name: str) -> Any:
        def call(*args: Any) -> int:
            self.calls.append((name, args))
            return self.result

        return call


class TestSystemPauseWatch:
    def test_both_are_registered_once_for_the_window(self) -> None:
        registrar = FakeSystemRegistrar()
        watch = SystemPauseWatch(registrar)
        assert watch.status == NOT_SET_UP
        assert watch.register(HWND) == SystemPauseStatus(suspend="on", lock="on")
        assert watch.register(HWND).failed == ()  # a second call reports the same
        assert registrar.calls == [("register_suspend", HWND), ("register_lock", HWND)]

    def test_the_win32_calls_ask_for_this_window_and_this_session(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        user32, wtsapi32 = _FakeDll(SUSPEND_HANDLE), _FakeDll(1)
        monkeypatch.setattr(system_events, "_user32", lambda: user32)
        monkeypatch.setattr(system_events, "_wtsapi32", lambda: wtsapi32)
        registrar = Win32SystemEventRegistrar()
        assert registrar.register_suspend(HWND) == SUSPEND_HANDLE
        assert registrar.register_lock(HWND) is True
        registrar.unregister_suspend(SUSPEND_HANDLE)
        registrar.unregister_lock(HWND)
        assert user32.calls == [
            ("RegisterSuspendResumeNotification", (HWND, DEVICE_NOTIFY_WINDOW_HANDLE)),
            ("UnregisterSuspendResumeNotification", (SUSPEND_HANDLE,)),
        ]
        assert wtsapi32.calls == [
            ("WTSRegisterSessionNotification", (HWND, NOTIFY_FOR_THIS_SESSION)),
            ("WTSUnRegisterSessionNotification", (HWND,)),
        ]
        refused_user32, refused_wts = _FakeDll(0), _FakeDll(0)
        monkeypatch.setattr(system_events, "_user32", lambda: refused_user32)
        monkeypatch.setattr(system_events, "_wtsapi32", lambda: refused_wts)
        assert registrar.register_suspend(HWND) == 0
        assert registrar.register_lock(HWND) is False

    @pytest.mark.parametrize(
        "registrar",
        [
            FakeSystemRegistrar(suspend_handle=0, lock_ok=False),
            FakeSystemRegistrar(raises=True),
        ],
        ids=["refused", "raising"],
    )
    def test_a_refusal_is_a_status_and_never_raises(self, registrar: Any) -> None:
        watch = SystemPauseWatch(registrar)
        status = watch.register(HWND)
        assert status == SystemPauseStatus(suspend="failed", lock="failed")
        assert status.failed == ("suspend", "lock")
        assert not watch.lock_matches(WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)
        watch.unregister()  # nothing was registered: nothing is given back
        assert registrar.calls == [("register_suspend", HWND), ("register_lock", HWND)]

    def test_unregister_gives_back_what_was_registered_exactly_once(self) -> None:
        registrar = FakeSystemRegistrar()
        watch = SystemPauseWatch(registrar)
        watch.register(HWND)
        watch.unregister()
        watch.unregister()  # idempotent (close, then quit, then the finally)
        assert registrar.calls[2:] == [
            ("unregister_suspend", SUSPEND_HANDLE),
            ("unregister_lock", HWND),
        ]
        assert watch.status == NOT_SET_UP

    def test_only_the_accepted_one_is_given_back(self) -> None:
        registrar = FakeSystemRegistrar(lock_ok=False)
        watch = SystemPauseWatch(registrar)
        assert watch.register(HWND) == SystemPauseStatus(suspend="on", lock="failed")
        watch.unregister()
        assert registrar.calls[2:] == [("unregister_suspend", SUSPEND_HANDLE)]

    def test_a_raising_unregister_never_raises(self) -> None:
        registrar = FakeSystemRegistrar()
        watch = SystemPauseWatch(registrar)
        watch.register(HWND)
        registrar.raises = True
        watch.unregister()
        assert watch.status == NOT_SET_UP

    def test_the_lock_matches_only_while_registered(self) -> None:
        watch = SystemPauseWatch(FakeSystemRegistrar())
        assert not watch.lock_matches(WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)
        watch.register(HWND)
        assert watch.lock_matches(WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)
        assert not watch.lock_matches(WM_WTSSESSION_CHANGE, WTS_SESSION_UNLOCK)
        watch.unregister()
        assert not watch.lock_matches(WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)


# --- the lock flag (codex round 51 PR-MED-300) ------------------------------------


class TestLockFlag:
    """Locked from the lock message until the unlock; a flag older than
    ``LOCK_RECHECK_AFTER_SECONDS`` is checked against Windows so a missed
    unlock cannot refuse Resume forever."""

    def _watch(self, **kwargs: Any) -> tuple[SystemPauseWatch, FakeSystemRegistrar, _Clock]:
        registrar = FakeSystemRegistrar(**kwargs)
        clock = _Clock()
        watch = SystemPauseWatch(registrar, clock)
        watch.register(HWND)
        return watch, registrar, clock

    def test_locked_from_the_lock_until_the_unlock(self) -> None:
        watch, registrar, _clock = self._watch()
        assert not watch.locked and watch.lock_state() == "unlocked"
        watch.note_lock()
        assert watch.locked and watch.lock_state() == "locked"
        assert registrar.queries == 0  # a young flag is trusted without asking
        watch.note_unlock()
        assert not watch.locked and watch.lock_state() == "unlocked"

    def test_a_young_flag_is_never_cleared_by_a_query(self) -> None:
        """A query racing the lock notification itself must not reopen the
        gap: within the recheck window Windows is not asked at all."""
        watch, registrar, clock = self._watch(locked_answer=False)
        watch.note_lock()
        clock.now += system_events.LOCK_RECHECK_AFTER_SECONDS - 0.1
        assert watch.lock_state() == "locked" and registrar.queries == 0

    def test_a_missed_unlock_clears_when_windows_says_unlocked(self) -> None:
        watch, registrar, clock = self._watch(locked_answer=True)
        watch.note_lock()
        clock.now += system_events.LOCK_RECHECK_AFTER_SECONDS
        assert watch.lock_state() == "locked" and registrar.queries == 1  # still locked
        registrar.locked_answer = False  # signed back in; the unlock was missed
        assert watch.lock_state() == "unlocked" and registrar.queries == 2
        assert not watch.locked
        assert watch.lock_state() == "unlocked" and registrar.queries == 2  # no more asking

    @pytest.mark.parametrize("raises", [False, True])
    def test_an_unanswered_query_stays_refused_and_says_so(self, raises: bool) -> None:
        watch, registrar, clock = self._watch(locked_answer=None)
        watch.note_lock()
        clock.now += system_events.LOCK_RECHECK_AFTER_SECONDS
        registrar.raises = raises
        assert watch.lock_state() == "unknown"
        assert watch.locked  # kept: only an unlock or Windows' "unlocked" clears it

    def test_giving_the_registrations_back_clears_the_flag(self) -> None:
        watch, _registrar, _clock = self._watch()
        watch.note_lock()
        watch.unregister()
        assert not watch.locked and watch.lock_state() == "unlocked"

    def test_the_unlock_matches_only_while_registered(self) -> None:
        watch = SystemPauseWatch(FakeSystemRegistrar(lock_ok=False))
        watch.register(HWND)
        assert not watch.unlock_matches(WM_WTSSESSION_CHANGE, WTS_SESSION_UNLOCK)
        watch = SystemPauseWatch(FakeSystemRegistrar())
        watch.register(HWND)
        assert watch.unlock_matches(WM_WTSSESSION_CHANGE, WTS_SESSION_UNLOCK)
        assert not watch.unlock_matches(WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)
        assert not watch.unlock_matches(WM_WTSSESSION_CHANGE, WTS_SESSION_LOGON)


class TestSessionInfoQuery:
    """``WTSSessionInfoEx`` read through ctypes' own layout of
    ``WTSINFOEXW`` — only ``Level`` and ``SessionFlags``."""

    def test_the_layout_is_cs(self) -> None:
        info = system_events._WTSINFOEXW
        level1 = system_events._WTSINFOEX_LEVEL1_W
        assert info.Data.offset == 8  # the union is 8-aligned by its 64-bit times
        assert level1.SessionFlags.offset == 8
        assert ctypes.sizeof(level1) % 8 == 0

    @pytest.mark.parametrize(
        ("level", "flags", "answer"),
        [(1, 0, True), (1, 1, False), (1, -1, None), (2, 0, None)],
        ids=["locked", "unlocked", "unknown", "other-level"],
    )
    def test_the_answer(self, level: int, flags: int, answer: bool | None) -> None:
        info = system_events._WTSINFOEXW()
        info.Level = level
        info.Data.WTSInfoExLevel1.SessionFlags = flags
        size = ctypes.sizeof(info)
        assert system_events.lock_state_from_info(info, size) is answer
        assert system_events.lock_state_from_info(info, size - 1) is None  # short buffer

    def test_the_win32_query_asks_for_this_session_and_fails_closed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        wtsapi32 = _FakeDll(0)  # the call fails
        monkeypatch.setattr(system_events, "_wtsapi32", lambda: wtsapi32)
        assert Win32SystemEventRegistrar().query_locked() is None
        ((name, args),) = wtsapi32.calls
        assert name == "WTSQuerySessionInformationW"
        assert args[:3] == (
            system_events.WTS_CURRENT_SERVER_HANDLE,
            system_events.WTS_CURRENT_SESSION,
            system_events.WTS_SESSION_INFO_EX,
        )
        answered = _FakeDll(1)  # "succeeds" but hands back no buffer
        monkeypatch.setattr(system_events, "_wtsapi32", lambda: answered)
        assert Win32SystemEventRegistrar().query_locked() is None
        assert [name for name, _ in answered.calls] == ["WTSQuerySessionInformationW"]


# --- the main window --------------------------------------------------------------


class TestLockWindow:
    """The main window: registered only by ``attach_system_pause``; a lock
    queued out of ``nativeEvent`` pauses through ``pause_for``; an unlock
    and every other state change nothing."""

    def test_a_window_registers_nothing_and_ignores_a_lock_until_attached(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """The control for every lock test below: without the registration,
        the same lock message pauses nothing."""
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        assert window.system_pause_status == NOT_SET_UP
        _recording(controller)
        assert _send(window, WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK) == (False, 0)
        qapp.processEvents()
        assert _pauses(controller) == 0
        registrar = FakeSystemRegistrar()
        assert window.attach_system_pause(registrar).failed == ()
        hwnd = int(window.winId())
        assert registrar.calls == [("register_suspend", hwnd), ("register_lock", hwnd)]
        window.deleteLater()

    def test_a_lock_pauses_a_recording_with_the_cue_and_unlock_does_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        window.attach_system_pause(FakeSystemRegistrar())
        _recording(controller)
        assert _send(window, WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK) == (False, 0)
        assert _pauses(controller) == 0  # queued, never run inside the native dispatch
        qapp.processEvents()
        assert _pauses(controller) == 1
        assert controller.state_value is SessionState.PAUSED
        cue = models.pause_cue_text("locked", linked=False)
        assert window.statusBar().currentMessage() == cue
        assert window.session_screen.message_label.text() == cue
        assert _send(window, WM_WTSSESSION_CHANGE, WTS_SESSION_UNLOCK) == (False, 0)
        qapp.processEvents()
        assert ("resume",) not in controller.calls  # Resume stays a deliberate press
        assert controller.state_value is SessionState.PAUSED
        window.deleteLater()

    @pytest.mark.parametrize(
        "state",
        [SessionState.PAUSED, SessionState.IDLE, SessionState.PROCESSING, SessionState.QUEUED],
    )
    def test_a_lock_otherwise_changes_nothing(
        self, qapp: Any, tmp_path: Path, state: SessionState
    ) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        window.attach_system_pause(FakeSystemRegistrar())
        _recording(controller)
        controller.state_value = state
        _send(window, WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)
        qapp.processEvents()
        assert _pauses(controller) == 0 and ("resume",) not in controller.calls
        assert window.statusBar().currentMessage() == ""
        window.deleteLater()

    def test_both_suspend_routes_and_a_lock_make_one_pause(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The classic broadcast and the registered notification are the same
        ``PBT_APMSUSPEND``; if both arrive, and a lock follows (standby locks
        first), the recording is paused once with one cue."""
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        window.attach_system_pause(FakeSystemRegistrar())
        _recording(controller)
        cues: list[str] = []
        monkeypatch.setattr(window.session_screen, "show_notice", cues.append)
        _send(window, WM_POWERBROADCAST, PBT_APMSUSPEND)
        _send(window, WM_POWERBROADCAST, PBT_APMSUSPEND)
        _send(window, WM_POWERBROADCAST, PBT_APMRESUMEAUTOMATIC)  # waking resumes nothing
        _send(window, WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)
        qapp.processEvents()
        assert _pauses(controller) == 1
        assert ("resume",) not in controller.calls
        assert cues == [models.pause_cue_text("suspend", linked=False)]
        window.deleteLater()

    @pytest.mark.parametrize("detach", [False, True])
    def test_a_lock_queued_before_detach_is_dropped(
        self, qapp: Any, tmp_path: Path, detach: bool
    ) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        window.attach_system_pause(FakeSystemRegistrar())
        _recording(controller)
        _send(window, WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)  # queued: not yet delivered
        if detach:
            window.detach_system_pause()
        qapp.processEvents()
        assert _pauses(controller) == (0 if detach else 1)
        window.deleteLater()

    def test_close_gives_both_back_once(self, qapp: Any, tmp_path: Path) -> None:
        from PySide6.QtGui import QCloseEvent

        window = _main_window(tmp_path, FakeController())
        registrar = FakeSystemRegistrar()
        window.attach_system_pause(registrar)
        event = QCloseEvent()
        window.closeEvent(event)
        assert event.isAccepted()
        hwnd = int(window.winId())
        assert registrar.calls[2:] == [
            ("unregister_suspend", SUSPEND_HANDLE),
            ("unregister_lock", hwnd),
        ]
        window.detach_system_pause()  # at quit too: idempotent
        assert len(registrar.calls) == 4
        assert window.system_pause_status == NOT_SET_UP
        window.deleteLater()

    def test_a_refusal_is_shown_on_the_desktop(self, qapp: Any, tmp_path: Path) -> None:
        window = _main_window(tmp_path, FakeController())
        bridge = window.attach_chrome_link()
        bridge.set_unavailable()  # a link state, so the Session screen shows its lines
        status = window.attach_system_pause(FakeSystemRegistrar(suspend_handle=0, lock_ok=False))
        assert status.failed == ("suspend", "lock")
        assert window.statusBar().currentMessage() == models.SYSTEM_PAUSE_FAILED_LINES["suspend"]
        label = window.session_screen.chrome_label.text()
        for line in models.SYSTEM_PAUSE_FAILED_LINES.values():
            assert line in label
        window.detach_system_pause()
        label = window.session_screen.chrome_label.text()
        assert not any(line in label for line in models.SYSTEM_PAUSE_FAILED_LINES.values())
        bridge.deleteLater()
        window.deleteLater()

    def test_an_accepted_registration_shows_no_line_and_a_later_bridge_gets_it(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _main_window(tmp_path, FakeController())
        window.attach_system_pause(FakeSystemRegistrar(lock_ok=False))
        bridge = window.attach_chrome_link()
        bridge.set_unavailable()
        label = window.session_screen.chrome_label.text()
        assert models.SYSTEM_PAUSE_FAILED_LINES["lock"] in label
        assert models.SYSTEM_PAUSE_FAILED_LINES["suspend"] not in label
        assert "lock" not in bridge.build_content()  # shown on the desktop only
        bridge.deleteLater()
        window.deleteLater()

    # --- locked until unlock (codex round 51 PR-MED-300) ------------------------

    def _locked_window(
        self, qapp: Any, tmp_path: Path, clock: _Clock | None = None, **kwargs: Any
    ) -> tuple[Any, Any, Any]:
        """A window with the Chrome bridge and a FAKE registration, an
        unlinked recording, and a lock message sent (not yet processed)."""
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        bridge = window.attach_chrome_link()
        window.attach_system_pause(FakeSystemRegistrar(**kwargs))
        if clock is not None:
            window._system_events._clock = clock  # the lock's age, under test control
        _recording(controller)
        _send(window, WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)
        return window, bridge, controller

    def test_the_lock_refuses_resume_before_the_queued_pause_runs(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """The flag is set while the lock message is dispatched: a command
        handled before the queued pause already meets the refusal."""
        window, bridge, controller = self._locked_window(qapp, tmp_path)
        assert window.session_locked
        assert _pauses(controller) == 0  # the pause is still queued
        assert bridge.resume_refusal() == "locked"
        qapp.processEvents()
        assert _pauses(controller) == 1
        bridge.deleteLater()
        window.deleteLater()

    def test_every_desktop_resume_path_is_refused_while_locked(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """An UNLINKED recording too: the Resume button's slot and the
        hotkey both meet the lock refusal, and nothing reaches the
        controller."""
        window, bridge, controller = self._locked_window(qapp, tmp_path)
        qapp.processEvents()  # paused by the lock
        locked = models.CHROME_REFUSALS["locked"]
        assert window.session_screen.on_resume() is False
        assert window.session_screen.message_label.text() == locked
        window.on_hotkey()
        assert window.statusBar().currentMessage() == locked
        assert ("resume",) not in controller.calls
        bridge.deleteLater()
        window.deleteLater()

    def test_the_unlock_clears_the_refusal_and_resumes_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window, bridge, controller = self._locked_window(qapp, tmp_path)
        qapp.processEvents()
        assert _send(window, WM_WTSSESSION_CHANGE, WTS_SESSION_UNLOCK) == (False, 0)
        qapp.processEvents()
        assert not window.session_locked
        assert ("resume",) not in controller.calls  # unlocking resumed nothing
        assert bridge.resume_refusal() is None
        assert window.session_screen.on_resume() is True  # the deliberate press works
        bridge.deleteLater()
        window.deleteLater()

    def test_a_missed_unlock_does_not_refuse_resume_forever(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        clock = _Clock()
        window, bridge, _controller = self._locked_window(
            qapp, tmp_path, clock, locked_answer=False
        )
        qapp.processEvents()
        assert window.session_screen.on_resume() is False  # young flag: refused
        clock.now += system_events.LOCK_RECHECK_AFTER_SECONDS
        assert window.session_screen.on_resume() is True  # Windows says unlocked
        assert not window.session_locked
        bridge.deleteLater()
        window.deleteLater()

    def test_an_unconfirmed_lock_is_refused_by_name(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        clock = _Clock()
        window, bridge, controller = self._locked_window(
            qapp, tmp_path, clock, locked_answer=None
        )
        qapp.processEvents()
        clock.now += system_events.LOCK_RECHECK_AFTER_SECONDS
        assert window.session_screen.on_resume() is False
        assert window.session_screen.message_label.text() == models.CHROME_REFUSALS[
            "lock_unknown"
        ]
        assert ("resume",) not in controller.calls
        bridge.deleteLater()
        window.deleteLater()

    def test_a_refused_lock_registration_never_sets_the_flag(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """The named residue: with the lock registration refused, no lock is
        seen, so nothing is refused (and nothing paused by a lock)."""
        window, bridge, controller = self._locked_window(qapp, tmp_path, lock_ok=False)
        qapp.processEvents()
        assert not window.session_locked
        assert bridge.resume_refusal() is None and _pauses(controller) == 0
        bridge.deleteLater()
        window.deleteLater()

    # --- a voice enrolment (round 57 SEC-019, practitioner decision 2026-09-28) ---

    def test_a_lock_and_a_suspend_each_stop_a_voice_enrolment(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Both go through the Practitioner tab's own Stop — the path whose
        worker checks save nothing (``test_ui_screens``' Stop tests)."""
        window = _main_window(tmp_path, FakeController())
        stops: list[int] = []
        monkeypatch.setattr(window.practitioner_screen, "on_stop", lambda: stops.append(1))
        _send(window, WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)  # not registered yet
        qapp.processEvents()
        assert stops == []
        window.attach_system_pause(FakeSystemRegistrar())
        _send(window, WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)
        assert stops == []  # queued with the lock's pause
        qapp.processEvents()
        assert stops == [1]
        _send(window, WM_POWERBROADCAST, PBT_APMSUSPEND)
        assert stops == [1, 1]  # synchronously, with the suspend's pause
        window.deleteLater()

    def test_a_record_press_is_refused_while_locked(self, qapp: Any, tmp_path: Path) -> None:
        """``begin_enrolment``'s blocker meets the lock like a Resume does:
        from the lock message until the unlock."""
        window = _main_window(tmp_path, FakeController())
        assert window._enrolment_blocker() is None
        window.attach_system_pause(FakeSystemRegistrar())
        _send(window, WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK)
        assert window._enrolment_blocker() == models.CHROME_REFUSALS["locked"]
        qapp.processEvents()
        _send(window, WM_WTSSESSION_CHANGE, WTS_SESSION_UNLOCK)
        assert window._enrolment_blocker() is None
        window.deleteLater()

    def test_the_override_never_raises_into_qt(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = _main_window(tmp_path, FakeController())
        window.attach_system_pause(FakeSystemRegistrar())

        def broken(*_args: object) -> bool:
            raise RuntimeError("boom")

        monkeypatch.setattr(window._system_events, "lock_matches", broken)
        assert _send(window, WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK) == (False, 0)
        window.deleteLater()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows messages")
    @pytest.mark.skipif(
        os.environ.get("SCRIBE_SKIP_INTEGRATION") == "1",
        reason="integration explicitly skipped via SCRIBE_SKIP_INTEGRATION=1",
    )
    def test_a_real_lock_message_through_qts_dispatch(self, tmp_path: Path) -> None:
        """Synthetic ``WM_WTSSESSION_CHANGE`` messages — SENT into the window
        procedure, then POSTED through Qt's event dispatcher — reach a native
        (never shown) window registered through a FAKE registrar; no real
        notification is ever registered. Before the registration a lock is
        ignored; after it a lock pauses and sets the lock flag during its
        own dispatch, and an unlock only clears the flag; a posted
        ``PBT_APMSUSPEND`` (what the registered suspend notification
        delivers) still pauses. This proves Qt hands the messages to the
        override — NOT that Windows sends them on this machine (the live
        smoke is that proof)."""
        env = dict(os.environ)
        env["QT_QPA_PLATFORM"] = "windows"
        child = subprocess.run(
            [sys.executable, "-c", _LOCK_DISPATCH_CHILD, str(tmp_path)],
            capture_output=True,
            env=env,
            timeout=120,
            check=False,
        )
        assert child.returncode == 0, child.stderr.decode(errors="replace")
        lines = child.stdout.decode().splitlines()
        assert lines[-4:] == [
            "UNREGISTERED []",
            "FLAGS [true, false]",  # set by the lock's dispatch, cleared by the unlock
            'SENT ["locked"]',
            'SEEN ["locked", "locked", "suspend"]',
        ]
        for marker in (b"Traceback", b"TypeError", b"ValueError", b"wrong argument"):
            assert marker not in child.stderr, child.stderr.decode(errors="replace")


_LOCK_DISPATCH_CHILD = """\
import ctypes, json, sys
from pathlib import Path
from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
apply_offline_env()
assert_offline_env()
from PySide6.QtWidgets import QApplication
from scribe_desktop.audio_capture import MockCaptureBackend
from scribe_desktop.clinics import ClinicRegistry
from scribe_desktop.session import SessionController
from scribe_desktop.ui.main_window import MainWindow
class FakeSystemRegistrar:
    def register_suspend(self, hwnd):
        return 1
    def unregister_suspend(self, handle):
        pass
    def register_lock(self, hwnd):
        return True
    def unregister_lock(self, hwnd):
        pass
app = QApplication([])
base = Path(sys.argv[1])
root = base / 'sessions'
backend = MockCaptureBackend()
controller = SessionController(backend, sessions_root=root)
w = MainWindow(controller, backend, sessions_root=root,
               profile_root=base / 'profile', config_root=base / 'config',
               style_root=base / 'style', language_model_available=lambda: False,
               clinic_registry=ClinicRegistry(base / 'clinics.json'))
seen = []
w.pause_for = lambda reason: seen.append(str(reason))
hwnd = int(w.winId())
user32 = ctypes.WinDLL('user32')
user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t,
                                ctypes.c_ssize_t]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t,
                                ctypes.c_ssize_t]
user32.PostMessageW.restype = ctypes.c_int
# Not registered yet: a lock is not this window's.
user32.SendMessageW(hwnd, 0x02B1, 0x7, 1)
app.processEvents()
print('UNREGISTERED ' + json.dumps(seen), flush=True)
status = w.attach_system_pause(FakeSystemRegistrar())
assert (status.suspend, status.lock) == ('on', 'on')
user32.SendMessageW(hwnd, 0x02B1, 0x7, 1)
flags = [w.session_locked]
user32.SendMessageW(hwnd, 0x02B1, 0x8, 1)
flags.append(w.session_locked)
app.processEvents()
print('FLAGS ' + json.dumps(flags), flush=True)
print('SENT ' + json.dumps(seen), flush=True)
assert user32.PostMessageW(hwnd, 0x02B1, 0x7, 1)
assert user32.PostMessageW(hwnd, 0x02B1, 0x8, 1)
for _ in range(5):
    app.processEvents()
assert user32.PostMessageW(hwnd, 0x0218, 0x0004, 0)
for _ in range(5):
    app.processEvents()
w.detach_system_pause()
print('SEEN ' + json.dumps(seen), flush=True)
"""
