; Installation plan Task 3.4 (D1, D5, D6, D8, D-I1): THE Clinic Scribe installer.
;
; Compiled ONLY by scripts/build-release.py (it passes every define below, from
; desktop/pyproject.toml and packaging/models-manifest.json), with Inno Setup
; 6.7.3 (Task 3.6's pin, an open practitioner item). Per machine, admin-only
; install folder, no per-user write, never launches the app (C3 / D8).
;
; What it writes: the app into {app} (C:\Program Files\ClinikoScribe, D-I1,
; whose inherited ACL is Users read-and-execute, Task 0.3); the models from the
; model pack beside setup.exe into {app}\models, every file checked against the
; compiled manifest (D5); HKLM only: the Chrome link, the crash-report (WER)
; exclusions, the backup and snapshot exclusions (D6, Task 0.3's forms) and,
; only if ticked, the clinic-only Chrome policy (D8). Uninstall removes all of
; that and never the data folder (C4).

#ifndef AppVersion
  #error AppVersion is not defined: build with scripts/build-release.py
#endif
#ifndef DistDir
  #error DistDir is not defined: build with scripts/build-release.py
#endif
#ifndef ModelPackDir
  #error ModelPackDir is not defined: build with scripts/build-release.py
#endif
#ifndef ModelsFiles
  #error ModelsFiles is not defined: build with scripts/build-release.py
#endif
#ifndef ModelsCode
  #error ModelsCode is not defined: build with scripts/build-release.py
#endif

; D-I1: the one folder install_layout.INSTALL_ROOTS accepts (pinned equal by
; desktop/tests/test_installer_script.py).
#define InstallRoot "C:\Program Files\ClinikoScribe"
#define HostName "com.scribe.cliniko_host"
#define UninstallKey "Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F3A6C2E-4D1B-4B7A-9E35-6C0D2F81A947}_is1"
#define PolicyKey "SOFTWARE\Policies\Google\Chrome"
#define PolicyValue "NativeMessagingUserLevelHosts"

[Setup]
AppId={{8F3A6C2E-4D1B-4B7A-9E35-6C0D2F81A947}
AppName=Clinic Scribe
AppVersion={#AppVersion}
AppVerName=Clinic Scribe {#AppVersion}
AppPublisher=Clinic Scribe
VersionInfoVersion={#AppVersion}
DefaultDirName={commonpf64}\ClinikoScribe
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
SetupLogging=no
UsedUserAreasWarning=no
CloseApplications=no
RestartApplications=no
OutputBaseFilename=ClinikoScribe-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Clinic Scribe
UninstallDisplayIcon={app}\scribe-app.exe

[Tasks]
Name: "clinicpolicy"; Description: "Clinic-only computer: block every per-user Chrome add-on that talks to a program. Chrome will then show ""managed by your organization"". Leave this unticked on a computer you also develop on."; Flags: unchecked

[InstallDelete]
; An upgrade, or a reinstall of an older build, replaces the program whole, so
; {app} holds exactly the audited bundle and never a previous build's leftovers
; (a second copy of a package's metadata, a stale extension file). Safe: the
; running-process check has refused while either program or Chrome runs, and
; the app writes nothing under {app}. The top-level files are replaced by name.
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\extension"
; A new model set replaces the old one whole, so {app}\models holds exactly
; the manifest's files.
Type: filesandordirs; Name: "{app}\models"; Check: ModelsNeedCopy

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#include ModelsFiles

[Icons]
Name: "{autoprograms}\Clinic Scribe"; Filename: "{app}\scribe-app.exe"

[Registry]
; The Chrome link (production host name, C2). Chrome reads a per-user link
; before this one (D9), so the app's Status tab warns when one shadows it.
Root: HKLM64; Subkey: "SOFTWARE\Google\Chrome\NativeMessagingHosts\{#HostName}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#HostName}.json"; Flags: uninsdeletekey
; Crash reports (D10): never for the two programs.
Root: HKLM64; Subkey: "SOFTWARE\Microsoft\Windows\Windows Error Reporting\ExcludedApplications"; ValueType: dword; ValueName: "scribe-app.exe"; ValueData: 1; Flags: uninsdeletevalue
Root: HKLM64; Subkey: "SOFTWARE\Microsoft\Windows\Windows Error Reporting\ExcludedApplications"; ValueType: dword; ValueName: "scribe-host.exe"; ValueData: 1; Flags: uninsdeletevalue
; Backup and snapshot exclusions (D6, best-effort, C5): live sessions and logs
; only, in the profile-independent $UserProfile$ form Task 0.3 proved lands
; verbatim (never Inno's expanded local-app-data folder, which names the
; ELEVATING account).
Root: HKLM64; Subkey: "SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToBackup"; ValueType: multisz; ValueName: "ClinikoScribe"; ValueData: "$UserProfile$\AppData\Local\ClinikoScribe\sessions\* /s{break}$UserProfile$\AppData\Local\ClinikoScribe\logs\* /s"; Flags: uninsdeletevalue
Root: HKLM64; Subkey: "SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToSnapshot"; ValueType: multisz; ValueName: "ClinikoScribe"; ValueData: "$UserProfile$\AppData\Local\ClinikoScribe\sessions\* /s{break}$UserProfile$\AppData\Local\ClinikoScribe\logs\* /s"; Flags: uninsdeletevalue
; D8: the clinic-only policy, only when ticked and only if nobody else set it.
Root: HKLM64; Subkey: "{#PolicyKey}"; ValueType: dword; ValueName: "{#PolicyValue}"; ValueData: 0; Tasks: clinicpolicy; Check: PolicyIsOurs; Flags: uninsdeletevalue

[UninstallDelete]
Type: filesandordirs; Name: "{app}\models"

[Code]
// Comments in this section use // only: a brace comment ends at the first
// closing brace, and Inno's constants are written in braces.

function CloseFirstMessage(): String;
begin
  Result := 'Close Clinic Scribe and Chrome completely, then run Setup again.' + #13#10#13#10 +
    'Chrome can keep running in the background after its windows close: check that no chrome.exe is left in Task Manager.';
end;

function CannotCheckMessage(): String;
begin
  Result := 'Setup could not check whether Clinic Scribe or Chrome is running.' + #13#10#13#10 +
    'Close Clinic Scribe and Chrome completely, then run Setup again.';
end;

function KeptDataMessage(): String;
begin
  // Round 27 PR-LOW-020: no retention period is claimed — after an uninstall
  // nothing sweeps, so the data stays exactly as it was.
  Result := 'Your sessions, Past sessions and audit record were left in your Windows profile, unchanged.';
end;

var
  ModelPaths: array of String;
  ModelHashes: array of String;
  ModelsCopy: Boolean;
  PolicyForeign: Boolean;
  IsUpgrade: Boolean;
  // Round 20: set when a copied model failed its check, or the policy this
  // installer set could not be removed; the Finish page then says so.
  ModelsIncomplete: Boolean;
  PolicyLeft: Boolean;

procedure AddModelFile(const Path, Sha256: String);
var
  Count: Integer;
begin
  Count := GetArrayLength(ModelPaths);
  SetArrayLength(ModelPaths, Count + 1);
  SetArrayLength(ModelHashes, Count + 1);
  ModelPaths[Count] := Path;
  ModelHashes[Count] := Sha256;
end;

#include ModelsCode

// --- the running-process check (scribe-app.exe, scribe-host.exe, chrome.exe) ---

function ProcessRunning(const ExeName: String): Boolean;
var
  Locator, Service, Found: Variant;
begin
  Locator := CreateOleObject('WbemScripting.SWbemLocator');
  Service := Locator.ConnectServer('.', 'root\CIMV2');
  Found := Service.ExecQuery('SELECT ProcessId FROM Win32_Process WHERE Name = ''' + ExeName + '''');
  Result := Found.Count > 0;
end;

// '' when none of the three runs; otherwise the message to show. A check that
// cannot run fails closed.
function RunningProgramsMessage(): String;
begin
  Result := '';
  try
    if ProcessRunning('scribe-app.exe') or ProcessRunning('scribe-host.exe') or ProcessRunning('chrome.exe') then
      Result := CloseFirstMessage;
  except
    Result := CannotCheckMessage;
  end;
end;

// --- the models (D5): the installed set, or the pack beside setup.exe ---

// Whether the file at Path exists and has the SHA-256 Sha256.
function ModelFileMatches(const Path, Sha256: String): Boolean;
var
  Digest: String;
begin
  Result := False;
  if not FileExists(Path) then
    Exit;
  try
    Digest := GetSHA256OfFile(Path);
  except
    Digest := '';
  end;
  Result := CompareText(Digest, Sha256) = 0;
end;

// The first manifest file under Folder that is missing or does not match its
// SHA-256, or '' when every one matches. Used BEFORE anything is copied, where
// any mismatch refuses the whole install.
function FirstModelMismatch(const Folder: String): String;
var
  I: Integer;
begin
  Result := '';
  for I := 0 to GetArrayLength(ModelPaths) - 1 do
    if not ModelFileMatches(Folder + ModelPaths[I], ModelHashes[I]) then
    begin
      Result := ModelPaths[I];
      Exit;
    end;
end;

// Round 20 PR-HIGH-003: AFTER the copy, EVERY manifest file under Folder is
// checked, never only the first. Removing each bad copy is ATTEMPTED (a
// removed one then reads as missing); one that could not be removed is named
// "(damaged, and could not be removed)", Setup exits 9
// (GetCustomSetupExitCode) and the app must not be opened before Setup is run
// again (round 28 PR-LOW-031). The bad files, one per line, or '' when every
// one matches.
function RemoveDamagedModels(const Folder: String): String;
var
  I: Integer;
begin
  Result := '';
  for I := 0 to GetArrayLength(ModelPaths) - 1 do
    if not ModelFileMatches(Folder + ModelPaths[I], ModelHashes[I]) then
    begin
      Result := Result + #13#10 + '  ' + ModelPaths[I];
      if FileExists(Folder + ModelPaths[I]) then
        if not DeleteFile(Folder + ModelPaths[I]) then
          Result := Result + ' (damaged, and could not be removed)';
    end;
end;

function ModelsNeedCopy(): Boolean;
begin
  Result := ModelsCopy;
end;

// --- the clinic-only policy (D8) ---

function PolicyIsOurs(): Boolean;
begin
  Result := not PolicyForeign;
end;

function InitializeSetup(): Boolean;
var
  Running: String;
begin
  ModelsCopy := True;
  ModelsIncomplete := False;
  PolicyLeft := False;
  AddModelFiles();
  IsUpgrade := RegKeyExists(HKLM64, '{#UninstallKey}');
  Running := RunningProgramsMessage();
  Result := Running = '';
  if not Result then
    MsgBox(Running, mbError, MB_OK);
end;

procedure InitializeWizard();
begin
  // Set by someone else (a value present that this installer did not
  // write): left exactly as it is, and not removed by THIS run's uninstall
  // record. Residue (threat model, "Installation"): an earlier run that set
  // the value logged its removal, and Inno keeps that log entry, so a value
  // someone sets after a later untick is still removed at uninstall.
  PolicyForeign := RegValueExists(HKLM64, '{#PolicyKey}', '{#PolicyValue}') and
    (GetPreviousData('ClinicOnlyPolicy', '0') <> '1');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Mismatch, Pack: String;
begin
  Result := RunningProgramsMessage();
  if Result <> '' then
    Exit;
  if CompareText(ExpandConstant('{app}'), '{#InstallRoot}') <> 0 then
  begin
    Result := 'Clinic Scribe installs only into {#InstallRoot}.';
    Exit;
  end;
  // Skipped when the installed models already match (an upgrade with the
  // same models needs no pack).
  ModelsCopy := FirstModelMismatch(ExpandConstant('{app}\models\')) <> '';
  if not ModelsCopy then
    Exit;
  Pack := ExpandConstant('{src}\{#ModelPackDir}\');
  if not DirExists(Pack) then
  begin
    Result := 'The model pack folder {#ModelPackDir} must be next to this setup program.' + #13#10#13#10 +
      'Put it beside setup, then run Setup again. Nothing was changed.';
    Exit;
  end;
  // Every pack file is checked before anything is copied: a refusal changes
  // nothing.
  Mismatch := FirstModelMismatch(Pack);
  if Mismatch <> '' then
    Result := 'The model file ' + Mismatch + ' in the model pack is missing or damaged.' + #13#10#13#10 +
      'Copy the model pack again, then run Setup again. Nothing was changed.';
end;

procedure RegisterPreviousData(PreviousDataKey: Integer);
begin
  // A policy this installer set and could not remove stays recorded as ours,
  // so the next run removes it (and never mistakes it for someone else's).
  if (WizardIsTaskSelected('clinicpolicy') and not PolicyForeign) or PolicyLeft then
    SetPreviousData(PreviousDataKey, 'ClinicOnlyPolicy', '1')
  else
    SetPreviousData(PreviousDataKey, 'ClinicOnlyPolicy', '0');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Damaged: String;
begin
  // Unticked on this run but set by an earlier run of this installer: removed
  // as the install starts (before the previous data is written), and checked
  // gone: a value that stays is said on the Finish page. HKLM only (C3).
  if CurStep = ssInstall then
    if (not WizardIsTaskSelected('clinicpolicy')) and (GetPreviousData('ClinicOnlyPolicy', '0') = '1') then
    begin
      RegDeleteValue(HKLM64, '{#PolicyKey}', '{#PolicyValue}');
      PolicyLeft := RegValueExists(HKLM64, '{#PolicyKey}', '{#PolicyValue}');
    end;
  if CurStep <> ssPostInstall then
    Exit;
  // The copies are checked again, every one of them.
  if ModelsCopy then
  begin
    Damaged := RemoveDamagedModels(ExpandConstant('{app}\models\'));
    if Damaged <> '' then
    begin
      ModelsIncomplete := True;
      MsgBox('These model files did not copy correctly:' + Damaged + #13#10#13#10 +
        'Clinic Scribe is NOT completely installed. Run Setup again with the model pack beside it.',
        mbError, MB_OK);
    end;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID <> wpFinished then
    Exit;
  // D8: the installer never launches the app (there is no Run section).
  // Round 20 PR-HIGH-003: a failed model copy is never "installed".
  if ModelsIncomplete then
    WizardForm.FinishedLabel.Caption := 'Clinic Scribe is NOT completely installed.' + #13#10#13#10 +
      'One or more model files did not copy correctly. Run Setup again with the model pack beside it, ' +
      'before you open Clinic Scribe.'
  else if IsUpgrade then
    WizardForm.FinishedLabel.Caption := 'Clinic Scribe is updated.' + #13#10#13#10 +
      'In Chrome, reload the Clinic Scribe Companion extension, then fully restart Chrome.' + #13#10#13#10 +
      'Open Clinic Scribe from the Start menu.'
  else
    WizardForm.FinishedLabel.Caption := 'Clinic Scribe is installed.' + #13#10#13#10 +
      'In Chrome, remove any older Clinic Scribe Companion, choose Load unpacked and select ' +
      ExpandConstant('{app}\extension') + ', then fully restart Chrome.' + #13#10#13#10 +
      'Open Clinic Scribe from the Start menu.';
  // Round 20 (PR-HIGH-003's sibling): an unticked policy that stayed is said.
  if PolicyLeft then
    WizardForm.FinishedLabel.Caption := WizardForm.FinishedLabel.Caption + #13#10#13#10 +
      'The clinic-only Chrome setting could not be removed. Run Setup again; if it stays, ' +
      'ask whoever manages this computer.';
  // Round 22: a ticked box over a value someone else set writes nothing (the
  // value is left exactly as it is), so the Finish page says so.
  if WizardIsTaskSelected('clinicpolicy') and PolicyForeign then
    WizardForm.FinishedLabel.Caption := WizardForm.FinishedLabel.Caption + #13#10#13#10 +
      'The clinic-only Chrome setting was already set on this computer by something else, ' +
      'so Setup left it exactly as it is. Ask whoever manages this computer what it is set to.';
  // Round 40 LOW-001: Inno sized the label for its own text before this page
  // showed; without re-sizing it after the last change, every paragraph past
  // the old height (the Start-menu line, the warnings above) was cut off.
  WizardForm.AdjustLabelHeight(WizardForm.FinishedLabel);
end;

// Round 27 PR-MED-019: a run that left a damaged model, or could not remove
// the clinic-only setting an earlier run set, does not end with Setup's
// success code. Inno calls this only when Setup ran to completion and would
// otherwise exit 0; 1-8 are Inno's own codes, so these are 9 and 10.
function GetCustomSetupExitCode(): Integer;
begin
  Result := 0;
  if ModelsIncomplete then
    Result := 9
  else if PolicyLeft then
    Result := 10;
end;

function InitializeUninstall(): Boolean;
var
  Running: String;
begin
  Running := RunningProgramsMessage();
  Result := Running = '';
  if not Result then
    MsgBox(Running, mbError, MB_OK);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent then
    MsgBox('Clinic Scribe has been removed.' + #13#10#13#10 + KeptDataMessage, mbInformation, MB_OK);
end;
