# Feature Implementation Plan
**Feature:** installation
**Overall Progress:** `80%`

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
- **C6 — Host-state reads go through seams,** tested in both directions. No test touches the real registry, `%LOCALAPPDATA%`, a real model file or a real Chrome; the conftest sentinels stay.
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
- Last completed step: **Phase 0 COMPLETE** — every spike run by the practitioner from a normal PowerShell (C7) on 2026-10-02 and recorded on its task by stage-0 executor leg i0-x12 (2026-10-02T22:46+10:00). Tasks 0.1, 0.2, 0.3, 0.4 and 0.5 are 🟩, and D-I1 / D-I2 are chosen 🟩. Earlier: the spike inputs (leg i0-x1), the peer pass stage-0.p1 (rounds 4–8, closed at the cap), and planning hardened by `/review-plan` and `/peer-loop` rounds 1–3.
- Current in-progress step (2026-10-03T02:11:26+10:00): **Phase 2 `/review-loop` CONVERGED at round 14** (no CRIT/HIGH/MED; round 14 Closed on composer suite 3, pytest 5559 passed / 20 skipped). Tasks 2.1–2.5 and 2.7 are 🟩 and 2.6 is 🟨 (the practitioner's dev-models copy is outstanding). The work sits in the worktree on top of Phase 1 committed `a7337a2`. See the leg i2-x3 brief below. (Phase 0 is committed as `9f43f8c`, Phase 1 as `a7337a2`.)
- Immediate next action (composer): the codex peer pass over the Phase 2 diff, then the Phase 2 commit on `installation-build`. Ask the practitioner for the Task 2.6 dev-models copy (the command is on Task 2.6), then re-run and report the real-ML legs' run/skip count. Keep `C:\scribe-spike` until the benchmark comparison (item 3 below) is done. No Phase 2 code draws a speed conclusion: Task 2.5 only measures and states its verdict line.
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
- Last plan sync: 2026-10-03T10:02:57+10:00
- Loop config: executor=claude-p model="claude-opus-5-5" effort=high profile=default; peer=codex model="gpt-6-astra" effort=medium; architect=off; cadence=every-phase; caps=review:3,peer:5; gates=executor; cap-raise=executor; high-auto=on; peer-max=12; notify=action-only; scope=all; autocommit=on; isolation=none; merge=off; perms=scoped; liveness=10; monitor-delivery=auto; verify=composer
- COMPOSER RUN-STATE: /execute-loop run iso `installation-20261002-113527-26e920`, started 2026-10-02T11:36+10:00; runkeys stage-0..stage-5 (stage-0 = Phase 0; stage-1..3 = Phases 1-3; stage-4 = Phase H; stage-5 = Phase P); probe logs `C:/Recording clinic software/.cursor/loops/stage-N-probe.log`. Phase 0 committed `9f43f8c` on `main`. **From Phase 1 on the run builds in the git WORKTREE `C:\scribe-build` (branch `installation-build`)** — practitioner decision 2026-10-02: the main checkout's `.venv` is the practitioner's EVERYDAY app (editable install) and stays on `main` until Phase P. The worktree has its own `.venv` copy (editable `.pth` → `C:\scribe-build\desktop\src`; `scribe-app.exe`/`scribe-host.exe` launchers regenerated for it; run mypy/pytest as `.venv/Scripts/python.exe -m …`). THIS worktree plan is authoritative; the main checkout's copy is stale until the branch merges, which happens only when the practitioner switches to the installed build. Phase 1 committed `a7337a2` (rounds 9–12), Phase 2 committed `7cfed96` (rounds 13–17) on `installation-build`. Phase 3 built and peer-converged (rounds 18–21), committed on `installation-build` by the composer at its close; its tasks stay 🟨 on their named practitioner/network/remote steps. Phase 2's Task 2.6 stays 🟨 until the practitioner fills `%LOCALAPPDATA%\ClinikoScribe-dev\models` and the composer re-runs the 11 real-ML legs. `stash@{0}` (the pre-worktree Phase 1 copy) is now redundant. `extension/key-dev.pem` is gitignored in the worktree; the main checkout holds an untracked copy — never commit it. Peer passes run as file-scoped codex slices (`.cursor/loops/inst-peer-run-wt.sh`). Phase H closed 2026-10-03 (rounds 22–30; H.1–H.5 🟩; H.6 hardened by a scoped /review-plan on 2026-10-03, ready for /execute), committed on `installation-build` by the composer. Next: the practitioner's open steps (Task 2.6 dev models, 3.3 manifest, 3.1 lock, 3.2/3.5 a real build, 3.6 pins/push/CI, the Inno licence), then Phase P (stage-5) with the practitioner.

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

- Round status: Open (0 pending). MED-001 was Applied by leg i3-x9 at 2026-10-03T10:02:57+10:00. It closes on the composer's suite after the practitioner regenerates the lock (until then the committed-lock test fails by name, as designed), and is proven by a green re-dispatched `Release` run.
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
- [ ] 🟨 **3.2 `packaging/scribe.spec`** (D1). Two windowed EXEs in one COLLECT. Collect `scribe_desktop` package data, apply Task 0.1's hidden imports and hooks, exclude the network Qt modules, no UPX, and add a version resource from D12.
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
- [ ] 🟨 **3.4 `packaging/scribe.iss`** (D1, D5, D6, D8, D-I1). It covers:
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
- [ ] 🟨 **3.5 `scripts/build-release.py`** (needs Tasks 3.1–3.4).
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
- [ ] 🟨 **3.8 `scripts/check-installed-sockets.py`.** Run from a normal terminal while the installed app transcribes and renders prose. It walks the `scribe-app.exe` and `scribe-host.exe` process trees with psutil (lessons: walk the tree) and reports any inet connection, text-free.
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
- [ ] 🟥 **H.6 The models root pinned for every test (C6)** — from round 27 PR-MED-022 (Include in plan); hardened in place by a scoped `/review-plan` on 2026-10-03 (its `[pending-hardening]` marker removed then; Executor tier inherited: entirely premium). Why: `install_layout.models_root()` is the ONE resolver every model path goes through — `benchmark.default_models_root()` → `speech.default_vad_model_path`, `transcription.default_whisper_model_dir`, `language_model.default_language_model_path`, `speaker_embedding.default_speaker_model_path`, each reading the attribute at call time, so one `monkeypatch.setattr(install_layout, "models_root", …)` reaches every path — yet the conftest pins only the channel and `is_frozen`, so a test that never redirects `LOCALAPPDATA` stats the host's real `%LOCALAPPDATA%\ClinikoScribe\models`: FULL on this computer (the everyday app's models until Phase P), EMPTY on CI; the suite is green on both today only because no test yet depends on the difference. The finding's sites: `MicrophoneScreen.refresh_model_status` (`ui/microphone.py` ~L335–342: `speaker_embedder_available()` then `model_file_report_lines()`), the `_main_window` helper (`test_ui_screens.py` ~L976) and the Learn-style poll (`test_ui_learn_style.py` ~L957) — all three reach the models root only through those two calls.
  1. **The pin.** In `desktop/tests/conftest.py`, one autouse function-scoped fixture `pinned_models_root(request, monkeypatch, tmp_path_factory) -> Path | None`: unless the test is exempt (step 2) it pins `install_layout.models_root` to `lambda of=None: root`, where `root = tmp_path_factory.mktemp("models")` — a fresh, EMPTY per-test folder OUTSIDE the test's own `tmp_path` (a test that lists or sweeps `tmp_path` as a sessions root sees nothing new); never pre-populated, so a presence check reads "absent" by default and a test that wants a model writes its own fixture there with `mkdir(parents=True)`. It returns the root (`None` when exempt). Ordering is pytest's own: autouse fixtures instantiate before requested ones of the same scope and share the one `monkeypatch`, so an explicit `real_ml_models` pin lands AFTER this one and wins; `on_real_ml_root` restores whatever was pinned when it ran (at import time the real function, inside a body this pin). `REAL_MODELS_ROOT`, `real_ml_models_root()` and the child processes' own pins (`test_integration_no_sockets.py`'s `_CHILD` sources, checked by `_CHILD_PIN`) are untouched. Docstring in the register of `_production_channel`'s, naming PR-MED-022 and C6.
  2. **The exemption: a registered marker, applied per class.** `@pytest.mark.real_models_root` registered under `[tool.pytest.ini_options] markers` in `desktop/pyproject.toml` (the suite's first custom marker; `--strict-markers` is NOT added — registration alone keeps the run warning-free); the fixture checks `request.node.get_closest_marker("real_models_root")` and then pins nothing. A MODULE-level opt-out is rejected: both exempt modules hold many tests that must stay pinned. Exempt — only the tests OF the resolver, each driving `LOCALAPPDATA` or the install root itself: `test_install_layout.py::TestModelsRoot` (~L241) and the `_builders()` consumer test (~L376, which asserts the `"models"` builder under the channel folder); `test_frozen_runtime.py::TestRealMlModelsRoot` (~L1081 — its `test_a_gate_probes_under_the_dev_root_then_the_pin_returns` asserts the REAL production answer after the restore, and its `test_the_body_fixture_pins_every_model_path` keeps proving the dev-root override); `test_language_model_runtime.py` `test_default_model_path_under_the_models_root` (~L94) and `test_localappdata_unset_reports_unavailable` (~L738 — the unset-`LOCALAPPDATA` contract, hollow under a pin); `test_speaker_embedding.py` `test_default_model_path_under_the_models_root` (~L98). Nothing else: the suite run in step 5 is the enumeration — a failure outside this list is either a resolver test to mark or a fixture builder to migrate (step 3), never a reason to widen the marker to a module or a file.
  3. **Fixture builders follow the pin, not `LOCALAPPDATA`.** The tests that hand-build model files under `<tmp LOCALAPPDATA>/ClinikoScribe/models` build under `install_layout.models_root()` (the pin) instead: `test_transcription.py` `_fake_snapshot` (~L994) and its seven Step-13 call sites (~L1015–1046, ~L1173); `test_ui_models.py` `_fake_whisper_snapshot` (~L357) and the two `vad_dir` lines (~L404, ~L480) in `TestModelReport`. Their `setenv("LOCALAPPDATA", …)` lines stay only where something else in the test still needs the data root. These tests are NOT marked: they test the resolver's consumers; the `LOCALAPPDATA` → `ClinikoScribe\models` mapping is the exempt tests' business. After this step no test outside step 2's set spells `"ClinikoScribe" / "models"` (grep).
  4. **Tripwires** (in `test_frozen_runtime.py` beside `TestRealMlModelsRoot`): (a) an UNMARKED test — `install_layout.models_root()` and `benchmark.default_models_root()` both equal the `pinned_models_root` fixture's value, which is under `tmp_path_factory.getbasetemp()` and empty, and `default_vad_model_path()`, `default_whisper_model_dir()`, `default_language_model_path()`, `default_speaker_model_path()` all resolve under it; (b) a MARKED class — `install_layout.models_root is REAL_MODELS_ROOT` and the fixture returned `None`; (c) an UNMARKED test with `real_ml_models` — `install_layout.models_root()` equals `real_ml_models_root()` (the dev root beats the pin; with Task 2.6's models in place the real-ML legs RUN, so a broken override fails them loudly rather than skipping). (d) the named sites — one test in `test_ui_screens.py` beside the PR-MED-022 site (~L727) builds `MicrophoneScreen(…, benchmark_runner=list, profile_root=tmp_path)` with NO presence stub, calls `refresh_model_status()` under a `pathlib.Path` spy on `NETWORK_IO_METHODS` (modelled on `forbid_network_io`; a small `record_path_io(monkeypatch) -> list[Path]` helper in conftest if that reads better) and asserts every probed path is under the pinned root or `tmp_path`; its docstring says why one site proves the class (the other two reach the models only through the same two calls).
  5. **Suite and docs.** `ruff check . && mypy && pytest` in `desktop/`: expect 5856 + the new tests passed / 9 skipped (the directory-symlink variants only — Task 2.6 is done, the dev root is filled and the real-ML legs run; a changed skip count needs a reason, Validation). Then C9's class reconciliation: the sentence beside the `WindowsLayer` sentinel in `docs/security/threat-model.md` (~L2871, "tests never reach the real one (a sentinel)") names the models-root pin as the second conftest sentinel; `AGENTS.md`'s installation Subsystem bullet ("every host-state read goes through a seam tested both ways (C6)") gains "and the conftest pins every test's models root to an empty temporary folder (`real_models_root` marks the resolver's own tests)"; `docs/lessons.md`'s 2026-09-24 host-file lesson (~L110) gains one recurrence line (PR-MED-022: the model-status poll read the real models folder; closed for the class by the pin, not per test); this plan's C6 names the pin among "the conftest sentinels".
  - Rejected (scoped `/review-plan`, 2026-10-03): (i) a pin that honours a redirected `LOCALAPPDATA` (calls the real function when the variable differs from the host's) — magic that blurs tripwire (a) and still needs the marker for the frozen cases; (ii) `setenv("LOCALAPPDATA", tmp)` for every test — redirects every data root, far beyond PR-MED-022's class; (iii) a per-test copy of the original function — `REAL_MODELS_ROOT` already serves that, and the exempt tests need the live attribute.
  - Risk, named: on this computer the production models folder is full, so a test that passes today only because a real model exists would FAIL under the pin — CI run 37081519723 was green with that folder empty, so none is known; if one appears it writes its own fixture under the pin (lessons 2026-09-24), never earns the marker.
  - Done when: the fixture and the registered marker are in place; the exempt set is exactly step 2's; step 3's builders use the pin and the grep finds no other `"ClinikoScribe" / "models"`; tripwires (a)–(d) pass; the full desktop suite is green at 9 skipped; the three docs and C6 name the pin; then `/review-loop` over the diff and one codex confirmation slice (conftest, pyproject, the five test files, the three docs).

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

  - **Prepared 2026-10-03 (composer, local commit, not pushed):** version 0.1.1 in every pinned place (`desktop/pyproject.toml`, `__version__`, `extension/src/manifest.ts`, `package.json` and both `package-lock.json` copies; `test_the_version_is_the_same_everywhere` holds), together with the CI timing-test bound (AGENTS.md Known Issues). After P.1 passes: push, run Release, verify the attestation, record the row in `docs/release/pilot-builds.md`, then run steps 1–3.

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
