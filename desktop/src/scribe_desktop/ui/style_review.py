"""The two dialogs of Flow 4 (note-learning-and-styles plan Task 3.4): the
review-before-save screen over a ``sample_notes.StyleProfileDraft``, and the
separate delete-originals confirmation (D9).

State, exactly: NOTHING here writes a file or a store. The review dialog
reports what the practitioner left in place (``StyleReviewChoice``) and the
delete dialog reports whether they asked for the originals to go
(``delete_requested``); the Practitioner tab does the saving
(``sample_notes.build_style_profile`` +
``practitioner_profile.save_style_profile``) and the deleting
(``sample_notes.delete_sample_files``) from what these return. Nothing here
logs: every list row and the summary line are derived from the practitioner's
own past notes, which are display text only.

Lifetime (peer round 17 PR-MED-019): a dialog holds sample-derived text — the
whole draft, every exemplar row (removed ones included, until ``choice()`` has
been read), the source paths — and Qt keeps a parented dialog alive after
``exec()`` returns. The two runners therefore read the result and then, on
EVERY exit (accept, reject, an exception out of ``exec``), ``release()`` the
dialog's strings and lists, unparent it and ``deleteLater()`` it
(``_dispose``), so no finished dialog outlives its answer. That is ONE of
three lifetimes (peer round 18 PR-LOW-029), stated exactly: (a) the
dialog-owned draft and rows — released on every runner exit, before the
tab's handler continues; (b) the handler's own copies — the read note texts
dropped after the learner, the draft and the choice dropped after the
profile is built, and the pasted source string held until
``on_learn_from_notes`` returns (through the save and the delete-originals
dialog); (c) the paste box's text — cleared only by a successful Save, kept
on Cancel or a failed Save so the practitioner can retry (a deliberate,
pinned contract). What persists is the derived, reviewed profile; the tab's
own copy of it is dropped on Delete.

Two display rules the dialogs hold to: an unrecognised shorthand token starts
UNTICKED (D10 — the review may only remove, never add), and the delete
checkbox starts UNTICKED (D9 — deleting the originals is a separate,
explicit choice). Every label that renders text derived from a sample note is
``Qt.TextFormat.PlainText``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, NamedTuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.note_config import MAX_STYLE_EXEMPLARS, RefusalClass, StyleExemplar
from scribe_desktop.sample_notes import StyleProfileDraft
from scribe_desktop.ui import models

# The order the refusal classes are named in, so the summary reads the same
# way every time.
_REFUSAL_ORDER: Final[tuple[RefusalClass, ...]] = ("name", "number", "date", "medication")

HEADINGS_HEADER: Final = "Section headings found:"
RECOGNISED_HEADER: Final = "Recognised shorthand (saved):"
UNRECOGNISED_HEADER: Final = (
    "Unrecognised abbreviations - tick the ones to keep (unticked ones are not saved):"
)
EXEMPLARS_HEADER: Final = (
    "Example sentences that passed the check unchanged - remove any you do not want kept:"
)
CONSENT_LINE: Final = (
    "Saving writes the learned style, encrypted, on this computer under the consent text "
    "on the Practitioner tab. The notes you chose were read, not copied; you will be asked "
    "separately whether to delete them."
)
DELETE_INTRO_LINE: Final = (
    "The learned style is saved. These files were read, not copied. Tick the box to delete "
    "them now; leave it unticked to keep them."
)


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" + ("" if count == 1 else "s")


def _refusal_classes(refused: Mapping[RefusalClass, int]) -> str:
    """The non-zero refusal classes as ``"name 2, number 1"``."""
    parts: list[str] = []
    for name in _REFUSAL_ORDER:
        count = refused.get(name, 0)
        if count:
            parts.append(f"{name} {count}")
    return ", ".join(parts)


def review_summary(draft: StyleProfileDraft) -> str:
    """The one-paragraph summary above the review lists: what was kept, and —
    when anything was not — how much was refused by the filter and how much
    was left out. Pure: no widget, no I/O."""
    summary = (
        f"From {_plural(draft.source_count, 'note')}: "
        f"{_plural(len(draft.section_order), 'section heading')}, "
        f"{_plural(len(draft.recognised_shorthand), 'recognised shorthand token')}, "
        f"{_plural(len(draft.unrecognised_shorthand), 'unrecognised token')}, "
        f"{_plural(len(draft.exemplars), 'example sentence')} kept."
    )
    refused = sum(draft.refused_exemplars.values())
    dropped = draft.dropped_exemplars
    if refused <= 0 and dropped <= 0:
        return summary
    classes = f" ({_refusal_classes(draft.refused_exemplars)})" if refused else ""
    return (
        f"{summary} Not kept: {_plural(refused, 'sentence')} refused by the "
        f"name/number/date/medication check{classes} and {dropped} left out (no section "
        f"heading, too long, or over the limit of {MAX_STYLE_EXEMPLARS})."
    )


class StyleReviewChoice(NamedTuple):
    """What the practitioner left in place: the ticked unrecognised tokens in
    list order, and the draft's OWN exemplar objects still in the list, in
    the draft's order (``build_style_profile`` refuses anything else)."""

    kept_unrecognised: tuple[str, ...]
    kept_exemplars: tuple[StyleExemplar, ...]


def _plain_label(text: str = "", *, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    if wrap:
        label.setWordWrap(True)
    return label


def _fixed_row(text: str) -> QListWidgetItem:
    item = QListWidgetItem(text)
    item.setFlags(Qt.ItemFlag.NoItemFlags)
    return item


class StyleReviewDialog(QDialog):
    """Review before save: the section headings, the recognised shorthand,
    the unrecognised shorthand to tick, and the example sentences to remove.
    ``choice()`` is the whole output; the dialog writes nothing."""

    def __init__(self, draft: StyleProfileDraft, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Review what will be learned")
        # None once ``release()`` ran: the draft is not kept past the answer.
        self._draft: StyleProfileDraft | None = draft
        self._removed: set[int] = set()

        self.summary_label = _plain_label(review_summary(draft), wrap=True)

        self.headings_header_label = _plain_label(HEADINGS_HEADER)
        self.headings_list = QListWidget()
        for key in draft.section_order:
            title = models.section_title(key)
            label = draft.heading_labels.get(key)
            text = f"{title} <- '{label}'" if label else title
            self.headings_list.addItem(_fixed_row(text))

        self.recognised_header_label = _plain_label(RECOGNISED_HEADER)
        self.recognised_list = QListWidget()
        for token in draft.recognised_shorthand:
            self.recognised_list.addItem(_fixed_row(token))

        self.unrecognised_header_label = _plain_label(UNRECOGNISED_HEADER, wrap=True)
        self.unrecognised_list = QListWidget()
        for token in draft.unrecognised_shorthand:
            item = QListWidgetItem(token)
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            # D10: unticked by default — a token the practitioner does not
            # tick is not saved.
            item.setCheckState(Qt.CheckState.Unchecked)
            self.unrecognised_list.addItem(item)

        self.exemplars_header_label = _plain_label(EXEMPLARS_HEADER, wrap=True)
        self.exemplars_list = QListWidget()
        for index, exemplar in enumerate(draft.exemplars):
            item = QListWidgetItem(
                f"{models.section_title(exemplar.section_key)}: {exemplar.exemplar_text}"
            )
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.exemplars_list.addItem(item)
        self.remove_exemplar_button = QPushButton("Remove selected sentence")
        self.remove_exemplar_button.setEnabled(self.exemplars_list.count() > 0)
        self.remove_exemplar_button.clicked.connect(self.remove_selected_exemplar)

        self.consent_label = _plain_label(CONSENT_LINE, wrap=True)

        self.save_button = QPushButton("Save learned style")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.headings_header_label)
        layout.addWidget(self.headings_list)
        layout.addWidget(self.recognised_header_label)
        layout.addWidget(self.recognised_list)
        layout.addWidget(self.unrecognised_header_label)
        layout.addWidget(self.unrecognised_list)
        layout.addWidget(self.exemplars_header_label)
        layout.addWidget(self.exemplars_list)
        layout.addWidget(self.remove_exemplar_button)
        layout.addWidget(self.consent_label)
        layout.addLayout(buttons)

    def remove_selected_exemplar(self) -> None:
        """Drop the selected sentence from the list and from ``choice()``;
        with nothing selected this does nothing."""
        row = self.exemplars_list.currentRow()
        if row < 0:
            return
        item = self.exemplars_list.takeItem(row)
        if item is None:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(index, int):
            self._removed.add(index)
        self.remove_exemplar_button.setEnabled(self.exemplars_list.count() > 0)

    def choice(self) -> StyleReviewChoice:
        draft = self._draft
        if draft is None:
            raise RuntimeError("the review dialog was released; its answer was already read")
        kept_tokens: list[str] = []
        for row in range(self.unrecognised_list.count()):
            item = self.unrecognised_list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                kept_tokens.append(item.text())
        kept_exemplars = tuple(
            exemplar
            for index, exemplar in enumerate(draft.exemplars)
            if index not in self._removed
        )
        return StyleReviewChoice(tuple(kept_tokens), kept_exemplars)

    def release(self) -> None:
        """Drop every sample-derived string this dialog holds — the draft and
        the four lists' rows — once its answer has been read (PR-MED-019).
        ``choice()`` refuses afterwards; the widget itself is disposed by the
        runner."""
        self._draft = None
        self._removed = set()
        self.summary_label.setText("")
        for widget in (
            self.headings_list,
            self.recognised_list,
            self.unrecognised_list,
            self.exemplars_list,
        ):
            widget.clear()


def _dispose(dialog: StyleReviewDialog | DeleteOriginalsDialog) -> None:
    """The one teardown both runners share: release the strings, take the
    dialog out of the parent's ownership (so nothing finds it again) and
    schedule the Qt object's deletion."""
    dialog.release()
    dialog.setParent(None)
    dialog.deleteLater()


def run_style_review(
    draft: StyleProfileDraft, parent: QWidget | None = None
) -> StyleReviewChoice | None:
    """Show the review modally; the practitioner's choice, or None when they
    cancelled (nothing is saved on a cancel). The dialog is disposed on every
    exit — accept, reject or an exception — after the answer was read."""
    dialog = StyleReviewDialog(draft, parent=parent)
    try:
        dialog.exec()
        if dialog.result() == QDialog.DialogCode.Accepted:
            return dialog.choice()
        return None
    finally:
        _dispose(dialog)


class DeleteOriginalsDialog(QDialog):
    """D9's separate, explicit confirmation: the files that were READ, and an
    unticked box that must be ticked for them to be deleted."""

    def __init__(self, paths: Sequence[Path], *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Delete the original notes?")

        self.intro_label = _plain_label(DELETE_INTRO_LINE, wrap=True)

        self.paths_list = QListWidget()
        for path in paths:
            self.paths_list.addItem(_fixed_row(str(path)))

        # D9: unticked by default — keeping the originals is the default.
        self.delete_checkbox = QCheckBox("Delete these files now")
        self.delete_checkbox.setChecked(False)

        self.confirm_button = QPushButton("Continue")
        self.confirm_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addWidget(self.confirm_button)
        buttons.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.intro_label)
        layout.addWidget(self.paths_list)
        layout.addWidget(self.delete_checkbox)
        layout.addLayout(buttons)

    def delete_requested(self) -> bool:
        """True only when the dialog was accepted WITH the box ticked."""
        return self.result() == QDialog.DialogCode.Accepted and self.delete_checkbox.isChecked()

    def release(self) -> None:
        """Drop the listed paths once the answer has been read (PR-MED-019)."""
        self.paths_list.clear()


def run_delete_originals(paths: Sequence[Path], parent: QWidget | None = None) -> bool:
    """Show the confirmation modally; True only when the practitioner asked
    for the listed files to be deleted. The dialog is disposed on every exit
    after the answer was read."""
    dialog = DeleteOriginalsDialog(paths, parent=parent)
    try:
        dialog.exec()
        return dialog.delete_requested()
    finally:
        _dispose(dialog)


__all__ = [
    "DeleteOriginalsDialog",
    "StyleReviewChoice",
    "StyleReviewDialog",
    "review_summary",
    "run_delete_originals",
    "run_style_review",
]
