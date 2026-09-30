"""Step 10: offscreen smoke tests for the UI screens — construction,
state-driven enablement, and signal wiring against fakes. No real audio
or ML in CI (mock backends and canned transcripts only)."""

from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import scribe_desktop.note_config as note_config_module  # noqa: E402
from scribe_desktop.audio_capture import AudioDevice  # noqa: E402
from scribe_desktop.benchmark import BenchmarkResult  # noqa: E402
from scribe_desktop.draft_write import WriteRecordStatus  # noqa: E402
from scribe_desktop.encounter import (  # noqa: E402
    ConsentAttestation,
    EncounterContext,
    Verification,
    linked_consent,
    unlinked_consent,
)
from scribe_desktop.enrolment import (  # noqa: E402
    EnrolmentCancelledError,
    EnrolmentProgress,
    EnrolmentTooShortError,
)
from scribe_desktop.note import (  # noqa: E402
    CANONICAL_SECTION_KEYS,
    CLINICIAN_OWNED_SECTIONS,
    NOTE_WARNING_SEVERITY,
    SECTION_TITLES,
    ConfirmationDecision,
    ExtractiveNoteProvider,
    GeneratedNote,
    ProposalResolution,
    compose_draft,
    finalise_note,
    manual_assertion_id,
    render_note,
    text_digest,
)
from scribe_desktop.note_config import (  # noqa: E402
    AUTOFILL_RULES_FILENAME,
    LEARNED_RULE_AUTO_CONFIRM_AFTER,
    LEARNED_SIDECAR_FILENAME,
    RULE_WORDING_MANY_CLAIMS,
    RULE_WORDING_TOO_LONG,
    SECTION_CUES_FILENAME,
    AutofillRule,
    LearnedRuleCandidate,
    NoteConfig,
    PrefillSeedAssertion,
    PrefillTemplate,
    SectionMapping,
    TemplateProfile,
    TemplateTarget,
    append_learned_rules,
    append_user_cues,
    load_learned_phrases,
    load_learned_rule_entries,
    load_learned_rules,
    load_note_config,
    record_rule_outcomes,
)
from scribe_desktop.secure_storage import SessionCrypto  # noqa: E402
from scribe_desktop.session import (  # noqa: E402
    ConsentRequiredError,
    EnrolmentLease,
    GenerationInProgressError,
    GenerationLease,
    RecordingSession,
    SessionActivityError,
    SessionState,
)
from scribe_desktop.session_store import (  # noqa: E402
    AUDIO_FILENAME,
    KEY_FILENAME,
    SessionChunkStore,
    StoreWriteError,
)
from scribe_desktop.transcription import (  # noqa: E402
    LIVE_SPEAKER_PENDING,
    SPEAKER_1,
    SPEAKER_2,
    LiveTranscriber,
    RecoveryOutcome,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
    is_number_token,
)
from scribe_desktop.ui import models  # noqa: E402


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _process_until(qapp: Any, predicate: Callable[[], bool], timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _document() -> TranscriptDocument:
    return TranscriptDocument(
        session_id=uuid.uuid4().hex,
        created_at=datetime.now(UTC),
        model_name="small",
        sample_rate=16_000,
        transcript_segments=(
            TranscriptSegment(
                start_seconds=0.0,
                end_seconds=2.0,
                speaker="speaker_1",
                transcript_words=(
                    TranscriptWord(
                        word_text="Hello",
                        start_seconds=0.0,
                        end_seconds=0.5,
                        probability=0.95,
                        uncertain=False,
                    ),
                    TranscriptWord(
                        word_text="Margaret",
                        start_seconds=0.6,
                        end_seconds=1.0,
                        probability=0.40,
                        uncertain=True,
                    ),
                ),
            ),
        ),
    )


class FakeBackend:
    def __init__(self, devices: list[AudioDevice] | None = None) -> None:
        self.devices = devices if devices is not None else [
            AudioDevice(device_id=1, name="Mic A", is_default=False),
            AudioDevice(device_id=7, name="Mic B", is_default=True),
        ]

    def list_input_devices(self) -> list[AudioDevice]:
        return list(self.devices)

    def open_stream(self, device_id: int, on_block: Any, on_error: Any) -> Any:
        # Smoke round 21: the microphone screen MAY open an idle-monitor
        # stream; this fake refuses, exercising the visible-failure path.
        raise AssertionError("fake backend cannot open streams")


class FakeController:
    """Duck-typed SessionControllerLike recording every call."""

    def __init__(self) -> None:
        self.state_value = SessionState.IDLE
        self.level_value = 0.25
        self.calls: list[tuple[Any, ...]] = []
        self.transcribe_error: Exception | None = None
        self.session_value: RecordingSession | None = None
        # Task 6.3: when set, every lease-guarded custody op refuses with it
        # (simulates a held generation lease — or, round 30, a held discard
        # reservation — in the real controller).
        self.generation_error: Exception | None = None
        self.lease: GenerationLease | None = None
        # Round 30: ids an in-flight discard has reserved (the real
        # controller's reserved_session_ids source).
        self.reserved_ids: frozenset[str] = frozenset()
        # Phase 7: the (directory, crypto) the scoped generation op hands to
        # its action. Tests point these at a real session dir when they want
        # the action (write_note) to actually run.
        self.generation_dir = Path("unused")
        self.generation_crypto: SessionCrypto | None = None
        # Practitioner-profile plan D15: True while a voice enrolment holds
        # the microphone (the real controller's `enrolling` property).
        self.enrolling = False
        # Phase 3: the enrolment activity as the Practitioner tab drives it —
        # a refusal to raise, the held lease, the registered blocker, and a
        # hook that observes the UI at the exact moment the lease is released.
        self.enrolment_error: Exception | None = None
        self.enrolment_lease: EnrolmentLease | None = None
        self.blocker: Callable[[], str | None] | None = None
        self.end_enrolment_hook: Callable[[], None] | None = None
        # Cliniko safeguards Task 3.3: the consent and context of every Start.
        self.started_with: list[tuple[ConsentAttestation, EncounterContext | None]] = []
        # Task 4.5: what the Chrome bridge reads (SessionControllerLike).
        self.session_ref: str | None = None
        self.recorded_seconds = 0
        self.live_failure: Any = None
        # Task 7.2 (D7): whether a live transcriber is attached.
        self.live_transcription_attached = False
        self.generating = False
        self.forgotten_refs: list[str] = []
        # Task 5.5: D2's registry for sessions other than the tracked one.
        self.refs: dict[str, str] = {}
        # Draft-write Task 3.3: the live session's write-record status (or an
        # exception to raise) that the Transcript screen's write_pending
        # refusal reads.
        self.write_status: WriteRecordStatus | Exception = WriteRecordStatus("none")

    def write_record_status(self, session_id: str) -> WriteRecordStatus:
        self.calls.append(("write_record_status", session_id))
        if isinstance(self.write_status, Exception):
            raise self.write_status
        return self.write_status

    @property
    def state(self) -> SessionState:
        return self.state_value

    @property
    def level(self) -> float:
        return self.level_value

    @property
    def session(self) -> RecordingSession | None:
        return self.session_value

    def _session(self) -> RecordingSession:
        return RecordingSession(consent=unlinked_consent()).with_state(self.state_value)

    def start(
        self,
        device_id: int,
        *,
        consent: ConsentAttestation,
        context: EncounterContext | None = None,
    ) -> RecordingSession:
        # Mirrors the real controller's Constraint-4 refusal.
        if not isinstance(consent, ConsentAttestation):
            raise ConsentRequiredError("start refused: no recording consent was given")
        self.calls.append(("start", device_id))
        self.started_with.append((consent, context))
        self.state_value = SessionState.RECORDING
        return self._session()

    def pause(self) -> RecordingSession:
        self.calls.append(("pause",))
        self.state_value = SessionState.PAUSED
        return self._session()

    def resume(self) -> RecordingSession:
        self.calls.append(("resume",))
        self.state_value = SessionState.RECORDING
        return self._session()

    def finish(self) -> RecordingSession:
        self.calls.append(("finish",))
        self.state_value = SessionState.PROCESSING
        return self._session()

    def transcribe(self, transcriber: Callable[[Path, Any], object]) -> RecordingSession:
        self.calls.append(("transcribe",))
        try:
            transcriber(Path("unused"), SessionCrypto())
        except Exception:
            self.state_value = SessionState.FAILED
            raise
        if self.transcribe_error is not None:
            self.state_value = SessionState.FAILED
            raise self.transcribe_error
        self.state_value = SessionState.QUEUED
        return self._session()

    def complete(self) -> RecordingSession:
        self.calls.append(("complete",))
        self.state_value = SessionState.WRITTEN
        return self._session()

    def complete_without_note(self, lease: GenerationLease) -> RecordingSession:
        self.calls.append(("complete_without_note",))
        if self.generation_error is not None:
            raise self.generation_error  # failure -> lease stays held (not consumed)
        if self.lease is lease:
            self.lease = None  # consume the lease only on success
        self.state_value = SessionState.WRITTEN
        return self._session()

    def complete_deleting_saved_note(self) -> RecordingSession:
        self.calls.append(("complete_deleting_saved_note",))
        if self.generation_error is not None:
            raise self.generation_error
        self.state_value = SessionState.WRITTEN
        return self._session()

    def discard(self) -> RecordingSession:
        self.calls.append(("discard",))
        self.state_value = SessionState.DISCARDED
        return self._session()

    def active_session_ids(self) -> frozenset[str]:
        return frozenset()

    def forget_session_ref(self, session_id: str) -> None:
        # Task 5.3: kept apart from `calls`, whose exact lists tests pin.
        self.forgotten_refs.append(session_id)
        for ref in [r for r, sid in self.refs.items() if sid == session_id]:
            del self.refs[ref]

    # Task 5.5 (D2): the registry for indexed sessions, apart from `calls`.
    def session_ref_for(self, session_id: str) -> str | None:
        return next((r for r, sid in self.refs.items() if sid == session_id), None)

    def register_session_ref(self, session_id: str) -> str:
        ref = self.session_ref_for(session_id)
        if ref is None:
            ref = secrets.token_urlsafe(18)
            self.refs[ref] = session_id
        return ref

    def resolve_session_ref(self, session_ref: str) -> str | None:
        if self.session_ref is not None and session_ref == self.session_ref:
            session = self.session_value
            return session.session_id if session is not None else None
        return self.refs.get(session_ref)

    # Practitioner-profile plan D15: the enrolment activity.

    def begin_enrolment(self) -> EnrolmentLease:
        self.calls.append(("begin_enrolment",))
        if self.enrolment_error is not None:
            raise self.enrolment_error
        lease = EnrolmentLease()
        self.enrolment_lease = lease
        self.enrolling = True
        return lease

    def end_enrolment(self, lease: EnrolmentLease) -> None:
        self.calls.append(("end_enrolment",))
        if self.end_enrolment_hook is not None:
            self.end_enrolment_hook()
        if self.enrolment_lease is lease:
            self.enrolment_lease = None
            self.enrolling = False

    def set_enrolment_blocker(self, blocker: Callable[[], str | None] | None) -> None:
        self.calls.append(("set_enrolment_blocker",))
        self.blocker = blocker

    # Note-learning plan D2: the live worker handover (None = batch as today)
    # and the factory registration.

    def claim_live_transcriber(self) -> Any:
        self.calls.append(("claim_live_transcriber",))
        return None

    def set_live_transcriber_factory(self, factory: Callable[[], Any] | None) -> None:
        self.calls.append(("set_live_transcriber_factory",))
        self.live_transcriber_factory = factory

    # Task 6.3: the lease + the lease-aware recovered-custody coordinator.

    def begin_generation(self) -> GenerationLease:
        self.calls.append(("begin_generation",))
        if self.generation_error is not None:
            raise self.generation_error
        lease = GenerationLease()
        self.lease = lease
        return lease

    def end_generation(self, lease: GenerationLease) -> None:
        self.calls.append(("end_generation",))
        if self.lease is lease:
            self.lease = None

    def reserved_session_ids(self) -> frozenset[str]:
        return self.reserved_ids

    def custody_protected_ids(self) -> frozenset[str]:
        # Mirrors the real controller's atomic snapshot semantics (round 31):
        # reservations plus the non-terminal live session.
        ids = self.reserved_ids
        if self.session_value is not None and not self.session_value.is_terminal:
            ids = ids | {self.session_value.session_id}
        return ids

    def complete_recovered(self, directory: Path, crypto: SessionCrypto) -> None:
        self.calls.append(("complete_recovered", directory))
        if self.generation_error is not None:
            raise self.generation_error
        crypto.destroy()

    def discard_recovered(self, directory: Path, crypto: SessionCrypto | None) -> None:
        self.calls.append(("discard_recovered", directory))
        if self.generation_error is not None:
            raise self.generation_error
        if crypto is not None:
            crypto.destroy()

    def destroy_recovered_crypto(self, crypto: SessionCrypto) -> None:
        self.calls.append(("destroy_recovered_crypto",))
        if self.generation_error is not None:
            raise self.generation_error
        crypto.destroy()

    def with_generation_custody(
        self, lease: GenerationLease, action: Callable[[Path, SessionCrypto], Any]
    ) -> Any:
        self.calls.append(("with_generation_custody",))
        if self.generation_error is not None:
            raise self.generation_error
        crypto = self.generation_crypto if self.generation_crypto is not None else SessionCrypto()
        return action(self.generation_dir, crypto)

    # Draft-write plan D9 (Task 4.1): the write reservation. `writing_id` is
    # the id a held reservation names — tests set it to simulate a write in
    # flight. Task 4.2: the seen-mode Complete re-acquires a reservation
    # (`reserve_write`) and completes under it (`complete_after_write`);
    # `reserve_error` / `complete_after_write_error` make either refuse, and
    # `write_releases` counts the releases of a HELD token (apart from
    # `calls`, whose exact lists tests pin).

    writing_id: str | None = None
    held_reservation: Any = None
    reserve_error: Exception | None = None
    complete_after_write_error: Exception | None = None
    write_releases = 0
    # Task 5.2: the (directory, crypto) the write's scoped custody hands its
    # action — tests use a ``WriteStore`` seam, so no real session is read.
    write_dir = Path("unused")

    def reserve_write(self, session_id: str) -> Any:
        self.calls.append(("reserve_write", session_id))
        if self.reserve_error is not None:
            raise self.reserve_error
        reservation = _FakeWriteReservation(self, session_id)
        self.held_reservation = reservation
        self.writing_id = session_id
        return reservation

    def complete_after_write(self, reservation: Any) -> RecordingSession:
        self.calls.append(("complete_after_write",))
        assert reservation is self.held_reservation, "completion needs the held token"
        if self.complete_after_write_error is not None:
            raise self.complete_after_write_error  # the reservation stays held
        self.held_reservation = None
        self.writing_id = None
        self.state_value = SessionState.WRITTEN
        return self._session()

    def with_write_custody(
        self, reservation: Any, action: Callable[[Path, SessionCrypto], Any]
    ) -> Any:
        # As the real accessor: only the HELD reservation reaches the files.
        self.calls.append(("with_write_custody",))
        if reservation is None or reservation is not self.held_reservation:
            raise SessionActivityError("scoped write access requires the held write reservation")
        return action(self.write_dir, SessionCrypto())

    def writing_session_id(self) -> str | None:
        return self.writing_id

    # SIMP-016 (Task 4.2): the reference prune's two reads.

    def live_session_ids(self) -> frozenset[str]:
        session = self.session_value
        return frozenset({session.session_id}) if session is not None else frozenset()

    def referenced_session_ids(self) -> frozenset[str]:
        return frozenset(self.refs.values())


class _FakeWriteReservation:
    """The fake's reservation token: ``release`` drops it only while it is
    the held one (idempotent, like the real ``WriteReservation``)."""

    def __init__(self, controller: FakeController, session_id: str) -> None:
        self._controller = controller
        self.session_id = session_id

    def release(self) -> None:
        controller = self._controller
        if controller.held_reservation is self:
            controller.held_reservation = None
            controller.writing_id = None
            controller.write_releases += 1


# ---------------------------------------------------------------------------
# Microphone screen.
# ---------------------------------------------------------------------------


class TestMicrophoneScreen:
    def test_devices_populated_and_default_selected(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.ui.microphone import MicrophoneScreen

        screen = MicrophoneScreen(
            FakeController(), FakeBackend(), benchmark_runner=list, profile_root=tmp_path
        )
        assert screen.device_combo.count() == 2
        assert screen.selected_device_id() == 7  # default device preferred
        screen.deleteLater()

    def test_level_meter_polls_controller_while_recording(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.microphone import MicrophoneScreen

        controller = FakeController()
        controller.state_value = SessionState.RECORDING
        controller.level_value = 0.5
        screen = MicrophoneScreen(
            controller, FakeBackend(), benchmark_runner=list, profile_root=tmp_path
        )
        screen._poll_level()
        assert screen.level_bar.value() == 50
        assert not screen.level_status_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_idle_monitor_streams_live_level(self, qapp: Any, tmp_path: Path) -> None:
        """Smoke round 21: selecting a device while IDLE must give live
        level feedback from a monitoring stream (not controller.level)."""
        from scribe_desktop.audio_capture import MockCaptureBackend
        from scribe_desktop.ui.microphone import MicrophoneScreen

        backend = MockCaptureBackend(
            [AudioDevice(device_id=3, name="Mock Mic", is_default=True)]
        )
        screen = MicrophoneScreen(
            FakeController(), backend, benchmark_runner=list, profile_root=tmp_path
        )
        screen._poll_level()  # opens the monitor
        assert backend.stream_open and backend.opened_device_id == 3
        backend.feed(b"\x00\x40" * 1600)  # loud-ish PCM16 block
        screen._poll_level()
        assert screen.level_bar.value() > 0
        assert not screen.level_status_label.isVisibleTo(screen)
        screen.stop_monitor()
        assert not backend.stream_open
        screen.deleteLater()

    def test_monitor_open_failure_shows_actionable_message(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.microphone import MicrophoneScreen

        screen = MicrophoneScreen(
            FakeController(), FakeBackend(), benchmark_runner=list, profile_root=tmp_path
        )
        screen._poll_level()
        assert screen.level_bar.value() == 0
        assert screen.level_status_label.isVisibleTo(screen)
        assert "Privacy" in screen.level_status_label.text()
        # The failure is latched: polling again must not hammer the device.
        screen._poll_level()
        assert screen.level_status_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_monitor_silence_shows_privacy_hint(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.audio_capture import MockCaptureBackend
        from scribe_desktop.ui import microphone as mic_module
        from scribe_desktop.ui.microphone import MicrophoneScreen

        backend = MockCaptureBackend(
            [AudioDevice(device_id=3, name="Mock Mic", is_default=True)]
        )
        screen = MicrophoneScreen(
            FakeController(), backend, benchmark_runner=list, profile_root=tmp_path
        )
        screen._poll_level()
        for _ in range(mic_module._SILENCE_POLLS):
            backend.feed(b"\x00\x00" * 1600)  # pure silence
            screen._poll_level()
        assert screen.level_status_label.isVisibleTo(screen)
        assert "No signal" in screen.level_status_label.text()
        # Signal returning clears the hint.
        backend.feed(b"\x00\x40" * 1600)
        screen._poll_level()
        assert not screen.level_status_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_poll_tick_during_enrolment_keeps_the_monitor_closed(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Practitioner-profile plan D15: a one-time monitor stop would be
        undone by the next poll tick, so the tick itself must not reopen the
        stream while the enrolment activity is held — and must resume once
        it is released."""
        from scribe_desktop.audio_capture import MockCaptureBackend
        from scribe_desktop.ui.microphone import MicrophoneScreen

        controller = FakeController()
        backend = MockCaptureBackend(
            [AudioDevice(device_id=3, name="Mock Mic", is_default=True)]
        )
        screen = MicrophoneScreen(
            controller, backend, benchmark_runner=list, profile_root=tmp_path
        )
        screen._poll_level()
        assert backend.stream_open
        controller.enrolling = True
        screen._poll_level()  # the tick closes the monitor
        assert not backend.stream_open
        assert screen.level_bar.value() == 0
        screen._poll_level()  # and does NOT reopen it while enrolling
        assert not backend.stream_open
        assert not screen.level_status_label.isVisibleTo(screen)  # not an error state
        controller.enrolling = False
        screen._poll_level()
        assert backend.stream_open and backend.opened_device_id == 3
        screen.stop_monitor()
        screen.deleteLater()

    def test_benchmark_refused_while_enrolling(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.ui.microphone import MicrophoneScreen

        controller = FakeController()
        controller.enrolling = True
        screen = MicrophoneScreen(
            controller, FakeBackend(), benchmark_runner=list, profile_root=tmp_path
        )
        screen.on_run_benchmark()
        assert "enrolment" in screen.benchmark_output.toPlainText()
        assert not screen.is_busy
        assert screen.benchmark_button.isEnabled()
        screen.deleteLater()

    def test_monitor_device_loss_surfaces_and_recording_takes_over(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.audio_capture import MockCaptureBackend
        from scribe_desktop.ui.microphone import MicrophoneScreen

        controller = FakeController()
        backend = MockCaptureBackend(
            [AudioDevice(device_id=3, name="Mock Mic", is_default=True)]
        )
        screen = MicrophoneScreen(
            controller, backend, benchmark_runner=list, profile_root=tmp_path
        )
        screen._poll_level()
        backend.fail()  # device lost mid-monitor
        screen._poll_level()
        assert screen.level_status_label.isVisibleTo(screen)
        assert "Privacy" in screen.level_status_label.text()
        # Recording state: meter switches to controller.level, monitor closed.
        controller.state_value = SessionState.RECORDING
        controller.level_value = 0.8
        screen._poll_level()
        assert screen.level_bar.value() == 80
        assert not screen.level_status_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_model_report_panel_shows_status_lines(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.ui.microphone import MicrophoneScreen

        screen = MicrophoneScreen(
            FakeController(), FakeBackend(), benchmark_runner=list, profile_root=tmp_path
        )
        text = screen.model_status_label.text()
        assert "Whisper model" in text and "VAD model" in text
        screen.deleteLater()

    def test_model_status_poll_does_not_read_the_profile(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 51 MED-001: the 5 s model-status poll (`refresh_model_status`,
        also what a finished benchmark calls) re-renders the model-FILE lines
        from stats and the CACHED profile line; only `refresh_profile_line`
        (construction via `refresh_devices`, a device refresh, the Practitioner
        tab's `profile_changed`) reads the profile — EXCEPT that a poll which
        finds the speaker model's presence flipped since the last read re-reads
        once (peer round 55 PR-REG-006: the line's text folds that stat in, so
        the report must not keep saying the model is absent after
        setup-models ran); steady presence still reads nothing."""
        from scribe_desktop.ui.microphone import MicrophoneScreen

        reads: list[Path | None] = []
        real = models.attribution_readiness
        present = {"value": False}

        def counted(*, profile_root: Path | None = None, kind: Any = None) -> Any:
            reads.append(profile_root)
            return real(profile_root=profile_root) if kind is None else real(
                profile_root=profile_root, kind=kind
            )

        monkeypatch.setattr(models, "attribution_readiness", counted)
        monkeypatch.setattr(models, "speaker_embedder_available", lambda *a: present["value"])
        screen = MicrophoneScreen(
            FakeController(), FakeBackend(), benchmark_runner=list, profile_root=tmp_path
        )
        assert reads == [tmp_path]  # construction: exactly one read, off the default store
        screen.refresh_model_status()
        screen.refresh_model_status()
        screen._on_benchmark_done([])
        assert reads == [tmp_path]  # the poll's slot and a finished benchmark read nothing
        lines = screen.model_status_label.text().split("\n")
        assert len(lines) == 4
        assert "MISSING" in lines[2]
        assert lines[3] == models.PROFILE_NOT_ENROLLED_LINE
        screen.refresh_profile_line()
        assert reads == [tmp_path, tmp_path]
        screen.refresh_devices()
        assert reads == [tmp_path, tmp_path, tmp_path]
        # The model file appears (setup-models ran): the next poll re-reads ONCE ...
        present["value"] = True
        screen.refresh_model_status()
        assert len(reads) == 4
        assert "installed" in screen.model_status_label.text().split("\n")[2]
        # ... and steady presence reads nothing again; a removal is a transition too.
        screen.refresh_model_status()
        screen.refresh_model_status()
        assert len(reads) == 4
        present["value"] = False
        screen.refresh_model_status()
        assert len(reads) == 5
        screen.refresh_model_status()
        assert len(reads) == 5
        screen.deleteLater()

    def test_benchmark_failure_threshold_shows_warning(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.microphone import MicrophoneScreen

        slow = BenchmarkResult(
            model_name="small",
            audio_seconds=50.0,
            load_seconds=1.0,
            transcribe_seconds=100.0,
            rtf=2.0,
            peak_memory_bytes=500 * 2**20,
            word_count=100,
        )
        screen = MicrophoneScreen(
            FakeController(),
            FakeBackend(),
            benchmark_runner=lambda: [slow],
            profile_root=tmp_path,
        )
        screen.on_run_benchmark()
        assert _process_until(qapp, lambda: screen.benchmark_button.isEnabled())
        assert "FAIL" in screen.benchmark_output.toPlainText()
        assert screen.benchmark_warning_label.isVisibleTo(screen)
        warning = screen.benchmark_warning_label.text()
        assert "no cloud fallback" in warning
        screen.deleteLater()

    def test_benchmark_ok_shows_no_warning(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.ui.microphone import MicrophoneScreen

        fast = BenchmarkResult(
            model_name="small",
            audio_seconds=50.0,
            load_seconds=1.0,
            transcribe_seconds=5.0,
            rtf=0.1,
            peak_memory_bytes=500 * 2**20,
            word_count=100,
        )
        screen = MicrophoneScreen(
            FakeController(),
            FakeBackend(),
            benchmark_runner=lambda: [fast],
            profile_root=tmp_path,
        )
        screen.on_run_benchmark()
        assert _process_until(qapp, lambda: screen.benchmark_button.isEnabled())
        assert "OK" in screen.benchmark_output.toPlainText()
        assert not screen.benchmark_warning_label.isVisibleTo(screen)
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Practitioner tab (practitioner-profile plan Phase 3, Task 3.1).
# ---------------------------------------------------------------------------

windows_only = pytest.mark.skipif(
    sys.platform != "win32", reason="DPAPI custody is Windows-only"
)


class _Running:
    """Duck-typed stand-in for a `TaskThread` that never finishes — the
    close-guard tests need `is_busy` True without starting a real worker."""

    def isRunning(self) -> bool:
        return True

    def finish(self) -> None:
        return None


class _StubEmbedder:
    """Identity only: the screen builds the embedder on the worker thread but
    never calls `embed` itself (the `embed` seam does)."""

    model_id = "stub-embedder-v1"
    model_sha256 = ""
    embedding_dim = 4

    def embed(self, pcm16: bytes) -> Any:
        raise AssertionError("embed is not called by the screen")


class _FakeCapture:
    """The `capture` seam: reports one progress tick (on the worker thread,
    exactly as `record_enrolment` does), then returns PCM, raises, or holds
    until the test releases it / a Stop is requested."""

    def __init__(
        self,
        *,
        pcm: bytes = b"\x00\x40" * 16_000,
        error: Exception | None = None,
        hold: bool = False,
    ) -> None:
        self.pcm = pcm
        self.error = error
        self.hold = hold
        self.calls: list[tuple[int]] = []
        self.hold_event = threading.Event()

    def __call__(
        self,
        backend: Any,
        device_id: int,
        on_progress: Callable[[EnrolmentProgress], None],
        should_stop: Callable[[], bool],
    ) -> bytes:
        self.calls.append((device_id,))
        on_progress(EnrolmentProgress(speech_seconds=12.0, captured_seconds=20.0, level=0.4))
        if self.hold:
            while not self.hold_event.wait(0.01):
                if should_stop():
                    raise EnrolmentCancelledError("enrolment cancelled")
        if self.error is not None:
            raise self.error
        return self.pcm


def _local_readiness(root: Path) -> Callable[[], Any]:
    """The readiness seam over the REAL profile store, WITHOUT the shipped
    identity pin: these tests enrol with `_StubEmbedder`, whose model id is
    not the shipped one, so `models.attribution_readiness` would report every
    saved profile as needing re-enrolment. The present/reason shape is the
    same (`models.PROFILE_UNUSABLE_REASON` for an unusable blob)."""
    from scribe_desktop.practitioner_profile import ProfileUnusableError, load_profile

    def readiness() -> Any:
        try:
            profile = load_profile(root=root)
        except ProfileUnusableError as exc:
            return models.AttributionReadiness(
                profile_present=True,
                profile=None,
                reason=models.PROFILE_UNUSABLE_REASON.format(reason=exc.reason),
            )
        if profile is None:
            return models.AttributionReadiness(
                profile_present=False, profile=None, reason=None
            )
        return models.AttributionReadiness(
            profile_present=True, profile=profile, reason=None
        )

    return readiness


def _practitioner_screen(
    controller: FakeController, backend: Any, tmp_path: Path, **overrides: Any
) -> Any:
    from scribe_desktop.ui.practitioner import PractitionerScreen

    kwargs: dict[str, Any] = {
        "profile_root": tmp_path,
        # Peer round 55 PR-LOW-041: the tab reads its cue file at construction,
        # so the helper roots that under tmp_path too (overrides still win) —
        # and, since the note-learning plan's Phase 3, the learned-style
        # store it stats for the writing-style options.
        "config_root": tmp_path / "config",
        "style_root": tmp_path / "style",
        # Phase H round 24 MED-006: the language model's presence is pinned
        # ABSENT through both seams — the tab's own probe and the options
        # provider — never read from this host.
        "language_model_available": lambda: False,
        "style_options_provider": lambda: models.style_options(
            style_root=tmp_path / "style", model_available=lambda: False
        ),
        "embedder_factory": lambda kind: _StubEmbedder(),
        "embedder_available": lambda kind: True,
        "vad_available": lambda: True,
        "embed": lambda pcm, embedder: ((0.6, 0.8, 0.0, 0.0), 31.0),
        "confirm_delete": lambda: True,
        "readiness_provider": _local_readiness(tmp_path),
    }
    kwargs.update(overrides)
    return PractitionerScreen(controller, backend, **kwargs)


class _NoKeyStore:
    """A key store no MainWindow test may touch."""

    def store(self, clinic_id: str, secret_name: str, value: str) -> None:
        pytest.fail("a MainWindow test stored a clinic key")

    def retrieve(self, clinic_id: str, secret_name: str) -> str | None:
        pytest.fail("a MainWindow test read a clinic key")

    def delete(self, clinic_id: str, secret_name: str) -> None:
        pytest.fail("a MainWindow test deleted a clinic key")


class _NoTransport:
    """A Cliniko transport no MainWindow test may call."""

    def request(self, *args: Any, **kwargs: Any) -> Any:
        pytest.fail("a MainWindow test called Cliniko")


def _main_window(tmp_path: Path, controller: Any | None = None, **overrides: Any) -> Any:
    """Every `MainWindow` a test builds (Phase H round 24 MED-006): the
    learned-style store and the language model's presence are SEAMS — a
    test never decrypts the real `style.enc` or stats the real 2.3 GiB
    model (docs/lessons.md 2026-09-24); overrides still win."""
    from scribe_desktop.clinics import ClinicRegistry
    from scribe_desktop.ui.main_window import MainWindow

    kwargs: dict[str, Any] = {
        "sessions_root": tmp_path,
        "profile_root": tmp_path,
        "config_root": tmp_path / "config",
        "style_root": tmp_path / "style",
        "language_model_available": lambda: False,
        # Cliniko safeguards Task 2.2: never the real clinics.json, never the
        # real Credential Manager, and a transport that fails any request.
        "clinic_registry": ClinicRegistry(
            tmp_path / "clinics.json", storage=_NoKeyStore(), transport=_NoTransport()
        ),
        "benchmark_runner": list,
        "recovery_runner": lambda d: pytest.fail("not called"),
    }
    kwargs.update(overrides)
    owner = controller if controller is not None else FakeController()
    return MainWindow(owner, FakeBackend(), **kwargs)


def _enrol(qapp: Any, screen: Any, capture: _FakeCapture) -> None:
    """Tick consent, record, and wait for the lease to be released."""
    screen.consent_checkbox.setChecked(True)
    screen.on_record()
    assert _process_until(qapp, lambda: not screen.is_busy and screen._lease is None)
    assert capture.calls, "the capture seam was never called"


def _make_consent_stale(root: Path, version: str = "consent-v1") -> Any:
    """Re-save the stored profile with an OLDER consent record (Task 5.0's
    older-version case; ``consent-v2`` since the note-learning plan's consent
    v3): the SAME key and the SAME vector, an older consent text. Returns the
    profile as it now reads back from disk."""
    from scribe_desktop.practitioner_profile import ConsentRecord, load_profile, save_profile

    profile = load_profile(root=root)
    assert profile is not None
    save_profile(
        profile.model_copy(
            update={
                "consent": ConsentRecord(
                    accepted_at=profile.consent.accepted_at,
                    consent_text_version=version,
                    learning_opt_in=profile.consent.learning_opt_in,
                )
            }
        ),
        root=root,
    )
    stale = load_profile(root=root)
    assert stale is not None
    return stale


class TestPractitionerScreen:
    def test_constructs_with_consent_text_verbatim_and_nothing_enabled(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.practitioner import NO_LEARNED_PHRASES_TEXT

        screen = _practitioner_screen(
            FakeController(), FakeBackend(), tmp_path, config_root=tmp_path / "config"
        )
        assert screen.consent_text_label.text() == models.CONSENT_TEXT_V3
        assert screen.consent_checkbox.text() == models.CONSENT_CHECKBOX_LABEL
        assert not screen.consent_checkbox.isChecked()
        assert not screen.learning_checkbox.isChecked()
        assert screen.consent_checkbox.isEnabled()
        assert screen.learning_checkbox.isEnabled()
        assert not screen.banner_label.isVisibleTo(screen)
        assert screen.profile_status_label.text() == "No voice profile yet."
        assert not screen.record_button.isEnabled()  # consent not given yet
        assert not screen.stop_button.isVisibleTo(screen)
        assert not screen.delete_button.isEnabled()
        # Nothing learned yet, nothing to delete, and no consent to confirm.
        assert screen.recently_learned_list.count() == 0
        assert screen.learned_phrases_list.count() == 0
        assert screen.learned_phrases_note_label.text() == NO_LEARNED_PHRASES_TEXT
        assert not screen.delete_recent_button.isEnabled()
        assert not screen.delete_learned_button.isEnabled()
        assert not screen.confirm_consent_button.isVisibleTo(screen)
        assert not screen.consent_notice_label.isVisibleTo(screen)
        assert screen.profile_present is False
        assert screen.device_combo.count() == 2
        assert screen.selected_device() == (7, "Mic B")  # the default device
        screen.deleteLater()

    def test_helper_built_tab_never_reads_the_default_stores(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Peer round 55 PR-LOW-041 (the PR-REG-005 class, completed): a tab
        built by the test helper reaches neither the default profile root nor
        the default config root — at construction (the learned-phrase read),
        on a profile re-read and on a learned-phrase refresh."""
        from scribe_desktop import note_config, practitioner_profile
        from scribe_desktop.ui.practitioner import NO_LEARNED_PHRASES_TEXT

        def forbidden() -> Path:
            raise AssertionError("a default store root must not be consulted")

        monkeypatch.setattr(practitioner_profile, "default_profile_root", forbidden)
        monkeypatch.setattr(note_config, "default_config_root", forbidden)
        screen = _practitioner_screen(FakeController(), FakeBackend(), tmp_path)
        screen.refresh_profile_state()
        screen.refresh_learned_phrases()
        assert screen.learned_phrases_note_label.text() == NO_LEARNED_PHRASES_TEXT
        screen.deleteLater()

    def test_record_enables_only_with_consent_and_availability(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen = _practitioner_screen(FakeController(), FakeBackend(), tmp_path)
        screen.consent_checkbox.setChecked(True)
        assert screen.record_button.isEnabled()
        assert not screen.availability_label.isVisibleTo(screen)

        no_model = _practitioner_screen(
            FakeController(), FakeBackend(), tmp_path, embedder_available=lambda kind: False
        )
        no_model.consent_checkbox.setChecked(True)
        assert not no_model.record_button.isEnabled()
        assert no_model.availability_label.isVisibleTo(no_model)
        assert "--only speaker-embedding" in no_model.availability_label.text()

        no_vad = _practitioner_screen(
            FakeController(), FakeBackend(), tmp_path, vad_available=lambda: False
        )
        no_vad.consent_checkbox.setChecked(True)
        assert not no_vad.record_button.isEnabled()
        assert no_vad.availability_label.isVisibleTo(no_vad)
        assert "silero" in no_vad.availability_label.text()
        screen.deleteLater()
        no_model.deleteLater()
        no_vad.deleteLater()

    def test_first_run_banner_shows_and_hides(self, qapp: Any, tmp_path: Path) -> None:
        """D10: first run ASKS. (The hide-after-save half is pinned in
        `test_enrolment_saves_profile_under_the_lease`, which needs DPAPI.)"""
        screen = _practitioner_screen(FakeController(), FakeBackend(), tmp_path)
        assert not screen.banner_label.isVisibleTo(screen)
        screen.show_first_run_banner()
        assert screen.banner_label.isVisibleTo(screen)
        assert screen.banner_label.text() == models.first_run_banner_text(style_present=False)
        screen.deleteLater()

    @windows_only
    def test_enrolment_saves_profile_under_the_lease(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """D15 end to end: the lease is taken before the capture and released
        only AFTER the result handler has re-read the store (the hook observes
        the UI at the release), and D8's in-memory capture writes nothing but
        the encrypted profile."""
        from scribe_desktop.practitioner_profile import load_profile

        controller = FakeController()
        capture = _FakeCapture()
        screen = _practitioner_screen(
            controller, FakeBackend(), tmp_path, capture=capture
        )
        screen.show_first_run_banner()
        screen.consent_checkbox.setChecked(True)
        screen.learning_checkbox.setChecked(True)
        seen: list[str] = []
        progress_seen: list[str] = []

        def on_release() -> None:
            seen.append(screen.profile_status_label.text())
            progress_seen.append(screen.progress_label.text())

        controller.end_enrolment_hook = on_release
        screen.on_record()
        # Busy UI, observed before the worker's result can be delivered.
        assert ("begin_enrolment",) in controller.calls
        assert controller.enrolling
        assert not screen.record_button.isEnabled()
        assert screen.stop_button.isVisibleTo(screen)
        assert screen.stop_button.isEnabled()
        assert not screen.delete_button.isEnabled()
        assert not screen.consent_checkbox.isEnabled()
        assert not screen.learning_checkbox.isEnabled()
        assert not screen.device_combo.isEnabled()
        assert _process_until(qapp, lambda: not screen.is_busy and screen._lease is None)
        assert controller.calls.count(("end_enrolment",)) == 1
        assert not controller.enrolling
        assert len(seen) == 1 and seen[0].startswith("Voice profile saved 20")
        assert progress_seen == ["Speech heard: 12 s of 30 s"]
        assert capture.calls == [(7,)]
        profile = load_profile(root=tmp_path)
        assert profile is not None
        assert profile.model_id == "stub-embedder-v1"
        assert profile.embedding == (0.6, 0.8, 0.0, 0.0)
        assert profile.embedding_dim == 4
        assert profile.enrolment_speech_seconds == 31.0
        assert profile.device_name == "Mic B"
        assert profile.consent.consent_text_version == models.CONSENT_TEXT_VERSION
        assert profile.consent.learning_opt_in is True
        text = screen.profile_status_label.text()
        assert text.startswith("Voice profile saved ")
        assert "(model stub-embedder-v1)" in text
        assert screen.record_button.text() == "Re-record my voice"
        assert screen.consent_checkbox.isChecked()
        assert not screen.consent_checkbox.isEnabled()
        assert screen.learning_checkbox.isChecked()
        assert screen.learning_checkbox.isEnabled()  # PR-MED-021: editable, applies next record
        assert screen.learning_note_label.isVisibleTo(screen)
        assert screen.delete_button.isEnabled()
        assert not screen.banner_label.isVisibleTo(screen)  # hidden by the save
        assert screen.level_bar.value() == 0
        screen.deleteLater()

    def test_refusal_by_the_controller_is_shown_and_holds_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        controller.enrolment_error = SessionActivityError(
            "voice enrolment refused: a session is recording"
        )
        capture = _FakeCapture()
        screen = _practitioner_screen(
            controller, FakeBackend(), tmp_path, capture=capture
        )
        screen.consent_checkbox.setChecked(True)
        screen.on_record()
        assert screen.enrolment_status_label.text() == (
            "Cannot record now - voice enrolment refused: a session is recording"
        )
        assert not screen.is_busy
        assert ("end_enrolment",) not in controller.calls
        assert capture.calls == []
        assert screen.record_button.isEnabled()
        assert list(tmp_path.iterdir()) == []
        screen.deleteLater()

    def test_a_refusal_by_a_draft_write_names_the_write(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Draft-write plan D9 (round 14): the write's refusal shows its
        line, never the error's own text."""
        from scribe_desktop.session import WriteInFlightError

        controller = FakeController()
        controller.enrolment_error = WriteInFlightError("voice enrolment")
        capture = _FakeCapture()
        screen = _practitioner_screen(controller, FakeBackend(), tmp_path, capture=capture)
        screen.consent_checkbox.setChecked(True)
        screen.on_record()
        assert screen.enrolment_status_label.text() == (
            "Cannot record now - " + models.write_line("write_in_flight")
        )
        assert not screen.is_busy and capture.calls == []
        screen.deleteLater()

    def test_capture_failure_releases_the_lease_and_saves_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        capture = _FakeCapture(
            error=EnrolmentTooShortError("only 12.0 s of speech in 90 s of audio")
        )
        screen = _practitioner_screen(
            controller, FakeBackend(), tmp_path, capture=capture
        )
        _enrol(qapp, screen, capture)
        assert screen.enrolment_status_label.text().startswith(
            "Enrolment did not complete - EnrolmentTooShortError: only 12.0 s"
        )
        assert controller.calls.count(("end_enrolment",)) == 1
        assert not controller.enrolling
        assert list(tmp_path.iterdir()) == []
        # A failed enrolment must not make the practitioner re-tick consent.
        assert screen.consent_checkbox.isChecked()
        assert screen.consent_checkbox.isEnabled()
        assert screen.record_button.isEnabled()
        assert not screen.stop_button.isVisibleTo(screen)
        assert screen.profile_present is False
        screen.deleteLater()

    def test_stop_cancels_and_saves_nothing(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        capture = _FakeCapture(hold=True)
        screen = _practitioner_screen(
            controller, FakeBackend(), tmp_path, capture=capture
        )
        screen.consent_checkbox.setChecked(True)
        screen.on_record()
        assert _process_until(
            qapp, lambda: screen.progress_label.text() == "Speech heard: 12 s of 30 s"
        )
        screen.on_stop()
        assert not screen.stop_button.isEnabled()
        assert screen.enrolment_status_label.text() == "Stopping..."
        assert _process_until(qapp, lambda: not screen.is_busy and screen._lease is None)
        assert screen.enrolment_status_label.text() == "Enrolment stopped - nothing was saved."
        assert ("end_enrolment",) in controller.calls
        assert controller.calls.count(("end_enrolment",)) == 1
        assert list(tmp_path.iterdir()) == []
        screen.deleteLater()

    def test_stop_after_the_capture_returned_still_saves_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 25 MED-001: `record_enrolment` honours Stop only while it
        runs; a Stop pressed while the embedding is in flight must still end
        in "nothing was saved", not in a profile written despite the click."""
        controller = FakeController()
        capture = _FakeCapture()
        embedding_started = threading.Event()
        release = threading.Event()

        def slow_embed(pcm: bytes, embedder: Any) -> tuple[Any, float]:
            embedding_started.set()
            assert release.wait(10.0), "the test never released the embedding"
            return (0.6, 0.8, 0.0, 0.0), 31.0

        screen = _practitioner_screen(
            controller, FakeBackend(), tmp_path, capture=capture, embed=slow_embed
        )
        screen.consent_checkbox.setChecked(True)
        screen.on_record()
        assert embedding_started.wait(10.0)
        screen.on_stop()
        release.set()
        assert _process_until(qapp, lambda: not screen.is_busy and screen._lease is None)
        assert screen.enrolment_status_label.text() == "Enrolment stopped - nothing was saved."
        assert controller.calls.count(("end_enrolment",)) == 1
        assert list(tmp_path.iterdir()) == []
        assert screen.profile_present is False
        screen.deleteLater()

    @windows_only
    def test_failed_re_enrolment_keeps_the_previous_profile(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.practitioner_profile import load_profile

        controller = FakeController()
        first = _FakeCapture()
        screen = _practitioner_screen(controller, FakeBackend(), tmp_path, capture=first)
        _enrol(qapp, screen, first)
        assert screen.profile_status_label.text().startswith("Voice profile saved")

        second = _FakeCapture(error=EnrolmentTooShortError("too short"))
        screen._capture = second
        _enrol(qapp, screen, second)
        assert screen.enrolment_status_label.text().startswith("Enrolment did not complete")
        assert screen.profile_status_label.text().startswith("Voice profile saved")
        assert load_profile(root=tmp_path) is not None
        assert screen.consent_checkbox.isChecked()
        assert not screen.consent_checkbox.isEnabled()
        screen.deleteLater()

    @windows_only
    def test_delete_is_key_deletion_and_resets_consent(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        capture = _FakeCapture()
        screen = _practitioner_screen(
            controller, FakeBackend(), tmp_path, capture=capture
        )
        _enrol(qapp, screen, capture)
        assert (tmp_path / "key.dpapi").exists() and (tmp_path / "voice.enc").exists()
        screen.on_delete()
        assert not (tmp_path / "key.dpapi").exists()  # the key goes FIRST
        assert not (tmp_path / "voice.enc").exists()
        assert screen.enrolment_status_label.text() == "Voice profile deleted."
        assert screen.profile_status_label.text() == "No voice profile yet."
        assert not screen.consent_checkbox.isChecked()
        assert not screen.learning_checkbox.isChecked()
        assert screen.consent_checkbox.isEnabled()
        assert screen.learning_checkbox.isEnabled()
        assert not screen.delete_button.isEnabled()
        assert screen.record_button.text() == "Record my voice (about a minute)"
        screen.deleteLater()

        # A declined confirmation deletes nothing.
        again = _FakeCapture()
        declined = _practitioner_screen(
            FakeController(),
            FakeBackend(),
            tmp_path,
            capture=again,
            confirm_delete=lambda: False,
        )
        _enrol(qapp, declined, again)
        declined.on_delete()
        assert (tmp_path / "key.dpapi").exists() and (tmp_path / "voice.enc").exists()
        declined.deleteLater()

    @windows_only
    def test_device_name_is_sanitised_for_the_profile(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.practitioner_profile import load_profile

        backend = FakeBackend(
            [AudioDevice(device_id=3, name="Mic\tX" + "y" * 300, is_default=True)]
        )
        capture = _FakeCapture()
        screen = _practitioner_screen(
            FakeController(), backend, tmp_path, capture=capture
        )
        _enrol(qapp, screen, capture)
        profile = load_profile(root=tmp_path)
        assert profile is not None
        assert profile.device_name.isprintable()
        assert "\t" not in profile.device_name
        assert len(profile.device_name) == 200
        screen.deleteLater()

    def test_profile_device_name_sanitiser(self) -> None:
        from scribe_desktop.ui.practitioner import profile_device_name

        assert profile_device_name("  \t ") == "unknown microphone"
        # U+2028 LINE SEPARATOR is not printable, so it becomes a plain space.
        assert profile_device_name("A" + chr(0x2028) + "B") == "A B"
        assert profile_device_name("x" * 300) == "x" * 200

    @windows_only
    def test_unusable_profile_is_reported_with_delete_available(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        (tmp_path / "voice.enc").write_bytes(b"garbage")  # no key beside it
        screen = _practitioner_screen(FakeController(), FakeBackend(), tmp_path)
        assert screen.profile_present is True
        assert "cannot be read (key)" in screen.profile_status_label.text()
        assert screen.delete_button.isEnabled()
        assert screen.record_button.text() == "Re-record my voice"
        # PR-HIGH-006: an unreadable blob is NOT evidence of consent — the box
        # stays unticked and editable, and Record waits for a fresh tick.
        assert not screen.consent_checkbox.isChecked()
        assert screen.consent_checkbox.isEnabled()
        assert not screen.record_button.isEnabled()
        assert not screen.learning_note_label.isVisibleTo(screen)
        screen.consent_checkbox.setChecked(True)
        assert screen.record_button.isEnabled()
        screen.deleteLater()

    @windows_only
    def test_interrupted_deletion_needs_a_fresh_consent_tick(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Peer round 27 PR-HIGH-006: the keyless remainder of an interrupted
        Delete (key unlinked, blob unlink failed) is present and deletable
        but is not consent — Record stays gated until the box is ticked
        afresh, and the re-record then writes a fresh key beside the blob."""
        from scribe_desktop.practitioner_profile import load_profile

        first = _FakeCapture()
        screen = _practitioner_screen(FakeController(), FakeBackend(), tmp_path, capture=first)
        _enrol(qapp, screen, first)
        assert screen.consent_checkbox.isChecked() and not screen.consent_checkbox.isEnabled()
        (tmp_path / "key.dpapi").unlink()  # the interrupted Delete's remainder
        # The same screen re-rendering (the delete error path does this): the
        # tick that came from the now-unreadable record is withdrawn.
        screen.refresh_profile_state()
        assert not screen.consent_checkbox.isChecked()
        assert screen.consent_checkbox.isEnabled()
        assert not screen.record_button.isEnabled()
        screen.deleteLater()

        again = _FakeCapture()
        fresh = _practitioner_screen(FakeController(), FakeBackend(), tmp_path, capture=again)
        assert fresh.profile_present is True
        assert "cannot be read (key)" in fresh.profile_status_label.text()
        assert not fresh.consent_checkbox.isChecked()
        assert fresh.consent_checkbox.isEnabled()
        assert not fresh.record_button.isEnabled()
        assert fresh.delete_button.isEnabled()
        fresh.consent_checkbox.setChecked(True)
        assert fresh.record_button.isEnabled()
        _enrol(qapp, fresh, again)
        assert load_profile(root=tmp_path) is not None
        assert (tmp_path / "key.dpapi").exists()
        assert fresh.consent_checkbox.isChecked()
        assert not fresh.consent_checkbox.isEnabled()
        fresh.deleteLater()

    @windows_only
    def test_re_record_changes_the_learning_opt_in(self, qapp: Any, tmp_path: Path) -> None:
        """Peer round 27 PR-MED-021: the opt-in stays editable while a profile
        exists and applies at the next re-record; a failed re-record leaves
        the stored choice unchanged (and the box shows the stored choice)."""
        from scribe_desktop.practitioner_profile import load_profile

        controller = FakeController()
        first = _FakeCapture()
        screen = _practitioner_screen(controller, FakeBackend(), tmp_path, capture=first)
        screen.learning_checkbox.setChecked(True)
        _enrol(qapp, screen, first)
        stored = load_profile(root=tmp_path)
        assert stored is not None and stored.consent.learning_opt_in is True
        assert screen.learning_checkbox.isEnabled()
        assert screen.learning_note_label.isVisibleTo(screen)

        screen.learning_checkbox.setChecked(False)
        second = _FakeCapture()
        screen._capture = second
        _enrol(qapp, screen, second)
        stored = load_profile(root=tmp_path)
        assert stored is not None and stored.consent.learning_opt_in is False

        screen.learning_checkbox.setChecked(True)
        failing = _FakeCapture(error=EnrolmentTooShortError("too short"))
        screen._capture = failing
        _enrol(qapp, screen, failing)
        stored = load_profile(root=tmp_path)
        assert stored is not None and stored.consent.learning_opt_in is False
        assert not screen.learning_checkbox.isChecked()  # the stored choice, re-read
        screen.deleteLater()

    def test_capture_start_hook_runs_before_the_capture_on_the_gui_thread(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Peer round 27 PR-MED-022: the idle monitor is handed over
        synchronously (the hook, on the GUI thread) before the worker can
        open the device."""
        order: list[tuple[str, int | None]] = []
        inner = _FakeCapture()

        def capture(backend: Any, device_id: int, on_progress: Any, should_stop: Any) -> bytes:
            order.append(("capture", threading.get_ident()))
            return inner(backend, device_id, on_progress, should_stop)

        controller = FakeController()
        screen = _practitioner_screen(
            controller,
            FakeBackend(),
            tmp_path,
            capture=capture,
            on_capture_start=lambda: order.append(("handoff", threading.get_ident())),
        )
        screen.consent_checkbox.setChecked(True)
        screen.on_record()
        assert order[0] == ("handoff", threading.main_thread().ident)
        assert ("begin_enrolment",) in controller.calls
        assert _process_until(qapp, lambda: not screen.is_busy and screen._lease is None)
        assert [name for name, _ in order] == ["handoff", "capture"]
        assert order[1][1] != threading.main_thread().ident
        screen.deleteLater()

    def test_a_failing_handoff_releases_the_lease_and_starts_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        def boom() -> None:
            raise RuntimeError("device busy")

        controller = FakeController()
        capture = _FakeCapture()
        screen = _practitioner_screen(
            controller, FakeBackend(), tmp_path, capture=capture, on_capture_start=boom
        )
        screen.consent_checkbox.setChecked(True)
        screen.on_record()
        assert not screen.is_busy
        assert screen.enrolment_status_label.text() == (
            "Cannot record now - RuntimeError: device busy"
        )
        assert controller.calls.count(("begin_enrolment",)) == 1
        assert controller.calls.count(("end_enrolment",)) == 1
        assert not controller.enrolling
        assert capture.calls == []
        assert list(tmp_path.iterdir()) == []
        screen.deleteLater()

    def test_stop_and_delete_are_inert_when_idle(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        screen = _practitioner_screen(controller, FakeBackend(), tmp_path)
        screen.on_stop()
        screen.on_delete()
        assert not screen.enrolment_status_label.isVisibleTo(screen)
        assert screen.enrolment_status_label.text() == ""
        assert controller.calls == []
        assert screen.profile_status_label.text() == "No voice profile yet."
        screen.deleteLater()

    # --- consent versions (Task 5.0) -------------------------------------

    @windows_only
    def test_a_current_consent_record_pre_ticks_with_nothing_to_confirm(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        capture = _FakeCapture()
        screen = _practitioner_screen(
            FakeController(),
            FakeBackend(),
            tmp_path,
            capture=capture,
            config_root=tmp_path / "config",
        )
        _enrol(qapp, screen, capture)  # saves a record for the CURRENT text
        assert screen.consent_current is True
        assert screen.consent_checkbox.isChecked()
        assert not screen.consent_checkbox.isEnabled()  # withdrawal is Delete
        assert not screen.consent_notice_label.isVisibleTo(screen)
        assert screen.confirm_consent_button.isVisibleTo(screen)
        assert not screen.confirm_consent_button.isEnabled()  # nothing to confirm
        screen.deleteLater()

    @windows_only
    @pytest.mark.parametrize("older_version", ["consent-v1", "consent-v2"])
    def test_a_stale_consent_record_does_not_pre_tick_and_gates_record(
        self, qapp: Any, tmp_path: Path, older_version: str
    ) -> None:
        """Every OLDER version re-asks (note-learning plan Task 0.1: a v2
        record reads but is not current, so the tab asks again)."""
        capture = _FakeCapture()
        first = _practitioner_screen(
            FakeController(),
            FakeBackend(),
            tmp_path,
            capture=capture,
            config_root=tmp_path / "config",
        )
        first.learning_checkbox.setChecked(True)
        _enrol(qapp, first, capture)
        first.deleteLater()
        stale = _make_consent_stale(tmp_path, older_version)
        assert stale.consent.consent_text_version == older_version
        assert not models.consent_is_current(stale)

        screen = _practitioner_screen(
            FakeController(), FakeBackend(), tmp_path, config_root=tmp_path / "config"
        )
        assert screen.consent_current is False
        assert not screen.consent_checkbox.isChecked()
        assert screen.consent_checkbox.isEnabled()
        assert screen.consent_notice_label.isVisibleTo(screen)
        assert screen.consent_notice_label.text() == models.CONSENT_STALE_NOTICE
        assert not screen.record_button.isEnabled()  # Record needs a fresh tick
        assert screen.confirm_consent_button.isVisibleTo(screen)
        assert not screen.confirm_consent_button.isEnabled()
        assert screen.learning_checkbox.isChecked()  # the STORED choice, shown
        screen.consent_checkbox.setChecked(True)
        assert screen.record_button.isEnabled()
        assert screen.confirm_consent_button.isEnabled()
        screen.deleteLater()

    @windows_only
    def test_confirm_consent_re_saves_the_same_vector_without_re_recording(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.practitioner_profile import load_profile

        capture = _FakeCapture()
        first = _practitioner_screen(
            FakeController(),
            FakeBackend(),
            tmp_path,
            capture=capture,
            config_root=tmp_path / "config",
        )
        first.learning_checkbox.setChecked(True)
        _enrol(qapp, first, capture)
        first.deleteLater()
        stale = _make_consent_stale(tmp_path)
        key_before = (tmp_path / "key.dpapi").read_bytes()
        second = _FakeCapture()
        screen = _practitioner_screen(
            FakeController(),
            FakeBackend(),
            tmp_path,
            capture=second,
            config_root=tmp_path / "config",
        )
        screen.consent_checkbox.setChecked(True)
        screen.learning_checkbox.setChecked(False)
        screen.on_confirm_consent()
        stored = load_profile(root=tmp_path)
        assert stored is not None
        assert stored.consent.consent_text_version == models.CONSENT_TEXT_VERSION
        assert stored.consent.learning_opt_in is False  # as ticked
        assert stored.embedding == stale.embedding  # the SAME vector
        assert stored.created_at == stale.created_at
        assert screen.consent_checkbox.isChecked()
        assert not screen.consent_checkbox.isEnabled()
        assert not screen.consent_notice_label.isVisibleTo(screen)
        assert screen.enrolment_status_label.text() == (
            "Consent saved - your voice profile is unchanged."
        )
        assert second.calls == []  # no microphone, no re-record
        assert (tmp_path / "key.dpapi").read_bytes() == key_before
        screen.deleteLater()

    @windows_only
    def test_the_learning_opt_in_is_saved_by_confirm_consent(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.practitioner_profile import load_profile

        capture = _FakeCapture()
        screen = _practitioner_screen(
            FakeController(),
            FakeBackend(),
            tmp_path,
            capture=capture,
            config_root=tmp_path / "config",
        )
        _enrol(qapp, screen, capture)  # current consent, opt-in OFF
        assert not screen.confirm_consent_button.isEnabled()
        before = load_profile(root=tmp_path)
        assert before is not None and before.consent.learning_opt_in is False
        screen.learning_checkbox.setChecked(True)
        assert screen.confirm_consent_button.isEnabled()  # a change to save
        screen.on_confirm_consent()
        stored = load_profile(root=tmp_path)
        assert stored is not None
        assert stored.consent.learning_opt_in is True
        assert stored.embedding == before.embedding
        assert stored.consent.consent_text_version == models.CONSENT_TEXT_VERSION
        assert not screen.confirm_consent_button.isEnabled()  # nothing left to save
        screen.deleteLater()

    @windows_only
    def test_a_record_found_stale_in_session_withdraws_its_own_tick_only(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        capture = _FakeCapture()
        screen = _practitioner_screen(
            FakeController(),
            FakeBackend(),
            tmp_path,
            capture=capture,
            config_root=tmp_path / "config",
        )
        _enrol(qapp, screen, capture)
        assert screen.consent_checkbox.isChecked()
        _make_consent_stale(tmp_path)
        screen.refresh_profile_state()
        # The tick came from a record that is no longer current: withdrawn.
        assert not screen.consent_checkbox.isChecked()
        assert screen.consent_notice_label.isVisibleTo(screen)
        screen.consent_checkbox.setChecked(True)  # the practitioner ticks again
        screen.refresh_profile_state()
        assert screen.consent_checkbox.isChecked()  # the hand tick STANDS
        assert screen.consent_notice_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_confirm_consent_is_inert_without_a_readable_profile(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        root = tmp_path / "profile"
        root.mkdir()
        screen = _practitioner_screen(
            FakeController(), FakeBackend(), root, config_root=tmp_path / "config"
        )
        screen.consent_checkbox.setChecked(True)
        screen.on_confirm_consent()
        assert list(root.iterdir()) == []  # nothing written
        assert screen.enrolment_status_label.text() == ""
        screen.deleteLater()

    @windows_only
    def test_confirm_consent_is_inert_without_a_fresh_tick(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        capture = _FakeCapture()
        first = _practitioner_screen(
            FakeController(),
            FakeBackend(),
            tmp_path,
            capture=capture,
            config_root=tmp_path / "config",
        )
        _enrol(qapp, first, capture)
        first.deleteLater()
        _make_consent_stale(tmp_path)
        blob_before = (tmp_path / "voice.enc").read_bytes()

        screen = _practitioner_screen(
            FakeController(), FakeBackend(), tmp_path, config_root=tmp_path / "config"
        )
        assert not screen.consent_checkbox.isChecked()
        screen.on_confirm_consent()
        assert (tmp_path / "voice.enc").read_bytes() == blob_before
        assert screen.consent_current is False
        screen.deleteLater()

    # --- learned phrases (Task 5.3) ---------------------------------------

    def test_learned_phrases_are_listed_newest_first_and_deletable(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from PySide6.QtCore import Qt

        from scribe_desktop.ui.practitioner import NO_LEARNED_PHRASES_TEXT

        root = tmp_path / "config"
        screen = _practitioner_screen(
            FakeController(), FakeBackend(), tmp_path, config_root=root
        )
        assert screen.recently_learned_list.count() == 0
        assert screen.learned_phrases_list.count() == 0
        assert screen.learned_phrases_note_label.text() == NO_LEARNED_PHRASES_TEXT

        append_user_cues(
            [("advice_home_exercise", "wall slide")],
            config_root=root,
            learned_at=datetime(2026, 9, 15, tzinfo=UTC),
        )
        append_user_cues(
            [("management_plan", "book the follow up")],
            config_root=root,
            learned_at=datetime(2026, 9, 16, tzinfo=UTC),
        )
        screen.refresh_learned_phrases()
        assert screen.recently_learned_list.count() == 2
        newest = screen.recently_learned_list.item(0).text()
        assert newest == (
            f"2026-09-16 - {models.section_title('management_plan')}: book the follow up"
        )
        assert screen.recently_learned_list.item(1).text() == (
            f"2026-09-15 - {models.section_title('advice_home_exercise')}: wall slide"
        )
        assert [
            screen.learned_phrases_list.item(index).text()
            for index in range(screen.learned_phrases_list.count())
        ] == [
            f"{models.section_title('advice_home_exercise')}: wall slide",
            f"{models.section_title('management_plan')}: book the follow up",
        ]
        assert screen.delete_recent_button.isEnabled()
        assert screen.delete_learned_button.isEnabled()

        assert screen.delete_learned_phrase("wall slide") is True
        assert screen.recently_learned_list.count() == 1
        assert screen.learned_phrases_list.count() == 1
        assert screen.learned_phrases_note_label.text() == "Deleted 'wall slide'."
        learned = load_learned_phrases(root)
        assert [item.phrase for item in learned.recent] == ["book the follow up"]
        assert learned.by_section == (("management_plan", ("book the follow up",)),)

        # A selection-driven delete goes through the same one writer.
        screen.learned_phrases_list.setCurrentRow(0)
        phrase = screen.learned_phrases_list.item(0).data(Qt.ItemDataRole.UserRole)
        assert phrase == "book the follow up"
        screen.delete_learned_button.click()
        assert screen.learned_phrases_list.count() == 0
        assert load_learned_phrases(root) == ((), ())
        screen.deleteLater()

    def test_a_sidecar_entry_whose_phrase_is_gone_is_not_listed(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        append_user_cues(
            [("advice_home_exercise", "wall slide")],
            config_root=root,
            learned_at=datetime(2026, 9, 15, tzinfo=UTC),
        )
        (root / LEARNED_SIDECAR_FILENAME).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "learned": {
                        "wall slide": {
                            "section": "advice_home_exercise",
                            "learned_at": "2026-09-15T00:00:00+00:00",
                        },
                        "ghost phrase": {
                            "section": "management_plan",
                            "learned_at": "2026-09-16T00:00:00+00:00",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        screen = _practitioner_screen(
            FakeController(), FakeBackend(), tmp_path, config_root=root
        )
        assert screen.recently_learned_list.count() == 1
        assert "wall slide" in screen.recently_learned_list.item(0).text()
        assert "ghost phrase" not in "\n".join(
            screen.recently_learned_list.item(index).text()
            for index in range(screen.recently_learned_list.count())
        )
        screen.deleteLater()

    def test_a_malformed_cue_file_is_reported_and_disables_delete(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        append_user_cues(
            [("advice_home_exercise", "wall slide")],
            config_root=root,
            learned_at=datetime(2026, 9, 15, tzinfo=UTC),
        )
        screen = _practitioner_screen(
            FakeController(), FakeBackend(), tmp_path, config_root=root
        )
        assert screen.learned_phrases_list.count() == 1
        (root / SECTION_CUES_FILENAME).write_text("{not json", encoding="utf-8")
        screen.refresh_learned_phrases()
        assert screen.learned_phrases_note_label.text().startswith(
            "Learned phrases unavailable - NoteConfigInvalidError:"
        )
        assert screen.recently_learned_list.count() == 0
        assert screen.learned_phrases_list.count() == 0
        assert not screen.delete_recent_button.isEnabled()
        assert not screen.delete_learned_button.isEnabled()
        screen.deleteLater()

    def test_a_raw_cleanup_error_on_delete_keeps_the_row_for_a_retry(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Peer round 37 PR-MED-025: a deletion whose sidecar write
        double-faults reaches the tab's typed error branch (no slot exception),
        the row stays, and the retry finishes the job."""
        root = tmp_path / "config"
        append_user_cues(
            [("advice_home_exercise", "wall slide")],
            config_root=root,
            learned_at=datetime(2026, 9, 15, tzinfo=UTC),
        )
        screen = _practitioner_screen(
            FakeController(), FakeBackend(), tmp_path, config_root=root
        )
        assert screen.learned_phrases_list.count() == 1
        blocker = root / (LEARNED_SIDECAR_FILENAME + ".tmp")
        blocker.mkdir()
        assert screen.delete_learned_phrase("wall slide") is False
        assert screen.learned_phrases_note_label.text().startswith(
            "Could not delete the phrase - NoteConfigWriteError:"
        )
        assert screen.learned_phrases_list.count() == 1  # the row stays for a retry
        blocker.rmdir()
        assert screen.delete_learned_phrase("wall slide") is True
        assert screen.learned_phrases_list.count() == 0
        assert screen.recently_learned_list.count() == 0
        assert load_learned_phrases(root) == ((), ())
        screen.deleteLater()

    @windows_only
    def test_confirm_consent_reports_a_raw_writer_error_instead_of_raising(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR-MED-025's in-phase sibling: the profile writer's double fault
        (a directory at `voice.enc.tmp`) is reported on the tab, not raised
        from the slot; the stored record is unchanged."""
        capture = _FakeCapture()
        first = _practitioner_screen(
            FakeController(),
            FakeBackend(),
            tmp_path,
            capture=capture,
            config_root=tmp_path / "config",
        )
        _enrol(qapp, first, capture)
        first.deleteLater()
        _make_consent_stale(tmp_path)
        blob_before = (tmp_path / "voice.enc").read_bytes()
        (tmp_path / "voice.enc.tmp").mkdir()
        screen = _practitioner_screen(
            FakeController(), FakeBackend(), tmp_path, config_root=tmp_path / "config"
        )
        screen.consent_checkbox.setChecked(True)
        screen.on_confirm_consent()  # must not raise
        assert screen.enrolment_status_label.text().startswith("Could not save your consent - ")
        assert (tmp_path / "voice.enc").read_bytes() == blob_before
        assert screen.consent_current is False
        screen.deleteLater()

    def test_delete_selected_without_a_selection_asks_for_one(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        append_user_cues(
            [("advice_home_exercise", "wall slide")],
            config_root=root,
            learned_at=datetime(2026, 9, 15, tzinfo=UTC),
        )
        screen = _practitioner_screen(
            FakeController(), FakeBackend(), tmp_path, config_root=root
        )
        screen._delete_selected(screen.learned_phrases_list)
        assert "Select a phrase" in screen.learned_phrases_note_label.text()
        assert load_learned_phrases(root).by_section == (
            ("advice_home_exercise", ("wall slide",)),
        )
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Session screen.
# ---------------------------------------------------------------------------


def _session_screen(
    controller: FakeController,
    *,
    device: int | None = 7,
    transcriber: Callable[[Path, Any], TranscriptDocument] | None = None,
) -> Any:
    from scribe_desktop.ui.session_screen import SessionScreen

    factory = (lambda: transcriber) if transcriber is not None else (
        lambda: (lambda d, c: _document())
    )
    screen = SessionScreen(
        controller,
        device_provider=lambda: device,
        transcriber_factory=factory,  # type: ignore[arg-type]
    )
    # Cliniko safeguards Task 3.3: the consent tick gates Start; the existing
    # screen tests start ticked (the tick tests below start from the default).
    screen.consent_checkbox.setChecked(True)
    return screen


class TestSessionScreen:
    def test_idle_enablement(self, qapp: Any) -> None:
        screen = _session_screen(FakeController())
        assert screen.start_button.isEnabled()
        for button in (
            screen.pause_button,
            screen.resume_button,
            screen.finish_button,
            screen.discard_button,
        ):
            assert not button.isEnabled()
        screen.deleteLater()

    def test_start_uses_selected_device_and_updates_enablement(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller, device=7)
        screen.on_start()
        assert ("start", 7) in controller.calls
        assert not screen.start_button.isEnabled()
        assert screen.pause_button.isEnabled()
        assert screen.finish_button.isEnabled()
        assert screen.discard_button.isEnabled()
        screen.deleteLater()

    def test_start_without_device_shows_message(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller, device=None)
        screen.on_start()
        assert controller.calls == []
        assert "Microphone screen" in screen.message_label.text()
        screen.deleteLater()

    def test_pause_resume_wiring(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller)
        screen.on_start()
        screen.on_pause()
        assert ("pause",) in controller.calls
        assert screen.resume_button.isEnabled() and not screen.pause_button.isEnabled()
        screen.on_resume()
        assert ("resume",) in controller.calls
        assert screen.pause_button.isEnabled()
        screen.deleteLater()

    def test_finish_drives_transcription_and_emits_document(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller)
        received: list[TranscriptDocument] = []
        screen.transcript_ready.connect(received.append)
        screen.on_start()
        screen.on_finish()
        assert _process_until(qapp, lambda: bool(received))
        assert ("transcribe",) in controller.calls
        assert controller.state_value == SessionState.QUEUED
        assert isinstance(received[0], TranscriptDocument)
        assert not screen.progress_bar.isVisibleTo(screen)
        screen.deleteLater()

    def test_start_emits_session_started_only_on_success(self, qapp: Any) -> None:
        """Round 7 LOW-003: the live view opens on a successful Start only."""
        controller = FakeController()
        screen = _session_screen(controller)
        started: list[int] = []
        screen.session_started.connect(lambda: started.append(1))
        screen.on_start()
        assert started == [1]

        def failing_start(device_id: int, **_kwargs: Any) -> Any:
            raise RuntimeError("no device")

        controller.start = failing_start  # type: ignore[method-assign]
        controller.state_value = SessionState.IDLE
        screen.refresh()
        screen.consent_checkbox.setChecked(True)  # cleared by the first Start
        screen.on_start()
        assert started == [1]  # not emitted on the failed Start
        assert "Start failed" in screen.message_label.text()
        screen.deleteLater()

    def test_live_status_reaches_the_progress_and_completion_messages(self, qapp: Any) -> None:
        """Note-learning plan C8: the live outcome reported from the
        processing thread joins the progress line while transcribing and the
        completion message afterwards; the queued signal marshals it."""
        controller = FakeController()
        screen = _session_screen(controller)
        screen.report_live_status("Live line.")  # the thread-safe entry point
        assert _process_until(qapp, lambda: screen._live_status == "Live line.")
        screen._transcribing = True
        screen._live_status = None
        screen._on_live_status("Live transcription could not keep up; batch instead.")
        assert "could not keep up" in screen.progress_label.text()
        screen._on_transcribed(_document())
        assert screen.message_label.text().startswith("Transcription complete")
        assert "could not keep up" in screen.message_label.text()
        screen.deleteLater()

    def test_transcription_failure_reports_recoverable(self, qapp: Any) -> None:
        controller = FakeController()

        def broken(_d: Path, _c: Any) -> TranscriptDocument:
            raise RuntimeError("model exploded")

        screen = _session_screen(controller, transcriber=broken)
        screen.on_start()
        screen.on_finish()
        assert _process_until(
            qapp, lambda: "recoverable" in screen.message_label.text()
        )
        assert controller.state_value == SessionState.FAILED
        assert screen.discard_button.isEnabled()  # failed -> discard only
        screen.deleteLater()

    def test_state_watcher_surfaces_async_capture_failure(self, qapp: Any) -> None:
        """PR round 18 (PR3): device loss flips the controller to failed from
        the worker thread; the poll must refresh enablement + message."""
        controller = FakeController()
        screen = _session_screen(controller)
        screen.on_start()
        controller.state_value = SessionState.FAILED  # async failure
        screen._watch_state()
        assert "Recording failed" in screen.message_label.text()
        assert screen.discard_button.isEnabled()
        assert not screen.pause_button.isEnabled()
        screen.deleteLater()

    def test_transcription_task_reference_dropped_after_success(self, qapp: Any) -> None:
        """PR round 18 (PR7): no closure chain retaining the plaintext
        document survives the run."""
        controller = FakeController()
        screen = _session_screen(controller)
        received: list[TranscriptDocument] = []
        screen.transcript_ready.connect(received.append)
        screen.on_start()
        screen.on_finish()
        assert _process_until(qapp, lambda: bool(received))
        assert screen._task is None
        assert screen.is_busy is False
        screen.deleteLater()

    def test_discard_wiring(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller)
        screen.on_start()
        screen.on_discard()
        assert ("discard",) in controller.calls
        assert "cryptographically deleted" in screen.message_label.text()
        # Task 3.3: Start was cleared of its consent tick, so the next
        # recording needs a fresh tick before Start enables.
        assert not screen.start_button.isEnabled()
        screen.consent_checkbox.setChecked(True)
        assert screen.start_button.isEnabled()
        screen.deleteLater()

    def test_discard_emits_session_discarded(self, qapp: Any) -> None:
        """Note-learning plan Task 1.4: a successful Discard announces itself
        so the Transcript screen's live view can be cleared."""
        controller = FakeController()
        screen = _session_screen(controller)
        emitted: list[int] = []
        screen.session_discarded.connect(lambda: emitted.append(1))
        screen.on_start()
        screen.on_discard()
        assert emitted == [1]
        assert ("discard",) in controller.calls
        screen.deleteLater()


def _linked_context(
    verification: Verification = Verification.VERIFIED,
) -> EncounterContext:
    return EncounterContext(
        clinic_id="0123456789abcdef",
        clinic_host="northside.au2.cliniko.com",
        patient_id="10",
        treatment_note_id="20",
        practitioner_id="30",
        verification=verification,
        verified_at=datetime.now(UTC) if verification is Verification.VERIFIED else None,
    )


class TestSessionScreenConsent:
    """Cliniko workflow safeguards plan Task 3.3 (Constraint 4): the desktop
    consent tick and the "Not linked to a Cliniko note" line."""

    def _screen(self, controller: FakeController) -> Any:
        screen = _session_screen(controller)
        screen.consent_checkbox.setChecked(False)  # the screen's own default
        return screen

    def test_the_tick_carries_plan_wording_and_is_never_pre_ticked(self, qapp: Any) -> None:
        from scribe_desktop.encounter import RECORDING_CONSENT_TEXT
        from scribe_desktop.ui.session_screen import SessionScreen

        screen = SessionScreen(FakeController(), device_provider=lambda: 7)
        assert screen.consent_checkbox.text() == RECORDING_CONSENT_TEXT
        assert RECORDING_CONSENT_TEXT == (
            "I confirm the patient has consented to AI-assisted recording and documentation"
        )
        assert not screen.consent_checkbox.isChecked()
        assert not screen.start_button.isEnabled()  # disabled, not error-handled
        screen.consent_checkbox.setChecked(True)
        assert screen.start_button.isEnabled()
        screen.deleteLater()

    def test_start_without_the_tick_is_refused_and_calls_nothing(self, qapp: Any) -> None:
        controller = FakeController()
        screen = self._screen(controller)
        screen.on_start()
        assert controller.calls == []
        assert screen.message_label.text() == models.CONSENT_REQUIRED_MESSAGE
        screen.deleteLater()

    def test_the_desktop_start_records_an_unlinked_consent_and_clears_the_tick(
        self, qapp: Any
    ) -> None:
        controller = FakeController()
        screen = self._screen(controller)
        screen.consent_checkbox.setChecked(True)
        screen.on_start()
        assert controller.calls == [("start", 7)]
        consent, context = controller.started_with[0]
        assert isinstance(consent, ConsentAttestation)
        assert consent.treatment_note_id is None and context is None
        assert not screen.consent_checkbox.isChecked()  # cleared after every Start
        screen.deleteLater()

    def test_a_failed_start_also_clears_the_tick(self, qapp: Any) -> None:
        controller = FakeController()

        def failing_start(device_id: int, **_kwargs: Any) -> Any:
            raise RuntimeError("no device")

        controller.start = failing_start  # type: ignore[method-assign]
        screen = self._screen(controller)
        screen.consent_checkbox.setChecked(True)
        screen.on_start()
        assert "Start failed" in screen.message_label.text()
        assert not screen.consent_checkbox.isChecked()
        assert not screen.start_button.isEnabled()
        screen.deleteLater()

    def test_start_linked_passes_its_consent_and_context(self, qapp: Any) -> None:
        controller = FakeController()
        screen = self._screen(controller)
        context = _linked_context()
        consent = linked_consent(context)
        started: list[int] = []
        screen.session_started.connect(lambda: started.append(1))
        screen.start_linked(consent, context)
        assert controller.started_with == [(consent, context)]
        assert started == [1]
        assert not screen.consent_checkbox.isChecked()
        screen.deleteLater()

    def test_the_link_line_says_not_linked_when_idle_and_unlinked(self, qapp: Any) -> None:
        controller = FakeController()
        screen = self._screen(controller)
        assert screen.link_label.text() == models.NOT_LINKED_DETAIL
        assert models.NOT_LINKED_LABEL in screen.link_label.text()
        controller.session_value = RecordingSession(consent=unlinked_consent()).with_state(
            SessionState.RECORDING
        )
        controller.state_value = SessionState.RECORDING
        screen.refresh()
        assert screen.link_label.text() == models.NOT_LINKED_DETAIL
        screen.deleteLater()

    @pytest.mark.parametrize(
        "verification, expected",
        [
            (Verification.VERIFIED, models.LINKED_VERIFIED_LABEL),
            (Verification.UNVERIFIED_OFFLINE, models.LINKED_UNVERIFIED_LABEL),
        ],
    )
    def test_the_link_line_for_a_linked_session_names_no_patient(
        self, qapp: Any, verification: Verification, expected: str
    ) -> None:
        controller = FakeController()
        screen = self._screen(controller)
        context = _linked_context(verification)
        controller.session_value = RecordingSession(
            consent=linked_consent(context), encounter_context=context
        ).with_state(SessionState.RECORDING)
        controller.state_value = SessionState.RECORDING
        screen.refresh()
        assert screen.link_label.text() == expected
        for identifier in ("10", "20", "30", "northside"):
            assert identifier not in screen.link_label.text()
        screen.deleteLater()

    def test_the_chrome_line_is_plain_text_and_hidden_when_empty(self, qapp: Any) -> None:
        from PySide6.QtCore import Qt

        screen = self._screen(FakeController())
        assert screen.chrome_label.isHidden()  # no bridge: nothing shown
        assert screen.chrome_label.textFormat() == Qt.TextFormat.PlainText
        screen.set_chrome_view("Chrome: connected.\n<b>not bold</b>")
        assert not screen.chrome_label.isHidden()
        assert screen.chrome_label.text() == "Chrome: connected.\n<b>not bold</b>"
        screen.set_chrome_view("")
        assert screen.chrome_label.isHidden()
        screen.deleteLater()

    def test_controls_report_whether_they_acted(self, qapp: Any) -> None:
        """Task 4.5: the bridge turns a False into a named refusal."""
        controller = FakeController()
        screen = self._screen(controller)
        assert screen.has_input_device()
        context = _linked_context()
        assert screen.start_linked(linked_consent(context), context) is True
        assert screen.on_pause() is True and screen.on_resume() is True
        assert screen.on_discard() is True

        def refuse(*_args: Any, **_kwargs: Any) -> Any:
            raise SessionActivityError("refused")

        for name in ("start", "pause", "resume", "finish", "discard"):
            setattr(controller, name, refuse)
        assert screen.start_linked(linked_consent(context), context) is False
        assert screen.on_pause() is False and screen.on_resume() is False
        assert screen.on_finish() is False and screen.on_discard() is False
        screen.deleteLater()

    def test_no_microphone_means_no_linked_start(self, qapp: Any) -> None:
        from scribe_desktop.ui.session_screen import SessionScreen

        controller = FakeController()
        screen = SessionScreen(controller, device_provider=lambda: None)
        assert not screen.has_input_device()
        context = _linked_context()
        assert screen.start_linked(linked_consent(context), context) is False
        assert controller.started_with == []
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Recovery screen.
# ---------------------------------------------------------------------------


def _make_recoverable(root: Path, *, finished: bool) -> str:
    session_id = uuid.uuid4().hex
    directory = root / session_id
    directory.mkdir(parents=True)
    (directory / KEY_FILENAME).write_bytes(b"\x01" * 64)
    crypto = SessionCrypto()
    store = SessionChunkStore.create(directory / AUDIO_FILENAME, crypto, session_id)
    store.append_chunk(b"\x00\x01" * 800)
    if finished:
        store.finish()
    store.close()
    crypto.destroy()
    return session_id


class TestRecoveryScreen:
    def test_lists_sessions_and_warns_on_unfinished_store(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.recovery import RecoveryScreen

        _make_recoverable(tmp_path, finished=False)
        screen = RecoveryScreen(
            tmp_path, recovery_runner=lambda d: pytest.fail("not called")
        )
        assert screen.session_list.count() == 1
        screen.session_list.setCurrentRow(0)
        qapp.processEvents()
        # Binding Step-10 note: warn whenever store_finished is False.
        assert screen.warning_label.isVisibleTo(screen)
        assert screen.warning_label.text() == models.UNFINISHED_STORE_WARNING
        assert screen.resume_button.isEnabled()
        screen.deleteLater()

    def test_finished_store_shows_no_warning(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.ui.recovery import RecoveryScreen

        _make_recoverable(tmp_path, finished=True)
        screen = RecoveryScreen(
            tmp_path, recovery_runner=lambda d: pytest.fail("not called")
        )
        screen.session_list.setCurrentRow(0)
        qapp.processEvents()
        assert not screen.warning_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_resume_processing_emits_outcome(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.ui.recovery import RecoveryScreen

        session_id = _make_recoverable(tmp_path, finished=False)
        outcome = RecoveryOutcome(
            document=_document(), crypto=SessionCrypto(), store_finished=False
        )
        received: list[object] = []
        screen = RecoveryScreen(tmp_path, recovery_runner=lambda d: outcome)
        screen.recovered.connect(received.append)
        screen.session_list.setCurrentRow(0)
        screen.on_resume_processing()
        assert _process_until(qapp, lambda: bool(received))
        directory, got = received[0]  # type: ignore[misc]
        assert directory == tmp_path / session_id
        assert got is outcome
        screen.deleteLater()

    def test_discard_deletes_key_first_and_refreshes(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.recovery import RecoveryScreen

        session_id = _make_recoverable(tmp_path, finished=True)
        screen = RecoveryScreen(
            tmp_path, recovery_runner=lambda d: pytest.fail("not called")
        )
        screen.session_list.setCurrentRow(0)
        screen.on_discard()
        assert not (tmp_path / session_id / KEY_FILENAME).exists()
        assert screen.session_list.count() == 0
        screen.deleteLater()

    def test_active_session_never_listed(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.ui.recovery import RecoveryScreen

        session_id = _make_recoverable(tmp_path, finished=False)
        screen = RecoveryScreen(
            tmp_path,
            active_ids_provider=lambda: frozenset({session_id}),
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        assert screen.session_list.count() == 0
        screen.deleteLater()

    def test_recovered_session_checked_out_until_released(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR round 18 (PR1): a recovered session must vanish from the list
        while its transcript view holds custody, and return on release
        (its key custody is still intact until Complete/Discard)."""
        from scribe_desktop.ui.recovery import RecoveryScreen

        session_id = _make_recoverable(tmp_path, finished=True)
        outcome = RecoveryOutcome(
            document=_document(), crypto=SessionCrypto(), store_finished=True
        )
        received: list[object] = []
        screen = RecoveryScreen(tmp_path, recovery_runner=lambda d: outcome)
        screen.recovered.connect(received.append)
        screen.session_list.setCurrentRow(0)
        screen.on_resume_processing()
        assert _process_until(qapp, lambda: bool(received))
        assert screen.session_list.count() == 0  # checked out, not listed
        assert screen.protected_session_ids() == frozenset({session_id})
        screen.release_checkouts()
        assert screen.protected_session_ids() == frozenset()
        assert screen.session_list.count() == 1  # key custody still live
        screen.deleteLater()

    def test_second_resume_refused_while_checkout_open(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR round 19 (MED): a second resume while a recovered transcript
        is still open must be refused — it would overwrite the open view's
        custody callbacks."""
        from scribe_desktop.ui.recovery import RecoveryScreen

        _make_recoverable(tmp_path, finished=True)
        _make_recoverable(tmp_path, finished=True)
        outcomes: list[object] = []
        calls: list[Path] = []

        def runner(directory: Path) -> RecoveryOutcome:
            calls.append(directory)
            return RecoveryOutcome(
                document=_document(), crypto=SessionCrypto(), store_finished=True
            )

        screen = RecoveryScreen(tmp_path, recovery_runner=runner)
        screen.recovered.connect(outcomes.append)
        screen.session_list.setCurrentRow(0)
        screen.on_resume_processing()
        assert _process_until(qapp, lambda: bool(outcomes))
        assert len(calls) == 1
        # One session remains listed; resume must now be refused.
        assert screen.session_list.count() == 1
        screen.session_list.setCurrentRow(0)
        qapp.processEvents()
        assert not screen.resume_button.isEnabled()
        screen.on_resume_processing()  # direct call also refused
        assert len(calls) == 1
        assert "Finish the open recovered transcript" in screen.message_label.text()
        screen.release_checkouts()
        screen.session_list.setCurrentRow(0)
        qapp.processEvents()
        assert screen.resume_button.isEnabled()
        screen.deleteLater()

    def test_failed_recovery_releases_protection(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.recovery import RecoveryScreen

        _make_recoverable(tmp_path, finished=True)

        def broken(_d: Path) -> RecoveryOutcome:
            raise RuntimeError("model exploded")

        screen = RecoveryScreen(tmp_path, recovery_runner=broken)
        screen.session_list.setCurrentRow(0)
        screen.on_resume_processing()
        assert _process_until(
            qapp, lambda: "Recovery failed" in screen.message_label.text()
        )
        assert screen.protected_session_ids() == frozenset()
        assert screen.session_list.count() == 1  # still recoverable
        screen.deleteLater()

    def test_no_resume_recording_control_exists(self, qapp: Any, tmp_path: Path) -> None:
        """Flow 3 Critical Constraint: recovery offers resume-PROCESSING and
        discard only — never resume recording. Task 5.4 (D6) adds the
        Unreviewed section's "Open for review" and its own Discard."""
        from PySide6.QtWidgets import QPushButton

        from scribe_desktop.ui.recovery import RecoveryScreen

        screen = RecoveryScreen(
            tmp_path, recovery_runner=lambda d: pytest.fail("not called")
        )
        labels = [b.text().lower() for b in screen.findChildren(QPushButton)]
        assert sorted(labels) == sorted(
            ["resume processing", "discard", "refresh", "open for review", "discard"]
        )
        assert not any("record" in label for label in labels)
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Transcript-inspection view.
# ---------------------------------------------------------------------------


def _live_segments(start: float, text: str, uncertain_word: str) -> tuple[TranscriptSegment, ...]:
    """One live window's worth of segments, as the live worker posts them:
    the speaker label is always LIVE_SPEAKER_PENDING (the speaker pass runs
    only at the drain)."""
    return (
        TranscriptSegment(
            start_seconds=start,
            end_seconds=start + 2.0,
            speaker=LIVE_SPEAKER_PENDING,
            transcript_words=(
                TranscriptWord(
                    word_text=text,
                    start_seconds=start,
                    end_seconds=start + 0.5,
                    probability=0.95,
                    uncertain=False,
                ),
                TranscriptWord(
                    word_text=uncertain_word,
                    start_seconds=start + 0.6,
                    end_seconds=start + 1.0,
                    probability=0.30,
                    uncertain=True,
                ),
            ),
        ),
    )


class TestTranscriptScreen:
    def test_renders_marks_and_speakers_and_completes(self, qapp: Any) -> None:
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        assert not screen.complete_button.isEnabled()
        completed: list[str] = []
        calls: list[str] = []
        screen.closed.connect(completed.append)
        screen.show_document(
            _document(),
            on_complete=lambda: calls.append("complete"),
            on_discard=lambda: calls.append("discard"),
        )
        text = screen.transcript_view.toPlainText()
        assert "speaker_1" in text
        assert "[Margaret?]" in text  # uncertainty mark visible
        assert "Hello" in text
        assert not screen.warning_label.isVisibleTo(screen)
        screen.on_complete()
        assert calls == ["complete"]
        assert completed == ["completed"]
        assert screen.transcript_view.toPlainText() == ""  # display cleared
        assert not screen.complete_button.isEnabled()
        screen.deleteLater()

    def test_transcript_view_has_no_text_interaction(self, qapp: Any) -> None:
        """PR round 18 (PR5): no selection/copy — transcript text must not
        reach the Windows clipboard (history / cloud sync)."""
        from PySide6.QtCore import Qt

        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        flags = screen.transcript_view.textInteractionFlags()
        assert flags == Qt.TextInteractionFlag.NoTextInteraction
        screen.deleteLater()

    def test_unfinished_store_warning_shown(self, qapp: Any) -> None:
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        screen.show_document(
            _document(),
            on_complete=lambda: None,
            on_discard=lambda: None,
            store_finished=False,
        )
        assert screen.warning_label.isVisibleTo(screen)
        assert screen.warning_label.text() == models.UNFINISHED_STORE_WARNING
        screen.deleteLater()

    def test_failed_complete_keeps_session_available(self, qapp: Any) -> None:
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()

        def failing() -> None:
            raise RuntimeError("verify failed")

        screen.show_document(
            _document(), on_complete=failing, on_discard=lambda: None
        )
        screen.on_complete()
        assert "Complete failed" in screen.message_label.text()
        # Round 42 LOW-001: the message states only what THIS action
        # verified — the sweep may have destroyed the key independently, so
        # the old unconditional "key was kept" claim was rewritten.
        assert "No key deletion was performed by this action" in (
            screen.message_label.text()
        )
        assert screen.complete_button.isEnabled()  # still actionable
        assert screen.transcript_view.toPlainText() != ""
        screen.deleteLater()

    def test_complete_and_discard_refused_by_a_draft_write_name_the_write(
        self, qapp: Any
    ) -> None:
        """Draft-write plan D9 (round 15): both failure lines show the write's
        line through ``custody_refusal_text``, never the error's own text."""
        from scribe_desktop.session import WriteInFlightError
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()

        def refused_complete() -> None:
            raise WriteInFlightError("complete")

        def refused_discard() -> None:
            raise WriteInFlightError("discard")

        closed: list[str] = []
        screen.closed.connect(closed.append)
        screen.show_document(
            _document(), on_complete=refused_complete, on_discard=refused_discard
        )
        line = models.write_line("write_in_flight")
        screen.on_complete()
        assert screen.message_label.text().startswith(
            f"Complete failed: {line.rstrip('.')}. No key deletion was performed"
        )
        screen.on_discard()
        assert screen.message_label.text() == f"Discard failed: {line}"
        assert closed == []
        assert screen.transcript_view.toPlainText() != ""
        screen.deleteLater()

    def test_a_write_in_flight_disables_the_row_and_refuses_at_the_click(
        self, qapp: Any
    ) -> None:
        """Draft-write Task 5.2 (D9): while the main window's write holds the
        session, Complete, Discard and Generate are disabled and a click
        that still arrives is refused with the write's line; nothing runs."""
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        ran: list[str] = []
        screen.show_document(
            _document(),
            on_complete=lambda: ran.append("complete"),
            on_discard=lambda: ran.append("discard"),
        )
        assert screen.complete_button.isEnabled()
        screen.set_write_blocked(True)
        assert not screen.complete_button.isEnabled()
        assert not screen.discard_button.isEnabled()
        line = models.write_line("write_in_flight")
        screen.on_complete()
        assert screen.message_label.text() == f"Complete refused: {line}"
        screen.on_discard()
        assert screen.message_label.text() == f"Discard refused: {line}"
        assert ran == []
        screen.set_write_blocked(False)
        assert screen.complete_button.isEnabled()
        screen.deleteLater()

    def test_discard_emits_closed(self, qapp: Any) -> None:
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        outcomes: list[str] = []
        screen.closed.connect(outcomes.append)
        screen.show_document(
            _document(), on_complete=lambda: None, on_discard=lambda: None
        )
        screen.on_discard()
        assert outcomes == ["discarded"]
        assert screen.transcript_view.toPlainText() == ""
        screen.deleteLater()

    def test_live_view_appends_posted_windows_without_speakers(self, qapp: Any) -> None:
        """Note-learning plan Task 1.4 (Flow 1): the live view appends each
        posted window's lines under its header — timestamps and [word?] marks,
        never a speaker (the label is LIVE_SPEAKER_PENDING) — and the worker's
        post crosses threads through the queued signal."""
        from PySide6.QtCore import Qt

        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        post = screen.live_poster()  # built inside Start, before the view opens
        screen.begin_live_view()
        assert screen.live_header_label.isVisibleTo(screen)
        assert screen.live_header_label.text() == models.LIVE_TRANSCRIPT_HEADER
        assert screen.transcript_view.toPlainText() == ""
        assert screen.transcript_view.placeholderText() == (
            models.LIVE_TRANSCRIPT_PLACEHOLDER
        )
        # The live view is the SAME display-only box (plan C2).
        assert screen.transcript_view.textInteractionFlags() == (
            Qt.TextInteractionFlag.NoTextInteraction
        )
        poster = threading.Thread(
            target=post,
            args=(_live_segments(0.0, "Hello", "Margaret"),),
        )
        poster.start()
        poster.join()
        assert _process_until(qapp, lambda: screen.transcript_view.toPlainText() != "")
        text = screen.transcript_view.toPlainText()
        assert text == "[00:00-00:02] Hello [Margaret?]"
        assert "pending" not in text
        assert "speaker_" not in text
        post(_live_segments(30.0, "Yes", "Ibuprofen"))
        assert _process_until(
            qapp, lambda: "Yes" in screen.transcript_view.toPlainText()
        )
        assert screen.transcript_view.toPlainText().splitlines() == [
            "[00:00-00:02] Hello [Margaret?]",
            "[00:30-00:32] Yes [Ibuprofen?]",
        ]
        screen.deleteLater()

    def test_final_document_replaces_the_live_view_wholesale(self, qapp: Any) -> None:
        """Task 1.4 / C2: at queued the final document overwrites the live
        lines and the header goes away."""
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        post = screen.live_poster()
        screen.begin_live_view()
        post(_live_segments(0.0, "Hello", "Margaret"))
        qapp.processEvents()
        assert screen.transcript_view.toPlainText() != ""
        document = _document()
        screen.show_document(
            document, on_complete=lambda: None, on_discard=lambda: None
        )
        assert not screen.live_header_label.isVisibleTo(screen)
        assert screen.transcript_view.toPlainText() == (
            models.format_transcript_text(document)
        )
        assert screen._live_active is False
        screen.deleteLater()

    def test_clear_live_view_drops_the_lines_and_late_posts_are_ignored(
        self, qapp: Any
    ) -> None:
        """Task 1.4: Discard during a recording clears the live view, and a
        post that arrives after it closed is DROPPED."""
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        post = screen.live_poster()
        screen.begin_live_view()
        post(_live_segments(0.0, "Hello", "Margaret"))
        qapp.processEvents()
        assert screen.transcript_view.toPlainText() != ""
        screen.clear_live_view()
        assert screen.transcript_view.toPlainText() == ""
        assert not screen.live_header_label.isVisibleTo(screen)
        post(_live_segments(30.0, "Yes", "Ibuprofen"))
        qapp.processEvents()
        assert screen.transcript_view.toPlainText() == ""
        screen.deleteLater()

    def test_a_previous_starts_late_post_is_not_drawn_in_the_new_view(self, qapp: Any) -> None:
        """Round 57 SEC-022: the retired worker's post, still queued when the
        next Start opens its view, carries the old token and is dropped; the
        new worker's post is drawn."""
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        old_post = screen.live_poster()
        screen.begin_live_view()
        new_post = screen.live_poster()  # the next Start builds its worker...
        screen.begin_live_view()  # ...then opens its view
        thread = threading.Thread(
            target=old_post, args=(_live_segments(0.0, "Hello", "Margaret"),)
        )
        thread.start()  # the old worker's post, queued across threads
        thread.join()
        qapp.processEvents()
        assert screen.transcript_view.toPlainText() == ""
        new_post(_live_segments(30.0, "Yes", "Ibuprofen"))
        assert _process_until(qapp, lambda: screen.transcript_view.toPlainText() != "")
        assert screen.transcript_view.toPlainText() == "[00:30-00:32] Yes [Ibuprofen?]"
        screen.deleteLater()

    def test_a_start_that_made_no_poster_draws_no_old_post(self, qapp: Any) -> None:
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        old_post = screen.live_poster()
        screen.begin_live_view()
        screen.begin_live_view()  # a Start with no live worker built
        old_post(_live_segments(0.0, "Hello", "Margaret"))
        qapp.processEvents()
        assert screen.transcript_view.toPlainText() == ""
        assert screen.live_segments((None, ())) is None  # no current token at all
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Main window wiring.
# ---------------------------------------------------------------------------


class TestMainWindow:
    def test_constructs_all_screens(self, qapp: Any, tmp_path: Path) -> None:
        window = _main_window(tmp_path)
        assert window.tabs.count() == 8
        titles = [window.tabs.tabText(i) for i in range(window.tabs.count())]
        assert titles == [
            "Microphone",
            "Session",
            "Recovery",
            "Transcript",
            "Note",
            "Practitioner",
            "Clinics",
            "Status",
        ]
        window.close()

    def test_live_transcript_routed_to_inspection_view(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        window = _main_window(tmp_path, controller)
        window.session_screen.transcript_ready.emit(_document())
        qapp.processEvents()
        assert window.tabs.currentWidget() is window.transcript_screen
        assert "[Margaret?]" in window.transcript_screen.transcript_view.toPlainText()
        # Complete routes to the controller (live custody path).
        window.transcript_screen.on_complete()
        assert ("complete",) in controller.calls
        window.close()

    def test_live_transcriber_factory_registered_and_opens_the_live_view(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Note-learning plan Task 1.4: the window registers the live worker's
        factory with the controller; the factory ONLY builds (round 7
        LOW-003: a failed Start must not open the view), the Session screen's
        successful Start opens the live view, and its Discard closes it
        again. The worker itself is never started here."""
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        assert ("set_live_transcriber_factory",) in controller.calls
        factory = controller.live_transcriber_factory
        assert callable(factory)
        worker = factory()
        assert isinstance(worker, LiveTranscriber)
        header = window.transcript_screen.live_header_label
        assert not header.isVisibleTo(window.transcript_screen)  # building opens nothing
        window.session_screen.session_started.emit()
        assert header.isVisibleTo(window.transcript_screen)
        window.session_screen.session_discarded.emit()
        assert not header.isVisibleTo(window.transcript_screen)
        window.close()

    def test_a_window_built_with_the_seam_never_probes_the_host(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Phase H round 24 MED-006: the language model's presence reaches
        the Practitioner tab and the prose stage through the window's seam
        — the real host is never asked, at construction or on the poll."""

        def forbidden() -> bool:
            raise AssertionError("the host must not be probed")

        monkeypatch.setattr(models, "language_model_available", forbidden)
        window = _main_window(tmp_path)
        window.practitioner_screen.refresh_availability()
        window.practitioner_screen.refresh_availability()
        assert not window.practitioner_screen.style_radios["narrative"].isEnabled()
        window.close()

    def test_start_releases_an_open_recovered_view_before_the_live_view_opens(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Phase H round 24 MED-001: a successful Start drops whatever the
        transcript screen held — a RECOVERED document's only route to its
        Complete/Discard — so the window must first destroy the retained
        key copy and release that session's checkout; otherwise a Discard
        during the recording leaves it checked out with its key resident and
        no control able to finish it until restart."""
        recovered_id = _make_recoverable(tmp_path, finished=True)
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        window.recovery_screen._protected.add(recovered_id)
        outcome = RecoveryOutcome(
            document=_document(), crypto=SessionCrypto(), store_finished=True
        )
        window.recovery_screen.recovered.emit((tmp_path / recovered_id, outcome))
        qapp.processEvents()
        assert window._recovered_crypto is not None
        assert window._transcript_source == recovered_id
        assert recovered_id in window.recovery_screen.protected_session_ids()

        window.session_screen.session_started.emit()
        assert window._recovered_crypto is None
        assert window._transcript_source is None
        assert recovered_id not in window.recovery_screen.protected_session_ids()
        assert ("destroy_recovered_crypto",) in controller.calls
        header = window.transcript_screen.live_header_label
        assert header.isVisibleTo(window.transcript_screen)
        # A Discard during the recording leaves nothing checked out behind.
        window.session_screen.session_discarded.emit()
        assert window.recovery_screen.protected_session_ids() == frozenset()
        window.close()

    def test_start_over_a_live_view_releases_no_checkout(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """The "live" source needs nothing at Start (the controller retired
        that session); an unrelated recovered checkout is untouched."""
        other_id = uuid.uuid4().hex
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        window = _main_window(tmp_path, controller)
        window.recovery_screen._protected.add(other_id)
        window.session_screen.transcript_ready.emit(_document())
        qapp.processEvents()
        assert window._transcript_source == "live"
        window.session_screen.session_started.emit()
        assert window._transcript_source is None
        assert other_id in window.recovery_screen.protected_session_ids()
        assert ("destroy_recovered_crypto",) not in controller.calls
        window.close()

    def test_close_refused_while_transcribing(self, qapp: Any, tmp_path: Path) -> None:
        """PR round 18 (PR6): closing must not destroy a running worker."""
        from PySide6.QtGui import QCloseEvent

        window = _main_window(tmp_path)
        window.session_screen._transcribing = True
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        window.session_screen._transcribing = False
        event2 = QCloseEvent()
        window.closeEvent(event2)
        assert event2.isAccepted()

    def test_close_refused_while_recording(self, qapp: Any, tmp_path: Path) -> None:
        """Round 42 MED-002 (guard-only, pending user ratification): closing
        mid-recording would kill the daemon capture worker and silently drop
        the buffered tail of a live consultation — refuse, like the PR6
        thread guard refuses for a running benchmark."""
        from PySide6.QtGui import QCloseEvent

        controller = FakeController()
        window = _main_window(tmp_path, controller)
        for blocked_state in (SessionState.RECORDING, SessionState.PAUSED):
            controller.state_value = blocked_state
            event = QCloseEvent()
            window.closeEvent(event)
            assert not event.isAccepted(), blocked_state
        controller.state_value = SessionState.IDLE
        event2 = QCloseEvent()
        window.closeEvent(event2)
        assert event2.isAccepted()

    def test_benchmark_refused_while_session_active(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 42 LOW-002 (guard-only, pending user ratification): the
        benchmark saturates the CPU for minutes and can starve live capture
        into a queue-overflow failure — never startable during an active
        session."""
        from scribe_desktop.ui.microphone import MicrophoneScreen

        controller = FakeController()
        screen = MicrophoneScreen(
            controller,
            FakeBackend(),
            benchmark_runner=lambda: pytest.fail("benchmark must not start"),
            profile_root=tmp_path,
        )
        for active_state in (
            SessionState.RECORDING,
            SessionState.PAUSED,
            SessionState.PROCESSING,
        ):
            controller.state_value = active_state
            screen.on_run_benchmark()
            assert not screen.is_busy, active_state
            assert "unavailable while a session is active" in (
                screen.benchmark_output.toPlainText()
            )
        screen.stop_monitor()

    def test_recovered_checkout_crypto_destroyed_on_live_overwrite(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 42 LOW-006: when a live transcript overwrites an open
        recovered checkout, the checkout's unwrapped in-memory key must be
        zeroized (its custody callbacks are unreachable; disk custody stays
        for a post-restart recovery)."""
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        crypto = SessionCrypto()
        directory = tmp_path / uuid.uuid4().hex
        directory.mkdir()
        outcome = RecoveryOutcome(
            document=_document(), crypto=crypto, store_finished=True
        )
        window._on_recovered((directory, outcome))
        assert not crypto.destroyed  # checkout open: key usable for custody
        controller.state_value = SessionState.QUEUED
        window.session_screen.transcript_ready.emit(_document())
        qapp.processEvents()
        assert crypto.destroyed  # overwritten checkout's key copy zeroized
        # disk custody untouched by the in-memory destroy (no key file was
        # ever created here — the destroy must not try to touch disk)
        assert not (directory / KEY_FILENAME).exists()
        window.close()

    def _recovered_window(
        self, tmp_path: Path
    ) -> tuple[Any, FakeController, Path, SessionCrypto]:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        crypto = SessionCrypto()
        directory = tmp_path / uuid.uuid4().hex
        directory.mkdir()
        outcome = RecoveryOutcome(document=_document(), crypto=crypto, store_finished=True)
        window._on_recovered((directory, outcome))
        return window, controller, directory, crypto

    def test_recovered_custody_routes_through_the_coordinator(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Task 6.3: the recovered transcript view's Complete/Discard run
        through the controller's lease-aware coordinator, never through raw
        store primitives."""
        window, controller, directory, crypto = self._recovered_window(tmp_path)
        window.transcript_screen.on_complete()
        assert ("complete_recovered", directory) in controller.calls
        assert crypto.destroyed
        window.close()

    def test_recovered_discard_routes_through_the_coordinator(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window, controller, directory, crypto = self._recovered_window(tmp_path)
        window.transcript_screen.on_discard()
        assert ("discard_recovered", directory) in controller.calls
        assert crypto.destroyed
        window.close()

    def test_recovered_complete_refused_while_generating(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """A held generation lease blocks recovered Complete: the refusal
        surfaces in the view, custody survives, the view stays open."""
        window, controller, directory, crypto = self._recovered_window(tmp_path)
        controller.generation_error = GenerationInProgressError(
            "complete refused: a note generation is in progress"
        )
        window.transcript_screen.on_complete()
        assert ("complete_recovered", directory) in controller.calls
        assert not crypto.destroyed
        assert "Complete failed" in window.transcript_screen.message_label.text()
        # The view did not close: its custody callbacks are still armed.
        assert window.transcript_screen.complete_button.isEnabled()
        window.close()

    def test_destroy_recovered_crypto_retained_while_generating(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Task 6.3 Done-when: `_destroy_recovered_crypto`-during-generation.
        The coordinator refuses, the in-memory key survives for the worker,
        and the retained reference is cleaned up on the next (post-release)
        pass."""
        window, controller, _directory, crypto = self._recovered_window(tmp_path)
        controller.generation_error = GenerationInProgressError(
            "recovered-key destruction refused: a note generation is in progress"
        )
        window._destroy_recovered_crypto()
        assert not crypto.destroyed
        assert window._recovered_crypto is crypto  # reference retained for cleanup
        controller.generation_error = None  # generation released
        window._destroy_recovered_crypto()
        assert crypto.destroyed
        assert window._recovered_crypto is None
        window.close()

    def test_destroy_recovered_crypto_retained_while_discard_reserved(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 30: the coordinator's coarse reservation refusal
        (SessionActivityError) is caught the same way as the generation
        refusal — key retained, cleaned up after release."""
        window, controller, _directory, crypto = self._recovered_window(tmp_path)
        controller.generation_error = SessionActivityError(
            "recovered-key destruction refused: a discard is in flight"
        )
        window._destroy_recovered_crypto()
        assert not crypto.destroyed
        assert window._recovered_crypto is crypto
        controller.generation_error = None
        window._destroy_recovered_crypto()
        assert crypto.destroyed
        window.close()

    def test_live_session_ids_include_reserved_discard_targets(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 30: the recovery-list exclusion is sourced from the
        controller's RESERVATION SET, not only the mutable live session."""
        reserved_id = uuid.uuid4().hex
        controller = FakeController()
        controller.reserved_ids = frozenset({reserved_id})
        window = _main_window(tmp_path, controller)
        assert reserved_id in window._live_session_ids()
        window.close()

    def test_stale_recovery_resume_refused_at_click_time(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 30: the rendered list can be stale — a session reserved by
        an in-flight discard AFTER listing must be refused at resume time,
        BEFORE any key unwrap."""
        recovered_id = _make_recoverable(tmp_path, finished=True)
        controller = FakeController()
        window = _main_window(
            tmp_path, controller, recovery_runner=lambda d: pytest.fail("must never unwrap")
        )
        assert window.recovery_screen.session_list.count() == 1
        window.recovery_screen.session_list.setCurrentRow(0)
        controller.reserved_ids = frozenset({recovered_id})  # discard begins now
        window.recovery_screen.on_resume_processing()
        assert not window.recovery_screen.is_busy  # refused before any unwrap
        assert "busy elsewhere" in window.recovery_screen.message_label.text()
        window.close()

    def test_live_session_ids_is_one_atomic_snapshot(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 31: the exclusion set is ONE controller snapshot — the
        window must not compose split reserved/live reads, because a
        Discard-reserve + admitted Start between two reads yields a set
        omitting the still-reserved session."""
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        snap_id = uuid.uuid4().hex
        calls: list[str] = []

        def atomic() -> frozenset[str]:
            calls.append("snapshot")
            return frozenset({snap_id})

        def split_read() -> frozenset[str]:
            pytest.fail("split read: a consumer composed reserved_session_ids")

        controller.custody_protected_ids = atomic  # type: ignore[method-assign]
        controller.reserved_session_ids = split_read  # type: ignore[method-assign]
        assert window._live_session_ids() == frozenset({snap_id})
        assert calls == ["snapshot"]
        window.close()

    def test_stale_recovery_discard_refused_at_click_time(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        recovered_id = _make_recoverable(tmp_path, finished=True)
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        assert window.recovery_screen.session_list.count() == 1
        window.recovery_screen.session_list.setCurrentRow(0)
        controller.reserved_ids = frozenset({recovered_id})
        window.recovery_screen.on_discard()
        assert (tmp_path / recovered_id).exists()  # custody untouched
        assert "busy elsewhere" in window.recovery_screen.message_label.text()
        window.close()

    def test_live_controller_session_excluded_from_recovery_list(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR round 18 (PR1): a queued/failed session the controller still
        owns must not be offered through the recovery custody path."""
        session_id = _make_recoverable(tmp_path, finished=True)
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        controller.session_value = RecordingSession.model_construct(
            session_id=session_id,
            encounter_context=None,
            consent=unlinked_consent(),
            key_reference="key.dpapi",
            state=SessionState.QUEUED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        window = _main_window(tmp_path, controller)
        assert window.recovery_screen.session_list.count() == 0
        controller.session_value = None
        window.recovery_screen.refresh()
        assert window.recovery_screen.session_list.count() == 1
        window.close()

    def test_live_transcript_close_never_releases_recovered_checkout(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR round 20 (PR-HIGH-009): closing a LIVE transcript must not
        strip an unrelated checkout's sweep/relist protection. Cliniko
        workflow safeguards plan Task 5.4 replaced the hold-until-restart
        residue: the recovered view the live transcript REPLACES loses its
        callbacks, so its checkout is released then (scoped, by id); a
        checkout the live view never replaced keeps its protection."""
        recovered_id = _make_recoverable(tmp_path, finished=True)
        other_id = uuid.uuid4().hex
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        window = _main_window(tmp_path, controller)
        # Simulate an open recovered transcript (checked out) beside another.
        window.recovery_screen._protected.update({recovered_id, other_id})
        outcome = RecoveryOutcome(
            document=_document(), crypto=SessionCrypto(), store_finished=True
        )
        window.recovery_screen.recovered.emit((tmp_path / recovered_id, outcome))
        qapp.processEvents()
        assert recovered_id in window.recovery_screen.protected_session_ids()
        # A live transcript replaces the view: the replaced checkout goes.
        window.session_screen.transcript_ready.emit(_document())
        qapp.processEvents()
        assert recovered_id not in window.recovery_screen.protected_session_ids()
        assert window._recovered_crypto is None
        window.transcript_screen.on_complete()  # live path -> controller
        qapp.processEvents()
        assert ("complete",) in controller.calls
        # The unrelated checkout's protection survives the live closure.
        assert other_id in window.recovery_screen.protected_session_ids()
        window.close()

    def test_a_complete_after_a_write_ends_on_the_written_done_line(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Draft-write D6 (seen mode, PR-LOW-014): ``closed("written")`` runs
        the ordinary close cleanup, then the Session screen shows the
        terminal ``written_done`` line — after its refresh, so it stays."""
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        controller.session_value = RecordingSession(consent=unlinked_consent()).with_state(
            SessionState.QUEUED
        )
        controller.write_status = WriteRecordStatus("written", note_matches=True)
        window = _main_window(tmp_path, controller)
        window.session_screen.transcript_ready.emit(_document())
        qapp.processEvents()
        window.transcript_screen.on_complete()
        qapp.processEvents()
        assert ("complete_after_write",) in controller.calls
        assert ("complete",) not in controller.calls
        assert window.session_screen.message_label.text() == models.write_line("written_done")
        assert window.tabs.currentWidget() is window.session_screen
        assert window._transcript_source is None
        window.close()

    def test_the_ref_prune_keeps_live_and_indexed_refs_and_drops_the_rest(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """SIMP-016 (PR-LOW-022): a ref that is neither the live session's
        nor a still-indexed session's — an unlinked or failed recording's,
        kept through retirement — is forgotten; the others stay."""
        from scribe_desktop.context_rules import ReminderEntry

        controller = FakeController()
        live = RecordingSession(consent=unlinked_consent()).with_state(SessionState.QUEUED)
        controller.session_value = live
        window = _main_window(tmp_path, controller)
        indexed, unlinked = uuid.uuid4().hex, uuid.uuid4().hex
        for session_id in (live.session_id, indexed, unlinked):
            controller.register_session_ref(session_id)
        window.reminders.add(ReminderEntry("clinic-1", "note-1", indexed))
        window.prune_session_refs()
        assert controller.referenced_session_ids() == {live.session_id, indexed}
        assert controller.forgotten_refs == [unlinked]
        window.close()

    def test_a_sweep_prune_forgets_an_expired_sessions_reminder_and_ref(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """The reminder prune keeps its key-existence rule; the ref prune runs
        right after it, so an expired indexed session loses both, a kept one
        neither, and an unindexed ref goes too."""
        from scribe_desktop.context_rules import ReminderEntry

        controller = FakeController()
        window = _main_window(tmp_path, controller)
        kept, expired, unlinked = (uuid.uuid4().hex for _ in range(3))
        (tmp_path / kept).mkdir()
        (tmp_path / kept / KEY_FILENAME).write_bytes(b"x" * 64)
        for session_id in (kept, expired):
            window.reminders.add(ReminderEntry("clinic-1", "note-1", session_id))
        for session_id in (kept, expired, unlinked):
            controller.register_session_ref(session_id)
        window.prune_reminders()
        assert window.reminders.session_ids() == {kept}
        assert controller.referenced_session_ids() == {kept}
        assert sorted(controller.forgotten_refs) == sorted([expired, unlinked])
        window.close()

    def test_recovered_transcript_close_releases_only_itself(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        recovered_id = _make_recoverable(tmp_path, finished=True)
        other_id = uuid.uuid4().hex
        window = _main_window(tmp_path)
        window.recovery_screen._protected.update({recovered_id, other_id})
        crypto = SessionCrypto()
        outcome = RecoveryOutcome(
            document=_document(), crypto=crypto, store_finished=True
        )
        window.recovery_screen.recovered.emit((tmp_path / recovered_id, outcome))
        qapp.processEvents()
        window.transcript_screen.on_discard()  # discards the recovered store
        qapp.processEvents()
        protected = window.recovery_screen.protected_session_ids()
        assert recovered_id not in protected
        assert other_id in protected  # scoped release: others untouched
        window.close()

    def test_recovered_transcript_carries_unfinished_warning(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _main_window(tmp_path)
        outcome = RecoveryOutcome(
            document=_document(), crypto=SessionCrypto(), store_finished=False
        )
        window.recovery_screen.recovered.emit((tmp_path / uuid.uuid4().hex, outcome))
        qapp.processEvents()
        assert window.tabs.currentWidget() is window.transcript_screen
        assert window.transcript_screen.warning_label.isVisibleTo(
            window.transcript_screen
        )
        window.close()

    # --- Practitioner tab wiring (practitioner-profile plan Phase 3) --------

    def test_first_run_selects_the_practitioner_tab_with_the_banner(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """D10: with no profile the window opens ON the Practitioner tab and
        shows the banner — first run ASKS, it never blocks."""
        window = _main_window(tmp_path)
        screen = window.practitioner_screen
        assert window.tabs.currentWidget() is screen
        assert screen.banner_label.isVisibleTo(screen)
        # Note-learning plan Task 3.4: with no learned style either, the
        # banner carries the optional sample-note line.
        assert screen.banner_label.text() == models.first_run_banner_text(style_present=False)
        assert models.FIRST_RUN_STYLE_LINE in screen.banner_label.text()
        window.close()

    @windows_only
    def test_startup_with_a_profile_stays_on_the_microphone_tab(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.practitioner_profile import (
            ConsentRecord,
            PractitionerProfile,
            save_profile,
        )
        from scribe_desktop.speaker_embedding import shipped_embedder_identity
        model_id, model_sha256 = shipped_embedder_identity()
        now = datetime.now(UTC)
        save_profile(
            PractitionerProfile(
                model_id=model_id,
                model_sha256=model_sha256,
                embedding=(0.6, 0.8),
                embedding_dim=2,
                created_at=now,
                enrolment_speech_seconds=31.0,
                device_name="Mic",
                consent=ConsentRecord(
                    accepted_at=now,
                    consent_text_version=models.CONSENT_TEXT_VERSION,
                    learning_opt_in=False,
                ),
            ),
            root=tmp_path,
        )
        window = _main_window(tmp_path)
        screen = window.practitioner_screen
        assert window.tabs.currentWidget() is window.microphone_screen
        assert not screen.banner_label.isVisibleTo(screen)
        assert screen.profile_present
        # With the speaker model file absent on this host the D2 fallback line
        # stands in for the saved-on date; either is correct here.
        status = screen.profile_status_label.text()
        assert status.startswith("Voice profile saved") or (
            status == models.SPEAKER_MODEL_MISSING_REASON
        )
        window.close()

    def test_benchmark_blocker_is_registered_for_enrolment(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """D15: `begin_enrolment` cannot see the benchmark worker, so the
        window registers it as the blocker."""
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        assert ("set_enrolment_blocker",) in controller.calls
        assert controller.blocker is not None
        assert controller.blocker() is None
        window.microphone_screen._benchmark_task = _Running()
        assert controller.blocker() == "a benchmark is running"
        window.microphone_screen._benchmark_task = None
        window.close()

    def test_close_refused_while_enrolling(self, qapp: Any, tmp_path: Path) -> None:
        from PySide6.QtGui import QCloseEvent

        controller = FakeController()
        window = _main_window(tmp_path, controller)
        controller.enrolling = True
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        assert "Voice enrolment in progress" in window.statusBar().currentMessage()
        controller.enrolling = False
        window.close()

    def test_close_refused_while_the_practitioner_tab_is_busy(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """The activity spans the result handler, so a finished-but-unhandled
        enrolment still refuses the close (the PR6 thread guard)."""
        from PySide6.QtGui import QCloseEvent

        window = _main_window(tmp_path)
        window.practitioner_screen._task = _Running()
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        assert "Voice enrolment in progress" in window.statusBar().currentMessage()
        window.practitioner_screen._task = None
        window.close()

    def test_practitioner_tab_hands_the_monitor_over_synchronously(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Peer round 27 PR-MED-022: the tab's capture-start hook IS the
        microphone screen's `stop_monitor`, so the idle monitor closes on the
        GUI thread before the enrolment worker starts."""
        window = _main_window(tmp_path)
        assert window.practitioner_screen._on_capture_start == (
            window.microphone_screen.stop_monitor
        )
        window.close()

    def test_profile_reads_never_touch_the_default_root(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Peer round 27 PR-REG-005: with `profile_root` supplied, neither the
        microphone screen's report (construction, a device refresh, the timer
        refresh) nor the Practitioner tab's re-read reaches the default
        store. Round 51 LOW-001: the same holds for the config store — the
        Practitioner tab's learned-phrase read never reaches the default
        config root either."""
        from scribe_desktop import note_config, practitioner_profile
        def forbidden() -> Path:
            raise AssertionError("the default profile root must not be consulted")

        monkeypatch.setattr(practitioner_profile, "default_profile_root", forbidden)
        monkeypatch.setattr(note_config, "default_config_root", forbidden)
        window = _main_window(tmp_path)
        window.microphone_screen.refresh_model_status()
        window.microphone_screen.refresh_devices()
        window.practitioner_screen.refresh_profile_state()
        window.practitioner_screen.refresh_learned_phrases()
        assert "Voice profile: not enrolled" in window.microphone_screen.model_status_label.text()
        window.close()


# ---------------------------------------------------------------------------
# Phase 7 note-review fixtures + tests.
# ---------------------------------------------------------------------------

_NOTE_SESSION_ID = "e" * 32


def _note_config() -> NoteConfig:
    profile = TemplateProfile(
        template_profile_id="clinic-a",
        display_name="Clinic A",
        template_targets=(
            TemplateTarget(
                target_id="t-main", group="Notes", field_label="Main", target_type="rich_text"
            ),
        ),
        section_mappings=tuple(
            SectionMapping(section_key=key, target_id="t-main")
            for key in CANONICAL_SECTION_KEYS
            if key != "consent"
        ),
        intentionally_unmapped=("consent",),
    )
    # Note-learning plan D5 (Phase 2): a HAND-authored rule now PRE-FILLS its
    # line (no confirm/decline row), so the fixture's autofill rule carries a
    # LEARNED id with no sidecar record — the one shape that still PROPOSES —
    # to keep the per-line confirm/decline/retract path under test. The
    # prefill seed pre-fills, as every hand-authored entry does now.
    return NoteConfig(
        template_profiles=(profile,),
        autofill_rules=(
            AutofillRule(
                rule_id=_LEARNED_RULE_ID,
                section_key="advice_home_exercise",
                trigger_phrase="ice pack",
                expansion=("Ice pack use explained.",),
            ),
        ),
        prefill_templates=(
            PrefillTemplate(
                prefill_id="knee-exam",
                display_name="Knee examination",
                region_keywords=("knee",),
                seed_assertions=(
                    PrefillSeedAssertion(
                        section_key="objective_examination", seed_text="Knee effusion assessed."
                    ),
                ),
            ),
        ),
    )


_LEARNED_RULE_ID = "learned-01J8ZK3Q9W4E5R6T7Y8U9I0O1P"


def _hand_authored_config() -> NoteConfig:
    """`_note_config` with a HAND-authored autofill rule: under D5 both its
    line and the prefill seed arrive pre-filled (config-decided)."""
    base = _note_config()
    return NoteConfig(
        template_profiles=base.template_profiles,
        autofill_rules=(
            AutofillRule(
                rule_id="rule-ice",
                section_key="advice_home_exercise",
                trigger_phrase="ice pack",
                expansion=("Ice pack use explained.",),
            ),
        ),
        prefill_templates=base.prefill_templates,
    )


def _note_words(text: str, *, probability: float = 0.9) -> tuple[TranscriptWord, ...]:
    return tuple(
        TranscriptWord(
            word_text=token,
            start_seconds=index * 0.3,
            end_seconds=index * 0.3 + 0.25,
            probability=probability,
            uncertain=probability < 0.60,
        )
        for index, token in enumerate(text.split())
    )


_NOTE_TURNS: tuple[tuple[str, str], ...] = (
    ("My left knee is sore when I walk", SPEAKER_1),
    ("On examination the range of motion is limited", SPEAKER_2),
    ("The diagnosis is a mild knee sprain", SPEAKER_2),
    ("Please use an ice pack tonight", SPEAKER_2),
)


def _note_document(turns: tuple[tuple[str, str], ...] = _NOTE_TURNS) -> TranscriptDocument:
    return TranscriptDocument(
        session_id=_NOTE_SESSION_ID,
        created_at=datetime.now(UTC),
        model_name="mock",
        sample_rate=16_000,
        transcript_segments=tuple(
            TranscriptSegment(
                start_seconds=float(index * 10),
                end_seconds=float(index * 10 + 5),
                speaker=speaker,
                transcript_words=_note_words(text),
            )
            for index, (text, speaker) in enumerate(turns)
        ),
    )


def _note_result(clinician: str | None = SPEAKER_2) -> models.NoteGenerationResult:
    document = _note_document()
    config = _note_config()
    draft = compose_draft(
        document, config, ExtractiveNoteProvider(), clinician_speaker=clinician
    )
    return models.NoteGenerationResult(draft=draft, config=config, document=document)


def _low_confidence_result() -> tuple[models.NoteGenerationResult, str]:
    """A result whose transcript carries a low-`probability` word in a patient
    utterance that matches no cue — omitted from the note, but reachable in
    the transcript panel (Task 7.6)."""
    marked_word = "wobbly"
    words = (
        TranscriptWord(
            word_text="It", start_seconds=0.0, end_seconds=0.2, probability=0.95, uncertain=False
        ),
        TranscriptWord(
            word_text="felt", start_seconds=0.2, end_seconds=0.4, probability=0.95, uncertain=False
        ),
        TranscriptWord(
            word_text=marked_word,
            start_seconds=0.4,
            end_seconds=0.7,
            probability=0.30,
            uncertain=True,
        ),
    )
    document = TranscriptDocument(
        session_id=_NOTE_SESSION_ID,
        created_at=datetime.now(UTC),
        model_name="mock",
        sample_rate=16_000,
        transcript_segments=(
            TranscriptSegment(
                start_seconds=0.0, end_seconds=1.0, speaker=SPEAKER_1, transcript_words=words
            ),
            TranscriptSegment(
                start_seconds=10.0,
                end_seconds=15.0,
                speaker=SPEAKER_2,
                transcript_words=_note_words("On examination the range of motion is limited"),
            ),
        ),
    )
    config = _note_config()
    draft = compose_draft(document, config, ExtractiveNoteProvider(), clinician_speaker=SPEAKER_2)
    return models.NoteGenerationResult(draft=draft, config=config, document=document), marked_word


# ---------------------------------------------------------------------------
# models view-logic (Task 7.4).
# ---------------------------------------------------------------------------


class TestNoteViewModels:
    def test_provenance_labels_distinguish_sources(self) -> None:
        assert models.provenance_label("transcript") == "from transcript"
        assert "clinician-authored" in models.provenance_label("autofill")
        assert "clinician-authored" in models.provenance_label("prefill")
        # Note-learning plan schema v2 (D4): a typed line is named as typed
        # and as the clinician's — never mistaken for a quote or a rule.
        typed = models.provenance_label("clinician")
        assert "typed" in typed
        assert "clinician-authored" in typed
        assert len({models.provenance_label(p) for p in ("transcript", "clinician")}) == 2

    def test_summarise_warnings_splits_and_groups(self) -> None:
        result = _note_result()
        # Nothing confirmed: every proposal is pending -> unconfirmed_proposal.
        note = finalise_note(result.draft, [], result.document, result.config)
        summary = models.summarise_warnings(note.note_warnings)
        assert summary.blocking  # unconfirmed_proposal errors, grouped
        assert all(group.severity == "error" for group in summary.blocking)
        assert all(group.severity == "review" for group in summary.review)
        # Grouped by code, not one row per finding.
        codes = [group.code for group in summary.blocking]
        assert len(codes) == len(set(codes))

    def test_laterality_mismatch_copy_is_source_neutral(self) -> None:
        """Round 59 PR-LOW-001. `laterality_mismatch` is emitted by TWO
        populations: an authored line against the transcript, and two
        authored lines against each other with no transcript evidence at all
        (`test_authored_pair_conflict_fires_on_the_later_assertion` pins
        `source_coords is None`). The title must be true of BOTH, so it may
        not claim a transcript comparison; the clear-hint may still point the
        clinician at the transcript, which is a real control and the right
        thing to check either way."""
        copy = models.WARNING_COPY["laterality_mismatch"]
        assert "transcript" not in copy.title.lower()
        assert copy.blocks is None  # review, never a block (Task H4.1)
        assert "acknowledge" in copy.clear_hint.lower()

    def test_every_registered_warning_code_has_copy(self) -> None:
        # No fallback copy may be reachable in shipping: `_fallback_copy`
        # renders a raw code and no clear-path, which is exactly the
        # fictitious/absent-clear-path class rounds 35 and 45 both hit.
        assert set(models.WARNING_COPY) == set(NOTE_WARNING_SEVERITY)
        for code, severity in NOTE_WARNING_SEVERITY.items():
            copy = models.WARNING_COPY[code]
            assert copy.clear_hint.strip()
            # An `error` names the action it blocks; a `review` blocks nothing.
            assert (copy.blocks is not None) is (severity == "error")

    def test_clear_hints_name_no_unbuilt_surface(self) -> None:
        """Round 45 MED-002 regression pin.

        `mapping_drop`'s hint used to send the clinician to an "Unmapped
        content" heading — the round-2 MAPPED-OUTPUT target, which is Phase
        4's and exists nowhere in this app. The dropped section is rendered
        in the note body like any other populated canonical section, so the
        hint must describe the missing TEMPLATE FIELD, never a missing view.
        """
        for copy in models.WARNING_COPY.values():
            assert "unmapped content" not in copy.clear_hint.lower()
        hint = models.WARNING_COPY["mapping_drop"].clear_hint
        assert "shown in the note" in hint

    def test_complete_block_reason(self) -> None:
        assert models.complete_block_reason(models.NoteReviewState()) is None
        assert models.complete_block_reason(
            models.NoteReviewState(generating=True)
        ) is not None
        assert models.complete_block_reason(
            models.NoteReviewState(has_note=True, unconfirmed_proposals=1)
        ) is not None
        assert models.complete_block_reason(
            models.NoteReviewState(has_note=True, blocking_errors=1)
        ) is not None
        assert models.complete_block_reason(
            models.NoteReviewState(has_note=True, note_saved=False)
        ) is not None
        assert models.complete_block_reason(
            models.NoteReviewState(
                has_note=True, note_saved=True, unacknowledged_reviews=1
            )
        ) is not None
        assert models.complete_block_reason(
            models.NoteReviewState(has_note=True, note_saved=True)
        ) is None

    def test_config_report_lines(self) -> None:
        lines = models.config_report_lines(_note_config(), "clinic-a")
        joined = "\n".join(lines)
        assert "Autofill rules: 1" in joined
        assert "Prefill regions: 1" in joined
        assert "Clinic A" in joined

    def test_render_proposal_reuses_format_timestamp(self) -> None:
        result = _note_result()
        autofill = next(
            p for p in result.draft.note_proposals if p.provenance == "autofill"
        )
        rendered = models.render_proposal(autofill)
        assert rendered.excerpt == autofill.note_excerpt
        # Attribution reuses format_timestamp (mm:ss) for the trigger time.
        assert ":" in rendered.attribution

    def test_speaker_quotations_one_per_cluster(self) -> None:
        quotes = models.speaker_quotations(_note_document())
        assert set(quotes) == {SPEAKER_1, SPEAKER_2}
        assert quotes[SPEAKER_1].startswith("My left knee")


# ---------------------------------------------------------------------------
# Note tab (Task 7.1 + 7.6).
# ---------------------------------------------------------------------------


class TestNoteScreen:
    def _screen(
        self, *, copy_enabled: bool = False, result: models.NoteGenerationResult | None = None
    ) -> tuple[Any, dict[str, list[Any]]]:
        from scribe_desktop.ui.note import NoteScreen

        record: dict[str, list[Any]] = {
            "saved": [],
            "abandoned": [],
            "cancelled": [],
            "states": [],
        }
        screen = NoteScreen()
        screen.begin_review(
            result if result is not None else _note_result(),
            copy_enabled=copy_enabled,
            on_save=lambda note: record["saved"].append(note),
            on_abandon=lambda: record["abandoned"].append(True),
            on_cancel=lambda: record["cancelled"].append(True),
            on_state_changed=lambda state: record["states"].append(state),
            template_profile_id="clinic-a",
        )
        return screen, record

    def _confirm_all(self, screen: Any) -> None:
        for proposal in screen._draft.note_proposals:
            screen.confirm_proposal(proposal.proposal_id)

    def test_the_review_renders_under_the_saved_writing_style(self, qapp: Any) -> None:
        """Note-learning plan Task 3.2 (D7): the style the provider reads at
        review start is stamped on every finalised note and the body is THE
        one rendering path under it; a prose style with no language model
        renders as Clean clinical and the info line says so (C8); an
        unreadable setting names itself; a screen built without a provider
        renders ``verbatim`` (the schema's own default)."""
        from scribe_desktop.note import render_note
        from scribe_desktop.ui.note import NoteScreen

        plain, _record = self._screen()
        assert plain.note_style == "verbatim" and plain._note.style == "verbatim"
        assert plain.note_body.toPlainText() == render_note(plain._note, "verbatim")
        plain.deleteLater()

        def _screen_for(choice: models.NoteStyleChoice) -> Any:
            screen = NoteScreen(note_style_provider=lambda: choice)
            screen.begin_review(
                _note_result(),
                on_save=lambda note: None,
                on_abandon=lambda: None,
                template_profile_id="clinic-a",
            )
            return screen

        clean = _screen_for(models.NoteStyleChoice("clean", None))
        assert clean.note_style == "clean" and clean._note.style == "clean"
        assert clean.note_body.toPlainText() == render_note(clean._note, "clean")
        assert clean.note_body.toPlainText() == models.format_note_body(clean._note)
        assert "Clean clinical" not in clean.info_label.text()
        clean.deleteLater()

        prose = _screen_for(models.NoteStyleChoice("own_voice", None))
        assert prose._note.style == "own_voice"
        assert prose.note_body.toPlainText() == render_note(prose._note, "clean")
        fallback = models.style_fallback_line("own_voice")
        assert fallback is not None and fallback in prose.info_label.text()
        prose.deleteLater()

        reason = models.STYLE_SETTING_UNREADABLE_LINE.format(reason="boom")
        unreadable = _screen_for(models.NoteStyleChoice("clean", reason))
        assert reason in unreadable.info_label.text()
        assert unreadable._note.style == "clean"
        unreadable.deleteLater()

    def test_a_typed_line_is_neither_a_quoted_segment_nor_a_provider_line(
        self, qapp: Any
    ) -> None:
        """Note-learning plan Task 0.2, the two `ui/note.py` provenance
        branches (`_segments_in_note`, `_provider_line_exists`): a typed
        ``clinician`` line in the working note quotes no segment — so it never
        marks an utterance as present — and is never taken for a provider
        line; it renders through the one rendering path under its own label.
        The Edit control that creates such a line is Task 2.1's; here the
        line is placed directly in the manual-additions map."""
        from scribe_desktop.note import (
            ConfirmationDecision,
            NoteAssertion,
            NoteSpan,
            text_digest,
        )

        screen, _record = self._screen()
        before = screen._segments_in_note()
        assert before  # the provider quoted something
        provider_line = screen._draft.note_sections[0].note_assertions[0].assertion_id
        text = "Cervical HVLA performed"
        typed = NoteAssertion(
            assertion_id="typed-1",
            section_key="treatment_performed",
            note_span=NoteSpan(span_text=text, provenance="clinician"),
            shown_text_digest=text_digest(text),
            config_digest=screen._draft.config_digest,
            confirmation=ConfirmationDecision(
                proposal_id="typed-1",
                note_confirmation="confirmed",
                decided_at=datetime.now(UTC),
            ),
        )
        screen._manual["typed-1"] = typed
        screen._refinalise()
        assert screen._segments_in_note() == before
        assert not screen._provider_line_exists("typed-1")
        assert screen._provider_line_exists(provider_line)
        body = screen.note_body.toPlainText()
        assert f"  - {text}  [{models.provenance_label('clinician')}]" in body
        # The typed line is not a movable/removable transcript row.
        assert "typed-1" not in {line.assertion_id for line in screen.editable_lines()}
        screen.deleteLater()

    def test_consent_manual_reminder_is_always_rendered(self, qapp: Any) -> None:
        """Task 7.7 / round 45 MED-001 — the consent Critical Constraint's
        third clause: "the note view renders it as a manual reminder only".

        The reminder states what the app NEVER does, so it must survive
        `clear()` and be readable on an empty tab — it cannot be conditional
        on a loaded note, and it must never become an acknowledgeable
        warning (that would make it suppressible).
        """
        from scribe_desktop.ui.note import NoteScreen

        text = models.CONSENT_MANUAL_REMINDER
        assert "Informed Consent" in text
        # Round 47 PR-MED-001 semantic pin. The copy must name the ATTESTATION
        # CHECKBOX (what is structurally unreachable is an
        # `attestation_checkbox` target, not all consent-related note text —
        # `DEFAULT_SECTION_CUES["consent"]` legitimately routes consent speech
        # into the rendered `consent` section), and it must carry the FULL
        # predicate the checkbox asserts. Reducing it to consent-alone invites
        # the clinician to attest more than the reminder asked them to verify.
        assert "attestation" in text.lower()
        lowered = text.lower()
        for clause in ("working diagnosis", "benefits", "risks", "consent was gained"):
            assert clause in lowered, clause

        empty = NoteScreen()  # no note ever loaded
        assert empty.consent_reminder_label.text() == text

        screen, _ = self._screen()
        assert screen.consent_reminder_label.text() == text
        screen.clear()
        assert screen.consent_reminder_label.text() == text

        # A standing statement, never a warning: no code, no acknowledgement.
        assert "consent" not in NOTE_WARNING_SEVERITY
        assert not any(
            "informed consent" in copy.clear_hint.lower()
            for copy in models.WARNING_COPY.values()
        )

    def test_sections_render_in_canonical_order(self, qapp: Any) -> None:
        screen, _record = self._screen()
        note = screen.current_note()
        assert note is not None
        keys = [section.section_key for section in note.note_sections]
        indexed = [CANONICAL_SECTION_KEYS.index(key) for key in keys]
        assert indexed == sorted(indexed)  # canonical order
        screen.deleteLater()

    def test_provenance_visible_after_confirming(self, qapp: Any) -> None:
        screen, _record = self._screen()
        self._confirm_all(screen)
        body = screen.note_body.toPlainText()
        assert "from transcript" in body
        assert "autofill (clinician-authored)" in body
        assert "prefill (clinician-authored)" in body
        screen.deleteLater()

    def test_proposals_show_exact_text_and_confirm_inserts(self, qapp: Any) -> None:
        screen, _record = self._screen()
        autofill = next(
            p for p in screen._draft.note_proposals if p.provenance == "autofill"
        )
        assert autofill.note_excerpt not in screen.note_body.toPlainText()
        screen.confirm_proposal(autofill.proposal_id)
        assert autofill.note_excerpt in screen.note_body.toPlainText()
        screen.deleteLater()

    def test_unconfirmed_proposals_block_saving(self, qapp: Any) -> None:
        screen, _record = self._screen()
        # Pending proposals -> unconfirmed_proposal blocking error -> Save off.
        assert not screen.save_button.isEnabled()
        state = screen.current_review_state()
        assert state.unconfirmed_proposals > 0
        assert state.blocking_errors > 0
        screen.deleteLater()

    def test_confirming_all_then_acknowledge_enables_save(self, qapp: Any) -> None:
        screen, _record = self._screen()
        self._confirm_all(screen)
        state = screen.current_review_state()
        assert state.unconfirmed_proposals == 0
        assert state.blocking_errors == 0
        # Confirmed clinician-authored assertions draw the unsuppressible
        # clinician_asserted review warnings.
        assert state.unacknowledged_reviews > 0
        # Round 36 PR-MED-002: Save requires acknowledgement (plan Flow 1), so
        # it stays DISABLED until every review warning is acknowledged.
        assert not screen.save_button.isEnabled()
        screen._acknowledge_all()
        assert screen.save_button.isEnabled()
        screen.deleteLater()

    def test_decline_keeps_proposal_out_of_note(self, qapp: Any) -> None:
        screen, _record = self._screen()
        autofill = next(
            p for p in screen._draft.note_proposals if p.provenance == "autofill"
        )
        screen.decline_proposal(autofill.proposal_id)
        assert autofill.note_excerpt not in screen.note_body.toPlainText()
        screen.deleteLater()

    def test_retract_confirmed_assertion_refinalises(self, qapp: Any) -> None:
        screen, _record = self._screen()
        autofill = next(
            p for p in screen._draft.note_proposals if p.provenance == "autofill"
        )
        screen.confirm_proposal(autofill.proposal_id)
        assert autofill.note_excerpt in screen.note_body.toPlainText()
        screen.retract_proposal(autofill.proposal_id)
        assert autofill.note_excerpt not in screen.note_body.toPlainText()
        screen.deleteLater()

    def test_acknowledge_all_clears_unacknowledged(self, qapp: Any) -> None:
        screen, _record = self._screen()
        self._confirm_all(screen)
        assert screen.current_review_state().unacknowledged_reviews > 0
        screen._acknowledge_all()
        assert screen.current_review_state().unacknowledged_reviews == 0
        screen.deleteLater()

    def test_save_calls_callback_when_ratified(self, qapp: Any) -> None:
        screen, record = self._screen()
        self._confirm_all(screen)
        screen._acknowledge_all()  # Save now requires acknowledgement (Flow 1)
        screen.save()
        assert len(record["saved"]) == 1
        assert isinstance(record["saved"][0], GeneratedNote)
        assert not screen.save_button.isEnabled()  # already saved
        screen.deleteLater()

    def test_save_requires_acknowledgement(self, qapp: Any) -> None:
        """Round 36 PR-MED-002: a note cannot be saved (finalised) while a
        review warning is unacknowledged — the plan's Flow 1 precondition, so
        a committed note.enc is always Complete-ready."""
        screen, record = self._screen()
        self._confirm_all(screen)
        assert screen.current_review_state().unacknowledged_reviews > 0
        assert not screen.save_button.isEnabled()
        screen.save()  # click-time guard also refuses
        assert record["saved"] == []
        screen.deleteLater()

    def test_delete_note_and_complete_calls_abandon(self, qapp: Any) -> None:
        screen, record = self._screen()
        assert screen.abandon_button.isEnabled()
        screen.abandon()
        assert record["abandoned"] == [True]
        assert screen.current_note() is None  # cleared
        screen.deleteLater()

    def test_a_complete_refused_by_a_draft_write_names_the_write(self, qapp: Any) -> None:
        """Draft-write plan D9 (round 14): the controller refuses the exit
        while a draft write holds the session; the tab shows the write-in-
        flight line, never the error's own text, and keeps the review."""
        from scribe_desktop.session import WriteInFlightError
        from scribe_desktop.ui.note import NoteScreen

        screen = NoteScreen()

        def refused() -> None:
            raise WriteInFlightError("complete")

        screen.begin_review(
            _note_result(),
            on_save=lambda note: None,
            on_abandon=refused,
            template_profile_id="clinic-a",
        )
        screen.abandon()
        assert screen.message_label.text() == (
            "Complete without a note failed: " + models.write_line("write_in_flight")
        )
        assert screen.current_note() is not None  # nothing cleared
        screen.deleteLater()

    def test_cancel_review_calls_callback_and_clears(self, qapp: Any) -> None:
        """Round 35 PR-MED-003: the non-destructive escape invokes on_cancel
        and clears the Note-tab plaintext."""
        screen, record = self._screen()
        assert screen.cancel_button.isEnabled()  # draft under review, not saved
        screen.cancel_review()
        assert record["cancelled"] == [True]
        assert record["abandoned"] == []  # NOT the destructive path
        assert screen.current_note() is None  # cleared
        screen.deleteLater()

    def test_cancel_disabled_after_save(self, qapp: Any) -> None:
        screen, _record = self._screen()
        self._confirm_all(screen)
        screen._acknowledge_all()  # Save requires acknowledgement (Flow 1)
        screen.save()
        assert not screen.cancel_button.isEnabled()  # cancel is a pre-commit escape
        screen.deleteLater()

    def test_copy_disabled_when_gate_not_passed(self, qapp: Any) -> None:
        from PySide6.QtCore import Qt

        screen, _record = self._screen(copy_enabled=False)
        assert not screen.copy_button.isEnabled()
        assert (
            screen.note_body.textInteractionFlags() == Qt.TextInteractionFlag.NoTextInteraction
        )
        screen.deleteLater()

    def test_copy_enabled_only_for_a_ratified_note(self, qapp: Any) -> None:
        """Round 35 PR-MED-002: the recorded copy flag is necessary but NOT
        sufficient — copy shares Complete's ratification bar. An
        unresolved-error / pending / unsaved note is never copyable, even with
        the flag on."""
        from PySide6.QtCore import Qt

        screen, _record = self._screen(copy_enabled=True)
        # Flag on, but proposals pending -> copy stays disabled + display-only.
        assert not screen.copy_button.isEnabled()
        assert (
            screen.note_body.textInteractionFlags() == Qt.TextInteractionFlag.NoTextInteraction
        )
        # Ratify the note: confirm all -> acknowledge all -> save.
        self._confirm_all(screen)
        assert not screen.copy_button.isEnabled()  # unacknowledged reviews still block
        screen._acknowledge_all()
        assert not screen.copy_button.isEnabled()  # not yet saved
        screen.save()
        assert screen.copy_button.isEnabled()  # fully ratified
        flags = screen.note_body.textInteractionFlags()
        assert flags & Qt.TextInteractionFlag.TextSelectableByMouse
        screen.deleteLater()

    def test_default_copy_binding_ships_enabled(self, qapp: Any) -> None:
        """The recorded decision (COPY_TO_CLINIKO_ENABLED) is True since the
        practitioner's 2026-09-27 decision (safeguards plan D12, Task 1.4) —
        and the flag is still not sufficient: an UNRATIFIED note under the
        default binding shows the button but can neither be copied nor
        selected."""
        from PySide6.QtCore import Qt

        assert models.COPY_TO_CLINIKO_ENABLED is True
        from scribe_desktop.ui.note import NoteScreen

        screen = NoteScreen()
        screen.begin_review(
            _note_result(),
            on_save=lambda note: None,
            on_abandon=lambda: None,
        )
        assert not screen.copy_button.isHidden()
        assert not screen.copy_button.isEnabled()
        assert (
            screen.note_body.textInteractionFlags() == Qt.TextInteractionFlag.NoTextInteraction
        )
        screen.deleteLater()

    def test_default_copy_binding_equals_the_recorded_flag(self, qapp: Any) -> None:
        """Task 9.1a, decision-agnostic: whatever copy decision is recorded
        (the practitioner's, D12 since 2026-09-27), the Note tab's default
        binding IS the recorded flag - the value bound into
        ``begin_review``'s ``copy_enabled`` default at import is the module
        constant itself, so the shipped-state pin above and the window wiring
        tests can never disagree with the flag. (A monkeypatch of the constant
        does not move this default, which is exactly why the window tests
        drive ``MainWindow._on_draft_ready``, the call-time read.)"""
        import inspect

        from scribe_desktop.ui.note import NoteScreen

        default = inspect.signature(NoteScreen.begin_review).parameters["copy_enabled"].default
        assert default is models.COPY_TO_CLINIKO_ENABLED

    def test_cleared_on_close(self, qapp: Any) -> None:
        screen, _record = self._screen()
        assert screen.note_body.toPlainText() != ""
        screen.clear()
        assert screen.note_body.toPlainText() == ""
        assert screen.transcript_view.toPlainText() == ""
        assert screen.current_note() is None
        screen.deleteLater()

    def test_transcript_visible_beside_note(self, qapp: Any) -> None:
        """Task 7.6: the full uncertainty-marked transcript is beside the note
        and is display-only."""
        from PySide6.QtCore import Qt

        screen, _record = self._screen()
        text = screen.transcript_view.toPlainText()
        assert "My left knee is sore" in text
        assert (
            screen.transcript_view.textInteractionFlags()
            == Qt.TextInteractionFlag.NoTextInteraction
        )
        screen.deleteLater()

    def test_low_confidence_word_reachable_though_omitted(self, qapp: Any) -> None:
        """Task 7.6 Done-when: a low-`probability` word cue routing omitted is
        still REACHABLE in the transcript panel at review time."""
        result, marked = _low_confidence_result()
        screen, _record = self._screen(result=result)
        note = screen.current_note()
        assert note is not None
        # The word is not in the note (patient utterance, no cue)...
        assert marked not in screen.note_body.toPlainText()
        # ...but it is reachable in the transcript panel, marked uncertain.
        assert f"[{marked}?]" in screen.transcript_view.toPlainText()
        screen.deleteLater()

    def test_clinician_owned_sections_empty_without_confirmed_role(self, qapp: Any) -> None:
        """Task 7.5 Done-when: a note composed without a confirmed role leaves
        clinician-owned sections empty — the diagnosis utterance never lands."""
        screen, _record = self._screen(result=_note_result(clinician=None))
        note = screen.current_note()
        assert note is not None
        present = {section.section_key for section in note.note_sections}
        assert not (present & CLINICIAN_OWNED_SECTIONS)
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Review edits and consented phrase learning on the Note tab
# (practitioner-profile plan Phase 5, D14 + D9 as amended — Tasks 5.1 / 5.1b /
# 5.2). The fixture transcript extends `_NOTE_TURNS` with three lines the
# shipped cues do NOT route (so the chooser has something to offer) and one
# the `management_plan` cue does route and that carries a number.
# ---------------------------------------------------------------------------

_EDIT_TURNS: tuple[tuple[str, str], ...] = (
    *_NOTE_TURNS,
    ("I walked to the shop this morning", SPEAKER_1),  # 4: unrouted patient line
    ("The knee felt steady on the stairs", SPEAKER_2),  # 5: unrouted, learnable
    ("The plan is to review you in two weeks", SPEAKER_2),  # 6: routed, carries a number
)
_QUESTION_TURNS: tuple[tuple[str, str], ...] = (
    *_EDIT_TURNS,
    ("Do you feel pain here?", SPEAKER_2),  # 7: the clinician's QUESTION
)
_REFUSED_TURNS: tuple[tuple[str, str], ...] = (
    *_NOTE_TURNS,
    ("The dose is 500 mg tonight", SPEAKER_2),  # 4: a number in the phrase
    ("The patient Margaret rested", SPEAKER_2),  # 5: a name in the phrase
)
_LEARNABLE_INDEX = 5  # `_EDIT_TURNS`' "The knee felt steady on the stairs"
_LEARNABLE_PHRASE = "the knee felt steady"
_PLAN_INDEX = 6  # `_EDIT_TURNS`' routed clinician line carrying "two"
_DIAGNOSIS_INDEX = 2  # `_NOTE_TURNS`' routed clinician line
_DIAGNOSIS_PHRASE = "the diagnosis is a"


def _edit_config(section_cues: dict[str, tuple[str, ...]] | None = None) -> NoteConfig:
    """`_note_config` plus cues. The LEARNER reads the config's cues (the
    fourth clinician config file), which the note fixture leaves empty."""
    base = _note_config()
    return NoteConfig(
        template_profiles=base.template_profiles,
        autofill_rules=base.autofill_rules,
        prefill_templates=base.prefill_templates,
        section_cues=section_cues or {},
    )


def _edit_result(
    turns: tuple[tuple[str, str], ...] = _EDIT_TURNS,
    *,
    clinician: str | None = SPEAKER_2,
    config: NoteConfig | None = None,
    route_by_config: bool = False,
) -> models.NoteGenerationResult:
    """`_note_result`'s shape over `turns`. `route_by_config` builds the
    provider FROM the config's cues (Task 4.3's shipping wiring) instead of
    the module defaults the note fixture composes with."""
    document = _note_document(turns)
    resolved = config if config is not None else _note_config()
    provider = (
        ExtractiveNoteProvider(cues=resolved.normalised_cues())
        if route_by_config
        else ExtractiveNoteProvider()
    )
    draft = compose_draft(document, resolved, provider, clinician_speaker=clinician)
    return models.NoteGenerationResult(draft=draft, config=resolved, document=document)


def _learning_on() -> models.LearningStatus:
    return models.LearningStatus(True, None)


def _provider_lines(screen: Any) -> dict[str, Any]:
    """The draft's own (provider-routed) transcript assertions, by id."""
    return {
        assertion.assertion_id: assertion
        for section in screen._draft.note_sections
        for assertion in section.note_assertions
    }


def _note_assertion(screen: Any, assertion_id: str) -> Any:
    note = screen.current_note()
    assert note is not None
    for section in note.note_sections:
        for assertion in section.note_assertions:
            if assertion.assertion_id == assertion_id:
                return assertion
    return None


def _warning_codes(screen: Any) -> set[str]:
    note = screen.current_note()
    assert note is not None
    return {warning.note_warning_code for warning in note.note_warnings}


def _eligible(screen: Any) -> dict[int, Any]:
    return {choice.segment_index: choice for choice in screen.eligible_utterances()}


def _lines_by_id(screen: Any) -> dict[str, Any]:
    return {line.assertion_id: line for line in screen.editable_lines()}


def _routed_line(screen: Any, segment_index: int) -> Any:
    """The provider's line for `segment_index`, which the shipped cues must
    have routed for the fixture to mean what the test says."""
    line = next(
        (item for item in screen.editable_lines() if item.segment_index == segment_index),
        None,
    )
    assert line is not None, f"the shipped cues no longer route segment {segment_index}"
    return line


def _utterance_text(screen: Any, segment_index: int) -> str:
    segment = screen._document.transcript_segments[segment_index]
    return " ".join(word.word_text for word in segment.transcript_words)


class TestNoteWriteButton:
    """Draft-write Task 5.2 (D2, D5, D10): the Note tab's "Write draft to
    Cliniko" button — hidden without a binding, enabled only for a saved,
    linked, non-mock note whose write record allows it, re-checked at the
    click, and busy while the main window's write is in flight."""

    _SESSION = "session-w"

    def _screen(
        self,
        *,
        status: Any = None,
        linked: bool = True,
        bind: bool = True,
        result: models.NoteGenerationResult | None = None,
    ) -> tuple[Any, list[str], list[str]]:
        from scribe_desktop.draft_write import WriteRecordStatus
        from scribe_desktop.ui.note import NoteScreen

        reads: list[str] = []
        current = [status if status is not None else WriteRecordStatus("none")]

        def provider(session_id: str) -> WriteRecordStatus:
            reads.append(session_id)
            value = current[0]
            if isinstance(value, Exception):
                raise value
            return value

        emitted: list[str] = []
        screen = NoteScreen(write_status_provider=provider)
        screen.write_requested.connect(emitted.append)
        screen.begin_review(
            result if result is not None else _note_result(),
            copy_enabled=True,
            on_save=lambda note: None,
            on_abandon=lambda: None,
            template_profile_id="clinic-a",
            write_binding=models.WriteBinding(self._SESSION, linked) if bind else None,
        )
        screen._status = current  # the test's handle on the provider's answer
        return screen, emitted, reads

    def _save(self, screen: Any) -> None:
        for proposal in screen._draft.note_proposals:
            screen.confirm_proposal(proposal.proposal_id)
        screen._acknowledge_all()
        screen.save()

    def test_hidden_without_a_binding(self, qapp: Any) -> None:
        screen, emitted, reads = self._screen(bind=False)
        self._save(screen)
        assert screen.write_button.isHidden()
        assert not screen.write_button.isEnabled()
        assert screen.write_label.text() == ""
        screen._on_write_clicked()  # a click that still arrives (the click-time check)
        assert emitted == [] and reads == []
        screen.deleteLater()

    def test_not_saved_first_then_ready_once_saved(self, qapp: Any) -> None:
        screen, emitted, reads = self._screen()
        assert not screen.write_button.isHidden()
        assert screen.write_button.text() == models.write_line("ready")
        assert not screen.write_button.isEnabled()
        assert screen.write_label.text() == models.write_line("not_saved")
        assert screen.write_button.toolTip() == models.write_line("not_saved")
        assert reads == []  # no record read before the note is saved
        self._save(screen)
        assert screen.write_button.isEnabled()
        assert screen.write_label.text() == ""
        assert set(reads) == {self._SESSION}
        screen.write_button.click()
        assert emitted == [self._SESSION]
        screen.deleteLater()

    def test_an_unlinked_session_never_reads_the_record(self, qapp: Any) -> None:
        screen, emitted, reads = self._screen(linked=False)
        self._save(screen)
        assert not screen.write_button.isEnabled()
        assert screen.write_label.text() == models.write_line("unlinked")
        screen.write_label.setText("")
        screen._on_write_clicked()  # a click that still arrives repeats the reason
        assert screen.write_label.text() == models.write_line("unlinked")
        assert emitted == [] and reads == []
        screen.deleteLater()

    def test_a_mock_note_is_refused_before_any_record_read(self, qapp: Any) -> None:
        """D10: the tab's gate; ``draft_write.refuse_before_read`` is the
        second one (pinned in ``test_ui_encounter.py``)."""
        screen, emitted, reads = self._screen()
        self._save(screen)
        saved = screen._note
        screen._note = saved.model_copy(update={"provider_name": "mock-provider"})
        screen._update_controls()
        assert not screen.write_button.isEnabled()
        assert screen.write_label.text() == models.write_line("mock_note")
        reads.clear()
        screen.write_label.setText("")
        screen._on_write_clicked()
        assert screen.write_label.text() == models.write_line("mock_note")
        assert emitted == [] and reads == []
        screen.deleteLater()

    @pytest.mark.parametrize(
        ("outcome", "matches", "key"),
        [
            ("written", True, "written_seen"),
            ("written", False, "write_uncertain"),
            ("unreadable", False, "record_unreadable"),
        ],
    )
    def test_a_write_record_that_closes_the_button(
        self, qapp: Any, outcome: str, matches: bool, key: str
    ) -> None:
        from scribe_desktop.draft_write import WriteRecordStatus

        screen, emitted, _reads = self._screen(
            status=WriteRecordStatus(outcome, note_matches=matches)  # type: ignore[arg-type]
        )
        self._save(screen)
        assert not screen.write_button.isEnabled()
        assert screen.write_label.text() == models.write_line(key)
        screen.write_label.setText("")
        screen._on_write_clicked()
        assert screen.write_label.text() == models.write_line(key)
        assert emitted == []
        screen.deleteLater()

    def test_a_record_read_that_fails_closes_the_button(self, qapp: Any) -> None:
        screen, emitted, _reads = self._screen(status=OSError("disk"))
        self._save(screen)
        assert not screen.write_button.isEnabled()
        assert screen.write_label.text() == models.write_line("record_unreadable")
        screen._on_write_clicked()
        assert screen.write_label.text() == models.write_line("record_unreadable")
        assert emitted == []
        screen.deleteLater()

    def test_the_status_is_read_once_per_binding_and_afresh_at_the_click(
        self, qapp: Any
    ) -> None:
        """Round 33 LOW-011: a control refresh never re-reads (decrypts) the
        record; a write starting or ending and every click do."""
        from scribe_desktop.draft_write import WriteRecordStatus

        screen, emitted, reads = self._screen()
        self._save(screen)
        assert len(reads) == 1  # the first binding after Save
        screen._update_controls()
        screen.show_write_line(models.write_line("checking"))
        assert len(reads) == 1
        screen.set_write_in_flight(True)
        screen.set_write_in_flight(False)
        assert len(reads) == 3  # one read at each end of a write
        screen._on_write_clicked()
        assert len(reads) == 4 and emitted == [self._SESSION]
        # `clear()` and a new binding drop the cache: a changed record shows.
        note = screen._note
        screen.clear()
        screen._status[0] = WriteRecordStatus("written", note_matches=True)
        screen.show_saved_note(
            note,
            _note_document(),
            info="",
            copy_enabled=True,
            write_binding=models.WriteBinding(self._SESSION, True),
        )
        assert screen.write_label.text() == models.write_line("written_seen")
        assert not screen.write_button.isEnabled()
        screen.deleteLater()

    def test_a_rendering_in_flight_names_itself_on_the_write_line(self, qapp: Any) -> None:
        """Round 33 LOW-005: Write waits on a prose rendering and says so
        on its own line — never Save's message."""
        screen, emitted, _reads = self._screen()
        self._save(screen)
        screen._style_job = object()
        screen._update_controls()
        rendering = models.rendering_in_flight_line(screen._note_style)
        assert not screen.write_button.isEnabled()
        assert screen.write_label.text() == rendering
        assert screen.write_button.toolTip() == rendering
        screen.write_label.setText("")
        screen._on_write_clicked()
        assert screen.write_label.text() == rendering and emitted == []
        screen._style_job = None
        screen._update_controls()
        assert screen.write_button.isEnabled()
        screen.deleteLater()

    @pytest.mark.parametrize("outcome", ["attempting", "unknown"])
    def test_an_open_attempt_stays_writable_and_says_so(self, qapp: Any, outcome: str) -> None:
        """D5: the next click reconciles an open attempt before any send."""
        from scribe_desktop.draft_write import WriteRecordStatus

        screen, emitted, _reads = self._screen(
            status=WriteRecordStatus(outcome, note_matches=True)  # type: ignore[arg-type]
        )
        self._save(screen)
        assert screen.write_button.isEnabled()
        assert screen.write_label.text() == models.write_line("unknown")
        screen.write_button.click()
        assert emitted == [self._SESSION]
        screen.deleteLater()

    def test_the_click_rechecks_the_record(self, qapp: Any) -> None:
        """A record that changed since the button was bound refuses at the
        click (fail closed) and says why."""
        from scribe_desktop.draft_write import WriteRecordStatus

        screen, emitted, _reads = self._screen()
        self._save(screen)
        assert screen.write_button.isEnabled()
        screen._status[0] = WriteRecordStatus("written", note_matches=True)
        screen._on_write_clicked()
        assert emitted == []
        assert screen.write_label.text() == models.write_line("written_seen")
        # Round 34 LOW-002: the button follows the reason it just showed.
        assert not screen.write_button.isEnabled()
        assert screen.write_button.toolTip() == models.write_line("written_seen")
        screen.deleteLater()

    def test_a_failed_read_is_never_cached(self, qapp: Any) -> None:
        """Round 34 LOW-001: a read that failed (or read ``unreadable``)
        closes Write, so no click could re-read it — the next refresh does,
        and a record readable again opens Write."""
        from scribe_desktop.draft_write import WriteRecordStatus

        screen, _emitted, reads = self._screen(status=OSError("sharing violation"))
        self._save(screen)
        assert screen.write_label.text() == models.write_line("record_unreadable")
        screen._status[0] = WriteRecordStatus("unreadable")
        count = len(reads)
        screen._update_controls()
        assert len(reads) == count + 1
        assert not screen.write_button.isEnabled()
        screen._status[0] = WriteRecordStatus("none")
        screen._update_controls()
        assert screen.write_button.isEnabled()
        assert screen.write_label.text() == ""
        screen.deleteLater()

    def test_in_flight_disables_write_and_holds_the_tab_busy(self, qapp: Any) -> None:
        screen, emitted, _reads = self._screen()
        self._save(screen)
        assert not screen.is_busy
        screen.set_write_in_flight(True)
        screen.show_write_line(models.write_line("checking"))
        assert screen.is_busy
        assert not screen.write_button.isEnabled()
        assert screen.write_label.text() == models.write_line("checking")
        screen._on_write_clicked()
        assert emitted == []
        assert screen.write_label.text() == models.write_line("write_in_flight")
        screen.show_write_line(models.write_line("written_seen"))
        screen.set_write_in_flight(False)
        assert not screen.is_busy
        assert screen.write_label.text() == models.write_line("written_seen")
        screen.deleteLater()

    def test_the_outcome_line_survives_a_ready_rebind(self, qapp: Any) -> None:
        """A refusal that leaves the button ready (e.g. ``check_failed``)
        stays on screen until the next write replaces it."""
        screen, _emitted, _reads = self._screen()
        self._save(screen)
        line = models.write_line("rate_limited", seconds=30)
        screen.show_write_line(line)
        assert screen.write_button.isEnabled()
        assert screen.write_label.text() == line
        screen.deleteLater()

    def test_clear_forgets_the_binding(self, qapp: Any) -> None:
        screen, emitted, _reads = self._screen()
        self._save(screen)
        screen.set_write_in_flight(True)
        screen.clear()
        assert screen.write_binding is None
        assert not screen.is_busy
        assert screen.write_button.isHidden()
        screen._on_write_clicked()
        assert emitted == []
        screen.deleteLater()

    def test_a_reopened_saved_note_offers_write(self, qapp: Any) -> None:
        """Task 5.4's adopted Unreviewed recording: ``show_saved_note`` takes
        the binding too."""
        from scribe_desktop.ui.note import NoteScreen

        source, _emitted, _reads = self._screen(bind=False)
        self._save(source)
        note = source._note
        source.deleteLater()
        emitted: list[str] = []
        screen = NoteScreen(write_status_provider=lambda _sid: _status_none())
        screen.write_requested.connect(emitted.append)
        screen.show_saved_note(
            note,
            _note_document(),
            info="",
            copy_enabled=True,
            write_binding=models.WriteBinding(self._SESSION, True),
        )
        assert screen.write_button.isEnabled()
        screen.write_button.click()
        assert emitted == [self._SESSION]
        screen.deleteLater()

    def test_a_save_refused_by_a_pending_write_shows_the_write_line(self, qapp: Any) -> None:
        """D5 (round 26): the second Save a write attempt blocks reads as the
        ``write_pending`` line, never the exception's class name."""
        from scribe_desktop.ui.note import NoteScreen
        from scribe_desktop.ui.transcript import WritePendingError

        screen = NoteScreen()

        def refused(_note: Any) -> None:
            raise WritePendingError(models.write_line("write_pending"))

        screen.begin_review(
            _note_result(),
            copy_enabled=True,
            on_save=refused,
            on_abandon=lambda: None,
            template_profile_id="clinic-a",
        )
        for proposal in screen._draft.note_proposals:
            screen.confirm_proposal(proposal.proposal_id)
        screen._acknowledge_all()
        screen.save()
        assert models.write_line("write_pending") in screen.message_label.text()
        assert "WritePendingError" not in screen.message_label.text()
        screen.deleteLater()


def _status_none() -> Any:
    from scribe_desktop.draft_write import WriteRecordStatus

    return WriteRecordStatus("none")


class TestNoteScreenEdits:
    """D14's add / remove / move / undo and D9's consented phrase learning."""

    def _screen(
        self,
        *,
        config_root: Path,
        result: models.NoteGenerationResult | None = None,
        learning_status_provider: Callable[[], models.LearningStatus] | None = None,
    ) -> tuple[Any, dict[str, list[Any]]]:
        from scribe_desktop.ui.note import NoteScreen

        record: dict[str, list[Any]] = {
            "saved": [],
            "abandoned": [],
            "cancelled": [],
            "states": [],
        }
        screen = NoteScreen(
            config_root=config_root, learning_status_provider=learning_status_provider
        )
        screen.begin_review(
            result if result is not None else _edit_result(),
            on_save=lambda note: record["saved"].append(note),
            on_abandon=lambda: record["abandoned"].append(True),
            on_cancel=lambda: record["cancelled"].append(True),
            on_state_changed=lambda state: record["states"].append(state),
            template_profile_id="clinic-a",
        )
        return screen, record

    def _ratify(self, screen: Any) -> None:
        for proposal in screen._draft.note_proposals:
            screen.confirm_proposal(proposal.proposal_id)
        screen._acknowledge_all()

    # --- the chooser and the add path (Task 5.1) --------------------------

    def test_the_chooser_offers_exactly_the_lines_not_already_in_the_note(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from PySide6.QtCore import Qt

        screen, _record = self._screen(config_root=tmp_path / "config")
        # The transcript panel stays display-only beside the edit group.
        assert (
            screen.transcript_view.textInteractionFlags()
            == Qt.TextInteractionFlag.NoTextInteraction
        )
        assert screen.edit_group.isVisibleTo(screen)
        document = screen._document
        in_note = {
            assertion.note_span.source_coords.segment_index
            for assertion in _provider_lines(screen).values()
        }
        assert in_note, "the fixture must have routed something to exclude"
        expected = [
            index
            for index in range(len(document.transcript_segments))
            if index not in in_note
        ]
        offered = [
            screen.utterance_combo.itemData(position)
            for position in range(screen.utterance_combo.count())
        ]
        assert offered == expected
        for position, index in enumerate(expected):
            segment = document.transcript_segments[index]
            label = screen.utterance_combo.itemText(position)
            assert label.startswith(f"{index + 1}. {segment.speaker}: ")
        # The section chooser follows the selected line's ownership rule.
        first = _eligible(screen)[expected[0]]
        sections = [
            screen.section_combo.itemData(position)
            for position in range(screen.section_combo.count())
        ]
        assert tuple(sections) == first.allowed_sections
        screen.deleteLater()

    def test_add_quotes_the_whole_utterance_and_clears_acknowledgements(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, _record = self._screen(config_root=tmp_path / "config")
        document = screen._document
        patient = next(
            choice
            for choice in screen.eligible_utterances()
            if document.transcript_segments[choice.segment_index].speaker == SPEAKER_1
        )
        key = patient.allowed_sections[0]
        self._ratify(screen)
        assert models.summarise_warnings(screen.current_note().note_warnings).review
        assert screen.save_button.isEnabled()

        assert screen.add_line(patient.segment_index, key) is True
        assert _utterance_text(screen, patient.segment_index) in screen.note_body.toPlainText()
        manual_id = manual_assertion_id(patient.segment_index)
        added = _note_assertion(screen, manual_id)
        assert added is not None
        assert added.section_key == key
        assert added.provenance == "transcript"
        words = document.transcript_segments[patient.segment_index].transcript_words
        assert added.note_span.source_coords == (patient.segment_index, 0, len(words) - 1)
        # Check 1 reconstructs it byte-identically.
        assert not _warning_codes(screen) & {
            "reconstruction_mismatch",
            "source_coords_invalid",
        }
        assert patient.segment_index not in _eligible(screen)
        assert _lines_by_id(screen)[manual_id].state == "added"
        # THE content-change path: acknowledgements cleared, Save closed again.
        assert screen.current_review_state().unacknowledged_reviews > 0
        assert not screen.save_button.isEnabled()
        screen.deleteLater()

    def test_a_line_already_in_the_note_is_refused_unchanged(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, _record = self._screen(config_root=tmp_path / "config")
        choice = screen.eligible_utterances()[0]
        key = choice.allowed_sections[0]
        assert screen.add_line(choice.segment_index, key) is True
        body = screen.note_body.toPlainText()
        lines = screen.editable_lines()
        assert screen.add_line(choice.segment_index, key) is False
        assert "already in the note" in screen.edit_status_label.text()
        assert screen.note_body.toPlainText() == body
        assert screen.editable_lines() == lines
        screen.deleteLater()

    def test_clinician_owned_sections_take_only_the_clinicians_statements(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        config_root = tmp_path / "config"
        screen, _record = self._screen(config_root=config_root)
        document = screen._document
        owned = "assessment"
        assert owned in CLINICIAN_OWNED_SECTIONS
        patient = next(
            choice
            for choice in screen.eligible_utterances()
            if document.transcript_segments[choice.segment_index].speaker == SPEAKER_1
        )
        assert screen.add_line(patient.segment_index, owned) is False
        assert models.section_title(owned) in screen.edit_status_label.text()
        assert _note_assertion(screen, manual_assertion_id(patient.segment_index)) is None

        # The confirmed clinician's own STATEMENT is admitted there...
        statement = _LEARNABLE_INDEX
        assert statement in _eligible(screen)
        assert screen.add_line(statement, owned) is True
        assert _note_assertion(screen, manual_assertion_id(statement)).section_key == owned
        assert "role_unconfirmed" not in _warning_codes(screen)
        screen.deleteLater()

        # ...their QUESTION is not.
        asking, _r = self._screen(
            config_root=config_root, result=_edit_result(_QUESTION_TURNS)
        )
        question = len(_QUESTION_TURNS) - 1
        assert question in _eligible(asking)
        assert owned not in _eligible(asking)[question].allowed_sections
        assert asking.add_line(question, owned) is False
        assert models.section_title(owned) in asking.edit_status_label.text()
        asking.deleteLater()

    def test_an_unknown_or_textless_line_can_never_be_added(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        config_root = tmp_path / "config"
        screen, _record = self._screen(config_root=config_root)
        assert screen.add_line(99, "presenting_complaint") is False
        assert "not in the transcript" in screen.edit_status_label.text()
        screen.deleteLater()

        silent_turns = (*_EDIT_TURNS, ("", SPEAKER_1))
        silent, _r = self._screen(
            config_root=config_root, result=_edit_result(silent_turns)
        )
        empty_index = len(silent_turns) - 1
        assert silent._document.transcript_segments[empty_index].transcript_words == ()
        assert empty_index not in _eligible(silent)
        assert empty_index not in [
            silent.utterance_combo.itemData(position)
            for position in range(silent.utterance_combo.count())
        ]
        silent.deleteLater()

    # --- remove / undo / move (Task 5.1b) ---------------------------------

    def test_removing_a_line_raises_an_acknowledgeable_omission_never_a_block(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, _record = self._screen(config_root=tmp_path / "config")
        line = _routed_line(screen, _PLAN_INDEX)
        assert line.state == "routed"
        segment = screen._document.transcript_segments[_PLAN_INDEX]
        assert any(is_number_token(word.word_text) for word in segment.transcript_words)
        self._ratify(screen)
        assert screen.save_button.isEnabled()
        assert "high_risk_omission" not in _warning_codes(screen)

        assert screen.remove_line(line.assertion_id) is True
        assert _utterance_text(screen, _PLAN_INDEX) not in screen.note_body.toPlainText()
        assert _lines_by_id(screen)[line.assertion_id].state == "removed"
        assert "high_risk_omission" in _warning_codes(screen)
        assert screen.current_review_state().blocking_errors == 0
        assert not screen.save_button.isEnabled()
        screen._acknowledge_all()
        assert screen.current_review_state().unacknowledged_reviews == 0
        assert screen.save_button.isEnabled()
        screen.deleteLater()

    def test_undo_restores_a_removed_line(self, qapp: Any, tmp_path: Path) -> None:
        screen, _record = self._screen(config_root=tmp_path / "config")
        line = _routed_line(screen, _DIAGNOSIS_INDEX)
        assert screen.remove_line(line.assertion_id) is True
        assert _utterance_text(screen, _DIAGNOSIS_INDEX) not in screen.note_body.toPlainText()
        assert screen.undo_line(line.assertion_id) is True
        assert _utterance_text(screen, _DIAGNOSIS_INDEX) in screen.note_body.toPlainText()
        restored = _lines_by_id(screen)[line.assertion_id]
        assert restored.state == "routed"
        assert restored.moved_to is None
        screen.deleteLater()

    def test_move_subtracts_the_provider_line_and_re_adds_the_utterance(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, _record = self._screen(config_root=tmp_path / "config")
        document = screen._document
        line = next(
            item
            for item in screen.editable_lines()
            if item.state == "routed"
            and document.transcript_segments[item.segment_index].speaker == SPEAKER_1
        )
        target = line.allowed_sections[0]
        manual_id = manual_assertion_id(line.segment_index)
        assert screen.move_line(line.assertion_id, target) is True
        assert _note_assertion(screen, line.assertion_id) is None
        moved = _note_assertion(screen, manual_id)
        assert moved is not None and moved.section_key == target
        rows = [
            item for item in screen.editable_lines() if item.segment_index == line.segment_index
        ]
        assert len(rows) == 1  # the re-added leg is not a second row
        assert rows[0].assertion_id == line.assertion_id
        assert rows[0].state == "moved"
        assert rows[0].moved_to == target
        assert line.segment_index not in _eligible(screen)

        assert screen.undo_line(line.assertion_id) is True
        assert _lines_by_id(screen)[line.assertion_id].state == "routed"
        assert _note_assertion(screen, line.assertion_id) is not None
        assert _note_assertion(screen, manual_id) is None
        assert screen._manual == {}

        # A section the ownership rule refuses changes nothing (patient line).
        before = screen.editable_lines()
        assert screen.move_line(line.assertion_id, "assessment") is False
        assert screen.editable_lines() == before
        assert _note_assertion(screen, line.assertion_id) is not None
        screen.deleteLater()

    def test_moving_an_added_line_changes_its_section_in_place(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, _record = self._screen(config_root=tmp_path / "config")
        choice = screen.eligible_utterances()[0]
        first = choice.allowed_sections[0]
        second = next(key for key in choice.allowed_sections if key != first)
        assert screen.add_line(choice.segment_index, first) is True
        manual_id = manual_assertion_id(choice.segment_index)
        assert screen.move_line(manual_id, second) is True
        rows = [
            item
            for item in screen.editable_lines()
            if item.segment_index == choice.segment_index
        ]
        assert len(rows) == 1
        assert rows[0].assertion_id == manual_id
        assert rows[0].state == "added"
        assert rows[0].section_key == second
        assert _note_assertion(screen, manual_id).section_key == second
        assert list(screen._manual) == [manual_id]
        screen.deleteLater()

    def test_edits_are_frozen_after_save(self, qapp: Any, tmp_path: Path) -> None:
        screen, record = self._screen(config_root=tmp_path / "config")
        line = _routed_line(screen, _DIAGNOSIS_INDEX)
        choice = screen.eligible_utterances()[0]
        key = choice.allowed_sections[0]
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        for refused in (
            lambda: screen.add_line(choice.segment_index, key),
            lambda: screen.remove_line(line.assertion_id),
            lambda: screen.move_line(line.assertion_id, key),
            lambda: screen.undo_line(line.assertion_id),
        ):
            screen.edit_status_label.setText("")
            assert refused() is False
            assert "edits are closed" in screen.edit_status_label.text()
        assert not screen.utterance_combo.isEnabled()
        assert not screen.section_combo.isEnabled()
        assert not screen.add_line_button.isEnabled()
        screen.deleteLater()

    def test_clear_empties_the_edit_controls_and_the_queue(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, _record = self._screen(
            config_root=tmp_path / "config", learning_status_provider=_learning_on
        )
        assert screen.add_line(_LEARNABLE_INDEX, "presenting_complaint") is True
        assert screen.learning_queue()
        assert screen.utterance_combo.count() > 0
        screen.clear()
        assert screen.utterance_combo.count() == 0
        assert screen.section_combo.count() == 0
        assert screen.editable_lines() == ()
        assert screen.learning_queue() == ()
        assert screen.edit_status_label.text() == ""
        screen.deleteLater()

    # --- phrase learning (D9 as amended, Task 5.2) ------------------------

    def test_a_patient_line_is_never_a_learning_candidate(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, _record = self._screen(
            config_root=tmp_path / "config", learning_status_provider=_learning_on
        )
        document = screen._document
        patient = next(
            choice
            for choice in screen.eligible_utterances()
            if document.transcript_segments[choice.segment_index].speaker == SPEAKER_1
        )
        assert screen.add_line(patient.segment_index, patient.allowed_sections[0]) is True
        assert screen.learning_queue() == ()
        assert "Will learn" not in screen.edit_status_label.text()
        # ...and the skip is SAID, never silent (live smoke 2026-09-17).
        assert models.LEARNING_NOT_ATTRIBUTED_NOTE in screen.edit_status_label.text()
        screen.deleteLater()

    def test_a_clinician_line_queues_its_leading_phrase(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, _record = self._screen(
            config_root=tmp_path / "config", learning_status_provider=_learning_on
        )
        assert _LEARNABLE_INDEX in _eligible(screen), "the fixture line must stay unrouted"
        key = _eligible(screen)[_LEARNABLE_INDEX].allowed_sections[0]
        assert screen.add_line(_LEARNABLE_INDEX, key) is True
        assert screen.learning_queue() == ((key, _LEARNABLE_PHRASE),)
        assert f"Will learn '{_LEARNABLE_PHRASE}'" in screen.edit_status_label.text()
        assert models.section_title(key) in screen.edit_status_label.text()
        screen.deleteLater()

    def test_a_name_or_a_number_in_the_phrase_is_refused_by_the_filter(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        config_root = tmp_path / "config"
        for index, refusal in ((4, "number"), (5, "name")):
            screen, _record = self._screen(
                config_root=config_root,
                result=_edit_result(_REFUSED_TURNS),
                learning_status_provider=_learning_on,
            )
            assert index in _eligible(screen)
            key = _eligible(screen)[index].allowed_sections[0]
            assert screen.add_line(index, key) is True
            status = screen.edit_status_label.text()
            assert "Not learned" in status
            assert refusal in status
            assert screen.learning_queue() == ()
            screen.deleteLater()

    def test_the_learning_line_reports_why_learning_is_off(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        config_root = tmp_path / "config"
        stale, _record = self._screen(
            config_root=config_root,
            learning_status_provider=lambda: models.LearningStatus(
                False, models.LEARNING_STALE_CONSENT_HINT
            ),
        )
        assert stale.learning_label.text() == models.LEARNING_STALE_CONSENT_HINT
        key = _eligible(stale)[_LEARNABLE_INDEX].allowed_sections[0]
        assert stale.add_line(_LEARNABLE_INDEX, key) is True
        assert stale.learning_queue() == ()
        assert models.LEARNING_STALE_CONSENT_HINT in stale.edit_status_label.text()
        stale.deleteLater()

        on, _r = self._screen(config_root=config_root, learning_status_provider=_learning_on)
        assert on.learning_label.text() == models.LEARNING_ON_LINE
        on.deleteLater()

        # A screen built WITHOUT a provider never reads the profile store.
        silent, _s = self._screen(config_root=config_root)
        assert silent.learning_label.text() == models.LEARNING_NO_PROFILE_HINT
        assert silent.add_line(_LEARNABLE_INDEX, key) is True
        assert silent.learning_queue() == ()
        assert models.LEARNING_NO_PROFILE_HINT in silent.edit_status_label.text()
        silent.deleteLater()

    def test_an_earlier_sections_cue_is_noted_never_silently_replaced(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR-MED-011: the learner says when an earlier section's cue would
        still route lines like this one — it never deletes that cue."""
        config = _edit_config({"presenting_complaint": ("on the stairs",)})
        screen, _record = self._screen(
            config_root=tmp_path / "config",
            result=_edit_result(config=config, route_by_config=True),
            learning_status_provider=_learning_on,
        )
        line = _routed_line(screen, _LEARNABLE_INDEX)
        assert line.section_key == "presenting_complaint"  # the config cue routed it
        assert screen.move_line(line.assertion_id, "management_plan") is True
        status = screen.edit_status_label.text()
        assert f"Will learn '{_LEARNABLE_PHRASE}'" in status
        assert "still routes this line first" in status
        assert models.section_title("presenting_complaint") in status
        assert screen.learning_queue() == (("management_plan", _LEARNABLE_PHRASE),)
        screen.deleteLater()

    def test_phrases_are_written_only_on_save(self, qapp: Any, tmp_path: Path) -> None:
        config_root = tmp_path / "config"
        screen, record = self._screen(
            config_root=config_root, learning_status_provider=_learning_on
        )
        key = _eligible(screen)[_LEARNABLE_INDEX].allowed_sections[0]
        assert screen.add_line(_LEARNABLE_INDEX, key) is True
        assert not config_root.exists()  # nothing is written before Save
        refreshed: list[int] = []
        screen.learned_phrases_changed.connect(lambda: refreshed.append(1))

        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        assert (config_root / SECTION_CUES_FILENAME).exists()
        assert (config_root / LEARNED_SIDECAR_FILENAME).exists()
        cues = load_note_config(config_root).normalised_cues()
        assert tuple(_LEARNABLE_PHRASE.split()) in cues[key]
        learned = load_learned_phrases(config_root)
        assert learned.recent[0].phrase == _LEARNABLE_PHRASE
        assert learned.recent[0].section_key == key
        assert "Learned 1" in screen.edit_status_label.text()
        assert refreshed == [1]
        assert screen.learning_queue() == ()
        screen.deleteLater()

    def test_an_undone_or_abandoned_add_teaches_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        config_root = tmp_path / "config"
        screen, record = self._screen(
            config_root=config_root, learning_status_provider=_learning_on
        )
        key = _eligible(screen)[_LEARNABLE_INDEX].allowed_sections[0]
        assert screen.add_line(_LEARNABLE_INDEX, key) is True
        assert screen.undo_line(manual_assertion_id(_LEARNABLE_INDEX)) is True
        assert screen.learning_queue() == ()
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        assert not config_root.exists()
        screen.deleteLater()

        cancelled, _r = self._screen(
            config_root=config_root, learning_status_provider=_learning_on
        )
        assert cancelled.add_line(_LEARNABLE_INDEX, key) is True
        cancelled.cancel_review()
        assert cancelled.learning_queue() == ()
        assert not config_root.exists()
        cancelled.deleteLater()

        abandoned, _a = self._screen(
            config_root=config_root, learning_status_provider=_learning_on
        )
        assert abandoned.add_line(_LEARNABLE_INDEX, key) is True
        abandoned.abandon()
        assert abandoned.learning_queue() == ()
        assert not config_root.exists()
        abandoned.deleteLater()

    def test_the_learning_status_is_re_read_at_save(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        config_root = tmp_path / "config"
        enabled = {"on": True}

        def provider() -> models.LearningStatus:
            if enabled["on"]:
                return models.LearningStatus(True, None)
            return models.LearningStatus(False, models.LEARNING_OPTED_OUT_HINT)

        screen, record = self._screen(
            config_root=config_root, learning_status_provider=provider
        )
        key = _eligible(screen)[_LEARNABLE_INDEX].allowed_sections[0]
        assert screen.add_line(_LEARNABLE_INDEX, key) is True
        assert screen.learning_queue()
        enabled["on"] = False  # opted out mid-review
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        assert not config_root.exists()
        status = screen.edit_status_label.text()
        assert "Nothing learned" in status
        assert models.LEARNING_OPTED_OUT_HINT in status
        screen.deleteLater()

    def test_a_learning_write_failure_is_reported_and_the_note_stays_saved(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        config_root = tmp_path / "config"
        config_root.mkdir(parents=True)
        blob = b"{not json"
        (config_root / SECTION_CUES_FILENAME).write_bytes(blob)
        screen, record = self._screen(
            config_root=config_root, learning_status_provider=_learning_on
        )
        key = _eligible(screen)[_LEARNABLE_INDEX].allowed_sections[0]
        assert screen.add_line(_LEARNABLE_INDEX, key) is True
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1  # the note is committed
        assert not screen.save_button.isEnabled()  # saved
        status = screen.edit_status_label.text()
        assert "were not learned" in status
        assert "NoteConfigInvalidError" in status
        assert (config_root / SECTION_CUES_FILENAME).read_bytes() == blob
        assert not (config_root / LEARNED_SIDECAR_FILENAME).exists()
        screen.deleteLater()

    def test_a_removal_teaches_nothing_but_a_moves_add_leg_queues(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        config_root = tmp_path / "config"
        screen, record = self._screen(
            config_root=config_root, learning_status_provider=_learning_on
        )
        line = _routed_line(screen, _DIAGNOSIS_INDEX)
        assert screen.remove_line(line.assertion_id) is True
        assert screen.learning_queue() == ()
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        assert not config_root.exists()
        screen.deleteLater()

        moved, _r = self._screen(
            config_root=tmp_path / "moved", learning_status_provider=_learning_on
        )
        line = _routed_line(moved, _DIAGNOSIS_INDEX)
        target = line.allowed_sections[0]
        assert moved.move_line(line.assertion_id, target) is True
        assert tuple(moved._learning_queue) == (manual_assertion_id(_DIAGNOSIS_INDEX),)
        assert moved.learning_queue() == ((target, _DIAGNOSIS_PHRASE),)
        moved.deleteLater()

    # --- round 34 pins ----------------------------------------------------

    def test_the_chooser_keeps_its_selection_across_a_refinalise(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 34 LOW-002: every re-finalise rebuilds the chooser; the
        practitioner's current line and section are carried across by data."""
        screen, _record = self._screen(config_root=tmp_path / "config")
        assert screen.utterance_combo.count() >= 2
        screen.utterance_combo.setCurrentIndex(1)
        chosen = screen.utterance_combo.currentData()
        assert screen.section_combo.count() >= 2
        screen.section_combo.setCurrentIndex(1)
        chosen_section = screen.section_combo.currentData()
        proposal = screen._draft.note_proposals[0]
        screen.confirm_proposal(proposal.proposal_id)  # re-finalises the note
        assert screen.utterance_combo.currentData() == chosen
        assert screen.section_combo.currentData() == chosen_section
        screen.deleteLater()

    def test_the_learning_status_is_re_read_at_each_add(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 34 LOW-003: learning turned on mid-review (on the Practitioner
        tab) applies to the next add — the gate and the line are re-read."""
        enabled = {"on": False}

        def provider() -> models.LearningStatus:
            if enabled["on"]:
                return models.LearningStatus(True, None)
            return models.LearningStatus(False, models.LEARNING_OPTED_OUT_HINT)

        screen, _record = self._screen(
            config_root=tmp_path / "config", learning_status_provider=provider
        )
        assert screen.learning_label.text() == models.LEARNING_OPTED_OUT_HINT
        enabled["on"] = True
        key = _eligible(screen)[_LEARNABLE_INDEX].allowed_sections[0]
        assert screen.add_line(_LEARNABLE_INDEX, key) is True
        assert screen.learning_queue() == ((key, _LEARNABLE_PHRASE),)
        assert screen.learning_label.text() == models.learning_queued_line(1)
        screen.deleteLater()

    # --- live smoke 2026-09-17: the queue must name Save note on this tab -----

    def test_the_learning_line_names_save_note_while_phrases_are_queued(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """The practitioner read the queued-phrase status as the outcome and
        left the review by another exit; nothing is written on any exit but
        Save note on this tab, so the line must say so while the queue is
        non-empty, and stand down when it empties or the note is saved."""
        config_root = tmp_path / "config"
        screen, record = self._screen(
            config_root=config_root, learning_status_provider=_learning_on
        )
        assert screen.learning_label.text() == models.LEARNING_ON_LINE
        key = _eligible(screen)[_LEARNABLE_INDEX].allowed_sections[0]
        assert screen.add_line(_LEARNABLE_INDEX, key) is True
        line = screen.learning_label.text()
        assert line == models.learning_queued_line(1)
        assert "Save note on this tab" in line
        assert "Cancel, Delete and Complete learn nothing" in line
        assert "Save note on this tab" in screen.edit_status_label.text()
        assert screen.undo_line(manual_assertion_id(_LEARNABLE_INDEX)) is True
        assert screen.learning_label.text() == models.LEARNING_ON_LINE
        assert screen.add_line(_LEARNABLE_INDEX, key) is True
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        assert screen.learning_label.text() == models.LEARNING_ON_LINE  # queue written
        assert "Learned 1" in screen.edit_status_label.text()
        # The tooltip sits on the button labelled "Save note", so it names
        # what that button does with the queue, not the button itself.
        assert "queued for learning are written here" in screen.save_button.toolTip()
        assert "1 phrase queued" in models.learning_queued_line(1)
        assert "2 phrases queued" in models.learning_queued_line(2)
        screen.deleteLater()

    def test_save_after_edits_that_queued_nothing_says_why(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Lines were added but nothing queued: Save says so instead of
        staying silent — the off-reason when learning is off, the
        ownership/filter reason when it is on. A review with no edit at all
        reports nothing about learning."""
        config_root = tmp_path / "config"
        # Learning ON, but the only added line is the patient's.
        screen, record = self._screen(
            config_root=config_root, learning_status_provider=_learning_on
        )
        document = screen._document
        choice = next(
            item
            for item in screen.eligible_utterances()
            if document.transcript_segments[item.segment_index].speaker == SPEAKER_1
        )
        assert screen.add_line(choice.segment_index, choice.allowed_sections[0]) is True
        assert models.LEARNING_NOT_ATTRIBUTED_NOTE in screen.edit_status_label.text()
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        status = screen.edit_status_label.text()
        assert status.startswith("Nothing learned from this note:")
        assert "one of yours" in status
        assert not config_root.exists()
        screen.deleteLater()

        # Learning OFF (opted out), a clinician line added.
        off, record_off = self._screen(
            config_root=config_root,
            learning_status_provider=lambda: models.LearningStatus(
                False, models.LEARNING_OPTED_OUT_HINT
            ),
        )
        key = _eligible(off)[_LEARNABLE_INDEX].allowed_sections[0]
        assert off.add_line(_LEARNABLE_INDEX, key) is True
        self._ratify(off)
        off.save()
        assert len(record_off["saved"]) == 1
        status = off.edit_status_label.text()
        assert status.startswith("Nothing learned from this note.")
        assert models.LEARNING_OPTED_OUT_HINT in status
        off.deleteLater()

        # No edit at all: Save says nothing about learning.
        plain, record_plain = self._screen(
            config_root=config_root, learning_status_provider=_learning_on
        )
        self._ratify(plain)
        plain.edit_status_label.setText("")
        plain.save()
        assert len(record_plain["saved"]) == 1
        assert plain.edit_status_label.text() == ""
        plain.deleteLater()

    # --- peer round 36 pins -----------------------------------------------

    def test_a_name_after_a_leading_filler_is_refused_by_the_learner(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR-HIGH-008 (verified MED): the real segment-start status travels
        with the candidate — a dropped leading filler cannot hand the opener
        exemption to a capitalised name after it; at a true start the pinned
        heuristic's admission of the same word stands."""
        turns = (
            *_NOTE_TURNS,
            ("Um, Will needs the exercises", SPEAKER_2),  # 4: filler, then a name
            ("Will needs the exercises", SPEAKER_2),  # 5: the same word at the start
        )
        screen, _record = self._screen(
            config_root=tmp_path / "config",
            result=_edit_result(turns),
            learning_status_provider=_learning_on,
        )
        for index in (4, 5):
            assert index in _eligible(screen), "the fixture lines must stay unrouted"
        key = _eligible(screen)[4].allowed_sections[0]
        assert screen.add_line(4, key) is True
        status = screen.edit_status_label.text()
        assert "Not learned" in status and "(name)" in status
        assert screen.learning_queue() == ()
        assert screen.add_line(5, key) is True
        assert screen.learning_queue() == ((key, "will needs the exercises"),)
        screen.deleteLater()

    def test_a_committed_phrase_with_a_failed_date_record_is_reported_and_listed(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PR-MED-023: a sidecar write that fails after the cue file was
        replaced is reported as learned-without-a-date, and the tab is told to
        refresh — never "were not learned"."""
        config_root = tmp_path / "config"
        real = note_config_module.atomic_write_bytes

        def selective(path: Path, blob: bytes, *, error_label: str) -> None:
            if path.name == LEARNED_SIDECAR_FILENAME:
                raise StoreWriteError(f"failed writing {error_label}: disk full")
            real(path, blob, error_label=error_label)

        monkeypatch.setattr(note_config_module, "atomic_write_bytes", selective)
        screen, record = self._screen(
            config_root=config_root, learning_status_provider=_learning_on
        )
        key = _eligible(screen)[_LEARNABLE_INDEX].allowed_sections[0]
        assert screen.add_line(_LEARNABLE_INDEX, key) is True
        refreshed: list[int] = []
        screen.learned_phrases_changed.connect(lambda: refreshed.append(1))
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        status = screen.edit_status_label.text()
        assert "Learned 1" in status
        assert "date record could not be written" in status
        assert "were not learned" not in status
        assert refreshed == [1]
        learned = load_learned_phrases(config_root)
        assert learned.by_section == ((key, (_LEARNABLE_PHRASE,)),)
        assert learned.recent == ()
        screen.deleteLater()

    def test_save_never_raises_after_the_note_is_committed(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR-MED-025 through the REAL atomic writer: a sidecar write that
        fails AND whose temp file cannot be unlinked (a directory planted at
        the temp path) must still leave `save()` returning normally — the
        note committed, the controls refreshed, the state emitted, the cue
        reported as learned without a date, the tab told to refresh."""
        config_root = tmp_path / "config"
        config_root.mkdir(parents=True)
        (config_root / (LEARNED_SIDECAR_FILENAME + ".tmp")).mkdir()
        screen, record = self._screen(
            config_root=config_root, learning_status_provider=_learning_on
        )
        key = _eligible(screen)[_LEARNABLE_INDEX].allowed_sections[0]
        assert screen.add_line(_LEARNABLE_INDEX, key) is True
        refreshed: list[int] = []
        screen.learned_phrases_changed.connect(lambda: refreshed.append(1))
        self._ratify(screen)
        states_before = len(record["states"])
        screen.save()  # must not raise
        assert len(record["saved"]) == 1
        assert not screen.save_button.isEnabled()  # controls updated after the write
        assert len(record["states"]) > states_before
        assert record["states"][-1].note_saved is True  # state emitted after the write
        status = screen.edit_status_label.text()
        assert "Learned 1" in status
        assert "date record could not be written" in status
        assert refreshed == [1]
        cues = load_note_config(config_root).normalised_cues()
        assert tuple(_LEARNABLE_PHRASE.split()) in cues[key]
        screen.deleteLater()

    def test_a_second_add_of_the_same_utterance_is_refused(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Task H6: the chooser's "already in the note" test reads the WORKING
        draft, which every mutation re-derives — so an utterance is added once,
        can be added again only after its Undo, and a Removed provider line's
        utterance can be added back exactly once."""
        screen, _record = self._screen(config_root=tmp_path / "config")
        manual_id = manual_assertion_id(_LEARNABLE_INDEX)
        key = _eligible(screen)[_LEARNABLE_INDEX].allowed_sections[0]
        assert screen.add_line(_LEARNABLE_INDEX, key) is True
        assert screen.add_line(_LEARNABLE_INDEX, key) is False
        assert screen.edit_status_label.text() == "That line is already in the note."
        assert [line.assertion_id for line in screen.editable_lines()].count(manual_id) == 1
        assert screen.undo_line(manual_id) is True
        assert screen.add_line(_LEARNABLE_INDEX, key) is True
        assert screen.add_line(_LEARNABLE_INDEX, key) is False
        line = _routed_line(screen, _DIAGNOSIS_INDEX)
        assert screen.add_line(_DIAGNOSIS_INDEX, line.section_key) is False
        assert screen.remove_line(line.assertion_id) is True
        assert screen.add_line(_DIAGNOSIS_INDEX, line.section_key) is True
        assert screen.add_line(_DIAGNOSIS_INDEX, line.section_key) is False
        assert screen.edit_status_label.text() == "That line is already in the note."
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Typed edits, shorthand learning and Save-as-ratification on the Note tab
# (note-learning-and-styles plan Phase 2, Tasks 2.1 / 2.3 / 2.4; D4, D5, D11).
# The widget rows and the inline editor are pinned in test_ui_note_editor.py;
# here the screen's edit / undo / queue / Save contract is driven directly.
# ---------------------------------------------------------------------------

_TYPED = "Mild knee sprain"
# `_EDIT_TURNS`' diagnosis line, "The diagnosis is a mild knee sprain": its
# trigger is the tail after the dropped opener.
_DIAGNOSIS_TRIGGER = "diagnosis is a mild knee sprain"


def _rooted_learned_result(
    config_root: Path,
    *,
    confirmations: int,
    turns: tuple[tuple[str, str], ...] = _EDIT_TURNS,
) -> tuple[models.NoteGenerationResult, str]:
    """A result whose config is the REAL loaded config under ``config_root``
    holding one learned rule ("ice pack" -> "Ice pack use explained.") with
    ``confirmations`` recorded, composed with the sidecar's entries — so the
    rule pre-fills once auto-confirmed and Save's outcomes find it on disk.
    A second call over the same root reuses the rule already there (with
    whatever count it has by then) instead of appending a duplicate."""
    existing = load_learned_rules(config_root).recent
    if existing:
        rule_id = existing[0].rule_id
    else:
        [added] = append_learned_rules(
            [LearnedRuleCandidate("advice_home_exercise", "ice pack", "Ice pack use explained.")],
            config_root=config_root,
            learned_at=datetime(2026, 9, 18, tzinfo=UTC),
        ).added
        rule_id = added.rule_id
    for _ in range(confirmations):
        record_rule_outcomes({rule_id: "confirmed"}, config_root=config_root)
    config = load_note_config(config_root)
    document = _note_document(turns)
    draft = compose_draft(
        document,
        config,
        ExtractiveNoteProvider(),
        clinician_speaker=SPEAKER_2,
        learned_rules=load_learned_rule_entries(config_root),
    )
    return models.NoteGenerationResult(draft=draft, config=config, document=document), rule_id


class TestNoteScreenTypedEdits:
    def _screen(
        self,
        *,
        config_root: Path,
        result: models.NoteGenerationResult | None = None,
        learning_status_provider: Callable[[], models.LearningStatus] | None = None,
    ) -> tuple[Any, dict[str, list[Any]]]:
        from scribe_desktop.ui.note import NoteScreen

        record: dict[str, list[Any]] = {"saved": [], "abandoned": [], "cancelled": []}
        screen = NoteScreen(
            config_root=config_root, learning_status_provider=learning_status_provider
        )
        screen.begin_review(
            result if result is not None else _edit_result(),
            on_save=lambda note: record["saved"].append(note),
            on_abandon=lambda: record["abandoned"].append(True),
            on_cancel=lambda: record["cancelled"].append(True),
            template_profile_id="clinic-a",
        )
        return screen, record

    def _ratify(self, screen: Any) -> None:
        for proposal in screen._draft.note_proposals:
            if proposal.proposal_id not in screen._prefilled_ids():
                screen.confirm_proposal(proposal.proposal_id)
        screen._acknowledge_all()

    # --- Task 2.1: the typed line end to end ------------------------------------

    def test_an_edit_produces_a_clinician_line_through_finalise_and_write(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.session_store import read_note, write_note
        from scribe_desktop.transcription import write_transcript

        screen, record = self._screen(config_root=tmp_path / "config")
        line = _routed_line(screen, _DIAGNOSIS_INDEX)
        original = _note_assertion(screen, line.assertion_id)
        assert screen.edit_line(line.assertion_id, f"  {_TYPED}  ") is True
        typed = _note_assertion(screen, "t0001")
        assert typed is not None
        assert typed.provenance == "clinician"
        assert typed.text == _TYPED
        assert typed.section_key == original.section_key
        assert typed.replaces == line.assertion_id
        assert typed.confirmation is not None and typed.confirmation.decided_by == "clinician"
        assert typed.confirmation.proposal_id == "t0001"
        assert _note_assertion(screen, line.assertion_id) is None
        assert f"  - {_TYPED}  [{models.provenance_label('clinician')}]" in (
            screen.note_body.toPlainText()
        )
        row = _lines_by_id(screen)[line.assertion_id]
        assert row.state == "replaced" and row.replaced_by == "t0001"
        [typed_row] = screen.typed_lines()
        assert (typed_row.assertion_id, typed_row.replaces) == ("t0001", line.assertion_id)
        # The replaced utterance is still spoken for: the chooser omits it.
        assert _DIAGNOSIS_INDEX not in _eligible(screen)
        # A typed line draws the clinician_asserted review like any authored line.
        assert "clinician_asserted" in _warning_codes(screen)
        assert screen.current_review_state().unacknowledged_reviews > 0
        self._ratify(screen)
        screen.save()
        [saved] = record["saved"]
        assert isinstance(saved, GeneratedNote)
        landed = next(
            a for s in saved.note_sections for a in s.note_assertions if a.assertion_id == "t0001"
        )
        assert landed.provenance == "clinician" and landed.replaces == line.assertion_id
        session_dir = tmp_path / _NOTE_SESSION_ID
        session_dir.mkdir()
        crypto = SessionCrypto()
        write_transcript(session_dir, crypto, screen._document)
        write_note(session_dir, crypto, saved, screen._config)
        assert read_note(session_dir, crypto) == saved
        screen.deleteLater()

    def test_undo_restores_the_replaced_line_from_either_row(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, _record = self._screen(config_root=tmp_path / "config")
        line = _routed_line(screen, _DIAGNOSIS_INDEX)
        body = screen.note_body.toPlainText()
        # Typed ids are NEVER reused within a review (the counter only climbs):
        # an undone id must not resolve to a later line. So the first edit is
        # t0001 and, once undone, the next is t0002.
        for expected_id, undo_by in (("t0001", "typed"), ("t0002", "replaced")):
            assert screen.edit_line(line.assertion_id, _TYPED) is True
            [typed_row] = screen.typed_lines()
            assert typed_row.assertion_id == expected_id
            undo_id = typed_row.assertion_id if undo_by == "typed" else line.assertion_id
            assert screen.undo_line(undo_id) is True
            assert screen.typed_lines() == ()
            assert screen.undo_line(expected_id) is False  # gone, not reusable
            assert screen.edit_line(expected_id, "anything") is False
            assert _note_assertion(screen, line.assertion_id) is not None
            assert _lines_by_id(screen)[line.assertion_id].state == "routed"
            assert screen.note_body.toPlainText() == body
        # Retyping keeps the id and what it replaced; an unchanged retype is refused.
        assert screen.edit_line(line.assertion_id, _TYPED) is True
        [typed_row] = screen.typed_lines()
        typed_id = typed_row.assertion_id
        assert typed_id == "t0003"
        assert screen.edit_line(typed_id, _TYPED) is False
        assert "unchanged" in screen.edit_status_label.text()
        assert screen.edit_line(typed_id, "Knee sprain, mild") is True
        assert _note_assertion(screen, typed_id).text == "Knee sprain, mild"
        assert _note_assertion(screen, typed_id).replaces == line.assertion_id
        assert [row.assertion_id for row in screen.typed_lines()] == [typed_id]
        screen.deleteLater()

    def test_an_edit_of_a_manual_line_sets_it_aside_and_undo_brings_it_back(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, _record = self._screen(
            config_root=tmp_path / "config", learning_status_provider=_learning_on
        )
        document = screen._document
        patient = next(
            choice
            for choice in screen.eligible_utterances()
            if document.transcript_segments[choice.segment_index].speaker == SPEAKER_1
        )
        key = patient.allowed_sections[0]
        assert screen.add_line(patient.segment_index, key) is True
        manual_id = manual_assertion_id(patient.segment_index)
        assert screen.edit_line(manual_id, "Walked to the shop") is True
        assert _note_assertion(screen, manual_id) is None
        assert _note_assertion(screen, "t0001").replaces == manual_id
        assert _lines_by_id(screen)[manual_id].state == "replaced"
        assert patient.segment_index not in _eligible(screen)
        # A patient's line teaches nothing, and the skip is SAID.
        assert screen.rule_queue() == ()
        assert models.LEARNING_NOT_ATTRIBUTED_NOTE in screen.edit_status_label.text()
        assert screen.undo_line("t0001") is True
        assert _note_assertion(screen, manual_id) is not None
        assert _lines_by_id(screen)[manual_id].state == "added"
        screen.deleteLater()

    def test_edits_refuse_bad_text_and_freeze_after_save(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, record = self._screen(config_root=tmp_path / "config")
        line = _routed_line(screen, _DIAGNOSIS_INDEX)
        for bad in ("", "   ", "Mild​sprain", "x" * 20_001):
            assert screen.edit_line(line.assertion_id, bad) is False
            assert screen.typed_lines() == ()
        assert screen.edit_line("nobody", _TYPED) is False
        assert "cannot be edited" in screen.edit_status_label.text()
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        assert screen.edit_line(line.assertion_id, _TYPED) is False
        assert "edits are closed" in screen.edit_status_label.text()
        screen.deleteLater()

    # --- Task 2.3: shorthand learning, written only on Save ------------------------

    def test_a_wording_the_rules_file_would_refuse_is_not_queued(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Phase H round 24 LOW-005: the rules file's own validation runs at
        the edit, so "Will learn" is never a promise Save withdraws."""
        screen, _record = self._screen(
            config_root=tmp_path / "config", learning_status_provider=_learning_on
        )
        line = _routed_line(screen, _DIAGNOSIS_INDEX)
        too_long = ("a " * 1100).strip()  # a valid typed line, not a valid rule
        assert screen.edit_line(line.assertion_id, too_long) is True
        assert screen.rule_queue() == () and screen.queued_rule_count() == 0
        status = screen.edit_status_label.text()
        assert f"Not learned: {RULE_WORDING_TOO_LONG}." in status
        assert "Will learn" not in status
        screen.deleteLater()

    def test_the_status_line_says_a_plain_reason_never_the_validators_message(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Phase H live smoke item 2 (2026-09-26): a typed line with a dash
        between words was refused with the rules file's AUTHORING message —
        rule id, "Value error", the JSON override — on the clinician's status
        line. The line now says the clinician's reason per class; the number
        class is unchanged; and a correction to an already-learned shorthand
        is checked at the edit the same way (it had been queued unchecked)."""
        authoring_text = ("learned-", "{", "Value error", "expansion entry")
        config_root = tmp_path / "config"
        screen, _record = self._screen(
            config_root=config_root, learning_status_provider=_learning_on
        )
        line = _routed_line(screen, _DIAGNOSIS_INDEX)
        # The dash case, as smoked.
        assert screen.edit_line(line.assertion_id, "Mild knee sprain - rest advised") is True
        assert screen.rule_queue() == () and screen.queued_rule_count() == 0
        status = screen.edit_status_label.text()
        assert f"Not learned: {RULE_WORDING_MANY_CLAIMS}." in status
        assert "Will learn" not in status
        assert not any(text in status for text in authoring_text)
        assert screen.undo_line("t0001") is True
        # The number case is unchanged.
        assert screen.edit_line(line.assertion_id, "Rest for 3 days") is True
        assert screen.rule_queue() == ()
        status = screen.edit_status_label.text()
        assert "Not learned: the typed wording contains a number/date/medication (" in status
        assert not any(text in status for text in authoring_text)
        screen.deleteLater()
        # A correction over an already-learned shorthand's line: the same
        # check at the edit, so Save never says "not updated (invalid: ...)".
        result, rule_id = _rooted_learned_result(config_root, confirmations=2)
        screen, _record = self._screen(
            config_root=config_root, result=result, learning_status_provider=_learning_on
        )
        [proposal] = [p for p in screen._draft.note_proposals if p.rule_id == rule_id]
        assert screen.edit_line(proposal.proposal_id, "Ice applied - well tolerated") is True
        assert screen.rule_replacement_queue() == ()
        status = screen.edit_status_label.text()
        # The proposal-line branch's own prefix (its number case says the same).
        assert f"Shorthand not updated: {RULE_WORDING_MANY_CLAIMS}." in status
        assert "Will update" not in status
        assert not any(text in status for text in authoring_text)
        screen.deleteLater()

    def test_a_typed_edit_over_the_practitioners_line_queues_a_rule_written_on_save(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        config_root = tmp_path / "config"
        screen, record = self._screen(
            config_root=config_root, learning_status_provider=_learning_on
        )
        line = _routed_line(screen, _DIAGNOSIS_INDEX)
        assert screen.edit_line(line.assertion_id, _TYPED) is True
        assert screen.rule_queue() == (
            LearnedRuleCandidate(line.section_key, _DIAGNOSIS_TRIGGER, _TYPED),
        )
        status = screen.edit_status_label.text()
        assert f"Will learn shorthand: '{_DIAGNOSIS_TRIGGER}' -> '{_TYPED}'" in status
        assert "Save note on this tab" in status
        assert screen.learning_label.text() == models.learning_queued_line(0, 1)
        assert screen.queued_rule_count() == 1
        assert not config_root.exists()  # nothing before Save
        refreshed: list[int] = []
        screen.learned_phrases_changed.connect(lambda: refreshed.append(1))
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        [learned] = load_learned_rules(config_root).recent
        assert learned.trigger_phrase == _DIAGNOSIS_TRIGGER
        assert learned.typed_wording == (_TYPED,)
        assert learned.section_key == line.section_key
        assert learned.confirmations == 0 and learned.auto_confirmed is False
        assert "Learned 1 shorthand" in screen.edit_status_label.text()
        assert "Practitioner tab" in screen.edit_status_label.text()
        assert refreshed == [1]
        assert screen.rule_queue() == () and screen.queued_rule_count() == 0
        assert screen.learning_label.text() == models.LEARNING_ON_LINE
        screen.deleteLater()

    def test_the_edit_and_save_status_lines_are_exact(self, qapp: Any, tmp_path: Path) -> None:
        """Task H6: the widget composes the status line from the decision
        module's verdict texts (set, then appended in order) — pinned here as
        WHOLE strings, where the pins above are substrings: a typed edit that
        queues a rule, and a Save report carrying a phrase part and a rule
        part. The hand-authored config pre-fills its lines, so no learned
        rule's count adds a third part."""
        config_root = tmp_path / "config"
        screen, record = self._screen(
            config_root=config_root,
            result=_edit_result(config=_hand_authored_config()),
            learning_status_provider=_learning_on,
        )
        key = _eligible(screen)[_LEARNABLE_INDEX].allowed_sections[0]
        assert screen.add_line(_LEARNABLE_INDEX, key) is True
        line = _routed_line(screen, _DIAGNOSIS_INDEX)
        title = models.section_title(line.section_key)
        assert screen.edit_line(line.assertion_id, _TYPED) is True
        assert screen.edit_status_label.text() == (
            f"Line replaced with your wording in {title}. Undo restores the original until "
            f"Save. Will learn shorthand: '{_DIAGNOSIS_TRIGGER}' -> '{_TYPED}' for {title} "
            "when you press Save note on this tab."
        )
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        assert screen.edit_status_label.text() == (
            f"Learned 1: '{_LEARNABLE_PHRASE}' for {models.section_title(key)}. "
            "Review learned phrases on the Practitioner tab. "
            f"Learned 1 shorthand: '{_DIAGNOSIS_TRIGGER}' -> '{_TYPED}' for {title}. "
            "Review learned shorthand on the Practitioner tab."
        )
        screen.deleteLater()

    def test_cancel_delete_discard_and_undo_write_no_rule(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        config_root = tmp_path / "config"
        for leave in ("cancel", "abandon", "clear", "undo"):
            screen, record = self._screen(
                config_root=config_root, learning_status_provider=_learning_on
            )
            line = _routed_line(screen, _DIAGNOSIS_INDEX)
            assert screen.edit_line(line.assertion_id, _TYPED) is True
            assert screen.queued_rule_count() == 1
            if leave == "cancel":
                screen.cancel_review()
                assert record["cancelled"] == [True]
            elif leave == "abandon":
                screen.abandon()
                assert record["abandoned"] == [True]
            elif leave == "clear":
                screen.clear()
            else:
                assert screen.undo_line("t0001") is True
                self._ratify(screen)
                screen.save()
                assert len(record["saved"]) == 1
            assert screen.rule_queue() == ()
            assert screen.queued_rule_count() == 0
            assert not config_root.exists(), leave
            screen.deleteLater()

    def test_the_filters_refuse_and_the_status_names_the_class(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, _record = self._screen(
            config_root=tmp_path / "config", learning_status_provider=_learning_on
        )
        line = _routed_line(screen, _DIAGNOSIS_INDEX)
        # The typed wording carries a number: the line stands, nothing is learned.
        assert screen.edit_line(line.assertion_id, "Sprain grade 2") is True
        assert _note_assertion(screen, "t0001").text == "Sprain grade 2"
        assert screen.rule_queue() == ()
        status = screen.edit_status_label.text()
        assert "Not learned: the typed wording contains" in status and "(number)" in status
        assert screen.undo_line("t0001") is True
        # The utterance carries a number: the trigger is refused by THE filter.
        plan = _routed_line(screen, _PLAN_INDEX)
        assert screen.edit_line(plan.assertion_id, "Review in a fortnight") is True
        assert screen.rule_queue() == ()
        status = screen.edit_status_label.text()
        assert "Not learned: the trigger contains" in status and "(number)" in status
        screen.deleteLater()

    def test_learning_off_or_a_config_line_teaches_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        off, _r = self._screen(
            config_root=tmp_path / "config",
            learning_status_provider=lambda: models.LearningStatus(
                False, models.LEARNING_OPTED_OUT_HINT
            ),
        )
        line = _routed_line(off, _DIAGNOSIS_INDEX)
        assert off.edit_line(line.assertion_id, _TYPED) is True
        assert off.rule_queue() == ()
        assert models.LEARNING_OPTED_OUT_HINT in off.edit_status_label.text()
        off.deleteLater()
        # A hand-authored pre-filled line (the prefill seed) has no utterance
        # behind it.
        on, _r = self._screen(
            config_root=tmp_path / "config", learning_status_provider=_learning_on
        )
        [knee] = [row for row in on.prefilled_lines() if "Knee effusion" in row.text]
        assert on.edit_line(knee.proposal_id, "Knee effusion absent") is True
        assert on.rule_queue() == () and on.rule_replacement_queue() == ()
        assert "came from your own config" in on.edit_status_label.text()
        on.deleteLater()

    # --- Task 2.4: pre-filled lines and the counted Save --------------------------

    def test_a_pre_filled_note_is_ratified_by_the_counted_save_while_a_review_gates(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, record = self._screen(
            config_root=tmp_path / "config", result=_edit_result(config=_hand_authored_config())
        )
        draft = screen._draft
        assert len(draft.config_decisions) == 2  # the hand rule and the prefill
        assert screen._rendered_excerpt == {}  # no confirm/decline rows
        assert not screen.proposals_header.isVisibleTo(screen)
        assert screen.proposals_scroll.isHidden()  # leg h1j: no empty framed box either
        rows = screen.prefilled_lines()
        assert [row.state for row in rows] == ["prefilled", "prefilled"]
        assert all(models.PREFILLED_MARK in row.label for row in rows)
        assert all(row.learned is False for row in rows)
        body = screen.note_body.toPlainText()
        assert f"[{models.PREFILLED_MARK} - autofill (clinician-authored)]" in body
        assert f"[{models.PREFILLED_MARK} - prefill (clinician-authored)]" in body
        assert screen.current_review_state().unconfirmed_proposals == 0
        assert "clinician_asserted" not in _warning_codes(screen)
        assert screen.save_button.text() == "Save - confirms the 2 pre-filled lines shown"
        # An UNRELATED review warning still gates: remove the routed line that
        # carries a number -> high_risk_omission, Save closed until acknowledged.
        plan = _routed_line(screen, _PLAN_INDEX)
        assert screen.remove_line(plan.assertion_id) is True
        assert "high_risk_omission" in _warning_codes(screen)
        assert not screen.save_button.isEnabled()
        screen.save()
        assert record["saved"] == []
        screen._acknowledge_all()
        assert screen.save_button.isEnabled()
        screen.save()
        [saved] = record["saved"]
        prefilled = [
            a for s in saved.note_sections for a in s.note_assertions if models.is_prefilled(a)
        ]
        assert len(prefilled) == 2
        assert all(a.confirmation.decided_by == "config" for a in prefilled)
        assert screen.save_button.text() == models.SAVE_BUTTON_LABEL
        screen.deleteLater()

    def test_save_is_refused_while_a_proposal_the_config_did_not_decide_is_pending(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen, record = self._screen(config_root=tmp_path / "config")
        [pending] = [
            p for p in screen._draft.note_proposals if p.rule_id == _LEARNED_RULE_ID
        ]
        assert pending.proposal_id in screen._rendered_excerpt  # it has a row
        assert screen.current_review_state().unconfirmed_proposals == 1
        assert screen.save_button.text() == "Save - confirms the 1 pre-filled line shown"
        screen._acknowledge_all()
        assert not screen.save_button.isEnabled()
        screen.save()
        assert record["saved"] == []
        assert "Confirm every proposed line" in screen.message_label.text()
        screen.confirm_proposal(pending.proposal_id)
        screen._acknowledge_all()
        assert screen.save_button.isEnabled()
        screen.save()
        assert len(record["saved"]) == 1
        screen.deleteLater()

    def test_remove_of_a_pre_filled_learned_line_declines_it_and_demotes_the_rule(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        config_root = tmp_path / "config"
        result, rule_id = _rooted_learned_result(
            config_root, confirmations=LEARNED_RULE_AUTO_CONFIRM_AFTER
        )
        assert load_learned_rule_entries(config_root)[rule_id].auto_confirmed is True
        screen, record = self._screen(
            config_root=config_root, result=result, learning_status_provider=_learning_on
        )
        # The shipped defaults hold no rules or prefills, so the learned rule
        # is the ONE pre-filled line under this root.
        [learned_row] = screen.prefilled_lines()
        assert learned_row.learned and learned_row.state == "prefilled"
        assert screen.save_button.text() == "Save - confirms the 1 pre-filled line shown"
        assert screen.remove_line(learned_row.proposal_id) is True
        assert "Save will record that you declined it" in screen.edit_status_label.text()
        [learned_row] = screen.prefilled_lines()
        assert learned_row.state == "removed"
        assert screen.save_button.text() == models.SAVE_BUTTON_LABEL
        assert "Ice pack use explained." not in screen.note_body.toPlainText()
        assert screen.current_review_state().unconfirmed_proposals == 0
        self._ratify(screen)
        screen.save()
        [saved] = record["saved"]
        ids = {a.assertion_id for s in saved.note_sections for a in s.note_assertions}
        assert learned_row.proposal_id not in ids
        entry = load_learned_rule_entries(config_root)[rule_id]
        assert (entry.confirmations, entry.auto_confirmed) == (0, False)
        assert "will propose again" in screen.edit_status_label.text()
        # The rule itself is never deleted: it PROPOSES next time.
        assert [r.rule_id for r in load_learned_rules(config_root).recent] == [rule_id]
        screen.deleteLater()

    def test_an_unchanged_pre_filled_line_and_a_confirmed_proposal_each_count_once(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        config_root = tmp_path / "config"
        result, rule_id = _rooted_learned_result(config_root, confirmations=0)
        screen, record = self._screen(
            config_root=config_root, result=result, learning_status_provider=_learning_on
        )
        [proposal] = [p for p in screen._draft.note_proposals if p.rule_id == rule_id]
        assert proposal.proposal_id in screen._rendered_excerpt  # proposes: count 0
        self._ratify(screen)  # confirms it by click
        screen.save()
        assert len(record["saved"]) == 1
        assert load_learned_rule_entries(config_root)[rule_id].confirmations == 1
        screen.deleteLater()
        # Two more: the third crosses the threshold and Save says so.
        for expected in (2, 3):
            result, _ = _rooted_learned_result(config_root, confirmations=0)  # re-reads
            again, record = self._screen(
                config_root=config_root, result=result, learning_status_provider=_learning_on
            )
            self._ratify(again)
            again.save()
            entry = load_learned_rule_entries(config_root)[rule_id]
            assert entry.confirmations == expected
            assert entry.auto_confirmed is (expected == LEARNED_RULE_AUTO_CONFIRM_AFTER)
            if entry.auto_confirmed:
                assert "will now arrive pre-filled" in again.edit_status_label.text()
            again.deleteLater()
        # Now it arrives PRE-FILLED and an unchanged line counts a fourth.
        result, _ = _rooted_learned_result(config_root, confirmations=0)
        prefilled, record = self._screen(
            config_root=config_root, result=result, learning_status_provider=_learning_on
        )
        assert [row.learned for row in prefilled.prefilled_lines()].count(True) == 1
        self._ratify(prefilled)
        prefilled.save()
        assert load_learned_rule_entries(config_root)[rule_id].confirmations == 4
        prefilled.deleteLater()

    def test_editing_a_learned_rules_line_replaces_its_wording_in_place_on_save(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        config_root = tmp_path / "config"
        result, rule_id = _rooted_learned_result(config_root, confirmations=2)
        screen, record = self._screen(
            config_root=config_root, result=result, learning_status_provider=_learning_on
        )
        [proposal] = [p for p in screen._draft.note_proposals if p.rule_id == rule_id]
        assert screen.edit_line(proposal.proposal_id, "Ice applied") is True
        assert screen.rule_replacement_queue() == ((rule_id, "Ice applied"),)
        assert screen.rule_queue() == ()
        assert "Will update this learned shorthand rule's wording" in (
            screen.edit_status_label.text()
        )
        assert screen.current_review_state().unconfirmed_proposals == 0
        assert screen.learning_label.text() == models.learning_queued_line(0, 1)
        # A click on the replaced proposal is ignored until Undo.
        screen.confirm_proposal(proposal.proposal_id)
        assert proposal.proposal_id not in screen._resolutions
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        [rule] = [r for r in load_note_config(config_root).autofill_rules if r.rule_id == rule_id]
        assert rule.expansion_texts() == ("Ice applied",)
        assert rule.trigger_phrase == "ice pack"
        entry = load_learned_rule_entries(config_root)[rule_id]
        assert (entry.confirmations, entry.auto_confirmed) == (0, False)
        assert [h.previous_expansion for h in entry.history] == [("Ice pack use explained.",)]
        assert "Updated a learned shorthand rule's wording" in screen.edit_status_label.text()
        screen.deleteLater()

    def test_a_removed_pre_filled_learned_line_demotes_even_with_learning_off(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 12 MED-002: with learning OFF at Save nothing new is learned
        and nothing is promoted, but the practitioner's Remove still resets
        the rule — otherwise it would pre-fill again on the next note."""
        config_root = tmp_path / "config"
        result, rule_id = _rooted_learned_result(
            config_root, confirmations=LEARNED_RULE_AUTO_CONFIRM_AFTER
        )
        off = lambda: models.LearningStatus(False, models.LEARNING_OPTED_OUT_HINT)  # noqa: E731
        screen, record = self._screen(
            config_root=config_root, result=result, learning_status_provider=off
        )
        [learned_row] = screen.prefilled_lines()
        assert screen.remove_line(learned_row.proposal_id) is True
        # A typed edit elsewhere queues nothing under learning-off...
        line = _routed_line(screen, _DIAGNOSIS_INDEX)
        assert screen.edit_line(line.assertion_id, _TYPED) is True
        assert screen.rule_queue() == ()
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        entry = load_learned_rule_entries(config_root)[rule_id]
        assert (entry.confirmations, entry.auto_confirmed) == (0, False)
        assert "will propose again" in screen.edit_status_label.text()
        screen.deleteLater()
        # ...and an unchanged pre-filled line does NOT count (no promotion off-consent).
        result, _ = _rooted_learned_result(config_root, confirmations=2)
        on_the_edge, record = self._screen(
            config_root=config_root, result=result, learning_status_provider=off
        )
        self._ratify(on_the_edge)
        on_the_edge.save()
        assert len(record["saved"]) == 1
        entry = load_learned_rule_entries(config_root)[rule_id]
        assert (entry.confirmations, entry.auto_confirmed) == (2, False)
        on_the_edge.deleteLater()

    def test_a_correction_never_inherits_the_old_wordings_confirmation(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 12 MED-001: counts are recorded BEFORE in-place corrections,
        so a new wording starts at 0 even when the old wording's proposal was
        confirmed by click in the same review."""
        config_root = tmp_path / "config"
        # An extra clinician turn whose tail IS the learned trigger ("ok" is
        # trailing discourse): typing over it corrects that rule in place.
        turns = (*_EDIT_TURNS, ("Ice pack ok", SPEAKER_2))
        result, rule_id = _rooted_learned_result(config_root, confirmations=1, turns=turns)
        screen, record = self._screen(
            config_root=config_root, result=result, learning_status_provider=_learning_on
        )
        [proposal] = [p for p in screen._draft.note_proposals if p.rule_id == rule_id]
        screen.confirm_proposal(proposal.proposal_id)  # the OLD wording, confirmed
        ice_index = len(turns) - 1
        if ice_index in _eligible(screen):  # unrouted by the shipped cues: add it first
            key = _eligible(screen)[ice_index].allowed_sections[0]
            assert screen.add_line(ice_index, key) is True
            target_id = manual_assertion_id(ice_index)
        else:
            target_id = _routed_line(screen, ice_index).assertion_id
        assert screen.edit_line(target_id, "Ice applied") is True
        assert screen.rule_replacement_queue() == ((rule_id, "Ice applied"),)
        assert "Will update the learned shorthand for 'ice pack'" in (
            screen.edit_status_label.text()
        )
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        entry = load_learned_rule_entries(config_root)[rule_id]
        assert (entry.confirmations, entry.auto_confirmed) == (0, False)
        assert [h.previous_expansion for h in entry.history] == [("Ice pack use explained.",)]
        screen.deleteLater()

    def test_a_generation_note_is_shown_beside_the_config_report(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 12 MED-003 (C8): the generator's note about an unreadable
        learned-shorthand record reaches the Note tab, as plain text."""
        from PySide6.QtCore import Qt

        base = _edit_result()
        noted = models.NoteGenerationResult(
            draft=base.draft, config=base.config, document=base.document,
            notes=(models.LEARNED_RULES_UNREADABLE_NOTE.format(reason="<b>x</b>"),),
        )
        screen, _record = self._screen(config_root=tmp_path / "config", result=noted)
        assert screen.info_label.textFormat() == Qt.TextFormat.PlainText
        text = screen.info_label.text()
        assert "Autofill rules: 1" in text
        assert "could not be read (<b>x</b>)" in text
        screen.deleteLater()

    def test_every_persisted_count_refreshes_the_connected_practitioner_tab(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Peer round 14 PR-LOW-024: a Save that only moves a learned rule's
        count 0→1 or 1→2 still refreshes the Practitioner tab's "Learned
        shorthand" lists through the connected signal — no manual refresh —
        and so does a correction whose sidecar reset landed but whose
        rules-file write failed."""
        config_root = tmp_path / "config"
        practitioner = _practitioner_screen(
            FakeController(), FakeBackend(), tmp_path, config_root=config_root
        )

        def listed() -> str:
            assert practitioner.learned_rules_list.count() == 1
            return str(practitioner.learned_rules_list.item(0).text())

        for expected in (1, 2):
            result, rule_id = _rooted_learned_result(config_root, confirmations=0)
            practitioner.refresh_learned_rules()  # the tab as it stood before this Save
            assert f"(confirmed {expected - 1} of 3)" in listed()
            screen, record = self._screen(
                config_root=config_root, result=result, learning_status_provider=_learning_on
            )
            # The main window's wiring (`learned_phrases_changed` -> the tab's
            # refresh), connected here the same way.
            screen.learned_phrases_changed.connect(practitioner.refresh_learned_rules)
            self._ratify(screen)  # confirms the learned proposal by click
            screen.save()
            assert len(record["saved"]) == 1
            assert load_learned_rule_entries(config_root)[rule_id].confirmations == expected
            assert f"(confirmed {expected} of 3)" in listed()
            screen.deleteLater()
        # A correction whose sidecar reset lands but whose rules write fails:
        # the tab shows the reset count, not the stale one.
        result, rule_id = _rooted_learned_result(config_root, confirmations=0)
        screen, record = self._screen(
            config_root=config_root, result=result, learning_status_provider=_learning_on
        )
        screen.learned_phrases_changed.connect(practitioner.refresh_learned_rules)
        [proposal] = [p for p in screen._draft.note_proposals if p.rule_id == rule_id]
        assert screen.edit_line(proposal.proposal_id, "Ice applied") is True
        assert screen.rule_replacement_queue() == ((rule_id, "Ice applied"),)
        real = note_config_module.atomic_write_bytes

        def rules_write_fails(path: Path, blob: bytes, *, error_label: str) -> None:
            if path.name == AUTOFILL_RULES_FILENAME:
                raise StoreWriteError(f"failed writing {error_label}: disk full")
            real(path, blob, error_label=error_label)

        monkeypatch.setattr(note_config_module, "atomic_write_bytes", rules_write_fails)
        self._ratify(screen)
        screen.save()
        assert len(record["saved"]) == 1
        assert "Shorthand wording was not updated" in screen.edit_status_label.text()
        entry = load_learned_rule_entries(config_root)[rule_id]
        assert (entry.confirmations, entry.auto_confirmed) == (0, False)
        assert "(confirmed 0 of 3)" in listed()
        assert "'Ice pack use explained.'" in listed()  # the old wording still in force
        screen.deleteLater()
        practitioner.deleteLater()

    def test_the_exit_and_queue_lines_name_rules(self) -> None:
        assert models.unlearned_on_exit_line(0, 1) == (
            "1 queued shorthand rule was not learned - only Save note on the Note tab "
            "learns them."
        )
        assert models.unlearned_on_exit_line(2, 1).startswith(
            "2 queued phrases and 1 queued shorthand rule were not learned"
        )
        assert models.unlearned_on_exit_line(1) == (
            "1 queued phrase was not learned - only Save note on the Note tab learns them."
        )
        assert "1 phrase and 2 shorthand rules queued" in models.learning_queued_line(1, 2)
        assert models.save_button_label(0) == models.SAVE_BUTTON_LABEL == "Save note"
        assert models.save_button_label(1) == "Save - confirms the 1 pre-filled line shown"


# ---------------------------------------------------------------------------
# Transcript screen generation controls (Task 7.2 + 7.5).
# ---------------------------------------------------------------------------


class TestTranscriptGeneration:
    def _screen(self, controller: FakeController) -> tuple[Any, models.NoteGenerationResult]:
        from scribe_desktop.ui.transcript import TranscriptScreen

        result = _note_result()

        def factory(**_kwargs: Any) -> Callable[[Path, Any], models.NoteGenerationResult]:
            return lambda _directory, _crypto: result

        screen = TranscriptScreen(
            controller, note_generator_factory=factory, config_loader=_note_config
        )
        screen.show_document(
            _note_document(),
            on_complete=controller.complete,
            on_discard=controller.discard,
            can_generate=True,
        )
        return screen, result

    def test_generate_disabled_until_role_and_profile_confirmed(self, qapp: Any) -> None:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        assert not screen.generate_button.isEnabled()
        screen.set_role(SPEAKER_2)
        assert not screen.generate_button.isEnabled()  # profile still unconfirmed
        screen.set_profile("clinic-a")
        assert screen.generate_button.isEnabled()
        screen.deleteLater()

    def test_generate_composes_draft_on_a_task_thread(self, qapp: Any) -> None:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, result = self._screen(controller)
        drafts: list[Any] = []
        screen.draft_ready.connect(drafts.append)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert screen.is_busy  # lease held from the start of generation
        assert _process_until(qapp, lambda: bool(drafts))
        assert drafts[0] is result
        assert ("begin_generation",) in controller.calls
        assert ("with_generation_custody",) in controller.calls
        assert screen.is_busy  # still held through review
        screen.deleteLater()

    def test_generate_refused_by_a_draft_write_names_the_write(self, qapp: Any) -> None:
        """Draft-write plan D9 (round 15): the refusal shows the write's line
        through ``custody_refusal_text``, never the error's own text."""
        from scribe_desktop.session import WriteInFlightError

        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        controller.generation_error = WriteInFlightError("generation")
        screen, _result = self._screen(controller)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert screen.message_label.text() == (
            "Cannot generate a note now: " + models.write_line("write_in_flight")
        )
        assert not screen.is_busy
        assert ("with_generation_custody",) not in controller.calls
        screen.deleteLater()

    def _live(self, status: WriteRecordStatus | Exception) -> FakeController:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        controller.session_value = RecordingSession(consent=unlinked_consent()).with_state(
            SessionState.QUEUED
        )
        controller.write_status = status
        return controller

    @staticmethod
    def _pending_line(status: WriteRecordStatus | Exception) -> str:
        """Round 26 MED-001: an OPEN attempt's ``write_pending`` carries the
        ``write_uncertain`` prefix (PR-MED-017); an unreadable record or a
        failed read is ``record_unreadable``, which claims no attempt."""
        if isinstance(status, Exception) or status.outcome == "unreadable":
            return models.write_line("record_unreadable")
        return models.write_line("write_pending", uncertain=status.open_attempt)

    def test_the_pending_lines_differ_by_status(self) -> None:
        warning = models.WRITE_LINES["write_uncertain"]
        for outcome in ("attempting", "unknown"):
            assert self._pending_line(WriteRecordStatus(outcome)).startswith(f"{warning} ")
        for status in (
            WriteRecordStatus("refused", note_matches=True, refusal="note_not_found"),
            WriteRecordStatus("written", note_matches=True),
        ):
            assert self._pending_line(status) == models.write_line("write_pending")
        for failed in (WriteRecordStatus("unreadable"), RuntimeError("x")):
            line = self._pending_line(failed)
            assert "attempted" not in line and not line.startswith(warning)

    @pytest.mark.parametrize(
        "status",
        [
            WriteRecordStatus("attempting"),
            WriteRecordStatus("unknown"),
            WriteRecordStatus("refused", note_matches=True, refusal="note_not_found"),
            WriteRecordStatus("written", note_matches=True),
            WriteRecordStatus("unreadable"),
            RuntimeError("the record could not be read"),
        ],
    )
    def test_any_write_attempt_refuses_regenerate(
        self, qapp: Any, status: WriteRecordStatus | Exception
    ) -> None:
        """Draft-write D5 / Task 3.3 (R22-15): once any attempt exists — or
        the record cannot be read at all (fail closed) — the saved note is
        frozen: no lease is taken."""
        controller = self._live(status)
        screen, _result = self._screen(controller)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert screen.message_label.text() == (
            "Cannot generate a note now: " + self._pending_line(status)
        )
        assert ("begin_generation",) not in controller.calls
        assert not screen.is_busy
        assert controller.session_value is not None
        assert ("write_record_status", controller.session_value.session_id) in controller.calls
        screen.deleteLater()

    def test_a_write_in_flight_is_named_not_called_earlier(
        self, qapp: Any, monkeypatch: Any
    ) -> None:
        """Round 27 LOW-002: while a write is in flight the record's
        ``attempting`` row is THAT write — Generate and Save show
        ``write_in_flight``, never the uncertain prefix inviting Copy."""
        from scribe_desktop.ui.transcript import WritePendingError

        controller = self._live(WriteRecordStatus("none"))
        screen, _result = self._screen(controller)
        monkeypatch.setattr("scribe_desktop.ui.transcript.write_note", lambda *args: None)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert _process_until(qapp, lambda: screen._generation_result is not None)
        assert controller.session_value is not None
        controller.write_status = WriteRecordStatus("attempting")
        controller.writing_id = controller.session_value.session_id
        with pytest.raises(WritePendingError) as info:
            screen.save_note(_note_result().draft)  # type: ignore[arg-type]
        assert str(info.value) == models.write_line("write_in_flight")
        assert screen.is_busy
        screen.deleteLater()
        fresh = self._live(WriteRecordStatus("attempting"))
        assert fresh.session_value is not None
        fresh.writing_id = fresh.session_value.session_id
        screen, _result = self._screen(fresh)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert screen.message_label.text() == (
            "Cannot generate a note now: " + models.write_line("write_in_flight")
        )
        assert ("begin_generation",) not in fresh.calls
        screen.deleteLater()

    def test_no_write_record_lets_generate_run(self, qapp: Any) -> None:
        controller = self._live(WriteRecordStatus("none"))
        screen, _result = self._screen(controller)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert ("begin_generation",) in controller.calls
        assert screen.is_busy
        screen.deleteLater()

    @pytest.mark.parametrize(
        "status",
        [
            WriteRecordStatus("attempting"),
            WriteRecordStatus("unknown"),
            WriteRecordStatus("refused", note_matches=True, refusal="note_not_found"),
            WriteRecordStatus("written", note_matches=True),
            WriteRecordStatus("unreadable"),
            RuntimeError("the record could not be read"),
        ],
    )
    def test_a_second_save_after_an_attempt_is_refused_and_keeps_the_lease(
        self, qapp: Any, monkeypatch: Any, status: WriteRecordStatus | Exception
    ) -> None:
        """Round 25 LOW-019: Save refuses on every status Generate refuses on."""
        from scribe_desktop.ui.transcript import WritePendingError

        controller = self._live(WriteRecordStatus("none"))
        screen, _result = self._screen(controller)
        writes: list[str] = []
        monkeypatch.setattr(
            "scribe_desktop.ui.transcript.write_note",
            lambda *args: writes.append("written"),
        )
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert _process_until(qapp, lambda: screen._generation_result is not None)
        controller.write_status = status
        with pytest.raises(WritePendingError) as info:
            screen.save_note(_note_result().draft)  # type: ignore[arg-type]
        assert str(info.value) == self._pending_line(status)
        assert writes == []
        assert screen.is_busy  # the lease stays held: Cancel review is the way out
        screen.deleteLater()

    def test_a_recovered_source_never_consults_the_live_record(self, qapp: Any) -> None:
        """The live session's record never refuses a recovered transcript's
        view (it has its own session); the screen does not even ask — not
        even when the live record holds a completed write (round 25
        LOW-020: a recovered transcript cannot generate, can_generate=False)."""
        controller = self._live(WriteRecordStatus("written", note_matches=True))
        screen, _result = self._screen(controller)
        screen.show_document(
            _note_document(),
            on_complete=lambda: None,
            on_discard=lambda: None,
            can_generate=False,
        )
        assert screen._write_pending() is None
        assert not any(call[0] == "write_record_status" for call in controller.calls)
        screen.deleteLater()

    # --- draft-write D6 (Task 4.2): Complete after a confirmed write ----------

    _WRITE_CALLS = ("reserve_write", "complete_after_write")

    def _completing(
        self, status: WriteRecordStatus | Exception
    ) -> tuple[Any, FakeController, list[str]]:
        controller = self._live(status)
        screen, _result = self._screen(controller)
        closed: list[str] = []
        screen.closed.connect(closed.append)
        return screen, controller, closed

    def test_a_written_record_completes_through_complete_after_write(self, qapp: Any) -> None:
        """Seen mode: the Complete button re-acquires the reservation and
        completes under it; the screen clears and says the draft is in
        Cliniko; nothing goes through the plain ``complete``."""
        screen, controller, closed = self._completing(
            WriteRecordStatus("written", note_matches=True)
        )
        assert controller.session_value is not None
        session_id = controller.session_value.session_id
        screen.on_complete()
        names = [call[0] for call in controller.calls]
        assert names.index("write_record_status") < names.index("reserve_write")
        assert names.index("reserve_write") < names.index("complete_after_write")
        assert ("reserve_write", session_id) in controller.calls
        assert ("complete",) not in controller.calls
        assert closed == ["written"]
        assert screen.message_label.text() == models.write_line("written_done")
        assert controller.held_reservation is None and controller.writing_id is None
        assert controller.write_releases == 0  # consumed by the completion, not released
        assert screen.transcript_view.toPlainText() == ""
        screen.deleteLater()

    @pytest.mark.parametrize(
        "status",
        [
            WriteRecordStatus("none"),
            WriteRecordStatus("attempting"),
            WriteRecordStatus("unknown"),
            WriteRecordStatus("refused", note_matches=True, refusal="note_not_found"),
            WriteRecordStatus("unreadable"),
        ],
    )
    def test_every_other_record_completes_as_before(
        self, qapp: Any, status: WriteRecordStatus
    ) -> None:
        """Manual Complete on a non-written session is unchanged (D6)."""
        screen, controller, closed = self._completing(status)
        screen.on_complete()
        assert ("complete",) in controller.calls
        assert not any(call[0] in self._WRITE_CALLS for call in controller.calls)
        assert closed == ["completed"]
        screen.deleteLater()

    def test_a_written_record_of_another_note_is_refused_never_completed_plainly(
        self, qapp: Any
    ) -> None:
        """D5 (round 31 LOW-002): a ``written`` record whose note identity
        differs — or whose saved note cannot be read — is ``write_uncertain``
        and never completes: nothing is reserved, and the plain ``complete``
        is never the way round the check."""
        screen, controller, closed = self._completing(
            WriteRecordStatus("written", note_matches=False)
        )
        screen.on_complete()
        assert screen.message_label.text() == (
            "Complete refused: " + models.write_line("write_uncertain")
        )
        assert ("complete",) not in controller.calls
        assert not any(call[0] in self._WRITE_CALLS for call in controller.calls)
        assert closed == []
        screen.deleteLater()

    @pytest.mark.parametrize(
        "status",
        [
            WriteRecordStatus("attempting"),
            WriteRecordStatus("unknown"),
            WriteRecordStatus("refused", note_matches=True, refusal="note_not_found"),
            WriteRecordStatus("written", note_matches=True),
            WriteRecordStatus("unreadable"),
            RuntimeError("the record could not be read"),
        ],
    )
    def test_delete_note_and_complete_is_refused_once_a_write_was_attempted(
        self, qapp: Any, status: WriteRecordStatus | Exception
    ) -> None:
        """D5 (round 31 LOW-001): the saved note is frozen once any attempt
        exists — the post-Save "delete note and complete without one" is
        refused by the same line as Regenerate and Save."""
        from scribe_desktop.ui.transcript import WritePendingError

        screen, controller, closed = self._completing(status)
        with pytest.raises(WritePendingError) as info:
            screen.abandon_note_and_complete()
        assert str(info.value) == self._pending_line(status)
        assert ("complete_deleting_saved_note",) not in controller.calls
        assert closed == []
        screen.deleteLater()

    def test_delete_note_and_complete_runs_with_no_write_record(self, qapp: Any) -> None:
        screen, controller, closed = self._completing(WriteRecordStatus("none"))
        screen.abandon_note_and_complete()
        assert ("complete_deleting_saved_note",) in controller.calls
        assert closed == ["completed"]
        screen.deleteLater()

    def test_a_failed_completion_releases_keeps_the_session_and_a_retry_succeeds(
        self, qapp: Any
    ) -> None:
        from scribe_desktop.session_store import StoreCorruptError

        screen, controller, closed = self._completing(
            WriteRecordStatus("written", note_matches=True)
        )
        controller.complete_after_write_error = StoreCorruptError(
            "transcript failed decrypt verification; key retained"
        )
        screen.on_complete()
        text = screen.message_label.text()
        assert text.startswith("Complete failed: StoreCorruptError: ")
        assert "No key deletion was performed by this action" in text
        assert closed == []
        assert controller.write_releases == 1 and controller.writing_id is None
        assert controller.state_value is SessionState.QUEUED
        assert screen.transcript_view.toPlainText() != ""  # the view stays loaded
        controller.complete_after_write_error = None
        screen.on_complete()
        assert closed == ["written"]
        assert controller.calls.count(("complete_after_write",)) == 2
        assert controller.write_releases == 1
        screen.deleteLater()

    def test_a_refused_reservation_completes_nothing(self, qapp: Any) -> None:
        from scribe_desktop.session import WriteInFlightError

        screen, controller, closed = self._completing(
            WriteRecordStatus("written", note_matches=True)
        )
        controller.reserve_error = WriteInFlightError("write")
        screen.on_complete()
        assert screen.message_label.text().startswith(
            "Complete failed: " + models.write_line("write_in_flight").rstrip(".")
        )
        assert ("complete_after_write",) not in controller.calls
        assert ("complete",) not in controller.calls
        assert closed == []
        screen.deleteLater()

    def test_a_failed_status_read_completes_nothing(self, qapp: Any) -> None:
        """Fail closed: a record that cannot be asked about neither routes
        to the write's completion nor falls back to the plain one."""
        screen, controller, closed = self._completing(
            RuntimeError("the record could not be read")
        )
        screen.on_complete()
        assert screen.message_label.text().startswith(
            "Complete failed: RuntimeError: the record could not be read"
        )
        assert ("complete",) not in controller.calls
        assert not any(call[0] in self._WRITE_CALLS for call in controller.calls)
        assert closed == []
        screen.deleteLater()

    def test_a_recovered_source_completes_through_its_own_callback(self, qapp: Any) -> None:
        """The live session's ``written`` record never reroutes a recovered
        transcript's Complete (it is not the live session)."""
        screen, controller, closed = self._completing(
            WriteRecordStatus("written", note_matches=True)
        )
        completed: list[str] = []
        screen.show_document(
            _note_document(),
            on_complete=lambda: completed.append("recovered"),
            on_discard=lambda: None,
            can_generate=False,
        )
        screen.on_complete()
        assert completed == ["recovered"]
        assert not any(call[0] == "write_record_status" for call in controller.calls)
        assert not any(call[0] in self._WRITE_CALLS for call in controller.calls)
        assert closed == ["completed"]
        screen.deleteLater()

    def test_complete_refused_while_generating(self, qapp: Any) -> None:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert not screen.complete_button.isEnabled()
        assert not screen.discard_button.isEnabled()
        screen.deleteLater()

    def test_complete_gated_on_note_review_state(self, qapp: Any) -> None:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        # No generation: Complete is available (transcript-only complete).
        assert screen.complete_button.isEnabled()
        screen.set_note_review_state(
            models.NoteReviewState(has_note=True, unconfirmed_proposals=1)
        )
        assert not screen.complete_button.isEnabled()
        screen.set_note_review_state(
            models.NoteReviewState(has_note=True, note_saved=True)
        )
        assert screen.complete_button.isEnabled()
        screen.deleteLater()

    def test_save_note_runs_write_on_gui_thread_and_releases_lease(
        self, qapp: Any, monkeypatch: Any
    ) -> None:
        import threading

        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, result = self._screen(controller)
        writes: list[str] = []

        def fake_write(directory: Path, crypto: Any, note: Any, config: Any) -> Path:
            writes.append(threading.current_thread().name)
            return directory / "note.enc"

        monkeypatch.setattr("scribe_desktop.ui.transcript.write_note", fake_write)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert _process_until(qapp, lambda: screen._generation_result is not None)
        note = finalise_note(
            result.draft,
            [
                ProposalResolution(
                    shown_text_digest=text_digest(p.note_excerpt),
                    confirmation=ConfirmationDecision(
                        proposal_id=p.proposal_id,
                        note_confirmation="declined",
                        decided_at=datetime.now(UTC),
                    ),
                )
                for p in result.draft.note_proposals
            ],
            result.document,
            result.config,
        )
        screen.save_note(note)
        assert writes == [threading.current_thread().name]  # GUI (calling) thread
        assert ("with_generation_custody",) in controller.calls
        assert not screen.is_busy  # lease released after the write
        assert ("end_generation",) in controller.calls
        assert screen._note_committed  # round 36: note.enc is on disk
        screen.deleteLater()

    def test_abandon_note_and_complete_without_one(self, qapp: Any) -> None:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        closed: list[str] = []
        screen.closed.connect(closed.append)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert _process_until(qapp, lambda: screen._generation_result is not None)
        screen.abandon_note_and_complete()
        assert ("complete_without_note",) in controller.calls
        assert not screen.is_busy  # lease released AFTER completion succeeded
        assert closed == ["completed"]
        screen.deleteLater()

    def test_abandon_failure_keeps_the_lease(self, qapp: Any) -> None:
        """Round 35 PR-MED-001: a completion failure must leave the lease and
        review HELD (never an unleased QUEUED session mid-review)."""
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        closed: list[str] = []
        screen.closed.connect(closed.append)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert _process_until(qapp, lambda: screen._generation_result is not None)
        controller.generation_error = SessionActivityError("complete failed")
        with pytest.raises(SessionActivityError):
            screen.abandon_note_and_complete()
        assert screen.is_busy  # lease STILL held
        assert closed == []  # not completed; recovery stays blocked
        screen.deleteLater()

    def test_cancel_note_review_is_non_destructive(self, qapp: Any) -> None:
        """Round 35 PR-MED-003: cancel releases the lease and drops the draft
        WITHOUT completing/discarding/deleting — the transcript, session key,
        and Generate stay available for a fresh generation."""
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert _process_until(qapp, lambda: screen._generation_result is not None)
        assert screen.is_busy
        screen.cancel_note_review()
        assert not screen.is_busy  # lease released
        assert screen._generation_result is None
        # Non-destructive: no completion/discard/delete happened.
        assert ("complete_without_note",) not in controller.calls
        assert ("complete",) not in controller.calls
        assert ("discard",) not in controller.calls
        assert ("end_generation",) in controller.calls  # deliberate lease release
        # Generate is available again (role + profile still confirmed).
        assert screen.generate_button.isEnabled()
        screen.deleteLater()

    def test_committed_note_survives_cancel_of_replacement(self, qapp: Any) -> None:
        """Round 36 PR-MED-002: after Save A, generating then canceling B must
        NOT forget A — `_note_committed` stays True, so the Complete gate's
        has_note agrees with disk and A (ratified at Save) stays completable."""
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        # Simulate a committed note.enc A (a prior successful save).
        screen._note_committed = True
        # Regenerate a replacement B, then cancel it.
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert _process_until(qapp, lambda: screen._generation_result is not None)
        screen.cancel_note_review()
        assert screen._note_committed  # A is NOT forgotten by cancel
        assert screen.complete_button.isEnabled()  # committed, ratified A stays completable
        screen.deleteLater()

    def test_recovered_transcript_has_no_generation_controls(self, qapp: Any) -> None:
        controller = FakeController()
        screen, _result = self._screen(controller)
        # Re-show as a recovered transcript (no generation).
        screen.show_document(
            _note_document(),
            on_complete=lambda: None,
            on_discard=lambda: None,
            can_generate=False,
        )
        assert not screen.generate_box.isVisibleTo(screen)
        screen.deleteLater()

    def test_generate_refused_while_recovery_in_flight(self, qapp: Any) -> None:
        """Round 33 MED-001: a note generation must NOT start while a recovery
        resume is in flight (mutual exclusion — otherwise the resume's
        completion would release the lease mid-generation and swap the view).
        """
        from scribe_desktop.ui.transcript import TranscriptScreen

        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        result = _note_result()
        busy = [True]
        screen = TranscriptScreen(
            controller,
            note_generator_factory=lambda **_k: (lambda _d, _c: result),
            config_loader=_note_config,
            recovery_busy_provider=lambda: busy[0],
        )
        screen.show_document(
            _note_document(),
            on_complete=controller.complete,
            on_discard=controller.discard,
            can_generate=True,
        )
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        # Recovery busy -> Generate disabled AND the click-time guard refuses.
        assert not screen.generate_button.isEnabled()
        screen.generate()
        assert screen._lease is None
        assert ("begin_generation",) not in controller.calls
        # Recovery finishes -> generation is available again.
        busy[0] = False
        screen._update_controls()
        assert screen.generate_button.isEnabled()
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Main window note wiring (Task 7.3).
# ---------------------------------------------------------------------------


class TestNoteWiring:
    def _window(self, tmp_path: Path, controller: FakeController) -> Any:
        return _main_window(tmp_path, controller)

    def _rooted_window(self, tmp_path: Path, controller: FakeController) -> Any:
        """A window whose profile AND config roots are both under `tmp_path`
        (the PR-REG-005 rule: no test may reach the real stores)."""
        return _main_window(tmp_path, controller, profile_root=tmp_path / "profile")

    def test_draft_ready_routes_to_note_tab(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        window = self._window(tmp_path, controller)
        window._on_draft_ready(_note_result())
        assert window.note_screen.current_note() is not None
        assert window.tabs.currentWidget() is window.note_screen
        window.close()

    def test_the_config_root_reaches_both_tabs_and_the_learning_provider(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Practitioner-profile plan Phase 5: the Note tab learns into the
        given config root and reads the learning status from the given profile
        root; the Practitioner tab lists the same config root's phrases."""
        controller = FakeController()
        window = self._rooted_window(tmp_path, controller)
        config_root = tmp_path / "config"
        assert window.note_screen._config_root == config_root
        assert window.practitioner_screen._config_root == config_root
        status = window.note_screen._read_learning_status()
        assert status.enabled is False
        assert status.reason == models.LEARNING_NO_PROFILE_HINT
        assert window.practitioner_screen.recently_learned_list.count() == 0
        append_user_cues(
            [("advice_home_exercise", "wall slide")],
            config_root=config_root,
            learned_at=datetime(2026, 9, 16, tzinfo=UTC),
        )
        window.note_screen.learned_phrases_changed.emit()
        qapp.processEvents()
        assert window.practitioner_screen.recently_learned_list.count() == 1
        assert "wall slide" in window.practitioner_screen.recently_learned_list.item(0).text()
        window.close()

    @windows_only
    def test_a_profile_change_on_the_tab_refreshes_the_microphone_report_line(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 51 MED-001: the microphone screen's voice-profile line is
        re-read when the Practitioner tab reports a profile change
        (`profile_changed` → `refresh_profile_line`), so it never depends on
        the 5 s poll — which no longer reads the profile."""
        from scribe_desktop.practitioner_profile import (
            ConsentRecord,
            PractitionerProfile,
            save_profile,
        )
        from scribe_desktop.speaker_embedding import ONNX_MODEL_ID, SPEAKER_MODEL_SHA256

        # The enrolled line needs the model FILE present; this host may not have it.
        monkeypatch.setattr(models, "speaker_embedder_available", lambda kind=None: True)
        controller = FakeController()
        window = self._rooted_window(tmp_path, controller)
        label = window.microphone_screen.model_status_label
        assert models.PROFILE_NOT_ENROLLED_LINE in label.text()
        now = datetime(2026, 9, 18, 6, 0, tzinfo=UTC)
        save_profile(
            PractitionerProfile(
                model_id=ONNX_MODEL_ID,
                model_sha256=SPEAKER_MODEL_SHA256,
                embedding=(0.6, 0.8),
                embedding_dim=2,
                created_at=now,
                enrolment_speech_seconds=31.0,
                device_name="Mic",
                consent=ConsentRecord(
                    accepted_at=now,
                    consent_text_version=models.CONSENT_TEXT_VERSION,
                    learning_opt_in=False,
                ),
            ),
            root=tmp_path / "profile",
        )
        # The poll alone would not show it (the line is cached) ...
        window.microphone_screen.refresh_model_status()
        assert models.PROFILE_NOT_ENROLLED_LINE in label.text()
        # ... the tab's re-read does, through the signal.
        window.practitioner_screen.refresh_profile_state()
        qapp.processEvents()
        assert "Voice profile: enrolled 2026-09-18" in label.text()
        window.close()

    def test_a_review_started_through_the_window_stays_off_the_real_stores(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        window = self._rooted_window(tmp_path, controller)
        window._on_draft_ready(_note_result())  # reads the learning status
        assert window.note_screen.current_note() is not None
        assert window.note_screen.learning_label.text() == models.LEARNING_NO_PROFILE_HINT
        assert not (tmp_path / "config").exists()  # nothing written by a review
        window.note_screen.clear()
        window.close()

    def test_new_live_transcript_clears_stale_note(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        window = self._window(tmp_path, controller)
        window._on_draft_ready(_note_result())
        assert window.note_screen.current_note() is not None
        window.session_screen.transcript_ready.emit(_note_document())
        qapp.processEvents()
        assert window.note_screen.current_note() is None  # cleared
        window.close()

    def test_generation_active_blocks_recovery(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        window = self._window(tmp_path, controller)
        window._on_generation_active(True)
        assert window.recovery_screen._generation_blocked is True
        window._on_generation_active(False)
        assert window.recovery_screen._generation_blocked is False
        window.close()

    def test_new_generation_invalidates_stale_note_tab(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 36 PR-MED-001: a new generation synchronously clears the stale
        (post-Save) Note tab, so its delete-and-complete action can never route
        through the new generation's lease."""
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        window = self._window(tmp_path, controller)
        window._on_draft_ready(_note_result())
        assert window.note_screen.current_note() is not None
        assert window.note_screen.abandon_button.isEnabled()
        # A new generation starts -> the stale Note tab is invalidated.
        window._on_generation_active(True)
        assert window.note_screen.current_note() is None  # cleared
        assert not window.note_screen.abandon_button.isEnabled()  # no stale action
        window.close()

    def test_close_refused_while_note_under_review(self, qapp: Any, tmp_path: Path) -> None:
        from PySide6.QtGui import QCloseEvent

        controller = FakeController()
        window = self._window(tmp_path, controller)
        window._on_draft_ready(_note_result())  # note under review, not saved
        assert window.note_screen.is_busy
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        window.note_screen.clear()
        event2 = QCloseEvent()
        window.closeEvent(event2)
        assert event2.isAccepted()

    # --- Task 9.1a: the recorded copy decision, driven through the window ---

    def _generate_through_window(
        self, qapp: Any, tmp_path: Path
    ) -> tuple[Any, FakeController]:
        """Reach a draft under review the way the app does: a live transcript
        arrives, the clinician confirms role and profile, Generate composes on
        a worker thread under the controller's lease, and ``draft_ready``
        routes the result through ``MainWindow._on_draft_ready`` - the one
        call site that reads ``models.COPY_TO_CLINIKO_ENABLED``, at call time.

        The window builds its Transcript screen with the module DEFAULT config
        loader and generator factory (both bound as function defaults, so a
        module-level monkeypatch cannot reach them, and the default generator
        reads a transcript from disk that the fake controller's ``unused``
        directory does not hold). The two instance seams below stand in the
        fixture config and an inert generator - the same shapes
        ``TestTranscriptGeneration._screen`` passes at construction."""
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        window = self._window(tmp_path, controller)
        result = _note_result()
        window.transcript_screen._config_loader = _note_config
        window.transcript_screen._note_generator_factory = (
            lambda **_kwargs: lambda _directory, _crypto: result
        )
        window.session_screen.transcript_ready.emit(_note_document())
        qapp.processEvents()
        window.transcript_screen.set_role(SPEAKER_2)
        window.transcript_screen.set_profile("clinic-a")
        window.transcript_screen.generate()
        assert window.transcript_screen.is_busy  # the lease generate() holds
        assert _process_until(qapp, lambda: window.note_screen.current_note() is not None)
        assert window.tabs.currentWidget() is window.note_screen
        return window, controller

    def _rooted_review_with_queue(self, qapp: Any, tmp_path: Path) -> tuple[Any, Any]:
        """Task 5.6: a review reached through the window's own wiring (the
        ``_generate_through_window`` route over a ROOTED window so a Save can
        never touch the real stores), learning on, and ONE of the confirmed
        clinician's unrouted lines added — one phrase queued. Returns the
        window and the added line's choice."""
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        window = self._rooted_window(tmp_path, controller)
        result = _note_result()
        window.transcript_screen._config_loader = _note_config
        window.transcript_screen._note_generator_factory = (
            lambda **_kwargs: lambda _directory, _crypto: result
        )
        window.session_screen.transcript_ready.emit(_note_document())
        qapp.processEvents()
        window.transcript_screen.set_role(SPEAKER_2)
        window.transcript_screen.set_profile("clinic-a")
        window.transcript_screen.generate()
        assert _process_until(qapp, lambda: window.note_screen.current_note() is not None)
        note_screen = window.note_screen
        note_screen._learning_status_provider = lambda: models.LearningStatus(True, None)
        note_screen._refresh_learning_status()
        document = note_screen._document
        choice = next(
            item
            for item in note_screen.eligible_utterances()
            if document.transcript_segments[item.segment_index].speaker == SPEAKER_2
        )
        assert note_screen.add_line(choice.segment_index, choice.allowed_sections[0]) is True
        assert note_screen.queued_learning_count() == 1
        return window, choice

    def test_cancel_with_a_queued_phrase_says_what_was_lost(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Task 5.6, surface 1: Cancel review and regenerate — the Transcript
        screen (where the practitioner lands) says the queued phrase was not
        learned and names Save note."""
        window, _choice = self._rooted_review_with_queue(qapp, tmp_path)
        window.note_screen.cancel_review()
        assert window.tabs.currentWidget() is window.transcript_screen
        message = window.transcript_screen.message_label.text()
        # Round 42 LOW-001: Cancel's own line first, never the stale
        # "Note generated" line under the appended sentence.
        assert message.startswith("Note review cancelled")
        assert "Note generated" not in message
        assert message.endswith(models.unlearned_on_exit_line(1))
        assert "1 queued phrase was not learned" in message
        assert "only Save note on the Note tab learns them" in message
        assert window.note_screen.queued_learning_count() == 0  # the tab cleared after
        assert not (tmp_path / "config").exists()  # nothing was written
        window.close()

    def test_delete_and_complete_with_a_queued_phrase_says_what_was_lost(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Task 5.6, surface 2: Delete note and complete without one — the
        sentence follows the completion message."""
        window, _choice = self._rooted_review_with_queue(qapp, tmp_path)
        window.note_screen.abandon()
        # Peer round 44 PR-MED-026: the sentence is VISIBLE — the window stays
        # on the Transcript screen instead of moving to the Session screen.
        assert window.tabs.currentWidget() is window.transcript_screen
        assert window.transcript_screen.message_label.text() == (
            "Session completed without a note (transcript verified, key destroyed). "
            + models.unlearned_on_exit_line(1)
        )
        assert window.note_screen.current_note() is None
        assert not (tmp_path / "config").exists()
        window.close()

    def test_discard_with_a_queued_phrase_says_what_was_lost(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Task 5.6, surface 3: Discard over a live review (the practitioner
        folded it in) — the sentence follows the discard message."""
        window, _choice = self._rooted_review_with_queue(qapp, tmp_path)
        window.transcript_screen.on_discard()
        assert window.tabs.currentWidget() is window.transcript_screen  # round 44 PR-MED-026
        assert window.transcript_screen.message_label.text() == (
            "Session discarded (audio cryptographically deleted). "
            + models.unlearned_on_exit_line(1)
        )
        assert window.note_screen.current_note() is None
        window.close()

    def test_two_queued_phrases_are_counted(self, qapp: Any, tmp_path: Path) -> None:
        """The count is the live queue's: an add AND a move (the routed
        diagnosis line, re-routed) make two, and the sentence pluralises."""
        window, _first = self._rooted_review_with_queue(qapp, tmp_path)
        note_screen = window.note_screen
        line = _routed_line(note_screen, _DIAGNOSIS_INDEX)
        assert note_screen.move_line(line.assertion_id, line.allowed_sections[0]) is True
        assert note_screen.queued_learning_count() == 2
        note_screen.cancel_review()
        assert window.transcript_screen.message_label.text().endswith(
            models.unlearned_on_exit_line(2)
        )
        assert "2 queued phrases were not learned" in models.unlearned_on_exit_line(2)
        window.close()

    def test_exits_with_an_empty_queue_report_nothing_about_learning(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Each exit with nothing queued shows only its own message; the
        queue read is the LIVE one, so an undone add reports nothing."""
        window, choice = self._rooted_review_with_queue(qapp, tmp_path)
        assert window.note_screen.undo_line(manual_assertion_id(choice.segment_index)) is True
        assert window.note_screen.queued_learning_count() == 0
        window.note_screen.cancel_review()
        assert "not learned" not in window.transcript_screen.message_label.text()
        window.close()

        window, _controller = self._generate_through_window(qapp, tmp_path)
        window.note_screen.abandon()
        message = window.transcript_screen.message_label.text()
        assert message == (
            "Session completed without a note (transcript verified, key destroyed)."
        )
        # Round 44 PR-MED-026: an empty-queue close keeps the pre-existing
        # landing on the Session screen.
        assert window.tabs.currentWidget() is window.session_screen
        window.close()

        window, _controller = self._generate_through_window(qapp, tmp_path)
        window.transcript_screen.on_discard()
        assert window.transcript_screen.message_label.text() == (
            "Session discarded (audio cryptographically deleted)."
        )
        assert window.tabs.currentWidget() is window.session_screen
        window.close()

    def test_a_saved_note_then_cancel_reports_nothing(
        self, qapp: Any, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Save note writes the queue (and empties it); a later Cancel has
        nothing to report."""
        window, _choice = self._rooted_review_with_queue(qapp, tmp_path)
        self._fake_write_note(monkeypatch)
        note_screen = window.note_screen
        for proposal in note_screen._draft.note_proposals:
            note_screen.confirm_proposal(proposal.proposal_id)
        note_screen._acknowledge_all()
        note_screen.save()
        assert note_screen.queued_learning_count() == 0
        assert "Learned 1" in note_screen.edit_status_label.text()
        assert (tmp_path / "config" / SECTION_CUES_FILENAME).exists()
        note_screen.cancel_review()
        assert "not learned" not in window.transcript_screen.message_label.text()
        window.close()

    def _fake_write_note(self, monkeypatch: Any) -> list[str]:
        """Fake the on-disk note write so a caller's ``NoteScreen.save`` can
        travel the window's own route - ``MainWindow._on_note_save`` ->
        ``TranscriptScreen.save_note`` under the held lease - without touching
        disk; returns the thread names the fake saw."""
        import threading

        writes: list[str] = []

        def fake_write(directory: Path, crypto: Any, note: Any, config: Any) -> Path:
            writes.append(threading.current_thread().name)
            return directory / "note.enc"

        monkeypatch.setattr("scribe_desktop.ui.transcript.write_note", fake_write)
        return writes

    def test_recorded_fail_keeps_copy_hidden_through_the_window(
        self, qapp: Any, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Task 9.1a, the FAIL outcome — now the flag-OFF outcome (copy
        withdrawn by a recorded practitioner decision, D12): with the recorded
        decision False, the Note tab reached through the window's own wiring
        shows no copy affordance at all - the button is hidden AND disabled
        and the note body is display-only - and full ratification changes
        nothing. The transcript panel is display-only as always."""
        from PySide6.QtCore import Qt

        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", False)
        window, _controller = self._generate_through_window(qapp, tmp_path)
        note_screen = window.note_screen
        no_interaction = Qt.TextInteractionFlag.NoTextInteraction
        assert note_screen.copy_button.isHidden()
        assert not note_screen.copy_button.isEnabled()
        assert note_screen.note_body.textInteractionFlags() == no_interaction
        assert note_screen.transcript_view.textInteractionFlags() == no_interaction
        # Ratify fully: confirm all -> acknowledge all -> save through the window.
        writes = self._fake_write_note(monkeypatch)
        for proposal in note_screen._draft.note_proposals:
            note_screen.confirm_proposal(proposal.proposal_id)
        note_screen._acknowledge_all()
        note_screen.save()
        assert len(writes) == 1  # the save went through the window's route
        assert not window.transcript_screen.is_busy  # lease released
        assert note_screen.copy_button.isHidden()
        assert not note_screen.copy_button.isEnabled()
        assert note_screen.note_body.textInteractionFlags() == no_interaction
        assert note_screen.transcript_view.textInteractionFlags() == no_interaction
        window.close()

    def test_recorded_pass_enables_copy_only_for_a_ratified_note_through_the_window(
        self, qapp: Any, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Task 9.1a, the PASS outcome — now the flag-ON outcome, the shipped
        state since 2026-09-27 (D12): with the recorded decision True, the
        Note tab reached through the window's own wiring SHOWS the copy
        button but keeps it disabled - and the note body display-only - while
        any proposal is pending, while a review warning is unacknowledged, and
        until the note is saved through the window (which needs the lease
        ``generate()`` holds). Only then is the button enabled and the body
        selectable. The transcript panel is display-only under this outcome
        too."""
        import threading

        from PySide6.QtCore import Qt

        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", True)
        window, controller = self._generate_through_window(qapp, tmp_path)
        note_screen = window.note_screen
        no_interaction = Qt.TextInteractionFlag.NoTextInteraction
        # Flag on: shown, but proposals are pending -> disabled, display-only.
        assert not note_screen.copy_button.isHidden()
        assert not note_screen.copy_button.isEnabled()
        assert note_screen.note_body.textInteractionFlags() == no_interaction
        assert note_screen.transcript_view.textInteractionFlags() == no_interaction
        writes = self._fake_write_note(monkeypatch)
        for proposal in note_screen._draft.note_proposals:
            note_screen.confirm_proposal(proposal.proposal_id)
        assert not note_screen.copy_button.isEnabled()  # review warnings unacknowledged
        assert note_screen.note_body.textInteractionFlags() == no_interaction
        note_screen._acknowledge_all()
        assert not note_screen.copy_button.isEnabled()  # not yet saved
        assert note_screen.note_body.textInteractionFlags() == no_interaction
        note_screen.save()  # -> _on_note_save -> save_note under the held lease
        assert writes == [threading.current_thread().name]  # GUI thread
        assert ("with_generation_custody",) in controller.calls
        assert not window.transcript_screen.is_busy  # lease released after the write
        assert not note_screen.copy_button.isHidden()
        assert note_screen.copy_button.isEnabled()  # fully ratified
        flags = note_screen.note_body.textInteractionFlags()
        assert flags & Qt.TextInteractionFlag.TextSelectableByMouse
        assert flags & Qt.TextInteractionFlag.TextSelectableByKeyboard
        # The transcript panels stay display-only whatever the decision.
        assert note_screen.transcript_view.textInteractionFlags() == no_interaction
        assert window.transcript_screen.transcript_view.textInteractionFlags() == no_interaction
        window.close()

    # --- Round 70 PR-HIGH-002 (verified MED): the clipboard contract itself ---

    def _fake_clipboard(
        self,
        monkeypatch: Any,
        mimes: list[Any] | None = None,
        native_keys: list[Any] | None = None,
    ) -> list[str]:
        """Stand in for ``QApplication.clipboard()`` inside ``ui.note`` so the
        copy action is observable WITHOUT touching the real Windows clipboard
        (history / cloud sync would retain even fixture text); returns the
        text of every placement on EITHER route — ``setText`` or, since Task
        8.2, ``setMimeData`` (whose ``QMimeData`` is also appended to
        ``mimes`` when given). ``ui.note`` uses ``QApplication`` for nothing
        else, so the module name is replaced rather than the Qt class
        patched.

        Round 46 PR-LOW-270: that stub cannot see Qt's NATIVE copy, so the
        tests must never reach it. The platform must be ``offscreen`` (whose
        clipboard is Qt's in-process one, never the Windows clipboard), and
        ``QPlainTextEdit``'s own ``keyPressEvent`` / ``copy`` are replaced by
        guards that fail the test on any Copy key or copy call BEFORE native
        Qt runs — so a panel whose interception regressed fails here instead
        of writing a clipboard. Every other key passes through to Qt (its
        key is appended to ``native_keys`` when given)."""
        from PySide6.QtGui import QGuiApplication, QKeySequence
        from PySide6.QtWidgets import QPlainTextEdit

        from scribe_desktop.ui import note as note_module

        assert QGuiApplication.platformName() == "offscreen", (
            "the copy tests run only on the offscreen platform; unset QT_QPA_PLATFORM"
        )
        native_key_press = QPlainTextEdit.keyPressEvent

        def _refuse_native_copy_key(widget: Any, event: Any) -> None:
            if event.matches(QKeySequence.StandardKey.Copy):
                raise AssertionError("a Copy key reached Qt's native copy")
            if native_keys is not None:
                native_keys.append(event.key())
            native_key_press(widget, event)

        def _refuse_native_copy(widget: Any) -> None:
            raise AssertionError("Qt's native copy was called")

        monkeypatch.setattr(QPlainTextEdit, "keyPressEvent", _refuse_native_copy_key)
        monkeypatch.setattr(QPlainTextEdit, "copy", _refuse_native_copy)

        payloads: list[str] = []

        class _Clipboard:
            def setText(self, text: str) -> None:  # noqa: N802 - Qt spelling
                payloads.append(text)

            def setMimeData(self, mime: Any) -> None:  # noqa: N802 - Qt spelling
                payloads.append(mime.text())
                if mimes is not None:
                    mimes.append(mime)

        clipboard = _Clipboard()

        class _StubApplication:
            @staticmethod
            def clipboard() -> _Clipboard:
                return clipboard

        monkeypatch.setattr(note_module, "QApplication", _StubApplication)
        return payloads

    @staticmethod
    def _copy_key_event(combination: Any = None) -> Any:
        """A key press of Copy (Ctrl+C unless another binding is given)."""
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent

        if combination is None:
            return QKeyEvent(
                QEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier
            )
        return QKeyEvent(
            QEvent.Type.KeyPress, combination.key(), combination.keyboardModifiers()
        )

    @staticmethod
    def _menu_copy_action(note_body: Any) -> Any:
        """The Copy entry of the note panel's own context menu (Task 8.2)."""
        menu = note_body.build_context_menu()
        return next(a for a in menu.actions() if a.text().startswith("&Copy"))

    @classmethod
    def _attempt_copy(cls, note_screen: Any) -> None:
        """Every copy route: the button (inert while disabled or hidden), a
        direct ``_copy_note`` call (the click-time re-check must refuse), and —
        since Task 8.2 — a copy of the note panel's WHOLE selection by the
        keyboard, by its context menu's Copy and by a direct call (each
        re-checks ratification, even over a selection made in code)."""
        note_screen.copy_button.click()
        note_screen._copy_note()
        body = note_screen.note_body
        body.selectAll()
        body.keyPressEvent(cls._copy_key_event())
        cls._menu_copy_action(body).trigger()
        body.copy_selection()

    def test_copy_never_reaches_the_clipboard_under_a_recorded_fail(
        self, qapp: Any, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Round 70 PR-HIGH-002 (FAIL outcome, i.e. the flag off): nothing reaches the clipboard on
        either route - the hidden button's click or a direct ``_copy_note``
        call - at any point of the review, full ratification included. The
        presentation pins above say the affordance is absent; this pins that
        the ACTION is inert."""
        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", False)
        window, _controller = self._generate_through_window(qapp, tmp_path)
        note_screen = window.note_screen
        payloads = self._fake_clipboard(monkeypatch)
        self._attempt_copy(note_screen)
        self._fake_write_note(monkeypatch)
        for proposal in note_screen._draft.note_proposals:
            note_screen.confirm_proposal(proposal.proposal_id)
        note_screen._acknowledge_all()
        note_screen.save()
        self._attempt_copy(note_screen)
        assert payloads == []
        window.close()

    def test_copy_delivers_exactly_the_ratified_note_under_a_recorded_pass(
        self, qapp: Any, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Round 70 PR-HIGH-002 (PASS outcome, i.e. the flag on): the clipboard receives nothing
        while a proposal is pending, a review warning is unacknowledged, or the
        note is unsaved - on the button route AND the direct-call route - and
        once ratified the Copy click delivers EXACTLY ``format_note_body`` of
        the note under review — since the note-learning plan's Task 3.2 the
        ONE rendering path under the note's own style, which for a window
        with no settings file is the shipped default ``clean`` — and every
        line is a section title or the confirmed text of one of the ratified
        note's own assertions (a pre-filled line carrying its D5 mark), so no
        raw transcript line the note does not hold can ride along."""
        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", True)
        window, _controller = self._generate_through_window(qapp, tmp_path)
        note_screen = window.note_screen
        payloads = self._fake_clipboard(monkeypatch)
        self._attempt_copy(note_screen)
        assert payloads == []  # proposals pending
        self._fake_write_note(monkeypatch)
        proposals = list(note_screen._draft.note_proposals)
        assert proposals  # the fixture's autofill rule must have fired
        for proposal in proposals:
            note_screen.confirm_proposal(proposal.proposal_id)
        self._attempt_copy(note_screen)
        assert payloads == []  # review warnings unacknowledged
        note_screen._acknowledge_all()
        self._attempt_copy(note_screen)
        assert payloads == []  # not yet saved
        note_screen.save()
        note_screen.copy_button.click()
        note = note_screen.current_note()
        assert note is not None
        assert note.style == "clean"  # the shipped default reached the note
        expected = models.format_note_body(note)
        assert expected == render_note(note, "clean")
        assert payloads == [expected]
        assert "Ice pack use explained." in expected  # the ratified proposal
        titles = set(SECTION_TITLES.values())
        ratified: set[str] = set()
        for section in note.note_sections:
            for assertion in section.note_assertions:
                ratified.add(assertion.text)
                if models.is_prefilled(assertion):
                    ratified.add(f"{assertion.text}  [{models.PREFILLED_MARK}]")
        for line in expected.splitlines():
            if not line:
                continue
            assert line in titles or line in ratified, line
        note_screen._copy_note()
        assert payloads == [expected, expected]  # the direct route agrees
        window.close()

    def test_copy_keeps_the_note_out_of_clipboard_history_and_sync(
        self, qapp: Any, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Task 8.2: the ratified note is placed as ONE ``QMimeData`` whose text
        is exactly ``format_note_body`` (what ``setText`` placed before) and
        which carries the three registered Windows formats with exactly their
        payloads — nothing more, and nothing before ratification."""
        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", True)
        window, _controller = self._generate_through_window(qapp, tmp_path)
        note_screen = window.note_screen
        mimes: list[Any] = []
        payloads = self._fake_clipboard(monkeypatch, mimes)
        self._fake_write_note(monkeypatch)
        for proposal in note_screen._draft.note_proposals:
            note_screen.confirm_proposal(proposal.proposal_id)
        note_screen._acknowledge_all()
        self._attempt_copy(note_screen)
        assert payloads == [] and mimes == []  # not yet saved
        note_screen.save()
        note_screen.copy_button.click()
        note = note_screen.current_note()
        assert note is not None
        (mime,) = mimes
        assert mime.text() == models.format_note_body(note)
        zero = b"\x00\x00\x00\x00"
        names = (
            "ExcludeClipboardContentFromMonitorProcessing",
            "CanIncludeInClipboardHistory",
            "CanUploadToCloudClipboard",
        )
        expected = {f'application/x-qt-windows-mime;value="{name}"': zero for name in names}
        assert set(mime.formats()) == {"text/plain", *expected}
        for mime_type, payload in expected.items():
            assert bytes(mime.data(mime_type).data()) == payload, mime_type
        window.close()

    @staticmethod
    def _assert_note_mime(mime: Any, text: str) -> None:
        """Task 8.2: exactly the text plus the three formats, each 4 zero bytes."""
        zero = b"\x00\x00\x00\x00"
        names = (
            "ExcludeClipboardContentFromMonitorProcessing",
            "CanIncludeInClipboardHistory",
            "CanUploadToCloudClipboard",
        )
        expected = {f'application/x-qt-windows-mime;value="{name}"': zero for name in names}
        assert mime.text() == text
        assert set(mime.formats()) == {"text/plain", *expected}
        for mime_type, payload in expected.items():
            assert bytes(mime.data(mime_type).data()) == payload, mime_type

    def _ratified_note_screen(
        self, qapp: Any, tmp_path: Path, monkeypatch: Any, mimes: list[Any]
    ) -> tuple[Any, Any, list[str]]:
        """A window whose note is fully ratified and saved, with the fake
        clipboard installed (flag on)."""
        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", True)
        window, _controller = self._generate_through_window(qapp, tmp_path)
        note_screen = window.note_screen
        payloads = self._fake_clipboard(monkeypatch, mimes)
        self._fake_write_note(monkeypatch)
        for proposal in note_screen._draft.note_proposals:
            note_screen.confirm_proposal(proposal.proposal_id)
        note_screen._acknowledge_all()
        note_screen.save()
        return window, note_screen, payloads

    def test_a_keyboard_copy_of_the_selection_carries_the_formats(
        self, qapp: Any, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Task 8.2 (the selection route): every binding of the platform's
        Copy key (Ctrl+C, and Ctrl+Insert where the scheme has it) places the
        selection exactly as Qt's own copy renders it — whole or a part that
        spans a line break — with the three formats; Qt's own copy never runs."""
        from PySide6.QtGui import QKeySequence, QTextCursor

        mimes: list[Any] = []
        window, note_screen, payloads = self._ratified_note_screen(
            qapp, tmp_path, monkeypatch, mimes
        )
        body = note_screen.note_body
        note = note_screen.current_note()
        assert note is not None
        bindings = QKeySequence.keyBindings(QKeySequence.StandardKey.Copy)
        assert any(seq.toString() == "Ctrl+C" for seq in bindings)
        body.selectAll()
        for sequence in bindings:
            body.keyPressEvent(self._copy_key_event(sequence[0]))
        assert len(mimes) == len(bindings)
        for mime in mimes:
            self._assert_note_mime(mime, models.format_note_body(note))
        text = body.toPlainText()
        start = max(0, text.index("\n") - 3)  # just before the first line break
        end = min(len(text), start + 10)
        assert "\n" in text[start:end]
        cursor = body.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        body.setTextCursor(cursor)
        mimes.clear()
        body.keyPressEvent(self._copy_key_event())
        (mime,) = mimes
        self._assert_note_mime(mime, text[start:end])
        assert cursor.selection().toPlainText() == text[start:end]  # Qt's own rendering
        assert payloads[-1] == text[start:end]
        window.close()

    def test_the_context_menu_copy_carries_the_formats(
        self, qapp: Any, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Task 8.2: the panel's context menu is its own (Qt's Copy would
        bypass the formats); its Copy places the selection with the formats,
        and a right-click opens exactly that menu."""
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QContextMenuEvent

        mimes: list[Any] = []
        window, note_screen, _payloads = self._ratified_note_screen(
            qapp, tmp_path, monkeypatch, mimes
        )
        body = note_screen.note_body
        note = note_screen.current_note()
        assert note is not None
        body.selectAll()
        menu = body.build_context_menu()
        labels = [action.text().split("\t")[0] for action in menu.actions()]
        assert labels == ["&Copy", "Select &All"]
        assert all(action.isEnabled() for action in menu.actions())
        self._menu_copy_action(body).trigger()
        (mime,) = mimes
        self._assert_note_mime(mime, models.format_note_body(note))

        opened: list[Any] = []

        class _Menu:
            def exec(self, position: Any) -> None:
                opened.append(position)

            def deleteLater(self) -> None:  # noqa: N802 - Qt spelling
                opened.append("deleted")

        monkeypatch.setattr(body, "build_context_menu", _Menu)
        body.contextMenuEvent(
            QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(1, 1), QPoint(5, 5))
        )
        assert opened == [QPoint(5, 5), "deleted"]
        window.close()

    def test_an_unratified_panel_places_nothing_even_with_a_selection(
        self, qapp: Any, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Task 8.2: before ratification the panel is display-only and every
        selection route — keyboard, context menu, direct call — places
        nothing, even over a selection made in code; the menu's Copy and
        Select All are disabled."""
        from PySide6.QtCore import Qt

        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", True)
        window, _controller = self._generate_through_window(qapp, tmp_path)
        note_screen = window.note_screen
        mimes: list[Any] = []
        payloads = self._fake_clipboard(monkeypatch, mimes)
        body = note_screen.note_body
        assert body.textInteractionFlags() == Qt.TextInteractionFlag.NoTextInteraction
        body.selectAll()
        assert body.textCursor().hasSelection()
        assert not any(action.isEnabled() for action in body.build_context_menu().actions())
        body.keyPressEvent(self._copy_key_event())
        self._menu_copy_action(body).trigger()
        assert body.copy_selection() is False
        assert payloads == [] and mimes == []
        window.close()

    def test_the_native_copy_guard_passes_other_keys_to_qt(
        self, qapp: Any, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Round 46 PR-LOW-270: the guard is not vacuous — a non-Copy key on
        the note panel reaches Qt's own handler through it, while the panel's
        Copy key is intercepted and never gets there."""
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent

        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", True)
        window, _controller = self._generate_through_window(qapp, tmp_path)
        native_keys: list[Any] = []
        payloads = self._fake_clipboard(monkeypatch, native_keys=native_keys)
        body = window.note_screen.note_body
        key_a = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
        body.keyPressEvent(key_a)
        assert native_keys == [Qt.Key.Key_A]
        body.selectAll()
        body.keyPressEvent(self._copy_key_event())
        assert native_keys == [Qt.Key.Key_A]  # the panel's own Copy took it
        assert payloads == []  # and refused it: the note is not ratified
        window.close()

    def test_an_unintercepted_copy_key_fails_before_any_clipboard(
        self, qapp: Any, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Round 46 PR-LOW-270: a note panel whose Copy interception
        regressed (its ``keyPressEvent`` removed, so Qt's own handler gets the
        key) fails the test before Qt's native copy runs, with nothing placed
        on the fake clipboard; a direct native ``copy()`` fails the same way."""
        from scribe_desktop.ui import note as note_module

        mimes: list[Any] = []
        window, note_screen, payloads = self._ratified_note_screen(
            qapp, tmp_path, monkeypatch, mimes
        )
        body = note_screen.note_body
        assert isinstance(body, note_module._NotePanel)
        monkeypatch.delattr(note_module._NotePanel, "keyPressEvent")
        body.selectAll()
        with pytest.raises(AssertionError, match="reached Qt's native copy"):
            body.keyPressEvent(self._copy_key_event())
        with pytest.raises(AssertionError, match="native copy was called"):
            body.copy()
        assert payloads == [] and mimes == []
        window.close()


# ---------------------------------------------------------------------------
# Transcript screen auto-confirm from the voice profile (practitioner-profile
# plan Task 2.3, D4 / D2).
# ---------------------------------------------------------------------------


def _attributed_document(
    enrolled: str = SPEAKER_2, similarity: float = 0.83
) -> TranscriptDocument:
    return _note_document().model_copy(
        update={
            "enrolled_speaker": enrolled,
            "enrolment_similarity": similarity,
            "speaker_model_id": "mock-speaker-embedder-v1",
        }
    )


def _readiness(present: bool, reason: str | None = None) -> Callable[[], Any]:
    readiness = models.AttributionReadiness(profile_present=present, profile=None, reason=reason)
    return lambda: readiness


class TestTranscriptAutoConfirm:
    def _screen(
        self,
        document: TranscriptDocument,
        *,
        readiness: Callable[[], Any] | None = None,
        can_generate: bool = True,
        config_loader: Callable[[], Any] = _note_config,
    ) -> tuple[Any, FakeController, list[dict[str, Any]]]:
        from scribe_desktop.ui.transcript import TranscriptScreen

        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        result = _note_result()
        factory_kwargs: list[dict[str, Any]] = []

        def factory(**kwargs: Any) -> Callable[[Path, Any], models.NoteGenerationResult]:
            factory_kwargs.append(kwargs)
            return lambda _directory, _crypto: result

        screen = TranscriptScreen(
            controller,
            note_generator_factory=factory,
            config_loader=config_loader,
            attribution_readiness_provider=readiness or _readiness(False),
        )
        screen.show_document(
            document,
            on_complete=controller.complete,
            on_discard=controller.discard,
            can_generate=can_generate,
        )
        return screen, controller, factory_kwargs

    def test_enrolled_speaker_is_prechecked_with_the_confirmation_line(self, qapp: Any) -> None:
        screen, _controller, _kwargs = self._screen(_attributed_document(SPEAKER_2, 0.83))
        assert screen.role_auto_confirmed
        assert screen._selected_role() == SPEAKER_2
        assert screen.attribution_label.isVisibleTo(screen)
        assert screen.attribution_label.text() == (
            "Clinician: confirmed from your voice profile (similarity 0.83) -"
        )
        assert screen.change_role_button.isVisibleTo(screen)
        assert screen.change_role_button.text() == "change"
        # The manual radios are replaced by the line (not merely pre-checked).
        assert not screen.role_prompt_label.isVisibleTo(screen)
        assert all(not radio.isVisibleTo(screen) for radio in screen._role_buttons.values())
        # PR-MED-009: the auto-confirm satisfies the ROLE predicate only.
        assert not screen.generate_button.isEnabled()
        screen.set_profile("clinic-a")
        assert screen.generate_button.isEnabled()
        screen.deleteLater()

    def test_the_similarity_is_shown_raw_even_when_negative(self, qapp: Any) -> None:
        screen, _controller, _kwargs = self._screen(_attributed_document(SPEAKER_1, -0.25))
        assert "(similarity -0.25)" in screen.attribution_label.text()
        assert screen._selected_role() == SPEAKER_1
        screen.deleteLater()

    def test_change_reverts_to_the_manual_radios_with_the_suggestion(self, qapp: Any) -> None:
        from scribe_desktop.note import speaker_role

        document = _attributed_document(SPEAKER_2, 0.83)
        screen, _controller, _kwargs = self._screen(document)
        screen.set_profile("clinic-a")
        assert screen.generate_button.isEnabled()
        screen.change_role_button.click()
        assert not screen.role_auto_confirmed
        assert screen._selected_role() is None  # un-checked: the choice is explicit again
        assert not screen.generate_button.isEnabled()  # role predicate no longer satisfied
        assert not screen.attribution_label.isVisibleTo(screen)
        assert not screen.change_role_button.isVisibleTo(screen)
        assert screen.role_prompt_label.isVisibleTo(screen)
        assert all(radio.isVisibleTo(screen) for radio in screen._role_buttons.values())
        suggested = speaker_role(document).preselected_clinician_speaker
        assert suggested is not None
        assert " (suggested)" in screen._role_buttons[suggested].text()
        marked = [s for s, r in screen._role_buttons.items() if " (suggested)" in r.text()]
        assert marked == [suggested]
        screen.set_role(SPEAKER_1)
        assert screen.generate_button.isEnabled()
        screen.change_role()  # idempotent once on the manual path
        assert screen._selected_role() == SPEAKER_1
        screen.deleteLater()

    def test_generate_reads_the_prechecked_role_as_the_confirmed_clinician(
        self, qapp: Any
    ) -> None:
        screen, controller, factory_kwargs = self._screen(_attributed_document(SPEAKER_2, 0.83))
        screen.set_profile("clinic-a")
        drafts: list[Any] = []
        screen.draft_ready.connect(drafts.append)
        screen.generate()
        assert _process_until(qapp, lambda: bool(drafts))
        assert factory_kwargs[-1]["clinician_speaker"] == SPEAKER_2
        assert ("begin_generation",) in controller.calls
        screen.deleteLater()

    def test_manual_path_when_the_document_carries_no_attribution(self, qapp: Any) -> None:
        screen, _controller, _kwargs = self._screen(_note_document(), readiness=_readiness(False))
        assert not screen.role_auto_confirmed
        assert screen._selected_role() is None
        assert not screen.attribution_label.isVisibleTo(screen)
        assert not screen.change_role_button.isVisibleTo(screen)
        assert screen.role_prompt_label.isVisibleTo(screen)
        assert all(radio.isVisibleTo(screen) for radio in screen._role_buttons.values())
        screen.deleteLater()

    @pytest.mark.parametrize(
        "reason",
        [
            models.SPEAKER_MODEL_MISSING_REASON,
            models.PROFILE_REENROL_REASON,
            models.PROFILE_UNUSABLE_REASON.format(reason="authentication"),
        ],
    )
    def test_the_fallback_is_named_when_a_profile_exists_but_was_not_applied(
        self, qapp: Any, reason: str
    ) -> None:
        screen, _controller, _kwargs = self._screen(
            _note_document(), readiness=_readiness(True, reason)
        )
        # The status line lives OUTSIDE the generation group (PR-HIGH-004).
        assert screen.attribution_status_label.isVisibleTo(screen)
        assert screen.attribution_status_label.text() == reason
        assert not screen.attribution_label.isVisibleTo(screen)  # no confirmation line
        assert not screen.change_role_button.isVisibleTo(screen)  # nothing to change
        assert screen._selected_role() is None  # still the manual path
        assert all(radio.isVisibleTo(screen) for radio in screen._role_buttons.values())
        screen.deleteLater()

    def test_a_usable_profile_with_no_attribution_says_attribution_did_not_run(
        self, qapp: Any
    ) -> None:
        screen, _controller, _kwargs = self._screen(_note_document(), readiness=_readiness(True))
        assert screen.attribution_status_label.isVisibleTo(screen)
        assert screen.attribution_status_label.text() == models.ATTRIBUTION_DID_NOT_RUN_REASON
        screen.deleteLater()

    def test_the_recovered_view_still_names_the_fallback(self, qapp: Any) -> None:
        """PR-HIGH-004: the recovered path applies the profile too, has no
        generation controls by design, and must still show the D2 line."""
        reason = models.PROFILE_REENROL_REASON
        screen, _controller, _kwargs = self._screen(
            _note_document(), readiness=_readiness(True, reason), can_generate=False
        )
        assert not screen.generate_box.isVisibleTo(screen)
        assert screen._role_buttons == {}  # no radios, no Generate: unchanged
        assert screen.attribution_status_label.isVisibleTo(screen)
        assert screen.attribution_status_label.text() == reason
        assert not screen.generate_button.isEnabled()
        screen.deleteLater()

    def test_no_status_on_the_recovered_view_without_a_profile(self, qapp: Any) -> None:
        screen, _controller, _kwargs = self._screen(
            _note_document(), readiness=_readiness(False), can_generate=False
        )
        assert not screen.attribution_status_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_a_failed_note_config_keeps_the_fallback_visible(self, qapp: Any) -> None:
        """PR-HIGH-004: a config error hides the generation group; the D2
        line must survive it, and Generate stays unavailable."""
        from scribe_desktop.note_config import NoteConfigError

        def broken() -> Any:
            raise NoteConfigError("template_profiles.json: field x is invalid")

        reason = models.SPEAKER_MODEL_MISSING_REASON
        screen, _controller, _kwargs = self._screen(
            _note_document(), readiness=_readiness(True, reason), config_loader=broken
        )
        assert "Note config could not be loaded" in screen.message_label.text()
        assert not screen.generate_box.isVisibleTo(screen)
        assert not screen.generate_button.isEnabled()
        assert screen.attribution_status_label.isVisibleTo(screen)
        assert screen.attribution_status_label.text() == reason
        screen.deleteLater()

    def test_no_status_for_a_transcript_without_speech(self, qapp: Any) -> None:
        def never() -> Any:
            pytest.fail("readiness consulted for a transcript with no speech")

        silent = _note_document().model_copy(update={"transcript_segments": ()})
        screen, _controller, _kwargs = self._screen(silent, readiness=never, can_generate=False)
        assert not screen.attribution_status_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_the_readiness_probe_is_not_consulted_for_an_attributed_document(
        self, qapp: Any
    ) -> None:
        def never() -> Any:
            pytest.fail("readiness consulted although the document is attributed")

        screen, _controller, _kwargs = self._screen(_attributed_document(), readiness=never)
        assert screen.role_auto_confirmed
        screen.deleteLater()

    def test_recovered_view_shows_no_auto_confirm_line(self, qapp: Any) -> None:
        screen, _controller, _kwargs = self._screen(_attributed_document(), can_generate=False)
        assert not screen.generate_box.isVisibleTo(screen)
        assert not screen.attribution_label.isVisibleTo(screen)
        assert not screen.role_auto_confirmed
        screen.deleteLater()

    def test_a_new_document_resets_the_auto_confirm_state(self, qapp: Any) -> None:
        screen, controller, _kwargs = self._screen(_attributed_document())
        assert screen.role_auto_confirmed
        screen.show_document(
            _note_document(),
            on_complete=controller.complete,
            on_discard=controller.discard,
            can_generate=True,
        )
        assert not screen.role_auto_confirmed
        assert screen._selected_role() is None
        assert not screen.attribution_label.isVisibleTo(screen)
        assert all(radio.isVisibleTo(screen) for radio in screen._role_buttons.values())
        screen.on_discard()
        assert not screen.attribution_label.isVisibleTo(screen)
        assert not screen.attribution_status_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_a_lying_enrolled_speaker_is_refused_before_the_screen_can_see_it(
        self, qapp: Any
    ) -> None:
        from pydantic import ValidationError

        base = _note_document().model_dump()
        with pytest.raises(ValidationError, match="transcribed text"):
            TranscriptDocument(
                **{
                    **base,
                    "enrolled_speaker": "speaker_9",
                    "enrolment_similarity": 0.9,
                    "speaker_model_id": "mock-speaker-embedder-v1",
                }
            )
        # A label that exists but transcribed to nothing has no radio either.
        textless = TranscriptSegment(
            start_seconds=50.0, end_seconds=51.0, speaker="speaker_3", transcript_words=()
        )
        with pytest.raises(ValidationError, match="transcribed text"):
            TranscriptDocument(
                **{
                    **base,
                    "transcript_segments": (*base["transcript_segments"], textless),
                    "enrolled_speaker": "speaker_3",
                    "enrolment_similarity": 0.9,
                    "speaker_model_id": "mock-speaker-embedder-v1",
                }
            )
