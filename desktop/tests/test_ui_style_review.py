"""Note-learning-and-styles plan Task 3.4: the Flow 4 dialogs — what the
review screen lists, what ``choice()`` reports after ticking and removing, and
the delete-originals confirmation's default-unticked box (D9, D10).

Offscreen Qt, against a hand-built ``StyleProfileDraft``: nothing here reads a
file, writes a store or shows a modal (``exec()`` would block), so the tests
drive ``accept()`` / ``reject()`` directly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QDialog  # noqa: E402

from scribe_desktop.note_config import (  # noqa: E402
    MAX_STYLE_EXEMPLARS,
    StyleExemplar,
    StyleMeasures,
)
from scribe_desktop.sample_notes import StyleProfileDraft  # noqa: E402
from scribe_desktop.ui.style_review import (  # noqa: E402
    DeleteOriginalsDialog,
    StyleReviewDialog,
    review_summary,
)

_SUMMARY = (
    "From 2 notes: 2 section headings, 2 recognised shorthand tokens, 2 unrecognised "
    "tokens, 3 example sentences kept."
)
_NOT_KEPT = (
    " Not kept: 3 sentences refused by the name/number/date/medication check "
    "(name 2, number 1) and 1 left out (no section heading, too long, or over the limit "
    "of 30)."
)


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _measures() -> StyleMeasures:
    return StyleMeasures(
        mean_sentence_words=7.0, abbreviation_ratio=0.1, person="third", tense="past"
    )


def _draft(**overrides: Any) -> StyleProfileDraft:
    kwargs: dict[str, Any] = {
        "section_order": ("presenting_complaint", "treatment_performed"),
        "heading_labels": {"presenting_complaint": "C/O", "treatment_performed": "Rx"},
        "recognised_shorthand": ("HVLA", "Cx"),
        "unrecognised_shorthand": ("NAGS2", "QWERTY"),
        "measures": _measures(),
        "exemplars": (
            StyleExemplar(
                section_key="treatment_performed",
                exemplar_text="Continue with the home programme.",
            ),
            StyleExemplar(
                section_key="presenting_complaint", exemplar_text="Keep the neck moving gently."
            ),
            StyleExemplar(
                section_key="treatment_performed", exemplar_text="Rest the shoulder for now."
            ),
        ),
        "source_count": 2,
        "source_paths": (Path("C:/x/a.txt"),),
        "refused_exemplars": {"name": 2, "number": 1},
        "dropped_exemplars": 1,
    }
    kwargs.update(overrides)
    return StyleProfileDraft(**kwargs)


def _texts(widget: Any) -> list[str]:
    return [widget.item(index).text() for index in range(widget.count())]


# ---------------------------------------------------------------------------
# review_summary — pure, no Qt needed
# ---------------------------------------------------------------------------


def test_review_summary_pins_the_counts_and_what_was_not_kept() -> None:
    assert MAX_STYLE_EXEMPLARS == 30
    assert review_summary(_draft()) == _SUMMARY + _NOT_KEPT


def test_review_summary_ends_after_kept_when_nothing_was_refused_or_dropped() -> None:
    draft = _draft(refused_exemplars={}, dropped_exemplars=0)
    assert review_summary(draft) == _SUMMARY
    assert "Not kept" not in review_summary(draft)


def test_review_summary_says_the_singular_for_one() -> None:
    draft = _draft(
        section_order=("assessment",),
        heading_labels={"assessment": "A"},
        recognised_shorthand=("Cx",),
        unrecognised_shorthand=("QWERTY",),
        exemplars=(StyleExemplar(section_key="assessment", exemplar_text="One kept line."),),
        source_count=1,
        refused_exemplars={"date": 1},
        dropped_exemplars=0,
    )
    assert review_summary(draft) == (
        "From 1 note: 1 section heading, 1 recognised shorthand token, 1 unrecognised "
        "token, 1 example sentence kept. Not kept: 1 sentence refused by the "
        "name/number/date/medication check (date 1) and 0 left out (no section heading, "
        "too long, or over the limit of 30)."
    )


class TestStyleReviewDialog:
    def test_lists_render_the_draft_and_labels_are_plain_text(self, qapp: Any) -> None:
        draft = _draft()
        dialog = StyleReviewDialog(draft)

        assert dialog.windowTitle() == "Review what will be learned"
        assert dialog.summary_label.text() == _SUMMARY + _NOT_KEPT
        assert _texts(dialog.headings_list) == [
            "Presenting complaint <- 'C/O'",
            "Treatment performed <- 'Rx'",
        ]
        assert _texts(dialog.recognised_list) == ["HVLA", "Cx"]
        assert _texts(dialog.unrecognised_list) == ["NAGS2", "QWERTY"]
        assert _texts(dialog.exemplars_list) == [
            "Treatment performed: Continue with the home programme.",
            "Presenting complaint: Keep the neck moving gently.",
            "Treatment performed: Rest the shoulder for now.",
        ]
        for row in range(dialog.unrecognised_list.count()):
            item = dialog.unrecognised_list.item(row)
            assert item.checkState() == Qt.CheckState.Unchecked
        for label in (
            dialog.summary_label,
            dialog.headings_header_label,
            dialog.recognised_header_label,
            dialog.unrecognised_header_label,
            dialog.exemplars_header_label,
            dialog.consent_label,
        ):
            assert label.textFormat() == Qt.TextFormat.PlainText
        assert "read, not copied" in dialog.consent_label.text()
        dialog.deleteLater()

    def test_a_heading_without_a_label_renders_the_title_alone(self, qapp: Any) -> None:
        draft = _draft(heading_labels={"presenting_complaint": "C/O"})
        dialog = StyleReviewDialog(draft)
        assert _texts(dialog.headings_list) == [
            "Presenting complaint <- 'C/O'",
            "Treatment performed",
        ]
        dialog.deleteLater()

    def test_the_default_choice_keeps_no_token_and_every_sentence(self, qapp: Any) -> None:
        draft = _draft()
        dialog = StyleReviewDialog(draft)
        choice = dialog.choice()
        assert choice.kept_unrecognised == ()
        assert choice.kept_exemplars == draft.exemplars
        for kept, offered in zip(choice.kept_exemplars, draft.exemplars, strict=True):
            assert kept is offered
        dialog.deleteLater()

    def test_ticking_a_token_keeps_exactly_that_token(self, qapp: Any) -> None:
        dialog = StyleReviewDialog(_draft())
        dialog.unrecognised_list.item(1).setCheckState(Qt.CheckState.Checked)
        assert dialog.choice().kept_unrecognised == ("QWERTY",)
        dialog.deleteLater()

    def test_removing_a_sentence_drops_it_and_no_selection_does_nothing(
        self, qapp: Any
    ) -> None:
        draft = _draft()
        dialog = StyleReviewDialog(draft)

        dialog.exemplars_list.setCurrentRow(1)
        dialog.remove_exemplar_button.click()

        assert dialog.exemplars_list.count() == 2
        assert _texts(dialog.exemplars_list) == [
            "Treatment performed: Continue with the home programme.",
            "Treatment performed: Rest the shoulder for now.",
        ]
        assert dialog.choice().kept_exemplars == (draft.exemplars[0], draft.exemplars[2])

        dialog.exemplars_list.setCurrentRow(-1)
        dialog.remove_exemplar_button.click()

        assert dialog.exemplars_list.count() == 2
        assert dialog.choice().kept_exemplars == (draft.exemplars[0], draft.exemplars[2])
        dialog.deleteLater()

    def test_an_empty_exemplar_list_disables_remove(self, qapp: Any) -> None:
        dialog = StyleReviewDialog(_draft(exemplars=()))
        assert dialog.exemplars_list.count() == 0
        assert not dialog.remove_exemplar_button.isEnabled()
        assert dialog.choice().kept_exemplars == ()
        dialog.deleteLater()

    def test_save_accepts_and_cancel_rejects(self, qapp: Any) -> None:
        dialog = StyleReviewDialog(_draft())
        dialog.accept()
        assert dialog.result() == QDialog.DialogCode.Accepted
        dialog.deleteLater()

        other = StyleReviewDialog(_draft())
        other.reject()
        assert other.result() == QDialog.DialogCode.Rejected
        other.deleteLater()


class TestDeleteOriginalsDialog:
    def test_lists_the_paths_and_starts_unticked(self, qapp: Any) -> None:
        paths = (Path("C:/x/a.txt"), Path("C:/x/b.docx"))
        dialog = DeleteOriginalsDialog(paths)

        assert dialog.windowTitle() == "Delete the original notes?"
        assert _texts(dialog.paths_list) == [str(paths[0]), str(paths[1])]
        assert not dialog.delete_checkbox.isChecked()
        assert dialog.intro_label.textFormat() == Qt.TextFormat.PlainText
        assert not dialog.delete_requested()
        dialog.deleteLater()

    def test_accepting_with_the_box_unticked_deletes_nothing(self, qapp: Any) -> None:
        dialog = DeleteOriginalsDialog((Path("C:/x/a.txt"),))
        dialog.accept()
        assert dialog.result() == QDialog.DialogCode.Accepted
        assert not dialog.delete_requested()
        dialog.deleteLater()

    def test_ticking_and_accepting_requests_the_deletion(self, qapp: Any) -> None:
        dialog = DeleteOriginalsDialog((Path("C:/x/a.txt"),))
        dialog.delete_checkbox.setChecked(True)
        dialog.accept()
        assert dialog.delete_requested()
        dialog.deleteLater()

    def test_ticking_then_cancelling_deletes_nothing(self, qapp: Any) -> None:
        dialog = DeleteOriginalsDialog((Path("C:/x/a.txt"),))
        dialog.delete_checkbox.setChecked(True)
        dialog.reject()
        assert dialog.result() == QDialog.DialogCode.Rejected
        assert not dialog.delete_requested()
        dialog.deleteLater()
