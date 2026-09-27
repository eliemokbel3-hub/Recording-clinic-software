# Feature Implementation Plan
**Feature:** cliniko-workflow-safeguards
**Overall Progress:** `91%` (39 of 43 tasks: every build task 1.1–8.2 and H1–H4; open: P.1 (clinic 2), P.2 (clinic 2), H2a and H3a — the last two added 2026-09-28 by the hardening stage; the Phases 4–8 live smoke PASSED on clinic 1 on 2026-09-28 and those phases are committed)

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

  **AS-BUILT ADDENDUM — sleep + screen lock (practitioner decision 2026-09-28, recorded as `OWNERSHIP: gate-disposition key=smoke-step5-sleep-pause choice=sleep-plus-lock`; supersedes "Screen lock does not pause").**
  - **The finding.** In step 5 of the morning smoke, a desktop recording was not paused by Start → Power → Sleep. The log shows no pause event.
    - The practitioner's PC is a Modern Standby machine: `powercfg /a` shows "Standby (S0 Low Power Idle) Network Connected" available, and S1–S3 disabled.
    - On such a machine a desktop window is not sent `WM_POWERBROADCAST` / `PBT_APMSUSPEND` unless it registers for it.
    - The Phase 5 real-dispatch test passed because it sent the broadcast itself. That was a test-harness blind spot.
  - **Now:** the main window registers once its handle exists, only from `app.main` (`system_events.py`, through an injectable `SystemEventRegistrar` seam).
    - `RegisterSuspendResumeNotification(hwnd, DEVICE_NOTIFY_WINDOW_HANDLE)`, so `PBT_APMSUSPEND` arrives on Modern Standby too. The classic broadcast is still handled; a second suspend finds the recording already paused, so there is one pause either way.
    - `WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_THIS_SESSION)`. A `WM_WTSSESSION_CHANGE` / `WTS_SESSION_LOCK` (Win+L, a lid close, standby with sign-in required) pauses ANY recording with the new reason `locked`, exactly like suspend: a linked one also gets the block.
  - **Unlock resumes nothing.** Resume stays a deliberate press through the guarded path, and a linked recording still needs a current matching report. A suspend or lock also ends a clicked "Resume previous" still waiting for its note's report (`SYSTEM_REASONS`).
  - **Locked until unlock (codex round 51 PR-MED-300).**
    - The lock message sets a flag during its own dispatch, before the queued pause runs. While it stands, the ONE resume check (`ChromeBridge.resume_refusal`, which every path runs: the Session screen's Resume, the hotkey, Chrome's `resume`, a waiting "Resume previous") refuses `locked` FIRST, for linked and unlinked recordings alike.
    - `resume_previous` creates nothing, and a waiting one is dropped.
    - `WTS_SESSION_UNLOCK` clears the flag and resumes nothing.
    - A missed unlock is re-checked with Windows once the flag is 5 s old (`WTSSessionInfoEx` → `SessionFlags`); an unanswered check is refused as `lock_unknown`.
    - There is no suspend flag (residue named in the threat model).
  - **Registration lifetime.** Both are given back on close, at quit and after a failed start (`app.py`'s `try/finally`). A refusal never raises; it is logged and shown on the status line and the Session screen.
  - **Residue** (threat model):
    - audio captured between the event and its handling;
    - a machine that sleeps without locking and without delivering the registered notification;
    - no automated test can prove Windows delivers either message on a given machine — the live re-smoke is the proof.
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
- **COMPOSER (2026-09-28, run stage-9 close): the Phases 4–8 LIVE SMOKE PASSED on clinic 1; Phases 4–8, the sleep/lock smoke fix and the hardening stage H1–H4 are committed locally (one commit each; not pushed).** Tasks 6.0–8.2 🟩; P.2 🟨 (clinic 2 waits on P.1 for clinic 2). NEXT: smoke finding S1 (the Recovery list is not refreshed when a Start retires a session — P.2's line), then H2a + H3a through one scoped `/review-plan` (four H3a items need the practitioner: removing Discard from the page block, the Cliniko call-rate numbers, an extra pipe ownership check, stopping a voice enrolment on lock; plus the "Clinic Scribe" vs "Cliniko Scribe" naming decision), then the draft-write plan.
- **EXECUTOR HANDOFF (leg `stage-9-exec-k8`, 2026-09-28T09:09+10:00, run stage-9) — display name "Clinic Scribe" (practitioner decision; H2a SIMP-006 DONE); `reason=composer-run`.**
  - Renamed display strings only:
    - `app.py` (2), `ui/main_window.py` (the window title) and `ui/models.py` (8, including "Clinic Scribe Companion");
    - `extension/src/connection.ts` (7 badge tooltips), `manifest.ts` (name and action title → "Clinic Scribe Companion") and `panel.html` `<title>`;
    - `scripts/setup-models.py`'s docstring.
  - Every `ClinikoScribe` identifier is byte-identical. No test pinned an old string; all pins go through the constants.
  - New `desktop/tests/test_display_name.py` (+2): a text-matching guard over the production source, plus identifier pins. It cannot see run-time-built or split literals, the built `extension/dist`, or docs.
  - Historical text left alone: this plan's closed rounds and the old smoke steps, and old CHANGELOG entries. The docs had no occurrence.
  - Checks: see the brief.
  - Expected:
    - desktop **4124 passed** with the app closed (4122 + 2), or 4123 + 1 skipped with it running;
    - extension **307** (unchanged); `npm run build` is required because the manifest, `connection.ts` and `panel.html` changed.
  - Re-check:
    - Rebuild the extension, reload it in `chrome://extensions`, fully restart Chrome and relaunch the app. The window title, the extension card's name and the icon tooltip read "Clinic Scribe", and the id is unchanged.
    - Validate a saved clinic on the Clinics tab. It must succeed without re-entering a key, which proves the Credential Manager prefix is untouched.
- **EXECUTOR HANDOFF (leg `stage-9-exec-k7`, 2026-09-28T08:21+10:00, run stage-9) — smoke finding S1 FIXED and CLOSED as round 62 (LOW-060); `reason=composer-run`.**
  - What changed:
    - `ui/main_window.py` `_on_session_retired` now re-lists the Recovery tab. It runs on the GUI thread, from a Start's synchronous `session_retired` or the adopt path, so nothing is queued.
    - A new `_on_tab_changed` re-lists the Recovery tab whenever it becomes current.
    - `refresh()` is unchanged: it is stat-only (nothing decrypted, Constraint 7) and applies the same custody exclusion.
  - Tests: +3 in `test_ui_pause_and_unreviewed.py` `TestReminderIndexWiring`. The one-pass in-session review of the diff found nothing.
  - Checks: ruff clean, mypy clean (50 source files), `loop-history-check` run (see the brief).
  - Expected: `cd desktop && ../.venv/Scripts/pytest.exe -q` → **4121 passed + 1 skipped** (4119 + 3 new; with `scribe-app` running, as before). Extension unchanged at 307; no rebuild needed.
  - Live re-check (one step): back-to-back with A saved → the Recovery tab lists A without pressing Refresh.
  - Next: H2a + H3a through one scoped `/review-plan`; P.2 for clinic 2 after P.1 for clinic 2.
- **EXECUTOR HANDOFF (leg `stage-9-exec-k6`, 2026-09-28T07:31+10:00, run stage-9) — codex round 61 FIXED and CLOSED; H4 🟩 (pass `stage-9.p1` converged at peer round 4 of 5); `reason=composer-run`.**
  - PR-LOW-340 (test-harness) is fixed in place. The different-session focus test is now one sequence: a same-session rebuild keeps focus on Pause, then a new session clears it. It fails if restoration is removed or applied across sessions.
  - Only `extension/src/panel.dom.test.ts` and this plan changed, with no production or doc file touched, while the practitioner's smoke runs.
  - Checks: extension `npm run typecheck` and `npm run lint` clean; `loop-history-check` OK (55 entries + 61 headings).
  - Expected: `cd extension && npm run qa`, **307** (unchanged; the test was rewritten, not added). Nothing new needs a build.
  - The hardening stage H1–H4 is 🟩. Open follow-ups: H2a and H3a (a scoped `/review-plan` after the smoke) and P.2 (the practitioner's smoke).
- **EXECUTOR HANDOFF (leg `stage-9-exec-k5`, 2026-09-28T07:25+10:00, run stage-9) — H4 codex rounds 58–60 FIXED and CLOSED (LEG 2 `/fix`); `reason=composer-run`.** The scoped codex confirmation (round 61) follows.
  - **Applied (all 7 findings):**
    - Docs:
      - PR-LOW-310/311 in the threat model;
      - PR-LOW-312 in the data-flow map;
      - PR-LOW-332 in the design system (three one-click desktop Discards named; no code).
    - Docstrings: PR-LOW-320, all three encounter-read callers.
    - Code: `extension/src/panel.ts` (PR-MED-330, plus the Ready-tick sibling) and `panel-view.ts` (PR-LOW-331).
  - **User-visible surface:** the SIDE PANEL only.
    - Live: the timer now updates in place; focus and clicks survive.
    - Blocked: "On screen" shows "No Cliniko note in front" when the bound note's tab is not in front.
    - Ready: ticking the box, then a newer snapshot, keeps its focus.
    - Needs `npm run build` and an extension reload.
  - **Smoke re-check (side panel):**
    1. During a linked recording, Tab to Pause and wait several seconds. Focus stays on Pause, and Enter pauses.
    2. Click Pause and Finish repeatedly across timer ticks. Every click lands.
    3. With the block up on patient B, switch to a non-Cliniko tab. The panel says "On screen: No Cliniko note in front", never B.
  - **Docs also:** CHANGELOG (Fixed), design-system Chrome side (a new "keeps its controls under the practitioner's hand" bullet and the Blocked "On screen" rule).
  - **Checks:** ruff "All checks passed!"; mypy 50 files, no issues; extension `npm run typecheck` and `npm run lint` clean; `loop-history-check` OK (54 entries + 60 headings).
  - **Expected suites:**
    - Desktop **4119 collected** (unchanged: 4118 passed + 1 skipped with `scribe-app` running). Only docstrings changed.
    - Extension **307** (299 + 8).
    - `npm run build` must be re-run.
- **EXECUTOR HANDOFF (leg `stage-9-exec-k4`, 2026-09-28T07:18+10:00, run stage-9) — H4 codex rounds 58–60 LEG 1 VERIFIED (verification only, nothing fixed); `reason=phase-complete`.** H3 is 🟩 (composer suites green: 4118 passed + 1 skipped, 299, build OK).
  - All 7 codex findings are CONFIRMED at the peer's severity:
    - Round 58: PR-LOW-310/311/312, all docs-only.
    - Round 59: PR-LOW-320, docs-only, plus a third decrypt caller, `session.py:1136` (adoption), that the peer missed. The SEC-022 assessment is agreed; it stays in H3a.
    - Round 60: PR-MED-330 and PR-LOW-331 are production-behavioral in the side panel; PR-LOW-332 is docs-only, with two more one-click Discards (Recovery list, Unreviewed list), so the doc changes, not the code.
  - Cap verdicts:
    - Round 58: accept, docs-only.
    - Round 59: accept, docs-only.
    - Round 60: raise +1, production-behavioral.
  - No CRIT/HIGH. The rounds stay Open (8 pending).
  - Nothing outside the plan changed in this leg.
  - **NEXT:** LEG 2, `/fix` of rounds 58–60 per the fix shapes in each `LEG 1 verified tuples` block.
    - PR-MED-330: an in-place timer update plus focus kept by `data-action`, with 4 DOM tests.
    - PR-LOW-331: a focus-matched "On screen" name.
    - The docs items.
    - Then one confirmation round for round 60's panel changes.
- **EXECUTOR HANDOFF (leg `stage-9-exec-k3`, 2026-09-28T06:55+10:00, run stage-9) — HARDENING H3 DONE (`/security-review`, round 57); `reason=composer-run`.** H2 is 🟩 (composer suites green: 4110 passed + 1 skipped, 297, build OK). H4 (the composer-seat codex pass) has not started. H2a and H3a wait for a scoped `/review-plan` after the smoke.
  - **Round 57:** 22 findings, all LOW, plus 1 record-only (SEC-018, write-back freshness, for the write plan).
    - 8 applied.
    - 13 recorded for H3a, each with an Executor recommendation and a `surface=`.
    - No must-pause.
  - **Production changes, and the user-visible surface each touches, for the smoke re-check:**
    1. `extension/src/page.ts`: a `pageshow` listener. A page restored by Back/Forward says hello again, so its **frame or block is redrawn** to the current state. Needs `npm run build` and an extension reload. (SEC-006)
    2. `encounter.py` `_check_note`: a deleted booking (404) no longer refuses the note. The **side panel's Ready layout** shows the note verified with no appointment time. (SEC-011)
    3. `pipe_server.py` `_await_client`: the pipe server survives a client that connects and closes before its connect call. Before, the **Chrome link** died silently until the app restarted. (SEC-002)
    4. `native_host.py` `_classify_raw`: a non-string `type` gets the typed `malformed` error. A fault path; no visible surface. (SEC-001)
    5. `logging_setup.py`: 9 tripwire signatures added (credential and registry). No visible surface. (SEC-010)
    6. `extension/package.json`: the `dev` script removed. (SEC-004)
    7. Docstrings: `pipe_client.py`, `pipe_server.py` ("Windows session").
  - **Smoke re-checks:**
    - On a linked recording's tab, go to another Cliniko page, then press **Back**. The frame, or the block, must match the recording's current state.
    - If a test note with a deleted booking exists, it verifies with no appointment time. Optional.
    - A normal Chrome link and badge after an app restart.
    - For H3a (optional during P.2):
      - After a real lock and unlock, press Resume at once. It should succeed, which confirms the unlock reading SEC-020 relies on.
      - Try sleeping the machine while pressing Start (SEC-021).
  - **Docs:**
    - `docs/security/threat-model.md`:
      - "Windows session", not "logon session";
      - the pipe residues for SEC-013, SEC-014, SEC-016 and SEC-017;
      - mutex SEC-015;
      - extension residue (1), SEC-003's hidden-block Discard;
      - extension residue (2), SEC-005's recording timing plus the build-only note.
    - `data-flow-map.md` flow 19, AGENTS.md and CHANGELOG (Security).
  - **Tests added:** desktop +8 and extension +2.
    - Desktop:
      - `test_native_host.py` +3;
      - `test_pipe_server.py` +1;
      - `test_encounter.py` +3;
      - `test_logging_setup.py` +1.
    - `test_integration_no_sockets.py` and `test_status_and_app.py` changed environment only.
    - Extension: `page.dom.test.ts` +2.
  - **Checks in this leg:** ruff "All checks passed!"; mypy 50 files, no issues; extension `npm run typecheck` and `npm run lint` clean; `loop-history-check` OK.
  - **Expected suites:**
    - Desktop **4119 collected**: 4118 passed + 1 skipped with `scribe-app` running, or 4119 passed with it closed. The launcher leg now logs under `tmp_path`.
    - Extension **299**.
    - `npm run build` must be re-run, because `page.ts` changed.
  - **NEXT:** the composer runs the suites, then H4 (composer-seat codex). H2a and H3a follow after the smoke.
- **EXECUTOR HANDOFF (leg `stage-9-exec-k2`, 2026-09-28T06:36+10:00, run stage-9) — HARDENING H2 DONE (`/simplify`, round 56); `reason=composer-run`.** H1 is 🟩 (composer suites green: 4110 passed + 1 skipped, 297, build OK). H3 has not started.
  - **Round 56:** 16 findings (2 MED + 14 LOW).
    - 3 LOW applied, all behaviour-neutral.
    - 13 recorded for the new task H2a, a scoped `/review-plan` after the P.2 smoke. Each carries an Executor recommendation and a `surface=`.
    - No must-pause: SIMP-006 (the "Clinic Scribe" / "Cliniko Scribe" split; recommended "Clinic Scribe") is the practitioner's call, but nothing changed, so it does not block a commit.
  - **Applied** (user-visible surface: **none**; no smoke step changes):
    1. `extension/src/context.ts`: `ContextReporter`'s `get active()` and `isTracked()` are removed. They had no caller; `npm run typecheck` pins this.
    2. `extension/src/panel.ts:19` and `:135`: the Checking layout takes `CHECKING` from `panel-view.ts`. The string is identical; `panel-view.test.ts:129` and the panel DOM tests pin it.
    3. Comments only:
       - `extension/src/connection.ts:122`;
       - the `ui/main_window.py` `recovered_writeback_target` / `live_writeback_target` docstrings, which now name PLAN.md Phase 4's draft write.
  - **Checks in this leg:** ruff "All checks passed!"; mypy 50 files, no issues; extension `npm run typecheck` and `npm run lint` clean; `loop-history-check` OK.
  - **Expected suites:**
    - Desktop **4111 collected**: 4110 passed + 1 skipped with `scribe-app` running, or 4111 passed with it closed. No test was added or removed.
    - Extension **297**, unchanged.
    - `npm run build` must be re-run, because `panel.ts`, `context.ts` and `connection.ts` changed.
  - **NEXT:** the composer runs the suites. Then H3 (`/security-review`) in a later leg. H2a waits for the smoke.
- **EXECUTOR HANDOFF (leg `stage-9-exec-k1`, 2026-09-28T06:28+10:00, run stage-9) — HARDENING H1 CONVERGED (`/review-loop` rounds 53–55 over Phases 1–8 as one surface); `reason=composer-run`.** H2, H3 and H4 have not started.
  - **Rounds:**
    - Round 53 (six lens subagents): 2 MED + 11 LOW.
    - Round 54 (regression and same-family sweep): 1 MED + 5 LOW.
    - Round 55 (regression): 2 LOW, docs only. Converged at round 3 of 3.
    - All 21 findings were applied; none is pending, and there is no must-pause.
  - **Production changes and the user-visible surface each touches (for the smoke re-check):**
    1. `ui/bridge.py` `_start`, plus `_start_guard_message` installed through the new `SessionScreen.set_start_guard` (`ui/session_screen.py` `_start`). Every Start — the **side panel Start** and the **Session tab Start** — is refused while the lock flag stands. The `ui/models.py` `CHROME_REFUSALS["locked"/"lock_unknown"]` texts now end "…then press it again." (the lock refusal wording on the **Session tab, side panel and hotkey flash**). (MED-039, MED-052)
    2. `ui/session_screen.py` `_start`, failure path: a Start that fails after retiring a queued linked session still announces it. `ui/main_window.py` `_released_checkout_entry` / `_index_released`, in `_on_session_started` and `_on_live_transcript`: a recovered linked view replaced without Complete or Discard is indexed from its checkout record, with no decrypt. Surface: the **Unreviewed banner in Chrome** / "Open for review". (LOW-040)
    3. `ui/bridge.py` `_Refusal.situation`, `_situation(action)` and `_current_refusal()`: the **side panel refusal line** and the Session tab's "Refused from Chrome" line drop a refusal once its tab, note, (for Start) verification, session or state changes. (LOW-042, LOW-053)
    4. `extension/src/page.ts` `REASONS.note_changed`: "The recording's tab opened a different treatment note." Surface: the **page block card**. Needs `npm run build` and an extension reload. (LOW-043)
    5. `encounter.py` `_display_text` and `ui/bridge.py` `_one_line` clean lone surrogates. Surface: **patient names** in the panel, the block and the Session tab; in practice this only affects malformed data. (LOW-044)
    6. Comments and docstrings only: `ui/__init__.py` and `extension/src/manifest.ts` (step 7).
  - **Smoke steps to re-check:**
    - **Step 5 re-smoke:** additionally lock with the side panel Ready shown, and confirm Start is refused after sign-in only while the flag stands.
    - **A normal Start from the panel and from the Session tab.**
    - **A patient switch (the block text).**
    - **A refused Start** on a final or unknown note, then opening another patient's note: the red line must go.
    - **The Unreviewed banner** after back-to-back consultations.
  - **Tests added:**
    - `test_ui_bridge.py` +6: Start locked ×2, desktop Start locked ×2, refusal leaves with its situation, a failed Resume previous stays shown.
    - `test_ui_pause_and_unreviewed.py` +1.
    - `test_ui_encounter.py` +4.
    - `test_encounter.py` +1.
    - `test_cross_patient.py`: one assertion updated (no refusal after the conn-2 report).
    - `page.dom.test.ts`: the text updated.
  - **Checks in this leg:** ruff "All checks passed!"; mypy 50 files, no issues; extension `npm run typecheck` and `npm run lint` clean; `loop-history-check` OK.
  - **Expected suites:**
    - Desktop **4111 collected** = 4099 + 12. That is 4110 passed + 1 skipped with `scribe-app` running, or 4111 passed with it closed.
    - Extension **297**, unchanged in count.
    - `npm run build` must be re-run, because `page.ts` changed.
  - **Recorded for H2** (round 53, lens f):
    - Three copies of the block-reason table.
    - The "Clinic Scribe" / "Cliniko Scribe" naming split (a practitioner naming call).
    - Test-only symbols.
    - Two re-verification pipelines.
    - Duplicated regexes and constants.
    - `pipe_client` importing `pipe_server`'s private helpers.
    - The oversized `ui/models.py`, `main_window.py` and `bridge.py`.
    - The LOW-047 ref-expiry code fix.
  - **Recorded for H3:**
    - A rate throttle honouring `RateLimited.reset`.
    - Stopping or refusing a voice enrolment on lock.
    - Checking a `WTS_SESSION_UNLOCK` with Windows before trusting it.
    - The unconfirmed re-entrant suspend during a GUI-thread Start (round 53 "needs investigation").
  - **For the write plan:** the write-back freshness gap (Follow-Up Continuation Notes).
  - **NEXT:** the composer runs `cd desktop && ../.venv/Scripts/pytest.exe -q` and `cd extension && npm run qa && npm run build`. Then H2 (`/simplify`) in a later leg.
- **EXECUTOR HANDOFF (leg `stage-8-exec-h7`, 2026-09-28T05:44+10:00, run stage-8) — codex round 51 FIXED and CLOSED (PR-MED-300: locked until unlock); `reason=composer-run`.** A scoped codex confirmation (round 52) follows.
  - **Fix:**
    - The lock message sets a flag during its own dispatch, before the queued pause. The one resume check (the Session tab's Resume, the hotkey, Chrome's `resume`, a waiting "Resume previous") refuses `locked` first, for every recording; `resume_previous` creates nothing while locked.
    - The unlock clears the flag and resumes nothing.
    - A missed unlock is re-checked with Windows after 5 s; `lock_unknown` names the escape.
    - No suspend flag (residue named). Full notes on round 51's `/fix decision` and final-disposition lines.
  - **Checks:** ruff "All checks passed!"; mypy 50 files, no issues; extension `npm run typecheck` and `npm run lint` clean (no extension change).
  - **Expected suites:**
    - Desktop **4099 collected** = 4076 + 23 (`test_system_pause.py` +19, `test_ui_bridge.py` +4). That is 4098 passed + 1 skipped while the practitioner's `scribe-app` is running (the launcher leg's host-state skip), or 4099 passed with it closed.
    - Extension **297**; `npm run build` unchanged.
    - Watch items:
      - (1) the real-dispatch child now expects `FLAGS [true, false]` before `SENT ["locked"]`;
      - (2) `TestSessionInfoQuery::test_the_layout_is_cs` pins `WTSINFOEXW`'s `Data` offset at 8 — ctypes' alignment of the 64-bit times.
  - **RE-SMOKE — step 5** (mock consultations, clinic 1 only; report PASS/FAIL per step; no identifying data in chat):
    1. Rebuild and reload the extension (`cd extension && npm run build`, reload in `chrome://extensions`), then fully quit and relaunch `scribe-app` from Explorer.
    2. **Lock, desktop:** start a DESKTOP recording, press **Win+L**, wait ~5 s and sign back in. *Expect:* paused with "Paused - the computer was locked. Press Resume to carry on recording."; still paused after signing in; **Resume** carries on. Then Discard.
    3. **Lock, linked:** start a LINKED recording from a mock patient's note (side panel → consent → Start), press **Win+L**, sign back in. *Expect:* the desktop and the side panel both show it PAUSED with the lock text, and the Cliniko page shows the block with "The computer was locked."; Resume (or Resume previous) works after sign-in. Then Discard.
    4. **Sleep:** with a linked recording, **Start → Power → Sleep**, wake and sign in. *Expect:* paused with a cue on wake, and the block reason "The computer went to sleep." or "The computer was locked."; Resume works after sign-in. If step 2, 3 or 4 does NOT pause, report the app log's `suspend_notification` / `lock_notification` lines (`on` or `failed`).
  - **NEXT:** the composer runs `cd desktop && ../.venv/Scripts/pytest.exe -q` and `cd extension && npm run qa && npm run build`, then the scoped codex confirmation (round 52), then the practitioner's re-smoke above.
- **EXECUTOR HANDOFF (leg `stage-8-exec-h6`, 2026-09-28, run stage-8) — LEG 1 VERIFICATION of codex round 51. Nothing fixed; no code or doc changed.** PR-MED-300 is VERIFIED as MED, behavioral, production, Fix-now. A `resume_previous` or `resume` command still in flight when the lock is handled runs after the lock's clearing, re-creates the pending resume or resumes directly, and the recording restarts behind the locked screen. `state_rev` cannot catch it, because a lock on a blocked session publishes an identical snapshot. Fix shape: a "locked until unlock" flag set synchronously in `nativeEvent` and checked FIRST in `resume_refusal`, the single guard every resume path funnels through (the button, the hotkey, Chrome's `resume`, a pending "Resume previous"), plus a refusal in `_resume_previous`. New refusal code `locked`; no suspend flag (residue named); about 7 regression tests. Round 51 stays Open. Cap verdict `accept`. NEXT: `/fix` of round 51 (composer's call).
- **EXECUTOR HANDOFF (leg `stage-8-exec-h5`, 2026-09-28T05:24+10:00, run stage-8) — SMOKE FIX for step 5 BUILT: sleep + screen-lock pause (practitioner decision `smoke-step5-sleep-pause` = sleep-plus-lock, amending D5); `/review-loop` rounds 49–50 converged (1 LOW applied, then clean); `reason=composer-run`.**
  - **What changed.** The main window now registers with Windows for the suspend notification that also works on Modern Standby, and for the session-lock notification (`system_events.py`). A lock pauses ANY recording with the cue "Paused - the computer was locked. Press Resume to carry on recording." (a linked one also gets the block). Unlock does nothing; Resume stays a press. A refused registration shows on the status line and the Session screen. The side panel and the page's block read "The computer was locked." Details are in D5's AS-BUILT addendum, Task 5.1's smoke line and round 49.
  - **Checks in this leg:** ruff "All checks passed!"; mypy 50 files (the new module), no issues; extension `npm run typecheck` and `npm run lint` clean.
  - **Expected suites:**
    - Desktop **4076** = 4027 + 49:
      - new `test_system_pause.py`: 26;
      - `test_context_rules.py`: +17 (the table's `PauseReason` parametrisations gain `locked`, and the suspend test covers lock);
      - `test_ui_bridge.py`: +6.
    - Extension **297** = 295 + 2 (`panel-view.test.ts`, `page.dom.test.ts`); `npm run build` must be re-run, because the panel and page text changed.
    - Watch items:
      - (1) `test_a_real_lock_message_through_qts_dispatch` (Windows, integration) expects `UNREGISTERED []`, `SENT ["locked"]`, `SEEN ["locked", "locked", "suspend"]`.
      - (2) The `app.main` start-up test in `test_hands_free.py` now patches `attach_system_pause` with a fake and pins the four registrar calls; no test registers with Windows.
  - **RE-SMOKE — step 5** (mock consultations, clinic 1 only; report PASS/FAIL per step; no identifying data in chat):
    1. Rebuild and reload the extension (`cd extension && npm run build`, then reload in `chrome://extensions`), then fully quit and relaunch `scribe-app` from Explorer.
    2. **Lock:** start a DESKTOP recording (Session tab, tick consent, Start), then press **Win+L**, wait ~5 s and sign back in. *Expect:* paused, with "Paused - the computer was locked. Press Resume to carry on recording." on the Session tab and the status line; still paused after signing in; **Resume** carries on. Then Discard.
    3. **Sleep:** start a LINKED recording from a mock patient's note in Chrome (side panel → consent → Start), then **Start → Power → Sleep**; wake and sign in. *Expect:* paused, with the desktop cue on wake, and the Cliniko page showing the block with the reason "The computer went to sleep." or "The computer was locked." (whichever Windows sent first).
    4. **Side panel:** check that it shows the same paused reason; then Resume previous or Resume on the recording's own note resumes, and Discard ends it. If step 2 or 3 does NOT pause, open the app log and report whether the `suspend_notification` / `lock_notification` lines say `on` or `failed`.
  - **NEXT:** the composer runs `cd desktop && ../.venv/Scripts/pytest.exe -q` (expect 4076) and `cd extension && npm run qa && npm run build` (expect 297, build OK), then the practitioner's re-smoke of step 5 above. A codex confirmation over this diff is the composer's call.
- **EXECUTOR HANDOFF — PHASE 8 FINAL (leg `stage-8-exec-h4`, 2026-09-28T04:37+10:00, run stage-8): codex rounds 46–47 FIXED and CLOSED; `reason=composer-run`.** The scoped codex confirmation (round 48) comes next. If it is clean, the composer closes Phase 8 without resuming this seat. Tasks 8.1 and 8.2 stay 🟨 until the morning smoke and commit; P.2 stays 🟥 (practitioner-owned).
  - **Codex pass `stage-8.p1`** (gpt-6-astra medium, two slices):
    - Round 46, slice A (the clipboard code, its tests and doc sites): 2 LOW. PR-LOW-270, test-harness: `_fake_clipboard` now asserts the offscreen platform and guards Qt's native `keyPressEvent` / `copy`, so a regressed Copy interception fails the test before any clipboard write; +2 tests. PR-LOW-271: `intended-use.md` names the clipboard limits.
    - Round 47, slice B (the security docs as one class): 2 LOW. PR-LOW-280: four sites now say a Chrome-LINKED recording starts from a verified (or `unverified_offline`) note, a desktop Start is unlinked, and D5's actual triggers apply (a separate non-Cliniko tab does not pause). PR-LOW-281: the incident recovery `netstat` check now applies with Chrome closed and no practitioner action.
    - Every finding was verified in leg h3 and applied here. There was no CRIT, HIGH or MED.
  - **Before that pass:** `/review-loop` round 45 converged at round 1 (2 LOW docs, both applied).
  - **Checks in this leg:** ruff "All checks passed!"; mypy 49 files, no issues; extension `npm run typecheck` and `npm run lint` clean (no extension change).
  - **Final expected suites:**
    - Desktop **4027** = 4025 + 2 (`test_the_native_copy_guard_passes_other_keys_to_qt`, `test_an_unintercepted_copy_key_fails_before_any_clipboard`).
    - Extension **295**; `npm run build` OK (no extension change in Phase 8).
    - Watch item: `_fake_clipboard` now patches `QPlainTextEdit.keyPressEvent` / `copy` at class level for each copy test, and monkeypatch restores them. If PySide6 refused a class attribute set, all seven copy tests would error at setup, and nothing would be written to a clipboard.
  - **MORNING LIVE CHECK — Task 8.2** (joins P.2; mock note only, never real patient text). First turn Windows clipboard history on (Settings → System → Clipboard) if it is off.
    1. Generate, ratify and Save a MOCK note in `scribe-app`, press the Note tab's **Copy** button, and paste into Notepad. *Expect:* the note exactly as shown.
    2. Select a few lines of the note body with the mouse, press **Ctrl+C** and paste into Notepad. *Expect:* exactly the selected text.
    3. Right-click the selection → **Copy** (the menu offers only Copy and Select All), then paste. *Expect:* exactly the selected text.
    4. Press **Win+V**. *Expect:* none of the three copies is listed. Report PASS/FAIL per step.
  - **For the practitioner to decide or know:**
    1. **Taken overnight, revisable — the selection copy** (composer disposition `task-8.2-selection-copy`). The ratified note panel stays selectable (round 35's design). Its Ctrl+C / Ctrl+Insert and its own right-click Copy now carry the same three formats as the button, and nothing copies before ratification. The alternative, an unselectable panel with the button as the only route, was not taken.
    2. **The code gap found while documenting** was that selection gap (leg h1's must-pause). It is closed in code by item 1, and no other gap was found.
    3. **Residues newly named in the threat model:**
       - **The clipboard (3A surface 4):**
         - once copied, the note is outside the app: it stays until replaced, since nothing clears it;
         - any same-user program can read it, and a third-party clipboard manager may ignore the marks;
         - a DRAG of the selection carries no marks (but does not use the clipboard);
         - a screenshot remains possible;
         - the app cannot see whether clipboard history or sync is on, so keeping cloud sync off stays advised.
       - **The encounter record:** no consent evidence outlives the session; a durable consent record belongs to PLAN.md Phase 6.
       - **"The Chrome extension" section, eleven residues:**
         - (1) the frame and block are a cue, not a control; Cliniko's page can hide them, and its shortcuts still pass;
         - (2) detectability: a Cliniko page can tell the extension is installed through `web_accessible_resources`;
         - (3) what a Cliniko page can see;
         - (4) an in-page session-expiry dialog does not report;
         - (5) speech before the next note loads, and latency;
         - (6) the login page is recognised by `/users/sign_in`, which is UNVERIFIED on a live Cliniko — worth a glance in the smoke;
         - (7) one Chrome profile links at a time;
         - (8) Chrome crash dumps;
         - (9) names in Chrome's memory;
         - (10) the no-storage / text-only guards are text-matching, not proofs;
         - (11) every report and click the extension relays is its assertion (the same-user pipe residue).
  - **NEXT:**
    - The composer runs `cd desktop && ../.venv/Scripts/pytest.exe -q` (expect 4027) and `cd extension && npm run qa && npm run build` (expect 295, build OK).
    - Then the scoped codex confirmation, round 48, over the h4 hunks: `test_ui_screens.py` `_fake_clipboard` plus the 2 tests; `intended-use.md`; `PLAN.md:47` and `:135`; `AGENTS.md:60`; `incident-process.md` Recover step 1.
    - Then the practitioner's P.2 with the check above, the Phase 4–7 smokes, and the commits.
- **EXECUTOR HANDOFF (leg `stage-8-exec-h3`, 2026-09-28, run stage-8) — LEG 1 VERIFICATION of codex rounds 46–47. Nothing was fixed and no code or doc changed.**
  - All four findings are valid LOWs (0 CRIT, 0 HIGH, 0 MED), each Fix-now:
    - PR-LOW-270, test-harness: an offscreen-platform assert plus a `QPlainTextEdit.keyPressEvent`/`copy` spy that refuses Copy keys, +2 tests. The real clipboard is not reachable in the default offscreen run.
    - PR-LOW-271, docs: one sentence in `intended-use.md`.
    - PR-LOW-280, docs: the class check widened it to 4 sites — `PLAN.md:47`, `PLAN.md:135`, `intended-use.md:47` and `AGENTS.md:60`.
    - PR-LOW-281, docs: `incident-process.md:61`.
  - Both rounds stay Open, and both Cap verdicts are `accept`. The tuples are in the LEG 1 blocks under each round.
  - NEXT: `/fix` of rounds 46–47 (composer's call).
- **EXECUTOR HANDOFF (leg `stage-8-exec-h2`, 2026-09-28T04:19+10:00, run stage-8) — the 8.2 selection-copy gap CLOSED in code (composer disposition `task-8.2-selection-copy`: complete 8.2's own goal, the round-35 selectable panel kept — revisable by the practitioner), then `/review-loop` round 45 over the whole Phase 8 diff CONVERGED at round 1 of cap 3 (0 CRIT / 0 HIGH / 0 MED / 2 LOW docs, both applied); `reason=composer-run`.** Tasks 8.1 and 8.2 stay 🟨 (details on the 8.2 task line's ADDED block and in round 45); P.2 🟥.
  - **Landed:** `ui/note.py` `_place_note_text` (the ONE placement of note text: plain text + the three formats; the Copy button now calls it) and `_NotePanel` (the note body): every binding of the Copy key (Ctrl+C, Ctrl+Insert) and the panel's own context menu (Copy, Select All — replacing Qt's) copy `textCursor().selection().toPlainText()` through that placement, each re-checking `_copy_ready`; nothing is placed before ratification, even over a selection made in code. Named, not covered: a drag of the selection (Qt's own, never the clipboard). Round 45 fixes: LOW-036 (AGENTS.md step 8 no longer calls Validate "the only moment the app talks to Cliniko"; the data-flow no-network non-flow and the incident trigger name the Chrome-report trigger) and LOW-037 (flow 20 / the Chrome-side retention row: the panel's Ready key, the worker's last-sent slices).
  - **Checks in-leg:** ruff "All checks passed!"; mypy 49 files, no issues; extension `npm run typecheck` and `npm run lint` clean (no extension change).
  - **Expected suites:** desktop **4025** = 4022 + 3 (`test_a_keyboard_copy_of_the_selection_carries_the_formats`, `test_the_context_menu_copy_carries_the_formats`, `test_an_unratified_panel_places_nothing_even_with_a_selection`; `_attempt_copy` now also drives the selection routes inside the two round-70 pins without adding tests). Extension **295**; `npm run build` unchanged.
  - **Watch items for the composer's run:** (1) the keyboard test iterates `QKeySequence.keyBindings(StandardKey.Copy)` on the offscreen platform and asserts Ctrl+C is among them — if the offscreen theme lists more bindings (Ctrl+Insert; an X11 Copy key), each is driven and must place one mime; (2) the context-menu test triggers the real `QAction` and stubs only the modal `exec`; (3) `_attempt_copy` now calls `selectAll()` on the note panel before ratification — the later exact-text assertions read the Copy button's payload, which does not depend on the selection.
  - **MORNING LIVE CHECK — Task 8.2 (joins P.2; mock note only, never real patient text):**
    1. Turn on Windows clipboard history (Settings → System → Clipboard) if it is off, and press Win+V once to see what is listed.
    2. In `scribe-app`, generate, ratify and Save a MOCK note, then press the Note tab's **Copy** button, and paste into Notepad (Ctrl+V). *Expect:* the note text exactly as shown in the Note tab.
    3. In the Note tab, select a few lines of the note body with the mouse and press **Ctrl+C**; paste into Notepad. Then right-click the selection → **Copy**; paste again. *Expect:* exactly the selected text each time, and the right-click menu offers only Copy and Select All.
    4. Press Win+V. *Expect:* none of the three note copies is in the history list. Report PASS/FAIL per step.
  - **NEXT:** the composer runs `cd desktop && ../.venv/Scripts/pytest.exe -q` (expect 4025) and `cd extension && npm run qa && npm run build` (expect 295, build OK); on green, round 45 needs no further in-session round (docs-only fixes, no CRIT/HIGH/MED); next is the composer-seat codex pass over the Phase 8 diff, then the practitioner's P.2 (which now includes the 8.2 check above).
- **EXECUTOR HANDOFF (leg `stage-8-exec-h1`, 2026-09-28T04:06+10:00, run stage-8) — Phase 8 Tasks 8.1 and 8.2 BUILT (both 🟨; file-by-file records under each task); `reason=must-pause` for ONE production gap found while documenting 8.2 (below), and the suites are owed on this tree either way.** Built on the uncommitted Phase 4–7 tree; nothing committed. P.2 stays 🟥 (practitioner-owned).
  - **Checks in-leg:** `ruff check .` "All checks passed!"; mypy "no issues found in 49 source files". No extension source changed (typecheck/lint baselines stand).
  - **Expected suites:** desktop **4022** = 4017 + 5 (`test_ui_screens.py` +1 `test_copy_keeps_the_note_out_of_clipboard_history_and_sync`; `test_ui_models.py` `TestClipboardFormats` +4); the two round-70 pins and `test_ui_prose_stage.py::test_display_reload_and_copy_agree` are unchanged in count and must stay green through the fakes' new `setMimeData`. Extension **295** (unchanged); `npm run build` unchanged.
  - **MUST-PAUSE item (surface=production, MED, scope expansion):** the practitioner's 8.2 decision ("keep it out of history and sync") is honoured by the Copy BUTTON only. Once a note is ratified, `_apply_copy_binding` makes the note panel (`QPlainTextEdit`, `ui/note.py:421`) selectable by mouse and keyboard (`ui/note.py:2071` `_apply_copy_binding`, round-35 design; the button's path is `_copy_note`, `ui/note.py:2027`), and a Ctrl+C or context-menu copy of a selection goes through Qt's own `createMimeDataFromSelection` — plain text with NONE of the three formats, so it lands in clipboard history and cloud sync when those are on. The docs now say exactly that at every site (not fixed in code, per the contract). **Executor recommendation: Include in plan** — a small Task 8.2b: give the note panel a `QPlainTextEdit` subclass whose `createMimeDataFromSelection` adds the same formats from `models.clipboard_mime_formats()` (one helper, two callers), tested by calling that method on an offscreen widget (never the real clipboard); then narrow the docs' residue sentence. Alternative: make the panel non-selectable and keep Copy as the only route (changes round 35's selectable-note decision — the practitioner's call). Not Accept: the natural gesture (select, Ctrl+C) silently bypasses the chosen mitigation.
  - **Watch items for the composer's run:** (1) the fakes now receive a real `QMimeData` from `_copy_note`; `mime.formats()` must be exactly `text/plain` plus the three `application/x-qt-windows-mime;value="…"` types on the offscreen platform (Qt stores them as given; no Windows conversion happens in the fake). (2) Nothing in the suite touches the real clipboard on the new path (every Copy test stubs `QApplication` in `ui.note`).
  - **Docs facts the reviewers should check against code** (load-bearing citations are on the 8.1 task line): the new "The Chrome extension" threat-model section and flow 20; the encounter record's three decrypt sites; the name-bearing `state` fields. One code-vs-doc contradiction was fixed in the docs, not the code: several docs still said the Chrome-driven verification was "unwired", that names were "shown nowhere", and that the pause rule acted only on pipe loss "until the Phase 6 extension" — all replaced with what the built bridge and extension do.
  - **MORNING LIVE CHECK — Task 8.2 (joins P.2; mock note only, never real patient text):**
    1. Turn on Windows clipboard history (Settings → System → Clipboard) if it is off, and press Win+V once to see what is listed.
    2. In `scribe-app`, generate, ratify and Save a MOCK note, then press the Note tab's **Copy** button.
    3. Paste into Notepad (Ctrl+V). *Expect:* the note text exactly as shown in the Note tab.
    4. Press Win+V. *Expect:* the copied note is NOT in the history list (an earlier item may be). Report PASS/FAIL per step; if it is listed, say whether you used the button or Ctrl+C.
  - **NEXT:** the composer runs `cd desktop && ../.venv/Scripts/pytest.exe -q` (expect 4022) and `cd extension && npm run qa && npm run build` (expect 295, build OK); relays the must-pause item to the practitioner; then `/review-loop` from round **45** over the Phase 8 diff (docs + the 8.2 hunks).
- **EXECUTOR HANDOFF (leg `stage-7-exec-g5`, 2026-09-28T03:49+10:00, run stage-7) — codex round 42 FIXED and closed, round 43 clean; history written; `reason=composer-run`.** Tasks 7.1–7.3 stay 🟨.
  - **Fixes.** PR-LOW-240: `app.py` gives the chord back in a `finally` if start-up fails after it is reserved. PR-LOW-241: `_on_hotkey_pressed` drops a press queued before detach.
  - **Checks.** ruff clean; mypy 49 files clean; extension typecheck and lint clean; no extension change.
  - **Expected suites.** Desktop **4017** passed (4014 + 3: `test_a_start_up_failure_after_attach_gives_the_chord_back` and `test_a_press_queued_before_detach_is_dropped[False|True]`). Extension **295** passed; `npm run build` OK.
  - **NEXT.** The scoped codex confirmation (round 44) over the two hunks; if it is clean, the composer closes the phase.
  - **Executor recommendation: surface=production.** The same no-`finally` shape remains for the Chrome pipe (`pipe.stop` only at `aboutToQuit`, `app.py:201`) and for the single-instance mutex handle. Both are released by Windows at process exit, and every thread is daemon, so a failed start cannot keep either alive. They were NOT folded into the same `finally`: `pipe.stop` joins its thread with a timeout, which would make the error path block, and the mutex has no release call today. My recommendation is Accept as named residue. Revisit only if start-up gains a non-daemon thread.
  - **MORNING LIVE SMOKE — Phase 7.** Run it AFTER the Phase 4, 5 and 6 smokes, with mock consultations and clinic 1 only, and never paste identifying data (names, note links, subdomains) into chat. Report pass/fail per step. Set-up: rebuild and reload the extension, fully restart Chrome, start `scribe-app` from Explorer, and open a clinic-1 mock patient's treatment note.
    1. **Hotkey.** Tick consent and Start from the side panel, then press **Ctrl+Shift+F9** from another window (e.g. Notepad). → The recording PAUSES; the desktop and the panel show the hotkey pause cue; there is no block. Press it again. → It RESUMES, and the status line says it resumed.
    2. **Refused Resume.** While recording, move the Cliniko tab to a DIFFERENT mock note. → The pause rule pauses the recording and the block shows. Press Ctrl+Shift+F9. → It stays paused, the desktop status line names the refusal, and the taskbar flashes. Go back to the recording's own note and press it again. → It resumes.
    3. **Chord held elsewhere.** Close `scribe-app` with no recording live. Start another program that takes Ctrl+Shift+F9 system-wide (any small hotkey tool; skip this step if none is to hand), then relaunch `scribe-app`. → The desktop status line and Session screen say the pause hotkey is unavailable, and the panel's Live layout says "Pause hotkey unavailable". Recording still works with the buttons. Close the other program afterwards.
    4. **Spoken pause.** While recording with live transcription running, the panel says `Say "scribe pause" to pause.` Say "…and prescribe, pause the tablets…" in a sentence. → Nothing pauses. Say "scribe pause" clearly, then stop talking. → Within a few seconds the recording PAUSES with the spoken-pause cue.
    5. **The phrase stays.** After Finish, the transcript still contains the words "scribe pause". Resume first and speak a little more before finishing, so the pause is not the last thing said.
    6. **"Unavailable" line.** On a normal recording, NO "Spoken pause unavailable" line shows while live transcription runs. If the Transcript screen ever reports that live transcription stopped or could not keep up, the line "Spoken pause unavailable for this recording - live transcription is off or has stopped." appears on the desktop, and the panel stops offering the phrase. Only observe this if it happens — don't force it.
    7. **New-consultation warning.** While recording, say "Thanks for coming in, see you next week", pause about 4 s, then say "Hello, take a seat". → Within a few seconds a new-consultation warning shows on the desktop status line (with a taskbar flash) and in the panel. The recording does NOT pause or block. Say it all again. → No second warning.
    8. **Reset.** Finish that recording and Start the next from a mock note. → No warning is shown for the new recording until the rule fires again.
  - **Interpretation calls for the practitioner** (each can be revised):
    - (a) The chord is **Ctrl+Shift+F9**: AltGr-safe (no Ctrl+Alt) and non-repeating. It clashes with Word's "Unlink fields" while `scribe-app` holds it (Word never sees the press). Changing it is one constant pair in `hotkey.py` plus the displayed text.
    - (b) The **one-second grace** after each Resume: "scribe pause" said within about the first second after a Resume is ignored, because up to one capture chunk of pre-Pause audio can still land after the Resume.
    - (c) The **3.0 s inter-word bound**: "scribe" and "pause" split across two transcript windows count as one phrase only when they start ≤3.0 s apart.
    - (d) **Refusals are desktop-only** for the hotkey: a refused hotkey Resume is named on the desktop (status line + flash), not in the panel's `last_refusal`, which stays for Chrome's own commands. The panel still shows the paused or blocked state.
- **EXECUTOR HANDOFF (leg `stage-7-exec-g4`, 2026-09-28T03:45+10:00, run stage-7) — LEG 1 verification of codex round 42 (pass stage-7.p1 slice A); no code changed.** Composer suites on the g3 tree: desktop 4014, extension 295, build OK. Round 42 stays Open (2 pending). PR-LOW-240: behavioral LOW, production, Fix-now as cheap hardening — the OS releases the chord at process exit and every thread is daemon, so there is no reachable leak; the fix is a `try/finally` detach around start-up and `app.exec()`, tested with a patched `main()`. PR-LOW-241: behavioral LOW, production, Fix-now — detach runs only outside RECORDING/PAUSED and posted events are delivered in order, so there is no reachable harm; the fix is a delivery-time "still reserved" check in `_on_hotkey_pressed`, tested with queue, detach, processEvents. Round 43 (slice B) is CLEAN; its history line is owed by the finishing seat of round 42. Cap verdict: accept. Tasks 7.1–7.3 stay 🟨.
- **EXECUTOR HANDOFF (leg `stage-7-exec-g3`, 2026-09-28T03:33+10:00, run stage-7) — `/review-loop` round 41 over the whole Phase 7 diff CONVERGED at round 1 of cap 3 (0 CRIT / 0 HIGH / 0 MED / 3 LOW, all applied); `reason=composer-run` because the round changed code and tests.** Tasks 7.1–7.3 stay 🟨. Fixes: LOW-033 (production) — `SpokenPauseDetector.feed` joins the carried word only when the next window's first word starts within `CARRY_MAX_GAP_SECONDS` (3.0 s, the window-closing silence), new test `test_a_silence_between_windows_breaks_the_phrase`; LOW-034 — `test_ui_bridge.py`'s spoken-pause test attaches a live transcriber first so the failure assertion discriminates; LOW-035 — the `WM_HOTKEY` child test now also POSTS the message through Qt's dispatcher (`SENT` then `SEEN` pinned). ruff clean, mypy 49 files clean; no extension change. **Composer: run `cd desktop && ../.venv/Scripts/pytest.exe -q` (expected 4014 passed = 4013 + 1) and `cd extension && npm run qa && npm run build` (expected 295, build OK).** On green, Phase 7 needs no further in-session round; NEXT is the composer-seat codex pass over the Phase 7 diff, then the morning live smoke (hotkey pause/resume + a refused resume, "scribe pause" while recording, the new-consultation warning, the side panel's hands-free lines) before phase-complete and the Phase 4–7 commits.
- **EXECUTOR HANDOFF (leg `stage-7-exec-g2`, 2026-09-28T03:23+10:00, run stage-7) — the g1 suite failure fixed in production code; `reason=composer-run`.** Tasks 7.1–7.3 stay 🟨.
  - Failure: `test_note.py::TestTokenisation::test_normalisation_has_exactly_one_implementation` found `def normalise_token` (as the prefix of g1's own `normalise_tokens`) in `voice_commands.py` — a second normaliser, which Task 1.2's pin forbids.
  - Fix (`voice_commands.py`): the tokeniser is now `phrase_tokens`, which only SPLITS a word (whitespace, hyphens, slashes) and passes every part to `note.normalise_token` — the one implementation — so no normalisation logic remains in the module. The pin is unchanged. Its second half (`_STRIP_PUNCT_RE`'s users = `note.py`, `transcription.py`) is unaffected: `voice_commands.py` never names it.
  - D7 behaviour is kept: "prescribe, pause", "scribe paused" and "scribes pause" still do not match; "Scribe, pause." and "scribe-pause" still do. One pinned case changed with the shared normaliser: a curly apostrophe inside a word is now kept as written (it was straightened in g1). No phrase in either list contains an apostrophe. The test case now pins `Don't` → `don't`.
  - Tests (`test_hands_free.py`): the import and `TestNormalise` renamed to `phrase_tokens`; a new spy test proves every part goes through `normalise_token`.
  - Checks in-leg: ruff clean; mypy 49 files, no issues; extension typecheck and lint clean (no extension change).
  - **Expected suites:** desktop **4013** = the g1 run's 4012 (4011 passed + the 1 failure, now passing) + 1 new test. Extension **295** (unchanged); `npm run build` unchanged.
  - NEXT: the composer runs the suites; then `/review-loop` from round **41**.
- **EXECUTOR HANDOFF (leg `stage-7-exec-g1`, 2026-09-28T03:17+10:00, run stage-7) — Phase 7 (hands-free and warnings) BUILT: Tasks 7.1, 7.2 and 7.3 🟨 awaiting the composer's suites; `reason=composer-run`.** Built on top of the uncommitted Phase 4–6 tree; nothing committed.
  - Landed (details under each task): new `desktop/src/scribe_desktop/hotkey.py` and `voice_commands.py`; `ui/main_window.py` (`_native_msg`, `nativeEvent`'s `WM_HOTKEY` branch via the queued `_hotkey_pressed_q`, `attach_hotkey` / `detach_hotkey` / `on_hotkey`, `_on_live_window`, `_on_session_resumed`, `_raise_new_consultation`, the detach in `closeEvent`); `ui/bridge.py` (`set_hotkey_status`, `set_new_consultation_warning`, `state.hotkey` / `spoken_pause` / `warnings`, the view fields); `ui/models.py` (hands-free and warning lines; `CHROME_HANDS_FREE_LINE` removed); `app.py` (attach after the Chrome link, detach at quit); extension `panel-view.ts` / `panel.ts` (the Live layout's hotkey and spoken-pause lines). No protocol, fixture, dependency or env-var change.
  - Checks in-leg: `ruff check .` clean; mypy **49** source files, no issues (47 + `hotkey.py` + `voice_commands.py`); extension `npm run typecheck` and `npm run lint` clean.
  - **Expected suites:** desktop **4012** = 3922 + 90 (`test_hands_free.py` +76: hotkey module 7, normalise 7, matcher 21, availability 9, warning rule 11, window hotkey 12 including the Windows real-dispatch child, window phrase rules 9; `test_ui_models.py` +8; `test_ui_bridge.py` `TestHandsFree` +6). Extension **295** = 292 + 3 (`panel-view.test.ts` +2, `panel.dom.test.ts` +1). `npm run build` unchanged in shape.
  - Watch items for the composer's run: (1) the real-dispatch child `test_a_real_wm_hotkey_through_qts_dispatch` (Windows, integration) sends a synthetic `WM_HOTKEY` through Qt's windows platform — the same path the suspend child proved; (2) `FakeController` gained `live_transcription_attached = False`, so a fake recording now reads "Spoken pause unavailable"; (3) `test_ui_models.py`'s `test_the_link_line_leads_and_hands_free_follows` now pins the two new lines.
  - **Interpretation calls for the practitioner** (each applied, LOW, revisable — answer yes or say what you want instead):
    1. The chord is **Ctrl+Shift+F9**: no Ctrl+Alt (AltGr on European layouts), no Alt+Shift (switches keyboard layout), no Win key (Windows' own). Chrome and Cliniko use nothing on it. While the app runs it is taken from every program; Word's Ctrl+Shift+F9 ("unlink field") is the known clash. On a laptop whose F-keys default to media keys it may need Fn.
    2. A hotkey Resume that the guard refuses is shown on the DESKTOP (status line, Session screen, taskbar flash) — not as `state.last_refusal`; the panel's Blocked/Paused layout already explains the state.
    3. `state.hotkey.available: false` covers both "not reserved" and "refused" (no protocol change); the panel says "Pause hotkey unavailable — see Clinic Scribe's Session tab" and the desktop names the refusal.
    4. The matcher needs whole words on BOTH sides ("scribe paused" and "scribes pause" do not match; "scribe-pause" and "Scribe, pause." do) and finds a phrase split across two windows through one carried word.
    5. The resume cutoff is the captured audio at the Resume plus ONE capture chunk (1 s), because the capture worker can still hold up to a chunk of pre-Pause audio then; a phrase begun within about a second of a Resume is ignored.
    6. `state.spoken_pause` is true only while a recording or paused session has a running live transcriber; with no recording the desktop reads 'say "scribe pause" while recording to pause'.
    7. The warning is raised ONCE per recording, kept while that recording is recording or paused, and dropped when it finishes; the desktop also flashes the taskbar. A greeting in the same window counts only AFTER the closing phrase. The lists: closings "see you next week / next time / soon / then", "take care", "all the best", "goodbye", "bye", "thanks / thank you for coming in", "have a good / nice / great day", "have a good weekend"; greetings "hello", "hi there", "good morning / afternoon / evening", "nice to meet you", "come on in", "take / have a seat", "what brings you in / here", "how have you been".
    8. The panel shows the hands-free lines only in the Live layout while recording or paused.
  - Residue named in the threat model (not controls): the hotkey is a global input (anyone at the keyboard, or a same-user program sending `WM_HOTKEY`) and does only what the Pause / guarded Resume buttons do; the phrase is heard from anyone in the room and can only pause; the warning is a heuristic cue.
  - NEXT: the composer runs the suites; then `/review-loop` from round **41** over the Phase 7 diff; the codex pass is composer-seat. The morning live-smoke checklist for Phase 7 comes with the phase-complete handoff (after the Phase 4, 5 and 6 smokes).
- **EXECUTOR HANDOFF (leg `stage-6-exec-f9`, 2026-09-28T02:54+10:00, run stage-6) — Phase 6 (Chrome extension UI) BUILD-COMPLETE and REVIEW-CONVERGED; `reason=phase-complete`; gate = the practitioner's live-user smoke below, after the Phase 4 and Phase 5 smokes.** Tasks 6.0–6.5 stay 🟨 until that smoke passes (the composer records 🟩).
  - Last leg: PR-LOW-230 fixed. `extension/src/sinks.test.ts`'s header now separates BARE-NAME rules from PREFIX-DEPENDENT ones, names the residue as a class and cites lint's `@typescript-eslint/no-implied-eval` (via `recommendedTypeChecked`); 2 fixtures; matcher unchanged. Round 40 Closed.
  - Checks in-leg: extension typecheck and lint clean; no desktop change this phase (ruff/mypy baselines stand).
  - **Final expected suites:** desktop **3922**; extension **292** = 290 + 2. `npm run build` unchanged in shape.
  - Phase 6 review record:
    - in-session `/review-loop` round 36: 5 LOW, all applied;
    - codex pass `stage-6.p1`: rounds 37–38, 1 MED + 5 LOW → round 39, 1 LOW → round 40, 1 LOW;
    - accept-closed at peer round 4 of 6 on the executor's cap verdict (the last two rounds were header accuracy in a test-harness guard);
    - every finding fixed, none deferred or accepted.
  - Open for the practitioner: Task P.1 for clinic 2; the interpretation calls below; the Phase 4 and 5 `[decision]` tasks 4.3 and 5.4 and their smokes.
  - **MORNING LIVE SMOKE — Phase 6, run AFTER the Phase 4 and Phase 5 smokes pass.**
    - Ground rules: mock consultations only (a made-up conversation, no real patient), clinic 1 only, on two draft treatment notes made for testing under two mock patients (call them A and B). Never paste anything identifying into chat: report the step number, PASS or FAIL, and any on-screen text with names, ids and the clinic's address blanked.
    1. **Build, restart, badge.** Run `cd extension && npm run build`. Reload the unpacked extension in `chrome://extensions`. Fully quit Chrome and check Task Manager shows no `chrome.exe`, then reopen Chrome. Double-click `.venv\Scripts\scribe-app.exe`, then click the pinned icon. *Expect:* the side panel opens; the badge is green **OK**; the panel says "Open a patient's treatment note to record". Close the app. *Expect:* grey **OFF**; the panel says "Clinic Scribe is not running — open it to record" with "If it is open, another Chrome profile may be connected to it." underneath. Relaunch the app: **OK** again.
    2. **Ready and the consent box.** Open A's note. *Expect:* "Checking with Cliniko…", then:
       - A's name, the appointment (or "No linked appointment") and the clinic;
       - "Note verified with Cliniko. It is checked again before anything is written back.";
       - an UNticked box reading "I confirm the patient has consented to AI-assisted recording and documentation";
       - Start greyed until the box is ticked.
       Tick the box, switch to a non-Cliniko tab, then come back. *Expect:* the panel showed "Open a patient's treatment note to record" while away, and the box is UNticked again on return.
    3. **Linked Start, Pause and Resume from the panel.** Tick the box, press Start and speak a few sentences. *Expect:* a thin red frame round the Cliniko page; badge **REC**; the panel reads "Recording" with a counting timer and "Consent confirmed <time>"; the box is unticked. Press Pause. *Expect:* amber frame, **PAUSED**, "Paused". Press Resume. *Expect:* red again, **REC**.
    4. **A patient change pauses and blocks.** In the SAME tab, open B's note. *Expect:*
       - the frame turns amber and a full-page card says "This tab opened a different treatment note.";
       - the card names A as the recording's patient and B as this tab's, with Resume previous / Finish previous / Discard previous;
       - badge **PAUSED**; the panel shows the same block;
       - the desktop shows its pause cue.
       Say whether the amber badge is legible.
    5. **Resume previous.** Click Resume previous on the card. *Expect:* the tab goes back to A's note, and within a few seconds recording resumes (red frame, **REC**, card gone). No other tab moves.
    6. **Chrome closing mid-recording.** Quit Chrome fully (no `chrome.exe` left). *Expect:* the desktop shows the recording paused. Reopen Chrome and open B's note. *Expect:* the amber card on B's page. Resume previous takes you back to A and resumes.
    7. **Discard takes two clicks.** Open B's note again. On the card, click Discard previous once. *Expect:* "Confirm discard" and "Discard this recording? This cannot be undone. Press Confirm discard to delete it."; after 15 s it reverts. Now click twice. *Expect:* the recording is discarded, the frame goes, and the panel shows B's Ready with the box unticked.
    8. **Finish and the Unreviewed banner.** On A's note, tick, Start, speak, then press Finish consultation. *Expect:* "Finishing <A>…" with NO timer, then Ready with "The last recording is waiting for review in Clinic Scribe." Close the app (twice within 10 s, as the desktop asks), relaunch it, and reload A's note. *Expect:* the panel's banner "Unreviewed recording for this note — Open for review". Pressing it brings that recording's review up in the app. Complete or discard it there.
    9. **Extension reload mid-recording.** On A's note, Start a new recording from the panel. Reload the extension in `chrome://extensions` and return to the Cliniko tab. *Expect:* the panel briefly says "Restoring the safeguards on this tab…" or "Connecting to Clinic Scribe…", then the recording shows paused with the amber card. Resume previous resumes it.
    10. **Lost link under a recording.** With that recording running, end Cliniko Scribe in Task Manager. *Expect:*
        - within a few seconds the badge reads red **!**;
        - the panel says "Clinic Scribe is not running — open it to record";
        - the frame disappears (the app is gone, so nothing records).
        Relaunch the app. *Expect:* badge **OK**; the Recovery tab lists the recording as recoverable. Discard it, then close the app normally. *Expect:* **OFF**.
    - If a step fails, get back to a working state this way (never a git command):
      - discard the mock recording in the app (Session, Transcript or Recovery tab → Discard);
      - if Chrome shows **ERR** or nothing changes, rebuild, reload the extension and fully restart Chrome;
      - report the step and the text.
  - **Interpretation calls and open questions for the practitioner** (each applied as described and revisable — answer yes, or say what you want instead):
    1. The Cliniko sign-in page is recognised by the PATH `/users/sign_in`. This is UNVERIFIED on a live account. If convenient, sign out once and report only the path. Any other path reads as "another Cliniko page", and the recording's tab leaving its note pauses it either way.
    2. The badge shows green **OK** while the app runs idle (D1 said nothing) and grey **OFF** when it is closed; red **!** means the link dropped under a live recording.
    3. "Resume previous" first brings forward a tab already showing the note. Otherwise it navigates only a tab on an allow-listed Cliniko page, and anything else opens the note in a new tab.
    4. With the link to the app down, Cliniko tabs keep an amber frame if a recording was live, and the block's card is dropped, because its buttons could not reach the app. With the app closed, nothing is drawn.
    5. The side panel has no Discard while recording (D1 lists Pause/Resume and Finish consultation). Discard stays on the desktop and on the block.
    6. The panel's banner shows only over the Message and Ready layouts, and only while a Cliniko tab is in front.
    7. D1's "Another Chrome profile is connected" has no signal, so the not-running message carries a hint instead.
    8. The page script's cue can be hidden or covered by Cliniko's own page. The heartbeat only puts back a removed element, and a per-heartbeat `important` restyle was considered and NOT applied, because the hiding routes are an open class. The app's pause rule and command checks are the enforcing controls.
    9. For Task 8.1 (detectability): the build tool (crxjs) adds a `web_accessible_resources` entry for the page-script module on Cliniko hosts (`use_dynamic_url: false`). A Cliniko page could therefore detect that the extension is installed. The file carries no data.
    10. `sidePanel.open()` was not needed and not tried live: the toolbar icon opens the panel via `setPanelBehavior`.
- **EXECUTOR HANDOFF (leg `stage-6-exec-f8`, 2026-09-28T02:52+10:00, run stage-6) — LEG 1 verification of codex round 40; no code changed; `reason=phase-complete`.**
  - PR-LOW-230 verified docs-only/low/test-harness; shape: narrow the header, name the residue as a class, cite lint's `no-implied-eval`; no block-comment strip.
  - **Cap verdict: accept** (no round 41).
- **EXECUTOR HANDOFF (leg `stage-6-exec-f7`, 2026-09-28T02:47+10:00, run stage-6) — LEG 2 `/fix` of codex round 39: PR-LOW-220 fixed (test-only); round 39 Closed; `reason=composer-run`.**
  - `sinks.test.ts`: bare-token bans for `write`/`writeln`/`eval`/`Function`, a `constructor` access ban, 5 detection fixtures, class declarations proven unflagged. Extension 290.
  - The morning smoke and the open questions written in this leg now sit in the f9 bullet above.
- **EXECUTOR HANDOFF (leg `stage-6-exec-f6`, 2026-09-28T02:44+10:00, run stage-6) — LEG 1 verification of codex round 39; no code changed; `reason=phase-complete`.**
  - Round 39 confirmed PR-MED-200, PR-LOW-201, PR-LOW-202, PR-LOW-211 and PR-LOW-212.
  - PR-LOW-220 is verified behavioral/low/test-harness: the sink scan misses the destructured `write` and the aliased `Function`, and no production file uses either.
  - Chosen shape: match the listed names as bare tokens (`write`/`writeln`/`Function`, plus property access to `constructor`), narrow the header to that class, and name the remaining gaps.
  - **Cap verdict: accept.** Round 39 stays Open. NEXT: LEG 2 `/fix`.
- **EXECUTOR HANDOFF (leg `stage-6-exec-f5`, 2026-09-28T02:35+10:00, run stage-6) — LEG 2 `/fix` of codex rounds 37–38: all six findings fixed; both rounds Closed; `reason=composer-run`.** Tasks 6.0–6.5 stay 🟨: the scoped codex confirmation (round 39) follows.
  - Round 37:
    - PR-MED-200: `extension/src/hub.ts` — event counter (`events`/`touched`/`activated`, `bump`), `resync` asks again when overtaken (3 tries, then inert until the next event), every `getTab` answer through `lookUp`, and the unknown-tab hello uses Chrome's URL.
    - PR-LOW-201: `connection.ts` `badgeFor` shows "!" until the new link's first snapshot.
    - PR-LOW-202: `manifest.test.ts` asserts the literal host pattern.
  - Round 38:
    - PR-LOW-210: `sinks.test.ts` token-level scan, wider file types, detection fixtures, lexical-guard residue.
    - PR-LOW-211: `Object.hasOwn` in `panel-view.ts` `lookUp` and `page.ts` `reasonText`.
    - PR-LOW-212: the page-cue residue restated as a class (Task 6.3, `page.ts` header, CHANGELOG); the `important` restyle was not applied.
  - Checks in-leg: extension typecheck and lint clean; no desktop change (ruff/mypy baselines stand).
  - **Expected suites:** desktop **3922**; extension **285** = 255 + 30 (`hub.test.ts` +8, `connection.test.ts` +1 row, `panel-view.test.ts` +3, `page.dom.test.ts` +1, `sinks.test.ts` +17: 22 tests replacing 5). `npm run build` unchanged in shape.
- **EXECUTOR HANDOFF (leg `stage-6-exec-f4`, 2026-09-28T02:25+10:00, run stage-6) — LEG 1 verification of codex rounds 37–38 (pass `stage-6.p1`); no code changed; `reason=phase-complete`.**
  - Round 37: PR-MED-200 behavioral/med/production (a stale async tab read can re-bind the unbound linked session and satisfy the resume check after a reconnect; 4 sites in `hub.ts`); PR-LOW-201 behavioral/low/production; PR-LOW-202 behavioral/low/test-harness. **Cap verdict: raise +1.**
  - Round 38: PR-LOW-210 behavioral/low/test-harness; PR-LOW-211 behavioral/low/production; PR-LOW-212 docs-only/low/docs. **Cap verdict: accept** (its fixes fold into round 37's confirmation round).
  - Both rounds stay Open. NEXT: LEG 2 `/fix` to the fix shapes and regression tests recorded under each round's LEG 1 block.
- **EXECUTOR HANDOFF (leg `stage-6-exec-f3`, 2026-09-28T02:10+10:00, run stage-6) — `/review-loop` round 36 over the whole Phase 6 diff: 0 CRIT / 0 HIGH / 0 MED / 5 LOW, all applied; `reason=composer-run`.** Tasks 6.0–6.5 stay 🟨.
  - Fixes (details in the Findings Log, round 36): `connection.ts` `badgeFor` — "!" outranks ERR under a live session (LOW-028); `panel-view.ts` `panelModel` — the banner only while a Cliniko tab is in front (LOW-029); `hub.ts` `goToRecordingNote` — the fallback navigates only a tab on an allow-listed Cliniko page, else opens a new tab (LOW-030); `context.ts` `tabUpdated` — a redundant line removed (LOW-031); new `sinks.test.ts` pins text-only rendering, no browser storage, no dynamic code and the one console call (LOW-032).
  - Checks in-leg: extension typecheck and lint clean; no desktop change (ruff/mypy baselines stand).
  - **Expected suites:** desktop **3922**; extension **255** = 247 + 8 (badge row 1, banner test 1, hub test 1, `sinks.test.ts` 5). `npm run build` unchanged in shape.
  - WATCH: `sinks.test.ts` reads the source tree with `readdirSync` from its own directory (as `protocol.test.ts` reads the fixtures); if a file list assertion fails, check for CRLF or a renamed file first.
  - Next: round 37 (`/review-loop` round 2 of cap 3, the post-fix regression check) once the suites are green; converged there → `phase-complete` for the codex pass.
- **EXECUTOR HANDOFF (leg `stage-6-exec-f2`, 2026-09-28T01:59+10:00, run stage-6) — Phase 6 Tasks 6.3–6.5 BUILT; all of 6.0–6.5 are 🟨; `reason=composer-run`.** f1's tree passed the composer's run (desktop 3922, extension 198, build OK). No desktop file changed in f2.
  - What landed (details on each task line): `extension/src/page.ts` (6.3, `PageScript`); `extension/src/panel-view.ts` (6.4, `panelModel` — the layout choice) + `panel.ts` (`Panel` — drawing, the port, commands) + `panel.html` (stylesheet); `hub.ts` `PanelView.focus` gains `tab_id` so Ready shows only for the note in front of the practitioner (`hub.test.ts`'s three focus expectations updated); 6.5's one missing class, "no key in any payload", added to `background.test.ts`. The 6.4 spike is recorded on its task line (not needed: the icon opens the panel through `setPanelBehavior`; nothing calls `sidePanel.open()`).
  - Checks in-leg: extension typecheck and lint clean; ruff "All checks passed!"; mypy "no issues found in 47 source files".
  - **Expected suites:** desktop **3922** (unchanged). Extension **247** = 198 + 49: `page.dom.test.ts` 12, `panel-view.test.ts` 26, `panel.dom.test.ts` 10, `background.test.ts` +1. `npm run build` must emit the panel page (now with the model and its stylesheet) and the page-script loader.
  - WATCH (first run): `page.dom.test.ts` and `panel.dom.test.ts` import their module per test after `vi.resetModules()` (both boot at import); two tests use `vi.useFakeTimers()` (Discard's 15 s disarm, the panel's 1 s reconnect) — the fake's ports deliver by `queueMicrotask`, which fake timers leave alone. jsdom events from `click()` are untrusted by design; the trusted path injects `isTrusted`.
  - Interpretation calls this leg: five for the panel (6.4's task line) and the page-script residue (6.3's task line). None is CRIT/HIGH or production-impacting beyond the planned UI; no Defer/Accept.
  - Next: `/review-loop` from round **36** over the whole Phase 6 diff (`extension/` + AGENTS.md + CHANGELOG), then the composer's codex pass; then my phase-complete handoff with the final smoke.
  - **DRAFT MORNING SMOKE — Phase 6, AFTER the Phase 4 and Phase 5 smokes** (finalised at phase-complete). Mock consultations only, clinic 1 only, on a draft treatment note made for testing; report step number + PASS/FAIL and on-screen text with names and ids blanked. First: `cd extension && npm run build`, reload the extension in `chrome://extensions`, fully restart Chrome (no `chrome.exe` left), then double-click `scribe-app.exe`.
    1. **Icon and panel.** Click the pinned icon. *Expect:* the side panel opens; the badge is green **OK**; the panel says "Open a patient's treatment note to record". Close the app: badge grey **OFF**, panel "Clinic Scribe is not running — open it to record". Relaunch the app: **OK** again.
    2. **Ready.** Open the test note in Cliniko. *Expect:* "Checking with Cliniko…", then the patient's name, the appointment (or "No linked appointment"), the clinic, "Note verified with Cliniko…", an UNticked consent box and a greyed Start.
    3. **Linked Start.** Tick the box, press Start, speak a few sentences. *Expect:* a thin red frame round the Cliniko page, badge **REC**, the panel's timer counting and "Consent confirmed <time>"; the box is unticked again.
    4. **Patient change pauses.** In the same tab, open a different patient's note. *Expect:* the frame turns amber, a full-page card names both patients with Resume previous / Finish previous / Discard previous, the badge reads **PAUSED** (say whether it is legible), the desktop shows its pause cue.
    5. **Resume previous.** Click Resume previous on the card. *Expect:* the tab goes back to the first note and, within a few seconds, recording resumes (red frame, **REC**, card gone).
    6. **Chrome closing mid-recording.** Quit Chrome fully. *Expect:* the app shows the recording paused. Reopen Chrome and the other patient's note. *Expect:* the amber card on that page; Resume previous takes you back and resumes.
    7. **Discard takes two clicks.** Open the other note again, then on the card click Discard previous once. *Expect:* "Confirm discard" and a warning line; wait 15 s and it reverts. Click twice. *Expect:* the recording is discarded, the frame goes, the panel shows Ready with the box unticked.
    8. **Finish and the reminder.** Start again, speak, press Finish consultation. *Expect:* "Finishing <name>…" with no timer, then Ready with "The last recording is waiting for review in Clinic Scribe." Close the app (twice within 10 s), relaunch it, and reload the note. *Expect:* the panel's banner "Unreviewed recording for this note — Open for review"; pressing it brings the recording's review up in the app.
    9. **Extension reload mid-recording.** Complete or discard the step-8 recording in the app; Start a new one from the panel, then reload the extension in `chrome://extensions` and return to the Cliniko tab. *Expect:* the panel briefly says "Restoring the safeguards on this tab…" or "Connecting…", the recording is paused with the amber card; Resume previous resumes it. Then Finish or discard it in the app.
    10. **Only if convenient:** sign out of Cliniko and say what the sign-in page's PATH is (for example `/users/sign_in` — no clinic name). The extension assumes that path for the login page.
- **EXECUTOR HANDOFF (leg `stage-6-exec-f1`, 2026-09-28T01:43+10:00, run stage-6) — Phase 6 Tasks 6.0–6.2 BUILT; `reason=composer-run`.** Built on the uncommitted Phase 4 + 5 tree; no desktop file changed.
  - Last completed: 6.0 (Vitest `node` + `dom` projects in the new `extension/vitest.config.ts`; `src/test/chrome-fake.ts`; jsdom 30.1.1 installed by the composer under the practitioner's 2026-09-27 21:39 authorisation), 6.1 (manifest + pin test; stubs `page.ts`, `panel.html`, `panel.ts`), 6.2 (`context.ts`, `hub.ts`, `connection.ts`, `background.ts`). All three 🟨 with BUILT notes on the task lines; 6.2's six interpretation calls are listed there.
  - Checks run in-leg: `npm run typecheck` clean, `npm run lint` clean. No Python changed (ruff/mypy baselines stand: clean, 47 files).
  - **Expected suites:** desktop **3922** (unchanged). Extension **198** = 105 + 93: `manifest.test.ts` 5; `connection.test.ts` +18 (handshake hook 1, `appState` 1, badge table 12, "!" flow 1, `send` 3; the handshake test now expects "…" until the first `state`, then OK); `context.test.ts` 36; `hub.test.ts` 28; `background.test.ts` 4; `test/chrome-fake.dom.test.ts` 2 (the `dom` project's first files — it proves jsdom is active).
  - **`npm run build` must pass:** crxjs has to emit the side panel page and the page-script loader. WATCH: the built `manifest.json`'s `content_scripts[0].js` is what `Hub.installed` re-injects (read at run time via `chrome.runtime.getManifest()`); if crxjs writes a loader there, that is the right file.
  - WATCH (first vitest run): `vitest.config.ts` now takes precedence over `vite.config.ts` for tests (the crx plugin no longer loads under test); if a project reports "no test files", check the two `include` globs. `background.test.ts` boots the worker with `vi.resetModules()` + dynamic import per test.
  - **Composer note — Phase 4 morning smoke on THIS build:** if the practitioner rebuilds the extension from this tree for the Phase 4 smoke, step 5's expectation changes: with the app closed the badge now reads grey **OFF**, not **OK** (the Phase 4 recommendation, applied). Steps 3–4 (app first, then Chrome → green **OK**) are unchanged. The page script and the panel are still stubs, so nothing new appears on Cliniko pages yet.
  - Next (leg f2): 6.3 (page script: frame, block, href heartbeat — the hub's `ToPage` / `FromPage` messages and `PageSlice` / `PageBlock` in `context.ts` are the contract), 6.4 (panel: layouts from `PanelView` — `connection`, the app's `state`, and `focus.kind` `none | not_cliniko | clinic_not_set_up | cliniko` with `restoring`; port name `PANEL_PORT`; commands as `PanelCommand` in `hub.ts`; the `sidePanel.open()` spike recorded from the API types — "may only be called in response to a user action"; the icon already opens the panel through `setPanelBehavior`), 6.5 (remaining classes: layouts, the markup-name fixture, `isTrusted`).
  - Open, for the panel leg: D1's "Another Chrome profile is connected to Clinic Scribe" has no protocol signal (the host pushes `app_running:false` whenever the pipe is absent or held), so the panel can only say the app is not running and add that another Chrome profile may be connected — an interpretation to record in 6.4.
- **EXECUTOR HANDOFF (leg `stage-5-exec-e7`, 2026-09-28T01:21+10:00, run stage-5) — Phase 5 BUILD-COMPLETE and CONVERGED; `reason=phase-complete`.**
  - State:
    - Tasks 5.1–5.6 are 🟩: suites 3922 + 105; in-session `/review-loop` round 32; codex pass stage-5.p1 rounds 33–35, converged at peer_round 3 of 5. Overall Progress `59%` (24 of 41).
    - Task 5.4 was decided (a) under the overnight pre-authorisation and is revisable.
    - Phases 4 AND 5 are both UNCOMMITTED. Each commit waits for its own live-user smoke: Phase 4's first, then this one.
  - **For the composer's `/document`** (AGENTS.md Current Status + Subsystem pointers):
    - Status: Phase 5 built:
      - the D5 pause rule (`context_rules.py`: `pause_action`, `ContextEvaluator`; the sleep handler in `MainWindow.nativeEvent`, which never raises into Qt; unlinked recordings pause only on sleep);
      - the resolution block and `resume_previous`;
      - the Session screen's two-click Discard;
      - back-to-back Start at QUEUED, gated by the review lease;
      - the Unreviewed review via `SessionController.adopt_queued` (5.4 (a), revisable), with the saved note read-only plus "Regenerate (replaces the saved note)";
      - the reminder index, rebuilt at start by one `encounter.enc` decrypt per session, `state.banner` and `open_review`;
      - the 2-hour expiry warning and the on-close list.

      Suites 3922 + 105; rounds 32–35.
    - New subsystem pointer: "If working on the pause rule, the resolution block or back-to-back (`context_rules.py`, the pause and resume parts of `ui/bridge.py`, `MainWindow.nativeEvent` / `pause_for`), or on the Unreviewed review (`SessionController.adopt_queued`, the Recovery screen's Unreviewed section, `MainWindow._on_review_requested` / `_open_adopted` / `open_unreviewed` / `reconstruct_reminders`, the reminder index), read plan D5/D6, Task 5.4's decision brief (its 15 custody consumers), the threat model's PAUSE RULE and OPEN FOR REVIEW paragraphs, flows 6 and 19, and the retention schedule's 24-hour rule."
    - Constraint 7's start-up exception (one `encounter.enc` decrypt per Unreviewed session, to rebuild the index) belongs beside the existing Cliniko-client pointer's text.
  - Executor recommendations for Phase 6+:
    1. The side panel must render every Phase 5 field it is handed: `state.block` on every tab of the block's own clinic host, `banner` with its count, the "Resume previous" navigation from `state.live`'s ids plus the allow-list, and plain copy for the refusal codes `session_active`, `review_in_progress`, `cannot_open`, `pipe_down` and `report_mismatch`. surface=production
    2. The adopted (reopened) session's `recorded_seconds` reads 0, because its store closed at the Finish that produced it. Phase 6 should show no timer for `phase: "queued"`, or the app should carry the count from the store's chunk count. surface=production
    3. After Regenerate → "Cancel review" on a reopened saved note, the saved note stays on disk but is no longer shown. This is the same as today's post-Save Regenerate → Cancel on a live session; consider re-showing it. surface=production
    4. The on-close list refuses the first close, and so it refuses a Windows shutdown or logoff once (a documented residue). Consider handling `WM_QUERYENDSESSION` / `aboutToQuit` so a shutdown is not held. surface=production
  - **PHASE 5 LIVE-USER SMOKE — for the practitioner, in the MORNING, AFTER the Phase 4 smoke.**
    - Ground rules: mock consultations only (a made-up conversation, no real patient); clinic 1 alone; never paste anything identifying into chat — report only the step number, PASS or FAIL, and any message text with names or ids blanked. Launch `scribe-app.exe` by double-click. Mark PASS or FAIL per step.
    1. **Sleep pauses a recording.** Session tab: tick consent, Start, speak a few sentences. Put the PC to sleep (Start → Power → Sleep), wake it and unlock. *Expect:* the session state reads `paused`; the status line and the Session tab say "Paused - the computer went to sleep. Press Resume to carry on recording."; the taskbar icon flashes; the window responds normally, with no error dialogs. Press Resume: recording continues.
    2. **Discard takes two clicks.** In the same recording, click Discard once. *Expect:* the button now reads "Confirm discard" and a line asks you to confirm. Wait about 15 seconds. *Expect:* the button goes back to "Discard" and nothing was deleted. Click Discard twice in a row. *Expect:* "Session discarded (audio cryptographically deleted)."
    3. **Back-to-back (A then B).** Record mock A and press Finish. *Expect:* "Start" stays greyed while A is transcribing; when A's transcript appears, "Start" is offered again once consent is ticked. Generate a note for A and Save it. Now tick consent and Start mock B. *Expect:* B is recording, and the Note tab no longer shows A's note. Press Finish on B and wait for its transcript.
    4. **Reopen A's saved note.** Recovery tab. *Expect:* A appears under "Unreviewed recordings" marked "note saved", with "Open for review" and "Discard" — and NO "Resume processing" for it. Select A and press Open for review. *Expect:* the Note tab shows A's note exactly as saved, read-only (no edit or Save), with Copy available. The Transcript tab's button reads "Regenerate (replaces the saved note)". B moves to the Unreviewed list. Press Complete on the Transcript tab. *Expect:* A is completed and leaves every list.
    5. **Reopen B, which has no note.** Recovery tab → select B → Open for review. *Expect:* B's transcript opens with "Generate note" offered. Leave it open, not completed.
    6. **A crashed recording keeps its warning.** Discard B (Transcript tab → Discard). Start mock C, speak a little, then end the app from Task Manager (select Cliniko Scribe → End task). Relaunch it. *Expect:* the Recovery tab lists C under "Recoverable sessions" with "did not finish cleanly". Press Resume processing. *Expect:* C's transcript opens with the red "Warning: recording did not finish cleanly; the tail may be missing." Do NOT complete it.
    7. **Closing with an unreviewed recording.** Close the window. *Expect:* it stays open; the status line and the Recovery tab list "Recording xxxxxxxx...: expires HH:MM" (8 characters, a time about 24 h after C began) and say "Close again within 10 seconds to quit." Close again at once. *Expect:* the app quits. Relaunch. *Expect:* C is now under "Unreviewed recordings" with "did not finish cleanly". Open it for review. *Expect:* the same red warning on the Transcript tab.
    8. **Clean up.** Discard C (Transcript tab → Discard), then Discard any other mock row left on the Recovery tab. *Expect:* both lists are empty and the window closes on the first try.
    - Cannot be tested until the Phase 6 side panel exists (Chrome shows nothing new yet):
      - pauses on a note or patient change in Cliniko, another note or the login page, and Chrome disconnecting or reconnecting;
      - the full-page block, "Resume previous", "Finish previous" and "Discard previous";
      - the "unreviewed recording" banner on reopening a note, and Open for review from Chrome;
      - a linked Start from the panel.
    - Please CONFIRM three interpretation calls while testing (answer yes, or say what you want instead):
      - (5.1) a desktop-started (unlinked) recording pauses only when the PC sleeps — never on anything Chrome does;
      - (5.3) starting the next recording clears the previous patient's saved note from the Note tab (it stays reopenable from the Unreviewed list);
      - (5.4, the D6 reading) a reopened saved note is read-only, and "Regenerate" replaces it only when that new review is Saved.
    - If a step fails, get back to a working state this way (never a git command):
      - discard the mock recording (Session or Transcript tab → Discard, or the Recovery tab row → Discard);
      - if the window will not close, finish or discard what the status line names;
      - as a last resort, Task Manager → End task is safe: crash recovery keeps everything, and the next launch lists it on the Recovery tab.

      Then relaunch `scribe-app.exe` and report the step number with the on-screen message (names and ids blanked).
- **EXECUTOR HANDOFF (leg `stage-5-exec-e6`, 2026-09-28T01:11+10:00, run stage-5): LEG 2 `/fix` of codex rounds 33–34, all four applied; both rounds Closed with their Review History lines; `reason=composer-run`.**
  - What landed:
    - PR-LOW-180: the reorder in `test_cross_patient.py::test_a_second_pipe_client_pauses_and_must_report_the_note_first`.
    - PR-MED-190, three sites:
      - `ui/main_window.py` `_open_adopted(..., store_finished=)`, fed by `_on_review_requested`;
      - `ui/models.py` `unreviewed_row_text`, which now carries the "no audio recorded" / "did not finish cleanly" tail;
      - `ui/recovery.py` `_update_controls`, which warns for either list's selection.
    - PR-MED-190 tests: `test_unreviewed_review.py`'s `_unreviewed` helper now writes a real audio store (sealed by default), plus 3 new tests.
    - PR-LOW-191: the threat model, CHANGELOG and the `context_rules.py` docstring.
    - PR-LOW-192: the threat model and the retention schedule.
  - **Expected counts:** desktop **3922** = 3919 + 3 (the unfinished/finished parametrised pair and the Chrome-route test). Extension **105**, unchanged. Ruff clean, mypy 47 files, extension typecheck and lint clean.
  - WATCH: every `_unreviewed` session now has an `audio.enc`. If a TestAdoptQueued / TestReconstruction / cross-patient positive case fails on the first run, check the store helper first.
  - Tasks stay 🟨; the scoped codex confirmation (round 35) follows.
- **EXECUTOR HANDOFF (leg `stage-5-exec-e5`, 2026-09-28T01:07+10:00, run stage-5): LEG 1 verification of codex rounds 33–34 (pass stage-5.p1) — all 4 findings CONFIRMED; nothing changed but the plan's records; `reason=phase-complete`.** The tuples:
  - PR-LOW-180: test-harness low; the old-client Resume row is vacuous, and the production guard is present.
  - PR-MED-190: regression med; the adoption hides the unfinished-store warning. The class check found a second site: the Unreviewed row text and selection.
  - PR-LOW-191: docs low; siblings are `CHANGELOG.md:37` and the `context_rules.py` docstring.
  - PR-LOW-192: docs low; the retention-schedule sibling.

  Cap verdicts: round 33 accept; round 34 raise +1. Both rounds stay Open (4 pending) for the `/fix` leg. The fix shapes and regression tests are under each round's LEG 1 block.
- **EXECUTOR HANDOFF (leg `stage-5-exec-e4`, 2026-09-28T00:53+10:00, run stage-5): `/review-loop` round 32 over the whole Phase 5 diff found 0 CRIT / 0 HIGH / 0 MED / 5 LOW, all applied; `reason=composer-run`.** The loop converged on findings (no CRIT/HIGH/MED), but the fixes changed code and tests, so the suites have to pass on this tree before `phase-complete`. Tasks 5.1–5.6 stay 🟨 (the codex pass follows). Overall Progress stays at 44%.
  - The five fixes (details in the Findings Log, round 32):
    - LOW-023: `open_review` refuses `session_active` before the window moves;
    - LOW-024: the Chrome route honours the Recovery screen's resume-in-flight block;
    - LOW-025: `saved_note_line` never raises after an adoption;
    - LOW-026: "Confirm discard" goes back to "Discard" when its window lapses or its session changes;
    - LOW-027: the on-close list names an open recovered checkout.
  - **Expected counts:** desktop **3919** = 3912 (e3, green) + 7: `TestOpenReview` 4 parametrised cases, `TestTwoStepDiscard` 1, `TestReconstruction` 1, `TestCloseList` 1. The `saved_note_line` case extends an existing test. Extension **105**, unchanged. Ruff clean, mypy 47 files.
  - WATCH: the new tests set screen internals directly — `recovery_screen._busy` in LOW-024's, and `_protected` plus `_transcript_source` in LOW-027's — as the existing tests set `state_value`.
  - Next: if green, round 33 is not owed (round 32 had no MED+), so the loop ends there → `phase-complete`, then the composer's codex pass.
- **EXECUTOR HANDOFF (leg `stage-5-exec-e3`, 2026-09-28T00:38+10:00, run stage-5): Tasks 5.5 and 5.6 are BUILT (🟨), so all of Phase 5 (5.1–5.6) is built and awaiting suites and review; `reason=composer-run`.** The tree is Phase 4 (uncommitted) plus 5.1–5.6. Overall Progress stays at 44%. The file-by-file records are under each task.
  - 5.5 in one line: at app start the reminder index is rebuilt (one `encounter.enc` decrypt per Unreviewed session; Constraint 7's own exception) and refs are minted. `state.banner` names the newest indexed recording for the focused note (ids and a count, no name). `open_review` is gated by exact ref plus index membership, then the window comes forward and adopts exactly that session.
  - 5.6 in one line: 5.1's evaluator tables are lifted and driven through a real bridge (19 rows), plus the remaining matrix rows, `open_review`'s own rows and the two positive restart cases (28 tests in `test_cross_patient.py`).
  - **Expected counts:** desktop **3912** = 3865 (e2, green) + 47 new:
    - bridge `TestBanner` 8 + `TestOpenReview` 6;
    - `TestReconstruction` 5;
    - `test_cross_patient.py` 28 (19 table rows + 9).

    `test_context_rules.py` only moved its tables, so its count is unchanged. Extension **105**, unchanged (no extension file touched). Ruff and mypy (47 files) are clean; the extension typecheck and lint were run at the end of this leg.
  - WATCH (first run):
    1. `test_cross_patient.py` now imports `test_ui_bridge`, `test_ui_screens`, `test_unreviewed_review` and `test_context_rules`. It became a Qt module (its own `qapp` and `harness` fixtures), so its 3.6 cases run in a process that has imported PySide6.
    2. `test_the_bound_tab_rows` / `test_another_tab_rows` assume the bridge's rule matches the evaluator row for row. A mismatch there is a real bridge finding, not a table bug.
    3. `TestReconstruction.test_restart_banner_then_open_review_opens_the_right_session` uses `make_registry`'s Northside clinic, whose id and host equal `_linked_context()`'s. It waits for both the bridge's verification and the adoption's re-verification before closing.
    4. Ordering in the reconstruction tests relies on `os.utime` back-dating the older key blob by an hour.
  - MORNING SMOKE addition (mock, clinic 1): with an Unreviewed linked recording on disk, restart the app, then open that recording's note in Chrome. `state.banner` is present (until Phase 6 renders it, the Session tab shows nothing new, so the smoke checks that restart, Recovery → Open for review, and the Unreviewed row all still work after the reconstruction).
  - Next: `/review-loop` from round 32 over the whole Phase 5 diff (5.1–5.6), then the codex pass.
- **EXECUTOR HANDOFF (leg `stage-5-exec-e2`, 2026-09-28T00:10+10:00 onward, run stage-5): the suspend failure is fixed IN PRODUCTION, and Task 5.4 is decided (a) and BUILT (🟨); `reason=composer-run`.** Tasks 5.5 and 5.6 were not started. I stopped at this clean point because 5.4 is large and its tests have not run yet. The tree is Phase 4 (uncommitted) plus 5.1–5.4. Overall Progress stays at 44%.
  - **The suspend fix — production, not only the test.**
    - The failure: `super().nativeEvent(b"windows_generic_MSG", <int>)` was refused by PySide6's argument marshalling ("called with wrong argument values").
    - Why production: the value was a 64-bit address, and a real `MSG*` on 64-bit Windows has that magnitude. The wheel ships stubs only (`message: int`) and no shiboken typesystem source, so this could not be proven by reading the binding. The base call would therefore most likely raise on real messages, into Qt's dispatch.
    - The fix (`ui/main_window.py` `nativeEvent`): the base is never called. The override returns `(False, 0)`, which is exactly QWidget's default "not handled", so Qt's own handling continues. The whole body sits in `try/except`, so nothing raises into the dispatch.
    - Tests:
      - `test_the_override_never_raises_into_qt` (a raising `pause_for` on a real suspend message, and a junk event type and message; both return `(False, 0)`).
      - `test_a_real_suspend_message_through_qts_dispatch` (Windows only): a child process on the real `windows` platform plugin sends `WM_POWERBROADCAST`/`PBT_APMSUSPEND`, another broadcast and `WM_NULL` through `SendMessageW`. It asserts the spy saw exactly `["suspend"]` and stderr has no traceback, `TypeError`, `ValueError` or "wrong argument".
    - WATCH:
      - If that test prints `SEEN []`, Qt is not delivering the broadcast to `nativeEvent`, and the suspend pause needs a native event filter. That would be a real finding, not a test bug.
      - MORNING SMOKE: sleep the PC during a mock recording. On wake it should be paused with the cue, and the window should respond with no error spam.
  - **Task 5.4 brief:** it is in the task: (a) `adopt_queued` vs (b) extending the lease to recovered checkouts, both costs, and all 15 custody consumers.
    - Executor recommendation: (a). Every consumer already handles a live queued session; (b) duplicates the leased save/complete path, where rounds 27–36 found their races.
    - Decided (a) under the overnight pre-authorisation, revisable by the practitioner.
  - **Reading recorded for review:** a reopened saved note is shown AS SAVED and read-only; changing it means "Regenerate (replaces the saved note)".
  - **Expected counts:** desktop **3865** = 3821 at e1 + 2 suspend tests + 42 Task 5.4 tests (`test_unreviewed_review.py`). Extension **105**, unchanged (no extension file touched this leg). Ruff, mypy (47 files) are clean; the extension's typecheck and lint were run at the end of this leg.
  - WATCH (5.4 tests, first run):
    1. `TestOpenForReview` / `TestCloseList` are the first tests to drive `MainWindow`'s Recovery path with a REAL `SessionController` and real DPAPI. A failure there more likely points at a seam than at custody.
    2. A first close is now refused while Unreviewed rows or a live queued session exist. Other tests' bare `window.close()` cleanups may leave such a window open; none asserts on it.
    3. `test_the_saved_note_line_follows_the_config` expects `PIPELINE_CONFIG.model_copy(update={"autofill_rules": ()})` to have a different `config_digest()`.
    4. `test_the_expiry_warning_shows_and_cues_once` relies on the key blob's mtime being the earliest trusted time.
  - MORNING SMOKE (add to the phase checklist; mock consultations, clinic 1): record A, Finish, then Start B (A retires); Discard B. Then:
    - Recovery → Unreviewed → Open for review on A: the transcript opens with Generate.
    - Generate, Save, then Start C and Discard it. Reopen A: the saved note is on the Note tab with Copy, and the Transcript screen offers Regenerate. Complete.
    - Close the app with an unreviewed row: the first close lists expiries and the second quits.
  - Next: the composer's suites → Task 5.5 (the banner, `open_review`, startup reconstruction decrypting `encounter.enc` once per session with its spy test) and 5.6 → `/review-loop` from round 32.
- **EXECUTOR HANDOFF (leg `stage-5-exec-e1`, 2026-09-27T23:54+10:00, run stage-5): Phase 5 Tasks 5.1, 5.2 and 5.3 are BUILT (🟨); `reason=composer-run`.** The tree is Phase 4 (uncommitted, smoke pending) plus these tasks. Overall Progress is unchanged at 44%, since nothing is 🟩 until the suites and review pass. The file-by-file records are under each task.
  - Landed:
    - `context_rules.py` (new, Qt-free): D5's `pause_action` table, the tab-binding `ContextEvaluator`, and the reminder index (`ReminderIndex`, `reminder_entry`).
    - `ui/bridge.py`:
      - `pause_for` pauses through the Session screen's slot and sets the block for a linked session.
      - `resume_refusal` is the ONE resume check, installed as the Session screen's guard.
      - `state.block`, `resume_previous` (pending, 30 s, resumes only on the focused report of the session's own note), and `notice: review_open`.
    - `ui/session_screen.py`: the resume guard, `session_resumed`, `session_retired`, the two-step Discard button, and Start at QUEUED disabled while the review lease is held.
    - `ui/main_window.py`:
      - `nativeEvent` suspend → `pause_for`, and the desktop cue (status line, message, taskbar flash).
      - The reminder index is filled on retirement and emptied by Complete, Discard, the Recovery list's Discard and the post-sweep prune.
      - The Note tab is cleared on Start (see 5.3's record: a stale post-Save "delete note and complete" could have completed the NEXT recording).
    - `ui/models.py`: the QUEUED Start, the cues and copy, and the Chrome view's phase and block lines.
    - `ui/recovery.py`: `session_removed` and `sessions_root`.
    - `app.py`: the prune after each sweep.
    - Docs: the threat model's "THE PAUSE RULE AND THE BLOCK" paragraph and its residue, the bridge sentence and pipe residue (1)(d), data-flow flow 19, CHANGELOG.
  - Checks (mine): ruff clean; mypy **47 files** (46 + `context_rules.py`). No extension file changed, so I did not run `typecheck`/`lint`. I did not run pytest or vitest (no grant).
  - **Expected suites: desktop 3821 passed** (3555 + 266):
    - `test_context_rules.py`: 212 (the D5 table alone is 178 parametrised cases);
    - `test_ui_bridge.py`: +31 net (the 2-case "Phase 5 actions are not available" test becomes 1 `open_review` case; plus `TestPauseRule` 21, `TestResolution` 8, `TestBackToBack` 3);
    - `test_ui_pause_and_unreviewed.py`: 17;
    - `test_ui_models.py`: +6 (the QUEUED pin is updated in place).
    - **Extension 105** (unchanged).
  - Watch items for the composer's run:
    1. `TestSuspendAndCue::test_suspend_pauses_a_recording_and_cues` calls the real `QMainWindow.nativeEvent` offscreen with a ctypes `MSG` address. If that base call misbehaves offscreen, the fix belongs in the test (call `_is_suspend_event` plus `pause_for`), not in the contract.
    2. Existing bridge tests that reconnect (`connect(2)`) or change the bound note during a recording now also pause it (D5). I read each one and none asserts RECORDING afterwards, but a failure there is the new rule acting, not a regression.
    3. `test_ui_models.py::TestControlsForState` pins QUEUED as `ControlSet(start=True)` (D6). Any other test asserting that Start is disabled at QUEUED is the old behaviour; I found none.
    4. The bridge harness now builds its Session screen with a fake transcriber (a bridge Finish would otherwise have loaded the real ML stack), and its teardown waits up to 15 s for a running check or transcription.
  - Next:
    1. The composer runs both suites.
    2. Then, in order: Task 5.4's decision brief (pre-authorised: the executor's recommended option) and its build; 5.5 (the banner and `open_review`, with startup reconstruction and refs minted for indexed sessions); and 5.6 (the context rows of `test_cross_patient.py`, reusing `test_context_rules.py`'s table).
    3. Then `/review-loop` from round 32 over the whole Phase 5 diff.
- **EXECUTOR HANDOFF (leg `stage-4-exec-d9`, 2026-09-27T23:30+10:00, run stage-4) — Phase 4 BUILD-COMPLETE and CONVERGED; `reason=phase-complete`.** Tasks 4.1–4.5 are 🟩. Suites: desktop 3555 passed, extension 105 passed. Rounds: in-session `/review-loop` 25–26; codex pass stage-4.p1 27–31, converged at peer_round 5 of 6. Overall Progress `44%` (18 of 41). The commit is HELD until the live-user smoke below passes (`OWNERSHIP: gate-disposition key=live-user-smoke-deferral`); later phases build on this uncommitted tree.
  - **Phase 4 LIVE-USER SMOKE — for the practitioner, in the MORNING.** Run each step and report PASS or FAIL per step number. Never paste a path, a patient, a note, a clinic web address or an email into chat.
    1. **One-time setup.** In a normal PowerShell window, from the repo folder, run `cd extension`, then `npm run build`. Then open `chrome://extensions` and press the reload arrow on "Cliniko Scribe Companion". You do NOT need to re-run `register-native-host.py`. Expected: the build finishes with no error, and the extension card shows no error.
    2. **Fully restart Chrome.** Quit Chrome, then check Task Manager: no `chrome.exe` may be left (end any that remain). Expected: no Chrome process is running.
    3. **Start the app.** Double-click `.venv\Scripts\scribe-app.exe` in Explorer and open the Session tab. Expected: a line reading "Chrome: not connected - open Cliniko in Chrome with the Cliniko Scribe Companion extension to record from a treatment note.", and below it "Pause hotkey: not set up. Spoken pause: not set up."
    4. **Open Chrome.** Expected: within a few seconds the pinned extension icon shows a green **OK** badge — the new version-2 handshake works. The app's Session tab now reads "Chrome: connected." A red **ERR** badge means Chrome is still running the old extension build: repeat steps 1–2.
    5. **Close the app while Chrome stays open.** Close Cliniko Scribe's window. Expected: Chrome's badge stays **OK**, because the badge only shows that Chrome reached its helper, not the app. Then double-click `scribe-app.exe` again. Expected: within about two seconds the Session tab reads "Chrome: connected." again, with no need to touch Chrome.
    6. **Close Chrome while the app stays open.** Quit Chrome fully, as in step 2. Expected: within a few seconds the app's Session tab returns to "Chrome: not connected - …". Reopen Chrome. Expected: **OK** again and "Chrome: connected."
    7. **Desktop recording still works (mock only).** On the Session tab, tick the consent box, press Start, wait about five seconds, then press Discard. Expected: recording starts and discards as before. The Chrome line stays "Chrome: connected." and shows NO "Recording for …" line, because a desktop Start is not linked to a note.
  - **Not testable until Phase 6** — do not expect these tonight:
    - the Chrome side panel, the page frame and the block;
    - Chrome reporting which Cliniko page or note is open, so no note is checked with Cliniko from Chrome;
    - starting, pausing or finishing from Chrome;
    - a linked "Recording for <patient> - <clinic>" line on the Session tab;
    - the reconnect re-check line.

    The protocol, the pipe, the relay and the app's bridge that those features ride on are what steps 3–6 exercise. They are also covered by automated tests against real named pipes and real host and app processes.
  - **If a step fails:**
    - Close the app and quit Chrome fully (no `chrome.exe` in Task Manager), then start the app first and Chrome second.
    - If the app says "Chrome link unavailable - another program is using its channel", another copy of the app, or a program holding its channel, is running. Close every Cliniko Scribe window, check Task Manager for a leftover `pythonw.exe` of the app, and relaunch.
    - Desktop recording from the Session tab works whether or not the Chrome link does: the link is additive.
    - Do NOT run `git checkout`, `git reset` or `git stash`. Phase 4 and later work exists only in the working tree, uncommitted. Just report which step failed.
  - **For the composer's `/document`** (AGENTS.md):
    - Current Status: Phase 4 of the Cliniko workflow safeguards plan — protocol v2 (`context` / `command` / `state`, fixtures-canonical, `LIMITS`); the per-user named pipe (`pipe_server.py`); the host's verified two-way relay (`pipe_client.py` + `native_host.py`); the app's Chrome bridge (`ui/bridge.py`) and the Session screen's Chrome line.
    - Task 4.3 decided (b) under the practitioner's overnight pre-authorisation — revisable by the practitioner.
    - Local Run Steps: after a protocol version change, rebuild and reload the extension and fully restart Chrome; `register-native-host.py` does not need re-running (the installed launcher runs the repo's code).
    - Subsystem pointers: if touching `pipe_server.py`, `pipe_client.py`, `native_host.py`'s relay or `ui/bridge.py`, read the threat model's "Chrome link" section and flow 19 of `docs/security/data-flow-map.md`. The ownership rule: only the reading thread closes a pipe handle. The re-check lifetime and D9 rules sit beside it.
    - Suites 3555 + 105.
  - Executor recommendation: Phase 6's badge should reflect the app from `state.app_running`, not only the host handshake. Today a green **OK** with the app closed is correct but easy to misread (step 5). surface=production
  - Executor recommendation: the draft-write plan (PLAN.md Phase 4) must pass a re-verification made FOR the write into `live_writeback_target(...)`. The bridge's `live_reverification()` is a reconnect status (round 21's observation; MED-012's guard already refuses a stale rev), not a pre-write check. surface=production
  - Executor recommendation: Phase 5's `open_review` / `resume_previous` must go through the bridge's existing `session_ref` gate. They are refused `not_available` today, so each needs its own cross-patient rows (Task 5.6). surface=production
- **EXECUTOR HANDOFF (leg `stage-4-exec-d8`, 2026-09-27T23:55+10:00, run stage-4) — LEG 2 `/fix` for codex round 30: PR-LOW-160 and PR-MED-161 applied; round 30 Closed; `reason=composer-run`.** Tasks stay 🟨; the scoped codex confirmation (round 31) follows.
  - Landed:
    - `native_host.py` `AppRelay.stop` never closes the link, even on a join timeout; it logs and returns False, and the handle goes with its reader or at process exit.
    - `native_host.py` `AppRelay.forward` clears `_link` when it retires it.
    - `pipe_client.py` `PipeConnection.write_frame` refuses before any I/O once `_ended()` (the retire or stop event is set).
    - Docs: the ownership rule is restated as a class in both modules' docstrings, the threat model's relay paragraph and CHANGELOG part 2.
    - Tests: `relay_fakes.FakeLink(settle_gate=…)`; `TestLinkOwnership` (2 tests); `test_a_retired_or_stopped_connection_writes_nothing[retire|stop]` on a real pipe.
  - Checks (mine): ruff clean; mypy 46 files; extension `typecheck` and `lint` clean (no extension change); `loop-history-check` OK (24 entries + 30 headings). Expected: **desktop 3555 passed** (3551 + 4); **extension 105** (unchanged).
- **EXECUTOR HANDOFF (leg `stage-4-exec-d7`, 2026-09-27T23:40+10:00, run stage-4) — LEG 1 verification of codex round 30. Nothing changed but round 30's record and this bullet; `reason=phase-complete`.** PR-LOW-160 and PR-MED-161 are both confirmed as behavioral and low; they are the unfinished halves of my PR-MED-140 and PR-MED-141 fixes. One shape covers both: the stopper never closes the link, even on a timeout, leaving it to the reader or to process exit; and `write_frame` refuses before any I/O once the connection is retired or stopped, with `forward` also clearing `_link` on retire. Cap verdict: raise +1 (the pass is at peer_round 4 of cap 5). Round 30 stays Open for the `/fix` leg; the shapes and tests are in its LEG 1 block.
- **EXECUTOR HANDOFF (leg `stage-4-exec-d6`, 2026-09-27T23:20+10:00, run stage-4) — LEG 2 `/fix` for codex rounds 27–29: 6 findings applied, 1 rejected; all three rounds are Closed; `reason=composer-run`.** Tasks stay 🟨; the scoped codex confirmation (round 30) follows.
  - Landed:
    - PR-MED-131: `framing.read_frame` catches `except ValueError`, which covers the digit-limit error.
    - PR-MED-140 and PR-MED-141, one mechanism:
      - `pipe_client.PipeConnection` gains a `retire` event, and `pipe_server._OverlappedReader` takes `*more_stops`, so the read waits on both.
      - `native_host.AppRelay.stop` no longer closes the link before the join; the relay thread closes it after the read settles. The link is closed from `stop` only on a join timeout, which is logged.
      - `AppRelay.forward` retires the connection on a failed write: no reuse, no replay.
      - `relay_fakes` model the shared stop event.
    - PR-LOW-142: `pipe_client` compares the ACE type, flags, mask and SID (`APP_ACE_MASKS`).
    - PR-MED-150: `ui/bridge.py` `_rev_current` is applied at install, read and display, and `on_clinics_changed` re-runs the live re-check.
    - PR-LOW-151: the threat model's THE BRIDGE paragraph gives two name lifetimes; the bridge docstring sibling is reworded.
    - Docs updated: the threat model's relay and bridge paragraphs, and CHANGELOG part 2.
  - Checks (mine): ruff clean; mypy 46 files; extension `typecheck` and `lint` clean (no extension change); `loop-history-check` OK (23 entries + 29 headings). Expected: **desktop 3551 passed** (3540 + 11: framing 1, native_host 1, relay 2, pipe_client 4 — the retire test, 2 contract rows and 1 real-pipe DACL case — and bridge 3); **extension 105** (unchanged).
  - Watch in the composer run: `test_pipe_client.py::TestConnect::test_the_apps_pipe_connects_verified_both_ways` asserts that the real app pipe's ACE mask is in `{0x1F01FF, GENERIC_ALL}`. That is FILE_ALL_ACCESS as `GA` maps on creation, which I could not observe without running Python. If it fails, the observed mask belongs in `APP_ACE_MASKS`; it is not a regression.
- **EXECUTOR HANDOFF (leg `stage-4-exec-d5`, 2026-09-27T23:03+10:00, run stage-4) — LEG 1 verification of codex pass stage-4.p1 (rounds 27–29). Nothing changed but the three rounds' records and this bullet; `reason=phase-complete`.** Of 7 findings, 6 are confirmed and 1 is invalid. No finding verifies as CRIT or HIGH.
  - Round 27: PR-MED-130 is **invalid** — JavaScript's `$` without the `m` flag matches only at end of input. PR-MED-131 is **confirmed, low**: the int-digit-limit `ValueError` escapes `read_frame`, the sibling LOW-020 missed; the Cliniko client already handles it.
  - Round 28: PR-MED-140 (shutdown closes the pipe handle before the reader settles its I/O), PR-MED-141 (a failed write leaves the connection current) and PR-LOW-142 (the DACL check ignores flags and mask) are all **confirmed, low**. 140 and 141 share one fix: a per-connection retire event, with the handle closed only by the relay thread.
  - Round 29: PR-MED-150 is **confirmed, med** — the reconnect re-check ignores D9's `clinic_rev`, so the screen can say "verified" under a replaced or removed key; the write path is still guarded by MED-012. PR-LOW-151 is **confirmed, docs-only**.
  - Cap verdicts: rounds 27, 28 and 29 each raise +1. All three rounds stay Open for the composer's `/fix` leg; the fix shapes and regression tests are in each LEG 1 block.
- **EXECUTOR HANDOFF (leg `stage-4-exec-d4`, 2026-09-27T22:46+10:00, run stage-4) — `/review-loop` round 26 (round 2 of cap 3): the 4 round-25 fixes are confirmed, and 1 LOW that MED-018's fix introduced (LOW-022) is applied; `reason=composer-run`.** Tasks 4.1, 4.2, 4.4 and 4.5 stay 🟨 and 4.3 stays 🟩.
  - LOW-022: `ChromeBridge._reset_connection` no longer clears a re-check that is waiting. A bare disconnect had stranded it on "Checking…" until Chrome reconnected. Test: `test_a_disconnect_does_not_strand_a_waiting_recheck`.
  - Count reconciliation: the extension's 105 (not the 102 I predicted in d3) is right. `protocol.test.ts` makes one vitest case per fixture file, so the three new fixtures are three cases. I misread the loop; no unintended test was added.
  - Checks (mine): ruff clean; mypy 46 files; `loop-history-check` OK (20 entries + 26 headings). Expected: desktop 3540 passed (3539 + 1); extension 105 (unchanged).
  - Next: round 27 (round 3 of cap 3) confirms LOW-022 and runs a last missed-issue pass. If it is clean on a green suite, the review-loop has converged and the codex pass follows.
- **EXECUTOR HANDOFF (leg `stage-4-exec-d3`, 2026-09-27T22:40+10:00, run stage-4) — `/review-loop` round 25 (round 1 of cap 3) over the whole Phase 4 diff: 0 CRIT / 0 HIGH / 1 MED / 3 LOW, all applied; `reason=composer-run`.** Tasks 4.1, 4.2, 4.4 and 4.5 stay 🟨 and 4.3 stays 🟩.
  - Checks (mine): ruff clean; mypy 46 files; extension `npm run typecheck` and `npm run lint` clean; `loop-history-check` OK (19 entries + 25 headings). I did not run pytest or vitest (no grant). Expected: desktop 3539 passed (3527 + 9 new tests + 3 new fixture cases); extension 102 passed (its fixture tests loop inside one test each).
  - Fixed: MED-018 (`ui/bridge.py`: the live session's reconnect re-check gets its own waiting slot, so a report's check can no longer displace it, and its result goes only to the current check by identity, never to the ledger); LOW-019 (the re-check's result, which names the patient, is dropped when its session ends); LOW-020 (`framing.read_frame`: a `RecursionError` from deeply nested JSON is now the `malformed` framing fault instead of silently killing a reader thread); LOW-021 (envelope parity: `protocol_version` is a `StrictInt`, the host's pre-check does not treat a boolean as a version, and TypeScript counts `request_id` / `session_nonce` in code points, backed by 2 invalid fixtures and 1 valid one). Details are in the round 25 block.
  - Next: the composer runs both suites, then round 26 (the post-fix check, round 2 of cap 3) in the next leg. If it is clean on a green suite, the review-loop has converged and the codex pass follows.
- **EXECUTOR HANDOFF (leg `stage-4-exec-d2`, 2026-09-27T22:24+10:00, run stage-4) — the d1 failure is fixed, Task 4.3 is recorded 🟩 (decided (b)) and Task 4.4 is BUILT 🟨; `reason=composer-run`.** All of Phase 4 (4.1, 4.2, 4.4, 4.5 🟨; 4.3 🟩) is now ready for the `/review-loop` in the next leg.
  - Checks (mine): ruff clean; mypy 46 files (45 + `pipe_client.py`); extension `npm run typecheck` and `npm run lint` clean (no extension code changed this leg). I did not run pytest or vitest (no grant).
  - **The d1 failure, fixed as a class:** `test_logging_setup.py::test_tripwire_drops_pydantic_repr_leak` now builds a real v2 `Envelope` (`protocol_version=PROTOCOL_VERSION`), so the tripwire is still proven against a real envelope's repr. The other `protocol_version` 1 literals in the suite now use `PROTOCOL_VERSION` too (`test_logging_setup.py` ×2, `test_framing.py` ×2; those were unvalidated dicts that still passed). The one remaining literal 1 is the deliberate `protocol/fixtures/invalid/version_1.json`.
  - **What landed:**
    - `desktop/src/scribe_desktop/pipe_client.py` (new):
      - `ServerUnverified` :84;
      - `unverified_reason` :104 — the (b) contract, one pure function: same logon session, same user SID, exactly the protected single-entry user DACL;
      - `read_server_identity` :136;
      - `PipeConnection` :149;
      - `AppPipeConnector` :207, whose `connect` :249 makes one bounded `WaitNamedPipe`, then opens the pipe for identification only, then verifies before any frame.
    - `desktop/src/scribe_desktop/native_host.py`:
      - `RELAYED_TYPES` :79 and `APP_NOT_RUNNING` :85;
      - `ChromeOut` :195;
      - `AppRelay` :235 — `forward` :280, `_run` :304, `_pump` :339;
      - `app_relay_factory` :367;
      - `run_host` :398 and `_main_loop` :425, one queue fed by a stdin thread and the relay;
      - `HostSession.handle` returns None for a relayed type with this session's nonce.
    - `desktop/src/scribe_desktop/pipe_server.py`: the peer lookups (`pipe_peer_pid` :210, `process_image_path` :231, `process_user_sid` :248), and `PipeServer._log_peer` :448 — the 4.3 tripwire, which logs the executable path only.
  - **What "verified" means under (b):** the pipe's server process runs in the host's own Windows logon session, its token user is the host's user SID, and the pipe's DACL is exactly `D:P(A;;GA;;;<that SID>)` as the app creates it.
    - A pipe that exists but fails any of these, cannot be checked, or denies the host is a typed `internal` error to Chrome and exit 1, never a retry.
    - Absent or busy is not unverified: the host sends `state{app_running:false}` once and re-waits.
  - **Expected suites:**
    - **desktop 3527 passed.** 3479 + 1 (the fixed test) + 47 new:
      - `test_native_host_relay.py` 24;
      - `test_pipe_client.py` 22, of which the 11-case contract table also runs off Windows;
      - `test_integration_no_sockets.py` +1 (the host-to-app relay leg).
      - Caveat: if a real `scribe-app` is listening on this user's pipe during the run, `test_full_handshake_via_launcher_with_no_sockets` SKIPS by name, giving **3526 passed, 1 skipped**. It skips because its real host would otherwise connect to the running app.
    - **extension 102 passed in 3 files** (unchanged).
  - **Watch items for the suite run:**
    1. The launcher leg now reads the host's stamped `state{app_running:false}` right after `hello_ack` and before the ping. It hangs only if the host never announces; the host always does when no app is listening.
    2. `test_pipe_client.py` creates squatter pipes on unique test names with a wider DACL, an unprotected DACL and a SYSTEM-only DACL. The unprotected case expects `dacl`: this assumes Windows does not report named-pipe DACLs as protected unless `P` was given. If it does, that one case fails, and the fix is to the test, not the contract.
    3. `test_both_ends_log_the_peer_path_and_nothing_else` expects exactly two `pipe_peer path=<python.exe>` lines, because this process is both ends.
    4. Every relay test runs `run_host` on a thread with fakes whose blocking reads end on a 10 s timeout, so a failing test cannot hang the suite.
  - **Before any Chrome-side smoke step works on this host (practitioner, in order):**
    1. Close `scribe-app`, then relaunch it by double-clicking `.venv\Scripts\scribe-app.exe`, so it runs the new pipe server and bridge.
    2. In a normal terminal: `cd extension && npm run build`, then **Reload** the unpacked extension in `chrome://extensions`. The installed build is v1, and the v2 host refuses its `hello`, so the badge shows ERR until this is done.
    3. **`scripts/register-native-host.py` does NOT need re-running.**
       - The installed `%LOCALAPPDATA%\ClinikoScribe\scribe-host.exe` is a copy of pip's launcher. The script's docstring says the copy "still runs the repo's code — the launcher embeds the venv interpreter path".
       - The venv is an editable install (`pip install -e`), so the new `native_host.py` and `pipe_client.py` load from the repo.
       - No entry point or manifest changed. Re-register only after a venv move or reinstall (AGENTS.md step 5).
    4. **Fully restart Chrome**, and check that no `chrome.exe` is left before relaunching (AGENTS.md step 7).
    5. EXPECT: with `scribe-app` running, the Session tab's Chrome line reads "Chrome: connected." once Chrome's host has connected. With the app closed, the extension receives "app not running". The side panel that SHOWS this is Phase 6; today only the Session screen and the badge do.
  - Docs:
    - The threat model's Chrome-link section: the 4.3 decision, what "verified" means, "THE HOST'S RELAY" with its residue, the four same-user items (a)–(d) stated as residue, and the squatter case. Its scope and review-trigger lines are updated too.
    - Data-flow flows 1 and 19, and CHANGELOG.
  - Next:
    1. The composer runs `cd desktop && ../.venv/Scripts/pytest.exe -q; cd extension && npm run qa`.
    2. `/review-loop` from round 25 over the whole Phase 4 diff (4.1–4.5), in the next leg.
    3. The phase-complete handoff then owes the ≤ 6-step live smoke (mock consultation, clinic 1, launched by double-clicking `.venv\Scripts\scribe-app.exe`, after the steps above).
- **EXECUTOR HANDOFF (leg `stage-4-exec-d1`, 2026-09-27T22:04+10:00, run stage-4) — Tasks 4.1, 4.2 and 4.5 BUILT (🟨, file-by-file records under each task); the 4.3 decision brief is written; 4.4 not started (blocked on 4.3); `reason=composer-run`.**
  - Checks (mine): ruff clean; mypy 45 files (43 + `pipe_server.py` + `ui/bridge.py`); extension `npm run typecheck` and `npm run lint` clean. I did not run pytest or vitest (no grant).
  - **Expected suites:**
    - **desktop 3480 passed.** 3323 + 157, counted by hand with the parametrize expansions:
      - `test_protocol.py` 19 → 93 (+74; 18 valid and 47 invalid fixtures);
      - `test_native_host.py` +1 (below-floor over 0 and 1);
      - `test_pipe_server.py` 26 (new);
      - `test_ui_bridge.py` 41 (new);
      - `test_session_machine.py` +3;
      - `test_ui_screens.py` +3;
      - `test_ui_models.py` +8;
      - `test_integration_no_sockets.py` +1;
      - `test_live_session.py` +0 (one test extended).
    - **extension 102 passed in 3 files** (was 36): `protocol.test.ts` 19 → 82, `connection.test.ts` 16 → 19, `scaffold.test.ts` 1.
  - **Decision brief for Task 4.3** (the practitioner's `[decision]`, to be relayed verbatim): it is written under Task 4.3 in `## Tasks`. It covers:
    - the default (b) and the upgrades (a) and (c), with what each costs;
    - the four residue items;
    - what the code shows about the launcher and redirector chain;
    - the one practitioner-run PowerShell measurement, which is needed only for (a) or (c).
    - Executor recommendation: (b) — every residue item requires same-user code, which boundary 2 already accepts with stronger capabilities (it can read the Cliniko key from Credential Manager and query the patient directly); (a) and (c) are defeated by that same attacker in one step (launching the real `scribe-host.exe`, parent spoofing or a venv edit) while adding a fail-closed break on every interpreter-path change. Optionally, as a cheap tripwire in the spirit of boundary 2's startup logging: the host logs the pipe server's image path at each connect and the app logs the client's (a path, never a frame), with no gate. The "pipe exists but server unverified" hard error in 4.4 stays, as the logon-session check.
  - **Watch items for the suite run:**
    1. `test_pipe_server.py` and the new no-sockets leg create REAL named pipes, each with a unique `ClinikoScribe-test-<uuid>` name, so a running `scribe-app` is never touched. The pipe writer is latest-wins, so the no-sockets child reads frames until the post-report snapshot arrives rather than counting them.
    2. `test_ui_bridge.py` runs the real `verify_note_context` on `TaskThread`s against `NoteTransport`; each test waits on `bridge.is_busy` before it asserts.
    3. `test_the_bridge_never_logs_and_the_label_is_plain_text` asserts that no captured log record contains the fake name, ids or host; nothing on that path holds a logger.
    4. `TestRecordedSeconds` feeds 8-byte chunks, so the count, not the audio length, is what it tests.
  - **Live-environment effect to know before any smoke:**
    - The host now speaks v2 and refuses a v1 `hello`. The practitioner's installed extension build is v1, so its badge will show ERR until `cd extension && npm run build`, a reload in `chrome://extensions` and a full Chrome restart.
    - The host still answers only hello/ping (the relay is 4.4). So on a real install the Session screen can only show "Chrome: not connected - …" and the hands-free line. Nothing from Chrome reaches the app until 4.4.
  - Scope notes:
    - Within 4.5's display line, the block reason (Phase 5), the hotkey and spoken-pause controls (Phase 7) and warnings (none produced yet) are deferred by phase. D7's "Spoken pause unavailable for this recording" line IS shown.
    - `resume_previous` and `open_review` are refused `not_available` until Phase 5 defines them.
  - Docs:
    - The threat model has a new "The Chrome link" section (protocol v2, the pipe, the bridge, each with its residue). Its out-of-scope and review-trigger lines are updated.
    - Data-flow map: flow 1, new flow 19, flow 18's second trigger, the components table, and the old "Phase 5 preview" replaced.
    - `CHANGELOG.md`.
    - Owed from the composer's `/document`: an AGENTS.md subsystem pointer for the pipe / bridge / protocol v2.
  - Next:
    1. The composer runs `cd desktop && ../.venv/Scripts/pytest.exe -q; cd extension && npm run qa`.
    2. It relays the 4.3 brief to the practitioner.
    3. `/review-loop` from round 25 over the 4.1 + 4.2 + 4.5 diff, in a later leg.
    4. 4.4 once 4.3 is decided.
    5. The phase-complete handoff then owes the ≤ 6-step live smoke (mock consultation, clinic 1, launched by double-clicking `.venv\Scripts\scribe-app.exe`).
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
- **Last plan sync:** 2026-09-28T04:19+10:00 (leg `stage-8-exec-h2`): Tasks 8.1 and 8.2 🟨 BUILT (8.2's selection route added under the composer's disposition), `/review-loop` round 45 converged; awaiting the composer's suites (desktop 4025, extension 295) and the codex pass; P.2 🟥; Overall Progress unchanged.
- **COMPOSER RUN-STATE (2026-09-28 03:58, `/execute-loop` run iso `cliniko-safeguards-20260927-152609-a3c9bc86`, isolation=none, branch main):** PHASES 1–3 CLOSED and committed (32e7289, dc6530b, 7a6cbd7). PHASE 4 BUILT + CONVERGED (stage-4, session b2a28af8; rounds 25–31). PHASE 5 BUILT + CONVERGED (stage-5, session 91142c7d; rounds 32–35). PHASE 6 BUILT + CONVERGED (stage-6, session 7e75d900, legs f1–f9): Tasks 6.0–6.5 🟨 until the live smoke passes; in-session `/review-loop` round 36 (5 LOW, fixed); codex pass stage-6.p1 over a Phase-6-only tree diff (Phase 5 tree 339b8ddf → final ceb3db22+) rounds 37–40 (1 MED + 5 LOW → 1 LOW → 1 LOW, every fix applied; accept-closed at peer round 4 of 6 on the executor's cap verdict after a recorded cap raise); composer suites 3922 desktop + 292 extension + `npm run build` green. PHASE 7 BUILT + CONVERGED (stage-7, session 01ef9b00, legs g1–g5): Tasks 7.1–7.3 🟨 until the live smoke passes; one composer-caught suite failure in g1 (a second word normaliser broke the single-normaliser pin; fixed in production by reusing `note.normalise_token`); in-session `/review-loop` round 41 (3 LOW, fixed); codex pass stage-7.p1 over a Phase-7-only tree diff (Phase 6 tree 70f4b247 → bea02e4a → c71f7c09) rounds 42–44 (2 LOW → 0 → clean confirmation; converged at peer round 3 of 5); composer suites 4017 desktop + 295 extension + build green. **Phases 4, 5, 6 AND 7 are UNCOMMITTED**: their live smokes (Phase 4: 7 steps in the stage-4 d9 bullet; Phase 5: 8 steps in the stage-5 e7 bullet; Phase 6: 10 steps in the stage-6 f9 bullet; Phase 7: 8 steps in the stage-7 g5 bullet — run in that order) were DEFERRED to the morning by the practitioner's 21:39 overnight instruction; each commit waits on its own smoke-pass. Overnight pre-authorisations applied: Task 4.3 → (b); Task 5.4 → (a); Task 6.0 → `jsdom` 30.1.1 (exact, dev-only, `--ignore-scripts`). `/document` for Phases 4–7 run by the composer (AGENTS.md). **Immediate next action:** Phase 8 (runkey stage-8, fresh session: 8.1 security docs, 8.2 clipboard exclusion; P.2 is practitioner-owned) on the uncommitted tree; never `git checkout`/`reset`/`stash`. Last plan sync: 2026-09-28 03:58.
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
- 2026-09-27 round 25 (Phase 4, /review-loop round 1 of cap 3): 0 CRIT / 0 HIGH / 1 MED / 3 LOW; all applied (MED-018 the live re-check's waiting slot; LOW-019..021); skew=pre-existing; action=none
- 2026-09-27 round 26 (Phase 4, /review-loop round 2 of cap 3, post-fix check): 0 CRIT / 0 HIGH / 0 MED / 1 LOW; 4/4 round-25 fixes confirmed; LOW-022 (a disconnect stranded a waiting re-check) applied; skew=fix-induced; action=none
- 2026-09-27 round 27 (codex gpt-6-astra medium, pass stage-4.p1 slice A): 0 CRIT / 0 HIGH / 2 MED / 0 LOW (verified: 1 low, 1 invalid); fixed 131 (the digit-limit ValueError in `read_frame`, LOW-020's sibling), rejected 130 (JavaScript `$` is end-of-input); skew=none; action=none
- 2026-09-27 round 28 (codex gpt-6-astra medium, pass stage-4.p1 slice B): 0 CRIT / 0 HIGH / 2 MED / 1 LOW (verified: 3 low); fixed 140 and 141 (a per-connection retire event, only the reader closes; a failed write ends the connection) and 142 (the DACL flags and mask compared); skew=none; action=none
- 2026-09-27 round 29 (codex gpt-6-astra medium, pass stage-4.p1 slice C): 0 CRIT / 0 HIGH / 1 MED / 1 LOW (verified: 1 med, 1 low docs-only); fixed 150 (D9's clinic_rev guards the live re-check) and 151 (two name lifetimes, docs); skew=none; action=none
- 2026-09-27 round 30 (codex gpt-6-astra medium, pass stage-4.p1 confirmation of rounds 27-29): 0 CRIT / 0 HIGH / 1 MED / 1 LOW (verified: 2 low); 131/142/150/151 and the 130 rejection confirmed; 160/161 fixed (the stopper never closes, even on a timeout; a retired or stopped link refuses writes before any I/O); skew=fix-induced; action=none
- 2026-09-27 round 31 (codex gpt-6-astra medium, pass stage-4.p1 confirmation of round 30): 0 CRIT / 0 HIGH / 0 MED / 0 LOW; clean (PR-LOW-160 and PR-MED-161 confirmed); skew=none; action=none — pass stage-4.p1 converged at peer_round 5 of 5
- 2026-09-28 round 32 (Phase 5, /review-loop round 1 of cap 3): 0 CRIT / 0 HIGH / 0 MED / 5 LOW; all applied (LOW-023 `open_review` refuses an active session before the window moves; LOW-024..027); skew=none; action=none
- 2026-09-28 round 33 (codex gpt-6-astra medium, pass stage-5.p1 slice A): 0 CRIT / 0 HIGH / 0 MED / 1 LOW; fixed (PR-LOW-180 test-harness: the old-client Resume row now discriminates); skew=none; action=none
- 2026-09-28 round 34 (codex gpt-6-astra medium, pass stage-5.p1 slice B): 0 CRIT / 0 HIGH / 1 MED / 2 LOW; all fixed (PR-MED-190 the unfinished-store warning kept on reopen and on the Unreviewed row and selection; PR-LOW-191 and PR-LOW-192 docs-only); skew=none; action=none
- 2026-09-28 round 35 (codex gpt-6-astra medium, pass stage-5.p1 confirmation of rounds 33-34): 0 CRIT / 0 HIGH / 0 MED / 0 LOW; clean (PR-LOW-180, PR-MED-190, PR-LOW-191, PR-LOW-192 confirmed); skew=none; action=none — pass stage-5.p1 converged at peer_round 3 of 5
- 2026-09-28 round 36 (Phase 6, /review-loop round 1 of cap 3): 0 CRIT / 0 HIGH / 0 MED / 5 LOW; all applied (LOW-028 "!" outranks ERR; LOW-029 banner only with a Cliniko tab in front; LOW-030 Resume previous navigates only an allow-listed tab; LOW-031 simplification; LOW-032 `sinks.test.ts` pins text-only / no-storage / one console call); skew=none; action=none
- 2026-09-28 round 37 (codex gpt-6-astra medium, pass stage-6.p1 slice A): 0 CRIT / 0 HIGH / 1 MED / 2 LOW; fixed (PR-MED-200 the event counter guarding every async tab read in `hub.ts`; PR-LOW-201 "!" until the new link's first snapshot; PR-LOW-202 literal host pattern); skew=none; action=none
- 2026-09-28 round 38 (codex gpt-6-astra medium, pass stage-6.p1 slice B): 0 CRIT / 0 HIGH / 0 MED / 3 LOW; fixed (PR-LOW-210 token-level sink scan with detection fixtures; PR-LOW-211 own-property lookups in four dictionaries; PR-LOW-212 the page-cue residue restated as a class, restyle not applied); skew=none; action=none
- 2026-09-28 round 39 (codex gpt-6-astra medium, pass stage-6.p1 confirmation): 0 CRIT / 0 HIGH / 0 MED / 1 LOW; fixed (PR-LOW-220 the sink scan's header overstated alias coverage — bare-token bans for `write`/`writeln`/`Function`, a `constructor` access ban, the header narrowed with every gap named; five of six round 37–38 fixes confirmed); skew=fix-induced; action=none
- 2026-09-28 round 40 (codex gpt-6-astra medium, pass stage-6.p1 confirmation): 0 CRIT / 0 HIGH / 0 MED / 1 LOW; fixed (PR-LOW-230 the sink scan's header overstated `constructor` coverage — narrowed to bare-name vs prefix-dependent rules with the residue named and lint's `no-implied-eval` cited; PR-LOW-220 confirmed); skew=fix-induced; action=none — pass accept-closed at peer round 4 of 6 on the executor's cap verdict
- 2026-09-28 round 41 (Phase 7, /review-loop round 1 of cap 3): 0 CRIT / 0 HIGH / 0 MED / 3 LOW; all applied (LOW-033 a carried word joins the next window only within 3 s; LOW-034 the spoken-pause bridge test discriminates again; LOW-035 the `WM_HOTKEY` child also POSTS through Qt's dispatcher); skew=none; action=none — converged at round 1 (no CRIT/HIGH/MED)
- 2026-09-28 round 42 (codex gpt-6-astra medium, pass stage-7.p1 slice A): 0 CRIT / 0 HIGH / 0 MED / 2 LOW; fixed (PR-LOW-240 start-up `finally` gives the chord back; PR-LOW-241 a press queued before detach is dropped); skew=none; action=none
- 2026-09-28 round 43 (codex gpt-6-astra medium, pass stage-7.p1 slice B): 0 CRIT / 0 HIGH / 0 MED / 0 LOW; clean; skew=none; action=none
- 2026-09-28 round 44 (codex gpt-6-astra medium, pass stage-7.p1 confirmation): 0 CRIT / 0 HIGH / 0 MED / 0 LOW; clean (PR-LOW-240 and PR-LOW-241 CONFIRMED); skew=none; action=none — pass stage-7.p1 converged at peer round 3 of 5
- 2026-09-28 round 45 (Phase 8, /review-loop round 1 of cap 3): 0 CRIT / 0 HIGH / 0 MED / 2 LOW; all applied (LOW-036 the "no call at startup or idle" contract names the Chrome-report trigger in AGENTS.md, the data-flow non-flow and the incident trigger; LOW-037 flow 20 and the Chrome-side retention row state the panel's Ready key and the worker's last-sent slices); skew=none; action=none — converged at round 1 (no CRIT/HIGH/MED)
- 2026-09-28 round 46 (codex gpt-6-astra medium, pass stage-8.p1 slice A): 0 CRIT / 0 HIGH / 0 MED / 2 LOW; fixed (PR-LOW-270 test-harness: offscreen assert + native-copy guards in `_fake_clipboard`, +2 tests; PR-LOW-271 intended-use clipboard limits); skew=none; action=none
- 2026-09-28 round 47 (codex gpt-6-astra medium, pass stage-8.p1 slice B): 0 CRIT / 0 HIGH / 0 MED / 2 LOW; fixed (PR-LOW-280 Chrome-linked start, the desktop and offline fallbacks and D5's triggers at four sites; PR-LOW-281 the incident recovery `netstat` check conditioned on Chrome closed and no practitioner action); skew=none; action=none
- 2026-09-28 round 48 (codex gpt-6-astra medium, pass stage-8.p1 confirmation): 0 CRIT / 0 HIGH / 0 MED / 0 LOW; clean (PR-LOW-270, 271, 280, 281 CONFIRMED); skew=none; action=none — pass stage-8.p1 converged at peer round 3 of 5
- 2026-09-28 round 49 (smoke fix — sleep + screen-lock pause, /review-loop round 1 of cap 3): 0 CRIT / 0 HIGH / 0 MED / 1 LOW; all applied (LOW-038 a suspend or lock no longer renames a block Chrome put up for a patient change); skew=none; action=none
- 2026-09-28 round 50 (smoke fix, /review-loop round 2 of cap 3): 0 CRIT / 0 HIGH / 0 MED / 0 LOW; clean (LOW-038 confirmed fixed); skew=none; action=none — converged at round 2
- 2026-09-28 round 51 (codex gpt-6-astra medium, pass stage-8.p2 smoke fix): 0 CRIT / 0 HIGH / 1 MED / 0 LOW; fixed (PR-MED-300 a Resume click in flight at the lock is refused: a lock flag set during the lock's dispatch, checked first in the one resume check and in `resume_previous`, cleared by the unlock, a missed unlock re-checked with Windows after 5 s); skew=fix-induced; action=none
- 2026-09-28 round 52 (codex gpt-6-astra medium, pass stage-8.p2 confirmation): 0 CRIT / 0 HIGH / 0 MED / 0 LOW; clean (PR-MED-300 confirmed closed); skew=none; action=none
- 2026-09-28 round 53 (H1, Phases 1–8 as one surface, /review-loop round 1 of cap 3): 0 CRIT / 0 HIGH / 2 MED / 11 LOW; all applied (MED-039 a Chrome Start refused while locked; MED-041 intended-use's startup claim qualified; LOW-040 a failed Start and a released recovered view reach the reminder index; LOW-042 a refusal goes when its situation does; LOW-043 page block wording; LOW-044 lone surrogates cleaned; LOW-045..051 docs and a comment); lens (f) recorded for H2; skew=none; action=none
- 2026-09-28 round 54 (H1, /review-loop round 2 of cap 3, post-fix regression + same-family sweep): 0 CRIT / 0 HIGH / 1 MED / 5 LOW; all applied (MED-052 the desktop Start refused while locked; LOW-053 a session command's refusal survives its note's check landing; LOW-054..057 docs: enrolment-under-lock and forged-unlock residue, the reconnect trigger, the lock claim qualified); skew=mixed; action=none
- 2026-09-28 round 55 (H1, /review-loop round 3 of cap 3, post-fix regression): 0 CRIT / 0 HIGH / 0 MED / 2 LOW; both applied (LOW-058 PLAN.md's reconnect trigger; LOW-059 the missed-unlock sentence covers Start, rewrapped); skew=fix-induced; action=none — H1 converged at round 3 of 3 (docs-only LOWs, no MED+)
- 2026-09-28 round 56 (H2, /simplify over Phases 1–8 seeded by round 53 lens f; smoke-time routing): 0 CRIT / 0 HIGH / 2 MED / 14 LOW; 3 LOW applied behaviour-neutral (SIMP-001 dead `ContextReporter` members; SIMP-002 the panel's Checking text from `CHECKING`; SIMP-003 stale comments), 13 recorded to task H2a for a scoped /review-plan after the smoke (SIMP-006 the product-name split is the practitioner's call); skew=none; action=none
- 2026-09-28 round 57 (H3, /security-review over Phases 1–8 via five read-only lens subagents, seeded by H1's carry-forward; smoke-time routing): 0 CRIT / 0 HIGH / 0 MED / 21 LOW + 1 record-only; 8 applied (SEC-001 host type guard; SEC-002 pipe server survives a connect-and-close; SEC-004 `dev` script removed; SEC-005 docs; SEC-006 bfcache re-hello; SEC-010 credential tripwire markers; SEC-011 a deleted booking no longer refuses the note; SEC-012 tests off the real logs), 13 recorded to task H3a (the call rate, enrolment on lock, the unlock query, suspend during Start, hidden-block Discard, pipe owner/label/writer/serve-end, mutex, URL forms, live-view tag), SEC-018 write-back freshness confirmed record-only for the write plan; skew=none; action=none
- 2026-09-28 round 58 (codex gpt-6-astra medium, pass stage-9.p1 H4 slice A): 0 CRIT / 0 HIGH / 0 MED / 3 LOW; fixed (PR-LOW-310 copy no longer "ships disabled"; PR-LOW-311 typed editing cross-referenced; PR-LOW-312 learned rules named as app-written config — docs only); skew=pre-existing; action=none
- 2026-09-28 round 59 (codex gpt-6-astra medium, pass stage-9.p1 H4 slice B): 0 CRIT / 0 HIGH / 0 MED / 1 LOW; fixed (PR-LOW-320 the encounter-read docstrings name their three callers, the executor's `adopt_queued` sibling included; SEC-022 assessed LOW, stays in H3a); skew=pre-existing; action=none
- 2026-09-28 round 60 (codex gpt-6-astra medium, pass stage-9.p1 H4 slice C): 0 CRIT / 0 HIGH / 1 MED / 2 LOW; fixed (PR-MED-330 the side panel's timer updates in place, focus and a straddling click survive, same-session focus restore, click-time refs, plus the Ready tick sibling; PR-LOW-331 "On screen" names a patient only for the focused note; PR-LOW-332 the three one-click desktop Discards named — doc only); skew=pre-existing; action=none — scoped confirmation round 61 follows
- 2026-09-28 round 61 (codex gpt-6-astra medium, pass stage-9.p1 H4 confirmation, peer round 4 of 5): 0 CRIT / 0 HIGH / 0 MED / 1 LOW; fixed (PR-MED-330, PR-LOW-331 and the five docs fixes confirmed closed; PR-LOW-340 the different-session focus test made discriminating — one sequence, same-session keeps focus then a new session clears it; test only); skew=fix-induced; action=none — H4 pass stage-9.p1 converged
- 2026-09-28 round 62 (practitioner live smoke S1, fixed by executor leg stage-9-exec-k7, claude-opus-5-5): 0 CRIT / 0 HIGH / 0 MED / 1 LOW; fixed (LOW-060 the Recovery tab's Unreviewed list re-lists when a Start retires a recording and when the tab is opened — stat-only, custody exclusion unchanged; +3 tests; in-session review pass clean); skew=pre-existing; action=none

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

### Round 25 - 2026-09-27 - Phase 4 (Tasks 4.1, 4.2, 4.4, 4.5: protocol v2, the named pipe, the host's relay, the Chrome bridge), `/review-loop` round 1 of cap 3

- Round status: Closed (0 pending) — 1 MED + 3 LOW, all Fix-now, all applied in this leg; pytest and vitest owed to the composer
- Source: Claude Code (executor leg stage-4-exec-d3, claude-opus-5-5, sequential lenses in-session — no subagents)
- Scope / baseline: the whole Phase 4 working-tree diff over `7a6cbd7` — `protocol.py`, `extension/src/protocol.ts`, `connection.ts`, `pipe_server.py`, `pipe_client.py`, `native_host.py`, `ui/bridge.py` (each read in full); `framing.py`, `session.py`, `encounter.py` (`VerificationLedger`, `reverification_request`), `logging_setup.py`, `app.py`, `ui/main_window.py`, `ui/session_screen.py`, `ui/models.py` (the changed hunks); `test_ui_bridge.py` (read in full), `test_protocol.py`, `test_native_host.py`, `test_framing.py` and the fixture layout (`protocol/fixtures/`, README, `meta.json`); the threat model's Chrome-link section, flow 19, CHANGELOG parts 1 and 2. Composer suites on the pre-round (d2) tree: desktop 3527 passed, extension 102 passed.
- Lenses and results:
  - Protocol v2 mirror parity — payload models CLEAN (every closed key set, shape rule, bound and text pattern agree line for line; Python's `$` is the Rust engine's end-of-text, so no trailing-newline gap). Found LOW-021 in the ENVELOPE's own fields.
  - Pipe security attributes — CLEAN: `FILE_FLAG_FIRST_PIPE_INSTANCE`, one instance, `PIPE_REJECT_REMOTE_CLIENTS`, `D:P(A;;GA;;;<SID>)`, `bInheritHandle` False; a held name is `name_taken` and the bridge says unavailable; a squatter of another user fails the session or user check, one with another DACL the DACL check, one whose DACL shuts the host out is `access_denied` — all `ServerUnverified`, none retried.
  - Overlapped I/O and stop — CLEAN on the wait paths (every wait includes the stop event, each thread cancels only its own I/O, short reads looped by `framing`, a zero-byte completion re-reads, stop is terminal). Found LOW-020 (an exception no reader catches ends a reader THREAD silently).
  - The host's (b) verification and the relay — CLEAN: identity read from the connected handle before any frame; every failure a typed `internal` error and exit 1; nonce stripped toward the app and stamped toward Chrome; both directions re-validated; nothing relayed is logged (types, states, paths only); EOF exits 0 after stopping the relay; one announcement per absence; a gone Chrome ends the relay.
  - The bridge — `session_ref` before the slot, `pause` ref-free, Phase 5 actions refused, `start` only against the bound, checked note, stale ledger results dropped by `(conn_gen, seq, target, clinic_rev)`: CLEAN. Found MED-018 (the live re-check's waiting slot) and LOW-019 (the re-check's result outlives its session).
  - Network confinement — CLEAN: no socket in any new module (named pipes only; the no-sockets legs cover the host relay and the app pipe); `cliniko_client` importers unchanged (`TestConfinement`).
  - Docs as control claims — the threat model's PROTOCOL residue (2) ("Python refuses the float") and both mirrors' headers ("Integers are JSON integers"; "Lengths count code points") overstated for the envelope → LOW-021; THE BRIDGE's "the name … goes when that session ends" overstated → LOW-019. Every other residue named; no other claim beyond the code.
- Findings:
  - **[MED]** MED-018: `desktop/src/scribe_desktop/ui/bridge.py` `_dispatch` / `_finish_task` — one waiting slot served both the ledger's report checks and the linked live session's reconnect re-check, latest wins: with a check in flight at reconnect (e.g. an offline check waiting out its 30 s deadline), the re-check queued, then the new connection's first report replaced it — so it NEVER ran; the Session screen said "Checking the note with Cliniko again…" for the rest of the session and `live_reverification()` stayed None, against the module docstring's and the threat model's "re-verified on every new connection". Separately, a re-check result whose check had been replaced or cleared fell through to `VerificationLedger.accept` (harmless only because matching tags imply the same note, clinic and rev) — materiality=behavioral surface=production — Triage: Fix-now; Decision: Applied — one waiting slot per KIND (`_waiting`, `_waiting_live`; each replaced only by its own kind; `_finish_task` runs the bound report's first, then the re-check only while it is still the current check); `_run(…, live=)` records the kind and `_on_verified` routes by it — a re-check result is applied only to the current check by identity and never offered to the ledger; `_reset_connection` drops both waiting requests (they answer the old connection). Tests: `TestLiveSession::test_a_report_check_never_displaces_the_live_recheck` (a gated check in flight, reconnect, the new report: the re-check still runs and verifies on the new `conn_gen`, the report too), `::test_a_recheck_answering_after_its_session_ended_is_dropped` (a spy on `accept`: never offered).
  - **[LOW]** LOW-019: `ui/bridge.py` `_tick` — `_live_display` (the name) was dropped when its session ended, but `_live_check.result` — a `Verified` outcome whose `NoteDisplay` carries the same patient's name — stayed until the next connection or linked Start, against "is held in memory for the live session it was verified for, and goes when that session ends" (module docstring, threat model THE BRIDGE, CHANGELOG) — the round-15 MED-006 / round-20 LOW-013 retention class — Triage: Fix-now; Decision: Applied — `_tick` drops `_live_check` on the same `ended(session_id)` rule as `_live_display`; the module docstring says so. Test: `TestLiveSession::test_the_recheck_goes_when_its_session_ends`.
  - **[LOW]** LOW-020: `desktop/src/scribe_desktop/framing.py` `read_frame` — a frame within the 1 MB bound nested past the interpreter's limit (`[[[…]]]`) makes `json.loads` raise `RecursionError`, which no reader caught: since Task 4.4 the host reads Chrome on a stdin THREAD (the thread died and the main loop waited forever — no error, no exit) and the relay and the app read the pipe on threads (the relay thread died with its link still set; the app's pipe thread died, closing the pipe while the bridge still said connected) — materiality=behavioral surface=production (a same-user sender or a broken peer only) — Triage: Fix-now; Decision: Applied — at the root, `read_frame` maps `RecursionError` to `FramingError("malformed")`, the fault every reader already handles (host: typed error + exit 1; relay and app: that connection closes). Tests: `test_framing.py::test_json_nested_past_the_recursion_limit_is_a_framing_fault`, `test_native_host.py::test_loop_deeply_nested_json_is_a_typed_error_not_a_hang`.
  - **[LOW]** LOW-021: `protocol.py` `Envelope.protocol_version` + `native_host._classify_raw` + `extension/src/protocol.ts` `parseEnvelope` — the envelope's own fields escaped v2's parity rules (pre-existing since v1; the v2 docs made the claim): Python's lax `int` accepted `"2"` (TypeScript: `malformed`) and a fraction-free float, and the host's pre-check classified `true` as `version_below_floor` (`True < 2`; TypeScript: `malformed`); TypeScript counted `request_id` / `session_nonce` in UTF-16 units (Python: code points) — against "Integers are JSON integers … this one refuses [the float]", "Lengths count code points, as Python's len() does", the README and the threat model's PROTOCOL residue (2) — materiality=behavioral surface=production (mirror parity) — Triage: Fix-now; Decision: Applied — `protocol_version: StrictInt`; `_classify_raw` skips a boolean; TypeScript counts both envelope strings in code points. Fixtures (both mirrors): `invalid/version_string.json`, `invalid/version_boolean.json`, `valid/ping__astral_request_id.json` (100 astral characters: 200 UTF-16 units, refused by the old TypeScript); README shapes paragraph. Test: `test_native_host.py::test_loop_a_non_integer_version_is_malformed` (true, false, "2", 2.5 → `malformed`).
- Verification counts: 7 lenses run, 4 candidates, 0 dropped, 0 downgraded
- Missed-issue pass (auditable): re-read `bridge.py` `_on_context` / `_start` / `_live_state` / `publish` after the fixes (the `_running_live` flag is read before `_finish_task` resets the run; a dropped re-check leaves `_waiting` to run), `pipe_server._serve` teardown order and `AppRelay.stop` against `_run`'s lock — no new candidate. [Round 26 found one regression this pass missed: LOW-022, below.]
- ruff clean; mypy 46 files; extension typecheck + lint clean; pytest and vitest owed to the composer (expected desktop 3527 + 12 = 3539 — 9 new tests plus 3 fixture cases in `test_protocol.py`'s parametrised fixture tests; extension stays 102 — its fixture tests loop inside one test each, so the three fixtures add assertions, not tests) [CORRECTED round 26: the composer's run gave 105 — `protocol.test.ts` builds one vitest case PER fixture (`for … test(file, …)` inside each `describe`), so the three fixtures are three cases; the 102 was my misreading, no unintended test]
- Last reviewed: 2026-09-27

### Round 26 - 2026-09-27 - Phase 4 round-25 fixes, `/review-loop` round 2 of cap 3 (post-fix regression check)

- Round status: Closed (0 pending) — 4/4 round-25 fixes confirmed; 1 LOW (fix-induced, from MED-018's fix), Fix-now, applied in this leg; pytest owed to the composer
- Source: Claude Code (executor leg stage-4-exec-d4, claude-opus-5-5, sequential lenses in-session — no subagents)
- Scope / baseline: the round-25 fix sites, then a missed-issue pass over the whole Phase 4 working-tree diff over `7a6cbd7` with round 25's lenses (protocol mirrors, pipe attributes, overlapped I/O and stop, the host's verification and relay, the bridge, network confinement, docs as control claims). Composer suites on the pre-round (d3) tree: desktop 3539 passed, extension 105 passed (see the count correction in round 25).
- Lenses and results:
  - Post-fix verification — MED-018 CONFIRMED (`_dispatch` routes by kind into `_waiting` / `_waiting_live`; `_finish_task` runs the report's first and the re-check only while `request is self._live_check.request`; `_on_verified` reads `_running_live` before `_finish_task` and applies a re-check result only by identity, never via `VerificationLedger.accept`; a reconnect's old running re-check is dropped because `_reverify_live` replaced the check; the two tests fail on the d2 code — the first leaves `live_reverification()` None). LOW-019 CONFIRMED (`_tick`'s `ended()` drops `_live_check` on the same rule as `_live_display`; `view()` and `live_reverification()` already required the same session). LOW-020 CONFIRMED (`RecursionError` → `FramingError("malformed")` inside `read_frame`, so all three reader threads — host stdin, relay, app pipe — see the fault they already handle; the host test proves hello_ack then a typed error and exit 1 instead of a hang). LOW-021 CONFIRMED (`StrictInt`; `_classify_raw` excludes `bool`; TypeScript counts both envelope strings in code points; the composer's 105 shows the three fixtures ran as their own cases on the TypeScript side, and 3539 on the Python side).
  - Post-fix regression — found LOW-022 (below): MED-018's fix also cleared the waiting re-check in `_reset_connection`, which runs on a bare DISCONNECT too.
  - Missed-issue pass — CLEAN over the whole surface: the relay's `forward` / `_run` close race (`PipeConnection.write_frame` and `close` share one lock and `_closed`); `forward`'s `make_pipe_envelope` cannot raise (the Chrome envelope's payload already passed the same payload model); `_start` clearing `_live_check` leaves any waiting re-check to be skipped by identity; the patient name reaches `state` only from `_live_display` (a Verified Start) or the bound report's `Verified` outcome; no socket, no new Cliniko importer.
- Findings:
  - **[LOW]** LOW-022: `ui/bridge.py` `_reset_connection` — round 25's MED-018 fix set `_waiting_live = None` there, but `_reset_connection` also runs on `_on_disconnected`: a re-check waiting behind a running check when the client went away was dropped, and — with no reconnect — the Session screen said "Checking the note with Cliniko again…" and `live_reverification()` stayed None until Chrome came back (the pre-fix code let it run). A re-check answers its SESSION, not the connection: a reconnect already replaces it (`_reverify_live`), and `_finish_task` skips one no longer current — skew=fix-induced, materiality=ux surface=production — Triage: Fix-now; Decision: Applied — `_reset_connection` clears only the report's waiting check; the comment says why. Test: `TestLiveSession::test_a_disconnect_does_not_strand_a_waiting_recheck` (a gated check in flight, reconnect, disconnect, release: the re-check runs and the Session screen says verified).
- Verification counts: 3 lenses run (4 fix checks + the regression check + the missed-issue pass), 1 candidate, 0 dropped, 0 downgraded
- ruff clean; mypy 46 files; no extension change; pytest owed to the composer (expected desktop 3539 + 1 = 3540; extension stays 105)
- Last reviewed: 2026-09-27

### Round 27 - 2026-09-27 - Phase 4 pipe, protocol v2, relay and state publisher (protocol v2), independent cross-family codex peer review (pass stage-4.p1 slice A)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Slice A protocol mirrors, nonce and command contracts, framing, logging tripwire, and permitted fixtures/tests; static review only, no writes, tests, or network.
- **PR-MED-130** (MED, behavioral, `extension/src/protocol.ts:254`): JavaScript’s `$` anchor accepts a match immediately before a final newline, so the TypeScript validator accepts invalid values that the Python mirror’s default Rust regex engine rejects. Examples include patient ID `"1001\n"`, a 24-character session reference followed by `"\n"`, and patient name `"Alex\n"`. This breaks mirror parity and the digits-only, exact-reference-length, and control-free-display contracts. The same issue affects host, reason, timestamp, and array-item checks — Evidence: line 62 declares `ID_PATTERN = /^[1-9][0-9]{0,18}$/`; line 254 uses `!pattern.test(value)` without requiring a full-string match; line 261 similarly uses `!TEXT_PATTERN.test(value)`; line 285 uses `!item.test(entry)`. Python applies `StringConstraints(strict=True, pattern=ID_PATTERN)` at `desktop/src/scribe_desktop/protocol.py:127`. The existing control-character fixture tests `"Alex\nExample"`, which misses the terminal-newline case. Recommendation: Fix-now — require absolute end-of-input across all TypeScript pattern checks and add shared trailing-line-terminator fixtures covering these field classes. /fix decision: Rejected — invalid: ECMAScript's `$` without the Multiline flag matches only at end of input, so `/^[1-9][0-9]{0,18}$/.test("1001\n")` is false; no TypeScript pattern carries `m` (`protocol.ts:62-69`), and the Python mirror's Rust-engine `$` is end-of-text too — both already refuse a trailing newline (composer re-checked; `OWNERSHIP: auto-disposition`). No change.
- **PR-MED-131** (MED, behavioral, `desktop/src/scribe_desktop/framing.py:98`): An oversized decimal integer inside an otherwise size-compliant frame escapes as an untyped `ValueError`. With Python’s standard integer-string digit limit enabled, a JSON body containing a 5,000-digit integer exceeds that limit while remaining far below the 1 MiB frame bound. Consequently, malformed input can escape `read_frame` instead of following its documented typed-fault contract — Evidence: line 98 executes `return json.loads(text)`; the only decoding handlers are `except json.JSONDecodeError as exc:` at line 99 and `except RecursionError:` at line 101. The new regression test at `desktop/tests/test_framing.py:82` covers excessive nesting only. Recommendation: Fix-now — translate the decoder’s integer-conversion `ValueError` into `FramingError("malformed", ...)` with fixed text, and add a regression case for a within-bound frame exceeding the enabled digit limit. /fix decision: Fixed — `desktop/src/scribe_desktop/framing.py` `read_frame` now catches `ValueError` (which covers `JSONDecodeError` and the digit-limit error, as `cliniko_client.py:516` does) → `FramingError("malformed", "frame body is not valid JSON")`, fixed text and `from None`; the `RecursionError` branch is kept. Tests: `test_framing.py::test_an_integer_past_the_digit_limit_is_a_framing_fault` (limit pinned at 4300 and restored; no digits in the message) and `test_native_host.py::test_loop_an_integer_past_the_digit_limit_is_a_typed_error` (the stdin-thread leg: hello_ack, a typed `malformed` error, exit 1). Applied by Claude Code, 2026-09-27.
- Verification counts: 2 claims checked, 2 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-27

#### LEG 1 verified tuples (executor, leg stage-4-exec-d5)
- PR-MED-130 (peer labels: MED, behavioral, Fix-now) — materiality=invalid severity=verified: low surface=production rec=Reject (no change) — ECMAScript's `$` with the Multiline flag off matches ONLY at end of input (the Assertion `$` algorithm: without Multiline it succeeds only when the index equals InputLength), so `/^[1-9][0-9]{0,18}$/.test("1001\n")` is false. The line-terminator-before-end behaviour the finding describes is Python's `re` (and Perl's), not JavaScript's. No TypeScript pattern carries the `m` flag: `ID_PATTERN`, `HOST_PATTERN`, `SESSION_REF_PATTERN`, `REASON_PATTERN` and `TIMESTAMP_PATTERN` have no flags (`protocol.ts:62-67`) and `TEXT_PATTERN` has `u` only (`:69`); a grep finds no `/m` in `protocol.ts`. The Python side uses pydantic-core's default Rust engine (no `regex_engine` override anywhere in `desktop/src`), whose `$` is also end-of-text, so both mirrors already refuse `"1001\n"`. `"Alex\n"` fails both mirrors anyway, because `\n` is inside `TEXT_PATTERN`'s excluded C0 range.
  - Fix shape: none. Optional hardening at the peer's discretion is a single shared invalid fixture with a trailing `\n` on a digit-string id, to pin the parity; it would pass on both mirrors today.
- PR-MED-131 (peer labels: MED, behavioral, Fix-now) — materiality=behavioral severity=verified: low surface=production rec=Fix-now — CONFIRMED, and a sibling that round 25's LOW-020 "at the root" fix missed. CPython's default integer-string limit (4300 digits; this repo runs 3.12+, and nothing here sets `PYTHONINTMAXSTRDIGITS` or `-X int_max_str_digits` — grep) applies to `json.loads`, which parses a JSON integer through the int constructor. That raises a plain `ValueError`, not a `JSONDecodeError`. The repo already relies on this: `test_cliniko_client.py:280` (`int-over-digit-limit`, 5000 digits → `Malformed`, codex round 8 PR-LOW-013) and `cliniko_client.py:516` `except (ValueError, RecursionError)`. `framing.read_frame:97-105` catches only `JSONDecodeError` and `RecursionError`, so a 1 MB-compliant frame with a 5000-digit integer kills the same three reader threads as LOW-020:
    - the host's stdin thread, where `_read_stdin` catches EndOfStream / FramingError / OSError, leaving the main loop waiting forever;
    - the relay thread (`_pump`);
    - the app's pipe thread (`_read_loop`).

  The senders are those of LOW-020: a same-user process or a broken peer. The extension builds its frames with `JSON.stringify` from validated values, so the verified severity matches LOW-020's low.
  - Fix shape: `framing.read_frame` → `except (ValueError, RecursionError)` after the UTF-8 decode (`JSONDecodeError` is a `ValueError`) → `FramingError("malformed", "frame body is not valid JSON")` with fixed text, the wording of `cliniko_client.py:516`. Regression tests:
    - `test_framing.py`: a 5000-digit integer frame → `FramingError` `malformed`, pinning `sys.set_int_max_str_digits(4300)` and restoring it as the Cliniko test does;
    - `test_native_host.py`: the stdin-thread leg → hello_ack, a typed error and exit 1.
- Decision (leg stage-4-exec-d6, `/fix`): PR-MED-130 Rejected — invalid (no change); PR-MED-131 Applied as shaped (`framing.read_frame` `except ValueError`; framing + host stdin-leg tests).
- Fix-delta self-check: PASS — re-read the `read_frame` hunk (the `RecursionError` branch intact, `UnicodeDecodeError` still handled by its own earlier try) and both tests (the limit restored in `finally`)
- Cap verdict: raise +1 — production-behavioral — PR-MED-131 confirmed (`read_frame` lets the digit-limit `ValueError` kill a reader thread, the LOW-020 class's missed sibling); PR-MED-130 invalid (JavaScript `$` without `m` is end-of-input only).

### Round 28 - 2026-09-27 - Phase 4 pipe, protocol v2, relay and state publisher (pipe and host relay), independent cross-family codex peer review (pass stage-4.p1 slice B)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Slice B’s specified plan sections, pipe server/client, host/app/config diffs and tests; static reading only, no writes, tests or network.
- **PR-MED-140** (MED, behavioral, `desktop/src/scribe_desktop/native_host.py:278`): Relay shutdown closes the pipe handle before its reader has finished cancelling and settling pending overlapped I/O. Signalling the stop event does not establish that completion, and the connection’s close lock excludes writes but not reads. — Evidence: shutdown calls `link.close()` before `thread.join(timeout)`; `pipe_client.py:202` executes `win32file.CloseHandle(self._handle)`, while `pipe_server.py:320` calls `_cancel_own_io(self._handle, self._overlapped)` on the reader thread. That helper requires the handle for `CancelIo` and `GetOverlappedResult`. The real-reader test instead joins before closing (`test_pipe_client.py:256–259`). Recommendation: Fix-now — Keep the handle valid until the reader acknowledges cancellation/completion, then close it; add a deterministic test that delays reader cancellation during relay shutdown. /fix decision: Fixed — `native_host.py` `AppRelay.stop` no longer closes the link before the join. It sets the stop flag, calls `connector.stop()` (whose event releases the read) and joins; the relay thread closes its own link after `_pump` returns (`_run`). Only a thread that outlives the join timeout has its link closed from `stop`, logged as `relay_stop state=join_timeout`. `pipe_client.PipeConnection` gains a per-connection `retire` event, and `pipe_server._OverlappedReader` takes extra stop events (`*more_stops`), so the read waits on the connector's stop and the connection's retire. `PipeLink` gains `retire`, and its docstring says only the reader closes. Tests: `test_native_host_relay.py::TestRelay::test_on_stop_only_the_relay_thread_closes_the_link_after_its_read` is deterministic — the old order appended "closed" synchronously before the read settled — and asserts events `["settled", "closed"]`, closed by `scribe-host-relay`. `test_pipe_client.py::TestConnect::test_retire_releases_a_blocked_read_and_its_thread_closes` runs on a real pipe. `relay_fakes`: `FakeConnector.stop` releases its links' reads, as the real shared event does, and `FakeLink` records events and close threads. Applied by Claude Code, 2026-09-27.
- **PR-MED-141** (MED, behavioral, `desktop/src/scribe_desktop/native_host.py:294`): A failed or timed-out outbound write only logs a dropped message and leaves the connection active. A failed command receives neither a refusal nor a connection-loss indication; after a partially transmitted frame, later frames also reuse a stream whose framing is no longer assured. — Evidence: `if not link.write_frame(stripped.model_dump(exclude_none=True)):` only executes `log_event(self._logger, "relay_dropped", state="write_failed")`; `pipe_client.py:187–189` cancels a timed-out write and returns `False` without retiring the connection. `relay_fakes.py:181–183` always returns `True`, so the relay tests miss this branch. Recommendation: Fix-now — Treat a failed write as connection failure, settle outstanding I/O and reconnect or exit with a typed error; test write failure and partial-frame cancellation without replaying commands. /fix decision: Fixed — `native_host.py` `AppRelay.forward`: when a write fails or times out, it logs `relay_dropped state=write_failed` and calls `link.retire()`. The read settles and ends, the relay thread closes the link, Chrome hears `app_running:false`, and the relay reconnects, so the app sees a new connection and sends a full snapshot. The message is never retried or replayed. `PipeConnection.write_frame` also waits on the retire event. The module docstring's THE RELAY section says so. Test: `test_native_host_relay.py::TestRelay::test_a_failed_write_retires_the_connection_and_is_never_replayed` checks that `FakeLink(write_ok=False)` is retired, closed by the relay thread and followed by "not running"; that the second link receives nothing; and that `app_running` goes True → False → True. The real-pipe write timeout (5 s) is not reproduced; the retire mechanism is pinned on a real pipe by the PR-MED-140 test. Applied by Claude Code, 2026-09-27.
- **PR-LOW-142** (LOW, behavioral, `desktop/src/scribe_desktop/pipe_client.py:129`): The verification checks a protected, single-user ALLOW entry but does not enforce the exact DACL promised by Task 4.3: ACE flags and access masks are discarded. Different permissions for the same SID therefore pass the same identity comparison. — Evidence: `(ace_type, _flags), _mask, sid = dacl.GetAce(index)` followed by `entries.append((int(ace_type), str(win32security.ConvertSidToStringSid(sid))))`; `unverified_reason` compares only `(ACCESS_ALLOWED_ACE_TYPE, own_sid)`. Recommendation: Fix-now — Preserve and validate the ACE flags and normalized access mask against the app-created DACL, with differing-mask/flags regression cases; retain the accepted same-user residue. /fix decision: Fixed — `pipe_client.py`:
  - `_pipe_dacl` keeps `(type, flags, mask & 0xFFFFFFFF, sid)`.
  - `unverified_reason` requires exactly one entry equal to `(ACCESS_ALLOWED_ACE_TYPE, APP_ACE_FLAGS=0, mask ∈ APP_ACE_MASKS, own_sid)`. `APP_ACE_MASKS` is FILE_ALL_ACCESS `0x1F01FF` (what `GA` maps to when Windows creates the pipe) plus GENERIC_ALL (the same grant, unmapped).
  - `ServerIdentity.dacl_entries` is now 4-tuples.
  - The module docstring, the threat model's THE HOST'S RELAY section and the CHANGELOG say so.

  Tests (`test_pipe_client.py`):
  - the contract table gains `read_write_mask` and `inherit_flag` rows, and the positive case also accepts unmapped GENERIC_ALL;
  - the real app-pipe test pins that the observed mask is in `APP_ACE_MASKS` with flags 0;
  - a real squatter `D:P(A;;GRGW;;;{sid})` → `ServerUnverified("dacl")`.

  Same-user residue retained. Applied by Claude Code, 2026-09-27.
- Verification counts: 6 claims checked, 3 confirmed, 3 dropped as unverifiable
- Last reviewed: 2026-09-27

#### LEG 1 verified tuples (executor, leg stage-4-exec-d5)
- PR-MED-140 (peer labels: MED, behavioral, Fix-now) — materiality=behavioral severity=verified: low surface=production rec=Fix-now — CONFIRMED. `AppRelay.stop` (`native_host.py:266-278`) sets the stop flag, calls `connector.stop()` (setting the event the reader waits on) and then, on the MAIN thread, `link.close()` → `PipeConnection.close` → `CloseHandle` (`pipe_client.py:196-204`), before `thread.join`. Meanwhile the relay thread's `_OverlappedReader.read` (`pipe_server.py:319-321`) wakes on the stop event and calls `_cancel_own_io(self._handle, …)`, whose `CancelIo` and `GetOverlappedResult(…, True)` then run on a handle that may already be closed, or recycled to another object. The `pywintypes.error`s are swallowed, so the settle-before-release guarantee the helper exists for is lost. `PipeConnection.close` locks against writes only, not the read. Bounds on the impact:
    - it happens only at host shutdown (`run_host`'s `finally`, after Chrome's EOF or a fatal error), just before the process exits;
    - the OVERLAPPED stays alive on the reader, so the practical harm is a narrow handle-recycling race, not a data leak.

  The close is also unnecessary: the stop event alone releases the reader, and `_run` already closes the link itself once `_pump` returns (`native_host.py:331`).
  - Fix shape: `AppRelay.stop` stops closing the link before the join. It sets the flag, calls `connector.stop()` and joins; only if the join times out does it close the link as a last resort, logged. The relay thread stays the one closer on the normal path. Shared with PR-MED-141: a per-connection retire event added to the reader's wait, so a connection can be ended without closing its handle from another thread. Regression test (`test_native_host_relay.py`): a `FakeLink` whose `read_frame` blocks on the connector's stop, then records a "settled" mark after a short delay; `close` records a "closed" mark. The test asserts "closed" comes after "settled" and that `close` ran on the relay thread (`threading.current_thread().name`).
- PR-MED-141 (peer labels: MED, behavioral, Fix-now) — materiality=behavioral severity=verified: low surface=production rec=Fix-now — CONFIRMED. `AppRelay.forward` (`native_host.py:288-290`) only logs `relay_dropped state=write_failed` when `link.write_frame` returns False. `PipeConnection.write_frame` returns False after a timed-out write (5 s wait → `_cancel_own_io`, `pipe_client.py:184-189`) or a failed `WriteFile` / `GetOverlappedResult`, and the link stays current. A cancelled pending write on a byte-mode pipe can leave part of the frame delivered, after which the stream's framing is not assured. Bounds on the impact:
    - the app's `_read_loop` refuses what follows (length or JSON garbage → `framing` or `malformed` → that connection closes), so it self-heals rather than mis-acting — a desynchronised stream parsing as a valid envelope is implausible;
    - the triggering condition is rare: the app's pipe thread not draining for 5 s, which the GUI thread cannot cause, because the server reads on its own thread;
    - the dropped command gets no refusal, so the panel simply shows no change.

  `relay_fakes.FakeLink.write_frame` always returns True, so this branch is untested.
  - Fix shape: a failed write retires the connection. `forward` calls a new `link.retire()`, which sets a per-connection event included in the reader's wait (the PR-MED-140 mechanism). The reader then settles its I/O, and `_pump` returns `"write_failed"`. The relay thread closes the handle, announces `app_running:false` and reconnects, so the app sees a new connection: `conn_gen` bumps and a fresh full snapshot follows. The failed command is never replayed. Regression tests: a `FakeLink` with a scripted False write — the relay ends that connection, announces, reconnects, and the second link receives no copy of the dropped command. Plus a real-pipe case where a stalled server makes the write time out and the relay ends the connection rather than reusing it.
- PR-LOW-142 (peer labels: LOW, behavioral, Fix-now) — materiality=behavioral severity=verified: low surface=production rec=Fix-now — CONFIRMED. `_pipe_dacl` (`pipe_client.py:129`) drops `_flags` and `_mask`, and `unverified_reason` compares `(type, sid)` only, while the module docstring and the threat model's THE HOST'S RELAY say the DACL is "exactly the one the app creates". So a protected single ACE for the host's SID with a different mask (e.g. `GR` only) or different ACE flags passes the check. This has no security consequence beyond the accepted residue: only a SAME-user server passes the session and user checks first, and that server can copy the exact DACL anyway (pipe residue (2)). The gap is between the claim and the check.
  - Fix shape: keep `(ace_type, ace_flags, mask, sid)` and require `(ACCESS_ALLOWED_ACE_TYPE, 0, <the mask the app's `GA` ACE maps to>, own_sid)`. The expected mask is pinned from a real app-created pipe, not hard-coded from memory: `TestConnect`'s existing positive case proves the real `pipe_sddl` pipe passes. Regression tests: squatter pipes `D:P(A;;GR;;;{sid})` and `D:P(A;OI;GA;;;{sid})` → `ServerUnverified("dacl")`, plus the `unverified_reason` contract table extended with differing-mask and differing-flag rows. If the practitioner prefers, the smaller truthful change is the docs route: reword "exactly the one" to "protected, one ALLOW entry for the host's SID". The code change is recommended because it makes the stated contract literal at little cost.
- Decision (leg stage-4-exec-d6, `/fix`): PR-MED-140 and PR-MED-141 Applied as shaped (one per-connection retire event, and only the reading thread closes); PR-LOW-142 Applied via the code (type, flags, mask and SID compared; the mask set covers the mapped and unmapped `GA`).
- Fix-delta self-check: PASS — re-read the `AppRelay.stop` / `forward` hunks against `_run` (the relay thread still closes after `_pump` on every exit path, and `stopping` is set before `connector.stop()`, so no announce follows a stop), `PipeConnection.retire` / `write_frame` (retire on an already-closed link only sets its event), `_OverlappedReader`'s `*more_stops` (the pipe server's one call is unchanged), `_pipe_dacl` / `unverified_reason`, and the fakes (a released link's EOF is read at most once)
- Cap verdict: raise +1 — production-behavioral — PR-MED-140, PR-MED-141 and PR-LOW-142 all confirmed. Each is low-impact (shutdown-only; rare and self-healing; claim-vs-check with no consequence beyond the accepted residue), and 140 and 141 share one fix: a per-connection retire event, with the handle closed only by the relay thread.

### Round 29 - 2026-09-27 - Phase 4 pipe, protocol v2, relay and state publisher (bridge, UI and docs), independent cross-family codex peer review (pass stage-4.p1 slice C)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Slice C’s specified plan sections, bridge, UI/controller diffs, tests and security-documentation diffs; static reading only, no writes, tests or network commands.
- **PR-MED-150** (MED, behavioral, `desktop/src/scribe_desktop/ui/bridge.py:412`): Live reconnect verification bypasses D9’s clinic-revision guard. Replacing a key during verification can install an old-revision result; replacing it after completion leaves that result displayed as verified. This affects the reconnect status, not the separately guarded write-back path. — Evidence: `if check is not None and result.request is check.request:` immediately assigns `check.result = result`; `on_clinics_changed()` at lines 247–254 only invokes `self._ledger.reverify_after_clinic_change()`, leaving `_live_check` unchanged; `_recheck_line()` returns `"verified"` for that retained result at lines 703–704. Recommendation: Fix-now — Check the current clinic revision before accepting or exposing a reconnect result, invalidate/recheck it on clinic changes, and cover both pending and completed results with regression tests while preserving plain-disconnect survival. /fix decision: Fixed — `ui/bridge.py` gains `_rev_current(request)`, the ledger's `_current_clinic` rule: the clinic record still exists and its rev equals `request.clinic_rev`. It is applied in three places:
  - `_on_verified`, before installing a re-check result;
  - `live_reverification()`, which returns None for a void result;
  - `_recheck_line`, now an instance method, which never says "verified" under a moved rev.

  `on_clinics_changed` re-runs `_reverify_live` when the live check's request rev has moved. That is a new check on the same connection (`conn_gen` unchanged), or "clinic_gone" when the clinic was removed. The module docstring says so. LOW-022's disconnect survival is untouched. Tests (`test_ui_bridge.py::TestLiveSession`):
  - `test_a_recheck_in_flight_under_a_replaced_key_is_void_and_rerun`
  - `test_a_completed_recheck_is_void_after_a_key_change` (void at once, before any signal; then "checking"; then verified under the new rev)
  - `test_a_removed_clinic_voids_the_recheck_as_clinic_gone`

  Applied by Claude Code, 2026-09-27.
- **PR-LOW-151** (LOW, docs-only, `docs/security/threat-model.md:1596`): The bridge’s name-lifetime claim conflates the bound report with the live session. A verified report publishes its patient name before Start and can continue publishing it after the recording ends; flow 19 correctly describes these as separate retained values. — Evidence: The threat model says the name reaches `state`, “is held in memory for the live session it was verified for, and goes when that session ends”; `desktop/src/scribe_desktop/ui/bridge.py:539–542` sets `state["patient_name"]` whenever the report outcome is `Verified`, without requiring a session. Session-end cleanup at lines 653–659 clears `_live_display` and `_live_check`, not the bound report. Recommendation: Fix-now — Document the bound-report and live-session display lifetimes separately, matching flow 19 and the intended Ready-state display. /fix decision: Fixed — `docs/security/threat-model.md` THE BRIDGE now states TWO lifetimes:
  - the bound report's name, published while that verified report is bound, before and after a Start; no longer published once the report changes or its `clinic_rev` moves; held in the ledger's reuse entry until it is pruned (at the first dispatch after its 60 s window) or the connection ends;
  - the live session's name, from its Start and its reconnect re-check, dropped when the session ends.

  The paragraph also states the D9 void of the re-check (PR-MED-150). Sibling: the `ui/bridge.py` module docstring's DISPLAY paragraph was reworded to match. The CHANGELOG part-1 parenthetical is about the Session screen's "Recording for" line, which shows only the live session's name, so it is accurate and unchanged. No code or test change. Applied by Claude Code, 2026-09-27.
- Verification counts: 2 claims checked, 2 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-27

#### LEG 1 verified tuples (executor, leg stage-4-exec-d5)
- PR-MED-150 (peer labels: MED, behavioral, Fix-now) — materiality=behavioral severity=verified: med surface=production rec=Fix-now — CONFIRMED. `_on_verified` applies a re-check result by identity alone (`bridge.py` `check.result = result`), never comparing `result.request.clinic_rev` with the clinic's current rev. `on_clinics_changed` (`bridge.py:247-254`) re-dispatches only the ledger's bound report and leaves `_live_check` untouched. `_recheck_line` then returns `"verified"` for the retained result, so after a Replace key or Remove the Session screen can still say "Cliniko verified the note again after Chrome reconnected", in two cases:
    - a result that was in flight under the OLD rev lands after the change;
    - a result that was already applied stays shown.

  That is against D9 ("Replace and Remove also clear that clinic's current verification outcome"), which the ledger honours via `_current_clinic` and the re-check does not. The write path is NOT affected. `live_reverification()` can hand back an old-rev result, but `writeback_context` already refuses one dispatched under a non-current rev (`reverification_stale`, MED-012 / round 20), and nothing consumes it until the write-back plan. Severity is med because it breaks an explicit decision contract and shows a false verified status after a key change or clinic removal, though it opens no gate.
  - Fix shape (`ui/bridge.py`):
    - `_on_verified` applies a re-check result only while its clinic still exists at `request.clinic_rev` (`clinics.record(...)` and `clinics.rev(...)`, as `VerificationLedger._current_clinic` does);
    - `live_reverification()` and `_recheck_line` treat a held result whose rev has moved as absent;
    - `on_clinics_changed` also re-runs `_reverify_live`'s request step for the CURRENT live session, without bumping `conn_gen`: a new `_LiveCheck` under the current rev, or `request=None` → "clinic_gone" when the clinic was removed, dispatched `live=True`.

    Keep LOW-022's survival: `_reset_connection` still leaves the waiting re-check. Regression tests in `TestLiveSession`:
    - pending: a gated re-check, a Replace key (rev bump), then release → not applied, and a fresh check under the new rev runs and verifies;
    - completed: a verified re-check, then a rev bump → the line is no longer "verified" and a new check is dispatched;
    - removed clinic → "clinic_gone".

    `test_a_disconnect_does_not_strand_a_waiting_recheck` must stay green.
- PR-LOW-151 (peer labels: LOW, docs-only, Fix-now) — materiality=docs-only severity=verified: low surface=docs rec=Fix-now (doc) — CONFIRMED. The threat model's THE BRIDGE paragraph says the name "is held in memory for the live session it was verified for, and goes when that session ends". Yet `_report_state` publishes `patient_name` from the bound report's `Verified` outcome with no session at all (the Ready state before Start, and after the recording ends while that report stays bound). That value lives in `VerificationLedger`'s run and its 60 s reuse entry until the report changes, the window passes or the connection ends. Flow 19 (`data-flow-map.md:607-613`) already describes the two values separately. Round 25's LOW-019 fixed the live-session half and left the sentence conflating the two.
  - Fix shape (docs): split the sentence in `threat-model.md` THE BRIDGE into two lifetimes:
    - the bound report's name, published while that verified report is bound and dropped with the report, the reuse window or the connection;
    - the live session's name, held for the session started from it and dropped when it ends (plus its reconnect re-check, LOW-019).

    Sibling sweep: the `ui/bridge.py` module docstring's DISPLAY paragraph (same wording) and the CHANGELOG part-1 parenthetical. No code or test change.
- Decision (leg stage-4-exec-d6, `/fix`): PR-MED-150 Applied as shaped (`_rev_current` at install, read and display; `on_clinics_changed` re-runs the re-check on the same connection); PR-LOW-151 Applied via the doc (two lifetimes; the bridge docstring's sibling reworded).
- Fix-delta self-check: flagged-and-fixed in-leg — my first rewrite of the threat-model sentence said the bound report's name "goes with … the ledger's 60 s reuse window", which overstated it: the reuse entry is pruned only at the next dispatch. It was reworded before the leg ended to "no longer published once the report changes or its rev moves; held in the reuse entry until pruned (at the first dispatch after its window) or the connection ends". Rest: PASS — re-read `_rev_current` and its three uses, `on_clinics_changed` (a check with `request=None` is not re-run: a removed clinic's re-add gets a new id), and the three tests
- Cap verdict: raise +1 — production-behavioral — PR-MED-150 confirmed: the reconnect re-check ignores D9's `clinic_rev` and can show "verified" under a replaced or removed key, with the write path still guarded by MED-012. PR-LOW-151 is a docs-only confirmation of the conflated name-lifetime sentence.

### Round 30 - 2026-09-27 - Phase 4 pipe, protocol v2, relay and state publisher (confirmation of rounds 27-29), independent cross-family codex peer review (pass stage-4.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Scoped confirmation of rounds 27–29 using only permitted files; static reading, no writes, tests or network.
- **PR-LOW-160** (LOW, behavioral, `desktop/src/scribe_desktop/native_host.py:298`): PR-MED-140 remains incomplete on shutdown timeout: the stopping thread closes the handle while the reader may still be settling overlapped I/O. The timeout establishes no completion guarantee, contradicting the new “only the relay thread closes” contract. — Evidence: `thread.join(timeout)` at line 291 falls through when the thread remains alive to `link.close()` at line 298; `desktop/src/scribe_desktop/pipe_server.py:321` still settles using `_cancel_own_io(self._handle, self._overlapped)`. The test at `desktop/tests/test_native_host_relay.py:258` exercises ordinary shutdown without holding settlement past the timeout. Recommendation: Fix-now — Leave closure with the reader even after timeout; add a gated timeout regression asserting the handle stays open until settlement. /fix decision: Fixed — `desktop/src/scribe_desktop/native_host.py` `AppRelay.stop` never closes the link. On a join timeout it logs `relay_stop state=join_timeout` and returns False. The handle goes with its reader once the read settles or, at the latest, at process exit, when Windows cancels a terminating thread's pending I/O and closes the process's handles; `run_host` returns right after. The docstrings (`stop`, the module's THE RELAY section), the threat model's THE HOST'S RELAY paragraph and CHANGELOG part 2 now state the rule as a class. Test: `test_native_host_relay.py::TestLinkOwnership::test_a_stop_that_times_out_never_closes_the_link`. A `FakeLink(settle_gate=…)` holds the read's end, `stop(timeout=0.05)` returns False with `close_threads == []`, and after the gate opens the relay thread closes: events `["settled", "closed"]`, closed by `scribe-host-relay`. The pre-fix code closed from `MainThread`. `relay_fakes.FakeLink` gains `settle_gate`. Applied by Claude Code, 2026-09-27.
- **PR-MED-161** (MED, behavioral, `desktop/src/scribe_desktop/pipe_client.py:214`): PR-MED-141’s retirement does not prevent subsequent writes before the relay reader closes the connection. Another queued Chrome command can therefore write onto the potentially partial frame’s stream. Waiting on the retire event after issuing `WriteFile` is too late to prevent transmission. — Evidence: `native_host.py:317` calls `link.retire()`, but `_link` is cleared only after `_pump` returns at lines 355–357; `pipe_client.py:214` checks only `if self._closed:` before `win32file.WriteFile(self._handle, buffer.getvalue(), overlapped)` at line 218. The retire event appears only in the subsequent wait at line 222. `test_native_host_relay.py:291` sends just one command before waiting for disconnection. Recommendation: Fix-now — Refuse writes to retired connections before issuing I/O, synchronized with retirement; add a regression holding the reader open while a second command arrives, asserting no second write occurs. /fix decision: Fixed — two layers:
  - `pipe_client.py` `PipeConnection.write_frame` refuses under its lock BEFORE any `WriteFile` when the connection is closed or `_ended()`, i.e. its retire or the connector's stop event is already signalled (`WaitForSingleObject(event, 0)`). `retire()` stays a lock-free `SetEvent`, so a write blocked in its wait still sees it; the one writer is also the one retirer.
  - `native_host.py` `AppRelay.forward` clears `self._link` under the relay lock when it retires that link, so a later message drops as `app_not_connected` before reaching it.

  Docstrings (the class and `_ended`, the module's THE RELAY section), the threat model and the CHANGELOG say so. Tests:
  - `test_native_host_relay.py::TestLinkOwnership::test_after_a_failed_write_no_later_message_reaches_that_link`: with the retired link's read held, a second command plus a ping gives `written` exactly one entry and no close; after release, the relay thread closes and "not running" follows;
  - `test_pipe_client.py::TestConnect::test_a_retired_or_stopped_connection_writes_nothing[retire|stop]`: on a real pipe, the write returns False while the connection is still open, and the server receives no message.

  Applied by Claude Code, 2026-09-27.
- Confirmations: PR-MED-131 CONFIRMED — fixed-text `ValueError` translation and the pinned 5,000-digit regression fail appropriately on pre-fix code (`framing.py:99`, `test_framing.py:96`); PR-MED-140 NOT CONFIRMED in full — normal shutdown ordering is corrected, but PR-LOW-160 remains; PR-MED-141 NOT CONFIRMED in full — failed-write retirement, reconnect and no replay are covered by a non-vacuous test, but PR-MED-161 permits stream reuse; PR-LOW-142 CONFIRMED — flags and normalized masks are checked, differing-permission cases discriminate against pre-fix behavior, and same-user residue remains documented (`pipe_client.py:125`, `test_pipe_client.py:115`, `test_pipe_client.py:220`); PR-MED-150 CONFIRMED — revision guards cover installation, retrieval and display, replacement triggers a fresh check, and plain disconnect preserves the waiting slot; the pending/completed/removal regressions discriminate against pre-fix code (`ui/bridge.py:251`, `ui/bridge.py:274`, `ui/bridge.py:442`, `ui/bridge.py:732`, `test_ui_bridge.py:688`); PR-LOW-151 CONFIRMED — the revised documentation separates bound-report and live-session names consistently with flow 19 and bridge publication/cleanup (`ui/bridge.py:554`, `ui/bridge.py:678`); PR-MED-130 rejection CONFIRMED — the TypeScript patterns have no multiline flag, `$` requires end of input, and the text character class excludes newline (`extension/src/protocol.ts:62`, `extension/src/protocol.ts:69`).
- Verification counts: 2 claims checked, 2 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-27

#### LEG 1 verified tuples (executor, leg stage-4-exec-d7)
- PR-LOW-160 (peer labels: LOW, behavioral, Fix-now) — materiality=behavioral severity=verified: low surface=production rec=Fix-now — CONFIRMED, and this is my own PR-MED-140 fix left incomplete. `AppRelay.stop` (`native_host.py:291-298`) falls through, after `thread.join(timeout)`, to `link.close()` on the stopping thread whenever the relay thread is still alive. At that moment the reader may be inside `_cancel_own_io` (`pipe_server.py:320-321`), which is the very race PR-MED-140 closed, and it contradicts the `PipeConnection` docstring's "only the READING thread closes … and never with `close`". The failing branch is narrow. After `connector.stop()`, a read settles at once, and the relay thread blocks elsewhere only briefly: in `WaitNamedPipe` (at most `WAIT_MS` = 1 s) or in a Chrome-side write, which fails fast because Chrome has gone. So a 5 s timeout needs a stuck kernel call. The close adds nothing even then. `run_host` returns just after `stop`, and at process exit Windows cancels a terminating thread's pending I/O and closes every handle the process owns. With no close from `stop`, the handle is released either by the reader once it settles or by the OS at exit, never by a thread that does not own the read.
  - Fix shape: `AppRelay.stop` never closes the link. On a join timeout it logs `relay_stop state=join_timeout` and returns False, leaving the handle to its reader or to process teardown; the docstring says that and names the process-exit release. Regression test (`test_native_host_relay.py`): a `FakeLink` option that holds `read_frame` on a test gate and ignores the connector's release. `relay.stop(timeout=0.05)` returns False, and the fake's `close_threads` is empty, so the stopper never closed it. Opening the gate then lets the read settle, and `close_threads == ["scribe-host-relay"]` with events `["settled", "closed"]`. Deterministic: a gate, not a sleep race.
- PR-MED-161 (peer labels: MED, behavioral, Fix-now) — materiality=behavioral severity=verified: low surface=production rec=Fix-now — CONFIRMED, and this is my own PR-MED-141 fix left incomplete. After `forward` calls `link.retire()` (`native_host.py:317`), the link stays in `AppRelay._link` until the relay thread's `_pump` returns and clears it (`_run`). Meanwhile `PipeConnection.write_frame` (`pipe_client.py:213-218`) checks only `self._closed` before `WriteFile`; the retire event is consulted only in the wait that follows. So a second Chrome message, drained by the main loop in that window, is written onto the stream that may hold a partial frame. That contradicts the docstring and threat-model "never followed on the same stream". Verified severity low, not med:
    - the window is the reader's wake, cancel and settle — short;
    - the app's `_read_loop` refuses a desynchronised stream as `framing` or `malformed` and closes the connection, so the misframed bytes are never acted on; a length prefix landing on JSON bytes is implausible to parse into a valid envelope;
    - the connection is being abandoned anyway.

  It is a real hole in the stated contract, and cheap to close.
  - Fix shape, one shape shared with PR-LOW-160 — ownership of the handle's I/O stays with the connection's own synchronisation:
    - `PipeConnection.write_frame` refuses BEFORE issuing I/O, under its lock, when the connection is closed or its retire or stop event is already signalled (`WaitForSingleObject(event, 0) == WAIT_OBJECT_0`) → False and no `WriteFile`. `retire()` stays a lock-free `SetEvent`, so a write blocked in its 5 s wait still sees the event. The only writer and the only retirer are the same (main) thread, so check-then-write has no interleaving; the event, not the lock, is the synchronisation.
    - Belt: `AppRelay.forward` clears `self._link` under the relay lock when it retires that link (`if self._link is link`), so later messages drop as `app_not_connected` before reaching the link. `_run` still closes its own local reference.

    Regression tests:
    - `test_native_host_relay.py`: `FakeLink(write_ok=False)` with `read_frame` held on a gate, so retirement cannot finish. Send two commands; the first write fails and retires; the second never reaches the link (`written` has exactly one entry and `relay_dropped` shows `app_not_connected`). Release the gate and the relay thread closes and reconnects as before.
    - `test_pipe_client.py::TestConnect`, a real pipe: `retire()`, then `write_frame` returns False and the server's recorder receives no message, while the connection is still open (no reader closed it). The same after `connector.stop()`.
- Decision (leg stage-4-exec-d8, `/fix`): PR-LOW-160 and PR-MED-161 Applied as shaped. The stopper never closes, even on a timeout, and the handle goes with its reader or at process exit. `write_frame` refuses before any I/O once retired or stopped, and `forward` makes the retired link non-current at once. The ownership rule is restated as a class in both modules' docstrings, the threat model and the CHANGELOG.
- Fix-delta self-check: PASS — re-read four things:
  - `AppRelay.stop`: no close on any path; the relay lock is no longer taken there.
  - `forward`: the clear is guarded by `self._link is link`, so a newer link set by `_run` is never cleared; `_run` still clears and closes its own reference after `_pump`.
  - `PipeConnection._ended` and `write_frame`: `_WAIT_OBJECT_0` is 0, and the check sits inside the lock before `_new_overlapped`.
  - The three tests: gates, not sleeps; each pre-fix failure is deterministic — `close_threads == ["MainThread"]`, two `written` entries, and a real write reaching the server.
- Cap verdict: raise +1 — production-behavioral — both confirmed as incomplete halves of my own PR-MED-140/141 fixes: the stopper still closes on a join timeout, and a retired link still accepts a write before its reader ends it. Both are low and share one ownership shape: the reader or process exit closes; `write_frame` refuses once retired or stopped. The fix leg plus a confirmation needs peer_round 5 of 5, with no headroom if the confirmation finds anything, hence +1.

### Round 31 - 2026-09-27 - Phase 4 pipe, protocol v2, relay and state publisher (confirmation of round 30), independent cross-family codex peer review (pass stage-4.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Scoped static confirmation of round 30’s two fixes, regression tests, ownership documentation and introduced regressions; no writes, tests or network.
- Confirmations: PR-LOW-160 CONFIRMED — `AppRelay.stop` ends with `"relay_stop", state="join_timeout"` and `return False`, without closing (`desktop/src/scribe_desktop/native_host.py:300`); closure remains after `_pump` (`desktop/src/scribe_desktop/native_host.py:367`). The gated regression asserts `link.close_threads == []` before releasing settlement (`desktop/tests/test_native_host_relay.py:328`), which the previous timeout-close path would fail. PR-MED-161 CONFIRMED — `if self._closed or self._ended(): return False` precedes I/O under the connection lock (`desktop/src/scribe_desktop/pipe_client.py:225`). Retirement and stop remain lock-free signals; exclusion from write initiation relies on the actual host’s single main-thread ordering, not event checks being atomic with `WriteFile`. That thread writes, retires and performs final shutdown. `forward` clears the matching retired link (`desktop/src/scribe_desktop/native_host.py:323`). The gated second-command/ping regression checks exactly one write (`desktop/tests/test_native_host_relay.py:354`); the real-pipe regression checks refusal while still open and no received message (`desktop/tests/test_pipe_client.py:321`, `desktop/tests/test_pipe_client.py:326`). Both discriminate against pre-fix behavior without sleep-based race windows.
- Documentation and regression check: Ownership wording agrees across the docstrings, `docs/security/threat-model.md:1572` (“Only the relay thread closes”) and `CHANGELOG.md:11` (“a shutdown that times out closes nothing”). No introduced lock cycle, unintended owner-lifetime escape or missing typed refusal found; disconnected-message dropping remains the stated relay contract.
- Verification counts: 2 claims checked, 2 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-27

### Round 32 - 2026-09-28 - Phase 5 (Tasks 5.1–5.6: the pause rule, the resolution block, back-to-back, Open for review, the banner and `open_review`, the cross-patient matrix), `/review-loop` round 1 of cap 3

- Round status: Closed (0 pending) — 5 LOW, all Fix-now, all applied in this leg; pytest owed to the composer
- Source: Claude Code (executor leg stage-5-exec-e4, claude-opus-5-5, sequential lenses in-session — no subagents)
- Scope / baseline: the whole Phase 5 working-tree diff on top of the uncommitted Phase 4 tree over `7a6cbd7`:
  - read in full: `context_rules.py`, `ui/bridge.py`, `ui/recovery.py`, `ui/main_window.py`;
  - read as changed hunks or functions: `session.py` (`adopt_queued`, the D2 registry, `_retire_locked`, `start`, `custody_protected_ids`), `session_store.session_expires_at`, `ui/models.py` (the Phase 5 constants and the Unreviewed helpers), `ui/session_screen.py`, `ui/transcript.py`, `ui/note.py` (`show_saved_note`, `_copy_ready`, `_copy_note`, `clear`), `app.py`;
  - tests: `test_cross_patient.py`'s Phase 5 section, and the `test_ui_bridge.py`, `test_unreviewed_review.py` and `test_ui_pause_and_unreviewed.py` classes the lenses name;
  - docs: the threat model's PAUSE RULE and OPEN FOR REVIEW paragraphs, flows 6 and 19, retention's 24-hour rule, CHANGELOG parts 2 and 3.

  Composer suites on the pre-round (e3) tree: desktop 3912 passed, extension 105 passed.
- Lenses and results:
  - D5 — CLEAN:
    - `pause_action` is D5's table (RECORDING pauses and blocks for a context reason; PAUSED only blocks; others nothing; a Chrome reason is nothing for an unlinked session).
    - `ContextEvaluator` pauses on the bound tab's note, patient, leave or close, and on a focused other note or login; it re-binds only on exact ids.
    - `nativeEvent` returns `(False, 0)` inside a blanket catch.
    - `resume_refusal` needs a connection and the focused tab's current bound target equal to the session's; every Resume (button, Chrome, the Phase 7 hotkey slot) runs it first, and `_on_resumed` binds only the verified focused tab.
  - Resolution block — CLEAN:
    - the Session screen's Discard takes two clicks (see LOW-026), and Chrome's `discard` carries `confirmed`;
    - `resume_previous` needs the live ref and a PAUSED linked session, lapses at 30 s or on a new connection, and resumes only through `on_resume`'s guard.
  - Back-to-back — CLEAN: Start at QUEUED; the lease refuses it (the desktop tooltip, and `review_open` from Chrome); `session_retired` feeds `reminder_entry` (QUEUED and linked only); `_on_session_started` clears the stale post-Save Note tab.
  - 5.4 custody — CLEAN on the controller:
    - `adopt_queued` refuses under the lock before the unwrap (lease, reservation, active state, foreign root, the live session), destroys the key on every later refusal, runs the reader before installing, and retires like `start`.
    - The adopted session is protected (`custody_protected_ids`) and completes or discards through the live path; `recovered_writeback_target` is None for it; a saved note is never replaced but by a Regenerate's Save.
    - Found LOW-024 (the Chrome route skips one Recovery-screen block) and LOW-025 (the saved-note line can raise after adoption).
  - 5.5 — CLEAN: `reconstruct_reminder_entries` decrypts each record once and destroys the key in `finally`; the banner is ids and a count; `open_review` refuses a stale, unknown or live ref before the opener; the window comes forward and flashes. Found LOW-023 (an active session is refused only inside the opener).
  - 5.6 matrix honesty — CLEAN: every refusal row asserts the refusal code AND an unchanged controller (`calls` equality or the tuple form the positive tests also use), and the pausing rows fail if the rule never ran, so no row passes vacuously.
  - Close with unreviewed — found LOW-027 (an open recovered checkout is missing from the list).
  - Docs as control claims — the threat model's `open_review` pre-refusal list and its on-close residue were narrower than the code once LOW-023 and LOW-027 were fixed; both were reworded with the fixes. No other claim goes beyond the code.
- Findings:
  - **[LOW]** LOW-023: `desktop/src/scribe_desktop/ui/bridge.py` `_open_review` — `open_review` while a session was recording, paused or processing ran the opener. The window came forward, `adopt_queued` refused ("single-active-session"), and `_on_review_requested` switched the desktop to the Recovery tab mid-recording, answering `cannot_open`. Custody held; the problem was that the named refusal came after the window moved — materiality=ux surface=production — Triage: Fix-now; Decision: Applied:
    - `_open_review` refuses `session_active` for a state in `ACTIVE_STATES`, after the lease check and before the opener;
    - the module docstring, the threat model's THE BANNER AND `open_review` sentence and the CHANGELOG say so;
    - test: `test_ui_bridge.py::TestOpenReview::test_an_active_session_is_refused_before_the_opener` (RECORDING, PAUSED, PROCESSING refused with the opener never called; QUEUED opens, since adoption retires it).
  - **[LOW]** LOW-024: `ui/main_window.py` `_on_review_requested` — the Chrome route (`open_unreviewed`) skipped the Recovery screen's resume-in-flight block, which disables that screen's own button (`_busy`). An adoption during a resume-processing run succeeded, and when the resume landed `_on_recovered` replaced the adopted session's view, leaving it live QUEUED with no transcript view. Custody held: it is listed on close and retired into the index by the next Start. `_protected`'s other case (an open checkout) is already refused through `_transcript_source`, and the lease through `adopt_queued` — materiality=ux surface=production — Triage: Fix-now; Decision: Applied:
    - `_on_review_requested` refuses while `recovery_screen.is_busy`, with `models.REVIEW_OPEN_RECOVERY_BUSY_LINE` shown on the Recovery tab;
    - test: `test_unreviewed_review.py::TestReconstruction::test_refused_while_a_recovery_is_transcribing`.
  - **[LOW]** LOW-025: `ui/models.py` `saved_note_line` — it caught only `NoteConfigError`, but `load_note_config` raises `RuntimeError` for a broken install (unreadable shipped defaults). It runs in `_open_adopted` AFTER the adoption, so that error left the adopted session open with no Note tab and raised into the slot; on the Chrome route it also skipped that message's publish — materiality=robustness surface=production — Triage: Fix-now; Decision: Applied:
    - any exception gives `SAVED_NOTE_CONFIG_UNREADABLE_LINE` (true: the configuration could not be loaded);
    - test: `TestReviewCopy::test_the_saved_note_line_follows_the_config` gains the `RuntimeError` case.
  - **[LOW]** LOW-026: `ui/session_screen.py` — the "Confirm discard" label outlived its 10 s window and its session. A click under it after the lapse only armed again, so the label promised a discard it did not do — materiality=ux surface=production — Triage: Fix-now; Decision: Applied:
    - `_discard_confirmable` is the one rule for both the click and the poll;
    - `_watch_state` (the 500 ms poll) disarms a lapsed or other-session arming, so a click under "Confirm discard" always discards;
    - CHANGELOG part 3 says so;
    - test: `test_ui_pause_and_unreviewed.py::TestTwoStepDiscard::test_the_confirm_label_goes_when_its_window_lapses_or_its_session_changes`.
  - **[LOW]** LOW-027: `ui/main_window.py` `_unreviewed_expiries` — D6's on-close list read only the listed Unreviewed rows plus the live queued session. An open recovered checkout (a resumed session with its transcript on screen, not yet Completed) is excluded from the listing as protected, so it was never named and the window closed at once — materiality=ux surface=production — Triage: Fix-now; Decision: Applied:
    - the list adds `_transcript_source` when it names a recovered session, with the sweep's own `session_expires_at`;
    - the threat model's residue (2) names the three sources;
    - test: `test_unreviewed_review.py::TestCloseList::test_an_open_recovered_checkout_is_listed_too`.
- Checked and not raised:
  - after a Regenerate of a reopened saved note, "Cancel review" leaves the saved note on disk but not shown — the same as today's post-Save Regenerate → Cancel, so not Phase 5's;
  - the adopted session's `recorded_seconds` reads 0 (its store was closed at the Finish that produced it; cosmetic, and nothing in Phase 5 displays it);
  - `adopt_queued` does not consult the enrolment lease — it opens no microphone.
- Verification counts: 8 lenses run, 5 candidates, 0 dropped, 0 downgraded
- Missed-issue pass (auditable): re-read after the fixes:
  - `bridge._open_review`'s refusal order: session_changed → busy → review_in_progress → session_active → the opener. `test_cross_patient.py::test_open_review_names_only_a_retired_session_still_indexed` runs RECORDING and still gets `session_changed` first.
  - `SessionScreen._watch_state` / `on_discard_clicked` / `_discard_confirmable`: the disarm runs before the state early-return, and `_discard_armed` is set in `__init__` before the timer starts.
  - `MainWindow._unreviewed_expiries` against `_on_transcript_closed`, which clears `_transcript_source`, so a closed checkout is never listed.
  - `_on_review_requested`'s busy order.

  Result: none.
- ruff clean; mypy 47 files; no extension change; pytest owed to the composer (expected desktop 3912 + 7 = 3919: 4 parametrised bridge cases and 3 new tests; extension stays 105)
- Last reviewed: 2026-09-28

### Round 33 - 2026-09-28 - Phase 5 pause rule, resolution, back-to-back and Unreviewed (pause rule, bridge and custody core), independent cross-family codex peer review (pass stage-5.p1 slice A)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Specified Phase-5-only tree diff and slice A files; static review only. Startup reconstruction internals, checkout release and remaining UI custody consumers could not be fully verified within the permitted files.
- **PR-LOW-180** (LOW, test-harness, `desktop/tests/test_cross_patient.py:595`): The old-client Resume assertion passes even without the connection-identity guard, so this matrix row does not establish rejection for its named reason. — Evidence: `h.command("resume", conn_id=1, session_ref=ref)` is followed only by `assert h.controller.state is SessionState.PAUSED`; the matching report arrives later at line 601. Without the connection check, `desktop/src/scribe_desktop/ui/bridge.py:432` still returns `"report_mismatch"`, preserving PAUSED and allowing the entire test to pass. Recommendation: Fix-now — Send the old-client Resume after the current connection has reported the matching note; assert no resume call or state change, then verify the same command from the current client succeeds. /fix decision: Fixed — `desktop/tests/test_cross_patient.py::test_a_second_pipe_client_pauses_and_must_report_the_note_first` reordered as the LEG 1 shape:
  1. connect(2);
  2. the conn-2 `resume` gets `report_mismatch`;
  3. the conn-2 report of the recording's note;
  4. THEN the conn-1 `resume`, asserted PAUSED, `h.controller.calls` unchanged, and `last_refusal` still the step-2 one (dropped, never processed);
  5. the conn-2 `resume` gives RECORDING.

  Discrimination: with `ChromeBridge._on_message`'s `conn_id != self._conn` drop removed, step 4 reaches `_on_command` with a matching ref, PAUSED and a bound target equal to the session's, so `resume_refusal` passes and it resumes; the test then fails on the state and the calls. Test-only; production unchanged. Applied by Claude Code, 2026-09-28.
- Verification counts: 4 claims checked, 1 confirmed, 3 dropped as unverifiable
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-5-exec-e5)
- PR-LOW-180 (peer labels: LOW, test-harness, Fix-now) — materiality=behavioral severity=verified: low surface=test-harness rec=Fix-now — CONFIRMED.
  - Why the row passes without the guard: in `test_a_second_pipe_client_pauses_and_must_report_the_note_first` (`test_cross_patient.py:586-605`), the old-client `resume` (`conn_id=1`, line 595) is sent right after `h.connect(2)`, before any report on connection 2. The guard it names is `ChromeBridge._on_message`'s `conn_id != self._conn` drop. Without that guard the command would reach `_on_command`: the ref matches, PAUSED allows resume, and `resume_refusal` still returns `"report_mismatch"`, because `_conn` is 2 and the ledger's bound target was cleared by `_reset_connection`. So the state stays PAUSED, and the only assertion (`state is PAUSED`) holds either way. The production guard is present and correct; only the matrix row is vacuous for its named reason.
  - Fix shape (test only), in this order:
    1. `connect(2)`;
    2. conn-2 `resume` → `report_mismatch` (kept);
    3. conn-2 report of the recording's note;
    4. THEN the conn-1 `resume`: assert PAUSED, `h.controller.calls` unchanged (no `("resume",)`), and `last_refusal` still the step-2 one (dropped, never processed);
    5. conn-2 `resume` → RECORDING.

    Discrimination check for the fix leg: with the `conn_id != self._conn` line removed, step 4 resumes, because the report now matches, so the test fails. Record that check in the fix notes.
- Cap verdict: accept — test-harness — a vacuous matrix row whose production guard (`_on_message`'s connection drop) is present; a one-test reorder, no production change, and no extra round needed.
- Decision (leg stage-5-exec-e6, `/fix`): PR-LOW-180 Applied as shaped (the test reorder; see the `/fix decision` line).

### Round 34 - 2026-09-28 - Phase 5 pause rule, resolution, back-to-back and Unreviewed (UI, Unreviewed review and docs), independent cross-family codex peer review (pass stage-5.p1 slice B)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase-5-only tree diff, slice B UI, Unreviewed review, tests and security documentation; static reading only, no writes, tests or network.
- **PR-MED-190** (MED, regression, `desktop/src/scribe_desktop/ui/main_window.py:564`): Opening an Unreviewed transcript suppresses the unfinished-recording warning. A crash-recovered recording can retain an unfinished audio store alongside its transcript; reopening now treats it as cleanly finished, hiding the possibility of missing speech. — Evidence: `_open_adopted` passes `store_finished=True`; `ui/transcript.py:374` consequently hides `warning_label`. The listing already preserves the actual footer result at `ui/models.py:708`, and `ui/models.py:164` requires the warning “whenever a recovered store carries no complete Finish footer.” The Unreviewed list also bypasses the ordinary recovery selection warning. Recommendation: Fix-now — Carry the actual finish status through adoption into the review display, preserve the warning for unfinished stores, and add a reopen regression case. /fix decision: Fixed — three sites:
  - `ui/main_window.py` `_open_adopted(session, opening, *, store_finished)` is given `info.store_finished` by `_on_review_requested` and passes it to `show_document`, so both the Recovery button and the Chrome `open_unreviewed` route are covered;
  - `ui/models.py` `unreviewed_row_text` appends "no audio recorded" or "did not finish cleanly", as `_describe` does;
  - `ui/recovery.py` `_update_controls` shows `UNFINISHED_STORE_WARNING` for an unfinished selection in EITHER list.

  CHANGELOG part 3 says so. Tests:
  - `test_unreviewed_review.py::TestOpenForReview::test_an_unfinished_store_keeps_its_warning_on_the_row_and_when_opened[unfinished|finished]`: row text, selection warning and the reopened transcript's `warning_label`; the finished case shows none of them;
  - `::TestReconstruction::test_the_chrome_route_keeps_the_unfinished_store_warning`.

  The `_unreviewed` helper now writes a real one-chunk audio store, sealed by default and `finished=False` leaving the footer off. Before, it wrote no `audio.enc`, which the listing reads as unfinished. Applied by Claude Code, 2026-09-28.
- **PR-LOW-191** (LOW, docs-only, `docs/security/threat-model.md:1647`): The new pause-rule paragraph contradicts its own bound-tab rule by claiming that any non-Cliniko page never pauses. The same contradiction appears in `CHANGELOG.md:37`. — Evidence: “any page that is not Cliniko's, never pauses” conflicts with `threat-model.md:1641`, “leaving its note (any other page, including one off the allow-list)”, and plan D5 explicitly distinguishes a separate non-Cliniko tab from the bound tab leaving its note. Recommendation: Fix-now — Limit the no-pause statement to a separate non-Cliniko tab; preserve the bound-tab navigation exception in both documents. /fix decision: Fixed — the no-pause clause now reads "a SEPARATE tab showing a page that is not Cliniko's", with the bound tab's leave-its-note rule named, in three places: `docs/security/threat-model.md` (THE PAUSE RULE), `CHANGELOG.md` part 3, and the sibling in the `context_rules.py` module docstring. No code or test change: `test_the_bound_tab_rows` already pins `not_cliniko` → `LEFT_NOTE`. Applied by Claude Code, 2026-09-28.
- **PR-LOW-192** (LOW, docs-only, `docs/security/threat-model.md:1722`): The new expiry claim overstates the listing’s guarantee; the retention schedule repeats this unconditional claim. — Evidence: “the listing's age filter means a session past its window is never offered for opening.” However, `ui/models.py:719` explicitly documents that when neither timestamp is readable, “the session IS listed regardless of age”; lines 724–731 implement that conservative fallback. Recommendation: Fix-now — Qualify both documents to say that established expired sessions are excluded, and name the unreadable-timestamp residue without changing custody behavior. /fix decision: Fixed — `docs/security/threat-model.md` OPEN FOR REVIEW residue (1) and `docs/security/retention-schedule.md`'s 24-hour rule now say a session whose age is ESTABLISHED past its window is not offered. They name the residue: with no readable timestamp at all, the session is listed regardless of age (round 47 PR-LOW-001; the sweep owns that case) and its shown expiry is provisional. No code or test change; custody unchanged. Applied by Claude Code, 2026-09-28.
- Verification counts: 5 claims checked, 3 confirmed, 2 dropped as unverifiable
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-5-exec-e5)
- PR-MED-190 (peer labels: MED, regression, Fix-now) — materiality=regression severity=verified: med surface=production rec=Fix-now — CONFIRMED.
  - The bug: `_open_adopted` (`ui/main_window.py`) calls `transcript_screen.show_document(..., store_finished=True)` unconditionally, so `show_document` hides `warning_label`.
  - The path exists: a crashed session is taken through Recovery → Resume processing, whose runner writes `transcript.enc` over an audio store with no Finish footer (`RecoveryOutcome.store_finished` False; `_on_recovered` passes it through correctly). If the practitioner leaves it un-Completed, the session is on the Unreviewed list at the next listing (it has a transcript) with `RecoverableSessionInfo.store_finished=False` (`models.py:708`). Reopening it shows the transcript as if cleanly finished.
  - Why med: this breaks the binding Step-10 note (PR-HIGH-007 residual, `models.py:164`: the warning is shown "whenever a recovered store carries no complete Finish footer"). A reviewer is no longer told the tail may be missing, which bears on the clinical completeness of a note written from it. It does not affect custody.
  - CLASS CHECK (every review-entry path):
    - `_on_live_transcript` passes True correctly: a live Finish writes the footer before PROCESSING, and a failed final flush goes to FAILED with no transcript.
    - `_on_recovered` passes `outcome.store_finished` correctly.
    - `_open_adopted` is WRONG. It is shared by the Recovery "Open for review" and the Chrome `open_unreviewed` route, so both lose the warning.
    - SECOND SITE of the same class (the listing): `unreviewed_row_text` omits the "did not finish cleanly" tail that the recoverable list's `_describe` carries. The Recovery screen's `warning_label` follows only the `session_list` selection (`RecoveryScreen._update_controls` reads `_selected_info()`), so selecting an unfinished Unreviewed row shows no warning either.
    - The start-up reconstruction displays nothing, so it is not affected.
  - Fix shape:
    - `_open_adopted(session, opening, *, store_finished)`, given `info.store_finished` by `_on_review_requested`, and passed to `show_document`. The listing read the footer, and a retired store is closed, so it cannot change after listing.
    - `unreviewed_row_text` appends "did not finish cleanly" when `not info.store_finished`, as `_describe` does.
    - `RecoveryScreen._update_controls` shows `UNFINISHED_STORE_WARNING` for an unfinished Unreviewed selection too.
    - Note for the fix leg: `test_unreviewed_review._unreviewed` writes NO `audio.enc`, which the listing reports as `store_finished=False`. Give the helper a real store — finished by default via `SessionChunkStore.create` plus its Finish, and `finished=False` leaving the footer off — so existing tests keep modelling a clean session.
  - Regression tests:
    1. an Unreviewed session with an unfinished store → Open for review → `transcript_screen.warning_label` visible with `UNFINISHED_STORE_WARNING`;
    2. the same through `window.open_unreviewed` (the Chrome route);
    3. a finished store → the warning hidden;
    4. the row text carries "did not finish cleanly", and selecting that row shows the Recovery screen's warning.
- PR-LOW-191 (peer labels: LOW, docs-only, Fix-now) — materiality=docs-only severity=verified: low surface=docs rec=Fix-now (doc) — CONFIRMED.
  - The contradiction: `threat-model.md:1647-1648` "…and any page that is not Cliniko's, never pauses" contradicts the same paragraph's bound-tab rule (lines 1640-1641) and `ContextEvaluator.evaluate`: the bound tab reporting any page that is not a note, `not_cliniko` included, returns `LEFT_NOTE`. D5 (plan line 567) distinguishes the bound tab navigating off the allow-list (pauses) from a SEPARATE non-Cliniko tab (no pause).
  - Siblings (searched for "not Cliniko's", "non-Cliniko", "not_cliniko" near "never paus…" / "does not pause"):
    - `CHANGELOG.md:37` (same wording);
    - `context_rules.py:18-19`, the module docstring: "…and neither does a page that is not Cliniko's" — a code-doc sibling the peer did not name.
  - Fix shape (docs and docstring only): in all three, restrict the no-pause clause to "a SEPARATE tab showing a page that is not Cliniko's"; keep the bound tab's leave-its-note rule, `not_cliniko` included. No code or test change: `test_the_bound_tab_rows` already pins `not_cliniko` → `LEFT_NOTE`.
- PR-LOW-192 (peer labels: LOW, docs-only, Fix-now) — materiality=docs-only severity=verified: low surface=docs rec=Fix-now (doc) — CONFIRMED.
  - The overstated claim: `list_recoverable_sessions` (`models.py:711-730`) lists a session "regardless of age" when neither `created_at` nor `key_mtime` is readable (`readable` empty), which round 47 PR-LOW-001 already documented in the code. So "a session past its window is never offered for opening" (`threat-model.md:1721-1722`) and the retention schedule's "The listing's age filter means a session already past its window is never offered for opening" (`retention-schedule.md:71-72`) are absolute claims the code does not make.
  - A sub-point for the same wording: for such a session `session_expires_at` falls back to `now + 24 h`, so its Unreviewed row and the on-close list show a moving expiry. That matches the sweep's own fallback (`_session_created_at` returns `now`), and it is the same residue.
  - Fix shape (docs only): both documents say a session whose age is ESTABLISHED past its window is not offered. They name the residue: with no readable timestamp, it is listed and its shown expiry is provisional, and the sweep owns that case, as round 47 records. No code or test change; custody behaviour is unchanged.
- Cap verdict: raise +1 — production-behavioral — PR-MED-190 is a confirmed regression of the binding unfinished-store warning, in two sites: the adoption display and the Unreviewed row and selection. The fix plus a confirmation round needs headroom; PR-LOW-191 and PR-LOW-192 are docs-only confirmations with one code-docstring sibling.
- Decision (leg stage-5-exec-e6, `/fix`): PR-MED-190 Applied as shaped at all three sites: the adoption display, the Unreviewed row text and the selection warning, with the helper's real audio store. PR-LOW-191 Applied via the docs plus the `context_rules.py` docstring sibling. PR-LOW-192 Applied via the docs.
- Fix-delta self-check: PASS — re-read four things:
  - `_open_adopted`'s one caller, which passes `info.store_finished`;
  - `_update_controls`, where both selections are read and `info` is the recoverable one;
  - `unreviewed_row_text` against the existing no-full-id test (its `_info` has no audio, so the row now also says "no audio recorded" and still holds only the 8-character prefix);
  - the helper's store: `SessionChunkStore.create` after `wrap_key_to_file`, as `require_key` needs. Its header's `created_at` is now, so the reconstruction tests' back-dated key blob stays the earliest trusted timestamp, and their ordering holds.

### Round 35 - 2026-09-28 - Phase 5 pause rule, resolution, back-to-back and Unreviewed (confirmation of rounds 33-34), independent cross-family codex peer review (pass stage-5.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Scoped confirmation of rounds 33–34 against the specified Phase-5-only diff and current permitted files; static reading only, no writes, tests or network. No new findings introduced by the fixes identified.
- Confirmations: PR-LOW-180 CONFIRMED — `desktop/tests/test_cross_patient.py:599` sends `h.report(conn_id=2)` before the old-client Resume at line 605; lines 606–610 assert unchanged state/calls followed by successful current-client Resume. Removing `desktop/src/scribe_desktop/ui/bridge.py:519`’s connection check would allow the old command through the now-satisfied resume checks. PR-MED-190 CONFIRMED — both Recovery and Chrome converge on `desktop/src/scribe_desktop/ui/main_window.py:541`, passing `store_finished=info.store_finished`; line 574 forwards it, and ordinary recovery preserves `outcome.store_finished` at line 838. `desktop/src/scribe_desktop/ui/models.py:868` adds “did not finish cleanly”; `desktop/src/scribe_desktop/ui/recovery.py:260` checks both lists; `desktop/src/scribe_desktop/ui/transcript.py:374` hides the warning for finished stores. The unfinished assertions at `desktop/tests/test_unreviewed_review.py:642` and line 852 would fail before the fix; the finished case checks warning absence. The helper’s real audio store preserves the existing tests’ explicit refusal, custody and ordering assertions. PR-LOW-191 CONFIRMED — “a SEPARATE tab” at `docs/security/threat-model.md:1648` agrees with `CHANGELOG.md:37`, `desktop/src/scribe_desktop/context_rules.py:19`, and the bound-tab `return PauseReason.LEFT_NOTE` at line 157. PR-LOW-192 CONFIRMED — “age is ESTABLISHED” and the unreadable-timestamp residue at `docs/security/threat-model.md:1725` agree with `docs/security/retention-schedule.md:72` and `desktop/src/scribe_desktop/ui/models.py:724`’s readable/earliest timestamp branches.
- Verification counts: 4 claims checked, 4 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-28

### Round 36 - 2026-09-28 - Phase 6 (Tasks 6.0–6.5: test environment, manifest, service worker, page script, side panel, extension tests), `/review-loop` round 1 of cap 3

- Round status: Closed (0 pending) — 5 LOW, all Fix-now, all applied in this leg; vitest and the build owed to the composer
- Source: Claude Code (executor leg stage-6-exec-f3, claude-opus-5-5, sequential lenses in-session — no subagents)
- Scope / baseline: the whole Phase 6 diff under `extension/` on top of the uncommitted Phase 4 + 5 tree over `7a6cbd7`:
  - read in full: `src/context.ts`, `src/hub.ts`, `src/connection.ts`, `src/background.ts`, `src/page.ts`, `src/panel-view.ts`, `src/panel.ts`, `src/panel.html`, `src/manifest.ts`, `src/manifest-paths.ts`, `vitest.config.ts`, `src/test/chrome-fake.ts`;
  - tests: every new or changed test file (`context`, `hub`, `background`, `connection`, `manifest`, `page.dom`, `panel-view`, `panel.dom`, `test/chrome-fake.dom`);
  - the BUILT output the composer produced (`dist/manifest.json` and the file list: the panel at `src/panel.html`, the page-script loader in `content_scripts[0].js`, crxjs's added `web_accessible_resources`);
  - docs: AGENTS.md (prerequisites, step 8), CHANGELOG parts 1–2, the plan's 6.x task lines, the security docs searched for claims Phase 6 made false.

  Composer suites on the pre-round (f2) tree: desktop 3922 passed, extension 247 passed, `npm run build` OK.
- Lenses and results:
  - Host scoping — CLEAN: `host_permissions` and the one content script are `https://*.cliniko.com/*` only, top frame only; no `tabs`, no `<all_urls>`; `scripting` reaches only Cliniko hosts and the hub injects only into tabs on a Cliniko host; the built manifest matches the pin. Noted residue (not raised): crxjs adds the page-script module as a `web_accessible_resource` for Cliniko hosts (`use_dynamic_url: false`), so a Cliniko page can detect that the extension is installed; loaded in the page's own world the module finds no `chrome.runtime` and does nothing. For Task 8.1's docs.
  - Page-script trust — CLEAN: inert until an active slice; slices accepted only from this extension's worker (`sender.id` equal, no `sender.tab`); trusted clicks only (the closed shadow root also keeps the page's scripts from reaching the buttons; an event on the host element never reaches them); reads only `location.href` and its own marker; the orphan and re-injection takeover. The app never believes the page: pause, resume and every refusal are decided from the worker's URL-derived reports, so a page that removes or covers the card changes nothing the app enforces — the named residue (removal between heartbeats, keyboard shortcuts pass) is stated on 6.3's line.
  - Side panel — found LOW-029. Every D1 layout and every Phase 5 field is drawn (block, banner, Resume previous, `last_refusal`'s message, D4's refusal codes); text only; the consent box is never pre-ticked and is cleared on Start and on any change of note (the key covers tab, host, patient, note and verification); no timer for queued or finishing.
  - Background — found LOW-028 and LOW-030. The reports match D5's inputs (the bound tab is the latest `focused` report; a separate non-Cliniko tab is never reported, so it cannot pause; the bound tab leaving sends `not_cliniko` once; `closed` on removal); a restarted worker resyncs on its first `state` and pushes the full snapshot to the panel; every outbound message re-parses under the mirror.
  - Interpretation calls — CLEAN: 6.2's six and 6.4's five each agree with D1/D5/D13 or are recorded as revisable on their task lines.
  - Test honesty — CLEAN: the trusted-click path injects `isTrusted`, and the production default is proven by the untrusted test on the booted instance; the fake timers wrap only the 15 s disarm and the 1 s reconnect (the ports deliver by microtask, which the fake timers leave alone); the cross-clinic leak test checks names, ids AND the host.
  - Docs as control claims — found LOW-032 (the text-only / no-storage / no-logging claims were held by review, not structure). No security-doc claim is made false by Phase 6; the Chrome-side memory and per-tab scoping are Task 8.1's planned additions to flow 19.
  - Simplicity — found LOW-031.
- Findings:
  - **[LOW]** LOW-028: `extension/src/connection.ts` `badgeFor` — a failed link (`error`: a dead host's missed pong, a broken peer) showed **ERR** even while a session was live, hiding D1's "!" warning for up to one backoff step — materiality=ux surface=production — Triage: Fix-now; Decision: Applied: the "!" check (link down or failed, and the last running snapshot had a live or blocked session) now runs before ERR; test: the badge table gains `["error", null, true, "!"]`.
  - **[LOW]** LOW-029: `extension/src/panel-view.ts` `panelModel` — the Unreviewed banner (which names the note on the app's BOUND tab) was shown over the Message layout while a non-Cliniko tab was in front, so "Unreviewed recording for this note" pointed at nothing on screen — materiality=ux surface=production — Triage: Fix-now; Decision: Applied: the banner shows only while `focus.kind` is `cliniko`; test: `panel-view.test.ts` "no banner while a page that is not Cliniko is in front".
  - **[LOW]** LOW-030: `extension/src/hub.ts` `goToRecordingNote` — the fallback navigated the focused tab when it was on ANY Cliniko host, including a clinic that is not set up (another account's page) — materiality=correctness surface=production — Triage: Fix-now; Decision: Applied: only a tab on an allow-listed Cliniko page is navigated; otherwise the note opens in a new tab; test: `hub.test.ts` "from the panel, a focused Cliniko tab of a clinic that is not set up is left alone".
  - **[LOW]** LOW-031: `extension/src/context.ts` `ContextReporter.tabUpdated` — a redundant `evaluate(tab.id)` for a tab that changed window (the same tab is evaluated at the end, and reports are de-duplicated) — materiality=simplification surface=production — Triage: Fix-now; Decision: Applied: the line removed; behaviour unchanged (the existing reporter tests cover the path).
  - **[LOW]** LOW-032: `extension/src/*` — D1's "every string rendered with `textContent` only" and Constraint 8's "never in extension storage, never logged" were true of the code but held only by review (lessons 2026-08-10: guard the surface, not the instance) — materiality=assurance surface=test-harness — Triage: Fix-now; Decision: Applied: new `extension/src/sinks.test.ts` scans every production file under `src/` (tests and fakes excluded, comment lines skipped) for HTML-parsing sinks, any browser storage API and dynamic code, and pins the ONE console call (the host-disconnect diagnostic, no payload); a file-list test proves the scan sees the production files.
- Checked and not raised:
  - after a service-worker restart `wasLive` starts false, so a link that is still down shows OFF rather than "!" until the app's first snapshot (the app has already paused on the pipe loss);
  - between a worker restart and its first `state`, a tab event can send the inert slice (the allow-list is not yet known), briefly removing a frame until the snapshot lands;
  - the page's block card shows no refusal line (the panel shows it); D1 asks for none on the page;
  - the Blocked panel's "On screen" names the app's bound report, which after a focus change may be another Cliniko tab — the panel may show both patients (D1, D2).
- Verification counts: 8 lenses run, 5 candidates, 0 dropped, 0 downgraded
- Missed-issue pass (auditable): re-read after the fixes — `badgeFor`'s order (the existing `["error", null, false, "ERR"]` row still reaches ERR); `panelModel`'s banner condition against the Blocked/Live exclusions and the DOM banner test (its focus is `cliniko`); `goToRecordingNote`'s three branches (focused already showing → nothing; another tracked tab showing → activate; else navigate an allow-listed tab or open a new one); `tabUpdated` sibling-then-self order. Result: none.
- typecheck and lint clean; ruff and mypy unchanged (no desktop change); vitest owed to the composer (expected extension 247 + 8 = 255: badge row 1, banner 1, hub 1, `sinks.test.ts` 5; desktop stays 3922)
- Last reviewed: 2026-09-28

### Round 37 - 2026-09-28 - Phase 6 Chrome extension UI (service worker, tab tracking, relay and manifest), independent cross-family codex peer review (pass stage-6.p1 slice A)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase-6-only tree diff, slice A’s named files and permitted references; static reading only, no tests, network commands or writes.
- **PR-MED-200** (MED, behavioral, `extension/src/hub.ts:192`): Delayed tab reads can overwrite newer navigation, focus or removal events and emit stale context with a fresh sequence number. For example, a startup query captures note A, A closes while the window lookup remains pending, and resync restores A after its removal. The `getTab` callbacks likewise lack freshness guards; the page-message callback also overwrites the fetched URL with the earlier message’s URL. — Evidence: `hub.ts:198` calls `"this.reporter.resync(tabs, focused, state.allow_list)"`; `context.ts:183` clears the current table with `"this.tabs.clear()"` before installing the queried snapshots. Sibling callbacks at `hub.ts:221`, `235` and `292` unconditionally apply non-null results, including `"this.tabUpdated({ ...tab, url })"`. Recommendation: Fix-now — Guard asynchronous reads with connection/tab/focus generations or reconcile intervening events; add deferred-promise tests for close, navigation and activation during each lookup. /fix decision: Fixed — `extension/src/hub.ts`:
  - An event counter: `events`, `touched` per tab, `activated` per window, bumped by `bump()` at every tab/window event — `tabUpdated`, `tabActivated`, `tabRemoved`, `tabReplaced`, `windowFocused`, and a page `hello`/`href`.
  - `resync` asks again when an event landed while Chrome answered, `RESYNC_ATTEMPTS` = 3; still moving → stays inert with `needSync`, and the next event (`bump`) or snapshot asks again.
  - Every `getTab` answer goes through `lookUp`, applied only if no newer event touched that tab and, for an active answer, no newer activation in its window. That covers `tabActivated`, `tabReplaced` and the page's unknown-tab path, which now applies Chrome's fetched URL, not the message's.
  - `installed` is unchanged (flag only).
  - Tests: `hub.test.ts` "lookups overtaken by a newer event" (8), using a hold/release `FakeApi` that answers with the state it was asked in: close, navigation and activation during the resync query; a resync overtaken on every try, then retried by the next event; an older activation answered after a newer one; a replacing tab that navigates during its lookup; the unknown-tab hello with Chrome's URL; an unknown tab closed during its lookup. (Claude Code, leg stage-6-exec-f5, 2026-09-28)
- **PR-LOW-201** (LOW, behavioral, `extension/src/connection.ts:80`): Reconnecting to the native host clears the live-recording “!” warning before the app supplies its replacement state. After `hello_ack`, `connection` is connected and `state` remains null, so the badge becomes “…” despite `wasLive` being true. — Evidence: `"const down = connection !== \"connected\" || (state !== null && !state.app_running)"` excludes this state; lines 93–94 return `"…"` for connected/null. The reconnect test at `connection.test.ts:389` immediately supplies state without asserting the intervening badge. Recommendation: Fix-now — Preserve “!” while `wasLive` is true and the new connection has no app snapshot; assert the badge immediately after acknowledgement. /fix decision: Fixed — `extension/src/connection.ts` `badgeFor`: `(down || state === null) && wasLive` → "!". Tests: `connection.test.ts` badge row `["connected", null, true, "!"]`, and the reconnect test asserts "!" right after the second `hello_ack`, before any state. (Claude Code, leg stage-6-exec-f5, 2026-09-28)
- **PR-LOW-202** (LOW, test-harness, `extension/src/manifest.test.ts:41`): The host-scope tests compare against the same constant used by the manifest, so they do not independently pin Cliniko-only access. Changing that constant to `https://*/*` would satisfy these assertions and both negative string checks. — Evidence: `"expect(manifest.host_permissions).toEqual([CLINIKO_MATCH])"` and line 51’s `"expect(script.matches).toEqual([CLINIKO_MATCH])"`; lines 43–44 exclude only `"<all_urls>"` and `"http://"`. Recommendation: Fix-now — Assert the literal approved pattern `https://*.cliniko.com/*` independently for host permissions and content-script matches. /fix decision: Fixed — `extension/src/manifest.test.ts` asserts the literal for `host_permissions` and for every content script's `matches`, and pins `CLINIKO_MATCH` itself to it. Test-only. (Claude Code, leg stage-6-exec-f5, 2026-09-28)
- Verification counts: 5 claims checked, 3 confirmed, 2 dropped as unverifiable
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-6-exec-f4)
- **PR-MED-200** (peer: MED, behavioral) → materiality=behavioral severity=verified: med surface=production rec=Fix-now — CONFIRMED. **/fix (leg f5): Fixed** — the event counter plus `lookUp` in `hub.ts`; 8 regression tests.
  - Evidence:
    - `hub.ts:185-206` `resync` awaits `queryTabs()` + `lastFocusedWindow()`.
    - Meanwhile the reporter is deactivated (`hub.ts:150/157/168`), so a close, navigation or activation during the wait only edits the table (`context.ts:210` `tabRemoved` deletes, and sends nothing for an untracked tab).
    - `context.ts:182-183` then clears the table and installs the older snapshot, reporting it under a fresh `seq`.
  - Can the stale report make the APP resume or re-bind a linked recording? YES — a fresh-`seq` stale report is indistinguishable from a current one:
    - (1) Resync runs exactly after a (re)connect. That reconnect has already paused the linked recording (`new_client` / `pipe_lost`, with the block) and called `ContextEvaluator.lose_tab()`, leaving the session unbound.
    - (2) `ContextEvaluator.evaluate` re-binds an unbound session to ANY report naming its exact ids (`context_rules.py:159-161`). A stale "tab A shows note A" for a tab that was closed, or navigated to patient B's note, during the query re-binds the session to that tab.
    - (3) The bridge's `resume_refusal` (`bridge.py:421-434`) passes when the ledger's bound target, from the latest `focused` report, equals the session's target. So the practitioner's next Resume — desktop button, panel or block, or a pending "Resume previous" within 30 s — RESUMES the recording while the note is not actually on screen.
  - Limits of the harm:
    - The app never resumes on a report alone; a click is always needed.
    - A full navigation is corrected when the new document's page script says hello (`hub.ts:283-294`), and an SPA change by the 500 ms heartbeat. A CLOSED tab is never corrected: it sends nothing more.
    - The navigate-to-B case is the cross-patient one, and exists only until that hello. The window is the milliseconds of one `tabs.query` on a reconnect.
  - Hence MED, not HIGH: user-initiated, narrow, self-correcting except for a closed tab (where the recording resumes for the right patient with its note closed).
  - Class check — every async callback that applies tab state:
    - (a) `hub.ts:192-198` `resync` (query + focused window) — AFFECTED: close, navigation and activation.
    - (b) `hub.ts:220-222` `tabActivated`'s `getTab` for an unknown tab — AFFECTED: a newer activation in between is undone by `active: true` plus `unfocusSiblings`, giving a stale `focused` report and a wrong bound tab.
    - (c) `hub.ts:234-236` `tabReplaced`'s `getTab` — AFFECTED: a navigation or removal of the added tab in between.
    - (d) `hub.ts:291-293` `pageMessage`'s `getTab` for an unknown tab — AFFECTED: `{...tab, url}` overwrites the freshly fetched URL with the message's older one.
    - (e) `hub.ts:253-264` `installed` — NOT affected. It only sets the `restoring` flag and injects; a tab closed during its query leaves a harmless flag on a dead id. Sibling: the flag is never cleared for that id, which is cosmetic.
    - (f) `background.ts` adapters and `connection.ts` — hold no tab state.
    - (g) `context.ts` — synchronous only.
  - Fix shape:
    - A monotonic event epoch in the hub (or reporter), bumped by every tab and window event (`tabUpdated`, `tabActivated`, `tabRemoved`, `tabReplaced`, `windowFocused`, page hello/href), plus a per-tab epoch.
    - `resync` captures the epoch before the query. If it moved by the time the query lands, it discards the result and queries again (bounded, e.g. 3 tries; the worst case waits for the next event).
    - Each `getTab` callback captures the tab's epoch, and for `tabActivated` the focus epoch. It applies only if unchanged; otherwise the newer event already carried the truth.
    - `pageMessage`'s unknown-tab path applies the FETCHED tab's URL (current by construction), never the message's.
  - Regression tests (`hub.test.ts`, with a deferred-promise `FakeApi`):
    - close, navigation and activation each landing during the resync query → no report for the closed tab, the navigated tab reported with its NEW note, the later-activated tab focused;
    - a newer activation landing during `tabActivated`'s lookup → the newer tab stays focused;
    - navigation during the unknown-tab page lookup → the fetched URL wins.
- **PR-LOW-201** (peer: LOW, behavioral) → materiality=behavioral severity=verified: low surface=production rec=Fix-now — CONFIRMED. **/fix (leg f5): Fixed** — `badgeFor`; badge row + post-ack assertion.
  - Evidence: `connection.ts:80` computes `down` false for connected with no snapshot yet, so `connection.ts:93` returns "…" after `hello_ack` even though `wasLive` is true. The "!" returns only if the app's first snapshot says the app is not running; a running app replaces it with PAUSED.
  - Impact: the warning blinks off for the round trip of the first snapshot, normally well under a second; a host that answers hello but never gets the app's snapshot leaves "…" until the ping watchdog.
  - Fix shape: `badgeFor` treats "connected, no snapshot yet" as down for the `wasLive` check.
  - Regression tests: badge table row `["connected", null, true, "!"]`, and the reconnect test asserts the badge right after the second `hello_ack` (before any state).
- **PR-LOW-202** (peer: LOW, test-harness) → materiality=behavioral severity=verified: low surface=test-harness rec=Fix-now — CONFIRMED. **/fix (leg f5): Fixed** — literal pattern asserted three times.
  - Evidence: `manifest.test.ts:41` and `:51` compare with `CLINIKO_MATCH`, imported from the same `manifest-paths.ts` the manifest uses. With it set to `https://*/*`, both equalities hold, and `:43-44` still pass (no `<all_urls>`, and "https://" is not "http://").
  - Fix shape: assert the literal `"https://*.cliniko.com/*"` for `host_permissions` and for every content script's `matches`, and pin `CLINIKO_MATCH` itself to that literal.
  - Regression tests: the same file; a mutation to `https://*/*` now fails three assertions.
- Cap verdict: raise +1 — production-behavioral — PR-MED-200 confirmed: a stale-but-fresh-`seq` report from an async tab read can re-bind the unbound linked session and satisfy the resume check (user-initiated; a closed tab is never corrected), across 4 async sites in `hub.ts`. PR-LOW-201 is a brief badge regression; PR-LOW-202 is a test that pins nothing independent. The fix leg plus a confirmation needs headroom.
- Fix-delta self-check: PASS — re-read the applied hunks in `hub.ts` (counter, `resync` retry, `bump`, `lookUp`, the five event entries), `connection.ts` `badgeFor`, `manifest.test.ts`, and the new `hub.test.ts` / `connection.test.ts` cases; exit paths checked: `resync`'s link-down return, exhaustion, catch; `lookUp`'s null, touched and activated discards.

### Round 38 - 2026-09-28 - Phase 6 Chrome extension UI (page script, side panel and docs), independent cross-family codex peer review (pass stage-6.p1 slice B)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase-6-only tree diff `339b8ddf…` → `ef142216…`, specified slice B files and permitted context; static reading only, no writes, tests or network.
- **PR-LOW-210** (LOW, test-harness, `extension/src/sinks.test.ts:32`): The sink scanner misses ordinary bracket access and aliases, so its structural guarantee is overstated. `document["write"](value)`, `chrome["storage"].local.set(value)`, and `const execute = eval; execute(value)` evade the patterns; production `.js` files also escape discovery. — Evidence: the patterns require `document\.write`, `chrome\.storage`, and `\beval\s*\(`; line 21 selects only `/\.(ts|html)$/`. Recommendation: Fix-now — Add syntax-aware checks for property access and aliases, cover supported production source extensions, and add positive scanner fixtures proving these spellings are detected. /fix decision: Fixed — `extension/src/sinks.test.ts`:
  - Token patterns: the sink, storage and dynamic-code names match as tokens, so dotted, bracketed, destructured and aliased spellings are caught — `write`/`writeln` after `.` or a string key, bare `storage`/`cookie`, bare `eval`, `Function(`, and string timers.
  - Files scanned: `.ts/.tsx/.js/.mjs/.cjs/.html`, excluding `*.test.*`.
  - 16 detection fixtures (each asserted DETECTED) plus one clean fixture.
  - The header now states it as a LEXICAL guard with its residue: a name assembled at run time is not caught; review stays the control there.
  - Test-only. (Claude Code, leg stage-6-exec-f5, 2026-09-28)
- **PR-LOW-211** (LOW, behavioral, `extension/src/panel-view.ts:263`): Unknown warning code `constructor` displays the inherited Object constructor instead of nothing. It passes the protocol’s reason pattern. The refusal and block-reason dictionaries have the same inherited-property fallback defect. — Evidence: `warnings: state.warnings.flatMap((code) => (WARNINGS[code] !== undefined ? [WARNINGS[code]] : []))`; `WARNINGS` is an ordinary object at line 66; `protocol.ts:65` permits `/^[a-z][a-z0-9_]{0,47}$/`. Siblings: `panel-view.ts:150`, `panel-view.ts:154`, and `page.ts:46`. Recommendation: Fix-now — Use own-property checks or Maps for all four dictionaries and verify `constructor` takes the unknown-code fallback. /fix decision: Fixed — `Object.hasOwn` at all four lookups: `panel-view.ts` `lookUp()` for `noteRefusalText`, `blockReasonText` and the warnings list, and `page.ts` `reasonText`. Tests: `panel-view.test.ts` sends `constructor` / `toString` / `__proto__` to all three panel lookups; `page.dom.test.ts` sends `constructor` / `toString` as the block's reason. (Claude Code, leg stage-6-exec-f5, 2026-09-28)
- **PR-LOW-212** (LOW, docs-only, `.cursor/plans/plan-cliniko-workflow-safeguards.md:2800`): The stated block residue incorrectly limits page interference to “between heartbeats.” A page can hide the accessible host once with `display:none`; subsequent heartbeats and renders retain that host and never restore its styles. The cue can remain invisible while the desktop still blocks. — Evidence: the task says “the page's own scripts can remove or cover the element between heartbeats”; `page.ts:194` only checks `!this.host.isConnected`, and lines 253–255 return the existing root without restoring host styling. Recommendation: Fix-now — State explicitly that page scripts/CSS can persistently hide or cover the cue; heartbeat recovery covers detachment only, while desktop pause and command guards remain the enforcing controls. /fix decision: Fixed (docs-only) — the residue is restated as a class in four places: Task 6.3's line, the `page.ts` header and `tick` docstring, and the CHANGELOG page-script bullet. The page's scripts or CSS can keep the cue hidden or covered for as long as they like; the heartbeat only re-attaches a removed element; the app's pause rule and command checks enforce. AGENTS.md and the security docs carry no page-script residue sentence, so nothing changed there. The optional `important` restyle was NOT applied: the hiding routes are an open class (transform, clip-path, size, inset, top layer, re-hide per tick), so re-asserting a fixed list would close only named cases, and it would rewrite the host's style attribute every heartbeat. (Claude Code, leg stage-6-exec-f5, 2026-09-28)
- Verification counts: 5 claims checked, 3 confirmed, 2 dropped as unverifiable
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-6-exec-f4)
- **PR-LOW-210** (peer: LOW, test-harness) → materiality=behavioral severity=verified: low surface=test-harness rec=Fix-now — CONFIRMED. **/fix (leg f5): Fixed** — token patterns, wider file types, 16 detection fixtures + 1 clean, the header reworded as a lexical guard.
  - Evidence:
    - `sinks.test.ts:33-35` match only dotted spellings, so `document["write"]`, `chrome["storage"]` and an aliased `const e = eval; e(x)` all pass the scan.
    - `:21` keeps only `.ts`/`.html`.
  - No production file uses any of these today, so this is a gap in the guard, not a live defect.
  - Fix shape:
    - Token-level patterns: the sink and storage names as identifiers OR string literals (`["'\`]write["'\`]` after `document`, a bare `\bstorage\b` token after `chrome`, a bare `\beval\b` token, and `\bFunction\s*\(`).
    - Scan `.ts/.tsx/.js/.mjs/.cjs/.html`.
    - Reword the file header, and the round-36 claim it carries, as a LEXICAL guard with its named residue: a key computed from a variable or built by concatenation is not caught, so review remains the control there.
  - Regression tests: positive fixtures (inline strings run through the same `FORBIDDEN` list) for dotted, bracketed and aliased spellings of each class, each asserted DETECTED, plus one clean fixture asserted not flagged.
- **PR-LOW-211** (peer: LOW, behavioral) → materiality=behavioral severity=verified: low surface=production rec=Fix-now — CONFIRMED. **/fix (leg f5): Fixed** — `Object.hasOwn` at all four lookups; tests in both files.
  - Evidence:
    - `panel-view.ts:39/54/66` (`NOTE_REFUSALS`, `BLOCK_REASONS`, `WARNINGS`) and `page.ts:34` (`REASONS`) are plain object literals.
    - Their lookups at `panel-view.ts:150/154/263` and `page.ts:46` read inherited keys.
    - `constructor` (also `toString`, `valueOf`, …) passes `protocol.ts:65`'s pattern and yields `Object.prototype.constructor`: rendered through `textContent` as the function's source text, or through `String(...)` for the `??` paths.
  - Harm: no injection (text only), and the app sends only known codes, so a wrong or garbled line appears only for a code the app never emits. LOW.
  - Fix shape: `Object.hasOwn(DICT, code)` (or `Map`s) at all four lookups, keeping each one's existing unknown-code fallback.
  - Regression tests: `panel-view.test.ts` asserts `constructor` and `toString` take the fallback for `noteRefusalText`, `blockReasonText` and the warnings list (the warning dropped); `page.dom.test.ts` asserts the page block's reason line for `constructor` is the generic fallback.
- **PR-LOW-212** (peer: LOW, docs-only) → materiality=docs-only severity=verified: low surface=docs rec=Fix-now — CONFIRMED. **/fix (leg f5): Fixed (docs-only)** — the residue restated as a class; the optional restyle not applied (an open class of hiding routes).
  - Evidence:
    - `page.ts` `tick` re-attaches only when `!this.host.isConnected`.
    - `ensureRoot` returns the existing root without restyling it.
    - The host's styles are set once, inline and without priority, so a one-time `display:none` (inline or an author `!important` rule) persists across heartbeats and renders. "Between heartbeats" understates the residue.
  - Can the page script re-assert visibility per heartbeat? PARTLY:
    - Re-applying the host's inline styles with `"important"` priority on each 500 ms tick (and on each render) beats an author stylesheet, including `!important` rules, and undoes a one-time inline edit.
    - It cannot beat a page script that re-hides every tick, or that covers the cue with a top-layer element (`<dialog>`/popover), or with a later-stacked element at the maximum `z-index`.
  - So the residue must be RESTATED in all cases: page scripts or CSS can persistently hide or cover the cue; the heartbeat restores detachment (and, if the hardening lands, inline styling) only; the desktop pause and the command guards are the enforcing controls.
  - Fix shape:
    - Restate the residue in Task 6.3's note, and in the threat-model / data-flow wording if it repeats "between heartbeats".
    - OPTIONAL cheap hardening, the /fix leg's call: `important` inline styles re-applied every heartbeat.
  - Regression test only if the hardening lands: `page.dom.test.ts` sets `host.style.display = "none"`, advances one heartbeat, and asserts `display` is restored.
- Cap verdict: accept — production-behavioral — three LOWs confirmed (211 is a behavioral inherited-key lookup with no injection path; 210 is test-harness; 212 is docs-only). Their fixes fold into the confirmation round that round 37's raise already provides.
- Fix-delta self-check: PASS — re-read the applied hunks in `panel-view.ts` (`lookUp` and its three callers), `page.ts` (`reasonText`, the header and `tick` docstring), `sinks.test.ts` (whole file), Task 6.3's line and the CHANGELOG bullet; the scan's production patterns re-checked against every non-comment production line (the only token hits are `//` comments).

### Round 39 - 2026-09-28 - Phase 6 Chrome extension UI (confirmation of rounds 37-38), independent cross-family codex peer review (pass stage-6.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Scoped confirmation of the six fixes using the specified fix diff and permitted current files; static reading only, no writes, tests or network.
- **PR-LOW-220** (LOW, test-harness, `extension/src/sinks.test.ts:41`): PR-LOW-210 remains partially unresolved: the new header claims destructured and aliased spellings are caught, but `const { write } = document; write.call(document, x);` and `const Build = Function; Build(x)();` evade every forbidden pattern without assembling a name at runtime. — Evidence: line 41 requires `"(\.|\[\s*["'`])\s*write(ln)?\b"`; line 44 requires `"\bFunction\s*\("`; lines 9–12 claim “destructured and aliased spellings are caught” and describe runtime-assembled names as the residue. All 16 existing positive fixtures exercise the actual patterns successfully, but neither counterexample is included. Recommendation: Fix-now — Cover these literal destructuring/alias forms with shared-matcher fixtures, or narrow the header and explicitly document these additional gaps. /fix decision: Fixed — `extension/src/sinks.test.ts`:
  - `write`/`writeln` joined the HTML-sink names as bare tokens (the property-access prefix is dropped).
  - The dynamic-code pattern matches bare `eval`/`Function` and any `.constructor` / `["constructor"]` access.
  - The header states exactly that class — any literal occurrence of a listed name in a non-comment line, whatever the spelling around it — and names every remaining gap:
    - a name assembled at run time;
    - a capability reached through a name not on the list;
    - string timers, matched only as a direct call with a string literal;
    - trailing or block comments are scanned (a false positive at worst).
  - 5 new detection fixtures: destructured `write`, renamed destructured `writeln`, aliased `Function`, dotted and bracketed `constructor`.
  - The clean fixture adds `class A { constructor() {} }` and a multi-line class with a parameter-property `constructor(`; neither is flagged, because the ban needs `.` or a bracketed quote before `constructor`.
  - A scan of the production tree finds none of the new tokens outside `//` comments.
  - Test-only. (Claude Code, leg stage-6-exec-f7, 2026-09-28)
- Confirmations: PR-MED-200 CONFIRMED — relevant tab/focus guards, three-attempt resync, event/snapshot recovery and Chrome-owned URL are present; deferred tests release their promises and distinguish pre-fix behavior (`hub.ts:203`, `hub.ts:227`, `hub.ts:238`, `hub.test.ts:242`). PR-LOW-201 CONFIRMED — connected/null preserves “!” only with `wasLive`, with a post-ack assertion (`connection.ts:84`, `connection.test.ts:391`). PR-LOW-202 CONFIRMED — literal host pattern pinned independently (`manifest.test.ts:43`). PR-LOW-210 NOT CONFIRMED — remaining coverage overstatement described in PR-LOW-220. PR-LOW-211 CONFIRMED — all four lookups require own properties and retain their fallbacks; inherited-key tests exercise them (`panel-view.ts:151`, `page.ts:49`). PR-LOW-212 CONFIRMED — Task 6.3, CHANGELOG and comments consistently describe persistent hiding and detachment-only recovery; AGENTS.md contains no contradictory strength claim (`page.ts:197`, `page.ts:256`).
- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-6-exec-f6)
- **PR-LOW-220** (peer: LOW, test-harness) → materiality=behavioral severity=verified: low surface=test-harness rec=Fix-now — CONFIRMED. **/fix (leg f7): Fixed** — bare-token bans plus the `constructor` access ban, the header narrowed to that class with every gap named, 5 detection fixtures, and class declarations proven unflagged.
  - Evidence:
    - `sinks.test.ts:41` matches `write`/`writeln` only after `.` or an opening string key, so `const { write } = document;` and `write.call(document, x)` contain no match.
    - `:44` matches `Function` only directly before `(`, so `const Build = Function; Build(x)();` contains no match.
    - The header at `:8-13` says destructured and aliased spellings are caught and names only run-time-assembled names as residue, so it overstates what the matcher proves.
  - Impact: no production file uses either form today (a scan of `extension/src` finds bare `write`, `writeln`, `Function` and `.constructor` tokens in test files only), so this is a guard gap, not a live defect. LOW.
  - Fix shape — CHOSEN: make the header TRUE as a class by matching the listed names as bare tokens wherever they occur, and narrow the header to exactly that class.
    - Why not narrow the header alone: bare-token bans are cheap and hit nothing in production, and they turn "destructured and aliased" into a real guarantee for every listed name (a destructured or aliased name still has to be spelled once).
    - (1) HTML sinks: `\b(innerHTML|outerHTML|insertAdjacentHTML|createContextualFragment|DOMParser|parseFromString|setHTMLUnsafe|write|writeln)\b`, dropping the property-access prefix.
    - (2) Dynamic code: bare `\beval\b` (unchanged) and bare `\bFunction\b` (any use as a value), plus a property access to `constructor` (`(\.|\[\s*["'\`])\s*constructor\b`). That covers the other literal route to the Function constructor, `(() => 0).constructor(x)`; class declarations write `constructor(` with no dot, so they are unaffected.
    - (3) Storage: unchanged (already bare tokens).
    - (4) Header reworded to what the matcher proves: "any literal occurrence of a listed name as a token in non-comment production code fails, whatever the spelling around it (dotted, bracketed string key, destructured, aliased)".
    - (5) Header residue, named in full:
      - a name assembled at run time (`el["inner" + "HTML"]`, `obj[key]`, `Reflect.get(o, key)`);
      - a capability reached through a name NOT on the list (e.g. an HTML sink such as `srcdoc`, a `javascript:` URL, a created `<script>`);
      - string timers, matched only as a direct `setTimeout(`/`setInterval(` call with a string literal (the names themselves are legitimate), so an aliased timer is not caught;
      - lines that start with `//` are skipped, but a trailing or block comment is scanned (a false positive only).
      Code review stays the control for all of these.
  - Regression fixtures (each through the shared `flagged()` matcher and asserted DETECTED):
    - `const { write } = document; write.call(document, x);` (HTML sink);
    - `const { writeln: w } = document; w(x);` (HTML sink);
    - `const Build = Function; Build(x)();` (dynamic code);
    - `(() => 0).constructor("x")();` and `f["constructor"]("x")` (dynamic code).
    - The clean fixture gains `class A { constructor() {} }` and `const writer = 1;` (both stay unflagged).
- Cap verdict: accept — test-harness — PR-LOW-220 is a lexical-guard coverage gap with no production use (bare-token scan clean). The fix plus its confirmation fits the remaining pass cap (round 39 is peer round 3 of 6); no production-behavioral finding remains open.
- Fix-delta self-check: PASS — re-read the whole of `sinks.test.ts` after the edit: the three patterns, the 21 detection fixtures, the clean fixture (class declarations, `writer`, a function timer, a comment line) and the production scan; the new tokens were re-checked against every non-comment production line (no hits).

### Round 40 - 2026-09-28 - Phase 6 Chrome extension UI (confirmation of round 39), independent cross-family codex peer review (pass stage-6.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Specified fix diff, current `extension/src/sinks.test.ts`, round-39 finding and verified tuple, and permitted production grep; static inspection only, no writes, tests, or network.
- **PR-LOW-230** (LOW, test-harness, `extension/src/sinks.test.ts:56`): The new header overstates constructor coverage: comment-separated property accesses escape the matcher despite using the literal listed name. For example, `f./* gap */constructor("x")();` matches none of the forbidden patterns. — Evidence: `extension/src/sinks.test.ts:13` claims “any property access to”; line 14 specifies “`constructor`”; line 56 requires `(\.|\[\s*["'`])\s*constructor\b`, which permits whitespace but not an intervening comment. Lines 43–47 retain block comments. Recommendation: Fix-now — Explicitly document comment-separated constructor accesses as remaining lexical gaps, or cover them with shared-pattern fixtures. /fix decision: Fixed — `extension/src/sinks.test.ts` header rewritten to two rule kinds:
  - BARE NAMES (any literal token, whatever the spelling around it; a comment cannot split a token).
  - PREFIX-DEPENDENT: `constructor` only as `.constructor` / `?.constructor` / `["constructor"]`, and string timers only as a direct call with a string literal — both with only whitespace or newlines between.
  - Residue, named as a class: any other route to a prefix-dependent name (a comment inside the access or call, destructuring, `Reflect.get(o, "constructor")`, an aliased timer). The comment line now says a scanned trailing or block comment is a false positive for bare names and a missed match inside a prefix-dependent spelling.
  - The header cites lint as the syntax-aware check: `extension/eslint.config.js` spreads `tseslint.configs.recommendedTypeChecked`, which enables `@typescript-eslint/no-implied-eval`.
  - 2 detection fixtures: `f\n  .constructor("x")()` and `f?.constructor("x")`.
  - The matcher itself is unchanged; no block-comment strip (it would let string-held `/*` … `*/` markers hide code).
  - Test-only. (Claude Code, leg stage-6-exec-f9, 2026-09-28)
- Confirmations: PR-LOW-220 CONFIRMED for both original counterexamples: bare-token patterns at `extension/src/sinks.test.ts:53` and `:56` detect the fixtures at `:89` and `:91`. Fixtures and production scanning share `FORBIDDEN` and `code()` (`:59`, `:95`, `:110`). `writer` and plain class constructors remain unflagged (`:101–103`); the permitted production grep returns only class-constructor declarations at `extension/src/connection.ts:120` and `extension/src/protocol.ts:195`, with no production-specific exemption added. The broader header-accuracy claim is NOT CONFIRMED, as recorded in PR-LOW-230.
- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-6-exec-f8)
- **PR-LOW-230** (peer: LOW, test-harness) → materiality=docs-only severity=verified: low surface=test-harness rec=Fix-now — CONFIRMED. **/fix (leg f9): Fixed** — header narrowed to bare-name vs prefix-dependent rules with the residue class named and lint's `no-implied-eval` cited; 2 fixtures; matcher unchanged.
  - Evidence:
    - `sinks.test.ts:56`'s `constructor` alternative needs `.` or `[` plus a quote, then only `\s*`, then the name. So in `f./* gap */constructor("x")()` the `/*` breaks the match.
    - `code()` (`:43-47`) drops only lines that START with `//`, so block and trailing comments stay in the scanned text.
    - The header (`:13-14`) says "any property access to `constructor`", which is more than the matcher proves.
  - The same limit covers the whole class, not only the peer's example: every PREFIX-dependent alternative breaks when a comment sits inside it.
    - The `constructor` access fails the same way with a bracket (`f[/* */"constructor"]`), and the string-timer call with `setTimeout(/* */"run()")`.
    - Other spellings of `constructor` that are not dotted or bracketed are not matched either: destructuring `const { constructor: C } = f` and `Reflect.get(f, "constructor")`.
    - The bare-token names (`innerHTML`…`write`, the storage names, `eval`, `Function`) are unaffected, because a comment cannot split a token.
  - No production file has any of these forms, so the matcher misses nothing in production today. The defect is only that the header overstates the guard; its materiality is docs-only.
  - Fix shape — CHOSEN: narrow the header to exactly what the two prefix-dependent alternatives prove, and name the residue as a class.
    - The header states that `constructor` is matched only in the property-access spellings `.constructor`, `?.constructor` and `["constructor"]`, with nothing but whitespace or newlines between the accessor and the name.
    - Any other route to it is residue: a comment inside the access, destructuring, or `Reflect.get(o, "constructor")`.
    - The same "whitespace only" limit is stated for the string-timer call.
    - Why not strip block comments before matching: a naive `/\/\*[\s\S]*?\*\//g` strip opens a NEW evasion. Code between two string literals that contain `/*` and `*/` would be deleted before the scan. A correct strip needs a tokenizer, which is out of proportion for a test-harness guard.
    - Why not widen the regex to accept comments inside the prefix: it closes only the peer's example, while destructuring and `Reflect.get` stay open. The header would still need a residue clause, so the narrowing is needed either way, and adding the regex only adds surface.
    - Also say in the header that the syntax-aware control for dynamic code is lint: `@typescript-eslint/no-implied-eval`, from `recommendedTypeChecked` in `extension/eslint.config.js`, flags `new Function` / `Function(...)` and string timers on the AST, so it is not fooled by comments.
  - Regression fixtures:
    - one detection fixture proving the stated whitespace allowance: `f\n  .constructor("x")();` and `f?.constructor("x")`, both DETECTED as dynamic code;
    - the clean fixture keeps its class declarations.
    - No fixture pins the residue as undetected: a test that asserts a gap would fight any future widening, and the header names the gap.
  - A further confirmation round: NOT worth a codex round after this fix.
    - This lexical guard has now had three rounds (38 → 39 → 40). Each round found one more spelling that a regex cannot see, which is the expected behaviour of a lexical scan, not a sign of an unstable fix.
    - After the fix the header states the matcher's limit as a class ("prefix-dependent patterns match whitespace-only spellings; everything else is residue"), so the next spelling a peer finds falls inside the named residue.
    - The fix is header prose plus one fixture, has no production code path, and is checked by the fix-delta self-check. I recommend closing pass `stage-6.p1` on it.
- Cap verdict: accept — test-harness — PR-LOW-230 is a header overstatement with no production use (docs-only materiality). The fix narrows the claim to the matcher's proven class with the residue named, so no further codex round is recommended after it (round 40 is peer round 4 of 6).
- Fix-delta self-check: PASS — re-read the rewritten header against the three `FORBIDDEN` patterns line by line (each claim is one the regex proves: bare names as `\b` tokens, the `constructor` alternative `(\.|\[\s*["'\`])\s*constructor\b`, the timer alternative `set(Timeout|Interval)\s*\(\s*["'\`]`), and traced the two new fixtures (line-broken `.constructor` and `?.constructor`) through `code()` and the dynamic-code pattern.

### Round 41 - 2026-09-28 - Phase 7 (Tasks 7.1–7.3: global hotkey, spoken pause, new-consultation warning), `/review-loop` round 1 of cap 3

- Round status: Closed (0 pending) — 3 LOW, all Fix-now, all applied in this leg; pytest owed to the composer
- Source: Claude Code (executor leg stage-7-exec-g3, claude-opus-5-5, sequential lenses in-session — no subagents)
- Scope / baseline: the whole Phase 7 diff on top of the uncommitted Phase 4–6 tree over `7a6cbd7` (git cannot separate it, so the scope is the files Phase 7 created or edited, named on the 7.x task lines):
  - read in full: `hotkey.py`, `voice_commands.py`; the Phase 7 parts of `ui/main_window.py` (`_MSG` / `_native_msg` / `_is_suspend_event`, `__init__`'s wiring, `attach_chrome_link`, the hotkey section, `nativeEvent`, `pause_for`, `closeEvent`, `_on_session_started`, the phrase-rule section), `ui/bridge.py` (the docstring, `__init__`, the hands-free section, `build_content`, `_tick`, `view`), `ui/models.py` (the hands-free lines, `ChromeView`, `chrome_view_text`, `SessionControllerLike`), `app.py`; `extension/src/panel-view.ts` and `panel.ts`;
  - re-read against the new callers (unchanged by Phase 7): `ui/session_screen.py` `on_resume` / `on_pause` / `show_notice`, `ui/transcript.py` `live_window` / `_on_live_window`, `session.py` `pause` / `resume` / `recorded_seconds` / `live_failure` / `live_transcription_attached`, `audio_capture.py` `CaptureWorker` (the buffer across a Pause), `context_rules.py` `pause_action`, `note.py` `normalise_token`;
  - tests: `test_hands_free.py`, the changed parts of `test_ui_bridge.py`, `test_ui_models.py`, `test_ui_screens.py` (`FakeController`), `panel-view.test.ts`, `panel.dom.test.ts`;
  - docs: the threat model's "HANDS-FREE AND WARNINGS" paragraph and the pause-rule paragraph's two edits, data-flow flows 14 and 19, the retention live-buffers row, CHANGELOG, the 7.x task lines and the g1/g2 handoffs.

  Composer suites on the pre-round (g2) tree: desktop 4013 passed, extension 295 passed, `npm run build` OK.
- Lenses and results:
  - `nativeEvent` — CLEAN: one `try` around the whole body, `(False, 0)` for every message; the suspend branch is unchanged (`is_suspend_message` on the same `_MSG` head, still synchronous); the hotkey branch only emits a queued signal, so no pause or resume runs inside Windows' dispatch; `self._hotkey` absent (a native event during construction) is caught like any other error.
  - No resume bypass — CLEAN: `on_hotkey` resumes only through `SessionScreen.on_resume`, whose guard is the bridge's `resume_refusal` (the same check the button and Chrome's `resume` run); a refusal calls nothing. "Desktop only, not `state.last_refusal`" is CONSISTENT with D2 (`last_refusal` names a refused Chrome COMMAND) and D5 ("the reason is named" — the desktop button's refusal is desktop-only too); the panel already shows the paused or blocked state. Recorded as interpretation call 2 on the g1 handoff.
  - Registration and release — CLEAN: `attach_hotkey` only from `app.main`; a refusal (error 1409, or any registrar error) is a status on the status line, the Session screen and `state.hotkey`; nothing reserved means nothing to release; `detach_hotkey` in an ACCEPTED `closeEvent` (a refused close keeps the chord while recording goes on) and at `aboutToQuit`, idempotent. A second instance exits at the single-instance guard before any window exists.
  - Spoken pause — found LOW-033. Whole-word tokens through `note.normalise_token` (the g2 fix); "prescribe, pause" can never match; the FIRST word's `start_seconds` against the cutoff. The one-chunk grace is justified by `CaptureWorker._run`: its partial `buffer` survives a Pause and is written with the first post-Resume chunk, so up to a second of pre-Pause audio lands after `recorded_seconds`; documented in the module docstring, threat-model residue (2) and interpretation call 5. The phrase stays in the transcript (the Transcript screen's own slot renders it). "Unavailable" comes from the existing `live_failure` and `live_transcription_attached`.
  - Warning never acts — CLEAN: `_raise_new_consultation` sets the bridge's `_warning_session`, a status line, a notice and a taskbar flash — no controller call, no `pause_for`, no block; once per recording (`_raised`); `reset` at every Start; the bridge publishes it only while THAT session is recording or paused, and `_tick` drops it after.
  - Test honesty — found LOW-034 and LOW-035. No test reserves a real chord: `_main_window` never calls `attach_hotkey`, and every test call passes a fake registrar (the child process too).
  - Docs as control claims — CLEAN: the threat model states the hotkey as a global input (anyone at the keyboard, or a same-user `WM_HOTKEY`) that reaches only Pause and the guarded Resume, the phrase as heard from anyone in the room and only pausing, the warning as a heuristic cue, and the latency; each claim matches the code. LOW-033's rule is added to the module docstring and CHANGELOG.
- Findings:
  - **[LOW]** LOW-033: `desktop/src/scribe_desktop/voice_commands.py` `SpokenPauseDetector.feed` — the word carried from the previous window was joined to the next window's first word across ANY silence, so "…ask the scribe" and, after a pause long enough to close the window, "Pause here" read as the phrase and paused the recording — materiality=correctness surface=production — Triage: Fix-now; Decision: Applied: the carry joins only when the next window's first word starts ≤ `CARRY_MAX_GAP_SECONDS` (= `TRANSCRIBE_WINDOW_MAX_GAP_SECONDS`, 3.0 s — the silence that closes a window) after it; test: `TestSpokenPauseMatcher.test_a_silence_between_windows_breaks_the_phrase` (3.1 s apart does not pause, 2.7 s does).
  - **[LOW]** LOW-034: `desktop/tests/test_ui_bridge.py` `test_the_timer_and_spoken_pause_follow_the_controller` — with g1's new `FakeController.live_transcription_attached = False`, its "unavailable after a failure" assertion held BEFORE the failure was set, so it no longer tested the failure — materiality=assurance surface=test-harness — Triage: Fix-now; Decision: Applied: the test first attaches a running live transcriber and asserts `spoken_pause` true and no unavailable line, then sets the failure.
  - **[LOW]** LOW-035: `desktop/tests/test_hands_free.py` `test_a_real_wm_hotkey_through_qts_dispatch` — the child only SENT `WM_HOTKEY` into the window procedure, while Windows POSTS a real press to the thread's queue, which Qt's event dispatcher pumps; the claimed "real dispatch" did not cover that path — materiality=assurance surface=test-harness — Triage: Fix-now; Decision: Applied: the child now sends (as before, printing `SENT ["hotkey"]`) and then POSTS the app's id and another id through `PostMessageW`, pumping events five times; the test pins `SENT ["hotkey"]` then `SEEN ["hotkey", "hotkey"]`.
- Checked and not raised:
  - `recorded_seconds` is read in `_on_session_resumed` after `controller.resume()` has let capture run, so a chunk completed in between moves the cutoff up to one more second LATER — only in the safe direction (a pre-Resume phrase is still excluded; a phrase in that extra second is missed);
  - a live window of a previous recording cannot reach the next one's rules: a Start is allowed only at QUEUED, after the drain has delivered every tail post, and a Discard stops the worker under its post lock before the next Start click is processed;
  - the hotkey pressed while a voice enrolment runs: the state is IDLE, so nothing happens;
  - `attach_hotkey` creates the native window (`winId()`) before `show()`; Qt keeps that handle when the window is shown (the recreated-handle case is threat-model residue (1));
  - the warning's `show_notice` replaces the Session screen's last message; the warning is raised only while recording or paused, when that line holds no failure.
- Verification counts: 7 lenses run, 3 candidates, 0 dropped, 0 downgraded
- Missed-issue pass (auditable): re-read after the fixes — `feed`'s three stream shapes (no carry; carry within 3 s; carry dropped), with the existing split, mixed-window and cutoff tests traced through the new condition (the mixed-window test's carry precedes the next window, a negative gap, so it is kept as before); the child script's ordering (the sent id is delivered by the first `processEvents`, the posted one by the pump loop; the other id is ignored on both paths); the bridge test's two states. Result: none.
- ruff clean; mypy 49 files, no issues; no extension change; pytest owed to the composer (expected desktop 4013 + 1 = 4014: `test_a_silence_between_windows_breaks_the_phrase`; the other two fixes change existing tests; extension stays 295)
- Last reviewed: 2026-09-28

### Round 42 - 2026-09-28 - Phase 7 hands-free and warnings (hotkey, spoken pause and warning core), independent cross-family codex peer review (pass stage-7.p1 slice A)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase-7-only tree diff `70f4b247…bea02e4a`, slice A and permitted references; static review only, no writes, tests or network.
- **PR-LOW-240** (LOW, behavioral, `desktop/src/scribe_desktop/app.py:205`): Startup exceptions after hotkey registration have no guaranteed unregister path. An exception before the event loop starts bypasses both normal close and `aboutToQuit` cleanup, leaving release dependent on process termination. — Evidence: `hotkey = window.attach_hotkey()` precedes `log_event(logger, "hotkey", state=hotkey.state)` and `app.aboutToQuit.connect(window.detach_hotkey)`; subsequent timer setup, `window.show()` and `app.exec()` have no enclosing `finally`. Recommendation: Fix-now — Enclose attachment and subsequent startup/event-loop work in `try/finally` calling the idempotent detach; verify with a fake registrar and an injected post-registration startup failure. /fix decision: Applied — /fix notes: `desktop/src/scribe_desktop/app.py`: everything after `attach_hotkey()`, from the log line through `app.exec()`, now runs in `try: … finally: window.detach_hotkey()`; the `aboutToQuit` connection is kept, since detach is idempotent. Test: `test_hands_free.py` `TestHotkeyWindow.test_a_start_up_failure_after_attach_gives_the_chord_back` patches `main()`'s collaborators, makes `show` raise, and asserts one register and exactly one unregister. Siblings (Chrome pipe `pipe.stop`, the single-instance mutex) were not touched and are recorded as an Executor recommendation in the g5 handoff. ruff and mypy clean; pytest composer-run. /fix date: 2026-09-28. /fix applied by: Claude Code
- **PR-LOW-241** (LOW, behavioral, `desktop/src/scribe_desktop/ui/main_window.py:438`): A queued hotkey press remains actionable after its registration is detached. Registration validity is checked before enqueueing, but not when the queued callback executes; detach therefore does not invalidate an already accepted press. — Evidence: lines 483–484 use `self._hotkey.matches(*head)` then `self._hotkey_pressed_q.emit()`, while `_on_hotkey_pressed` unconditionally calls `self.on_hotkey()`; `detach_hotkey` only unregisters and publishes status. Recommendation: Fix-now — Bind queued presses to a registration generation and reject delivery after detach or replacement; add a fake-registrar test that queues a press, detaches, then processes events and asserts no action. /fix decision: Applied — /fix notes: `desktop/src/scribe_desktop/ui/main_window.py` `_on_hotkey_pressed` calls `on_hotkey()` only while `self._hotkey.status.available`. There is no generation counter: the chord is registered at most once, and nothing re-registers after detach (LEG 1). Test: `test_hands_free.py` `TestHotkeyWindow.test_a_press_queued_before_detach_is_dropped[False|True]` queues a press while RECORDING; with detach nothing is called, and the control case pauses. The existing queued-press and real-dispatch tests still deliver while reserved. No other queued signal is on the hotkey path (LEG 1 class check). ruff and mypy clean; pytest composer-run. /fix date: 2026-09-28. /fix applied by: Claude Code
- Verification counts: 3 claims checked, 2 confirmed, 1 dropped as unverifiable
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-7-exec-g4)

Verification only (2026-09-28T03:45+10:00): the code was re-read and nothing was changed.

- **PR-LOW-240** (peer: LOW, behavioral, `app.py:205`, Fix-now) — materiality=behavioral severity=LOW surface=production rec=Fix-now (cheap hardening; no reachable leak today) — the claim holds as stated: `app.py:205–224` has no `finally`, and only the accepted `closeEvent` and `aboutToQuit` call `detach_hotkey`. Evidence:
  - **What a leaked `RegisterHotKey` costs on Windows.** The reservation belongs to the window handle and its thread. Windows' window manager drops it when that window is destroyed or its thread or process ends: `UnregisterWindowHotKeys` and `UnregisterThreadHotKeys` in the window-manager cleanup, as ReactOS mirrors it. So a leak lasts only as long as the process does.
  - **Can a failed start-up keep the process alive?** No. Every thread in the app is daemon (`scribe-pipe-server` and its writers, the capture worker, the live transcriber), so an exception out of `main()` ends the interpreter, which destroys the window and the thread and gives the chord back. An exception inside `app.exec()` in a slot is printed by PySide6, and the loop runs on with the chord correctly held. A HUNG but alive process keeps the chord, and it also keeps the window and the single-instance mutex. A relaunch then says "already running" anyway, so the hotkey adds no new failure.
  - **Class check.** `pipe.stop` at `aboutToQuit` (`app.py:201`) and the mutex handle have the same no-`finally` shape and the same release at process exit. This is not a new class; the hotkey is its newest member.

  **Fix shape:** wrap `app.py:205–226` (from `attach_hotkey` through `app.exec()`) in `try: … finally: window.detach_hotkey()`, keeping the `aboutToQuit` connection (detach is idempotent). **Regression test:** in `test_status_and_app.py`, follow the pattern of `test_main_refuses_second_instance`. Monkeypatch the lock to acquired, `SoundDeviceBackend`, `default_sessions_root` to `tmp_path`, `_start_chrome_link` to `None`, and `MainWindow.attach_hotkey` to use a fake registrar that records unregisters. Make `MainWindow.show` raise, then assert `main()` raises and the fake saw one unregister.
- **PR-LOW-241** (peer: LOW, behavioral, `ui/main_window.py:438`, Fix-now) — materiality=behavioral severity=LOW surface=production rec=Fix-now (a one-line delivery-time check; no reachable harm today) — the claim holds: `matches()` (`hotkey.py:143–145`, false once `unregister` resets the status to `NOT_SET_UP`) is checked only when the press is queued (`main_window.py:483–484`). `_on_hotkey_pressed` (`:438–439`) calls `on_hotkey` unconditionally. Evidence:
  - **Can a late press act after close?** Not in effect. `detach_hotkey` has exactly two callers:
    - the ACCEPTED `closeEvent` (`:846`), which is reached only when the state is neither RECORDING nor PAUSED (`:784–795` refuses the close otherwise);
    - `aboutToQuit`, after which the event loop delivers nothing more.

    `on_hotkey` reads the controller state when the press is delivered, and acts only in RECORDING (pause) or PAUSED (the guarded Resume). A press delivered after an accepted close therefore finds nothing to act on. Nothing calls `setQuitOnLastWindowClosed(False)` and there is no tray icon, so an accepted close quits the app.
  - **Can a late press reach a DIFFERENT (next) recording?** Not through detach. Qt delivers the thread's posted events in order, so any LATER posted command (the relay thread's queued bridge signals, `bridge.py:281`) runs after the press. A new recording also cannot follow an accepted close.

    One property of any queued delivery, unrelated to detach: in theory a native input message (a Start click on the desktop) could be dispatched between the `WM_HOTKEY` and the press's delivery. Then the press would PAUSE the recording just started. That is the safe direction, and it is visible with its cue and Resume. A press can never RESUME a different recording: moving from one PAUSED recording to another PAUSED recording takes more than one event.
  - **Class check: every queued signal the hotkey path uses.** `_hotkey_pressed_q` (`:326–327`) is the ONLY queued hop. Everything downstream is synchronous on the GUI thread:
    - `pause_for` (`:489`);
    - `SessionScreen.on_resume` → `session_resumed` → `MainWindow._on_session_resumed` and the bridge's `_on_resumed` (`:356`, `bridge.py:288`, both same-thread direct connections);
    - `bridge.pause_cue` → `_show_pause_cue` (`:405`, direct).

    The sibling phrase path's cross-thread hop, `TranscriptScreen.live_window` (emitted from the live worker's thread, `transcript.py:292`), ALREADY re-checks when it is delivered: `_on_live_window` acts only in RECORDING or PAUSED, and the start-time reset plus event order keep an old recording's window out (round 41, checked and not raised). The hotkey hop is the one member of the class without a delivery-time check.

  **Fix shape:** `_on_hotkey_pressed` delivers only while the chord is still reserved: `if self._hotkey is not None and self._hotkey.status.available: self.on_hotkey()`. `attach_hotkey` registers at most once per `GlobalHotkey` (`hotkey.py:119–120`) and nothing re-registers after `detach`, so a "still reserved" check is exact and needs no generation counter. **Regression test:** add to `test_hands_free.py` `TestHotkeyWindow`. Attach a `FakeRegistrar`, set the fake controller to RECORDING, emit `window._hotkey_pressed_q`, call `detach_hotkey()`, then `processEvents()`, and assert no `pause` among `_actions(controller)`. Add a control case (the same steps without detach) that pauses, so the test can tell the two apart.
Cap verdict: accept — production-behavioral — both claims verified true but neither is reachable as harm (the OS releases the chord at process exit and every thread is daemon; detach runs only outside RECORDING/PAUSED, and posted events are delivered in order); each fix is a few lines with a deterministic in-process test, confirmable by the finishing seat without another peer round.
- LEG 2 decisions (leg stage-7-exec-g5, 2026-09-28; composer disposition `OWNERSHIP: auto-disposition` under `gates=executor`; cap verdict accepted):
  - PR-LOW-240 → **Applied** as the fix shape above; test `test_a_start_up_failure_after_attach_gives_the_chord_back`.
  - PR-LOW-241 → **Applied** as the fix shape above; tests `test_a_press_queued_before_detach_is_dropped[False|True]`.
- Fix-delta self-check: PASS. I re-read the two applied hunks and three new test cases.
  - `app.py`: `code` is bound only inside the `try`, so a failure raises before `return code`, and the normal exit still logs `app_exit`. The `finally` detach after the `aboutToQuit` detach is a no-op, because `unregister` is idempotent.
  - `_on_hotkey_pressed`: the two existing tests that deliver a press (queued-only-for-the-reserved-chord, and the real-dispatch child, which detaches only after its last `processEvents`) still deliver while reserved.
  - The new `main()` test disconnects the `aboutToQuit` slot it wired on the shared app, and patches only `app` module names and the one window instance.

### Round 43 - 2026-09-28 - Phase 7 hands-free and warnings (bridge, models, side panel and docs), independent cross-family codex peer review (pass stage-7.p1 slice B)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Specified Phase-7-only tree diff, permitted slice B files, and designated plan sections; static review only, with no writes, tests, npm, or network commands.
- No verified findings. The shared snapshot preserves hands-free status across reconnects; warnings are restricted to their live recording. Panel warning lookups use own entries and rendering uses `textContent`. The revised failure test distinguishes available from failed transcription. Desktop-only hotkey refusals are consistent with D2’s Chrome-command refusal channel and Task 7.1’s recorded behavior.
- Verification counts: 12 claims checked, 10 confirmed, 2 dropped as unverifiable within this slice: production controller accessor behavior and core hotkey/detector enforcement behind the documentation claims.
- Last reviewed: 2026-09-28

### Round 44 - 2026-09-28 - Phase 7 hands-free and warnings (confirmation of round 42), independent cross-family codex peer review (pass stage-7.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Scoped confirmation of `bea02e4a…c71f7c09`, the four permitted current files and Round 42; static reading only, no writes, tests or network. No new findings.
- Confirmations: **PR-LOW-240 CONFIRMED** — `desktop/src/scribe_desktop/app.py:207` protects all work after successful attachment through `app.exec()` with `finally: window.detach_hotkey()` (`:227`). Window construction precedes this block; existing close/quit cleanup and pipe-stop ordering remain intact, with no exception suppression or premature mutex release added. The regression test injects `raise RuntimeError("start-up failed")` (`desktop/tests/test_hands_free.py:552`), requires its propagation (`:570`), and asserts exactly one unregister (`:574`); pre-fix code leaves that list empty. Existing tests pin repeated detach to one unregister (`:529`). **PR-LOW-241 CONFIRMED** — `desktop/src/scribe_desktop/ui/main_window.py:441` checks `self._hotkey.status.available` on the same object that detach unregisters (`:434`), consistent with Round 42’s verified status-reset contract. The parametrised test sets RECORDING, queues delivery, optionally detaches, then processes events; `assert _actions(controller) == ([] if detach else [("pause",)])` (`desktop/tests/test_hands_free.py:592`) requires a real pause call in the control case. The detached case fails against the pre-fix unconditional callback.
- Verification counts: 2 claims checked, 2 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-28

### Round 45 - 2026-09-28 - Phase 8 (Tasks 8.1–8.2: security docs as one class, copied note kept out of clipboard history and sync), `/review-loop` round 1 of cap 3

- Round status: Closed (0 pending) — 2 LOW, both Fix-now docs, both applied in this leg; pytest owed to the composer (8.2's selection route changed code before the round)
- Source: Claude Code (executor leg stage-8-exec-h2, claude-opus-5-5, sequential lenses in-session — no subagents)
- Scope / baseline: the whole Phase 8 diff on top of the uncommitted Phase 4–7 tree over `7a6cbd7` (git cannot separate it, so the scope is what the 8.1 and 8.2 task lines name):
  - docs: `docs/security/threat-model.md` (scope, trust boundary 1, the Cliniko client's callers, NOTE VERIFICATION, THE ENCOUNTER RECORD, the pause-rule residue, 3A surface 4, the new "The Chrome extension" section, out of scope, review triggers), `data-flow-map.md` (title, intro, components, flows 10, 18, 20, the non-flows, the closing block), `retention-schedule.md` (intro, clipboard, API-response, encounter rows and the four new rows), `intended-use.md`, `docs/security/README.md`, `incident-process.md`, `docs/design-system.md`, `protocol/fixtures/README.md`, `PLAN.md`, AGENTS.md, CHANGELOG;
  - code and tests: `ui/models.py` (`CLIPBOARD_EXCLUSION_FORMATS`, `clipboard_mime_formats`, `windows_clipboard_mime_type`), `ui/note.py` (`_place_note_text`, `_NotePanel`, `_copy_note`, the module docstring), `test_ui_screens.py` (the copy section), `test_ui_prose_stage.py`'s stub, `test_ui_models.py` `TestClipboardFormats`;
  - re-read against the claims: `extension/src/manifest.ts`, `background.ts`, `hub.ts`, `context.ts`, `connection.ts`, `page.ts`, `panel.ts`, `panel-view.ts`, `extension/dist/manifest.json`; `ui/bridge.py` (`_on_context`, `_dispatch`, `_report_state` … `build_content`); `protocol.py` (the state payload models); `encounter.py` (`ConsentAttestation`, `read_encounter_record` and its three callers).

  Composer suites on the pre-round (h1) tree: desktop 4022 passed, extension 295 passed, `npm run build` OK.
- Lenses and results:
  - Control claims enforced by the code they name — found LOW-037; the load-bearing claims hold: the manifest (`manifest.ts:23-41`; the built `web_accessible_resources` entry with `use_dynamic_url: false`), reports from URLs only (`context.ts:55-70`, `243-259`), sender checks (`hub.ts:318-358`, `362-420`), `isTrusted` (`page.ts:383`), per-tab scoping (`context.ts:300-340`), `textContent` (`page.ts:122`), the inert/teardown lifecycle (`page.ts:215-245`) and re-injection (`hub.ts:293-313`), the worker's snapshot cleared on connect, fail and disconnect (`connection.ts:160`, `259`, `272`), the name-bearing `state` fields and the banner never named (`protocol.py:243-311`, `ui/bridge.py:938-961`), the three `encounter.enc` decrypt sites (`ui/main_window.py:988`, `session.py:1136`, `ui/models.py:977`), `ConsentAttestation` (`encounter.py:145-154`).
  - No two docs state one control differently — found LOW-036. Discard's two clicks (desktop 10 s, block and panel 15 s), the frame colours, the badge, the clipboard formats and their residue now read the same at every site.
  - Stale wording under `docs/`, `PLAN.md`, AGENTS.md and source docstrings — CLEAN: no "Phase 5 preview", "unwired", "shown nowhere", "until the Phase 6 extension", and no leftover h1 "a keyboard copy carries none of them" sentence. One historical match stays by design: CHANGELOG's Phase 4 part 1 entry ("refused until Phase 5") records that phase's state.
  - `PLAN.md` — CLEAN: exactly the four listed edits (`git diff`: steps 9 and "stop", `ConsentAttestation`, the Phase 5 delivery note) and nothing more.
  - 8.2's formats and payloads — CLEAN: three names, each `(0).to_bytes(4, "little")`, under `application/x-qt-windows-mime;value="<name>"`; one placement (`_place_note_text`) for the button and the selection; each route re-checks `_copy_ready` at the moment of copying; the selection text is `textCursor().selection().toPlainText()`, the text `QTextEditMimeData` places as `text/plain`. Class check across `ui/`: `note_body` is the only selectable surface showing note text.
  - The round-70 pins' strength — CLEAN: `_fake_clipboard` records `setText` AND `setMimeData`; `_attempt_copy` now tries the button, the direct call and every selection route over `selectAll()`, so the flag-off pin and the pre-ratification half of the flag-on pin cover them; the exact-text assertion after ratification is unchanged.
  - Test honesty — CLEAN: the unratified test proves a selection exists before asserting nothing is placed; the context-menu wiring test stubs the menu (no modal `exec`); the keyboard test iterates the platform's real Copy bindings and asserts Ctrl+C is among them; no test touches the real clipboard.
  - Identifying data — CLEAN: none in any changed file.
- Findings:
  - **[LOW]** LOW-036: AGENTS.md Local Run Steps step 8, `docs/security/data-flow-map.md` (the no-network non-flow) and `docs/security/incident-process.md` (the network trigger) — step 8 still called Validate "the only moment the app talks to Cliniko", and the other two stated "none at startup or idle" without saying that a Chrome note report triggers a verification, so an app started while Chrome shows a Cliniko note (it verifies that note once the report arrives) read as a contract breach and an incident — materiality=assurance surface=docs — Triage: Fix-now; Decision: Applied: step 8 names both triggers; the non-flow says a call follows only a practitioner action or a Chrome note report and that the no-sockets legs measure startup and idle with no Chrome link; the incident trigger excludes a note open in Chrome. (The threat model's client section already said so since h1.)
  - **[LOW]** LOW-037: `docs/security/data-flow-map.md` flow 20 and the retention "Chrome-side memory" row — flow 20 said the panel keeps "the one note the consent tick was given for, until the tick clears" (`panel.ts` keeps the Ready layout's KEY — tab, host, patient and note ids, verification — while that layout stands), and neither listed the worker's last-sent slice per tab (`hub.ts` `sentSlices`, change detection), which can hold that tab's clinic's patient name — materiality=assurance surface=docs — Triage: Fix-now; Decision: Applied: both sites now state the key and its lifetime and the last-sent slice (dropped when the tab closes, on a resync or on the page script's hello).
- Checked and not raised:
  - drag of the ratified selection out of the note panel: Qt's own drag (`createMimeDataFromSelection`, no formats) never touches the clipboard, so history and sync never see it; named as residue at every 8.2 site rather than blocked (blocking it would need Qt's private drag switch or a mouse-event override for no clipboard gain);
  - overriding `createMimeDataFromSelection` instead of intercepting the actions: rejected — the ownership of a Python-returned `QMimeData` from that virtual could not be verified offline, and a wrongly owned object would leave the clipboard a dangling pointer;
  - Cut and Paste on the read-only panel do nothing, and the transcript views stay `NoTextInteraction`;
  - the extra blank line after the PLAN.md delivery note is formatting only.
- Verification counts: 8 lenses run, 2 candidates, 0 dropped, 0 downgraded
- Missed-issue pass (auditable): re-read after the fixes — the three contract statements against `ui/bridge.py` `_on_context` / `_dispatch` (a call only on a report or a new connection under a linked session) and the no-sockets legs' scope; flow 20 and the retention row against `panel.ts:118-121` and `hub.ts:130`, `213`, `273`, `306`, `331`, `492-493`; the h2 selection route against its three tests. Result: none.
- ruff clean; mypy 49 files, no issues; extension typecheck and lint clean (no extension change); pytest owed to the composer (expected desktop 4022 + 3 = 4025: the three new selection tests; `_attempt_copy` changes existing tests without adding any; extension stays 295)
- Last reviewed: 2026-09-28

### Round 46 - 2026-09-28 - Phase 8 security docs and clipboard exclusion (clipboard exclusion code, tests and its doc sites), independent cross-family codex peer review (pass stage-8.p1 slice A)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase-8-only slice A diff between the supplied tree objects, permitted current code/tests, plan constraints and clipboard documentation; static review only, no writes, tests or network.
- **PR-LOW-270** (LOW, test-harness, `desktop/tests/test_ui_screens.py:6321`): The clipboard fake intercepts the Python placement helper but cannot intercept Qt’s native clipboard path, which the new keyboard tests exercise if interception regresses. Such a regression can touch the real clipboard before the positive test fails; negative assertions over the fake’s payload list cannot detect that native write. — Evidence: `monkeypatch.setattr(note_module, "QApplication", _StubApplication)` replaces only the module binding; line 6355 calls `body.keyPressEvent(cls._copy_key_event())`, while `desktop/src/scribe_desktop/ui/note.py:287` retains `super().keyPressEvent(event)`. Recommendation: Fix-now — Add a test guard that detects and prevents native Copy delegation before clipboard access, preserving fake-only execution even when the interception regresses. /fix decision: Applied — /fix notes: `desktop/tests/test_ui_screens.py` only (no production change). `_fake_clipboard` now:
  - asserts `QGuiApplication.platformName() == "offscreen"`;
  - replaces `QPlainTextEdit.keyPressEvent` with a guard that raises `AssertionError("a Copy key reached Qt's native copy")` on any `StandardKey.Copy` event and passes every other key to the saved original (optionally recording it in `native_keys`);
  - replaces `QPlainTextEdit.copy` with a guard that raises.

  Two new tests:
  - `test_the_native_copy_guard_passes_other_keys_to_qt`: Key_A reaches Qt through the guard; the panel's own Ctrl+C never does and places nothing unratified.
  - `test_an_unintercepted_copy_key_fails_before_any_clipboard`: with `_NotePanel.keyPressEvent` deleted, Ctrl+C and a direct `copy()` each raise the guard's error with the fake clipboard empty.

  Verified: ruff clean; mypy 49 files. The tests are composer-run (expected +2). Sibling sites: the prose-stage stub in `test_ui_prose_stage.py` drives no key or native copy (none needed). /fix date: 2026-09-28. /fix applied by: Claude Code
- **PR-LOW-271** (LOW, docs-only, `docs/security/intended-use.md:61`): The intended-use clipboard paragraph omits the third-party-manager, indefinite-residue/no-clearing and drag-and-drop limitations explicitly required at every clipboard documentation site. — Evidence: lines 63–66 say “Windows clipboard history and cloud clipboard sync leave it out” and “the marks do not stop other programs reading the clipboard”, then end with the cloud-sync advice and cross-reference. In contrast, `docs/security/threat-model.md:407–414` explicitly records all three missing limitations. Recommendation: Fix-now — Add those limitations to the intended-use paragraph so it matches flow 10, the retention row and the threat model. /fix decision: Applied — /fix notes: `docs/security/intended-use.md` current scope note. The clipboard paragraph now names the three limits the threat model's 3A surface 4 records:
  - a third-party clipboard manager may ignore the marks;
  - the copy stays until replaced, and the app never clears it;
  - a drag of the selection carries no marks, does not use the clipboard, and lands wherever it is dropped.

  Verified by re-reading it against `threat-model.md:404-418`. Sibling sites: none (flow 10, the retention row and the threat model already carry all three). /fix date: 2026-09-28. /fix applied by: Claude Code
- Verification counts: 3 claims checked, 2 confirmed, 1 dropped as unverifiable (independent Windows interpretation of the exclusion-format payload could not be established from the permitted local sources).
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-8-exec-h3)

- **PR-LOW-270** (peer: LOW, test-harness) — materiality=behavioral (test-harness side effect only, conditional) severity=LOW surface=test-harness rec=Fix-now — the peer's mechanism is real: `_fake_clipboard` replaces only `note_module.QApplication` (`test_ui_screens.py:6321`), and `_NotePanel.keyPressEvent` hands every non-Copy key to `super().keyPressEvent(event)` (`ui/note.py:287`). So a regression that dropped the Copy match would send Ctrl+C from `_attempt_copy` (`test_ui_screens.py:6355`, after `selectAll()`) into Qt's C++ `QPlainTextEdit::copy`, which calls `QGuiApplication::clipboard()` natively, and no Python patch can see that call.
  - **Can a test run ACTUALLY place note text on the real clipboard today? No, not under the default run.**
    - (1) The interception is in place: the h2 tree's keyboard and context-menu tests passed in the composer's run (4025), so no copy key reaches the native path.
    - (2) Every UI test module does `os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")` before a `QApplication` exists (e.g. `test_ui_screens.py:21`). The offscreen QPA's clipboard is Qt's in-process `QPlatformClipboard`, not the Windows clipboard. This is believed, not verifiable offline.
    - `test_hands_free.py:607` sets `windows` only in a child subprocess's environment, which runs no copy test.
    - The real clipboard is reachable only if BOTH a native `QT_QPA_PLATFORM` is preset in the shell (`setdefault` honours it) AND the interception regresses. The test text is a mock note, never patient text.
  - **Smallest shape that makes the tests unable to touch it:**
    - (a) In `_fake_clipboard`, assert `QGuiApplication.platformName() == "offscreen"` and fail loudly otherwise, so a preset native platform stops the copy tests before any copy.
    - (b) In the same fake, `monkeypatch.setattr(QPlainTextEdit, "keyPressEvent", spy)` and `monkeypatch.setattr(QPlainTextEdit, "copy", refuse)`. The spy raises `AssertionError` for any event where `event.matches(QKeySequence.StandardKey.Copy)` and otherwise calls the saved original. Python's `super()` resolves the patched attribute at call time, so a regressed panel fails in Python before native Qt runs.
    - Regression tests:
      - (i) Key_A through `_NotePanel.keyPressEvent` reaches the spy's pass-through. This proves the patch is not vacuous.
      - (ii) With `_NotePanel.keyPressEvent` monkeypatched back to `QPlainTextEdit.keyPressEvent`, Ctrl+C raises the spy's `AssertionError` and the fake records nothing.
    - Net suite +2. No production change.
- **PR-LOW-271** (peer: LOW, docs-only) — materiality=docs-only severity=LOW surface=docs rec=Fix-now — confirmed. The Task 8.2 line requires the residue at every doc site. The `intended-use.md` clipboard paragraph names only "other programs reading the clipboard", while threat-model 3A surface 4, flow 10 and the retention clipboard row also name:
  - third-party clipboard managers that ignore the formats;
  - the copy staying until replaced, because nothing clears it;
  - a drag of the selection carrying no formats.
  - Shape: add one sentence naming those three to that paragraph. No code.
- Cap verdict: accept — test-harness — both LOW are Fix-now within the pass; the default run is offscreen with the interception passing, so the harness gap is latent, not a live write to the practitioner's clipboard, and the fix is test-only (+2 tests) plus one docs sentence.
- Final dispositions (leg stage-8-exec-h4 /fix; composer `OWNERSHIP: auto-disposition`):
  - PR-LOW-270 → Applied (shape (a) + (b) and tests (i) + (ii), as above; test-only).
  - PR-LOW-271 → Applied (one sentence in `intended-use.md`).
- Fix-delta self-check: PASS — re-read 2 applied hunks across 2 files: the `_fake_clipboard` guards plus 2 tests, and the intended-use sentence.
  - The guard leaves the existing copy tests' routes untouched: each goes through `_NotePanel`'s own Copy match before `super()`.
  - The deleted-handler test restores through `monkeypatch`.
  - The platform assert runs after `qapp` exists.

### Round 47 - 2026-09-28 - Phase 8 security docs and clipboard exclusion (security docs as one class), independent cross-family codex peer review (pass stage-8.p1 slice B)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase-8-only diff `d07f111629e9201229bb20f482a5f6c1e0c60f57` → `a1bcc0a3a44731d4e0c67a335c90278ac23407ee`, the nine specified slice B files, selected plan constraints/decisions/tasks, and cited implementation checks; read-only, no tests or network.
- **PR-LOW-280** (LOW, docs-only, `PLAN.md:135`): The new delivery summary overstates the recording and pause guarantees: offline-unverified starts are permitted, desktop starts remain unlinked, and switching to a separate non-Cliniko tab does not pause. — Evidence: “Recording starts only from an open treatment note that Cliniko verifies” and “any patient, note, tab or login change pauses”; `desktop/src/scribe_desktop/encounter.py:765` explicitly permits “verified or `unverified_offline`”, while `desktop/src/scribe_desktop/context_rules.py:162` checks `report.focused and report.page == "note" and not same`, followed by the login check and otherwise `return None` at line 166. Recommendation: Fix-now — Qualify the summary as Chrome-linked recording, name the offline-unverified and desktop fallbacks, and describe D5’s specific pause triggers. /fix decision: Applied — /fix notes: all four class-check sites qualified:
  - `PLAN.md:135` (the delivery note): a Chrome-linked recording starts from a verified note or an `unverified_offline` one; a desktop Start is unlinked and cannot be written back; D5's triggers are listed; a separate non-Cliniko tab does not pause; any recording pauses on system sleep.
  - `PLAN.md:47` (step 9): "met by construction" is scoped to a Chrome-linked recording, and the desktop exception is named.
  - `docs/security/intended-use.md` (current scope note): the same as `PLAN.md:135`.
  - `AGENTS.md:60` (Current Status): the same, condensed.

  Verified against `encounter.py:763-770` (`start_context`), `context_rules.py:55-68` (`PauseReason`) and `162-166`. Sibling sites: `PLAN.md:128` is the original spec text, left as it is (the LEG 1 class check). /fix date: 2026-09-28. /fix applied by: Claude Code
- **PR-LOW-281** (LOW, docs-only, `docs/security/incident-process.md:61`): The recovery checklist retains an unconditional zero-connections idle check, so legitimate Chrome-driven verification can fail its stated recovery gate. — Evidence: “connection from either desktop process while the app is idle”; `docs/security/data-flow-map.md:745` explains that an open treatment note “verifies it once that report arrives” and line 747 qualifies the no-sockets checks as “with no Chrome link”. In `desktop/src/scribe_desktop/ui/bridge.py:610`, a report’s verification request is dispatched without a recording-state condition. Recommendation: Fix-now — Require no Chrome link and no pending practitioner-triggered verification for the zero-connections check, matching the data-flow qualification. /fix decision: Applied — /fix notes: `docs/security/incident-process.md` Recover step 1. The `netstat` check now applies "with Chrome closed, so no Cliniko note report arrives, and no practitioner action such as a Validate", and it says that a note open in Chrome is verified with Cliniko when its report arrives, which is expected.

  Verified: a grep for unconditional idle-zero statements across `docs/security`, `AGENTS.md` and `PLAN.md` leaves only the contract's own name (`data-flow-map.md:12`, `threat-model.md:1295`), which is qualified beside it. Sibling sites: none. /fix date: 2026-09-28. /fix applied by: Claude Code
- Verification counts: 2 claims checked, 2 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-8-exec-h3)

- **PR-LOW-280** (peer: LOW, docs-only) — materiality=docs-only severity=LOW surface=docs rec=Fix-now — confirmed:
  - `encounter.py:765` admits `unverified_offline`;
  - a desktop Start makes an unlinked recording;
  - `context_rules.py:162-166` pauses a LINKED recording only on a change to its bound tab (note, patient, leave, close), another NOTE focused, the login page, the pipe dropping or a new client. Focusing a separate non-Cliniko tab returns `None`.

  **Class check** (`PLAN.md`, `docs/security/*`, `AGENTS.md`; greps for "starts only from", "only from", "verifies, behind" and "any patient, note, tab") found the same overstatement at four sites:
  - (1) `PLAN.md:135`, the delivery note (the peer's site);
  - (2) `PLAN.md:47`, the step 9 addendum, also a Phase 8 edit: "recording starts only from an open Cliniko treatment note";
  - (3) `docs/security/intended-use.md:47`: "recording from an open treatment note that Cliniko verifies";
  - (4) `AGENTS.md:60`, Current Status: "Recording starts only from an open Cliniko treatment note verified through…".

  Clean at the other sites:
  - `threat-model.md:1664` and `design-system.md:77` say the patient LABEL comes only from a verified note, which is accurate;
  - `PLAN.md:128` ("every patient-context change") is the original Phase 5 spec text, not a Phase 8 edit, so it stays.

  **Shape:** at sites (1)–(4), say "a Chrome-linked recording starts from an open Cliniko treatment note that Cliniko verifies (or, offline, `unverified_offline`); a recording started on the desktop is unlinked and cannot be written back". At (1) and (3), replace "any patient, note, tab or login change" with D5's triggers and add "switching to a non-Cliniko tab does not pause". At (2), state that the "already open" point holds for a LINKED recording. Docs only, no test.
- **PR-LOW-281** (peer: LOW, docs-only) — materiality=docs-only severity=LOW surface=docs rec=Fix-now — confirmed:
  - `incident-process.md:60-61`'s recovery gate says "`netstat` shows no connection from either desktop process while the app is idle", with no condition.
  - `ui/bridge.py:607-611` dispatches a verification on a report from the bound tab whatever the recording state.
  - The same file's own trigger bullet (lines 29-33, fixed in round 45 LOW-036) and `data-flow-map.md:745-747` already qualify it.

  **Class check** for unconditional idle-zero statements: `threat-model.md:1322` ("asserts zero connections") describes the no-sockets test's own scope and is clean. There are no other hits.

  **Shape:** qualify the recovery check as "with Chrome closed (no Cliniko note report) and no practitioner action, e.g. no Validate". Docs only.
- Cap verdict: accept — docs-only — two LOW wording fixes at five named sites, no code or test change; the code behaves as D5, D4 and the offline contract state it.
- Final dispositions (leg stage-8-exec-h4 /fix; composer `OWNERSHIP: auto-disposition`):
  - PR-LOW-280 → Applied at all four sites (`PLAN.md:47`, `PLAN.md:135`, `intended-use.md` scope note, `AGENTS.md:60`).
  - PR-LOW-281 → Applied (`incident-process.md` Recover step 1).
- Fix-delta self-check: PASS — re-read 5 applied hunks across 4 files. Each trigger list matches `PauseReason` and `_rule`: system sleep is stated for ANY recording, and the rest for a LINKED one. No site claims a desktop start can be written back. The incident trigger bullet (round 45 LOW-036) and the new recovery condition agree.

### Round 48 - 2026-09-28 - Phase 8 security docs and clipboard exclusion (confirmation of rounds 46-47), independent cross-family codex peer review (pass stage-8.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Scoped confirmation of the supplied fix diff and permitted current implementation; static reading only, no writes, tests or network. No new findings.
- Confirmations: PR-LOW-270 **CONFIRMED** — `desktop/tests/test_ui_screens.py:6320` requires `platformName() == "offscreen"`; lines 6325–6336 reject native Copy and pass other keys to the saved handler, with both class patches restored by `monkeypatch`. The tests at lines 6642 and 6665 check pass-through and deliberately removed interception; line 6686 requires `payloads == [] and mimes == []`. Removing interception fails the first test at its Copy call and the second at its required `monkeypatch.delattr`. Positive tests remain substantive: line 6557 requires `len(mimes) == len(bindings)`, followed by exact text and format assertions. PR-LOW-271 **CONFIRMED** — `docs/security/intended-use.md:72` states “third-party clipboard manager may ignore them”; lines 73–75 name replacement-only retention, no clearing and unmarked drag-and-drop, matching the limitations recorded in round 46’s verified tuple. PR-LOW-280 **CONFIRMED** — `PLAN.md:47` scopes the already-open claim to “a Chrome-linked recording” and names the desktop exception; `PLAN.md:135`, `AGENTS.md:60` and `docs/security/intended-use.md:47` distinguish verified/offline starts, unlinked desktop starts and the bounded pause rule. These agree with `desktop/src/scribe_desktop/encounter.py:765` (“verified or `unverified_offline`”) and `desktop/src/scribe_desktop/context_rules.py:162`–166, where another focused note or login pauses, otherwise `return None`. PR-LOW-281 **CONFIRMED** — `docs/security/incident-process.md:61` conditions the check on “Chrome closed” and “no practitioner action such as a Validate”; lines 63–64 explicitly allow report-triggered verification, matching the data-flow qualification quoted in round 47. Cross-document comparisons used those permitted round records, without reopening excluded files.
- Verification counts: 4 claims checked, 4 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-28

### Round 49 - 2026-09-28 - Smoke fix: sleep and screen-lock pause (D5 as amended 2026-09-28), `/review-loop` round 1 of cap 3

- Round status: Closed (0 pending) — 1 LOW, Fix-now, applied in this leg. Pytest is owed to the composer.
- Source: Claude Code (executor leg stage-8-exec-h5, claude-opus-5-5, sequential lenses in-session — no subagents)
- Scope / baseline: this fix's diff only, on top of the uncommitted Phases 4–8 tree.
  - Code: new `system_events.py`; `context_rules.py` (`LOCKED`, `SYSTEM_REASONS`, `WM_WTSSESSION_CHANGE` / `WTS_SESSION_LOCK`, `is_lock_message`); `ui/main_window.py` (`_session_locked_q`, `attach_system_pause` / `detach_system_pause` / `_on_session_locked`, the `nativeEvent` branch, `closeEvent`); `app.py`; `ui/bridge.py` (`pause_for` clears a waiting "Resume previous" on a system reason, `set_system_pause_status`, the view); `ui/models.py` (the `locked` cue, `SYSTEM_PAUSE_FAILED_LINES`, `ChromeView.system_pause_failed`); `extension/src/panel-view.ts` and `page.ts` (the `locked` text).
  - Tests: new `test_system_pause.py`; `test_ui_bridge.py`; `test_context_rules.py`; `test_hands_free.py` (the `app.main` start-up test now uses a fake system registrar); `panel-view.test.ts`; `page.dom.test.ts`.
  - Docs: the plan's D5 addendum and Task 5.1 line; threat model; design system; CHANGELOG; AGENTS.md.
- Lenses and results:
  - **Never raises into Qt — CLEAN.**
    - The new `nativeEvent` branch sits inside the one `try`, and every message still returns `(False, 0)` (`test_the_override_never_raises_into_qt`, with a raising `lock_matches`).
    - The lock only emits a queued signal; the pause runs outside Windows' dispatch.
    - `SystemPauseWatch.register` / `unregister` swallow every registrar error (the refused, raising and raising-unregister tests).
    - `Win32SystemEventRegistrar` on a Windows without `RegisterSuspendResumeNotification` fails at `_user32()` inside `register`'s `try`, so it becomes a status.
  - **Registration lifetime on every exit path — CLEAN.**
    - Registered once the handle exists (`int(self.winId())`, before `show()`, as the hotkey is).
    - Given back on an ACCEPTED close (`closeEvent`, next to `detach_hotkey`), at quit (`aboutToQuit`), and in `app.py`'s `finally` if start-up fails after this point (`test_a_start_up_failure_after_attach_gives_the_chord_back` now also pins the four registrar calls).
    - Unregister is idempotent and gives back only what Windows accepted.
    - A refused close keeps them, correctly, since the window stays.
    - The bridge attached before the registration (`_start_chrome_link` runs first) receives the status from `attach_system_pause`.
  - **No resume on unlock — CLEAN.** `is_lock_message` matches `WTS_SESSION_LOCK` only; an unlock reaches no branch (the window test and the real-dispatch child both send one). No report path resumes: the rule never resumes, and `resume_refusal` still guards every Resume.
  - **A lock during a "Resume previous" window or a block cannot resume anything — found LOW-038; the resume half was CLEAN.**
    - `ChromeBridge.pause_for` clears `_pending_resume` for `SYSTEM_REASONS` before anything else, so the note's report arriving behind a locked screen resumes nothing (`test_a_suspend_or_lock_ends_a_waiting_resume_previous`).
    - Only the system reasons end the click: `test_a_chrome_reason_leaves_a_waiting_resume_previous` covers the tab passing through other pages on its way back.
    - LOW-038 is the block's REASON, not a resume.
  - **One pause per event — CLEAN.**
    - Suspend is handled synchronously and the lock is queued; whichever runs second finds the session PAUSED: an unlinked one does nothing, a linked one is not a `new_block`, so there is no second cue.
    - The classic and registered suspend are the same message (`test_both_suspend_routes_and_a_lock_make_one_pause`, which also sends the resume broadcast).
  - **Test honesty (would a test pass with the registration removed?) — CLEAN.**
    - `test_a_window_registers_nothing_and_ignores_a_lock_until_attached` is the control: the same lock message pauses nothing without the registration.
    - Every lock test needs `lock_matches`, which needs an accepted registration.
    - The real-dispatch child prints `UNREGISTERED []` before registering.
    - Removing `app.py`'s call fails the start-up test's registrar-call pin.
    - The Win32 argument test checks `DEVICE_NOTIFY_WINDOW_HANDLE` / `NOTIFY_FOR_THIS_SESSION` against a stand-in DLL.
    - What no test can prove — Windows DELIVERING the messages on this hardware — is named in the new module's, the test module's and the child test's docstrings, and in the threat model's residue (3).
- Findings:
  - **[LOW]** LOW-038: `desktop/src/scribe_desktop/ui/bridge.py` `pause_for`. A lock (or suspend) on a linked recording already blocked for a patient change overwrote the block's reason ("latest reason wins"). The full-page block and the side panel then read "The computer was locked." instead of "This tab opened a different treatment note." when the practitioner came back. Nothing unsafe followed (both patients stay side by side, and Resume previous still needs the matching report), but it hid the reason that matters. The lock made this far more likely than suspend alone — materiality=ux surface=production.
    - Triage: Fix-now.
    - Decision: Applied. A system reason names the block only when it STARTS one (`new_block`); a Chrome reason still renames it.
    - Tests: `test_a_system_reason_names_a_block_it_starts_but_a_chrome_one_renames` (new), and `test_a_suspend_or_lock_ends_a_waiting_resume_previous` now pins that the `note_changed` reason and its one cue stay.
    - Docs: the threat model's pause-rule paragraph.
- Checked and not raised:
  - Qt recreating the main window's native handle would leave both registrations (and the hotkey) on a dead HWND. Nothing in `ui/` calls `setWindowFlags` / `setParent` on the main window or re-creates it, so this is not reachable today.
  - Remote disconnect and fast user switching send other `WTS_*` codes (not handled); a lock precedes a console switch.
  - A display turning off without a lock, and sign-in on wake set to "Never", are the named residue (3).
  - The lock is queued while the suspend is synchronous: this is deliberate. The practitioner's instruction queues the new message like the hotkey press, and the suspend's synchronous path is the unchanged Phase 5 behaviour whose tests stay green.
  - The refusal lines show on the Session screen's Chrome area, which exists whenever the bridge does — always in `app.main`.
- Verification counts: 6 lenses run, 1 candidate, 0 dropped, 0 downgraded
- Missed-issue pass (auditable): re-read `SystemPauseWatch` against its fake-registrar tests; `app.py`'s order (`_start_chrome_link` → `attach_hotkey` → `try` → `attach_system_pause`); `log_event`'s key whitelist (`state=` only; the first draft's `suspend=` / `lock=` keys would have raised `ValueError` at start-up and were replaced before any check ran — two events, `suspend_notification` / `lock_notification`). Result: none.
- ruff clean; mypy 50 files (the new module), no issues; extension `npm run typecheck` and `npm run lint` clean. Pytest and vitest are owed to the composer.
- Last reviewed: 2026-09-28

### Round 50 - 2026-09-28 - Smoke fix: sleep and screen-lock pause, `/review-loop` round 2 of cap 3 (confirmation of LOW-038)

- Round status: Closed (0 pending) — clean
- Source: Claude Code (executor leg stage-8-exec-h5, claude-opus-5-5, in-session)
- Scope / baseline: the LOW-038 hunk in `ui/bridge.py` `pause_for` and its two tests, plus a re-read of round 49's six lenses over the whole fix after it.
- Lenses and results:
  - **LOW-038 — CONFIRMED FIXED.** Each block case holds:
    - No block → a system reason starts and names it.
    - A block of ANOTHER (stale) session → replaced (`new_block`).
    - Chrome's block on this session → a system reason keeps its reason and adds no cue (`paused` false, `new_block` false).
    - A Chrome reason → renames as before (`test_paused_already_only_blocks_and_cues_once` unchanged).
    - The pending-resume clearing still runs first, whatever the block does.
  - **The six lenses** over the post-fix diff — CLEAN: nothing in the hunk raises, touches a registration or resumes, and it adds no pause.
- Findings: none
- Verification counts: 6 lenses re-run, 0 candidates
- ruff clean; mypy 50 files, no issues.
- Last reviewed: 2026-09-28

### Round 51 - 2026-09-28 - Smoke fix: Modern Standby sleep and session-lock pause, independent cross-family codex peer review (pass stage-8.p2)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Specified smoke-fix diff and permitted current-file context; registration, lifetime, pause/resume ordering, tests and documentation reviewed by reading only. No tests run or files written.
- **PR-MED-300** (MED, behavioral, `desktop/src/scribe_desktop/ui/bridge.py:429`): Lock cancels an already-established pending resume but does not prevent a delayed resume command from restarting recording behind the locked screen. A `resume_previous` click still travelling through Chrome/native messaging when the lock is processed can subsequently recreate `_pending_resume`; a matching report then resumes recording without another lock event to pause it. — Evidence: lock handling calls only `self.pause_for(PauseReason.LOCKED)` (`desktop/src/scribe_desktop/ui/main_window.py:518`); the system-reason branch clears only `self._pending_resume = None` (`bridge.py:429–430`); `_resume_previous` later unconditionally assigns `self._pending_resume = _PendingResume(session.session_id, self._clock())` (`bridge.py:800`). `resume_refusal` checks connection and note identity but no locked state (`bridge.py:455–463`), and `_resume_if_pending` calls `self._screen.on_resume()` (`bridge.py:549`). The new test establishes the pending command **before** locking (`desktop/tests/test_ui_bridge.py:1180–1184`), so it misses this ordering. Recommendation: Fix-now — Track session-lock state and refuse resume requests while locked; unlock should clear that guard without resuming. Add a fake-registration regression covering lock → delayed resume command → matching report, including the shared hotkey resume path. /fix decision: Applied — /fix notes:
  - `system_events.py`: the lock flag (`note_lock` / `note_unlock` / `locked` / `lock_state`); `query_locked` on the registrar seam, with `Win32SystemEventRegistrar.query_locked` via `WTSQuerySessionInformationW` + `WTSSessionInfoEx` (ctypes' own `WTSINFOEXW` layout, `SessionFlags` only, buffer freed); `LOCK_RECHECK_AFTER_SECONDS = 5.0`; the flag is cleared by `unregister`.
  - `context_rules.py`: `WTS_SESSION_UNLOCK`, `is_unlock_message`.
  - `ui/main_window.py`: `nativeEvent` sets the flag on the lock message before emitting the queued pause, and clears it on the unlock (resuming nothing); `_lock_refusal` is handed to the bridge in `attach_chrome_link`; `session_locked`.
  - `ui/bridge.py`: `set_lock_refusal`; `resume_refusal` returns `locked` / `lock_unknown` FIRST, for every session; `_resume_previous` refuses before creating a pending resume; `_resume_if_pending` drops a pending resume on a lock refusal.
  - `ui/models.py`: `CHROME_REFUSALS["locked"]` / `["lock_unknown"]`.
  - Tests (fakes only): +19 in `test_system_pause.py` (`TestLockFlag`, `TestSessionInfoQuery`, six window tests, and the child now prints `FLAGS [true, false]`) and +4 in `test_ui_bridge.py` (the peer's ordering, a waiting click dropped on the flag, and Chrome `resume` refused under both codes, each with its unlocked control).
  - Verified: ruff clean; mypy 50 files; extension typecheck and lint clean (no extension change). Pytest is owed to the composer.
  - Sibling sites: every resume path goes through `resume_refusal`; `open_review` (not a resume) is unchanged.

  /fix date: 2026-09-28. /fix applied by: Claude Code
- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-8-exec-h6)

- **PR-MED-300** (peer: MED, behavioral) — materiality=behavioral severity=MED (verified) surface=production rec=Fix-now — the race is real.
  - **The command path.** A panel or block click → the service worker (`hub.ts:349-352`, the command carries `session_ref` + `state_rev`) → the native host → the pipe thread, which emits `_message_q` (a QUEUED connection, `bridge.py:284-289`) → `_on_message` → `_on_command` (`bridge.py:717`). There, `resume_previous` is checked only for `session_ref` and busy (`:726-735`), and `_resume_previous` assigns `_pending_resume` unconditionally for a PAUSED linked session (`:800`), then calls `_resume_if_pending` (`:801`).
  - **The lock path.** `WM_WTSSESSION_CHANGE` → `nativeEvent` emits `_session_locked_q` (also queued) → `pause_for(LOCKED)` clears `_pending_resume` (`:429-430`). So a command already queued (or still in Chrome / the host) when the lock is handled runs AFTER that clearing and re-creates the pending resume. `_resume_if_pending` (`:531-550`) then resumes on the first report naming the note: at once if the tab already shows it, or when Chrome's navigation for "Resume previous" completes behind the locked screen.
  - **The same hole on the plain `resume` command.** A `resume` in flight at the lock: the lock on a PAUSED session changes no state, then `_on_command` → `resume_refusal()` (`:455-463`: pipe and note identity only) → `SessionScreen.on_resume` → resumed.
  - **Harm and likelihood.** The recording restarts while the practitioner is away, capturing the room into the previous patient's session — exactly what the lock pause exists to stop. The window is narrow (a click made in the moment before a lock), hence MED, not HIGH.
  - **Why `state_rev` does not close it.** Every command carries `state_rev`, but only Start checks it (`:806`). A lock on an already-blocked PAUSED session publishes an IDENTICAL snapshot (round 49 LOW-038 keeps the block's reason), so `state_rev` does not move. A `stale_state` check on `resume` / `resume_previous` would miss exactly this case.
  - **Class check — every resume path while locked or asleep.**
    - They all end in ONE funnel: `SessionScreen.on_resume` runs its resume guard first (`session_screen.py:319-327`), and the bridge installs that guard (`bridge.py:295`, `_resume_guard_message` → `resume_refusal`). That covers:
      - (1) the desktop Resume button;
      - (2) the hotkey (`MainWindow.on_hotkey` → `session_screen.on_resume`);
      - (3) Chrome's `resume` command (`resume_refusal` then `on_resume`);
      - (4) a pending "Resume previous" completing on a report (`_resume_if_pending` → `resume_refusal` → `on_resume`).
    - (5) `resume_previous` itself never resumes, but it creates the pending resume.
    - Who can reach the funnel while locked:
      - The Resume button cannot be pressed behind a locked screen, but it shares the funnel, so it gets the check for free.
      - A hotkey press cannot be made on the secure desktop. A WM_HOTKEY posted before the lock message is delivered before it, in queue order.
      - A Chrome command or a pending resume CAN arrive while locked.
    - **Recommendation: a "locked until unlock" flag checked at the funnel, not a Chrome-only refusal.** Refusing only the Chrome paths would leave the funnel's other callers to reasoning about Windows' secure desktop and queue order. One check at the one guard costs nothing and covers every path by name, including any future one.
  - **Fix shape.**
    - `context_rules`: `WTS_SESSION_UNLOCK = 0x8`, `is_unlock_message`.
    - `MainWindow.nativeEvent`: sets a `_session_locked` flag SYNCHRONOUSLY on the lock message (a bool assignment inside the existing `try`), so every queued command handled after the lock message is dispatched sees it, before the queued pause runs. It still queues the pause. On `WTS_SESSION_UNLOCK` (only while the lock registration stands) it clears the flag and resumes NOTHING. `detach_system_pause` clears the flag.
    - The flag is pushed to the bridge (`set_session_locked(bool)`).
    - `resume_refusal()` returns `"locked"` FIRST, for linked AND unlinked sessions (today it returns None for an unlinked one before any check).
    - `_resume_previous` refuses `"locked"` before it creates the pending resume.
    - `_resume_if_pending` drops the pending resume on `"locked"` rather than waiting.
    - New refusal code `locked` in `models.CHROME_REFUSALS`: "The computer is locked - sign in, then press Resume." The desktop shows the same text through the guard (`on_resume` shows the refusal), and the hotkey path flashes it.
    - No protocol change: `last_refusal.reason` is a pattern-checked code. The panel shows the app's own message.
  - **No suspend flag.**
    - On S3 the process does not run. On Modern Standby, standby with sign-in required LOCKS first, so the lock flag covers it (the practitioner's smoke machine locked).
    - A "suspended until resumed" flag would need a trustworthy user-present resume signal. `PBT_APMRESUMEAUTOMATIC` also fires on unattended wakes, and `PBT_APMRESUMESUSPEND` is not reliably sent on Modern Standby. So a flag would either stick forever or clear on an unattended wake.
    - Instead, the threat model's residue (3) gains one clause: a Chrome command in flight at a suspend WITHOUT a lock (sign-in on wake "Never") can apply after wake.
  - **Regression tests** (fakes only):
    - (a) bridge: locked → a `resume_previous` command is refused `locked`, no pending is created, and a later matching report resumes nothing. This is the peer's ordering: lock FIRST, then the delayed command.
    - (b) bridge: locked → a Chrome `resume` with a matching report is refused `locked`.
    - (c) an unlinked recording: locked → `session_screen.on_resume()` and `MainWindow.on_hotkey()` are both refused with the locked message, and nothing reaches the controller.
    - (d) window: `nativeEvent(lock)` sets the flag BEFORE `processEvents` (`bridge.resume_refusal() == "locked"` with the pause still queued).
    - (e) unlock clears the flag and resumes nothing; the next Resume works.
    - (f) a refused lock registration never sets the flag (named residue).
    - (g) the real-dispatch child also sends an unlock and prints the flag.
    - Controls: the existing `test_resume_previous_waits_for_the_recordings_own_note` and the unlocked Resume tests show that the same commands resume when not locked.
- Cap verdict: accept — production-behavioral — one verified MED with a contained fix at the single resume funnel plus `_resume_previous`, about 7 regression tests, no protocol change; a scoped codex confirmation of the fix follows within pass stage-8.p2.
- **Final disposition** (leg stage-8-exec-h7 /fix; composer `OWNERSHIP: auto-disposition`): PR-MED-300 → Applied, in the LEG 1 shape plus the composer's no-stuck-flag addition. The guard chosen, and why:
  - A lock flag older than `LOCK_RECHECK_AFTER_SECONDS` (5 s) is re-checked with Windows (`WTSSessionInfoEx` → `SessionFlags`) when a Resume meets it. It clears only on Windows' "unlocked"; an unanswered check refuses as `lock_unknown`, whose text names the escape (lock and sign in again, which sends a fresh unlock).
  - The 5 s young-flag window is deliberate. A query racing the lock notification itself must not clear the flag in exactly the sub-second window PR-MED-300 is about; a missed unlock is a minutes-scale case.
  - The flag is NOT cleared on `WTS_SESSION_LOGON` / `WTS_CONSOLE_CONNECT`, contrary to the composer's suggestion:
    - a LOGON of this app's own session cannot happen while the app runs in it;
    - a CONSOLE_CONNECT (switching back to the session) lands on the LOCK screen until the user signs in, and is followed by `WTS_SESSION_UNLOCK`. Clearing on it would reopen the gap.
    - The lazy re-check covers any missed unlock instead.
  - The panel needed no change: its refusal line is the app's own `last_refusal.message` (`panel-view.ts`), so the text arrives from `CHROME_REFUSALS`.
- Fix-delta self-check: PASS — re-read 5 applied hunks across 5 files.
  - The flag is set inside `nativeEvent`'s existing `try`, before the queued emit.
  - `resume_refusal`'s new first check runs for unlinked sessions too, and the unlocked path is unchanged (the controls in both new bridge tests resume).
  - `_resume_if_pending` drops the pending resume only on the two lock codes; other refusals still wait.
  - `lock_state` never raises (query errors → `unknown`); `unregister` clears the flag.
  - No hunk touches the pause path, the registrations or the protocol.

### Round 52 - 2026-09-28 - Smoke fix confirmation: the lock flag against resume behind a locked screen, independent cross-family codex peer review (pass stage-8.p2)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Specified fix diff and permitted current-file context. PR-MED-300 confirmed closed: synchronous lock flag, shared resume refusal, delayed-command rejection and pending-resume cancellation. Reviewed query signatures, Unicode layout, buffer cleanup, five-second guard, failure refusal, notification handling, regression tests and documentation. Windows 7’s flag inversion does not apply to Windows 11; logon and console-connect correctly do not clear the flag. Panel implementation was outside the permitted files; the app’s refusal lookup and outgoing message were verified. Static review only; no tests, network operations or writes.
- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-28

### Round 53 - 2026-09-28 - Hardening H1: Phases 1–8 as one surface (cross-phase seams), `/review-loop` round 1 of cap 3

- Round status: Closed (0 pending). 2 MED + 11 LOW, all Fix-now, all applied in this leg. Pytest and vitest are owed to the composer.
- Source: Claude Code (executor leg stage-9-exec-k1, claude-opus-5-5). Six parallel read-only lens subagents (the same model: lens diversity, not model diversity); verification, dedupe and triage done in this session.
- Scope / baseline: `git diff f9887a7 -- . ':!.cursor'` plus every untracked file. That is Phases 1–3 committed and Phases 4–8 plus the smoke fix uncommitted: 86 tracked files (~16.7k insertions) and 36 untracked. Lockfile (`extension/package-lock.json`) skipped.
- Lenses and results:
  - **(a) Custody and key lifetime** (encounter → session → Unreviewed → review → Copy) — found LOW-040 (and its recovered-release sibling) and LOW-047; all other questions CLEAN:
    - The lease and discard reservation guard every retire, adopt and complete path.
    - The adopted session is protected as live; a recovered checkout is protected through `protected_session_ids`.
    - `encounter.enc` is decrypted at exactly three sites: `session.py` `adopt_queued`, `ui/main_window.py` `_open_checkout_encounter`, and `models.reconstruct_reminder_entries`, which only `app.main` calls, once.
    - Consent is written before audio on every start, and the tick is cleared on every Start.
    - `writeback_context` refuses unlinked, unverified, not-re-verified and rev-stale sessions. Its freshness gap is recorded for the write plan (below).
  - **(b) Every Resume path and pause source through the one guard** — found MED-039; all other questions CLEAN:
    - PAUSED → RECORDING has one controller entry, `resume()`, whose only caller is `SessionScreen.on_resume`, and its guard runs first.
    - Every pause source reaches `pause_for`.
    - The lock flag cannot stick silently.
    - The spoken-pause cutoff moves on every Resume path (`session_resumed`).
    - Several sources firing together keep the block consistent.
  - **(c) The Chrome link end to end** — found LOW-042, LOW-043 and LOW-044; all other questions CLEAN:
    - The mirrors agree with `meta.json` field by field, and every code the app sends matches the shared code pattern.
    - Stale results are dropped by tag or identity on the GUI thread.
    - Every session-bound action is checked by `session_ref` before its slot runs.
    - The nonce is stamped and stripped only by the host, and `app_running:false` only by the host.
    - Per-tab scoping holds, and display text is `textContent` only.
    - Reconnect clears the per-connection state.
    - Senders and `isTrusted` are checked.
  - **(d) The offline contract and the one-importer rule** — found LOW-045 and LOW-046; all other questions CLEAN:
    - Only `clinics.py` and `encounter.py` import the client, and none of the Phase 4–7 modules imports a network module; their `ctypes` loads are `kernel32`, `user32` and `wtsapi32` only.
    - No call happens at startup or idle on its own, apart from the named Chrome-report trigger.
    - The key is read once per call and never logged or retained.
    - The host's absence of `SSLKEYLOGFILE` handling is inert, because it has no TLS.
    - `clinic_rev` drops stale results on every path.
  - **(e) Docs vs code as a class** — found MED-041 and LOW-048 through LOW-051. There is no line-number drift: every doc cites by symbol, and each symbol was spot-checked.
  - **(f) Dead code and duplicated logic** — RECORDED FOR H2 below, not refactored and not counted.
- Findings:
  - **[MED]** MED-039: `desktop/src/scribe_desktop/ui/bridge.py` `_start` — a Chrome `start` is not refused while the computer is locked. This is PR-MED-300's class, for Start.
    - Classification: 🆕 (the round-51 fix covered the Resume funnel and `resume_previous` only).
    - Triage: Fix-now. Fix route: premium.
    - Why it matters: a Start clicked just before Win+L and handled after the lock's queued pause has run at IDLE or QUEUED (where `pause_action` does nothing) begins a NEW recording behind the locked screen, and nothing pauses it. That is exactly what D5's amended "a lock pauses ANY recording" exists to stop.
    - Current behaviour: `_start` checks state_rev, tab, verification, busy, lease and microphone, never the lock flag.
    - Desired behaviour: refuse `locked` / `lock_unknown` FIRST, before anything else, like `resume_refusal`.
    - Invariant: no path from a Chrome command reaches `SessionScreen.start_linked` while the main window's lock flag stands.
    - Pattern siblings: every command slot (searched `_locked_refusal|start_linked|def _start|_open_review|adopt_queued`).
      - `resume` and `resume_previous` are already guarded.
      - `open_review` installs QUEUED (no capture), so it is not affected.
      - The desktop Start cannot be pressed on the secure desktop, and a click queued before the lock is dispatched before it.
    - Decision: Applied.
      - The lock check is the first statement after the target assert (`ui/bridge.py` `_start`).
      - The `locked` / `lock_unknown` texts now say "…then press it again." (they now serve Start as well as Resume; `ui/models.py` `CHROME_REFUSALS`).
      - Test: `TestStart.test_a_start_is_refused_while_locked[locked|lock_unknown]`, with a verified report and the control "unlocked → the same Start records".
      - Docs: the threat model's LOCKED UNTIL UNLOCK paragraph and residue (3) ("a Chrome Resume or Start click in flight at the suspend"), the design system and CHANGELOG.
    - surface=production. User-visible: **side panel Start** (and the lock refusal wording on the Session tab, panel and hotkey).
    - /fix date: 2026-09-28. /fix applied by: Claude Code.
  - **[MED]** MED-041: `docs/security/intended-use.md` — a bare "It makes no connection at startup or while idle".
    - Classification: 🆕.
    - Triage: Fix-now.
    - Why it matters: the intended-use statement claimed more than the code. `hub.ts` re-reports every open Cliniko tab on each connection, so an app launched with a note open in Chrome makes a GET at startup with no practitioner action. Every other site carries that qualifier (threat model "Cliniko API client", flow 18, incident process, AGENTS.md step 8).
    - Pattern siblings (grep `at startup or idle|at startup or while idle|none at startup`):
      - `PLAN.md`'s delivery note: fixed.
      - The headline of the data-flow map and threat model: qualified later in the same section; left as the contract's name.
    - Decision: Applied. Both sites now say "on its own: every call answers a practitioner action or a report from Chrome", naming the startup case.
    - surface=docs. /fix date: 2026-09-28. /fix applied by: Claude Code.
  - **[LOW]** LOW-040: `ui/session_screen.py` `_start` — a Start that fails after the controller retired the queued session left that session out of the reminder index until restart. `session.py` `start` retires it before `CaptureWorker.start` can raise `DeviceLostError`, and `session_retired` was emitted only on success.
    - Decision: Applied. The failure path emits `session_retired(previous)` when the controller no longer tracks it. Test: `TestStartAtQueued.test_a_start_that_fails_after_retiring_still_announces_it`, which has a before-retirement failure as its control.
    - Sibling, applied: a RECOVERED linked session whose view a Start or a live transcript replaces without Complete or Discard was Unreviewed but unindexed. `ui/main_window.py` `_released_checkout_entry` / `_index_released` index it from the checkout's already-decrypted record and register its ref. Test: `TestRecoveredCheckout.test_a_checkout_released_without_complete_enters_the_index_if_linked[start|live_transcript × linked|unlinked]`, which also asserts that no decrypt happens.
    - Docs: threat model (the pause-rule paragraph), flow 19 and the retention row.
    - surface=production. User-visible: the **Unreviewed banner** in Chrome after a failed Start or a released recovered view.
    - Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-042: `ui/bridge.py` `last_refusal` — a refusal stayed in every snapshot until the next command. For example, a Start refused for A's final note sat under B's Ready panel.
    - Decision: Applied. `_Refusal.situation` captures the bound tab and target, the outcome's kind, the live `session_ref` and the state. `_current_refusal()` drops a refusal once any of these changes, and `build_content` and `view()` both use it.
    - Test: `TestStart.test_a_refusal_goes_when_what_it_was_about_leaves_the_screen`; its control is a `_tick` that keeps it.
    - `test_cross_patient.py` `test_a_second_pipe_client_pauses_and_must_report_the_note_first` now expects no refusal after the conn-2 report. The old client's dropped command is still pinned by the state and call assertions.
    - surface=production. User-visible: the **side panel refusal line** and the Session tab's "Refused from Chrome" line.
    - Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-043: `extension/src/page.ts` `REASONS.note_changed` — every allow-listed tab gets the block, but the text read "This tab opened a different treatment note."
    - Decision: Applied. The text now matches the panel's: "The recording's tab opened a different treatment note."
    - Updated: `page.dom.test.ts` and the design system.
    - surface=production. User-visible: the **page block card**. The extension needs a rebuild.
    - Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-044: `ui/bridge.py` `_one_line` and `encounter.py` `_display_text` — a lone surrogate from a JSON escape in a Cliniko name was not cleaned. It would fail the snapshot's validation, and `publish` drops such a snapshot silently, which freezes Chrome on the last one.
    - Decision: Applied. `Cs` joins the cleaned categories at both sites.
    - Test: `test_encounter.py` `test_a_lone_surrogate_in_a_name_becomes_a_space`.
    - surface=production. User-visible: patient names in the **side panel, block and Session tab** (in practice only for such data).
    - Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-045 (docs): the source-level network ban's list was not named as incomplete.
    - The list names `socket`, `http`, `urllib.request` and QtNetwork only. `asyncio`, the mail and ftp modules, `xmlrpc.client`, `multiprocessing.connection`, and `ctypes` or COM HTTP are not banned by name. None is used.
    - Decision: Applied. The threat model's CONFINEMENT residue names them. `ui/__init__.py`'s stale "no UI module imports it yet" now says how the UI reaches Cliniko.
    - surface=docs. Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-046 (docs): the per-note throttle bounds concurrency, not rate, and this was not named.
    - Rapid tab switching drops every answer, because the run moves on before any is reused. Refused, offline and 429 outcomes are never reused, and `RateLimited.reset` is not honoured.
    - Decision: Applied. The residue is named at the threat model's NOTE VERIFICATION throttle sentence.
    - A code throttle stays an H3 candidate.
    - surface=docs. Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-047 (docs): D2 and the retention row said a session reference goes on expiry. But `prune_reminders` forgets only INDEXED sessions, so an unlinked or failed recording's ref stays until process end. It resolves to no command.
    - Decision: Applied. The retention row now states exactly that.
    - A code fix needs a new controller listing API; it is an H2 candidate.
    - surface=docs. Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-048 (docs): "any recording pauses on system sleep" omitted the session lock at two sites.
    - Sites: `intended-use.md` scope note and `PLAN.md` delivery note.
    - Decision: Applied. Both now say "…or when Windows locks the session".
    - surface=docs. Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-049 (docs): `docs/design-system.md` Interaction posture listed only two close refusals, recording and enrolment.
    - Decision: Applied. It now lists paused, any running worker (the list `closeEvent` names), and the Unreviewed first-close refusal with its 10 s second close.
    - surface=docs. Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-050 (docs): `AGENTS.md` Current Status still said "Phases 4–7 BUILT … NEXT: Phase 8".
    - Decision: Applied. It now says Phases 4–8 BUILT, adds the Phase 8 and smoke-fix line, and gives NEXT as P.2 and the hardening stage. The Documentation Status line was updated too.
    - surface=docs. Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-051: an `extension/src/manifest.ts` comment cited "AGENTS.md step 8" for the full Chrome restart; it is step 7.
    - Decision: Applied.
    - surface=production (a comment only; no behaviour).
    - Triage: Fix-now; Decision: Applied.
- Recorded for H2 (lens f; per the leg brief, not counted, nothing refactored):
  - Drifted copies:
    - The block-reason table is held three times: `page.ts` `REASONS`, `panel-view.ts` `BLOCK_REASONS`, `models.PAUSE_CUES`. One copy had already drifted (LOW-043).
    - The product name is "Clinic Scribe" in the panel, page and User-Agent, but "Cliniko Scribe" in the window title, badge titles, manifest and desktop texts. This is a practitioner naming call.
    - `NOTE_REFUSALS` in `panel-view.ts` restates `models.NOTE_REFUSAL_REASONS` with different wording.
  - Test-only in production:
    - `ContextReporter.isTracked` / `active`
    - `main_window._is_suspend_event`
    - `session_locked` / `SystemPauseWatch.locked`
    - `ContextEvaluator.bound_tab`
    - `SpokenPauseDetector.cutoff_seconds`
    - `NewConsultationWatcher.raised`
    - `ChromeBridge.conn_gen`
    - `ERROR_HOTKEY_ALREADY_REGISTERED`
    - the `pipe_lost` signal (no production connection)
    - `panel-view.ts` `CHECKING`
  - Unreachable or unread:
    - The `not_available` refusal (production always passes both handlers).
    - The `notice` values `open_a_note` / `clinic_not_set_up`, which the panel recomputes itself.
  - Duplicated pipelines and constants:
    - Two re-verification pipelines: `main_window` `_dispatch_reverification` / `_run_reverification` / `_finish_reverify_task` against `bridge` `_dispatch` / `_run` / `_finish_task`. The "rev still current" check appears three times.
    - The `pause_for` fallback in `main_window` repeats the bridge's table application.
    - Display-text cleaning is written twice: `encounter._display_text` and `bridge._one_line` (both now include `Cs`).
    - The host → clinic lookup is written three times.
    - The id, host and clinic-id regexes are copied across `protocol` / `encounter` / `clinics` / `cliniko_client`.
    - `MAX_DISPLAY_NAME_CHARS` restates `LIMITS["max_display_chars"]`.
    - `"recording-consent-v1"` appears five times.
    - `isObject` exists three times in TypeScript.
    - `RELAYED_TYPES` == `INBOUND_TYPES`.
    - `pipe_client` imports `pipe_server`'s private Win32 helpers (seam: `win32_pipe.py`).
    - The discard arm/disarm logic is copied between `page.ts` and `panel.ts`.
    - `state in (RECORDING, PAUSED)` appears eight times (seam: `LIVE_STATES`).
    - `review_open` and `review_in_progress` are two codes for one condition.
    - `_ACTION_CONTROL` is an identity map.
  - Oversized modules:
    - `ui/models.py` (3.5k lines; seam: `ui/chrome_text.py`).
    - `ui/main_window.py` (native events / reminders / re-verification).
    - `ui/bridge.py` (snapshot builders apart from commands).
  - Stale comments: `connection.ts` "(rendered by the Phase 6 UI)"; `main_window` "Phase 4's entry" (meaning the draft-write plan).
  - The LOW-047 code fix.
- Recorded for H3 / the write plan:
  - LOW-046's code throttle: honour `RateLimited.reset`, and do not re-dispatch for the target already running or waiting.
  - The write-back freshness gap: `writeback_context` has no age bound; `recovered_writeback_target()` uses the checkout-time re-verification; `live_reverification()` is unwired. This is in Follow-Up Continuation Notes.
- Needs investigation (not a finding: no evidence it happens):
  - A `PBT_APMSUSPEND` dispatched RE-ENTRANTLY inside the GUI thread's `controller.start` (if opening the PortAudio stream pumps messages in a COM wait) would meet IDLE and be lost, so the recording would come back after wake unpaused.
  - A lock is safe here, because its pause is queued.
  - Unconfirmed whether `sd.RawInputStream` / `stream.start()` pumps. A candidate for H3 or the live smoke.
- Dropped:
  - CHANGELOG's Phase 4 part 1 "18 valid, 47 invalid" is a dated entry, and the later part 2 entry states the current 19 / 49. Not a defect.
- Verification counts: 6 lenses (subagents), 19 candidates.
  - 1 dropped (the CHANGELOG count).
  - 1 downgraded to needs-investigation (the re-entrant suspend).
  - 1 merged as a sibling (the recovered release into LOW-040).
  - 3 routed to H2 or H3 as code follow-ups of docs-applied LOWs.
- Missed-issue pass (auditable): re-read `bridge.py` `_on_command` / `_start` / `_open_review` / `_resume_previous` / `build_content` / `view`; `session.py` `start` and `_retire_locked`; `session_screen.py` `_start`; `main_window.py` `_on_session_started` / `_on_live_transcript` / `_on_transcript_closed` / `_on_session_retired` / `prune_reminders`. Result: the recovered-release sibling of LOW-040 (merged into it).
- Fix-delta self-check: PASS. Re-read 9 applied production hunks across 7 files:
  - `_start`'s lock check runs before `state_rev`, and its refusal carries the post-check situation.
  - The failed-Start emit fires only when the controller no longer tracks `previous`. A refusal before retirement, including `_retire_locked`'s own refusal, leaves it tracked, so nothing is emitted.
  - `_released_checkout_entry` is computed before `_end_checkout_encounter` and applied only where the checkout is released and its id matches.
  - Every `_refuse` call runs after its attempt, so the situation is the post-attempt one. A Start that fails after retiring keeps its "failed" line.
  - No hunk touches custody ordering, a registration or the protocol.
- ruff: "All checks passed!". mypy: 50 files, no issues. Extension `npm run typecheck` and `npm run lint`: clean. Pytest and vitest are owed to the composer.
- Last reviewed: 2026-09-28

### Round 54 - 2026-09-28 - Hardening H1: post-fix regression and same-family sweep over round 53, `/review-loop` round 2 of cap 3

- Round status: Closed (0 pending) — 1 MED + 5 LOW, all Fix-now, all applied in this leg. Pytest and vitest are owed to the composer.
- Source: Claude Code (executor leg stage-9-exec-k1, claude-opus-5-5). Two read-only subagents were run: (1) a post-fix regression check of every round-53 change against its callers and the existing tests; (2) a same-family sweep of round 53's two classes (capture after a lock; a doc claim stronger than the code).
- Scope / baseline:
  - Primary: the same whole surface (`git diff f9887a7 -- . ':!.cursor'` plus untracked).
  - Regression: round 53's applied hunks, 9 production and the docs, located by symbol.
- Round classification: 0 🆕 / 3 ⚡ / 3 🔁.
  - ⚡ fix-induced: LOW-053 comes from LOW-042's situation; LOW-055 and LOW-057 come from MED-041's and LOW-048's new wording.
  - 🔁 same-family: MED-052, LOW-054 and LOW-056 are siblings of MED-039's class.
- Regression result per round-53 change:
  - MED-039: CLEAN.
  - LOW-040 and its sibling: CLEAN. No completed, discarded, adopted or unreleased session can be indexed; `register_session_ref` is safe; the tests' fake implements it.
  - LOW-042: LOW-053 (below).
  - LOW-043: CLEAN.
  - LOW-044: CLEAN.
  - Docs: see LOW-055 and LOW-057.
  - No existing test pins the old lock text or the old page text. None expects a refusal to survive a change of situation, apart from the one updated in round 53.
- Findings:
  - **[MED]** MED-052: `ui/session_screen.py` `_start` — the DESKTOP Start was not refused while the computer is locked. 🔁 of MED-039.
    - Triage: Fix-now. Fix route: premium.
    - Why it matters: Windows retrieves posted messages before queued input. A Start click (or Space on the button) queued while the GUI thread was busy at the moment of Win+L is dispatched AFTER the lock message has set the flag and its queued pause has run at IDLE. An unlinked recording then begins behind the locked screen, and nothing pauses it.
    - Current behaviour: the lock is checked only in `ChromeBridge._start` and the resume funnel.
    - Desired behaviour: every Start from the Session screen runs the lock check first.
    - Invariant: no path reaches `SessionController.start` from the Session screen while the lock flag stands.
    - Decision: Applied.
      - `SessionScreen.set_start_guard` is run first by `_start`, which both the desktop button and `start_linked` pass through.
      - The bridge installs `_start_guard_message`, which returns the lock refusal's text or None.
      - The bridge's own `_start` check stays, so a Chrome refusal still carries the `locked` code.
      - Test: `TestStart.test_the_desktop_start_is_refused_while_locked[locked|lock_unknown]`, with the unlocked control (an unlinked recording starts).
      - Docs: the threat model's LOCKED UNTIL UNLOCK ("every Start … the Session tab's button alike"), the design system, CHANGELOG, and the `models` comment.
    - surface=production. User-visible: the **Session tab Start** (refused only while the lock flag stands).
    - /fix date: 2026-09-28. /fix applied by: Claude Code.
  - **[LOW]** LOW-053 ⚡: `ui/bridge.py` `_situation` — the outcome kind in LOW-042's situation made a SESSION command's refusal vanish when a check of the same note landed. Example: "Resume previous" completing on the note's report with its check still running, then failing ("It did not work…"); the line disappeared about a second later.
    - Decision: Applied. The situation carries the action, and it includes the outcome kind only for `start`, whose refusals ("checking", "not verified") are about the verification.
    - Test: `TestResolution.test_a_failed_resume_previous_stays_shown_when_the_notes_check_lands`. It uses an offline transport, so the check is really in flight.
    - surface=production. User-visible: the **side panel refusal line**.
    - Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-054 🔁 (docs): a voice enrolment is not covered by the lock. A running one keeps capturing in memory up to its limit, and what is said in the room goes into the saved profile. D5 is worded for recordings, and no doc named this.
    - Decision: Applied as named residue in the threat model's lock paragraph.
    - Code option (stop, or refuse, an enrolment on lock) recorded for H3. It belongs to the practitioner-profile surface, beyond this plan's scope.
    - surface=docs. Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-055 ⚡/🆕 (docs): the reconnect trigger was left out of three texts.
    - The texts: MED-041's new intended-use sentence, the data-flow map's network non-flow ("a call follows only a practitioner action or a note report") and the incident trigger.
    - The code: a new pipe connection re-checks a LINKED recording's own note with no report and no action (`ChromeBridge._on_connected` → `_reverify_live`). Flow 18 and the threat model already said so.
    - Decision: Applied at all three sites.
    - surface=docs. Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-056 🔁 (docs): an unlock message is believed as delivered (`note_unlock`). A same-user program can forge `WTS_SESSION_UNLOCK` and clear the flag.
    - Decision: Applied as named residue under trust boundary 2, beside the forgeable `WM_HOTKEY`.
    - Querying Windows on unlock is recorded for H3. It would change the round-51/52 converged smoke fix.
    - surface=docs. Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-057 ⚡ (docs): LOW-048's new "any recording pauses on … when Windows locks the session" was unqualified in `intended-use.md` and `PLAN.md`. A refused registration or an undelivered notification does not pause.
    - Decision: Applied. Both now say "when Windows delivers those notifications", pointing at the threat model's residue.
    - surface=docs. Triage: Fix-now; Decision: Applied.
- Checked and clean (sweep):
  - `controller.resume` has one caller, which is guarded.
  - Resuming the live transcriber happens inside `resume` only.
  - Chrome's `resume`, `resume_previous`, a waiting "Resume previous", `start`, and `open_review` (QUEUED, no capture) are covered.
  - The hotkey never starts anything.
  - No timer starts or resumes.
  - The benchmark opens no microphone.
  - The level monitor is outside the class (level only, never stored, pre-existing).
  - `_lock_refusal` is None only before `attach_system_pause`, which runs before `app.exec()`.
  - `set_lock_refusal` is always installed.
- Verification counts: 2 lenses (subagents), 6 candidates, 0 dropped, 0 downgraded.
- Missed-issue pass (auditable): re-read `session_screen.py` `_start` / `on_start` / `start_linked` / `on_resume`; `bridge.py` `_situation` / `_current_refusal` / `_refuse` callers (`_on_command`, `_resume_if_pending`, `_start`, `_open_review`) / `_start_guard_message`; the threat model's lock paragraph as edited twice. Result: none.
- Fix-delta self-check: PASS. Re-read 4 applied production hunks across 2 files:
  - The start guard runs before the device check, so a refusal leaves no half-state; `on_start` has already cleared the tick, as for every Start.
  - `_situation(action)` is called with the refusal's own action on both sides of the comparison.
  - The guard is None when no bridge is attached, so tests and desktop-only behaviour are unchanged.
- ruff: "All checks passed!". mypy: 50 files, no issues. Extension `npm run typecheck` and `npm run lint`: clean. Pytest and vitest are owed to the composer.
- Last reviewed: 2026-09-28

### Round 55 - 2026-09-28 - Hardening H1: post-fix regression over round 54, `/review-loop` round 3 of cap 3 — CONVERGED

- Round status: Closed (0 pending) — 2 LOW (docs), Fix-now, applied in this leg. No CRIT, HIGH or MED, so the loop converged.
- Source: Claude Code (executor leg stage-9-exec-k1, claude-opus-5-5). One read-only regression subagent.
- Scope / baseline: primary is the whole surface as before. Regression covers round 54's applied hunks (the start guard, `_situation(action)`, the two new tests, the edited doc paragraphs).
- Round classification: 0 🆕 / 2 ⚡ / 0 🔁. Both LOWs come from round 54's doc edits and are docs only, so the loop is converging.
- Results:
  1. **Start guard — CLEAN.**
     - `SessionScreen._start` holds the only `controller.start(` in `desktop/src`. `on_start` and `start_linked` both pass through it, and the guard runs first.
     - `app.py` always attaches the bridge, even when the pipe is refused, so the guard is always installed.
     - No test installs a lock and expects a Start to succeed.
     - The screen guard cannot turn the bridge's named `locked` refusal into "failed". Both reads are synchronous on the GUI thread with no event loop between them, and `lock_state()` only ever clears the flag.
  2. **Refusal situation — CLEAN.**
     - All 27 `_refuse` sites run inside `_on_message`, directly or through `_on_context` / `_resume_previous` → `_resume_if_pending`, and each is published at least once with an unchanged situation.
     - `action` in the tuple is constant per refusal.
     - The only behaviour change is the intended one: a non-start refusal survives a check landing.
  3. **The two new tests — CLEAN.** Each fails with its fix reverted:
     - The desktop Start test's `started_with == []` assertion.
     - The resume-previous test. The offline outcome is never reused, so the A-note report dispatches a NEW run with outcome None, and the monkeypatched `resume` is the one `on_resume` calls.
  4. **Docs — 2 LOW, applied.** Every other new sentence was checked true against the code:
     - forged unlock (`nativeEvent` → `note_unlock`, no query);
     - enrolment (a 30 s speech target or a 90 s cap, and the profile is saved without a further click);
     - the reconnect trigger (`_on_connected` → `_reverify_live`, RECORDING/PAUSED only).
- Findings:
  - **[LOW]** LOW-058 ⚡: the `PLAN.md` delivery note still said "every call answers a practitioner action or a report from Chrome". This is LOW-055's class at a site round 54 missed.
    - Decision: Applied. It now includes "or — for a linked recording in progress — the Chrome link reconnecting".
    - The threat model's section header uses the general phrase but lists the reconnect trigger two sentences later, so it was left.
    - surface=docs. Triage: Fix-now; Decision: Applied.
  - **[LOW]** LOW-059 ⚡: the threat model's "A missed unlock cannot refuse Resume forever … a refused Resume asks Windows" also covers Start since MED-052, because both guards go through `lock_state()`. The same paragraph's hand-wrapping was broken, and one line in the data-flow map was overlong.
    - Decision: Applied. It now reads "Resume or Start", and the lines are re-wrapped.
    - surface=docs. Triage: Fix-now; Decision: Applied.
- Verification counts: 1 lens (subagent), 2 candidates, 0 dropped, 0 downgraded.
- Missed-issue pass (auditable): re-read the threat model's lock paragraph after the rewrap, the `PLAN.md` delivery note, and data-flow map lines 744–752. Result: none.
- Fix-delta self-check: PASS — re-read 3 applied doc hunks across 3 files. No production file changed in this round.
- Convergence: the round-3 review found no CRIT/HIGH/MED, and its findings are mostly ⚡ docs LOWs that were applied. The loop is done at the cap, with no further round owed.
- Last reviewed: 2026-09-28

### Round 56 - 2026-09-28 - Hardening H2: `/simplify` over Phases 1–8 as one surface, seeded by round 53's lens (f) list

- Round status: Closed for this leg. 3 LOW applied, all behaviour-neutral. 13 recorded (2 MED + 11 LOW) and routed to the new task H2a: a scoped `/review-plan` after the P.2 live smoke. Nothing was applied that restructures a production path, changes a user-visible string or moves logic between modules.
- Source: Claude Code simplify (executor leg stage-9-exec-k2, claude-opus-5-5). Run under the composer's smoke-time routing: apply only trivial, test-pinned, behaviour-neutral items; record everything else.
- Scope / baseline:
  - Surface: `git diff f9887a7 -- . ':!.cursor'` plus untracked files, the same surface as rounds 53–55.
  - Seed: round 53's "Recorded for H2" list. Each seed was re-checked against the current tree, with the search evidence given on the finding.
  - No skips.
- Simplifications found:
  - **[LOW]** SIMP-001 (applied): `extension/src/context.ts` `ContextReporter` (class at :109) carried two members with no caller: the `get active()` getter and `isTracked(tabId)`.
    - Search evidence: `reporter.active`, `.isTracked(` and `isTracked` have no hits in production or tests. The other `.active` hits are `tab.active` (Chrome's field) and the page-state `active` key.
    - Current: two public members, read by nothing.
    - Desired: removed.
    - Why behaviour-neutral: nothing reads them, and `npm run typecheck` would fail on any caller.
    - Pinned by: `npm run typecheck`, and `context.test.ts` / `hub.test.ts` unchanged.
    - Regression risk: none.
    - surface=production (dead code only).
    - Triage: Fix-now. /fix decision: Applied.
  - **[LOW]** SIMP-002 (applied): `extension/src/panel.ts:135` wrote the Checking layout's text as a second literal. `panel-view.ts` already exports it as `CHECKING`, which the round-53 list had called test-only.
    - Current: `"Checking with Cliniko…"` written again in `panel.ts`.
    - Desired: `panel.ts` imports `CHECKING` (:19) and uses it.
    - Why behaviour-neutral: the string is identical, so there is one source for it.
    - Pinned by: `panel-view.test.ts:129` and the panel DOM tests' Checking layout.
    - Pattern siblings: the other panel literals already come from `panel-view.ts`, so none were found.
    - Regression risk: none.
    - surface=production (same user-visible text, one source).
    - Triage: Fix-now. /fix decision: Applied.
  - **[LOW]** SIMP-003 (applied): stale comments at two sites.
    - `extension/src/connection.ts:122` said the state was "(rendered by the Phase 6 UI)". It now reads "The app's latest `state` snapshot, handed to the hub (`hub.ts`)".
    - The docstrings of `ui/main_window.py:1246` `recovered_writeback_target` and `:1257` `live_writeback_target` said "Phase 4's entry", which reads as this plan's Phase 4. They now name PLAN.md Phase 4's draft write, the next plan.
    - Pattern siblings: grep for `Phase 4's` across `desktop/src`. The `encounter.py` hits (:34, :833, :890) already say "the next plan" or mean the write itself. The `note_*` / `models.py` hits are the note-pipeline plan's own Phase 4. None are stale.
    - Why behaviour-neutral: comments and docstrings only.
    - Pinned by: n/a (not behaviour). ruff and mypy are clean.
    - surface=production (comments only).
    - Triage: Fix-now. /fix decision: Applied.
  - **[MED]** SIMP-004 (recorded): the block-reason text table is held three times: `page.ts` `REASONS` (:44–), `panel-view.ts` `BLOCK_REASONS` (:69–) and `ui/models.py` `PAUSE_CUES` (:445–).
    - One copy had already drifted (LOW-043). They still differ in the product name ("Clinic Scribe" in the two TypeScript copies, "Cliniko Scribe" in the desktop copy).
    - Why it matters: a duplicated user-visible invariant drifts.
    - Executor recommendation: one canonical table under `protocol/fixtures/` (for example `text/block_reasons.json`), read by a both-mirrors test that pins each copy to it. The TypeScript side could import it at build time. Do this after SIMP-006 settles the name.
    - surface=production (user-visible strings in the page, panel and desktop).
    - Triage: Fix-now → task H2a, a scoped `/review-plan` after the smoke. /fix decision: Pending.
  - **[LOW]** SIMP-005 (recorded): `panel-view.ts` `NOTE_REFUSALS` (:49–) restates `ui/models.py` `NOTE_REFUSAL_REASONS` in different wording.
    - Executor recommendation: the same fixture treatment as SIMP-004. The practitioner picks the wording once.
    - surface=production (user-visible strings).
    - Triage: Fix-now → task H2a. /fix decision: Pending.
  - **[LOW]** SIMP-006 (recorded; the PRACTITIONER'S naming call, nothing changed): the product name is split.
    - "Clinic Scribe" is used in:
      - `cliniko_client.py:101` `APP_NAME`, the User-Agent Cliniko's servers see;
      - `panel-view.ts` (11 strings);
      - `page.ts:44–45`.
    - "Cliniko Scribe" is used in:
      - `main_window.py:203`, the window title;
      - `app.py:53` and `:115`;
      - `ui/models.py` (8 strings);
      - the badge titles, `connection.ts:88–103`;
      - `manifest.ts:20` and `:26`, "Cliniko Scribe Companion".
    - Executor recommendation: standardise on **"Clinic Scribe"**, for three reasons:
      - It is already the name Cliniko sees in every API request.
      - The D1 mockups and panel copy use it.
      - It keeps Cliniko's trademark out of the product's own name ahead of the commercial path in PLAN.md.
    - Changing the manifest `name` does not change the extension id, which comes from its key.
    - One pass after the smoke, together with SIMP-004/005, since the same strings move.
    - surface=production (user-visible: window title, badge tooltips, the extensions page, desktop messages).
    - Triage: Fix-now → task H2a. It needs the practitioner's choice first. /fix decision: Applied (leg stage-9-exec-k8, 2026-09-28 — the practitioner chose "Clinic Scribe" (`OWNERSHIP: gate-disposition key=product-display-name choice=clinic-scribe`); every display string listed above renamed, plus `panel.html`'s title and `setup-models.py`'s docstring; every `ClinikoScribe` identifier unchanged; guard test `test_display_name.py`).
  - **[MED]** SIMP-007 (recorded): there are two re-verification pipelines.
    - `ui/main_window.py` `_dispatch_reverification` / `_run_reverification` / `_finish_reverify_task`.
    - `ui/bridge.py` `_dispatch` / `_run` / `_finish_task`.
    - The "rev still current" check is written three times. `main_window`'s `pause_for` fallback repeats the bridge's pause-table application.
    - Why it matters: stale-result dropping is a custody control, and two copies can diverge.
    - Executor recommendation: one worker-and-ledger helper owned by the bridge, which `main_window`'s checkout re-verification calls. Scope it at `/review-plan`, because it moves custody-adjacent logic between modules.
    - surface=production (bridge / re-verification; not user-visible).
    - Triage: Fix-now → task H2a. /fix decision: Pending.
  - **[LOW]** SIMP-008 (recorded): display-text cleaning is written twice, as `encounter._display_text` and `ui/bridge._one_line`. Both now clean `Cs` (LOW-044).
    - Executor recommendation: the bridge calls the encounter helper, with `_one_line` keeping only its length cut.
    - surface=production (moves logic between modules).
    - Triage: Fix-now → task H2a. /fix decision: Pending.
  - **[LOW]** SIMP-009 (recorded): duplicated constants and lookups.
    - The host → clinic lookup is written 3× (per round 53).
    - The id, host and clinic-id regexes are copied across `protocol` / `encounter` / `clinics` / `cliniko_client`.
    - `MAX_DISPLAY_NAME_CHARS` restates `LIMITS["max_display_chars"]`.
    - `"recording-consent-v1"` is a literal at 6 production sites:
      - `encounter.py:79` (the constant) and `:151` (a `Literal` annotation);
      - `protocol.py:207`;
      - `hub.ts:416`;
      - `protocol.ts:136` and `:342`.
      - Round 53 said 5. The `Literal` annotations need the literal, so the constant cannot replace all of them.
    - Executor recommendation: a small shared-ids module for the regexes and limits. Keep `cliniko_client.py` importing nothing new, so the TID251 confinement pin holds. The TypeScript consent literal should become one exported constant in `protocol.ts`.
    - surface=production (moves constants between modules).
    - Triage: Fix-now → task H2a. /fix decision: Pending.
  - **[LOW]** SIMP-010 (recorded): duplicated TypeScript helpers.
    - `isObject` exists in `hub.ts:110` and `page.ts:71`, beside `protocol.ts:206` `isPlainObject`. That is 2 plus 1 differently named; round 53 said 3.
    - The Discard arm/disarm logic is copied between `page.ts` and `panel.ts:216–260`.
    - Executor recommendation: export `isPlainObject` from `protocol.ts`, after checking that the page script's bundle may import it (`page.ts` is injected on its own). Put a shared `DiscardArm` in `panel-view.ts`.
    - surface=production (extension state).
    - Triage: Fix-now → task H2a. /fix decision: Pending.
  - **[LOW]** SIMP-011 (recorded): protocol-shaped duplicates.
    - `RELAYED_TYPES` equals `INBOUND_TYPES`.
    - `_ACTION_CONTROL` is an identity map.
    - `review_open` and `review_in_progress` are two refusal codes for one condition.
    - The `not_available` refusal is unreachable, because production always passes both handlers.
    - The `notice` values `open_a_note` / `clinic_not_set_up` are sent but unread, because the panel recomputes them.
    - Executor recommendation: the two Python aliases collapse freely. Merging a refusal code or dropping a notice value changes protocol v2 and its fixtures, so do that with the Phase 4 write plan's protocol bump, not alone.
    - surface=production (protocol).
    - Triage: Fix-now → task H2a. /fix decision: Pending.
  - **[LOW]** SIMP-012 (recorded): `state in (RECORDING, PAUSED)` is spelled at 8 sites:
    - `session.py:724`;
    - `voice_commands.py:145`;
    - `ui/bridge.py:527`, `:562` and `:613`;
    - `ui/main_window.py:902` and `:1050`;
    - `ui/microphone.py:38`.
    - The TypeScript variants are `connection.ts:241` and `page.ts:84`.
    - Executor recommendation: a `LIVE_STATES` frozenset in `session.py`. It is behaviour-neutral, but it touches session custody, so it goes to H2a under the routing rule.
    - surface=production (session custody).
    - Triage: Fix-now → task H2a. /fix decision: Pending.
  - **[LOW]** SIMP-013 (recorded): `pipe_client.py` imports `pipe_server.py`'s private Win32 helpers.
    - Executor recommendation: move them to a `win32_pipe.py` seam that both import. The threat model's Chrome-link section names the files, so it moves with them.
    - surface=production (pipe).
    - Triage: Fix-now → task H2a. /fix decision: Pending.
  - **[LOW]** SIMP-014 (recorded): test-only members in production.
    - `main_window._is_suspend_event` (kept: a test calls it);
    - `session_locked` / `SystemPauseWatch.locked`;
    - `ContextEvaluator.bound_tab`;
    - `SpokenPauseDetector.cutoff_seconds`;
    - `NewConsultationWatcher.raised`;
    - `ChromeBridge.conn_gen`;
    - `ERROR_HOTKEY_ALREADY_REGISTERED`;
    - the `pipe_lost` signal (no production connection).
    - Executor recommendation: keep the ones that are test seams on purpose (`conn_gen`, `bound_tab`) and remove the rest together with their tests. That is not behaviour-neutral for the suite, so it was not applied here.
    - surface=production (dead or test-only code).
    - Triage: Fix-now → task H2a. /fix decision: Pending.
  - **[LOW]** SIMP-015 (recorded): oversized modules.
    - `ui/models.py`, about 3.5k lines. Seam: a `ui/chrome_text.py` for the Chrome refusal, pause and notice tables, which SIMP-004/005 want anyway.
    - `ui/main_window.py`: native events, reminders and re-verification.
    - `ui/bridge.py`: the snapshot builders apart from the command handlers.
    - Executor recommendation: split only after SIMP-004/007 land. Each split is a move with no logic change.
    - surface=production (moves logic between modules).
    - Triage: Fix-now → task H2a. /fix decision: Pending.
  - **[LOW]** SIMP-016 (recorded): LOW-047's code follow-up. `prune_reminders` forgets only indexed sessions, so an unlinked or failed recording's `session_ref` stays until the process ends. It resolves to no command.
    - Executor recommendation: a controller API that lists the live session ids, so the registry prunes to them.
    - surface=production (bridge `session_ref` registry).
    - Triage: Fix-now → task H2a. /fix decision: Pending.
- Consciously left alone:
  - The `encounter.py` "Phase 4's write" docstrings, which already say the next plan.
  - `_is_suspend_event`'s separate existence, because a test calls it.
  - The TypeScript `"recording" || "paused"` checks in `connection.ts` / `page.ts`, where a two-value check reads more clearly than a shared set.
- Summary:
  - 16 findings: 0 CRIT, 0 HIGH, 2 MED, 14 LOW.
  - 3 applied: SIMP-001..003, all LOW.
  - 13 recorded for task H2a: SIMP-004..016.
  - SIMP-006 needs the practitioner's naming choice, but not before commit: nothing was changed.
- Fix-delta self-check: PASS. Re-read the four applied hunks:
  - `context.ts`: two members removed, nothing else.
  - `panel.ts`: the import line and one `el(...)` call.
  - `connection.ts:122`: one comment.
  - `main_window.py`: two docstrings.
  - No logic, string or custody change.
- ruff: "All checks passed!". mypy: 50 files, no issues. Extension `npm run typecheck` and `npm run lint`: clean. Pytest, vitest and the build are owed to the composer.
- Last reviewed: 2026-09-28

### Round 57 - 2026-09-28 - Hardening H3: `/security-review` over Phases 1–8 as one surface, seeded by H1's carry-forward list

- Round status: Closed for this leg. 22 findings: 0 CRIT, 0 HIGH, 0 MED, 21 LOW, plus 1 record-only item.
  - 8 applied: 7 code (with tests) and 1 docs-only.
  - 13 recorded for the new task H3a. Five of these also have their residue named in the threat model now.
  - 1 record-only item for the draft-write plan.
  - No must-pause: nothing needs the practitioner before commit.
- Source: Claude Code security-review (executor leg stage-9-exec-k3, claude-opus-5-5). The portable checklist ran as five read-only lens subagents:
  - A, the Chrome link;
  - B, the extension;
  - C, secrets, logs and test hygiene;
  - D, Cliniko calls;
  - E, lock, sleep, hotkey and enrolment.
- Every candidate was re-read by the executor before logging, against its surrounding guards.
- Composer routing (smoke in progress):
  - LOW/MED items with a small local fix are applied, with tests.
  - Anything needing a design choice, touching a practitioner decision (D1, D5, Task 4.3) or restructuring a production path is recorded.
- Scope / baseline:
  - Surface: `git diff f9887a7 -- . ':!.cursor'` plus untracked files.
  - Trust boundaries examined: Chrome ↔ host (native messaging), host ↔ app (the named pipe), the page ↔ worker ↔ panel messages, app → Cliniko (HTTPS), window messages → app, the logs, and the tests' reach into per-user state.
  - Seeded items: the Cliniko rate limit, enrolment under lock, the unlock query, sleep during Start, and write-back freshness.
  - No skips.
- Security findings:
  - **[LOW]** SEC-001 (applied): `native_host.py` `_classify_raw` ran `raw.get("type") in NONCE_REQUIRED` on any value.
    - Threat: a `type` that is a list or object (only our own extension can send one, so a buggy or compromised one) raised `TypeError` outside the loop's `ValidationError` catch. The host then died without the typed error the threat model promises.
    - Mitigation: a non-string `type` falls through to envelope validation, giving `malformed`.
    - Test: `test_native_host.py::test_loop_an_unhashable_type_is_a_typed_error_not_a_crash` (3 cases).
    - Pattern siblings: grep for `in NONCE_REQUIRED` / `in INBOUND_TYPES` / `in RELAYED_TYPES` over `desktop/src`. The pipe's checks run after `parse_pipe_envelope`, which has already typed the value, so there are no other sites.
    - Surface: none user-visible (a fault path).
    - Triage: Fix-now. /fix decision: Applied.
  - **[LOW]** SEC-002 (applied): `pipe_server.py` `_await_client`'s synchronous `ConnectNamedPipe` treated `ERROR_NO_DATA` (a client that connected and closed before the call) as a failure.
    - Consequence: `_serve` returned, the handle closed, the name was freed, and the app was never told. The overlapped path already served that case.
    - Mitigation: the synchronous `ERROR_NO_DATA` is served the same way (the read loop sees the client gone).
    - Test: `test_pipe_server.py::TestFaults::test_a_client_gone_before_the_connect_call_does_not_end_the_server`.
    - The remaining class — any OTHER end of the serve loop leaves the link down with no "unavailable" line — is SEC-017.
    - Surface: the Chrome link after a same-user connect-and-close (panel/badge).
    - Triage: Fix-now. /fix decision: Applied.
  - **[LOW]** SEC-003 (recorded; residue named): `page.ts` block buttons (:350–406) check `isTrusted` only.
    - Threat: a script in a Cliniko page (a Cliniko XSS) raises the block with `pushState` to another note on the bound tab, hides or covers it, and collects two real clicks on "Discard previous". The app then discards the paused recording irreversibly.
    - Severity: MED if a Cliniko XSS is in scope.
    - Executor recommendation: remove Discard from the page block and keep it in the side panel and on the desktop, which Cliniko cannot script. The block keeps Resume previous / Finish previous.
    - This changes D1's block layout, so it is the practitioner's call at H3a's `/review-plan`. Named now in threat-model extension residue (1).
    - surface=production (the page block's buttons).
    - Triage: Fix-now → task H3a. /fix decision: Pending.
  - **[LOW]** SEC-004 (applied): `extension/package.json` `"dev": "vite"`.
    - Threat: crxjs's serve mode writes into `dist/` (the folder loaded unpacked):
      - a web-accessible entry `resources: ["**/*"]` on `<all_urls>`;
      - a worker loader that imports its code from `http://localhost:<port>`.
    - The extension id is pinned by `key`, so the host accepts that build.
    - Mitigation: the script is removed. Nothing referenced it (grep: `npm run dev` only in bootstrap templates). The threat model says the web-accessible claims hold for `npm run build` only.
    - Surface: none (a developer script).
    - Triage: Fix-now. /fix decision: Applied.
  - **[LOW]** SEC-005 (applied, docs): the page script's element exists only while a frame or block is drawn, and `sliceFor` draws the frame on every allow-listed tab.
    - So any allow-listed Cliniko page, including another clinic's, can learn WHEN a recording is live or paused (not whose).
    - Mitigation: named in threat-model extension residue (2).
    - Drawing the frame only on the recording clinic's tabs would be a D1 design change and was not proposed.
    - surface=docs. Triage: Fix-now. /fix decision: Applied.
  - **[LOW]** SEC-006 (applied): a page restored from Chrome's back/forward cache kept its old frame or block.
    - `page.ts` said hello only at start, and `hub.ts:492` skips a slice equal to the last one sent to that tab. A recording could show no red frame, or a stale block (its buttons carry an old ref the app refuses).
    - Mitigation: a `pageshow` listener with `persisted` true says hello again, which clears the worker's sent-slice memory. The listener is removed on stop.
    - Tests: `page.dom.test.ts`, "a page restored from the back/forward cache says hello again" and "a stopped page script ignores a back/forward restore".
    - Surface: the page frame/block after Back/Forward (smoke re-check).
    - Triage: Fix-now. /fix decision: Applied.
  - **[LOW]** SEC-007 (recorded): `context.ts:33` `NOTE_PATH` matches the path as written.
    - `//patients/1/...` or `%31` forms, if Cliniko serves them (UNVERIFIED), classify as `other_cliniko`.
    - For the bound tab this fails safe (pause). For "another note is focused" it fails open.
    - Executor recommendation: first check on a real Cliniko whether such URLs render a note. Only then collapse repeated slashes and decode percent-encoded digits before `NOTE_PATH`, keeping the id check.
    - surface=production (extension URL parsing).
    - Triage: Fix-now → task H3a. /fix decision: Pending.
  - **[LOW]** SEC-008 (recorded; seed "a real rate limit", part 1): switching A → B → A while A's check runs throws A's answer away (`encounter.py` `accept`, seq mismatch) and `bridge._finish_task` runs the waiting A again. Fast switching never fills the 60 s reuse.
    - Executor recommendation:
      - store a current-connection, current-rev `Verified` answer in `_recent` even when its run moved on;
      - add `VerificationLedger.reuse(request)`;
      - `_finish_task` reuses before `_run`.
      - Test: A → B → A with a gated answer makes one note call.
    - It touches the ledger and bridge that H2a's SIMP-007 consolidates, so do it with or after that.
    - surface=production (bridge / ledger; no user-visible text).
    - Triage: Fix-now → task H3a. /fix decision: Pending.
  - **[LOW]** SEC-009 (recorded; seed part 2): a 429 is not honoured.
    - `encounter.py:426` maps `RateLimited` to offline and discards `.reset`, and every new report calls again at once. The rate is unbounded.
    - Cliniko's 200/min is reachable by a script in a Cliniko page (`pushState` loops; the extension reports every URL change) or by a same-user pipe client. A person switching tabs will not normally reach it.
    - Impact: verification drops to `unverified_offline` and the practitioner's API user is throttled. No exposure.
    - Executor recommendation:
      - `UnverifiedOffline.rate_limited`;
      - a fixed 60 s per-clinic cooldown in `ChromeBridge._dispatch`, which records an offline result without a call;
      - optionally a 1 s spacing between calls.
    - Both numbers need the practitioner's sign-off.
    - surface=production (bridge; the offline line shows during a cooldown).
    - Triage: Fix-now → task H3a. /fix decision: Pending.
  - **[LOW]** SEC-010 (applied): the log tripwire (`logging_setup.py` `_PAYLOAD_SIGNATURES`) had no marker for the Cliniko credential or the registry.
    - Mitigation: the quoted and unquoted forms of `Authorization` (plus the raw `Authorization:` header line), `api_key` and `contact_email` are added. A backstop only: no production log call carries them (lens C traced every `log_event`; the client, clinics, encounter and every `ui/` module have no logger).
    - Test: `test_logging_setup.py::test_tripwire_drops_the_cliniko_credential_and_registry_renderings`. The existing disjointness test pins that no `log_event` key collides.
    - Pattern siblings: `practitioner_id` / `subdomain` were considered and left out. They are ids and a host, not secrets, and `subdomain` risks colliding with ordinary text.
    - Surface: none.
    - Triage: Fix-now. /fix decision: Applied.
  - **[LOW]** SEC-011 (applied; correctness, fails closed): `encounter.py` `_check_note` read the booking for display only (D4), yet its 404 refused the whole note as "note not found".
    - Mitigation: `NotFound` on the booking read means no appointment time. Any other booking failure still refuses or goes offline as before.
    - Tests: `test_encounter.py::test_a_deleted_booking_shows_no_time_and_still_verifies` and `test_any_other_booking_failure_is_unchanged` (401, 503).
    - Surface: the side panel's Ready layout for a note whose booking was deleted (it now verifies, with no time).
    - Triage: Fix-now. /fix decision: Applied.
  - **[LOW]** SEC-012 (applied; test hygiene): two tests wrote into the practitioner's real per-user logs.
    - `test_integration_no_sockets.py` launcher leg: the host with the inherited `LOCALAPPDATA` wrote `scribe-host.log` lines, which the incident process treats as signals.
    - `test_status_and_app.py::test_main_refuses_second_instance`: `setup_logging` wrote `scribe-app.log`, and the offline switches were left on the pytest process.
    - Mitigation: the launcher gets `LOCALAPPDATA=<tmp_path>`. The second-instance test patches `setup_logging` / `apply_offline_env` / `assert_offline_env` as `test_hands_free.py` does.
    - The launcher leg's pipe-name race (an app started after its skip check) cannot be redirected, because the name comes from the SID. It is noted beside the skip.
    - Surface: none.
    - Triage: Fix-now. /fix decision: Applied.
  - **[LOW]** SEC-013 (recorded; docs corrected): `pipe_client.py` reads the server's user through `GetNamedPipeServerProcessId`, a pid recorded when the pipe was created, not a live reference.
    - Threat: another account in the same Windows session could create the pipe with the app's DACL, hand the handle on, exit, and wait for pid reuse.
    - The "session" check is the Windows (Terminal Services) session, not the logon session.
    - Applied now: the wording, "Windows session", in the threat model, flow 19, `pipe_client.py` / `pipe_server.py` docstrings, AGENTS.md and CHANGELOG. The residue is named.
    - Executor recommendation: also require the pipe's OWNER SID to equal the host's user. A non-admin cannot assign another user's SID as owner. This extends Task 4.3's (b) check set, so it is the practitioner's to confirm.
    - surface=production (host verification).
    - Triage: Fix-now → task H3a. /fix decision: Pending.
  - **[LOW]** SEC-014 (recorded; residue named; UNVERIFIED): the pipe's SDDL `D:P(A;;GA;;;<SID>)` has no mandatory label.
    - The default label blocks only writes from lower integrity, so a low-integrity (non-AppContainer) process of this user may open it read-only and receive `state`, patient name included, while holding the only slot.
    - Executor recommendation: test on the host first. Then use `S:(ML;;NWNRNX;;;ME)`, and have the host require a medium-or-higher, non-AppContainer server.
    - The SDDL is pinned by `test_pipe_server.py`, and this is Task 4.3's surface.
    - surface=production (pipe security).
    - Triage: Fix-now → task H3a. /fix decision: Pending.
  - **[LOW]** SEC-015 (recorded; residue named; pre-existing): the single-instance mutex `Global\ClinikoScribe-app-<username>` (`app.py:59-98`) can be created first by ANOTHER standard account, which stops the practitioner's app. A denial of service only.
    - Executor recommendation: put the SID in the name, use a user-only descriptor, and fail open when the existing mutex's owner is not this user.
    - surface=production (start-up).
    - Triage: Fix-now → task H3a. /fix decision: Pending.
  - **[LOW]** SEC-016 (recorded; docs qualified): `pipe_server.py:480-486, 552-559`. A writer thread that outlives the 5 s join under extreme load could write connection N's taken frame to client N+1. `:554` clears the shared frame even for a stale connection id.
    - Executor recommendation: clear the frame only when the id matches, and do not accept a new client while the old writer lives.
    - Concurrency in the pipe is custody-adjacent, so do it at H3a with a test, not during the smoke.
    - surface=production (pipe).
    - Triage: Fix-now → task H3a. /fix decision: Pending.
  - **[LOW]** SEC-017 (recorded; SEC-002's remainder): any other unexpected end of `PipeServer._serve` (a `GetOverlappedResult` failure, an exception) leaves the Chrome link down with no `set_unavailable` line on the Session screen.
    - Executor recommendation: a `PipeEvents` failure callback, on any exit but stop, that calls `bridge.set_unavailable()`.
    - surface=production (Session screen line).
    - Triage: Fix-now → task H3a. /fix decision: Pending.
  - **[record-only]** SEC-018 (the write-back freshness seed): confirmed there is NO write path today.
    - `cliniko_client` refuses every method but GET before a connection exists.
    - `writeback_context`, both `MainWindow` write-target entries and `ChromeBridge.live_reverification` are called only from tests.
    - New detail: `writeback_context` checks neither `verified_at` nor `conn_gen`. Added to Follow-Up Continuation Notes for the draft-write plan. Nothing to build here.
  - **[LOW]** SEC-019 (recorded; seed "stop a voice enrolment on lock"): `MainWindow._on_session_locked` and the suspend branch only `pause_for(...)`, which acts on a recording. An enrolment capture keeps capturing for up to 90 s behind a lock or across a sleep, and `_enrolment_blocker` does not refuse a Record press queued at the lock.
    - Executor recommendation:
      - call `practitioner_screen.on_stop()` (a no-op unless enrolling; the worker's checks save nothing) in both branches;
      - `_enrolment_blocker` refuses through `_lock_refusal()`;
      - tests in `test_system_pause.py`;
      - update the LOW-054 residue.
    - It extends D5 to the practitioner-profile surface, so it needs the practitioner's one-line acknowledgement at H3a.
    - surface=production (Practitioner tab: an enrolment stops on lock).
    - Triage: Fix-now → task H3a. /fix decision: Pending.
  - **[LOW]** SEC-020 (recorded; seed "check an unlock with Windows"): `nativeEvent` → `SystemPauseWatch.note_unlock()` clears the lock flag with no query.
    - Threat: a same-user process can post a forged `WTS_SESSION_UNLOCK`, then a forged `WM_HOTKEY`, and resume an UNLINKED recording behind a locked screen (the lock flag is its only guard).
    - Executor recommendation: `note_unlock` asks `registrar.query_locked()` (the same WTS call the 5 s re-check uses) and keeps the flag only on a positive LOCKED. None or an exception believes the message, so `lock_unknown` keeps its way out.
    - Tests: `TestLockFlag` / `TestLockWindow` fakes pass `locked_answer=False`, plus a forged-unlock test.
    - Deferred from this leg because it changes the lock path the practitioner is smoke-testing right now. Apply after P.2 confirms a real unlock's `SessionFlags`. The unlock still resumes nothing; D5 is unchanged.
    - surface=production (lock flag).
    - Triage: Fix-now → task H3a. /fix decision: Pending.
  - **[LOW]** SEC-021 (recorded; seed "sleep during Start", trigger UNCONFIRMED): a `PBT_APMSUSPEND` sent re-entrantly inside `controller.start` would meet IDLE or QUEUED and be lost. This can happen if the PortAudio stream open pumps messages on the GUI thread.
    - Only a sleep that does not lock first is exposed, because the lock is safe here (flag plus a queued pause).
    - Executor recommendation: an additive queued re-check. When a suspend meets a non-live state, a queued `_on_suspended` calls `pause_for(SUSPEND)` after Start returns. It is idempotent and fails safe.
    - Add a live-smoke step: sleep the machine while pressing Start.
    - surface=production (sleep pause).
    - Triage: Fix-now → task H3a. /fix decision: Pending.
  - **[LOW]** SEC-022 (recorded; PLAUSIBLE, found by lens E outside its brief, confirmed by reading): live-transcript posts carry no session tag.
    - `TranscriptScreen.post_live_window` emits a queued signal. The retired session's worker is stopped under `_post_lock` in `_retire_locked`, but a post it emitted BEFORE the stop is still in Qt's queue when the new Start's synchronous `session_started` → `begin_live_view()` runs.
    - That post is then drawn into the NEW session's live view: the previous patient's last words, until the final document replaces them. It is also fed to the spoken-pause and new-consultation detectors, which fails safe (a pause or a warning).
    - The final transcript is unaffected (built from the new session's own audio).
    - Executor recommendation: a per-Start live-view token captured by `_build_live_transcriber`'s `on_window` and checked in both `live_window` slots. It changes the signal's payload and about 13 test call sites, so it goes to H3a.
    - surface=production (the Transcript tab's live view).
    - Triage: Fix-now → task H3a. /fix decision: Pending.
- Checked and clean:
  - **AuthN/AuthZ:**
    - The host verifies before any frame crosses, and `SECURITY_IDENTIFICATION` applies.
    - The panel port needs its name, extension id, no tab and the exact panel URL.
    - Page messages need our id, the top frame and a Cliniko host.
    - Block actions are limited to three; Start needs the consent tick and a well-shaped target.
    - No `externally_connectable`.
  - **Injection:**
    - No HTML sinks, `eval` or string timers in extension production code.
    - Cliniko ids are checked three times before a path is built. Headers are protected by the key and email checks.
  - **Secrets:**
    - The key goes only to Credential Manager and the Basic header, never to a repr, exception, log, `state` or clipboard.
    - `probe-cliniko.py` prints shapes only.
  - **SSRF:** the connect host is `api.<shard>.cliniko.com` from the stored key's shard, and a Chrome-reported host only selects a registry record.
  - **Crypto/TLS:** `PROTOCOL_TLS_CLIENT`, hostname and certificate verification, TLS 1.2 or later, no keylog, no proxy or tunnel.
  - **Resource bounds:**
    - The 1 MB frame cap applies before allocation, with digit, depth and surrogate handling.
    - Response bodies are capped at 1 MiB, redirects are refused, and only a 200 is read.
    - The worker drops a stale answer by `(conn_gen, seq, target, clinic_rev)`.
  - **Dependencies:** exact-pinned devDependencies only, and no install scripts on Windows.
  - **Offline contract:** no Cliniko call at startup, idle or on a timer; reconnect re-verification happens only for a live linked session.
  - **Window messages:** none starts, discards, finishes or opens anything. Hotkey and spoken pause do only pause or the guarded resume.
  - **Test hygiene otherwise:** fakes for the hotkey, system events and clipboard; unique test pipe names; `MemoryKeyStore`; no registry writes.
- Summary:
  - Round 57: 22 findings, all LOW, plus 1 record-only item.
  - Applied (8): SEC-001, 002, 004, 006, 010, 011, 012 in code, and 005 in docs.
  - Recorded to H3a (13): SEC-003, 007, 008, 009, 013, 014, 015, 016, 017, 019, 020, 021 and 022. The residues of 003 and 013–016 are named in the threat model now.
  - Record-only for the write plan: SEC-018.
  - No security issue blocks the commit.
  - The project's own security tests are the desktop suite (tripwire, no-sockets, confinement pins) and `sinks.test.ts`. There is no network dependency audit (no network; the lockfile is unchanged).
- Verification counts:
  - 5 lenses (subagents), 24 candidates.
  - 1 merged: the pipe server's F2 split into SEC-002 (applied) and SEC-017 (recorded).
  - 1 moved to record-only: SEC-018.
  - 1 found outside a brief and confirmed by reading: SEC-022.
  - 0 dropped as false positives.
  - 1 downgraded: SEC-003 from "arguably MED" to LOW, because it needs a Cliniko XSS.
- Fix-delta self-check: PASS. Re-read every applied hunk:
  - `native_host.py`: only the `isinstance` guard added.
  - `pipe_server.py`: the synchronous branch now matches the overlapped one; docstrings.
  - `pipe_client.py`: docstring.
  - `encounter.py`: `NotFound` caught around `get_booking` only; `booking_id` is kept as the note's link.
  - `logging_setup.py`: 9 signatures appended.
  - `page.ts`: listener added in `start` and removed in `stop`; `lastHref` updated before the hello.
  - `package.json`: one script line.
  - Two tests: environment only.
  - No custody ordering, registration, protocol shape or practitioner decision changed.
- ruff: "All checks passed!" (after wrapping one test line and ordering one import). mypy: 50 files, no issues. Extension `npm run typecheck` and `npm run lint`: clean. Pytest, vitest and the build are owed to the composer.
- Last reviewed: 2026-09-28

### Round 58 - 2026-09-28 - Hardening H4 slice A: Cliniko client, clinic registry, offline contract and the security docs, independent cross-family codex peer review (pass stage-9.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Specified slice-A diff and current files, permitted plan sections, and targeted test-source checks; read-only verification, no tests or network commands.
- **PR-LOW-310** (LOW, docs-only, `docs/security/threat-model.md:333`): The clinician-asserted-content section incorrectly treats disabled copying as a current restriction, contradicting the enabled copy control documented elsewhere. — Evidence: “copy-to-Cliniko is Phase 4+ and currently ships disabled”; the same document at lines 385–387 says `COPY_TO_CLINIKO_ENABLED` “ships ENABLED since the practitioner's 2026-09-27 decision.” Recommendation: Fix-now — Describe ratified copying as available, while retaining the requirement for clinician finalisation in Cliniko. /fix decision: Applied (leg stage-9-exec-k5 — `threat-model.md` surface 2: a fully ratified note can be copied since D12, surface 4's flag + `_copy_ready`, the app writes nothing to Cliniko, record content only after finalisation in Cliniko; re-grep "ships disabled" in `docs/`: 0 hits)
- **PR-LOW-311** (LOW, docs-only, `docs/security/threat-model.md:362`): The review-edit section excludes free-text assertion editing even though the same threat model documents that implemented input path and its controls. — Evidence: “free-text editing of an assertion does not exist”; lines 865–873 instead state “The Edit control is BUILT” and explain that it types over a line or proposal, with refusal filters deciding what is learned rather than what the clinician may write. Recommendation: Fix-now — Replace the obsolete exclusion with a cross-reference to the typed-edit controls in surface 12. /fix decision: Applied (leg stage-9-exec-k5 — the clause now reads "typing over a line or a proposal is the Edit control of the note-learning section's surface 12 ("Typed edits"; its text admitted by `check_typed_text`; a typed line draws `clinician_asserted`)"; re-grep "free-text edit": 0 hits)
- **PR-LOW-312** (LOW, docs-only, `docs/security/data-flow-map.md:725`): The plaintext-config non-flow omits learned rules and therefore understates what the application writes outside encrypted session storage. — Evidence: “The one thing the app writes into that class itself is a learned phrase,” qualified as two to four words and name-filtered; `docs/security/threat-model.md:883–894` instead documents practitioner-typed learned wording with “NO name heuristic” and `append_learned_rules` replacing `autofill_rules.json` and writing its metadata sidecar. Recommendation: Fix-now — Include learned rules in the plaintext-config exceptions and state their distinct admission controls and retention. /fix decision: Applied (leg stage-9-exec-k5 — `data-flow-map.md` explicit non-flows: the app writes TWO things into that class, (1) the learned phrase as before and (2) the learned rule: its trigger through `refuse_learning_candidate`, its typed wording through `refuse_typed_wording` with no name check (D11), written only on Save into `autofill_rules.json` with its sidecar; retention points to the Learned rules row)
- Verification counts: 5 claims checked, 3 confirmed, 2 dropped as unverifiable
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-9-exec-k4)
- PR-LOW-310 — peer: LOW, docs-only.
  - Verified: materiality=docs-only severity=LOW surface=docs (`threat-model.md` surface 2, Phase 3A section) rec=Fix-now.
  - Evidence: `threat-model.md:333-334` reads "copy-to-Cliniko is Phase 4+ and currently ships disabled", while `:385-388` (surface 4) says `COPY_TO_CLINIKO_ENABLED` "ships ENABLED since the practitioner's 2026-09-27 decision". It is the only such site: a grep of `docs/` for "ships disabled" finds only `:333`.
  - Fix shape: say a ratified note can be copied (surface 4: flag plus `_copy_ready`), and keep "signed clinical-record content only after the clinician finalises the note in Cliniko".
  - Tests: none (docs). Verify with a re-grep: no "ships disabled" left.
- PR-LOW-311 — peer: LOW, docs-only.
  - Verified: materiality=docs-only severity=LOW surface=docs (`threat-model.md` surface 2 review edits) rec=Fix-now.
  - Evidence: `:361-362` reads "free-text editing of an assertion does not exist", but `:865-874` (surface 12) says "The Edit control is BUILT (Phase 2, `ui/note.py` `edit_line`): it types only OVER a line or proposal". The grep for "free-text edit" in `docs/` has one hit.
  - Fix shape: replace that clause with "typing over a line or proposal is the Edit control of surface 12 (admitted by `check_typed_text`; a typed line draws `clinician_asserted`)", keeping "edits freeze at Save".
  - Tests: none.
- PR-LOW-312 — peer: LOW, docs-only.
  - Verified: materiality=docs-only severity=LOW surface=docs (`data-flow-map.md` explicit non-flows) rec=Fix-now.
  - Evidence: `data-flow-map.md:725-731` says "The one thing the app writes into that class itself is a learned phrase". `threat-model.md:875-894` (surface 13) documents `append_learned_rules` replacing `autofill_rules.json` and writing `autofill_rules.learned.json`: practitioner-TYPED wording through `refuse_typed_wording`, with NO name heuristic.
  - Fix shape: name BOTH app-written plaintext-config items:
    - the learned phrase (flow 13 as now);
    - the learned rule (trigger from the practitioner's own utterance through `refuse_learning_candidate`; wording typed by the practitioner through `refuse_typed_wording` with no name check; written only on Save; its sidecar);
    - each reviewable and deletable on the Practitioner tab, pointing to its retention row.
  - Tests: none.
- Cap verdict: accept — docs-only — three confirmed claim-vs-doc drifts in the Phase 3A / note-learning text, no code path changes.
- LEG 2 (leg stage-9-exec-k5, `OWNERSHIP: auto-disposition` → Fix-now): all three Applied as the fix shapes above. Fix-delta: re-read the 2 threat-model hunks and the 1 data-flow-map hunk. No code changed.

### Round 59 - 2026-09-28 - Hardening H4 slice B: custody, encounter, the pipe, the native host and the pause rule, independent cross-family codex peer review (pass stage-9.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Permitted slice-B files and plan sections; source-only review against `f9887a7` → `47cbc5d5079226d3bd22b3511cb99d655a2515ba`. No writes, tests, npm, or network.
- **PR-LOW-320** (LOW, docs-only, `desktop/src/scribe_desktop/encounter.py:233`): Both encounter-read helpers incorrectly document checkout as the exclusive decryption path, omitting the authorised startup reminder reconstruction — Evidence: `encounter.py:233` says “on a CHECKOUT only”; `desktop/src/scribe_desktop/session_store.py:880` says “Called ONLY on a checkout”; `desktop/src/scribe_desktop/ui/models.py:997` documents reconstruction “at APP START”, and line 1017 executes `record = read(info.directory, crypto, info.session_id)`. Recommendation: Fix-now — Update both helper docstrings to include the once-per-session startup read permitted by Critical Constraint 7; preserve the prohibition on listing/sweep decryption. /fix decision: Applied (leg stage-9-exec-k5 — `encounter.read_encounter_record` and `session_store.read_encounter` now name all THREE authorised callers: the recovery checkout, `SessionController.adopt_queued` (the executor's LEG 1 sibling, `session.py:1136`) and `ui.models.reconstruct_reminder_entries`; "never the recovery listing, the sweep or a refresh" kept; `reconstruct_reminder_entries`' own "the ONE path besides a checkout" now also names the Unreviewed open-for-review read)
- SEC-022 assessment: Confirmed untagged producer interface: `desktop/src/scribe_desktop/ui/models.py:2940` accepts `on_window: Callable[[tuple[TranscriptSegment, ...]], None]`, passed unchanged at line 2965. Retirement stops the worker before destroying its in-memory key (`desktop/src/scribe_desktop/session.py:1548`), but does not invalidate previously queued UI posts. LOW is reasonable for the recorded transient display/pause effect; no severity increase is established. Saved transcript assembly uses the claimed worker and session header (`ui/models.py:2993`–2995). The complete Qt delivery interleaving cannot be independently confirmed without the excluded UI handlers.
- Verification limits: Full Start/Resume guard wiring and TypeScript/JSON-fixture parity require files outside this slice; neither is certified by this round.
- Verification counts: 4 candidate claims checked, 1 confirmed, 3 dropped as unverifiable.
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-9-exec-k4)
- PR-LOW-320 — peer: LOW, docs-only.
  - Verified: materiality=docs-only severity=LOW surface=docstrings (`encounter.py` `read_encounter_record`, `session_store.py` `read_encounter`) rec=Fix-now.
  - Evidence:
    - `encounter.py:233` says "on a CHECKOUT only".
    - `session_store.py:880` says "Called ONLY on a checkout ... never by the recovery listing or the sweep".
    - `ui/models.py:997-1017` `reconstruct_reminder_entries` decrypts at APP START and describes itself as "the ONE path besides a checkout".
  - Pattern siblings (grep for `read_encounter_record|read_encounter\(` over `desktop/src`) turn up a THIRD caller the peer did not list: `session.py:1136`, the Unreviewed "Open for review" adoption (`adopt_queued`; a stat-listed session decrypted on the practitioner's click). The full set is:
    - `ui/main_window.py:1109` (the recovery checkout);
    - `session.py:1136` (adoption);
    - `ui/models.py:1017` (the startup rebuild).
  - Fix shape: both docstrings name the three authorised callers and keep "never the recovery listing, the sweep or a refresh". `reconstruct_reminder_entries`' own "the ONE path besides a checkout" should also count adoption as a checkout-class read, or say "besides a checkout or an adoption".
  - Tests: none (docstrings). An optional caller pin in `test_encounter.py` would enumerate the three importers, the way `TestConfinement` does for the client.
- SEC-022 assessment — agree: LOW, it stays in H3a. The peer's own limit (the Qt delivery interleaving is outside its slice) matches round 57's "PLAUSIBLE, confirmed by reading": `begin_live_view` runs synchronously from `_on_session_started` (`ui/main_window.py:1030`), after the retired worker's pre-stop posts are already queued.
- Cap verdict: accept — docs-only — one docstring drift, a confirmed pattern of three callers, no behaviour change.
- LEG 2 (leg stage-9-exec-k5): PR-LOW-320 Applied as the fix shape. Three docstrings were changed (`encounter.py`, `session_store.py`, `ui/models.py`). No code changed; ruff and mypy are clean. The optional caller pin was not added (a record-only suggestion, not part of the finding). SEC-022 stays in H3a.

### Round 60 - 2026-09-28 - Hardening H4 slice C: the Chrome extension, the desktop UI wiring and hands-free, independent cross-family codex peer review (pass stage-9.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: The 18 permitted slice-C files and specified plan sections, against `f9887a7` → `47cbc5d5079226d3bd22b3511cb99d655a2515ba`; static reading only, no writes, tests or network; relay/pipe internals outside the permitted file list.
- **PR-MED-330** (MED, behavioral, `extension/src/panel.ts:155`): Live timer updates repeatedly remove the focused control, disrupting keyboard operation of Pause and Finish consultation during recording. Every changed snapshot rebuilds the entire panel without preserving focus. — Evidence: `panel.ts:72–76` compares `JSON.stringify(message.view)` and calls `this.render()` whenever it changes; `panel.ts:125` creates a new section and `:155` executes `this.mount.replaceChildren(section)`. `desktop/src/scribe_desktop/ui/bridge.py:992–993` includes the advancing `"recorded_seconds"` in snapshots published by `_tick` at `:1146`. Recommendation: Fix-now — Preserve control nodes during timer updates, or restore focus to the same action for the same session; add a focused-control regression check across successive live snapshots. /fix decision: Applied (leg stage-9-exec-k5 — `panel.ts`: a structure key without the timer and the `state_rev`s; a timer-only change updates the timer's `textContent` in place (the buttons stay the same nodes); any other change rebuilds and restores focus to the same `data-action` only when the session is the same; every button reads `session_ref` / `state_rev` from the model on screen when clicked; sibling on Ready — a tick records itself as drawn, so a newer view of the same note keeps the box and its focus; tests `panel.dom.test.ts` ×4: ticks keep node, focus and a straddling press (the click sends the newest rev), a same-session rebuild restores focus, a different-session rebuild does not, and the Ready sibling)
- **PR-LOW-331** (LOW, behavioral, `extension/src/panel-view.ts:200`): The blocked panel can identify an unfocused patient's name as the patient “On screen.” After a block and verified report for B, switching to a separate non-Cliniko tab leaves B's report bound, and the blocked layout continues displaying B without checking the current focus. — Evidence: `panel-view.ts:200–202` selects `report.patient_name` solely from verified status; `panel.ts:226` labels this value `"On screen"`. `desktop/src/scribe_desktop/ui/bridge.py:665–666` changes `_bound_tab` only when `report.focused` is true. The focus-match check at `panel-view.ts:249` occurs after the blocked layout has returned. Recommendation: Fix-now — Show the current patient's name only when the report matches the focused Cliniko tab; otherwise show neutral wording without claiming a patient is on screen. /fix decision: Applied (leg stage-9-exec-k5 — `panel-view.ts`: the Blocked `current` is the report's (name or "The patient on screen") only when `focus.kind === "cliniko"` and `report.tab_id === focus.tab_id`, else the new exported constant `NO_NOTE_IN_FRONT` = "No Cliniko note in front", drawn via `textContent`; tests `panel-view.test.ts` ×3 (another tab, no tab, a non-Cliniko tab: no patient name anywhere in the layout) + `panel.dom.test.ts` ×1)
- **PR-LOW-332** (LOW, docs-only, `docs/design-system.md:84`): The documented two-click Discard guarantee exceeds the implemented coverage: the Transcript screen still discards on its first click. — Evidence: The document says `"Discard takes two clicks, on every surface"` and, at `:89–90`, `"nothing is deleted on one click."` In `desktop/src/scribe_desktop/ui/transcript.py:257`, `self.discard_button.clicked.connect(self.on_discard)` directly reaches `:822`, `self._on_discard()`, with no confirmation step. Recommendation: Fix-now — Limit the documented guarantee to the Session screen, side panel and page block, and explicitly describe the Transcript screen's existing single-click behavior. /fix decision: Applied (leg stage-9-exec-k5 — DOC change only: `design-system.md` now reads "Discard of a live recording takes two clicks" for the Session screen, the block and the side panel, and names THREE one-click desktop Discards — the Transcript screen's and the Recovery tab's two lists (the Unreviewed one by Task 5.4's decision); re-grep "every surface" / "on one click" in docs: only the new wording)
- Verification counts: 3 claims checked, 3 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-9-exec-k4)
- PR-MED-330 — peer: MED, behavioral.
  - Verified: materiality=production-behavioral severity=MED surface=side panel Live layout (Pause, Resume, Finish consultation) while recording rec=Fix-now.
  - The render path:
    - `bridge.py:306` polls every `PUBLISH_INTERVAL_MS = 500` (`:151`).
    - `_live_state` (`:992-994`) carries `recorded_seconds`, a whole-chunk count that rises once a second while recording (`session.py:489-501`).
    - `publish` (`:1100-1118`) sends whenever the content differs, bumping `state_rev` too.
    - `panel.ts:70-76` re-renders on any change of `JSON.stringify(view)`.
    - `render` builds a new `<section>` and calls `mount.replaceChildren` (`:125`, `:155`). So about once a second every Live control is a NEW node.
  - Keyboard: focus on Pause or Finish is lost (it falls to `body`).
  - Mouse (asked): also affected. A click whose mousedown and mouseup straddle a replace is lost, because the pressed button is detached, so no `click` reaches its listener. That is roughly (click hold time ÷ 1 s) of Pause/Finish clicks while recording, e.g. about 10% for a 100 ms click.
  - The Blocked and Ready layouts do not tick: `recorded_seconds` is frozen while PAUSED or QUEUED, and neither shows a timer. Discard's armed state already survives by `armedRef`.
  - Fix shape (the smallest honest one):
    - `Panel.render` keeps a STRUCTURE key: the `PanelModel` JSON with `layout.timer`, `layout.state_rev` and `banner.state_rev` removed.
    - When the key and the layout kind are unchanged, update only the timer `<p data-part="timer">` `textContent` and store the new model. The buttons then stay the same nodes, keeping focus and a pressed mouse.
    - Otherwise do the full rebuild, then restore focus to the new element with the same `data-action` when the previously focused one had one and the `session_ref` is unchanged.
    - Handlers read `state_rev` / `session_ref` from the CURRENT model at click time, not a closure. Only `start` checks `state_rev` (`bridge.py:888`), and Ready does not tick, but a closure would carry a stale rev after an in-place update.
  - Regression tests (`panel.dom.test.ts`):
    - (1) Live rs=5 → focus Pause → deliver rs=6 → `document.activeElement` is the SAME Pause node (`toBe`), and the timer reads the new time.
    - (2) A click after the tick sends `pause` with the new `state_rev` and the same `session_ref`.
    - (3) A phase change (recording → paused) rebuilds, and focus moves to Resume only if focus was on Pause (by action; otherwise none).
    - (4) The Pause node captured before a tick is still `isConnected` after it (the mouse straddle).
- PR-LOW-331 — peer: LOW, behavioral.
  - Verified: materiality=production-behavioral severity=LOW surface=side panel Blocked layout ("On screen" line) rec=Fix-now.
  - Evidence:
    - `panel-view.ts:197-202` takes `current` from `state.report` whenever it is verified. `state.report` is the BOUND tab's (`bridge.py:937-941`).
    - `_bound_tab` moves only on a focused report (`:665-666`).
    - A tab never on an allow-listed host is never reported (`context.ts:241-242`). So when the practitioner switches from B's note to Gmail, or to another Chrome window's non-Cliniko tab, only B's `focused:false` report arrives, B stays bound, and the panel keeps "On screen: <B>".
    - The Ready path does check `report.tab_id === focus.tab_id` (`:249`); the blocked branch returns before it.
  - Wording only: B's name was already shown when B was in front, and the panel is extension UI, not a page, so there is no new exposure.
  - Fix shape: in the blocked branch, use `report.patient_name` only when `view.focus.kind === "cliniko" && report.tab_id === view.focus.tab_id`; otherwise a neutral line (proposed "No Cliniko note in front", a new display string).
  - Tests (`panel-view.test.ts`): a block plus a verified report on tab 7 gives the name when focus is on tab 7, and the neutral line when focus is on another tab or none. A `panel.dom.test.ts` case pins the rendered line.
- PR-LOW-332 — peer: LOW, docs-only.
  - Verified: materiality=docs-only severity=LOW surface=docs (`docs/design-system.md` Interaction posture) rec=Fix-now (DOC change, not code).
  - Evidence: `design-system.md:84-90` says "Discard takes two clicks, on every surface ... nothing is deleted on one click".
  - Pattern siblings (grep for `QPushButton("...(Discard|Delete)` in `ui/`) show THREE one-click Discards, not one:
    - `ui/transcript.py:255`, which reaches `on_discard` (`:818-828`); from `634eaf5`, Phase 2;
    - `ui/recovery.py:120`, the Recovery list, reaching `_discard` (`:419-433`); pre-existing;
    - `ui/recovery.py:138`, the Unreviewed list. This one is new in Phase 5, but Task 5.4 decision (a) deliberately reuses "the existing stat-only `discard_session(dir, None)`" (plan Task 5.4 brief, item 10).
  - The doc should change. Making any of the three two-click would be a behaviour change the practitioner has not asked for; it can be a design-system question at H2a/H3a if wanted.
  - Fix shape: "Chrome's Discard (page block, side panel) and the Session screen's take two clicks ...; the Transcript screen's Discard and the Recovery tab's Discard (both lists) act on one click on a stopped, selected session."
  - Tests: none.
- Cap verdict: raise +1 — production-behavioral — PR-MED-330 (panel re-render every second loses focus and straddled clicks) and PR-LOW-331 change `panel.ts` / `panel-view.ts` behaviour and need a confirmation round.
- LEG 2 (leg stage-9-exec-k5): all three Applied (see each `/fix decision`).
  - PR-MED-330 as the fix shape, with one change from LEG 1's test (3): a phase change does NOT move focus to a different action. Focus returns only to the SAME `data-action` in the SAME session, per the composer's brief.
  - One same-class sibling folded in: after the consent tick, a newer view of the same note redrew Ready under the practitioner's focus. The tick now records itself as drawn. Tested.
  - PR-LOW-331 adds the own-module constant `NO_NOTE_IN_FRONT`.
  - PR-LOW-332 is a doc change only.
  - Tests: extension +8 (`panel.dom.test.ts` +5, `panel-view.test.ts` +3).
  - Fix-delta self-check: PASS. Re-read the `panel.ts` render path, its three handler groups and the change listener, and the `panel-view.ts` blocked branch:
    - the in-place path returns only when the structure key is unchanged (layout without the timer and revisions, banner text and ref, queued, refusal, warnings, tick, arming);
    - Discard arming and the tick are in the key, so each still redraws;
    - no string reaches a sink but `textContent`.
  - The scoped confirmation is round 61.

### Round 61 - 2026-09-28 - Hardening H4 confirmation: the side-panel render and the docs fixes, independent cross-family codex peer review (pass stage-9.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Supplied fix diff `47cbc5d` → `8502c33`, permitted current-file context and rounds 58–60; static verification only, no writes, tests or network.
- **PR-LOW-340** (LOW, test-harness, `extension/src/panel.dom.test.ts:275`): The different-session focus test would also pass with PR-MED-330 entirely reverted, contrary to this round’s explicit test-honesty criterion. It remains useful as a negative guard against unconditional focus restoration. — Evidence: line 282 asserts `expect(document.activeElement).not.toBe(q('button[data-action="pause"]'))`; line 285 then calls `click("pause")` on the newly rendered button. The baseline `panel.ts:155` already executes `this.mount.replaceChildren(section)` without restoring focus, and its new button captures the new session reference and revision. Recommendation: Fix-now — Precede the different-session transition with a same-session rebuild and assert that Pause retains focus; then verify that changing sessions clears it. This makes the combined test fail when restoration is removed or applied across sessions. /fix decision: Applied (leg stage-9-exec-k6 — the test is rewritten IN PLACE as one sequence, "focus returns after a same-session rebuild but never across sessions": (1) Pause focused → a same-session non-timer change (a warning) → the rebuilt Pause is connected and IS `activeElement`; (2) → a different session → the new Pause is a new node and is NOT `activeElement` (body or the detached node); the click still sends the new session's ref and rev 23. Count unchanged)
- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-09-28

#### LEG 1 verified tuples (executor, leg stage-9-exec-k6)
- PR-LOW-340 — peer: LOW, test-harness.
  - Verified: materiality=test-harness severity=LOW surface=`extension/src/panel.dom.test.ts` (no production file) rec=Fix-now (composer-predisposed, `OWNERSHIP: auto-disposition`).
  - Evidence: before PR-MED-330, `panel.ts` rebuilt with `replaceChildren` and never restored focus, so a different-session case alone passes on the unfixed panel. It only guards against UNCONDITIONAL restoration.
  - Note: the separate same-session test ("a rebuild for the same session keeps focus on the same action") does fail on a revert, so the suite was not blind. This test on its own was, as the peer says.
- Fail-without-the-fix reasoning (vitest not run here; from `panel.ts` `render`):
  - (a) Restoration removed, or PR-MED-330 fully reverted: step 1's rebuild leaves `activeElement` on the detached node or the body, so `expect(document.activeElement).toBe(samePause)` FAILS.
  - (b) Restoration applied across sessions (the `sameSession` guard dropped): step 2 focuses the new Pause, so `expect(document.activeElement).not.toBe(newPause)` FAILS.
  - (c) With the fix, step 1's structure key changes (warnings), the session is the same (`REF`), and focus goes to the new `[data-action="pause"]`. Step 2's key changes (`session_ref`) and `sessionOf` differs, so there is no restore.
- Checks: extension `npm run typecheck` and `npm run lint` clean. Nothing but this test file and the plan changed (the practitioner's smoke is running on the current build).
- Cap verdict: accept — test-harness — one test made discriminating in place; no production change, and the pass converges at peer round 4 of 5.

### Round 62 - 2026-09-28 - Smoke finding S1: the Recovery list after a Start retires a recording

- Round status: Closed (0 pending) — 1 LOW, production, Fix-now, applied in this leg.
- Source: practitioner live smoke (P.2, clinic 1, finding S1); fixed by executor leg stage-9-exec-k7 (claude-opus-5-5).
- Scope: `ui/main_window.py` `_on_session_retired` and the tab widget; `ui/recovery.py` `refresh()` is read and unchanged.
- Findings:
  - **[LOW]** LOW-060: after a Start retires a recording (back-to-back: A's note saved, then B started from the side panel), the Recovery tab's Unreviewed list did not show A until the practitioner pressed Refresh. The reminder index and the banner were correct.
    - Evidence: `_on_session_retired` added the reminder entry but never re-listed. `RecoveryScreen.refresh()` ran only at construction, on the Refresh button and after its own actions, and nothing refreshed it when the tab was shown.
    - Thread check: no queuing is needed. `session_retired` is emitted synchronously by `SessionScreen._start` on the GUI thread, and the adopt path calls `_on_session_retired` directly from `_on_review_requested`, which also runs on the GUI thread.
    - Fix: `_on_session_retired` now calls `recovery_screen.refresh()`, which covers a Start, a failed Start that retired its predecessor, and the adopt path. On the adopt path the adopted session is already live, so it stays excluded. A new `_on_tab_changed`, connected to `tabs.currentChanged`, re-lists the Recovery tab when it becomes current.
    - Why this is safe: `refresh()` stays stat-only, using `list_recoverable_sessions` (key size and mtime, the audio header, file presence), so nothing is decrypted (Constraint 7). The custody exclusion is unchanged: `custody_protected_ids()` plus the screen's `_protected`.
    - Known effect: a re-list clears the list selection. The existing programmatic switches into Recovery (the review-open refusals and the close warning) only show a message, and none relies on a selection. A refusal raised from the Recovery tab itself does not change the tab, so it does not re-list.
    - Tests (`test_ui_pause_and_unreviewed.py` `TestReminderIndexWiring`, +3; they use stat-only stand-ins for the key and the transcript file):
      - a retired session is listed without a manual refresh;
      - a custody-protected session is still never listed when a retire re-lists;
      - opening the Recovery tab re-lists it.
    - surface=desktop Recovery tab. Triage: Fix-now; Decision: Applied.
- In-session review (`/review-loop`, one pass over this leg's diff, executor-read; folded here because it found nothing):
  - Ordering: on a Start, `controller.start` installs B before `session_retired` is emitted, so B is protected. On the adopt path, `adopt_queued` installs the adopted session before the call at `main_window.py` `_on_review_requested`.
  - Every existing programmatic `refresh()` caller already runs it without the Refresh button's busy gate, so a re-list during a resume run is not new. The running session stays in `_protected`.
  - A re-list can emit the 2-hour expiry cue, but only for sessions newly inside the window, as the Refresh button already does.
  - Result: none.
- Verification counts: 1 finding (practitioner-observed), 1 confirmed; review pass 0 candidates.
- Fix-delta self-check: PASS. Re-read the two `main_window.py` hunks and the three tests; no other production file changed.
- Checks: ruff clean; mypy clean (50 source files). Suite composer-run.
- Last reviewed: 2026-09-28

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
- [x] 🟩 4.1: **Protocol v2**
  - DONE 2026-09-27 (leg stage-4-exec-d9): protocol v2 in both mirrors against the fixtures (19 valid, 49 invalid), with `LIMITS` pinned in `meta.json`. Since the build:
    - the envelope's `protocol_version` is a strict integer, and TypeScript counts `request_id` / `session_nonce` in code points (round 25 LOW-021);
    - `read_frame` turns deep nesting and the int-digit limit into `malformed` (LOW-020, PR-MED-131);
    - PR-MED-130 (TypeScript `$`) was rejected as invalid.

    Suites 3555 + 105; rounds: in-session 25–26, codex stage-4.p1 27–31.
  - Files: `protocol/fixtures/` (meta 2/2, valid and invalid fixtures including bad ids, over-length values, a missing nonce, a `not_cliniko` report with a host (invalid), a `closed` report, and a session-bound command without `session_ref` (invalid), README); `protocol.py` (per-type payload models, `NONCE_REQUIRED` extended); `extension/src/protocol.ts`; both mirror tests.
  - Behaviour: D2. A refusal arrives in `state.last_refusal`.
  - Built (leg `stage-4-exec-d1`, 2026-09-27; awaiting the composer's suites):
    - `protocol/fixtures/meta.json` — protocol 2 / floor 2, and a `limits` object (seq and state_rev ≤ 2^53−1, tab/window ids ≤ 2^31−1, recorded seconds ≤ 1 000 000, banner count ≤ 99, request id 128, display 120, label 80, message 300, reason 48, timestamp 40, chord 40, allow-list 16, warnings 8, session_ref exactly 24), pinned to `LIMITS` by both mirror suites.
    - `protocol/fixtures/valid/` — the five Phase-1 fixtures bumped to v2; new `context__{note,login,not_cliniko,closed}`, `command__{start,pause,resume,finish,discard}`, `state__{live,app_not_running,refusal,block_and_banner}` (18). Placeholders only: host `example-clinic.au1.cliniko.com`, ids 1001/2002.
    - `protocol/fixtures/invalid/` — the old eleven bumped (`version_below_floor` stays 0) plus `version_1`, `hello__non_empty_payload`, `error__overlong_message`, 13 `context__*` (missing nonce, leading-zero / non-digit / over-long / numeric id, `not_cliniko` with a host, `closed` with ids, a note without ids, a URL key, a non-Cliniko host, a negative tab id, seq 0, an explicit null), 9 `command__*` (a session-bound command without `session_ref`, start without target / consent / with an unconfirmed consent / with a ref, discard unconfirmed, a ref of the wrong length, an unknown action, a target on pause) and 11 `state__*` (missing nonce, over-long name and allow-list and warnings, a control character in a name, `app_running:false` with a live session, a name on an unverified report, an unlinked live session with a patient, a bad timestamp, a non-boolean `app_running`, a refusal without a code) — 47.
    - `protocol/fixtures/README.md` — rewritten for v2: the `<type>__<variant>` layout, the per-type rules, the pipe rule and the named residue (TS cannot tell `1.0` from `1`).
    - `desktop/src/scribe_desktop/protocol.py` — v2; `context`/`command`/`state` in `MessageType`, `NONCE_REQUIRED` and `PIPE_TYPES`; `LIMITS` and the id / host / session-ref / reason / timestamp / text patterns; closed frozen payload models (`EmptyPayload`, `ErrorPayload`, `ContextPayload`, `CommandPayload` with `CommandConsent`/`CommandTarget`, `StatePayload` with `ReportState`/`LiveState`/`BlockState`/`BannerState`/`HotkeyState`/`RefusalState`) with explicit nulls refused and strict scalars; the envelope validates its payload per type; `parse_pipe_envelope` / `make_pipe_envelope` (no nonce, pipe types only); `typed_payload`.
    - `extension/src/protocol.ts` — the same rules and limits (code-point lengths, `/u` text pattern); a missing nonce is `bad_nonce`, a payload fault `malformed`.
    - `extension/src/connection.ts` — an `onState` callback: a nonce-matched `state` while connected is delivered (a refusal keeps the connection); any other `state` fails it.
    - `desktop/src/scribe_desktop/logging_setup.py` — `patient_name` and `note_id` tripwire signatures.
    - Tests: `desktop/tests/test_protocol.py` (rewritten, 93), `extension/src/protocol.test.ts` (rewritten, 82), `extension/src/connection.test.ts` (+3; literals use `PROTOCOL_VERSION`), `desktop/tests/test_native_host.py` (the below-floor case now over versions 0 and 1), `conftest.py` and `test_integration_no_sockets.py` literals.
- [x] 🟩 4.2: **Named-pipe server in `scribe-app`**
  - DONE 2026-09-27 (leg stage-4-exec-d9): `pipe_server.py`, a per-user pipe with `FILE_FLAG_FIRST_PIPE_INSTANCE`, one instance, remote clients rejected and a protected user-only DACL. It uses overlapped I/O with a stop event and a latest-wins writer per connection, and logs each client's executable path (`pipe_peer`). Since the build: `_OverlappedReader` takes extra stop events for the host's per-connection retire (PR-MED-140/141). Suites 3555 + 105; rounds 25–31.
  - Files: new `pipe_server.py`; `app.py` (lifecycle); `desktop/pyproject.toml` (mypy overrides for `win32event`/`win32gui`/`win32process`).
  - Behaviour:
    - `FILE_FLAG_FIRST_PIPE_INSTANCE` (literal `0x00080000`), `nMaxInstances=1`, `PIPE_REJECT_REMOTE_CLIENTS`, and a user-only DACL from SDDL.
    - Overlapped I/O plus a stop event, and a short-read-looping `ReadFile` adapter for `framing.read_frame`.
    - Messages are emitted only as queued Qt signals, and a new client connection is signalled as pipe loss and bumps D4's `conn_gen`.
  - Built (leg `stage-4-exec-d1`, 2026-09-27; awaiting the composer's suites):
    - `desktop/src/scribe_desktop/pipe_server.py` (new, Qt-free) — `pipe_name(sid)` → `\\.\pipe\ClinikoScribe-<SID>` and `pipe_sddl(sid)` → `D:P(A;;GA;;;<SID>)`, both refusing a malformed SID; `current_user_sid()`; `PipeServer(name, events, *, sddl, logger)` with `OPEN_MODE` = duplex | overlapped | `FILE_FLAG_FIRST_PIPE_INSTANCE` (0x00080000), `PIPE_MODE` = byte | wait | `PIPE_REJECT_REMOTE_CLIENTS`, `MAX_INSTANCES` = 1, a non-inheritable security attributes; `start()` creates the pipe synchronously and raises `PipeUnavailable("name_taken" | "create_failed")`; overlapped connect/read/write each waiting on the operation's event AND the stop event, each thread cancelling only its own I/O; `_OverlappedReader` is the short-read-looping `read(size)` adapter for `framing.read_frame`; inbound frames must be nonce-free `context`/`command` (`parse_pipe_envelope`) or the connection closes (`framing`, `malformed`, `unexpected_type`, `io_error`); `send(conn_id, envelope)` puts the frame in a per-connection latest-wins mailbox and drops it for any other connection; `stop(timeout)` is prompt in every state; logs `pipe_client` state/count and `pipe_server` state/error code only. The `PipeEvents` protocol (`connected` / `message` / `disconnected`) is what the bridge implements with queued signals (Task 4.5), so the conn_gen bump happens there.
    - `desktop/src/scribe_desktop/framing.py` — a `ByteReader` protocol so `read_frame` takes the adapter.
    - `desktop/src/scribe_desktop/app.py` — `_start_chrome_link` after the single-instance guard: `attach_chrome_link()`, `PipeServer.for_current_user(bridge)`, `bridge.attach(server)` BEFORE `start()`; on `PipeUnavailable` the bridge shows the link as unavailable; `aboutToQuit` → `stop`.
    - `desktop/pyproject.toml` — mypy overrides for `win32event`, `win32gui`, `win32process`.
    - Tests: `desktop/tests/test_pipe_server.py` (new, 26, real uniquely named pipes — never the real per-user name): the flags and the exact `CreateNamedPipe` arguments, the DACL's single user entry, a held name refused, one client at a time, short writes assembled, a new connection number per client, a frame for an old connection never reaching the next, each fault closing the connection and the server waiting for the next client, stop in every state.
- [x] 🟩 4.3: **Pipe peer identity** `[decision]`
  - **Decided (b) 2026-09-27 under the practitioner's overnight pre-authorisation to follow the executor's recommendation; revisable by the practitioner.** Composer record: `OWNERSHIP: gate-disposition key=task-4.3-decision`. The four residue items are stated AS RESIDUE in the threat model's Chrome-link section (pipe residue (1)(a)–(d)), with the squatter case as residue (2). Under (b), "verified" means the server runs in the host's logon session, its token user is the host's user SID, and the pipe's DACL is exactly the protected single-entry DACL the app creates (`pipe_client.unverified_reason`); anything else is the hard error. The optional log-only tripwire was built (leg `stage-4-exec-d2`): each end logs the other's executable path at connect (`pipe_peer`) — a path only, no gate, no new dependency, no new capability.
  - Default (b): session id plus the user-only DACL, with the residue documented as `app.py:76-77` does for the mutex. The residue list must name what a same-user process on the pipe can do:
    - forge a start with consent;
    - read names for chosen note ids through `state`;
    - hold the only pipe slot;
    - drive `resume_previous` (ids only; the extension builds the URL).
  - Upgrades: (a) the host verifies the server's parent chain up to `Scripts\scribe-app.exe`; (c) the server checks the client PID's image and parent.
  - Decide after: 4.2 works and the launcher/redirector chain is measured on this host.
  - Blocks: 4.4's connect contract. "Pipe exists but server unverified" is a hard error under every option.
  - **Decision brief (leg `stage-4-exec-d1`, 2026-09-27; 4.2 is built, its suite not yet run).**
    - *What is being decided.* Who the two ends of the pipe trust. Today the pipe's DACL admits every process running as the practitioner's Windows user, and nothing else (4.2). The question is whether to add a check of WHICH program is at the other end.
    - *Residue under the default (b)* — what any program running as the same Windows user can do once it is on the pipe while the slot is free (now written into the threat model's "Chrome link" section, pipe residue (1)):
      1. forge a `start` with the consent tick set — the app cannot see the side panel, so a forged tick is indistinguishable from a real one;
      2. read the patient's name for a note id of its choosing through `state` — it reports that note on an allow-listed host, and the bridge verifies it with Cliniko and publishes the name;
      3. hold the only pipe slot — the Chrome link is then down (the Session screen would read "Chrome: connected" while Chrome shows the app as not running);
      4. drive `resume_previous` once Phase 5 builds it — ids only; the extension builds the URL from the allow-list.
      Plus the squatter case (pipe residue (2)): a same-user program that creates the pipe name before the app. The app then says the Chrome link is unavailable; the host (4.4) must treat "pipe exists but server unverified" as a hard error under every option.
    - *Option (b), the default: session id + the user-only DACL.* The host checks that the pipe's server runs in its own logon session (`GetNamedPipeServerSessionId` against its own session), and the DACL keeps other users out. Cost: a few lines in 4.4 and the residue as documented; no new fragility. It adds nothing against a same-user program.
    - *Upgrade (a): the host verifies the server's parent chain up to `Scripts\scribe-app.exe`.* The host takes the server's PID (`GetNamedPipeServerProcessId`), walks its parents (a Toolhelp snapshot via ctypes — pywin32 does not expose the parent PID), and checks each hop's image path (`QueryFullProcessImageNameW`) up to the venv's `Scripts\scribe-app.exe`. Cost: one module plus fake-process-table tests in 4.4, and a hop list pinned from the measurement below. It fails CLOSED whenever the chain changes shape (a Python upgrade that changes the base interpreter's path, a venv rebuild, a Store/MSIX interpreter) — the Chrome link then stays down until the pin is updated. What it buys: the host no longer talks to a squatter that was not launched through `scribe-app.exe`. It is defeated by a same-user program that launches the real `scribe-app.exe` with a modified venv (boundary 2's code hijack), or that spoofs its parent (`PROC_THREAD_ATTRIBUTE_PARENT_PROCESS` is available to same-user code).
    - *Upgrade (c): the server checks the client PID's image and parent.* The mirror of (a) on the app side (`GetNamedPipeClientProcessId`, walk up to `%LOCALAPPDATA%\ClinikoScribe\scribe-host.exe`, optionally `chrome.exe` above it). Cost: the same as (a), on the app side, with the same fail-closed fragility. What it buys: a program that opens the pipe directly is refused. It is defeated in ONE step, because any same-user program can launch the installed `scribe-host.exe` itself with the extension's origin as its argument and speak the protocol on its stdio (the host's origin check is on argv, boundary 1). Requiring `chrome.exe` above it is defeated by parent spoofing.
    - *What reading the code establishes about the launcher chain.*
      - `scripts/register-native-host.py` copies the venv's `scribe-host.exe` to `%LOCALAPPDATA%\ClinikoScribe\scribe-host.exe` and points the manifest there. Its docstring records that the copy "still runs the repo's code — the launcher embeds the venv interpreter path": the installed `.exe` is pip's gui-script launcher, not the host itself.
      - `.venv\Scripts\scribe-app.exe` is the same kind of launcher for `scribe_desktop.app:main`.
      - So the process that owns the pipe is NOT `scribe-app.exe`: it is the Python interpreter the launcher starts. The process at the host's end is likewise not the installed `scribe-host.exe`.
      - Python's documented venv layout on Windows adds a second hop: `.venv\Scripts\python(w).exe` is a redirector that starts the base interpreter.
      - The expected chain is therefore `scribe-app.exe` → venv `pythonw.exe` → base `pythonw.exe` (the pipe server), and Chrome → `scribe-host.exe` → venv `pythonw.exe` → base `pythonw.exe` (the host). This is inferred from the code and the documented behaviour; it has NOT been measured on this machine.
    - *What only a practitioner-run measurement on this host can establish.* Agent shells here are MSIX-virtualised (`docs/lessons.md`), so an agent-run measurement would not show the real chain. What to measure:
      - the actual hop count and each hop's image path, with the app launched by double-click and the host launched by Chrome;
      - whether the base interpreter is a python.org install or a Store/WindowsApps one, which adds a hop and a `WindowsApps` path;
      - whether each launcher and redirector stays alive for the whole session, which a parent walk needs;
      - that the two `GetNamedPipe*ProcessId` calls return the base interpreter.
      How to measure: in a normal PowerShell window, with the app running and Chrome's badge green, run `Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'scribe|python' } | Select-Object ProcessId, ParentProcessId, Name, ExecutablePath`. Report only the process names, whether each ParentProcessId matches the row above, and whether each path is under `.venv`, under `%LOCALAPPDATA%\ClinikoScribe`, under a Python install folder or under `WindowsApps`. Never paste the paths themselves, because they contain the Windows user name. This measurement matters only if (a) or (c) is chosen.
    - *Weighing.* Every residue item needs code running as the practitioner's Windows user. Threat-model boundary 2 already accepts that attacker, and it already has more than the pipe gives it:
      - it can read the Cliniko API key from Credential Manager and call `/patients/<id>` directly, which is residue 2 without the pipe;
      - it can use the microphone itself, which is residue 1's effect without a consent tick;
      - it can repoint the host registration.
      (a) and (c) are each defeated by that same attacker (a modified venv, parent spoofing, or launching the real host), and they add a fail-closed dependency on the interpreter's install path.
    - Executor recommendation: (b) — every residue item requires same-user code, which boundary 2 already accepts with stronger capabilities (it can read the Cliniko key from Credential Manager and query the patient directly); (a) and (c) are defeated by that same attacker in one step (launching the real `scribe-host.exe`, parent spoofing or a venv edit) while adding a fail-closed break on every interpreter-path change. Optionally, as a cheap tripwire in the spirit of boundary 2's startup logging: the host logs the pipe server's image path at each connect and the app logs the client's (a path, never a frame), with no gate. The "pipe exists but server unverified" hard error in 4.4 stays, as the logon-session check.
- [x] 🟩 4.4: **Two-way native-host relay**
  - DONE 2026-09-27 (leg stage-4-exec-d9): `pipe_client.py` and the relay in `native_host.py`, on Task 4.3 (b). Before any frame, the host verifies the logon session, the user and the exact DACL; since PR-LOW-142 that means type, flags, mask and SID. It strips and stamps the nonce, says "not running" once per absence and re-waits, and exits on Chrome's EOF. Since the build:
    - only the relay thread closes its link, even when a shutdown times out (PR-MED-140, PR-LOW-160);
    - a failed write retires the connection, which takes no further write, and the message is never replayed (PR-MED-141, PR-MED-161).

    Suites 3555 + 105; rounds 25–31.
  - Files: `native_host.py`; `desktop/tests/test_native_host*.py`; the no-sockets host legs.
  - Behaviour:
    - Two threads with a stdout lock. The host answers hello/ping itself.
    - While the pipe is absent it pushes `state{app_running:false}` and keeps re-waiting (bounded `WaitNamedPipe` per attempt, no exit).
    - It stamps and strips the nonce per D2 and validates envelopes. Its logging never records a relayed payload.
    - It exits on Chrome-side EOF.
  - Verification: the existing handshake-with-no-app leg, plus a new app-pipe-open no-sockets leg.
  - Built (leg `stage-4-exec-d2`, 2026-09-27; on Task 4.3 (b); awaiting the composer's suites):
    - `desktop/src/scribe_desktop/pipe_client.py` (new) — `AppPipeConnector.connect()`: one `WaitNamedPipe` of at most `WAIT_MS` (1 s), then `CreateFile` with `OPEN_FLAGS` = overlapped | `SECURITY_SQOS_PRESENT` | `SECURITY_IDENTIFICATION`; absent, busy or any open failure → None (re-wait); `ERROR_ACCESS_DENIED` → `ServerUnverified("access_denied")`; then `read_server_identity` + `unverified_reason` (the (b) contract as one pure function: `session`, `user`, `dacl`) before any frame, else `ServerUnverified` with the handle closed. `PipeConnection`: `read_frame` over `pipe_server._OverlappedReader` (a stop or an I/O error ends it as `EndOfStream`), `write_frame` bounded at 5 s under a lock, `close`. The server's executable path is logged at connect (`pipe_peer`).
    - `desktop/src/scribe_desktop/pipe_server.py` — the shared peer lookups (`pipe_peer_pid`, `pipe_server_session_id`, `process_session_id`, `process_image_path`, `process_user_sid`; kernel32 via ctypes, as pywin32 exposes none of the pipe-peer calls); the server logs each client's executable path at connect (`_log_peer`); the docstring records the 4.3 decision.
    - `desktop/src/scribe_desktop/native_host.py` — `ChromeOut` (one lock over every stdout frame); `AppRelay` (starts after `hello_ack` with the session nonce; `forward` strips the nonce toward the app and drops while no app is connected; its thread verifies-and-connects, relays each valid nonce-free `state` stamped with the nonce, ends a connection on anything else, sends `state{app_running:false}` once per absence and re-waits every `RETRY_S`; `ServerUnverified` or an unexpected connector failure → a typed `internal` error and exit 1; a gone Chrome ends it); `HostSession.handle` returns None for a `context`/`command` carrying this session's nonce (else `bad_nonce`); `run_host(..., relay_factory=)` drains one queue fed by a stdin thread and the relay; `main()` uses `app_relay_factory()` (the per-user pipe). Logging: message types, relay states, the peer path — never a payload.
    - Tests: `desktop/tests/relay_fakes.py` (new: fake Chrome stdin/stdout, `FakeLink`, `FakeConnector`, `HostRun`); `desktop/tests/test_native_host_relay.py` (new, 24); `desktop/tests/test_pipe_client.py` (new, 22: the contract table on every platform; real uniquely named pipes — the app's own, absent, busy, three squatter DACLs, the identification flags, a stop during a read, both ends' path logs, the host relaying both ways and saying "not running" when the app stops); `test_integration_no_sockets.py` — the launcher leg now expects the stamped `state{app_running:false}` after the ack and skips BY NAME if a real `scribe-app` is listening on this user's pipe; a new leg runs a real host process against a real app process on a unique pipe (+1).
    - Docs: threat model Chrome-link section (the decision, what "verified" means, THE HOST'S RELAY with its residue, the four residue items as residue); data-flow flows 1 and 19; CHANGELOG.
- [x] 🟩 4.5: **App bridge, state publisher and the desktop linked-session display**
  - DONE 2026-09-27 (leg stage-4-exec-d9): `ui/bridge.py`, with queued signals only; D4 staleness via the ledger; `start`, `session_ref`, `pause` and the Phase 5 refusals in `state.last_refusal`; one snapshot published on change and every 500 ms; the Session screen's Chrome line. Since the build:
    - the live re-check has its own waiting slot and survives a bare disconnect (MED-018, LOW-022);
    - its result is dropped with its session (LOW-019) and is void under a moved `clinic_rev` (PR-MED-150);
    - the threat model states two name lifetimes (PR-LOW-151).

    `open_review` / `resume_previous` stay `not_available` until Phase 5. Suites 3555 + 105; rounds 25–31.
  - Files: new `ui/bridge.py`; `session.py` (a `recorded_seconds` accessor from chunk count, excluding pauses, plus the live-failure accessor for D7); `ui/models.py` (`SessionControllerLike`); `ui/main_window.py`; `ui/session_screen.py`.
  - Behaviour:
    - `command` goes to the SessionScreen slots (`start_linked` with the target and verification-outcome check, `on_pause`, `on_resume`, `on_finish`, `on_discard` with the confirm flag, `open_review`). Every command except `start` and `pause` is refused BEFORE its slot runs unless its `session_ref` matches (D2), so a stale Discard/Finish/Resume can never act on a newer session. A missing microphone becomes a named refusal.
    - One `publish()` builds the full `state` snapshot and sends it on change.
    - A `context` for a note triggers `verify_note_context` off the GUI thread, marshalled back, and applied only when its `(conn_gen, seq, target)` is still current (D4) and its `clinic_rev` is unchanged (D9); results from an earlier connection or an older key are dropped.
    - A linked live session re-verifies on pipe reconnect.
    - The Session screen shows the patient, clinic, verification line, block reason, hotkey and spoken-pause status, and warnings.
  - Built (leg `stage-4-exec-d1`, 2026-09-27; awaiting the composer's suites):
    - `desktop/src/scribe_desktop/ui/bridge.py` (new) — `ChromeBridge(QObject)` implements the pipe's `PipeEvents` by emitting queued signals only; on the GUI thread:
      - **Connections.** `connected`/`disconnected` call `VerificationLedger.new_connection()` (the D4 `conn_gen` bump), clear the per-tab reports, the bound tab, the seq, the last refusal and the last-sent snapshot, emit `pipe_lost`, and publish the full snapshot on connect. A linked live session (recording or paused) is re-verified with Cliniko on every new connection (`reverification_request(..., conn_gen=)`); the result is held per session (`live_reverification()`) and shown on the Session screen.
      - **Reports.** A `context` with a non-rising seq is ignored. The bound tab is the latest one reporting `focused`, and only its reports reach `ledger.report`. Only a note page on an allow-listed host becomes a `NoteTarget`. Verification runs on a `TaskThread` using the holder pattern, one at a time: a newer request waits, and a stale result is dropped by `ledger.accept`, or by identity for the live check.
      - **Commands.** `start` is refused, in this order, as `stale_state` (its `state_rev` is not the last sent), `target_mismatch` (a different tab, or ids that are not the bound report's), `no_report` / `checking` / `not_verified` (`ledger.start_context`), `session_active`, `review_open` (the controller's generation lease), `no_microphone`, or `failed`. Otherwise it runs `SessionScreen.start_linked(linked_consent(context), context)` and keeps the verified display for that session.
        - `resume`/`finish`/`discard` are refused as `session_changed` BEFORE any slot unless their `session_ref` equals `controller.session_ref`; then `busy`, then `not_allowed_now` from `controls_for_state`.
        - A linked `resume` also needs the bound report to be its own note (`report_mismatch`).
        - `pause` needs no ref.
        - `resume_previous` and `open_review` are refused as `not_available`: their behaviour is Phase 5's (Tasks 5.x resolution and Unreviewed).
      - **Snapshot.** `build_content()` makes one snapshot (allow-list, bound report with the name only when VERIFIED, live session, notice, last refusal; hotkey `available:false` and `spoken_pause:false` until Phase 7; `warnings` empty; no `block`/`banner` until Phase 5). `publish()` sends it when it differs from the last one sent on this connection. `state_rev` is bumped only on a send, and a snapshot that fails the protocol's own validation is never sent. A 500 ms tick republishes and drops the live display name when its session ends. `view()` feeds the Session screen.
    - `desktop/src/scribe_desktop/session.py` — `recorded_seconds` (the open store's `next_index`, or the closing count after Finish or a failure, × the 1 s chunk, so pauses add nothing), `live_failure` (the attached worker's `failed_reason`), `live_transcription_attached`; `_LiveSession.closed_chunks`.
    - `desktop/src/scribe_desktop/encounter.py` — `reverification_request(..., conn_gen=0)`: the bridge passes the connection it re-checks for; a checkout keeps 0.
    - `desktop/src/scribe_desktop/ui/models.py` — the Chrome copy (`CHROME_*` lines, `CHROME_RECHECK_LINES`, `CHROME_REFUSALS` covering every `StartRefusal`), `chrome_refusal_message`, `ChromeView` + `chrome_view_text`; `SessionControllerLike` gains `session_ref`, `recorded_seconds`, `live_failure`, `generating`.
    - `desktop/src/scribe_desktop/ui/session_screen.py` — `chrome_label` (plain text, hidden until the bridge sets it), `set_chrome_view`, `has_input_device`; `start_linked` and the four control slots return whether they acted (a button ignores it).
    - `desktop/src/scribe_desktop/ui/main_window.py` — `attach_chrome_link()` builds the bridge (only `app.py` calls it, so a test's `MainWindow` creates no pipe) and connects `clinics_changed` → `on_clinics_changed`; the close guard waits for a running bridge verification.
    - Deferred within the task's display line, by phase: the block reason (Phase 5 builds the block), the hotkey and spoken-pause controls (Phase 7; shown as "not set up"), warnings (none is produced yet). D7's "Spoken pause unavailable for this recording" line IS shown from `live_failure`.
    - Tests: `desktop/tests/test_ui_bridge.py` (new, 41: a fake sender, `encounter_fakes` transport and registry, the real `SessionScreen` over a `FakeController` subclass), `TestRecordedSeconds` (+3) in `test_session_machine.py`, the live-failure accessors in `test_live_session.py`, three Session-screen tests and the controller fields in `test_ui_screens.py`, `TestChromeView` (+8) in `test_ui_models.py`, and the no-sockets leg with the pipe listening and a client connected in `test_integration_no_sockets.py` (+1).
    - Docs: threat model "The Chrome link" section (protocol v2, the pipe, the bridge, each with its residue) and its scope and review-trigger lines; data-flow flow 1, new flow 19, flow 18's second trigger, the components table; CHANGELOG.

### Phase 5 — Pause rule, resolution, back-to-back and Unreviewed `[executor: premium-only]`
- [x] 🟩 5.1: **ContextEvaluator and `pause_for`**
  - DONE 2026-09-28 (leg stage-5-exec-e7):
    - `context_rules.py`: D5's `pause_action` table and `ContextEvaluator` (bound-tab and focused-tab reasons; re-bind by exact ids only).
    - The bridge's `pause_for`, pipe loss and new client, and `resume_refusal` run before every Resume.
    - Sleep via `nativeEvent`, which returns `(False, 0)` and never raises into Qt (the e2 production fix).
    - Unlinked recordings pause only on sleep.

    Suites 3922 + 105; rounds 32 (in-session) and 33–35 (codex stage-5.p1). Live-user smoke deferred to the morning.
  - **SMOKE FINDING and FIX (2026-09-28, leg stage-8-exec-h5):** morning-smoke step 5 found that sleep did NOT pause on the practitioner's Modern Standby machine. The classic `PBT_APMSUSPEND` broadcast never reached the window, and this task's real-dispatch test had sent that broadcast itself.
    - Fixed under D5's AS-BUILT addendum (the practitioner's "sleep + screen lock" decision): the new `system_events.py`, a `LOCKED` reason in `SYSTEM_REASONS` beside `SUSPEND`, `MainWindow.attach_system_pause` / `detach_system_pause`, and the `app.py` wiring.
    - Reviewed in rounds 49+. The suites and the live re-smoke are pending.
  - Files: new `context_rules.py`; `ui/bridge.py`; `ui/main_window.py` (`PBT_APMSUSPEND` via `nativeEvent`).
  - Behaviour: D5 exactly, including `pause_for` per session state, sleep, a new-client pipe loss, resume refused without a current matching report, and re-binding by ids. Parameterised-tested against the D5 table.
  - Built (leg `stage-5-exec-e1`, 2026-09-27; awaiting the composer's suites):
    - `desktop/src/scribe_desktop/context_rules.py` (new, Qt-free):
      - `PauseReason` and `CONTEXT_REASONS` (every reason except `hotkey` and `spoken`).
      - `LINKED_ONLY_REASONS` (the context reasons minus `suspend`).
      - `pause_action(state, reason, *, linked)`, D5's table: RECORDING → pause, plus a block for a context reason on a linked session; PAUSED → block only; every other state → nothing. A Chrome reason does nothing to an unlinked recording.
      - `is_suspend_message`, `names_note`.
      - `ContextEvaluator`, which holds the linked live session's tab binding (`bind` / `lose_tab` / `forget` / `evaluate`). For the BOUND tab, `closed` → `tab_closed`, a page other than a note → `left_note`, and another note or patient → `note_changed`. For the FOCUSED tab, another note → `other_note` and a login page → `login`. It re-binds only to a report naming the session's exact host, patient and note, and only while unbound.
    - `ui/bridge.py`:
      - `pause_for(reason)` pauses through `SessionScreen.on_pause`, sets `_Block` only when the session is then PAUSED, and emits `pause_cue` when it paused or newly blocked.
      - Every report goes to `_apply_rule` before the ledger. Pipe loss and a new client call `pause_for`, and `_reset_connection` calls `lose_tab`.
      - `resume_refusal()` returns `pipe_down` / `report_mismatch` / None and is installed as the Session screen's resume guard. `_on_resumed` clears the block and binds the session to the focused tab.
      - A linked Start binds the session to `target.tab_id`.
    - `ui/main_window.py`:
      - `nativeEvent` → `_is_suspend_event` (a 3-field `_MSG` head) → `pause_for(PauseReason.SUSPEND)`.
      - `pause_for` delegates to the bridge when attached. Otherwise it applies the same table through the Session screen's slot.
      - `_show_pause_cue` shows the status line, the Session screen's message and `QApplication.alert`.
    - `ui/session_screen.py`: `set_resume_guard`, which every `on_resume` consults first (a named refusal, and no controller call); `session_resumed`; `show_notice`.
    - `ui/models.py`: `PAUSE_CUES` and `pause_cue_text`, `CHROME_REFUSALS["pipe_down"]`, `BLOCK_DESKTOP_LINE`, and `ChromeView.phase` / `blocked`.
    - Scoping reading, recorded here: D5's report and pipe reasons concern a recording bound to a note, so an UNLINKED (desktop) recording ignores them; suspend pauses every recording. The block needs the session's own clinic (`BlockState` requires it), so only a linked session gets one.
    - Tests: `desktop/tests/test_context_rules.py` (new: the D5 table over every state × reason × linked, the evaluator over every report shape including the positive controls, re-binding, the suspend message); in `test_ui_bridge.py`, `TestPauseRule`; in `desktop/tests/test_ui_pause_and_unreviewed.py` (new), `TestResumeGuard` and `TestSuspendAndCue`.
    - Docs: the threat model's new "THE PAUSE RULE AND THE BLOCK" paragraph with residue (1)–(4); THE BRIDGE's command sentence; pipe residue (1)(d); data-flow flow 19; the bridge module docstring; CHANGELOG.
- [x] 🟩 5.2: **Resolution block**
  - DONE 2026-09-28 (leg stage-5-exec-e7):
    - `state.block` carries the reason, the live ref and the recording's own clinic, plus its own patient only when verified.
    - `resume_previous` resumes only on a matching report within 30 s on the same connection.
    - The Session screen's two-click Discard now drops "Confirm discard" when its window lapses or the session changes (round 32 LOW-026).

    Suites 3922 + 105; rounds 32–35.
  - Files: `context_rules.py`, `ui/bridge.py`, `ui/session_screen.py`.
  - Behaviour: Flow 3, with a two-step Discard. `resume_previous` asks the extension to navigate by ids and resumes only on a matching report. The desktop Resume and the hotkey honour the block.
  - Built (leg `stage-5-exec-e1`, 2026-09-27; awaiting the composer's suites):
    - `ui/bridge.py`:
      - `_block_state()` publishes `state.block`: the reason, the live `session_ref`, the recording's OWN clinic host and label, and its patient's name under the live-display rule. It is published only while that linked session is PAUSED, and `_tick` drops it once resolved.
      - `resume_previous` goes through the existing `session_ref` gate, then `_resume_previous`, which needs a PAUSED linked session and otherwise refuses `not_allowed_now`. It sets `_PendingResume`, and `_resume_if_pending` (run after every report) resumes through `on_resume` only when `resume_refusal()` passes, within `RESUME_PREVIOUS_WINDOW_SECONDS` (30). A new connection or the session ending clears the pending resume; a context pause does not.
      - `open_review` stays `not_available` until Task 5.5.
      - The navigation itself is the extension's: it builds the URL from `state.live`'s ids and the allow-list (Task 6.2 already carries this). No protocol change.
    - `ui/session_screen.py`: the Discard BUTTON is two-step (`on_discard_clicked`). The first click arms it for the current `session_ref` and shows `DISCARD_CONFIRM_MESSAGE` with the button reading "Confirm discard". The second click, within `DISCARD_CONFIRM_SECONDS` (10) for the same ref, calls `on_discard`. A disabled Discard disarms. `on_discard` itself stays the confirmed action, used by the bridge after Chrome's own second click, which the protocol requires as `confirmed: true`.
    - The desktop Resume and the hotkey honour the block through the one resume guard.
    - Tests: `TestResolution` (bridge); `TestTwoStepDiscard`.
- [x] 🟩 5.3: **Back-to-back flow**
  - DONE 2026-09-28 (leg stage-5-exec-e7):
    - Start is offered at QUEUED unless a review holds the lease (desktop tooltip; `review_open` from Chrome).
    - `session_retired` feeds the in-memory reminder index (linked and queued only).
    - "Finishing…" shows the processing tail.
    - Start clears the previous patient's post-Save Note tab.

    Suites 3922 + 105; rounds 32–35.
  - Files: `ui/bridge.py`, `ui/session_screen.py`, `ui/main_window.py` (`_on_session_started`).
  - Behaviour: D6: "Finishing <A>…"; Start at QUEUED unless the lease is held ("Save or cancel <A>'s note review to start"); retirement fills the reminder index (a list per note, D6) from the in-memory context.
  - Measure A's tail (timing only) in the Done note.
  - Built (leg `stage-5-exec-e1`, 2026-09-27; awaiting the composer's suites):
    - `ui/models.py`: `_CONTROLS[QUEUED] = ControlSet(start=True)`, `REVIEW_OPEN_START_HINT`, and the `_live_line` phases ("Finishing <A> - <clinic>...", "Ready for review: ...").
    - `ui/session_screen.py`:
      - Start and the consent tick are disabled while `controller.generating`, with the hint as a tooltip; `_watch_state` re-renders when the lease changes.
      - `_start` reads the tracked session BEFORE `start()` and emits `session_retired(previous)` when a non-terminal session was retired.
    - `ui/bridge.py`: `notice: review_open` while the lease is held. The existing `review_open` refusal now applies at QUEUED.
    - `context_rules.py`:
      - `ReminderIndex`: (clinic_id, note_id) → [session_id, …], newest first. `add` moves an entry rather than duplicating it, and `remove` takes out exactly one entry.
      - `reminder_entry(session)`: only a linked QUEUED session.
    - `ui/main_window.py`:
      - `self.reminders`; `_on_session_retired`.
      - `forget_unreviewed` (the index entry and `controller.forget_session_ref`), wired to the Recovery list's Discard (new `RecoveryScreen.session_removed`) and to `_on_transcript_closed` for a recovered source's `completed` / `discarded`.
      - `prune_reminders` (a stat of `key.dpapi` only), called after each periodic sweep in `app.py`.
    - `SessionControllerLike.forget_session_ref`.
    - Found while building, and applied as part of D6 (it is D6's own precondition): `_on_session_started` now also clears the Note tab. Starting B at QUEUED leaves A's post-Save Note tab live. Its "delete note and complete" calls `complete_deleting_saved_note()` on whichever session the controller tracks, so once B queued — before `_on_live_transcript` clears the tab — a click would complete B, deleting B's note. Start is refused while a pre-Save review holds the lease, so no unsaved review is ever dropped. A reopens from the Unreviewed section (Task 5.4).
    - A's tail: timing is live-only. The measurement is P.2's (the Validation list already names "the measured tail of 5.3").
    - Tests: `TestBackToBack` (bridge); `TestStartAtQueued` and `TestReminderIndexWiring`; `TestReminderEntry` / `TestReminderIndex`; `test_ui_models.py`'s QUEUED control pin updated, plus the phase lines and the cue coverage.
- [x] 🟩 5.4: **Unreviewed review reopen** `[decision]`, then build
  - DONE 2026-09-28 (leg stage-5-exec-e7): DECIDED (a) under the practitioner's overnight pre-authorisation — revisable at the morning smoke.
    - `SessionController.adopt_queued` reinstalls a retired session as the live queued one. It decrypts `encounter.enc` once, reads the transcript and any saved note (verified) before installing, and refuses by name.
    - The Recovery tab's Unreviewed section offers "Open for review" and Discard, never "Resume processing".
    - A saved note reopens read-only, with Copy and "Regenerate (replaces the saved note)" (the D6 reading, to confirm).
    - A crash-recovered store keeps its unfinished-store warning (codex round 34 PR-MED-190).
    - There is a 2-hour expiry warning and the on-close list.

    Suites 3922 + 105; rounds 32–35.
  - Options:
    - (a) a new controller `adopt_queued(directory)` that unwraps the key and reinstalls the session as the live QUEUED session, refused while any session is active. This is a NEW custody consumer, so enumerate every consumer (lessons 2026-08-12).
    - (b) extend the generation lease and `with_generation_custody` to recovered checkouts.
  - Decide after: 5.3 lands.
  - **Decision brief** (leg `stage-5-exec-e2`, 2026-09-28T00:10+10:00; 5.3 built):
    - The problem: a retired session's transcript and saved note are on disk under its DPAPI key, but the only generation-capable path is the controller's live QUEUED session (`with_generation_custody` → `_require_state(QUEUED)`); the recovered checkout shows Complete/Discard only (`can_generate=False`), and its "Resume processing" re-transcribes, unlinking `note.enc`.
    - (a) `SessionController.adopt_queued(directory, reader)` reinstalls the retired session as THE live QUEUED session. Cost: one new controller method (a new custody consumer, enumerated below). Everything downstream is the path that exists and is already hardened — the lease, `with_generation_custody`, `write_note`, `complete` / `complete_without_note` / `complete_deleting_saved_note` / `discard`, the D2 ref, `custody_protected_ids`, the Chrome `live` state. Limit: single-active-session holds, so adopting retires whatever queued/failed session is live, exactly as Start does, and it is refused while anything is recording, paused or processing.
    - (b) Extend the lease and `with_generation_custody` to recovered checkouts. Cost: a second, parallel custody path — a lease that covers a NON-live session, recovered twins of the save / abandon / post-save delete (`complete_without_note`, `complete_deleting_saved_note` have no recovered form), `destroy_recovered_crypto` interplay with a held lease, the Transcript screen's committed-note state on a recovered source, and a second generation-custody consumer for the sweep to protect through `RecoveryScreen._protected` rather than the controller. Every Phase-6.3 race class would need re-proving for the new path.
    - Custody consumers of (a), each checked against the adopted session (lessons 2026-08-12):
      1. `start()` / `_retire_locked`: a later Start retires the adopted session like any queued one (refused while the lease is held; the in-memory key copy destroyed; `key.dpapi` stays). `adopt_queued` itself retires a live queued/failed session the same way, under the same generation and uncleared-live refusals.
      2. `complete()`, `complete_without_note(lease)`, `complete_deleting_saved_note()`: act on `_live` at QUEUED — the adopted session — through `complete_session` (verifies `note.enc` against the on-disk transcript first).
      3. `discard()`: key-first on the snapshot; the reservation consumers are unchanged.
      4. `transcribe()`, `mark_queued()`, `claim_live_transcriber()`: need PROCESSING or an attached live worker; the adopted session has neither (`store`/`worker`/`live_transcriber` None, `transcribing` False).
      5. `begin_generation` / `end_generation` / `with_generation_custody`: serve the adopted session unchanged (QUEUED + lease identity). `adopt_queued` refuses while the lease is held — adoption would retire the session a generation depends on.
      6. `_custody_reservations`: `adopt_queued` refuses a target an in-flight Discard reserved (by id) and while any reservation is held (coarse, like `begin_generation`).
      7. `custody_protected_ids()` / the sweep / the recovery listing: the adopted session is the live non-terminal session, so the sweep skips it and the listing excludes it (no second custody path through the Recovery list); retired again, it is listed again.
      8. `active_session_ids()`: QUEUED is not active — unchanged.
      9. The recovered coordinator ops (`complete_recovered`, `discard_recovered`, `destroy_recovered_crypto`): reachable only from a recovered checkout; `adopt_queued` refuses while the Recovery screen holds one (`_protected` non-empty, checked by the caller) and the listing never offers the live adopted id.
      10. `RecoveryScreen` (`_protected`, `release_checkout`, list Discard): the Unreviewed list's Discard is the existing stat-only `discard_session(dir, None)` behind the click-time `_selection_blocked` re-check, which sees the adopted id as protected.
      11. The D2 registry: the adopted session keeps the reference it already had (kept through retirement), else one is minted; Complete/Discard forget it as today.
      12. `begin_enrolment` / `_on_capture_failure`: QUEUED is not active; no capture worker exists.
      13. `MainWindow`: `_recovered_crypto` and `_checkout` — adoption is refused while a recovered checkout is open; the adopted session's link line and D4 re-verification reuse the checkout machinery from the record `adopt_queued` already decrypted (no second decrypt; Constraint 7), and `recovered_writeback_target` returns None for it (the live entry, `live_writeback_target`, governs a live session).
      14. The Chrome bridge: publishes the adopted session as `live` at `queued` under its reference; `_tick` drops a stale display and block as for any queued session.
      15. The reminder index: the adopted session's entry is removed on adoption and re-added when a Start retires it again.
    - Executor recommendation: (a) — every consumer above already handles a live QUEUED session, so the new surface is one method whose refusals mirror `start()`'s; (b) duplicates the whole leased save/complete path for a second session kind, which is where rounds 27–36 found their custody races.
    - **Decided (a) 2026-09-28T00:10+10:00 under the practitioner's overnight pre-authorisation (2026-09-27) to follow the executor's recommendation; revisable by the practitioner** (`OWNERSHIP: gate-disposition key=task-5.4-decision choice=a-adopt-queued`).
  - Then build, in `ui/recovery.py` (the Unreviewed section), `ui/models.py`, `ui/main_window.py` and `session.py`:
    - rows with a transcript offer "Open for review", never "Resume processing";
    - with no `note.enc`, review opens from `transcript.enc` with generate, save and copy available; with a `note.enc`, it opens the saved note through `session_store.read_note` with its edits, copy available and generation only as an explicit "Regenerate (replaces the saved note)"; a note that fails verification is a named refusal on the row, never a silent regenerate (D6);
    - the checkout is released when the review ends (fixing today's hold-until-restart at `main_window.py:348-354`);
    - the expiry warning (2 h, the sweep's timestamp helpers) and the on-close expiry list.
  - Built (leg `stage-5-exec-e2`, 2026-09-28; awaiting the composer's suites):
    - `session.py`: `adopt_queued(directory, reader) -> (session, value)` and `ReviewOpenRefused(reason)`. The refusals and their order: the lease; any reservation; an active session; outside the root or not a session id; already live; no `transcript.enc` (`no_transcript`); the unwrap (`key_unavailable`); `encounter.enc` (`consent_unavailable`); the reader (`unreadable`, cause chained); then retirement of a live queued or failed session. The key is destroyed in memory on every refusal after the unwrap. The existing reference is reused, else one is minted. The class docstring's custody list names it.
    - `session_store.py`: `session_expires_at(dir, now)` = `_session_created_at` + the window (THE sweep's derivation).
    - `ui/models.py`:
      - `RecoverableSessionInfo.expires_at`, filled from `session_expires_at`.
      - `ReviewOpening` / `ReviewReadError` / `read_for_review` (the transcript, then `read_note` when `note.enc` exists).
      - `review_refusal_line`, `saved_note_line` (current config digest vs the note's), `unreviewed_row_text`, `expiry_text`, `expiring_soon`, `expiry_warning_line`, `close_expiry_message`.
      - The copy constants, and `SessionControllerLike.adopt_queued`.
    - `ui/recovery.py`: the Unreviewed list (rows with a transcript) above the recoverable list. "Open for review" emits `review_requested` behind the same blocks and click-time `_selection_blocked` re-check as a resume. Discard is shared as `_discard`. `expiry_label` plus the `expiry_warning` signal fire once per session entering the window. Also `unreviewed_infos`, `show_message` and the `clock` seam.
    - `ui/transcript.py`: `show_document(note_committed=)` sets `_note_committed` after the reset and relabels Generate as `REGENERATE_NOTE_LABEL`.
    - `ui/note.py`: `show_saved_note(note, document, info=, copy_enabled=, on_abandon=)` shows the note read-only (`format_note_body`, the one renderer). `_copy_ready` accepts a saved note when the flag is on and it has no unresolved error. `clear()` drops it.
    - `ui/main_window.py`:
      - `_on_review_requested` (named refusals on the row) and `_open_adopted`: it clears the Note tab (the 5.3 rule), shows the document on the live callbacks with `can_generate=True`, sets source "live", runs `_begin_checkout(..., adopted=True)` from the adoption's record (no second decrypt), and lands on the saved note or the transcript.
      - `_begin_checkout`, factored out of `_open_checkout_encounter`.
      - `recovered_writeback_target` returns None for an adopted checkout.
      - `_on_live_transcript` releases a replaced recovered checkout (only when its key copy was destroyed).
      - The expiry cue.
      - `closeEvent`'s on-close list (a first close is refused with the list; a second within `CLOSE_CONFIRM_SECONDS` quits), via `_unreviewed_expiries` (the Unreviewed rows plus the live queued session).
    - Reading recorded for the review: D6's "keeping the clinician's edits, confirmations and saved prose" is read as the saved note shown AS SAVED and read-only (a ratified note has no draft to re-edit), so changing it means Regenerate. The config-mismatch case adds its reason line to that same read-only view.
    - Tests: `test_unreviewed_review.py` (new):
      - `TestAdoptQueued` (13, Windows).
      - `TestReadForReview` (4), `TestReviewCopy` (8).
      - `TestUnreviewedSection` (5).
      - `TestOpenForReview` (9, Windows), `TestCloseList` (3, Windows).
      - `test_ui_screens.py`: the Recovery button-label pin, and `test_live_transcript_close_never_releases_recovered_checkout` rewritten (the replaced checkout is released; an unrelated one survives).
    - Docs: the threat model's "OPEN FOR REVIEW" paragraph with residue (1)–(3); data-flow flow 6; the retention schedule's encounter row and 24-hour rule; CHANGELOG.
  - Composer's suites on the e2 tree: GREEN (desktop 3865, extension 105). 5.5 and 5.6 followed in leg e3.
- [x] 🟩 5.5: **Reminder on reopening a note**
  - DONE 2026-09-28 (leg stage-5-exec-e7):
    - App start rebuilds the reminder index: one `encounter.enc` decrypt per Unreviewed session, and a ref minted for each.
    - `state.banner` carries ids and a count, never a name.
    - `open_review` is gated by exact ref plus index membership; it is refused while a review holds the lease or a session is active (round 32 LOW-023). The window comes forward and flashes.

    Suites 3922 + 105; rounds 32–35. Needs the Phase 6 panel to see from Chrome.
  - Files: `ui/bridge.py`.
  - Behaviour: a `context` for a note in the index sets the banner in `state`, carrying the banner target's `session_ref` from D2's registry (refs for indexed sessions are minted at startup reconstruction and kept through retirement). `open_review` resolves that exact ref and brings the desktop window forward on that session, flashing the taskbar where Windows refuses focus.
  - Verification: restart → banner → review opens the right session; a service-worker restart re-renders the banner from `state`; a delayed click after the entry was removed or replaced is refused.
  - Built (leg `stage-5-exec-e3`, 2026-09-28; awaiting the composer's suites):
    - `session.py`: `session_ref_for(session_id)` (the reverse lookup, shared as `_ref_for_locked` with `adopt_queued`) and `register_session_ref(session_id)`, which returns the existing ref or mints one and refuses a non-session-id.
    - `ui/models.py`:
      - `reconstruct_reminder_entries(infos, *, unwrap=None, read_record=None)`, oldest first. It covers only rows with a transcript AND an encounter record: the key is unwrapped for the one read and destroyed in `finally`, any failure is skipped, and an unlinked record gives no entry. The readers resolve at call time (the spy seam).
      - `SessionControllerLike` gains `session_ref_for`, `register_session_ref` and `resolve_session_ref`.
      - `CHROME_REFUSALS` gains `review_in_progress` and `cannot_open`.
    - `ui/bridge.py`:
      - Constructor kwargs `reminders` and `open_review`.
      - `_banner_state`: the bound (focused) tab's allow-listed note → its clinic's `(clinic_id, note_id)` in the index → the newest session still referenced, its ref and the count capped at `max_banner_count`, with no name. It is published in `build_content`.
      - `_open_review(session_ref)` gates on: no index or opener (`not_available`); a ref that does not resolve, or resolves to a session not in the index (`session_changed`); `busy`; the lease (`review_in_progress`). It then calls the opener and reports its refusal.
      - Module docstring: COMMANDS, THE BANNER.
    - `ui/main_window.py`:
      - `attach_chrome_link` passes the index and `open_unreviewed`.
      - `reconstruct_reminders()` refreshes the listing, adds the entries and registers their refs.
      - `open_unreviewed(session_id)` looks the session up in the Unreviewed rows (refreshing once), returning `session_changed` when absent. It then calls `_raise_window` (showNormal when minimised, raise, activate, `QApplication.alert`) and `_on_review_requested`, whose False becomes `cannot_open`.
      - `_on_review_requested` now returns bool and lands on the Recovery tab on a refusal.
    - `app.py`: `window.reconstruct_reminders()` once, after the start-up sweep and before the Chrome link.
    - The banner carries no `patient_name`: a retired session keeps no display string (D3's display lifetimes), so it names ids and a count only.
    - Tests:
      - `test_ui_bridge.py`: `TestBanner` (8), `TestOpenReview` (6); the old `not_available` pin is kept as `test_open_review_without_an_index_is_not_available`; the Harness takes `reminders` and `open_review`.
      - `test_unreviewed_review.py`: `TestReconstruction` (5, Windows). It covers the decrypt spy (once per Unreviewed session, never again on refresh or prune), an unreadable record skipped, `open_unreviewed` for exactly that session, `cannot_open` under the lease, and restart → banner → `open_review` end to end.
      - `test_ui_screens.py`: `FakeController` gains the registry methods.
    - Docs: the threat model's bridge paragraph, its "Open for review" paragraph (the banner, `open_review`, residue (4)) and pipe residue (e); data-flow flows 6 and 19; the retention schedule's encounter row; CHANGELOG.
- [x] 🟩 5.6: **Cross-patient matrix — context cases**
  - DONE 2026-09-28 (leg stage-5-exec-e7): `test_cross_patient.py` — 5.1's tables run through a real bridge (19 rows), delayed A commands after B, a replayed report, `resume_previous` while B is on screen, pipe down, a second client (the old-client row now discriminates, codex round 33 PR-LOW-180), `open_review`'s own rows, and the two positive restart cases. Suites 3922 + 105; rounds 32–35.
  - Files: `test_cross_patient.py`.
  - Behaviour: the remaining matrix rows (target/`state_rev` mismatch, stale-`session_ref` Discard/Finish/Resume after B starts, bound-tab departure and closure vs a separate non-Cliniko tab, a non-bound or stale tab, a replayed report, Resume previous while B is shown, resume with the pipe down, a second pipe client, and the two-recordings-one-note reminder case), reusing 5.1's table. Zero failures across 3.6 + 5.6 is PLAN.md Phase 5's completion evidence.
  - Built (leg `stage-5-exec-e3`, 2026-09-28; awaiting the composer's suites):
    - `test_context_rules.py`: the evaluator's two tables are lifted to module constants `BOUND_TAB_CASES` (10) and `OTHER_TAB_CASES` (9), unchanged, and its tests parametrize over them.
    - `test_cross_patient.py` (a new section driven through the bridge `Harness` from `test_ui_bridge.py`: fake sender, injected Cliniko answers, no socket). The rows:
      - `test_the_bound_tab_rows` (10) and `test_another_tab_rows` (9) over 5.1's tables: paused, with the block's reason, iff the table says so. In each, the session and its context are unchanged; the bound tab stays `TAB` (or unbound after it closed); another tab never takes the binding. This includes the bound tab going `not_cliniko` or `closed` versus a separate non-Cliniko tab (the positive control), and a non-bound tab.
      - Start with a stale `state_rev` / a non-bound target.
      - Delayed Discard (confirmed), Finish, Resume and Resume previous for A after B started: each is `session_changed`, no slot runs, and B is unchanged.
      - A replayed report after resolution is ignored.
      - Resume previous while B's note is on screen never resumes, even once A's note returns after the window lapses.
      - Resume with the pipe down is `pipe_down`.
      - A second pipe client pauses with the `new_client` block; the old client's command is ignored, the new client's resume is `report_mismatch` until it reports the note.
      - `open_review` rows (the Phase 4 recommendation): the live ref, an unknown ref and a removed entry's ref are each `session_changed` with the opener never run.
      - Positive (Windows): two recordings on one note stay indexed across two restarts, and completing one keeps the other; a saved note reopens as saved after a restart.
    - What the stale-seq row covers: a report from a STALE tab or seq is ignored — `seq` is per connection (the replay row); the stale-result rows are 3.6's.
    - The saved-edits positive case writes the finalised note directly: the saved note IS the edits, and "retire" is the reconstruction's own path.

### Phase 6 — Chrome extension UI
- [x] 🟩 6.0: **Extension test environment**
  - DONE 2026-09-28: live smoke PASS (the consolidated morning smoke over Phases 4–8, clinic 1, mock patients; practitioner-reported in chat).
  - Get the practitioner's authorisation, then add a pinned DOM-environment devDependency to `extension/package.json` and the Vitest config, with a `chrome.*` fake module.
  - BUILT (leg `stage-6-exec-f1`, 2026-09-28): the practitioner authorised ONE pinned dev-only DOM library at 2026-09-27 21:39; the composer installed **`jsdom` 30.1.1** as an exact devDependency with `--ignore-scripts` (`package.json` + `package-lock.json`). `extension/vitest.config.ts` (new; the crx build plugin no longer loads under test) runs two projects: `node` (every `src/**/*.test.ts` except DOM tests, as before) and `dom` (`src/**/*.dom.test.ts` under jsdom). `extension/src/test/chrome-fake.ts` is the recording `chrome.*` fake (runtime, alarms, action, tabs, windows, scripting, sidePanel, storage — storage records every write so a test can prove no name is stored). jsdom's engines (`^22.22.2 || ^24.15.0 || >=26.0.0`) narrow AGENTS.md's Node 22 floor to 22.22.2 (updated). 🟨 until the composer's `npm run qa` shows both projects running.
- [x] 🟩 6.1: **Manifest and build**
  - DONE 2026-09-28: live smoke PASS (the consolidated morning smoke over Phases 4–8, clinic 1, mock patients; practitioner-reported in chat).
  - Files: `extension/src/manifest.ts`, `extension/vite.config.ts`, a stub `extension/src/page.ts`.
  - Behaviour: `sidePanel` and `scripting` permissions (scripting limited to Cliniko hosts), `side_panel.default_path`, `content_scripts` for `https://*.cliniko.com/*`, no `tabs` permission. A manifest pin test.
  - `AGENTS.md` Local Run Steps: rebuild, reload, and fully restart Chrome after manifest changes.
  - BUILT (leg `stage-6-exec-f1`): `manifest.ts` adds `sidePanel` + `scripting`, `side_panel.default_path: src/panel.html`, and one content script (`src/page.ts`, `https://*.cliniko.com/*` only, `all_frames: false`, `document_idle`); no `tabs`, no `<all_urls>`. `scripting` has no host scoping of its own — it reaches only `host_permissions` (Cliniko), and the hub injects only into tabs on a Cliniko host. New `src/manifest-paths.ts` holds the shared paths so the worker never bundles the crx plugin. `vite.config.ts` is UNCHANGED: crxjs builds `side_panel.default_path` and TS content scripts from the manifest. Stubs `src/panel.html` / `src/panel.ts` / `src/page.ts` build until 6.3/6.4. `manifest.test.ts` pins the four permissions, the hosts, the one top-frame content script, the panel path, and the key's extension id (`mbmhglgadhdohpgbmpbjnaifjagfdfid`, computed from the key). AGENTS.md step 8 updated (rebuild/reload/restart after a manifest change; the badge now reflects the app). 🟨 until `npm run qa` + `npm run build` pass.
- [x] 🟩 6.2: **Background: tab tracking, reports, relay, badge and re-injection**
  - DONE 2026-09-28: live smoke PASS (the consolidated morning smoke over Phases 4–8, clinic 1, mock patients; practitioner-reported in chat).
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
  - BUILT (leg `stage-6-exec-f1`): `context.ts` (new: `classifyUrl` / `clinikoHost` / `noteUrl`, `ContextReporter` — the one `context` producer — and `sliceFor`); `hub.ts` (new, `chrome`-free: the relay, sender checks, commands, "Resume previous", re-injection, the panel view and per-tab slices); `connection.ts` (`send` validates the whole envelope with the mirror before posting; `badgeFor` replaces `BADGES`; `onHandshake` / `onChange` hooks; `appState` / `wasLive`); `background.ts` wires Chrome's events, `setPanelBehavior({openPanelOnActionClick: true})`, and a `HubApi` over the real APIs. Tests: `context.test.ts`, `hub.test.ts`, `background.test.ts` (the worker booted against the fake), `connection.test.ts` (+ badge, `send`, hooks). Interpretation calls (each LOW, applied, revisable): (1) the badge keeps a green **OK** while the app runs idle (D1 said "nothing") — the Phase 4 executor's recommendation that the badge reflect the app; OFF when it is closed; (2) `focused` ignores `WINDOW_ID_NONE` (Chrome losing focus to another program changes nothing); (3) "Resume previous" brings forward a tracked tab already showing the note before navigating anything, and never reloads a tab already on it; (4) the login page is matched as `/users/sign_in` — UNVERIFIED on a live account (any other path reads `other_cliniko`, and the bound tab leaving its note pauses either way); (5) a tracked tab reported `not_cliniko` is untracked, so later focus changes on it send nothing; (6) with the link down, allow-listed tabs keep the page script live and show the paused frame if a session was live (the app pauses on pipe loss), and the block is dropped (its buttons could not reach the app). Unexpected host-bound types still fail the connection as before (a broken peer); a refusal never does. 🟨 until the composer's `npm run qa` + `npm run build`.
- [x] 🟩 6.3: **Page script: frame, block and URL heartbeat**
  - DONE 2026-09-28: live smoke PASS (the consolidated morning smoke over Phases 4–8, clinic 1, mock patients; practitioner-reported in chat).
  - Files: `extension/src/page.ts`.
  - Behaviour: D1's frame and block in a closed shadow root, rendered with `textContent` only. Buttons act on `isTrusted` clicks and carry the `session_ref` of the `state` the block was rendered from; Discard needs its second click. The script is inert until allow-listed, and returns to inert (frame, block and patient data removed; reports stopped) when its host leaves the allow-list (D13). It sends only `location.href` changes to the background (the SPA backstop; the background stays the single `context` reporter) and never reads Cliniko's DOM.
  - BUILT (leg `stage-6-exec-f2`): `extension/src/page.ts` — `PageScript` (hello once at start; slices accepted only from this extension's worker, never a tab; inert/teardown on an inactive slice; a 500 ms heartbeat that runs only while active and reports only an href change; the frame (`data-frame`) and the block card inside a CLOSED shadow root on one `[data-cliniko-scribe]` element, styled through the CSSOM so the page's CSP cannot refuse it; buttons act on trusted clicks only and send `{kind: "block", action, session_ref, state_rev[, confirmed]}` from the slice they were drawn from; Discard arms for 15 s and disarms on a different session's block; an element the page removes is re-attached on the next heartbeat; an orphaned copy (runtime gone after an update) tears itself down; a re-injected copy removes the old copy's element). The only DOM it reads is its own marker element. Tests: `page.dom.test.ts` (12). Residue (a cue, never the control — D13): the block overlay absorbs pointer input but not the page's keyboard shortcuts, and the page's own scripts or CSS can keep the frame and the block hidden or covered for as long as they like (restyled, clipped, moved off screen, covered from the top layer, or re-hidden on every tick); the heartbeat only puts back an element that was removed. The app's pause rule and command checks are the enforcing controls (round 38 PR-LOW-212; an `important` restyle per heartbeat was considered and not applied, because the hiding routes are an open class).
- [x] 🟩 6.4: **Side panel**
  - DONE 2026-09-28: live smoke PASS (the consolidated morning smoke over Phases 4–8, clinic 1, mock patients; practitioner-reported in chat).
  - Files: new `extension/src/panel.html`, `extension/src/panel.ts`.
  - Behaviour: D1's five layouts plus the banner, `textContent` only, the consent tick rules, Start sending `command{start, consent, target, state_rev}`, every other session command carrying the `session_ref` from the `state` it was rendered from (D2), and the refusal line from `last_refusal`.
  - Spike: can `sidePanel.open()` run from the action click? Record the result.
  - BUILT (leg `stage-6-exec-f2`): new `extension/src/panel-view.ts` (the pure layout model: `panelModel(view)` → Message / Checking / Ready / Live / Blocked plus the banner, the queued line, the refusal line and the warnings) and `panel.ts` (`Panel`: draws the model with `textContent` only, a port to the worker named `scribe-panel` that reconnects 1 s after a worker restart, commands built from the drawn model); `panel.html` gains the stylesheet. Rules held: Ready only when the app's bound report IS the focused tab (the hub's `PanelView.focus` now carries `tab_id`); Start sends `{action: start, state_rev, consent: true, target}` and clears the tick, the tick is never pre-ticked and is cleared when the note (tab, host, patient, note, verification) changes or Ready goes away; Live's Pause / Resume / Finish consultation and Blocked's Resume previous / Finish previous / Discard previous (second click within 15 s) carry the ref of the state they were drawn from; the banner's "Open for review" carries the banner's ref; a queued or reopened session shows no timer, only "The last recording is waiting for review in Clinic Scribe."; the refusal line is the app's `last_refusal.message` (`role="alert"`), and a refused note names D4's reason in the desktop's words. Tests: `panel-view.test.ts` (26), `panel.dom.test.ts` (10).
  - SPIKE (recorded from `@types/chrome` 0.2.2 — no live check headless): `chrome.sidePanel.open({windowId|tabId})` (Chrome 116+) "may only be called in response to a user action". It is NOT needed for the action click: the worker calls `setPanelBehavior({openPanelOnActionClick: true})`, so the toolbar icon opens the panel natively. Content scripts cannot call `chrome.sidePanel`, so the page block's buttons send their commands directly (D1) and never open the panel. Whether a worker-side `open()` would honour a gesture forwarded from a block click was NOT tried — nothing depends on it. The morning smoke checks the icon.
  - Interpretation calls (LOW, applied, revisable): (1) D1's "Another Chrome profile is connected to Clinic Scribe" has no protocol signal (the host sends `app_running: false` whenever it cannot reach the app), so the not-running message carries the hint "If it is open, another Chrome profile may be connected to it."; (2) "Finishing <A>…" has no timer and no buttons; (3) Live has no Discard (D1 lists Pause/Resume and Finish consultation; Discard stays on the desktop and in Blocked); (4) the banner is shown over Message and Ready only, as D1 says, and only while a Cliniko tab is in front (round 36 LOW-029); (5) warnings map known codes (`new_consultation`, Phase 7) and show nothing for an unknown code.
- [x] 🟩 6.5: **Extension tests**
  - DONE 2026-09-28: live smoke PASS (the consolidated morning smoke over Phases 4–8, clinic 1, mock patients; practitioner-reported in chat).
  - Files: `*.test.ts`.
  - Behaviour: Validation's extension classes (layouts, the markup-name fixture, host scoping, trust checks, re-injection, badge, manifest pin, no names in storage, no key in payloads).
  - BUILT (legs f1–f2), class by class: the URL parser, inertness and teardown, per-tab host scoping with the cross-clinic block (`context.test.ts`, `hub.test.ts`, `page.dom.test.ts`); the five layouts plus the banner (`panel-view.test.ts`, `panel.dom.test.ts`); the markup-name fixture (`page.dom.test.ts`, `panel.dom.test.ts`, `context.test.ts`); `isTrusted` and sender checks (`page.dom.test.ts`, `hub.test.ts`); re-injection on `onInstalled` (`hub.test.ts`, `background.test.ts`); the badge (`connection.test.ts`); the worker restart getting state back (`hub.test.ts`, `background.test.ts`); `resume_previous` navigation from the allow-list (`hub.test.ts`); the manifest pin (`manifest.test.ts`); no name in `chrome.storage` (`background.test.ts`, `panel.dom.test.ts`); no key in any payload (`background.test.ts`: every message to the host re-parses under the mirror, which refuses unknown fields, and an injected key-shaped field never reaches the host or a tab).

### Phase 7 — Hands-free and warnings
- [x] 🟩 7.1: **Global hotkey** `[executor: premium-only]`
  - DONE 2026-09-28: live smoke PASS (the consolidated morning smoke over Phases 4–8, clinic 1, mock patients; practitioner-reported in chat).
  - Files: `ui/main_window.py` (`nativeEvent`), new `hotkey.py`.
  - Behaviour: D7. The chord is chosen here (AltGr-safe); pause/resume go through `pause_for` and the guarded resume; a registration failure shows in the desktop and in `state`.
  - BUILT (leg `stage-7-exec-g1`, 2026-09-28; awaiting the composer's suites):
    - `desktop/src/scribe_desktop/hotkey.py` (new, Qt-free): **Ctrl+Shift+F9** (`MODIFIERS` = Ctrl | Shift | `MOD_NOREPEAT`, `VK_F9`, id `0x5C51`); the `HotkeyRegistrar` seam with `Win32HotkeyRegistrar` (ctypes `RegisterHotKey` / `UnregisterHotKey`, returning the Windows error code); `HotkeyStatus` (`not_set_up` / `on` / `failed` + error); `GlobalHotkey.register` / `unregister` never raise (a refusal is a status), `matches` only while reserved.
    - `ui/main_window.py`: `_native_msg` (the `_MSG` head, shared with `_is_suspend_event`); `nativeEvent` re-delivers the reserved chord's `WM_HOTKEY` through the queued `_hotkey_pressed_q` signal and still returns `(False, 0)`; `attach_hotkey(registrar=None)` (only `app.main` calls it; a refusal goes to the status line and the bridge), `detach_hotkey` (in `closeEvent` and at `aboutToQuit`), `hotkey_status`; `on_hotkey`: RECORDING → `pause_for(PauseReason.HOTKEY)`; PAUSED → `SessionScreen.on_resume()` (the resume guard runs — no bypass), a refusal flashed with its message; any other state nothing. `attach_chrome_link` hands the bridge the current status.
    - `ui/bridge.py`: `set_hotkey_status` → `state.hotkey` (`{available: true, chord}` only while reserved) and the Session screen's line.
    - `ui/models.py`: `HOTKEY_LINES`, `SPOKEN_PAUSE_LINES`, `hands_free_lines`, `HOTKEY_FAILED_STATUS`, `HOTKEY_RESUMED_STATUS`; `ChromeView.hotkey` / `hotkey_chord` / `spoken_pause` (replacing `spoken_pause_unavailable`) / `new_consultation`; `CHROME_HANDS_FREE_LINE` ("not set up") removed; `SessionControllerLike.live_transcription_attached`.
    - `app.py`: `window.attach_hotkey()` after the Chrome link, a `hotkey` log line (state only), `aboutToQuit` → `detach_hotkey`.
    - Side panel (`panel-view.ts` / `panel.ts`): the Live layout (recording or paused) shows "<chord> pauses and resumes." or "Pause hotkey unavailable — see Clinic Scribe's Session tab." — the chord from `state`, as text.
    - Tests: `test_hands_free.py` `TestHotkeyModule` (fake registrar), `TestHotkeyWindow` (fake registrar; one synthetic `WM_HOTKEY` through Qt's real Windows dispatch in a child process — no real chord is ever reserved); `TestHandsFree` (bridge); `TestChromeView` hotkey lines.
- [x] 🟩 7.2: **Spoken pause**
  - DONE 2026-09-28: live smoke PASS (the consolidated morning smoke over Phases 4–8, clinic 1, mock patients; practitioner-reported in chat).
  - Files: new `voice_commands.py`; a slot on `TranscriptScreen.live_window` wired in `ui/main_window.py`.
  - Behaviour: D7: the leading-boundary matcher, ignoring a phrase whose first word starts before the last resume's captured-audio cutoff (word timestamps, not window end), the "unavailable" status through 4.5's accessor, and the desktop cue on every pause.
  - BUILT (leg `stage-7-exec-g1`, 2026-09-28; awaiting the composer's suites):
    - `desktop/src/scribe_desktop/voice_commands.py` (new, Qt-free): `phrase_tokens` (a word split only at whitespace, hyphens and slashes, each part normalised by `note.normalise_token` — Task 1.2's ONE normaliser, pinned by `test_note.py::test_normalisation_has_exactly_one_implementation`; leg g2 replaced g1's own `normalise_tokens`, which that pin caught); `SpokenPauseDetector` — "scribe pause" as two consecutive whole-word tokens, one token carried from the previous window (joined only when the two words start ≤ `CARRY_MAX_GAP_SECONDS` = 3.0 s apart — round 41 LOW-033), a match counting only when its FIRST word's `start_seconds` ≥ the cutoff; `note_resume(captured_seconds)` sets the cutoff to that + `RESUME_CUTOFF_MARGIN_SECONDS` (one capture chunk, 1.0 s — the capture worker can still hold up to a chunk of pre-Pause audio at the Resume), never lower; `reset` per recording. `spoken_pause_state(state, attached, failure)` → `idle` / `on` / `unavailable` (4.5's `live_failure` plus the controller's existing `live_transcription_attached`; no new controller accessor was needed). The module docstring documents the latency.
    - `ui/main_window.py`: `transcript_screen.live_window` → `_on_live_window` (only while RECORDING or PAUSED) → `pause_for(PauseReason.SPOKEN)` (the desktop cue on every pause, through the one path); `session_resumed` → `_on_session_resumed` (the cutoff from `controller.recorded_seconds`); `_on_session_started` resets both rules. The Transcript screen's own slot still renders every word.
    - `ui/bridge.py`: `state.spoken_pause` and the Session screen's spoken line from `spoken_pause_state`; the existing unavailable line now also covers live transcription being off.
    - Side panel: 'Say "scribe pause" to pause.' or "Spoken pause unavailable for this recording." in the Live layout.
    - Tests: `test_hands_free.py` `TestNormalise`, `TestSpokenPauseMatcher` (positives; "prescribe, pause" and other near-misses; the cutoff; a mixed window spanning the Resume both ways; a phrase split across windows), `TestSpokenPauseState` (every state), `TestPhraseRulesInTheWindow` (pause and the phrase kept in the live view; a pre-Resume phrase ignored; a new Start clears the cutoff; windows outside a recording ignored; the unavailable line).
- [x] 🟩 7.3: **New-consultation warning**
  - DONE 2026-09-28: live smoke PASS (the consolidated morning smoke over Phases 4–8, clinic 1, mock patients; practitioner-reported in chat).
  - Files: `voice_commands.py`, `ui/bridge.py`.
  - Behaviour: D8. A warning only, in the panel and the desktop, test-pinned.
  - BUILT (leg `stage-7-exec-g1`, 2026-09-28; awaiting the composer's suites):
    - `voice_commands.py`: `CLOSING_PHRASES` (14), `GREETING_PHRASES` (12), `NEW_CONSULTATION_WINDOWS = 3`, `NEW_CONSULTATION_WARNING = "new_consultation"`; `NewConsultationWatcher.feed` returns True exactly once per recording when a greeting follows a closing phrase in the same window (after it) or within 3 windows.
    - `ui/main_window.py` `_raise_new_consultation`: the status line, the Session screen's message and a taskbar flash; `bridge.set_new_consultation_warning(session_id)`. No pause, block or state change.
    - `ui/bridge.py`: `state.warnings = ["new_consultation"]` and the Session screen's warning line while THAT recording is recording or paused; dropped by `_tick` once it finishes or ends.
    - No protocol change: `state.warnings` already carries reason codes (fixtures unchanged), and the panel already mapped `new_consultation` (Phase 6); an unknown code still shows nothing.
    - Tests: `TestNewConsultationRule` (the lists and N pinned; once per recording; the window budget 0/1/3 warn, 4 does not; near-misses), `TestPhraseRulesInTheWindow.test_the_warning_is_shown_and_never_pauses`, bridge `TestHandsFree` (published only for its live recording, dropped at Finish), `panel.dom.test.ts` (drawn as text, no control changed).
    - Docs (Phase 7 as a class): threat model "HANDS-FREE AND WARNINGS" paragraph with residue (1)–(3), and the pause-rule paragraph's two forward references; data-flow flows 14 and 19; retention live-buffers row; CHANGELOG.

### Phase 8 — Security docs for the new surfaces and the live smoke
- [x] 🟩 8.1: **Security docs for the pipe, Chrome and encounter surfaces, as one class** `[executor: premium-only]`
  - DONE 2026-09-28: live smoke PASS (the consolidated morning smoke over Phases 4–8, clinic 1, mock patients; practitioner-reported in chat).
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
  - BUILT (leg `stage-8-exec-h1`, 2026-09-28; docs only, awaiting review):
    - `threat-model.md`: title and scope (patient names now exist, in memory); trust boundary 1 points to the pipe; the Cliniko client's callers (adds the Chrome bridge and Unreviewed adoption, drops "ledger unwired"); NOTE VERIFICATION (names now shown by the bridge only); THE ENCOUNTER RECORD (every decrypt site — checkout `ui/main_window.py:988`, adoption `session.py:1136`, the start-up index pass `ui/models.py:977`; the consent record goes with its session, durable evidence is PLAN Phase 6; the tick is the extension's assertion); the pause rule's residue (1) no longer says "until the Phase 6 extension"; NEW section "The Chrome extension" — enforced (manifest `extension/src/manifest.ts:23-41`; reports from URLs only `context.ts:55-70`, 243-259; sender checks `hub.ts:318-358`, 362-420; `isTrusted` `page.ts:383`; per-tab scoping `context.ts:300-340`; `textContent` `page.ts:122`; lifecycle `page.ts:215-245`, re-injection `hub.ts:293-313`) and residues (1)–(11): the cue is not a control and keyboard input passes under the block; detectability via the web-accessible page-script module (`extension/dist/manifest.json` `web_accessible_resources`, `use_dynamic_url: false`) and the page script's own marker element; what a Cliniko page can see; the in-page session-expiry dialog; pre-navigation speech and the report-to-pause latency; the unverified login path; ONE Chrome profile; crash dumps (Chrome's and Windows Error Reporting's) possibly holding names; Chrome's memory; the text-matching sinks guard; reports as assertions. Out-of-scope and review triggers updated.
    - `data-flow-map.md`: title; intro callers; components row for the extension; flow 10 (8.2); flow 18's triggers; NEW flow 20 (what Chrome reads, keeps and draws; per-tab scoping; memory only); the Chrome-storage non-flow; "The host↔app link (was Phase 5 preview)" replaced by "The Chrome side at a glance".
    - `retention-schedule.md`: title and intro; clipboard row (8.2); API-response row (names shown only by the bridge); encounter row (no consent evidence outlives the session → PLAN Phase 6); NEW rows — the Unreviewed reminder index and session references, the Chrome link in the app, Chrome-side memory, crash dumps.
    - `docs/design-system.md`: intro; the two-click Discard on every surface (desktop 10 s, block and panel 15 s); NEW "Chrome side" section (the five layouts and the banner, the never-pre-ticked panel consent box as the explicit exception, the frame as a cue, the block, the badge, text-only strings); Copy's formats.
    - `protocol/fixtures/README.md`: which `state` fields can carry a name (`banner.patient_name` allowed by the shape, never sent — `ui/bridge.py:938-961`); `context`/`command` carry no name, URL or key.
    - `PLAN.md` (exactly the four): "stop" means pause; flow step 9 met by construction; the Phase 5 delivery note (read-only API); `ConsentAttestation` as built (`encounter.py:145-154`).
    - Also for consistency (same class): `docs/security/intended-use.md` scope note (2026-09-28), `docs/security/README.md`, `docs/security/incident-process.md` (pipe squatter / wrong-patient / cross-clinic-name triggers; the badge's OK), AGENTS.md pointers (the extension pointer gains the threat-model section, flow 20 and the one-profile residue; a new Copy pointer), CHANGELOG.
- [x] 🟩 8.2: **Copied note kept out of Windows clipboard history and cloud sync** `[executor: premium-only]`
  - DONE 2026-09-28: live smoke PASS (the consolidated morning smoke over Phases 4–8, clinic 1, mock patients; practitioner-reported in chat).
  - BUILT (leg `stage-8-exec-h1`, 2026-09-28; awaiting the composer's suites):
    - `ui/models.py`: `CLIPBOARD_EXCLUSION_FORMATS` (the three names, each `(0).to_bytes(4, "little")` — the exclusion format also carries the zero DWORD so every format holds a non-empty block; the task allowed "empty/zero"), `clipboard_mime_formats()` (a fresh name → bytes dict), `windows_clipboard_mime_type(name)` (`application/x-qt-windows-mime;value="<name>"`). Qt-free.
    - `ui/note.py` `_copy_note`: `QMimeData` with `setText(models.format_note_body(note))` — what `QClipboard.setText` itself builds, so the paste is byte-identical — plus `setData` for each format, then `setMimeData`. `_copy_ready` and the click-time re-check unchanged. Module docstring and method docstring state the button-only reach.
    - Tests: `test_ui_screens.py` `_fake_clipboard` captures `setMimeData` (text into the same payload list; optional `mimes` list) as well as `setText`, so both round-70 pins keep their strength on either clipboard route; NEW `test_copy_keeps_the_note_out_of_clipboard_history_and_sync` (nothing before Save; one mime whose text is `format_note_body`, exactly `text/plain` + the three formats, each payload 4 zero bytes); `test_ui_prose_stage.py`'s stub gains `setMimeData`; `test_ui_models.py` `TestClipboardFormats` (+4: the map, the DWORD shape, a fresh map per call, the MIME type).
    - Docs at every listed site, each saying what the formats do NOT do (same-user readers, third-party managers, stays until replaced, nothing cleared): threat model 3A surface 4, data-flow flow 10, the retention clipboard row, `intended-use.md`, `docs/design-system.md` (Copy), CHANGELOG.
  - ADDED (leg `stage-8-exec-h2`, 2026-09-28; composer disposition `OWNERSHIP: gate-disposition key=task-8.2-selection-copy` — completing 8.2's own goal, the round-35 selectable panel KEPT; revisable by the practitioner): the selection route.
    - Class check across `ui/`: `note_body` is the only widget that shows note text selectably (both transcript views are `NoTextInteraction`; `benchmark_output` and the Practitioner tab's `paste_box` hold no note).
    - `ui/note.py`: `_place_note_text(text)` — the ONE placement (plain text + the three formats; the button's `_copy_note` now calls it). `_NotePanel(QPlainTextEdit)` replaces the plain `note_body`: `keyPressEvent` takes every binding of `QKeySequence.StandardKey.Copy` (Ctrl+C, Ctrl+Insert) and calls `copy_selection()` instead of Qt's copy; `build_context_menu()` (Copy — enabled only for a ratified note with a selection — and Select All) replaces Qt's context menu, whose Copy would bypass the formats; `copy_selection()` re-checks the screen's `_copy_ready` at the moment of copying and places `textCursor().selection().toPlainText()` — the text Qt's own copy would place. Intercepting the ACTIONS (not overriding `createMimeDataFromSelection`) was chosen because the ownership of a QMimeData returned from a Python override of that virtual could not be verified offline; a dangling clipboard pointer would crash.
    - Named, not covered: a DRAG of the selection is Qt's own (`createMimeDataFromSelection`, no formats) but never touches the clipboard; the text lands where it is dropped. Screenshots and same-user clipboard readers as before.
    - Tests (`test_ui_screens.py`): `_attempt_copy` now also tries the selection routes (keyboard, context menu, direct call over `selectAll()`), so both round-70 pins cover them; NEW `test_a_keyboard_copy_of_the_selection_carries_the_formats` (every Copy binding over the whole selection, then a partial selection across a line break — exact text and formats), `test_the_context_menu_copy_carries_the_formats` (the menu's two entries, Copy's placement, and a right-click opening exactly that menu through a stub — never a modal `exec`), `test_an_unratified_panel_places_nothing_even_with_a_selection`; the shared `_assert_note_mime` / `_ratified_note_screen` helpers.
    - Docs: the residue sentence at every h1 site now states what the code does (threat model 3A surface 4, flow 10, the retention clipboard row, `intended-use.md`, design system, AGENTS.md Copy pointer, CHANGELOG, `ui/note.py` / `ui/models.py` comments).
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
- [ ] 🟨 P.2: **Practitioner live smoke** (practitioner-owned) — clinic 1 PASS 2026-09-28; clinic 2 waits on Task P.1 for clinic 2
  - Clinic 1, 2026-09-28 (mock patients A and B, no patient data recorded): the consolidated 22-step smoke over Phases 4–8 PASSED, plus the re-checks R1–R5 for the morning's fixes (the Modern Standby sleep + session-lock pause, rounds 49–52; H1's Start-while-locked refusal and block wording; H3's Back/Forward redraw; H4's side-panel focus and "On screen" label). Step 2 first failed on a missing native-host registry key (fixed by re-running `register-native-host.py` from the practitioner's own terminal — `docs/lessons.md`); step 5 first failed (sleep did not pause on Modern Standby) and led to the practitioner's sleep + lock decision (D5 addendum). Optional O1–O3 not run (O2's sign-in path stays unverified).
  - Smoke finding **S1** (LOW, production, the Recovery tab): after a Start retires a recording, the Recovery tab's Unreviewed list is not refreshed until an event that refreshes it (the practitioner pressed Refresh and A appeared, marked "note saved"). The reminder index and banner were correct. Fix: refresh the list when a Start retires a session (and when the tab is shown). **FIXED 2026-09-28 (round 62, LOW-060, leg stage-9-exec-k7):** a retire and opening the Recovery tab both re-list it (stat-only; custody exclusion unchanged). Re-check: back-to-back with A saved → the Recovery tab lists A without pressing Refresh.
  - The "confirm as you go" items (desktop recordings pause on sleep or lock only; Start clears the previous patient's saved note from the Note tab; a reopened saved note is read-only and Regenerate replaces it only on Save; the Ctrl+Shift+F9 chord, the 1 s grace and the 3 s gap; a refused hotkey Resume shows on the desktop only; no Discard in the panel while recording; Ctrl+C and right-click Copy protected like the Copy button) raised no objection; the overnight decisions (Tasks 4.3 (b), 5.4 (a), Task 6.0's jsdom) stand as revisable.
  - The Validation practitioner-run list, on both clinics.
  - Record the outcomes (no patient data) in the Done note.

### Hardening stage
- [x] 🟩 H1: `/review-loop` to convergence over Phases 1–8 as one surface
  - Done (leg `stage-9-exec-k1`, 2026-09-28; converged at round 3 of cap 3; suites composer-run):
    - Rounds 53–55 found 3 MED + 18 LOW, all applied:
      - Round 53: 2 MED + 11 LOW. Six lens subagents.
      - Round 54: 1 MED + 5 LOW. Regression and same-family sweep.
      - Round 55: 0 MED + 2 LOW, docs only.
    - Production changes:
      - Every Start (Chrome's and the desktop's) is refused while the computer is locked.
      - A failed Start, or a replaced recovered view, still puts the retired or recovered linked session in the Unreviewed index.
      - A refusal line goes when what it was about leaves the screen, but a session command's refusal survives its note's check landing.
      - The page block's `note_changed` wording now matches the panel's.
      - Lone surrogates are cleaned from names.
    - Docs: the claim-vs-code class across the threat model, intended use, the data-flow map, the incident process, the retention schedule, the design system, PLAN.md, AGENTS.md and CHANGELOG.
    - Lens (f) dead code and duplication is recorded for H2 in round 53.
    - For H3: the code throttle, enrolment under lock, and checking an unlock with Windows.
    - For the write plan: the write-back freshness gap (Follow-Up Continuation Notes).
    - Expected suites:
      - Desktop: 4111 collected, 4110 passed + 1 skipped while `scribe-app` runs.
      - Extension: 297.
      - `npm run build` is required, because `page.ts` changed.
- [x] 🟩 H2: `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`
  - Done (leg `stage-9-exec-k2`, 2026-09-28; round 56; suites composer-run):
    - 16 findings (2 MED + 14 LOW).
    - 3 LOW applied, each behaviour-neutral and pinned:
      - `ContextReporter`'s dead `active` / `isTracked` removed;
      - the panel's Checking text taken from `CHECKING`;
      - two stale comments.
    - 13 recorded for H2a, each with an Executor recommendation and a `surface=`.
    - No user-visible string changed.
    - Expected suites:
      - Desktop: 4111 collected, 4110 passed + 1 skipped while `scribe-app` runs.
      - Extension: 297.
      - `npm run build` is required, because `panel.ts`, `context.ts` and `connection.ts` changed.
- [ ] 🟥 H2a: round 56's recorded simplifications (SIMP-004..016) — a scoped `/review-plan` on this task AFTER the P.2 live smoke, then `/fix` in the order it sets. Suggested order:
  - SIMP-006, the practitioner's product-name choice (recommended: "Clinic Scribe").
    - **DECIDED 2026-09-28 by the practitioner ("Go with Clinic Scribe") and DONE in leg stage-9-exec-k8.** The display name is "Clinic Scribe" everywhere a person sees it, and the extension is "Clinic Scribe Companion". Every internal `ClinikoScribe` identifier is byte-identical: the `%LOCALAPPDATA%\ClinikoScribe` folders, the mutex, the pipe, the Credential Manager prefix, the DPAPI key descriptions, `INSTALL_DIR`, the native-host name and the extension id. `desktop/tests/test_display_name.py` guards both halves.
  - Then SIMP-004 / 005, the canonical text tables pinned by a both-mirrors test.
  - Then SIMP-007, one re-verification pipeline.
  - Then the rest: 008–016.
  - SIMP-011's protocol-code merges wait for the write plan's protocol bump.
- [x] 🟩 H3: `/security-review` — log findings; same impact-tiered routing
  - Done (leg `stage-9-exec-k3`, 2026-09-28; round 57; suites composer-run):
    - 22 findings: 21 LOW + 1 record-only. No CRIT, HIGH or MED; no must-pause.
    - 8 applied:
      - 7 code, with 8 new desktop tests + 2 extension tests: the host's type guard, the pipe server surviving a connect-and-close, the back/forward re-hello, the credential tripwire markers, a deleted booking no longer refusing its note, the `dev` script removed, and two tests off the real logs.
      - 1 docs.
      - The threat model also now says "Windows session" and names five new residues.
    - 13 recorded for H3a, each with an Executor recommendation and a `surface=`.
    - SEC-018 (write-back freshness) confirmed as record-only for the write plan, in Follow-Up Continuation Notes.
    - Expected suites:
      - Desktop: 4119 collected, 4118 passed + 1 skipped while `scribe-app` runs.
      - Extension: 299.
      - `npm run build` is required, because `page.ts` changed.
- [ ] 🟥 H3a: round 57's recorded security items — a scoped `/review-plan` on this task AFTER the P.2 live smoke (together with H2a where they touch the same code), then `/fix`.
  - Needs the practitioner at the review:
    - SEC-003: Discard off the page block (D1).
    - SEC-009: the cooldown and spacing numbers.
    - SEC-013: the pipe-owner check (Task 4.3).
    - SEC-019: enrolment stops on lock (extends D5 to the profile surface).
  - Needs a host check first:
    - SEC-014: a low-integrity open of the pipe.
    - SEC-007: whether Cliniko serves the odd URL forms.
    - SEC-020: a real unlock's `SessionFlags`, confirmed during P.2.
    - SEC-021: sleep while pressing Start, added as a smoke step.
  - Code with tests:
    - SEC-008 (with H2a SIMP-007);
    - SEC-015;
    - SEC-016;
    - SEC-017;
    - SEC-022 (the live-view token).
- [x] 🟩 H4: a cross-family codex `/peer-review`, sliced by file group:
  - client + registry + security docs;
  - custody + encounter + pipe + host;
  - extension + UI + hands-free.

  Re-check to convergence.
  - Done (pass `stage-9.p1`, codex gpt-6-astra medium; legs stage-9-exec-k4 → k6, 2026-09-28; converged at peer round 4 of 5):
    - Rounds 58–60, the three slices: 1 MED + 6 LOW, all confirmed by the executor's LEG 1 and fixed in LEG 2 (k5).
      - Round 58: 3 LOW docs.
      - Round 59: 1 LOW docstrings, plus the `adopt_queued` sibling.
      - Round 60: PR-MED-330 and PR-LOW-331 in the side panel, and PR-LOW-332 as a doc change.
      - SEC-022 re-assessed LOW; it stays in H3a.
    - Round 61, the confirmation: every fix confirmed closed, plus 1 test-harness LOW (PR-LOW-340), fixed in place (k6).
    - Production changes (the side panel):
      - the timer updates in place, so focus and a click in progress survive;
      - focus is restored for the same session only;
      - buttons read their ref and revision at click time;
      - the Ready tick records itself as drawn;
      - "On screen" names a patient only for the focused note.
    - Expected suites:
      - Desktop 4119 collected (4118 passed + 1 skipped while `scribe-app` runs).
      - Extension 307.
      - `npm run build` is required (from k5's `panel.ts`).

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
  - (H1 round 53, recorded for the write plan) `writeback_context` has NO freshness bound: a re-verification counts until the clinic, target or `clinic_rev` changes, however old. `MainWindow.recovered_writeback_target()` takes no argument and uses the checkout's re-verification from when the session was opened, while `live_writeback_target(reverification)` needs the caller's; `ChromeBridge.live_reverification()` exists but nothing passes it in. The write must re-verify IMMEDIATELY before writing, on both entries — or bound `verified_at` — and wire one source, not add a third.
  - (H3 round 57 SEC-018, confirmed) There is NO write path today: `cliniko_client` refuses every method but GET before a connection exists, no POST/PATCH/PUT/DELETE appears in `desktop/src`, and `writeback_context`, both `MainWindow` write-target entries and `ChromeBridge.live_reverification` are called only from tests. One more fact for the write: `writeback_context` checks neither `verified_at` nor the request's `conn_gen` — only the target and `clinic_rev` bind it.

---
*Plan saved to: .cursor/plans/plan-cliniko-workflow-safeguards.md*
*To resume in a new session: run /start-session, then /load-plan*
*State-once convention: cross-section contracts live in Design Decisions (D1–D12) and Critical Constraints; other sections point to them.*
