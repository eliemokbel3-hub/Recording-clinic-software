"""Development-recordings plan Task 1.1 (D1, C3, C9): the development setting
``config\\development.json`` (``note_config.DevelopmentSettings`` /
``read_development_settings``).

It fails CLOSED to OFF on every path: an absent file is off, and a file that
is present but cannot be used is off too, named as unreadable — the OPPOSITE
of ``read_pilot_settings``, whose unreadable state is shadow ON. Keeping a
recording is the risky direction, so nothing that cannot be read keeps one.

Every file is under ``tmp_path`` or the conftest's pinned development root
(``pinned_development_root``, C9)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import REAL_DEVELOPMENT_SETTINGS_ROOT, bounded_read_spy
from scribe_desktop import note_config
from scribe_desktop.note_config import (
    DEVELOPMENT_SETTINGS_FILENAME,
    MAX_DEVELOPMENT_SETTINGS_BYTES,
    DevelopmentSettings,
    DevelopmentSettingsRead,
    NoteConfigError,
    PilotSettingsRead,
    keep_recordings_on,
    read_development_settings,
    read_pilot_settings,
    save_development_settings,
)

OFF = DevelopmentSettingsRead(keep_recordings=False, unreadable=False)
ON = DevelopmentSettingsRead(keep_recordings=True, unreadable=False)
UNREADABLE = DevelopmentSettingsRead(keep_recordings=False, unreadable=True)

_UNUSABLE = [
    "{not json",
    "",
    '{"schema_version": 1, "keep_recordings": true, "extra": 1}',
    '{"schema_version": 2, "keep_recordings": true}',
    '{"schema_version": 1, "keep_recordings": 1}',
    '{"schema_version": 1, "keep_recordings": "true"}',
    # Round 26's rule: only an integer is a version this app wrote.
    '{"schema_version": true, "keep_recordings": true}',
    '{"schema_version": 1.0, "keep_recordings": true}',
    '{"schema_version": "1", "keep_recordings": true}',
    "[true]",
    "null",
    b"\xff\xfe\x00",
    # Present but naming no setting: no readable setting, so unreadable.
    "{}",
    '{"schema_version": 1}',
    # Review round 8 LOW-001: stored bytes must NAME their version — the
    # model's default is for building one — so this is OFF, never ON.
    '{"keep_recordings": true}',
    # Nested deeper than the parser allows, inside the size bound.
    "[" * 2000 + "]" * 2000,
]


def _write(root: Path, blob: bytes | str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / DEVELOPMENT_SETTINGS_FILENAME
    path.write_bytes(blob.encode("utf-8") if isinstance(blob, str) else blob)
    return path


class TestTheSettingsFile:
    def test_an_absent_file_is_off_and_not_unreadable(self, tmp_path: Path) -> None:
        assert read_development_settings(tmp_path) == OFF
        assert keep_recordings_on(tmp_path) is False

    def test_saved_on_and_off_read_back(self, tmp_path: Path) -> None:
        path = save_development_settings(
            DevelopmentSettings(keep_recordings=True), config_root=tmp_path
        )
        assert path == tmp_path / "development.json"
        assert json.loads(path.read_text(encoding="utf-8")) == {
            "schema_version": 1,
            "keep_recordings": True,
        }
        assert read_development_settings(tmp_path) == ON
        assert keep_recordings_on(tmp_path) is True
        save_development_settings(DevelopmentSettings(keep_recordings=False), config_root=tmp_path)
        assert read_development_settings(tmp_path) == OFF
        assert keep_recordings_on(tmp_path) is False

    @pytest.mark.parametrize("blob", _UNUSABLE)
    def test_a_file_it_cannot_use_is_off_and_named(
        self, tmp_path: Path, blob: bytes | str
    ) -> None:
        """C3: a corrupt file never keeps a recording — OFF, and named as
        unreadable so the Status tab can say so."""
        _write(tmp_path, blob)
        assert read_development_settings(tmp_path) == UNREADABLE
        assert keep_recordings_on(tmp_path) is False

    @pytest.mark.parametrize("blob", ["{not json", "{}", '{"schema_version": 1}'])
    def test_the_polarity_is_the_opposite_of_the_pilot_setting(
        self, tmp_path: Path, blob: str
    ) -> None:
        """The same unusable bytes read as shadow ON in ``pilot.json`` and as
        keep OFF here: copying ``read_pilot_settings`` literally would have
        inverted this (the plan's Integration Notes)."""
        _write(tmp_path, blob)
        (tmp_path / "pilot.json").write_bytes(blob.encode("utf-8"))
        assert read_pilot_settings(tmp_path) == PilotSettingsRead(
            shadow_mode=True, unreadable=True
        )
        assert read_development_settings(tmp_path) == UNREADABLE

    def test_an_oversized_file_is_off_and_read_bounded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        body = '{"schema_version": 1, "keep_recordings": true}'
        _write(tmp_path, body + " " * MAX_DEVELOPMENT_SETTINGS_BYTES)
        sizes = bounded_read_spy(monkeypatch, DEVELOPMENT_SETTINGS_FILENAME)
        assert read_development_settings(tmp_path) == UNREADABLE
        assert sizes == [MAX_DEVELOPMENT_SETTINGS_BYTES + 1]

    def test_a_file_that_cannot_be_opened_is_off_and_named(self, tmp_path: Path) -> None:
        (tmp_path / DEVELOPMENT_SETTINGS_FILENAME).mkdir(parents=True)  # a folder: open fails
        assert read_development_settings(tmp_path) == UNREADABLE

    def test_a_nul_in_the_root_is_off_and_named(self, tmp_path: Path) -> None:
        assert read_development_settings(tmp_path / "a\x00b") == UNREADABLE

    def test_a_failed_save_raises_by_type(self, tmp_path: Path) -> None:
        blocker = tmp_path / "config"
        blocker.write_bytes(b"")  # a file where the folder should be
        with pytest.raises(NoteConfigError):
            save_development_settings(
                DevelopmentSettings(keep_recordings=True), config_root=blocker
            )

    def test_the_setting_must_be_named_to_build(self) -> None:
        with pytest.raises(ValueError):
            DevelopmentSettings()  # type: ignore[call-arg]

    def test_a_saved_file_names_its_version(self, tmp_path: Path) -> None:
        """What ``save`` writes is what ``from_bytes`` reads: the version is
        always named, so the round 8 rule never refuses this app's file."""
        settings = DevelopmentSettings(keep_recordings=True)
        assert json.loads(settings.to_bytes())["schema_version"] == 1
        assert DevelopmentSettings.from_bytes(settings.to_bytes()) == settings


class TestTheDefaultRoot:
    def test_the_real_resolver_is_the_config_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The resolver's own test: the real function, with ``LOCALAPPDATA``
        driven to ``tmp_path`` (never the host's)."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert REAL_DEVELOPMENT_SETTINGS_ROOT() == note_config.default_config_root()
        assert REAL_DEVELOPMENT_SETTINGS_ROOT() == tmp_path / "ClinikoScribe" / "config"

    def test_every_test_reads_an_empty_pinned_root(self, pinned_development_root: Path) -> None:
        """C9: with no root passed, the read lands in the test's own empty
        folder (off), never the host's config — and a save lands there too,
        in both directions."""
        assert note_config.development_settings_root() == pinned_development_root
        assert list(pinned_development_root.iterdir()) == []
        assert read_development_settings() == OFF
        save_development_settings(DevelopmentSettings(keep_recordings=True))
        assert (pinned_development_root / DEVELOPMENT_SETTINGS_FILENAME).is_file()
        assert read_development_settings() == ON
        assert keep_recordings_on() is True

    def test_the_pinned_root_is_not_the_pilot_root(
        self, pinned_development_root: Path, pinned_pilot_root: Path
    ) -> None:
        assert pinned_development_root != pinned_pilot_root
