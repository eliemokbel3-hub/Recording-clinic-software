# Installation spikes — practitioner runbook (plan-installation Phase 0)

Written 2026-10-02 by the stage-0 executor. These are **throwaway tests**. They answer the questions the installer build depends on. Nothing here is the real installer.

**Read this first**
- Run every step from a **normal PowerShell window** that you opened yourself: Start menu, type `PowerShell`, Enter. Never run them from Claude, and never from a chat "Run" button. Agent shells on this computer see a private copy of `%LOCALAPPDATA%` and the registry, so a check run there proves nothing.
- When a step says **elevated**, open **Windows PowerShell as administrator** (right-click → *Run as administrator*) and run only that step there.
- Each box holds **one** command. Copy it, paste it, press Enter, then compare with *What you should see*.
- Nothing here adds a clinic, opens a patient or touches your real Past sessions, audit record, voice profile or style. Task 0.1 runs in a scratch copy of the app's data folder (`C:\scribe-spike\Local`) and refuses to start anywhere else. **The one exception is Task 0.2**: your everyday app and Chrome run on your real data folder for one connection check, as they do every day. You start no recording and open no patient.
- Everything the spikes build goes under `C:\scribe-spike\`. The **Finishing up** section at the end removes it.
- **Order:** 0.1 → 0.5 → 0.2 → 0.3 → 0.4. Task 0.5 scans the program 0.1 builds, and 0.2 reuses 0.1's Python.
- When you finish, send back everything under each **Report back** heading. Screenshots are fine.
- **Each task starts with a "Before you start" check block.** Each one confirms the computer is in the expected state before anything changes. If a check there does not match, stop and report it: nothing has been changed yet.
- **If a later step fails** (an error, or a result that does not match *What you should see*), stop. Run the matching "put it back" procedure below, then report the step number and what the screen says. Each procedure is safe to run however far you got.

  | Where it failed | Run this first |
  |---|---|
  | Task 0.1, any step | nothing — Task 0.1 only changes `C:\scribe-spike`. Your everyday Python environment is copied there and the copy is used; the original is never changed |
  | Task 0.2, from step 7 on | Task 0.2's **Put everything back** (steps 20–25) |
  | Task 0.3, from step 4 on | Task 0.3's step 14 (uninstall) |
  | Task 0.5 | nothing — it only scans |

---

## Task 0.1 — The packaged app, run in a scratch profile

**What this answers:** whether the packaged `scribe-app.exe` works. That means Qt, the speech and language models, the keyring, the Windows voice (SAPI), the bundled note settings and no networking parts. It also answers which Python version to build with, and whether a windowless program gets working input and output pipes (Task 0.2 needs that answer).

**What the scratch profile does NOT keep apart** (checked in the code on 2026-10-02):
- Every data folder the app uses (sessions, audit, Past sessions, logs, settings, profile, style, clinics list, the lock file) and the models folder follow `LOCALAPPDATA`. The spike sets that to the scratch folder, so they all land in `C:\scribe-spike\Local\ClinikoScribe`.
- **Windows Credential Manager is shared.** The scratch clinics list is empty, so no clinic key is read. Two things do touch it:
  - The Status tab's self-test writes a test entry and then deletes it, exactly as your everyday app's self-test does.
  - The spike's checks make one read of an entry name that does not exist.
  - **Do not add a clinic in the spike.**
- **The app's one-copy lock and the Chrome link pipe are shared** with your everyday app. So **close Clinic Scribe and Chrome before you start.** If Chrome were open, it could link the extension to the spike app.
- **Windows' temporary folder is shared.** The Microphone tab's benchmark puts its synthetic voice clip in your normal `%TEMP%` for a moment and deletes it, as it does today.
- **Two Windows registry reads are shared**: crash-report exclusions and the Chrome link. Both are read only.
- **Documents is shared.** An export from the Past sessions tab would go there, so **do not export anything.**

### Before you start

1. Close Clinic Scribe and Chrome completely, then check that none are left:

```powershell
Get-Process scribe-app, scribe-host, pythonw, chrome -ErrorAction SilentlyContinue
```
*What you should see:* nothing (a new prompt line). If anything is listed, close it (Task Manager → End task) and run the check again.

2. Record the newest change time in your **real** data folder. You will repeat this at the end; the two answers must be identical.

```powershell
@(Get-Item (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ClinikoScribe')) + @(Get-ChildItem (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ClinikoScribe') -Recurse -Force -ErrorAction SilentlyContinue) | Sort-Object LastWriteTime -Descending | Select-Object -First 1 FullName, LastWriteTime
```
*Report back:* the `FullName` and `LastWriteTime` shown (**"real folder BEFORE"**).

3. Go to the project folder:

```powershell
Set-Location "C:\Recording clinic software"
```

4. Check the Python version the build will use:

```powershell
.venv\Scripts\python.exe --version
```
*Report back:* the version (expected `Python 3.14.x`).

4a. Check there is no spike folder left from an earlier attempt:

```powershell
Test-Path C:\scribe-spike
```
*What you should see:* `False`. If it says `True`, an earlier attempt left it, so clear it first:
1. If `C:\scribe-spike\hkcu-host-backup.reg` exists, an earlier Task 0.2 may not have been put back. Run Task 0.2's **Put everything back** (steps 20–25) first. It needs that file, and it is safe to run again.
2. Delete the old folder:

```powershell
Remove-Item -Recurse -Force C:\scribe-spike
```
3. Run the `Test-Path` check again; it should now say `False`. If it still says `True`, something has a file open there: close it and repeat 2 and 3.

4b. Make the spike folder:

```powershell
New-Item -ItemType Directory C:\scribe-spike
```

4c. Record the package list of your everyday Python environment. This only reads it. The last section of this runbook compares against this list to prove the environment was never changed.

```powershell
.venv\Scripts\python.exe -m pip freeze --all | Out-File -Encoding utf8 C:\scribe-spike\everyday-before.txt
```

4d. Make a **build copy** of the everyday Python environment. PyInstaller goes into this copy, and every build runs from it. Your everyday environment (`.venv`) is never changed. The copy needs a few GB of free space and can take a few minutes.

```powershell
Copy-Item -Recurse -Force .venv C:\scribe-spike\venv-build
```
If the copy stops with an error, delete the half-made copy with the command below, then run the copy again:

```powershell
Remove-Item -Recurse -Force C:\scribe-spike\venv-build
```

4e. Check the build copy is its own environment:

```powershell
C:\scribe-spike\venv-build\Scripts\python.exe -c "import sys; print(sys.prefix)"
```
*What you should see:* `C:\scribe-spike\venv-build`. If it shows the project's `.venv` instead, stop and report it.

> **From here on, use the build copy ONLY as `C:\scribe-spike\venv-build\Scripts\python.exe -m …`, exactly as the steps show.** Never run any other program inside `C:\scribe-spike\venv-build\Scripts` (such as `pip.exe` or `pyinstaller.exe`). Those were copied from your everyday environment and would act on it.

### Install PyInstaller (a build tool only, not part of the app)

PyInstaller turns the app into a folder with `.exe` files. It is a **developer-only build tool**: the app never loads it, and it adds no app dependency. Installing it is a setup-time network step, like step 2 of the project's setup.

**Which version.** The plan wants a version that supports Python 3.14. I believe that is **6.16.0 or later**, but I could not confirm it: web access was denied in this session. Use the newest release, and record its exact number. Task 3.2 pins it.

5. See the available versions:

```powershell
C:\scribe-spike\venv-build\Scripts\python.exe -m pip index versions pyinstaller
```
*Report back:* the first version number listed after `Available versions:`.

Now store that number once, in this window, so no later command needs you to type it. This reads it from the first line pip prints, `pyinstaller (…)`, and shows it:

```powershell
$v = (C:\scribe-spike\venv-build\Scripts\python.exe -m pip index versions pyinstaller | Select-String '^pyinstaller \((.+)\)').Matches[0].Groups[1].Value; $v
```
*What you should see:* the same number you just reported. Then check it is new enough:

```powershell
[version]$v -ge [version]"6.16.0"
```
*What you should see:* `True`. If it says `False`, stop and report it. If either command shows an error or a blank line, report it and stop.

`$v` lasts only as long as this window. If you close the window before step 8, open a new one, run step 3 and then the `$v = …` command above again.

6. Check whether the Microsoft C++ build tools are installed. The bootloader (the small program at the front of each `.exe`) is built from source when they are, because self-built bootloaders draw fewer antivirus false alarms (plan D1):

```powershell
& "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property displayName
```
*What you should see:*
- **A product name** (for example `Visual Studio Build Tools 2022`): follow **6a**.
- **Nothing**, or *"is not recognized"*: follow **6b**.

**6a — with the build tools: build the bootloader from source**

Download the PyInstaller source for that exact version (`$v`, from step 5):

```powershell
git clone --depth 1 --branch "v$v" https://github.com/pyinstaller/pyinstaller.git C:\scribe-spike\pyinstaller-src
```

Record the fingerprint of the ready-made windowed bootloader that ships in the source:

```powershell
Get-FileHash C:\scribe-spike\pyinstaller-src\PyInstaller\bootloader\Windows-64bit-intel\runw.exe
```

Go to the bootloader folder:

```powershell
Set-Location C:\scribe-spike\pyinstaller-src\bootloader
```

Build the bootloader:

```powershell
& C:\scribe-spike\venv-build\Scripts\python.exe ./waf all --target-arch=64bit
```
*What you should see:* it ends with `'all' finished successfully`.

**If it says it cannot find a compiler**, build it from Visual Studio's own prompt instead:
1. Open **x64 Native Tools Command Prompt for VS** from the Start menu. This is a Command Prompt, not PowerShell, so it takes these two exact lines, not the PowerShell line above. First go to the bootloader folder:

```bat
cd /d C:\scribe-spike\pyinstaller-src\bootloader
```

2. Then build it:

```bat
C:\scribe-spike\venv-build\Scripts\python.exe ./waf all --target-arch=64bit
```
3. It should end with `'all' finished successfully`.
4. Close that window and carry on below in your PowerShell window.

Record the fingerprint again:

```powershell
Get-FileHash C:\scribe-spike\pyinstaller-src\PyInstaller\bootloader\Windows-64bit-intel\runw.exe
```
*What you should see:* a **different** hash from the first one. That proves the bootloader was rebuilt here.

Go back to the project folder:

```powershell
Set-Location "C:\Recording clinic software"
```

Install PyInstaller from that source:

```powershell
C:\scribe-spike\venv-build\Scripts\python.exe -m pip install C:\scribe-spike\pyinstaller-src
```

**6b — without the build tools: use the ready-made bootloader for now**

```powershell
C:\scribe-spike\venv-build\Scripts\python.exe -m pip install "pyinstaller==$v"
```
This means the spike runs on PyInstaller's ready-made bootloader. D1's "built from source" stays open. It is then proved on the CI build machine: GitHub's Windows build machines include the C++ tools (checked 2026-10-02 in their published image lists). Task 0.5's antivirus result then applies to the ready-made bootloader.

Installing **Build Tools for Visual Studio** on this computer is NOT part of this runbook. If you ever choose to, it is your own decision, and it can be removed again from Settings → Apps.

7. Record the exact tool versions:

```powershell
C:\scribe-spike\venv-build\Scripts\python.exe -m PyInstaller --version
```

```powershell
C:\scribe-spike\venv-build\Scripts\python.exe -m pip show pyinstaller-hooks-contrib
```
*Report back:* the PyInstaller version, the `Version:` line of the second command, and whether you took **6a** (with both hashes) or **6b**.

Then confirm the build copy is still consistent:

```powershell
C:\scribe-spike\venv-build\Scripts\python.exe -m pip check
```
*What you should see:* `No broken requirements found.` If it lists anything, stop and report what it listed. Only the build copy is affected, so there is nothing to put back.

Record what the install added or changed, compared with your everyday environment:

```powershell
Compare-Object (Get-Content C:\scribe-spike\everyday-before.txt) (C:\scribe-spike\venv-build\Scripts\python.exe -m pip freeze --all)
```
*Report back:* the lines shown. `=>` marks a package that is new or at a new version in the build copy; `<=` marks the version it replaced. Task 3.2 uses this list. A pair of lines for the project itself (`scribe-desktop` / `scribe_desktop`) that differ only in a long commit id is expected: it reflects the project's current version, not a change to the environment.

### Build the spike app

8. Build it. This takes several minutes and prints a lot:

```powershell
C:\scribe-spike\venv-build\Scripts\python.exe -m PyInstaller --noconfirm --distpath C:\scribe-spike\dist --workpath C:\scribe-spike\build packaging\spike\scribe.spec
```
*What you should see:* the last lines include `Building COLLECT` … `completed successfully`.

*Report back:*
- whether it succeeded;
- any line that starts with `SPIKE-FILTERED`. Those name a networking file a hook tried to add; none is expected;
- any line containing `ERROR`.

If you see a security alert from Windows Security during the build, screenshot it and **do not allow or exclude anything** (rule C10).

9. List the build's warnings about the app's own parts. This answers which hidden imports Task 3.2 needs:

```powershell
Select-String -Path C:\scribe-spike\build\scribe\warn-scribe.txt -Pattern "scribe_desktop|keyring|llama|ctranslate2|onnxruntime|faster_whisper|sounddevice|win32com|PySide6"
```
*Report back:* the lines shown, or "none". This file lists missing optional modules only, never data.

10. Check that no Qt networking file was bundled:

```powershell
Get-ChildItem C:\scribe-spike\dist\scribe-app -Recurse -Include "Qt6Network*.dll", "Qt6WebSockets*.dll"
```
*What you should see:* nothing.

11. Check that the spike refuses your real data folder. This window still has your normal `LOCALAPPDATA`:

```powershell
& C:\scribe-spike\dist\scribe-app\scribe-app.exe
```
*What you should see:* a box titled **Clinic Scribe spike** saying that `LOCALAPPDATA` points at your REAL Local AppData folder. Click OK; nothing else opens. *Report back:* the box appeared (yes/no).

### Make the scratch profile

12. Make the scratch models folder:

```powershell
New-Item -ItemType Directory -Force C:\scribe-spike\Local\ClinikoScribe\models\whisper
```

13. Copy the four model folders into it from your real models folder. Copying only reads the originals.

```powershell
Copy-Item -Recurse (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ClinikoScribe\models\silero-vad') C:\scribe-spike\Local\ClinikoScribe\models
```

```powershell
Copy-Item -Recurse (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ClinikoScribe\models\whisper\medium') C:\scribe-spike\Local\ClinikoScribe\models\whisper
```

```powershell
Copy-Item -Recurse (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ClinikoScribe\models\speaker-embedding') C:\scribe-spike\Local\ClinikoScribe\models
```

```powershell
Copy-Item -Recurse (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ClinikoScribe\models\language-model') C:\scribe-spike\Local\ClinikoScribe\models
```
The last copy is about 2.3 GB and can take a minute. Copy nothing else: no clinics file, no Past sessions, no audit, no profile, no style.

14. **From now on, keep this same window open for the rest of Task 0.1.** Point it at the scratch profile:

```powershell
$env:LOCALAPPDATA = "C:\scribe-spike\Local"
```
This affects only this window and the programs started from it. If you close the window, you must run this line again in the new window before any spike step.

### The automatic checks

15. Clear any results from an earlier try of these steps. It prints nothing, and it touches only the scratch folder:

```powershell
Remove-Item -Recurse -Force C:\scribe-spike\Local\spike-results -ErrorAction SilentlyContinue
```

```powershell
Test-Path C:\scribe-spike\Local\spike-results
```
*What you should see:* `False`. If it says `True`, an earlier spike program is still running: close it (Task Manager → End task on `scribe-app.exe`), then repeat both commands.

Then run the spike's checks. There is no window and it takes several minutes; the prompt comes back when it finishes:

```powershell
Start-Process -FilePath C:\scribe-spike\dist\scribe-app\scribe-app.exe -ArgumentList "--spike-checks" -Wait
```

16. Read the results:

```powershell
Get-Content C:\scribe-spike\Local\spike-results\checks.txt
```
*What you should see:* twelve lines, then `=== spike checks done: 12 of 12 passed ===`. The lines that matter most:

| Line | Good result |
|---|---|
| `frozen:` | `python=3.14…` `frozen=True` |
| `stdio_at_entry:` / `stdio_pipe_raw:` / `stdio_pipe_adapted:` | any value (they are measurements); `stdio_pipe_adapted` should say `echo=ok` |
| `qt_platform:` | `platform=windows` |
| `qt_network:` | `importable=none loaded=none dlls=none` |
| `keyring:` | `backend=…WinVaultKeyring` (or `inner=WinVaultKeyring`) and `read_missing=None` |
| `config:` | `defaults=` a number above 0 |
| `audio:` | `input_devices=` a number above 0 |
| `onnx:` | PASS |
| `sapi_whisper:` | `words=` above 0, and an `rtf=` |
| `prose:` | `errored=0` and `passed=` 1 (a `failed=1` is a quality result, not a packaging failure — report it) |

*Report back:* the whole file. **Read it before you send it.**
- It holds fixed words and numbers.
- For any check that FAILED, it also holds the error's type and message. A message can include a file path (the scratch or program folders, possibly with your Windows user name) or a library's own error text.
- It never holds patient information, because the scratch profile has none.
- Blank out anything in a message you would rather not share.

17. Read the pipe measurements:

```powershell
Get-Content C:\scribe-spike\Local\spike-results\stdio.txt
```
*Report back:* the whole file. Its `echo-child-raw before:` line answers the plan's question: `stdin=None(handle=valid)` means the windowed program's input stream is missing even though Windows gave it a pipe. In that case Task 0.2's adaptation is required.

### The app itself

18. Start the spike app from this window:

```powershell
& C:\scribe-spike\dist\scribe-app\scribe-app.exe
```
*What you should see:* the Clinic Scribe window. If instead a box says the app is already running, your everyday app is still open: close both and repeat from step 1. If a box titled *Unhandled exception* appears, screenshot it.

19. In the window:
   - **Status tab:** the self-test shows **2/2**. Read every warning line. The Chrome-link line shows your everyday registration, which is expected.
   - **Microphone tab:** your microphone is listed. Run the hardware benchmark. It should end with a line for `medium` showing an RTF number.
   - **Practitioner tab:** read the speaker-model and language-model status lines.
   - Do **not** open the Clinics tab, add a clinic, export anything or tick consent for a patient.
   - *Optional:* a 10-second desktop recording checks that the microphone opens. Tick the consent box, press Start, say "testing one two three", press Finish, then Discard.

*Report back:* the self-test result, every Status-tab warning line word for word, the benchmark's `medium` line, and the two Practitioner-tab model lines (screenshots are fine).

20. Close the spike app with its window's close button. Then check its log for crashes:

```powershell
Select-String -Path C:\scribe-spike\Local\ClinikoScribe\logs\scribe-app.log -Pattern "uncaught_exception|app_start|app_exit|pipe_server"
```
*Report back:* the lines shown.

21. Read the pipe file again. The benchmark worker added lines to it:

```powershell
Get-Content C:\scribe-spike\Local\spike-results\stdio.txt
```
*Report back:* the `benchmark-worker` lines.

22. Repeat the real-folder check from step 2. It is the same command and works in this window, because it asks Windows for the real folder rather than reading `LOCALAPPDATA`:

```powershell
@(Get-Item (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ClinikoScribe')) + @(Get-ChildItem (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ClinikoScribe') -Recurse -Force -ErrorAction SilentlyContinue) | Sort-Object LastWriteTime -Descending | Select-Object -First 1 FullName, LastWriteTime
```
*What you should see:* **exactly** the same `FullName` and `LastWriteTime` as step 2. *Report back:* **"real folder AFTER"**, and whether it matches.

23. Close this PowerShell window. That ends the scratch setting. **Keep `C:\scribe-spike`**: Tasks 0.5, 0.2 and 0.3 use it.

**If the Python 3.14 build or run failed** (step 8 or step 16): report it first. The fallback is Python 3.12, the CI floor. Wait for the go-ahead before doing it; it is a long download. Then:
1. Make a second environment, `C:\scribe-spike\venv312`, set up the same way as step 2 of the project's setup. The exact commands come with the go-ahead. It lives inside `C:\scribe-spike`, so Finishing up removes it.
2. Open a new normal PowerShell window and run step 3 (the project folder). Then run steps 5–23 again with one change: wherever a command starts `C:\scribe-spike\venv-build\Scripts\python.exe`, use `C:\scribe-spike\venv312\Scripts\python.exe` instead. Two parts are skipped:
   - if you took 6a the first time, skip its download, both fingerprints and the bootloader build, which are already done in `C:\scribe-spike\pyinstaller-src`; run only the install from that source (6b is run as written);
   - in step 7, skip the `Compare-Object`: it compares against your everyday 3.14 list, so it would only show differences.
3. Task 0.2 step 2 then builds the host with `venv312` too (it shows the command).

---

## Task 0.5 — Antivirus and Smart App Control

**What this answers:** whether Windows Defender flags the unsigned build, and whether Smart App Control would block it.

**The rule (C10):** never add a Defender exclusion and never turn Smart App Control down to make the build run. Either of the following **pauses the plan for a signing decision**:
- a detection;
- Smart App Control set to **On**.

1. **Elevated.** Scan the spike app folder (a few minutes):

```powershell
Start-MpScan -ScanType CustomScan -ScanPath C:\scribe-spike\dist\scribe-app
```

2. **Elevated.** List anything Defender has detected:

```powershell
Get-MpThreatDetection
```
*What you should see:* nothing. *Report back:* "nothing", or the `ThreatID`, `InitialDetectionTime` and `Resources` lines shown.

3. Open **Windows Security** → **App & browser control** → **Smart App Control settings**. *Report back:* the selected option: **On**, **Evaluation** or **Off**.

4. *Optional second reading.* This registry value is how Smart App Control's state is commonly reported. I could not verify it from the Microsoft documentation in this session, so the Windows Security page above is the authority:

```powershell
reg query "HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy" /v VerifiedAndReputablePolicyState
```
*Report back:* the value shown, or "not found".

A program you built on this computer carries no "downloaded from the internet" mark, so SmartScreen does not prompt for it. The CI-built installer you download in Phase P will carry that mark, and SmartScreen may then show "Windows protected your PC". That is expected for an unsigned build (D7).

---

## Task 0.2 — Chrome starts the packaged host from the install folder

**What this answers:** whether Chrome starts a native host that lives in `C:\Program Files\ClinikoScribe` and is registered for the whole machine (HKLM). It also answers whether a per-user (HKCU) registration overrides the machine one.

**Scope:** a connection check only. The badge turns green **OK**, and that is all. You start no recording and open no patient. Your everyday app runs on your real data folder as it does every day; its normal start-up housekeeping (sweep, prune, logs) runs as usual. The packaged host runs today's host code and writes only its usual content-free log.

**The names used below come from the code:**
- host name `com.scribe.cliniko_host`;
- extension `chrome-extension://mbmhglgadhdohpgbmpbjnaifjagfdfid/`;
- the per-user key `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host`;
- the machine key is the same path under `HKLM\SOFTWARE`.

**Not yet confirmed — this spike finds out:** Chrome checks the per-user key first, then the machine key, in both registry views (the plan's External Findings, from Chromium's source). The steps write the machine key in the 64-bit view.

### Build the host

1. Open a **new** normal PowerShell window. Do not reuse the Task 0.1 window: this one must have your normal `LOCALAPPDATA`. Go to the project folder:

```powershell
Set-Location "C:\Recording clinic software"
```

2. Build the packaged host with the same environment that built the working Task 0.1 app. Run **one** of these two commands.

   Normally (Task 0.1 worked on Python 3.14), use the build copy:

```powershell
C:\scribe-spike\venv-build\Scripts\python.exe -m PyInstaller --noconfirm --distpath C:\scribe-spike\dist --workpath C:\scribe-spike\build packaging\spike\host.spec
```

   Only if Task 0.1 used the Python 3.12 fallback:

```powershell
C:\scribe-spike\venv312\Scripts\python.exe -m PyInstaller --noconfirm --distpath C:\scribe-spike\dist --workpath C:\scribe-spike\build packaging\spike\host.spec
```
*What you should see:* `Building COLLECT` … `completed successfully`. *Report back:* which of the two you ran.

3. **Elevated.** Scan it as in Task 0.5:

```powershell
Start-MpScan -ScanType CustomScan -ScanPath C:\scribe-spike\dist\scribe-host
```

```powershell
Get-MpThreatDetection
```
*Report back:* "nothing", or what is listed. A detection pauses here (C10).

### Swap the Chrome link to the machine-wide copy

> **From step 7 on, your everyday Chrome link is changed.** If any step from 7 onwards fails, or you need to stop for any reason, go straight to **Put everything back** (steps 20–25). Run all of them, in order, before you report.
>
> Each of those steps is safe to run whatever you had reached. A step that finds nothing to undo says so, and that is fine.

4. Close Clinic Scribe and Chrome completely:

```powershell
Get-Process scribe-app, scribe-host, pythonw, chrome -ErrorAction SilentlyContinue
```
*What you should see:* nothing.

4a. Check that this computer has **no** machine-wide Chrome link for Clinic Scribe yet, in either registry view. Nothing has been changed so far, so if either check shows a value, stop and report it.

```powershell
reg query "HKLM\SOFTWARE\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" /reg:64
```

```powershell
reg query "HKLM\SOFTWARE\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" /reg:32
```
*What you should see:* both say `ERROR: The system was unable to find the specified registry key or value.`

4b. Check that the two folders the spike may create do not exist yet. If either says `True`, stop and report it.

```powershell
Test-Path "C:\Program Files\ClinikoScribe"
```

```powershell
Test-Path C:\ClinikoScribe
```
*What you should see:* `False` both times.

4c. Clear the spike's pipe file from any earlier try. It prints nothing, whether or not the file was there:

```powershell
Remove-Item "$env:TEMP\scribe-spike-host-stdio.txt" -ErrorAction SilentlyContinue
```

```powershell
Test-Path "$env:TEMP\scribe-spike-host-stdio.txt"
```
*What you should see:* `False`. If it says `True`, an earlier spike host is still running: repeat step 4's check, then both commands.

5. Check that today's per-user link is exactly the one the project's setup makes. This is the state step 23 puts back. Record it:

```powershell
reg query "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" /ve
```

Then check it:

```powershell
(Get-ItemProperty "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" -ErrorAction SilentlyContinue).'(default)' -eq "$env:LOCALAPPDATA\ClinikoScribe\com.scribe.cliniko_host.json"
```
*What you should see:* `True`. If it says `False`, the link is missing or points somewhere unexpected, so your everyday Chrome link may already not be working. **Stop here and report** both outputs. Nothing has been changed yet.

6. Save a copy of it (step 18 and step 23 put it back from this copy):

```powershell
reg export "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" C:\scribe-spike\hkcu-host-backup.reg /y
```
*What you should see:* `The operation completed successfully.` If not, stop and report. Nothing has been changed yet.

7. Remove the per-user link. The host program and its manifest stay where they are; only the registry key goes.

```powershell
reg delete "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" /f
```

8. **Elevated.** Make the install folder. Once it is made, the command notes that down in `C:\scribe-spike\created-folders.txt`. Step 22 removes a folder only if it is in that note, so it can never remove one the spike did not make.

```powershell
try { New-Item -ItemType Directory "C:\Program Files\ClinikoScribe" -ErrorAction Stop | Out-Null; Add-Content C:\scribe-spike\created-folders.txt "C:\Program Files\ClinikoScribe" -ErrorAction Stop; "Made and noted down." } catch { "NOT done: go to Put everything back." }
```
*What you should see:* `Made and noted down.`

9. **Elevated.** Put the host manifest in it:

```powershell
Copy-Item "C:\Recording clinic software\packaging\spike\host-manifest-programfiles.json" "C:\Program Files\ClinikoScribe\com.scribe.cliniko_host.json"
```

10. **Elevated.** Copy the packaged host beside it:

```powershell
Copy-Item -Recurse -Path C:\scribe-spike\dist\scribe-host\* -Destination "C:\Program Files\ClinikoScribe"
```

11. **Elevated.** Register it for the whole machine:

```powershell
reg add "HKLM\SOFTWARE\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" /ve /t REG_SZ /d "C:\Program Files\ClinikoScribe\com.scribe.cliniko_host.json" /f /reg:64
```

12. Check it landed (a normal window is fine):

```powershell
reg query "HKLM\SOFTWARE\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" /ve /reg:64
```
*What you should see:* `(Default)    REG_SZ    C:\Program Files\ClinikoScribe\com.scribe.cliniko_host.json`.

### The connection check

13. Start your **everyday** app by double-clicking `C:\Recording clinic software\.venv\Scripts\scribe-app.exe` in Explorer. Then open Chrome.

    Expect the app's Status tab to say the Chrome link is **not registered**: it only reads the per-user key, which you just removed. That is the gap D9 fixes. Report the line.

14. Wait up to 30 seconds and look at the pinned Clinic Scribe icon. If it still shows grey **OFF**, open your Cliniko home page once. Do not open any patient.

    *Report back:* the badge: **OK**, **OFF**, **ERR** or **!**.

15. Read the host's log in your real data folder:

```powershell
Select-String -Path "$env:LOCALAPPDATA\ClinikoScribe\logs\scribe-host.log" -Pattern "host_start|host_manifest|origin_verified|origin_rejected|uncaught_exception" | Select-Object -Last 6
```
*What you should see:*
- a `host_start path=C:\Program Files\ClinikoScribe\scribe-host.exe` line;
- then `host_manifest state=unreadable`, which is expected because the host also reads only the per-user key (D9);
- then `origin_verified state=ok`.

*Report back:* the lines.

16. Read the pipe line the packaged host wrote:

```powershell
Get-Content "$env:TEMP\scribe-spike-host-stdio.txt"
```
*Report back:* the line. It says whether Chrome's pipes reached the host as missing streams (`stdin=None`) and whether the adaptation rebuilt them (`rebuilt`) or left them alone (`kept`).

17. Confirm the app saw the packaged host connect:

```powershell
Select-String -Path "$env:LOCALAPPDATA\ClinikoScribe\logs\scribe-app.log" -Pattern "pipe_peer" | Select-Object -Last 2
```
*What you should see:* `pipe_peer path=C:\Program Files\ClinikoScribe\scribe-host.exe`.

**If the badge is not OK**, check two things before the fallback:
- Was there a `host_start` line with the Program Files path in step 15? If yes, Chrome did start the host, and the problem is the pipes, not the folder.
- Open `chrome://extensions` → Clinic Scribe Companion → **service worker** → Console, and report its last red line. *"Specified native messaging host not found"* means Chrome did not accept the location.

**Only** in that second case, try the fallback folder:
1. Close Chrome and the app.
2. **Elevated**, one command each. The first makes the folder and notes it down, as in step 8; it should say `Made and noted down.`

```powershell
try { New-Item -ItemType Directory C:\ClinikoScribe -ErrorAction Stop | Out-Null; Add-Content C:\scribe-spike\created-folders.txt "C:\ClinikoScribe" -ErrorAction Stop; "Made and noted down." } catch { "NOT done: go to Put everything back." }
```

```powershell
icacls C:\ClinikoScribe /inheritance:r /grant:r "*S-1-5-32-544:(OI)(CI)F" "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-545:(OI)(CI)RX"
```

```powershell
Copy-Item "C:\Recording clinic software\packaging\spike\host-manifest-c-root.json" C:\ClinikoScribe\com.scribe.cliniko_host.json
```

```powershell
Copy-Item -Recurse -Path C:\scribe-spike\dist\scribe-host\* -Destination C:\ClinikoScribe
```

```powershell
reg add "HKLM\SOFTWARE\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" /ve /t REG_SZ /d "C:\ClinikoScribe\com.scribe.cliniko_host.json" /f /reg:64
```

```powershell
icacls C:\ClinikoScribe
```
3. The last command should list only `BUILTIN\Administrators:(OI)(CI)(F)`, `NT AUTHORITY\SYSTEM:(OI)(CI)(F)` and `BUILTIN\Users:(OI)(CI)(RX)`.
4. Repeat steps 13–17, with `C:\ClinikoScribe` in place of the Program Files path.

*Report back:* which folder gave a green OK.

### Does a per-user link override the machine one?

18. Close Chrome (leave the app open). Check with `Get-Process chrome -ErrorAction SilentlyContinue`, which should show nothing. Then put the per-user link back from the copy saved in step 6:

```powershell
reg import C:\scribe-spike\hkcu-host-backup.reg
```
*What you should see:* `The operation completed successfully.`

19. Open Chrome, wait for the badge, then:

```powershell
Select-String -Path "$env:LOCALAPPDATA\ClinikoScribe\logs\scribe-host.log" -Pattern "host_start" | Select-Object -Last 1
```
*What you should see:* `host_start` with your **everyday** host's path under `AppData\Local\ClinikoScribe`, not the Program Files one. That means the per-user link wins (D9). *Report back:* the line.

### Put everything back (do not skip)

Run steps 20–25 in order. Run them at the end of the task, and also straight away if anything from step 7 on failed or you had to stop.

20. Close Clinic Scribe and Chrome completely. Run the step 4 check until it shows nothing.

21. **Elevated.** Remove the machine-wide link:

```powershell
reg delete "HKLM\SOFTWARE\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" /f /reg:64
```
If it says *unable to find the specified registry key or value*, there was nothing to remove. That is fine.

22. **Elevated.** Remove the spike's install folders: the Program Files one and the fallback one. The command removes a folder only if step 8 (or the fallback's first command) noted it down, and then checks it is really gone:

```powershell
foreach ($p in "C:\Program Files\ClinikoScribe", "C:\ClinikoScribe") { if (-not (Test-Path $p)) { "${p}: nothing to remove." } elseif ((Get-Content C:\scribe-spike\created-folders.txt -ErrorAction SilentlyContinue) -notcontains $p) { "${p}: NOT removed - the spike did not make this folder." } else { try { Remove-Item -Recurse -Force $p -ErrorAction Stop } catch {}; if (Test-Path $p) { "${p}: NOT fully removed - something still has a file open." } else { "${p}: removed." } } }; "Continue with step 23."
```
*What you should see:* one line per folder, each `removed.` or `nothing to remove.`, then `Continue with step 23.` Whatever it says, continue with step 23. Then:
- *NOT fully removed*: after step 25, run step 20's check again and repeat this step.
- *NOT removed - the spike did not make this folder*: leave it alone and report it.

23. In a **normal** (not elevated) window, put your everyday per-user link back from the copy saved in step 6. If you stopped before step 7, the link was never removed, and this simply rewrites the same value.

```powershell
reg import C:\scribe-spike\hkcu-host-backup.reg
```
*What you should see:* `The operation completed successfully.` If it says the file cannot be found, you stopped before step 6, so the link was never removed. Continue with the check below.

Check the link is exactly as step 5 found it:

```powershell
(Get-ItemProperty "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" -ErrorAction SilentlyContinue).'(default)' -eq "$env:LOCALAPPDATA\ClinikoScribe\com.scribe.cliniko_host.json"
```
*What you should see:* `True`. If it says `False`, stop and report it. Keep `C:\scribe-spike`: it holds the copy.

24. Remove the spike's pipe file (this prints nothing, whether or not the file was there):

```powershell
Remove-Item "$env:TEMP\scribe-spike-host-stdio.txt" -ErrorAction SilentlyContinue
```

25. Start your everyday app and Chrome as normal. The badge should be green **OK**, and the Status tab should show the Chrome link registered again. *Report back:* both.

---

## Task 0.3 — Installer mechanics (Inno Setup)

**What this answers:**
- whether an Inno Setup installer that asks for admin rights installs for the whole machine;
- how long it takes to check a 2.3 GB file's fingerprint;
- which registry value forms land as written;
- who can change the install folder;
- whether a newer build installs over an older one in place.

The spike installer installs one text file into `C:\Program Files\ClinikoScribeInnoSpike`. Every registry value it writes uses a made-up name (`inno-spike-app.exe`, `ClinikoScribeSpike…`), so nothing real is excluded or changed. Uninstalling removes all of it.

> **If any step from 4 onwards fails, or you need to stop**, run the uninstall in step 14 before you report. If step 14 says the file cannot be found, the spike was never installed and there is nothing to undo.

### Before you start

**A.** Is Inno Setup 6 already on this computer?

```powershell
Test-Path "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
```
- `True`: skip step 1 and use the copy you have. Do not install over it. Step 2 shows its version.
- `False`: step 1 installs it.

**B.** Check that nothing from an earlier try of this spike is left. Run all five commands below:

```powershell
Test-Path "C:\Program Files\ClinikoScribeInnoSpike"
```

```powershell
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{5B7E2C1D-9A4F-4E8B-B3C6-2F1D0A9E7C54}_is1"
```

```powershell
reg query "HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting\ExcludedApplications" /v inno-spike-app.exe
```

```powershell
reg query "HKLM\SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToBackup" /f ClinikoScribeSpike
```

```powershell
reg query "HKLM\SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToSnapshot" /f ClinikoScribeSpike
```
*What you should see:*
- the first says `False`;
- the next two say `ERROR: The system was unable to find the specified registry key or value.`;
- the last two say `End of search: 0 match(es) found.`

If any of them shows something, an earlier try of this spike left it behind. Clear it like this:
1. If `C:\Program Files\ClinikoScribeInnoSpike\unins000.exe` exists, run step 14's uninstall command.
2. Run the five checks again.
3. If anything is still shown, stop and report it.

These names belong only to this spike, so nothing else can own them.

1. Only if check A said `False`: install **Inno Setup 6.7.1** from its official site, <https://jrsoftware.org/isdl.php>, with the default options. That is the version GitHub's build machines carry (checked 2026-10-02), so your local builds match the CI build. If the site offers only a newer 6.x, install that instead.

   Inno Setup stays installed for the later build tasks, which use it. If you decide not to keep it, remove it from Settings → Apps → Inno Setup. *Report back:* whether you installed it, and the exact version.

2. Compile the first spike installer, from the project folder in a normal window:

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVer=0.0.1 packaging\spike\inno-spike.iss
```
*What you should see:* `Successful compile`. The first lines also show the compiler's version.

3. Compile the second one, the "upgrade":

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVer=0.0.2 packaging\spike\inno-spike.iss
```

4. Run the first installer. It times the fingerprint check over the language-model copy in your Task 0.1 scratch folder.

```powershell
& C:\scribe-spike\inno-out\inno-spike-0.0.1.exe
```
*What you should see:*
1. A Windows admin prompt (**Yes**).
2. A **Spike hash test** box. *Report back:* its milliseconds and the "Matches" answer, which should be **yes**.
3. The installer pages. Click through them and Finish.

5. Check that the install was per machine:

```powershell
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{5B7E2C1D-9A4F-4E8B-B3C6-2F1D0A9E7C54}_is1" /v DisplayVersion
```
*What you should see:* `0.0.1`.

6. Check that nothing was installed per user:

```powershell
reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{5B7E2C1D-9A4F-4E8B-B3C6-2F1D0A9E7C54}_is1"
```
*What you should see:* `ERROR: The system was unable to find the specified registry key or value.`

7. Check the machine crash-report value:

```powershell
reg query "HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting\ExcludedApplications" /v inno-spike-app.exe
```
*What you should see:* `REG_DWORD    0x1`.

8. Check the backup value forms:

```powershell
reg query "HKLM\SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToBackup" /f ClinikoScribeSpike
```

9. Check the snapshot value forms:

```powershell
reg query "HKLM\SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToSnapshot" /f ClinikoScribeSpike
```
*What you should see (steps 8 and 9):* three values in each (`_UserProfile`, `_EnvVar`, `_Expanded`), all `REG_MULTI_SZ`. *Report back:* all six lines exactly. They show whether `$UserProfile$` and `%LOCALAPPDATA%` land word for word, and what Inno's own folder name expanded to.

   **The limit of this check:** it proves what was written, not what Windows backup honours. Whether `FilesNotToBackup` understands `$UserProfile$` is answered from Microsoft's documentation ("Registry Keys and Values for Backup and Restore"), not by this spike. Windows 11 Home has no Windows Server Backup to observe it with. That reading is recorded on the task, and the docs keep calling these exclusions best-effort (C5).

10. Check who can change the install folder:

```powershell
icacls "C:\Program Files\ClinikoScribeInnoSpike"
```
*Report back:* the lines. Expected: Administrators, SYSTEM and TrustedInstaller have full control (`F`); Users have only read & execute (`RX`).

11. In a normal (**not** elevated) window, try to write into it:

```powershell
New-Item -ItemType File "C:\Program Files\ClinikoScribeInnoSpike\user-write-probe.txt"
```
*What you should see:* an *Access to the path … is denied* error. That is the result we want. If the file is created instead, report it, and remove it in an **elevated** window so step 14's uninstall can remove the folder:

```powershell
Remove-Item "C:\Program Files\ClinikoScribeInnoSpike\user-write-probe.txt"
```

12. Run the upgrade over the top:

```powershell
& C:\scribe-spike\inno-out\inno-spike-0.0.2.exe
```
*Report back:*
- the hash box's milliseconds (a second, warm-cache reading);
- whether the installer asked you to choose a folder (expected: no — it reuses the first one).

13. Check the upgrade replaced the old version in place:

```powershell
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{5B7E2C1D-9A4F-4E8B-B3C6-2F1D0A9E7C54}_is1" /v DisplayVersion
```

```powershell
Get-ChildItem "C:\Program Files\ClinikoScribeInnoSpike"
```
*What you should see:* `0.0.2`, and one `unins000.exe` (not `unins001.exe`). Settings → Apps lists **ClinikoScribe Inno Spike** once.

14. Uninstall it:

```powershell
& "C:\Program Files\ClinikoScribeInnoSpike\unins000.exe"
```
Then run the five checks in **Before you start B** again. *What you should see:* the same results as before the spike: `False`, two `unable to find` errors and two `0 match(es) found`. *Report back:* that they match. If any still shows something, report which one; do not delete it by hand.

**If the language-model copy is no longer in the scratch folder**, make a 2.5 GB test file instead:

```powershell
$f = [IO.File]::OpenWrite('C:\scribe-spike\big.bin'); $b = New-Object byte[] (64MB); (New-Object Random 1).NextBytes($b); 1..40 | ForEach-Object { $f.Write($b, 0, $b.Length) }; $f.Close()
```

Compile against it. It has no expected value, so the box only reports the time:

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVer=0.0.1 /DHashFile=C:\scribe-spike\big.bin /DHashExpected= packaging\spike\inno-spike.iss
```

**Already answered, nothing for you to do:** GitHub's build machines carry Inno Setup 6.7.1 and the Microsoft C++ build tools. This covers `windows-latest` (Windows Server 2025), `windows-2025` and `windows-2022`, checked 2026-10-02 in GitHub's published image lists. The details are recorded on Task 0.3 in the plan.

---

## Task 0.4 — The speaker model's licence

**What this answers:** whether the speaker model (WeSpeaker VoxCeleb ResNet34-LM, ONNX export) may be shipped inside the model pack. Decision D-I2 waits on it.

**Already answered on 2026-10-02 — nothing for you to run.** The model is published under **Creative Commons Attribution 4.0 International (CC BY 4.0)**.
- **The model's own page** (the one `scripts/setup-models.py` downloads from) gives that licence: <https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM>.
- **The WeSpeaker project's "Model License" section** says its VoxCeleb models follow the VoxCeleb dataset's CC BY 4.0 licence: <https://github.com/wenet-e2e/wespeaker/blob/master/docs/pretrained.md>.

**One point for you to weigh** under decision D-I2: the VoxCeleb dataset page describes the dataset as available "for research purposes" under that licence. The full source list and this caveat are recorded on Task 0.4 in the plan.

---

## What to send back

One message, with these in order:
1. **0.1:**
   - real folder BEFORE and AFTER, and whether they match;
   - the Python version, and whether you needed the 3.12 fallback;
   - PyInstaller and hooks versions, and route 6a (both hashes) or 6b;
   - the `Compare-Object` lines (what the PyInstaller install added or changed);
   - build success, plus any `SPIKE-FILTERED` or `ERROR` lines;
   - the warn-file lines;
   - steps 10 and 11;
   - the whole `checks.txt` and `stdio.txt`;
   - the self-test, Status warnings, benchmark `medium` line and Practitioner model lines;
   - the log lines from step 20.
2. **0.5:** the Defender result and the Smart App Control setting (plus the optional registry value).
3. **0.2:**
   - which environment built the host (step 2: the build copy or `venv312`);
   - the old HKCU value and step 5's `True`;
   - the Defender result for the host;
   - the badge;
   - the host-log, stdio and `pipe_peer` lines;
   - which folder worked;
   - the shadow check line;
   - that step 23's check says `True`, and the badge is green.
4. **0.3:**
   - whether Inno Setup was already installed or you installed it, and its version;
   - both hash timings and "Matches";
   - the per-machine and per-user checks;
   - the WER value;
   - the six backup/snapshot lines;
   - the `icacls` lines and the write-probe error;
   - the upgrade results;
   - that after uninstall, check B matches what it showed before.
5. **0.4:** nothing; it is answered.
6. **Finishing up:** step 1's result (your everyday Python environment unchanged).

---

## Finishing up

Run this when the tasks are done, or when you stop for good. It only reads your everyday Python environment and then removes the spike's own folder.

1. Check your everyday Python environment was never changed. In a normal window, in the project folder (`Set-Location "C:\Recording clinic software"`):

```powershell
Compare-Object (Get-Content C:\scribe-spike\everyday-before.txt) (.venv\Scripts\python.exe -m pip freeze --all)
```
*What you should see:* nothing. The one exception: a pair of lines for the project itself (`scribe-desktop` / `scribe_desktop`) that differ only in a long commit id. That is expected, because it reflects the project's current version. Any other line: report it, and keep `C:\scribe-spike`.

2. Before deleting the spike folder, make sure Task 0.2 is put back. If you started Task 0.2, its step 23 check must have said `True`. If it did not, or you are not sure, run Task 0.2's **Put everything back** (steps 20–25) now: it needs the copy kept in this folder.

3. When everything is recorded on the plan, close any window that was using the build copy, then delete the spike folder:

```powershell
Remove-Item -Recurse -Force C:\scribe-spike
```

```powershell
Test-Path C:\scribe-spike
```
*What you should see:* `False`. If it says `True`, something still has a file open. Close it and run both commands again.
