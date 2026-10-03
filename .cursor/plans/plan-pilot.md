# Feature Implementation Plan
**Feature:** pilot
**Overall Progress:** `0%` (0 of 34 tasks)

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: `plan-installation.md` (PLAN.md Phase 7, installation half — Completed, Follow-ups Retained). This plan is the pilot half (PLAN.md Phase 7 bullets 1–3 and 6).
- Follow-up plans: None

## Goal
Run the pilot that PLAN.md Phase 7 requires before routine personal use, and build the three things it needs that do not exist yet:

1. **Shadow mode** — a per-recording mode in which the app drafts its note as usual but refuses, by name, to write it to Cliniko or let it be copied, so the practitioner's own note can be compared with the app's.
2. **A validation harness** — an offline batch run of the real pipeline over at least 50 synthetic or mock encounters, reporting text-free quality numbers against a pass rule ratified beforehand.
3. **Pilot governance** — a text-free pilot log, a findings register and a per-clinic exit gate.

Then the practitioner runs: validation (at least 50 encounters), 10 consented shadow consultations, 20 reviewed consultations at clinic 1, the clinic 1 exit gate, and — once clinic 2 grants Cliniko API-key permission — clinic 2's install, 20 consultations and its own gate. Routine use opens per clinic only when every high-risk finding is resolved or explicitly controlled (PLAN.md L165).

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable 5.1 (`claude-fable-5-1`); executor Opus-class through `/execute-loop` (cross-family peer codex `gpt-6-astra`); tier-gap dosing applied (design decisions, edge-case inventory, schema contracts and per-task acceptance criteria locked). Every Phase P step, the harness runs and every check of installed state are run by the PRACTITIONER from a normal terminal or Explorer, never by an agent shell (`docs/lessons.md`, MSIX).

Planning sources: `plan-installation.md` "Follow-Up Continuation Notes" (the practitioner's decisions of 2026-10-02), the approved Plan Mode source of 2026-10-04 (decisions D-A, D-B, D-C and the Step 3.5 dispositions), PLAN.md L158–221, and the `/review-plan` re-probe at `1be6fd8`.

### Agreed Scope (Build Now)
- Shadow mode covering EVERY recording started while the setting is on (practitioner, 2026-10-04 — widened from "linked recordings" so a desktop-started recording cannot be copied into Cliniko): Write draft, every Copy of note text and Past sessions' "Copy saved note" refused by name; the note body display-only; no phrase or shorthand learning from a shadow Save (practitioner, 2026-10-04).
- Audit row v2 (`mode`, `app_version`), encounter record v2 and Past-sessions label v2, each with upgrade-on-read and two-way tests.
- The app version shown on the Status tab; the build becomes 0.2.0.
- The validation harness, its metrics, the text-to-speech set builder, about 40 synthetic scripts, and its documentation.
- Governance documents in `docs/pilot/`, the consent sheet's pilot paragraph (`patient-info-v2`), and the security documents updated for all of the above.
- The role-play recording set (practitioner-profile Task 6.1), which also closes speaker measurement (Phase 3A Task 2.3 / profile 6.2), decision D-S1 and the Task 9.1 quality run.
- The practitioner runs and the per-clinic exit gates (Phase P), including note-learning Task P.2 and clinic 2's owed safeguards and draft-write smokes.

### Deferred — Actionable Later
- In-app, content-free timing metrics (transcription time, review time) in the audit row.
  - Why deferred: the pilot log and rubric R6 already record review minutes by hand (practitioner, 2026-10-04: Defer).
  - Intended future outcome: timing columns in the audit CSV export.
  - Relevant files / subsystems: `audit.py`, `transcription.py`, `ui/note.py`.
  - Dependencies / prerequisites: audit v2 (Task 1.3).
  - Recommended next action: revisit at the clinic 1 exit gate.
  - Risk if deferred: minor: hand timing is coarse but sufficient for 50 consultations.
  - Revisit by: the clinic 1 exit gate (Task P.6), or earlier if hand timing proves unreliable in the shadow runs.

### Excluded — Revisit Only If Needed
- Shadow state shown in Chrome's side panel.
  - Why excluded: it needs a protocol change (`LiveState` is `extra=forbid`) and an extension reload on every computer; the desktop app shows the state and names the refusal (practitioner, 2026-10-04: Accept).
  - When to revisit: if the missing indicator causes confusion in the shadow runs.
  - Relevant files / subsystems: `protocol.py`, `protocol/fixtures/`, `extension/src/panel-view.ts`.
  - Recommended next action (if any): none.
- A new Cliniko read to fetch the practitioner's own note for an automatic comparison.
  - Why excluded: decided 2026-10-02 — the comparison is by hand on the rubric; the offline contract admits no new call.
  - When to revisit: never for the pilot.
  - Relevant files / subsystems: `cliniko_client.py`.
  - Recommended next action (if any): none.

### Accepted Assumptions — Revalidate Later
- Everyday clinical use of the installed app, with Cliniko writes, continues during the pilot build and runs (D-A, practitioner 2026-10-04).
  - Why accepted for now: the practitioner's standing decision; every note is reviewed and finalised in Cliniko by the clinician.
  - Risk if assumption becomes false: a quality defect the validation run would have caught reaches a reviewed draft before the gate.
  - Trigger for revisit: any high-risk finding in the register (Task 3.1), or a failed validation run (Task P.3).
  - Recommended next action: on a trigger, turn shadow mode on for everyday use until the finding is resolved or controlled.
- Rolling back below 0.2.0 with unfinished recordings (practitioner 2026-10-04: Accept with a rule).
  - Why accepted for now: shadow mode is a user setting, not an enforced control; a downgrade guard would touch the installer.
  - Risk if assumption becomes false: an older build treats a shadow recording awaiting recovery as unlinked (Copy allowed) and cannot open an Unreviewed recording made on 0.2.0.
  - Trigger for revisit: any rollback below 0.2.0.
  - Recommended next action: the rule in `docs/release/pilot-builds.md` (Task 3.4) — finish or discard every recording first.
- A second real person is available for about 10 role-plays, and a third voice for one (D-C).
  - Why accepted for now: practitioner confirmed 2026-10-04.
  - Risk if assumption becomes false: speaker measurement, D-S1 and the 9.1 run stay open; the validation set falls to synthetic scripts only (at least 50 are then needed from text-to-speech).
  - Trigger for revisit: Task P.2 cannot be scheduled within two weeks of the 0.2.0 install.
  - Recommended next action: author 10 more synthetic scripts and run P.3 without the role-plays.
- At least two usable Windows text-to-speech voices are installed on the developer computer.
  - Why accepted for now: not checkable from an agent shell with authority; Task 2.5 enumerates and refuses clearly.
  - Risk if assumption becomes false: one voice for both roles weakens the speaker-separation part of the synthetic set.
  - Trigger for revisit: Task 2.5's enumeration reports fewer than two.
  - Recommended next action: install a second Windows voice (Settings, Speech), or separate roles by rate and pitch and say so in the report.

### Key Design Decisions
- See `Design Decisions` (D1–D13); each still applies to follow-up work unless it says otherwise.

## Key Findings

All paths are under `desktop/src/scribe_desktop/` unless they start with another folder. Line numbers are as of `1be6fd8` (2026-10-04).

### Files / Symbols Involved
**Shadow mode and schemas**
- `session.py`: `RecordingSession` (:259, frozen, `extra=forbid`); `SessionController.start` (:785), its `audit.begin` call (:842–848), `encounter.enc` written in `_start_locked` (:884–889); `adopt_queued` (:1523–1536).
- `encounter.py`: `EncounterRecord` (:188–205, `schema_version: Literal[1]` at :195); `from_bytes` raises `EncounterUnavailable` (:208–215); the three-caller rule for `read_encounter_record` (:236–243).
- `ui/session_screen.py`: `on_start` (:314), `start_linked` (:330), `_start` (:350–389; the controller call at :367). Linked starts arrive from `ui/bridge.py:1071`.
- `ui/main_window.py`: `StatusPanel` (:223–283) and the developer-writes checkbox (:272–304); recovery checkout (:1492–1503); `_open_adopted` builds a fresh `EncounterRecord` (:1107); `show_saved_note` (:1116); `keep_label_for` (:1723–1763); `begin_review` (:1786); `_on_write_requested` (:1895) and its pre-send check (:1987).
- `draft_write.py`: `WriteRefusalName` (:1055–1067, 11 names); `dev_build_writes_off` (:1070); `refuse_before_read` (:1158); the one send (:1333).
- `ui/models.py`: `WRITE_LINES` (:321–416); `WRITE_UNCERTAIN_PREFIXED` (:426–445); `write_refusal_line` (:592–616); `write_control` (:729).
- `ui/note.py`: `_place_note_text` (:248–264); `_NotePanel.copy_selection` (:284), keyboard copy (:293–296), `build_context_menu` (:299–314); `_copy_note` (:2187); `_copy_ready` (:2201–2223); selectability keyed on it (:2231–2238); Write's "saved" derived from it (:2285).
- `past_sessions.py`: `KeepLabel` / `keep_label` (:193–225); `UNKNOWN_LABEL` (:206); `PastSessionLabel` (:228–236, `Literal[1]`); `_decode_label` (:820–823); `PastSessionSettings` (:930).
- `ui/past_sessions.py`: `_copy_reason` / `on_copy` (:472–496).
- `audit.py`: `AuditRow` (:271); `_version_first` (:297–304); `_decode` (:328–344, returns `_NEWER` for a higher version); `AuditLog.begin(session_id, *, consent, context, user_id, started_at)` (:542–550); `CSV_COLUMNS` (:1011–1035); `_csv_values` (:1055–1084).
- `logging_setup.py`: `_PAYLOAD_SIGNATURES` (:73).
- `note_config.py`: `DevSettings` (:1056–1105, `config\dev.json`) — the model for pilot settings; `_write_config_file`.
- Version: `__init__.py:3` (`__version__`), `desktop/pyproject.toml:7`, `scripts/build-release.py:163`, the extension manifest, `package.json` and its lock file (pinned equal by `tests/test_install_layout.py:866–881`).

**Harness**
- `transcription.py`: `transcribe_session` (:1175; needs an encrypted store with a 16 kHz header, writes `transcript.enc` itself); `resolve_whisper_model` (:930, falls back silently from `medium` to `small`); `TranscriptWord.uncertain` / `.probability` (:311–312).
- `note.py`: `normalise_token` (:246), `content_tokens` (:256); `NoteAssertion` (:445) with `note_span.provenance` and `source_coords`; `NoteProposal` (:541); `ExtractiveNoteProvider` (:1598); `ProposalResolution` (:2329); `compose_draft` (:2357, runs no checks — the enforced order is stated at :2378); `finalise_note` (:2471, calls `check_note` at :2603).
- `note_check.py`: `check_note` (:1686); warning codes — errors `source_coords_invalid`, `reconstruction_mismatch`, `contradiction`, `unconfirmed_proposal`, `autofill_trigger_absent`, `role_unconfirmed`; review `low_confidence_source`, `contradiction_low_confidence`, `dose_mismatch`, `laterality_mismatch`, `clinician_asserted`, `mapping_drop`, `high_risk_omission`, `style_fallback`; `_StructuredClaim` (:547).
- `note_fill.py`: `config_decisions` (:359). `ui/note_review.py`: `build_resolutions` (:148, Qt-free).
- `ui/models.py` (Qt-free): `_extractive_provider_from_config` (:2755, private); `build_prose_stage` (:3336).
- `note_config.py`: `load_note_config(config_root=None)` (:911, :962) — with no argument it reads the user's own config.
- `speaker_eval.py`: `read_wav_pcm` (:296); custody helpers `_write_store`, `_attempt_all`, `_remove_tree`, `_probe`, `_raise_if_residue`, `_destroy_temporary_store`, `_ReplayProvider`, `_transcribe_in_temporary_store` (:874–1045); `render_report` (:1163); `main` (:1390).
- `benchmark.py`: `apply_offline_env` (:137), `assert_offline_env` (:146), `generate_speech_sample` (:428–459).
- `desktop/tests/sapi_fixture.py`: `resample_wav_to_pcm16` (:34, PyAV), `synthesize_speech_wav` (:56–72, default voice only; SAPI writes 22050 Hz).
- `install_layout.py`: `models_root()` (:213). `desktop/tests/conftest.py`: `pinned_models_root` (:153), `real_ml_models` (:126).

### Codebase Integration Notes
- **Shared helpers across phases:** `speaker_eval`'s temporary-store helpers stay where they are and gain public names (Task 2.1) for the harness — its tests replace `SessionCrypto`, `_probe`, `delete_session_key` and others directly on that module (`test_speaker_eval.py:1017, 1088, 1138, 1191, 1221, 1318`), so moving them would silently disarm those failure injections; the pilot settings accessor (Task 1.1) is read by the Start funnel and the Status tab only; `SessionMode` (Task 1.2) is the one type the write refusal, the Copy refusal, the audit row and the Past-sessions label all consume.
- **Every way note text leaves the app:** the clipboard only through `_place_note_text` (callers: `copy_selection`, `_copy_note`, `ui/past_sessions.on_copy`); Cliniko only through `draft_write.py:1333`; a drag of the selection is Qt's own; and the inline line editor (`_LineEditor`, `ui/note.py:233`, created at :1730 with the line's text) has Qt's native Copy, Cut and context menu, which bypass `_place_note_text`. No other explicit `clipboard()`, `QMimeData` or `QDrag` use exists in `src`.
- **Every place a session is rebuilt:** recovery checkout, `adopt_queued`, `_open_adopted` (constructs, does not read) and the reminder rebuild (ids only — needs no mode). `begin_review` and `show_saved_note` receive no session mode today.
- **What an older build does with newer data:** an audit row reads as `_NEWER` (updates fail quietly and are counted; Start is refused only for a duplicate id); a label fails validation, the entry lists as unreadable and Copy fails closed; an encounter record raises `EncounterUnavailable` — recovery treats it as unlinked (Write refused, Copy ALLOWED), `adopt_queued` refuses `consent_unavailable`, the sweep and listing never decrypt. None refuses Start.
- **Tests that will fail when the change lands, by design:** `test_write_lines.py:150` (exact `WRITE_LINES`), `:268–279` (the unprefixed set), `:286–293` (any line containing "copy" must be prefixed); iterations over `WriteRefusalName` (`test_write_lines.py:438`, `test_draft_write.py:1655/1674`, `test_audit.py:209–211`); `test_audit.py:878–892` (CSV header), `:153–164` (every string field constrained), `:166–176` (forbidden field-name words), `:178–183` (tripwire drops every rendering), `:431, 706, 710–711` (use `schema_version: 2` as "newer"); the `read_encounter_record` call-count spies (`test_ui_encounter.py:206–233/340`, `test_unreviewed_review.py:169–176/753/798–805`, `test_ui_models.py:317`, `test_session_machine.py:2446`); `test_speaker_eval.py:1064, 1107, 1164, 1192, 1293` patch `speaker_eval.shutil` / `tempfile`.
- **Chrome:** no write, copy or refusal code crosses the protocol; a new refusal name needs no protocol or extension change.
- **Harness gaps found by the re-probe:** no word-error-rate or edit-distance code exists; no non-UI policy resolves proposals or chooses the clinician speaker; the extractive note only quotes the transcript, so "unsupported" must be measured against the script, not the note's provenance; `TranscriptWord.uncertain` is set for every number and name-like word, so the uncertainty tally counts `low_confidence_source` warnings instead; DPAPI custody makes the harness Windows-only.
- **Recorded timings:** whisper `medium` real-time factor about 0.6 (0.63 on the installed build); prose about 6 s per section.
- **Gotchas (`docs/lessons.md`):** agent shells are MSIX-virtualised; a test must inject host state through its seam in both directions; a corrupt pywin32 `gen_py` cache breaks the SAPI fixture; "no X can escape" guards confine the surface rather than enumerate spellings; a docs claim states only what the structure enforces.

### External / API Findings
- None. No new network call; the Cliniko client is untouched.

## Planned Workflow Summary

### Flow 1 — A shadow consultation
- The practitioner ticks "Shadow mode (pilot)" on the Status tab. The Session tab says new recordings are shadow recordings.
- They obtain consent with the v2 sheet, tick the consent box and Start (from Chrome on the Cliniko note, or on the desktop). The mode is fixed for that recording at Start.
- The app records, transcribes and drafts as usual. On the Note tab the practitioner decides proposals, acknowledges warnings and scores R1–R6 by hand at the rubric's scoring point, then Saves and Completes. Write draft and Copy are disabled with a named reason; the note text cannot be selected; the Save teaches the app no phrase or shorthand.
- The practitioner writes their own note in Cliniko as they always have, and enters the scores and a comparison line in the pilot log (no text, no ids).
- The kept Past-sessions entry is marked as a shadow recording; "Copy saved note" is refused for it.

### Flow 2 — The validation run
- On the developer build, from a normal terminal, the practitioner builds the synthetic set (text-to-speech WAVs from the repo's scripts) and adds the role-play WAVs.
- `scripts/run-validation.py <set-folder> --config <config-folder>` runs each encounter through transcription, note composition, the declared proposal policy and the checks, in a temporary encrypted store destroyed key-first.
- It prints a text-free report: per-encounter and total word error rate, per-fact verdicts, the unsupported-line, omission and uncertainty tallies, the model names, commit and models-manifest hash, and pass or fail against the ratified rule.
- Failures become findings in the register.

### Flow 3 — A reviewed pilot consultation
- Shadow mode off. The consultation runs as everyday use does now; the audit row records mode `normal` and the app version.
- After finalising the note in Cliniko the practitioner adds one line to the pilot log (date, clinic, rubric scores, minutes, findings count).

### Flow 4 — A finding and the exit gate
- Anything wrong-side, wrong-dose, negation-flipped, cross-patient, or a privacy or custody event goes into the findings register with a severity and a status.
- At 20 reviewed consultations the exit gate is read per clinic: every high-risk finding resolved or explicitly controlled, the validation and shadow results recorded, the practice documents independently reviewed. The practitioner signs the gate line; routine use opens for that clinic.

## Design Decisions
- **D1 — Shadow mode is a per-recording mode fixed at Start, covering every recording started while the setting is on.** Because a setting read at click time could change mid-review, and a desktop-started recording left copyable could still be pasted into Cliniko.
  Alternatives considered: linked recordings only (the 2026-10-02 wording; rejected 2026-10-04 by the practitioner); a global live switch (rejected: a recording's treatment would change under it).
- **D2 — Shadow mode is a user setting, not an enforced control.** `config\pilot.json` is user-writable, like `config\dev.json`. The threat model says so and names the residue.
  Alternatives considered: a machine-wide or signed setting (rejected: single practitioner, unsigned build; adds an installer surface for no pilot benefit).
- **D3 — Fail closed on unknown.** A missing `pilot.json` means shadow off; a present but unreadable one means shadow ON, named on the Status tab. A rebuilt session whose mode cannot be read is treated as shadow. `UNKNOWN_LABEL` is shadow.
  Alternatives considered: unreadable means off (rejected: a corrupt file would silently re-enable Copy and Write during the shadow runs).
- **D4 — Write is refused through the existing path.** `shadow_session` joins `WriteRefusalName` and is checked in `refuse_before_read` and `write_control` beside `dev_build_writes_off`, so no request is made and the attempt is recorded like any refusal. Its on-screen line does not contain the word "copy".
  Alternatives considered: hiding the Write button (rejected: a refusal with a reason is the app's convention, `docs/design-system.md`).
- **D5 — Copy is refused by a separate shadow reason, never through `_copy_ready`.** Write derives "saved" from `_copy_ready`, so reusing it would show "not saved". The shadow reason gates the Copy button, `copy_selection` (keyboard and context menu) and selectability, so the note body is display-only and a drag is closed too; the inline line editor, whose Qt-native Copy and Cut never pass through `_place_note_text`, has those two actions and drag refused while editing stays available.
  Alternatives considered: gating only `_place_note_text` (rejected alone: it leaves the selection draggable; it is still gated as the last line).
- **D6 — Schema upgrades happen on read, and the older build's behaviour is accepted with a rule.** Audit v1 rows are upgraded in `_decode` before validation (mode `normal`, no app version); label v1 reads as not-shadow; encounter v1 reads as `normal`. Rolling back below 0.2.0 requires finishing or discarding every recording first (Accepted Assumptions).
  Alternatives considered: an installer downgrade guard (rejected by the practitioner 2026-10-04).
- **D7 — `app_version` is pattern-constrained** (`digits.digits.digits`) and optional (absent on upgraded v1 rows); `mode` is an enum. Both are flat tokens and need no new log-tripwire signature; the task states this in the code comment and the threat model.
- **D8 — The harness measures against the script.** Each encounter's JSON carries reference lines and expected facts. One word-level alignment between the script's reference tokens and the transcript's words (the same one that yields the word error rate) carries everything: an "unsupported clinical line" is a note line containing a side, number, dose or negation word that the alignment marks substituted or inserted; each expected fact maps to exact transcript words, and an omission warning counts for a fact only when one of those words is itself an uncovered high-risk word behind that warning. Nothing is decided per segment. The exact contract is Task 2.3's. Word error rate is an in-repo edit distance over `note.normalise_token`.
  Alternatives considered: counting from the note's provenance (rejected: near zero by construction for the extractive provider); adding `jiwer` (rejected: a new dependency for forty lines of code).
- **D9 — The harness declares its policies and inputs.** Proposals: confirm all (through `ui/note_review.build_resolutions`); because that policy confirms what a clinician might decline, the checker's own contradiction and mismatch warnings on the finalised note count against the encounter (Task 2.3's checker tally). Clinician speaker: from each encounter's timed label track (hand-made for role-plays, builder-emitted for synthetic ones), aligned to the diarised segments by `speaker_eval.align_segments`; no mapping = a failed encounter. Config: an explicit `--config` folder, never the user's own. Model: `medium` required; a fallback to `small` is refused unless `--allow-small`, and the report names the model either way. It runs only on the developer build and writes no audit row and no Past-sessions entry.
- **D10 — One recording set serves four uses.** The role-plays are recorded live through the app (the 9.1 quality run) and captured in parallel as labelled 16 kHz WAVs (speaker measurement, D-S1, the harness). They are mock content with a second real person. Their retention is decision task 3.6.
- **D11 — Consent sheet v2, practitioner sign-off, independent review at the gate** (D-B). The app's consent tick text (`consent-v3`) is unchanged: the patient-facing change is the comparison use, which the sheet and the practitioner's script carry.
- **D13 — A shadow recording teaches the app nothing.** A shadow Save adds no learned phrase or learned shorthand and replaces no learned wording, because learned wording is global and would reappear in a later normal note that can be written to Cliniko. Demotions still apply (they only make the app more cautious). The refusal is named on the Note tab.
  Alternatives considered: keep learning and name it a residue (rejected by the practitioner 2026-10-04); carry shadow provenance through every learned rule (rejected: far more surface for ten consultations).
- **D12 — Routine use opens per clinic.** Clinic 1's gate does not wait on clinic 2's Cliniko permission. The 20 consultations per clinic count only on the pilot build, after the validation and shadow runs (D-A).

## Schema / Data Changes
| Store | Change | Reading older data | Older build reading newer data |
|---|---|---|---|
| `config\pilot.json` (new) | `shadow_mode: bool` | absent = off | file ignored (unknown to it) |
| `sessions\<id>\encounter.enc` | `EncounterRecord` v2: `mode` (`normal` / `shadow`) | v1 = `normal` | `EncounterUnavailable`: recovery treats as unlinked (Copy allowed), `adopt_queued` refuses |
| `audit\YYYY-MM\<id>.enc` | `AuditRow` v2: `mode`, `app_version`; two CSV columns | v1 upgraded in `_decode`: `normal`, no version | `_NEWER`: updates fail quietly, Start unaffected |
| `past_sessions\<id>\label.enc` | `PastSessionLabel` v2: shadow flag | v1 = not shadow | entry unreadable; Copy fails closed; sweep keeps it |

No change to the protocol, the transcript, the note or `write.enc`. The harness's only store is a temporary encrypted session folder destroyed key-first at the end of each encounter.

## Config / Environment / Deployment Impact
- No environment variables and no new runtime dependency (pywin32 and PyAV are already present).
- Version 0.2.0 in every place `tests/test_install_layout.py:866–881` pins equal; a CI `Release` run produces the build of record, recorded in `docs/release/pilot-builds.md` and verified by attestation and hash before install. The model pack is unchanged, so only `setup.exe` is needed for the upgrade.
- After the upgrade: reload the extension and fully restart Chrome (the manifest version changes; the protocol does not).
- Rollback rule: finish or discard every recording before installing a build older than 0.2.0.
- The harness, the set builder and `scripts/run-validation.py` are developer-build tools; the release build does not ship the scripts or the validation set.
- Role-play WAVs and the filled pilot log never enter the repository.

## Critical Constraints
1. **No fourth `read_encounter_record` caller.** The mode travels with the records the three authorised callers already read, and through `_open_adopted`'s construction.
2. **The shadow refusal never goes through `_copy_ready`,** and the audit upgrade happens in `_decode` before `AuditRow.model_validate` (both were traps in the first draft).
3. **Every path that carries note text out is gated in shadow mode:** the Write refusal, the Copy button, keyboard and context-menu Copy, selectability, `_place_note_text`, the inline line editor's native Copy, Cut and drag, and Past sessions' Copy. Nothing a shadow Save writes outlives the session except its Past-sessions entry and audit row: no learned phrase, rule or wording (D13). A new exit path added later must be gated too; the test enumerates the callers of `_place_note_text`, every widget class that can hold note text, and the one send.
4. **An audit row stays content-free by construction:** every new string field is pattern- or enum-constrained; no field name contains patient, text, audio, display or words.
5. **Custody is unchanged:** no path destroys a session key while a worker may hold plaintext; the harness's temporary store is torn down key-first with the fail-closed probe, exactly as `speaker_eval` does.
6. **The offline contract is unchanged:** the harness applies and asserts the offline environment; nothing in this plan adds a network call or an importer of the Cliniko client.
7. **Reports, the pilot log template, the findings register and the scoring sheets are text-free:** counts, yes/no, ids of synthetic encounters only — never a transcript or note line, a name, or a real session id.
8. **Only mock or synthetic content is stored outside app custody.** A real consultation is never exported to WAV or fed to the harness.
9. **Tests never touch real host state:** pilot settings, models root, the clipboard, SAPI voices and the app version are injected through seams, tested in both directions; nothing verified from an agent shell counts for installed state.
10. **Production identities, the developer channel split and the release process are untouched** (installation plan C2, C8).
11. **Documents claim only what the structure enforces** and name residues; the practice documents keep their review banner, use plain English, and cite every state the earlier research covers.
12. **Enforcing controls are not widened** (the refusal filter, the connective allow-list, Check 2's severity contract). A harness failure is a finding, not a reason to tune a gate.

## Validation / Verification
**Suites (composer-run on this host, `verify=composer`):**
- `desktop/`: `ruff check . && mypy && pytest`. Baseline at `1be6fd8`, 2026-10-04, agent shell: ruff "All checks passed!"; mypy "no issues found in 59 source files"; pytest "5912 passed, 9 skipped" in 3 min 36 s. Expected after each phase: ruff and mypy clean; pytest with no failure, the count rising by the new tests.
- `extension/`: `npm run qa` — expected unchanged (only the version strings move); not re-run at planning time.
- A pre-existing SAPI failure is checked against the `gen_py` cache before blaming a diff (`docs/lessons.md`).

**Per-phase live smokes (practitioner, developer build, normal terminal):**
- Phase 1: with the installed app closed, run the developer build; tick shadow mode; record one desktop mock; confirm the Session line, the refused Write and Copy with their wording, the unselectable note, the marked Past-sessions entry, and that typing over a line and saving teaches nothing (the Practitioner tab's learned lists are unchanged); untick and confirm a new recording is normal while the earlier one stays shadow.
- Phase 2: `scripts\build-validation-set.py` on three scripts, then `scripts\run-validation.py` on them; report the printed table and that no temporary folder remains.
- Phase 3: read-through of the pilot documents and consent sheet v2.

**Installed-state checks** belong to Task P.1 and count only when run by the practitioner.

**Completion criteria:** Phases 1–3 and H built and converged; 0.2.0 recorded as a build of record; P.1–P.6 recorded; clinic 1's gate signed. Task P.7 may remain open as a retained follow-up if clinic 2's permission has not arrived (the plan then closes as Completed — Follow-ups Retained).

## Deferred / Out of Scope
Owned by other plans and NOT re-deferred here (their own entries carry the risk tags and triggers):
- An enforced machine allow-list, and code signing — `plan-installation.md` Deferred (security; before a second clinic computer or commercialisation). Clinic 2's computer is set up under Task P.7 with the unsigned, attested build, as the installation plan decided.
- Passphrase-protected backup and restore of Past sessions — `plan-installation.md` / `plan-privacy-professional-controls.md` (correctness; before Past sessions is relied on as part of the health record). A likely next plan after the clinic 1 gate.
- A larger PortAudio input buffer — `plan-installation.md` Retained (first `status_input_overflow` in a log). A pilot finding of that kind re-opens it.
- Three-or-more-speaker labelling beyond decision D-S1, and diarisation tuning — `AGENTS.md` Known Issues; measured by Task P.2, decided there, built (if at all) in a later plan.
- Phase 3B (a generative note model) and its validation gate — PLAN.md L110. The harness and the rubric are written so they can be re-used for it.
- Commercial-path work (organisation accounts, TGA scope, selling to other practitioners) — PLAN.md L219–221, after a successful pilot.
- The nine deferred simplification and security items of the safeguards plan (SEC-008, SIMP-007 … SIMP-016) — untouched unless a task here edits the same lines.

True non-goals for this plan: any automatic comparison with the practitioner's own note; any export of a real consultation; shadow state in the Chrome panel (Excluded, above).

## Current State / Handoff Note
- Last completed step: Planning complete (hardened by `/review-plan` 2026-10-04; code facts re-probed at `1be6fd8`)
- Current in-progress step: None
- Immediate next action: Task 1.1 via `/execute` or `/execute-loop` (Phase 1). The cross-family plan peer loop ran 2026-10-04 (5 rounds, 8 findings, all applied; cap reached — see Review History). Task 2.3's metric contract drew a new finding in each of rounds 2–5, so give it a focused review when Phase 2 is built and before decision 3.5 is ratified.
- Open blockers / open questions: clinic 2's Cliniko API-key permission (blocks only Task P.7); a second person for the role-plays (Task P.2); an outside reviewer for `docs/practice/` (Task P.6).
- Last plan sync: 2026-10-04

## Review History
- 2026-10-04 round 1: 0 CRIT / 1 HIGH / 2 MED / 0 LOW; skew=none; action=amend-plan (plan peer-review; all three applied)
- 2026-10-04 round 2: 0 CRIT / 1 HIGH / 1 MED / 0 LOW; skew=none; action=amend-plan (plan peer-review; both applied; one practitioner decision — no learning in shadow)
- 2026-10-04 round 3: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=fix-induced; action=amend-plan (plan peer-review; applied — the metric contract moved from per-segment to word-level alignment)
- 2026-10-04 round 4: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=fix-induced; action=amend-plan (plan peer-review; applied — `warned` now needs the fact's own word to be uncovered high-risk evidence)
- 2026-10-04 round 5: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=fix-induced; action=amend-plan (plan peer-review; applied — checker warnings on the finalised note now count in the pass rule). Cap reached (5 of 5); loop stopped unconverged-by-rule: rounds 3–5 each found one new MED on the harness metric contract (Task 2.3, D8) and nothing elsewhere.

## Review Findings Log

### Round 1 - 2026-10-04 - pilot plan, independent cross-family codex plan peer-review (round 1)

- Round status: Closed
- Source: Codex plan peer-review
- Recorded by: the owning planning session, verbatim from the peer's read-only output
- Materiality: 3 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: 1be6fd8 + working-tree plan
- Files read: `.agents/skills/peer-review/SKILL.md`; `.cursor/plans/plan-pilot.md` in full; scoped portions of `AGENTS.md`, `PLAN.md`, and `.cursor/plans/plan-installation.md:2453–2504`; named symbols in `desktop/src/scribe_desktop/{session.py,encounter.py,draft_write.py,past_sessions.py,audit.py,logging_setup.py,note_config.py,transcription.py,note.py,note_check.py,note_fill.py,speaker_eval.py,benchmark.py,ui/session_screen.py,ui/bridge.py,ui/main_window.py,ui/models.py,ui/note.py,ui/past_sessions.py,ui/note_review.py}`; relevant portions of `desktop/tests/{test_write_lines.py,test_audit.py,test_install_layout.py,test_speaker_eval.py,sapi_fixture.py}`; `docs/testing/{shipping-gate.md,speaker-measurement.md}`, `docs/practice/patient-information-and-consent.md`, `docs/release/pilot-builds.md`, and `docs/lessons.md`.
- Finding verification: 10 candidates / 7 dropped / 0 downgraded
- Review method: Static, read-only. No files changed; no tests or builds run.

#### Findings

##### Coverage

**PR-HIGH-001 — Inline editing leaves shadow note text copyable**

- Plan section: Codebase Integration Notes; D5; Task 1.5.
- Materiality: build-affecting.
- Why it matters: During shadow review, opening a line’s editor exposes its existing note text in a `QLineEdit`. Selecting that text and using native Copy/Cut shortcuts or its context menu bypasses `_place_note_text`. Gating the note body and that helper therefore does not deliver the promised refusal of every Copy.
- Current plan text: `.cursor/plans/plan-pilot.md:265`:
  > In `ui/note.py` add a shadow reason separate from `_copy_ready` (D5): it disables the Copy button with its reason, makes `copy_selection` (keyboard and context menu) a refusal, keeps the note body non-selectable, and `_place_note_text` refuses as the last line.
- Evidence: `desktop/src/scribe_desktop/ui/note.py:233`:
  ```python
  class _LineEditor(QLineEdit):
  ```
  `desktop/src/scribe_desktop/ui/note.py:241–245` delegates every key except Escape to the native editor:
  ```python
      def keyPressEvent(self, event: QKeyEvent, /) -> None:
          if event.key() == Qt.Key.Key_Escape:
              self.escape_pressed.emit()
              return
          super().keyPressEvent(event)
  ```
  `desktop/src/scribe_desktop/ui/note.py:1730–1731`:
  ```python
          editor = _LineEditor()
          editor.setText(current_text)
  ```
- Suggested change: Extend Task 1.5 to gate the inline editor’s native Copy/Cut shortcuts and context-menu actions in shadow mode while preserving review editing. Explicitly keep editor drag export disabled. Add shadow/normal fake-clipboard tests for these routes; enumerating `_place_note_text` callers cannot detect inherited Qt clipboard operations.
- /fix decision: Applied
- /fix notes: Verified (ui/note.py:233, :1730). Task 1.5 now refuses the inline editor's native Copy, Cut, context-menu actions and drag in shadow while keeping editing; its test enumerates every widget class that can hold note text. Siblings reconciled: D5, Critical Constraint 3, the "every way note text leaves the app" integration note. Verified materiality: build-affecting.
- /fix date: 2026-10-04
- /fix applied by: Claude Code (owning planning session)

##### Practicality / feasibility / sequencing

**PR-MED-002 — Re-exporting custody helpers does not preserve existing failure injections**

- Plan section: Task 2.1.
- Materiality: build-affecting.
- Why it matters: Moved functions resolve their globals in `eval_store`, even when re-exported by `speaker_eval`. Keeping shared `shutil` and `tempfile` imports preserves their module-object patches, but tests also replace names directly on `speaker_eval`. Those replacements will stop reaching the implementation, breaking the promised unchanged suite and bypassing its injected custody failures.
- Current plan text: `.cursor/plans/plan-pilot.md:276`:
  > Move `speaker_eval.py`'s temporary-store helpers (`_write_store` … `_transcribe_in_temporary_store`) into a new `eval_store.py`; `speaker_eval` re-exports them and keeps importing `shutil` and `tempfile` so `test_speaker_eval.py`'s patches still bind.
  
  `.cursor/plans/plan-pilot.md:277`:
  > Done when: `test_speaker_eval.py` passes unchanged.
- Evidence: `desktop/tests/test_speaker_eval.py:1017`:
  ```python
      monkeypatch.setattr(speaker_eval, "SessionCrypto", factory)
  ```
  `desktop/tests/test_speaker_eval.py:1088`:
  ```python
          monkeypatch.setattr(speaker_eval, "_probe", lambda path, **kwargs: "unreadable")
  ```
  `desktop/tests/test_speaker_eval.py:1138`:
  ```python
          monkeypatch.setattr(speaker_eval, "delete_session_key", _refuse_unlink)
  ```
  The extracted functions consume these module-local names at `desktop/src/scribe_desktop/speaker_eval.py:940`, `:1004`, and `:1065`:
  ```python
      root_state = "gone" if temp_root is None else _probe(temp_root)
  ```
  ```python
          legs.append(("key unlink", functools.partial(delete_session_key, session_dir)))
  ```
  ```python
      crypto = SessionCrypto()
  ```
- Suggested change: Update the affected patch targets to the defining `eval_store` module while preserving their assertions, or explicitly forward dependencies through compatibility wrappers. Replace “passes unchanged” with verification that every existing failure scenario still exercises the extracted implementation.
- /fix decision: Applied
- /fix notes: Verified (test_speaker_eval.py:1017, 1088, 1138, 1191, 1221, 1318 replace names on the speaker_eval module). Took the simpler route: Task 2.1 no longer moves the helpers; they stay in speaker_eval.py and gain public names, so no patch target changes. Siblings reconciled: the shared-helpers integration note, Task 2.4's wording; no eval_store.py is created. Verified materiality: build-affecting.
- /fix date: 2026-10-04
- /fix applied by: Claude Code (owning planning session)

**PR-MED-003 — Synthetic speaker mapping lacks the timed ground truth it requires**

- Plan section: D9; Tasks 2.2, 2.4 and 2.5.
- Materiality: build-affecting.
- Why it matters: The runner must choose the diarised clinician label before composing the note. The specified `speaker_eval` approach uses overlap with timed role spans. Synthetic scripts supply role/text lines, but the plan requires label tracks only for role-plays. Variable speech rates, concatenation and overlap prevent line order from supplying those timings. Inferring roles from recognised words would introduce a different policy that becomes unreliable when transcription fails.
- Current plan text: `.cursor/plans/plan-pilot.md:175`:
  > Clinician speaker: from the script's role labels, mapped to diarised labels the way `speaker_eval` maps roles.
  
  `.cursor/plans/plan-pilot.md:278`:
  > A set folder holds `<id>.json` + `<id>.wav` (the `read_wav_pcm` contract) and, for role-plays, the Audacity label file `docs/testing/speaker-measurement.md` already defines.
- Evidence: `desktop/src/scribe_desktop/speaker_eval.py:380–382`:
  ```python
  def align_segments(
      segments: Sequence[SpeechSegment], track: LabelTrack
  ) -> tuple[SegmentTruth, ...]:
  ```
  `desktop/src/scribe_desktop/speaker_eval.py:394–397`:
  ```python
          for span in track.spans:
              seconds = min(segment.end_seconds, span.end_seconds) - max(
                  segment.start_seconds, span.start_seconds
              )
  ```
  Its tie contract at `desktop/src/scribe_desktop/speaker_eval.py:387–389` states:
  > A tie for the lead (within ``_SECONDS_EPSILON``) has no majority: the  
  > segment carries no ``true_label``, is MIXED and ``tied``, and is scored  
  > by nobody — ground truth is never decided by a spelling.
- Suggested change: Require Task 2.5 to emit timed role labels from the final resampled sample offsets, including overlapping turns. Have the runner load these for synthetic encounters as well as role-plays. Add alignment tests after rate/overlap changes and specify what happens when no clinician mapping can be established.
- /fix decision: Applied
- /fix notes: Verified (speaker_eval.py align_segments needs timed spans). Task 2.5 emits the label file from final sample offsets; Task 2.2 requires a label file for every encounter; Task 2.4 aligns with align_segments and counts an unresolved role as a failed encounter. Sibling reconciled: D9. Verified materiality: build-affecting.
- /fix date: 2026-10-04
- /fix applied by: Claude Code (owning planning session)

PEER-PLAN-ROUND-1 RESULT: 3 findings (CRIT 0 / HIGH 1 / MED 2 / LOW 0; build-affecting 3 / record-only 0 / invalid 0).

### Round 2 - 2026-10-04 - pilot plan, independent cross-family codex plan peer-review (round 2)

- Round status: Closed
- Source: Codex plan peer-review
- Recorded by: the owning planning session, verbatim from the peer's read-only output
- Materiality: 2 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: `1be6fd8` + working-tree plan
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `AGENTS.md`; `.cursor/plans/plan-pilot.md` body, Tasks and `/fix notes` only; `PLAN.md:158–221`; `.cursor/plans/plan-installation.md:2453–2504`.
  - Scoped symbols under `desktop/src/scribe_desktop/`: `session.py`, `encounter.py`, `draft_write.py`, `past_sessions.py`, `audit.py`, `logging_setup.py`, `note_config.py`, `transcription.py`, `note.py`, `note_fill.py`, `note_check.py`, `speaker_eval.py`, `benchmark.py`; `ui/session_screen.py`, `ui/bridge.py`, `ui/main_window.py`, `ui/models.py`, `ui/note.py`, `ui/note_review.py`, `ui/past_sessions.py`, `ui/transcript.py`, `ui/practitioner.py`, `ui/style_review.py`.
  - Scoped tests: `desktop/tests/sapi_fixture.py`, `test_write_lines.py`, `test_audit.py`, `test_install_layout.py`, `test_speaker_eval.py`; resampler/provider references in tests.
  - Cited portions of `docs/testing/shipping-gate.md`, `docs/testing/speaker-measurement.md`, `docs/practice/patient-information-and-consent.md`, `docs/release/pilot-builds.md`, `docs/lessons.md`.
- Finding verification: 14 candidates / 12 dropped / 0 downgraded
- Review was static and read-only; no tests or builds ran.

#### Findings

##### Coverage

**PR-HIGH-021 — Shadow Save can carry note wording into a later normal recording through learned shorthand**

- Plan section: D5, Critical Constraint 3, Tasks 1.5–1.6.
- Materiality: build-affecting
- Why it matters: With learning enabled, editing an eligible clinician line in a shadow recording and saving it persists the edited wording as a global learned rule. Correcting an existing learned rule also replaces its global wording. Neither route retains the recording’s mode. A subsequent normal recording can trigger that expansion, confirm it, and copy or write it through the normal controls. Gating the current note, inline editor and Past-sessions entry therefore does not close this transfer into a non-shadow context. The Practitioner tab also displays the persisted wording outside Task 1.5’s widget inventory.
- Current plan text:
  - `.cursor/plans/plan-pilot.md:201`: “**Every path that carries note text out is gated in shadow mode:**”
  - `.cursor/plans/plan-pilot.md:386`: “a test enumerates `_place_note_text`'s callers AND every widget class in `ui/note.py` and `ui/past_sessions.py` that can hold note text, so a new one fails until gated (Constraint 3).”
- Evidence:
  - `desktop/src/scribe_desktop/ui/note_review.py:322`:
    ```python
    queued = LearnedRuleCandidate(typed.section_key, candidate.phrase, typed.text)
    ```
  - `desktop/src/scribe_desktop/ui/note.py:2039–2040`:
    ```python
    learned = self._write_learned_phrases()
    rules = self._write_learned_rules()
    ```
  - `desktop/src/scribe_desktop/ui/note.py:2111–2112`:
    ```python
    outcome = append_learned_rules(
        queued, config_root=self._config_root, learned_at=now
    ```
  - The replacement sibling, `desktop/src/scribe_desktop/ui/note.py:2139–2140`:
    ```python
    replaced = replace_learned_rule_wording(
        rule_id, wording, config_root=self._config_root, replaced_at=now
    ```
  - Future proposal creation, `desktop/src/scribe_desktop/note_fill.py:212` and `:224`:
    ```python
    for entry_index, assertion_text in enumerate(rule.expansion_texts()):
    ```
    ```python
    note_excerpt=assertion_text,
    ```
  - `desktop/src/scribe_desktop/ui/practitioner.py:1628`:
    ```python
    wording = " | ".join(rule.typed_wording)
    ```
  - Normal note export, `desktop/src/scribe_desktop/ui/note.py:2198`:
    ```python
    if _place_note_text(models.format_note_body(note)):
    ```
- Suggested change: Explicitly close the shadow learning boundary. The simplest approach is to prevent shadow Save from adding learned phrases/rules or replacing learned wording, with a named explanation; retain safety-direction demotions. Test new-rule and replacement paths, then start a normal recording and prove that shadow wording was not persisted or reused. Alternatively, carry shadow provenance through learning and gate all resulting views and reuse.
- /fix decision: Applied
- /fix notes: Verified (ui/note.py:1477, 2039-2040, 2047, 2139). Practitioner decision 2026-10-04: no learning in shadow. New Task 1.9 and D13: a shadow Save writes no learned phrase or rule and replaces no learned wording; demotions still apply. Siblings reconciled: Agreed Scope, Flow 1, Critical Constraint 3, the Phase 1 live smoke, the task count (34). Verified materiality: build-affecting.
- /fix date: 2026-10-04
- /fix applied by: Claude Code (owning planning session)

##### Practicality / feasibility / sequencing

**PR-MED-022 — The metric contract lacks distinctions required by the proposed pass rule**

- Plan section: D8, Tasks 2.2–2.4 and decision 3.5.
- Materiality: build-affecting
- Why it matters: The proposed rule distinguishes unsupported *clinical* claims from other unsupported lines, and requires a warning for each particular omitted material fact. The specified outputs provide unsupported-line and omission tallies without defining either distinction. Aggregate warning counts cannot prove coverage: a warning about one segment must not excuse an unrelated material omission. Implementing the runner before defining these relationships leaves the pass evaluator dependent on an unstated classification and matching policy.
- Current plan text:
  - `.cursor/plans/plan-pilot.md:400`: “word error rate; per-fact verdicts; unsupported-line, omission and uncertainty-surfaced tallies.”
  - `.cursor/plans/plan-pilot.md:421`: “zero unsupported lines that are clinical claims”
  - `.cursor/plans/plan-pilot.md:421`: “no omitted material fact without a warning”
- Evidence:
  - Script facts are specified without a source-line or time association at `.cursor/plans/plan-pilot.md:398`: “expected facts (kind: laterality / dose / negation / absent / present; tokens; `material`; `expect_uncertain`)”.
  - Actual checker warnings identify assertions or transcript coordinates, not expected-script facts, at `desktop/src/scribe_desktop/note.py:583–587`:
    ```python
    note_warning_code: str
    severity: NoteWarningSeverity
    section_key: NoteSectionKey | None = None
    assertion_id: str | None = None
    source_coords: SourceCoords | None = None
    ```
  - `desktop/src/scribe_desktop/note_check.py:1516–1518`:
    ```python
    note_warning_code="high_risk_omission",
    severity="review",
    source_coords=SourceCoords(segment_index, min(uncovered), max(uncovered)),
    ```
  - Uncertainty warnings likewise point to individual transcript words, `desktop/src/scribe_desktop/note_check.py:534`:
    ```python
    source_coords=SourceCoords(coords.segment_index, index, index),
    ```
- Suggested change: Extend Tasks 2.2–2.3 to define how expected facts map to reference content and checker coordinates, and return per-fact warning coverage as enums/booleans. Define how unsupported clinical claims are distinguished—or explicitly propose the conservative rule that every unsupported line fails for decision 3.5. Add hand-computed cases for an unrelated warning beside a material omission, repeated facts, and unsupported nonclinical content. Establish this contract before Task 2.4 implements pass/fail evaluation.
- /fix decision: Applied
- /fix notes: Verified (note.py NoteWarning carries assertion_id / source_coords only; note_check.py high_risk_omission and low_confidence_source point at transcript coordinates). Task 2.2 adds each fact's reference-line index; Task 2.3 now defines reference alignment, the unsupported clinical line, per-fact verdicts with warned / uncertainty_surfaced booleans, and silent omission, with the three hand-computed cases the peer named; decision 3.5 option (a) is restated in those terms. Sibling reconciled: D8. Verified materiality: build-affecting.
- /fix date: 2026-10-04
- /fix applied by: Claude Code (owning planning session)

PEER-PLAN-ROUND-2 RESULT: 2 findings (CRIT 0 / HIGH 1 / MED 1 / LOW 0; build-affecting 2 / record-only 0 / invalid 0).

### Round 3 - 2026-10-04 - pilot plan, independent cross-family codex plan peer-review (round 3)

- Round status: Closed
- Source: Codex plan peer-review
- Recorded by: the owning planning session, verbatim from the peer's read-only output
- Materiality: 1 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: `1be6fd8` + working-tree plan
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `AGENTS.md`; `.cursor/plans/plan-pilot.md` body, Tasks and `/fix notes`; `PLAN.md:158–221`; `.cursor/plans/plan-installation.md:2453–2504`.
  - Named symbols and relevant call sites under `desktop/src/scribe_desktop/`: `session.py`, `encounter.py`, `draft_write.py`, `past_sessions.py`, `audit.py`, `logging_setup.py`, `note_config.py`, `transcription.py`, `note.py`, `note_check.py`, `speaker_eval.py`, `benchmark.py`; `ui/session_screen.py`, `ui/bridge.py`, `ui/main_window.py`, `ui/models.py`, `ui/note.py`, `ui/past_sessions.py`, `ui/note_review.py`.
  - Named portions of `desktop/tests/test_write_lines.py`, `test_audit.py`, `test_install_layout.py`, `test_speaker_eval.py`, `sapi_fixture.py`.
  - Cited portions of `docs/testing/shipping-gate.md`, `docs/testing/speaker-measurement.md`, `docs/practice/patient-information-and-consent.md`, `docs/release/pilot-builds.md`, `docs/lessons.md`.
- Finding verification: 5 candidates / 4 dropped / 0 downgraded. Dropped candidates were already constrained by the plan or lacked a concrete contradictory implementation requirement. No files changed; no tests or builds run.

#### Findings

##### Practicality / feasibility / sequencing

**PR-MED-031 — Reference-line-to-segment alignment can falsely satisfy the pass rule and reject correctly supported notes**

- Plan section: D8; Task 2.3 reference alignment, unsupported-line and per-fact metrics; decision 3.5.
- Materiality: build-affecting
- Why it matters: Reference lines and VAD segments do not have matching boundaries. Multiple reference lines can occupy one transcript segment. Under the proposed rule, an omission warning concerning one fact then marks another omitted material fact in that segment as `warned`, allowing a silent omission to pass decision 3.5. Likewise, an unrelated low-confidence word can satisfy another fact’s `uncertainty_surfaced` requirement. A reference line split across segments can instead lose its relevant warning when only the highest-overlap segment is selected.

  The same boundary assumption affects unsupported lines: the extractive provider emits whole utterances. An accurately transcribed assertion combining two reference lines can fail single-reference coverage and be classified as unsupported clinical content because its best reference line lacks the other line’s number or side. These are ordinary segmentation outcomes, including with the planned overlap conditions.

- Current plan text:
  - `.cursor/plans/plan-pilot.md:513`:
    > **Reference alignment:** each reference line is matched to the transcript segment with the highest content-token overlap (ties and no-overlap = unaligned, reported).
  - `.cursor/plans/plan-pilot.md:514`:
    > **Unsupported line:** a note line with no reference line covering its content tokens at the declared threshold. It is an **unsupported clinical line** when it carries a structured-claim token (a side, a number, dose or unit, or a negation) that the best-matching reference line does not — every such line fails the run; other unsupported lines are counted and listed by encounter id and line index only.
  - `.cursor/plans/plan-pilot.md:515`:
    > **Per expected fact:** a verdict (`correct` / `wrong` / `omitted` / `correctly_absent` / `wrongly_present`) and two booleans — `warned` (a `high_risk_omission` warning's coordinates fall in the segment aligned to the fact's `line`; a warning elsewhere never excuses it) and `uncertainty_surfaced` (a `low_confidence_source` warning in that segment, for facts marked `expect_uncertain`).
  - `.cursor/plans/plan-pilot.md:517` includes:
    > an unrelated warning beside a material omission (still silent)

- Evidence:
  - `desktop/src/scribe_desktop/transcription.py:1187`:
    ```python
    """Flow 2: VAD -> Whisper per ~30 s window of consecutive segments ->
    word->segment attribution -> uncertainty marks -> speaker labels ->
    ```
    Segments are determined by audio processing, independently of reference-line boundaries.
  - `desktop/src/scribe_desktop/note.py:1601`:
    ```python
    Every emitted assertion is one whole utterance quoted exactly, carrying
    that utterance's contiguous coordinates, so Check 1 reconstructs it
    ```
  - `desktop/src/scribe_desktop/note_check.py:530`:
    ```python
    note_warning_code="low_confidence_source",
    ```
    Its evidence is word-specific at `desktop/src/scribe_desktop/note_check.py:534`:
    ```python
    source_coords=SourceCoords(coords.segment_index, index, index),
    ```
  - `desktop/src/scribe_desktop/note_check.py:1516`:
    ```python
    note_warning_code="high_risk_omission",
    ```
    Its coordinates cover the uncovered high-risk words at `desktop/src/scribe_desktop/note_check.py:1518`:
    ```python
    source_coords=SourceCoords(segment_index, min(uncovered), max(uncovered)),
    ```
    Neither warning establishes coverage of every expected fact sharing that segment.

- Suggested change: Replace the single-segment contract with deterministic alignment between reference/fact evidence and transcript word spans, allowing split and merged boundaries. Require fact-specific warning evidence; shared segment membership alone must not set either boolean. Preserve ambiguity explicitly and define its conservative pass-rule treatment. Allow a merged assertion to obtain support from its corresponding reference spans, without pooling unrelated claims. Add hand-computed cases for one reference line split across segments, multiple reference lines merged into one segment, unrelated warnings within the same segment, and overlapping turns. Keep this logic in the harness without widening the enforcing checker.
- /fix decision: Applied
- /fix notes: Verified (transcription.py:1187 segments come from audio; note.py:1601 one assertion is one whole utterance; note_check.py:530-534 and :1516-1518 warnings carry word coordinates). Changed the contract rather than patching the per-segment rule: Task 2.3 now uses ONE word-level edit-distance alignment (the word-error-rate alignment) between reference tokens and transcript words; unsupported clinical lines, per-fact verdicts, warned and uncertainty_surfaced are all decided at word level, ambiguity takes the worse outcome, and the peer's four boundary cases are in the Done-when. Sibling reconciled: D8. Decision 3.5's option (a) needed no change. Verified materiality: build-affecting.
- /fix date: 2026-10-04
- /fix applied by: Claude Code (owning planning session)

PEER-PLAN-ROUND-3 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 0; build-affecting 1 / record-only 0 / invalid 0).

### Round 4 - 2026-10-04 - pilot plan, independent cross-family codex plan peer-review (round 4)

- Round status: Closed
- Source: Codex plan peer-review
- Recorded by: the owning planning session, verbatim from the peer's read-only output
- Materiality: 1 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: `1be6fd8` + working-tree plan
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `AGENTS.md`; scoped portions of `PLAN.md` and `.cursor/plans/plan-installation.md`; `.cursor/plans/plan-pilot.md` body, Tasks and logged `/fix notes`.
  - Named symbols under `desktop/src/scribe_desktop/`: `session.py`, `encounter.py`, `draft_write.py`, `past_sessions.py`, `audit.py`, `logging_setup.py`, `note_config.py`, `transcription.py`, `note.py`, `note_check.py`, `speaker_eval.py`, `benchmark.py`; `ui/session_screen.py`, `ui/bridge.py`, `ui/main_window.py`, `ui/models.py`, `ui/note.py`, `ui/past_sessions.py`, `ui/note_review.py`.
  - Scoped tests: `desktop/tests/sapi_fixture.py`, `test_write_lines.py`, `test_audit.py`, `test_install_layout.py`, `test_speaker_eval.py`.
  - Cited portions of `docs/testing/shipping-gate.md`, `docs/testing/speaker-measurement.md`, `docs/practice/patient-information-and-consent.md`, `docs/release/pilot-builds.md`, `docs/lessons.md`.
- Finding verification: 6 candidates / 5 dropped / 0 downgraded. No files changed; no tests or builds run.

#### Findings

##### Practicality / feasibility / sequencing

**PR-MED-041 — Bounding warning coordinates can hide an unrelated silent omission**

- Plan section: D8; Task 2.3’s `warned` contract and Done-when; decision 3.5 option (a).
- Materiality: build-affecting
- Why it matters: A `high_risk_omission` warning contains the interval between its first and last uncovered high-risk words, including intervening words that did not trigger it. Two unrelated omitted high-risk words can therefore bracket an omitted material symptom in the same clinician segment. The planned overlap check credits that symptom as warned, removes it from silent omissions, and can let option (a) pass. Word-level overlap alone does not close the earlier unrelated-warning defect.
- Current plan text:
  - `.cursor/plans/plan-pilot.md:590`: “`warned` (a `high_risk_omission` warning whose word range overlaps the fact's aligned words)”
  - `.cursor/plans/plan-pilot.md:590`: “A warning elsewhere in the same segment never counts.”
  - `.cursor/plans/plan-pilot.md:591`: “**Silent omission** = `omitted` and `material` and not `warned`.”
  - `.cursor/plans/plan-pilot.md:613`: “zero silent omissions”
- Evidence:
  - `desktop/src/scribe_desktop/note_check.py:1507` selects only uncovered high-risk positions:

    ```python
    uncovered = [
        word_index
        for word_index, word in enumerate(segment.transcript_words)
        if (segment_index, word_index) not in covered
        and _is_high_risk_token(word.word_text, first_in_segment=word_index == 0)
    ]
    ```

  - `desktop/src/scribe_desktop/note_check.py:1518` converts those potentially disconnected positions into a bounding interval:

    ```python
    source_coords=SourceCoords(segment_index, min(uncovered), max(uncovered)),
    ```

- Suggested change: Require the fact’s aligned positions to intersect actual uncovered high-risk evidence contributing to the warning, rather than merely its bounding interval. The harness can derive that evidence from the transcript, assertion coverage and existing high-risk predicate without changing the checker. Add a hand-computed case with unrelated omitted high-risk words on both sides of an omitted material non-high-risk fact; that middle fact must remain a silent omission and fail option (a).
- /fix decision: Applied
- /fix notes: Verified (note_check.py:1507-1518: the warning's coordinates are min..max of possibly disconnected uncovered high-risk words; `_is_high_risk_token` at :1472). Task 2.3's `warned` now requires one of the fact's own aligned words to be an uncovered high-risk word in a segment carrying the warning, derived by the harness from the transcript, the note's coverage and the existing predicate (read, not changed); the bracketed-omission hand case is in the Done-when. Sibling reconciled: D8. Verified materiality: build-affecting.
- /fix date: 2026-10-04
- /fix applied by: Claude Code (owning planning session)

PEER-PLAN-ROUND-4 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 0; build-affecting 1 / record-only 0 / invalid 0).

### Round 5 - 2026-10-04 - pilot plan, independent cross-family codex plan peer-review (round 5)

- Round status: Closed
- Source: Codex plan peer-review
- Recorded by: the owning planning session, verbatim from the peer's read-only output
- Materiality: 1 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: `1be6fd8` + working-tree plan
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `AGENTS.md`; `.cursor/plans/plan-pilot.md` body, Tasks and logged `/fix notes`; `PLAN.md:158–221`; `.cursor/plans/plan-installation.md:2453–2504`.
  - Named symbols in `desktop/src/scribe_desktop/`: `session.py`, `encounter.py`, `draft_write.py`, `past_sessions.py`, `audit.py`, `logging_setup.py`, `note_config.py`, `transcription.py`, `note.py`, `note_check.py`, `speaker_eval.py`, `benchmark.py`; `ui/session_screen.py`, `ui/bridge.py`, `ui/main_window.py`, `ui/models.py`, `ui/note.py`, `ui/past_sessions.py`, `ui/note_review.py`.
  - Scoped tests: `desktop/tests/sapi_fixture.py`, `test_write_lines.py`, `test_audit.py`, `test_install_layout.py`, `test_speaker_eval.py`.
  - Cited portions of `docs/testing/shipping-gate.md`, `docs/testing/speaker-measurement.md`, `docs/practice/patient-information-and-consent.md`, `docs/release/pilot-builds.md`, `docs/lessons.md`.
- Finding verification: 4 candidates / 3 dropped / 0 downgraded
- Review was static and read-only; no files changed and no tests or builds run.

#### Findings

##### Missing verification / rollback / migration

**PR-MED-051 — The validation rule can pass a finalised note containing a contradictory configuration proposal**

- Plan section: D9; Tasks 2.3, 2.4 and decision 3.5(a).
- Materiality: build-affecting
- Why it matters: With an accurate transcript and correctly extracted material facts, a confirmed configuration proposal can add the opposite side or polarity. Its line has no transcript coordinates, so Task 2.3 excludes it from unsupported-line scoring; the correctly extracted facts retain their passing verdicts. `check_note` can identify the contradiction, but `finalise_note` returns the note with warnings attached. Option (a) contains no condition that fails on those warnings. Consequently, this clinically contradictory output can receive a validation pass. This is a harness acceptance defect; it does not require changing the app’s checker severity contract or the confirm-all policy.
- Current plan text:
  - `.cursor/plans/plan-pilot.md:644`: “Lines that came from the practitioner's config (no word coordinates) are counted separately and not judged.”
  - `.cursor/plans/plan-pilot.md:645`: “a verdict (`correct` / `wrong` / `omitted` / `correctly_absent` / `wrongly_present`) from whether the fact's aligned words are inside a note line”
  - `.cursor/plans/plan-pilot.md:668`: “zero unsupported clinical lines; zero `wrong` or `wrongly_present` verdicts among material facts; zero silent omissions; every `expect_uncertain` fact `uncertainty_surfaced`; no "role unresolved" encounter; word error rate, other unsupported lines and warned omissions recorded, not thresholded”
- Evidence:
  - `desktop/src/scribe_desktop/note.py:2577–2579` constructs the confirmed proposal’s span without source coordinates:
    ```python
    note_span=NoteSpan(
        span_text=proposal.note_excerpt, provenance=proposal.provenance
    ),
    ```
  - `desktop/src/scribe_desktop/note.py:2603–2604` returns warnings rather than refusing the finalised artifact:
    ```python
    warnings = check_note(unchecked, document, config, pending_proposals=pending)
    return _assemble(warnings)
    ```
  - `desktop/src/scribe_desktop/note_check.py:1143–1144` explicitly includes configuration-authored assertions:
    ```python
    # Authored text — autofill, prefill and a typed ``clinician``
    # line (schema v2) alike — is checked against the quoted evidence.
    ```
  - `desktop/src/scribe_desktop/note_check.py:1321–1326` produces the relevant warnings:
    ```python
    if key[0] == "laterality":
        warnings.append(_laterality_mismatch_warning(assertion, other))
    elif key[0] == "dose" and not _same_state(mine, other):
        warnings.append(_dose_mismatch_warning(assertion, other))
    else:
        warnings.append(_contradiction_warning(assertion, other))
    ```
- Suggested change: Extend Tasks 2.3–2.4 and rule 3.5(a) so configuration-authored clinical contradictions cannot escape the verdict. Require checker errors to fail the encounter, and resolve clinical mismatch warnings against explicit script expectations before allowing a pass. Keep the existing checker and its severity contract unchanged. Add hand-computed cases with an accurate transcript and correct extracted facts plus a conflicting confirmed configuration proposal for laterality, dose and negation; each must fail, with text-free output.
- /fix decision: Applied
- /fix notes: Verified (note.py:2577-2579 a confirmed proposal's span has no source coordinates; :2603-2604 finalise_note returns the note with warnings; note_check.py:1321-1326 raises laterality, dose and contradiction warnings for authored text). Task 2.3 gains a checker tally: any error-severity warning, and any contradiction / laterality / dose mismatch warning the script does not list in its new `expected_warnings` field (Task 2.2), fails the encounter; decision 3.5 option (a) and D9 say so; three config-conflict hand cases are in the Done-when. The checker is unchanged. Verified materiality: build-affecting.
- /fix date: 2026-10-04
- /fix applied by: Claude Code (owning planning session)

PEER-PLAN-ROUND-5 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 0; build-affecting 1 / record-only 0 / invalid 0).

## Tasks
Phases are grouped for `/execute-loop`: Phase 1 is the schema and safety-boundary phase and stands alone; Phase 2 is developer-only tooling; Phase 3 is documents and two decisions. Each task defers to `Validation / Verification` for the suite run unless it says otherwise. Paths are under `desktop/src/scribe_desktop/` unless they start with another folder; line numbers are in `Key Findings`.

### Phase 1 — Shadow mode and audit v2 (build 0.2.0)

- [ ] 🟥 **1.1 Pilot settings and the Status tab.** Add a pilot-settings model and accessor in `note_config.py` beside `DevSettings` (`config\pilot.json`, one field `shadow_mode`, written through `_write_config_file`); absent = off, present but unreadable = ON (D3). In `ui/main_window.py` `StatusPanel`, add a "Shadow mode (pilot)" checkbox built like the developer-writes checkbox, a line naming an unreadable file, and a line showing the app version (`__version__`). Wording follows `docs/design-system.md`.
  - Done when: tests cover absent, valid on, valid off and unreadable, each through an injected config root; the checkbox round-trips; the version line is pinned against `__version__`.
- [ ] 🟥 **1.2 The mode on the session and the encounter record.** Define `SessionMode` (`normal` / `shadow`). Add it to `RecordingSession` and `EncounterRecord` (v2; v1 reads as `normal`). `SessionController.start` takes the mode from the Start funnel (`ui/session_screen._start`, for both `on_start` and `start_linked`), which reads the pilot setting at the click. Carry it through `adopt_queued`, the recovery checkout and `_open_adopted`'s construction; a session whose record cannot be read is treated as shadow (D3). Constraint 1.
  - Done when: a session started with the setting on is shadow after Start, after recovery, after `adopt_queued` and after an Unreviewed open; changing the setting mid-recording changes nothing; the `read_encounter_record` call-count spies still pass unchanged; v1 fixture bytes read as `normal`.
- [ ] 🟥 **1.3 Audit row v2.** In `audit.py` add `mode` (enum) and `app_version` (pattern, optional) to `AuditRow`; `AuditLog.begin` receives both from `SessionController.start`; upgrade v1 rows in `_decode` before validation (D6, D7); add both to `CSV_COLUMNS` and `_csv_values` together. Move the tests' "newer version" fixtures from 2 to 3. State in a comment that flat tokens need no new `_PAYLOAD_SIGNATURES` entry.
  - Done when: `test_audit.py`'s constraint, forbidden-name, tripwire and CSV-header tests pass with the new fields; a stored v1 row exports with mode `normal` and an empty version; a v3 row reads as `_NEWER` without refusing Start.
- [ ] 🟥 **1.4 Write refused by name.** Add `shadow_session` to `draft_write.WriteRefusalName`; refuse in `refuse_before_read` and `ui/models.write_control` beside `dev_build_writes_off` (D4); add its `WRITE_LINES` entry (no "copy" in the text) and place it deliberately in or out of `WRITE_UNCERTAIN_PREFIXED`; `MainWindow._on_write_requested` passes the session's mode.
  - Done when: for a shadow session no request is made (the transport spy sees zero calls), the Write control shows the shadow line, the audit row records the refusal name, and the pinned `WRITE_LINES` / prefix-set tests are updated in the same change.
- [ ] 🟥 **1.5 Copy refused by name; the note body display-only.** In `ui/note.py` add a shadow reason separate from `_copy_ready` (D5): it disables the Copy button with its reason, makes `copy_selection` (keyboard and context menu) a refusal, keeps the note body non-selectable, and `_place_note_text` refuses as the last line. `begin_review` and `show_saved_note` receive the mode from `MainWindow`. Write's "saved" derivation is untouched.
  - The inline line editor (`_LineEditor`, a `QLineEdit` created at `ui/note.py:1730` holding the line's existing text) keeps editing in shadow but its native Copy and Cut — shortcuts and its context-menu actions — are refused and drag is off; Paste, typing, Undo and Escape are unchanged (peer round 1, PR-HIGH-001).
  - Done when: with the fake clipboard, every caller of `_place_note_text` places nothing for a shadow session and behaves exactly as before for a normal one; the body's interaction flags are display-only in shadow at every review state; the line editor's Copy, Cut, context menu and drag place nothing in shadow and work as before in normal mode; a test enumerates `_place_note_text`'s callers AND every widget class in `ui/note.py` and `ui/past_sessions.py` that can hold note text, so a new one fails until gated (Constraint 3).
- [ ] 🟥 **1.6 Past sessions.** Carry the shadow flag through `KeepLabel` / `keep_label` and `MainWindow.keep_label_for` into `PastSessionLabel` v2 (v1 = not shadow); `UNKNOWN_LABEL` is shadow. `ui/past_sessions._copy_reason` / `on_copy` refuse a shadow entry with a named reason; the list marks the entry as a shadow recording.
  - Done when: a completed shadow session's entry is marked and its Copy refused; a v1 label still opens and copies; an unknown label refuses; the entry is still written and verified before the session key goes (existing custody tests unchanged).
- [ ] 🟥 **1.9 No learning from a shadow Save** (peer round 2, PR-HIGH-021; practitioner decision 2026-10-04; numbered 1.9, built here). In `ui/note.py`, a Save of a shadow session writes no learned phrase (`_write_learned_phrases`, :1477), no learned rule (`_write_learned_rules`, :2047 → `append_learned_rules`) and replaces no learned wording (`replace_learned_rule_wording`, :2139); the queue lines in `ui/note_review.py` say "not learned: shadow recording" instead of "will learn … when you save". Safety-direction demotions of a rule the practitioner corrected still apply. D13.
  - Done when: after a shadow Save with an eligible typed line, an edited learned rule and a queued phrase, the cue file and the learned-rules store are byte-identical to before (except a demotion count), the Practitioner tab shows nothing new, and a following normal recording offers no proposal carrying that wording; the same three actions in a normal session learn exactly as today.
- [ ] 🟥 **1.7 The Session tab says so.** `ui/session_screen.py`: a line above Start while the setting is on ("new recordings are shadow recordings: their notes cannot be copied or written to Cliniko"), and the same state shown for a live or recovered shadow recording. Add the cue to `docs/design-system.md`.
  - Done when: the line appears and disappears with the setting, and a live shadow recording stays labelled after the setting is turned off.
- [ ] 🟥 **1.8 Version 0.2.0 and the two-way schema tests.** Bump every pinned version location. Add a test module that, for each of the three v2 schemas, reads committed v1 fixture bytes with the new code, and asserts the "newer than current" behaviour the older build relies on (audit `_NEWER`, label unreadable and Copy closed, encounter `EncounterUnavailable` with Start unaffected).
  - Done when: `test_install_layout.py`'s version test passes at 0.2.0 and the new module passes; `CHANGELOG.md` has the 0.2.0 entry.

### Phase 2 — Validation harness (developer build only)

- [ ] 🟥 **2.1 Reuse the custody helpers in place.** Do NOT move them (peer round 1, PR-MED-002: `test_speaker_eval.py` injects failures by replacing `SessionCrypto`, `_probe` and `delete_session_key` on the `speaker_eval` module, and a moved function would no longer see those replacements). Give the two helpers the harness needs — the temporary-store transcription and its teardown — public names in `speaker_eval.py` (the private names stay as aliases), with their contract stated in the docstring.
  - Done when: `test_speaker_eval.py` passes unchanged, and a new test proves the public names are the same objects as the private ones.
- [ ] 🟥 **2.2 The encounter script format.** New `validation.py`: a strict model for one encounter — id, appointment type, axis tags (PLAN.md L188–201), lines (`role`, `text`), expected facts (kind: laterality / dose / negation / absent / present; tokens; `line` — the index of the reference line that states it; `material`; `expect_uncertain`), `expected_warnings` (the checker warning codes this encounter is written to provoke, for the contradictory-statement scripts; empty otherwise), and conditions (voice per role, rate, signal-to-noise ratio, overlap). A set folder holds, for EVERY encounter, `<id>.json` + `<id>.wav` (the `read_wav_pcm` contract) + the timed Audacity label file `docs/testing/speaker-measurement.md` already defines — hand-made for role-plays, emitted by the builder for synthetic ones (peer round 1, PR-MED-003: the role mapping needs timed spans; line order cannot supply them once rate and overlap vary).
  - Done when: valid and invalid fixtures are accepted and refused by name; a role-play folder made for `measure-speakers.py` loads without change once its JSON is added.
- [ ] 🟥 **2.3 The metrics.** Pure functions in `validation.py` (D8): word error rate; per-fact verdicts; unsupported-line, omission and uncertainty-surfaced tallies. Inputs are the transcript document, the finalised note and the script; outputs are numbers and enum verdicts only. The contract the pass rule needs (peer round 2, PR-MED-022), defined here before Task 2.4 evaluates anything:
    - **One word-level alignment** (peer round 3, PR-MED-031 — reference lines and transcript segments do not share boundaries, so nothing is decided per segment): the script's reference tokens, in spoken order (overlapped turns ordered by start time), are aligned to the transcript's words by the same edit-distance alignment that yields the word error rate. Every reference token is thereby matched, substituted or deleted, and every transcript word is matched, substituted or inserted; each expected fact's tokens map to exact transcript word positions (segment and word index), wherever the segment boundaries fall.
    - **Unsupported clinical line:** a note line taken from the transcript (it carries word coordinates) in which a structured-claim word — a side, a number, dose or unit, or a negation — is a substitution or an insertion in the alignment. Every such line fails the run. A line spanning several reference lines is judged word by word, so merging never makes it unsupported. Other substituted or inserted words in note lines are counted only. Lines that came from the practitioner's config (no word coordinates) are counted separately; they are judged through the checker tally below, not through the alignment.
    - **Checker tally** (peer round 5, PR-MED-051 — a confirmed config proposal can contradict an accurately transcribed fact, and `finalise_note` returns such a note with warnings rather than refusing it): per encounter, the count of each warning code on the finalised note. Any error-severity warning, and any `contradiction`, `contradiction_low_confidence`, `laterality_mismatch` or `dose_mismatch` the script does not list in its `expected_warnings`, fails the encounter. The checker and its severity contract are unchanged (Constraint 12). Structured-claim words are recognised by reading `note_check`'s existing token classes; that module is not changed (Constraint 12).
    - **Per expected fact:** a verdict (`correct` / `wrong` / `omitted` / `correctly_absent` / `wrongly_present`) from whether the fact's aligned words are inside a note line, and two booleans decided at WORD level — `warned` (the segment carries a `high_risk_omission` warning AND at least one of the fact's aligned words is itself an uncovered high-risk word — outside every note line and high-risk by `note_check`'s existing predicate, read not changed; the warning's coordinates are only a bounding interval, so lying inside them proves nothing: peer round 4, PR-MED-041) and `uncertainty_surfaced` (a `low_confidence_source` warning on one of the fact's aligned words, for facts marked `expect_uncertain`). A warning elsewhere in the same segment never counts. A fact whose tokens were deleted by transcription has no aligned words: it is `omitted`, not warned, and reported as "not transcribed".
    - **Silent omission** = `omitted` and `material` and not `warned`.
    - **Ambiguity is conservative:** when the alignment has equal-cost alternatives for a fact's tokens, the fact takes the worse outcome.
  - Done when: each metric has hand-computed cases including empty transcript, empty note, a negation flip, a left/right swap, a dose change, a fact the script marks absent, a fact stated twice, an unsupported non-clinical word (counted, not failing), one reference line split across two segments, two reference lines merged into one segment and into one note line, an unrelated warning in the same segment as a material omission (still silent), a fact deleted by transcription, an accurate transcript with correct facts plus a conflicting confirmed config proposal for each of side, dose and negation (each fails the encounter), an expected contradiction listed in `expected_warnings` (does not fail), an omitted material fact that is not high-risk lying between two unrelated omitted high-risk words in one segment (still silent, and it fails option (a) of decision 3.5), and an overlapped pair of turns; no output type can hold a string of note or transcript text (Constraint 7).
- [ ] 🟥 **2.4 The runner.** In `validation.py`: per encounter, transcribe in a temporary store (the Task 2.1 helpers), choose the clinician speaker by aligning the diarised segments with the encounter's timed label track (`speaker_eval.align_segments`; an encounter where no clinician mapping can be established is reported as "role unresolved" and counts as a failed encounter, never skipped), load the config from the explicit folder, build the extractive provider from that config's cues (give `ui/models._extractive_provider_from_config` a public name), `compose_draft` → resolve every proposal under the declared policy → `finalise_note`; optionally run the narrative prose stage. Apply and assert the offline environment first; refuse a `small` fallback unless allowed (D9). Report in the style of `speaker_eval.render_report`, with model names, commit and models-manifest hash, and pass or fail against a rule passed in as data.
  - Done when: with injected fake transcription and note providers the runner produces the expected report and leaves no store behind on success, on a provider error and on a teardown failure (which raises naming the path); the tests never read the real models folder.
- [ ] 🟥 **2.5 The synthetic set builder.** Move `resample_wav_to_pcm16` from `tests/sapi_fixture.py` into `src` (the fixture re-imports it). New builder: enumerate the installed Windows voices, assign one per role, vary rate, concatenate turns, mix noise at fixed signal-to-noise ratios and simulate overlap, with a fixed seed per encounter; write the label file from the FINAL resampled sample offsets of each turn, overlapping turns included; refuse clearly when fewer than two voices exist.
  - Done when: the signal-processing steps are tested on generated tones (level, ratio, overlap offsets, determinism); the emitted label spans match the placed turns to the sample after rate and overlap changes and parse with `speaker_eval.parse_audacity_labels`; voice enumeration is behind a seam tested with zero, one and two voices; no test calls the real speech engine except the existing fixture leg.
- [ ] 🟥 **2.6 The scripts.** About 40 synthetic encounter scripts in `validation/scripts/` covering common osteopathic appointment types and every axis of PLAN.md L188–201 (negation and changing symptoms; left/right and regions; numbers, medications, doses; small talk; uncertain and contradictory statements; a spoken instruction to the scribe; an end-of-consultation followed by a new-patient greeting; noise, overlap and rate variation through the conditions). Invented patients only.
  - Done when: a test loads every script, and a coverage test asserts each axis and each fact kind appears at least three times.
- [ ] 🟥 **2.7 Entry point and documentation.** `scripts/run-validation.py` and `scripts/build-validation-set.py` (thin launchers like `scripts/measure-speakers.py`); `docs/testing/validation-harness.md` (inputs, what each number means, the policies of D9, custody, how to run from a normal terminal); one line in `docs/testing/shipping-gate.md` saying the harness is separate from that run; a row in `scripts/README.md`.
  - Done when: both launchers print usage without models present and refuse by name when the models folder is empty.

### Phase 3 — Governance documents and decisions

- [ ] 🟥 **3.1 `docs/pilot/`.** `README.md` (the run order, who does what), `pilot-log-template.md` (one row per consultation: date, clinic, mode, app version, R1–R6, minutes, findings count — no text, no session ids), `findings-register.md` (id, date, severity, category anchored on rubric R4 plus cross-patient, privacy and custody, status open / resolved / controlled, the control), `exit-gate.md` (the per-clinic checklist of Flow 4 and the signature line). The filled log stays off-repo; the register in the repo holds no clinical content.
  - Done when: the four files exist and a docs test (or the existing docs lint, if one applies) finds no session-id-shaped or free-text clinical field in the templates.
- [ ] 🟥 **3.2 Incident process.** `docs/security/incident-process.md`: clinical-safety incidents are entered in the findings register; cross-reference both ways.
- [ ] 🟥 **3.3 Consent sheet v2.** `docs/practice/patient-information-and-consent.md` → `patient-info-v2`: a short Part A paragraph (for a limited number of appointments the practitioner also writes the note the usual way and compares it with the program's draft to check its quality; the draft is not placed in the record for those appointments; scores kept hold no name and nothing that was said), the Part B script and Cliniko record line updated, Part C's version. Update `docs/practice/README.md`. Constraint 11.
  - Done when: the banner, the state coverage and every existing statement the app backs are intact; the practitioner has read and approved the wording (recorded here with the date).
- [ ] 🟥 **3.4 Security and project documents.** `docs/security/threat-model.md` (shadow mode as a user setting with its residues: user-writable setting, the rollback rule, no Chrome indicator, drag closed by display-only; audit v2; the harness and its stores), `docs/security/data-flow-map.md` (the harness flow; the shadow branch of the Copy and Write flows), `docs/security/retention-schedule.md` (`pilot.json`; the role-play WAVs per decision 3.6; the off-repo pilot log), `docs/release/pilot-builds.md` (the rollback rule), `PLAN.md` (fix the stale Phase 7 delivery note at L167 and L173; point at this plan), `AGENTS.md` (status, a subsystem pointer for shadow mode and the harness, run step for the harness).
  - Done when: every sibling statement of a changed claim is reconciled across these files (grep the phrasing, not just the cited line).
- [ ] 🟥 **3.5 Ratify the validation pass rule.** [decision]
  - Options: (a) proposed, in Task 2.3's terms — zero unsupported clinical lines; zero `wrong` or `wrongly_present` verdicts among material facts; zero silent omissions; every `expect_uncertain` fact `uncertainty_surfaced`; no checker error and no unexpected contradiction, side or dose mismatch warning on any finalised note (the checker tally); no "role unresolved" encounter; word error rate, other unsupported lines and warned omissions recorded, not thresholded; (b) the same with a word-error-rate ceiling; (c) the practitioner's own rule.
  - Decide after: Task 2.3 defines the metrics; before any run of Task P.3.
  - Blocks: Task P.3. Recorded in `docs/testing/validation-harness.md` as rule v1, never adjusted after a run.
- [ ] 🟥 **3.6 Decide the role-play WAV retention.** [decision] (closes the retention question of Phase 3A Task 2.3)
  - Options: (a) keep the mock WAVs in one folder on the clinic computer, outside the repo and outside any synced folder, until D-S1 is decided and Phase 3B's gate has re-used them, then delete; (b) delete them once Tasks P.2 and P.3 are recorded.
  - Decide after: nothing further; before Task P.2.
  - Blocks: Task P.2. Recorded in `docs/security/retention-schedule.md` and `docs/testing/speaker-measurement.md`.

### Hardening stage

- [ ] 🟥 **H1** `/review-loop` over Phases 1–3 as one surface, to convergence. Cross-phase lenses: every exit path for note text; every rebuild of a session; every reader of the three v2 schemas; every document claim against the code.
- [ ] 🟥 **H2** `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`.
- [ ] 🟥 **H3** `/security-review` — same routing. Focus: the shadow boundary, schema upgrade, harness custody, text-free outputs.
- [ ] 🟥 **H4** Cross-family `/peer-review` (codex), sliced into rounds of at most about 15 files, with a confirmation round after any fix.
- [ ] 🟥 **H5** Build of record 0.2.0: push to `main`, run the CI `Release` workflow, record the row in `docs/release/pilot-builds.md`.
  - Done when: the row holds the commit, run id and both hashes.

### Phase P — Practitioner runs (normal terminal or Explorer; results recorded under each task as dated RUN lines)

- [ ] 🟥 **P.1 Install 0.2.0 on this computer.** Verify attestation and hash; close Clinic Scribe and Chrome; run `setup.exe`; reload the extension; restart Chrome. Check: the Status tab shows 0.2.0 and the shadow checkbox (off); an existing Past-sessions entry opens and copies; the audit CSV export has the two new columns with earlier rows as `normal`. Then tick shadow mode, record one mock consultation from the desktop and one from a disposable Cliniko draft, and confirm Write and Copy are refused with their reasons, the note cannot be selected, and the Past-sessions entry is marked and not copyable. Untick it.
  - Done when: each step's on-screen wording is reported and recorded here.
- [ ] 🟥 **P.2 The role-play set and its measurements.** After decision 3.6: about 10 mock consultations with a second person as the patient (one with a third voice), following `docs/testing/shipping-gate.md` (recorded live from the desktop, scored on rubric v1 under `clean`) and captured in parallel as labelled WAVs, plus one enrolment WAV. Run `scripts\measure-speakers.py` with `--enrolment`. Record: the 9.1 scoring table and decision line (in `plan-phase3a-note-pipeline.md` Task 9.1), the speaker numbers (Task 2.3 there and practitioner-profile Task 6.2), and decide D-S1. Initial the shipping-gate addendum first.
  - Done when: those four records exist and practitioner-profile Tasks 6.1–6.3 and Phase 3A Tasks 2.3 and 9.1 are marked done in their plans.
- [ ] 🟥 **P.3 The validation run.** After decision 3.5, on the developer build with the installed app closed: build the synthetic set, add the role-play folders with their scripts, run `scripts\run-validation.py` over at least 50 encounters. Record the report's totals and pass or fail here; enter every failure in the findings register.
  - Done when: the result is recorded against rule v1 with the commit and manifest hash. A fail stops the plan at this task until its findings are resolved or controlled and the run repeated.
- [ ] 🟥 **P.4 Ten shadow consultations at clinic 1.** After P.3 passes and consent sheet v2 is approved (Task 3.3): Flow 1, ten times, each with consent recorded in Cliniko as v2. Fill the pilot log; enter findings.
  - Done when: ten log rows with mode `shadow` exist, the audit export shows ten shadow rows on 0.2.x, and the R4 total is recorded.
- [ ] 🟥 **P.5 Twenty reviewed consultations at clinic 1.** Shadow mode off; Flow 3. Within them close note-learning Task P.2 (live transcription on a real recording, review edits across three consultations, one sample-note learning run, each writing style once).
  - Done when: twenty log rows with mode `normal` exist and note-learning Task P.2 is marked done in its plan.
- [ ] 🟥 **P.6 Clinic 1 exit gate.** Read `docs/pilot/exit-gate.md`: validation passed; ten shadow and twenty reviewed consultations logged; every high-risk finding resolved or explicitly controlled; the independent review of `docs/practice/` (including the VoxCeleb "research purposes" caveat) done and its changes applied; the deferred timing item revisited.
  - Done when: the gate line is signed and dated; routine use at clinic 1 is recorded in `PLAN.md` and `AGENTS.md`.
- [ ] 🟥 **P.7 Clinic 2.** When its Cliniko API-key permission exists: install the current build of record on its computer (installation plan P.1 steps), run the safeguards plan's P.1 and P.2 and the draft-write plan's `--test-write` and live write smoke there, then twenty reviewed consultations and its own exit gate.
  - Done when: clinic 2's gate line is signed, and the owed tasks are marked done in `plan-cliniko-workflow-safeguards.md` and `plan-cliniko-draft-write.md`. Clinic 1 does not wait on this task.

## Retained Follow-Up Items
(Filled at completion review.)

## Follow-Up Continuation Notes
(Filled at completion review.)

---
*Plan saved to: .cursor/plans/plan-pilot.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
