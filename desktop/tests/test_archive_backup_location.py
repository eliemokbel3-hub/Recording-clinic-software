"""Past-sessions-backup plan Task 1.4 (D7, D10; C6): where a backup may be
written and read from, and ``config\\backup.json``.

Every Windows call goes through ``Layer`` — a fake with nothing real behind
it (the conftest sentinel makes the real ``Win32WindowsLayer`` raise). Every
path is synthetic; the settings tests use the test's own folder."""

from __future__ import annotations

import builtins
import json
import os
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from scribe_desktop import exclusions, note_config
from scribe_desktop.exclusions import (
    BACKUP_DRIVE_REFUSED,
    BACKUP_SAME_DISK,
    BACKUP_SOURCE_REFUSED,
    DRIVE_CDROM,
    DRIVE_RAMDISK,
    DRIVE_REMOTE,
    DRIVE_REMOVABLE,
    EXPORT_APP_FOLDER,
    EXPORT_NETWORK,
    EXPORT_ONEDRIVE,
    EXPORT_ROAMING,
    EXPORT_UNCHECKED,
    FILE_ATTRIBUTE_DIRECTORY,
    FILE_ATTRIBUTE_REPARSE_POINT,
    ArchiveBackupLocation,
    check_archive_backup_location,
    check_backup_source,
    check_export_location,
    proposed_backup_folder,
)
from scribe_desktop.note_config import (
    BACKUP_SETTINGS_FILENAME,
    MAX_BACKUP_SETTINGS_BYTES,
    BackupSettings,
    NoteConfigWriteError,
    read_backup_settings,
    save_backup_settings,
)

_LOCAL = r"C:\Users\pat\AppData\Local"
_ENV = {"LOCALAPPDATA": _LOCAL, "USERPROFILE": r"C:\Users\pat"}
_FILE = 0x20  # FILE_ATTRIBUTE_ARCHIVE: an ordinary file
VOL_C = "\\\\?\\Volume{0000000c-0000-0000-0000-000000000000}\\"
VOL_D = "\\\\?\\Volume{0000000d-0000-0000-0000-000000000000}\\"
VOL_E = "\\\\?\\Volume{0000000e-0000-0000-0000-000000000000}\\"


class Layer:
    """A ``WindowsLayer`` fake. ``real`` maps a path to what ``realpath``
    resolves it to; ``drives`` a drive root to its type (fixed by default);
    ``volumes`` a (case-folded) path prefix to its volume — the longest
    prefix wins, else the drive letter's own volume; ``attributes`` a path
    to its attributes (a folder by default); ``absent`` the paths whose
    attributes raise ``FileNotFoundError``; ``broken`` the methods that
    raise. ``touched`` records every call that touches a path."""

    def __init__(
        self,
        *,
        env: dict[str, str] | None = None,
        real: dict[str, str] | None = None,
        drives: dict[str, int] | None = None,
        volumes: dict[str, tuple[str, int]] | None = None,
        attributes: dict[str, int] | None = None,
        absent: tuple[str, ...] = (),
        broken: tuple[str, ...] = (),
    ) -> None:
        self.env = {**_ENV, **(env or {})}
        self.real = dict(real or {})
        self.drives = {key.upper(): value for key, value in (drives or {}).items()}
        self.volumes = {key.casefold(): value for key, value in (volumes or {}).items()}
        self.attributes = {key.casefold(): value for key, value in (attributes or {}).items()}
        self.absent = {path.casefold() for path in absent}
        self.broken = set(broken)
        self.touched: list[tuple[str, str]] = []
        self.drive_calls: list[str] = []

    def _check(self, name: str) -> None:
        if name in self.broken:
            raise RuntimeError(f"{name} broke")

    def environ(self, name: str) -> str | None:
        self._check("environ")
        return self.env.get(name) or None

    def realpath(self, path: str) -> str:
        self.touched.append(("realpath", path))
        self._check("realpath")
        return self.real.get(path, path)

    def drive_type(self, root: str) -> int:
        self._check("drive_type")
        self.drive_calls.append(root)
        return self.drives.get(root.upper(), 3)

    def volume_of(self, path: str) -> tuple[str, int]:
        self.touched.append(("volume_of", path))
        self._check("volume_of")
        folded = path.casefold().replace("/", "\\")
        matches = [prefix for prefix in self.volumes if folded.startswith(prefix)]
        if matches:
            return self.volumes[max(matches, key=len)]
        letter = folded[:1].upper()
        root = f"{letter}:\\"
        return f"\\\\?\\Volume{{letter-{letter}}}\\", self.drives.get(root, 3)

    def file_attributes(self, path: str) -> int:
        self.touched.append(("file_attributes", path))
        self._check("file_attributes")
        folded = path.casefold()
        if folded in self.absent:
            raise FileNotFoundError(path)
        return self.attributes.get(folded, FILE_ATTRIBUTE_DIRECTORY)

    def set_file_attributes(self, path: str, attributes: int) -> bool:
        raise AssertionError("a location check never sets an attribute")


def _check(folder: str, **layer: Any) -> ArchiveBackupLocation:
    return check_archive_backup_location(Layer(**layer), Path(folder))


def _refused(code: str, line: str) -> ArchiveBackupLocation:
    return ArchiveBackupLocation("refused", code, line)


_UNCHECKED = _refused("location_unchecked", EXPORT_UNCHECKED)

# Round 23 PR-MED-2302: the extended UNC namespace in any case, and a
# prefixed path that names no drive letter once its prefix is removed.
_NAMESPACED = (
    r"\\?\UNC\server\share",
    r"\\?\unc\server\share",
    r"\\?\Unc\server\share",
    r"\\?\GLOBALROOT\Device\Mup\server\share",
    # Security review round 41: the NT object prefix, passed through unchanged.
    r"\??\UNC\server\share",
    r"\??\unc\server\share",
)


# ---------------------------------------------------------------------------
# The destination rule.
# ---------------------------------------------------------------------------


class TestArchiveBackupLocation:
    def test_another_fixed_drive_is_admitted(self) -> None:
        assert _check(r"D:\Backups") == ArchiveBackupLocation("ok", "location_ok")

    def test_a_removable_drive_is_admitted(self) -> None:
        result = _check(r"E:\Backups", drives={"E:\\": DRIVE_REMOVABLE})
        assert result == ArchiveBackupLocation("ok", "location_ok")

    def test_the_data_folders_own_volume_is_warned_through_a_drive_letter(self) -> None:
        result = _check(r"C:\Backups")
        assert result == ArchiveBackupLocation("warned", "location_same_volume", BACKUP_SAME_DISK)

    def test_the_same_volume_is_found_through_a_mounted_folder(self) -> None:
        """By GUID name: a folder of D: that mounts C:'s volume is C:'s disk;
        a folder of C: that mounts another volume is not."""
        volumes = {
            "c:\\": (VOL_C, 3),
            "d:\\": (VOL_D, 3),
            "d:\\mnt\\system": (VOL_C, 3),
            "c:\\mnt\\other": (VOL_E, DRIVE_REMOVABLE),
        }
        mounted = _check(r"D:\mnt\system\Backups", volumes=volumes)
        assert mounted.outcome == "warned"
        other = _check(r"C:\mnt\other\Backups", volumes=volumes)
        assert other == ArchiveBackupLocation("ok", "location_ok")

    def test_a_mounted_folder_is_judged_by_its_volumes_type(self) -> None:
        volumes = {"d:\\mnt\\disc": (VOL_E, DRIVE_CDROM)}
        result = _check(r"D:\mnt\disc", volumes=volumes)
        assert result == _refused("location_drive", BACKUP_DRIVE_REFUSED)

    @pytest.mark.parametrize(
        "drive_type",
        [0, 1, DRIVE_CDROM, DRIVE_RAMDISK],
        ids=["unknown", "no_root", "cdrom", "ramdisk"],
    )
    def test_a_drive_a_backup_cannot_be_kept_on_is_refused(self, drive_type: int) -> None:
        result = _check(r"E:\Backups", drives={"E:\\": drive_type})
        assert result == _refused("location_drive", BACKUP_DRIVE_REFUSED)

    def test_onedrive_is_refused(self) -> None:
        onedrive = {"OneDrive": r"C:\Users\pat\OneDrive"}
        result = _check(r"C:\Users\pat\OneDrive\Backups", env=onedrive)
        assert result == _refused("location_onedrive", EXPORT_ONEDRIVE)

    def test_the_roaming_profile_is_refused(self) -> None:
        result = _check(
            r"C:\Users\pat\AppData\Roaming\Backups",
            env={"APPDATA": r"C:\Users\pat\AppData\Roaming"},
        )
        assert result == _refused("location_roaming", EXPORT_ROAMING)

    def test_a_folder_that_resolves_onto_the_network_is_refused(self) -> None:
        result = _check("chosen-folder", real={"chosen-folder": r"\\server\share\b"})
        assert result == _refused("location_network", EXPORT_NETWORK)

    def test_a_remote_volume_behind_a_mounted_folder_is_refused(self) -> None:
        result = _check(r"D:\mnt\remote", volumes={"d:\\mnt\\remote": (VOL_E, DRIVE_REMOTE)})
        assert result == _refused("location_network", EXPORT_NETWORK)

    @pytest.mark.parametrize(
        "folder",
        [_LOCAL + r"\ClinikoScribe", _LOCAL + r"\ClinikoScribe\past_sessions",
         _LOCAL + r"\CLINIKOSCRIBE-DEV\backups"],
        ids=["production", "production_child", "dev_any_case"],
    )
    def test_either_app_data_folder_is_refused(self, folder: str) -> None:
        assert _check(folder) == _refused("location_app_folder", EXPORT_APP_FOLDER)

    @pytest.mark.parametrize("folder", [r"\\server\share\backups", r"Z:\backups", *_NAMESPACED])
    def test_a_network_path_is_refused_from_its_text_alone(self, folder: str) -> None:
        """No call that touches the path: the fake fails on realpath,
        attributes and volume_of, and the answer is still the network
        refusal — only the drive root's type was asked."""
        layer = Layer(
            drives={"Z:\\": DRIVE_REMOTE}, broken=("realpath", "file_attributes", "volume_of")
        )
        result = check_archive_backup_location(layer, Path(folder))
        assert result == _refused("location_network", EXPORT_NETWORK)
        assert layer.touched == []
        assert all(len(root) == 3 for root in layer.drive_calls)

    def test_an_absent_folder_is_refused(self) -> None:
        result = _check(r"D:\Backups", absent=(r"d:\backups",))
        assert result == _UNCHECKED

    def test_a_file_where_the_folder_should_be_is_refused(self) -> None:
        assert _check(r"D:\Backups", attributes={r"d:\backups": _FILE}) == _UNCHECKED

    @pytest.mark.parametrize(
        "broken", ["environ", "realpath", "drive_type", "volume_of", "file_attributes"]
    )
    def test_a_check_that_cannot_be_made_refuses(self, broken: str) -> None:
        assert _check(r"D:\Backups", broken=(broken,)) == _UNCHECKED

    def test_the_data_folders_volume_unreadable_refuses(self) -> None:
        layer = Layer()
        original = layer.volume_of

        def only_the_destination(path: str) -> tuple[str, int]:
            if "clinikoscribe" in path.casefold():
                raise OSError("no volume")
            return original(path)

        layer.volume_of = only_the_destination  # type: ignore[method-assign]
        assert check_archive_backup_location(layer, Path(r"D:\Backups")) == _UNCHECKED

    def test_no_layer_is_refused(self) -> None:
        assert check_archive_backup_location(None, Path(r"D:\Backups")) == _UNCHECKED


class TestExportLocationUnchanged:
    """``check_export_location`` keeps its own outcomes (fixed drives only);
    its full table is ``test_exclusions.py``'s. Through the shared helper it
    now also refuses a network path from the text."""

    def test_a_removable_drive_is_still_refused_for_an_export(self) -> None:
        layer = Layer(drives={"E:\\": DRIVE_REMOVABLE})
        refusal = check_export_location(layer, Path(r"E:\labels"))
        assert refusal is not None and refusal.code == "location_not_fixed"

    def test_a_fixed_drive_is_still_admitted_and_volume_of_is_never_asked(self) -> None:
        layer = Layer()
        assert check_export_location(layer, Path(r"D:\labels")) is None
        assert not [call for call in layer.touched if call[0] != "realpath"]

    @pytest.mark.parametrize("folder", [r"\\server\share\labels", *_NAMESPACED])
    def test_a_network_path_is_refused_before_realpath(self, folder: str) -> None:
        layer = Layer(broken=("realpath",))
        refusal = check_export_location(layer, Path(folder))
        assert refusal is not None and refusal.code == "location_network"
        assert layer.touched == []

    def test_a_local_extended_path_is_still_judged_by_its_drive(self) -> None:
        layer = Layer()
        assert check_export_location(layer, Path(r"\\?\D:\labels")) is None


# ---------------------------------------------------------------------------
# The remembered folder (D7: never handed to a dialog unless it still passes).
# ---------------------------------------------------------------------------


class TestProposedFolder:
    def test_an_admitted_or_warned_folder_is_proposed(self) -> None:
        assert proposed_backup_folder(Layer(), r"D:\Backups") == Path(r"D:\Backups")
        assert proposed_backup_folder(Layer(), r"C:\Backups") == Path(r"C:\Backups")

    def test_a_drive_that_has_become_remote_is_never_proposed_or_touched(self) -> None:
        layer = Layer(drives={"E:\\": DRIVE_REMOTE}, broken=("realpath", "volume_of"))
        assert proposed_backup_folder(layer, r"E:\Backups") is None
        assert layer.touched == []

    @pytest.mark.parametrize("remembered", _NAMESPACED)
    def test_a_namespaced_network_folder_is_never_proposed_or_touched(
        self, remembered: str
    ) -> None:
        layer = Layer(broken=("realpath", "volume_of", "file_attributes"))
        assert proposed_backup_folder(layer, remembered) is None
        assert layer.touched == []

    def test_an_absent_or_uninspectable_folder_is_never_proposed(self) -> None:
        assert proposed_backup_folder(Layer(absent=(r"e:\backups",)), r"E:\Backups") is None
        assert proposed_backup_folder(Layer(broken=("volume_of",)), r"E:\Backups") is None

    def test_nothing_remembered_or_no_layer_proposes_nothing(self) -> None:
        assert proposed_backup_folder(Layer(), None) is None
        assert proposed_backup_folder(Layer(), "") is None
        assert proposed_backup_folder(None, r"D:\Backups") is None


# ---------------------------------------------------------------------------
# The source rule (Open a backup).
# ---------------------------------------------------------------------------

_SOURCE = r"E:\Backups\ClinikoScribe-backup-2026-10-01.csbk"
_SOURCE_REFUSED = exclusions.ExclusionWarning("source_refused", BACKUP_SOURCE_REFUSED)


def _source(path: str = _SOURCE, **layer: Any) -> exclusions.ExclusionWarning | None:
    attributes = {path: _FILE, **layer.pop("attributes", {})}
    return check_backup_source(Layer(attributes=attributes, **layer), Path(path))


class TestBackupSource:
    def test_an_ordinary_file_on_an_attached_drive_is_admitted(self) -> None:
        assert _source(drives={"E:\\": DRIVE_REMOVABLE}) is None
        assert _source(r"C:\Backups\b.csbk") is None  # no same-disk warning for a source

    def test_a_link_is_refused(self) -> None:
        link = _FILE | FILE_ATTRIBUTE_REPARSE_POINT
        assert _source(attributes={_SOURCE: link}) == _SOURCE_REFUSED

    def test_a_folder_is_refused(self) -> None:
        assert _source(attributes={_SOURCE: FILE_ATTRIBUTE_DIRECTORY}) == _SOURCE_REFUSED

    @pytest.mark.parametrize(
        "path",
        [r"\\server\share\b.csbk", r"Z:\b.csbk", *(rf"{prefix}\b.csbk" for prefix in _NAMESPACED)],
    )
    def test_a_network_source_is_refused_from_its_text_alone(self, path: str) -> None:
        layer = Layer(
            drives={"Z:\\": DRIVE_REMOTE}, broken=("realpath", "file_attributes", "volume_of")
        )
        assert check_backup_source(layer, Path(path)) == _SOURCE_REFUSED
        assert layer.touched == []

    @pytest.mark.parametrize(
        ("change", "expected"),
        [
            ({"env": {"OneDrive": r"E:\Backups"}}, "onedrive"),
            ({"drives": {"E:\\": DRIVE_CDROM}}, "cdrom"),
            ({"real": {_SOURCE: _LOCAL + r"\ClinikoScribe\b.csbk"}}, "app folder"),
            ({"real": {_SOURCE: r"\\server\share\b.csbk"}}, "resolves to the network"),
            ({"broken": ("volume_of",)}, "uninspectable"),
            ({"broken": ("file_attributes",)}, "attributes unreadable"),
        ],
    )
    def test_a_file_whose_resolved_folder_is_refused(
        self, change: dict[str, Any], expected: str
    ) -> None:
        assert _source(**change) == _SOURCE_REFUSED, expected

    def test_no_layer_is_refused(self) -> None:
        assert check_backup_source(None, Path(_SOURCE)) == _SOURCE_REFUSED

    def test_a_refused_source_is_never_opened(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backup = tmp_path / "b.csbk"
        backup.write_bytes(b"synthetic")
        opened: list[Any] = []
        real_open = builtins.open

        def spy_open(*args: Any, **kwargs: Any) -> Any:
            opened.append(args[:1])
            return real_open(*args, **kwargs)

        def spy_os_open(*args: Any, **kwargs: Any) -> int:
            opened.append(args[:1])
            raise AssertionError("os.open reached")

        layer = Layer(attributes={str(backup): _FILE | FILE_ATTRIBUTE_REPARSE_POINT})
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "open", spy_open)
            patch.setattr(os, "open", spy_os_open)
            answer = check_backup_source(layer, backup)
        assert answer == _SOURCE_REFUSED
        assert opened == []


# ---------------------------------------------------------------------------
# config\backup.json (D10).
# ---------------------------------------------------------------------------

_MADE = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


class TestBackupSettings:
    def test_a_round_trip(self, tmp_path: Path) -> None:
        settings = BackupSettings(folder=r"E:\Backups", last_backup_at=_MADE)
        path = save_backup_settings(settings, config_root=tmp_path)
        assert path == tmp_path / BACKUP_SETTINGS_FILENAME
        assert json.loads(path.read_bytes()) == {
            "schema_version": 1,
            "folder": r"E:\Backups",
            "last_backup_at": "2026-10-01T09:00:00Z",
        }
        found = read_backup_settings(tmp_path)
        assert found == note_config.BackupSettingsRead(settings, unreadable=False)

    def test_an_offset_time_reads_back_as_the_same_instant(self, tmp_path: Path) -> None:
        sydney = _MADE.astimezone(timezone(timedelta(hours=11)))
        save_backup_settings(BackupSettings(last_backup_at=sydney), config_root=tmp_path)
        found = read_backup_settings(tmp_path).settings.last_backup_at
        assert found == _MADE

    def test_absent_is_no_folder_and_no_date(self, tmp_path: Path) -> None:
        found = read_backup_settings(tmp_path)
        assert found == note_config.BackupSettingsRead(BackupSettings(), unreadable=False)
        assert found.settings.folder is None and found.settings.last_backup_at is None

    @pytest.mark.parametrize(
        "blob",
        [
            b"not json",
            b"[]",
            b'{"folder": null, "last_backup_at": null}',
            b'{"schema_version": true}',
            b'{"schema_version": 2}',
            b'{"schema_version": 1, "folder": "E:\\\\B", "extra": 1}',
            b'{"schema_version": 1, "last_backup_at": "2026-10-01T09:00:00"}',
            b'{"schema_version": 1, "folder": "E:\\u0000B"}',
            b'{"schema_version": 1, "folder": ""}',
            b" " * (MAX_BACKUP_SETTINGS_BYTES + 1),
        ],
        ids=[
            "not_json", "not_an_object", "no_version", "bool_version", "newer", "extra_key",
            "naive_time", "control_char", "empty_folder", "over_bound",
        ],
    )
    def test_an_unreadable_file_is_no_folder_and_no_date(self, tmp_path: Path, blob: bytes) -> None:
        (tmp_path / BACKUP_SETTINGS_FILENAME).write_bytes(blob)
        found = read_backup_settings(tmp_path)
        assert found == note_config.BackupSettingsRead(BackupSettings(), unreadable=True)

    def test_the_default_root_is_the_tests_own_pinned_folder(
        self, pinned_backup_root: Path
    ) -> None:
        save_backup_settings(BackupSettings(last_backup_at=_MADE))
        assert (pinned_backup_root / BACKUP_SETTINGS_FILENAME).is_file()
        assert read_backup_settings().settings.last_backup_at == _MADE

    def test_a_document_over_its_bound_is_never_written(self, tmp_path: Path) -> None:
        # Within the character bound, over the byte bound: four bytes each.
        long_folder = "E:\\" + "\U0001f600" * 1020
        assert len(long_folder) <= note_config.MAX_BACKUP_FOLDER_CHARS
        with pytest.raises(NoteConfigWriteError):
            save_backup_settings(BackupSettings(folder=long_folder), config_root=tmp_path)
        assert not (tmp_path / BACKUP_SETTINGS_FILENAME).exists()

    def test_a_failed_write_is_typed(self, tmp_path: Path) -> None:
        blocker = tmp_path / "config"
        blocker.write_bytes(b"a file where the folder would be")
        with pytest.raises(NoteConfigWriteError):
            save_backup_settings(BackupSettings(), config_root=blocker)
