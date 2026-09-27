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
  - Risk if assumption becomes false: key validation or note verification needs another route. The Task 1.3 `[decision]` covers the subdomain source.
  - Trigger for revisit: Task P.1.
  - Recommended next action: P.1.
- **The processing tail after Finish is short (seconds) when live transcription ran**
  - Why accepted for now: the live transcriber transcribes during recording; only the tail and the speaker pass remain.
  - Risk if assumption becomes false: B waits noticeably. Revisit true overlap (Excluded).
  - Trigger for revisit: Task 5.3's measurement and the Task P.2 smoke.
  - Recommended next action: measure in 5.3.
- **Cliniko changes the page URL without a full page load, and `tabs.onUpdated` reports every such change on a host-permissioned tab**
  - Why accepted for now: that is Chrome's documented behaviour for history-state changes.
  - Risk if assumption becomes false: a missed change means a missed pause. Task 6.2 adds a content-script URL heartbeat as a backstop.
  - Trigger for revisit: Task P.2.
  - Recommended next action: include the backstop.

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
  - `write_note` (`:774-848`) is the encrypted-sidecar precedent for `context.enc`; it uses no AAD, so `context.enc` must take a distinct AAD.
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
- **Decrypt `context.enc` only on checkout, or once when a session joins the Unreviewed list.** Never in `list_recoverable_sessions` or on the 15-minute sweep: that is the periodic-decrypt class (`docs/lessons.md` 2026-09-18).
- **No Cliniko call at startup or idle**, only on a context report, a Clinics-tab Validate, or an Unreviewed-list open. This keeps `test_scribe_app_process_has_no_sockets` at zero.
- **Tests never depend on host state** (lessons 2026-09-24). The Cliniko transport, the pipe, the hotkey and Credential Manager are injected in unit tests.
- **Security-doc claims are control claims** (lessons 2026-08-14). Rewrite every "no network" sibling as a class (grep, not the cited line), and budget a cross-family peer pass.
- **MSIX virtualisation** (lessons 2026-07-28): Credential Manager entries, `clinics.json` in `%LOCALAPPDATA%` and pipe reachability from a user-launched Chrome are verified only by the practitioner's live launch (Task P.2).
- **A message describing a deferred outcome names the control that commits it** (lessons 2026-09-17). For example, "Unreviewed note — Open for review", "Write-back blocked until verified".
- **A codex peer on this repo must not create files in the repo, and should not run pytest** (lessons 2026-08-04). Slice any whole-surface codex round by file group (lessons 2026-09-25).

**Shared-helpers inventory (reuse across phases, do not re-invent)**
- `cliniko_client.ClinikoClient` + `Transport` seam (Task 1.1).
- `clinics.ClinicRegistry` (Task 2.1).
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
Open the desktop app's Clinics tab, paste a clinic's Cliniko API key and a contact email for Cliniko's User-Agent, then press Validate. The app checks the key against Cliniko: practitioner role, the practitioner record, a subdomain that matches, and a key shard that matches the clinic host. It stores the key in Credential Manager and the non-secret clinic record in `clinics.json`. Repeat for the second clinic.

### Flow 2 — A consultation
1. Open the patient's treatment note in Cliniko. The side panel shows "Checking with Cliniko…", then the patient's name, the appointment time, the clinic and "Note verified with Cliniko". If Cliniko is unreachable it shows "Not verified with Cliniko — recording allowed, writing to Cliniko blocked until verified".
2. Tick the consent box. Start recording becomes enabled; press it.
3. While recording, a red frame surrounds the Cliniko page, and the panel shows the timer, the patient, "Consent confirmed <time>", and Pause / Finish consultation. The icon badge reads REC.
4. Press Finish consultation. The panel shows "Finishing <patient>…" through the short processing tail. The session joins the Unreviewed list, and the desktop app shows its transcript and review as it does today.

### Flow 3 — Patient change mid-recording
Opening another patient's note (or leaving the note, closing the tab, logging out, or Chrome disconnecting) pauses the recording at once. The frame turns amber and a full-page block covers Cliniko, showing "Recording belongs to <A>" beside "You opened <B>", with three choices:
- **Finish previous (<A>)** finishes A's consultation.
- **Resume previous** returns the tab to A's note, and resumes only when Chrome reports A's note again.
- **Discard previous** runs the existing Discard, with its confirmation.

Nothing moves between patients.

### Flow 4 — Back-to-back patients and the Unreviewed list
After A's tail finishes, B's note can be started. A waits in "Unreviewed notes" in the desktop app and opens straight into review without re-transcribing. Reopening A's note in Cliniko later shows "Unreviewed note for <A>" with an Open for review button that brings the desktop app forward on A's review. Two hours before any unreviewed note reaches the 24 h limit, the app warns.

### Flow 5 — Hands-free and warnings
- Ctrl+Alt+P (or the chord chosen in Task 7.1) pauses or resumes from anywhere in Windows. A resume passes the same context check as the panel.
- Saying "scribe pause" pauses once the live transcriber reaches that window, a few seconds later. Resuming always needs the hotkey or a click.
- A closing phrase followed by a greeting shows a "This may be a new consultation" warning in the panel and the desktop app. It is only a warning; nothing is paused or switched.

### Flow 6 — Desktop-only fallback
The desktop Start button still works, labelled "Not linked to a Cliniko note", and requires the same consent tick. The session is copy-only and can never be written to Cliniko.

## Design Decisions
- **D1 — Side panel UI** (practitioner, 2026-09-27; four mockup directions were compared in chat; the chosen design is recorded here in words).
  - Consent and every control live in Chrome's global side panel (`chrome.sidePanel`, a new permission), never in Cliniko's DOM.
  - The only in-page elements, rendered by the page script from the app's `state` inside a closed shadow root, are:
    - (a) a 3 px frame round the viewport: red while recording, amber while paused or blocked;
    - (b) the full-page block on a context change: a dimmed page and a centred card with the two patients side by side and three buttons.
  - Panel states, in order of precedence:
    1. "Clinic Scribe is not running — open it to record" (no pipe);
    2. "This clinic is not set up — add its key in Clinic Scribe's Clinics tab";
    3. "Open a patient's treatment note to record" (any other Cliniko page);
    4. "Checking with Cliniko…";
    5. ready (name, appointment, clinic, verification line, consent checkbox, Start disabled until ticked);
    6. the unverified-offline note;
    7. Recording;
    8. Paused;
    9. "Finishing <A>…";
    10. Blocked (mirrors the block and names both patients);
    11. "Unreviewed note for <patient> — Open for review".
  - The icon badge shows REC (red), PAUSED (amber), or nothing, and "!" when the pipe is down while a session is live.
  - Copy follows `docs/design-system.md` Microcopy: plain clinical English, named actions, no exclamation marks.
  - If `sidePanel.open()` cannot be driven from the block's buttons (it needs a user gesture), the block's buttons send commands directly and the panel mirrors them; Task 6.4 spikes this.
  - Rejected: a strip inside Cliniko's layout; a corner pill alone; desktop-led.
- **D2 — Protocol v2: three new message types; the host stays a validating relay.**
  - `context` (extension→app): `{tab_id, window_id, focused, host, page: note|login|other_cliniko|not_cliniko, patient_id?, note_id?}`.
  - `command` (extension→app): `{action: start|pause|resume|finish|discard|resume_previous|open_review, consent?: {confirmed: true, text_version}}`. "Finish/Discard previous" map to finish/discard of the single live session. `resume_previous` makes the app instruct the extension to navigate the bound tab back, and the app then resumes on a matching `context`.
  - `state` (app→extension): the app's whole view state, including the allow-list, display strings, the block, reminder flags, hotkey and spoken-pause availability, and warnings. It is pushed on change and in full on every (re)connect.
  - `meta.json` becomes version 2, floor 2. Per-type payload models in `protocol.py` and `protocol.ts` (the envelope `payload` is untyped today). Fixtures stay the canonical contract, and `error` is reused.
  - The host validates envelopes with the existing `protocol.py`/`framing.py` and never interprets commands.
  - Rejected: separate "previous" message types (the single-active-session invariant makes them the plain actions).
- **D3 — Encounter model** (`encounter.py`).
  - `EncounterContext`: `clinic_id, clinic_host, patient_id, treatment_note_id, booking_id?, practitioner_id, template_id?, verification: verified|unverified_offline, verified_at?`. Ids are Cliniko int64 values kept as strings.
  - `ConsentAttestation`: `confirmed_at`, `text_version="recording-consent-v1"`, and linked-or-unlinked. The text is PLAN.md's: "I confirm the patient has consented to AI-assisted recording and documentation". It is distinct from the learning consent `CONSENT_TEXT_V3`.
  - Display strings (patient name, appointment time) are NEVER persisted. They live in app memory and are pushed in `state`.
  - `booking_id` is optional: the panel shows "No linked appointment" when it is absent.
  - Rejected: a required booking (the auto-created draft's link is unverified until P.1).
- **D4 — Verification** (`verify_note_context`).
  - One `GET /treatment_notes/<id>`. The note's patient link id must equal the URL's patient id; `draft` must be true and `finalized_at` null; its practitioner link must equal the clinic's practitioner id. Then `GET /patients/<id>` and the booking (if linked) for display only.
  - Outcomes: `verified` · `unverified_offline` (connection error, timeout, 5xx or 429: recording allowed, write-back blocked) · refusal by name (mismatch, final note, wrong practitioner, 401/403/404: Start refused and the reason shown).
  - Re-verification runs on recovery checkout and whenever the pipe reconnects to a linked live session.
- **D5 — The pause rule, evaluated only in the app** (`ContextEvaluator`). Pause when:
  - the bound tab's report has a different note or patient, or `page ≠ note`;
  - the bound tab is removed;
  - the pipe closes;
  - the FOCUSED tab of the FOCUSED window reports `page=note` for another patient or note, or `page=login`.

  Non-Cliniko tabs and `not_cliniko` reports never pause. One idempotent `pause_for(reason)` serves context, pipe loss, the hotkey and speech. Resume from the block requires a matching bound-tab report. The desktop Resume and the hotkey honour the block.
- **D6 — Back-to-back.** The single-active-session invariant is kept. While A is PROCESSING the panel shows "Finishing <A>…" and Start is disabled. When A reaches QUEUED, starting B retires A into the Unreviewed list (the existing `start()` retirement). An Unreviewed session reopens through the existing recovery checkout path plus a NEW "open for review" branch: it reads `transcript.enc` and opens the Transcript/Note review, with no re-transcription. The reminder index maps `(clinic_id, note_id) → session_id`, built by decrypting `context.enc` ONCE when a session joins the list (and once per app start for the existing ones).
- **D7 — Hands-free.**
  - The hotkey uses `RegisterHotKey` handled in `MainWindow.nativeEvent`, on the GUI thread. A registration failure is shown as a status line, never silently ignored.
  - Spoken pause tees `LiveTranscriber.on_window` in `_build_live_transcriber` into a queued signal, and a matcher for the normalised phrase "scribe pause" calls `pause_for("spoken")`.
  - The phrase stays in the transcript: the transcript is raw evidence.
  - When live transcription is off, failed or fell behind, the panel and the desktop say "Spoken pause unavailable for this recording".
  - The latency (≥ the 3 s window gap plus inference; up to about 30 s during continuous speech) is documented, not hidden.
- **D8 — New-consultation warning.** Phrase rules run over live windows: a closing phrase ("see you next week", "take care", "all done for today"…) followed within N windows by a greeting ("hi, come in", "nice to meet you", "how have you been"…). The lists and N are constants in one module, pinned by tests. The warning shows only in the panel and the desktop; it never pauses or switches.
- **D9 — Cliniko client contract** (`cliniko_client.py`).
  - Uses `http.client.HTTPSConnection` with the host built only from a validated shard (`api.<shard>.cliniko.com`, shard ∈ the documented set), port 443, and the default `ssl` context (Windows certificate store).
  - No redirects are followed and no proxy is used. Timeouts are set. The body is read up to a cap + 1 and anything over the cap is refused. JSON is parsed. The User-Agent is `Clinic Scribe (<contact email>)`.
  - Errors are typed and refused by name: `CredentialsRejected`, `NotFound`, `RateLimited(reset)`, `Unreachable`, `Malformed`.
  - Every call goes through a `Transport` protocol; tests inject a fake. The client exposes only GET methods in this plan, and the transport is only ever handed the method `"GET"`, pinned by a test.
  - The key is read from Credential Manager per call and never logged, stored elsewhere or put in exceptions.
  - The one `# noqa: TID251` sits on the `http.client` import, pinned by a test that finds exactly one such site in `src/`.
- **D10 — Clinic registry** (`clinics.py`).
  - `clinics.json` in `%LOCALAPPDATA%\ClinikoScribe\` holds non-secret records `{clinic_id, display_name, subdomain, shard, user_id, practitioner_id, validated_at}` plus the User-Agent contact email. The key lives in Credential Manager under `SecureStorageProvider(clinic_id, "cliniko_api_key")`.
  - Validation: `GET /user` (role practitioner, active) → `GET /practitioners?q[]=user_id:=` (exactly one) → the subdomain from `/settings/public` (or the Task 1.3 decision's route). The key shard must equal the host shard, and a duplicate subdomain is refused.
  - The allow-list delivered to Chrome is exactly the registry's `<subdomain>.<shard>.cliniko.com` hosts.
- **D11 — `context.enc`.** Encrypted under the session key with a distinct AAD. It is written atomically after `key.dpapi` and BEFORE `audio.enc` in `start()`, so a crash never leaves a linked recording without its binding. Discard's `rmtree` and complete→sweep GC cover it. Missing or undecryptable means unlinked (copy only).
- **D12 — Copy flag.** `COPY_TO_CLINIKO_ENABLED` flips to `True` under the practitioner's 2026-09-27 decision, and the ratification bar (`_copy_ready`) is untouched. The flip was blocked by the permission classifier during planning, so Task 1.4 confirms it with the practitioner at execution.

## Schema / Data Changes
- New `EncounterContext` / `ConsentAttestation` (pydantic, frozen, `extra="forbid"`) in `encounter.py`. `RecordingSession.encounter_context` becomes `EncounterContext | None`, and a `consent: ConsentAttestation` field is added.
- New per-session file `context.enc` (D11). No change to `audio.enc`, `transcript.enc` or `note.enc` formats.
- New `%LOCALAPPDATA%\ClinikoScribe\clinics.json` (D10), with a schema version and a fail-closed loader.
- New Credential Manager entries `ClinikoScribe/<clinic_id>` / `cliniko_api_key`.
- Protocol v2 (D2): `protocol/fixtures/meta.json` goes to 2/2, with new valid and invalid fixtures.
- The logging tripwire's field set gains the new context and consent field names (derived, not hand-listed, per lessons 2026-08-10).

## Config / Environment / Deployment Impact
- No environment variables. No new Python runtime dependency (stdlib `http.client`/`ssl`).
- A new extension devDependency for a DOM test environment (happy-dom or jsdom, pinned). This is a dev-only npm dependency, authorised by the practitioner when Task 6.5 runs.
- Manifest changes (`sidePanel` permission, `side_panel.default_path`, `content_scripts`) need `npm run build` and a reload in `chrome://extensions`, plus a full Chrome restart (AGENTS.md step 7). The pinned `key` keeps the extension id, so `allowed_origins` is unchanged.
- The native host is unchanged in path and name. Re-running `register-native-host.py` is needed only if the venv moved.
- The pipe name is fixed per user (e.g. `\\.\pipe\ClinikoScribe-<user SID>`), created by `scribe-app` at startup.
- Release risk: the first real network traffic from `scribe-app`. The live check is Task P.2, run by the practitioner from a user-launched app.

## Critical Constraints
1. **Drafts only, by construction.** This plan has no write method at all, and no code path can send `draft: false`.
2. **The Cliniko client is the only network surface.** One module, a pinned host, no redirects and no proxy. No Cliniko call at startup or idle. Every existing no-sockets leg stays at zero connections.
3. **The app is the single owner of state and pause decisions** (D5). Chrome renders the app's `state`, and nothing moves speech between patients.
4. **Consent before every recording**, on every Start path. The controller refuses `start()` without a `ConsentAttestation`.
5. **Write-back is refused unless the context is verified** (`writeback_context`). Unlinked, unverified, mismatched and recovered-but-not-re-verified sessions are all refused.
6. **Custody.** GUI-thread-only custody calls. `context.enc` is written before `audio.enc`. Decrypt only on checkout or when a session joins the list. The single-active-session invariant is unchanged.
7. **The key is never logged, displayed after entry, put in an exception, sent to Chrome or written outside Credential Manager.** Patient names never enter extension storage or any log.
8. **Named pipe only for host↔app** (the locked Phase 1 topology) — never a socket, never a polled file.
9. **`protocol/fixtures/` is the contract**; both mirrors are tested against it.
10. **Security-doc claims state only what the structure enforces**, rewritten as a class (lessons 2026-08-14, 2026-08-10).

## Validation / Verification
**Baselines (dry-run 2026-09-27 at `main @ 33bd35e`; read-only checks only)**
- `desktop`: `ruff check .` → "All checks passed!".
- `grep -rn "noqa: TID251" desktop/src | wc -l` → 0.
- `grep -rn "import http\|from http\|import ssl\|urllib" desktop/src | wc -l` → 0.
- `start(0)` call sites in `desktop/tests/*.py` → 59.
- Suite: 2817 passed at the last recorded run (`AGENTS.md`, 2026-09-27); mypy 39 files.
- Node v24.18.0. The extension has Vitest 4.1.10 and no DOM environment.

**Per phase (composer-run on the Windows host)**
- `desktop/`: `ruff check . && mypy && pytest`.
- `extension/`: `npm run qa`.
- After Phase 1:
  - The TID251 noqa count is exactly 1, in `cliniko_client.py`.
  - The stdlib network-import count equals the client's import lines.
- The existing `test_integration_no_sockets.py` legs stay at zero connections. The host-handshake-with-no-app leg still passes after Phase 4, and a new leg with the app's pipe open asserts no sockets.

**Required test classes**
- Client: the host pin; redirects refused; the size cap; every error class; the transport only ever receiving "GET"; the key absent from every exception and log record.
- Registry: validation success and each refusal; duplicate subdomain; shard mismatch; no network call at app startup or idle (with an injected transport counting calls).
- Encounter and custody:
  - `start()` refuses without consent on both paths.
  - `context.enc` is written before `audio.enc`, including the crash-ordering test.
  - Decrypt happens only on checkout, pinned by a spy.
  - Recovered linked sessions re-verify.
- Pipe:
  - The hardening flags and DACL are pinned.
  - An unverified server is a hard error.
  - Framing over short reads.
  - Relay both ways.
  - The host answers hello/ping with no app.
- Protocol: every v2 fixture, valid and invalid, in both mirrors.
- Pause rule: the D5 table as a parameterised test, including non-Cliniko tabs NOT pausing and multi-window focus.
- **Cross-patient adversarial matrix** (Task 3.6). Every case ends with `writeback_context` refusing and no speech attributed across patients:
  - the URL patient differs from the API note's patient;
  - a note from the other clinic, or a host/shard mismatch;
  - a finalised note;
  - a wrong practitioner;
  - a report from a non-bound or stale tab;
  - a replayed report after resolution;
  - Resume previous while B is on screen;
  - a missing or corrupt `context.enc` after a crash;
  - an unlinked session;
  - an `unverified_offline` session.
- Extension (Vitest + DOM environment + `chrome.*` fakes):
  - URL parser;
  - allow-list inertness (no frame or reports on non-allow-listed hosts or before the first `state`);
  - panel rendering of every D1 state;
  - badge;
  - the service-worker restart re-requesting state.
- Hands-free: hotkey registration success and failure; the spoken matcher (positives and near-misses); "unavailable" when live is off or failed; boundary-rule positives and negatives.

**Practitioner-run**
- Task P.1: the read-only feasibility check on both clinics.
- Task P.2: the live smoke — every Flow 1–6 on a user-launched app and Chrome, both clinics, including a deliberate patient switch, a Chrome close mid-recording, an unreachable network at Start, the hotkey, "scribe pause", and the Unreviewed reminder.

**Success criteria**
- PLAN.md Phase 5's completion line: workflow and adversarial tests cannot attach one consultation to another patient.
- PLAN.md test plan: recording cannot start without the consent checkbox; switching patient, appointment or clinic pauses immediately; context loss blocks write-back; cross-patient tests pass with zero failures.

## Deferred / Out of Scope
See `Planning Extraction Summary` → Deferred, and Excluded. The Phase 4 write is the next plan and needs no rediscovery: `.cursor/plans/explore-cliniko-integration.md` carries its findings and assumptions, and this plan's `writeback_context` and `ClinikoClient` are its entry points.

## Current State / Handoff Note
- Last completed step: Planning complete (2026-09-27, `/create-plan` from the Cliniko-integration exploration).
- Current in-progress step: None
- Immediate next action: a `/review-plan` hardening pass or a cross-family `/peer-review` of this plan, then Task 1.1 via `/execute-loop`.
- Open blockers / open questions:
  - Task P.1 (practitioner) gates Task 1.3's `[decision]`.
  - Task 1.4 (copy flag) needs the practitioner's confirmation at execution: the permission classifier blocked it during planning.
  - The Task 6.5 dev dependency needs authorisation.
- Last plan sync: 2026-09-27

## Review History
- (no reviews yet)

## Review Findings Log
- (no findings logged yet)

## Tasks
Every task's verification is the per-phase suite in `Validation / Verification` plus the test classes it names. `[executor: premium-only]` marks custody, concurrency, network-surface and security-doc work. The executor tier is entirely premium, so the labels record where care concentrates rather than routing.

### Phase 1 — Cliniko read client, feasibility check, copy flag
- [ ] 🟥 1.1: **Cliniko read client** `[executor: premium-only]`
  - Files: new `desktop/src/scribe_desktop/cliniko_client.py`; new `desktop/tests/test_cliniko_client.py`.
  - Behaviour: `ClinikoClient(key_provider, contact_email, transport=HttpsTransport())` exposes GET-only methods for `/user`, `/practitioners?user_id`, `/settings/public`, `/treatment_notes/<id>`, `/patients/<id>` and `/bookings/<id>`, per D9. It also parses the shard from the key suffix.
  - The one `# noqa: TID251` sits on `import http.client`. A test pins exactly one such site in `src/` and that the transport only ever receives "GET".
  - Verification: the client test classes in Validation.
- [ ] 🟥 1.2: **Read-only feasibility script**
  - Files: new `scripts/probe-cliniko.py`.
  - Behaviour: it runs from a normal terminal, reads the key with `getpass` (never argv or env), and asks for a note id the practitioner opens. It calls 1.1's client for `/user`, `/practitioners`, `/settings/public` (and `/settings` if refused), `/treatment_notes/<id>` and the linked booking and template.
  - It prints ONLY structure: HTTP status per call, field presence, `draft`/`finalized_at` null-ness, whether booking and template links exist, the note practitioner id == the key user's practitioner id (a boolean), and the note `content` shape with answers reduced to empty/non-empty. It never prints a name, id value, answer text or the key.
  - Verification: a unit test on the redaction function with a fixture response.
- [ ] 🟥 P.1: **Practitioner runs the feasibility check on both clinics** (practitioner-owned)
  - Open a patient's treatment note in each clinic (Cliniko creates the draft), then run `.venv\Scripts\python.exe scripts\probe-cliniko.py` from a normal terminal at the repo root.
  - Paste the printed structure (it contains no patient data) into this task's Done note.
- [ ] 🟥 1.3: **Key-to-clinic subdomain source** `[decision]`
  - Options:
    - (a) `/settings/public` (P.1 shows a practitioner key may call it);
    - (b) `/settings`;
    - (c) the practitioner types the subdomain and the app confirms it against the first tab host whose note verifies with that key.
  - Decide after: P.1.
  - Blocks: 2.1 validation step 3.
  - Also record here what P.1 showed for the booking link, the template link and the practitioner link (feeds D3/D4; `booking_id` stays optional either way).
- [ ] 🟥 1.4: **Copy-to-Cliniko flag flip and shipping-gate reframing** (confirm with the practitioner before editing — the planning-time edit was blocked by the permission classifier as security-weakening)
  - Files:
    - `ui/models.py` (flag `True` plus the decision comment, D12);
    - `desktop/tests/test_ui_screens.py` (rename `test_default_copy_binding_ships_disabled` → `…_ships_enabled`, `is True`, and assert an unratified note under the default binding is still not copyable);
    - `ui/note.py` module docstring (`:122`);
    - `docs/testing/shipping-gate.md` (status: a quality measurement, not a block, 2026-09-27; "What the gate decides" and "What a decision flips" reworded);
    - `docs/design-system.md` (`:221-229`), `docs/security/threat-model.md` (`:361-363`), `docs/security/data-flow-map.md` (`:209`);
    - `AGENTS.md`, `CHANGELOG.md`;
    - `.cursor/plans/plan-phase3a-note-pipeline.md` (a dated note on Task 9.1).
  - Derive the site list with the gate doc's own grep, never from this list.
  - Behaviour: a fully ratified note is copyable. Everything else is unchanged.

### Phase 2 — Clinic keys and the offline-contract rewrite
- [ ] 🟥 2.1: **Clinic registry and key validation** `[executor: premium-only]`
  - Files: new `desktop/src/scribe_desktop/clinics.py`; tests.
  - Behaviour: `ClinicRegistry` loads and saves `clinics.json` fail-closed. `validate_and_store(key, contact_email)` runs D10's validation through 1.1 and 1.3's route, stores the key via `SecureStorageProvider`, and returns a typed result or a refusal by name. `remove(clinic_id)` deletes the key and the record. `allow_list()` returns the hosts.
  - Verification: the registry test classes, including "no network call at startup or idle".
- [ ] 🟥 2.2: **Clinics tab**
  - Files: new `ui/clinics.py`; `ui/main_window.py` (register the tab); `ui/models.py` (copy constants).
  - Behaviour:
    - A password-masked key field, cleared after Validate. A contact-email field.
    - Validate / Replace key / Remove, each with a status line naming the outcome.
    - Validation runs only on the button. Nothing validates at startup.
  - Follows `docs/design-system.md` (state drives enablement; named destructive actions).
  - Verification: offscreen UI tests with an injected registry.
- [ ] 🟥 2.3: **Offline-contract rewrite, as a class** `[executor: premium-only]`
  - Files: `desktop/pyproject.toml` (`:8` description, `:91-95` ban comment); `ui/__init__.py:9`; `language_model.py:21`; the four security docs.
  - Docs:
    - `docs/security/data-flow-map.md`: `:11-14`, `:49-51`, `:141-142`, `:487-493`, plus a NEW flow "Cliniko API reads" (what leaves: key, ids; what returns: names, appointment time, note metadata; memory only).
    - `docs/security/threat-model.md`: `:76-78`, `:118-119`, `:1259`, plus a NEW surface for the client (D9's controls and their residue: same-user key read; TLS trust in the Windows store).
    - `docs/security/retention-schedule.md`: rows for `clinics.json` and the API responses (memory only).
    - `docs/security/intended-use.md`: `:3-4`, `:21-22`, `:34-39`.
  - Find every sibling of "no network" / "no sockets" / "never the app" / "ONLY sanctioned network" with a grep, and record the grep in the Done note.
  - Behaviour: every claim states exactly what the structure enforces.

### Phase 3 — Encounter context, consent and session binding `[executor: premium-only]`
- [ ] 🟥 3.1: **Encounter and consent types**
  - Files: new `encounter.py`; `session.py` (`RecordingSession` fields); `logging_setup.py` (tripwire field set).
  - Behaviour: the D3 types, with `RecordingSession.encounter_context: EncounterContext | None` and `consent: ConsentAttestation`. The tripwire drops every new field.
  - Verification: type tests and a tripwire test.
- [ ] 🟥 3.2: **Note verification**
  - Files: `encounter.py` (`verify_note_context`); tests.
  - Behaviour: D4's check and its three outcomes, through 1.1 with an injected transport. The display strings are returned separately from the context and never persisted.
- [ ] 🟥 3.3: **`start()` with consent and context; `context.enc`**
  - Files:
    - `session.py` (`start(device_id, *, consent, context=None)`);
    - `session_store.py` (write/read `context.enc`, D11);
    - `ui/models.py` (`SessionControllerLike.start`);
    - `ui/session_screen.py` (a desktop consent checkbox above Start, per the design-system consent posture; "Not linked to a Cliniko note" label);
    - all callers: the 59 `start(0)` test sites via a shared test helper, and the 4 no-sockets child scripts.
  - Behaviour: `start()` refuses without consent. A linked start writes `context.enc` after `key.dpapi` and before `audio.enc`.
  - Verification: the consent refusal on both paths, and the ordering/crash test.
- [ ] 🟥 3.4: **Context on recovery and checkout**
  - Files: `session_store.py`, `ui/recovery.py`, `ui/models.py`.
  - Behaviour:
    - `context.enc` is decrypted only on checkout (a spy test proves `list_recoverable_sessions` and the sweep never decrypt it).
    - A recovered linked session is re-verified (D4) before it counts as linked.
    - Missing or undecryptable means unlinked.
    - `RecoveryScreen._describe` shows linked/unlinked and the clinic.
- [ ] 🟥 3.5: **Write-back guard**
  - Files: `encounter.py` (`writeback_context(session) -> VerifiedTarget | Refusal`).
  - Behaviour: refuses unlinked, unverified, not-re-verified and mismatched sessions, each by name. This is Phase 4's only entry to a write target.
- [ ] 🟥 3.6: **Cross-patient adversarial matrix**
  - Files: new `desktop/tests/test_cross_patient.py`.
  - Behaviour: every case in Validation's matrix ends in a refusal, with zero failures. This is PLAN.md Phase 5's completion evidence.

### Phase 4 — Pipe, protocol v2, relay and state publisher `[executor: premium-only]`
- [ ] 🟥 4.1: **Protocol v2**
  - Files: `protocol/fixtures/` (meta 2/2, new valid and invalid fixtures for `context`/`command`/`state`, README); `protocol.py` (per-type payload models); `extension/src/protocol.ts`; both mirror tests.
  - Behaviour: D2. Unknown types and bad payloads fail closed in both mirrors.
- [ ] 🟥 4.2: **Named-pipe server in `scribe-app`**
  - Files: new `pipe_server.py`; `app.py` (lifecycle).
  - Behaviour: one per-user pipe with:
    - the Phase 2 hardening list: `FILE_FLAG_FIRST_PIPE_INSTANCE` (literal `0x00080000`), `nMaxInstances=1`, `PIPE_REJECT_REMOTE_CLIENTS`, and a user-only DACL from SDDL;
    - overlapped I/O plus a stop event;
    - a `ReadFile` adapter feeding `framing.read_frame` that loops on short reads;
    - messages emitted only as queued Qt signals.
  - Verification: pinned flags/DACL, framing over short reads, clean stop.
- [ ] 🟥 4.3: **Pipe peer identity** `[decision]`
  - Options:
    - (a) the host verifies the server PID's parent chain up to `Scripts\scribe-app.exe` plus `GetNamedPipeServerSessionId`;
    - (b) session id plus the user-only DACL, with the same-user residue documented as `app.py:76-77` does for the mutex;
    - (c) (a) with a server-side check of the client PID.
  - Decide after: 4.2 works and the redirector chain is measured on this host.
  - Blocks: 4.4's connect contract. "Pipe exists but server unverified" is a hard error under every option.
- [ ] 🟥 4.4: **Two-way native-host relay**
  - Files: `native_host.py`; `desktop/tests/test_native_host*.py`; the no-sockets host legs.
  - Behaviour:
    - Two threads (stdin→pipe, pipe→stdout) with a stdout lock.
    - The host still answers hello/ping itself with no app, and retries the pipe with a bounded `WaitNamedPipe`.
    - Envelopes are validated with `protocol.py`; commands are never interpreted. The host exits on EOF from either side.
  - Verification: the existing handshake-with-no-app leg passes, plus a new app-pipe-open no-sockets leg.
- [ ] 🟥 4.5: **App dispatcher and state publisher**
  - Files: new `ui/bridge.py` (or `bridge.py`); `ui/main_window.py`; `ui/session_screen.py` (elapsed time excluding pauses).
  - Behaviour:
    - `command` routes to the SessionScreen slots (`on_start` with the consent and context, `on_pause`, `on_resume`, `on_finish`, `on_discard`, `open_review`). A missing microphone becomes a panel block reason.
    - `StatePublisher` pushes `state` on every state change (hooked on the `_watch_state` poll and on explicit events) and in full on connect.
    - A `context` report for a note triggers `verify_note_context` off the GUI thread, with its result marshalled back.

### Phase 5 — Pause rule, resolution, back-to-back and the Unreviewed list `[executor: premium-only]`
- [ ] 🟥 5.1: **ContextEvaluator**
  - Files: new `context_rules.py`; `ui/bridge.py`.
  - Behaviour: D5 exactly, with one idempotent `pause_for(reason)` used by context, pipe loss, the hotkey (7.1) and speech (7.2). It is parameterised-tested against the D5 table.
- [ ] 🟥 5.2: **Resolution block**
  - Files: `context_rules.py`, `ui/bridge.py`, `ui/session_screen.py`.
  - Behaviour:
    - Finish previous / Resume previous / Discard previous per Flow 3.
    - `resume_previous` asks the extension to navigate the bound tab back and resumes only on a matching report.
    - The desktop Resume and the hotkey honour the block.
- [ ] 🟥 5.3: **Back-to-back flow**
  - Files: `ui/bridge.py`, `ui/session_screen.py`, `ui/main_window.py` (`_on_session_started`).
  - Behaviour: D6. "Finishing <A>…" shows while PROCESSING; B's Start unlocks at QUEUED; starting B retires A into the Unreviewed list.
  - Measure A's tail duration: timing only, no content. Record it in the Done note (feeds the Accepted Assumption).
- [ ] 🟥 5.4: **Unreviewed list and review reopen**
  - Files: `ui/recovery.py` (or a new `ui/unreviewed.py`), `ui/models.py`, `ui/main_window.py`.
  - Behaviour:
    - Queued sessions with `transcript.enc` are listed as Unreviewed.
    - "Open for review" checks the session out and opens Transcript/Note review from `transcript.enc` with no re-transcription.
    - The `(clinic_id, note_id) → session_id` index is built once per join or app start (D6).
    - An expiry warning fires 2 h before 24 h, from the plaintext `created_at`.
- [ ] 🟥 5.5: **Reminder on reopening a note**
  - Files: `ui/bridge.py`.
  - Behaviour: a `context` for a note in the index sets the reminder in `state`. The panel's Open for review sends `open_review`, which brings the desktop window forward on that session.

### Phase 6 — Chrome extension UI
- [ ] 🟥 6.1: **Manifest and build**
  - Files: `extension/src/manifest.ts`, `extension/vite.config.ts`.
  - Behaviour: adds the `sidePanel` permission, `side_panel.default_path`, and `content_scripts` for `https://*.cliniko.com/*` (inert until allow-listed). No `tabs` permission. `setPanelBehavior({openPanelOnActionClick: true})` in background.
- [ ] 🟥 6.2: **Background: tab tracking, reports and relay**
  - Files: `extension/src/background.ts`, new `extension/src/context.ts` (URL parser), `connection.ts`.
  - Behaviour:
    - `tabs.onUpdated`/`onActivated`/`onRemoved` and `windows.onFocusChanged` drive `context` reports.
    - The note URL parser covers `/patients/<id>/treatment_notes/<id>/edit`, the login page and other Cliniko pages. Nothing is reported for non-allow-listed hosts.
    - The allow-list and state are held in memory only; after a service-worker restart the extension re-requests state on reconnect.
    - The badge follows `state`.
    - A content-script URL heartbeat is the backstop for the SPA assumption.
- [ ] 🟥 6.3: **Page script: frame and block**
  - Files: new `extension/src/page.ts`.
  - Behaviour: renders only from `state` inside a closed shadow root — the red/amber frame and the D1 block. The block's buttons send `command`. The script is inert (renders nothing, reports nothing) until the first `state` names this host in the allow-list. It never reads Cliniko's DOM.
- [ ] 🟥 6.4: **Side panel**
  - Files: new `extension/src/panel.html`, `extension/src/panel.ts`.
  - Behaviour:
    - Every D1 panel state in precedence order.
    - The consent checkbox gates Start, and Start sends `command{start, consent}`.
    - Pause / Finish consultation, the block mirror, the Unreviewed reminder.
  - Spike first: can `sidePanel.open()` run from the block's button gesture? Record the result, and apply D1's fallback if not.
- [ ] 🟥 6.5: **Extension tests**
  - Files: `extension/package.json` (a DOM environment devDependency — authorise before adding); new `*.test.ts`.
  - Behaviour: Validation's extension classes using `chrome.*` fakes.

### Phase 7 — Hands-free and warnings
- [ ] 🟥 7.1: **Global hotkey** `[executor: premium-only]`
  - Files: `ui/main_window.py` (`nativeEvent`), a new small `hotkey.py` (registration and unregistration).
  - Behaviour: D7. The chord pauses or resumes through `pause_for`/the guarded resume. A registration failure is shown in the desktop app and in `state`.
- [ ] 🟥 7.2: **Spoken pause**
  - Files: `ui/main_window.py` (`_build_live_transcriber` tee), new `voice_commands.py`.
  - Behaviour: D7. A queued signal carries the live window; the matcher triggers `pause_for("spoken")`. "Spoken pause unavailable for this recording" shows when live transcription is off or failed.
- [ ] 🟥 7.3: **New-consultation warning**
  - Files: `voice_commands.py` (or `boundary_rules.py`), `ui/bridge.py`.
  - Behaviour: D8. The warning appears in the panel and the desktop, never pauses, and is test-pinned on positives and negatives.

### Phase 8 — Docs and the live smoke
- [ ] 🟥 8.1: **Docs for the new surfaces** `[executor: premium-only]`
  - `docs/security/data-flow-map.md`: flows for the pipe, `context`/`state`, and the patient name into Chrome memory. Replace the "Phase 5 preview" block.
  - `docs/security/threat-model.md`: surfaces for the pipe (with 4.3's decision and residue), the extension page script and panel, `context.enc`, and the pause rule's residue (an in-page session-expiry modal that does not change the URL).
  - `docs/security/retention-schedule.md`: rows for `context.enc` and the Unreviewed index (memory).
  - `docs/design-system.md`: the panel, frame, block and desktop consent cues.
  - `AGENTS.md`: Local Run Steps (rebuild and reload the extension, the Clinics tab, the pipe); Subsystem Documentation pointers.
  - `protocol/fixtures/README.md`.
  - `PLAN.md`: "pause/stop" now means pause only by voice; Phase 5 delivered with the read-only API.
  - `CHANGELOG.md`.
- [ ] 🟥 P.2: **Practitioner live smoke** (practitioner-owned)
  - Flows 1–6 on both clinics from a user-launched app and a fully restarted Chrome, per Validation's practitioner-run list.
  - Record the outcomes (no patient data) in this task's Done note.

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
- **Decisions that still apply:** D2 (protocol), D3/D4 (encounter and verification), D9 (client contract), D10 (registry), D11 (`context.enc`), and the Critical Constraints.
- **Must not be rediscovered:**
  - `urllib` bypasses the host pin (redirects, proxies).
  - The venv `python.exe` is a redirector (4.3).
  - The periodic-decrypt class.
  - No Cliniko call at startup or idle keeps the no-sockets legs at zero.

---
*Plan saved to: .cursor/plans/plan-cliniko-workflow-safeguards.md*
*To resume in a new session: run /start-session, then /load-plan*
*State-once convention: cross-section contracts live in Design Decisions (D1–D12) and Critical Constraints; other sections point to them.*
