"""Installation plan Task 3.4: the text pins of ``packaging/scribe.iss``.

The installer script is Inno Setup's language, so it is checked as text:
its keys, flags and wording against the app's own constants (the install
folder, the Chrome link, the crash-report set, the backup patterns), and the
constraints it must keep — per machine, nothing per user (C3), never
launching the app (D8), no ``{localappdata}``/``%LOCALAPPDATA%`` form in the
exclusions (Task 0.3), uninstall keeping the data (C4). Whether it COMPILES
and installs is the practitioner's step (ISCC, then Phase P)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scribe_desktop import exclusions, identity, install_layout

REPO = Path(__file__).resolve().parents[2]
ISS = REPO / "packaging" / "scribe.iss"
TEXT = ISS.read_text(encoding="utf-8")


def _sections() -> dict[str, list[str]]:
    """The non-comment lines of every ``[Section]`` (Inno's ``;`` comments)."""
    sections: dict[str, list[str]] = {}
    current = None
    for raw in TEXT.splitlines():
        line = raw.strip()
        header = re.fullmatch(r"\[(\w+)\]", line)
        if header:
            current = header.group(1)
            sections.setdefault(current, [])
            continue
        if current is not None and line and not line.startswith(";"):
            sections[current].append(line)
    return sections


def _section(name: str) -> list[str]:
    return _sections().get(name, [])


_DEFINES = dict(re.findall(r'^#define (\w+) "([^"]*)"$', TEXT, re.MULTILINE))


def _expand(value: str) -> str:
    """``{#Name}`` replaced by the script's own ``#define`` (ISPP's inline form)."""
    return re.sub(r"\{#(\w+)\}", lambda m: _DEFINES[m.group(1)], value)


def _entries() -> list[dict[str, str]]:
    """Every entry of every entry section (all but [Setup] and [Code])."""
    return [
        _entry(line)
        for name, lines in _sections().items()
        if name not in ("Setup", "Code")
        for line in lines
        if not line.startswith("#")
    ]


def _setup() -> dict[str, str]:
    return dict(line.split("=", 1) for line in _section("Setup"))


def _entry(line: str) -> dict[str, str]:
    """``Key: value; Key: "value"`` → a dict (quotes removed)."""
    fields: dict[str, str] = {}
    for match in re.finditer(r'(\w+):\s*("(?:[^"]|"")*"|[^;]*)', line):
        value = match.group(2).strip()
        if value.startswith('"'):
            value = value[1:-1].replace('""', '"')
        fields[match.group(1)] = value
    return fields


def _registry() -> list[dict[str, str]]:
    return [_entry(line) for line in _section("Registry")]


def _body(header: str) -> str:
    """One ``[Code]`` routine, from its header (``procedure X`` /
    ``function X``) to its closing ``end;`` at the start of a line."""
    return _code().split(f"\n{header}", 1)[1].split("\nend;", 1)[0]


def _code() -> str:
    """Everything after the ``[Code]`` header LINE (never a mention in a comment)."""
    return re.split(r"^\[Code\]$", TEXT, maxsplit=1, flags=re.MULTILINE)[1]


def _com_objects() -> list[str]:
    """Every COM object ``[Code]`` creates or gets (by ProgID)."""
    return re.findall(r"\b(?:CreateOleObject|GetActiveOleObject)\('([^']*)'\)", _code())


# A WMI call that changes anything — starting a process included — rather
# than reading (round 22).
_WMI_ACTIONS = re.compile(
    r"\.(?:Get|Create|ExecMethod_?|SpawnInstance_?|Put_?|Delete_?)\s*\(", re.IGNORECASE
)


class TestSetup:
    def test_per_machine_admin_install_with_no_setup_log(self) -> None:
        setup = _setup()
        assert setup["PrivilegesRequired"] == "admin"
        assert "PrivilegesRequiredOverridesAllowed" not in setup
        assert setup["SetupLogging"] == "no"
        assert setup["ArchitecturesInstallIn64BitMode"] == "x64compatible"

    def test_the_app_id_is_fixed(self) -> None:
        # In-place upgrade (Task 0.3) needs the SAME AppId on every build.
        assert _setup()["AppId"] == "{{8F3A6C2E-4D1B-4B7A-9E35-6C0D2F81A947}"
        assert "{8F3A6C2E-4D1B-4B7A-9E35-6C0D2F81A947}_is1" in TEXT

    def test_the_install_folder_is_d_i1s_and_cannot_be_changed(self) -> None:
        setup = _setup()
        assert setup["DefaultDirName"] == r"{commonpf64}\ClinikoScribe"
        assert setup["DisableDirPage"] == "yes"
        [root] = install_layout.INSTALL_ROOTS
        assert f'#define InstallRoot "{root}"' in TEXT
        assert "CompareText(ExpandConstant('{app}'), '{#InstallRoot}') <> 0" in _code()

    def test_the_version_and_inputs_come_from_the_build(self) -> None:
        for name in ("AppVersion", "DistDir", "ModelPackDir", "ModelsFiles", "ModelsCode"):
            assert f"#ifndef {name}\n  #error" in TEXT
        assert _setup()["AppVersion"] == "{#AppVersion}"
        assert "#include ModelsFiles" in _section("Files")
        assert "#include ModelsCode" in _code()

    def test_nothing_per_user_is_written_c3(self) -> None:
        for forbidden in ("HKCU", "HKA", "{userappdata}", "{localappdata}", "{userdocs}",
                          "%LOCALAPPDATA%", "{userdesktop}", "{userprograms}"):
            assert forbidden not in TEXT, forbidden
        assert all(entry["Root"] == "HKLM64" for entry in _registry())


class TestNoNetworkAndNoDefenderChange:
    """Round 22: C1 (the installer makes no network connection) and C10 (no
    Defender exclusion or weakening anywhere in the release path), pinned on
    the surfaces that could do either."""

    def test_the_installer_reaches_no_network(self) -> None:
        for forbidden in ("DownloadTemporaryFile", "CreateDownloadPage", "://"):
            assert forbidden not in TEXT, forbidden
        # The only COM object is the local WMI locator, on this computer ('.').
        assert _com_objects() == ["WbemScripting.SWbemLocator"]
        assert "ConnectServer('.', 'root\\CIMV2')" in _code()

    def test_no_release_file_touches_defender_settings(self) -> None:
        files = (
            ISS,
            REPO / "scripts" / "build-release.py",
            REPO / ".github" / "workflows" / "release.yml",
        )
        forbidden = re.compile(
            r"Add-MpPreference|Set-MpPreference|Exclusion(?:Path|Process|Extension)|"
            r"DisableRealtimeMonitoring|Windows Defender\\Exclusions",
            re.IGNORECASE,
        )
        for path in files:
            assert not forbidden.search(path.read_text(encoding="utf-8")), path.name
        assert forbidden.search("Add-MpPreference -ExclusionPath C:\\x")


class TestNeverLaunchesTheApp:
    def test_nothing_launches_a_program(self) -> None:
        """D8: Inno's runasoriginaluser cannot guarantee an unelevated launch,
        so no surface that starts a program exists — no [Run] or [UninstallRun]
        section, no entry flagged to run after install, and no [Code] call that
        starts a process. (``ssPostInstall`` is an install STEP, not a launch.)"""
        sections = {name.lower() for name in _sections()}
        assert "run" not in sections and "uninstallrun" not in sections
        for entry in _entries():
            flags = entry.get("Flags", "").lower().split()
            assert "postinstall" not in flags and "runasoriginaluser" not in flags, entry
        launches = re.compile(
            r"\b(?:Exec|ShellExec|ExecAsOriginalUser|ShellExecAsOriginalUser|"
            r"ExecAndCaptureOutput|ExecAndLogOutput)\s*\(",
            re.IGNORECASE,
        )
        assert not launches.search(_code())
        # Round 22: WMI can start a process too (Win32_Process.Create). The
        # one COM object is the WMI locator, and its one use is a SELECT.
        assert _com_objects() == ["WbemScripting.SWbemLocator"]
        assert not _WMI_ACTIONS.search(_code())
        [query] = re.findall(r"ExecQuery\('([^']*)", _code())
        assert query.startswith("SELECT ")

    def test_the_wmi_check_sees_a_wmi_launch(self) -> None:
        """The WMI half above is not vacuous."""
        assert _WMI_ACTIONS.search("Service.Get('Win32_Process').Create('scribe-app.exe', ...)")
        assert _WMI_ACTIONS.search("Proc.ExecMethod_('Create', Params)")
        assert not _WMI_ACTIONS.search("Found := Service.ExecQuery('SELECT ProcessId')")

    def test_the_launch_check_sees_a_launch(self) -> None:
        """The check above is not vacuous: each launching form is caught."""
        launches = re.compile(r"\b(?:Exec|ShellExec)\s*\(", re.IGNORECASE)
        assert launches.search("  Exec(ExpandConstant('{app}\\scribe-app.exe'), '', '',")
        assert not launches.search("Found := Service.ExecQuery('SELECT ProcessId')")
        assert "postinstall" in _entry(
            r'Filename: "{app}\scribe-app.exe"; Flags: nowait postinstall'
        )["Flags"].split()

    def test_the_finish_page_says_what_to_do_in_chrome(self) -> None:
        code = _code()
        assert "remove any older Clinic Scribe Companion, choose Load unpacked" in code
        assert "ExpandConstant('{app}\\extension')" in code
        assert "then fully restart Chrome" in code
        assert "reload the Clinic Scribe Companion extension, then fully restart Chrome" in code
        assert code.count("Open Clinic Scribe from the Start menu.") == 2

    def test_the_finish_label_is_resized_after_its_last_change(self) -> None:
        """Round 40 LOW-001: the Finish page showed only the first two
        paragraphs — the label kept the height Inno gave its own text. It is
        re-sized once, after EVERY caption change (the appended warnings
        included), so nothing the script says is cut off."""
        finish = _body("procedure CurPageChanged")
        resize = "WizardForm.AdjustLabelHeight(WizardForm.FinishedLabel);"
        assert finish.count(resize) == 1
        last_change = finish.rindex("WizardForm.FinishedLabel.Caption :=")
        assert finish.index(resize) > last_change
        # Nothing after it changes the text again (only the routine's end).
        assert finish.split(resize, 1)[1].strip() == ""

    def test_a_start_menu_shortcut_opens_the_app(self) -> None:
        [icon] = [_entry(line) for line in _section("Icons")]
        assert icon["Filename"] == r"{app}\scribe-app.exe"


class TestTheRegistry:
    def test_the_chrome_link_is_the_production_host_in_hklm(self) -> None:
        [link] = [e for e in _registry() if "NativeMessagingHosts" in e["Subkey"]]
        expected = identity.registry_key("production")
        assert link["Subkey"].replace("{#HostName}", identity.HOST_NAME).lower() == (
            expected.lower()
        )
        assert f'#define HostName "{identity.HOST_NAME}"' in TEXT
        assert link["ValueData"] == r"{app}\{#HostName}.json"
        assert link["ValueName"] == ""
        assert link["Flags"] == "uninsdeletekey"

    def test_the_crash_report_set_is_the_production_set(self) -> None:
        wer = [e for e in _registry() if "Windows Error Reporting" in e["Subkey"]]
        assert sorted(e["ValueName"] for e in wer) == sorted(
            exclusions.WER_PRODUCTION_APPLICATIONS
        )
        for entry in wer:
            assert entry["Subkey"].lower() == exclusions.WER_EXCLUDED_KEY.lower()
            assert (entry["ValueType"], entry["ValueData"]) == ("dword", "1")
            assert entry["Flags"] == "uninsdeletevalue"

    @pytest.mark.parametrize("key", ["FilesNotToBackup", "FilesNotToSnapshot"])
    def test_the_backup_and_snapshot_values_are_task_0_3s_form(self, key: str) -> None:
        [entry] = [e for e in _registry() if e["Subkey"].endswith(key)]
        assert entry["Subkey"] == rf"SYSTEM\CurrentControlSet\Control\BackupRestore\{key}"
        assert entry["ValueName"] == install_layout.BACKUP_VALUE_NAME
        assert entry["ValueType"] == "multisz"
        assert entry["ValueData"] == "{break}".join(install_layout.backup_exclusion_patterns())
        assert entry["Flags"] == "uninsdeletevalue"
        assert "{localappdata}" not in entry["ValueData"]
        assert "%LOCALAPPDATA%" not in entry["ValueData"].upper()

    def test_the_clinic_only_policy_is_opt_in_and_only_ours(self) -> None:
        # The entry names the key through the script's defines: match on the
        # EXPANDED key, the one Inno writes.
        [policy] = [
            e for e in _registry() if _expand(e["Subkey"]) == r"SOFTWARE\Policies\Google\Chrome"
        ]
        assert _expand(policy["ValueName"]) == "NativeMessagingUserLevelHosts"
        assert policy["Tasks"] == "clinicpolicy"
        assert policy["Check"] == "PolicyIsOurs"
        assert policy["Flags"] == "uninsdeletevalue"
        assert (policy["ValueType"], policy["ValueData"]) == ("dword", "0")
        [task] = [_entry(line) for line in _section("Tasks")]
        assert task["Name"] == "clinicpolicy"
        assert task["Flags"] == "unchecked"  # off by default (D8)
        assert "block every per-user Chrome add-on that talks to a program" in task["Description"]
        assert '"managed by your organization"' in task["Description"]

    def test_unticking_removes_only_a_policy_this_installer_set(self) -> None:
        code = _code()
        assert "GetPreviousData('ClinicOnlyPolicy', '0') = '1'" in code
        assert "RegDeleteValue(HKLM64, '{#PolicyKey}', '{#PolicyValue}')" in code
        assert "PolicyForeign := RegValueExists(HKLM64, '{#PolicyKey}', '{#PolicyValue}')" in code

    def test_a_removal_that_did_not_take_is_said_and_kept_ours(self) -> None:
        """Round 20 (PR-HIGH-003's sibling): the untick's removal is checked;
        a value that stays is said on the Finish page and stays recorded as
        this installer's, so the next run removes it. HKLM only (C3)."""
        step = _body("procedure CurStepChanged")
        install = step.split("if CurStep <> ssPostInstall then", 1)[0]
        assert "if CurStep = ssInstall then" in install
        assert "RegDeleteValue(HKLM64, '{#PolicyKey}', '{#PolicyValue}');" in install
        assert "PolicyLeft := RegValueExists(HKLM64, '{#PolicyKey}', '{#PolicyValue}');" in install
        previous = _body("procedure RegisterPreviousData")
        assert "or PolicyLeft then" in previous
        finish = _body("procedure CurPageChanged")
        assert "if PolicyLeft then" in finish
        assert "The clinic-only Chrome setting could not be removed." in finish

    def test_a_ticked_box_over_someone_elses_value_is_said(self) -> None:
        """Round 22: ticked, but the value is someone else's, so nothing is
        written (``Check: PolicyIsOurs``) — the Finish page says so instead of
        a silent "installed"."""
        [policy] = [e for e in _registry() if e.get("ValueName") == "{#PolicyValue}"]
        assert policy["Check"] == "PolicyIsOurs" and policy["Tasks"] == "clinicpolicy"
        finish = _body("procedure CurPageChanged")
        assert "if WizardIsTaskSelected('clinicpolicy') and PolicyForeign then" in finish
        assert "was already set on this computer by something else" in finish


class TestTheModels:
    def test_every_model_is_checked_before_anything_is_copied(self) -> None:
        code = _code()
        assert "GetSHA256OfFile" in code
        prepare = code.split("function PrepareToInstall", 1)[1].split("\nend;", 1)[0]
        # the installed set first (an unchanged upgrade needs no pack)...
        assert "FirstModelMismatch(ExpandConstant('{app}\\models\\'))" in prepare
        # ...then the pack beside setup.exe, named by the build
        assert "ExpandConstant('{src}\\{#ModelPackDir}\\')" in prepare
        assert "The model file ' + Mismatch + ' in the model pack is missing or damaged." in prepare
        assert "Nothing was changed." in prepare

    def test_the_old_model_set_is_replaced_whole_and_removed_on_uninstall(self) -> None:
        [delete] = [
            e for e in map(_entry, _section("InstallDelete")) if e["Name"] == r"{app}\models"
        ]
        assert delete == {
            "Type": "filesandordirs",
            "Name": r"{app}\models",
            "Check": "ModelsNeedCopy",
        }
        [uninstall] = [_entry(line) for line in _section("UninstallDelete")]
        assert uninstall == {"Type": "filesandordirs", "Name": r"{app}\models"}

    def test_an_upgrade_replaces_the_program_whole(self) -> None:
        """Round 18 MED-001: the installed tree is the audited bundle — an
        upgrade or a rollback never keeps a previous build's program files.
        Unconditional (no Check): the running-process check has already
        refused while anything could hold them."""
        deletes = [_entry(line) for line in _section("InstallDelete")]
        program = [e for e in deletes if "Check" not in e]
        assert program == [
            {"Type": "filesandordirs", "Name": r"{app}\_internal"},
            {"Type": "filesandordirs", "Name": r"{app}\extension"},
        ]
        # Every other deletion is the models' own, conditional rule.
        assert [e["Name"] for e in deletes if "Check" in e] == [r"{app}\models"]

    def test_every_copy_is_checked_again(self) -> None:
        """Round 20 PR-HIGH-003: after the copy, EVERY model is checked (never
        only the first), each bad one is removed with its removal checked, and
        any failure marks the install not complete."""
        step = _body("procedure CurStepChanged")
        post = step.split("if CurStep <> ssPostInstall then", 1)[1]
        assert "Damaged := RemoveDamagedModels(ExpandConstant('{app}\\models\\'));" in post
        assert "ModelsIncomplete := True;" in post
        assert "These model files did not copy correctly:" in post
        assert "Clinic Scribe is NOT completely installed." in post
        assert "FirstModelMismatch" not in post
        remove = _body("function RemoveDamagedModels")
        assert "Exit;" not in remove  # the loop never stops at the first bad file
        assert "for I := 0 to GetArrayLength(ModelPaths) - 1 do" in remove
        assert "if not ModelFileMatches(Folder + ModelPaths[I], ModelHashes[I]) then" in remove
        assert "if not DeleteFile(Folder + ModelPaths[I]) then" in remove
        assert "(damaged, and could not be removed)" in remove

    def test_a_failed_copy_is_never_called_installed(self) -> None:
        finish = _body("procedure CurPageChanged")
        incomplete = finish.index("if ModelsIncomplete then")
        assert finish.index("else if IsUpgrade then") > incomplete
        assert "'Clinic Scribe is NOT completely installed.'" in finish
        assert "Run Setup again with the model pack beside it" in finish

    def test_an_incomplete_install_never_exits_with_success(self) -> None:
        """Round 27 PR-MED-019: a damaged model (or a policy that could not be
        removed) makes Setup's exit code non-zero, past Inno's own 0-8."""
        exit_code = _body("function GetCustomSetupExitCode(): Integer;")
        assert "Result := 0;" in exit_code
        assert "if ModelsIncomplete then\n    Result := 9" in exit_code
        assert "else if PolicyLeft then\n    Result := 10;" in exit_code

    def test_the_checks_share_one_file_test(self) -> None:
        first = _body("function FirstModelMismatch")
        assert "ModelFileMatches(Folder + ModelPaths[I], ModelHashes[I])" in first
        matches = _body("function ModelFileMatches")
        assert "GetSHA256OfFile(Path)" in matches and "FileExists(Path)" in matches


class TestRunningProgramsAndUninstall:
    def test_the_three_programs_are_checked_at_start_prepare_and_uninstall(self) -> None:
        code = _code()
        for exe in ("scribe-app.exe", "scribe-host.exe", "chrome.exe"):
            assert f"ProcessRunning('{exe}')" in code
        assert "Close Clinic Scribe and Chrome completely, then run Setup again." in code
        for function in ("InitializeSetup", "PrepareToInstall", "InitializeUninstall"):
            body = code.split(f"function {function}", 1)[1].split("\nend;", 1)[0]
            assert "RunningProgramsMessage()" in body, function

    def test_a_check_that_cannot_run_fails_closed(self) -> None:
        body = _code().split("function RunningProgramsMessage", 1)[1].split("\nend;", 1)[0]
        assert "except\n    Result := CannotCheckMessage;" in body

    def test_uninstall_says_the_data_stays_c4(self) -> None:
        code = _code()
        # Round 27 PR-LOW-020: no retention period is claimed (nothing sweeps
        # after an uninstall).
        assert (
            "Your sessions, Past sessions and audit record were left in your Windows "
            "profile, unchanged."
        ) in code
        assert "kept 7 years" not in code
        assert "usPostUninstall" in code
        # Nothing under the user's profile is named for deletion.
        for section in ("UninstallDelete", "InstallDelete"):
            for line in _section(section):
                assert _entry(line)["Name"].startswith("{app}")

    def test_brace_comments_never_appear_in_code(self) -> None:
        """A Pascal brace comment ends at the first closing brace, and Inno
        constants are braces — so [Code] uses // comments only."""
        for line in _code().splitlines():
            assert not line.lstrip().startswith("{ "), line
