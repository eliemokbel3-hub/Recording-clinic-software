"""Note review tab (Phase 3A, Tasks 7.1 + 7.6).

The clinician's review surface for a generated note. It renders the composed
note (canonical-section order, provenance visibly distinguished, one bullet
per assertion — NEVER assembled prose), the per-proposal confirm/decline
controls showing the EXACT text that will be inserted, and the checker
warnings GROUPED and SUMMARISED (warning fatigue is this phase's top risk),
with blocking errors kept DISTINCT from review warnings. Task 7.6 keeps the
full uncertainty-marked transcript visible BESIDE the note through the whole
review, so a low-confidence phrase the note omitted is still reachable.

Clinical-content discipline (Critical Constraints, design-system):
- The transcript panel is display-only (``NoTextInteraction``) ALWAYS, and is
  cleared on close.
- The note is the RATIFIED copyable surface, but only once the Task 9.1
  shipping gate passes: copy is bound to ``models.COPY_TO_CLINIKO_ENABLED``,
  which ships False, so copy is DISABLED and the note panel is display-only
  until that recorded decision flips.
- Nothing here logs or persists clinical text. Confirmation evidence
  (``shown_text_digest``) is computed from the text the widget ACTUALLY
  rendered — read back from the proposal label, never copied from the
  proposal — so a rendering bug produces evidence ``finalise_note`` refuses.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
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
    ConfirmationDecision,
    GeneratedNote,
    NoteDraft,
    ProposalResolution,
    finalise_note,
    text_digest,
)
from scribe_desktop.note_config import NoteConfig
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

    def __init__(self, parent: QWidget | None = None) -> None:
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

        # --- the note review side -----------------------------------------
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)

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
            "acknowledged, and no blocking warning remains."
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
        self.message_label.setWordWrap(True)

        note_side = QWidget()
        note_layout = QVBoxLayout(note_side)
        note_layout.addWidget(self.info_label)
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

        self.transcript_view.setPlainText(models.format_transcript_text(result.document))
        self.info_label.setText(
            "  ".join(
                models.config_report_lines(result.config, template_profile_id)
            )
        )
        self._build_proposal_rows()
        self._refinalise()  # -> _update_controls -> _apply_copy_binding

    def clear(self) -> None:
        """Clear all plaintext and review state (on close, or when a
        different transcript loads over this note — Task 7.1/7.3)."""
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
        self.transcript_view.setPlainText("")
        self.note_body.setPlainText("")
        self.info_label.setText("")
        self.message_label.setText("")
        _clear_layout(self._proposals_box)
        _clear_layout(self._blocking_box)
        _clear_layout(self._review_box)
        self.proposals_header.hide()
        self.blocking_header.hide()
        self.review_header.hide()
        self.acknowledge_all_button.hide()
        self._update_controls()

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
            self._after_resolution_change()

    def _set_resolution(
        self, proposal_id: str, decision: Literal["confirmed", "declined"]
    ) -> None:
        if proposal_id not in self._rendered_excerpt:
            return
        self._resolutions[proposal_id] = decision
        self._after_resolution_change()

    def _after_resolution_change(self) -> None:
        # A content change invalidates prior acknowledgements and un-saves the
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
        self._note = finalise_note(draft, self._build_resolutions(), document, config)
        self.note_body.setPlainText(models.format_note_body(self._note))
        self._refresh_proposal_states()
        self._refresh_warnings()
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
