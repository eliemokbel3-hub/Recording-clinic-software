"""Main window: the Phase-1 status window EXTENDED into the Step 10
multi-screen app (mic / session / recovery / transcript-inspection, plus
the Phase-1 registration/self-test panel as a Status tab)."""

from __future__ import annotations

import ctypes
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal

from PySide6.QtCore import QByteArray, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop import __version__, identity, install_layout
from scribe_desktop.audio_capture import CaptureBackend
from scribe_desktop.audit import AuditLog
from scribe_desktop.benchmark import BenchmarkResult
from scribe_desktop.clinics import ClinicRegistry
from scribe_desktop.context_rules import (
    PauseReason,
    ReminderEntry,
    ReminderIndex,
    is_suspend_message,
    pause_action,
    reminder_entry,
)
from scribe_desktop.draft_write import (
    AlreadyWritten,
    Hop1Result,
    PreparedWrite,
    WriteOutcome,
    WriteRecord,
    WriteRefusal,
    attempt_record,
    finished_record,
    prepare_write,
    read_for_write,
    reconciled_record,
    refuse_before_read,
    write_for_click,
)
from scribe_desktop.encounter import (
    RATE_LIMIT_COOLDOWN_SECONDS,
    EncounterRecord,
    EncounterUnavailable,
    RateLimitLatch,
    UnverifiedOffline,
    VerificationRequest,
    VerificationResult,
    Verified,
    VerifiedTarget,
    WritebackRefusal,
    WritebackRefused,
    WritebackSubject,
    rate_limited_result,
    read_encounter_record,
    reverification_request,
    verify_note_context,
    writeback_context,
)
from scribe_desktop.exclusions import WindowsLayer
from scribe_desktop.hotkey import (
    NOT_SET_UP,
    GlobalHotkey,
    HotkeyRegistrar,
    HotkeyStatus,
    Win32HotkeyRegistrar,
)
from scribe_desktop.note import GeneratedNote
from scribe_desktop.note_config import (
    DevSettings,
    NoteConfig,
    NoteConfigError,
    PilotSettings,
    TemplateProfile,
    dev_writes_allowed,
    load_dev_settings,
    load_note_config,
    read_pilot_settings,
    save_dev_settings,
    save_pilot_settings,
    shadow_mode_on,
)
from scribe_desktop.past_sessions import KeepLabel, PastSessionStore, keep_label
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import (
    CAPTURING_STATES,
    GenerationInProgressError,
    RecordingSession,
    ReviewOpenRefused,
    SessionActivityError,
    SessionControllerError,
    SessionState,
    WriteInFlightError,
    WriteReservation,
)
from scribe_desktop.session_mode import SessionMode
from scribe_desktop.session_store import KEY_FILENAME, audit_created_at, session_expires_at
from scribe_desktop.status import read_registration_status, registration_lines, run_self_test
from scribe_desktop.system_events import NOT_SET_UP as SYSTEM_PAUSE_NOT_SET_UP
from scribe_desktop.system_events import (
    SystemEventRegistrar,
    SystemPauseStatus,
    SystemPauseWatch,
    Win32SystemEventRegistrar,
)
from scribe_desktop.transcription import (
    LiveTranscriber,
    RecoveryOutcome,
    TranscriptDocument,
)
from scribe_desktop.ui import models
from scribe_desktop.ui.bridge import ChromeBridge
from scribe_desktop.ui.clinics import ClinicsScreen
from scribe_desktop.ui.microphone import MicrophoneScreen
from scribe_desktop.ui.note import NoteScreen
from scribe_desktop.ui.past_sessions import PastSessionsScreen
from scribe_desktop.ui.past_sessions_view import PAST_SESSIONS_TAB_TITLE
from scribe_desktop.ui.practitioner import PractitionerScreen
from scribe_desktop.ui.recovery import RecoveryScreen
from scribe_desktop.ui.session_screen import SessionScreen
from scribe_desktop.ui.tasks import TaskThread
from scribe_desktop.ui.transcript import TranscriptScreen
from scribe_desktop.voice_commands import NewConsultationWatcher, SpokenPauseDetector


@dataclass
class _CheckoutEncounter:
    """The recovered checkout's Cliniko link (Task 3.4). ``record`` is the
    decrypted ``encounter.enc`` (None: missing or undecryptable, so the
    session is unlinked); ``request`` the re-verification in flight and
    ``result`` the one that answered it. ``record`` holds ids only; a
    ``Verified`` ``result`` also carries Cliniko's display strings (the
    patient's name), in memory only — the checkout line never shows them,
    and ``keep_label_for`` reads the name for the Past-sessions label at
    Complete (privacy-professional-controls D5)."""

    session_id: str | None = None
    record: EncounterRecord | None = None
    request: VerificationRequest | None = None
    result: VerificationResult | None = None
    stopped: bool = False
    # Task 5.4: the session was ADOPTED as the live session (Open for review);
    # its record came from the adoption's one decrypt, and write-back goes
    # through the live entry, never the recovered one.
    adopted: bool = False


@dataclass
class _WriteJob:
    """ONE "Write draft to Cliniko" click (draft-write Task 5.2), on the GUI
    thread from the click until its last handler: the held reservation
    (D9), the session it names, the click's own verification request (D3 —
    its clinic's key is what both hops read), what the click read under the
    reservation (the record, the saved note and its identity — repr-hidden:
    note text), whether an EARLIER attempt was open at the click (the
    ``write_uncertain`` prefix, PR-MED-017), the worker running, the stage,
    and the ``attempting`` row once it is on disk."""

    reservation: WriteReservation
    session_id: str
    request: VerificationRequest = field(repr=False)
    inputs: models.WriteInputs = field(repr=False)
    uncertain: bool
    task: TaskThread | None = None
    stage: Literal["hop1", "prepare", "hop2"] = "hop1"
    attempt: WriteRecord | None = None


def _utc_now() -> datetime:
    return datetime.now(UTC)



class _MSG(ctypes.Structure):
    """The head of a Windows ``MSG`` (``nativeEvent``'s
    ``windows_generic_MSG``): enough to recognise a power broadcast or a
    hotkey press."""

    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
    ]


def _native_msg(event_type: object, message: object) -> tuple[int, int] | None:
    """A Windows native event's ``(message, wParam)``; None for anything else."""
    name = event_type.data() if isinstance(event_type, QByteArray) else event_type
    to_int = getattr(message, "__int__", None)  # an int, or shiboken's VoidPtr
    if name != b"windows_generic_MSG" or to_int is None:
        return None
    address = to_int()
    if not isinstance(address, int) or address == 0:
        return None
    msg = _MSG.from_address(address)
    return int(msg.message), int(msg.wParam)


def _is_suspend_event(event_type: object, message: object) -> bool:
    """D5: the native event is ``WM_POWERBROADCAST`` / ``PBT_APMSUSPEND``."""
    head = _native_msg(event_type, message)
    return head is not None and is_suspend_message(*head)


# Installation plan D4: the dev-only Status checkbox and its save failure.
DEV_WRITES_CHECKBOX_TEXT: Final = "Allow Cliniko writes from this developer build"
DEV_WRITES_SAVE_FAILED: Final = (
    "The developer build's write setting could not be saved; the box shows the setting "
    "in use."
)
# Pilot plan Task 1.1 (D1-D3): the shadow-mode checkbox, in both channels.
SHADOW_MODE_CHECKBOX_TEXT: Final = "Shadow mode (pilot)"
SHADOW_MODE_UNREADABLE: Final = (
    "The shadow-mode setting could not be read, so shadow mode is on. Untick the box "
    "to turn it off."
)
SHADOW_MODE_SAVE_FAILED: Final = (
    "The shadow-mode setting could not be saved; the box shows the setting in use."
)


def version_line(version: str) -> str:
    """The Status tab's app-version line (pilot plan Task 1.1)."""
    return f"Clinic Scribe version {version}"


class StatusPanel(QWidget):
    """The Phase-1 status window content (registration + self-test), under
    the intended-use line (privacy-professional-controls D14) and the
    start-up exclusion warnings (Task 4.1, Flow 6 — fixed lines computed once
    by ``app.main`` before the window is built; hidden when there are none).

    Installation plan D4 (Task 1.6): in the DEV channel only, the "Allow
    Cliniko writes from this developer build" checkbox — off by default, read
    from and saved to ``config\\dev.json`` under ``config_root``; a failed
    save says so and shows the setting re-read from the file. A production
    build has no checkbox and never reads the file. ``dev_writes_changed``
    fires after every save attempt, failed or not.

    Pilot plan Task 1.1 (D1-D3): in BOTH channels, the "Shadow mode (pilot)"
    checkbox, read from and saved to ``config\\pilot.json`` under
    ``config_root`` (None: ``note_config.pilot_settings_root``); a file that
    cannot be read shows the box ticked (shadow on, D3) with a line naming
    it; a failed save says so and re-reads the box. ``shadow_mode_changed``
    fires after every save attempt. And the app version (``app_version``,
    the seam; ``__version__`` when None)."""

    dev_writes_changed = Signal()
    shadow_mode_changed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        exclusion_warnings: Sequence[str] = (),
        config_root: Path | None = None,
        windows_layer: WindowsLayer | None = None,
        app_version: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._config_root = config_root
        self._windows_layer = windows_layer
        self.version_label = QLabel(
            version_line(app_version if app_version is not None else __version__)
        )
        self.version_label.setTextFormat(Qt.TextFormat.PlainText)
        self.shadow_checkbox = QCheckBox(SHADOW_MODE_CHECKBOX_TEXT)
        self.shadow_label = QLabel()
        self.shadow_label.setWordWrap(True)
        self.shadow_label.setTextFormat(Qt.TextFormat.PlainText)
        self._show_shadow_setting()
        self.shadow_checkbox.toggled.connect(self._on_shadow_toggled)
        self.intended_use_label = QLabel(models.INTENDED_USE_LINE)
        self.intended_use_label.setWordWrap(True)
        self.intended_use_label.setTextFormat(Qt.TextFormat.PlainText)
        self.exclusion_warnings = tuple(exclusion_warnings)
        self.exclusions_label = QLabel("\n".join(self.exclusion_warnings))
        self.exclusions_label.setWordWrap(True)
        self.exclusions_label.setTextFormat(Qt.TextFormat.PlainText)
        self.exclusions_label.setVisible(bool(self.exclusion_warnings))
        self.registration_label = QLabel()
        self.self_test_label = QLabel("Self-test: not run")
        self.self_test_button = QPushButton("Run self-test")
        self.self_test_button.clicked.connect(self.on_self_test)
        self.dev_writes_checkbox: QCheckBox | None = None
        self.dev_writes_label = QLabel()
        self.dev_writes_label.setWordWrap(True)
        self.dev_writes_label.setTextFormat(Qt.TextFormat.PlainText)
        self.dev_writes_label.hide()

        layout = QVBoxLayout()
        layout.addWidget(self.intended_use_label)
        layout.addWidget(self.exclusions_label)
        layout.addWidget(self.version_label)
        layout.addWidget(QLabel(f"Native host: {identity.host_name()}"))
        layout.addWidget(self.registration_label)
        layout.addWidget(self.shadow_checkbox)
        layout.addWidget(self.shadow_label)
        if install_layout.channel() == "dev":
            checkbox = QCheckBox(DEV_WRITES_CHECKBOX_TEXT)
            checkbox.setChecked(load_dev_settings(config_root).allow_cliniko_writes)
            checkbox.toggled.connect(self._on_dev_writes_toggled)
            self.dev_writes_checkbox = checkbox
            layout.addWidget(checkbox)
            layout.addWidget(self.dev_writes_label)
        layout.addWidget(self.self_test_button)
        layout.addWidget(self.self_test_label)
        layout.addStretch(1)
        self.setLayout(layout)
        self.refresh_registration()

    def _on_dev_writes_toggled(self, checked: bool) -> None:
        checkbox = self.dev_writes_checkbox
        assert checkbox is not None  # connected only when it exists
        try:
            save_dev_settings(
                DevSettings(allow_cliniko_writes=checked), config_root=self._config_root
            )
        except NoteConfigError:
            # The box shows what is ON DISK, re-read (a failure after the
            # replace landed still saved the tick), and the Write button
            # re-reads it too; an unreadable file reads as writes off.
            checkbox.blockSignals(True)
            checkbox.setChecked(load_dev_settings(self._config_root).allow_cliniko_writes)
            checkbox.blockSignals(False)
            self.dev_writes_label.setText(DEV_WRITES_SAVE_FAILED)
            self.dev_writes_label.show()
            self.dev_writes_changed.emit()
            return
        self.dev_writes_label.hide()
        self.dev_writes_changed.emit()

    def _show_shadow_setting(self) -> bool:
        """Show the setting as it is ON DISK (D3: unreadable reads as on,
        named); True when the file could not be read."""
        setting = read_pilot_settings(self._config_root)
        self.shadow_checkbox.blockSignals(True)
        self.shadow_checkbox.setChecked(setting.shadow_mode)
        self.shadow_checkbox.blockSignals(False)
        self.shadow_label.setText(SHADOW_MODE_UNREADABLE if setting.unreadable else "")
        self.shadow_label.setVisible(setting.unreadable)
        return setting.unreadable

    def _on_shadow_toggled(self, checked: bool) -> None:
        try:
            save_pilot_settings(PilotSettings(shadow_mode=checked), config_root=self._config_root)
        except NoteConfigError:
            # The box shows what is ON DISK, re-read (a failure after the
            # replace landed still saved the tick); every Start re-reads it.
            if not self._show_shadow_setting():
                self.shadow_label.setText(SHADOW_MODE_SAVE_FAILED)
                self.shadow_label.show()
            self.shadow_mode_changed.emit()
            return
        self._show_shadow_setting()
        self.shadow_mode_changed.emit()

    def refresh_registration(self) -> None:
        # Installation plan Task 2.3 (D9): read in Chrome's order through the
        # Windows layer `app.main` hands in (C6: none in a test window, which
        # then reads nothing and says "not checked").
        status = read_registration_status(self._windows_layer)
        self.registration_label.setText("\n".join(registration_lines(status)))

    def on_self_test(self) -> None:
        results = run_self_test()
        lines = [f"{r.name}: {'PASS' if r.passed else 'FAIL'} ({r.detail})" for r in results]
        self.self_test_label.setText("Self-test:\n" + "\n".join(lines))


class MainWindow(QMainWindow):
    # Task 7.1: a hotkey press, re-delivered from ``nativeEvent`` as a queued
    # call so the pause or resume runs outside Windows' message dispatch.
    _hotkey_pressed_q = Signal()
    # D5 as amended 2026-09-28: the session locked, re-delivered the same way.
    _session_locked_q = Signal()
    # Round 57 SEC-021: a suspend that met no recording, looked at again once
    # the dispatch it arrived in has returned (it may have been inside Start).
    _suspend_recheck_q = Signal()

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
        rate_limit_latch: RateLimitLatch | None = None,
        write_store: models.WriteStore | None = None,
        write_profile: Callable[[GeneratedNote], TemplateProfile | None] | None = None,
        audit: AuditLog | None = None,
        past_sessions: PastSessionStore | None = None,
        past_sessions_confirm: Callable[[str, str], bool] | None = None,
        past_sessions_save_path: Callable[[], Path | None] | None = None,
        exclusion_warnings: Sequence[str] = (),
        windows_layer: WindowsLayer | None = None,
        live_ready: Callable[[], bool] | None = None,
        start_hold: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Clinic Scribe")
        self._controller = controller
        # Installation plan round 35 MED-001: whether the transcription
        # stack's imports have finished warming (``ml_warmup.ImportWarmup``,
        # started by ``app.main``). False: a Start runs without a live worker.
        # None — every test that does not ask for it — is always ready.
        self._live_ready = live_ready
        self._live_deferred = False
        # Privacy-professional-controls Task 1.4: the audit record the draft
        # write reports into (best-effort, C2); the recovery list and the Past
        # sessions tab are handed it — and the archive — directly below. None —
        # every test that does not ask for it — records nothing; ``app.main``
        # passes the one the controller holds.
        self._audit = audit
        # Draft-write Task 5.2: the one write in flight (None: none), the
        # session files it reads and writes under its reservation, and the
        # template profile it matches against — the last two are test seams
        # (a test never needs a real `note.enc` or the real config root).
        self._write_job: _WriteJob | None = None
        self._write_seq = 0
        self._write_store: models.WriteStore = (
            write_store if write_store is not None else models.SessionWriteStore()
        )
        self._write_profile: Callable[[GeneratedNote], TemplateProfile | None] = (
            write_profile
            if write_profile is not None
            else (lambda note: models.write_profile(note, self._config_root))
        )
        # Draft-write D13: THE 429 cooldown, owned here and shared by the
        # Chrome bridge's checks, the checkout re-verification and the draft
        # write — a 429 any of them sees cools the clinic for all of them.
        # `rate_limit_latch` is the test seam (its clock is injectable).
        self._rate_limit_latch = (
            rate_limit_latch if rate_limit_latch is not None else RateLimitLatch()
        )
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
            # Pilot plan D1: the pilot setting under this window's config root
            # (None: ``note_config.pilot_settings_root``), read at each Start.
            shadow_mode=lambda: shadow_mode_on(config_root),
        )
        # Installation plan round 36 MED-001 (the practitioner's option (b)):
        # every Start waits out the start-up import warm-up, bounded
        # (``ml_warmup.ImportWarmup.holds_start``; None never holds).
        self.session_screen.set_start_hold(start_hold)
        self.recovery_screen = RecoveryScreen(
            sessions_root,
            active_ids_provider=self._live_session_ids,
            recovery_runner=recovery_runner,
            audit=audit,
            past_sessions=past_sessions,
        )
        self.transcript_screen = TranscriptScreen(
            controller, recovery_busy_provider=self._recovery_in_flight
        )
        # D5: the Completes the Transcript screen calls itself are labelled
        # through the same resolution as the ones this window wires.
        self.transcript_screen.set_keep_label_provider(self.keep_label_for)
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
            # Draft-write D5 (R22-03): the Write button reads the session's
            # record through the controller's content-free accessor only.
            write_status_provider=controller.write_record_status,
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
            self._clinic_registry,
            live_session_clinic=self._live_session_clinic,
            writing_clinic=self._writing_clinic,
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
        # Task 4.5: the Chrome link, attached by `app.main` with the pipe
        # (`attach_chrome_link`); None in tests that build a window alone.
        self.chrome_bridge: ChromeBridge | None = None
        # Task 5.3 (D6): the Unreviewed reminder index — ids only, in memory,
        # filled when a Start retires a linked queued session.
        self.reminders = ReminderIndex()
        # Task 5.4 (D6): the note config a reopened saved note is compared
        # with — the root the Note tab learns into (None: the default root,
        # exactly as the generator resolves it).
        self._config_root = config_root
        # D6's on-close list: when the first close showed it (monotonic).
        self._close_armed_at: float | None = None
        # Phase 7 (D7, D8): the global hotkey (reserved only by
        # `attach_hotkey`, which only `app.py` calls — a test's window reserves
        # nothing) and the phrase rules over the live windows, per recording.
        self._hotkey: GlobalHotkey | None = None
        self._spoken_pause = SpokenPauseDetector()
        self._new_consultation = NewConsultationWatcher()
        self._hotkey_pressed_q.connect(
            self._on_hotkey_pressed, Qt.ConnectionType.QueuedConnection
        )
        # D5 as amended 2026-09-28: the suspend and lock notifications
        # (registered only by `attach_system_pause`, which only `app.py`
        # calls — a test's window registers nothing with Windows).
        self._system_events: SystemPauseWatch | None = None
        self._session_locked_q.connect(
            self._on_session_locked, Qt.ConnectionType.QueuedConnection
        )
        self._suspend_recheck_q.connect(
            self._on_suspend_recheck, Qt.ConnectionType.QueuedConnection
        )
        # Privacy-professional-controls Task 4.1 (Flow 6): the start-up
        # exclusion warnings, computed by `app.main` BEFORE this window is built
        # (`exclusions.startup_exclusions`) and shown on the Status tab and the
        # Past sessions status line. The window itself makes no Windows call
        # for them; the default `()` (every test that does not ask) shows none.
        # Installation plan Task 2.3: the registration line reads the registry
        # through the Windows layer `app.main` built (None reads nothing).
        self.status_panel = StatusPanel(
            exclusion_warnings=exclusion_warnings,
            config_root=config_root,
            windows_layer=windows_layer,
        )
        # Installation plan D4: the dev write setting changed — the Note tab's
        # Write button re-reads it now (a click always re-reads it anyway).
        self.status_panel.dev_writes_changed.connect(self.note_screen.refresh_write_control)
        # Pilot plan Task 1.7: the Session tab's line follows the setting at
        # once (a recording's own mode stays fixed at Start, D1).
        self.status_panel.shadow_mode_changed.connect(self.session_screen.refresh)
        # Privacy-professional-controls Task 3.1: what the archive kept, its
        # retention setting and the audit record's export. Construction reads
        # only the settings file under `config_root`; the archive is listed
        # when the tab is opened. `past_sessions` None (a test that does not
        # ask for it) touches no archive. Its confirmation and save dialog are
        # seams (round 16 LOW-018): None opens the real ones; a test passes
        # fakes so no real dialog ever opens (C6).
        self.past_sessions_screen = PastSessionsScreen(
            past_sessions,
            audit=audit,
            config_root=config_root,
            confirm=past_sessions_confirm,
            choose_csv_path=past_sessions_save_path,
            exclusion_warnings=exclusion_warnings,
        )

        self.tabs = QTabWidget()
        self.tabs.addTab(self.microphone_screen, "Microphone")
        self.tabs.addTab(self.session_screen, "Session")
        self.tabs.addTab(self.recovery_screen, "Recovery")
        self.tabs.addTab(self.transcript_screen, "Transcript")
        self.tabs.addTab(self.note_screen, "Note")
        self.tabs.addTab(self.past_sessions_screen, PAST_SESSIONS_TAB_TITLE)
        self.tabs.addTab(self.practitioner_screen, "Practitioner")
        self.tabs.addTab(self.clinics_screen, "Clinics")
        self.tabs.addTab(self.status_panel, "Status")
        self.setCentralWidget(self.tabs)
        # Smoke S1: opening the Recovery tab re-lists it (stat-only, nothing
        # decrypted), so the tab never opens on a list gone stale while hidden.
        self.tabs.currentChanged.connect(self._on_tab_changed)

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
        self.session_screen.session_resumed.connect(self._on_session_resumed)
        # Tasks 7.2 and 7.3: the phrase rules read every live window (a queued
        # GUI-thread delivery, beside the Transcript screen's own rendering).
        self.transcript_screen.live_window.connect(self._on_live_window)
        self.session_screen.session_retired.connect(self._on_session_retired)
        self.session_screen.session_discarded.connect(self.transcript_screen.clear_live_view)
        self.recovery_screen.session_removed.connect(self.forget_unreviewed)
        self.recovery_screen.review_requested.connect(self._on_review_requested)
        self.recovery_screen.expiry_warning.connect(self._on_expiry_warning)
        # The Recovery screen listed once before this connection existed: a
        # session already inside the 2-hour window is announced now.
        soon = models.expiring_soon(self.recovery_screen.unreviewed_infos(), time.time())
        if soon:
            self.statusBar().showMessage(models.expiry_warning_line(len(soon)))
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
        # Privacy-professional-controls D2: the body a review showed first is
        # kept as `generated.enc`, under the review's lease.
        self.note_screen.generated_shown.connect(self._on_generated_shown)
        # Draft-write Task 5.2 (Constraint 2): THE one entry to a Cliniko
        # write and its reconcile — pinned (`TestWriteSlot`) as this slot's
        # only connection.
        self.note_screen.write_requested.connect(self._on_write_requested)

    # --- the Chrome link (Task 4.5) ------------------------------------------

    def attach_chrome_link(self) -> ChromeBridge:
        """Build the Chrome bridge over this window's controller, Session
        screen and clinic registry (``app.main`` then hands it the pipe). A
        Replace key or Remove re-checks its bound report (D9)."""
        if self.chrome_bridge is None:
            bridge = ChromeBridge(
                self._controller,
                self.session_screen,
                self._clinic_registry,
                parent=self,
                reminders=self.reminders,
                open_review=self.open_unreviewed,
                latch=self._rate_limit_latch,
            )
            self.clinics_screen.clinics_changed.connect(bridge.on_clinics_changed)
            bridge.pause_cue.connect(self._show_pause_cue)
            bridge.set_hotkey_status(self.hotkey_status)
            bridge.set_system_pause_status(self.system_pause_status)
            bridge.set_lock_refusal(self._lock_refusal)
            self.chrome_bridge = bridge
        return self.chrome_bridge

    # --- the global hotkey (Task 7.1, D7) --------------------------------------

    @property
    def hotkey_status(self) -> HotkeyStatus:
        return self._hotkey.status if self._hotkey is not None else NOT_SET_UP

    def attach_hotkey(self, registrar: HotkeyRegistrar | None = None) -> HotkeyStatus:
        """Reserve the pause hotkey for this window (``app.main`` only; a
        test passes a fake ``registrar``). A refusal is shown on the status
        line and, through the bridge, in Chrome's side panel."""
        if self._hotkey is None:
            self._hotkey = GlobalHotkey(
                registrar if registrar is not None else Win32HotkeyRegistrar()
            )
        status = self._hotkey.register(int(self.winId()))
        if status.state == "failed":
            self.statusBar().showMessage(models.HOTKEY_FAILED_STATUS.format(chord=status.chord))
        if self.chrome_bridge is not None:
            self.chrome_bridge.set_hotkey_status(status)
        return status

    def detach_hotkey(self) -> None:
        """Give the chord back (on close and at quit; idempotent)."""
        if self._hotkey is not None:
            self._hotkey.unregister()
            if self.chrome_bridge is not None:
                self.chrome_bridge.set_hotkey_status(self._hotkey.status)

    def _on_hotkey_pressed(self) -> None:
        # A press queued before ``detach_hotkey`` is dropped: it acts only
        # while the chord is still reserved (round 42 PR-LOW-241).
        if self._hotkey is not None and self._hotkey.status.available:
            self.on_hotkey()

    def on_hotkey(self) -> None:
        """A press of the reserved chord: RECORDING pauses through
        ``pause_for`` (with its cue); PAUSED asks the Session screen's
        guarded Resume — the same check as its button and Chrome's Resume
        (Constraint 7), with no bypass — and a refusal is flashed here, since
        the practitioner is probably in another window. Anything else does
        nothing."""
        state = self._controller.state
        if state is SessionState.RECORDING:
            self.pause_for(PauseReason.HOTKEY)
            return
        if state is not SessionState.PAUSED or self.session_screen.is_busy:
            return
        if self.session_screen.on_resume():
            self.statusBar().showMessage(models.HOTKEY_RESUMED_STATUS)
            return
        self.statusBar().showMessage(self.session_screen.message_label.text())
        QApplication.alert(self)

    # --- suspend and lock notifications (D5 as amended 2026-09-28) ------------

    @property
    def system_pause_status(self) -> SystemPauseStatus:
        if self._system_events is None:
            return SYSTEM_PAUSE_NOT_SET_UP
        return self._system_events.status

    def attach_system_pause(
        self, registrar: SystemEventRegistrar | None = None
    ) -> SystemPauseStatus:
        """Ask Windows for this window's suspend (Modern-Standby aware) and
        session-lock notifications (``app.main`` only; a test passes a fake
        ``registrar``). Never raises; a refusal is shown on the status line
        and the Session screen (``SYSTEM_PAUSE_FAILED_LINES``)."""
        if self._system_events is None:
            self._system_events = SystemPauseWatch(
                registrar if registrar is not None else Win32SystemEventRegistrar()
            )
        status = self._system_events.register(int(self.winId()))
        if status.failed:
            self.statusBar().showMessage(models.SYSTEM_PAUSE_FAILED_LINES[status.failed[0]])
        if self.chrome_bridge is not None:
            self.chrome_bridge.set_system_pause_status(status)
        return status

    def detach_system_pause(self) -> None:
        """Give both registrations back (on close, at quit and after a
        failed start; idempotent)."""
        if self._system_events is not None:
            self._system_events.unregister()
            if self.chrome_bridge is not None:
                self.chrome_bridge.set_system_pause_status(self._system_events.status)

    @property
    def session_locked(self) -> bool:
        """The session locked and no unlock has been seen since."""
        return self._system_events is not None and self._system_events.locked

    def _lock_refusal(self) -> str | None:
        """The bridge's first Resume check (codex round 51 PR-MED-300):
        ``locked`` between a lock and the unlock, ``lock_unknown`` when a
        flag Windows was asked about could not be confirmed either way."""
        watch = self._system_events
        if watch is None:
            return None
        state = watch.lock_state()
        if state == "locked":
            return "locked"
        if state == "unknown":
            return "lock_unknown"
        return None

    def _on_session_locked(self) -> None:
        # A lock queued before ``detach_system_pause`` is dropped, like a
        # hotkey press: it acts only while the registration stands.
        if self._system_events is not None and self._system_events.status.lock == "on":
            self.pause_for(PauseReason.LOCKED)
            # Round 57 SEC-019 (D5 extended to the Practitioner tab,
            # practitioner decision 2026-09-28): a voice enrolment stops too —
            # Stop's own path, so nothing is saved unless the worker had
            # already passed its final check.
            self.practitioner_screen.on_stop()

    # --- the pause rule (Task 5.1, D5) ----------------------------------------

    def nativeEvent(self, eventType: object, message: object) -> object:  # noqa: N802, N803
        """D5: the machine suspending pauses a recording — the classic
        broadcast or, on a Modern Standby machine, the one Windows sends
        because ``attach_system_pause`` registered for it (either way the
        same ``PBT_APMSUSPEND``, handled here synchronously; a second finds
        the recording already paused). D5 as amended 2026-09-28: the session
        LOCKING (``WM_WTSSESSION_CHANGE`` / ``WTS_SESSION_LOCK``, only while
        registered) sets the lock flag at once — every Resume is refused
        until the unlock (codex round 51 PR-MED-300) — and is re-delivered as
        a queued call that pauses with ``PauseReason.LOCKED``; the unlock
        (``WTS_SESSION_UNLOCK``) only clears the flag. D7 (Task 7.1): a
        ``WM_HOTKEY`` for the chord this window reserved is re-delivered as
        a queued call to ``on_hotkey`` (only while it is reserved).

        Qt calls this for EVERY native message the window receives, so it
        must never raise into Qt's dispatch and must hand every message back
        to Qt's own handling. It returns ``(False, 0)`` — "not handled",
        exactly what ``QWidget::nativeEvent``'s default returns — WITHOUT
        calling the base: PySide6 refused ``super().nativeEvent`` a 64-bit
        message address ("called with wrong argument values", seen
        2026-09-28), and a real ``MSG*`` on 64-bit Windows is such an
        address. Qt does nothing with ``WM_HOTKEY`` itself, so the hotkey's
        message is answered the same way, and so is the session change.
        ``TestSuspendAndCue``, ``TestHotkeyWindow`` and ``TestLockWindow``
        drive real messages through Qt's dispatch in a child process."""
        try:
            head = _native_msg(eventType, message)
            if head is not None:
                if is_suspend_message(*head):
                    self.pause_for(PauseReason.SUSPEND)
                    self.practitioner_screen.on_stop()  # SEC-019: an enrolment stops too
                    if self._controller.state not in CAPTURING_STATES:
                        self._suspend_recheck_q.emit()  # SEC-021: maybe inside Start
                elif self._system_events is not None and self._system_events.lock_matches(*head):
                    # Codex round 51 PR-MED-300: refuse every Resume from
                    # this moment — before the queued pause, and before any
                    # command already queued behind this message runs.
                    self._system_events.note_lock()
                    self._session_locked_q.emit()
                elif self._system_events is not None and self._system_events.unlock_matches(
                    *head
                ):
                    self._system_events.note_unlock()  # resumes nothing
                elif self._hotkey is not None and self._hotkey.matches(*head):
                    self._hotkey_pressed_q.emit()
        except Exception:  # noqa: BLE001 - nothing may raise into Qt's dispatch
            pass
        return False, 0

    def _on_suspend_recheck(self) -> None:
        """Round 57 SEC-021: a suspend delivered re-entrantly INSIDE
        ``controller.start`` (a device open that pumps messages) read the old
        state — the controller's lock is an ``RLock`` — and paused nothing.
        Once that Start has returned, pause the recording it made. Fails safe:
        at IDLE or QUEUED ``pause_for`` does nothing, and a recording already
        paused is not paused again."""
        self.pause_for(PauseReason.SUSPEND)

    def pause_for(self, reason: PauseReason) -> None:
        """D5's ``pause_for`` for app-level reasons (suspend and the session
        lock; Phase 7's hotkey and spoken pause). The Chrome bridge applies it when attached
        (it owns the block); otherwise the same table pauses through the
        Session screen's slot."""
        if self.chrome_bridge is not None:
            self.chrome_bridge.pause_for(reason)
            return
        session = self._controller.session
        linked = session is not None and session.encounter_context is not None
        action = pause_action(self._controller.state, reason, linked=linked)
        if action.pause and self.session_screen.on_pause():
            self._show_pause_cue(models.pause_cue_text(reason.value, linked=linked))

    def _show_pause_cue(self, text: str) -> None:
        """D5: every pause shows a desktop cue — the status line, the Session
        screen's message, and a taskbar flash."""
        self.statusBar().showMessage(text)
        self.session_screen.show_notice(text)
        QApplication.alert(self)

    # --- the Unreviewed reminder index (Task 5.3, D6) ------------------------

    def _on_session_retired(self, previous: object) -> None:
        """A Start retired ``previous``: a linked, queued one waits for review
        in the reminder index (from its in-memory context — nothing is
        decrypted), under the reference it already had (D2)."""
        if not isinstance(previous, RecordingSession):
            return
        binding = self.note_screen.write_binding
        if binding is not None and binding.session_id == previous.session_id:
            # Draft-write round 34 LOW-004: a Start that FAILED after
            # retiring the session (H1 round 53 LOW-040) never reaches
            # `_on_session_started`'s clear, so the Note tab would stay bound
            # to a session that is no longer live; it reopens from Unreviewed.
            self.note_screen.clear()
        entry = reminder_entry(previous)
        if entry is not None:
            self.reminders.add(entry)
        # Smoke S1: the retired recording is Unreviewed now, so list it at
        # once. A stat-only listing (nothing is decrypted, Constraint 7) under
        # the unchanged custody exclusion; always on the GUI thread (emitted
        # synchronously by `SessionScreen._start`, called by the adopt path).
        self.recovery_screen.refresh()

    def _on_tab_changed(self, index: int) -> None:
        widget = self.tabs.widget(index)
        if widget is self.recovery_screen:
            self.recovery_screen.refresh()
        # Task 3.1: the Past sessions tab is re-listed each time it is opened,
        # and the opened entry's text and the listed names leave the widgets
        # and memory when it is left (round 16 LOW-008).
        if widget is self.past_sessions_screen:
            self.past_sessions_screen.refresh()
        else:
            self.past_sessions_screen.on_left()

    def _released_checkout_entry(self) -> ReminderEntry | None:
        """H1 round 53 LOW-040's sibling: the index entry of a RECOVERED
        linked session whose view is being replaced without a Complete or
        Discard — from the record its checkout already decrypted (nothing is
        decrypted here). It is Unreviewed from now on, exactly as the start-up
        rebuild would index it. An adopted session is live, not released."""
        checkout = self._checkout
        record = checkout.record
        context = record.context if record is not None else None
        if checkout.adopted or checkout.session_id is None or context is None:
            return None
        return ReminderEntry(context.clinic_id, context.treatment_note_id, checkout.session_id)

    def _index_released(self, entry: ReminderEntry | None, source: str) -> None:
        if entry is not None and entry.session_id == source:
            self.reminders.add(entry)
            self._controller.register_session_ref(source)

    def forget_unreviewed(self, session_id: str) -> None:
        """A retired session was completed, discarded or expired: drop its
        own index entry and its reference (D2, D6) — and only those."""
        self.reminders.remove(session_id)
        self._controller.forget_session_ref(session_id)

    def prune_reminders(self) -> None:
        """After a sweep: forget every indexed session whose key is gone
        (expired or removed), then prune the reference registry
        (``prune_session_refs``). A stat only — nothing is decrypted."""
        root = self.recovery_screen.sessions_root
        for session_id in self.reminders.session_ids():
            if not (root / session_id / KEY_FILENAME).is_file():
                self.forget_unreviewed(session_id)
        self.prune_session_refs()

    def prune_session_refs(self) -> None:
        """SIMP-016 (draft-write Task 4.2), run right after the reminder
        prune: forget every controller reference whose session is neither
        the live one nor still indexed — an unlinked or failed recording's
        ref, kept through retirement with no banner to serve (D2). The live
        and indexed sessions keep theirs; an expired session has already
        lost its reminder above, so it loses its ref here too."""
        keep = self._controller.live_session_ids() | self.reminders.session_ids()
        for session_id in self._controller.referenced_session_ids() - keep:
            self._controller.forget_session_ref(session_id)

    # --- Open for review (Task 5.4, D6; decided option (a)) --------------------

    def reconstruct_reminders(self) -> None:
        """Task 5.5 (D6), called ONCE by ``app.main`` after the start-up
        sweep: rebuild the reminder index from the sessions on disk — the one
        path besides a checkout that decrypts ``encounter.enc``, once per
        Unreviewed session (``models.reconstruct_reminder_entries``) — and
        give each indexed session a reference, so its banner can name it."""
        self.recovery_screen.refresh()
        for entry in models.reconstruct_reminder_entries(self.recovery_screen.unreviewed_infos()):
            self.reminders.add(entry)
            self._controller.register_session_ref(entry.session_id)

    def open_unreviewed(self, session_id: str) -> str | None:
        """Task 5.5: the Chrome banner's "Open for review" for exactly
        ``session_id`` (the bridge resolved its reference and found it in the
        index). The window comes forward — Windows may refuse the focus, so
        the taskbar flashes too — and the session opens as from its Recovery
        row. Returns None, or a ``CHROME_REFUSALS`` code."""
        info = next(
            (
                row
                for row in self.recovery_screen.unreviewed_infos()
                if row.session_id == session_id
            ),
            None,
        )
        if info is None:
            self.recovery_screen.refresh()
            info = next(
                (
                    row
                    for row in self.recovery_screen.unreviewed_infos()
                    if row.session_id == session_id
                ),
                None,
            )
        if info is None:
            return "session_changed"
        self._raise_window()
        return None if self._on_review_requested(info) else "cannot_open"

    def _raise_window(self) -> None:
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()
        QApplication.alert(self)

    def _on_review_requested(self, info: object) -> bool:
        """An Unreviewed row's "Open for review": the controller ADOPTS the
        session as the live queued session (``adopt_queued``, which decrypts
        its consent record — the checkout — and reads the transcript and any
        saved note before installing anything), then it opens on the path
        every live queued session uses. Every refusal is named on the row.
        True when the session opened."""
        if not isinstance(info, models.RecoverableSessionInfo):
            return False
        recovery = self.recovery_screen
        if self.is_writing:
            # D9: adopting would retire the session a draft write holds.
            recovery.show_message(models.write_line("write_in_flight"))
            self.tabs.setCurrentWidget(recovery)
            return False
        if self.transcript_screen.is_busy or self.note_screen.is_busy:
            recovery.show_message(models.REVIEW_OPEN_BUSY_LINE)
            self.tabs.setCurrentWidget(recovery)
            return False
        if self.session_screen.is_discarding:
            # Installation plan round 40 LOW-002: the Session tab's Discard runs
            # off the GUI thread while live transcription stops; an adoption
            # must never change which session that discard acts on.
            recovery.show_message(models.REVIEW_OPEN_DISCARDING_LINE)
            self.tabs.setCurrentWidget(recovery)
            return False
        if recovery.is_busy:
            # The Recovery screen's own button is disabled for this; the Chrome
            # route checks it here — the resume would land on the adopted
            # session's view (round 32 LOW-024).
            recovery.show_message(models.REVIEW_OPEN_RECOVERY_BUSY_LINE)
            self.tabs.setCurrentWidget(recovery)
            return False
        if self._transcript_source not in (None, "live"):
            recovery.show_message(
                "Finish the open recovered transcript first (Complete or Discard) before "
                "opening another recording."
            )
            self.tabs.setCurrentWidget(recovery)
            return False
        previous = self._controller.session
        try:
            session, opening = self._controller.adopt_queued(
                info.directory, models.read_for_review
            )
        except ReviewOpenRefused as exc:
            refusal = models.review_refusal_line(exc.reason, exc.__cause__)
        except WriteInFlightError:
            refusal = models.write_line("write_in_flight")
        except SessionControllerError as exc:
            refusal = f"This recording cannot be opened for review now: {exc}."
        except Exception:  # noqa: BLE001 - named, never a crash (nor its text: PR-LOW-044)
            refusal = (
                f"This recording cannot be opened for review: {models.CUSTODY_UNEXPECTED_REASON}."
            )
        else:
            if (
                previous is not None
                and not previous.is_terminal
                and previous.session_id != session.session_id
            ):
                self._on_session_retired(previous)  # D6: as a Start would retire it
            self.reminders.remove(session.session_id)  # in review now; re-added if retired
            self._open_adopted(session, opening, store_finished=info.store_finished)
            return True
        recovery.refresh()
        recovery.show_message(refusal)
        # The refusal is named on the row — show it (a Chrome banner's click
        # lands here with the window just brought forward).
        self.tabs.setCurrentWidget(recovery)
        return False

    def _open_adopted(
        self,
        session: RecordingSession,
        opening: models.ReviewOpening,
        *,
        store_finished: bool,
    ) -> None:
        """Show the adopted session exactly as a live queued one: the
        controller owns its custody (Complete/Discard), generation is offered
        — as "Regenerate (replaces the saved note)" when a saved note exists —
        and a saved note opens on the Note tab as it was saved.
        ``store_finished`` is the listing's footer read (a retired store is
        closed, so it cannot change): a crash-recovered store without one
        keeps the binding unfinished-store warning (codex round 34
        PR-MED-190)."""
        self._destroy_recovered_crypto()
        self._end_checkout_encounter()
        # The retired session's post-Save Note tab would act on whichever
        # session the controller tracks — this one now (the 5.3 rule).
        self.note_screen.clear()
        self.transcript_screen.show_document(
            opening.document,
            on_complete=self._complete_live,
            on_discard=self._controller.discard,
            store_finished=store_finished,
            can_generate=True,
            note_committed=opening.note is not None,
        )
        self._transcript_source = "live"
        self._begin_checkout(
            session.session_id,
            EncounterRecord(
                consent=session.consent,
                context=session.encounter_context,
                mode=session.mode,
                # Development-recordings D2: the adopted session's own copy
                # (taken from its record by ``adopt_queued``), as ``mode`` is.
                development_consent=session.development_consent,
            ),
            adopted=True,
        )
        self.recovery_screen.refresh()
        self.session_screen.refresh()
        note = opening.note
        if note is None:
            self.tabs.setCurrentWidget(self.transcript_screen)
            return
        self.note_screen.show_saved_note(
            note,
            opening.document,
            info=models.saved_note_line(note, self._load_note_config),
            copy_enabled=models.COPY_TO_CLINIKO_ENABLED,
            on_abandon=self._on_note_abandon,
            # D2: an adopted session writes through the same path as a live one.
            write_binding=self._live_write_binding(),
            mode=session.mode,  # pilot plan D5: as it was started (v1: normal)
        )
        self.tabs.setCurrentWidget(self.note_screen)

    def _load_note_config(self) -> NoteConfig:
        return load_note_config(self._config_root)

    def _on_expiry_warning(self, text: str) -> None:
        """D6: a recording is inside its last 2 hours — status line and a
        taskbar flash (no clinic, no patient)."""
        self.statusBar().showMessage(text)
        QApplication.alert(self)

    def _unreviewed_expiries(self) -> list[tuple[str, float | None]]:
        """D6's on-close list: every Unreviewed row plus the live queued
        session and an open recovered checkout — both excluded from the
        listing as protected (round 32 LOW-027) — each counted by the sweep
        from its creation."""
        self.recovery_screen.refresh()
        entries: list[tuple[str, float | None]] = [
            (info.session_id, info.expires_at)
            for info in self.recovery_screen.unreviewed_infos()
        ]
        extra: list[str] = []
        session = self._controller.session
        if session is not None and session.state is SessionState.QUEUED:
            extra.append(session.session_id)
        source = self._transcript_source
        if source is not None and source != "live":
            extra.append(source)
        root = self.recovery_screen.sessions_root
        for session_id in extra:
            entries.append((session_id, session_expires_at(root / session_id, time.time())))
        return entries

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

    def _build_live_transcriber(self) -> LiveTranscriber | None:
        """The controller calls this on the GUI thread inside ``start()``:
        build the worker whose posts the Transcript screen renders. It only
        builds — the view opens on ``session_started`` (round 7 LOW-003),
        which adopts this worker's token (round 57 SEC-022). None while the
        import warm-up runs (installation plan round 35 MED-001): the worker
        would import the stack beside the microphone stream; the recording
        runs without one and the empty view says so."""
        self._live_deferred = self._live_ready is not None and not self._live_ready()
        if self._live_deferred:
            return None
        return models.build_live_transcriber(on_window=self.transcript_screen.live_poster())

    def _enrolment_blocker(self) -> str | None:
        """The activity `begin_enrolment` cannot see for itself (D15): a
        benchmark run saturates every core and owns no microphone, but its
        worker must not overlap the enrolment capture. And (round 57
        SEC-019) the session lock: a Record press queued behind the lock
        message is refused like a Resume, until the unlock. And (installation
        plan round 37 LOW-002) the start-up import warm-up's bounded hold:
        an enrolment capture is a microphone stream like a recording's."""
        refusal = self._lock_refusal()
        if refusal is not None:
            return models.chrome_refusal_message(refusal)
        if self.session_screen.start_held():
            return models.START_GETTING_READY_MESSAGE
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

    def _writing_clinic(self) -> str | None:
        """The clinic a Cliniko draft write in flight writes to, for the
        Clinics tab's Replace key refusal (draft-write plan D9: the key read
        in hop 1 must stay the clinic's key for hop 2). Remove needs no
        second source: the writing session is always the LIVE one
        (``reserve_write`` admits only the live QUEUED session and every
        retiring action is refused while it is held), so
        ``_live_session_clinic`` already names its clinic. ``reserve_write``
        does not check linkage — an unlinked session names no clinic (None)
        and reads no key: the Write click (``_on_write_requested``) refuses
        it before anything is reserved, and ``writeback_context`` would
        refuse it again before any key is read."""
        writing = self._controller.writing_session_id()
        session = self._controller.session
        if writing is None or session is None or session.session_id != writing:
            return None
        return self._live_session_clinic()

    @property
    def is_writing(self) -> bool:
        """A Cliniko draft write holds the live session's custody (D9): true
        over the write's handlers' FULL span — from the Write click's
        ``reserve_write`` (the controller's marker, taken before the first
        worker; the job is recorded under it) until its last handler has
        released the reservation — and,
        momentarily, while the seen-mode Complete re-acquires one for
        ``complete_after_write`` (D6). Read by "Open for review"
        (``_on_review_requested``) and the close refusal; the Note tab, the
        Transcript row and the Recovery screen are blocked over the same
        span (``_set_writing``), and the Chrome bridge's pre-checks read the
        controller's reservation, which spans the same handlers."""
        return self._write_job is not None or self._controller.writing_session_id() is not None

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
        if self.session_screen.is_discarding:
            # Installation plan round 40 LOW-002: named before the recording
            # line below, which would ask for the Discard already under way.
            self.statusBar().showMessage(
                "A recording is being discarded - wait for it to finish before closing."
            )
            event.ignore()
            return
        if self._controller.state in CAPTURING_STATES:
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
        if self.is_writing:
            # Draft-write D9 (Task 5.2): the write-specific line, before the
            # generic busy branch — a hop's worker may be running, and its
            # handler must record the outcome and release the session.
            self.statusBar().showMessage(models.write_line("write_in_flight"))
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
            or (self.chrome_bridge is not None and self.chrome_bridge.is_busy)
        ):
            self.statusBar().showMessage(
                "Work in progress - wait for transcription, note generation, "
                "prose rendering, a benchmark, a clinic key check or a Cliniko "
                "note check to finish before closing."
            )
            event.ignore()
            return
        # Task 5.4 (D6): list the unreviewed recordings and when each expires.
        # Shown on a first close, which is refused; a second close inside
        # CLOSE_CONFIRM_SECONDS quits (a modal box would block every close).
        entries = self._unreviewed_expiries()
        if entries:
            now = time.monotonic()
            armed = self._close_armed_at
            if armed is None or not 0 <= now - armed <= models.CLOSE_CONFIRM_SECONDS:
                self._close_armed_at = now
                text = models.close_expiry_message(entries, time.time())
                self.statusBar().showMessage(text)
                self.recovery_screen.show_message(text)
                self.tabs.setCurrentWidget(self.recovery_screen)
                event.ignore()
                return
        self._close_armed_at = None
        # Release the idle level-monitor's device before the window goes away
        # (smoke round 21) — never leave a PortAudio stream running teardown.
        self.microphone_screen.stop_monitor()
        # Task 7.1: the chord goes back to Windows with the window, and so do
        # the suspend and lock notifications (D5 as amended 2026-09-28).
        self.detach_hotkey()
        self.detach_system_pause()
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
            on_complete=self._complete_live,
            on_discard=self._controller.discard,
            store_finished=True,
            can_generate=True,
        )
        # A recovered transcript this replaces loses its callbacks, so its
        # in-memory key copy is destroyed (round 42 LOW-006) and — Task 5.4,
        # replacing the PR-round-20 hold-until-restart residual — its checkout
        # is released (scoped, by id), so it is listed and swept again.
        self._destroy_recovered_crypto()
        entry = self._released_checkout_entry()
        self._end_checkout_encounter()
        source = self._transcript_source
        if source is not None and source != "live" and self._recovered_crypto is None:
            self.recovery_screen.release_checkout(source)
            self._index_released(entry, source)
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
        and no Start can interleave with the Session screen's own Discard: a
        Discard with no live worker runs synchronously on the GUI thread, and
        one that waits for live transcription (installation plan round 40
        LOW-002) runs on a worker thread while the Session screen refuses every
        Start (`on_start` / `start_linked`) and Chrome's Start is refused
        through `is_busy` (the controller deliberately admits a concurrent
        `start()` mid-discard — round 30 — but the GUI never issues one)."""
        self._destroy_recovered_crypto()
        entry = self._released_checkout_entry()
        self._end_checkout_encounter()
        source = self._transcript_source
        self._transcript_source = None
        if source is not None and source != "live":
            self.recovery_screen.release_checkout(source)
            self._index_released(entry, source)
        # Task 5.3 (D6): a Start at QUEUED retired the session a post-Save
        # Note tab still shows. Its "delete note and complete" acts on
        # WHICHEVER session the controller tracks — the new recording once it
        # queues — so the stale review goes now; the retired session reopens
        # from the Unreviewed section. (Start is refused while a review holds
        # the lease, so no unsaved review is ever dropped here.)
        self.note_screen.clear()
        self.transcript_screen.begin_live_view(ready=not self._live_deferred)
        # Phase 7: the phrase rules start afresh for the new recording.
        self._spoken_pause.reset()
        self._new_consultation.reset()

    # --- the phrase rules (Tasks 7.2, 7.3; D7, D8) ------------------------------

    def _on_session_resumed(self) -> None:
        """D7: nothing said before this Resume may pause the recording again
        — the cutoff is the captured audio so far (pauses add none)."""
        self._spoken_pause.note_resume(float(self._controller.recorded_seconds))

    def _on_live_window(self, payload: object) -> None:
        """One live window (GUI thread): "scribe pause" spoken after the last
        Resume pauses through ``pause_for`` (which does nothing unless the
        recording is running); a goodbye then a greeting raises the
        new-consultation WARNING, which changes nothing. The transcript keeps
        every word either way. Only the current Start's posts count (round 57
        SEC-022): a retired worker's late window reaches neither rule."""
        segments = self.transcript_screen.live_segments(payload)
        if segments is None:
            return
        if self._controller.state not in CAPTURING_STATES:
            return
        if self._spoken_pause.feed(segments):
            self.pause_for(PauseReason.SPOKEN)
        if self._new_consultation.feed(segments):
            self._raise_new_consultation()

    def _raise_new_consultation(self) -> None:
        session = self._controller.session
        if session is not None and self.chrome_bridge is not None:
            self.chrome_bridge.set_new_consultation_warning(session.session_id)
        self.statusBar().showMessage(models.NEW_CONSULTATION_WARNING_LINE)
        self.session_screen.show_notice(models.NEW_CONSULTATION_WARNING_LINE)
        QApplication.alert(self)

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
            # D5: the label is resolved at the click, before the Complete.
            on_complete=lambda: self._controller.complete_recovered(
                directory, crypto, label=self.keep_label_for(directory.name)
            ),
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
        record: EncounterRecord | None
        try:
            record = read_encounter_record(directory, crypto, directory.name)
        except EncounterUnavailable:
            record = None
        self._begin_checkout(directory.name, record)

    def _begin_checkout(
        self, session_id: str, record: EncounterRecord | None, *, adopted: bool = False
    ) -> None:
        """Hold ``record`` for the open session and re-verify a linked one
        (D4). An ADOPTED session (Task 5.4) passes the record its adoption
        already decrypted — never a second decrypt."""
        self._end_checkout_encounter()
        self._checkout = _CheckoutEncounter(session_id=session_id, record=record, adopted=adopted)
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
        latch = self._rate_limit_latch
        if latch.cooling(request.clinic.clinic_id, latch.clock()) is not None:
            # D13: the clinic is cooling after a 429 — answered as a 429 was
            # (the existing offline line), with no call; reopening the row
            # after the cooldown checks again.
            if request is self._checkout.request:
                self._checkout.result = rate_limited_result(request)
            return
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
        # D13 (PR-LOW-008): a real 429 cools the clinic for every caller —
        # recorded BEFORE any waiting check starts, whether or not this
        # result is still current (the cooldown's own answers never come
        # here: they make no call).
        if (
            isinstance(result, VerificationResult)
            and isinstance(result.outcome, UnverifiedOffline)
            and result.outcome.rate_limited
        ):
            latch = self._rate_limit_latch
            latch.record_429(result.request.clinic.clinic_id, latch.clock())
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
        self.transcript_screen.set_shadow_line(False)

    def _show_checkout_line(self) -> None:
        """On the Transcript screen — where opening a recovered session
        lands (round 20 LOW-014). Pilot plan Task 1.7: with the shadow line
        when the checked-out session is a shadow recording's (an unreadable
        record is one, D3)."""
        checkout = self._checkout
        if checkout.session_id is None:
            self.transcript_screen.set_link_line("")
            self.transcript_screen.set_shadow_line(False)
            return
        self.transcript_screen.set_shadow_line(
            self.session_mode_for(checkout.session_id) is not SessionMode.NORMAL
        )
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
        """Constraint 6 over the recovered checkout: None when no recovered
        session is checked out — and for an ADOPTED one (Task 5.4), which is
        the live session: ``live_writeback_target`` governs it. A test-only
        entry: the draft write builds its own subject in
        ``draft_write.prepare_write``; this stays because its tests cover
        the checkout's guard."""
        if self._checkout.session_id is None or self._checkout.adopted:
            return None
        subject = WritebackSubject.of_checkout(self._checkout.record, self._checkout.result)
        return writeback_context(subject, self._clinic_registry)

    def live_writeback_target(
        self, reverification: VerificationResult | None = None
    ) -> VerifiedTarget | WritebackRefused | None:
        """Constraint 6 over the live session: refused until
        ``reverification`` — a current check of the session's note, D4 —
        answers under the clinic's current rev (round 20 MED-012). None with
        no non-terminal session. A test-only entry: the draft write builds
        its own subject in ``draft_write.prepare_write``; this stays because
        its tests cover the live guard."""
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
        generation; this catch is the custody backstop, not the UX. A draft
        write's reservation (D9) also refuses this call, and that holds the
        same way: while a write runs, the Recovery screen is blocked and the
        Transcript row disabled (draft-write Task 5.2, ``_set_writing``), and
        the controller refuses a Start and an adoption by name. If a
        future caller CAN reach it while blocked, give the release path an
        explicit re-run rather than relying on the next view change."""
        if self._recovered_crypto is None:
            return
        try:
            self._controller.destroy_recovered_crypto(self._recovered_crypto)
        except (GenerationInProgressError, SessionActivityError):
            return
        self._recovered_crypto = None

    # --- the Past-sessions label and the generated note (privacy-
    # professional-controls D2 / D5) ------------------------------------------

    def keep_label_for(self, session_id: str) -> KeepLabel:
        """D5: the Past-sessions label for ``session_id``, resolved in the UI
        BEFORE its Complete, every source matched on the session id:

        1. the Chrome bridge's display from the Verified Start of the live
           session (the bridge is None when the pipe did not start);
        2. the bridge's re-verification of the linked live session;
        3. the checkout's re-verification (a recovered or adopted session)
           when its outcome is ``Verified``.

        Otherwise no name: "Name not available" for a linked (or unknown)
        recording, "Desktop recording (no Cliniko note)" for a desktop one —
        the kind comes from the live session's encounter context or the
        checkout's decrypted record. The name is never persisted at Start
        (``EncounterRecord`` stays ids-only); it lives in this label only.
        Pilot plan Task 1.6: the label is a shadow recording's whenever
        ``session_mode_for`` says so (fail closed, D3)."""
        name: str | None = None
        recording: Literal["linked", "desktop", "unknown"] = "unknown"
        clinic_id: str | None = None
        session = self._controller.session
        bridge = self.chrome_bridge
        if session is not None and session.session_id == session_id:
            context = session.encounter_context
            recording = "linked" if context is not None else "desktop"
            clinic_id = context.clinic_id if context is not None else None
            if bridge is not None:
                name = bridge.live_display_name(session_id)
                if name is None:
                    check = bridge.live_reverification()
                    if check is not None and isinstance(check.outcome, Verified):
                        name = check.outcome.display.patient_display_name
        checkout = self._checkout
        if checkout.session_id == session_id:
            record = checkout.record
            if recording == "unknown" and record is not None:
                context = record.context
                recording = "linked" if context is not None else "desktop"
                clinic_id = context.clinic_id if context is not None else None
            result = checkout.result
            if name is None and result is not None and isinstance(result.outcome, Verified):
                name = result.outcome.display.patient_display_name
        shadow = self.session_mode_for(session_id) is not SessionMode.NORMAL
        return keep_label(name, recording, clinic_id, shadow=shadow)

    def session_mode_for(self, session_id: str | None) -> SessionMode:
        """Pilot plan D1/D3: the mode of ``session_id`` — the live (or
        adopted) session's own, fixed at Start; a recovered checkout's from
        its decrypted record, SHADOW when that record could not be read; and
        SHADOW for anything else (fail closed). Ids only, no decrypt: the
        three authorised ``read_encounter_record`` callers already read it."""
        if session_id is None:
            return SessionMode.SHADOW
        session = self._controller.session
        if session is not None and session.session_id == session_id:
            return session.mode
        checkout = self._checkout
        if checkout.session_id == session_id:
            record = checkout.record
            return record.mode if record is not None else SessionMode.SHADOW
        return SessionMode.SHADOW

    def _live_mode(self) -> SessionMode:
        """The live session's mode (the Note tab's review and reopened saved
        note belong to it); SHADOW with no non-terminal live session."""
        session = self._controller.session
        if session is None or session.is_terminal:
            return SessionMode.SHADOW
        return session.mode

    def _complete_live(self) -> RecordingSession:
        """The live (or adopted) session's Complete, labelled at the click."""
        session = self._controller.session
        label = self.keep_label_for(session.session_id) if session is not None else None
        return self._controller.complete(label=label)

    def _on_generated_shown(self, body: object) -> None:
        """D2: keep the body the review showed first (and, before any edit,
        its first prose rendering) as ``generated.enc`` under the lease. A
        failure never stops the review; it is said on the status bar."""
        assert isinstance(body, models.GeneratedBody)
        kept = self.transcript_screen.keep_generated(body)
        # A review shown with no lease held (nothing to keep it under) is not
        # a failure to report; a refused write under the lease is.
        if not kept and self.transcript_screen.is_busy:
            self.statusBar().showMessage(models.GENERATED_NOT_KEPT_LINE)

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
            write_binding=self._live_write_binding(),
            # Pilot plan D5/D13: a shadow recording's note is display-only and
            # its Save teaches nothing.
            mode=self._live_mode(),
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

    def _on_transcript_closed(self, outcome: str) -> None:
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
            if outcome in ("completed", "discarded"):
                self.forget_unreviewed(source)  # D6: only this session's entry
            self.recovery_screen.release_checkout(source)
        else:
            self.recovery_screen.refresh()
        if outcome == "written":
            # Draft-write D6 (seen mode): the terminal line, after refresh().
            self.session_screen.show_notice(models.write_line("written_done"))
        # Peer round 44 PR-MED-026: a terminal exit that dropped queued
        # phrases stays on the Transcript screen so the appended sentence is
        # actually seen; every other close (ordinary Complete, Complete after
        # Save, an empty queue) lands on the Session screen as before.
        landing = self.transcript_screen if queued + rules > 0 else self.session_screen
        self.tabs.setCurrentWidget(landing)

    # --- the Cliniko draft write (draft-write Task 5.2; D2, D3, D5, D6, D9) ----

    def _live_write_binding(self) -> models.WriteBinding | None:
        """D2: the Note tab's binding for the live session's note — its id
        and whether it is linked (``encounter_context is not None``). None
        with no live session: Write is hidden."""
        session = self._controller.session
        if session is None or session.is_terminal:
            return None
        return models.WriteBinding(session.session_id, session.encounter_context is not None)

    def clinic_user_id(self, clinic_id: str) -> str | None:
        """The clinic registry's Cliniko ``user_id`` for ``clinic_id``, or
        None — what ``app.main`` registers as the controller's clinic-user
        resolver, so a linked Start's audit row names it (privacy-
        professional-controls D8). A registry read only; nothing contacts
        Cliniko."""
        record = self._clinic_registry.record(clinic_id)
        return record.user_id if record is not None else None

    def _on_write_requested(self, session_id: str) -> None:
        """THE slot for "Write draft to Cliniko" (D2, D3; Constraint 2 — a
        write and its reconcile start only here, and this slot's only
        connection is the Note tab's ``write_requested``). GUI thread, in
        order, each refusal named on the Note tab and taken before anything
        is reserved or sent:

        - a write already in flight; a click for a session that is no longer
          the live one (stale); a SHADOW recording (``shadow_session``, pilot
          plan D4 — before the unlinked line, which invites a Copy shadow
          mode refuses; recorded in the audit row like any pre-send refusal);
          an unlinked session (Constraint 10 — it never wrote, so it holds no
          record);
        - the write record, content-free (D5; ``models.write_record_block``,
          the Note tab's own mapping): unreadable → ``record_unreadable``,
          ``written`` → ``written_seen`` (seen mode: no network call — only
          Complete consumes it); an OPEN attempt makes every later refusal
          carry the ``write_uncertain`` prefix (PR-MED-017);
        - the session lock (the PR-MED-300 rule: a click queued behind the
          lock is refused); a recovery resume running
          (``recovery_busy``, PR-MED-023); a Validate / Replace key in flight
          for this clinic (``clinic_busy``, round 14 LOW-011 — the reverse
          arrival order of D9's Replace-key refusal); the latch's cooldown
          (``rate_limited``, D13); a clinic no longer set up;
        - ``reserve_write`` (D9 — BEFORE the first worker), then, under the
          reservation, the record, the saved note and its identity
          (``WriteStore.load`` through ``with_write_custody``) and
          ``refuse_before_read`` (mock note, D10; unreadable or ``written``
          record) — so those cases make no request;
        - hop 1 on a worker: ``read_for_write`` (ONE client call, the key
          read once, ONE request: the note read — D3 as amended by D15).

        Anything raised after the reservation releases it (R22-07)."""
        if self._write_job is not None:
            self._show_write_line(models.write_line("write_in_flight"))
            return
        session = self._controller.session
        if session is None or session.is_terminal or session.session_id != session_id:
            self._show_write_line(models.write_line("not_sent"))
            return
        if session.mode is not SessionMode.NORMAL:
            # Pilot plan D4: nothing reserved, read or sent — so no session
            # date is read either. Start wrote this session's row; only after
            # "Start a new audit record" (D9) does the update make a pre_audit
            # row, then dated by the audit clock and naming no mode (review
            # round 22).
            if self._audit is not None:
                self._audit.record_write_refusal(session_id, "shadow_session")
            self._show_write_line(models.write_line("shadow_session"))
            return
        context = session.encounter_context
        if context is None:
            # Before the record (the Note tab's order, ``models.write_control``):
            # an unlinked session never wrote, so it holds no record.
            self._show_write_line(models.write_line("unlinked"))
            return
        try:
            status = self._controller.write_record_status(session_id)
        except Exception:  # noqa: BLE001 - fail closed: the record may exist
            status = None
        blocked = models.write_record_block(status)
        if blocked is not None or status is None:
            self._show_write_line(blocked or models.write_line("record_unreadable"))
            return
        uncertain = status.open_attempt
        lock = self._lock_refusal()
        if lock is not None:
            self._show_write_line(
                models.write_prefixed(models.chrome_refusal_message(lock), uncertain=uncertain)
            )
            return
        if self.recovery_screen.is_busy:
            self._show_write_line(models.write_line("recovery_busy", uncertain=uncertain))
            return
        if self.clinics_screen.pending_clinic_id == context.clinic_id:
            self._show_write_line(models.write_line("clinic_busy", uncertain=uncertain))
            return
        latch = self._rate_limit_latch
        cooling = latch.cooling(context.clinic_id, latch.clock())
        if cooling is not None:
            self._show_write_line(
                models.write_line("rate_limited", uncertain=uncertain, seconds=cooling)
            )
            return
        self._write_seq += 1
        request = reverification_request(context, self._clinic_registry, seq=self._write_seq)
        if request is None:
            reason = models.writeback_refusal_line(WritebackRefusal.CLINIC_GONE)
            self._show_write_line(
                models.write_line("check_failed", uncertain=uncertain, reason=reason)
            )
            return
        try:
            reservation = self._controller.reserve_write(session_id)
        except WriteInFlightError:
            self._show_write_line(models.write_line("write_in_flight"))
            return
        except Exception:  # noqa: BLE001 - named, never a crash; nothing reserved
            self._show_write_line(models.write_line("not_sent", uncertain=uncertain))
            return
        try:
            store = self._write_store
            inputs = self._controller.with_write_custody(
                reservation, lambda directory, crypto: store.load(directory, crypto, session_id)
            )
            early = refuse_before_read(
                inputs.note,
                inputs.record,
                inputs.note_identity,
                channel=install_layout.channel(),
                allow_dev_writes=dev_writes_allowed(self._config_root),
                shadow=session.mode is not SessionMode.NORMAL,
            )
            if early is not None:
                if self._audit is not None:
                    # Flow 2 (round 7 LOW-001): every pre-send refusal records
                    # its fixed code, dated under the still-held reservation.
                    self._audit.record_write_refusal(
                        session_id, early.name, created_at=self._write_created_at(reservation)
                    )
                reservation.release()
                self._show_write_line(models.write_refusal_line(early))
                return
            job = _WriteJob(reservation, session_id, request, inputs, uncertain)
            self._write_job = job
            self._set_writing(True)
            self._show_write_line(models.write_line("checking"))
            registry = self._clinic_registry
            # The holder pattern (`ui/clinics.py`): the worker takes the
            # request; the thread object keeps nothing of it.
            holder = [request]

            def hop1() -> Hop1Result:
                return read_for_write(
                    holder.pop(),
                    key_store=registry.key_store,
                    transport=registry.transport,
                )

            task = TaskThread(hop1, self)
            task.succeeded.connect(self._after_hop1)
            task.failed.connect(self._on_write_task_failed)
            job.task = task
            task.start()
        except Exception:  # noqa: BLE001 - R22-07: never left reserved
            job_now = self._write_job
            if job_now is not None and job_now.reservation is reservation:
                self._end_write(job_now, models.write_line("not_sent", uncertain=uncertain))
            else:
                reservation.release()
                self._show_write_line(models.write_line("not_sent", uncertain=uncertain))

    def _after_hop1(self, result: object) -> None:
        """Hop 1 answered (GUI thread): ``_prepare_attempt`` decides the
        click (D3's order, Task 3.4) and puts the ``attempting`` row on disk
        (Constraint 5), then hop 2 — the PATCH alone, in its OWN client call
        (``write_for_click``, D3) — is dispatched. A refusal, an
        already-landed write or anything raised ends the click here, with
        the reservation released (R22-07: ``unknown`` once an attempt row
        was written, else ``not_sent``)."""
        job = self._write_job
        if job is None or job.stage != "hop1":
            return  # not this click's answer (defensive: one write at a time)
        try:
            job.stage = "prepare"
            self._join_write_task(job)
            prepared = self._prepare_attempt(job, result)
            if isinstance(prepared, str):
                self._end_write(job, prepared)
                return
            self._show_write_line(models.write_line("writing"))
            registry = self._clinic_registry
            holder = [(job.request, prepared)]

            def hop2() -> WriteOutcome:
                hop_request, hop_prepared = holder.pop()
                return write_for_click(
                    hop_request,
                    hop_prepared,
                    key_store=registry.key_store,
                    transport=registry.transport,
                )

            task = TaskThread(hop2, self)
            task.succeeded.connect(self._finish_write)
            task.failed.connect(self._on_write_task_failed)
            job.task = task
            job.stage = "hop2"
            task.start()
        except Exception:  # noqa: BLE001 - R22-07: never left reserved
            self._end_write(job, self._write_failure_line(job))

    def _prepare_attempt(self, job: _WriteJob, result: object) -> PreparedWrite | str:
        """The GUI-thread step between the hops (D3; Task 3.4's order inside
        ``prepare_write``). A 429 on hop 1 is recorded in the latch (D13) and
        shown as ``rate_limited``; so is a cooldown another path recorded
        while hop 1 ran (the latch is read again here, before anything is
        stored — PR-MED-038). Returns the prepared write once its
        ``attempting`` row is on disk, or the line that ends the click: a
        refusal, or ``written_seen`` when reconcile found this session's
        earlier write in Cliniko (recorded ``written``, no PATCH — D5)."""
        uncertain = job.uncertain
        if not isinstance(result, Hop1Result):
            return models.write_line("not_sent", uncertain=uncertain)
        clinic_id = job.request.clinic.clinic_id
        latch = self._rate_limit_latch
        if result.rate_limited:
            latch.record_429(clinic_id, latch.clock())
            seconds = latch.cooling(clinic_id, latch.clock()) or RATE_LIMIT_COOLDOWN_SECONDS
            return models.write_line("rate_limited", uncertain=uncertain, seconds=seconds)
        # Codex round 35 PR-MED-038 (D13: "a 429 seen by one path must stop
        # the others"): the Chrome bridge or the checkout may have recorded
        # a 429 for this clinic while hop 1 ran, so the latch is read again
        # before any record is stored or hop 2 is dispatched.
        cooling = latch.cooling(clinic_id, latch.clock())
        if cooling is not None:
            return models.write_line("rate_limited", uncertain=uncertain, seconds=cooling)
        session = self._controller.session
        if session is None or session.session_id != job.session_id:
            return models.write_line("not_sent", uncertain=uncertain)
        inputs = job.inputs
        prepared = prepare_write(
            result,
            consent=session.consent,
            context=session.encounter_context,
            clinics=self._clinic_registry,
            record=inputs.record,
            note=inputs.note,
            note_identity=inputs.note_identity,
            profile=self._write_profile(inputs.note),
            channel=install_layout.channel(),
            allow_dev_writes=dev_writes_allowed(self._config_root),
            shadow=session.mode is not SessionMode.NORMAL,
        )
        if isinstance(prepared, WriteRefusal):
            # Task 1.4 (round 1 PR-MED-005): the refusal's FIXED code, never
            # the display line; best-effort (C2).
            if self._audit is not None:
                self._audit.record_write_refusal(
                    job.session_id,
                    prepared.name,
                    created_at=self._write_created_at(job.reservation),
                )
            return models.write_refusal_line(prepared)
        if isinstance(prepared, AlreadyWritten):
            earlier = inputs.record
            if not isinstance(earlier, WriteRecord):
                return models.write_line("write_uncertain")  # unreachable: reconcile needs one
            try:
                self._store_write_record(job, reconciled_record(earlier, now=_utc_now()))
            except Exception:  # noqa: BLE001 - still open on disk: the next click reconciles
                return models.write_line("unknown")
            return models.write_line("written_seen")
        attempt = attempt_record(prepared, now=_utc_now())
        self._store_write_record(job, attempt)  # on disk BEFORE hop 2 (Constraint 5)
        job.attempt = attempt
        return prepared

    def _finish_write(self, outcome: object) -> None:
        """Hop 2 answered (GUI thread): the outcome by the HTTP answer only
        (D5 — a 200 is never relabelled), a 429 into the latch (D13), the
        record finished on disk, the reservation RELEASED (seen mode, D6:
        Complete re-acquires one later — nothing completes here), and the
        line: ``written_seen`` / ``finalised_before_write`` / the ``not_taken``
        cause / ``unknown``. A record that could not be finished stays
        ``attempting`` on disk — read as ``unknown`` and reconciled by the
        next click — so the line is ``unknown`` then."""
        job = self._write_job
        if job is None or job.stage != "hop2":
            return
        line = models.write_line("unknown")
        try:
            self._join_write_task(job)
            answer = outcome if isinstance(outcome, WriteOutcome) else WriteOutcome("unknown")
            if answer.rate_limited:
                latch = self._rate_limit_latch
                latch.record_429(job.request.clinic.clinic_id, latch.clock())
            attempt = job.attempt
            if attempt is None:
                raise RuntimeError("hop 2 ran without an attempt row")  # unreachable
            self._store_write_record(job, finished_record(attempt, answer, now=_utc_now()))
            line = models.write_outcome_line(answer)
        except Exception:  # noqa: BLE001 - the attempt row stays: unknown, reconciled next
            line = models.write_line("unknown")
        finally:
            self._end_write(job, line)

    def _on_write_task_failed(self, _message: str) -> None:
        """A hop's worker raised (neither hop's function raises for Cliniko's
        answers; the message is never shown). After hop 2's dispatch the
        request may have left, so it is recorded ``unknown``; before it,
        nothing was sent."""
        job = self._write_job
        if job is None:
            return
        if job.stage == "hop2":
            self._finish_write(WriteOutcome("unknown"))
            return
        try:
            self._join_write_task(job)
        finally:
            self._end_write(job, self._write_failure_line(job))

    def _store_write_record(self, job: _WriteJob, record: WriteRecord) -> None:
        """``write.enc`` through the held reservation ONLY (D9: the write's
        one accessor to its session files).

        THE one boundary every durable write-record transition passes
        through — the attempt, a reconciled ``written``, the finish and its
        ``unknown`` fallback — so it is also where the audit row learns the
        write (privacy-professional-controls Task 1.4): the attempt number,
        the outcome and, once ``written``, when. Only AFTER the record is on
        disk (a record that failed to store is not a transition), and
        best-effort — ``AuditLog.update`` never raises, so the audit can
        never change what the write does or reports (C2). A refused one also
        records Cliniko's fixed refusal code (round 6 LOW-006)."""
        store = self._write_store
        session_id = job.session_id
        audit = self._audit

        def stored(directory: Path, crypto: SessionCrypto) -> float | None:
            store.store(directory, crypto, session_id, record)
            # D8 (round 6 LOW-007): the session's creation time, read in the
            # same custody hold, dates a pre-audit session's first row.
            return audit_created_at(directory) if audit is not None else None

        created_at = self._controller.with_write_custody(job.reservation, stored)
        if audit is not None:
            audit.record_write(
                session_id,
                attempt=record.attempt,
                outcome=record.outcome,
                finished_at=record.finished_at,
                refusal=record.refusal,
                created_at=created_at,
            )

    def _write_created_at(self, reservation: WriteReservation) -> float | None:
        """D8 (round 6 LOW-007): the writing session's creation time, through
        the held write custody, for a pre-audit session's first row. Never
        raises — None lets the audit use its own clock."""
        try:
            return self._controller.with_write_custody(
                reservation, lambda directory, _crypto: audit_created_at(directory)
            )
        except Exception:  # noqa: BLE001 - a date, never a reason the write changes
            return None

    def _write_failure_line(self, job: _WriteJob) -> str:
        """R22-07: ``unknown`` once an attempt row was written, else
        ``not_sent`` (nothing can have reached Cliniko)."""
        if job.attempt is not None:
            return models.write_line("unknown")
        return models.write_line("not_sent", uncertain=job.uncertain)

    @staticmethod
    def _join_write_task(job: _WriteJob) -> None:
        if job.task is not None:
            job.task.finish()
            job.task = None

    def _end_write(self, job: _WriteJob, line: str) -> None:
        """The click's last step, whatever happened: release the
        reservation (idempotent), forget the job, unblock the screens and
        show ``line``."""
        try:
            job.reservation.release()
        finally:
            if self._write_job is job:
                self._write_job = None
            self._set_writing(False)
            self._show_write_line(line)

    def _set_writing(self, active: bool) -> None:
        """D9: while a write holds the live session, the Note tab's Write
        is disabled (and the tab busy), the Transcript row disabled and the
        Recovery screen blocked — in both arrival orders with a recovery
        resume (PR-MED-023: the Write click refuses ``recovery_busy``) — and
        the Session screen's Start re-read (it reads the controller's writing
        marker; H1 round 45 LOW-002)."""
        self.note_screen.set_write_in_flight(active)
        self.transcript_screen.set_write_blocked(active)
        self.recovery_screen.set_write_blocked(active)
        self.session_screen.refresh()

    def _show_write_line(self, line: str) -> None:
        self.note_screen.show_write_line(line)
