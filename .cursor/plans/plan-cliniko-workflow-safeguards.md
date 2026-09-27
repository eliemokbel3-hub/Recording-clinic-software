# Feature Implementation Plan
**Feature:** cliniko-workflow-safeguards
**Overall Progress:** `32%` (13 of 41 tasks: 1.1, 1.2, 1.3, 1.4, 2.1a, 2.1b, 2.2, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6; Task 8.2 added 2026-09-27 by practitioner decision)

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
- Two clinic API keys, entered in a new desktop Clinics tab, stored in Windows Credential Manager and validated against Cliniko: ~~practitioner role~~ an active login with exactly one active practitioner record (whatever its role — D10 as amended 2026-09-27 after Task P.1), subdomain, and a shard that matches the clinic host.
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
    - **Task P.1 finding for the "typed text" definition (clinic 1, 2026-09-27):** a freshly opened draft is NOT content-empty — most of the practitioner's templates default the "Presenting complaint / patient progress" answer to a prompt scaffold (labels with blank values: site, chronicity, sensory, aggravating, relieving, general, associated symptoms). "Refuse the write if the note already holds typed text" must therefore treat an answer equal to the template's default as NOT typed (e.g. compare each answer with the default from `treatment_note_template.links.self`), or every auto-created draft would be refused. The scaffold labels are also a candidate structure for mapping that section's content — a practitioner-owned decision for the Phase 4 plan. The note's `content` is `sections[] → questions[] {name, type, answer? | answers?[{value}]}`.
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
  - **P.1 clinic 1 (2026-09-27):** a freshly opened note read back as `draft: true`, `finalized_at: null`, with booking, template, patient and practitioner links — confirmed. It is NOT content-empty: it holds the template's default answer text (see the Phase 4 bullet under Deferred). Clinic 2 owed.
- **Cliniko API details are per docs.api.cliniko.com and unverified live.** Covers: the roles that may call `/settings/public`; whether the auto-created draft carries booking and template links; whether the note's practitioner link equals the key user's practitioner record.
  - **P.1 clinic 1 (2026-09-27): all three confirmed** — an `administrator` key read `/settings/public` (200, `account.subdomain` present and matching the note URL's); the draft carried booking and template links; the note's practitioner link equalled the key user's single practitioner record. Still unverified: which statuses `/settings/public` refuses with (no key was refused there), and everything on clinic 2 (its practitioner user cannot create API keys yet).
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

**Endpoints used in this plan (reads only)** — Task P.1 ran on clinic 1 on 2026-09-27 (structure only; clinic 2 owed, its user cannot create API keys yet).
- `GET /user`: `id`, `role`, `active` — confirmed by P.1 clinic 1. The practitioner's own login's role is `administrator` (hence D10's 2026-09-27 amendment). A `user_active` field is also present.
- `GET /practitioners?q[]=user_id:=<id>`: a `practitioners` list whose entries carry `id`, `active`, `display_name` and a `user` link, plus `total_entries` — confirmed by P.1 clinic 1 (exactly one record for the user).
- `GET /settings/public`: `account.subdomain` — confirmed by P.1 clinic 1, answered for an `administrator` key and matching the note URL's subdomain. Which statuses it refuses with is still UNCONFIRMED (no refusal seen).
- `GET /treatment_notes/<id>`: `draft`, `finalized_at`, and links for `patient`, `practitioner`, `booking`, `treatment_note_template` — confirmed by P.1 clinic 1 on an open draft (patient link = the URL's patient; practitioner link = the key user's practitioner record). Also `archived_at`, `deleted_at`, and `content.sections[].questions[]`. An ARCHIVED note answers 404 (P.1's first run).
- `GET /patients/<id>`: the display name — 200 in P.1 clinic 1 (`first_name`, `last_name`, `preferred_first_name`, `archived_at` among others).
- `GET /bookings/<id>` or `/individual_appointments/<id>`: `starts_at` in UTC — `/bookings/<id>` answered 200 with `starts_at` in P.1 clinic 1.

**Web app URLs** (practitioner-supplied; ids are placeholders — never commit real ids)
- Host: `https://<subdomain>.<shard>.cliniko.com`. One clinic is on `au2`, the same shard as its key suffix (P.1 clinic 1 confirmed key shard = URL shard, 2026-09-27).
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
Open the desktop app's Clinics tab, paste a clinic's Cliniko API key and a contact email for Cliniko's User-Agent, then press Validate. The app checks the key against Cliniko: an active login with exactly one active practitioner record (whatever its role — D10 as amended 2026-09-27), a subdomain that matches, and a key shard that matches the clinic host. It stores the key in Credential Manager and the non-secret clinic record in `clinics.json`. It then advises clearing Windows clipboard history. Repeat for the second clinic.

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
  - Validation: `GET /user` (~~role practitioner,~~ active) → `GET /practitioners?q[]=user_id:=` (exactly one, and it active) → the subdomain from `/settings/public`. If that is refused, the practitioner types the subdomain, and it is CONFIRMED by the first note that verifies with that key on that host (the former `[decision]`, settled in the hardening pass; P.1 records which route applies — clinic 1: the `/settings/public` route).
  - **Amended 2026-09-27 (practitioner decision after Task P.1; composer record `OWNERSHIP: gate-disposition key=d10-role-check choice=practitioner-record-decides`):** "Practitioner record decides" — accept any active login linked to exactly one active practitioner record, whatever its role. P.1 found the practitioner's own login is an `administrator`, which the role check would have refused. A receptionist or bookkeeper login has no practitioner record, so it is still refused. Built in leg `stage-2-exec-b2`: the role field is no longer read; zero records, several records, or one inactive record is each a named refusal.
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
- **EXECUTOR HANDOFF (leg `stage-3-exec-c6`, 2026-09-27T20:02+10:00, run stage-3) — Phase 3 BUILD-COMPLETE and CONVERGED; `reason=phase-complete`.** Tasks 3.1–3.6 are 🟩 (suite 3323 passed; `/review-loop` rounds 20–21; codex pass stage-3.p1 rounds 22–24 converged at peer_round 3 of 5). Overall Progress `32%` (13 of 41). Owed to the practitioner: the live-user smoke below.
  - **Phase 3 live-user smoke (practitioner; about 10 minutes).** This checks the new consent tick and the "linked / not linked" lines. It uses a mock consultation only: speak a few made-up sentences, never real patient details. It needs NO clinic key and makes no Cliniko call, so having only clinic 1 set up is fine. Please don't paste anything from the app or from Cliniko into chat — just report PASS or FAIL for each step, and for a FAIL describe what you saw in your own words. Launch the app by double-clicking `.venv\Scripts\scribe-app.exe`.
    1. Open the **Session** tab. EXPECT: above the buttons, the line "Not linked to a Cliniko note - a recording started here cannot be written back to Cliniko.", then an UNTICKED box reading "I confirm the patient has consented to AI-assisted recording and documentation". **Start** is greyed out.
    2. Tick the box. EXPECT: **Start** becomes clickable. Untick it. EXPECT: **Start** greys out again.
    3. Tick the box and press **Start**. Speak a few made-up sentences, then press **Finish**. EXPECT: recording works as before; the box is unticked again straight after you pressed Start; the line still says "Not linked to a Cliniko note". The app moves to the **Transcript** tab when the transcript is ready.
    4. On the **Transcript** tab press **Discard** (confirm if asked). EXPECT: the recording is gone, as before.
    5. Back on the **Session** tab, tick the box and press **Start** again, speak a sentence or two, and then — while it is still recording — close the app from Task Manager (right-click scribe-app → **End task**; this stands in for a crash). Launch the app again and open the **Recovery** tab. EXPECT: the session is listed, and its row ends with "- Cliniko link checked when opened" (it may also say the recording was not finished — that is expected).
    6. Select that session and press **Resume processing** (confirm if asked). EXPECT: the app moves to the **Transcript** tab, and under the transcript the line reads "Not linked to a Cliniko note - this recording cannot be written back to Cliniko." No "checking it with Cliniko" line appears. Then press **Discard** on the Transcript tab (confirm if asked).
    - Escape (if any step goes wrong): a recording still running is ended with **Discard** on the Session tab; a transcript on screen with **Discard** on the Transcript tab; a crashed session left on the Recovery tab by selecting it and pressing **Discard** there. After that the Recovery tab should list nothing from this test, and nothing is left behind.
  - What the composer's `/document` should carry: Phase 3 closed (AGENTS.md Current Status, phase-history); the recording-consent tick and `encounter.enc` in the run notes; the threat model's "Cliniko API client" section as now built (second importer, NOTE VERIFICATION, THE ENCOUNTER RECORD, THE WRITE-BACK GUARD); the AGENTS.md subsystem pointer for the Cliniko client extended to `encounter.py` and the checkout block in `ui/main_window.py`.
  - Executor recommendation: the Phase 4 plan should require that its draft write passes a re-verification made FOR that write. `writeback_context` binds a re-verification to the clinic's current `clinic_rev`, not to its age, so a recovered checkout's re-verification stays valid for as long as the checkout is open; alternatively, the guard can gain an age bound then. surface=production (the next plan; no Phase 3 change).
  - Executor recommendation: the hardening stage's whole-surface read should check the remaining `TaskThread(…, self)` closure sites that keep their inputs for the owning widget's lifetime — `ui/microphone.py`, `ui/recovery.py`, `ui/session_screen.py`, `ui/transcript.py`, `ui/practitioner.py` (first recorded in round 15). `ui/clinics.py`, `ui/note.py`'s prose job and, since round 20 LOW-013, the checkout re-verification in `ui/main_window.py` use the holder pattern. None of the remaining sites holds a Cliniko key; whether any keeps transcript or profile plaintext is the open question. surface=production.
- **EXECUTOR HANDOFF (leg `stage-3-exec-c5`, 2026-09-27T19:53+10:00, run stage-3) — `/fix` codex rounds 22 + 23 DONE; both rounds Closed; `reason=composer-run`.** PR-LOW-100 is fixed in the test harness: `encounter_fakes.py` gives each fake clinic its own key (`OTHER_KEY`, strict `CLINIC_KEYS`), and `test_the_other_clinics_note_verifies_under_its_own_key` now verifies and accepts clinic B's request and asserts B's Basic credential, the API host and B's verified context. PR-LOW-110 is fixed in the doc: the threat model's ENCOUNTER RECORD sentence now binds the practitioner "if it names a practitioner". Ruff clean; mypy 43 files.
  - **Expected suite: 3323 passed** (one test strengthened, none added or removed).
  - Next: the scoped codex confirmation (round 24); tasks 3.1–3.6 stay 🟨.
- **EXECUTOR HANDOFF (leg `stage-3-exec-c4`, 2026-09-27T19:51+10:00, run stage-3) — codex rounds 22 + 23 LEG 1 VERIFIED (no `/fix`); `reason=phase-complete`.** PR-LOW-100 is confirmed as LOW, test-harness, Fix-now: the other-clinic test never verifies, and every fake clinic shares one key. Fix shape: distinct per-clinic fake keys, and the test verifies, accepts and asserts B's credential, host and context. PR-LOW-110 is confirmed as LOW, docs-only, Fix-now. The DOC is the right fix, not the code: D3 keeps `practitioner_id` optional; the only production constructor always sets it; D4 checks the practitioner separately; and requiring it would break two refusal tests' constructions. Cap verdicts: accept (22, test-harness) and accept (23, docs-only). Both rounds stay Open (1 pending each) until `/fix`; the suite is unchanged at 3323.
- **EXECUTOR HANDOFF (leg `stage-3-exec-c3`, 2026-09-27T19:43+10:00, run stage-3) — `/review-loop` CONVERGED at round 21 (round 2 of cap 3); `reason=phase-complete`.** The c2 tree was GREEN (3323). Round 21: 6/6 round-20 fixes confirmed; the missed-issue pass found nothing; no code or test change, so the suite stays **3323 passed**. Tasks 3.1–3.6 stay 🟨 for the codex pass. Ruff clean; mypy 43 files.
  - Executor recommendation (for the Phase 4 plan, surface=production, not a Phase 3 change): `writeback_context` binds a re-verification to the clinic's CURRENT `clinic_rev`, not to its age, so a recovered checkout's re-verification stays valid for as long as the checkout is open. D4 places the fresh check "in Phase 4 before the write"; the Phase 4 write should pass a re-verification made for that write (or the guard should gain an age bound then), not the checkout's.
  - Owed to the practitioner: the ≤ 6-step live smoke in the c1 bullet below, with c2's step-6 change (the link line is on the Transcript screen).
- **EXECUTOR HANDOFF (leg `stage-3-exec-c2`, 2026-09-27T19:37+10:00, run stage-3) — `/review-loop` round 20 (round 1 of cap 3) RUN and FIXED; `reason=composer-run`.** The c1 tree was GREEN (3318). Round 20: 0 CRIT / 0 HIGH / 1 MED / 5 LOW, all Fix-now, all applied (details in the Findings Log): MED-012 write-back now needs a current re-verification on the LIVE path too (a Start verification alone no longer yields a target — D9's Replace key could otherwise leave it write-eligible); LOW-013 the checkout thread's closure no longer keeps the request (holder pattern); LOW-014 the checkout's link line moved to the Transcript screen; LOW-015 the clinic-gone line no longer offers an impossible remedy; LOW-016 the ledger's per-note throttle (a VERIFIED outcome reused for 60 s on the same connection and rev); LOW-017 flow 6's sweep wording. Ruff clean; mypy 43 files.
  - **Expected suite: 3323 passed** (3318 + 5: `TestWritebackContext` +1, `TestLedger` +3, `TestRecoveredCheckout` +1; three tests changed, none removed).
  - **Reconciling c1's count (3317 vs the actual 3318):** `test_encounter.py` has 95 collected tests, not 94. I counted 53 plain functions; it has 54 (`TestWritebackContext` has 16 functions, `TestLedger` 16), plus 41 parametrized cases. No unintended test.
  - Live-smoke change from c1's checklist: step 6 — after opening the recovered session, the line "Not linked to a Cliniko note - this recording cannot be written back to Cliniko." is now on the **Transcript** screen, under the transcript; there is no need to switch back to the Recovery tab.
  - Next: the composer re-runs `cd desktop && ../.venv/Scripts/pytest.exe -q` and resumes me for round 21 (the post-fix regression check).
- **EXECUTOR HANDOFF (leg `stage-3-exec-c1`, 2026-09-27T19:24+10:00, run stage-3) — Phase 3 BUILT (Tasks 3.1–3.6 🟨); `reason=composer-run`.** Ruff clean; mypy 43 files. File-by-file records are under each task. Summary: new `encounter.py` (types, D4 verification worker + GUI ledger, the write-back guard; the client's second importer, `TestConfinement` pin and the security docs updated together); `session.py` (`consent` REQUIRED on `RecordingSession` — the Task 3.1 decision; `start(device_id, *, consent, context=None)`; `encounter.enc` between the key and audio; D2's `session_ref` registry); `session_store.py` (`encounter.enc` read/write); `logging_setup.py` (3 new signatures); `clinics.py` (`key_store` / `transport` properties); `ui/models.py`, `ui/session_screen.py` (the consent tick + link line), `ui/recovery.py`, `ui/main_window.py` (the checkout decrypt + re-verification, `_live_session_clinic` from the live context, the two write-back entries). Docs: threat model "Cliniko API client", data-flow intro + flows 3, 6, 18, retention intro + rows 47–48 + a new encounter-record row (appended last so existing row references hold), design system, CHANGELOG.
  - **Expected suite: 3317 passed** (3136 + 181, counted by hand with parametrize expansions: `test_encounter.py` 94, `test_ui_encounter.py` 23, `test_cross_patient.py` 21, `test_session_machine.py` +22, `test_session_types.py` +10, `TestSessionScreenConsent` +8, `test_ui_models.py` +3; the confinement pin renamed, not added). The Windows-only classes (`TestEncounterRecordOnStart`, `TestSessionRefs`) count as passed on the host.
  - Watch items for the pytest run (not runnable by me): (1) `TestSessionRefs.test_discard_and_complete_stop_the_ref_resolving` completes a live queued session after writing a stand-in `transcript.enc` — if `complete()` needs more custody state than that, adjust the test, not the controller. (2) The 4 `test_integration_no_sockets.py` child scripts now import `scribe_desktop.encounter` — its import closure includes `cliniko_client` (no socket at import; the idle child is the check). (3) `test_ui_encounter.py` builds real `MainWindow`s with a temporary registry whose transport is a fake; a re-verification `TaskThread` must finish before teardown (each test waits on `is_reverifying`).
  - Scope notes: the ledger (`VerificationLedger`) has no production caller until Phase 4's pipe (Task 4.5); expiry-driven `session_ref` removal waits for Phase 5 (`forget_session_ref` exists); `NoteDisplay` is shown nowhere yet.
  - For round 20 to weigh (UX, not safety): the checkout's link line lives on the Recovery tab (`recovery_screen.set_link_line`), but opening a recovered session switches to the Transcript screen, so the practitioner sees it only by switching back. Write-back stays refused either way; Phase 4's write UI may be the better home.
  - **Live smoke (practitioner; Task 3.3 is UI-bearing; mock consultation only).** Launch by double-clicking `.venv\Scripts\scribe-app.exe`.
    1. Open the **Session** tab. EXPECT: above Start, "Not linked to a Cliniko note - a recording started here cannot be written back to Cliniko." and an UNTICKED box "I confirm the patient has consented to AI-assisted recording and documentation"; **Start** is greyed out.
    2. Tick the box. EXPECT: Start enables. Untick it. EXPECT: Start greys out again.
    3. Tick the box and press **Start**; speak a few mock sentences, then **Finish**. EXPECT: recording runs as before; the box is unticked again after Start; the link line still says "Not linked to a Cliniko note".
    4. On the **Transcript** screen press **Discard** and confirm. EXPECT: the session is gone as before.
    5. Tick, Start a second mock recording, speak briefly, then end the app from Task Manager (**End task** on scribe-app — a crash stand-in) and relaunch it. Open the **Recovery** tab. EXPECT: the recovered session's row ends "- Cliniko link checked when opened".
    6. Open that recovered session (the app moves to the Transcript screen), then switch back to the **Recovery** tab. EXPECT: the line under the list says "Not linked to a Cliniko note - this recording cannot be written back to Cliniko." and no "checking it with Cliniko" line appears (an unlinked recording makes no Cliniko call). End it with the Transcript screen's **Discard**.
  - Next: the composer runs `cd desktop && ../.venv/Scripts/pytest.exe -q` and resumes an executor for `/review-loop` from round 20 (cap 3) over the whole Phase 3 diff.
- **EXECUTOR HANDOFF (leg `stage-2-exec-b9`, 2026-09-27T18:00+10:00, run stage-2) — Phase 2 BUILD-COMPLETE; `reason=phase-complete`.** Tasks 2.1a, 2.1b and 2.2 are 🟩 (suite 3136; `/review-loop` rounds 15–16; codex pass stage-2.p1 rounds 17–19 converged). Overall Progress `17%` (7 of 41). Task P.1 stays 🟨 (clinic 2 owed). Owed to the practitioner: the live smoke below.
  - **Live smoke (practitioner, clinic 1 only).** Each Validate or Replace key makes a few READ-ONLY calls to Cliniko (your user, your practitioner record, the clinic's public settings); nothing is ever written to Cliniko. Launch by double-clicking `.venv\Scripts\scribe-app.exe`.
    1. Open the **Clinics** tab (between Practitioner and Status). EXPECT: the list is empty, no "Checking the key with Cliniko..." line and no progress bar — nothing contacted Cliniko at startup.
    2. Type a clinic name and your contact email, paste `not-a-key` in the key field, press **Validate**. EXPECT: "That is not a Cliniko API key - a key ends in its region…", the key field emptied, nothing added. (This one is refused locally, before any call.)
    3. Paste the real clinic-1 key (the one P.1 used), leave the web address blank, press **Validate**. EXPECT: "Checking the key with Cliniko..." briefly, then "<name> added - Cliniko confirmed the key, your practitioner record and <clinic>.<shard>.cliniko.com."; the list row reads "<name> - <address> - checked <today>"; the key field is empty and the key shows nowhere on the tab.
    4. Select the clinic, paste the same key again, press **Replace key**. EXPECT: "The key for <name> was replaced and checked with Cliniko."; the row unchanged.
    5. With the clinic selected, press **Remove** once. EXPECT: the button becomes "Confirm remove" and the line says "Press Confirm remove to remove <name>…"; the clinic is still listed. Press **Confirm remove**. EXPECT: "<name> removed, and its key deleted from Windows Credential Manager."; the list is empty. Then re-add it exactly as in step 3, so you end with clinic 1 registered.
    6. Close the app and launch it again. EXPECT: clinic 1 is still listed with the same "checked" date, with no checking line — it was not re-validated. Afterwards, clear the pasted key from clipboard history (Windows key + V).
- **EXECUTOR HANDOFF (leg `stage-2-exec-b8`, 2026-09-27T17:57+10:00, run stage-2) — `/fix` codex round 18 DONE (docs only); round 18 Closed; `reason=phase-complete`.** PR-LOW-080: `retention-schedule.md:48` and the threat-model CLINIC KEYS residue (`threat-model.md:1389-1395`) now give the typed key two separate lifetimes (the Python request until commit; the Qt field's un-zeroed storage until reuse). PR-LOW-081: `retention-schedule.md:47` names the built caller (answers dropped when `_validate` returns; only the ids and subdomain go on to `clinics.json`) and keeps Phase 3 as the next caller. No code or test change: the suite stays 3136. Next: a scoped codex confirmation (round 19); tasks 2.1a/2.1b/2.2 stay 🟨.
- **EXECUTOR HANDOFF (leg `stage-2-exec-b7`, 2026-09-27T17:56+10:00, run stage-2) — codex round 18 LEG 1 VERIFIED (no `/fix`); `reason=phase-complete`.** The b6 tree was GREEN (3136); round 18 confirmed PR-LOW-070. PR-LOW-080 and PR-LOW-081 are both confirmed as LOW, docs-only, surface=docs, Fix-now. PR-LOW-080 adds a class sibling the peer missed: the threat model's CLINIC KEYS residue sentence (`threat-model.md:1389-1391`) ties the Qt buffer to the commit too. PR-LOW-081's model text is flow 18's CALLERS paragraph. Cap verdict: accept. Round 18 stays Open (2 pending) until `/fix`.
- **EXECUTOR HANDOFF (leg `stage-2-exec-b6`, 2026-09-27T17:52+10:00, run stage-2) — `/fix` codex round 17 DONE; round 17 Closed; `reason=composer-run`.** PR-LOW-070 fixed in `clinics.py` `commit_validation`: the worker-refusal return now sits below the gone, rev and stale-id guards, so a delayed refusal after Remove is `CLINIC_GONE` and after a later Replace is `SUPERSEDED`; a current refusal is unchanged. Docstrings (method + module thread-split list) state the order. Ruff clean; mypy 42 files.
  - **Expected suite: 3136 passed** (3132 + 4: three `TestClinicRev`, one `TestDelayedResults`; none removed or changed).
  - Next: the codex docs slice (round 18) and a confirmation; tasks 2.1a/2.1b/2.2 stay 🟨.
- **EXECUTOR HANDOFF (leg `stage-2-exec-b5`, 2026-09-27T17:50+10:00, run stage-2) — codex round 17 LEG 1 VERIFIED (no `/fix`); `reason=phase-complete`.** The b4 tree was GREEN (3132); the in-session review-loop is converged (LOW-011's confirmation folds into the codex pass). PR-LOW-070 is confirmed as LOW, behavioral, production, and Fix-now: a stale worker refusal skips the gone and rev guards and replaces the status line. Fix shape: move the Refused early return below the two guards; three tests. Cap verdict: accept. Round 17 stays Open (1 pending) until `/fix`.
- **EXECUTOR HANDOFF (leg `stage-2-exec-b4`, 2026-09-27T17:45+10:00, run stage-2) — `/review-loop` round 16 (round 2 of cap 3, the post-fix check) RUN; `reason=composer-run`.** The b3 tree was GREEN (3132). Round 16: all five round-15 fixes CONFIRMED; the missed-issue pass found 0 CRIT / 0 HIGH / 0 MED / 1 LOW, applied: LOW-011 `clinics.py` `commit_validation` — a Replace result landing after Remove was always named `SUPERSEDED` (the rev check ran first and Remove always bumps), so the docstring's and the copy's `CLINIC_GONE` was unreachable; now a Replace whose clinic is gone is refused `CLINIC_GONE` before the rev check. Two tests tightened (the registry's permissive either-reason assertion and the tab's delayed-result status line). Ruff clean; mypy 42 files.
  - **Expected suite: 3132 passed** (no test added or removed; two expectations tightened).
  - Round 16 found one LOW, so it is not a clean convergence round: round 17 (round 3 of cap 3) is the post-fix check of LOW-011. Tasks 2.1a/2.1b/2.2 stay 🟨; the codex pass follows convergence.
- **EXECUTOR HANDOFF (leg `stage-2-exec-b3`, 2026-09-27T17:38+10:00, run stage-2) — `/review-loop` round 15 (round 1 of cap 3) RUN and FIXED; `reason=composer-run`.** The b2 tree was GREEN (3128). Round 15: 0 CRIT / 0 HIGH / 1 MED / 4 LOW, all Fix-now, all applied (details in the Findings Log): MED-006 `ui/clinics.py` `_dispatch` — the check thread's closure kept the request (and the typed key) alive for the tab's lifetime; now the holder pattern. LOW-007 a Replace's typed-address mismatch is `ADDRESS_MISMATCH`, not `DIFFERENT_ACCOUNT`. LOW-008 a pasted key's surrounding whitespace is stripped by the tab. LOW-009 flow 18's "on a refusal, nothing" scoped. LOW-010 `_commit_new` deletes whatever a failed store wrote before un-listing the clinic. Ruff clean; mypy 42 files.
  - **Expected suite: 3132 passed** (3128 + 4: two `TestWriteOrder`, two `TestValidate` UI tests; one test's expectation changed, none removed).
  - Watch item: `test_a_finished_check_leaves_no_reference_to_the_request` walks `gc.get_referents` from each finished check thread's `_fn` (found via `findChildren(QThread)`; it asserts at least one exists, so it cannot pass vacuously).
  - Executor recommendation: the other `TaskThread(…, self)` sites (`ui/microphone.py:355`, `ui/recovery.py:237`, `ui/session_screen.py:251`, `ui/transcript.py:643`, `ui/practitioner.py:1097`) keep their closures for their tab's lifetime too. None holds a Cliniko key; whether any retains transcript or profile plaintext is a pre-existing question outside Phase 2 (`ui/note.py`'s prose job already uses the holder). surface=production — a candidate for the hardening stage's whole-surface read, not fixed here.
  - Next: the composer re-runs `cd desktop && ../.venv/Scripts/pytest.exe -q` and resumes me for round 16 (the post-fix regression check).
- **EXECUTOR HANDOFF (leg `stage-2-exec-b2`, 2026-09-27T17:31+10:00, run stage-2) — the b1 tree was GREEN (composer: 3123 passed); P.1 clinic 1 recorded and D10's role amendment BUILT; `reason=composer-run`.** Ruff clean; mypy 42 files.
  - P.1: Task P.1 is 🟨 with a clinic-1 Done note (clinic 2 owed); External / API Findings, both P.1-dependent Accepted Assumptions, the host line, Flow 1 and Agreed Scope marked "confirmed by P.1 clinic 1, 2026-09-27"; the template-default finding is recorded for the Phase 4 plan on the Deferred Phase 4 bullet (not a task here).
  - D10 amended (dated, with the composer's gate record) and built: `clinics.py` no longer reads the user's role — `_user_identity` → `(id, active)`; `_practitioner_records` → `(id, active)` per record; exactly one record, and it active; new `ClinicRefusal.PRACTITIONER_INACTIVE`; `ACCEPTED_USER_ROLES` and `ROLE_NOT_ACCEPTED` removed. The assumption block at the top of `clinics.py` is now "Cliniko's answers, as Task P.1 found them", items (a)–(d) each CONFIRMED (clinic 1) or owed; still unconfirmed: which statuses `/settings/public` refuses with (401/403/404 assumed), and all of clinic 2. Copy: `ui/models.py` (the ROLE line removed; NO_PRACTITIONER_RECORD reworded; PRACTITIONER_INACTIVE added). Docs: threat-model CLINIC KEYS, AGENTS.md step 8, CHANGELOG.
  - Tests as a class (`test_clinics.py`): `USER` is now an administrator (as P.1); `PRACTITIONERS` entries carry `active`; `test_the_role_is_no_gate_one_active_record_decides` ×5 (administrator, practitioner, receptionist, no role, a non-string role — all ACCEPTED); refusals: zero records, two records (both active; one inactive), one INACTIVE record (`PRACTITIONER_INACTIVE`), a record with no or a non-boolean `active` (unreadable); the three role refusals removed.
  - **Expected suite: 3128 passed** (3123 + 5: −1 role test +5 parametrised cases; −3 role refusals +4 practitioner-record refusals).
  - Executor recommendation: `.cursor/plans/explore-cliniko-integration.md` (the Phase 4 plan's input scratch, lines ~109, 135, 174) still says key validation checks "the role is practitioner"; the next plan's `/create-plan` should carry D10 as amended. Not edited here (another plan's scratch). surface=docs.
  - Next: the composer runs `cd desktop && ../.venv/Scripts/pytest.exe -q` and resumes me for `/review-loop` from round 15 (cap 3) over the whole Phase 2 diff.
- **EXECUTOR HANDOFF (leg `stage-2-exec-b1`, 2026-09-27T17:23+10:00, run stage-2) — Tasks 2.1a, 2.1b, 2.2 BUILT, all 🟨 awaiting the composer's pytest; `reason=composer-run`.** Ruff clean; mypy 42 files (40 + `clinics.py` + `ui/clinics.py`). Not run by me: pytest (no grant).
  - What landed (file-by-file on each task's Built note): `desktop/src/scribe_desktop/clinics.py` (new: `ClinicRecord`, the fail-closed loader, `ClinicRegistry.begin_validation` / `run_validation` / `commit_validation` / `remove` / `confirm_subdomain_from_note`, `clinic_rev`); `ui/clinics.py` (new: `ClinicsScreen`); `ui/models.py` (the Clinics copy); `ui/main_window.py` (the "Clinics" tab, the `clinic_registry=` seam, `_live_session_clinic()`, the close guard); `cliniko_client.py` (docstring only); tests `test_clinics.py` (new), `test_ui_clinics.py` (new), `test_cliniko_client.py` (the importer pin), `test_ui_screens.py`, `test_status_and_app.py`, `test_integration_no_sockets.py` (the idle child); docs: threat model, data-flow map, retention schedule, `intended-use.md`, `incident-process.md`, `design-system.md`, `AGENTS.md` step 8, `CHANGELOG.md`.
  - **Expected suite: 2973 + 150 new = 3123 passed** (`test_clinics.py` 132, `test_ui_clinics.py` 18; one `TestConfinement` test renamed, none removed), skips unchanged.
  - **P.1 must confirm** (all in the ONE "P.1 must confirm" block at the top of `clinics.py`, items (a)–(e)): (a) `GET /user` answers `id` (digits, string or number), `role` (a word) and `active` (a JSON boolean); (b) the accepted role set is `{"practitioner"}` — a key whose user's role reads `administrator` is REFUSED as written, so if the practitioner's own user is an administrator-practitioner, D10's "role practitioner" needs a practitioner decision; (c) `GET /practitioners?q[]=user_id:=<id>` answers a `practitioners` list whose entries carry `id`; (d) `GET /settings/public` answers `account.subdomain`, and 401/403/404 there mean "use the typed address" (anything else — 5xx, 429 — is a refusal, not the fallback); (e) the clinic's web-host shard equals its API key's shard.
  - Watch items for the pytest run: (1) `test_ui_clinics.py` imports helpers `from test_clinics import …` (the tests dir is on `sys.path`, as `test_framing.py`'s `from conftest import` already relies on); (2) `TestLoader::test_an_unopenable_file_fails_closed` opens a DIRECTORY as the file (PermissionError on Windows → `UNREADABLE`); (3) two UI tests run a real `TaskThread` against a `threading.Event`-gated transport (10 s bounded waits); (4) if `tests/test_sapi_fixture.py` fails with `AttributeError` in `gencache.py`, that is the stale `gen_py` cache (environment), not this diff.
  - For Phase 3 (not built here, by design): `MainWindow._live_session_clinic()` returns None until a session is linked to a clinic — Phase 3 must answer from the live session's `EncounterContext`; "Replace and Remove clear the clinic's verification outcome" has no outcome to clear yet — Phase 3's outcome must carry the `clinic_rev` it was dispatched under (or listen to `ClinicsScreen.clinics_changed`), and its Credential-Manager key read + the note verification caller must update `TestConfinement`'s importer pin with the threat model and flow 18.
  - No deferral-gate candidates accumulated. Next: the composer runs `cd desktop && ../.venv/Scripts/pytest.exe -q` and resumes me; then `/review-loop` from round 15 (cap 3).
- 2026-09-27 17:00 (leg stage-1-exec-a11, executor claude-opus-5-5): the Task 1.4 live smoke PASSED (practitioner: "pass but cancel review and regenerate was greyed out").
  - **Smoke observation: intended** (pre-existing design, not a regression). Evidence:
    - `ui/note.py:2085-2089` enables "Cancel review and regenerate" only `… and not self._note_saved`. Its comment: "Cancel/regenerate is a PRE-commit escape: available while a draft is under review and not yet saved (round 35 PR-MED-003)".
    - `:2090-2099`: proposal buttons and every "Edit the note" control freeze after Save (D14). This matches the screenshot, where all of them are greyed.
    - `:1834-1837`: Save's own status line says "Acknowledge any review warnings, then Complete on the Transcript screen."
    - This run changed `ui/note.py` only in docstrings (`git diff`: the module docstring `:121-126` and the `_copy_ready` / `_apply_copy_binding` docstrings). No enabling logic changed.
  - **The a10 checklist's step 6 was WRONG**: after Save there is no "Cancel review and regenerate". The correct end of a throwaway session after Save is the Transcript screen's **Discard**. `ui/transcript.py:533` `discard_button.setEnabled(loaded and not generating)`, and after Save the Note tab reports `generating=not self._note_saved` = False (`ui/note.py:2048`), so Discard is enabled. A kept, consented session ends with that screen's **Complete** (`:532`, gated by `complete_block_reason`). "Delete note and complete without one" (`ui/note.py:445-449`, enabled whenever a handler exists, `:2084`) also ends it, but it COMPLETES the session with no note, which is the wrong exit for a mock. The practitioner's session from the smoke is therefore still open; end it with Discard on the Transcript screen.
  - Executor recommendation: no code change (intended behaviour). Record the correct post-Save exits in P.2's checklist wording: Discard for a mock, Complete for a kept session. Optionally, make Save's status line name Discard for a session you do not keep. That is a UX-copy change, and it is the practitioner's call. surface=docs (plan P.2) / production UX copy (`ui/note.py:1834-1837`) if taken.
  - **Clipboard control: practitioner chose (a)** "Keep it out of history and sync (Recommended)" on 2026-09-27.
    - Added as **Task 8.2** in Phase 8, which already owns the security docs it must change, and P.2's live smoke re-checks it. No Phase 2–7 task touches `ui/note.py`'s copy path, and 8.2 has no dependency, so the composer may run it earlier.
    - Overall Progress is now 4 of 41 (`10%`). `AGENTS.md`'s "40 tasks" is for the composer's `/document`.
- 2026-09-27 16:47 (leg stage-1-exec-a10, executor claude-opus-5-5): **Phase 1 is BUILD-COMPLETE.** Tasks 1.1–1.4 are 🟩 and Overall Progress is `10%`.
  - Suite 2973; codex passes stage-1.p1 (rounds 8–10) and stage-1.p2 (rounds 13–14) converged.
  - Still owed: the practitioner's LIVE SMOKE of Task 1.4, because the Note tab's Copy button is now shown by default.
  - **Live-smoke checklist.** Use a throwaway recording: speak a mock consultation yourself, never a real patient.
    1. Launch the app by double-clicking `.venv\Scripts\scribe-app.exe` in Explorer (never from an ephemeral terminal). Expect it to open normally; a second launch says "already running".
    2. On the Session screen press Start, speak about 30 s of mock consultation (e.g. "left knee sore for two weeks, ice pack advised"), then press Finish. Expect the Transcript screen to open with the transcript.
    3. Confirm the clinician role and the template profile, then press "Generate note". Expect the Note tab to open with the draft beside the transcript. The "Copy note" button is VISIBLE but greyed out, and note text cannot be selected.
    4. Try to select text in the transcript panel, and press Ctrl+A / Ctrl+C in it. Expect nothing to be selectable and nothing to be copied. This stays true for the whole review.
    5. Confirm or Decline every proposal, then press "Acknowledge all review warnings". After each of these, "Copy note" is still greyed out. Then press "Save note". Now "Copy note" is ENABLED and the note text is selectable. With no proposals and no warnings, only Save enables it.
    6. Press "Copy note" and paste into Notepad (not Cliniko). Expect exactly the note body: section titles and note lines, no transcript lines. Then close Notepad without saving, copy any harmless text to overwrite the clipboard, and end the session: "Cancel review and regenerate", then Discard on the Transcript screen. Expect nothing to be kept.
  - **Open practitioner decision — the clipboard control** (the a7 Executor recommendation, kept open). surface=production (`ui/note.py` `_copy_note`) + docs (threat-model 3A surface 4, the retention clipboard row). The options, recommended first:
    - (a) **RECOMMENDED:** mark the copy so Windows keeps it out of clipboard history and cloud sync. This means adding the `ExcludeClipboardContentFromMonitorProcessing`, `CanIncludeInClipboardHistory=0` and `CanUploadToCloudClipboard=0` formats through `QMimeData`. It is small, it does not change what gets pasted, and it closes the cloud-sync route regardless of the machine's settings.
    - (b) Also clear the clipboard after a timeout (e.g. 2 minutes), but only if it still holds the copied note. This lowers how long the note lingers, at the cost of an occasional surprise when a slow paste finds the clipboard empty.
    - (c) Leave it as is: the operating rule "cloud clipboard sync off" in `intended-use.md` stays the only mitigation.
- 2026-09-27 16:42 (leg stage-1-exec-a9, executor claude-opus-5-5): `/fix` on codex round 13, which is now CLOSED.
  - PR-LOW-050 is fixed as a class, docstrings and comments only: `ui/note.py` `_copy_ready` / `_apply_copy_binding`, `ui/models.py:524` `format_note_body`, and eight `test_ui_screens.py` docstrings or comments. No predicate, assertion or test name changed. The widened grep finds zero hits in `desktop/`.
  - PR-LOW-051 is fixed: flow 10 is scoped to what the app holds, with the Copy named as the one exception. The sibling threat-model 3A surface 3 sentence is scoped the same way.
  - The Review History line for round 13 is written; ruff is clean and mypy covers 40 files.
  - Expected pytest: **2973 passed** (only comment and docstring changes).
  - Task 1.4 stays 🟨 for the scoped codex confirmation round.
  - The a7 bullet's second Executor recommendation is done here. Its first one, a clipboard-clearing or clipboard-history-exclusion control, stays open for the practitioner.
- 2026-09-27 16:39 (leg stage-1-exec-a8, executor claude-opus-5-5): composer pytest on the a7 tree was GREEN at 2973 passed. I verified codex round 13 (pass stage-1.p2); it stays Open. The tuples:
  - PR-LOW-050 → docs-only / low / docs / Fix-now as a class. Six stale "9.1 gate/flag" docstring and comment sites, plus the unnamed sibling `ui/models.py:524`.
  - PR-LOW-051 → docs-only / low / docs / Fix-now. Flow 10's unscoped memory and storage claims.
  - Cap verdict: accept — docs-only.
  - This supersedes the a7 bullet's second Executor recommendation (the `_copy_ready` / `_apply_copy_binding` docstrings), which is now PR-LOW-050's fix. No code changed in this leg.
- 2026-09-27 16:34 (leg stage-1-exec-a7, executor claude-opus-5-5):
  - Part A: Tasks 1.1–1.3 are 🟩, Overall Progress `8%`.
  - Part B: Task 1.4 is BUILT and 🟨. The flag Edit was NOT refused.
  - What landed:
    - `desktop/src/scribe_desktop/ui/models.py:449` `COPY_TO_CLINIKO_ENABLED: Final[bool] = True`, with the D12 comment at `:440-448`.
    - `desktop/tests/test_ui_screens.py:3532` `test_default_copy_binding_ships_enabled`.
    - The `ui/note.py:121-126` docstring.
    - The `docs/testing/shipping-gate.md` reframing; design-system, threat-model 3A surface 4, flow 10, `PLAN.md:110`, `AGENTS.md`, CHANGELOG (Changed), and the phase-3a Task 9.1 REFRAMED bullet.
    - Round 11's MED-005 (docs-only), which names the copied note's Windows-clipboard residue in threat-model surface 4, flow 10, a new retention row and `intended-use.md`.
  - Every grep hit's disposition is in Task 1.4's BUILT note.
  - Review: `/review-loop` rounds 11 (1 MED, applied) and 12 (0) converged. ruff is clean and mypy covers 40 files.
  - Expected pytest: **2973 passed** (one test renamed; none added or removed).
  - **Executor recommendation:** the copied note stays on the Windows clipboard indefinitely, and cloud clipboard sync can carry it off the machine. A small code control would close most of that: after a copy, clear the clipboard once a timeout passes, if the clipboard still holds the copied text; or mark the copy with Windows' `ExcludeClipboardContentFromMonitorProcessing` / `CanIncludeInClipboardHistory=0` / `CanUploadToCloudClipboard=0` formats through `QMimeData`. That is a behaviour change beyond D12, so it is the practitioner's call. surface=production (`ui/note.py` `_copy_note`) + docs (threat-model 3A surface 4, the retention clipboard row).
  - **Executor recommendation:** the `ui/note.py` `_copy_ready` (`:1996-2004`, "even after Task 9.1 flips the flag") and `_apply_copy_binding` (`:2012`, "per the 9.1 shipping flag") docstrings are stale wording. They were left because D12 keeps `_copy_ready` untouched; a docstring-only reword is safe. surface=docs-in-code.
  - Composer's `/document` owns the `AGENTS.md:60` status ("0%", "NEXT: Task 1.1").
- **EXECUTOR HANDOFF (leg `stage-1-exec-a6`, 2026-09-27T16:22+10:00, run stage-1) — codex round 9 FIXED (docs-only) and CLOSED; `reason=phase-complete`.** The a4 pytest was GREEN (2973 passed). PR-MED-030 fixed as a class: every Cliniko exception claim is now scoped to what an exception RENDERS, and the traceback-frame memory residue is named. Sites: threat-model SECRETS + RESIDUE (2) + new RESIDUE (6); the in-use-key retention row (text + destruction column); data-flow flow 3 (`:65-68`) and flow 18 (`:499-506`); the `cliniko_client.py` module docstring (`:41-51`, `:59-62`). The sibling grep and the sites deliberately left are on the finding's `/fix decision` line. No code behaviour or test changed (docstring only); ruff clean, mypy 40 files; the suite should stay 2973. Nothing found beyond PR-MED-030. 1.1–1.3 stay 🟨 until the scoped confirmation round 10.
- **EXECUTOR HANDOFF (leg `stage-1-exec-a5`, 2026-09-27T16:20+10:00, run stage-1) — codex round 9 LEG 1 VERIFIED, nothing changed.** PR-MED-030 confirmed, downgraded to LOW. Exception tracebacks keep the call's frames — the key before `del api_key`, `_get`'s `headers` with the Basic token, and the path/ids/body — referenced while the exception lives. No rendered channel carries them. Rec: Fix-now, docs-only. Cap verdict: accept. **LEG 2 would:** scope each "no exception carries…" sentence to the rendered text, and add the traceback-frame memory residue to threat-model SECRETS/RESIDUE, the in-use-key retention row, data-flow flows 3 (:67) and 18 (:499), and the `cliniko_client.py` module docstring. No code change (`traceback.clear_frames` was rejected — it would wipe the caller's frames). Round 9 stays Open (1 pending); the a4 pytest result (expected 2973) is owed to LEG 2.
- **EXECUTOR HANDOFF (leg `stage-1-exec-a4`, 2026-09-27T16:14+10:00, run stage-1) — codex round 8 FIXED and CLOSED (LEG 2 `/fix`); `reason=composer-run`.** What landed: `cliniko_client.py` — `_read_bounded` reads with `response.read1` (the `_Response` protocol exposes `read1` only; PR-MED-010), `HTTPSTransport.request` reads a body only when `status == 200` (PR-MED-012), and the deadline comment, `RawResponse`/class/module docstrings state both; `scripts/probe-cliniko.py` `main` refuses any argument but `-h/--help` with fixed text before argparse (PR-MED-011); `test_cliniko_client.py` — `FakeResponse.read1` (and a `read` that fails the test), the drip test on `read1`, `test_a_refusal_whose_body_stalls_keeps_its_own_name` ×7, `test_a_non_200_answer_carries_no_body`, the digit-limit case pinned to `sys.set_int_max_str_digits(4300)` and restored (PR-LOW-013); `test_probe_cliniko.py` — `test_an_argument_is_refused_without_echoing_it` ×5 and `test_help_alone_still_prints_the_help` (replacing the old SystemExit-only test). Docs as a class: threat-model TRANSPORT (read1 + the per-step-only residue incl. chunked framing) and UNTRUSTED ANSWERS (200-only body), flow 18, the API-responses retention row, CHANGELOG. One logged sibling beyond the four (module docstring's "one Credential Manager read" — round 7 LOW-003's class). Ruff clean, mypy 40 files. **Expected suite: 2973 passed** (2960 + 14 new − 1 replaced). 1.1–1.3 stay 🟨 — the docs slice (codex round 9) follows.
- **EXECUTOR HANDOFF (leg `stage-1-exec-a3`, 2026-09-27T16:10+10:00, run stage-1) — codex round 8 LEG 1 VERIFIED, no code changed.** The composer's pytest on the a2 tree was GREEN (2960 passed). Round 8 tuples: PR-MED-010 med/production Fix-now; PR-MED-011 downgraded low/production Fix-now; PR-MED-012 med/production Fix-now; PR-LOW-013 low/test-harness Fix-now; Cap verdict accept. **LEG 2 (/fix) would:** read the body with `response.read1` (one receive per call, `in_time()` before each; the residue named in threat-model TRANSPORT and the constant's comment); consume a body only on 200 (a stalled 401/403/404/429/3xx keeps its own named error and the 429 its reset); refuse any probe argument but `-h/--help` with fixed text before argparse; pin `sys.set_int_max_str_digits(4300)` for the digit-limit case — each with a test through the real transport seam or capsys. Round 8 stays Open (4 pending); the /fix seat writes its Review History line.
- **EXECUTOR HANDOFF (leg `stage-1-exec-a2`, 2026-09-27T15:59+10:00, run stage-1) — `/review-loop` CONVERGED at round 7 (round 1 of cap 3): 0 CRIT / 0 HIGH / 0 MED / 4 LOW, all applied; `reason=composer-run` for the re-run.** The a1 suite (2956 passed, 2 errors) failed only the setup/teardown of the 100 000-deep-array case — its generated parametrize id overflowed Windows' 32 767-char `PYTEST_CURRENT_TEST`; all eight bodies now carry explicit `pytest.param(..., id=...)`. Round 7 fixes (details in the Findings Log): LOW-001 a 30 s request deadline (`DEADLINE_SECONDS`, injectable `clock`) checked after the send and before every body read, beside the 15 s per-step timeout — code, threat model, flow 18, CHANGELOG; LOW-002 `RawResponse.body` out of the repr; LOW-003 two doc sentences made exact (allocation bound incl. `http.client`'s header limits; the key row's reader); LOW-004 the probe's key-printing residue named. Ruff clean, mypy 40 files. **Expected suite: 2960 passed** (2957 + 3 new: two deadline tests, one repr test), 0 errors. On green: mark 1.1/1.2/1.3 🟩, progress 3/40, end `reason=phase-complete` (no further in-session round needed — round 7 had no CRIT/HIGH/MED). Task 1.4's answer ("flip") is recorded on its line; not built here.
- **EXECUTOR HANDOFF (leg `stage-1-exec-a1`, 2026-09-27T15:48+10:00, run stage-1) — Tasks 1.1, 1.2, 1.3 BUILT, all 🟨 awaiting the composer's pytest; `reason=composer-run`.** Ruff clean; mypy 40 files (39 + `cliniko_client.py`). Not run by me: pytest (no grant). **Expected suite: 2817 + 140 new = 2957 passed** (`test_cliniko_client.py` 126, `test_probe_cliniko.py` 14), skips unchanged; the existing `test_integration_no_sockets.py` legs are untouched in code (docstring only) and must stay at zero connections — nothing imports the client. What landed: `desktop/src/scribe_desktop/cliniko_client.py` (new; the one `noqa: TID251` at `:57`), `benchmark.py` (`FORBIDDEN_TLS_OVERRIDES`, `apply_offline_env`/`assert_offline_env`), `scripts/probe-cliniko.py` (new), the two test files, the docs listed in 1.2's Done note (its two greps and every hit's disposition are recorded there), `CHANGELOG.md`, `scripts/README.md`. Deviations recorded on the tasks: two named errors added beyond D9's list (`RedirectRefused`, `UnexpectedStatus`); the probe prints the key user's account role word; `language_model.py:21` left unchanged (accurate as scoped). **Watch items for the pytest run:** (a) `TestConfinement` counts `noqa: TID251` across `desktop/src` — exactly 1 expected; (b) `TestTlsContext` builds a real `SSLContext` and calls `load_default_certs` (reads the Windows store, no network); (c) `TestStatusMapping` feeds a 100 000-deep JSON array to prove `RecursionError` → `Malformed`; (d) if `tests/test_sapi_fixture.py` fails with `AttributeError` in `gencache.py`, that is the stale `gen_py` cache (environment), not this diff. **Next:** composer runs `cd desktop && ../.venv/Scripts/pytest.exe -q` and resumes me; then `/review-loop` from round 7 (cap 3). P.1 and the Task 1.4 must-pause stay with the practitioner/composer (untouched: `COPY_TO_CLINIKO_ENABLED`, `ui/models.py`, `shipping-gate.md`).
- **COMPOSER RUN-STATE (2026-09-27 21:25, `/execute-loop` run iso `cliniko-safeguards-20260927-152609-a3c9bc86`, isolation=none, branch main):** PHASE 1 CLOSED (stage-1, commit 32e7289). PHASE 2 CLOSED (stage-2, commit dc6530b). PHASE 3 CLOSED (stage-3): Tasks 3.1–3.6 🟩 (13 of 41, 32%); `/review-loop` rounds 20–21; codex pass stage-3.p1 (rounds 22–24; PR-LOW-100 and PR-LOW-110 auto-disposed Fix-now under gates=executor, fixed in leg c5, confirmed by round 24) converged; composer pytest 3323 passed; practitioner live smoke PASS (OWNERSHIP smoke-pass 21:22); queued notices flushed 20:03; `/document` run by the composer (AGENTS.md; `explore-cliniko-integration.md` carries the executor's Phase 4-plan recommendation on the write-back guard's re-verification age); committed locally (never pushed). Carried to the hardening stage: the executor's `TaskThread(…, self)` closure-site recommendation (c6 handoff). **Immediate next action:** spawn the Phase 4 executor (runkey stage-4, fresh session) on Phase 4's tasks. Last plan sync: 2026-09-27 21:25.
- Loop config: executor=claude-p model="claude-opus-5-5" effort=high profile=default; peer=codex model="gpt-6-astra" effort=medium; architect=off; cadence=every-phase; caps=review:3,peer:5; gates=executor; cap-raise=executor; high-auto=on; peer-max=12; notify=action-only; scope=all; autocommit=on; isolation=none; merge=off; perms=scoped; liveness=10; monitor-delivery=auto; verify=composer
- Earlier step: `/review-plan` hardening pass (2026-09-27; four lens subagents — coverage, practicality, risk, simplicity; ~45 findings folded in; deferral gate recorded).
- Last completed step: `/peer-loop` plan review (codex `gpt-6-astra` medium), converged at round 6. Round 1: 5 findings (2 HIGH, 3 MED), all accepted and amended. Round 2 (attempt 1 inconclusive on the codex usage limit; resumed session `01a0e113`): 3 MED, all accepted and amended. Round 3: 2 MED (connection generation for verification results; per-connection snapshot), accepted and amended. Round 4: 1 MED (clinic key changes invalidate pending verification — `clinic_rev`), accepted and amended. Round 5: 1 MED (removing a clinic — Remove refused while the live session is linked; page-script teardown), accepted and amended. The pass hit its cap of 5 without a clean round; the practitioner approved one more round, and round 6 was clean (0 findings) — the loop CONVERGED.
- Current in-progress step: None
- Immediate next action (superseded 2026-09-27 15:30 — the hardened plan was committed as `51f91ab`/`f9887a7`; see the COMPOSER RUN-STATE bullet above): Task 1.1 via `/execute-loop`.
- Open blockers / open questions:
  - Task P.1 (practitioner) confirms D10's subdomain route and the note-link fields.
  - Task 1.4 is a composer must-pause (the permission classifier blocked the flag edit during planning).
  - Task 6.0 needs the practitioner's authorisation for a dev dependency.
  - `[decision]` tasks remain at 4.3 (default (b)) and 5.4 (review-reopen custody).
- Last plan sync: 2026-09-27

## Review History
- 2026-09-27 round 7: 0 CRIT / 0 HIGH / 0 MED / 4 LOW; skew=none; action=none
- 2026-09-27 round 8 (codex gpt-6-astra medium, pass stage-1.p1 slice A): 0 CRIT / 0 HIGH / 3 MED / 1 LOW; all fixed; skew=none; action=none
- 2026-09-27 round 9 (codex gpt-6-astra medium, pass stage-1.p1 slice B): 0 CRIT / 0 HIGH / 1 MED / 0 LOW; fixed (docs-only); skew=none; action=none
- 2026-09-27 round 10 (codex gpt-6-astra medium, pass stage-1.p1 confirmation): 0 CRIT / 0 HIGH / 0 MED / 0 LOW; 5/5 round-8/9 fixes confirmed; pass converged at peer_round 3 of cap 5; skew=none; action=none
- 2026-09-27 round 11 (Task 1.4, /review-loop round 1 of cap 3): 0 CRIT / 0 HIGH / 1 MED / 0 LOW; MED-005 applied (docs-only: the clipboard residue of the enabled copy); skew=none; action=none
- 2026-09-27 round 12 (Task 1.4, /review-loop round 2 of cap 3, post-fix check): 0 CRIT / 0 HIGH / 0 MED / 0 LOW; MED-005 confirmed; converged; skew=none; action=none
- 2026-09-27 round 13 (codex gpt-6-astra medium, pass stage-1.p2): 0 CRIT / 0 HIGH / 0 MED / 2 LOW; both fixed (docs-only); skew=none; action=none
- 2026-09-27 round 14 (codex gpt-6-astra medium, pass stage-1.p2 confirmation): 0 CRIT / 0 HIGH / 0 MED / 0 LOW; 2/2 round-13 fixes confirmed; pass converged at peer_round 2 of cap 5; skew=none; action=none
- 2026-09-27 round 15 (Phase 2, /review-loop round 1 of cap 3): 0 CRIT / 0 HIGH / 1 MED / 4 LOW; all applied (MED-006 the worker closure retained the typed key; LOW-007..010); skew=none; action=none
- 2026-09-27 round 16 (Phase 2, /review-loop round 2 of cap 3, post-fix check): 0 CRIT / 0 HIGH / 0 MED / 1 LOW; 5/5 round-15 fixes confirmed; LOW-011 applied (a Replace result after Remove was named SUPERSEDED, not CLINIC_GONE); skew=none; action=none
- 2026-09-27 round 17 (codex gpt-6-astra medium, pass stage-2.p1 slice A): 0 CRIT / 0 HIGH / 0 MED / 1 LOW; fixed (PR-LOW-070 a stale worker refusal skipped the gone and rev guards); skew=none; action=none
- 2026-09-27 round 18 (codex gpt-6-astra medium, pass stage-2.p1 slice B): 0 CRIT / 0 HIGH / 0 MED / 2 LOW; PR-LOW-070 confirmed; both fixed (docs-only; PR-LOW-080 with its threat-model sibling); skew=none; action=none
- 2026-09-27 round 19 (codex gpt-6-astra medium, pass stage-2.p1 confirmation): 0 CRIT / 0 HIGH / 0 MED / 0 LOW; 2/2 round-18 fixes confirmed; pass converged at peer_round 3 of cap 5; skew=none; action=none
- 2026-09-27 round 20 (Phase 3, /review-loop round 1 of cap 3): 0 CRIT / 0 HIGH / 1 MED / 5 LOW; all applied (MED-012 a live session's Start verification sufficed for write-back; LOW-013..017); skew=none; action=none
- 2026-09-27 round 21 (Phase 3, /review-loop round 2 of cap 3, post-fix check): 0 CRIT / 0 HIGH / 0 MED / 0 LOW; 6/6 round-20 fixes confirmed; converged; skew=none; action=none
- 2026-09-27 round 22 (codex gpt-6-astra medium, pass stage-3.p1 slice A): 0 CRIT / 0 HIGH / 0 MED / 1 LOW; fixed (PR-LOW-100 test-harness: distinct per-clinic fake keys; the other-clinic test verifies B's credential); skew=none; action=none
- 2026-09-27 round 23 (codex gpt-6-astra medium, pass stage-3.p1 slice B): 0 CRIT / 0 HIGH / 0 MED / 1 LOW; fixed (PR-LOW-110 docs-only: the linked consent's practitioner is bound only when named); skew=none; action=none
- 2026-09-27 round 24 (codex gpt-6-astra medium, pass stage-3.p1 confirmation of rounds 22-23): 0 CRIT / 0 HIGH / 0 MED / 0 LOW; clean (PR-LOW-100 and PR-LOW-110 confirmed); skew=none; action=none — pass stage-3.p1 converged at peer_round 3 of 5

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

### Round 7 - 2026-09-27 - Phase 1 (Tasks 1.1–1.3: Cliniko read client, offline-contract rewrite, feasibility probe), `/review-loop` round 1 of cap 3

- Round status: Closed (0 pending) — 4 LOW, all Fix-now, all applied in this leg; converged (no CRIT/HIGH/MED)
- Source: Claude Code (executor leg stage-1-exec-a2, claude-opus-5-5, sequential lenses in-session — no subagents)
- Scope / baseline: the Phase 1 working-tree diff over `f9887a7` — `desktop/src/scribe_desktop/cliniko_client.py` (new, read in full), `benchmark.py` (diff + both functions), `desktop/tests/test_cliniko_client.py` and `test_probe_cliniko.py` (new, read in full), `scripts/probe-cliniko.py` (new, read in full), `pyproject.toml`, `ui/__init__.py`, `logging_setup.py`, the `test_integration_no_sockets.py` docstring, the five security docs (`data-flow-map.md`, `threat-model.md`, `retention-schedule.md`, `intended-use.md`, `incident-process.md` — every changed passage re-read against the code), `AGENTS.md`, `CHANGELOG.md`, `scripts/README.md`, `scripts/setup-models.py` and `desktop/requirements-ml-prose.txt` headers. Composer suite on the pre-round tree: 2956 passed, 2 errors — setup and teardown of ONE parametrised case whose generated id was the 100 000-deep array (Windows caps `PYTEST_CURRENT_TEST` at 32 767 chars); fixed before the round by explicit `pytest.param(..., id=...)` on all eight bodies (test-harness only; the case and its `RecursionError` → `Malformed` proof kept).
- Lenses and results:
  - Correctness / security — the host pin, GET-only guard, `_classify` order against the `http.client`/`ssl` raise set, `_guarded`'s no-context raise, the bounded read, the status map, the key's single read and drop: correct. Found LOW-001 (no overall deadline) and LOW-002 (the body in `RawResponse`'s repr).
  - Plan adherence (D9, Constraints 1, 2, 8, 12) — CLEAN: no write method, one module, pinned host from a validated shard, no redirects/proxy, TLS 1.2+, `SSLKEYLOGFILE` removed and refused, one `noqa: TID251`. Recorded deviations (two extra named errors; the probe's role word) are on the Task lines.
  - Docs as control claims (lessons 2026-08-14, 2026-09-20) — found LOW-001's doc half ("a 15 s timeout" read as a request bound), LOW-003 (the allocation sentence omitted `http.client`'s own header limits and the reader buffer; the retention row named Credential Manager as the reader, which is the Phase 2 caller's source, not the client's), LOW-004 (the probe's key rule claimed "can never print" without naming the identifier-shaped-key residue).
  - Executor judgment / structural quality — none (the module is ~480 lines, one seam per concern; no duplicated helper — `SecureStorageProvider` and `log_event` untouched and unneeded).
  - Missed-issue pass: re-read `cliniko_client.py` in full, `benchmark.py:57-140`, `scripts/probe-cliniko.py` in full, the threat-model "Cliniko API client" section and flow 18; result: LOW-003, LOW-004 (from this pass).
- Findings:
  - **[LOW]** LOW-001: `desktop/src/scribe_desktop/cliniko_client.py:277-302` — only a per-socket-operation timeout: a body dripping one byte per receive kept a request alive without end, and the docs said "a 15 s timeout" — Triage: Fix-now; Decision: Applied — `DEADLINE_SECONDS = 30.0` and an injectable `clock` on `HTTPSTransport`; `in_time()` checked after the send and before every body read (`_read_bounded(..., in_time)`), raising `Unreachable` outside any `except`; the constant's comment, threat-model TRANSPORT, flow 18 and CHANGELOG now state both bounds exactly (a single library call stays bounded only per step — named). Tests: `test_a_slow_drip_body_is_abandoned_at_the_deadline`, `test_a_slow_request_is_abandoned_before_the_answer_is_read`.
  - **[LOW]** LOW-002: `cliniko_client.py:188-195` — `RawResponse`'s dataclass repr included `body`, patient data, so a stray repr in a log or traceback would carry it — Triage: Fix-now; Decision: Applied — `body: bytes = field(repr=False)` (equality unchanged). Test: `test_the_raw_response_repr_carries_no_body`.
  - **[LOW]** LOW-003: `docs/security/threat-model.md` ("UNTRUSTED ANSWERS") and `docs/security/retention-schedule.md` (the in-use key row) — two sentences stronger than the structure — Triage: Fix-now; Decision: Applied — the allocation sentence now says "in total, plus the stdlib reader's own buffer" and names `http.client`'s header limits (100 lines × 64 KiB) as the stdlib's bound; the key row says the client calls `read_key` exactly once and that Credential Manager is the Phase 2 source.
  - **[LOW]** LOW-004: `scripts/probe-cliniko.py` (module docstring, `shape`) — "so a data-bearing key can never print" overclaimed: an identifier-shaped data-bearing key would print — Triage: Fix-now; Decision: Applied — both docstrings name the residue (Cliniko keys objects by fixed field names).
- Verification counts: 5 lenses run, 4 candidates, 0 dropped, 0 downgraded
- ruff clean; mypy 40 files; pytest owed to the composer (expected 2957 + 3 = 2960 passed)
- Last reviewed: 2026-09-27

### Round 8 - 2026-09-27 - Phase 1 (Tasks 1.1–1.3) code slice, independent cross-family codex peer review (pass stage-1.p1 slice A)

- Round status: Closed (0 pending) — all four fixed in leg stage-1-exec-a4 (2026-09-27); pytest owed to the composer
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Pinned Phase 1 slice A files and specified plan contracts; static inspection only, no writes, tests or network commands.
- **PR-MED-010** (MED, behavioral, `desktop/src/scribe_desktop/cliniko_client.py:347`): The deadline does not bound a slow-drip response body. `HTTPResponse.read(amt)` can perform repeated socket receives before returning; a peer sending bytes within each socket timeout can keep this call blocked well beyond 30 seconds. The test instead makes each simulated receive return from `read`, so it misses the actual failure. — Evidence: `in_time()` followed by `chunk = _guarded(partial(response.read, allowance - total))`; `desktop/tests/test_cliniko_client.py:484` uses `FakeResponse(body=b"x" * 100, chunk=1)`. Recommendation: Fix-now — Enforce the remaining deadline during underlying reads, preserve the allocation cap, and cover buffered multi-receive behavior with a socket-free regression test. /fix decision: Fixed — `cliniko_client.py` `_read_bounded` now reads with `response.read1` (one receive per call; the `_Response` protocol exposes `read1` only), `in_time()` still before each; the deadline comment, module docstring and threat-model TRANSPORT name the per-step-only residue (connect/handshake/send, status + headers, chunked framing); `FakeResponse.read` now fails the test and the drip test drives `read1` (leg stage-1-exec-a4, 2026-09-27)
- **PR-MED-011** (MED, behavioral, `scripts/probe-cliniko.py:249`): Passing a key accidentally as an argument prints that key to stderr: default argparse rejection includes the unrecognized argument verbatim. The existing test exercises precisely this path but checks only `SystemExit`, missing the secret disclosure. — Evidence: `argparse.ArgumentParser(...).parse_args(argv)`; `desktop/tests/test_probe_cliniko.py:306–307`: `with pytest.raises(SystemExit):` and `probe.main([KEY], ...)`. Recommendation: Fix-now — Reject unexpected arguments with fixed text that never interpolates their values; assert captured stdout and stderr contain no key for positional and option-shaped inputs. /fix decision: Fixed — `scripts/probe-cliniko.py` `main` refuses any argument but `-h`/`--help` with a fixed sentence (never interpolated) BEFORE argparse, asks nothing and sends nothing; `test_an_argument_is_refused_without_echoing_it` (positional, `--key=`, `-k <key>`, `--help <key>`, email+URL) checks captured stdout+stderr, and `test_help_alone_still_prints_the_help` keeps `--help` (leg stage-1-exec-a4, 2026-09-27)
- **PR-MED-012** (MED, behavioral, `desktop/src/scribe_desktop/cliniko_client.py:317`): Reading every response body before interpreting its status can replace an already-known refusal with the wrong error. For example, a 401 or 403 whose body stalls or is truncated becomes `Unreachable`, losing the credential refusal; a 429 similarly loses its rate-limit classification and reset information. — Evidence: `status = _guarded(lambda: int(response.status))`, then `body = _read_bounded(response, max_body, in_time)`; `CredentialsRejected(status)` is raised only later at line 474. Recommendation: Fix-now — Classify non-200 statuses without consuming their unused bodies, close the connection, and test known refusal statuses with failing body readers through the real transport seam. /fix decision: Fixed — `cliniko_client.py` `HTTPSTransport.request` reads a body only when `status == 200` (`RawResponse.body = b""` otherwise; the class, `RawResponse` and module docstrings state the policy; threat-model UNTRUSTED ANSWERS, flow 18 and the retention row say so); `test_a_refusal_whose_body_stalls_keeps_its_own_name` (401, 403, 404, 429 with its reset, 302, 422, 503 — each over a reader that raises `IncompleteRead`, never touched) and `test_a_non_200_answer_carries_no_body` (leg stage-1-exec-a4, 2026-09-27)
- **PR-LOW-013** (LOW, test-harness, `desktop/tests/test_cliniko_client.py:279`): The integer-overflow case depends on the interpreter’s ambient integer-string conversion limit. With `PYTHONINTMAXSTRDIGITS=0` or a limit above 5000, this body is a valid JSON object and the test fails despite correct client behavior. — Evidence: `pytest.param(b'{"n": ' + b"9" * 5000 + b"}", id="int-over-digit-limit")` feeds an unconditional `with pytest.raises(cc.Malformed)` at line 284. Recommendation: Fix-now — Set and restore a known integer conversion limit for this case, or inject the decoder failure when testing its error mapping. /fix decision: Fixed — `test_a_body_that_is_not_a_json_object_is_malformed` sets `sys.set_int_max_str_digits(4300)`, asserts it took, and restores the host's value in `finally` (test-only; leg stage-1-exec-a4, 2026-09-27)
- Verification counts: 4 claims checked, 4 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-27

#### LEG 1 verified tuples (executor, leg stage-1-exec-a3)
Evidence note: this leg's shell has no read grant on the base interpreter's stdlib (`C:\Python314\Lib`, the venv's `home` per `.venv/pyvenv.cfg`), so PR-MED-010's stdlib chain is verified from CPython 3.12–3.14's `http.client` as released (not re-read on disk). `HTTPResponse.read(amt)`, for a Content-Length body, clips `amt` to `self.length` and returns `self.fp.read(amt)`. `self.fp` is `sock.makefile("rb")`, a `BufferedReader`, whose `read(n)` issues raw reads until it has `n` bytes or reaches EOF. A chunked body goes `_read_chunked` → `_safe_read`, which loops the same way. So ONE `read(amt)` spans many `recv`s, each bounded only by the 15 s socket timeout. `HTTPResponse.read1(n)` → `BufferedReader.read1(n)` does at most ONE raw read (for a chunked body: plus the chunk-size line's bounded `readline`).
- PR-MED-010 (peer: MED, behavioral) → `materiality=behavioral severity=verified: med surface=production rec=Fix-now — confirmed: cliniko_client.py:_read_bounded calls response.read(allowance - total), a multi-recv call, so the deadline checked BETWEEN calls does not bound a drip inside one; shape: read with response.read1(allowance - total) (one receive per call; add read1 to the _Response protocol), keep in_time() before each call and the allowance cap unchanged, name the remaining residue exactly (a single receive ≤ 15 s past the deadline; a chunked body's chunk-size line and the status/header read stay bounded per step only); test: FakeResponse gains read1 recording each call and a read() that FAILS the test if called, the drip test drives read1 one byte per call and asserts Unreachable at the deadline; threat-model TRANSPORT + the constant's comment reworded to match. In Task 1.1 scope, no dependency.`
- PR-MED-011 (peer: MED, behavioral) → `materiality=behavioral severity=verified: low surface=production rec=Fix-now — confirmed: probe-cliniko.py main() → ArgumentParser.parse_args(argv) → on an unknown positional, argparse's error() prints "unrecognized arguments: <value>" to stderr, so a key given as an argument is echoed. Downgraded to LOW because the precondition is the practitioner already typing the key into the shell (on screen and in its history) — but it breaks the script's own "never prints the key" claim. Shape: before any parsing, if argv holds anything other than -h/--help, print a fixed sentence (no interpolation) and return 2; test with capsys for a positional, an --key=<value> option shape and a -k <value> pair: stdout+stderr carry no key and nothing is sent. In Task 1.3 scope (a practitioner-run tool, not the app).`
- PR-MED-012 (peer: MED, behavioral) → `materiality=behavioral severity=verified: med surface=production rec=Fix-now — confirmed: HTTPSTransport.request reads status, then _read_bounded for EVERY status; a 401/403/429 whose body stalls or is cut becomes Unreachable (IncompleteRead/timeout) — under D4 that turns a named refusal (Start refused) into unverified_offline (recording allowed; write-back still blocked, so fail-safe for write-back but wrong for Start), and a 429 loses its reset. Shape: the transport consumes a body only when status == 200 (RawResponse.body = b"" otherwise; docstring states the policy); the connection is closed in the existing finally. Tests through the real transport seam: 401, 403, 404, 429 (with a reset header) and a 3xx each with a FakeResponse whose read/read1 raise IncompleteRead → the status's own named error, read never called. In Task 1.1 scope.`
- PR-LOW-013 (peer: LOW, test-harness) → `materiality=behavioral severity=verified: low surface=test-harness rec=Fix-now — confirmed: the int-over-digit-limit body is Malformed only while sys.get_int_max_str_digits() is in (0, 5000); PYTHONINTMAXSTRDIGITS=0 or -X int_max_str_digits>5000 makes it a valid object (lessons 2026-09-24: tests never depend on host state). Shape: the test sets sys.set_int_max_str_digits(4300) and restores the previous value in a finally/fixture for that case, and asserts the limit is what it set. Test-only.`

LEG 2 final dispositions (leg stage-1-exec-a4, `/fix`): PR-MED-010 Fixed; PR-MED-011 Fixed; PR-MED-012 Fixed; PR-LOW-013 Fixed — details on each finding's `/fix decision` line. One sibling outside the four, logged not silent: the `cliniko_client.py` module docstring still said the call makes "one Credential Manager read" — the same overclaim round 7 LOW-003 fixed in the retention row; reworded in this leg to "calls `read_key` ONCE (from the clinic-key phase that source is Credential Manager …)" (docs-only, a pattern sibling of an already-applied finding).

Cap verdict: accept — production-behavioral — 3 of the 4 findings are real behavioural defects with bounded fixes in Task 1.1/1.3 scope (read1 per receive, no body read on non-200, fixed-text argv refusal) and the 4th is test-only; peer_round 1 of cap 5, so no raise is needed and nothing is deferred.

### Round 9 - 2026-09-27 - Phase 1 Task 1.2 docs slice, independent cross-family codex peer review (pass stage-1.p1 slice B)

- Round status: Closed (0 pending) — PR-MED-030 fixed (docs-only) in leg stage-1-exec-a6 (2026-09-27)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Pinned Task 1.2 documentation changes, client and offline-guard structure, specified plan contracts, rounds 7–8, and permitted sibling search; static inspection only.
- **PR-MED-030** (MED, docs-only, `docs/security/retention-schedule.md:47`): The key-retention guarantee omits live references retained by exception tracebacks. A failed request can retain the Authorization header after the logical call closes; an invalid key can remain directly referenced by the validation traceback. Fixed exception text and removal of chained context do not clear these frames. — Evidence: the row promises “Reference dropped at the end of the call”; `docs/security/threat-model.md:1341` says “no reference kept here”. However, `desktop/src/scribe_desktop/cliniko_client.py:421` validates before `del api_key` at line 423, and `_get` keeps `"Authorization": self._authorization` in local `headers` at lines 474–480. `close()` at line 447 clears only `self._authorization`; propagated exceptions retain the failing frames. Recommendation: Fix-now — Document traceback-held references as an additional memory-lifetime residue and scope the exception guarantee to rendered text; reconcile retention row 47, threat-model lines 1327–1343, flow 18’s exception wording at line 499, and the client docstring at lines 50–56. /fix decision: Fixed (docs-only, leg stage-1-exec-a6, 2026-09-27) — sibling grep `(?i)in an exception|in any exception|no exception|no reference|reference dropped|drops its only reference|keeps no copy|never holds it|holds no key|dropped when the call ends|drops its reference|refuses further use|no chained context|carries nothing` over `docs/**`, `desktop/src/**`, `CHANGELOG.md`, `AGENTS.md`, `PLAN.md`, `scripts/`. REWORDED: `retention-schedule.md:47` (the text is "never in any exception's rendered text"; the destruction column names the live-exception frame residue); `threat-model.md` SECRETS (scoped to what an exception RENDERS; the object → RESIDUE (6)), RESIDUE (2) ("the module's own references go"; (6) lengthens it) and a NEW RESIDUE (6) (the traceback frames hold the key / Basic token, path, ids, response bytes while the exception lives; `from None` removes context, not frames; `traceback.clear_frames` rejected and why); `data-flow-map.md:65-68` (flow 3: "at rest ONLY here"; the client's own references go at the call's end, a live exception aside) and `:499-506` (flow 18: rendered text; the frame residue); `cliniko_client.py:41-51` and `:59-62` (module docstring: rendered vs object, "this module's own references"). LEFT (true as scoped): `cliniko_client.py:283` / `:512` "no chained context" (context, not frames), `:404` "Holds no key" (the client object), CHANGELOG line 8 ("with fixed text, raised without chained context" — text), and the non-Cliniko hits `enrolment.py:262`, `threat-model.md:501`, `transcription.py:1432`, `ui/note.py:1631` (normal-return or text claims in other subsystems, outside this finding). No code behaviour changed; ruff clean, mypy 40 files.
- Verification counts: 3 claims checked, 1 confirmed, 2 dropped as unverifiable
- Last reviewed: 2026-09-27

#### LEG 1 verified tuples (executor, leg stage-1-exec-a5)
Evidence (re-located on the a4 tree). Every named error carries `__traceback__`, and that traceback holds the frames it unwound through, locals included, for as long as the exception object lives. `raise … from None` (and `_guarded`'s raise after its `except`) removes the chained CONTEXT, not the frame chain. The frames hold:
- `ClinikoClient.call` (`cliniko_client.py:418-425`): `api_key` is a live local when `shard_of_key(api_key)` (`:421`) raises `InvalidKey` (and `shard_of_key`'s own frame, `:382-385`, holds it as a parameter), before `del api_key` (`:423`).
- `ClinikoCall._get` (`:472-481`): the local `headers` dict holds `"Authorization": "Basic <token>"`, and it is in the traceback of EVERY error raised through the transport or `_interpret`. `close()` (`:446-447`) clears only `self._authorization`, not that dict.
- The same frames hold the request path (`resource`), the id arguments and, in `_interpret`/`_parse_object`, the `RawResponse` and its body bytes.

So while a caller keeps the exception (bound beyond its `except`, stored on an object, `sys.last_exc`, a debugger), the key/token, ids and response bytes stay referenced past the logical call's end. The RENDERED guarantee still holds: `str`, `repr` and `traceback.format_exception` print source lines, never locals, and `TestNothingLeaks` pins that.
- PR-MED-030 (peer: MED, docs-only) → `materiality=docs-only severity=verified: low surface=docs rec=Fix-now (docs-only) — confirmed as a claim-outruns-structure overstatement, not a leak: "Reference dropped at the end of the call" (retention row), "drops its only reference on exit" / "no reference kept here" (threat-model SECRETS + RESIDUE (2)), "keeps no copy" (data-flow flow 3, :67), "never put in an exception" (flow 18, :499) and the module docstring (:50-56, "no exception … carries" / "no reference is kept here") all omit traceback-held frame references. Downgraded to LOW: this extends the memory lifetime of values the doc already calls un-zeroable (LOW-009), inside the same-user boundary, and no rendered channel (text, repr, formatted traceback, log record) carries them. Shape: scope every exception sentence to what the exception RENDERS; add a RESIDUE item (and the retention row's destruction column): while an exception raised during a call is alive, its traceback frames reference the key/Basic token, the path, ids and response bytes, until the exception is dropped; reword flow 3's "keeps no copy" and flow 18 to the same; the plan's D9 "No exception … carries" line reads as text and stays. REJECTED alternative (a code change): `traceback.clear_frames(exc.__traceback__)` in `ClinikoClient.call` would also wipe the CALLER's finished frames in that traceback (a debugging side effect on code outside the module) and still misses the `InvalidKey` raised before the `yield`. The docs-only change is the smaller truthful one.`

LEG 2 final disposition (leg stage-1-exec-a6, `/fix`): PR-MED-030 Fixed (docs-only, as a class) — sites and sibling grep on the finding's `/fix decision` line.

Cap verdict: accept — docs-only — one confirmed docs-only overstatement (traceback-held frame references), fixable as a class across the retention row, threat-model SECRETS/RESIDUE, flows 3 and 18 and the client docstring; peer_round 2 of cap 5, 2 of the peer's 3 claims already dropped as unverifiable, so the docs slice is converging.

### Round 10 - 2026-09-27 - Phase 1 round-8/9 fixes, independent cross-family codex peer review (scoped confirmation, pass stage-1.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Five round-8/9 fixes, their named tests, and the specified documentation changes; static inspection only, no writes, tests or network.
- Confirmed fixed: PR-MED-010 (`cliniko_client.py:369–374`: `in_time()` precedes `response.read1`, with `allowance - total`; lines 94–96 explicitly name the remaining per-step limits); PR-MED-011 (`scripts/probe-cliniko.py:254–260`: unexpected arguments receive fixed text and `return 2` before argparse; named tests check both output streams and help); PR-MED-012 (`cliniko_client.py:339`: body read only `if status == 200 else b""`, with `conn.close()` in `finally`; named tests preserve refusal classifications and the 429 reset); PR-LOW-013 (`test_cliniko_client.py:288–297`: pins `4300` and restores `previous` in `finally`); PR-MED-030 (`cliniko_client.py:42–50`: distinguishes what an exception “RENDERS” from its traceback-held locals; threat-model SECRETS/RESIDUE, retention row 47, and flows 3/18 consistently state that distinction).
- Verification counts: 5 claims checked, 5 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-27

### Round 11 - 2026-09-27 - Task 1.4 (copy-to-Cliniko flag flip and shipping-gate reframing), `/review-loop` round 1 of cap 3

- Round status: Closed (0 pending) — 1 MED (docs-only), Fix-now, applied in this leg
- Source: Claude Code (executor leg stage-1-exec-a7, claude-opus-5-5, sequential lenses in-session — no subagents)
- Scope / baseline: the Task 1.4 diff only — `ui/models.py:440-449` (flag + decision comment), the `ui/note.py` module docstring (`:121-126`), `desktop/tests/test_ui_screens.py` (`test_default_copy_binding_ships_enabled`), the `test_note_pipeline.py` module docstring, `docs/testing/shipping-gate.md` (status, intro, "What the gate decides", "What a decision flips"), `docs/design-system.md:221-231`, threat-model Phase 3A surface 4, data-flow flow 10, `PLAN.md`'s 3A delivery note, `AGENTS.md` (Phase 9 prep line, the active-plan line, the shipping-gate pointer), `CHANGELOG.md` (Changed), `plan-phase3a-note-pipeline.md` Task 9.1 (dated REFRAMED bullet). ruff clean, mypy 40 files on the pre-round tree.
- Lenses and results:
  - Correctness — the flag is read in two places only (`main_window.py:453` at call time; `note.py:512` as `begin_review`'s default at import) and both now yield `True`; `_copy_ready` / `_apply_copy_binding` untouched, so an unratified note still gets a shown-but-disabled button and a `NoTextInteraction` body — the renamed pin asserts exactly that. The window-wiring tests monkeypatch the flag both ways and stay decision-agnostic; no other test builds a `NoteScreen` on the default binding and asserts the old hidden state (`copy_button` grep over `desktop/tests`). CLEAN.
  - Plan adherence (D12, Task 1.4 Files) — every listed file touched; `PLAN.md` and `test_note_pipeline.py` added by the gate's own grep; `_copy_ready` untouched. CLEAN.
  - Docs as control claims (lessons 2026-08-14, 2026-09-20) — found MED-005: enabling copy creates a NEW route for ratified clinical text out of the app (the Windows clipboard), and no doc named its custody or the clipboard-history / cloud-sync residue. The docs still said, or implied, that no clinical text reaches the clipboard (threat-model surface 4 of the foundation and 3A surface 3 are transcript-scoped and stay true).
  - Executor judgment / structural quality — none.
  - Missed-issue pass: re-grep of `copy-to-cliniko|copyable|ships DISABLED` over `PLAN.md`, `docs/**`, `desktop/src/**`; `intended-use.md` re-read in full; result: MED-005's `intended-use.md` site (the threat-model sentence first pointed to it for an operating rule it did not state).
- Findings:
  - **[MED]** MED-005: `docs/security/threat-model.md` (Phase 3A surface 4), `docs/security/data-flow-map.md` (flow 10), `docs/security/retention-schedule.md`, `docs/security/intended-use.md` — with copy now ENABLED, a copied ratified note sits on the Windows clipboard, outside the app's custody. It is readable by same-user processes, kept past the next copy by clipboard history, and sent to the user's Microsoft account by cloud clipboard sync, and none of the four docs said so (a new outbound route for clinical text under a "not a cloud service" statement) — materiality=docs-only surface=docs — Triage: Fix-now; Decision: Applied — surface 4 gains a "Residue once copied" paragraph (the app neither clears the clipboard nor detects history/sync; cloud sync off is an operating rule, not a control) and its over-long line reflowed; flow 10 names the clipboard as outside the app's custody; a new retention row "A copied note on the Windows clipboard" (OS custody; history clears unpinned items at restart; destruction: none by the app); `intended-use.md`'s current scope note says how a note reaches Cliniko until Phase 4 and to keep cloud clipboard sync off; CHANGELOG's Task 1.4 entry names it. A code control (clearing the clipboard after a delay, or refusing copy while cloud sync is on) is NOT built — a behaviour change beyond D12, recorded as an executor recommendation in the handoff.
- Verification counts: 5 lenses run, 1 candidate, 0 dropped, 0 downgraded
- Last reviewed: 2026-09-27

### Round 12 - 2026-09-27 - Task 1.4 round-11 fix, `/review-loop` round 2 of cap 3 (post-fix regression check)

- Round status: Closed (0 pending) — 0 findings; converged
- Source: Claude Code (executor leg stage-1-exec-a7, claude-opus-5-5, in-session)
- Scope / baseline: MED-005's five edited passages plus the whole Task 1.4 diff re-read against round 11.
- Post-fix regression check: MED-005 confirmed fixed. Surface 4 states custody, the same-user read, history and sync, and "operating rule, not a control"; flow 10 and the retention row agree with it; the retention row is 4 columns with no stray pipe; the intended-use sentence it points to exists. No new overclaim: clipboard history is stated as cleared for unpinned items at restart, not "kept until cleared"; "sent to the user's Microsoft account" is scoped to "when cloud sync is on".
- Round classification: 🆕 0 / 🔁 0 — converged (no CRIT/HIGH/MED).
- Verification counts: 1 fix checked, 1 confirmed, 0 regressions
- ruff clean; mypy 40 files; pytest owed to the composer (expected 2973 passed — one test renamed, none added or removed)
- Last reviewed: 2026-09-27

### Round 13 - 2026-09-27 - Task 1.4 copy-flag flip, independent cross-family codex peer review (pass stage-1.p2)

- Round status: Closed (0 pending) — both fixed (docs-only) in leg stage-1-exec-a9 (2026-09-27); pytest owed to the composer
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Task 1.4’s specified code, tests, plan excerpts and documentation; static inspection only, no writes, tests or network. No unratified-copy bypass verified; both flag outcomes remain covered.
- **PR-LOW-050** (LOW, docs-only, `desktop/tests/test_ui_screens.py:3510`): Test docstrings still describe Task 9.1 as the copy-enablement authority, contradicting D12; the prescribed grep misses these sentences. — Evidence: “the 9.1 gate is necessary but NOT sufficient”; line 3557 also says “whatever Task 9.1 records”. The already-noted siblings in `desktop/src/scribe_desktop/ui/note.py:2006` and `:2014` say “Task 9.1 flips the flag” and “per the 9.1 shipping flag”. Recommendation: Fix-now — Reword this class of comments/docstrings around the independently recorded copy decision and broaden the reconciliation search to catch these variants; preserve runtime predicates and both-outcome assertions. /fix decision: Fixed (docs-only, as a class; leg stage-1-exec-a9, 2026-09-27). Each site now names the recorded copy flag or the practitioner's D12 decision, and the old 9.1 PASS/FAIL framing is kept as history where tests carry it:
  - `ui/note.py:1999-2006` (`_copy_ready` docstring: "the recorded copy flag … on since the practitioner's 2026-09-27 decision, D12 … when the flag is on").
  - `ui/note.py:2015` (`_apply_copy_binding`: "per the recorded copy flag").
  - `ui/models.py:524-525` (`format_note_body`: "gated on the recorded copy flag and full ratification — `_copy_ready`"; the sibling the peer did not name).
  - `test_ui_screens.py:3510-3513` and `:3517` ("flag", not "gate").
  - `:3558-3560` ("whatever copy decision is recorded (the practitioner's, D12 since 2026-09-27)").
  - `:5942-5944`, `:5975-5976`, `:6056` and `:6078`: the four both-outcome docstrings, where "the FAIL/PASS outcome" is now the flag-OFF/ON outcome; the test NAMES are kept.
  - `:5992` ("Flag on").
  - No predicate, assertion or test name changed.
  - Widened grep: `(?i)9\.1[a-z]? (gate|flag|shipping|decision|records)|whatever Task 9\.1|gate (is )?on\b|(Task )?9\.1 flips|shipping (flag|decision)` over `desktop/src/** desktop/tests/** docs/** PLAN.md AGENTS.md`. Zero hits remain in `desktop/`. What is left in the docs is correct as written: `AGENTS.md:57` (the 9.1 RUN stays paused), `:86` (the pointer, already reframed), `PLAN.md:110` (already reframed), `phase-history.md:11,25` (history), `shipping-gate-config/README.md:3,14` (the run's config), and `cross-agent-orchestration.md:266` (unrelated).
- **PR-LOW-051** (LOW, docs-only, `docs/security/data-flow-map.md:224`): Flow 10 retains an unconditional plaintext-lifetime/storage claim immediately before its new clipboard exception, leaving the control description internally inconsistent. — Evidence: “Plaintext note and the full transcript coexist in memory only for the review window”; “the note is never logged and never written outside the encrypted store”. Lines 228–230 then state that copied text goes to the Windows clipboard outside app custody, including history and cloud sync; `desktop/src/scribe_desktop/ui/note.py:1995` performs `clipboard.setText(models.format_note_body(note))`. Recommendation: Fix-now — Scope the memory and encrypted-storage claims to app-managed review/session data and explicitly exempt the clinician-initiated clipboard export and its retained copies. /fix decision: Fixed (docs-only; leg stage-1-exec-a9, 2026-09-27).
  - `data-flow-map.md:224-229`: flow 10 now reads "Inside the app, … coexist in memory only for the review window …, and the app never logs the note and never writes it outside the encrypted store — with ONE exception the app does not hold: the clinician-initiated Copy below, whose clipboard copy (and any clipboard-history or cloud-sync copy of it) outlives the review".
  - Sibling `threat-model.md` 3A surface 3 (`:361-364`): "No new on-disk plaintext and no new logging channel are introduced" is now "The app introduces no new on-disk plaintext and no new logging channel (the one route out of its custody is the clinician's Copy of a ratified note, whose clipboard residue surface 4 names)".
  - Checked and LEFT as true when read as written:
    - Retention row 34 (in-memory plaintext) is scoped to process memory; the clipboard has its own row, added in round 11.
    - `design-system.md:217,223` "never leaves the app" / "never written outside the encrypted store" refer to the TRANSCRIPT, which is never copyable.
    - The sibling grep `(?i)outside the encrypted store|never leaves the (app|machine)` over `docs/** desktop/src/** PLAN.md AGENTS.md` finds only those two lines and the rewritten flow 10.
- Verification counts: 2 claims checked, 2 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-27

#### LEG 1 verified tuples (executor, leg stage-1-exec-a8)
Evidence (a7 tree, re-read):
- The copy class still names Task 9.1 as the enablement authority in six places:
  - `test_ui_screens.py:3510-3512`: "the 9.1 gate is necessary but NOT sufficient … even with the gate on".
  - `:3516`: "Gate on, but proposals pending".
  - `:3557`: "whatever Task 9.1 records".
  - `:5988`: "Gate on: shown …".
  - `ui/note.py:2000-2006` (`_copy_ready`): "the 9.1 shipping flag … when the gate is on … even after Task 9.1 flips the flag".
  - `:2014` (`_apply_copy_binding`): "visible per the 9.1 shipping flag".
  - `ui/models.py:524` (`format_note_body`): "gated on the 9.1 shipping decision".
- None of these matches the gate page's grep (`COPY_TO_CLINIKO_ENABLED|ships DISABLED|shipping gate`), which is why Task 1.4 missed them. `models.py:524` is a sibling the peer did not name.
- Flow 10 (`data-flow-map.md:224-226`) says, unscoped, "coexist in memory only for the review window" and "never written outside the encrypted store". It then states the clipboard export at `:226-231`, and `ui/note.py:1995` `clipboard.setText(models.format_note_body(note))` is exactly that export.

Tuples:
- PR-LOW-050 (peer: LOW, docs-only) → `materiality=docs-only severity=verified: low surface=docs rec=Fix-now (docs-only, as a class) — confirmed: the stale "9.1 gate/flag" wording sits in test docstrings/comments (test_ui_screens.py:3510-3512, :3516, :3557, :5988) and production docstrings/comments (ui/note.py:2000-2006, :2014; plus the unnamed sibling ui/models.py:524). It is comment/docstring text only: runtime predicates and both-outcome assertions are untouched. Shape: reword each to "the recorded copy flag (COPY_TO_CLINIKO_ENABLED; practitioner decision 2026-09-27, D12)". D12's "_copy_ready untouched" is about the predicate, and its docstring may change. Broaden the reconciliation search with the variant grep (?i)9\.1 (gate|flag|shipping)|whatever Task 9\.1|gate (is )?on over desktop/src desktop/tests, and record the grep in Task 1.4's note.`
- PR-LOW-051 (peer: LOW, docs-only) → `materiality=docs-only severity=verified: low surface=docs rec=Fix-now (docs-only) — confirmed: flow 10's "coexist in memory only for the review window" and "never written outside the encrypted store" are unscoped and sit directly before the clipboard export the same paragraph states (ui/note.py:1995 setText). Shape: scope both to what the app itself holds or writes — app-managed memory and storage — "except the clinician-initiated Copy, whose clipboard copy (and any history/cloud-sync copies) is outside the app's custody". Sibling check at fix time covers threat-model 3A §3 and the retention in-memory-plaintext row (row 34) for the same unscoped claim.`

LEG 2 final dispositions (leg stage-1-exec-a9, `/fix`): PR-LOW-050 Fixed (docs-only, as a class, including the `ui/models.py:524` sibling); PR-LOW-051 Fixed (docs-only, plus the threat-model 3A surface 3 sibling). The sites and the widened greps are on each finding's `/fix decision` line. ruff clean; mypy 40 files; pytest owed to the composer (expected 2973: docstrings and comments only).

Cap verdict: accept — docs-only — both findings are confirmed comment/docstring and doc-scope inconsistencies with no runtime effect. The peer verified no unratified-copy bypass. This is peer_round 1 of cap 5, so no raise is needed.

### Round 14 - 2026-09-27 - Task 1.4 round-13 fixes, independent cross-family codex peer review (scoped confirmation, pass stage-1.p2)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Round-13 fixes and regression inspection within the specified files and hunks; static inspection only, no writes, tests or network.
- Confirmed fixed: PR-LOW-050 and PR-LOW-051 within the prescribed scope. PR-LOW-050: `desktop/src/scribe_desktop/ui/note.py:2000` now says “the recorded copy flag”; `desktop/src/scribe_desktop/ui/models.py:524` says “gated on the recorded copy flag and full ratification”. The specified test rewordings change only comments/docstrings; the HEAD diff’s shipped-default test rename and assertions belong to Task 1.4’s original flag flip. PR-LOW-051: `docs/security/data-flow-map.md:224` scopes memory to “Inside the app”, explicitly excepting “the clinician-initiated Copy” at line 227 and clipboard-history/cloud-sync copies at line 228. `docs/security/threat-model.md:363` agrees: “the clinician’s Copy of a ratified note”, with the residue described in surface 4.
- No new findings: The fixes introduce no runtime changes or verified D12 contradiction. `desktop/src/scribe_desktop/ui/note.py:1991` retains the click-time `_copy_ready()` check; line 2020 applies the same predicate to copy binding. Both documents consistently place clipboard residue outside app custody and retain the display-only transcript contract.
- Verification counts: 2 claims checked, 2 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-27

### Round 15 - 2026-09-27 - Phase 2 (Tasks 2.1a, 2.1b, 2.2: clinic registry, key validation and storage, Clinics tab), `/review-loop` round 1 of cap 3

- Round status: Closed (0 pending) — 1 MED + 4 LOW, all Fix-now, all applied in this leg; pytest owed to the composer
- Source: Claude Code (executor leg stage-2-exec-b3, claude-opus-5-5, sequential lenses in-session — no subagents)
- Scope / baseline: the whole Phase 2 working-tree diff over `32e7289` — `clinics.py`, `ui/clinics.py`, `test_clinics.py`, `test_ui_clinics.py` (new, read in full), `ui/models.py` (the Clinics copy), `ui/main_window.py`, `cliniko_client.py` (docstring), `test_cliniko_client.py` / `test_ui_screens.py` / `test_status_and_app.py` / `test_integration_no_sockets.py` (the changed hunks), the threat model's "Cliniko API client" section, data-flow intro + flows 3 and 18, the retention rows, `intended-use.md`, `incident-process.md`, `design-system.md`, `AGENTS.md` step 8, `CHANGELOG.md`. Composer suite on the pre-round (b2) tree: 3128 passed.
- Lenses and results:
  - Key custody (never displayed, logged or in exception text; the masked field cleared incl. undo; the in-memory lifetime) — found MED-006 (the worker closure kept the request, so the typed key, alive for the tab's lifetime) and LOW-008 (a pasted key's surrounding whitespace was refused as "not a key"). Otherwise clean: the key reaches only the request (repr-excluded), the client call and the key store; no `Refused`, `ValidatedAccount`, status line or list row carries it; a worker failure shows fixed copy.
  - `clinic_rev` stale-result rule — CLEAN: a Replace bumps at dispatch and commit, Remove bumps first, every commit compares the captured rev on the GUI thread, a removed clinic's delayed result is SUPERSEDED/CLINIC_GONE and writes nothing, `confirm_subdomain_from_note` checks rev + host + existence; ids are never re-minted. Found LOW-007 (a Replace refused for a typed address was named "different account").
  - Remove-while-live-session refusal — CLEAN at the registry (refused before any bump or delete) and the tab (the provider read at the confirming click); `MainWindow._live_session_clinic()` returns None by design until Phase 3 (recorded on Task 2.2 and in the handoff).
  - Fail-closed registry load/save — CLEAN for load (missing → empty; unreadable/oversize/invalid/inconsistent → empty + every mutation refused; the file never overwritten). Found LOW-010 (a key store that wrote before raising was then un-listed, leaving a key at rest the registry did not list — against the module's and threat model's write-order claim).
  - Nothing at startup or idle — CLEAN: construction reads `clinics.json` only; `SecureStorageProvider` is constructed, not called; the transport is built per call; the idle integration child now builds the tab with the real transport.
  - Docs as control claims — found LOW-009 (flow 18 said "on a refusal, nothing" while a failed store / write can leave the named partial states); the CLINIC KEYS paragraph's lifetime sentence was false until MED-006's fix and is true after it.
  - Missed-issue pass: the repo's own precedent for MED-006 (`ui/note.py:1633-1646`, the prose job's holder, round 20 MED-001) found by grepping every `TaskThread(` site.
- Findings:
  - **[MED]** MED-006: `desktop/src/scribe_desktop/ui/clinics.py` `_dispatch` — `TaskThread(lambda: registry.run_validation(request), self)`: the thread object is a child of the tab, so its closure kept the `ValidationRequest` — and the typed key in it — referenced for the tab's (the app's) lifetime after every Validate / Replace key, while the threat model's CLINIC KEYS and the in-use-key retention row say it lives "until the result is committed" — materiality=behavioral surface=production — Triage: Fix-now; Decision: Applied — the holder pattern (`holder = [request]`; `lambda: registry.run_validation(holder.pop())`), with a comment citing the precedent; the only other reference, `_pending`, is dropped at commit. Test: `test_ui_clinics.py::TestValidate::test_a_finished_check_leaves_no_reference_to_the_request` (a `gc.get_referents` walk from every finished check thread's function finds no `ValidationRequest`). Sibling note: the other `TaskThread(…, self)` sites (`microphone.py:355`, `recovery.py:237`, `session_screen.py:251`, `transcript.py:643`, `practitioner.py:1097`) carry no key; any plaintext they retain is outside Phase 2's scope — recorded as an executor recommendation in the handoff, not changed.
  - **[LOW]** LOW-007: `clinics.py` `begin_validation` — a Replace whose TYPED ADDRESS was not the clinic's was refused as `DIFFERENT_ACCOUNT` ("This key is for a different Cliniko account"), naming the key when the address was the mismatch — Triage: Fix-now; Decision: Applied — split: a key-shard mismatch stays `DIFFERENT_ACCOUNT`; a typed-address mismatch is `ADDRESS_MISMATCH`, whose copy now reads "The web address you typed does not match this key's clinic - check you pasted the right clinic's key, or clear the web address field." (true for both the add and the Replace case). Test updated (`TestReplaceKey::test_a_typed_address_for_another_clinic_is_refused`, plus the rev unchanged).
  - **[LOW]** LOW-008: `ui/clinics.py` `_take_key` — a key pasted with a trailing space or tab was refused as `KEY_FORMAT` ("That is not a Cliniko API key") — Triage: Fix-now; Decision: Applied — the tab strips surrounding whitespace before `begin_validation` (the registry stays strict: `KEY + "\r\n"` is still refused there). Test: `TestValidate::test_surrounding_whitespace_on_a_pasted_key_is_dropped`.
  - **[LOW]** LOW-009: `docs/security/data-flow-map.md` flow 18 CALLERS — "on a refusal, nothing" overstated: a failed Credential Manager store or file write can leave the partial states the threat model names — materiality=docs-only — Triage: Fix-now; Decision: Applied — "on a refusal by Cliniko or a local check, nothing", plus a sentence naming the two partial states and pointing at CLINIC KEYS.
  - **[LOW]** LOW-010: `clinics.py` `_commit_new` — when the key store raised AFTER writing, the rollback rewrote the file without the clinic, leaving a key at rest the registry did not list (the exact state the ORDER OF WRITES claim excludes) — Triage: Fix-now; Decision: Applied — on a store failure the registry first deletes whatever the store may have written, then rewrites the file; if either step fails the clinic stays listed (in memory and on disk) so Remove clears it. Module docstring and threat-model CLINIC KEYS (write order + residue) reworded to match. Tests: `TestWriteOrder::test_a_store_that_wrote_before_failing_leaves_no_unlisted_key`, `::test_a_failed_cleanup_keeps_the_clinic_listed_for_remove`.
- Verification counts: 6 lenses run, 5 candidates, 0 dropped, 0 downgraded
- ruff clean; mypy 42 files; pytest owed to the composer (expected 3128 + 4 = 3132 passed)
- Last reviewed: 2026-09-27

### Round 16 - 2026-09-27 - Phase 2 round-15 fixes, `/review-loop` round 2 of cap 3 (post-fix regression check)

- Round status: Closed (0 pending) — 5/5 round-15 fixes confirmed; 1 new LOW, Fix-now, applied in this leg; pytest owed to the composer
- Source: Claude Code (executor leg stage-2-exec-b4, claude-opus-5-5, sequential lenses in-session — no subagents)
- Scope / baseline: the round-15 fix sites, then a missed-issue pass over the whole Phase 2 working-tree diff over `32e7289` (`clinics.py` and `ui/clinics.py` re-read in full; the Clinics copy in `ui/models.py`; the `main_window.py` and `cliniko_client.py` hunks; the round-15 tests; threat-model CLINIC KEYS; flow 18; the retention rows for the in-use key, the keys at rest and the registry). Composer suite on the pre-round (b3) tree: 3132 passed.
- Lenses and results:
  - Post-fix verification — MED-006 CONFIRMED (`_dispatch` hands the request through `holder.pop()`; the closure keeps only `holder` and `registry`; the test's `gc.get_referents` walk would reach the request through the old closure cell, so it is non-vacuous; `_pending` is the only other reference and is dropped in `_finish_task`). LOW-007 CONFIRMED (a key-shard mismatch is `DIFFERENT_ACCOUNT`, a typed-address mismatch `ADDRESS_MISMATCH`, both before the bump — the test pins the rev unchanged; the copy is true for add and Replace). LOW-008 CONFIRMED (`_take_key` strips; the registry stays strict). LOW-009 CONFIRMED (flow 18 CALLERS scoped to "a refusal by Cliniko or a local check" and names the partial states). LOW-010 CONFIRMED (`_commit_new` deletes, then rewrites, restoring `_records` only when both succeed; the module docstring, threat-model CLINIC KEYS write order and residue, and the keys-at-rest retention row's "never a key with no listing" all match; both tests exercise the two branches).
  - Missed-issue pass (claim-outruns-structure siblings) — found LOW-011. Otherwise clean: the copy's `.format` substitutes practitioner-typed names as values only; a Remove during a pending Replace supersedes it; a KEY_STORE_FAILED new clinic left listed is named by its copy ("If a new clinic still shows in the list, Remove it"); the close guard covers an in-flight check.
- Findings:
  - **[LOW]** LOW-011: `clinics.py` `commit_validation` — the module docstring (CLINIC_REV: "a delayed result for a removed clinic is `CLINIC_GONE`") and the `CLINIC_GONE` copy ("That clinic is no longer set up") were unreachable at commit: Remove always bumps the rev, and the rev was compared first, so a Replace result landing after Remove was always `SUPERSEDED` ("The clinic changed while its key was being checked"); `test_clinics.py` accepted either reason, so nothing pinned the claim — materiality=behavioral (status wording only; both refuse whole and write nothing) surface=production — Triage: Fix-now; Decision: Applied — a Replace whose clinic is gone is refused `CLINIC_GONE` before the rev check (a new clinic's request is unaffected). Tests tightened: `TestClinicRev` (the Remove case now asserts `CLINIC_GONE` exactly) and `test_ui_clinics.py::TestDelayedResults::test_a_replace_result_landing_after_remove_restores_nothing` (the status line is the `CLINIC_GONE` copy).
- Verification counts: 2 lenses run (6 checks), 1 candidate, 0 dropped, 0 downgraded
- ruff clean; mypy 42 files; pytest owed to the composer (expected 3132 passed — no test added, two tightened)
- Last reviewed: 2026-09-27

### Round 17 - 2026-09-27 - Phase 2 clinic keys (code), independent cross-family codex peer review (pass stage-2.p1 slice A)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase 2 Tasks 2.1a, 2.1b and 2.2; specified code, diffs and tests, checked by reading only. No files written, tests run or network commands executed.
- **PR-LOW-070** (LOW, behavioral, `desktop/src/scribe_desktop/clinics.py:669`): Delayed validation refusals bypass the removal and revision guards. Start Replace key, remove that clinic while the request is pending, then receive a refusal: the obsolete error replaces the removal status instead of returning `CLINIC_GONE`. A superseded refusal similarly bypasses `SUPERSEDED`. No key or registry entry is restored, but stale display data violates D9. — Evidence: “`if isinstance(result, Refused):`” / “`return result`” precedes the guards at lines 677–680; `desktop/src/scribe_desktop/ui/clinics.py:290` forwards that outcome through “`self._refuse(outcome, operation)`”. Recommendation: Fix-now — Check clinic existence and revision before returning worker refusals; extend delayed-result tests to cover failed results after Remove and Replace. /fix decision: Fixed — `clinics.py` `commit_validation` (:665-687): the worker-refusal early return moved below the gone check, the rev check and the new-clinic stale-id check (and above the too-many and duplicate checks), so a stale refusal is `CLINIC_GONE` / `SUPERSEDED` and a current one returns unchanged; method and module docstrings state the order. /fix notes: tests `test_clinics.py::TestClinicRev::test_a_delayed_refusal_after_remove_is_named_gone`, `::test_a_delayed_refusal_after_a_later_replace_is_superseded` (both fail on the old order: it returned `KEY_REJECTED`), `::test_a_current_refusal_is_returned_unchanged`, and `test_ui_clinics.py::TestDelayedResults::test_a_refused_replace_landing_after_remove_is_named_gone` (a 401 held in flight on a `GatedTransport`, then Remove: the status line is the `CLINIC_GONE` copy); ruff clean, mypy 42 files, pytest owed to the composer; sibling sites none (the only worker-result commit point). /fix date: 2026-09-27. /fix applied by: Claude Code
- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-27

#### LEG 1 verified tuples (executor, leg stage-2-exec-b5)

- PR-LOW-070 (peer: LOW, behavioral) — `materiality=behavioral severity=verified: low surface=production rec=Fix-now — confirmed: clinics.py:669-670 returns a worker Refused before the gone check (:677-678) and the rev check (:679-680); ui/clinics.py:288-291 shows it via _refuse, so a Replace in flight, then Remove, then a Cliniko refusal (e.g. KEY_REJECTED) replaces "<name> removed…" with the stale refusal's copy ("Cliniko refused this key…"); nothing is written or restored (the refusal path touches no state), so wording only.` Reach in the shipped tab: only Remove can supersede a pending check (Replace key and Validate are disabled while busy), so the reachable case is Remove during a Replace; the SUPERSEDED branch is reachable through the registry API (a second `begin_validation`), which Phase 3 callers will share. Same class as round 16 LOW-011 (the guard order decides the named reason), which fixed the success path but not the refusal path.
  - Fix shape: in `commit_validation`, move the `isinstance(result, Refused)` early return BELOW the gone check and the rev check (the load-problem check order is immaterial, since it is set only at construction). A current worker refusal then returns unchanged; a stale one becomes `CLINIC_GONE` (a Replace whose clinic is gone) or `SUPERSEDED` (a moved rev, or a new-clinic id now listed). The module docstring's CLINIC_REV paragraph already states this rule ("a Validate or Replace whose rev moved is dropped whole").
  - Tests: `test_clinics.py::TestClinicRev` — a Replace refused by Cliniko committed after Remove is `CLINIC_GONE`; after a second Replace dispatch it is `SUPERSEDED`; a current refusal still returns unchanged (the existing refusal tests pin that). `test_ui_clinics.py::TestDelayedResults` — Replace blocked in flight on a `GatedTransport` answering 401, Remove confirmed, gate released: the status line is the `CLINIC_GONE` copy, the list is empty and the store holds no key.
  - Decision (leg stage-2-exec-b6, `/fix`): Fixed as the shape above, placing the refusal return also below the new-clinic stale-id check; the three registry tests and the tab test landed as named (see the finding's `/fix decision`).

Fix-delta self-check: PASS — re-read the one applied hunk in `commit_validation` (a current refusal on either path still returns unchanged; the too-many and duplicate checks now see only a `ValidatedAccount`, so mypy narrows `result.host`; the load-problem check sits first but cannot fire after a successful dispatch) and the two docstrings.

Cap verdict: accept — production-behavioral — pass stage-2.p1 is at peer_round 1 of cap 5, and a one-guard reorder with three tests fits the remaining rounds; no cap change needed.

### Round 18 - 2026-09-27 - Phase 2 clinic keys (docs + round-17 confirmation), independent cross-family codex peer review (pass stage-2.p1 slice B)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase 2 documentation diffs, D10 and P.1 context, and PR-LOW-070 confirmation; verified by reading only. No writes, tests or network commands.
- Confirmed fixed: PR-LOW-070 — `desktop/src/scribe_desktop/clinics.py:680–687` checks clinic removal and revision before “`if isinstance(result, Refused): return result`”. The module and method docstrings describe that precedence. `desktop/tests/test_clinics.py:794–837` pins delayed refusal after Remove as `CLINIC_GONE`, after another Replace as `SUPERSEDED`, and a current refusal as unchanged. `desktop/tests/test_ui_clinics.py:444–471` pins the delayed 401’s displayed `CLINIC_GONE` outcome and empty registry/key store.
- **PR-LOW-080** (LOW, docs-only, `docs/security/retention-schedule.md:48`): The added retention wording incorrectly ties Qt’s residual key buffer lifetime to validation completion. Dropping the Python request does not clear Qt’s residual allocation; the threat model correctly gives that residue a separate lifetime. — Evidence: the row says “held in the dispatched request, and in the field's own buffer … until the result is committed and the request dropped”; `desktop/src/scribe_desktop/ui/clinics.py:199–200` performs “`key = self.key_field.text().strip()`” and “`self.key_field.setText("")`”, while `:288–289` commits and executes “`del request`” without any Qt-buffer scrubbing. Recommendation: Fix-now — Separate the request’s reference lifetime from Qt’s un-zeroed buffer residue, which may persist until Qt reuses its storage. /fix decision: Fixed — `docs/security/retention-schedule.md:48` (the in-use-key row) and its class sibling `docs/security/threat-model.md:1389-1395` (CLINIC KEYS residue) now state two lifetimes separately: the Python `str` in the dispatched request until the result is committed and the request dropped (the closure keeps none, MED-006), and the line edit's storage, released by `setText("")` but never zeroed, until Qt or the allocator reuses it, whatever the commit does. /fix notes: docs only; no other doc states the typed key's lifetime (LEG 1 grep). /fix date: 2026-09-27. /fix applied by: Claude Code
- **PR-LOW-081** (LOW, docs-only, `docs/security/retention-schedule.md:47`): The API-response retention row still denies an app caller and postpones the caller-specific retention description, contradicting the now-built validation flow documented alongside it. — Evidence: “no app caller yet” and “The callers … arrive in the plan's Phases 2–3 … and extend this row”; `desktop/src/scribe_desktop/clinics.py:625–638` now calls “`call.get_user()`”, “`call.get_practitioners_for_user(user_id)`” and “`call.get_public_settings()`”, and `:659–664` returns the selected identity and host fields for persistence. Recommendation: Fix-now — Update the response row to distinguish the built validation caller’s transient answers and retained registry fields from Phase 3’s future note-verification caller. /fix decision: Fixed — `docs/security/retention-schedule.md:47`: the heading names the first caller BUILT at Tasks 2.1b/2.2 (not "no app caller yet"); the lifetime cell names it — the three answers live inside the worker's one `_validate` call and are dropped when it returns, only the user id, practitioner id and subdomain go on to `clinics.json` on commit, the role and the rest never kept — and keeps Phase 3's note verification as the next caller (D3). /fix notes: docs only, modelled on flow 18's CALLERS paragraph, which already said this. /fix date: 2026-09-27. /fix applied by: Claude Code
- Verification counts: 3 claims checked, 3 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-27

#### LEG 1 verified tuples (executor, leg stage-2-exec-b7)

- PR-LOW-080 (peer: LOW, docs-only) — `materiality=docs-only severity=verified: low surface=docs rec=Fix-now — confirmed: retention-schedule.md:48 says the typed key is "held in the dispatched request, and in the field's own buffer after setText("") clears it, until the result is committed and the request dropped", but ui/clinics.py:199-200 only reads and setText("")s the field and :288-289 drops the Python request; nothing reaches Qt's QString storage, so that residue lasts until Qt/the allocator reuses it, independent of the commit.` Sibling (same class, missed by the peer): `threat-model.md:1389-1391` CLINIC KEYS residue — "the typed key is a Python `str` held in the dispatched request (and in the field's own buffer until Qt reuses it) until the result is committed" — gives the Qt buffer its own lifetime in the parenthesis but grammatically ties both to "until the result is committed". No other doc states the typed key's lifetime (flow 18 does not; the `clinics.py` residue paragraph names only the request; the `ui/clinics.py` docstrings claim only "cleared with setText").
  - Fix shape (as a class): in both the in-use-key retention row and the threat-model CLINIC KEYS residue, state two lifetimes separately — (i) the Python `str` in the dispatched `ValidationRequest` (and the tab's `_pending`) until the result is committed and the request dropped (the MED-006 holder leaves no other reference), and (ii) the Qt line edit's own storage, which `setText("")` releases but never zeroes, so the bytes may persist until Qt or the allocator reuses them — both never zeroed (the LOW-009 / residue (2) posture). Docs only; no test.
  - Decision (leg stage-2-exec-b8, `/fix`): Fixed as the shape above at both sites (retention row :48, threat-model CLINIC KEYS :1389-1395).
- PR-LOW-081 (peer: LOW, docs-only) — `materiality=docs-only severity=verified: low surface=docs rec=Fix-now — confirmed: retention-schedule.md:47's heading says "no app caller yet" and its body says "The callers ... arrive in the plan's Phases 2–3 ... and extend this row", while clinics.py _validate (:622-640) is a built caller of /user, /practitioners and /settings/public, and :659-664 returns the ids and host that commit_validation persists to clinics.json (row 50).` Flow 18's CALLERS paragraph (`data-flow-map.md:517-533`) already states the built caller correctly ("The role, the practitioner list and the rest of each answer are dropped with the call"; "Note verification (Phase 3) adds the next caller"), so it is the model, not a sibling to fix. No other doc says "no caller yet" (grep over `docs/`, `desktop/src/`, `AGENTS.md`).
  - Fix shape: re-title the row to "client BUILT at Task 1.1; first caller BUILT at Tasks 2.1b/2.2"; in its lifetime cell, name the built caller: a Validate / Replace key's three answers live inside the worker's one `_validate` call and are dropped when it returns; only the user id, the practitioner id and the subdomain (a `ValidatedAccount`) go on, to be persisted in `clinics.json` (row 50) on commit, and the role and the rest of each answer are never kept. Keep Phase 3's note verification as the next caller that extends the row (display strings never persisted, D3). Docs only; no test.
  - Decision (leg stage-2-exec-b8, `/fix`): Fixed as the shape above (retention row :47).

Fix-delta self-check: PASS — re-read the three applied hunks (retention rows 47 and 48, threat-model CLINIC KEYS residue) against `ui/clinics.py` `_take_key` / `_dispatch` / `_on_checked` and `clinics.py` `run_validation` / `_validate`: each lifetime stated matches the code (the worker's exception, if any, is dropped inside `run_validation`, so no answer outlives `_validate` there); no drive-by edit.

Cap verdict: accept — docs-only — pass stage-2.p1 is at peer_round 2 of cap 5; two docs rewordings (three sites, one retention row per finding plus the threat-model sibling) fit the remaining rounds, and a confirmation round follows.

### Round 19 - 2026-09-27 - Phase 2 round-18 fixes, independent cross-family codex peer review (scoped confirmation, pass stage-2.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Round-18 findings, verified tuples and fix decisions; specified retention rows, CLINIC KEYS section, flow 18 CALLERS paragraph, and validation code. Read-only verification; no writes, tests or network commands.
- Confirmed fixed: PR-LOW-080 — `docs/security/retention-schedule.md:48` separately states the request lifetime and Qt storage residue, “whatever the commit does”; `docs/security/threat-model.md:1390` explicitly names “two lifetimes,” with the same distinction through line 1395. Code supports this: `desktop/src/scribe_desktop/ui/clinics.py:199` reads the key, line 200 calls `setText("")`, line 264 consumes `holder.pop()`, line 275 clears `_pending`, and lines 288–289 call `commit_validation(request, result)` then `del request`. PR-LOW-081 — `docs/security/retention-schedule.md:47` now names the “first caller … BUILT at Tasks 2.1b/2.2,” its transient answers, retained identity/subdomain fields, and Phase 3’s next caller. `desktop/src/scribe_desktop/clinics.py:625`, `:628` and `:638` perform the three reads; lines 659–664 return `ValidatedAccount` containing selected fields, and lines 695–704 construct the registry record. This agrees with `docs/security/data-flow-map.md:529`: “The role, the practitioner list and the rest of each answer are dropped with the call.”
- No new findings: No verified overclaim, lifetime inconsistency or regression in the scoped fixes.
- Verification counts: 2 claims checked, 2 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-27

### Round 20 - 2026-09-27 - Phase 3 (Tasks 3.1–3.6: consent, encounter record, note verification, write-back guard, cross-patient matrix), `/review-loop` round 1 of cap 3

- Round status: Closed (0 pending) — 1 MED + 5 LOW, all Fix-now, all applied in this leg; pytest owed to the composer
- Source: Claude Code (executor leg stage-3-exec-c2, claude-opus-5-5, sequential lenses in-session — no subagents)
- Scope / baseline: the whole Phase 3 working-tree diff over `dc6530b` — `encounter.py` (new, read in full), `session.py`, `session_store.py`, `logging_setup.py`, `clinics.py`, `ui/models.py`, `ui/main_window.py`, `ui/session_screen.py`, `ui/recovery.py` (the changed hunks); `test_cross_patient.py`, `test_encounter.py` (the ledger and guard classes), `test_ui_encounter.py` (read in full), the `test_session_machine.py`, `test_session_types.py`, `test_ui_screens.py`, `test_ui_models.py` and `test_cliniko_client.py` hunks; the threat model's "Cliniko API client" additions, data-flow flows 6 and 18, retention rows 47–48 and the encounter row, the design-system consent entry, the CHANGELOG entry. Composer suite on the pre-round (c1) tree: 3318 passed.
- Lenses and results:
  - Consent (model, `start()`, the UI tick, the child scripts) — CLEAN: `RecordingSession.consent` is required and bound by `_consent_bound`; `start()` refuses a non-attestation, a malformed context and an unbound consent before the lock; the one production `start(` caller is `SessionScreen._start`; the tick is never pre-ticked, gates Start, and is cleared on every press; the four child scripts pass `unlinked_consent()`.
  - `encounter.enc` custody and ordering — CLEAN: written between `wrap_key_to_file` and `SessionChunkStore.create` under the failure cleanup; the order spy and both crash tests pin it; decrypted only in `_open_checkout_encounter` (the listing spy, the sweep spy and the refresh spy pin the rest). Found LOW-017 (flow 6 said the sweep reads whether the file exists; it never touches it).
  - Verification (D4 outcomes, the tags, throttling, stale results, display strings) — outcomes, tags and stale-result rules CLEAN. Found LOW-016 (the "per-note throttle" was per report RUN: A → B → A re-checked A every switch) and LOW-013 (the finished checkout thread's closure kept the request — the checkout's patient and note ids — for the window's lifetime, against flow 18's and the retention row's "dropped when the checkout ends"; the round-15 MED-006 class).
  - Write-back guard — found MED-012 (below). Every refusal is named; the checkout path was already re-verification-only.
  - Cross-patient matrix honesty — CLEAN: every refused row asserts the named refusal and routes through `_NoStartController`, which fails the test if reached; the stale-seq and earlier-connection rows assert `accept` returns False before checking the target and outcome; the positive rows start real sessions. The verified-start positive row changes with MED-012 (it now also pins the refusal before the re-verification).
  - Network confinement — CLEAN: `encounter.py` is the second importer, pinned by `TestConfinement` with the threat model and flow 18; nothing calls the client at import, startup or idle (the checkout is a practitioner action; the ledger has no production caller until Phase 4).
  - UX (the c1 handoff's own note) — found LOW-014; and the copy lens found LOW-015.
  - Docs as control claims — the guard paragraph changes with MED-012; LOW-017.
- Findings:
  - **[MED]** MED-012: `desktop/src/scribe_desktop/encounter.py` `writeback_context` — a LIVE session whose context was VERIFIED at Start yielded a `VerifiedTarget` with no re-verification, so a Replace key (D9: "Replace and Remove also clear that clinic's current verification outcome") after Start left it write-eligible on the old verification; `VerifiedTarget`'s docstring ("a clinic whose key … unchanged since verification") claimed what the live path did not check — materiality=behavioral surface=production — Triage: Fix-now; Decision: Applied — both paths now need a re-verification of the same note dispatched under the clinic's CURRENT `clinic_rev` that came back VERIFIED (D4: Phase 4 re-verifies before the write); no re-verification → `not_reverified` (`not_verified` for a live context that was never verified). `MainWindow.live_writeback_target(reverification=None)` takes Phase 4's result. Docstrings (module, guard, `WritebackSubject`, `VerifiedTarget`), the threat model's WRITE-BACK GUARD paragraph and the CHANGELOG reworded. Tests: `TestWritebackContext::test_a_verified_live_session_yields_its_target_after_a_reverification` (renamed; now passes a re-verification), new `::test_a_start_verification_alone_is_not_trusted` (Start-verified alone → `not_reverified`; a re-verification under an older rev → `reverification_stale`); `test_cross_patient.py::test_a_verified_start_writes_back_only_to_its_own_note` and `test_ui_encounter.py::test_the_live_writeback_target_follows_the_live_session` updated (refused before, a target after the re-verification).
  - **[LOW]** LOW-013: `ui/main_window.py` `_run_reverification` — `TaskThread(lambda: verify_note_context(request, …), self)`: the thread is a child of the window, so its closure kept every checkout's `VerificationRequest` (the host, patient and note ids) for the app's lifetime, while flow 18 and the retention schedule say the checkout's decrypted ids go when the checkout ends — Triage: Fix-now; Decision: Applied — the holder pattern (`holder.pop()`), as round 15 MED-006. Test: `TestRecoveredCheckout::test_a_finished_check_keeps_no_reference_to_its_request` (a `gc.get_referents` walk from the `_run_reverification` thread's function after the checkout ended; asserts such a thread exists).
  - **[LOW]** LOW-014: `ui/main_window.py` `_show_checkout_line` — the checkout's link line was set on the Recovery tab, but opening a recovered session switches to the Transcript screen, so the practitioner saw it only by switching back — materiality=ux surface=production — Triage: Fix-now; Decision: Applied — `TranscriptScreen.link_label` + `set_link_line` (plain text, beside the attribution status line) carry it; `RecoveryScreen.link_label` / `set_link_line` removed (the listing keeps its stat-only suffix). Tests: every checkout assertion reads `transcript_screen.link_label`; the linked-checkout test also pins that the Transcript screen is the current tab.
  - **[LOW]** LOW-015: `ui/models.py` `CHECKOUT_CLINIC_GONE_LINE` — "add its key on the Clinics tab; until then this recording cannot be written back" offered a remedy the structure makes impossible: a clinic added again gets a NEW clinic id (ids are never re-minted), so it never matches the stored context — Triage: Fix-now; Decision: Applied — the line now states the fact only ("…in a clinic that is no longer set up in this app - this recording cannot be written back to Cliniko."), with a comment naming why no remedy is offered.
  - **[LOW]** LOW-016: `encounter.py` `VerificationLedger` — D4's "Context-triggered calls are throttled per note" (Task 3.2) was built as per-RUN sharing, and the docstring called that the per-note throttle: alternating two notes' tabs re-checked each on every switch (up to three GETs each) — Triage: Fix-now; Decision: Applied — a new run for a note VERIFIED within `VERIFIED_REUSE_SECONDS` (60 s) on the same connection generation, clinic id and `clinic_rev` reuses that outcome with no call; refusals and offline outcomes are never reused; `new_connection` clears the entries and every dispatch prunes expired ones (so a reused outcome's display strings are held no longer than the window). `VerificationLedger(clinics, *, clock=time.monotonic)`. Threat model NOTE VERIFICATION and the CHANGELOG say so. Tests: `TestLedger::test_a_recently_verified_note_is_reused_without_a_call`, `::test_reuse_ends_with_the_window_the_rev_or_the_connection`, `::test_a_refused_or_offline_note_is_never_reused`.
  - **[LOW]** LOW-017: `docs/security/data-flow-map.md` flow 6 — "the recovery listing and the sweep read whether the file exists" — the sweep never references `encounter.enc` — materiality=docs-only — Triage: Fix-now; Decision: Applied — "the recovery listing reads only whether the file exists; the sweep never reads it".
- Verification counts: 8 lenses run, 6 candidates, 0 dropped, 0 downgraded
- ruff clean; mypy 43 files; pytest owed to the composer (expected 3318 + 5 = 3323 passed)
- Last reviewed: 2026-09-27

### Round 21 - 2026-09-27 - Phase 3 round-20 fixes, `/review-loop` round 2 of cap 3 (post-fix regression check)

- Round status: Closed (0 pending) — 6/6 round-20 fixes confirmed; no new finding; converged
- Source: Claude Code (executor leg stage-3-exec-c3, claude-opus-5-5, sequential lenses in-session — no subagents)
- Scope / baseline: the round-20 fix sites, then a missed-issue pass over the whole Phase 3 working-tree diff over `dc6530b` (`encounter.py` guard, ledger and worker re-read; the `main_window.py` checkout block; `transcript.py` / `recovery.py` hunks; `ui/models.py` copy; `session.py`, `session_store.py`, `logging_setup.py` hunks; the round-20 tests; threat-model NOTE VERIFICATION and WRITE-BACK GUARD, flows 6 and 18, the retention rows, CHANGELOG). Composer suite on the pre-round (c2) tree: 3323 passed.
- Lenses and results:
  - Post-fix verification — MED-012 CONFIRMED (`writeback_context` returns a target only from `result.outcome.context` after the rev, target and clinic-id match; with no re-verification the live path is `not_verified` / `not_reverified` and the checkout path `not_reverified`; the new test pins both the refusal and the stale-rev case; the three changed tests assert the refusal before and the target after). LOW-013 CONFIRMED (`holder.pop()`; the closure keeps only `holder` and `registry`; the test filters to `_run_reverification` threads and asserts one exists, so it cannot pass vacuously; the other live references, `_reverify_running` and `_checkout.request`, are dropped at finish and at checkout end). LOW-014 CONFIRMED (every `set_link_line` goes to `transcript_screen`; `_end_checkout_encounter` clears it on the session-started, live-transcript and transcript-closed paths; `RecoveryScreen` keeps only the stat suffix; the test pins the current tab). LOW-015 CONFIRMED (no remedy offered; the other "add its key" line, `NoteRefusal.CLINIC_NOT_SET_UP`, is set only by the ledger's host lookup, where adding the clinic does work). LOW-016 CONFIRMED (reuse needs the same connection generation, clinic id and CURRENT rev, within 60 s, VERIFIED only; `new_connection` clears and every dispatch prunes; `reverify_after_clinic_change` cannot reuse, because the rev moved; the three tests walk the window, rev and connection edges). LOW-017 CONFIRMED (the sweep never names `encounter.enc`).
  - Missed-issue pass — CLEAN: the consent path (the one production `start(` caller is `SessionScreen._start`), `_clinic_host`'s `ValueError` contract with `parse_clinic_address`, a checkout opened while a previous check still runs (the new request waits and the old result is dropped by identity), `closeEvent` counting a stale running check as busy (bounded by the client's deadlines), and the tripwire signatures (disjoint from `ALLOWED_KEYS`, pinned).
  - Observation, not a finding (Phase 4's design, recorded as an executor recommendation in the handoff): the guard binds a re-verification to the clinic's current rev, not to its age — a checkout's re-verification stays valid while the checkout is open. D4 puts the fresh check "in Phase 4 before the write"; Phase 4's write must pass a check made for that write.
- Verification counts: 2 lenses run (6 fix checks + the missed-issue pass), 0 candidates, 0 dropped, 0 downgraded
- ruff clean; mypy 43 files; no code or test change (suite stays 3323)
- Last reviewed: 2026-09-27

### Round 22 - 2026-09-27 - Phase 3 consent, encounter and write-back guard (core code), independent cross-family codex peer review (pass stage-3.p1 slice A)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Slice A’s specified core code, diffs, tests and plan sections; static review only, without writes, test execution or network commands.
- **PR-LOW-100** (LOW, test-harness, `desktop/tests/test_encounter.py:698`): The other-clinic credential test never performs verification, so it passes without establishing that clinic B’s key is used. Its shared fixture also gives both clinics the same key, masking credential selection errors even if verification were added. — Evidence: the test ends at line 709 with `assert request is not None and request.clinic.clinic_id == OTHER_CLINIC_ID`; `desktop/tests/encounter_fakes.py:174` assigns `store.store(record["clinic_id"], KEY_SECRET_NAME, KEY)` to every clinic. Recommendation: Fix-now — Give the clinics distinct fake keys, execute and accept B’s verification, and assert the transport used B’s credential and returned B’s verified context. /fix decision: Fixed — `desktop/tests/encounter_fakes.py:27-33,179` (new `OTHER_KEY` and `CLINIC_KEYS`; `make_registry` stores each clinic's OWN key and refuses an unknown clinic id) and `desktop/tests/test_encounter.py` `TestLedger::test_the_other_clinics_note_verifies_under_its_own_key` (now verifies and accepts B's request, asserts every call's `Authorization` is B's Basic token and never A's, the API host, and a `Verified` outcome for `OTHER_CLINIC_ID` / `OTHER_HOST`)
- Verification counts: 3 claims checked, 1 confirmed, 2 dropped as unverifiable
- Last reviewed: 2026-09-27

#### LEG 1 verified tuples (executor, leg stage-3-exec-c4)
- PR-LOW-100 (peer labels: LOW, test-harness, Fix-now) — materiality=behavioral severity=verified: low surface=test-harness rec=Fix-now — CONFIRMED: `test_encounter.py:698-709` `test_the_other_clinics_note_verifies_under_its_own_key` stops at `request.clinic.clinic_id == OTHER_CLINIC_ID`, so no verification runs and no credential is observed; `encounter_fakes.py:173-174` `make_registry` stores the same `KEY` for every clinic, so even an executed verification could not tell clinic B's key from clinic A's. Production is not implicated: `encounter._verify`'s `read_key` retrieves `request.clinic.clinic_id`'s key (`encounter.py` `_verify`), and the ledger builds the request from the host-matched record — but nothing pins that selection, which is the test's stated purpose.
  - Fix shape: `make_registry` gives each clinic a DISTINCT key (the default clinic keeps `KEY`; any other record gets its own, e.g. `KEY_2` or a derived fake with the same `-au2` shard) — check the few `make_registry(…, clinic_record(), clinic_record(OTHER_CLINIC_ID, …))` callers (`test_encounter.py`, `test_cross_patient.py`) still hold; then the test runs `verify_note_context` on B's request, `accept`s it, and asserts (a) every transport call's `Authorization` header is the Basic token of B's key and never A's, (b) the host is B's shard API host, and (c) the applied outcome is `Verified` with `context.clinic_id == OTHER_CLINIC_ID` and `clinic_host == OTHER_HOST`. Test-only; suite +0 (one test strengthened).
  - Decision (leg stage-3-exec-c5, `/fix`): Applied as shaped — `OTHER_KEY` for `OTHER_CLINIC_ID`, `CLINIC_KEYS` strict lookup; the two-clinic callers (`test_encounter.py`, `test_cross_patient.py` ×2) read no key, so they hold. Ruff clean; mypy 43 files.
- Cap verdict: accept — test-harness — the one test meant to pin per-clinic key selection never verifies, and the shared fake key would mask a wrong selection.

### Round 23 - 2026-09-27 - Phase 3 consent, encounter and write-back guard (UI + docs), independent cross-family codex peer review (pass stage-3.p1 slice B)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase 3 UI wiring, scoped tests and documentation; static inspection only, with encounter public APIs as reference. No files written, tests run or network commands executed.
- **PR-LOW-110** (LOW, docs-only, `docs/security/threat-model.md:1434`): The consent-binding claim overstates the enforced practitioner requirement: a linked attestation may omit its practitioner ID. — Evidence: the threat model says “a linked one exactly the context's note and practitioner”; `desktop/src/scribe_desktop/encounter.py:152` declares `practitioner_id: _ClinikoId | None = None`, and line 167 checks mismatch only with `if consent.practitioner_id is not None and consent.practitioner_id != context.practitioner_id:`. Recommendation: Fix-now — State that a linked consent must name the context's note and, **if supplied**, its practitioner; preserve the plan's optional-field contract. /fix decision: Fixed — `docs/security/threat-model.md:1434-1439` (THE ENCOUNTER RECORD: "a linked one names exactly the context's note and, if it names a practitioner (the field is optional, D3), the context's practitioner — `linked_consent`, the only production constructor of a linked consent, always names it"); no code or test change
- Verification counts: 3 claims checked, 1 confirmed, 2 dropped as unverifiable
- Last reviewed: 2026-09-27

#### LEG 1 verified tuples (executor, leg stage-3-exec-c4)
- PR-LOW-110 (peer labels: LOW, docs-only, Fix-now) — materiality=docs-only severity=verified: low surface=docs rec=Fix-now (doc) — CONFIRMED: `threat-model.md:1434` says "a linked one exactly the context's note and practitioner", but `ConsentAttestation.practitioner_id` is optional (`encounter.py:152`) and `bind_consent` (`encounter.py:167`) compares it only when set. The code's own docstrings already state it correctly ("and, if it names a practitioner, the context's practitioner", `encounter.py:160` and the module docstring); the threat model is the only site that overstates (grep over `docs/`, `desktop/src/` and `CHANGELOG.md`).
  - Doc or code: the DOC is the smaller truthful change. D3 fixes `practitioner_id?` as optional (PLAN.md's core type), and the plan's Schema section repeats it; requiring it on a linked consent would change that contract and move the check into `ConsentAttestation` construction — `test_session_machine.py::TestStartRefusesWithoutConsent::test_a_consent_that_does_not_name_the_note_is_refused` and `test_session_types.py::test_consent_must_name_the_sessions_note` build linked consents without a practitioner OUTSIDE their `pytest.raises` blocks, so they would error. It would also add little: the only production constructor of a linked consent, `linked_consent`, always copies the context's practitioner, and D4's verification separately refuses a note whose practitioner is not the clinic's (`wrong_practitioner`).
  - Fix shape: `threat-model.md:1434-1435` → "an unlinked consent names no note; a linked one names exactly the context's note and, if it names a practitioner, the context's practitioner (`linked_consent`, the only production constructor, always names it)". Docs-only; no code or test change.
  - Decision (leg stage-3-exec-c5, `/fix`): Applied as shaped, via the doc. Sibling sweep: the other consent-binding sentences (`encounter.py` module docstring and `bind_consent`, flow 6's "the note and practitioner it names, if any", the CHANGELOG entry) already say "if it names" or make no practitioner claim.
- Cap verdict: accept — docs-only — one threat-model sentence claims a practitioner binding the structure enforces only when the optional field is set.

### Round 24 - 2026-09-27 - Phase 3 consent, encounter and write-back guard (confirmation of rounds 22-23), independent cross-family codex peer review (pass stage-3.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Static confirmation of PR-LOW-100 and PR-LOW-110, affected fixture callers, and regressions introduced by those fixes; specified files only. No writes, tests or network commands.
- Confirmations: **PR-LOW-100 CONFIRMED** — `desktop/tests/encounter_fakes.py:33` maps distinct keys through `CLINIC_KEYS`; line 179 uses `CLINIC_KEYS[record["clinic_id"]]`, raising `KeyError` for unknown IDs. `desktop/tests/test_encounter.py:714` executes verification through `_answer` and accepts it; line 719 asserts `transport.calls`, and line 720 requires the exact singleton `{basic[OTHER_KEY]}`. Because the keys differ, clinic A’s token cannot satisfy that assertion. Lines 721–726 assert the API host and a `Verified` outcome naming clinic B. Affected callers retain their intended behavior; the clinic tests’ separate `make_registry` is unaffected. **PR-LOW-110 CONFIRMED** — `docs/security/threat-model.md:1435` now says “if it names a practitioner”, matching `desktop/src/scribe_desktop/encounter.py:167`: `if consent.practitioner_id is not None and consent.practitioner_id != context.practitioner_id:`. `linked_consent` explicitly sets `practitioner_id=context.practitioner_id` at line 180. It is the only linked-consent constructor in the production code inspected; repository-wide exclusivity is outside the permitted scope. No remaining consent-binding overstatement or newly introduced regression was identified.
- Verification counts: 2 claims checked, 2 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-27

## Tasks
Every task's verification is the per-phase suite in `Validation / Verification` plus the test classes it names. `[executor: premium-only]` marks custody, concurrency, network-surface and security-doc work. The tier is entirely premium, so the labels record where care concentrates rather than routing.

**Order note (hardening pass).** P.1 gates only 2.1b's live route and 3.2's field assumptions. Tasks 1.1, 1.2, 2.1a, 3.1, 3.3, 4.1 and 4.2 have no Cliniko dependency and may run while P.1 is pending. Task 1.4 has no dependents and sits off the critical path.

### Phase 1 — Cliniko read client, offline-contract rewrite, feasibility check
- [x] 🟩 1.1: **Cliniko read client** `[executor: premium-only]`
  - DONE 2026-09-27 (leg stage-1-exec-a7): suite 2973 passed (composer, a6 tree); ruff clean, mypy 40 files; reviewed by `/review-loop` round 7 (4 LOW, applied), codex rounds 8 (3 MED + 1 LOW, fixed) and 10 (confirmation, 0 findings) — pass stage-1.p1 converged.
  - Files: new `desktop/src/scribe_desktop/cliniko_client.py`; `benchmark.py` (`apply_offline_env`/`assert_offline_env` handle `SSLKEYLOGFILE`); new `desktop/tests/test_cliniko_client.py`.
  - Behaviour: GET-only methods for `/user`, `/practitioners?user_id`, `/settings/public`, `/settings`, `/treatment_notes/<id>`, `/patients/<id>`, `/bookings/<id>`, exactly per D9.
  - Verification: the client test classes in Validation.
  - Built (leg `stage-1-exec-a1`, 2026-09-27; 🟨 until the composer's pytest run):
    - `cliniko_client.py` (new): `SHARDS` (the 11 documented shards), `MAX_BODY_BYTES` = 1 MiB, `TIMEOUT_SECONDS` = 15; named errors `ClinikoError` → `InvalidKey`, `CredentialsRejected(status)` (401/403, and a missing key), `NotFound`, `RateLimited(reset)`, `Unreachable(status?)` (connection/DNS/timeout/non-cert TLS/5xx), `CertificateRejected`, `Malformed`, `RedirectRefused(status)`, `UnexpectedStatus(status)` — the last two are ADDITIONS to D9's list (a 3xx and an unlisted status each needed a name); `InvalidContactEmail` / `InvalidId` are `ValueError`s. Every error's text is a fixed class sentence and is raised OUTSIDE the classifying `except` (`_guarded`, `_parse_object`), so `__context__` is None. `Transport` protocol + `RawResponse`; `HTTPSTransport` (GET-only guard before any connection; `connection_factory` / `tls_context` injectable; one connection per request; `set_debuglevel(0)`; each library call wrapped separately; `_read_bounded` asks only for what is left of `max_body + 1`); `_classify` maps `SSLCertVerificationError` → CertificateRejected, `RemoteDisconnected`/`IncompleteRead`/any `OSError` → Unreachable, everything else → Malformed. `build_tls_context` = `SSLContext(PROTOCOL_TLS_CLIENT)` + TLS 1.2 minimum + `load_default_certs` + `keylog_filename = None` (NOT `create_default_context`, which opens `SSLKEYLOGFILE`). `ClinikoClient(contact_email=, transport=)` → `call(read_key)` context manager (key read once, shard → host, Basic token, the call dropped and refusing use on exit) → `ClinikoCall.get_*` returning the JSON object. The practitioners query is `/v1/practitioners?q%5B%5D=user_id%3A%3D<id>`.
    - `benchmark.py`: `FORBIDDEN_TLS_OVERRIDES = ("SSLKEYLOGFILE",)`, deleted by `apply_offline_env`, refused by name by `assert_offline_env` ("TLS key log export present, refused: …").
    - `tests/test_cliniko_client.py` (new): `TestHostPin`, `TestGetOnly`, `TestStatusMapping`, `TestHTTPSTransport` (21 per-stage library failures), `TestTlsContext`, `TestSslKeyLogFile`, `TestNothingLeaks`, `TestContactEmail`, `TestKeyReadOnce`, `TestIds`, `TestConfinement` (exactly one `noqa: TID251`, on the `http.client` import; only the client imports `http`/`ssl`/`socket`/`urllib.request`/`PySide6.QtNetwork`; the native host's import closure never reaches the client; NO app module imports the client yet — Phases 2–3 must update this pin with the docs).
    - ruff clean; mypy 40 files (39 → 40, the new module).
    - Round 7 (leg `stage-1-exec-a2`): `DEADLINE_SECONDS` = 30 (checked after the send and before every body read; injectable `clock`) beside the 15 s per-step timeout, and `RawResponse.body` out of the repr; the deep-array test case got explicit parametrize ids (Windows' 32 767-char env-var cap on `PYTEST_CURRENT_TEST`).
- [x] 🟩 1.2: **Offline-contract rewrite, as a class** `[executor: premium-only]`
  - DONE 2026-09-27 (leg stage-1-exec-a7): suite 2973 passed; reviewed by `/review-loop` round 7 (the doc LOWs applied), codex round 9 (docs slice: 1 MED verified LOW, fixed docs-only as a class) and round 10 (confirmation, 0 findings).
  - Placed here so the docs are never false once `http.client` lands.
  - Files: `desktop/pyproject.toml` (`:8`, `:91-95`); `ui/__init__.py:9`; `language_model.py:21`; the `test_integration_no_sockets.py` module docstring; `AGENTS.md` ("two sanctioned network steps"); the four security docs.
  - Docs:
    - `data-flow-map.md`: `:11-14`, `:49-51`, `:141-142`, `:487-493`, plus a NEW flow "Cliniko API reads" (what leaves: the key, ids, the contact email; what returns: names, appointment time, note metadata; memory only).
    - `threat-model.md`: `:76-78`, `:118-119`, `:1259`, plus a NEW client surface with D9's controls and residue (same-user key read; the Windows-store TLS trust in inspection roots; clipboard history).
    - `retention-schedule.md`: rows for the clinic keys in Credential Manager, `clinics.json`, the API responses (memory) and the contact email.
    - `intended-use.md`: `:3-4`, `:21-22`, `:34-39`.
  - Find every sibling with a recorded grep for "no network", "no sockets", "never the app", "ONLY sanctioned", "sanctioned network".
  - Built (leg `stage-1-exec-a1`, 2026-09-27; 🟨 until the composer's pytest run):
    - **Grep 1 (the task's list)**, `(?i)no network|no sockets|never the app|ONLY sanctioned|sanctioned network` over the repo minus `.cursor/`, `CHANGELOG.md`, `node_modules` (before the edits): `AGENTS.md:33,34`; `desktop/pyproject.toml:92,93`; `desktop/requirements-ml-prose.txt:19`; `scripts/setup-models.py:3,451`; `scripts/measure-prose-fixtures.py:76`; `data-flow-map.md:11,14,17,141,142,373,415,487,550`; `threat-model.md:118,1035`; `docs/architecture/phase-history.md:7`; `src/note.py:46`; `src/benchmark.py:300`; `src/logging_setup.py:398`; `tests/test_integration_no_sockets.py:570,807,981`.
    - **Grep 2 (the class, wider)**, `(?i)network|socket|offline|outbound|internet|leaves? the machine|fully local|no cloud` over `docs/security/`, `desktop/src`, `AGENTS.md`, `PLAN.md` (0 hits), `scripts/`.
    - REWRITTEN: `pyproject.toml:8` (description) and `:90-95` (comment + all four ban messages); `ui/__init__.py:9`; `logging_setup.py:12` ("TID251 bans network imports" → everywhere but the client's one exemption); `test_integration_no_sockets.py` module docstring (scope paragraph); `AGENTS.md` steps 2–3 ("sanctioned" → "setup-time", + the app's only network use), the `.env` note (`SSLKEYLOGFILE`/`LLAMA_CPP_LIB_PATH` removed at startup) and a new Subsystem pointer; `scripts/setup-models.py:3-6`; `requirements-ml-prose.txt:19`; `data-flow-map.md` intro (:10-19 → the contract, its enforcing structure and the dynamic-import residue), components row (`scribe-app`), flow 3 (keys arrive with this plan's Phase 2), flow 9 title and :166-167 ("runtime processes stay socketless"), the network non-flow (:487-494), and NEW flow 18 "Cliniko API reads" (leaves: key, ids, email; returns: role, practitioner, subdomain, note state/links/content, patient record, booking time; memory only; not yet called); `threat-model.md` :76-78 (Credential Manager), surface 3 :118-119, surface 17 :1035 ("SECOND sanctioned" → setup-time), NEW section "Cliniko API client" (confinement, what it can send, transport, untrusted answers, secrets, residue: Windows-store trust incl. inspection roots, un-zeroable key `str`, same-user Credential Manager, clipboard paste, what leaves by design), and the review trigger (:1262-1266); `retention-schedule.md` intro + 4 rows (API responses — BUILT; key in use — BUILT; keys at rest and `clinics.json` + contact email — marked PLANNED, Phase 2); `intended-use.md` :3-4, :21-22 (the Cliniko-API-only network use), :34-39 (a current scope note); `incident-process.md` :15-19 (+ a network-connection incident), :26, :46 (`netstat` wording).
    - LEFT, each still true as scoped: `language_model.py:21` (the prose runtime's own enforcing control — cited by the task, found accurate, unchanged); the per-flow "in-process, zero network" labels and `data-flow-map.md:373,415,550` (each about its own flow); `note.py:46`, `benchmark.py:20,300`, `speech.py:24`, `transcription.py:33`, `speaker_eval.py:50` (module-scoped); `setup-models.py:451`, the three no-sockets test comments, `measure-prose-fixtures.py:76` and `logging_setup.py:398` (not offline-contract claims); `phase-history.md` and `CHANGELOG.md` (history).
    - Two pins added so the new sentences are enforced, not asserted (in `TestConfinement`): the native host's import closure never reaches the client, and no app module imports the client yet.
- [x] 🟩 1.3: **Read-only feasibility script**
  - DONE 2026-09-27 (leg stage-1-exec-a7): suite 2973 passed; reviewed by `/review-loop` round 7 (LOW-004 applied), codex round 8 (PR-MED-011 — the argv echo — fixed) and round 10 (confirmation, 0 findings). The practitioner's run is Task P.1.
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
  - Built (leg `stage-1-exec-a1`, 2026-09-27; 🟨 until the composer's pytest run):
    - `scripts/probe-cliniko.py` (new): prompts for the contact email and the open note's URL (`input`) and the key (`getpass` only; argparse takes NO arguments, so a key on argv is an error); `apply_offline_env` + `assert_offline_env` first; `parse_note_url` (https only, `<subdomain>.<shard>.cliniko.com/patients/<id>/treatment_notes/<id>`); `shape()` reduces every leaf to `<text>`/`<empty>`/`<number>`/`<bool>`/null, prints a non-identifier key as `<key>`, lists as length + distinct shapes, depth capped at 12; `Probe.run` prints each call's status (a refusal as its class name + HTTP status), the shapes, and yes/no facts (key shard vs URL shard, role, active, practitioner record count, `/settings/public` answered + subdomain present/matches, draft, `finalized_at` null/set, the four links, patient link = URL patient, note practitioner = key user's practitioner, booking `starts_at` present). One addition beyond the task's list: the key user's account ROLE word is printed when it is a plain lower-case word (`[a-z_]{1,32}`, e.g. `practitioner`) — D10 validates on it and it is neither a name, id, answer nor key; anything else prints as its kind. A bad email, URL or key sends nothing and is not echoed.
    - `tests/test_probe_cliniko.py` (new): `TestRedaction` (fixture responses carrying names, ids, answer text, phone, DOB, subdomain, email, key — none printed; the expected fact lines present; GET only; one secret prompt), `TestNothingSent`, `TestShape`.
    - `scripts/README.md` entry.
- [ ] 🟨 P.1: **Practitioner runs the feasibility check on both clinics** (practitioner-owned) — clinic 1 DONE 2026-09-27; clinic 2 OWED
  - **Clinic 1 Done note (2026-09-27, two runs by the practitioner from a normal terminal; structure only, relayed by the composer — no ids, names, URL, subdomain or key recorded here):**
    - Key shard = the note URL's shard: yes (confirms D10's shard rule and `clinics.py` item (d)).
    - `GET /user` 200: `id`, `role`, `active` present; role `administrator`, active yes (confirms item (a); the role finding drove D10's 2026-09-27 amendment).
    - `GET /practitioners` for the user 200: exactly 1 record; entries carry `id` and `active` (confirms item (b)).
    - `GET /settings/public` 200 for an administrator key: `account.subdomain` present and matching the note URL's — **D10's primary route applies; the typed-subdomain fallback was not needed** (confirms item (c)'s field; the refusal statuses stay unconfirmed).
    - `GET /settings` 200 (a superset of `/settings/public`).
    - `GET /treatment_notes/<id>`: run 1 404 — the note had been ARCHIVED before the probe (practitioner); run 2, on a freshly opened note left open: 200, `draft: true`, `finalized_at: null`, patient / practitioner / booking / template links present, patient link = the URL's patient, practitioner link = the key user's practitioner record (confirms D4's checks and the draft-links assumption). The note already held the TEMPLATE-DEFAULT answer text (not typed) — recorded for the Phase 4 plan under Deferred.
    - `GET /patients/<id>` 200; `GET /bookings/<id>` 200 with `starts_at` (run 1 skipped it: that note linked no booking — `booking_id` stays optional, D3).
  - **Clinic 2 owed:** the practitioner's user on the second Cliniko account cannot create API keys yet (the account owner must allow it); run P.1 there once it can.
  - Open a patient's treatment note in each clinic, then run `.venv\Scripts\python.exe scripts\probe-cliniko.py` from a normal terminal at the repo root.
  - Paste the printed structure (no patient data) into this task's Done note.
  - Record which D10 subdomain route applies, and what the booking, template and practitioner links showed (feeds D3/D4; `booking_id` stays optional either way).
- [x] 🟩 1.4: **Copy-to-Cliniko flag flip and shipping-gate reframing** — COMPOSER MUST-PAUSE, off the critical path
  - DONE 2026-09-27 (leg stage-1-exec-a10). Suite: 2973 passed (composer, a9 tree). Reviews:
    - `/review-loop` rounds 11 (MED-005: the clipboard residue, docs-only, applied) and 12 (0 findings).
    - Codex round 13 (2 LOW, docs-only, fixed as a class) and round 14 (confirmation, 0 findings). Pass stage-1.p2 converged.
  - Live smoke owed; the checklist is in the handoff.
  - Ask the practitioner, verbatim: "Flip COPY_TO_CLINIKO_ENABLED to True per your 2026-09-27 decision (the shipping gate becomes a quality measurement)?"
  - ANSWERED 2026-09-27 15:31: **Yes — flip it** (composer record `OWNERSHIP: gate-disposition key=task-1.4-copy-flag choice=flip`). The composer briefs a separate leg for the edit after the Phase 1 peer pass; not built in legs a1/a2.
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
  - BUILT 2026-09-27 (leg stage-1-exec-a7; 🟨 until the composer's pytest). The flag Edit was NOT refused. Changes:
    - `ui/models.py:440-449`: `COPY_TO_CLINIKO_ENABLED: Final[bool] = True`, with the dated D12 decision comment. `_copy_ready` and `_apply_copy_binding` are byte-unchanged.
    - `test_ui_screens.py`: `test_default_copy_binding_ships_enabled` asserts `is True`, and that under the default binding an unratified note shows the button (`not isHidden()`), keeps it disabled and keeps the body `NoTextInteraction`.
    - Docs reconciled: `ui/note.py:121-126`, shipping-gate.md (status, intro, both sections, and the "applied 2026-09-27" paragraph), design-system, threat-model 3A surface 4, flow 10, PLAN.md, AGENTS.md, CHANGELOG, and the phase-3a Task 9.1 REFRAMED bullet.
    - Review: rounds 11 (1 MED docs-only, MED-005, the clipboard residue, applied) and 12 (0, converged). ruff clean, mypy 40 files, expected pytest 2973.
  - Grep (the gate page's own, case-insensitive, `COPY_TO_CLINIKO_ENABLED|ships DISABLED|shipping gate` over `desktop/src desktop/tests docs PLAN.md AGENTS.md CHANGELOG.md .cursor/plans/plan-phase3a-note-pipeline.md`). Pre-edit hits and their dispositions:
    - `ui/models.py` flag + comment: FLIPPED. The `__all__` entry `:2403` is left as is (a name).
    - `ui/main_window.py:453` call-time read: LEFT (reads whatever is recorded).
    - `ui/note.py:122` docstring: REWORDED. `:512` default: LEFT (binds the constant).
    - `test_ui_screens.py:3533-3534`: RENAMED + `is True`.
    - `test_ui_screens.py:3559` decision-agnostic pin, the `:5742` docstring and the four monkeypatch outcome tests: LEFT, decision-agnostic by design.
    - `test_note_pipeline.py:19-20` ("the BINDING … stays Task 9.1's shipping gate"): REWORDED to a measurement. `:527`: LEFT (still true).
    - `docs/design-system.md:221,224,229`: REWORDED.
    - `threat-model.md:366-368`: REWORDED.
    - `data-flow-map.md:227`: REWORDED.
    - `PLAN.md:110`: REWORDED with the date.
    - `AGENTS.md:56`: dated note added. `:60`: the must-pause removed from the practitioner-owned list. `:86`: the pointer reframed. `:65`: LEFT (the previous session's history).
    - `CHANGELOG.md:27,29,30`: LEFT (dated history entries); a new Changed entry was added.
    - `docs/architecture/phase-history.md:11,19`: LEFT (history).
    - `shipping-gate.md:1` (title) and `:81` (the grep itself): LEFT, the title kept as the rubric's historical name, which the status line says. `:5,:9,:84,:86`: REWORDED or marked as history.
    - `plan-phase3a-note-pipeline.md` (34 hits: 105–108, 193, 228, 254, 352, 375–419, 440, 516, 534, 543, 636, 1092, 1178, 1312–1403): LEFT as dated plan history. The ONE dated REFRAMED bullet on Task 9.1 supersedes its "bind copy enablement" clause and the Ratified bullet's "flip through `/execute`".
  - Left deliberately:
    - The `_copy_ready` / `_apply_copy_binding` docstrings in `ui/note.py` still say "after Task 9.1 flips the flag" and "the 9.1 shipping flag". D12 keeps `_copy_ready` untouched, and neither wording matches the grep. They are recorded as an executor recommendation in the handoff.
    - `AGENTS.md:60`'s "0%" and "NEXT: Task 1.1" are session status, which belongs to the composer's `/document`.

### Phase 2 — Clinic keys
- [x] 🟩 2.1a: **Clinic record type and loader** (no network)
  - DONE 2026-09-27 (leg stage-2-exec-b9): suite 3136 passed (composer, b6 tree; b8 docs only); ruff clean, mypy 42 files; reviewed by `/review-loop` rounds 15 (1 MED + 4 LOW, applied) and 16 (1 LOW, applied), codex rounds 17 (1 LOW, fixed), 18 (2 LOW docs, fixed) and 19 (confirmation, 0) — pass stage-2.p1 converged.
  - Files: new `clinics.py` (`ClinicRecord`, `ClinicRegistry` load/save fail-closed, `allow_list()`); tests.
  - Built (leg `stage-2-exec-b1`, 2026-09-27; 🟨 until the composer's pytest run):
    - `desktop/src/scribe_desktop/clinics.py` (new): `ClinicRecord` (pydantic, frozen, `extra="forbid"`): `clinic_id` (16 hex, minted by `secrets.token_hex(8)`, never re-minted after a Remove), `display_name` (1–60 chars through `note_config._no_control_chars`), `subdomain` (DNS label, `api`/`www` refused), `shard` (∈ `SHARDS`), `user_id` / `practitioner_id` (the D2 id shape), `validated_at` (aware), and `subdomain_confirmed` (StrictBool) — an ADDITION to D10's field list: the typed-address route needs to record that the subdomain is not yet confirmed; `.host`. `_RegistryFile` = `{schema_version: 1, contact_email, clinics}` with `MAX_CLINICS = 2` (Agreed Scope's two clinics; also bounds the allow-list).
    - Loader: missing file → empty; unreadable / > 64 KiB / not the schema / a repeated clinic id or subdomain → EMPTY registry with `load_problem` set and every mutation refused (`REGISTRY_UNREADABLE`) — a damaged file is never overwritten. Save is `session_store.atomic_write_bytes` (temp + fsync + replace). `allow_list()` = the registry's hosts, sorted. `parse_clinic_address` (a typed host or an `https://` URL on it; only the host kept). `default_registry_path()` = `%LOCALAPPDATA%\ClinikoScribe\clinics.json`.
    - Tests: `tests/test_clinics.py` `TestLoader` (28), `TestClinicAddress` (21).
- [x] 🟩 2.1b: **Key validation and storage** `[executor: premium-only]`
  - DONE 2026-09-27 (leg stage-2-exec-b9): suite 3136 passed; ruff clean, mypy 42 files; `/review-loop` rounds 15–16 and codex rounds 17–19 (pass stage-2.p1 converged). The new-clinic write order below is as amended by round 15 LOW-010 (a failed store deletes whatever it wrote, then rewrites the file; if either step fails the clinic stays listed for Remove), and a stale result — refusal or success — is named `CLINIC_GONE` / `SUPERSEDED` (round 16 LOW-011, round 17 PR-LOW-070).
  - Files: `clinics.py` (`validate_and_store`, `remove`, `confirm_subdomain_from_note`); tests.
  - Behaviour: D10's validation through 1.1, the key via `SecureStorageProvider`, and typed results or named refusals.
  - Verification: the registry test classes, including zero calls at startup or idle.
  - Built (leg `stage-2-exec-b1`, 2026-09-27; 🟨 until the composer's pytest run). ADAPTATION (no scope change): the task's `validate_and_store` is built as a thread split so the network never runs on the GUI thread and the registry is only mutated there — `begin_validation` (GUI: email / key-format + shard / typed address / name checks, a new id, or for Replace key the D9 `clinic_rev` bump; captures the rev) → `run_validation` (worker: ONE `ClinikoClient.call` with the typed key; `GET /user` → `GET /practitioners` → `GET /settings/public`; never raises — every failure a `Refused(reason, clinic_id)`) → `commit_validation` (GUI: rev unchanged, the clinic still exists for a Replace, duplicate subdomain vs the CURRENT registry, then store + write). Plus `remove(clinic_id, *, live_session_clinic)` and `confirm_subdomain_from_note(clinic_id, host, expected_rev)`.
    - `ClinicRefusal` names 26 reasons (every `ClinikoError` class maps to one); the key never enters a `Refused`, a `ValidatedAccount` or the `ValidationRequest` repr.
    - Write order (no failure leaves an unlisted key at rest): new clinic = file then key (a failed store rewrites the file without it); Replace = key then file (a failed write leaves the new key under the old record; the rev is bumped at dispatch AND commit so nothing pending commits); Remove = bump, key delete, then file.
    - `clinic_rev` is NOT bumped by `confirm_subdomain_from_note` (it changes no identity a pending result depends on) — recorded in the module docstring.
    - ~~**P.1 must confirm** — items (a)–(e) incl. `ACCEPTED_USER_ROLES = {"practitioner"}`~~ SUPERSEDED in leg `stage-2-exec-b2` (2026-09-27): P.1 clinic 1 ran and D10 was amended. The block at the top of `clinics.py` ("Cliniko's answers, as Task P.1 found them", items (a)–(d)) now marks each item CONFIRMED (clinic 1) or still owed: (a) `/user` `id` + `active` (role NOT read); (b) `practitioners[]` `id` + `active` — exactly one, active; (c) `account.subdomain` confirmed, the refusal statuses (`_SETTINGS_REFUSED` = 401/403/404) unconfirmed; (d) web shard = key shard, confirmed. `ACCEPTED_USER_ROLES` and `ClinicRefusal.ROLE_NOT_ACCEPTED` are removed; `ClinicRefusal.PRACTITIONER_INACTIVE` is added.
    - Tests: `tests/test_clinics.py` `TestValidation` (54), `TestNothingAtStartupOrIdle` (2), `TestReplaceKey` (6), `TestClinicRev` (5), `TestRemove` (6), `TestWriteOrder` (4), `TestConfirmSubdomainFromNote` (6). `test_cliniko_client.py::TestConfinement` — `test_no_app_module_imports_the_client_yet` → `test_only_the_clinic_registry_imports_the_client` (`["clinics.py"]`), updated WITH the threat model and flow 18.
- [x] 🟩 2.2: **Clinics tab**
  - DONE 2026-09-27 (leg stage-2-exec-b9): suite 3136 passed; ruff clean, mypy 42 files; `/review-loop` rounds 15–16 and codex rounds 17–19 (pass stage-2.p1 converged). Live smoke is owed to the practitioner (checklist in the top handoff bullet). `MainWindow._live_session_clinic()` returns None until Phase 3 links sessions to clinics.
  - Files: new `ui/clinics.py`; `ui/main_window.py`; `ui/models.py` (copy constants); `AGENTS.md` Local Run Steps (the Clinics tab step).
  - Behaviour:
    - A password-masked key field, cleared with `setText("")` after Validate, which also clears undo.
    - A contact-email field.
    - Validate / Replace key / Remove, each with a named status line. Remove needs a second confirming click, and is refused while the live session is linked to that clinic (D10). Replace and Remove bump the clinic's `clinic_rev` (D9) and clear its verification outcome.
  - Verification (clinic mutation): a delayed verification or Validate result after Replace key, after Remove, and with Replace landing between its requests — none restores verified eligibility, display data or a removed registry entry. Remove of the live session's clinic is refused; Remove of the OTHER clinic leaves the live session unchanged.
    - The clipboard-history advice line.
    - Nothing validates at startup.
  - Verification: offscreen UI tests with an injected registry.
  - Built (leg `stage-2-exec-b1`, 2026-09-27; 🟨 until the composer's pytest run):
    - `ui/clinics.py` (new) `ClinicsScreen(registry, *, live_session_clinic)`: the clinic list (`models.clinic_row` — name, host, checked date, "web address not yet confirmed by a note"), the fields (name, contact email prefilled from the registry, a `Password`-echo key field, an optional clinic web address), Validate / Replace key / Remove, an indeterminate progress bar, a plain-text status line, and a red load-problem line that names the file. `_take_key` reads the key once and `setText("")` before the check starts. The check is a `TaskThread` over `registry.run_validation`; the result commits on the GUI thread; a worker failure shows fixed copy only. Validate and Replace key are disabled while a check runs; Remove stays enabled so it can supersede one. Remove arms on the first click ("Confirm remove"; a selection change disarms). `clinics_changed` is emitted after a Replace dispatch (the rev moved), every commit and every Remove.
    - `ui/models.py`: `CLINICS_INTRO`, `CLINIC_KEY_CLIPBOARD_ADVICE`, `CLINIC_ADDRESS_HINT`, the checking / stopped / no-selection lines, the Remove labels, `clinic_refusal_line` (every `ClinicRefusal`, the write-failure line per operation), `clinic_load_problem_line`, `clinic_row`, `clinic_success_line`, `clinic_remove_prompt`.
    - `ui/main_window.py`: a "Clinics" tab between Practitioner and Status; `MainWindow(clinic_registry=)` (the test seam; None = the real `clinics.json`); `_live_session_clinic()` returns None — no session is linked to a clinic until Phase 3, which must answer from the live session there; a window close waits for a running key check.
    - `AGENTS.md` Local Run Steps step 8 (the Clinics tab); `docs/design-system.md` (the tab, "A secret is entered once and never shown again"). Security docs as a class: threat model "Cliniko API client" (the caller, confinement pin, a CLINIC KEYS paragraph with its residue, residue (4), the review trigger), data-flow intro + flows 3 and 18, retention intro + the in-use-key source + the two rows now BUILT, `intended-use.md` scope note, `incident-process.md`; the `cliniko_client.py` docstring's key-source sentence (the Validate reads the typed key, not Credential Manager).
    - Tests: `tests/test_ui_clinics.py` (new, 18: construction with zero calls and zero key reads at startup and idle, masking, advice, damaged file; Validate; Replace key; two-click Remove; linked-clinic refusal; the other clinic's Remove; a Replace result landing after Remove; a Replace landing between the requests; copy for every refusal); `test_ui_screens.py` (the tab list; `_main_window` passes a temporary registry whose key store and transport fail any use); `test_status_and_app.py` smoke and the `test_integration_no_sockets.py` idle child pass a temporary registry (the child keeps the REAL transport, so the idle leg covers the built Clinics tab).

### Phase 3 — Consent, encounter and write-back guard `[executor: premium-only]`
- [x] 🟩 3.1: **Encounter and consent types**
  - DONE 2026-09-27 (leg stage-3-exec-c6): `EncounterContext` / `ConsentAttestation` / `EncounterRecord` and `bind_consent` in `encounter.py`; `consent` REQUIRED on `RecordingSession` (the recorded decision below); three new tripwire signatures. Suite 3323 passed; ruff clean, mypy 43 files; converged by `/review-loop` rounds 20–21 and codex pass stage-3.p1 rounds 22–24 (round 23 PR-LOW-110 corrected the threat model's practitioner-binding sentence).
  - Files: new `encounter.py`; `session.py` (`RecordingSession` fields); `logging_setup.py` (tripwire); the Key Findings test sites for `RecordingSession` (`test_session_types.py:178` rewritten with a typed context, the bare constructions, `test_ui_screens.py:2711`).
  - Behaviour: D3. Decide and record here whether `consent` is required on the model or only at `start()`.
  - Built (leg `stage-3-exec-c1`, 2026-09-27; 🟨 until the composer's pytest run):
    - **DECISION: `consent` is REQUIRED on the model** (`RecordingSession.consent: ConsentAttestation`, no default), not only at `start()`. Reason: Constraint 4 then holds for EVERY construction path (a recovered, retired or test-built session cannot exist without one), and the model's own validator runs `bind_consent` against `encounter_context`, so a consent that names another note is unrepresentable. `start()` keeps its own check first, so the refusal is named (`ConsentRequiredError`) before anything is created. Cost: every bare `RecordingSession()` in the tests now passes `consent=unlinked_consent()` (`test_session_types.py` `_session()`, `test_ui_screens.py` `FakeController.session` and the `TestMainWindow` `model_construct` site).
    - `encounter.py` (new): `EncounterContext` (frozen, `extra="forbid"`: `clinic_id` 16 hex, `clinic_host` = exactly `parse_clinic_address(host).host`, patient / treatment note / practitioner ids, optional booking and template ids, `verification` ∈ {`verified`, `unverified_offline`}, `verified_at` set exactly when verified; `.target`); `ConsentAttestation` (`confirmed_at` aware, `text_version: Literal["recording-consent-v1"]`, optional `practitioner_id` / `treatment_note_id`); `bind_consent` (THE rule: an unlinked consent names no note; a linked one names exactly the context's note and, when it names a practitioner, the context's); `unlinked_consent()` / `linked_consent(context)`; `RECORDING_CONSENT_TEXT` (PLAN.md Flow 2 step 4, verbatim); `EncounterRecord` (`schema_version` 1, consent, context?; validator runs `bind_consent`; `to_bytes` / `from_bytes`, the latter raising `EncounterUnavailable` outside its `except`).
    - `session.py`: `RecordingSession.encounter_context: EncounterContext | None` (was `str | None`) and `consent` with the `_consent_bound` validator.
    - `logging_setup.py`: `_PAYLOAD_SIGNATURES` gains `patient_id`, `treatment_note_id`, `patient_display_name` (quoted and `=` forms) — an encounter model's repr, dump or JSON is dropped; the new signatures are pinned disjoint from `ALLOWED_KEYS`.
    - Tests: `test_session_types.py` (consent required on the model; a linked typed context, frozen; `bind_consent` ×4 on the model; the tripwire case rewritten with a typed context, ×2 linked/unlinked; new `TestEncounterTypesTripwire` ×3); `test_encounter.py` `TestTypes`, `TestEncounterRecord`.
- [x] 🟩 3.2: **Note verification**
  - DONE 2026-09-27 (leg stage-3-exec-c6): `verify_note_context` (one client call, the key read once, never raises; D4's three outcomes), the GUI-thread `VerificationLedger` (conn_gen / run / target / clinic_rev tags; the 60 s per-note reuse of a VERIFIED outcome, round 20 LOW-016), the second `TestConfinement` importer with its docs. Suite 3323; rounds 20–24 (round 22 PR-LOW-100 made the other-clinic test prove per-clinic key selection).
  - Files: `encounter.py` (`verify_note_context`); tests.
  - Behaviour: D4's check, its three outcomes, results tagged with `(conn_gen, seq, target, clinic_rev)` and per-note throttling, through 1.1 with an injected transport. Display strings are returned separately and never persisted.
  - Built (leg `stage-3-exec-c1`, 2026-09-27; 🟨 until the composer's pytest run):
    - Worker `verify_note_context(request, *, key_store, transport=None, clock=None) -> VerificationResult`, never raises: a host that is not the clinic's → `clinic_mismatch` with no call; ONE `ClinikoClient.call` whose `read_key` reads Credential Manager once (`KeyStore.retrieve`; failure or empty → `key_unavailable`); `GET /treatment_notes/<id>` → patient link vs the URL's patient (`patient_mismatch`) → open draft (`note_final` / `note_archived`) → practitioner link vs the clinic's (`wrong_practitioner`) → `GET /patients/<id>` → `GET /bookings/<id>` only when linked. `Unreachable` / `RateLimited` (connection, timeout, 5xx, 429) anywhere → `UnverifiedOffline` (ids only); `CredentialsRejected` / `InvalidKey` → `key_rejected`; `NotFound` → `note_not_found`; `CertificateRejected` → its own reason; everything else (Malformed, redirect, unexpected status, off-shape answer) → `answer_unreadable`.
    - Every assumption about Cliniko's answers sits in ONE block, "Cliniko's answers, as Task P.1 found them" (a)–(d), each marked CONFIRMED (clinic 1); clinic 2 owed. `_LINK_RE` reads `links.self` as `https://<host>.cliniko.com/v1/<resource>/<id>`; patient must be `patients`, practitioner `practitioners`.
    - `NoteDisplay(patient_display_name, appointment_starts_at)` is a separate dataclass on `Verified` (`repr=False`): Cc/Cf/Zl/Zp → space, whitespace collapsed, ≤ 120 chars, "Unnamed patient" when empty; time parsed ISO → UTC or None. Never a field of any model or record.
    - GUI-thread `VerificationLedger(clinics)`: `new_connection()` bumps `conn_gen` and clears the run; `report(seq, target)` drops a seq ≤ the latest, extends the current run for the SAME target (one verification per run), else starts a run — reusing a VERIFIED outcome of the same note from the last 60 s on the same connection and `clinic_rev` with no call (the per-note throttle, round 20 LOW-016) — and returns a `VerificationRequest(conn_gen, seq, target, clinic, clinic_rev, contact_email)` — or records `clinic_not_set_up` with no call (no clinic for the host, or no contact email); `accept(result)` applies only for the same `conn_gen`, the run's `seq_start`, the same target, clinic id and rev, with the clinic still registered (a VERIFIED result also `confirm_subdomain_from_note`); `outcome()` returns None once the rev moves; `reverify_after_clinic_change()`; `start_context(target)` → `EncounterContext` (verified or offline) or `StartRefused` (`no_report`, `target_mismatch`, `checking`, `not_verified` + the note refusal). `reverification_request(context, clinics, *, seq)` for a checkout. ADAPTATION: the ledger is built and tested but has no production caller until Phase 4 wires it to the pipe (Task 4.5).
    - `clinics.py`: `ClinicRegistry.key_store` and `.transport` properties (read by the checkout's worker).
    - `test_cliniko_client.py::TestConfinement`: the importer pin is now `["clinics.py", "encounter.py"]` (`test_only_the_clinic_registry_and_note_verification_import_the_client`), updated WITH the threat model's "Cliniko API client" section (the second caller, NOTE VERIFICATION, THE ENCOUNTER RECORD, THE WRITE-BACK GUARD, the Remove clause, the Replace residue, the review trigger) and data-flow flows 3, 18 and the intro; retention rows 47–48 name the caller.
    - Tests: `test_encounter.py` `TestVerifyNoteContext` (one call, one key read, a key replaced mid-call not mixed in, every refusal and offline class, off-shape answers, display text plain and bounded, no key in any repr), `TestLedger` (dispatch and bind, same-note throttle, replayed report, stale seq, an earlier connection's same-seq result, new connection, Replace key, rev-moved void, Remove, unregistered host, not-a-note, `start_context` refusals, offline startable, subdomain confirmation, the other clinic's key), `TestReverificationRequest`; fakes in `tests/encounter_fakes.py` (injected transport and key store; no socket).
- [x] 🟩 3.3: **`start()` with consent, target and `encounter.enc`; the desktop consent tick**
  - DONE 2026-09-27 (leg stage-3-exec-c6): `start(device_id, *, consent, context=None)` refusing without a bound consent; `encounter.enc` written between `key.dpapi` and `audio.enc` on every start; D2's in-memory `session_ref` registry; the Session screen's consent tick (never pre-ticked, cleared on every Start) and link line. (The c1 leg left this checkbox 🟥 by oversight; it was built there with 3.1–3.6.) Suite 3323; rounds 20–24. The live smoke is owed to the practitioner (the checklist in the top handoff bullet).
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
  - Built (leg `stage-3-exec-c1`, 2026-09-27; 🟨 until the composer's pytest run):
    - `session.py` `start(device_id, *, consent, context=None)`: not a `ConsentAttestation` → `ConsentRequiredError` (new, a `SessionControllerError`); a context that is not an `EncounterContext` → `SessionControllerError`; `bind_consent` failing → `ConsentRequiredError` (`from None`) — all before any directory exists. Order: dir → `wrap_key_to_file` → `write_encounter_record(EncounterRecord(consent, context))` → `SessionChunkStore.create` → capture; a failed encounter write takes the existing failure cleanup (no audio, directory removed). D2 registry: `_new_session_ref()` = `secrets.token_urlsafe(18)` (24 chars, never persisted, never the session id), minted after a successful start; `session_ref`, `resolve_session_ref`, `forget_session_ref`; refs are forgotten at every TERMINAL transition and by `complete_recovered` / `discard_recovered`; a retired (queued) session's ref keeps resolving. Expiry-driven removal waits for Phase 5's Unreviewed list (it can call `forget_session_ref`).
    - `session_store.py`: `ENCOUNTER_FILENAME = "encounter.enc"`, `write_encounter` / `read_encounter` (AES-GCM under the session key, AAD `b"encounter:" + session_id`, `atomic_write_bytes`; a read failure is `StoreCorruptError("encounter record unavailable")` raised outside the `except`); `encounter.write_encounter_record` / `read_encounter_record` wrap them with the schema (`EncounterUnavailable`).
    - `ui/models.py`: `SessionControllerLike.start` signature; `RECORDING_CONSENT_LABEL` (= the verbatim text), `CONSENT_REQUIRED_MESSAGE`, `NOT_LINKED_LABEL` ("Not linked to a Cliniko note"), `NOT_LINKED_DETAIL`, `LINKED_VERIFIED_LABEL`, `LINKED_UNVERIFIED_LABEL`, `session_link_line(session)` (ids never shown).
    - `ui/session_screen.py`: `link_label` (plain text) and `consent_checkbox` directly above Start — never pre-ticked, enabled only when Start is allowed and nothing is busy; Start is enabled only when ticked; `on_start()` refuses unticked with `CONSENT_REQUIRED_MESSAGE`, else clears the tick and starts UNLINKED (`unlinked_consent()`, context None); new `start_linked(consent, context)` for Task 4.5 clears the tick and passes both through; a failed start leaves the tick cleared.
    - Callers: `tests/conftest.py` `start_unlinked(controller, device_id=0)` replaces the in-process `start(0)` / `start(99)` sites (session machine, live session, enrolment, transcription, status-and-app); the 4 child-script strings in `test_integration_no_sockets.py` import `unlinked_consent` and call `controller.start(0, consent=unlinked_consent())`; `FakeController.start` mirrors the refusal and records `started_with`.
    - `docs/design-system.md`: "Recording consent is per recording and never pre-ticked" (the explicit exception to the stored-consent pre-tick rule).
    - Tests: `test_session_machine.py` `TestStartRefusesWithoutConsent` (×3 non-consent values, the missing-argument TypeError, ×3 unbound consents, a malformed context — nothing created in each), `TestEncounterRecordOnStart` (unlinked, linked and offline records; each start its own record; the key → encounter → audio ORDER spy; a simulated crash (a `BaseException`, so no cleanup runs) before audio leaves key + consent record and no audio; a crash before the encounter write leaves no audio; a failed write cleans up; Discard removes it), `TestSessionRefs` (×5); `test_ui_screens.py` `TestSessionScreenConsent` (×8) and the existing screen tests start ticked (`_session_screen`).
- [x] 🟩 3.4: **Encounter on recovery and checkout**
  - DONE 2026-09-27 (leg stage-3-exec-c6): stat-only `has_transcript` / `has_note` / `has_encounter`; the ONE decrypt on checkout with the D4 re-verification on a worker (holder pattern, round 20 LOW-013); the link line on the Transcript screen the checkout lands on (round 20 LOW-014); spy tests for the listing, sweep and refresh. Suite 3323; rounds 20–24.
  - Files: `session_store.py`, `ui/recovery.py`, `ui/models.py` (`RecoverableSessionInfo.has_transcript`/`has_note`/`has_encounter` by stat), `test_ui_models.py:184-265`.
  - Behaviour:
    - `encounter.enc` is decrypted only on checkout (spy test: the list, the sweep and the periodic refresh never decrypt).
    - A checked-out linked session re-verifies (D4) before it counts as linked.
    - Missing or undecryptable means unlinked.
    - `_describe` shows linked/unlinked from the stat, never a decrypted clinic.
  - Built (leg `stage-3-exec-c1`, 2026-09-27; 🟨 until the composer's pytest run):
    - ADAPTATION (the plan's `_describe` line cannot hold as written): `encounter.enc` is written on EVERY start (Task 3.3), so its presence cannot say linked vs unlinked without a decrypt. `_describe` therefore shows what the stat CAN say — "Cliniko link checked when opened" (record present) or "not linked to a Cliniko note (consent record unavailable)" (absent) — and the linked/unlinked status appears only after the checkout's decrypt, on the recovery screen's new link line.
    - `ui/models.py`: `RecoverableSessionInfo.has_transcript` / `has_note` / `has_encounter` by `is_file()` in `list_recoverable_sessions`; `recovery_link_line`, `checkout_link_line(record, *, checking, outcome, clinic_known)`, the `RECOVERY_*` / `CHECKOUT_*` lines, `NOTE_REFUSAL_REASONS` + `note_refusal_line` (a plain line per `NoteRefusal`).
    - `ui/recovery.py`: `_describe` appends the stat line. (The checkout's link line moved to `ui/transcript.py` `link_label` / `set_link_line` in round 20 LOW-014 — the screen a checkout lands on.)
    - `ui/main_window.py`: `_open_checkout_encounter(directory, crypto)` from `_on_recovered` is THE one decrypt (`read_encounter_record`; missing or undecryptable → `record=None`, i.e. unlinked); a linked record dispatches `reverification_request` on a `TaskThread` (one at a time; a queued newer request runs after a stale one finishes; results applied by request identity, `_on_reverified` / `_on_reverify_failed`); `_on_clinics_changed` (from `clinics_screen.clinics_changed`) re-dispatches when the checkout's clinic is gone or its rev moved; `_end_checkout_encounter()` drops the decrypted record on the live-transcript, session-started and transcript-closed paths; `is_reverifying` counts as busy in `closeEvent` ("a Cliniko note check"). `_live_session_clinic()` now answers from the live non-terminal session's `encounter_context.clinic_id` (the Clinics tab's Remove refusal, D10).
    - Tests: `test_ui_models.py` stat flags and `TestEncounterNeverDecryptedOutsideCheckout` (spies on `read_encounter`, `read_encounter_record`, `SessionCrypto.decrypt` and `unwrap_key_from_file`: the listing ×3 refreshes and the sweep — kept and expired — never call them); `test_ui_encounter.py` (23: `_live_session_clinic` for a linked live session ×5 states and none ×3, Remove refused while linked; the list says only what the stat shows ×2 and a refresh never decrypts; a linked checkout decrypts once and re-verifies, is not linked before the answer, an answer after the view closed changes nothing, missing/unlinked record → unlinked with no call ×2, an undecryptable record is consent-unavailable, a removed clinic → no call and no write-back, a refused and an offline re-verification, a key Replace voids the re-verification and checks again, the live write-back target follows the live session).
- [x] 🟩 3.5: **Write-back guard**
  - DONE 2026-09-27 (leg stage-3-exec-c6): `writeback_context` → `VerifiedTarget` or a named refusal, and — since round 20 MED-012 — only on a current re-verification (same note, the clinic's current `clinic_rev`) for live and checked-out sessions alike; `recovered_writeback_target()` / `live_writeback_target(reverification)` as Phase 4's entries. Suite 3323; rounds 20–24.
  - Files: `encounter.py` (`writeback_context(target) -> VerifiedTarget | Refusal`, where `target` is a live session OR a checked-out recovered/Unreviewed session's decrypted encounter plus its re-verification result).
  - Behaviour: each refusal is named. This is Phase 4's only entry to a write target. Both paths are tested.
  - Built (leg `stage-3-exec-c1`, 2026-09-27; 🟨 until the composer's pytest run):
    - `encounter.py`: `WritebackSubject(consent, context, live, reverification)` with `of_live(consent, context, reverification=None)` and `of_checkout(record | None, reverification)`; `writeback_context(subject, clinics) -> VerifiedTarget | WritebackRefused`, checked in order: no consent → `consent_unavailable`; no context → `unlinked`; `bind_consent` fails → `consent_mismatch`; clinic gone → `clinic_gone`; host or practitioner changed → `clinic_changed`; no re-verification → `not_verified` (a live context that is not VERIFIED) / `not_reverified` (every other case — AMENDED by round 20 MED-012: a live context VERIFIED at Start no longer passes alone); a re-verification for another clinic id, another target or an older rev → `reverification_stale`; refused → `reverification_refused` (+ the `NoteRefusal`); offline → `not_verified`; a verified answer naming another note → `context_changed`; else `VerifiedTarget` (ids, booking, template) from the re-verification. Phase 4's write passes its pre-write re-verification (D4) through `live_writeback_target(reverification)`.
    - `ui/main_window.py`: `recovered_writeback_target()` and `live_writeback_target()` — Phase 4's entries; nothing calls them for a write yet.
    - Tests: `test_encounter.py` `TestWritebackContext` (×15, both paths); `test_ui_encounter.py` (the checkout's target before and after re-verification, and the live target); `test_cross_patient.py`.
- [x] 🟩 3.6: **Cross-patient matrix — encounter and custody cases**
  - DONE 2026-09-27 (leg stage-3-exec-c6): `test_cross_patient.py` — 21 cases, every refused row asserting its named refusal through a controller that fails the test if reached, plus the positive offline and verified Starts (the verified one now also pins the refusal before its re-verification). Suite 3323; rounds 20–24.
  - Files: new `desktop/tests/test_cross_patient.py`.
  - Behaviour: the matrix rows that need no pipe or Chrome (mismatches, other clinic, final note, wrong practitioner, missing or corrupt `encounter.enc`, unlinked, unverified, stale `seq`). Every case refuses its named operation; the positive `unverified_offline` Start case (records, write-back refused) lands here too.
  - Built (leg `stage-3-exec-c1`, 2026-09-27; 🟨 until the composer's pytest run): `tests/test_cross_patient.py` (new, 21 cases) — Start refused for a URL patient differing from the note's, not a draft, finalised, wrong practitioner, another clinic's note, an unregistered host or shard (×6); a Start target not the bound report; a stale-seq result and an earlier connection's same-seq result finishing last change neither target, display nor eligibility; a result dispatched before a Replace key cannot start; write-back refused for a missing / empty / corrupt `encounter.enc` (×3), a valid but un-re-verified checkout, unlinked (live and checkout), unverified offline, and a session of the other clinic borrowing this clinic's verification; the positive offline Start (records, write-back refused); a verified start writes back only to its own note; a consent for another note cannot start a linked session. Every row asserts the named refusal and no re-bind. Context rows (patient change, tab close, reconnect) stay Task 5.6's.

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
- [ ] 🟥 8.2: **Copied note kept out of Windows clipboard history and cloud sync** `[executor: premium-only]`
  - Why: practitioner decision 2026-09-27, option (a) "Keep it out of history and sync (Recommended)", taken at the Task 1.4 live smoke (leg stage-1-exec-a11). It closes the residue named by round 11 MED-005.
  - Why this phase: Phase 8 already owns the security docs this task must change, and its live smoke (P.2) re-checks Copy. No earlier phase touches `ui/note.py`'s copy path, and the task has no dependency, so it can also run earlier if the composer prefers.
  - Files: `desktop/src/scribe_desktop/ui/note.py` (`_copy_note`); a pure helper in `ui/models.py` (e.g. `clipboard_mime_formats()` returning the name → bytes map, Qt-free); tests in `desktop/tests/test_ui_screens.py` (`TestNoteWiring`) and `test_ui_models.py`.
  - Behaviour:
    - `_copy_note` places the note through `QClipboard.setMimeData` with a `QMimeData` carrying:
      - the text, `setText(models.format_note_body(note))`, byte-identical to today's `setText` payload;
      - three registered Windows formats, set as `application/x-qt-windows-mime;value="<name>"`:
        - `ExcludeClipboardContentFromMonitorProcessing` (presence is the signal; empty/zero payload);
        - `CanIncludeInClipboardHistory` = DWORD 0 (4 bytes little-endian);
        - `CanUploadToCloudClipboard` = DWORD 0.
    - `_copy_ready` and the click-time re-check are unchanged. Nothing reaches the clipboard unless ratified.
    - Off Windows (CI on Linux) the extra formats are inert, and the text is still what a paste yields.
  - Tests (offscreen, never the real clipboard — extend the existing `_fake_clipboard` stub to capture `setMimeData`):
    - The two round-70 both-outcome pins keep their strength. Under flag off, nothing is placed on either route. Under flag on and ratified, the captured mime's `text()` equals `format_note_body(note)` exactly, and nothing is placed before ratification.
    - A new pin: the captured mime carries all three format names with exactly the payloads above.
    - A helper test pins the name → bytes map.
  - Docs, all stating honestly what the formats do and do NOT do:
    - What they do: Windows clipboard history and cloud clipboard sync honour them, so the note is not kept in history or uploaded.
    - What they do NOT do:
      - they do not stop ANY same-user process reading the current clipboard (boundary 2);
      - third-party clipboard managers may ignore `ExcludeClipboardContentFromMonitorProcessing`;
      - the note stays on the clipboard until something replaces it;
      - nothing is cleared.
    - Sites: threat-model 3A surface 4 ("Residue once copied"), data-flow flow 10, the retention row "A copied note on the Windows clipboard" (Retention and Destruction columns), `intended-use.md`'s scope note (cloud sync off stays advised but is no longer the only mitigation), `docs/design-system.md` if it describes Copy, and `CHANGELOG.md`.
  - Verification: the tests above plus ruff and mypy. P.2 adds a live check: after Copy, Win+V history does not list the note, and the paste into Notepad is unchanged.
  - Not in scope (recorded, not built): clearing the clipboard after a timeout (option (b), not chosen).
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
