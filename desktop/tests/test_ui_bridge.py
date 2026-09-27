"""The Chrome bridge (Cliniko workflow safeguards plan Task 4.5): reports in,
verification on a worker, commands to the Session screen's slots, one
``state`` snapshot out. Offscreen; the pipe is a recording fake sender,
every Cliniko answer comes from ``NoteTransport`` and every key from memory
— no socket, no named pipe."""

from __future__ import annotations

import logging
import os
import secrets
import threading
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
from scribe_desktop.encounter import (  # noqa: E402
    ConsentAttestation,
    EncounterContext,
    Verification,
    Verified,
    unlinked_consent,
)
from scribe_desktop.protocol import (  # noqa: E402
    Envelope,
    StatePayload,
    make_pipe_envelope,
    typed_payload,
)
from scribe_desktop.session import RecordingSession, SessionState  # noqa: E402
from scribe_desktop.transcription import LiveFailure, LiveFailureKind  # noqa: E402
from scribe_desktop.ui import models  # noqa: E402
from scribe_desktop.ui.bridge import ChromeBridge  # noqa: E402
from scribe_desktop.ui.session_screen import SessionScreen  # noqa: E402
from test_ui_screens import FakeController, _process_until  # noqa: E402

PATIENT_NAME = "Jan Citizen"  # encounter_fakes.PATIENT_BODY's display name
TAB = 412
OTHER_TAB = 413


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


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


class Harness:
    def __init__(
        self,
        qapp: Any,
        tmp_path: Path,
        *,
        transport: Any = None,
        device: int | None = 1,
    ) -> None:
        self.qapp = qapp
        self.transport = transport if transport is not None else NoteTransport()
        self.registry = make_registry(tmp_path, transport=self.transport)
        self.controller = BridgeController()
        self.screen = SessionScreen(self.controller, device_provider=lambda: device)
        # A long interval: the tests drive publish/_tick themselves.
        self.bridge = ChromeBridge(
            self.controller, self.screen, self.registry, publish_interval_ms=60_000
        )
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
            payload.update(patient_id=PATIENT, note_id=note_id)
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
        assert models.CHROME_HANDS_FREE_LINE in text
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

    def test_no_microphone_is_refused(self, harness: Any) -> None:
        h = harness(device=None)
        h.verified_report()
        h.start()
        self._refused(h, "no_microphone")

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

    @pytest.mark.parametrize("action", ["resume_previous", "open_review"])
    def test_phase_5_actions_are_not_available(self, harness: Any, action: str) -> None:
        h = harness()
        h.connect()
        h.command(action, session_ref=secrets.token_urlsafe(18))
        assert self._refusal(h) == (action, "not_available")
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
        h.bridge._tick()
        live = h.sender.last.live
        assert live is not None and live.recorded_seconds == 42
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
