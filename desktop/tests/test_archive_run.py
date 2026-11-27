"""Past-sessions-backup plan Task 2.1 (D4, D11): the run gate.

- ``ArchiveRun``: the run object owns the passphrase and the derived key as
  ``bytearray``s and zeroes both on every exit; its ``close`` is idempotent
  and releases the gate once.
- ``MainWindow.archive_run_refusal``: the admission, in its order — a draft
  write in flight (before the live-recording line its reservation would
  also raise), a live recording, the Recovery page (a row made visible only
  by the admission's own refresh, and a recovered transcript awaiting
  Complete or Discard), a voice enrolment (its Stop stays usable: the gate is
  never taken), then the generic busy list and the Past sessions page itself.
- ``begin_archive_run``: the gate taken in one call — the rail, the Settings
  strip and every page disabled — and released only by ``ArchiveRun.close``.
- ``PeriodicSweep``: none of its three steps runs and no clock moves while
  the gate is held.
- ``ChromeBridge``: Start, Discard and "Open for review" refused
  ``backup_running`` (never ``getting_ready``), an armed development tick
  cleared by the refused Start, and the refusal gone when the run ends with no
  further command.
- ``closeEvent``: refused with the run's line before the note engine's
  ``prepare_close``; accepted once the run ends.

Fakes only: the window's seams, the fake controller, no real thread, dialog,
clipboard or Windows layer; synthetic ids only."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from scribe_desktop.ui import models  # noqa: E402
from scribe_desktop.ui import past_sessions_view as view  # noqa: E402
from scribe_desktop.ui.past_sessions import ArchiveRun  # noqa: E402
from test_ui_bridge import Harness  # noqa: E402
from test_ui_screens import (  # noqa: E402
    FakeController,
    _main_window,
    _make_recoverable,
)


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def harness(qapp: Any, tmp_path: Path) -> Iterator[Any]:
    """``test_ui_bridge``'s bridge harness builder (the same shape)."""
    made: list[Harness] = []

    def build(**kwargs: Any) -> Harness:
        root = tmp_path / f"h{len(made)}"
        root.mkdir()
        h = Harness(qapp, root, **kwargs)
        made.append(h)
        return h

    yield build
    for h in made:
        h.close()


_windows: list[Any] = []


@pytest.fixture(autouse=True)
def _windows_closed() -> Iterator[None]:
    """Every window a test built is released and closed, whatever failed."""
    yield
    for window in _windows:
        run = window._archive_run
        if run is not None:
            run.close()
        window.close()
        window.deleteLater()
    _windows.clear()


def _window(tmp_path: Path, controller: Any = None) -> Any:
    window = _main_window(tmp_path, controller)
    _windows.append(window)
    return window


def _run(passphrase: bytes = b"correct horse battery staple") -> ArchiveRun:
    return ArchiveRun(bytearray(passphrase))


def _gated(window: Any) -> bool:
    return not (
        window.rail.isEnabled() or window.settings_strip.isEnabled() or window.tabs.isEnabled()
    )


# ---------------------------------------------------------------------------
# The run object (D4).
# ---------------------------------------------------------------------------


class TestArchiveRun:
    def test_close_zeroes_both_buffers_and_releases_once(self) -> None:
        from scribe_desktop.past_sessions_backup import new_kdf_params

        passphrase = bytearray(b"a passphrase of twenty+")
        key = bytearray(b"\x07" * 32)
        run = ArchiveRun(passphrase)
        run.accept_key(key, new_kdf_params())
        released: list[ArchiveRun] = []
        run.hold_gate(released.append)
        assert run.holds_gate
        run.close()
        run.close()  # idempotent
        assert released == [run]
        assert passphrase == bytearray(len(passphrase))
        assert key == bytearray(32)
        assert run.passphrase is None and run.backup_key is None
        assert run.closed and not run.holds_gate

    def test_the_passphrase_is_zeroed_when_dropped(self) -> None:
        passphrase = bytearray(b"a passphrase of twenty+")
        run = ArchiveRun(passphrase)
        run.drop_passphrase()
        assert passphrase == bytearray(len(passphrase))
        assert run.passphrase is None
        run.close()

    def test_a_key_handed_to_a_closed_run_is_zeroed_and_not_kept(self) -> None:
        from scribe_desktop.past_sessions_backup import new_kdf_params

        run = _run()
        run.close()
        key = bytearray(b"\x09" * 32)
        run.accept_key(key, new_kdf_params())
        assert key == bytearray(32)
        assert run.backup_key is None and run.backup_kdf is None

    def test_a_second_key_zeroes_the_first(self) -> None:
        from scribe_desktop.past_sessions_backup import new_kdf_params

        run = _run()
        first = bytearray(b"\x01" * 32)
        run.accept_key(first, new_kdf_params())
        run.accept_key(bytearray(b"\x02" * 32), new_kdf_params())
        assert first == bytearray(32)
        run.close()

    def test_a_run_closed_without_the_gate_calls_no_release(self) -> None:
        run = _run()
        run.close()
        assert run.closed and not run.holds_gate


# ---------------------------------------------------------------------------
# The admission (D11).
# ---------------------------------------------------------------------------


class TestAdmission:
    def test_an_idle_window_admits_a_run(self, qapp: Any, tmp_path: Path) -> None:
        window = _window(tmp_path)
        assert window.archive_run_refusal() is None

    def test_a_live_recording_refuses(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        controller.reserved_ids = frozenset({uuid.uuid4().hex})
        window = _window(tmp_path, controller)
        assert window.archive_run_refusal() == view.ARCHIVE_LIVE_LINE

    def test_a_reserved_draft_write_gives_the_write_line_first(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Its reservation is also one of the live ids: the write's own line,
        not the recording line."""
        controller = FakeController()
        session_id = uuid.uuid4().hex
        controller.writing_id = session_id
        controller.reserved_ids = frozenset({session_id})
        window = _window(tmp_path, controller)
        assert window.archive_run_refusal() == models.write_line("write_in_flight")

    def test_a_recovery_row_seen_only_by_the_admissions_own_refresh_refuses(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _window(tmp_path)
        _make_recoverable(tmp_path, finished=True)
        recovery = window.recovery_screen
        assert recovery.session_list.count() + recovery.unreviewed_list.count() == 0
        assert window.archive_run_refusal() == view.ARCHIVE_RECOVERY_LINE
        assert recovery.session_list.count() + recovery.unreviewed_list.count() == 1

    def test_a_recovered_transcript_awaiting_complete_refuses(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """A checked-out recovery is in neither list (it is protected)."""
        window = _window(tmp_path)
        window.recovery_screen._protected.add(uuid.uuid4().hex)
        assert window.archive_run_refusal() == view.ARCHIVE_RECOVERY_LINE

    def test_a_voice_enrolment_refuses_and_takes_no_gate(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Enrolment's Stop must stay usable: the window is never disabled."""
        controller = FakeController()
        controller.enrolling = True
        window = _window(tmp_path, controller)
        assert window.archive_run_refusal() == view.ARCHIVE_ENROLMENT_LINE
        run = _run()
        assert window.begin_archive_run(run) == view.ARCHIVE_ENROLMENT_LINE
        assert not run.holds_gate and not window.archive_running
        assert window.tabs.isEnabled() and window.practitioner_screen.isEnabled()
        run.close()

    @pytest.mark.parametrize(
        "screen",
        [
            "session_screen",
            "recovery_screen",
            "microphone_screen",
            "transcript_screen",
            "note_screen",
            "clinics_screen",
        ],
    )
    def test_the_generic_busy_list_refuses(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, screen: str
    ) -> None:
        window = _window(tmp_path)
        monkeypatch.setattr(type(getattr(window, screen)), "is_busy", property(lambda _s: True))
        assert window.archive_run_refusal() == view.ARCHIVE_BUSY_LINE

    def test_a_reverification_refuses(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = _window(tmp_path)
        monkeypatch.setattr(type(window), "is_reverifying", property(lambda _s: True))
        assert window.archive_run_refusal() == view.ARCHIVE_BUSY_LINE

    def test_the_past_sessions_page_itself_refuses_while_its_worker_runs(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _window(tmp_path)
        page = window.past_sessions_screen
        page._hops.append(object())
        try:
            assert page.is_busy
            assert window.archive_run_refusal() == view.ARCHIVE_BUSY_LINE
        finally:
            page._hops.clear()
        assert window.archive_run_refusal() is None


# ---------------------------------------------------------------------------
# The gate (D11).
# ---------------------------------------------------------------------------


class TestTheGate:
    def test_begin_takes_the_gate_and_close_releases_it(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _window(tmp_path)
        assert not _gated(window)
        run = _run()
        assert window.begin_archive_run(run) is None
        assert window.archive_running and run.holds_gate
        assert _gated(window)
        # A second run is refused while one holds the gate.
        second = _run()
        assert window.begin_archive_run(second) == view.ARCHIVE_RUNNING_LINE
        assert not second.holds_gate
        second.close()
        assert window.archive_running and _gated(window)
        run.close()
        assert not window.archive_running
        assert window.rail.isEnabled()
        assert window.settings_strip.isEnabled()
        assert window.tabs.isEnabled()

    def test_a_refused_admission_takes_no_gate(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        controller.reserved_ids = frozenset({uuid.uuid4().hex})
        window = _window(tmp_path, controller)
        run = _run()
        assert window.begin_archive_run(run) == view.ARCHIVE_LIVE_LINE
        assert not window.archive_running and not run.holds_gate and not _gated(window)
        run.close()

    def test_release_refreshes_the_recovery_page(self, qapp: Any, tmp_path: Path) -> None:
        window = _window(tmp_path)
        run = _run()
        assert window.begin_archive_run(run) is None
        _make_recoverable(tmp_path, finished=True)  # appears while the gate is held
        run.close()
        recovery = window.recovery_screen
        assert recovery.session_list.count() + recovery.unreviewed_list.count() == 1

    def test_release_publishes_to_chrome(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = _window(tmp_path)
        bridge = window.attach_chrome_link()
        published: list[bool] = []
        monkeypatch.setattr(bridge, "publish", lambda: published.append(window.archive_running))
        run = _run()
        assert window.begin_archive_run(run) is None
        run.close()
        assert published == [False]  # after the gate went

    def test_close_is_refused_while_held_before_prepare_close(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from PySide6.QtGui import QCloseEvent

        window = _window(tmp_path)
        prepared: list[bool] = []
        monkeypatch.setattr(window.note_screen, "prepare_close", lambda: prepared.append(True))
        run = _run()
        assert window.begin_archive_run(run) is None
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        assert window.statusBar().currentMessage() == view.ARCHIVE_CLOSE_LINE
        assert prepared == []
        run.close()
        event = QCloseEvent()
        window.closeEvent(event)
        assert event.isAccepted()
        assert prepared == [True]


# ---------------------------------------------------------------------------
# The periodic sweep (D11).
# ---------------------------------------------------------------------------


class TestThePeriodicSweep:
    def test_no_step_runs_and_no_clock_moves_while_held(self) -> None:
        from scribe_desktop.app import (
            _AUDIT_PRUNE_INTERVAL_S,
            PeriodicSweep,
        )

        events: list[Any] = []

        class Recovery:
            def protected_session_ids(self) -> frozenset[str]:
                return frozenset()

            def refresh(self) -> None:
                events.append("recovery")

        class Tab:
            def run_retention_sweep(self) -> list[str]:
                events.append("retention")
                return []

        class Window:
            recovery_screen = Recovery()
            past_sessions_screen = Tab()

            def prune_reminders(self) -> None:
                events.append("reminders")

        class Audit:
            def prune(self) -> int:
                events.append("prune")
                return 0

        held = [True]
        now = 1000.0 + _AUDIT_PRUNE_INTERVAL_S
        tick = PeriodicSweep(
            Window(),  # type: ignore[arg-type]
            Audit(),  # type: ignore[arg-type]
            lambda ids: events.append(("sweep", ids)),
            last_prune=1000.0,
            last_retention_sweep=1000.0,
            monotonic=lambda: now,
            archive_running=lambda: held[0],
        )
        tick()
        assert events == []
        assert (tick.last_prune, tick.last_retention_sweep) == (1000.0, 1000.0)
        held[0] = False
        tick()
        assert events == [
            ("sweep", frozenset()),
            "reminders",
            "recovery",
            "prune",
            "retention",
        ]
        assert tick.last_prune == now and tick.last_retention_sweep == now


# ---------------------------------------------------------------------------
# The Chrome bridge (D11).
# ---------------------------------------------------------------------------


def _refusal(h: Harness) -> tuple[str, str] | None:
    refusal = h.sender.last.last_refusal
    return None if refusal is None else (refusal.action, refusal.reason)


class TestTheBridge:
    def test_a_start_is_refused_backup_running_and_the_refusal_goes_with_the_run(
        self, harness: Any
    ) -> None:
        h: Harness = harness()
        h.verified_report()
        held = [True]
        h.bridge.set_archive_gate(lambda: held[0])
        h.start()
        assert _refusal(h) == ("start", "backup_running")
        assert h.sender.last.last_refusal is not None
        assert h.sender.last.last_refusal.message == models.START_BACKUP_RUNNING_MESSAGE
        assert h.controller.started_with == []
        held[0] = False
        h.bridge.publish()  # no further command
        assert h.sender.last.last_refusal is None
        h.start()
        assert _refusal(h) is None and len(h.controller.started_with) == 1

    def test_never_getting_ready_even_while_the_warm_up_holds(self, harness: Any) -> None:
        h: Harness = harness()
        h.verified_report()
        h.screen.set_start_hold(lambda: True)
        h.bridge.set_archive_gate(lambda: True)
        h.start()
        assert _refusal(h) == ("start", "backup_running")

    def test_a_refused_start_clears_and_announces_the_development_tick(
        self, harness: Any
    ) -> None:
        h: Harness = harness(keep_recordings=True)
        h.verified_report()
        h.screen.development_checkbox.setChecked(True)
        h.bridge.set_archive_gate(lambda: True)
        h.start()
        assert _refusal(h) == ("start", "backup_running")
        assert not h.screen.development_checkbox.isChecked()
        assert h.screen.development_label.text() == models.DEVELOPMENT_TICK_CLEARED_LINE

    def test_discard_is_refused_while_held(self, harness: Any) -> None:
        h: Harness = harness()
        h.verified_report()
        h.start()
        ref = h.controller.session_ref
        held = [True]
        h.bridge.set_archive_gate(lambda: held[0])
        h.command("discard", session_ref=ref, confirmed=True)
        assert _refusal(h) == ("discard", "backup_running")
        assert ("discard",) not in h.controller.calls
        held[0] = False
        h.bridge.publish()
        assert h.sender.last.last_refusal is None

    def test_open_review_is_refused_while_held(self, harness: Any) -> None:
        import secrets

        h: Harness = harness()
        h.connect()
        h.bridge.set_archive_gate(lambda: True)
        h.command("open_review", session_ref=secrets.token_urlsafe(18))
        assert _refusal(h) == ("open_review", "backup_running")
        assert h.controller.calls == []

    def test_the_window_hands_its_gate_to_the_bridge(self, qapp: Any, tmp_path: Path) -> None:
        window = _window(tmp_path)
        bridge = window.attach_chrome_link()
        assert not bridge._archive_running()
        run = _run()
        assert window.begin_archive_run(run) is None
        assert bridge._archive_running()
        run.close()
        assert not bridge._archive_running()
