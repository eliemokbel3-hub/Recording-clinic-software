"""Main window: the Phase-1 status window EXTENDED into the Step 10
multi-screen app (mic / session / recovery / transcript-inspection, plus
the Phase-1 registration/self-test panel as a Status tab)."""

from __future__ import annotations

from collections.abc import Callable
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
from scribe_desktop.note import GeneratedNote
from scribe_desktop.protocol import HOST_NAME
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import (
    GenerationInProgressError,
    SessionActivityError,
    SessionState,
)
from scribe_desktop.status import read_registration_status, run_self_test
from scribe_desktop.transcription import RecoveryOutcome, TranscriptDocument
from scribe_desktop.ui import models
from scribe_desktop.ui.microphone import MicrophoneScreen
from scribe_desktop.ui.note import NoteScreen
from scribe_desktop.ui.recovery import RecoveryScreen
from scribe_desktop.ui.session_screen import SessionScreen
from scribe_desktop.ui.transcript import TranscriptScreen


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
        ] = models.build_transcriber,
        recovery_runner: Callable[[Path], RecoveryOutcome] | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Cliniko Scribe")
        self._controller = controller
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
            controller, backend, benchmark_runner=benchmark_runner
        )
        self.session_screen = SessionScreen(
            controller,
            device_provider=self.microphone_screen.selected_device_id,
            transcriber_factory=transcriber_factory,
        )
        self.recovery_screen = RecoveryScreen(
            sessions_root,
            active_ids_provider=self._live_session_ids,
            recovery_runner=recovery_runner,
        )
        self.transcript_screen = TranscriptScreen(
            controller, recovery_busy_provider=self._recovery_in_flight
        )
        self.note_screen = NoteScreen()
        self.status_panel = StatusPanel()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.microphone_screen, "Microphone")
        self.tabs.addTab(self.session_screen, "Session")
        self.tabs.addTab(self.recovery_screen, "Recovery")
        self.tabs.addTab(self.transcript_screen, "Transcript")
        self.tabs.addTab(self.note_screen, "Note")
        self.tabs.addTab(self.status_panel, "Status")
        self.setCentralWidget(self.tabs)

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
        if (
            self.session_screen.is_busy
            or self.recovery_screen.is_busy
            or self.microphone_screen.is_busy
            or self.transcript_screen.is_busy
            or self.note_screen.is_busy
        ):
            self.statusBar().showMessage(
                "Work in progress - wait for transcription, note generation, "
                "or benchmark to finish before closing."
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
        self._transcript_source = "live"
        self.tabs.setCurrentWidget(self.transcript_screen)

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
        self.tabs.setCurrentWidget(self.transcript_screen)

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
        self.transcript_screen.cancel_note_review()
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
        self.note_screen.clear()
        self.session_screen.refresh()
        # PR round 20 (PR-HIGH-009): release ONLY the checkout owned by the
        # transcript that just closed — never an unscoped clear.
        # Round 42 LOW-006: the closing custody action (Complete/Discard)
        # already destroyed the key — this is the idempotent cleanup of the
        # retained reference.
        self._destroy_recovered_crypto()
        source = self._transcript_source
        self._transcript_source = None
        if source is not None and source != "live":
            self.recovery_screen.release_checkout(source)
        else:
            self.recovery_screen.refresh()
        self.tabs.setCurrentWidget(self.session_screen)
