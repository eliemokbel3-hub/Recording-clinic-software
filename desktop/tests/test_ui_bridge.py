"""The Chrome bridge (Cliniko workflow safeguards plan Task 4.5): reports in,
verification on a worker, commands to the Session screen's slots, one
``state`` snapshot out. Offscreen; the pipe is a recording fake sender,
every Cliniko answer comes from ``NoteTransport`` and every key from memory
— no socket, no named pipe."""

from __future__ import annotations

import logging
import os
import secrets
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from encounter_fakes import (  # noqa: E402
    CLINIC_ID,
    HOST,
    NOTE,
    OTHER_HOST,
    OTHER_NOTE,
    PATIENT,
    NoteTransport,
    make_registry,
    note_body,
    ok,
    status,
)
from scribe_desktop.context_rules import PauseReason  # noqa: E402
from scribe_desktop.encounter import (  # noqa: E402
    ConsentAttestation,
    EncounterContext,
    RateLimitLatch,
    UnverifiedOffline,
    Verification,
    Verified,
    unlinked_consent,
)
from scribe_desktop.hotkey import HotkeyStatus  # noqa: E402
from scribe_desktop.protocol import (  # noqa: E402
    Envelope,
    StatePayload,
    make_pipe_envelope,
    typed_payload,
)
from scribe_desktop.session import RecordingSession, SessionState  # noqa: E402
from scribe_desktop.transcription import LiveFailure, LiveFailureKind  # noqa: E402
from scribe_desktop.ui import models  # noqa: E402
from scribe_desktop.ui.bridge import (  # noqa: E402
    MIN_CALL_SPACING_SECONDS,
    RATE_LIMIT_COOLDOWN_SECONDS,
    ChromeBridge,
    _one_line,
)
from scribe_desktop.ui.session_screen import SessionScreen  # noqa: E402
from test_ui_screens import FakeController, _document, _process_until  # noqa: E402

PATIENT_NAME = "Jan Citizen"  # encounter_fakes.PATIENT_BODY's display name
TAB = 412
OTHER_TAB = 413


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.parametrize(
    ("text", "limit", "expected"),
    [
        ("Ann\ud800Lee", 40, "Ann Lee"),  # a lone surrogate (H1 round 53 LOW-044)
        ("Ann Lee", 40, "Ann Lee"),  # a line separator
        ("Ann\x00Lee", 40, "Ann Lee"),  # a control character
        ("Ann  Marie   Lee", 8, "Ann Mari"),  # collapsed, then cut
        ("\x00 \ud800", 8, "Fallback"),  # nothing left: the fallback
    ],
    ids=["lone-surrogate", "line-separator", "nul", "over-limit", "all-control"],
)
def test_display_text_in_a_snapshot_is_one_clean_line(
    text: str, limit: int, expected: str
) -> None:
    """H2a SIMP-008's pin, written against the code before the refactor:
    what the protocol allows in a snapshot's display text."""
    assert _one_line(text, limit, "Fallback") == expected


class FakeSender:
    """``PipeServer.send`` as the bridge sees it: records every frame."""

    def __init__(self) -> None:
        self.sent: list[tuple[int, Envelope]] = []

    def send(self, conn_id: int, envelope: Envelope) -> bool:
        self.sent.append((conn_id, envelope))
        return True

    def states(self, conn_id: int | None = None) -> list[StatePayload]:
        out = []
        for conn, envelope in self.sent:
            assert envelope.type == "state"  # the bridge sends nothing else
            if conn_id is None or conn == conn_id:
                payload = typed_payload(envelope)
                assert isinstance(payload, StatePayload)
                out.append(payload)
        return out

    @property
    def last(self) -> StatePayload:
        return self.states()[-1]


class BridgeController(FakeController):
    """``FakeController`` (which carries what the bridge reads) plus a
    tracked session that follows the controls."""

    def _track(self) -> None:
        if self.session_value is not None:
            self.session_value = self.session_value.with_state(self.state_value)

    def start(
        self,
        device_id: int,
        *,
        consent: ConsentAttestation,
        context: EncounterContext | None = None,
    ) -> RecordingSession:
        super().start(device_id, consent=consent, context=context)
        self.session_value = RecordingSession(
            consent=consent, encounter_context=context
        ).with_state(SessionState.RECORDING)
        self.session_ref = secrets.token_urlsafe(18)
        return self.session_value

    def pause(self) -> RecordingSession:
        super().pause()
        self._track()
        return self._session()

    def resume(self) -> RecordingSession:
        super().resume()
        self._track()
        return self._session()

    def discard(self) -> RecordingSession:
        super().discard()
        self.session_value = None
        self.session_ref = None
        self.state_value = SessionState.IDLE
        return self._session()

    def finish(self) -> RecordingSession:
        super().finish()
        self._track()
        return self._session()

    def transcribe(self, transcriber: Any) -> RecordingSession:
        try:
            return super().transcribe(transcriber)
        finally:
            self._track()


class Harness:
    def __init__(
        self,
        qapp: Any,
        tmp_path: Path,
        *,
        transport: Any = None,
        device: int | None = 1,
        reminders: Any = None,
        open_review: Any = None,
        call_spacing: float = 0.0,
        latch_clock: Callable[[], float] | None = None,
    ) -> None:
        self.qapp = qapp
        self.transport = transport if transport is not None else NoteTransport()
        self.registry = make_registry(tmp_path, transport=self.transport)
        self.controller = BridgeController()
        # Never the real ML stack: a Finish transcribes to a fixed document.
        self.screen = SessionScreen(
            self.controller,
            device_provider=lambda: device,
            transcriber_factory=lambda: (lambda _d, _c: _document()),
        )
        self.now = 1000.0  # the bridge's clock (a "Resume previous" lapses)
        # Draft-write D13: the shared 429 latch, injected as the main window
        # injects it — on the same clock unless a test gives the latch its
        # own — so a test can play another caller.
        self.latch = RateLimitLatch(
            latch_clock if latch_clock is not None else (lambda: self.now)
        )
        # A long interval: the tests drive publish/_tick themselves.
        self.bridge = ChromeBridge(
            self.controller,
            self.screen,
            self.registry,
            publish_interval_ms=60_000,
            clock=lambda: self.now,
            reminders=reminders,
            open_review=open_review,
            # SEC-009's call spacing is off here (this clock never moves on
            # its own) and on in `TestRateLimit`, which pins it.
            call_spacing_seconds=call_spacing,
            latch=self.latch,
        )
        self.cues: list[str] = []
        self.bridge.pause_cue.connect(self.cues.append)
        self.sender = FakeSender()
        self.bridge.attach(self.sender)
        self.seq = 0

    def pump(self) -> None:
        self.qapp.processEvents()
        self.qapp.processEvents()

    def settle(self) -> None:
        assert _process_until(self.qapp, lambda: not self.bridge.is_busy)
        self.pump()

    def connect(self, conn_id: int = 1) -> None:
        self.bridge.connected(conn_id)
        self.pump()

    def report(
        self,
        *,
        conn_id: int = 1,
        tab_id: int = TAB,
        focused: bool = True,
        page: str = "note",
        host: str = HOST,
        note_id: str = NOTE,
        patient_id: str = PATIENT,
        seq: int | None = None,
    ) -> None:
        if seq is None:
            self.seq += 1
            seq = self.seq
        payload: dict[str, Any] = {
            "seq": seq,
            "tab_id": tab_id,
            "window_id": 3,
            "focused": focused,
            "page": page,
        }
        if page in ("note", "login", "other_cliniko"):
            payload["host"] = host
        if page == "note":
            payload.update(patient_id=patient_id, note_id=note_id)
        self.bridge.message(conn_id, make_pipe_envelope("context", payload=payload))
        self.pump()

    def command(self, action: str, *, conn_id: int = 1, **fields: Any) -> None:
        payload: dict[str, Any] = {"action": action, "state_rev": self.bridge.state_rev}
        payload.update(fields)
        self.bridge.message(conn_id, make_pipe_envelope("command", payload=payload))
        self.pump()

    def start(self, *, tab_id: int = TAB, note_id: str = NOTE, **fields: Any) -> None:
        self.command(
            "start",
            consent={"confirmed": True, "text_version": "recording-consent-v1"},
            target={
                "tab_id": tab_id,
                "clinic_host": HOST,
                "patient_id": PATIENT,
                "note_id": note_id,
            },
            **fields,
        )

    def verified_report(self) -> None:
        self.connect()
        self.report()
        self.settle()
        report = self.sender.last.report
        assert report is not None and report.verification == "verified"

    def close(self) -> None:
        # Let a check, or a Finish's transcription, end before teardown.
        _process_until(
            self.qapp, lambda: not self.bridge.is_busy and not self.screen.is_busy, 15.0
        )
        self.bridge.deleteLater()
        self.screen.deleteLater()
        self.pump()


@pytest.fixture
def harness(qapp: Any, tmp_path: Path) -> Any:
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


class _GatedAnswer:
    """A note answer held until ``release`` (a verification in flight)."""

    def __init__(self) -> None:
        self.gate = threading.Event()
        self.entered = threading.Event()

    def __call__(self) -> Any:
        self.entered.set()
        self.gate.wait(10)
        return ok(note_body())


class TestLinkAndSnapshot:
    def test_attached_waits_and_sends_nothing_without_a_client(self, harness: Any) -> None:
        h = harness()
        assert h.sender.sent == []
        text = h.screen.chrome_label.text()
        assert text.startswith(models.CHROME_WAITING_LINE)
        assert models.HOTKEY_LINES["not_set_up"] in text
        assert not h.screen.chrome_label.isHidden()

    def test_unavailable_names_the_desktop_fallback(self, harness: Any) -> None:
        h = harness()
        h.bridge.set_unavailable()
        assert h.screen.chrome_label.text().startswith(models.CHROME_UNAVAILABLE_LINE)

    def test_a_client_gets_the_full_snapshot_once_per_connection(self, harness: Any) -> None:
        h = harness()
        gen = h.bridge.conn_gen
        h.connect(1)
        assert h.bridge.conn_gen == gen + 1
        first = h.sender.last
        assert first.state_rev == 1 and first.app_running is True
        assert first.allow_list == [HOST]
        assert first.hotkey.available is False and first.spoken_pause is False
        assert first.notice == "open_a_note"
        assert first.report is None and first.live is None and first.last_refusal is None
        h.bridge.publish()
        h.bridge._tick()
        assert len(h.sender.sent) == 1  # unchanged: nothing resent
        assert models.CHROME_CONNECTED_LINE in h.screen.chrome_label.text()
        h.connect(2)  # a NEW client: the same content is sent again
        assert h.bridge.conn_gen == gen + 2
        assert [c for c, _ in h.sender.sent] == [1, 2]
        assert h.sender.last.state_rev == 2

    def test_a_disconnect_bumps_conn_gen_and_an_old_one_is_ignored(self, harness: Any) -> None:
        h = harness()
        h.connect(1)
        h.connect(2)
        gen = h.bridge.conn_gen
        h.bridge.disconnected(1, "closed")  # the earlier client: ignored
        h.pump()
        assert h.bridge.conn_gen == gen
        h.bridge.disconnected(2, "closed")
        h.pump()
        assert h.bridge.conn_gen == gen + 1
        assert h.screen.chrome_label.text().startswith(models.CHROME_WAITING_LINE)
        sent = len(h.sender.sent)
        h.bridge.publish()
        assert len(h.sender.sent) == sent  # no client: nothing sent

    def test_pipe_lost_fires_on_connect_and_disconnect(self, harness: Any) -> None:
        h = harness()
        lost: list[int] = []
        h.bridge.pipe_lost.connect(lambda: lost.append(1))
        h.connect(1)
        h.bridge.disconnected(1, "closed")
        h.pump()
        assert lost == [1, 1]

    def test_a_message_from_another_connection_is_ignored(self, harness: Any) -> None:
        h = harness()
        h.connect(1)
        h.report(conn_id=9)
        assert h.transport.calls == []


class TestPipeUnavailableFallback:
    """Phase 4's contract, re-checked after round 57 SEC-013 gave the pipe an
    explicit owner (k10): when the pipe cannot be created — its name held, or
    ``CreateNamedPipe`` refusing, which is where an unassignable owner would
    fail — ``scribe-app`` still starts, the Chrome link reads unavailable and
    the desktop still records (``app._start_chrome_link``)."""

    @pytest.mark.parametrize("reason", ["name_taken", "create_failed"])
    def test_the_link_is_unavailable_and_the_desktop_still_records(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reason: str
    ) -> None:
        from scribe_desktop import app
        from scribe_desktop.pipe_server import PipeUnavailable
        from test_ui_screens import _main_window

        class _Refused:
            def start(self) -> None:
                raise PipeUnavailable(reason)

        monkeypatch.setattr(
            app.PipeServer, "for_current_user", staticmethod(lambda _events, **_kw: _Refused())
        )
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        assert app._start_chrome_link(window, logging.getLogger("test-pipe-fallback")) is None
        screen = window.session_screen
        assert screen.chrome_label.text().startswith(models.CHROME_UNAVAILABLE_LINE)
        screen._device_provider = lambda: 7
        screen.consent_checkbox.setChecked(True)
        screen.on_start()
        assert any(call[0] == "start" for call in controller.calls)
        assert window.chrome_bridge is not None
        window.chrome_bridge.deleteLater()
        window.deleteLater()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows named pipes")
    def test_a_refused_descriptor_leaves_a_working_app(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """H3a step 1 (round 65's start-up gap): the REAL server's start with
        Windows refusing the pipe's descriptor. The conversion now fails
        before any pipe exists, so the real per-user name is never touched."""
        import pywintypes

        from scribe_desktop import app, pipe_server
        from test_ui_screens import _main_window

        def refuse(*_args: Any) -> Any:
            raise pywintypes.error(
                1336, "ConvertStringSecurityDescriptorToSecurityDescriptor", "refused by the test"
            )

        monkeypatch.setattr(
            pipe_server.win32security, "ConvertStringSecurityDescriptorToSecurityDescriptor", refuse
        )
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        assert app._start_chrome_link(window, logging.getLogger("test-pipe-fallback")) is None
        screen = window.session_screen
        assert screen.chrome_label.text().startswith(models.CHROME_UNAVAILABLE_LINE)
        screen._device_provider = lambda: 7
        screen.consent_checkbox.setChecked(True)
        screen.on_start()
        assert any(call[0] == "start" for call in controller.calls)
        assert window.chrome_bridge is not None
        window.chrome_bridge.deleteLater()
        window.deleteLater()


class TestServerEnded:
    def test_a_server_that_stops_serving_reads_unavailable_and_sends_nothing(
        self, harness: Any
    ) -> None:
        """Round 57 SEC-017: the pipe server's ``ended`` (after its current
        connection was reported ``server_failed``) turns the link line to
        unavailable, and no snapshot is sent after it."""
        h = harness()
        h.verified_report()
        h.bridge.disconnected(1, "server_failed")
        h.bridge.ended()
        h.pump()
        assert h.screen.chrome_label.text().startswith(models.CHROME_UNAVAILABLE_LINE)
        count = len(h.sender.sent)
        h.bridge.connected(2)  # nothing can arrive now; if it did, still no sender
        h.pump()
        h.bridge.publish()
        assert len(h.sender.sent) == count


class TestReports:
    def test_a_note_report_is_verified_and_named(self, harness: Any) -> None:
        h = harness()
        h.verified_report()
        report = h.sender.last.report
        assert report is not None
        assert (report.tab_id, report.clinic_host, report.patient_id, report.note_id) == (
            TAB,
            HOST,
            PATIENT,
            NOTE,
        )
        assert report.patient_name == PATIENT_NAME
        assert report.clinic_label == "Northside"
        assert report.appointment_starts_at is not None
        assert h.sender.last.notice is None
        assert [c[0] for c in h.transport.calls] == ["GET"] * len(h.transport.calls)

    def test_checking_is_published_while_the_check_runs(self, harness: Any) -> None:
        answer = _GatedAnswer()
        h = harness(transport=NoteTransport(note=answer))
        h.connect()
        h.report()
        assert answer.entered.wait(5)
        h.bridge.publish()
        report = h.sender.last.report
        assert report is not None and report.verification == "checking"
        assert report.patient_name is None
        answer.gate.set()
        h.settle()
        assert h.sender.last.report is not None
        assert h.sender.last.report.verification == "verified"

    def test_a_refused_note_publishes_its_reason_and_no_name(self, harness: Any) -> None:
        h = harness(transport=NoteTransport(note=status(404)))
        h.connect()
        h.report()
        h.settle()
        report = h.sender.last.report
        assert report is not None and report.verification == "refused"
        assert report.refusal is not None and report.patient_name is None

    def test_a_host_not_on_the_allow_list_is_never_checked(self, harness: Any) -> None:
        h = harness()
        h.connect()
        h.report(host=OTHER_HOST)
        h.settle()
        assert h.transport.calls == []
        assert h.sender.last.report is None
        assert h.sender.last.notice == "clinic_not_set_up"

    def test_a_replayed_seq_is_ignored(self, harness: Any) -> None:
        h = harness()
        h.connect()
        h.report(seq=5)
        h.settle()
        calls = len(h.transport.calls)
        h.report(seq=5, note_id=OTHER_NOTE)
        h.report(seq=4, note_id=OTHER_NOTE)
        h.settle()
        assert len(h.transport.calls) == calls
        assert h.sender.last.report is not None and h.sender.last.report.note_id == NOTE

    def test_only_the_focused_tab_is_bound(self, harness: Any) -> None:
        h = harness()
        h.connect()
        h.report(tab_id=TAB)
        h.settle()
        calls = len(h.transport.calls)
        h.report(tab_id=OTHER_TAB, focused=False, note_id=OTHER_NOTE)
        h.settle()
        assert len(h.transport.calls) == calls  # an unfocused tab feeds nothing
        assert h.sender.last.report is not None and h.sender.last.report.tab_id == TAB
        h.report(tab_id=OTHER_TAB, focused=True, note_id=OTHER_NOTE)
        h.settle()
        report = h.sender.last.report
        assert report is not None and (report.tab_id, report.note_id) == (OTHER_TAB, OTHER_NOTE)

    def test_closing_the_bound_tab_clears_the_report(self, harness: Any) -> None:
        h = harness()
        h.verified_report()
        h.report(page="closed")
        assert h.sender.last.report is None
        assert h.sender.last.notice == "open_a_note"

    def test_a_result_for_an_earlier_connection_is_dropped(self, harness: Any) -> None:
        answer = _GatedAnswer()
        h = harness(transport=NoteTransport(note=answer))
        h.connect(1)
        h.report(conn_id=1)
        assert answer.entered.wait(5)
        h.connect(2)  # conn_gen moves on; the running check is now stale
        h.seq = 0
        h.report(conn_id=2)  # waits behind the running check
        answer.gate.set()
        h.settle()
        notes = [c for c in h.transport.calls if c[2].startswith("/v1/treatment_notes/")]
        assert len(notes) == 2  # the stale answer was not reused for the new report
        report = h.sender.last.report
        assert report is not None and report.verification == "verified"


def _note_calls(h: Harness) -> int:
    return len([c for c in h.transport.calls if c[2].startswith("/v1/treatment_notes/")])


class TestRateLimit:
    """Round 57 SEC-009 (practitioner decision 2026-09-28): after a 429 the
    clinic's checks make no call for ``RATE_LIMIT_COOLDOWN_SECONDS``, and no
    two calls start closer than ``MIN_CALL_SPACING_SECONDS``."""

    def test_a_429_answers_the_clinic_offline_without_a_call_for_a_minute(
        self, harness: Any
    ) -> None:
        h = harness(transport=NoteTransport(note=status(429)))
        h.connect()
        h.report()
        h.settle()
        assert _note_calls(h) == 1
        report = h.sender.last.report
        assert report is not None and report.verification == "unverified_offline"
        h.transport.routes["/v1/treatment_notes/"] = ok(note_body())
        h.now += RATE_LIMIT_COOLDOWN_SECONDS - 1
        h.report(note_id=OTHER_NOTE)  # a new run inside the cooldown: no call
        h.settle()
        assert _note_calls(h) == 1
        report = h.sender.last.report
        assert report is not None and report.note_id == OTHER_NOTE
        assert report.verification == "unverified_offline"  # recording stays allowed
        # The cooldown's own answer did not extend it: a minute after the 429
        # the next run is checked again.
        h.now += 1
        h.report()
        h.settle()
        assert _note_calls(h) == 2
        report = h.sender.last.report
        assert report is not None and report.verification == "verified"

    def test_a_429_the_bridge_sees_cools_the_shared_latch(self, harness: Any) -> None:
        """Draft-write D13: the bridge records a real 429 in the ONE latch,
        so the checkout and the write see the clinic cooling for a minute."""
        h = harness(transport=NoteTransport(note=status(429)))
        h.connect()
        h.report()
        h.settle()
        assert h.latch.cooling(CLINIC_ID, h.now) == RATE_LIMIT_COOLDOWN_SECONDS
        assert h.latch.cooling(CLINIC_ID, h.now + RATE_LIMIT_COOLDOWN_SECONDS - 1) == 1.0
        assert h.latch.cooling(CLINIC_ID, h.now + RATE_LIMIT_COOLDOWN_SECONDS) is None

    def test_a_429_recorded_by_another_caller_cools_the_bridge(self, harness: Any) -> None:
        """A 429 the write or the checkout records makes the bridge's checks
        answer offline with no call, until the minute is up."""
        h = harness()
        h.connect()
        h.latch.record_429(CLINIC_ID, h.now)  # as a write hop or the checkout would
        h.report()
        h.settle()
        assert _note_calls(h) == 0
        report = h.sender.last.report
        assert report is not None and report.verification == "unverified_offline"
        h.now += RATE_LIMIT_COOLDOWN_SECONDS
        # A minute on, a NEW run (another note: a repeat report of the same
        # target continues its run and dispatches nothing) is checked again.
        h.report(note_id=OTHER_NOTE)
        h.settle()
        assert _note_calls(h) == 1
        report = h.sender.last.report
        assert report is not None and report.note_id == OTHER_NOTE
        assert report.verification == "verified"

    def test_the_bridge_reads_and_records_on_the_latchs_clock(self, harness: Any) -> None:
        """Round 9 LOW-012, pinned by round 11 LOW-006: with the bridge's
        clock at 1000 and the latch's at 0, a 429 recorded at latch-time 0
        still cools the bridge, and a 429 the bridge sees is recorded at
        latch-time 0 — never on the bridge's own clock."""
        latch_now = [0.0]
        h = harness(latch_clock=lambda: latch_now[0])
        h.connect()
        h.latch.record_429(CLINIC_ID, 0.0)
        h.report()
        h.settle()
        assert _note_calls(h) == 0
        report = h.sender.last.report
        assert report is not None and report.verification == "unverified_offline"

        seen = harness(transport=NoteTransport(note=status(429)), latch_clock=lambda: 0.0)
        seen.connect()
        seen.report()
        seen.settle()
        assert _note_calls(seen) == 1
        assert seen.latch.cooling(CLINIC_ID, 0.0) == RATE_LIMIT_COOLDOWN_SECONDS

    def test_the_bridge_builds_its_own_latch_when_none_is_given(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        now = [50.0]
        screen = SessionScreen(
            BridgeController(),
            device_provider=lambda: 1,
            transcriber_factory=lambda: (lambda _d, _c: _document()),
        )
        bridge = ChromeBridge(
            BridgeController(), screen, make_registry(tmp_path), clock=lambda: now[0]
        )
        try:
            latch = bridge._latch
            assert isinstance(latch, RateLimitLatch) and latch.clock() == 50.0
        finally:
            bridge.deleteLater()
            screen.deleteLater()

    def test_a_live_recheck_inside_the_cooldown_makes_no_call(self, harness: Any) -> None:
        """Round 63 LOW: the cooldown answers the linked live session's
        reconnect re-check too (the ``live`` branch), offline and by identity."""
        h: Harness = harness()
        h.verified_report()
        h.start()
        h.transport.routes["/v1/treatment_notes/"] = status(429)
        h.report(note_id=OTHER_NOTE)  # a 429 starts the clinic's cooldown
        h.settle()
        calls = len(h.transport.calls)
        h.connect(2)  # the re-check: answered offline without a call
        h.settle()
        assert len(h.transport.calls) == calls
        result = h.bridge.live_reverification()
        assert result is not None and result.request.conn_gen == h.bridge.conn_gen
        assert isinstance(result.outcome, UnverifiedOffline) and result.outcome.rate_limited

    # --- a waiting check that went stale makes no call (codex round 65 PR-LOW-350) ---

    @pytest.mark.parametrize(
        "moved_on",
        [{"page": "closed"}, {"page": "other_cliniko"}, {}],
        ids=["tab_closed", "not_a_note", "back_to_a_reused_note"],
    )
    def test_a_check_deferred_by_the_spacing_is_dropped_once_its_tab_moves_on(
        self, harness: Any, moved_on: dict[str, Any]
    ) -> None:
        h = harness(call_spacing=MIN_CALL_SPACING_SECONDS)
        h.connect()
        h.report()
        h.settle()
        assert _note_calls(h) == 1
        h.report(note_id=OTHER_NOTE)  # deferred by the spacing
        assert h.bridge.is_busy and _note_calls(h) == 1
        # The tab closes, shows a page that is no note, or returns to the
        # first note (verified moments ago: reused, no call of its own).
        h.report(**moved_on)
        h.settle()  # the timer fires and finds nothing the ledger awaits
        assert _note_calls(h) == 1
        if not moved_on:
            report = h.sender.last.report
            assert report is not None and report.note_id == NOTE
            assert report.verification == "verified"

    def test_a_check_waiting_behind_a_running_one_is_dropped_once_its_tab_closes(
        self, harness: Any
    ) -> None:
        """The same class without the spacing: a report check waiting in its
        slot behind a check in flight."""
        answer = _GatedAnswer()
        h = harness(transport=NoteTransport(note=answer))
        h.connect()
        h.report()
        assert answer.entered.wait(5)
        h.report(note_id=OTHER_NOTE)  # waits behind the running check
        h.report(page="closed")
        answer.gate.set()
        h.settle()
        assert _note_calls(h) == 1

    def test_a_deferred_live_recheck_still_runs(self, harness: Any) -> None:
        """The linked live session's re-check keeps its own semantics: it
        answers its session, not the bound report, so no report run gates
        it — deferred by the spacing, it still runs."""
        h: Harness = harness(call_spacing=MIN_CALL_SPACING_SECONDS)
        h.verified_report()
        h.start()
        calls = _note_calls(h)
        h.connect(2)  # the re-check, inside the spacing: deferred
        assert h.bridge.is_busy and _note_calls(h) == calls
        h.settle()
        assert _note_calls(h) == calls + 1
        result = h.bridge.live_reverification()
        assert result is not None and isinstance(result.outcome, Verified)

    def test_an_offline_answer_that_is_not_a_429_starts_no_cooldown(self, harness: Any) -> None:
        h = harness(transport=NoteTransport(note=status(503)))
        h.connect()
        h.report()
        h.settle()
        h.transport.routes["/v1/treatment_notes/"] = ok(note_body())
        h.report(note_id=OTHER_NOTE)
        h.settle()
        assert _note_calls(h) == 2
        report = h.sender.last.report
        assert report is not None and report.verification == "verified"

    def test_a_check_inside_the_spacing_waits_without_blocking_and_is_coalesced(
        self, harness: Any
    ) -> None:
        h = harness(call_spacing=MIN_CALL_SPACING_SECONDS)
        h.connect()
        h.report()
        h.settle()
        assert _note_calls(h) == 1
        h.report(note_id=OTHER_NOTE)  # inside the spacing: returns, no call yet
        assert _note_calls(h) == 1 and h.bridge.is_busy
        h.bridge.publish()
        report = h.sender.last.report
        assert report is not None and report.verification == "checking"
        h.report(note_id="2003")  # a newer report replaces the waiting one
        h.settle()  # the single-shot timer starts the ONE deferred call
        assert _note_calls(h) == 2
        assert h.transport.calls[-3][2] == "/v1/treatment_notes/2003"
        report = h.sender.last.report
        assert report is not None and report.note_id == "2003"
        assert report.verification == "verified"
        # The timer's pass is spent: the next report is spaced again.
        h.report(note_id=OTHER_NOTE)
        assert _note_calls(h) == 2 and h.bridge.is_busy
        h.settle()
        assert _note_calls(h) == 3


class TestStart:
    def test_a_verified_report_starts_a_linked_recording(self, harness: Any) -> None:
        h = harness()
        h.verified_report()
        h.start()
        assert len(h.controller.started_with) == 1
        consent, context = h.controller.started_with[0]
        assert context is not None and context.verification is Verification.VERIFIED
        assert (context.patient_id, context.treatment_note_id) == (PATIENT, NOTE)
        assert consent.treatment_note_id == NOTE
        state = h.sender.last
        assert state.last_refusal is None
        live = state.live
        assert live is not None and live.linked and live.phase == "recording"
        assert live.session_ref == h.controller.session_ref
        assert live.patient_name == PATIENT_NAME and live.clinic_label == "Northside"
        text = h.screen.chrome_label.text()
        assert f"Recording for {PATIENT_NAME} - Northside." in text
        assert not h.screen.consent_checkbox.isChecked()

    def test_an_offline_report_starts_unverified_and_unnamed(self, harness: Any) -> None:
        h = harness(transport=NoteTransport(note=status(503)))
        h.connect()
        h.report()
        h.settle()
        report = h.sender.last.report
        assert report is not None and report.verification == "unverified_offline"
        h.start()
        _, context = h.controller.started_with[0]
        assert context is not None
        assert context.verification is Verification.UNVERIFIED_OFFLINE
        live = h.sender.last.live
        assert live is not None and live.patient_name is None
        assert "a patient (name not verified)" in h.screen.chrome_label.text()

    def _refused(self, h: Harness, reason: str) -> None:
        refusal = h.sender.last.last_refusal
        assert refusal is not None
        assert (refusal.action, refusal.reason) == ("start", reason)
        assert h.controller.started_with == []
        assert f"Refused from Chrome: {refusal.message}" in h.screen.chrome_label.text()

    def test_a_stale_state_rev_is_refused(self, harness: Any) -> None:
        h = harness()
        h.verified_report()
        h.start(state_rev=h.bridge.state_rev - 1)
        self._refused(h, "stale_state")

    def test_another_tab_is_a_target_mismatch(self, harness: Any) -> None:
        h = harness()
        h.verified_report()
        h.start(tab_id=OTHER_TAB)
        self._refused(h, "target_mismatch")

    def test_another_note_is_a_target_mismatch(self, harness: Any) -> None:
        h = harness()
        h.verified_report()
        h.start(note_id=OTHER_NOTE)
        self._refused(h, "target_mismatch")

    def test_no_report_is_refused(self, harness: Any) -> None:
        h = harness()
        h.connect()
        h.start()
        self._refused(h, "target_mismatch")  # no bound tab at all

    def test_a_check_in_flight_is_refused_as_checking(self, harness: Any) -> None:
        answer = _GatedAnswer()
        h = harness(transport=NoteTransport(note=answer))
        h.connect()
        h.report()
        assert answer.entered.wait(5)
        h.start()
        self._refused(h, "checking")
        answer.gate.set()
        h.settle()

    def test_a_refused_note_is_not_verified_with_its_reason(self, harness: Any) -> None:
        h = harness(transport=NoteTransport(note=status(404)))
        h.connect()
        h.report()
        h.settle()
        h.start()
        self._refused(h, "not_verified")

    def test_an_active_session_is_refused(self, harness: Any) -> None:
        h = harness()
        h.verified_report()
        h.controller.state_value = SessionState.RECORDING
        h.start()
        self._refused(h, "session_active")

    def test_an_open_review_is_refused(self, harness: Any) -> None:
        h = harness()
        h.verified_report()
        h.controller.generating = True
        h.start()
        self._refused(h, "review_open")

    def test_a_draft_write_in_flight_is_session_active(self, harness: Any) -> None:
        """Draft-write D9 (Task 5.2): a Start would retire the session a
        Cliniko write holds — refused with the EXISTING code (D2)."""
        h = harness()
        h.verified_report()
        h.controller.writing_id = "held-by-a-write"
        h.start()
        self._refused(h, "session_active")
        h.controller.writing_id = None
        h.start()
        assert len(h.controller.started_with) == 1  # the control

    def test_no_microphone_is_refused(self, harness: Any) -> None:
        h = harness(device=None)
        h.verified_report()
        h.start()
        self._refused(h, "no_microphone")

    @pytest.mark.parametrize("code", ["locked", "lock_unknown"])
    def test_a_start_is_refused_while_locked(self, harness: Any, code: str) -> None:
        """H1 round 53 MED-039 (PR-MED-300's class): a Start still on its
        way when the lock arrived records nothing behind the locked screen,
        even with a verified report; once unlocked the same Start records
        (the control)."""
        h = harness()
        h.verified_report()
        lock: list[str | None] = [code]
        h.bridge.set_lock_refusal(lambda: lock[0])
        h.start()
        self._refused(h, code)
        assert h.sender.last.last_refusal is not None
        assert h.sender.last.last_refusal.message == models.CHROME_REFUSALS[code]
        lock[0] = None
        h.start()
        assert h.sender.last.last_refusal is None
        assert len(h.controller.started_with) == 1

    @pytest.mark.parametrize("code", ["locked", "lock_unknown"])
    def test_the_desktop_start_is_refused_while_locked(self, harness: Any, code: str) -> None:
        """H1 round 54 MED-052 (the same class as MED-039): a desktop Start
        click still queued when the computer locked starts nothing; the
        Session screen names the lock. Once unlocked the same press records
        (the control)."""
        h = harness()
        lock: list[str | None] = [code]
        h.bridge.set_lock_refusal(lambda: lock[0])
        h.screen.consent_checkbox.setChecked(True)
        h.screen.on_start()
        assert h.controller.started_with == []
        assert h.screen.message_label.text() == models.CHROME_REFUSALS[code]
        lock[0] = None
        h.screen.consent_checkbox.setChecked(True)  # every Start clears the tick
        h.screen.on_start()
        assert len(h.controller.started_with) == 1
        _, context = h.controller.started_with[0]
        assert context is None  # the desktop Start is unlinked

    def test_a_chrome_start_is_refused_while_the_warm_up_holds(self, harness: Any) -> None:
        """Installation plan round 36 MED-001 (the practitioner's option
        (b)): a Chrome Start during the start-up import warm-up is refused
        with the getting-ready line — the controller is never asked (no
        audit row, no session) and the desktop tick is untouched; once the
        hold lifts the same Start records (the control)."""
        h = harness()
        h.verified_report()
        held = [True]
        h.screen.set_start_hold(lambda: held[0])
        h.screen.consent_checkbox.setChecked(True)
        h.start()
        self._refused(h, "getting_ready")
        assert h.sender.last.last_refusal is not None
        assert h.sender.last.last_refusal.message == models.START_GETTING_READY_MESSAGE
        assert h.screen.consent_checkbox.isChecked()  # nothing consumed it
        held[0] = False
        h.start()
        assert h.sender.last.last_refusal is None
        assert len(h.controller.started_with) == 1

    def test_the_desktop_start_is_refused_while_the_warm_up_holds_and_keeps_the_tick(
        self, harness: Any
    ) -> None:
        """Round 36 MED-001: the desktop Start names the hold and KEEPS the
        consent tick, so the next press — once the hold lifts — records."""
        h = harness()
        held = [True]
        h.screen.set_start_hold(lambda: held[0])
        h.screen.consent_checkbox.setChecked(True)
        h.screen.on_start()
        assert h.controller.started_with == []
        assert h.screen.message_label.text() == models.START_GETTING_READY_MESSAGE
        assert h.screen.consent_checkbox.isChecked()
        held[0] = False
        h.screen.on_start()
        assert len(h.controller.started_with) == 1
        assert not h.screen.consent_checkbox.isChecked()  # a Start that ran clears it

    def test_a_linked_start_reaching_the_screen_while_held_is_refused(
        self, harness: Any
    ) -> None:
        """Round 36 MED-001, the screen's own check: ``start_linked`` refuses
        a held Start before clearing the desktop tick or asking the
        controller (the bridge asks first; this is the second line)."""
        h = harness()
        h.screen.set_start_hold(lambda: True)
        h.screen.consent_checkbox.setChecked(True)
        assert h.screen.start_linked(unlinked_consent(), None) is False
        assert h.controller.started_with == []
        assert h.screen.consent_checkbox.isChecked()
        assert h.screen.message_label.text() == models.START_GETTING_READY_MESSAGE

    def test_a_hung_warm_up_holds_start_for_its_bound_only(self, harness: Any) -> None:
        """Round 36 MED-001: a warm-up that never returns refuses Start only
        until ``hold_seconds`` after it began (a fake clock, no real import);
        from then on Start is admitted (Chrome's and the desktop's)."""
        from scribe_desktop.ml_warmup import ImportWarmup

        h = harness()
        h.verified_report()
        gate = threading.Event()
        now = [100.0]

        def hang() -> None:
            gate.wait()

        warmup = ImportWarmup(hang, clock=lambda: now[0])
        warmup.start()
        try:
            h.screen.set_start_hold(warmup.holds_start)
            now[0] = 159.9  # inside the 60 s bound
            h.start()
            self._refused(h, "getting_ready")
            now[0] = 160.0  # the bound: admitted although the warm-up still runs
            assert not warmup.is_finished()
            h.start()
            assert h.sender.last.last_refusal is None
            assert len(h.controller.started_with) == 1
        finally:
            gate.set()
            assert warmup.wait(5.0)

    def test_a_failed_warm_up_holds_nothing(self, harness: Any) -> None:
        from scribe_desktop.ml_warmup import ImportWarmup

        def broken() -> None:
            raise ImportError("no ML stack")

        h = harness()
        warmup = ImportWarmup(broken)
        warmup.start()
        assert warmup.wait(5.0)
        h.screen.set_start_hold(warmup.holds_start)
        h.screen.consent_checkbox.setChecked(True)
        h.screen.on_start()
        assert len(h.controller.started_with) == 1

    def test_a_refusal_goes_when_what_it_was_about_leaves_the_screen(
        self, harness: Any
    ) -> None:
        """H1 round 53 LOW-042: a refused Start for one note stays while that
        note is in front (the poll keeps it), and goes when another tab's
        note comes to the front — it never sits under another patient's
        Ready panel."""
        h = harness(transport=NoteTransport(note=status(404)))
        h.connect()
        h.report()
        h.settle()
        h.start()
        self._refused(h, "not_verified")
        h.bridge._tick()
        assert h.sender.last.last_refusal is not None  # nothing changed: it stays
        h.report(tab_id=OTHER_TAB, note_id=OTHER_NOTE)
        h.settle()
        assert h.sender.last.last_refusal is None
        assert "Refused from Chrome" not in h.screen.chrome_label.text()

    def test_a_refusal_is_state_never_an_error_and_clears_on_the_next_command(
        self, harness: Any
    ) -> None:
        h = harness()
        h.verified_report()
        h.start(state_rev=h.bridge.state_rev + 5)  # a future rev is stale too
        assert h.sender.last.last_refusal is not None
        h.start()
        assert h.sender.last.last_refusal is None
        assert all(envelope.type == "state" for _, envelope in h.sender.sent)


class TestSessionCommands:
    def _recording(self, harness: Any) -> Harness:
        h: Harness = harness()
        h.verified_report()
        h.start()
        assert h.controller.session_ref is not None
        return h

    def _refusal(self, h: Harness) -> tuple[str, str] | None:
        refusal = h.sender.last.last_refusal
        return None if refusal is None else (refusal.action, refusal.reason)

    @pytest.mark.parametrize("action", ["resume", "finish", "discard"])
    def test_a_wrong_ref_is_refused_before_the_slot(self, harness: Any, action: str) -> None:
        h = self._recording(harness)
        calls = list(h.controller.calls)
        fields: dict[str, Any] = {"session_ref": secrets.token_urlsafe(18)}
        if action == "discard":
            fields["confirmed"] = True
        h.command(action, **fields)
        assert self._refusal(h) == (action, "session_changed")
        assert h.controller.calls == calls

    def test_pause_needs_no_ref_and_resume_needs_its_own_note(self, harness: Any) -> None:
        h = self._recording(harness)
        ref = h.controller.session_ref
        h.command("pause")
        assert ("pause",) in h.controller.calls and self._refusal(h) is None
        live = h.sender.last.live
        assert live is not None and live.phase == "paused"
        h.report(note_id=OTHER_NOTE)  # the practitioner moved to another note
        h.settle()
        h.command("resume", session_ref=ref)
        assert self._refusal(h) == ("resume", "report_mismatch")
        assert ("resume",) not in h.controller.calls
        h.report(note_id=NOTE)
        h.settle()
        h.command("resume", session_ref=ref)
        assert self._refusal(h) is None and ("resume",) in h.controller.calls

    def test_a_control_the_state_does_not_allow_is_refused(self, harness: Any) -> None:
        h = self._recording(harness)
        h.command("resume", session_ref=h.controller.session_ref)  # already recording
        assert self._refusal(h) == ("resume", "not_allowed_now")
        assert ("resume",) not in h.controller.calls

    def test_discard_with_the_live_ref_discards(self, harness: Any) -> None:
        h = self._recording(harness)
        h.command("discard", session_ref=h.controller.session_ref, confirmed=True)
        assert ("discard",) in h.controller.calls and self._refusal(h) is None
        assert h.sender.last.live is None

    def test_discard_is_refused_busy_while_a_draft_write_holds_the_session(
        self, harness: Any
    ) -> None:
        """Draft-write D9 (Task 5.2): Pause still works; Discard would
        destroy the session the write holds and is refused ``busy``."""
        h = self._recording(harness)
        ref = h.controller.session_ref
        h.controller.writing_id = "held-by-a-write"
        h.command("discard", session_ref=ref, confirmed=True)
        assert self._refusal(h) == ("discard", "busy")
        assert ("discard",) not in h.controller.calls
        h.command("pause")
        assert ("pause",) in h.controller.calls and self._refusal(h) is None
        h.controller.writing_id = None
        h.command("discard", session_ref=ref, confirmed=True)
        assert ("discard",) in h.controller.calls and self._refusal(h) is None

    def test_a_discard_waiting_for_live_transcription_is_reported_when_it_ends(
        self, harness: Any
    ) -> None:
        """Installation plan round 40 LOW-002: with live transcription
        attached, a Chrome Discard runs off the GUI thread. Every Chrome
        command meanwhile is refused ``busy`` and reaches nothing. One that
        live transcription outlasts is refused ``failed`` once it ends (as a
        refused Discard always was), the session kept."""
        from scribe_desktop.session import LiveStopPendingError

        h = self._recording(harness)
        ref = h.controller.session_ref
        h.controller.live_transcription_attached = True
        entered, gate = threading.Event(), threading.Event()

        def outlasted() -> RecordingSession:
            h.controller.calls.append(("discard",))
            h.controller.state_value = SessionState.FAILED  # capture stopped, key kept
            entered.set()
            assert gate.wait(5)
            raise LiveStopPendingError("discard refused: the live transcriber has not stopped yet")

        h.controller.discard = outlasted  # type: ignore[method-assign]
        h.command("discard", session_ref=ref, confirmed=True)
        assert entered.wait(5)
        assert self._refusal(h) is None and h.screen.is_busy
        calls = list(h.controller.calls)
        h.command("pause")
        assert self._refusal(h) == ("pause", "busy")
        h.command("discard", session_ref=ref, confirmed=True)
        assert self._refusal(h) == ("discard", "busy")
        assert h.controller.calls == calls
        gate.set()
        assert _process_until(h.qapp, lambda: not h.screen.is_busy)
        assert self._refusal(h) == ("discard", "failed")
        assert h.screen.message_label.text() == models.DISCARD_KEPT_LIVE_STOPPING_MESSAGE
        assert h.controller.session_ref == ref  # kept: Discard can be pressed again

    def test_open_review_without_an_index_is_not_available(self, harness: Any) -> None:
        """A bridge built without the main window's reminder index and opener
        (Task 5.5) refuses ``open_review`` by name and runs nothing."""
        h = harness()
        h.connect()
        h.command("open_review", session_ref=secrets.token_urlsafe(18))
        assert self._refusal(h) == ("open_review", "not_available")
        assert h.controller.calls == []


class TestLiveSession:
    def test_a_new_client_reverifies_the_linked_live_session(self, harness: Any) -> None:
        h: Harness = harness()
        h.verified_report()
        h.start()
        assert h.bridge.live_reverification() is None
        notes = len(h.transport.calls)
        h.connect(2)
        h.settle()
        result = h.bridge.live_reverification()
        assert result is not None and isinstance(result.outcome, Verified)
        assert result.request.conn_gen == h.bridge.conn_gen
        assert len(h.transport.calls) > notes
        assert models.CHROME_RECHECK_LINES["verified"] in h.screen.chrome_label.text()
        # the re-check never binds a report: Start still needs a fresh one
        assert h.sender.last.report is None

    def test_a_reverification_is_for_its_own_session_only(self, harness: Any) -> None:
        h: Harness = harness()
        h.verified_report()
        h.start()
        h.connect(2)
        h.settle()
        h.controller.session_value = RecordingSession(consent=unlinked_consent()).with_state(
            SessionState.RECORDING
        )
        assert h.bridge.live_reverification() is None

    def test_the_name_goes_when_its_session_ends(self, harness: Any) -> None:
        h: Harness = harness()
        h.verified_report()
        h.start()
        assert PATIENT_NAME in h.screen.chrome_label.text()
        h.controller.session_value = None
        h.controller.session_ref = None
        h.controller.state_value = SessionState.IDLE
        h.bridge._tick()
        assert h.bridge._live_display is None
        assert PATIENT_NAME not in h.screen.chrome_label.text()
        assert h.sender.last.live is None

    def test_a_rechecked_name_outlives_a_later_reconnect_for_the_label(
        self, harness: Any
    ) -> None:
        """Privacy-professional-controls D5 (H1 round 32 LOW-005): a Start
        made offline has no name; a reconnect's Verified re-check finds it.
        Once the session is queued, a further reconnect clears the re-check
        (write-back needs a current one) — but the name stays for this
        session's Past-sessions label, is never shown in Chrome, and goes
        with its session."""
        h: Harness = harness(transport=NoteTransport(note=status(503)))
        h.connect()
        h.report()
        h.settle()
        h.start()  # unverified_offline: no Start display
        session = h.controller.session_value
        assert session is not None
        session_id = session.session_id
        assert h.bridge.live_display_name(session_id) is None
        h.transport.routes["/v1/treatment_notes/"] = ok(note_body())
        h.connect(2)
        h.settle()
        assert h.bridge.live_display_name(session_id) == PATIENT_NAME
        h.controller.state_value = SessionState.QUEUED
        h.controller.session_value = session.with_state(SessionState.QUEUED)
        h.connect(3)
        h.settle()
        assert h.bridge.live_reverification() is None  # not capturing: cleared
        assert h.bridge.live_display_name(session_id) == PATIENT_NAME
        assert h.bridge.live_display_name(secrets.token_hex(16)) is None
        live = h.sender.last.live
        assert live is None or live.patient_name is None  # never shown in Chrome
        h.controller.session_value = None
        h.controller.session_ref = None
        h.controller.state_value = SessionState.IDLE
        h.bridge._tick()
        assert h.bridge._recheck_display is None

    def test_a_report_check_never_displaces_the_live_recheck(self, harness: Any) -> None:
        """Round 25 MED-018: with a check in flight at reconnect, the re-check
        waited in the ONE slot a report's check then took — so it never ran
        and the Session screen said "Checking..." for the session's life."""
        answer = _GatedAnswer()
        answer.gate.set()
        h: Harness = harness(transport=NoteTransport(note=answer))
        h.verified_report()
        h.start()
        answer.gate.clear()
        answer.entered.clear()
        h.report(note_id=OTHER_NOTE)  # a check in flight on connection 1
        assert answer.entered.wait(5)
        h.connect(2)  # the re-check waits behind it...
        h.seq = 0
        h.report(conn_id=2)  # ...and so does connection 2's first report
        answer.gate.set()
        h.settle()
        result = h.bridge.live_reverification()
        assert result is not None and isinstance(result.outcome, Verified)
        assert result.request.conn_gen == h.bridge.conn_gen
        report = h.sender.last.report
        assert report is not None and report.verification == "verified"
        assert models.CHROME_RECHECK_LINES["verified"] in h.screen.chrome_label.text()

    def test_a_disconnect_does_not_strand_a_waiting_recheck(self, harness: Any) -> None:
        """Round 26 LOW-022: a re-check waiting behind a running check still
        runs after the client goes away — it answers its session, not the
        connection (clearing it left "Checking..." until a reconnect)."""
        answer = _GatedAnswer()
        answer.gate.set()
        h: Harness = harness(transport=NoteTransport(note=answer))
        h.verified_report()
        h.start()
        answer.gate.clear()
        answer.entered.clear()
        h.report(note_id=OTHER_NOTE)  # a check in flight on connection 1
        assert answer.entered.wait(5)
        h.connect(2)  # the re-check waits behind it
        h.bridge.disconnected(2, "closed")
        h.pump()
        answer.gate.set()
        h.settle()
        result = h.bridge.live_reverification()
        assert result is not None and isinstance(result.outcome, Verified)
        assert models.CHROME_RECHECK_LINES["verified"] in h.screen.chrome_label.text()

    def test_a_recheck_in_flight_under_a_replaced_key_is_void_and_rerun(
        self, harness: Any
    ) -> None:
        """Codex round 29 PR-MED-150 (D9): a Replace key while the re-check
        runs voids it — its answer is never installed — and checks again
        under the current key."""
        answer = _GatedAnswer()
        answer.gate.set()
        h: Harness = harness(transport=NoteTransport(note=answer))
        h.verified_report()
        h.start()
        answer.gate.clear()
        answer.entered.clear()
        h.connect(2)  # the re-check runs under the current rev
        assert answer.entered.wait(5)
        old = h.bridge._live_check
        h.registry._bump(CLINIC_ID)  # Replace key (D9)
        h.bridge.on_clinics_changed()
        assert h.bridge._live_check is not old  # checked again, same connection
        answer.gate.set()
        h.settle()
        result = h.bridge.live_reverification()
        assert result is not None and isinstance(result.outcome, Verified)
        assert result.request.clinic_rev == h.registry.rev(CLINIC_ID)
        assert result.request.conn_gen == h.bridge.conn_gen

    def test_a_completed_recheck_is_void_after_a_key_change(self, harness: Any) -> None:
        """Codex round 29 PR-MED-150 (D9): a verified re-check stops counting
        the moment the clinic's rev moves — never shown as verified under a
        replaced key — and Replace key's signal checks it again."""
        answer = _GatedAnswer()
        answer.gate.set()
        h: Harness = harness(transport=NoteTransport(note=answer))
        h.verified_report()
        h.start()
        h.connect(2)
        h.settle()
        assert models.CHROME_RECHECK_LINES["verified"] in h.screen.chrome_label.text()
        answer.gate.clear()
        answer.entered.clear()
        h.registry._bump(CLINIC_ID)
        assert h.bridge.live_reverification() is None  # void at once, before any signal
        h.bridge._refresh_view()
        assert models.CHROME_RECHECK_LINES["verified"] not in h.screen.chrome_label.text()
        h.bridge.on_clinics_changed()
        assert answer.entered.wait(5)  # checked again under the new key
        assert models.CHROME_RECHECK_LINES["checking"] in h.screen.chrome_label.text()
        answer.gate.set()
        h.settle()
        result = h.bridge.live_reverification()
        assert result is not None and result.request.clinic_rev == h.registry.rev(CLINIC_ID)

    def test_a_removed_clinic_voids_the_recheck_as_clinic_gone(self, harness: Any) -> None:
        """Codex round 29 PR-MED-150 (D9): Remove voids the re-check; the
        Session screen says the clinic is gone, never "verified"."""
        h: Harness = harness()
        h.verified_report()
        h.start()
        h.connect(2)
        h.settle()
        h.registry.remove(CLINIC_ID, live_session_clinic=None)
        h.bridge.on_clinics_changed()
        h.settle()
        assert h.bridge.live_reverification() is None
        text = h.screen.chrome_label.text()
        assert models.CHROME_RECHECK_LINES["clinic_gone"] in text
        assert models.CHROME_RECHECK_LINES["verified"] not in text

    def test_the_recheck_goes_when_its_session_ends(self, harness: Any) -> None:
        """Round 25 LOW-019: the re-check's result carries the patient's name,
        so it is dropped with the session, like the Start verification's."""
        h: Harness = harness()
        h.verified_report()
        h.start()
        h.connect(2)
        h.settle()
        assert h.bridge.live_reverification() is not None
        h.controller.session_value = None
        h.controller.session_ref = None
        h.controller.state_value = SessionState.IDLE
        h.bridge._tick()
        assert h.bridge._live_check is None

    def test_a_recheck_answering_after_its_session_ended_is_dropped(
        self, harness: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 25 MED-018: a re-check whose session ended while it ran is
        dropped by identity — never offered to the report ledger."""
        answer = _GatedAnswer()
        answer.gate.set()
        h: Harness = harness(transport=NoteTransport(note=answer))
        h.verified_report()
        h.start()
        answer.gate.clear()
        answer.entered.clear()
        h.connect(2)  # the re-check runs
        assert answer.entered.wait(5)
        h.controller.session_value = None
        h.controller.session_ref = None
        h.controller.state_value = SessionState.IDLE
        h.bridge._tick()
        offered: list[object] = []
        original = h.bridge._ledger.accept

        def spy(result: Any) -> bool:
            offered.append(result)
            return original(result)

        monkeypatch.setattr(h.bridge._ledger, "accept", spy)
        answer.gate.set()
        h.settle()
        assert offered == [] and h.bridge._live_check is None

    def test_the_timer_and_spoken_pause_follow_the_controller(self, harness: Any) -> None:
        h: Harness = harness()
        h.verified_report()
        h.start()
        h.controller.recorded_seconds = 42
        # Round 41 LOW-034: a RUNNING live transcriber first, so the
        # unavailable line below can only come from the failure.
        h.controller.live_transcription_attached = True
        h.bridge._tick()
        live = h.sender.last.live
        assert live is not None and live.recorded_seconds == 42
        assert h.sender.last.spoken_pause is True
        assert models.CHROME_SPOKEN_PAUSE_UNAVAILABLE_LINE not in h.screen.chrome_label.text()
        h.controller.live_failure = LiveFailure(LiveFailureKind.WORKER_ERROR, "x")
        h.bridge._tick()
        assert models.CHROME_SPOKEN_PAUSE_UNAVAILABLE_LINE in h.screen.chrome_label.text()
        assert h.sender.last.spoken_pause is False

    def test_an_unlinked_session_publishes_no_ids(self, harness: Any) -> None:
        h: Harness = harness()
        h.connect()
        h.screen.consent_checkbox.setChecked(True)
        h.screen.on_start()  # the desktop Start: unlinked
        assert h.controller.started_with[0][1] is None
        h.bridge._tick()
        live = h.sender.last.live
        assert live is not None and live.linked is False
        assert live.patient_id is None and live.note_id is None and live.patient_name is None


def _recording(harness: Any) -> Harness:
    """A linked, verified recording started from ``TAB`` on ``NOTE``."""
    h: Harness = harness()
    h.verified_report()
    h.start()
    assert h.controller.state is SessionState.RECORDING
    return h


def _refusal_of(h: Harness) -> tuple[str, str] | None:
    refusal = h.sender.last.last_refusal
    return None if refusal is None else (refusal.action, refusal.reason)


class TestHandsFree:
    """Phase 7 (D7, D8) as the bridge SHOWS it: the hotkey's status, the
    spoken pause's availability and the warning, in ``state`` and on the
    Session screen — none of them changing a session."""

    def test_the_hotkey_status_reaches_state_and_the_desktop(self, harness: Any) -> None:
        h: Harness = harness()
        h.connect()
        assert h.sender.last.hotkey.available is False
        h.bridge.set_hotkey_status(HotkeyStatus("on"))
        hotkey = h.sender.last.hotkey
        assert hotkey.available is True and hotkey.chord == "Ctrl+Shift+F9"
        assert models.HOTKEY_LINES["on"].format(chord="Ctrl+Shift+F9") in (
            h.screen.chrome_label.text()
        )
        h.bridge.set_hotkey_status(HotkeyStatus("failed", error=1409))
        hotkey = h.sender.last.hotkey
        assert hotkey.available is False and hotkey.chord is None
        assert "Pause hotkey unavailable" in h.screen.chrome_label.text()
        assert h.controller.calls == []  # a status changes no session

    def test_spoken_pause_is_on_only_while_a_live_transcriber_runs(self, harness: Any) -> None:
        h = _recording(harness)
        h.bridge._tick()
        assert h.sender.last.spoken_pause is False  # no live transcriber attached
        assert models.CHROME_SPOKEN_PAUSE_UNAVAILABLE_LINE in h.screen.chrome_label.text()
        h.controller.live_transcription_attached = True
        h.bridge._tick()
        assert h.sender.last.spoken_pause is True
        assert models.SPOKEN_PAUSE_LINES["on"] in h.screen.chrome_label.text()
        h.controller.live_failure = LiveFailure(LiveFailureKind.FELL_BEHIND, "x")
        h.bridge._tick()
        assert h.sender.last.spoken_pause is False
        assert models.CHROME_SPOKEN_PAUSE_UNAVAILABLE_LINE in h.screen.chrome_label.text()

    def test_the_warning_is_published_for_its_live_recording_only(self, harness: Any) -> None:
        h = _recording(harness)
        session = h.controller.session
        assert session is not None
        h.bridge.set_new_consultation_warning(session.session_id)
        assert h.sender.last.warnings == ["new_consultation"]
        assert models.NEW_CONSULTATION_WARNING_LINE in h.screen.chrome_label.text()
        assert ("pause",) not in h.controller.calls  # a warning never pauses
        assert h.sender.last.block is None and h.controller.state is SessionState.RECORDING
        h.screen.on_pause()
        h.bridge._tick()
        assert h.sender.last.warnings == ["new_consultation"]  # still live while paused
        h.screen.on_finish()
        h.bridge._tick()
        assert h.sender.last.warnings == []
        assert h.bridge._warning_session is None
        assert models.NEW_CONSULTATION_WARNING_LINE not in h.screen.chrome_label.text()

    def test_a_warning_for_another_recording_is_not_shown(self, harness: Any) -> None:
        h = _recording(harness)
        h.bridge.set_new_consultation_warning("0" * 32)
        assert h.sender.last.warnings == []

    @pytest.mark.parametrize("reason", [PauseReason.HOTKEY, PauseReason.SPOKEN])
    def test_a_hands_free_pause_pauses_without_a_block(
        self, harness: Any, reason: PauseReason
    ) -> None:
        """D5: only a context reason sets the block; the hotkey and the
        spoken phrase pause, cue, and leave Resume to the one guard."""
        h = _recording(harness)
        h.bridge.pause_for(reason)
        assert h.controller.state is SessionState.PAUSED
        assert h.sender.last.block is None
        assert h.cues == [models.pause_cue_text(reason.value, linked=True)]
        h.bridge.pause_for(reason)  # PAUSED: nothing more
        assert h.controller.calls.count(("pause",)) == 1
        assert h.screen.on_resume() is True  # its own note is still the focused report
        assert h.controller.state is SessionState.RECORDING


class TestPauseRule:
    """Task 5.1: D5 as the bridge applies it — every pause through the
    Session screen's slot, the block on a linked session, the desktop cue."""

    @pytest.mark.parametrize(
        ("shape", "reason"),
        [
            ({"note_id": OTHER_NOTE}, "note_changed"),
            ({"page": "other_cliniko"}, "left_note"),
            ({"page": "not_cliniko"}, "left_note"),  # the bound tab left the allow-list
            ({"page": "closed"}, "tab_closed"),
            ({"tab_id": OTHER_TAB, "note_id": OTHER_NOTE}, "other_note"),
            ({"tab_id": OTHER_TAB, "page": "login"}, "login"),
        ],
    )
    def test_a_context_change_pauses_and_blocks(
        self, harness: Any, shape: dict[str, Any], reason: str
    ) -> None:
        h = _recording(harness)
        h.report(**shape)
        h.settle()
        assert ("pause",) in h.controller.calls
        assert h.controller.state is SessionState.PAUSED
        state = h.sender.last
        assert state.live is not None and state.live.phase == "paused"
        block = state.block
        assert block is not None and block.reason == reason
        assert block.session_ref == h.controller.session_ref
        assert (block.clinic_host, block.clinic_label) == (HOST, "Northside")
        assert block.patient_name == PATIENT_NAME  # the recording's own patient
        assert h.cues == [models.pause_cue_text(reason, linked=True)]
        assert models.BLOCK_DESKTOP_LINE in h.screen.chrome_label.text()

    @pytest.mark.parametrize(
        "shape",
        [
            {"tab_id": OTHER_TAB, "page": "not_cliniko"},  # a SEPARATE non-Cliniko tab
            {"tab_id": OTHER_TAB, "page": "other_cliniko"},  # the calendar elsewhere
            {"tab_id": OTHER_TAB, "note_id": OTHER_NOTE, "focused": False},
            {"tab_id": OTHER_TAB, "page": "closed"},
            {"tab_id": OTHER_TAB},  # the same note in a second tab
            {},  # its own note again
        ],
    )
    def test_the_positive_controls_never_pause(
        self, harness: Any, shape: dict[str, Any]
    ) -> None:
        h = _recording(harness)
        h.report(**shape)
        h.settle()
        assert ("pause",) not in h.controller.calls
        assert h.controller.state is SessionState.RECORDING
        assert h.sender.last.block is None and h.cues == []

    def test_pipe_loss_pauses_and_resume_is_refused_until_the_note_is_reported(
        self, harness: Any
    ) -> None:
        h = _recording(harness)
        h.bridge.disconnected(1, "closed")
        h.pump()
        assert h.controller.state is SessionState.PAUSED
        assert h.cues == [models.pause_cue_text("pipe_lost", linked=True)]
        # the desktop button: refused by name, nothing called
        assert h.screen.on_resume() is False
        assert ("resume",) not in h.controller.calls
        assert h.screen.message_label.text() == models.CHROME_REFUSALS["pipe_down"]
        h.connect(2)  # a new client: still paused (already), still refused
        assert h.screen.on_resume() is False
        assert h.screen.message_label.text() == models.CHROME_REFUSALS["report_mismatch"]
        h.seq = 0
        h.report(conn_id=2, tab_id=900)  # Chrome restarted: a NEW tab id, same note
        h.settle()
        assert h.screen.on_resume() is True
        assert h.controller.state is SessionState.RECORDING
        assert h.sender.last.block is None
        # the session is bound to the re-bound tab: that tab leaving pauses
        h.report(conn_id=2, tab_id=900, page="other_cliniko")
        assert h.controller.state is SessionState.PAUSED

    def test_a_new_client_pauses_a_recording(self, harness: Any) -> None:
        h = _recording(harness)
        h.connect(2)
        h.settle()
        assert h.controller.state is SessionState.PAUSED
        block = h.sender.last.block
        assert block is not None and block.reason == "new_client"

    @pytest.mark.parametrize("reason", [PauseReason.SUSPEND, PauseReason.LOCKED])
    def test_an_unlinked_recording_ignores_chrome_but_not_suspend_or_lock(
        self, harness: Any, reason: PauseReason
    ) -> None:
        h: Harness = harness()
        h.connect()
        h.screen.consent_checkbox.setChecked(True)
        h.screen.on_start()
        h.report(note_id=OTHER_NOTE)
        h.bridge.disconnected(1, "closed")
        h.pump()
        assert h.controller.state is SessionState.RECORDING and h.cues == []
        h.bridge.pause_for(reason)
        assert h.controller.state is SessionState.PAUSED
        assert h.cues == [models.pause_cue_text(reason.value, linked=False)]
        assert h.bridge._block is None  # no note, so no block
        assert h.screen.on_resume() is True  # no report needed for an unlinked one
        h.settle()

    def test_a_lock_pauses_and_blocks_a_linked_recording(self, harness: Any) -> None:
        """D5 as amended 2026-09-28: a lock is a system reason — exactly like
        suspend it pauses a linked recording and puts up the block."""
        h = _recording(harness)
        h.bridge.pause_for(PauseReason.LOCKED)
        h.settle()
        assert h.controller.state is SessionState.PAUSED
        block = h.sender.last.block
        assert block is not None and block.reason == "locked"
        assert h.cues == [models.pause_cue_text("locked", linked=True)]
        h.report()  # its own note again: a report alone never resumes
        h.settle()
        assert ("resume",) not in h.controller.calls

    @pytest.mark.parametrize(
        "state", [SessionState.PROCESSING, SessionState.QUEUED, SessionState.IDLE]
    )
    def test_pause_for_is_a_no_op_outside_recording_and_paused(
        self, harness: Any, state: SessionState
    ) -> None:
        h = _recording(harness)
        h.controller.state_value = state
        h.controller._track()
        for reason in PauseReason:
            h.bridge.pause_for(reason)
        assert ("pause",) not in h.controller.calls
        assert h.cues == [] and h.bridge._block is None

    def test_paused_already_only_blocks_and_cues_once(self, harness: Any) -> None:
        h = _recording(harness)
        h.command("pause")
        pauses = h.controller.calls.count(("pause",))
        h.report(note_id=OTHER_NOTE)
        h.report(page="other_cliniko")
        h.settle()
        assert h.controller.calls.count(("pause",)) == pauses  # nothing paused again
        block = h.sender.last.block
        assert block is not None and block.reason == "left_note"  # the latest reason
        assert h.cues == [models.pause_cue_text("note_changed", linked=True)]

    def test_a_replayed_report_after_resolution_changes_nothing(self, harness: Any) -> None:
        h = _recording(harness)
        h.report(note_id=OTHER_NOTE)  # seq 2: pauses
        stale = h.seq
        h.report()  # its own note again
        h.settle()
        assert h.screen.on_resume() is True
        h.report(note_id=OTHER_NOTE, seq=stale)  # replayed: ignored
        assert h.controller.state is SessionState.RECORDING

    @pytest.mark.parametrize("code", ["locked", "lock_unknown"])
    def test_a_resume_command_is_refused_while_locked(self, harness: Any, code: str) -> None:
        """Codex round 51 PR-MED-300: a Chrome ``resume`` arriving after the
        lock is refused by name even with the note's current report — and
        the same command resumes once unlocked (the control)."""
        h = _recording(harness)
        ref = h.controller.session_ref
        h.command("pause", session_ref=ref)
        lock: list[str | None] = [code]
        h.bridge.set_lock_refusal(lambda: lock[0])
        h.report()  # its own note, focused: everything but the lock is satisfied
        h.settle()
        h.command("resume", session_ref=ref)
        assert _refusal_of(h) == ("resume", code)
        assert ("resume",) not in h.controller.calls
        assert h.screen.on_resume() is False  # the desktop slot meets it too
        assert h.screen.message_label.text() == models.CHROME_REFUSALS[code]
        lock[0] = None
        h.command("resume", session_ref=ref)
        assert _refusal_of(h) is None and h.controller.state is SessionState.RECORDING

    def test_resume_command_needs_the_focused_report_of_its_own_note(self, harness: Any) -> None:
        h = _recording(harness)
        ref = h.controller.session_ref
        h.report(tab_id=OTHER_TAB, note_id=OTHER_NOTE)  # B focused: pauses
        h.settle()
        h.command("resume", session_ref=ref)
        assert _refusal_of(h) == ("resume", "report_mismatch")
        h.report(tab_id=TAB)  # A's tab focused again
        h.settle()
        h.command("resume", session_ref=ref)
        assert _refusal_of(h) is None and h.controller.state is SessionState.RECORDING
        assert h.sender.last.block is None


class TestResolution:
    """Task 5.2: Flow 3's block — Finish previous, Resume previous (by ids,
    resuming only on a matching report) and Discard previous (confirmed)."""

    def _blocked(self, harness: Any) -> Harness:
        h = _recording(harness)
        h.report(note_id=OTHER_NOTE)  # the recording's tab opened B's note
        h.settle()
        assert h.sender.last.block is not None
        return h

    def test_resume_previous_waits_for_the_recordings_own_note(self, harness: Any) -> None:
        h = self._blocked(harness)
        ref = h.controller.session_ref
        h.command("resume_previous", session_ref=ref)
        assert _refusal_of(h) is None
        assert h.controller.state is SessionState.PAUSED  # B is still on screen
        h.report(note_id=OTHER_NOTE)  # B again: still waiting
        h.settle()
        assert ("resume",) not in h.controller.calls
        h.report()  # the extension took the tab back to A's note
        h.settle()
        assert ("resume",) in h.controller.calls
        assert h.controller.state is SessionState.RECORDING
        assert h.sender.last.block is None and h.bridge._pending_resume is None

    def test_resume_previous_when_the_note_is_already_shown_resumes_at_once(
        self, harness: Any
    ) -> None:
        h = self._blocked(harness)
        h.report()
        h.settle()
        assert h.controller.state is SessionState.PAUSED  # a report alone never resumes
        h.command("resume_previous", session_ref=h.controller.session_ref)
        assert h.controller.state is SessionState.RECORDING

    def test_resume_previous_lapses(self, harness: Any) -> None:
        h = self._blocked(harness)
        h.command("resume_previous", session_ref=h.controller.session_ref)
        h.now += 31
        h.report()
        h.settle()
        assert h.controller.state is SessionState.PAUSED
        assert h.bridge._pending_resume is None

    @pytest.mark.parametrize("reason", [PauseReason.SUSPEND, PauseReason.LOCKED])
    def test_a_suspend_or_lock_ends_a_waiting_resume_previous(
        self, harness: Any, reason: PauseReason
    ) -> None:
        """D5 as amended 2026-09-28: a "Resume previous" still waiting for
        its note's report ends when the machine sleeps or locks, so the
        report arriving behind a locked screen resumes nothing (the control
        is ``test_resume_previous_waits_for_the_recordings_own_note``: the
        same report without the lock resumes)."""
        h = self._blocked(harness)
        h.command("resume_previous", session_ref=h.controller.session_ref)
        assert h.bridge._pending_resume is not None
        h.bridge.pause_for(reason)
        assert h.bridge._pending_resume is None
        h.report()  # the extension took the tab back to the recording's note
        h.settle()
        assert ("resume",) not in h.controller.calls
        assert h.controller.state is SessionState.PAUSED
        block = h.sender.last.block
        # Round 49 LOW-038: the block Chrome put up keeps its own reason.
        assert block is not None and block.reason == "note_changed"
        assert h.cues == [models.pause_cue_text("note_changed", linked=True)]

    def test_a_system_reason_names_a_block_it_starts_but_a_chrome_one_renames(
        self, harness: Any
    ) -> None:
        """Round 49 LOW-038: a lock or suspend never renames a block Chrome
        put up, but a later Chrome reason still does (the latest page
        change is what the practitioner must see)."""
        h = _recording(harness)
        h.bridge.pause_for(PauseReason.LOCKED)  # starts the block: named by the lock
        h.settle()
        block = h.sender.last.block
        assert block is not None and block.reason == "locked"
        h.report(note_id=OTHER_NOTE)
        h.settle()
        block = h.sender.last.block
        assert block is not None and block.reason == "note_changed"
        h.bridge.pause_for(PauseReason.SUSPEND)
        h.settle()
        block = h.sender.last.block
        assert block is not None and block.reason == "note_changed"

    def test_a_resume_previous_arriving_after_the_lock_creates_nothing(
        self, harness: Any
    ) -> None:
        """Codex round 51 PR-MED-300, the peer's ordering: the lock is
        handled FIRST, then the click that was already on its way arrives —
        refused by name, no waiting resume, and the note's report resumes
        nothing."""
        h = self._blocked(harness)
        lock: list[str | None] = ["locked"]
        h.bridge.set_lock_refusal(lambda: lock[0])
        h.bridge.pause_for(PauseReason.LOCKED)
        h.command("resume_previous", session_ref=h.controller.session_ref)
        assert _refusal_of(h) == ("resume_previous", "locked")
        assert h.bridge._pending_resume is None
        h.report()  # the recording's own note, behind the locked screen
        h.settle()
        assert ("resume",) not in h.controller.calls
        assert h.controller.state is SessionState.PAUSED
        lock[0] = None  # unlocked: the same click works again (the control)
        h.command("resume_previous", session_ref=h.controller.session_ref)
        assert ("resume",) in h.controller.calls

    def test_a_failed_resume_previous_stays_shown_when_the_notes_check_lands(
        self, harness: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 54 LOW-053: "Resume previous" completes on the note's report
        while that report's check is still running; if the Resume then
        fails, the refusal stays when the check lands (it was not about the
        verification). An offline outcome is never reused, so the check is
        really in flight."""
        h = harness(transport=NoteTransport(note=status(503)))
        h.connect()
        h.report()
        h.settle()
        h.start()
        assert h.controller.state is SessionState.RECORDING
        h.report(note_id=OTHER_NOTE)  # the recording's tab opened B's note
        h.settle()
        h.command("resume_previous", session_ref=h.controller.session_ref)

        def fails() -> Any:
            raise RuntimeError("the device went away")

        monkeypatch.setattr(h.controller, "resume", fails)
        h.report()  # back on the recording's note: a new check starts
        assert _refusal_of(h) == ("resume_previous", "failed")
        h.settle()  # the check lands
        assert _refusal_of(h) == ("resume_previous", "failed")

    def test_a_waiting_resume_previous_ends_when_the_lock_is_flagged(self, harness: Any) -> None:
        """The lock flag is set before the queued pause runs: a waiting
        click whose note report arrives in between is dropped, not
        completed."""
        h = self._blocked(harness)
        h.command("resume_previous", session_ref=h.controller.session_ref)
        assert h.bridge._pending_resume is not None  # B still on screen: waiting
        h.bridge.set_lock_refusal(lambda: "locked")  # flagged; pause still queued
        h.report()
        h.settle()
        assert ("resume",) not in h.controller.calls
        assert h.bridge._pending_resume is None

    def test_a_chrome_reason_leaves_a_waiting_resume_previous(self, harness: Any) -> None:
        """Only the system reasons end the click: the tab passing through
        other pages on its way back to the note must not."""
        h = self._blocked(harness)
        h.command("resume_previous", session_ref=h.controller.session_ref)
        h.report(page="other_cliniko")
        h.settle()
        assert h.bridge._pending_resume is not None
        h.report()
        h.settle()
        assert ("resume",) in h.controller.calls

    def test_resume_previous_lapses_on_a_new_connection(self, harness: Any) -> None:
        h = self._blocked(harness)
        h.command("resume_previous", session_ref=h.controller.session_ref)
        h.connect(2)
        h.seq = 0
        h.report(conn_id=2)
        h.settle()
        assert h.controller.state is SessionState.PAUSED
        assert h.bridge._pending_resume is None

    def test_resume_previous_needs_the_live_ref_and_a_paused_linked_session(
        self, harness: Any
    ) -> None:
        h = self._blocked(harness)
        h.command("resume_previous", session_ref=secrets.token_urlsafe(18))
        assert _refusal_of(h) == ("resume_previous", "session_changed")
        assert h.bridge._pending_resume is None
        h.report()
        h.settle()
        h.command("resume", session_ref=h.controller.session_ref)
        h.command("resume_previous", session_ref=h.controller.session_ref)  # recording
        assert _refusal_of(h) == ("resume_previous", "not_allowed_now")

    def test_finish_previous_finishes_the_blocked_recording(self, harness: Any) -> None:
        h = self._blocked(harness)
        h.command("finish", session_ref=h.controller.session_ref)
        assert ("finish",) in h.controller.calls and _refusal_of(h) is None
        assert _process_until(h.qapp, lambda: not h.screen.is_busy)
        h.bridge._tick()
        assert h.controller.state is SessionState.QUEUED
        assert h.sender.last.block is None and h.bridge._block is None

    def test_discard_previous_carries_its_confirmation(self, harness: Any) -> None:
        h = self._blocked(harness)
        h.command("discard", session_ref=h.controller.session_ref, confirmed=True)
        assert ("discard",) in h.controller.calls
        assert h.sender.last.block is None and h.sender.last.live is None

    def test_the_desktop_resume_honours_the_block(self, harness: Any) -> None:
        h = self._blocked(harness)
        assert h.screen.on_resume() is False  # B's note is on screen
        assert ("resume",) not in h.controller.calls
        h.report()
        h.settle()
        assert h.screen.on_resume() is True
        assert h.sender.last.block is None


class TestBackToBack:
    """Task 5.3 (D6): the next patient's Start at QUEUED, refused while the
    previous note review holds the generation lease."""

    def _queued(self, harness: Any) -> Harness:
        h = _recording(harness)
        h.controller.state_value = SessionState.QUEUED
        h.controller._track()
        h.bridge._tick()
        live = h.sender.last.live
        assert live is not None and live.phase == "queued"
        return h

    def test_start_at_queued_starts_the_next_recording(self, harness: Any) -> None:
        h = self._queued(harness)
        h.start()
        assert len(h.controller.started_with) == 2 and _refusal_of(h) is None
        assert h.controller.state is SessionState.RECORDING

    def test_an_open_review_refuses_start_and_says_so(self, harness: Any) -> None:
        h = self._queued(harness)
        h.controller.generating = True
        h.bridge._tick()
        assert h.sender.last.notice == "review_open"
        h.start()
        assert _refusal_of(h) == ("start", "review_open")
        assert len(h.controller.started_with) == 1

    def test_the_processing_tail_shows_finishing(self, harness: Any) -> None:
        h = _recording(harness)
        h.controller.state_value = SessionState.PROCESSING
        h.controller._track()
        h.bridge._tick()
        live = h.sender.last.live
        assert live is not None and live.phase == "finishing"
        assert f"Finishing {PATIENT_NAME} - Northside..." in h.screen.chrome_label.text()


def _indexed(controller: BridgeController, index: Any, note_id: str = NOTE) -> tuple[str, str]:
    """A retired recording of ``note_id`` in the reminder index, with the
    reference D2's registry gives it (startup reconstruction's shape)."""
    from scribe_desktop.context_rules import ReminderEntry

    session_id = secrets.token_hex(16)
    index.add(ReminderEntry(CLINIC_ID, note_id, session_id))
    return session_id, controller.register_session_ref(session_id)


class TestBanner:
    """Task 5.5 (D6): the reminder on reopening a note — ids and a count
    only, for the note the focused tab reports."""

    def _harness(self, harness: Any) -> tuple[Harness, Any]:
        from scribe_desktop.context_rules import ReminderIndex

        index = ReminderIndex()
        h: Harness = harness(reminders=index, open_review=lambda _sid: None)
        h.connect()
        return h, index

    def test_a_report_of_an_indexed_note_sets_the_banner(self, harness: Any) -> None:
        h, index = self._harness(harness)
        _older, _ = _indexed(h.controller, index)
        _newer, newer_ref = _indexed(h.controller, index)
        h.report()
        h.settle()
        banner = h.sender.last.banner
        assert banner is not None
        assert (banner.session_ref, banner.clinic_host, banner.note_id, banner.count) == (
            newer_ref,
            HOST,
            NOTE,
            2,
        )
        assert banner.patient_name is None  # a retired session keeps no name

    @pytest.mark.parametrize(
        "shape",
        [
            {"note_id": OTHER_NOTE},
            {"page": "other_cliniko"},
            {"host": OTHER_HOST},
            {"focused": False},
        ],
        ids=["other-note", "not-a-note", "off-allow-list", "not-focused"],
    )
    def test_no_banner_for_any_other_page(self, harness: Any, shape: dict[str, Any]) -> None:
        h, index = self._harness(harness)
        _indexed(h.controller, index)
        h.report(**shape)
        h.settle()
        assert h.sender.last.banner is None

    def test_the_banner_goes_with_its_entry(self, harness: Any) -> None:
        h, index = self._harness(harness)
        session_id, _ = _indexed(h.controller, index)
        h.report()
        h.settle()
        assert h.sender.last.banner is not None
        index.remove(session_id)
        h.bridge._tick()
        assert h.sender.last.banner is None

    def test_a_new_connection_re_renders_the_banner(self, harness: Any) -> None:
        """A service-worker restart is a new pipe connection: the full
        snapshot, banner included, is sent again once the tab reports."""
        h, index = self._harness(harness)
        _session_id, ref = _indexed(h.controller, index)
        h.report()
        h.settle()
        h.connect(2)
        h.seq = 0
        h.report(conn_id=2)
        h.settle()
        states = h.sender.states(2)
        assert states and states[-1].banner is not None
        assert states[-1].banner.session_ref == ref

    def test_no_index_no_banner(self, harness: Any) -> None:
        h: Harness = harness()
        h.connect()
        h.report()
        h.settle()
        assert h.sender.last.banner is None


class TestOpenReview:
    """Task 5.5 (D2): ``open_review`` goes through the session gate for a
    RETIRED session — the exact reference, still in the index."""

    def _harness(self, harness: Any, refusal: str | None = None) -> tuple[Harness, Any, list[str]]:
        from scribe_desktop.context_rules import ReminderIndex

        index = ReminderIndex()
        opened: list[str] = []

        def opener(session_id: str) -> str | None:
            opened.append(session_id)
            return refusal

        h: Harness = harness(reminders=index, open_review=opener)
        h.connect()
        return h, index, opened

    def test_the_banner_ref_opens_exactly_its_session(self, harness: Any) -> None:
        h, index, opened = self._harness(harness)
        older, older_ref = _indexed(h.controller, index)
        _newer, _ = _indexed(h.controller, index)
        h.command("open_review", session_ref=older_ref)
        assert opened == [older]  # the exact ref — never "the newest session"
        assert _refusal_of(h) is None

    def test_a_delayed_click_after_the_entry_went_is_refused(self, harness: Any) -> None:
        h, index, opened = self._harness(harness)
        session_id, ref = _indexed(h.controller, index)
        index.remove(session_id)  # completed, discarded, expired or opened meanwhile
        h.command("open_review", session_ref=ref)
        assert opened == []
        assert _refusal_of(h) == ("open_review", "session_changed")

    def test_an_unknown_or_forgotten_ref_is_refused(self, harness: Any) -> None:
        h, index, opened = self._harness(harness)
        session_id, ref = _indexed(h.controller, index)
        h.controller.forget_session_ref(session_id)  # the ref no longer resolves
        for candidate in (ref, secrets.token_urlsafe(18)):
            h.command("open_review", session_ref=candidate)
            assert _refusal_of(h) == ("open_review", "session_changed")
        assert opened == []

    def test_the_live_sessions_ref_is_not_an_unreviewed_one(self, harness: Any) -> None:
        h, index, opened = self._harness(harness)
        h.report()
        h.settle()
        h.start()
        live_ref = h.controller.session_ref
        assert live_ref is not None
        h.command("open_review", session_ref=live_ref)
        assert opened == []
        assert _refusal_of(h) == ("open_review", "session_changed")

    def test_refused_while_a_review_holds_the_lease(self, harness: Any) -> None:
        h, index, opened = self._harness(harness)
        _session_id, ref = _indexed(h.controller, index)
        h.controller.generating = True
        h.command("open_review", session_ref=ref)
        assert opened == []
        assert _refusal_of(h) == ("open_review", "review_in_progress")

    def test_refused_busy_while_a_draft_write_holds_the_live_session(
        self, harness: Any
    ) -> None:
        """Draft-write D9 (Task 5.2): adopting would retire the session a
        Cliniko write holds."""
        h, index, opened = self._harness(harness)
        session_id, ref = _indexed(h.controller, index)
        h.controller.writing_id = "held-by-a-write"
        h.command("open_review", session_ref=ref)
        assert opened == []
        assert _refusal_of(h) == ("open_review", "busy")
        h.controller.writing_id = None
        h.command("open_review", session_ref=ref)
        assert opened == [session_id]

    @pytest.mark.parametrize(
        ("state", "refused"),
        [
            (SessionState.RECORDING, True),
            (SessionState.PAUSED, True),
            (SessionState.PROCESSING, True),
            (SessionState.QUEUED, False),
        ],
    )
    def test_an_active_session_is_refused_before_the_opener(
        self, harness: Any, state: SessionState, refused: bool
    ) -> None:
        """Round 32 LOW-023: named before the window comes forward — a
        queued session is retired by the adoption instead."""
        h, index, opened = self._harness(harness)
        session_id, ref = _indexed(h.controller, index)
        h.controller.state_value = state
        h.command("open_review", session_ref=ref)
        if refused:
            assert opened == []
            assert _refusal_of(h) == ("open_review", "session_active")
        else:
            assert opened == [session_id] and _refusal_of(h) is None

    def test_the_openers_refusal_is_reported(self, harness: Any) -> None:
        h, index, opened = self._harness(harness, refusal="cannot_open")
        session_id, ref = _indexed(h.controller, index)
        h.command("open_review", session_ref=ref)
        assert opened == [session_id]
        assert _refusal_of(h) == ("open_review", "cannot_open")


class TestNothingLeaks:
    def test_the_bridge_never_logs_and_the_label_is_plain_text(
        self, harness: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        from PySide6.QtCore import Qt

        caplog.set_level(logging.DEBUG)
        h: Harness = harness()
        h.verified_report()
        h.start()
        h.connect(2)
        h.settle()
        h.bridge._tick()
        for record in caplog.records:
            message = record.getMessage()
            for secret in (PATIENT_NAME, PATIENT, NOTE, HOST):
                assert secret not in message
        assert h.screen.chrome_label.textFormat() == Qt.TextFormat.PlainText

    def test_a_display_name_is_one_bounded_line(self, harness: Any) -> None:
        long_name = {
            "id": PATIENT,
            "first_name": "Ann <b>" + "x" * 300,
            "preferred_first_name": None,
            "last_name": "Line\nBreak",
            "archived_at": None,
        }
        h = harness(transport=NoteTransport(patient=ok(long_name)))
        h.verified_report()
        report = h.sender.last.report
        assert report is not None and report.patient_name is not None
        assert len(report.patient_name) <= 120
        assert "\n" not in report.patient_name and " " not in report.patient_name


def test_a_held_start_writes_nothing_through_the_real_controller(
    qapp: Any, tmp_path: Path
) -> None:
    """Installation plan round 36 MED-001: the warm-up's refusal comes
    BEFORE ``SessionController.start`` — no audit ``begin``, no session
    folder, the state still idle and the desktop consent tick kept."""
    from scribe_desktop.audio_capture import MockCaptureBackend
    from scribe_desktop.session import SessionController

    class _Audit:
        def __init__(self) -> None:
            self.begun: list[str] = []

        def begin(self, session_id: str, **kwargs: Any) -> None:
            self.begun.append(session_id)

        def record_start_failed(self, session_id: str) -> None:
            pass

    audit = _Audit()
    root = tmp_path / "sessions"
    controller = SessionController(MockCaptureBackend(), sessions_root=root, audit=audit)
    screen = SessionScreen(
        controller,
        device_provider=lambda: 0,
        transcriber_factory=lambda: (lambda _d, _c: _document()),
    )
    screen.set_start_hold(lambda: True)
    screen.consent_checkbox.setChecked(True)
    screen.on_start()
    assert screen.message_label.text() == models.START_GETTING_READY_MESSAGE
    assert audit.begun == []
    assert not root.exists() or list(root.iterdir()) == []
    assert controller.state is SessionState.IDLE
    assert screen.consent_checkbox.isChecked()
    screen.deleteLater()
