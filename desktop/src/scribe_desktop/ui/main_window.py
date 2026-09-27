"""Main window: the Phase-1 status window EXTENDED into the Step 10
multi-screen app (mic / session / recovery / transcript-inspection, plus
the Phase-1 registration/self-test panel as a Status tab)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.audio_capture import CaptureBackend
from scribe_desktop.benchmark import BenchmarkResult
from scribe_desktop.clinics import ClinicRegistry
from scribe_desktop.encounter import (
    EncounterRecord,
    EncounterUnavailable,
    VerificationRequest,
    VerificationResult,
    VerifiedTarget,
    WritebackRefused,
    WritebackSubject,
    read_encounter_record,
    reverification_request,
    verify_note_context,
    writeback_context,
)
from scribe_desktop.note import GeneratedNote
from scribe_desktop.protocol import HOST_NAME
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import (
    GenerationInProgressError,
    SessionActivityError,
    SessionState,
)
from scribe_desktop.status import read_registration_status, run_self_test
from scribe_desktop.transcription import (
    LiveTranscriber,
    RecoveryOutcome,
    TranscriptDocument,
)
from scribe_desktop.ui import models
from scribe_desktop.ui.clinics import ClinicsScreen
from scribe_desktop.ui.microphone import MicrophoneScreen
from scribe_desktop.ui.note import NoteScreen
from scribe_desktop.ui.practitioner import PractitionerScreen
from scribe_desktop.ui.recovery import RecoveryScreen
from scribe_desktop.ui.session_screen import SessionScreen
from scribe_desktop.ui.tasks import TaskThread
from scribe_desktop.ui.transcript import TranscriptScreen


@dataclass
class _CheckoutEncounter:
    """The recovered checkout's Cliniko link (Task 3.4). ``record`` is the
    decrypted ``encounter.enc`` (None: missing or undecryptable, so the
    session is unlinked); ``request`` the re-verification in flight and
    ``result`` the one that answered it. Ids only — never a display string."""

    session_id: str | None = None
    record: EncounterRecord | None = None
    request: VerificationRequest | None = None
    result: VerificationResult | None = None
    stopped: bool = False


class StatusPanel(QWidget):
    """The Phase-1 status window content (registration + self-test)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.registration_label = QLabel()
        self.self_test_label = QLabel("Self-test: not run")
        self.self_test_button = QPushButton("Run self-test")
        self.self_test_button.clicked.connect(self.on_self_test)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Native host: {HOST_NAME}"))
        layout.addWidget(self.registration_label)
        layout.addWidget(self.self_test_button)
        layout.addWidget(self.self_test_label)
        layout.addStretch(1)
        self.setLayout(layout)
        self.refresh_registration()

    def refresh_registration(self) -> None:
        status = read_registration_status()
        if status.registered:
            text = "registered ✓"
        else:
            text = "NOT registered — run scripts/register-native-host.py"
        self.registration_label.setText(f"Registration: {text}")

    def on_self_test(self) -> None:
        results = run_self_test()
        lines = [f"{r.name}: {'PASS' if r.passed else 'FAIL'} ({r.detail})" for r in results]
        self.self_test_label.setText("Self-test:\n" + "\n".join(lines))


class MainWindow(QMainWindow):
    def __init__(
        self,
        controller: models.SessionControllerLike,
        backend: CaptureBackend,
        *,
        sessions_root: Path | None = None,
        benchmark_runner: Callable[[], list[BenchmarkResult]] | None = None,
        transcriber_factory: Callable[
            [], Callable[[Path, SessionCrypto], TranscriptDocument]
        ]
        | None = None,
        recovery_runner: Callable[[Path], RecoveryOutcome] | None = None,
        profile_root: Path | None = None,
        config_root: Path | None = None,
        style_root: Path | None = None,
        language_model_available: Callable[[], bool] | None = None,
        clinic_registry: ClinicRegistry | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Cliniko Scribe")
        self._controller = controller
        # Phase H round 24 MED-006: the language model's presence is a seam
        # here too — the Practitioner tab's poll and the Note tab's prose
        # stage both ask it, and a test must never read the real host's
        # install (docs/lessons.md 2026-09-24). None resolves the module
        # function at call time.
        self._language_model_available: Callable[[], bool] = (
            language_model_available
            if language_model_available is not None
            else (lambda: models.language_model_available())
        )
        # PR round 20 (PR-HIGH-009): which session the transcript view is
        # showing — "live", a recovered session id, or None. Closing the
        # view releases ONLY its own recovery checkout; a live transcript
        # closing must never release an unrelated recovered session's
        # sweep/relist protection.
        self._transcript_source: str | None = None
        # Round 42 LOW-006: the recovered checkout's unwrapped in-memory
        # key, retained so it can be destroy()ed (idempotent, in-memory
        # copy ONLY — disk custody untouched) when the view is overwritten
        # by a live transcript or closed; previously it was dropped to GC
        # unzeroized. Matches _retire_locked's in-memory-copy semantics.
        self._recovered_crypto: SessionCrypto | None = None

        self.microphone_screen = MicrophoneScreen(
            controller, backend, benchmark_runner=benchmark_runner, profile_root=profile_root
        )
        self.session_screen = SessionScreen(
            controller,
            device_provider=self.microphone_screen.selected_device_id,
            transcriber_factory=(
                transcriber_factory
                if transcriber_factory is not None
                else self._live_aware_transcriber
            ),
        )
        self.recovery_screen = RecoveryScreen(
            sessions_root,
            active_ids_provider=self._live_session_ids,
            recovery_runner=recovery_runner,
        )
        self.transcript_screen = TranscriptScreen(
            controller, recovery_busy_provider=self._recovery_in_flight
        )
        # Practitioner-profile plan Phase 5: the Note tab learns phrases into
        # the user cue file under `config_root` (None = the default config
        # root, exactly as the generator's loader resolves it) and reads the
        # learning status — a readable profile, the current consent version,
        # the opt-in — from the profile store at review start and at Save.
        # Note-learning plan Task 3.2: the writing style is read from
        # `practitioner_settings.json` under the same config root at every
        # review start and stamped on the finalised note (D7).
        # Note-learning plan Task 4.4: a prose style runs the language-model
        # stage on the Note tab's own TaskThread (the model loads there, once
        # per process); `style_root` is the learned-style store the own-voice
        # stage reads.
        self.note_screen = NoteScreen(
            config_root=config_root,
            learning_status_provider=lambda: models.learning_status(profile_root=profile_root),
            note_style_provider=lambda: models.read_note_style(config_root),
            prose_stage_provider=lambda style: models.build_prose_stage(
                style, style_root=style_root, available=self._language_model_available
            ),
        )
        # Practitioner-profile plan Phase 3: the voice-profile tab. It reads
        # the profile store at construction (a stat and one profile read, no
        # model loaded) — `profile_root` is the test seam for the store, and
        # `style_root` the learned-style store's (note-learning plan Phase 3).
        self.practitioner_screen = PractitionerScreen(
            controller,
            backend,
            profile_root=profile_root,
            config_root=config_root,
            style_root=style_root,
            language_model_available=self._language_model_available,
            # D15 (peer round 27 PR-MED-022): the idle monitor is handed over
            # synchronously before the enrolment worker opens the device.
            on_capture_start=self.microphone_screen.stop_monitor,
        )
        # A phrase learned on Save shows up on the Practitioner tab at once —
        # and so does a learned shorthand rule (note-learning plan Task 2.5:
        # the Note tab emits this same signal when rules change).
        self.note_screen.learned_phrases_changed.connect(
            self.practitioner_screen.refresh_learned_phrases
        )
        self.note_screen.learned_phrases_changed.connect(
            self.practitioner_screen.refresh_learned_rules
        )
        # The microphone screen's voice-profile report line is re-read when
        # the Practitioner tab changes the profile — not on the screen's 5 s
        # model-file poll, which must never decrypt the profile (round 51
        # MED-001).
        self.practitioner_screen.profile_changed.connect(
            self.microphone_screen.refresh_profile_line
        )
        # Cliniko workflow safeguards plan Task 2.2: the clinic keys. The
        # registry reads `clinics.json` at construction and nothing else — no
        # key, no Cliniko call (a call happens only on Validate / Replace key).
        # `clinic_registry` is the test seam: a test never reads the real file.
        self._clinic_registry = (
            clinic_registry if clinic_registry is not None else ClinicRegistry()
        )
        self.clinics_screen = ClinicsScreen(
            self._clinic_registry, live_session_clinic=self._live_session_clinic
        )
        # Task 3.4: a recovered checkout's encounter record, decrypted ONCE on
        # checkout (`_on_recovered`), and its D4 re-verification.
        self._checkout = _CheckoutEncounter()
        self._checkout_seq = 0
        self._reverify_task: TaskThread | None = None
        self._reverify_running: VerificationRequest | None = None
        # D9: a Replace key or Remove moves the clinic's rev — a checkout's
        # re-verification under the old rev no longer counts; check again.
        self.clinics_screen.clinics_changed.connect(self._on_clinics_changed)
        self.status_panel = StatusPanel()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.microphone_screen, "Microphone")
        self.tabs.addTab(self.session_screen, "Session")
        self.tabs.addTab(self.recovery_screen, "Recovery")
        self.tabs.addTab(self.transcript_screen, "Transcript")
        self.tabs.addTab(self.note_screen, "Note")
        self.tabs.addTab(self.practitioner_screen, "Practitioner")
        self.tabs.addTab(self.clinics_screen, "Clinics")
        self.tabs.addTab(self.status_panel, "Status")
        self.setCentralWidget(self.tabs)

        # D15 (the wiring owed from Phase 1): the controller cannot see the
        # microphone screen's benchmark `TaskThread`, so `begin_enrolment`
        # consults this blocker; the reverse refusal (the benchmark while
        # enrolling) lives in `MicrophoneScreen.on_run_benchmark`.
        controller.set_enrolment_blocker(self._enrolment_blocker)
        # Note-learning plan Task 1.4: the live worker's factory, registered here
        # because the live view is a screen this window owns.
        controller.set_live_transcriber_factory(self._build_live_transcriber)
        # The live view opens on a SUCCESSFUL Start (round 7 LOW-003) and
        # closes on the Session screen's Discard. `session_started` is emitted
        # synchronously inside `on_start`, before the GUI thread returns to
        # its event loop, so it always precedes the delivery of the worker's
        # first queued `live_window` post.
        self.session_screen.session_started.connect(self._on_session_started)
        self.session_screen.session_discarded.connect(self.transcript_screen.clear_live_view)
        # D10: first run asks, never blocks — with no profile the tab is
        # selected and its banner shown; every other screen works as today.
        if not self.practitioner_screen.profile_present:
            self.practitioner_screen.show_first_run_banner()
            self.tabs.setCurrentWidget(self.practitioner_screen)

        self.session_screen.transcript_ready.connect(self._on_live_transcript)
        self.recovery_screen.recovered.connect(self._on_recovered)
        self.transcript_screen.closed.connect(self._on_transcript_closed)
        # Phase 7: generation orchestration. The Transcript screen composes a
        # draft (holding the lease); the Note tab reviews it; save/abandon
        # relay back to the Transcript screen (which owns the lease + scoped
        # write). While the lease is held, the Recovery screen is blocked so
        # no view swap can overwrite the retained recovered key (the residue).
        self.transcript_screen.draft_ready.connect(self._on_draft_ready)
        self.transcript_screen.generation_active_changed.connect(
            self._on_generation_active
        )

    # --- routing -----------------------------------------------------------

    def _live_aware_transcriber(self) -> Callable[[Path, SessionCrypto], TranscriptDocument]:
        """The default transcriber factory (note-learning plan Task 1.3):
        the real ML stack, claiming the sealed live worker from the
        controller INSIDE the run and reporting the live outcome to the
        Session screen. Built per Finish, so the controller is consulted at
        run time, never at construction."""
        return models.build_transcriber(
            live_source=self._controller.claim_live_transcriber,
            on_status=self.session_screen.report_live_status,
        )

    def _build_live_transcriber(self) -> LiveTranscriber:
        """The controller calls this on the GUI thread inside ``start()``:
        build the worker whose posts the Transcript screen renders. It only
        builds — the view opens on ``session_started`` (round 7 LOW-003)."""
        return models.build_live_transcriber(on_window=self.transcript_screen.post_live_window)

    def _enrolment_blocker(self) -> str | None:
        """The activity `begin_enrolment` cannot see for itself (D15): a
        benchmark run saturates every core and owns no microphone, but its
        worker must not overlap the enrolment capture."""
        return "a benchmark is running" if self.microphone_screen.is_busy else None

    def _live_session_clinic(self) -> str | None:
        """The clinic the live session is linked to, for the Clinics tab's
        Remove refusal (D10): the tracked session's `EncounterContext` in any
        non-terminal state (recording, paused, processing, queued — and
        failed, whose custody the controller still holds). None when there
        is no such session or it is unlinked."""
        session = self._controller.session
        if session is None or session.is_terminal or session.encounter_context is None:
            return None
        return session.encounter_context.clinic_id

    def _recovery_in_flight(self) -> bool:
        """Round 33 MED-001: a recovery resume is running, so a note
        generation must not start (they must stay mutually exclusive — see
        the Transcript screen's guard). Paired with `set_generation_blocked`,
        which blocks a resume starting during a generation."""
        return self.recovery_screen.is_busy

    def _live_session_ids(self) -> frozenset[str]:
        """Exclude every custody-protected session from the recovery list:
        the controller's live session in ANY non-terminal state (PR round
        18, PR1 — a queued/failed session the controller still owns must
        not be recoverable through a second custody path) and every id an
        in-flight Discard has reserved (round 30 PR-MED-001 — the admitted
        concurrent start() swaps the live pointer mid-discard).

        Taken as ONE atomic controller snapshot (round 31 PR-MED-001):
        composing separate reserved/live reads was itself a race — a
        Discard-reserve plus admitted Start between the reads yielded a
        set omitting the still-reserved session for the length of its
        window."""
        return self._controller.custody_protected_ids()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Refuse to close while a worker thread runs (PR round 18, PR6):
        destroying a running QThread aborts the process. A force-kill is
        still safe — crash recovery (Flow 3) covers it — but a normal close
        must not tear down a live transcription/benchmark thread."""
        if self._controller.state in (SessionState.RECORDING, SessionState.PAUSED):
            # Round 42 MED-002 (guard-only, pending user ratification;
            # sibling of the PR-round-18 PR6 thread guard below): closing
            # would kill the daemon capture worker mid-chunk and silently
            # drop the buffered tail of a LIVE consultation. Finish or
            # Discard first; a force-kill remains safe via crash recovery.
            self.statusBar().showMessage(
                "Recording in progress - Finish or Discard the session "
                "before closing."
            )
            event.ignore()
            return
        if self._controller.enrolling or self.practitioner_screen.is_busy:
            # Practitioner-profile plan D15: the activity spans capture ->
            # embed -> save -> the tab's result handler; closing mid-way would
            # destroy the running worker (the PR6 hazard) or leave the lease
            # held. Stop is the escape: it is honoured inside the capture and
            # before the embedding and the save; the WORKER saves, and the
            # lease stays held through the handler that reports the result.
            self.statusBar().showMessage(
                "Voice enrolment in progress - wait for it to finish (or Stop "
                "it) before closing."
            )
            event.ignore()
            return
        if (
            self.session_screen.is_busy
            or self.recovery_screen.is_busy
            or self.microphone_screen.is_busy
            or self.transcript_screen.is_busy
            or self.note_screen.is_busy
            or self.clinics_screen.is_busy
            or self.is_reverifying
        ):
            self.statusBar().showMessage(
                "Work in progress - wait for transcription, note generation, "
                "prose rendering, a benchmark, a clinic key check or a Cliniko "
                "note check to finish before closing."
            )
            event.ignore()
            return
        # Release the idle level-monitor's device before the window goes away
        # (smoke round 21) — never leave a PortAudio stream running teardown.
        self.microphone_screen.stop_monitor()
        super().closeEvent(event)

    def _on_live_transcript(self, document: object) -> None:
        assert isinstance(document, TranscriptDocument)
        # A different transcript replaces any stale note plaintext (Task 7.3).
        self.note_screen.clear()
        # Live path: the controller owns custody (queued -> Complete/Discard),
        # and note generation is available (a QUEUED controller session exists
        # for the scoped generation op).
        self.transcript_screen.show_document(
            document,
            on_complete=self._controller.complete,
            on_discard=self._controller.discard,
            store_finished=True,
            can_generate=True,
        )
        # If a recovered transcript was open it stays CHECKED OUT (protected
        # from sweep/relist) until app restart — availability residual only,
        # never a custody violation (PR round 20 residual, recorded in plan).
        # Round 42 LOW-006: its replaced callbacks are unreachable now, so
        # destroy the in-memory key copy (disk custody remains for a
        # post-restart recovery; adds zero availability loss).
        self._destroy_recovered_crypto()
        self._end_checkout_encounter()
        self._transcript_source = "live"
        self.tabs.setCurrentWidget(self.transcript_screen)

    def _on_session_started(self) -> None:
        """A successful Start (note-learning plan Task 1.4) opens the live
        view, whose first act is to DROP whatever the transcript screen held
        — including a RECOVERED document's Complete/Discard closures, the
        only route to that session's custody actions. Phase H round 24
        MED-001: a view change that drops those closures must do what a
        close does — destroy the retained in-memory key copy and release
        the recovered checkout (scoped, by id) — BEFORE the live view opens;
        otherwise a Discard during the recording leaves the recovered
        session checked out with its key copy resident and no control able
        to finish it until restart. A "live" source needs nothing: the
        controller retired that session at Start. `_destroy_recovered_crypto`'s
        two refusal branches stay unreachable here (round 45 LOW-004): Start
        itself is refused under a generation lease (`_refuse_while_generating`),
        and a discard reservation is held synchronously on the GUI thread by
        the Session screen's own Discard handler, so no Start click can
        interleave with it (the controller deliberately admits a concurrent
        `start()` mid-discard — round 30 — but the GUI never issues one)."""
        self._destroy_recovered_crypto()
        self._end_checkout_encounter()
        source = self._transcript_source
        self._transcript_source = None
        if source is not None and source != "live":
            self.recovery_screen.release_checkout(source)
        self.transcript_screen.begin_live_view()

    def _on_recovered(self, payload: object) -> None:
        assert isinstance(payload, tuple) and len(payload) == 2
        directory, outcome = payload
        assert isinstance(directory, Path)
        assert isinstance(outcome, RecoveryOutcome)
        # Recovered path: custody actions route through the controller's
        # lease-aware coordinator (Task 6.3) — never raw store primitives
        # from the UI, so a live note generation blocks recovered Complete/
        # Discard exactly as it blocks the live-session ones (the Flow 2
        # ordering itself is unchanged, performed inside the coordinator).
        # PR round 18 (PR7): the callbacks close over the crypto ONLY —
        # never over the outcome, so no plaintext document reference
        # outlives the inspection view.
        crypto = outcome.crypto
        # A different transcript replaces any stale note plaintext (Task 7.3).
        self.note_screen.clear()
        # Recovered path: no QUEUED controller session exists, so note
        # generation is unavailable here — the view shows Complete/Discard
        # only (can_generate defaults False).
        self.transcript_screen.show_document(
            outcome.document,
            on_complete=lambda: self._controller.complete_recovered(directory, crypto),
            on_discard=lambda: self._controller.discard_recovered(directory, crypto),
            store_finished=outcome.store_finished,
        )
        # Round 42 LOW-006: retain for destroy-on-overwrite/close (a prior
        # retained copy cannot exist while a checkout blocks resume, but
        # destroy() is idempotent — belt and braces).
        self._destroy_recovered_crypto()
        self._recovered_crypto = crypto
        self._transcript_source = directory.name
        self._open_checkout_encounter(directory, crypto)
        self.tabs.setCurrentWidget(self.transcript_screen)

    # --- the recovered checkout's Cliniko link (Task 3.4) --------------------

    def _open_checkout_encounter(self, directory: Path, crypto: SessionCrypto) -> None:
        """THE one decrypt of a recovered session's ``encounter.enc`` —
        here, on checkout, never in the listing, the sweep or a refresh
        (Critical Constraint 7). Missing or undecryptable means unlinked. A
        linked record is re-verified with Cliniko (D4) before it counts as
        linked: until an answer lands, write-back is refused."""
        self._end_checkout_encounter()
        record: EncounterRecord | None
        try:
            record = read_encounter_record(directory, crypto, directory.name)
        except EncounterUnavailable:
            record = None
        self._checkout = _CheckoutEncounter(session_id=directory.name, record=record)
        if record is not None and record.context is not None:
            self._checkout_seq += 1
            request = reverification_request(
                record.context, self._clinic_registry, seq=self._checkout_seq
            )
            if request is not None:
                self._dispatch_reverification(request)
        self._show_checkout_line()

    def _dispatch_reverification(self, request: VerificationRequest) -> None:
        """One check runs at a time; a request made while an older (now
        stale) one runs is started when that one finishes."""
        self._checkout.request = request
        if self._reverify_task is None:
            self._run_reverification(request)

    def _run_reverification(self, request: VerificationRequest) -> None:
        registry = self._clinic_registry
        # The holder pattern (`ui/clinics.py`, round 15 MED-006): the thread
        # object stays a child of this window, so a closure that kept the
        # request would keep the checkout's ids alive after the checkout
        # ended (round 20 LOW-013). The worker takes it; nothing here keeps it.
        holder = [request]
        task = TaskThread(
            lambda: verify_note_context(
                holder.pop(), key_store=registry.key_store, transport=registry.transport
            ),
            self,
        )
        task.succeeded.connect(self._on_reverified)
        task.failed.connect(self._on_reverify_failed)
        self._reverify_task = task
        self._reverify_running = request
        task.start()

    def _finish_reverify_task(self) -> VerificationRequest | None:
        ran = self._reverify_running
        self._reverify_running = None
        if self._reverify_task is not None:
            self._reverify_task.finish()
            self._reverify_task = None
        return ran

    def _start_waiting_reverification(self, ran: VerificationRequest | None) -> None:
        waiting = self._checkout.request
        if waiting is not None and waiting is not ran and self._checkout.result is None:
            self._run_reverification(waiting)

    def _on_reverified(self, result: object) -> None:
        ran = self._finish_reverify_task()
        # Applied only to the checkout that dispatched it (identity): a result
        # arriving after the view closed or moved on changes nothing.
        if (
            isinstance(result, VerificationResult)
            and self._checkout.request is not None
            and result.request is self._checkout.request
        ):
            self._checkout.result = result
        self._start_waiting_reverification(ran)
        self._show_checkout_line()

    def _on_reverify_failed(self, _message: str) -> None:
        # `verify_note_context` never raises; if it did, fixed copy only.
        ran = self._finish_reverify_task()
        if ran is not None and ran is self._checkout.request:
            self._checkout.stopped = True
        self._start_waiting_reverification(ran)
        self._show_checkout_line()

    @property
    def is_reverifying(self) -> bool:
        return self._reverify_task is not None

    def _on_clinics_changed(self) -> None:
        checkout = self._checkout
        record = checkout.record
        if checkout.session_id is None or record is None or record.context is None:
            return
        request = checkout.request
        registry = self._clinic_registry
        if (
            request is not None
            and registry.record(request.clinic.clinic_id) is not None
            and registry.rev(request.clinic.clinic_id) == request.clinic_rev
        ):
            return  # the check in hand (or in flight) is still current
        checkout.result = None
        checkout.stopped = False
        self._checkout_seq += 1
        fresh = reverification_request(record.context, registry, seq=self._checkout_seq)
        if fresh is None:
            checkout.request = None
        else:
            self._dispatch_reverification(fresh)
        self._show_checkout_line()

    def _end_checkout_encounter(self) -> None:
        """Drop the checkout's decrypted record (ids) when its view closes or
        is replaced. A re-verification still running answers nobody."""
        self._checkout = _CheckoutEncounter()
        self.transcript_screen.set_link_line("")

    def _show_checkout_line(self) -> None:
        """On the Transcript screen — where opening a recovered session
        lands (round 20 LOW-014)."""
        checkout = self._checkout
        if checkout.session_id is None:
            self.transcript_screen.set_link_line("")
            return
        record = checkout.record
        context = record.context if record is not None else None
        result = checkout.result
        self.transcript_screen.set_link_line(
            models.checkout_link_line(
                record,
                checking=checkout.request is not None and result is None and not checkout.stopped,
                outcome=result.outcome if result is not None else None,
                clinic_known=(
                    context is None
                    or self._clinic_registry.record(context.clinic_id) is not None
                ),
            )
        )

    def recovered_writeback_target(self) -> VerifiedTarget | WritebackRefused | None:
        """Constraint 6 over the recovered checkout (Phase 4's entry): None
        when no recovered session is checked out."""
        if self._checkout.session_id is None:
            return None
        subject = WritebackSubject.of_checkout(self._checkout.record, self._checkout.result)
        return writeback_context(subject, self._clinic_registry)

    def live_writeback_target(
        self, reverification: VerificationResult | None = None
    ) -> VerifiedTarget | WritebackRefused | None:
        """Constraint 6 over the live session (Phase 4's entry): refused
        until ``reverification`` — Phase 4's pre-write check of the session's
        note, D4 — answers under the clinic's current rev (round 20
        MED-012). None with no non-terminal session."""
        session = self._controller.session
        if session is None or session.is_terminal:
            return None
        subject = WritebackSubject.of_live(
            session.consent, session.encounter_context, reverification
        )
        return writeback_context(subject, self._clinic_registry)

    def _destroy_recovered_crypto(self) -> None:
        """Zeroize the retained recovered-checkout key copy (round 42
        LOW-006). Idempotent; a no-op after Complete/Discard already
        destroyed it. In-memory copy only — key.dpapi is never touched.

        Routed through the lease-aware coordinator (Task 6.3): while a note
        generation is in flight (GenerationInProgressError) or a discard's
        custody reservation is held (round 30: SessionActivityError, the
        coarse identity-less refusal), the coordinator refuses and the
        REFERENCE IS RETAINED.

        Round 45 LOW-004 corrects what happens next. Nothing re-runs this
        cleanup on release — `_on_generation_active(False)` only unblocks the
        recovery screen — so a retained reference waits for the NEXT call
        site (a transcript opening or closing), which may be never before
        exit. That is not a live gap: both refusal branches are unreachable
        under the shipped wiring, because every caller of this method
        (`_on_live_transcript`, `_on_recovered`, `_on_transcript_closed`) is
        itself already blocked while a lease or a discard reservation is
        held. Phase 7's busy guards own keeping view swaps unreachable during
        generation; this catch is the custody backstop, not the UX. If a
        future caller CAN reach it while blocked, give the release path an
        explicit re-run rather than relying on the next view change."""
        if self._recovered_crypto is None:
            return
        try:
            self._controller.destroy_recovered_crypto(self._recovered_crypto)
        except (GenerationInProgressError, SessionActivityError):
            return
        self._recovered_crypto = None

    # --- note generation orchestration (Phase 7) --------------------------

    def _on_draft_ready(self, result: object) -> None:
        assert isinstance(result, models.NoteGenerationResult)
        self.note_screen.begin_review(
            result,
            copy_enabled=models.COPY_TO_CLINIKO_ENABLED,
            on_save=self._on_note_save,
            on_abandon=self._on_note_abandon,
            on_cancel=self._on_note_cancel,
            on_state_changed=self.transcript_screen.set_note_review_state,
            template_profile_id=self.transcript_screen.selected_profile_id(),
        )
        self.tabs.setCurrentWidget(self.note_screen)

    def _on_note_save(self, note: object) -> None:
        # write_note runs on THIS (GUI) thread via the scoped op; raises on
        # refusal so the Note tab surfaces it and the lease stays held.
        assert isinstance(note, GeneratedNote)
        self.transcript_screen.save_note(note)

    def _on_note_abandon(self) -> None:
        # Delete-note-and-complete-without-one: completes (deleting any
        # note.enc) UNDER the held lease, releasing it only on success (round
        # 35 PR-MED-001). Raises on failure -> the Note tab surfaces it with
        # the lease + review still held. On success the transcript screen
        # emits closed("completed").
        self.transcript_screen.abandon_note_and_complete()

    def _on_note_cancel(self) -> None:
        # Non-destructive cancel/regenerate (round 35 PR-MED-003): drop the
        # in-memory draft, release the lease, keep transcript + key, and
        # return to the Transcript screen with Generate available again.
        # Practitioner-profile plan Task 5.6: the learning queue dies with the
        # draft (the Note tab clears after this callback), so read it FIRST
        # and say what was lost on the screen the practitioner lands on.
        queued = self.note_screen.queued_learning_count()
        rules = self.note_screen.queued_rule_count()
        self.transcript_screen.cancel_note_review()
        self.transcript_screen.report_unlearned_phrases(queued, rules)
        self.tabs.setCurrentWidget(self.transcript_screen)

    def _on_generation_active(self, active: object) -> None:
        active_bool = bool(active)
        # While a live generation lease is held, block recovery view swaps so
        # the retained recovered key cannot be overwritten (residue guard).
        self.recovery_screen.set_generation_blocked(active_bool)
        # Round 36 PR-MED-001: when a NEW generation starts, synchronously
        # invalidate any stale (post-Save) Note tab, so its still-enabled
        # delete-and-complete action can never route through the NEW lease.
        # The new generation's own Note tab appears only after draft_ready
        # (its compose worker has returned), so no terminal action can fire
        # while a compose worker runs.
        if active_bool:
            self.note_screen.clear()

    def _on_transcript_closed(self, _outcome: str) -> None:
        # Practitioner-profile plan Task 5.6: Delete-note-and-complete and
        # Discard reach here with the review's learning queue still live —
        # read it before the clear, then append what was lost to the
        # Transcript screen's own closing message. A saved note has an empty
        # queue, so Complete after Save reports nothing.
        queued = self.note_screen.queued_learning_count()
        rules = self.note_screen.queued_rule_count()
        self.note_screen.clear()
        self.transcript_screen.report_unlearned_phrases(queued, rules)
        self.session_screen.refresh()
        # PR round 20 (PR-HIGH-009): release ONLY the checkout owned by the
        # transcript that just closed — never an unscoped clear.
        # Round 42 LOW-006: the closing custody action (Complete/Discard)
        # already destroyed the key — this is the idempotent cleanup of the
        # retained reference.
        self._destroy_recovered_crypto()
        self._end_checkout_encounter()
        source = self._transcript_source
        self._transcript_source = None
        if source is not None and source != "live":
            self.recovery_screen.release_checkout(source)
        else:
            self.recovery_screen.refresh()
        # Peer round 44 PR-MED-026: a terminal exit that dropped queued
        # phrases stays on the Transcript screen so the appended sentence is
        # actually seen; every other close (ordinary Complete, Complete after
        # Save, an empty queue) lands on the Session screen as before.
        landing = self.transcript_screen if queued + rules > 0 else self.session_screen
        self.tabs.setCurrentWidget(landing)
