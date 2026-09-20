"""Note-learning plan Task 2.5: the Practitioner tab's "Learned shorthand"
group — what it lists, what Delete removes, and how a loader failure reads.
Offscreen, against the REAL config writers under a tmp config root; the tab's
other seams (profile store, models, microphone) are stubbed, and no default
store root is ever consulted."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from scribe_desktop.audio_capture import AudioDevice  # noqa: E402
from scribe_desktop.note_config import (  # noqa: E402
    LEARNED_RULES_SIDECAR_FILENAME,
    LearnedRuleCandidate,
    append_learned_rules,
    load_learned_rules,
    record_rule_outcomes,
)
from scribe_desktop.ui import models  # noqa: E402

_FIRST = LearnedRuleCandidate("treatment_performed", "crack into the neck", "HVLA Cx")
_SECOND = LearnedRuleCandidate(
    "advice_home_exercise", "keep up the stretches", "Home exercises reviewed."
)
_FIRST_AT = datetime(2026, 9, 18, tzinfo=UTC)
_SECOND_AT = datetime(2026, 9, 19, tzinfo=UTC)

_FIRST_RECENT = (
    "2026-09-18 - Treatment performed: 'crack into the neck' -> 'HVLA Cx' (confirmed 0 of 3)"
)
_SECOND_RECENT = (
    "2026-09-19 - Advice and home exercise: 'keep up the stretches' -> "
    "'Home exercises reviewed.' (confirmed 0 of 3)"
)
_FIRST_ALL = "Treatment performed: 'crack into the neck' -> 'HVLA Cx' (confirmed 0 of 3)"
_SECOND_ALL = (
    "Advice and home exercise: 'keep up the stretches' -> "
    "'Home exercises reviewed.' (confirmed 0 of 3)"
)


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


def _screen(tmp_path: Path, **overrides: Any) -> Any:
    from scribe_desktop.ui.practitioner import PractitionerScreen

    kwargs: dict[str, Any] = {
        "profile_root": tmp_path / "profile",
        "config_root": tmp_path / "config",
        "style_root": tmp_path / "style",
        "embedder_available": lambda kind: True,
        "vad_available": lambda: True,
        "readiness_provider": lambda: models.AttributionReadiness(
            profile_present=False, profile=None, reason=None
        ),
    }
    kwargs.update(overrides)
    return PractitionerScreen(_FakeController(), _FakeBackend(), **kwargs)


def _texts(widget: Any) -> list[str]:
    return [widget.item(index).text() for index in range(widget.count())]


def _ids(widget: Any) -> list[str]:
    from PySide6.QtCore import Qt

    return [
        str(widget.item(index).data(Qt.ItemDataRole.UserRole)) for index in range(widget.count())
    ]


def _learn_both(root: Path) -> tuple[str, str]:
    """Learn the two candidates, oldest first; returns their rule ids."""
    first = append_learned_rules([_FIRST], config_root=root, learned_at=_FIRST_AT)
    second = append_learned_rules([_SECOND], config_root=root, learned_at=_SECOND_AT)
    assert first.skipped == () and second.skipped == ()
    assert first.sidecar_error is None and second.sidecar_error is None
    return first.added[0].rule_id, second.added[0].rule_id


class TestLearnedShorthandGroup:
    def test_constructs_empty_with_nothing_to_delete(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.ui.practitioner import NO_LEARNED_RULES_TEXT

        screen = _screen(tmp_path)
        assert screen.recently_learned_rules_list.count() == 0
        assert screen.learned_rules_list.count() == 0
        assert screen.learned_rules_note_label.text() == NO_LEARNED_RULES_TEXT
        assert not screen.delete_recent_rule_button.isEnabled()
        assert not screen.delete_learned_rule_button.isEnabled()
        screen.deleteLater()

    def test_lists_learned_rules_newest_first_and_by_section(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        first_id, _second_id = _learn_both(root)
        screen = _screen(tmp_path)
        screen.refresh_learned_rules()

        assert _texts(screen.recently_learned_rules_list) == [_SECOND_RECENT, _FIRST_RECENT]
        # Canonical section order: treatment_performed before advice_home_exercise.
        assert _texts(screen.learned_rules_list) == [_FIRST_ALL, _SECOND_ALL]
        assert _ids(screen.learned_rules_list) == [first_id, _second_id]
        assert screen.delete_recent_rule_button.isEnabled()
        assert screen.delete_learned_rule_button.isEnabled()
        assert screen.learned_rules_note_label.text() == (
            "Delete removes the rule from your rules file; its lines then never "
            "propose or pre-fill again."
        )

        for _ in range(3):
            record_rule_outcomes({first_id: "confirmed"}, config_root=root)
        screen.refresh_learned_rules()
        assert _texts(screen.learned_rules_list)[0] == (
            "Treatment performed: 'crack into the neck' -> 'HVLA Cx' (pre-filled)"
        )
        assert _texts(screen.recently_learned_rules_list)[1] == (
            "2026-09-18 - Treatment performed: 'crack into the neck' -> 'HVLA Cx' (pre-filled)"
        )
        screen.deleteLater()

    def test_delete_removes_the_rule_and_says_so(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.ui.practitioner import NO_LEARNED_RULES_TEXT

        root = tmp_path / "config"
        first_id, second_id = _learn_both(root)
        screen = _screen(tmp_path)
        screen.refresh_learned_rules()

        assert screen.delete_learned_rule(first_id) is True
        assert screen.recently_learned_rules_list.count() == 1
        assert _ids(screen.learned_rules_list) == [second_id]
        assert first_id not in {rule.rule_id for rule in load_learned_rules(root).recent}
        assert screen.learned_rules_note_label.text() == f"Deleted shorthand rule '{first_id}'."

        # The same deletion through the list selection and the button.
        screen.learned_rules_list.setCurrentRow(0)
        screen.delete_learned_rule_button.click()
        assert screen.learned_rules_list.count() == 0
        assert screen.recently_learned_rules_list.count() == 0
        assert load_learned_rules(root).by_section == ()
        assert screen.learned_rules_note_label.text() == f"Deleted shorthand rule '{second_id}'."

        screen.refresh_learned_rules()
        assert screen.learned_rules_note_label.text() == NO_LEARNED_RULES_TEXT
        screen.deleteLater()

    def test_a_malformed_sidecar_is_shown_not_raised(self, qapp: Any, tmp_path: Path) -> None:
        root = tmp_path / "config"
        _learn_both(root)
        (root / LEARNED_RULES_SIDECAR_FILENAME).write_text("{not json", encoding="utf-8")
        screen = _screen(tmp_path)
        screen.refresh_learned_rules()
        assert screen.learned_rules_note_label.text().startswith("Learned shorthand unavailable")
        assert screen.recently_learned_rules_list.count() == 0
        assert screen.learned_rules_list.count() == 0
        assert not screen.delete_recent_rule_button.isEnabled()
        assert not screen.delete_learned_rule_button.isEnabled()
        screen.deleteLater()

    def test_helper_built_tab_never_reads_the_default_config_root(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The PR-REG-005 class for the shorthand group: a tab built with an
        explicit config root reaches the default root neither at construction
        nor on a refresh."""
        from scribe_desktop import note_config
        from scribe_desktop.ui.practitioner import NO_LEARNED_RULES_TEXT

        def forbidden() -> Path:
            raise AssertionError("the default config root must not be consulted")

        monkeypatch.setattr(note_config, "default_config_root", forbidden)
        screen = _screen(tmp_path)
        screen.refresh_learned_rules()
        assert screen.learned_rules_note_label.text() == NO_LEARNED_RULES_TEXT
        screen.deleteLater()
