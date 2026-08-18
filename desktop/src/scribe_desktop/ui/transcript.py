"""Transcript-inspection view: decrypted transcript display (uncertainty
marks + speaker labels visible) with the Phase-2 Complete and Discard
actions (plan Flow 2 custody ordering), EXTENDED in Phase 7 with the
pre-generation clinician-role and template-profile controls (Task 7.5) and
the Generate action that composes a note draft on a worker thread (Task 7.2).

The transcript is DISPLAYED only. It is never written to disk, logged, or
copied anywhere by this widget; the display is cleared as soon as the session
is completed or discarded.

Generation ownership (Task 7.2): this screen owns the lease lifecycle. The
lease is acquired BEFORE the compose ``TaskThread`` starts and released only
after the GUI-thread ``write_note`` succeeds (or the compose/abandon path
cleans up) — the whole operation, never just the worker. ``write_note`` runs
on the GUI thread via ``SessionController.with_generation_custody`` (a
worker-thread write could interleave with a GUI-thread Complete, which a
button guard cannot prevent). Generation is LIVE-path only: the recovered
path has no QUEUED controller session for the scoped op, so its transcript
view shows Complete/Discard only.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.note import GeneratedNote, speaker_role
from scribe_desktop.note_config import NoteConfig, NoteConfigError, load_note_config
from scribe_desktop.note_fill import detect_prefill_candidates
from scribe_desktop.session import GenerationLease
from scribe_desktop.session_store import write_note
from scribe_desktop.transcription import TranscriptDocument
from scribe_desktop.ui import models
from scribe_desktop.ui.tasks import TaskThread


def _clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()


class TranscriptScreen(QWidget):
    # Emitted after a successful Complete ("completed") or Discard ("discarded").
    closed = Signal(str)
    # Emitted with a models.NoteGenerationResult once a draft is composed.
    draft_ready = Signal(object)
    # Emitted True/False as the generation lease is acquired/released, so the
    # main window can keep view swaps unreachable during generation (the
    # Task 6.3 residue guard).
    generation_active_changed = Signal(bool)

    def __init__(
        self,
        controller: models.SessionControllerLike | None = None,
        *,
        note_generator_factory: Callable[..., Callable[..., models.NoteGenerationResult]] = (
            models.build_note_generator
        ),
        config_loader: Callable[[], NoteConfig] = load_note_config,
        recovery_busy_provider: Callable[[], bool] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._note_generator_factory = note_generator_factory
        self._config_loader = config_loader
        # Round 33 MED-001: a generation lease must NEVER be held while a
        # recovery resume is in flight — otherwise the resume's completion
        # (`_on_recovered`) swaps the transcript view and releases the lease
        # mid-generation. `set_generation_blocked` already blocks a resume
        # STARTING during a lease; this is the symmetric guard that blocks a
        # generation STARTING during a resume, so the two flows are mutually
        # exclusive and `_on_recovered` can never fire while a lease is held.
        self._recovery_busy_provider = recovery_busy_provider
        self._on_complete: Callable[[], object] | None = None
        self._on_discard: Callable[[], object] | None = None

        self._can_generate = False
        self._config: NoteConfig | None = None
        self._lease: GenerationLease | None = None
        self._generation_result: models.NoteGenerationResult | None = None
        self._note_review_state = models.NoteReviewState()
        # Round 36 PR-MED-002: a note.enc is committed on disk (from a
        # successful save_note) and not yet completed/discarded. The Complete
        # gate's has_note must agree with THIS, not only the current in-memory
        # review — a cancelled regeneration leaves the prior note.enc on disk.
        self._note_committed = False
        self._role_buttons: dict[str, QRadioButton] = {}
        self._role_group: QButtonGroup | None = None
        self._task: TaskThread | None = None

        self.warning_label = QLabel()
        self.warning_label.setStyleSheet("color: #b00020; font-weight: bold;")
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()

        self.transcript_view = QPlainTextEdit()
        self.transcript_view.setReadOnly(True)
        self.transcript_view.setPlaceholderText("No transcript loaded.")
        # PR round 18 (PR5->MED, defense-in-depth at the same-user boundary):
        # no selection/copy — Windows clipboard history / cloud clipboard
        # sync must never receive transcript text from this view.
        self.transcript_view.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )

        self.legend_label = QLabel("Uncertain words are shown as [word?] - verify them.")

        # --- Task 7.5: pre-generation role + template controls -------------
        self.generate_box = QGroupBox("Generate note")
        generate_layout = QVBoxLayout(self.generate_box)
        generate_layout.addWidget(
            QLabel("Confirm the clinician and template before generating a note:")
        )
        self._role_box = QVBoxLayout()
        generate_layout.addWidget(QLabel("Clinician (choose the speaker who is the clinician):"))
        generate_layout.addLayout(self._role_box)
        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Template profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(lambda *_: self._update_controls())
        profile_row.addWidget(self.profile_combo, 1)
        generate_layout.addLayout(profile_row)
        prefill_row = QHBoxLayout()
        prefill_row.addWidget(QLabel("Prefill region:"))
        self.prefill_combo = QComboBox()
        prefill_row.addWidget(self.prefill_combo, 1)
        generate_layout.addLayout(prefill_row)
        self.generate_button = QPushButton("Generate note")
        self.generate_button.setToolTip(
            "Compose a draft note from this transcript. Enabled once both the "
            "clinician and the template profile are confirmed."
        )
        self.generate_button.clicked.connect(self.generate)
        generate_layout.addWidget(self.generate_button)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.hide()
        generate_layout.addWidget(self.progress_bar)
        self.generate_box.hide()

        self.complete_button = QPushButton("Complete")
        self.complete_button.setToolTip(
            "Verify the encrypted transcript, then cryptographically delete "
            "the session (audio becomes unrecoverable)."
        )
        self.discard_button = QPushButton("Discard")
        self.complete_button.clicked.connect(self.on_complete)
        self.discard_button.clicked.connect(self.on_discard)

        self.message_label = QLabel()
        # Round 48 PR-LOW-002: PLAIN TEXT, always. This label renders
        # exception detail (config validation errors, save/compose failures),
        # which reproduces USER-AUTHORED input - config text a clinician
        # edited, or note text. AutoText would interpret anything markup-like
        # in it as rich text. Same discipline as the proposal excerpt label.
        self.message_label.setTextFormat(Qt.TextFormat.PlainText)
        self.message_label.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.addWidget(self.complete_button)
        buttons.addWidget(self.discard_button)
        buttons.addStretch(1)

        layout = QVBoxLayout()
        layout.addWidget(self.warning_label)
        layout.addWidget(self.transcript_view)
        layout.addWidget(self.legend_label)
        layout.addWidget(self.generate_box)
        layout.addLayout(buttons)
        layout.addWidget(self.message_label)
        self.setLayout(layout)
        self._update_controls()

    # --- loading -----------------------------------------------------------

    def show_document(
        self,
        document: TranscriptDocument,
        *,
        on_complete: Callable[[], object],
        on_discard: Callable[[], object],
        store_finished: bool = True,
        can_generate: bool = False,
    ) -> None:
        """Display a decrypted transcript with its custody callbacks.

        ``on_complete`` must implement the binding Flow 2 ordering
        (fsync -> verify decrypt round-trip -> delete key custody);
        ``on_discard`` deletes the key FIRST. Both are supplied by the
        caller so live (controller) and recovered (custody-primitive)
        sessions share this one view. ``can_generate`` shows the Task 7.5
        generation controls — LIVE sessions only (the scoped generation op
        needs a QUEUED controller session)."""
        self._reset_generation_state()
        self._on_complete = on_complete
        self._on_discard = on_discard
        self._note_review_state = models.NoteReviewState()
        self.transcript_view.setPlainText(models.format_transcript_text(document))
        self.message_label.setText("")
        if store_finished:
            self.warning_label.hide()
        else:
            # Binding Step-10 note (PR-HIGH-007 residual).
            self.warning_label.setText(models.UNFINISHED_STORE_WARNING)
            self.warning_label.show()
        self._can_generate = can_generate and self._controller is not None
        if self._can_generate:
            self._populate_generation_controls(document)
        self.generate_box.setVisible(self._can_generate)
        self._update_controls()

    def _populate_generation_controls(self, document: TranscriptDocument) -> None:
        _clear_layout(self._role_box)
        self._role_buttons = {}
        if self._role_group is not None:
            self._role_group.deleteLater()
        self._role_group = QButtonGroup(self)
        preselection = speaker_role(document)
        suggested = preselection.preselected_clinician_speaker
        quotes = models.speaker_quotations(document)
        for speaker, quote in quotes.items():
            marker = " (suggested)" if speaker == suggested else ""
            radio = QRadioButton(f'{speaker}{marker}: "{quote}"')
            self._role_group.addButton(radio)
            self._role_buttons[speaker] = radio
            radio.toggled.connect(lambda *_: self._update_controls())
            self._role_box.addWidget(radio)
        # None is pre-checked: role confirmation is mandatory and explicit.
        self.profile_combo.clear()
        self.prefill_combo.clear()
        try:
            config = self._config_loader()
        except NoteConfigError as exc:
            self._config = None
            # Round 48 PR-LOW-002: surface the ACTIONABLE detail. The loader
            # builds a message naming the file and the failing field precisely
            # so a clinician editing plaintext config can repair it — and this
            # was the one path that threw it away, showing only the exception
            # CLASS at the moment it is most needed (Generate is about to be
            # disabled). The detail is local-UI-only and rendered plain-text
            # (see `message_label`); it must never be logged.
            self.message_label.setText(
                f"Note config could not be loaded, so note generation is "
                f"unavailable. You can still Complete or Discard.\n\n"
                f"{type(exc).__name__}: {exc}"
            )
            self._can_generate = False
            return
        self._config = config
        self.profile_combo.addItem("- choose template profile -", None)
        for profile in config.template_profiles:
            self.profile_combo.addItem(profile.display_name, profile.template_profile_id)
        self.prefill_combo.addItem("No prefill", None)
        for candidate in detect_prefill_candidates(document, config):
            self.prefill_combo.addItem(candidate.display_name, candidate.prefill_id)

    def _reset_generation_state(self) -> None:
        self._release_lease()
        self._generation_result = None
        self._config = None
        self._note_review_state = models.NoteReviewState()
        # Reset the committed-note flag ONLY on a new session (show_document)
        # or a terminal action (_clear) — NOT on cancel_note_review, which
        # keeps a prior committed note.enc on disk (round 36 PR-MED-002).
        self._note_committed = False
        self.progress_bar.hide()

    def _update_controls(self) -> None:
        loaded = self._on_complete is not None
        generating = self._lease is not None
        # Generation controls (Task 7.5): Generate is unreachable without both
        # a confirmed clinician role and a confirmed template profile.
        both_confirmed = self._role_confirmed() and self._profile_confirmed()
        can_generate_now = (
            self._can_generate
            and not generating
            and self._config is not None
            and not self._recovery_in_flight()
        )
        self.generate_button.setEnabled(can_generate_now and both_confirmed)
        self.profile_combo.setEnabled(can_generate_now)
        self.prefill_combo.setEnabled(can_generate_now)
        for radio in self._role_buttons.values():
            radio.setEnabled(can_generate_now)
        # Complete gating (Flow 2): refused while generating, while a proposal
        # is unconfirmed, while an error is unresolved, or while a review
        # warning is unacknowledged. Round 36 PR-MED-002: a committed note.enc
        # on disk (`_note_committed`) counts as a note even when the current
        # in-memory review was cancelled — so has_note agrees with disk and
        # "no note" is asserted only when no note.enc exists. A committed note
        # is always fully ratified (Save requires acknowledgement), so it is
        # safe to complete.
        state = self._note_review_state
        merged = replace(
            state,
            generating=generating,
            has_note=state.has_note or self._note_committed,
            note_saved=state.note_saved or self._note_committed,
        )
        reason = models.complete_block_reason(merged)
        self.complete_button.setEnabled(loaded and reason is None)
        self.discard_button.setEnabled(loaded and not generating)
        if loaded and reason is not None:
            self.complete_button.setToolTip(reason)
        else:
            self.complete_button.setToolTip(
                "Verify the encrypted transcript, then cryptographically delete "
                "the session (audio becomes unrecoverable)."
            )

    def _clear(self) -> None:
        self._on_complete = None
        self._on_discard = None
        self.transcript_view.setPlainText("")
        self.warning_label.hide()
        self._can_generate = False
        self.generate_box.hide()
        self._reset_generation_state()
        self._update_controls()

    # --- Task 7.5 selection accessors --------------------------------------

    def _selected_role(self) -> str | None:
        for speaker, radio in self._role_buttons.items():
            if radio.isChecked():
                return speaker
        return None

    def _role_confirmed(self) -> bool:
        return self._selected_role() is not None

    def selected_profile_id(self) -> str | None:
        data = self.profile_combo.currentData()
        return data if isinstance(data, str) else None

    def _profile_confirmed(self) -> bool:
        return self.selected_profile_id() is not None

    def _selected_prefill_id(self) -> str | None:
        data = self.prefill_combo.currentData()
        return data if isinstance(data, str) else None

    def set_role(self, speaker: str) -> None:
        radio = self._role_buttons.get(speaker)
        if radio is not None:
            radio.setChecked(True)

    def set_profile(self, profile_id: str | None) -> None:
        index = self.profile_combo.findData(profile_id)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)

    def set_prefill(self, prefill_id: str | None) -> None:
        index = self.prefill_combo.findData(prefill_id)
        if index >= 0:
            self.prefill_combo.setCurrentIndex(index)

    # --- Task 7.2 generation -----------------------------------------------

    @property
    def is_busy(self) -> bool:
        """True while a note generation lease is held — the compose worker is
        running or the draft is under review. Closing and view swaps must
        wait (the Task 6.3 residue guard); a worker write must not race a
        Complete."""
        return self._lease is not None

    def _recovery_in_flight(self) -> bool:
        return self._recovery_busy_provider is not None and self._recovery_busy_provider()

    def generate(self) -> None:
        controller = self._controller
        if controller is None or self._lease is not None:
            return
        role = self._selected_role()
        profile_id = self.selected_profile_id()
        if role is None or profile_id is None:
            return  # Generate is disabled until both are confirmed; defensive.
        # Round 33 MED-001 click-time guard (fail closed, like the recovery
        # screen's stale-selection re-check): a resume that began after the
        # last _update_controls must not slip a lease in beside it.
        if self._recovery_in_flight():
            self.message_label.setText(
                "A recovery is in progress - wait for it to finish before "
                "generating a note."
            )
            return
        try:
            lease = controller.begin_generation()
        except Exception as exc:  # noqa: BLE001 - surfaced, never crashes the UI
            self.message_label.setText(
                f"Cannot generate a note now: {type(exc).__name__}: {exc}"
            )
            return
        self._lease = lease
        self.generation_active_changed.emit(True)
        self.progress_bar.show()
        self.message_label.setText("Generating note locally...")
        generator = self._note_generator_factory(
            clinician_speaker=role,
            template_profile_id=profile_id,
            prefill_id=self._selected_prefill_id(),
        )

        def job() -> models.NoteGenerationResult:
            return controller.with_generation_custody(lease, generator)

        task = TaskThread(job, self)
        task.succeeded.connect(self._on_composed)
        task.failed.connect(self._on_compose_failed)
        self._task = task
        self._update_controls()
        task.start()

    def _end_compose_task(self) -> None:
        if self._task is not None:
            self._task.finish()
            self._task = None

    def _on_composed(self, result: object) -> None:
        self._end_compose_task()
        self.progress_bar.hide()
        assert isinstance(result, models.NoteGenerationResult)
        self._generation_result = result
        self.message_label.setText("Note generated - review it on the Note tab.")
        self.draft_ready.emit(result)
        self._update_controls()

    def _on_compose_failed(self, message: str) -> None:
        self._end_compose_task()
        self.progress_bar.hide()
        self._release_lease()
        self.message_label.setText(
            f"Note generation failed ({message}). The transcript is unchanged; "
            "you can try again or complete without a note."
        )
        self._update_controls()

    def _release_lease(self) -> None:
        if self._lease is not None and self._controller is not None:
            self._controller.end_generation(self._lease)
        if self._lease is not None:
            self._lease = None
            self.generation_active_changed.emit(False)
            self._update_controls()

    # --- driven by the Note tab (relayed through the main window) ----------

    def save_note(self, note: GeneratedNote) -> None:
        """Write the reviewed note on the GUI thread via the scoped, lease-
        aware op (Task 7.2 — write_note NEVER on the worker thread), then
        release the lease. Raises on failure so the Note tab surfaces it and
        the lease stays held for a retry."""
        controller = self._controller
        lease = self._lease
        result = self._generation_result
        if controller is None or lease is None or result is None:
            raise RuntimeError("no note generation is in progress")
        config = result.config
        controller.with_generation_custody(
            lease, lambda directory, crypto: write_note(directory, crypto, note, config)
        )
        self._note_committed = True  # note.enc is on disk (round 36 PR-MED-002)
        self._release_lease()

    def abandon_note_and_complete(self) -> None:
        """The Note tab's delete-note-and-complete-without-one exit. Routes by
        lease state (round 36 PR-MED-001 — a stale post-Save action must never
        consume a LATER generation's lease):

        - PRE-save (a lease is held): complete UNDER the held lease and release
          it only AFTER success (round 35 PR-MED-001 — a completion failure
          keeps the lease + review held).
        - POST-save (no lease, note committed): delete the committed note.enc
          and complete via the guarded non-leased path (refused while a
          regeneration is in flight).

        A stale post-Save Note tab cannot reach here for a LATER generation:
        the main window clears the Note tab when a new generation starts, so
        this method always acts on the current review's lease/committed
        state. Raises on failure so the Note tab surfaces it."""
        controller = self._controller
        if controller is None:
            raise RuntimeError("no controller")
        lease = self._lease
        if lease is not None:
            controller.complete_without_note(lease)  # pre-save: raises -> lease + review held
        else:
            controller.complete_deleting_saved_note()  # post-save: no lease, guarded
        # Success: _clear() releases any local lease mirror + emits
        # generation_active_changed(False), unblocking recovery, and resets
        # the committed-note flag (the session is now terminal).
        self._clear()
        self.message_label.setText(
            "Session completed without a note (transcript verified, key destroyed)."
        )
        self.closed.emit("completed")

    def cancel_note_review(self) -> None:
        """Non-destructive escape from a note review (round 35 PR-MED-003):
        discard only the IN-MEMORY draft and release the held lease, WITHOUT
        touching ``note.enc``, transcript custody, or session state — the
        QUEUED transcript and session key are retained so the clinician can
        regenerate. Reachable only after the draft is presented (the Note tab
        shows only once the compose worker has returned), so releasing the
        lease here is safe. Resets the note-review state so a stale note
        cannot later re-enable Complete, and re-enables Generate."""
        self._release_lease()
        self._generation_result = None
        self._note_review_state = models.NoteReviewState()
        self._update_controls()

    def set_note_review_state(self, state: models.NoteReviewState) -> None:
        self._note_review_state = state
        self._update_controls()

    # --- Phase-2 custody actions -------------------------------------------

    def on_complete(self) -> None:
        if self._on_complete is None:
            return
        try:
            self._on_complete()
        except Exception as exc:  # noqa: BLE001 - key custody kept on any failure
            # Round 42 LOW-001: state only what THIS action verified — the
            # Complete primitive deleted nothing on failure, but the key may
            # be gone for another reason (e.g. the 24 h sweep at expiry).
            self.message_label.setText(
                f"Complete failed: {type(exc).__name__}: {exc}. "
                "No key deletion was performed by this action; if the "
                "session is still within its 24-hour window it remains "
                "available."
            )
            return
        self._clear()
        self.message_label.setText(
            "Session completed: transcript verified and the session key "
            "destroyed (cryptographic deletion)."
        )
        self.closed.emit("completed")

    def on_discard(self) -> None:
        if self._on_discard is None:
            return
        try:
            self._on_discard()
        except Exception as exc:  # noqa: BLE001
            self.message_label.setText(f"Discard failed: {type(exc).__name__}: {exc}")
            return
        self._clear()
        self.message_label.setText("Session discarded (audio cryptographically deleted).")
        self.closed.emit("discarded")
