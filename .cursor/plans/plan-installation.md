# Feature Implementation Plan
**Feature:** installation
**Overall Progress:** `0%`

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
- Last completed step: Planning complete — hardened by `/review-plan` on 2026-10-02 (native plan → three critique lenses → practitioner clarifications → deferral gate), then peer-hardened by `/peer-loop` (codex `gpt-6-astra` medium, plan-review mode): rounds 1–3, 3 → 2 → 0 findings, converged at round 3 (no new build-affecting finding).
- Current in-progress step: None
- Immediate next action: commit this plan; then Task 0.1 (the agent builds the frozen-app spike; the PRACTITIONER runs it in an isolated `LOCALAPPDATA` from a normal terminal), then Task 0.2 (the frozen host), via `/execute` or `/execute-loop`.
- Open blockers / open questions: `[decision]` D-I1 (install location) waits on Task 0.2; `[decision]` D-I2 (bundle the speaker model) waits on Task 0.4.
- Last plan sync: 2026-10-02

## Review History
- 2026-10-02 round 1: 0 CRIT / 0 HIGH / 3 MED / 0 LOW; skew=none; action=amend (codex gpt-6-astra medium plan peer-review; 3 build-affecting, all applied by the owning planning session)
- 2026-10-02 round 2: 0 CRIT / 0 HIGH / 2 MED / 0 LOW; skew=none; action=amend (codex gpt-6-astra medium; verified 1 build-affecting / 1 record-only, both applied)
- 2026-10-02 round 3: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium; 8 candidates, 8 dropped; plan-review loop CONVERGED — no new build-affecting finding from round 2 on; one precision note applied to Task 0.2)

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

## Tasks
Paths are under `desktop/src/scribe_desktop/` unless stated. Every code task's verification is the plan's Validation section (composer-run suites) unless the task names its own. Phases are grouped for `/execute-loop`: foundational layout and identity (Phase 1) are isolated ahead of the frozen-runtime work (Phase 2) and the build (Phase 3).

### Phase 0 — Spikes (agent builds, PRACTITIONER verifies from a normal terminal)
- [ ] 🟥 **0.1 Frozen app runtime, run in an ISOLATED profile.** A spike `packaging/spike/scribe.spec` building `scribe-app.exe` on Python 3.14 (fallback 3.12). Checks:
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
- [ ] 🟥 **0.2 Frozen host launched by Chrome** (after Task 0.1: it uses 0.1's interpreter).
  - The agent writes a throwaway `packaging/spike/host.spec`: a one-folder windowed `scribe-host.exe` from the real `native_host.main`.
  - If Task 0.1 found the standard streams None, the spike entry carries the minimal stdio adaptation: binary stdin/stdout obtained through `msvcrt.open_osfhandle(GetStdHandle(...))` before `set_binary_stdio` (`framing.py:54`) and `run_host` (`native_host.py:570-573`). Without it the handshake cannot succeed whatever the folder (round 1 PR-MED-002). Task 2.2 then integrates and hardens this PROVEN adaptation.
  - The practitioner copies it to `C:\Program Files\ClinikoScribe\` with a manifest there, registers it in HKLM (exact `reg add` lines are given in the task hand-off), removes the HKCU dev registration first, and opens Cliniko with the dev app running.
  - Scope of this check (round 2 PR-MED-001): it is TRANSPORT-ONLY — the badge turns green OK; no recording is started, no patient note is opened beyond the page needed for the link, and no clinical data is written (the dev app's ordinary start-up maintenance — sweep, prune, logs — still runs, as it does every day; round 3 precision note). The dev app here is today's ordinary app on today's data folder, unchanged (Phase 1 has not run), so the spike adds no new data path. The frozen host runs the same `native_host` code as today's host and writes only its content-free log under Chrome's environment (the real `logs\` folder, as today). Isolating the app as well is not required because nothing new runs against the stores.
  - If Program Files fails, repeat at `C:\ClinikoScribe` with `icacls /inheritance:r`, Administrators and SYSTEM full, Users read and execute. Also re-add the HKCU entry once to confirm it shadows HKLM (D9).
  - Done when: the host log shows `origin_verified` and the badge is green OK from the chosen folder; the result is recorded on this task; the HKCU dev registration is restored afterwards.
- [ ] 🟥 **0.3 Inno mechanics and CI.** A throwaway `.iss` with `PrivilegesRequired=admin`, a `[Code]` `GetSHA256OfFile` check over a 2.5 GB file (timed), the HKLM WER values, the `FilesNotToSnapshot`/`FilesNotToBackup` value forms (does `$UserProfile$` work for `FilesNotToBackup`, or only `%var%`?), the install-folder ACL, and in-place upgrade under the same AppId. Separately, confirm whether `windows-latest` has Inno Setup 6, and which version to pin.
  - Done when: each answer is recorded on this task, and Task 3.4's value forms are fixed.
- [ ] 🟥 **0.4 WeSpeaker licence.** Confirm the licence of the `wespeaker-voxceleb-resnet34-LM` ONNX export at its source (the "MIT" claim was dropped as unverified, `plan-practitioner-profile.md` round 8).
  - Done when: the licence text and source URL are recorded here.
- [ ] 🟥 **0.5 Defender and Smart App Control.**
  - Run a Defender custom scan of the Task 0.1 bundle: `Start-MpScan -ScanType CustomScan -ScanPath <dist>` then `Get-MpThreatDetection`.
  - Record this computer's Smart App Control state (Windows Security → App & browser control).
  - Done when: both results are recorded. A detection or Smart App Control "On" pauses the plan for a signing decision (C10).
- [ ] 🟥 **D-I1: Install location.** `[decision]`
  - Options: `C:\Program Files\ClinikoScribe` / `C:\ClinikoScribe` with an explicit ACL.
  - Decide after: Task 0.2.
  - Blocks: Tasks 1.1 (`install_root`), 3.4.
- [ ] 🟥 **D-I2: Bundle the speaker model?** `[decision]`
  - Options: in the model pack (licence permits redistribution) / fetched per computer by `setup-models.py --only speaker-embedding --root {app}\models` run as admin, and verified by the installer's manifest check on the next install.
  - Decide after: Task 0.4.
  - Blocks: Task 3.3.

### Phase 1 — Channel, layout and the dev separation
- [ ] 🟥 **1.1 `install_layout.py` (new).** It provides:
  - `is_frozen()`, injectable;
  - `channel() -> Literal["production","dev"]`;
  - `install_root()`: frozen → the folder of `sys.executable`, checked against D-I1; dev → `None`;
  - `data_root()`: `%LOCALAPPDATA%\ClinikoScribe` or `…\ClinikoScribe-dev`, re-reading the environment on every call; when `LOCALAPPDATA` is unset it keeps today's home-folder fallback;
  - `models_root()`: frozen → `install_root()\models`; dev → `data_root()\models`, keeping `default_models_root`'s raise-when-unset contract (`test_language_model_runtime.py:722`);
  - `app_data_root_via(layer)`, for the `WindowsLayer`-seamed caller.

  A conftest autouse fixture pins the production channel (D2).

  Done when: tests cover both channels, frozen and not, and `LOCALAPPDATA` set and unset.
- [ ] 🟥 **1.2 Repoint every data-folder builder** (the table in Key Findings) to `install_layout`. `benchmark.default_models_root` delegates to `models_root()`.
  - Add a grep test: no `ClinikoScribe` path built outside `install_layout`, with the non-path literals allow-listed BY NAME.
  - Done when: the suite is green with the channel pinned to production, and a dev-channel test shows each store under `ClinikoScribe-dev` (C8).
- [ ] 🟥 **1.3 Extension `--mode dev|release` and the dev key** (first: Task 1.4 needs the dev ID).
  - `vite.config.ts`/`manifest.ts` take the key, name suffix (" (dev)") and host name from the mode. `protocol.ts` `HOST_NAME` is injected at build (`define`).
  - FIRST, `scripts/generate-extension-key.py --out extension/key-dev.pem` (gitignored; the script gains `--out`, default unchanged); the dev PUBLIC key is committed and the dev extension ID derived from it is recorded on this task.
  - `manifest.test.ts`/`scaffold.test.ts` cover both modes, and the release mode keeps `mbmh…`.
  - The default `npm run build` stays release, so today's `extension/dist` is unchanged.
  - Done when: `npm run qa` passes, and both builds produce manifests with their own key and host name.
- [ ] 🟥 **1.4 Identity accessors** in `identity.py` (desktop) for each channel:
  - `host_name()`, `extension_id()`, `expected_origin()`, `registry_key()` and `pipe_prefix()`;
  - dev values: `com.scribe.cliniko_host_dev`, the dev ID recorded by Task 1.3, and `ClinikoScribe-dev-`.

  Production constants are unchanged (C2). Consumers switch to the accessors: `native_host.py:70,114,537`, `status.py:14`, `ui/main_window.py:87,234`, `pipe_server.py:176`, `pipe_client.py`.

  Done when: the pins in `test_protocol.py:58`, `test_display_name.py` and `test_pipe_server.py` pass unchanged, and new dev-channel tests pass.
- [ ] 🟥 **1.5 One single-instance guard across channels** (D3). Both channels acquire the same per-user exclusion (today's mutex name, plus a lock in a channel-independent location chosen and justified by the executor), so the second app shows "already running" whichever channel started first.
  - Done when: `test_status_and_app.py`'s guard tests pass for both channels, and a cross-channel test proves mutual exclusion through the seam.
- [ ] 🟥 **1.6 Dev write guard (D4).**
  - Add `dev_build_writes_off` to `WriteRefusalName` (`draft_write.py:1054`).
  - `refuse_before_read` gains a `channel`/`allow` input from its two callers (`main_window.py:1874`, `draft_write.py:1180`), and `ui/models.write_control` disables Write with the same reason.
  - Add the wording in `write_refusal_line`; decide whether it joins `WRITE_UNCERTAIN_PREFIXED` (`ui/models.py:399`; expected: no).
  - `config\dev.json` loader on the `PastSessionSettings` pattern.
  - The dev-only Status checkbox, worded "Allow Cliniko writes from this developer build", default off.
  - Update pins `test_write_lines.py:70`, `test_draft_write.py:1649,1666`, `test_audit.py:204-208`.
  - Done when: in production the guard can never refuse (test); in dev it refuses until ticked; the audit row records `last_refusal=dev_build_writes_off`.
- [ ] 🟥 **1.7 Remedy lines.** One `install_layout.model_remedy()` and one `registration_remedy()`. Frozen: "Missing or damaged — reinstall Clinic Scribe". Dev: today's script commands. They replace every string in Key Findings' remedy list and update the listed test pins.
  - Done when: both channels are tested and a grep finds no other "run scripts/" string in `src`.
- [ ] 🟥 **1.8 Version pin (D12).** One test asserts that pyproject, `__init__.__version__`, `manifest.ts` and `package.json` agree. Version stays `0.1.0` until the first release task bumps it.

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
- [ ] 🟥 **3.4 `packaging/scribe.iss`** (D1, D5, D6, D8, D-I1). It covers:
  - `PrivilegesRequired=admin`, a fixed AppId and `SetupLogging=no`;
  - a running-process check (`scribe-app.exe`, `scribe-host.exe`, `chrome.exe`) with the "Close Clinic Scribe and Chrome completely" message;
  - the install folder with D-I1's ACL;
  - the models copied from the adjacent pack and checked against the compiled manifest (abort with a message naming the file; skipped when `{app}\models` already matches);
  - HKLM: the native-host key and manifest, the WER values, the backup and snapshot values (Task 0.3's forms), and the optional clinic-only policy checkbox with D8's wording;
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
