# Feature Implementation Plan
**Feature:** installation
**Overall Progress:** `19%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
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
- **GitHub's `actions/attest-build-provenance`** produces a Sigstore attestation that `gh attestation verify <file> --repo eliemokbel3-hub/Recording-clinic-software` checks. Whether Inno Setup is preinstalled on `windows-latest` is UNVERIFIED (Task 0.3); otherwise the job installs a pinned version.

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
- **C6 — Host-state reads go through seams,** tested in both directions. No test touches the real registry, `%LOCALAPPDATA%`, a real model file or a real Chrome; the conftest sentinels stay.
- **C7 — Checks from an agent shell never count** for registry, ACL, `%LOCALAPPDATA%`, install, Chrome or model-folder state (MSIX). They are practitioner steps with scripted on-screen wording to report.
- **C8 — The dev channel never reads or writes the production data folder or models.** The one exception is the shared single-instance guard (D3).
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
- Last completed step: **Phase 0 COMPLETE** — every spike run by the practitioner from a normal PowerShell (C7) on 2026-10-02 and recorded on its task by stage-0 executor leg i0-x12 (2026-10-02T22:46+10:00). Tasks 0.1, 0.2, 0.3, 0.4 and 0.5 are 🟩, and D-I1 / D-I2 are chosen 🟩. Earlier: the spike inputs (leg i0-x1), the peer pass stage-0.p1 (rounds 4–8, closed at the cap), and planning hardened by `/review-plan` and `/peer-loop` rounds 1–3.
- Current in-progress step: Phase 0 closed in the plan, awaiting the composer's Phase 0 commit. Phase 1 is BUILT and held in `git stash` (see COMPOSER RUN-STATE).
- Immediate next action (composer):
  1. Commit Phase 0 (the plan plus `packaging/spike/`; never `extension/key-dev.pem`).
  2. `git stash pop`.
  3. Apply Task 1.1's D-I1 narrowing (`INSTALL_ROOTS` → `C:\Program Files\ClinikoScribe`).
  4. The composer-run suites, then `/review-loop` for Phase 1.
  5. Keep `C:\scribe-spike` until the benchmark comparison below is done (Finishing up step 3 is held).
- Open blockers / open questions: the Phase 0 MUST-PAUSE for practitioner runs is DISCHARGED (2026-10-02). None of the following blocks Phase 0's close; each is owned and has a recommendation.
  1. **Inno Setup licensing** `[practitioner]`. The local ISCC 6.7.3 prints **"Non-commercial use only"** (Task 0.3).
     - The plan currently ASSUMES Inno Setup is freely usable: Config / Deployment Impact lists it only as "a pinned version on the CI runner and on the practitioner's machine". No licence term is recorded, and PLAN.md has a commercial path.
     - Whether a clinician building an installer for their own practice counts as commercial use, and what a commercial licence would cost or require, is unchecked.
     - rec= before Task 3.4 / 3.6 ship any release installer, the composer runs one web-granted research leg on jrsoftware.org's current licence terms. The practitioner then decides: licence it, confirm it is not needed, or switch to an alternative. Phases 1–2 and the build work through Task 3.2 do not depend on it.
  2. **Task 3.6 Inno pin** `[decision, Task 3.6]`. CI images carry 6.7.1 (leg i0-x2); the practitioner's local build used 6.7.3.
     - rec= **pin 6.7.3 on both sides**:
       - CI installs that exact version from a SHA-256-checked installer and asserts `ISCC`'s version banner, rather than relying on the image's preinstalled copy, which images update weekly and which would drift anyway;
       - local builds keep the 6.7.3 already installed;
       - the `windows-2025` label stands.
     - This supersedes the leg i0-x2 recommendation of 6.7.1. Downgrading the practitioner's machine to 6.7.1 would also work, but it pins the build to whatever the image happens to carry.
     - Take it together with item 1, since a licence decision may change the version.
  3. **Frozen benchmark speed** `[practitioner run]`. The GUI benchmark through the frozen worker path gave medium RTF **1.27** (FAIL) ON BATTERY. The in-process spike check gave **0.482** on the same 53.2 s sample (Task 0.1). The cause — frozen worker, the benchmark's measurement, or battery — is NOT established.
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
  - **Docs left for H.1:** `docs/security/threat-model.md` (still names the old remedy constants and the single data folder), `scripts/README.md`, `extension/KEY.md` (the dev key), and AGENTS.md Local Run Steps (dev folder, `--mode dev`).
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
- Last plan sync: 2026-10-02T22:46+10:00
- Loop config: executor=claude-p model="claude-opus-5-5" effort=high profile=default; peer=codex model="gpt-6-astra" effort=medium; architect=off; cadence=every-phase; caps=review:3,peer:5; gates=executor; cap-raise=executor; high-auto=on; peer-max=12; notify=action-only; scope=all; autocommit=on; isolation=none; merge=off; perms=scoped; liveness=10; monitor-delivery=auto; verify=composer
- COMPOSER RUN-STATE: /execute-loop run iso `installation-20261002-113527-26e920` (isolation=none, checkout base), started 2026-10-02T11:36+10:00; runkeys stage-0..stage-5 (stage-0 = Phase 0 spikes; stage-1..3 = Phases 1-3; stage-4 = Phase H; stage-5 = Phase P); probe logs `.cursor/loops/stage-N-probe.log`; spawn helper `.cursor/loops/inst-spawn.sh`. Phase 0 peer pass stage-0.p1 CLOSED at the cap (rounds 4–8; runbook hardened); Phase 0 stays OPEN (MUST-PAUSE practitioner-spikes, uncommitted). Practitioner chose 2026-10-02 to start Phase 1 meanwhile (install_root's D-I1 left as a marked placeholder). Phase 1 BUILT by leg i1-x2 (2026-10-02T13:36, session 2c6ee9f4-c834-41e3-a814-f9ffeff0da77; ruff+mypy clean, suites NOT yet run). Its code is HELD in `git stash` entry "installation Phase 1 (stage-1 leg i1-x2) …" (51 files) because the venv's editable install makes the working tree live for the everyday app and Chrome host and for the Phase 0 spike runbook (which assumes today's code). `extension/key-dev.pem` is untracked while the stash holds its .gitignore line — never commit it. Resume order: practitioner spikes → Phase 0 results/close/commit → `git stash pop` → composer-run suites → resume i1-x2's session for /review-loop.

## Review History
- 2026-10-02 round 1: 0 CRIT / 0 HIGH / 3 MED / 0 LOW; skew=none; action=amend (codex gpt-6-astra medium plan peer-review; 3 build-affecting, all applied by the owning planning session)
- 2026-10-02 round 2: 0 CRIT / 0 HIGH / 2 MED / 0 LOW; skew=none; action=amend (codex gpt-6-astra medium; verified 1 build-affecting / 1 record-only, both applied)
- 2026-10-02 round 3: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium; 8 candidates, 8 dropped; plan-review loop CONVERGED — no new build-affecting finding from round 2 on; one precision note applied to Task 0.2)
- 2026-10-02 round 4: 0 CRIT / 0 HIGH / 3 MED / 1 LOW; skew=none; action=fix → all 4 Applied with siblings, round Closed (codex gpt-6-astra medium, pass stage-0.p1 peer_round 1 — Phase 0 spike inputs and runbook; LEG 1 verified 1 MED + 3 LOW, all CONFIRMED; LEG 2 /fix leg i0-x4 2026-10-02T12:33+10:00 edited `packaging/spike/RUNBOOK.md` and the `spike_app_entry.py` docstring only)
- 2026-10-02 round 5: 0 CRIT / 0 HIGH / 2 MED / 1 LOW; skew=none; action=fix → all 3 Applied with every enumerated sibling, round Closed (codex gpt-6-astra medium, pass stage-0.p1 peer_round 2 — confirmation of round 4's fix; LEG 1 verified 2 MED + 1 LOW, all CONFIRMED; LEG 2 /fix leg i0-x6 2026-10-02T12:42+10:00 edited `packaging/spike/RUNBOOK.md` only; the prior-state check + exact undo + failure route class is now closed across every state-changing step)
- 2026-10-02 round 6: 0 CRIT / 0 HIGH / 2 MED / 1 LOW; skew=fix-induced; action=fix → all 3 Applied with every sibling, round Closed (codex gpt-6-astra medium, pass stage-0.p1 peer_round 3 — confirmation of round 5's fix; LEG 1 leg i0-x7 verified 1 MED + 2 LOW, all CONFIRMED; LEG 2 /fix leg i0-x8 2026-10-02T12:53+10:00 edited `packaging/spike/RUNBOOK.md` only: the venv half closed by DESIGN — the build runs in a copy `C:\scribe-spike\venv-build`, the everyday `.venv` is only read, and the backup/restore is removed — plus record-gated, verified install-folder cleanup; the class is closed)
- 2026-10-02 round 7: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=none; action=fix → 1 Applied with both siblings, round Closed (codex gpt-6-astra medium, pass stage-0.p1 peer_round 4 — confirmation of round 6's redesign; LEG 1 leg i0-x9 verified 1 LOW (peer MED), test-harness, CONFIRMED; LEG 2 /fix leg i0-x10 2026-10-02T12:59+10:00 edited `packaging/spike/RUNBOOK.md` only: the 3.12 fallback is a numbered procedure that replaces every build-copy call, and 0.2 step 2 gives the `venv312` host-build command)
- 2026-10-02 round 8: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=accept-close (codex gpt-6-astra medium, pass stage-0.p1 peer_round 5 = cap — confirmation of round 7's fix; PR-LOW-015 verified low test-harness, Accepted with record per the executor's cap verdict; peer pass stage-0.p1 CLOSED at the cap, trajectory 4 → 3 → 3 → 1 → 1)

## Review Findings Log
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
- [ ] 🟨 **1.1 `install_layout.py` (new).** It provides:
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
- [ ] 🟨 **1.2 Repoint every data-folder builder** (the table in Key Findings) to `install_layout`. `benchmark.default_models_root` delegates to `models_root()`.
  - Add a grep test: no `ClinikoScribe` path built outside `install_layout`, with the non-path literals allow-listed BY NAME.
  - Done when: the suite is green with the channel pinned to production, and a dev-channel test shows each store under `ClinikoScribe-dev` (C8).
- [ ] 🟨 **1.3 Extension `--mode dev|release` and the dev key** (first: Task 1.4 needs the dev ID). Leg i1-x1: `--out` added to the key script (default unchanged; a relative path is from the repo root) and `extension/key-dev.pem` added to `.gitignore` (the bare `key.pem` entry does not match it); the key run is composer-run.
  - `vite.config.ts`/`manifest.ts` take the key, name suffix (" (dev)") and host name from the mode. `protocol.ts` `HOST_NAME` is injected at build (`define`).
  - FIRST, `scripts/generate-extension-key.py --out extension/key-dev.pem` (gitignored; the script gains `--out`, default unchanged); the dev PUBLIC key is committed and the dev extension ID derived from it is recorded on this task.
  - `manifest.test.ts`/`scaffold.test.ts` cover both modes, and the release mode keeps `mbmh…`.
  - The default `npm run build` stays release, so today's `extension/dist` is unchanged.
  - Done when: `npm run qa` passes, and both builds produce manifests with their own key and host name.
  - Leg i1-x2: the composer ran the key script (exit 0; `git check-ignore` → `.gitignore:28`). **Dev extension ID: `pecfiifdlmdbkifmjkbkeiaflpenfejd`.** The dev PUBLIC key is committed in the new `extension/src/channel.ts` (`CHANNELS.dev.key`), beside the unchanged release key and `mbmh…` id; `channelForMode` maps `dev` → dev, `release`/`production` (Vite's default) → release, and refuses anything else. The dev build outputs to `extension/dist-dev` (gitignored), so `extension/dist` stays release. `HOST_NAME` is `__SCRIBE_HOST_NAME__` from `buildDefines` (vitest injects the release value). `manifest.test.ts` derives each id from its key; `test_identity.py` cross-checks `channel.ts` against `identity.py`.
- [ ] 🟨 **1.4 Identity accessors** in `identity.py` (desktop) for each channel:
  - `host_name()`, `extension_id()`, `expected_origin()`, `registry_key()` and `pipe_prefix()`;
  - dev values: `com.scribe.cliniko_host_dev`, the dev ID recorded by Task 1.3, and `ClinikoScribe-dev-`.

  Production constants are unchanged (C2). Consumers switch to the accessors: `native_host.py:70,114,537`, `status.py:14`, `ui/main_window.py:87,234`, `pipe_server.py:176`, `pipe_client.py`.

  Done when: the pins in `test_protocol.py:58`, `test_display_name.py` and `test_pipe_server.py` pass unchanged, and new dev-channel tests pass.
  - Leg i1-x2: the accessors take `of: Channel | None = None` and read `install_layout.channel()` at call time; production constants (`HOST_NAME`, `EXTENSION_ID`, `EXPECTED_ORIGIN`, `REGISTRY_KEY`, new `PIPE_PREFIX`) are unchanged, and `pipe_server.PIPE_PREFIX` is still exported. `scripts/register-native-host.py` registers the running channel's host, origin and install folder (`ClinikoScribe-dev` from source); its legacy-artifact sweep stays on the production name. `test_display_name.py`'s literal `INSTALL_DIR` source pin (not an identity value) was updated to the new expression.
- [ ] 🟨 **1.5 One single-instance guard across channels** (D3). Both channels acquire the same per-user exclusion (today's mutex name, plus a lock in a channel-independent location chosen and justified by the executor), so the second app shows "already running" whichever channel started first.
  - Done when: `test_status_and_app.py`'s guard tests pass for both channels, and a cross-channel test proves mutual exclusion through the seam.
  - Leg i1-x2: the lock is `%LOCALAPPDATA%\ClinikoScribe\app.lock` for BOTH channels (`install_layout.instance_guard_root()`), with the mutex name unchanged. Justification: the production folder is the one per-user location both channels already resolve and that a dev build may touch (C8's named exception), and keeping it there leaves today's production lock where it is. The dev build creates only `app.lock` there (pinned by test).
- [ ] 🟨 **1.6 Dev write guard (D4).**
  - Add `dev_build_writes_off` to `WriteRefusalName` (`draft_write.py:1054`).
  - `refuse_before_read` gains a `channel`/`allow` input from its two callers (`main_window.py:1874`, `draft_write.py:1180`), and `ui/models.write_control` disables Write with the same reason.
  - Add the wording in `write_refusal_line`; decide whether it joins `WRITE_UNCERTAIN_PREFIXED` (`ui/models.py:399`; expected: no).
  - `config\dev.json` loader on the `PastSessionSettings` pattern.
  - The dev-only Status checkbox, worded "Allow Cliniko writes from this developer build", default off.
  - Update pins `test_write_lines.py:70`, `test_draft_write.py:1649,1666`, `test_audit.py:204-208`.
  - Done when: in production the guard can never refuse (test); in dev it refuses until ticked; the audit row records `last_refusal=dev_build_writes_off`.
  - Leg i1-x2: the pure check is `draft_write.dev_build_writes_off(channel, allow)`, run after `mock_note` and before `record_unreadable`. The settings file lives in `note_config` (`DevSettings`, `load_dev_settings`, `save_dev_settings`, `dev_writes_allowed`), not `draft_write`, because `draft_write` is pinned disk-free. A file it cannot use reads as writes OFF, and production never reads it. NOT in `WRITE_UNCERTAIN_PREFIXED`. If saving the Status checkbox fails, the box is put back and a line says why.
- [ ] 🟨 **1.7 Remedy lines.** One `install_layout.model_remedy()` and one `registration_remedy()`. Frozen: "Missing or damaged — reinstall Clinic Scribe". Dev: today's script commands. They replace every string in Key Findings' remedy list and update the listed test pins.
  - Done when: both channels are tested and a grep finds no other "run scripts/" string in `src`.
  - Leg i1-x2: remedies key on `is_frozen()` (a source run of either channel has the scripts). The frozen clause is `FROZEN_REMEDY = "reinstall Clinic Scribe"`, placed after each line's own "missing or damaged" wording. The former constants are now functions (`models.language_model_absent_reason()`, `speaker_model_missing_reason()`, `attribution_did_not_run_reason()`, `exclusions.wer_not_excluded_line()`). Not in the plan's list but covered: `language_model._import_llama`'s prose-runtime remedy.
- [ ] 🟨 **1.8 Version pin (D12).** One test asserts that pyproject, `__init__.__version__`, `manifest.ts` and `package.json` agree. Version stays `0.1.0` until the first release task bumps it.
  - Leg i1-x2: the pin is in `test_install_layout.py` and also covers both `package-lock.json` copies (root and `packages[""]`), which the plan did not list.

### Phase 2 — Frozen-runtime support
- [ ] 🟥 **2.1 Benchmark worker entry.**
  - When frozen, `benchmark.run_all` spawns `[sys.executable, "--benchmark-worker", "--single", …]`.
  - `app.main` dispatches `--benchmark-worker` to `benchmark.main(argv)` BEFORE `QApplication` (`app.py:549`) and before the guard, only when `_WORKER_ENV == "1"` and the argv shape matches exactly. Anything else is ignored, not started.
  - The worker's stdout must exist under the windowed bootloader. If Task 0.1 found it None, write the JSON to a temp file whose path is passed in argv.
  - Done when: tests cover the frozen and dev spawn shapes, and that the dispatch refuses without the env var or with extra arguments.
- [ ] 🟥 **2.2 Native-host stdio fallback** (integrates and hardens the adaptation Task 0.2 proved).
  - `native_host.main` obtains binary stdin/stdout from `sys.stdin.buffer`, or, when None (frozen windowed), from `msvcrt.open_osfhandle(GetStdHandle(...))` through a small seam.
  - `set_binary_stdio` applies to whichever it got.
  - Done when: the seam is tested with both shapes and protocol tests are unchanged.
- [ ] 🟥 **2.3 Registry readers in Chrome's order (D9).**
  - A new `WindowsLayer` method returns the host entries for a name in HKCU and HKLM, in both views.
  - `status.read_registration_status` and `_log_registration_paths` report the winning entry and the others.
  - In a frozen build a production-name HKCU entry raises the Status warning.
  - Fake-layer tests cover none, HKCU-only, HKLM-only, both, and the 32-bit view only.
- [ ] 🟥 **2.4 The WER set by channel, plus a backup-exclusion check (D10, D6).**
  - `check_wer` takes the channel's set and reads HKLM then HKCU.
  - New `check_backup_exclusions` reads the two HKLM `ClinikoScribe` values and checks they cover `sessions` and `logs`.
  - Both only ever warn, wrapped so a read error is a warning (`startup_exclusions`, `exclusions.py:338-365`).
  - Done when: FakeLayer tests cover each state, and the dev channel never warns about the HKLM values.
- [ ] 🟥 **2.5 Hardware check (D11).**
  - The Microphone tab's benchmark gains a prose-stage timing:
    - fixed non-clinical lines;
    - `build_prose_stage` in-process, timed per section;
    - CPU seconds and wall seconds;
    - skipped with a named line when the language model is absent;
    - the injectable runner keeps tests model-free.
  - It also shows whisper `medium`'s real-time factor and `threshold_report`'s verdict for both. The results are text-free.
  - Done when: tests inject the model present and absent, and the panel lines are pinned.

### Phase 3 — Build and installer
- [ ] 🟥 **3.1 `desktop/requirements-build.txt`.** Every runtime dependency (the `[ml]` extra, `sounddevice`), PyInstaller and its hooks package, all `--require-hashes`. The prose wheel stays in `requirements-ml-prose.txt`. A test checks that every `pyproject` runtime dependency appears in the lock.
- [ ] 🟥 **3.2 `packaging/scribe.spec`** (D1). Two windowed EXEs in one COLLECT. Collect `scribe_desktop` package data, apply Task 0.1's hidden imports and hooks, exclude the network Qt modules, no UPX, and add a version resource from D12.
  - Done when: `pyinstaller packaging/scribe.spec` builds on the composer's machine. The bundle audit runs on that output once Task 3.5 lands; this task is not blocked on it.
- [ ] 🟥 **3.3 Models manifest** (D5, D-I2).
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
- [ ] 🟥 **3.4 `packaging/scribe.iss`** (D1, D5, D6, D8, D-I1). It covers:
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
- [ ] 🟥 **3.5 `scripts/build-release.py`** (needs Tasks 3.1–3.4).
  - Steps: clean build venv, `pip install --require-hashes -r desktop/requirements-build.txt` plus the prose wheel, PyInstaller with Task 3.2's spec, then `--audit`:
    - the expected files are present;
    - no `Qt6Network`/`QtWebSockets`;
    - the frozen app's offline variables are asserted by running `scribe-app.exe --self-check-offline` (a no-GUI, exit-code-only entry dispatched like 2.1);
    - a Defender custom scan when available;
  - then `npm ci` and `npm run build -- --mode release` into `{dist}\extension`, ISCC over Task 3.4's `scribe.iss` with `/DAppVersion`, and `SHA256SUMS.txt` over every output.
  - `--model-pack` copies Task 3.3's `build/models` into `ClinikoScribe-models-<sha8>/` and verifies it against the manifest.
  - Run by the practitioner for local builds.
  - Done when: `--audit` and `--model-pack` are tested against fake trees for each refusal, and one local build passes the audit (the integration gate for Task 3.2).
- [ ] 🟥 **3.6 `.github/workflows/release.yml`** (D7; needs Task 3.5). `workflow_dispatch` on `main` only, `windows-latest`, the pinned Python from D12, Inno from Task 0.3 (preinstalled or a pinned install), `build-release.py` without the model pack, `actions/attest-build-provenance` over `setup.exe` and `SHA256SUMS.txt`, then upload the artifact. Permissions are least-privilege.
  - Done when: one green run is attested and `gh attestation verify` passes (practitioner); the existing `ci.yml` is unchanged.
- [ ] 🟥 **3.7 `scripts/register-native-host.py` becomes dev-only.**
  - It registers `com.scribe.cliniko_host_dev` in HKCU only, installing to `%LOCALAPPDATA%\ClinikoScribe-dev`.
  - `--unregister` also removes a stray HKCU `com.scribe.cliniko_host` key and the legacy production-folder copy.
  - A `PermissionError` with winerror 32 gives "Close Clinic Scribe and Chrome completely, then run this again" (retires `plan-privacy-professional-controls.md` L1313).
  - Update `test_register_native_host.py` and `test_display_name.py:64`.
- [ ] 🟥 **3.8 `scripts/check-installed-sockets.py`.** Run from a normal terminal while the installed app transcribes and renders prose. It walks the `scribe-app.exe` and `scribe-host.exe` process trees with psutil (lessons: walk the tree) and reports any inet connection, text-free.
  - Done when: it is tested against a fake process table, and the practitioner runs it in P.1.
- [ ] 🟥 **3.9 `docs/release/pilot-builds.md`.** A table of version, commit, CI run, the installer SHA-256 and the model-pack manifest SHA-256, plus the two verification commands (`gh attestation verify`, `Get-FileHash`).

### Phase H — Documents and hardening
- [ ] 🟥 **H.1 Security and project documents, as one class (C9).**
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
- [ ] 🟥 **H.2 `/review-loop`** over the whole plan's diff to convergence.
- [ ] 🟥 **H.3 `/simplify`.** Log findings; trivial ones go to `/fix`, substantial ones to a scoped `/review-plan`.
- [ ] 🟥 **H.4 `/security-review`.** Same routing.
- [ ] 🟥 **H.5 Cross-family codex peer** (`gpt-6-astra`) in slices of at most 15 files each: (a) packaging, scripts and CI; (b) layout, identity, guard, write guard and readers; (c) benchmark, UI and docs. A confirmation round follows any hardening fix.

### Phase P — Install on this computer (PRACTITIONER, normal terminal or Explorer)
- [ ] 🟥 **P.1 Install and verify.**
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

  Done when: every step's on-screen wording is reported and recorded here.
- [ ] 🟥 **P.2 Hardware check** on the installed app (Microphone tab): record whisper `medium`'s real-time factor and the prose seconds per section, against the margin verdict. This closes note-learning P.2's timing line and revisits the whisper `small` exclusion if `medium` falls behind.
- [ ] 🟥 **P.3 Upgrade and rollback smoke** with the next CI build (version bumped):
  1. Install N+1 over N; the models are skipped as matching and the data is unchanged.
  2. Reinstall N over N+1; the app starts and reads every store.
  3. Uninstall, check that the data folder remains, then reinstall.

  Done when: each step's result is recorded.

## Retained Follow-Up Items
N/A until completion.

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
