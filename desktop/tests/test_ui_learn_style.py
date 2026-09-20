"""Note-learning-and-styles plan Tasks 3.4-3.6: the Practitioner tab's "Learn
from my notes" and "Learned style" groups — the consent gate, the picker cap,
what a review's Save writes, the SEPARATE delete-the-originals step, the
per-item Remove, the key-first Delete, and the rule that no 5 s poll ever
decrypts the STYLE store (with the speaker model's presence held steady, as
the poll case holds it, neither poll opens either store; the microphone
poll's one voice-profile re-read on a presence transition is round 55
PR-REG-006's documented exception).

Offscreen Qt, against the REAL learner and the REAL style store under a tmp
style root; the tab's other seams (voice profile, models, microphone) are
stubbed, and no default store root is ever consulted. The style store is
DPAPI-custodied, so every case that actually writes it is Windows-only; the
pure-widget cases (gating, the picker, a cancelled review, the poll case with
the decrypt primitive patched) run everywhere.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402

from scribe_desktop import practitioner_profile  # noqa: E402
from scribe_desktop.audio_capture import AudioDevice  # noqa: E402
from scribe_desktop.note_config import MAX_SAMPLE_NOTES  # noqa: E402
from scribe_desktop.practitioner_profile import (  # noqa: E402
    PROFILE_BLOB_FILENAME,
    STYLE_BLOB_FILENAME,
    load_style_profile,
    style_profile_present,
)
from scribe_desktop.sample_notes import StyleProfileDraft  # noqa: E402
from scribe_desktop.session import SessionState  # noqa: E402
from scribe_desktop.session_store import KEY_FILENAME, StoreWriteError  # noqa: E402
from scribe_desktop.ui import models  # noqa: E402
from scribe_desktop.ui.practitioner import (  # noqa: E402
    LEARN_CANCELLED_TEXT,
    LEARN_CONSENT_GATE_TEXT,
    LEARN_INTRO_TEXT,
    LEARN_NOTHING_CHOSEN_TEXT,
)
from scribe_desktop.ui.style_review import (  # noqa: E402
    DeleteOriginalsDialog,
    StyleReviewChoice,
    StyleReviewDialog,
    run_delete_originals,
    run_style_review,
)

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI custody is Windows-only")

# One note in the practitioner's own hand: headings the parser knows, two
# recognised shorthand tokens per section, one unrecognised token, and lines
# the refusal filter turns away (a number, a date-shaped plan).
NOTE = "\n".join([
    "C/O: Neck pain for three days.",
    "Keep the neck moving gently.",
    "O/E: ROM limited on the left. NAD on palpation today.",
    "Pt reports improvement (QWERTY protocol).",
    "Rx: HVLA Cx applied with good release.",
    "Continue with the home programme.",
    "Plan: Review in one week.",
])


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


class _FakeBackend:
    """Only what the tab calls while it is merely shown."""

    def list_input_devices(self) -> list[AudioDevice]:
        return [AudioDevice(device_id=7, name="Mic B", is_default=True)]

    def open_stream(self, device_id: int, on_block: Any, on_error: Any) -> Any:
        raise AssertionError("fake backend cannot open streams")


class _FakeController:
    """The enrolment activity, never entered by these tests."""

    def __init__(self) -> None:
        self.enrolling = False

    def begin_enrolment(self) -> Any:
        raise AssertionError("no enrolment is started here")

    def end_enrolment(self, lease: Any) -> None:
        raise AssertionError("no enrolment is started here")


class _MicFakeController:
    """The minimal controller surface ``MicrophoneScreen`` reads: the idle
    state, the level meter and the enrolment flag."""

    def __init__(self) -> None:
        self.enrolling = False
        self.state_value = SessionState.IDLE

    @property
    def state(self) -> SessionState:
        return self.state_value

    @property
    def level(self) -> float:
        return 0.0


class _CapturingRunner:
    """A review runner that records the draft it was shown and answers with a
    choice over THAT draft: the named unrecognised tokens ticked, every
    exemplar kept except the listed indices (the review may only remove)."""

    def __init__(
        self,
        kept_unrecognised: tuple[str, ...] = (),
        drop_indices: tuple[int, ...] = (),
    ) -> None:
        self.seen: list[StyleProfileDraft] = []
        self._kept_unrecognised = tuple(kept_unrecognised)
        self._dropped = frozenset(drop_indices)

    def __call__(self, draft: StyleProfileDraft, parent: Any) -> StyleReviewChoice:
        self.seen.append(draft)
        return StyleReviewChoice(
            self._kept_unrecognised,
            tuple(e for i, e in enumerate(draft.exemplars) if i not in self._dropped),
        )


def _capturing_runner(
    kept_unrecognised: tuple[str, ...] = (),
    drop_indices: tuple[int, ...] = (),
) -> _CapturingRunner:
    return _CapturingRunner(kept_unrecognised, drop_indices)


def _cancelling_runner(draft: StyleProfileDraft, parent: Any) -> None:
    """The practitioner closed the review: nothing is saved."""
    return None


def _screen(tmp_path: Path, **overrides: Any) -> Any:
    from scribe_desktop.ui.practitioner import PractitionerScreen

    kwargs: dict[str, Any] = {
        "profile_root": tmp_path / "profile",
        "config_root": tmp_path / "config",
        # The learned-style store root — never the default one.
        "style_root": tmp_path / "style",
        "embedder_available": lambda kind: True,
        "vad_available": lambda: True,
        "readiness_provider": lambda: models.AttributionReadiness(
            profile_present=False, profile=None, reason=None
        ),
        # The Task 3.4 / 3.6 seams: nothing picked, a review that keeps the
        # whole draft, the originals kept, and a confirmed style deletion.
        "file_picker": lambda: (),
        "review_runner": _capturing_runner(),
        "delete_originals_runner": lambda paths, parent: False,
        "confirm_delete_style": lambda: True,
    }
    kwargs.update(overrides)
    return PractitionerScreen(_FakeController(), _FakeBackend(), **kwargs)


def _style_root(tmp_path: Path) -> Path:
    return tmp_path / "style"


def _learned(tmp_path: Path, **screen_overrides: Any) -> Any:
    """A tab that has just learned a style from ``NOTE``, keeping everything."""
    screen = _screen(tmp_path, **screen_overrides)
    screen.consent_checkbox.setChecked(True)
    screen.paste_box.setPlainText(NOTE)
    screen.learn_button.click()
    assert screen.style_profile is not None
    return screen


class TestLearnGroup:
    def test_the_group_starts_gated_and_empty(self, qapp: Any, tmp_path: Path) -> None:
        """Case 1: with consent unticked the gate line stands, the button is
        dead, nothing is chosen, and every label of the group is PLAIN text
        (they quote file names and reader errors)."""
        screen = _screen(tmp_path)

        assert not screen.learn_gate_label.isHidden()
        assert screen.learn_gate_label.text() == LEARN_CONSENT_GATE_TEXT
        assert not screen.learn_button.isEnabled()
        assert screen.learn_intro_label.text() == LEARN_INTRO_TEXT
        assert screen.sample_files_list.count() == 0
        assert screen.sample_files() == ()
        assert not screen.remove_file_button.isEnabled()
        assert screen.choose_files_button.isEnabled()
        assert screen.learn_status_label.isHidden()
        for label in (
            screen.learn_intro_label,
            screen.learn_gate_label,
            screen.learn_status_label,
        ):
            assert label.textFormat() == Qt.TextFormat.PlainText
        screen.deleteLater()

    def test_consent_opens_the_gate_and_something_to_learn_from_arms_it(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 2: the gate line goes with the tick, but the button still
        needs a note — the pasted one arms it, and clearing it disarms it."""
        screen = _screen(tmp_path)

        screen.consent_checkbox.setChecked(True)
        assert screen.learn_gate_label.isHidden()
        assert not screen.learn_button.isEnabled()

        screen.paste_box.setPlainText(NOTE)
        assert screen.learn_button.isEnabled()

        screen.paste_box.clear()
        assert not screen.learn_button.isEnabled()
        screen.deleteLater()

    def test_the_picker_caps_the_list_and_names_what_it_refused(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 3: over the cap the extras are refused BY NAME, never
        silently dropped; the button then closes, a second pick adds nothing,
        and a path already listed is not added twice."""
        picked = tuple(tmp_path / f"n{i}.txt" for i in range(7))
        screen = _screen(tmp_path, file_picker=lambda: picked)

        screen.choose_files_button.click()

        assert screen.sample_files() == picked[:MAX_SAMPLE_NOTES]
        assert screen.sample_files_list.count() == MAX_SAMPLE_NOTES
        assert not screen.learn_status_label.isHidden()
        status = screen.learn_status_label.text()
        assert status.startswith(f"Not added (the limit is {MAX_SAMPLE_NOTES} notes at a time):")
        assert "n5.txt" in status
        assert "n6.txt" in status
        assert not screen.choose_files_button.isEnabled()

        screen.on_choose_files()  # a second pick: the cap still holds
        assert screen.sample_files() == picked[:MAX_SAMPLE_NOTES]
        screen.deleteLater()

        same = tmp_path / "same.txt"
        twice = _screen(tmp_path, file_picker=lambda: (same, same))
        twice.choose_files_button.click()
        assert twice.sample_files() == (same,)
        assert twice.sample_files_list.count() == 1
        twice.deleteLater()

    def test_remove_drops_exactly_the_selected_file(self, qapp: Any, tmp_path: Path) -> None:
        """Case 4."""
        first, second = tmp_path / "a.txt", tmp_path / "b.txt"
        screen = _screen(tmp_path, file_picker=lambda: (first, second))
        screen.choose_files_button.click()

        screen.sample_files_list.setCurrentRow(0)
        screen.remove_file_button.click()

        assert screen.sample_files() == (second,)
        assert screen.sample_files_list.count() == 1
        screen.deleteLater()

    def test_the_consent_gate_is_re_checked_at_click_time(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 5: the gate is not merely an enablement — a click that arrives
        with consent unticked shows the gate line, reviews nothing and writes
        nothing."""
        runner = _capturing_runner()
        screen = _screen(tmp_path, review_runner=runner)
        screen.paste_box.setPlainText(NOTE)

        screen.on_learn_from_notes()

        assert screen.learn_status_label.text() == LEARN_CONSENT_GATE_TEXT
        assert runner.seen == []
        assert not _style_root(tmp_path).exists()
        screen.deleteLater()

    def test_nothing_chosen_is_said_at_click_time(self, qapp: Any, tmp_path: Path) -> None:
        """Case 6."""
        runner = _capturing_runner()
        screen = _screen(tmp_path, review_runner=runner)
        screen.consent_checkbox.setChecked(True)

        screen.on_learn_from_notes()

        assert screen.learn_status_label.text() == LEARN_NOTHING_CHOSEN_TEXT
        assert runner.seen == []
        screen.deleteLater()

    def test_an_unreadable_file_names_itself_and_reviews_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 7: a PDF is not read (the reader refuses the suffix); the
        status line names the file and nothing reaches the review."""
        scan = tmp_path / "scan.pdf"
        scan.write_bytes(b"%PDF")
        runner = _capturing_runner()
        screen = _screen(tmp_path, file_picker=lambda: (scan,), review_runner=runner)
        screen.choose_files_button.click()
        screen.consent_checkbox.setChecked(True)

        screen.on_learn_from_notes()

        assert screen.learn_status_label.text().startswith("Could not read your notes - ")
        assert "scan.pdf" in screen.learn_status_label.text()
        assert runner.seen == []
        assert not _style_root(tmp_path).exists()
        screen.deleteLater()

    def test_a_cancelled_review_saves_nothing_and_consumes_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 8: Save is the ONLY thing that writes — a cancelled review
        leaves no key, no blob and the pasted note still in the box."""
        screen = _screen(tmp_path, review_runner=_cancelling_runner)
        screen.consent_checkbox.setChecked(True)
        screen.paste_box.setPlainText(NOTE)

        screen.learn_button.click()

        assert screen.learn_status_label.text() == LEARN_CANCELLED_TEXT
        assert not style_profile_present(root=_style_root(tmp_path))
        root = _style_root(tmp_path)
        assert not root.exists() or list(root.iterdir()) == []
        assert screen.paste_box.toPlainText() == NOTE
        screen.deleteLater()


@windows_only
class TestLearnSave:
    def test_save_writes_the_style_store_with_its_own_consent_record(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 9: sample learning needs NO voice profile (D9) — the style
        store carries its own current consent record; the review's removals
        are honoured; the line, the lists and the writing-style reason all
        follow the one read the save takes."""
        runner = _capturing_runner(kept_unrecognised=("QWERTY",), drop_indices=(1,))
        screen = _screen(
            tmp_path,
            review_runner=runner,
            delete_originals_runner=lambda paths, parent: pytest.fail(
                "no paths for pasted text"
            ),
        )
        screen.consent_checkbox.setChecked(True)
        screen.learning_checkbox.setChecked(True)
        screen.paste_box.setPlainText(NOTE)

        screen.learn_button.click()

        profile = load_style_profile(root=_style_root(tmp_path))
        assert profile is not None
        assert models.consent_is_current(profile)
        assert profile.consent.learning_opt_in is True
        assert profile.consent.consent_text_version == models.CONSENT_TEXT_VERSION
        assert profile.source_count == 1
        assert "QWERTY" in profile.shorthand

        draft = runner.seen[0]
        dropped = draft.exemplars[1]
        assert dropped not in profile.exemplars
        assert list(profile.exemplars) == [
            exemplar for index, exemplar in enumerate(draft.exemplars) if index != 1
        ]

        assert screen.style_profile == profile
        assert screen.style_line_label.text() == models.style_profile_line(profile)
        status = screen.learn_status_label.text()
        assert status.startswith("Learned style saved from 1 note:")
        assert "original" not in status
        assert screen.paste_box.toPlainText() == ""
        # The prose style still needs the language model, but no longer a style.
        assert not screen.style_radios["own_voice"].isEnabled()
        assert models.STYLE_PROFILE_EMPTY_REASON not in screen.style_reason_label.text()
        assert screen.learned_exemplars_list.count() == len(profile.exemplars)
        assert screen.learned_shorthand_list.count() == len(profile.shorthand)
        assert screen.delete_style_button.isEnabled()
        assert screen.remove_exemplar_button.isEnabled()
        assert not (tmp_path / "profile" / PROFILE_BLOB_FILENAME).exists()
        screen.deleteLater()

    def test_the_originals_are_kept_when_the_separate_step_is_declined(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 10: the delete-the-originals confirmation is SEPARATE and
        names exactly the notes that were read, in order; declined, the files
        stand and the status line says so."""
        notes = tmp_path / "notes"
        notes.mkdir()
        first, second = notes / "a.txt", notes / "b.txt"
        first.write_text(NOTE, encoding="utf-8")
        second.write_text(NOTE, encoding="utf-8")
        offered: list[tuple[Path, ...]] = []

        def decline(paths: Any, parent: Any) -> bool:
            offered.append(tuple(paths))
            return False

        screen = _screen(
            tmp_path, file_picker=lambda: (first, second), delete_originals_runner=decline
        )
        screen.choose_files_button.click()
        screen.consent_checkbox.setChecked(True)

        screen.learn_button.click()

        assert first.exists() and second.exists()
        assert "The original notes were kept." in screen.learn_status_label.text()
        assert offered == [(first, second)]
        assert screen.sample_files() == ()
        assert screen.sample_files_list.count() == 0
        screen.deleteLater()

    def test_accepting_the_delete_step_unlinks_only_the_listed_notes(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 11: exactly the notes that were read, nothing beside them."""
        notes = tmp_path / "notes"
        notes.mkdir()
        first, second = notes / "a.txt", notes / "b.txt"
        keep = notes / "keep.txt"
        for path in (first, second, keep):
            path.write_text(NOTE, encoding="utf-8")

        screen = _screen(
            tmp_path,
            file_picker=lambda: (first, second),
            delete_originals_runner=lambda paths, parent: True,
        )
        screen.choose_files_button.click()
        screen.consent_checkbox.setChecked(True)

        screen.learn_button.click()

        assert not first.exists()
        assert not second.exists()
        assert keep.exists()
        assert "Deleted 2 original file(s)." in screen.learn_status_label.text()
        assert style_profile_present(root=_style_root(tmp_path))
        screen.deleteLater()

    def test_the_delete_step_never_runs_when_the_review_was_cancelled(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 12: the offer comes only AFTER a save — a cancelled review
        never reaches it, and the notes stand."""
        notes = tmp_path / "notes"
        notes.mkdir()
        first = notes / "a.txt"
        first.write_text(NOTE, encoding="utf-8")

        screen = _screen(
            tmp_path,
            file_picker=lambda: (first,),
            review_runner=_cancelling_runner,
            delete_originals_runner=lambda paths, parent: pytest.fail("must not be reached"),
        )
        screen.choose_files_button.click()
        screen.consent_checkbox.setChecked(True)

        screen.learn_button.click()

        assert screen.learn_status_label.text() == LEARN_CANCELLED_TEXT
        assert first.exists()
        screen.deleteLater()

    def test_the_learning_opt_in_is_recorded_as_it_stands(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 13: the style store's own record carries the phrase-learning
        choice as ticked at the save — off here."""
        screen = _screen(tmp_path)
        screen.consent_checkbox.setChecked(True)
        screen.learning_checkbox.setChecked(False)
        screen.paste_box.setPlainText(NOTE)

        screen.learn_button.click()

        profile = load_style_profile(root=_style_root(tmp_path))
        assert profile is not None
        assert profile.consent.learning_opt_in is False
        assert models.consent_is_current(profile)
        screen.deleteLater()

    def test_a_failed_write_names_itself_and_saves_nothing(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Case 14: the note is still in the box, so the practitioner can
        retry after fixing the disk."""

        def raiser(profile: Any, *, root: Any = None) -> Any:
            raise StoreWriteError("disk full")

        monkeypatch.setattr("scribe_desktop.ui.practitioner.save_style_profile", raiser)
        screen = _screen(tmp_path)
        screen.consent_checkbox.setChecked(True)
        screen.paste_box.setPlainText(NOTE)

        screen.learn_button.click()

        status = screen.learn_status_label.text()
        assert status.startswith("Could not save the learned style - ")
        assert "disk full" in status
        assert not style_profile_present(root=_style_root(tmp_path))
        assert screen.paste_box.toPlainText() == NOTE
        screen.deleteLater()

    def test_the_first_run_banners_second_line_follows_the_store(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 15: the sample-note line is shown while no learned style
        exists (a stat), goes when one is learned, and comes back when it is
        deleted — the banner never blocks either way (D10)."""
        screen = _screen(tmp_path)
        screen.show_first_run_banner()

        assert screen.banner_label.text() == models.first_run_banner_text(style_present=False)
        assert models.FIRST_RUN_STYLE_LINE in screen.banner_label.text()

        screen.consent_checkbox.setChecked(True)
        screen.paste_box.setPlainText(NOTE)
        screen.learn_button.click()
        assert screen.banner_label.text() == models.FIRST_RUN_BANNER

        screen.on_delete_style()
        assert screen.banner_label.text() == models.first_run_banner_text(style_present=False)
        screen.deleteLater()


@windows_only
class TestLearnedStyleGroup:
    def test_both_lists_render_the_saved_profile(self, qapp: Any, tmp_path: Path) -> None:
        """Case 16: each row carries what Remove needs — the exemplar's index,
        the shorthand's token."""
        screen = _learned(tmp_path)
        profile = screen.style_profile

        assert screen.learned_exemplars_list.count() == len(profile.exemplars)
        for index, exemplar in enumerate(profile.exemplars):
            item = screen.learned_exemplars_list.item(index)
            title = models.section_title(exemplar.section_key)
            assert item.text() == f"{title}: {exemplar.exemplar_text}"
            assert item.data(Qt.ItemDataRole.UserRole) == index
        assert screen.learned_shorthand_list.count() == len(profile.shorthand)
        for index, token in enumerate(profile.shorthand):
            item = screen.learned_shorthand_list.item(index)
            assert item.text() == token
            assert item.data(Qt.ItemDataRole.UserRole) == token
        assert screen.learned_style_note_label.text().startswith(
            "Remove rewrites the learned style"
        )
        screen.deleteLater()

    def test_removing_a_sentence_rewrites_the_store_under_the_same_key(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 17: Remove is a whole-store rewrite that keeps the existing
        style key (a new key would orphan nothing but cost the blob)."""
        screen = _learned(tmp_path)
        before = screen.style_profile
        key_before = (_style_root(tmp_path) / KEY_FILENAME).read_bytes()

        screen.learned_exemplars_list.setCurrentRow(2)
        removed = before.exemplars[2]
        screen.remove_exemplar_button.click()

        after = load_style_profile(root=_style_root(tmp_path))
        assert after is not None
        assert len(after.exemplars) == len(before.exemplars) - 1
        assert removed not in after.exemplars
        assert screen.learned_exemplars_list.count() == len(after.exemplars)
        assert screen.learned_style_note_label.text() == "Removed the sentence."
        assert (_style_root(tmp_path) / KEY_FILENAME).read_bytes() == key_before
        screen.deleteLater()

    def test_removing_a_shorthand_token_rewrites_the_store(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 18."""
        screen = _learned(tmp_path)
        rows = [
            index
            for index in range(screen.learned_shorthand_list.count())
            if screen.learned_shorthand_list.item(index).text() == "Cx"
        ]
        assert rows, "the learner did not keep the Cx token"
        screen.learned_shorthand_list.setCurrentRow(rows[0])

        screen.remove_shorthand_button.click()

        after = load_style_profile(root=_style_root(tmp_path))
        assert after is not None
        assert "Cx" not in after.shorthand
        assert screen.learned_shorthand_list.count() == len(after.shorthand)
        assert "Cx" not in [
            screen.learned_shorthand_list.item(i).text()
            for i in range(screen.learned_shorthand_list.count())
        ]
        assert screen.learned_style_note_label.text() == "Removed 'Cx'."
        screen.deleteLater()

    def test_a_failed_rewrite_keeps_the_row_and_names_the_failure(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Case 19: the list is left as it was so Remove can be retried."""
        screen = _learned(tmp_path)
        blob = _style_root(tmp_path) / STYLE_BLOB_FILENAME
        blob_before = blob.read_bytes()
        count_before = screen.learned_exemplars_list.count()

        def raiser(profile: Any, *, root: Any = None) -> Any:
            raise StoreWriteError("locked")

        monkeypatch.setattr("scribe_desktop.ui.practitioner.save_style_profile", raiser)
        screen.learned_exemplars_list.setCurrentRow(0)
        screen.remove_exemplar_button.click()

        assert screen.learned_style_note_label.text().startswith(
            "Could not update the learned style - "
        )
        assert screen.learned_exemplars_list.count() == count_before
        assert blob.read_bytes() == blob_before
        screen.deleteLater()

    def test_delete_is_key_first_confirmed_and_leaves_the_voice_profile_alone(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Case 20: the key dies first (the cryptographic death of the blob),
        the tab forgets the style, and nothing under the voice-profile root is
        created or touched (D9)."""
        screen = _learned(tmp_path)
        order: list[str] = []
        real_unlink = Path.unlink

        def _record(self: Path, missing_ok: bool = False) -> None:
            order.append(self.name)
            real_unlink(self, missing_ok=missing_ok)

        monkeypatch.setattr(Path, "unlink", _record)
        screen.delete_style_button.click()
        monkeypatch.undo()

        assert order == [KEY_FILENAME, STYLE_BLOB_FILENAME]
        assert screen.style_profile is None
        assert screen.style_line_label.text() == models.STYLE_NOT_LEARNED_LINE
        assert screen.learned_exemplars_list.count() == 0
        assert screen.learned_shorthand_list.count() == 0
        assert not screen.delete_style_button.isEnabled()
        assert screen.learned_style_note_label.text() == "Learned style deleted."
        assert models.STYLE_PROFILE_EMPTY_REASON in screen.style_reason_label.text()
        assert not (tmp_path / "profile").exists()
        screen.deleteLater()

    def test_a_declined_confirmation_deletes_nothing(self, qapp: Any, tmp_path: Path) -> None:
        """Case 21."""
        screen = _learned(tmp_path, confirm_delete_style=lambda: False)
        before = screen.style_profile

        screen.delete_style_button.click()

        assert style_profile_present(root=_style_root(tmp_path))
        assert load_style_profile(root=_style_root(tmp_path)) == before
        assert screen.style_profile == before
        screen.deleteLater()

    def test_a_failed_delete_names_itself_and_stays_offered(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Case 22: presence is a stat, so Delete stays available to retry."""
        screen = _learned(tmp_path)

        def raiser(*, root: Any = None) -> None:
            raise StoreWriteError("in use")

        monkeypatch.setattr("scribe_desktop.ui.practitioner.delete_style_profile", raiser)
        screen.delete_style_button.click()

        assert screen.learned_style_note_label.text().startswith(
            "Could not delete the learned style - "
        )
        assert screen.delete_style_button.isEnabled()
        assert style_profile_present(root=_style_root(tmp_path))
        screen.deleteLater()

    def test_an_unusable_store_says_so_and_offers_only_delete(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Case 23: Remove needs a READABLE profile; Delete needs only
        presence, so the practitioner can always get out of it."""
        screen = _learned(tmp_path)
        (_style_root(tmp_path) / STYLE_BLOB_FILENAME).write_bytes(b"\x00" * 40)

        screen.refresh_style_profile_state()

        assert screen.style_profile is None
        assert screen.style_line_label.text().startswith("Learned style: cannot be read")
        assert screen.delete_style_button.isEnabled()
        assert not screen.remove_exemplar_button.isEnabled()
        assert screen.learned_style_note_label.text() == (
            "The learned style cannot be read - delete it and learn again."
        )
        screen.deleteLater()


def _auto_exec(decision: str, seen: list[Any]) -> Any:
    """A stand-in for ``QDialog.exec`` that answers the REAL dialog without a
    modal loop and records the dialog so the test can inspect it after the
    runner has disposed of it."""

    def fake_exec(self: Any) -> int:
        seen.append(self)
        if decision == "remove-then-accept":
            self.exemplars_list.setCurrentRow(0)
            self.remove_selected_exemplar()
            self.accept()
        elif decision == "accept":
            self.accept()
        elif decision == "reject":
            self.reject()
        elif decision == "raise":
            raise RuntimeError("the review blew up")
        return int(self.result())

    return fake_exec


def _assert_released(screen: Any, dialog: Any) -> None:
    """PR-MED-019's invariant: a finished dialog holds no sample-derived text
    and is no longer owned by the tab."""
    assert dialog._draft is None
    assert dialog.exemplars_list.count() == 0
    assert dialog.unrecognised_list.count() == 0
    assert dialog.headings_list.count() == 0
    assert dialog.summary_label.text() == ""
    assert dialog.parent() is None
    assert screen.findChildren(StyleReviewDialog) == []
    with pytest.raises(RuntimeError):
        dialog.choice()


class TestDialogDisposal:
    """Peer round 17 PR-MED-019 over the REAL runners: whatever way the review
    ends, the dialog's draft (the removed sentences included) and its rows are
    released and the dialog leaves the tab's ownership."""

    def test_a_cancelled_review_releases_the_dialog(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[Any] = []
        monkeypatch.setattr(StyleReviewDialog, "exec", _auto_exec("reject", seen))
        screen = _screen(tmp_path, review_runner=run_style_review)
        screen.consent_checkbox.setChecked(True)
        screen.paste_box.setPlainText(NOTE)

        screen.learn_button.click()

        assert screen.learn_status_label.text() == LEARN_CANCELLED_TEXT
        assert len(seen) == 1
        _assert_released(screen, seen[0])
        assert not style_profile_present(root=_style_root(tmp_path))
        screen.deleteLater()

    def test_an_exception_out_of_the_review_still_releases_the_dialog(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[Any] = []
        monkeypatch.setattr(StyleReviewDialog, "exec", _auto_exec("raise", seen))
        screen = _screen(tmp_path, review_runner=run_style_review)
        screen.consent_checkbox.setChecked(True)
        screen.paste_box.setPlainText(NOTE)

        with pytest.raises(RuntimeError):
            screen.on_learn_from_notes()

        _assert_released(screen, seen[0])
        assert not style_profile_present(root=_style_root(tmp_path))
        screen.deleteLater()

    @windows_only
    def test_a_saved_review_releases_the_removed_sentence_everywhere(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Save after removing the first sentence: the store lacks it, the
        dialog no longer holds it, and the tab's own copy is the saved
        profile — once the handler has RETURNED, the removed sentence is held
        by no dialog, no tab copy and (the Save path clears the paste box) no
        widget; the handler's pasted-source local lives only until that
        return (PR-LOW-029's three lifetimes)."""
        seen: list[Any] = []
        monkeypatch.setattr(StyleReviewDialog, "exec", _auto_exec("remove-then-accept", seen))
        screen = _screen(tmp_path, review_runner=run_style_review)
        screen.consent_checkbox.setChecked(True)
        screen.paste_box.setPlainText(NOTE)
        removed_text = "Keep the neck moving gently."  # the first exemplar of NOTE

        screen.learn_button.click()

        profile = load_style_profile(root=_style_root(tmp_path))
        assert profile is not None
        assert removed_text not in [e.exemplar_text for e in profile.exemplars]
        assert len(profile.exemplars) == 4
        _assert_released(screen, seen[0])
        assert screen.style_profile == profile
        rows = [
            screen.learned_exemplars_list.item(i).text()
            for i in range(screen.learned_exemplars_list.count())
        ]
        assert all(removed_text not in row for row in rows)
        screen.deleteLater()

    @windows_only
    def test_the_delete_originals_dialog_is_released_too(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        review_seen: list[Any] = []
        delete_seen: list[Any] = []
        monkeypatch.setattr(StyleReviewDialog, "exec", _auto_exec("accept", review_seen))
        monkeypatch.setattr(DeleteOriginalsDialog, "exec", _auto_exec("reject", delete_seen))
        notes = tmp_path / "notes"
        notes.mkdir()
        first = notes / "a.txt"
        first.write_text(NOTE, encoding="utf-8")
        screen = _screen(
            tmp_path,
            file_picker=lambda: (first,),
            review_runner=run_style_review,
            delete_originals_runner=run_delete_originals,
        )
        screen.choose_files_button.click()
        screen.consent_checkbox.setChecked(True)

        screen.learn_button.click()

        assert first.exists()
        assert "The original notes were kept." in screen.learn_status_label.text()
        assert len(delete_seen) == 1
        dialog = delete_seen[0]
        assert dialog.paths_list.count() == 0
        assert dialog.parent() is None
        assert screen.findChildren(DeleteOriginalsDialog) == []
        _assert_released(screen, review_seen[0])
        screen.deleteLater()


class TestPollNeverDecrypts:
    def test_no_five_second_poll_opens_either_store(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Case 24 (round 51 MED-001, over BOTH 5 s timers): neither the
        Practitioner tab's availability poll nor the microphone screen's
        model-status poll opens the STYLE store, and with the speaker model's
        presence held steady (as this test holds it) neither opens either
        store — the microphone poll's one voice-profile re-read on a presence
        transition is round 55 PR-REG-006's documented exception. Only
        ``refresh_style_profile_state`` decrypts the style store, and it is
        called on the tab's own learn / remove / delete events."""
        from scribe_desktop.ui.microphone import MicrophoneScreen

        screen = _screen(tmp_path)
        mic = MicrophoneScreen(
            _MicFakeController(), _FakeBackend(), benchmark_runner=list, profile_root=tmp_path
        )
        opened: list[str] = []

        def counting_open(store: Any, base: Path) -> None:
            opened.append(str(base))
            return None

        monkeypatch.setattr(practitioner_profile, "_open", counting_open)

        screen.refresh_availability()
        screen.refresh_availability()
        screen.refresh_availability()
        screen._update_controls()
        screen.refresh_style_options()
        mic.refresh_model_status()
        mic.refresh_model_status()
        mic.refresh_model_status()
        mic._on_benchmark_done([])

        assert opened == []

        screen.refresh_style_profile_state()
        assert len(opened) == 1

        mic.deleteLater()
        screen.deleteLater()
