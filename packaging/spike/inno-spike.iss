; Installation plan Task 0.3 SPIKE — throwaway. NOT packaging/scribe.iss (Task 3.4).
;
; Answers, on this computer, from a normal terminal (packaging/spike/RUNBOOK.md):
;   1. PrivilegesRequired=admin gives a per-machine install (HKLM uninstall key,
;      64-bit Program Files).
;   2. How long [Code] GetSHA256OfFile takes over a ~2.5 GB file, and that its
;      digest matches (default: the scratch copy of the pinned language model
;      made in Task 0.1, whose SHA-256 is known).
;   3. The HKLM WER ExcludedApplications value lands as DWORD 1.
;   4. Which FilesNotToBackup / FilesNotToSnapshot value forms land verbatim:
;      the profile-independent "$UserProfile$" form, a literal "%LOCALAPPDATA%"
;      form, and Inno's expanded {localappdata} (the installing user's path).
;      Every pattern names a folder that does not exist (ClinikoScribeSpike),
;      so nothing real is excluded.
;   5. The install folder's ACL (inherited from Program Files).
;   6. An in-place upgrade under the same AppId: compile twice,
;      /DAppVer=0.0.1 then /DAppVer=0.0.2, install one over the other.
;
; Compile from the repo root:
;   & "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVer=0.0.1 packaging\spike\inno-spike.iss
; Override the hashed file with /DHashFile="C:\path" /DHashExpected=<64 hex, or empty>.

#ifndef AppVer
  #define AppVer "0.0.1"
#endif
#ifndef HashFile
  #define HashFile "C:\scribe-spike\Local\ClinikoScribe\models\language-model\Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
#endif
#ifndef HashExpected
  ; language_model.LANGUAGE_MODEL_SHA256
  #define HashExpected "3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597"
#endif

[Setup]
AppId={{5B7E2C1D-9A4F-4E8B-B3C6-2F1D0A9E7C54}
AppName=ClinikoScribe Inno Spike
AppVersion={#AppVer}
AppPublisher=Installation spike (throwaway)
DefaultDirName={commonpf64}\ClinikoScribeInnoSpike
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=C:\scribe-spike\inno-out
OutputBaseFilename=inno-spike-{#AppVer}
SetupLogging=no
UsedUserAreasWarning=no
Compression=lzma2
SolidCompression=yes

[Files]
Source: "inno-payload.txt"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
; 3. WER, per machine. A made-up exe name: nothing real changes.
Root: HKLM64; Subkey: "SOFTWARE\Microsoft\Windows\Windows Error Reporting\ExcludedApplications"; ValueType: dword; ValueName: "inno-spike-app.exe"; ValueData: 1; Flags: uninsdeletevalue
; 4. Backup and snapshot value forms (each a REG_MULTI_SZ with one pattern).
Root: HKLM64; Subkey: "SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToBackup"; ValueType: multisz; ValueName: "ClinikoScribeSpike_UserProfile"; ValueData: "$UserProfile$\AppData\Local\ClinikoScribeSpike\sessions\* /s"; Flags: uninsdeletevalue
Root: HKLM64; Subkey: "SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToBackup"; ValueType: multisz; ValueName: "ClinikoScribeSpike_EnvVar"; ValueData: "%LOCALAPPDATA%\ClinikoScribeSpike\sessions\* /s"; Flags: uninsdeletevalue
Root: HKLM64; Subkey: "SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToBackup"; ValueType: multisz; ValueName: "ClinikoScribeSpike_Expanded"; ValueData: "{localappdata}\ClinikoScribeSpike\sessions\* /s"; Flags: uninsdeletevalue
Root: HKLM64; Subkey: "SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToSnapshot"; ValueType: multisz; ValueName: "ClinikoScribeSpike_UserProfile"; ValueData: "$UserProfile$\AppData\Local\ClinikoScribeSpike\sessions\* /s"; Flags: uninsdeletevalue
Root: HKLM64; Subkey: "SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToSnapshot"; ValueType: multisz; ValueName: "ClinikoScribeSpike_EnvVar"; ValueData: "%LOCALAPPDATA%\ClinikoScribeSpike\sessions\* /s"; Flags: uninsdeletevalue
Root: HKLM64; Subkey: "SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToSnapshot"; ValueType: multisz; ValueName: "ClinikoScribeSpike_Expanded"; ValueData: "{localappdata}\ClinikoScribeSpike\sessions\* /s"; Flags: uninsdeletevalue

[Code]
function GetTickCount: DWord;
  external 'GetTickCount@kernel32.dll stdcall';

function InitializeSetup(): Boolean;
var
  Started, Elapsed: DWord;
  Digest, Verdict: String;
begin
  Result := True;
  if not FileExists('{#HashFile}') then
  begin
    MsgBox('Spike hash test: file not found:' + #13#10 + '{#HashFile}' + #13#10 +
      'Setup continues without the timing.', mbError, MB_OK);
    Exit;
  end;
  Started := GetTickCount;
  Digest := GetSHA256OfFile('{#HashFile}');
  Elapsed := GetTickCount - Started;
  if '{#HashExpected}' = '' then
    Verdict := 'no expected value given'
  else if LowerCase(Digest) = LowerCase('{#HashExpected}') then
    Verdict := 'yes'
  else
    Verdict := 'NO';
  MsgBox('Spike hash test' + #13#10 +
    'SHA-256 took ' + IntToStr(Integer(Elapsed)) + ' ms.' + #13#10 +
    'First 16 characters: ' + Copy(LowerCase(Digest), 1, 16) + #13#10 +
    'Matches the expected value: ' + Verdict, mbInformation, MB_OK);
end;
