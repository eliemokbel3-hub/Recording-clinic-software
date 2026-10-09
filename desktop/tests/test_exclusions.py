"""Privacy-professional-controls Task 4.1 (D10, Flow 6, C3, C6): the start-up
exclusions and the exception hooks.

Every Windows call goes through ``FakeLayer`` — no test reads the real
registry, WER, environment or ``%LOCALAPPDATA%``, and no real file attribute
is set (the conftest sentinel makes the real ``Win32WindowsLayer`` raise). The
exception hooks are installed and restored inside a fixture."""

from __future__ import annotations

import gc
import logging
import os
import sys
import threading
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from conftest import use_channel, use_frozen  # noqa: E402
from scribe_desktop import exclusions, install_layout  # noqa: E402
from scribe_desktop import past_sessions as exclusions_past_sessions  # noqa: E402
from scribe_desktop.exclusions import (  # noqa: E402
    BACKUP_EXCLUSION_KEYS,
    BACKUP_NOT_EXCLUDED,
    BACKUP_UNCHECKED,
    DRIVE_REMOTE,
    FILE_ATTRIBUTE_NOT_CONTENT_INDEXED,
    LOCATION_NETWORK,
    LOCATION_ONEDRIVE,
    LOCATION_ROAMING,
    LOCATION_UNCHECKED,
    NOT_INDEXED_FAILED,
    WER_EXCLUDED_APPLICATIONS,
    WER_EXCLUDED_KEY,
    WER_UNCHECKED,
    ExceptionHook,
    check_backup_exclusions,
    check_location,
    check_wer,
    exception_type_name,
    install_exception_hooks,
    mark_not_indexed,
    remove_exception_hooks,
    startup_exclusions,
    uncovered_launch_line,
    wer_not_excluded_line,
)

_DIRECTORY = 0x10
_HIDDEN = 0x2
_ALL_EXCLUDED = dict.fromkeys(WER_EXCLUDED_APPLICATIONS, 1)
# Installation plan Task 2.4: what the installer writes (Task 3.4's forms).
_ALL_BACKUP = dict.fromkeys(BACKUP_EXCLUSION_KEYS, install_layout.backup_exclusion_patterns())
_LOCAL = r"C:\Users\pat\AppData\Local"
_PROFILE_ENV = {"LOCALAPPDATA": _LOCAL, "USERPROFILE": r"C:\Users\pat"}


class FakeLayer:
    """A ``WindowsLayer`` with nothing real behind it. ``real`` maps a path to
    what ``realpath`` resolves it to; ``attributes`` holds each folder's
    attributes (a plain directory by default); ``refuse`` lists the paths
    ``SetFileAttributesW`` refuses; ``broken`` lists the method names that
    raise."""

    def __init__(
        self,
        *,
        env: dict[str, str] | None = None,
        real: dict[str, str] | None = None,
        drives: dict[str, int] | None = None,
        attributes: dict[str, int] | None = None,
        refuse: tuple[str, ...] = (),
        wer: dict[str, int] | None = None,
        wer_error: Exception | None = None,
        hklm_wer: dict[str, int] | None = None,
        backup: dict[str, tuple[str, ...]] | None = None,
        backup_error: Exception | None = None,
        entries: tuple[exclusions.HostEntry, ...] = (),
        broken: tuple[str, ...] = (),
    ) -> None:
        self.env = dict(env or {})
        self.real = dict(real or {})
        self.drives = dict(drives or {})
        self.attributes = dict(attributes or {})
        self.refuse = set(refuse)
        # ``wer`` is the per-user (HKCU) set; ``hklm_wer`` the machine set,
        # the same as HKCU unless given (installation plan Task 2.4).
        self.wer = dict(_ALL_EXCLUDED if wer is None else wer)
        self.hklm_wer = dict(self.wer if hklm_wer is None else hklm_wer)
        self.wer_error = wer_error
        self.backup = dict(_ALL_BACKUP if backup is None else backup)
        self.backup_error = backup_error
        self.entries = entries
        self.broken = set(broken)
        self.set_calls: list[tuple[str, int]] = []
        self.drive_calls: list[str] = []
        self.wer_hives: list[str] = []
        self.backup_reads = 0

    def _check(self, name: str) -> None:
        if name in self.broken:
            raise RuntimeError(f"{name} broke")

    def environ(self, name: str) -> str | None:
        self._check("environ")
        return self.env.get(name) or None

    def realpath(self, path: str) -> str:
        self._check("realpath")
        return self.real.get(path, path)

    def drive_type(self, root: str) -> int:
        self._check("drive_type")
        self.drive_calls.append(root)
        return self.drives.get(root.upper(), 3)

    def file_attributes(self, path: str) -> int:
        self._check("file_attributes")
        return self.attributes.get(path, _DIRECTORY)

    def set_file_attributes(self, path: str, attributes: int) -> bool:
        self._check("set_file_attributes")
        self.set_calls.append((path, attributes))
        if path in self.refuse:
            return False
        self.attributes[path] = attributes
        return True

    def wer_exclusions(self, hive: str = "HKCU") -> dict[str, int]:
        self._check("wer_exclusions")
        self.wer_hives.append(hive)
        if self.wer_error is not None:
            raise self.wer_error
        return dict(self.hklm_wer if hive == "HKLM" else self.wer)

    def backup_exclusions(self) -> dict[str, tuple[str, ...]]:
        self._check("backup_exclusions")
        self.backup_reads += 1
        if self.backup_error is not None:
            raise self.backup_error
        return dict(self.backup)

    def native_host_entries(self, key: str) -> tuple[exclusions.HostEntry, ...]:
        self._check("native_host_entries")
        return self.entries


def _codes(warnings: list[exclusions.ExclusionWarning]) -> list[str]:
    return [warning.code for warning in warnings]


# ---------------------------------------------------------------------------
# The C6 sentinel itself.
# ---------------------------------------------------------------------------


def test_the_real_layer_cannot_be_built_in_a_test() -> None:
    with pytest.raises(AssertionError, match="C6"):
        exclusions.Win32WindowsLayer()


def test_the_wer_names_and_key_are_d10s() -> None:
    assert WER_EXCLUDED_KEY == (
        r"Software\Microsoft\Windows\Windows Error Reporting\ExcludedApplications"
    )
    # Development-recordings hardening round 45 PR-HIGH-002: ``python.exe``
    # joined the dev set (the developer tools that read a recording refuse
    # without it); production's two are unchanged (installation plan C2).
    assert WER_EXCLUDED_APPLICATIONS == (
        "pythonw.exe",
        "python.exe",
        "scribe-app.exe",
        "scribe-host.exe",
    )
    assert exclusions.WER_PRODUCTION_APPLICATIONS == ("scribe-app.exe", "scribe-host.exe")
    # Clinic-smoke plan D11 (Task 1.5): the dev register script writes one
    # more, ``audacity.exe``, from its own superset; the app's own required
    # lists above stay four (dev) and two (production).
    assert exclusions.WER_REGISTERED_APPLICATIONS == (
        *WER_EXCLUDED_APPLICATIONS,
        "audacity.exe",
    )
    assert exclusions.wer_applications("dev") == WER_EXCLUDED_APPLICATIONS
    assert "audacity.exe" not in exclusions.wer_applications("production")


# ---------------------------------------------------------------------------
# check_location (D10).
# ---------------------------------------------------------------------------


def _root_at(resolved: str) -> tuple[Path, dict[str, str]]:
    root = Path("ClinikoScribe-root")
    return root, {str(root): resolved}


class TestCheckLocation:
    def test_the_usual_place_has_no_warning(self) -> None:
        root, real = _root_at(_LOCAL + r"\ClinikoScribe")
        layer = FakeLayer(env=_PROFILE_ENV, real=real)
        assert check_location(layer, root) == []
        assert layer.drive_calls == ["C:\\"]

    @pytest.mark.parametrize("variable", ["OneDrive", "OneDriveCommercial", "OneDriveConsumer"])
    def test_inside_onedrive_warns(self, variable: str) -> None:
        root, real = _root_at(r"C:\Users\pat\OneDrive - Clinic\ClinikoScribe")
        env = {**_PROFILE_ENV, variable: r"C:\Users\pat\OneDrive - Clinic"}
        warnings = check_location(FakeLayer(env=env, real=real), root)
        assert warnings == [exclusions.ExclusionWarning("location_onedrive", LOCATION_ONEDRIVE)]

    def test_onedrive_is_matched_without_case_and_through_the_resolved_path(self) -> None:
        # A junction (realpath) carries the folder into OneDrive.
        root, real = _root_at(r"C:\USERS\PAT\ONEDRIVE\Data\ClinikoScribe")
        env = {**_PROFILE_ENV, "OneDrive": r"c:\users\pat\onedrive\\"}
        assert _codes(check_location(FakeLayer(env=env, real=real), root)) == [
            "location_onedrive"
        ]

    def test_a_folder_that_only_shares_onedrives_prefix_is_not_inside_it(self) -> None:
        root, real = _root_at(r"C:\Users\pat\OneDriveBackup\ClinikoScribe")
        env = {**_PROFILE_ENV, "OneDrive": r"C:\Users\pat\OneDrive"}
        assert check_location(FakeLayer(env=env, real=real), root) == []

    @pytest.mark.parametrize(
        "resolved",
        [
            r"\\server\share\ClinikoScribe",
            r"\\?\UNC\server\share\ClinikoScribe",
            "//server/share/ClinikoScribe",
        ],
    )
    def test_a_network_path_warns(self, resolved: str) -> None:
        root, real = _root_at(resolved)
        layer = FakeLayer(env=_PROFILE_ENV, real=real)
        assert _codes(check_location(layer, root)) == ["location_network"]
        assert layer.drive_calls == []  # a \\ path needs no drive lookup

    def test_a_remote_drive_letter_warns(self) -> None:
        root, real = _root_at(r"Z:\Profile\AppData\Local\ClinikoScribe")
        layer = FakeLayer(env=_PROFILE_ENV, real=real, drives={"Z:\\": DRIVE_REMOTE})
        assert check_location(layer, root) == [
            exclusions.ExclusionWarning("location_network", LOCATION_NETWORK)
        ]
        assert layer.drive_calls == ["Z:\\"]

    def test_an_extended_length_local_path_is_local(self) -> None:
        root, real = _root_at("\\\\?\\" + _LOCAL + r"\ClinikoScribe")
        assert check_location(FakeLayer(env=_PROFILE_ENV, real=real), root) == []

    def test_the_roaming_profile_warns(self) -> None:
        root, real = _root_at(r"C:\Users\pat\AppData\Roaming\ClinikoScribe")
        env = {**_PROFILE_ENV, "APPDATA": r"C:\Users\pat\AppData\Roaming"}
        assert check_location(FakeLayer(env=env, real=real), root) == [
            exclusions.ExclusionWarning("location_roaming", LOCATION_ROAMING)
        ]

    def test_a_redirected_roaming_profile_on_a_share_warns_twice(self) -> None:
        root, real = _root_at(r"\\files\profiles\pat\Roaming\ClinikoScribe")
        env = {**_PROFILE_ENV, "APPDATA": r"\\files\profiles\pat\Roaming"}
        assert _codes(check_location(FakeLayer(env=env, real=real), root)) == [
            "location_network",
            "location_roaming",
        ]

    def test_an_unusual_but_harmless_place_is_logged_not_shown(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        logger = logging.getLogger("test-exclusions-location")
        caplog.set_level(logging.INFO, logger=logger.name)
        root, real = _root_at(r"D:\Data\ClinikoScribe")
        assert check_location(FakeLayer(env=_PROFILE_ENV, real=real), root, logger) == []
        assert [r.getMessage() for r in caplog.records if r.name == logger.name] == [
            "exclusions detail_code=location_unusual"
        ]
        # A logger that fails is not a failed check.
        broken: Any = object()
        assert check_location(FakeLayer(env=_PROFILE_ENV, real=real), root, broken) == []

    def test_empty_variables_are_ignored(self) -> None:
        root, real = _root_at(_LOCAL + r"\ClinikoScribe")
        env = {**_PROFILE_ENV, "OneDrive": "", "APPDATA": ""}
        assert check_location(FakeLayer(env=env, real=real), root) == []


# ---------------------------------------------------------------------------
# check_export_location (development-recordings plan Task 3.3; D10, C2).
# ---------------------------------------------------------------------------


def _folder_at(resolved: str) -> tuple[Path, dict[str, str]]:
    folder = Path("chosen-folder")
    return folder, {str(folder): resolved}


class TestCheckExportLocation:
    """Every destination the code positively identifies as off this
    computer or outside custody is REFUSED (a returned refusal — never a
    warning to export anyway, round 1 PR-HIGH-002); a folder on this
    computer's own fixed drive, outside both app data folders, is admitted."""

    def _check(self, resolved: str, **layer: Any) -> exclusions.ExclusionWarning | None:
        folder, real = _folder_at(resolved)
        env = {**_PROFILE_ENV, **layer.pop("env", {})}
        return exclusions.check_export_location(FakeLayer(env=env, real=real, **layer), folder)

    def test_a_folder_on_the_fixed_drive_is_admitted(self) -> None:
        assert self._check(r"C:\Users\pat\Documents") is None
        assert self._check(r"D:\Labelling") is None

    def test_onedrive_is_refused(self) -> None:
        refusal = self._check(
            r"C:\Users\pat\OneDrive\Documents", env={"OneDrive": r"C:\Users\pat\OneDrive"}
        )
        assert refusal == exclusions.ExclusionWarning(
            "location_onedrive", exclusions.EXPORT_ONEDRIVE
        )

    @pytest.mark.parametrize("resolved", [r"\\server\share\labels", r"\\?\UNC\server\share"])
    def test_a_unc_path_is_refused(self, resolved: str) -> None:
        refusal = self._check(resolved)
        assert refusal is not None and refusal.code == "location_network"
        assert refusal.line == exclusions.EXPORT_NETWORK

    def test_a_remote_drive_is_refused(self) -> None:
        refusal = self._check(r"Z:\labels", drives={"Z:\\": DRIVE_REMOTE})
        assert refusal is not None and refusal.code == "location_network"

    def test_the_roaming_profile_is_refused(self) -> None:
        refusal = self._check(
            r"C:\Users\pat\AppData\Roaming\labels",
            env={"APPDATA": r"C:\Users\pat\AppData\Roaming"},
        )
        assert refusal == exclusions.ExclusionWarning(
            "location_roaming", exclusions.EXPORT_ROAMING
        )

    @pytest.mark.parametrize(
        "drive_type", [0, 1, 2, 5, 6], ids=["unknown", "no_root", "removable", "cdrom", "ramdisk"]
    )
    def test_a_drive_that_is_not_fixed_is_refused(self, drive_type: int) -> None:
        refusal = self._check(r"E:\labels", drives={"E:\\": drive_type})
        assert refusal == exclusions.ExclusionWarning(
            "location_not_fixed", exclusions.EXPORT_NOT_FIXED
        )

    @pytest.mark.parametrize(
        "resolved",
        [_LOCAL + r"\ClinikoScribe", _LOCAL + r"\ClinikoScribe\past_sessions",
         _LOCAL + r"\CLINIKOSCRIBE-DEV\exports"],
        ids=["production", "production_child", "dev_any_case"],
    )
    def test_either_app_data_folder_is_refused(self, resolved: str) -> None:
        """Round-26 SEC-005's rule, BOTH channels, whatever this one is."""
        refusal = self._check(resolved)
        assert refusal == exclusions.ExclusionWarning(
            "location_app_folder", exclusions.EXPORT_APP_FOLDER
        )

    def test_a_sibling_of_the_app_folder_is_admitted(self) -> None:
        assert self._check(_LOCAL + r"\ClinikoScribeLabels") is None

    @pytest.mark.parametrize("broken", ["environ", "realpath", "drive_type"])
    def test_a_check_that_cannot_be_made_refuses(self, broken: str) -> None:
        refusal = self._check(r"C:\Users\pat\Documents", broken=(broken,))
        assert refusal == exclusions.ExclusionWarning(
            "location_unchecked", exclusions.EXPORT_UNCHECKED
        )


# ---------------------------------------------------------------------------
# check_wer (D10, round 2 PR-MED-006).
# ---------------------------------------------------------------------------


class TestCheckWer:
    """D10's DEV branch — a source checkout, the four per-user values —
    which is what these cases always described (installation plan Task 2.4
    made the set follow the channel; the production branch is
    ``TestCheckWerProduction``)."""

    @pytest.fixture(autouse=True)
    def _dev_channel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        use_channel(monkeypatch, "dev")

    @pytest.mark.parametrize(
        "executable",
        [
            "pythonw.exe",
            r"C:\Recording clinic software\.venv\Scripts\pythonw.exe",
            r"C:\Python314\PythonW.EXE",
            # Development-recordings hardening round 45: the console launch
            # is covered from a source checkout once python.exe is excluded.
            r"C:\Recording clinic software\.venv\Scripts\python.exe",
            r"C:\Python314\PYTHON.EXE",
            "scribe-app.exe",
            "SCRIBE-HOST.EXE",
        ],
    )
    def test_an_excluded_launch_with_all_four_values_is_clear(self, executable: str) -> None:
        assert check_wer(FakeLayer(), executable) == []

    def test_another_interpreter_name_shows_d10s_line(self) -> None:
        warnings = check_wer(FakeLayer(), r"C:\Python314\python3.14.exe")
        assert [w.line for w in warnings] == [
            "Crash reports are not excluded for this launch (python3.14.exe) — "
            "start the app with scribe-app.exe."
        ]
        assert _codes(warnings) == ["wer_uncovered_launch"]

    @pytest.mark.parametrize(
        "values",
        [
            {},
            {"pythonw.exe": 1, "scribe-app.exe": 1},
            {"pythonw.exe": 1, "python.exe": 1, "scribe-app.exe": 1, "scribe-host.exe": 0},
            {"pythonw.exe": 2, "python.exe": 1, "scribe-app.exe": 1, "scribe-host.exe": 1},
            # Round 45: a registration from before python.exe joined the set.
            {"pythonw.exe": 1, "scribe-app.exe": 1, "scribe-host.exe": 1},
        ],
    )
    def test_a_missing_or_wrong_value_warns(self, values: dict[str, int]) -> None:
        assert check_wer(FakeLayer(wer=values), "pythonw.exe") == [
            exclusions.ExclusionWarning("wer_not_excluded", wer_not_excluded_line())
        ]

    @pytest.mark.parametrize(
        ("frozen", "remedy"),
        [
            (False, "run scripts/register-native-host.py again from a normal terminal"),
            (True, "reinstall Clinic Scribe"),
        ],
    )
    def test_the_missing_exclusion_names_this_builds_remedy(
        self, monkeypatch: pytest.MonkeyPatch, frozen: bool, remedy: str
    ) -> None:
        # Installation plan Task 1.7: a packaged build has no scripts folder.
        use_frozen(monkeypatch, frozen)
        assert wer_not_excluded_line() == (
            f"Crash reports are not excluded for Clinic Scribe — {remedy}, then restart "
            "Clinic Scribe."
        )

    def test_an_unreadable_registry_says_so_and_still_checks_the_launch(self) -> None:
        warnings = check_wer(FakeLayer(wer_error=PermissionError("denied")), "py.exe")
        assert _codes(warnings) == ["wer_unchecked", "wer_uncovered_launch"]
        assert warnings[0].line == WER_UNCHECKED

    @pytest.mark.parametrize("name", ["py thon.exe", "x" * 65, "evil\nline.exe", ""])
    def test_a_name_that_is_not_plain_is_never_shown(self, name: str) -> None:
        assert uncovered_launch_line(name) == (
            "Crash reports are not excluded for this launch (this program) — "
            "start the app with scribe-app.exe."
        )

    def test_the_dev_channel_reads_only_the_per_user_values(self) -> None:
        layer = FakeLayer(hklm_wer={})
        assert check_wer(layer, "pythonw.exe") == []
        assert layer.wer_hives == ["HKCU"]


class TestCheckToolWer:
    """Development-recordings hardening round 45 PR-HIGH-002 (practitioner
    decision 2026-10-08): the developer tools that read a recording which may
    hold a real consultation run only while the RUNNING interpreter's crash
    reports are excluded — the one refusing check here, failing closed."""

    _VENV_PYTHON = r"C:\Recording clinic software\.venv\Scripts\python.exe"

    @pytest.fixture(autouse=True)
    def _dev_channel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        use_channel(monkeypatch, "dev")

    @pytest.mark.parametrize(
        "executable", [_VENV_PYTHON, r"C:\Python314\PYTHON.EXE", "pythonw.exe"]
    )
    def test_an_excluded_interpreter_runs(self, executable: str) -> None:
        layer = FakeLayer()
        assert exclusions.check_tool_wer(lambda: layer, executable) is None
        assert layer.wer_hives == ["HKCU"]

    @pytest.mark.parametrize(
        "values",
        [
            {},
            {"pythonw.exe": 1, "scribe-app.exe": 1, "scribe-host.exe": 1},  # before round 45
            {"python.exe": 0},
            {"python.exe": 2},
        ],
    )
    def test_an_interpreter_not_excluded_is_refused(self, values: dict[str, int]) -> None:
        refusal = exclusions.check_tool_wer(lambda: FakeLayer(wer=values), self._VENV_PYTHON)
        assert refusal == "wer_not_excluded"

    def test_only_the_running_interpreter_counts(self) -> None:
        # The other names being excluded never clears an interpreter whose
        # own name is not (nor one the layer does not read at all).
        everything_else = {name: 1 for name in WER_EXCLUDED_APPLICATIONS if name != "python.exe"}
        layer = FakeLayer(wer=everything_else)
        assert exclusions.check_tool_wer(lambda: layer, self._VENV_PYTHON) == "wer_not_excluded"

    @pytest.mark.parametrize("executable", [r"C:\Py\python3.14.exe", "py.exe", "evil\nname.exe"])
    def test_a_name_the_register_script_never_excludes_is_refused_unread(
        self, executable: str
    ) -> None:
        """Round 46 PR-MED-001, decided fail closed: the reader stays confined
        to the values this app writes and removes, so an exclusion added by
        hand for another image name never counts — refused before the
        registry is read, with a remedy that can work (registration cannot)."""

        def never() -> FakeLayer:
            raise AssertionError("the registry must not be read for an uncovered name")

        assert exclusions.check_tool_wer(never, executable) == "wer_uncovered_name"
        line = exclusions.tool_wer_refusal_line("wer_uncovered_name", executable)
        assert "register-native-host" not in line
        assert line.endswith(
            "start this with the developer build's .venv\\Scripts\\python.exe instead"
        )

    def test_the_uncovered_name_line(self) -> None:
        assert exclusions.tool_wer_refusal_line("wer_uncovered_name", r"C:\Py\python3.14.exe") == (
            "crash reports are checked only for the Python names the register script "
            "excludes, not python3.14.exe - start this with the developer build's "
            ".venv\\Scripts\\python.exe instead"
        )

    def test_an_unreadable_registry_refuses(self) -> None:
        layer = FakeLayer(wer_error=PermissionError("denied"))
        assert exclusions.check_tool_wer(lambda: layer, self._VENV_PYTHON) == "wer_unchecked"

    def test_a_layer_that_cannot_be_built_refuses(self) -> None:
        # The real layer in a test raises (the C6 sentinel): unresolved refuses.
        refusal = exclusions.check_tool_wer(exclusions.Win32WindowsLayer, self._VENV_PYTHON)
        assert refusal == "wer_unchecked"

    def test_any_other_failure_refuses(self) -> None:
        layer = FakeLayer(broken=("wer_exclusions",))
        assert exclusions.check_tool_wer(lambda: layer, self._VENV_PYTHON) == "wer_unchecked"

    def test_the_refusal_names_the_interpreter_and_the_fix(self) -> None:
        line = exclusions.tool_wer_refusal_line("wer_not_excluded", self._VENV_PYTHON)
        assert line == (
            "crash reports are not excluded for python.exe, so a crash could put part of a "
            "recording into a Windows crash report - run scripts/register-native-host.py "
            "again from a normal terminal, then retry"
        )
        unchecked = exclusions.tool_wer_refusal_line("wer_unchecked", self._VENV_PYTHON)
        assert unchecked == (
            "could not check whether crash reports are excluded for python.exe - "
            f"{install_layout.registration_remedy()}, then retry"
        )

    def test_the_refusal_takes_the_builds_remedy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Round 45, h-v45b: the remedy goes through install_layout (a packaged
        # build would say to reinstall, never name a script).
        use_frozen(monkeypatch, True)
        refusals: tuple[exclusions.ToolWerRefusal, ...] = ("wer_not_excluded", "wer_unchecked")
        for refusal in refusals:
            line = exclusions.tool_wer_refusal_line(refusal, self._VENV_PYTHON)
            assert line.endswith(f"- {install_layout.FROZEN_REMEDY}, then retry")
            assert "scripts/" not in line
        assert "this program" in exclusions.tool_wer_refusal_line(
            "wer_not_excluded", "evil\nname.exe"
        )


class TestCheckWerProduction:
    """Installation plan D10 / Task 2.4, the production channel (the
    installed build): its two executables, read in HKLM then HKCU — a value
    in either hive excludes that executable — and ``pythonw.exe`` is neither
    needed nor a covered launch."""

    def test_the_sets_and_hives_follow_the_channel(self) -> None:
        assert exclusions.wer_applications("production") == ("scribe-app.exe", "scribe-host.exe")
        assert exclusions.wer_applications("dev") == WER_EXCLUDED_APPLICATIONS
        assert exclusions.wer_applications() == ("scribe-app.exe", "scribe-host.exe")  # pinned
        assert exclusions.wer_hives("production") == ("HKLM", "HKCU")
        assert exclusions.wer_hives("dev") == ("HKCU",)

    @pytest.mark.parametrize(
        "executable", ["scribe-app.exe", r"C:\Program Files\X\SCRIBE-HOST.EXE"]
    )
    def test_the_two_machine_values_clear_an_installed_launch(self, executable: str) -> None:
        layer = FakeLayer(wer={}, hklm_wer={"scribe-app.exe": 1, "scribe-host.exe": 1})
        assert check_wer(layer, executable) == []
        assert layer.wer_hives == ["HKLM", "HKCU"]

    def test_a_per_user_value_is_accepted_for_either_executable(self) -> None:
        layer = FakeLayer(wer={"scribe-host.exe": 1}, hklm_wer={"scribe-app.exe": 1})
        assert check_wer(layer, "scribe-app.exe") == []

    @pytest.mark.parametrize(
        ("hkcu", "hklm"),
        [
            ({}, {}),
            ({}, {"scribe-app.exe": 1}),
            ({"scribe-app.exe": 1}, {"scribe-app.exe": 1}),
            ({"scribe-host.exe": 0}, {"scribe-app.exe": 1, "scribe-host.exe": 2}),
            # pythonw.exe alone excludes nothing the installed build runs.
            ({"pythonw.exe": 1}, {"pythonw.exe": 1}),
        ],
    )
    def test_an_executable_excluded_in_neither_hive_warns(
        self, hkcu: dict[str, int], hklm: dict[str, int]
    ) -> None:
        assert check_wer(FakeLayer(wer=hkcu, hklm_wer=hklm), "scribe-app.exe") == [
            exclusions.ExclusionWarning("wer_not_excluded", wer_not_excluded_line())
        ]

    @pytest.mark.parametrize("executable", ["pythonw.exe", "python.exe"])
    def test_a_python_launch_is_uncovered_in_production(self, executable: str) -> None:
        assert _codes(check_wer(FakeLayer(), executable)) == ["wer_uncovered_launch"]

    def test_an_unreadable_hive_says_so(self) -> None:
        warnings = check_wer(FakeLayer(wer_error=PermissionError("denied")), "scribe-app.exe")
        assert _codes(warnings) == ["wer_unchecked"]

    @pytest.mark.parametrize(
        ("unreadable", "readable", "expected"),
        [
            # Round 14 LOW-003: the readable hive answers when it covers both.
            ("HKLM", {"scribe-app.exe": 1, "scribe-host.exe": 1}, []),
            ("HKCU", {"scribe-app.exe": 1, "scribe-host.exe": 1}, []),
            # ...and "could not check" only when it leaves one uncovered.
            ("HKLM", {"scribe-app.exe": 1}, ["wer_unchecked"]),
            ("HKCU", {}, ["wer_unchecked"]),
        ],
    )
    def test_one_unreadable_hive_does_not_hide_the_other(
        self, unreadable: str, readable: dict[str, int], expected: list[str]
    ) -> None:
        class OneHiveDenied(FakeLayer):
            def wer_exclusions(self, hive: str = "HKCU") -> dict[str, int]:
                self.wer_hives.append(hive)
                if hive == unreadable:
                    raise PermissionError("denied")
                return dict(readable)

        layer = OneHiveDenied()
        assert _codes(check_wer(layer, "scribe-app.exe")) == expected
        assert layer.wer_hives == ["HKLM", "HKCU"]


class TestCheckBackupExclusions:
    """Installation plan D6 / Task 2.4: the installer's two HKLM values must
    name the live sessions and the logs; production only, warnings only."""

    def test_the_patterns_are_task_3_4s(self) -> None:
        assert install_layout.backup_exclusion_patterns() == (
            r"$UserProfile$\AppData\Local\ClinikoScribe\sessions\* /s",
            r"$UserProfile$\AppData\Local\ClinikoScribe\logs\* /s",
        )
        assert install_layout.BACKUP_VALUE_NAME == "ClinikoScribe"
        assert exclusions.BACKUP_RESTORE_KEY == r"SYSTEM\CurrentControlSet\Control\BackupRestore"
        assert BACKUP_EXCLUSION_KEYS == ("FilesNotToBackup", "FilesNotToSnapshot")

    def test_both_values_in_place_are_clear(self) -> None:
        assert check_backup_exclusions(FakeLayer()) == []

    def test_case_space_and_extra_patterns_do_not_matter(self) -> None:
        held = tuple(
            f"  {pattern.upper()} " for pattern in install_layout.backup_exclusion_patterns()
        ) + (r"C:\Other\* /s",)
        layer = FakeLayer(backup=dict.fromkeys(BACKUP_EXCLUSION_KEYS, held))
        assert check_backup_exclusions(layer) == []

    @pytest.mark.parametrize(
        "backup",
        [
            {},
            {"FilesNotToBackup": install_layout.backup_exclusion_patterns()},
            {"FilesNotToSnapshot": install_layout.backup_exclusion_patterns()},
            dict.fromkeys(
                BACKUP_EXCLUSION_KEYS, install_layout.backup_exclusion_patterns()[:1]
            ),  # sessions only
            dict.fromkeys(
                BACKUP_EXCLUSION_KEYS, install_layout.backup_exclusion_patterns()[1:]
            ),  # logs only
            dict.fromkeys(
                BACKUP_EXCLUSION_KEYS, (r"%LOCALAPPDATA%\ClinikoScribe\sessions\* /s",)
            ),
        ],
    )
    def test_a_missing_value_or_pattern_warns(self, backup: dict[str, tuple[str, ...]]) -> None:
        assert check_backup_exclusions(FakeLayer(backup=backup)) == [
            exclusions.ExclusionWarning("backup_not_excluded", BACKUP_NOT_EXCLUDED)
        ]

    def test_an_unreadable_value_says_so(self) -> None:
        assert check_backup_exclusions(FakeLayer(backup_error=PermissionError("denied"))) == [
            exclusions.ExclusionWarning("backup_unchecked", BACKUP_UNCHECKED)
        ]

    def test_the_lines_are_best_effort_wording(self) -> None:
        # C5: never "excluded from backups"; the installed build's remedy.
        assert "best-effort" in BACKUP_NOT_EXCLUDED
        assert "excluded from" not in BACKUP_NOT_EXCLUDED + BACKUP_UNCHECKED
        assert BACKUP_NOT_EXCLUDED.endswith("reinstall Clinic Scribe.")

    def test_the_dev_channel_never_reads_or_warns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        use_channel(monkeypatch, "dev")
        layer = FakeLayer(backup={}, broken=("backup_exclusions",))
        assert check_backup_exclusions(layer) == []
        assert layer.backup_reads == 0

    def test_start_up_shows_the_line_and_a_broken_read_is_only_a_warning(
        self, tmp_path: Path
    ) -> None:
        root = _real_root(tmp_path)
        logger = logging.getLogger("t-backup")
        assert startup_exclusions(
            FakeLayer(backup={}), executable="scribe-app.exe", logger=logger, root=root
        ) == (BACKUP_NOT_EXCLUDED,)
        assert startup_exclusions(
            FakeLayer(broken=("backup_exclusions",)),
            executable="scribe-app.exe",
            logger=logger,
            root=root,
        ) == (BACKUP_UNCHECKED,)

    def test_the_dev_start_up_never_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        use_channel(monkeypatch, "dev")
        root = _real_root(tmp_path)
        layer = FakeLayer(backup={})
        logger = logging.getLogger("t")
        assert startup_exclusions(layer, executable="pythonw.exe", logger=logger, root=root) == ()
        assert layer.backup_reads == 0


def test_the_checked_data_folder_follows_the_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Installation plan Task 1.2 (C8): the start-up checks look at the
    channel's own folder, read through the layer (``LOCALAPPDATA`` unset
    there falls back to the home folder, as every store does)."""
    layer = FakeLayer(env=_PROFILE_ENV)
    assert exclusions.app_data_root(layer) == Path(_LOCAL) / "ClinikoScribe"
    use_channel(monkeypatch, "dev")
    assert exclusions.app_data_root(layer) == Path(_LOCAL) / "ClinikoScribe-dev"
    assert exclusions.app_data_root(FakeLayer(env={})) == Path.home() / "ClinikoScribe-dev"
    assert exclusions.APP_FOLDER_NAME == "ClinikoScribe"


# ---------------------------------------------------------------------------
# mark_not_indexed: best effort, folders only, links never followed.
# ---------------------------------------------------------------------------


class TestMarkNotIndexed:
    def test_every_folder_is_marked_and_no_file(self, tmp_path: Path) -> None:
        root = tmp_path / "ClinikoScribe"
        (root / "sessions" / "a").mkdir(parents=True)
        (root / "audit").mkdir()
        (root / "app.lock").write_bytes(b"")
        (root / "audit" / "row.enc").write_bytes(b"x")
        layer = FakeLayer(attributes={str(root): _DIRECTORY | _HIDDEN})
        assert mark_not_indexed(layer, root) == 0
        marked = {path for path, _attributes in layer.set_calls}
        assert marked == {
            str(root),
            str(root / "sessions"),
            str(root / "sessions" / "a"),
            str(root / "audit"),
        }
        # What the folder carried is kept; DIRECTORY is not a settable bit.
        assert dict(layer.set_calls)[str(root)] == _HIDDEN | FILE_ATTRIBUTE_NOT_CONTENT_INDEXED

    def test_a_folder_already_marked_is_not_set_again_but_is_walked(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "ClinikoScribe"
        (root / "logs").mkdir(parents=True)
        layer = FakeLayer(attributes={str(root): _DIRECTORY | FILE_ATTRIBUTE_NOT_CONTENT_INDEXED})
        assert mark_not_indexed(layer, root) == 0
        assert [path for path, _ in layer.set_calls] == [str(root / "logs")]

    def test_a_refusal_is_counted_and_the_walk_goes_on(self, tmp_path: Path) -> None:
        root = tmp_path / "ClinikoScribe"
        (root / "sessions" / "inner").mkdir(parents=True)
        layer = FakeLayer(refuse=(str(root / "sessions"),))
        assert mark_not_indexed(layer, root) == 1
        assert str(root / "sessions" / "inner") in {path for path, _ in layer.set_calls}

    def test_an_unreadable_folder_is_counted_never_raised(self, tmp_path: Path) -> None:
        root = tmp_path / "ClinikoScribe"
        root.mkdir()
        assert mark_not_indexed(FakeLayer(broken=("file_attributes",)), root) == 1
        assert mark_not_indexed(FakeLayer(broken=("set_file_attributes",)), root) == 1

    def test_a_missing_root_marks_nothing(self, tmp_path: Path) -> None:
        layer = FakeLayer()
        assert mark_not_indexed(layer, tmp_path / "absent") == 0
        assert layer.set_calls == []

    @pytest.mark.skipif(sys.platform != "win32", reason="junctions exist only on Windows")
    def test_a_junction_is_never_followed_or_marked(self, tmp_path: Path) -> None:
        import _winapi

        outside = tmp_path / "outside"
        (outside / "deep").mkdir(parents=True)
        root = tmp_path / "ClinikoScribe"
        root.mkdir()
        _winapi.CreateJunction(str(outside), str(root / "link"))
        layer = FakeLayer()
        assert mark_not_indexed(layer, root) == 0
        assert [path for path, _ in layer.set_calls] == [str(root)]
        # A junctioned ROOT is not walked at all.
        linked_root = tmp_path / "linked-root"
        _winapi.CreateJunction(str(outside), str(linked_root))
        layer = FakeLayer()
        assert mark_not_indexed(layer, linked_root) == 0
        assert layer.set_calls == []


# ---------------------------------------------------------------------------
# startup_exclusions: the lines, their log codes, never a refusal.
# ---------------------------------------------------------------------------


def _real_root(tmp_path: Path) -> Path:
    root = tmp_path / "ClinikoScribe"
    root.mkdir()
    return root


class TestStartupExclusions:
    """A source checkout's start-up — the DEV channel, whose WER branch these
    cases always described (installation plan Task 2.4: the WER set follows
    the channel, and the dev channel has no backup check). The production
    start-up's backup line: ``TestCheckBackupExclusions``."""

    @pytest.fixture(autouse=True)
    def _dev_channel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        use_channel(monkeypatch, "dev")

    def test_a_clean_start_has_no_line(self, tmp_path: Path) -> None:
        root = _real_root(tmp_path)
        layer = FakeLayer(env=_PROFILE_ENV, real={str(root): _LOCAL + r"\ClinikoScribe"})
        logger = logging.getLogger("test-exclusions-clean")
        assert startup_exclusions(layer, executable="pythonw.exe", logger=logger, root=root) == ()
        assert [path for path, _ in layer.set_calls] == [str(root)]

    def test_every_warning_in_order_and_logged_by_code_only(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        logger = logging.getLogger("test-exclusions-all")
        caplog.set_level(logging.INFO, logger=logger.name)
        root = _real_root(tmp_path)
        onedrive = r"C:\Users\pat\OneDrive"
        layer = FakeLayer(
            env={**_PROFILE_ENV, "OneDrive": onedrive},
            real={str(root): onedrive + r"\ClinikoScribe"},
            refuse=(str(root),),
            wer={},
        )
        # Round 45: python.exe is in the dev set now — an interpreter name the
        # checkout does not exclude still shows the uncovered-launch line.
        lines = startup_exclusions(layer, executable="python3.14.exe", logger=logger, root=root)
        assert lines == (
            NOT_INDEXED_FAILED,
            LOCATION_ONEDRIVE,
            wer_not_excluded_line(),
            uncovered_launch_line("python3.14.exe"),
        )
        records = [record for record in caplog.records if record.name == logger.name]
        messages = [record.getMessage() for record in records]
        assert messages == [
            "exclusions detail_code=not_indexed_failed",
            "exclusions detail_code=location_onedrive",
            "exclusions detail_code=wer_not_excluded",
            "exclusions detail_code=wer_uncovered_launch",
            "exclusions count=4 state=checked",
        ]
        for record in records:  # no path, no line text (C3)
            assert str(root) not in record.getMessage()
            assert "OneDrive" not in record.getMessage()

    def test_a_layer_that_breaks_everywhere_never_refuses_start_up(self, tmp_path: Path) -> None:
        root = _real_root(tmp_path)
        layer = FakeLayer(
            broken=(
                "environ",
                "realpath",
                "drive_type",
                "file_attributes",
                "set_file_attributes",
                "wer_exclusions",
            )
        )
        lines = startup_exclusions(
            layer, executable="pythonw.exe", logger=logging.getLogger("t"), root=root
        )
        assert lines == (NOT_INDEXED_FAILED, LOCATION_UNCHECKED, WER_UNCHECKED)

    def test_the_default_root_is_localappdatas_clinikoscribe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        use_channel(monkeypatch, "production")  # the production folder's name
        root = _real_root(tmp_path)
        layer = FakeLayer(env={"LOCALAPPDATA": str(tmp_path), "USERPROFILE": str(tmp_path)})
        startup_exclusions(layer, executable="pythonw.exe", logger=logging.getLogger("t"))
        assert layer.set_calls and layer.set_calls[0][0] == str(root)

    def test_a_broken_logger_still_returns_the_lines(self, tmp_path: Path) -> None:
        root = _real_root(tmp_path)
        layer = FakeLayer(env=_PROFILE_ENV, real={str(root): _LOCAL + r"\ClinikoScribe"})
        broken: Any = object()  # log_event's logger.info raises AttributeError
        assert startup_exclusions(
            layer, executable="python3.14.exe", logger=broken, root=root
        ) == (uncovered_launch_line("python3.14.exe"),)


# ---------------------------------------------------------------------------
# The exception hooks (C3): the type name only, never raising.
# ---------------------------------------------------------------------------

_SECRET = "Jane Citizen left knee"


@pytest.fixture
def hook_logger(caplog: pytest.LogCaptureFixture) -> Iterator[logging.Logger]:
    """The three hooks installed for one test, then restored."""
    logger = logging.getLogger("test-exclusions-hooks")
    caplog.set_level(logging.INFO, logger=logger.name)
    restore = install_exception_hooks(logger)
    try:
        yield logger
    finally:
        restore()


def _hook_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "test-exclusions-hooks"]


def _assert_only(caplog: pytest.LogCaptureFixture, expected: list[str]) -> None:
    records = _hook_records(caplog)
    assert [r.getMessage() for r in records] == expected
    for record in records:
        assert record.exc_info is None and record.exc_text is None
        assert record.stack_info is None
        assert _SECRET not in record.getMessage()


class TestExceptionHooks:
    def test_the_main_hook_logs_the_type_name_only(
        self, hook_logger: logging.Logger, caplog: pytest.LogCaptureFixture
    ) -> None:
        try:
            raise ValueError(_SECRET)
        except ValueError as exc:
            sys.excepthook(type(exc), exc, exc.__traceback__)
        _assert_only(caplog, ["uncaught_exception detail_code=main error_code=ValueError"])

    def test_a_thread_hook_logs_the_type_name_only(
        self, hook_logger: logging.Logger, caplog: pytest.LogCaptureFixture
    ) -> None:
        def boom() -> None:
            raise RuntimeError(_SECRET)

        thread = threading.Thread(target=boom)
        thread.start()
        thread.join()
        _assert_only(caplog, ["uncaught_exception detail_code=thread error_code=RuntimeError"])

    def test_a_threads_system_exit_is_silent_as_pythons_own(
        self, hook_logger: logging.Logger, caplog: pytest.LogCaptureFixture
    ) -> None:
        def leave() -> None:
            raise SystemExit(3)

        thread = threading.Thread(target=leave)
        thread.start()
        thread.join()
        _assert_only(caplog, [])

    def test_an_unraisable_exception_logs_the_type_name_only(
        self, hook_logger: logging.Logger, caplog: pytest.LogCaptureFixture
    ) -> None:
        class Leaky:
            def __del__(self) -> None:
                raise KeyError(_SECRET)

        Leaky()
        gc.collect()
        _assert_only(caplog, ["uncaught_exception detail_code=unraisable error_code=KeyError"])

    def test_the_main_hook_drops_the_interpreters_last_exception(
        self, hook_logger: logging.Logger, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Round 21 LOW-001: ``PyErr_Print`` (a Qt slot's exception) sets
        ``sys.last_*`` before calling the hook; the hook drops them, so the
        exception's frames — and their locals — are not kept alive."""
        names = ("last_exc", "last_type", "last_value", "last_traceback")
        try:
            raise ValueError(_SECRET)
        except ValueError as exc:
            caught = exc
        for name, value in zip(
            names, (caught, ValueError, caught, caught.__traceback__), strict=True
        ):
            setattr(sys, name, value)
        try:
            sys.excepthook(ValueError, caught, caught.__traceback__)
            assert [name for name in names if hasattr(sys, name)] == []
        finally:
            for name in names:
                if hasattr(sys, name):
                    delattr(sys, name)
        _assert_only(caplog, ["uncaught_exception detail_code=main error_code=ValueError"])

    def test_a_console_launch_shows_the_one_line_on_stderr_and_nothing_else(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Round 21 LOW-003: a console launch (``python.exe``, stderr
        present) still SHOWS something — the hook's type-name line reaches
        ``setup_logging``'s stderr handler — and never the message or a
        traceback (the default hook, which printed both, is not called)."""
        from scribe_desktop.logging_setup import setup_logging

        logger = setup_logging("test-exclusions-console", log_dir=tmp_path)
        restore = install_exception_hooks(logger)
        try:
            try:
                raise ValueError(_SECRET)
            except ValueError as exc:
                sys.excepthook(type(exc), exc, exc.__traceback__)
        finally:
            restore()
            for handler in logger.handlers:
                handler.close()
            logger.handlers.clear()
        err = capsys.readouterr().err
        assert "uncaught_exception detail_code=main error_code=ValueError" in err
        assert _SECRET not in err and "Traceback" not in err
        written = (tmp_path / "test-exclusions-console.log").read_text(encoding="utf-8")
        assert "error_code=ValueError" in written and _SECRET not in written

    @pytest.mark.parametrize("where", ["main", "thread", "unraisable"])
    def test_a_failing_log_sink_never_prints_the_handled_exception(
        self, tmp_path: Path, capfd: pytest.CaptureFixture[str], where: str
    ) -> None:
        """Round 23 PR-MED-020: the hook's log line fails to write (the real
        file handler's rollover raises) WHILE an exception carrying clinical
        text is being handled — Python runs the thread hook inside
        ``except:``; the main hook and an unraisable ``__del__`` are driven
        inside one here. Only the fixed failure line and the hook's own type
        line reach stderr; nothing reaches stdout."""
        from scribe_desktop.logging_setup import handler_error_count
        from test_logging_setup import _close, _failing_logger

        logger = _failing_logger(tmp_path, f"test-failing-hook-{where}")
        restore = install_exception_hooks(logger)
        before = handler_error_count()
        try:
            if where == "main":
                try:
                    raise ValueError(_SECRET)
                except ValueError as exc:
                    sys.excepthook(type(exc), exc, exc.__traceback__)
            elif where == "thread":

                def boom() -> None:
                    raise ValueError(_SECRET)

                thread = threading.Thread(target=boom)
                thread.start()
                thread.join()
            else:

                class Leaky:
                    def __del__(self) -> None:
                        raise KeyError(_SECRET)

                leaky: Any = Leaky()
                try:
                    raise ValueError(_SECRET)
                except ValueError:
                    del leaky
        finally:
            restore()
            _close(logger)
        assert handler_error_count() > before  # the failure path really ran
        out, err = capfd.readouterr()
        assert out == ""
        assert "--- Logging error (OSError) ---" in err
        assert f"uncaught_exception detail_code={where}" in err
        for leak in (_SECRET, "Traceback", "the disk is full", "Message:"):
            assert leak not in err, leak

    def test_the_replaced_hooks_are_never_called_and_are_restored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []
        monkeypatch.setattr(sys, "excepthook", lambda *args: calls.append("main"))
        monkeypatch.setattr(threading, "excepthook", lambda args: calls.append("thread"))
        monkeypatch.setattr(sys, "unraisablehook", lambda args: calls.append("unraisable"))
        before = (sys.excepthook, threading.excepthook, sys.unraisablehook)
        restore = install_exception_hooks(logging.getLogger("test-exclusions-quiet"))
        args = SimpleNamespace(exc_type=OSError, exc_value=OSError(_SECRET))
        sys.excepthook(OSError, OSError(_SECRET), None)
        threading.excepthook(args)  # type: ignore[arg-type]
        sys.unraisablehook(args)  # type: ignore[arg-type]
        assert calls == []
        restore()
        assert (sys.excepthook, threading.excepthook, sys.unraisablehook) == before

    def test_restore_leaves_a_hook_installed_after_ours(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "excepthook", sys.excepthook)  # undone at teardown
        restore = install_exception_hooks(logging.getLogger("test-exclusions-later"))

        def later(*args: object) -> None:
            pass

        sys.excepthook = later
        restore()
        assert sys.excepthook is later
        assert not isinstance(threading.excepthook, ExceptionHook)

    def test_a_hook_never_raises(self) -> None:
        broken: Any = object()  # logger.info raises AttributeError
        args = SimpleNamespace(exc_type=ValueError, exc_value=ValueError(_SECRET))
        ExceptionHook(broken, "main", print)(ValueError, ValueError(_SECRET), None)
        ExceptionHook(broken, "thread", print)(args)
        ExceptionHook(broken, "unraisable", print)(args)
        ExceptionHook(logging.getLogger("t"), "thread", print)()  # no argument at all

    def test_remove_unwinds_every_installed_hook(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "excepthook", sys.excepthook)
        monkeypatch.setattr(threading, "excepthook", threading.excepthook)
        monkeypatch.setattr(sys, "unraisablehook", sys.unraisablehook)
        before = (sys.excepthook, threading.excepthook, sys.unraisablehook)
        install_exception_hooks(logging.getLogger("t"))
        install_exception_hooks(logging.getLogger("t"))
        assert remove_exception_hooks() is True
        assert (sys.excepthook, threading.excepthook, sys.unraisablehook) == before
        assert remove_exception_hooks() is False

    def test_only_a_plain_type_name_is_logged(self) -> None:
        assert exception_type_name(ValueError) == "ValueError"
        assert exception_type_name(type("bad name!", (Exception,), {})) == "unknown"
        assert exception_type_name(type("x" * 65, (Exception,), {})) == "unknown"
        assert exception_type_name(None) == "unknown"


# ---------------------------------------------------------------------------
# The warning lines on screen (Status tab and Past sessions).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


_LINES = (LOCATION_ONEDRIVE, uncovered_launch_line("python.exe"))


class TestOnScreen:
    def test_the_status_panel_shows_the_lines_and_hides_when_none(self, qapp: Any) -> None:
        from scribe_desktop.ui.main_window import StatusPanel

        panel = StatusPanel(exclusion_warnings=_LINES)
        assert panel.exclusions_label.text() == "\n".join(_LINES)
        assert not panel.exclusions_label.isHidden()
        assert StatusPanel().exclusions_label.isHidden()

    def test_the_past_sessions_status_line_always_carries_them(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui import past_sessions_view as view
        from scribe_desktop.ui.past_sessions import PastSessionsScreen

        screen = PastSessionsScreen(None, config_root=tmp_path, exclusion_warnings=_LINES)
        assert screen.status_lines() == [view.STORE_UNAVAILABLE, *_LINES]
        screen.refresh()  # a repaint derives them again
        assert screen.status_label.text().splitlines()[-2:] == list(_LINES)
        assert not screen.status_label.isHidden()

    def test_the_window_hands_both_the_same_lines(self, qapp: Any, tmp_path: Path) -> None:
        from test_ui_screens import _main_window

        window = _main_window(tmp_path, exclusion_warnings=_LINES)
        try:
            assert window.status_panel.exclusions_label.text() == "\n".join(_LINES)
            assert window.past_sessions_screen.status_lines()[-2:] == list(_LINES)
        finally:
            window.deleteLater()
        (tmp_path / "plain").mkdir()
        plain = _main_window(tmp_path / "plain")
        try:
            assert plain.status_panel.exclusions_label.isHidden()
            assert not set(_LINES) & set(plain.past_sessions_screen.status_lines())
        finally:
            plain.deleteLater()


# ---------------------------------------------------------------------------
# app.main: the hooks first, the checks before the window.
# ---------------------------------------------------------------------------


class _StopMain(Exception):
    pass


def test_main_installs_the_hooks_first_and_checks_before_the_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6.QtWidgets import QApplication

    from scribe_desktop import app as app_module

    events: list[Any] = []
    logger = logging.getLogger("test-exclusions-main")

    class FakeAudit:
        def __init__(self, **kwargs: Any) -> None:
            pass

        def prune(self) -> int:
            return 0

        def record_deletion(self, *args: Any, **kwargs: Any) -> bool:
            return True

        def record_past_session(self, *args: Any, **kwargs: Any) -> bool:
            return True

        # Development-recordings Task 1.4 (review round 8 LOW-004).
        def record_recording_kept(self, *args: Any, **kwargs: Any) -> bool:
            return True

        def keeps_rows_of(self, *args: Any) -> bool:  # review round 13 LOW-005
            return True

        def record_recording_deleted(self, *args: Any, **kwargs: Any) -> bool:
            return True

        def record_recording_exported(self, *args: Any, **kwargs: Any) -> bool:
            return True

    class FakePastSessions:
        def __init__(self, **kwargs: Any) -> None:
            pass

        def recover_exports(self) -> Any:  # development-recordings Task 3.3
            return exclusions_past_sessions.ExportRecovery()

        def clean_staging(self) -> int:
            return 0

        def remove_pending_entry(self, session_id: str) -> bool:
            return True

        def reconcile_pending(self, sessions_root: Path) -> list[str]:
            return []

        def entry_label(self, session_id: str) -> Any:  # review round 15 PR-MED-001
            return None

        # Development-recordings Task 2.2: the start-up repair and the tidy.
        def kept_entries(self) -> list[Any]:
            return []

        def deleted_recordings(self) -> list[Any]:
            return []

        def tidy_dead_recordings(self, *, cleared: frozenset[str] | None = None) -> int:
            return 0

    class FakeController:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            events.append(("controller",))

        def custody_protected_ids(self) -> frozenset[str]:
            return frozenset()

        def set_clinic_user_resolver(self, resolver: Any) -> None:
            pass

    class FakeWindowsLayer:
        def __init__(self) -> None:
            events.append(("layer",))

    class FakeWarmup:
        """Installation plan round 35 MED-001: started after the guard,
        before anything else; its readiness reaches the window."""

        def __init__(self, **kwargs: Any) -> None:
            assert kwargs == {"logger": logger}
            warmups.append(self)

        def start(self) -> None:
            events.append(("warmup",))

        def is_finished(self) -> bool:
            return False

        def holds_start(self) -> bool:
            return True

    warmups: list[FakeWarmup] = []

    class FakeWindow:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            # Installation plan Task 2.3: the same layer reaches the window.
            layer = type(kwargs["windows_layer"]).__name__
            events.append(("window", kwargs["exclusion_warnings"], layer))
            assert kwargs["live_ready"] == warmups[0].is_finished
            assert kwargs["start_hold"] == warmups[0].holds_start  # round 36 MED-001

        def clinic_user_id(self, clinic_id: str) -> str | None:
            return None

        def reconstruct_reminders(self) -> None:
            raise _StopMain()

    def checks(layer: Any, *, executable: str, logger: logging.Logger) -> tuple[str, ...]:
        events.append(("checks", type(layer).__name__, executable, logger))
        return _LINES

    for name, value in {
        "setup_logging": lambda name: logger,
        "install_exception_hooks": lambda given: events.append(("hooks", given)),
        "apply_offline_env": lambda: events.append(("offline",)),
        "assert_offline_env": lambda: None,
        "QApplication": lambda argv: QApplication.instance() or QApplication(argv),
        "acquire_instance_exclusion": lambda name=None, lock_path=None: (
            app_module.InstanceExclusion("acquired")
        ),
        "SoundDeviceBackend": lambda: object(),
        "AuditLog": FakeAudit,
        "PastSessionStore": FakePastSessions,
        "SessionController": FakeController,
        "default_sessions_root": lambda: tmp_path / "sessions",
        "sweep_sessions": lambda *args, **kwargs: [],
        "Win32WindowsLayer": FakeWindowsLayer,
        "startup_exclusions": checks,
        "MainWindow": FakeWindow,
        "ImportWarmup": FakeWarmup,
    }.items():
        monkeypatch.setattr(app_module, name, value)
    with pytest.raises(_StopMain):
        app_module.main()
    assert events == [
        ("hooks", logger),
        ("offline",),
        ("warmup",),
        ("controller",),
        ("layer",),
        ("checks", "FakeWindowsLayer", sys.executable, logger),
        ("window", _LINES, "FakeWindowsLayer"),
    ]
