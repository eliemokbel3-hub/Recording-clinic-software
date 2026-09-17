"""Note review tab (Phase 3A, Tasks 7.1 + 7.6; practitioner-profile plan Phase 5).

The clinician's review surface for a generated note. It renders the composed
note (canonical-section order, provenance visibly distinguished, one bullet
per assertion — NEVER assembled prose), the per-proposal confirm/decline
controls showing the EXACT text that will be inserted, and the checker
warnings GROUPED and SUMMARISED (warning fatigue is this phase's top risk),
with blocking errors kept DISTINCT from review warnings. Task 7.6 keeps the
full uncertainty-marked transcript visible BESIDE the note through the whole
review, so a low-confidence phrase the note omitted is still reachable.

It also carries the consent Critical Constraint's third clause (Task 7.7):
a standing, unconditional reminder that this app never ticks, writes or
proposes Cliniko's Informed Consent ATTESTATION CHECKBOX, which must be
ticked by hand. Round 54 PR-LOW-001 narrowed this sentence: it used to say
"Informed Consent is never written, ticked, or proposed", which is broader
than the structure enforces — what is unmappable is an
``attestation_checkbox`` TARGET, while consent speech may legitimately
populate the canonical free-text ``consent`` section and another profile may
map that section to a free-text target (see the rationale on
``models.CONSENT_MANUAL_REMINDER``, corrected for the same reason at round
47). The reminder is not a warning — nothing acknowledges or suppresses it —
and it survives ``clear()``, because it states what the app never does rather
than anything about a particular note.

Review edits (practitioner-profile plan D14, Tasks 5.1 / 5.1b). An explicit
"Edit the note" control group beside the transcript panel lets the clinician
ADD a whole transcript utterance to a section, REMOVE a line the router
placed, MOVE one to another section, and UNDO any of those until Save. The
edits SUBTRACT or RE-ROUTE the transcript's own lines only: an addition is
one whole utterance as a ``transcript``-provenance assertion with contiguous
coordinates (Check 1 reconstructs it byte-identically) under the router's
own ownership rule (``note.admissible_sections`` — a clinician-owned section
admits only the confirmed clinician's non-question lines), an utterance
already anywhere in the note is refused, and there is no free-text editing.
Every edit goes through the one content-change path — acknowledgements
cleared, the note un-saved, re-finalised over the WORKING draft
(``models.working_draft``) — so every check runs on the edited note and a
stale acknowledgement cannot survive a change (PR-MED-010). After Save the
edits are frozen like proposal decisions. The transcript panel itself stays
a non-interactive text box.

Phrase learning (D9 as amended 2026-09-16, Task 5.2). After an add or a move
of one of the practitioner's OWN lines — ``note.spoken_by_confirmed_clinician``,
so another speaker's line never reaches the learner — and only while the
learning status, re-read at that add or move, says learning is on (a readable
profile, the CURRENT consent version, the opt-in ticked), the line's leading
content tokens become a
candidate phrase; ``note_config.refuse_learning_candidate`` (the enforcing
control) refuses one carrying a name-like, numeric, date-shaped or
medication-shaped source token, a phrase already among the cues is noted, and
an accepted candidate is QUEUED on this screen. The queue is written ONLY on
Save (``note_config.append_user_cues``): an add undone before Save, a
removal, a move's remove leg and a cancelled or abandoned review teach
nothing. The learning status is re-read at Save, so a profile deleted or
opted out mid-review writes nothing.

Clinical-content discipline (Critical Constraints, design-system):
- The transcript panel is display-only (``NoTextInteraction``) ALWAYS, and is
  cleared with the rest of the tab whenever the review ends (``clear()`` on
  Complete, Discard, cancel, a new transcript or a new generation); an accepted
  window close ends the process — ``MainWindow.closeEvent`` refuses to close
  while a review is busy and calls no separate tab-clear (round 70 PR-LOW-013).
- The note is the RATIFIED copyable surface, but only once the Task 9.1
  shipping gate passes: copy is bound to ``models.COPY_TO_CLINIKO_ENABLED``,
  which ships False, so copy is DISABLED and the note panel is display-only
  until that recorded decision flips.
- Nothing here logs or persists clinical text. Confirmation evidence
  (``shown_text_digest``) is computed from the text the widget ACTUALLY
  rendered — read back from the proposal label, never copied from the
  proposal — so a rendering bug produces evidence ``finalise_note`` refuses.
  The one thing this tab writes outside the session store is a learned
  PHRASE — the practitioner's own words, by their consent — to their cue file.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    ConfirmationDecision,
    GeneratedNote,
    NoteAssertion,
    NoteDraft,
    NoteSectionKey,
    ProposalResolution,
    admissible_sections,
    content_tokens,
    finalise_note,
    first_matching_section,
    is_interrogative,
    manual_assertion_id,
    reconstruct_span_text,
    spoken_by_confirmed_clinician,
    text_digest,
    whole_utterance_assertion,
)
from scribe_desktop.note_config import (
    NoteConfig,
    NoteConfigError,
    append_user_cues,
    propose_learning_phrase,
    refuse_learning_candidate,
)
from scribe_desktop.transcription import TranscriptDocument
from scribe_desktop.ui import models


def _clear_layout(layout: QLayout) -> None:
    """Remove and delete every widget a rebuildable panel holds."""
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()


class NoteScreen(QWidget):
    """The Note tab. Driven by ``begin_review`` and its callbacks; all view
    logic lives in ``ui.models`` so this widget stays thin and its state is
    offscreen-testable."""

    # Emitted after learned phrases were WRITTEN on Save, so the Practitioner
    # tab can refresh its lists (Task 5.3).
    learned_phrases_changed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config_root: Path | None = None,
        learning_status_provider: Callable[[], models.LearningStatus] | None = None,
    ) -> None:
        super().__init__(parent)
        self._draft: NoteDraft | None = None
        self._document: TranscriptDocument | None = None
        self._config: NoteConfig | None = None
        self._copy_enabled: bool = False
        self._on_save: Callable[[GeneratedNote], None] | None = None
        self._on_abandon: Callable[[], None] | None = None
        self._on_cancel: Callable[[], None] | None = None
        self._on_state_changed: Callable[[models.NoteReviewState], None] | None = None

        # Per-proposal review state.
        self._resolutions: dict[str, Literal["confirmed", "declined"]] = {}
        self._rendered_excerpt: dict[str, str] = {}  # what each row actually showed
        self._state_labels: dict[str, QLabel] = {}
        self._proposal_buttons: list[QPushButton] = []
        self._acknowledged: set[str] = set()
        self._note: GeneratedNote | None = None
        self._note_saved = False

        # Review edits (D14) and the learning queue (D9 as amended). A screen
        # constructed WITHOUT a learning status provider never reads the
        # profile store and reports learning as unavailable: the main window
        # supplies the provider over its profile root (tests stay off the
        # default store — the PR-REG-005 rule).
        self._config_root = config_root
        self._learning_status_provider = learning_status_provider
        self._learning = models.LearningStatus(False, models.LEARNING_NO_PROFILE_HINT)
        self._removed: set[str] = set()
        self._manual: dict[str, NoteAssertion] = {}
        self._learning_queue: dict[str, tuple[NoteSectionKey, str]] = {}
        self._working: NoteDraft | None = None
        self._line_widgets: list[QWidget] = []

        # --- Task 7.6: the transcript, always beside the note --------------
        self.transcript_view = QPlainTextEdit()
        self.transcript_view.setReadOnly(True)
        self.transcript_view.setPlaceholderText("No transcript loaded.")
        self.transcript_view.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        transcript_panel = QWidget()
        transcript_layout = QVBoxLayout(transcript_panel)
        transcript_layout.addWidget(
            QLabel("Full transcript (uncertain words shown as [word?]):")
        )
        transcript_layout.addWidget(self.transcript_view)

        # --- the "Edit the note" control group (Tasks 5.1 / 5.1b) ----------
        self.utterance_combo = QComboBox()
        self.utterance_combo.currentIndexChanged.connect(lambda *_: self._refresh_section_combo())
        self.section_combo = QComboBox()
        self.add_line_button = QPushButton("Add line to section")
        self.add_line_button.setToolTip(
            "Add the chosen transcript line, word for word, to the chosen section. "
            "Only sections that line may enter are offered; Undo removes it until Save."
        )
        self.add_line_button.clicked.connect(self._on_add_clicked)
        add_row = QHBoxLayout()
        add_row.addWidget(QLabel("Line:"))
        add_row.addWidget(self.utterance_combo, stretch=1)
        add_row.addWidget(QLabel("to:"))
        add_row.addWidget(self.section_combo, stretch=1)
        add_row.addWidget(self.add_line_button)
        self.lines_header = QLabel("Lines in the note - remove, move or undo:")
        self._lines_box = QVBoxLayout()
        lines_scroll = QScrollArea()
        lines_scroll.setWidgetResizable(True)
        lines_content = QWidget()
        lines_content.setLayout(self._lines_box)
        lines_scroll.setWidget(lines_content)
        self.learning_label = QLabel()
        self.learning_label.setTextFormat(Qt.TextFormat.PlainText)
        self.learning_label.setWordWrap(True)
        # PLAIN TEXT: this line quotes a learned phrase and loader errors.
        self.edit_status_label = QLabel()
        self.edit_status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.edit_status_label.setWordWrap(True)
        self.edit_group = QGroupBox("Edit the note")
        edit_layout = QVBoxLayout()
        edit_layout.addLayout(add_row)
        edit_layout.addWidget(self.lines_header)
        edit_layout.addWidget(lines_scroll)
        edit_layout.addWidget(self.learning_label)
        edit_layout.addWidget(self.edit_status_label)
        self.edit_group.setLayout(edit_layout)
        transcript_layout.addWidget(self.edit_group)

        # --- the note review side -----------------------------------------
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)

        # Task 7.7 (round 45 MED-001): the consent Critical Constraint's third
        # clause. Static and unconditional — never cleared, never
        # acknowledgeable, never config-dependent (see the constant's comment
        # in ui.models). It states what the app never does, so it must be
        # readable on an empty tab as well as beside a note.
        self.consent_reminder_label = QLabel(models.CONSENT_MANUAL_REMINDER)
        self.consent_reminder_label.setWordWrap(True)
        self.consent_reminder_label.setStyleSheet("font-weight: bold;")

        self.blocking_header = QLabel("Cannot save the note yet:")
        self.blocking_header.setStyleSheet("color: #b00020; font-weight: bold;")
        self.blocking_header.hide()
        self._blocking_box = QVBoxLayout()

        self.review_header = QLabel("Review before completing:")
        self.review_header.setStyleSheet("font-weight: bold;")
        self.review_header.hide()
        self._review_box = QVBoxLayout()
        self.acknowledge_all_button = QPushButton("Acknowledge all review warnings")
        self.acknowledge_all_button.clicked.connect(self._acknowledge_all)
        self.acknowledge_all_button.hide()

        self.note_body = QPlainTextEdit()
        self.note_body.setReadOnly(True)
        self.note_body.setPlaceholderText("No note generated.")

        self.proposals_header = QLabel("Proposed additions - confirm or decline each:")
        self.proposals_header.hide()
        self._proposals_box = QVBoxLayout()

        self.save_button = QPushButton("Save note")
        self.save_button.setToolTip(
            "Verify and store the note for this session. Enabled once every "
            "proposed line is confirmed or declined, every review warning is "
            "acknowledged, and no blocking warning remains. Phrases queued for "
            "learning are written here and nowhere else."
        )
        self.save_button.clicked.connect(self.save)
        self.cancel_button = QPushButton("Cancel review and regenerate")
        self.cancel_button.setToolTip(
            "Discard this draft note and return to the Transcript screen to "
            "generate again. The recording and session are kept; nothing is "
            "deleted."
        )
        self.cancel_button.clicked.connect(self.cancel_review)
        self.abandon_button = QPushButton("Delete note and complete without one")
        self.abandon_button.setToolTip(
            "Discard this note and complete the session with no note attached."
        )
        self.abandon_button.clicked.connect(self.abandon)
        self.copy_button = QPushButton("Copy note")
        self.copy_button.clicked.connect(self._copy_note)

        self.message_label = QLabel()
        # Round 48 PR-LOW-002: PLAIN TEXT, always. This label renders
        # exception detail (config validation errors, save/compose failures),
        # which reproduces USER-AUTHORED input - config text a clinician
        # edited, or note text. AutoText would interpret anything markup-like
        # in it as rich text. Same discipline as the proposal excerpt label.
        self.message_label.setTextFormat(Qt.TextFormat.PlainText)
        self.message_label.setWordWrap(True)

        note_side = QWidget()
        note_layout = QVBoxLayout(note_side)
        note_layout.addWidget(self.info_label)
        note_layout.addWidget(self.consent_reminder_label)
        note_layout.addWidget(self.blocking_header)
        note_layout.addLayout(self._blocking_box)
        note_layout.addWidget(self.review_header)
        note_layout.addLayout(self._review_box)
        note_layout.addWidget(self.acknowledge_all_button)
        note_layout.addWidget(QLabel("Note:"))
        note_layout.addWidget(self.note_body)
        note_layout.addWidget(self.proposals_header)
        proposals_scroll = QScrollArea()
        proposals_scroll.setWidgetResizable(True)
        proposals_content = QWidget()
        proposals_content.setLayout(self._proposals_box)
        proposals_scroll.setWidget(proposals_content)
        note_layout.addWidget(proposals_scroll)
        buttons = QHBoxLayout()
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.abandon_button)
        buttons.addWidget(self.copy_button)
        buttons.addStretch(1)
        note_layout.addLayout(buttons)
        note_layout.addWidget(self.message_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(transcript_panel)
        splitter.addWidget(note_side)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        outer = QVBoxLayout(self)
        outer.addWidget(splitter)

        self._update_controls()  # -> _apply_copy_binding (copy off until a ratified note)

    # --- lifecycle ---------------------------------------------------------

    def begin_review(
        self,
        result: models.NoteGenerationResult,
        *,
        copy_enabled: bool = models.COPY_TO_CLINIKO_ENABLED,
        on_save: Callable[[GeneratedNote], None],
        on_abandon: Callable[[], None],
        on_cancel: Callable[[], None] | None = None,
        on_state_changed: Callable[[models.NoteReviewState], None] | None = None,
        template_profile_id: str | None = None,
    ) -> None:
        """Load a fresh draft for review. ``result`` carries the draft, the
        config it was composed under, and the on-disk transcript — all three
        used so finalisation stays digest-consistent (``models`` docstring).
        """
        self.clear()
        self._draft = result.draft
        self._document = result.document
        self._config = result.config
        self._copy_enabled = copy_enabled
        self._on_save = on_save
        self._on_abandon = on_abandon
        self._on_cancel = on_cancel
        self._on_state_changed = on_state_changed
        self._refresh_learning_status()

        self.transcript_view.setPlainText(models.format_transcript_text(result.document))
        self.info_label.setText(
            "  ".join(
                models.config_report_lines(result.config, template_profile_id)
            )
        )
        self._build_proposal_rows()
        self._refinalise()  # -> _update_controls -> _apply_copy_binding

    def clear(self) -> None:
        """Clear all plaintext and review state. Called when a different
        transcript or a new generation replaces this note, on cancel, and
        when the transcript closes on Complete or Discard (Task 7.1/7.3);
        an accepted window close is NOT a caller — it ends the process
        (round 71 PR-LOW-017). The learning queue dies here too: a review
        that ends without Save teaches nothing."""
        self._draft = None
        self._document = None
        self._config = None
        self._on_save = None
        self._on_abandon = None
        self._on_cancel = None
        self._on_state_changed = None
        self._resolutions.clear()
        self._rendered_excerpt.clear()
        self._state_labels.clear()
        self._proposal_buttons.clear()
        self._acknowledged.clear()
        self._note = None
        self._note_saved = False
        self._removed.clear()
        self._manual.clear()
        self._learning_queue.clear()
        self._working = None
        self.transcript_view.setPlainText("")
        self.note_body.setPlainText("")
        self.info_label.setText("")
        self.message_label.setText("")
        self.learning_label.setText("")
        self.edit_status_label.setText("")
        self.utterance_combo.clear()
        self.section_combo.clear()
        _clear_layout(self._lines_box)
        self._line_widgets.clear()
        _clear_layout(self._proposals_box)
        _clear_layout(self._blocking_box)
        _clear_layout(self._review_box)
        self.proposals_header.hide()
        self.blocking_header.hide()
        self.review_header.hide()
        self.acknowledge_all_button.hide()
        self._update_controls()

    def _read_learning_status(self) -> models.LearningStatus:
        provider = self._learning_status_provider
        if provider is None:
            return models.LearningStatus(False, models.LEARNING_NO_PROFILE_HINT)
        return provider()

    def _refresh_learning_status(self) -> models.LearningStatus:
        """Re-read the learning gate and show it. Called at review start, at
        every add or move (round 34 LOW-003: a practitioner who turns
        learning on or off mid-review on the Practitioner tab must not meet a
        stale gate or a stale line) and again at Save."""
        self._learning = self._read_learning_status()
        self._render_learning_line()
        return self._learning

    def _render_learning_line(self) -> None:
        """The learning line: the off-reason, or — while phrases are queued —
        the exact control that writes them (live smoke 2026-09-17: the queue
        was mistaken for the outcome and the review left without Save note)."""
        status = self._learning
        if self._draft is None:
            self.learning_label.setText("")  # a cleared tab shows no stale status
        elif not status.enabled:
            self.learning_label.setText(status.reason or "")
        elif self._learning_queue and not self._note_saved:
            self.learning_label.setText(models.learning_queued_line(len(self._learning_queue)))
        else:
            self.learning_label.setText(models.LEARNING_ON_LINE)

    # --- proposal rows -----------------------------------------------------

    def _build_proposal_rows(self) -> None:
        assert self._draft is not None
        for proposal in self._draft.note_proposals:
            rendered = models.render_proposal(proposal)
            row = QFrame()
            row.setFrameShape(QFrame.Shape.StyledPanel)
            row_layout = QVBoxLayout(row)
            heading = QLabel(f"{rendered.section_title} - {rendered.provenance_label}")
            heading.setStyleSheet("font-weight: bold;")
            row_layout.addWidget(heading)
            # PLAIN TEXT so the label shows the excerpt literally and reads
            # back byte-identically for the shown-text digest.
            excerpt = QLabel(rendered.excerpt)
            excerpt.setTextFormat(Qt.TextFormat.PlainText)
            excerpt.setWordWrap(True)
            row_layout.addWidget(excerpt)
            # The digest is computed from what the widget RENDERED, not from
            # the proposal (a rendering bug must be refusable — note.py).
            self._rendered_excerpt[proposal.proposal_id] = excerpt.text()
            row_layout.addWidget(QLabel(rendered.attribution))
            state_label = QLabel()
            self._state_labels[proposal.proposal_id] = state_label
            row_layout.addWidget(state_label)
            confirm = QPushButton("Confirm")
            confirm.clicked.connect(
                lambda _=False, pid=proposal.proposal_id: self.confirm_proposal(pid)
            )
            decline = QPushButton("Decline")
            decline.clicked.connect(
                lambda _=False, pid=proposal.proposal_id: self.decline_proposal(pid)
            )
            retract = QPushButton("Retract (undo decision)")
            retract.clicked.connect(
                lambda _=False, pid=proposal.proposal_id: self.retract_proposal(pid)
            )
            actions = QHBoxLayout()
            actions.addWidget(confirm)
            actions.addWidget(decline)
            actions.addWidget(retract)
            actions.addStretch(1)
            row_layout.addLayout(actions)
            self._proposal_buttons.extend((confirm, decline, retract))
            self._proposals_box.addWidget(row)
        self.proposals_header.setVisible(bool(self._draft.note_proposals))

    # --- resolution / acknowledgement --------------------------------------

    def confirm_proposal(self, proposal_id: str) -> None:
        self._set_resolution(proposal_id, "confirmed")

    def decline_proposal(self, proposal_id: str) -> None:
        self._set_resolution(proposal_id, "declined")

    def retract_proposal(self, proposal_id: str) -> None:
        """Withdraw a decision, returning the proposal to pending — the
        explicit retract-and-refinalise control (Task 7.1)."""
        if proposal_id in self._resolutions:
            del self._resolutions[proposal_id]
            self._after_content_change()

    def _set_resolution(
        self, proposal_id: str, decision: Literal["confirmed", "declined"]
    ) -> None:
        if proposal_id not in self._rendered_excerpt:
            return
        self._resolutions[proposal_id] = decision
        self._after_content_change()

    def _after_content_change(self) -> None:
        # THE content-change path (PR-MED-010): a proposal decision OR a
        # review edit invalidates prior acknowledgements and un-saves the
        # note: the clinician acknowledges a STABLE note, then saves.
        self._acknowledged.clear()
        self._note_saved = False
        self._refinalise()

    def _acknowledge(self, code: str) -> None:
        self._acknowledged.add(code)
        self._refresh_warnings()
        self._update_controls()  # acknowledgement changes copy readiness (PR-MED-002)
        self._emit_state()

    def _acknowledge_all(self) -> None:
        note = self._note
        if note is None:
            return
        summary = models.summarise_warnings(note.note_warnings)
        for group in summary.review:
            self._acknowledged.add(group.code)
        self._refresh_warnings()
        self._update_controls()  # acknowledgement changes copy readiness (PR-MED-002)
        self._emit_state()

    # --- review edits (D14: add / remove / move / undo) ---------------------

    @property
    def _edits_open(self) -> bool:
        return self._draft is not None and self._document is not None and not self._note_saved

    def _set_edit_status(self, message: str) -> None:
        self.edit_status_label.setText(message)

    def _segments_in_note(self) -> set[int]:
        working = self._working
        if working is None:
            return set()
        present: set[int] = set()
        for section in working.note_sections:
            for assertion in section.note_assertions:
                coords = assertion.note_span.source_coords
                if assertion.provenance == "transcript" and coords is not None:
                    present.add(coords.segment_index)
        return present

    def eligible_utterances(self) -> tuple[models.UtteranceChoice, ...]:
        """The utterances the chooser offers: not already in the working
        note, with the sections each may enter (the ownership rule)."""
        draft, document = self._draft, self._document
        if draft is None or document is None:
            return ()
        return models.eligible_utterances(
            document, clinician_speaker=draft.clinician_speaker, in_note=self._segments_in_note()
        )

    def editable_lines(self) -> tuple[models.EditableLine, ...]:
        """The line-editor rows: the provider's transcript lines with their
        remove/move state, then the manual additions."""
        draft, document = self._draft, self._document
        if draft is None or document is None:
            return ()
        return models.editable_lines(
            draft, document, removed=self._removed, additions=self._manual
        )

    def learning_queue(self) -> tuple[tuple[NoteSectionKey, str], ...]:
        """What Save would learn, in queue order (a read-only view)."""
        return tuple(self._learning_queue.values())

    def _allowed_sections(self, segment_index: int) -> tuple[NoteSectionKey, ...]:
        draft, document = self._draft, self._document
        assert draft is not None and document is not None
        segment = document.transcript_segments[segment_index]
        return admissible_sections(
            CANONICAL_SECTION_KEYS,
            speaker=segment.speaker,
            clinician_speaker=draft.clinician_speaker,
            text=reconstruct_span_text(segment.transcript_words),
        )

    def add_line(self, segment_index: int, section_key: NoteSectionKey) -> bool:
        """Add the whole utterance at ``segment_index`` to ``section_key`` as
        a ``transcript`` assertion (id ``m<segment>``). Refused — with the
        reason on the status line and nothing changed — after Save, for a
        segment already anywhere in the working note, for a segment with no
        quotable text, and for a section the ownership rule does not admit.
        Returns whether the line was added."""
        if not self._edits_open:
            self._set_edit_status("The note is saved - edits are closed.")
            return False
        document = self._document
        assert document is not None
        if not 0 <= segment_index < len(document.transcript_segments):
            self._set_edit_status("That line is not in the transcript.")
            return False
        if segment_index in self._segments_in_note():
            self._set_edit_status("That line is already in the note.")
            return False
        if section_key not in self._allowed_sections(segment_index):
            self._set_edit_status(
                f"That line cannot go in {models.section_title(section_key)}: "
                "clinician-owned sections take only the confirmed clinician's "
                "statements."
            )
            return False
        segment = document.transcript_segments[segment_index]
        assertion = whole_utterance_assertion(
            manual_assertion_id(segment_index),
            section_key,
            segment_index=segment_index,
            speaker=segment.speaker,
            words=segment.transcript_words,
        )
        if assertion is None:
            self._set_edit_status("That line has no words to add.")
            return False
        self._manual[assertion.assertion_id] = assertion
        self._set_edit_status(
            f"Added to {models.section_title(section_key)}. Undo removes it until Save."
        )
        self._consider_learning(assertion)
        self._after_content_change()
        return True

    def remove_line(self, assertion_id: str) -> bool:
        """Subtract a provider-routed line (D14). Reversible with ``undo_line``
        until Save; any omission warning it raises is acknowledgeable."""
        if not self._edits_open:
            self._set_edit_status("The note is saved - edits are closed.")
            return False
        if assertion_id in self._manual:
            return self.undo_line(assertion_id)
        if not self._provider_line_exists(assertion_id) or assertion_id in self._removed:
            return False
        self._removed.add(assertion_id)
        self._set_edit_status("Line removed. Undo restores it until Save.")
        self._after_content_change()
        return True

    def move_line(self, assertion_id: str, section_key: NoteSectionKey) -> bool:
        """Move a line to another section: remove + add under the ownership
        rule (D14). For a provider line the provider's assertion is subtracted
        and the utterance re-added as ``m<segment>``; for a manual line its
        section changes. The add leg is the one the learner sees."""
        if not self._edits_open:
            self._set_edit_status("The note is saved - edits are closed.")
            return False
        segment_index = self._segment_of(assertion_id)
        if segment_index is None:
            return False
        document = self._document
        assert document is not None
        if section_key not in self._allowed_sections(segment_index):
            self._set_edit_status(
                f"That line cannot go in {models.section_title(section_key)}: "
                "clinician-owned sections take only the confirmed clinician's "
                "statements."
            )
            return False
        segment = document.transcript_segments[segment_index]
        assertion = whole_utterance_assertion(
            manual_assertion_id(segment_index),
            section_key,
            segment_index=segment_index,
            speaker=segment.speaker,
            words=segment.transcript_words,
        )
        if assertion is None:
            return False
        if assertion_id not in self._manual:
            self._removed.add(assertion_id)  # the provider leg is subtracted
        self._learning_queue.pop(assertion.assertion_id, None)
        self._manual[assertion.assertion_id] = assertion
        self._set_edit_status(
            f"Moved to {models.section_title(section_key)}. Undo restores it until Save."
        )
        self._consider_learning(assertion)
        self._after_content_change()
        return True

    def undo_line(self, assertion_id: str) -> bool:
        """Reverse an add, a removal or a move of the line ``assertion_id``
        names (a provider id undoes its removal AND the re-added leg of a
        move; a manual id undoes the addition). Its queued phrase, if any,
        is dropped — an add undone before Save teaches nothing."""
        if not self._edits_open:
            self._set_edit_status("The note is saved - edits are closed.")
            return False
        changed = False
        if assertion_id in self._manual:
            del self._manual[assertion_id]
            self._learning_queue.pop(assertion_id, None)
            changed = True
        elif assertion_id in self._removed:
            self._removed.discard(assertion_id)
            segment_index = self._segment_of(assertion_id)
            if segment_index is not None:
                manual_id = manual_assertion_id(segment_index)
                if manual_id in self._manual:
                    del self._manual[manual_id]
                    self._learning_queue.pop(manual_id, None)
            changed = True
        if not changed:
            return False
        self._set_edit_status("Undone.")
        self._after_content_change()
        return True

    def _provider_line_exists(self, assertion_id: str) -> bool:
        draft = self._draft
        if draft is None:
            return False
        return any(
            assertion.assertion_id == assertion_id and assertion.provenance == "transcript"
            for section in draft.note_sections
            for assertion in section.note_assertions
        )

    def _segment_of(self, assertion_id: str) -> int | None:
        """The transcript segment a provider or manual line quotes."""
        draft = self._draft
        if draft is None:
            return None
        manual = self._manual.get(assertion_id)
        if manual is not None and manual.note_span.source_coords is not None:
            return manual.note_span.source_coords.segment_index
        for section in draft.note_sections:
            for assertion in section.note_assertions:
                coords = assertion.note_span.source_coords
                if assertion.assertion_id == assertion_id and coords is not None:
                    return coords.segment_index
        return None

    # --- phrase learning (D9 as amended) -------------------------------------

    def _consider_learning(self, assertion: NoteAssertion) -> None:
        """Queue the added/moved line's phrase, or say why not. The
        ownership test comes FIRST and silently: a line that is not the
        confirmed clinician's is never a candidate, whatever the status."""
        draft, document, config = self._draft, self._document, self._config
        coords = assertion.note_span.source_coords
        if draft is None or document is None or config is None or coords is None:
            return
        segment = document.transcript_segments[coords.segment_index]
        if not spoken_by_confirmed_clinician(segment.speaker, draft.clinician_speaker):
            # Never a candidate (the ownership rule) — but SAY so (live smoke
            # 2026-09-17: a silent skip reads as a broken feature).
            self._append_edit_status(models.LEARNING_NOT_ATTRIBUTED_NOTE)
            return
        status = self._refresh_learning_status()
        if not status.enabled:
            self._append_edit_status(status.reason or "")
            return
        words = [word.word_text for word in segment.transcript_words]
        candidate = propose_learning_phrase(words)
        if candidate is None:
            self._append_edit_status("Not learned: the line is too short to make a phrase.")
            return
        # The REAL segment-start status travels with the candidate (peer
        # round 36 PR-HIGH-008): a leading filler that was dropped does not
        # hand the opener exemption to the word after it.
        refusal = refuse_learning_candidate(
            candidate.source_words,
            first_in_segment=candidate.first_in_segment,
            following=candidate.following,
        )
        if refusal is not None:
            self._append_edit_status(
                f"Not learned: contains a name/number/date/medication ({refusal})."
            )
            return
        tokens = tuple(candidate.phrase.split(" "))
        cues = config.normalised_cues()
        for key, phrases in cues.items():
            if tokens in phrases:
                self._append_edit_status(
                    f"Not learned: '{candidate.phrase}' is already a cue for "
                    f"{models.section_title(key)}."
                )
                return
        section_key = assertion.section_key
        proposed = dict(cues)
        proposed[section_key] = (*proposed.get(section_key, ()), tokens)
        text = reconstruct_span_text(segment.transcript_words)
        winner = first_matching_section(
            proposed,
            content_tokens(text),
            CANONICAL_SECTION_KEYS,
            speaker=segment.speaker,
            clinician_speaker=draft.clinician_speaker,
            question=is_interrogative(text),
        )
        self._learning_queue[assertion.assertion_id] = (section_key, candidate.phrase)
        message = (
            f"Will learn '{candidate.phrase}' for {models.section_title(section_key)} "
            "when you press Save note on this tab."
        )
        if winner is not None and winner != section_key:
            # PR-MED-011: noted, never a silent cue deletion — the earlier
            # section's cue keeps first-match routing for lines like this one.
            message += (
                f" Note: a {models.section_title(winner)} cue still routes this line "
                "first."
            )
        self._append_edit_status(message)

    def _append_edit_status(self, message: str) -> None:
        current = self.edit_status_label.text()
        self._set_edit_status(f"{current} {message}".strip())

    def _write_learned_phrases(self) -> str | None:
        """Save-time write of the queue (the ONLY write): the status is
        re-read first, so a profile deleted or opted out during the review
        writes nothing. Returns the status-line text — what was learned, why
        the write failed, or why nothing was learned when lines were added or
        moved — or None when this review had no edit at all."""
        queued = list(self._learning_queue.values())
        self._learning_queue.clear()
        if not queued and not self._manual:
            return None  # no add or move this review: nothing to report, no read
        status = self._refresh_learning_status()
        if not queued:
            # Lines were added or moved but none queued (live smoke
            # 2026-09-17): name the reason rather than stay silent.
            if not status.enabled:
                return f"Nothing learned from this note. {status.reason or ''}".strip()
            return (
                "Nothing learned from this note: no added or moved line was one of yours "
                "that passed the checks above."
            )
        if not status.enabled:
            return f"Nothing learned. {status.reason or ''}".strip()
        try:
            outcome = append_user_cues(
                queued, config_root=self._config_root, learned_at=datetime.now(UTC)
            )
        except NoteConfigError as exc:
            return f"Phrases were not learned - {type(exc).__name__}: {exc}"
        parts: list[str] = []
        if outcome.added:
            listed = "; ".join(
                f"'{phrase}' for {models.section_title(key)}" for key, phrase in outcome.added
            )
            parts.append(f"Learned {len(outcome.added)}: {listed}.")
            if outcome.sidecar_error is not None:
                # Peer round 36 PR-MED-023: the cue file WAS replaced — say
                # so, and refresh the tab that lists it, rather than report
                # a failure that would hide a persisted phrase.
                parts.append(
                    "The date record could not be written, so they appear under Learned "
                    f"phrases without a date ({outcome.sidecar_error})."
                )
            self.learned_phrases_changed.emit()
        if outcome.skipped:
            parts.append(f"Skipped {len(outcome.skipped)} already among the cues.")
        parts.append("Review learned phrases on the Practitioner tab.")
        return " ".join(parts)

    # --- the line editor's widgets ------------------------------------------

    def _rebuild_edit_controls(self) -> None:
        # Round 34 LOW-002: the chooser is rebuilt on every re-finalise (a
        # proposal decision included), so the practitioner's current choice
        # is carried across by its data, as `refresh_devices` does.
        selected = self.utterance_combo.currentData()
        self.utterance_combo.blockSignals(True)
        self.utterance_combo.clear()
        for choice in self.eligible_utterances():
            self.utterance_combo.addItem(choice.label, choice.segment_index)
        if selected is not None:
            index = self.utterance_combo.findData(selected)
            if index >= 0:
                self.utterance_combo.setCurrentIndex(index)
        self.utterance_combo.blockSignals(False)
        self._refresh_section_combo()
        _clear_layout(self._lines_box)
        self._line_widgets.clear()
        for line in self.editable_lines():
            row = QWidget()
            row_layout = QHBoxLayout(row)
            label = QLabel(line.label)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            row_layout.addWidget(label, stretch=1)
            if line.state in ("routed", "added"):
                if line.state == "routed":
                    remove = QPushButton("Remove line")
                    remove.clicked.connect(
                        lambda _=False, aid=line.assertion_id: self.remove_line(aid)
                    )
                else:
                    remove = QPushButton("Undo add")
                    remove.clicked.connect(
                        lambda _=False, aid=line.assertion_id: self.undo_line(aid)
                    )
                row_layout.addWidget(remove)
                self._line_widgets.append(remove)
                if line.allowed_sections:
                    target = QComboBox()
                    for key in line.allowed_sections:
                        target.addItem(models.section_title(key), key)
                    move = QPushButton("Move")
                    move.clicked.connect(
                        lambda _=False, aid=line.assertion_id, combo=target: self.move_line(
                            aid, combo.currentData()
                        )
                    )
                    row_layout.addWidget(target)
                    row_layout.addWidget(move)
                    self._line_widgets.extend((target, move))
            else:
                state = (
                    "(removed)"
                    if line.moved_to is None
                    else f"(moved to {models.section_title(line.moved_to)})"
                )
                state_label = QLabel(state)
                row_layout.addWidget(state_label)
                undo = QPushButton("Undo")
                undo.clicked.connect(
                    lambda _=False, aid=line.assertion_id: self.undo_line(aid)
                )
                row_layout.addWidget(undo)
                self._line_widgets.append(undo)
            self._lines_box.addWidget(row)

    def _refresh_section_combo(self) -> None:
        selected = self.section_combo.currentData()
        self.section_combo.clear()
        data = self.utterance_combo.currentData()
        if data is None:
            return
        for key in self._allowed_sections(int(data)):
            self.section_combo.addItem(models.section_title(key), key)
        if selected is not None:
            index = self.section_combo.findData(selected)
            if index >= 0:
                self.section_combo.setCurrentIndex(index)

    def _on_add_clicked(self) -> None:
        segment = self.utterance_combo.currentData()
        section = self.section_combo.currentData()
        if segment is None or section is None:
            self._set_edit_status("Choose a line and a section first.")
            return
        self.add_line(int(segment), section)

    # --- finalisation ------------------------------------------------------

    def _build_resolutions(self) -> list[ProposalResolution]:
        draft = self._draft
        assert draft is not None
        resolutions: list[ProposalResolution] = []
        for proposal in draft.note_proposals:
            decision = self._resolutions.get(proposal.proposal_id)
            if decision is None:
                continue  # pending -> finalise_note flags unconfirmed_proposal
            rendered = self._rendered_excerpt[proposal.proposal_id]
            resolutions.append(
                ProposalResolution(
                    shown_text_digest=text_digest(rendered),
                    confirmation=ConfirmationDecision(
                        proposal_id=proposal.proposal_id,
                        note_confirmation=decision,
                        decided_at=datetime.now(UTC),
                    ),
                )
            )
        return resolutions

    def _refinalise(self) -> None:
        draft, document, config = self._draft, self._document, self._config
        if draft is None or document is None or config is None:
            return
        # D14: the WORKING draft — removed lines filtered out, additions
        # appended — is what every check runs over.
        self._working = models.working_draft(
            draft, removed=self._removed, additions=tuple(self._manual.values())
        )
        self._note = finalise_note(self._working, self._build_resolutions(), document, config)
        self.note_body.setPlainText(models.format_note_body(self._note))
        self._refresh_proposal_states()
        self._refresh_warnings()
        self._rebuild_edit_controls()
        self._update_controls()
        self._emit_state()

    def _refresh_proposal_states(self) -> None:
        for proposal_id, label in self._state_labels.items():
            decision = self._resolutions.get(proposal_id)
            if decision == "confirmed":
                label.setText("Confirmed - will be inserted.")
            elif decision == "declined":
                label.setText("Declined - not inserted.")
            else:
                label.setText("Not yet confirmed or declined.")

    def _refresh_warnings(self) -> None:
        _clear_layout(self._blocking_box)
        _clear_layout(self._review_box)
        if self._note is None:
            self.blocking_header.hide()
            self.review_header.hide()
            self.acknowledge_all_button.hide()
            return
        summary = models.summarise_warnings(self._note.note_warnings)
        self.blocking_header.setVisible(bool(summary.blocking))
        for group in summary.blocking:
            text = f"{group.title} ({group.count}). Blocks {group.blocks}. {group.clear_hint}"
            item = QLabel(text)
            item.setWordWrap(True)
            item.setStyleSheet("color: #b00020;")
            self._blocking_box.addWidget(item)
        unacknowledged = [g for g in summary.review if g.code not in self._acknowledged]
        self.review_header.setVisible(bool(summary.review))
        for group in summary.review:
            acked = group.code in self._acknowledged
            row = QWidget()
            row_layout = QHBoxLayout(row)
            status = "acknowledged" if acked else "not acknowledged"
            item = QLabel(f"{group.title} ({group.count}) - {status}. {group.clear_hint}")
            item.setWordWrap(True)
            row_layout.addWidget(item, stretch=1)
            if not acked:
                button = QPushButton("Acknowledge")
                button.clicked.connect(
                    lambda _=False, code=group.code: self._acknowledge(code)
                )
                row_layout.addWidget(button)
            self._review_box.addWidget(row)
        self.acknowledge_all_button.setVisible(bool(unacknowledged))

    # --- save / abandon / copy ---------------------------------------------

    def save(self) -> None:
        note = self._note
        on_save = self._on_save
        if note is None or on_save is None:
            return
        state = self.current_review_state()
        if state.blocking_errors or state.unacknowledged_reviews:
            self.message_label.setText(
                "Confirm every proposed line and acknowledge every review "
                "warning before saving."
            )
            return
        try:
            on_save(note)
        except Exception as exc:  # noqa: BLE001 - surfaced, never crashes the UI
            self.message_label.setText(f"Save failed: {type(exc).__name__}: {exc}")
            return
        self._note_saved = True
        self.message_label.setText(
            "Note saved. Acknowledge any review warnings, then Complete on the "
            "Transcript screen."
        )
        # D9 as amended: phrases are written ONLY here, after the note is
        # committed; a learning failure never un-saves the note.
        learned = self._write_learned_phrases()
        if learned is not None:
            self._set_edit_status(learned)
        self._update_controls()
        self._emit_state()

    def abandon(self) -> None:
        """The explicit delete-note-and-complete-without-one exit (Task 7.1).
        Every blocking state reaches this: it needs no clean note."""
        if self._on_abandon is None:
            return
        try:
            self._on_abandon()
        except Exception as exc:  # noqa: BLE001
            self.message_label.setText(
                f"Complete without a note failed: {type(exc).__name__}: {exc}"
            )
            return
        self.clear()

    def cancel_review(self) -> None:
        """The NON-destructive escape (round 35 PR-MED-003): discard this
        draft and return to the Transcript screen to regenerate — the visible
        clear-path for a blocking error on a base assertion that cannot be
        retracted. The callback (``on_cancel``) releases the lease and keeps
        the transcript/key; this then clears the Note-tab plaintext."""
        if self._on_cancel is None:
            return
        self._on_cancel()
        self.clear()

    def _copy_note(self) -> None:
        note = self._note
        if not self._copy_ready() or note is None:  # click-time re-check (fail closed)
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(models.format_note_body(note))
            self.message_label.setText("Note copied.")

    def _copy_ready(self) -> bool:
        """The single predicate copy enablement derives from (round 35
        PR-MED-002): the 9.1 shipping flag is NECESSARY but not sufficient —
        copy shares Complete's ratification bar. A note may reach any
        clipboard path only when the gate is on AND the review is fully
        ratified (no pending proposal, no blocking error, saved, no
        unacknowledged review — exactly what ``complete_block_reason``
        enforces), so an unresolved-error note can never be copied even after
        Task 9.1 flips the flag."""
        return (
            self._copy_enabled
            and self._note is not None
            and models.complete_block_reason(self.current_review_state()) is None
        )

    def _apply_copy_binding(self) -> None:
        """Bind the copy affordance: the Copy BUTTON is visible per the 9.1
        shipping flag, but both the button's ENABLED state and the note
        panel's selectability derive from ``_copy_ready()`` — so selectable
        text (which carries native copy shortcuts) and the button share one
        predicate. The transcript panel is display-only always."""
        ready = self._copy_ready()
        if ready:
            self.note_body.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
        else:
            self.note_body.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.copy_button.setVisible(self._copy_enabled)
        self.copy_button.setEnabled(ready)

    # --- state / enablement ------------------------------------------------

    def current_note(self) -> GeneratedNote | None:
        return self._note

    def current_review_state(self) -> models.NoteReviewState:
        draft, note = self._draft, self._note
        if draft is None or note is None:
            return models.NoteReviewState()
        summary = models.summarise_warnings(note.note_warnings)
        pending = sum(
            1
            for proposal in draft.note_proposals
            if proposal.proposal_id not in self._resolutions
        )
        unacknowledged = sum(
            1 for group in summary.review if group.code not in self._acknowledged
        )
        return models.NoteReviewState(
            generating=not self._note_saved,
            has_note=True,
            unconfirmed_proposals=pending,
            blocking_errors=summary.blocking_count,
            unacknowledged_reviews=unacknowledged,
            note_saved=self._note_saved,
        )

    def _emit_state(self) -> None:
        if self._on_state_changed is not None:
            self._on_state_changed(self.current_review_state())

    def _update_controls(self) -> None:
        has_note = self._note is not None
        state = self.current_review_state()
        # Save requires a FULLY RATIFIED note (round 36 PR-MED-002): plan
        # Flow 1 makes zero unresolved error AND zero unacknowledged review
        # warnings the finalisation preconditions, so a committed note.enc is
        # always Complete-ready and can never be completed unacknowledged.
        save_ready = (
            has_note
            and not self._note_saved
            and state.blocking_errors == 0
            and state.unacknowledged_reviews == 0
        )
        self.save_button.setEnabled(save_ready)
        self.abandon_button.setEnabled(self._on_abandon is not None)
        # Cancel/regenerate is a PRE-commit escape: available while a draft is
        # under review and not yet saved (round 35 PR-MED-003).
        self.cancel_button.setEnabled(
            self._on_cancel is not None and self._draft is not None and not self._note_saved
        )
        # After Save the note is committed and its lease released — proposal
        # editing is disabled (regenerate to change it); acknowledgement stays
        # available for the Complete gate.
        for button in self._proposal_buttons:
            button.setEnabled(not self._note_saved)
        # Review edits are frozen after Save exactly like proposal decisions
        # (D14) and unavailable with no draft.
        edits_open = self._edits_open
        self.utterance_combo.setEnabled(edits_open)
        self.section_combo.setEnabled(edits_open)
        self.add_line_button.setEnabled(edits_open and self.utterance_combo.count() > 0)
        for widget in self._line_widgets:
            widget.setEnabled(edits_open)
        # The learning line follows the queue (a queued phrase names Save note).
        self._render_learning_line()
        # Copy shares Complete's ratification bar (round 35 PR-MED-002) — its
        # readiness changes with resolution/acknowledgement/save, so re-derive
        # it on every control refresh.
        self._apply_copy_binding()

    @property
    def is_busy(self) -> bool:
        """True while a draft is under review and not yet saved or abandoned —
        the state during which a generation lease is held. Closing must wait
        (the in-progress note would be lost)."""
        return self._draft is not None and not self._note_saved
