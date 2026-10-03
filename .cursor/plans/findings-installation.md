# Review findings — installation

Companion to `plan-installation.md`. It holds the FULL review round blocks that the plan carries only as digests.

**Lifecycle:** this file and its companion plan are ONE unit — move, archive or delete them together. A round present here must have its digest (or, mid-recovery, its full copy) in the plan; a round digest in the plan must have its full block here.

### Round 1 - 2026-10-02 - installation plan, independent cross-family codex plan peer-review (round 1)

- Round status: Closed
- Source: Codex plan peer-review
- Materiality: 3 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: `7849dc4` + working-tree plan
- Files read: Full `.cursor/plans/plan-installation.md`; `.agents/skills/peer-review/SKILL.md`; scoped passages in `AGENTS.md`, `PLAN.md`, `docs/lessons.md`, and the three named security documents. Scoped symbols in `desktop/src/scribe_desktop/`: `identity.py`, `protocol.py`, `exclusions.py`, `app.py`, `benchmark.py`, `native_host.py`, `framing.py`, `status.py`, `secure_storage.py`, `pipe_server.py`, `draft_write.py`, `ui/models.py`, `transcription.py`, `language_model.py`, `speaker_embedding.py`, `clinics.py`. Also `scripts/register-native-host.py`, `scripts/setup-models.py`, `scripts/generate-extension-key.py`, `extension/src/manifest.ts`, `extension/src/protocol.ts`, `extension/vite.config.ts`, `extension/package.json`, `protocol/fixtures/meta.json`, `desktop/pyproject.toml`, `desktop/requirements-ml-prose.txt`, `.github/workflows/ci.yml`, `desktop/tests/conftest.py`, `desktop/tests/test_display_name.py`.
- Finding verification: 8 candidates / 5 dropped / 0 downgraded
- Review method: Static, read-only review. No files changed; no tests or builds run.

#### Findings

##### Practicality / feasibility / sequencing

**PR-MED-001 — `runasoriginaluser` alone does not enforce the prohibition on elevated app launches**

- Plan section: D8, C3, Task 3.6.
- Materiality: build-affecting
- Why it matters: Starting Setup through “Run as administrator” or an already elevated terminal leaves no unelevated original token for this flag to restore. The Finish-page launch can therefore run the application elevated, potentially under a different administrator’s profile. This contradicts the explicit installation contract and can create a separate clinical store under the wrong Windows identity. This limitation is documented by [Inno Setup](https://jrsoftware.org/ishelp/topic_runsection.htm).
- Current plan text:
  - `.cursor/plans/plan-installation.md:362`: “**D8 — The installer writes nothing per-user and never runs the app elevated.**”
  - `.cursor/plans/plan-installation.md:364`: “"Launch Clinic Scribe" uses `runasoriginaluser`.”
  - `.cursor/plans/plan-installation.md:606`: “the Finish page (Flow 2 step 4) and launch via `runasoriginaluser`;”
- Evidence:
  - The [Inno Setup Run-section documentation](https://jrsoftware.org/ishelp/topic_runsection.htm), under `runasoriginaluser`, explicitly describes both pre-elevated launch cases.
  - `desktop/src/scribe_desktop/exclusions.py:222`: `base = layer.environ("LOCALAPPDATA") or str(Path.home())`
  - `desktop/src/scribe_desktop/exclusions.py:223`: `return Path(base) / APP_FOLDER_NAME`
  - These roots follow the launched process’s identity; the app does not recover the intended clinician’s profile from an elevated installer.
- Suggested change: Remove the installer’s application launch and direct the practitioner to the Start menu, or suppress launch unless an unelevated original-user token is positively established. Add practitioner verification for both ordinary UAC elevation and Setup started already elevated.
- /fix decision: Applied — verified (Inno `runasoriginaluser` cannot de-elevate a Setup started already elevated). D8 now says the installer NEVER launches the app; Flow 2 step 5 and Task 3.6 say open it from the Start menu, with a text-pin that the `.iss` has no `[Run]` entry starting `scribe-app.exe`; P.1 step 6 adds a Task Manager "Elevated" check. Landed + siblings reconciled (Flow 2, D8, Task 3.6, P.1). Materiality confirmed build-affecting. Applied by: Claude Code (owning planning session), 2026-10-02.

**PR-MED-002 — The frozen-host spike requires a fix that is deferred until after its completion gate**

- Plan section: Phase 0 Tasks 0.1–0.2; Task 2.2; D-I1.
- Materiality: build-affecting
- Why it matters: Task 0.1 requires the real windowed host to connect successfully, but postpones the missing-stdio adaptation to Phase 2. Windowed PyInstaller applications have unavailable Python standard streams, so the current host fails before logging `origin_verified`. Changing the installation directory cannot resolve that failure. Task 0.1 also depends on the interpreter selected by the later Task 0.2. The prescribed first gate cannot establish the installation-location decision in this order. [PyInstaller documents the standard-stream behavior](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#sys-stdin-sys-stdout-and-sys-stderr-in-noconsole-windowed-applications-windows-only).
- Current plan text:
  - `.cursor/plans/plan-installation.md:474`: “The agent writes a throwaway `packaging/spike/host.spec`: a one-folder windowed `scribe-host.exe` from the real `native_host.main`, built on the Task 0.2 interpreter.”
  - `.cursor/plans/plan-installation.md:476`: “Check that `sys.stdin`/`sys.stdout` exist under the windowed bootloader. If either is None, the fallback (`msvcrt.open_osfhandle(GetStdHandle(...))`) is built into Task 2.2.”
  - `.cursor/plans/plan-installation.md:478`: “Done when: the host log shows `origin_verified` and the badge is green OK from the chosen folder; the result is recorded on this task; the HKCU dev registration is restored afterwards.”
- Evidence:
  - `desktop/src/scribe_desktop/native_host.py:570`: `set_binary_stdio()`
  - `desktop/src/scribe_desktop/native_host.py:571`: `log_event(logger, "origin_verified", state="ok")`
  - `desktop/src/scribe_desktop/framing.py:54`: `msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)`
  - `desktop/src/scribe_desktop/native_host.py:573`: `sys.stdin.buffer, sys.stdout.buffer, logger, relay_factory=app_relay_factory()`
- Suggested change: Select the spike interpreter first. Include the minimal stdio adaptation in the host spike before requiring a successful handshake; let Task 2.2 subsequently integrate and harden that proven implementation. Establish D-I1 only after the adapted host passes from the proposed installation directory.
- /fix decision: Applied — verified (`native_host.py:570-573`, `framing.py:54`). Phase 0 reordered: Task 0.1 is now the frozen-app spike (interpreter + the stdio result), Task 0.2 the frozen host, which carries the minimal stdio adaptation when 0.1 found the streams None; Task 2.2 integrates the proven adaptation; D-I1 decides after Task 0.2. Landed + siblings reconciled (Accepted Assumption, External Findings, D1, handoff, Tasks 0.5, D-I1, 2.1, 2.2, 3.2). Materiality confirmed build-affecting. Applied by: Claude Code, 2026-10-02.

##### Missing verification / rollback / migration

**PR-MED-003 — The early frozen-app spike has no concrete isolation from existing patient stores**

- Plan section: Task 0.2; Phase 1 layout work; C8.
- Materiality: build-affecting
- Why it matters: Phase 0 runs before the new layout abstraction exists. Copying model files does not redirect the application’s data roots. An Explorer launch of the current app under the practitioner’s login reaches the existing clinical stores and performs startup pruning and sweeping before the practitioner can inspect the UI. The spike therefore needs storage isolation before invoking the real application entry point.
- Current plan text:
  - `.cursor/plans/plan-installation.md:479`: “**0.2 Frozen app runtime.** A spike `scribe.spec` building `scribe-app.exe` on Python 3.14 (fallback 3.12). Checks:”
  - `.cursor/plans/plan-installation.md:488`: “The practitioner runs it from Explorer against a COPY of the models (never the dev data).”
  - `.cursor/plans/plan-installation.md:520`: “**1.2 Repoint every data-folder builder** (the table in Key Findings) to `install_layout`. `benchmark.default_models_root` delegates to `models_root()`.”
- Evidence:
  - `desktop/src/scribe_desktop/app.py:569`: `past_sessions = PastSessionStore(logger=logger)`
  - `desktop/src/scribe_desktop/app.py:573`: `sessions_root = default_sessions_root()`
  - `desktop/src/scribe_desktop/app.py:592`: `audit.prune()  # Flow 4: the audit month prune at start-up...`
  - `desktop/src/scribe_desktop/app.py:593`: `run_sweep()  # Flow 3: app start -> sweep BEFORE the recovery list renders`
  - `desktop/src/scribe_desktop/benchmark.py:146`: `return Path(local_app_data) / "ClinikoScribe" / "models"`
  - The current entry point has neither a spike-specific data root nor an argument that selects the copied model directory.
- Suggested change: Define a spike-only harness that binds every store and model root to an isolated scratch profile before invoking application startup, or run the spike under a separate disposable Windows account. Specify that clinical records and credentials are not copied into it. Make isolation a prerequisite to the first spike launch, with a practitioner check that the existing clinical stores remain untouched.
- /fix decision: Applied — verified (`app.py:569-593` opens Past sessions, the sessions root, `audit.prune()` and `run_sweep()` at start-up; every store reads `LOCALAPPDATA`). Task 0.1 now requires launching ONLY from a persistent PowerShell with `$env:LOCALAPPDATA` pointed at a scratch folder, models copied in, nothing clinical copied, and a before/after check that the real data folder is unchanged — chosen over a separate Windows account as the lighter control that the existing code already honours. Landed + siblings reconciled (the old "from Explorer against a COPY of the models" line removed). Materiality confirmed build-affecting. Applied by: Claude Code, 2026-10-02.

PEER-PLAN-ROUND-1 RESULT: 3 findings (CRIT 0 / HIGH 0 / MED 3 / LOW 0; build-affecting 3 / record-only 0 / invalid 0).

### Round 2 - 2026-10-02 - installation plan, independent cross-family codex plan peer-review (round 2)

- Round status: Closed
- Source: Codex plan peer-review
- Materiality: 1 build-affecting / 1 record-only / 0 invalid (owning-session verified; peer's labels were 2 / 0 / 0 — PR-MED-001 reclassified record-only)
- Plan reviewed at: `7849dc4` + working-tree plan
- Files read: Full `.cursor/plans/plan-installation.md`; `.agents/skills/peer-review/SKILL.md`; scoped passages in `AGENTS.md`, `PLAN.md`, `docs/lessons.md`, `docs/security/threat-model.md`, `docs/security/retention-schedule.md`, and `docs/security/data-flow-map.md`. Named symbols in `desktop/src/scribe_desktop/`: `identity.py`, `protocol.py`, `exclusions.py`, `app.py`, `benchmark.py`, `native_host.py`, `framing.py`, `status.py`, `secure_storage.py`, `pipe_server.py`, `draft_write.py`, `ui/models.py`, `transcription.py`, `language_model.py`, `speaker_embedding.py`, and `clinics.py`. Also `scripts/register-native-host.py`, `scripts/setup-models.py`, `scripts/generate-extension-key.py`, `extension/src/manifest.ts`, `extension/src/protocol.ts`, `extension/vite.config.ts`, `extension/package.json`, `protocol/fixtures/meta.json`, `desktop/pyproject.toml`, `desktop/requirements-ml-prose.txt`, `.github/workflows/ci.yml`, `desktop/tests/conftest.py`, and `desktop/tests/test_display_name.py`.
- Finding verification: 7 candidates / 5 dropped / 0 downgraded
- Review method: Static, read-only review. No files changed; no tests or builds run.
- Amendment verification: The installer no-launch amendment and the reordered host-stdio spike resolve their original findings. Task 0.1’s nonempty `LOCALAPPDATA` override isolates the clinical stores under its stated no-copy/no-clinic conditions. Its Credential Manager self-test uses the dedicated `test`/`probe` entry; shared Windows identity alone does not demonstrate clinical-data access. D4 explicitly permits dev verification reads. The remaining isolation gap is the separate Task 0.2 launch path below.

#### Findings

##### Missing verification / rollback / migration

**PR-MED-001 — The host spike does not carry forward isolation to its application and Chrome-launched host**

- Plan section: Phase 0, Task 0.2; Task 0.1 isolation prerequisite.
- Materiality: build-affecting
- Why it matters: Task 0.2 runs before Phase 1 creates the separate dev data root. Following its instruction to run the “dev app” normally therefore opens the existing clinical stores and runs startup pruning and sweeping. Independently, a host launched by an already-running Chrome inherits Chrome’s environment, not Task 0.1’s PowerShell override, and starts logging in the real profile. The Round 1 amendment protects the first spike but does not establish isolation for this adjacent process chain.
- Current plan text: `.cursor/plans/plan-installation.md:564`:
  > The practitioner copies it to `C:\Program Files\ClinikoScribe\` with a manifest there, registers it in HKLM (exact `reg add` lines are given in the task hand-off), removes the HKCU dev registration first, and opens Cliniko with the dev app running.
- Evidence:
  - `desktop/src/scribe_desktop/app.py:569`: `past_sessions = PastSessionStore(logger=logger)`
  - `desktop/src/scribe_desktop/app.py:592`: `audit.prune()  # Flow 4: the audit month prune at start-up...`
  - `desktop/src/scribe_desktop/app.py:593`: `run_sweep()  # Flow 3: app start -> sweep BEFORE the recovery list renders`
  - `desktop/src/scribe_desktop/app.py:621`: `window.past_sessions_screen.run_retention_sweep()`
  - `desktop/src/scribe_desktop/native_host.py:550`: `logger = setup_logging("scribe-host")`
  - `.cursor/plans/plan-installation.md:596` schedules the root conversion later: “**1.2 Repoint every data-folder builder** (the table in Key Findings) to `install_layout`. `benchmark.default_models_root` delegates to `models_root()`.”
- Suggested change: Make the scratch-root/no-clinic protocol a prerequisite for both runtime spikes. Explicitly launch Task 0.2’s application with the scratch root and bind the spike host’s root before `native_host.main`. Specify Chrome shutdown and launch handling, or a spike wrapper, so host isolation does not depend on an existing Chrome process inheriting a shell override. Verify both processes’ roots and leave real patient encounters out of the transport-only badge check.
- /fix decision: Applied (reclassified record-only by the owning session) — verified in part: the "dev app" Task 0.2 runs is today's ordinary app on today's data folder (Phase 1 has not run), exactly as the practitioner uses it daily, so the spike introduces no new data path; the frozen host is today's `native_host` code writing only its content-free log under Chrome's environment. What was missing is the statement of that scope: Task 0.2 now says the check is TRANSPORT-ONLY (badge green OK; no recording, nothing written) and why app isolation is not required there. Landed; siblings: none (Task 0.1's isolation contract is unchanged). Applied by: Claude Code (owning planning session), 2026-10-02.

##### Practicality / feasibility / sequencing

**PR-MED-002 — Several task completion gates still require artifacts assigned to later tasks**

- Plan section: Tasks 1.3–1.4 and 3.2–3.6.
- Materiality: build-affecting
- Why it matters: The Phase 0 ordering correction does not close this class across the remaining plan. Task 1.3 needs the identity generated in 1.4. Task 3.2 cannot satisfy its audit gate before 3.4 creates that audit, and 3.3 invokes the same later builder. Most concretely, Task 3.5 requires a successful, attested installer build before Task 3.6 supplies the installer script. Sequential execution must either stop or implement later tasks early without an explicit dependency order.
- Current plan text:
  - `.cursor/plans/plan-installation.md:601`:
    > dev values: `com.scribe.cliniko_host_dev`, the dev ID from Task 1.4's key, and `ClinikoScribe-dev-`.
  - `.cursor/plans/plan-installation.md:659`:
    > Done when: `pyinstaller packaging/scribe.spec` builds on the composer's machine, and Task 3.4's audit passes.
  - `.cursor/plans/plan-installation.md:664`:
    > `build-release.py --model-pack` copies `build/models` into `ClinikoScribe-models-<sha8>/` and verifies it against the manifest.
  - `.cursor/plans/plan-installation.md:675`:
    > Done when: one green run is attested and `gh attestation verify` passes (practitioner); the existing `ci.yml` is unchanged.
- Evidence:
  - `scripts/generate-extension-key.py:29`: `KEY_PEM = REPO / "extension" / "key.pem"`
  - `desktop/src/scribe_desktop/identity.py:15`: `EXTENSION_ID = "mbmhglgadhdohpgbmpbjnaifjagfdfid"`
  - `.cursor/plans/plan-installation.md:608` assigns generation of the new identity to the later task: “`scripts/generate-extension-key.py --out extension/key-dev.pem` (gitignored); the dev PUBLIC key is committed.”
  - `.cursor/plans/plan-installation.md:665` introduces “**3.4 `scripts/build-release.py`.**”
  - `.cursor/plans/plan-installation.md:676` introduces “**3.6 `packaging/scribe.iss`** (D1, D5, D6, D8, D-I1). It covers:”
- Suggested change: Extract dev-key generation before Task 1.3. Give Phase 3 an explicit dependency order: build lock, spec and manifest, audit/model-pack helpers, installer script, complete release builder, then the green CI/attestation gate. Alternatively, distinguish implementation tasks from later integration gates and state that the earlier tasks are not blocked on those gates. Reconcile the task numbers and references together.
- /fix decision: Applied — verified. Task 1.3 is now the extension mode + dev key (the key is generated FIRST and the dev ID recorded), Task 1.4 the identity accessors consuming it. Phase 3 is in dependency order: 3.1 lock → 3.2 spec (builds; not blocked on the audit) → 3.3 models manifest (the pack copy moved out) → 3.4 `scribe.iss` → 3.5 `build-release.py` (audit, `--model-pack`, ISCC over 3.4; its local audited build is 3.2's integration gate) → 3.6 the CI release job. Landed + siblings reconciled (Validation `npm run qa` tasks, Config uninstall note, Task 0.3 Done-when, D-I1 Blocks, Task 1.4's dev-ID line). Applied by: Claude Code, 2026-10-02.

PEER-PLAN-ROUND-2 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 2 / LOW 0; build-affecting 2 / record-only 0 / invalid 0).

### Round 3 - 2026-10-02 - installation plan, independent cross-family codex plan peer-review (round 3)

- Round status: Closed — No new findings this round
- Source: Codex plan peer-review
- Materiality: 0 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: `7849dc4` + working-tree plan
- Files read: Full `.cursor/plans/plan-installation.md`, including Rounds 1–2; `.agents/skills/peer-review/SKILL.md`; scoped passages in `AGENTS.md`, `PLAN.md`, `docs/lessons.md`, and the three named security documents. Named symbols in `desktop/src/scribe_desktop/`: `identity.py`, `protocol.py`, `exclusions.py`, `app.py`, `benchmark.py`, `native_host.py`, `framing.py`, `status.py`, `secure_storage.py`, `pipe_server.py`, `draft_write.py`, `ui/models.py`, `transcription.py`, `language_model.py`, `speaker_embedding.py`, and `clinics.py`; additionally the two write-call sites in `ui/main_window.py`. Also the three named scripts, extension manifest/protocol/Vite/package files, `protocol/fixtures/meta.json`, `desktop/pyproject.toml`, `desktop/requirements-ml-prose.txt`, `.github/workflows/ci.yml`, `desktop/tests/conftest.py`, and `desktop/tests/test_display_name.py`.
- Finding verification: 8 candidates / 8 dropped / 0 downgraded
- Review method: Static, read-only review across all five lenses. No files changed; no tests or builds run.

#### Findings

None survived verification.

- **Amendments:** Dev-key generation now precedes its consumers; preserving the generator’s default leaves existing `key.pem` references valid. Phase 3’s manifest precedes the installer constants and text-pin test. Task 0.2 uses the ordinary application and its existing stores; its clarification does not introduce another storage path. Ordinary startup maintenance still occurs, so “nothing is written” describes the clinical action, not literal filesystem inactivity.
- **Integrity:** The separately produced model pack is anchored through the committed per-file manifest compiled into the attested installer. Substituting model bytes cannot satisfy those expected hashes. Installation verification plus the required admin-only directory addresses the acknowledged absence of Whisper/silero load-time hashing.
- **Dev writes:** Both application write-entry checks reach `refuse_before_read`; retry reconciliation follows that check inside `prepare_write`. The proposed guard is an intentional, overridable developer setting. No additional application bypass was established.
- **Registry:** HKCU-before-HKLM matches the inspected [Chromium implementation](https://chromium.googlesource.com/chromium/src/%2B/57c3662e332095c8e7d98255d86e29d3a86c530c/chrome/browser/extensions/api/messaging/native_process_launcher_win.cc). The suspected independent HKCU registry-view residue was dropped: this `HKCU\Software` branch is shared across views under [Windows’ WOW64 rules](https://learn.microsoft.com/en-us/windows/win32/winprog64/shared-registry-keys). Task 3.7 explicitly removes the production-name registration before the dev name is registered.
- **Claims and rollback:** The fallback ACL requirement, best-effort exclusion wording, same-AppId upgrade, installed-model recheck and practitioner rollback smoke cover the examined concerns. No concrete defect requiring another build task was established.

PEER-PLAN-ROUND-3 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0; build-affecting 0 / record-only 0 / invalid 0).

### Round 4 - 2026-10-02 - Phase 0 spike inputs and runbook, independent cross-family codex peer review (pass stage-0.p1)

- Round status: Closed
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: All packaging/spike files, specified Phase 0 plan sections, and permitted production symbols; static read-only review, without builds, tests, registry execution or network access.

#### Findings

- **PR-MED-004** (MED, behavioral, `packaging/spike/RUNBOOK.md:12`): The failure instruction can leave the everyday Chrome link removed or pointing at the spike: it tells the clinician to stop immediately, without routing failures after mutation through restoration. — Evidence: “If any step fails, stop there and report the step number”; line 398 deletes the HKCU registration, while restoration does not begin until line 519, “Put everything back (do not skip)”. Recommendation: Fix-now — Provide an explicit failure-recovery branch after the first mutation, with commands conditional on which steps completed; require restoration before stopping to report. /fix decision: Applied.
  - /fix notes:
    - `RUNBOOK.md` "Read this first": the failure rule now routes Task 0.2 (from step 7) through "Put everything back" (steps 20–25) and Task 0.3 (from step 4) through step 14 before reporting. It also states that Task 0.1 changes nothing outside `C:\scribe-spike` except the venv.
    - A callout above 0.2 step 4 gives the same route.
    - The restore steps were made safe to run from any point: step 21's "not found is fine" line, step 22's guarded removal (see PR-MED-005), and step 24 `-ErrorAction SilentlyContinue`.
    - Siblings:
      - the 0.2 fallback block and step 18 are covered by the same restore (step 21 deletes the one HKLM key, step 22 removes either folder, and step 23 recreates the HKCU key);
      - the 0.3 steps 4–12 installed-spike state has a callout routing to step 14;
      - the 0.1 venv install gained a `pip check` step and an exact `pip uninstall -y pyinstaller pyinstaller-hooks-contrib` undo (it names only those two: helper packages such as `pywin32-ctypes` may be keyring's own dependency, so they are not removed).
    - Verified by re-reading every changed step in context. No command was executed: C7, the practitioner runs it.
  - /fix date: 2026-10-02
  - /fix applied by: Claude Code

- **PR-MED-005** (MED, behavioral, `packaging/spike/RUNBOOK.md:422`): The HKLM registration is overwritten without checking or preserving its previous state, then deleted during cleanup, so the procedure cannot restore an existing machine registration. — Evidence: line 422 uses `reg add "HKLM\SOFTWARE\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" … /f /reg:64`; line 526 uses `reg delete "HKLM\SOFTWARE\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" /f /reg:64`. The backup at line 392 covers HKCU only. Recommendation: Fix-now — Before changing either registration, record its existence and preserve any existing key in the applicable registry view; restore that state exactly, or require the machine key to be absent before proceeding. /fix decision: Applied.
  - /fix notes (the "require absent" option):
    - The new 0.2 step 4a queries the HKLM key in BOTH `/reg:64` and `/reg:32` before any change and stops if either exists, so step 21's delete restores the prior (absent) state exactly and a 32-bit-view key cannot confound the result.
    - The new step 4b requires both spike folders to be absent (`Test-Path` False).
    - Sibling (step 22's unconditional `Remove-Item -Recurse -Force`): it is now a single guarded command per folder that removes the folder only if it holds the spike manifest ("installation spike", present in both `host-manifest-*.json` descriptions) or is empty, and otherwise prints "NOT removed … Report it".
    - Steps 9/10, and the fallback block's two copies, were reordered so the manifest marker lands BEFORE the host files. Any partial copy is therefore recognisable.
    - 0.3's made-up value names cannot collide (no change).
    - Verified by re-reading the commands. PowerShell 5.1 semantics checked by reading: `-Quiet` with `-ErrorAction SilentlyContinue` on a missing file is falsy, and `-not (Get-ChildItem <empty>)` is true.
  - /fix date: 2026-10-02
  - /fix applied by: Claude Code

- **PR-MED-006** (MED, docs-only, `packaging/spike/RUNBOOK.md:107`): The compiler-discovery fallback directs the clinician to run PowerShell syntax in a Command Prompt, where it fails. — Evidence: line 105 gives `& "C:\Recording clinic software\.venv\Scripts\python.exe" ./waf all --target-arch=64bit`; line 107 says “run the same command from **x64 Native Tools Command Prompt for VS** instead”. The leading `&` is PowerShell’s invocation operator, not valid CMD invocation syntax. Recommendation: Fix-now — Supply the exact CMD commands, including `cd /d` into the bootloader folder and the quoted Python invocation without the leading `&`. /fix decision: Applied.
  - /fix notes:
    - In 0.1 step 6a, the compiler fallback is now a numbered procedure for **x64 Native Tools Command Prompt for VS**. It is labelled "a Command Prompt, not PowerShell" and has two `bat` blocks: `cd /d C:\scribe-spike\pyinstaller-src\bootloader`, then `"C:\Recording clinic software\.venv\Scripts\python.exe" ./waf all --target-arch=64bit` with no `&`. It then says to return to the PowerShell window.
    - Siblings: none (the only cmd-hosted instruction).
  - /fix date: 2026-10-02
  - /fix applied by: Claude Code

- **PR-LOW-007** (LOW, docs-only, `packaging/spike/RUNBOOK.md:245`): The description of the checks file understates what it contains: exception messages are included, not merely error type names and fixed measurements. — Evidence: “the whole file (it holds only fixed words, numbers and error type names)”; `packaging/spike/spike_checks.py:56` instead reads `text = " ".join(str(exc).split())`, and line 57 returns `f"{type(exc).__name__}: {text[:300]}"`. Recommendation: Fix-now — Describe the exception-message output accurately, including possible paths and library diagnostics, and tell the practitioner to inspect it before sharing. /fix decision: Applied.
  - /fix notes:
    - `RUNBOOK.md` step 16's report line now says: read it before sending; it holds fixed words and numbers plus, for a FAILED check, the error's type and message, which can include a file path (possibly with the Windows user name) or library text; it never holds patient information; blank out anything you would rather not share.
    - Sibling: the `spike_app_entry.py` module docstring was corrected the same way (stdio.txt fixed words only; checks.txt messages can carry paths or diagnostics). Re-read for syntax; it is a docstring-only change.
    - `spike_checks.py`'s docstring was already accurate.
  - /fix date: 2026-10-02
  - /fix applied by: Claude Code

- Verification counts: 8 claims checked, 4 confirmed, 4 dropped as unverifiable
- Last reviewed: 2026-10-02

#### LEG 1 verified tuples

Executor leg i0-x3, 2026-10-02T12:29+10:00, verification only. Nothing was fixed. Each claim was checked against the current `packaging/spike/` files. Every finding is CONFIRMED. All four recommendations are Fix-now; two severities are downgraded, with the evidence in the line.

- PR-MED-004: materiality=behavioral severity=verified med surface=production rec=Fix-now — CONFIRMED. final=Applied (LEG 2 leg i0-x4, all listed siblings included).
  - The cited lines:
    - `RUNBOOK.md:12` reads "If any step fails, stop there and report the step number and what the screen says";
    - `:398` (0.2 step 7) deletes the HKCU link (`reg delete "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" /f`);
    - restoration starts only at `:519` ("Put everything back (do not skip)").
  - So any failure in 0.2 steps 8–17 or the fallback, followed by "stop there", leaves the everyday app's Chrome link removed (the badge OFF on a clinic day), and possibly an HKLM key and spike files in Program Files, until someone works out to run steps 20–25.
  - It is recoverable (step 23's `register-native-host.py` restores it, and nothing is lost), so MED stands.
  - siblings=
    - 0.2 steps 8–11 and the fallback block (`:477-497`) mutate with no per-step undo;
    - 0.2 step 18 (`:509`) re-adds HKCU mid-test;
    - 0.3 steps 4 and 12 install the spike, which stays installed with its HKLM values until step 14 (made-up names, harmless, but no failure branch);
    - 0.1 steps 6a/6b install PyInstaller into the everyday `.venv` with no undo line (`:125`, `:131`).
- PR-MED-005: materiality=behavioral severity=verified low (peer MED) surface=test-harness rec=Fix-now — CONFIRMED. final=Applied (LEG 2 leg i0-x4, step-22 sibling included).
  - The cited lines:
    - `:422` writes `reg add "HKLM\SOFTWARE\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host" … /f /reg:64` without first querying either view;
    - `:526` deletes it unconditionally;
    - the only backup, `:392`, is HKCU.
  - Downgrade evidence:
    - this project has never written an HKLM key (`register-native-host.py` is HKCU-only, and no installer exists yet), so a pre-existing machine key is unlikely, though not verified;
    - after restore (step 23) the HKCU key wins, so the everyday Chrome link works whatever HKLM holds. The everyday app is unaffected; only machine state outside the app could be lost.
  - **Sharper consequence:** a stray 32-bit-view HKLM key would never be seen, and could confound the 0.2 result itself. The runbook never queries `/reg:32`.
  - Fix: a cheap precondition — `reg query … /ve /reg:64` and `/reg:32`, and stop if either exists.
  - siblings=
    - 0.2 step 22 (`:532`, `:537`) removes `C:\Program Files\ClinikoScribe` / `C:\ClinikoScribe` with `-Recurse -Force` without confirming that the spike created them. Step 8's `New-Item` without `-Force` would have errored on an existing folder, but under PR-MED-004's "stop" rule nothing records that.
    - 0.3 steps 7–9 use made-up value names, so they cannot collide (none there).
- PR-MED-006: materiality=docs-only severity=verified low (peer MED) surface=docs rec=Fix-now — CONFIRMED. final=Applied (LEG 2 leg i0-x4; no siblings).
  - The cited lines:
    - `:105` is `& "C:\Recording clinic software\.venv\Scripts\python.exe" ./waf all --target-arch=64bit`;
    - `:107` says "run the same command from **x64 Native Tools Command Prompt for VS** instead, in the same folder".
  - In cmd, `&` is a command separator, so the line fails, and a new prompt also does not open "in the same folder" (it needs `cd /d C:\scribe-spike\pyinstaller-src\bootloader`).
  - Downgrade evidence: the failure is loud and changes nothing (no state is mutated before or by it), and line 12 routes it to a report. It costs a round-trip, not a wrong state.
  - siblings=none. This is the only cmd-hosted instruction; every other block runs in PowerShell, where `&`, `$env:` and `${env:ProgramFiles(x86)}` are valid.
- PR-LOW-007: materiality=docs-only severity=verified low surface=docs rec=Fix-now — CONFIRMED. final=Applied (LEG 2 leg i0-x4, `spike_app_entry.py` docstring sibling included).
  - The cited lines:
    - `RUNBOOK.md:245` says checks.txt "holds only fixed words, numbers and error type names";
    - `spike_checks.py:56-57` writes `text = " ".join(str(exc).split())` and returns `f"{type(exc).__name__}: {text[:300]}"`. That is the exception MESSAGE, which can carry paths (scratch, bundle and possibly system DLL paths) and library diagnostics.
  - No clinical data exists in the scratch profile, so the risk is an inaccurate claim plus a possible Windows user-name path, not patient content.
  - siblings=
    - the `spike_app_entry.py` module docstring ("Result lines (fixed words and numbers, no clinical data exists in a scratch profile)") makes the same overstatement for the checks.txt it dispatches to;
    - `spike_checks.py`'s own docstring is accurate ("Failure details carry the exception type and its message");
    - the "What to send back" list (`:708`, "the whole `checks.txt` and `stdio.txt`") repeats no claim.

Cap verdict: accept — production-behavioral — peer round 1 of cap 5. Only PR-MED-004 reaches the everyday app: it can leave the Chrome link removed after a mid-procedure stop. Its fix is procedural (a failure-recovery branch that runs the restore steps before reporting). The other three are a cheap precondition and two wording corrections. No finding needs a code change under `desktop/`, so the pass can continue normally after the fix.

Fix-delta self-check: PASS. I re-read the 13 applied hunks across `RUNBOOK.md` and `spike_app_entry.py`:
- the "Read this first" rule and the two callouts;
- 0.1 6a's cmd fallback and the pip-check/undo block;
- 0.2 steps 4a/4b, the reordered 9/10, the fallback's reordered copies, and steps 21, 22 and 24;
- 0.3's callout;
- the step 16 report line;
- the docstring.

Each restore step is safe whatever point was reached. The marker is present before any host file lands. No step number or cross-reference changed (the new steps are 4a/4b, so steps 13–17, 20–25 and 14 still resolve). There was no drive-by edit.

### Round 5 - 2026-10-02 - Phase 0 confirmation of round 4's fix, independent cross-family codex peer review (pass stage-0.p1)

- Round status: Closed
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Current RUNBOOK.md, spike_app_entry.py module docstring, spike_checks.py lines 40–70, and plan-installation.md Round 4 only; static read-only confirmation.

#### Findings

- **PR-MED-008** (MED, behavioral, `packaging/spike/RUNBOOK.md:172`): The venv rollback remains incomplete: neither installation route records prior package state, uninstall removes both named packages even if previously installed, and a failed consistency check still directs the clinician to stop before undoing changes. — Evidence: line 152 installs `pyinstaller==X.Y.Z`; line 172 says “If it lists anything, stop and report it”; line 174 says “Any helper packages pip added with it stay behind”; line 177 runs `pip uninstall -y pyinstaller pyinstaller-hooks-contrib`. Recommendation: Fix-now — Preserve the prior package state and provide restoration for both installation routes, with install/check failures explicitly routed through restoration; remove only packages established as newly added. /fix decision: Applied.
  - /fix notes: the exact-state route, a whole-environment copy, rather than per-package uninstalls.
    - **Before the install:** the new 0.1 steps 4a–4d require `C:\scribe-spike` to be absent (an earlier attempt's folder is cleared only after running the environment restore if its `venv-backup` exists), create it, copy `.venv` to `C:\scribe-spike\venv-backup` (`Copy-Item -Recurse -Force`) and record `pip freeze --all` to `venv-before.txt`.
    - **After the install:** `pip check` failing now routes to the restore. A `venv-after.txt` plus `Compare-Object` reports what the install added or changed (Task 3.2 input). The old `pip uninstall` line is removed, because it could take out a package that was there before.
    - **The new final section "Put the Python environment back"**, run after Task 0.2, on a 0.1 steps 6–7 failure, or from 4a:
      1. close the app and Chrome;
      2. check the backup exists;
      3. one guarded command moves `.venv` aside, or clears a partial copy left by an earlier try;
      4. copy the backup back;
      5. `Compare-Object` against `venv-before.txt` must be empty (the project's own editable-install line may differ only by commit id, which the step says);
      6. badge and self-test;
      7. only then delete `C:\scribe-spike`.
    - The "Read this first" failure rule is now one table: "Before you start" blocks stop with nothing changed; later failures run the named restore first.
    - Sibling, the Build Tools suggestion (0.1 6b): it is no longer an instruction. It is the practitioner's own decision, outside this runbook, with its undo named (Settings → Apps).
    - Verified by re-reading every changed step in context. Nothing was executed (C7).
  - /fix date: 2026-10-02
  - /fix applied by: Claude Code

- **PR-MED-009** (MED, behavioral, `packaging/spike/RUNBOOK.md:609`): HKCU recovery never uses the exported original key, so it recreates the standard registration rather than restoring the recorded prior state. A different existing registration passes the merely advisory expectation and is deleted; recovery also depends on the registration script succeeding, without a backup-import fallback. — Evidence: line 451 says the original value “is expected to end in” the standard path; line 456 exports `hkcu-host-backup.reg`; line 462 deletes the key; step 23 instead runs `.venv\Scripts\python.exe scripts\register-native-host.py` at line 612. Recommendation: Fix-now — Restore and verify the exported key during both normal and failure cleanup, or enforce the exact supported prior registration before deletion and provide an explicit backup restoration branch. /fix decision: Applied.
  - /fix notes: both halves of the recommendation.
    - **Step 5 is now a GATE.** Besides the `reg query` record, a check command compares the `(default)` value with exactly `$env:LOCALAPPDATA\ClinikoScribe\com.scribe.cliniko_host.json` (what `register-native-host.py` writes) and must print `True`. `False` (missing or different, including the absent-key case from lessons 2026-09-28) stops the run with nothing changed.
    - **Step 6** exports with `/y` and must print `The operation completed successfully.`
    - **Step 23** now restores FROM THE EXPORT (`reg import C:\scribe-spike\hkcu-host-backup.reg`) in a normal window, then re-runs the step-5 check, which must print `True`. If the backup file is not found, the run stopped before step 6, so nothing was removed.
    - It no longer depends on the venv or `register-native-host.py`, so a venv broken by 0.1 cannot block it.
    - Siblings:
      - step 18 now re-adds the link by `reg import` of the same export instead of an assumed `reg add` value;
      - the stale `%TEMP%\scribe-spike-host-stdio.txt` is cleared in the new 0.2 step 4c before anything runs.
    - The send-back list is updated: step 5's `True` and step 23's `True`.
  - /fix date: 2026-10-02
  - /fix applied by: Claude Code

- **PR-LOW-010** (LOW, test-harness, `packaging/spike/RUNBOOK.md:635`): Task 0.3 still lacks prior-state checks for its installation folder, uninstall registration and test registry values. Made-up names do not establish absence: a previous spike run can already own them, and the prescribed install/uninstall sequence does not preserve that starting state. — Evidence: line 635 asserts “Every registry value it writes uses a made-up name … so nothing real is excluded or changed”; step 4 runs the installer at line 657 without absence checks; line 739 requires the values to be gone after uninstall. Recommendation: Fix-now — Require the spike folder, uninstall registration and exact test values to be absent before the first installation; stop before mutation if remnants exist and provide a deliberate recovery procedure. /fix decision: Applied.
  - /fix notes:
    - **New 0.3 "Before you start" block.**
      - Check A: `Test-Path …\Inno Setup 6\ISCC.exe`. True means use the installed copy and never install over it; False means step 1 installs 6.7.1.
      - Check B: five absence checks — the spike folder, the `{5B7E2C1D-…}_is1` uninstall key, the WER `inno-spike-app.exe` value, and `FilesNotToBackup` / `FilesNotToSnapshot` searched for `ClinikoScribeSpike`. Each has its exact "absent" output.
      - The deliberate recovery: if anything is present, run the earlier spike's uninstaller if it exists, re-run the checks, then stop and report if anything remains.
    - **Step 14** now ends by re-running check B, which must match the pre-spike results, so the undo is verified against the recorded starting state.
    - Sibling, 0.3 step 1's Inno Setup install: it is now conditional on check A. It is kept for Phase 3, with its undo named (Settings → Apps → Inno Setup).
    - The other siblings are fixed under PR-MED-008 / PR-MED-009:
      - 0.1's appended result files: a fresh `C:\scribe-spike` (4a), plus a scratch-only clear of `spike-results` before step 15;
      - 0.2's appended `%TEMP%` file (step 4c).
  - /fix date: 2026-10-02
  - /fix applied by: Claude Code

- Verification counts: 3 claims checked, 3 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-02

#### LEG 1 verified tuples

Executor leg i0-x5, 2026-10-02T12:37+10:00, verification only. Nothing was fixed. Each claim was checked against the current `packaging/spike/RUNBOOK.md`. All three are CONFIRMED, all Fix-now, one severity downgraded. All three belong to the round-4 class: **every state change needs (a) a prior-state check, (b) an undo that restores THAT state, and (c) a failure branch that reaches the undo.** That class is NOT yet fully enumerated by these three; the further siblings are listed on each line and summarised after them.

- PR-MED-008: materiality=behavioral severity=verified med surface=production rec=Fix-now — CONFIRMED. final=Applied (LEG 2 leg i0-x6; Build Tools sibling included).
  - The cited lines:
    - `:146` (6a) `pip install C:\scribe-spike\pyinstaller-src` and `:152` (6b) `pip install pyinstaller==X.Y.Z` record no prior package state;
    - `:172` says "If it lists anything, stop and report it", a failure branch that stops without undoing;
    - `:174` says "Any helper packages pip added with it stay behind";
    - `:177` uninstalls both names unconditionally, even if one was there before.
  - It is MED and production because the everyday app runs from this same `.venv` (`.venv\Scripts\scribe-app.exe`, AGENTS.md). An install that upgrades or breaks a shared package, left in place by "stop and report", can stop the everyday app, and the same broken venv would also break 0.2 step 23's restore (`register-native-host.py` runs from it).
  - The likelihood is low, since PyInstaller's dependencies are few and pip changes a package only to satisfy a constraint. That is unverified, so MED stands.
  - The fix needs a restorable baseline taken BEFORE step 6 (for example a `pip freeze --all` record, or a copy of the venv), and an undo that returns exactly to it.
  - siblings=
    - 0.3 step 1 (`:639`) installs Inno Setup machine-wide with no prior-version check and no undo line (an existing different Inno version is silently upgraded or downgraded);
    - 0.1 6b's text (`:154`) suggests installing Build Tools for Visual Studio, likewise with no prior-state or undo note.
- PR-MED-009: materiality=behavioral severity=verified med surface=production rec=Fix-now — CONFIRMED. final=Applied (LEG 2 leg i0-x6; step-18 and absent-key siblings included).
  - The cited lines:
    - `:451` "It is expected to end in `\ClinikoScribe\com.scribe.cliniko_host.json`" is advisory, not a gate;
    - `:456` exports `hkcu-host-backup.reg`;
    - `:462` deletes the key;
    - restore step 23 (`:612`) re-runs `register-native-host.py` and never uses the export.
  - The script recreates the STANDARD value, and its `verified : OK` read-back is stronger than a bare import, since it also checks the manifest and exe. But a non-standard prior value is lost, and if the script cannot run (see PR-MED-008: a venv broken by step 6) there is no `reg import` fallback, so the everyday Chrome link stays broken. Nothing is lost permanently.
  - Also unhandled: the key may be ABSENT at step 5. `docs/lessons.md` (2026-09-28) records the real HKCU key going missing, cause not found. Step 6's export then errors, and step 23 would CREATE a key that was not there before (the desired state, but not "restore exactly", and the precondition is unreported).
  - siblings=
    - 0.2 step 18 (`:570`ff) re-adds HKCU with the assumed standard `$env:LOCALAPPDATA\ClinikoScribe\…json` path rather than the recorded step-5 value;
    - the absent-at-step-5 branch above (no "what you should see if it is missing").
- PR-LOW-010: materiality=behavioral severity=verified low surface=test-harness rec=Fix-now — CONFIRMED. final=Applied (LEG 2 leg i0-x6; Inno-install and appended-result-file siblings included).
  - The cited lines:
    - `:635` "Every registry value it writes uses a made-up name … so nothing real is excluded or changed";
    - step 4 (`:657`) installs with no absence check of `C:\Program Files\ClinikoScribeInnoSpike`, the `{5B7E2C1D-…}_is1` uninstall key or the seven test values;
    - step 14 then expects them all gone.
  - The made-up names can only be owned by an earlier run of THIS spike, so the "prior state" a remnant would represent is itself spike debris. Preserving it has no value; the right fix is a precondition that stops (or uninstalls the earlier spike first) and reports.
  - It is test-harness surface: the everyday app and data are untouched either way. A remnant would mainly corrupt the readings (step 5's version, step 13's single `unins000.exe`).
  - The same "a prior spike run left state" shape exists in other tasks (siblings).
  - siblings=
    - 0.1 steps 12–17: `C:\scribe-spike\Local` is not required to be fresh, and `spike_stdio.append_result` APPENDS, so a second 0.1 run mixes stale lines into `checks.txt` / `stdio.txt`, and step 16's "twelve lines … 12 of 12" no longer holds;
    - 0.2 step 16: `%TEMP%\scribe-spike-host-stdio.txt` is appended the same way, so a stale line from an earlier attempt reads as this run's;
    - 0.1 step 6a `git clone` into an existing `C:\scribe-spike\pyinstaller-src` fails loudly (no state change; not a defect).

**Class enumeration after this round.** The complete set of state-changing steps in the runbook, with their status:
- **Covered (prior-state check + undo + failure branch):** 0.2 steps 7–11, the fallback block and steps 21–22 (rounds 4/5's 4a/4b, the marker, the guarded removal, the callout).
- **Open (these three findings):** the 0.1 venv install (008); the 0.2 HKCU delete and restore (009); the 0.3 spike install (010).
- **Open (the siblings above):**
  - 0.3 step 1's Inno Setup install;
  - 0.1 6b's Build Tools suggestion;
  - 0.2 step 18's assumed HKCU value;
  - 0.2 step 5's absent-key branch;
  - the appended result files: 0.1 `spike-results\*.txt` and 0.2 `%TEMP%\scribe-spike-host-stdio.txt`.
- **Not state changes, or scratch-only by construction:**
  - 0.1 steps 11, 12–14, 15–21 (scratch profile behind the isolation guard), apart from the append issue above;
  - 0.1 step 8 build output (`--noconfirm`, in `C:\scribe-spike`);
  - 0.5 (scans; a detection could be quarantined by Defender inside `C:\scribe-spike\dist`, scratch only, and C10 already pauses);
  - 0.3 steps 2–3 (`C:\scribe-spike\inno-out`).

With those siblings folded in, I found no further state-changing step.

Cap verdict: accept — production-behavioral — peer round 2 of cap 5. PR-MED-008 and PR-MED-009 can each leave the everyday app or its Chrome link not working, and they compound: a venv broken by step 6 also disables 0.2's restore. Both fixes are procedural:
- a restorable venv baseline with an exact undo and a failure route to it;
- step 5 made a gate (standard value or stop), a reported absent-key branch, and a `reg import` of the step-6 export as the restore fallback.

PR-LOW-010 and the listed siblings close the class (prior-state check + exact undo + failure route) across all three tasks. No `desktop/` change is needed. After the fix, continue to a confirmation round.

Fix-delta self-check: flagged-and-fixed in-leg. The re-read of the leg's hunks found that the new "Put the Python environment back" step 4 (a bare `Move-Item .venv …\venv-spike-old`) was NOT safe to repeat, as the section claims.
- A second try would collide with the existing `venv-spike-old`, or leave a partial copy from a failed step 5.
- It was corrected in this leg to one guarded `try`/`catch` command: it moves `.venv` aside on the first try, or clears the partial copy if an earlier try got that far, and prints an explicit *NOT moved / NOT cleared* line when something holds the folder open.

The re-read covered:
- the "Read this first" table;
- 0.1 steps 4a–4d, 7 (pip check / compare) and 15 (results clear), and the 6b Build Tools text;
- 0.2 steps 4c, 5, 6, 18 and 23;
- 0.3 Before you start A/B, step 1 and step 14;
- the send-back list;
- the new final section.

Every other changed step is safe from any starting point, and no step number or cross-reference changed: 4a–4d and A/B are new labels, and 13–17, 20–25 and 14 still resolve. There was no drive-by edit. **The class is now closed:** every state-changing step in the runbook has a prior-state check, an undo that restores THAT state, and a failure route that reaches it. That is the per-step enumeration in LEG 1's "Class enumeration", with each "open" item now fixed.

### Round 6 - 2026-10-02 - Phase 0 confirmation of round 5's fix, independent cross-family codex peer review (pass stage-0.p1)

- Round status: Closed
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Current packaging/spike/RUNBOOK.md, spike_app_entry.py module docstring, spike_checks.py lines 40–70, and plan-installation.md Round 5 only; static read-only confirmation.

#### Findings

- **PR-MED-011** (MED, regression, `packaging/spike/RUNBOOK.md:943`): A partial backup can replace the working everyday environment. If step 4c fails after copying `Scripts\python.exe`, the next attempt’s step 4a routes into restoration merely because the backup folder exists. Restoration checks only that executable, moves the working `.venv` aside, and copies the incomplete backup into its place. Package metadata comparison cannot establish file completeness. — Evidence: line 76 says “If `C:\scribe-spike\venv-backup` exists, run **Put the Python environment back**”; line 93 runs `Copy-Item -Recurse -Force .venv C:\scribe-spike\venv-backup`; line 943 checks only `Test-Path C:\scribe-spike\venv-backup\Scripts\python.exe`; lines 950–957 move/remove `.venv` before copying the backup. Recommendation: Fix-now — Use a separately created scratch build environment for both PyInstaller routes and host packaging, leaving the everyday `.venv` untouched; this removes the evidenced partial-copy replacement risk and the multi-GB restoration requirement. /fix decision: Applied.
  - /fix notes: by the DESIGN in LEG 1's rec — build in a COPY of `.venv`, used read-write as the build environment; the everyday `.venv` is never written.
    - **0.1 Before you start:** 4a requires `C:\scribe-spike` absent (an earlier attempt's folder is cleared only after Task 0.2's Put everything back if its `hkcu-host-backup.reg` exists, then re-checked with `Test-Path`; a still-present folder means close what holds it and repeat). 4b creates it. 4c records `.venv\Scripts\python.exe -m pip freeze --all` to `everyday-before.txt` (read-only). 4d copies `.venv` to `C:\scribe-spike\venv-build`; a partial copy is deleted and copied again (harmless: nothing is ever copied back). 4e must print `sys.prefix` = `C:\scribe-spike\venv-build`, else stop.
    - **The launcher hazard:** a callout after 4e says to use the copy ONLY as `C:\scribe-spike\venv-build\Scripts\python.exe -m …` and never another program in its `Scripts` (the copied `pip.exe` / `pyinstaller.exe` / `scribe-*.exe` launchers embed the original's interpreter path). Every later build command — 5's `pip index`, 6a's waf (both the PowerShell and the `.bat` line) and source install, 6b's install, 7's `--version` / `pip show` / `pip check`, 8's build, and 0.2 step 2's host build — calls the copy's `python.exe -m`.
    - **Removed:** the `venv-backup` copy, `venv-before.txt` / `venv-after.txt`, and the whole "Put the Python environment back" section (its move-aside, restore copy and backup check). Step 7's `Compare-Object` now compares the build copy against `everyday-before.txt` (what the install added, for Task 3.2).
    - **New final section "Finishing up":** step 1 is the read-only `Compare-Object` of `everyday-before.txt` against the everyday `.venv`'s current `pip freeze --all` — empty, apart from the editable project line's commit id — which proves the original untouched; step 2 requires Task 0.2's step 23 check to have said `True` (else run Put everything back now, which needs the folder); step 3 deletes `C:\scribe-spike` and confirms `Test-Path` → `False` (else close what holds it and repeat). Send-back item 6 reports step 1.
    - Verified by re-reading every changed step in context. Nothing was executed (C7).
  - /fix date: 2026-10-02
  - /fix applied by: Claude Code

- **PR-MED-012** (MED, behavioral, `packaging/spike/RUNBOOK.md:19`): Failure routing still leaves the everyday venv modified when work stops after installation: Task 0.1 build/run failures, Task 0.5 pauses, and Task 0.2 build/scan/precondition failures do not reach the Python restore. The normal restore requires finishing Task 0.2, which these failures prevent. — Evidence: line 19 routes “Task 0.1, any other step” to “nothing”; line 22 routes Task 0.5 to “nothing”; line 223 says “PyInstaller stays in the project environment until you finish Task 0.2”; line 384 directs a build/run failure to “report it first”; line 925 names restoration after finishing Task 0.2 or failures in Task 0.1 steps 6–7 only. Recommendation: Fix-now — Eliminate the everyday-venv mutation as above, or route every subsequent failure/pause through its restoration, after restoring the Chrome registration wherever applicable. /fix decision: Applied.
  - /fix notes: by the same design as PR-MED-011 — the everyday venv is never modified, so no failure or pause needs a Python restore.
    - The "Read this first" failure table's venv rows are gone: "Task 0.1, any step | nothing — Task 0.1 only changes `C:\scribe-spike`; your everyday Python environment is copied there and the copy is used; the original is never changed". The 0.2 (steps 20–25), 0.3 (step 14) and 0.5 (nothing) rows stand.
    - Siblings: step 7's `pip check` failure now says "stop and report; only the build copy is affected, so there is nothing to put back"; the 3.12 fallback (`C:\scribe-spike\venv312`, already separate) now reads "that environment's `python.exe -m pip` / `python.exe -m PyInstaller` in place of the build copy's"; 0.2 step 2's host build uses the build copy; the "Read this first" tidy-up line points at Finishing up.
  - /fix date: 2026-10-02
  - /fix applied by: Claude Code

- **PR-LOW-013** (LOW, test-harness, `packaging/spike/RUNBOOK.md:664`): Both folder cleanup commands can report successful removal when removal failed, and their marker-based retry is incomplete. A partial manifest copy without the marker leaves a nonempty spike-created folder that cleanup refuses; a partial deletion that removes the manifest but leaves another file produces the same unrecoverable-by-these-instructions state. — Evidence: lines 664 and 670 gate deletion on `"installation spike"` or an empty directory, then execute `Remove-Item -Recurse -Force …; "Removed the spike folder."` without terminating-error handling or an absence check; otherwise they print “NOT removed: this folder is not the spike's.” Recommendation: Fix-now — Retain creation evidence outside each deletion target, handle partial-copy and partial-delete states, and print success only after verifying absence; preserve the route onward to HKCU restoration when folder cleanup fails. /fix decision: Applied.
  - /fix notes: per LEG 1's rec.
    - **Creation evidence outside the target:** 0.2 step 8 and the fallback's first command are each ONE guarded command — `try { New-Item … -ErrorAction Stop; Add-Content C:\scribe-spike\created-folders.txt "<path>" -ErrorAction Stop; "Made and noted down." } catch { "NOT done: go to Put everything back." }` — so a folder is noted only after it is made (step 4b's `Test-Path` → `False` already proves prior absence). If the note itself fails, step 22 refuses the folder and asks for a report: the safe direction, never a deletion of a folder the spike did not make. Step 9 no longer claims the manifest marks the folder.
    - **Step 22** is one elevated command over both folders: absent → "nothing to remove"; not in the note → "NOT removed - the spike did not make this folder"; otherwise `try { Remove-Item -Recurse -Force … -ErrorAction Stop } catch {}` then `Test-Path` → "removed." only when absent, else "NOT fully removed - something still has a file open". It always ends "Continue with step 23.", and the text routes: NOT fully removed → after step 25, repeat step 20's check and step 22; not the spike's → leave it and report. Partial-copy and partial-delete states are handled because the gate no longer reads folder content.
    - Siblings: 0.1 step 15's `spike-results` clear and 0.2 step 4c's `%TEMP%` pipe-file clear each gain a `Test-Path` → `False` check (else end the still-running spike program and repeat; the 4c one was found by this leg's self-check); 0.1 4a's delete re-check now says what to do if it still says `True`; Finishing up's delete gains its `Test-Path` check; 0.3 step 11's write probe, if it unexpectedly succeeds, removes the probe file (elevated) so step 14's uninstall can remove the folder; 0.3 step 14 says to report, not hand-delete, anything check B still shows.
  - /fix date: 2026-10-02
  - /fix applied by: Claude Code

- Verification counts: 3 claims checked, 3 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-02

#### LEG 1 verified tuples

Executor leg i0-x7, 2026-10-02T12:47+10:00, verification only. Nothing was fixed. Each claim was checked against the current `packaging/spike/RUNBOOK.md`; every finding is CONFIRMED.

**The trajectory (4 → 3 → 3, with round 5's fix inducing PR-MED-011) says the venv half of the class should be closed by DESIGN, not by patching the restore a third time.** I recommend a design below.

- PR-MED-011: materiality=regression severity=verified med surface=production — CONFIRMED. final=Applied (LEG 2 leg i0-x8; by the build-copy design, backup/restore removed, sys.prefix check and launcher callout included).
  - The cited lines:
    - `:76` "If `C:\scribe-spike\venv-backup` exists, run **Put the Python environment back**" (presence only);
    - `:93` `Copy-Item -Recurse -Force .venv C:\scribe-spike\venv-backup` (a copy that can stop partway);
    - `:943` checks only `Test-Path C:\scribe-spike\venv-backup\Scripts\python.exe`;
    - `:950-957` move the working `.venv` aside and copy the backup over it.
  - So a partial backup can replace the everyday environment. Step 6's `pip freeze` comparison reads package metadata, not file completeness: a backup holding every `dist-info` but missing DLLs would pass. Step 8 then deletes the `venv-spike-old` copy, which is the only intact copy.
  - It is MED, not HIGH: before step 8 the original sits intact in `venv-spike-old`, and even after it, the AGENTS.md step-2 setup rebuilds the venv (network, about an hour). Nothing clinical is touched.
  - rec=Fix-now — by DESIGN: **build in a COPY of `.venv`, used read-write as the build environment, and never write the original.** Remove the backup/restore machinery entirely.
  - **Why a copy works:**
    - a venv's `Scripts\python.exe` is a redirector that reads the `pyvenv.cfg` beside it (lessons 2026-09-28), so `C:\scribe-spike\venv-build\Scripts\python.exe` runs with `sys.prefix` = the copy;
    - `python -m pip` therefore installs PyInstaller into the copy, and `python -m PyInstaller` builds from it;
    - the editable `.pth` / finder points at the repo's `desktop/src`, which is read-only use.
  - **The one hazard:** the copied `Scripts\*.exe` launchers (`pip.exe`, `scribe-app.exe`, `scribe-host.exe`) embed the ORIGINAL venv's interpreter path, so running one would act on the everyday venv. The runbook must call ONLY `<copy>\Scripts\python.exe -m pip` / `-m PyInstaller`, and verify first that `<copy>\Scripts\python.exe -c "import sys; print(sys.prefix)"` prints `C:\scribe-spike\venv-build`.
  - **Cost:**
    - local only: a few GB of disk and minutes of copying;
    - no extra network beyond PyInstaller itself, which both options need;
    - the frozen-build inputs are BYTE-IDENTICAL to what the everyday app runs (same files), which is exactly what Task 0.1 should measure.
  - **The alternative — a fresh `python -m venv` plus network installs — is rejected:**
    - it needs the whole `[ml]` stack, `sounddevice`, the hashed prose wheel and its two follow-up installs re-downloaded (about 1–2 GB, the AGENTS.md step-2 sequence);
    - it resolves the unpinned `PySide6>=6.8` / `faster-whisper>=1.2` / `onnxruntime>=1.28` afresh, so the frozen inputs can DRIFT from what the everyday app runs unless every version is constrained from a read-only `pip freeze` of `.venv` (more steps, and the editable and wheel lines need special handling).
  - **Partial copies:** under this design a partial copy is harmless (the build fails loudly; delete the copy and copy again), because nothing is ever copied back.
  - A read-only end check (the everyday `.venv`'s `pip freeze --all` identical before and after the campaign) proves the original was untouched.
  - siblings=
    - the restore section's steps 3–5 (`:940-957`) and 0.1 step 4a's route into it. Both are removed by the design.
    - No other step replaces user state on the strength of a possibly-partial artefact: 0.2's `reg import` is gated by step 6's success line before step 7 deletes anything, and 0.3's remnant recovery runs the spike's own uninstaller.
- PR-MED-012: materiality=behavioral severity=verified low (peer MED) surface=production — CONFIRMED. final=Applied (LEG 2 leg i0-x8; by the same design; failure-table, 3.12-fallback and 0.2 host-build siblings included).
  - The cited lines:
    - `:19` "Task 0.1, any other step | nothing";
    - `:22` "Task 0.5 | nothing";
    - `:223` "PyInstaller stays in the project environment until you finish Task 0.2";
    - `:384` routes a build/run failure to "report it first";
    - `:925` restores only after Task 0.2 or a 0.1 steps 6–7 failure.
  - So a later failure or pause leaves the everyday venv modified.
  - Downgrade evidence: what is left is only the PyInstaller addition that step 7's `pip check` already verified consistent, and the everyday app never imports PyInstaller. The effect is drift from the recorded state, not a broken app.
  - rec=Fix-now — by the SAME design as PR-MED-011. With the build done in `C:\scribe-spike\venv-build`, the everyday venv is never modified, so no failure route needs a Python restore. 0.1/0.5/0.2 failures then route only to their existing per-task put-back (0.2's steps 20–25), and the venv rows leave the failure table.
  - siblings=
    - the "Read this first" table rows for 0.1 steps 6–7, "any other step" and 0.5 (`:18-22`);
    - the 3.12 fallback paragraph (`:384`, its `C:\scribe-spike\venv312`, already a separate environment — consistent with the design);
    - Task 0.2 step 2's host build (it must use the same build copy's `python.exe -m PyInstaller`).
- PR-LOW-013: materiality=behavioral severity=verified low surface=production — CONFIRMED. final=Applied (LEG 2 leg i0-x8; record-gated, verified step 22; the note is written after a successful `New-Item`, as the rec says; step-15, 4a, Finishing-up and 0.3 step 11/14 siblings included).
  - The cited lines: `:664` and `:670` run `Remove-Item -Recurse -Force …; "Removed the spike folder."`. `Remove-Item`'s errors are non-terminating there, so the success line prints even when removal failed, and no `Test-Path` confirms absence.
  - The gate is the in-target marker or emptiness, so two states fall to the misleading "NOT removed: this folder is not the spike's":
    - an interrupted manifest copy (a zero-byte manifest);
    - a partial delete that removed the manifest first but left a locked file.
  - **Surface production, not test-harness:** step 22 says "Report it" without saying to CONTINUE with step 23, and a practitioner who stops there leaves the everyday HKCU link deleted. Step 23 restores it whenever it runs, so this is LOW.
  - rec=Fix-now:
    - record creation evidence OUTSIDE the target: a line in `C:\scribe-spike\created-folders.txt` written immediately after step 8's (and the fallback's) `New-Item` succeeds, plus the 4b `Test-Path` False already proving prior absence;
    - gate deletion on that record, not on in-folder content;
    - use `Remove-Item -ErrorAction Stop` inside `try`/`catch`, and print "Removed" only after `Test-Path` returns False;
    - make every step-22 outcome say "then continue with step 23".
  - siblings=
    - the restore section's step 8 `Remove-Item -Recurse -Force C:\scribe-spike` (`:972`): no absence check, scratch only; it goes away with the design anyway;
    - 0.1 step 15's `Remove-Item … spike-results -ErrorAction SilentlyContinue` (a locked stale `checks.txt` would survive silently and mix into the results; add an absence check);
    - 0.1 step 4a's delete is already followed by a `Test-Path` re-check (fine, not a sibling).

**Class status after this round's fix.** Once the copy-as-build-environment design is in, every remaining state-changing step is covered:
- 0.2 steps 7–11 / fallback / 18 / 21–23 (rounds 4–5 plus PR-LOW-013's tightened cleanup);
- 0.3 steps 1/4/12 (round 5's A/B checks and step 14).

The everyday `.venv` and its restore drop out of the class entirely. Nothing else in the runbook changes user state.

Cap verdict: accept — production-behavioral — peer round 3 of cap 5.
- PR-MED-011 is a fix-induced regression that reaches the everyday environment.
- The recommended DESIGN removes the venv mutation, and with it 011, 012 and the multi-GB backup/restore, instead of patching the restore again.
- PR-LOW-013 is a bounded edit to two commands.
- I expect the class to close at the next confirmation round, well inside the cap, so no raise is needed.

Fix-delta self-check: flagged-and-fixed in-leg. Leg i0-x8 re-read every changed hunk in context (the failure table and tidy-up line; 0.1 4a–4e, the launcher callout, 5–8 and 15; 0.2 steps 2, 4c, 8, 9, the fallback block and 22; 0.3 steps 11 and 14; send-back item 6; Finishing up).
- Found: 0.2 step 4c's `%TEMP%\scribe-spike-host-stdio.txt` clear was the same silent `-ErrorAction SilentlyContinue` delete as step 15's, so a locked stale line could still read as this run's in step 16. It now has the `Test-Path` → `False` check too.
- Found and corrected before the hunk was final: the first draft wrote the creation note BEFORE `New-Item`, which would let step 22 delete a pre-existing folder if step 4b's absence check were skipped. The note is now written only after `New-Item` succeeds, in one guarded command, as LEG 1's rec says.
- PowerShell forms checked by reading: `"${p}: …"` (braced, so not a scope-qualified variable), `-notcontains` against a missing note file (`$null` → refuse), `-ErrorAction Stop` inside `try` making a failed `New-Item` skip the note. Nothing was executed (C7). No step number or cross-reference changed except the removed final section, whose every reference (the 4a route, the failure table, send-back item 6, "Read this first") now points at Finishing up or is gone.

**The class is closed.** Every state-changing step in the runbook has a prior-state check, an undo that restores THAT state, and a failure route that reaches it:
- 0.1 changes only `C:\scribe-spike` (4a absence, Finishing up's verified delete); the everyday `.venv` is only READ, before (4c) and after (Finishing up step 1);
- 0.2's HKCU link (5 gate, 6 export, 18/23 import + check), HKLM link (4a absence, 21), install folders (4b absence, the 8/fallback note, the gated and verified 22), the `%TEMP%` pipe file (4c verified clear, 24);
- 0.3's install (A/B, 14 with check B re-run; 11's probe file removed if it lands), Inno Setup itself (A, Settings → Apps);
- 0.5 changes nothing.

### Round 7 - 2026-10-02 - Phase 0 confirmation of round 6's fix, independent cross-family codex peer review (pass stage-0.p1)

- Round status: Closed
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Current RUNBOOK.md, spike_app_entry.py module docstring, spike_checks.py lines 40–70, and plan-installation.md Round 6; read-only verification of fixes, siblings, rollback paths and build-copy usage.

#### Findings

- **PR-MED-014** (MED, test-harness, `packaging/spike/RUNBOOK.md:459`): The Python 3.12 fallback does not propagate to the host build. After successfully rebuilding the app with `venv312`, Task 0.2 selects the Python 3.14 build copy again, contradicting its same-environment requirement and potentially repeating the packaging failure that required the fallback. — Evidence: line 396 limits substitution to “steps 5–22 again with that environment's `python.exe -m pip` / `python.exe -m PyInstaller`”; line 456 requires “the same Python and PyInstaller as Task 0.1”; line 459 explicitly invokes `C:\scribe-spike\venv-build\Scripts\python.exe -m PyInstaller`. Recommendation: Fix-now — Carry the successful environment choice into Task 0.2 step 2, explicitly using `C:\scribe-spike\venv312\Scripts\python.exe` when the fallback was used. /fix decision: Applied.
  - /fix notes:
    - **Task 0.2 step 2** now says to build the host "with the same environment that built the working Task 0.1 app" and gives two exact commands, run one: the build copy `C:\scribe-spike\venv-build\Scripts\python.exe -m PyInstaller … host.spec` normally, or `C:\scribe-spike\venv312\Scripts\python.exe -m PyInstaller … host.spec` only if 0.1 used the 3.12 fallback. *Report back:* which one ran.
    - **Sibling, the 3.12 fallback paragraph (`:396`)** is now a numbered procedure:
      1. make `C:\scribe-spike\venv312` (exact commands come with the go-ahead; Finishing up removes it with the folder);
      2. in a new normal window at the project folder (step 3), rerun steps 5–23, replacing EVERY `C:\scribe-spike\venv-build\Scripts\python.exe` with `C:\scribe-spike\venv312\Scripts\python.exe`. That covers 6a's `./waf` lines, 6b, 7 and 8, not only `-m pip` / `-m PyInstaller`. Skip 6a's download, fingerprints and bootloader build if 6a was taken the first time (already done in `pyinstaller-src`; a second `git clone` would fail on the existing folder), and skip step 7's `Compare-Object` (a 3.14 baseline);
      3. Task 0.2 step 2 uses `venv312` too.
    - **Sibling, the send-back list:** 0.1 reports whether the 3.12 fallback was needed; 0.2 reports which environment built the host.
    - Verified by re-reading the changed hunks in context. Nothing was executed (C7).
  - /fix date: 2026-10-02
  - /fix applied by: Claude Code

- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-02

#### LEG 1 verified tuples

Executor leg i0-x9, 2026-10-02T12:57+10:00, verification only. Nothing was fixed. The claim was checked against the current `packaging/spike/RUNBOOK.md` and is CONFIRMED.

- PR-MED-014: materiality=behavioral severity=verified low (peer MED) surface=test-harness rec=Fix-now — CONFIRMED. final=Applied (LEG 2 leg i0-x10; both siblings included, plus the 6a re-clone and new-window/cwd gaps found in the fix-delta re-read).
  - The cited lines:
    - `:396` "then steps 5–22 again with that environment's `python.exe -m pip` / `python.exe -m PyInstaller` in place of the build copy's" — the substitution is scoped to Task 0.1 only;
    - `:456` "Build the packaged host, with the same Python and PyInstaller as Task 0.1";
    - `:459` `C:\scribe-spike\venv-build\Scripts\python.exe -m PyInstaller … packaging\spike\host.spec` — hard-codes the 3.14 build copy.
  - So after a 3.12 fallback, a literal reading builds the host on 3.14 again. Either it fails the same way, or it measures D-I1 and the stdio question on the runtime that was rejected.
  - Downgrade evidence:
    - step 2 runs BEFORE any change to the computer (the first change is step 7's HKCU delete), so a failed build stops with nothing to undo;
    - a host that builds but misbehaves only reaches step 7 onward, where the existing Put everything back (steps 20–25) restores the Chrome link;
    - the fallback is gated by `:396` "Wait for the go-ahead before doing this", so the composer is in the loop before it is used.
    - The cost is a wasted or misleading spike reading, not harm to the everyday app or data, so it is test-harness and LOW.
  - Fix: a one-line edit — step 2 names `C:\scribe-spike\venv312\Scripts\python.exe` when the 3.12 fallback was used. Fix-now because it is cheap and it settles which runtime the spike measured.
  - siblings=
    - `:396` itself: its substitution names only `-m pip` / `-m PyInstaller`, but steps 5–8 also call the build copy at `:160` / `:174` (6a's `./waf` lines, PowerShell and `.bat`) and at `:228` (step 7's `Compare-Object … venv-build … pip freeze`). That comparison against `everyday-before.txt` (a 3.14 list) would be noise for a 3.12 environment. Better wording: "every `C:\scribe-spike\venv-build\Scripts\python.exe` in steps 5–8 becomes `C:\scribe-spike\venv312\Scripts\python.exe`, and step 7's comparison is skipped".
    - The send-back list (0.1 item: "the Python version"; 0.2 has no environment line): it does not record which environment built the host. Add "which environment built the host" to item 3.
    - No other later step names `venv-build`. Task 0.5 scans `dist\scribe-app` and 0.3 compiles with ISCC, so both are environment-agnostic. Finishing up deletes `C:\scribe-spike` (which includes `venv312`) and reads only the everyday `.venv`.
    - No PowerShell-only syntax is handed to cmd: the `.bat` block at `:174` is a plain command line.
    - No mutating step lacks an undo: `venv312` lives under `C:\scribe-spike` and is removed by Finishing up.

Cap verdict: accept — test-harness — peer round 4 of cap 5.
- One LOW, test-harness finding: a missed carry-through of the round-6 rename into the 3.12 fallback path. It is a bounded wording fix (step 2's interpreter, plus the `:396` substitution sentence and one send-back line).
- The trajectory is 4 → 3 → 3 → 1, with no production-surface finding this round. The class from rounds 4–6 (prior-state check + exact undo + failure route) drew no new finding.
- The confirmation round after the fix (peer_round 5) is the cap. Given the size of this fix, I expect it to converge there, so no raise is needed.

Fix-delta self-check: flagged-and-fixed in-leg. Leg i0-x10 re-read the fallback procedure, 0.2 step 2 and the send-back list in context, and found two gaps in its own first draft of the fallback:
- "rerun 6a" would have re-run `git clone` into the existing `pyinstaller-src`, which fails loudly and reads as a failure. 6a's download, fingerprints and bootloader build are now skipped when 6a was taken the first time.
- The rerun had no working folder: step 23 closes the window, and step 8's `packaging\spike\scribe.spec` is a relative path. The procedure now opens a new normal window and runs step 3 first, which also keeps the environment set-up out of a scratch-`LOCALAPPDATA` window.

**Class enumeration after this round.**
- Every later command that names an environment now follows the one actually used: 0.1 steps 5–8 through the fallback's replace-every rule, and 0.2 step 2's two explicit commands. No other step names `venv-build`. 0.5 and 0.3 are environment-agnostic, and Finishing up reads only the everyday `.venv`.
- `venv312` is created inside the fresh `C:\scribe-spike` (4a's absence check) and removed by Finishing up's verified delete.
- The prior-state check + exact undo + failure route class from rounds 4–6 is unchanged and still closed.

### Round 8 - 2026-10-02 - Phase 0 confirmation of round 7's fix, independent cross-family codex peer review (pass stage-0.p1)

- Round status: Closed
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Current RUNBOOK.md, spike_app_entry.py module docstring, spike_checks.py lines 40–70, and plan-installation.md Round 7; read-only confirmation of environment selection, siblings, state changes and rollback.

#### Findings

- **PR-LOW-015** (LOW, test-harness, `packaging/spike/RUNBOOK.md:562`): Successful folder creation followed by a failed marker write leaves a spike-created folder that rollback refuses to remove. The fallback folder has the same gap at line 636. — Evidence: both commands perform `New-Item ... -ErrorAction Stop` before `Add-Content C:\scribe-spike\created-folders.txt ... -ErrorAction Stop`, but their catch only says `"NOT done: go to Put everything back."` Line 695 refuses removal when the marker does not contain the path, and line 699 directs `"leave it alone and report it."` Recommendation: Fix-now — Track successful creation separately and explicitly undo it if recording the marker fails, with a retry route if removal fails; apply to both folder-creation commands. /fix decision: Accepted — the residue is an empty, administrator-controlled folder that step 22 refuses and asks the practitioner to report; nothing of the practitioner's is at risk, and it is the safe direction chosen deliberately in round 6.

- Verification counts: 3 claims checked, 1 confirmed, 2 dropped as unverifiable
- Last reviewed: 2026-10-02

#### LEG 1 verified tuples

Executor leg i0-x11, 2026-10-02T13:02+10:00, verification only. Nothing was fixed. The claim was checked against the current `packaging/spike/RUNBOOK.md` and is CONFIRMED.

- PR-LOW-015: materiality=behavioral severity=verified low surface=test-harness rec=Accept (Accept-with-record, the v33 D9 default: this is the 2nd consecutive round of test-harness-only survivors at MED and below) — CONFIRMED.
  - **The cited lines:**
    - `:562` and `:636` both run `try { New-Item … -ErrorAction Stop | Out-Null; Add-Content C:\scribe-spike\created-folders.txt "<path>" -ErrorAction Stop; "Made and noted down." } catch { "NOT done: go to Put everything back." }`;
    - `:695` (step 22) refuses a folder missing from the note;
    - `:699` says "leave it alone and report it".
    - So if `New-Item` succeeds and `Add-Content` then fails, the made folder is never removed by the runbook.
  - **What the practitioner sees:**
    - `NOT done: go to Put everything back.`;
    - then, at step 22, `C:\Program Files\ClinikoScribe: NOT removed - the spike did not make this folder.` followed by `Continue with step 23.`;
    - steps 23–25 still restore the everyday HKCU link and verify it `True`, so the Chrome link is whole.
  - **What is left behind:** one EMPTY folder (nothing has been copied into it yet, and step 11's HKLM link is not reached), with Program Files' inherited permissions (only administrators can change it). It is reported, so the composer can give a one-line elevated `Remove-Item` on review.
  - **Nothing of the practitioner's is at risk:**
    - no data, registry value, Chrome link or everyday app file is involved;
    - a rerun of 0.2 is stopped at 4b ("stop and report"), so a leftover can never be mistaken for a fresh state;
    - the future installer's own install folder is unaffected by an empty pre-existing folder.
  - **Likelihood is near zero.** `Add-Content` appends to a user-writable file in `C:\scribe-spike`, which 4a/4b created minutes earlier, in an elevated window, immediately after a successful `New-Item`. It fails only if the disk filled in that instant or the folder was removed.
  - **Why accept rather than fix:** the reverse failure is the one that matters. If the runbook auto-removed a folder it could not prove it made, that could delete a folder the spike did not make. Round 6's fix chose the refuse-and-report direction deliberately (round 6 Fix-delta self-check). The peer's remedy, an explicit undo inside the `catch` with its own retry route, adds a third branch to a one-line command for a near-zero path; a clinician-facing runbook is better served by "report it".
  - siblings=none.
    - No other mutating step pairs a state change with a second write that can fail after it.
    - The other mutating steps are paired with their undo: 0.1 4b/4d (Finishing up's verified delete); 0.2 7/11/18 (steps 21/23 with the `True` check); the fallback's `icacls`/copies (inside the noted folder, removed with it); 0.3 4/12 (step 14 + check B).
    - No PowerShell-only syntax is handed to cmd: only the `.bat` block at 0.1 6a's compiler fallback is cmd, and it is plain.

Cap verdict: accept — test-harness — CAP round, peer_round 5 of 5; close the pass with PR-LOW-015 recorded as Accepted on this round.
- The trajectory is 4 → 3 → 3 → 1 → 1, and the last two rounds' survivors are test-harness LOW only. The finding is a near-zero-likelihood path whose outcome is a reported, empty, administrator-controlled folder, with the everyday Chrome link still restored and verified.
- No production-surface or behavioral-to-the-practitioner finding remains, so a `raise +1` would buy only a third branch in a one-line command.
- The class closed in rounds 6–7 (prior-state check + exact undo + failure route) holds: this path's failure route ends in a report rather than an undo, by design, in the safe direction.

### Round 9 - 2026-10-02 - Phase 1 (Tasks 1.1–1.8), in-session /review-loop pass 1 (executor stage-1 leg i1-x5)

- Round status: Closed — all 13 dispositions applied; composer-run suite 4 green 2026-10-02 ~23:47 (ruff clean, mypy 57 files, pytest 5417 passed / 9 skipped in 309 s — the expected +24; `.cursor/loops/stage-1-suite4-pytest.txt` in the main checkout); closed by executor leg i1-x6 2026-10-02T23:47:10+10:00
- Source: Claude Code
- Reviewer: executor `claude-opus-5-5` (high), two independent lenses run in parallel — correctness/security and plan-adherence — over one changed-files set
- Baseline: `git diff main` in the worktree `C:\scribe-build` (branch `installation-build`), plus the untracked new files (`install_layout.py`, `test_install_layout.py`, `test_identity.py`, `test_dev_write_guard.py`, `extension/src/channel.ts`, `channel.dom.test.ts`, `src/test/build-defines.ts`). Skipped with reason: `packaging/spike/` (Phase 0, closed) and the Findings-Log rounds 1–8 (not this round's).
- Files read: every changed file under `desktop/src/scribe_desktop/` (27), `desktop/tests/` (13 changed + 3 new), `extension/` (6 changed + 3 new), `scripts/` (4), `.gitignore`, and this plan's Phase 1–3 and H task text.
- Finding verification: 19 candidates; 6 dropped (no matching file:line evidence, or already covered by a planned task); 1 downgraded (MED-001, HIGH → MED: test collection only, no runtime behaviour)
- Dropped in verification: the merge-to-`main` hazard (the branch merges only at Phase P, COMPOSER RUN-STATE); HKCU-only registry reading (Task 2.3); the stray production HKCU key at unregister (Task 3.7, which P.1 step 2 depends on); `scaffold.test.ts` covering one mode (`manifest.test.ts` pins both channels' host names, `buildDefines` and `channelForMode`); `vite.config.ts`'s wiring being checked only by the build (by design `vitest.config.ts` never loads the crx plugin, and both builds are in every composer suite with their manifests checked); the shared keyring prefix as a defect (D3/C2 keep it — recorded as an H.1 residue instead, LOW-010).
- Suites at review: pytest 5393 passed / 9 skipped; ruff clean; mypy 57 files; `npm run qa` 13 files / 313 tests; both builds OK (composer, suite 3).

#### Findings

**MED-001 — `test_exclusions.py`: a module-level test inserted inside `class TestCheckWer` swallowed two of the class's tests**

- File: `desktop/tests/test_exclusions.py:303-324`
- Triage: Fix-now
- Why it matters: `test_the_checked_data_folder_follows_the_channel` was written at module level between `TestCheckWer`'s methods, so `test_an_unreadable_registry_says_so_and_still_checks_the_launch` and the four `test_a_name_that_is_not_plain_is_never_shown` cases became nested functions and were never collected (5 items silently lost; the WER-unchecked line and the plain-name guard lost their pins).
- Current behaviour: 5 test items not collected. Desired behaviour: all collected.
- Pattern siblings: a multiline search over `desktop/tests` for a module-level `def` followed by an indented `def …(self` found no other site.
- /fix decision: Applied
- /fix notes: the module-level function moved below the class, before the `mark_not_indexed` section; the two methods are back inside `TestCheckWer` unchanged. The suite count should rise by 5 (plus the new tests below).
- /fix date: 2026-10-02T23:38:40+10:00
- /fix applied by: Claude Code (executor stage-1 leg i1-x5)

**MED-002 — Task 1.7's "both channels tested" covered the `ui/models` lines only; the raised model and runtime errors had no frozen-side test**

- File: `desktop/tests/test_install_layout.py` (`TestRemedies`); sources `speech.py:183`, `transcription.py:990`, `language_model.py:166-177,259-281`, `speaker_embedding.py:289-322`, `benchmark.py:360`, `ui/main_window.py:302`
- Triage: Fix-now
- Why it matters: the remedy text a packaged build shows comes from these raise sites, and a regression to a "scripts/…" or ".venv" line in a frozen build (where neither exists) would pass every test.
- Desired behaviour: each site tested with `use_frozen` True and False, asserting this build's remedy and, when frozen, no "scripts/" or ".venv".
- /fix decision: Applied
- /fix notes: new `TestEveryRaisedModelLineFollowsTheBuild` (parametrised on frozen, 6 tests × 2): the VAD and Whisper not-found lines, `benchmark.run_all` with no models, the language model's not-found / size / digest lines, `_import_llama` (FROZEN_REMEDY and no "AGENTS.md" when frozen), the speaker model's not-found (the `.onnx.candidate` note only from a source run) / digest / onnxruntime-import lines, and the Status tab's registration line. Explicit `tmp_path` files and a faked registry only (C6); import failures by `sys.modules[...] = None`.
- /fix date: 2026-10-02T23:38:40+10:00
- /fix applied by: Claude Code (executor stage-1 leg i1-x5)

**MED-003 — after P.1 the production-pinned real-ML test legs will skip silently**

- File: `desktop/tests/test_integration_no_sockets.py:126` (`requires_ml_models`), `test_speech.py:461`, `test_speaker_embedding.py:575`, `test_benchmark.py:250`, `test_transcription.py:1384`
- Triage: Fix-now (as a planned task — the change needs a populated dev models root, which only the practitioner can create from a normal terminal, C7)
- Why it matters: the conftest pins the production channel, so these gates look in `%LOCALAPPDATA%\ClinikoScribe\models`. Once a source checkout's models live in `ClinikoScribe-dev\models`, the real-ML legs skip and the suite still reads green.
- /fix decision: Applied — included in the plan as Task 2.6 (resolve the gates through the dev root, a loud skip reason naming it, and a composer-reported run/skip count). AUTO-DISPOSABLE: MED, test-harness only, do-the-work.
- /fix date: 2026-10-02T23:38:40+10:00
- /fix applied by: Claude Code (executor stage-1 leg i1-x5)

- **[LOW]** LOW-001: `desktop/src/scribe_desktop/speaker_embedding.py:319-322` — the onnxruntime "not importable" line names the source checkout's pip command in a packaged build — Triage: Fix-now; Decision: Applied (an `is_frozen()` → `FROZEN_REMEDY` branch, as `_import_llama` has; pinned by MED-002's test).
- **[LOW]** LOW-002: `desktop/tests/test_install_layout.py` (the Task 1.2 AST scan) — references to `APP_FOLDER_NAME` / `DEV_FOLDER_NAME` / `folder_name` outside `install_layout` were unseen, and `install_layout.py:4-5` claimed more than a scan proves — Triage: Fix-now; Decision: Applied (`ast.Name` / `ast.Attribute` / import-alias references are offences under the same by-name allow-list; `exclusions.APP_FOLDER_NAME` allow-listed by name; four new must-see cases and one must-pass case; the module docstring now says "a scan, not a proof").
- **[LOW]** LOW-003: `desktop/tests/test_install_layout.py` `test_no_other_script_remedy_is_spelled_in_src` — a line-by-line grep misses a remedy split across lines or a `+` — Triage: Fix-now; Decision: Applied (folds each parsed string as the folder scan does; a split-remedy self-test added).
- **[LOW]** LOW-004: `.gitignore:32` — the comment says registration installs into `%LOCALAPPDATA%\ClinikoScribe` only — Triage: Fix-now; Decision: Applied (names the channel's folder, `ClinikoScribe-dev` from a source checkout).
- **[LOW]** LOW-005: module docstrings name the production paths only — `exclusions.py:8`, `pipe_server.py:9`, `session_store.py:4`, `audit.py:6`, `clinics.py:7`, `note_config.py:12`, `practitioner_profile.py:4` (and the style store at :54), `past_sessions.py:6`, `benchmark.py:19`, `ui/practitioner.py:109` — Triage: Fix-now; Decision: Applied (each names the dev folder or pipe and its `install_layout` / `identity` source; `benchmark` and `ui/practitioner` name this build's model remedy).
- **[LOW]** LOW-006: `desktop/src/scribe_desktop/ui/main_window.py` `_on_dev_writes_toggled` — on a failed save the box showed the inverse of the click, not the file, and the Write button was not told — Triage: Fix-now; Decision: Applied (re-reads `load_dev_settings` with signals blocked, emits `dev_writes_changed`; `DEV_WRITES_SAVE_FAILED` now says the box shows the setting in use; new test for a save that landed then raised).
- **[LOW]** LOW-007: `extension/KEY.md:5` — says the key is pinned in `src/manifest.ts` and does not record the dev ID, `key-dev.pem` or `--out` — Triage: Fix-now; Decision: Applied (both channels' IDs, `channel.ts` `CHANNELS`, both private keys, `--out extension/key-dev.pem`; Task 1.7's "Docs left for H.1" note updated).
- **[LOW]** LOW-008: `desktop/tests/test_ui_encounter.py` — the dev refusal's audit row is pinned only through the fake recorder — Triage: Fix-now; Decision: Applied (`test_audit.py::…test_the_dev_build_refusal_is_recorded` writes it through a real `AuditLog`).
- **[LOW]** LOW-009: `desktop/src/scribe_desktop/install_layout.py:140-152` — only `models_root` calls `install_root()`, so a frozen build outside `INSTALL_ROOTS` still runs as production with full data access — Triage: Fix-now (scope-expansion, LOW, as a planned task); Decision: Applied — included in the plan as Task 2.7 (both entry points refuse to start; AUTO-DISPOSABLE: LOW, no production build exists before Phase 3).
- **[LOW]** LOW-010: the Phase 1 documentation residue — AGENTS.md Database Notes and Local Run Steps 3–8, `data-flow-map.md`, `threat-model.md` (`language_model_absent_reason`, the pipe name, the old remedy constants), `retention-schedule.md`, `docs/lessons.md`, `incident-process.md`, `docs/design-system.md` (the dev line and its prefix, the Status checkbox), `scripts/README.md`, and the shared Credential Manager namespace as a named residue — Triage: Fix-now (as planned work); Decision: Applied — included in H.1 as the "Phase 1 review round 9 pointers" list (`scripts/README.md` and `docs/design-system.md` were already there).

### Round 10 - 2026-10-02 - Phase 1 (Tasks 1.1–1.8), in-session /review-loop pass 2 — re-review after round 9's fix (executor stage-1 leg i1-x6)

- Round status: Closed — all 5 dispositions applied; composer-run suite 5 green on 2026-10-03 (ruff clean, mypy 57 files, pytest 5422 passed / 9 skipped, the expected +5; `.cursor/loops/stage-1-suite5-pytest.txt` in the main checkout). Closed by executor leg i1-x7 at 2026-10-03T00:05:37+10:00. `/review-loop` CONVERGED here: there are no CRIT/HIGH/MED findings, and every survivor is a LOW that is now fixed and verified.
- Source: Claude Code
- Reviewer: executor `claude-opus-5-5` (high), two independent read-only lenses run in parallel:
  - **(a) post-fix regression** over each round-9 fix, its tests and docstrings, plus a sweep of `desktop/src/scribe_desktop/` for source-checkout-only commands (`.venv`, `pip install`, `scripts/`, `AGENTS.md`) that a packaged build could show;
  - **(b) missed-issue** over the whole Phase 1 diff, covering C8 (every store root, the lock, the exclusions walk), every path to the one Cliniko write under the dev guard, the identity of both processes and the register script, and the extension builds.
- Baseline: `git diff main` in `C:\scribe-build` plus the untracked new files (as round 9). Rounds 1–9 were not re-read except as context.
- Finding verification: 18 candidates; 13 dropped (no matching file:line evidence, or already handled); 0 downgraded. Every survivor was re-read at its cited lines by the executor.
- Round classification:
  - ⚡ fix-induced: LOW-001 and LOW-003 (round 9's new scan and its `KEY.md` rewrite, each left incomplete);
  - 🆕 pre-existing: LOW-002, LOW-004 and LOW-005;
  - no 🔁 same-family recurrence.
  - skew=none: 2 of 5 are fix-induced, both LOW and test-harness or documentation only, and no runtime behaviour changed.
- Dropped in verification:
  - **The round-9 fixes:** both restored `TestCheckWer` methods are collected. The frozen-parametrised raises all fire before any ML import, under `tmp_path` with the registry patched. The dev-write tests fail under the old behaviour. No signal loop: `blockSignals` wraps the re-set, and `refresh_write_control` only reads the file. The checkbox and the Write button read the same file and root, and `load_dev_settings` never raises. `NoteConfigError` covers every save failure. The `exclusions.py` allow-list entry is matched by owner, so it covers only that one assignment.
  - **The source-command sweep:** every `.venv`, pip or `AGENTS.md` line sits behind an `is_frozen()` branch, and every other hit is a docstring or comment.
  - **C8:** a dev run touches the production folder only through `_hold_lock_file`'s `mkdir` and the empty `app.lock`; `mark_not_indexed` and `check_location` walk only the dev folder.
  - **The write path:** the one `write_draft_note` call is reached only through `_on_write_requested` → `refuse_before_read` → hop 1 → `_prepare_attempt` → `prepare_write`, which re-reads the setting → hop 2, back to back on the GUI thread. `ui/bridge.py` and `ui/recovery.py` have no write path, and production never reads `dev.json`.
  - **Identity:** each process takes its channel from its own `sys.frozen`, and every accessor is read at call time. The register script never touches the production key, manifest or launcher.
  - **Extension:** an unknown mode is refused, the two output folders are separate, and the vitest setup file is never in a bundle.
  - **Minor items:** a dev-created production folder holding only `app.lock` without the not-indexed mark (a later production start marks it); `pipe_client`'s local variables shadowing the module; reading `dev.json` per control update (dev only, negligible); pipe-name collision (a SID starts with `S-`); `--out` outside `extension/` (the key gives ID stability only); dev `--unregister` removing the shared per-user WER values (Task 2.4); 8.3 names and junctions in `install_root` (`realpath`; Task 2.7); the HKCU-only read (Task 2.3).

#### Findings

- **[LOW]** LOW-001: `desktop/tests/test_install_layout.py` `test_no_other_script_remedy_is_spelled_in_src` — round 9's AST remedy scan was case-sensitive and forward-slash only (`run\s+scripts/`), and its self-test checked `"run scripts/" in text` instead of the scan's own pattern, so a "Run scripts\…" line or a broken regex would pass — ⚡ — Triage: Fix-now; Decision: Applied. A module-level `_REMEDY_PATTERN = re.compile(r"run\s+scripts[/\\]", re.IGNORECASE)` is shared by the scan and by a now-parametrised self-test with four cases (`+` concatenation, a newline split, a capitalised backslash f-string, an implicit concatenation across lines). A pre-check grep of `src` (single-line and across lines) found no current match outside `install_layout.py`.
- **[LOW]** LOW-002: `desktop/tests/test_install_layout.py` `test_no_cliniko_scribe_folder_is_built_outside_install_layout` — the docstring listed "an f-string that splits the name around a placeholder" as unseen, but `_folded_str` joins an f-string's literal parts, so `f"Cliniko{x}Scribe"` IS seen — 🆕 — Triage: Fix-now; Decision: Applied. The docstring now says so and keeps "a placeholder that supplies part of the name" as unseen; a must-see case `f"{base}\\Cliniko{x}Scribe"` was added.
- **[LOW]** LOW-003: `extension/KEY.md` — round 9's lost-key steps named `src/channel.ts` only, but the host registration writes `allowed_origins` from `identity.py`'s `EXTENSION_ID` / `DEV_EXTENSION_ID`, so following them would register the old id ("host not found") — ⚡ — Triage: Fix-now; Decision: Applied (it now names both files and why).
- **[LOW]** LOW-004: `desktop/src/scribe_desktop/draft_write.py:1158-1160` vs D4 — with dev writes off, the Write click is refused before hop 1, so D4's "reads and verification still work, so the safeguards can be smoke-tested without writing" overstated what is reachable. The write path's own pre-write checks and the reconcile of an attempt left open do not run until the box is ticked — 🆕 — Triage: Fix-now (plan record; dev channel only, no production surface); Decision: Applied. The code keeps D4's first bullet as written (the guard in `refuse_before_read`, no request on a refused click), and D4 gains an AS-BUILT sub-bullet that names what "reads and verification" covers and how to smoke-test the pre-write checks or reconcile an open attempt. AUTO-DISPOSABLE: LOW, dev-only, do-the-work.
- **[LOW]** LOW-005: `desktop/src/scribe_desktop/draft_write.py:1323-1378` (`send_write`, `write_for_click`) — hop 2 does not re-check the dev guard; it holds only because `prepare_write` is the sole builder of a `PreparedWrite` (defence in depth; no bypass exists today) — 🆕 — Triage: Fix-now; Decision: Applied. `test_dev_write_guard.py::test_only_prepare_write_builds_a_prepared_write` is an AST pin: every `PreparedWrite(...)` call in `src` must sit in `draft_write.prepare_write`, with a self-check that the visitor sees an attribute-form call.

### Round 11 - 2026-10-03 - Phase 1 (Tasks 1.1–1.8), independent cross-family codex peer review (pass stage-1.p1, peer_round 1 of cap 5; four file-scoped slices)

- Round status: Closed (0 pending — PR-LOW-016 Applied by leg i1-x9; the composer-run full desktop suite confirms it)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: the whole uncommitted Phase 1 diff in worktree `C:/scribe-build` (`git diff main` + the 7 new files), read in four slices — A identity/layout/Chrome link/scripts (15 files), B data stores/models/app write guard (17), C extension channel build + new test modules (12), D changed existing tests (11); composer transcription of the four slice outputs (`.cursor/loops/stage-1-peer-r11{A,B,C,D}.log`), slice-local ID `PR-LOW-C01` renumbered to the plan's one counter.

#### Findings
- **PR-LOW-016** (LOW, test-harness, `desktop/tests/test_install_layout.py:231`): Source-model tests leave `is_frozen()` dependent on host state, contrary to C6 and the module's injection claim. The same omission affects the unset-environment test and `test_every_store_is_under_the_channels_folder`. — Evidence: "`use_channel(monkeypatch, which)`" followed by "`assert install_layout.models_root() == tmp_path / folder / "models"`"; `desktop/tests/conftest.py:45` explicitly says "`is_frozen()` is NOT pinned", and `desktop/src/scribe_desktop/install_layout.py:148–150` branches on it before resolving the actual executable. Recommendation: Fix-now — Explicitly call `use_frozen(monkeypatch, False)` in these source-layout tests. /fix decision: Applied — /fix notes:
  - **The class-level form of the peer's remedy.** `conftest.py` pins `install_layout.is_frozen` to `False` in two places: `pytest_configure`, before collection, so the import-time real-ML `skipif` gates are covered; and the autouse `_production_channel`, through `use_frozen(monkeypatch, False)`.
  - `REAL_IS_FROZEN` is captured beside `REAL_CHANNEL`, and both docstrings are updated.
  - Every source-run test is now independent of the host's `sys.frozen`, and `use_frozen(monkeypatch, True)` still overrides per test.
  - **Siblings:** all of them are covered by the pin with no assertion changed. That includes the three cited tests, the dev-registration test, the `setup-models` remedy tests in `test_ui_models` / `test_language_model_runtime` / `test_speaker_embedding` / `test_transcription` / `test_speech`, `test_exclusions`' `check_wer` comparisons, and the five real-ML gates.
  - **The five child processes in `test_integration_no_sockets.py`** each pin `install_layout.is_frozen = lambda: False` beside their existing channel pin.
  - **`test_install_layout.py`:** `test_is_frozen_reads_sys_frozen` now restores `REAL_IS_FROZEN` before checking the real function. `test_the_tests_run_pinned_to_production` sets `sys.frozen = True` and asserts `is_frozen()` stays `False` and `install_root()` is `None`, so the pin is proven against the host value. The module docstring now says how `sys.frozen` is injected.
  - **Verified:**
    - every reader of `sys.frozen` in `src`/`scripts` goes through `install_layout.is_frozen` (only `install_layout.py:81` reads it);
    - no `src` or `scripts` module binds `is_frozen` by `from … import`, so the module-attribute pin reaches every caller;
    - ruff clean, mypy clean (57 files);
    - the full desktop suite is composer-run.
  - /fix date: 2026-10-03T00:41:10+10:00 — /fix applied by: Claude Code (executor stage-1 leg i1-x9).
- Verification counts: 41 claims checked, 1 confirmed, 3 dropped as unverifiable (slice A 15/0/0, B 3/0/3, C 12/1/0, D 11/0/0); slices A, B and D reported 0 findings.
- Last reviewed: 2026-10-03

#### LEG 1 verified tuples

Executor leg i1-x8, 2026-10-03T00:37:33+10:00, verification only. Nothing was fixed. The claim was checked against the current worktree and is CONFIRMED.

- PR-LOW-016: materiality=behavioral severity=verified low surface=test-harness rec=Fix-now — CONFIRMED. **Final disposition (LEG 2, leg i1-x9, 2026-10-03T00:41:10+10:00): Applied**, with every sibling below covered by the class-level conftest pin plus the five child-process pins. The composer-run suite is pending.
  - **The cited lines:**
    - `test_install_layout.py:231-234` runs `use_channel(monkeypatch, which)` / `monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))` / `assert install_layout.models_root() == tmp_path / folder / "models"` with no `use_frozen`;
    - `:242-245` (`test_a_source_run_without_localappdata_raises`) and `:284-300` (`test_every_store_is_under_the_channels_folder`, through `_builders()`'s `benchmark.default_models_root()`) do the same.
    - `install_layout.py:159` `root = install_root()` → `:146` `if not is_frozen(): return None` → `:148` `Path(os.path.realpath(executable()))`.
    - `conftest.py:45-47` says "``is_frozen()`` is NOT pinned — a source run's models root and remedies stay as they are".
    - So each test reads the real `sys.frozen`, contrary to C6 and to the module docstring ("``sys.frozen``, ``sys.executable`` and ``LOCALAPPDATA`` are injected per test").
  - **Impact:** test-harness only. pytest under a PyInstaller interpreter is the only host where `sys.frozen` is set, so no runtime behaviour or current result changes. But the C6 promise is unenforced: under such a host these tests would hit the real `sys.executable` and fail with `InstallLayoutError` rather than test anything.
  - **The fix, at the class level rather than per test:**
    - pin `is_frozen()` to `False` in the conftest's autouse fixture beside the production channel (source run: production channel, not frozen — today's real state, now injected);
    - keep a `REAL_IS_FROZEN` capture, as `REAL_CHANNEL` is kept, for `TestChannel.test_is_frozen_reads_sys_frozen` and `test_the_channel_is_production_exactly_when_frozen`;
    - update the conftest docstring;
    - `use_frozen` still overrides per test.
    - This also covers every sibling below without touching them, and no assertion changes.
  - siblings (every other test that resolves a frozen-branching `install_layout` path or line — `install_root`, `models_root`, `default_models_root`, `model_remedy`, `registration_remedy`, or the `is_frozen()` branches in `language_model._import_llama`, `speaker_embedding.load_onnx_session`, `ui/models.language_model_absent_reason`, `exclusions.wer_not_excluded_line` and `StatusPanel.refresh_registration` — without `use_frozen`):
    - `test_install_layout.py`: the three tests above, plus `test_the_dev_registration_names_the_dev_host_and_extension` (`:303`, the register script at import);
    - `test_ui_models.py:376,379,447,454,543` (the "setup-models" remedy lines);
    - `test_language_model_runtime.py:91` (default path under the models root) and `:446-452` (`--only language-model` / `setup-models.py`);
    - `test_speaker_embedding.py:95` (default path), `:289`, `:318` (`[ml]`), `:459` and `:568` (`setup-models`);
    - `test_transcription.py:976` and `:1034`, and `test_speech.py:323` (`setup-models`);
    - `test_exclusions.py`'s `check_wer` tests that compare against `wer_not_excluded_line()` (they compute both sides from the same function, so they cannot diverge, but they still read the host);
    - the import-time real-ML skip gates through `benchmark.default_models_root()` — `test_integration_no_sockets.py:126`, `test_speech.py:461`, `test_speaker_embedding.py:575`, `test_benchmark.py:250`, `test_transcription.py:1384` — which the conftest's `pytest_configure` should pin too, since they run before any fixture (Task 2.6 then re-points them at the dev root).
    - Tests that already pin it: `TestInstallRoot`, the frozen `TestModelsRoot` cases, `TestRemedies`, `TestEveryRaisedModelLineFollowsTheBuild`, `test_exclusions.py:292`.

Cap verdict: accept — test-harness — peer_round 1 of cap 5. This is the pass's only survivor, a LOW harness gap with no production surface and no current failing or wrong result. Its fix is one conftest pin of a state the suite already runs in. Slices A, B and D (43 of 55 files) reported 0 findings. So a fix plus one confirmation round fits well inside the existing cap, and no raise is warranted.

Fix-delta self-check: PASS. I re-read the 5 applied hunks across 3 files:
- the conftest pin, its capture and its docstrings;
- the two `TestChannel` tests and the module docstring;
- the five child-process pins.

No neighbouring exit path changed. `REAL_IS_FROZEN` is captured at conftest import, before `pytest_configure` replaces the function, as `REAL_CHANNEL` is. Monkeypatch teardown restores the configure-time pin, not the host function. The `sys.frozen = True` assertion is undone by monkeypatch at teardown. No drive-by edit.

### Round 12 - 2026-10-03 - Phase 1 confirmation of round 11's fix, independent cross-family codex peer review (pass stage-1.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Specified conftest and child-process diffs, complete test_install_layout.py, install_layout.py function lookup, and Round 11’s finding and sibling record; read-only confirmation of PR-LOW-016, pin coverage, teardown, non-vacuous assertions, and comment accuracy.

#### Findings

- Verification counts: 12 claims checked, 0 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-03

### Round 13 - 2026-10-03 - Phase 2 (Tasks 2.1–2.7), in-session /review-loop pass 1 (executor stage-2 leg i2-x2)

- Round status: Closed. All 14 were Applied by leg i2-x2 at 2026-10-03T01:48:24+10:00. Composer-run suite 2 is green: ruff clean, mypy 58 files, pytest 5555 passed / 20 skipped, exactly the expected +28. The 20 skips are unchanged (9 symlink, 11 real-ML on the empty dev root); the run is in `.cursor/loops/stage-2-suite2-pytest.txt` in the main checkout. Closed by executor leg i2-x3 at 2026-10-03T01:54:55+10:00.
- Source: Claude Code
- Reviewer: executor `claude-opus-5-5` (high). Two independent read-only lenses ran in parallel, then the executor re-read every survivor at its cited lines and merged them:
  - **(a) correctness and security** over every changed source file, read in full;
  - **(b) plan adherence, test quality and missed issues**: each task's `Done when:` and as-built claims checked against the code, plus C2, C6, C8 and the source scan.
- Baseline: `git diff HEAD` in `C:\scribe-build` (branch `installation-build`, HEAD `a7337a2` = Phase 1), plus the untracked `ui/hardware_check.py`, `tests/test_frozen_runtime.py` and `tests/test_hardware_check.py`. The plan file was read as context only.
- Files read: the 11 changed or new modules under `desktop/src/scribe_desktop/` in full, the 16 changed or new test modules, and this plan's D6/D8–D11, C1–C8 and Phase 2 task text.
- Suites at review (composer suite 1): pytest 5527 passed / 20 skipped; ruff clean; mypy 58 files; `npm run qa` 13 files / 313 tests.
- Finding verification: 17 candidates (lens (a) 6, lens (b) 9, the executor's own read 2); 1 dropped; 0 downgraded; 2 merged (the executor's and lens (b)'s duplicate-model finding are MED-001; the two lenses' worker-exception findings are MED-003).
- Dropped in verification:
  - An empty REG_SZ default value read as the winning Chrome link. Chromium's `RegKey::ReadValue` succeeds on an empty string, so Chrome uses it too, and our reading matches.
  - Lens (a) confirmed the rest as fine; its list is not repeated here.

#### Findings

**MED-001 — the hardware check can hold a second 2.3 GiB language model**

- File: `desktop/src/scribe_desktop/ui/hardware_check.py:127-129` (`build_prose_stage(..., cache=None, ...)`)
- Triage: Fix-now
- Why it matters: `ui/models.py:3238-3244` keeps ONE resident model per process because "two copies must never be resident", and `cache=None` is documented as a test seam (`:3305`). After the Note tab has rendered any prose note, the benchmark loads a fresh copy beside the cached one, about 4.7 GiB in total, on the clinic hardware the check is meant to judge.
- Current behaviour: a fresh model per check. Desired behaviour: the check uses the process's one cache (`LocalLanguageModel.complete` holds its own lock, so sharing is safe). When the model is already resident the load is not timed, and the line says so.
- Pattern to follow: `build_prose_stage`'s default `cache` (the Note tab's).
- Pattern siblings: `cache=None` elsewhere in `src`: none (the other uses are tests).
- Verification: a test with an injected cache that already holds the model shows "model already loaded" and makes no factory call. A test with an empty cache loads once and leaves the model in that cache. No test touches the process-wide cache.
- /fix decision: Applied
- /fix notes:
  - **The change:** `run_prose_benchmark` gained a `cache` seam, defaulting to `models._LANGUAGE_MODEL_CACHE` (the Note tab's), and passes it to `build_prose_stage`.
  - **The result:** `benchmark.ProseBenchmark` gained `preloaded`, set when the factory was never called. `prose_report` then says "model already loaded" in place of "load x s".
  - **Loading:** a model this check loads stays resident, as the Note tab's first prose note would leave it. A load failure the cache remembers comes back as the stage's own load-failed line.
  - **Docs:** the module docstring and Task 2.5's as-built note are updated.
  - **Tests (`test_hardware_check.py`):** every runner test passes a fresh `_LanguageModelCache`. Added:
    - `test_a_resident_model_is_used_and_no_load_is_timed`;
    - `test_the_default_cache_is_the_note_tabs`;
    - `test_a_load_failure_the_cache_remembers_is_skipped_with_its_line`;
    - in the timing test, the model staying in the one cache it was given.
  - **Siblings:** none; `cache=None` in `src` was only here.
- /fix date: 2026-10-03T01:48:24+10:00
- /fix applied by: Claude Code (executor stage-2 leg i2-x2)

**MED-002 — a prose stage whose every model call fails is reported as OK**

- File: `desktop/src/scribe_desktop/ui/hardware_check.py:145`
- Triage: Fix-now
- Why it matters: `errored` counts `model_error` sections, which have no rendering and whose time is only the time to fail (`prose_style.py:548-551,566-571`). These are counted in `rendered`, so a runtime that raises on every call gives "3 of 3 sections … 0.1 s per section OK".
- Desired behaviour:
  - Any model error is a named skip: "the language model failed on N of M sections".
  - `rendered` is `passed + failed`, the calls that returned text.
  - Nothing rendered (every section too long) is a named skip, never an "ok" from 0.0 s.
- Verification: tests where the mock model raises on one call and on every call, and where every section is too long. Each must be skipped with its line.
- /fix decision: Applied
- /fix notes:
  - **The change:** `model_errors = errored - too_long`. Any model error skips with "the language model failed on N of 3 sections".
  - `rendered = passed + failed`. When it is 0, the run skips with "no section could be given to the language model".
  - **Tests:** `test_a_failed_model_call_is_never_a_verdict`, for 1 and 3 failing calls; its verdict reads "prose stage not timed". Also `test_nothing_rendered_is_never_a_verdict`, where a mock's tokenizer overflows the window.
  - **Siblings:** none. `rendered` is computed only here, and the Note tab's counts (`ui/models.py:3436-3450`) already split errors from too-long sections.
- /fix date: 2026-10-03T01:48:24+10:00
- /fix applied by: Claude Code (executor stage-2 leg i2-x2)

**MED-003 — the packaged benchmark worker has no exception boundary**

- File: `desktop/src/scribe_desktop/benchmark.py` `run_worker` (`return main(list(argv[2:]))`); `app.py:566`
- Triage: Fix-now
- Why it matters: the worker is dispatched before `install_exception_hooks`. Any error — a corrupt model, `OfflineEnvError` — escapes `app.main` in a windowed packaged exe.
  - PyInstaller's windowed bootloader then shows an "Unhandled exception" traceback box from a child the user never started (unless the spec sets `disable_windowed_traceback=True`; the Phase 0 spike spec does not). `run_all` waits up to its 600 s timeout.
  - Without the box, the full traceback (paths included) reaches the panel through `proc.stderr` (`benchmark.py:554`). That breaks the Phase 6 rule that `scribe-app` reports type names only (C3).
  - Lens (b) also raised this as a LOW (worker traceback on screen); merged.
- Desired behaviour: `run_worker` catches `Exception` around `main`, writes ONE `benchmark_worker error_code=<type name>` line to stderr (stderr only, no log file) and returns 1. Task 3.2's spec sets `disable_windowed_traceback=True` for both executables (recorded on Task 3.2).
- Verification: a test whose worker `main` raises a `ValueError` carrying a name returns 1, and stderr holds the type name and not the message. The `SystemExit` of an argparse error still passes through.
- /fix decision: Applied
- /fix notes:
  - **The change:** `benchmark.run_worker` wraps `main` in `except Exception`. It prints `benchmark_worker error_code=<exception_type_name>` to stderr (when there is one) and returns 1.
  - `benchmark.py` now imports `exception_type_name` from `logging_setup`, which imports only `install_layout`, so there is no cycle.
  - **The spec half:** recorded on Task 3.2 as `disable_windowed_traceback=True` for both executables. That box can also come from an exception escaping `app.main` itself.
  - **Tests (`test_frozen_runtime.py`):**
    - `test_a_worker_exception_is_one_type_name_line`: stderr is exactly the line, "Jane" is absent, and stdout is empty.
    - `test_a_worker_exception_with_no_stderr_is_still_exit_1`.
    - `test_an_argparse_exit_passes_through`.
  - **Siblings:** none. The source-run worker (`python -m scribe_desktop.benchmark`) runs `main` from `__main__`, which is the pre-existing Phase 2 baseline, not this task's entry; it is named as a residue in the handoff.
- /fix date: 2026-10-03T01:48:24+10:00
- /fix applied by: Claude Code (executor stage-2 leg i2-x2)

- **[LOW]** LOW-001: `ui/hardware_check.py:132-134` — the per-section CPU figure includes the model load, while the wall figure (`model_seconds`) excludes it, so "4.0 s wall and 10.0 s CPU per section" mixes bases — Triage: Fix-now; Decision: Applied. `timed_factory` clocks wall and CPU around the load. `ProseBenchmark.wall_seconds` and `cpu_seconds` cover the sections only, with the load subtracted. The line reads "load x s; sections y s wall, z s CPU; …". The timing test pins the subtraction (7.5 s wall, 3.0 s CPU).
- **[LOW]** LOW-002: `native_host.py` `open_std_stream` — `msvcrt.open_osfhandle` on a stale or invalid non-null handle raises `OSError`, which escapes `binary_stdio` and `main` instead of `host_stdio state=absent` and exit 4 — Triage: Fix-now; Decision: Applied. `open_osfhandle` and `open` are wrapped in `except OSError: return None`. `test_a_handle_the_c_runtime_refuses_is_none` covers stdin and stdout on Windows, with a fake `kernel32` and a refusing `open_osfhandle`, so no real handle is used.
- **[LOW]** LOW-003: `native_host.py` `_log_registration_paths` — `Win32WindowsLayer()` is built inside the broad `except`, so the conftest's C6 sentinel (an `AssertionError` from `__init__`) is swallowed as `state=unreadable` instead of failing a test loudly — Triage: Fix-now; Decision: Applied. The reader is built before the `try`; building the real layer never fails outside tests. Pinned by `test_reaching_the_real_layer_is_never_swallowed`.
- **[LOW]** LOW-004: `benchmark.py` `run_all` / `worker_argv` — the spawn shape is not checked against `is_worker_argv`. In a packaged build a candidate folder named `-x` would start a full second app (its "already running" box), not fail the benchmark — Triage: Fix-now; Decision: Applied. When frozen, `worker_argv` raises `RuntimeError("benchmark worker arguments for <name> are not admissible")`, which reaches the panel's failure line. A source run is unchanged. Pinned by `test_a_packaged_build_refuses_a_shape_its_dispatch_would_not_take` (`-x`, `--models`, empty).
- **[LOW]** LOW-005: `exclusions.py` `native_host_entries` — opens with `KEY_READ`, while Chromium opens these keys with `KEY_QUERY_VALUE`, so a query-only ACL would be passed over here but used by Chrome — Triage: Fix-now; Decision: Applied. Now `KEY_QUERY_VALUE | <view>`. The fake `winreg` records each open's access mask, and the order test asserts it is query-only. The WER and backup reads keep `KEY_READ`; they are not Chrome's lookup.
- **[LOW]** LOW-006: `tests/test_frozen_runtime.py:883-884` — the Task 2.6 skip-gate scan collects only `ast.Name` probes (an attribute call such as `lm.language_model_file_available()` slips through), and it passes any condition that mentions `on_real_ml_root` anywhere, even with an unguarded probe beside it — Triage: Fix-now; Decision: Applied. `_gate_offences` now:
  - matches probes by `Name` or `Attribute`;
  - requires each probe node to sit inside an `on_real_ml_root(...)` argument;
  - finds `skipif` and `on_real_ml_root` called either way.
  - `test_the_gate_scan_sees_what_it_claims` has 6 cases: a bare probe, an attribute probe, and an unguarded probe beside a guarded one are flagged; two guarded forms and a platform gate pass.
- **[LOW]** LOW-007: `install_layout.py:68` `BACKUP_VALUE_NAME = APP_FOLDER_NAME` — a new name carrying the folder name, invisible to Task 1.2's source scan (`test_install_layout.py:355` `_FOLDER_NAME_REFS`) — Triage: Fix-now; Decision: Applied.
  - `BACKUP_VALUE_NAME` joins `_FOLDER_NAME_REFS`.
  - `("exclusions.py", "backup_exclusions")` is allow-listed by name: it reads a registry value of that name and builds no folder.
  - `test_every_allow_listed_literal_still_exists` proves the entry is needed.
  - Added a must-see case (`Path(base) / install_layout.BACKUP_VALUE_NAME`) and a must-pass case.
- **[LOW]** LOW-008: `tests/test_frozen_runtime.py:536-539` `test_the_32_bit_view_only` — checks only `.place` of an entry the test built itself; no real-layer case has only a 32-bit view — Triage: Fix-now; Decision: Applied. Added `TestRealLayerOverAFakeWinreg.test_a_32_bit_view_only_entry_wins` for HKCU and HKLM: only that view populated, it wins, and all four views are looked at. The reader-side test now also pins its Status line.
- **[LOW]** LOW-009: `tests/test_ui_models.py:381-391` `test_models_ready_matches_resolved_availability` — under the production pin and the real `LOCALAPPDATA` it stats this computer's `ClinikoScribe\models` (C6/C8). It is a Task 2.6 sibling that is not a skip gate, so neither the enumeration nor the scan saw it — 🆕 — Triage: Fix-now (test harness, AUTO-DISPOSABLE); Decision: Applied.
  - The test now injects `LOCALAPPDATA=tmp_path` and checks agreement in both states, empty (False) and complete (True).
  - **Sibling found by the exhaustive search:** `test_report_lines_name_the_default_model` (`:366`) also had no injected `LOCALAPPDATA`, and now has one.
  - **Search:** every test call of `model_report_lines(`, `models_ready()`, `vad_model_available()`, `whisper_model_available(resolve`, `speaker_model_available()`, `language_model_available()`, `language_model_file_available()` and `default_models_root()`. Every other hit injects `LOCALAPPDATA`, a `tmp_path` model path, or the dev-root gate.
- **[LOW]** LOW-010: `benchmark.py:109` — the comment says the worker is "dispatched by `app.main` before anything else runs", but it runs after Task 2.7's install-folder check (the `app.py` docstring is right) — Triage: Fix-now; Decision: Applied. The comment now names the install-folder check first.
- **[LOW]** LOW-011: `status.py:57-62` `read_registration_status` — a manifest whose JSON is not an object (`["x"]`), or whose `path` is not a string, raises `TypeError` out of `refresh_registration`. The function's own docstring says a failure "must not crash the app" (LOW-010 of Phase 1's era) — 🆕 — Triage: Fix-now; Decision: Applied. `TypeError` joins the caught set. `test_a_malformed_manifest_is_not_registered_never_a_crash` covers `["x"]`, `{"path": 7}`, `"text"` and non-JSON. The host's own launcher read is already inside its broad `except`.

Fix-delta self-check: PASS. I re-read the 14 applied hunks across 9 files. No neighbouring exit path changed. Points checked:
- **The timing:** `timed_factory` runs only inside `cache.get`, so `preloaded` is exactly "not loaded here". The four-call clock order in the timing test matches the code's order (stage start, load start, load end, stage end; wall then CPU each time).
- **The shared cache:** a remembered failure reaches the stage's `reason` without a factory call. `LocalLanguageModel` serialises `complete` and `count_tokens` under its own lock, so a Note-tab job and the check can share the model.
- **The worker:** `run_worker` still returns `None` before `main` for any non-worker launch.
- **The registry reader:** building it outside the `try` changes nothing in production.
- **No drive-by edit.**
- ruff clean; mypy clean (58 files). The pytest run is the composer's.

### Round 14 - 2026-10-03 - Phase 2 (Tasks 2.1–2.7), in-session /review-loop pass 2 — re-review after round 13's fix (executor stage-2 leg i2-x3)

- Round status: Closed. All 4 were Applied by leg i2-x3 at 2026-10-03T02:05:35+10:00. Composer-run suite 3 is green: ruff clean, mypy 58 files, pytest 5559 passed / 20 skipped, exactly the expected +4. The run is in `.cursor/loops/stage-2-suite3-pytest.txt` in the main checkout. Closed by executor leg i2-x4 at 2026-10-03T02:11:26+10:00. `/review-loop` CONVERGED here: no CRIT/HIGH/MED, and every survivor is a LOW that is now fixed and verified.
- Source: Claude Code
- Reviewer: executor `claude-opus-5-5` (high), two independent read-only lenses run in parallel, then each survivor re-read at its cited lines by the executor:
  - **(a) post-fix regression** over each of round 13's 14 fixes: callers, neighbouring exits, sibling sweeps, vacuous tests, and the plan record;
  - **(b) missed-issue** with fresh eyes over the whole Phase 2 diff (round 13's findings not re-reported).
- Baseline: `git diff HEAD` in `C:\scribe-build` plus the three untracked files (as round 13). The regression baseline is round 13's pre-`/fix` state, as recorded in its Findings Log entries.
- Finding verification: 5 candidates; 1 dropped; 0 downgraded.
  - Dropped: `native_host.open_std_stream`'s `os.O_RDONLY if reading else 0`. Both values are 0 and the C runtime's `_open_osfhandle` ignores the access mode, so it is cosmetic only. Lens (b) did not count it either.
- Round classification: ⚡ fix-induced LOW-001, LOW-002 and LOW-004 (round 13's MED-001/MED-002 fixes); 🆕 pre-existing LOW-003; no 🔁.
  - skew=fix-induced, but all LOW and in one function. The executor is already the premium model, so there is no model to escalate to; action=none.
- Lens (a) confirmed the rest of round 13 as sound: MED-002, MED-003 and LOW-001–011 match the code, each test fails when its fix is reverted, and C1/C2/C3/C6/C8 hold.
- Lens (b) confirmed the rest of the diff as sound: the install-folder refusal's order and comparison, the log keys, the worker, the Chrome lookup, the WER and backup checks, the panel defaults, imports, and C6 across the changed tests.

#### Findings

- **[LOW]** LOW-001: `ui/hardware_check.py:147-152` — since MED-001 the check shares the Note tab's cache, and the load-failure line no longer fits. Two cases — ⚡ — Triage: Fix-now; Decision: Applied.
  - **The cases:**
    - The Note tab failed first: the check showed the Note tab's own line, which ends "this note is shown as Clean clinical", on the Microphone panel.
    - The check failed first: the cache now remembers it for the Note tab too, but the line dropped the "restart the app after fixing this" advice.
  - **The fix:** `run_prose_benchmark` takes the model through `cache.get(timed_factory)` BEFORE building the stage. A `LanguageModelError` there is ONE line, "the language model could not be loaded (<reason>; restart the app after fixing this)", in both cases. The new `hardware_check.RESTART_ADVICE` is added only when the factory ran; the cache's remembered failure already carries it.
  - **Tests:** `test_a_load_failure_is_skipped_with_its_reason` now pins the exact line and that the cache remembers it. `test_a_load_failure_the_cache_remembers_is_the_same_line` (renamed from `…_is_skipped_with_its_line`) pins the same exact line and no "this note". Together they pin `RESTART_ADVICE` to the cache's wording.
  - Task 2.5's as-built note records that a failed load during the check blocks the Note tab's prose until restart.
- **[LOW]** LOW-002: `ui/hardware_check.py:144-146,171-173` — a check that waited on the cache lock for another thread's in-progress load counted that wait as section wall and CPU time, and still said "model already loaded" — ⚡ — Triage: Fix-now; Decision: Applied.
  - The same up-front `cache.get` now runs before the stage clocks start, so the section figures never hold a load (no subtraction left).
  - The timing test's clock order is now load start, load end, stage start, stage end. It pins 2.5 s load, 7.0 s wall and 3.0 s CPU.
  - The verdict was never affected (it uses `model_seconds`).
- **[LOW]** LOW-003: `exclusions.py:456` `check_wer` — in production one unreadable hive (an HKLM key a managed computer denies) made the whole check "could not check", even when the other hive covered both executables — 🆕 — Triage: Fix-now; Decision: Applied.
  - Each hive is now read in its own `try`. The readable hives answer. Only when they leave an executable uncovered AND a hive could not be read is it `wer_unchecked`.
  - Dev (one hive) and both-unreadable behave as before, and the existing tests are unchanged.
  - New: `TestCheckWerProduction.test_one_unreadable_hive_does_not_hide_the_other`, 4 cases (HKLM or HKCU denied; the other covering both → `[]`, or covering one or none → `wer_unchecked`).
- **[LOW]** LOW-004: `benchmark.py` `ProseBenchmark` docstring — listed three skip causes; MED-002 added a fourth ("no section could be given to the language model") — ⚡ — Triage: Fix-now; Decision: Applied (docstring now names all four).

Fix-delta self-check: PASS. I re-read the 4 applied hunks across 3 source files and 2 test files. Points checked:
- **Up-front load:** `cache.get` runs once before the stage, so the stage's own `cache.get` returns the cached model without calling the factory. `load_wall` is non-empty exactly when this check ran the factory, which keeps `preloaded` and the advice choice consistent.
- **`result.reason`:** that path is kept for any other stage refusal.
- **`check_wer`:** with every hive readable, the answer is the same as before. With every hive unreadable it is still `wer_unchecked`, because `all()` over an empty list is True for every name.
- **No drive-by edit.**

### Round 15 - 2026-10-03 - Phase 2 (Tasks 2.1–2.7), independent cross-family codex peer review (pass stage-2.p1, peer_round 1 of cap 5; three file-scoped slices)

- Round status: Closed (0 pending). PR-LOW-017 and PR-LOW-018, with both siblings, were Applied by leg i2-x6 at 2026-10-03T02:22:51+10:00. They are docstring and comment changes only; the composer-run full desktop suite confirms them.
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: the whole uncommitted Phase 2 diff in worktree `C:/scribe-build` (`git diff HEAD` + untracked new files), read in three slices — A source (11 files), B frozen-runtime/registry/exclusion/hardware-check tests (7), C real-ML gates and remaining tests (9); composer transcription of the slice outputs (`.cursor/loops/stage-2-peer-r15{A,B,C}.log`), slice-local IDs `PR-LOW-B01` / `PR-LOW-C01` renumbered to the plan's one counter.

#### Findings
- **PR-LOW-017** (LOW, docs-only, `desktop/tests/test_frozen_runtime.py:13`): The module overstates its host-state isolation: `sys.executable` is not injected in the worker-spawn tests. — Evidence: lines 13–14 claim "`sys.executable` … [is] injected per test"; lines 89–94 only pin `is_frozen` and then expect the real `sys.executable`. Recommendation: Fix-now — Inject an explicit executable in these tests or narrow the module's claim to the isolation actually enforced (C9). /fix decision: Applied — /fix notes: the module docstring (`test_frozen_runtime.py:13-18`) now names what IS injected — `sys.frozen` through `install_layout.is_frozen`, the packaged path through `install_layout.executable`, `LOCALAPPDATA`, the registry and every stream. It also states that `sys.executable` is the one host value used as it is: read only as the benchmark spawn's argv[0], compared as a string, never run (every spawn is faked). No test changed; siblings none (leg 1). /fix date: 2026-10-03T02:22:51+10:00 — /fix applied by: Claude Code (executor stage-2 leg i2-x6).
- **PR-LOW-018** (LOW, docs-only, `desktop/tests/test_language_model_runtime.py:161`): The real-model smoke's documentation claims agent shells cannot read the practitioner's model cache, although the revised test runs whenever the dev model is available. This misstates Task 2.6's execution gate. — Evidence: "agent shells cannot see the practitioner's model cache" (lines 163–164), while lines 171–172 skip only on `if not lm.language_model_file_available():`; the adjacent comment also says "it always skips" (line 159). Recommendation: Fix-now — Describe the actual prerequisites: the pinned runtime and a populated dev model root; remove the unconditional agent-shell claims from both comments. /fix decision: Applied — /fix notes:
  - **The cited lines:** `test_language_model_runtime.py`'s comment above `TestRealModelSmoke` and its class docstring now say it runs wherever the pinned wheel is installed and the dev models root holds the model (Task 2.6, `real_ml_models`). Otherwise it skips by name, the reason naming that root. The "always skips" and "agent shells cannot see" wording is gone.
  - **Both leg-1 siblings, same fix:**
    - `test_language_model_runtime.py`'s module docstring, `TestRealModelSmoke` bullet: the wheel plus the GGUF in `%LOCALAPPDATA%\ClinikoScribe-dev\models`, "skips by name, naming that root, when either is absent - in any shell";
    - `test_speaker_embedding.py:10-13`'s module docstring: skip-marked when the speaker model is absent from the dev models root, the reason naming it. That matches its gate `on_real_ml_root(speaker_model_available)` / `real_ml_skip_reason(...)` (`:578-584`).
  - **Left as is, per leg 1:** the not-siblings (`:18` about the runtime wheel, `speaker_eval.py:1286`, and the register-script and lock-file lines).
  - Comments and docstrings only; no test changed.
  - /fix date: 2026-10-03T02:22:51+10:00 — /fix applied by: Claude Code (executor stage-2 leg i2-x6).
- Verification counts: 27 claims checked, 2 confirmed, 3 dropped as unverifiable (slice A 12/0/2, B 14/1/1, C 1/1/0); slice A reported 0 findings.
- Last reviewed: 2026-10-03

#### LEG 1 verified tuples

Executor leg i2-x5, 2026-10-03T02:20:52+10:00, verification only. Nothing was fixed. Both claims were checked against the current worktree and are CONFIRMED.

- PR-LOW-017: materiality=docs-only severity=verified low surface=test-harness rec=Fix-now siblings=none — CONFIRMED. **Final disposition (LEG 2, leg i2-x6, 2026-10-03T02:22:51+10:00): Applied** — the module docstring is narrowed to the isolation the tests enforce.
  - **What the docstring claims:** `test_frozen_runtime.py:13-14` says "Host state is never read (C6): ``sys.frozen``, ``sys.executable``, ``LOCALAPPDATA``, the registry and every stream are injected per test."
  - **What the tests do:** the Task 2.1 tests use the REAL `sys.executable` without injecting it:
    - `_worker()` (`:73-74`) and `TestWorkerArgv` (`:78-123`): `assert _worker() == [sys.executable, "-m", …]`, `[sys.executable, "--benchmark-worker", …]` and `assert argv[0] == sys.executable`;
    - `TestWorkerDispatch`'s `_worker()` callers, the two `app_module.main(_worker())` tests among them;
    - `test_a_packaged_build_refuses_a_shape_its_dispatch_would_not_take`.
  - **Impact:** the value is read as a string only; every spawn is faked (`benchmark.subprocess.run` patched), so nothing is launched and no behaviour changes. Only the docstring overclaims.
  - **The smaller fix:** narrow the claim to what is enforced. `sys.frozen` / `install_layout.executable()` are injected, and `sys.executable` is read only as the spawn's argv[0] and never run. The alternative is to inject `sys.executable` in those tests.
  - **Siblings:** none. The search covered the docstrings and comments of every Phase 2 test addition and change: `test_hardware_check.py` (presence and clocks injected — true), `TestRealLayerOverAFakeWinreg` ("nothing real is read" — true), conftest `real_ml_*`, `test_status_and_app.py`, and the round-13 `test_ui_models.py` comments. Every other "injected" claim in this module holds: `LOCALAPPDATA` via `setenv`/`delenv`, streams via `SimpleNamespace`/`BytesIO`/fake `kernel32`, the registry via `_Layer`/`FakeWinreg`.
- PR-LOW-018: materiality=docs-only severity=verified low surface=test-harness rec=Fix-now siblings=`test_language_model_runtime.py:19-21` (module docstring); `test_speaker_embedding.py:10-11` (module docstring) — CONFIRMED. **Final disposition (LEG 2, leg i2-x6, 2026-10-03T02:22:51+10:00): Applied**, with both siblings: three docstrings and one comment now name the dev models root (Task 2.6) as the prerequisite.
  - **What the comments say:** `test_language_model_runtime.py:157-159` says "…that file is absent in the executor's shell, so it always skips by name there." `:161-164` says "…it skips by name everywhere else (the file is absent in the executor's shell - agent shells cannot see the practitioner's model cache, docs/lessons.md)."
  - **What the test does:** since Task 2.6 it runs under `@pytest.mark.usefixtures("real_ml_models")` and skips only on `if not lm.language_model_file_available(): pytest.skip(real_ml_skip_reason(...))` (`:166-172`). So it RUNS in any shell, an agent's included, once the dev root holds the model.
  - **Why the claim is unsupported:** Task 2.6's own as-built record names reading the practitioner-created dev folder from the composer's agent shell as the assumption to confirm. `docs/lessons.md`'s MSIX finding concerns redirected WRITES, so "agent shells cannot see" is not established.
  - **Siblings, the same over-claim:**
    - `test_language_model_runtime.py:19-21`: "it skips by name in every other shell (the model file is absent in the executor's)";
    - `test_speaker_embedding.py:10-11`: "the real-model tests are skip-marked when the local cache is absent (agent shells cannot see the practitioner's cache)". Its gate (`TestRealModel`) now looks in the dev root (Task 2.6).
  - **Desired fix:** each should name the real prerequisites — the pinned runtime (for the prose smoke) and a populated `ClinikoScribe-dev\models` root (Task 2.6) — and drop the unconditional agent-shell and "always skips" wording.
  - **Not siblings:** `test_language_model_runtime.py:18` is about the prose RUNTIME wheel not being installed in agent shells and CI, not the model cache. `speaker_eval.py:1286` and the `test_register_native_host.py` / `test_status_and_app.py:411` lines are about write virtualization or a script run from a normal terminal, outside Task 2.6's gates. All are left as they are.

Cap verdict: accept — docs-only — peer_round 1 of cap 5. Both survivors are LOW test-module docstring or comment corrections (4 sites in 3 test files), with no production or test behaviour change. Slice A, all 11 source files, reported 0 findings. A fix plus one confirmation round fits well inside the cap, and no raise is warranted.

Fix-delta self-check: PASS. I re-read the 4 applied hunks across 3 test files: the `test_frozen_runtime.py` module docstring, the `test_language_model_runtime.py` module bullet, its comment and class docstring, and the `test_speaker_embedding.py` module docstring.
- Each claim matches the code: the `real_ml_models` / `on_real_ml_root` / `real_ml_skip_reason` gates, and `_worker()`'s real `sys.executable` used as a string under a faked `subprocess.run`.
- The regular-string backslashes are escaped.
- No code, assertion or test changed, and no drive-by edit.
- ruff clean; mypy clean (58 files).

### Round 16 - 2026-10-03 - Phase 2 confirmation of round 15's fix, independent cross-family codex peer review (pass stage-2.p1)

- Round status: Closed (0 pending) — PR-LOW-019 Applied by leg i2-x8 2026-10-03T02:31:49+10:00 (docstrings only); the composer-run full desktop suite confirms it
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Round 15’s fixes and enumerated siblings in the three specified test modules, checked against their current test code; read-only, no tests or network commands.

#### Findings

- **PR-LOW-019** (LOW, docs-only, `desktop/tests/test_language_model_runtime.py:22`): The revised module and class docstrings incorrectly claim that the missing-runtime skip reason names the dev models root. — Evidence: line 22 says “skips by name, naming that root, when either is absent”; lines 165–166 repeat “without either it skips by name, the reason naming that root.” However, line 170 uses `pytest.importorskip("llama_cpp", reason="the prose runtime is not installed")`; only the missing-model branch at lines 173–174 calls `real_ml_skip_reason`. Recommendation: Fix-now — Narrow both docstrings to say that the missing-model skip names the dev root, while the missing-runtime skip names the runtime. /fix decision: Applied — /fix notes: both docstrings narrowed as recommended. The module bullet (`:19-23`) now reads "skips by name when either is absent, in any shell: a missing runtime says the prose runtime is not installed, a missing model names that root". The class docstring (`:163-167`) reads "a missing runtime as "the prose runtime is not installed", a missing model with the reason naming that root". Both match `:170` (`importorskip(..., reason="the prose runtime is not installed")`) and `:173-174` (`real_ml_skip_reason(...)`). Siblings none (leg 1). Docstrings only; no test changed. /fix date: 2026-10-03T02:31:49+10:00 — /fix applied by: Claude Code (executor stage-2 leg i2-x8).

- Verification counts: 5 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-03

#### LEG 1 verified tuples

Executor leg i2-x7, 2026-10-03T02:30:32+10:00, verification only. Nothing was fixed. The claim was checked against the current worktree and is CONFIRMED. It is fix-induced: leg i2-x6's round-15 wording.

- PR-LOW-019: materiality=docs-only severity=verified low surface=test-harness rec=Fix-now siblings=none. **Final disposition (LEG 2, leg i2-x8, 2026-10-03T02:31:49+10:00): Applied** — both docstrings now separate the runtime skip from the model skip.
  - **The over-claim:** `test_language_model_runtime.py:19-22` (module bullet) says "…and skips by name, naming that root, when either is absent - in any shell." `:163-166` (class docstring) says "…without either it skips by name, the reason naming that root."
  - **The code:** `:170` is `pytest.importorskip("llama_cpp", reason="the prose runtime is not installed")`, which names the runtime, not the root. Only `:173-174` (`if not lm.language_model_file_available(): pytest.skip(real_ml_skip_reason("the pinned language model"))`) names the dev root. The comment at `:158-161` ("skips by name otherwise") is accurate.
  - **Why Fix-now over the D9 default `Accept-with-record`:** the false sentence is OUR round-15 wording, so accepting it would commit a docstring known to be wrong about the gate Task 2.6 depends on. The fix is two clause-level narrowings in one file: the missing-model skip names the dev root, and the missing-runtime skip names the runtime. That is nearly free, carries no behaviour risk, and needs only ruff in-leg.
  - **Siblings:** none. `test_speaker_embedding.py:10-13` claims only that the tests are "skip-marked when the speaker model is absent from the source run's dev models root … the skip reason names that root". Its class gate (`:580-583`, `real_ml_skip_reason("the pinned speaker model")`) does exactly that. The body's `importorskip("numpy")` / `("onnxruntime")` (`:587-588`) is a different case the docstring does not describe. `test_frozen_runtime.py:13-18` (PR-LOW-017's fix) is accurate.

Cap verdict: accept — docs-only — peer_round 2 of cap 5. The trajectory is 2 → 1, and the one survivor is a LOW docstring narrowing in one test file, with no production or test behaviour change. The pass can continue normally after the fix. A confirmation round for a two-clause docstring fix is optional; the composer decides.

Fix-delta self-check: PASS. I re-read the 2 applied docstring hunks in `test_language_model_runtime.py` against `:168-174`. Each skip's stated wording matches its code, the regular-string backslashes are unchanged, there is no drive-by edit, and ruff is clean with mypy clean (58 files).

### Round 17 - 2026-10-03 - Phase 2 confirmation of round 16's fix, independent cross-family codex peer review (pass stage-2.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Current docstrings, edited comments and corresponding test code in the three specified modules; rounds 15–16, their verified tuples and enumerated siblings. Read-only verification; no tests, builds or network commands.

#### Findings

- Verification counts: 5 claims checked, 0 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-03

### Round 18 - 2026-10-03 - Phase 3 (Tasks 3.1–3.9), in-session /review-loop pass 1 (executor stage-3 leg i3-x3)

- Round status: Closed. All 5 were Applied by leg i3-x3 at 2026-10-03T03:31:53+10:00.
  - Composer suite 3 is green: ruff clean, mypy 58 files, pytest 5725 passed / 23 skipped, exactly the expected +2.
  - The ISCC 6.7.3 re-compile succeeded (2.203 s).
  - Closed by executor leg i3-x4.
- Source: Claude Code
- Reviewer: executor `claude-opus-5-5` (high), sequential passes in this session: correctness/security, executor judgment, structural quality, post-fix regression, missed-issue, then finding verification.
- Baseline: HEAD `7cfed96` (the Phase 2 commit, before any Phase 3 work) → `git diff HEAD` in `C:\scribe-build` plus the untracked Phase 3 files. Loop round 1 of cap 3.
- **Changed files, all read in full:**
  - Source: `install_layout.py` and `app.py` (diff hunks, with the surrounding functions).
  - Scripts: `register-native-host.py`, `setup-models.py` (the `--root` hunks plus `models_root` and `fetch_whisper`), and the new `build-release.py`, `lock-build-requirements.py` and `check-installed-sockets.py`.
  - Packaging: `scribe.spec`, `scribe.iss`, `entry_app.py`, `entry_host.py` and `speaker-model-ATTRIBUTION.txt`.
  - CI and docs: `.github/workflows/release.yml`, `docs/release/pilot-builds.md`, `.gitattributes` and `.gitignore`.
  - Tests: the six new modules, and the hunks of the five changed ones.
  - The plan's own text is checked only where a finding cites it.
- **No generated artefacts are in scope.** The lock, the models manifest and the bundle do not exist yet.
- **Focus asked by the composer, each checked:**
  - **C2/C8 — HOLDS:** `--unregister` deletes the dev key, ONE production-named HKCU key and exactly two named files. It never touches HKLM or the folder; the test asserts the registry roots touched are `{"HKCU"}` and that the folder's other files survive.
  - **C3/D8 — HOLDS:** every `[Registry]` entry is `HKLM64`; there is no `{user*}` / `{localappdata}` constant and no `[Run]` / `[UninstallRun]` section; the only process query is WMI `ExecQuery`.
  - **C4 — HOLDS:** `[InstallDelete]` / `[UninstallDelete]` name only `{app}\…` paths, and uninstall's message says the data stays.
  - **C1 — HOLDS:** the network is used only at build and setup time — pip download, `npm ci`, the PyInstaller clone, CI's Inno download, and `setup-models --root`, which downloads into DIR (Hugging Face's default cache is the home folder, not `%LOCALAPPDATA%`). The app adds only the self-check, which opens nothing. `check-installed-sockets.py` uses `psutil`, already a runtime dependency (`pyproject.toml:16`).
  - **C6 — HOLDS after leg i3-x2:** every new test reads fixtures or committed source; a grep for `LOCALAPPDATA` / `os.environ` / `sys.executable` / `subprocess` / `winreg` / `.venv` / `Path.home` across the six new modules finds only the `.iss` text pins.
  - **Task 3.1's freeze source (verified, not assumed):** the worktree `.venv` holds `setuptools`, `packaging` and `pywin32-ctypes`, so `EXTRA_REQUIREMENTS` is pinnable from it.
- Finding verification: 7 candidates; 2 dropped; 0 downgraded.
  - **Dropped 1:** "the Defender scan's 'not run' lets a release pass". This is Task 3.5's chosen behaviour ("where one can run"), and the result is printed.
  - **Dropped 2:** "the model checks hash ~4 GB twice at install, with no progress". This is the D5 design (verify before and after the copy); UX only.
- Round classification: round 1 of this phase's loop, so skew=none.

#### Findings

**MED-001 — an upgrade or rollback leaves the previous build's program files in `{app}`, so the installed tree is not the audited bundle**

- File: `packaging/scribe.iss:68-75` (`[InstallDelete]`, `[Files]`)
- Triage: Fix-now
- Fix route: fix-on-fast (one section of one script, plus its pin)
- **Why it matters:**
  - `[Files] Source: "{#DistDir}\*"; … recursesubdirs` copies over an existing `{app}`, but nothing removes what the previous build had and this one does not. An in-place upgrade (Task 0.3, P.3 step 1) and the rollback "reinstall N over N+1" (P.3 step 2) therefore leave a superset.
  - The concrete risk: a dependency bump renames its `*.dist-info` folder, and then TWO metadata folders for one package sit in `_internal`. `keyring`'s Windows backend is found through that metadata (the spec's `copy_metadata("keyring")`), so its discovery can change after an upgrade.
  - **More generally:** `build-release.py --audit` (no Qt networking file, the offline self-check) proves the BUILT bundle. The installed `_internal` must equal that bundle, or the audit's guarantee does not carry to the computer.
  - The same applies to stale files in `{app}\extension`, the folder Chrome loads unpacked.
- Current behaviour: `[InstallDelete]` clears only `{app}\models`, and only when the models need copying.
- Desired behaviour: `[InstallDelete]` also clears `{app}\_internal` and `{app}\extension` unconditionally. This is safe because the running-process check has already refused while either program or Chrome runs, and the frozen app writes nothing under `{app}`. The folder's top-level files (the two programs and the host manifest) are replaced by name. `{app}\models` keeps its own rule.
- Pattern to follow: the existing `{app}\models` "replaced whole" entry.
- Pattern siblings: none found. Searched: `[InstallDelete]`, `[UninstallDelete]` and `[Files]` (`DestDir:`, `recursesubdirs`) in `scribe.iss`. The `{app}` root holds only the files named by the bundle; the models are covered.
- Verification: `test_installer_script.py` pins both new entries (unconditional, `{app}`-relative), and the models entry is unchanged.
- Regression risk: the uninstall log is unchanged (the files are logged by `[Files]`); C4 holds (`{app}` only).
- /fix decision: Applied
- /fix notes:
  - **The change:** two unconditional `[InstallDelete]` entries, `{app}\_internal` and `{app}\extension`, placed before the models' conditional entry, with a comment giving the reason and the safety argument.
  - **Tests:** the models test now selects its entry by name. The new `test_an_upgrade_replaces_the_program_whole` pins exactly the two unconditional entries and checks that the only conditional deletion is the models'.
  - Task 3.4's note records it.
  - The ISCC compile check still applies: `[InstallDelete]` uses the same syntax as the existing models entry.
- /fix date: 2026-10-03T03:31:53+10:00
- /fix applied by: Claude Code (executor stage-3 leg i3-x3)

- **[LOW]** LOW-001: `scripts/register-native-host.py:15-19` (docstring) and its `--unregister` help — they call the production-named HKCU key "stray", but until Phase P that key is the EVERYDAY source-run app's live Chrome link (`main` still registers the production name). An `--unregister` run in this worktree to clean the dev registration would unlink the clinical app until it is re-registered — Triage: Fix-now; Decision: Applied.
  - The docstring now says that until the app is installed, the key and files are the source-run app's LIVE link. It says to run `--unregister` only as Phase P step 2, or when you mean to unlink that app, and to re-register from its own checkout to undo.
  - The help says the same in short form.
  - The behaviour is Task 3.7's spec and is unchanged.
- **[LOW]** LOW-002: `desktop/tests/test_build_release.py:356` — `HOSTILE_ENV` is a hand-kept copy of `benchmark.OFFLINE_ENV` + `FORBIDDEN_NATIVE_OVERRIDES` + `FORBIDDEN_TLS_OVERRIDES`, but the test pins only a three-name subset. A kill-switch added to the app would not be set wrong by the audit, so its self-check would not exercise it — Triage: Fix-now; Decision: Applied. The new `test_every_variable_the_app_enforces_is_set_wrong` pins the key set EQUAL to those three sources, every kill-switch's value to differ from its required one, and every override to be non-empty. `HOSTILE_ENV` is unchanged; it already matched.
- **[LOW]** LOW-003: `docs/release/pilot-builds.md:37-43` — `Get-FileHash` prints the hash in CAPITALS while `SHA256SUMS.txt` (sha256sum format) is lower case. "The hash must equal" invites a false mismatch for a reader comparing by eye — Triage: Fix-now; Decision: Applied. The doc now says to compare the letters and digits, ignoring capitals.
- **[LOW]** LOW-004: `.cursor/plans/plan-installation.md` (leg i3-x1 handoff bullet, practitioner step 1) — it names `desktop/requirements-build.lock`, but the file the generator writes, the tests read and Task 3.1 names is `desktop/requirements-build.txt` — Triage: Fix-now; Decision: Applied. The step now names `desktop/requirements-build.txt` and "the worktree `.venv`'s freeze", the source Task 3.1's own practitioner step uses (it had said `C:\scribe-spike\venv-build`), and points to Task 3.1 for the commands.

Fix-delta self-check: PASS. I re-read the 5 applied hunks across `scribe.iss`, `register-native-host.py`, two test modules, the doc and the plan.
- **`[InstallDelete]`:** the order is the program folders, then the models. Every `Name` is `{app}`-relative (C4's test still passes over all of them), and `_entry` parses the new lines to exactly the pinned dicts.
- **The register script:** the help string names no `ClinikoScribe` spelling (Task 1.2's source scan) and no "Cliniko Scribe" (the display-name scan).
- **The hostile-env test:** imports `benchmark` only inside the test.
- **No drive-by edit.**
- ruff clean; mypy clean (58 files). The pytest run is the composer's.

### Round 19 - 2026-10-03 - Phase 3 (Tasks 3.1–3.9), in-session /review-loop pass 2 — re-review after round 18's fix (executor stage-3 leg i3-x4)

- Round status: Closed. LOW-001 was Applied by leg i3-x4 at 2026-10-03T03:41:41+10:00.
  - Composer suite 4 is green: ruff clean, mypy 58 files, pytest 5727 passed / 23 skipped, exactly the expected +2.
  - Closed by executor leg i3-x5 at 2026-10-03T03:46:58+10:00.
  - `/review-loop` CONVERGED here at loop round 2 of cap 3: no CRIT/HIGH/MED, and the one 🆕 LOW is fixed and verified.
- Source: Claude Code
- Reviewer: executor `claude-opus-5-5` (high), the full set of sequential passes again over the whole Phase 3 scope (not only the fix delta).
- **Baselines:**
  - Primary: HEAD `7cfed96` (as round 18) → `git diff HEAD` plus the untracked files.
  - Regression: round 18's pre-`/fix` state, recorded in its entries.
- **Read in full this round:**
  - The three new test modules not read in full in round 18: `test_build_lock.py`, `test_build_spec.py` and `test_check_installed_sockets.py`.
  - Every round-18 hunk and its neighbours: `scribe.iss` `[InstallDelete]`, the register script's docstring and help, the hostile-env test, and the pilot-builds doc.
  - `build-release.py`'s run and compile paths.
  - The rest as round 18.
- **Post-fix regression (round 18):**
  - MED-001's entries parse to the pinned dicts. C4 still holds (only `{app}` paths). The delete runs after `PrepareToInstall`'s refusal, and the ISCC re-compile passed.
  - A cancelled upgrade after the program folders are cleared leaves an incomplete install, but Inno never restored overwritten files before this fix either, so a rerun of Setup was already the remedy. Not worse; noted, not a finding.
  - LOW-001–004 changed only documentation and test pins. LOW-002's new test holds against the current `HOSTILE_ENV`.
  - **No regression.**
- **Verified, not assumed:** `INNO_BANNER` ("Compiler engine version: Inno Setup 6.7.3") is the wording the practitioner's real 6.7.3 compile printed (Task 0.3's result, recorded in the plan).
- **Missed-issue pass:** I re-read `build-release.py` `_run`, `preflight`, `compile_installer` and `stage_two`; `release.yml`'s Inno step; `check-installed-sockets.py` `sample` / `watch`; and the three tests above. Result: LOW-001.
- Finding verification: 3 candidates; 2 dropped; 0 downgraded.
  - **Dropped 1:** "`release.yml`'s `cache: npm` can poison a release build". `npm ci` checks every package against the lock's integrity hashes, so a poisoned cache entry fails instead of building.
  - **Dropped 2:** "`SHA256SUMS.txt` is written with Windows line endings, so `sha256sum -c` breaks". There is no evidence: whether the checker accepts CRLF was not established, and the documented check is `Get-FileHash`.
- Round classification: 1 🆕 (pre-existing in the Phase 3 code, not made by round 18's fixes); 0 ⚡; 0 🔁. skew=pre-existing; action=triage-and-ship.

#### Findings

- **[LOW]** LOW-001: `scripts/build-release.py` `compile_installer` (and `_run`'s `Completed`) — ISCC runs with its output captured (for the 6.7.3 banner check), and a failed compile raised only "Inno Setup failed (exit N)". `Completed` kept stdout alone, and stderr, where a compiler error goes, was dropped, so a red CI or local build had no reason on screen — 🆕 — Triage: Fix-now; Decision: Applied.
  - **The fix:** `Completed` carries `stderr`. When the compile fails, or the banner is not the pinned one, `compile_installer` writes ISCC's stdout and stderr to the build's stderr before refusing.
  - The output is the build's own: paths and script lines, never a person's data.
  - **Tests:** the fake runner gains `errors`. New: `test_a_refused_compile_shows_the_compilers_own_words` (exit 2 → the error line on stderr) and `test_a_good_compile_prints_nothing_extra`.
  - **Siblings:** the one other captured call, preflight's `git rev-parse`, already refuses with its own specific line ("is not PyInstaller 6.22.3 at commit …"). Every other build step (pip, waf, PyInstaller, npm, the Defender scan) is not captured and streams to the console. Searched: `capture=True` and `capture_output` in `build-release.py`.

Fix-delta self-check: PASS. I re-read the 3 hunks in `build-release.py` and the 2 test additions.
- `Completed`'s new field has a default, so the existing constructions are unchanged.
- The banner-mismatch path still deletes the output, after printing.
- The good path prints nothing.
- No drive-by edit.
- ruff clean; mypy clean (58 files).

### Round 20 - 2026-10-03 - Phase 3 (Tasks 3.1–3.9), independent cross-family codex peer review (pass stage-3.p1, peer_round 1 of cap 5; three file-scoped slices)

- Round status: Closed (0 pending). All four (PR-HIGH-001–003 verified MED, PR-MED-018 verified LOW) and their siblings were Applied by leg i3-x7 (fix-delta correction to the test fake by leg i3-x8); composer suite 6 5743 passed / 23 skipped, ISCC 6.7.3 re-compile exit 0; confirmed by codex round 21 (0 findings).
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: the whole uncommitted Phase 3 diff in worktree `C:/scribe-build` (`git diff HEAD` + untracked new files), read in three slices — A build, lock and PyInstaller spec (11 files), B installer, release workflow, release record and socket check (7), C app self-check, install layout and the source-run scripts (9); composer transcription of the slice outputs (`.cursor/loops/stage-3-peer-r20{A,B,C}.log`), slice-local IDs `PR-HIGH-A01`/`A02`/`B01` and `PR-MED-C01` renumbered to the plan's counters (PR-HIGH-001–003, PR-MED-018).

#### Findings
- **PR-HIGH-001** (HIGH, behavioral, `scripts/build-release.py:570`): The PyInstaller pin verifies HEAD but accepts modified source files, allowing an unverified bootloader or packager into the release. — Evidence: `head = run(["git", "-C", pyinstaller_src, "rev-parse", "HEAD"], capture=True)` checks only the commit; lines 594 and 600 subsequently build and install that working tree. Recommendation: Fix-now — Verify source-tree integrity before executing it, including tracked changes and untracked build inputs; use a clean checkout of the pinned commit. /fix decision: Applied (as verified MED) — /fix notes:
  - **The tree check:** `preflight` (`build-release.py:589-599`) now runs, after the commit check and before anything is built, `git -C <src> status --porcelain --untracked-files=all --ignored`. A failing status or ANY line refuses with "has local changes or extra files (an earlier build's among them); clone it again into an empty folder: `PYINSTALLER_CLONE`" (`:84`).
    - `--ignored` catches an earlier waf build's ignored output.
    - The check runs before waf, which rewrites the tracked `runw.exe`.
  - **The repository-tree sibling: RECORDED, not refused.** D7 (`:360-362`) says local builds serve "spikes and the model pack", which may carry uncommitted work, and the build of record is CI's clean checkout.
    - `source_state` (`:689`) returns this checkout's commit (or `unknown`) and `clean` / `DIRTY` / `unknown`.
    - `write_build_info` (`:705`) writes `BUILD-INFO.txt` (version, commit, tree) beside the setup program BEFORE `SHA256SUMS.txt`, so it is summed (`:740`).
    - `stage_two` prints `source   : <commit> (<tree>)`, plus a "never the build of record (D7)" warning when the tree is not clean.
    - `docs/release/pilot-builds.md` now records only a build whose `BUILD-INFO.txt` says `tree=clean`.
  - **Tests (`test_build_release.py`):**
    - `test_preflight_refusals` gains `dirty`, `ignored` and `status fails`.
    - `test_the_source_tree_is_checked_whole_before_waf` (`:672`): the exact status argv, on the source, BEFORE `./waf`, with the interpreter and platform injected (C6).
    - `TestTheBuildRecord`: `test_the_source_state` (`:723`, 4 cases: clean, dirty, git failing, not a commit) and `test_the_build_writes_it_beside_the_setup_and_sums_it` (`:734`, a faked `stage_two`).
  - /fix date: 2026-10-03T04:05:03+10:00 — /fix applied by: Claude Code (executor stage-3 leg i3-x7)
  - **Fix-delta correction (leg i3-x8, 2026-10-03T04:12:03+10:00) — a TEST-HARNESS defect, the code unchanged:**
    - **Symptom:** composer suite 5 failed one case, `test_preflight_refusals[status fails-…]`, with the COMMIT refusal.
    - **Cause:** the fake `_Runner` matched each key as a SUBSTRING of the whole joined command line. pytest names the case's temporary folder `test_preflight_refusals_status0`, so the `rev-parse` call (`git -C …\test_preflight_refusals_status0\pyinstaller-src rev-parse HEAD`) also "contained" `status` and got its exit code 128.
    - **Why `preflight` is right as written:** a failing `git status` refuses with "has local changes or extra files … clone it again", fail-closed, and it comes after the commit check. This is the chosen wording for "cannot verify the tree": a fresh clone is the remedy either way.
    - **The fix, as a class:** `_Runner` now matches a key against each command WORD, or the name and stem of its last path part (`_names`: `ISCC` for `…\ISCC.exe`), and never against any part of a path. Every key the tests use is one of those: `--self-check-offline`, `powershell.exe`, `rev-parse`, `status` and `ISCC`.
    - **Guard:** `test_the_fake_runner_matches_words_never_paths` pins this, including a key inside a folder name (`…_status0`, `C:\ISCC-builds`) not answering.
    - **Siblings:** none. The search covered every test fake that matches on a joined line; `test_build_lock.py`'s fake indexes `--dest` by position.
- **PR-HIGH-002** (HIGH, behavioral, `scripts/build-release.py:737`): Standalone `--audit` exits successfully when Defender detects a threat, allowing its documented integration gate to pass a detected bundle. — Evidence: `code = _print_failures("audit", audit_bundle(args.audit, run))`, followed by `print(f"defender : {defender_scan(args.audit, run)}")` and `return code`; the detection never changes the exit status, unlike `stage_two` at lines 683–685. Recommendation: Fix-now — Return nonzero for `detected` and add a fake-runner CLI regression test. /fix decision: Applied (as verified MED) — /fix notes:
  - **The change:** standalone `--audit` now keeps the scan's verdict. On `detected` it prints `FAIL     : <DEFENDER_DETECTED>` and returns 1 (`build-release.py:797-803`). `DEFENDER_DETECTED` (`:115`) is the one wording, which `stage_two`'s refusal now also uses (`:738`, C10).
  - **Unchanged:** `not run (…)` keeps a passing audit's exit 0 (Task 3.5's choice, shown as such).
  - **Test:** `test_a_defender_detection_fails_the_audit_cli` (`test_build_release.py:436`), 3 cases: detected → 1 with both lines; clean → 0; not run → 0.
  - Siblings: none (LEG 1).
  - /fix date: 2026-10-03T04:05:03+10:00 — /fix applied by: Claude Code (executor stage-3 leg i3-x7)
- **PR-HIGH-003** (HIGH, behavioral, `packaging/scribe.iss:288`): Post-copy verification can leave unverified models installed and still display success. If two files change after pack preflight, `FirstModelMismatch` stops at the first; only that file is deleted, leaving the second unchecked. Deletion failure is also ignored. — Evidence: “`Mismatch := FirstModelMismatch(ExpandConstant('{app}\models\'));`”, “`DeleteFile(ExpandConstant('{app}\models\') + Mismatch);`” (288–291), followed by “`Clinic Scribe is installed.`” (308). The generated copy entries use “`Flags: external ignoreversion; Check: ModelsNeedCopy`” without per-copy verification (`scripts/build-release.py:513–514`). Recommendation: Fix-now — Verify every installed model, check cleanup results, and fail installation on any mismatch rather than reaching the success page. /fix decision: Applied (as verified MED, with the sibling) — /fix notes:
  - **One file test:** `ModelFileMatches` (`scribe.iss:179`) is now the single check, used by both `FirstModelMismatch` (before the copy, where any mismatch still refuses) and the new `RemoveDamagedModels` (`:214`).
  - **`RemoveDamagedModels`** checks EVERY manifest file after the copy, with no early exit. It deletes each bad one, checks each `DeleteFile` result (nested `if`s, so it never relies on short-circuit evaluation), and names a removal that failed "(damaged, and could not be removed)".
  - **`ssPostInstall`** (`:324`): any bad copy sets `ModelsIncomplete` and shows "These model files did not copy correctly: … Clinic Scribe is NOT completely installed. Run Setup again with the model pack beside it."
  - **The Finish page** (`:341`) then says "Clinic Scribe is NOT completely installed. … Run Setup again with the model pack beside it, before you open Clinic Scribe." It never says "installed" or "updated".
  - **Sibling (the policy untick):**
    - The removal moved to `ssInstall` (`:313`), so it is done before the previous data is written.
    - It is checked gone: `PolicyLeft := RegValueExists(HKLM64, …)` (`:317`).
    - `RegisterPreviousData` keeps a value that stayed recorded as this installer's (`or PolicyLeft`, `:300`), so the next run retries it and never treats it as someone else's.
    - The Finish page adds "The clinic-only Chrome setting could not be removed. Run Setup again; if it stays, ask whoever manages this computer." (`:355`). HKLM only (C3).
  - **Order assumption, which ISCC cannot check:** Inno writes the previous data (with the uninstall entry) after `ssInstall`. P.3's upgrade smoke exercises it.
  - **Tests (`test_installer_script.py`):**
    - `test_every_copy_is_checked_again` (`:279`, replaces `test_the_copies_are_checked_again`): no `Exit;` in the loop, the delete result checked, `ModelsIncomplete` and the message.
    - `test_a_failed_copy_is_never_called_installed` (`:297`).
    - `test_the_checks_share_one_file_test` (`:304`).
    - `test_a_removal_that_did_not_take_is_said_and_kept_ours` (`:225`).
    - A new `_body()` helper reads one `[Code]` routine.
  - **ISCC re-check:** owed (composer).
  - /fix date: 2026-10-03T04:05:03+10:00 — /fix applied by: Claude Code (executor stage-3 leg i3-x7)
- **PR-MED-018** (MED, test-harness, `desktop/tests/test_frozen_runtime.py:329`): The new self-check test probes the real environment’s installed Qt modules without a seam or named skip, contrary to C6’s review requirement. Its result depends on the executing venv. — Evidence: “The real finder: a source checkout HAS PySide6.QtNetwork” (line 325) and `assert app_module.run_offline_self_check(_SELF_CHECK) == 2` (line 329); `desktop/src/scribe_desktop/app.py:569` selects `importlib.util.find_spec` when no finder is supplied. Recommendation: Fix-now — Patch the default finder for this unit test; keep real package discovery in the packaged audit integration gate. /fix decision: Applied (as verified LOW; SEAMED, not dropped) — /fix notes:
  - **The change:** `test_a_source_run_finds_qt_networking` is now `test_the_default_finder_is_importlibs_at_call_time` (`test_frozen_runtime.py:324`). It patches `app_module.importlib.util.find_spec` to a fake that finds only `PySide6.QtNetwork`, asserts exit 2, and asserts that exactly that one module was asked.
  - **Why seamed rather than dropped:** it still pins what only it pins. With no finder passed, the check asks `importlib.util.find_spec` resolved at CALL time, and a findable module is exit 2 (the `main` test covers only the exit-0 side). It now does so without reading this venv's packages (C6). Real discovery remains the packaged audit's (Task 3.5).
  - Siblings: none (LEG 1).
  - /fix date: 2026-10-03T04:05:03+10:00 — /fix applied by: Claude Code (executor stage-3 leg i3-x7)
- Verification counts: 6 claims checked, 4 confirmed, 2 dropped as unverifiable (slice A 4/2/2, B 1/1/0, C 1/1/0)
- Last reviewed: 2026-10-03

#### LEG 1 verified tuples

Executor leg i3-x6, 2026-10-03T03:58:31+10:00. Verification only; nothing was fixed. Each claim was checked against the current worktree. All four defects are REAL. None meets this round's HIGH bar (ships an unverified binary or model, exposes or alters clinical data, or crashes the installed app at start), so the three HIGHs are DOWNGRADED to MED and PR-MED-018 to LOW.

- PR-HIGH-001: materiality=behavioral severity=verified MED (downgraded from HIGH) surface=build rec=Fix-now siblings=`build-release.py` builds the REPOSITORY working tree as it stands (the spec over `desktop/src`, `scribe.iss`, `npm ci` + build of `extension/`, and the copied `packaging/models-manifest.json`), with no clean-tree check and no commit recorded; that is the same class for a local build — CONFIRMED. **Final disposition (LEG 2, leg i3-x7, 2026-10-03T04:05:03+10:00): Applied** — the PyInstaller source is checked clean before waf; the repository tree is RECORDED in `BUILD-INFO.txt` (D7).
  - **The defect:**
    - `build-release.py:570-575` checks only `head = run(["git", "-C", pyinstaller_src, "rev-parse", "HEAD"], capture=True)` against `PYINSTALLER_COMMIT`.
    - `:594` then builds that WORKING TREE's bootloader (`./waf all`, `cwd=pyinstaller_src / "bootloader"`).
    - `:600` installs it (`pip install --no-deps --no-build-isolation pyinstaller_src`).
    - So modified tracked files or untracked inputs pass the pin. The plan's notes say "the build refuses any commit but `ecd7993…`", which is a commit check, not a tree check; the defect is that the pin is weaker than its purpose (D1: the bootloader built from the pinned SOURCE).
  - **Why not HIGH:**
    - The build of record is the CI artifact (D7, `:360`: "CI artifact with attestation as the build of record"; `build-release.py` "builds the same thing locally, for spikes and the model pack").
    - CI's step is a fresh `git clone --depth 1 --branch v6.22.3`, which cannot be dirty.
    - P.1 step 3 verifies the attestation, so a locally built installer is never what this computer installs.
    - A dirty tree is in reach only of a reused local checkout (for example, a rerun into the same `C:\scribe-release\pyinstaller-src`, Task 3.5's step 1).
  - **Fix note:** waf REWRITES the tracked `PyInstaller/bootloader/Windows-64bit-intel/runw.exe`, so any clean-tree check (`git status --porcelain --untracked-files=all` empty) must run in `preflight`, BEFORE waf. A rerun over an already-built checkout would then be refused with a "clone it again" line. The repository-tree sibling is clean by construction on CI; for a local build, refusing a dirty repo or recording `git rev-parse HEAD` plus a dirty flag in the output would close it.
- PR-HIGH-002: materiality=behavioral severity=verified MED (downgraded from HIGH) surface=build rec=Fix-now siblings=none — CONFIRMED. **Final disposition (LEG 2, leg i3-x7, 2026-10-03T04:05:03+10:00): Applied** — `--audit` exits 1 on a detection.
  - **The defect:** `build-release.py:736-740`:

    ```python
    code = _print_failures("audit", audit_bundle(args.audit, run))
    if not args.no_defender:
        print(f"defender : {defender_scan(args.audit, run)}")
    return code
    ```

    A `detected` verdict is printed but never changes the exit status. `stage_two` refuses it (`:684` `if scan == "detected": raise ReleaseError(... C10 ...)`).
  - **Why not HIGH:** the release build, which is the only path to an installer, refuses a detection, and the line "defender : detected" is on screen. Task 3.2's documented integration gate runs `--audit … --no-defender`, so Defender is not run there at all. What fails open is the exit code of a standalone gate command, which nothing in CI consumes.
  - **Siblings:** none. A standalone "not run (…)" verdict proceeding with exit 0 is Task 3.5's recorded choice ("where one can run", round 18 drop 1), not this defect. Every other exit path in `main` raises `ReleaseError` (exit 1), or crashes non-zero on an unexpected exception.
- PR-HIGH-003: materiality=behavioral severity=verified MED (downgraded from HIGH) surface=production rec=Fix-now siblings=`scribe.iss:283` `RegDeleteValue(HKLM64, '{#PolicyKey}', '{#PolicyValue}')`, the policy untick, also ignores its result (a failed removal is silent and the policy stays); `PrepareToInstall`'s first-match-only checks (`:249`, `:261`) are NOT siblings, since any mismatch there refuses the whole install ("Nothing was changed") — CONFIRMED. **Final disposition (LEG 2, leg i3-x7, 2026-10-03T04:05:03+10:00): Applied, with the sibling** — every copy is checked and removed, each removal is checked, and the Finish page says "NOT completely installed"; the policy removal is checked, kept ours and said.
  - **The defect:** `scribe.iss:288-294`. `Mismatch := FirstModelMismatch(ExpandConstant('{app}\models\'));` stops at the first bad file. `DeleteFile(...)` removes only that one and its Boolean result is discarded. The `MsgBox` is `mbError`, and then `:304-311` shows "Clinic Scribe is installed." / "…is updated.". So a SECOND damaged copy stays in `{app}\models`, unverified, and the install completes.
  - **Why not HIGH:**
    - `PrepareToInstall` (`:259-264`) hashes EVERY pack file before anything is copied, and any mismatch refuses with "Nothing was changed". The post-copy case therefore needs the pack to change, or a copy to corrupt silently, between that check and the copy (a time-of-check-to-time-of-use window), and the double-fault case needs it twice.
    - Inno's own copy reports I/O errors (Retry/Abort).
    - The models are only ever under `{app}` (admin-only, D-I1).
    - The app re-verifies two of the four models at load: the speaker model (`speaker_embedding.py:455` `load_onnx_session(path, expected_sha256=SPEAKER_MODEL_SHA256)`) and the language model (`language_model.py:245` `expected_sha256: str = LANGUAGE_MODEL_SHA256`).
    - **Residue:** whisper `medium`, pinned by commit with no per-file hash at load, has the installer as its only byte check. A damaged copy could degrade transcripts, which the clinician reviews before any note is saved.
  - **Fix note:** check EVERY file post-copy, delete each mismatch and check each `DeleteFile`, and on any failure make the Finish page say the install is NOT complete ("run Setup again with the model pack beside it"). `ssPostInstall` cannot roll the install back, so the honest Finish text plus the deletion is the fail-closed shape.
- PR-MED-018: materiality=test-harness severity=verified LOW (downgraded from MED) surface=test-harness rec=Fix-now — CONFIRMED. **Final disposition (LEG 2, leg i3-x7, 2026-10-03T04:05:03+10:00): Applied** — the test is SEAMED, not dropped.
  - **The test:** `test_frozen_runtime.py:324-329` `test_a_source_run_finds_qt_networking` calls `run_offline_self_check(_SELF_CHECK)` with no finder, so `app.py`'s default `importlib.util.find_spec` probes the executing venv.
  - **Why LOW:** the probed module ships inside a declared hard dependency (`pyproject.toml:12` `"PySide6>=6.8"`; the venv's PySide6 includes `QtNetwork`; `pyproject.toml:96` bans its import). The test cannot vary with this machine's state: if PySide6 were absent, `app` itself would not import. It is still a real package probe with no seam, against C6's letter.
  - **The redundancy:** the default-finder WIRING is already proven seam-fully by `test_app_main_answers_before_the_install_folder_logging_and_qt` (`:357` `monkeypatch.setattr(app_module.importlib.util, "find_spec", lambda name: None)` → exit 0).
  - **Fix note:** patch `app_module.importlib.util.find_spec` to a fake that finds `PySide6.QtNetwork` (it then pins that the default resolves at CALL time to `importlib.util.find_spec`), or drop the test as redundant.
  - **Siblings:** none. The search covered every Phase 3 test for an unseamed host or venv read: `test_build_release.py` reads committed pins and source, and its runner is faked; `test_build_spec.py` executes the spec's own source; `test_build_lock.py`, `test_check_installed_sockets.py` and `test_release_workflow.py` use fakes or committed text; `test_setup_scripts.py` and `test_install_layout.py` inject `LOCALAPPDATA`; `test_register_native_host.py` redirects every production path.

Cap verdict: accept — production-behavioral — peer_round 1 of cap 5. The four survivors are 3 verified MED (one installer path that ships and two build-tool exit paths) and 1 test-harness LOW. Each fix is local: one `[Code]` procedure plus its Finish text; one `preflight` check; one `--audit` exit code; one test seam. All fit one fix leg plus a confirmation round well inside the cap, so no raise is warranted.

### Round 21 - 2026-10-03 - Phase 3 confirmation of round 20's fix, independent cross-family codex peer review (pass stage-3.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Read-only confirmation of round 20’s four fixes, their in-scope siblings, regression risks, test seams and documentation; only the specified files and plan sections. No builds or tests run.

#### Findings

- Verification counts: 4 claims checked, 4 confirmed, 0 dropped as unverifiable (fix closures confirmed; no new findings).
- Last reviewed: 2026-10-03

### Round 22 - 2026-10-03 - Phase H (Task H.2), in-session /review-loop pass 1 over the whole plan diff (executor stage-4 leg i4-x1)

- Round status: Closed. All 31 Applied (3 MED + 28 LOW, written as 22 LOW entries — LOW-011 groups seven lens-C items) by leg i4-x1.
  - Composer suite (2026-10-03 ~04:57) is green: ruff clean, mypy clean, pytest 5754 passed / 23 skipped, exactly the expected +11.
  - The ISCC 6.7.3 compile of the changed `packaging/scribe.iss`: "Successful compile (2.937 sec)", exit 0.
  - Closed by executor leg i4-x2; re-reviewed in round 23.
- Source: Claude Code
- Reviewer: executor `claude-opus-5-5` (high) plus four parallel read-only lenses in this session: A correctness/security of the code, B installer/build/CI, C the doc surface as a class (C9), D tests and seams (C6). Each lens's candidates were re-verified by the executor against the worktree before triage.
- Baseline: `git diff 9f43f8c..HEAD` (Phases 1–3, committed) plus the uncommitted H.1 doc changes in `C:\scribe-build`. Loop round 1 of cap 3.
- Skipped: the generated artefacts (the lock, the models manifest, a bundle) — none exists yet; the extension source (unchanged since Phase 1's review, rounds 9–12).
- Finding verification: 32 candidates; 1 dropped; 0 downgraded below the lens's own severity (lens B's six were raised as LOW and stay LOW).
  - **Dropped (lens D F6):** "the extension test config does not wire the dev/production define, so the build's host name is untested". `vitest.config.ts` deliberately never loads `vite.config.ts` (the crx plugin), the dev and production manifests were checked at Phase 1's composer suite 3, and the release `--audit`'s `audit_extension` checks that the bundle names the installed host.
- Lens totals after verification: A 0 MED / 4 LOW; B 0 MED / 6 LOW; C 2 MED / 13 LOW; D 1 MED / 5 LOW (+1 dropped).
- Round classification: round 1 of Phase H's loop, so skew=none.

#### Findings

**MED-001 — the release-workflow pin test skips a pin that carries a trailing comment**

- File: `desktop/tests/test_release_workflow.py:29` (`_USES`)
- Triage: Fix-now
- Fix route: fix-on-fast (one pattern, its two guards)
- **Why it matters:** `_USES` was anchored `…@(\S+)\s*$`, so a `uses: owner/action@<sha> # vX` line — the usual way a pinned action is written — did not match at all. Once Task 3.6 pins the actions with their version comments, the "every action is pinned to a full commit" test would read NONE of them and pass vacuously.
- Current behaviour: a commented `uses:` line is invisible to the pin and known-action tests.
- Desired behaviour: the pattern accepts an optional `# …` comment; the set of new actions is pinned EQUAL to the known set, so a line the pattern misses fails the test.
- Pattern siblings: none. Searched: every regex over `release.yml` / `ci.yml` in the test modules.
- Verification: `test_the_uses_pattern_reads_a_commented_pin` (a commented and an uncommented line both parse) and `test_every_new_action_is_known` (`set(new) == NEW_ACTIONS`).
- Regression risk: none; the pattern only widens.
- /fix decision: Applied
- /fix notes: `_USES = re.compile(r"^\s*(?:-\s+)?uses:\s*([^\s@]+)@(\S+)\s*(?:#.*)?$", re.MULTILINE)`; `NEW_ACTIONS` names `attest-build-provenance`, `download-artifact` and `upload-artifact` (the last two since LOW B-F3's job split).
- /fix date: 2026-10-03
- /fix applied by: Claude Code (executor stage-4 leg i4-x1)

**MED-002 — `docs/lessons.md` gave stale fix advice for the native-host registration**

- File: `docs/lessons.md` (the registry and WinError 32 lessons)
- Triage: Fix-now
- Fix route: fix-on-fast (doc)
- **Why it matters:** the lessons still told the reader to rerun `register-native-host.py` to restore the Chrome link and models via `setup-models.py`, with the production paths. Since Task 3.7 the script registers ONLY the dev host, and its `--unregister` removes the production-name key that is, until Phase P, the everyday app's live link. Followed literally after Phase P, the advice registers the wrong host or unlinks the clinical app — the lessons file is "required reading before any task".
- Desired behaviour: each lesson says which build it applies to; the installed app's remedy is "reinstall"; `--unregister` is named as the Phase P migration; the WinError 32 lesson notes the script now catches it and names the dev path.
- Pattern siblings: the same stale advice in `scripts/README.md`, `extension/KEY.md` and the incident process — all reconciled in H.1 (C9).
- /fix decision: Applied
- /fix date: 2026-10-03
- /fix applied by: Claude Code (executor stage-4 leg i4-x1)

**MED-003 — the retention schedule's backup rule implied live sessions are excluded from backups (C5)**

- File: `docs/security/retention-schedule.md` (the Phase 6 backup rule)
- Triage: Fix-now
- Fix route: fix-on-fast (doc, as a class with the threat model)
- **Why it matters:** C5 says every document states the backup exclusions as best-effort, never as "excluded". The rule read as if `sessions\` and `logs\` are kept out of backups, a claim the structure cannot back: System Restore does not honour `FilesNotToBackup`, and `FilesNotToSnapshot` is not applied to vssadmin snapshots or Previous Versions.
- Desired behaviour: "only MARKED to be left out", with the residue named and a pointer to the Installation rows; the same wording in the threat model's residue (g).
- Pattern siblings: threat-model residue (g) and the EXCLUSIONS paragraph, data-flow flow 22, `docs/practice/privacy-information.md`, the design-system Status line — each checked or reconciled.
- /fix decision: Applied
- /fix date: 2026-10-03
- /fix applied by: Claude Code (executor stage-4 leg i4-x1)

- **[LOW]** LOW-001 (lens A1): `docs/security/threat-model.md` OPTIONAL POLICY — the foreign-value residue named only the registry, not that the app's verdict and the host log also read a value Setup did not write — Triage: Fix-now; Decision: Applied (residue (2) extended).
- **[LOW]** LOW-002 (lens A2): threat model HKCU SHADOWING — the warning names no remedy and a reinstall does not remove an HKCU key; the doc now says so and names `register-native-host.py --unregister` or removal by hand — Triage: Fix-now; Decision: Applied.
- **[LOW]** LOW-003 (lens A3): the hardware check's prose timing includes a wait on the shared model lock when a Note-tab rendering is in flight, so it can read slow — Triage: Fix-now; Decision: Applied as documentation (design-system "run it with no prose rendering in flight"; D11 AS-BUILT note, which also records that the verdict uses WALL seconds and CPU is only reported).
- **[LOW]** LOW-004 (lens A4): `benchmark.py` `run_worker` docstring named the wrong dispatch step — Triage: Fix-now; Decision: Applied ("``app.main``'s third step, after the build audit's offline self-check and the install-folder refusal").
- **[LOW]** LOW-005 (lens B-F1): `scripts/register-native-host.py --unregister` treated only WinError 32 as "in use", but deleting a RUNNING image gives WinError 5 — Triage: Fix-now; Decision: Applied (`_in_use(exc, *, deleting=False)`: 32, or 5 when deleting; tests: the held-file case parametrized [32, 5]; `test_a_running_image_is_in_use_only_when_deleting`).
- **[LOW]** LOW-006 (lens B-F2): a part-way upgrade (after `[InstallDelete]` cleared the program folders) leaves the app unstartable until Setup reruns, and Setup has no free-space check — Triage: Fix-now; Decision: Applied as a named residue in the threat model's THE INSTALLER (an optional free-space pre-check is recorded for the composer as a future improvement).
- **[LOW]** LOW-007 (lens B-F3): `release.yml` gave the BUILD job `id-token: write` — Triage: Fix-now; Decision: Applied (job split: `build` holds `contents: read` only; a new `attest` job on `ubuntu-24.04` downloads the artifact and attests it, with no `run:` step; the permissions test pins both jobs).
- **[LOW]** LOW-008 (lens B-F4): `docs/release/pilot-builds.md`'s `gh attestation verify` accepted an attestation from any workflow or branch of the repo — Triage: Fix-now; Decision: Applied (`--signer-workflow …/release.yml --source-ref refs/heads/main`, with the reason).
- **[LOW]** LOW-009 (lens B-F5): `packaging/scribe.iss` left a foreign clinic-policy value silently — Triage: Fix-now; Decision: Applied (the Finish page says it was already set by something else and left exactly as it is; `test_a_ticked_box_over_someone_elses_value_is_said`).
- **[LOW]** LOW-010 (lens B-F6): the `PolicyForeign` comment in `scribe.iss` misdescribed the uninstall log — Triage: Fix-now; Decision: Applied (comment corrected; the residue already in the threat model).
- **[LOW]** LOW-011 (lens C items 3–8 and 11, seven one-line items): H.1 doc-class wording corrections across the threat model, the data-flow map, the retention schedule and the incident process, among them the all-users Start-menu shortcut missing from the installer's write list (C5: threat model THE INSTALLER, flow 23, the Components row) — Triage: Fix-now; Decision: Applied (each grep-reconciled across the doc surface, C9).
- **[LOW]** LOW-012 (lens C9): the data-flow Components table lacked the dev extension ID and said the setup script and prose-runtime install run for every build — Triage: Fix-now; Decision: Applied ("for a source checkout only", with where the installed app's models and runtime come from).
- **[LOW]** LOW-013 (lens C10): `docs/design-system.md` gave the source-checkout remedy as THE remedy for a disabled prose style and printed `--only <entry>` as always present — Triage: Fix-now; Decision: Applied (per-build remedy; `[ --only <entry>]` when one model is named, as `install_layout.model_remedy`).
- **[LOW]** LOW-014 (lens C12): AGENTS.md (twice) said the dev channel touches the production folder only through `app.lock`, omitting the one-time `--unregister` migration — Triage: Fix-now; Decision: Applied (AGENTS.md ×2; the C8 AS-BUILT note; data-flow flow 24 and the retention dev row already said it).
- **[LOW]** LOW-015 (lens C13): AGENTS.md named `exclusions.native_host_entries`, a method of the `WindowsLayer` seam — Triage: Fix-now; Decision: Applied (`exclusions.WindowsLayer.native_host_entries`).
- **[LOW]** LOW-016 (lens C14): retention, data-flow flow 8 and AGENTS said the old models are MOVED to the dev folder; Task 2.6 COPIES them and the old copy is deleted at Phase P after the installed models verify — Triage: Fix-now; Decision: Applied.
- **[LOW]** LOW-017 (lens C15): flow 8's model-pack sentence read as if the pack holds whisper `medium` only; AGENTS step 4 lacked "(after Phase P)" — Triage: Fix-now; Decision: Applied.
- **[LOW]** LOW-018 (lens D-F2): five app-side no-sockets children did not pin the production channel, so they could pass in the dev layout without proving the production paths — Triage: Fix-now; Decision: Applied (production channel + `is_frozen=False` in the startup inline child, `_PIPE_APP_CHILD`, `_APP_SERVER_CHILD`, `_PROSE_STAGE_CHILD`, `_CRASH_RECORDER_CHILD`; `_HOST_RELAY_CHILD` stays dev by design; `test_every_app_child_proves_the_production_channel` guards the class). Siblings searched: children in other test modules are behaviour tests with explicit roots, not no-sockets proofs.
- **[LOW]** LOW-019 (lens D-F3): the installer's "no launch" test did not exclude a WMI-driven launch (`Win32_Process.Create`) — Triage: Fix-now; Decision: Applied (COM objects == `WbemScripting.SWbemLocator` only, no WMI action methods, the one `ExecQuery` a SELECT; `test_the_wmi_check_sees_a_wmi_launch`).
- **[LOW]** LOW-020 (lens D-F4): C1 (installer makes no network connection) and C10 (no Defender exclusions) had no pin — Triage: Fix-now; Decision: Applied (`TestNoNetworkAndNoDefenderChange` over `scribe.iss`, `build-release.py` and `release.yml`).
- **[LOW]** LOW-021 (lens D-F5): the spec's version test matched text, not meaning — Triage: Fix-now; Decision: Applied (`VERSION` parsed equal to the pyproject read; each EXE's version is a `_version_info` call; `_version_info` executed with stub classes).
- **[LOW]** LOW-022 (lens D-F7): no test pinned that the host log and the Status tab read THIS channel's registry key — Triage: Fix-now; Decision: Applied (`TestHostRegistrationLog.test_it_reads_this_channels_key`, production and dev).

Fix-delta self-check: PASS. I re-read every applied hunk.
- **Code:** `register-native-host.py` `_in_use` (the copy path still raises on 5); `scribe.iss` `CurPageChanged`'s new note sits under the existing `WizardIsTaskSelected('clinicpolicy')` branch and uses only existing globals; `release.yml`'s `attest` job `needs: build` and consumes the artifact by its uploaded name; `benchmark.py` docstring only.
- **Tests:** every new test reads committed text, fakes or an injected layer (C6); no host read added.
- **Docs:** each corrected phrase grepped across the doc surface (C9); no claim of an installed app (the delivery note says BUILT, NOT YET INSTALLED).
- **No drive-by edit.** ruff clean; mypy clean (58 files). The pytest run and the ISCC compile are the composer's.

### Round 23 - 2026-10-03 - Phase H (Task H.2), in-session /review-loop pass 2 — re-review after round 22's fix (executor stage-4 leg i4-x2)

- Round status: Closed. All 5 Applied by leg i4-x2.
  - Composer suite (2026-10-03 ~05:15) is green: ruff clean, mypy clean, pytest 5758 passed / 23 skipped, exactly the expected +4. No `.iss` or extension change, so no ISCC compile or `npm run qa` was owed.
  - MED-001's network check, run by the composer (read-only GitHub API): `gh repo view eliemokbel3-hub/Recording-clinic-software --json visibility,isPrivate` → `{"isPrivate":false,"visibility":"PUBLIC"}` on 2026-10-03. Attestation is available and D7 holds as designed; leg i4-x3 recorded the fact on Task 3.6 step 0 and in the docs.
  - Loop round 2 of cap 3: a MED was found, so the loop was not converged; round 24 re-reviews. Closed by executor leg i4-x3.
- Source: Claude Code
- Reviewer: executor `claude-opus-5-5` (high) — the post-fix regression check of every round-22 hunk, plus two parallel read-only missed-issue lenses over the whole plan diff (app code; packaging, scripts and CI), each candidate re-verified by the executor before triage.
- **Baselines:** primary `git diff 9f43f8c..HEAD` plus the uncommitted Phase H changes; regression: round 22's pre-`/fix` state as recorded in its entries.
- **Post-fix regression (round 22):**
  - `release.yml`: `attest` `needs: build`, so it is skipped whenever the main-only build is; it downloads the artifact by the uploaded name, and a single-directory upload stores the folder's contents, so `installer/*.exe` matches. The signer workflow is still `release.yml`, so `pilot-builds.md`'s `--signer-workflow` holds after the split.
  - `scribe.iss`: the new Finish note sits after `CurPageChanged`'s `wpFinished` guard and reads only existing globals.
  - `register-native-host.py`: `deleting=True` is passed only on `--unregister`'s deletes; the register path's copy still raises on 5. Its sibling doc was incomplete (LOW-004).
  - Round 22's tests and docs: no regression.
- Finding verification: 8 candidates; 3 dropped; 0 downgraded.
  - **Dropped 1 (app lens LOW-1):** "an empty registry value wins in our reader but Chrome skips it". As I recall Chromium's `FindManifest`, a successful read of an empty value counts as FOUND, and the path is then refused as not absolute, so Chrome fails too and "NOT registered" is the truth. The lens itself flagged its claim as from memory; nothing here changes.
  - **Dropped 2 (packaging lens LOW-1's sibling):** "the Defender scan has no timeout". It shows no window, so it is not the self-check's hang class; a long scan is real work, bounded by the job's own limit.
  - **Dropped 3:** "`--unregister` now calls a genuine access-denied 'in use'". The line says to close everything and run again; a persisting line is now documented as a permission problem (LOW-004). Not a defect.
- Round classification: 4 🆕 (pre-existing in Phases 2–3, missed by earlier rounds), 1 ⚡ (LOW-004, an incomplete sibling of round 22's LOW-005), 0 🔁. skew=pre-existing; action=fix.

#### Findings

**MED-001 — the build of record assumes GitHub can attest this repository, which is unverified**

- File: `.github/workflows/release.yml` (`attest` job); plan D7 and Task 3.6; `docs/release/pilot-builds.md`
- Triage: Fix-now
- Fix route: fix-on-fast (plan step + docs; the check needs the network, so it is the practitioner's)
- **Why it matters:** GitHub produces artifact attestations for public repositories on every plan, but for a private or internal one only on GitHub Enterprise Cloud. Neither the plan nor the repo records this repository's visibility. If it is private on a personal plan, the `attest` job fails on every run, no build is ever attested, and `pilot-builds.md`'s first check — the integrity control for an UNSIGNED build — can never pass. D7's build of record would not exist as designed, and that would surface only after the pins, the push and a full build.
- Current behaviour: Task 3.6's practitioner steps go straight to recording pins and pushing.
- Desired behaviour: Task 3.6 step 0 checks visibility first (`gh repo view … --json visibility`) and STOPS for a D7 decision if attestation cannot work; the External Findings line, threat-model BUILD OF RECORD residue (5), `pilot-builds.md`, PLAN.md's still-to-run list and AGENTS.md's installed-app paragraph say the same.
- Pattern siblings: every place that names `gh attestation verify` as the install check — `pilot-builds.md`, the threat model, AGENTS.md, PLAN.md's delivery note, Task 3.6 step 4 and Phase P.1 step 3 (which follows `pilot-builds.md`). Searched: `attestation verify`, `attest` across the doc surface and the plan.
- Verification: doc and plan only; the check itself is a network step (C1/C7: never from this shell).
- Regression risk: none.
- /fix decision: Applied
- /fix notes: Task 3.6 gains step 0, an AS-BUILT bullet (the job split, the third pin, the Inno exit check), three named actions in step 1, and step 4 pointing at `pilot-builds.md`'s full verify command; External Findings marks the visibility UNVERIFIED; threat-model residue (5) and the second job's description; `pilot-builds.md` paragraph; PLAN.md and AGENTS.md still-to-run lists.
- /fix date: 2026-10-03T05:09:40+10:00
- /fix applied by: Claude Code (executor stage-4 leg i4-x2)

- **[LOW]** LOW-001: `desktop/src/scribe_desktop/status.py` `registration_lines` — in the installed app a BROKEN per-user entry that wins was told "reinstall Clinic Scribe", which cannot fix it (the installer writes HKLM only, C3, and never removes the HKCU key), while the override warning gave no remedy — 🆕 — Triage: Fix-now; Decision: Applied. `PER_USER_BROKEN_REMEDY` ("the per-user Chrome link that Chrome uses is broken, and reinstalling does not remove it") replaces the remedy when `per_user_override` is set (an HKCU entry exists, and Chrome reads HKCU first, so it is the winner); `test_a_broken_per_user_winner_is_not_told_to_reinstall` pins both sides. Siblings: `docs/design-system.md` (the Status line bullet) and `docs/practice/downtime-procedure.md` (the warning's bullet), both updated; the host log reports state, not remedies.
- **[LOW]** LOW-002: `scripts/build-release.py` `audit_bundle` — the packaged self-check ran with no time limit; a frozen app that fails at start shows the windowed bootloader's error box (`disable_windowed_traceback` removes only the traceback), which nobody clicks on a runner, so the build hung to the job limit instead of failing with the audit's reason — 🆕 — Triage: Fix-now; Decision: Applied. `_run` takes `timeout` and reports `TIMED_OUT`; the self-check is bounded at `SELF_CHECK_TIMEOUT_S` (120 s) and a timeout is an audit failure. Tests: `test_a_self_check_that_never_ends_fails`, `test_the_runner_reports_a_timeout_and_refuses_a_missing_tool`.
- **[LOW]** LOW-003: `.github/workflows/release.yml` "Install Inno Setup" and `build-release.py` `_run` — the silent install's exit code was never checked, and a missing `ISCC.exe` (or any tool) ended the build with a raw `FileNotFoundError` traceback, blaming the wrong step — 🆕 — Triage: Fix-now; Decision: Applied. The step uses `-Wait -PassThru`, throws on a non-zero exit, and checks `ISCC.exe` is at `build-release.py`'s `DEFAULT_ISCC`; `_run` turns an `OSError` at launch into a `ReleaseError` naming the program. Test: `test_a_failed_inno_install_fails_the_step` (also pins the path to `DEFAULT_ISCC`).
- **[LOW]** LOW-004: `docs/lessons.md` (the WinError 32 lesson) and Task 3.7 — round 22 LOW-005's WinError 5 handling was not reflected in the lesson that describes the script's in-use handling — ⚡ — Triage: Fix-now; Decision: Applied. The lesson now names `[WinError 5]` on `--unregister`'s deletes, and that a persisting line means a real permission problem; Task 3.7 has an AS-BUILT note.

Fix-delta self-check: PASS. I re-read every hunk.
- `_run`'s new `timeout` defaults to `None`, so every other call is unchanged; `ReleaseError` is defined above it and `main` already turns it into an `ERROR:` line; `TIMED_OUT` (-999) is no real exit code. The fake runners take `**kwargs`, so the extra keyword reaches them harmlessly.
- `registration_lines`: the source-checkout remedy and every registered case are unchanged (the existing tests still state them); the new branch needs `per_user_override`, which is frozen-only.
- The workflow test reads `build-release.py` as the existing pin test does.
- No drive-by edit. ruff clean; mypy clean (58 files).

### Round 24 - 2026-10-03 - Phase H (Task H.2), in-session /review-loop pass 3 — re-review after round 23's fix (executor stage-4 leg i4-x3)

- Round status: Closed. LOW-001 Applied by leg i4-x3; composer suite (2026-10-03 ~05:31) green — ruff clean, mypy clean, pytest 5771 passed / 23 skipped (rounds 24–26 together, exactly the expected +13). `/review-loop` CONVERGED here at loop round 3 of cap 3: no CRIT/HIGH/MED, and the one 🆕 LOW is fixed and verified. No cap raise was warranted. Closed by executor leg i4-x4.
- Source: Claude Code
- Reviewer: executor `claude-opus-5-5` (high) — the post-fix regression check of every round-23 hunk, plus one fresh read-only lens fact-checking the whole H.1 doc surface against the code (the surface round 23's code lenses did not cover).
- **Baselines:** primary `git diff 9f43f8c..HEAD` plus the uncommitted Phase H changes; regression: round 23's pre-`/fix` state as recorded.
- **Post-fix regression (round 23):**
  - `_run`'s `OSError` → `ReleaseError`: no caller catches `OSError` itself; `main` turns `ReleaseError` into an `ERROR:` line in every mode; `source_state`'s git is the same git `preflight` already required, so a missing git still refuses (now with a named line, not a traceback).
  - The bounded self-check: PyInstaller's onedir bootloader runs the app in-process on Windows, so `subprocess.run`'s kill at the limit ends it.
  - The CI Inno check: `${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe` is the path the composer's own local 6.7.3 compile command uses (Task 3.4) and `DEFAULT_ISCC`.
  - `registration_lines`: unchanged for every case but the frozen broken per-user winner.
  - **No regression.**
- **Recorded:** round 23 MED-001's network check, run by the composer — the repository is PUBLIC (2026-10-03), so attestation is available; Task 3.6 step 0, External Findings, threat-model residue (5), `pilot-builds.md`, PLAN.md and AGENTS.md now state the checked fact (a re-check before the pins stays, since visibility can change).
- Finding verification: 1 candidate; 0 dropped; 0 downgraded.
- Round classification: 1 🆕 (pre-existing in Phase 2), 0 ⚡, 0 🔁. skew=pre-existing; action=triage-and-ship.

#### Findings

- **[LOW]** LOW-001: `desktop/src/scribe_desktop/benchmark.py` `is_worker_argv` vs threat model PACKAGED-BUILD ERRORS — the doc says the packaged worker is its own boundary ("one type-name line, exit 1"), but a non-number `--audio-seconds` passed the shape check, so `main`'s parser printed its usage text (with the value) and exited 2 via `SystemExit`, which the boundary does not catch. Reachable only by a hand-made launch with `SCRIBE_BENCHMARK_WORKER=1` (`run_all` always sends a float) — 🆕 — Triage: Fix-now; Decision: Applied. The admission check now also requires the seconds to parse as a float, so such a launch is not the worker (`run_worker` returns `None`) and the doc's claim holds; `test_anything_else_is_not_the_worker` gains the case. The other three values are untyped strings or paths argparse never refuses. Siblings: none — `main` has no other typed option the worker sends.

Fix-delta self-check: PASS. The new check runs after the shape check, so its index is always in range; a float the parser takes is what `float()` takes. ruff clean; mypy clean (58 files).

### Round 25 - 2026-10-03 - Phase H (Task H.3), /simplify over the whole plan diff (executor stage-4 leg i4-x3)

- Round status: Closed. All 3 Applied by leg i4-x3; verified by the composer suite of 2026-10-03 ~05:31 (pytest 5771 passed / 23 skipped, ruff and mypy clean). Closed by executor leg i4-x4.
- Source: Claude Code simplify
- Reviewer: executor `claude-opus-5-5` (high) with one read-only simplification lens over `git diff 9f43f8c -- desktop/src/scribe_desktop/ scripts/ packaging/scribe.spec packaging/entry_*.py`, every candidate re-read by the executor against the conservatism guard (behaviour-preserving, clearly value-positive, not plan-chosen).
- Candidates: 7; kept 3; consciously left alone 4:
  - `worker_argv` spelling the options its frozen branch already checks against `_WORKER_OPTIONS` — a drift fails loudly there and is tested; the spelled tail reads better.
  - `language_model_absent_reason`'s two branches — explicit per channel, byte-identical either way; taste.
  - `lock-build-requirements.py` `EXTRA_REQUIREMENTS` repeating `BUILD_TOOL_PINS`' names — the grouped, commented list is the clearer record of why each is there.
  - The silero path spelled in three modules — only worth it when someone touches it.
  - (The lens's own "left alone" list — the C2 constants, the channel one-liners, the seams and test hooks — was checked and agreed.)

#### Findings

- **[LOW]** SIMP-001: the shipped whisper model was spelled `"medium"` in three places — `transcription.DEFAULT_WHISPER_MODEL`, `benchmark.SHIPPED_WHISPER_MODEL` and `scripts/build-release.py` `WHISPER_PACK_MODEL` — with no test pinning them equal, so a change of the app's default would ship a pack without the model the app uses — Triage: Fix-now; Decision: Applied. `benchmark.SHIPPED_WHISPER_MODEL` is the one spelling; `DEFAULT_WHISPER_MODEL = SHIPPED_WHISPER_MODEL` (its decision comment kept); `_whisper_files` reads it, including its "--only" remedy. Every value is still `"medium"`. Guard: `test_the_pack_ships_the_apps_own_whisper_model`.
- **[LOW]** SIMP-002: `install_layout.instance_guard_root` re-spelled `data_root("production")`'s body — Triage: Fix-now; Decision: Applied (`return data_root("production")`; the same read, the same fallback).
- **[LOW]** SIMP-003: `exclusions.WER_EXCLUDED_APPLICATIONS` repeated the two production executables — Triage: Fix-now; Decision: Applied (`("pythonw.exe", *WER_PRODUCTION_APPLICATIONS)`, the same tuple in the same order; D10's "dev = production + pythonw" stated once).

Fix-delta self-check: PASS. Each change leaves every value, order, error path and import direction as it was (`transcription` already imported from `benchmark`). ruff clean; mypy clean (58 files).

### Round 26 - 2026-10-03 - Phase H (Task H.4), /security-review over the whole plan diff (executor stage-4 leg i4-x3)

- Round status: Closed. All 4 Applied by leg i4-x3; verified by the composer suite of 2026-10-03 ~05:31 (pytest 5771 passed / 23 skipped, ruff and mypy clean; no `.iss` or extension change, so no ISCC compile or `npm run qa` was owed). Closed by executor leg i4-x4.
- Source: Claude Code security-review (portable threat-model checklist; no native reviewer is listed in this session)
- Reviewer: executor `claude-opus-5-5` (high) with one read-only security lens over `git diff 9f43f8c` (app code, scripts, packaging, the release workflow, the extension's channel and manifest), each finding re-verified by the executor.
- Trust boundaries examined: the elevated installer (process check, path refusal, model hashes before and after the copy, HKLM writes, `[InstallDelete]` / `[UninstallDelete]`); the install-folder refusal; the channel split (env, argv, files, pipe, host name, origin); the registry readers and the log tripwire; the benchmark worker entry; the release workflow (token scope, `${{ }}` in `run:`, artifact hand-off, caches); the build scripts' supply chain; the dev write guard; logs, `BUILD-INFO.txt` and the Status lines.
- Checked and clean: privilege escalation through Setup (the TOCTOU on the pack is closed by the post-copy re-hash inside the admin-only `{app}\models`; nothing is written or deleted outside `{app}`); `.iss` include injection (manifest paths pattern-limited, hashes lower-case hex); the install-folder refusal (real path, case-insensitive, before any log or data folder); the channel split (from `sys.frozen` only; distinct pipe names; per-channel origin); the benchmark worker (same-user only, offline env set and checked first, type-name-only errors); the dev write guard (fails closed; production never reads it); the workflow's expressions (none inside `run:`), `persist-credentials: false`, the one OIDC holder, the `--signer-workflow` / `--source-ref` verification; `--require-hashes --no-deps` wheels; no new runtime or install-time network use apart from SEC-003.
- The threat model's named Installation residues were not re-reported.

#### Findings

- **[LOW]** SEC-001: `scripts/build-release.py` `stage_two` — the extension build (`npm ci` + the Vite build, third-party code with write access to the bundle) ran AFTER the bundle audit, so anything it changed in `_internal` would be compiled into the installer and attested unaudited (no install script runs on Windows today; the extension itself is the same dependency's reach) — Triage: Fix-now; Decision: Applied. The extension is built first, then the bundle and extension audits, then the Defender scan and the compile; `test_the_bundle_is_audited_after_the_extension_build` pins the order. Threat model BUILD OF RECORD and flow 9 (c) say so. Not taken: `npm ci --ignore-scripts` — it could change what the extension build produces, which cannot be verified without a real build here.
- **[LOW]** SEC-002: `.github/workflows/release.yml` — the build of record ran `checkout`, `setup-python` and `setup-node` by movable tags (the pin test exempted `ci.yml`'s three) and restored a shared npm cache — Triage: Fix-now; Decision: Applied. All six actions are now `@PIN-REQUIRED # <release>` (fail closed until pinned, as the other three already were); `cache: npm` is removed; `ci.yml` is unchanged. Tests: `test_the_release_job_never_runs_a_tag_or_restores_a_cache`, and the pin and known-action tests now cover all six (and count every `uses:` line). Task 3.6's step 1 and AS-BUILT note updated.
- **[LOW]** SEC-003: `status.read_registration_status` and `native_host._log_registration_paths` — a registry manifest path (or the manifest's launcher path) on a network share was stat'ed / opened at every app and host start, so a value planted by same-user code caused SMB I/O (an NTLM exposure, and against C1's "no connection at start-up"); `REG_EXPAND_SZ` expansion widened it — Triage: Fix-now; Decision: Applied. `is_unc_path` moved to `install_layout` as the one definition (`speaker_embedding` and `language_model` import it there); the Status reader treats a UNC manifest or launcher as not registered without touching it; the host logs `host_manifest state=network_path` and returns. Tests: `test_a_network_manifest_is_never_touched` (2), `test_a_network_launcher_is_never_touched`, `test_a_network_manifest_is_logged_never_opened` (2). Docs: threat model HKCU SHADOWING (Chrome itself would still open it — part of the planted-entry residue), incident process. Siblings: the existing model-path refusals (`speech`, `transcription`, `speaker_embedding`, `language_model`) already refuse UNC.
- **[LOW]** SEC-004: `scripts/build-release.py` `defender_scan` — the quote refusal missed the curly single quotes U+2018–U+201B, which PowerShell also ends a single-quoted string at, so an `--out` path holding one could break out of the scan's `-Command` (the practitioner chooses `--out`; CI's is fixed — informational) — Triage: Fix-now; Decision: Applied. All five are refused before the command is built; `test_a_quote_in_the_path_never_reaches_powershell` (5).

Fix-delta self-check: PASS. The stage-two reorder keeps every step and its refusals; the UNC checks run before any filesystem call and change nothing for a local path; `is_unc_path`'s move keeps its behaviour (it now also takes a `str`); the workflow change only replaces refs and drops the cache. ruff clean; mypy clean (58 files).

### Round 27 - 2026-10-03 - Phase H Task H.5, independent cross-family codex peer review over the whole plan diff (pass stage-4.p1, peer_round 1 of cap 5; eight file-scoped slices)

- Round status: Closed (0 pending). 11 Applied by leg i4-x6 and PR-MED-022 routed to Task H.6 `[pending-hardening]`; composer suite 4 5805 passed / 23 skipped, ISCC 6.7.3 re-compile exit 0; codex round 28 confirmed the fixes and raised 5 LOW residues as its own findings.
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: the whole installation plan diff in worktree `C:/scribe-build` (`git diff 9f43f8c` — Phases 1–3 committed plus the uncommitted Phase H changes; 98 files excluding `.cursor/`), read in eight slices per leg i4-x4's H.5 list — a1 build, installer and CI (15), a2 source-run scripts (10), b1 layout, identity and channel split (15), b2 start-up, write guard and registry readers (13), b3 the extension's channel (10), c1 benchmark, models and UI (15), c2 model and UI tests (8), c3 docs (12); composer transcription of `.cursor/loops/stage-4-peer-r27{A1..C3}.log`, slice-local IDs renumbered to the plan's counters (PR-MED-A101→PR-MED-019, PR-LOW-A102→PR-LOW-020, PR-LOW-A103→PR-LOW-021, PR-LOW-A201→PR-LOW-022, PR-LOW-B101→PR-LOW-023, PR-MED-B201→PR-MED-020, PR-LOW-B301→PR-LOW-024, PR-MED-C101→PR-MED-021, PR-MED-C201→PR-MED-022, PR-LOW-C301→PR-LOW-025, PR-LOW-C302→PR-LOW-026, PR-LOW-C303→PR-LOW-027).

#### Findings
- **PR-MED-019** (MED, behavioral, `packaging/scribe.iss:330`): A failed post-copy model verification still finishes with a successful installer exit status; only the message and Finish label change. Callers checking Setup’s exit code can therefore accept an incomplete installation. — Evidence: `ModelsIncomplete := True;` followed by `MsgBox(...)`; no abort or custom failure exit code is implemented. Recommendation: Fix-now — Return a nonzero Setup exit code when `ModelsIncomplete` is set, and cover that failure contract. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x6)) — `scribe.iss` `GetCustomSetupExitCode` returns 9 when `ModelsIncomplete`, else 10 when `PolicyLeft` (the sibling), else 0; Inno calls it only on a completed run that would exit 0, and 1–8 are Inno's own. Pinned by `test_installer_script.py::test_an_incomplete_install_never_exits_with_success`; the threat model's THE MODELS and OPTIONAL POLICY and `docs/design-system.md`'s installer bullet name the codes.
- **PR-LOW-020** (LOW, docs-only, `packaging/scribe.iss:124`): The uninstall message incorrectly assigns seven-year retention to live sessions and implies a fixed duration for Past sessions. — Evidence: `'Your sessions, Past sessions and audit record stay in your Windows profile (kept 7 years).'`; `docs/security/retention-schedule.md:34` makes unprotected sessions expiry-eligible at 24 hours, and line 22 gives Past sessions a default of indefinite retention. Recommendation: Fix-now — Say uninstall leaves existing data untouched; remove the blanket retention claim and update its text pin. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x6)) — `KeptDataMessage` now reads "Your sessions, Past sessions and audit record were left in your Windows profile, unchanged." (no period claimed: nothing sweeps after an uninstall); its pin `test_uninstall_says_the_data_stays_c4` asserts the new string and that "kept 7 years" is gone; the two quotes (`docs/design-system.md`, the threat model's UNINSTALL LEAVES THE DATA) follow.
- **PR-LOW-021** (LOW, docs-only, `scripts/build-release.py:33`): The build’s help text describes the superseded audit-before-extension order. — Evidence: `the host manifest, ``--audit``, the extension`; actual lines 762–763 call `build_extension(...)` before `audit_bundle(...)`. Recommendation: Fix-now — Describe extension build → bundle and extension audits → Defender → compilation. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x6)) — the module docstring's stage two now reads PyInstaller, the host manifest, the extension (`npm ci`, `npm run build -- --mode release`), THEN the bundle and extension audits (no npm code after them, round 26 SEC-001) and the Defender scan, then Inno Setup — `stage_two`'s order.
- **PR-LOW-022** (LOW, docs-only, `scripts/setup-models.py:8`): The setup documentation still describes the app’s Cliniko client as read-only, contradicting the implemented draft-write capability and C9. — Evidence: “the app's only network use is its read-only Cliniko API client”; `desktop/src/scribe_desktop/cliniko_client.py:740` defines `write_draft_note`, and line 152 sets `_WRITE_METHOD` to `"PATCH"`. Recommendation: Fix-now — Describe the permitted Cliniko API reads and guarded draft write. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x6)) — `scripts/setup-models.py:8-9` "its Cliniko API client — reads, and the one guarded draft write (flow 18)"; the sibling comment at `desktop/requirements-ml-prose.txt:20-21` likewise (comment only; the URL and hash are untouched).
- **PR-LOW-023** (LOW, docs-only, `desktop/src/scribe_desktop/install_layout.py:248`): The UNC helper’s docstring overstates the protection, contradicting the accepted redirected-storage residue (C9). — Evidence: “Refused BEFORE any filesystem touch wherever a path comes from the environment or the registry” conflicts with `desktop/src/scribe_desktop/session_store.py:242–245`: “Deliberately NO UNC refusal here” and “folder-redirected LOCALAPPDATA would place session stores on SMB”. Recommendation: Fix-now — Limit the claim to guarded callers and explicitly retain the custody-store exception. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x6)) — `install_layout.is_unc_path`'s docstring names its refusing callers (the model loaders and probes, the benchmark, the Chrome-link registry readers) and states that the custody stores deliberately do NOT refuse (the redirected-`LOCALAPPDATA` residue, `session_store.default_sessions_root`).
- **PR-MED-020** (MED, behavioral, `desktop/src/scribe_desktop/status.py:57`): Mixed-separator UNC paths bypass SEC-003 and can trigger SMB access at startup. A value such as `\/server/share/host.json` passes the raw-string check, but Windows `Path` normalizes it into a UNC path before filesystem access. The host reader has the same bypass. — Evidence: the shared helper at `desktop/src/scribe_desktop/install_layout.py:252` uses `return str(path).startswith(("\\\\", "//"))`; Status then calls `manifest.is_file()` at line 61, and `desktop/src/scribe_desktop/native_host.py:577` calls `Path(winner.manifest).read_text(encoding="utf-8")`. The installed Python’s `pathlib` parser confirms separator normalization before path parsing. Recommendation: Fix-now — normalize separators before the shared UNC check and cover both mixed-prefix forms for manifests and launchers with filesystem calls replaced by failing fakes. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x6)) — the ONE helper now normalises (`str(path).replace("/", "\\").startswith("\\\\")`, as `ntpath.splitroot` does), closing all three raw-string sites and any future one; the four inline model-path checks (`speech.py` SileroVad and `vad_model_available`, `transcription.py` `whisper_model_available` and the provider) now call it too, so there is one definition. Tests: the manifest tests (`test_a_network_manifest_is_never_touched`, `test_a_network_manifest_is_logged_never_opened`) gain both mixed forms under their failing fakes, the launcher test is parametrized with a mixed form, and `test_install_layout.py::TestIsUncPath` pins five network and six local shapes. The threat model's HKCU SHADOWING sentence and flow 6 of the data-flow map say "every separator form".
- **PR-LOW-024** (LOW, behavioral, `scripts/generate-extension-key.py:62`): `--out` permits writing an unencrypted private key into a non-gitignored repository file. For example, `--out extension/dev-key.pem` bypasses both existing key exclusions. — Evidence: `key_pem: Path = args.out if args.out.is_absolute() else REPO / args.out`; line 43 writes `key_pem.write_bytes(` using `serialization.NoEncryption()`. `.gitignore:30–33` excludes only `key.pem` and `extension/key-dev.pem`. Recommendation: Fix-now — Restrict the resolved output to the two designated gitignored key paths before generating or writing a key. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x6)) — `resolve_out` resolves `--out` (relative from the repo root) and admits only `ALLOWED_KEY_FILES` (`extension/key.pem`, `extension/key-dev.pem`); anything else is a usage error (exit 2) before any key is read or written. New `desktop/tests/test_generate_extension_key.py` (4 allowed shapes, 4 refused shapes with key I/O failing the test); no real key is read. `scripts/README.md` and the script docstring say so.
- **PR-MED-021** (MED, behavioral, `desktop/src/scribe_desktop/benchmark.py:197`): Benchmark paths bypass the UNC refusal used by the other model loaders, allowing SMB traffic outside C1’s Cliniko-only network contract. A redirected developer models root reaches directory enumeration; the packaged worker also admits UNC model/audio arguments. — Evidence: `if not whisper_dir.is_dir():`; admission rejects only `not value or value.startswith("-")`; `run_single` passes `str(model_dir)` to `WhisperModel` and `str(audio_path)` to `model.transcribe` without a UNC check. Recommendation: Fix-now — Reject UNC roots before enumeration and UNC model/audio paths before worker filesystem or ML access; verify with injected paths and filesystem tripwires. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x6)) — `benchmark.py`: `list_whisper_candidates` returns `[]` for a network root before any stat; `run_all` refuses one with a clear `RuntimeError` before listing or sampling; `run_single` refuses a network model or audio path after the offline assert and before any ML import; `is_worker_argv` refuses a network value of `_WORKER_PATH_OPTIONS` (`--single`, which is joined to the root and would replace it, `--models-root`, `--audio`), so the frozen `worker_argv` refuses its own UNC shape. Tests: `test_benchmark.py` (`test_a_network_root_is_never_touched` ×2 with `is_dir`/`iterdir` failing, `TestNetworkPathsRefused` ×3) and `test_frozen_runtime.py` (three new not-the-worker shapes, `test_a_packaged_build_never_spawns_a_network_worker`).
- **PR-MED-022** (MED, test-harness, `desktop/tests/test_ui_screens.py:727`): The modified microphone polling tests still inspect real production model paths, violating C6. `profile_root` isolates the profile, but neither test redirects the models root. — Evidence: construction supplies `"benchmark_runner=list, profile_root=tmp_path"`; `refresh_model_status()` calls `"models.model_file_report_lines()"` (`desktop/src/scribe_desktop/ui/microphone.py:342`), whose VAD probe ends with `"return path.is_file()"`. Conftest pins production and non-frozen without redirecting `LOCALAPPDATA`. The same omission occurs at `desktop/tests/test_ui_learn_style.py:957` and in the shared `_main_window` helper at `desktop/tests/test_ui_screens.py:976`, used by the new encounter tests. Recommendation: Fix-now — redirect `install_layout.models_root` to a temporary directory for these UI tests, preserving explicit presence-change stubs. /fix decision: Include in plan (2026-10-03, Claude Code (executor stage-4 leg i4-x6)) — Phase H Task H.6 `[pending-hardening]`: the class-closing conftest autouse pin of `install_layout.models_root`, with its two exemptions and a Done-when; not built in this leg.
- **PR-LOW-025** (LOW, docs-only, `docs/security/data-flow-map.md:139`): The registration flow retains a space-free-path requirement contradicted by the verified installation location. — Evidence: “Chrome resolves the manifest only from a space-free path”; `.cursor/plans/plan-installation.md:2793` explicitly says the no-spaces rule “is also superseded by Task 0.2, which ran the installed host from Program Files.” Recommendation: Fix-now — Remove the blanket restriction and distinguish any remaining developer-launcher limitation. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x6)) — flow 5's sentence now says the dev host folder is kept space-free as a conservative guard and a space alone is not Chrome's rule (Task 0.2); siblings: `register-native-host.py`'s docstring item 1 (the gate's failure named as not re-diagnosed), its `INSTALL_DIR` comment and its refusal line (the refusal kept: harmless, never reached for the space-free dev folder), `test_register_native_host.py`'s skip reason, and AGENTS.md step 5 (the `.exe` half kept).
- **PR-LOW-026** (LOW, docs-only, `docs/security/retention-schedule.md:33`): Losing a private extension key does not change the unpacked extension’s ID; this claim could prompt unnecessary identity replacement. — Evidence: “losing one changes that channel's extension ID and breaks its Chrome link”; `extension/src/manifest.ts:24` reads `const identity = CHANNELS[channel]`, then line 27 sets `key: identity.key` from the committed public key. The same incorrect claim appears at `docs/security/threat-model.md:99`. Recommendation: Fix-now — State that replacing the manifest public key changes the ID; losing the private file alone leaves existing builds and registration unchanged. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x6)) — the retention row now says losing a private key changes nothing (the ID comes from the committed public key) and only committing a NEW key's public half changes the ID; the threat model's Extension identity item says the same.
- **PR-LOW-027** (LOW, docs-only, `docs/security/threat-model.md:3070`): Documentation guarantees deletion of damaged model copies despite an explicitly handled deletion-failure path. — Evidence: “a damaged copy is deleted”; `packaging/scribe.iss:224` checks `if not DeleteFile(...)` and line 225 reports “damaged, and could not be removed”. The unconditional claim also appears at `docs/security/data-flow-map.md:1022` and `docs/security/retention-schedule.md:82`. Recommendation: Fix-now — Describe deletion as attempted, name the retained-damaged-file residue, and retain the instruction to complete repair before opening the app. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x6)) — the threat model's THE MODELS (deleted where Windows allows it; one that could not be removed is named; Setup exits 9; RESIDUE: a damaged copy that could not be deleted stays, and the app must not be opened before Setup is run again), flow 23 of the data-flow map and the retention schedule's installed-models row all say so.
- Verification counts: 54 claims checked, 46 confirmed, 8 dropped as unverifiable
- Last reviewed: 2026-10-03

#### LEG 1 verified tuples

Executor leg i4-x5, 2026-10-03. Verification only; nothing was fixed. Each claim was checked against the current worktree. All 12 defects are REAL; none meets a MED/HIGH bar on its evidence (no consumer of the installer's exit code, every UNC case needs a same-user foothold or the dev channel, every doc item is wording), so the four MEDs are DOWNGRADED to LOW. Three are fix-induced or incomplete siblings of round 26 (⚡: PR-MED-020, PR-LOW-021, PR-LOW-023); the other nine are pre-existing in the Phases 1–3 work or older.

- PR-MED-019: materiality=behavioral severity=verified LOW (downgraded from MED) surface=production rec=Fix-now — `scribe.iss:325-334` `CurStepChanged(ssPostInstall)` only sets `ModelsIncomplete := True` and shows `MsgBox(…'Clinic Scribe is NOT completely installed…')`; no code ever makes Setup's exit code non-zero, so it exits 0. Inno Setup's `[Code]` event `function GetCustomSetupExitCode(): Integer` exists for exactly this (it is called only when Setup ran to completion with exit 0, and a non-zero result becomes the exit code; values above Inno's documented 0–8 avoid a clash). That is the honest shape; `Abort` from `ssPostInstall` cannot roll back the copied files, and `PrepareToInstall` cannot see a post-copy failure. Why LOW: nothing consumes the exit code here. Phase P installs interactively, CI never runs `setup.exe`, and the failure is already shown twice: a `MsgBox` (not `SuppressibleMsgBox`, so it shows even under `/VERYSILENT /SUPPRESSMSGBOXES`) and the Finish label "NOT completely installed". `RemoveDamagedModels` also deletes each bad copy, so the app reports the model missing. siblings=`PolicyLeft` (`scribe.iss:320`, the unticked policy could not be removed) also ends with exit 0 while the Finish page says so; the same `GetCustomSetupExitCode` can return a second code for it. Not siblings: the foreign-policy note (an informational state, not a failure) and the `PrepareToInstall` refusals (they already end Setup unsuccessfully).
- PR-LOW-020: materiality=docs-only severity=verified LOW surface=production rec=Fix-now — `scribe.iss:124` `KeptDataMessage`: "Your sessions, Past sessions and audit record stay in your Windows profile (kept 7 years)." Only the audit record has a fixed 7 years. A live session is removed at Complete or Discard and an unfinished one is swept after 24 h at the next start. Past sessions are kept "Until I delete them" by default, or at least 7 years (AGENTS.md Database Notes; `retention-schedule.md:22`, `:34`). After an uninstall nothing sweeps at all, so "stay … untouched until the app is installed again or you delete them" is the truthful claim. siblings=the quotes of that string at `docs/design-system.md:575` and `docs/security/threat-model.md:3200`, and its pin `desktop/tests/test_installer_script.py:390-391` (change all four together).
- PR-LOW-021: materiality=docs-only severity=verified LOW surface=build rec=Fix-now — `scripts/build-release.py:32-35` (module docstring, stage two): "PyInstaller over packaging/scribe.spec, the host manifest, ``--audit``, the extension (``npm ci`` …) into the bundle's ``extension`` folder, Inno Setup …". Since round 26 SEC-001, `stage_two` builds the extension, then runs `audit_bundle`, `audit_extension`, the Defender scan and `compile_installer`. ⚡: SEC-001's own fix missed this sibling. siblings=none — the threat model's BUILD OF RECORD and flow 9 (c) were updated in round 26, and `scripts/README.md` gives no order (checked).
- PR-LOW-022: materiality=docs-only severity=verified LOW surface=docs rec=Fix-now — `scripts/setup-models.py:8-9`: "the app's only network use is its read-only Cliniko API client (flow 18)". Since the draft-write plan the client also holds the one draft write (`cliniko_client.py` `write_draft_note`, `_WRITE_METHOD = "PATCH"`). Pre-existing: the line is unchanged since before `9f43f8c` (`git diff 9f43f8c -- scripts/setup-models.py` touches only lines 11 onward), and this plan's diff touches the file. siblings=`desktop/requirements-ml-prose.txt:20` ("the app's own only network use is its read-only Cliniko API client"). The AGENTS.md:71, CHANGELOG and phase-history mentions are historical records of Phase 5, not current claims, so they are not siblings.
- PR-LOW-023: materiality=docs-only severity=verified LOW surface=production rec=Fix-now — `install_layout.py:248-251`: "Refused BEFORE any filesystem touch wherever a path comes from the environment or the registry". The custody roots deliberately do NOT refuse: `session_store.py:242-246` ("Deliberately NO UNC refusal here … a folder-redirected LOCALAPPDATA would place session stores on SMB"); likewise `audit.py:145`, `past_sessions.py:144`, `practitioner_profile.py:273`, `clinics.py:334` and `note_config.py:86`/`:912`. ⚡: this docstring was written in round 26 (SEC-003). siblings=none beyond the docstring. The threat model's new HKCU SHADOWING sentence is scoped to the registry readers ("no SMB I/O from their own start-up"), which is accurate.
- PR-MED-020: materiality=behavioral severity=verified LOW (downgraded from MED) surface=production rec=Fix-now — CONFIRMED.
  - **The bypass:** `install_layout.is_unc_path` is `str(path).startswith(("\\\\", "//"))`. A RAW string `\/server/share/host.json` (or `/\server\share\…`) fails both prefixes. Windows `pathlib` parses through `ntpath.splitroot`, which replaces the alternate separator with `\` BEFORE testing for the `\\` UNC prefix, so `Path(r"\/server/share/host.json")` is the UNC path `\\server\share\host.json`.
  - **The raw-string call sites:** `status.py:57` (`registry_value`, the raw registry string) then `manifest.is_file()` at `:61`; `status.py:66` (the manifest JSON's raw `"path"`) then `Path(launcher).is_file()`; `native_host.py:574` (`winner.manifest`, raw) then `Path(winner.manifest).read_text()` at `:577`.
  - **Not affected:** every model-path caller (`speaker_embedding.py:259/284`, `language_model.py:145/255`, `speech.py:179/376`, `transcription.py:925/985`) is handed a `Path` built by `install_layout` (or a `type=Path` argv), and `str(Path)` is already normalised. `exclusions.py:385-405` normalises (`\\?\UNC\` → `\\`) before its own `startswith("\\\\")`.
  - **Why LOW:** the foothold is unchanged from SEC-003, which was LOW: writing the user's own HKCU, so code already running as that user. Chrome itself opens whatever path the winning entry names when it launches the host. ⚡: an incomplete round 26 fix.
  - siblings=the three raw-string sites above, and no other in the plan diff (searched every `is_unc_path` and `startswith(("\\\\", "//"))` site). The fix belongs in the ONE helper, by normalising `/` to `\` (or parsing with `PureWindowsPath`) before the prefix test, which closes all three and any future raw-string caller. Its tests should cover both mixed prefixes for the manifest and the launcher, with the filesystem calls replaced by failing fakes.
- PR-LOW-024: materiality=behavioral severity=verified LOW surface=build rec=Fix-now — `scripts/generate-extension-key.py:62` `key_pem: Path = args.out if args.out.is_absolute() else REPO / args.out`, then `:43-49` writes the PKCS8 private key with `NoEncryption()`. `.gitignore:30,33` ignores only `key.pem` (any folder) and `extension/key-dev.pem`, so `--out extension/dev-key.pem` writes an unignored private key into the repository. Why LOW: the operator chooses `--out`; the PUBLIC key in `extension/src/channel.ts` alone already gives anyone the same unpacked-extension ID, so a leaked private key adds little while the Web Store is deferred; and a commit is still a reviewed, deliberate act. siblings=none — no other script writes key material (`build-release.py` copies `extension/dist`, which holds no private key).
- PR-MED-021: materiality=behavioral severity=verified LOW (downgraded from MED) surface=production rec=Fix-now — CONFIRMED, PRE-EXISTING (`git show 9f43f8c:…/benchmark.py` has the same `list_whisper_candidates` at L177-182).
  - **The gap:** `benchmark.py:196-199` `whisper_dir.is_dir()` / `iterdir()` / `whisper_snapshot_complete` on `models_root / "whisper"` with no UNC refusal; `run_single` (`:449-462`) passes `str(model_dir)` to `WhisperModel` and `str(audio_path)` to `transcribe`; `is_worker_argv` (`:506-525`) refuses only empty or option-like values.
  - **Why LOW:**
    - A packaged build's root is `install_root() / "models"` (`install_layout.py:216-218`), and the app refuses to start outside `C:\Program Files\ClinikoScribe`, so production never has a UNC root. Only the dev channel with a folder-redirected `LOCALAPPDATA` (whose session stores are already on SMB by the accepted residue) or a hand-made same-user worker launch reaches it.
    - The benchmark runs on the user's button press, never at start-up or idle, so C1's "none at startup or idle" is not crossed.
    - It is still inconsistent with the stated rule "Model paths DO refuse UNC" (`session_store.py:246`).
  - siblings=`run_all` (the root it enumerates), `run_single` (model and audio), and the worker admission (`--models-root`, `--audio`). The prose stage (`language_model`) and every other model probe already refuse UNC.
- PR-MED-022: materiality=test-harness severity=verified LOW (downgraded from MED) surface=test-harness rec=Include-in-plan — CONFIRMED, PRE-EXISTING.
  - **The reads:** `test_ui_screens.py:727-756` builds `MicrophoneScreen(…, profile_root=tmp_path)` and polls `refresh_model_status()`, which calls `models.model_file_report_lines()` (`ui/models.py:2783-2812`). That runs `whisper_model_available` / `resolve_whisper_model` / `vad_model_available` against `install_layout.models_root()`. The conftest pins the production channel and `is_frozen=False` (`conftest.py:50-64`) but never redirects `LOCALAPPDATA` or `models_root`, so the polls STAT the practitioner's real `%LOCALAPPDATA%\ClinikoScribe\models`.
  - **What the plan's diff changed here:** only one-line API updates (`HardwareCheck([], None)`, `speaker_model_missing_reason()`); the real-root reads predate `9f43f8c` (the production root was the only root then).
  - **Why LOW:** the reads are stat-only and read-only, and every assertion is host-independent. `model_file_report_lines` always returns three lines, the test checks only `len == 4`, line 2 (the speaker line, stubbed through `speaker_embedder_available`) and line 3. So no flake and no write, but it is a C6 breach in letter.
  - siblings=`test_ui_learn_style.py:957` (the same poll) and the shared `_main_window` helper (`test_ui_screens.py:976`) with every test built on it; by construction, any test that constructs `MicrophoneScreen` or `MainWindow` without pinning the models root.
  - **Why Include-in-plan, not one-site Fix-now:** a three-site patch leaves the class open. The class-closing fix is a conftest-level autouse pin of `install_layout.models_root` to a per-test temporary folder, and it must EXEMPT `test_install_layout.py`'s own `models_root` tests (which drive `LOCALAPPDATA` and `install_root` and need the real function) and keep `on_real_ml_root` / the real-ML fixture working (they already patch and restore `install_layout.models_root`). That is a scoped task worth a short plan line and a full-suite run.
- PR-LOW-025: materiality=docs-only severity=verified LOW surface=docs rec=Fix-now — `data-flow-map.md:139` "(Chrome resolves the manifest only from a space-free path — see the threat model.)". The threat model has no such claim (searched "space"), and Task 0.2 linked Chrome to the host in `C:\Program Files\ClinikoScribe` (the plan at `:2817`: "Their no-spaces rule is also superseded by Task 0.2"). siblings=`scripts/register-native-host.py:86` and `:194` (the refusal line "contains a space; Chrome will not resolve the host manifest there" states a superseded cause; the dev install folder has no space anyway, so the check never fires) and AGENTS.md step 5 ("must stay space-free and `.exe`-based or Chrome silently reports 'host not found'"; the `.exe` half is still true, the space half is the superseded rule). Fix the wording as a class; whether to keep the script's refusal is the fix leg's call (harmless and never reached).
- PR-LOW-026: materiality=docs-only severity=verified LOW surface=docs rec=Fix-now — `retention-schedule.md:33` "losing one changes that channel's extension ID and breaks its Chrome link". The ID comes from the manifest `key`, the committed PUBLIC key (`manifest.ts:24-27` `const identity = CHANNELS[channel]` … `key: identity.key`; the keys live in `extension/src/channel.ts`), so losing the private file changes nothing for the existing builds or the registration. Only generating a NEW key (re-running the key script without the file) and committing its public key would change the ID. siblings=`docs/security/threat-model.md:99` ("losing it means a new ID and mandatory re-registration"), pre-existing. `extension/KEY.md` was checked and makes no such claim.
- PR-LOW-027: materiality=docs-only severity=verified LOW surface=docs rec=Fix-now — `threat-model.md:3070` "a damaged copy is deleted". `scribe.iss:223-225`: `if FileExists(…) then if not DeleteFile(…) then Result := Result + ' (damaged, and could not be removed)'`, so a failed delete is a handled state. In that state a damaged whisper or silero file (not re-verified at load) could stay until Setup is rerun, while the Finish page and the `MsgBox` say "NOT completely installed … Run Setup again". siblings=`docs/security/data-flow-map.md:1022` ("a damaged one deleted") and `docs/security/retention-schedule.md:82` ("a copy that failed its check is deleted at install"). The fix should say "deleted where possible", name the could-not-remove residue and keep the "run Setup again before you open Clinic Scribe" instruction.

Cap verdict: accept — production-behavioral — peer_round 1 of cap 5. The 12 survivors are all LOW after verification:
- three behavioral in shipped code: the installer's exit code, the shared UNC helper's normalisation, and the benchmark's UNC refusal;
- one behavioral in a dev tool (the key script's `--out`);
- one test-harness class (the models-root pin), routed as a scoped plan item;
- seven docs-only.

Each fix is local: one `[Code]` event function, one helper line plus its tests, two or three refusals in `benchmark.py`, one path guard, and doc and string edits with the one installer-string pin. They fit one fix leg and a confirmation round well inside the cap; no raise is warranted. A `.iss` change makes an ISCC 6.7.3 re-compile owed with the suite.

#### LEG 2 dispositions (executor leg i4-x6, 2026-10-03)

Per the composer's disposition: 11 Fix-now, 1 Include in plan. Each fix was applied one finding at a time, re-read, and its siblings closed as the tuples above name them.
- Applied (11): PR-MED-019 (exit codes 9/10 via `GetCustomSetupExitCode`, sibling `PolicyLeft`), PR-LOW-020, PR-LOW-021, PR-LOW-022 (+ the `requirements-ml-prose.txt` sibling), PR-LOW-023, PR-MED-020 (the one helper normalises, and the four inline model-path checks route through it), PR-LOW-024, PR-MED-021 (root, single run, run_all and the worker admission), PR-LOW-025 (+ the register-script, test-skip and AGENTS siblings), PR-LOW-026 (+ the threat-model sibling), PR-LOW-027 (+ the data-flow and retention siblings).
- Include in plan (1): PR-MED-022 → Phase H Task H.6 `[pending-hardening]`.
- Fix-delta self-check: PASS. `is_unc_path` widens only to the mixed forms (`\/`, `/\`) Windows already reads as UNC; no local path changes answer (pinned by six local shapes). It returns False for `""`, so the empty registry value still reaches the absolute-path check as round 23 recorded. The benchmark refusals run before any stat, listing or ML import. `run_single` keeps the offline assert first, so `test_run_single_asserts_offline_before_ml_import` is unchanged. `GetCustomSetupExitCode` is a new event function and no existing `[Code]` path changes. The key-script guard runs before `load_or_create_private_key`, and the default `--out` is allowed. No drive-by edit. ruff clean; mypy clean (see the handoff bullet).

### Round 28 - 2026-10-03 - Phase H confirmation of round 27's fix, independent cross-family codex peer review (pass stage-4.p1, peer_round 2 of cap 5; two file-scoped slices)

- Round status: Closed (0 pending). All 5 Applied by leg i4-x8; composer suite 5 5835 passed / 23 skipped; codex round 29 confirmed them and raised 1 LOW sibling as its own finding.
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: the files leg i4-x6 changed, in two slices — X1 code and tests (15), X2 docs and comments (7); round 27's block and C1–C10; composer transcription of `.cursor/loops/stage-4-peer-r28{X1,X2}.log`, slice-local IDs renumbered (PR-LOW-X101→PR-LOW-028, PR-LOW-X102→PR-LOW-029, PR-LOW-X103→PR-LOW-030, PR-LOW-X104→PR-LOW-031, PR-LOW-X201→PR-LOW-032).

#### Findings
- **PR-LOW-028** (LOW, behavioral, `desktop/src/scribe_desktop/install_layout.py:260`): The UNC helper also rejects legitimate extended local paths such as `\\?\C:\models`, so the new benchmark guards reject local storage. — Evidence: `return str(path).replace("/", "\\").startswith("\\\\")`; the local-path cases at `desktop/tests/test_install_layout.py:310` omit extended paths. Recommendation: Fix-now — Distinguish extended local drive paths from UNC paths, retaining refusal of `\\?\UNC\server\share`, and test both. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x8)) — `install_layout.is_unc_path` judges the `\\?\`, `\\.\` and NT `\??\` prefixes (`_DEVICE_PREFIXES`) by an allow-list: local only when a drive follows (`X:` then `\` or end); `UNC\…`, `GLOBALROOT\…`, `Volume{…}`, pipes and malformed drives fail closed; the plain and mixed forms are unchanged. `TestIsUncPath` gains 6 extended-local and 10 refused shapes; the docstring and flow 6 say so. `exclusions._normalised` left as recorded (warn-only, not a sibling).
- **PR-LOW-029** (LOW, behavioral, `desktop/src/scribe_desktop/benchmark.py:588`): The benchmark’s temporary audio path remains an unguarded sibling: a UNC temporary directory causes filesystem access and sample writing before worker admission rejects it. — Evidence: `with tempfile.TemporaryDirectory() as tmp:` followed by `audio_seconds = generate_speech_sample(audio_path)`; line 447 executes `stream.Open(str(target), 3)` without a path guard. Recommendation: Fix-now — Select and validate a local temporary parent before directory creation, and guard the sample writer before opening its target. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x8)) — `run_all` refuses when a cached `tempfile.tempdir` or any of `_TEMP_VARIABLES` (TMPDIR, TEMP, TMP) is network, before any tempfile call (reading them never probes); `generate_speech_sample` refuses a network target before importing SAPI. Tests: `test_run_all_refuses_a_network_temporary_folder` ×4 (`TemporaryDirectory` and the sampler fail the test if reached) and `test_the_sample_writer_refuses_a_network_target` ×2 (`win32com.client` stubbed to fail the import). Flow 6 says so.
- **PR-LOW-030** (LOW, test-harness, `desktop/tests/test_frozen_runtime.py:815`): The network-refusal tests delegate to the real filesystem if the guard regresses, rather than failing before network access as round 27 required. — Evidence: both spies execute `return real_is_file(self)` (lines 815 and 836); their no-touch assertions run afterwards. Recommendation: Fix-now — Make the manifest spy fail immediately; allow only the temporary manifest in the launcher spy and reject every other path before filesystem access. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x8)) — one conftest helper `forbid_network_io` makes every `Path` call in `NETWORK_IO_METHODS` (exists, is_file, is_dir, stat, open, read_text, read_bytes, iterdir) raise on a network path before the filesystem, local paths passing through; it replaces both fall-through spies in `test_frozen_runtime.py` and guards the siblings `test_benchmark.py::test_run_single_refuses_a_network_path` (also `faster_whisper` stubbed to fail the import), `test_speech.py::test_unc_model_path_rejected` and `test_transcription.py::test_unc_model_path_rejected`. The helper is itself tested (`test_the_network_tripwire_raises_before_the_filesystem` ×8).
- **PR-LOW-031** (LOW, docs-only, `packaging/scribe.iss:213`): The damaged-model comment retains the deletion guarantee that PR-LOW-027 corrected elsewhere. — Evidence: “Each bad copy is removed, so the app reports the model missing and never loads damaged bytes”; lines 226–227 explicitly handle failed deletion with “damaged, and could not be removed”. Recommendation: Fix-now — State that deletion is attempted and a retained damaged file requires repair before launching the app. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x8)) — the `RemoveDamagedModels` comment now says removal is ATTEMPTED, a copy that could not be removed is named, Setup exits 9, and the app must not be opened before Setup is run again. Comment-only: no `[Code]` line changed.
- **PR-LOW-032** (LOW, docs-only, `docs/security/threat-model.md:215`): The single-instance section still claims the lock is the sole developer-channel use of the production folder, contradicting C8’s migration exception. — Evidence: “the one place the dev channel uses the production folder”; the same document at line 3188 states “with two named exceptions”, including `register-native-host.py --unregister`. Recommendation: Fix-now — Qualify this as the running app’s only use and name the separate one-time registration migration. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x8)) — the threat model now says "the running developer app's one use of the production folder" and names the one-time `--unregister` migration as C8's other exception; the sibling docstring `install_layout.instance_guard_root` is qualified the same way.
- Verification counts: 22 claims checked, 20 confirmed, 2 dropped as unverifiable
- Last reviewed: 2026-10-03

#### LEG 1 verified tuples

Executor leg i4-x7, 2026-10-03. Verification only; nothing was fixed. Each claim was checked against the current worktree. All 5 are REAL and LOW. Two are incomplete sibling closures of round 27's own fixes (⚡: PR-LOW-029 is a sibling of PR-MED-021, PR-LOW-031 a sibling of PR-LOW-027, and leg i4-x5's sibling lists missed both). PR-LOW-030 is partly ⚡: round 27's PR-MED-020 asked for "failing fakes", and leg i4-x6 extended the fall-through spies instead. Two are pre-existing (PR-LOW-028, PR-LOW-032).
- PR-LOW-028: materiality=behavioral severity=verified LOW surface=production rec=Fix-now.
  - **The defect:** `install_layout.py:260` is `return str(path).replace("/", "\\").startswith("\\\\")`. It answers True for the extended local forms `\\?\C:\models` and `\\.\C:\models`, so every refusing caller refuses a local folder in that form. Those callers are the model loaders and probes, the benchmark, and the Status and host registry readers; the latter would read a hand-written `\\?\C:\…` manifest value as "not registered", which Chrome itself accepts.
  - **Pre-existing, not fix-induced:** the round-26 helper `startswith(("\\\\", "//"))` and the older inline checks answered True for `\\?\C:\…` too. Round 27 added only the mixed `/` forms.
  - **Can a caller legitimately receive a `\\?\` local path? None by default:**
    - Production `models_root` is `install_root() / "models"`. `install_root` takes `os.path.realpath(sys.executable)` (CPython strips the `\\?\` prefix whenever the plain path resolves to the same file) and then requires a normalised match with `C:\Program Files\ClinikoScribe` (`install_layout.py:188-191`), so an extended form never gets that far.
    - The dev root comes from the `LOCALAPPDATA` environment variable, which Windows sets to `C:\Users\…\AppData\Local`.
    - The registry manifest values are written by the installer (`{app}\…`) and by `register-native-host.py` (`data_root("dev")`).
    - The benchmark's argv is built from those roots plus `tempfile` (the `TEMP`/`TMP` environment, `os.path.abspath` only).
    - So a `\\?\` value reaches a caller only when the same user hand-sets an environment or registry value. The effect is fail-closed: a refusal of a local path, never SMB I/O.
  - **The class-closing helper shape:** an ALLOW-list of local forms, not a deny-list of network prefixes. After normalising `/` to `\`:
    - a `\\?\` or `\\.\` prefix is admitted as local only when the rest is drive-absolute (`^[A-Za-z]:(\\|$)`);
    - `\\?\UNC\…` and `\\.\UNC\…` are network;
    - every other device-namespace form is refused fail-closed: `\\?\GLOBALROOT\Device\Mup\…` (a network path through the device namespace, which a naive "strip `\\?\` and re-test" would let through), `\\?\Volume{…}\`, pipes;
    - an NT-namespace `\??\` lead gets the same allow-list. The claim that Win32 passes `\??\UNC\…` through to the redirector is UNVERIFIED here: it was not run (C7), and it comes from the documented `RtlDosPathNameToNtPathName` pass-through, so the fix leg should verify it from the documentation or simply refuse that form;
    - any other `\\` lead stays network.
    - Mapped network drive letters remain the documented residue (`speech.py:174-178`).
    - Tests: `\\?\C:\x`, `\\.\C:\x`, `//?/C:/x` and `\??\C:\x` are local; `\\?\UNC\s\sh`, `\\.\UNC\s\sh`, `\\?\GLOBALROOT\Device\Mup\s\sh` and `\??\UNC\s\sh` are network or refused; the existing eleven cases stay unchanged.
  - siblings=`test_install_layout.py:310-312` (the local-shape list); the docstring at `install_layout.py:247-259`. Related, not a sibling: `exclusions._normalised` / `_is_network` (`exclusions.py:383-410`). It strips `\\?\` but would read `\\?\GLOBALROOT\…` and `\??\UNC\…` as local. It is warn-only (the location warning on `realpath` of the data folder, which CPython de-prefixes), so it needs at most one shared prefix parser, not a refusal.
- PR-LOW-029: materiality=behavioral severity=verified LOW surface=production rec=Fix-now ⚡.
  - **The defect:** `benchmark.py:588-590` runs `with tempfile.TemporaryDirectory() as tmp:` → `audio_path = Path(tmp) / "benchmark_sample.wav"` → `generate_speech_sample(audio_path)`, whose `:447` `stream.Open(str(target), 3)` and `:452` `wave.open(str(target), "rb")` carry no guard.
  - **Reach:**
    - `TemporaryDirectory()` calls `tempfile.gettempdir()`, whose first use PROBES each candidate (TMPDIR/TEMP/TMP, then the platform defaults) by writing a test file.
    - So a network `TEMP` costs SMB I/O (a probe file, `mkdtemp`, the SAPI write, the WAV read) BEFORE the round-27 refusals fire. Those are the frozen `worker_argv` → `is_worker_argv` refusal of a network `--audio`, and in a source run the worker's `run_single`.
    - This reaches production too: a frozen app inherits the user's `TEMP`.
  - **Why LOW:**
    - It needs a same-user environment foothold.
    - It runs only on the benchmark button, never at start-up or idle (C1's clause), and the audio is synthetic SAPI speech with no clinical content.
  - **The fix shape:**
    - Before ANY tempfile call, refuse when a set `tempfile.tempdir` or any of the TMPDIR/TEMP/TMP values is network, using the one helper (reading the values never probes).
    - Then guard `generate_speech_sample`'s target, as `run_single` does.
    - Test with a fake `generate_speech_sample` and a `TemporaryDirectory` that fails the test when reached.
  - siblings=`generate_speech_sample` (its own target guard).
  - **Checked, not siblings:**
    - `audit.py:1098` (`mkstemp(dir=path.parent)`, the user-chosen export file);
    - `speaker_eval.py:1070` (`mkdtemp`, the practitioner-run measurement harness, outside the app's model-path class, with its own custody contract in `docs/testing/speaker-measurement.md`).
- PR-LOW-030: materiality=test-harness severity=verified LOW surface=test-harness rec=Fix-now.
  - **The defect:** `test_frozen_runtime.py:813-815` and `:834-836` are spies that `touched.append(str(self))` and then `return real_is_file(self)`. If the guard regressed, the real `is_file` would stat `\\host\share\…` (an SMB name lookup) before the `touched == []` or `not startswith("\\\\")` assertion fails.
  - **What the fix should do:**
    - Make the manifest spy raise immediately.
    - Let the launcher spy pass ONLY the test's own temporary manifest and raise for any other path.
  - siblings, the same fall-through shape:
    - ⚡ `test_benchmark.py:240-248` `test_run_single_refuses_a_network_path` (round 27's own). On a regression it would import `faster_whisper` and call `WhisperModel(r"\\h\s\whisper\small")` with no tripwire. Stub the imports, or make `WhisperModel` fail the test.
    - Pre-existing: `test_speech.py:327-330` `test_unc_model_path_rejected` and `test_transcription.py:979-982` `test_unc_model_path_rejected` (constructor tests on `\\evil-host\share\…` with no tripwire). The probe tests next to them (`test_speech.py:332`, `test_transcription.py:1048`) already raise.
    - [2026-10-03 correction] Only `test_speech.py:332` raised, and only on `is_file`. `test_transcription.py:1048` had NO tripwire; this sentence was written without reading it. Round 29 PR-LOW-033 found it, enumerated the whole class, and leg i4-x10 closed it.
    - The class-closing shape is ONE conftest helper that makes `Path.is_file` / `is_dir` / `exists` / `stat` / `open` / `read_text` / `iterdir` raise for any `install_layout.is_unc_path(self)` path, used by every network-refusal test.
  - **Not siblings:**
    - `test_a_network_manifest_is_logged_never_opened` (`read_text` already raises);
    - `test_a_network_root_is_never_touched` (`is_dir`/`iterdir` raise);
    - `test_run_all_refuses_a_network_root` (list and sample fail the test).
- PR-LOW-031: materiality=docs-only severity=verified LOW surface=production rec=Fix-now ⚡.
  - **The defect:** the comment at `scribe.iss:212-215` reads "Each bad copy is removed, so the app reports the model missing and never loads damaged bytes; a removal that fails is named". Its own lines `:225-227` (`if not DeleteFile(...) then … '(damaged, and could not be removed)'`) and the docs corrected by PR-LOW-027 contradict "never loads damaged bytes".
  - **What the fix should say:** the deletion is attempted; a copy that could not be removed is named, Setup exits 9 (`GetCustomSetupExitCode`), and the app must not be opened before Setup is run again.
  - siblings=none (grep of the `.iss`, PR-LOW-027's three docs and `docs/design-system.md` for "removed"/"deleted" found no other unconditional claim). The ISCC re-compile is owed only if code lines change; a comment-only edit compiles identically.
- PR-LOW-032: materiality=docs-only severity=verified LOW surface=docs rec=Fix-now.
  - **The defect:** `threat-model.md:212-216` says "a developer build also holds it in the production folder (creating the folder if absent, and touching nothing else there) … — the one place the dev channel uses the production folder." The same document at `:3187-3192` gives "two named exceptions": `app.lock` and the one-time `register-native-host.py --unregister` migration, which deletes the old per-user registration's two files. Flow 24 (`data-flow-map.md:1051-1055`), the retention row (`retention-schedule.md:87`) and AGENTS.md's Database Notes all name both exceptions.
  - **The fix:** say "the running dev app's one use of the production folder", and point to the separate one-time migration.
  - siblings=`install_layout.py:158-168` `instance_guard_root`'s docstring. Its claim "D3/C8 name the guard as the one thing the dev channel shares … reads or writes nothing else in it" is accurate for the running app but unqualified; the fix should qualify it in the same words. Pre-existing (Phase 1 Task 1.5 text, carried through H.1).

Cap verdict: accept — production-behavioral — peer_round 2 of cap 5. Findings are converging (12 → 5, all LOW). Each fix is local: one helper's allow-list plus its tests; one benchmark pre-check and a sample guard; three or five test tripwires behind one conftest helper; two comment or doc edits with one docstring sibling. They fit one fix leg and a confirmation round 29 inside the cap, so no raise is warranted.

#### LEG 2 dispositions (executor leg i4-x8, 2026-10-03)

Per the composer's disposition (five `stage-4/r28/PR-LOW-0NN` auto-disposition records), all five are Fix-now with the siblings named above, and all five were Applied one at a time with re-read:
- PR-LOW-028 Applied (the allow-list helper, with 16 new shape cases);
- PR-LOW-029 Applied (the temporary-folder pre-check and the sample-writer guard, with 6 tests);
- PR-LOW-030 Applied (`forbid_network_io` across 5 refusal tests, plus its own 8 tests);
- PR-LOW-031 Applied (comment-only);
- PR-LOW-032 Applied (the threat model, with the `instance_guard_root` docstring sibling).

None was routed to Accept, Defer or Include in plan.

Fix-delta self-check: PASS — I re-read every applied hunk across 11 files:
- **`is_unc_path`:**
  - Every earlier case keeps its answer: plain and mixed `\\` / `//` leads are still network; `C:\`, `/x`, `\x`, relative and empty paths are still local.
  - A `\\??\` string is not mistaken for the `\??\` prefix.
  - Pipe names are never passed to it (no caller does).
- **The temporary-folder pre-check:**
  - It sits after the models-root refusal and listing, and before `TemporaryDirectory`.
  - It reads values only.
  - It fails closed when any candidate variable is network, even one that `tempfile` would not choose: a deliberate over-refusal of a same-user setting, never an SMB touch.
- **`generate_speech_sample`:** the guard comes before its imports, so the local-path callers (`run_all`, `tests/sapi_fixture.py`'s users) are unchanged.
- **`forbid_network_io`:**
  - It wraps only `Path` methods, binding each original through a default argument, so there is no late-binding bug in the loop.
  - The AssertionError is not caught by `status.read_registration_status` (it catches only `ValueError`/`KeyError`/`TypeError`/`OSError`).
- **The two replaced spies:** they keep their behavioural assertions; the `touched` lists went with them. ruff clean; mypy clean (58 source files).

### Round 29 - 2026-10-03 - Phase H confirmation of round 28's fix, independent cross-family codex peer review (pass stage-4.p1)

- Round status: Closed (0 pending). PR-LOW-033 and its five siblings Applied by leg i4-x10; composer suite 6 5835 passed / 23 skipped; codex round 30 confirmed the class closed and raised 1 docs-only LOW on the new comments.
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: the 11 files leg i4-x8 changed (one slice), round 28's block and C1–C10; composer transcription of `.cursor/loops/stage-4-peer-r29X.log`, `PR-LOW-X01` renumbered PR-LOW-033.

#### Findings
- **PR-LOW-033** (LOW, test-harness, `desktop/tests/test_transcription.py:1059`): PR-LOW-030 leaves an unprotected sibling: the UNC availability/resolver test lacks a filesystem tripwire, despite round 28 describing it as already protected. A regressed guard could reach the network before assertions fail. — Evidence: `monkeypatch.setenv("LOCALAPPDATA", r"\\evil-host\share")` immediately precedes `assert not whisper_model_available()`; subsequent calls include `resolve_whisper_model()` and `WhisperSpeechProvider()` without `forbid_network_io(monkeypatch)`. Recommendation: Fix-now — Apply the shared helper before these calls and correct round 28’s sibling classification. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x10)) — `forbid_network_io(monkeypatch)` now guards the finding (`test_transcription.py::test_unc_localappdata_reports_unavailable_without_io`, before `LOCALAPPDATA` is set) and every enumerated sibling: class (a) `test_speaker_embedding.py::test_missing_and_unc_paths_refused_before_onnxruntime_import`, `test_language_model_runtime.py::test_unc_path_is_refused_before_the_factory` and `::test_unc_path_reports_unavailable_without_touching_it`; class (b) `test_speech.py::test_unc_availability_probe_refuses_without_io` and `test_speaker_embedding.py::test_unc_availability_probe_refuses_without_io` (their `is_file`-only `_boom` replaced). No probe catches `AssertionError` (each catches `OSError`/`RuntimeError`/`ValueError` at most), so a regression fails loudly. Round 28's sibling sentence carries a `[2026-10-03 correction]` line.
- Verification counts: 6 claims checked, 6 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-03

#### LEG 1 verified tuples

Executor leg i4-x9, 2026-10-03. Verification only; nothing was fixed. The finding is REAL and LOW. It is ⚡: an incomplete sibling closure of round 28's PR-LOW-030, caused by a wrong claim in MY round-28 LEG 1 tuple. That tuple said "The probe tests next to them (`test_speech.py:332`, `test_transcription.py:1048`) already raise". `test_speech.py:335` does raise (its `_boom` on `is_file`), but the transcription test has NO tripwire, and I had not read it. The class was then enumerated from the code: the test tree was grepped for `\\` / `//` / mixed-slash literals, `evil`, `share` and `UNC`, and each hit was read.
- PR-LOW-033: materiality=test-harness severity=verified LOW surface=test-harness rec=Fix-now.
  - **The defect:** `test_transcription.py:1051-1065` `test_unc_localappdata_reports_unavailable_without_io` runs `monkeypatch.setenv("LOCALAPPDATA", r"\\evil-host\share")`, then `assert not whisper_model_available()`, `assert not whisper_model_available(FALLBACK_WHISPER_MODEL)`, `assert resolve_whisper_model() == DEFAULT_WHISPER_MODEL`, `apply_offline_env()` and `WhisperSpeechProvider()` under `pytest.raises(TranscriptionModelError, match="UNC")`. No `forbid_network_io`, no spy.
  - **Reach on a regression:**
    - `whisper_model_available` (`transcription.py:925` guard, then `:927` `whisper_snapshot_complete(model_dir)`) would reach `benchmark._present` (`benchmark.py:181-185`: `path.is_file() and path.stat()`) on `\\evil-host\share\ClinikoScribe\models\whisper\…`. The conftest pins the production channel and is not frozen, so `models_root` reads `LOCALAPPDATA`.
    - The provider's `whisper_snapshot_missing(path)` (`transcription.py:989`) would do the same, so the run makes SMB name lookups before any assertion fails.
  - **Why LOW:** the guard holds today (the suite is green), so the exposure is only a hypothetical regression's I/O, never wrong behaviour.
  - **The fix:** call `forbid_network_io(monkeypatch)` before the first call (it already imports into this module), and correct my round-28 sibling sentence in the `/fix` notes.
  - **siblings, the full enumerated class** (tests that hand a network `LOCALAPPDATA`, models root or model path to a function that can reach the filesystem):
    - **(a) NO filesystem tripwire, real siblings to fix the same way:**
      - `test_speaker_embedding.py:286-295` `test_missing_and_unc_paths_refused_before_onnxruntime_import`, its UNC leg `load_onnx_session(Path(r"\\evil-host\share\model.onnx"))`. Only `sys.modules["onnxruntime"] = None` guards it, and on a regression `speaker_embedding.py:286` `model_path.is_file()` (and the digest read `sha256_of_file` → `path.open("rb")`) run BEFORE the import.
      - `test_language_model_runtime.py:445-452` `test_unc_path_is_refused_before_the_factory`. Only `record == []` (the factory) guards it, and on a regression `language_model.py:259` `path.is_file()` runs first.
      - `test_language_model_runtime.py:714-715` `test_unc_path_reports_unavailable_without_touching_it`. No guard at all, and on a regression `language_model.py:147` `path.is_file()` runs.
    - **(b) A single-method tripwire, adequate for today's code:** a `_boom` on `Path.is_file` only, which is each probe's ONE filesystem call after its guard (`speech.py:378`, `speaker_embedding.py:261`). Switch them to `forbid_network_io` for one shape across the class (recommended, optional):
      - `test_speech.py:335-347` `test_unc_availability_probe_refuses_without_io` (both its explicit-path and its `LOCALAPPDATA` leg);
      - `test_speaker_embedding.py:553-562` `test_unc_availability_probe_refuses_without_io` (both legs).
    - **(c) Already on `forbid_network_io`:**
      - `test_frozen_runtime.py:806` and `:820`;
      - `test_benchmark.py:242` (with `faster_whisper` stubbed too);
      - `test_speech.py:327`;
      - `test_transcription.py:979`;
      - the helper's own self-tests in `test_install_layout.py`.
    - **(d) Their own failing fakes, adequate:**
      - `test_benchmark.py:219` (`is_dir`/`iterdir` raise);
      - `test_benchmark.py:257` (listing and sampling fail the test);
      - `test_benchmark.py:268` (`TemporaryDirectory` and sampling fail);
      - `test_benchmark.py:291` (`win32com.client` import fails);
      - `test_frozen_runtime.py:920` (`read_text` raises, and the host reads nothing else).
    - **(e) Not in the class (no filesystem reach):**
      - `test_frozen_runtime.py:135-180`: `is_worker_argv` / `worker_argv` string checks;
      - `test_install_layout.py` `TestIsUncPath`: pure;
      - `test_exclusions.py:211-250`: `check_location` reads only through `FakeLayer` (`realpath`, `drive_type`), and the real layer is refused by the conftest C6 sentinel;
      - the pipe-name constants in `test_identity.py`, `test_display_name.py`, `test_pipe_client.py`, `test_pipe_server.py` and `test_integration_no_sockets.py` (never passed to `is_unc_path` or a `Path` call).

Cap verdict: accept — test-harness — peer_round 3 of cap 5. Findings are converging (12 → 5 → 1, all LOW, none behavioral). The fix is mechanical: `forbid_network_io` added to the finding plus 3 class-(a) tests, optionally class (b)'s 2 as well, with no production code touched. One fix leg and confirmation round 30 fit inside the cap, so no raise is warranted.

#### LEG 2 dispositions (executor leg i4-x10, 2026-10-03)

PR-LOW-033 Applied, per the composer's `stage-4/r29/PR-LOW-033` auto-disposition: the finding, plus every sibling in classes (a) and (b), so the enumerated class is closed in one leg. Classes (c)–(e) are unchanged by design.

Fix-delta self-check: PASS — I re-read the 6 changed tests across 5 files:
- Each calls `forbid_network_io` BEFORE its first network-path call. In `test_transcription.py` it also comes before `LOCALAPPDATA` is set.
- `test_missing_and_unc_paths_refused_before_onnxruntime_import`'s local `tmp_path` leg still reaches the real `is_file` (local paths pass through) and still expects "setup-models".
- The two `_boom` helpers were removed whole. `Path` is still used elsewhere in both files (ruff clean).
- No production code was touched. ruff clean; mypy clean (58 source files).

### Round 30 - 2026-10-03 - Phase H confirmation of round 29's fix, independent cross-family codex peer review (pass stage-4.p1)

- Round status: Closed (0 pending). PR-LOW-034 Applied by leg i4-x12 (comments only); closed on composer suite 7 (5835 passed / 23 skipped) without a confirmation round, per the cap verdict (gate record `h5-peer-close`, peer_round 4 of cap 5). Peer pass stage-4.p1 CLOSED, trajectory 12 → 5 → 1 → 1.
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: the five test files leg i4-x10 changed plus `conftest.py`, round 29's block and C6; composer transcription of `.cursor/loops/stage-4-peer-r30X.log`, `PR-LOW-X01` renumbered PR-LOW-034 (peer category `comment-accuracy` recorded as docs-only).

#### Findings
- **PR-LOW-034** (LOW, docs-only, `desktop/tests/test_language_model_runtime.py:722`): New comments overstate the tripwire’s coverage as all filesystem calls; it patches only eight named `Path` methods, not direct `os` or built-in file operations. — Evidence: “any filesystem call on the network path raises”; siblings `desktop/tests/test_speech.py:341` and `desktop/tests/test_speaker_embedding.py:560` say “every filesystem call”; `desktop/tests/conftest.py:170` limits patching to “for method in NETWORK_IO_METHODS:”. Recommendation: Fix-now — Qualify these comments and the equivalent “any filesystem call” comments in transcription and speech as covering the `Path` methods listed in `NETWORK_IO_METHODS`. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x12)) — all ten class-(a) comments and docstrings are reworded to the listed `Path` methods. The `conftest.forbid_network_io` docstring now names what it does NOT cover: direct `os` calls, the built-in `open`, unlisted `Path` methods, and native libraries given a `str` (each test stubs that import or factory). The other nine: `test_language_model_runtime.py`, `test_speech.py` ×2, `test_speaker_embedding.py`, `test_transcription.py` ×2, `test_frozen_runtime.py` ×2 and `test_benchmark.py`. Comments only: no statement, assertion or test count changed.
- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-03

#### LEG 1 verified tuples

Executor leg i4-x11, 2026-10-03. Verification only; nothing was fixed. The finding is REAL, LOW and docs-only (test comments). It is ⚡: the wording was written by legs i4-x8 and i4-x10.
- **What `forbid_network_io` actually does:** `conftest.py:150-159` `NETWORK_IO_METHODS = ("exists", "is_file", "is_dir", "stat", "open", "read_text", "read_bytes", "iterdir")`, and `:170-180` patches only those `pathlib.Path` methods. `os.stat` / `os.path.*`, built-in `open`, `wave.open`, `Path.resolve` / `lstat` / `glob`, and native libraries handed a `str` (CTranslate2, onnxruntime, llama.cpp) are not covered.
- **The coverage is adequate for today's code.** Every guarded function's post-guard filesystem reach is one of those `Path` methods: `_present` (`benchmark.py:181-185`: `is_file`, `stat`), `sha256_of_file` (`speaker_embedding.py:267`: `path.open`), the probes' `is_file`, and `status`'s `is_file` / `read_text`. Each native-library hand-off sits behind an import or factory stub in its test: `faster_whisper`, `onnxruntime`, the fake `llama_factory`; `SileroVad` and `WhisperSpeechProvider` reach a `Path` check first. So only the WORDING overclaims.
- PR-LOW-034: materiality=docs-only severity=verified LOW surface=test-harness rec=Fix-now.
  - **The fix:** word every one as "the `Path` methods in `NETWORK_IO_METHODS`" (or "a listed `Path` call"), and name in the conftest docstring what the helper does NOT cover (direct `os` calls, built-in `open`, unlisted `Path` methods, native libraries given a `str`).
  - **siblings, the full enumeration** (grep of the test tree for `forbid_network_io`, "filesystem call", "without touching", "SMB" and "reached a network", each hit read):
    - **(a) Claims wider than the listed `Path` methods, to reword:**
      - `test_language_model_runtime.py:721-722` ("'without touching it' is enforced — any filesystem call on the network path raises"; the cited line);
      - `test_speech.py:341-342` ("the shared tripwire (every filesystem call on a network path raises)");
      - `test_speaker_embedding.py:560-561` (the same sentence);
      - `test_speech.py:329-330` ("fails here before any filesystem call on the network path");
      - `test_transcription.py:981-982` (the same);
      - `test_transcription.py:1059-1060` (the same);
      - `test_frozen_runtime.py:810-811` ("a regressed guard fails here BEFORE any filesystem call");
      - `test_frozen_runtime.py:825-826` ("the network launcher fails the test before any filesystem call if reached");
      - `test_benchmark.py:249-251` ("… and no `Path` call reaches it either": wider than the eight methods);
      - `conftest.py:163-167`, the helper's own docstring ("so a regressed guard fails the test without any SMB I/O"). That is true only for a regression whose I/O goes through a listed `Path` method, so the docstring should state the boundary.
    - **(b) Accurate, no change:**
      - `test_language_model_runtime.py:446-448` and `test_speaker_embedding.py:292-294`: "fail at the filesystem call", meaning the presence check (`is_file`) and the digest read (`Path.open`), both listed;
      - `test_install_layout.py:353-354`: "a network path raises at the call; a local one passes", parametrized over exactly `NETWORK_IO_METHODS`;
      - `test_frozen_runtime.py:809`: "no stat or read of a network-share path", which describes the code under test, not the tripwire.
    - **Not in scope:** the plan's own round-28/29 `/fix` notes already say "every `Path` call in `NETWORK_IO_METHODS`", which is accurate; the hits in `test_ui_prose_stage.py:164` and `test_ui_screens.py:7798` ("without touching" the clipboard or the disk write) are unrelated.

Cap verdict: accept — docs-only — peer_round 4 of cap 5; RECOMMEND closing without round 31.
- Findings are converging (12 → 5 → 1 → 1), and this one is comment-only: ten comment or docstring edits in seven test files, with no statement, assertion or test count changed.
- The suite's outcome cannot depend on it, and codex round 30 already confirmed the behavioural class closed.
- A round 31 would spend the cap's last round on prose. Instead, close round 30 on the composer's green suite (expected count unchanged) plus the fix leg's self-check, which should include a mechanical grep showing that no test comment or docstring still says "any/every filesystem call" or "without any SMB I/O" unqualified.
- The fifth round stays in reserve, so no cap raise is needed.

#### LEG 2 dispositions (executor leg i4-x12, 2026-10-03)

PR-LOW-034 Applied over every class-(a) sibling, per the composer's `stage-4/r30/PR-LOW-034` auto-disposition; class (b) is unchanged by design. The peer pass closes without round 31, per the cap verdict and the `h5-peer-close` gate record.

Fix-delta self-check: PASS — I re-read the 10 reworded comments and docstrings across 7 test files.
- Each now states the boundary as the `Path` methods in `NETWORK_IO_METHODS` (or "its first listed `Path` call"), and the conftest docstring names what is NOT covered.
- **Mechanical check:** a case-insensitive grep of `desktop/tests` for `(any|every) filesystem call|without any SMB|before any filesystem|no \`Path\` call` returns ONE line, `test_transcription.py:1056` ("LOCALAPPDATA must short-circuit to False BEFORE any filesystem touch"). That is the peer-round-36 comment describing the CODE under test (the probe's guard), not the tripwire, the same class (b) as `test_frozen_runtime.py:809`. It is correct as written.
- No code line changed. ruff clean; mypy clean (58 source files).

### Round 31 - 2026-10-03 - Tasks 3.1 and 3.6, the first Release run's failure (executor stage-3 leg i3-x9)

- Round status: Closed (0 pending). MED-001 was Applied by leg i3-x9 at 2026-10-03T10:02:57+10:00. Closed 2026-10-03 (composer): the practitioner regenerated the lock (59 pins), the composer suite passed, and the re-dispatched `Release` run 37081519723 on `e730cd5` was green and attested.
- Source: first Release run (CI), composer-observed
- Reviewer: composer (observed `Release` run 37079569271); diagnosis and fix by executor `claude-opus-5-5` (high).
- Scope: `scripts/lock-build-requirements.py`, `scripts/build-release.py`'s PyInstaller install and preflight, their tests, and Tasks 3.1 / 3.6.

#### Findings
- **MED-001** (MED, build, `scripts/lock-build-requirements.py:57` / `scripts/build-release.py` PyInstaller-from-source install): the hashed build lock lacked PyInstaller's build backend. `build-release.py` installs the pinned PyInstaller source with `pip install --no-deps --no-build-isolation`, so pip uses only what the build venv already holds, and the source's `pyproject.toml` declares `[build-system] requires = ["hatchling"]`, `build-backend = "hatchling.build"`. The lock, generated from the proven environment's freeze plus Task 0.1's three tool pins, carried no hatchling: Task 0.1's spike installed WITH build isolation, which fetched hatchling unhashed and hid the need. — Evidence: `Release` run 37079569271 failed with `BackendUnavailable: Cannot import 'hatchling.build'` (CI run 37079562194 on the same commit green). Why MED, not HIGH: the build of record cannot be produced, but the failure is closed (no artifact, no attestation, nothing ships), and the control held. Recommendation: Fix-now — lock the backend; do not drop `--no-build-isolation`, which is what keeps every build input hash-pinned. /fix decision: Applied (2026-10-03, Claude Code (executor stage-3 leg i3-x9)):
  - **The lock generator:** `BUILD_TOOL_PINS` gains `hatchling` 1.32.4 and its Requires-Dist closure on Python 3.14 — `pathspec` 1.1.1, `pluggy` 1.6.0, `tomlkit` 0.15.1, `trove-classifiers` 2026.9.21.13 (`packaging` is already locked from the freeze; `tomli` applies only below 3.11), the versions the composer read from PyPI on 2026-10-03. `EXTRA_REQUIREMENTS` gains `hatchling`, so `pip download` resolves its closure under those pins. How the code treats them (confirmed): `generate` builds `pins = proven_pins(freeze) | BUILD_TOOL_PINS`, so a build-tool pin is both a constraint and the ONLY admitted version, and it wins over a freeze version of the same name (acceptable: these run only while PyInstaller installs into the build venv, never in the app); a downloaded wheel at any other version is refused by name.
  - **The build's preflight (the optional refusal, taken):** `PYINSTALLER_BUILD_REQUIRES = ("hatchling",)` sits beside `PYINSTALLER_COMMIT`, its comment naming the source's `[build-system]` lines. Preflight now refuses, before any venv or `waf` work, (1) a lock with no `hatchling==` entry ("lacks hatchling, the build backend of PyInstaller's source; generate the lock again …") and (2) a PyInstaller source whose `pyproject.toml` declares a build requirement outside that tuple, or none it can read (`pyinstaller_build_requires`, tomllib; names PEP 503-normalised). Reasoning: a stale lock or a changed backend otherwise fails only after the slow venv install and the bootloader build, as this run did; the check is a file read, and the commit pin already fixes the source, so (2) is defence for a future pin bump.
  - **Tests:** `test_build_release.py` — the fixture lock carries `hatchling==1.32.4` and the fixture source a `pyproject.toml`; four new preflight refusal cases (lock lacks the backend, backend changed, no `pyproject.toml`, no `[build-system]`); `test_every_build_requirement_of_pyinstaller_is_locked` (each name in `PYINSTALLER_BUILD_REQUIRES` is in the lock script's `BUILD_TOOL_PINS` and `EXTRA_REQUIREMENTS`, hatchling's four dependencies are pinned, `packaging` is requested) and `test_the_backend_is_read_from_the_source`. `test_build_lock.py` — the pin dict test now asserts all eight; `test_a_build_tool_pin_admits_a_package_the_freeze_lacks` (pathspec 1.1.1 admitted, 1.2.0 refused by name); the committed-lock test asserts each build-tool pin is present with a "regenerate it (Task 3.1)" message.
  - **Docs:** `scripts/README.md`'s build line names the locked hatchling backend. `docs/release/pilot-builds.md` does not describe the build's install step, so it is unchanged. Task 3.1 REOPENED (🟨) with the regeneration step; Task 3.6 records the run and this fix.
  - **Residue (named, not closable offline):** a hatchling build hook could request more through `get_requires_for_build_wheel`; under `--no-build-isolation` pip does not install those, so the re-dispatched `Release` run is the proof. `desktop/requirements-build.txt` NOT touched (practitioner step).
- Verification counts: 1 claim checked (the CI log line and the source's `[build-system]`, as the composer quoted them; no network here to re-read either), 1 confirmed, 0 dropped
- Last reviewed: 2026-10-03

### Round 32 - 2026-10-03 - Task H.6 (the models-root pin), in-session /review-loop pass 1 (executor stage-4 leg i4-x13)

- Round status: Closed (0 pending). All 3 Applied by leg i4-x13 at 2026-10-03T11:55:00+10:00; ruff clean, mypy clean (58 source files). Closed 2026-10-03 by the composer's suite 8: ruff clean, mypy clean (58 files), pytest 5872 passed / 9 skipped.
- Source: in-session /review (the composed /review-loop), over `git diff ee6b657` including uncommitted work
- Reviewer: executor `claude-opus-5-5` (high), same session as the build
- Scope: `desktop/tests/conftest.py`, `desktop/pyproject.toml`, `test_frozen_runtime.py`, `test_install_layout.py`, `test_language_model_runtime.py`, `test_speaker_embedding.py`, `test_speech.py`, `test_transcription.py`, `test_ui_models.py`, `test_ui_screens.py`, `docs/security/threat-model.md`, `docs/lessons.md`, `AGENTS.md`, this plan's C6 and H.6

#### Findings
- **LOW-001** (LOW, test-harness, `desktop/tests/test_frozen_runtime.py`): the exempt set was checked once by reading; nothing stopped a later test, or a module-level `pytestmark`, from widening the opt-out that step 2 forbids ("never a reason to widen the marker to a module or a file"). Recommendation: Fix-now — pin the set by a source scan. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x13)) — `test_only_the_resolvers_own_tests_opt_out` scans every `test_*.py` for the marker in a class or function decorator (anything else, such as a `pytestmark`, is reported as `<elsewhere>`) and asserts step 2's set plus the two marker tripwires (`_REAL_MODELS_ROOT_MARKED`); `test_the_opt_out_scan_sees_each_form` covers the class, function and two `pytestmark` shapes. A marker applied at run time is named as unseen.
- **LOW-002** (LOW, docs-only, `desktop/tests/test_install_layout.py` `test_every_model_line_carries_this_builds_remedy`): its `setenv("LOCALAPPDATA", …)  # no model is there` comment was stale under the pin, because the models root no longer follows `LOCALAPPDATA`. The sibling is `test_hardware_check.py` `_screen` ("# the model report's stats (C6)"). Recommendation: Fix-now — say what the line still guards. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x13)) — both comments now say C6 for any data root, and that the model stats land in the conftest's empty pin. Each `setenv` is kept, since it still covers the other data roots; neither test asserts on it.
- **LOW-003** (LOW, docs-only, `desktop/tests/conftest.py` / `test_frozen_runtime.py` / `test_ui_models.py`): wording. The pin's docstring said "full here", which is ambiguous outside this computer. The real-ML tripwire's comment ended with a dangling "…". A comment in `test_models_ready_matches_resolved_availability` was left orphaned above a blank line. /fix decision: Applied (2026-10-03, Claude Code (executor stage-4 leg i4-x13)) — "full on the development computer, empty on CI"; "The conftest pin was applied, and the body's pin replaced it."; the blank line is removed.
- Dropped (3):
  - (i) "`mktemp` per test is what the plan names." The session parent plus numbered children keeps every stated property: fresh, empty, per test, outside `tmp_path`, and under the base temp. It avoids an O(n²) rescan of the base folder by `make_numbered_dir`, as the factory docstring says. Recorded as an interpretation, not a defect.
  - (ii) "The three UNC tests no longer use `LOCALAPPDATA`." That is intended: under the pin, a UNC `LOCALAPPDATA` no longer reaches the probe, so each test would pass hollow. They now pin a network models root with `use_models_root`, which keeps their refusal non-vacuous. The `LOCALAPPDATA` → root mapping is `TestModelsRoot`'s job.
  - (iii) "`test_hardware_check.py` is outside H.6's named files." Its comment is a pure-comment sibling of LOW-002, so it is not scope expansion.
- Verification counts: 6 claims checked, 3 confirmed, 3 dropped
- Last reviewed: 2026-10-03

### Round 33 - 2026-10-03 - Task H.6, in-session /review-loop pass 2 — re-review after round 32's fix (executor stage-4 leg i4-x13)

- Round status: Closed (0 pending); no findings.
- Source: in-session /review (the composed /review-loop), the round-32 fix delta plus a re-read of the whole H.6 diff
- Reviewer: executor `claude-opus-5-5` (high)
- Post-fix regression check: the opt-out scan's expected set equals the eight decorated sites, because a class decorator's comment is not part of the AST. No `real_models_root` attribute appears outside a decorator: the docstrings, `get_closest_marker("real_models_root")` in `conftest.py` (not a `test_*.py` file) and the parametrized source strings are constants. ruff clean, mypy clean (58 source files).
- Dropped (2):
  - (i) "The marker tripwires are not 'the resolver's own tests', as the docs say." They assert which resolver is in place (`models_root is REAL_MODELS_ROOT`), and step 4 (b) itself requires a marked class, so the docs' wording holds.
  - (ii) "`record_path_io` records a path twice when one listed method calls another." Harmless: the assertion is over set membership, and non-emptiness is the only count used.
- Verification counts: 2 claims checked, 0 confirmed, 2 dropped
- Last reviewed: 2026-10-03

### Round 34 - 2026-10-03 - Task H.6, cross-family peer pass stage-4.p2 (composer-seat codex)

- Round status: Closed (0 pending); no findings.
- Source: codex `gpt-6-astra` (medium), read-only sandbox, `.cursor/loops/stage-4-peer-r34A.log` in the main checkout; peer_round 1 of cap 5
- Scope: one slice of 14 files — `desktop/pyproject.toml`, `desktop/tests/conftest.py`, the nine changed test files, `docs/security/threat-model.md`, `docs/lessons.md`, `AGENTS.md` — plus this plan's H.6, C1–C10 and rounds 32–33
- The peer read every diff and searched the tests for `models_root`, `LOCALAPPDATA`, the real-ML fixtures, subprocess starts and module-level model defaults, looking for a route to a models folder that bypasses the pin. It found none.
- Verification counts: 2 claims checked, 0 confirmed, 2 dropped as unverifiable
- PEER-ROUND-34-A RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0). The peer pass converged at its first round; no confirmation round is owed.
- Last reviewed: 2026-10-03

### Round 35 - 2026-10-03 - Phase P.1 live smoke on the installed 0.1.0 (practitioner-observed)

- Round status: Closed on the composer-run suites (MED-001 Applied by executor stage-5 leg i5-x1; the remaining overlap is round 36 MED-001).
- Source: practitioner smoke (Task P.1 step 10), composer-observed from the installed app's log
- Reviewer: composer `claude-opus-5-5`; observation by the practitioner

#### Findings
- **MED-001** (MED, behavioral, `desktop/src/scribe_desktop/session.py` `_on_capture_failure` / `audio_capture.py` `CaptureWorker`): the first recording after installing failed one second after Start, and the cause cannot be read back because the capture failure's exception type is never logged. — Evidence: `%LOCALAPPDATA%\ClinikoScribe\logs\scribe-app.log`: `15:52:30,562 … session_transition session_id=f12d6080… session_state=recording`, `15:52:31,575 … live_transcriber_stop_timeout … session_state=recording`, `15:52:31,575 … session_transition … session_state=failed`; `_on_capture_failure(self, _exc)` discards `_exc`; `CHUNK_BYTES` is one second of audio, so the failure is at the first chunk (`store.append_chunk` raising) or a PortAudio status flag (`CaptureOverflowError` "device reported dropped frames"). It did not recur in the same process or after a relaunch. Likely (unconfirmed): the live worker's first model load after install (first Defender scan of the new DLLs and model files) starving the capture path. Recommendation: Fix-now — (1) log the capture failure's type name (content-free, like the exception hooks) so the next occurrence is diagnosable; (2) find and remove the starvation path, e.g. load the live worker's models off the capture path or before Start, and check whether a dropped-frames status at stream start should fail a session at all; (3) a test that a slow live-worker load cannot fail capture. /fix decision: Applied (executor stage-5 leg i5-x1, 2026-10-03):
  - **Diagnosis (from the code; the log cannot confirm it).** Every path from `recording` to `failed` runs `CaptureWorker._fail` → `on_failure` → `SessionController._on_capture_failure` → `_fail_locked`, which stops the live worker with the 1 s in-lock bound (`_LIVE_STOP_LOCKED_TIMEOUT_S`) and only then logs `failed`. So the stop-timeout at 31,575 puts the failure's arrival at ≈30,575 — about 13 ms after the `recording` line (the callback waits on the controller lock Start holds, so it may have fired during Start). "One second after Start" is the stop bound, not a chunk. The paths, ranked:
    1. **PortAudio status flag → `CaptureOverflowError` (MOST LIKELY).** The callback delivers the block and then fails on any truthy status (input overflow = the device dropped frames). It is the only path that can fire within ~100 ms of `stream.start()`. Supporting evidence: (a) the live worker was busy 1 s later — `stop` timed out, so it was inside an uninterruptible call, and the only one possible before any window is ready is `_load_models` (VAD → `SileroVad` imports numpy + onnxruntime; Whisper → `WhisperSpeechProvider` imports faster-whisper, which brings ctranslate2, tokenizers and av); (b) it was this process's FIRST import of that stack, from a fresh install (new DLLs Defender had not scanned, modules from the PYZ); (c) a retry in the SAME process rebuilt every model but re-imported nothing, and passed; a relaunch passed on now-scanned files. Mechanism: the load runs on the worker's own thread (D3), never the capture worker thread. But sounddevice's callback is Python and needs the GIL, and an extension module's initialisation, or any C call that holds the GIL, starves it beyond the ~100–200 ms host buffer (blocksize 100 ms). The Windows loader lock during a Defender-scanned `LoadLibrary` is a variant the log cannot tell apart.
    2. **`finished` callback → `DeviceLostError` ("stream ended").** Possible at any time. Nothing points to it: the retry on the same device recorded normally.
    3. **The sink (`store.append_chunk` raising, `StoreWriteError`).** Needs a full 1 s chunk (`CHUNK_BYTES`), so it is excluded by timing unless the capture worker was itself starved for over 1 s, and a disk-full or key error would have recurred. Unlikely.
    4. **`_on_block` `queue.Full`.** Needs 256 blocks (about 25 s). Excluded.
    5. **The live worker's `start` or `feed`.** `start` only spawns a thread. `feed` never raises: the tee fails the worker instead, and the store's exception is the only one that crosses it. Neither can fail capture directly. Excluded except as the GIL starvation in (1).
  - **What the log cannot distinguish:** (1) from (2); GIL hold from loader lock from plain CPU/disk contention; and which module or model was loading.
  - **Diagnosable now:** `_on_capture_failure` logs `capture_failure detail_code=<word> error_code=<type name> session_id=… session_state=…` before the `failed` transition, never the message. `detail_code` comes from the fixed `audio_capture.CAPTURE_DETAIL_CODES`, built from the flag attributes and never from `str(status)`: `status_input_overflow`, `status_input_underflow`, `status_other`, `stream_ended`, `open_failed`, `queue_full`, `unspecified`, and `none` for a non-capture error such as `StoreWriteError`.
  - **Fix (structural, the import phase):**
    - New `ml_warmup.ImportWarmup`: `app.main` starts it once the guard is held. On a daemon thread it imports numpy, onnxruntime (telemetry off) and faster-whisper, after asserting the offline switches. Modules only: no model, audio, session or connection. It logs `ml_warmup state=done|failed duration_ms=… [error_code=<type>]`.
    - Until it finishes, `MainWindow(live_ready=…)` makes the live-worker factory return None. `SessionController` accepts that: no worker is attached, it logs `live_transcriber state=not_attached`, Finish takes the batch path, and the empty live view shows `LIVE_TRANSCRIPT_NOT_READY_PLACEHOLDER` without the header. The 0.1.0 failure came 10 minutes after launch, so the warm-up would have long finished.
    - Per-session model construction still runs on the worker's thread beside capture. The same-process retry is the evidence that this is harmless; nothing bounds it. The residue is named in the threat model.
  - **The dropped-frames rule (decided: unchanged).** A status flag in a stream's first moments still fails the session. Reasons:
    1. The never-silently-drop rule has no time exemption, and the opening seconds often hold the introduction and consent conversation.
    2. The failure is visible and the audio is recoverable.
    3. The cause is removed rather than tolerated.
    4. Tolerating it would weaken the rule, which needs the practitioner (MUST-PAUSE).
  - **Recommended follow-up, not built (needs a hardware smoke):** a larger PortAudio input latency (`RawInputStream(latency=…)`) would let a GIL stall of up to that length pass without dropped frames, whatever its cause.
  - **Tests:**
    - A blocked model load never fails capture.
    - A factory that returns None records without a worker.
    - The `capture_failure` line, three ways: type name and detail word only, logged before `failed`.
    - The detail codes.
    - `ml_warmup`.
    - The window gate and the not-ready view.
    - `app.main` ordering: the warm-up after the guard, and its readiness reaching the window.
    - The startup no-sockets proof now runs the warm-up.
- Verification counts: 1 claim checked, 1 confirmed (by the log), 0 dropped
- Last reviewed: 2026-10-03

### Round 36 - 2026-10-03 - round 35 MED-001's fix diff (in-session /review-loop pass 1)

- Round status: Closed on the composer-run suites (MED-001 Applied as the practitioner's option (b), leg i5-x2); the 8 LOW Applied.
- Source: in-session /review (the composed /review-loop) over the uncommitted diff, plus one independent read-only general-purpose subagent asked to find failing or flaky tests (the executor cannot run pytest: verify=composer)
- Reviewer: executor `claude-opus-5-5` (high), stage-5 leg i5-x1
- Post-fix regression check: ruff clean, mypy clean (59 source files). The subagent traced every exact log string (`log_event` sorts keys), the log-before-`failed` ordering, the 5 s live-queue arithmetic and the one-segment VAD outcome, and found no test that would fail.

#### Findings
- **MED-001** (MED, behavioral, `ml_warmup.py` / `ui/main_window.py` `_build_live_transcriber`): a Start made while the warm-up still runs withholds the live worker, but the warm-up's own imports carry on beside the capture stream — the round 35 overlap, narrowed to that window, not removed. Its length is unmeasured on a first launch after an install (now logged as `ml_warmup duration_ms`). Closing it needs Start to wait or refuse while warming, a clinician-facing change. Recommendation: practitioner decision — (b) below. /fix decision: Applied — **the practitioner chose (b) on 2026-10-03** (gate `r36-med001-early-start`, in chat). Built by executor stage-5 leg i5-x2:
  - `ImportWarmup.holds_start` is True while the warm-up runs AND less than `START_HOLD_SECONDS` = 60 s have passed since it began. It is False before start, once the warm-up finishes or fails, and after the bound. The clock is injectable.
  - Why 60 s: it is the practitioner's "about a minute", and about ten times the frozen spike's cold Whisper load (5.3 s, imports and model together) or prose load (6.9 s).
  - `SessionScreen.set_start_hold` / `start_held`: `on_start` refuses after the consent check and BEFORE clearing the tick, so the tick is kept. `start_linked` refuses before clearing the desktop tick. `ChromeBridge._start` refuses as `getting_ready` right after the lock check. All of these refuse before `SessionController.start`, so there is no audit `begin`, no folder and no key.
  - The line, on both the Session tab and the panel, is `START_GETTING_READY_MESSAGE`: "Clinic Scribe is still getting ready - start again in a moment."
  - A Start admitted after the bound while the warm-up still runs keeps the round-35 behaviour: no live worker.
  - Stated residue: the side panel clears its own tick when it sends Start. This is extension behaviour shared by every Chrome refusal; the extension is not touched here. Options: (a) accept as a residue (as built; named in the threat model, `ml_warmup` docstring and data-flow map); (b) refuse Start while the warm-up runs, bounded (e.g. at most 60 s after launch, then record without the live worker), with a Session-tab and side-panel line "Clinic Scribe is still getting ready — start again in a moment", through the existing start guard; (c) a wait-then-start Start (asynchronous; a larger change).
- **LOW-001** (`ui/transcript.py` `begin_live_view`): the not-ready view showed the header "Live — updates while recording" although nothing would update. /fix decision: Applied — the header is hidden when not ready (tests updated).
- **LOW-002** (`ml_warmup.py` docstring, threat model): the causal story read as confirmed. /fix decision: Applied — "most likely (the log could not name it)".
- **LOW-003** (`enrolment.py:167`, the mock backend): pattern siblings without a detail word. /fix decision: Applied — `queue_full`, `open_failed`, `stream_ended`.
- **LOW-004** (`tests/test_integration_no_sockets.py`, the startup child): the "mirrors app.main" proof did not run the new start-up imports. /fix decision: Applied — the child starts the real warm-up, passes `live_ready`, and waits for it (bounded 45 s) before READY.
- **LOW-005** (`session.py` `_start_locked`): `live_transcriber state=not_attached` was logged before the capture worker started, so a failed Start left a line naming a removed session. /fix decision: Applied — logged only after Start succeeds.
- **LOW-006** (`audio_capture.status_detail_code`): `is True` would misread a truthy non-bool flag. /fix decision: Applied — `bool(...)`.
- **LOW-007** (`ui/transcript.py` `begin_live_view`): a not-ready Start adopted a poster token an earlier failed Start left pending. Harmless today, since that worker is stopped and drops its posts. /fix decision: Applied — a not-ready view adopts none (test added).
- **LOW-008** (`test_audit.py` ×2, `test_hands_free.py`): three `app.main` tests started a real warm-up thread whose offline check depends on what earlier tests left in the environment. /fix decision: Applied — `conftest.InertWarmup`.
- Dropped (2) [round 36]: (i) "`detail_code="none"` is not in `CAPTURE_DETAIL_CODES`" — deliberate: it marks a non-capture error, and the test pins it. (ii) "A daemon warm-up thread mid-import at interpreter exit" — the same as every other daemon worker here; nothing is written.
- Verification counts: 11 claims checked, 9 confirmed, 2 dropped
- Last reviewed: 2026-10-03

### Round 37 - 2026-10-03 - round 36 MED-001's option (b) delta (in-session /review-loop pass 2)

- Round status: Closed on the composer-run suites; 4 LOW Applied, converged (no CRIT/HIGH/MED).
- Source: in-session /review over the leg i5-x2 delta (`ml_warmup.holds_start`, `SessionScreen.set_start_hold` / `start_held`, `ChromeBridge._start`'s `getting_ready`, the wiring, tests and docs), plus the same independent read-only subagent. It traced `Harness.command`'s per-call `state_rev`, that a real `SessionController` constructor touches nothing, that the refusal precedes `SessionController.start` (no audit `begin`), the `REASON_PATTERN` / message limits, and every fake-clock boundary. It predicted no failing test.
- Reviewer: executor `claude-opus-5-5` (high), stage-5 leg i5-x2
- Post-fix regression check: ruff clean, mypy clean (59 source files).

#### Findings
- **LOW-001** (`ui/session_screen.py` `_start`): a third hold check inside `_start`, redundant because both callers check before clearing the tick. /fix decision: Applied — removed; the test calls `start_linked`.
- **LOW-002** (`ui/main_window.py` `_enrolment_blocker`): a voice enrolment opens a microphone stream beside the warm-up's imports, the same hazard. /fix decision: Applied — the blocker returns `START_GETTING_READY_MESSAGE` while the hold applies (tested), and the threat model and design system say so.
- **LOW-003** (`tests/test_integration_no_sockets.py`): the child's `warmup.wait(45)`, after the start-up work, could overrun the parent's 60 s READY read on a cold, Defender-scanned machine. /fix decision: Applied — 30 s.
- **LOW-004** (`ui/session_screen.py` `on_start` docstring): it still said the tick is cleared whatever the outcome. /fix decision: Applied.
- **LOW-005** (the order of checks: the bridge checks the lock then the hold, `on_start` the hold then the lock, inside `_start`): when both apply, the two Starts name different reasons first. /fix decision: dropped as harmless. Both refuse. The overlap is a lock within a minute of launch. Aligning them would change the existing lock path's tick handling, which is outside this decision.
- Dropped (2): (i) the LOW-005 order mismatch, above. (ii) "Start stays enabled and the getting-ready line stays after the hold lifts" — the intended (b) behaviour: the press is refused with a line and the clinician presses again, like every other refusal.
- Verification counts: 7 claims checked, 5 confirmed, 2 dropped
- Last reviewed: 2026-10-03

### Round 38 - 2026-10-03 - cross-family peer pass stage-5.p1 over the rounds 35–37 fix (composer-seat codex)

- Round status: Closed (0 pending). 4 Applied by leg i5-x3; composer suite 3: ruff clean, mypy clean (59 files), pytest 5904 passed / 9 skipped; codex round 39 confirmed all four fixes with no new finding.
- Source: codex `gpt-6-astra` (medium), read-only sandbox, `.cursor/loops/stage-5-peer-r38{A,B,C}.log` in the main checkout; peer_round 1 of cap 5
- Scope: slice A code (`audio_capture.py`, `session.py`, `ml_warmup.py`, `app.py`, `enrolment.py`, `ui/bridge.py`, `ui/main_window.py`, `ui/models.py`, `ui/session_screen.py`, `ui/transcript.py`); slice B tests (11 files); slice C docs (threat model, data-flow map, design system, AGENTS.md)

#### Findings
- **PR-LOW-A01** (LOW, docs-only, `desktop/src/scribe_desktop/ui/models.py:212`): The deferred-transcription message guarantees recording is unaffected even when warm-up imports still overlap capture after the timeout. — Evidence: “The recording is not affected”; `ml_warmup.py:122` releases Start solely when elapsed time reaches the bound, and its lines 23–26 acknowledge “the one remaining overlap” and possible failure. Recommendation: Fix-now — Remove the unconditional reassurance; state only that live transcription is off and transcription will be attempted at Finish. /fix decision: Applied (leg i5-x3) — the line is now "Live transcription is off for this recording - Clinic Scribe was still getting ready; transcribing after the recording instead.", in the C8 fallback lines' words. The comment above it says such a Start exists only after the 60 s hold. The design system says it promises nothing about the recording.
- **PR-LOW-B01** (LOW, test-harness, `desktop/tests/test_live_session.py:803`): The slow-load test does not prove capture progresses while model loading is blocked; queued audio could drain only after release and still pass. — Evidence: `_feed(...)`, `time.sleep(0.05)` and state assertions precede `gate.set()`, but transcription is checked only afterwards. Recommendation: Fix-now — assert all five chunks reach encrypted storage while the load gate remains closed, using bounded synchronization. /fix decision: Applied (leg i5-x3) — the test unwraps the session key and polls `iter_chunks(audio.enc)` (`_wait`, bounded at 5 s; `_write_record` flushes every record, and a partial tail ends the iteration cleanly) until all five chunks are stored. It then asserts the gate is still closed and that the stored chunks equal the fed PCM. The `time.sleep(0.05)` is gone.
- **PR-LOW-B02** (LOW, test-harness, `desktop/tests/test_integration_no_sockets.py:455`): The child can announce READY with warm-up still running, allowing the test to pass without reaching the claimed post-warm-up state. — Evidence: `"warmup.wait(30)\n"` ignores its result before `"print('READY', os.getpid(), flush=True)\n"`; the parent then polls five times and kills the child. Recommendation: Fix-now — require successful completion of the bounded wait before emitting READY. /fix decision: Applied (leg i5-x3) — the child prints `READY <pid> warmup:<wait result>`, and the parent asserts `warmup:True` before the socket checks. A failed warm-up also counts as finished; without the ML stack it fails fast, so CI is unaffected. The pattern of `test_scribe_app_with_the_chrome_link_open_has_no_sockets` is followed.
- **PR-LOW-C01** (LOW, docs-only, `docs/design-system.md:342`): The documented timeout starts at launch, conflicting with the warm-up-start boundary specified elsewhere. — Evidence: “bounded to a minute after launch”; `docs/security/threat-model.md:1021` says “from the warm-up’s start”, and `.cursor/plans/plan-installation.md:3068` specifies “60 s have passed since it began”. Recommendation: Fix-now — Say “60 seconds after the warm-up starts” so the documented clock boundary is consistent. /fix decision: Applied (leg i5-x3) — "bounded to 60 seconds after the loading starts (... measured from the warm-up's start, which is moments after launch)".
- Verification counts: slice A 2/1/1, slice B 2/2/0, slice C 6/1/5 (checked/confirmed/dropped)

#### LEG 1 verified tuples (executor stage-5 leg i5-x3, 2026-10-03T16:59:36+10:00)
- **PR-LOW-A01 — CONFIRMED.** `ui/models.py` `LIVE_TRANSCRIPT_NOT_READY_PLACEHOLDER` said "The recording is not affected". Since round 36 that line appears only for a Start admitted after the 60 s hold while the warm-up still imports beside capture, which is the one overlap `ml_warmup`'s docstring names. A promise there is unbacked.
  - Siblings: a search for "not affected" / "unaffected" / "never held back" / "transcript is made when you finish" across src, docs and AGENTS.md found no other copy in this diff; the other hits are unrelated, older lines.
  - The comment above the constant ("just after Clinic Scribe opens") was stale after round 36: such a Start comes only after the hold. Fixed with it.
  - `test_live_session.py`'s `test_a_factory_returning_none_records_without_a_worker` docstring ("returns None while the import warm-up runs") lacked the round-36 qualifier. Fixed.
- **PR-LOW-B01 — CONFIRMED.** The test fed five chunks, slept 50 ms and checked only state; storage was first read after `gate.set()` and Finish. Capture was therefore never shown to progress while the load was blocked. No siblings: the round-35 tests that block a load (`test_a_start_failure_stops_a_loading_worker_with_the_short_bound`) prove a different property.
- **PR-LOW-B02 — CONFIRMED.** `warmup.wait(30)`'s result was discarded before `print('READY', …)`. Siblings: the other READY children were checked.
  - `_PIPE_APP_CHILD` breaks on a deadline but puts the outcome on its READY line, and the parent asserts it — the pattern copied here.
  - `_APP_SERVER_CHILD` waits on nothing.
  - Neither is in this diff, and neither ignores a wait result.
- **PR-LOW-C01 — CONFIRMED.** The design system said "a minute after launch". The code (`holds_start`: `clock() - _started_at`, set in `start()`), the threat model ("from the warm-up's start") and the data-flow map ("from its start") measure from the warm-up's start.
  - Siblings: the `ml_warmup.START_HOLD_SECONDS` comment ("from when it began (just after launch)") and the `app.py` comment are consistent.
  - The plan's round-36 option (b) text ("at most 60 s after launch") is the historical option the practitioner chose. It is left as written; its as-built line under round 36 MED-001 says "since it began".
- Verification counts: 4 checked, 4 confirmed, 0 dropped.
- PEER-ROUND-38 RESULT: 4 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 4)
- Last reviewed: 2026-10-03

### Round 39 - 2026-10-03 - confirmation of round 38's fix, peer pass stage-5.p1 (composer-seat codex)

- Round status: Closed (0 pending); no findings.
- Source: codex `gpt-6-astra` (medium), read-only sandbox, `.cursor/loops/stage-5-peer-r39A.log` in the main checkout; peer_round 2 of cap 5
- Scope: `ui/models.py`, `test_live_session.py`, `test_integration_no_sockets.py`, `docs/design-system.md` (round 38's fix), `ml_warmup.py` for reference, round 38's block and C1–C10
- Verification counts: 4 claims checked, 4 confirmed (each round-38 finding closed as a class), 0 dropped
- PEER-ROUND-39-A RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0). Peer pass stage-5.p1 converged; trajectory 4 → 0.
- Last reviewed: 2026-10-03

### Round 40 - 2026-10-03 - Task P.3 live smoke on 0.1.0 and 0.1.1 (practitioner-observed)

- Round status: Closed (0 pending). 2 Applied by legs i5-x4/i5-x5 (reconciled by leg i5-x6). Closed 2026-10-03 by the composer: suite 4 — ruff clean, mypy clean (59 files), pytest 5912 passed / 9 skipped; an ISCC 6.7.3 compile of `packaging/scribe.iss` against a placeholder bundle, exit 0, "Successful compile"; codex round 43, 0 findings.
- Source: practitioner smoke (Task P.3), composer-observed from the Finish-page screenshots and the installed app's log
- Reviewer: composer `claude-opus-5-5`; observation by the practitioner

#### Findings
- **LOW-001** (LOW, behavioral, `packaging/scribe.iss` `CurPageChanged`): the Finish page shows only the first two paragraphs of the caption the script sets. — Evidence: every Finish page this run (0.1.0 install, 0.1.1 update, 0.1.1 reinstall) showed "Clinic Scribe is installed./updated." and the Chrome paragraph, but never the third paragraph "Open Clinic Scribe from the Start menu.", which `CurPageChanged` sets on all three. The likely cause: `WizardForm.FinishedLabel` keeps the height sized for the default text, and nothing re-sizes it after `Caption` changes (Inno's `WizardForm.AdjustLabelHeight`). Consequence: the appended warnings ("The clinic-only Chrome setting could not be removed…", the foreign-policy note) would be cut off too, and so would the second paragraph of "NOT completely installed" if it wraps past the label. Recommendation: Fix-now — resize the label after every caption change, and pin it in `test_installer_script.py`; confirm on the next build's Finish page. /fix decision: Applied (legs i5-x4/i5-x5): `CurPageChanged` ends with `WizardForm.AdjustLabelHeight(WizardForm.FinishedLabel);`, once and after the last caption change, so every branch is covered — the warnings and "NOT completely installed" included. No wording changed. Pinned by `test_installer_script.py::test_the_finish_label_is_resized_after_its_last_change`: exactly one call, after the last `Caption :=`, with nothing after it. Two checks remain open: the ISCC 6.7.3 compile check (the composer's), and the next build's Finish page (the practitioner's). The longest case — a fresh install plus a policy warning — could still exceed the page height, so check it at the practitioner's display scaling.
- **LOW-002** (LOW, behavioral, `desktop/src/scribe_desktop/session.py` `discard` / the Session tab's Discard): a Discard pressed while the live worker is mid-window waits up to `LIVE_STOP_TIMEOUT_SECONDS` (10 s) to stop it, with no feedback, then (by the custody rule, correctly) routes the session to `failed` and needs a second Discard. — Evidence: log `19:10:27,039 live_transcriber_stop_timeout … session_state=recording`, `19:10:27,041 … session_state=failed`, `19:10:30,713 … session_state=discarded`; the practitioner pressed Discard twice, and the first press looked like nothing happened. Recommendation: Fix-now (UX only; the custody rule stays) — show that Discard is waiting for live transcription to stop, and either retry the discard once the worker has stopped or say plainly "press Discard again"; check whether the join blocks the GUI thread. /fix decision: Applied (legs i5-x4/i5-x5). The custody rule is unchanged: the controller's `discard()` body is untouched except for the exception's type.
  - `session.LiveStopPendingError(SessionActivityError)` is now raised by `_refuse_uncleared_live`, so the PR-MED-017 refusal can be named.
  - With `live_transcription_attached`, `SessionScreen.on_discard` runs `controller.discard()` on a `TaskThread`, under `DISCARD_STOPPING_LIVE_LINE` ("Discarding - stopping live transcription first..."). Only the line string crosses threads, never the exception.
  - Without a live worker, Discard runs synchronously exactly as before.
  - While the wait runs:
    - every Session control is held (`on_pause` / `on_resume` / `on_finish` / `on_discard` / `on_start` / `start_linked`, the latter two before the consent tick is spent);
    - `is_busy` holds every Chrome command;
    - the main window refuses "Open for review" (`REVIEW_OPEN_DISCARDING_LINE`) and the close;
    - the state poll does not call the routed FAILED a device failure.
  - An outlasted stop shows `DISCARD_KEPT_LIVE_STOPPING_MESSAGE` ("Recording stopped, but live transcription did not stop in time, so nothing was deleted - the recording is kept. Press Discard again in a moment to delete it."). The Chrome bridge keeps its `failed` refusal through `on_refused`.
  - Chosen over an automatic retry: after the timeout the session is FAILED and kept, and the controller's `discard()` takes no session id. A retry would be a destructive step without a fresh confirmation, and would need session pinning the controller does not have.
  - Docs: `docs/design-system.md` (a new bullet), threat-model surface 11 CUSTODY, data-flow map flow 14, and the `AGENTS.md` pointer.
  - Tests:
    - `test_ui_screens.py`: the off-thread wait and the hold, the outlasted case and the second Discard, the backstop (`test_a_discard_ended_by_a_non_exception_still_releases_the_hold`), the refusal line, and the close refusal `[reconciled 2026-10-03 leg i5-x6: the backstop test is the in-job version's]`;
    - `test_ui_bridge.py`: the Chrome Discard is busy-held and reported `failed`;
    - `test_unreviewed_review.py`: "Open for review" is refused while discarding.
- Verification counts: 2 claims checked, 2 confirmed, 0 dropped

#### LEG 1 verified tuples (executor stage-5 legs i5-x4/i5-x5, 2026-10-03T20:27:07+10:00)
- **LOW-001 — CONFIRMED.** `CurPageChanged` assigned `WizardForm.FinishedLabel.Caption` up to three times and never re-sized the label. Inno sizes the label for its own text before `CurPageChanged(wpFinished)` runs, so text past that height was clipped.
  - `TWizardForm.AdjustLabelHeight(ALabel: TNewStaticText): Integer` is public to `[Code]`. The independent review confirmed this; the ISCC compile is the proof.
  - Nothing is laid out below the label (no `[Run]`, no restart choice), so no other control needs moving.
  - Siblings:
    - `FinishedLabel` is the only caption set at run time.
    - Every `MsgBox` is sized by Windows.
    - `PrepareToInstall`'s returned text is laid out by Inno on its Preparing page, not a caption the script sets.
    - The `[Tasks]` description is static.
    - None is this class.
- **LOW-002 — CONFIRMED.** `SessionScreen.on_discard` called `controller.discard()` on the GUI thread. That call stops and joins the live worker outside the controller lock for up to `transcription.LIVE_STOP_TIMEOUT_SECONDS` (10.0 s), so the window froze. An outlasted join raised the PR-MED-017 refusal, shown as "Discard failed: SessionActivityError: discard refused: …", and the next Discard needed two clicks again.
  - The log matches: `live_transcriber_stop_timeout` at RECORDING, then FAILED 2 ms later, then DISCARDED 3.7 s after.
  - Siblings that join the live worker:
    - Finish: seals only; its capture join is short.
    - The three Complete paths and Start's retirement: `_stop_live_locked`, a 1 s in-lock bound. At QUEUED the worker was already claimed, so no wait in practice.
    - The Transcript tab's Discard: QUEUED, worker claimed.
    - The Recovery tab's Discard: a folder, no live worker.
    - App close: refused while capturing; now also while discarding.
    - The Chrome Discard: the same slot, fixed with it.
  - Residue recorded, not fixed: "Open for review" of an outlasted, FAILED session retires it, which waits at most 1 s in the lock and is then refused with the existing "start refused: the live transcriber has not stopped yet…". This predates the fix and is bounded; the only issue is the word "start" (`_retire_locked`'s fixed operation name).
- Verification counts: 2 checked, 2 confirmed, 0 dropped.

### Round 41 - 2026-10-03 - round 40's fix diff (in-session /review-loop pass 1)

- Round status: Closed (0 pending). 6 LOW Applied; closes with the round 40 fix on the composer-run full desktop suite and the ISCC compile check.
- Source: executor stage-5 legs i5-x4/i5-x5 (in-session), plus one independent read-only subagent review (general-purpose), over the whole `git diff` against `33ed7cc` (14 files).
- Loop: /review-loop pass 1 of cap 3.

#### Findings
- **LOW-001** (LOW, behavioral, `ui/main_window.py` `closeEvent`): while a discard waits at RECORDING, a close said "Recording in progress - Finish or Discard the session before closing", asking for the Discard already under way. /fix decision: Applied. A check runs first and names the discard: "A recording is being discarded - wait for it to finish before closing." (`test_close_refused_while_a_discard_waits_and_says_so`).
- **LOW-002** (LOW, behavioral, `ui/session_screen.py` `on_start` / `start_linked`): a Start refused mid-discard (by the `_start` guard) had already cleared the desktop consent tick, unlike the round-36 rule. /fix decision: Applied. The guard moved ahead of the tick-clear in both; the `_start` guard was removed; the tick is pinned kept in the off-thread test.
- **LOW-003** (LOW, robustness, `ui/session_screen.py` `_begin_discard`): `TaskThread.run` catches only `Exception`. A non-`Exception` escaping it would emit neither signal and hold every control, every Chrome command and the close for good. /fix decision: Applied. The job itself catches any other `BaseException` after `except Exception` and returns the fixed line "Discard failed: <`CUSTODY_UNEXPECTED_REASON`>", so `succeeded` always fires and the hold always ends; `failed` stays connected to the same line as defence in depth. Swallowing it hides no real exit: a `KeyboardInterrupt` is only delivered to the main thread, and a `SystemExit` raised on a worker thread never ends the process. The bridge still hears the refusal through `on_refused` (`test_a_discard_ended_by_a_non_exception_still_releases_the_hold`). `[reconciled 2026-10-03 leg i5-x6]` This entry first described a `task.finished` backstop (test `test_a_discard_thread_that_ends_with_no_result_releases_the_hold`); leg i5-x4 replaced it at 20:27 with the in-job `except BaseException` above, and that is the final code.
- **LOW-004** (LOW, docs-only, `ui/main_window.py` `_on_session_started` docstring): it said the discard reservation is held synchronously on the GUI thread. /fix decision: Applied. It now says why no Start interleaves on both paths.
- **LOW-005** (LOW, wording, `ui/models.py` `CHROME_REFUSALS["busy"]`): "The app is still transcribing - wait for it to finish." was shown for a discard wait, and already for a draft write. /fix decision: Applied. It is now "The app is busy with a recording - wait for it to finish." (no test pinned the old text). The design system also names Start's `session_active` refusal.
- **LOW-006** (LOW, docs-only, `docs/design-system.md`, `docs/security/threat-model.md`): the line sits ABOVE the progress bar, not under it; and the threat model's long parenthetical broke the CUSTODY list. /fix decision: Applied. "Above"; the round-40 text is its own sentences after the list, and names the close and the backstop.
- Dropped (the independent review's checks):
  - a lambda slot running on the worker thread: PySide queues it, as `note.py` already relies on;
  - the TaskThread's parent: the same as the transcription task's;
  - the 2 s `finish()` join: the thread has already emitted its result;
  - a pause dropped mid-discard: capture stops at the start of `discard()`;
  - existing `pytest.raises(SessionActivityError, match=…)`: a subclass matches;
  - logs and audit records: no `exception_type_name` call is on this path;
  - a Chrome Discard that succeeded off the thread: the bridge's 500 ms tick publishes it;
  - two concurrent `on_discard`: guarded.
- Verification counts: 6 confirmed (2 in-session, 4 from the independent review), 0 downgraded; 8 candidates dropped.
- Last reviewed: 2026-10-03

### Round 42 - 2026-10-03 - round 41's fixes (in-session /review-loop pass 2)

- Round status: Closed (0 pending). 1 LOW Applied (fix-induced, docs-only); /review-loop CONVERGED at loop round 2 of cap 3 (no CRIT, HIGH or MED; triage-and-ship).
- Source: executor stage-5 leg i5-x5. The whole diff was re-read after the interrupted leg i5-x4, without trusting memory of it.

#### Findings
- **LOW-001** (LOW, docs-only, fix-induced, `docs/design-system.md`): round 41's rewrap left a line break mid-sentence in the new bullet. /fix decision: Applied (re-flowed).
- The six round-41 fixes were re-read in the code and confirmed: the close check is first; the tick is kept on both Start paths; the backstop always sends a result (the job catches any `BaseException` and returns the fixed line); the docstring; the `busy` text; the threat-model sentences. `[reconciled 2026-10-03 leg i5-x6]` This line first said "the backstop acts only when neither signal came", which described the superseded `task.finished` handler; leg i5-x6 re-read the final diff fresh and confirmed the in-job version.
- Verification counts: 1 confirmed, 0 dropped.
- Last reviewed: 2026-10-03

### Round 43 - 2026-10-03 - cross-family peer pass stage-5.p2 over the round 40 fixes (composer-seat codex)

- Round status: Closed (0 pending); no findings.
- Source: codex `gpt-6-astra` (medium), read-only sandbox, `.cursor/loops/stage-5-peer-r43{A,B}.log` in the main checkout; peer_round 1 of cap 5
- Scope: slice A — `session.py`, `ui/session_screen.py`, `ui/bridge.py`, `ui/main_window.py`, `ui/models.py`, `packaging/scribe.iss`, `test_installer_script.py`, `test_ui_screens.py`, `test_ui_bridge.py`, `test_unreviewed_review.py`; slice B — `docs/design-system.md`, the threat model, the data-flow map, `AGENTS.md`; plus rounds 40–42 and C1–C10. Slice A read each diff and every changed file in full, with searches across them.
- Verification counts: slice A 2/2/0; slice B 6/0/6 (docs internally consistent) — checked/confirmed/dropped
- PEER-ROUND-43 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0). Peer pass stage-5.p2 converged at its first round.
- Last reviewed: 2026-10-03
