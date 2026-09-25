"""The Practitioner tab: voice enrolment, consent, deletion, learned phrases
(practitioner-profile plan Phase 3, Task 3.1; Phase 5, Tasks 5.0 + 5.3).

The tab shows the CURRENT consent text VERBATIM (``models.CONSENT_TEXT_V3``,
version ``models.CONSENT_TEXT_VERSION``) with the consent checkbox and the
separate phrase-learning opt-in, a microphone pick, and a read-aloud of about
a minute. That read-aloud is captured IN MEMORY by
``enrolment.record_enrolment`` on a ``TaskThread`` (D8): no session is
created, no store is touched, no file is ever written, and the PCM is dropped
as soon as ``enrolment.enrol`` has turned it into one vector — the only thing
saved is the encrypted profile ``save_profile`` writes.

The whole capture -> embed -> save -> result-handler sequence runs under
``SessionController.begin_enrolment()`` (D15), so Start/Resume, the
microphone screen's monitor poll and the benchmark all refuse while it runs,
and Re-record/Delete are disabled meanwhile; the idle monitor itself is
handed over synchronously through ``on_capture_start`` (the main window
passes the microphone screen's ``stop_monitor``) before the worker starts.
The lease is released in the result handler — on EVERY path, success or
failure — never before it, so the status line a handler writes is already
visible when the activity ends.
``record_enrolment``'s ``on_progress`` callback fires on the worker thread,
so it is marshalled to the GUI thread through a Qt signal rather than
touching a widget directly.

Consent versions (Task 5.0). The consent box is pre-ticked ONLY from a
READABLE profile whose consent record carries the CURRENT text version. A
record carrying an older version (``consent-v1``, ``consent-v2``) is readable
but not current: the box stays unticked and editable, a one-line notice asks the
practitioner to read the new text and tick again, Record needs that fresh
tick, and phrase learning is treated as OFF until re-consent
(``models.learning_status``). "Confirm consent" re-saves the SAME vector
under the existing key with a current consent record — no re-recording —
and the same action saves a changed learning opt-in; a re-record saves the
opt-in too.

Re-record replaces the profile under the existing key; Delete asks for
confirmation and is KEY deletion (``delete_profile``: the key first, which is
the cryptographic death of the blob).

Learned phrases (Task 5.3, D9 as amended). "Recently learned" lists the last
``note_config.RECENTLY_LEARNED_LIMIT`` phrases the Note tab learned (the
sidecar's entries that still exist in the cue file, with their section and
date); "Learned phrases" lists every phrase in the user cue file the shipped
default does not carry, by section. Delete on either removes the phrase from
the cue file and the sidecar through ``note_config.delete_user_cue`` — the
loader stays the cue file's only reader; this tab never parses it itself.

Learned shorthand (note-learning plan Task 2.5) is the same shape one level
down: "Recently learned" and "All learned shorthand" list every learned rule
in the user rules file (``note_config.load_learned_rules``) with its trigger,
the wording it expands to and whether it still proposes or now arrives
pre-filled, and Delete removes the rule from the rules file and its sidecar
through ``note_config.delete_learned_rule``.

Writing style (note-learning plan Task 3.1). The "Writing style" group picks
how the note BODY reads on the Note tab; the choice is saved the moment a
radio is picked, into ``practitioner_settings.json`` through
``models.save_note_style`` (``note_config.PRACTITIONER_SETTINGS_FILENAME``,
never part of the config digest). All four styles are LISTED: Verbatim and
Clean clinical need no model and are always available; Own voice and
Narrative are disabled with a one-line reason under the group until the
local language model is installed, and Own voice also until a style has
been learned (C8 — a choice the app cannot honour yet is shown disabled
with its reason, never hidden). A saved style that is currently
unavailable stays SELECTED and disabled, with the Clean-clinical fallback
line (``models.style_fallback_line``) on the status line, and an unreadable
settings file shows its own line rather than silently rewriting the setting.
Option availability is ``models.style_options``, which STATS the learned-style
store — it never decrypts it. The model can be installed while the app runs,
so the 5 s availability poll re-checks ``models.language_model_available()``
(an import probe plus a STAT of the model file — never a load, never a
decrypt) and re-computes the options only when that presence CHANGES, which
is what enables the two prose radios without a restart (Task 4.4).

Learning from past notes (note-learning plan Tasks 3.4–3.6; D9, D10; C5,
C6). The "Learn from my notes" group takes one to five of the practitioner's
own notes (files chosen through a picker, or one pasted note) and, on the
GUI thread, reads them INTO MEMORY (``sample_notes.read_sample_note`` —
never copied, never moved), derives a draft (``learn_style_profile``: the
exemplar sentences are the ones THE refusal filter passed unchanged) and
shows it for review (``ui.style_review.run_style_review``: unrecognised
shorthand unticked by default, per-sentence remove). ONLY the review's Save
writes anything: ``sample_notes.build_style_profile`` (the review may only
remove) with the style store's OWN ``ConsentRecord`` — the consent box above
must be ticked, and NO voice profile is needed — then
``practitioner_profile.save_style_profile``. Deleting the originals is a
SEPARATE confirmation after the save (``run_delete_originals``: the paths
listed, the box unticked by default), and only then are exactly those paths
unlinked (``delete_sample_files``). The consent box is pre-ticked from the
VOICE profile's record only (PR-HIGH-006); a style record alone never
pre-ticks it — the practitioner ticks again to learn again, which costs a
click and leaks nothing.

The learned-style line (Task 3.5) and the "Learned style" group (Task 3.6)
are rendered from ONE decrypt of the style store
(``refresh_style_profile_state``), taken at construction and after a learn,
a per-item remove or a delete — NEVER from the 5 s availability poll, which
reads no store (round 51 MED-001; the microphone screen's poll renders stats
too, re-reading the VOICE profile only on a speaker-model presence
transition — round 55 PR-REG-006 — and never the style store). Remove on
either list rewrites the store; "Delete learned style" is key-first through
``delete_style_profile``, independent of the voice profile, and every style
change re-computes the writing-style options (``refresh_style_options``).

Enrolment is disabled only when the SELECTED embedder or the VAD model is
unavailable, and the message names ``scripts/setup-models.py`` (D16).

Nothing here logs, and no label ever renders a field of the profile beyond
its creation date and the embedder's ``model_id``.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop import note_config
from scribe_desktop.audio_capture import CaptureBackend
from scribe_desktop.enrolment import (
    DEFAULT_TARGET_SPEECH_SECONDS,
    EnrolmentCancelledError,
    EnrolmentProgress,
    enrol,
    record_enrolment,
)
from scribe_desktop.note import NoteStyle
from scribe_desktop.note_config import (
    DEFAULT_NOTE_STYLE,
    LEARNED_RULE_AUTO_CONFIRM_AFTER,
    MAX_SAMPLE_NOTES,
    NoteConfigError,
    StyleProfile,
    delete_user_cue,
    load_learned_phrases,
    load_learned_rules,
)
from scribe_desktop.practitioner_profile import (
    ConsentRecord,
    PractitionerProfile,
    ProfileError,
    ProfileUnusableError,
    delete_profile,
    delete_style_profile,
    load_style_profile,
    save_profile,
    save_style_profile,
    style_profile_present,
)
from scribe_desktop.sample_notes import (
    SampleNote,
    SampleNoteError,
    StyleProfileDraft,
    build_style_profile,
    delete_sample_files,
    learn_style_profile,
    read_sample_note,
)
from scribe_desktop.session import EnrolmentLease, SessionActivityError
from scribe_desktop.session_store import StoreWriteError
from scribe_desktop.speaker_embedding import (
    SHIPPED_SPEAKER_EMBEDDER,
    EmbedderKind,
    SpeakerEmbedder,
    build_speaker_embedder,
    speaker_embedder_available,
)
from scribe_desktop.speech import vad_model_available
from scribe_desktop.ui import models
from scribe_desktop.ui.style_review import (
    StyleReviewChoice,
    run_delete_originals,
    run_style_review,
)
from scribe_desktop.ui.tasks import TaskThread

_AVAILABILITY_POLL_MS: Final = 5000
DEVICE_NAME_MAX_CHARS: Final = 200  # PractitionerProfile.device_name's bound
UNKNOWN_DEVICE_NAME: Final = "unknown microphone"
NO_LEARNED_PHRASES_TEXT: Final = "No learned phrases yet."
NO_LEARNED_RULES_TEXT: Final = "No learned shorthand yet."
# Note-learning plan Task 3.4: the "Learn from my notes" group's copy.
LEARN_INTRO_TEXT: Final = (
    f"Teach the scribe your note style from 1-{MAX_SAMPLE_NOTES} of your own past notes "
    "(.txt, .docx or .pdf), or paste one note below. The notes are read, never copied; what "
    "would be kept is shown for review before anything is saved, and you are asked "
    "separately whether to delete the original files afterwards."
)
LEARN_CONSENT_GATE_TEXT: Final = (
    "Tick the consent box above to learn from your notes (no voice profile is needed)."
)
LEARN_NOTHING_CHOSEN_TEXT: Final = f"Choose 1-{MAX_SAMPLE_NOTES} notes or paste one first."
LEARN_CANCELLED_TEXT: Final = "Nothing was saved - the review was cancelled."
NO_LEARNED_STYLE_TEXT: Final = "No learned style yet."
SAMPLE_NOTE_FILTER: Final = "Notes (*.txt *.docx *.pdf)"

CaptureFn = Callable[
    [CaptureBackend, int, Callable[[EnrolmentProgress], None], Callable[[], bool]], bytes
]
EmbedFn = Callable[[bytes, SpeakerEmbedder], tuple[Any, float]]
LearnerFn = Callable[[Sequence[SampleNote]], StyleProfileDraft]
ReviewRunner = Callable[[StyleProfileDraft, QWidget], StyleReviewChoice | None]
DeleteOriginalsRunner = Callable[[Sequence[Path], QWidget], bool]


def _default_capture(
    backend: CaptureBackend,
    device_id: int,
    on_progress: Callable[[EnrolmentProgress], None],
    should_stop: Callable[[], bool],
) -> bytes:
    return record_enrolment(backend, device_id, on_progress=on_progress, should_stop=should_stop)


def _default_embed(pcm: bytes, embedder: SpeakerEmbedder) -> tuple[Any, float]:
    return enrol(pcm, embedder)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def profile_device_name(name: str) -> str:
    """A device name reduced to what ``PractitionerProfile.device_name``
    accepts: printable, single-line, at most ``DEVICE_NAME_MAX_CHARS``. Every
    non-printable character, and every whitespace character other than a plain
    space, becomes a space; an empty result becomes ``UNKNOWN_DEVICE_NAME``.
    So a device name can never fail the profile's validation."""
    cleaned = "".join(
        " " if (not ch.isprintable() or (ch.isspace() and ch != " ")) else ch for ch in name
    )
    cleaned = cleaned.strip()[:DEVICE_NAME_MAX_CHARS]
    return cleaned if cleaned else UNKNOWN_DEVICE_NAME


def _rule_flag(rule: note_config.LearnedRule) -> str:
    """What a listed learned rule's line says about its state: pre-filled
    (auto-confirmed, D5) or how far its confirmations have got."""
    if rule.auto_confirmed:
        return " (pre-filled)"
    return f" (confirmed {rule.confirmations} of {LEARNED_RULE_AUTO_CONFIRM_AFTER})"


class PractitionerScreen(QWidget):
    # Emitted from the CAPTURE WORKER thread; delivered queued to the GUI slot
    # (`record_enrolment` calls `on_progress` on the thread it runs on).
    _progress_reported = Signal(object)
    # Emitted on the GUI thread whenever this tab re-reads the profile store
    # (after a save, a re-consent, a delete, a failed attempt — every
    # `refresh_profile_state`), so the microphone screen's voice-profile
    # report line is re-read THEN and not on its 5 s poll (round 51 MED-001).
    profile_changed = Signal()

    def __init__(
        self,
        controller: models.SessionControllerLike,
        backend: CaptureBackend,
        *,
        profile_root: Path | None = None,
        config_root: Path | None = None,
        style_root: Path | None = None,
        style_options_provider: Callable[[], tuple[models.StyleOption, ...]] | None = None,
        language_model_available: Callable[[], bool] | None = None,
        embedder_kind: EmbedderKind = SHIPPED_SPEAKER_EMBEDDER,
        embedder_factory: Callable[[EmbedderKind], SpeakerEmbedder] = build_speaker_embedder,
        embedder_available: Callable[[EmbedderKind], bool] = speaker_embedder_available,
        vad_available: Callable[[], bool] = vad_model_available,
        capture: CaptureFn = _default_capture,
        embed: EmbedFn = _default_embed,
        readiness_provider: Callable[[], models.AttributionReadiness] | None = None,
        confirm_delete: Callable[[], bool] | None = None,
        clock: Callable[[], datetime] = _utc_now,
        on_capture_start: Callable[[], None] | None = None,
        file_picker: Callable[[], Sequence[Path]] | None = None,
        learner: LearnerFn = learn_style_profile,
        review_runner: ReviewRunner = run_style_review,
        delete_originals_runner: DeleteOriginalsRunner = run_delete_originals,
        confirm_delete_style: Callable[[], bool] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._backend = backend
        # Peer round 27 PR-MED-022: the main window passes the microphone
        # screen's `stop_monitor` so the idle monitor is handed over
        # SYNCHRONOUSLY, before the worker can open the device.
        self._on_capture_start = on_capture_start
        self._profile_root = profile_root
        self._config_root = config_root
        # The learned-style store root: `models.style_options` STATS it for
        # the Own-voice option (`style_profile_present`), it never decrypts it.
        self._style_root = style_root
        # Phase H round 24 MED-006: the language model's presence is a test
        # seam like every other host-state input (docs/lessons.md 2026-09-24
        # — a test must never read whether THIS host has the 2.3 GiB model).
        # None resolves `models.language_model_available` at CALL time, so a
        # monkeypatch of the module attribute still takes effect. The default
        # options provider asks the SAME probe (round 25 R25-01): the
        # `style_options` default would otherwise bind the real probe at
        # definition time and bypass the seam.
        self._language_model_probe = language_model_available
        self._style_options_provider: Callable[[], tuple[models.StyleOption, ...]] = (
            style_options_provider
            if style_options_provider is not None
            else (
                lambda: models.style_options(
                    style_root=style_root, model_available=self._probe_language_model
                )
            )
        )
        # The "Writing style" status line's two parts (MED-005): the base
        # text and the fallback line of a disabled saved style.
        self._style_status_base = ""
        self._style_status_fallback: str | None = None
        self._embedder_kind = embedder_kind
        self._embedder_factory = embedder_factory
        self._embedder_available = embedder_available
        self._vad_available = vad_available
        self._capture = capture
        self._embed = embed
        self._readiness_provider: Callable[[], models.AttributionReadiness] = (
            readiness_provider
            if readiness_provider is not None
            else (
                lambda: models.attribution_readiness(
                    profile_root=profile_root, kind=embedder_kind
                )
            )
        )
        self._confirm_delete = confirm_delete if confirm_delete is not None else self._ask_delete
        self._clock = clock
        # Task 3.4 / 3.6 seams: the file picker (a modal dialog in the app),
        # the learner (pure over the read notes), the two Flow-4 dialogs and
        # the delete-style confirmation.
        self._file_picker = file_picker if file_picker is not None else self._pick_files
        self._learner = learner
        self._review_runner = review_runner
        self._delete_originals_runner = delete_originals_runner
        self._confirm_delete_style = (
            confirm_delete_style if confirm_delete_style is not None else self._ask_delete_style
        )
        self._sample_files: list[Path] = []
        # The learned style as last READ from its store (one decrypt per
        # learn / remove / delete / consent-renewal event, never per poll);
        # None when absent or
        # unusable — `_style_present` (a stat) still enables Delete then.
        self._style_profile: StyleProfile | None = None
        self._style_present = False

        self._task: TaskThread | None = None
        self._lease: EnrolmentLease | None = None
        self._cancel_requested = threading.Event()
        self._available = False
        self._profile_present = False
        self._profile: PractitionerProfile | None = None
        # Task 5.0: whether the READABLE profile's consent record is current.
        self._consent_current = False
        self._device_names: dict[int, str] = {}
        # Task 3.1: the style as it stands ON DISK (never a pending pick), and
        # which styles may be chosen right now.
        self._saved_style: NoteStyle = DEFAULT_NOTE_STYLE
        self._style_enabled: dict[NoteStyle, bool] = {}

        # --- first-run banner (D10: first run ASKS, never blocks) -----------
        self.banner_label = QLabel()
        self.banner_label.setTextFormat(Qt.TextFormat.PlainText)
        self.banner_label.setWordWrap(True)
        self.banner_label.setStyleSheet("font-weight: bold;")
        self.banner_label.hide()

        # --- profile state --------------------------------------------------
        self.profile_status_label = QLabel()
        self.profile_status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.profile_status_label.setWordWrap(True)
        profile_box = QGroupBox("Voice profile")
        profile_layout = QVBoxLayout()
        profile_layout.addWidget(self.profile_status_label)
        profile_box.setLayout(profile_layout)

        # --- consent (the CURRENT text VERBATIM) -----------------------------
        self.consent_text_label = QLabel(models.CONSENT_TEXT_V3)
        self.consent_text_label.setTextFormat(Qt.TextFormat.PlainText)
        self.consent_text_label.setWordWrap(True)
        self.consent_notice_label = QLabel(models.CONSENT_STALE_NOTICE)
        self.consent_notice_label.setTextFormat(Qt.TextFormat.PlainText)
        self.consent_notice_label.setWordWrap(True)
        self.consent_notice_label.setStyleSheet("font-weight: bold;")
        self.consent_notice_label.hide()
        self.consent_checkbox = QCheckBox(models.CONSENT_CHECKBOX_LABEL)
        self.consent_checkbox.setChecked(False)
        self.consent_checkbox.toggled.connect(lambda *_: self._update_controls())
        self.learning_checkbox = QCheckBox(models.LEARNING_OPT_IN_LABEL)
        self.learning_checkbox.setChecked(False)
        self.learning_checkbox.toggled.connect(lambda *_: self._update_controls())
        self.learning_note_label = QLabel(
            "Press Confirm consent to save this choice, or it is saved when you next "
            "record your voice (the saved choice stands until then)."
        )
        self.learning_note_label.setWordWrap(True)
        self.learning_note_label.hide()
        self.confirm_consent_button = QPushButton(models.CONFIRM_CONSENT_BUTTON_LABEL)
        self.confirm_consent_button.setToolTip(
            "Save your consent to the current text, and your phrase-learning choice, "
            "without re-recording your voice."
        )
        self.confirm_consent_button.clicked.connect(self.on_confirm_consent)
        self.confirm_consent_button.hide()
        consent_box = QGroupBox("Consent")
        consent_layout = QVBoxLayout()
        consent_layout.addWidget(self.consent_text_label)
        consent_layout.addWidget(self.consent_notice_label)
        consent_layout.addWidget(self.consent_checkbox)
        consent_layout.addWidget(self.learning_checkbox)
        consent_layout.addWidget(self.learning_note_label)
        consent_layout.addWidget(self.confirm_consent_button)
        consent_box.setLayout(consent_layout)

        # --- the read-aloud --------------------------------------------------
        self.device_combo = QComboBox()
        self.refresh_devices_button = QPushButton("Refresh devices")
        self.refresh_devices_button.clicked.connect(self.refresh_devices)
        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Microphone:"))
        device_row.addWidget(self.device_combo, stretch=1)
        device_row.addWidget(self.refresh_devices_button)

        self.availability_label = QLabel()
        self.availability_label.setTextFormat(Qt.TextFormat.PlainText)
        self.availability_label.setWordWrap(True)
        self.availability_label.setStyleSheet("color: #b00020;")
        self.availability_label.hide()

        self.record_button = QPushButton("Record my voice (about a minute)")
        self.record_button.clicked.connect(self.on_record)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.on_stop)
        self.stop_button.hide()
        button_row = QHBoxLayout()
        button_row.addWidget(self.record_button)
        button_row.addWidget(self.stop_button)

        self.level_bar = QProgressBar()
        self.level_bar.setRange(0, 100)
        self.level_bar.setValue(0)
        self.level_bar.setTextVisible(False)
        self.progress_label = QLabel(self._progress_text(0.0))
        self.enrolment_status_label = QLabel()
        self.enrolment_status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.enrolment_status_label.setWordWrap(True)
        self.enrolment_status_label.hide()

        record_box = QGroupBox("Record your voice")
        record_layout = QVBoxLayout()
        record_layout.addLayout(device_row)
        record_layout.addWidget(self.availability_label)
        record_layout.addLayout(button_row)
        record_layout.addWidget(QLabel("Input level:"))
        record_layout.addWidget(self.level_bar)
        record_layout.addWidget(self.progress_label)
        record_layout.addWidget(self.enrolment_status_label)
        record_box.setLayout(record_layout)

        # --- deletion ---------------------------------------------------------
        self.delete_button = QPushButton("Delete voice profile")
        self.delete_button.clicked.connect(self.on_delete)

        # --- writing style (note-learning plan Task 3.1) ---------------------
        # All four styles are listed; the ones that cannot be honoured yet are
        # disabled with their reason under the group (C8), never hidden.
        self.style_button_group = QButtonGroup(self)
        self.style_button_group.setExclusive(True)
        self.style_radios: dict[NoteStyle, QRadioButton] = {}
        style_box = QGroupBox("Writing style")
        style_layout = QVBoxLayout()
        style_layout.addWidget(
            QLabel(
                "How the note body reads on the Note tab (Verbatim and Clean clinical "
                "need no model):"
            )
        )
        for style in models.NOTE_STYLES:
            radio = QRadioButton(models.STYLE_LABELS[style])
            radio.toggled.connect(
                lambda checked, style=style: (
                    self.on_style_selected(style) if checked else None
                )
            )
            self.style_button_group.addButton(radio)
            self.style_radios[style] = radio
            style_layout.addWidget(radio)
        # PLAIN TEXT: both labels render loader errors, which quote config text.
        self.style_reason_label = QLabel()
        self.style_reason_label.setTextFormat(Qt.TextFormat.PlainText)
        self.style_reason_label.setWordWrap(True)
        self.style_reason_label.hide()
        self.style_status_label = QLabel()
        self.style_status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.style_status_label.setWordWrap(True)
        self.style_status_label.hide()
        style_layout.addWidget(self.style_reason_label)
        style_layout.addWidget(self.style_status_label)
        style_box.setLayout(style_layout)

        # --- learned phrases (Task 5.3) -------------------------------------
        # Both lists render the practitioner's OWN learned phrases (config
        # plaintext), each item's data holding the stored phrase for Delete.
        self.recently_learned_list = QListWidget()
        self.delete_recent_button = QPushButton("Delete selected")
        self.delete_recent_button.clicked.connect(
            lambda *_: self._delete_selected(self.recently_learned_list)
        )
        self.learned_phrases_list = QListWidget()
        self.delete_learned_button = QPushButton("Delete selected")
        self.delete_learned_button.clicked.connect(
            lambda *_: self._delete_selected(self.learned_phrases_list)
        )
        # PLAIN TEXT: this label renders loader errors, which quote config text.
        self.learned_phrases_note_label = QLabel(NO_LEARNED_PHRASES_TEXT)
        self.learned_phrases_note_label.setTextFormat(Qt.TextFormat.PlainText)
        self.learned_phrases_note_label.setWordWrap(True)
        phrases_box = QGroupBox("Learned phrases")
        phrases_layout = QVBoxLayout()
        phrases_layout.addWidget(
            QLabel("Recently learned (phrases from lines you added or moved, newest first):")
        )
        phrases_layout.addWidget(self.recently_learned_list)
        phrases_layout.addWidget(self.delete_recent_button)
        phrases_layout.addWidget(QLabel("All learned phrases, by section:"))
        phrases_layout.addWidget(self.learned_phrases_list)
        phrases_layout.addWidget(self.delete_learned_button)
        phrases_layout.addWidget(self.learned_phrases_note_label)
        phrases_box.setLayout(phrases_layout)

        # --- learned shorthand (note-learning plan Task 2.5) -----------------
        # Both lists render the practitioner's OWN learned rules (config
        # plaintext), each item's data holding the rule id for Delete.
        self.recently_learned_rules_list = QListWidget()
        self.delete_recent_rule_button = QPushButton("Delete selected")
        self.delete_recent_rule_button.clicked.connect(
            lambda *_: self._delete_selected_rule(self.recently_learned_rules_list)
        )
        self.learned_rules_list = QListWidget()
        self.delete_learned_rule_button = QPushButton("Delete selected")
        self.delete_learned_rule_button.clicked.connect(
            lambda *_: self._delete_selected_rule(self.learned_rules_list)
        )
        # PLAIN TEXT: this label renders loader errors, which quote config text.
        self.learned_rules_note_label = QLabel(NO_LEARNED_RULES_TEXT)
        self.learned_rules_note_label.setTextFormat(Qt.TextFormat.PlainText)
        self.learned_rules_note_label.setWordWrap(True)
        rules_box = QGroupBox("Learned shorthand")
        rules_layout = QVBoxLayout()
        rules_layout.addWidget(
            QLabel("Recently learned (shorthand from lines you typed over, newest first):")
        )
        rules_layout.addWidget(self.recently_learned_rules_list)
        rules_layout.addWidget(self.delete_recent_rule_button)
        rules_layout.addWidget(QLabel("All learned shorthand, by section:"))
        rules_layout.addWidget(self.learned_rules_list)
        rules_layout.addWidget(self.delete_learned_rule_button)
        rules_layout.addWidget(self.learned_rules_note_label)
        rules_box.setLayout(rules_layout)

        # --- learn from my notes (note-learning plan Task 3.4) ---------------
        # PLAIN TEXT throughout: the status lines quote file names and reader
        # errors; nothing here renders a note's text (the review dialog does).
        self.learn_intro_label = QLabel(LEARN_INTRO_TEXT)
        self.learn_intro_label.setTextFormat(Qt.TextFormat.PlainText)
        self.learn_intro_label.setWordWrap(True)
        self.choose_files_button = QPushButton(f"Choose notes (up to {MAX_SAMPLE_NOTES})")
        self.choose_files_button.clicked.connect(self.on_choose_files)
        self.sample_files_list = QListWidget()
        self.remove_file_button = QPushButton("Remove selected")
        self.remove_file_button.clicked.connect(self._remove_selected_file)
        self.paste_box = QPlainTextEdit()
        self.paste_box.setPlaceholderText("Or paste one note here")
        self.paste_box.textChanged.connect(self._update_controls)
        self.learn_button = QPushButton("Learn from these notes")
        self.learn_button.clicked.connect(self.on_learn_from_notes)
        self.learn_gate_label = QLabel(LEARN_CONSENT_GATE_TEXT)
        self.learn_gate_label.setTextFormat(Qt.TextFormat.PlainText)
        self.learn_gate_label.setWordWrap(True)
        self.learn_status_label = QLabel()
        self.learn_status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.learn_status_label.setWordWrap(True)
        self.learn_status_label.hide()
        learn_box = QGroupBox("Learn from my notes")
        learn_layout = QVBoxLayout()
        learn_layout.addWidget(self.learn_intro_label)
        learn_layout.addWidget(self.choose_files_button)
        learn_layout.addWidget(self.sample_files_list)
        learn_layout.addWidget(self.remove_file_button)
        learn_layout.addWidget(self.paste_box)
        learn_layout.addWidget(self.learn_gate_label)
        learn_layout.addWidget(self.learn_button)
        learn_layout.addWidget(self.learn_status_label)
        learn_box.setLayout(learn_layout)

        # --- learned style (note-learning plan Tasks 3.5 + 3.6) --------------
        # The lists render the practitioner's OWN example sentences and
        # shorthand (decrypted style-store content), each item's data holding
        # the exemplar's index / the token for Remove.
        self.style_line_label = QLabel(models.STYLE_NOT_LEARNED_LINE)
        self.style_line_label.setTextFormat(Qt.TextFormat.PlainText)
        self.style_line_label.setWordWrap(True)
        self.learned_exemplars_list = QListWidget()
        self.remove_exemplar_button = QPushButton("Remove selected sentence")
        self.remove_exemplar_button.clicked.connect(self._remove_selected_exemplar)
        self.learned_shorthand_list = QListWidget()
        self.remove_shorthand_button = QPushButton("Remove selected shorthand")
        self.remove_shorthand_button.clicked.connect(self._remove_selected_shorthand)
        self.delete_style_button = QPushButton("Delete learned style")
        self.delete_style_button.clicked.connect(self.on_delete_style)
        self.learned_style_note_label = QLabel(NO_LEARNED_STYLE_TEXT)
        self.learned_style_note_label.setTextFormat(Qt.TextFormat.PlainText)
        self.learned_style_note_label.setWordWrap(True)
        learned_style_box = QGroupBox("Learned style")
        learned_style_layout = QVBoxLayout()
        learned_style_layout.addWidget(self.style_line_label)
        learned_style_layout.addWidget(QLabel("Example sentences kept (by section):"))
        learned_style_layout.addWidget(self.learned_exemplars_list)
        learned_style_layout.addWidget(self.remove_exemplar_button)
        learned_style_layout.addWidget(QLabel("Shorthand kept:"))
        learned_style_layout.addWidget(self.learned_shorthand_list)
        learned_style_layout.addWidget(self.remove_shorthand_button)
        learned_style_layout.addWidget(self.delete_style_button)
        learned_style_layout.addWidget(self.learned_style_note_label)
        learned_style_box.setLayout(learned_style_layout)

        layout = QVBoxLayout()
        layout.addWidget(self.banner_label)
        layout.addWidget(profile_box)
        layout.addWidget(consent_box)
        layout.addWidget(record_box)
        layout.addWidget(self.delete_button)
        layout.addWidget(style_box)
        layout.addWidget(learn_box)
        layout.addWidget(learned_style_box)
        layout.addWidget(phrases_box)
        layout.addWidget(rules_box)
        layout.addStretch(1)
        # Nine groups stacked in one column outgrow any ordinary window: the
        # tab SCROLLS vertically (note-learning plan Phase 4 live smoke,
        # 2026-09-20: "make a scroll button because i can't read the stuff" —
        # at 1920×1200 the lists collapsed to slivers). The content widget
        # keeps every group at its natural height; the width follows the tab
        # (no horizontal bar — every long label word-wraps), so the widgets
        # the tests reach by attribute are unchanged, one level deeper.
        self.scroll_content = QWidget()
        self.scroll_content.setLayout(layout)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.scroll_area)
        self.setLayout(outer)

        self._progress_reported.connect(self._on_progress)

        # Task 4.4: the language model's presence as the last poll saw it, so
        # the poll can spot a TRANSITION (installed / removed while the app
        # runs) and re-compute the style options then and only then. Taken
        # before the timer starts, so the first tick compares against a real
        # value rather than a guess.
        self._language_model_available = self._probe_language_model()

        self._availability_timer = QTimer(self)
        self._availability_timer.setInterval(_AVAILABILITY_POLL_MS)
        self._availability_timer.timeout.connect(self.refresh_availability)
        self._availability_timer.start()

        self.refresh_devices()
        self.refresh_availability()
        self.refresh_profile_state()
        self.refresh_style_profile_state()  # one style-store read; before the options
        self.refresh_style_setting()
        self.refresh_learned_phrases()
        self.refresh_learned_rules()

    # --- text helpers --------------------------------------------------------

    def _progress_text(self, speech_seconds: float) -> str:
        return (
            f"Speech heard: {speech_seconds:.0f} s of "
            f"{DEFAULT_TARGET_SPEECH_SECONDS:.0f} s"
        )

    def _ask_delete(self) -> bool:
        return (
            QMessageBox.question(
                self,
                "Delete voice profile",
                "Delete your voice profile? Consultations go back to the manual "
                "clinician confirmation until you record again.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

    # --- devices --------------------------------------------------------------

    def refresh_devices(self) -> None:
        current = self.device_combo.currentData()
        self.device_combo.clear()
        try:
            devices = self._backend.list_input_devices()
        except Exception:  # noqa: BLE001 - enumeration failure must not crash the UI
            devices = []
        for device in devices:
            self._device_names[device.device_id] = device.name
            label = device.name + (" (default)" if device.is_default else "")
            self.device_combo.addItem(label, device.device_id)
            if device.is_default and current is None:
                self.device_combo.setCurrentIndex(self.device_combo.count() - 1)
        if current is not None:
            index = self.device_combo.findData(current)
            if index >= 0:
                self.device_combo.setCurrentIndex(index)
        self._update_controls()

    def selected_device(self) -> tuple[int, str] | None:
        """``(device_id, raw device name)`` for the selected microphone."""
        data = self.device_combo.currentData()
        if data is None:
            return None
        device_id = int(data)
        return device_id, self._device_names.get(device_id, UNKNOWN_DEVICE_NAME)

    # --- model availability (D16) ---------------------------------------------

    def refresh_availability(self) -> None:
        model_ok = self._embedder_available(self._embedder_kind)
        vad_ok = self._vad_available()
        lines: list[str] = []
        if not model_ok:
            lines.append(
                "Voice enrolment is unavailable: the speaker model is not installed - "
                "run scripts/setup-models.py --only speaker-embedding."
            )
        if not vad_ok:
            lines.append(
                "Voice enrolment is unavailable: the VAD model (silero) is not "
                "installed - run scripts/setup-models.py."
            )
        self._available = model_ok and vad_ok
        self.availability_label.setText("\n".join(lines))
        if lines:
            self.availability_label.show()
        else:
            self.availability_label.hide()
        self._update_controls()
        # Task 4.4: the two prose radios enable as soon as the local language
        # model is installed. `models.language_model_available()` is an import
        # probe plus a stat, so the poll may ask it every tick; only a CHANGE
        # re-computes the options, and the provider stats the learned-style
        # store too — it never decrypts it (round 51 MED-001 is about profile
        # decrypts and is untouched).
        language_ok = self._probe_language_model()
        if language_ok != self._language_model_available:
            self._language_model_available = language_ok
            self.refresh_style_options()

    def _probe_language_model(self) -> bool:
        """The injected presence probe, or ``models.language_model_available``
        resolved now (never bound at construction — MED-006)."""
        probe = self._language_model_probe
        if probe is None:
            probe = models.language_model_available
        return probe()

    # --- profile state ---------------------------------------------------------

    def refresh_profile_state(self) -> None:
        """Re-read the profile store (one profile read, no model loaded) and
        re-render everything that depends on it."""
        previously_readable = self._profile is not None
        previously_current = self._consent_current
        readiness = self._readiness_provider()
        self._profile_present = readiness.profile_present
        self._profile = readiness.profile
        self._consent_current = (
            readiness.profile is not None and models.consent_is_current(readiness.profile)
        )
        if not readiness.profile_present:
            self.profile_status_label.setText("No voice profile yet.")
        elif readiness.profile is not None:
            profile = readiness.profile
            self.profile_status_label.setText(
                f"Voice profile saved {profile.created_at:%Y-%m-%d} "
                f"(model {profile.model_id})."
            )
        else:
            self.profile_status_label.setText(
                readiness.reason or models.ATTRIBUTION_DID_NOT_RUN_REASON
            )
        self.consent_notice_label.setVisible(
            self._profile is not None and not self._consent_current
        )
        if readiness.profile_present:
            if self._profile is not None:
                # A READABLE profile carries the consent record ticked when it
                # was saved: that record pre-ticks the box ONLY when it is
                # CURRENT (peer round 27 PR-HIGH-006; Task 5.0). An older
                # version is not consent to the current text: the box is left
                # editable for a fresh tick — and a tick that came from a
                # record that was current is withdrawn when the record is
                # found stale (a fresh tick the practitioner just made stands).
                # An unreadable blob is NOT evidence of consent — its box stays
                # as it is (unticked on construction) and enabled, so recording
                # over it needs a fresh tick; Delete stays available either way.
                if self._consent_current:
                    self.consent_checkbox.setChecked(True)
                elif previously_current:
                    self.consent_checkbox.setChecked(False)
                self.learning_checkbox.setChecked(self._profile.consent.learning_opt_in)
                self.learning_note_label.show()
            else:
                if previously_readable:
                    # The tick on show came from a record that is now
                    # unreadable (an interrupted Delete in this session): it
                    # is withdrawn with the record; a tick the practitioner
                    # made over an already-unreadable blob is kept.
                    self.consent_checkbox.setChecked(False)
                self.learning_note_label.hide()
            self.record_button.setText("Re-record my voice")
            self.banner_label.hide()
        else:
            # The checkboxes are left AS THEY ARE: a failed enrolment must not
            # make the practitioner tick consent again.
            self.learning_note_label.hide()
            self.record_button.setText("Record my voice (about a minute)")
        self._update_controls()
        self.profile_changed.emit()

    @property
    def profile_present(self) -> bool:
        return self._profile_present

    @property
    def consent_current(self) -> bool:
        """True when a readable profile's consent record carries the current
        text version (Task 5.0)."""
        return self._consent_current

    @property
    def is_busy(self) -> bool:
        """True while the enrolment worker runs (close must wait — D15)."""
        return self._task is not None and self._task.isRunning()

    def show_first_run_banner(self) -> None:
        """The first-run banner (D10): the voice-profile line, plus the
        sample-note line while no learned style exists (Task 3.4, Flow 4 —
        optional, never blocking). Presence is a stat."""
        self.banner_label.setText(models.first_run_banner_text(style_present=self._style_present))
        self.banner_label.show()

    # --- enablement --------------------------------------------------------------

    def _update_controls(self) -> None:
        busy = self.is_busy
        self.record_button.setEnabled(
            not busy
            and self._available
            and self.consent_checkbox.isChecked()
            and self.selected_device() is not None
        )
        self.stop_button.setVisible(busy)
        self.stop_button.setEnabled(busy and not self._cancel_requested.is_set())
        self.delete_button.setEnabled(not busy and self._profile_present)
        self.device_combo.setEnabled(not busy)
        self.refresh_devices_button.setEnabled(not busy)
        # Consent is fixed while a READABLE profile with a CURRENT record
        # exists (withdrawal is Delete); an unreadable blob or a stale record
        # leaves it editable (PR-HIGH-006; Task 5.0). The learning opt-in
        # stays editable whenever idle — saved by Confirm consent or at the
        # next (re-)record (PR-MED-021).
        self.consent_checkbox.setEnabled(not busy and not self._consent_current)
        self.learning_checkbox.setEnabled(not busy)
        profile = self._profile
        # Codex round 31 PR-LOW-048: "Confirm consent" renews BOTH stores —
        # shown when either profile exists, enabled when the box is ticked
        # and the voice record is stale (or its opt-in changed) or the STYLE
        # record is stale; the style store had no renewal path of its own.
        learned = self._style_profile
        style_stale = learned is not None and not models.consent_is_current(learned)
        voice_needs = profile is not None and (
            not self._consent_current
            or self.learning_checkbox.isChecked() != profile.consent.learning_opt_in
        )
        self.confirm_consent_button.setVisible(profile is not None or learned is not None)
        self.confirm_consent_button.setEnabled(
            not busy and self.consent_checkbox.isChecked() and (voice_needs or style_stale)
        )
        self.delete_recent_button.setEnabled(
            not busy and self.recently_learned_list.count() > 0
        )
        self.delete_learned_button.setEnabled(
            not busy and self.learned_phrases_list.count() > 0
        )
        self.delete_recent_rule_button.setEnabled(
            not busy and self.recently_learned_rules_list.count() > 0
        )
        self.delete_learned_rule_button.setEnabled(
            not busy and self.learned_rules_list.count() > 0
        )
        for style, radio in self.style_radios.items():
            radio.setEnabled(not busy and self._style_enabled.get(style, False))
        # Task 3.4: the consent gate is the SAME box the voice enrolment uses
        # (the v3 text covers the learned style); the button also needs
        # something to learn from, within the cap.
        consented = self.consent_checkbox.isChecked()
        chosen = len(self._sample_files) + (1 if self.paste_box.toPlainText().strip() else 0)
        self.learn_gate_label.setVisible(not consented)
        self.choose_files_button.setEnabled(not busy and len(self._sample_files) < MAX_SAMPLE_NOTES)
        self.remove_file_button.setEnabled(not busy and self.sample_files_list.count() > 0)
        self.learn_button.setEnabled(not busy and consented and 1 <= chosen <= MAX_SAMPLE_NOTES)
        # Task 3.6: Remove needs a READABLE profile; Delete needs only presence.
        readable = self._style_profile is not None
        self.remove_exemplar_button.setEnabled(
            not busy and readable and self.learned_exemplars_list.count() > 0
        )
        self.remove_shorthand_button.setEnabled(
            not busy and readable and self.learned_shorthand_list.count() > 0
        )
        self.delete_style_button.setEnabled(not busy and self._style_present)

    def _set_enrolment_status(self, message: str | None) -> None:
        if message is None:
            self.enrolment_status_label.setText("")
            self.enrolment_status_label.hide()
        else:
            self.enrolment_status_label.setText(message)
            self.enrolment_status_label.show()

    # --- re-consent without re-record (Task 5.0) ----------------------------------

    def on_confirm_consent(self) -> None:
        """Re-save each present profile under its existing key with a consent
        record for the CURRENT text and the learning opt-in as ticked: the
        SAME voice vector (``save_profile`` replaces only ``voice.enc``) and —
        codex round 31 PR-LOW-048 — the SAME learned style (``save_style_profile``
        replaces only ``style.enc``; the reviewed exemplars are untouched),
        which had no renewal path of its own. Needs a ticked consent box and
        at least one readable profile; runs on the GUI thread (small atomic
        file replaces, no microphone, no lease)."""
        profile, style = self._profile, self._style_profile
        if self.is_busy or not self.consent_checkbox.isChecked():
            return
        if profile is None and style is None:
            return
        consent = ConsentRecord(
            accepted_at=self._clock(),
            consent_text_version=models.CONSENT_TEXT_VERSION,
            learning_opt_in=self.learning_checkbox.isChecked(),
        )
        saved: list[str] = []
        try:
            if profile is not None:
                save_profile(
                    profile.model_copy(update={"consent": consent}), root=self._profile_root
                )
                saved.append("voice profile")
            if style is not None:
                save_style_profile(
                    style.model_copy(update={"consent": consent}), root=self._style_root
                )
                saved.append("learned style")
        except (StoreWriteError, ProfileError, OSError) as exc:
            # OSError too (peer round 37 PR-MED-025's in-phase sibling): the
            # atomic writer's temp-file cleanup can surface a raw error in
            # place of the typed one, and a GUI slot must not raise.
            self._set_enrolment_status(f"Could not save your consent - {exc}")
            self.refresh_profile_state()
            self.refresh_style_profile_state()
            return
        # The voice-only sentence is the pinned, pre-existing one (byte for
        # byte); the other two shapes follow its grammar (leg h1g).
        verb = "are" if len(saved) > 1 else "is"
        self._set_enrolment_status(
            f"Consent saved - your {' and '.join(saved)} {verb} unchanged."
        )
        # Re-read both from disk: the tick now comes from the records.
        self.refresh_profile_state()
        self.refresh_style_profile_state()

    # --- enrolment ----------------------------------------------------------------

    def on_record(self) -> None:
        if self.is_busy:
            return
        device = self.selected_device()
        if device is None:
            self._set_enrolment_status("No microphone selected - pick one above.")
            return
        if not self.consent_checkbox.isChecked():
            self._set_enrolment_status("Tick the consent box to record your voice.")
            return
        if not self._available:
            return  # the availability label already names the remedy
        try:
            lease = self._controller.begin_enrolment()
        except SessionActivityError as exc:
            self._set_enrolment_status(f"Cannot record now - {exc}")
            return
        self._lease = lease
        if self._on_capture_start is not None:
            # PR-MED-022: hand the microphone over on THIS (GUI) thread before
            # the worker starts; the microphone screen's poll guard keeps the
            # monitor closed afterwards. A failing handoff releases the lease
            # and starts nothing.
            try:
                self._on_capture_start()
            except Exception as exc:  # noqa: BLE001 - surfaced, the lease released
                self._release_lease()
                self._set_enrolment_status(f"Cannot record now - {type(exc).__name__}: {exc}")
                return
        self._cancel_requested.clear()
        device_id, device_name = device
        learning_opt_in = self.learning_checkbox.isChecked()
        kind = self._embedder_kind
        backend, capture, embed = self._backend, self._capture, self._embed
        embedder_factory, clock, root = self._embedder_factory, self._clock, self._profile_root
        saved_device_name = profile_device_name(device_name)
        emit_progress = self._progress_reported.emit
        should_stop = self._cancel_requested.is_set

        def raise_if_stopped() -> None:
            # Round 25 MED-001: the capture honours Stop only while it runs;
            # a Stop pressed after it returned must not end in a saved
            # profile. Checked again before the embedding and after it —
            # once that final check has passed, the profile is built and
            # ``save_profile`` runs regardless (round 28 PR-LOW-032: the
            # residue starts at the final check, not at the save); it is
            # then shown, and Delete removes it.
            if should_stop():
                raise EnrolmentCancelledError("enrolment cancelled")

        def work() -> None:  # WORKER THREAD (TaskThread) — no widget access here
            embedder = embedder_factory(kind)  # BEFORE the read-aloud: load failures fail fast
            pcm = capture(backend, device_id, emit_progress, should_stop)
            try:
                raise_if_stopped()
                vector, speech_seconds = embed(pcm, embedder)
            finally:
                del pcm  # D8: the only reference this thread holds is dropped here
            raise_if_stopped()
            now = clock()
            profile = PractitionerProfile(
                model_id=embedder.model_id,
                model_sha256=embedder.model_sha256,
                embedding=tuple(float(v) for v in vector),
                embedding_dim=len(vector),
                created_at=now,
                enrolment_speech_seconds=speech_seconds,
                device_name=saved_device_name,
                consent=ConsentRecord(
                    accepted_at=now,
                    consent_text_version=models.CONSENT_TEXT_VERSION,
                    learning_opt_in=learning_opt_in,
                ),
            )
            save_profile(profile, root=root)

        self._set_enrolment_status("Listening - read aloud in your normal voice.")
        self.level_bar.setValue(0)
        self.progress_label.setText(self._progress_text(0.0))
        task = TaskThread(work, self)
        task.succeeded.connect(self._on_enrolment_done)
        task.failed.connect(self._on_enrolment_failed)
        self._task = task
        # `is_busy` reads `QThread.isRunning()`, which is only true once
        # `start()` has been called — so the busy enablement is applied AFTER
        # the start, never before it (the result handler cannot have run yet:
        # its delivery is queued to this, the GUI, thread).
        task.start()
        self._update_controls()

    def _on_progress(self, progress: object) -> None:
        # GUI thread (queued delivery of `_progress_reported`).
        assert isinstance(progress, EnrolmentProgress)
        self.level_bar.setValue(round(progress.level * 100))
        self.progress_label.setText(self._progress_text(progress.speech_seconds))

    def on_stop(self) -> None:
        if not self.is_busy:
            return
        self._cancel_requested.set()
        self._set_enrolment_status("Stopping...")
        self._update_controls()

    def _join_task(self) -> None:
        if self._task is not None:
            self._task.finish()
            self._task = None

    def _release_lease(self) -> None:
        lease = self._lease
        self._lease = None
        if lease is not None:
            self._controller.end_enrolment(lease)

    def _on_enrolment_done(self, _result: object) -> None:
        try:
            self._join_task()
            self._set_enrolment_status("Voice profile saved.")
            self.refresh_profile_state()  # re-read from disk: the status line proves the save
            self.level_bar.setValue(0)
            self._update_controls()
        finally:
            self._release_lease()  # D15: released only after this handler, on every path

    def _on_enrolment_failed(self, message: str) -> None:
        try:
            self._join_task()
            if message.startswith("EnrolmentCancelledError"):
                text = "Enrolment stopped - nothing was saved."
            else:
                text = f"Enrolment did not complete - {message}"
            self._set_enrolment_status(text)
            self.refresh_profile_state()  # a failed re-enrolment leaves the previous one usable
            self.level_bar.setValue(0)
            self.progress_label.setText(self._progress_text(0.0))
            self._update_controls()
        finally:
            self._release_lease()

    # --- deletion -------------------------------------------------------------------

    def on_delete(self) -> None:
        if self.is_busy or not self._profile_present:
            return
        if not self._confirm_delete():
            return
        try:
            delete_profile(root=self._profile_root)
        except StoreWriteError as exc:
            self._set_enrolment_status(f"Could not delete the voice profile - {exc}")
            self.refresh_profile_state()
            return
        self.consent_checkbox.setChecked(False)
        self.learning_checkbox.setChecked(False)
        self._set_enrolment_status("Voice profile deleted.")
        self.refresh_profile_state()

    # --- learn from my notes (note-learning plan Task 3.4) ---------------------------

    def _pick_files(self) -> Sequence[Path]:
        names, _filter = QFileDialog.getOpenFileNames(
            self, "Choose your past notes", "", SAMPLE_NOTE_FILTER
        )
        return tuple(Path(name) for name in names)

    def _set_learn_status(self, text: str | None) -> None:
        self.learn_status_label.setText(text or "")
        self.learn_status_label.setVisible(bool(text))

    def _render_sample_files(self) -> None:
        self.sample_files_list.clear()
        for path in self._sample_files:
            item = QListWidgetItem(str(path))
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.sample_files_list.addItem(item)
        self._update_controls()

    def on_choose_files(self) -> None:
        """Add the picked files to the list, up to the cap — the extras are
        refused by name in the status line, never silently dropped."""
        if self.is_busy:
            return
        added: list[Path] = []
        refused: list[Path] = []
        for path in self._file_picker():
            if path in self._sample_files or path in added:
                continue
            if len(self._sample_files) + len(added) >= MAX_SAMPLE_NOTES:
                refused.append(path)
                continue
            added.append(path)
        self._sample_files.extend(added)
        self._render_sample_files()
        if refused:
            names = ", ".join(path.name for path in refused)
            self._set_learn_status(
                f"Not added (the limit is {MAX_SAMPLE_NOTES} notes at a time): {names}"
            )
        elif added:
            self._set_learn_status(None)

    def _remove_selected_file(self) -> None:
        item = self.sample_files_list.currentItem()
        if self.is_busy or item is None:
            return
        chosen = Path(str(item.data(Qt.ItemDataRole.UserRole)))
        self._sample_files = [path for path in self._sample_files if path != chosen]
        self._render_sample_files()

    def sample_files(self) -> tuple[Path, ...]:
        return tuple(self._sample_files)

    def on_learn_from_notes(self) -> None:
        """Flow 4, on the GUI thread: read → learn → review → (Save) write the
        style store under its OWN consent record → (separate confirmation)
        delete the originals. Every gate is re-checked here at click time;
        every failure names itself on the status line and writes nothing."""
        if self.is_busy:
            return
        if not self.consent_checkbox.isChecked():
            self._set_learn_status(LEARN_CONSENT_GATE_TEXT)
            return
        notes: list[SampleNote] = []
        try:
            for path in self._sample_files:
                notes.append(read_sample_note(path))
            pasted = self.paste_box.toPlainText()
            if pasted.strip():
                notes.append(read_sample_note(pasted))
        except SampleNoteError as exc:
            self._set_learn_status(f"Could not read your notes - {exc}")
            return
        if not notes:
            self._set_learn_status(LEARN_NOTHING_CHOSEN_TEXT)
            return
        if len(notes) > MAX_SAMPLE_NOTES:
            self._set_learn_status(
                f"Learn from at most {MAX_SAMPLE_NOTES} notes at a time ({len(notes)} chosen)."
            )
            return
        try:
            draft = self._learner(notes)
        except SampleNoteError as exc:
            self._set_learn_status(f"Could not learn from your notes - {exc}")
            return
        # Drops the read SampleNote list; the pasted source stays in `pasted`
        # until this handler returns and in the paste box until a successful
        # Save (the three lifetimes in `ui/style_review`'s docstring).
        del notes
        choice = self._review_runner(draft, self)
        if choice is None:
            self._set_learn_status(LEARN_CANCELLED_TEXT)
            return
        now = self._clock()
        consent = ConsentRecord(
            accepted_at=now,
            consent_text_version=models.CONSENT_TEXT_VERSION,
            learning_opt_in=self.learning_checkbox.isChecked(),
        )
        try:
            profile = build_style_profile(
                draft,
                kept_unrecognised=choice.kept_unrecognised,
                kept_exemplars=choice.kept_exemplars,
                consent=consent,
                learned_at=now,
            )
        except SampleNoteError as exc:
            self._set_learn_status(f"Could not save the learned style - {exc}")
            return
        # PR-MED-019: the draft (every candidate sentence, the removed ones
        # included) and the choice are dropped here; what this handler still
        # holds is the ratified profile, the paths the next dialog needs and
        # `pasted` (until the return — the three lifetimes in
        # `ui/style_review`'s docstring).
        source_paths = draft.source_paths
        del draft, choice
        try:
            save_style_profile(profile, root=self._style_root)
        except (StoreWriteError, ProfileError, OSError) as exc:
            self._set_learn_status(f"Could not save the learned style - {exc}")
            self.refresh_style_profile_state()
            return
        self._sample_files.clear()
        self.paste_box.clear()
        self._render_sample_files()
        self.refresh_style_profile_state()  # re-read from disk: the line proves the save
        notes_word = "note" if profile.source_count == 1 else "notes"
        summary = (
            f"Learned style saved from {profile.source_count} {notes_word}: "
            f"{len(profile.exemplars)} example sentence(s), "
            f"{len(profile.shorthand)} shorthand token(s)."
        )
        summary += self._offer_to_delete_originals(source_paths)
        self._set_learn_status(summary)

    def _offer_to_delete_originals(self, paths: Sequence[Path]) -> str:
        """D9: a SEPARATE explicit confirmation naming the paths, unticked by
        default; only a ticked-and-confirmed dialog unlinks them, and then
        exactly those paths. Returns the sentence for the status line."""
        if not paths:
            return ""
        if not self._delete_originals_runner(paths, self):
            return " The original notes were kept."
        report = delete_sample_files(paths)
        text = f" Deleted {len(report.deleted)} original file(s)."
        if report.failed:
            failures = "; ".join(f"{path.name}: {why}" for path, why in report.failed)
            text += f" Not deleted - {failures}."
        return text

    # --- learned style (note-learning plan Tasks 3.5 + 3.6) -------------------------

    def _ask_delete_style(self) -> bool:
        return (
            QMessageBox.question(
                self,
                "Delete learned style",
                "Delete the learned style? Own voice becomes unavailable until you learn "
                "again; your voice profile is not affected.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

    def refresh_style_profile_state(self) -> None:
        """ONE style-store read (a stat, then a DPAPI unwrap and a decrypt on
        the GUI thread) and a re-render of the learned-style line and both
        lists. Called at construction and after a learn, a remove, a delete or
        a consent renewal (Confirm consent re-saves the same profile with a
        current record — codex round 31 PR-LOW-048) — never from a poll
        (round 51 MED-001). An unusable store shows its
        line and keeps Delete available."""
        self._style_present = style_profile_present(root=self._style_root)
        try:
            self._style_profile = load_style_profile(root=self._style_root)
        except ProfileUnusableError as exc:
            self._style_profile = None
            line = models.STYLE_UNUSABLE_LINE.format(reason=exc.reason)
        else:
            line = models.style_profile_line(self._style_profile)
        self.style_line_label.setText(line)
        self.learned_exemplars_list.clear()
        self.learned_shorthand_list.clear()
        profile = self._style_profile
        if profile is not None:
            for index, exemplar in enumerate(profile.exemplars):
                item = QListWidgetItem(
                    f"{models.section_title(exemplar.section_key)}: {exemplar.exemplar_text}"
                )
                item.setData(Qt.ItemDataRole.UserRole, index)
                self.learned_exemplars_list.addItem(item)
            for token in profile.shorthand:
                item = QListWidgetItem(token)
                item.setData(Qt.ItemDataRole.UserRole, token)
                self.learned_shorthand_list.addItem(item)
            self.learned_style_note_label.setText(
                "Remove rewrites the learned style without that item; Delete learned style "
                "removes the whole store (your voice profile is not affected)."
            )
        elif not self._style_present:
            self.learned_style_note_label.setText(NO_LEARNED_STYLE_TEXT)
        else:
            self.learned_style_note_label.setText(
                "The learned style cannot be read - delete it and learn again."
            )
        if self.banner_label.isVisibleTo(self):
            self.show_first_run_banner()  # the second line follows the store
        self.refresh_style_options()  # -> _update_controls

    @property
    def style_profile(self) -> StyleProfile | None:
        """The learned style as last read (None when absent or unusable)."""
        return self._style_profile

    def _rewrite_style_profile(self, updated: StyleProfile, done: str) -> bool:
        """Replace the store with ``updated`` (the existing key kept) and
        re-read it; a failed write leaves the lists as they were so Remove can
        be retried, and names the failure."""
        try:
            save_style_profile(updated, root=self._style_root)
        except (StoreWriteError, ProfileError, OSError) as exc:
            self.learned_style_note_label.setText(f"Could not update the learned style - {exc}")
            return False
        self.refresh_style_profile_state()
        self.learned_style_note_label.setText(done)
        return True

    def _remove_selected_exemplar(self) -> None:
        profile = self._style_profile
        item = self.learned_exemplars_list.currentItem()
        if self.is_busy or profile is None or item is None:
            return
        index = int(item.data(Qt.ItemDataRole.UserRole))
        kept = tuple(e for i, e in enumerate(profile.exemplars) if i != index)
        self._rewrite_style_profile(
            profile.model_copy(update={"exemplars": kept}), "Removed the sentence."
        )

    def _remove_selected_shorthand(self) -> None:
        profile = self._style_profile
        item = self.learned_shorthand_list.currentItem()
        if self.is_busy or profile is None or item is None:
            return
        token = str(item.data(Qt.ItemDataRole.UserRole))
        kept = tuple(t for t in profile.shorthand if t != token)
        self._rewrite_style_profile(
            profile.model_copy(update={"shorthand": kept}), f"Removed '{token}'."
        )

    def on_delete_style(self) -> None:
        """Key-first deletion of the learned style (``delete_style_profile``),
        independent of the voice profile; the in-memory copy goes with it."""
        if self.is_busy or not self._style_present:
            return
        if not self._confirm_delete_style():
            return
        try:
            delete_style_profile(root=self._style_root)
        except StoreWriteError as exc:
            # Re-read FIRST (the store may be half-gone), then the C8 line —
            # the refresh renders the group's help text, which must not
            # overwrite the failure message; Delete stays offered by stat.
            self.refresh_style_profile_state()
            self.learned_style_note_label.setText(f"Could not delete the learned style - {exc}")
            return
        self._style_profile = None
        self.refresh_style_profile_state()
        self.learned_style_note_label.setText("Learned style deleted.")

    # --- writing style (note-learning plan Task 3.1) ---------------------------------

    def refresh_style_setting(self) -> None:
        """Re-read the saved writing style (``practitioner_settings.json``)
        and check its radio WITHOUT saving it back; an unreadable file becomes
        the default style plus the reason line (C8), never a rewrite."""
        choice = models.read_note_style(self._config_root)
        self._saved_style = choice.style
        self._check_style_radio(choice.style)
        self._set_style_status(choice.reason)
        self.refresh_style_options()

    def refresh_style_options(self) -> None:
        """Re-compute which styles may be chosen (``models.style_options`` — a
        STAT of the learned-style store, never a decrypt) and render the
        reasons of the ones that may not. Public: a later leg calls it when
        the learned style changes."""
        options = self._style_options_provider()
        reasons: list[str] = []
        by_style = {option.style: option for option in options}
        for option in options:
            self._style_enabled[option.style] = option.enabled
            if not option.enabled and option.reason is not None:
                reasons.append(option.reason)
        self.style_reason_label.setText("\n".join(reasons))
        self.style_reason_label.setVisible(bool(reasons))
        checked = next(
            (style for style, radio in self.style_radios.items() if radio.isChecked()), None
        )
        # A SAVED style the app cannot honour yet stays selected-but-disabled
        # and says how the note is rendered meanwhile (C8). Phase H round 24
        # MED-005: the line names the disabled option's OWN reasons (a saved
        # Own voice with the model installed but no learned style names the
        # learned style, never the model), and it is RE-RENDERED from the
        # kept base text on every recompute — so the poll's next transition
        # (the model installed, a style learned) retracts it.
        fallback: str | None = None
        chosen = by_style.get(checked) if checked is not None else None
        if checked is not None and chosen is not None and not chosen.enabled:
            fallback = models.style_fallback_line(checked, chosen.reasons)
        self._render_style_status(fallback)
        self._update_controls()

    def on_style_selected(self, style: NoteStyle) -> None:
        """Save the picked style at once (D7). A failed write leaves the
        setting as it is on disk: the radio goes back to the saved style and
        the status line names the failure."""
        if style == self._saved_style:
            return
        try:
            models.save_note_style(style, config_root=self._config_root)
        except NoteConfigError as exc:
            self._set_style_status(
                f"Could not save the writing style - {type(exc).__name__}: {exc}"
            )
            self._check_style_radio(self._saved_style)
            return
        self._saved_style = style
        self._set_style_status(f"Writing style saved: {models.STYLE_LABELS[style]}.")
        # Round 25 R25-02: the fallback line belongs to the CHECKED style —
        # recompute it for the one just saved (an enabled style has none).
        self.refresh_style_options()

    def _check_style_radio(self, style: NoteStyle) -> None:
        """Check one radio without firing ``on_style_selected``: the style is
        being READ (from disk, or restored after a failed write), not picked."""
        radio = self.style_radios.get(style)
        if radio is None:
            return
        blocked = [(each, each.blockSignals(True)) for each in self.style_radios.values()]
        try:
            radio.setChecked(True)
        finally:
            for each, was_blocked in blocked:
                each.blockSignals(was_blocked)

    def _set_style_status(self, text: str | None) -> None:
        """The group's BASE status (the read reason, a save's outcome or its
        failure); the fallback line of a disabled saved style is appended by
        `_render_style_status` from the current options, never accumulated."""
        self._style_status_base = text or ""
        self._render_style_status(self._style_status_fallback)

    def _render_style_status(self, fallback: str | None) -> None:
        self._style_status_fallback = fallback
        parts = [part for part in (self._style_status_base, fallback) if part]
        text = "\n".join(parts)
        self.style_status_label.setText(text)
        self.style_status_label.setVisible(bool(text))

    # --- learned phrases (Task 5.3) --------------------------------------------------

    def refresh_learned_phrases(self) -> None:
        """Re-read the user cue file and its sidecar through ``note_config``
        and re-render both lists; a loader error is shown, never swallowed."""
        self.recently_learned_list.clear()
        self.learned_phrases_list.clear()
        try:
            learned = load_learned_phrases(self._config_root)
        except NoteConfigError as exc:
            self.learned_phrases_note_label.setText(
                f"Learned phrases unavailable - {type(exc).__name__}: {exc}"
            )
            self._update_controls()
            return
        for item in learned.recent:
            entry = QListWidgetItem(
                f"{item.learned_at:%Y-%m-%d} - {models.section_title(item.section_key)}: "
                f"{item.phrase}"
            )
            entry.setData(Qt.ItemDataRole.UserRole, item.phrase)
            self.recently_learned_list.addItem(entry)
        for key, phrases in learned.by_section:
            for phrase in phrases:
                entry = QListWidgetItem(f"{models.section_title(key)}: {phrase}")
                entry.setData(Qt.ItemDataRole.UserRole, phrase)
                self.learned_phrases_list.addItem(entry)
        if learned.by_section:
            self.learned_phrases_note_label.setText(
                "Delete removes the phrase from your cue file; the shipped phrases are "
                "not listed and stay."
            )
        else:
            self.learned_phrases_note_label.setText(NO_LEARNED_PHRASES_TEXT)
        self._update_controls()

    def _delete_selected(self, widget: QListWidget) -> None:
        if self.is_busy:
            return
        item = widget.currentItem()
        if item is None:
            self.learned_phrases_note_label.setText("Select a phrase to delete first.")
            return
        self.delete_learned_phrase(str(item.data(Qt.ItemDataRole.UserRole)))

    def delete_learned_phrase(self, phrase: str) -> bool:
        """Delete one learned phrase from the cue file and the sidecar
        (``note_config.delete_user_cue``), then re-read both lists."""
        try:
            removed = delete_user_cue(phrase, config_root=self._config_root)
        except NoteConfigError as exc:
            # The lists are deliberately NOT refreshed here (peer round 36
            # PR-MED-024): the row stays so Delete can be retried, and the
            # retry removes whichever representation the failed attempt
            # left behind.
            self.learned_phrases_note_label.setText(
                f"Could not delete the phrase - {type(exc).__name__}: {exc}"
            )
            self._update_controls()
            return False
        self.refresh_learned_phrases()
        if removed:
            self.learned_phrases_note_label.setText(f"Deleted '{phrase}'.")
        return removed

    # --- learned shorthand (note-learning plan Task 2.5) -----------------------------

    def refresh_learned_rules(self) -> None:
        """Re-read the user rules file and its sidecar through ``note_config``
        and re-render both lists; a loader error is shown, never swallowed."""
        self.recently_learned_rules_list.clear()
        self.learned_rules_list.clear()
        try:
            learned = load_learned_rules(self._config_root)
        except NoteConfigError as exc:
            self.learned_rules_note_label.setText(
                f"Learned shorthand unavailable - {type(exc).__name__}: {exc}"
            )
            self._update_controls()
            return
        for rule in learned.recent:
            wording = " | ".join(rule.typed_wording)
            entry = QListWidgetItem(
                f"{rule.learned_at:%Y-%m-%d} - {models.section_title(rule.section_key)}: "
                f"'{rule.trigger_phrase}' -> '{wording}'{_rule_flag(rule)}"
            )
            entry.setData(Qt.ItemDataRole.UserRole, rule.rule_id)
            self.recently_learned_rules_list.addItem(entry)
        for key, rules in learned.by_section:
            for rule in rules:
                wording = " | ".join(rule.typed_wording)
                entry = QListWidgetItem(
                    f"{models.section_title(key)}: "
                    f"'{rule.trigger_phrase}' -> '{wording}'{_rule_flag(rule)}"
                )
                entry.setData(Qt.ItemDataRole.UserRole, rule.rule_id)
                self.learned_rules_list.addItem(entry)
        if learned.by_section:
            self.learned_rules_note_label.setText(
                "Delete removes the rule from your rules file; its lines then never "
                "propose or pre-fill again."
            )
        else:
            self.learned_rules_note_label.setText(NO_LEARNED_RULES_TEXT)
        self._update_controls()

    def _delete_selected_rule(self, widget: QListWidget) -> None:
        if self.is_busy:
            return
        item = widget.currentItem()
        if item is None:
            self.learned_rules_note_label.setText("Select a shorthand rule to delete first.")
            return
        self.delete_learned_rule(str(item.data(Qt.ItemDataRole.UserRole)))

    def delete_learned_rule(self, rule_id: str) -> bool:
        """Delete one learned rule from the rules file and the sidecar
        (``note_config.delete_learned_rule``), then re-read both lists."""
        try:
            removed = note_config.delete_learned_rule(rule_id, config_root=self._config_root)
        except NoteConfigError as exc:
            # The lists are deliberately NOT refreshed here, for the same
            # reason as the phrases (peer round 36 PR-MED-024): the row stays
            # so Delete can be retried, and the retry removes whichever
            # representation the failed attempt left behind.
            self.learned_rules_note_label.setText(
                f"Could not delete the shorthand - {type(exc).__name__}: {exc}"
            )
            self._update_controls()
            return False
        self.refresh_learned_rules()
        if removed:
            self.learned_rules_note_label.setText(f"Deleted shorthand rule '{rule_id}'.")
        return removed


__all__ = [
    "DEVICE_NAME_MAX_CHARS",
    "NO_LEARNED_PHRASES_TEXT",
    "NO_LEARNED_RULES_TEXT",
    "UNKNOWN_DEVICE_NAME",
    "PractitionerScreen",
    "profile_device_name",
]
