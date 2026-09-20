"""Note-learning plan Task 3.1: the Practitioner tab's "Writing style" group —
what it lists, what it disables and why, when it saves, and how an unreadable
setting or a failed write reads. Offscreen, against the REAL settings writer
under a tmp config root; the tab's other seams (profile store, models,
microphone) are stubbed, and no default store root is ever consulted."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from scribe_desktop.audio_capture import AudioDevice  # noqa: E402
from scribe_desktop.note_config import (  # noqa: E402
    PRACTITIONER_SETTINGS_FILENAME,
    NoteConfigWriteError,
    PractitionerSettings,
    load_practitioner_settings,
    save_practitioner_settings,
)
from scribe_desktop.ui import models  # noqa: E402


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
        # The learned-style store root the default options provider STATS —
        # never the default one.
        "style_root": tmp_path / "style",
        "embedder_available": lambda kind: True,
        "vad_available": lambda: True,
        "readiness_provider": lambda: models.AttributionReadiness(
            profile_present=False, profile=None, reason=None
        ),
    }
    kwargs.update(overrides)
    return PractitionerScreen(_FakeController(), _FakeBackend(), **kwargs)


def _settings_path(tmp_path: Path) -> Path:
    return tmp_path / "config" / PRACTITIONER_SETTINGS_FILENAME


def _write_settings_blob(tmp_path: Path, blob: str) -> None:
    root = tmp_path / "config"
    root.mkdir(parents=True, exist_ok=True)
    (root / PRACTITIONER_SETTINGS_FILENAME).write_text(blob, encoding="utf-8")


class TestWritingStyleGroup:
    def test_lists_every_style_with_the_unavailable_ones_disabled(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """C8: all four styles are shown; the two prose styles are disabled
        with their reason under the group, never hidden."""
        screen = _screen(tmp_path)

        assert list(screen.style_radios) == list(models.NOTE_STYLES)
        assert [screen.style_radios[style].text() for style in models.NOTE_STYLES] == [
            models.STYLE_LABELS[style] for style in models.NOTE_STYLES
        ]
        assert screen.style_radios["clean"].isChecked()  # the default setting
        assert screen.style_radios["verbatim"].isEnabled()
        assert screen.style_radios["clean"].isEnabled()
        assert not screen.style_radios["own_voice"].isEnabled()
        assert not screen.style_radios["narrative"].isEnabled()

        assert not screen.style_reason_label.isHidden()
        lines = screen.style_reason_label.text().split("\n")
        assert len(lines) == 2
        assert lines[0].startswith(models.STYLE_LABELS["own_voice"])
        assert models.LANGUAGE_MODEL_ABSENT_REASON in lines[0]
        assert models.STYLE_PROFILE_EMPTY_REASON in lines[0]
        assert lines[1].startswith(models.STYLE_LABELS["narrative"])
        assert models.LANGUAGE_MODEL_ABSENT_REASON in lines[1]
        assert models.STYLE_PROFILE_EMPTY_REASON not in lines[1]

        assert screen.style_status_label.isHidden()
        screen.deleteLater()

    def test_picking_a_style_saves_it_at_once_and_it_comes_back(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen = _screen(tmp_path)
        screen.style_radios["verbatim"].click()

        assert load_practitioner_settings(tmp_path / "config").note_style == "verbatim"
        assert screen.style_status_label.text() == "Writing style saved: Verbatim."
        assert not screen.style_status_label.isHidden()
        screen.deleteLater()

        reopened = _screen(tmp_path)
        assert reopened.style_radios["verbatim"].isChecked()
        assert not reopened.style_radios["clean"].isChecked()
        reopened.deleteLater()

    def test_an_unreadable_setting_falls_back_and_says_so(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        _write_settings_blob(tmp_path, "{not json")
        screen = _screen(tmp_path)

        assert screen.style_radios["clean"].isChecked()
        assert not screen.style_status_label.isHidden()
        assert screen.style_status_label.text().startswith("Writing style setting unreadable")
        screen.deleteLater()

    def test_a_saved_but_unavailable_style_stays_selected_and_disabled(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """A style the app cannot honour yet is not silently rewritten: the
        radio stays checked, disabled, and the status line says how the note
        is rendered meanwhile (C8)."""
        save_practitioner_settings(
            PractitionerSettings(note_style="own_voice"), config_root=tmp_path / "config"
        )
        screen = _screen(tmp_path)

        assert screen.style_radios["own_voice"].isChecked()
        assert not screen.style_radios["own_voice"].isEnabled()
        fallback = models.style_fallback_line("own_voice")
        assert fallback is not None
        assert fallback in screen.style_status_label.text()
        assert not screen.style_status_label.isHidden()
        assert load_practitioner_settings(tmp_path / "config").note_style == "own_voice"
        screen.deleteLater()

    def test_every_style_is_enabled_once_its_needs_are_met(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen = _screen(
            tmp_path,
            style_options_provider=lambda: models.style_options(
                model_available=lambda: True, style_present=lambda root: True
            ),
        )

        assert all(screen.style_radios[style].isEnabled() for style in models.NOTE_STYLES)
        assert screen.style_reason_label.isHidden()
        assert screen.style_reason_label.text() == ""
        screen.deleteLater()

    def test_a_failed_write_keeps_the_saved_style_and_names_the_failure(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        screen = _screen(tmp_path)

        def raiser(style: Any, *, config_root: Any = None) -> Any:
            raise NoteConfigWriteError("disk full")

        monkeypatch.setattr(models, "save_note_style", raiser)
        screen.style_radios["verbatim"].click()

        assert screen.style_status_label.text().startswith("Could not save the writing style")
        assert "NoteConfigWriteError" in screen.style_status_label.text()
        assert screen.style_radios["clean"].isChecked()
        assert not screen.style_radios["verbatim"].isChecked()
        assert not _settings_path(tmp_path).exists()
        screen.deleteLater()

    def test_helper_built_tab_never_reads_the_default_config_root(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The PR-REG-005 class for the writing-style group: a tab built with
        an explicit config root reaches the default root neither at
        construction nor when a style is picked."""
        from scribe_desktop import note_config

        def forbidden() -> Path:
            raise AssertionError("the default config root must not be consulted")

        monkeypatch.setattr(note_config, "default_config_root", forbidden)
        screen = _screen(tmp_path)
        screen.style_radios["verbatim"].click()

        assert _settings_path(tmp_path).exists()
        assert load_practitioner_settings(tmp_path / "config").note_style == "verbatim"
        screen.deleteLater()

    def test_the_radios_are_disabled_while_the_tab_is_busy(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        screen = _screen(
            tmp_path,
            style_options_provider=lambda: models.style_options(
                model_available=lambda: True, style_present=lambda root: True
            ),
        )
        assert all(screen.style_radios[style].isEnabled() for style in models.NOTE_STYLES)

        monkeypatch.setattr(type(screen), "is_busy", property(lambda self: True))
        screen._update_controls()

        assert not any(screen.style_radios[style].isEnabled() for style in models.NOTE_STYLES)
        screen.deleteLater()
