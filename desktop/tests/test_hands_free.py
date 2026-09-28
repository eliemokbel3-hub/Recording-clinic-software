"""Cliniko workflow safeguards plan Phase 7 (D7, D8): the global hotkey, the
spoken pause and the new-consultation warning. Offscreen; every hotkey
registration goes through a FAKE registrar — no test reserves a real chord
on the host — and the phrase rules read hand-built live windows (no model).
One test sends and posts a synthetic ``WM_HOTKEY`` through Qt's real Windows
dispatch in a child process, as the suspend test does with its broadcast."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from scribe_desktop import hotkey as hotkey_module  # noqa: E402
from scribe_desktop.context_rules import PauseReason  # noqa: E402
from scribe_desktop.encounter import unlinked_consent  # noqa: E402
from scribe_desktop.hotkey import (  # noqa: E402
    CHORD_TEXT,
    ERROR_HOTKEY_ALREADY_REGISTERED,
    HOTKEY_ID,
    MODIFIERS,
    VIRTUAL_KEY,
    WM_HOTKEY,
    GlobalHotkey,
    is_hotkey_message,
)
from scribe_desktop.session import RecordingSession, SessionState  # noqa: E402
from scribe_desktop.transcription import (  # noqa: E402
    LiveFailure,
    LiveFailureKind,
    TranscriptSegment,
    TranscriptWord,
)
from scribe_desktop.ui import models  # noqa: E402
from scribe_desktop.voice_commands import (  # noqa: E402
    CARRY_MAX_GAP_SECONDS,
    CLOSING_PHRASES,
    GREETING_PHRASES,
    NEW_CONSULTATION_WARNING,
    NEW_CONSULTATION_WINDOWS,
    RESUME_CUTOFF_MARGIN_SECONDS,
    SPOKEN_PAUSE_PHRASE,
    NewConsultationWatcher,
    SpokenPauseDetector,
    phrase_tokens,
    spoken_pause_state,
)
from test_system_pause import SUSPEND_HANDLE, FakeSystemRegistrar  # noqa: E402
from test_ui_screens import FakeController, _main_window  # noqa: E402


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _say(text: str, start: float, step: float = 0.4) -> TranscriptSegment:
    """One live segment: ``text``'s words, the first starting at ``start``."""
    words = tuple(
        TranscriptWord(
            word_text=word,
            start_seconds=start + i * step,
            end_seconds=start + i * step + 0.3,
            probability=0.9,
            uncertain=False,
        )
        for i, word in enumerate(text.split())
    )
    return TranscriptSegment(
        start_seconds=start,
        end_seconds=start + len(words) * step,
        speaker="pending",
        transcript_words=words,
    )


def _window(*parts: tuple[str, float]) -> tuple[TranscriptSegment, ...]:
    return tuple(_say(text, start) for text, start in parts)


def _open_live_view(window: Any) -> Any:
    """What a Start does (round 57 SEC-022): build the worker's poster, then
    open the live view, which adopts its token. Returns the poster."""
    post = window.transcript_screen.live_poster()
    window.transcript_screen.begin_live_view()
    return post


class FakeRegistrar:
    """``HotkeyRegistrar`` that records calls and never touches Windows."""

    def __init__(self, error: int = 0, raises: bool = False) -> None:
        self.error = error
        self.raises = raises
        self.registered: list[tuple[int, int, int, int]] = []
        self.unregistered: list[tuple[int, int]] = []

    def register(self, hwnd: int, hotkey_id: int, modifiers: int, virtual_key: int) -> int:
        self.registered.append((hwnd, hotkey_id, modifiers, virtual_key))
        if self.raises:
            raise OSError("boom")
        return self.error

    def unregister(self, hwnd: int, hotkey_id: int) -> None:
        self.unregistered.append((hwnd, hotkey_id))


# --- Task 7.1: the hotkey module ------------------------------------------------


class TestHotkeyModule:
    def test_the_chord_is_ctrl_shift_f9_without_alt_or_win(self) -> None:
        """D7: AltGr-safe — Ctrl+Alt is AltGr on European layouts."""
        mod_alt, mod_win = 0x0001, 0x0008
        assert MODIFIERS & mod_alt == 0 and MODIFIERS & mod_win == 0
        assert MODIFIERS == hotkey_module.MOD_CONTROL | hotkey_module.MOD_SHIFT | 0x4000
        assert VIRTUAL_KEY == 0x78  # F9
        assert CHORD_TEXT == "Ctrl+Shift+F9"
        assert 0 <= HOTKEY_ID < 0xC000  # an application's id range
        assert WM_HOTKEY == 0x0312

    def test_a_registration_reserves_the_chord_once(self) -> None:
        registrar = FakeRegistrar()
        hotkey = GlobalHotkey(registrar)
        status = hotkey.register(4242)
        assert status.state == "on" and status.available and status.chord == CHORD_TEXT
        assert registrar.registered == [(4242, HOTKEY_ID, MODIFIERS, VIRTUAL_KEY)]
        assert hotkey.register(4242) is status  # nothing reserved twice
        assert len(registrar.registered) == 1
        assert hotkey.matches(WM_HOTKEY, HOTKEY_ID)
        assert not hotkey.matches(WM_HOTKEY, HOTKEY_ID + 1)
        assert not hotkey.matches(0x0218, HOTKEY_ID)

    @pytest.mark.parametrize(
        "registrar, error",
        [
            (FakeRegistrar(error=ERROR_HOTKEY_ALREADY_REGISTERED), 1409),
            (FakeRegistrar(raises=True), -1),
        ],
    )
    def test_a_refused_registration_is_a_status(self, registrar: Any, error: int) -> None:
        hotkey = GlobalHotkey(registrar)
        status = hotkey.register(4242)
        assert status.state == "failed" and not status.available and status.error == error
        assert not hotkey.matches(WM_HOTKEY, HOTKEY_ID)  # a press cannot arrive
        hotkey.unregister()
        assert registrar.unregistered == []  # nothing was reserved

    def test_unregister_gives_the_chord_back_once(self) -> None:
        registrar = FakeRegistrar()
        hotkey = GlobalHotkey(registrar)
        hotkey.register(7)
        hotkey.unregister()
        hotkey.unregister()
        assert registrar.unregistered == [(7, HOTKEY_ID)]
        assert hotkey.status.state == "not_set_up"
        assert not hotkey.matches(WM_HOTKEY, HOTKEY_ID)

    def test_a_failing_unregister_never_raises(self) -> None:
        registrar = FakeRegistrar()

        def broken(_hwnd: int, _id: int) -> None:
            raise OSError("gone")

        registrar.unregister = broken  # type: ignore[method-assign]
        hotkey = GlobalHotkey(registrar)
        hotkey.register(7)
        hotkey.unregister()
        assert hotkey.status.state == "not_set_up"

    def test_the_message_test(self) -> None:
        assert is_hotkey_message(WM_HOTKEY, HOTKEY_ID)
        assert not is_hotkey_message(WM_HOTKEY, 0)
        assert not is_hotkey_message(0x0000, HOTKEY_ID)


# --- Task 7.2: the spoken pause ---------------------------------------------------


class TestNormalise:
    @pytest.mark.parametrize(
        "text, tokens",
        [
            ("Scribe, pause.", ["scribe", "pause"]),
            ("prescribe, pause", ["prescribe", "pause"]),
            ("SCRIBE-PAUSE", ["scribe", "pause"]),
            ("'scribe'", ["scribe"]),
            ("Don't", ["don't"]),
            ("  ", []),
        ],
    )
    def test_tokens_are_whole_words(self, text: str, tokens: list[str]) -> None:
        assert phrase_tokens(text) == tokens

    def test_each_part_goes_through_the_one_normaliser(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Task 1.2's pin (`test_note.py`): no second normaliser in src/ —
        the phrase rules call ``note.normalise_token`` for every part."""
        from scribe_desktop import voice_commands

        seen: list[str] = []

        def spy(token: str) -> str:
            seen.append(token)
            return token.lower()

        monkeypatch.setattr(voice_commands, "normalise_token", spy)
        assert phrase_tokens("Scribe-pause now") == ["scribe", "pause", "now"]
        assert seen == ["Scribe", "pause", "now"]

    def test_the_phrase(self) -> None:
        assert SPOKEN_PAUSE_PHRASE == ("scribe", "pause")
        assert RESUME_CUTOFF_MARGIN_SECONDS == 1.0  # one capture chunk


class TestSpokenPauseMatcher:
    @pytest.mark.parametrize(
        "text",
        [
            "scribe pause",
            "Scribe, pause.",
            "okay scribe pause now",
            "SCRIBE PAUSE",
            "scribe-pause",
            "right. Scribe pause, please",
        ],
    )
    def test_the_phrase_pauses(self, text: str) -> None:
        assert SpokenPauseDetector().feed(_window((text, 3.0)))

    @pytest.mark.parametrize(
        "text",
        [
            "prescribe, pause",
            "prescribe pause",
            "describe pause",
            "scribe paused",
            "scribe pauses",
            "scribes pause",
            "the scribe will pause",
            "pause scribe",
            "scribe",
            "pause",
            "",
        ],
    )
    def test_near_misses_do_not(self, text: str) -> None:
        segments = _window((text, 3.0)) if text else ()
        assert not SpokenPauseDetector().feed(segments)

    def test_a_phrase_before_the_last_resume_is_ignored(self) -> None:
        detector = SpokenPauseDetector()
        detector.note_resume(10.0)
        assert detector.cutoff_seconds == 11.0
        assert not detector.feed(_window(("scribe pause", 10.9)))
        assert detector.feed(_window(("scribe pause", 11.0)))

    def test_a_mixed_window_is_judged_by_the_phrases_first_word(self) -> None:
        """D7 (peer r2 PR-MED-003): one window can span a Pause and a Resume
        — its end time is never the test."""
        detector = SpokenPauseDetector()
        detector.note_resume(8.0)  # cutoff 9.0
        before = _window(("scribe pause", 5.0), ("carry on then", 9.5))
        assert not detector.feed(before)  # the window ends after the cutoff
        after = _window(("that was it", 5.0), ("scribe pause", 9.5))
        assert detector.feed(after)

    def test_a_phrase_split_across_two_windows(self) -> None:
        detector = SpokenPauseDetector()
        assert not detector.feed(_window(("okay then scribe", 20.0)))
        assert detector.feed(_window(("pause", 21.5)))
        late = SpokenPauseDetector()
        assert not late.feed(_window(("okay then scribe", 20.0)))
        late.note_resume(21.0)  # a Resume between the two windows drops the carry
        assert not late.feed(_window(("pause", 22.5)))

    def test_a_silence_between_windows_breaks_the_phrase(self) -> None:
        """Round 41 LOW-033: "…the scribe" then, after a silence that
        closed the window, "Pause here" is two sentences, not the phrase."""
        assert CARRY_MAX_GAP_SECONDS == 3.0  # the window-closing silence
        apart = SpokenPauseDetector()
        assert not apart.feed(_window(("ask the scribe", 20.0)))  # "scribe" at 20.8
        assert not apart.feed(_window(("Pause here", 23.9)))  # 3.1 s later
        close = SpokenPauseDetector()
        assert not close.feed(_window(("ask the scribe", 20.0)))
        assert close.feed(_window(("pause", 23.5)))  # 2.7 s later

    def test_the_cutoff_never_moves_back_and_reset_clears_it(self) -> None:
        detector = SpokenPauseDetector()
        detector.note_resume(30.0)
        detector.note_resume(5.0)
        assert detector.cutoff_seconds == 31.0
        detector.reset()
        assert detector.cutoff_seconds == 0.0
        assert detector.feed(_window(("scribe pause", 0.5)))


class TestSpokenPauseState:
    @pytest.mark.parametrize("state", list(SessionState))
    def test_available_only_while_recording_with_a_running_transcriber(
        self, state: SessionState
    ) -> None:
        live = state in (SessionState.RECORDING, SessionState.PAUSED)
        failure = LiveFailure(LiveFailureKind.WORKER_ERROR, "x")
        assert spoken_pause_state(state, attached=True, failure=None) == (
            "on" if live else "idle"
        )
        assert spoken_pause_state(state, attached=False, failure=None) == (
            "unavailable" if live else "idle"
        )
        assert spoken_pause_state(state, attached=True, failure=failure) == (
            "unavailable" if live else "idle"
        )


# --- Task 7.3: the new-consultation warning ---------------------------------------


class TestNewConsultationRule:
    def test_the_lists_and_the_window_budget_are_pinned(self) -> None:
        assert NEW_CONSULTATION_WARNING == "new_consultation"
        assert NEW_CONSULTATION_WINDOWS == 3
        assert CLOSING_PHRASES == (
            "see you next week",
            "see you next time",
            "see you soon",
            "see you then",
            "take care",
            "all the best",
            "goodbye",
            "bye",
            "thanks for coming in",
            "thank you for coming in",
            "have a good day",
            "have a nice day",
            "have a great day",
            "have a good weekend",
        )
        assert GREETING_PHRASES == (
            "hello",
            "hi there",
            "good morning",
            "good afternoon",
            "good evening",
            "nice to meet you",
            "come on in",
            "take a seat",
            "have a seat",
            "what brings you in",
            "what brings you here",
            "how have you been",
        )

    def test_a_goodbye_then_a_greeting_warns_once(self) -> None:
        watcher = NewConsultationWatcher()
        assert watcher.feed(_window(("Great, see you next week.", 1.0), ("Good morning!", 9.0)))
        assert watcher.raised
        assert not watcher.feed(_window(("bye", 20.0), ("hello", 25.0)))  # once per recording
        watcher.reset()
        assert not watcher.raised
        assert watcher.feed(_window(("bye", 30.0), ("hello", 35.0)))

    @pytest.mark.parametrize("gap, warns", [(0, True), (1, True), (3, True), (4, False)])
    def test_the_greeting_must_follow_within_the_window_budget(
        self, gap: int, warns: bool
    ) -> None:
        watcher = NewConsultationWatcher()
        assert not watcher.feed(_window(("Take care.", 1.0)))
        for i in range(gap - 1):
            assert not watcher.feed(_window(("mm", 10.0 + i)))
        if gap == 0:
            watcher = NewConsultationWatcher()
            assert watcher.feed(_window(("Take care. Hello", 1.0)))
            return
        assert watcher.feed(_window(("Hi there, come on in", 50.0))) is warns

    @pytest.mark.parametrize(
        "parts",
        [
            [("hello, how is the knee", 1.0)],  # a greeting alone
            [("see you next week", 1.0)],  # a closing alone
            [("hello there. Take care", 1.0)],  # the greeting came FIRST
            [("I'd take the care plan", 1.0), ("hello", 5.0)],  # not the phrase
            [("goodbyes are hard", 1.0), ("good morning", 5.0)],  # not a whole word
        ],
    )
    def test_near_misses_do_not_warn(self, parts: list[tuple[str, float]]) -> None:
        watcher = NewConsultationWatcher()
        assert not any(watcher.feed(_window(part)) for part in parts)


# --- the main window's wiring ---------------------------------------------------------


_SESSION_ACTIONS = frozenset({"start", "pause", "resume", "finish", "discard"})


def _actions(controller: FakeController) -> list[tuple[Any, ...]]:
    """The session controls called (a window's construction registers its
    blocker and live factory on the controller too)."""
    return [call for call in controller.calls if call[0] in _SESSION_ACTIONS]


def _recording(controller: FakeController) -> RecordingSession:
    session = RecordingSession(consent=unlinked_consent()).with_state(SessionState.RECORDING)
    controller.session_value = session
    controller.state_value = SessionState.RECORDING
    return session


class TestHotkeyWindow:
    """Task 7.1 in the main window: reserved only by ``attach_hotkey``, a
    press queued out of ``nativeEvent``, pause through ``pause_for``,
    resume through the Session screen's guard."""

    def _msg(self, message: int, wparam: int) -> tuple[Any, int]:
        from scribe_desktop.ui.main_window import _MSG

        msg = _MSG(None, message, wparam)
        return msg, ctypes.addressof(msg)

    def test_a_window_reserves_nothing_until_attached(self, qapp: Any, tmp_path: Path) -> None:
        window = _main_window(tmp_path, FakeController())
        assert window.hotkey_status.state == "not_set_up"
        registrar = FakeRegistrar()
        status = window.attach_hotkey(registrar)
        assert status.state == "on"
        assert registrar.registered == [(int(window.winId()), HOTKEY_ID, MODIFIERS, VIRTUAL_KEY)]
        window.deleteLater()

    def test_a_refusal_is_shown_on_the_desktop_and_reaches_the_bridge(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _main_window(tmp_path, FakeController())
        bridge = window.attach_chrome_link()
        bridge.set_unavailable()  # a link state, so the Session screen shows its lines
        window.attach_hotkey(FakeRegistrar(error=ERROR_HOTKEY_ALREADY_REGISTERED))
        assert window.statusBar().currentMessage() == models.HOTKEY_FAILED_STATUS.format(
            chord=CHORD_TEXT
        )
        assert bridge.build_content()["hotkey"] == {"available": False}
        assert "Pause hotkey unavailable" in window.session_screen.chrome_label.text()
        bridge.deleteLater()
        window.deleteLater()

    def test_a_bridge_attached_later_gets_the_status(self, qapp: Any, tmp_path: Path) -> None:
        window = _main_window(tmp_path, FakeController())
        window.attach_hotkey(FakeRegistrar())
        bridge = window.attach_chrome_link()
        assert bridge.build_content()["hotkey"] == {"available": True, "chord": CHORD_TEXT}
        bridge.deleteLater()
        window.deleteLater()

    def test_wm_hotkey_is_queued_only_for_the_reserved_chord(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = _main_window(tmp_path, FakeController())
        pressed: list[int] = []
        monkeypatch.setattr(window, "on_hotkey", lambda: pressed.append(1))
        keep, address = self._msg(WM_HOTKEY, HOTKEY_ID)
        assert window.nativeEvent(b"windows_generic_MSG", address) == (False, 0)
        qapp.processEvents()
        assert pressed == []  # not reserved: nothing
        window.attach_hotkey(FakeRegistrar())
        other, other_address = self._msg(WM_HOTKEY, HOTKEY_ID + 1)
        assert window.nativeEvent(b"windows_generic_MSG", other_address) == (False, 0)
        assert window.nativeEvent(b"windows_generic_MSG", address) == (False, 0)
        assert pressed == []  # queued, never run inside the native dispatch
        qapp.processEvents()
        assert pressed == [1]
        assert keep is not None and other is not None
        window.deleteLater()

    def test_a_press_while_recording_pauses_with_the_cue(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        _recording(controller)
        window.on_hotkey()
        assert _actions(controller) == [("pause",)]
        cue = models.pause_cue_text("hotkey", linked=False)
        assert window.statusBar().currentMessage() == cue
        assert window.session_screen.message_label.text() == cue
        window.deleteLater()

    def test_a_press_while_paused_resumes_through_the_guard(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        _recording(controller)
        controller.state_value = SessionState.PAUSED
        refusal = "Open this recording's own treatment note in Cliniko to resume it."
        window.session_screen.set_resume_guard(lambda: refusal)
        window.on_hotkey()
        assert ("resume",) not in controller.calls  # no bypass (Constraint 7)
        assert window.statusBar().currentMessage() == refusal
        window.session_screen.set_resume_guard(lambda: None)
        window.on_hotkey()
        assert ("resume",) in controller.calls
        assert window.statusBar().currentMessage() == models.HOTKEY_RESUMED_STATUS
        window.deleteLater()

    @pytest.mark.parametrize(
        "state",
        [SessionState.IDLE, SessionState.PROCESSING, SessionState.QUEUED, SessionState.FAILED],
    )
    def test_a_press_otherwise_does_nothing(
        self, qapp: Any, tmp_path: Path, state: SessionState
    ) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        controller.state_value = state
        window.on_hotkey()
        assert _actions(controller) == []
        window.deleteLater()

    def test_close_gives_the_chord_back(self, qapp: Any, tmp_path: Path) -> None:
        from PySide6.QtGui import QCloseEvent

        window = _main_window(tmp_path, FakeController())
        registrar = FakeRegistrar()
        window.attach_hotkey(registrar)
        event = QCloseEvent()
        window.closeEvent(event)
        assert event.isAccepted()
        assert registrar.unregistered == [(int(window.winId()), HOTKEY_ID)]
        window.detach_hotkey()  # at quit too: idempotent
        assert len(registrar.unregistered) == 1
        window.deleteLater()

    def test_a_start_up_failure_after_attach_gives_the_chord_back(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 42 PR-LOW-240: ``app.main`` reserves the chord, then start-up
        fails before the event loop runs (``show`` raises here) — its
        ``finally`` gives the chord back, exactly once."""
        import logging

        from PySide6.QtWidgets import QApplication

        from scribe_desktop import app as app_module

        controller = FakeController()
        window = _main_window(tmp_path, controller)
        registrar = FakeRegistrar()
        attach = window.attach_hotkey
        monkeypatch.setattr(window, "attach_hotkey", lambda: attach(registrar))
        # D5 as amended 2026-09-28: main() also registers the suspend and
        # lock notifications — through a fake here, never Windows.
        system_registrar = FakeSystemRegistrar()
        attach_system = window.attach_system_pause
        monkeypatch.setattr(
            window, "attach_system_pause", lambda: attach_system(system_registrar)
        )

        def fail_show() -> None:
            raise RuntimeError("start-up failed")

        monkeypatch.setattr(window, "show", fail_show)
        for name, value in {
            "setup_logging": lambda name: logging.getLogger("test-hands-free"),
            "apply_offline_env": lambda: None,
            "assert_offline_env": lambda: None,
            "QApplication": lambda argv: QApplication.instance() or QApplication(argv),
            "acquire_instance_exclusion": lambda name=None, lock_path=None: (
                app_module.InstanceExclusion("acquired")
            ),
            "SoundDeviceBackend": lambda: object(),
            "SessionController": lambda *args, **kwargs: controller,
            "default_sessions_root": lambda: tmp_path / "sessions",
            "sweep_protected_ids": lambda *args: frozenset(),
            "sweep_sessions": lambda *args, **kwargs: None,
            "MainWindow": lambda *args, **kwargs: window,
            "_start_chrome_link": lambda *args: None,
        }.items():
            monkeypatch.setattr(app_module, name, value)
        with pytest.raises(RuntimeError, match="start-up failed"):
            app_module.main()
        qapp.aboutToQuit.disconnect(window.detach_hotkey)  # main() wired the shared app
        qapp.aboutToQuit.disconnect(window.detach_system_pause)
        assert len(registrar.registered) == 1
        assert registrar.unregistered == [(int(window.winId()), HOTKEY_ID)]
        hwnd = int(window.winId())
        assert system_registrar.calls == [
            ("register_suspend", hwnd),
            ("register_lock", hwnd),
            ("unregister_suspend", SUSPEND_HANDLE),
            ("unregister_lock", hwnd),
        ]
        window.deleteLater()

    @pytest.mark.parametrize("detach", [False, True])
    def test_a_press_queued_before_detach_is_dropped(
        self, qapp: Any, tmp_path: Path, detach: bool
    ) -> None:
        """Round 42 PR-LOW-241: the queued press re-checks the reservation
        when it is delivered, so a press already queued when the chord is
        given back does nothing (the control case still pauses)."""
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        window.attach_hotkey(FakeRegistrar())
        _recording(controller)
        window._hotkey_pressed_q.emit()  # queued: not yet delivered
        if detach:
            window.detach_hotkey()
        qapp.processEvents()
        assert _actions(controller) == ([] if detach else [("pause",)])
        window.deleteLater()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows messages")
    @pytest.mark.skipif(
        os.environ.get("SCRIBE_SKIP_INTEGRATION") == "1",
        reason="integration explicitly skipped via SCRIBE_SKIP_INTEGRATION=1",
    )
    def test_a_real_wm_hotkey_through_qts_dispatch(self, tmp_path: Path) -> None:
        """A synthetic ``WM_HOTKEY`` — first SENT into the window procedure,
        then POSTED to the thread's queue as Windows delivers a real press
        (through Qt's event dispatcher; round 41 LOW-035) — reaches a native
        (never shown) window whose chord a FAKE registrar "reserved"; no real
        chord is ever reserved. Another id is ignored on both paths."""
        env = dict(os.environ)
        env["QT_QPA_PLATFORM"] = "windows"
        child = subprocess.run(
            [sys.executable, "-c", _HOTKEY_DISPATCH_CHILD, str(tmp_path)],
            capture_output=True,
            env=env,
            timeout=120,
            check=False,
        )
        assert child.returncode == 0, child.stderr.decode(errors="replace")
        lines = child.stdout.decode().splitlines()
        assert lines[-2:] == ['SENT ["hotkey"]', 'SEEN ["hotkey", "hotkey"]']
        for marker in (b"Traceback", b"TypeError", b"ValueError", b"wrong argument"):
            assert marker not in child.stderr, child.stderr.decode(errors="replace")


_HOTKEY_DISPATCH_CHILD = """\
import ctypes, json, sys
from pathlib import Path
from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
apply_offline_env()
assert_offline_env()
from PySide6.QtWidgets import QApplication
from scribe_desktop.audio_capture import MockCaptureBackend
from scribe_desktop.clinics import ClinicRegistry
from scribe_desktop.hotkey import HOTKEY_ID, WM_HOTKEY
from scribe_desktop.session import SessionController
from scribe_desktop.ui.main_window import MainWindow
class FakeRegistrar:
    def register(self, hwnd, hotkey_id, modifiers, virtual_key):
        return 0
    def unregister(self, hwnd, hotkey_id):
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
w.on_hotkey = lambda: seen.append('hotkey')
assert w.attach_hotkey(FakeRegistrar()).state == 'on'
hwnd = int(w.winId())
user32 = ctypes.WinDLL('user32')
user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t,
                                ctypes.c_ssize_t]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t,
                                ctypes.c_ssize_t]
user32.PostMessageW.restype = ctypes.c_int
lparam = (0x78 << 16) | 0x0006
# Sent: straight into the window procedure.
user32.SendMessageW(hwnd, WM_HOTKEY, HOTKEY_ID, lparam)
user32.SendMessageW(hwnd, WM_HOTKEY, HOTKEY_ID + 1, 0)
app.processEvents()
print('SENT ' + json.dumps(seen), flush=True)
# Posted: through the thread's queue and Qt's event dispatcher — how Windows
# really delivers WM_HOTKEY (round 41 LOW-035).
assert user32.PostMessageW(hwnd, WM_HOTKEY, HOTKEY_ID, lparam)
assert user32.PostMessageW(hwnd, WM_HOTKEY, HOTKEY_ID + 1, 0)
for _ in range(5):
    app.processEvents()
w.detach_hotkey()
print('SEEN ' + json.dumps(seen), flush=True)
"""


class TestPhraseRulesInTheWindow:
    """Tasks 7.2 and 7.3 in the main window: the live windows reach the
    rules; a spoken pause goes through ``pause_for``; the warning changes
    nothing; the transcript keeps every word."""

    def test_the_phrase_pauses_and_stays_in_the_live_transcript(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        _recording(controller)
        post = _open_live_view(window)
        post(_window(("okay, scribe pause", 4.0)))
        assert _actions(controller) == [("pause",)]
        cue = models.pause_cue_text("spoken", linked=False)
        assert window.statusBar().currentMessage() == cue
        assert "scribe pause" in window.transcript_screen.transcript_view.toPlainText()
        window.deleteLater()

    def test_a_previous_starts_late_window_does_not_pause_the_new_recording(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 57 SEC-022: a window the RETIRED worker posted, delivered
        after the next Start opened its view, reaches neither phrase rule;
        the new worker's same words pause (the control)."""
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        old_post = _open_live_view(window)
        _recording(controller)
        new_post = _open_live_view(window)
        old_post(_window(("okay, scribe pause", 4.0)))
        assert _actions(controller) == []
        assert "scribe pause" not in window.transcript_screen.transcript_view.toPlainText()
        new_post(_window(("okay, scribe pause", 4.0)))
        assert _actions(controller) == [("pause",)]
        window.deleteLater()

    def test_a_phrase_from_before_the_resume_does_not_pause_again(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        _recording(controller)
        post = _open_live_view(window)
        controller.state_value = SessionState.PAUSED
        controller.recorded_seconds = 10
        assert window.session_screen.on_resume()  # cutoff: 10 s + one chunk
        post(_window(("scribe pause", 9.0), ("and we carry on", 12.0)))
        assert ("pause",) not in controller.calls
        post(_window(("scribe pause", 11.5)))
        assert ("pause",) in controller.calls
        window.deleteLater()

    def test_a_new_start_clears_the_cutoff(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        _recording(controller)
        controller.state_value = SessionState.PAUSED
        controller.recorded_seconds = 100
        window.session_screen.on_resume()
        post = window.transcript_screen.live_poster()  # built inside the new Start
        window.session_screen.session_started.emit()
        controller.state_value = SessionState.RECORDING
        post(_window(("scribe pause", 2.0)))
        assert ("pause",) in controller.calls
        window.deleteLater()

    @pytest.mark.parametrize(
        "state", [SessionState.IDLE, SessionState.PROCESSING, SessionState.QUEUED]
    )
    def test_windows_outside_a_recording_are_ignored(
        self, qapp: Any, tmp_path: Path, state: SessionState
    ) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        controller.state_value = state
        post = _open_live_view(window)  # a current post: only the state refuses it
        post(_window(("scribe pause", 1.0), ("bye", 5.0), ("hello", 9.0)))
        assert _actions(controller) == []
        assert window.statusBar().currentMessage() == ""
        window.deleteLater()

    def test_the_warning_is_shown_and_never_pauses(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        bridge = window.attach_chrome_link()
        session = _recording(controller)
        post = _open_live_view(window)
        post(_window(("see you next week", 1.0)))
        post(_window(("good morning, take a seat", 8.0)))
        assert _actions(controller) == []  # a WARNING: no pause, no block
        assert controller.state_value is SessionState.RECORDING
        assert window.statusBar().currentMessage() == models.NEW_CONSULTATION_WARNING_LINE
        assert window.session_screen.message_label.text() == models.NEW_CONSULTATION_WARNING_LINE
        assert bridge.build_content()["warnings"] == [NEW_CONSULTATION_WARNING]
        assert bridge._warning_session == session.session_id
        assert "block" not in bridge.build_content()
        bridge.deleteLater()
        window.deleteLater()

    def test_the_unavailable_line_when_live_transcription_fails(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        bridge = window.attach_chrome_link()
        bridge.set_unavailable()  # a link state, so the Session screen shows its lines
        _recording(controller)
        controller.live_transcription_attached = True
        controller.live_failure = LiveFailure(LiveFailureKind.WORKER_ERROR, "x")
        bridge._tick()
        assert models.CHROME_SPOKEN_PAUSE_UNAVAILABLE_LINE in (
            window.session_screen.chrome_label.text()
        )
        assert bridge.build_content()["spoken_pause"] is False
        bridge.deleteLater()
        window.deleteLater()

    def test_the_pause_reasons_are_hands_free_not_context(self) -> None:
        from scribe_desktop.context_rules import CONTEXT_REASONS

        assert PauseReason.HOTKEY not in CONTEXT_REASONS
        assert PauseReason.SPOKEN not in CONTEXT_REASONS
