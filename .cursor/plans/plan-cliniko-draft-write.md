# Feature Implementation Plan
**Feature:** cliniko-draft-write
**Overall Progress:** `0%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: `.cursor/plans/plan-cliniko-workflow-safeguards.md` (PLAN.md Phase 5, built first by practitioner decision 2026-09-27; this plan consumes its verified context, clinic keys, read-only client and write-back guard)
- Follow-up plans: None (PLAN.md Phase 6 — the audit record — is the likely next plan)

## Goal
PLAN.md Phase 4: after the clinician ratifies a note (Save), one click on the desktop Note tab writes it into the Cliniko draft treatment note the recording was started from, by `PATCH /treatment_notes/<note_id>` — never a POST, never anything but a draft. The write re-reads the note with Cliniko for that click, refuses by name when the note is final or already holds typed text, matches the note's own template before sending, records the attempt in the session before the request leaves, reconciles an unknown outcome by re-reading before any manual retry, and completes the session (key destroyed, directory removed) once Cliniko confirms — automatically, or after the clinician has seen the draft in Chrome, as the test write decides (D6). Notes still reach Cliniko by Copy when a write is refused. The security docs are rewritten as one class: the app's only network use is Cliniko's API, now reads plus this one draft write, and none at startup or idle.

Hardened 2026-09-29 by `/review-plan` (four lenses: coverage, practicality, risk, simpler-path) in the planning session; the adjustments are folded in below and summarised in the Handoff Note.

## Planning Extraction Summary
Populated 2026-09-29 from the confirmed extraction (anchor: `.cursor/plans/explore-cliniko-integration.md`, 2026-09-27, code baseline `33bd35e`; re-probed at HEAD `e509b56`), the safeguards plan's items routed here, and the critique gate (three lenses) plus the deferral gate.

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable 5.1 (extraction on Opus 5.5); executor Opus-class (Opus 5.5) via `/execute-loop`; tier-gap dosing applied (design decisions, edge-case inventory, API contract, per-task acceptance criteria locked; the transport allow-list, the custody ordering and the call gate carry exact wording)

### Agreed Scope (Build Now)
- The practitioner's test write on clinic 1 (moved out of the safeguards plan's P.1), through a `--test-write` mode of `scripts/probe-cliniko.py` that calls the app's own write method with the safeguards in Task 1.2, answering SIX questions: (1) does PATCH fill a web-created draft; (2) is a partial `content` MERGED (untargeted questions kept) or does it REPLACE the whole content — this decides the body shape (D4); (3) does the template GET carry the default answer text; (4) does Cliniko echo our HTML verbatim or sanitised (confirmation only — the comparison is always normalised, D5), with an adversarial marker; (5) with the Cliniko editor left open, does an editor save or autosave AFTER our write overwrite it; (6) does an edit saved in the editor BETWEEN our note GET and our PATCH survive (the probe pauses between the two). A finalised-note leg runs only on a dummy patient the practitioner creates.
- One `[decision]` task after the test write (Task 2.1) settling the typed-text default source (D4, A or C), the body shape (D4, partial or full) and whether a confirmed write completes automatically or after the clinician has seen it (D6).
- `cliniko_client.py`: a keyword-only request body reachable only through one public `write_draft_note(note_id, content: DraftContent)`; PATCH allowed only to `/v1/treatment_notes/<id>`; `DraftContent` a typed model holding `content` alone, defined IN the client module (D1); `get_treatment_note_template`; a PATCH-only bounded 422 read keeping filtered error field NAMES. `TestGetOnly` → `TestMethods` ("GET plus exactly one PATCH"); the drafts-only source and body-model tests.
- A shared `RateLimitLatch` (the per-clinic 60 s cooldown after a 429) owned by `MainWindow`, injected into the Chrome bridge and consulted by the checkout re-verification and the write (D13); the bridge's 1 s spacing stays bridge-private. SIMP-007's "one source" is met for the cooldown; SEC-008 is deferred (gate 2026-09-29).
- Rendering for Cliniko: `note.render_section_lines(..., apparatus=)` shared with `render_note`, a per-target grouper over `TemplateProfile.target_for`; `rich_text` → `paragraph` (escaped HTML), `plain_text` → `text`, the attestation checkbox never answered; review apparatus stripped (D7).
- Template match at write time against the note's own template (one GET); the profile resolved from `note.template_profile_id`; mismatch, ambiguity or an oversight-unmapped section refuses by name, nothing dropped silently (D4). Under Option C, a per-clinic `template_defaults.json` captured from a pristine note during P.1.
- The per-session write record `write.enc` — ONE current-state document with an `attempt` counter, rewritten with fsync per transition, the `attempting` state on disk before the request leaves — outcome classes written / refused / unknown, per-question normalised digests, bound to the saved note's identity (regeneration and a second Save are refused once an attempt exists), reconcile-by-re-read before a manual retry, no automatic retry (D5).
- The write in three hops (D3): worker (GET note = the verification, GET template) → GUI thread (`writeback_context`, reconcile, typed text, match, body, attempt row through `with_write_custody`) → worker (PATCH only) → GUI thread (result).
- Write custody: the existing `_custody_reservations` plus a `_writing_id` marker, held from before the first dispatch until the result is recorded; Replace key / Remove refused for that clinic meanwhile; `MainWindow.is_writing` read by `closeEvent`, `note_screen.is_busy`, the Transcript row and the bridge's pre-checks (D9).
- `complete_after_write(reservation)`: verify, key destroyed, directory removed, refs forgotten, reservation released under one lock; reached either automatically on `written` or from the Complete button after the clinician has seen the draft, per Task 2.1 (D6). SIMP-016 corrected: the reminder index keeps its key-existence prune (`ui/main_window.py` `prune_reminders`, an expired recording loses its reminder AND its ref as today); the separate ref-registry prune drops every ref that is neither a live session's nor a still-indexed session's (PR-LOW-022).
- The Note tab's "Write draft to Cliniko" button beside Copy, enabled by Save + the Copy ratification predicate + a `linked` fact pushed by `MainWindow`; live and adopted sessions only; no Chrome protocol change (D2). A mock-provider note is refused (D10). The success line rides `closed("written")`.
- A ~12-key microcopy dictionary that also covers every `WritebackRefusal` and `NoteRefusal` name through the existing `clinic_refusal_line` / `note_refusal_line` patterns (Task 5.1).
- The security-docs class rewrite as one task (D11): threat model, data-flow map (flow 18 + non-flows), retention schedule (the pre-committed write-back rule becomes built; a `write.enc` row; the `template_defaults.json` row if Option C is chosen), intended-use, incident-process (a wrong-note write incident), shipping-gate (mock sessions never write), `docs/security/README.md`, PLAN.md wording ("create" → "fill"), `AGENTS.md` pointers :84/:85/:88/:95 and Current Status, `docs/design-system.md` (the write control and its lines), the probe docstring.
- Offline-contract pins: a one-call-site AST pin that the write jobs are constructed only inside `MainWindow._on_write_requested`, whose only `connect` is the Note tab's `write_requested`; mock and unlinked sessions never call the transport.

### Deferred — Actionable Later
- **Clinic 2: P.1 (probe) and the test write.**
  - Why deferred: the practitioner lacks API-key permission on that Cliniko account (carried from the safeguards plan).
  - Intended future outcome: the same probe and test write, then the live smoke, on clinic 2.
  - Relevant files / subsystems: `scripts/probe-cliniko.py`, the Clinics tab.
  - Dependencies / prerequisites: Cliniko API-key permission for clinic 2.
  - Recommended next action: run Task P.1 then P.2 there when the key exists.
  - Risk if deferred: blocked-work: clinic 2 stays copy-only.
  - Revisit by: when the clinic 2 API key exists
- **Durable consent and audit evidence (PLAN.md Phase 6).**
  - Why deferred: the write record `write.enc` dies with the session (D5); a lasting record of consent, write and deletion results is Phase 6's minimal audit record.
  - Intended future outcome: an audit row per session (consent timestamp, clinic, booking/note ids, write result, deletion result) with its own custody and retention.
  - Relevant files / subsystems: `session_store.py`, `encounter.py`, `docs/security/retention-schedule.md`.
  - Dependencies / prerequisites: this plan closed.
  - Recommended next action: `/create-plan` for Phase 6.
  - Risk if deferred: correctness: until Phase 6, durable evidence rests on Cliniko and the practitioner's own process.
  - Revisit by: PLAN.md Phase 6 planning
- **SIMP-013 / SIMP-014 / SIMP-015** (`pipe_client.py` importing `pipe_server`'s private helpers; test-only members and the unconnected `pipe_lost` signal; splitting `ui/models.py`, `ui/main_window.py`, `ui/bridge.py`).
  - Why deferred: deferral gate 2026-09-29 — none touches the draft write, and SIMP-015 would churn the two files this plan edits most.
  - Intended future outcome: as recorded in the safeguards plan's H2a list.
  - Relevant files / subsystems: `pipe_client.py`, `pipe_server.py`, the three UI modules.
  - Recommended next action: a scoped `/review-plan` when the pipe changes or a UI split is planned.
  - Risk if deferred: minor: maintainability only; each is pinned by its own tests.
  - Revisit by: the next plan that changes the pipe or splits the UI modules
- **Manual Complete removing the session directory** (parity with `complete_after_write`, PLAN step 10).
  - Why deferred: deferral gate 2026-09-29 — outside the write feature; touches three Complete variants and their tests.
  - Intended future outcome: every Complete variant destroys the key then removes the directory, instead of leaving ciphertexts for the sweep.
  - Relevant files / subsystems: `session_store.complete_session`, `session.py` `complete*`, `docs/security/retention-schedule.md`.
  - Recommended next action: fold into the next custody change to `complete_session`.
  - Risk if deferred: minor: unreadable ciphertexts wait for the next sweep, as today.
  - Revisit by: the next custody change to `session_store.complete_session`
- **SEC-008** (A→B→A tab switching makes one extra Cliniko call while A's check runs).
  - Why deferred: deferral gate 2026-09-29 — the fix is bridge-internal (`VerificationLedger` keeping a current-connection, current-rev `Verified` answer whose run moved on; `_finish_task` reusing it before `_run`), and the `CallGate` that was to carry it became the smaller latch (D13).
  - Intended future outcome: A→B→A makes one note call, pinned by a test.
  - Relevant files / subsystems: `ui/bridge.py`, `encounter.VerificationLedger`.
  - Recommended next action: a small scoped task at the next bridge-ledger change.
  - Risk if deferred: minor: at most one extra call per such switch, spaced and cooled as today.
  - Revisit by: the next change to `ui/bridge.py`'s verification ledger
- **SEC-014's host half** (the native host also requiring the pipe server to be medium integrity or higher and not an AppContainer) — goes to the next Task 4.3 revision in the safeguards plan, not here. Risk if deferred: minor. Revisit by: the next Task 4.3 revision.
- **SIMP-010** (`hub.ts` message parsing) — Risk if deferred: minor. Revisit by: the next change to `hub.ts`'s message parsing.
- **Three-or-more-speaker labelling and diarization tuning** — unchanged; blocked on the shared recording set (practitioner-profile plan Task 6.1). Risk if deferred: ux-degradation. Revisit by: the shared recording set.

### Excluded — Revisit Only If Needed
- **`POST /treatment_notes` (a second note).** Why excluded: Cliniko creates the draft when the practitioner opens treatment notes; filling it gives exactly one note per consultation by construction (practitioner 2026-09-27). When to revisit: if the test write shows the auto-created draft cannot be filled. Files: `cliniko_client.py`.
- **A Chrome-side write state** (a `state` field, a panel line, a badge). Why excluded: practitioner 2026-09-29 — desktop only, no protocol bump; SIMP-009/011 stay deferred with the safeguards plan. When to revisit: the next protocol bump. Files: `protocol/fixtures/`, `ui/bridge.py`, `extension/src/panel*.ts`.
- **Appending or asking when the note already holds text.** Why excluded: practitioner 2026-09-29 — refuse by name; Copy stays (D8). When to revisit: if refusals are frequent in clinic.
- **Filling the "Presenting complaint" scaffold labels (Site / Chron / Sensory / …) individually.** Why excluded: practitioner 2026-09-29 — the scaffold is replaced whole; mapping into its labels is a template-config change. When to revisit: a practitioner-owned `template_profiles.json` change. Files: `config_defaults/template_profiles.json`, `note_config.py`.
- **Writing the note `title`, `draft`, booking or patient fields.** Why excluded: the body carries `content` only (D1). When to revisit: never for `draft`; the title only if Cliniko's default title proves wrong in clinic.
- **Starting a recording from the calendar; a trial account; a test-patient write guard; a separate network helper process; true overlap of consultations; automatic finalisation** — carried from the safeguards plan, unchanged (finalisation: never).

### Accepted Assumptions — Revalidate Later
- **Retries happen only inside the 24 h recovery window, and only on a practitioner action.** Why accepted: the offline contract and the retention bound already exist; a longer outage means the practitioner writes the note by hand or copies it. Risk if false: none for correctness. Trigger: an outage longer than 24 h in clinic.
- **The re-read note's `content` can be edited and sent back so untouched questions round-trip** (checkbox `answers` arrays, unknown question types, the attestation question). Why accepted: Cliniko's documented content shape is the same for GET and PATCH; sending the full re-read content is correct whether Cliniko replaces or merges. Risk if false: a changed shape on echo — the test write's second question confirms. Trigger: Task P.1.
- **The Cliniko `paragraph` sanitiser keeps `<p>` and `<br>`** (the only tags the renderer emits, D7). Risk if false: formatting collapses to one paragraph; content survives; the normalised comparison (D5) is unaffected. Trigger: the test write's fourth question.
- **An open Cliniko editor does not silently overwrite a PATCHed draft.** UNVERIFIED — the test write's fifth question answers it and Task 2.1 decides D6's completion mode on the answer. Risk if false with auto-complete: the draft is replaced with nothing local left. Trigger: Task P.1.
- **The GET→PATCH window is a named residue, not a closed defect.** Cliniko offers no conditional write; an edit the clinician saves in the web editor during the milliseconds between our note GET and our PATCH is reverted under a full body (not under a partial body, if Cliniko merges — P.1 question 2). Why accepted: no server-side precondition exists to enforce; the practitioner is told in the docs and the status line says to reload. Risk if it bites: one edit lost, visible on reload. Trigger: P.1 question 6's result; any Cliniko API change adding a version field.
- **`HTTPSTransport`'s failure classes cannot tell "not sent" from "sent, no answer"**, so every PATCH failure other than a clean 4xx is an unknown outcome (D5). Verified at `cliniko_client.py:326-339` (`_guarded` → `Unreachable`).
- **Facts, no longer assumptions:** the note author is the key's practitioner (P.1: the note's practitioner link equals the key user's record); the HTTP stack is stdlib `http.client` with the one `noqa: TID251` and no per-file carve-out; the auto-created draft is NOT content-empty (the scaffold).

### Key Design Decisions
- **Fill the open note by PATCH; drafts only by construction** — D1. Still applies to follow-up work: Yes.
- **Desktop-only write entry, live and adopted sessions, no protocol change** — D2 (practitioner 2026-09-29). Yes.
- **A fresh read of the note for every click, in three hops** — D3 (hardening 2026-09-29: the separate Phase A re-verification and the `CallGate` were replaced; the worker's note GET is the verification). Yes.
- **Typed text, template match and the scaffold; the body is always the full re-read content** — D4, the baseline finalised by Task 2.1. Yes.
- **Per-session `write.enc` (one document), attempt-before-send, per-question normalised digests, no automatic retry** — D5 (practitioner 2026-09-29 on the ledger; hardening 2026-09-29 on the document shape and comparison). Yes.
- **Confirmed write → `complete_after_write`: key, then directory, under one lock; automatic or after the clinician has seen the draft, decided by Task 2.1 on P.1's question 5** — D6 (practitioner 2026-09-29). Yes.
- **Rendering strips review apparatus; attestation never answered** — D7. Yes.
- **A note already holding text is refused; Copy stays** — D8 (practitioner 2026-09-29). Yes.
- **Write custody reuses `_custody_reservations`** — D9 (hardening 2026-09-29). Yes.
- **One `RateLimitLatch` for the 429 cooldown; spacing stays in the bridge** — D13 (hardening 2026-09-29). Yes.
- **Carried from the safeguards plan, unchanged:** D2 (protocol/`session_ref`), D4 (verification outcomes), D9 (client contract), D10 as AMENDED (the role is not a gate; exactly one active practitioner record decides — the scratch's "role is practitioner" wording is superseded), D11 (`encounter.enc`), D13 (page-script trust); keys only in Windows Credential Manager; the offline contract; the shipping gate stays a quality measurement; the practitioner's own accounts with no test-patient guard.

## Key Findings

### Files / Symbols Involved
All paths under `desktop/src/scribe_desktop/` unless stated; line numbers at HEAD `e509b56`.
- `cliniko_client.py` — `Transport.request(method, host, path, headers, max_body)` (:228, no body parameter); `_Connection.request` (:247); `HTTPSTransport.request` refuses any method but GET before connecting (:316) and reads a body only on 200 (:339; `_guarded` defined :348, every stage failure → `Unreachable`); `_interpret` (:492-507, 5xx → `Unreachable`, other → `UnexpectedStatus`); `ClinikoCall` GET methods (:456-476, no template GET); `ClinikoClient.call(read_key)` reads the key once per call (:417-436); constants `TIMEOUT_SECONDS` 15, `DEADLINE_SECONDS` 30, `MAX_BODY_BYTES` 1 MiB (:98-100). NEW here: `DraftContent`, `write_draft_note`, `get_treatment_note_template`, `ClinikoRejected(field_names)`.
- `encounter.py` — `EncounterContext` (:115-142, has `template_id` and `verified_at`; docstring "ids only"); `_note_state` / `_link_id` (:369-393, to become public `note_state` / `link_id`); `_check_note` (:535-576: GET note, then GET patient and booking for display; drops `content`); `verify_note_context` (:474); `NoteRefusal` (:274-287); `VerificationLedger` (:638-828); `reverification_request` (:831); `writeback_context` (:935-989, binds by `clinic_rev` only, never age); `VerifiedTarget` (:880); `write_encounter_record` / `read_encounter_record` (:224/:230). NEW here: `RateLimitLatch`.
- `draft_write.py` — NEW: the Qt-free write orchestration (D3), `render_targets` / `to_cliniko_answer`, `match_template`, `note_has_text`, `build_body`, the write record. Third pinned importer of the client (the pin changes in Task 3.2, where the import first exists).
- `session.py` — `complete()` (:882, needs QUEUED, no lease, no discard reservation), `complete_without_note` (:920), `complete_deleting_saved_note` (:958), `complete_recovered` (:1348), `discard_recovered` (:1358), `destroy_recovered_crypto` (:1367), `with_generation_custody` (:1385, lease-bound — the only scoped custody accessor today), `_forget_refs_locked` (:564), `register_session_ref` / `forget_session_ref` (:542/:558), `adopt_queued` (:1093), `begin_generation` (:1201), `begin_enrolment` (:1260), `custody_protected_ids` (:1327), `_reserve_custody_locked` / `_release_custody_locked` (:1414/:1420 — the counted per-id reservation already refused at :902, :944, :973, :1118, :1218, :1279, :1379, :826), `GenerationLease` (:326), `LEGAL_TRANSITIONS` QUEUED → {WRITTEN, DISCARDED, EXPIRED}. Tests: `desktop/tests/test_session_machine.py`, `test_live_session.py`.
- `session_store.py` — `complete_session` (:683-722, deletes only `key.dpapi`), `discard_session` (:725, key then `rmtree`), `write_note`/`read_note` (:783/:900), `write_encounter`/`read_encounter` (:866/:879, the AAD pattern `encounter:<id>`), `sweep_sessions` (:1007-1066; a directory without a key is skipped by the recovery listing at `ui/models.py:767` and removed as an orphan at :1049), `RECOVERY_WINDOW` 24 h (:138).
- `note.py` — `GeneratedNote` (:675-763, `template_profile_id` :683, `provider_name` `mock-…` for the mock provider :1795), `render_note` (:970-990, the only public renderer), private `_verbatim_block` (:915: `Title:` heading, `  - text  [label]` lines), `_clean_block` (:940: heading without colon, inline `[PREFILLED_MARK]`), `_prose_block` (:959: appends "[includes N lines …]"), `SECTION_TITLES` (:777), `PREFILLED_MARK` (:792).
- `note_config.py` — `TemplateProfile` (:315-368), `TemplateTarget{target_id, group, field_label, target_type}` (:295), `target_for` (:370, no callers), `bind_template_profile`, `unmapped_section_keys`; the `%LOCALAPPDATA%\ClinikoScribe\config` override (:12, :913 — tests must pass profiles explicitly); `config_defaults/template_profiles.json` (one profile `template-a`, 7 targets: 4 sections → `presenting-progress`, 5 → `assessment`, 4 → `management-advice`, 1 each → `diagnosis` / `treatment` / `response-to-treatment`, `informed-consent` attestation; `consent` intentionally unmapped).
- `ui/note.py` — button row (:569-574), `_copy_note` (:2103), `_copy_ready` (:2117-2138 — knows ratification and the copy flag only, not linkage or session id), `_apply_copy_binding` (:2141), the `TaskThread` style-job idiom with orphan disposal (:1760-1860), `is_busy`.
- `ui/main_window.py` — `prune_reminders` (:682; the ref registry deliberately holds refs of indexed retired Unreviewed sessions, `reconstruct_reminders` :692, `_index_released` :670), `open_unreviewed` (:703), `_on_review_requested` (:739-793, refuses on `note_screen.is_busy` :755), `_open_adopted` (:795-842, `_begin_checkout` at :824, `_transcript_source = "live"` :822), `_live_session_clinic` (:906-915, guards Remove only), `closeEvent` busy list (:939-985; the generic "Work in progress" branch fires first), `_on_recovered` (:1109), `_begin_checkout` (:1158), checkout re-verification `TaskThread` (:1182-1199, no gate), `is_reverifying` (:1260, the checkout task only), `recovered_writeback_target` (:1290, returns None for adopted), `live_writeback_target(reverification)` (:1301), `_on_generation_active` (:1390-1402, clears the Note tab), `_on_transcript_closed` (:1404-1432, clears the Note tab, lands on the session screen; the `outcome in ("completed","discarded")` branch at :1424).
- `ui/transcript.py` — `save_note` (:746-761, releases the lease), the Complete/Discard row (:258-278), `_update_controls`, `on_complete` closure writing its fixed text into the Transcript label and emitting `closed("completed")` (:833-854).
- `ui/bridge.py` — `RATE_LIMIT_COOLDOWN_SECONDS` (:160), `MIN_CALL_SPACING_SECONDS` (:161), `_cooldown_until` (:303, :821), the spacing QTimer served by `_spacing_served` (:724-757, :815-823), `_start` (:992 checks the session screen's `is_busy` only), `_open_review` (:921 resolves the ref), `CHROME_REFUSALS` fallback `failed`; the pause rule does nothing for a queued session (:970); live re-check only in recording/paused (:637-651).
- `ui/models.py` — `COPY_TO_CLINIKO_ENABLED = True` (:1121), `format_note_body` (:1226), `complete_block_reason` (:1513), the controller Protocol `SessionControllerLike` (:543-672), `reconstruct_reminder_entries` (:991-1016 — a saved-note session reappears as Unreviewed after a restart), `controls_for_state` (:471).
- `practitioner_profile.py` — `_SealedStore` / `_seal` / `_open` (:286-394): the non-session DPAPI pattern (NOT used by this plan after the ledger decision; listed so nobody re-invents it).
- `app.py` — `run_sweep` (:407), `sweep_protected_ids` (:337).
- `scripts/probe-cliniko.py` — read-only probe, key by `getpass` (:245), argv guard (:249-262); tests in `desktop/tests/test_probe_cliniko.py` (fake transport :154).
- Tests: `desktop/tests/test_cliniko_client.py` `TestGetOnly` (:156-211) and `TestConfinement` (:814-874); transport fakes at `encounter_fakes.py:112`, `test_cliniko_client.py:72/:371`, `test_clinics.py:84`, `test_probe_cliniko.py:154`, `test_ui_clinics.py:61`; `test_ui_encounter.py:224-469` (the two write-back entries); `test_integration_no_sockets.py`; `test_unreviewed_review.py`.
- Docs: `docs/security/threat-model.md`, `data-flow-map.md`, `retention-schedule.md`, `intended-use.md`, `incident-process.md`, `README.md`; `docs/testing/shipping-gate.md`; `docs/design-system.md`; `PLAN.md`; `AGENTS.md`.

### Codebase Integration Notes
- **Shared helpers this plan adds and every phase reuses:** `RateLimitLatch` (Task 1.3; bridge, checkout, write), `note_state` / `link_id` made public (Task 1.1), `render_section_lines` / `render_targets` (Task 3.1), the write record (Task 3.3), `with_write_custody` and the write reservation (Task 4.1).
- **No production caller reaches the write-back guard today.** `live_writeback_target` and `recovered_writeback_target` are called only by tests. `writeback_context` refuses in this order: `consent_unavailable`, `unlinked`, `consent_mismatch`, `clinic_gone`, `clinic_changed`, `not_verified` / `not_reverified`, `reverification_stale`, `reverification_refused`, `not_verified` (offline), `context_changed`. It must stay on the GUI thread (it reads `clinics.rev`). It needs only a `VerificationResult` whose request carries the current `clinic_rev` — the worker's note GET (hop 1) supplies that; no separate re-verification round trip is needed.
- **Entry points that can write:** a live QUEUED session with a saved note, and an adopted Unreviewed session (`adopt_queued` makes it live; `_open_adopted` sets `_transcript_source = "live"`, so both reach `live_writeback_target`). The crash-recovery checkout (`_on_recovered`) has no Note tab and cannot write; `recovered_writeback_target` stays unused and the docs say so. After a restart a saved-note session reappears as Unreviewed (`reconstruct_reminder_entries`), so a session with a `written` or `attempting` record is reachable again through "Open for review" — the record decides what the click does (D5).
- **No lease at write time.** Save releases the `GenerationLease` (`ui/transcript.py:740-741`); `_copy_ready`'s saved-note branch holds none, and `with_generation_custody` is the only scoped custody accessor. The write therefore needs its own reservation AND its own accessor `with_write_custody(reservation, action)` (D9). `begin_generation` cannot be reused: `_on_generation_active(True)` clears the Note tab.
- **Completion must go through the Transcript screen's completion path**, not `controller.complete` directly, or `_on_transcript_closed`'s cleanup (Note tab clear, checkout release, session refresh, reminders) never runs; the written variant emits `closed("written")`, which `_on_transcript_closed` treats as completed and then sets the success line on the landing (session) screen after `refresh()`.
- **The 429 cooldown is bridge-private state** (`_cooldown_until`), and the bridge exists only when the pipe starts (`app.py:423`); the checkout path runs its own `TaskThread` with no gate. Hence `RateLimitLatch` in `encounter.py` (Qt-free), owned by `MainWindow`, injected into the bridge in place of `_cooldown_until`, consulted by the checkout and the write. The bridge's 1 s spacing is for bursts of Chrome reports and stays where it is: a write is one click and its three requests run inside one worker unspaced, as the Start verification's three do today. A refused admission is a named, latched refusal, never a retry loop (design-system :209-212).
- **Rendering.** The private block helpers put the section title first and carry the review apparatus — verbatim `Title:` + `  - text  [label]`, clean's inline `[PREFILLED_MARK]`, prose's trailing "[includes N lines …]". A tag-free renderer therefore cannot reproduce `render_note` byte-for-byte on its own: `render_section_lines(note, section, style, *, apparatus)` reproduces today's lines with `apparatus=True` (title added by `render_note` per style) and gives Cliniko the bare lines with `apparatus=False` (verbatim renders as clean lines). Template A folds up to five sections into one target, so a per-target grouper gives each section a heading line only when several share a target. `format_note_body` stays the ONE path for Copy (`ui/note.py:104` invariant); Cliniko is a second consumer of the same per-section renderer.
- **Custody rules that bind the workers** (`docs/lessons.md` 2026-09-19): a worker does network I/O only; the write record, the reservation, `writeback_context` and every Qt call happen on the GUI thread between and after the hops, keyed by session id so a stale result applies to nothing; the reservation is taken BEFORE the first dispatch; `MainWindow.is_writing` is true from the click until the last handler finishes and is read by `closeEvent` (before its generic busy branch), `note_screen.is_busy`, the Transcript row and the bridge's pre-checks — a running `QThread` at close is the PR6 hazard.
- **Which profile:** resolved from `note.template_profile_id` through `bind_template_profile` against the current config; a missing profile, a target missing from the template, a duplicate question name, a type mismatch, or a section the profile leaves unmapped by oversight (`unmapped_section_keys`) all refuse `template_mismatch` — Copy still renders every section, so nothing is lost.
- **Repo gotchas that apply:** `urllib` bypasses the host pin (use the existing transport only); the venv `python.exe` is a launcher (tests never assert on a child's pid); a test must never depend on host state (inject `model_available`-style seams); a message that describes a deferred outcome names the control that commits it (the "attempting" row wording); transcribe peer rounds from the LAST header; slice codex passes by file group.
- **Sweep interplay:** `write.enc` lives in the session directory, so the existing sweep and orphan GC destroy it with the session; the ledger never protects a session from the sweep; `complete_after_write` removes the directory itself.

### External / API Findings
(Cliniko public API, docs.api.cliniko.com; P.1 findings from clinic 1, 2026-09-27; the test write (Task P.1) confirms the four open questions.)
- `PATCH /treatment_notes/{id}` accepts `content`, `draft`, `title`, `patient_id`, `booking_id`, `attendee_id`, `treatment_note_template_id`; this plan sends `content` ONLY. A final note is immutable; `DELETE` is an archive alias; there is no idempotency key.
- `content` = `sections[{name, description?, questions[{name, type ∈ text|paragraph|date|checkboxes|radiobuttons|bodycharts, answer | answers[{value, selected}]}]}]`. A `paragraph` answer is sanitised HTML (allowed: p, div, br, ul, ol, li, blockquote, h1, h2, b, i, u, a); this plan emits `<p>` and `<br>` only.
- `GET /treatment_note_templates/{id}`: sections/questions "like a note's but without answers" (exploration) — whether it carries the default answer text is UNKNOWN (test-write question 3).
- P.1 (clinic 1): a fresh note answers 200 with `draft: true`, `finalized_at: null`, patient/practitioner/booking/`treatment_note_template` links; its practitioner equals the key user's; an archived note answers NotFound; the auto-created draft holds the template's scaffold in "Presenting complaint" (Site - / Chron - / Sensory - / Agg - / Rel - / General … / Assoc ssx -).
- Limits: 200 requests/min per user; 429 carries `X-RateLimit-Reset`; 422 body `{"message":"Validation Failed","errors":{field: msg}}` (values may echo content — never logged; names only kept).
- A write is 3 requests — GET template + GET note (hop 1), PATCH (hop 2) — or 4 when the linked context carries no template id and hop 1 opens with a discovery note GET (D3). (The Start verification's `_check_note` makes 2–3 — note, patient, booking — because it also fetches display names; the write's note GET skips those.)
- HTTP status classes for the PATCH (D5), decided on the STATUS LINE before the body is read: 200 → `written` (a body that then fails to read or parse leaves it `written`, PR-MED-005); 401/403 → `key_rejected`; 404 → `note_not_found`; 422 → `cliniko_rejected(fixed categories)`; any other 4xx except 429 → `cliniko_rejected` (no names); 429, 5xx, timeout, connection loss, TLS failure, no status line → `unknown`.
- Cliniko documents NO conditional write (no ETag / `If-Match` / version field on treatment notes): an edit saved in the web editor between our note GET and our PATCH is reverted by a full-content body — the D4 body decision and residue (PR-HIGH-002); P.1 question 6 exercises exactly that ordering.

## Planned Workflow Summary

### Flow 1 — Write a ratified note into the open Cliniko draft
- The clinician finishes review and presses Save. "Write draft to Cliniko" enables (same rule as Copy, plus linked and not mock). One click, GUI thread: the lock refusal, the latch (`cooling` → named refusal), the write reservation, `is_writing = True`. Hop 1 (worker, one `ClinikoCall`): GET the note — this IS the click's verification (`note_state` invariants; patient, draft/final/archived, practitioner) and yields a `VerificationResult` plus the raw `content` — then GET the template. GUI thread: `writeback_context` over that result → `VerifiedTarget` or a named refusal; reconcile against the write record; `note_has_text`; `match_template`; `build_body`; the `attempting` state fsynced through `with_write_custody`. Hop 2 (worker): the PATCH only. GUI thread: record the outcome, release the reservation. On `written`, D6's mode applies: automatic completion through the Transcript screen's written-completion closure, or the Note tab stays with Copy and the line telling the clinician to reload the page and press Complete when they can see it. Any refusal is a named status line on the Note tab with Copy still available.

### Flow 2 — Retry after an unknown or interrupted outcome
- A 429, 5xx, timeout, connection loss during the PATCH — or a crash that leaves the record at `attempting` — leaves the session QUEUED with the record not `written`. The next click (live, or after "Open for review") reconciles first, before any PATCH: re-read the note; if every targeted answer's normalised digest equals the record's, the outcome is `written` with no second PATCH and D6 applies; if the targeted answers are still at baseline, the write proceeds as attempt n+1; otherwise the write is refused with the "an earlier write may have reached Cliniko — check the note before copying" line (never a plain `note_has_text`). A record already `written` completes without any network call. Nothing retries without a click; the 24 h window expires the session as today.

### Flow 3 — Unreviewed recording written later
- "Open for review" adopts the recording as the live QUEUED session and runs the checkout re-verification (display only). The clinician reviews, saves and clicks Write; Flow 1 applies unchanged — the click's own note GET is its verification, never the checkout's result.

### Flow 4 — The practitioner's test write (once per clinic)
- With a note open on a DUMMY patient, `probe-cliniko.py --test-write` re-reads the note, refuses unless it is the key user's own unfinalised draft, asks for the dummy patient's surname and the note id's last four digits (compared, never printed), shows what it will write and waits for a typed `yes`, then writes the adversarial marker (`Clinic Scribe test write - delete this text: a < b & "c" 'd' é`, a second line, an empty line) into one rich-text and one plain-text question through `write_draft_note`, re-reads and reports per question equal / sanitised / rejected and whether every untargeted question came back unchanged (questions 1, 4), prints the template GET's question structure and whether each carries default text (question 3), then pauses: "Now save or edit the note in the open Cliniko editor, then press Enter" — re-reads and reports whether the marker survived (question 5) — then runs the window pass: GET the note, pause ("edit and save a DIFFERENT question AND the targeted question in the editor, then press Enter"), PATCH the earlier full body, re-read and report which of the two edits survived (question 6 — the targeted edit is expected to be lost in every mode), and the same pass with a partial body carrying only the targeted question, reporting whether the untargeted edit and every other question survived (question 2: merge vs replace) — and finally restores: re-read, and PATCH the original content back only if the markers are the only difference; on any failure print `MARKER LEFT - delete it by hand in Cliniko` and exit non-zero. A second, separately confirmed leg (`--test-write-final`) PATCHes the marker into a note the practitioner has FINALISED on the dummy patient and prints the status and the 422 categories; a 200 there is printed as an alarm with the same instruction. The Done note answers the six questions and Task 2.1 decides.

## Design Decisions
- **D1 — Fill the open note by `PATCH /treatment_notes/<id>`; drafts only by construction.** The transport accepts exactly two request shapes before connecting: GET with no body, or PATCH with a body to a path matching `^/v1/treatment_notes/[1-9][0-9]{0,18}$`; anything else raises before a connection exists. The only production caller is `ClinikoCall.write_draft_note(note_id, content: DraftContent)`, whose body is serialised from a typed model holding `content` alone — there is no `draft`, `title` or id field to set, so `draft: false` cannot be expressed; a source test pins that the literal `PATCH` appears exactly once in the module (the transport allow-list) and that no other key reaches the serialised body. Alternatives rejected: POST of a second note (duplicates by construction, practitioner 2026-09-27); an allow-list of call forms (`docs/lessons.md` 2026-08-10: guard the surface, not the spellings).
- **D2 — Desktop-only entry; live and adopted sessions; no protocol change.** The button lives on the Note tab beside Copy. `MainWindow` pushes a `WriteBinding(session_id, linked)` into the Note tab on `begin_review` / `show_saved_note` (linked = `session.encounter_context is not None`) and a `set_write_in_flight(bool)`; the tab's `_write_ready` = `_copy_ready()` AND `binding.linked` AND not in flight AND no style job AND `provider_name` not `mock-…` (D10) AND the write record does not read `written` (a `written` record in seen mode shows `written_seen` instead — D5; `unknown` / `attempting` keep Write enabled because the click reconciles); the click emits `write_requested(session_id)` to ONE slot, `MainWindow._on_write_requested`, which owns every write job. The Chrome panel, `state` and protocol v2 are untouched, so SIMP-009/011 stay deferred; the bridge's Start / Discard / open-for-review pre-checks map a write in flight to the EXISTING codes (`session_active` / `busy`, text only). The crash-recovery checkout cannot write (no Note tab); `recovered_writeback_target` stays unused and the docs say so. Alternatives rejected: a panel line (a protocol bump); Write replacing Save (an outage would block the local save).
- **D3 — A fresh read for every click, in three hops (template GET, note GET, PATCH), one clinic key read, behind the latch.** GUI thread first: `_lock_refusal()` (a click queued behind a session lock is refused, the PR-MED-300 rule), `latch.cooling(clinic_id, now)` → `rate_limited(s)` refusal, `reserve_write`, `is_writing = True`, THEN dispatch. Hop 1 (worker, ONE `ClinikoCall`, the key read once at its start): the template id is the context's `template_id`, or — when the context has none (an offline-started session, `_offline_context` at `encounter.py:450`; PR-MED-012) — a DISCOVERY `GET /treatment_notes/<id>` supplies it; then `GET /treatment_note_templates/<template_id>`; then `verify_note_for_write(request)` — the FINAL `GET /treatment_notes/<id>`, applying `note_state` (patient link = context's, draft and unfinalised, not archived, practitioner = clinic's) and returning a `VerificationResult` tagged with the request's `clinic_rev` PLUS the raw `content`; the final note's `treatment_note_template` link MUST equal the fetched template's id, else `template_mismatch` (fail closed — the template changed under us); no patient or booking GET (the final note read sits as close to the PATCH as the design allows — D4's window residue). GUI thread: `writeback_context(subject, clinics)` over that result (a stored checkout result or the bridge's reconnect re-check is never accepted — MED-012/SEC-018's freshness gap closes by construction of the click; `writeback_context` gains no age bound); reconcile (D5); `note_has_text` (D4); `match_template`; `build_body`; `attempting` written through `with_write_custody`. Hop 2 (worker, the same key): the PATCH only. GUI thread: classify by the HTTP answer ONLY (a 200 is never relabelled), `record_429` on a 429 from either hop, record, release. Alternatives rejected: a separate re-verification round trip before the worker (double reads, and its patient/booking GETs); a `CallGate` with call spacing (hop 2 follows hop 1 by under a second; the bridge's spacing is timer-served, not clock-compared).
- **D4 — Typed text, the template match, the scaffold, the body.** The write is refused (`note_has_text`) when any answer this profile targets is non-empty AND differs from its known "untyped" default; the default source is decided by Task 2.1 — Option A: the default answer text from the template GET (if P.1 question 3 shows it carries one — preferred); Option C: a per-clinic `template_defaults.json` under `%LOCALAPPDATA%\ClinikoScribe\config`, keyed by the clinic's HOST (`<subdomain>.<shard>.cliniko.com`, as the address bar and the Clinics tab show it — unique by construction, since the registry refuses a duplicate subdomain, whereas display names are not checked for duplicates, PR-MED-021) and the Cliniko template's NAME (as Cliniko shows it; the template GET's `name` field is matched at write time — PR-LOW-020: the redacted probe prints no id, so ids cannot be the keys), holding, nested by section name then question name (never a joined key — PR-MED-024), the scaffold text the practitioner TRANSCRIBES from a pristine note as Cliniko's own editor shows it during P.1 (PR-MED-013: the probe prints structure only and never answer text, so it reports only WHICH questions carry a default; non-clinical prompt text only; loaded fail-closed like the other config files; a question with no entry has no default, so any non-empty answer is typed). A Start-time snapshot of the note's answers is NOT a baseline (PR-HIGH-001: text typed before Start, or a previous recording's write, would be snapshotted as "untyped" and replaced). Comparison is ALWAYS normalised and QUESTION-TYPE-AWARE (PR-HIGH-009): an API `paragraph` answer is an HTML REPRESENTATION and is converted to visible text exactly ONCE (`html_to_visible`: `<p>`, `<div>`, `<br>`, `<li>` and blockquote boundaries become newlines so adjacent tokens never concatenate, then entities are unescaped); a `text` answer and an Option C transcription are ALREADY visible text and are never HTML-decoded (PR-MED-016: a scaffold whose visible text carries literal entity notation must compare equal to its transcription and different from an edit that replaced the notation); only then does the shared `normalise_visible` (whitespace collapse + NFC) apply — the same two-step `normalise_answer(value, representation)` serves the default comparison and the reconcile digests. The template match is name-based on (section index, section name, question name) between the profile's `group`/`field_label` and the note's own template; the profile is `bind_template_profile(note.template_profile_id)` against the current config; a missing profile, a missing target, a duplicate name, a type mismatch or an oversight-unmapped section refuses `template_mismatch`. **The body** is decided by Task 2.1 on P.1 question 2: `partial` — only the targeted sections/questions — IF Cliniko MERGES partial `content` (preferred: an UNTARGETED answer the clinician saves between our GET and our PATCH cannot be reverted); otherwise `full` — the re-read `content` with only the targeted answers replaced (checkbox `answers` arrays, unknown types and the attestation question round-trip byte-equal). In BOTH modes the GET→PATCH window is a named residue for the TARGETED answers (PR-HIGH-002, PR-MED-011): Cliniko documents no conditional write — no ETag / If-Match — so an edit the clinician saves to a targeted question between our note GET and our PATCH is replaced by ours, whatever the body shape; the window is kept to milliseconds by placing the note GET LAST in hop 1, the status line tells the clinician to reload, and the docs state it. `build_body` does NFC, `json.dumps(ensure_ascii=False)` and a strict UTF-8 encode BEFORE the attempt row, so a lone surrogate refuses (`answer_unreadable`) with nothing sent. A note whose rendering yields NO writable answer — an empty saved note, or one whose only content sits in intentionally unmapped sections — refuses `nothing_to_write` before any attempt is recorded or any PATCH dispatched (PR-LOW-025); the record's `digests` are therefore never empty, and reconcile requires a non-empty recorded target set before it can establish `written`. The scaffold is one default answer and is replaced whole. Alternatives rejected: a stored Cliniko template id per clinic (config churn); filling the scaffold's labels (practitioner 2026-09-29); a Start-time snapshot baseline (PR-HIGH-001); trusting merge semantics without P.1's answer.
- **D5 — The per-session write record `write.enc`; attempt before send; per-question digests; bound to the saved note; no automatic retry.** `write.enc` is written beside `note.enc` under the session key with AAD `write:<session_id>`: ONE document `{attempt: n, started_at, target ids, note_identity: sha256 of the saved note.enc plaintext, digests: {question_key: sha256 of the normalised answer text}, body_sha256, outcome ∈ attempting|written|refused|unknown, refusal?, finished_at?}`, never note text, rewritten atomically with fsync at every transition; `attempting` is on disk before hop 2 is dispatched. Classes: see External / API Findings — a 200 status line is `written` even when its response body then fails to read or parse (PR-MED-005: the status is classified before the body is touched; the parsed note is optional). Reconcile on the next click, BEFORE any PATCH, for any record not `written`: re-read; every targeted answer's normalised digest equals `digests` AND `digests` is non-empty → `written` (no second PATCH, D6 applies; an empty target set never establishes a write — PR-LOW-025); every targeted answer still at its default → attempt n+1; otherwise → `write_uncertain` ("an earlier write may have reached Cliniko — check the note before copying"), never a bare `note_has_text`. A trailing `attempting` (crash before the outcome was recorded) is treated exactly as `unknown`. While the record holds an `attempting` or `unknown` attempt, every refusal the next click meets BEFORE reconcile can run — a failed or refused note read, the latch's cooldown, a gone or changed clinic, a rejected key, a note since finalised — is shown WITH the `write_uncertain` warning and never as a bare Copy suggestion, on a live session and after a reopen alike (PR-MED-017). **Once any attempt exists, the saved note is frozen for that session** (PR-HIGH-003): "Cancel review and regenerate", "Regenerate (replaces the saved note)" and a second Save are refused by name (`write_pending`) — the escape is Copy, Complete (per D6) or Discard — and `complete_after_write` and reconcile both require the record's `note_identity` to equal the saved note's; a mismatch (only possible through a path the refusal missed) is `write_uncertain` and never completes. A record already `written` is handled by completion mode (PR-MED-010): in auto mode (or on a reopen after a failed automatic completion) it completes without any network call, even if the note has since been finalised; in seen mode Write is DISABLED while the record reads `written` (the tab shows `written_seen`), a reopened written session shows the same line, and ONLY Complete consumes custody — nothing completes on a Write click. The record dies with the session; a corrupt or undecryptable record refuses the write and is shown as its OWN uncertainty line (`record_unreadable`: the earlier outcome cannot be checked — inspect the note in Cliniko before copying), never as a Cliniko rejection, since a local read failure says nothing about the chart (PR-MED-018). Alternatives rejected: a DPAPI 7-day ledger (an audit record — Phase 6; practitioner reversed 2026-09-29); a list of rows (nothing reads history); a whole-body digest for reconcile (any drift in untargeted questions — a ticked attestation, a normalised checkbox — would read as foreign text and block the practitioner for good); allowing regeneration after an attempt (the old record would complete and destroy a note that never reached Cliniko).
- **D6 — A confirmed write completes the session: `complete_after_write(reservation)`.** Guards as `complete()` (QUEUED, no lease) plus, under the controller lock: the reservation is held and is this session's, the record reads `written`, and the record's `note_identity` equals the saved note's (D5); then under the SAME lock hold: fsync + decrypt-verify as `complete_session`, delete `key.dpapi`, zero the in-memory key, `rmtree` best-effort (as `discard_session` after the key), `_forget_refs_locked`, release the reservation — no release-then-complete gap. Reservation lifetime (PR-MED-004): in auto mode the result handler records `written` and calls `complete_written` with the reservation STILL HELD, and completion consumes it; on a completion failure the handler releases it, the key and the record stay, and the next Complete re-acquires. In seen mode the handler releases after recording; the Complete button re-acquires through `reserve_write` and `complete_after_write` revalidates the record under the lock; a reopened (Unreviewed → adopted) already-written session takes the same path. Reached through the Transcript screen's `complete_written(on_complete_written)` closure (mirrors `on_complete`: try / clear / emit `closed("written")`; on failure the text keeps QUEUED and the key), so `_on_transcript_closed` runs its cleanup and then sets `WRITE_LINES["written_done"]` (the terminal entry; PR-LOW-014) on the session screen after `refresh()`. **Completion mode is decided by Task 2.1 on P.1's question 5:** (auto) `written` → `complete_written` at once; (seen) `written` → the Note tab stays with Copy and the line "Draft written to Cliniko. Reload the note page in Chrome; press Complete once you can see it there." and the existing Complete button, when the record reads `written`, runs `complete_after_write` instead of `complete`. A crash after the key is deleted leaves a keyless directory the recovery list skips and the sweep removes as an orphan. After completion the only copy of the note is in Cliniko — stated in the docs. Manual Complete on a non-written session is unchanged (deferred parity item). Alternatives rejected: a flag on `complete()`; calling the controller directly (skips the screen cleanup); auto-complete regardless of question 5 (an editor autosave could replace the draft with nothing local left).
- **D7 — Rendering for Cliniko.** `note.render_section_lines(note, section, style, *, apparatus: bool) -> list[str]`: with `apparatus=True` today's lines minus the title (verbatim bullets and `[label]` tags, clean's inline `[PREFILLED_MARK]`, prose's trailing "[includes N lines …]"), and `render_note` = the style's title line + those lines, byte-identical to today for all four styles (pinned by fixture digests, the prose leg with `style_renderings` present); with `apparatus=False` the bare body lines — verbatim rendered as clean lines, no bullets, tags or marks; prose falls back to clean per section as today. The private blocks fold into it (one path, `ui/note.py:104`). `draft_write.render_targets(note, profile, style) -> {target_id: (TemplateTarget, lines)}` groups by `target_for`, adds a `SECTION_TITLES` heading line only when several sections share a target, and never yields an `attestation_checkbox` target. `to_cliniko_answer(lines, target_type)`: `rich_text` → one `<p>` per line with `html.escape(text, quote=True)` (no other tag), `plain_text` → lines joined by `\n`; pure functions with their own tests (`a<b&c` → `a&lt;b&amp;c`, non-ASCII kept). Alternatives rejected: calling the private blocks per section (repeated titles, marks in the chart).
- **D8 — A note that already holds text is refused; Copy stays.** Because the re-read check (D4) refuses non-baseline text and the write record (D5) recognises only THIS session's own digests, a second recording on a note the app already filled is refused with `note_has_text`; the clinician pastes it. Alternatives rejected: append (a merge rule per question); ask (replacing text typed in Cliniko).
- **D9 — Write custody reuses the existing reservation.** `SessionController.reserve_write(session_id) -> WriteReservation` = `_reserve_custody_locked(id)` plus a `_writing_id` marker, taken on the GUI thread BEFORE the first dispatch and released only by the result handler or `complete_after_write`, both under the lock. Refused while held (the exhaustive set of custody-mutating public methods at HEAD): already through `_custody_reservations` — `complete` :902, `complete_without_note` :944, `complete_deleting_saved_note` :973, `adopt_queued` :1118, `begin_generation` :1218, `begin_enrolment` :1279, `destroy_recovered_crypto` :1379, `transcribe` :826; newly checking `_writing_id` — `discard`, `start` (both deliberately admit a concurrent discard today), `complete_after_write` for another id; newly checking the write RECORD (D5, `write_pending`, refused whenever any attempt exists, not only in flight) — `begin_generation` (Regenerate / "Cancel review and regenerate") and `save_note` (a second Save); state-guarded and unaffected — `pause`, `resume`, `finish`, `mark_queued`; other-id and unaffected — `complete_recovered`, `discard_recovered`, `register_session_ref` / `forget_session_ref`. The UI maps the existing "a discard is completing" refusals of those methods to `write_in_flight`; `MainWindow._on_review_requested` (the "Open for review" path; not a controller method) refuses on `is_writing`. Writing and Recovery's "Resume processing" are mutually exclusive in BOTH arrival orders (PR-MED-023): the Write click is refused (`recovery_busy`) while `recovery_screen.is_busy`, and the Recovery screen is blocked while `is_writing` through the existing `set_generation_blocked` pattern (`main_window.py:922`, `:1394`), including a queued click — so a recovered session's result can never clear the writing session's Note tab, replace its transcript view or swap its completion callback; a test pins the transcript source, the completion callback and the saved-note view bound to the writing session until its last handler finishes. `with_write_custody(reservation, action)` mirrors `with_generation_custody` (checks the reservation identity and QUEUED) and is the ONLY accessor the write uses for `write.enc`. `custody_protected_ids` already covers the live non-terminal session; the reservation adds nothing there. While a write is in flight, the Clinics tab refuses Replace key and Remove for that clinic (`_live_session_clinic` extended from Remove to both), so the key read once in hop 1 stays the clinic's key. `MainWindow.is_writing` (true from the click until the last handler finishes) is read by `closeEvent` — the write-specific line BEFORE the generic busy branch — `note_screen.is_busy`, the Transcript row's `_update_controls`, and the bridge's pre-checks. Alternatives rejected: a parallel reservation mechanism (re-opens the split-read composition race closed at round 31 of Phase 3A); the mid-flight `clinic_rev → unknown` rule (a worker cannot see the rev; a real 200 must never be relabelled).
- **D10 — Mock notes never write.** `_write_ready` and `draft_write` both refuse (`mock_note`) when `GeneratedNote.provider_name` starts with `mock-`, pinned by a test that fails if either gate is removed; the shipping-gate's scored mock sessions therefore cannot reach a chart.
- **D11 — The security docs are rewritten as ONE class in one task, last**, driven by a grep checklist ("GET only", "read-only", "reads only", "writes nothing", "two callers", "only … import", "create", "creation", "never at startup or idle", "Complete, Discard or expiry", "no evidence outlives") across the eight groups listed in Task 6.1; PLAN.md's "create" becomes "fill"; the threat model gains a review trigger "the first write of a new session type"; `incident-process.md` gains "a draft written into the wrong note or patient" (response: the practitioner deletes/archives it in Cliniko; the write record and Cliniko's own history are the evidence). The 422 path: the response is reduced to FIXED categories before any exception exists — each top-level `errors` key is mapped to Cliniko's documented treatment-note field names (`content`, `title`, `patient_id`, `booking_id`, `attendee_id`, `treatment_note_template_id`, `draft`) or to `other`; nothing else from the body survives (PR-MED-006: an identifier-shaped key can itself carry data, so a shape filter is not a residue boundary and the docs never call this surface residue-free); the reduced tuple is carried out of the `except` block and the named error is raised OUTSIDE it, the client's existing pattern (`cliniko_client.py:349-350`), so neither `__cause__` nor `__context__` holds the parser exception or the body (PR-MED-007; `raise … from None` alone would keep `__context__`); the tests assert both attributes are `None` for a malformed 422 and that a 422 whose keys AND values carry a sentinel note phrase (including an identifier-shaped key) leaves no trace in any log record, exception text or status line.
- **D12 — Re-deferred and excluded items** are as recorded in the Planning Extraction Summary; nothing else from the safeguards plan's H2a/H3a lists moves into this plan.
- **D13 — One `RateLimitLatch` for the 429 cooldown; spacing stays in the bridge.** `encounter.RateLimitLatch(clock)`: `cooling(clinic_id, now) -> float | None` (seconds left) and `record_429(clinic_id, now)`; `RATE_LIMIT_COOLDOWN_SECONDS` (60) moves beside it. `MainWindow` owns it and hands the bridge its clock; the bridge replaces `_cooldown_until` with the latch (its queue, `MIN_CALL_SPACING_SECONDS` and the QTimer are untouched; `test_ui_bridge.py::TestRateLimit` keeps passing through the injected latch); the checkout re-verification consults it, shows the existing rate-limited line (re-dispatched when the row is reopened, as today) AND records its own 429 into the latch before dispatching waiting work, whether or not its display result is stale (PR-LOW-008: the checkout is the third producer); the write consults it once per click and records a 429 from either hop. Alternatives rejected: a `CallGate` carrying spacing (see D3); leaving the cooldown bridge-private (the bridge may not exist; a 429 seen by one path must stop the others).

## Schema / Data Changes
- **New session file `write.enc`** (D5): AES-GCM under the session key, AAD `write:<session_id>`, ONE JSON document as in D5; written by `session_store.write_write_record` / read by `read_write_record` following the `encounter.enc` pattern, reached only through `with_write_custody`; destroyed with the session. Retention row added (Task 6.1).
- **`template_defaults.json`** ONLY if Task 2.1 chooses Option C (D4): a per-clinic config file under `%LOCALAPPDATA%\ClinikoScribe\config`, `{"<clinic host>": {"<template name>": {"<section name>": {"<question name>": "<scaffold text>"}}}}` — section and question names NESTED as separate keys, never joined (PR-MED-024: both shipped labels already contain slashes — `Treatment/Management`, `Management/Advice` — so a flattened key could alias two questions); both outer keys human-visible and the host unique (`ClinicRecord.host`, matched exactly; Cliniko's template name, matched against the fetched template's `name`), a missing key meaning no defaults — non-clinical prompt text only, loaded fail-closed like `template_profiles.json`, transcribed by the practitioner from the pristine note as Cliniko's editor shows it (the probe names which questions carry a default; it never prints the text; the app never writes the file). No `encounter.enc` change in either option.
- **Request body model** `cliniko_client.DraftContent` (pydantic, `extra="forbid"` at the top level, one field `content: list[Section]` loosely typed so unknown question types and `answers` arrays round-trip): serialised as `{"content": …}` only.
- No change to `clinics.json`, `template_profiles.json`, protocol v2 or `meta.json`.

## Config / Environment / Deployment Impact
- No new dependency, environment variable, model or install step. `config_defaults/template_profiles.json` is unchanged (the match is by name at write time, D4).
- `TestConfinement`'s importer pin gains `draft_write.py` (Task 3.2); the security docs name three importers.
- `scripts/probe-cliniko.py` gains `--test-write` and `--test-write-final` modes; its docstring stops saying "READ-ONLY" (Task 1.2 + 6.1). The practitioner runs it from a normal terminal at the repo root, never an agent shell (`docs/lessons.md` MSIX); it needs no Qt, Credential Manager or `%LOCALAPPDATA%`.
- Release risk: the first real write into a chart. Mitigations by construction: drafts only (D1), the fresh check (D3), the typed-text refusal (D4), the practitioner finalises every note, the mock gate (D10).
- The extension needs no rebuild; `register-native-host.py` needs no re-run.

## Critical Constraints
1. **Drafts only, by construction** (D1): no code path can send `draft`, a POST, or a PATCH to any path but the note's; pinned by the transport test, the source test and the body-model test.
2. **The write and its reconcile start only from the Note tab's button slot; a retry is a click** — never at startup, on a timer, from the sweep, on clinics-changed or on reconnect. The existing READ contract is retained unchanged (PR-LOW-015): a new Chrome link connection may verify a LINKED live recording once, and the bridge's spacing timer may dispatch a check that was already requested by a report; neither is autonomous polling, and the app still makes no call at startup or idle. Pinned by Task 5.3.
3. **A write needs a note read made for that click** (D3); the checkout's or the bridge's result is never accepted; `writeback_context` runs on the GUI thread over hop 1's result.
4. **A note holding non-default text, as observed by the click's own note read, is never overwritten** (D4/D8): refusal by name, Copy stays. An edit saved to a targeted question in the milliseconds between that read and the PATCH is the named residue (D4), in both body modes.
5. **The `attempting` state is on disk before hop 2 is dispatched** (D5); every 429/5xx/transport outcome and every trailing `attempting` is `unknown` and reconciled before another PATCH; a 200 is never relabelled.
6. **Untargeted questions round-trip unchanged** (D4); the attestation question is never answered (D7).
7. **The workers do network I/O only** (D3/D9): the record, the reservation, `writeback_context` and every Qt call happen on the GUI thread between and after the hops, keyed by session id; the reservation precedes the first dispatch; a running worker refuses close.
8. **The key survives a failed completion** (D6): `complete_after_write` destroys the key only after fsync + decrypt-verify, and only when the record reads `written` under the lock.
9. **No log line, exception text or status line carries the key, an id value, a URL, an answer or a 422 error VALUE** (client contract D9 of the safeguards plan, extended to the write).
10. **Mock notes and unlinked (desktop-started) sessions never write** (D2, D10).
11. **Every copy of note text to Cliniko goes through the ONE per-section renderer** shared with `format_note_body` (D7).
12. **The docs claim only what the structure enforces** (`docs/lessons.md` 2026-08-14) — the rewrite is a class, and it names the residue: Cliniko's sanitiser may change formatting; after a confirmed write the only copy is in Cliniko.

## Validation / Verification
Baseline dry-run 2026-09-29 at `e509b56` (read-only): `ruff check .` — All checks passed; `mypy` — no issues in 50 source files; `pytest --collect-only -q` — 4187 tests collected. Every phase leaves ruff clean, mypy clean (file count grows by the new modules) and the suite green; the loop's `verify=composer` runs them (`docs/lessons.md` 2026-08-13).
- **Client (Phase 1):** `TestMethods` (renamed from `TestGetOnly`): GET without body and PATCH-with-body to `^/v1/treatment_notes/[1-9][0-9]{0,18}$` connect; POST/PUT/DELETE/HEAD/lower-case `get`, PATCH without body, PATCH to any other path, GET with body all raise before `connection_factory` is called; `vars(ClinikoCall)` exposes exactly the GET set + `get_treatment_note_template` + `write_draft_note`; the source names `"PATCH"` exactly once; `DraftContent` has exactly one field and the serialised body exactly one top-level key `content`; a PATCH 200 whose body is malformed, oversize or stalled is still `written` (PR-MED-005); a 422 body is read only for a PATCH, bounded to `MAX_BODY_BYTES`, reduced to D11's fixed categories, raised outside the handler with `__cause__` and `__context__` both `None`, and a 422 whose keys (including an identifier-shaped one) and values both carry a sentinel phrase leaves no trace in any log record (the tripwire), exception text or status line; a stalled or oversize 422 body → `cliniko_rejected` with no categories. `test_exactly_one_tid251_noqa` unchanged.
- **Latch (Task 1.3):** `test_ui_bridge.py::TestRateLimit` keeps passing through the injected latch; a 429 recorded by the bridge makes `cooling` non-None for the checkout and the write for 60 s and None after; a 429 from a write hop cools the bridge; a 429 from the checkout cools the bridge and the write, including when the checkout's result is stale (PR-LOW-008).
- **Probe (Task 1.2):** fake-transport tests for every refusal (final, archived, wrong patient, wrong practitioner, wrong surname, wrong digits, no `yes`), the marker body, the restore-only-if-marker-is-the-only-change rule, the `MARKER LEFT` non-zero exit, the finalised-leg alarm, and structure-only output (no id value, name, URL, answer text or key in stdout).
- **Rendering (Phase 3):** `render_note` byte-identical to the pinned digests of the ten `scripts/measure-prose-fixtures.py` fixtures in ALL FOUR styles (the prose leg with `style_renderings`), captured BEFORE `note.py` is touched; `render_section_lines(apparatus=False)` carries no title, mark, tag or "[includes" text; `render_targets` never yields `informed-consent`; a 5-section target gets 5 heading lines and a 1-section target none; `to_cliniko_answer`: `a<b&c` → `<p>a&lt;b&amp;c</p>`, `"` escaped, non-ASCII kept, only `<p>`/`<br>` emitted.
- **Match, typed text, body (Task 3.2):** fixtures shaped from P.1's printed structure: the baseline note passes; a changed targeted answer → `note_has_text`; an untargeted checkbox `answers` array round-trips byte-equal in the body; duplicate question name, missing target, type mismatch, missing profile, oversight-unmapped section → `template_mismatch`; Option C defaults are looked up by the clinic's host + the fetched template's `name`, and a missing key means no defaults (a non-empty answer is then typed); two clinics with the same display name and equally named templates never share a default (PR-MED-021); two (section, question) pairs whose slash-joined forms coincide keep distinct defaults (PR-MED-024); an extra template question preserved; a lone surrogate → `answer_unreadable` with no body built; an empty saved note, an intentionally-unmapped-only note and an `unknown` record with empty digests each refuse `nothing_to_write` / never reconcile to `written` and never trigger completion; the digests are over type-aware normalised text (a `<p>`-wrapped, entity-escaped, re-spaced echo of a PARAGRAPH answer digests equal; a `text` answer holding a literal `<b>` or `&amp;` digests DIFFERENT from one without, and a plain-text default differing only by such literals is typed; `<p>a</p><p>b</p>` and `a<br>b` normalise to `a
b`, never `ab`; an untouched paragraph scaffold whose visible text carries literal entity notation compares equal to its Option C transcription, and the clinician's edit replacing the notation with the character compares different). Profiles are passed explicitly; a test fails if the default `%LOCALAPPDATA%` loader runs under pytest.
- **Orchestration (Task 3.4):** with a fake `ClinikoCall` recording the request sequence: hop 1 = GET template, GET note (no patient/booking GET), or discovery GET note, GET template, GET note when the context has no template id; a final note whose template link differs from the fetched template → `template_mismatch`, no PATCH; reconcile before any PATCH for every non-`written` record; one test per outcome class and per refusal name; a trailing `attempting` behaves as `unknown`; a `written` record makes no request; no Qt import in `draft_write.py` (pinned).
- **Custody (Phase 4):** every method in D9's refused set is refused by name while a reservation is held and allowed after release; `discard`/`start` refuse on `_writing_id`; `with_write_custody` refuses a foreign or released reservation; `complete_after_write` refuses without a held reservation, without a `written` record, and when the record's `note_identity` differs from the saved note's; keeps the key when fsync/verify fails; removes the directory and forgets refs on success; releases under the same lock; `begin_generation` and `save_note` refuse `write_pending` after any attempt (`attempting`, `written`, `refused`, `unknown`) and allow with no record; the record round-trips and a corrupt record refuses; `prune_reminders` still forgets a sweep-expired session's reminder AND ref; `prune_session_refs` keeps a live session's and a still-indexed Unreviewed session's ref and drops an unlinked/failed one (SIMP-016, PR-LOW-022); Replace key / Remove refused for the writing clinic.
- **UI (Phase 5):** `_write_ready` false without Save, unlinked, mock, during a render or write; the click applies the lock refusal and the latch first, takes the reservation before dispatch; hop 1 then hop 2 with the expected body; on 200 in auto mode `closed("written")` fires and the session screen shows the success line after `refresh()`; in seen mode the Note tab keeps Copy and the `written_seen` line with Write DISABLED, a second Write click or a reopen completes nothing, and only Complete runs `complete_after_write`, after which the session screen shows `written_done`; on `unknown` the session stays QUEUED and the next click reconciles without a PATCH when the fake returns our digests; an `unknown` record followed by an offline, rejected-key, final-note or cooldown click shows the `write_uncertain` warning together with the refusal, on the live session and after a reopen; an unreadable `write.enc` after an unknown attempt or after a seen-mode `written` shows `record_unreadable` with Write refused and Copy available, also after a reopen; close is refused mid-write with the write-specific line; the Transcript row is disabled while writing; Recovery's Resume is blocked while writing and Write is refused while a recovery runs, in both orders, with the writing session's transcript source, completion callback and Note tab unchanged by any recovery result; a Chrome Start / Discard / open-for-review during a write is refused with an existing code (one test per action); a stale result (another session live) applies nothing; an adopted session writes through the same path. Fake clipboard only; no real hotkey; no real network; no host state.
- **Offline contract (Task 5.3):** the AST pin — the write jobs are constructed only inside `_on_write_requested`, whose only `connect` is `write_requested`; `test_integration_no_sockets.py` idle/startup/Chrome-link legs unchanged; mock and unlinked sessions never call the transport.
- **Docs (Task 6.1):** the grep checklist in D11 returns zero stale hits; a cross-family codex pass over the docs slice (H4) — a docs phase needs it (`docs/lessons.md` 2026-08-14).
- **Manual (practitioner):** Task P.1 (the test write, clinic 1, six questions) and Task P.2 (the live smoke: one real consultation note written, reloaded in Chrome, finalised by hand; one refused write on a note with typed text; one unknown-outcome rehearsal with Wi-Fi disabled after the click, then a reconcile click; close refused mid-write; the Unreviewed path).

## Deferred / Out of Scope
See the Planning Extraction Summary's Deferred / Excluded / Accepted Assumptions sections (state-once). In one line each: clinic 2 (blocked on a key); the Phase 6 audit record; SIMP-013/014/015 and SEC-008 (re-deferred, gate 2026-09-29); manual Complete's directory parity (deferred, gate 2026-09-29); SEC-014 host half; SIMP-010; 3+ speakers; POST; a Chrome write state; append/ask; scaffold labels; title/draft/booking fields; calendar Start; trial account; test-patient guard; network helper; overlap; finalisation (never).

## Current State / Handoff Note
- Last completed step: Cross-family `/peer-loop` CONVERGED 2026-09-29 — codex `gpt-6-astra` medium, plan-review mode, 8 rounds (8 → 7 → 2 → 3 → 2 → 2 → 1 → 0 findings; the cap raised by the practitioner from 5 to 8 one round at a time), 25 amendments applied in place and each confirmed by the following round; every disposition is in the Findings Log's Round 1–8 blocks. Before that: `/review-plan` hardening pass applied 2026-09-29 (four lenses). Main adjustments: three-hop write with the worker's note GET as the verification (no separate re-verification round trip; 3 requests); `RateLimitLatch` replaces the `CallGate` (spacing stays in the bridge; SEC-008 deferred); custody reuses `_custody_reservations` + `with_write_custody`; `write.enc` is one document with per-question normalised digests and the "write may have reached Cliniko" line; body = full re-read content and normalised comparison decided; completion mode (auto vs after-seen) decided by Task 2.1 on P.1's new question 5 (the open Cliniko editor); phases renumbered for `/execute-loop`; line/path corrections.
- Current in-progress step: None
- Immediate next action: commit the plan, then Phase 1 via `/execute-loop` (executor Opus 5.5 — the plan was authored on Fable 5.1 with tier-gap dosing)
- Open blockers / open questions: none in code; Task P.1 (practitioner) gates Phases 3–6
- Last plan sync: 2026-09-29

## Review History
Each /review invocation appends a one-line entry here. Round NUMBERS
are never allocated by counting this section's entries — allocation
follows /review's **Detect review round** rule (the canonical
definition: the `Review Findings Log`'s round headers, with a legacy
highest-History-round fallback when the Log has no headers; every
findings writer follows it). Ignore the placeholder line when reading
this section.

- 2026-09-29 round 1: 0 CRIT / 3 HIGH / 4 MED / 1 LOW; skew=none; action=amend-plan (Codex plan peer-review, gpt-6-astra medium; 8 build-affecting / 0 record-only / 0 invalid)
- 2026-09-29 round 2: 0 CRIT / 1 HIGH / 4 MED / 2 LOW; skew=none; action=amend-plan (Codex plan peer-review, gpt-6-astra medium; 6 build-affecting / 1 record-only / 0 invalid; attack-the-class re-review)
- 2026-09-29 round 3: 0 CRIT / 0 HIGH / 2 MED / 0 LOW; skew=none; action=amend-plan (Codex plan peer-review, gpt-6-astra medium; 2 build-affecting / 0 record-only / 0 invalid; attack-the-class re-review)
- 2026-09-29 round 4: 0 CRIT / 0 HIGH / 1 MED / 2 LOW; skew=none; action=amend-plan (Codex plan peer-review, gpt-6-astra medium; 3 build-affecting / 0 record-only / 0 invalid; attack-the-class re-review)
- 2026-09-29 round 5: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=none; action=amend-plan (Codex plan peer-review, gpt-6-astra medium; 2 build-affecting / 0 record-only / 0 invalid; attack-the-class re-review; CAP REACHED at 5, not converged)
- 2026-09-29 round 6: 0 CRIT / 0 HIGH / 2 MED / 0 LOW; skew=none; action=amend-plan (Codex plan peer-review, gpt-6-astra medium; 2 build-affecting / 0 record-only / 0 invalid; attack-the-class re-review under a practitioner-raised cap of 6; not converged)
- 2026-09-29 round 7: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=amend-plan (Codex plan peer-review, gpt-6-astra medium; 1 build-affecting / 0 record-only / 0 invalid; attack-the-class re-review under a practitioner-raised cap of 7; not converged)
- 2026-09-29 round 8: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (Codex plan peer-review, gpt-6-astra medium; 0 build-affecting / 0 record-only / 0 invalid; attack-the-class re-review under a practitioner-raised cap of 8; CONVERGED — pass closed, 25 amendments over rounds 1–7)

## Review Findings Log
Each /review invocation appends a detailed findings block here, with
/fix updating per-finding Decision and Notes as it processes each one.
Plan peer-review rounds carry `Source: <Tool> plan peer-review` and a
`Materiality:` summary; /fix never ingests them. Closed-round
compaction is `/document` Step 6.7's move (marker line →
`findings-cliniko-draft-write.md`, one lifecycle unit with this plan).

### Round 1 — 2026-09-29 — cliniko-draft-write plan, independent cross-family codex plan peer-review (round 1)

- Round status: Closed (8 applied as plan amendments; verified 8 build-affecting / 0 record-only / 0 invalid)
- Source: Codex plan peer-review
- Materiality: 8 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: e509b56 + working-tree plan
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `.cursor/plans/plan-cliniko-draft-write.md` in full; scoped sections of `AGENTS.md`, `PLAN.md`, and `docs/lessons.md`.
  - Named symbols in `desktop/src/scribe_desktop/cliniko_client.py`, `encounter.py`, `session.py`, `session_store.py`, `note.py`, `note_config.py`, and `config_defaults/template_profiles.json`.
  - Named symbols in `desktop/src/scribe_desktop/ui/note.py`, `transcript.py`, `main_window.py`, `bridge.py`, and `models.py`.
  - Scoped portions of `scripts/probe-cliniko.py`, `desktop/tests/test_cliniko_client.py`, `desktop/tests/test_integration_no_sockets.py`, and `desktop/pyproject.toml`.
  - Cited sections of `docs/security/threat-model.md`, `data-flow-map.md`, `retention-schedule.md`, `intended-use.md`, and `docs/design-system.md`.
- Finding verification: 12 candidates / 4 dropped / 1 downgraded
- Verification method: Static review only. No files written; no tests or builds run.

#### Findings

##### Unstated assumptions

**PR-HIGH-001 — Option B treats existing clinical text as an untyped baseline**

- Plan section: D4, D8, Task 2.1, Task 3.2.
- Materiality: build-affecting
- Why it matters: A clinician can start a recording on a draft that already contains typed text or an earlier recording’s written note. Option B captures that content as the baseline. An unchanged answer then passes the proposed check and is replaced. A new session has no previous `write.enc` to prevent this.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:179`: “Option B: a per-question digest of the note's targeted answers captured by the Start-time verification”; `:183`: “a second recording on a note the app already filled is refused with `note_has_text`”.
- Evidence: `desktop/src/scribe_desktop/encounter.py:540`: `note = call.get_treatment_note(target.note_id)`; `:541`: `state = _note_state(note)`. The state check at `:389` is `if not draft or note["finalized_at"] is not None:`; `:391` checks archival/deletion. These checks do not establish that existing content is an untouched scaffold.
- Suggested change: Keep Task 2.1 practitioner-owned, but require Option B to establish a pristine scaffold independently before accepting captured answers as replaceable. Otherwise refuse automatic writing. Add cases for text entered before Start and a second recording on an already-filled draft.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): D4's Option B (Start-time snapshot) removed; Option C = a practitioner-written per-clinic `template_defaults.json` from P.1's pristine-note structure; Task 2.1, Task 3.2, Schema updated.
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

##### Missing verification / rollback / migration

**PR-HIGH-002 — The full-content PATCH can overwrite edits made after the verification GET**

- Plan section: D3, D4, Critical Constraint 4, Task P.1.
- Materiality: build-affecting
- Why it matters: Between the note GET and PATCH, the clinician can save an edit in Cliniko. The planned body then replaces that edit with the earlier snapshot. Because the body contains all questions, even an untargeted answer or attestation changed during this interval can be reverted. Question 5 tests editor saves after PATCH, which is the opposite ordering.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:179`: “The body is ALWAYS the full re-read `content` with only the targeted answers replaced”; `:207`: “A note holding non-baseline text is never overwritten”.
- Evidence: `.cursor/plans/plan-cliniko-draft-write.md:178` places the template GET and GUI preparation between the note GET and “Hop 2 (worker, the same key): the PATCH only.” The existing guard at `desktop/src/scribe_desktop/encounter.py:970` checks `or request.clinic_rev != clinics.rev(context.clinic_id)`—the local clinic revision, not a server-side note revision.
- Suggested change: Add a feasibility gate for an atomic server-side conditional write and test an edit occurring between GET and PATCH. If Cliniko cannot enforce a precondition, return this concrete overwrite risk to the practitioner before enabling the feature. Another GET alone cannot establish the claimed guarantee.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): the body shape returns to Task 2.1 (partial preferred if P.1 question 2 shows Cliniko merges); hop 1 orders template GET first, note GET last; the window named as a residue in D4, Accepted Assumptions and Task 6.1; P.1 question 6 and the probe's window pass added.
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

**PR-HIGH-003 — An old write outcome can authorise destruction of a regenerated note**

- Plan section: D5, D6, Tasks 3.3, 4.2, 5.2.
- Materiality: build-affecting
- Why it matters: After writing note A, seen mode or interrupted completion retains the session. The existing UI permits regeneration and Save of note B. The old `written` record then completes without sending B and destroys B’s key. The same failure occurs when an unknown attempt for A reconciles successfully after B has been saved.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:180`: “A record already `written` completes without any network call, even if the note has since been finalised.” Completion at `:181` checks “the record reads `written` under the controller lock”.
- Evidence: `desktop/src/scribe_desktop/ui/main_window.py:820` passes `can_generate=True` when opening an adopted session. `desktop/src/scribe_desktop/ui/transcript.py:397` documents `"Regenerate (replaces the saved note)"`; `:758` saves through `lease, lambda directory, crypto: write_note(directory, crypto, note, config)`.
- Suggested change: Bind successful-write completion to the current saved-note identity and rendered payload. Preserve the historical attempt for reconciliation, but refuse success-driven deletion when the saved note has changed. Test both `written` and `unknown` attempts across regeneration and restart.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): the record carries `note_identity`; `complete_after_write` and reconcile require it to equal the saved note's; `begin_generation` and `save_note` refuse `write_pending` once any attempt exists (D5, D9, Tasks 3.3, 4.1, 4.2, Validation).
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

##### Practicality / feasibility / sequencing

**PR-MED-004 — The UI sequence releases the reservation before the operation that must consume it**

- Plan section: D6, Flow 1, Task 5.2.
- Materiality: build-affecting
- Why it matters: Following Task 5.2 literally leaves automatic completion holding a released reservation. Seen-mode completion also needs a defined way to acquire custody later. Either completion fails or the implementation weakens the identity/lifetime check to accommodate the contradictory sequence.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:290`: “record, `record_429`, release, then `complete_written` (auto) or the seen line”. D6 at `:181` requires “release the reservation — no release-then-complete gap.”
- Evidence: The proposed accessor’s existing pattern rejects stale ownership: `desktop/src/scribe_desktop/session.py:1405`: `if self._generation is None or self._generation is not lease:`. Plan validation at `.cursor/plans/plan-cliniko-draft-write.md:225` explicitly requires “`with_write_custody` refuses a foreign or released reservation”.
- Suggested change: Make automatic completion consume the still-held reservation. Define reacquisition and record revalidation for later Complete in seen mode and for reopening an already-written session. Specify release ownership on completion failure and test each branch.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): D6 and Task 5.2 — auto mode completes with the reservation still held (completion consumes it; failure releases); seen mode releases and Complete re-acquires with record revalidation under the lock.
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

**PR-MED-005 — Existing response processing can discard an observed PATCH 200**

- Plan section: D3, Task 1.1, Client validation.
- Materiality: build-affecting
- Why it matters: A successful PATCH followed by a malformed, oversized or stalled response body becomes an exception under the existing transport/parser. The write orchestrator never receives the observed 200 and can misclassify the write as unknown, contrary to the locked outcome contract.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:178`: “classify by the HTTP answer ONLY (a 200 is never relabelled)”; Task 1.1 at `:266`: “every other status as today.”
- Evidence: `desktop/src/scribe_desktop/cliniko_client.py:339`: `body = _read_bounded(response, max_body, in_time) if status == 200 else b""`; `:495`: `return _parse_object(raw.body)`; `:519`: `raise Malformed()  # raised outside the except block: no chained context`.
- Suggested change: Specify PATCH-specific status handling that preserves an observed 200 independently of optional response-body processing. Keep GET parsing unchanged. Test malformed, oversized and stalled PATCH 200 bodies, plus failure reading an optional header after obtaining the status.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): `write_draft_note` classifies on the status line before the body; a 200 with a malformed/oversize/stalled body stays `written` (D5, Task 1.1, External findings, Validation).
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

##### Simpler / safer alternatives

**PR-MED-006 — A shape filter cannot make returned 422 field names residue-free**

- Plan section: D11, Task 1.1, Client validation.
- Materiality: build-affecting
- Why it matters: An identifier-shaped response key can itself contain clinical information and pass the proposed filter into exception/status text. Testing only a sentinel containing disallowed characters would miss this.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:186`: “The 422 path is named as a residue-free surface”; the same line specifies “at most 8, the rest counted as "other"”.
- Evidence: The existing probe explicitly acknowledges the same limitation at `scripts/probe-cliniko.py:26`: “Named residue: a JSON KEY is printed”; `:27`: “when it has the shape of a field name (lower-case identifier)”.
- Suggested change: Emit only fixed, recognised schema field names or fixed categories; map everything else to “other”. Test an identifier-shaped data-bearing key as well as echoed values. Do not describe a shape-only filter as residue-free.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): 422 keys reduced to Cliniko's documented field names or `other`; the 'residue-free' claim removed; the identifier-shaped data key added to the tripwire test (D11, Task 1.1, Validation).
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

**PR-MED-007 — Suppressing exception display does not remove the raw parsing exception**

- Plan section: D11, Task 1.1, Client validation.
- Materiality: build-affecting
- Why it matters: Raising inside a parser exception handler with `from None` suppresses displayed chaining but retains `__context__`. A malformed 422 can therefore leave the original parsing exception and its response document attached, contrary to the existing client contract.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:186`: “values dropped before the exception is built, `raise … from None` (no `JSONDecodeError.doc` on `__cause__`)”.
- Evidence: `desktop/src/scribe_desktop/cliniko_client.py:349–350` documents “Run one library call; on failure raise its named error with NO” and “``__context__`` (raised after the ``except`` block has finished).” Existing tests at `desktop/tests/test_cliniko_client.py:104–105` require `assert error.__cause__ is None` and `assert error.__context__ is None`.
- Suggested change: Follow the existing outside-the-handler raise pattern after reducing the response to safe categories. Extend malformed-422 tests to assert both exception attributes are absent. Keep the separately documented traceback-local lifetime residue distinct.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): the named error is raised outside the handler per the module's `_guarded` pattern; tests assert `__cause__` and `__context__` are both None (D11, Task 1.1, Validation).
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

##### Coverage

**PR-LOW-008 — Checkout consumes the shared cooldown but never contributes its own 429**

- Plan section: D13, Task 1.3, Latch validation.
- Materiality: build-affecting
- Why it matters: A checkout verification can receive a 429 without cooling subsequent bridge checks or writes. The shared latch therefore misses one of its three producers. Severity is LOW because the demonstrated consequence is additional requests during throttling.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:188`: “a 429 seen by one path must stop the others”. Task 1.3 at `:268` only says checkout “consults `cooling` and shows the existing rate-limited line instead of calling”.
- Evidence: `desktop/src/scribe_desktop/ui/main_window.py:1223–1225` stores `self._checkout.result = result`, then calls `self._start_waiting_reverification(ran)` and `self._show_checkout_line()`. In contrast, `desktop/src/scribe_desktop/ui/bridge.py:818` explicitly handles `if isinstance(outcome, UnverifiedOffline) and outcome.rate_limited:`.
- Suggested change: Record checkout-originated 429s in the latch before dispatching waiting work, independently of whether the display result is stale. Add checkout-to-bridge and checkout-to-write cooldown tests.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): the checkout's `_finish_reverify_task` records a 429 into the latch before dispatching waiting work (D13, Task 1.3, Validation).
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

PEER-PLAN-ROUND-1 RESULT: 8 findings (CRIT 0 / HIGH 3 / MED 4 / LOW 1; build-affecting 8 / record-only 0 / invalid 0).


### Round 2 — 2026-09-29 — cliniko-draft-write plan, independent cross-family codex plan peer-review (round 2)

- Round status: Closed (7 applied as plan amendments; verified 6 build-affecting / 1 record-only / 0 invalid)
- Source: Codex plan peer-review
- Materiality: 6 build-affecting / 1 record-only / 0 invalid
- Plan reviewed at: e509b56 + working-tree plan
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `.cursor/plans/plan-cliniko-draft-write.md` in full, including Round 1 dispositions.
  - Scoped sections of `AGENTS.md`, `PLAN.md`, `docs/lessons.md`, `docs/design-system.md`, and `docs/security/{threat-model,data-flow-map,retention-schedule,intended-use}.md`.
  - Named symbols in `desktop/src/scribe_desktop/{cliniko_client,encounter,session,session_store,note,note_config}.py` and `config_defaults/template_profiles.json`.
  - Named symbols in `desktop/src/scribe_desktop/ui/{note,transcript,main_window,bridge,models}.py`.
  - Scoped portions of `scripts/probe-cliniko.py`, `desktop/tests/test_cliniko_client.py`, `desktop/tests/test_integration_no_sockets.py`, and `desktop/pyproject.toml`.
- Finding verification: 15 candidates / 8 dropped / 0 downgraded
- Verification method: Static review only. No files written; no tests or builds run.
- Class coverage: Rechecked clinical-text baseline and identity confusion; read-to-write and write-to-completion races; success delivery through persistence and UI; structural guarantees versus stated claims; and shared cooldown producers/consumers. No additional verified finding in reservation lifetime, outcome-fsync ordering, or the amended three-path cooldown contract.

#### Findings

##### Unstated assumptions

**PR-HIGH-009 — HTML normalization can erase meaningful plain-text differences**

- Plan section: D4, D5, Tasks 3.2–3.3.
- Materiality: build-affecting
- Why it matters: This is the baseline/identity-confusion class. Plain-text answers have no HTML semantics. Stripping literal angle-bracket annotations or decoding literal entity notation can make clinician-entered text compare equal to a baseline, or make different chart content compare equal to the attempted answer. The former permits overwriting typed text; the latter permits reconciliation to declare success and destroy local custody despite a content difference.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:181`: “Comparison is ALWAYS normalised: tags stripped, HTML entities unescaped, whitespace collapsed, NFC.” At `:182`: “every targeted answer's normalised digest equals `digests` → `written`”.
- Evidence: `desktop/src/scribe_desktop/config_defaults/template_profiles.json:17`: `"field_label": "Assessment",`; `:18`: `"target_type": "plain_text"`. The plan itself distinguishes the output types at `.cursor/plans/plan-cliniko-draft-write.md:184`: “`plain_text` → lines joined by `\n`”.
- Suggested change: Make comparison and digest normalization question-type-aware. Interpret HTML only for paragraph answers; preserve literal characters in text answers. Add baseline-refusal and unknown-outcome reconciliation tests covering literal angle brackets and entity notation in plain text.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): normalisation is question-type-aware — HTML interpreted only for paragraph answers, plain-text answers compared literally (whitespace + NFC only) — in D4/D5, Task 3.2 and Validation.
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

**PR-MED-010 — The already-written shortcut does not preserve the seen-mode acknowledgment explicitly**

- Plan section: Flow 2, D2, D5, D6, Task 5.2.
- Materiality: build-affecting
- Why it matters: This is the write-to-completion class. Seen mode retains custody until the clinician presses Complete after seeing the chart. However, Write remains eligible after the result handler releases its reservation, and D5 gives an unconditional completion instruction for an already-written record. Following that branch on a second Write click—or after reopening the session—bypasses the action that seen mode relies on.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:182`: “A record already `written` completes without any network call, even if the note has since been finalised.” At `:179`: “the tab's `_write_ready` = `_copy_ready()` AND `binding.linked` AND not in flight AND no style job AND `provider_name` not `mock-…` (D10)”.
- Evidence: The contrasting requirement is explicit at `.cursor/plans/plan-cliniko-draft-write.md:183`: “In seen mode the handler releases after recording; the Complete button re-acquires through `reserve_write`”. The existing reopened-note predicate at `desktop/src/scribe_desktop/ui/note.py:2134` is `return self._copy_enabled and not saved.blocking_warnings()`, so the proposed Write predicate does not exclude this state.
- Suggested change: Define the already-written branch by completion mode. In seen mode, another Write click must only redisplay the confirmation/instructions; only Complete acknowledges seeing the draft and consumes custody. Preserve automatic completion when that mode is chosen. Test both live and reopened written sessions.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): the already-written branch is mode-aware — in seen mode Write is disabled and the tab shows `written_seen`; only Complete consumes custody; a reopened written session takes the same path (D2, D5, D6, Task 5.2, Validation).
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

##### Missing verification / rollback / migration

**PR-MED-011 — Partial content does not eliminate overwrites of targeted questions**

- Plan section: Accepted Assumptions, D4, Task 2.1, Task P.1, Critical Constraint 4.
- Materiality: build-affecting
- Why it matters: This is the read-to-PATCH race class applied to the amendment. A partial merge protects omitted questions, but still replaces each included answer. A clinician edit to a targeted question after the GET can therefore be lost. The proposed probe deliberately edits a different question, so its successful partial-body result cannot establish the broader safety claim used by Task 2.1.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:408`: “partial — only the targeted sections/questions (preferred if question 2 shows Cliniko MERGES partial content: an edit saved during the GET→PATCH window cannot be reverted)”.
- Evidence: `.cursor/plans/plan-cliniko-draft-write.md:175` instructs the window pass to “edit and save a DIFFERENT question in the editor, then press Enter”. D4 at `:181` correctly describes the narrower benefit: “an untargeted answer the clinician saves between our GET and our PATCH cannot be reverted”. The existing local guard at `desktop/src/scribe_desktop/encounter.py:970` checks `or request.clinic_rev != clinics.rev(context.clinic_id)`, which is not a server-side answer precondition.
- Suggested change: State that targeted-answer races remain in both body modes. Add a targeted-question edit to the window verification, and present that residual overwrite risk in Task 2.1 regardless of the partial/full decision. Narrow Critical Constraint 4 to what the pre-write observation actually establishes.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): the targeted-answer race is a residue in BOTH body modes; the window pass also edits the targeted question; Task 2.1's partial option claims only the untargeted benefit; Critical Constraint 4 narrowed to the click's own read (D4, Flow 4, Task 1.2, Task 2.1, Accepted Assumptions).
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

##### Practicality / feasibility / sequencing

**PR-MED-012 — Template-first ordering requires an identifier a valid linked session may not have**

- Plan section: D3, Tasks 3.4 and 5.2, Orchestration validation.
- Materiality: build-affecting
- Why it matters: A session legitimately started while Cliniko was unavailable is linked but has no template identifier. It cannot perform the newly mandated first request. A stored identifier can also become stale: the current write-back guard does not compare template identities. The plan needs discovery and an explicit check that the fetched template belongs to the final note observation.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:180`: “`GET /treatment_note_templates/<template_id>` FIRST, then `verify_note_for_write(request)`”. At `:159`: “A write is exactly 3 requests”.
- Evidence: `desktop/src/scribe_desktop/encounter.py:126`: `template_id: _ClinikoId | None = None`. `_offline_context` at `:450` constructs `EncounterContext` without a template identifier and sets `verification=Verification.UNVERIFIED_OFFLINE,` at `:456`. The identifier is discovered after the note GET at `:553`: `template_id = _link_id(note, "treatment_note_template", None)`. `_same_note` at `:926` compares `(a.clinic_id, a.clinic_host, a.patient_id, a.treatment_note_id, a.practitioner_id)`, excluding template.
- Suggested change: Permit a discovery note GET when the template identifier is absent, fetch that template, then perform the final note GET and require its template identifier to match. Define fail-closed behavior for a changed template. Update the fixed request-count claim and the still-note-first sequence test at plan `:226`.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): hop 1 runs a discovery note GET when the context has no template id, and the FINAL note GET's template link must equal the fetched template's id (else `template_mismatch`); the request count is 3 or 4 (D3, External findings, Task 3.4, Validation).
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

**PR-MED-013 — Option C requires scaffold output the probe must redact**

- Plan section: D4, Schema / Data Changes, Tasks 1.2, P.1 and 2.1.
- Materiality: build-affecting
- Why it matters: Option C is needed when the template response lacks default answers, but its specified source—the probe’s printed output—cannot contain the required scaffold. Implementing the proposed output restriction leaves the practitioner unable to construct the configuration as instructed; printing the scaffold instead violates the acceptance criterion.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:181`: “the scaffold text as printed by the probe from a note the practitioner confirms PRISTINE during P.1”. At `:223`: “structure-only output (no id value, name, URL, answer text or key in stdout)”.
- Evidence: `scripts/probe-cliniko.py:98`: `if isinstance(value, str):`; `:99`: `return "<empty>" if value == "" else "<text>"`. Task 1.2 at `.cursor/plans/plan-cliniko-draft-write.md:401` specifies “the template structure and default-text presence” and “Structure only in stdout.”
- Suggested change: Give Option C an executable capture procedure, such as practitioner transcription directly from a confirmed pristine Cliniko note. Alternatively, specify a separately authorized scaffold-capture mode and its data-handling contract. Keep ordinary probe output structure-only.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): Option C's scaffold text is transcribed by the practitioner from the pristine note as shown in Cliniko's own editor; the probe prints presence only and stays structure-only (D4, Schema, Task P.1, Task 2.1).
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

**PR-LOW-014 — Completion looks up a success-message key absent from the dictionary**

- Plan section: D6, Task 5.1, Task 5.2.
- Materiality: build-affecting
- Why it matters: This is the success-delivery class. Following the explicit lookup raises after successful completion has destroyed custody, instead of displaying the promised confirmation. The dictionary defines pending-seen and automatic-write messages but no terminal `written` entry.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:183`: “sets `WRITE_LINES["written"]` on the session screen after `refresh()`”.
- Evidence: Task 5.1 at `.cursor/plans/plan-cliniko-draft-write.md:424` defines `written_auto` and `written_seen`, but no `written`. Its `written_seen` text is “Draft written to Cliniko. Reload the note page in Chrome; press Complete once you can see it there.” The existing completion sequence at `desktop/src/scribe_desktop/ui/transcript.py:849` executes `self._clear()` before `self.closed.emit("completed")` at `:854`.
- Suggested change: Define a terminal success entry and reference it consistently, keeping the pre-completion seen instruction separate. Test message delivery after both automatic completion and explicit seen-mode Complete.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): a terminal `written_done` entry added to Task 5.1; D6 references it; `written_seen` stays the pre-completion line.
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

##### Coverage

**PR-LOW-015 — The global offline constraint contradicts the retained reconnect and spacing behavior**

- Plan section: Critical Constraint 2, D13, Task 6.1.
- Materiality: record-only
- Why it matters: This is the stronger-than-structure claim class. The plan retains existing bridge behavior, including reconnect-triggered verification and a timer that dispatches previously requested work. The blanket constraint inaccurately rules those out and could propagate into the security-docs rewrite.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:207`: “No Cliniko call except on a practitioner action or a Chrome report, and none at startup, idle, timer, sweep or reconnect”.
- Evidence: D13 at `.cursor/plans/plan-cliniko-draft-write.md:190` explicitly preserves “its queue, `MIN_CALL_SPACING_SECONDS` and the QTimer”. `desktop/src/scribe_desktop/ui/bridge.py:788` defines `def _on_spacing_elapsed(self) -> None:` and calls `self._next()` at `:793`. `docs/security/data-flow-map.md:598` documents “once per new pipe connection — the linked live” session’s verification, continued at `:599`.
- Suggested change: Scope the button-only/no-reconnect rule to write and reconciliation. Preserve the existing read contract: reconnect may request verification, and the spacing timer may dispatch already-requested work; neither introduces autonomous polling.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment, record-only): Critical Constraint 2 scoped to the write and its reconcile; the existing read contract (reconnect verification of a linked live session, the spacing timer dispatching already-requested checks) stated as retained.
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

PEER-PLAN-ROUND-2 RESULT: 7 findings (CRIT 0 / HIGH 1 / MED 4 / LOW 2; build-affecting 6 / record-only 1 / invalid 0).

### Round 3 — 2026-09-29 — cliniko-draft-write plan, independent cross-family codex plan peer-review (round 3)

- Round status: Closed (2 applied as plan amendments; verified 2 build-affecting / 0 record-only / 0 invalid)
- Source: Codex plan peer-review
- Materiality: 2 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: e509b56 + working-tree plan
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `.cursor/plans/plan-cliniko-draft-write.md` in full, including both prior rounds’ dispositions.
  - Scoped sections of `AGENTS.md`, `PLAN.md`, `docs/lessons.md`, `docs/design-system.md`, and `docs/security/{threat-model,data-flow-map,retention-schedule,intended-use}.md`.
  - Named symbols in `desktop/src/scribe_desktop/{cliniko_client,encounter,session,session_store,note,note_config}.py` and `config_defaults/template_profiles.json`.
  - Named symbols in `desktop/src/scribe_desktop/ui/{note,transcript,main_window,bridge,models}.py`; supporting worker lifecycle code in `ui/tasks.py`.
  - Scoped portions of `scripts/probe-cliniko.py`, `desktop/tests/test_cliniko_client.py`, `desktop/tests/test_integration_no_sockets.py`, and `desktop/pyproject.toml`.
- Finding verification: 14 candidates / 12 dropped / 0 downgraded
- Verification method: Static review only. No files written; no tests or builds run.
- Class coverage: Reviewed classes (a)–(j), including the amendments themselves. The findings below concern comparison semantics and uncertainty surviving failed retries. Reservation lifetime, completion-mode acknowledgment, saved-note identity, optional booking/template context, worker-close protection, and the scoped cooldown contract produced no additional verified finding.

#### Findings

##### Unstated assumptions

**PR-MED-016 — Paragraph normalization conflates input representation and visible text**

- Plan section: D4, D5, D7, Schema / Data Changes, Tasks 3.2–3.3.
- Materiality: build-affecting
- Why it matters: Classes **(a), (f), and (i)**. Option C stores already-visible text transcribed from the editor, whereas an API paragraph contains HTML. Applying the same HTML decoding to both can falsely reject an untouched scaffold. Conversely, if the visible scaffold contains literal entity notation, a clinician’s edit replacing that notation with its represented character can match the incorrectly decoded baseline and be overwritten. Separately, stripping paragraph/break tags without preserving separators can concatenate clinical tokens and make different answers reconcile as equal.
- Current plan text:
  - `.cursor/plans/plan-cliniko-draft-write.md:181`: “the scaffold text the practitioner TRANSCRIBES from a pristine note as Cliniko's own editor shows it”
  - Same line: “a `paragraph` answer has HTML semantics, so tags are stripped and entities unescaped before whitespace is collapsed and NFC applied”
  - Same line: “the same `normalise_answer(text, question_type)` serves the default comparison and the reconcile digests.”
- Evidence:
  - `.cursor/plans/plan-cliniko-draft-write.md:194`: “transcribed by the practitioner from the pristine note as Cliniko's editor shows it”
  - `.cursor/plans/plan-cliniko-draft-write.md:184`: “`rich_text` → one `<p>` per line”
  - `desktop/src/scribe_desktop/note.py:926–930`:
    ```python
    def _clean_lines(section: GeneratedSection) -> list[str]:
        """One terse line per assertion, in the note's order: the confirmed
        text exactly as confirmed — no substitution, no bullet, no provenance
        tag (the line editor keeps the per-line provenance; the tag is review
        apparatus, not clinical content). A pre-filled line keeps its D5 mark."""
    ```
  - `desktop/src/scribe_desktop/note.py:941`:
    ```python
    return "\n".join([SECTION_TITLES[section.section_key], *_clean_lines(section)])
    ```
- Suggested change: Distinguish representation from question type. Convert API paragraph HTML to visible text exactly once, preserving separators at paragraph, break, and list boundaries. Treat Option C transcription as already-visible text; apply shared whitespace/NFC normalization afterward. Add tests for an untouched scaffold containing literal entity notation, the corresponding clinician-edited variant, and adjacent clinical tokens separated by HTML block boundaries.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): D4 separates REPRESENTATION from question type — API paragraph HTML → visible text once with block/br/li boundaries as newlines, then entities; `text` answers and Option C transcriptions are already visible and never decoded; shared whitespace + NFC afterwards; three tests added to Validation.
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

##### Coverage

**PR-MED-017 — A failed retry verification replaces the unresolved-write warning with Copy guidance**

- Plan section: D3, D5, Task 3.4, Task 5.1, UI validation.
- Materiality: build-affecting
- Why it matters: Classes **(c) and (d)**. A PATCH can reach Cliniko while its response is lost, leaving `unknown`. On the next click, connectivity failure, rejected credentials, or a now-final note can prevent verification. The prescribed guard returns before reconciliation, and the generic failure message invites copying despite the unresolved possibility that the draft is already present. D5 specifies the caution for content-comparison failures, but does not preserve it through these earlier exits.
- Current plan text:
  - `.cursor/plans/plan-cliniko-draft-write.md:537`: “the GUI-thread step: `writeback_context`, reconcile, `note_has_text`, `match_template`, `build_body`”
  - `.cursor/plans/plan-cliniko-draft-write.md:544`: “`check_failed` "The note could not be checked with Cliniko just now (<reason>). Copy the note, or try again."”
- Evidence:
  - `desktop/src/scribe_desktop/encounter.py:974–977`:
    ```python
    if isinstance(outcome, NoteRefused):
        return WritebackRefused(WritebackRefusal.REVERIFICATION_REFUSED, outcome.reason)
    if isinstance(outcome, UnverifiedOffline):
        return WritebackRefused(WritebackRefusal.NOT_VERIFIED)
    ```
  - `.cursor/plans/plan-cliniko-draft-write.md:182`: “otherwise → `write_uncertain` ("an earlier write may have reached Cliniko — check the note before copying"), never a bare `note_has_text`.”
- Suggested change: Preserve unresolved-attempt status through every failed retry admission or verification. For an existing `attempting`/`unknown` record, show the may-have-reached-Cliniko warning alongside the current refusal reason instead of unconditional Copy guidance. Keep Copy available under the practitioner’s decision. Test offline, rejected-key, final-note, and cooldown retry exits, including after reopening the session.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): D5 and Task 5.1 — while the record holds an `attempting`/`unknown` attempt, every pre-reconcile refusal (offline, rejected key, final note, cooldown, gone clinic) carries the `write_uncertain` warning, live and after a reopen; Validation's UI bullet pins it.
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

PEER-PLAN-ROUND-3 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 2 / LOW 0; build-affecting 2 / record-only 0 / invalid 0).

### Round 4 — 2026-09-29 — cliniko-draft-write plan, independent cross-family codex plan peer-review (round 4)

- Round status: Closed (3 applied as plan amendments; verified 3 build-affecting / 0 record-only / 0 invalid)
- Source: Codex plan peer-review
- Materiality: 3 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: e509b56 + working-tree plan
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `.cursor/plans/plan-cliniko-draft-write.md` in full, including previous dispositions.
  - Scoped sections of `AGENTS.md`, `PLAN.md`, `docs/lessons.md`, `docs/design-system.md`, and `docs/security/{threat-model,data-flow-map,retention-schedule,intended-use}.md`.
  - Named symbols in `desktop/src/scribe_desktop/{cliniko_client,encounter,session,session_store,note,note_config}.py` and `config_defaults/template_profiles.json`.
  - Named symbols in `desktop/src/scribe_desktop/ui/{note,transcript,main_window,bridge,models}.py`; supporting Discard entry in `ui/session_screen.py`.
  - Scoped portions of `scripts/probe-cliniko.py`, `desktop/tests/test_cliniko_client.py`, `desktop/tests/test_integration_no_sockets.py`, and `desktop/pyproject.toml`.
- Finding verification: 8 candidates / 5 dropped / 1 downgraded
- Verification method: Static review only. No files written; no tests or builds run.
- Class coverage: Reviewed classes (a)–(l), including the amendments. Dropped the proposed discard-first race because its production interleaving was not established under the GUI-thread contract and the documented arbitrary-thread residue.

#### Findings

##### Coverage

**PR-MED-018 — An unreadable write record falsely reports that Cliniko rejected the draft**

- Plan section: D5, Task 3.3, Task 5.1, UI validation.
- Materiality: build-affecting
- Why it matters: Classes **(c), (d), and (l)**. A PATCH can succeed, leave a retained session, and later have an unreadable `write.enc`. The amended uncertainty warning depends on reading `attempting` or `unknown`, so it cannot cover this case reliably. Task 5.1 instead classifies “write record unreadable” under “Cliniko did not take the draft” and recommends Copy. Local record failure cannot establish remote rejection; that guidance can encourage duplicating content already present in the chart.
- Current plan text:
  - `.cursor/plans/plan-cliniko-draft-write.md:182`: “a corrupt or undecryptable record refuses (`write_record_unreadable`).”
  - `.cursor/plans/plan-cliniko-draft-write.md:623`: “`not_taken` "Cliniko did not take the draft (<cause>). Copy the note instead."”
  - Same line includes the cause “write record unreadable” and conditions the warning on “whenever the record holds an `attempting` or `unknown` attempt”.
- Evidence:
  - `.cursor/plans/plan-cliniko-draft-write.md:615`: “unreadable → `write_record_unreadable`”.
  - The encrypted-record reader used as the proposed pattern cannot recover an outcome after authentication failure: `desktop/src/scribe_desktop/session_store.py:895`: `except InvalidTag:`; `:897`: `raise StoreCorruptError("encounter record unavailable")  # outside the except`.
- Suggested change: Give unreadable write records a distinct uncertainty message: the previous outcome cannot be checked, so inspect Cliniko before copying. Preserve the write refusal and Copy availability. Test an unreadable record after both an unknown attempt and a confirmed write retained in seen mode, including reopening.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): an unreadable `write.enc` gets its own `record_unreadable` uncertainty line (D5, Task 5.1) — never a `not_taken` cause; Validation pins it after an unknown attempt and after a seen-mode written record, live and reopened.
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

##### Practicality / feasibility / sequencing

**PR-LOW-019 — The prescribed refusal formatter accepts a different refusal type**

- Plan section: Task 5.1.
- Materiality: build-affecting
- Why it matters: Class **(j)**. `clinic_refusal_line` formats clinic-registration operations, not `WritebackRefusal`. Following the explicit routing instruction produces a type/signature mismatch or missing dictionary entry for cases such as `consent_unavailable` and `context_changed`. The new write formatter needs its own exhaustive mapping.
- Current plan text:
  - `.cursor/plans/plan-cliniko-draft-write.md:623`: “`<reason>` from `clinic_refusal_line` for every `WritebackRefusal` name and from `note_refusal_line` for every `NoteRefusal` name”.
- Evidence:
  - `desktop/src/scribe_desktop/ui/models.py:3253`: `refusal: Refused, *, operation: ClinicOperation, clinic_name: str, path: Path`
  - `:3255`: `"""The status line for a refused Validate / Replace key / Remove."""`
  - `:3259`: `template = _CLINIC_REFUSAL_COPY[refusal.reason]`
  - `desktop/src/scribe_desktop/encounter.py:861`: `CONSENT_UNAVAILABLE = "consent_unavailable"`
  - `:870`: `CONTEXT_CHANGED = "context_changed"`
- Suggested change: Specify a typed `WritebackRefusal` mapping inside `write_line` or a dedicated formatter, reusing the existing formatting *pattern*. Retain `note_refusal_line` for nested note refusals and the exhaustive resolution test.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): Task 5.1 specifies a typed `writeback_refusal_line(WritebackRefusal)` with its own exhaustive table in the `clinic_refusal_line` pattern; `note_refusal_line` kept for nested note refusals; the enumeration test unchanged.
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

**PR-LOW-020 — Option C does not explain how the practitioner obtains its required identity keys**

- Plan section: D4, Schema / Data Changes, Tasks P.1 and 2.1.
- Materiality: build-affecting
- Why it matters: Classes **(i) and (j)**. The revised procedure supplies scaffold text, but the configuration also requires the app’s clinic identifier and Cliniko’s template identifier. Neither is supplied by the stated transcription procedure or permitted probe output. This leaves setup incomplete if Option C is selected. Downgraded from MED to LOW because it blocks configuration rather than demonstrating an unsafe write.
- Current plan text:
  - `.cursor/plans/plan-cliniko-draft-write.md:194`: `{clinic_id: {template_id: {"<section name>/<question name>": "<scaffold text>"}}}`
  - `.cursor/plans/plan-cliniko-draft-write.md:604`: “the practitioner transcribes the scaffold text of every defaulted question from a PRISTINE note as Cliniko's editor shows it into `template_defaults.json`; the probe's output names the questions only”.
- Evidence:
  - `.cursor/plans/plan-cliniko-draft-write.md:223`: “structure-only output (no id value, name, URL, answer text or key in stdout)”.
  - `scripts/probe-cliniko.py:216`: `out(f"  {field} link present: {_yes(_link_id(note, field) is not None)}")`
  - `desktop/src/scribe_desktop/encounter.py:553`: `template_id = _link_id(note, "treatment_note_template", None)`
  - The local profile identifier is different: `desktop/src/scribe_desktop/config_defaults/template_profiles.json:5`: `"template_profile_id": "template-a",`
- Suggested change: Add exact practitioner lookup steps for both identifiers, or a local configuration bootstrap procedure, followed by a check that the loaded defaults match the selected clinic and template. Keep pasted probe output redacted.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): `template_defaults.json` is keyed by the clinic's display name and the Cliniko template's name (matched against the fetched template's `name`), both human-visible; a missing key = no defaults (D4, Schema, Task P.1, Validation).
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

PEER-PLAN-ROUND-4 RESULT: 3 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 2; build-affecting 3 / record-only 0 / invalid 0).

### Round 5 — 2026-09-29 — cliniko-draft-write plan, independent cross-family codex plan peer-review (round 5)

- Round status: Closed (2 applied as plan amendments; verified 2 build-affecting / 0 record-only / 0 invalid)
- Source: Codex plan peer-review
- Materiality: 2 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: e509b56 + working-tree plan
- Files read: `.agents/skills/peer-review/SKILL.md`; the working-tree plan in full, including prior dispositions; scoped sections of `AGENTS.md`, `PLAN.md`, `docs/lessons.md`, `docs/design-system.md`, and `docs/security/{threat-model,data-flow-map,retention-schedule,intended-use}.md`; named symbols in `desktop/src/scribe_desktop/{cliniko_client,encounter,session,session_store,note,note_config}.py`, `config_defaults/template_profiles.json`, and `ui/{note,transcript,main_window,bridge,models}.py`; scoped portions of `scripts/probe-cliniko.py`, `desktop/tests/test_cliniko_client.py`, `desktop/tests/test_integration_no_sockets.py`, and `desktop/pyproject.toml`; narrowly scoped supporting code in `clinics.py` and `app.py`.
- Finding verification: 9 candidates / 7 dropped / 0 downgraded
- Verification method: Static review only. No files written; no tests or builds run.
- Class coverage: Reviewed classes (a)–(o), including the amendments. No additional verified defect in reservation lifetime, completion-mode acknowledgment, saved-note freezing, status-line preservation, or the three-path cooldown contract.

#### Findings

##### Unstated assumptions

**PR-MED-021 — Option C selects safety baselines using non-unique clinic names**

- Plan section: D4, Schema / Data Changes, Tasks P.1 and 3.2.
- Materiality: build-affecting
- Why it matters: Classes **(a)** baseline identity confusion and **(o)** practitioner-supplied identifiers. Two legitimate clinic records can share a display name and use equally named templates with identical question structure but different defaults. The amended configuration aliases their baselines. For example, text that is a scaffold default in clinic A can be clinician-entered text in clinic B. Using A’s baseline for B classifies that text as untyped and permits replacement. Patient verification and structural template matching do not distinguish the baseline’s provenance.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:181`: “keyed by the clinic's DISPLAY NAME (as the Clinics tab shows it) and the Cliniko template's NAME”. At `:194`: `{"<clinic display name>": {"<template name>": {"<section name>/<question name>": "<scaffold text>"}}}`.
- Evidence: `desktop/src/scribe_desktop/clinics.py:572` reads `name = (display_name or "").strip()`. The subsequent name checks reject blank/control characters and excessive length, but not duplicate names. At `:581–582`:

  ```python
  if typed is not None and any(r.subdomain == typed.subdomain for r in self._records):
      return Refused(ClinicRefusal.DUPLICATE_SUBDOMAIN)
  ```

  Commit likewise checks duplicate subdomains at `:701–705`, then stores `display_name=request.display_name,` at `:708`.
- Suggested change: Preserve human-readable setup while binding defaults to an unambiguous clinic identity, such as its visible host, or explicitly refuse ambiguous display-name resolution and provide a disambiguation procedure. Test two same-name clinics with equally named templates and different defaults; neither clinic’s baseline may authorise replacing text in the other.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): `template_defaults.json` is keyed by the clinic's HOST (unique — the registry refuses duplicate subdomains) instead of its display name (D4, Schema, Task P.1, Validation: two same-name clinics never share a default).
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

##### Practicality / feasibility / sequencing

**PR-LOW-022 — The proposed reminder union retains expired recordings**

- Plan section: Agreed Scope, Task 4.2, Custody validation.
- Materiality: build-affecting
- Why it matters: Class **(n)**, a helper’s actual purpose differing from its proposed use. Every existing reminder already belongs to `indexed-Unreviewed`. Including that set in the retention union makes membership sufficient to survive pruning after expiry, even when the session key and directory are gone. The Chrome banner can continue offering a recording that cannot be opened.
- Current plan text: `.cursor/plans/plan-cliniko-draft-write.md:39`: “SIMP-016 corrected: `ui/main_window.py` `prune_reminders` prunes to live ∪ indexed-Unreviewed ∪ key-exists.” Task 4.2 at `:701` repeats “prunes to live ∪ indexed-Unreviewed ∪ key-exists”.
- Evidence: `desktop/src/scribe_desktop/ui/main_window.py:686–688`:

  ```python
  for session_id in self.reminders.session_ids():
      if not (root / session_id / KEY_FILENAME).is_file():
          self.forget_unreviewed(session_id)
  ```

  `forget_unreviewed` removes both entries at `:679–680`:

  ```python
  self.reminders.remove(session_id)
  self._controller.forget_session_ref(session_id)
  ```

  `desktop/src/scribe_desktop/app.py:451–452`:

  ```python
  run_sweep(window.recovery_screen.protected_session_ids())
  window.prune_reminders()  # D6: an expired session's reminder goes too
  ```

  The banner consumes these retained entries at `desktop/src/scribe_desktop/ui/bridge.py:1140`: `sessions = reminders.sessions_for(record.clinic_id, target.note_id)`, and returns a banner when `if ref is not None:` at `:1143`.
- Suggested change: Preserve key-existence pruning of the reminder index. If SIMP-016 intends to prune the controller’s reference registry, name that separate operation and use live sessions plus still-valid indexed sessions after expired reminders are removed. Add a test proving a sweep-expired session loses both its reminder and reference while a recoverable indexed session retains them.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): the reminder index keeps its key-existence prune; SIMP-016 becomes a separate `prune_session_refs()` that drops refs neither live nor still-indexed (Agreed Scope, Task 4.2, Validation).
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

PEER-PLAN-ROUND-5 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 1; build-affecting 2 / record-only 0 / invalid 0).

### Round 6 — 2026-09-29 — cliniko-draft-write plan, independent cross-family codex plan peer-review (round 6)

- Round status: Closed (2 applied as plan amendments; verified 2 build-affecting / 0 record-only / 0 invalid)
- Source: Codex plan peer-review
- Materiality: 2 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: e509b56 + working-tree plan
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `.cursor/plans/plan-cliniko-draft-write.md` in full, including prior dispositions.
  - Scoped sections of `AGENTS.md`, `PLAN.md`, `docs/lessons.md`, `docs/design-system.md`, and `docs/security/{threat-model,data-flow-map,retention-schedule,intended-use}.md`.
  - Named symbols in `desktop/src/scribe_desktop/{cliniko_client,encounter,session,session_store,note,note_config}.py`, `config_defaults/template_profiles.json`, and `ui/{note,transcript,main_window,bridge,models}.py`.
  - Scoped portions of `scripts/probe-cliniko.py`, `desktop/tests/test_cliniko_client.py`, `desktop/tests/test_integration_no_sockets.py`, and `desktop/pyproject.toml`.
  - Supporting Recovery action and result handlers in `desktop/src/scribe_desktop/ui/recovery.py`.
- Finding verification: 8 candidates / 6 dropped / 0 downgraded
- Verification method: Static review only. No files written; no tests or builds run.
- Class coverage: Reviewed classes (a)–(q), including baseline and lookup identity, read/write/completion timing, success persistence and delivery, structural guarantees, cooldown producers, comparison representations, completion modes, optional context, practitioner procedures, referenced interfaces, warning propagation, refusal accuracy, and prune membership. The two retained findings concern an omitted asynchronous view-changing path and an ambiguous baseline key.

#### Findings

##### Practicality / feasibility / sequencing

**PR-MED-023 — Recovery processing can replace the transcript view during a write**

- Plan section: D2, D9, Tasks 4.1 and 5.2.
- Materiality: build-affecting
- Why it matters: Classes **(b)** custody and ownership across asynchronous operations, **(c)** success delivery, and **(g)** completion-mode routing. Start writing saved live session A, then use Recovery’s “Resume processing” for another unfinished session B. The recovery exclusion protects A’s identity, but permits B. When B finishes, its result clears A’s Note tab and replaces the transcript and completion callback while the controller still owns A. Checking A’s live session id therefore does not detect this view replacement. Automatic written-completion can clean up B’s current view; seen mode loses A’s Copy view and leaves a Complete callback for B. Starting B’s recovery first and clicking Write for A while recovery runs is also unguarded.
- Current plan text:
  - `.cursor/plans/plan-cliniko-draft-write.md:186`: “`MainWindow._on_review_requested` (the "Open for review" path; not a controller method) refuses on `is_writing`.”
  - Same line: “`MainWindow.is_writing` (true from the click until the last handler finishes) is read by `closeEvent` — the write-specific line BEFORE the generic busy branch — `note_screen.is_busy`, the Transcript row's `_update_controls`, and the bridge's pre-checks.”
  - `.cursor/plans/plan-cliniko-draft-write.md:780`: “`_finish_write` keyed by session id: record the outcome, `record_429`; then in auto mode `complete_written` with the reservation STILL HELD”.
- Evidence:
  - `desktop/src/scribe_desktop/ui/recovery.py:248`: `blocked = self._busy or bool(self._protected) or self._generation_blocked`
  - `desktop/src/scribe_desktop/ui/recovery.py:324`: `if info is None or self._busy or self._generation_blocked:`
  - `desktop/src/scribe_desktop/ui/recovery.py:361`: `self.recovered.emit(payload)`
  - `desktop/src/scribe_desktop/ui/main_window.py:1124`: `self.note_screen.clear()`
  - `desktop/src/scribe_desktop/ui/main_window.py:1128`: `self.transcript_screen.show_document(`
  - `desktop/src/scribe_desktop/ui/main_window.py:1130`: `on_complete=lambda: self._controller.complete_recovered(directory, crypto),`
  - `desktop/src/scribe_desktop/ui/main_window.py:1139`: `self._transcript_source = directory.name`
  - The existing generation path already supplies the two-way exclusion pattern: `desktop/src/scribe_desktop/ui/main_window.py:922`: `return self.recovery_screen.is_busy`; `:1394`: `self.recovery_screen.set_generation_blocked(active_bool)`.
- Suggested change: Explicitly make writing and Recovery resume mutually exclusive in both arrival orders. Refuse Write while recovery processing runs, and block/refuse Recovery resume while writing, including queued clicks. Retain the separate “Open for review” guard. Add tests proving the transcript source, completion callback, and saved-note view remain bound to A until its write handler finishes.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): D9 makes writing and Recovery's Resume mutually exclusive in both arrival orders (Write refused `recovery_busy` while recovery is busy; Recovery blocked while `is_writing` via the `set_generation_blocked` pattern, queued clicks included); Task 5.2 touches `ui/recovery.py`; Validation pins the view/callback binding; Task 5.1 gains `recovery_busy`.
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

##### Unstated assumptions

**PR-MED-024 — Option C’s slash-joined key can alias distinct template questions**

- Plan section: D4, Schema / Data Changes, Tasks P.1 and 3.2.
- Materiality: build-affecting
- Why it matters: Classes **(p)** non-unique safety lookup and **(a)** baseline identity confusion. Section and question names can both contain slashes. Joining them with an unescaped slash does not uniquely represent their pair: different partitions can produce the same key while both section names and both question names remain distinct. The duplicate-name refusal therefore does not address this collision. A default belonging to one question can classify clinician-entered text in another as an untouched scaffold and permit replacement.
- Current plan text:
  - `.cursor/plans/plan-cliniko-draft-write.md:194`: `{"<clinic host>": {"<template name>": {"<section name>/<question name>": "<scaffold text>"}}}`
  - `.cursor/plans/plan-cliniko-draft-write.md:181`: “The template match is name-based on (section index, section name, question name) between the profile's `group`/`field_label` and the note's own template”.
- Evidence:
  - `desktop/src/scribe_desktop/note_config.py:301`: `group: _LabelText`
  - `desktop/src/scribe_desktop/note_config.py:302`: `field_label: _LabelText`
  - `desktop/src/scribe_desktop/note_config.py:242`: `StringConstraints(min_length=1, max_length=MAX_CONFIG_LABEL_CHARS),`
  - `desktop/src/scribe_desktop/note_config.py:243`: `AfterValidator(_no_control_chars),`
  - The shipped configuration already uses slashes in both components: `desktop/src/scribe_desktop/config_defaults/template_profiles.json:34`: `"group": "Treatment/Management",`; `:47`: `"field_label": "Management/Advice",`.
- Suggested change: Preserve section and question names as separate fields, using nested objects or explicit records. Refuse ambiguous flattened keys rather than choosing a baseline. Add a test with distinct section/question pairs whose slash-joined forms coincide, verifying that neither question inherits the other’s default.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): `template_defaults.json` nests section name then question name as separate keys (never slash-joined); D4, Schema and Validation updated with the coinciding-pair test.
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

PEER-PLAN-ROUND-6 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 2 / LOW 0; build-affecting 2 / record-only 0 / invalid 0).

### Round 7 — 2026-09-29 — cliniko-draft-write plan, independent cross-family codex plan peer-review (round 7)

- Round status: Closed (1 applied as a plan amendment; verified 1 build-affecting / 0 record-only / 0 invalid)
- Source: Codex plan peer-review
- Materiality: 1 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: e509b56 + working-tree plan
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `.cursor/plans/plan-cliniko-draft-write.md` in full, including prior dispositions.
  - Scoped sections of `AGENTS.md`, `PLAN.md`, `docs/lessons.md`, `docs/design-system.md`, and `docs/security/{threat-model,data-flow-map,retention-schedule,intended-use}.md`.
  - Named symbols in `desktop/src/scribe_desktop/{cliniko_client,encounter,session,session_store,note,note_config}.py`, `config_defaults/template_profiles.json`, and `ui/{note,transcript,main_window,bridge,models}.py`.
  - Scoped portions of `scripts/probe-cliniko.py`, `desktop/tests/test_cliniko_client.py`, `desktop/tests/test_integration_no_sockets.py`, and `desktop/pyproject.toml`.
- Finding verification: 9 candidates / 8 dropped / 1 downgraded
- Verification method: Static review only. No files written; no tests or builds run.

#### Findings

##### Missing verification / rollback / migration

**PR-LOW-025 — Empty write targets can produce a false “draft written” result**

- Plan section: D2, D5, D7; Tasks 3.2–3.4; rendering and orchestration validation.
- Materiality: build-affecting
- Why it matters: Classes **(q)** set-membership rules and **(m)** reporting more than was established. A saved empty note, or one containing only intentionally unmapped content, can pass the proposed Write predicate while yielding no writable answers. Full-body mode can send unchanged content; partial mode can send an empty set. If an interrupted attempt records no answer digests, D5’s “every targeted answer” comparison succeeds vacuously, permitting `written` and automatic completion without establishing that any note content reached Cliniko. Downgraded from MED to LOW because the clinician has already ratified the local note; this does not demonstrate loss of unreviewed content.
- Current plan text:
  - `.cursor/plans/plan-cliniko-draft-write.md:179`: “the tab's `_write_ready` = `_copy_ready()` AND `binding.linked` AND not in flight AND no style job AND `provider_name` not `mock-…` (D10) AND the write record does not read `written`”
  - `.cursor/plans/plan-cliniko-draft-write.md:182`: “every targeted answer's normalised digest equals `digests` → `written` (no second PATCH, D6 applies)”
  - `.cursor/plans/plan-cliniko-draft-write.md:184`: “groups by `target_for`” and “never yields an `attestation_checkbox` target.”
- Evidence:
  - `desktop/src/scribe_desktop/note.py:690`:
    ```python
    note_sections: tuple[GeneratedSection, ...] = ()
    ```
  - `desktop/src/scribe_desktop/note.py:989`:
    ```python
    if not blocks:
        return NO_NOTE_CONTENT
    ```
  - `desktop/src/scribe_desktop/ui/note.py:2134`:
    ```python
    return self._copy_enabled and not saved.blocking_warnings()
    ```
  - `desktop/src/scribe_desktop/note_config.py:334`:
    ```python
    # silent. The shipped profile lists `consent` here: Template A's only
    # consent target is the attestation checkbox, which is never written.
    intentionally_unmapped: tuple[NoteSectionKey, ...] = ()
    ```
  - `desktop/src/scribe_desktop/note_config.py:378`:
    ```python
    return None
    ```
    This is `target_for`’s result for an unmapped section.
- Suggested change: Refuse Write with a named “no writable note content” reason when rendering yields no writable answers, before recording an attempt or dispatching PATCH. Require a nonempty recorded target set before reconciliation can establish `written`. Add cases for an empty saved note, an intentionally-unmapped-only note, and an unknown record with empty digests; none should announce a successful write or trigger write-driven completion.
- /fix decision: Applied (plan amendment)
- /fix notes: Applied 2026-09-29 (plan amendment): `nothing_to_write` refusal before any attempt when rendering yields no writable answer; reconcile requires non-empty recorded digests to establish `written` (D4, D5, Task 5.1, Validation).
- /fix date: 2026-09-29
- /fix applied by: Claude Code (planning session, Fable 5.1)

PEER-PLAN-ROUND-7 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 1; build-affecting 1 / record-only 0 / invalid 0).

### Round 8 — 2026-09-29 — cliniko-draft-write plan, independent cross-family codex plan peer-review (round 8)

- Round status: Closed — No new findings this round
- Source: Codex plan peer-review
- Materiality: 0 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: e509b56 + working-tree plan
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `.cursor/plans/plan-cliniko-draft-write.md`; scoped sections of `AGENTS.md`, `PLAN.md`, and `docs/lessons.md`.
  - Named symbols in `desktop/src/scribe_desktop/{cliniko_client,encounter,session,session_store,note,note_config}.py` and `config_defaults/template_profiles.json`.
  - Named symbols in `desktop/src/scribe_desktop/ui/{note,transcript,main_window,bridge,models}.py`; relevant Recovery controls.
  - Scoped portions of `scripts/probe-cliniko.py`, `desktop/tests/test_cliniko_client.py`, `desktop/tests/test_integration_no_sockets.py`, and `desktop/pyproject.toml`.
  - Cited sections of `docs/security/{threat-model,data-flow-map,retention-schedule,intended-use}.md` and `docs/design-system.md`.
- Finding verification: 5 candidates / 5 dropped / 0 downgraded
- Verification method: Static review only. No files written; no tests or builds run.

#### Findings

No verified new findings across coverage; practicality / feasibility / sequencing; unstated assumptions; simpler / safer alternatives; or missing verification / rollback / migration.

The verification filter dropped:

- Heading-boundary normalization: D4 already requires visible-text conversion that prevents adjacent tokens concatenating.
- Template-name collisions: the scoped evidence did not establish that Cliniko permits duplicate template names.
- Reconciliation against a changed profile: D4/D5 require a nonempty recorded target set and matching recorded digests; comparing only a surviving subset would violate that contract.
- Already-written automatic-mode retry ambiguity: D6 explicitly provides reacquisition through Complete after failed completion.
- Outcome-record persistence failure after HTTP 200: the durable `attempting` record and required reconciliation already preserve the recovery path.

PEER-PLAN-ROUND-8 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0; build-affecting 0 / record-only 0 / invalid 0).

## Tasks
Legend: 🟥 To Do · 🟨 In Progress · 🟩 Done. No task carries `[executor: premium-only]` (the whole plan is premium). Phases are `/execute-loop` boundaries in build order: each code phase ends with `/review-loop` + a cross-family codex pass sliced by file group (≤ 15 files a slice). Phase 2 is practitioner-gated and has no code. Every task defers to `Validation / Verification` unless it says otherwise. Task 5.1's dictionary is the ONE source of user-facing write strings; earlier tasks use its keys, never their own strings.

### Phase 1 — The client's one write method, the probe's test-write mode, the latch (security-foundational)
- [ ] 🟥 **Task 1.1 — Transport body, `DraftContent`, `write_draft_note`, `get_treatment_note_template`, public `note_state`.** Touches `cliniko_client.py` (`Transport.request` :228, `_Connection.request` :247, `HTTPSTransport.request` :316-339, `ClinikoCall` :439-490, `_interpret` :492, the module docstring :17-19), `encounter.py` (`_note_state` → `note_state`, `_link_id` → `link_id`, :369-393, unchanged behaviour), every transport fake listed in Files / Symbols (plus `test_ui_screens.py:843` `_NoTransport`, harmless), `desktop/tests/test_cliniko_client.py`. Behaviour: D1 — keyword-only `body: bytes | None = None`; the two admitted request shapes; `DraftContent` (pydantic, one field `content`, `extra="forbid"`) defined here; `write_draft_note(note_id, content: DraftContent) -> WriteAnswer` sending `Content-Type: application/json` and classifying on the STATUS LINE before any body read — a 200 is `WriteAnswer(written=True, note=<parsed or None>)` whatever its body does (PR-MED-005); the PATCH-only 422 read → `ClinikoRejected(categories)` per D11 (fixed categories reduced inside the handler, the error raised OUTSIDE it — the module's existing `_guarded` pattern — so `__cause__` and `__context__` are both `None`); `get_treatment_note_template(template_id)`; every other status as today. Acceptance: Validation's Client bullet; `TestGetOnly` renamed `TestMethods` with those assertions; the source-count and body-model tests. Includes its own verification; every fake updated in the same commit.
- [ ] 🟥 **Task 1.2 — `--test-write` and `--test-write-final` modes of `scripts/probe-cliniko.py`.** Touches `scripts/probe-cliniko.py` (docstring, argv guard :249-262, `run_test_write`, `run_test_write_final`), `desktop/tests/test_probe_cliniko.py`. Behaviour: Flow 4 exactly — inputs (email, note URL, key by `getpass`, the dummy patient's surname, the note id's last four digits; surname and digits compared to the re-read note and never printed); refusals unless `draft: true`, `finalized_at` null, not archived, patient = URL's, practitioner = key user's; what-it-will-do summary and a typed `yes`; the adversarial marker into ONE rich-text and ONE plain-text question chosen by printed position; re-read and per-question `equal` / `sanitised` / `rejected` plus untargeted-unchanged (questions 1, 2, 4); the template structure and default-text presence (question 3); the editor pause and marker-survival report (question 5); a SECOND marker pass that pauses BETWEEN its note GET and its PATCH ("now edit and save a different question in the open editor, then press Enter"), PATCHes the full re-read body, re-reads and reports whether that edit survived (question 6 — a `--partial` variant of the same pass sends only the targeted question and reports whether the untargeted edit and the other questions survived, answering question 2 as merge vs replace); restore only if the markers are the only difference, else `MARKER LEFT - delete it by hand in Cliniko` and exit 2. The `--test-write-final` leg refuses unless the note re-reads as final, PATCHes the marker, prints the status and the filtered 422 names; a 200 is printed as an alarm with the same instruction. Structure only in stdout. Acceptance: Validation's Probe bullet.
- [ ] 🟥 **Task 1.3 — `RateLimitLatch`.** Touches `encounter.py` (new `RateLimitLatch(clock)` with `cooling(clinic_id, now)` / `record_429(clinic_id, now)`; `RATE_LIMIT_COOLDOWN_SECONDS` moves here, re-exported by the bridge), `ui/bridge.py` (:303, :729-731, :819-823 — `_cooldown_until` replaced by the injected latch; the queue, `MIN_CALL_SPACING_SECONDS` and the QTimer untouched; constructor gains `latch`), `ui/main_window.py` (owns the latch; the checkout dispatch at :1182-1199 consults `cooling` and shows the existing rate-limited line instead of calling; re-dispatch when the row is reopened, as today; `_finish_reverify_task` :1223-1225 calls `record_429` for an `UnverifiedOffline(rate_limited)` result BEFORE `_start_waiting_reverification`, stale or not — PR-LOW-008), `app.py` (:423 injects the latch and its clock), `desktop/tests/test_ui_bridge.py`, `test_encounter.py`, `test_ui_encounter.py`. Behaviour: D13. Acceptance: Validation's Latch bullet.

### Phase 2 — The practitioner's test write and the decision it feeds (no code)
- [ ] 🟥 **Task P.1 — The practitioner runs the test write on clinic 1** (practitioner-owned; a normal terminal at the repo root; a note the practitioner opens on a DUMMY patient they create in their own clinic; the finalised leg on a second note of the same dummy patient, finalised by hand first). Done-when: the Done note answers all SIX questions with the printed structure pasted (for question 3 / Option C: the practitioner transcribes the scaffold text of every defaulted question from a PRISTINE note as Cliniko's editor shows it into `template_defaults.json`, keyed by the clinic's host (from the address bar) and the template's name as Cliniko shows it; the probe's output names the questions only), plus the finalised leg's status and categories. Clinic 2 stays deferred.
- [ ] 🟥 **Task 2.1 — Decide the typed-text default source, the body shape and the completion mode** `[decision]`
  - Options (default source, D4): A — the template GET's default answer text (preferred if question 3 shows the template carries it); C — a per-clinic `template_defaults.json` written by the practitioner from P.1's pristine-note structure (Schema / Data Changes). A Start-time snapshot is NOT an option (PR-HIGH-001).
  - Options (body shape, D4): partial — only the targeted sections/questions (preferred if question 2 shows Cliniko MERGES partial content: an UNTARGETED edit saved during the GET→PATCH window cannot be reverted); full — the re-read content with targeted answers replaced. In BOTH modes a targeted-question edit in the window is replaced (PR-MED-011) — the residue is recorded in Task 6.1 whichever is chosen.
  - Options (completion, D6): auto — `written` completes at once (only if question 5 shows the open editor cannot overwrite our draft); seen — the Note tab stays with Copy and the "press Complete once you can see it" line, and Complete runs `complete_after_write`.
  - Decide after: Task P.1's Done note.
  - Blocks: Tasks 3.2, 3.3, 3.4, 4.2, 5.2.

### Phase 3 — The Qt-free write module: rendering, match, record, orchestration
- [ ] 🟥 **Task 3.1 — `render_section_lines` and the target grouper.** Touches `note.py` (`render_section_lines(note, section, style, *, apparatus)`; the private blocks fold into it; `render_note` = title per style + lines with `apparatus=True`), new `draft_write.py` (`render_targets`, `to_cliniko_answer`), `desktop/tests/test_note.py`, `test_draft_write.py`. Behaviour: D7. Acceptance: Validation's Rendering bullet — capture the four-style fixture digests BEFORE touching `note.py`.
- [ ] 🟥 **Task 3.2 — Template match, the typed-text predicate, body construction, the importer pin.** Touches `draft_write.py` (`match_template(profile, template, note_content) -> Match | TemplateMismatch`, `note_has_text(note_content, baseline, match) -> bool`, `normalise_answer`, `answer_digests`, `build_body(note_content, match, answers, shape) -> DraftContent | AnswerUnreadable` — the first import of `cliniko_client` from this module), `desktop/tests/test_cliniko_client.py::TestConfinement` (:859-874 — importers become `["clinics.py", "draft_write.py", "encounter.py"]`, the docstring naming the docs it obliges), `note_config.py` (Option C ONLY: `load_template_defaults` fail-closed beside the other config loaders), `desktop/tests/test_draft_write.py` with fixtures shaped from Task P.1's printed structure. Behaviour: D4 as decided by Task 2.1 (default source A or C; body partial or full). Acceptance: Validation's Match bullet.
- [ ] 🟥 **Task 3.3 — `write.enc`.** Touches `session_store.py` (`write_write_record` / `read_write_record` beside `write_encounter` :866 / `read_encounter` :879, AAD `write:<id>`, atomic write + fsync), `draft_write.py` (`WriteRecord` model with `note_identity`, `reconcile(record, note_content, match, saved_note_identity) -> Written | Baseline | Uncertain`), `desktop/tests/test_session_store.py`, `test_draft_write.py`. Behaviour: D5's document and transitions; unreadable → `write_record_unreadable`; a `note_identity` mismatch → `Uncertain`. Acceptance: round-trip, fsync-before-return, corrupt-refuses, trailing-`attempting`-as-`unknown`, identity-mismatch-never-written, reconcile per class.
- [ ] 🟥 **Task 3.4 — The Qt-free orchestration.** Touches `draft_write.py` (`verify_note_for_write(call, request) -> VerificationResult + content` — hop 1's note GET applying `note_state`, no patient/booking GET; `fetch_template(call, template_id)`; `prepare_write(result, record, profile, note, style, clinics_subject) -> PreparedWrite | WriteRefusal` — the GUI-thread step: `writeback_context`, reconcile, `note_has_text`, `match_template`, `build_body`; `send_write(call, target, prepared) -> WriteOutcome` — hop 2, classifying by the HTTP answer only; the mock gate `mock_note`), `desktop/tests/test_draft_write.py` with a fake `ClinikoCall`. Behaviour: D3, D5, D8, D10. Acceptance: Validation's Orchestration bullet; no Qt import in the module (pinned).

### Phase 4 — Custody: the reservation, the accessor, completion after a write
- [ ] 🟥 **Task 4.1 — `reserve_write`, `with_write_custody`, the refusal map.** Touches `session.py` (`reserve_write` = `_reserve_custody_locked` + `_writing_id`; `WriteReservation.release`; `discard` and `start` check `_writing_id`; `with_write_custody(reservation, action)` mirroring `with_generation_custody` :1385; `begin_generation` :1201 refuses `write_pending` when the session's write record holds any attempt — read through the store under the lock), `ui/transcript.py` (`save_note` :746 refuses `write_pending` the same way; "Cancel review and regenerate" disabled with the line), `ui/models.py` (`SessionControllerLike` :543-672 gains both; the "a discard is completing" texts mapped to `write_in_flight`), `ui/main_window.py` (`_live_session_clinic` :906-915 extended so Replace key and Remove are refused for the writing clinic; `_on_review_requested` :755 refuses on `is_writing`), `desktop/tests/test_session_machine.py`, `test_live_session.py`, `test_ui_clinics.py`. Behaviour: D9 — one test per method in the refused set (`docs/lessons.md` 2026-08-12: an exhaustive consumer enumeration). Acceptance: Validation's Custody bullet, first five items.
- [ ] 🟥 **Task 4.2 — `complete_after_write` and SIMP-016.** Touches `session.py` (`complete_after_write(reservation)` per D6, under one lock — held reservation, `written`, `note_identity` equals the saved note's; `live_session_ids()`), `session_store.py` (`complete_session(..., remove_directory=True)`: verify → key → `rmtree` best-effort), `ui/models.py` (Protocol), `ui/main_window.py` (`prune_reminders` :682 UNCHANGED in its key-existence rule; a new `prune_session_refs()` called right after it drops every controller ref that is neither in `live_session_ids()` nor in `self.reminders.session_ids()` — the unlinked/failed refs SIMP-016 named — while an expired session, already forgotten by `prune_reminders`, loses both), `ui/transcript.py` (`complete_written(on_complete_written)` mirroring `on_complete` :833-854, emitting `closed("written")`; in seen mode the Complete button routes to `complete_after_write` when the record reads `written`), `desktop/tests/test_session_machine.py`, `test_ui_screens.py`. Behaviour: D6 in the mode Task 2.1 chose; SIMP-016 as corrected. Acceptance: Validation's Custody bullet, remaining items.

### Phase 5 — The desktop UI and the offline pins
- [ ] 🟥 **Task 5.1 — Microcopy dictionary.** Touches `ui/models.py` (`WRITE_LINES: Mapping[str, str]`, `write_line(key, **detail)`) and later `docs/design-system.md` (Task 6.1 copies it). Keys and lines, plain clinical English, no exclamation marks: `ready` "Write draft to Cliniko"; `checking` "Checking the note with Cliniko …"; `writing` "Writing the draft to Cliniko …"; `written_auto` "Draft written to Cliniko. Reload the note page in Chrome to see it, then review and finalise it there."; `written_seen` "Draft written to Cliniko. Reload the note page in Chrome; press Complete once you can see it there."; `written_done` "Draft written to Cliniko and this recording is complete. Review and finalise the note in Cliniko." (the terminal line after either completion mode); `not_saved` "Save the note first."; `unlinked` "This recording is not linked to a Cliniko note. Copy the note instead."; `mock_note` "This note came from the test provider and cannot be written to a chart."; `check_failed` "The note could not be checked with Cliniko just now (<reason>). Copy the note, or try again." — `<reason>` from a NEW typed `writeback_refusal_line(WritebackRefusal)` — its own exhaustive table in the `clinic_refusal_line` PATTERN (`clinic_refusal_line` itself formats Validate / Replace key / Remove and is not reused — PR-LOW-019) — for every `WritebackRefusal` name and from the existing `note_refusal_line` for every `NoteRefusal` name (so `note_final`, `note_archived`, `patient_mismatch`, `wrong_practitioner`, `answer_unreadable`, `consent_*`, `clinic_*`, `*_stale`, `context_changed` all resolve); `rate_limited` "Cliniko is rate-limiting this clinic. Try again in N s."; `note_has_text` "The Cliniko note already holds text. Copy the note and paste it in yourself."; `write_uncertain` "An earlier write may have reached Cliniko. Check the note there before copying anything." — and whenever the record holds an `attempting` or `unknown` attempt, EVERY other refusal line on the Note tab (`check_failed`, `rate_limited`, `not_taken`, `unlinked`, …) is PREFIXED by this sentence, so a failed retry never invites a bare Copy (PR-MED-017); `nothing_to_write` "This note has no content that maps to the Cliniko template, so there is nothing to write. Copy the note instead." (PR-LOW-025); `not_taken` "Cliniko did not take the draft (<cause>). Copy the note instead." — causes: template mismatch (<question>), rejected (<categories>), key rejected (validate it on the Clinics tab), note not found, no baseline; `record_unreadable` "The record of this recording's earlier write cannot be read, so its outcome cannot be checked. Look at the note in Cliniko before copying anything." (PR-MED-018); `unknown` "The write did not confirm. Nothing is lost - press Write again to check the note before anything is sent."; `write_in_flight` "A draft is being written to Cliniko. Wait for it to finish." (also the close-refusal line); `recovery_busy` "A recovered recording is still being processed. Wait for it to finish, then write.". Acceptance: a test enumerates `WritebackRefusal`, `NoteRefusal` and every `WriteOutcome`/refusal name and asserts each resolves to a line.
- [ ] 🟥 **Task 5.2 — The Note tab's "Write draft to Cliniko" and MainWindow's write wiring.** Touches `ui/note.py` (button beside Copy :569-574; `WriteBinding(session_id, linked)` set from `begin_review` / `show_saved_note` kwargs; `set_write_in_flight`; `_write_ready`; `write_requested = Signal(str)`; a click on the disabled button repeats the reason, design-system :389-392; `is_busy` reads in-flight), `ui/main_window.py` (`_on_write_requested`: `_lock_refusal()` → latch → `reserve_write` → `is_writing` → hop 1 `TaskThread` → `_after_hop1` (GUI: `prepare_write`, `with_write_custody` attempt) → hop 2 `TaskThread` → `_finish_write` keyed by session id: record the outcome, `record_429`; then in auto mode `complete_written` with the reservation STILL HELD (completion consumes it; on failure the handler releases), in seen mode release and show the line (Complete later re-acquires — D6); `closeEvent` gains the write-specific line before the generic busy branch; `_on_transcript_closed` treats `written` as completed and sets the success line after `refresh()`; `begin_review` / `show_saved_note` pass the binding), `ui/transcript.py` (`_update_controls` disables the row while writing), `ui/recovery.py` (blocked while writing via `set_generation_blocked`-style state; the Write click refuses `recovery_busy` while `recovery_screen.is_busy` — PR-MED-023), `ui/bridge.py` (`_start` :992, `discard`, `_open_review` :921 pre-check `is_writing` → existing codes), `desktop/tests/test_ui_screens.py`, `test_ui_encounter.py`, `test_unreviewed_review.py`, `test_ui_bridge.py`. Behaviour: Flows 1–3; D2, D3, D6, D9. Acceptance: Validation's UI bullet.
- [ ] 🟥 **Task 5.3 — Offline-contract pins for the write.** Touches `desktop/tests/test_integration_no_sockets.py` (the one-call-site AST pin), `test_ui_encounter.py` (mock and unlinked sessions never call the transport), `test_cliniko_client.py::TestConfinement` docstring. Acceptance: Validation's Offline bullet.

### Phase 6 — Docs
- [ ] 🟥 **Task 6.1 — The security-docs class rewrite.** Touches `docs/security/threat-model.md` (:11, :98-109 the custody order, :130-132, :363-368, :420-421, :1339-1614 the client section, :1568-1571, :1576-1585, :1599-1600, :2179-2180, review triggers :2186-2204), `docs/security/data-flow-map.md` (:11-16, :25-32, :44, flow 10 :258-265, flow 18 :536-605 retitled "Cliniko API reads and the one draft write", non-flows :733-736 and :766-781), `docs/security/retention-schedule.md` (:30, :46-47, :50, the `write.enc` row, :119-121 becomes built, the `template_defaults.json` row if Option C is chosen), `docs/security/intended-use.md` (:11-12, :19-28, :33-34, :49, :69-85), `docs/security/incident-process.md` (:15-19, :29-35, :63-66, the wrong-note incident, the stale "(Phase 1)" title), `docs/security/README.md` (:5), `docs/testing/shipping-gate.md` (:19, :40, :76 + "mock sessions never write"), `docs/design-system.md` (the write control, its states, Task 5.1's lines, the Note tab's button row), `PLAN.md` (:10, :46, :48, :116, :122, :135 "create" → "fill"/"write"; step 10 per the chosen completion mode), `AGENTS.md` (Current Status; pointers :84 the Chrome link now consults the latch, :85 an adopted session writes, :88 the Write button shares the one renderer, :95 three importers, `draft_write.py`, `write.enc`, the MainWindow write wiring), `scripts/probe-cliniko.py` docstring. Behaviour: D11's grep checklist returns zero stale hits; every claim states what the structure enforces and names the residue (Constraint 12: Cliniko's sanitiser may change formatting; the open editor may overwrite (if question 5 said so, and why the seen mode exists); after completion the only copy is in Cliniko). Acceptance: the checklist run recorded in the Done note; H4's docs slice.

### Phase P — The practitioner's live smoke
- [ ] 🟥 **Task P.2 — Live smoke on clinic 1** (practitioner-owned; scripted by the composer at the phase boundary; screenshots are the observation channel; each step names the exact on-screen line from Task 5.1). Steps: one consultation note written and reloaded in Chrome, completed per the chosen mode; a refused write on a note with typed text (type one word in Cliniko and save first); an unknown-outcome rehearsal (disable Wi-Fi after the click, reconnect, click again — expect a reconcile, no second draft); close refused mid-write; the Unreviewed path. Done-when: each step's line matches. Clinic 2 deferred.

### Hardening stage
- [ ] 🟥 **Step H: Hardening pass**
  - [ ] 🟥 H1: `/review-loop` to convergence over Phases 1–6 as ONE surface, with the cross-phase lenses custody → latch → record → UI → docs (`docs/lessons.md` 2026-09-18: per-phase convergence is not whole-surface convergence)
  - [ ] 🟥 H2: `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`
  - [ ] 🟥 H3: `/security-review` — log findings; same routing (the first write of a new session type is a named review trigger)
  - [ ] 🟥 H4: cross-family codex `/peer-review` sliced by file group — (a) client + `draft_write.py` + probe + tests, (b) custody + UI, (c) docs — re-checked to convergence; a fix that moves the plaintext or custody bound earns a fresh round (`docs/lessons.md` 2026-09-19)

## Retained Follow-Up Items
Use this section when the plan is in `Completed — Follow-ups Retained` state.

### Deferred — Actionable Later
- (none yet — populated at completion by mechanical review of the Planning Extraction Summary)

### Excluded — Revisit Only If Needed
- (none yet)

### Accepted Assumptions — Revalidate Later
- (none yet)

## Follow-Up Continuation Notes
- Next follow-up first: PLAN.md Phase 6 (the audit record) — it reads the write outcome that today dies with `write.enc`; and clinic 2's P.1 + test write + smoke when its key exists.
- Stays out of scope there: POST of a second note, a Chrome write state, appending to a filled note, automatic finalisation.
- Decisions that still apply: D1–D13 here and the safeguards plan's D2/D4/D9/D10-as-amended/D11/D13.
- Must not be rediscovered: the write's own note GET is its verification (never the checkout's or the bridge's result); the `attempting` state is on disk before the PATCH is dispatched; a 200 is never relabelled; the reconcile compares per-question normalised digests, never a whole-body hash; the only copy after completion is in Cliniko; the open Cliniko editor may overwrite a PATCHed draft (P.1 question 5); the venv `python.exe` is a launcher; `urllib` bypasses the host pin; no Cliniko call at startup or idle keeps the no-sockets legs at zero.

---
*Plan saved to: .cursor/plans/plan-cliniko-draft-write.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
*State-once convention: cross-section contracts live in Design Decisions (D1–D13) and Critical Constraints; every other section points to them.*
