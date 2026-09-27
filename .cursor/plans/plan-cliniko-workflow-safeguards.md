# Feature Implementation Plan
**Feature:** cliniko-workflow-safeguards
**Overall Progress:** `0%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: None
- Follow-up plans: None

## Goal
Build PLAN.md Phase 5 (workflow safeguards) in full, before Phase 4. Recording starts only from an open Cliniko treatment note, and the note is verified with Cliniko's API. The encounter is locked to the session at Start behind a consent tick. A Chrome side panel carries consent and every control, and a red or amber frame marks the Cliniko page while recording or paused. Any patient, note, account, tab or login change pauses immediately, and a full-page block asks Finish previous / Resume previous / Discard previous. A hotkey pauses and resumes; a spoken phrase pauses. A phrase-rule warning flags a likely new consultation. Write-back is refused whenever the context cannot be verified. Back-to-back consultations work: each finished note waits in an Unreviewed list, with a reminder when its note is reopened. This plan ALSO brings in the clinic API keys and a read-only Cliniko client, so the app's "no network" claim becomes "only to Cliniko's API". Writing the draft into Cliniko is the next plan (PLAN.md Phase 4).

## Planning Extraction Summary
Source: `/explore` scratch `.cursor/plans/explore-cliniko-integration.md` (2026-09-27, code baseline `main @ 33bd35e`), the Phase 5 half, plus the `/create-plan` session's decisions (2026-09-27). The Phase 4 half of that scratch is carried below under Deferred as the next plan's input.

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Opus 5.5; executor Opus-class via `/execute-loop`; no planner/executor tier gap

### Agreed Scope (Build Now)
- A read-only Cliniko API client inside `scribe-app`, confined to one module and to `api.<shard>.cliniko.com`, plus a practitioner-run read-only feasibility check built on it.
- Two clinic API keys, entered in a new desktop Clinics tab, stored in Windows Credential Manager and validated against Cliniko: practitioner role, practitioner record, subdomain, and a shard that matches the clinic host.
- The offline-contract rewrite, as a class: ruff bans, docstrings and the security docs go from "no network sockets" to "no connection except Cliniko's API, and none at startup or idle".
- A typed `EncounterContext` and `ConsentAttestation`, verified against Cliniko, locked at Start, and persisted encrypted before the first audio chunk.
- The consent tick required before EVERY recording, on the side panel and on the kept desktop Start ("Not linked to a Cliniko note").
- The host↔app named pipe with the Phase 2 hardening list; protocol v2 (`context`, `command`, `state`); a two-way native-host relay; and an app-side state publisher.
- The pause rule, owned by the app: the bound tab leaves the note, the bound tab closes, Chrome disconnects, or the active tab shows another Cliniko patient or note. Then the resolution block: Finish previous / Resume previous / Discard previous.
- Back-to-back consultations: patient B's Start unlocks once A's processing tail finishes; A joins an "Unreviewed notes" list and reopens straight into review; the side panel reminds when A's note is reopened; a warning fires before any unreviewed note reaches the 24 h limit.
- The Chrome UI: the side panel, the red/amber page frame, the full-page block, the icon badge, and a URL-only page script with a clinic-host allow-list delivered by the app.
- Hands-free controls: a Windows hotkey pauses and resumes; the spoken phrase "scribe pause" only pauses. Plus phrase-rule new-consultation warnings (warning only).
- A write-back guard predicate that the Phase 4 plan consumes, and the cross-patient adversarial test matrix.
- The copy-to-Cliniko flag flip and the shipping-gate reframing, as one task confirmed with the practitioner when it runs (Deferral gate: Fix now → blocked by the permission classifier → recorded as a task, 2026-09-27).
- Security, retention, design-system and run-step docs; the live smoke on both clinics; a Hardening stage.
- Added by the `/review-plan` hardening pass (2026-09-27):
  - Start is bound to the exact context the practitioner saw.
  - The consent record is saved on EVERY start (`encounter.enc`).
  - Refusals travel in `state`, never `error`.
  - Pause on sleep; a linked session cannot resume without Chrome reporting its note.
  - Automatic re-injection of the page script after an extension reload.
  - Page-script and pipe input hardening, and client TLS hardening.
  - A two-step Discard confirmation.
  - The desktop Session screen shows the linked-session display.
  - The Unreviewed list is a Recovery-screen section.

### Deferred — Actionable Later
- **PLAN.md Phase 4 — writing the draft into the open Cliniko note (next plan)**
  - Why deferred: practitioner decision 2026-09-27 — two plans in order. The write consumes this plan's verified context, keys and client.
  - Intended future outcome:
    - `PATCH /treatment_notes/<note_id>` fills the draft the practitioner opened. Before every write the note is re-read, and the write is refused if the note is final or already holds typed text.
    - Each template profile is bound per clinic to a Cliniko template id, with a section/question name match.
    - A write ledger and a reconcile step run before any retry.
    - The session completes automatically after a confirmed write (PLAN flow step 10).
    - The scratch's Phase 4 Accepted Assumptions carry over: the "typed text" definition, ledger/reconcile, rendering, the 24 h retry window and ledger encryption.
  - Relevant files / subsystems: `cliniko_client.py` (this plan; the write method lands there), `encounter.py`'s write-back guard (this plan), `session.py`, `session_store.py`, `note_config.py`, `ui/note.py`, `ui/transcript.py`, `docs/security/*`.
  - Dependencies / prerequisites: this plan closed. The Phase 4 plan's first task is the practitioner's test write, which was moved out of this plan's feasibility check (2026-09-27).
  - Recommended next action: `/create-plan` for Phase 4 from `.cursor/plans/explore-cliniko-integration.md` once this plan closes.
  - Risk if deferred: blocked-work: notes still reach Cliniko only by copy/paste until Phase 4 lands.
  - Revisit by: this plan's close
- **Durable consent evidence**
  - Why deferred: the recording-consent record lives in `encounter.enc` and is destroyed with the session (about 24 h). A lasting record belongs to PLAN.md Phase 6's minimal audit record (consent timestamp, user, clinic, booking/note ids, write and deletion results). Deferral gate, practitioner 2026-09-27.
  - Intended future outcome: a text-free audit record that outlives the session.
  - Relevant files / subsystems: `encounter.py` (`ConsentAttestation`), `docs/security/retention-schedule.md`.
  - Dependencies / prerequisites: a PLAN.md Phase 6 plan.
  - Recommended next action: carry into the Phase 6 plan.
  - Risk if deferred: correctness: until Phase 6, durable consent evidence rests on Cliniko and the practitioner's own process.
  - Revisit by: PLAN.md Phase 6 planning
- **Three-or-more-speaker labelling and diarization tuning**
  - Why deferred: unchanged from `plan-phase3a-note-pipeline.md`; blocked on the shared recording set.
  - Intended future outcome: see that plan.
  - Relevant files / subsystems: `speaker*.py`, `transcription.py`.
  - Dependencies / prerequisites: practitioner-profile Task 6.1 (the shared recording set).
  - Recommended next action: none here.
  - Risk if deferred: ux-degradation: a third voice merges into another speaker label.
  - Revisit by: Phase 3 validation set construction

### Excluded — Revisit Only If Needed
- **Starting a recording from the calendar or any page other than an open treatment note**
  - Why excluded: the calendar URL carries no patient or booking id, and DOM reading is fragile (practitioner, 2026-09-27).
  - When to revisit: if starting from an open note proves impractical in clinic.
  - Relevant files / subsystems: `extension/src/*`.
  - Recommended next action (if any): none.
- **Creating a second note with `POST /treatment_notes`**
  - Why excluded: Cliniko creates an empty draft when the practitioner opens treatment notes, and filling it gives exactly one note per consultation (practitioner, 2026-09-27).
  - When to revisit: if the Phase 4 test write shows the auto-created draft cannot be filled.
  - Relevant files / subsystems: `cliniko_client.py`.
  - Recommended next action (if any): none.
- **A Cliniko free-trial account; a test-patient write guard**
  - Why excluded: the practitioner declined both. Testing uses their own accounts, and they finalise every draft (2026-09-27).
  - When to revisit: commercialisation, i.e. when the practitioner is no longer the sole finaliser.
  - Relevant files / subsystems: none.
  - Recommended next action (if any): none.
- **A separate network helper process**
  - Why excluded: practitioner, 2026-09-27. They accepted that the key is held in `scribe-app`'s memory and that no future per-program firewall rule can block `scribe-app` outright.
  - When to revisit: before an independent privacy/security review ahead of commercialisation.
  - Relevant files / subsystems: `cliniko_client.py`.
  - Recommended next action (if any): none.
- **True overlap of consultations (B recording while A is still processing)**
  - Why excluded: holding two sessions at once touches key custody, the area that took the most review rounds (`docs/lessons.md` 2026-08-12). A's tail after Finish is short because live transcription does most of the work (practitioner, 2026-09-27).
  - When to revisit: if Task 5.3's measured tail is routinely long.
  - Relevant files / subsystems: `session.py` (the single-active-session invariant).
  - Recommended next action (if any): none.
- **Voice or hotkey Finish/Discard; reading the Cliniko page DOM; a desktop appointment picker; automatic finalisation**
  - Why excluded: practitioner decisions 2026-09-27 (pause only by voice or hotkey; names come from the API; the open-note design supersedes the picker), and PLAN.md (never finalise).
  - When to revisit: never for finalisation; the others only on a new practitioner decision.
  - Relevant files / subsystems: —
  - Recommended next action (if any): none.

### Accepted Assumptions — Revalidate Later
- **Clicking "treatment notes" from an appointment creates a new, empty draft and opens it (per the practitioner; not probed through the API)**
  - Why accepted for now: the practitioner observed it directly (2026-09-27).
  - Risk if assumption becomes false: the open note may be an older draft, or not linked to the booking. Verification (Task 3.2) still refuses a final note, and the booking is optional.
  - Trigger for revisit: Task P.1's output.
  - Recommended next action: record what P.1 shows.
- **Cliniko API details are per docs.api.cliniko.com and unverified live.** Covers: the roles that may call `/settings/public`; whether the auto-created draft carries booking and template links; whether the note's practitioner link equals the key user's practitioner record.
  - Why accepted for now: Task P.1 measures them first.
  - Risk if assumption becomes false: key validation or note verification needs another route. D10's typed-subdomain fallback covers a refused `/settings/public`.
  - Trigger for revisit: Task P.1.
  - Recommended next action: P.1.
- **The processing tail after Finish is short (seconds) when live transcription ran**
  - Why accepted for now: the live transcriber transcribes during recording; only the tail and the speaker pass remain.
  - Risk if assumption becomes false: B waits noticeably. Revisit true overlap (Excluded).
  - Trigger for revisit: Task 5.3's measurement and the Task P.2 smoke.
  - Recommended next action: measure in 5.3.
- **Cliniko changes the page URL without a full page load, and `tabs.onUpdated` reports every such change on a host-permissioned tab**
  - Why accepted for now: that is Chrome's documented behaviour for history-state changes.
  - Risk if assumption becomes false: a missed change means a missed pause. Task 6.3's page script sends `location.href` changes as a backstop, with the background staying the single `context` reporter.
  - Trigger for revisit: Task P.2.
  - Recommended next action: include the backstop.
- **Accepted residue — one Chrome profile** (deferral gate, practitioner 2026-09-27)
  - Why accepted for now: only one Chrome profile can link to the app at a time. A second profile's panel shows "Another Chrome profile is connected".
  - Risk if assumption becomes false: a practitioner using two profiles is refused, never silently mixed.
  - Trigger for revisit: a multi-profile need.
  - Recommended next action: document it in threat-model and AGENTS.md (Task 8.1).
- **Accepted residue — Windows-level key exposure** (deferral gate, practitioner 2026-09-27)
  - Why accepted for now: Windows clipboard history and cloud clipboard sync keep a pasted key, and the Windows certificate store trusts antivirus or corporate inspection roots.
  - Risk if assumption becomes false: the key lingers in clipboard history, and inspecting software sees the API traffic.
  - Trigger for revisit: commercialisation or an independent security review.
  - Recommended next action: the Clinics tab advises clearing clipboard history after pasting (Task 2.2); the threat model states both residues (Task 1.2).
- **Accepted residue — page-level limits** (deferral gate, practitioner 2026-09-27)
  - Why accepted for now: several limits cannot be closed from the page:
    - Cliniko's page can hide the frame, so the frame is a cue, not a control.
    - An in-page session-expiry modal does not change the URL, so it cannot trigger a pause.
    - The next patient's speech before their note is opened (the greeting at the door), and the report→pause latency, land in the previous recording.
  - Risk if assumption becomes false: a few seconds of the next patient can reach the previous recording. Write-back still requires a verified note, and no session is ever re-bound.
  - Trigger for revisit: Task P.2 or a later hardening pass.
  - Recommended next action: state all three in the threat model (Task 8.1).

### Key Design Decisions
- **All of PLAN.md Phase 5 before Phase 4, as two plans in order** (practitioner, 2026-09-27).
  - Why: Phase 4's draft write needs a verified encounter.
  - Alternatives rejected: a desktop appointment picker; Phase 5 context-only slices; one combined plan.
  - Still applies to follow-up work: Yes.
- **Recording starts only from an open treatment note, and the Phase 4 draft fills THAT note** (practitioner, 2026-09-27).
  - Why: the note URL `/patients/<patient_id>/treatment_notes/<note_id>/edit` gives both ids, and one note per consultation holds by construction.
  - Alternatives rejected: calendar Start; POST of a second note.
  - Still applies to follow-up work: Yes.
- **UI: a Chrome side panel, a red/amber page frame and a full-page block on patient change** (practitioner, 2026-09-27, chosen from four mockups). The full design is in `Design Decisions` D1.
  - Alternatives rejected: a strip inside Cliniko's layout; a corner pill alone; desktop-led.
  - Still applies to follow-up work: Yes.
- **Clinic keys and read-only Cliniko verification live in this plan; the write lives in Phase 4** (practitioner, 2026-09-27).
  - Alternatives rejected: Phase 5 trusting the URL alone.
  - Still applies to follow-up work: Yes.
- **Cliniko HTTPS runs inside `scribe-app`, in one module, on the Python standard library `http.client`** (practitioner, 2026-09-27; `http.client` over `urllib` per the practicality lens).
  - Why: `urllib.request` follows cross-host redirects and honours `HTTPS_PROXY`, and either would bypass the host pin.
  - Alternatives rejected: a separate helper process; pinned `httpx`.
  - Still applies to follow-up work: Yes.
- **The practitioner's own Cliniko accounts are used, with no guard; the shipping gate becomes a quality measurement** (practitioner, 2026-09-27).
  - Still applies to follow-up work: Yes.
- **Desktop Start is kept, marked "Not linked to a Cliniko note"**, gains the same consent tick, and can never be written to Cliniko (copy only) (practitioner, 2026-09-27).
  - Still applies to follow-up work: Yes.
- **Pause rule: Cliniko changes only.** Switching to a non-Cliniko tab does not pause (practitioner, 2026-09-27).
  - Still applies to follow-up work: Yes.
- **Hands-free: the hotkey pauses and resumes; speech only pauses; Finish and Discard always need a click. New-consultation warnings come from phrase rules** (practitioner, 2026-09-27).
  - Still applies to follow-up work: Yes.
- **Patient name and appointment time come from the API**, are relayed to the panel and are held in Chrome memory only; the page DOM is never read (practitioner, 2026-09-27).
  - Still applies to follow-up work: Yes.
- **Cliniko unreachable at Start: recording goes ahead, marked "Not verified with Cliniko", and write-back is blocked until the note is verified** (practitioner, 2026-09-27).
  - Alternatives rejected: blocking Start.
  - Still applies to follow-up work: Yes (the Phase 4 write re-verifies).
- **Back-to-back: B starts after A's tail; A waits in an Unreviewed list. The reminder appears on reopening A's note, and there is a warning 2 h before the 24 h limit** (practitioner, 2026-09-27).
  - Alternatives rejected: true overlap (Excluded); forcing review before B.
  - Still applies to follow-up work: Yes.
- **The feasibility check is read-only; the test write moves to the Phase 4 plan** (practitioner, 2026-09-27).
  - Still applies to follow-up work: Yes.
- **Sleep pauses; locking the screen does not** (practitioner, 2026-09-27, hardening pass).
  - Alternatives rejected: pausing on both.
  - Still applies to follow-up work: Yes.
- **After an extension reload or update, the page script is re-injected automatically**, using the `scripting` permission limited to Cliniko hosts (practitioner, 2026-09-27).
  - Alternatives rejected: asking the practitioner to reload the tab.
  - Still applies to follow-up work: Yes.
- **One plan, built phase by phase** (practitioner, 2026-09-27).
  - Alternatives rejected: splitting into keys/client/encounter and pipe/Chrome plans.
  - Still applies to follow-up work: Yes.

## Key Findings

### Files / Symbols Involved
Verified at `main @ 33bd35e` (2026-09-27). Line numbers drift; the symbols are the anchors.

**Session and session store**
- `desktop/src/scribe_desktop/session.py`
  - `SessionState` (`:82-93`): all nine PLAN states. `ACTIVE_STATES` includes PROCESSING (`:97-99`).
  - `RecordingSession` (`:156-187`): frozen; `encounter_context: str | None` (`:170`, max_length 256, always None today).
  - `SessionController.start(device_id)` (`:419`): builds `RecordingSession(key_reference="key.dpapi")` at `:443`. The single-active invariant is at `:432-436`, and a queued session is retired at `:437-442`.
  - `pause` (`:490`), `resume` (`:513`), `finish` (`:524`), `claim_live_transcriber` (`:569`), `transcribe` (`:596`), `complete*` (`:683-785`), `discard` (`:787`).
  - `custody_protected_ids` (`:1044-1063`). The concurrency contract forbids non-GUI-thread custody callers (`:317-332`).
- `session_store.py`
  - `write_note` (`:774-848`) is the encrypted-sidecar precedent for `encounter.enc`; it uses no AAD, so `encounter.enc` must take a distinct AAD.
  - `complete_session` (`:674-713`), `discard_session` (`:716-724`, key first, then `rmtree`), `sweep_sessions` (`:948-1006`), `read_note` (`:851`, test-only caller today).
- `app.py`
  - `sweep_protected_ids` (`:115-136`), `apply_offline_env`/`assert_offline_env` at startup (`:143-144`), the 15-minute sweep timer (`:175-183`).
  - The named-mutex single instance (`:68`), whose same-user residue wording is at `:76-77`.

**Desktop UI**
- `ui/models.py`
  - `SessionControllerLike.start` (`:161`).
  - `COPY_TO_CLINIKO_ENABLED` (`:446`, `False`; exported at `:2400`).
  - `list_recoverable_sessions` (`:283`, plaintext header only).
  - `build_live_transcriber` (`:2228`), `LIVE_FALLBACK_STATUS` (`:2211-2222`).
- `ui/main_window.py`
  - The live transcriber factory is wired at `:212`, `_build_live_transcriber` at `:252-256`, `_on_session_started` at `:358-381`, and `_on_draft_ready` at `:449-460` (reads the copy flag at call time, `:453`).
- `ui/session_screen.py`
  - `on_start` (`:171-180`, needs `_device_provider`), `on_resume` (`:192`), `on_finish` → `_begin_transcription` (`:200-256`, drives PROCESSING→QUEUED and emits `transcript_ready`).
  - The `_watch_state` 500 ms `QTimer` poll (`:128`).
- `ui/recovery.py`: `RecoveryScreen` (`:43`) with `_describe` (`:30-40`, id and time only) and `refresh` (`:122`). It offers only "Resume processing" and Discard (`:1-4`).
- `ui/transcript.py`: the save/complete path (`:684-699`, `:771-792`), and the worker→signal marshalling pattern (`:278-282`).
- `ui/note.py`: `begin_review` copy default (`:510`), `_copy_ready`/`_apply_copy_binding` (`:1996-2026`), module docstring (`:122`).

**Transcription, credentials, logging and config**
- `transcription.py`
  - `LiveSegmenter` (`:1450`), `LiveTranscriber` (`:1764`), `LiveFailureKind.FELL_BEHIND` (`:1424`).
  - Windows are ≤30 s and close on a 3 s gap (`:211`, `:216`).
  - `on_window` has a single consumer and runs on the worker thread (`:1779`, `:1793`).
- `secure_storage.py`: `SecureStorageProvider.store/retrieve/delete(clinic_id, secret_name[, value])` (`:47-57`), keyring service `ClinikoScribe/<clinic_id>`.
- `logging_setup.py`: the tripwire drops `encounter_context` (`:82-86`). Its scanned set is derived from `LOG_FORMAT` (lessons 2026-08-10).
- `note_config.py`: `default_config_root` (`:910-914`, `%LOCALAPPDATA%\ClinikoScribe\config\`).

**Native messaging and protocol**
- `native_host.py`
  - `HostSession.handle` (`:81-122`) handles only hello/ping; unknown types → error + exit.
  - `run_host` (`:154-196`, single-threaded blocking stdin), `verify_origin` (`:48-59`).
- `protocol.py`: `MessageType` Literal (`:26`), `Envelope` (`:41`, untyped `payload` dict), `make_envelope`/`make_error` (`:91-112`).
- `framing.py`: `read_frame`/`write_frame` over `BinaryIO` (`:62`, `:95`).
- `protocol/fixtures/`: `meta.json` (version 1, floor 1, 1 MiB frame); `valid/` has 5 messages; `invalid/` has 11 cases.
- `extension/src/`
  - `manifest.ts` (`:13-14`: `nativeMessaging`, `alarms`, `host_permissions: ["https://*.cliniko.com/*"]`; no content scripts; no popup).
  - `background.ts`, `connection.ts` (backoff 0.5/1/2/5 min at `:22`), `protocol.ts` (the hand-written mirror).
  - Tests: `scaffold.test.ts`, `protocol.test.ts`, `connection.test.ts`.
- Build: `extension/package.json` (Vitest 4.1.10, no DOM environment). `extension/vite.config.ts` uses crxjs 2.7.1, which supports `side_panel.default_path`.

**Tests and lint config**
- `desktop/tests/test_integration_no_sockets.py`: psutil `net_connections` must equal `[]` (`:141-143`) across child processes. The legs are the host handshake with no app (`:157`), the `scribe-app` idle poll (`:212-255`), capture/live/real Whisper, prose, crash recovery and the socket-stub child (`:1399`). There is no allow-list. The 4 child scripts call `start(0)` (`:478/672/856/1201`).
- `desktop/pyproject.toml:90-95`: ruff `TID251` bans `socket`, `http`, `urllib.request`, `PySide6.QtNetwork`. `ssl` is not banned. pywin32 is a dependency at `:19`, with a mypy override at `:107-115`.

### Codebase Integration Notes
**Rules for touching the code**
- **The app is the single owner of state and pause decisions.** Chrome (page script, background, panel) reports facts and renders the app's `state` push; it never infers "recording". On port or pipe loss the panel shows "disconnected", and the app pauses when it sees the pipe close.
- **Panel and hotkey commands go through the SessionScreen slots, never straight to the controller.** `on_finish` starts the transcription `TaskThread`. A direct `controller.finish()` would leave the session stuck in PROCESSING and skip `session_discarded` and the live-view clear.
- **Pipe, live-window and hotkey events reach the GUI thread only as queued Qt signals** (the `ui/transcript.py:278-282` pattern). The controller forbids non-GUI custody callers.
- **Decrypt `encounter.enc` only on checkout, or once per session at app start for the reminder index (D6).** Never in `list_recoverable_sessions` or on the 15-minute sweep: that is the periodic-decrypt class (`docs/lessons.md` 2026-09-18).
- **No Cliniko call at startup or idle**, only on a context report, a Clinics-tab Validate, or an Unreviewed-list open. This keeps `test_scribe_app_process_has_no_sockets` at zero.
- **Tests never depend on host state** (lessons 2026-09-24). The Cliniko transport, the pipe, the hotkey and Credential Manager are injected in unit tests.
- **Security-doc claims are control claims** (lessons 2026-08-14). Rewrite every "no network" sibling as a class (grep, not the cited line), and budget a cross-family peer pass.
- **MSIX virtualisation** (lessons 2026-07-28): Credential Manager entries, `clinics.json` in `%LOCALAPPDATA%` and pipe reachability from a user-launched Chrome are verified only by the practitioner's live launch (Task P.2).
- **A message describing a deferred outcome names the control that commits it** (lessons 2026-09-17). For example, "Unreviewed note — Open for review", "Write-back blocked until verified".
- **A codex peer on this repo must not create files in the repo, and should not run pytest** (lessons 2026-08-04). Slice any whole-surface codex round by file group (lessons 2026-09-25).

**Hardening-pass code facts (2026-09-27, verified; each shapes a task)**
- **The extension drops the connection on ANY `error` and on any unexpected type** (`extension/src/connection.ts:136-139`, the `fail()` path at `:143`). Backoff is then 0.5/1/2/5 min (`:22`). A refusal sent as `error` would disconnect, the app would see the pipe close, and the recording would pause (D2).
- **`SessionController.pause()` requires RECORDING** (`session.py:495` `_require_state`) and raises otherwise (D5's `pause_for`).
- **`start()` is refused while the generation lease is held** (`session.py:430` `_refuse_while_generating`). The lease spans the whole Note review and is released only on Save, Cancel or Abandon (`ui/main_window.py:476-487`), which is why D1 has the "Save or cancel <A>'s note review" state.
- **A recovered checkout cannot generate or save a note.**
  - `MainWindow` passes `can_generate=False` on the recovered path (`ui/main_window.py:399-406`), and `with_generation_custody` serves only the live QUEUED session (`session.py:~1100-1127`).
  - Recovery's "Resume processing" re-transcribes (`transcription.py:1342` `recover_session_transcription`) and unlinks `note.enc` (`ui/recovery.py:273`).
  - The read path exists: `unwrap_key_from_file` + `transcription.read_transcript` (`transcription.py:1089`).
  - A recovered checkout stays checked out until restart (`ui/main_window.py:348-354`). That drives the Task 5.4 `[decision]`.
- **`SessionScreen.on_discard` discards immediately, with no confirmation** (`ui/session_screen.py:217-224`), which is why D5 adds the two-step confirm.
- **A GUI-thread live-window signal already exists:** `TranscriptScreen.live_window` (`ui/transcript.py:96`, emitted at `:278`). `LiveTranscriber.on_window` runs under the worker's post lock (`transcription.py:1779`), so do not tee it. `LiveTranscriber.failed_reason` (`:1855`) has no public accessor through the controller.
- **The sweep's timestamp derivation is** `_session_created_at` / `earliest_trusted_timestamp` (`session_store.py:885-913`). The expiry warning must reuse it.
- **`start()` ordering:** `crypto` exists at `session.py:445`. `encounter.enc` goes between `wrap_key_to_file` (`:453`) and `SessionChunkStore.create` (`:454`) via `atomic_write_bytes` (`session_store.py:510`), and the failure cleanup at `:482` covers it.
- **Test sites that change with `start()` and `RecordingSession`:**
  - the 59 `start(0)` sites, including the 4 child-script strings in `test_integration_no_sockets.py:478/672/856/1201` (subprocess code: no conftest helper);
  - `start(99)` at `test_live_session.py:750` and `test_session_machine.py:310`;
  - `FakeController` at `test_ui_screens.py:163-211`;
  - `RecordingSession(encounter_context="patient-123")` at `test_session_types.py:178` (the PR-MED-001 tripwire test) and ~10 bare `RecordingSession()` there;
  - `model_construct(encounter_context=None)` at `test_ui_screens.py:2711`.
- **`RecoverableSessionInfo` (`ui/models.py:275`) has no has-transcript or has-context field.** Its list tests are `test_ui_models.py:184-265`.
- **The mypy overrides (`desktop/pyproject.toml:107-115`) lack `win32event`, `win32gui` and `win32process`.**
- **`ConnectionManager.BADGES` (OK/OFF/ERR, `connection.ts:43-48`) is pinned in `connection.test.ts`.** D1's badge replaces it.
- **An open `connectNative` port keeps the MV3 service worker alive** (`connection.ts:3-4`). Reload, update and crash are the risk, not idle suspension. Manifest content scripts are NOT re-injected into open tabs after a reload.
- **`ssl.create_default_context()` honours `SSLKEYLOGFILE`**, and nothing in `desktop/src` removes it today.

**Shared-helpers inventory (reuse across phases, do not re-invent)**
- `cliniko_client.ClinikoClient` + `Transport` seam (Task 1.1).
- `clinics.ClinicRegistry` (Tasks 2.1a, 2.1b).
- `encounter.EncounterContext` / `ConsentAttestation` / `verify_note_context` / `writeback_context` (Tasks 3.1, 3.2, 3.5).
- `protocol.py` / `protocol.ts` v2 payload models (Task 4.1).
- `pipe_server.PipeServer` (Task 4.2).
- The app-side `ContextEvaluator` and `StatePublisher` (Tasks 4.5, 5.1).
- The existing `SecureStorageProvider`, `framing.read_frame/write_frame`, the sweep and recovery checkout, and the logging tripwire.

### External / API Findings
Sources: docs.api.cliniko.com and its OpenAPI bundle; GitHub `redguava/cliniko-api` is archived (LEGACY). Detail is in the scratch's External / API findings.

**Authentication and limits**
- HTTP Basic auth: the API key is the username, the password is empty, over TLS 1.2+.
- A key's `-auN` suffix selects `https://api.auN.cliniko.com/v1`; a key with no suffix uses au1. Documented shards: au1–au5, ca1, uk1–uk3, us1, eu1.
- A `User-Agent: <app name> (<contact email>)` header is required; requests without it may be blocked.
- Keys are per user and carry that user's permissions.
- Rate limit: 200 requests/min per user; a 429 carries `X-RateLimit-Reset`. A 422 body is `{"message","errors":{field: msg}}`.

**Endpoints used in this plan (reads only)**
- `GET /user`: `id`, `role`, `active`.
- `GET /practitioners?q[]=user_id:=<id>`.
- `GET /settings/public`: `account.subdomain`. Which roles may call it is UNCONFIRMED.
- `GET /treatment_notes/<id>`: `draft`, `finalized_at`, and links for `patient`, `practitioner`, `booking`, `treatment_note_template`.
- `GET /patients/<id>`: the display name.
- `GET /bookings/<id>` or `/individual_appointments/<id>`: `starts_at` in UTC.

**Web app URLs** (practitioner-supplied; ids are placeholders — never commit real ids)
- Host: `https://<subdomain>.<shard>.cliniko.com`. One clinic is on `au2`, the same shard as its key suffix.
- The calendar is `/appointments?calendar_start_date=<date>`; clicking a patient there does NOT change the URL.
- The note page is `/patients/<patient_id>/treatment_notes/<note_id>/edit?page=1`.

**Chrome MV3**
- `host_permissions` for `https://*.cliniko.com/*` already exposes `tab.url` for Cliniko tabs (no `tabs` permission needed). `tabs.onUpdated` reports history-state URL changes.
- A global side panel uses `side_panel.default_path` plus `setPanelBehavior({openPanelOnActionClick: true})`.
- `sidePanel.open()` requires a user gesture (Task 6.4 spike).

**Windows**
- pywin32 312 provides `CreateNamedPipe`, `ConnectNamedPipe`, `WaitNamedPipe`, `GetNamedPipeServerProcessId`/`SessionId`, `PIPE_REJECT_REMOTE_CLIENTS`, SDDL→security descriptor, and `win32gui.RegisterHotKey`.
- It lacks the `FILE_FLAG_FIRST_PIPE_INSTANCE` constant (use `0x00080000`) and `CancelIoEx` (use overlapped I/O plus a stop event).
- `.venv\Scripts\python.exe` is a redirector: the real image is the base interpreter shared by every Python process (see the Task 4.3 `[decision]`).

## Planned Workflow Summary

### Flow 1 — One-time clinic setup
Open the desktop app's Clinics tab, paste a clinic's Cliniko API key and a contact email for Cliniko's User-Agent, then press Validate. The app checks the key against Cliniko: practitioner role, the practitioner record, a subdomain that matches, and a key shard that matches the clinic host. It stores the key in Credential Manager and the non-secret clinic record in `clinics.json`. It then advises clearing Windows clipboard history. Repeat for the second clinic.

### Flow 2 — A consultation
1. Open the patient's treatment note in Cliniko. The side panel shows "Checking with Cliniko…", then the patient's name, the appointment time (local time), the clinic and "Note verified with Cliniko". If Cliniko is unreachable it shows "Not verified with Cliniko — recording allowed, writing to Cliniko blocked until verified".
2. Tick the consent box. It is never pre-ticked and clears after every Start. Start recording becomes enabled; press it. The app starts only if the tab, clinic, patient and note still match what the panel showed.
3. While recording, a red frame surrounds the Cliniko page, and the panel shows the timer, the patient, "Consent confirmed <time>", and Pause / Finish consultation. The icon badge reads REC. The desktop Session screen shows the same patient, clinic and verification line.
4. Press Finish consultation. The panel shows "Finishing <patient>…" through the short processing tail. The session joins the Unreviewed section, and the desktop app shows its transcript and review as it does today.

### Flow 3 — Patient change mid-recording
Opening another patient's note (or leaving the note, closing the tab, logging out, Chrome disconnecting, or the computer going to sleep) pauses the recording at once. The frame turns amber and a full-page block covers Cliniko, showing "Recording belongs to <A>" beside "You opened <B>" (when A is in the other clinic, the page block names only the clinic and the panel names A), with three choices:
- **Finish previous (<A>)** finishes A's consultation.
- **Resume previous** returns the tab to A's note, and resumes only when Chrome reports A's note again.
- **Discard previous** asks "Discard <A>'s recording? This cannot be undone." and needs a second click.

No session is ever re-bound to another patient. A linked session cannot resume, from the desktop, the hotkey or the panel, while Chrome is disconnected or its note is not reported.

### Flow 4 — Back-to-back patients and the Unreviewed section
After A's tail finishes, B's note can be started, unless A's Note review is open, in which case the panel says "Save or cancel <A>'s note review to start". A waits in the Recovery screen's "Unreviewed notes" section and opens straight into review without re-transcribing, showing the saved note with its edits when one was saved (D6). Two recordings on the same note both wait there; the banner names the count. Reopening A's note in Cliniko later shows a banner, "Unreviewed note for <A>", with an Open for review button that brings the desktop app forward (or flashes it in the taskbar) on A's review. The app warns two hours before any unreviewed note reaches the 24 h limit, and on closing the app it lists the expiry times.

### Flow 5 — Hands-free and warnings
- The hotkey (Task 7.1 picks a chord that is safe on AltGr layouts) pauses or resumes from anywhere in Windows. A resume passes the same context check as the panel.
- Saying "scribe pause" pauses once the live transcriber reaches that window, a few seconds later. Every pause shows a desktop cue. Resuming always needs the hotkey or a click.
- A closing phrase followed by a greeting shows a "This may be a new consultation" warning in the panel and the desktop app. It is only a warning; nothing is paused or switched.

### Flow 6 — Desktop-only fallback
The desktop Start button still works, labelled "Not linked to a Cliniko note", and requires the same consent tick. The consent record is saved as for a linked start. The session is copy-only and can never be written to Cliniko.

## Design Decisions
- **D1 — Side panel UI** (practitioner, 2026-09-27; four mockup directions compared in chat; recorded here in words; layouts simplified in the hardening pass).
  - Consent and every control live in Chrome's global side panel (`chrome.sidePanel`), never in Cliniko's DOM.
  - The only in-page elements, rendered by the page script from its tab's slice of the app's `state` inside a closed shadow root, are:
    - (a) a 3 px viewport frame: red while recording, amber while paused or blocked;
    - (b) the full-page block: a dimmed page and a centred card with the two patients side by side and Finish previous / Resume previous / Discard previous. Discard needs a second confirming click. When the recording belongs to ANOTHER clinic, the block names only this tab's patient and says "Recording belongs to a patient in <other clinic's label>"; the previous patient's name appears only in the panel (peer r2 PR-MED-002).
  - Five panel layouts plus one banner:
    1. **Message** — "Clinic Scribe is not running — open it to record" / "This clinic is not set up — add its key in Clinic Scribe's Clinics tab" / "Open a patient's treatment note to record" / "Another Chrome profile is connected to Clinic Scribe" / "Save or cancel <A>'s note review to start" / "Restoring the safeguards on this tab…".
    2. **Checking** — "Checking with Cliniko…".
    3. **Ready** — the patient name, appointment (local time, zone labelled), clinic, a verification line ("Note verified with Cliniko" or the unverified-offline wording), the consent checkbox (never pre-ticked, cleared on any context change and after every Start), and Start (disabled until ticked).
    4. **Live** — a recording, paused or "Finishing <A>…" variant, with the timer, patient, "Consent confirmed <time>", Pause/Resume and Finish consultation.
    5. **Blocked** — mirrors the page block and names both patients.
    6. **Banner** — "Unreviewed note for <patient> — Open for review", shown over Message or Ready.
  - The icon badge shows REC (red), PAUSED (amber), "!" when the pipe is down while a session is live, or nothing. This replaces `ConnectionManager.BADGES`.
  - Copy follows `docs/design-system.md` Microcopy. Recording consent is an EXPLICIT exception to the design system's pre-tick rule, and 8.1 records it there.
  - Every string from the app is rendered with `textContent` only, never `innerHTML`.
  - Content scripts cannot call `chrome.sidePanel`, so the block's buttons send commands directly and the panel mirrors them. Task 6.4 spikes whether `sidePanel.open()` can run from an action-click gesture.
  - Rejected: a strip inside Cliniko's layout; a corner pill alone; desktop-led.
- **D2 — Protocol v2: three new message types; refusals travel in `state`.**
  - `context` (extension→app): `{seq, tab_id, window_id, focused, host?, page: note|login|other_cliniko|not_cliniko|closed, patient_id?, note_id?}`. `host` is present only for allow-listed hosts. A tab the extension has already reported that navigates off the allow-list sends `page: not_cliniko` with NO host and NO URL; its removal sends `page: closed`. An untracked non-Cliniko tab is never reported (peer r1 PR-HIGH-002).
  - `command` (extension→app): `{action: start|pause|resume|finish|discard|resume_previous|open_review, state_rev, session_ref?, consent?: {confirmed: true, text_version}, target?: {tab_id, clinic_host, patient_id, note_id}}`. `start` MUST carry `target` and `state_rev`, and the app refuses unless both match its latest bound report AND that report's verification outcome is `verified` or `unverified_offline` (never pending or a named refusal); the check runs on the GUI thread. `resume`, `finish`, `discard`, `resume_previous` and `open_review` MUST carry the `session_ref` they act on, and the app refuses (named, in `last_refusal`) unless it equals the current live session's (or, for `open_review`, the indexed session's) `session_ref`, checked on the GUI thread before the slot runs. `pause` is fail-safe and acts on the current live session without a ref. `discard` from the block must also carry `confirmed: true` from the second click, bound to the same `session_ref` (peer r1 PR-HIGH-001).
  - **Reference registry (peer r2 PR-MED-001).** The app keeps ONE in-memory map `session_ref → session_id` for its lifetime, never persisted. A ref is minted when a session starts, and for each session the reminder index gains at startup reconstruction. It is kept through retirement and checkout (the live ref becomes the indexed ref), and removed when its session is completed, discarded or expired. A command resolves to exactly the entry its ref names, never to "the newest"; a ref that no longer resolves is a named refusal. After an app restart every ref is new, so a click rendered before the restart is refused and the panel re-renders from the next `state`.
  - `state` (app→extension): a FULL snapshot of the app's view, built by one `build_state()`, compared with the last snapshot sent ON THE CURRENT PIPE CONNECTION, and sent only if different. The poll, the events and every (re)connect call the same `publish()`. The last-sent snapshot belongs to the connection: it is cleared when a pipe client connects, so the first `publish()` on every new connection sends the full snapshot even when the app's state is unchanged (peer r3 PR-MED-002). A service-worker restart closes the native port, so the extension "re-requests state" by reconnecting; there is no separate state-request message. It carries `state_rev`, `app_running`, the live session's `session_ref` and, separately, the banner target's `session_ref` (opaque random tokens from the app-lifetime reference registry below, never a session directory name), the allow-list, display strings, the block, reminder flags, hotkey and spoken-pause availability, warnings and `last_refusal` (the named reason for a refused command).
  - `error` is for FATAL protocol faults only. The extension disconnects on it (`connection.ts:136`). A refused command never uses `error`.
  - Every id matches `^[1-9][0-9]{0,18}$`. Every string and array in every payload has a maximum length, checked in both mirrors and pinned in the fixtures.
  - `context`/`command`/`state` require the session nonce. The HOST stamps it on app→extension `state` and strips it toward the app; the app never sees it.
  - The host originates exactly one thing: `state{app_running:false}` while the pipe is absent. It keeps re-waiting on the pipe rather than exiting, so no 5-minute backoff follows an app restart.
  - `meta.json` becomes version 2, floor 2, with per-type payload models in `protocol.py` and `protocol.ts`.
  - The background sends each tab ONLY the frame colour and block data for its own host. A patient name reaches a page tab only when that patient belongs to that tab's own clinic; the panel may show both. A block across clinics names the other clinic by its label only (D1).
  - Commands are accepted by the background only from the panel's extension URL or an allow-listed `sender.tab.url`. Page-script buttons act only on `event.isTrusted`.
  - Rejected: `error` for refusals (it disconnects); separate "previous" message types; deltas.
- **D3 — Encounter model** (`encounter.py`).
  - `EncounterContext`: `clinic_id, clinic_host, patient_id, treatment_note_id, booking_id?, practitioner_id, template_id?, verification: verified|unverified_offline, verified_at?`. Ids are strings.
  - `ConsentAttestation` (PLAN.md core type): `confirmed_at`, `text_version="recording-consent-v1"` (PLAN.md's wording), `practitioner_id?`, `treatment_note_id?` (absent means unlinked). It is distinct from the learning consent `CONSENT_TEXT_V3`.
  - Display strings (patient name, appointment time) are NEVER persisted.
  - `booking_id` is optional: the panel shows "No linked appointment" when it is absent.
- **D4 — Verification** (`verify_note_context`).
  - One `GET /treatment_notes/<id>`. The note's patient link equals the URL's patient id; `draft` is true and `finalized_at` null; its practitioner link equals the clinic's practitioner id. Then `GET /patients/<id>` and the booking (if linked), for display only.
  - Outcomes:
    - `verified`;
    - `unverified_offline` — a connection error, timeout, 5xx or 429 (recording allowed, write-back blocked);
    - a named refusal — a mismatch, a final note, the wrong practitioner, 401/403/404, or a TLS certificate failure (Start refused, reason shown).
  - The app numbers pipe connections: a `conn_gen` counter bumped on every new pipe client (the app's own count, never sent to Chrome). `seq` restarts per connection. Each verification carries the `(conn_gen, seq, clinic_host, patient_id, note_id)` it answered, and is applied only if that is still the latest report of the CURRENT connection for the same target AND the clinic's `clinic_rev` is unchanged; anything else, including every result pending from an earlier connection, is dropped without touching the target, display strings or Start eligibility. A new connection also clears the bound report, so Start and Resume need a fresh report on the new connection (peer r3 PR-MED-001). Context-triggered calls are throttled per note.
  - Re-verification runs on recovery or Unreviewed checkout, on pipe reconnect for a linked live session, and in Phase 4 before the write. The panel copy says so.
- **D5 — The pause rule, evaluated only in the app** (`ContextEvaluator`). Pause when:
  - the bound report changes note or patient, or `page ≠ note` (including the bound tab navigating off the allow-list, which arrives as `page: not_cliniko` per D2);
  - the bound tab is removed (`page: closed`);
  - the pipe closes, or a NEW pipe client connects;
  - the focused tab of the focused window reports `page=note` for another patient or note, or `page=login`;
  - the machine suspends (`PBT_APMSUSPEND`).

  Screen lock does not pause. Non-Cliniko tabs never pause: activating or focusing a SEPARATE non-Cliniko tab changes nothing; only the BOUND tab leaving its note pauses.
  - `pause_for(reason)` by state:
    - RECORDING → pause and set the block when the reason is a context reason;
    - PAUSED → set the block only;
    - PROCESSING / QUEUED / IDLE → no-op.
  - Resume (panel, desktop button, hotkey) is refused for a linked session while the pipe is down or the latest bound report is stale or mismatched, and the reason is named. After a Chrome restart the session re-binds to a tab reporting the same `(clinic_host, note_id)`. `resume_previous` carries ids only, and the extension builds the URL from the allow-list.
  - Every pause shows a desktop cue (status line plus window flash) as well as the panel.
- **D6 — Back-to-back and Unreviewed.**
  - The single-active-session invariant is kept. "Finishing <A>…" shows while PROCESSING. Start for B is allowed at QUEUED unless A's generation lease is held ("Save or cancel <A>'s note review to start").
  - Starting B retires A (the existing `start()` retirement). Unreviewed is a section of `RecoveryScreen`, so its single `_protected` set keeps feeding the periodic sweep.
  - `RecoverableSessionInfo` gains `has_transcript`, `has_note` and `has_encounter`, from stat only. Rows with a transcript offer "Open for review" instead of "Resume processing", so a saved note is never re-transcribed away.
  - "Open for review" has two paths (peer r1 PR-MED-004). With no `note.enc` the review opens from `transcript.enc`. With a `note.enc` it opens the SAVED note through the verified `session_store.read_note` (today nothing in the UI calls it), keeping the clinician's edits, confirmations and saved prose; generation is offered only as an explicit "Regenerate (replaces the saved note)" action. A `note.enc` that fails verification is a named refusal on the row, never a silent regenerate or overwrite. A saved note whose note config no longer matches is shown read-only with that reason, and copy stays available on it.
  - How a retired session gets back to a generation-capable review is Task 5.4's `[decision]`.
  - The reminder index `(clinic_id, note_id) → [session_id, …]` (newest first; one note can own several recordings, e.g. a second recording on the same open note) is filled from the in-memory `EncounterContext` at retirement. The banner names the count when it is more than one; `open_review` opens the newest, and the Unreviewed section lists every one. Removing one session (Complete, Discard or expiry) removes only that entry (peer r1 PR-MED-005). Only app start decrypts `encounter.enc`, once per existing session, and that path has a spy test.
  - The expiry warning reuses `_session_created_at` / `earliest_trusted_timestamp`. The app warns 2 h before the limit, and on close it lists expiry times.
- **D7 — Hands-free.**
  - The hotkey uses `RegisterHotKey` handled in `MainWindow.nativeEvent`. The chord avoids Ctrl+Alt (AltGr on European layouts), and a registration failure is shown.
  - Spoken pause is a slot on `TranscriptScreen.live_window` (already a queued GUI-thread signal). A leading-word-boundary matcher for the normalised phrase "scribe pause" ("prescribe, pause" must not match) calls `pause_for("spoken")`. The resume cutoff is kept on the captured-audio timeline (the live transcriber's audio seconds at the last Resume). A match counts only if the matched phrase's FIRST word starts at or after that cutoff (from `TranscriptWord.start_seconds`); a whole window's end time is never the test, because a window can span a Pause/Resume (peer r2 PR-MED-003).
  - The phrase stays in the transcript.
  - "Spoken pause unavailable for this recording" comes from a new controller accessor over the live transcriber's failure state.
  - The latency is documented.
- **D8 — New-consultation warning.** Phrase rules over live windows (a closing phrase followed within N windows by a greeting), with the lists and N as constants in `voice_commands.py`, pinned by tests. It is a warning only.
- **D9 — Cliniko client contract** (`cliniko_client.py`).
  - Uses `http.client.HTTPSConnection` with an explicit `ssl` context (TLS 1.2 minimum, default Windows store). The host is built only from a validated shard (`api.<shard>.cliniko.com`, shard ∈ the documented set); an unknown or missing suffix is REFUSED, never defaulted.
  - No redirects, no proxy, timeouts, and `set_debuglevel(0)` pinned. The body is read up to a cap + 1 and anything over the cap is refused.
  - The User-Agent is `Clinic Scribe (<contact email>)`, and the email is rejected if it contains CR/LF or fails a simple shape check.
  - Named errors: `CredentialsRejected`, `NotFound`, `RateLimited(reset)`, `Unreachable`, `CertificateRejected`, `Malformed`. No exception or log line carries the key, a request path or an id.
  - A `Transport` protocol is injected in tests. GET only, pinned.
  - The one `# noqa: TID251` sits on the `http.client` import, pinned by a test.
  - `apply_offline_env` removes `SSLKEYLOGFILE` and `assert_offline_env` refuses it, beside `LLAMA_CPP_LIB_PATH`.
  - The key is read from Credential Manager once per client call and dropped after. One `verify_note_context` or one Validate is ONE client call: its requests share that single read, so a key replaced mid-verification can never mix credentials within it.
  - Each clinic has an in-memory `clinic_rev`, bumped on Replace key, Remove and a registry edit (peer r4 PR-MED-001). A verification or Validate captures it at dispatch and commits only if it is unchanged, on the GUI thread; otherwise its result, display strings and any registry write are dropped. Replace and Remove also clear that clinic's current verification outcome, so Start needs a fresh verification under the new key; a removed clinic's pending work can never restore its registry entry.
- **D10 — Clinic registry** (`clinics.py`).
  - `clinics.json` holds non-secret records `{clinic_id, display_name, subdomain, shard, user_id, practitioner_id, validated_at}` plus the contact email. The key lives in `SecureStorageProvider(clinic_id, "cliniko_api_key")`.
  - Validation: `GET /user` (role practitioner, active) → `GET /practitioners?q[]=user_id:=` (exactly one) → the subdomain from `/settings/public`. If that is refused, the practitioner types the subdomain, and it is CONFIRMED by the first note that verifies with that key on that host (the former `[decision]`, settled in the hardening pass; P.1 records which route applies).
  - The key shard must equal the host shard. A duplicate subdomain is refused.
  - The allow-list sent to Chrome is exactly the registry's hosts.
  - Remove is REFUSED while the live session (recording, paused, processing or queued) is linked to that clinic: "Finish or discard the recording for <clinic> first" (peer r5 PR-MED-001). Removing it therefore never strands a live recording with a bound report the app can no longer verify or write to. Unreviewed sessions of a removed clinic stay reviewable and copyable; their write-back is refused because the clinic is gone (Constraint 6).
- **D11 — `encounter.enc`.**
  - Written on EVERY start, linked or not. It is `{consent, context?}`, encrypted under the session key with a distinct AAD, and written atomically after `key.dpapi` and BEFORE `audio.enc`.
  - "Unlinked" means consent present, context absent. Missing or undecryptable means unlinked for write-back purposes, and "consent record unavailable" is shown.
  - Discard's `rmtree` and the complete→sweep GC cover it.
- **D12 — Copy flag.** `COPY_TO_CLINIKO_ENABLED` flips to `True` under the practitioner's 2026-09-27 decision; `_copy_ready` is untouched. Task 1.4 is a composer must-pause because the permission classifier blocked the planning-time edit.
- **D13 — Page-script lifecycle and trust.**
  - Content scripts are declared for `https://*.cliniko.com/*` but stay inert until their host is in the allow-list of the first `state`. A host that LEAVES the allow-list (its clinic removed) tears its page scripts down on the next `state`: frame and block removed, patient data dropped, `location.href` reports stopped, and the background stops reporting that host's tabs and rejecting its commands as before. It reactivates only through a fresh allow-list and a fresh report.
  - On `runtime.onInstalled` (update or reload), the background re-injects the page script into open Cliniko tabs with `chrome.scripting.executeScript` (`scripting` permission, Cliniko hosts only). Until the page script reports, the panel shows "Restoring the safeguards on this tab…".
  - The page script is a cue plus an input path, never the enforcing control: the app enforces the pause, and write-back enforces verification.

## Schema / Data Changes
- New `EncounterContext` / `ConsentAttestation` (pydantic, frozen, `extra="forbid"`) in `encounter.py` (D3). `RecordingSession.encounter_context` becomes `EncounterContext | None`, and `consent: ConsentAttestation` is added. Whether `consent` is required on the MODEL or only at `start()` is Task 3.1's call: required on the model breaks every bare `RecordingSession()`, which is listed in Key Findings.
- New per-session file `encounter.enc` (D11), written on every start. No change to `audio.enc`, `transcript.enc` or `note.enc` formats.
- `RecoverableSessionInfo` gains `has_transcript`, `has_note` and `has_encounter` (stat only).
- New `%LOCALAPPDATA%\ClinikoScribe\clinics.json` (D10), with a schema version and a fail-closed loader.
- New Credential Manager entries `ClinikoScribe/<clinic_id>` / `cliniko_api_key`.
- Protocol v2 (D2): `protocol/fixtures/meta.json` goes to 2/2, with new valid and invalid fixtures, including over-length and bad-id cases.
- The logging tripwire's field set gains the new context and consent field names (derived, per lessons 2026-08-10). The native host's logging covers relayed payloads.

## Config / Environment / Deployment Impact
- No environment variables are added. `SSLKEYLOGFILE` is REMOVED at startup by `apply_offline_env` (D9). No new Python runtime dependency.
- `desktop/pyproject.toml`: mypy overrides for `win32event`, `win32gui` and `win32process` (Tasks 4.2, 7.1).
- New extension devDependency: a DOM test environment (happy-dom or jsdom, pinned exactly), authorised by the practitioner at Task 6.0, BEFORE the extension UI tasks.
- Manifest changes: `sidePanel` and `scripting` permissions, `side_panel.default_path`, and `content_scripts` for Cliniko hosts. They need `npm run build`, a reload in `chrome://extensions`, and a full Chrome restart (AGENTS.md step 7). The pinned `key` keeps the extension id, so `allowed_origins` is unchanged.
- The native host is unchanged in path and name; re-register only after a venv move. The pipe name is per user (`\\.\pipe\ClinikoScribe-<user SID>`), created by `scribe-app`.
- CI (`.github/workflows/ci.yml:20`) sets `SCRIBE_SKIP_INTEGRATION=1`, so the no-sockets and relay integration legs run only on the practitioner's host. The composer's local run is the gate, and unit tests for the pipe must not depend on the native-host registration.
- Release risk: the first real network traffic from `scribe-app`. The live check is Task P.2, run from a user-launched app.

## Critical Constraints
1. **Drafts only, by construction.** This plan has no write method, and no code path can send `draft: false`.
2. **The Cliniko client is the only network surface.** One module, a pinned host from a validated shard, no redirects, no proxy, TLS 1.2+, and `SSLKEYLOGFILE` removed. No Cliniko call without a context report, a Clinics-tab Validate or a checkout. Every existing no-sockets leg stays at zero connections.
3. **The app is the single owner of state and pause decisions** (D5). Chrome renders the app's `state` and relays clicked intents. No session is ever re-bound to another patient.
4. **Consent before every recording, recorded on every start.** The controller refuses `start()` without a `ConsentAttestation`; `encounter.enc` is written before `audio.enc`; the tick is never pre-ticked.
5. **Start is bound to what the practitioner saw; every other mutating command is bound to its session.** A `start` whose `target`/`state_rev` does not match the latest bound report, or whose report is not `verified` or `unverified_offline`, is refused; an `unverified_offline` Start records with write-back blocked (Constraint 6). A `resume`/`finish`/`discard`/`resume_previous`/`open_review` whose `session_ref` does not match is refused and changes nothing (D2).
6. **Write-back is refused unless the context is verified** (`writeback_context`, over a live session OR a checked-out recovered or Unreviewed session). Unlinked, unverified, not-re-verified and mismatched sessions are all refused.
7. **Custody:**
   - custody calls happen on the GUI thread only;
   - `encounter.enc` is decrypted only on checkout, plus once per session at app start for the reminder index;
   - the single-active-session invariant is unchanged;
   - a linked session never resumes without a current matching report.
8. **Secrets and names.** The key is never logged, displayed after entry, put in an exception, sent to Chrome or written outside Credential Manager. Patient names never enter extension storage, a log, or another clinic's tab, and are rendered as text only.
9. **Refusals never travel as `error`.** `error` is fatal-only, because it disconnects the extension.
10. **Named pipe only for host↔app** (the locked Phase 1 topology). All pipe and protocol input is validated: ids are digits, and every length is bounded.
11. **`protocol/fixtures/` is the contract**; both mirrors are tested against it.
12. **Security-doc claims state only what the structure enforces**, rewritten as a class (lessons 2026-08-14, 2026-08-10).

## Validation / Verification
**Baselines (dry-run 2026-09-27 at `main @ 33bd35e`, re-probed at the hardening pass; read-only checks only)**
- `desktop`: `ruff check .` → "All checks passed!".
- `grep -rn "noqa: TID251" desktop/src | wc -l` → 0.
- `grep -rn "import http\|from http\|import ssl\|urllib" desktop/src | wc -l` → 0.
- `start(0)` sites in `desktop/tests/*.py` → 59 (including the 4 child-script strings); `start(99)` → 2.
- Suite: 2817 passed at the last recorded run (`AGENTS.md`, 2026-09-27); mypy 39 files.
- Node v24.18.0. The extension has Vitest 4.1.10 and no DOM environment.

**Per phase (composer-run on the Windows host; the local run is the gate because CI skips integration)**
- `desktop/`: `ruff check . && mypy && pytest`.
- `extension/`: `npm run qa`.
- After Task 1.1: the TID251 noqa count is exactly 1, in `cliniko_client.py`.
- The existing `test_integration_no_sockets.py` legs stay at zero connections. The host-handshake-with-no-app leg still passes after Phase 4, and a new leg with the app's pipe open asserts no sockets.

**Required test classes**
- Client:
  - the host pin, and an unknown suffix refused;
  - redirects refused, the size cap, and every named error including `CertificateRejected`;
  - the transport only ever receiving "GET";
  - no key, path or id in any exception or log record;
  - a CR/LF email refused;
  - `SSLKEYLOGFILE` removed and refused.
- Registry: validation success and each refusal; duplicate subdomain; shard mismatch; the typed-subdomain confirmation route; zero calls at startup or idle with an injected counting transport.
- Encounter and custody:
  - `start()` refuses without consent on both paths;
  - `encounter.enc` is written before `audio.enc` on every start (ordering and crash tests);
  - decrypt happens only on checkout plus the one app-start pass (spy);
  - recovered and Unreviewed linked sessions re-verify;
  - the consent tick never pre-ticks and clears after Start.
- Pipe:
  - the hardening flags and DACL are pinned;
  - an unverified server is a hard error;
  - a new client connection counts as pipe loss;
  - framing over short reads;
  - relay both ways;
  - the host answers hello/ping and pushes `app_running:false` with no app, and keeps re-waiting.
- Protocol: every v2 fixture, valid and invalid (bad ids, over-length strings and arrays, a missing nonce), in both mirrors. A refusal arrives in `state.last_refusal` and does NOT disconnect the extension.
- Pause rule: the D5 table as a parameterised test, including:
  - non-Cliniko tabs NOT pausing;
  - multi-window focus;
  - `pause_for` in every session state;
  - sleep pausing, and lock not pausing;
  - resume refused while the pipe is down;
  - re-binding by ids after a Chrome restart.
- **Cross-patient adversarial matrix** (`test_cross_patient.py`; Task 3.6 has the encounter and custody cases, Task 5.6 the context cases). Every case ends in a refusal of the named operation (Start, Resume, a session-bound command, or write-back) and no session re-bound or changed:
  - the URL patient differs from the API note's patient;
  - a note from the other clinic, or a host/shard mismatch;
  - a finalised note;
  - a wrong practitioner;
  - a missing or corrupt `encounter.enc`;
  - an unlinked session;
  - an `unverified_offline` session (write-back refused; Start itself is ALLOWED — see the positive case below);
  - a stale verification result (wrong `seq`), and a result from an EARLIER connection carrying the SAME `seq` that finishes last after an extension reload (must not change the current target, display or Start eligibility);
  - a start whose `target`/`state_rev` does not match;
  - a delayed Discard (second click), Finish or Resume for A arriving after A was finished and B started — each refused by `session_ref` with B unchanged;
  - the bound tab navigating off the allow-list (`not_cliniko`) or closing (`closed`) — pauses; a SEPARATE non-Cliniko tab activated — no pause (the positive control);
  - a report from a non-bound or stale tab;
  - a replayed report after resolution;
  - Resume previous while B is on screen;
  - resume with the pipe down;
  - a second pipe client.
  - Positive cases (must SUCCEED): an `unverified_offline` Start records with consent in `encounter.enc`, the target immutable, and `writeback_context` refused; two recordings on one note both stay in the reminder index across a restart, and completing one keeps the other's reminder; a saved note reopened from Unreviewed shows the saved edits (save edits → retire → restart → reopen).
- Extension (Vitest + DOM environment + `chrome.*` fakes):
  - the URL parser;
  - allow-list inertness, and teardown when a host leaves the allow-list (frame, block and names removed; no further reports);
  - each of the five layouts plus the banner;
  - a markup-bearing patient name rendered as text;
  - per-tab host scoping of frame and block data, including a cross-clinic block whose payload and rendered DOM carry neither the previous patient's name nor their ids;
  - `isTrusted` and sender checks;
  - re-injection on `onInstalled`;
  - the badge;
  - the service-worker restart re-requesting state;
  - `resume_previous` navigation built from the allow-list;
  - a manifest pin (`sidePanel` and `scripting` present, no `tabs`, content scripts only on Cliniko hosts);
  - no patient name in `chrome.storage` and no key in any payload.
- Hands-free:
  - hotkey registration success and failure;
  - the spoken matcher (positives, "prescribe, pause" and other near-misses);
  - a phrase spoken before the last resume being ignored, including in a mixed window that spans the Resume, while a wholly post-Resume phrase in the same kind of window still pauses;
  - "unavailable" when live transcription is off or failed;
  - the boundary rules (positives and negatives).

**Practitioner-run**
- Task P.1: the read-only feasibility check on both clinics.
- Task P.2: the live smoke — Flows 1–6 on both clinics from a user-launched app and a fully restarted Chrome, including:
  - a deliberate patient switch;
  - a Chrome close mid-recording, then resuming after reopening the note;
  - an unreachable network at Start;
  - an extension reload mid-recording (re-injection);
  - sleep mid-recording;
  - the hotkey and "scribe pause";
  - the Unreviewed reminder and the expiry list on close;
  - the measured tail of 5.3.

**Success criteria**
- PLAN.md Phase 5's completion line: workflow and adversarial tests cannot attach one consultation to another patient. Every matrix case refuses, and no session is re-bound. The pre-navigation speech residue is stated (Accepted Assumptions).
- PLAN.md test plan: recording cannot start without the consent checkbox; switching patient, appointment or clinic pauses immediately; context loss blocks write-back; cross-patient tests pass with zero failures.

## Deferred / Out of Scope
See `Planning Extraction Summary` → Deferred, and Excluded. The Phase 4 write is the next plan and needs no rediscovery: `.cursor/plans/explore-cliniko-integration.md` carries its findings and assumptions, and this plan's `writeback_context` and `ClinikoClient` are its entry points.

## Current State / Handoff Note
- Earlier step: `/review-plan` hardening pass (2026-09-27; four lens subagents — coverage, practicality, risk, simplicity; ~45 findings folded in; deferral gate recorded).
- Last completed step: `/peer-loop` plan review (codex `gpt-6-astra` medium), converged at round 6. Round 1: 5 findings (2 HIGH, 3 MED), all accepted and amended. Round 2 (attempt 1 inconclusive on the codex usage limit; resumed session `01a0e113`): 3 MED, all accepted and amended. Round 3: 2 MED (connection generation for verification results; per-connection snapshot), accepted and amended. Round 4: 1 MED (clinic key changes invalidate pending verification — `clinic_rev`), accepted and amended. Round 5: 1 MED (removing a clinic — Remove refused while the live session is linked; page-script teardown), accepted and amended. The pass hit its cap of 5 without a clean round; the practitioner approved one more round, and round 6 was clean (0 findings) — the loop CONVERGED.
- Current in-progress step: None
- Immediate next action: commit the hardened plan (practitioner's say-so), then Task 1.1 via `/execute-loop`.
- Open blockers / open questions:
  - Task P.1 (practitioner) confirms D10's subdomain route and the note-link fields.
  - Task 1.4 is a composer must-pause (the permission classifier blocked the flag edit during planning).
  - Task 6.0 needs the practitioner's authorisation for a dev dependency.
  - `[decision]` tasks remain at 4.3 (default (b)) and 5.4 (review-reopen custody).
- Last plan sync: 2026-09-27

## Review History
- (no reviews yet)

## Review Findings Log
### Round 1 - 2026-09-27 - cliniko-workflow-safeguards plan, independent cross-family codex plan peer-review (round 1)

- Round status: Closed (5 accepted, 0 rejected; amended in place)
- Source: Codex plan peer-review
- Recorded by: composer (transcribed verbatim from the read-only peer's stdout, `.cursor/loops/cliniko-safeguards-plan-peer-r1.log`)
- Materiality: 5 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: 096f3e4 + working-tree plan
- Files read:
  - Full `.cursor/plans/plan-cliniko-workflow-safeguards.md`; `.agents/skills/peer-review/SKILL.md`; scoped `AGENTS.md`, `PLAN.md`, and `docs/lessons.md`.
  - Named symbols in `desktop/src/scribe_desktop/`: `session.py`, `session_store.py`, `app.py`, `benchmark.py`, `logging_setup.py`, `secure_storage.py`, `native_host.py`, `protocol.py`, `framing.py`, `transcription.py`; UI `session_screen.py`, `main_window.py`, `recovery.py`, `models.py`, `transcript.py`.
  - Extension `manifest.ts`, `connection.ts`, `background.ts`, `protocol.ts`, `package.json`; `protocol/fixtures/meta.json` and fixture inventory.
  - `desktop/pyproject.toml`; detection helper and leg inventory in `desktop/tests/test_integration_no_sockets.py`; `.github/workflows/ci.yml`.
  - Scoped excerpts of `docs/security/{threat-model,data-flow-map,retention-schedule,intended-use}.md`, `docs/testing/shipping-gate.md`, and `docs/design-system.md`.
- Finding verification: 9 candidates / 4 dropped / 0 downgraded. Overlapping observations deduplicated. Static review only; no files written, tests run, or builds run.

#### Findings

##### Unstated assumptions — PR-HIGH-001: Non-Start commands lack an enforced session binding

- Plan section: D2; Task 4.5; cross-patient matrix.
- Materiality: build-affecting
- Why it matters: A second-click Discard intended for A can arrive after desktop actions finish A and start B. The proposed bridge dispatches to a slot that discards the current session. Carrying `state_rev` does not prevent this unless its validation is required for that command. The plan explicitly requires that check only for Start. A stale confirmation could therefore cryptographically delete B; stale Finish or Resume can likewise affect the wrong consultation.
- Current plan text:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:392`: “`start` MUST carry `target` and `state_rev`, and the app refuses unless both match its latest verified bound report (checked on the GUI thread). `discard` from the block must carry `confirmed: true` from the second click.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:750`: “`command` goes to the SessionScreen slots (`start_linked` with the target check, `on_pause`, `on_resume`, `on_finish`, `on_discard` with the confirm flag, `open_review`). A missing microphone becomes a named refusal.”
- Evidence:
  - `desktop/src/scribe_desktop/ui/session_screen.py:219`: `self._controller.discard()`
  - `desktop/src/scribe_desktop/ui/session_screen.py:202`: `session = self._controller.finish()`
  - `desktop/src/scribe_desktop/session.py:794`: `live = self._require_live()`
- Suggested change: Require every session-mutating remote command, including its destructive confirmation, to identify the intended session and pass a GUI-thread revision/session check before dispatch. Add delayed A Discard, Finish and Resume cases arriving after B starts; each must refuse without changing B.
- /fix decision: Accepted (verified: `session_screen.py:219` discards whatever is current; D2 bound only `start`) — D2 adds a per-recording opaque `session_ref` in `state`; resume/finish/discard/resume_previous/open_review must carry it and are refused before their slot on mismatch; pause stays fail-safe. Siblings: Constraint 5, Tasks 3.3/4.1/4.5/6.3/6.4, matrix rows + 5.6.

##### Coverage — PR-HIGH-002: The host filter suppresses bound-tab context loss

- Plan section: D2/D5; Task 6.2.
- Materiality: build-affecting
- Why it matters: If the bound tab leaves Cliniko for an unallowlisted destination, Task 6.2 suppresses the report needed to pause recording. The app retains its last matching report. Closing the tab also needs a defined invalidation representation; merely registering `onRemoved` does not specify one. This differs from activating a separate non-Cliniko tab, which must continue to leave recording running.
- Current plan text:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:795`: “`tabs.onUpdated`/`onActivated`/`onRemoved` and `windows.onFocusChanged` drive `seq`-numbered `context` reports; the URL parser handles the note, login and other pages; nothing is reported for non-allow-listed hosts.”
- Evidence:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:416`: “the bound report changes note or patient, or `page ≠ note`;”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:417`: “the bound tab is removed;”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:391`: “`context` (extension→app): `{seq, tab_id, window_id, focused, host, page: note|login|other_cliniko|not_cliniko, patient_id?, note_id?}`.”
  - `desktop/src/scribe_desktop/protocol.py:26`: `MessageType = Literal["hello", "hello_ack", "ping", "pong", "error"]`
- Suggested change: Define tab invalidation/removal reports for previously tracked tabs, independent of the destination allow-list and without sending the destination URL. Specify their app-side handling. Test bound-tab departure, bound-tab closure and activation of a separate non-Cliniko tab through background→protocol→app.
- /fix decision: Accepted (verified: D2 listed `not_cliniko` yet Task 6.2 reported nothing off the allow-list, and `onRemoved` had no message) — D2 `host?` + `page: closed`; a tracked tab leaving the allow-list reports `not_cliniko` with no host/URL; D5 names both; separate non-Cliniko tab stays a no-pause positive control. Siblings: Task 6.2, 4.1 fixtures, matrix + 5.6.

##### Practicality / feasibility / sequencing — PR-MED-003: The Start predicate contradicts the required offline fallback

- Plan section: D2/D4; Critical Constraint 5; validation.
- Materiality: build-affecting
- Why it matters: Implementing the mandatory “verified bound report” predicate literally refuses the agreed offline recording path. The adversarial matrix also says every case refuses, including `unverified_offline`, without identifying that write-back—not Start—is the operation that must refuse.
- Current plan text:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:490`: “**Start is bound to what the practitioner saw.** A `start` whose `target`/`state_rev` does not match the latest verified bound report is refused.”
- Evidence:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:411`: “`unverified_offline` — a connection error, timeout, 5xx or 429 (recording allowed, write-back blocked);”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:548`: “**Cross-patient adversarial matrix** (`test_cross_patient.py`; Task 3.6 has the encounter and custody cases, Task 5.6 the context cases). Every case ends in a refusal and no session re-bound:”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:555`: “an `unverified_offline` session;”
- Suggested change: Define Start eligibility as a matching current context with either a `verified` or an explicitly allowed `unverified_offline` outcome. Keep write-back restricted to verified context. Specify the refused operation in each matrix row and add a positive offline Start test covering consent, immutable target and blocked write-back.
- /fix decision: Accepted (verified: D2 and Constraint 5 said "verified bound report" against D4's offline-allowed Start) — Start accepts `verified` or `unverified_offline`; the matrix now names the refused operation per row and adds the positive offline Start case. Siblings: D2, Constraint 5, Task 3.6.

##### Coverage — PR-MED-004: Unreviewed reopening does not specify restoration of the saved note

- Plan section: D6; Task 5.4; recovery verification.
- Materiality: build-affecting
- Why it matters: Save releases the generation lease while retaining `note.enc`, allowing the next Start to retire that session. Reopening only its transcript does not restore clinician edits, confirmations or saved prose. Regeneration followed by Save replaces the existing note. Avoiding re-transcription alone does not preserve the saved review.
- Current plan text:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:432`: “Rows with a transcript offer "Open for review" instead of "Resume processing", so a saved note is never re-transcribed away.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:774`: “review opens from `transcript.enc` with generate, save and copy available;”
- Evidence:
  - `desktop/src/scribe_desktop/ui/transcript.py:698`: `self._note_committed = True  # note.enc is on disk (round 36 PR-MED-002)`
  - `desktop/src/scribe_desktop/ui/transcript.py:699`: `self._release_lease()`
  - `desktop/src/scribe_desktop/ui/main_window.py:398`: `self.note_screen.clear()`
  - `desktop/src/scribe_desktop/session_store.py:851`: `def read_note(session_dir: Path, crypto: SessionCrypto) -> GeneratedNote:`
  - `desktop/src/scribe_desktop/session_store.py:847`: `atomic_write_bytes(note_path, crypto.encrypt(note.to_bytes()), error_label="note artifact")`
- Suggested change: Specify separate reopen paths for transcript-only sessions and sessions with a saved note. Restore the latter through verified `read_note`, preserving saved content and defining configuration compatibility and copy eligibility. Add a save-edits→retire→restart→reopen test, plus corrupt/mismatched-note handling that does not silently regenerate or overwrite.
- /fix decision: Accepted (verified: `transcript.py:698-699` releases the lease after Save; no UI caller of `session_store.read_note:851`; recovered view clears the note screen at `main_window.py:398`) — D6 two reopen paths, saved note via verified `read_note`, explicit Regenerate, named refusal on a bad note, `has_note` by stat. Siblings: Flow 4, Schema, Tasks 3.4/5.4, positive matrix case.

##### Unstated assumptions — PR-MED-005: The reminder index assumes one session per Cliniko note without enforcing it

- Plan section: D4/D6; Tasks 5.3–5.5.
- Materiality: build-affecting
- Why it matters: Finish recording against note N, start another recording against N, then start another patient. Both N sessions remain recoverable, but the specified index has only one value for their shared key. Retirement or startup reconstruction overwrites one reminder. No verification rule or Start gate prevents this sequence.
- Current plan text:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:434`: “The reminder index `(clinic_id, note_id) → session_id` is filled from the in-memory `EncounterContext` at retirement. Only app start decrypts `encounter.enc`, once per existing session, and that path has a spy test.”
- Evidence:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:430`: “Start for B is allowed at QUEUED unless A's generation lease is held ("Save or cancel <A>'s note review to start").”
  - `desktop/src/scribe_desktop/session.py:442`: `self._retire_locked(live)`
  - `desktop/src/scribe_desktop/session.py:443`: `session = RecordingSession(key_reference="key.dpapi")  # state defaults to idle`
  - `desktop/src/scribe_desktop/session.py:1252`: `"""Drop the in-memory handle to a non-active session. On-disk state`
  - `desktop/src/scribe_desktop/session.py:1253`: `is untouched: a queued/failed session stays recoverable through its`
- Suggested change: Use a collection of session IDs per note with explicit selection, or define a duplicate-note Start refusal that directs the practitioner to the existing session. Test repeated recordings against the same note, restart reconstruction, and removal of one session without losing another’s reminder.
- /fix decision: Accepted (verified: `start()` retires at `session.py:442`, nothing prevents a second recording on one note) — the index maps a note to a newest-first list; banner names the count; removal drops one entry. Chose the list over a Start refusal (a second recording on an open note is legitimate). Phase 4 follow-up note added for the double-write. Siblings: Flow 4, Task 5.3, 5.6, positive matrix case.

- /fix notes (composer, plan-review mode): each amendment re-read from disk after it landed; sibling sweep over Goal/Flows/D2/D5/D6/Schema/Constraints/Validation/Tasks/handoff done by exact-unique scripted replacements outside this log. No finding rejected; no severity changed.

### Round 2 - 2026-09-27 - cliniko-workflow-safeguards plan, independent cross-family codex plan peer-review (round 2)

- Round status: Closed (3 accepted, 0 rejected; amended in place)
- Source: Codex plan peer-review
- Recorded by: composer (transcribed verbatim from the read-only peer's stdout, `.cursor/loops/cliniko-safeguards-plan-peer-r2b.log`; attempt 1 was inconclusive on the codex usage limit, this is the resumed session `01a0e113`)
- Materiality: 3 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: 096f3e4 + working-tree plan
- Files read:
  - Full `.cursor/plans/plan-cliniko-workflow-safeguards.md`, including round 1 dispositions; `.agents/skills/peer-review/SKILL.md`; scoped `AGENTS.md`, `PLAN.md`, and `docs/lessons.md`.
  - Named symbols in `desktop/src/scribe_desktop/`: `session.py`, `session_store.py`, `app.py`, `benchmark.py`, `logging_setup.py`, `secure_storage.py`, `native_host.py`, `protocol.py`, `framing.py`, `transcription.py`; UI `session_screen.py`, `main_window.py`, `recovery.py`, `models.py`, `transcript.py`.
  - Extension `manifest.ts`, `connection.ts`, `background.ts`, `protocol.ts`, `package.json`; protocol fixture metadata and inventory.
  - `desktop/pyproject.toml`; socket-detection helper and integration-leg inventory; `.github/workflows/ci.yml`.
  - Cited excerpts of security documents, shipping-gate documentation and design-system consent/microcopy.
- Finding verification: 9 candidates / 6 dropped / 0 downgraded. Overlapping findings deduplicated. Static review only; no files written, tests run, or builds run.

#### Findings

##### Practicality / feasibility / sequencing — PR-MED-001: Recovered reminders have no defined command-token lifecycle

- Plan section: D2/D6; Tasks 3.3, 5.5 and 6.4.
- Materiality: build-affecting
- Why it matters: Finish A, retire it by starting B, restart the app, then reopen A’s Cliniko note. The reminder index is reconstructed, but its required `session_ref` was never persisted and the only specified minting occurs at Start. The snapshot also specifies only the live session’s reference. Consequently, the banner cannot supply A’s required reference. Using B’s reference refuses legitimate review; bypassing the check defeats the round 1 amendment.
- Current plan text:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:392`: “`resume`, `finish`, `discard`, `resume_previous` and `open_review` MUST carry the `session_ref` they act on”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:393`: “the live session's `session_ref` (an opaque random token minted per recording at Start, never the session directory name)”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:802`: “`start()` also mints the session's in-memory `session_ref` (a random opaque token, never persisted, never the directory name) that D2's session-bound commands match.”
- Evidence:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:435`: “The reminder index `(clinic_id, note_id) → [session_id, …]`”
  - `desktop/src/scribe_desktop/ui/models.py:276`: `session_id: str`
  - `desktop/src/scribe_desktop/session.py:1273`: `live.crypto.destroy()  # in-memory copy only; key.dpapi (if any) remains`
  - `desktop/src/scribe_desktop/session.py:1274`: `self._live = None`
- Suggested change: Define an app-lifetime reference registry covering live and indexed recoverable sessions. Mint fresh references during startup reconstruction, retain them through retirement and checkout, and publish the banner target’s reference separately from the live reference. Resolve a click to that exact entry, never whichever entry is newest when it arrives. Test restart→banner→review, service-worker state restoration, and delayed clicks after an entry is removed or replaced.
- /fix decision: Accepted (verified: the ref was minted only at `start()` and published only for the live session, while the index is rebuilt at startup) — D2 gains an app-lifetime in-memory reference registry (`session_ref → session_id`, minted at Start and at startup reconstruction, kept through retirement/checkout, removed on complete/discard/expiry; exact-entry resolution; refs die with the app so pre-restart clicks refuse); `state` publishes the banner target's ref separately. Siblings: Task 3.3, Task 5.5 (+ its three verification cases).

##### Coverage — PR-MED-002: The cross-clinic page block contradicts patient-name isolation

- Plan section: Flow 3; D1/D2; Critical Constraint 8; Tasks 6.2–6.5.
- Materiality: build-affecting
- Why it matters: While recording A in one clinic, opening B in the other clinic must display a full-page block containing both patients. That sends A’s name into the other clinic’s tab, which D2 and Constraint 8 prohibit. Even within one clinic, the specified named page block contradicts “Patient names reach only the panel.” An executor cannot satisfy both contracts.
- Current plan text:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:377`: “the full-page block: a dimmed page and a centred card with the two patients side by side and Finish previous / Resume previous / Discard previous.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:399`: “Patient names reach only the panel, never another clinic's tab.”
- Evidence:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:498`: “Patient names never enter extension storage, a log, or another clinic's tab, and are rendered as text only.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:902`: “Behaviour: D1's frame and block in a closed shadow root, rendered with `textContent` only.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:572`: “per-tab host scoping of frame and block data;”
- Suggested change: Keep patient names in the extension-owned panel and use generic previous/current-consultation wording in the page block, preserving its controls and session binding. Reconcile Flow 3, D1 and page-script task text accordingly. Add a cross-clinic test asserting that neither the destination tab’s payload nor its rendered block contains the previous clinic’s patient name.
- /fix decision: Accepted with a narrower fix than suggested (verified: D1(b)/Flow 3 name both patients on the page while D2 said names reach only the panel). The practitioner approved the two-names-side-by-side block, so it stays for the SAME clinic (both names already belong to that Cliniko account); across clinics the page block names only its own patient plus the other clinic's label, and the panel names both. D2's rule reworded to match Constraint 8. Siblings: Flow 3, D1(b), D2, extension test (payload + DOM carry no previous-patient name or ids).

##### Unstated assumptions — PR-MED-003: A window-end cutoff still accepts spoken commands from before Resume

- Plan section: D7; Task 7.2; hands-free validation.
- Materiality: build-affecting
- Why it matters: Say “scribe pause,” manually pause before its open window is transcribed, then resume and continue speaking. The existing transcriber retains that window across Pause/Resume. When the combined window arrives, its end is after Resume, so the proposed filter accepts the old command and unexpectedly pauses the resumed consultation. The existing negative test covers wholly old windows, not windows spanning the cutoff.
- Current plan text:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:439`: “A window whose audio ended before the last resume is ignored.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:583`: “a window from before the last resume being ignored;”
- Evidence:
  - `desktop/src/scribe_desktop/transcription.py:1940–1944`:
    ```python
    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False
    ```
  - `desktop/src/scribe_desktop/transcription.py:2186–2188`:
    ```python
    window = SpeechSegment(
        start_seconds=group[0].start_seconds, end_seconds=group[-1].end_seconds
    )
    ```
  - `desktop/src/scribe_desktop/ui/transcript.py:282`: `self.live_window.emit(segments)`
- Suggested change: Define the Resume cutoff in the captured-audio timeline and apply it to the matched phrase’s timestamped words, rather than only the enclosing window’s end. Reject matches beginning before or spanning that cutoff. Test a mixed window containing an old command and new speech, alongside a wholly post-Resume command that must still pause.
- /fix decision: Accepted (verified: `LiveTranscriber.pause/resume` at `transcription.py:1940-1944` only flip a flag, `_transcribe_window` at `:2186` spans the grouped segments, and `TranscriptWord` carries `start_seconds`) — the cutoff is the captured-audio seconds at the last Resume, tested against the matched phrase's first word, never the window end. Siblings: Validation hands-free line, Task 7.2.

PEER-PLAN-ROUND-2 RESULT: 3 findings (CRIT 0 / HIGH 0 / MED 3 / LOW 0; build-affecting 3 / record-only 0 / invalid 0).

- /fix notes (composer, plan-review mode): each amendment re-read from disk; sibling sweep (Flow 3, D1, D2, D7, Constraint 8, Validation, Tasks 3.3/5.5/7.2) by exact-unique scripted replacements outside the log; stale phrasings (`minted per recording`, `reach only the panel`, `audio ended before`) confirmed absent outside the log.

### Round 3 - 2026-09-27 - cliniko-workflow-safeguards plan, independent cross-family codex plan peer-review (round 3)

- Round status: Closed (2 accepted, 0 rejected; amended in place)
- Source: Codex plan peer-review
- Recorded by: composer (transcribed verbatim from the read-only peer's stdout, `.cursor/loops/cliniko-safeguards-plan-peer-r3.log`)
- Materiality: 2 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: 096f3e4 + working-tree plan
- Files read:
  - Full `.cursor/plans/plan-cliniko-workflow-safeguards.md`, including rounds 1–2 dispositions; `.agents/skills/peer-review/SKILL.md`; scoped `AGENTS.md`, `PLAN.md`, and `docs/lessons.md`.
  - Named symbols at HEAD in `desktop/src/scribe_desktop/`: `session.py`, `session_store.py`, `app.py`, `benchmark.py`, `logging_setup.py`, `secure_storage.py`, `native_host.py`, `protocol.py`, `framing.py`, `transcription.py`; UI `session_screen.py`, `main_window.py`, `recovery.py`, `models.py`, `transcript.py`.
  - Extension `manifest.ts`, `connection.ts`, `background.ts`, `protocol.ts`, `package.json`; protocol fixture metadata and inventory.
  - `desktop/pyproject.toml`; socket-detection helper and integration-leg inventory in `desktop/tests/test_integration_no_sockets.py`; `.github/workflows/ci.yml`.
  - Scoped excerpts of `docs/security/{threat-model,data-flow-map,retention-schedule,intended-use}.md`, `docs/testing/shipping-gate.md`, and `docs/design-system.md`.
- Finding verification: 7 candidates / 5 dropped / 0 downgraded. Dropped candidates were already covered by the reference-registry, custody and destination-host contracts, or lacked evidence of a build defect. Static review only; no files written, tests run, or builds run.

#### Findings

##### Unstated assumptions — PR-MED-001: Verification sequence numbers have no defined connection lifetime

- Plan section: D2/D4; Tasks 3.2, 4.5 and 6.2; cross-patient verification matrix.
- Materiality: build-affecting
- Why it matters: An API verification can outlive the Chrome connection that initiated it. For example, verification for A at sequence 1 remains pending while the extension reloads; the replacement worker reports B at sequence 1, and A’s result finishes last. The specified sequence-only check can accept A’s outcome or display fields as B’s current verification. Keeping the old sequence watermark instead can reject legitimate replacement-worker reports. The plan defines neither sequence continuity nor a connection generation that distinguishes these cases. Fresh `session_ref` values do not solve this: verification and Start occur before a recording reference exists.
- Current plan text:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:414`: “Each verification carries the `context.seq` it answered, and a stale result is dropped. Context-triggered calls are throttled per note.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:397`: “`context`/`command`/`state` require the session nonce. The HOST stamps it on app→extension `state` and strips it toward the app; the app never sees it.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:931`: “A `context` for a note triggers `verify_note_context` off the GUI thread, marshalled back, with a stale `seq` dropped.”
- Evidence:
  - `desktop/src/scribe_desktop/native_host.py:93`: `self.session_nonce = self.nonce_factory()`
  - `extension/src/connection.ts:66`: `this.sessionNonce = null; // discard any stale nonce (plan acceptance criterion)`
  - `extension/src/connection.ts:117`: `this.sessionNonce = envelope.session_nonce ?? null;`
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:558`: “a stale verification result (wrong `seq`);”
  - The existing handshake distinguishes connection lifetimes, but D2 removes that discriminator before the app. The planned test covers a different sequence, not the same sequence reused by a replacement worker.
- Suggested change: Define an app-owned connection generation and correlate reports and asynchronous verification results by generation, sequence and immutable target. Invalidate the previous generation’s pending results on disconnect/new client, and require fresh context before Start or Resume. Specify the sequence reset policy. Add a reconnect test where the old and new requests have equal sequence numbers and the old result finishes last; it must not change the current target, display or verification eligibility.
- /fix decision: Accepted (verified: `seq` was the only discriminator at D4 and D2 strips the host's per-connection nonce before the app, so a reloaded extension can reuse a `seq`) — D4 adds an app-owned `conn_gen` bumped on every new pipe client, `seq` restarting per connection, results applied only when `(conn_gen, seq, target)` is still current, and a new connection clearing the bound report so Start/Resume need a fresh report. Siblings: Tasks 3.2, 4.2, 4.5, matrix row (same-`seq` earlier-connection result).

##### Practicality / feasibility / sequencing — PR-MED-002: Snapshot deduplication can suppress state needed by a replacement worker

- Plan section: D2; Tasks 4.5, 5.5 and 6.2.
- Materiality: build-affecting
- Why it matters: Leave the app idle after publishing its allow-list and an Unreviewed reminder, then reload the extension. The replacement worker has no snapshot, but the app remains alive with its previous “last push.” With no live recording to pause, the application snapshot can remain unchanged. Calling the same change-only `publish()` then sends nothing, leaving the replacement worker without the allow-list or reminder. Re-requesting state does not resolve this under the stated unconditional “only if different” rule.
- Current plan text:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:394`: “a FULL snapshot of the app's view, built by one `build_state()`, compared with the last push, and sent only if different. The poll, the events and every (re)connect call the same `publish()`.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:981`: “State is re-requested after a worker restart.”
- Evidence:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:959`: “Verification: restart → banner → review opens the right session; a service-worker restart re-renders the banner from `state`; a delayed click after the entry was removed or replaced is refused.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:465`: “Content scripts are declared for `https://*.cliniko.com/*` but stay inert until their host is in the allow-list of the first `state`.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:427`: “PROCESSING / QUEUED / IDLE → no-op.”
  - `desktop/src/scribe_desktop/native_host.py:156`: `session = HostSession()`
  - A replacement host connection does not restart the app’s publisher, and the specified idle pause handling supplies no state change that guarantees publication.
- Suggested change: Scope the last-sent snapshot to each connection, resetting it when a client connects, or explicitly force a full snapshot on every new connection and state request. Keep change-only publication for ordinary polling. Extend the restart test to assert delivery with an unchanged idle snapshot, an existing reminder and no intervening application-state change.
- /fix decision: Accepted (verified: D2's `publish()` compared against one app-wide last push, so an idle unchanged app sends nothing to a reloaded worker) — the last-sent snapshot is per pipe connection and cleared on connect, so every new connection gets a full snapshot; the extension re-requests by reconnecting (no new message type). Siblings: Task 6.2 (+ the idle-reload verification case).

PEER-PLAN-ROUND-3 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 2 / LOW 0; build-affecting 2 / record-only 0 / invalid 0).

- /fix notes (composer, plan-review mode): each amendment re-read from disk; sibling sweep (D2, D4, D5's new-client pause unchanged, Tasks 3.2/4.2/4.5/6.2, matrix) by exact-unique scripted replacements outside the log; the phrase "stale seq dropped" confirmed absent outside the log; Task 3.6's "stale seq" row label kept (it now covers both cases).

### Round 4 - 2026-09-27 - cliniko-workflow-safeguards plan, independent cross-family codex plan peer-review (round 4)

- Round status: Closed (1 accepted, 0 rejected; amended in place)
- Source: Codex plan peer-review
- Recorded by: composer (transcribed verbatim from the read-only peer's stdout, `.cursor/loops/cliniko-safeguards-plan-peer-r4.log`)
- Materiality: 1 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: 096f3e4 + working-tree plan
- Files read:
  - Full `.cursor/plans/plan-cliniko-workflow-safeguards.md`, including rounds 1–3 dispositions; `.agents/skills/peer-review/SKILL.md`; scoped `AGENTS.md`, `PLAN.md`, and `docs/lessons.md`.
  - Named HEAD symbols in `desktop/src/scribe_desktop/`: `session.py`, `session_store.py`, `app.py`, `benchmark.py`, `logging_setup.py`, `secure_storage.py`, `native_host.py`, `protocol.py`, `framing.py`, `transcription.py`; UI `session_screen.py`, `main_window.py`, `recovery.py`, `models.py`, `transcript.py`.
  - Extension `manifest.ts`, `connection.ts`, `background.ts`, `protocol.ts`, `package.json`; protocol fixture metadata and inventory.
  - `desktop/pyproject.toml`; socket-detection helper and integration-leg inventory in `desktop/tests/test_integration_no_sockets.py`; `.github/workflows/ci.yml`.
  - Scoped security-document excerpts, shipping-gate documentation, and design-system consent/microcopy.
- Finding verification: 6 candidates / 5 dropped / 0 downgraded. Overlapping observations deduplicated. Dropped candidates were covered by existing lifecycle/custody requirements or lacked a demonstrable ordering defect. Static review only; no files written, tests run, or builds run.

#### Findings

##### Unstated assumptions — PR-MED-001: Clinic-key changes do not invalidate pending verification

- Plan section: D4, D9–D10; Tasks 2.1b, 2.2, 3.2 and 4.5.
- Materiality: build-affecting
- Why it matters: Start verification, then replace the clinic’s key while Chrome remains on the same note and connection. The old result still satisfies the amended connection/sequence/target check and can restore verified eligibility under the previous credential or practitioner configuration. Removing the clinic likewise does not explicitly invalidate its pending result. Because verification makes several requests and credentials are retrieved per call, replacement can also mix credential generations within one verification. Round 3 closes connection replacement, but its result-application contract does not cover this independently mutable dependency.
- Current plan text:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:414`: “Each verification carries the `(conn_gen, seq, clinic_host, patient_id, note_id)` it answered, and is applied only if that is still the latest report of the CURRENT connection for the same target”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:453`: “The key is read from Credential Manager once per client call and dropped after.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:915`: “Validate / Replace key / Remove, each with a named status line. Remove needs a second confirming click.”
- Evidence:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:409`: “its practitioner link equals the clinic's practitioner id.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:987`: “A `context` for a note triggers `verify_note_context` off the GUI thread, marshalled back, and applied only when its `(conn_gen, seq, target)` is still current (D4); results from an earlier connection are dropped.”
  - `desktop/src/scribe_desktop/secure_storage.py:48`: `keyring.set_password(self._service(clinic_id), self._check_name(secret_name), value)`
  - `desktop/src/scribe_desktop/secure_storage.py:51`: `return keyring.get_password(self._service(clinic_id), secret_name)`
  - `desktop/src/scribe_desktop/secure_storage.py:55`: `keyring.delete_password(self._service(clinic_id), secret_name)`
- Suggested change: Bind verification to a clinic/credential revision as well as connection and target. Check that revision across requests and before applying results, or serialize clinic mutations across verification. Replace/Remove must invalidate existing verification and associated cached outcomes. Define equivalent commit ordering for asynchronous Validate operations. Preserve D9’s per-call credential release. Add delayed-result tests covering key replacement and removal, including replacement between verification requests; stale work must not restore verification, display data or a removed registry entry.
- /fix decision: Accepted (verified: the round-3 result-application key had no credential dimension and D9 read the key "once per client call" without defining a call, while `secure_storage.py:48/55` lets Replace/Remove land at any time) — D9 defines one verification or Validate as ONE client call sharing one key read, adds a per-clinic in-memory `clinic_rev` bumped on Replace/Remove/registry edit and checked at GUI-thread commit, and Replace/Remove clear that clinic's verification outcome. Siblings: D4 application rule, Tasks 2.2 (+ delayed-result verification), 3.2, 4.5.

PEER-PLAN-ROUND-4 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 0; build-affecting 1 / record-only 0 / invalid 0).

- /fix notes (composer, plan-review mode): each amendment re-read from disk; sibling sweep (D4, D9, D10 unchanged, Tasks 2.2/3.2/4.5) by exact-unique scripted replacements outside the log.

### Round 5 - 2026-09-27 - cliniko-workflow-safeguards plan, independent cross-family codex plan peer-review (round 5)

- Round status: Closed (1 accepted, 0 rejected; amended in place)
- Source: Codex plan peer-review
- Recorded by: composer (transcribed verbatim from the read-only peer's stdout, `.cursor/loops/cliniko-safeguards-plan-peer-r5.log`)
- Materiality: 1 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: 096f3e4 + working-tree plan
- Files read:
  - Full `.cursor/plans/plan-cliniko-workflow-safeguards.md`, including rounds 1–4 dispositions; `.agents/skills/peer-review/SKILL.md`; scoped `AGENTS.md`, `PLAN.md`, and `docs/lessons.md`.
  - Named symbols in `desktop/src/scribe_desktop/`: `session.py`, `session_store.py`, `app.py`, `benchmark.py`, `logging_setup.py`, `secure_storage.py`, `native_host.py`, `protocol.py`, `framing.py`, `transcription.py`; UI `session_screen.py`, `main_window.py`, `recovery.py`, `models.py`, `transcript.py`.
  - Extension `manifest.ts`, `connection.ts`, `background.ts`, `protocol.ts`, `package.json`; protocol fixture metadata and inventory.
  - `desktop/pyproject.toml`; socket-detection helper and integration-leg inventory; `.github/workflows/ci.yml`.
  - Scoped security-document excerpts, shipping-gate documentation, and design-system consent/microcopy.
- Finding verification: 8 candidates / 7 dropped / 0 downgraded. Round 4’s single credential read and revision-bound result commit address its reported race. Other candidates were covered, concerned fixed rather than independently mutable settings, or lacked a concrete defect. Static review only; no files written, tests run, or builds run.

#### Findings

##### Coverage — PR-MED-001: Removing a clinic does not revoke its already-active page context

- Plan section: D5, D9–D10, D13; Tasks 2.2, 6.2–6.3.
- Materiality: build-affecting
- Why it matters: Remove the bound clinic while its treatment-note tab remains open without navigation. Round 4 clears verification and rejects pending results, but neither invalidates the existing bound report nor defines deactivation of an already-authorised page script. The recording can remain active, and the old matching report can still satisfy the stated Resume predicate. Previously rendered patient data and block controls also have no defined removal path. Publishing a smaller allow-list alone does not specify these transitions. Existing sender checks reject commands from the removed host; this finding concerns retained app context and presentation, not a bypass of those checks.
- Current plan text:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:454`: “Replace and Remove also clear that clinic's current verification outcome, so Start needs a fresh verification under the new key; a removed clinic's pending work can never restore its registry entry.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:459`: “The allow-list sent to Chrome is exactly the registry's hosts.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:466`: “Content scripts are declared for `https://*.cliniko.com/*` but stay inert until their host is in the allow-list of the first `state`.”
- Evidence:
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:428`: “Resume (panel, desktop button, hotkey) is refused for a linked session while the pipe is down or the latest bound report is stale or mismatched, and the reason is named.”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:1072`: “`tabs.onUpdated`/`onActivated`/`onRemoved` and `windows.onFocusChanged` drive `seq`-numbered `context` reports”
  - `.cursor/plans/plan-cliniko-workflow-safeguards.md:1081`: “The script is inert until allow-listed.”
  - `extension/src/manifest.ts:14`: `host_permissions: ["https://*.cliniko.com/*"],`
  - Removing a registry entry does not change this wildcard permission, navigate the stationary tab, or satisfy a specified D5 pause trigger.
- Suggested change: Define clinic removal as an explicit revocation event. Invalidate affected bound reports and Resume eligibility on the GUI thread, pause an affected linked recording, and explicitly reset already-injected scripts for removed hosts: remove their frame/block and patient display data, stop reporting, and retain the existing command rejection. Require fresh authorised context before reactivation. Add tests for removing the bound clinic without navigation, a paused session attempting Resume after removal, and removal of another clinic leaving the current session unchanged.
- /fix decision: Accepted with a narrower fix than suggested (verified: round 4 cleared verification on Remove but left the bound report and the already-injected page script untouched, and `manifest.ts:14`'s wildcard host permission does not change on Remove). Instead of a revocation path that pauses a live recording, D10 REFUSES Remove while the live session is linked to that clinic (the practitioner finishes or discards first), so no live recording is ever stranded; D13 defines teardown of page scripts for a host that leaves the allow-list (frame, block, names removed; reports stopped; reactivation only via a fresh allow-list and report). Unreviewed sessions of a removed clinic stay reviewable/copyable with write-back refused. Siblings: Task 2.2 (+ refusal and other-clinic-unchanged verification), Task 6.3, extension test list.

PEER-PLAN-ROUND-5 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 0; build-affecting 1 / record-only 0 / invalid 0).

- /fix notes (composer, plan-review mode): each amendment re-read from disk; sibling sweep (D10, D13, Constraint 6 unchanged, Tasks 2.2/6.3, extension tests) by exact-unique scripted replacements outside the log.
- Pass status: CAP REACHED (5 of 5) without a zero-build-affecting round; the trend was 5 → 3 → 2 → 1 → 1, every finding MED or above accepted and amended, no CRIT, HIGH only in round 1. Continuation is the practitioner's call.

### Round 6 - 2026-09-27 - cliniko-workflow-safeguards plan, independent cross-family codex plan peer-review (round 6)

- Round status: Closed
- No new findings this round
- Source: Codex plan peer-review
- Recorded by: composer (transcribed verbatim from the read-only peer's stdout, `.cursor/loops/cliniko-safeguards-plan-peer-r6.log`)
- Materiality: 0 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: 096f3e4 + working-tree plan
- Files read:
  - Full `.cursor/plans/plan-cliniko-workflow-safeguards.md`, including rounds 1–5 dispositions; `.agents/skills/peer-review/SKILL.md`; scoped `AGENTS.md`, `PLAN.md` and `docs/lessons.md`.
  - Named HEAD symbols in `desktop/src/scribe_desktop/`: `session.py`, `session_store.py`, `app.py`, `benchmark.py`, `logging_setup.py`, `secure_storage.py`, `native_host.py`, `protocol.py`, `framing.py`, `transcription.py`; UI `session_screen.py`, `main_window.py`, `recovery.py`, `models.py`, `transcript.py`.
  - Extension `manifest.ts`, `connection.ts`, `background.ts`, `protocol.ts`, `package.json`; protocol fixture metadata and inventory.
  - `desktop/pyproject.toml`; socket-detection helper and integration-leg inventory in `desktop/tests/test_integration_no_sockets.py`; `.github/workflows/ci.yml`.
  - Scoped excerpts of `docs/security/{threat-model,data-flow-map,retention-schedule,intended-use}.md`, `docs/testing/shipping-gate.md` and `docs/design-system.md`.
- Finding verification: 4 candidates / 4 dropped / 0 downgraded. Candidates concerned offline linkage, removal interacting with `resume_previous`, teardown interacting with retained reminder references, and abbreviated task wording. Re-reading the governing contracts established coverage or insufficient evidence of a build defect. Static review only; no files written, tests run or builds run.

#### Findings

None across the five plan-review lenses.

Round 5’s guard covers `unverified_offline` recordings because they retain an encounter context. Removing another clinic cannot remove the live session’s navigation destination. Page-script teardown is consistent with retaining Unreviewed references for desktop review and copy.

The combined rounds 1–5 amendments produced no verified build-affecting contradiction across the decisions, tasks, validation matrix or Critical Constraints.

PEER-PLAN-ROUND-6 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0; build-affecting 0 / record-only 0 / invalid 0).

- Loop outcome (composer): CONVERGED — round 6 (a fresh one-round pass the practitioner approved after the first pass reached its cap) returned zero build-affecting findings. Six rounds total: 5 → 3 → 2 → 1 → 1 → 0, all 12 findings accepted and amended.

## Tasks
Every task's verification is the per-phase suite in `Validation / Verification` plus the test classes it names. `[executor: premium-only]` marks custody, concurrency, network-surface and security-doc work. The tier is entirely premium, so the labels record where care concentrates rather than routing.

**Order note (hardening pass).** P.1 gates only 2.1b's live route and 3.2's field assumptions. Tasks 1.1, 1.2, 2.1a, 3.1, 3.3, 4.1 and 4.2 have no Cliniko dependency and may run while P.1 is pending. Task 1.4 has no dependents and sits off the critical path.

### Phase 1 — Cliniko read client, offline-contract rewrite, feasibility check
- [ ] 🟥 1.1: **Cliniko read client** `[executor: premium-only]`
  - Files: new `desktop/src/scribe_desktop/cliniko_client.py`; `benchmark.py` (`apply_offline_env`/`assert_offline_env` handle `SSLKEYLOGFILE`); new `desktop/tests/test_cliniko_client.py`.
  - Behaviour: GET-only methods for `/user`, `/practitioners?user_id`, `/settings/public`, `/settings`, `/treatment_notes/<id>`, `/patients/<id>`, `/bookings/<id>`, exactly per D9.
  - Verification: the client test classes in Validation.
- [ ] 🟥 1.2: **Offline-contract rewrite, as a class** `[executor: premium-only]`
  - Placed here so the docs are never false once `http.client` lands.
  - Files: `desktop/pyproject.toml` (`:8`, `:91-95`); `ui/__init__.py:9`; `language_model.py:21`; the `test_integration_no_sockets.py` module docstring; `AGENTS.md` ("two sanctioned network steps"); the four security docs.
  - Docs:
    - `data-flow-map.md`: `:11-14`, `:49-51`, `:141-142`, `:487-493`, plus a NEW flow "Cliniko API reads" (what leaves: the key, ids, the contact email; what returns: names, appointment time, note metadata; memory only).
    - `threat-model.md`: `:76-78`, `:118-119`, `:1259`, plus a NEW client surface with D9's controls and residue (same-user key read; the Windows-store TLS trust in inspection roots; clipboard history).
    - `retention-schedule.md`: rows for the clinic keys in Credential Manager, `clinics.json`, the API responses (memory) and the contact email.
    - `intended-use.md`: `:3-4`, `:21-22`, `:34-39`.
  - Find every sibling with a recorded grep for "no network", "no sockets", "never the app", "ONLY sanctioned", "sanctioned network".
- [ ] 🟥 1.3: **Read-only feasibility script**
  - Files: new `scripts/probe-cliniko.py` (built on 1.1's client; the key via `getpass`, never argv or env).
  - Behaviour: prints ONLY structure:
    - status per call;
    - field presence;
    - `draft`/`finalized_at` null-ness;
    - whether booking and template links exist;
    - whether the note practitioner equals the key user's practitioner (a boolean);
    - whether `/settings/public` answered;
    - the note `content` shape with answers reduced to empty/non-empty.

    Never a name, id value, answer text or the key.
  - Verification: a unit test on the redaction with a fixture response.
- [ ] 🟥 P.1: **Practitioner runs the feasibility check on both clinics** (practitioner-owned)
  - Open a patient's treatment note in each clinic, then run `.venv\Scripts\python.exe scripts\probe-cliniko.py` from a normal terminal at the repo root.
  - Paste the printed structure (no patient data) into this task's Done note.
  - Record which D10 subdomain route applies, and what the booking, template and practitioner links showed (feeds D3/D4; `booking_id` stays optional either way).
- [ ] 🟥 1.4: **Copy-to-Cliniko flag flip and shipping-gate reframing** — COMPOSER MUST-PAUSE, off the critical path
  - Ask the practitioner, verbatim: "Flip COPY_TO_CLINIKO_ENABLED to True per your 2026-09-27 decision (the shipping gate becomes a quality measurement)?"
  - The planning-time edit was blocked by the permission classifier as security-weakening. The practitioner may need to approve the permission prompt, or make the two-line edit themselves (`ui/models.py:446`, `test_ui_screens.py:3534`), after which the executor does the rest.
  - Files:
    - `ui/models.py` (flag plus decision comment, D12);
    - `desktop/tests/test_ui_screens.py` (rename `test_default_copy_binding_ships_disabled` → `…_ships_enabled`, `is True`, and assert an unratified note under the default binding is not copyable);
    - `ui/note.py` docstring (`:122`);
    - `docs/testing/shipping-gate.md` (status: a quality measurement, 2026-09-27; "What the gate decides" and "What a decision flips" reworded);
    - `docs/design-system.md` (`:221-229`), `threat-model.md` (`:361-363`), `data-flow-map.md` (`:209`);
    - `AGENTS.md`, `CHANGELOG.md`;
    - `plan-phase3a-note-pipeline.md` (a dated note on Task 9.1).
  - Derive the site list with the gate doc's own grep.

### Phase 2 — Clinic keys
- [ ] 🟥 2.1a: **Clinic record type and loader** (no network)
  - Files: new `clinics.py` (`ClinicRecord`, `ClinicRegistry` load/save fail-closed, `allow_list()`); tests.
- [ ] 🟥 2.1b: **Key validation and storage** `[executor: premium-only]`
  - Files: `clinics.py` (`validate_and_store`, `remove`, `confirm_subdomain_from_note`); tests.
  - Behaviour: D10's validation through 1.1, the key via `SecureStorageProvider`, and typed results or named refusals.
  - Verification: the registry test classes, including zero calls at startup or idle.
- [ ] 🟥 2.2: **Clinics tab**
  - Files: new `ui/clinics.py`; `ui/main_window.py`; `ui/models.py` (copy constants); `AGENTS.md` Local Run Steps (the Clinics tab step).
  - Behaviour:
    - A password-masked key field, cleared with `setText("")` after Validate, which also clears undo.
    - A contact-email field.
    - Validate / Replace key / Remove, each with a named status line. Remove needs a second confirming click, and is refused while the live session is linked to that clinic (D10). Replace and Remove bump the clinic's `clinic_rev` (D9) and clear its verification outcome.
  - Verification (clinic mutation): a delayed verification or Validate result after Replace key, after Remove, and with Replace landing between its requests — none restores verified eligibility, display data or a removed registry entry. Remove of the live session's clinic is refused; Remove of the OTHER clinic leaves the live session unchanged.
    - The clipboard-history advice line.
    - Nothing validates at startup.
  - Verification: offscreen UI tests with an injected registry.

### Phase 3 — Consent, encounter and write-back guard `[executor: premium-only]`
- [ ] 🟥 3.1: **Encounter and consent types**
  - Files: new `encounter.py`; `session.py` (`RecordingSession` fields); `logging_setup.py` (tripwire); the Key Findings test sites for `RecordingSession` (`test_session_types.py:178` rewritten with a typed context, the bare constructions, `test_ui_screens.py:2711`).
  - Behaviour: D3. Decide and record here whether `consent` is required on the model or only at `start()`.
- [ ] 🟥 3.2: **Note verification**
  - Files: `encounter.py` (`verify_note_context`); tests.
  - Behaviour: D4's check, its three outcomes, results tagged with `(conn_gen, seq, target, clinic_rev)` and per-note throttling, through 1.1 with an injected transport. Display strings are returned separately and never persisted.
- [ ] 🟥 3.3: **`start()` with consent, target and `encounter.enc`; the desktop consent tick**
  - Files:
    - `session.py` (`start(device_id, *, consent, context=None)`);
    - `session_store.py` (write/read `encounter.enc`, D11);
    - `ui/models.py` (`SessionControllerLike.start`);
    - `ui/session_screen.py` — the desktop consent checkbox above Start (never pre-ticked, cleared after Start), the "Not linked to a Cliniko note" label, and a new `start_linked(consent, context)` slot beside `on_start()` for Task 4.5;
    - the design-system entry for the desktop consent cue.
  - Callers:
    - the 55 in-process `start(0)` sites (via a shared helper);
    - the 4 child-script strings in `test_integration_no_sockets.py` (edited in place);
    - the 2 `start(99)` sites;
    - `FakeController` (`test_ui_screens.py:163-211`).
  - Behaviour: `start()` refuses without consent; `encounter.enc` is written on every start between `wrap_key_to_file` and `SessionChunkStore.create`. `start()` also registers the session in D2's reference registry (a random opaque `session_ref`, never persisted, never the directory name) that D2's session-bound commands match.
  - Verification: the consent refusal on both paths, and the ordering/crash test.
- [ ] 🟥 3.4: **Encounter on recovery and checkout**
  - Files: `session_store.py`, `ui/recovery.py`, `ui/models.py` (`RecoverableSessionInfo.has_transcript`/`has_note`/`has_encounter` by stat), `test_ui_models.py:184-265`.
  - Behaviour:
    - `encounter.enc` is decrypted only on checkout (spy test: the list, the sweep and the periodic refresh never decrypt).
    - A checked-out linked session re-verifies (D4) before it counts as linked.
    - Missing or undecryptable means unlinked.
    - `_describe` shows linked/unlinked from the stat, never a decrypted clinic.
- [ ] 🟥 3.5: **Write-back guard**
  - Files: `encounter.py` (`writeback_context(target) -> VerifiedTarget | Refusal`, where `target` is a live session OR a checked-out recovered/Unreviewed session's decrypted encounter plus its re-verification result).
  - Behaviour: each refusal is named. This is Phase 4's only entry to a write target. Both paths are tested.
- [ ] 🟥 3.6: **Cross-patient matrix — encounter and custody cases**
  - Files: new `desktop/tests/test_cross_patient.py`.
  - Behaviour: the matrix rows that need no pipe or Chrome (mismatches, other clinic, final note, wrong practitioner, missing or corrupt `encounter.enc`, unlinked, unverified, stale `seq`). Every case refuses its named operation; the positive `unverified_offline` Start case (records, write-back refused) lands here too.

### Phase 4 — Pipe, protocol v2, relay and state publisher `[executor: premium-only]`
- [ ] 🟥 4.1: **Protocol v2**
  - Files: `protocol/fixtures/` (meta 2/2, valid and invalid fixtures including bad ids, over-length values, a missing nonce, a `not_cliniko` report with a host (invalid), a `closed` report, and a session-bound command without `session_ref` (invalid), README); `protocol.py` (per-type payload models, `NONCE_REQUIRED` extended); `extension/src/protocol.ts`; both mirror tests.
  - Behaviour: D2. A refusal arrives in `state.last_refusal`.
- [ ] 🟥 4.2: **Named-pipe server in `scribe-app`**
  - Files: new `pipe_server.py`; `app.py` (lifecycle); `desktop/pyproject.toml` (mypy overrides for `win32event`/`win32gui`/`win32process`).
  - Behaviour:
    - `FILE_FLAG_FIRST_PIPE_INSTANCE` (literal `0x00080000`), `nMaxInstances=1`, `PIPE_REJECT_REMOTE_CLIENTS`, and a user-only DACL from SDDL.
    - Overlapped I/O plus a stop event, and a short-read-looping `ReadFile` adapter for `framing.read_frame`.
    - Messages are emitted only as queued Qt signals, and a new client connection is signalled as pipe loss and bumps D4's `conn_gen`.
- [ ] 🟥 4.3: **Pipe peer identity** `[decision]`
  - Default (b): session id plus the user-only DACL, with the residue documented as `app.py:76-77` does for the mutex. The residue list must name what a same-user process on the pipe can do:
    - forge a start with consent;
    - read names for chosen note ids through `state`;
    - hold the only pipe slot;
    - drive `resume_previous` (ids only; the extension builds the URL).
  - Upgrades: (a) the host verifies the server's parent chain up to `Scripts\scribe-app.exe`; (c) the server checks the client PID's image and parent.
  - Decide after: 4.2 works and the launcher/redirector chain is measured on this host.
  - Blocks: 4.4's connect contract. "Pipe exists but server unverified" is a hard error under every option.
- [ ] 🟥 4.4: **Two-way native-host relay**
  - Files: `native_host.py`; `desktop/tests/test_native_host*.py`; the no-sockets host legs.
  - Behaviour:
    - Two threads with a stdout lock. The host answers hello/ping itself.
    - While the pipe is absent it pushes `state{app_running:false}` and keeps re-waiting (bounded `WaitNamedPipe` per attempt, no exit).
    - It stamps and strips the nonce per D2 and validates envelopes. Its logging never records a relayed payload.
    - It exits on Chrome-side EOF.
  - Verification: the existing handshake-with-no-app leg, plus a new app-pipe-open no-sockets leg.
- [ ] 🟥 4.5: **App bridge, state publisher and the desktop linked-session display**
  - Files: new `ui/bridge.py`; `session.py` (a `recorded_seconds` accessor from chunk count, excluding pauses, plus the live-failure accessor for D7); `ui/models.py` (`SessionControllerLike`); `ui/main_window.py`; `ui/session_screen.py`.
  - Behaviour:
    - `command` goes to the SessionScreen slots (`start_linked` with the target and verification-outcome check, `on_pause`, `on_resume`, `on_finish`, `on_discard` with the confirm flag, `open_review`). Every command except `start` and `pause` is refused BEFORE its slot runs unless its `session_ref` matches (D2), so a stale Discard/Finish/Resume can never act on a newer session. A missing microphone becomes a named refusal.
    - One `publish()` builds the full `state` snapshot and sends it on change.
    - A `context` for a note triggers `verify_note_context` off the GUI thread, marshalled back, and applied only when its `(conn_gen, seq, target)` is still current (D4) and its `clinic_rev` is unchanged (D9); results from an earlier connection or an older key are dropped.
    - A linked live session re-verifies on pipe reconnect.
    - The Session screen shows the patient, clinic, verification line, block reason, hotkey and spoken-pause status, and warnings.

### Phase 5 — Pause rule, resolution, back-to-back and Unreviewed `[executor: premium-only]`
- [ ] 🟥 5.1: **ContextEvaluator and `pause_for`**
  - Files: new `context_rules.py`; `ui/bridge.py`; `ui/main_window.py` (`PBT_APMSUSPEND` via `nativeEvent`).
  - Behaviour: D5 exactly, including `pause_for` per session state, sleep, a new-client pipe loss, resume refused without a current matching report, and re-binding by ids. Parameterised-tested against the D5 table.
- [ ] 🟥 5.2: **Resolution block**
  - Files: `context_rules.py`, `ui/bridge.py`, `ui/session_screen.py`.
  - Behaviour: Flow 3, with a two-step Discard. `resume_previous` asks the extension to navigate by ids and resumes only on a matching report. The desktop Resume and the hotkey honour the block.
- [ ] 🟥 5.3: **Back-to-back flow**
  - Files: `ui/bridge.py`, `ui/session_screen.py`, `ui/main_window.py` (`_on_session_started`).
  - Behaviour: D6: "Finishing <A>…"; Start at QUEUED unless the lease is held ("Save or cancel <A>'s note review to start"); retirement fills the reminder index (a list per note, D6) from the in-memory context.
  - Measure A's tail (timing only) in the Done note.
- [ ] 🟥 5.4: **Unreviewed review reopen** `[decision]`, then build
  - Options:
    - (a) a new controller `adopt_queued(directory)` that unwraps the key and reinstalls the session as the live QUEUED session, refused while any session is active. This is a NEW custody consumer, so enumerate every consumer (lessons 2026-08-12).
    - (b) extend the generation lease and `with_generation_custody` to recovered checkouts.
  - Decide after: 5.3 lands.
  - Then build, in `ui/recovery.py` (the Unreviewed section), `ui/models.py`, `ui/main_window.py` and `session.py`:
    - rows with a transcript offer "Open for review", never "Resume processing";
    - with no `note.enc`, review opens from `transcript.enc` with generate, save and copy available; with a `note.enc`, it opens the saved note through `session_store.read_note` with its edits, copy available and generation only as an explicit "Regenerate (replaces the saved note)"; a note that fails verification is a named refusal on the row, never a silent regenerate (D6);
    - the checkout is released when the review ends (fixing today's hold-until-restart at `main_window.py:348-354`);
    - the expiry warning (2 h, the sweep's timestamp helpers) and the on-close expiry list.
- [ ] 🟥 5.5: **Reminder on reopening a note**
  - Files: `ui/bridge.py`.
  - Behaviour: a `context` for a note in the index sets the banner in `state`, carrying the banner target's `session_ref` from D2's registry (refs for indexed sessions are minted at startup reconstruction and kept through retirement). `open_review` resolves that exact ref and brings the desktop window forward on that session, flashing the taskbar where Windows refuses focus.
  - Verification: restart → banner → review opens the right session; a service-worker restart re-renders the banner from `state`; a delayed click after the entry was removed or replaced is refused.
- [ ] 🟥 5.6: **Cross-patient matrix — context cases**
  - Files: `test_cross_patient.py`.
  - Behaviour: the remaining matrix rows (target/`state_rev` mismatch, stale-`session_ref` Discard/Finish/Resume after B starts, bound-tab departure and closure vs a separate non-Cliniko tab, a non-bound or stale tab, a replayed report, Resume previous while B is shown, resume with the pipe down, a second pipe client, and the two-recordings-one-note reminder case), reusing 5.1's table. Zero failures across 3.6 + 5.6 is PLAN.md Phase 5's completion evidence.

### Phase 6 — Chrome extension UI
- [ ] 🟥 6.0: **Extension test environment**
  - Get the practitioner's authorisation, then add a pinned DOM-environment devDependency to `extension/package.json` and the Vitest config, with a `chrome.*` fake module.
- [ ] 🟥 6.1: **Manifest and build**
  - Files: `extension/src/manifest.ts`, `extension/vite.config.ts`, a stub `extension/src/page.ts`.
  - Behaviour: `sidePanel` and `scripting` permissions (scripting limited to Cliniko hosts), `side_panel.default_path`, `content_scripts` for `https://*.cliniko.com/*`, no `tabs` permission. A manifest pin test.
  - `AGENTS.md` Local Run Steps: rebuild, reload, and fully restart Chrome after manifest changes.
- [ ] 🟥 6.2: **Background: tab tracking, reports, relay, badge and re-injection**
  - Files: `extension/src/background.ts`, `extension/src/connection.ts`, new `extension/src/context.ts`.
  - Behaviour:
    - `onMessage` is rewritten: only `error` disconnects, and v2 messages are routed.
    - `tabs.onUpdated`/`onActivated`/`onRemoved` and `windows.onFocusChanged` drive `seq`-numbered `context` reports; the URL parser handles the note, login and other pages. An untracked non-allow-listed tab is never reported; a tab already reported that navigates off the allow-list sends `page: not_cliniko` with no host or URL (the missing `tabs` permission leaves its URL unreadable, which is itself the signal), and `onRemoved` for a tracked tab sends `page: closed` (D2).
    - Each tab gets only its own host's slice of `state`.
    - Command sender checks.
    - `resume_previous` navigation is built from the allow-list and ids.
    - The badge replaces `BADGES`.
    - Page-script re-injection runs on `onInstalled`.
    - State is re-requested after a worker restart by reconnecting (D2: the app sends a full snapshot on every new pipe connection). Verification: an idle app with an existing reminder and allow-list, no state change, extension reloaded — the new worker receives both.
- [ ] 🟥 6.3: **Page script: frame, block and URL heartbeat**
  - Files: `extension/src/page.ts`.
  - Behaviour: D1's frame and block in a closed shadow root, rendered with `textContent` only. Buttons act on `isTrusted` clicks and carry the `session_ref` of the `state` the block was rendered from; Discard needs its second click. The script is inert until allow-listed, and returns to inert (frame, block and patient data removed; reports stopped) when its host leaves the allow-list (D13). It sends only `location.href` changes to the background (the SPA backstop; the background stays the single `context` reporter) and never reads Cliniko's DOM.
- [ ] 🟥 6.4: **Side panel**
  - Files: new `extension/src/panel.html`, `extension/src/panel.ts`.
  - Behaviour: D1's five layouts plus the banner, `textContent` only, the consent tick rules, Start sending `command{start, consent, target, state_rev}`, every other session command carrying the `session_ref` from the `state` it was rendered from (D2), and the refusal line from `last_refusal`.
  - Spike: can `sidePanel.open()` run from the action click? Record the result.
- [ ] 🟥 6.5: **Extension tests**
  - Files: `*.test.ts`.
  - Behaviour: Validation's extension classes (layouts, the markup-name fixture, host scoping, trust checks, re-injection, badge, manifest pin, no names in storage, no key in payloads).

### Phase 7 — Hands-free and warnings
- [ ] 🟥 7.1: **Global hotkey** `[executor: premium-only]`
  - Files: `ui/main_window.py` (`nativeEvent`), new `hotkey.py`.
  - Behaviour: D7. The chord is chosen here (AltGr-safe); pause/resume go through `pause_for` and the guarded resume; a registration failure shows in the desktop and in `state`.
- [ ] 🟥 7.2: **Spoken pause**
  - Files: new `voice_commands.py`; a slot on `TranscriptScreen.live_window` wired in `ui/main_window.py`.
  - Behaviour: D7: the leading-boundary matcher, ignoring a phrase whose first word starts before the last resume's captured-audio cutoff (word timestamps, not window end), the "unavailable" status through 4.5's accessor, and the desktop cue on every pause.
- [ ] 🟥 7.3: **New-consultation warning**
  - Files: `voice_commands.py`, `ui/bridge.py`.
  - Behaviour: D8. A warning only, in the panel and the desktop, test-pinned.

### Phase 8 — Security docs for the new surfaces and the live smoke
- [ ] 🟥 8.1: **Security docs for the pipe, Chrome and encounter surfaces, as one class** `[executor: premium-only]`
  - `data-flow-map.md`: flows for the pipe, `context`/`state`, and the patient name into Chrome memory (per-tab scoping). Replace the "Phase 5 preview" block.
  - `threat-model.md` surfaces:
    - the pipe (4.3's decision and the same-user residue list);
    - the page script and panel (D13: cue, not control; `textContent`; `isTrusted`; sender checks);
    - `encounter.enc`;
    - the pause rule's residues (in-page expiry modal, pre-navigation speech and latency, the page hiding the frame);
    - one Chrome profile;
    - Chrome crash minidumps possibly holding names.
  - `retention-schedule.md`: `encounter.enc` (consent, destroyed with the session — durable evidence deferred to PLAN Phase 6), the reminder index (memory).
  - `docs/design-system.md`: the panel, frame, block, the recording-consent pre-tick exception, and the two-step Discard.
  - `AGENTS.md` Subsystem Documentation pointers.
  - `protocol/fixtures/README.md`.
  - `PLAN.md`:
    - voice/hotkey "stop" means pause only;
    - flow step 9 ("open the draft") is met because the note is already open;
    - Phase 5 delivered with the read-only API;
    - `ConsentAttestation` as built.
  - `CHANGELOG.md`.
- [ ] 🟥 P.2: **Practitioner live smoke** (practitioner-owned)
  - The Validation practitioner-run list, on both clinics.
  - Record the outcomes (no patient data) in the Done note.

### Hardening stage
- [ ] 🟥 H1: `/review-loop` to convergence over Phases 1–8 as one surface
- [ ] 🟥 H2: `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`
- [ ] 🟥 H3: `/security-review` — log findings; same impact-tiered routing
- [ ] 🟥 H4: a cross-family codex `/peer-review`, sliced by file group:
  - client + registry + security docs;
  - custody + encounter + pipe + host;
  - extension + UI + hands-free.

  Re-check to convergence.

## Retained Follow-Up Items
(none yet — populated at completion by mechanical review of the Planning Extraction Summary)

## Follow-Up Continuation Notes
- **Next focus after this plan: the Phase 4 plan (writing the draft).** Start with the practitioner's test write moved out of P.1, then `PATCH` into the verified note through `writeback_context`, the ledger, reconcile, and auto-complete.
- **Out of scope for that plan too:** POST of a second note, calendar Start, true overlap.
- **Decisions that still apply:** D2 (protocol), D3/D4 (encounter and verification), D9 (client contract), D10 (registry), D11 (`encounter.enc`), D13 (page-script trust), and the Critical Constraints.
- **Must not be rediscovered:**
  - `urllib` bypasses the host pin (redirects, proxies).
  - The venv `python.exe` is a redirector (4.3).
  - The periodic-decrypt class.
  - No Cliniko call at startup or idle keeps the no-sockets legs at zero.
  - One Cliniko note can own several recordings (D6's reminder list). The Phase 4 write must decide how a second session's note lands in a draft the first already filled (refuse, append, or ask); never overwrite silently.

---
*Plan saved to: .cursor/plans/plan-cliniko-workflow-safeguards.md*
*To resume in a new session: run /start-session, then /load-plan*
*State-once convention: cross-section contracts live in Design Decisions (D1–D12) and Critical Constraints; other sections point to them.*
