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
already anywhere in the note is refused, and there is no free-text AREA —
typing happens only OVER a line (the Edit control below).
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

Typed edits, shorthand learning and Save-as-ratification (note-learning-and-
styles plan Phase 2, Tasks 2.1 / 2.3 / 2.4; D4, D5, D11). Edit on a note line
or a proposal opens an inline single-line editor; committing it produces a
``clinician`` assertion — the typed text, the clinician's own decision naming
the line, ``replaces`` recording the line or proposal it stands in for — and
subtracts what it replaced (a provider line goes to ``_removed``, a manual
line is set aside, a proposal is declined at finalisation); Undo restores it.
When the replaced line is one of the practitioner's OWN utterances
(``spoken_by_confirmed_clinician``) the edit is a shorthand candidate: the
utterance's tail becomes the trigger through THE refusal filter
(``propose_rule_trigger`` + ``refuse_learning_candidate``), the typed text the
wording through ``refuse_typed_wording`` (numbers, dates, medications; no
name heuristic — the practitioner's own words), and the pair is QUEUED; an
edit of a LEARNED rule's own line queues an in-place wording replacement
instead. Like phrases, rules are written ONLY on Save
(``append_learned_rules`` / ``replace_learned_rule_wording`` /
``record_rule_outcomes``); Cancel, Discard and Delete write nothing and the
exit notice names what was dropped. Lines the practitioner's own config
PRE-FILLED arrive with the emitter's ``decided_by="config"`` decision on the
draft (``NoteDraft.config_decisions``): they render marked, have no
confirm/decline row, and the Save button says how many it confirms; Remove
replaces the config decision with the clinician's decline (and demotes a
learned rule's count at Save), Edit replaces it with a typed line; an
unchanged pre-filled line counts as one confirmation at Save. Save stays
refused while any proposal the config did NOT decide is pending, and while
any review warning is unacknowledged — ``clinician_asserted`` is not drawn
for a config-decided line (the counted Save is its acknowledgement), every
other warning keeps its gate.

The prose stage (note-learning-and-styles plan Phase 4, Task 4.4; D6, D7;
C4, C8). Under a prose writing style (``own_voice`` / ``narrative``) every
finalisation is followed by ONE stage job on a ``TaskThread``
(``models.build_prose_stage``): the language model renders the sections that
have no rendering bound to their current texts, and the result lands here on
the GUI thread through ``models.bind_stage_result`` — a rendering is bound
only where its input digest is the section's digest NOW, so an edit made
while the job ran invalidates exactly the sections it changed and a fresh job
renders those. Save is DISABLED while a job is in flight and re-enabled only
after the completed prose has been DISPLAYED (codex PR-MED-015: Save
snapshots ``_note``, so a Save can never persist wording the practitioner has
not seen); a job whose result arrives after the review ended is dropped. A
section whose prose failed Check 5 keeps ``clean`` and draws the
``style_fallback`` review warning (acknowledged like any other), and every
fallback — language model absent or failed to load, learned style missing,
rendering in flight — names itself on the style line under the note (C8).
``format_note_body`` stays the ONE rendering path: the body shown, the
``note.enc`` Save writes and Copy all read the same bound renderings.

Where the decisions live (note-learning plan Task H6). This widget holds
every piece of review STATE and the order it mutates it in; the DECISIONS it
consults — the resolution precedence, the learned-rule outcomes at Save, what
an add, a move or a typed edit teaches, and the review counts — are
functions in the Qt-free ``ui.note_review``, called with the state as
parameters. Their verdicts come back with the exact status texts, which this
widget appends in order.

Clinical-content discipline (Critical Constraints, design-system):
- The transcript panel is display-only (``NoTextInteraction``) ALWAYS, and is
  cleared with the rest of the tab whenever the review ends (``clear()`` on
  Complete, Discard, cancel, a new transcript or a new generation); an accepted
  window close ends the process — ``MainWindow.closeEvent`` refuses to close
  while a review is busy and calls no separate tab-clear (round 70 PR-LOW-013).
- The note is the RATIFIED copyable surface: copy is bound to
  ``models.COPY_TO_CLINIKO_ENABLED``, which ships True since the
  practitioner's 2026-09-27 decision (safeguards plan D12; the Task 9.1 run
  is now a quality measurement, not an enablement gate). The flag is
  necessary, not sufficient: the Copy button stays disabled and the note
  panel display-only until the note is fully ratified (``_copy_ready``).
- Nothing here logs or persists clinical text. Confirmation evidence
  (``shown_text_digest``) is computed from the text the widget ACTUALLY
  rendered — read back from the proposal label, never copied from the
  proposal — so a rendering bug produces evidence ``finalise_note`` refuses.
  The one thing this tab writes outside the session store is a learned
  PHRASE — the practitioner's own words, by their consent — to their cue file.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
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
    NoteProposal,
    NoteSectionKey,
    NoteSpan,
    NoteStyle,
    admissible_sections,
    bound_rendering,
    finalise_note,
    manual_assertion_id,
    note_input_digest,
    reconstruct_span_text,
    text_digest,
    whole_utterance_assertion,
)
from scribe_desktop.note_config import (
    LearnedRuleCandidate,
    NoteConfig,
    NoteConfigError,
    append_learned_rules,
    append_user_cues,
    plain_skip_reason,
    record_rule_outcomes,
    replace_learned_rule_wording,
)
from scribe_desktop.transcription import TranscriptDocument
from scribe_desktop.ui import models, note_review
from scribe_desktop.ui.tasks import TaskThread


def _refused_sections(note: GeneratedNote) -> frozenset[NoteSectionKey]:
    """The sections whose BOUND rendering is a Check 5 refusal — the ones a
    `style_fallback` warning stands for right now."""
    return frozenset(
        section.section_key
        for section in note.note_sections
        if (rendering := bound_rendering(note, section)) is not None
        and rendering.verdict == "failed"
    )


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


class _LineEditor(QLineEdit):
    """The inline single-line editor a row shows while the clinician types
    over that line (note-learning plan Task 2.1). Enter applies it (the
    inherited ``returnPressed``); Escape cancels — the one key the base class
    does not already report, so it is the only reason this subclass exists."""

    escape_pressed = Signal()

    def keyPressEvent(self, event: QKeyEvent, /) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            return
        super().keyPressEvent(event)


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
        note_style_provider: Callable[[], models.NoteStyleChoice] | None = None,
        prose_stage_provider: Callable[[NoteStyle], models.ProseStage | None] | None = None,
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
        # Writing style (note-learning plan D7, Task 3.2): read ONCE per
        # review from `practitioner_settings.json` under `config_root` (the
        # main window's provider, whose absent-file default is `clean`) and
        # stamped on every finalised note, so the body the tab shows, the
        # `note.enc` it saves and Copy all render alike. A screen built
        # WITHOUT a provider renders `verbatim` — the note schema's own
        # default, so the Phase 3A body pins keep their meaning; the shipped
        # window always supplies the provider.
        self._note_style_provider = note_style_provider
        self._note_style: NoteStyle = "verbatim"
        # The prose stage (Task 4.4): the provider gives the stage callable
        # for the review's style (None for the deterministic styles and for
        # a screen built without one — no job ever runs there); one job at a
        # time, bound to the digest of the note it was started for; a job
        # orphaned by `clear()` keeps its thread object alive until it ends
        # and its result is dropped.
        self._prose_stage_provider = prose_stage_provider
        self._prose_stage: models.ProseStage | None = None
        self._style_job: TaskThread | None = None
        self._style_job_abort: threading.Event | None = None
        self._orphaned_jobs: list[TaskThread] = []
        # ONE set for two kinds of id (practitioner decision 2026-09-26): the
        # provider lines Removed (or typed over) and the pre-filled proposals
        # Removed. The namespaces cannot collide — an assertion id is
        # `x<nnnn>` (provider), `m<nnnn>` (manual) or `t<nnnn>` (typed), a
        # proposal id is `autofill-<24 hex>` or `prefill-<24 hex>`
        # (`note_fill._proposal_id`) — pinned by `tests/test_note_review.py`.
        self._removed: set[str] = set()
        self._manual: dict[str, NoteAssertion] = {}
        self._learning_queue: dict[str, tuple[NoteSectionKey, str]] = {}
        self._working: NoteDraft | None = None
        self._line_widgets: list[QWidget] = []
        # Typed edits (note-learning plan Task 2.1) and shorthand learning
        # (Task 2.3): typed lines by id (``t<n>``), each typed id -> the id it
        # replaced, the manual assertion a typed line displaced (restored on
        # Undo), the proposal ids a typed line stands in for (declined at
        # finalisation), the queued rule candidates and the queued in-place
        # wording replacements — both keyed by typed id, written on Save only.
        self._typed: dict[str, NoteAssertion] = {}
        self._replaced: dict[str, str] = {}
        self._replaced_manual: dict[str, NoteAssertion] = {}
        self._edited_proposals: dict[str, str] = {}
        self._rule_queue: dict[str, LearnedRuleCandidate] = {}
        self._rule_replacements: dict[str, note_review.RuleReplacement] = {}
        self._typed_counter = 0
        # The inline editor (Task 2.1): the request — the id being typed over
        # and the text the field opens with — survives a row rebuild and is
        # what renders the field; the live widget does not (the rows are
        # recreated on every re-finalise, so an open editor is simply dropped
        # and rebuilt from the request).
        self._editor_request: tuple[str, str] | None = None
        self._editor: tuple[str, QLineEdit] | None = None

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
        self.lines_header = QLabel("Lines in the note - remove, move, edit or undo:")
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
        # PLAIN TEXT (round 12 MED-003): beside the config report this label
        # shows the generation notes, which quote a loader error's detail —
        # user-authored config text — exactly as the message label does.
        self.info_label.setTextFormat(Qt.TextFormat.PlainText)
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
        # The style line (Task 4.4, C8): rendering in flight, what landed,
        # or why the note is shown as Clean clinical. PLAIN TEXT: it quotes
        # a loader's or the runtime's error detail.
        self.style_label = QLabel()
        self.style_label.setTextFormat(Qt.TextFormat.PlainText)
        self.style_label.setWordWrap(True)

        self.proposals_header = QLabel("Proposed additions - confirm or decline each:")
        self.proposals_header.hide()
        self._proposals_box = QVBoxLayout()

        self.save_button = QPushButton(models.SAVE_BUTTON_LABEL)
        self.save_button.setToolTip(
            "Verify and store the note for this session. Enabled once every "
            "proposed line is confirmed or declined, every review warning is "
            "acknowledged, and no blocking warning remains. Lines pre-filled by "
            "your config are confirmed by this Save (the button counts them). "
            "Phrases and shorthand rules queued for learning are written here and "
            "nowhere else."
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
        note_layout.addWidget(self.style_label)
        note_layout.addWidget(self.proposals_header)
        # The proposal rows' scroll area shows and hides WITH its header
        # (Phase H live smoke, leg h1j): with no proposal it used to stay as
        # a large empty framed box under the style line, which reads as a
        # blank prose pane — the prose itself is in `note_body` above.
        self.proposals_scroll = QScrollArea()
        self.proposals_scroll.setWidgetResizable(True)
        proposals_content = QWidget()
        proposals_content.setLayout(self._proposals_box)
        self.proposals_scroll.setWidget(proposals_content)
        self.proposals_scroll.hide()
        note_layout.addWidget(self.proposals_scroll)
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
        style_choice = self._read_note_style()
        self._note_style = style_choice.style
        # Task 4.4: the stage for this review's style — None for the two
        # deterministic styles, and None on a screen built without a
        # provider (then a prose style still says it renders as Clean
        # clinical, below); with a provider, the stage itself names on the
        # style line why nothing rendered (model absent or failed to load,
        # learned style missing).
        provider = self._prose_stage_provider
        self._prose_stage = provider(style_choice.style) if provider is not None else None

        self.transcript_view.setPlainText(models.format_transcript_text(result.document))
        # The config report, then any generation note (C8: a fallback names
        # its reason on screen — the unreadable learned-shorthand record
        # that made every learned rule propose (round 12 MED-003), an
        # unreadable style setting, or a prose style chosen while no
        # language model exists (Task 3.2: rendered as Clean clinical).
        notes = [*result.notes]
        if style_choice.reason is not None:
            notes.append(style_choice.reason)
        fallback = models.style_fallback_line(style_choice.style)
        if fallback is not None and provider is None:
            notes.append(fallback)
        self.info_label.setText(
            "  ".join(
                (*models.config_report_lines(result.config, template_profile_id), *notes)
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
        self._orphan_style_job()
        self._prose_stage = None
        self.style_label.setText("")
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
        self._typed.clear()
        self._replaced.clear()
        self._replaced_manual.clear()
        self._edited_proposals.clear()
        self._rule_queue.clear()
        self._rule_replacements.clear()
        self._typed_counter = 0
        self._editor_request = None
        self._editor = None
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
        self.proposals_scroll.hide()
        self.blocking_header.hide()
        self.review_header.hide()
        self.acknowledge_all_button.hide()
        self._update_controls()

    def _read_learning_status(self) -> models.LearningStatus:
        provider = self._learning_status_provider
        if provider is None:
            return models.LearningStatus(False, models.LEARNING_NO_PROFILE_HINT)
        return provider()

    def _read_note_style(self) -> models.NoteStyleChoice:
        provider = self._note_style_provider
        if provider is None:
            return models.NoteStyleChoice("verbatim", None)
        return provider()

    @property
    def note_style(self) -> NoteStyle:
        """The writing style this review renders under (read at ``begin_review``)."""
        return self._note_style

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
        elif (self._learning_queue or self._queued_rules()) and not self._note_saved:
            self.learning_label.setText(
                models.learning_queued_line(len(self._learning_queue), self._queued_rules())
            )
        else:
            self.learning_label.setText(models.LEARNING_ON_LINE)

    def _queued_rules(self) -> int:
        return len(self._rule_queue) + len(self._rule_replacements)

    # --- proposal rows -----------------------------------------------------

    def _prefilled_ids(self) -> frozenset[str]:
        """The proposals the practitioner's own config decided (D5): no
        confirm/decline row — they are in the note, marked, until Removed."""
        return note_review.prefilled_ids(self._draft)

    def _build_proposal_rows(self) -> None:
        assert self._draft is not None
        prefilled = self._prefilled_ids()
        for proposal in self._draft.note_proposals:
            if proposal.proposal_id in prefilled:
                continue  # a pre-filled line: in the note, marked; Remove/Edit below
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
            # Task 2.1: type over the proposal instead of deciding it — the
            # editor opens on the text this row RENDERED.
            edit = QPushButton("Edit")
            edit.setToolTip(
                "Replace this proposed line with your own wording. Undo returns it here."
            )
            edit.clicked.connect(
                lambda _=False, pid=proposal.proposal_id, text=rendered.excerpt: self.open_editor(
                    pid, text
                )
            )
            actions = QHBoxLayout()
            actions.addWidget(confirm)
            actions.addWidget(decline)
            actions.addWidget(retract)
            actions.addWidget(edit)
            actions.addStretch(1)
            row_layout.addLayout(actions)
            self._proposal_buttons.extend((confirm, decline, retract, edit))
            self._proposals_box.addWidget(row)
        has_rows = any(p.proposal_id not in prefilled for p in self._draft.note_proposals)
        self.proposals_header.setVisible(has_rows)
        self.proposals_scroll.setVisible(has_rows)

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
        if proposal_id not in self._rendered_excerpt or proposal_id in self._edited_proposals:
            return  # no row (pre-filled), or replaced by a typed line (Undo first)
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
                # Quoted lines only: a typed ``clinician`` line (schema v2)
                # carries no coordinates and marks no segment as present...
                if assertion.provenance == "transcript" and coords is not None:
                    present.add(coords.segment_index)
        # ...except through the line it REPLACED (Task 2.1): the utterance a
        # typed line stands in for is still spoken for, so the chooser does
        # not offer it again.
        for replaced_id in self._replaced.values():
            segment_index = self._segment_of(replaced_id)
            if segment_index is not None:
                present.add(segment_index)
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
        additions = {**self._manual, **self._replaced_manual}
        replaced = {target: typed_id for typed_id, target in self._replaced.items()}
        return models.editable_lines(
            draft, document, removed=self._removed, additions=additions, replaced=replaced
        )

    def typed_lines(self) -> tuple[models.TypedLine, ...]:
        """The typed rows of the line editor (Task 2.1), in edit order."""
        return models.typed_lines(self._typed)

    def prefilled_lines(self) -> tuple[models.PrefilledLine, ...]:
        """The pre-filled rows of the line editor (D5): one per config
        decision the draft carries, with its Remove / Edit state."""
        draft = self._draft
        if draft is None:
            return ()
        replaced = {target: typed_id for typed_id, target in self._replaced.items()}
        return models.prefilled_lines(draft, removed=self._removed, replaced=replaced)

    def learning_queue(self) -> tuple[tuple[NoteSectionKey, str], ...]:
        """What Save would learn, in queue order (a read-only view)."""
        return tuple(self._learning_queue.values())

    def rule_queue(self) -> tuple[LearnedRuleCandidate, ...]:
        """The shorthand rules Save would write, in edit order (read-only)."""
        return tuple(self._rule_queue.values())

    def rule_replacement_queue(self) -> tuple[tuple[str, str], ...]:
        """The learned rules whose wording Save would replace in place —
        ``(rule_id, typed wording)`` — in edit order (read-only)."""
        return tuple(self._rule_replacements.values())

    def queued_learning_count(self) -> int:
        """How many phrases Save note would write right now (Task 5.6: the
        main window reads it BEFORE an exit clears this tab, to say what the
        exit dropped)."""
        return len(self._learning_queue)

    def queued_rule_count(self) -> int:
        """How many shorthand rules (new or corrected) Save note would write
        right now — read by the main window before an exit clears this tab,
        exactly as ``queued_learning_count`` is (Task 2.3)."""
        return self._queued_rules()

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
        """Subtract a provider-routed line (D14) or a line the practitioner's
        config PRE-FILLED (D5: the config decision is replaced by the
        clinician's decline at Save, and a learned rule's count is reset —
        the rule itself is never deleted here). Reversible with
        ``undo_line`` until Save; any omission warning it raises is
        acknowledgeable. A typed line's Remove is its Undo."""
        if not self._edits_open:
            self._set_edit_status("The note is saved - edits are closed.")
            return False
        if assertion_id in self._manual or assertion_id in self._typed:
            return self.undo_line(assertion_id)
        if assertion_id in self._removed or assertion_id in self._replaced.values():
            return False
        if assertion_id in self._prefilled_ids():
            self._removed.add(assertion_id)
            self._set_edit_status(
                "Pre-filled line removed - Save will record that you declined it. "
                "Undo restores it until Save."
            )
            self._after_content_change()
            return True
        if not self._provider_line_exists(assertion_id):
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
        if assertion_id in self._typed:
            self._undo_typed(assertion_id)
            changed = True
        elif assertion_id in self._replaced.values():
            # Undo on the REPLACED line undoes the typed line that stands in
            # for it (Task 2.1): one edit, one undo, whichever row is used.
            typed_id = next(t for t, target in self._replaced.items() if target == assertion_id)
            self._undo_typed(typed_id)
            changed = True
        elif assertion_id in self._manual:
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

    # --- typed edits (note-learning plan Task 2.1) ------------------------------

    def _next_typed_id(self) -> str:
        """``t<n>`` — a third id scheme beside the provider's ``x<segment>``
        and the manual ``m<segment>``, so a typed line can never collide with
        a quoted one in one note and is recognisable by its id."""
        self._typed_counter += 1
        return f"t{self._typed_counter:04d}"

    def _proposal(self, proposal_id: str) -> NoteProposal | None:
        return note_review.proposal_by_id(self._draft, proposal_id)

    def _edit_target_section(self, target_id: str) -> NoteSectionKey | None:
        """The section a typed line inherits from what it replaces: a
        provider line still in the note, a manual line, a proposal (pending,
        decided or pre-filled — but not one already replaced) — or None when
        ``target_id`` is none of these."""
        draft = self._draft
        if draft is None:
            return None
        if target_id in self._replaced.values():
            return None
        manual = self._manual.get(target_id)
        if manual is not None:
            return manual.section_key
        if target_id not in self._removed:
            for section in draft.note_sections:
                for assertion in section.note_assertions:
                    if assertion.assertion_id == target_id:
                        return section.section_key
        proposal = self._proposal(target_id)
        if proposal is not None and target_id not in self._removed:
            return proposal.section_key
        return None

    def edit_line(self, target_id: str, text: str) -> bool:
        """Type ``text`` over the line or proposal ``target_id`` (Task 2.1):
        the result is a ``clinician`` assertion in the target's section —
        typed text as its span, the clinician's own decision naming it,
        ``replaces`` = ``target_id`` — and the target is subtracted (a
        provider line to ``_removed``, a manual line set aside, a proposal
        declined at finalisation, a pre-filled line likewise). Editing a
        TYPED line again replaces its wording in place, keeping what it
        replaced. Refused, with the reason on the status line and nothing
        changed: after Save, for an unknown or already-replaced target, and
        for text ``models.check_typed_text`` refuses. Returns whether the
        edit was applied. Shorthand learning is considered afterwards
        (``_consider_rule_learning``): a candidate is QUEUED, never written."""
        if not self._edits_open:
            self._set_edit_status("The note is saved - edits are closed.")
            return False
        draft = self._draft
        assert draft is not None
        reason = models.check_typed_text(text)
        if reason is not None:
            self._set_edit_status(reason)
            return False
        wording = text.strip()
        if target_id in self._typed:
            return self._retype(target_id, wording)
        section_key = self._edit_target_section(target_id)
        if section_key is None:
            self._set_edit_status("That line cannot be edited here.")
            return False
        typed_id = self._next_typed_id()
        typed = self._typed_assertion(typed_id, section_key, wording, replaces=target_id)
        manual = self._manual.pop(target_id, None)
        if manual is not None:
            self._replaced_manual[typed_id] = manual
        elif self._proposal(target_id) is not None:
            self._edited_proposals[target_id] = typed_id
        else:
            self._removed.add(target_id)
        self._typed[typed_id] = typed
        self._replaced[typed_id] = target_id
        self._set_edit_status(
            f"Line replaced with your wording in {models.section_title(section_key)}. "
            "Undo restores the original until Save."
        )
        self._consider_rule_learning(typed_id)
        self._after_content_change()
        return True

    # --- the inline editor (Task 2.1) --------------------------------------

    def open_editor(self, target_id: str, current_text: str) -> None:
        """Open the one-line editor over the line or proposal ``target_id``,
        prefilled with ``current_text``. Refused after Save like every other
        edit. Only ONE editor is open at a time: opening another replaces it
        (the request is single-valued and the rows are rebuilt here)."""
        if not self._edits_open:
            self._set_edit_status("The note is saved - edits are closed.")
            return
        self._editor_request = (target_id, current_text)
        self._rebuild_edit_controls()

    def commit_editor(self) -> bool:
        """Apply the open editor's text over its target (``edit_line``). On
        success the row rebuild inside ``_after_content_change`` closes the
        editor; on refusal it stays open, carrying what was typed, with the
        reason on the status line. Returns what ``edit_line`` returned."""
        editor = self._editor
        request = self._editor_request
        if editor is None or request is None:
            return False
        target_id = request[0]
        text = editor[1].text()
        self._editor_request = None
        if self.edit_line(target_id, text):
            return True
        self._editor_request = (target_id, text)
        return False

    def cancel_editor(self) -> None:
        """Close the editor, changing nothing: no content changed, so the
        note is neither re-finalised nor un-acknowledged."""
        self._editor_request = None
        self._rebuild_edit_controls()
        self._update_controls()

    def _retype(self, typed_id: str, wording: str) -> bool:
        previous = self._typed[typed_id]
        if previous.text == wording:
            self._set_edit_status("The wording is unchanged.")
            return False
        self._typed[typed_id] = self._typed_assertion(
            typed_id, previous.section_key, wording, replaces=previous.replaces
        )
        self._set_edit_status("Wording updated. Undo restores the original line until Save.")
        self._consider_rule_learning(typed_id)
        self._after_content_change()
        return True

    def _typed_assertion(
        self, typed_id: str, section_key: NoteSectionKey, wording: str, *, replaces: str | None
    ) -> NoteAssertion:
        draft = self._draft
        assert draft is not None
        return NoteAssertion(
            assertion_id=typed_id,
            section_key=section_key,
            note_span=NoteSpan(span_text=wording, provenance="clinician"),
            shown_text_digest=text_digest(wording),
            config_digest=draft.config_digest,
            confirmation=ConfirmationDecision(
                proposal_id=typed_id,
                note_confirmation="confirmed",
                decided_at=datetime.now(UTC),
            ),
            replaces=replaces,
        )

    def _undo_typed(self, typed_id: str) -> None:
        """Drop the typed line and restore what it replaced; its queued rule
        or wording replacement dies with it (nothing is written before Save)."""
        del self._typed[typed_id]
        target = self._replaced.pop(typed_id)
        self._rule_queue.pop(typed_id, None)
        self._rule_replacements.pop(typed_id, None)
        manual = self._replaced_manual.pop(typed_id, None)
        if manual is not None:
            self._manual[manual.assertion_id] = manual
        elif self._edited_proposals.get(target) == typed_id:
            del self._edited_proposals[target]
        else:
            self._removed.discard(target)

    # --- shorthand learning (note-learning plan Task 2.3; D5, D11) -----------------

    def _consider_rule_learning(self, typed_id: str) -> None:
        """Queue the shorthand this typed edit teaches, or say why not — the
        decision is ``note_review.consider_rule_learning``'s (the ownership
        test first, THE refusal filter, both correction paths validated);
        this applies its verdict. Both queue entries are dropped FIRST, so a
        retype that no longer teaches leaves nothing queued. Every entry is
        keyed by the typed id, so Undo drops it, and nothing is written here."""
        self._rule_queue.pop(typed_id, None)
        self._rule_replacements.pop(typed_id, None)
        draft, document, config = self._draft, self._document, self._config
        typed = self._typed[typed_id]
        target = typed.replaces
        if draft is None or document is None or config is None or target is None:
            return
        verdict = note_review.consider_rule_learning(
            typed,
            draft=draft,
            document=document,
            config=config,
            segment_index=self._segment_of(target),
            learning_status=self._refresh_learning_status,
        )
        if verdict.rule is not None:
            self._rule_queue[typed_id] = verdict.rule
        if verdict.replacement is not None:
            self._rule_replacements[typed_id] = verdict.replacement
        for message in verdict.messages:
            self._append_edit_status(message)

    def _provider_line_exists(self, assertion_id: str) -> bool:
        draft = self._draft
        if draft is None:
            return False
        # A provider line is a quoted line; a typed ``clinician`` line
        # (schema v2) is never the provider's.
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
        if manual is None:
            manual = next(
                (a for a in self._replaced_manual.values() if a.assertion_id == assertion_id),
                None,
            )
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
        """Queue the added/moved line's phrase, or say why not — the decision
        is ``note_review.consider_learning``'s (the ownership test FIRST: a
        line that is not the confirmed clinician's is never a candidate,
        whatever the status); this applies its verdict."""
        draft, document, config = self._draft, self._document, self._config
        if draft is None or document is None or config is None:
            return
        verdict = note_review.consider_learning(
            assertion,
            draft=draft,
            document=document,
            config=config,
            learning_status=self._refresh_learning_status,
        )
        if verdict.queued is not None:
            self._learning_queue[assertion.assertion_id] = verdict.queued
        for message in verdict.messages:
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
        # Every row widget dies here, the open editor's field with them; the
        # REQUEST survives and re-renders the field in whichever row now
        # carries its target (Task 2.1).
        self._editor = None
        request = self._editor_request
        edited_id = request[0] if request is not None else None
        for line in self.editable_lines():
            row = QWidget()
            row_layout = QHBoxLayout(row)
            if request is not None and line.assertion_id == edited_id:
                self._build_editor_row(row_layout, request)
                self._lines_box.addWidget(row)
                continue
            label = QLabel(line.label)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            row_layout.addWidget(label, stretch=1)
            if line.state == "replaced":
                # Typed over (Task 2.1): one undo, from either row.
                replaced_label = QLabel("(replaced by your typed line)")
                replaced_label.setTextFormat(Qt.TextFormat.PlainText)
                row_layout.addWidget(replaced_label)
                undo = QPushButton("Undo")
                undo.clicked.connect(
                    lambda _=False, aid=line.assertion_id: self.undo_line(aid)
                )
                row_layout.addWidget(undo)
                self._line_widgets.append(undo)
            elif line.state in ("routed", "added"):
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
                edit = QPushButton("Edit")
                edit.setToolTip(
                    "Replace this line with your own wording. Undo restores it until Save."
                )
                # The FULL text of the line, not the row's truncated label.
                edit.clicked.connect(
                    lambda _=False, aid=line.assertion_id: self.open_editor(
                        aid, self._line_text(aid)
                    )
                )
                row_layout.addWidget(edit)
                self._line_widgets.append(edit)
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
        for prefilled in self.prefilled_lines():
            row = QWidget()
            row_layout = QHBoxLayout(row)
            if request is not None and prefilled.proposal_id == edited_id:
                self._build_editor_row(row_layout, request)
                self._lines_box.addWidget(row)
                continue
            # ``label`` already carries the pre-filled mark (D5).
            label = QLabel(prefilled.label)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            row_layout.addWidget(label, stretch=1)
            if prefilled.state == "prefilled":
                remove = QPushButton("Remove line")
                remove.setToolTip(
                    "Save will record that you declined this pre-filled line."
                )
                remove.clicked.connect(
                    lambda _=False, pid=prefilled.proposal_id: self.remove_line(pid)
                )
                edit = QPushButton("Edit")
                edit.setToolTip(
                    "Replace this pre-filled line with your own wording."
                )
                edit.clicked.connect(
                    lambda _=False, pid=prefilled.proposal_id, text=prefilled.text: (
                        self.open_editor(pid, text)
                    )
                )
                row_layout.addWidget(remove)
                row_layout.addWidget(edit)
                self._line_widgets.extend((remove, edit))
            else:
                state_text = (
                    "(removed - Save records your decline)"
                    if prefilled.state == "removed"
                    else "(replaced by your typed line)"
                )
                state_label = QLabel(state_text)
                state_label.setTextFormat(Qt.TextFormat.PlainText)
                row_layout.addWidget(state_label)
                undo = QPushButton("Undo")
                undo.clicked.connect(
                    lambda _=False, pid=prefilled.proposal_id: self.undo_line(pid)
                )
                row_layout.addWidget(undo)
                self._line_widgets.append(undo)
            self._lines_box.addWidget(row)
        for typed in self.typed_lines():
            row = QWidget()
            row_layout = QHBoxLayout(row)
            if request is not None and typed.assertion_id == edited_id:
                self._build_editor_row(row_layout, request)
                self._lines_box.addWidget(row)
                continue
            label = QLabel(f"{typed.label} [typed]")
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            row_layout.addWidget(label, stretch=1)
            edit = QPushButton("Edit")
            edit.setToolTip("Change your wording.")
            edit.clicked.connect(
                lambda _=False, aid=typed.assertion_id, text=typed.text: self.open_editor(
                    aid, text
                )
            )
            undo = QPushButton("Undo")
            undo.setToolTip("Restores the line this replaced")
            undo.clicked.connect(
                lambda _=False, aid=typed.assertion_id: self.undo_line(aid)
            )
            row_layout.addWidget(edit)
            row_layout.addWidget(undo)
            self._line_widgets.extend((edit, undo))
            self._lines_box.addWidget(row)
        if request is not None and self._editor is None:
            # The target has no row of its own — a proposal still awaiting a
            # decision, whose row sits in the proposals panel (which is built
            # once, at ``begin_review``). Its editor opens here, where every
            # other edit is made.
            row = QWidget()
            row_layout = QHBoxLayout(row)
            heading = QLabel("Your wording for the proposed line:")
            heading.setTextFormat(Qt.TextFormat.PlainText)
            row_layout.addWidget(heading)
            self._build_editor_row(row_layout, request)
            self._lines_box.addWidget(row)

    def _line_text(self, assertion_id: str) -> str:
        """The FULL text of a line in the working note — what the editor
        opens with, since a row's label is truncated to its leading words."""
        working = self._working
        if working is None:
            return ""
        for section in working.note_sections:
            for assertion in section.note_assertions:
                if assertion.assertion_id == assertion_id:
                    return assertion.text
        return ""

    def _build_editor_row(self, row_layout: QHBoxLayout, request: tuple[str, str]) -> None:
        """Render the open editor INSIDE ``row_layout``, in place of the
        row's label and buttons: the field, Apply and Cancel. Every widget
        joins ``_line_widgets``, so Save freezes them with the rest."""
        target_id, current_text = request
        editor = _LineEditor()
        editor.setText(current_text)
        editor.setToolTip("Type this line's wording. Enter applies it, Escape cancels.")
        editor.returnPressed.connect(self.commit_editor)
        editor.escape_pressed.connect(self.cancel_editor)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(lambda _=False: self.commit_editor())
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(lambda _=False: self.cancel_editor())
        row_layout.addWidget(editor, stretch=1)
        row_layout.addWidget(apply_button)
        row_layout.addWidget(cancel_button)
        self._line_widgets.extend((editor, apply_button, cancel_button))
        self._editor = (target_id, editor)

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

    def _refinalise(self) -> None:
        draft, document, config = self._draft, self._document, self._config
        if draft is None or document is None or config is None:
            return
        # D14: the WORKING draft — removed lines filtered out, additions
        # (quoted manual lines and typed lines) appended — is what every
        # check runs over.
        self._working = models.working_draft(
            draft,
            removed=self._removed,
            additions=(*self._manual.values(), *self._typed.values()),
        )
        # The resolution precedence (C3, D5) is `note_review.build_resolutions`;
        # the shown-text digests come from `_rendered_excerpt`, which each row
        # filled by reading its label back (`_build_proposal_rows`).
        resolutions = note_review.build_resolutions(
            draft,
            resolutions=self._resolutions,
            removed=self._removed,
            edited_proposals=self._edited_proposals,
            rendered_excerpt=self._rendered_excerpt,
            now=datetime.now(UTC),
        )
        note = finalise_note(self._working, resolutions, document, config)
        # D7: the note records the style it is rendered under; `model_copy`
        # changes that one field on the frozen model. Task 4.4: the previous
        # note's renderings are carried over where a section's texts are
        # unchanged (the digest binding decides — `carry_renderings`), then
        # the stage renders what is left.
        styled = note.model_copy(update={"style": self._note_style})
        self._note = models.carry_renderings(styled, self._note)
        self.note_body.setPlainText(models.format_note_body(self._note))
        self._refresh_proposal_states()
        self._refresh_warnings()
        self._rebuild_edit_controls()
        self._start_style_stage()
        self._update_controls()
        self._emit_state()

    # --- the prose stage (Task 4.4) -----------------------------------------

    def _start_style_stage(self) -> None:
        """Run the stage for the note as it stands, unless one is already in
        flight (its landing re-checks the digest and starts again) or every
        populated section already has a rendering bound to its current
        texts. Sets the in-flight line; `_update_controls` reads the job."""
        stage, note = self._prose_stage, self._note
        if stage is None or note is None or self._style_job is not None:
            return
        if not models.sections_to_render(note):
            return
        # The closure hands the note to the stage and keeps NO reference to
        # it afterwards (the session screen's holder pattern, PR rounds
        # 18/PR6): the thread object is a child of this widget, so anything
        # the closure retained would live as long as the tab does — past
        # `clear()`, past the review (round 20 MED-001).
        holder = [note]
        # Phase H round 24 MED-002: the job's abort flag. `_orphan_style_job`
        # (so `clear()` — Abandon, Cancel, Complete, Discard, a replacement
        # review) sets it, and the provider consults it before EACH section's
        # model call: an orphaned job stops after the call in progress
        # instead of handing the rest of a note whose review has ended — and
        # whose session key may already be gone — to the model.
        abort = threading.Event()
        job = TaskThread(lambda: stage(holder.pop(), abort=abort.is_set), self)
        self._style_job_abort = abort
        job.succeeded.connect(lambda result, job=job: self._on_style_done(job, result))
        job.failed.connect(lambda message, job=job: self._on_style_failed(job, message))
        # Disposal rides the thread's OWN `finished` signal (codex round 22
        # PR-MED-036): Qt emits it after `run` has returned, queued to this
        # thread, so the object is deleted only once the thread has provably
        # ended — never on the strength of a timed join.
        job.finished.connect(lambda job=job: self._dispose_style_job(job))
        self._style_job = job
        self.style_label.setText(models.rendering_in_flight_line(self._note_style))
        job.start()

    def _release_style_job(self, job: TaskThread) -> bool:
        """A job just REPORTED (its result or failure): stop treating it as
        the current job. True when it was; False for an orphan (the review
        it belonged to has ended). The thread object stays in
        `_orphaned_jobs` — and `is_busy` stays True — until its `finished`
        signal disposes it (`_dispose_style_job`)."""
        current = job is self._style_job
        if current:
            self._style_job = None
            self._style_job_abort = None
            self._orphaned_jobs.append(job)
        return current

    def _dispose_style_job(self, job: TaskThread) -> None:
        """The thread has ENDED (its `finished` signal): drop the last
        reference — the closure holds nothing (the holder was popped), the
        result was delivered by signal — and delete the object. Bounded
        join first only as a formality: `finished` fires after `run`
        returned."""
        job.finish()
        if not job.isFinished():
            # `finished` is emitted just before the thread ends; a join that
            # timed out leaves the object orphaned (and the tab busy) rather
            # than deleting a thread that is still running.
            if job is not self._style_job and job not in self._orphaned_jobs:
                self._orphaned_jobs.append(job)
            return
        if job is self._style_job:
            self._style_job = None
        if job in self._orphaned_jobs:
            self._orphaned_jobs.remove(job)
        job.setParent(None)
        job.deleteLater()
        self._update_controls()
        self._emit_state()

    def _orphan_style_job(self) -> None:
        """`clear()`: a running job cannot be joined on the GUI thread (the
        model may be mid-generation for seconds); keep its thread object
        alive until it reports, then drop its result."""
        job = self._style_job
        if job is None:
            return
        abort = self._style_job_abort
        if abort is not None:
            abort.set()  # MED-002: at most the section call in progress remains
        self._style_job_abort = None
        self._style_job = None
        self._orphaned_jobs.append(job)

    def _on_style_done(self, job: TaskThread, result: object) -> None:
        current = self._release_style_job(job)
        note = self._note
        if not current or note is None or self._prose_stage is None:
            return  # the review ended (or restarted) while the job ran
        assert isinstance(result, models.StyleStageResult)
        # Bind what still matches (a section edited meanwhile drops here),
        # DISPLAY it, and only then re-enable Save (`_update_controls`).
        refused_before = _refused_sections(note)
        self._note = models.bind_stage_result(note, result)
        # Phase H round 24 LOW-003: a `style_fallback` acknowledged for the
        # sections refused so far does not cover a section this result has
        # just refused — the only warning that can arrive OUTSIDE the
        # content-change path (which clears every acknowledgement). A new
        # refusal re-opens the code; Save waits for a fresh acknowledgement.
        if _refused_sections(self._note) - refused_before:
            self._acknowledged.discard("style_fallback")
        self.note_body.setPlainText(models.format_note_body(self._note))
        self.style_label.setText(models.style_stage_line(result, self._note))
        self._refresh_warnings()
        if result.note_digest != note_input_digest(self._note) and models.sections_to_render(
            self._note
        ):
            # Content changed during the job: render the sections it missed.
            self._start_style_stage()
        self._update_controls()
        self._emit_state()

    def _on_style_failed(self, job: TaskThread, message: object) -> None:
        current = self._release_style_job(job)
        if not current or self._note is None:
            return
        # An unexpected error in the stage (a model failure is a RESULT, not
        # this): nothing landed, the body already shows Clean clinical, and
        # Save is re-enabled because nothing unseen exists.
        label = models.STYLE_LABELS[self._note_style]
        reason = (
            f"Writing style '{label}': rendering failed ({message}) - this note is shown as "
            "Clean clinical."
        )
        self.style_label.setText(models.with_retained_prose(reason, self._note))
        self._update_controls()
        self._emit_state()

    @property
    def rendering_in_flight(self) -> bool:
        """True while a prose rendering job runs for the review (Save is
        disabled meanwhile — a Save must never persist unseen wording)."""
        return self._style_job is not None

    def _refresh_proposal_states(self) -> None:
        for proposal_id, label in self._state_labels.items():
            if proposal_id in self._edited_proposals:
                # Task 2.1: a typed line stands in for it — the decision
                # controls are inert until that line is undone.
                label.setText("Replaced by your typed line - Undo it to decide again.")
                continue
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
        if self._style_job is not None:
            # Click-time re-check (fail closed): the note under the button
            # would be the pre-rendering one, never shown with its prose.
            self.message_label.setText(models.SAVE_WHILE_RENDERING_MESSAGE)
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
        # committed; a learning failure never un-saves the note. Shorthand
        # rules and their counts follow (Task 2.3; C6), the same way.
        learned = self._write_learned_phrases()
        rules = self._write_learned_rules()
        reported = " ".join(part for part in (learned, rules) if part is not None)
        if reported:
            self._set_edit_status(reported)
        self._update_controls()
        self._emit_state()

    def _write_learned_rules(self) -> str | None:
        """Save-time write of the shorthand queue, the in-place wording
        replacements and the confirmation counts (the ONLY write; C6). Same
        gate as phrases: the learning status re-read now decides, so a
        profile deleted or opted out mid-review writes nothing. Returns the
        status-line text or None when this review touched no learned rule."""
        queued = list(self._rule_queue.values())
        replacements = list(self._rule_replacements.values())
        self._rule_queue.clear()
        self._rule_replacements.clear()
        # What this Save says about each LEARNED rule whose line was in play
        # (D5; `removed` wins) — `note_review.learned_rule_outcomes`.
        draft = self._draft
        outcomes = (
            {}
            if draft is None
            else note_review.learned_rule_outcomes(
                draft,
                resolutions=self._resolutions,
                removed=self._removed,
                edited_proposals=self._edited_proposals,
            )
        )
        if not queued and not replacements and not outcomes:
            return None
        status = self._refresh_learning_status()
        parts: list[str] = []
        changed = False
        now = datetime.now(UTC)
        if not status.enabled:
            # Learning off (round 12 MED-002): nothing NEW is learned and no
            # rule is PROMOTED — but a Remove still DEMOTES, because the
            # practitioner's own removal of a pre-filled line is the safe
            # direction whatever the consent state, and the line would
            # otherwise pre-fill again next time.
            if queued or replacements:
                parts.append(f"Shorthand not learned. {status.reason or ''}".strip())
            outcomes = {rid: o for rid, o in outcomes.items() if o == "removed"}
            queued, replacements = [], []
        # Counts FIRST (round 12 MED-001): a confirmation counts for the
        # wording that was actually shown; a correction below then resets
        # the rule to 0, so a new wording never inherits the old one's count.
        if outcomes:
            try:
                report = record_rule_outcomes(outcomes, config_root=self._config_root)
            except NoteConfigError as exc:
                parts.append(f"Shorthand counts were not updated - {type(exc).__name__}: {exc}")
            else:
                # Any persisted count (an ordinary 0→1 included) refreshes
                # the tab's "(confirmed N of 3)" text (peer round 14
                # PR-LOW-024), not only a promotion or demotion.
                changed = bool(report.updated)
                if report.auto_confirmed:
                    parts.append(
                        f"{len(report.auto_confirmed)} learned shorthand will now arrive "
                        "pre-filled (confirmed 3 times)."
                    )
                if report.demoted:
                    parts.append(
                        f"{len(report.demoted)} learned shorthand will propose again "
                        "(removed or declined)."
                    )
        if queued:
            try:
                outcome = append_learned_rules(
                    queued, config_root=self._config_root, learned_at=now
                )
            except NoteConfigError as exc:
                parts.append(f"Shorthand was not learned - {type(exc).__name__}: {exc}")
            else:
                if outcome.added:
                    listed = "; ".join(
                        f"'{rule.trigger_phrase}' -> '{rule.typed_wording[0]}' for "
                        f"{models.section_title(rule.section_key)}"
                        for rule in outcome.added
                    )
                    parts.append(f"Learned {len(outcome.added)} shorthand: {listed}.")
                    changed = True
                    if outcome.sidecar_error is not None:
                        parts.append(
                            "The date record could not be written, so they appear under "
                            f"Learned shorthand without a date ({outcome.sidecar_error})."
                        )
                for candidate, reason in outcome.skipped:
                    # The writer's reason is for its record; the line says
                    # the clinician's form (Phase H smoke item 2).
                    plain = plain_skip_reason(reason, candidate.typed_wording)
                    parts.append(
                        f"Shorthand '{candidate.trigger_phrase}' was not learned: {plain}."
                    )
        for rule_id, wording in replacements:
            try:
                replaced = replace_learned_rule_wording(
                    rule_id, wording, config_root=self._config_root, replaced_at=now
                )
            except NoteConfigError as exc:
                parts.append(f"Shorthand was not updated - {type(exc).__name__}: {exc}")
                continue
            if replaced.replaced:
                parts.append(f"Updated a learned shorthand rule's wording to '{wording}'.")
                changed = True
            else:
                detail = replaced.rules_file_error or (
                    plain_skip_reason(replaced.reason, wording) if replaced.reason else "unknown"
                )
                parts.append(f"Shorthand wording was not updated ({detail}).")
                # A rules write that failed AFTER the sidecar's reset landed
                # still changed what the tab lists (PR-LOW-024).
                changed = changed or replaced.rules_file_error is not None
        if changed:
            self.learned_phrases_changed.emit()
        if parts:
            parts.append("Review learned shorthand on the Practitioner tab.")
        return " ".join(parts) if parts else None

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
        PR-MED-002): the recorded copy flag (``models.COPY_TO_CLINIKO_ENABLED``,
        on since the practitioner's 2026-09-27 decision, D12) is NECESSARY but
        not sufficient — copy shares Complete's ratification bar. A note may
        reach any clipboard path only when the flag is on AND the review is
        fully ratified (no pending proposal, no blocking error, saved, no
        unacknowledged review — exactly what ``complete_block_reason``
        enforces), so an unresolved-error note can never be copied with the
        flag on."""
        return (
            self._copy_enabled
            and self._note is not None
            and models.complete_block_reason(self.current_review_state()) is None
        )

    def _apply_copy_binding(self) -> None:
        """Bind the copy affordance: the Copy BUTTON is visible per the
        recorded copy flag, but both the button's ENABLED state and the note
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
        counts = note_review.review_counts(
            draft,
            note,
            resolutions=self._resolutions,
            edited_proposals=self._edited_proposals,
            acknowledged=self._acknowledged,
        )
        return models.NoteReviewState(
            generating=not self._note_saved,
            has_note=True,
            unconfirmed_proposals=counts.unconfirmed_proposals,
            blocking_errors=counts.blocking_errors,
            unacknowledged_reviews=counts.unacknowledged_reviews,
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
            # Task 4.4 (codex PR-MED-015): never while a rendering is in
            # flight — Save snapshots `_note`, which must be what is shown.
            and self._style_job is None
        )
        self.save_button.setEnabled(save_ready)
        # D5: the button SAYS how many pre-filled lines this Save confirms —
        # the ones still in the note (not Removed, not replaced by a typed
        # line); after Save it reads plainly again.
        standing = sum(1 for line in self.prefilled_lines() if line.state == "prefilled")
        self.save_button.setText(
            models.save_button_label(0 if self._note_saved else standing)
        )
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
        the state during which a generation lease is held — OR while a prose
        rendering thread is still running (the current job, or one orphaned
        by a Cancel / Delete / Discard that has not yet ended; codex round 22
        PR-MED-036). Closing must wait: the in-progress note would be lost,
        and destroying a running QThread aborts the process (the PR-round-18
        PR6 hazard the window's close guard exists for)."""
        reviewing = self._draft is not None and not self._note_saved
        return reviewing or self._style_job is not None or bool(self._orphaned_jobs)
