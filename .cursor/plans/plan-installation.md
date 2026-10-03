# Feature Implementation Plan
**Feature:** installation
**Overall Progress:** `100%`

## Lifecycle State
- Completed — Follow-ups Retained

## Completion Status
- Completion timestamp: 2026-10-04
- Main implementation complete: Yes
- Ready for archive: No

## Plan Lineage
- Parent plan: None (PLAN.md Phase 7, installation half)
- Follow-up plans: plan-pilot.md (PLAN.md Phase 7, pilot half — not yet written; see Follow-Up Continuation Notes)

## Goal
Turn the developer-only app into an installed product on the clinic computer: PLAN.md Phase 7's installation bullets (L163–164), built so the pilot (plan-pilot.md) runs on an installed, hash-verified build. In plain terms:
- **Installed app.** A PyInstaller one-folder build of `scribe-app.exe` and `scribe-host.exe`, installed per machine by an Inno Setup installer into a folder only an admin can change. This retires the user-writable-venv launcher-hijack residue.
- **Models.** A separately shipped, SHA-256-verified model pack; the app never downloads anything.
- **What the installer writes.** The Chrome link in HKLM, the admin-only exclusions for live sessions and logs, and the HKLM crash-report exclusions.
- **Build of record.** Built by CI, with SHA-256s recorded and a build-provenance attestation. The build is unsigned for the pilot.
- **Developer build kept apart.** On this dual-use computer the developer build becomes a separate channel: its own data folder, Chrome link, extension and models. It refuses Cliniko writes unless you allow them.
- **Machine checks.** A hardware check that also times the language model, and an upgrade path for the next pilot build.
- **Install on this computer.** Verified from your own terminal, including a no-network check and a crash-recovery check on the installed build.

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Opus 5.5 (`claude-opus-5-5`); executor the same Opus-class model through `/execute-loop` (cross-family peer codex `gpt-6-astra`); no planner/executor tier gap. Every spike and the install itself (Phase 0, Phase P) are run by the PRACTITIONER from a normal terminal (MSIX lesson), never by an agent shell.

### Agreed Scope (Build Now)
All confirmed by the practitioner in the 2026-10-02 planning session (native Plan Mode, then this `/review-plan` pass).
- **Spikes first (Phase 0).** Retire the packaging risks before building on them:
  - the frozen host launched by Chrome from the install folder;
  - the frozen app's runtime: Qt, ctranslate2, onnxruntime, `llama_cpp`, keyring, SAPI;
  - Inno mechanics, and the CI runner having Inno;
  - the WeSpeaker licence;
  - Defender and Smart App Control behaviour on an unsigned build.
- **Developer/installed separation (D2, D3).** One channel switch in a new `install_layout.py`.
  - The installed app is the production channel and owns `%LOCALAPPDATA%\ClinikoScribe` as it stands today (your Past sessions, audit, voice profile, style and clinics carry over unchanged).
  - A source checkout is the dev channel. It gets `ClinikoScribe-dev` (data and models), its own Chrome host name, pipe, extension key and ID, and its own Credential Manager entries (separated by data folder, D3).
  - The two never run at once, through one shared single-instance guard.
  - The dev channel refuses Write draft to Cliniko unless a dev-only setting allows it (D4).
- **Frozen-runtime support.**
  - A benchmark worker entry in `app.main`.
  - A stdio fallback in the native host.
  - Registry readers that read HKCU and HKLM in both registry views and say which entry wins (and warn when an HKCU entry shadows the installed one).
  - The crash-report (WER) set chosen by channel.
  - A read-only check of the backup and snapshot exclusions.
  - Remedy lines that say "reinstall" in a frozen build.
- **Build and installer (D1, D5–D8).** A hashed build lock, `packaging/scribe.spec` and the committed `packaging/models-manifest.json`, then:
  - a model-pack builder;
  - `scripts/build-release.py` for local and spike builds;
  - a **CI release job** (practitioner Fix-now at the deferral gate, 2026-10-02): a Windows runner builds the app installer, audits the bundle, uploads it with its SHA-256 list and a build-provenance attestation;
  - `packaging/scribe.iss`: per-machine install; models copied and hash-checked inside the installer; HKLM Chrome link, WER and scoped backup/snapshot exclusions; an optional "clinic-only computer" Chrome policy; a running-process check; in-place upgrade; uninstall keeps your data;
  - `register-native-host.py` registers the dev channel only, with a friendly WinError 32 message;
  - `docs/release/pilot-builds.md` records each build.
- **Hardware check.** The Microphone tab's benchmark also times the language model's prose stage (CPU seconds per section) and reports whisper `medium`'s real-time factor. It runs in the frozen build.
- **An installed-build no-sockets check script**, run during a transcription and a prose run.
- **Security and project documents** updated as one class (Phase H), then the hardening stage.
- **Install on this computer** (Phase P), with the upgrade and rollback smoke on the next build.

### Deferred — Actionable Later
- **The pilot half of Phase 7: plan-pilot.md.**
  - Why deferred: the practitioner split Phase 7 in two (2026-10-02). The pilot takes weeks of clinic time and carries different risks.
  - Intended future outcome: shadow mode, the validation harness, the pilot governance documents, then the validation (≥50), shadow (10) and pilot (20 + 20) runs and the per-clinic routine-use gate.
  - Relevant files / subsystems: see Follow-Up Continuation Notes (the decided scope and the code facts already verified).
  - Dependencies / prerequisites: none to plan it. To RUN it on the installed build: this plan's Phase P. The harness can be built in parallel once this plan's Phase 1 has landed.
  - Recommended next action: `/review-plan` over the Follow-Up Continuation Notes to write `plan-pilot.md`.
  - Risk if deferred: blocked-work: routine clinical use waits on the pilot gate.
  - Revisit by: when this plan reaches Phase 3
  - [2026-10-04 reconciliation] Still valid — this plan is complete; the pilot plan is the next thing to write.
- **Enforced machine allow-list** (an admin-written list of the Cliniko hosts a computer may use).
  - Why deferred: practitioner decision 2026-10-02. This computer holds both clinics and the practitioner is its admin, so for the pilot an enforced list adds little and risks lock-out. PLAN.md L164 is met by procedure: Task P.1 records the authorised hosts, and the Status tab lists the connected ones.
  - Intended future outcome: a second, clinic-only computer (or a sold install) is bound to its authorised clinic(s).
  - Relevant files / subsystems: `clinics.py` (`ClinicRegistry`; NOT a filter on `records`, which would erase hidden clinics on the next save, but a separate authorised view); `ui/bridge.py:699-701` (Chrome's list, read from `records`); the readers at `ui/bridge.py:432,1068,1188`, `encounter.py:777,806,849,912,1027`, `ui/main_window.py:1501,1538,1779`; Validate's host from `/settings/public` (`clinics.py:681-701`).
  - Dependencies / prerequisites: this plan's install folder (an admin-only policy file location).
  - Recommended next action: plan it with the second computer.
  - Risk if deferred: security: a key for an unauthorised Cliniko account could be added on this computer; the practitioner is its only user and admin.
  - Revisit by: before a second clinic computer is set up, or at commercialisation
- **Code signing.**
  - Why deferred: practitioner decision 2026-10-02 (D7). Two computers, installed by the practitioner; integrity comes from the CI attestation plus recorded SHA-256s.
  - Intended future outcome: a signed installer and executables (removes the SmartScreen warning and Smart App Control blocks).
  - Relevant files / subsystems: `packaging/scribe.iss`, the CI release job.
  - Dependencies / prerequisites: a signing certificate or cloud signing service.
  - Recommended next action: buy one at commercialisation, or immediately if Smart App Control is on for a target computer (Task 0.5).
  - Risk if deferred: security: an unsigned build is checked only by hash and attestation, which the practitioner must actually run each time.
  - Revisit by: commercialisation, or a target computer with Smart App Control on
- **Past-sessions backup and restore** (carried from the privacy-professional-controls plan, not owned here).
  - Why deferred: a feature of its own. This plan only keeps it possible: the exclusions leave Past sessions and audit backup-eligible (D6).
  - Risk if deferred: correctness: a lost disk loses every kept transcript (unchanged).
  - Revisit by: before commercialisation, or before Past sessions is relied on as part of the health record

### Excluded — Revisit Only If Needed
- **Chrome Web Store publication.**
  - Why excluded: the Web Store assigns its own extension ID (`extension/KEY.md`) and is a commercial step. The installed extension is loaded unpacked from the install folder with the pinned key, so the ID stays the same.
  - When to revisit: commercialisation.
  - Relevant files / subsystems: `extension/src/manifest.ts:19`, `identity.py:15`.
- **Defender exclusions for the app.**
  - Why excluded: they would weaken the machine's protection. A false positive is handled by Task 0.5's scan and, if needed, signing.
  - When to revisit: never as an exclusion. A recurring false positive is a trigger for signing.
- **A per-user Chrome-link block on this computer.**
  - Why excluded: practitioner decision 2026-10-02 (D3 + the Chrome-policy answer). It would also stop Claude in Chrome, the Codex extension and the dev channel here. The installer offers the policy for a clinic-only computer only; here the Status tab warns on an HKCU shadow and the threat model names the residue.
  - When to revisit: if this computer stops being a development machine.
- **Shipping whisper `small`.**
  - Why excluded: `resolve_whisper_model` uses `small` only when `medium` is missing (`transcription.py` ~142), and the pack always holds `medium`.
  - When to revisit: if P.2's hardware check shows `medium` cannot keep up (then a model choice setting plus `small` in the pack).

### Accepted Assumptions — Revalidate Later
- **The practitioner's Windows login is an administrator.** The installer elevates in the same account, so nothing per-user lands in another profile; even so, the installer writes nothing per-user (Critical Constraint C3).
  - Why accepted for now: a single-practitioner computer.
  - Risk if assumption becomes false: a standard user elevating with separate admin credentials still installs correctly, because every write is HKLM, Program Files or `$UserProfile$`-relative (C3).
  - Trigger for revisit: a second computer with separate admin credentials.
  - Recommended next action: none; Task P.1 records which case applied.
- **The Windows backup and snapshot exclusions are best-effort.** `FilesNotToBackup` is honoured by Windows Server Backup / wbadmin, partly by deleting files at restore. `FilesNotToSnapshot` is best-effort and not applied to `vssadmin` snapshots or Previous Versions (Microsoft Learn, External Findings).
  - Why accepted for now: no stronger per-folder control exists for a local app; session data is already encrypted at rest and crypto-deleted.
  - Risk if assumption becomes false: an encrypted session copy survives in a snapshot. It is protected by DPAPI and a deleted key only if the snapshot did not also capture `key.dpapi`.
  - Trigger for revisit: commercialisation.
  - Recommended next action: H.1 states the limit exactly (claim-outruns-structure lesson).
- **Program Files works for the native host.** The Phase-1 "no spaces" failure is believed to come from the old `.bat`/venv launcher, not Chrome.
  - Why accepted for now: Task 0.2 tests it before anything depends on it. `[decision]` D-I1 picks the location from that result.
  - Risk if assumption becomes false: the fallback `C:\ClinikoScribe`, with an explicit admin-only ACL.
  - Trigger for revisit: Task 0.2's result.

### Key Design Decisions
See `## Design Decisions` (D1–D12). Headlines:
- the channel comes from `sys.frozen`, but the production names stay fixed constants;
- models ship as a separate pack checked inside the installer;
- the exclusions are scoped to `sessions\` and `logs\`;
- the dev channel's write guard;
- the CI release with attestation;
- the separate dev Chrome profile and the shared single-instance guard.

## Key Findings

Code baseline: `main` @ `7849dc4`, verified 2026-10-02 by three critique lenses and the composer. Paths are under `desktop/src/scribe_desktop/` unless stated.

### Files / Symbols Involved
**Data-folder builders (Task 1.2 repoints every one to `install_layout.data_root()`):**

| Builder | Location | Note |
|---|---|---|
| `exclusions.app_data_root(layer)` | `exclusions.py:219-223` | reads `LOCALAPPDATA` through the `WindowsLayer` seam, not `os.environ`; `APP_FOLDER_NAME` constant at :82 |
| `app.py` lock path | `app.py:251-252` | |
| `clinics.py` | `:334-335` | `clinics.json` |
| `session_store.py` | `:245` | |
| `audit.py` | `:145` | |
| `logging_setup.py` | `:468` | |
| `note_config.default_config_root` | `:910-913` | |
| `past_sessions.py` | `:144` | |
| `practitioner_profile.py` | `:275`, `:282` | |
| `benchmark.default_models_root` | `:142-146` | models root; RAISES when `LOCALAPPDATA` is unset (no home fallback), pinned by `tests/test_language_model_runtime.py:722` |
| `scripts/register-native-host.py` `INSTALL_DIR` | `:64` | pinned literally by `tests/test_display_name.py:64` |

Non-path `ClinikoScribe` literals that are NOT data-folder builders (a grep test must allow-list them by name): `pipe_server.py:89` `PIPE_PREFIX`, `pipe_client.py:308` (`ClinikoScribe-unknown`), `app.py:124` (mutex), `secure_storage.py:23` (keyring service prefix), and the DPAPI key descriptions `session_store.py:601`, `audit.py:101`, `past_sessions.py:111`, `practitioner_profile.py:105,111`.

**Model roots (Tasks 1.1–1.2):**
- Root resolution: `speech.py:248-249`, `transcription.py:905-906`, `speaker_embedding.py:243-244`, `language_model.py:131-132`. `language_model` refuses UNC paths and re-verifies the GGUF digest at every load; whisper and silero are NOT re-verified at load.
- Other callers of `default_models_root`: `ui/microphone.py:25,49` (`run_all(default_models_root())`), `benchmark.py:413`, `scripts/setup-models.py:104,181`.

**"Run scripts/…" remedy strings (Task 1.7):**
- Models:
  - `ui/models.py:2772,2778,2830,3014,3482,3494`
  - `ui/practitioner.py:768,773`
  - `speech.py:182`
  - `transcription.py:989`
  - `speaker_embedding.py:290,304`
  - `language_model.py:251-270`
  - `benchmark.py:358`
- Registration:
  - `exclusions.py:98-99` (`WER_NOT_EXCLUDED`)
  - `ui/main_window.py:247`
- Tests pinning the wording:
  - `test_speaker_embedding.py:289,459,568`
  - `test_speech.py:323`
  - `test_transcription.py:976`
  - `test_language_model_runtime.py:452`
  - `test_ui_models.py:376-379,447,454,543`

**Identity (Tasks 1.3–1.5):**
- `HOST_NAME` is defined at `protocol.py:59` and re-exported by `identity.py:13`. `identity.py` also holds `EXTENSION_ID` (15), `EXPECTED_ORIGIN` (16) and `REGISTRY_KEY` (17).
- Consumers:
  - `native_host.py:70,114,537`
  - `status.py:14`
  - `ui/main_window.py:87,234`
  - `scripts/register-native-host.py:59-60,65,82,160-195`
  - `tests/test_native_host.py:14`
  - `tests/test_integration_no_sockets.py:87`
- Pins that must stay on PRODUCTION values:
  - `protocol/fixtures/meta.json:4` (`host_name`), checked by `tests/test_protocol.py:58`
  - `tests/test_display_name.py:55-62` (service prefix, every DPAPI description, `PIPE_PREFIX`, `HOST_NAME`)
  - `extension` `scaffold.test.ts:9`, `manifest.test.ts:64-65` (key → `mbmh…`)
  - `test/chrome-fake.ts:96`
- Extension side:
  - `HOST_NAME` const at `extension/src/protocol.ts:17`, used by `connection.ts:164`
  - key at `extension/src/manifest.ts:19`
  - `vite.config.ts` has no mode handling
  - `scripts/generate-extension-key.py:29` hard-codes `key.pem` (gitignored private key; only the PUBLIC key is committed in `manifest.ts`)
- Pipe: `PIPE_PREFIX` `pipe_server.py:89`, `pipe_name` `:176`. Pinned by `tests/test_pipe_server.py:299,685` and `test_status_and_app.py:341`.
- Single instance: mutex `Global\ClinikoScribe-app-<user>` at `app.py:111-124` (user-only DACL); the real exclusion is the `app.lock` file (`app.py:247-252,312-335`).
- Keyring: service `ClinikoScribe/<clinic_id>` (`secure_storage.py:23,39`), with random clinic ids. Used only by `clinics.py:479` and the self-test (`status.py:69-73`).
- DPAPI key descriptions are CHECKED on unwrap: `session_store.py:622-639`, `audit.py:990`, `past_sessions.py:316`.

**Frozen-runtime touch points (Phase 2):**
- `app.main`:
  - exception hooks installed at `app.py:542`
  - `apply_offline_env` / `assert_offline_env`
  - `QApplication([])` at `:549`
  - `acquire_instance_exclusion()` at `:554`
- `benchmark.run_all` (`:348-399`):
  - spawns `[sys.executable, "-m", "scribe_desktop.benchmark", "--single", <name>, "--models-root", …, "--audio", …, "--audio-seconds", …]` with `env = os.environ | OFFLINE_ENV | {_WORKER_ENV: "1"}` (`:366-381`)
  - parses the child's stdout as JSON (`:397-398`)
  - `main` refuses `--single` unless `_WORKER_ENV == "1"` (`:416`)
- `native_host.main` (`:560-575`): `verify_origin`, then `set_binary_stdio()` (`framing.py:54-55`, `msvcrt.setmode(sys.stdin.fileno())`), then `run_host(sys.stdin.buffer, sys.stdout.buffer, …)`. There is no guard for `sys.stdin is None`. Logging already tolerates a missing stderr (`logging_setup.py:511-512`).
- Registry readers that read HKCU only:
  - `status.read_registration_status` (`status.py:35`)
  - `native_host._log_registration_paths` (`:540`)
  - `exclusions.check_wer` (`:201`, `:288-304`)
- `WindowsLayer` Protocol: `exclusions.py:132-161`; `Win32WindowsLayer`: `:174`; `startup_exclusions`: `:338-365`.
- `WER_EXCLUDED_APPLICATIONS` (`exclusions.py:66-72`) = `pythonw.exe`, `scribe-app.exe`, `scribe-host.exe`.
- conftest `_no_real_windows_layer` (`tests/conftest.py:22-41`) makes the real layer raise in tests.

**Draft write (Task 1.6):**
- `WriteRefusalName` Literal at `draft_write.py:1054-1065`.
- `refuse_before_read(note, record, note_identity)` at `:1118`; callers `ui/main_window.py:1874` and `draft_write.py:1180` (inside `prepare_write`).
- `prepare_write` gets consent and context from the session (`main_window.py:1983-1987`).
- Pre-click button state: `ui/models.write_control` (`:669-693`; `mock_note` checked at `:685`). Wording: `ui/models.write_refusal_line`.
- Pins:
  - `tests/test_write_lines.py:70,427`
  - `tests/test_draft_write.py:1649,1666`
  - `tests/test_audit.py:204-208`
- The audit `_CODE_PATTERN` (`audit.py:118`, `^[a-z][a-z0-9_]{0,47}$`) already admits a new refusal name.

**Version:** `0.1.0` in four places: `desktop/pyproject.toml:7`, `scribe_desktop/__init__.py:3`, `extension/src/manifest.ts:22`, `extension/package.json:4`. The only existing check is `tests/test_smoke.py:7`.

**Models and pins (Task 3.3):**
- `scripts/setup-models.py`:
  - silero v5.1.2 SHA-256 at `:69-74`;
  - whisper repos pinned to Hugging Face commit only, with no per-file hashes (`:79-96`);
  - `--only` at `:580-581`.
- Speaker model: `speaker_embedding.py:58-66` (26,530,309 B).
- Language model: `language_model.py:57-87` (2,497,281,120 B; the runtime wheel pin `LANGUAGE_RUNTIME_*`, pinned by `tests/test_language_model_runtime.py`).
- `desktop/requirements-ml-prose.txt`: `llama_cpp_python-0.3.35-py3-none-win_amd64.whl` with a sha256 (`py3-none`, so any interpreter works).

**Packaging today:** none. There is no PyInstaller, Inno, WiX or `.spec` file. `.github/workflows/ci.yml` has a Windows desktop matrix (3.12, 3.14) and an Ubuntu extension job, with no artifact step.

### Codebase Integration Notes
- **Host-state seams.** Every new check that reads the host goes through an injected seam, tested in BOTH directions (lessons: "a test that reads real host state…"):
  - `install_layout.is_frozen()`;
  - the registry views;
  - SAPI voices;
  - model presence.

  Registry and attribute calls go through `WindowsLayer` (the conftest sentinel fails a test that touches the real one).
- **Read the environment on every call.** About 30 tests `monkeypatch.setenv("LOCALAPPDATA", tmp)`, and `test_integration_no_sockets.py:285` passes it to a subprocess, so `data_root()` must re-read the environment each time and never cache it.
- **Settings files** follow `PastSessionSettings` (`past_sessions.py:929-1023`): `extra="forbid"`, a size cap, missing file means defaults, a corrupt file raises. They are written through `note_config._write_config_file` (`:1673`) under `note_config.default_config_root()`.
- **Agent shells are MSIX-virtualized** (`docs/lessons.md`): `%LOCALAPPDATA%` and HKCU writes and reads from an agent shell prove nothing. Every registry, ACL, install, Chrome and model-folder check is a practitioner step from a normal terminal or Explorer.
- **`register-native-host.py` fails with WinError 32 while Chrome holds the host exe** (lessons, 2026-10-02). The installer's running-process check and Task 3.7 both handle it.
- **The `sys.executable` launcher lesson** (2026-09-28) does not apply to a frozen build, because `scribe-app.exe` is the real process. It still applies to every dev-channel test that spawns a child.
- **Shared helpers for this plan:**
  - `install_layout` (channel, roots, frozen detection);
  - `exclusions.WindowsLayer` (every registry or attribute read);
  - `benchmark.apply_offline_env` / `assert_offline_env` (`:114`, `:123`; also used by `speaker_eval`);
  - `note_config._write_config_file`;
  - the models manifest (one source for the installer's hash check, the build's bundle audit and the pin cross-check test).

### External / API Findings
Checked by the critique lens on 2026-10-02. Each one still needs Phase 0's live confirmation.
- **Chrome native messaging on Windows.**
  - The host is looked up in the registry in both the 32-bit and 64-bit views. The Chromium-based Edge docs state HKCU is checked before HKLM, so a per-user entry shadows a machine entry.
  - Native-host paths under `C:\Program Files` are common in practice. The Phase-1 failure coincided with the old `.bat` launcher (`LEGACY_ARTIFACTS`).
  - Sources: developer.chrome.com native-messaging; learn.microsoft.com Edge native-messaging.
- **`NativeMessagingUserLevelHosts=0`** (HKLM Chrome policy) blocks every per-user native host. Like any HKLM Chrome policy, it makes Chrome show "managed by your organization".
- **Backup and snapshot exclusions** (Microsoft Learn "Registry Keys and Values for Backup and Restore", "Excluding Files from Shadow Copies").
  - `FilesNotToBackup` is honoured by Windows Server Backup and wbadmin, in part by deleting matching files at restore; System Restore does not honour it.
  - `FilesNotToSnapshot` (`REG_MULTI_SZ`, `$UserProfile$`-relative patterns such as `$UserProfile$\AppData\Local\ClinikoScribe\sessions\* /s`) is best-effort and not applied to `vssadmin` snapshots or Previous Versions.
- **Inno Setup 6** has no slice-size limit. `GetSHA256OfFile` is available in `[Code]`. `PrivilegesRequired=admin` gives a per-machine install.
- **Unsigned PyInstaller builds** draw frequent Defender false positives; building the bootloader from source reduces them. Smart App Control, on a fresh Windows 11 install, blocks unsigned executables and DLLs outright, and turning it off cannot be undone without a reset.
- **Python 3.14 support** in PyInstaller and its hooks for `llama_cpp` and `ctranslate2` are UNVERIFIED. Task 0.1 proves them; the fallback is 3.12, the CI floor.
- **GitHub's `actions/attest-build-provenance`** produces a Sigstore attestation that `gh attestation verify <file> --repo eliemokbel3-hub/Recording-clinic-software` checks. Artifact attestations need a PUBLIC repository, or GitHub Enterprise Cloud for a private one; this repository was checked PUBLIC on 2026-10-03 (round 23; Task 3.6 step 0 re-checks it before the pins). Whether Inno Setup is preinstalled on `windows-latest` is UNVERIFIED (Task 0.3); otherwise the job installs a pinned version.

## Planned Workflow Summary

### Flow 1 — Making a pilot build
1. Push to `main` and run the `release` workflow (manual dispatch).
2. A Windows runner installs the hashed build lock and the prose wheel, runs PyInstaller, audits the bundle (no `Qt6Network`/`QtWebSockets`, the offline variables set in the frozen app, a Defender scan where the runner allows it), builds the extension in release mode, runs ISCC, and uploads `ClinikoScribe-<version>-setup.exe` plus `SHA256SUMS.txt` with a build-provenance attestation.
3. The model pack is built ONCE by the practitioner (`scripts/build-release.py --model-pack`, from a normal terminal) and re-built only when a pin changes. Its manifest is committed, so CI compiles the expected hashes into the installer.
4. `docs/release/pilot-builds.md` records the version, the commit and every SHA-256.

### Flow 2 — Installing on a computer
1. Close Clinic Scribe and Chrome completely.
2. Verify the installer: `gh attestation verify` and `Get-FileHash` against `SHA256SUMS.txt`.
3. Put the model pack folder next to `setup.exe` and run `setup.exe` (one admin approval). It:
   - checks for running Clinic Scribe or Chrome processes;
   - copies the app into the install folder (`[decision]` D-I1);
   - copies the models into `{app}\models`, checking every file's SHA-256 against the manifest, and stops with a message on any mismatch;
   - writes the HKLM Chrome link, the HKLM WER exclusions and the scoped backup/snapshot exclusions;
   - optionally sets the clinic-only Chrome policy.
4. Finish page: "In Chrome, remove any older Clinic Scribe Companion, Load unpacked `{app}\extension`, then fully restart Chrome." On an upgrade the wording is "Reload the extension, then fully restart Chrome".
5. Launch Clinic Scribe from the Start menu as the logged-in user. The installer never launches it (D8). The Status tab shows registration (the winning entry), WER and backup lines; the Microphone tab runs the hardware check.

### Flow 3 — Developing on the same computer
- A source checkout is the dev channel:
  - data and models in `%LOCALAPPDATA%\ClinikoScribe-dev`;
  - host `com.scribe.cliniko_host_dev`, registered per user by `register-native-host.py`;
  - the dev extension (its own key and ID), loaded only in a SEPARATE Chrome profile.
- The dev app and the installed app never run at once (one shared guard).
- Dev refuses Write draft to Cliniko unless its dev-only "Allow Cliniko writes from this developer build" setting is ticked.

### Flow 4 — Upgrading to the next pilot build
- Flow 1, then Flow 2 over the existing install: same AppId, in place, without the model pack when its manifest is unchanged; the installer re-checks the installed models.
- Uninstall removes the app and the HKLM keys but never `%LOCALAPPDATA%\ClinikoScribe` (7-year retention), and says so.
- Rollback = install the previous build's `setup.exe` over the newer one. This plan changes no persisted schema, so a rollback reads all data; plan-pilot owns the compatibility tests for its schema changes.

## Design Decisions
- **D1 — PyInstaller one-folder plus Inno Setup, per-machine.**
  - The build is one COLLECT with two windowed EXEs (`scribe-app.exe`, `scribe-host.exe`), no UPX and a bootloader built from source.
  - It installs into an admin-only folder: `C:\Program Files\ClinikoScribe` if Task 0.2 passes, else `C:\ClinikoScribe` with inheritance removed and an explicit ACL (Administrators/SYSTEM full, Users read and execute). `[decision]` D-I1 records which.
  - Why: an admin-only folder retires the user-writable-venv launcher-hijack residue (threat-model ~L74).
  - Alternatives rejected: a scripted per-user setup (venv stays writable, no admin exclusions); an MSI built with WiX (heavier for two computers).
- **D2 — The channel comes from `sys.frozen`; production names stay fixed constants.**
  - `install_layout.channel()` returns `"production"` when frozen and `"dev"` otherwise, through the injectable `is_frozen()`.
  - Every existing production constant keeps its name and value (`HOST_NAME`, `EXTENSION_ID`, `EXPECTED_ORIGIN`, `REGISTRY_KEY`, `PIPE_PREFIX`, `APP_FOLDER_NAME`, the keyring prefix, every DPAPI description). Per-channel ACCESSORS sit beside them, and only those accessors are channel-aware.
  - A conftest autouse fixture pins the channel to production, so existing tests and pins test what ships; dedicated tests inject the dev channel.
  - Alternatives rejected:
    - constants that change by channel (breaks `protocol/fixtures/meta.json`, `test_display_name.py`, `manifest.test.ts`, and would make every source-run test the dev channel);
    - an environment variable (the project keeps no env vars).
- **D3 — The dev channel's scope.**
  - Separate:
    - data and models root `ClinikoScribe-dev`;
    - host name `com.scribe.cliniko_host_dev`, registered in HKCU only;
    - pipe `ClinikoScribe-dev-<SID>`;
    - the dev extension, built with `--mode dev` from a committed dev PUBLIC key (private key gitignored) and loaded only in a separate Chrome profile.
  - NOT separate:
    - the keyring service prefix — clinic ids are random per data folder, so separate folders already separate the entries, and production keeps today's entries with no mapping;
    - the DPAPI descriptions — checked on unwrap, so changing them would lock out existing data.
  - Shared:
    - ONE per-user single-instance guard across both channels, so the installed and dev apps never run at once. This also prevents a Ctrl+Shift+F9 hotkey clash and keeps a single owner of the pipe namespace.
  - Why: practitioner decisions D6 (no per-user-link block here) and D7 (separate dev folder) from the native plan. A dev HKCU entry under its OWN host name never shadows the production HKLM entry.
  - Alternative rejected: one shared Chrome link (the dev HKCU registration would shadow the installed host).
- **D4 — The dev channel's Cliniko write guard.**
  - In the dev channel, `refuse_before_read` and `ui/models.write_control` refuse with `dev_build_writes_off` unless `config\dev.json` (dev data root only, `extra="forbid"`, `allow_cliniko_writes: bool`, default false) allows it.
  - The setting is a dev-only Status-tab checkbox. A production build never reads the file, and the name never applies there.
  - Reads and verification still work, so the safeguards can be smoke-tested without writing.
    - AS BUILT (Phase 1 review round 10, LOW-004): "reads and verification" are the note verification when a treatment note opens or a linked recording is reopened, the encounter checks it feeds, and the Clinics tab's Validate. The Write click's own hop-1 read (`read_for_write`) and the pre-write checks in `prepare_write` (template match, finalised draft, the open-record reconcile) run only when writes are allowed, because the guard sits in `refuse_before_read` as this decision's first bullet says, so a refused click makes no request. Two consequences follow. To smoke-test those pre-write checks, the practitioner ticks the box against a disposable draft. And an attempt left open, after which the box is unticked, stays open with the `write_uncertain`-prefixed line until the box is ticked again (the next click then reconciles it before any PATCH).
  - Why: practitioner decision 2026-10-02.
  - Alternatives rejected: a Cliniko trial account (depends on Cliniko); no guard.
- **D5 — The models ship as a separate, verified pack.**
  - A folder `ClinikoScribe-models-<manifest-sha8>\` sits next to `setup.exe`. The installer copies it to `{app}\models` and checks every file against `packaging/models-manifest.json`, compiled into the installer as `[Code]` constants and checked with `GetSHA256OfFile`.
  - Frozen `models_root()` returns `{app}\models` (read-only to users).
  - Contents: silero, whisper `medium`, the speaker model (subject to `[decision]` D-I2) and the language model.
  - Why: the practitioner's choice 2026-10-02. It matches PLAN.md's "installed separately" and the 2026-09-16 "never downloaded in-app" decision, and pilot fixes re-ship only a small installer.
  - Alternative rejected: one disk-spanned installer of about 3 GB.
- **D6 — The backup and snapshot exclusions cover live sessions and logs only.**
  - `FilesNotToSnapshot` and `FilesNotToBackup` for `ClinikoScribe\sessions\*` and `ClinikoScribe\logs\*`, in the profile-independent `$UserProfile$` form if Task 0.3 confirms it; otherwise `%LOCALAPPDATA%`-expanded for the installing user, named as a residue.
  - Past sessions, audit, profile and style stay backup-eligible.
  - Why: practitioner choice 2026-10-02. Those stores are 7-year records whose only copy is this disk while backup/restore is deferred.
  - Alternative rejected: excluding the whole data folder.
- **D7 — Unsigned build; CI artifact with attestation as the build of record.**
  - Why: practitioner decisions 2026-10-02 (unsigned; then Fix-now on CI building the installer). The attestation gives provenance an unsigned file otherwise lacks.
  - `scripts/build-release.py` builds the same thing locally, for spikes and the model pack.
- **D8 — The installer writes nothing per-user and never runs the app elevated.**
  - The model check is in `[Code]`. The HKLM WER exclusions go under `HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting\ExcludedApplications` (`scribe-app.exe`, `scribe-host.exe`).
  - The installer NEVER launches the app: there is no Finish-page "Launch" option. Inno's `runasoriginaluser` has no unelevated token to restore when Setup was started already elevated (Run as administrator, or an elevated terminal), so it cannot guarantee a non-elevated launch (round 1 PR-MED-001). The Finish page says "Open Clinic Scribe from the Start menu".
  - `SetupLogging=no`.
  - The clinic-only checkbox writes `HKLM\SOFTWARE\Policies\Google\Chrome\NativeMessagingUserLevelHosts=0` (DWORD). It is off by default, and its text says it shows "managed by your organization" and blocks every per-user Chrome add-on that talks to a program.
  - Why: an elevated installer may run as a different account (the critique lens). Running the app elevated would create admin-owned files in the data folder.
- **D9 — Registry readers follow Chrome's lookup order.**
  - `status.read_registration_status`, `native_host._log_registration_paths` and a new layer method read the host name's entry in HKCU then HKLM, each in both registry views. They report the WINNING entry and every other entry found.
  - In a frozen build, any HKCU entry for the production host name is a Status warning ("a per-user Chrome link overrides the installed one").
- **D10 — The WER set follows the channel.**
  - Frozen: `scribe-app.exe` and `scribe-host.exe`, checked in HKLM, with HKCU accepted.
  - Dev: today's three (`pythonw.exe` included) in HKCU.
  - `check_backup_exclusions` reads the two HKLM values through `WindowsLayer` and only ever warns.
- **D11 — The hardware check adds the prose stage.**
  - The Microphone tab's benchmark also times `ui/models.build_prose_stage` in-process on fixed, non-clinical lines (CPU seconds per section) beside whisper's real-time factor. The frozen build runs whisper timing through a `scribe-app.exe --benchmark-worker` entry dispatched in `app.main` before `QApplication`.
  - The margin verdict extends `threshold_report`.
  - Why: PLAN.md L204 ("the installer still benchmarks"), done after install rather than inside the elevated installer (D8).
  - AS-BUILT (round 22): the verdict uses WALL seconds per section, which is what the clinician waits for; CPU seconds are reported beside it, not judged. Accepted interpretation: CPU time understates a stage that waits on memory or a busy machine. A rendering in flight on the Note tab shares the model lock, so the check is run with none in flight (`docs/design-system.md`).
- **D12 — One version.**
  - `pyproject` is the source. `__init__.__version__`, `manifest.ts` and `package.json` are pinned equal by one test, and `build-release.py` / CI pass it to ISCC as `/DAppVersion=`.

## Schema / Data Changes
- **No change to any persisted schema**: audit, Past sessions, encounter, session files, clinics, profile and style are untouched. The installed app adopts `%LOCALAPPDATA%\ClinikoScribe` exactly as it is.
- **New, dev only:** `%LOCALAPPDATA%\ClinikoScribe-dev\` (the whole dev tree) and its `config\dev.json` (D4).
- **New, committed:** `packaging/models-manifest.json` (path, size and SHA-256 for every model file).
- **New, on the installed computer:** `{app}\models\` (read-only) and HKLM keys (D8, D6, D9). The dev models move from `ClinikoScribe\models` to `ClinikoScribe-dev\models` in a PRACTITIONER step (P.1, normal terminal). The old copy is removed only after the installed app's models verify.

## Config / Environment / Deployment Impact
- **Environment variables:** none added. The no-env-vars rule stands; the channel is `sys.frozen`.
- **New build-time dependencies:**
  - PyInstaller, in a hashed `desktop/requirements-build.txt` together with every runtime dependency and `sounddevice`;
  - Inno Setup 6, a pinned version on the CI runner and on the practitioner's machine for local builds;
  - `actions/attest-build-provenance`.
  - All are build-time only; nothing reaches the runtime besides the frozen dependencies already in use.
- **New CI workflow:** `.github/workflows/release.yml` (manual dispatch on `main`). It needs `permissions: id-token: write, attestations: write, contents: read`.
- **Registry (installer, HKLM):**
  - the native-host key for `com.scribe.cliniko_host` → `{app}\com.scribe.cliniko_host.json`;
  - WER `ExcludedApplications`;
  - `BackupRestore\FilesNotToBackup` and `FilesNotToSnapshot` values named `ClinikoScribe`;
  - optionally the Chrome policy.
  - Uninstall removes all of them except where noted in Task 3.4.
- **Ordering on this computer:** canonical in Task P.1. In short: remove today's HKCU production-name key BEFORE installing, and move the dev models only AFTER the installed app's models verify.
- **Release risks:**
  - an unsigned build drawing SmartScreen warnings, Defender false positives, or Smart App Control blocks (Task 0.5);
  - an HKCU shadow on this dual-use computer (D9 warning);
  - a model-pack mismatch, which fails closed at install.

## Critical Constraints
- **C1 — Offline contract unchanged.** The app never downloads anything and makes no connection except Cliniko's API, never at startup or idle. The installer makes no network connection. Network use at build time (CI, the model-pack fetch) is build-time only and is recorded in data-flow-map flow 9.
- **C2 — The production identities are unchanged:** host name, extension ID, origin, pipe prefix, data folder name, keyring prefix, every DPAPI key description and the mutex name. Existing data, keys and the Chrome link must keep working in the installed app (D2).
- **C3 — The installer writes nothing per-user and never runs the app elevated** (D8). Every write is HKLM, the install folder, or a `$UserProfile$`-relative exclusion pattern.
- **C4 — Uninstall and upgrade never delete or move `%LOCALAPPDATA%\ClinikoScribe`** (7-year retention, retention-schedule). Uninstall says the data stays.
- **C5 — The exclusions cover `sessions\` and `logs\` only** (D6). Every document states them as best-effort, exactly as External Findings describes; never as "excluded from backups".
- **C6 — Host-state reads go through seams,** tested in both directions. No test touches the real registry, `%LOCALAPPDATA%`, a real model file or a real Chrome; the conftest sentinels stay (the `Win32WindowsLayer` refusal, and since Task H.6 the models-root pin `pinned_models_root`, which only the resolver's own `real_models_root`-marked tests skip).
- **C7 — Checks from an agent shell never count** for registry, ACL, `%LOCALAPPDATA%`, install, Chrome or model-folder state (MSIX). They are practitioner steps with scripted on-screen wording to report.
- **C8 — The dev channel never reads or writes the production data folder or models.** The one exception is the shared single-instance guard (D3).
  - AS-BUILT (round 22): a second, one-time exception is the migration `scripts/register-native-host.py --unregister` (Task 3.7), which removes the old per-user production-name key and its two files in the production folder; it is run only as Phase P step 2 (AGENTS.md step 5, data-flow flows 5 and 24).
- **C9 — Documentation claims state only what the structure enforces,** with residues named, and are reconciled as a class: grep the whole doc surface for each sibling phrase (lessons: "claim outruns the enforcing structure", docs).
- **C10 — No Defender exclusions and no weakening of Smart App Control.** A blocked unsigned build is a signing trigger, never a security relaxation.

## Validation / Verification
**Baseline (gate dry-run, 2026-10-02, `main` @ `7849dc4`, composer-run):**
- `desktop/`:
  - `ruff check .` → All checks passed
  - `mypy` → no issues in 56 source files
  - `pytest -q` → 5301 passed, 9 skipped (197.8 s)
- `extension/`: `npm run qa` → exit 0, 12 test files, 306 tests passed.

These are the numbers every phase's suite run compares against. Expect growth only; a change in the skip count needs a reason.

**Per phase:**
- **Every code task:** `ruff check . && mypy && pytest` in `desktop/` (composer-run, `verify=composer`), plus `npm run qa` in `extension/` for Tasks 1.3 and 1.8.
- **Phase 1:** a grep test that finds no `ClinikoScribe` path builder outside `install_layout` (the non-path literals in Key Findings are allow-listed by name). Both channels are injected in the layout, identity, write-guard and guard tests. `npm run build -- --mode dev` and `--mode release` both pass, and `manifest.test.ts` covers both IDs.
- **Phase 3:**
  - `scripts/build-release.py --audit <dist>` passes on the spike build;
  - the models-manifest-versus-pins test passes;
  - the `.iss` text-pin test passes;
  - the `release` workflow runs green once, attests and uploads;
  - `gh attestation verify` passes on the downloaded installer (practitioner).
- **Phase P (practitioner, normal terminal):**
  - Every step in Task P.1 / P.2 / P.3, with the on-screen wording reported back.
  - The installed-build no-sockets check (Task 3.8) passes during a transcription and a prose run.
  - A kill-mid-recording, relaunch and recovery check passes.
  - A Start with Cliniko offline behaves as today (`unverified_offline`).

**Not re-validated here:**
- The cross-patient write-back suites. They are unchanged source tests; they stay in the suite, and H.1's docs cite them. PLAN.md L200 is satisfied by the suite run on every phase.
- AI quality. That belongs to plan-pilot.

## Deferred / Out of Scope
Canonical entries are in the Planning Extraction Summary:
- **Deferred:** plan-pilot, the enforced allow-list, signing, Past-sessions backup/restore.
- **Excluded:** Web Store, Defender exclusions, the per-user-link block on this computer, whisper `small`.

The pilot-half scope and its already-verified code facts are in Follow-Up Continuation Notes.

## Current State / Handoff Note
- Last completed step: **PLAN COMPLETE 2026-10-04 — Completed — Follow-ups Retained.** Every task 🟩 (40/40). Phase P on this computer: P.1 install and verify (0.1.0, 2026-10-03; step 14's old models folder removed 2026-10-04), P.2 hardware check, P.3 update 0.1.0 → 0.1.1, rollback, uninstall and reinstall; 0.1.2 (the round 40 fixes) installed and confirmed 2026-10-04. Builds of record in `docs/release/pilot-builds.md`. The main checkout fast-forwarded to `origin/main` (`32e7278`) and re-registered as the developer build (`verified : OK`). Review rounds 1–43 compacted 2026-10-04 into `findings-installation.md` (the plan keeps one digest per round).
- Current in-progress step: none — the /execute-loop run is closed.
- Immediate next action: the practitioner's first clinic day on 0.1.2 (from 2026-10-06); then the pilot plan from Follow-Up Continuation Notes (Plan Mode, then `/review-plan`). Retained items are listed under Retained Follow-Up Items.
- Open blockers / open questions: the Phase 0 MUST-PAUSE for practitioner runs is DISCHARGED (2026-10-02). None of the following blocks Phase 0's close; each is owned and has a recommendation.
  1. **Inno Setup licensing** `[practitioner]`. The local ISCC 6.7.3 prints **"Non-commercial use only"** (Task 0.3).
     - The plan currently ASSUMES Inno Setup is freely usable: Config / Deployment Impact lists it only as "a pinned version on the CI runner and on the practitioner's machine". No licence term is recorded, and PLAN.md has a commercial path.
     - Whether a clinician building an installer for their own practice counts as commercial use, and what a commercial licence would cost or require, is unchecked.
     - rec= before Task 3.4 / 3.6 ship any release installer, the composer runs one web-granted research leg on jrsoftware.org's current licence terms. The practitioner then decides: licence it, confirm it is not needed, or switch to an alternative. Phases 1–2 and the build work through Task 3.2 do not depend on it.
     - **Chosen (practitioner, 2026-10-03): continue WITHOUT buying a licence.** Research leg (composer, web, 2026-10-03): the licence file shipped with the installed 6.7.3 (`C:\Program Files (x86)\Inno Setup 6\license.txt`, line 13) and jrsoftware.org's `license.txt` both read "Permission is granted to anyone to use this software for any purpose, including commercial applications", on condition that copyright notices and the website address stay in binary redistributions, the origin is not misrepresented, and modified versions are marked. Separately, jrsoftware.org/isorder.php REQUESTS ("It is not strictly required") that commercial users — for-profit, annual revenue over USD 5,000, in-house-only use included — buy a licence (Single User about EUR 140 ex VAT via a reseller, perpetual, 2 years of updates). The practitioner declined the request. Keep: Inno's own notices in the compiled installer (ISCC adds them by default; do not strip them). Re-check the licence file whenever the pinned Inno version changes, since the terms are version-specific.
  2. **Task 3.6 Inno pin** `[decision, Task 3.6]`. CI images carry 6.7.1 (leg i0-x2); the practitioner's local build used 6.7.3.
     - rec= **pin 6.7.3 on both sides**:
       - CI installs that exact version from a SHA-256-checked installer and asserts `ISCC`'s version banner, rather than relying on the image's preinstalled copy, which images update weekly and which would drift anyway;
       - local builds keep the 6.7.3 already installed;
       - the `windows-2025` label stands.
     - This supersedes the leg i0-x2 recommendation of 6.7.1. Downgrading the practitioner's machine to 6.7.1 would also work, but it pins the build to whatever the image happens to carry.
     - Take it together with item 1, since a licence decision may change the version.
  3. **Frozen benchmark speed** `[practitioner run]`. The GUI benchmark through the frozen worker path gave medium RTF **1.27** (FAIL) ON BATTERY. The in-process spike check gave **0.482** on the same 53.2 s sample (Task 0.1). The cause — frozen worker, the benchmark's measurement, or battery — is NOT established. **RESOLVED 2026-10-02 (practitioner, on mains, recorded by the composer 2026-10-03):** frozen spike app medium RTF **0.676** (load 13.65 s, 53.2 s audio, peak 1494.6 MiB, 142 words, OK; live window 20.3 s per 30 s, keeps up) vs the everyday app **0.589** on the same sample — the 1.27 was battery throttling; the frozen build passes (< 1.00, within the 0.75 margin), about 15% slower than the everyday app with a slower first model load. `C:\scribe-spike` was then deleted.
     - rec= the PRACTITIONER, ON MAINS, before `C:\scribe-spike` is deleted, runs:
       - (a) the everyday app's Microphone-tab benchmark;
       - (b) the spike app's GUI benchmark from a scratch window (runbook 0.1 steps 14 and 18–19);
       - and reports both `medium RTF … load_s …` lines.
     - No D11 / Task 2.1 / 2.5 conclusion until then. P.2 on the installed app is the final reading.
  4. **D6 value form** `[recorded, confirm at review]`. Task 3.4 now names the `$UserProfile$` form for both keys (D6's primary branch). Its fallback, expanded for the installing user, is shown by Task 0.3 to bind to the ELEVATING account and to conflict with C3/D8.
     - rec= accept at Phase 3's review. Whether backup honours `$UserProfile$` in `FilesNotToBackup` remains a named C5 residue (not observable on Windows 11 Home).
  5. **Task 2.2's heading** says "the adaptation Task 0.2 proved". Task 0.2 found that Chrome GIVES the frozen host stdin/stdout (the adaptation was a no-op), and that stderr is None.
     - rec= at Phase 2, read Task 2.2 as defence-in-depth, and add a check that a None stderr is tolerated (Task 0.2 RESULT). Not edited here (outside this leg's scope).
  6. Carried: the VoxCeleb "for research purposes" caveat goes to the independent privacy/legal review of `docs/practice/` (D-I2).
- **EXECUTOR stage-0 leg i0-x1 (2026-10-02T12:09+10:00) — brief:**
  - **Built (all new, all throwaway, nothing under `desktop/`, `extension/`, `scripts/`, `docs/`):** `packaging/spike/RUNBOOK.md`; `scribe.spec` + `spike_app_entry.py` + `spike_checks.py` + `spike_stdio.py` (Task 0.1); `host.spec` + `spike_host_entry.py` + `host-manifest-programfiles.json` + `host-manifest-c-root.json` (Task 0.2); `inno-spike.iss` + `inno-payload.txt` (Task 0.3). Build output goes to `C:\scribe-spike\` (outside the repo).
  - **Runbook revised by the peer round 4 fix (leg i0-x4, 2026-10-02T12:33+10:00).** What the practitioner now does differently:
    - On a failure, Task 0.2 (from step 7) goes through "Put everything back" (steps 20–25) and Task 0.3 (from step 4) through the step-14 uninstall, BEFORE reporting.
    - The new 0.2 steps 4a/4b check that no HKLM link exists (in both registry views) and that neither spike folder exists, before anything changes.
    - The spike manifest is copied first, as a marker, and step 22 removes only a folder that carries it (or is empty).
    - 0.1 gained a `pip check` and an exact PyInstaller uninstall line.
    - The compiler fallback is exact Command Prompt syntax.
    - The checks.txt report line says to read it before sending.
  - **Runbook revised again by the peer round 5 fix (leg i0-x6, 2026-10-02T12:42+10:00).** What the practitioner now does:
    - Every task opens with a **"Before you start" block** that stops with nothing changed if the computer is not in the expected state.
    - **0.1 steps 4a–4d:** a fresh `C:\scribe-spike`, a full copy of `.venv` as `venv-backup`, and a `pip freeze` record taken before PyInstaller goes in. Step 7 reports what the install changed.
    - **0.2:** step 5 is a gate (the HKCU link must be exactly the standard value). The link is put back with `reg import` of the step-6 export at steps 18 and 23, verified `True`. This **supersedes** Task 0.2's earlier "restore via `register-native-host.py` / WinError 32" description; the script is no longer used.
    - **0.3:** check A uses an already-installed Inno Setup instead of installing over it; check B requires no spike remnants, and step 14 re-verifies them gone.
    - **The new final section "Put the Python environment back"** (after Task 0.2, or on a 0.1 install failure) restores `.venv` from the copy and verifies it against `venv-before.txt` before `C:\scribe-spike` may be deleted.
    - Failures route through one table in "Read this first".
  - **Runbook revised by the peer round 6 fix (leg i0-x8, 2026-10-02T12:53+10:00).** This **supersedes** the round 5 bullet's `venv-backup` / "Put the Python environment back" description:
    - **0.1 steps 4a–4e:** a fresh `C:\scribe-spike`; a read-only `pip freeze --all` of the everyday `.venv` to `everyday-before.txt`; a copy of `.venv` as the BUILD environment `C:\scribe-spike\venv-build`, checked by `sys.prefix`. PyInstaller goes into the copy and every build (0.1 and 0.2's host) runs as `C:\scribe-spike\venv-build\Scripts\python.exe -m …` — never the copy's other `Scripts\*.exe` launchers, which point at the original. **The everyday `.venv` is never written**, so there is no backup, no restore and no venv row in the failure table.
    - **0.2:** steps 8 and the fallback note each folder in `C:\scribe-spike\created-folders.txt` only after making it; step 22 removes only a noted folder, confirms it is gone, and always says to continue with step 23. The step-15 (0.1) and 4c (0.2) result-file clears are confirmed by `Test-Path`.
    - **Peer round 7 fix (leg i0-x10, 2026-10-02T12:59+10:00):** the Python 3.12 fallback (end of 0.1) is a numbered procedure: make `C:\scribe-spike\venv312`, then rerun steps 5–23 from a new window with every build-copy `python.exe` replaced by `venv312`'s; 0.2 step 2 offers the matching `venv312` host-build command, and the send-back list records which environment was used.
    - **The final section is now "Finishing up":** a read-only compare of the everyday `.venv` against `everyday-before.txt` (proves it untouched), then — once 0.2's step 23 check has said `True` — delete `C:\scribe-spike` and confirm it is gone.
  - **Isolation by construction (0.1):** the spike entry REFUSES (message box, exit 3, nothing opened) unless `LOCALAPPDATA` is set and lies outside the real Local AppData known folder read through `SHGetKnownFolderPath`, which ignores the variable — an Explorer double-click is refused; runbook step 11 makes the practitioner see the refusal once.
  - **Verified from code:** every store root and the models root resolve from `LOCALAPPDATA` (list on Task 0.1). Residues the scratch profile does NOT isolate, named in the runbook with what to avoid: Credential Manager (self-test write/delete of `ClinikoScribe/test`; one spike read of a non-existent name; no clinic may be added), the shared mutex and pipe (real app and Chrome closed), read-only HKCU Chrome-link and WER reads, `%TEMP%` (GUI benchmark WAV), Documents (export — not to be clicked).
  - **Found while building (Task 0.1/D11 input):** frozen, `benchmark.run_all` re-spawns `sys.executable -m scribe_desktop.benchmark …`, which would start a second `scribe-app.exe`; the spike entry dispatches that argv to `benchmark.main` (with the stdio adaptation, since the parent reads the worker's JSON from stdout) — a prototype of D11's planned `--benchmark-worker`, already in scope (no new task).
  - **Stdio (0.1 → 0.2):** measured three ways — at entry, through a pipe-echo child of the exe with and without the adaptation (no Chrome needed), and in the benchmark worker; the host spike applies the adaptation UNCONDITIONALLY (a no-op when the streams exist) and writes which case happened to `%TEMP%\scribe-spike-host-stdio.txt`.
  - **0.3 CI and 0.4 licence:** answered in leg i0-x2 (below). Both images have Inno Setup 6.7.1 and the MSVC C++ tools. The speaker model is CC BY 4.0, from the model card and the upstream "Model License" section.
  - **Unsure / unverified (stated as such in the runbook):** the PyInstaller version — I believe 6.16.0 is the first with Python 3.14 support but could not check; the runbook has the practitioner take the newest release ≥ 6.16.0 and record it exactly; whether `waf` finds MSVC from a plain PowerShell (fallback: x64 Native Tools prompt); that GitHub's Windows runners carry the C++ tools (for 6b's from-source bootloader later); the `VerifiedAndReputablePolicyState` registry reading of Smart App Control (marked optional, the Windows Security page is the authority); Chrome's HKCU-before-HKLM order (the spike's shadow check measures it); whether `FilesNotToBackup` honours `$UserProfile$` (the spike shows what lands; honouring is a Microsoft Learn reading).
  - **Decisions (open, NOT chosen):** D-I1 rec=`C:\Program Files\ClinikoScribe` — if 0.2 logs `host_start` from that path + `origin_verified state=ok` + `pipe_peer` and the badge is green OK; D-I2 rec=in the model pack with a CC BY 4.0 attribution notice beside the file (updated in leg i0-x2; the dataset "research purposes" caveat is a separate check on using the model at all).
  - **Verification:** `desktop/` untouched — `ruff check .` All checks passed; `mypy` no issues in 56 source files (baseline unchanged). No pytest run (no `desktop/` change). `/review-loop` NOT run this phase by brief: the deliverables are throwaway spike inputs and a runbook whose spikes have not run; results land on the tasks after the practitioner reports — the composer decides the review/peer cadence.
- **EXECUTOR stage-0 leg i0-x2 (2026-10-02T12:19+10:00) — web research only**, under the practitioner's read-only WebFetch grant.
  - **Task 0.4 → 🟩:** CC BY 4.0. The sources, the attribution terms and the VoxCeleb "research purposes" caveat are on the task.
  - **Task 0.3's CI question answered:** Inno Setup 6.7.1 and the MSVC C++ tools are on `windows-2025-vs2026` (= `windows-latest`/`windows-2025`) and on `windows-2022`. Rec for Task 3.6: pin 6.7.1 with an `ISCC` version assertion and the `windows-2025` label. Task 0.3 stays 🟨 for the practitioner's local spike.
  - **D-I2's recommendation updated:** model pack plus an attribution notice; still not chosen.
  - **Runbook corrected:**
    - 0.1 step 6b: the CI C++ tools are now verified;
    - 0.3 step 1: install Inno 6.7.1 to match CI;
    - 0.3's "still open" block and § 0.4 now state the answers, with nothing left to run.
  - No other file was touched, and nothing under `desktop/`.
- **EXECUTOR stage-1 leg i1-x1 (2026-10-02T13:04+10:00) — brief:** Phase 1 started ahead of Phase 0's close (practitioner decision 2026-10-02). Task 1.3 🟨: `scripts/generate-extension-key.py` gained `--out` (default `extension/key.pem` unchanged; relative paths from the repo root; prints the key file's own name); `.gitignore` gained `extension/key-dev.pem`. Handoff to the composer to run `.venv/Scripts/python.exe scripts/generate-extension-key.py --out extension/key-dev.pem` from the repo root and resume with the printed public key and dev extension ID. Nothing else touched yet.
- **EXECUTOR stage-1 leg i1-x2 (2026-10-02T13:35:35+10:00) — brief:** Tasks 1.1–1.8 BUILT (all 🟨); ruff clean, mypy clean (57 files). The pytest, `npm run qa` and both extension builds are composer-run; no 🟩 until they are green.
  - **Built:**
    - New `desktop/src/scribe_desktop/install_layout.py`, with the channel and frozen seams.
    - The 11 data-folder builders repointed to it (the Key Findings table matched the code exactly).
    - The identity accessors and their consumers.
    - One cross-channel instance guard.
    - The dev write guard and its Status checkbox.
    - The channel-aware remedy functions.
    - The version pin.
    - Extension `--mode dev|release` (new `extension/src/channel.ts`; dev bundle in `extension/dist-dev`, gitignored).
    - New tests: `test_install_layout.py` (includes the AST grep control, with non-path literals allow-listed by name: the pipe prefixes, the keyring service prefix, the five DPAPI descriptions and the mutex-name builder), `test_identity.py` and `test_dev_write_guard.py`. Additions to `test_status_and_app.py`, `test_ui_encounter.py`, `test_exclusions.py`, `test_draft_write.py`, `test_write_lines.py` and `manifest.test.ts`. The conftest production pin.
  - **D-I1 placeholder:** see Task 1.1. `INSTALL_ROOTS` is one marked constant that accepts both candidates.
  - **What the plan's lists missed (all handled):**
    - `language_model._import_llama`'s remedy.
    - The two version copies in `package-lock.json`.
    - The `ClinikoScribe\models` paths in the docstrings of `scripts/setup-models.py` and `scripts/speaker-embedding-smoke.py`.
    - Test child processes are real source runs, so they were the dev channel. Each now pins production after `assert_offline_env()`.
    - Collection-time `skipif`s would have seen dev and silently skipped the real-ML tests. Fixed by also installing the pin in `pytest_configure`.
  - **Docs left for H.1:** `docs/security/threat-model.md` (still names the old remedy constants and the single data folder), `scripts/README.md`, and AGENTS.md Local Run Steps (dev folder, `--mode dev`). (`extension/KEY.md`'s dev key was done in Phase 1 review round 9, LOW-007.)
  - **Interpretation calls:**
    - Remedies and the models root key on `is_frozen()`, not the channel.
    - The lock stays in the production folder.
    - The dev build's outDir is `dist-dev`.
    - The frozen remedy clause is "reinstall Clinic Scribe".
    - The dev settings live in `note_config`, because `draft_write` is pinned disk-free.
  - **Practitioner-visible consequence (for P.1):** once this lands, a SOURCE run is the dev channel.
    - Its data and models live in `%LOCALAPPDATA%\ClinikoScribe-dev`.
    - Today's HKCU production registration still launches the venv host, which now refuses the release extension's origin. That means a red/OFF badge until the dev host is registered and the dev extension is loaded.
    - `setup-models.py` run from source downloads into `ClinikoScribe-dev\models`.
    - Writes to Cliniko are off until the dev Status checkbox is ticked.
    - The data already in `ClinikoScribe` is untouched.
  - **Composer to verify:**
    - The full desktop pytest. It should grow from 5301; the skip count should stay 9. Watch that the real-ML integration legs RUN rather than skip.
    - `cd extension && npm run qa`, which should pass, including the vitest `define` injection.
    - `npm run build -- --mode dev`: `dist-dev/manifest.json` should carry the dev key and the name "Clinic Scribe Companion (dev)", and the bundle should contain `com.scribe.cliniko_host_dev`.
    - `npm run build -- --mode release`: `dist` should be unchanged, with the release key, the release name and `com.scribe.cliniko_host`.
  - **Assumptions most likely to break:**
    - `define` in vitest inline projects.
    - `_winapi.CreateJunction` and `realpath` in the junction-refusal test.
    - QCheckBox construction under the dev pin in the StatusPanel tests.
- **EXECUTOR stage-0 leg i0-x12 (2026-10-02T22:46+10:00) — the practitioner's spike results and the two decisions recorded:**
  - **Evidence:** only `.cursor/loops/stage-0-practitioner-results.md` (the composer's verbatim transcription). Every value written on the tasks is quoted from it; anything it does not hold is marked "not reported".
  - **🟩 this leg, with every `Done when:` item evidenced:**
    - **0.1:** Python 3.14.6 (no fallback); PyInstaller 6.22.3 with the bootloader built from source (both `runw.exe` SHA-256s); 12/12 checks; self-test 2/2; the real folder identical before and after; the stdio shapes; the Task 3.2 inputs (load-bearing `Qt6Network.dll` filter, bloat list, `_rocm_sdk_core` DLL dir, repo root on the module path).
    - **0.2:** Program Files works; D9 confirmed (HKCU shadows HKLM); Chrome gives stdin/stdout, and stderr is None; the host bundle is clean; the put-back was verified.
    - **0.3:** Inno 6.7.3 "Non-commercial use only"; 14235 ms SHA-256 over 2.3 GiB on mains; per-machine; WER and all six backup/snapshot forms landed verbatim; `{localappdata}` resolves to the elevating account; Users RX with user write denied; in-place upgrade with one `unins000` and no folder prompt; uninstall removes every value. Task 3.4's forms are fixed.
    - **0.5:** no detections on either bundle; Smart App Control Off; no signing pause.
    - **D-I1 / D-I2:** chosen as recorded.
  - **Plan text updated beyond the RESULT bullets:**
    - Task 0.2's stale restore description and its "PROVEN adaptation" line (both corrected in place);
    - 0.3's 6.7.1 pin recommendation (marked superseded);
    - Task 1.1 (the D-I1 narrowing to apply when Phase 1 resumes — stash untouched);
    - Task 3.3 (the attribution notice joins the pack);
    - Task 3.4 (the `$UserProfile$` value forms and D-I1's inherited ACL);
    - Overall Progress (7 of 37 task lines 🟩 → 19%).
  - **Runbook:** `packaging/spike/RUNBOOK.md` step 5 now sets `$v` once from pip's own output, with a `[version]` check against 6.16.0. 6a clones `--branch "v$v"`, and 6b installs `"pyinstaller==$v"`, so no command carries an `X.Y.Z` placeholder.
  - **Open (non-blocking for the Phase 0 close; recommendations in "Open blockers" above):**
    - the Inno Setup licence;
    - the Task 3.6 pin (rec 6.7.3);
    - the frozen-benchmark comparison on mains (practitioner, before `C:\scribe-spike` is deleted);
    - the D6 form confirmation;
    - Task 2.2's reading;
    - the VoxCeleb caveat to the `docs/practice/` review.
  - **Not touched:** `desktop/`, `extension/`, `scripts/`, `docs/`, the git stash and every ref. No code changed, so no suite was run.
- **EXECUTOR stage-1 leg i1-x3 (2026-10-02T23:01:22+10:00) — the composer's first Phase 1 suite, fixed (in the worktree `C:\scribe-build`):** ruff clean and mypy clean (57 files) again. The pytest, `npm run qa` and both builds are re-requested; every Phase 1 task stays 🟨.
  - **pytest collection error, fixed as a class.**
    - The cause: `test_native_host.py` imports `EXPECTED_ORIGIN` from `native_host`, and leg i1-x2 had dropped that import. mypy checks `src` only, so it could not see a test importing a removed name.
    - The enumeration: every top-level name the Phase 1 diff removed from `desktop/src`, `scripts/` and `extension/` (from `git diff -U0`), each grepped across tests, scripts and src, including attribute and string-path monkeypatches.
    - The removed names: the `os` imports in five modules, `exclusions.WER_NOT_EXCLUDED`, `native_host.EXPECTED_ORIGIN`, `status.REGISTRY_KEY`, `main_window.HOST_NAME` and `Literal`, the three `ui/models` reason constants, the key script's `load_or_create_private_key()` signature, and the register script's `os`.
    - The result: `native_host.EXPECTED_ORIGIN` was the ONLY removed name with a remaining consumer. It is restored as an explicit re-export of the production constant (`from scribe_desktop.identity import EXPECTED_ORIGIN as EXPECTED_ORIGIN`), so the pin passes UNCHANGED. A module constant cannot follow the channel, so `verify_origin` still checks `identity.expected_origin()`, which is that same value in production.
    - Not re-added: `status.REGISTRY_KEY` and `main_window.HOST_NAME`. They have no consumers, and a production-only name in those modules would invite a dev-channel caller to use the production key. The three reason constants became functions in i1-x2, and every consumer was moved then.
    - Every attribute the register-script tests patch (`INSTALL_DIR`, `MANIFEST_PATH`, `INSTALLED_EXE`, `LEGACY_ARTIFACTS`, `venv_executable`, the WER names) still exists.
  - **`npm run qa` dom suite, fixed for every environment.**
    - The cause: in a jsdom (client-transformed) project, vite leaves `define` to its dev client script, which jsdom never loads. the free identifier `__SCRIBE_HOST_NAME__` was therefore unbound under jsdom, while node replaces them statically.
    - The fix: a new setup file, `extension/src/test/build-defines.ts`, assigns `buildDefines("release")`, the build's one source, onto `globalThis`. `vitest.config.ts` lists it as `setupFiles` for BOTH projects, beside the existing `define`, with a comment that a new project must list both. `src/test/` is outside the `sinks.test.ts` production scan.
    - New pin: `extension/src/channel.dom.test.ts` asserts that the jsdom project sees the release host name. The node twin is `manifest.test.ts`.
    - `__SCRIBE_HOST_NAME__` is the only build-time define in `extension/src`; there is no `import.meta.env`.
  - **D-I1 applied:** see Task 1.1.
  - **Composer to verify:**
    - The full desktop suite (`.venv/Scripts/python.exe -m pytest` in `desktop/`). Expect 5301+ passing and 9 skips. The real-ML legs should RUN.
    - `npm run qa`: every file loads, and the new `channel.dom.test.ts` passes.
    - Both builds, as before.
- **EXECUTOR stage-1 leg i1-x4 (2026-10-02T23:12:42+10:00) — the second composer suite's one diff-caused failure, fixed at the classification, not the pin:** ruff clean, mypy clean (57 files). The full desktop suite is re-requested. Every Phase 1 task stays 🟨.
  - **The failure:** `test_write_lines.py::TestUncertainPrefix::test_the_progress_success_in_flight_and_open_outcome_lines_are_never_prefixed`. The new kind was outside that test's never-prefixed set.
  - **The decision:** it does NOT belong in that set. Its line invites Copy, and PR-MED-017 prefixes every Copy-inviting refusal while an earlier attempt is open. A refusal before anything is sent is not by itself a reason to skip the prefix: `mock_note`, `not_saved` and `unlinked` are pre-send and prefixed.
  - **The real bug behind it:** the guard ran BEFORE the record's checks and never carried `earlier_attempt_open`. So "allowed → write left open → unticked" showed a bare "copy the note instead".
  - **The fix:**
    - `dev_build_writes_off` added to `WRITE_UNCERTAIN_PREFIXED`. The failing pin now passes UNCHANGED.
    - `draft_write.refuse_before_read` checks the guard after the record's refusals and sets `earlier_attempt_open` from the record.
    - `ui/models.write_control` checks the guard after `write_record_block`, prefixed by `status.open_attempt`. This mirrors the click path, which decides the record first.
    - The two `WRITE_LINES` / docstring comments were corrected.
  - **Tests:**
    - `test_draft_write.py`: the PR-MED-017 unprefixed set is back to its original three names. `TestTheDevBuildWriteGuard` now pins the record-first order (the dev result equals production's for an unreadable or written record) and the open-attempt flag (`attempting` / `unknown` → True, `refused` → False). `test_its_line_is_never_prefixed` became `test_its_line_is_prefixed_while_an_earlier_attempt_is_open`.
    - `test_dev_write_guard.py`: the open-attempt prefix and the record lines' precedence on the button.
    - `test_write_lines.py`: `test_every_copy_inviting_line_is_prefixed` now matches "copy" in any case. That is the gap that let the lowercase dev line through; the case-insensitive `\bcopy\b` adds no other line, because "copying" is not the word.
  - **The class check:** every enumeration of write-line or refusal kinds was found through sibling names (`write_forbidden`, `nothing_to_write`, `mock_note`, …). They are `WriteRefusalName`, `WRITE_LINES`, `WRITE_UNCERTAIN_PREFIXED`, `test_write_lines._EXPECTED`, the two `test_draft_write` refusal sweeps (`get_args`) and `test_audit.py`'s code-pattern test (`get_args`). All account for the new kind. `ui/note.py` holds no such enumeration.
  - **For H.1:** `docs/design-system.md`'s copy of `WRITE_LINES` gains the dev line and its prefix.
  - **Extension:** green in suite 2 (13 files / 313 tests, both builds) and untouched by this leg.
  - **Launcher:** the composer's venv-launcher regeneration was not touched.
- **EXECUTOR stage-1 leg i1-x5 (2026-10-02T23:39:30+10:00) — Phase 1 marked 🟩, then `/review-loop` round 9, fixed; the composer's suite is needed before it Closes:** ruff clean, mypy clean (57 files).
  - **Markers:** Tasks 1.1–1.8 are 🟩. Every `Done when:` is met by the composer's suite 3 (pytest 5393 passed / 9 skipped; `npm run qa` 13 files / 313 tests; both builds, with the `dist-dev` and `dist` manifests and bundles checked). None of them needs a practitioner smoke to be done. Overall Progress is 15 of 39 task lines (38%), after round 9 added Tasks 2.6 and 2.7.
  - **Round 9:** 0 CRIT / 0 HIGH / 3 MED / 10 LOW, every one Applied. There were 19 candidates; 6 were dropped and 1 downgraded. The full block is in the Findings Log.
    - **Code fixes:** MED-001 (5 `TestCheckWer` items were not collected); LOW-001 (the onnxruntime remedy in a packaged build); LOW-006 (the Status checkbox re-reads the file when a save fails).
    - **Test fixes:** MED-002 (frozen-side tests for every raised model or runtime line and for the registration line); LOW-002 and LOW-003 (the two source scans); LOW-008 (the real-store audit row).
    - **Doc fixes:** LOW-004 (`.gitignore`); LOW-005 (10 module docstrings); LOW-007 (`extension/KEY.md`).
    - **Plan work:** MED-003 → Task 2.6 (the real-ML test legs follow the dev models root); LOW-009 → Task 2.7 (a packaged build refuses to start outside its install folder); LOW-010 → H.1's pointer list.
    - **The extension:** only `KEY.md` changed (a document no test reads), so `npm run qa` and the builds are not re-requested.
  - **Composer to verify:** the full desktop suite. Expect about 5417 passed (+5 restored, +19 new) and 9 skips, with the real-ML legs RUNNING. Then round 10, the re-review, runs in-session.
  - **For H.1** (besides its own list):
    - `docs/design-system.md`'s copy of `WRITE_LINES` gains the `dev_build_writes_off` line with its `write_uncertain` prefix, and the dev-only Status checkbox with its new save-failure line;
    - the round-9 pointers listed on H.1, including the shared Credential Manager namespace residue.
  - **Practitioner smoke for Phase 1: NOT needed before Phase 2.**
    - Phase 1 lives only in this worktree, on `installation-build`. The everyday app runs from `main` in `C:\Recording clinic software` with its own `.venv`, and nothing in Phase 1 touches it: no registration, no data folder, no Chrome profile.
    - Every Phase 1 behaviour is pinned by the suite with injected channels, folders and registries (C6).
    - An OPTIONAL dev-channel smoke can wait until Task 2.6 needs the dev models anyway. From a normal terminal it would be: populate `%LOCALAPPDATA%\ClinikoScribe-dev\models`; run `register-native-host.py` from this worktree's venv (the dev host); load `extension\dist-dev` in a SEPARATE Chrome profile; then check for the green OK badge, "(dev)" in the name, and the Write button off until the Status checkbox is ticked.
- **EXECUTOR stage-1 leg i1-x6 (2026-10-02T23:58:08+10:00) — round 9 Closed on composer suite 4, round 10 (the re-review) run and fixed; the loop converges on the next composer suite:** ruff clean, mypy clean (57 files). Review History integrity: OK (`loop-history-check`: 10 + 10, strictly increasing).
  - **Round 9:** Closed on composer suite 4 (pytest 5417 passed / 9 skipped, exactly the +24 expected).
  - **Round 10 (loop round 2 of cap 3):** 0 CRIT / 0 HIGH / 0 MED / 5 LOW, all Applied. There were 18 candidates, 13 dropped.
    - **LOW-001 ⚡:** the remedy scan now ignores case and accepts either slash, and its self-test uses the scan's own pattern, with 4 cases.
    - **LOW-002:** the folder-scan docstring is corrected, with one f-string case added.
    - **LOW-003 ⚡:** `KEY.md` names `identity.py` as well as `channel.ts`.
    - **LOW-004:** D4 gains an AS-BUILT note. With dev writes off, the Write click's own read and pre-write checks do not run. The code is unchanged because it follows D4's first bullet.
    - **LOW-005:** a new AST pin says only `prepare_write` builds a `PreparedWrite`, so hop 2 cannot bypass the dev guard.
  - **What changed:** test files (`test_install_layout.py`, `test_dev_write_guard.py`), `extension/KEY.md` and the plan. No `src` code changed and no extension source changed.
  - **Composer to verify:** the full desktop suite. Expect 5417 + 5 = about 5422 passed (+4 remedy self-test cases replacing 1, +1 folder case, +1 PreparedWrite pin) and 9 skips.
  - **Next:** on green the round Closes and `/review-loop` has CONVERGED (no CRIT/HIGH/MED in round 10). The next leg records that and hands off `reason=phase-complete` for the composer's codex peer pass. `/peer-loop` was not run.
  - **H.1 and the practitioner-smoke statement:** unchanged from leg i1-x5. No smoke is needed before Phase 2. The D4 AS-BUILT note adds one optional dev-smoke step: tick the box against a disposable draft to exercise the pre-write checks.
- **EXECUTOR stage-1 leg i1-x7 (2026-10-03T00:05:37+10:00) — round 10 Closed on composer suite 5; Phase 1's `/review-loop` CONVERGED:**
  - **Evidence:** pytest 5422 passed / 9 skipped; ruff clean; mypy 57 files. The extension is unchanged since suite 2: 13 files / 313 tests, both builds OK.
  - **Convergence, per the `/review-loop` SKILL termination check:**
    - Round 10 (loop round 2 of cap 3) found no CRIT, HIGH or MED findings.
    - Its Round Classification is 3 🆕 + 2 ⚡, all LOW, with skew=none and no 🔁 recurrence.
    - Every Fix-now finding was applied and is green on suite 5.
    - No Defer, Accept or MUST-PAUSE item is open.
  - **Trajectory:** round 9 had 3 MED + 10 LOW; round 10 had 5 LOW. `loop-history-check` reports 10 + 10 rounds, strictly increasing.
  - **Markers:** Tasks 1.1–1.8 stay 🟩. Overall Progress is unchanged at 38% (15 of 39 task lines).
  - **This leg changed** the plan only.
  - **Next (composer):** the cross-family codex peer pass over Phase 1, then the Phase 1 commit on `installation-build`. `/peer-loop` was not run here.
  - **Carried forward unchanged from legs i1-x5 and i1-x6:**
    - the H.1 items;
    - no practitioner smoke is needed before Phase 2;
    - the optional dev-channel smoke, which now includes ticking the box against a disposable draft to exercise the pre-write checks;
    - the new Phase 2 Tasks 2.6 and 2.7.
- **EXECUTOR stage-1 leg i1-x9 (2026-10-03T00:41:10+10:00) — LEG 2 (/fix) of peer round 11: PR-LOW-016 Applied with every sibling:** ruff clean, mypy clean (57 files).
  - **The fix:** `desktop/tests/conftest.py` pins `install_layout.is_frozen` to `False` before collection (`pytest_configure`, which covers the import-time real-ML gates) and per test (the autouse fixture, via `use_frozen`). `REAL_IS_FROZEN` is kept for the one test of the real function.
  - **The other test edits:**
    - `test_integration_no_sockets.py`: the five child processes pin it beside their channel pin.
    - `test_install_layout.py`: the real-function test restores `REAL_IS_FROZEN`, and the pinned-state test now proves the pin holds with `sys.frozen = True`.
  - **Covered with no assertion changed:** every sibling the leg-1 tuple listed.
  - **Untouched:** `src`, scripts, the extension and git refs.
  - **Fix-delta self-check:** PASS.
  - **Composer to verify:** the full desktop suite. Expect 5422 passed / 9 skipped, unchanged: no test was added or removed, only assertions. The real-ML legs should still RUN.
- **EXECUTOR stage-2 leg i2-x1 (2026-10-03T01:22:34+10:00) — Phase 2 (Tasks 2.1–2.7) BUILT in the worktree `C:\scribe-build`; every task 🟨; ruff clean, mypy clean (58 source files, +1 `ui/hardware_check.py`):** the per-task notes are on each task.
  - **Built:**
    - 2.1: the frozen worker argv and its exact-shape dispatch, first in `app.main`. The temp-file fallback is NOT built; Task 0.1's evidence shows working pipes.
    - 2.2: the `binary_stdio` seam, built as defence-in-depth, and `set_binary_stdio(stdin, stdout)`. A None stderr is pinned as tolerated.
    - 2.3: `WindowsLayer.native_host_entries` in Chrome's order; the Status line (winner, the others, the frozen per-user override warning); the host log; the layer passed `app.main` → `MainWindow` → `StatusPanel`.
    - 2.4: the WER set and hives by channel, and `check_backup_exclusions` (production only).
    - 2.5: the prose-stage timing (`ui/hardware_check.py`), the `ProseBenchmark` lines and the verdict for both, on the Microphone panel.
    - 2.6: the real-ML legs (gates, bodies, children) on the dev models root.
    - 2.7: a packaged build outside its install folder refuses in both entry points before any data root.
  - **Enumerations (from the code, on the tasks):**
    - the real-ML legs: 7 gates, plus 3 child scripts pinned by a class-closed test and an AST `skipif` scan;
    - the `WindowsLayer` fakes updated: `test_exclusions.FakeLayer` and the integration child's string fake;
    - the callers of `read_registration_status` and `_on_benchmark_done`, all updated.
  - **Composer to verify:**
    - The full desktop suite (`.venv/Scripts/python.exe -m pytest` in `desktop/`). Expect about +115 tests: `test_frozen_runtime.py` ≈68 new, `test_hardware_check.py` ≈22 new, `test_exclusions.py` +27, and `test_status_and_app.py` −2 +1 (two real-machine HKCU registration tests replaced; Task 2.3), so about 5537 passed.
    - **The skip count rises:** until the practitioner populates `%LOCALAPPDATA%\ClinikoScribe-dev\models`, every real-ML leg SKIPS with a reason naming that root. Please report the skip list.
    - `npm run qa`: the extension is untouched; re-run only if the suite set requires it.
  - **Open items:**
    - **PRACTITIONER (Task 2.6, normal PowerShell, C7):** `Copy-Item -Recurse "$env:LOCALAPPDATA\ClinikoScribe\models" "$env:LOCALAPPDATA\ClinikoScribe-dev\models"`, about 5.3 GiB if every model is present. Then report the summed size (the command is on Task 2.6). The composer then re-runs the suite and reports the run/skip count of the real-ML legs. Only then can 2.6 go 🟩. rec= do it before the Phase 2 commit, so the real-ML no-sockets legs run on Phase 2's code.
    - **Ratify (Task 2.5):** the prose verdict bar, 5 s OK / 10 s warning per section. rec= accept; it is a local line only and one constant pair.
  - **For H.1:**
    - the D9 policy residue (`NativeMessagingUserLevelHosts=0` makes the override warning moot; the policy is not read);
    - the frozen refusal's stderr-only line (usually unseen);
    - the Status registration wording, the WER/backup lines and the hardware-check lines in `docs/design-system.md`;
    - `threat-model.md`'s EXCLUSIONS paragraph (HKLM WER, the backup check) and its Chrome-link section (Chrome's lookup order, the 32-bit-view-first claim from Chromium's source);
    - `docs/testing/` or AGENTS.md Local Run Steps: the real-ML legs now need the dev models root.
  - **Not touched:** the extension, `scripts/`, `docs/`, git refs and the main checkout.
- **EXECUTOR stage-2 leg i2-x2 (2026-10-03T01:48:24+10:00) — Phase 2 markers, then `/review-loop` round 13 (loop round 1 of cap 3); all 14 findings applied; composer-run suite pending:**
  - **Markers:** on composer suite 1 (pytest 5527 passed / 20 skipped, ruff clean, mypy 58, `npm run qa` 13 / 313), Tasks 2.1–2.5 and 2.7 are 🟩. Overall Progress is 21 of 39 task lines, 54%.
    - Task 2.6 stays 🟨. What remains: (1) the practitioner's dev-models copy (the command is on Task 2.6, normal PowerShell, C7); (2) the composer re-runs pytest and reports how many of the 11 real-ML legs run and how many skip.
    - The prose bar is ACCEPTED by the composer (recorded on Task 2.5).
  - **Round 13:** two read-only lenses (correctness/security; plan adherence and tests), merged and re-verified at their lines. 0 CRIT / 0 HIGH / 3 MED / 11 LOW, all applied. Details are in the Findings Log.
    - MED-001: the hardware check uses the Note tab's ONE language-model cache, never a second 2.3 GiB copy.
    - MED-002: a failed model call, or nothing rendered, is a named skip, never an "OK".
    - MED-003: the frozen benchmark worker is its own exception boundary, one type-name line and exit 1; Task 3.2 gains `disable_windowed_traceback=True`.
    - The LOWs:
      - the load excluded from the per-section CPU;
      - a stale std handle → `None`;
      - the host's registry tripwire no longer swallows the C6 sentinel;
      - the packaged spawn shape is checked against its dispatch;
      - `KEY_QUERY_VALUE` as Chromium opens the keys;
      - a stricter gate scan;
      - `BACKUP_VALUE_NAME` in the source scan;
      - a 32-bit-view-only real-layer case;
      - `test_ui_models`' two host-state reads, now on an injected `LOCALAPPDATA`;
      - a comment fix;
      - a malformed manifest never crashes the Status tab.
    - In-leg: ruff clean, mypy 58 files.
  - **Composer to run:** the full desktop suite. Expected pytest **5555 passed / 20 skipped** (+28: `test_hardware_check.py` +6, `test_frozen_runtime.py` +21 of which 2 are Windows-only, `test_install_layout.py` +1). The extension is untouched.
  - **Then:** resume the executor for `/review-loop` round 14, the re-review after round 13's fix.
  - **Residue for H.1 (new):** the SOURCE-run benchmark worker (`python -m scribe_desktop.benchmark`, `__main__`) still prints a traceback to stderr on an exception. That behaviour predates Phase 2 and has no windowed box; it is dev channel only.
  - **The one open item:** Task 2.6's practitioner step. It does not block convergence.
  - **Not touched:** the extension, `scripts/`, `docs/`, git refs and the main checkout.
- **EXECUTOR stage-2 leg i2-x3 (2026-10-03T02:05:35+10:00) — round 13 Closed on composer suite 2; `/review-loop` round 14 (loop round 2 of cap 3) found 0 CRIT / 0 HIGH / 0 MED / 4 LOW, all applied; /review-loop CONVERGED (no CRIT/HIGH/MED), pending the composer-run suite for the 4 LOW fixes:**
  - **Round 13 closed:** composer suite 2 had pytest 5555 passed / 20 skipped, exactly the expected count.
  - **Round 14** (two lenses: post-fix regression, missed-issue):
    - LOW-001: one load-failure line, with the restart advice, whichever of the Note tab and the check failed first, and never "this note".
    - LOW-002: the model is taken before the stage is clocked, so a wait on another thread's load is never section time.
    - LOW-003: the production crash-report check reads each hive on its own, so one unreadable hive no longer hides the other.
    - LOW-004: a docstring.
    - Three are ⚡ in round 13's hardware-check fix, all LOW, in one function.
    - In-leg: ruff clean, mypy 58 files.
  - **Composer to run:** the full desktop suite. Expected pytest **5559 passed / 20 skipped** (+4, all `test_exclusions.py`). The extension is untouched.
  - **Then:** resume the executor to close round 14 on that suite and END `phase-complete`. No round 15 is owed, since round 14 had no CRIT/HIGH/MED. A failure there is a /fix stop-on-failure (must-pause).
  - **The one open item:** Task 2.6's practitioner step (the dev-models copy, then the composer's real-ML run/skip report). It does not block convergence.
  - **Not touched:** the extension, `scripts/`, `docs/`, git refs and the main checkout.
- **EXECUTOR stage-2 leg i2-x4 (2026-10-03T02:11:26+10:00) — round 14 Closed on composer suite 3 (ruff clean, mypy 58, pytest 5559 passed / 20 skipped); Phase 2 `/review-loop` CONVERGED at loop round 2 of cap 3; plan-only leg, no code changed:**
  - **Trajectory:** round 13 found 3 MED / 11 LOW, round 14 found 0 MED / 4 LOW. Every finding is applied and verified, with no CRIT or HIGH in either round.
  - **Markers:** Tasks 2.1–2.5 and 2.7 are 🟩, and 2.6 is 🟨. Overall Progress is unchanged at 21 of 39 task lines (54%).
  - **Next (composer):** the codex peer pass over the Phase 2 diff (`git diff HEAD` plus the three untracked files), then the Phase 2 commit on `installation-build`.
  - **The one open item:** Task 2.6's PRACTITIONER step. Copy the models into `%LOCALAPPDATA%\ClinikoScribe-dev\models` from a normal PowerShell (the command is on Task 2.6). The composer then re-runs pytest and reports the 11 real-ML legs' run/skip count. Only then can 2.6 go 🟩.
  - **Carried for H.1:**
    - the D9 policy residue;
    - the frozen refusal's stderr-only line;
    - the source-run benchmark worker's traceback;
    - the Status registration, WER/backup and hardware-check lines in `docs/design-system.md`;
    - `threat-model.md`'s EXCLUSIONS and Chrome-link sections;
    - the real-ML legs' dev models root in `docs/testing/` or AGENTS.md.
  - **Not touched:** the extension, `scripts/`, `docs/`, code, git refs and the main checkout.
- **EXECUTOR stage-2 leg i2-x6 (2026-10-03T02:22:51+10:00) — LEG 2 (/fix) of codex peer round 15 (pass stage-2.p1, peer_round 1 of cap 5); round 15 Closed pending the composer-run suite:**
  - **Applied:**
    - PR-LOW-017: `test_frozen_runtime.py`'s module docstring is narrowed to the isolation enforced; `sys.executable` is read only as the spawn's argv[0], never run.
    - PR-LOW-018, with both leg-1 siblings: `test_language_model_runtime.py`'s module bullet, comment and class docstring, and `test_speaker_embedding.py`'s module docstring, now name the dev models root (Task 2.6) as the prerequisite. The "always skips" and "agent shells cannot see" wording is gone.
    - Docstrings and comments only; no test or code changed.
  - In-leg: ruff clean, mypy 58 files.
  - **Composer to run:** the full desktop suite. Expected pytest **5559 passed / 20 skipped**, unchanged, since there is no new or removed test.
  - **Then:** a confirmation round of the peer pass (stage-2.p1 peer_round 2), then the Phase 2 commit.
  - **The one open item:** Task 2.6's practitioner step (the dev-models copy, then the composer's real-ML run/skip report).
  - **Not touched:** source code, the extension, `scripts/`, `docs/`, git refs and the main checkout.
- **EXECUTOR stage-2 leg i2-x8 (2026-10-03T02:31:49+10:00) — LEG 2 (/fix) of codex peer round 16 (pass stage-2.p1, peer_round 2 of cap 5; trajectory 2 → 1); round 16 Closed pending the composer-run suite:**
  - **Applied:** PR-LOW-019. `test_language_model_runtime.py`'s module bullet and `TestRealModelSmoke` docstring now say a missing runtime skips as "the prose runtime is not installed" and a missing model skips naming the dev root. Siblings: none. Docstrings only.
  - In-leg: ruff clean, mypy 58 files.
  - **Composer to run:** the full desktop suite. Expected pytest **5559 passed / 20 skipped**, unchanged.
  - **Then:** the composer decides whether a confirmation round is owed for a two-clause docstring fix, then the Phase 2 commit.
  - **The one open item:** Task 2.6's practitioner step.
  - **Not touched:** source code, the extension, `scripts/`, `docs/`, git refs and the main checkout.
- **EXECUTOR stage-3 leg i3-x1 (2026-10-03T03:11:20+10:00) — Phase 3 (Tasks 3.1–3.9) BUILT in the worktree `C:\scribe-build`; every task 🟨; ruff clean, mypy clean (58 source files):** each task's "Leg i3-x1" note carries its detail, interpretation calls and practitioner step.
  - **New:**
    - `scripts/lock-build-requirements.py` (3.1)
    - `packaging/scribe.spec`, `packaging/entry_app.py`, `packaging/entry_host.py` (3.2)
    - `packaging/speaker-model-ATTRIBUTION.txt` (3.3, D-I2)
    - `scripts/build-release.py` (3.3 and 3.5)
    - `packaging/scribe.iss` (3.4)
    - `.github/workflows/release.yml` (3.6)
    - `scripts/check-installed-sockets.py` (3.8)
    - `docs/release/pilot-builds.md` (3.9)
    - tests: `test_build_lock.py`, `test_build_spec.py`, `test_build_release.py`, `test_installer_script.py`, `test_release_workflow.py`, `test_check_installed_sockets.py`
  - **Changed:**
    - `install_layout.py`: `data_root(of=)`, plus `model_pack_name` and its two constants.
    - `app.py`: `--self-check-offline` (3.2), dispatched FIRST in `main`, before Task 2.7's install-folder check.
    - `scripts/register-native-host.py`: dev-only (3.7).
    - `scripts/setup-models.py`: `--root` (3.3).
    - `.gitattributes`: `eol=lf` for the attribution notice and `packaging/models-manifest.json`.
    - `.gitignore`: `/build/`.
    - Their tests: `test_register_native_host.py`, `test_install_layout.py`, `test_display_name.py`, `test_setup_scripts.py`, `test_frozen_runtime.py`.
  - **Composer to run:** the full desktop suite and the extension `npm run qa`.
    - The baseline is 5559 passed / 20 skipped. Expected about **+159 passed / +3 skipped**, roughly 5718 / 23; the count is estimated, not exact.
    - The extension is unchanged, so `npm run qa` should be 13 files / 313 tests.
    - The three new skips are named:
      - the committed lock (`_LOCK_ABSENT`, Task 3.1);
      - the committed model manifest (`_MANIFEST_ABSENT`, Task 3.3);
      - the workflow's commit pins (`PIN-REQUIRED`, Task 3.6).
    - Markers go 🟩 only on that green suite, and only for tasks whose Done needs no practitioner step: 3.7 and 3.9.
  - **Interpretation calls** (each recorded on its task):
    - PyInstaller is pinned by source commit, not in the hashed lock (D1).
    - The offline self-check runs before Task 2.7's check, so a scratch-run bundle can answer it.
    - `model_pack_name` lives in `install_layout`, because of the source scan.
    - The policy's untick removal uses Inno's previous data. Residue: the uninstall log can still remove a foreign policy written later.
    - The WMI running-process check fails closed.
    - The installer refuses any `{app}` other than D-I1.
    - Bundle trims are evidence-based: `huggingface_hub` and `av` are kept, since faster_whisper imports them at module level.
    - The Qt network filter is broadened past the spike's two prefixes, to `Qt6NetworkAuth` and `Qt6QmlNetwork`.
    - `windows-2025` instead of `windows-latest`.
    - Every action beyond `ci.yml`'s three is commit-pinned.
  - **PRACTITIONER/COMPOSER STEPS** (none can run from this shell; exact commands are on each task):
    1. 3.1: generate and commit `desktop/requirements-build.txt` from the worktree `.venv`'s freeze (network; the exact commands are on Task 3.1).
    2. 3.3: `--write-manifest` over the dev models root, then commit `packaging/models-manifest.json`. This needs the models, so Task 2.6 comes first.
    3. 3.4: the ISCC 6.7.3 compile check.
    4. 3.2: the bundle gate (self-check and trims) on a build from `venv-build`.
    5. 3.5: the full local build plus `--model-pack`.
    6. 3.6: the two action SHAs, the Inno installer SHA-256 and its URL, push `main`, dispatch, `gh attestation verify`. Remote-affecting, so it is the practitioner's call.
    7. 3.8: run in P.1.
    - Task 2.6 (the dev-models copy) is still open.
  - **Open (not decided here):**
    - Inno Setup's "Non-commercial use only" licence notice.
    - The Inno version pin: built to the recommendation, 6.7.3 on both sides (`INNO_VERSION`, release.yml). CI's preinstalled 6.7.1 is therefore not used.
  - **H.1 doc items to add (not changed here, by the brief):**
    - data-flow flow 9: the lock generation, the PyInstaller clone and CI's Inno download as setup/build-time network;
    - threat-model installation residues: the policy untick, WMI fail-closed, the self-check ordering, and the register script's one production-folder delete (C8 migration);
    - `scripts/README.md`: the four new scripts and the dev-only register;
    - AGENTS.md: the release steps;
    - the retention schedule: the model pack, `SHA256SUMS.txt` and `build/`.
  - **Not touched:** the extension, `ci.yml`, git refs, private keys and the main checkout.
- **EXECUTOR stage-3 leg i3-x2 (2026-10-03T03:21:04+10:00) — composer suite 1's 8 failures fixed at their roots, each as a class; ruff clean, mypy clean (58 source files); every Phase 3 task stays 🟨:**
  - **Root 1, the bound default (5 failures; C6):**
    - The failures: `TestStageOne` ×3 (the clean environment, preflight `out`, preflight `commit`) and `TestTheInstallerCompile` ×2.
    - The cause: `build-release.py`'s `load_manifest(path=MANIFEST_PATH)` bound the REAL repo path at definition, so the `build_inputs` fixture's stand-in never reached it. Every reader died on the absent practitioner artefact. The `manifest` refusal passed only because the real file is absent.
    - The fix: the default resolves at CALL time.
    - Class guards:
      - `TestNoRepoArtefactIsRead`: the reader follows the stand-in, present and absent;
      - an AST scan of `build-release.py` and `lock-build-requirements.py`: no function binds an UPPER-CASE module constant as a default (it is clean today).
    - The lock already resolved at call time, and the lock script has no bound path defaults.
  - **Root 2, spelling pins in place of semantic surfaces (3 failures):**
    - **`test_installer_script.py`:**
      - D8 now pins the launch surface: no `[Run]` or `[UninstallRun]`, no `postinstall` or `runasoriginaluser` flag on any entry, no process-starting call in `[Code]`. A companion proves the check is not vacuous.
      - The policy entry is matched by its `#define`-expanded key.
      - `_code()` splits at the header line.
      - `scribe.iss` is unchanged.
    - **`test_release_workflow.py`:**
      - The pins read the workflow with full-line comments removed (`BODY`), and each step is found by its own first line (`_step`). The old slice started at the header comment's "Install Inno Setup", which is why the hash pin was not found.
      - The hash pin now also checks the order: refuse, then download, then compare.
      - New: the comment can never be taken for the step.
      - **Also fixed, the same class but latent:** the commit-pin test's skip condition read `TEXT`, whose header comment mentions PIN-REQUIRED. It would have skipped forever after the real pins land; it now reads `BODY`.
      - `release.yml` is unchanged.
  - **Recorded on Task 3.4:** the composer's ISCC 6.7.3 compile check PASSED, and the practitioner is to delete `C:\scribe-iss-check`.
  - **Composer to run:** the full desktop suite. Expected **5723 passed / 23 skipped**: 5741 tests before, +5 new; the 3 named skips are unchanged. The extension is untouched, so suite 1's `npm run qa` (13 / 313) stands.
  - **Then:** markers per leg i3-x1 (🟩 only for 3.7 and 3.9 on green), then `/review-loop` from round 18.
  - **Not touched:** `scribe.iss`, `release.yml`, app source, the extension, git refs and the main checkout.
- **EXECUTOR stage-3 leg i3-x3 (2026-10-03T03:32:20+10:00) — Phase 3 markers on composer suite 2, then `/review-loop` round 18 (loop round 1 of cap 3): 1 MED + 4 LOW, all Applied; ruff clean, mypy clean (58 source files):**
  - **Markers:** on composer suite 2 (pytest 5723 passed / 23 skipped; `npm run qa` 13 / 313), Tasks 3.7 and 3.9 are 🟩: their Done needs no practitioner step.
    - Tasks 3.1–3.6 and 3.8 stay 🟨, each with its remaining step named on the task: the lock (network), the manifest (Task 2.6's models first), the real PyInstaller and ISCC builds, the CI pins and run, and the P.1 socket run.
    - Overall Progress is 23 of 39 task lines, 59%.
  - **Round 18:** read every changed file in full; the composer's focus points (C2/C8, C3/D8, C4, C1, C6) all HOLD, with the evidence recorded in the round header.
    - **MED-001:** `scribe.iss` now clears `{app}\_internal` and `{app}\extension` at every install, so an upgrade or rollback installs exactly the audited bundle.
    - **LOW-001:** the register script's docs warn that, until Phase P, the production-named HKCU link is the everyday app's live one.
    - **LOW-002:** `HOSTILE_ENV` is pinned equal to everything the app enforces.
    - **LOW-003:** the pilot-builds doc says to compare hashes ignoring capitals.
    - **LOW-004:** this plan's step 1 now names the right lock file and freeze source.
    - Review History integrity: OK (18 + 18).
  - **Composer to run:** the full desktop suite. Expected **5725 passed / 23 skipped** (+2 new tests: `test_an_upgrade_replaces_the_program_whole`, `test_every_variable_the_app_enforces_is_set_wrong`). The extension is untouched.
    - **Optional but cheap:** re-run the Task 3.4 ISCC compile check, since `scribe.iss` changed (the same command; it last passed in suite 1).
  - **Then:** `/review-loop` round 19 (loop round 2 of cap 3), the re-review, to convergence.
  - **Open items, not convergence blockers:**
    - the practitioner and network steps on Tasks 3.1–3.6 and 3.8;
    - Task 2.6;
    - the Inno licence notice and the 6.7.3 pin;
    - deleting `C:\scribe-iss-check`.
  - **Not touched:** app source, the extension, `release.yml`, `ci.yml`, git refs and the main checkout.
- **EXECUTOR stage-3 leg i3-x4 (2026-10-03T03:41:41+10:00) — round 18 Closed on composer suite 3; `/review-loop` round 19 (loop round 2 of cap 3): 0 CRIT / 0 HIGH / 0 MED / 1 LOW, Applied; ruff clean, mypy clean (58 source files):**
  - **Recorded:** the composer's ISCC 6.7.3 re-compile after MED-001 ("Successful compile (2.203 sec)") on Task 3.4. Round 18 is Closed.
  - **Round 19:** a full re-review plus the post-fix regression check over round 18. No regression. One 🆕 LOW, applied: `build-release.py` now shows ISCC's own output when a compile is refused (`Completed.stderr`), with 2 new tests.
  - **The loop CONVERGES** (no CRIT/HIGH/MED; 1 🆕 LOW fixed) once the composer's suite confirms the fix.
  - **Composer to run:** the full desktop suite. Expected **5727 passed / 23 skipped** (+2: `test_a_refused_compile_shows_the_compilers_own_words`, `test_a_good_compile_prints_nothing_extra`). The extension and `scribe.iss` are untouched.
  - **Then:** close round 19 and mark the phase's review CONVERGED (the next leg ends `reason=phase-complete`), then the Phase 3 commit.
  - **Markers:** unchanged. 3.7 and 3.9 are 🟩; 3.1–3.6 and 3.8 stay 🟨 on their named practitioner, network or build steps; Overall Progress is 59%.
  - **Open items, not convergence blockers:**
    - those steps;
    - Task 2.6;
    - the Inno licence notice and the 6.7.3 pin;
    - deleting `C:\scribe-iss-check`;
    - the H.1 doc items listed in leg i3-x1.
  - **Not touched:** app source, the extension, `scribe.iss`, `release.yml`, `ci.yml`, git refs and the main checkout.
- **EXECUTOR stage-3 leg i3-x5 (2026-10-03T03:46:58+10:00) — round 19 Closed on composer suite 4 (ruff clean, mypy 58, pytest 5727 passed / 23 skipped); Phase 3 `/review-loop` CONVERGED at loop round 2 of cap 3 (rounds 18–19); plan-only leg, no code changed:**
  - **Markers, unchanged and truthful:** 3.7 and 3.9 are 🟩. Overall Progress is 23 of 39 task lines (59%). The rest stay 🟨, each on a named step:
    - 3.1: the practitioner generates and commits `desktop/requirements-build.txt` (network).
    - 3.2: a real PyInstaller build passes `--audit`.
    - 3.3: `--write-manifest` over the dev models, after Task 2.6; commit `packaging/models-manifest.json`.
    - 3.4: installs in Phase P. It COMPILES with ISCC 6.7.3 already (twice).
    - 3.5: the full local build plus `--model-pack`.
    - 3.6: the two action SHAs, the Inno installer SHA-256 and URL, then push and dispatch on `main` and `gh attestation verify` (remote-affecting; the practitioner decides).
    - 3.8: the P.1 step 10 socket run.
    - 2.6 is still 🟨.
  - **The 23 skips:** 9 directory-symlink variants, 11 real-ML legs (Task 2.6), and the 3 named artefact skips (lock 3.1, manifest 3.3, workflow pins 3.6). Each turns into a run when its artefact lands.
  - **Open (not decided here):** Inno Setup's "Non-commercial use only" licence notice; the 6.7.3 pin (built to it on both sides); deleting `C:\scribe-iss-check`; the H.1 doc items listed in leg i3-x1.
  - **Files for the composer's codex peer pass** (27 files, every Phase 3 change; source and its tests together):
    - **Slice A, build and lock (11):**
      - `scripts/build-release.py` and `desktop/tests/test_build_release.py`
      - `scripts/lock-build-requirements.py` and `desktop/tests/test_build_lock.py`
      - `packaging/scribe.spec`, `packaging/entry_app.py`, `packaging/entry_host.py` and `desktop/tests/test_build_spec.py`
      - `packaging/speaker-model-ATTRIBUTION.txt`, `.gitattributes`, `.gitignore`
    - **Slice B, installer, CI, release record and socket check (7):**
      - `packaging/scribe.iss` and `desktop/tests/test_installer_script.py`
      - `.github/workflows/release.yml` and `desktop/tests/test_release_workflow.py`
      - `docs/release/pilot-builds.md`
      - `scripts/check-installed-sockets.py` and `desktop/tests/test_check_installed_sockets.py`
    - **Slice C, app, layout and the source-run scripts (9):**
      - `desktop/src/scribe_desktop/app.py` (the self-check) and `desktop/tests/test_frozen_runtime.py`
      - `desktop/src/scribe_desktop/install_layout.py` and `desktop/tests/test_install_layout.py`
      - `scripts/register-native-host.py`, `desktop/tests/test_register_native_host.py` and `desktop/tests/test_display_name.py`
      - `scripts/setup-models.py` and `desktop/tests/test_setup_scripts.py`
    - **Peer focus worth naming:**
      - C2/C8: `--unregister`'s two production files and its one HKCU key.
      - C3/D8/C4: the installer's HKLM-only writes, no launch, `{app}`-only deletes (including round 18's unconditional `_internal` and `extension` clear).
      - C1: the network at build time only, and the self-check opens nothing.
      - C6: the tests read no artefact or host state; leg i3-x2's call-time defaults and comment-free pins.
      - The interpretation calls on each task's leg i3-x1 note: PyInstaller pinned by commit (not in the lock), the self-check before Task 2.7's check, the policy's previous-data untick and its uninstall residue, WMI failing closed, `windows-2025`, and commit-pinned new actions.
  - **Then:** the Phase 3 commit, after the composer's peer pass.
  - **Not touched this leg:** any code, test, doc or script; git refs; the main checkout.
- **EXECUTOR stage-3 leg i3-x7 (2026-10-03T04:05:03+10:00) — LEG 2 (/fix) of codex peer round 20 (pass stage-3.p1, peer_round 1 of cap 5): all 4 Applied with their siblings; ruff clean, mypy clean (58 source files); the round stays Open for codex confirmation round 21:**
  - **PR-HIGH-001 (verified MED), `scripts/build-release.py`:**
    - `preflight` `:589-599` refuses a PyInstaller source with any changed, untracked or IGNORED file (`git status --porcelain --untracked-files=all --ignored`), before waf, with a re-clone line (`PYINSTALLER_CLONE` `:84`).
    - The sibling is RECORDED, not refused (D7, local builds are for spikes). `source_state` `:689` and `write_build_info` `:705` write `BUILD-INFO.txt` (commit, `tree=clean|DIRTY|unknown`), which is summed (`:740`), and `stage_two` prints it.
  - **PR-HIGH-002 (verified MED), `scripts/build-release.py`:** standalone `--audit` returns 1 on `detected` (`:797-803`), with `DEFENDER_DETECTED` `:115` shared with `stage_two`'s refusal (`:738`).
  - **PR-HIGH-003 (verified MED), `packaging/scribe.iss`:**
    - `ModelFileMatches` `:179` is the one file test.
    - `RemoveDamagedModels` `:214` checks EVERY copy, deletes each bad one and checks each delete.
    - `ssPostInstall` `:324` sets `ModelsIncomplete`, and the Finish page `:341` says "NOT completely installed".
    - **Sibling:** the policy removal moved to `ssInstall` `:313` and is checked with `RegValueExists` `:317`; `RegisterPreviousData` `:300` keeps it "ours" (`or PolicyLeft`), and the Finish page says it stayed (`:355`).
    - **Assumption for P.3:** Inno writes the previous data after `ssInstall`.
  - **PR-MED-018 (verified LOW), `desktop/tests/test_frozen_runtime.py:324`:** seamed. A fake `find_spec` stands in, and the test still pins the call-time default and exit 2.
  - **Docs:** `docs/release/pilot-builds.md` (Commit) records only a `tree=clean` build.
  - **Files changed (for the confirmation slice), 7:**
    - `scripts/build-release.py`
    - `packaging/scribe.iss`
    - `desktop/tests/test_build_release.py`
    - `desktop/tests/test_installer_script.py`
    - `desktop/tests/test_frozen_runtime.py`
    - `docs/release/pilot-builds.md`
    - `.cursor/plans/plan-installation.md` (round 20 only, plus this bullet and the round-20 History line)
  - **Composer to run:**
    1. The full desktop suite. Expected **5742 passed / 23 skipped** (+15: `test_preflight_refusals` +3; `test_the_source_tree_is_checked_whole_before_waf` +1; `test_a_defender_detection_fails_the_audit_cli` +3; `test_the_source_state` +4; `test_the_build_writes_it_beside_the_setup_and_sums_it` +1; installer +3, one renamed; the frozen-runtime test renamed, 0).
    2. The ISCC 6.7.3 compile re-check with the placeholder command, since `scribe.iss`'s `[Code]` changed.
  - **Then:** codex confirmation round 21 over the 7 files above.
  - **Not touched:** app source, the extension, `release.yml`, `ci.yml`, git refs and the main checkout.
- **EXECUTOR stage-3 leg i3-x8 (2026-10-03T04:12:03+10:00) — composer suite 5 was RED with 1 failure (5741 passed / 23 skipped), a test-harness defect, now fixed as a class; ruff clean, mypy clean (58 source files):**
  - **The failure:** `test_preflight_refusals[status fails-…]` got the commit refusal. The fake `_Runner` matched keys as substrings of the whole command line, and pytest's temporary folder for that case is named `…_status0`, so `git -C <that folder>\pyinstaller-src rev-parse HEAD` answered with the `status` key's exit 128.
  - **The fix:** `desktop/tests/test_build_release.py` `_names` / `_Runner` now match a key against a command word, or the name and stem of its last path part, never part of a path. The new `test_the_fake_runner_matches_words_never_paths` guards it. `build-release.py` is UNCHANGED: a failing `git status` already refuses, fail-closed, after the commit check. Recorded under round 20 PR-HIGH-001 as a fix-delta correction.
  - **Recorded:** the composer's ISCC 6.7.3 re-check of round 20's `scribe.iss` ("Successful compile (2.235 sec)") on Task 3.4.
  - **Composer to run:** the full desktop suite. Expected **5743 passed / 23 skipped**: the 5742 expected before plus this leg's guard test.
  - **Then:** codex confirmation round 21 over leg i3-x7's 7 files (this leg touched only `test_build_release.py` and the plan).
  - **Not touched:** `build-release.py`, `scribe.iss`, app source, the extension, git refs and the main checkout.
- **EXECUTOR stage-4 leg i4-x1 (2026-10-03T04:51:22+10:00) — Phase H: H.1 docs written (🟨, closes with H.2), H.2 /review-loop round 22 run and all 31 findings Applied; ruff clean, mypy clean (58 source files); ENDS composer-run:**
  - **H.1 (C9, one class):** threat model (new "Installation" section, channel-aware EXCLUSIONS, residues (g)/(i)/(l), Surface 17, boundaries 2–3), data-flow map (Components rows, flows 1, 5, 8, 9 (a)/(c), 19, 22, new 23 and 24, non-flows), retention schedule (new "Installation" table, the per-channel rows, the C5 backup wording), incident process, `docs/lessons.md`, `docs/design-system.md`, `docs/practice/downtime-procedure.md` and `privacy-information.md`, `docs/testing/shipping-gate-config/README.md`, `AGENTS.md` (two channels, installed-app steps, the developer build's steps, a packaging pointer, gpt-oss → Qwen3-4B-Instruct-2507), `PLAN.md` (Phase 7 delivery note: BUILT, NOT YET INSTALLED, with the still-to-run list), `CHANGELOG.md` (one Phase H line), `scripts/README.md`, `extension/KEY.md`, `docs/release/pilot-builds.md`. `Last Session` untouched.
  - **Round 22 (H.2 pass 1):** 0 CRIT / 0 HIGH / 3 MED / 28 LOW, 1 dropped; full record under Round 22. Code and test changes: `release.yml` (build/attest job split; only `attest` holds `id-token: write`), `scribe.iss` (Finish-page note for a foreign policy value; a comment), `register-native-host.py` (WinError 5 is "in use" when deleting), the `benchmark.py` docstring, and tests in `test_release_workflow.py`, `test_frozen_runtime.py`, `test_installer_script.py`, `test_register_native_host.py`, `test_integration_no_sockets.py`, `test_build_spec.py`. Plan: D11 and C8 AS-BUILT notes.
  - **Composer to run:**
    - The full desktop suite. Expected **5754 passed / 23 skipped** (5743 + 11: `test_release_workflow.py` +2, `test_frozen_runtime.py` +3, `test_installer_script.py` +4, `test_register_native_host.py` +2; `test_build_spec.py` and `test_integration_no_sockets.py` changed in place, same counts).
    - The ISCC 6.7.3 compile of `packaging/scribe.iss` (its `[Code]` `CurPageChanged` changed).
    - `npm run qa` is NOT needed (no extension source change; `extension/KEY.md` only).
  - **Then:** resume me for round 23 (the H.2 re-review, loop round 2 of cap 3), then H.3 `/simplify` and H.4 `/security-review`.
  - **Still to run, never faked (named in PLAN.md's delivery note and AGENTS.md):** Task 2.6 (dev models copy), 3.1 (hashed build lock), 3.3 (models manifest), 3.2/3.5 (a real build), 3.6 (workflow pins, push, first CI run — `release.yml` now also has `actions/download-artifact@PIN-REQUIRED`), the Inno Setup licence question, Phase P.
  - **rec for the composer (not built; scope):** an optional free-space pre-check in the installer's `PrepareToInstall` would shrink round 22 LOW-006's part-way-upgrade residue; record it as a later improvement, not Phase H work.
  - **Not touched:** app source beyond the one docstring, the extension source, git refs and the main checkout.
- **EXECUTOR stage-4 leg i4-x2 (2026-10-03T05:09:40+10:00) — round 22 CLOSED on the composer's green suite; round 23 (H.2 pass 2) found 1 MED + 4 LOW, all Applied; ruff clean, mypy clean (58 source files); ENDS composer-run:**
  - **Recorded:** composer suite after leg i4-x1 — pytest 5754 passed / 23 skipped (exactly as expected), ruff and mypy clean; the ISCC 6.7.3 compile of the changed `scribe.iss` "Successful compile (2.937 sec)", exit 0 — on round 22 and Task 3.4.
  - **Round 23:** MED-001, the attestation-visibility precondition. GitHub attests only a public repository, or a private one on Enterprise Cloud, and this repository's visibility is unrecorded. It is now Task 3.6 step 0, a practitioner network check that stops for a D7 decision if attestation cannot work; docs reconciled. LOW-001: the Status remedy for a broken per-user link. LOW-002: the bundle self-check is bounded at 120 s. LOW-003: the CI Inno install's exit check and a named refusal for a missing tool. LOW-004: a lesson sibling.
  - **Files this leg:** `desktop/src/scribe_desktop/status.py`, `scripts/build-release.py`, `.github/workflows/release.yml`, `desktop/tests/test_frozen_runtime.py`, `desktop/tests/test_build_release.py`, `desktop/tests/test_release_workflow.py`, `docs/design-system.md`, `docs/practice/downtime-procedure.md`, `docs/lessons.md`, `docs/security/threat-model.md`, `docs/release/pilot-builds.md`, `PLAN.md`, `AGENTS.md`, the plan.
  - **Composer to run:** the full desktop suite. Expected **5758 passed / 23 skipped** (5754 + 4: `test_frozen_runtime.py` +1, `test_build_release.py` +2, `test_release_workflow.py` +1). No ISCC compile (no `.iss` change) and no `npm run qa` (no extension change).
  - **Then:** resume me for round 24 (H.2 pass 3 = loop round 3 of cap 3), then H.3 `/simplify` and H.4 `/security-review`.
  - **For the practitioner, new (Task 3.6 step 0, network, before any pin):** `gh repo view eliemokbel3-hub/Recording-clinic-software --json visibility`. If `PRIVATE` on a personal plan, D7 needs a decision (public repository, or another provenance route) before the build of record can exist.
- **EXECUTOR stage-4 leg i4-x3 (2026-10-03T05:24:43+10:00) — round 23 CLOSED on the composer's green suite (5758 / 23); round 24 CONVERGED the H.2 loop; H.3 (round 25) and H.4 (round 26) run; 8 LOW Applied in all; ruff clean, mypy clean (58 source files); ENDS composer-run:**
  - **Recorded:** the composer's visibility check — the repository is PUBLIC (2026-10-03). Task 3.6 step 0 (kept as a re-check), External Findings, threat-model residue (5), `pilot-builds.md`, PLAN.md and AGENTS.md state the fact.
  - **Round 24 (H.2 pass 3):** 1 🆕 LOW — the benchmark worker's admission now also requires the seconds to parse. `/review-loop` CONVERGED at loop round 3 of cap 3 (no CRIT/HIGH/MED). **No cap raise is warranted.**
  - **Round 25 (H.3 `/simplify`):** SIMP-001 one spelling of the shipped whisper model (`benchmark.SHIPPED_WHISPER_MODEL`, read by `transcription` and `build-release.py`), SIMP-002 `instance_guard_root` via `data_root`, SIMP-003 the WER tuples. 4 candidates left alone (listed in the round).
  - **Round 26 (H.4 `/security-review`):** SEC-001 the extension builds before the bundle audit; SEC-002 every `release.yml` action is `@PIN-REQUIRED # <release>` (`checkout`, `setup-python`, `setup-node` too) and no npm cache — Task 3.6 step 1 now names six pins; SEC-003 a network-share manifest or launcher is never touched (`install_layout.is_unc_path`, the one definition); SEC-004 curly quotes refused in the Defender scan path.
  - **Files this leg:** `desktop/src/scribe_desktop/{benchmark.py, transcription.py, install_layout.py, exclusions.py, speaker_embedding.py, language_model.py, status.py, native_host.py}`, `scripts/build-release.py`, `.github/workflows/release.yml`, `desktop/tests/{test_frozen_runtime.py, test_build_release.py, test_release_workflow.py}`, `docs/security/{threat-model.md, data-flow-map.md, incident-process.md}`, `docs/release/pilot-builds.md`, `PLAN.md`, `AGENTS.md`, the plan.
  - **Composer to run:** the full desktop suite. Expected **5771 passed / 23 skipped** (5758 + 13: `test_frozen_runtime.py` +6 — 1 argv case, 2 + 1 Status network-path cases, 2 host-log cases; `test_build_release.py` +7 — the whisper single-source guard, the stage-two order, 5 quote cases; `test_release_workflow.py` ±0 — one test replaced, two renamed, the pin test still skips by name). No ISCC compile (no `.iss` change); no `npm run qa` (no extension change).
  - **Then:** resume me to close rounds 24–26 on that suite, mark H.1–H.4 🟩, update Overall Progress and END `phase-complete` with the H.5 slice lists. No further review round is planned unless the suite is red.
- **EXECUTOR stage-4 leg i4-x4 (2026-10-03T05:31:40+10:00) — Phase H's in-session work CLOSED; ENDS phase-complete (plan-only leg, no review round):**
  - **Recorded:** composer suite after leg i4-x3 — ruff clean, mypy clean, pytest **5771 passed / 23 skipped** (exactly as expected). Rounds 24, 25 and 26 Closed on it.
  - **Markers:** H.1, H.2, H.3 and H.4 are 🟩 (each line says what met it); H.5 stays 🟥 (the composer's). Overall Progress is 27 of 39 task lines, **69%**.
  - **H.5 scope:** `git diff 9f43f8c` (the committed Phases 1–3 plus the uncommitted Phase H changes in the working tree) — **98 files**, excluding `.cursor/`. At ≤ 15 files a slice, the three named groups need **EIGHT slices** (a1–a2, b1–b3, c1–c3); every file is in exactly one. A slice's reviewer may READ any file outside it for context.
    - **(a1) build, installer and CI — 15:** `packaging/scribe.iss`, `packaging/scribe.spec`, `packaging/entry_app.py`, `packaging/entry_host.py`, `packaging/speaker-model-ATTRIBUTION.txt`, `scripts/build-release.py`, `scripts/lock-build-requirements.py`, `.github/workflows/release.yml`, `.gitattributes`, `docs/release/pilot-builds.md`, `desktop/tests/test_installer_script.py`, `test_build_release.py`, `test_build_spec.py`, `test_build_lock.py`, `test_release_workflow.py`.
      - Focus: the installer fails closed and never says "installed" falsely (process check, the `{app}` refusal, model hashes before AND after the copy, HKLM-only writes, the policy's ours/foreign logic and its Finish lines, `[InstallDelete]` scope, uninstall keeps the data — C3/C4); `build-release.py`'s preflight, the order (extension build → bundle audit → Defender → compile), the bounded self-check, `_run`'s refusals, the Defender path quoting; `release.yml`'s two jobs and permissions, every action `@PIN-REQUIRED`, no cache, the Inno hash and exit checks; that each test pins behaviour, not just text.
    - **(a2) source-run scripts — 10:** `scripts/register-native-host.py`, `scripts/setup-models.py`, `scripts/check-installed-sockets.py`, `scripts/speaker-embedding-smoke.py`, `scripts/README.md`, `.gitignore`, `desktop/tests/test_register_native_host.py`, `test_setup_scripts.py`, `test_check_installed_sockets.py`, `test_display_name.py`.
      - Focus: the register script is dev-only; `--unregister` touches HKCU only, the one stray production key and exactly two named files (C2/C8); the in-use handling (32 on copy, 32/5 on delete); `setup-models.py --root` fetches only into its root; the socket check's classification; C7 wording (normal terminal, never an agent shell).
    - **(b1) layout, identity and the channel split — 15:** `desktop/src/scribe_desktop/install_layout.py`, `identity.py`, `pipe_server.py`, `pipe_client.py`, `framing.py`, `clinics.py`, `audit.py`, `past_sessions.py`, `session_store.py`, `practitioner_profile.py`, `desktop/tests/conftest.py`, `test_install_layout.py`, `test_identity.py`, `test_audit.py`, `test_integration_no_sockets.py`.
      - Focus: C2 — every production identity unchanged (host name, extension ID, origin, pipe prefix, folder name, keyring prefix, DPAPI descriptions, mutex); C8 — no dev path reaches `%LOCALAPPDATA%\ClinikoScribe` except `app.lock`; the channel only from `sys.frozen`; `is_unc_path`'s move (the one definition); the conftest sentinels (C6) and the no-sockets children pinned to the production channel.
    - **(b2) start-up, write guard and registry readers — 13:** `desktop/src/scribe_desktop/app.py`, `native_host.py`, `exclusions.py`, `status.py`, `draft_write.py`, `note_config.py`, `logging_setup.py`, `desktop/tests/test_frozen_runtime.py`, `test_exclusions.py`, `test_dev_write_guard.py`, `test_draft_write.py`, `test_status_and_app.py`, `test_write_lines.py`.
      - Focus: the start-up order (offline self-check → install-folder refusal → benchmark worker → logging and the guard) and that the refusal writes nothing; the dev write guard fails closed and production never reads `dev.json` (D4); Chrome-order registry readers (D9), the per-user override and broken-winner lines, the network-share refusal (SEC-003); channel-aware WER and backup checks warn only (D10/D6); type-name-only errors.
    - **(b3) the extension's channel — 10:** `extension/src/channel.ts`, `extension/src/channel.dom.test.ts`, `extension/src/manifest.ts`, `extension/src/manifest.test.ts`, `extension/src/protocol.ts`, `extension/src/test/build-defines.ts`, `extension/vite.config.ts`, `extension/vitest.config.ts`, `extension/KEY.md`, `scripts/generate-extension-key.py`.
      - Focus: the release build answers only `com.scribe.cliniko_host` and the dev build only `com.scribe.cliniko_host_dev`; the manifest key and ID per mode; the key script never prints or writes private-key content anywhere but the gitignored file; the tests' defines match the real build's. (Composer: `npm run qa` is unchanged since Phase 1 — 13 files / 313 tests.)
    - **(c1) benchmark, models and UI — 15:** `desktop/src/scribe_desktop/benchmark.py`, `language_model.py`, `speaker_embedding.py`, `speech.py`, `transcription.py`, `ui/hardware_check.py`, `ui/microphone.py`, `ui/main_window.py`, `ui/models.py`, `ui/note.py`, `ui/practitioner.py`, `ui/transcript.py`, `desktop/tests/test_benchmark.py`, `test_hardware_check.py`, `test_language_model_runtime.py`.
      - Focus: the benchmark worker's admission (env + exact argv + parseable seconds) and its one-line error boundary; the prose-stage timing and verdict (wall seconds, D11; never model text); `SHIPPED_WHISPER_MODEL` as the one spelling; models read from the channel's root, re-verified where the docs say; every remedy line per channel; the dev-only Status checkbox and its save-failure path.
    - **(c2) model and UI tests — 8:** `desktop/tests/test_speaker_embedding.py`, `test_speech.py`, `test_transcription.py`, `test_ui_models.py`, `test_ui_screens.py`, `test_ui_writing_style.py`, `test_ui_learn_style.py`, `test_ui_encounter.py`.
      - Focus (read with c1's sources): C6 — no test reads the real registry, `LOCALAPPDATA`, a real model or a real Chrome; each changed assertion still pins the behaviour it names; the channel and frozen pins are set where a test depends on them.
    - **(c3) docs — 12:** `docs/security/threat-model.md`, `docs/security/data-flow-map.md`, `docs/security/retention-schedule.md`, `docs/security/incident-process.md`, `docs/design-system.md`, `docs/lessons.md`, `docs/practice/downtime-procedure.md`, `docs/practice/privacy-information.md`, `docs/testing/shipping-gate-config/README.md`, `AGENTS.md`, `PLAN.md`, `CHANGELOG.md`.
      - Focus: C9 — each claim states only what the code enforces, with residues named (check against the sources in a1–c1); "BUILT, NOT YET INSTALLED", never a claim of an installed app; backups "marked to be left out", never "excluded" (C5); the practice documents in plain English with no file names; the repository-visibility fact (public, 2026-10-03) and the re-check; the user-visible strings quoted equal to the code's constants.
  - **Still open, never faked:** Task 2.6 (dev models), 3.1 (build lock), 3.3 (models manifest), 3.2/3.5 (a real build), 3.6 (six action pins and the Inno hash, the visibility re-check, push, first CI run), the Inno licence question, Phase P.
  - **Not touched this leg:** any code, test or doc file — the plan only.
- **EXECUTOR stage-4 leg i4-x6 (2026-10-03T06:06:28+10:00) — round 27 LEG 2 (/fix): 11 Applied, 1 Include in plan (Task H.6 `[pending-hardening]`); ruff clean, mypy clean (58 source files), history-check OK (27 + 27); Round status stays Open for codex confirmation round 28; ENDS composer-run:**
  - **Facts:** `packaging/scribe.iss:376` `GetCustomSetupExitCode` (9 = models incomplete, 10 = the clinic-only policy left; 1–8 are Inno's) and the new `KeptDataMessage` (no retention claim); `install_layout.py:247` `is_unc_path` normalises `/` to `\` before the prefix test; `speech.py:179/376` and `transcription.py:925/985` now call it; `benchmark.py:120` `_WORKER_PATH_OPTIONS`, `:197` `list_whisper_candidates` (`[]` for a network root), `:464` `run_single`'s refusal, `:576` `run_all`'s refusal, and `is_worker_argv` refuses a network path value; `scripts/generate-extension-key.py:39/42` `ALLOWED_KEY_FILES` / `resolve_out` (a usage error before any key I/O; no key content read or printed by this leg); plan Task H.6 at `### Phase H` (a 40th task line, so Overall Progress is 27 of 40, **68%**).
  - **Files changed this leg (the confirmation slice):** `packaging/scribe.iss`, `desktop/src/scribe_desktop/install_layout.py`, `desktop/src/scribe_desktop/speech.py`, `desktop/src/scribe_desktop/transcription.py`, `desktop/src/scribe_desktop/benchmark.py`, `scripts/build-release.py` (docstring), `scripts/setup-models.py` (docstring), `scripts/generate-extension-key.py`, `scripts/register-native-host.py` (docstring, comment, refusal text), `scripts/README.md`, `desktop/requirements-ml-prose.txt` (comment only), `desktop/tests/test_installer_script.py`, `desktop/tests/test_frozen_runtime.py`, `desktop/tests/test_install_layout.py`, `desktop/tests/test_benchmark.py`, `desktop/tests/test_generate_extension_key.py` (NEW), `desktop/tests/test_register_native_host.py` (skip reason), `docs/security/threat-model.md`, `docs/security/data-flow-map.md`, `docs/security/retention-schedule.md`, `docs/design-system.md`, `AGENTS.md` (step 5 only; Last Session untouched), and this plan.
  - **Composer to run:**
    - The full desktop suite. Expected **5805 passed / 23 skipped** (5771 + 34: `test_installer_script.py` +1; `test_frozen_runtime.py` +9 — 2 + 2 mixed-form manifest cases, +1 launcher case, +3 not-the-worker shapes, +1 packaged network worker; `test_install_layout.py` +11 — `TestIsUncPath` 5 network + 6 local; `test_benchmark.py` +5 — 2 network-root, 2 `run_single`, 1 `run_all`; `test_generate_extension_key.py` +8 new).
    - The ISCC 6.7.3 compile re-check of `packaging/scribe.iss` (a new `[Code]` event function and a changed string).
    - `npm run qa` is NOT needed (no extension change).
  - **Then:** codex confirmation round 28 over the files above (one slice of ≤ 15 code/test files plus the docs as a second slice if needed); Task H.6 waits on a scoped `/review-plan` to clear its `[pending-hardening]` marker.
  - **Not touched:** the extension, `release.yml`, `ci.yml`, git refs and the main checkout.
- **EXECUTOR stage-4 leg i4-x8 (2026-10-03T06:23:02+10:00) — round 28 LEG 2 (/fix): all 5 LOW Applied with their siblings; ruff clean, mypy clean (58 source files), history-check OK; Round status stays Open for codex confirmation round 29; ENDS composer-run:**
  - **Recorded:** the composer suite after leg i4-x6 was green (5805 passed / 23 skipped; ISCC 6.7.3 "Successful compile (3.344 sec)"), and round 27 is closed on it and on round 28's confirmation.
  - **Facts:**
    - `install_layout.py:252` `_DEVICE_PREFIXES` and `:255` `is_unc_path` (the allow-list); `:158` `instance_guard_root`'s docstring.
    - `benchmark.py:123` `_TEMP_VARIABLES`, `:444` the sample-writer guard, `:598` the temporary-folder pre-check.
    - `tests/conftest.py:150` `NETWORK_IO_METHODS`, `:162` `forbid_network_io`.
    - `packaging/scribe.iss:213` (comment only).
    - `docs/security/threat-model.md:215`; flow 6 of the data-flow map.
  - **Files changed this leg (the round-29 confirmation slice):** `desktop/src/scribe_desktop/install_layout.py`, `desktop/src/scribe_desktop/benchmark.py`, `desktop/tests/conftest.py`, `desktop/tests/test_install_layout.py`, `desktop/tests/test_benchmark.py`, `desktop/tests/test_frozen_runtime.py`, `desktop/tests/test_speech.py`, `desktop/tests/test_transcription.py`, `packaging/scribe.iss` (comment only), `docs/security/threat-model.md`, `docs/security/data-flow-map.md`, and this plan.
  - **Composer to run:**
    - The full desktop suite. Expected **5835 passed / 23 skipped** (5805 + 30):
      - `test_install_layout.py` +24: 6 extended-local, 10 refused device forms, 8 tripwire self-tests;
      - `test_benchmark.py` +6: 4 temporary-folder sources, 2 sample-writer targets;
      - `test_frozen_runtime.py`, `test_speech.py` and `test_transcription.py` ±0: changed in place.
    - **No ISCC re-compile is owed:** `scribe.iss` changed in a `//` comment only, with no `[Code]` statement, section or string changed.
    - `npm run qa` is not needed (no extension change).
  - **Then:** codex confirmation round 29 over the 11 files above (one slice).
  - **Not touched:** the extension, `release.yml`, `ci.yml`, `AGENTS.md`, git refs and the main checkout.
- **EXECUTOR stage-4 leg i4-x10 (2026-10-03T06:33:41+10:00) — round 29 LEG 2 (/fix): PR-LOW-033 Applied with every enumerated sibling (classes (a) and (b)); ruff clean, mypy clean (58 source files), history-check OK; Round status stays Open for codex confirmation round 30; ENDS composer-run:**
  - **Recorded:** the composer suite after leg i4-x8 was green (5835 passed / 23 skipped). Round 28 was closed on it and on round 29. Leg i4-x9 (LEG 1) wrote round 29's tuples, verification only.
  - **Files changed this leg (the round-30 confirmation slice):** `desktop/tests/test_transcription.py`, `desktop/tests/test_speaker_embedding.py`, `desktop/tests/test_speech.py`, `desktop/tests/test_language_model_runtime.py`, and this plan (round 29's records, plus the `[2026-10-03 correction]` line under round 28's PR-LOW-030 tuple). No production code, no docs.
  - **The six tests now on `forbid_network_io`:**
    - `test_transcription.py::test_unc_localappdata_reports_unavailable_without_io`;
    - `test_speaker_embedding.py::test_missing_and_unc_paths_refused_before_onnxruntime_import` and `::test_unc_availability_probe_refuses_without_io`;
    - `test_speech.py::test_unc_availability_probe_refuses_without_io`;
    - `test_language_model_runtime.py::test_unc_path_is_refused_before_the_factory` and `::test_unc_path_reports_unavailable_without_touching_it`.
  - **Composer to run:**
    - The full desktop suite. Expected **5835 passed / 23 skipped**, unchanged: no test was added or removed, and six were changed in place.
    - No ISCC compile and no `npm run qa` (no installer or extension change).
  - **Then:** codex confirmation round 30 over the 4 test files (one slice).
  - **Not touched:** app source, packaging, docs, the extension, `AGENTS.md`, git refs and the main checkout.
- **EXECUTOR stage-4 leg i4-x12 (2026-10-03T06:42:34+10:00) — round 30 LEG 2 (/fix): PR-LOW-034 Applied (comments only); the peer pass closes WITHOUT round 31 (cap verdict, `h5-peer-close`); H.5 🟨 "closes on the composer suite"; ruff clean, mypy clean (58 source files), history-check OK (30 + 30); ENDS composer-run:**
  - **Recorded:** the composer suite after leg i4-x10 was green (5835 passed / 23 skipped); round 29 was closed on it and on round 30. Leg i4-x11 (LEG 1) wrote round 30's tuples.
  - **Files changed this leg:** `desktop/tests/conftest.py` (the `forbid_network_io` docstring), `desktop/tests/test_language_model_runtime.py`, `desktop/tests/test_speech.py`, `desktop/tests/test_speaker_embedding.py`, `desktop/tests/test_transcription.py`, `desktop/tests/test_frozen_runtime.py`, `desktop/tests/test_benchmark.py` (comments only), and this plan (round 30's records, H.5's marker and notes). No code line changed.
  - **Markers:** H.5 is 🟨 (closes on the composer suite; the composer flips it); H.6 is 🟥 (hardened in place by a scoped `/review-plan` on 2026-10-03; marker removed, ready for `/execute`). Overall Progress stays 27 of 40 task lines, **68%**; it becomes 28 of 40 (**70%**) when H.5 flips.
  - **Composer to run:** the full desktop suite. Expected **5835 passed / 23 skipped**, unchanged (comments only). No ISCC compile and no `npm run qa`. If it is green, flip H.5 to 🟩 and close round 30.
  - **Phase H summary (for AGENTS.md / CHANGELOG):**
    - **What Phase H changed:**
      - **H.1 docs:** the docs now state the installation as BUILT, NOT YET INSTALLED. The threat model gained an "Installation" section and channel-aware exclusions; the data-flow map gained flows 23 and 24; the retention schedule gained an "Installation" table; the incident process, `docs/lessons.md`, `docs/design-system.md`, `docs/release/pilot-builds.md` and the practice documents were updated.
      - **Hardening fixes:**
        - The release workflow's build and attest jobs are split, and only `attest` holds `id-token: write`. Every action is `@PIN-REQUIRED`, with no npm cache. The Inno install is exit-checked.
        - `build-release.py` builds the extension BEFORE the bundle and extension audits, then runs the Defender scan, then compiles. The packaged self-check is time-bounded, a missing tool is a clear error, and curly quotes are refused in the Defender path.
        - The installer exits 9 (a damaged model) or 10 (the clinic-only policy left behind) instead of 0, and its uninstall message claims no retention period.
        - **The network-path class:**
          - One `install_layout.is_unc_path` decides every network path. It normalises mixed slashes, and for the `\\?\`, `\\.\` and `\??\` forms it treats only a drive letter as local.
          - It is applied by the Chrome-link registry readers (the Status tab and the host log), the model loaders and probes, and the benchmark: its models root, model and audio paths, worker arguments, temporary folder and sample writer.
          - A shared test tripwire, `forbid_network_io`, backs the refusal tests.
        - The Status tab gives a remedy for a broken per-user Chrome link. The benchmark worker's argument check also requires the seconds to parse. There is one spelling of the shipped whisper model.
        - The key script's `--out` accepts only the two gitignored key files. The register script treats WinError 5 as "in use"; its space-free folder is described as a conservative guard.
        - Task 3.6 step 0 records the repository visibility (public on 2026-10-03; re-check before pinning).
    - **Review rounds 22–30:**
      - H.2 `/review-loop`: rounds 22–24 (3 MED + 28 LOW → 1 MED + 4 LOW → 1 LOW), converged.
      - H.3 `/simplify`: round 25, 3 LOW.
      - H.4 `/security-review`: round 26, 0 CRIT/HIGH/MED, 4 LOW.
      - H.5 codex `gpt-6-astra` medium, rounds 27–30 (12 → 5 → 1 → 1, all LOW after verification). The first pass was sliced 8 ways over the 98-file diff.
      - Every finding was Applied except round 27's PR-MED-022, which went to Task H.6.
      - Suite: 5743 at the Phase 3 close, 5835 passed / 23 skipped now.
    - **Still open for the PRACTITIONER (never faked):**
      - Task 2.6 (the dev models copy, normal terminal);
      - 3.1 (the hashed build lock);
      - 3.3 (the models manifest);
      - 3.2 / 3.5 (a real build with `--audit`);
      - 3.6 (the visibility re-check, six action pins and the Inno installer hash, push, the first CI run);
      - the Inno Setup "Non-commercial use only" licence question;
      - ~~the frozen-vs-everyday benchmark on mains power~~ — done 2026-10-02 (0.676 frozen vs 0.589 everyday; PASS);
      - deleting `C:\scribe-iss-check`;
      - Phase P (the first install on this computer).
    - **Hardened, ready to build:** Task H.6 (the conftest-level pin of `install_layout.models_root` for every test, closing PR-MED-022's C6 class) was hardened in place by a scoped `/review-plan` on 2026-10-03 and its `[pending-hardening]` marker removed; it is the next buildable task (`/execute`, single session — five test files, conftest, pyproject, three docs).
  - **Not touched:** app source, packaging, docs, the extension, `AGENTS.md`, `CHANGELOG.md`, git refs and the main checkout.
- **EXECUTOR stage-3 leg i3-x9 (2026-10-03T10:02:57+10:00) — the first `Release` run's failure fixed as round 31 (MED-001, Applied; round Open until the lock is regenerated and `Release` re-runs green); Task 3.1 REOPENED 🟨; ruff clean, mypy clean (58 source files); ENDS composer-run:**
  - **Cause:** `Release` run 37079569271 failed with `BackendUnavailable: Cannot import 'hatchling.build'`. The PyInstaller source installs with `--no-build-isolation` (kept — it is the control), and the lock did not carry the backend.
  - **Changed:** `scripts/lock-build-requirements.py` (hatchling 1.32.4, pathspec 1.1.1, pluggy 1.6.0, tomlkit 0.15.1, trove-classifiers 2026.9.21.13 in `BUILD_TOOL_PINS`; `hatchling` in `EXTRA_REQUIREMENTS`); `scripts/build-release.py` (`PYINSTALLER_BUILD_REQUIRES`, two preflight refusals, `pyinstaller_build_requires`); `scripts/README.md`; `desktop/tests/test_build_release.py` (+6 tests: 4 preflight cases, 2 stage-one); `desktop/tests/test_build_lock.py` (+1 test, one renamed, the committed-lock check widened); this plan (Tasks 3.1 and 3.6, round 31). `desktop/requirements-build.txt` NOT touched.
  - **Expected composer suite:** the previous count + 6 passed, **1 FAILED** — `test_build_lock.py::TestLockCoversTheRuntime::test_the_committed_lock_covers_the_runtime_and_is_fully_hashed` (its first assertion: `missing_runtime_dependencies` returns `['hatchling']`), by design until the lock is regenerated — and skips unchanged. After regeneration: + 7 passed, 0 failed.
  - **PRACTITIONER STEP (normal PowerShell at `C:\scribe-build`; network):**
    - `.venv\Scripts\python.exe -m pip freeze --all | Out-File -Encoding utf8 "$env:TEMP\proven-freeze.txt"`
    - `.venv\Scripts\python.exe scripts\lock-build-requirements.py --constraints "$env:TEMP\proven-freeze.txt"`
    - Report the "wrote N pinned wheels" line (most likely 59) or the refusal. Then the composer commits the lock, re-runs the suite, pushes `main` and re-dispatches `Release`.
  - **Residue:** a hatchling build hook's extra requirements (`get_requires_for_build_wheel`) are proven only by the next `Release` run.
  - **Doc item (not edited, outside this leg's brief):** `docs/security/data-flow-map.md` flow 9 (c) still says "none of it run yet"; a `Release` run has now run (and failed). Update it at the next docs pass or when the build of record exists.
- **EXECUTOR stage-4 leg i4-x13 (2026-10-03T11:56:01+10:00) — Task H.6 BUILT (🟨) and `/review-loop` CONVERGED (rounds 32–33, loop round 2 of cap 3; 3 LOW Applied, then 0); ruff clean, mypy clean (58 source files), history-check OK (33 + 33); ENDS composer-run:**
  - **What changed:**
    - An autouse `pinned_models_root` in `desktop/tests/conftest.py` pins `install_layout.models_root` for every test to a fresh, empty per-test folder (from a session `models_root_factory`), outside `tmp_path` and under pytest's base temp. Supporting helpers: `use_models_root`, and `record_path_io` for tripwire (d).
    - The `real_models_root` marker is registered in `desktop/pyproject.toml`. It is applied to exactly step 2's set, plus the two marker tripwires, and a source scan pins that set.
    - Step 3's builders use the pin.
    - Three UNC-refusal tests that the pin would have hollowed now pin a network models root. This is interpretation call (iii) on the H.6 line, found from the code, not by a failure.
    - Tripwires (a)–(d) are in place, plus a source scan of `src/` and `scripts/` that pins every caller of the resolver (10 functions).
    - Docs: the threat model, AGENTS.md, `docs/lessons.md` and C6.
  - **Files changed:**
    - `desktop/pyproject.toml`, `desktop/tests/conftest.py`;
    - the test files `test_frozen_runtime.py`, `test_install_layout.py`, `test_language_model_runtime.py`, `test_speaker_embedding.py`, `test_speech.py`, `test_transcription.py`, `test_ui_models.py`, `test_ui_screens.py`, and `test_hardware_check.py` (one comment, round 32 LOW-002's sibling);
    - `docs/security/threat-model.md`, `docs/lessons.md`, `AGENTS.md`, and this plan.
    - No app source changed. The extension, packaging and the main checkout were not touched.
  - **Composer to run:** the full desktop suite. Expected **5872 passed / 9 skipped**: 5856 plus 16 new tests (15 in `test_frozen_runtime.py`, 1 in `test_ui_screens.py`; one test renamed). The 9 skips are the directory-symlink variants, and the real-ML legs run on the filled dev root, including the new `test_a_real_ml_body_pin_lands_after_and_wins`. No `npm run qa` and no ISCC compile.
  - **If a test fails:** a failure outside step 2's set is a builder to migrate under the pin, never a reason to mark. The one expected risk is named on the H.6 line: a test that passed only because this computer's production models folder is full. Resume me with the failure.
  - **If green:** flip H.6 to 🟩, close round 32, and recompute Overall Progress (80% in the header today, so H.6 adds one task line).
  - **Codex confirmation slice:** two slices, each under 15 files.
    - Slice 1, code: `desktop/tests/conftest.py`, `desktop/pyproject.toml`, `test_frozen_runtime.py`, `test_install_layout.py`, `test_language_model_runtime.py`, `test_speaker_embedding.py`, `test_speech.py`, `test_transcription.py`, `test_ui_models.py`, `test_ui_screens.py`, `test_hardware_check.py`.
    - Slice 2, docs: `docs/security/threat-model.md` (the sentinel sentence near L2871), `AGENTS.md` (the installation bullet), `docs/lessons.md` (the 2026-09-24 lesson), and this plan's C6 and H.6 lines.
  - **Open gates:** none.
- **EXECUTOR stage-5 leg i5-x1 (2026-10-03T16:34:59+10:00) — round 35 MED-001 (the first-recording failure on the installed 0.1.0) FIXED and reviewed. The `/review-loop` paused in round 36 at one MUST-PAUSE gate; 8 LOW were Applied. ruff clean; mypy clean (59 source files). ENDS must-pause:**
  - **Diagnosis** (detail in round 35 MED-001):
    - The failure arrived about 13 ms after the `recording` line, not 1 s later; the 1 s is `_fail_locked`'s in-lock live-stop bound. A full chunk cannot have been written by then, and the queue cannot have filled.
    - Most likely cause: a PortAudio dropped-frames status (`CaptureOverflowError`). The capture callback (Python, needs the GIL) was starved while the live worker made the process's first import of numpy, onnxruntime and faster-whisper from a fresh, unscanned install. Supporting evidence: the worker could not stop 1 s later; a same-process retry re-imported nothing and passed.
    - The log cannot tell this from device loss, or GIL from loader lock.
  - **Changes:**
    - The new `capture_failure` log line: the type name plus a fixed `detail_code` word, never the message.
    - New module `ml_warmup.py`: the start-up import warm-up, which `app.main` starts after the guard.
    - `MainWindow(live_ready=…)`: the live-worker factory returns None until the warm-up finishes. The controller accepts that and logs `live_transcriber state=not_attached`; the view shows a not-ready placeholder without the header.
    - Never-drop rule kept, with reasons. A larger PortAudio input latency is recommended as a follow-up; it needs a hardware smoke.
  - **Files:**
    - src: `audio_capture.py`, `session.py`, `ml_warmup.py` (new), `app.py`, `enrolment.py`, `ui/main_window.py`, `ui/models.py`, `ui/transcript.py`.
    - tests: `conftest.py`, `test_ml_warmup.py` (new), `test_audio_capture.py`, `test_live_session.py`, `test_ui_screens.py`, `test_exclusions.py`, `test_status_and_app.py`, `test_audit.py`, `test_hands_free.py`, `test_integration_no_sockets.py`.
    - docs: `docs/security/threat-model.md` (surface 11, "THE WARM-UP"), `docs/security/data-flow-map.md` (flow 14), `docs/design-system.md` (live transcript), `AGENTS.md` (the live-transcription pointer), and this plan.
    - The extension, packaging and the main checkout were not touched.
  - **Composer to run:**
    - The full desktop suite. Expected **5893 passed / 9 skipped** (5872 + 21 new):
      - 8 in `test_audio_capture.py`;
      - 5 in `test_live_session.py` (Windows-only, numpy);
      - 6 in `test_ml_warmup.py`;
      - 2 in `test_ui_screens.py`.
    - `test_integration_no_sockets.py::test_scribe_app_process_has_no_sockets` now performs the REAL warm-up imports in its child, so expect a few seconds more.
    - No `npm run qa` and no ISCC compile.
  - **If a test fails:** resume me with the output. I could not run pytest; an independent read-only review traced every new assertion and predicted no failure.
  - **Open gate (MUST-PAUSE), round 36 MED-001:** a Start made while the warm-up still runs withholds the live worker, but the warm-up's imports continue beside capture. The overlap is narrowed, not removed, and the window is unmeasured on a first launch after an install (now logged as `ml_warmup duration_ms`). Options:
    - (a) accept as a residue (as built);
    - (b) a bounded Start refusal while warming ("Clinic Scribe is still getting ready — start again in a moment", at most ~60 s after launch, then record without the live worker);
    - (c) an asynchronous wait-then-start.

    rec=(b) if the practitioner accepts a brief refusal after launch; otherwise (a), with the existing interim advice (a test recording after each install or update).
  - **Codex slices** (each under 15 files):
    - Slice 1, code: `audio_capture.py`, `session.py`, `ml_warmup.py`, `app.py`, `enrolment.py`, `ui/main_window.py`, `ui/models.py`, `ui/transcript.py`.
    - Slice 2, tests: the ten test files above.
    - Slice 3, docs: the four doc files plus this plan's rounds 35–36.
- **EXECUTOR stage-5 leg i5-x2 (2026-10-03T16:48:56+10:00) — round 36 MED-001 BUILT as the practitioner's option (b), a bounded Start refusal while the start-up warm-up runs. `/review-loop` CONVERGED (round 37, loop round 2 of cap 3; 4 LOW Applied, 2 dropped); ruff clean; mypy clean (59 source files); history-check OK (37 + 37). ENDS composer-run:**
  - **What changed:**
    - `ml_warmup.ImportWarmup.holds_start` uses an injectable clock and `START_HOLD_SECONDS` = 60.0. That is the practitioner's minute, and about ten times the frozen spike's cold load (5.3 s for Whisper, 6.9 s for prose). It holds only while the warm-up runs AND it began less than 60 s ago, so a hung warm-up never blocks recording longer than 60 s and a failed one holds nothing.
    - `SessionScreen.set_start_hold` / `start_held`. `on_start` refuses after the consent check, before clearing the tick (the tick is KEPT); `start_linked` refuses before clearing it. `ChromeBridge._start` refuses as `getting_ready`, right after the lock check. Every refusal comes before `SessionController.start`: no audit `begin`, no folder, no key.
    - The line on both surfaces is `START_GETTING_READY_MESSAGE`: "Clinic Scribe is still getting ready - start again in a moment." (and `CHROME_REFUSALS["getting_ready"]`).
    - Round 37 LOW-002: `MainWindow._enrolment_blocker` holds a voice enrolment too.
    - Wiring: `MainWindow(start_hold=…)`; `app.main` passes `warmup.holds_start`.
    - A Start admitted after the bound keeps the round-35 behaviour: no live worker.
    - Stated residue: the side panel clears its own tick on every Start press (extension behaviour shared by every refusal; the extension is not touched).
    - The PortAudio input-latency idea is recorded under Retained Follow-Up Items: not built, needs a real-hardware test.
  - **Files changed in this leg:**
    - src: `ml_warmup.py`, `ui/session_screen.py`, `ui/bridge.py`, `ui/models.py`, `ui/main_window.py`, `app.py`.
    - tests: `test_ui_bridge.py`, `test_ml_warmup.py`, `test_ui_screens.py`, `test_exclusions.py`, `conftest.py`, `test_integration_no_sockets.py`.
    - docs: `docs/security/threat-model.md`, `docs/security/data-flow-map.md`, `docs/design-system.md`, `AGENTS.md`, and this plan.
  - **Composer to run:**
    - The full desktop suite. Expected **5904 passed / 9 skipped**: 5893 plus 11 new tests (6 in `test_ui_bridge.py`, 4 in `test_ml_warmup.py`, 1 in `test_ui_screens.py`).
    - `test_scribe_app_process_has_no_sockets` still performs the real warm-up imports, now waiting at most 30 s before READY.
    - No `npm run qa` and no ISCC compile.
  - **If a test fails:** resume me with the output.
  - **If green:** close rounds 35–37 and commit as version 0.1.1. Before the P.3 build, run a 10-second test recording on the dev build: Start straight after launch should show the getting-ready line.
  - **Codex slices** for the WHOLE round 35–37 diff (`git diff e5e7c9f` plus the two untracked files), each under 15 files:
    - Slice 1, code (10): `desktop/src/scribe_desktop/audio_capture.py`, `session.py`, `ml_warmup.py` (new), `app.py`, `enrolment.py`, `ui/bridge.py`, `ui/main_window.py`, `ui/models.py`, `ui/session_screen.py`, `ui/transcript.py`.
    - Slice 2, tests (11): `desktop/tests/conftest.py`, `test_ml_warmup.py` (new), `test_audio_capture.py`, `test_live_session.py`, `test_ui_bridge.py`, `test_ui_screens.py`, `test_exclusions.py`, `test_status_and_app.py`, `test_audit.py`, `test_hands_free.py`, `test_integration_no_sockets.py`.
    - Slice 3, docs (5): `docs/security/threat-model.md` (surface 11, "THE WARM-UP"), `docs/security/data-flow-map.md` (flow 14), `docs/design-system.md` (the live transcript and the Start-waits bullet), `AGENTS.md` (the live-transcription pointer), and this plan's rounds 35–37, Task P.1's FAULT note and Retained Follow-Up Items.
  - **Open gates:** none.
- **EXECUTOR stage-5 leg i5-x3 (2026-10-03T16:59:36+10:00) — codex round 38 verified and fixed: 4 LOW, all CONFIRMED and Applied (`#### LEG 1 verified tuples` in round 38); ruff clean; mypy clean (59 source files). Round 38 stays Open until the composer suite and codex confirmation round 39. ENDS composer-run:**
  - **What changed:**
    - A01: the not-ready live placeholder no longer promises the recording is unaffected ("Live transcription is off for this recording - Clinic Scribe was still getting ready; transcribing after the recording instead."). Its comment now says such a Start comes only after the 60 s hold.
    - B01: the slow-load test proves all five chunks are in encrypted storage (`iter_chunks`, bounded `_wait`) while the load gate is still closed. The sleep is gone.
    - B02: the no-sockets startup child reports `warmup:<wait result>` on its READY line, and the parent requires `warmup:True`.
    - C01: the design system measures the 60 s hold from the warm-up's start.
  - **Files changed in this leg** (the confirmation slice for round 39): `desktop/src/scribe_desktop/ui/models.py`, `desktop/tests/test_live_session.py`, `desktop/tests/test_integration_no_sockets.py`, `docs/design-system.md`, and this plan's round 38 block.
  - **Composer to run:**
    - The full desktop suite. Expected **5904 passed / 9 skipped**: no new tests, two stricter ones.
    - No `npm run qa` and no ISCC compile.
  - **If a test fails:** resume me with the output.
  - **If green:** run codex round 39 over the five files above; close round 38 on its confirmation.
  - **Open gates:** none.
- **[SUPERSEDED by leg i5-x6 below — kept only for the concurrent-writer record; its file list, counts and next steps are restated there] EXECUTOR stage-5 leg i5-x5 (2026-10-03T20:27:07+10:00; it finishes leg i5-x4, which a CLI 401 cut off before anything was recorded): round 40's two LOW are CONFIRMED and Applied; /review-loop CONVERGED (rounds 41–42, 6 + 1 LOW Applied); ruff clean; mypy clean (59 source files). Round 40 stays Open. ENDS must-pause (gate `i5-x5-concurrent-writer`):**
  - **GATE (2026-10-03T20:27:07+10:00 onwards): a second process is editing this worktree while this leg runs**, most likely leg i5-x4's `claude -p`, which a 401 cut off but which was apparently not stopped.
    - After this leg's reads, `ui/session_screen.py`'s round-41 backstop changed from a `task.finished` handler to `except BaseException` inside the job (`return unexpected`).
    - The backstop test was renamed and rewritten (`test_a_discard_ended_by_a_non_exception_still_releases_the_hold`).
    - The threat model's sentence now reads "any `BaseException` sends the fixed reason".
    - `test_ui_screens.py` kept growing during the leg (153 → 184 added lines).
    - Round 41 LOW-003 below still describes the `finished` design, so the record and the code disagree until reconciled.
    - Either design satisfies the finding. Swallowing a `BaseException` in a worker thread is acceptable: nothing could propagate it from a `QThread` anyway.
    - rec=stop every other `claude -p` running the stage-5 executor prompt on `C:/scribe-build` (check the process list and the probe log). Then resume this executor once to reconcile round 41 LOW-003 and the handoff with the final code, and to re-run ruff, mypy and the history check. Do not run the suite before that.
  - **What changed:**
    - LOW-001: `packaging/scribe.iss` `CurPageChanged` ends with `WizardForm.AdjustLabelHeight(WizardForm.FinishedLabel);`. No wording changed.
    - LOW-002 (UX only; the custody rule is unchanged): a confirmed Discard with live transcription attached runs on a `TaskThread` under "Discarding - stopping live transcription first...". Everything is held meanwhile: the Session controls, Chrome commands, "Open for review" and the close. An outlasted stop says "Recording stopped, but live transcription did not stop in time, so nothing was deleted - the recording is kept. Press Discard again in a moment to delete it." There is no automatic retry.
    - `LiveStopPendingError` (a `SessionActivityError`) names the refusal.
    - The Chrome `busy` text is now "The app is busy with a recording - wait for it to finish."
  - **Files changed** (the codex slice, 14 files plus this plan):
    - src: `desktop/src/scribe_desktop/session.py`, `ui/session_screen.py`, `ui/bridge.py`, `ui/main_window.py`, `ui/models.py`.
    - installer: `packaging/scribe.iss`.
    - tests: `desktop/tests/test_installer_script.py`, `test_ui_screens.py`, `test_ui_bridge.py`, `test_unreviewed_review.py`.
    - docs: `docs/design-system.md`, `docs/security/threat-model.md` (surface 11 CUSTODY), `docs/security/data-flow-map.md` (flow 14), `AGENTS.md` (the live-transcription pointer).
    - plan: rounds 40–42.
  - **Composer to run:**
    - The full desktop suite. Expected **5912 passed / 9 skipped**: 5904 plus 8 new tests (counted from the diff; this leg could not run pytest).
      - `test_installer_script.py`: 1.
      - `test_ui_screens.py`: 5 — the off-thread wait, the outlasted case, the backstop, the refusal line, and the close refusal.
      - `test_ui_bridge.py`: 1.
      - `test_unreviewed_review.py`: 1.
    - **An ISCC 6.7.3 compile check of `packaging/scribe.iss` IS needed** (the new `AdjustLabelHeight` call).
    - No `npm run qa`: the extension was not touched.
  - **If green:** run a codex confirmation over the 14 files, and close round 40. The next build's Finish page should show "Open Clinic Scribe from the Start menu.". A Discard during live transcription should show the waiting line and stay responsive.
  - **Open gates:** none.
- **EXECUTOR stage-5 leg i5-x6 (2026-10-03T20:33:10+10:00; a FRESH executor after the composer stopped both i5-x4 and i5-x5): the final uncommitted diff (15 files) re-reviewed from scratch, no defect found, so no round 43; rounds 40–42 reconciled to the final code; ruff clean; history-check OK (42 + 42); mypy NOT run by this leg (every invocation needed a permission approval this headless session could not get), so the composer runs it. Round 40 stays Open. ENDS composer-run:**
  - **What happened before this leg:** legs i5-x4 (resumed after a transient CLI 401) and i5-x5 edited this worktree at the same time, 20:25–20:29. Leg i5-x4's last edit, at 20:27, replaced round 41 LOW-003's `task.finished` backstop with an `except BaseException` inside the discard job, renamed its test and reworded the threat-model sentence. The plan text partly described the superseded version.
  - **Review of the final code (fresh, every hunk read):**
    - The backstop: `_begin_discard`'s job returns `discard_refusal_line(exc)` for an `Exception` and the fixed `CUSTODY_UNEXPECTED_REASON` line for any other `BaseException`, so `TaskThread.succeeded` always fires and `_on_discard_done` always clears `_discarding`. `failed` cannot double-fire with it (one of the two per run). Nothing hides a real exit: a `KeyboardInterrupt` only reaches the main thread, and a `SystemExit` on a worker thread never ends the process.
    - The GUI thread never waits on the discard: `on_discard` returns True at once. Its only join is `TaskThread.finish()`'s bounded 2 s join, AFTER the thread has emitted its result.
    - The custody rule is the controller's, unchanged: `discard()`'s body is untouched except that `_refuse_uncleared_live` now raises `LiveStopPendingError`, a `SessionActivityError`.
    - The hold is consistent everywhere: every Session slot returns False while discarding (Start before the consent tick is spent); the bridge refuses every Chrome command `busy` (Start `session_active`) through `is_busy`; the bridge's Discard returns True while under way and reports `failed` exactly once, through `on_refused`; the main window refuses "Open for review" and the close with their own lines. A FAILED seen mid-discard is not called a device failure, and `_on_discard_done`'s `refresh()` sets `_last_state`, so a later poll cannot show that line either.
    - No leftovers: there is no `finished` handler, no duplicate backstop test, and the threat model's sentence ("any `BaseException` sends the fixed reason") matches the code. `ui/models.py`'s strings, `docs/design-system.md` and `AGENTS.md` agree with the code.
  - **Plan reconciled** (marked `[reconciled 2026-10-03 leg i5-x6]`): round 40 LOW-002's Tests line (it names the backstop test), round 41 LOW-003 (the in-job design and its test), round 42's re-read line, and the round 41 Review History line. Leg i5-x5's bullet above is marked superseded.
  - **Files changed** (the codex slice, 14 files plus this plan; this leg changed only the plan):
    - src: `desktop/src/scribe_desktop/session.py`, `ui/session_screen.py`, `ui/bridge.py`, `ui/main_window.py`, `ui/models.py`.
    - installer: `packaging/scribe.iss`.
    - tests: `desktop/tests/test_installer_script.py`, `test_ui_screens.py`, `test_ui_bridge.py`, `test_unreviewed_review.py`.
    - docs: `docs/design-system.md`, `docs/security/threat-model.md` (surface 11 CUSTODY), `docs/security/data-flow-map.md` (flow 14), `AGENTS.md` (the live-transcription pointer).
    - plan: rounds 40–42, Review History round 41, and these handoff bullets.
  - **Composer to run:**
    - The full desktop suite. Expected **5912 passed / 9 skipped**: 5904 plus 8 new tests, counted from the final diff (no test was removed or renamed away): `test_installer_script.py` 1; `test_ui_screens.py` 5 (the off-thread wait, the outlasted case, the backstop, the refusal line, the close refusal; `_gated_discard` is a helper); `test_ui_bridge.py` 1; `test_unreviewed_review.py` 1. Leg i5-x4's 5913 counted the superseded version.
    - An ISCC 6.7.3 compile check of `packaging/scribe.iss` (the new `AdjustLabelHeight` call).
    - mypy (`cd desktop && ../.venv/Scripts/python.exe -m mypy`): leg i5-x5 reported it clean (59 source files), possibly before leg i5-x4's last edit to `ui/session_screen.py`; this leg could not run it.
    - No `npm run qa`: the extension was not touched.
  - **If a test fails:** resume me with the output.
  - **If green:** run a codex confirmation over the 14 files, and close round 40. The practitioner then checks the next build's Finish page ("Open Clinic Scribe from the Start menu." visible) and a Discard during live transcription (the waiting line, a responsive window).
  - **Open gates:** none.
- Last plan sync: 2026-10-04 (/document close-out)
- Retro report: .cursor/loops/retro-installation-20261002-113527-26e920-2026-10-04.md (2026-10-04)
- Loop config: executor=claude-p model="claude-opus-5-5" effort=high profile=default; peer=codex model="gpt-6-astra" effort=medium; architect=off; cadence=every-phase; caps=review:3,peer:5; gates=executor; cap-raise=executor; high-auto=on; peer-max=12; notify=action-only; scope=all; autocommit=on; isolation=none; merge=off; perms=scoped; liveness=10; monitor-delivery=auto; verify=composer
- COMPOSER RUN-STATE (CLOSED 2026-10-04 — kept for the record; the worktree note below is historical, the main checkout is current): /execute-loop run iso `installation-20261002-113527-26e920`, started 2026-10-02T11:36+10:00; runkeys stage-0..stage-5 (stage-0 = Phase 0; stage-1..3 = Phases 1-3; stage-4 = Phase H; stage-5 = Phase P); probe logs `C:/Recording clinic software/.cursor/loops/stage-N-probe.log`. Phase 0 committed `9f43f8c` on `main`. **From Phase 1 on the run builds in the git WORKTREE `C:\scribe-build` (branch `installation-build`)** — practitioner decision 2026-10-02: the main checkout's `.venv` is the practitioner's EVERYDAY app (editable install) and stays on `main` until Phase P. The worktree has its own `.venv` copy (editable `.pth` → `C:\scribe-build\desktop\src`; `scribe-app.exe`/`scribe-host.exe` launchers regenerated for it; run mypy/pytest as `.venv/Scripts/python.exe -m …`). THIS worktree plan is authoritative; the main checkout's copy is stale until the branch merges, which happens only when the practitioner switches to the installed build. Phase 1 committed `a7337a2` (rounds 9–12), Phase 2 committed `7cfed96` (rounds 13–17) on `installation-build`. Phase 3 built and peer-converged (rounds 18–21), committed on `installation-build` by the composer at its close; its tasks stay 🟨 on their named practitioner/network/remote steps. Phase 2's Task 2.6 stays 🟨 until the practitioner fills `%LOCALAPPDATA%\ClinikoScribe-dev\models` and the composer re-runs the 11 real-ML legs. `stash@{0}` (the pre-worktree Phase 1 copy) is now redundant. `extension/key-dev.pem` is gitignored in the worktree; the main checkout holds an untracked copy — never commit it. Peer passes run as file-scoped codex slices (`.cursor/loops/inst-peer-run-wt.sh`). Phase H closed 2026-10-03 (rounds 22–30; H.1–H.5 🟩; H.6 hardened by a scoped /review-plan on 2026-10-03, ready for /execute), committed on `installation-build` by the composer. Next: the practitioner's open steps (Task 2.6 dev models, 3.3 manifest, 3.1 lock, 3.2/3.5 a real build, 3.6 pins/push/CI, the Inno licence), then Phase P (stage-5) with the practitioner.

## Review History
- 2026-10-02 round 1: 0 CRIT / 0 HIGH / 3 MED / 0 LOW; skew=none; action=amend (codex gpt-6-astra medium plan peer-review; 3 build-affecting, all applied by the owning planning session)
- 2026-10-02 round 2: 0 CRIT / 0 HIGH / 2 MED / 0 LOW; skew=none; action=amend (codex gpt-6-astra medium; verified 1 build-affecting / 1 record-only, both applied)
- 2026-10-02 round 3: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium; 8 candidates, 8 dropped; plan-review loop CONVERGED — no new build-affecting finding from round 2 on; one precision note applied to Task 0.2)
- 2026-10-02 round 4: 0 CRIT / 0 HIGH / 3 MED / 1 LOW; skew=none; action=fix → all 4 Applied with siblings, round Closed (codex gpt-6-astra medium, pass stage-0.p1 peer_round 1 — Phase 0 spike inputs and runbook; LEG 1 verified 1 MED + 3 LOW, all CONFIRMED; LEG 2 /fix leg i0-x4 2026-10-02T12:33+10:00 edited `packaging/spike/RUNBOOK.md` and the `spike_app_entry.py` docstring only)
- 2026-10-02 round 5: 0 CRIT / 0 HIGH / 2 MED / 1 LOW; skew=none; action=fix → all 3 Applied with every enumerated sibling, round Closed (codex gpt-6-astra medium, pass stage-0.p1 peer_round 2 — confirmation of round 4's fix; LEG 1 verified 2 MED + 1 LOW, all CONFIRMED; LEG 2 /fix leg i0-x6 2026-10-02T12:42+10:00 edited `packaging/spike/RUNBOOK.md` only; the prior-state check + exact undo + failure route class is now closed across every state-changing step)
- 2026-10-02 round 6: 0 CRIT / 0 HIGH / 2 MED / 1 LOW; skew=fix-induced; action=fix → all 3 Applied with every sibling, round Closed (codex gpt-6-astra medium, pass stage-0.p1 peer_round 3 — confirmation of round 5's fix; LEG 1 leg i0-x7 verified 1 MED + 2 LOW, all CONFIRMED; LEG 2 /fix leg i0-x8 2026-10-02T12:53+10:00 edited `packaging/spike/RUNBOOK.md` only: the venv half closed by DESIGN — the build runs in a copy `C:\scribe-spike\venv-build`, the everyday `.venv` is only read, and the backup/restore is removed — plus record-gated, verified install-folder cleanup; the class is closed)
- 2026-10-02 round 7: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=none; action=fix → 1 Applied with both siblings, round Closed (codex gpt-6-astra medium, pass stage-0.p1 peer_round 4 — confirmation of round 6's redesign; LEG 1 leg i0-x9 verified 1 LOW (peer MED), test-harness, CONFIRMED; LEG 2 /fix leg i0-x10 2026-10-02T12:59+10:00 edited `packaging/spike/RUNBOOK.md` only: the 3.12 fallback is a numbered procedure that replaces every build-copy call, and 0.2 step 2 gives the `venv312` host-build command)
- 2026-10-02 round 8: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=accept-close (codex gpt-6-astra medium, pass stage-0.p1 peer_round 5 = cap — confirmation of round 7's fix; PR-LOW-015 verified low test-harness, Accepted with record per the executor's cap verdict; peer pass stage-0.p1 CLOSED at the cap, trajectory 4 → 3 → 3 → 1 → 1)
- 2026-10-02 round 9: 0 CRIT / 0 HIGH / 3 MED / 10 LOW; skew=none; action=fix → all 13 Applied (10 in code/tests/docs, 3 as plan work: Tasks 2.6, 2.7 and H.1's pointer list), round Closed on composer suite 4 (pytest 5417 passed / 9 skipped) (in-session /review-loop pass 1 over Phase 1, executor stage-1 leg i1-x5; 19 candidates, 6 dropped, 1 downgraded)
- 2026-10-02 round 10: 0 CRIT / 0 HIGH / 0 MED / 5 LOW; skew=none; action=fix → all 5 Applied (tests, `KEY.md` and D4's as-built note; 2 ⚡ fix-induced LOW, 3 🆕); round Closed on composer suite 5 (pytest 5422 passed / 9 skipped); /review-loop CONVERGED at loop round 2 of cap 3 (in-session /review-loop pass 2, executor stage-1 leg i1-x6; 18 candidates, 13 dropped)
- 2026-10-03 round 11: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=fix → 1 Applied with every enumerated sibling (one class-level conftest pin covers them all), round Closed pending the composer-run full desktop suite (codex gpt-6-astra medium, pass stage-1.p1 peer_round 1 of cap 5, four file-scoped slices; LEG 1 leg i1-x8 verified PR-LOW-016 low test-harness, CONFIRMED; LEG 2 /fix leg i1-x9 2026-10-03T00:41:10+10:00 edited `desktop/tests/conftest.py`, `test_install_layout.py` and `test_integration_no_sockets.py` only)
- 2026-10-03 round 12: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none — round 11's PR-LOW-016 fix confirmed closed as a class (codex gpt-6-astra medium, pass stage-1.p1 peer_round 2 of cap 5; peer pass CONVERGED, trajectory 1 → 0)
- 2026-10-03 round 13: 0 CRIT / 0 HIGH / 3 MED / 11 LOW; skew=none; action=none → all 14 Applied (code, tests, and a Task 3.2 spec note); round Closed on composer suite 2 (pytest 5555 passed / 20 skipped) (in-session /review-loop pass 1 over Phase 2, executor stage-2 leg i2-x2; 17 candidates, 1 dropped, 2 merged)
- 2026-10-03 round 14: 0 CRIT / 0 HIGH / 0 MED / 4 LOW; skew=fix-induced; action=none → all 4 Applied (3 ⚡ in round 13's hardware-check fix, all LOW, already on the premium executor; 1 🆕); round Closed on composer suite 3 (pytest 5559 passed / 20 skipped); /review-loop CONVERGED at loop round 2 of cap 3 (in-session /review-loop pass 2, executor stage-2 leg i2-x3; 5 candidates, 1 dropped)
- 2026-10-03 round 15: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=none; action=fix → both Applied with every enumerated sibling (4 docstring/comment sites in 3 test files, no code change), round Closed pending the composer-run full desktop suite (codex gpt-6-astra medium, pass stage-2.p1 peer_round 1 of cap 5, three file-scoped slices; LEG 1 leg i2-x5 verified both docs-only, test-harness, CONFIRMED; LEG 2 /fix leg i2-x6 2026-10-03T02:22:51+10:00 edited `test_frozen_runtime.py`, `test_language_model_runtime.py` and `test_speaker_embedding.py` docstrings/comments only)
- 2026-10-03 round 16: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=fix-induced; action=fix → 1 Applied (two docstring clauses in `test_language_model_runtime.py`, no code change), round Closed pending the composer-run full desktop suite (codex gpt-6-astra medium, pass stage-2.p1 peer_round 2 of cap 5, confirmation of round 15; one docs-only LOW in round 15's own docstring fix; LEG 1 leg i2-x7 CONFIRMED, rec=Fix-now over the D9 Accept default; LEG 2 /fix leg i2-x8 2026-10-03T02:31:49+10:00)
- 2026-10-03 round 17: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none — round 16's PR-LOW-019 fix confirmed (codex gpt-6-astra medium, pass stage-2.p1 peer_round 3 of cap 5; peer pass CONVERGED, trajectory 2 → 1 → 0)
- 2026-10-03 round 18: 0 CRIT / 0 HIGH / 1 MED / 4 LOW; skew=none; action=none → all 5 Applied (the installer's upgrade cleanup, a docstring, a test pin, a doc line, a plan line); round Closes on the composer-run full desktop suite (in-session /review-loop pass 1 over Phase 3, executor stage-3 leg i3-x3; 7 candidates, 2 dropped); Closed on composer suite 3 (pytest 5725 passed / 23 skipped; ISCC re-compile OK)
- 2026-10-03 round 19: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=pre-existing; action=triage-and-ship → 1 Applied (ISCC's own output shown on a refused compile); no CRIT/HIGH/MED; Closed on composer suite 4 (pytest 5727 passed / 23 skipped); /review-loop CONVERGED at loop round 2 of cap 3 (in-session /review-loop pass 2, executor stage-3 leg i3-x4; 3 candidates, 2 dropped)
- 2026-10-03 round 20: 0 CRIT / 3 HIGH / 1 MED / 0 LOW; skew=none; action=verify → codex gpt-6-astra medium, pass stage-3.p1 peer_round 1 of cap 5, three slices (A 2 HIGH, B 1 HIGH, C 1 MED); LEG 1 leg i3-x6 verified 3 MED (downgraded from HIGH) + 1 LOW test-harness, all CONFIRMED; LEG 2 /fix leg i3-x7 2026-10-03T04:05:03+10:00 → all 4 Applied with siblings (`build-release.py`, `scribe.iss`, three test modules, `pilot-builds.md`); the round closes on codex confirmation round 21
- 2026-10-03 round 21: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none — round 20's four fixes and siblings confirmed (codex gpt-6-astra medium, pass stage-3.p1 peer_round 2 of cap 5; peer pass CONVERGED, trajectory 4 → 0)
- 2026-10-03 round 22: 0 CRIT / 0 HIGH / 3 MED / 28 LOW; skew=none; action=fix → all 31 Applied (a workflow pin test, the release job split, the register script's in-use check, the installer's Finish note, five test pins, and doc-class corrections across the H.1 surface); round Closes on the composer-run full desktop suite and the ISCC 6.7.3 compile (in-session /review-loop pass 1 over the whole plan diff, executor stage-4 leg i4-x1 with four parallel lenses; 32 candidates, 1 dropped)
- 2026-10-03 round 23: 0 CRIT / 0 HIGH / 1 MED / 4 LOW; skew=pre-existing; action=fix → all 5 Applied (the attestation-visibility precondition as Task 3.6 step 0 plus docs, the Status remedy for a broken per-user link, the bounded self-check, the Inno install exit check and missing-tool refusal, a lesson sibling); round Closes on the composer-run full desktop suite; not converged (one MED), round 24 re-reviews (in-session /review-loop pass 2, executor stage-4 leg i4-x2 with two parallel lenses; 8 candidates, 3 dropped)
- 2026-10-03 round 24: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=pre-existing; action=triage-and-ship → 1 Applied (the benchmark worker's admission also checks the seconds parse); /review-loop CONVERGED at loop round 3 of cap 3, no cap raise; round Closes on the composer-run full desktop suite (in-session /review-loop pass 3, executor stage-4 leg i4-x3 with one doc fact-check lens; 1 candidate, 0 dropped)
- 2026-10-03 round 25: 0 CRIT / 0 HIGH / 0 MED / 3 LOW; skew=none; action=fix → all 3 Applied (SIMP-001 one whisper-model spelling, SIMP-002, SIMP-003); round Closes on the composer-run full desktop suite (H.3 /simplify, executor stage-4 leg i4-x3; 7 candidates, 4 left alone)
- 2026-10-03 round 26: 0 CRIT / 0 HIGH / 0 MED / 4 LOW; skew=none; action=fix → all 4 Applied (SEC-001 audit after the extension build, SEC-002 every release action commit-pinned and no cache, SEC-003 no network-share manifest touched, SEC-004 curly quotes refused); round Closes on the composer-run full desktop suite (H.4 /security-review, portable checklist, executor stage-4 leg i4-x3)
- 2026-10-03 round 27: 0 CRIT / 0 HIGH / 4 MED / 8 LOW; skew=none; action=verify → codex gpt-6-astra medium, Task H.5, pass stage-4.p1 peer_round 1 of cap 5, eight slices (a1 1M/2L, a2 1L, b1 1L, b2 1M, b3 1L, c1 1M, c2 1M, c3 3L); pending executor leg-1 verification
- 2026-10-03 round 28: 0 CRIT / 0 HIGH / 0 MED / 5 LOW; skew=fix-induced; action=verify → codex gpt-6-astra medium, pass stage-4.p1 peer_round 2 of cap 5, confirmation of round 27 in two slices (X1 4L: extended local paths refused by the UNC helper, the benchmark's temp-audio sibling, two test spies that fall through to the real filesystem, an installer comment; X2 1L: a threat-model sentence); pending executor leg-1 verification
- 2026-10-03 round 29: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=fix-induced; action=verify → codex gpt-6-astra medium, pass stage-4.p1 peer_round 3 of cap 5, confirmation of round 28 (one unprotected UNC test sibling of PR-LOW-030); trajectory 12 → 5 → 1; pending executor leg-1 verification
- 2026-10-03 round 30: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=fix-induced; action=verify → codex gpt-6-astra medium, pass stage-4.p1 peer_round 4 of cap 5, confirmation of round 29 (the class is closed; one docs-only LOW: new test comments say "any filesystem call" where the tripwire covers the `Path` methods in `NETWORK_IO_METHODS`); trajectory 12 → 5 → 1 → 1; pending executor leg-1 verification
- 2026-10-03 round 31: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=none; action=Applied → first Release run (CI) failed (`Cannot import 'hatchling.build'`): PyInstaller's build backend and its four dependencies are now build-tool pins, and preflight refuses a lock without the backend and an unexpected backend; Task 3.1 reopened (the practitioner regenerates the lock); closes on the composer suite and a green re-dispatched `Release`
- 2026-10-03 round 32: 0 CRIT / 0 HIGH / 0 MED / 3 LOW; skew=none; action=fix → all 3 Applied (a source scan pinning the opt-out set, two stale test comments, tripwire wording); round Closes on the composer-run full desktop suite (Task H.6, in-session /review-loop pass 1 over the H.6 diff, executor stage-4 leg i4-x13; 6 candidates, 3 dropped)
- 2026-10-03 round 33: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none — round 32's three fixes re-read and confirmed; /review-loop CONVERGED at loop round 2 of cap 3 (Task H.6, in-session /review-loop pass 2, executor stage-4 leg i4-x13; 2 candidates, 2 dropped)
- 2026-10-03 round 34: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none → codex gpt-6-astra medium, pass stage-4.p2 peer_round 1 of cap 5, one slice of 14 files over the Task H.6 diff (every diff read, plus a search of the tests for any other route to a models folder); 2 candidates, 2 dropped; peer pass CONVERGED
- 2026-10-03 round 35: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=none; action=fix → Phase P.1 step 10 (practitioner smoke on the installed 0.1.0): the first recording after installing failed at the first one-second chunk; cause unconfirmed because the capture failure's type is not logged; MED-001 Applied by executor stage-5 leg i5-x1 (diagnosis, the type-name log line, the start-up import warm-up and the live-worker gate), pending the composer-run suites
- 2026-10-03 round 36: 0 CRIT / 0 HIGH / 1 MED / 8 LOW; skew=none; action=fix → 8 LOW Applied; MED-001 (a Start made while the warm-up still runs overlaps its imports) paused at a MUST-PAUSE gate, then Applied as the practitioner's option (b) — a bounded Start refusal — by leg i5-x2
- 2026-10-03 round 37: 0 CRIT / 0 HIGH / 0 MED / 5 LOW; skew=none; action=fix → 4 LOW Applied (a redundant third hold check removed, the no-sockets child's warm-up wait 45 → 30 s, voice enrolment held too, a stale `on_start` docstring); /review-loop CONVERGED at loop round 2 of cap 3 (round 36 MED-001's option (b) delta, executor stage-5 leg i5-x2, in-session plus the same independent read-only subagent; 7 candidates, 2 dropped) (round 35 MED-001's fix diff, in-session /review-loop pass 1, executor stage-5 leg i5-x1, plus one independent read-only subagent review; 11 candidates, 2 dropped)
- 2026-10-03 round 38: 0 CRIT / 0 HIGH / 0 MED / 4 LOW; skew=none; action=fix → all 4 confirmed and Applied by leg i5-x3, round Closed; codex gpt-6-astra medium, pass stage-5.p1 peer_round 1 of cap 5, three slices (code 10, tests 11, docs 4) over the rounds 35–37 diff
- 2026-10-03 round 39: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none → codex gpt-6-astra medium, pass stage-5.p1 peer_round 2 of cap 5, confirmation of round 38 (4 claims checked, 4 confirmed closed); peer pass CONVERGED
- 2026-10-03 round 40: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=none; action=fix → Task P.3 practitioner smoke on 0.1.0/0.1.1: the Finish page truncates its later paragraphs, and Discard during live transcription blocks and needs a second press; both CONFIRMED and Applied by legs i5-x4/i5-x5 (the Finish label re-sized after its last change; Discard with live transcription waits off the GUI thread with a line, everything held, and an outlasted stop says plainly that nothing was deleted — custody rule unchanged, no automatic retry); closes on the composer suite, the ISCC compile and codex confirmation
- 2026-10-03 round 41: 0 CRIT / 0 HIGH / 0 MED / 6 LOW; skew=fix-induced; action=fix → all 6 Applied (the close names the discard; a refused Start keeps the tick; the in-job `BaseException` backstop (reconciled by leg i5-x6: it superseded a `finished` handler); a stale docstring; the Chrome `busy` text; two doc corrections) (round 40's fix diff, in-session /review-loop pass 1, executor stage-5 legs i5-x4/i5-x5 plus one independent read-only subagent review; 14 candidates, 8 dropped)
- 2026-10-03 round 42: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=fix-induced; action=triage-and-ship → 1 Applied (a mid-sentence line break in the new design-system bullet); round 41's six fixes re-read and confirmed; /review-loop CONVERGED at loop round 2 of cap 3 (in-session pass 2, executor stage-5 leg i5-x5)
- 2026-10-03 round 43: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none → codex gpt-6-astra medium, pass stage-5.p2 peer_round 1 of cap 5, two slices (code, installer and tests 10; docs 4) over the round 40 fixes; every changed file read in full; peer pass CONVERGED

## Review Findings Log
### Round 1 - 2026-10-02 - installation plan, independent cross-family codex plan peer-review (round 1)
- Round status: Closed
- Source: Codex plan peer-review
- Materiality: 3 build-affecting / 0 record-only / 0 invalid
- Materiality: build-affecting
- Materiality: build-affecting
- Materiality: build-affecting
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 2 - 2026-10-02 - installation plan, independent cross-family codex plan peer-review (round 2)
- Round status: Closed
- Source: Codex plan peer-review
- Materiality: 1 build-affecting / 1 record-only / 0 invalid (owning-session verified; peer's labels were 2 / 0 / 0 — PR-MED-001 reclassified record-only)
- Materiality: build-affecting
- Materiality: build-affecting
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 3 - 2026-10-02 - installation plan, independent cross-family codex plan peer-review (round 3)
- Round status: Closed — No new findings this round
- Source: Codex plan peer-review
- Materiality: 0 build-affecting / 0 record-only / 0 invalid
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 4 - 2026-10-02 - Phase 0 spike inputs and runbook, independent cross-family codex peer review (pass stage-0.p1)
- Round status: Closed
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-MED-004 · `packaging/spike/RUNBOOK.md:12` · The failure instruction can leave the everyday Chrome link removed or pointing at the spike: it tells the clin… · Applied
  - PR-MED-005 · `packaging/spike/RUNBOOK.md:422` · The HKLM registration is overwritten without checking or preserving its previous state, then deleted during cl… · Applied
  - PR-MED-006 · `packaging/spike/RUNBOOK.md:107` · The compiler-discovery fallback directs the clinician to run PowerShell syntax in a Command Prompt, where it f… · Applied
  - PR-LOW-007 · `packaging/spike/RUNBOOK.md:245` · The description of the checks file understates what it contains: exception messages are included, not merely e… · Applied

### Round 5 - 2026-10-02 - Phase 0 confirmation of round 4's fix, independent cross-family codex peer review (pass stage-0.p1)
- Round status: Closed
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-MED-008 · `packaging/spike/RUNBOOK.md:172` · The venv rollback remains incomplete: neither installation route records prior package state, uninstall remove… · Applied
  - PR-MED-009 · `packaging/spike/RUNBOOK.md:609` · HKCU recovery never uses the exported original key, so it recreates the standard registration rather than rest… · Applied
  - PR-LOW-010 · `packaging/spike/RUNBOOK.md:635` · Task 0.3 still lacks prior-state checks for its installation folder, uninstall registration and test registry … · Applied

### Round 6 - 2026-10-02 - Phase 0 confirmation of round 5's fix, independent cross-family codex peer review (pass stage-0.p1)
- Round status: Closed
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-MED-011 · `packaging/spike/RUNBOOK.md:943` · A partial backup can replace the working everyday environment. If step 4c fails after copying `Scripts\python.… · Applied
  - PR-MED-012 · `packaging/spike/RUNBOOK.md:19` · Failure routing still leaves the everyday venv modified when work stops after installation: Task 0.1 build/run… · Applied
  - PR-LOW-013 · `packaging/spike/RUNBOOK.md:664` · Both folder cleanup commands can report successful removal when removal failed, and their marker-based retry i… · Applied

### Round 7 - 2026-10-02 - Phase 0 confirmation of round 6's fix, independent cross-family codex peer review (pass stage-0.p1)
- Round status: Closed
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-MED-014 · `packaging/spike/RUNBOOK.md:459` · The Python 3.12 fallback does not propagate to the host build. After successfully rebuilding the app with `ven… · Applied

### Round 8 - 2026-10-02 - Phase 0 confirmation of round 7's fix, independent cross-family codex peer review (pass stage-0.p1)
- Round status: Closed
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-LOW-015 · `packaging/spike/RUNBOOK.md:562` · Successful folder creation followed by a failed marker write leaves a spike-created folder that rollback refus… · Accepted

### Round 9 - 2026-10-02 - Phase 1 (Tasks 1.1–1.8), in-session /review-loop pass 1 (executor stage-1 leg i1-x5)
- Round status: Closed — all 13 dispositions applied; composer-run suite 4 green 2026-10-02 ~23:47 (ruff clean, mypy 57 files, pytest 5417 passed / 9 skipped in 309 s — the expected +24; `.cursor/loops/stage-1-suite4-pytest.txt` in the main checkout); closed by executor leg i1-x6 2026-10-02T23:47:10+10:00
- Source: Claude Code
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `desktop/src/scribe_desktop/speaker_embedding.py:319-322` · the onnxruntime "not importable" line names the source checkout's pip command in a packaged build · Applied
  - LOW-002 · `desktop/tests/test_install_layout.py` · references to `APP_FOLDER_NAME` / `DEV_FOLDER_NAME` / `folder_name` outside `install_layout` were unseen, and … · Applied
  - LOW-003 · `desktop/tests/test_install_layout.py` · a line-by-line grep misses a remedy split across lines or a `+` · Applied
  - LOW-004 · `.gitignore:32` · the comment says registration installs into `%LOCALAPPDATA%\ClinikoScribe` only · Applied
  - LOW-005 · `exclusions.py:8` · module docstrings name the production paths only — `exclusions.py:8`, `pipe_server.py:9`, `session_store.py:4`… · Applied
  - LOW-006 · `desktop/src/scribe_desktop/ui/main_window.py` · on a failed save the box showed the inverse of the click, not the file, and the Write button was not told · Applied
  - LOW-007 · `extension/KEY.md:5` · says the key is pinned in `src/manifest.ts` and does not record the dev ID, `key-dev.pem` or `--out` · Applied
  - LOW-008 · `desktop/tests/test_ui_encounter.py` · the dev refusal's audit row is pinned only through the fake recorder · Applied
  - LOW-009 · `desktop/src/scribe_desktop/install_layout.py:140-152` · only `models_root` calls `install_root()`, so a frozen build outside `INSTALL_ROOTS` still runs as production … · Applied
  - LOW-010 · `data-flow-map.md` · the Phase 1 documentation residue — AGENTS.md Database Notes and Local Run Steps 3–8, `data-flow-map.md`, `thr… · Applied

### Round 10 - 2026-10-02 - Phase 1 (Tasks 1.1–1.8), in-session /review-loop pass 2 — re-review after round 9's fix (executor stage-1 leg i1-x6)
- Round status: Closed — all 5 dispositions applied; composer-run suite 5 green on 2026-10-03 (ruff clean, mypy 57 files, pytest 5422 passed / 9 skipped, the expected +5; `.cursor/loops/stage-1-suite5-pytest.txt` in the main checkout). Closed by executor leg i1-x7 at 2026-10-03T00:05:37+10:00. `/review-loop` CONVERGED here: there are no CRIT/HIGH/MED findings, and every survivor is a LOW that is now fixed and verified.
- Source: Claude Code
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `desktop/tests/test_install_layout.py` · round 9's AST remedy scan was case-sensitive and forward-slash only (`run\s+scripts/`), and its self-test chec… · Applied
  - LOW-002 · `desktop/tests/test_install_layout.py` · the docstring listed "an f-string that splits the name around a placeholder" as unseen, but `_folded_str` join… · Applied
  - LOW-003 · `extension/KEY.md` · round 9's lost-key steps named `src/channel.ts` only, but the host registration writes `allowed_origins` from … · Applied
  - LOW-004 · `desktop/src/scribe_desktop/draft_write.py:1158-1160` · with dev writes off, the Write click is refused before hop 1, so D4's "reads and verification still work, so t… · Applied
  - LOW-005 · `desktop/src/scribe_desktop/draft_write.py:1323-1378` · hop 2 does not re-check the dev guard; it holds only because `prepare_write` is the sole builder of a `Prepare… · Applied

### Round 11 - 2026-10-03 - Phase 1 (Tasks 1.1–1.8), independent cross-family codex peer review (pass stage-1.p1, peer_round 1 of cap 5; four file-scoped slices)
- Round status: Closed (0 pending — PR-LOW-016 Applied by leg i1-x9; the composer-run full desktop suite confirms it)
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-LOW-016 · `desktop/tests/test_install_layout.py:231` · Source-model tests leave `is_frozen()` dependent on host state, contrary to C6 and the module's injection clai… · Applied

### Round 12 - 2026-10-03 - Phase 1 confirmation of round 11's fix, independent cross-family codex peer review (pass stage-1.p1)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 13 - 2026-10-03 - Phase 2 (Tasks 2.1–2.7), in-session /review-loop pass 1 (executor stage-2 leg i2-x2)
- Round status: Closed. All 14 were Applied by leg i2-x2 at 2026-10-03T01:48:24+10:00. Composer-run suite 2 is green: ruff clean, mypy 58 files, pytest 5555 passed / 20 skipped, exactly the expected +28. The 20 skips are unchanged (9 symlink, 11 real-ML on the empty dev root); the run is in `.cursor/loops/stage-2-suite2-pytest.txt` in the main checkout. Closed by executor leg i2-x3 at 2026-10-03T01:54:55+10:00.
- Source: Claude Code
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `ui/hardware_check.py:132-134` · the per-section CPU figure includes the model load, while the wall figure (`model_seconds`) excludes it, so "4… · Applied
  - LOW-002 · `native_host.py` · `msvcrt.open_osfhandle` on a stale or invalid non-null handle raises `OSError`, which escapes `binary_stdio` a… · Applied
  - LOW-003 · `native_host.py` · `Win32WindowsLayer()` is built inside the broad `except`, so the conftest's C6 sentinel (an `AssertionError` f… · Applied
  - LOW-004 · `benchmark.py` · the spawn shape is not checked against `is_worker_argv`. In a packaged build a candidate folder named `-x` wou… · Applied
  - LOW-005 · `exclusions.py` · opens with `KEY_READ`, while Chromium opens these keys with `KEY_QUERY_VALUE`, so a query-only ACL would be pa… · Applied
  - LOW-006 · `tests/test_frozen_runtime.py:883-884` · the Task 2.6 skip-gate scan collects only `ast.Name` probes (an attribute call such as `lm.language_model_file… · Applied
  - LOW-007 · `install_layout.py:68` · a new name carrying the folder name, invisible to Task 1.2's source scan (`test_install_layout.py:355` `_FOLDE… · Applied
  - LOW-008 · `tests/test_frozen_runtime.py:536-539` · checks only `.place` of an entry the test built itself; no real-layer case has only a 32-bit view · Applied
  - LOW-009 · `tests/test_ui_models.py:381-391` · under the production pin and the real `LOCALAPPDATA` it stats this computer's `ClinikoScribe\models` (C6/C8). … · Applied
  - LOW-010 · `benchmark.py:109` · the comment says the worker is "dispatched by `app.main` before anything else runs", but it runs after Task 2.… · Applied
  - LOW-011 · `status.py:57-62` · a manifest whose JSON is not an object (`["x"]`), or whose `path` is not a string, raises `TypeError` out of `… · Applied

### Round 14 - 2026-10-03 - Phase 2 (Tasks 2.1–2.7), in-session /review-loop pass 2 — re-review after round 13's fix (executor stage-2 leg i2-x3)
- Round status: Closed. All 4 were Applied by leg i2-x3 at 2026-10-03T02:05:35+10:00. Composer-run suite 3 is green: ruff clean, mypy 58 files, pytest 5559 passed / 20 skipped, exactly the expected +4. The run is in `.cursor/loops/stage-2-suite3-pytest.txt` in the main checkout. Closed by executor leg i2-x4 at 2026-10-03T02:11:26+10:00. `/review-loop` CONVERGED here: no CRIT/HIGH/MED, and every survivor is a LOW that is now fixed and verified.
- Source: Claude Code
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `ui/hardware_check.py:147-152` · since MED-001 the check shares the Note tab's cache, and the load-failure line no longer fits. Two cases — ⚡ · Applied
  - LOW-002 · `ui/hardware_check.py:144-146,171-173` · a check that waited on the cache lock for another thread's in-progress load counted that wait as section wall … · Applied
  - LOW-003 · `exclusions.py:456` · in production one unreadable hive (an HKLM key a managed computer denies) made the whole check "could not chec… · Applied
  - LOW-004 · `benchmark.py` · listed three skip causes; MED-002 added a fourth ("no section could be given to the language model") — ⚡ · Applied

### Round 15 - 2026-10-03 - Phase 2 (Tasks 2.1–2.7), independent cross-family codex peer review (pass stage-2.p1, peer_round 1 of cap 5; three file-scoped slices)
- Round status: Closed (0 pending). PR-LOW-017 and PR-LOW-018, with both siblings, were Applied by leg i2-x6 at 2026-10-03T02:22:51+10:00. They are docstring and comment changes only; the composer-run full desktop suite confirms them.
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-LOW-017 · `desktop/tests/test_frozen_runtime.py:13` · The module overstates its host-state isolation: `sys.executable` is not injected in the worker-spawn tests. · Applied
  - PR-LOW-018 · `desktop/tests/test_language_model_runtime.py:161` · The real-model smoke's documentation claims agent shells cannot read the practitioner's model cache, although … · Applied

### Round 16 - 2026-10-03 - Phase 2 confirmation of round 15's fix, independent cross-family codex peer review (pass stage-2.p1)
- Round status: Closed (0 pending) — PR-LOW-019 Applied by leg i2-x8 2026-10-03T02:31:49+10:00 (docstrings only); the composer-run full desktop suite confirms it
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-LOW-019 · `desktop/tests/test_language_model_runtime.py:22` · The revised module and class docstrings incorrectly claim that the missing-runtime skip reason names the dev m… · Applied

### Round 17 - 2026-10-03 - Phase 2 confirmation of round 16's fix, independent cross-family codex peer review (pass stage-2.p1)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 18 - 2026-10-03 - Phase 3 (Tasks 3.1–3.9), in-session /review-loop pass 1 (executor stage-3 leg i3-x3)
- Round status: Closed. All 5 were Applied by leg i3-x3 at 2026-10-03T03:31:53+10:00.
- Source: Claude Code
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `scripts/register-native-host.py:15-19` · they call the production-named HKCU key "stray", but until Phase P that key is the EVERYDAY source-run app's l… · Applied
  - LOW-002 · `desktop/tests/test_build_release.py:356` · `HOSTILE_ENV` is a hand-kept copy of `benchmark.OFFLINE_ENV` + `FORBIDDEN_NATIVE_OVERRIDES` + `FORBIDDEN_TLS_O… · Applied
  - LOW-003 · `docs/release/pilot-builds.md:37-43` · `Get-FileHash` prints the hash in CAPITALS while `SHA256SUMS.txt` (sha256sum format) is lower case. "The hash … · Applied
  - LOW-004 · `.cursor/plans/plan-installation.md` · it names `desktop/requirements-build.lock`, but the file the generator writes, the tests read and Task 3.1 nam… · Applied

### Round 19 - 2026-10-03 - Phase 3 (Tasks 3.1–3.9), in-session /review-loop pass 2 — re-review after round 18's fix (executor stage-3 leg i3-x4)
- Round status: Closed. LOW-001 was Applied by leg i3-x4 at 2026-10-03T03:41:41+10:00.
- Source: Claude Code
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `scripts/build-release.py` · ISCC runs with its output captured (for the 6.7.3 banner check), and a failed compile raised only "Inno Setup … · Applied

### Round 20 - 2026-10-03 - Phase 3 (Tasks 3.1–3.9), independent cross-family codex peer review (pass stage-3.p1, peer_round 1 of cap 5; three file-scoped slices)
- Round status: Closed (0 pending). All four (PR-HIGH-001–003 verified MED, PR-MED-018 verified LOW) and their siblings were Applied by leg i3-x7 (fix-delta correction to the test fake by leg i3-x8); composer suite 6 5743 passed / 23 skipped, ISCC 6.7.3 re-compile exit 0; confirmed by codex round 21 (0 findings).
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-HIGH-001 · `scripts/build-release.py:570` · The PyInstaller pin verifies HEAD but accepts modified source files, allowing an unverified bootloader or pack… · Applied
  - PR-HIGH-002 · `scripts/build-release.py:737` · Standalone `--audit` exits successfully when Defender detects a threat, allowing its documented integration ga… · Applied
  - PR-HIGH-003 · `packaging/scribe.iss:288` · Post-copy verification can leave unverified models installed and still display success. If two files change af… · Applied
  - PR-MED-018 · `desktop/tests/test_frozen_runtime.py:329` · The new self-check test probes the real environment’s installed Qt modules without a seam or named skip, contr… · Applied

### Round 21 - 2026-10-03 - Phase 3 confirmation of round 20's fix, independent cross-family codex peer review (pass stage-3.p1)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 22 - 2026-10-03 - Phase H (Task H.2), in-session /review-loop pass 1 over the whole plan diff (executor stage-4 leg i4-x1)
- Round status: Closed. All 31 Applied (3 MED + 28 LOW, written as 22 LOW entries — LOW-011 groups seven lens-C items) by leg i4-x1.
- Source: Claude Code
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `docs/security/threat-model.md` · the foreign-value residue named only the registry, not that the app's verdict and the host log also read a val… · Applied
  - LOW-002 · `register-native-host.py --unregister` · threat model HKCU SHADOWING — the warning names no remedy and a reinstall does not remove an HKCU key; the doc… · Applied
  - LOW-003 · `—` · the hardware check's prose timing includes a wait on the shared model lock when a Note-tab rendering is in fli… · Applied as documentation
  - LOW-004 · `benchmark.py` · `benchmark.py` `run_worker` docstring named the wrong dispatch step · Applied
  - LOW-005 · `scripts/register-native-host.py --unregister` · `scripts/register-native-host.py --unregister` treated only WinError 32 as "in use", but deleting a RUNNING im… · Applied
  - LOW-006 · `[InstallDelete]` · a part-way upgrade (after `[InstallDelete]` cleared the program folders) leaves the app unstartable until Setu… · Applied as a named residue in the threat model's THE INSTALL…
  - LOW-007 · `release.yml` · `release.yml` gave the BUILD job `id-token: write` · Applied
  - LOW-008 · `docs/release/pilot-builds.md` · `docs/release/pilot-builds.md`'s `gh attestation verify` accepted an attestation from any workflow or branch o… · Applied
  - LOW-009 · `packaging/scribe.iss` · `packaging/scribe.iss` left a foreign clinic-policy value silently · Applied
  - LOW-010 · `PolicyForeign` · the `PolicyForeign` comment in `scribe.iss` misdescribed the uninstall log · Applied
  - LOW-011 · `—` · H.1 doc-class wording corrections across the threat model, the data-flow map, the retention schedule and the i… · Applied
  - LOW-012 · `—` · the data-flow Components table lacked the dev extension ID and said the setup script and prose-runtime install… · Applied
  - LOW-013 · `docs/design-system.md` · `docs/design-system.md` gave the source-checkout remedy as THE remedy for a disabled prose style and printed `… · Applied
  - LOW-014 · `app.lock` · AGENTS.md (twice) said the dev channel touches the production folder only through `app.lock`, omitting the one… · Applied
  - LOW-015 · `exclusions.native_host_entries` · AGENTS.md named `exclusions.native_host_entries`, a method of the `WindowsLayer` seam · Applied
  - LOW-016 · `—` · retention, data-flow flow 8 and AGENTS said the old models are MOVED to the dev folder; Task 2.6 COPIES them a… · Applied
  - LOW-017 · `medium` · flow 8's model-pack sentence read as if the pack holds whisper `medium` only; AGENTS step 4 lacked "(after Pha… · Applied
  - LOW-018 · `is_frozen=False` · five app-side no-sockets children did not pin the production channel, so they could pass in the dev layout wit… · Applied
  - LOW-019 · `Win32_Process.Create` · the installer's "no launch" test did not exclude a WMI-driven launch (`Win32_Process.Create`) · Applied
  - LOW-020 · `TestNoNetworkAndNoDefenderChange` · C1 (installer makes no network connection) and C10 (no Defender exclusions) had no pin · Applied
  - LOW-021 · `VERSION` · the spec's version test matched text, not meaning · Applied
  - LOW-022 · `TestHostRegistrationLog.test_it_reads_this_channels_key` · no test pinned that the host log and the Status tab read THIS channel's registry key · Applied

### Round 23 - 2026-10-03 - Phase H (Task H.2), in-session /review-loop pass 2 — re-review after round 22's fix (executor stage-4 leg i4-x2)
- Round status: Closed. All 5 Applied by leg i4-x2.
- Source: Claude Code
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `desktop/src/scribe_desktop/status.py` · in the installed app a BROKEN per-user entry that wins was told "reinstall Clinic Scribe", which cannot fix it… · Applied
  - LOW-002 · `scripts/build-release.py` · the packaged self-check ran with no time limit; a frozen app that fails at start shows the windowed bootloader… · Applied
  - LOW-003 · `.github/workflows/release.yml` · the silent install's exit code was never checked, and a missing `ISCC.exe` (or any tool) ended the build with … · Applied
  - LOW-004 · `docs/lessons.md` · round 22 LOW-005's WinError 5 handling was not reflected in the lesson that describes the script's in-use hand… · Applied

### Round 24 - 2026-10-03 - Phase H (Task H.2), in-session /review-loop pass 3 — re-review after round 23's fix (executor stage-4 leg i4-x3)
- Round status: Closed. LOW-001 Applied by leg i4-x3; composer suite (2026-10-03 ~05:31) green — ruff clean, mypy clean, pytest 5771 passed / 23 skipped (rounds 24–26 together, exactly the expected +13). `/review-loop` CONVERGED here at loop round 3 of cap 3: no CRIT/HIGH/MED, and the one 🆕 LOW is fixed and verified. No cap raise was warranted. Closed by executor leg i4-x4.
- Source: Claude Code
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `desktop/src/scribe_desktop/benchmark.py` · the doc says the packaged worker is its own boundary ("one type-name line, exit 1"), but a non-number `--audio… · Applied

### Round 25 - 2026-10-03 - Phase H (Task H.3), /simplify over the whole plan diff (executor stage-4 leg i4-x3)
- Round status: Closed. All 3 Applied by leg i4-x3; verified by the composer suite of 2026-10-03 ~05:31 (pytest 5771 passed / 23 skipped, ruff and mypy clean). Closed by executor leg i4-x4.
- Source: Claude Code simplify
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - SIMP-001 · `"medium"` · the shipped whisper model was spelled `"medium"` in three places — `transcription.DEFAULT_WHISPER_MODEL`, `ben… · Applied
  - SIMP-002 · `install_layout.instance_guard_root` · `install_layout.instance_guard_root` re-spelled `data_root("production")`'s body · Applied
  - SIMP-003 · `exclusions.WER_EXCLUDED_APPLICATIONS` · `exclusions.WER_EXCLUDED_APPLICATIONS` repeated the two production executables · Applied

### Round 26 - 2026-10-03 - Phase H (Task H.4), /security-review over the whole plan diff (executor stage-4 leg i4-x3)
- Round status: Closed. All 4 Applied by leg i4-x3; verified by the composer suite of 2026-10-03 ~05:31 (pytest 5771 passed / 23 skipped, ruff and mypy clean; no `.iss` or extension change, so no ISCC compile or `npm run qa` was owed). Closed by executor leg i4-x4.
- Source: Claude Code security-review (portable threat-model checklist; no native reviewer is listed in this session)
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - SEC-001 · `scripts/build-release.py` · the extension build (`npm ci` + the Vite build, third-party code with write access to the bundle) ran AFTER th… · Applied
  - SEC-002 · `.github/workflows/release.yml` · the build of record ran `checkout`, `setup-python` and `setup-node` by movable tags (the pin test exempted `ci… · Applied
  - SEC-003 · `status.read_registration_status` · a registry manifest path (or the manifest's launcher path) on a network share was stat'ed / opened at every ap… · Applied
  - SEC-004 · `scripts/build-release.py` · the quote refusal missed the curly single quotes U+2018–U+201B, which PowerShell also ends a single-quoted str… · Applied

### Round 27 - 2026-10-03 - Phase H Task H.5, independent cross-family codex peer review over the whole plan diff (pass stage-4.p1, peer_round 1 of cap 5; eight file-scoped slices)
- Round status: Closed (0 pending). 11 Applied by leg i4-x6 and PR-MED-022 routed to Task H.6 `[pending-hardening]`; composer suite 4 5805 passed / 23 skipped, ISCC 6.7.3 re-compile exit 0; codex round 28 confirmed the fixes and raised 5 LOW residues as its own findings.
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-MED-019 · `packaging/scribe.iss:330` · A failed post-copy model verification still finishes with a successful installer exit status; only the message… · Applied
  - PR-LOW-020 · `packaging/scribe.iss:124` · The uninstall message incorrectly assigns seven-year retention to live sessions and implies a fixed duration f… · Applied
  - PR-LOW-021 · `scripts/build-release.py:33` · The build’s help text describes the superseded audit-before-extension order. · Applied
  - PR-LOW-022 · `scripts/setup-models.py:8` · The setup documentation still describes the app’s Cliniko client as read-only, contradicting the implemented d… · Applied
  - PR-LOW-023 · `desktop/src/scribe_desktop/install_layout.py:248` · The UNC helper’s docstring overstates the protection, contradicting the accepted redirected-storage residue (C… · Applied
  - PR-MED-020 · `desktop/src/scribe_desktop/status.py:57` · Mixed-separator UNC paths bypass SEC-003 and can trigger SMB access at startup. A value such as `\/server/shar… · Applied
  - PR-LOW-024 · `scripts/generate-extension-key.py:62` · `--out` permits writing an unencrypted private key into a non-gitignored repository file. For example, `--out … · Applied
  - PR-MED-021 · `desktop/src/scribe_desktop/benchmark.py:197` · Benchmark paths bypass the UNC refusal used by the other model loaders, allowing SMB traffic outside C1’s Clin… · Applied
  - PR-MED-022 · `desktop/tests/test_ui_screens.py:727` · The modified microphone polling tests still inspect real production model paths, violating C6. `profile_root` … · Include in plan
  - PR-LOW-025 · `docs/security/data-flow-map.md:139` · The registration flow retains a space-free-path requirement contradicted by the verified installation location… · Applied
  - PR-LOW-026 · `docs/security/retention-schedule.md:33` · Losing a private extension key does not change the unpacked extension’s ID; this claim could prompt unnecessar… · Applied
  - PR-LOW-027 · `docs/security/threat-model.md:3070` · Documentation guarantees deletion of damaged model copies despite an explicitly handled deletion-failure path. · Applied

### Round 28 - 2026-10-03 - Phase H confirmation of round 27's fix, independent cross-family codex peer review (pass stage-4.p1, peer_round 2 of cap 5; two file-scoped slices)
- Round status: Closed (0 pending). All 5 Applied by leg i4-x8; composer suite 5 5835 passed / 23 skipped; codex round 29 confirmed them and raised 1 LOW sibling as its own finding.
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-LOW-028 · `desktop/src/scribe_desktop/install_layout.py:260` · The UNC helper also rejects legitimate extended local paths such as `\\?\C:\models`, so the new benchmark guar… · Applied
  - PR-LOW-029 · `desktop/src/scribe_desktop/benchmark.py:588` · The benchmark’s temporary audio path remains an unguarded sibling: a UNC temporary directory causes filesystem… · Applied
  - PR-LOW-030 · `desktop/tests/test_frozen_runtime.py:815` · The network-refusal tests delegate to the real filesystem if the guard regresses, rather than failing before n… · Applied
  - PR-LOW-031 · `packaging/scribe.iss:213` · The damaged-model comment retains the deletion guarantee that PR-LOW-027 corrected elsewhere. · Applied
  - PR-LOW-032 · `docs/security/threat-model.md:215` · The single-instance section still claims the lock is the sole developer-channel use of the production folder, … · Applied

### Round 29 - 2026-10-03 - Phase H confirmation of round 28's fix, independent cross-family codex peer review (pass stage-4.p1)
- Round status: Closed (0 pending). PR-LOW-033 and its five siblings Applied by leg i4-x10; composer suite 6 5835 passed / 23 skipped; codex round 30 confirmed the class closed and raised 1 docs-only LOW on the new comments.
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-LOW-033 · `desktop/tests/test_transcription.py:1059` · PR-LOW-030 leaves an unprotected sibling: the UNC availability/resolver test lacks a filesystem tripwire, desp… · Applied

### Round 30 - 2026-10-03 - Phase H confirmation of round 29's fix, independent cross-family codex peer review (pass stage-4.p1)
- Round status: Closed (0 pending). PR-LOW-034 Applied by leg i4-x12 (comments only); closed on composer suite 7 (5835 passed / 23 skipped) without a confirmation round, per the cap verdict (gate record `h5-peer-close`, peer_round 4 of cap 5). Peer pass stage-4.p1 CLOSED, trajectory 12 → 5 → 1 → 1.
- Source: independent cross-family codex peer review
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-LOW-034 · `desktop/tests/test_language_model_runtime.py:722` · New comments overstate the tripwire’s coverage as all filesystem calls; it patches only eight named `Path` met… · Applied

### Round 31 - 2026-10-03 - Tasks 3.1 and 3.6, the first Release run's failure (executor stage-3 leg i3-x9)
- Round status: Closed (0 pending). MED-001 was Applied by leg i3-x9 at 2026-10-03T10:02:57+10:00. Closed 2026-10-03 (composer): the practitioner regenerated the lock (59 pins), the composer suite passed, and the re-dispatched `Release` run 37081519723 on `e730cd5` was green and attested.
- Source: first Release run (CI), composer-observed
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - MED-001 · `scripts/lock-build-requirements.py:57` · the hashed build lock lacked PyInstaller's build backend. `build-release.py` installs the pinned PyInstaller s… · Applied

### Round 32 - 2026-10-03 - Task H.6 (the models-root pin), in-session /review-loop pass 1 (executor stage-4 leg i4-x13)
- Round status: Closed (0 pending). All 3 Applied by leg i4-x13 at 2026-10-03T11:55:00+10:00; ruff clean, mypy clean (58 source files). Closed 2026-10-03 by the composer's suite 8: ruff clean, mypy clean (58 files), pytest 5872 passed / 9 skipped.
- Source: in-session /review (the composed /review-loop), over `git diff ee6b657` including uncommitted work
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `desktop/tests/test_frozen_runtime.py` · the exempt set was checked once by reading; nothing stopped a later test, or a module-level `pytestmark`, from… · Applied
  - LOW-002 · `desktop/tests/test_install_layout.py` · its `setenv("LOCALAPPDATA", …)  # no model is there` comment was stale under the pin, because the models root … · Applied
  - LOW-003 · `desktop/tests/conftest.py` · wording. The pin's docstring said "full here", which is ambiguous outside this computer. The real-ML tripwire'… · Applied

### Round 33 - 2026-10-03 - Task H.6, in-session /review-loop pass 2 — re-review after round 32's fix (executor stage-4 leg i4-x13)
- Round status: Closed (0 pending); no findings.
- Source: in-session /review (the composed /review-loop), the round-32 fix delta plus a re-read of the whole H.6 diff
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 34 - 2026-10-03 - Task H.6, cross-family peer pass stage-4.p2 (composer-seat codex)
- Round status: Closed (0 pending); no findings.
- Source: codex `gpt-6-astra` (medium), read-only sandbox, `.cursor/loops/stage-4-peer-r34A.log` in the main checkout; peer_round 1 of cap 5
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 35 - 2026-10-03 - Phase P.1 live smoke on the installed 0.1.0 (practitioner-observed)
- Round status: Closed on the composer-run suites (MED-001 Applied by executor stage-5 leg i5-x1; the remaining overlap is round 36 MED-001).
- Source: practitioner smoke (Task P.1 step 10), composer-observed from the installed app's log
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - MED-001 · `desktop/src/scribe_desktop/session.py` · the first recording after installing failed one second after Start, and the cause cannot be read back because … · Applied

### Round 36 - 2026-10-03 - round 35 MED-001's fix diff (in-session /review-loop pass 1)
- Round status: Closed on the composer-run suites (MED-001 Applied as the practitioner's option (b), leg i5-x2); the 8 LOW Applied.
- Source: in-session /review (the composed /review-loop) over the uncommitted diff, plus one independent read-only general-purpose subagent asked to find failing or flaky tests (the executor cannot run pytest: verify=composer)
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - MED-001 · `ml_warmup.py` · a Start made while the warm-up still runs withholds the live worker, but the warm-up's own imports carry on be… · Applied
  - LOW-001 · `ui/transcript.py` · the not-ready view showed the header "Live — updates while recording" although nothing would update. · Applied
  - LOW-002 · `ml_warmup.py` · the causal story read as confirmed. · Applied
  - LOW-003 · `enrolment.py:167` · pattern siblings without a detail word. · Applied
  - LOW-004 · `tests/test_integration_no_sockets.py` · the "mirrors app.main" proof did not run the new start-up imports. · Applied
  - LOW-005 · `session.py` · `live_transcriber state=not_attached` was logged before the capture worker started, so a failed Start left a l… · Applied
  - LOW-006 · `audio_capture.status_detail_code` · `is True` would misread a truthy non-bool flag. · Applied
  - LOW-007 · `ui/transcript.py` · a not-ready Start adopted a poster token an earlier failed Start left pending. Harmless today, since that work… · Applied
  - LOW-008 · `test_audit.py` · three `app.main` tests started a real warm-up thread whose offline check depends on what earlier tests left in… · Applied

### Round 37 - 2026-10-03 - round 36 MED-001's option (b) delta (in-session /review-loop pass 2)
- Round status: Closed on the composer-run suites; 4 LOW Applied, converged (no CRIT/HIGH/MED).
- Source: in-session /review over the leg i5-x2 delta (`ml_warmup.holds_start`, `SessionScreen.set_start_hold` / `start_held`, `ChromeBridge._start`'s `getting_ready`, the wiring, tests and docs), plus the same independent read-only subagent. It traced `Harness.command`'s per-call `state_rev`, that a real `SessionController` constructor touches nothing, that the refusal precedes `SessionController.start` (no audit `begin`), the `REASON_PATTERN` / message limits, and every fake-clock boundary. It predicted no failing test.
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `ui/session_screen.py` · a third hold check inside `_start`, redundant because both callers check before clearing the tick. · Applied
  - LOW-002 · `ui/main_window.py` · a voice enrolment opens a microphone stream beside the warm-up's imports, the same hazard. · Applied
  - LOW-003 · `tests/test_integration_no_sockets.py` · the child's `warmup.wait(45)`, after the start-up work, could overrun the parent's 60 s READY read on a cold, … · Applied
  - LOW-004 · `ui/session_screen.py` · it still said the tick is cleared whatever the outcome. · Applied
  - LOW-005 · `on_start` · when both apply, the two Starts name different reasons first. · dropped as harmless

### Round 38 - 2026-10-03 - cross-family peer pass stage-5.p1 over the rounds 35–37 fix (composer-seat codex)
- Round status: Closed (0 pending). 4 Applied by leg i5-x3; composer suite 3: ruff clean, mypy clean (59 files), pytest 5904 passed / 9 skipped; codex round 39 confirmed all four fixes with no new finding.
- Source: codex `gpt-6-astra` (medium), read-only sandbox, `.cursor/loops/stage-5-peer-r38{A,B,C}.log` in the main checkout; peer_round 1 of cap 5
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - PR-LOW-A01 · `desktop/src/scribe_desktop/ui/models.py:212` · The deferred-transcription message guarantees recording is unaffected even when warm-up imports still overlap … · Applied
  - PR-LOW-B01 · `desktop/tests/test_live_session.py:803` · The slow-load test does not prove capture progresses while model loading is blocked; queued audio could drain … · Applied
  - PR-LOW-B02 · `desktop/tests/test_integration_no_sockets.py:455` · The child can announce READY with warm-up still running, allowing the test to pass without reaching the claime… · Applied
  - PR-LOW-C01 · `docs/design-system.md:342` · The documented timeout starts at launch, conflicting with the warm-up-start boundary specified elsewhere. · Applied

### Round 39 - 2026-10-03 - confirmation of round 38's fix, peer pass stage-5.p1 (composer-seat codex)
- Round status: Closed (0 pending); no findings.
- Source: codex `gpt-6-astra` (medium), read-only sandbox, `.cursor/loops/stage-5-peer-r39A.log` in the main checkout; peer_round 2 of cap 5
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 40 - 2026-10-03 - Task P.3 live smoke on 0.1.0 and 0.1.1 (practitioner-observed)
- Round status: Closed (0 pending). 2 Applied by legs i5-x4/i5-x5 (reconciled by leg i5-x6). Closed 2026-10-03 by the composer: suite 4 — ruff clean, mypy clean (59 files), pytest 5912 passed / 9 skipped; an ISCC 6.7.3 compile of `packaging/scribe.iss` against a placeholder bundle, exit 0, "Successful compile"; codex round 43, 0 findings.
- Source: practitioner smoke (Task P.3), composer-observed from the Finish-page screenshots and the installed app's log
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `packaging/scribe.iss` · the Finish page shows only the first two paragraphs of the caption the script sets. · Applied
  - LOW-002 · `desktop/src/scribe_desktop/session.py` · a Discard pressed while the live worker is mid-window waits up to `LIVE_STOP_TIMEOUT_SECONDS` (10 s) to stop i… · Applied

### Round 41 - 2026-10-03 - round 40's fix diff (in-session /review-loop pass 1)
- Round status: Closed (0 pending). 6 LOW Applied; closes with the round 40 fix on the composer-run full desktop suite and the ISCC compile check.
- Source: executor stage-5 legs i5-x4/i5-x5 (in-session), plus one independent read-only subagent review (general-purpose), over the whole `git diff` against `33ed7cc` (14 files).
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `ui/main_window.py` · while a discard waits at RECORDING, a close said "Recording in progress - Finish or Discard the session before… · Applied
  - LOW-002 · `ui/session_screen.py` · a Start refused mid-discard (by the `_start` guard) had already cleared the desktop consent tick, unlike the r… · Applied
  - LOW-003 · `ui/session_screen.py` · `TaskThread.run` catches only `Exception`. A non-`Exception` escaping it would emit neither signal and hold ev… · Applied
  - LOW-004 · `ui/main_window.py` · it said the discard reservation is held synchronously on the GUI thread. · Applied
  - LOW-005 · `ui/models.py` · "The app is still transcribing - wait for it to finish." was shown for a discard wait, and already for a draft… · Applied
  - LOW-006 · `docs/design-system.md` · the line sits ABOVE the progress bar, not under it; and the threat model's long parenthetical broke the CUSTOD… · Applied

### Round 42 - 2026-10-03 - round 41's fixes (in-session /review-loop pass 2)
- Round status: Closed (0 pending). 1 LOW Applied (fix-induced, docs-only); /review-loop CONVERGED at loop round 2 of cap 3 (no CRIT, HIGH or MED; triage-and-ship).
- Source: executor stage-5 leg i5-x5. The whole diff was re-read after the interrupted leg i5-x4, without trusting memory of it.
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".
  - LOW-001 · `docs/design-system.md` · round 41's rewrap left a line break mid-sentence in the new bullet. · Applied

### Round 43 - 2026-10-03 - cross-family peer pass stage-5.p2 over the round 40 fixes (composer-seat codex)
- Round status: Closed (0 pending); no findings.
- Source: codex `gpt-6-astra` (medium), read-only sandbox, `.cursor/loops/stage-5-peer-r43{A,B}.log` in the main checkout; peer_round 1 of cap 5
- Compacted 2026-10-04 → findings-installation.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

## Tasks
Paths are under `desktop/src/scribe_desktop/` unless stated. Every code task's verification is the plan's Validation section (composer-run suites) unless the task names its own. Phases are grouped for `/execute-loop`: foundational layout and identity (Phase 1) are isolated ahead of the frozen-runtime work (Phase 2) and the build (Phase 3).

### Phase 0 — Spikes (agent builds, PRACTITIONER verifies from a normal terminal)
- [x] 🟩 **0.1 Frozen app runtime, run in an ISOLATED profile.** A spike `packaging/spike/scribe.spec` building `scribe-app.exe` on Python 3.14 (fallback 3.12). Checks:
  - the PySide6 `windows` platform plugin;
  - the ctranslate2, onnxruntime and `llama_cpp` DLLs load;
  - the keyring backend resolves to `WinVaultKeyring` (pin it explicitly if entry points are lost);
  - `importlib.resources` finds `config_defaults/*.json`;
  - SAPI through `win32com`;
  - `QtNetwork`/`QtWebSockets` excluded (`Qt6Network.dll` absent);
  - the bootloader built from source;
  - whether `sys.stdin`/`sys.stdout` are None under the windowed bootloader (input to Task 0.2 and Task 2.1).

  **Isolation is a prerequisite to the first launch (round 1 PR-MED-003).** Phase 0 runs before `install_layout` exists, and today's start-up opens Past sessions, the sessions root, `audit.prune()` and `run_sweep()` (`app.py:569-593`). So:
  - the practitioner launches the spike ONLY from a persistent normal PowerShell with `$env:LOCALAPPDATA` set to a scratch folder (for example `C:\scribe-spike\Local`), never from Explorer. Every store and the models root read `LOCALAPPDATA` (`exclusions.py:222`, `benchmark.py:142-146` and the Key Findings builder table);
  - the models are COPIED into `<scratch>\ClinikoScribe\models` first;
  - no clinic key, Past session, audit row or profile is copied in;
  - the spike adds no clinic;
  - before and after the spike, the practitioner records the newest modified time under `%LOCALAPPDATA%\ClinikoScribe` (the real folder) and confirms it is unchanged.

  Done when: self-test 2/2, one SAPI sample transcribed, prose rendered in one style, the real data folder unchanged, the interpreter choice recorded (D12 build input), the stdio result recorded, and any hidden imports or hooks listed for Task 3.2.
  - **Spike inputs BUILT 2026-10-02 (stage-0 leg i0-x1); practitioner run OUTSTANDING** — `packaging/spike/scribe.spec` (one-folder windowed, no UPX, `collect_dynamic_libs` for ctranslate2/onnxruntime/`llama_cpp`, `copy_metadata("keyring")`, QtNetwork/QtWebSockets excluded and any `Qt6Network*`/`Qt6WebSockets*` binary filtered with a printed `SPIKE-FILTERED` line), `spike_app_entry.py` (an isolation guard that refuses unless `LOCALAPPDATA` is set and is not inside the Shell's real Local AppData known folder; a `-m scribe_desktop.benchmark` worker dispatch prototyping D11, since frozen `benchmark.run_all` re-spawns `sys.executable`; `--spike-checks`; two pipe-echo child modes), `spike_checks.py` (12 checks, each USING the library) and `spike_stdio.py`; runbook `packaging/spike/RUNBOOK.md` § Task 0.1. Results land in `<scratch>\spike-results\checks.txt` / `stdio.txt`.
  - **Verified from code (2026-10-02):** every store root and the models root resolve from `LOCALAPPDATA` (else `Path.home()`): `app.py:251` lock, `clinics.py:334`, `session_store.py:245`, `audit.py:145`, `logging_setup.py:468`, `note_config.py:913`, `past_sessions.py:144`, `practitioner_profile.py:275,282`, `benchmark.py:143-146` (models; raises when unset), `exclusions.py:222` (via the layer). **Residues the scratch profile does NOT isolate** (named in the runbook): Windows Credential Manager (`secure_storage.py:23` service prefix; the Status self-test writes then deletes `ClinikoScribe/test`, and the spike makes one read of a non-existent entry); the named mutex `Global\ClinikoScribe-app-<user>` (`app.py:124`) and the pipe `ClinikoScribe-<SID>` (`pipe_server.py:89`) — so the real app AND Chrome must be closed; HKCU reads of the Chrome link (`status.py:35`) and WER (`exclusions.py:201`), read-only; `%TEMP%` (the GUI benchmark's SAPI WAV, `benchmark.py:361`); Documents (`ui/past_sessions.py:861`, export only — the runbook says do not export). Qt's own `QStandardPaths` uses the Shell, not the variable; the app uses it only for that export.
  - **RESULT 2026-10-02 (practitioner run, recorded leg i0-x12)** — evidence: `.cursor/loops/stage-0-practitioner-results.md` § Task 0.1 (run from ~15:58, resumed ~19:28 +10:00, normal PowerShell, C7).
    - **Done when, item by item — all evidenced:**
      - **Self-test 2/2:** the scratch Status tab shows "credential_store: PASS (store/retrieve/delete round-trip); session_crypto: PASS (encrypt/decrypt + post-destruction failure) → 2/2", with NO warning lines.
      - **One SAPI sample transcribed:** `sapi_whisper: PASS (35.9 s) audio_s=53.2 words=142 load_s=5.3 rtf=0.482`.
      - **Prose rendered in one style:** `prose: PASS (11.9 s) load_s=6.9 render_s=4.7 passed=1 failed=0 errored=0` (the spike check uses the "narrative" provider).
      - **The real data folder unchanged:** step 2 (BEFORE) and step 22 (AFTER) both read `C:\Users\eliem\AppData\Local\ClinikoScribe\logs\scribe-app.log` with LastWriteTime `2/10/2026 8:00:57 AM` — "IDENTICAL".
      - **The interpreter choice (D12 build input):** **Python 3.14.6, no 3.12 fallback**.
        - PyInstaller **6.22.3**, from source tag `v6.22.3` at commit `ecd7993d65c43b254f4e3f718e36d5b4a70a3ed5`. The wheel built from it has sha256 `f25f5dc0b8381d689569b48dcf1884606d18406a736e5e70620b5dbed15cdebf`.
        - `pyinstaller-hooks-contrib` **2026.8**. The install added only `altgraph 0.17.5` and `pefile 2024.8.26` (`Compare-Object` shows `=>` additions only, no `<=` line). `pip check` reports "No broken requirements found."
        - **Bootloader built from source (D1):** `vswhere` reported "Visual Studio Build Tools 2026", so route 6a. `waf all --target-arch=64bit` from a PLAIN PowerShell found MSVC 14.51.36231 (`…\18\BuildTools\VC\Tools\MSVC\14.51.36231\bin\HostX64\x64\CL.exe`), with CFG enabled, and "'install_releasew' finished successfully".
        - The `runw.exe` SHA-256 before (shipped) was `2291F269C3A3804FDE1079462239E09A8B32FFFBEEAA8F628A531FAF5BE77D41`; after (rebuilt) it is `86D9C90E36660C6DC2EBB084131D199A36E1B36779D8CA3ED1762FF5E3485B9B`. They differ, so it was rebuilt here, and the build used the rebuilt one.
        - The build SUCCEEDED in 141.8 s.
      - **The stdio result:**
        - GUI launch (step 18, started from PowerShell with no pipes handed to it): `gui-launch before: stdin=None(handle=none) stdout=None(handle=none) stderr=None(handle=none)`, the same as `stdio_at_entry` in the checks;
        - a child of the exe given pipes (the echo children, and the benchmark worker): all three `present(handle=valid)`, adaptation `stdin=kept stdout=kept`;
        - `stdio_pipe_raw` and `stdio_pipe_adapted` both `echo=ok`.
        - So the windowed bootloader leaves the streams None only when the parent supplies none, and inherited pipes arrive intact. Task 2.1's worker can keep JSON on stdout; its temp-file branch ("If Task 0.1 found it None") is not triggered by this evidence.
      - **Hidden imports, hooks and bundle scope listed for Task 3.2:** below.
    - **The 12 checks (verbatim, 2026-10-02T16:13:15):** "12 of 12 passed".
      - frozen `python=3.14.6 frozen=True bundle=yes`;
      - qt_platform `platform=windows`;
      - qt_network `importable=none loaded=none dlls=none`;
      - keyring `backend=keyring.backends.Windows.WinVaultKeyring … read_missing=None`;
      - config `defaults=6 profiles=1`;
      - audio `portaudio=PortAudio V19.7.0-devel input_devices=11`;
      - onnx `onnxruntime=1.28.0 silero_inputs=3 speaker_inputs=1`;
      - sapi_whisper and prose as above.
      - So the ctranslate2 (whisper), onnxruntime and `llama_cpp` (prose) DLLs load, and SAPI through `win32com` synthesised the sample. Step 10 found no `Qt6Network*`/`Qt6WebSockets*` DLL in `dist`.
      - Step 11's refusal box appeared with the guard's text (isolation holds). The step-20 scratch log shows `app_start` / `pipe_server state=listening` / `app_exit state=closed` and NO `uncaught_exception`.
      - The GUI's Microphone tab showed whisper `medium` ready, silero ready, and the speaker model "installed - verified when it loads". The Practitioner tab loads, and "Narrative" is selectable.
    - **Task 3.2 inputs (from the build log, `warn-scribe.txt` and the hook log):**
      - **The Qt network filter is LOAD-BEARING.** The build printed ONE `SPIKE-FILTERED PySide6\Qt6Network.dll (from …\PySide6\Qt6Network.dll)` line: a PySide6 hook adds `Qt6Network.dll` even with `PySide6.QtNetwork` excluded (`warn-scribe.txt` confirms "excluded module named PySide6.QtNetwork"). Task 3.2's spec must keep the binary filter, not only the module exclude, and Task 3.5's audit must keep checking the DLL.
      - **Hidden imports the spec carried, all needed:** `scribe_desktop.native_host`, `scribe_desktop.speaker_eval`, `keyring.backends.Windows`, `win32timezone`.
      - **Build WARNINGs:** hidden imports `pycparser.lextab`, `pycparser.yacctab` and `tzdata` not found. None was hit at run time (12/12 and the GUI ran), so they are candidates for an explicit exclude or `collect` decision, not failures.
      - **Missing modules in `warn-scribe.txt`:** all optional or other-platform — `win32com.gen_py`, keyring's Linux/macOS backends, `pydantic.BaseModel` (conditional), ctranslate2's converters (`torch`/`tensorflow`/`transformers`/`opennmt`/`fairseq`), `requests` (llama_cpp grammar / fsspec, delayed), `py3nvml`/`cpuinfo`/`onnxruntime.training`, `openai` (llama_cpp, optional). NO `scribe_desktop` module and no runtime DLL module were reported missing.
      - **Bundle-scope BLOAT to trim in Task 3.2, each to be checked against a run of the 12 checks after trimming:**
        - setuptools, with its vendored jaraco/tomli/wheel/importlib_metadata/zipp and `pyi_rth_setuptools`;
        - the pydantic hook, with `pydantic.mypy`, which pulls in `mypy.*`;
        - jinja2, pygments, anyio, httpx;
        - huggingface_hub (with `hf_api`, the inference client and the cli) and fsspec;
        - certifi, webbrowser, sqlite3;
        - the tensorflow and gi pre-safe hooks were probed;
        - av (PyAV) with cython references (av is a faster-whisper dependency; whether the app's paths use it is for Task 3.2 to check before trimming).
        - Not bloat: lxml/docx, which sample-note ingest uses to read `.docx`.
        - Several of these are network-capable libraries (httpx, huggingface_hub, fsspec, `requests` if collected). Excluding those that are unused at run time also narrows C1's surface.
      - **DLL search directories:** the ctranslate2 DLL dir includes `ctranslate2/../_rocm_sdk_core/bin`, and `llama_cpp\lib` is on the DLL path. Task 3.2 should confirm that the `_rocm_sdk_core` path is harmless when absent, or drop it.
      - **The module search path** had `C:\Recording clinic software` (the repo root) FIRST, and `desktop\src` twice. Task 3.2's spec should set `pathex` to `desktop\src` only, so nothing at the repo root can shadow a bundled module.
    - **OPEN QUESTION — the frozen benchmark's speed (D11 input; NOT a conclusion):**
      - The GUI benchmark ran through the frozen worker path, which spawns `sys.executable -m scribe_desktop.benchmark` and is dispatched by the spike entry. It returned a full result, so the dispatch WORKS: "medium RTF 1.270 load_s 9.98 audio_s 53.2 peak MiB 1787.3 words 142 FAIL", "live window latency 38.1 s per 30 s window (0.79x real time)", and the red line "Benchmark threshold FAILED for medium."
      - On the same 53.2 s / 142-word sample, the in-process `sapi_whisper` check measured `rtf=0.482` at 16:13.
      - The laptop was ON BATTERY during the GUI benchmark (practitioner confirmed).
      - Whether 1.27 comes from the frozen worker path, the benchmark's own measurement, or battery throttling is NOT established.
      - **RESOLVED 2026-10-02 (practitioner, on mains, recorded by the composer 2026-10-03):** frozen spike app medium RTF **0.676** (load 13.65 s, 53.2 s audio, peak 1494.6 MiB, 142 words, OK; live window 20.3 s per 30 s, keeps up) vs the everyday app **0.589** on the same sample — the 1.27 was battery throttling; the frozen build passes (< 1.00, within the 0.75 margin), about 15% slower than the everyday app with a slower first model load. `C:\scribe-spike` was then deleted.
      - Owner: the PRACTITIONER, from a normal terminal, ON MAINS power, BEFORE `C:\scribe-spike` is deleted (Finishing up step 3):
        - (a) the everyday app's Microphone-tab benchmark — record the `medium RTF … load_s …` line;
        - (b) the spike app's GUI benchmark again, from a scratch window (runbook 0.1 steps 14 and 18–19).
      - Compare the two before any D11 / Task 2.1 / Task 2.5 conclusion.
    - **Incidental:** the first `git clone` used the runbook's literal `vX.Y.Z` placeholder and failed harmlessly. The runbook now sets `$v` once at step 5 (leg i0-x12). Task 0.5's note says Task 0.1 ran in a window whose prompt began `PS C:\WINDOWS\system32>` (likely elevated). The scratch guard and the real-folder check held, so the results stand, but the per-user reads in that run were made by the elevated token.
- [x] 🟩 **0.2 Frozen host launched by Chrome** (after Task 0.1: it uses 0.1's interpreter).
  - The agent writes a throwaway `packaging/spike/host.spec`: a one-folder windowed `scribe-host.exe` from the real `native_host.main`.
  - If Task 0.1 found the standard streams None, the spike entry carries the minimal stdio adaptation: binary stdin/stdout obtained through `msvcrt.open_osfhandle(GetStdHandle(...))` before `set_binary_stdio` (`framing.py:54`) and `run_host` (`native_host.py:570-573`). Without it the handshake cannot succeed whatever the folder (round 1 PR-MED-002). Task 2.2 then integrates and hardens this PROVEN adaptation. **(Corrected leg i0-x12 by the RESULT below: under Chrome the frozen host RECEIVED stdin/stdout, so the adaptation ran as a no-op. It is not proven NEEDED under Chrome; Task 2.2 stays planned as defence-in-depth for the no-pipes launch shape Task 0.1 measured.)**
  - The practitioner copies it to `C:\Program Files\ClinikoScribe\` with a manifest there, registers it in HKLM (exact `reg add` lines are given in the task hand-off), removes the HKCU dev registration first, and opens Cliniko with the dev app running.
  - Scope of this check (round 2 PR-MED-001): it is TRANSPORT-ONLY — the badge turns green OK; no recording is started, no patient note is opened beyond the page needed for the link, and no clinical data is written (the dev app's ordinary start-up maintenance — sweep, prune, logs — still runs, as it does every day; round 3 precision note). The dev app here is today's ordinary app on today's data folder, unchanged (Phase 1 has not run), so the spike adds no new data path. The frozen host runs the same `native_host` code as today's host and writes only its content-free log under Chrome's environment (the real `logs\` folder, as today). Isolating the app as well is not required because nothing new runs against the stores.
  - If Program Files fails, repeat at `C:\ClinikoScribe` with `icacls /inheritance:r`, Administrators and SYSTEM full, Users read and execute. Also re-add the HKCU entry once to confirm it shadows HKLM (D9).
  - Done when: the host log shows `origin_verified` and the badge is green OK from the chosen folder; the result is recorded on this task; the HKCU dev registration is restored afterwards.
  - **Spike inputs BUILT 2026-10-02 (stage-0 leg i0-x1); practitioner run OUTSTANDING** — `packaging/spike/host.spec`, `spike_host_entry.py` (the stdio adaptation from `spike_stdio.py` applied UNCONDITIONALLY: it rebuilds `sys.stdin`/`sys.stdout` over `msvcrt.open_osfhandle(GetStdHandle(...))` only when they are None, else a no-op, then calls the unchanged `native_host.main`; one fixed-word line to `%TEMP%\scribe-spike-host-stdio.txt` says which), `host-manifest-programfiles.json` / `host-manifest-c-root.json` (name `com.scribe.cliniko_host`, origin `chrome-extension://mbmhglgadhdohpgbmpbjnaifjagfdfid/`, from `protocol.py:59` / `identity.py:15-17`); runbook § Task 0.2: HKCU export+delete, elevated copy and `reg add … /reg:64`, the transport check (badge; `host_start path=` + `origin_verified state=ok` in `%LOCALAPPDATA%\ClinikoScribe\logs\scribe-host.log`; `pipe_peer path=` in `scribe-app.log`), the `C:\ClinikoScribe` + `icacls` (SIDs `*S-1-5-32-544`/`*S-1-5-18` F, `*S-1-5-32-545` RX) fallback, the HKCU-shadow check, and the restore (**corrected leg i0-x12:** the runbook restores the HKCU link by `reg import` of the step-6 export and checks it `True` — the earlier `register-native-host.py` / WinError 32 restore was superseded in leg i0-x6 and was not used). Expect `host_manifest state=unreadable` and the Status tab's "not registered" while only HKLM holds the link — today's HKCU-only readers (D9).
  - **RESULT 2026-10-02 (practitioner run, recorded leg i0-x12)** — evidence: `.cursor/loops/stage-0-practitioner-results.md` § Task 0.2 (spike at ~22:23 +10:00).
    - **Done when, item by item — all evidenced:**
      - **`origin_verified` and badge green OK from the chosen folder:**
        - `scribe-host.log`: `2026-10-02 22:23:19,802 host_start path=C:\Program Files\ClinikoScribe\scribe-host.exe pid=23756`, then `host_manifest state=unreadable` (expected: the host reads HKCU only, D9), then `origin_verified state=ok`;
        - `scribe-app.log`: `22:23:19,811 pipe_peer path=C:\Program Files\ClinikoScribe\scribe-host.exe`;
        - the badge was green **OK** with Chrome open, with no Cliniko page needed.
        - So **`C:\Program Files\ClinikoScribe` WORKS** (HKLM `/reg:64` → `C:\Program Files\ClinikoScribe\com.scribe.cliniko_host.json`), and the `C:\ClinikoScribe` fallback was NOT needed or created (step 22: "C:\ClinikoScribe: nothing to remove.").
      - **Recorded on this task:** this bullet.
      - **The HKCU dev registration restored afterwards:**
        - steps 20–25: step 21 removed HKLM; step 22 printed "C:\Program Files\ClinikoScribe: removed." / "C:\ClinikoScribe: nothing to remove." / "Continue with step 23.";
        - step 23's `reg import` completed with the equality check `True`;
        - step 25: badge green OK, Status "registered ✓".
    - **Preconditions held:** HKLM absent in both views (4a), neither folder present (4b), no stale pipe file (4c). The HKCU value was the standard `C:\Users\eliem\AppData\Local\ClinikoScribe\com.scribe.cliniko_host.json` (step 5 `True`) and was exported (step 6).
    - **HKCU shadows HKLM — D9 CONFIRMED (step 19):** with BOTH registrations present, the newest `host_start` (22:26:00,335) was `path=C:\Recording clinic software\.venv\Scripts\pythonw.exe`, the per-user host. The badge state at step 19 was not reported separately. While only HKLM held the link, the everyday Status tab said "NOT registered — run scripts/register-native-host.py" (step 13), the HKCU-only-reader gap D9 / Task 2.3 fix.
    - **Stdio under Chrome:** `host before: stdin=present(handle=valid) stdout=present(handle=valid) stderr=None(handle=none) | adapt: stdin=kept stdout=kept`.
      - Chrome hands the windowed frozen host working stdin/stdout, so the adaptation was a no-op. stderr is None, because Chrome supplies none.
      - **Bearing on Task 2.1 / 2.2:** the stdin/stdout adaptation is defence-in-depth for a launch with no pipes (Task 0.1's GUI-launch shape), NOT a need proven under Chrome. Task 2.2 stays planned; its heading's "the adaptation Task 0.2 proved" should be read as "the adaptation Task 0.2 exercised".
      - **stderr = None under Chrome is a real input:** any frozen host code that writes to `sys.stderr` must tolerate None. Per AGENTS.md, the Phase 6 exception hook prints one `uncaught_exception` line to the console as well as the log, so Task 2.2 should confirm that path tolerates a None stderr. The spike's clean `origin_verified` run does not exercise it.
    - **Host build:** the build copy (Python 3.14, no fallback) — "Build complete!" in 44.3 s, with the rebuilt `runw.exe` bootloader. The only warning was hidden import `tzdata` not found. The hooks included pydantic, psutil, setuptools (vendored), webbrowser, zoneinfo and pywintypes; there were no extra DLL search dirs.
    - **Defender (step 3, elevated):** `Start-MpScan CustomScan C:\scribe-spike\dist\scribe-host` completed; `Get-MpThreatDetection` → nothing.
- [x] 🟩 **0.3 Inno mechanics and CI.** A throwaway `.iss` with `PrivilegesRequired=admin`, a `[Code]` `GetSHA256OfFile` check over a 2.5 GB file (timed), the HKLM WER values, the `FilesNotToSnapshot`/`FilesNotToBackup` value forms (does `$UserProfile$` work for `FilesNotToBackup`, or only `%var%`?), the install-folder ACL, and in-place upgrade under the same AppId. Separately, confirm whether `windows-latest` has Inno Setup 6, and which version to pin.
  - Done when: each answer is recorded on this task, and Task 3.4's value forms are fixed.
  - **Spike inputs BUILT 2026-10-02 (stage-0 leg i0-x1); practitioner run OUTSTANDING** — `packaging/spike/inno-spike.iss` (+ `inno-payload.txt`): `PrivilegesRequired=admin`, `x64compatible` (needs Inno 6.3+), a `[Code]` `InitializeSetup` timing `GetSHA256OfFile` over the Task 0.1 scratch copy of the language model (expected digest `LANGUAGE_MODEL_SHA256`; `/DHashFile` / `/DHashExpected` override, plus a 2.5 GB random-file one-liner), an HKLM WER DWORD for a made-up `inno-spike-app.exe`, three `FilesNotToBackup` and three `FilesNotToSnapshot` REG_MULTI_SZ forms for a non-existent `ClinikoScribeSpike` folder (`$UserProfile$…`, literal `%LOCALAPPDATA%…`, Inno-expanded `{localappdata}…`), all `uninsdeletevalue`; compiled twice (`/DAppVer=0.0.1`, `0.0.2`) for the same-AppId upgrade. Runbook § Task 0.3 gives the `reg query` / `icacls` / non-elevated write-probe checks. **Limit stated in the runbook:** the `reg query` proves what LANDS, not what Windows backup HONOURS; whether `FilesNotToBackup` honours `$UserProfile$` is a Microsoft Learn reading (not observable on Windows 11 Home, which has no Windows Server Backup).
  - **CI question ANSWERED 2026-10-02 (stage-0 leg i0-x2, read from `actions/runner-images` `main`):**
    - `windows-latest` = Windows Server 2025, the same image as `windows-2025` and `windows-2025-vs2026` (`README.md` label table; it notes that `-latest` migrations are gradual, over 1–2 months).
    - **`windows-2025-vs2026`** (OS 10.0.26100 Build 33438, image `20260922.246.2`; `images/windows/Windows2025-VS2026-Readme.md`):
      - `InnoSetup 6.7.1`;
      - Visual Studio Enterprise 2026 `18.10.12210.168`, with `Microsoft.VisualStudio.Component.VC.Tools.x86.x64` `18.10.12020.329` and `Microsoft.VisualStudio.ComponentGroup.NativeDesktop.Core`.
    - **`windows-2022`** (OS 10.0.20348 Build 5622, image `20260920.314.1`; `images/windows/Windows2022-Readme.md`):
      - `InnoSetup 6.7.1`;
      - Visual Studio Enterprise 2022 `17.14.37710.0`, with `Microsoft.VisualStudio.Component.VC.Tools.x86.x64` `17.14.36510.44`.
    - So both images can build the PyInstaller bootloader from source (D1).
    - **Recommendation for Task 3.6:**
      - pin **Inno Setup 6.7.1**, with the job ASSERTING the `ISCC` version (fail on any other) rather than trusting the preinstalled copy, because runner images are updated weekly;
      - pin the runner label `windows-2025` rather than `windows-latest`, because of the gradual-migration note.
    - The runbook's 0.3 step 1 now asks for 6.7.1 locally, so local and CI builds match.
    - Sources:
      - https://github.com/actions/runner-images/blob/main/README.md
      - https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-VS2026-Readme.md
      - https://github.com/actions/runner-images/blob/main/images/windows/Windows2022-Readme.md
    - **(Superseded in part leg i0-x12:** the practitioner's local Inno is 6.7.3, not 6.7.1 — see the RESULT's pin recommendation below; the `windows-2025` label and the version assertion stand.)
  - **RESULT 2026-10-02 (practitioner run, recorded leg i0-x12)** — evidence: `.cursor/loops/stage-0-practitioner-results.md` § Task 0.3.
    - **Prior state (Before you start):** check A `False` — Inno Setup was not installed. Check B was all clean: the folder `False`, the uninstall key and WER value not found, and 0 matches in both `FilesNotToBackup` and `FilesNotToSnapshot`.
    - **Inno Setup version:** the practitioner installed it; the compiler banner reads **"Compiler engine version: Inno Setup 6.7.3"**, and ISCC prints **"Non-commercial use only"**. The licensing question is OPEN; see the handoff note.
      - Both spike installers compiled: 0.0.1 "Successful compile (4.343 sec)" and 0.0.2 "(2.891 sec)".
    - **`GetSHA256OfFile` timing:** "SHA-256 took 14235 ms. First 16 characters: 3605803b982cb64a. Matches the expected value: yes".
      - It ran over the Task 0.1 scratch copy of the language model (2.3 GiB, i.e. ≈ 2.5 GB, which meets the task's size), on MAINS power (practitioner confirmed). That is about 14 s per install-time check of the largest model.
      - This reading is from the 0.0.2 run; the 0.0.1 box's timing was not reported.
    - **Per-machine:** HKLM `Uninstall\{5B7E2C1D-9A4F-4E8B-B3C6-2F1D0A9E7C54}_is1` DisplayVersion `0.0.1`; the same key in HKCU was not found, so nothing was written per-user.
    - **WER:** HKLM `ExcludedApplications` `inno-spike-app.exe REG_DWORD 0x1` landed.
    - **Backup and snapshot value forms — every form LANDED VERBATIM as `REG_MULTI_SZ`**, three in each key:
      - `ClinikoScribeSpike_UserProfile` = `$UserProfile$\AppData\Local\ClinikoScribeSpike\sessions\* /s`;
      - `ClinikoScribeSpike_EnvVar` = `%LOCALAPPDATA%\ClinikoScribeSpike\sessions\* /s`;
      - `ClinikoScribeSpike_Expanded` = `C:\Users\eliem\AppData\Local\ClinikoScribeSpike\sessions\* /s`.
      - **The answer to "does `$UserProfile$` work for `FilesNotToBackup`?":** it is WRITTEN unchanged, so Inno does not mangle it. Whether Windows backup HONOURS it there is NOT observable on this computer (Windows 11 Home has no Windows Server Backup). It rests on the Microsoft Learn reading in External Findings, which is not re-checked in this leg (no web). Stated as a residue under C5's "best-effort".
      - **`{localappdata}` expands to the INSTALLING (elevating) account's profile.** Here that is `C:\Users\eliem`, because the practitioner approved UAC as themselves. Under an over-the-shoulder elevation by a different administrator it would be THAT admin's profile, which excludes the wrong user's folder. So D6's "otherwise `%LOCALAPPDATA%`-expanded for the installing user" fallback is weaker than D6 states, and it conflicts with C3 / D8 ("writes nothing per-user"; "every write is … a `$UserProfile$`-relative exclusion pattern").
    - **Install-folder ACL:** every entry inherited — TrustedInstaller F, SYSTEM F, Administrators F, Users RX, CREATOR OWNER F (IO), ALL APPLICATION PACKAGES RX, ALL RESTRICTED APPLICATION PACKAGES RX. A non-elevated `New-Item` of a probe file was "Access to the path … is denied", twice, so Users cannot write the install folder (D1 holds with no custom ACL).
    - **In-place upgrade under the same AppId:** after 0.0.2 over 0.0.1, DisplayVersion is `0.0.2`. The folder holds `inno-payload.txt`, `unins000.dat` and `unins000.exe` — ONE `unins000`, no `unins001`. The upgrade did NOT ask for a folder; it reused the 0.0.1 one (practitioner confirmed).
    - **Uninstall removes every value:** after `unins000.exe`, check B returned exactly to the prior state — folder `False`, uninstall key and WER value not found, 0 matches in both keys.
    - **Done when, item by item:**
      - **Each answer recorded on this task:** yes. The CI question was answered in leg i0-x2. Which version to pin is answered as a recommendation for Task 3.6, recorded in the handoff note as an open item for the practitioner: **pin 6.7.3**, installed explicitly on CI from a SHA-256-checked installer and asserted by `ISCC`'s banner, so local and CI builds match. It supersedes the leg i0-x2 recommendation of 6.7.1.
      - **Task 3.4's value forms fixed:** yes, on Task 3.4, as a recommendation under D6's own rule. Both keys use the `$UserProfile$` form; the expanded and `%LOCALAPPDATA%` forms are rejected.
- [x] 🟩 **0.4 WeSpeaker licence.** Confirm the licence of the `wespeaker-voxceleb-resnet34-LM` ONNX export at its source (the "MIT" claim was dropped as unverified, `plan-practitioner-profile.md` round 8).
  - Done when: the licence text and source URL are recorded here.
  - **ANSWERED 2026-10-02 (stage-0 leg i0-x2): Creative Commons Attribution 4.0 International (CC BY 4.0).** The two sources agree.
    - **Pinned source** (`scripts/setup-models.py:144-147`): `https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM/resolve/main/voxceleb_resnet34_LM.onnx`.
    - **The model repo** (`https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM`; API `https://huggingface.co/api/models/Wespeaker/wespeaker-voxceleb-resnet34-LM`, repo sha `f0c48c298fd835726c27956a5d617bad7115627e`, lastModified 2024-05-06):
      - its `README.md` front matter and the API's `cardData` both read `license: cc-by-4.0`;
      - the card states "License: CC-BY-4.0" and gives a BibTeX citation (Wang et al., "Wespeaker: A research and production oriented speaker embedding learning toolkit", ICASSP 2023);
      - the repo's files are `.gitattributes`, `README.md`, `avg_model`, `config.yaml` and `voxceleb_resnet34_LM.onnx` — there is **no LICENSE file**.
    - **Upstream** `https://github.com/wenet-e2e/wespeaker/blob/master/docs/pretrained.md`, heading "## Model License", verbatim: "The pretrained model in WeNet follows the license of it's corresponding dataset. For example, the pretrained model on VoxCeleb follows Creative Commons Attribution 4.0 International License, since it is used as license of the VoxCeleb dataset, see https://mm.kaist.ac.kr/datasets/voxceleb/."
    - **The code is a separate licence:** the repo-root `LICENSE` is Apache 2.0, which covers the toolkit code, not the model.
    - **Redistribution:** CC BY 4.0 permits copying and redistributing the model, including in our model pack, on condition of attribution. That means:
      - credit the creators (the WeSpeaker authors and the citation above);
      - give the licence name and a link to it (`https://creativecommons.org/licenses/by/4.0/`);
      - link the source;
      - say whether the file was changed (we ship it byte-identical, SHA-256-pinned).
      - The attribution conditions above are CC BY 4.0's standard terms, not quoted from the legal code in this leg.
    - **Caveat, stated plainly, not resolved:** the VoxCeleb dataset page (`https://mm.kaist.ac.kr/datasets/voxceleb/`) says "The VoxCeleb dataset is available to download for research purposes under a Creative Commons Attribution 4.0 International License. The copyright remains with the original owners of the video."
      - The model's own licence (CC BY 4.0, on the card and upstream) carries no research-only term.
      - Whether the dataset page's "for research purposes" framing reaches a model trained on it in clinical or commercial use is not settled by these sources.
      - This applies to TODAY's use of the model too, not only to bundling.
      - It is a practitioner/legal judgement, recorded here for D-I2 and for commercialisation.
- [x] 🟩 **0.5 Defender and Smart App Control.**
  - Run a Defender custom scan of the Task 0.1 bundle: `Start-MpScan -ScanType CustomScan -ScanPath <dist>` then `Get-MpThreatDetection`.
  - Record this computer's Smart App Control state (Windows Security → App & browser control).
  - Done when: both results are recorded. A detection or Smart App Control "On" pauses the plan for a signing decision (C10).
  - **Runbook BUILT 2026-10-02 (stage-0 leg i0-x1); practitioner run OUTSTANDING** — runbook § Task 0.5 (elevated `Start-MpScan` of `C:\scribe-spike\dist\scribe-app`, `Get-MpThreatDetection`, the Windows Security → App & browser control → Smart App Control page as the authority, an optional `VerifiedAndReputablePolicyState` registry reading marked unverified), repeated for the host bundle in § Task 0.2 step 3; C10 stated (no exclusion, no SAC change; a detection or "On" pauses for signing). Note for the record: a locally built exe carries no Mark-of-the-Web, so SmartScreen will not prompt here; the CI-downloaded installer (Phase P) will.
  - **RESULT 2026-10-02 (practitioner run, recorded leg i0-x12)** — evidence: `.cursor/loops/stage-0-practitioner-results.md` § Task 0.5 and § Task 0.2 step 3.
    - **Defender:** `Start-MpScan -ScanType CustomScan -ScanPath C:\scribe-spike\dist\scribe-app` completed with no output, and `Get-MpThreatDetection` → nothing. The host bundle (`dist\scribe-host`, Task 0.2 step 3, admin window) also → nothing. **No detections** on either bundle, built with the from-source bootloader.
    - **Smart App Control: Off**, read by the practitioner on the Windows Security page (the authority). The optional registry reading agrees: `VerifiedAndReputablePolicyState` `REG_DWORD 0x0`.
    - **Done when — both results recorded:** yes. There is no detection and Smart App Control is not "On", so **no signing pause (C10)**. No exclusion was added and Smart App Control was not changed.
    - A note on the first scan: the practitioner was confirming elevation from the prompt shown (`PS C:\Users\eliem>`). The scan completed and the threat list is empty, so the result stands.
- [x] 🟩 **D-I1: Install location.** `[decision]`
  - Options: `C:\Program Files\ClinikoScribe` / `C:\ClinikoScribe` with an explicit ACL.
  - Decide after: Task 0.2.
  - Blocks: Tasks 1.1 (`install_root`), 3.4.
  - **Chosen: `C:\Program Files\ClinikoScribe`** — practitioner, 2026-10-02, on Task 0.2's evidence (the executor's recommendation): `host_start`, `origin_verified state=ok` and `pipe_peer` all from that path, badge green OK. It inherits the admin-only ACL (Task 0.3: Users RX, user write denied), so no custom `icacls` is needed. Journalled as `OWNERSHIP: gate-disposition key=D-I1` in the stage-0 probe log; recorded leg i0-x12.
  - Executor recommendation (2026-10-02, stage-0 leg i0-x1; NOT chosen — the practitioner decides): `C:\Program Files\ClinikoScribe`, IF Task 0.2 shows `host_start path=C:\Program Files\ClinikoScribe\scribe-host.exe` + `origin_verified state=ok` in `scribe-host.log`, `pipe_peer` with the same path in `scribe-app.log`, and a green OK badge — it inherits an admin-only ACL with no custom `icacls` to maintain. Choose `C:\ClinikoScribe` (explicit ACL) only if Chrome reports "Specified native messaging host not found" for the Program Files path.
- [x] 🟩 **D-I2: Bundle the speaker model?** `[decision]`
  - Options: in the model pack (licence permits redistribution) / fetched per computer by `setup-models.py --only speaker-embedding --root {app}\models` run as admin, and verified by the installer's manifest check on the next install.
  - Decide after: Task 0.4.
  - Blocks: Task 3.3.
  - **Chosen: in the model pack**, with the CC BY 4.0 attribution notice beside the file — practitioner, 2026-10-02 (the executor's recommendation). The VoxCeleb "for research purposes" caveat (Task 0.4) goes to the independent privacy/legal review of `docs/practice/`, because it bears on using the model at all, bundled or fetched. Journalled as `OWNERSHIP: gate-disposition key=D-I2` in the stage-0 probe log; recorded leg i0-x12.
  - Executor recommendation (updated 2026-10-02, stage-0 leg i0-x2; NOT chosen — the practitioner decides): **in the model pack.**
    - Task 0.4 found CC BY 4.0 on both the model card and the upstream "Model License" section, and that licence permits redistribution with attribution.
    - Ship an attribution notice beside the file in the pack: creators and citation, "CC BY 4.0" with its link, the source URL, and "unmodified".
    - Task 3.3 then adds that notice to the pack, and H.1's documents mention it.
    - A per-computer fetch would not change the licensing position: the same file under the same licence is used either way.
    - The one open point is the VoxCeleb dataset page's "for research purposes" wording (Task 0.4 caveat). It bears on using the model at all, bundled or fetched, so it is a separate practitioner/legal check, best taken with `docs/practice/`'s independent review or at commercialisation. It is not a reason to prefer the fetch.

### Phase 1 — Channel, layout and the dev separation
- [x] 🟩 **1.1 `install_layout.py` (new).** It provides:
  - `is_frozen()`, injectable;
  - `channel() -> Literal["production","dev"]`;
  - `install_root()`: frozen → the folder of `sys.executable`, checked against D-I1; dev → `None`;
  - `data_root()`: `%LOCALAPPDATA%\ClinikoScribe` or `…\ClinikoScribe-dev`, re-reading the environment on every call; when `LOCALAPPDATA` is unset it keeps today's home-folder fallback;
  - `models_root()`: frozen → `install_root()\models`; dev → `data_root()\models`, keeping `default_models_root`'s raise-when-unset contract (`test_language_model_runtime.py:722`);
  - `app_data_root_via(layer)`, for the `WindowsLayer`-seamed caller.

  A conftest autouse fixture pins the production channel (D2).

  Done when: tests cover both channels, frozen and not, and `LOCALAPPDATA` set and unset.
  - Leg i1-x2 (built; awaiting the composer suite): D-I1 is a PLACEHOLDER — `install_layout.INSTALL_ROOTS` (one named constant, marked `# D-I1 pending — set when the practitioner decides after Task 0.2`) accepts both candidates (`C:\Program Files\ClinikoScribe`, `C:\ClinikoScribe`); the decision narrows that one line plus the pin in `test_install_layout.py`.
  - **D-I1 decided 2026-10-02 (recorded leg i0-x12): `C:\Program Files\ClinikoScribe`.** When Phase 1 resumes (`git stash pop`; the code is held in the stash and was NOT touched here), narrow the placeholder `install_layout.INSTALL_ROOTS` to that one path, drop its `# D-I1 pending` marker, and update the pin in `test_install_layout.py` to match. Tests go through the seams (`is_frozen`, `executable`, `install_root(accepted=)`). Frozen-only behaviour (install root, models root, remedies) keys on `is_frozen()`; channel behaviour (data folder, identities, write guard) keys on `channel()`. The conftest pin is also installed in `pytest_configure`, so collection-time `skipif`s see production; test child processes pin production themselves.
  - **Leg i1-x3: D-I1 APPLIED.** `INSTALL_ROOTS = (r"C:\Program Files\ClinikoScribe",)` (still a tuple, so tests inject their own root through the same seam); the `# D-I1 pending` marker is replaced by the decision's comment, and the pin is now `test_install_layout.py::TestInstallRoot::test_d_i1_the_one_accepted_root_is_program_files`.
- [x] 🟩 **1.2 Repoint every data-folder builder** (the table in Key Findings) to `install_layout`. `benchmark.default_models_root` delegates to `models_root()`.
  - Add a grep test: no `ClinikoScribe` path built outside `install_layout`, with the non-path literals allow-listed BY NAME.
  - Done when: the suite is green with the channel pinned to production, and a dev-channel test shows each store under `ClinikoScribe-dev` (C8).
- [x] 🟩 **1.3 Extension `--mode dev|release` and the dev key** (first: Task 1.4 needs the dev ID). Leg i1-x1: `--out` added to the key script (default unchanged; a relative path is from the repo root) and `extension/key-dev.pem` added to `.gitignore` (the bare `key.pem` entry does not match it); the key run is composer-run.
  - `vite.config.ts`/`manifest.ts` take the key, name suffix (" (dev)") and host name from the mode. `protocol.ts` `HOST_NAME` is injected at build (`define`).
  - FIRST, `scripts/generate-extension-key.py --out extension/key-dev.pem` (gitignored; the script gains `--out`, default unchanged); the dev PUBLIC key is committed and the dev extension ID derived from it is recorded on this task.
  - `manifest.test.ts`/`scaffold.test.ts` cover both modes, and the release mode keeps `mbmh…`.
  - The default `npm run build` stays release, so today's `extension/dist` is unchanged.
  - Done when: `npm run qa` passes, and both builds produce manifests with their own key and host name.
  - Leg i1-x2: the composer ran the key script (exit 0; `git check-ignore` → `.gitignore:28`). **Dev extension ID: `pecfiifdlmdbkifmjkbkeiaflpenfejd`.** The dev PUBLIC key is committed in the new `extension/src/channel.ts` (`CHANNELS.dev.key`), beside the unchanged release key and `mbmh…` id; `channelForMode` maps `dev` → dev, `release`/`production` (Vite's default) → release, and refuses anything else. The dev build outputs to `extension/dist-dev` (gitignored), so `extension/dist` stays release. `HOST_NAME` is `__SCRIBE_HOST_NAME__` from `buildDefines` (vitest injects the release value). `manifest.test.ts` derives each id from its key; `test_identity.py` cross-checks `channel.ts` against `identity.py`.
- [x] 🟩 **1.4 Identity accessors** in `identity.py` (desktop) for each channel:
  - `host_name()`, `extension_id()`, `expected_origin()`, `registry_key()` and `pipe_prefix()`;
  - dev values: `com.scribe.cliniko_host_dev`, the dev ID recorded by Task 1.3, and `ClinikoScribe-dev-`.

  Production constants are unchanged (C2). Consumers switch to the accessors: `native_host.py:70,114,537`, `status.py:14`, `ui/main_window.py:87,234`, `pipe_server.py:176`, `pipe_client.py`.

  Done when: the pins in `test_protocol.py:58`, `test_display_name.py` and `test_pipe_server.py` pass unchanged, and new dev-channel tests pass.
  - Leg i1-x2: the accessors take `of: Channel | None = None` and read `install_layout.channel()` at call time; production constants (`HOST_NAME`, `EXTENSION_ID`, `EXPECTED_ORIGIN`, `REGISTRY_KEY`, new `PIPE_PREFIX`) are unchanged, and `pipe_server.PIPE_PREFIX` is still exported. `scripts/register-native-host.py` registers the running channel's host, origin and install folder (`ClinikoScribe-dev` from source); its legacy-artifact sweep stays on the production name. `test_display_name.py`'s literal `INSTALL_DIR` source pin (not an identity value) was updated to the new expression.
- [x] 🟩 **1.5 One single-instance guard across channels** (D3). Both channels acquire the same per-user exclusion (today's mutex name, plus a lock in a channel-independent location chosen and justified by the executor), so the second app shows "already running" whichever channel started first.
  - Done when: `test_status_and_app.py`'s guard tests pass for both channels, and a cross-channel test proves mutual exclusion through the seam.
  - Leg i1-x2: the lock is `%LOCALAPPDATA%\ClinikoScribe\app.lock` for BOTH channels (`install_layout.instance_guard_root()`), with the mutex name unchanged. Justification: the production folder is the one per-user location both channels already resolve and that a dev build may touch (C8's named exception), and keeping it there leaves today's production lock where it is. The dev build creates only `app.lock` there (pinned by test).
- [x] 🟩 **1.6 Dev write guard (D4).**
  - Add `dev_build_writes_off` to `WriteRefusalName` (`draft_write.py:1054`).
  - `refuse_before_read` gains a `channel`/`allow` input from its two callers (`main_window.py:1874`, `draft_write.py:1180`), and `ui/models.write_control` disables Write with the same reason.
  - Add the wording in `write_refusal_line`; decide whether it joins `WRITE_UNCERTAIN_PREFIXED` (`ui/models.py:399`; expected: no).
  - `config\dev.json` loader on the `PastSessionSettings` pattern.
  - The dev-only Status checkbox, worded "Allow Cliniko writes from this developer build", default off.
  - Update pins `test_write_lines.py:70`, `test_draft_write.py:1649,1666`, `test_audit.py:204-208`.
  - Done when: in production the guard can never refuse (test); in dev it refuses until ticked; the audit row records `last_refusal=dev_build_writes_off`.
  - Leg i1-x2: the pure check is `draft_write.dev_build_writes_off(channel, allow)`, run after `mock_note` and before `record_unreadable`. The settings file lives in `note_config` (`DevSettings`, `load_dev_settings`, `save_dev_settings`, `dev_writes_allowed`), not `draft_write`, because `draft_write` is pinned disk-free. A file it cannot use reads as writes OFF, and production never reads it. If saving the Status checkbox fails, the box is put back and a line says why.
  - **Leg i1-x4: the prefix decision REVERSED and the order moved.**
    - The plan's "expected: no" for `WRITE_UNCERTAIN_PREFIXED` does not survive PR-MED-017's rule, which keys on whether the line invites a Copy, not on whether it refuses before any read (`mock_note` refuses before any read and IS prefixed). The dev line says "copy the note instead", so it IS in `WRITE_UNCERTAIN_PREFIXED`.
    - The guard now runs AFTER the record's own refusals in both `refuse_before_read` and `write_control`: mock → `record_unreadable` → `already_written` / `write_uncertain` → `dev_build_writes_off`. The click path already decides the record first (`write_record_block`), so this matches it. The refusal carries `earlier_attempt_open` from the record.
    - The scenario it closes: in a dev build, a write is allowed and its outcome stays open, then the setting is unticked. The click or button then showed a bare "copy the note instead" with no warning that the earlier write may have reached Cliniko.
    - The audit row still records `last_refusal=dev_build_writes_off`.
- [x] 🟩 **1.7 Remedy lines.** One `install_layout.model_remedy()` and one `registration_remedy()`. Frozen: "Missing or damaged — reinstall Clinic Scribe". Dev: today's script commands. They replace every string in Key Findings' remedy list and update the listed test pins.
  - Done when: both channels are tested and a grep finds no other "run scripts/" string in `src`.
  - Leg i1-x2: remedies key on `is_frozen()` (a source run of either channel has the scripts). The frozen clause is `FROZEN_REMEDY = "reinstall Clinic Scribe"`, placed after each line's own "missing or damaged" wording. The former constants are now functions (`models.language_model_absent_reason()`, `speaker_model_missing_reason()`, `attribution_did_not_run_reason()`, `exclusions.wer_not_excluded_line()`). Not in the plan's list but covered: `language_model._import_llama`'s prose-runtime remedy.
- [x] 🟩 **1.8 Version pin (D12).** One test asserts that pyproject, `__init__.__version__`, `manifest.ts` and `package.json` agree. Version stays `0.1.0` until the first release task bumps it.
  - Leg i1-x2: the pin is in `test_install_layout.py` and also covers both `package-lock.json` copies (root and `packages[""]`), which the plan did not list.

### Phase 2 — Frozen-runtime support
- [x] 🟩 **2.1 Benchmark worker entry.**
  - When frozen, `benchmark.run_all` spawns `[sys.executable, "--benchmark-worker", "--single", …]`.
  - `app.main` dispatches `--benchmark-worker` to `benchmark.main(argv)` BEFORE `QApplication` (`app.py:549`) and before the guard, only when `_WORKER_ENV == "1"` and the argv shape matches exactly. Anything else is ignored, not started.
  - The worker's stdout must exist under the windowed bootloader. If Task 0.1 found it None, write the JSON to a temp file whose path is passed in argv.
  - Done when: tests cover the frozen and dev spawn shapes, and that the dispatch refuses without the env var or with extra arguments.
  - **Leg i2-x1 (built; 🟩 leg i2-x2 on composer suite 1: pytest 5527 passed / 20 skipped, ruff clean, mypy 58 files, `npm run qa` 13 files / 313 tests):**
    - `benchmark.worker_argv` is the one spawn shape: `-m scribe_desktop.benchmark` from source, `WORKER_FLAG` (`--benchmark-worker`) when `install_layout.is_frozen()`.
    - `benchmark.is_worker_argv` admits only the exact shape: the flag first, then the four options once each in order, each value non-empty and not starting with `-`. `benchmark.run_worker` also needs `SCRIBE_BENCHMARK_WORKER=1`.
    - `app.main(argv=None)` calls it right after Task 2.7's check, before logging (so the worker never opens `scribe-app.log` beside the running app), the guard and `QApplication`. Any other arguments are ignored and the app starts as it always has.
    - **The temp-file fallback is NOT built.** Task 0.1's RESULT measured the frozen worker under `subprocess` pipes with stdin/stdout/stderr all `present(handle=valid)`, and the frozen GUI benchmark returned full JSON. The plan's condition ("if Task 0.1 found it None") is not met, so there is nothing for the fallback to defend.
    - Tests: `test_frozen_runtime.py` `TestWorkerArgv`, `TestWorkerDispatch`.
- [x] 🟩 **2.2 Native-host stdio fallback** (integrates and hardens the adaptation Task 0.2 proved).
  - `native_host.main` obtains binary stdin/stdout from `sys.stdin.buffer`, or, when None (frozen windowed), from `msvcrt.open_osfhandle(GetStdHandle(...))` through a small seam.
  - `set_binary_stdio` applies to whichever it got.
  - Done when: the seam is tested with both shapes and protocol tests are unchanged.
  - **Leg i2-x1 (built as defence-in-depth; 🟩 leg i2-x2 on composer suite 1):**
    - Task 0.2 measured that Chrome GIVES the frozen host stdin/stdout, so the fallback is not a proven need. It covers only the no-pipes launch shape Task 0.1 measured.
    - `native_host.binary_stdio(stdin, stdout, open_std=open_std_stream)` returns each stream's `.buffer`, or for a None stream `open_std_stream` (a binary stream over `msvcrt.open_osfhandle(GetStdHandle(...))`, never closing the handle). It returns `None` when either stream cannot be had.
    - `main` then calls `framing.set_binary_stdio(stdin, stdout)`, which now takes the streams it is given and keeps its no-argument default, and `run_host(stdin, stdout, …)`. With no streams the host logs `host_stdio state=absent` and exits 4 before protocol mode.
    - The rebuild branch has never run live: in Task 0.1's no-pipes GUI launch the Win32 handles were invalid as well.
    - **stderr None (Task 0.2's recommendation):** a test pins that `setup_logging` builds no stderr handler, that the main exception hook still writes its one type-name line to the file, and that `QuietHandlerErrors.handleError` does not raise.
    - Tests: `test_frozen_runtime.py` `TestBinaryStdio` and the host-stream tests. `test_native_host.py` / `test_protocol.py` are unchanged.
- [x] 🟩 **2.3 Registry readers in Chrome's order (D9).**
  - A new `WindowsLayer` method returns the host entries for a name in HKCU and HKLM, in both views.
  - `status.read_registration_status` and `_log_registration_paths` report the winning entry and the others.
  - In a frozen build a production-name HKCU entry raises the Status warning.
  - Fake-layer tests cover none, HKCU-only, HKLM-only, both, and the 32-bit view only.
  - **Leg i2-x1 (built; 🟩 leg i2-x2 on composer suite 1):**
    - **The layer method:** `WindowsLayer.native_host_entries(key)` returns `exclusions.HostEntry(hive, view, manifest)` entries in `CHROME_LOOKUP_ORDER`: HKCU 32 → HKCU 64 → HKLM 32 → HKLM 64.
      - The 32-bit-view-first order is Chromium's `GetManifestPathFromRegistry`, taken from its source and not observed here. Task 0.2 observed only HKCU over HKLM.
      - A view whose key or default value cannot be read is passed over, as Chrome passes over it. `REG_EXPAND_SZ` is expanded and other value types are skipped.
      - The same value in both views of one hive is listed once (HKCU's `Software` is shared between the views).
    - **The Status reader:** `status.read_registration_status(layer)` uses the winning entry for the verdict, and records `others` and `per_user_override` (`is_frozen()` and any HKCU entry).
      - A broken winner is NOT rescued by a good later entry, because Chrome uses the first.
      - `layer=None`, or a layer that raises, gives `checked=False` and the line "Registration: not checked".
    - **The Status line:** `status.registration_lines` shows no path. It reads, for example, "registered ✓ (per-user Chrome link; 1 other link found, not used)", plus D9's warning "Warning: a per-user Chrome link overrides the installed one."
    - **The host log:** `native_host._log_registration_paths(logger, layer=None)` logs `host_manifest path= detail_code=<hkcu_32…> count=` for the winner, one `host_manifest_other` line per other entry, `host_launcher`, `state=absent` when there are none, and `state=unreadable` on any failure. It never raises.
    - **The wiring:** `app.main` builds ONE `Win32WindowsLayer` for `startup_exclusions` and passes it to `MainWindow(windows_layer=)` → `StatusPanel(windows_layer=)`.
      - Every test window has no layer, so it now reads no registry. Before, every `MainWindow` test read the real HKCU.
      - **The removed tests:** `test_status_and_app.py`'s two real-machine registration tests read this computer's HKCU (a C6 breach) and were replaced by one no-layer test. Their no-spaces rule is also superseded by Task 0.2, which ran the installed host from Program Files. The count is −2 +1.
    - **Residue for H.1:** with the clinic-only policy `NativeMessagingUserLevelHosts=0` set (D8's optional checkbox), Chrome ignores HKCU entries. The D9 warning would then name an override that does not happen. The policy is not read.
    - Tests: `test_frozen_runtime.py` `TestRegistrationStatus`, `TestHostRegistrationLog`, `TestRealLayerOverAFakeWinreg` (the real layer's methods over a fake `winreg` module; `__init__`, the conftest sentinel, is not run) and the Status-panel test. `test_exclusions.py`'s app-main test also pins that the same layer reaches the window.
- [x] 🟩 **2.4 The WER set by channel, plus a backup-exclusion check (D10, D6).**
  - `check_wer` takes the channel's set and reads HKLM then HKCU.
  - New `check_backup_exclusions` reads the two HKLM `ClinikoScribe` values and checks they cover `sessions` and `logs`.
  - Both only ever warn, wrapped so a read error is a warning (`startup_exclusions`, `exclusions.py:338-365`).
  - Done when: FakeLayer tests cover each state, and the dev channel never warns about the HKLM values.
  - **Leg i2-x1 (built; 🟩 leg i2-x2 on composer suite 1):**
    - **The WER set by channel:** `exclusions.wer_applications(of)` is production `WER_PRODUCTION_APPLICATIONS` (`scribe-app.exe`, `scribe-host.exe`) or dev `WER_EXCLUDED_APPLICATIONS` (the three, unchanged; the register script still uses them). `wer_hives(of)` is production HKLM then HKCU, dev HKCU only (D10).
      - `check_wer` warns when any of the channel's executables is excluded in NONE of its hives, and checks the uncovered launch against the channel's set.
      - `WindowsLayer.wer_exclusions(hive="HKCU")` reads that hive's 64-bit view.
    - **The backup check:** `check_backup_exclusions(layer)` runs in production only. It reads `WindowsLayer.backup_exclusions()`: the REG_MULTI_SZ `ClinikoScribe` value under `HKLM\SYSTEM\CurrentControlSet\Control\BackupRestore\{FilesNotToBackup,FilesNotToSnapshot}`.
      - Both values must hold every `install_layout.backup_exclusion_patterns()` entry, which are Task 3.4's `$UserProfile$` forms, built from `APP_FOLDER_NAME` so the source scan holds. Matching ignores case and surrounding spaces.
      - The lines are `BACKUP_NOT_EXCLUDED`, best-effort wording per C5 with the remedy "reinstall Clinic Scribe", and `BACKUP_UNCHECKED`.
      - `startup_exclusions` wraps it, so any error becomes `backup_unchecked`.
    - **Test edits (the dev branch):** the existing `TestCheckWer` and `TestStartupExclusions` describe a source run's start-up. Under the production pin they would now see the installed build's set, so each gained a class-level `use_channel("dev")` fixture, with every assertion unchanged. The one default-root test pins production inside itself.
    - The integration child's string fake layer gained the two new methods and the `hive` parameter.
    - Tests: `test_exclusions.py` `TestCheckWerProduction`, `TestCheckBackupExclusions`, and the dev-channel WER test.
- [x] 🟩 **2.5 Hardware check (D11).**
  - The Microphone tab's benchmark gains a prose-stage timing:
    - fixed non-clinical lines;
    - `build_prose_stage` in-process, timed per section;
    - CPU seconds and wall seconds;
    - skipped with a named line when the language model is absent;
    - the injectable runner keeps tests model-free.
  - It also shows whisper `medium`'s real-time factor and `threshold_report`'s verdict for both. The results are text-free.
  - Done when: tests inject the model present and absent, and the panel lines are pinned.
  - **Leg i2-x1 (built; 🟩 leg i2-x2 on composer suite 1):**
    - **The timing:** the new `ui/hardware_check.py` `run_prose_benchmark(model_factory=, available=, wall_clock=, cpu_clock=)` runs the REAL `models.build_prose_stage("narrative", cache=None)` in-process.
      - The input is `prose_benchmark_note()`: three sections of two fixed lines, each a phrase of `benchmark.BENCHMARK_TEXT` (pinned by test), held in memory for the one call.
      - ~~The model is loaded fresh, so its load is measured, and released, so nothing stays resident.~~ **Round 13 MED-001:** the model comes from the process's ONE language-model cache, the Note tab's, so there is never a second resident copy.
      - A model already loaded is used as it is, and the line says "model already loaded".
      - Otherwise this check loads it, timed, and it stays resident.
      - Any failed model call, or no section rendered, is a named skip, never a verdict (MED-002).
      - The sections' wall and CPU exclude the load (LOW-001); since round 14 LOW-002 the model is taken before the stage is clocked.
      - **Round 14 LOW-001:** a load that fails during the check is remembered by that cache for the process, so the Note tab's prose styles also refuse until a restart. Either way the check's line is "the language model could not be loaded (<reason>; restart the app after fixing this)".
      - The absent model gives `skipped = language_model_absent_reason()`. A load failure gives "the language model could not be loaded (<reason>)".
    - **The result:** `benchmark.ProseBenchmark` holds numbers only — sections, sections the model was called for, load, model seconds, wall, process CPU, and the per-section wall and CPU.
    - **The lines:** `benchmark.prose_report`, `hardware_verdict` ("Hardware check: whisper medium RTF x OK|…; prose stage y s per section OK|…", or "not measured (not installed)" / "not timed"), and `threshold_report(results, prose=None)` appending both (unchanged without `prose`).
    - **The panel:** `MicrophoneScreen(prose_runner=)` runs whisper then prose on one `TaskThread`, and a slow prose stage adds `PROSE_SLOW_WARNING` to the warning label.
      - The real prose runner is the default ONLY alongside the default whisper runner. A screen given its own `benchmark_runner` (every test) times no prose, so no test reaches the real language model (C6).
      - The result type `HardwareCheck` is public. Two tests that called `_on_benchmark_done([])` now pass `HardwareCheck([], None)`.
    - **Interpretation call (ACCEPTED by the composer at leg i2-x2's resume; the practitioner may still revise it):** the verdict bar is `PROSE_MARGIN_S = 5.0` / `PROSE_REQUIRED_S = 10.0` model-wall seconds per section (OK / NOTE / WARNING).
      - Neither D11 nor the plan gives a number. The bar reads the practitioner's 2026-09-18 note-learning decision ("CPU inference … acceptable for a few seconds per section").
      - It only ever produces a local line. One constant pair, pinned by `test_the_prose_bar_is_the_recorded_interpretation`.
    - Tests: the new `test_hardware_check.py`.
- [x] 🟩 **2.6 The real-ML test legs follow the source-run models root** (added by Phase 1 review round 9, MED-003).
  - DONE 2026-10-03 (composer): the practitioner copied the production models into `%LOCALAPPDATA%\ClinikoScribe-dev\models` from a normal PowerShell (Test-Path False before; 5,670,532,487 bytes after). Composer suite at `f8744f6`: **5846 passed / 12 skipped** — all 11 real-ML legs RAN and passed; the 12 skips are the 9 directory-symlink variants and the 3 artefact skips (lock, manifest — run before the file existed — and workflow pins).
  - Today the conftest pins the production channel, so every real-ML gate and child resolves `%LOCALAPPDATA%\ClinikoScribe\models`: `test_integration_no_sockets.py`'s `requires_ml_models` (~L126) and its children, `test_speech.py` (~L461), `test_speaker_embedding.py` (~L575), `test_benchmark.py` (~L250) and `test_transcription.py` (~L1384). Once the models live only in `ClinikoScribe-dev\models` (the source checkout's root after P.1) or in the install folder, these legs SKIP silently and the suite still reads green.
  - Resolve these gates' models root as a source run's dev root (`install_layout` with the dev channel, never the production data folder — C8), keep every other test on the production pin, and make the skip reason name the dev root it looked in.
  - Done when: a test pins the gates' root to `ClinikoScribe-dev\models` under an injected `LOCALAPPDATA`, the composer's suite runs the real-ML legs against a populated dev root (the practitioner copies or re-fetches the models there first, from a normal terminal — C7), and the composer reports the run/skip count of those legs.
  - **Leg i2-x1 (code and pinning tests built; stays 🟨 until the practitioner populates the dev root and the composer reports the legs' run/skip count):**
    - **Leg i2-x2 status:** the pinning tests pass in composer suite 1 (pytest 5527 passed / 20 skipped). The 11 real-ML legs SKIP there, each naming the empty `ClinikoScribe-dev\models` root. What remains: (1) the PRACTITIONER STEP below; (2) the composer re-runs pytest and reports how many of those 11 legs ran and how many skipped.
    - **The helpers:** `install_layout.models_root(of=None)` gained a channel argument, the same `of` idiom as `folder_name` and the identity accessors. The conftest gained:
      - `real_ml_models_root()` = `models_root("dev")` = `%LOCALAPPDATA%\ClinikoScribe-dev\models`, whatever the pin, or `None` when `LOCALAPPDATA` is unset;
      - `on_real_ml_root(probe)`, a gate's presence probe run with every model path resolving there, safe at import time and restoring the pin;
      - `real_ml_skip_reason(what)`, which names the dev root it looked in;
      - the `real_ml_models` fixture, which pins a leg's BODY to the same root.
    - **The legs, enumerated from the code** (every `skipif` or in-body skip whose condition calls a model-presence probe, plus every real-model child script):
      - `test_speech.py` `TestSileroVadRealModel`;
      - `test_speaker_embedding.py` `TestRealModel`;
      - `test_benchmark.py` `TestRealModelSmoke` (its explicit `ClinikoScribe\models` path replaced);
      - `test_transcription.py` `test_prompt_token_count_exact_with_real_tokenizer` (not in the plan's list; same class) and `TestLiveEndToEnd`;
      - `test_language_model_runtime.py` `TestRealModelSmoke` (not in the plan's list);
      - `test_integration_no_sockets.py` `requires_ml_models` (two tests) and `test_prose_generation_no_sockets_with_the_real_model` (not in the plan's list).
      - Their three child scripts (`_REAL_TRANSCRIBE_CHILD`, `_REAL_PROSE_CHILD`, `_STUBBED_NETWORK_CHILD`) pin `install_layout.models_root` to `models_root("dev")` right after their channel pin.
    - **The pins:**
      - `test_frozen_runtime.py` `TestRealMlModelsRoot` checks the root under an injected `LOCALAPPDATA` for both channel pins, the probe-then-restore, the skip reason and the body fixture.
      - `test_every_real_model_child_loads_from_the_dev_root` is class-closed over the module's `*_CHILD` constants: exactly those three construct a real model, and each pins after its channel pin.
      - `test_every_real_model_skip_gate_looks_in_the_dev_root` is an AST scan of every test module's `skipif`. It is a scan, not a proof; the two in-body language-model skips are enumerated above.
    - **Consequence until the practitioner step runs:** with `ClinikoScribe-dev\models` empty, every real-ML leg SKIPS, and its reason names the dev root. That is the intended loud form of the silent skip MED-003 described.
    - **PRACTITIONER STEP (normal PowerShell, C7 — not from an agent shell).** Copy the everyday app's models into the dev root. No network is needed, and the production copy is untouched:
      `Copy-Item -Recurse "$env:LOCALAPPDATA\ClinikoScribe\models" "$env:LOCALAPPDATA\ClinikoScribe-dev\models"`
      Then report `(Get-ChildItem "$env:LOCALAPPDATA\ClinikoScribe-dev\models" -Recurse -File | Measure-Object Length -Sum).Sum`.
      - The size is whatever the everyday folder holds: about 5.3 GiB with all four whisper candidates, the speaker model and the language model (silero + whisper `small` alone ≈ 470 MiB; the language model 2.33 GiB).
      - The alternative is a re-fetch from the worktree's venv, which Phase 1 points at the dev root: `C:\scribe-build\.venv\Scripts\python.exe C:\scribe-build\scripts\setup-models.py`. It downloads the same pinned files over the network.
      - Assumption to confirm on the composer's run: the composer's agent shell READS the practitioner-created dev folder, as it already reads the production models (MSIX virtualization redirects writes, not these reads).
- [x] 🟩 **2.7 A packaged build refuses to start outside its install folder** (added by Phase 1 review round 9, LOW-009).
  - Only `models_root` calls `install_root()` today, so a frozen build copied anywhere else still runs as production with full access to the production data folder; only its model loads fail.
  - `app.main` and `native_host.main`, when `install_layout.is_frozen()`, call `install_root()` before the guard, the data roots and any window; an `InstallLayoutError` is one type-name log line and a plain refusal ("Clinic Scribe is not running from its install folder — reinstall Clinic Scribe"), never a start. A source run is unaffected.
  - Done when: tests inject frozen inside and outside `INSTALL_ROOTS` (and a link to it) for both entry points, and the refusal touches no data root.
  - **Leg i2-x1 (built; 🟩 leg i2-x2 on composer suite 1):**
    - **The check:** `install_layout.outside_install_folder()` returns the `InstallLayoutError`, or `None` for a source run or the install folder. `app.main` and `native_host.main` call it FIRST, before logging, the guard, every data root and any window.
    - **The refusal:**
      - The type-name line goes through `setup_logging(name, file=False)`, a new keyword: stderr only, no log folder created. It reads `app_exit` / `host_exit error_code=InstallLayoutError state=not_installed`.
      - `scribe-app` then shows `install_layout.NOT_INSTALLED_LINE` ("Clinic Scribe is not running from its install folder — reinstall Clinic Scribe.") in a box and returns 1. `scribe-host` returns 3.
      - **Residue for H.1:** a windowed packaged build usually has no stderr (Task 0.2: Chrome gives the host none), so the line is mostly unseen. The app's box is the visible refusal; for the host it is Chrome's failed link.
    - Tests: `test_frozen_runtime.py` `TestOutsideTheInstallFolder`, parametrized over both entry points.
      - The cases: outside (refused; the injected `LOCALAPPDATA` stays empty), the install folder, a source run that never reads the executable, a junction INTO the folder (proceeds), and a junction AT the install path pointing elsewhere (refused).
      - Also `test_stderr_only_logging_creates_no_folder`.

### Phase 3 — Build and installer
- [x] 🟩 **3.1 `desktop/requirements-build.txt`.** Every runtime dependency (the `[ml]` extra, `sounddevice`), PyInstaller and its hooks package, all `--require-hashes`. The prose wheel stays in `requirements-ml-prose.txt`. A test checks that every `pyproject` runtime dependency appears in the lock.
  - RE-DONE 2026-10-03 (after round 31): the practitioner regenerated the lock — "wrote 59 pinned wheels"; the diff adds exactly hatchling 1.32.4, pathspec 1.1.1, pluggy 1.6.0, tomlkit 0.15.1 and trove-classifiers 2026.9.21.13, each hash-locked (59 pins, 59 hashes). Composer suite: ruff clean, mypy clean, pytest 5856 passed / 9 skipped (symlink only).
  - **REOPENED 2026-10-03 (round 31, executor leg i3-x9): the lock must be REGENERATED.** The first `Release` run failed installing PyInstaller from source: under `--no-build-isolation` its build backend `hatchling` must already be installed, and the lock did not carry it. `BUILD_TOOL_PINS` and `EXTRA_REQUIREMENTS` now include hatchling 1.32.4 and its dependencies (pathspec 1.1.1, pluggy 1.6.0, tomlkit 0.15.1, trove-classifiers 2026.9.21.13; `packaging` is already locked from the freeze). Until the lock is regenerated, `test_build_lock.py::TestLockCoversTheRuntime::test_the_committed_lock_covers_the_runtime_and_is_fully_hashed` FAILS (its first assertion: `missing_runtime_dependencies` returns `['hatchling']`; past it, "hatchling is not in the lock: regenerate it (Task 3.1)"), and `build-release.py` refuses in preflight ("lacks hatchling, the build backend of PyInstaller's source").
    - **PRACTITIONER STEP (normal PowerShell at `C:\scribe-build`; network — the same two commands as before):** `.venv\Scripts\python.exe -m pip freeze --all | Out-File -Encoding utf8 "$env:TEMP\proven-freeze.txt"` then `.venv\Scripts\python.exe scripts\lock-build-requirements.py --constraints "$env:TEMP\proven-freeze.txt"`. Most likely "wrote 59 pinned wheels" (54 + the five new names), or a refusal by name — report either. Then the composer commits the lock and re-runs the suite: the committed-lock test must then pass. 🟩 again on that green suite.
  - DONE 2026-10-03: the practitioner ran the lock from a normal PowerShell at `C:/scribe-build` (pip freeze of the worktree `.venv` as constraints): "wrote 54 pinned wheels to …desktop
equirements-build.txt". Composer check: every one of the 54 carries `--hash=sha256:`; the 51 runtime pins equal the build venv's installed versions exactly; the 3 not in the venv (`altgraph` 0.17.5, `pefile` 2024.8.26, `pyinstaller-hooks-contrib` 2026.8) are the PyInstaller build-tool pins. The lock test now RUNS; suite 5848 passed / 10 skipped (9 symlink + the Task 3.6 pins). Composer committed the lock.
  - **Leg i3-x1 (generator and tests built; stays 🟨 until the practitioner generates and commits the lock — a build-time network step):**
    - **`scripts/lock-build-requirements.py`** writes the lock; it chooses NO version itself. The versions come from a `pip freeze --all` of the proven environment (`--constraints`) plus `BUILD_TOOL_PINS` (Task 0.1 RESULT: `pyinstaller-hooks-contrib` 2026.8, `altgraph` 0.17.5, `pefile` 2024.8.26). One `pip download --only-binary=:all:` resolves pyproject's dependencies + `[ml]` + `EXTRA_REQUIREMENTS` (`sounddevice`; the prose runtime's own Requires-Dist, read from the installed wheel's METADATA: `typing-extensions`, `numpy`, `diskcache`, `jinja2`; PyInstaller's install needs: hooks-contrib, altgraph, pefile, `pywin32-ctypes`, `packaging`, `setuptools`). It refuses, by name: a wheel whose version the proven environment does not pin, an sdist, anything in `NEVER_LOCKED` (`pyinstaller`, `llama-cpp-python`, the dev tools), and a lock that would miss a runtime dependency.
    - **Interpretation call (D1 over the task's wording):** PyInstaller itself is NOT in the lock. D1 needs the bootloader built from source, and Task 0.1 proved that route (6a: the source at tag v6.22.3, commit `ecd7993…`, `waf`, `pip install` of the tree). So `build-release.py` pins PyInstaller by that COMMIT and checks it, and the lock carries its hooks package and its dependencies. A PyPI PyInstaller wheel would ship the prebuilt bootloader that D1 and Task 0.5's Defender result excluded.
    - **Tests:** `test_build_lock.py`, covering the generator on a fixture freeze and a fake `pip download`, each refusal, and the task's check on a fixture lock. The committed-lock test **SKIPS BY NAME** ("desktop/requirements-build.txt is not generated yet …") until the lock exists; it then checks the runtime coverage, a hash on every entry, no `NEVER_LOCKED` name, and the tool pins.
    - **PRACTITIONER STEP (normal PowerShell at `C:\scribe-build`; network):** `.venv\Scripts\python.exe -m pip freeze --all | Out-File -Encoding utf8 "$env:TEMP\proven-freeze.txt"` then `.venv\Scripts\python.exe scripts\lock-build-requirements.py --constraints "$env:TEMP\proven-freeze.txt"`. Report the "wrote N pinned wheels" line, or the refusal. Then the composer commits `desktop/requirements-build.txt` and re-runs the suite: the skipped test must then RUN and pass.
- [x] 🟩 **3.2 `packaging/scribe.spec`** (D1). Two windowed EXEs in one COLLECT. Collect `scribe_desktop` package data, apply Task 0.1's hidden imports and hooks, exclude the network Qt modules, no UPX, and add a version resource from D12.
  - **DONE 2026-10-03 (composer):** the spec built both EXEs in CI (Release runs 37081519723 for 0.1.0 and 37108950093 for 0.1.1, each auditing the bundle); the installed app passed P.1 and P.3 on this computer.
  - Done when: `pyinstaller packaging/scribe.spec` builds on the composer's machine. The bundle audit runs on that output once Task 3.5 lands; this task is not blocked on it.
  - **From Phase 2 review round 13 (MED-003):** both EXEs set `disable_windowed_traceback=True`. The Phase 0 spike spec left it `False`. With it `False`, an exception escaping `app.main` or the host's `main` — the benchmark worker's included, whose own boundary is now `benchmark.run_worker` — shows PyInstaller's windowed "Unhandled exception" box with the full traceback, against C3's type-name-only rule.
  - **Leg i3-x1 (spec, entries and pins built; stays 🟨 until a real PyInstaller build passes `build-release.py --audit` — the practitioner's or composer's step):**
    - **`packaging/scribe.spec`:** two Analyses (`packaging/entry_app.py`, `packaging/entry_host.py`, each calling the real `main`), two windowed EXEs (`scribe-app`, `scribe-host`; `console=False`, `upx=False`, `disable_windowed_traceback=True`, a `VSVersionInfo` from pyproject's version, D12) and ONE `COLLECT` named `scribe` (`<dist>\scribe\`).
      - `pathex` is `desktop\src` ONLY (Task 0.1 found the repository root first).
      - The app's modules and its `config_defaults/*.json` are enumerated from the source tree, not imported. The hidden imports are Task 0.1's: the app's modules (with `native_host` and `speaker_eval`), `keyring.backends.Windows`, `win32com.client` and `win32timezone`. The spike's `collect_dynamic_libs` (ctranslate2, onnxruntime, llama_cpp), `collect_data_files("faster_whisper")` and `copy_metadata("keyring")` are kept.
    - **The Qt-network filter (LOAD-BEARING, Task 0.1):** it runs over both Analyses' binaries AND datas, using one rule, `is_qt_network_file`, written identically in the spec and in `build-release.py`. The rule is broader than the spike's two prefixes: any Qt file whose name says network or websockets, so `Qt6NetworkAuth.dll` and `Qt6QmlNetwork.dll` (both present in the venv's PySide6) are covered, plus Qt's `plugins\tls` and `plugins\networkinformation`. A test executes the spec's copy and checks it equal to the audit's on 13 names.
    - **Bundle trims from Task 0.1's list, with the evidence:**
      - TRIMMED: `mypy`, `pydantic.mypy` and `pydantic.v1.mypy` (a type checker the pydantic hook drags in), plus `setuptools`, `pkg_resources` and `_distutils_hack`. The only runtime-package importer found of these is cffi's build-time `setuptools_ext`.
      - NOT trimmed, because the app imports them at run time:
        - `huggingface_hub` and `av`: `faster_whisper/utils.py:7` and `faster_whisper/audio.py:15` import them at module level;
        - `httpx`, `anyio` and `certifi`: the client `huggingface_hub` uses;
        - `jinja2`: llama_cpp's chat format;
        - `sqlite3`: `diskcache/core.py`, which llama_cpp's cache imports;
        - lxml: python-docx.
      - `tzdata` (a hook warning): the app uses no `zoneinfo`.
      - `_rocm_sdk_core` (Task 0.1): harmless when absent, because `ctranslate2/__init__.py` wraps `os.add_dll_directory` in `except (FileNotFoundError, OSError)`, and nobody but an admin can create it under the admin-only install folder.
      - A test pins that no trimmed module is imported anywhere in `scribe_desktop`. It is a scan, not the proof.
    - **The trims are verified on the INSTALLED app, not on a scratch run:** Task 2.7 stops a packaged build from running outside `C:\Program Files\ClinikoScribe`, so the spike's 12-check scratch launch no longer applies. The audit's self-check runs from anywhere (Task 3.5), and P.1 steps 7 and 10–12 plus P.2 exercise the runtime (self-test, a transcription, a prose render, the hardware check).
    - **Tests:** `test_build_spec.py` (syntax-tree pins).
    - **The integration gate (PRACTITIONER or composer, normal PowerShell at `C:\scribe-build`; no network if `C:\scribe-spike\venv-build` still exists — it holds PyInstaller 6.22.3 with the from-source bootloader):** `C:\scribe-spike\venv-build\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath C:\scribe-spike\p3\dist --workpath C:\scribe-spike\p3\work packaging\scribe.spec`, then `.venv\Scripts\python.exe scripts\build-release.py --audit C:\scribe-spike\p3\dist\scribe --no-defender`. Report the build's last line, every `FILTERED` line, and the audit's `FAIL` / `audit:` lines. Otherwise, the full `build-release.py` run (Task 3.5) is the gate.
- [x] 🟩 **3.3 Models manifest** (D5, D-I2).
  - DONE 2026-10-03: the practitioner ran `build-release.py --write-manifest --models "$env:LOCALAPPDATA\ClinikoScribe\models"` (the read-only everyday-models alternative): "wrote … packaging\models-manifest.json (8 files)", pack name `ClinikoScribe-models-10a83493`. The committed-manifest test now RUNS and passes (`test_build_release.py` 90 passed). Composer committed the manifest.
  - `scripts/setup-models.py --root <dir>` stages into a gitignored `build/models`; `%LOCALAPPDATA%` is never touched when `--root` is given.
  - `packaging/models-manifest.json` lists every file's relative path, size and SHA-256 (silero; whisper `medium` every file; the speaker model per D-I2; the language model). It is generated once by the practitioner and committed.
  - A test checks it against the existing pins (setup-models silero, `speaker_embedding.py:58-66`, `language_model.py:57-87`).
  - Copying the staged models into a pack is Task 3.5's `--model-pack`.
  - **D-I2 decided 2026-10-02: the speaker model is IN the pack.** The manifest therefore lists `speaker-embedding\wespeaker-voxceleb-resnet34-LM.onnx`. An attribution notice joins the pack beside the file, listed in the manifest like any other file. It contains:
    - the creators, with the WeSpeaker citation from Task 0.4;
    - "Creative Commons Attribution 4.0 International (CC BY 4.0)" with `https://creativecommons.org/licenses/by/4.0/`;
    - the source URL (`scripts/setup-models.py`'s pinned Hugging Face URL);
    - "unmodified (byte-identical, SHA-256-pinned)".
    - H.1's documents mention it.
  - **Leg i3-x1 (staging, generator, notice and tests built; stays 🟨 until the practitioner writes and commits the manifest):**
    - **`setup-models.py --root DIR`** stages a fetch into DIR, and the default root is then never computed. A test, over each of the four pack entries, proves an injected `LOCALAPPDATA` stays empty.
    - **`build-release.py --write-manifest --models DIR`** reads DIR only and writes `packaging/models-manifest.json` (`{"version": 1, "files": [{path, size, sha256}]}`, sorted, in one canonical JSON form).
      - It REFUSES a pinned file that is off its pin: silero against `setup-models.SILERO_VAD_SHA256`, the speaker model against `speaker_embedding`'s size and SHA-256, the language model against `language_model`'s. It also refuses an incomplete whisper `medium`, using `benchmark.whisper_snapshot_missing`.
      - It lists every whisper `medium` file with a `.bin`/`.json`/`.txt` suffix, skipping huggingface_hub's `.cache` bookkeeping, and only `medium` (the Excluded item: no `small`).
      - It lists the attribution notice as `speaker-embedding/ATTRIBUTION.txt`, from the committed `packaging/speaker-model-ATTRIBUTION.txt`, which carries Task 0.4's terms (the "Wang et al." citation as Task 0.4 recorded it, CC BY 4.0 and its link, the pinned source URL, "unmodified (byte-identical, SHA-256-pinned)").
      - It checks every path as plain, relative and Inno-safe (no `..`, no backslash, no quote, no brace).
    - **Line endings:** `.gitattributes` gains `text eol=lf` for the notice and the manifest, so their bytes, and so the manifest's hashes and the pack's name, are the same on the practitioner's checkout and the CI runner (`core.autocrlf=true` here). The pack name is also taken over the canonical form, never the file bytes.
    - **Tests:** `test_build_release.py` `TestTheManifest` and `TestTheAttributionNotice`, on fake models with fake pins: each refusal, the selection, the digest, and that the real pins are the runtime's. The committed-manifest test **SKIPS BY NAME** until the file exists. It then checks every pin, the notice's hash, the whisper set, the four top folders, and the bytes being the canonical form.
    - **PRACTITIONER STEP (normal PowerShell at `C:\scribe-build`):**
      - **rec — the plan's route, network:** stage fresh copies, one run each:
        - `.venv\Scripts\python.exe scripts\setup-models.py --root build\models --only silero-vad`
        - the same with `--only medium`, `--only speaker-embedding` and `--only language-model` (about 3.9 GB in all);
        - then `.venv\Scripts\python.exe scripts\build-release.py --write-manifest --models build\models`.
      - **Alternative (no network, read only):** `--models "$env:LOCALAPPDATA\ClinikoScribe\models"`, the everyday models, which hold the same pinned files.
      - Report the "wrote … (N files)" and "pack name: ClinikoScribe-models-xxxxxxxx" lines. The composer then commits the manifest and re-runs the suite: the skipped test must then RUN and pass.
- [x] 🟩 **3.4 `packaging/scribe.iss`** (D1, D5, D6, D8, D-I1). It covers:
  - **DONE 2026-10-03 (composer):** ISCC 6.7.3 compiled both builds of record in CI; install, in-place upgrade, rollback, uninstall (data kept) and reinstall all passed on this computer (P.1, P.3). Round 40 LOW-001 (Finish-page text cut off) is open as a fix, not a blocker.
  - `PrivilegesRequired=admin`, a fixed AppId and `SetupLogging=no`;
  - a running-process check (`scribe-app.exe`, `scribe-host.exe`, `chrome.exe`) with the "Close Clinic Scribe and Chrome completely" message;
  - the install folder with D-I1's ACL (D-I1 chosen 2026-10-02: `C:\Program Files\ClinikoScribe`, whose inherited ACL Task 0.3 showed is Users RX, so no custom ACL);
  - the models copied from the adjacent pack and checked against the compiled manifest (abort with a message naming the file; skipped when `{app}\models` already matches);
  - HKLM: the native-host key and manifest, the WER values, the backup and snapshot values (Task 0.3's forms), and the optional clinic-only policy checkbox with D8's wording;
  - **The backup and snapshot value forms (fixed by Task 0.3, leg i0-x12; the executor's recommendation under D6's own rule, since D6 has no explicit choice for this case):**
    - Under `HKLM\SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToBackup` AND `…\FilesNotToSnapshot`, one `REG_MULTI_SZ` value named `ClinikoScribe` holding the two `$UserProfile$`-relative patterns, written literally (Inno must not expand them):
      - `$UserProfile$\AppData\Local\ClinikoScribe\sessions\* /s`
      - `$UserProfile$\AppData\Local\ClinikoScribe\logs\* /s`
      - Both flagged `uninsdeletevalue`.
    - **Why this form:** Task 0.3 showed it lands verbatim, and it is profile-independent, so it satisfies C3/D8.
    - **Rejected forms:**
      - the Inno-expanded `{localappdata}` form, which Task 0.3 showed resolves to the INSTALLING (elevating) account's profile — the wrong user under an over-the-shoulder elevation (C3/D8);
      - a literal `%LOCALAPPDATA%` form, whose expansion context in the backup engine is unknown.
    - **Residue (C5):** whether Windows backup honours `$UserProfile$` in `FilesNotToBackup` is a Microsoft Learn reading, not observed on this Windows 11 Home computer. The documents call both exclusions best-effort.
    - The text-pin test checks these exact strings and that no `{localappdata}` / `%LOCALAPPDATA%` form appears in either value.
  - the Finish page (Flow 2 step 4) with NO launch option (D8); a text-pin asserts the `.iss` has no `[Run]` entry that starts `scribe-app.exe`;
  - uninstall removes the app, the models, the host key, the WER values, the backup and snapshot values and the policy (only if this installer set it), and shows "Your sessions, Past sessions and audit record stay in your Windows profile (kept 7 years)".

  A text-pin test (`desktop/tests/test_installer_script.py`) checks the keys, flags and wording.
  - **Leg i3-x1 (script and text pins built; stays 🟨 until it COMPILES with ISCC 6.7.3, then installs in Phase P):**
    - **[Setup]:**
      - a fixed new AppId `{8F3A6C2E-4D1B-4B7A-9E35-6C0D2F81A947}`;
      - `PrivilegesRequired=admin`, `SetupLogging=no`, x64;
      - `DefaultDirName={commonpf64}\ClinikoScribe` with `DisableDirPage=yes`;
      - `OutputBaseFilename=ClinikoScribe-<version>-setup`.
      - Every input arrives as a `/D` define from `build-release.py`, and `#error` fires without one.
    - **[Code] `PrepareToInstall`** refuses (before anything changes) when:
      - `scribe-app.exe`, `scribe-host.exe` or `chrome.exe` runs (WMI `Win32_Process`; the check FAILS CLOSED when WMI cannot run, which is named for H.1);
      - `{app}` is not D-I1's `C:\Program Files\ClinikoScribe` (pinned equal to `install_layout.INSTALL_ROOTS`);
      - the installed models do not all match the compiled SHA-256s and the pack `{src}\ClinikoScribe-models-<sha8>\` is absent, or one of its files is missing or does not match. The message names the file and says "Nothing was changed".
    - **The models:**
      - When they need copying, `[InstallDelete]` clears `{app}\models` and the generated `[Files]` entries copy each file (`external`, `Check: ModelsNeedCopy`).
      - `ssPostInstall` re-hashes the copies. A bad copy is deleted (so the app reports it missing and says reinstall, never loads damaged bytes) and a message names it.
      - An upgrade with matching models needs no pack.
    - **[Registry], all `HKLM64`:**
      - the Chrome link `SOFTWARE\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host` → `{app}\com.scribe.cliniko_host.json` (`uninsdeletekey`). `build-release.py` writes the manifest into the bundle: production identities, path `C:\Program Files\ClinikoScribe\scribe-host.exe`;
      - WER DWORD 1 for `exclusions.WER_PRODUCTION_APPLICATIONS`;
      - `FilesNotToBackup` and `FilesNotToSnapshot` value `ClinikoScribe` = exactly `install_layout.backup_exclusion_patterns()` joined by `{break}` (Task 0.3's `$UserProfile$` form);
      - the policy, only with the unticked-by-default `[Tasks]` box (D8's wording) AND `Check: PolicyIsOurs`. A value someone else set is left alone and never removed.
    - **The policy's interpretation call:** an upgrade that unticks the box removes the value only if an earlier run of THIS installer set it (`GetPreviousData`). **Residue for H.1:** Inno's uninstall log keeps the earlier install's `uninsdeletevalue`, so a policy someone sets AFTER such an untick would still be removed at uninstall.
    - **The rest:**
      - no `[Run]` section (D8);
      - the Finish text in `CurPageChanged` follows Flow 2 step 4: Load unpacked `{app}\extension` / reload on an upgrade, fully restart Chrome, open from the Start menu, with a Start-menu shortcut in `[Icons]`;
      - `[UninstallDelete]` covers `{app}\models` only;
      - uninstall shows "Your sessions, Past sessions and audit record stay in your Windows profile (kept 7 years)." and refuses while any of the three programs runs.
    - **Inno syntax care:** `[Code]` uses `//` comments only, because a Pascal brace comment ends at the first `}` and Inno's constants are braces. A test pins that.
    - **Tests:** `test_installer_script.py` (21 text pins), plus `test_build_release.py` `TestTheInstallerInputs` (the host manifest and the generated includes).
    - **COMPILE CHECK (PRACTITIONER or composer, normal PowerShell at `C:\scribe-build`; no network). It only compiles; nothing installs.**
      ```powershell
      New-Item -ItemType Directory -Force C:\scribe-iss-check\dist | Out-Null
      Set-Content C:\scribe-iss-check\dist\placeholder.txt "x"
      Set-Content C:\scribe-iss-check\files.iss "; none"
      Set-Content C:\scribe-iss-check\code.iss "procedure AddModelFiles();`r`nbegin`r`nend;"
      & "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=0.1.0 /DDistDir=C:\scribe-iss-check\dist /DModelPackDir=ClinikoScribe-models-00000000 /DModelsFiles=C:\scribe-iss-check\files.iss /DModelsCode=C:\scribe-iss-check\code.iss /OC:\scribe-iss-check\out packaging\scribe.iss
      ```
      - Report "Successful compile" or the first error line, then delete `C:\scribe-iss-check`.
      - The real compile is inside `build-release.py` (Task 3.5).
    - **COMPILE CHECK RESULT (composer, 2026-10-03 ~03:20, from `C:\scribe-build` with the command above):** Inno Setup 6.7.3 ISCC "Successful compile (3.594 sec) … ClinikoScribe-0.1.0-setup.exe", exit 0. Output is in `C:/Recording clinic software/.cursor/loops/stage-3-iscc-check.txt`.
      - The script compiles with placeholder model includes.
      - Still owed: the real-include compile (Task 3.5) and the install (Phase P).
      - **PRACTITIONER:** delete `C:\scribe-iss-check`; the composer's tool could not.
    - **Leg i3-x2 (composer suite 1's two `.iss` pin failures, fixed in the TEST, as a class; `scribe.iss` unchanged):**
      - **D8 pin:** it now checks the launch SURFACE, no longer the spelling. It forbids:
        - any `[Run]` or `[UninstallRun]` section;
        - any entry whose `Flags` include `postinstall` or `runasoriginaluser`;
        - any `[Code]` call to `Exec`, `ShellExec`, `*AsOriginalUser`, `ExecAndCaptureOutput` or `ExecAndLogOutput`.
        - `ssPostInstall`, an install step, is now allowed. A companion test proves the check catches a launch and passes over WMI's `ExecQuery`.
      - **Policy pin:** it matches the entry by the EXPANDED key (the script's own `#define`s resolved), the key Inno writes.
      - `_code()` splits at the `[Code]` header LINE, never at a mention of it.
    - **Round 18 MED-001 (leg i3-x3):** `[InstallDelete]` now also clears `{app}\_internal` and `{app}\extension`, UNCONDITIONALLY. An in-place upgrade (P.3 step 1) or a rollback (P.3 step 2) therefore installs exactly the audited bundle, never the previous build's leftovers; one such leftover is a second `*.dist-info` for a package, and keyring's backend is found through that metadata.
      - It runs after `PrepareToInstall`'s running-process refusal. The app writes nothing under `{app}`, and the top-level files are replaced by name.
      - `{app}\models` keeps its own conditional rule.
      - Pinned by `test_an_upgrade_replaces_the_program_whole`.
      - **ISCC re-check after MED-001 (composer, 2026-10-03 ~03:45, the same placeholder command):** Inno Setup 6.7.3 "Successful compile (2.203 sec)", exit 0.
    - **Round 20 PR-HIGH-003 and its sibling (leg i3-x7):** `RemoveDamagedModels` checks every copied model and each removal; the Finish page says "NOT completely installed" on any failure; the policy untick is removed at `ssInstall`, checked gone, and kept "ours" if it stayed.
      - **ISCC re-check (composer, 2026-10-03 ~04:12):** Inno Setup 6.7.3 "Successful compile (2.235 sec)", exit 0.
    - **Round 22 LOW-009/010 (leg i4-x1):** the Finish page says when a clinic-policy value set by something else was left exactly as it is; the `PolicyForeign` comment corrected.
      - **ISCC re-check (composer, 2026-10-03 ~04:57, the same placeholder command):** Inno Setup 6.7.3 "Successful compile (2.937 sec)", exit 0.
- [x] 🟩 **3.5 `scripts/build-release.py`** (needs Tasks 3.1–3.4).
  - **DONE 2026-10-03 (composer):** `build-release.py` produced both builds of record in CI (preflight, audit, Defender scan, ISCC, `BUILD-INFO.txt` with `tree=clean`); the practitioner's `--model-pack` run built the pack `ClinikoScribe-models-10a83493` and verified it against the manifest.
  - Steps: clean build venv, `pip install --require-hashes -r desktop/requirements-build.txt` plus the prose wheel, PyInstaller with Task 3.2's spec, then `--audit`:
    - the expected files are present;
    - no `Qt6Network`/`QtWebSockets`;
    - the frozen app's offline variables are asserted by running `scribe-app.exe --self-check-offline` (a no-GUI, exit-code-only entry dispatched like 2.1);
    - a Defender custom scan when available;
  - then `npm ci` and `npm run build -- --mode release` into `{dist}\extension`, ISCC over Task 3.4's `scribe.iss` with `/DAppVersion`, and `SHA256SUMS.txt` over every output.
  - `--model-pack` copies Task 3.3's `build/models` into `ClinikoScribe-models-<sha8>/` and verifies it against the manifest.
  - Run by the practitioner for local builds.
  - Done when: `--audit` and `--model-pack` are tested against fake trees for each refusal, and one local build passes the audit (the integration gate for Task 3.2).
  - **Leg i3-x1 (script, the app's self-check and tests built; stays 🟨 until one local build passes the audit — practitioner):**
    - **Modes:** `--write-manifest` (Task 3.3), `--model-pack`, `--audit DIST`, and the build.
    - **`--model-pack --models DIR --out DIR`:** checks EVERY source file against the manifest first (missing, size, SHA-256), so a refusal writes nothing. It then copies exactly the manifest's files into `<out>\ClinikoScribe-models-<sha8>` and checks each copy. It never overwrites a pack.
      - The name comes from the new `install_layout.model_pack_name`, so no script spells the folder name (the Task 1.2 source scan).
    - **`--audit DIST`** reports:
      - both programs;
      - every shipped `config_defaults/*.json` (enumerated from the source);
      - a native library in each of `_internal/ctranslate2`, `onnxruntime/capi` and `llama_cpp/lib`;
      - NO Qt networking file (`is_qt_network_file`, Task 3.2);
      - the self-check, `scribe-app.exe --self-check-offline` run with `HOSTILE_ENV` (the three kill-switches at `0`, `SSLKEYLOGFILE` and `LLAMA_CPP_LIB_PATH` set), which must exit 0;
      - then a Defender custom scan (`Start-MpScan`, then the detections naming the bundle), reported `clean` / `detected` / `not run (…)` and never "clean" when it did not run.
      - A detection fails the build, never an exclusion (C10).
    - **The app's self-check (new, `app.run_offline_self_check`, `SELF_CHECK_FLAG`):** the exact argv `[exe, --self-check-offline]` applies and asserts the offline environment as a start does, then checks that `PySide6.QtNetwork` and `PySide6.QtWebSockets` cannot be found. Exit codes: 0, 1 (the offline environment), 2 (a Qt network module). It opens no window, writes no log and reads no data root.
      - **Interpretation call:** it runs FIRST in `app.main`, BEFORE Task 2.7's install-folder check, because an audit runs the bundle where it was built, which Task 2.7 would always refuse. The install-folder refusal still comes before logging, the guard, every data root and any window; `install_layout.outside_install_folder`'s docstring says so. The host is unchanged.
    - **The build, stage one** (any Python 3.14, standard library only), refusing first on each of these:
      - not Windows;
      - not Python 3.14;
      - no lock (Task 3.1);
      - no manifest (Task 3.3);
      - a non-empty `--out`;
      - `--pyinstaller-src` not at commit `ecd7993d…` (`git rev-parse HEAD`).
      - Then: a clean `build-venv`; `pip install --require-hashes --no-deps` of the lock and of the prose wheel; `waf all --target-arch=64bit` (the C++ build tools); a refusal if `runw.exe` still has the SHIPPED SHA-256 `2291f269…` (Task 0.1), i.e. was not rebuilt; `pip install --no-deps --no-build-isolation` of the source; `pip check`; then stage two under the build venv's own interpreter.
    - **The build, stage two:**
      - PyInstaller over the spec;
      - the host manifest written into the bundle;
      - the audit and Defender;
      - `npm ci` and `npm run build -- --mode release`, copied to `<bundle>\extension`, then the extension audit: not the dev name, no dev host, names the installed host;
      - the two generated Inno includes;
      - ISCC with `/DAppVersion` (pyproject, D12), `/DDistDir`, `/DModelPackDir`, `/DModelsFiles`, `/DModelsCode` and `/O`. It refuses, deleting the output, unless ISCC printed `Compiler engine version: Inno Setup 6.7.3`;
      - the manifest copied beside the setup;
      - `SHA256SUMS.txt` over both.
    - **Tests:** `test_build_release.py`: the model pack, the audit (each refusal, the hostile environment, the CLI), Defender's three verdicts, the extension audit, the includes, the sums, stage one's command sequence and its seven refusals, and ISCC's defines and banner refusal. Also `test_frozen_runtime.py` `TestOfflineSelfCheck` (11 tests, including `app.main` answering before the install-folder check, logging, Qt and the worker).
    - **PRACTITIONER STEP (the integration gate; normal PowerShell at `C:\scribe-build`, after Tasks 3.1 and 3.3 are committed; network for the lock install, `npm ci` and the source clone):**
      1. `git clone --depth 1 --branch v6.22.3 https://github.com/pyinstaller/pyinstaller.git C:\scribe-release\pyinstaller-src`
      2. `py -3.14 scripts\build-release.py --pyinstaller-src C:\scribe-release\pyinstaller-src --out C:\scribe-release\out` (any Python 3.14; the `.venv` interpreter works too).
      3. `.venv\Scripts\python.exe scripts\build-release.py --model-pack --models build\models --out C:\scribe-release\out\installer`
      - Report the final `version` / `installer` / `sha256` / `models` / `defender` lines, or the `ERROR:` line.
      - Building from Program Files is not needed: the audit's self-check runs from the build folder.
- [x] 🟩 **3.6 `.github/workflows/release.yml`** (D7; needs Task 3.5). `workflow_dispatch` on `main` only, `windows-latest`, the pinned Python from D12, Inno from Task 0.3 (preinstalled or a pinned install), `build-release.py` without the model pack, `actions/attest-build-provenance` over `setup.exe` and `SHA256SUMS.txt`, then upload the artifact. Permissions are least-privilege.
  - **RUNS 2026-10-03 (practitioner-approved push of `installation-build` to `origin/main`):**
    - Run 37079569271 on `932c07a`: FAILED installing PyInstaller from source (hatchling build backend not in the lock) — round 31, fixed by leg i3-x9, lock regenerated (59 pins).
    - Run **37081519723** on `e730cd5`: **GREEN** — build (PyInstaller, bundle and extension audits, Defender scan, ISCC 6.7.3 compile) and attest both succeeded. Artifact `clinic-scribe-installer`: `ClinikoScribe-0.1.0-setup.exe` 104,995,817 bytes, SHA-256 `e48a6602a08b6bfd43834937a713542896e607a290f7a511f5410677e880ac99`, equal to its `SHA256SUMS.txt` line; `models-manifest.json` SHA-256 `10a83493…` (= the pack name `ClinikoScribe-models-10a83493`); `BUILD-INFO.txt` `version=0.1.0 commit=e730cd5… tree=clean`.
    - `gh attestation verify` with `--signer-workflow …/release.yml --source-ref refs/heads/main` PASSED (exit 0) for both the installer and `SHA256SUMS.txt` (composer, read-only, 2026-10-03): signer `release.yml@refs/heads/main`, source commit `e730cd5`. Negative control: the same verify with `--source-ref refs/heads/some-other-branch` exits 1. The practitioner re-runs the check at P.1 step 3 on the copy they install.
    - CI on `e730cd5`: desktop 3.14 failed once on the timing assertion `test_live_session.py::test_finish_seals_only_and_the_last_flushed_chunk_is_in_the_tail` (`assert 0.32 < 0.1` on the shared runner); untouched by this plan; the re-run of the failed job passed (3.12, 3.14, extension all green). Recorded in AGENTS.md Known Issues.
    - Recorded in `docs/release/pilot-builds.md`.
  - Done when: one green run is attested and `gh attestation verify` passes (practitioner); the existing `ci.yml` is unchanged.
  - **Leg i3-x1 (workflow and text pins built; stays 🟨 — its pins need the network, and its run needs a push to `main`, the practitioner's call):**
    - **What it does:**
      - `workflow_dispatch` only, with the job `if: github.ref == 'refs/heads/main'`;
      - top-level `contents: read`, and the job adds only `id-token: write` and `attestations: write`;
      - `persist-credentials: false`;
      - `runs-on: windows-2025` (Task 0.3's recommendation over the task's `windows-latest`: that label's moves are gradual);
      - Python `3.14.6` (Task 0.1) and Node 24;
      - Inno Setup **6.7.3** installed from a SHA-256-checked download (the handoff's open item 2 recommendation, built to it), and the build's own banner check refuses any other compiler;
      - the PyInstaller source cloned at `v6.22.3` (the build refuses any commit but `ecd7993…`);
      - `build-release.py` with no model pack and the Defender scan on;
      - an attestation over `release/installer/*.exe` and `SHA256SUMS.txt`, and an upload with `if-no-files-found: error`.
      - `ci.yml` is unchanged.
    - **Fail-closed placeholders, not invented values:**
      - `actions/attest-build-provenance@PIN-REQUIRED` and `actions/upload-artifact@PIN-REQUIRED`: no ref for either is recorded in the repo. The three actions `ci.yml` already uses keep `ci.yml`'s tags.
      - The Inno installer's SHA-256 is `"PIN-REQUIRED"`, so the step throws "not recorded yet".
      - The Inno download URL (`https://files.jrsoftware.org/is/6/innosetup-6.7.3.exe`) was written without network access and is to be confirmed.
    - **Tests:** `test_release_workflow.py` (7 pins). `test_every_new_action_is_pinned_to_a_commit` **SKIPS BY NAME** while any `PIN-REQUIRED` remains, then requires a 40-hex commit for every action beyond `ci.yml`'s three. The job holds an OIDC token, so that is this leg's interpretation call.
    - **AS-BUILT (round 22 LOW-007, round 23):** the job is split. `build` (`windows-2025`) holds `contents: read` only and uploads the installer; `attest` (`ubuntu-24.04`, `needs: build`) alone holds `id-token: write` and `attestations: write`, downloads that artifact (`actions/download-artifact@PIN-REQUIRED`, a third pin) and attests it, with no `run:` step. The Inno install step checks the installer's exit code and that `ISCC.exe` is where `build-release.py`'s default `--iscc` looks (round 23). H.4 SEC-002 supersedes "the three actions `ci.yml` already uses keep `ci.yml`'s tags": every action in `release.yml` — `checkout`, `setup-python` and `setup-node` included — is now `@PIN-REQUIRED # <release>`, to be pinned to a commit, and the job restores no npm cache (`ci.yml` itself is unchanged).
    - **PRACTITIONER/COMPOSER STEP (needs the network; remote-affecting, the practitioner decides):**
      0. **First, re-check that GitHub can attest this repository (round 23):** artifact attestations are available for PUBLIC repositories on every plan, but for a private or internal one only on GitHub Enterprise Cloud. **CHECKED 2026-10-03 (composer, read-only GitHub API): `{"isPrivate":false,"visibility":"PUBLIC"}` — attestation is available and D7 holds as designed.** Visibility can change, so re-run `gh repo view eliemokbel3-hub/Recording-clinic-software --json visibility` before the pins are recorded. If it ever says `PRIVATE` on a personal plan, the `attest` job will fail and D7's build of record cannot exist as designed: STOP and decide (make the repository public again, or choose another provenance route for D7, a `[decision]` with Chosen) before recording any pin.
      1. Record the commit SHA of the chosen release of each of the six actions (`checkout` v5, `setup-python` v6, `setup-node` v5 — the releases their comments name — plus `attest-build-provenance`, `upload-artifact`, `download-artifact`), and the Inno 6.7.3 installer's `Get-FileHash` from the official download; confirm the URL.
         - **DONE 2026-10-03 (composer, read-only GitHub API, practitioner-approved):** checkout v5.1.0 `fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09`; setup-python v6.3.0 `ece7cb06caefa5fff74198d8649806c4678c61a1`; setup-node v5.0.0 `a0853c24544627f65ddf259abe73b1d18a591444`; upload-artifact v7.0.1 `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`; download-artifact v8.0.1 `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c` (errors on a digest mismatch by default); attest-build-provenance v4.2.2 `4d101475d8b20a2381f78447822ac1eab6504dd8` — each the latest release in the major its comment named (the first three match `ci.yml`'s majors) and each `runs.using` node24 or composite. Inno Setup 6.7.3: SHA-256 `9c73c3bae7ed48d44112a0f48e66742c00090bdb5bef71d9d3c056c66e97b732`, 10,592,232 bytes — GitHub's recorded digest for the `jrsoftware/issrc` `is-6_7_3` release asset, equal to `sha256sum` of the practitioner's installed copy. The workflow's URL was WRONG (`files.jrsoftware.org/is/6/innosetup-6.7.3.exe` answers 404); it now downloads that release asset (the one jrsoftware.org's download page links). `test_release_workflow.py`'s pin test now RUNS (12 passed).
      2. Settle the open Inno licence item first ("Non-commercial use only").
         - **DONE 2026-10-03:** continue without buying (Open blockers item 1, `Chosen:`).
      3. Push `main` with the workflow.
      4. Run `Release` once, then verify the downloaded artifact exactly as `docs/release/pilot-builds.md` says (`gh attestation verify … --repo … --signer-workflow …/release.yml --source-ref refs/heads/main`).
         - **FIRST RUN 2026-10-03 (composer-observed): FAILED.** CI run 37079562194 was green; `Release` run 37079569271 failed in `build-release.py` at the PyInstaller-from-source install with `BackendUnavailable: Cannot import 'hatchling.build'` — `--no-build-isolation` (kept: it is the control that stops pip fetching an unhashed backend) needs the backend in the build venv, and the lock lacked it (Task 0.1's spike had built WITH isolation, so it never showed). No artifact, no attestation.
         - **FIX (round 31, executor leg i3-x9):** hatchling and its dependencies are now build-tool pins in `scripts/lock-build-requirements.py`; `build-release.py` holds `PYINSTALLER_BUILD_REQUIRES = ("hatchling",)` (from the source's `pyproject.toml` `[build-system] requires`) and its preflight now refuses, before any venv or `waf` work, a lock without the backend and a PyInstaller source declaring a build requirement not in that list. A test ties every name in it to `BUILD_TOOL_PINS` and `EXTRA_REQUIREMENTS`.
         - **NEXT:** the practitioner regenerates the lock (Task 3.1's reopened step), the composer commits it and pushes `main`, then re-dispatches `Release`. Residue: a hatchling build hook could ask for more through `get_requires_for_build_wheel`; that is not checkable offline, and the re-run is the proof.
- [x] 🟩 **3.7 `scripts/register-native-host.py` becomes dev-only.**
  - It registers `com.scribe.cliniko_host_dev` in HKCU only, installing to `%LOCALAPPDATA%\ClinikoScribe-dev`.
  - `--unregister` also removes a stray HKCU `com.scribe.cliniko_host` key and the legacy production-folder copy.
  - A `PermissionError` with winerror 32 gives "Close Clinic Scribe and Chrome completely, then run this again" (retires `plan-privacy-professional-controls.md` L1313). AS-BUILT (round 22 LOW-005): `--unregister`'s deletes also treat winerror 5 (deleting a running host's image) as in use.
  - Update `test_register_native_host.py` and `test_display_name.py:64`.
  - **Leg i3-x1 (built; 🟩 on a green composer suite — no practitioner step is part of its Done):**
    - The script names the dev channel OUTRIGHT, whatever the importing process's pin: `identity.host_name("dev")`, `expected_origin("dev")`, `registry_key("dev")`, and `install_layout.data_root("dev")`, a new `of` argument on `data_root`, the same idiom as `models_root`.
    - `--unregister` also deletes the HKCU key `identity.REGISTRY_KEY` (production name, HKCU only — never HKLM) and exactly two files in the production data folder, `com.scribe.cliniko_host.json` and `scribe-host.exe`. It never deletes the folder or anything else in it. This is the one place a source checkout's tool writes the production folder, as P.1 step 2's migration (C8 note for H.1).
    - Windows error 32 on the copy or on any delete prints the task's line and exits 1; any other `OSError` still raises.
    - **Tests:**
      - `test_register_native_host.py` +5: the dev identities under the production pin, the stray link and only its two files, the in-use line for register and unregister, and another error not mistaken. `_install_under` now also redirects `STRAY_PRODUCTION_FILES`, so no test can reach the real folder (C6).
      - `test_install_layout.py`: the script's folder is the dev one in either pin, `data_root(of)`, and `model_pack_name`.
      - `test_display_name.py`: the literal is now `data_root("dev")`.
- [x] 🟩 **3.8 `scripts/check-installed-sockets.py`.** Run from a normal terminal while the installed app transcribes and renders prose. It walks the `scribe-app.exe` and `scribe-host.exe` process trees with psutil (lessons: walk the tree) and reports any inet connection, text-free.
  - **DONE 2026-10-03 (composer):** the practitioner's P.1 step 10 run (`--seconds 240`, during a transcription and a Narrative render on the installed app) printed `RESULT: no connection seen`.
  - Done when: it is tested against a fake process table, and the practitioner runs it in P.1.
  - **Leg i3-x1 (built and tested; stays 🟨 until the practitioner's P.1 step 10 run):**
    - **What it does:** each second for `--seconds` (default 60), it lists every process named `scribe-app.exe` or `scribe-host.exe` (any case), adds all their descendants (`children(recursive=True)`), and reads `net_connections(kind="inet")`.
    - **What it prints:** each distinct connection once, as `CONNECTION <program> pid= status= remote=`, and nothing else of the process.
    - **Exit codes:**
      - 0: none seen;
      - 1: a connection seen;
      - 2: no target running;
      - 3: a process could not be read, so nothing is proven.
      - A process that ends during a look is "gone", not an error.
    - **Tests:** `test_check_installed_sockets.py` (7, a fake process table and a fake clock).
    - **P.1 step 10's command:** `.venv\Scripts\python.exe scripts\check-installed-sockets.py --seconds 120`, from the repository root, run during a desktop transcription and a prose render.
- [x] 🟩 **3.9 `docs/release/pilot-builds.md`.** A table of version, commit, CI run, the installer SHA-256 and the model-pack manifest SHA-256, plus the two verification commands (`gh attestation verify`, `Get-FileHash`).
  - **Leg i3-x1 (written; 🟩 on the composer's review — a document with no test):**
    - The table has an empty first row, and each field's source (the run's `SHA256SUMS.txt`; the manifest's first 8 hex name the pack folder).
    - Both commands come with what each must show, and "if either check fails, do not run the installer".
    - Rows are added from the first green `Release` run (Task 3.6).

### Phase H — Documents and hardening
- [x] 🟩 **H.1 Security and project documents, as one class (C9).** DONE (leg i4-x1, reconciled through rounds 22–26; closed by leg i4-x4 on the composer suite 5771 / 23): every item below is written and grep-reconciled across the doc surface; the docs state the installation as BUILT, NOT YET INSTALLED, with the still-to-run list named.
  - `docs/security/threat-model.md`: a new "Installation" section covering:
    - the install-folder ACL and the retired launcher-hijack residue (revise ~L74);
    - HKCU shadowing and the dual-use-computer residue;
    - the unsigned build's integrity (attestation plus hashes, which the practitioner must run);
    - the dev channel and its write guard;
    - the exclusions as best-effort;
    - the shared guard;
    - uninstall leaving the data;
    - the optional policy.

    Also update "Out of scope" and the second-machine review trigger.
  - `data-flow-map.md`: flow 9 (CI and model-pack build network), flow 8 (read-only installed models), and new flows for the installer's writes and the dev channel.
  - `retention-schedule.md`: installed models, the model pack, `SHA256SUMS.txt` and the dev tree.
  - `AGENTS.md`: installed run steps, the dev channel (separate Chrome profile, `register-native-host.py` now dev-only), a packaging pointer in Subsystem Documentation, and `gpt-oss-20b` corrected to Qwen3-4B-Instruct-2507.
  - `PLAN.md`: a Phase 7 installation delivery note.
  - `docs/design-system.md`: the dev-build lines and the Status warnings.
  - `scripts/README.md`.
  - **Phase 1 review round 9 pointers (LOW-010), each to be re-found by text, not line:**
    - AGENTS.md Database Notes (the dev folder) and Local Run Steps 3–8 (the dev models root, `npm run build -- --mode dev` → `dist-dev`, a separate Chrome profile, the dev host registration);
    - `docs/security/data-flow-map.md` ~L54, ~L207 and ~L718 (the single data folder);
    - `docs/security/threat-model.md` ~L1382 (`language_model_absent_reason`, now a function) and ~L2059 (the pipe name, now per channel), plus every old remedy constant it names;
    - `docs/security/retention-schedule.md` ~L39 (the data folder);
    - `docs/lessons.md` and `docs/security/incident-process.md` where they name the data folder;
    - `docs/design-system.md`: the `dev_build_writes_off` line with its `write_uncertain` prefix, and the dev-only Status checkbox and its save-failure line;
    - the threat model names as a residue that the dev and production channels SHARE the Credential Manager namespace (`secure_storage._SERVICE_PREFIX`, kept by D3/C2): clinic entries stay apart only because clinic ids are random per data folder, and the self-test's `test` entry is common to both.
- [x] 🟩 **H.2 `/review-loop`** over the whole plan's diff to convergence. DONE: rounds 22–24 (3 MED + 28 LOW → 1 MED + 4 LOW → 1 LOW), CONVERGED at loop round 3 of cap 3, every finding Applied and verified (composer suites 5754, 5758, 5771 passed / 23 skipped; ISCC 6.7.3 compile after round 22).
- [x] 🟩 **H.3 `/simplify`.** Log findings; trivial ones go to `/fix`, substantial ones to a scoped `/review-plan`. DONE: round 25 — 3 LOW, all trivial, Applied and verified; 4 candidates left alone (recorded); no substantial refactor, so no scoped `/review-plan`.
- [x] 🟩 **H.4 `/security-review`.** Same routing. DONE: round 26 — 0 CRIT/HIGH/MED, 4 LOW, all localized, Applied and verified; no substantial hardening task.
- [x] 🟩 **H.5 Cross-family codex peer** (`gpt-6-astra`) in slices of at most 15 files each: (a) packaging, scripts and CI; (b) layout, identity, guard, write guard and readers; (c) benchmark, UI and docs. A confirmation round follows any hardening fix.
  - DONE 2026-10-03 (composer): codex rounds 27–30 over the whole plan diff in eight slices then confirmations, trajectory 12 → 5 → 1 → 1, all verified LOW; closed without a round 31 per the executor's cap verdict (gate record `h5-peer-close`); composer suite 7: ruff clean, mypy clean, pytest 5835 passed / 23 skipped. PR-MED-022 became Task H.6 `[pending-hardening]`.
  - Done so far: peer rounds 27–30 (peer_round 1–4 of cap 5; 12 → 5 → 1 → 1, all LOW after verification, none CRIT/HIGH), every finding Applied except PR-MED-022, which went to Task H.6.
  - Closes on the composer suite: round 30's last finding was comment wording, so per the recorded cap verdict (`h5-peer-close`) there is no round 31. H.5 closes when the composer's full desktop suite is green at 5835 passed / 23 skipped after leg i4-x12; the composer flips this marker.
- [x] 🟩 **H.6 The models root pinned for every test (C6)** — from round 27 PR-MED-022 (Include in plan); hardened in place by a scoped `/review-plan` on 2026-10-03 (its `[pending-hardening]` marker removed then; Executor tier inherited: entirely premium). Why: `install_layout.models_root()` is the ONE resolver every model path goes through — `benchmark.default_models_root()` → `speech.default_vad_model_path`, `transcription.default_whisper_model_dir`, `language_model.default_language_model_path`, `speaker_embedding.default_speaker_model_path`, each reading the attribute at call time, so one `monkeypatch.setattr(install_layout, "models_root", …)` reaches every path — yet the conftest pins only the channel and `is_frozen`, so a test that never redirects `LOCALAPPDATA` stats the host's real `%LOCALAPPDATA%\ClinikoScribe\models`: FULL on this computer (the everyday app's models until Phase P), EMPTY on CI; the suite is green on both today only because no test yet depends on the difference. The finding's sites: `MicrophoneScreen.refresh_model_status` (`ui/microphone.py` ~L335–342: `speaker_embedder_available()` then `model_file_report_lines()`), the `_main_window` helper (`test_ui_screens.py` ~L976) and the Learn-style poll (`test_ui_learn_style.py` ~L957) — all three reach the models root only through those two calls.
  - **DONE 2026-10-03 (composer):** built by executor leg i4-x13 (in-session /review-loop rounds 32–33: 3 LOW applied, then 0); composer suite 8 green — ruff clean, mypy clean (58 files), pytest **5872 passed / 9 skipped** (5856 + 16 new; the 9 are directory-symlink privilege, the real-ML legs run on the filled dev root); codex round 34 (pass stage-4.p2) 0 findings.
  1. **The pin.** In `desktop/tests/conftest.py`, one autouse function-scoped fixture `pinned_models_root(request, monkeypatch, tmp_path_factory) -> Path | None`: unless the test is exempt (step 2) it pins `install_layout.models_root` to `lambda of=None: root`, where `root = tmp_path_factory.mktemp("models")` — a fresh, EMPTY per-test folder OUTSIDE the test's own `tmp_path` (a test that lists or sweeps `tmp_path` as a sessions root sees nothing new); never pre-populated, so a presence check reads "absent" by default and a test that wants a model writes its own fixture there with `mkdir(parents=True)`. It returns the root (`None` when exempt). Ordering is pytest's own: autouse fixtures instantiate before requested ones of the same scope and share the one `monkeypatch`, so an explicit `real_ml_models` pin lands AFTER this one and wins; `on_real_ml_root` restores whatever was pinned when it ran (at import time the real function, inside a body this pin). `REAL_MODELS_ROOT`, `real_ml_models_root()` and the child processes' own pins (`test_integration_no_sockets.py`'s `_CHILD` sources, checked by `_CHILD_PIN`) are untouched. Docstring in the register of `_production_channel`'s, naming PR-MED-022 and C6.
  2. **The exemption: a registered marker, applied per class.** `@pytest.mark.real_models_root` registered under `[tool.pytest.ini_options] markers` in `desktop/pyproject.toml` (the suite's first custom marker; `--strict-markers` is NOT added — registration alone keeps the run warning-free); the fixture checks `request.node.get_closest_marker("real_models_root")` and then pins nothing. A MODULE-level opt-out is rejected: both exempt modules hold many tests that must stay pinned. Exempt — only the tests OF the resolver, each driving `LOCALAPPDATA` or the install root itself: `test_install_layout.py::TestModelsRoot` (~L241) and the `_builders()` consumer test (~L376, which asserts the `"models"` builder under the channel folder); `test_frozen_runtime.py::TestRealMlModelsRoot` (~L1081 — its `test_a_gate_probes_under_the_dev_root_then_the_pin_returns` asserts the REAL production answer after the restore, and its `test_the_body_fixture_pins_every_model_path` keeps proving the dev-root override); `test_language_model_runtime.py` `test_default_model_path_under_the_models_root` (~L94) and `test_localappdata_unset_reports_unavailable` (~L738 — the unset-`LOCALAPPDATA` contract, hollow under a pin); `test_speaker_embedding.py` `test_default_model_path_under_the_models_root` (~L98). Nothing else: the suite run in step 5 is the enumeration — a failure outside this list is either a resolver test to mark or a fixture builder to migrate (step 3), never a reason to widen the marker to a module or a file.
  3. **Fixture builders follow the pin, not `LOCALAPPDATA`.** The tests that hand-build model files under `<tmp LOCALAPPDATA>/ClinikoScribe/models` build under `install_layout.models_root()` (the pin) instead: `test_transcription.py` `_fake_snapshot` (~L994) and its seven Step-13 call sites (~L1015–1046, ~L1173); `test_ui_models.py` `_fake_whisper_snapshot` (~L357) and the two `vad_dir` lines (~L404, ~L480) in `TestModelReport`. Their `setenv("LOCALAPPDATA", …)` lines stay only where something else in the test still needs the data root. These tests are NOT marked: they test the resolver's consumers; the `LOCALAPPDATA` → `ClinikoScribe\models` mapping is the exempt tests' business. After this step no test outside step 2's set spells `"ClinikoScribe" / "models"` (grep).
  4. **Tripwires** (in `test_frozen_runtime.py` beside `TestRealMlModelsRoot`): (a) an UNMARKED test — `install_layout.models_root()` and `benchmark.default_models_root()` both equal the `pinned_models_root` fixture's value, which is under `tmp_path_factory.getbasetemp()` and empty, and `default_vad_model_path()`, `default_whisper_model_dir()`, `default_language_model_path()`, `default_speaker_model_path()` all resolve under it; (b) a MARKED class — `install_layout.models_root is REAL_MODELS_ROOT` and the fixture returned `None`; (c) an UNMARKED test with `real_ml_models` — `install_layout.models_root()` equals `real_ml_models_root()` (the dev root beats the pin; with Task 2.6's models in place the real-ML legs RUN, so a broken override fails them loudly rather than skipping). (d) the named sites — one test in `test_ui_screens.py` beside the PR-MED-022 site (~L727) builds `MicrophoneScreen(…, benchmark_runner=list, profile_root=tmp_path)` with NO presence stub, calls `refresh_model_status()` under a `pathlib.Path` spy on `NETWORK_IO_METHODS` (modelled on `forbid_network_io`; a small `record_path_io(monkeypatch) -> list[Path]` helper in conftest if that reads better) and asserts every probed path is under the pinned root or `tmp_path`; its docstring says why one site proves the class (the other two reach the models only through the same two calls).
  5. **Suite and docs.** `ruff check . && mypy && pytest` in `desktop/`: expect 5856 + the new tests passed / 9 skipped (the directory-symlink variants only — Task 2.6 is done, the dev root is filled and the real-ML legs run; a changed skip count needs a reason, Validation). Then C9's class reconciliation: the sentence beside the `WindowsLayer` sentinel in `docs/security/threat-model.md` (~L2871, "tests never reach the real one (a sentinel)") names the models-root pin as the second conftest sentinel; `AGENTS.md`'s installation Subsystem bullet ("every host-state read goes through a seam tested both ways (C6)") gains "and the conftest pins every test's models root to an empty temporary folder (`real_models_root` marks the resolver's own tests)"; `docs/lessons.md`'s 2026-09-24 host-file lesson (~L110) gains one recurrence line (PR-MED-022: the model-status poll read the real models folder; closed for the class by the pin, not per test); this plan's C6 names the pin among "the conftest sentinels".
  - Rejected (scoped `/review-plan`, 2026-10-03): (i) a pin that honours a redirected `LOCALAPPDATA` (calls the real function when the variable differs from the host's) — magic that blurs tripwire (a) and still needs the marker for the frozen cases; (ii) `setenv("LOCALAPPDATA", tmp)` for every test — redirects every data root, far beyond PR-MED-022's class; (iii) a per-test copy of the original function — `REAL_MODELS_ROOT` already serves that, and the exempt tests need the live attribute.
  - Risk, named: on this computer the production models folder is full, so a test that passes today only because a real model exists would FAIL under the pin — CI run 37081519723 was green with that folder empty, so none is known; if one appears it writes its own fixture under the pin (lessons 2026-09-24), never earns the marker.
  - Done when: the fixture and the registered marker are in place; the exempt set is exactly step 2's; step 3's builders use the pin and the grep finds no other `"ClinikoScribe" / "models"`; tripwires (a)–(d) pass; the full desktop suite is green at 9 skipped; the three docs and C6 name the pin; then `/review-loop` over the diff and one codex confirmation slice (conftest, pyproject, the five test files, the three docs).
  - BUILT 2026-10-03 (leg i4-x13; /review-loop rounds 32–33, converged at loop round 2 of cap 3); 🟨 until the composer's suite is green.
    - **Steps 1–2 as written,** with three interpretation calls:
      - **(i) The folder.** The per-test folder comes from a session-scoped `models_root_factory`: one `tmp_path_factory.mktemp("models")` parent, and a numbered empty child per test. A `mktemp` per test would make pytest's `make_numbered_dir` rescan the whole base folder for every one of ~5,900 tests. Every property step 1 names holds: fresh, empty, outside `tmp_path`, under `getbasetemp()`.
      - **(ii) The helper.** A `use_models_root(monkeypatch, root)` helper sits beside `use_channel` / `use_frozen`, and the pin uses it.
      - **(iii) Three hollowed tests (found from the code, not by a failure).** Each set `LOCALAPPDATA` to a UNC share to prove that a default model path refuses a network root without I/O. Under the pin they would pass vacuously. They now pin a network models root with `use_models_root`, under the same `forbid_network_io` tripwire. The tests: `test_speech.py` `test_unc_availability_probe_refuses_without_io`, `test_speaker_embedding.py` `test_unc_availability_probe_refuses_without_io`, `test_transcription.py` `test_unc_localappdata_reports_unavailable_without_io`. These are step 3's class (consumers of the resolver), not markers. A sweep found no other UNC `LOCALAPPDATA` in the tests.
      - **Also:** `test_language_model_runtime.py`'s `test_default_path_probe_follows_localappdata` is renamed `…_follows_the_models_root` (its name was the hollow claim) and drops its `setenv`.
    - **Step 3:** the builders use `install_layout.models_root()`, and `_provider` drops its unused `tmp_path`. The `setenv` lines are dropped where only the models root needed them. They are kept, with a comment, in the three `TestModelReport` tests that read the default profile root. The grep finds `"ClinikoScribe" / "models"` only in step 2's tests.
    - **Step 4 (tripwires):**
      - (a) `TestModelsRootPin`, parametrized twice so that a shared folder fails;
      - (b) the marked class `TestTheMarkerOptsOut`, plus a marked FUNCTION (the language and speaker exemptions are function marks);
      - (c) `test_a_real_ml_body_pin_lands_after_and_wins`;
      - (d) `test_model_status_poll_reads_only_the_pinned_models_root` in `test_ui_screens.py`, with `conftest.record_path_io`.
    - **Class closure, from the code:**
      - `test_every_models_root_caller_is_known` is a scan of `src/` and `scripts/`. Every call of `models_root` / `default_models_root` and every read of `MODELS_DIRNAME` is one of 10 known functions: the four path builders (a) resolves, plus the callers that hand the root on.
      - `test_only_the_resolvers_own_tests_opt_out` scans every test module, so the opt-out cannot widen. It reports a `pytestmark` as `<elsewhere>`.
      - Each scan has a self-test of the forms it sees.
    - **Step 5 docs:**
      - the threat model's `WindowsLayer` sentinel sentence;
      - AGENTS.md's installation bullet;
      - `docs/lessons.md`'s 2026-09-24 lesson (the recurrence line);
      - C6.
    - **Expected suite:** 5856 + 16 = **5872 passed / 9 skipped**.

### Phase P — Install on this computer (PRACTITIONER, normal terminal or Explorer)
- [x] 🟩 **P.1 Install and verify.**
  1. Close Chrome (no `chrome.exe` left) and Clinic Scribe.
  2. Run `register-native-host.py --unregister` from the venv.
  3. Run `gh attestation verify` and `Get-FileHash` against `SHA256SUMS.txt`.
  4. Run `setup.exe` with the model pack beside it; leave the clinic-only policy unticked on this computer.
  5. In Chrome, remove the old unpacked extension, Load unpacked `{app}\extension`, fully restart Chrome.
  6. Launch Clinic Scribe from the Start menu, and confirm in Task Manager (Details, "Elevated" column) that `scribe-app.exe` is NOT elevated.
  7. Check the Status tab: the registration line names HKLM as the winner with no shadow warning; WER OK; backup lines OK; the self-test passes 2/2.
  8. Check that Past sessions, the audit record, the voice profile and both clinics are present (carried over), and record the authorised hosts on this task (PLAN.md L164 by procedure).
  9. `reg query` HKLM and HKCU for the host name, and `icacls "{app}"`.
  10. Run `check-installed-sockets.py` during a desktop transcription and a prose render; expect zero connections.
  11. Run the crash-recovery check: kill `scribe-app.exe` mid-recording, relaunch, and confirm the recording is offered for recovery.
  12. Start with the network unplugged: expect `unverified_offline`.
  13. Re-register the DEV host with the new script, and move the dev models to `ClinikoScribe-dev\models` (the exact commands are given at hand-off).
  14. Delete `ClinikoScribe\models` only after step 7 passes.

  - **Prep done 2026-10-03 (practitioner, normal terminal over remote desktop):** `build-release.py --model-pack` printed "model pack: C:\scribe-release\0.1.0\ClinikoScribe-models-10a83493 (verified against models-manifest.json)". Step 3: `gh attestation verify` on `ClinikoScribe-0.1.0-setup.exe` printed "Verification succeeded!" (digest `e48a6602…e880ac99`; signer and build workflow `.github/workflows/release.yml@refs/heads/main`; source ref `refs/heads/main`), and `Get-FileHash` printed `E48A6602A08B6BFD43834937A713542896E607A290F7A511F5410677E880AC99`, equal to `SHA256SUMS.txt` and the pilot-builds row. Steps 1–2 and 4–14 remain (in person).

  - **RUN 2026-10-03 (practitioner at the computer, normal non-elevated PowerShell — `IsInRole(Administrator)` printed `False`; composer recording):**
    1. `Get-Process chrome, scribe-app, scribe-host, pythonw` printed nothing.
    2. `register-native-host.py --unregister` printed `removed  : HKCU\Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host; WER exclusion pythonw.exe; WER exclusion scribe-app.exe; WER exclusion scribe-host.exe; …\ClinikoScribe\com.scribe.cliniko_host.json; …\ClinikoScribe\scribe-host.exe`.
    3. Done at prep (above).
    4. Setup 0.1.0, clinic-only policy unticked. Finish page: "Clinic Scribe is installed." then "In Chrome, remove any older Clinic Scribe Companion, choose Load unpacked and select C:\Program Files\ClinikoScribe\extension, then fully restart Chrome." No model warning.
    5. Old unpacked extension removed; `C:\Program Files\ClinikoScribe\extension` loaded; Chrome fully restarted.
    6. Started from the Start menu; Task Manager Elevated = **No**; the pinned icon shows green **OK**. The app's log shows `pipe_peer path=C:\Program Files\ClinikoScribe\scribe-host.exe`.
    7. Status tab: "Native host: com.scribe.cliniko_host", "Registration: registered ✓ (this computer's Chrome link)" (HKLM winner, no other link, no per-user override line); self-test `credential_store: PASS`, `session_crypto: PASS`. No exclusion warning lines; the log line at the installed app's start reads `exclusions count=0 state=checked` (location, not-indexed, WER and backup checks all passed).
    8. Carried over: Past sessions empty (none existed before); audit CSV export works; Practitioner tab shows the voice profile enrolled; Clinics tab lists the one clinic (as before). **Authorised host recorded (PLAN.md L164 by procedure): `tuneup-osteopathy.au2.cliniko.com` (TuneUp Osteopathy, checked 2026-09-29).** Clinic 2 still awaits its API-key permission.
    9. `reg query HKLM\…\com.scribe.cliniko_host` → `(Default) REG_SZ C:\Program Files\ClinikoScribe\com.scribe.cliniko_host.json`; the HKCU query → "unable to find the specified registry key or value"; `icacls "C:\Program Files\ClinikoScribe"` → inherited TrustedInstaller/SYSTEM/Administrators `(F)`, `BUILTIN\Users:(I)(RX)`, CREATOR OWNER `(F)` (inherit-only, the Program Files default), the two application-package groups `(RX)`.
    10. `check-installed-sockets.py --seconds 240` during a test recording's Finish, transcription and a **Narrative** render: `RESULT: no connection seen`. The Note tab: "writing style 'narrative' prose shown for 5 sections (26.7s)" (also P.2's prose timing).
    11. A test recording ended mid-way with Task Manager's End task; on relaunch the Recovery tab listed "Session 5d1306b4… (2026-10-03 06:02 UTC) - Cliniko link checked when opened - did not finish cleanly". A recording started straight after this relaunch ran normally.
    12. With a Cliniko treatment note open, Wi-Fi off, app restarted: the Chrome side panel showed "Patient not checked with Cliniko", "Appointment not checked", "Cliniko could not be reached — you can record, but this note cannot be written back until Cliniko verifies it." (the `unverified_offline` path).
    13. `register-native-host.py` (dev): `com.scribe.cliniko_host_dev` → `%LOCALAPPDATA%\ClinikoScribe-dev\com.scribe.cliniko_host_dev.json`, per-user WER exclusions re-added, `verified : OK`.
    14. **Done 2026-10-04 (practitioner, normal terminal; on 0.1.2 after P.3):** `Test-Path "C:\Program Files\ClinikoScribe\models\whisper"` → `True`, then `Remove-Item -Recurse -Force "$env:LOCALAPPDATA\ClinikoScribe\models"` (no output). The practitioner chose to close out before a clinic day on 0.1.2 (the fallback it removes was the old everyday app). Same session: the main checkout fast-forwarded to `origin/main` (`32e7278`) and is now the DEV channel; `register-native-host.py` from it → `com.scribe.cliniko_host_dev` → `%LOCALAPPDATA%\ClinikoScribe-dev\com.scribe.cliniko_host_dev.json`, `verified : OK`. (Was deferred by composer recommendation until the first-recording fix shipped.)
  - **FAULT found at step 10 (round 35 MED-001, open):** the FIRST recording after installing failed at 1.0 s: log `session_transition … recording`, then 1.01 s later `live_transcriber_stop_timeout … recording` and `session_transition … failed`; the Session tab said "Recording failed (device lost or disk full)". The capture failure's exception type is not logged (`session._on_capture_failure` ignores it). A retry in the same process recorded normally, and so did the first recording after a relaunch (step 11). CHUNK_BYTES is one second, so the failure is at the first chunk write or a stream status flag. Likely cause (unconfirmed): the live worker's first-ever model load (Defender's first scan of the newly installed DLLs and the 1.5 GB model) starving the capture path, so PortAudio reports dropped frames (`CaptureOverflowError`). Interim advice to the practitioner: a 10-second test recording after each install or update, before the first patient.
    - **Fix BUILT 2026-10-03 (executor stage-5 leg i5-x1, for 0.1.1; not yet suite-verified or committed):** the capture failure now logs its type name and a fixed detail word, and the transcription stack's imports are warmed once at app start, with the live worker withheld until they finish. The diagnosis and the decisions are in round 35 MED-001. Round 36 MED-001 (a Start made during the warm-up) was decided by the practitioner as option (b) and built by leg i5-x2: every Start, and a voice enrolment, is refused with "still getting ready" while the warm-up runs, for at most 60 s. The interim advice stands until 0.1.1 is installed.

  Done when: every step's on-screen wording is reported and recorded here.
- [x] 🟩 **P.2 Hardware check** on the installed app (Microphone tab): record whisper `medium`'s real-time factor and the prose seconds per section, against the margin verdict. This closes note-learning P.2's timing line and revisits the whisper `small` exclusion if `medium` falls behind.
  - **RUN 2026-10-03 (practitioner, installed 0.1.0, Microphone tab "Run hardware benchmark", on mains):** model report "Whisper model (medium): ready", "VAD model (silero): ready", "Speaker model (wespeaker-voxceleb-resnet34-LM): installed - verified when it loads", "Voice profile: enrolled 2026-09-18". Benchmark: "RTF thresholds: required < 1.00, margin <= 0.75"; `medium` RTF **0.627**, load 3.89 s, audio 53.2 s, peak 1812.8 MiB, 142 words, OK; "live window latency 18.8 s per 30 s window (1.59x real time) - live transcription keeps up on this machine"; "Prose stage (Narrative style): 3 of 3 sections, load 8.5 s; sections 18.1 s wall, 218.6 s CPU; 6.0 s wall and 72.9 s CPU per section WARNING"; "NOTE: the prose styles take 6.0 s per section (> 5 s) on this machine; a long note waits longer for them."; verdict "Hardware check: whisper medium RTF 0.63 OK; prose stage 6.0 s per section WARNING". P.1 step 10 adds a real note: "writing style 'narrative' prose shown for 5 sections (26.7s)".
  - **Verdict:** whisper `medium` keeps up within the margin, so the whisper `small` exclusion stands (D5). The prose WARNING is a wait-time note, not a gate: a 5–8 section prose note waits about 30–50 s after Finish; Verbatim and Clean clinical are immediate. This closes note-learning P.2's timing line; a smaller prose model stays a later option if the wait proves a problem in practice.
- [x] 🟩 **P.3 Upgrade and rollback smoke** with the next CI build (version bumped):
  1. Install N+1 over N; the models are skipped as matching and the data is unchanged.
  2. Reinstall N over N+1; the app starts and reads every store.
  3. Uninstall, check that the data folder remains, then reinstall.

  - **Prepared 2026-10-03 (composer, local commit, not pushed):** version 0.1.1 in every pinned place (`desktop/pyproject.toml`, `__version__`, `extension/src/manifest.ts`, `package.json` and both `package-lock.json` copies; `test_the_version_is_the_same_everywhere` holds), together with the CI timing-test bound (AGENTS.md Known Issues). After P.1 passes: push, run Release, verify the attestation, record the row in `docs/release/pilot-builds.md`, then run steps 1–3.

  - **RUN 2026-10-03 (practitioner at the computer; composer read the installed app's log):**
    0. `gh attestation verify` on `ClinikoScribe-0.1.1-setup.exe` (Release run 37108950093, commit `f9f7642`): "Verification succeeded!" (signer and build workflow `release.yml@refs/heads/main`); `Get-FileHash` `4C5B7455861946C96A7E832F68F4DA8ADB1D9BBE84F497D40CD848F246B04D9D`, equal to `SHA256SUMS.txt` and the pilot-builds row.
    1. **0.1.0 → 0.1.1 in place:** Finish page "Clinic Scribe is updated." / "In Chrome, reload the Clinic Scribe Companion extension, then fully restart Chrome." (models skipped as matching; no pack was needed). The extension reloaded as **0.1.1** with the same ID `mbmhglgadhdohpgbmpbjnaifjagfdfid`; badge **OK**. Log: `ml_warmup duration_ms=2406 state=done` 2.4 s after `app_start`; a Start 3.8 s later recorded normally (no "still getting ready", since the warm-up had finished). Status: "Registration: registered ✓ (this computer's Chrome link)", self-test 2/2. A Discard pressed during live transcription produced `live_transcriber_stop_timeout` then `failed` (by design: the key is kept while the worker may hold plaintext), and a second Discard completed (round 40 LOW-002).
    2. **0.1.1 → 0.1.0 rollback:** Finish page "Clinic Scribe is updated."; the app started on 0.1.0 (log `app_start` 19:17:30 with no `ml_warmup` line, as 0.1.0 has none) and read its stores; no recording was made on 0.1.0.
    3. **Uninstall and reinstall:** Settings → Apps uninstall showed "Clinic Scribe has been removed." / "Your sessions, Past sessions and audit record were left in your Windows profile, unchanged."; `Test-Path "$env:LOCALAPPDATA\ClinikoScribe\config"` → `True`, `Test-Path "C:\Program Files\ClinikoScribe"` → `False`. Reinstalled 0.1.1 with the pack beside it: Finish page "Clinic Scribe is installed." (no model warning); extension loaded unpacked; badge **OK**; Status ✓ and 2/2; data present. Log: `ml_warmup duration_ms=2586 state=done`, then a test recording `recording` → `processing` → `queued` (28 s), discarded.
    - **Result:** every step passed. The practitioner is on **0.1.1** for clinic. Found in passing: round 40 LOW-001 (the Finish page cuts off its third and later paragraphs) and LOW-002 (Discard during live transcription can block for up to 10 s and needs a second press).
    - **Update to 0.1.2 (2026-10-04, practitioner; the round 40 fixes, Release run 37117373944):** `gh attestation verify` "Verification succeeded!" and `Get-FileHash` `C24AF1E6AA75781B2799F8850710D7204DE9FF9EEFB3ACDC69A19531243A2DDA`; in-place update over 0.1.1 "very smooth". Log: `app_start` 00:08:56, `ml_warmup duration_ms=2076 state=done`, a test recording `recording` 00:09:01 → `discarded` 00:09:07 on one press. The Finish page showed all three paragraphs, ending "Open Clinic Scribe from the Start menu." (round 40 LOW-001 confirmed on a real install). The practitioner is on **0.1.2** for clinic.

  Done when: each step's result is recorded.

## Retained Follow-Up Items
Reconciled 2026-10-04 at completion. The pilot plan, the machine allow-list, code signing and Past-sessions backup stay under `Deferred — Actionable Later` with their own fields.
- **Clinic 2's install and Task P.1** (the second clinic's Cliniko key on the installed app, then P.1's Clinics-tab steps for it).
  - Why retained: waiting on the clinic's Cliniko API-key permission (the same wait as the safeguards plan's clinic-2 items).
  - Risk if deferred: blocked-work: clinic 2 cannot use the installed app until its key validates.
  - Revisit by: when clinic 2 grants API-key permission
- **Speaker labels split one voice (P.1 observation, 2026-10-03).** Reading a paragraph alone, the practitioner was labelled as both Speaker 1 and Speaker 2, as had happened before when speaking quietly. Not caused by this plan: the two-speaker step and its threshold are unchanged by installation.
  - Why retained: belongs with the speaker measurement (practitioner-profile Task 6.1 / Phase 3A Task 2.3) and AGENTS.md's three-or-more-speaker item, which need the shared recording set.
  - Risk if deferred: ux-degradation: the clinician fixes attribution when reviewing.
  - Revisit by: the shared recording set (practitioner-profile Task 6.1)
- **The independent review of `docs/practice/`, now including the VoxCeleb "research purposes" caveat** on the shipped speaker model (Task 0.4, D-I2).
  - Why retained: an outside privacy, legal and clinical review; not code.
  - Risk if deferred: correctness: the practice documents and the model's licence position stay unreviewed drafts.
  - Revisit by: before the pilot's routine-use gate
- **Open follow-up, recorded 2026-10-03 (round 35 MED-001), NOT built — needs a real-hardware test:** a larger PortAudio input buffer. `SoundDeviceBackend.open_stream` would pass `RawInputStream(latency=…)` with seconds instead of sounddevice's default `'high'`, which with the 100 ms blocksize tolerates only about 0.1–0.2 s. The capture callback could then wait out a GIL or loader-lock stall of up to that length without a dropped-frames status, whatever caused the stall: a third-party model constructor, Defender, or CPU or disk contention.
  - Unknown until measured on this computer's WASAPI device: whether PortAudio honours a large input latency in shared mode, whether the level meter's cadence changes, and what the extra delay before Finish's last block costs.
  - Trigger: a logged `capture_failure … detail_code=status_input_overflow` on 0.1.1 or later.
  - Risk if deferred: ux-degradation: a capture stall still ends a recording with a clear message.
  - Revisit by: the first `status_input_overflow` in a log
  - [2026-10-04 reconciliation] Still valid — no relevant code changes since 0.1.1; none logged yet.

## Follow-Up Continuation Notes
**Next: write `plan-pilot.md` with `/review-plan`, using this section as its planning source.** The decisions below are the PRACTITIONER's from 2026-10-02; the code facts were verified by the critique lenses at `7849dc4`.

**Decided scope for the pilot plan:**
- **Shadow mode.**
  - A setting captured at Start marks a LINKED recording as a shadow session.
  - Write draft to Cliniko, the Note tab's Copy (button, keyboard and context menu) and Past sessions' Copy saved note are all refused BY NAME; everything else runs normally.
  - The practitioner writes their own note and scores the app's note by hand on the rubric. There is no new Cliniko read.
- **Validation harness.** An offline batch harness runs the real pipeline over a folder of encounters (16 kHz mono 16-bit WAV plus a JSON script of reference lines and expected facts) and reports text-free metrics:
  - WER;
  - per-fact verdicts (laterality, dose, negation, absent);
  - an UNSUPPORTED-ASSERTION tally (PLAN.md L191's main clause, from the assertion model's provenance);
  - an UNCERTAINTY-SURFACED tally;
  - the commit and the models-manifest hash.

  The set is about 40 scripts voiced by text-to-speech, with a voice per role, rate variation, mixed noise at fixed signal-to-noise ratios and simulated overlap, plus about 10 practitioner role-plays. The role-plays are the shared recording set, practitioner-profile Task 6.1, which also feeds Task 2.3/6.2, D-S1 and the 9.1 rubric run. A practitioner-RATIFIED pass rule is set before the run.
- **Governance documents.** A pilot-log template (text-free; the filled copy stays off-repo), a findings register (no session ids; severity, R4-anchored category, status open/resolved/controlled), and an exit gate with routine use opened PER CLINIC (clinic 1 does not wait on clinic 2's Cliniko permission). `incident-process.md` points clinical-safety incidents to the register.
- **Runs:**
  - validation (at least 50);
  - shadow (10, consented);
  - 20 reviewed consultations at clinic 1;
  - clinic 2's safeguards P.1/P.2 first, then 20 there;
  - per-clinic exit gate;
  - note-learning P.2 closed.

**Code facts already verified (re-probe at that plan's write time):**
- **Shadow mode.**
  - Carry the mode on `RecordingSession`, captured at `SessionController.start` (`session.py:774`), and pass it to `audit.begin` (`:831`) before `encounter.enc` is written (`:873-878`). Store it in `EncounterRecord` (`encounter.py:188-205`, `Literal[1]` → v2) so recovery and `adopt_queued` rebuild it.
  - Do NOT add a fourth `read_encounter_record` caller (Critical Constraint 7, `encounter.py:236-243`).
  - The Start funnel is `ui/session_screen.py:302-319`; linked starts arrive via `bridge.py:1053` → `start_linked` (`:293`).
- **Write refusal.** Add `shadow_session` next to D4's `dev_build_writes_off`: the same `refuse_before_read` / `write_control` path.
- **Copy.**
  - Do not refuse through `_copy_ready` (`ui/note.py:2199-2221`): Write derives "saved" from it (`:2283`) and would show "not saved". Add a separate shadow reason that also gates `_NotePanel.copy_selection` (`:286`) and the context menu (`:305`).
  - Past sessions' `_copy_reason`/`on_copy` (`ui/past_sessions.py:472-496`) see only `PastSessionEntry`. The flag goes into `PastSessionLabel` (`past_sessions.py:233-235`, `extra=forbid`, `Literal[1]` → v2) through `KeepLabel`/`keep_label` (`:193-224`), and `UNKNOWN_LABEL` (`:205`) defaults to fail-closed.
- **Audit v2.**
  - Add `mode` and `app_version`. Upgrade v1 rows in `_decode` BEFORE `AuditRow.model_validate`, because `_version_first` (`audit.py:296-303`) rejects any non-current version.
  - `_csv_values` (`:1054-1083`) changes together with `CSV_COLUMNS` (`:1010-1034`).
  - `_PAYLOAD_SIGNATURES` lives in `logging_setup.py:72`; flat tokens need no new signature (state it).
  - Precedents for upgrade-on-read: `past_sessions.py:952-960`, `clinics.py:275`.
- **Upgrade and rollback.** Every v2 schema (audit, label, encounter) needs tests in BOTH directions: N+1 reads N's data, and N reads N+1's data as `_NEWER`/unreadable without refusing Start. A recoverable session from N adopted by N+1 defaults to "normal".
- **Harness.**
  - Entry points (Qt-free):
    - `transcription.transcribe_session` (`:1171`);
    - `note.compose_draft` (`:2357`) → resolve proposals under a declared policy → `note.finalise_note` (`:2471`, which runs the checks; calling `check_note` straight after compose violates the enforced order, `note.py:2378`);
    - prose via `ui/models.build_prose_stage` (`:3250`);
    - provider `note.ExtractiveNoteProvider` (`:1598`).
  - Custody helpers in `speaker_eval.py` (`_write_store` `:874` … `_transcribe_in_temporary_store` `:1045`) move to `eval_store.py`. KEEP re-exports, and keep `speaker_eval` importing `shutil`/`tempfile`, because `tests/test_speaker_eval.py:1064,1088,1107,1318` patch them there.
  - The offline assertion is `benchmark.apply_offline_env`/`assert_offline_env`. The WAV contract is `speaker_eval.read_wav_pcm` (`:296`).
  - SAPI has no voice or rate control yet (`tests/sapi_fixture.py:56-72`, `benchmark.generate_speech_sample` `:287-315`); `resample_wav_to_pcm16` (`sapi_fixture.py:34`) moves into src.
- **Pilot settings** follow `PastSessionSettings` in `config\pilot.json`. The file is user-writable, so shadow mode is a user setting, NOT an enforced control; say so in the threat model.

**Must not be rediscovered:** the shadow refusal must not reuse `_copy_ready`, and the audit upgrade must happen in `_decode`. Both are traps the lenses found in the first draft.

---
*Plan saved to: .cursor/plans/plan-installation.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
*Sections marked (Only if relevant) can be omitted when genuinely not applicable, but never omit decisions, constraints, verification steps, or integration knowledge that a fresh session would otherwise have to rediscover.*
*State-once convention (new plans): state each cross-section contract — a critical constraint, design decision, invariant, or other normative rule — once in its canonical section, and have every other section point to it rather than restate it.*
