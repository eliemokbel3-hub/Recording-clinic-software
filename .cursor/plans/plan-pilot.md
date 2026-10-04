# Feature Implementation Plan
**Feature:** pilot
**Overall Progress:** `26%` (9 of 34 tasks)

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
- Loop config: executor=claude-p model="claude-opus-5-5" effort=high profile=default; peer=codex model="gpt-6-astra" effort=medium; architect=off; cadence=every-phase; caps=review:3,peer:5; gates=executor; cap-raise=executor; high-auto=on; peer-max=12; notify=action-only; scope=all; autocommit=on; isolation=none; merge=off; perms=scoped; liveness=10; monitor-delivery=auto; verify=composer
- COMPOSER RUN-STATE: /execute-loop run iso `pilot-20261004-104335-7c2e` (isolation=none, builds on `main` in this checkout), started 2026-10-04T10:45+11:00; runkeys stage-1 = Phase 1, stage-2 = Phase 2, stage-3 = Phase 3, stage-4 = Hardening stage, stage-5 = Phase P; probe logs `C:/Recording clinic software/.cursor/loops/stage-N-probe.log`; spawn helper `.cursor/loops/pilot-spawn.sh`, peer runner `.cursor/loops/pilot-peer-run.sh`; policy log `.cursor/loops/pilot-20261004-104335-7c2e-policy.log` (high-auto=on and gates=executor attested). Preflight PASS 2026-10-04 (harness probe: scoped grants run in-executor; pytest composer-run). Current: Phase 1 BUILT and converged (review-loop rounds 6–8; codex peer rounds 9–10, pass stage-1.p1 converged at peer round 2); full suites green (desktop 6017 passed / 9 skipped before round 9, the round-9 re-run 675 passed; extension 313); live-user smoke PASS on the developer build (practitioner, 2026-10-04T20:55); /document run; next the composer's Phase 1 commit, then Phase 2 (stage-2) with a fresh executor. Phase 1 executor session 47b50144-bffe-49a4-bff2-ef7853edb8f0 (discarded at the phase boundary).
- Last completed step: Phase 1 COMPLETE in the executor (stage-1, 2026-10-04T11:44:46+11:00). Tasks 1.1–1.9 are 🟩, uncommitted, with no commit made by the executor.
  - Suites: the full desktop run passed 6007 before the review-loop's fixes; the targeted re-runs after each fix passed (`test_ui_screens.py` 429, `test_unreviewed_review.py` 90, then 170 across `test_unreviewed_review.py`, `test_pilot_settings.py` and `test_ui_encounter.py`); extension qa passed 313. ruff "All checks passed!"; mypy "no issues found in 60 source files".
  - In-session `/review-loop`, rounds 6–8, reached its cap of 3 and converged on CRIT/HIGH/MED. Round 6: 1 MED, 1 LOW. Round 7: 1 MED (the Transcript-tab shadow line for a recovered recording, Task 1.7), 1 LOW. Round 8: 1 doc-only LOW. All applied.
  - Brief: `.cursor/loops/stage-1-handoff.md`.
- Current in-progress step: Phase 1 close-out at the composer seat. Done since the hand-back: full suites (desktop 6017 passed / 9 skipped, extension 313, ruff and mypy clean); the codex peer pass (round 9: 2 MED + 2 LOW verified, all fixed; round 10: confirmation, 0 findings); the practitioner's live smoke on the developer build (PASS, 2026-10-04); `/document`. Remaining: the Phase 1 commit.
- Operator brief (Phase 1):
  - What exists: a "Shadow mode (pilot)" checkbox on the Status tab, plus the version line.
  - A recording keeps the mode it had at Start, through Finish, an Unreviewed reopen and a crash-recovered checkout. Anything it cannot read counts as shadow.
  - In shadow mode, Write is refused by name with an audit record, before anything is reserved or sent.
  - Copy is refused at the button, keyboard, menu, line editor and Past sessions, and `_place_note_text` refuses as its last line.
  - A shadow Save writes no phrase, rule or wording; demoting a learned rule still applies.
  - The Session, Transcript, Note and Past-sessions tabs say so.
  - The audit row, the encounter record and the Past-sessions label are v2 and read v1 files as normal. The version is 0.2.0.
  - Watch in the peer pass: `_live_mode()` makes any review with no live session a shadow review, which fails closed. Generation is live-path only today; a future recovered-view generation must pass the checkout's mode.
  - Watch also the D13 demotion on a shadow Save, which is permitted and pinned by test.
  - Phase P.1 checks the installed wording.
- Immediate next action: the composer's Phase 1 commit. After that, Phase 2 (stage-2, Task 2.1). The cross-family plan peer loop ran 2026-10-04 (5 rounds, 8 findings, all applied; cap reached — see Review History). Task 2.3's metric contract drew a new finding in each of rounds 2–5, so give it a focused review when Phase 2 is built and before decision 3.5 is ratified.
- Open blockers / open questions: clinic 2's Cliniko API-key permission (blocks only Task P.7); a second person for the role-plays (Task P.2); an outside reviewer for `docs/practice/` (Task P.6).
- Last plan sync: 2026-10-04

## Review History
- 2026-10-04 round 1: 0 CRIT / 1 HIGH / 2 MED / 0 LOW; skew=none; action=amend-plan (plan peer-review; all three applied)
- 2026-10-04 round 2: 0 CRIT / 1 HIGH / 1 MED / 0 LOW; skew=none; action=amend-plan (plan peer-review; both applied; one practitioner decision — no learning in shadow)
- 2026-10-04 round 3: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=fix-induced; action=amend-plan (plan peer-review; applied — the metric contract moved from per-segment to word-level alignment)
- 2026-10-04 round 4: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=fix-induced; action=amend-plan (plan peer-review; applied — `warned` now needs the fact's own word to be uncovered high-risk evidence)
- 2026-10-04 round 5: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=fix-induced; action=amend-plan (plan peer-review; applied — checker warnings on the finalised note now count in the pass rule). Cap reached (5 of 5); loop stopped unconverged-by-rule: rounds 3–5 each found one new MED on the harness metric contract (Task 2.3, D8) and nothing elsewhere.
- 2026-10-04 round 6: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=none; action=none
- 2026-10-04 round 7: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=none; action=none
- 2026-10-04 round 8: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=none (cap reached, 3 of 3; converged on CRIT/HIGH/MED — the one LOW is a doc-only fix)
- 2026-10-04 round 9: 0 CRIT / 0 HIGH / 2 MED / 2 LOW (verified; peer labels 0 / 2 / 1 / 1); skew=none; action=fix (codex peer, pass stage-1.p1 peer round 1 of 5, composer seat; all four Fix-now applied by the executor fix leg; re-run 675 passed)
- 2026-10-04 round 10: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (codex confirmation, pass stage-1.p1 peer round 2 of 5; all four round-9 fixes confirmed; the peer pass converged)

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

### Round 6 - 2026-10-04 - pilot plan Phase 1, /review (round 1 of the Phase 1 code review-loop)

- Round status: Closed (2 applied; tests pending the composer's pytest run)
- Source: Claude Code (stage-1 executor session, `claude-opus-5-5`; in-session `/review-loop`, cap 3)
- Primary review baseline: `1500e2f` (HEAD; Phase 1 is uncommitted working-tree change). Changed files: the 13 source files, `session_mode.py` (new), 16 test modules plus 3 new (`test_pilot_settings.py`, `test_schema_versions.py`, `test_shadow_exits.py`), `docs/design-system.md`, `CHANGELOG.md`, the four version files. Skipped with reason: `extension/package-lock.json` (generated; only its two version strings moved, pinned by `test_install_layout.py`).
- Passes run: correctness/security; executor judgment; structural quality (none); post-fix regression (the two composer-run test fixes: test-only, no caller change); missed-issue.
- Missed-issue pass: re-read `ui/main_window.py` (`keep_label_for`, `session_mode_for`, `_live_mode`, `_open_adopted`, `_open_checkout_encounter`, `_on_write_requested`), `ui/note.py` (`_LineEditor`, `_place_note_text`, `_NotePanel`, `_copy_note`, `_apply_copy_binding`, `_write_control`, `_read_learning_status`, `_write_learned_rules`), `ui/transcript.py` `_keep_label`, `session.py` (`start`, `adopt_queued`, every `label=` Complete), `past_sessions.py` (`keeper`, `UNKNOWN_LABEL`), `audit.py` `_decode`, and the design-system bullet against the code; result: LOW-001.
- Finding verification: 5 candidates; 3 dropped (an absent `schema_version` reading as v2 normal: `encounter.enc` and `label.enc` are AEAD-sealed under keys only this app holds, so no other writer exists; the shadow refusal reading the write record: content-free and needed for Write's other lines; per-refresh reads of `pilot.json`: refresh runs on state change only, not on the 500 ms poll); 0 downgraded.
- Not findings (checked): every Complete without a resolved label falls to `UNKNOWN_LABEL` (shadow); the one `keeper` path; `generated.enc` stays display-only in Past sessions; the security documents are Task 3.4's.

#### Findings

**MED-001 — Task 1.2's Done-when has no test for "shadow after recovery" or "after an Unreviewed open"**

- Classification: n/a (round 1 of this code loop)
- Triage: Fix-now; Fix route: fix-on-fast (test additions)
- Why it matters: the mode must survive every rebuild (D1), and an unreadable record must read as shadow (D3). The recovered checkout's mode decides the Past-sessions label (copy refused or not), and the Unreviewed open decides whether the reopened saved note is display-only and Write refused. Neither path had a test, so a regression there would pass the suite.
- Current behaviour: `test_schema_versions.py` covered Start, Finish and `adopt_queued`; nothing drove `MainWindow._open_checkout_encounter` → `session_mode_for` / `keep_label_for` or the window's Unreviewed open with a shadow record.
- Desired behaviour: tests for both paths, both modes, plus v1, missing and newer records on the recovery path.
- Evidence: `desktop/src/scribe_desktop/ui/main_window.py:1570-1581` (`_open_checkout_encounter`), `:1846-1861` (`session_mode_for`), `:1178-1201` (`_open_adopted`); no test referenced `session_mode_for` or opened a shadow Unreviewed row.
- Pattern siblings: searched `session_mode_for`, `_open_checkout_encounter`, `open_unreviewed`, `_open_row` in `desktop/tests` — none with a mode; the Chrome route (`open_unreviewed`) shares `_open_adopted`, so the row test covers it.
- Regression risk: tests only.
- /fix decision: Applied
- /fix notes: `test_unreviewed_review.py` gains `TestShadowAfterRecoveryAndReopen`. Its recovery-checkout test runs on the real `_open_checkout_encounter` with SessionCrypto, no DPAPI, over five stored records: shadow, normal, the committed v1 bytes, missing and newer. In each case it asserts `session_mode_for`, the keep-label's shadow flag, and SHADOW once the checkout ends. It also adds Unreviewed-open tests in both modes (windows_only), checking the saved note's shadow state, Copy, the shadow line, Write's `shadow_session` line and the label. `_write_session` / `_unreviewed` take `mode=`. ruff and mypy are clean; pytest is pending (composer).
- /fix date: 2026-10-04
- /fix applied by: Claude Code (stage-1 executor)

##### LOW

- **[LOW]** LOW-001: `docs/design-system.md` (shadow-mode bullet) — it claimed the Status tab "heads with" the version line, and that a keyboard or menu Copy "says" the refusal line. The version sits under the intended-use line and warnings, and a keyboard or menu Copy on the non-selectable panel places nothing and shows nothing; the line is the disabled button's tooltip (Constraint 11: claim only what the code does). — Triage: Fix-now; Decision: Applied (wording corrected to match `StatusPanel`'s layout and `_apply_copy_binding` / `_NotePanel.copy_selection`)

ROUND-6 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 1); both applied.

### Round 7 - 2026-10-04 - pilot plan Phase 1, /review (round 2 of the Phase 1 code review-loop)

- Round status: Closed (2 applied; tests pending the composer's pytest run)
- Source: Claude Code (stage-1 executor session, `claude-opus-5-5`; in-session `/review-loop`, cap 3)
- Primary review baseline: `1500e2f` (HEAD; Phase 1 is uncommitted working-tree change), the same scope as round 6 plus round 6's fixes (`test_unreviewed_review.py`, `docs/design-system.md`).
- Passes run: correctness/security; executor judgment; structural quality (none); post-fix regression (round 6's test additions: test-only; the composer re-ran `test_unreviewed_review.py`, 90 passed); missed-issue.
- Missed-issue pass: re-read each Phase 1 task's text against the code it names — Task 1.7's "the same state shown for a live or recovered shadow recording" against every screen a recovered session lands on (`_open_checkout_encounter` → `_begin_checkout` → `_show_checkout_line`, the Transcript screen), and Task 1.2's "for both `on_start` and `start_linked`" against the tests; also `ui/bridge.py` (no copy path), the conftest pins, every Complete's label and the one `keeper`. Result: MED-002 and LOW-002.
- Finding verification: 4 candidates; 2 dropped (the bridge carries no note text, so it needs no shadow gate; an adopted session's Transcript screen is reached through `_begin_checkout` too, so it shares the MED-002 fix rather than being a separate finding); 0 downgraded.
- Round classification: MED-002 🆕 pre-existing since the Phase 1 build, missed by round 6 (not fix-induced); LOW-002 🆕 pre-existing test gap. Skew: none.

#### Findings

**MED-002 — a recovered shadow recording's Transcript screen did not say it was a shadow recording (Task 1.7)**

- Classification: 🆕 pre-existing (missed by round 6)
- Triage: Fix-now; Fix route: fix-on-fast
- Why it matters: Task 1.7 requires the shadow state to be "shown for a live or recovered shadow recording". A recovered session lands on the Transcript screen. There the only line was the link line, so the practitioner learned it was shadow only on reaching the Note tab. An unreadable record (shadow by D3) gave no cue at all until then.
- Current behaviour: `MainWindow._show_checkout_line` set only `models.checkout_link_line(...)`; the Session tab's line follows only the TRACKED session, which a recovered checkout is not.
- Desired behaviour: the Transcript screen shows `SHADOW_RECORDING_LINE` for a checked-out (recovered or adopted) session whose mode is not NORMAL, and hides it when the checkout ends.
- Evidence: `desktop/src/scribe_desktop/ui/main_window.py` `_show_checkout_line` / `_end_checkout_encounter`; `ui/transcript.py` had no shadow widget; `ui/session_screen.py:287` labels only the tracked session.
- Pattern siblings: the Note tab already shows its line (`NoteScreen.shadow_label`); Past sessions marks the entry; the Session tab covers live and queued recordings.
- Regression risk: low. The link line keeps its exact text, so the twelve pins in `test_ui_encounter.py` are unaffected. The shadow line is a separate label, shown or hidden only by `_show_checkout_line` and `_end_checkout_encounter`.
- /fix decision: Applied
- /fix notes: `TranscriptScreen.shadow_label` (fixed text `SHADOW_RECORDING_LINE`, hidden by default) and `set_shadow_line(shown)`; `_show_checkout_line` shows it when `session_mode_for(checkout.session_id) is not SessionMode.NORMAL`, and both clear paths hide it. Tests: `TestShadowAfterRecoveryAndReopen`'s five-way recovery test asserts the label visible exactly for shadow, missing and newer records, and hidden after the checkout ends. The two Unreviewed-open tests assert it shown in shadow and hidden in normal. The design-system bullet names the Transcript tab. ruff and mypy are clean; pytest is pending (composer).
- /fix date: 2026-10-04
- /fix applied by: Claude Code (stage-1 executor)

##### LOW

- **[LOW]** LOW-002: `desktop/tests/test_pilot_settings.py` — Task 1.2 names both Start entry points (`on_start` and `start_linked`), but only the desktop Start was tested. The code is shared (`SessionScreen._start`), so this is a test gap, not a defect. — Classification: 🆕 pre-existing; Triage: Fix-now; Decision: Applied. `test_a_chrome_start_takes_the_setting_too` is parametrized on and off and drives `start_linked` with a linked consent and context. The tracking fake now carries the context, so `bind_consent` accepts the linked consent.

ROUND-7 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 1); both applied.

### Round 8 - 2026-10-04 - pilot plan Phase 1, /review (round 3 of the Phase 1 code review-loop; the cap)

- Round status: Closed (1 applied, documentation only)
- Source: Claude Code (stage-1 executor session, `claude-opus-5-5`; in-session `/review-loop`, cap 3)
- Primary review baseline: `1500e2f` (HEAD; Phase 1 is uncommitted working-tree change), the round 6 scope plus round 7's fixes (`ui/transcript.py`, `ui/main_window.py` `_show_checkout_line` / `_end_checkout_encounter`, `test_unreviewed_review.py`, `test_pilot_settings.py`, `docs/design-system.md`).
- Passes run: correctness/security; executor judgment; structural quality (none); post-fix regression (round 7's: the composer re-ran `test_unreviewed_review.py`, `test_pilot_settings.py` and `test_ui_encounter.py` — 170 passed, the link-line pins unchanged); missed-issue.
- Missed-issue pass: `MainWindow._on_draft_ready`'s `_live_mode()` against a recovered checkout; `_on_write_requested`'s shadow branch and its audit call; `audit._decode` / `_upgrade_v1` / `begin` and the CSV columns; `ui/bridge.py` for any write or copy path; `ui/past_sessions.py`'s display panels; `SessionScreen._refresh_shadow_line`; every claim in the `CHANGELOG.md` 0.2.0 entry and the design-system bullet against the code. Result: LOW-003.
- Finding verification: 3 candidates; 2 dropped. (1) A recovered NORMAL checkout's review would be marked shadow through `_live_mode()`. Dropped: generation runs only for the live session, and the recovered view offers Complete or Discard only (`ui/transcript.py` module docstring), so no review exists there. (2) "Saving it teaches the app nothing" against the permitted D13 demotion. Dropped: a demotion lowers a learned shorthand's confirmations rather than teaching anything, and the Note tab's status line names it ("… will propose again (removed or declined)."). 0 downgraded.
- Round classification: LOW-003 🆕 fix-adjacent. Round 7 added the Transcript-tab cue, which showed that the Session-tab sentence's "recovered" had always over-claimed. Skew: none.
- Not findings (checked): the bridge has no Write or Copy path; Past sessions' panels are `NoTextInteraction`; a v1 `pre_audit` row upgrades to mode `normal`, which is right because it predates 0.2.0; `begin` leaves out a malformed version rather than refusing Start.

#### Findings

##### LOW

- **[LOW]** LOW-003: `docs/design-system.md` (the shadow-mode bullet) said the Session tab shows `SHADOW_RECORDING_LINE` "for a live, queued or recovered shadow recording". `SessionScreen._refresh_shadow_line` follows only the controller's TRACKED session. That covers a live recording and a queued one, including one reopened from Unreviewed, but not a crash-recovered checkout; that one is now cued on the Transcript tab (round 7 MED-002). Constraint 11: claim only what the code does. — Classification: 🆕 fix-adjacent; Triage: Fix-now; Decision: Applied. The bullet now says "for a live or queued shadow recording (one reopened from Unreviewed included)", and the `CHANGELOG.md` 0.2.0 entry names the Transcript tab beside the others. Documentation only; no test reads either sentence.

ROUND-8 RESULT: 1 finding (CRIT 0 / HIGH 0 / MED 0 / LOW 1); applied. The loop is at its cap (rounds 6–8) and converged on CRIT/HIGH/MED: round 8 found none, and its only finding is a doc-only LOW.

### Round 9 - 2026-10-04 - pilot plan Phase 1, independent cross-family codex peer-review (pass stage-1.p1, peer round 1 of cap 5)

- Round status: Closed (4 applied by the LEG-2 /fix, 2026-10-04T12:04:04+11:00; tests pending the composer's pytest run)
- Source: Codex peer (`gpt-6-astra`, reasoning medium, read-only sandbox; composer seat, three file-scoped slices A/B/C run in one activation, leg p1-r9)
- Recorded by: the composer, verbatim from each slice's final answer (`.cursor/loops/stage-1-peer-r9{A,B,C}.log`, transcribed from the last answer block)
- Primary review baseline: `1500e2f` (HEAD); Phase 1 uncommitted in the working tree after review-loop rounds 6–8; full suites green before the round (desktop 6017 passed / 9 skipped, extension 313, ruff and mypy clean).
- Slices: A = the shadow boundary (note text exits, Write, Past sessions); B = the mode on the session (settings, encounter record, audit v2, window wiring); C = UI-screen tests, remaining test edits, version pins, documents.

#### Peer findings (verbatim)

- **PR-MED-A01** (MED, test-harness, `desktop/tests/test_shadow_exits.py:102`): The exit enumeration silently permits additional widgets and send callers at already-listed locations, weakening Constraint 3’s future-change guard. Another default-selectable `QPlainTextEdit()` in `NoteScreen.__init__` produces the existing set entry; another `write_draft_note` call anywhere in `draft_write.py` also passes. — Evidence: `built.add((_relative(path), scope, str(name)))`; line 140: `callers.add(_relative(path))`. Recommendation: Fix-now — Track individual construction/send sites and their counts, and verify with in-memory mutation cases that an additional ungated widget or send fails the checks. /fix decision: Applied
  - /fix notes:
    - `desktop/tests/test_shadow_exits.py` now COUNTS sites: `Counter`s `_PLACEMENT_CALLERS`, `_BUILT_WIDGETS` and `_SEND_CALLERS`.
    - The send is pinned to its function, `draft_write.send_write`, which takes only a `PreparedWrite`, and only `prepare_write` makes one. It is no longer pinned only to its file.
    - New in-memory mutation tests use `_with_extra`, which appends a statement to a named function in a re-parsed copy of the source:
      - a second `_place_note_text` in `NoteScreen._copy_note`;
      - a second `QPlainTextEdit()` in `NoteScreen.__init__`, the peer's exact case;
      - a second `write_draft_note` in `send_write` and in `prepare_write`.
      Each must change the count.
    - The current counts (each 1) were checked by grep against `ui/note.py:528,609,1830`, `ui/past_sessions.py:105`, `ui/note.py:357,2302`, `ui/past_sessions.py:498` and `draft_write.py:1348`.
    - Docstring updated. Pattern siblings: none (the selectable-flag test already lists exact scopes, and a flag needs no count). ruff clean; pytest pending (composer).
  - /fix date: 2026-10-04
  - /fix applied by: Claude Code (stage-1 executor, LEG 2)
- Verification counts (slice A): 2 claims checked, 1 confirmed, 1 dropped as unverifiable.
- **PR-HIGH-B01** (HIGH, behavioral, `desktop/src/scribe_desktop/encounter.py:217`): Persisted encounter bytes missing both `schema_version` and `mode` are accepted as NORMAL, violating D3’s unknown-mode fallback. With otherwise valid consent/context, adoption carries that inferred mode into review, bypassing shadow restrictions. — Evidence: the rejection requires `"schema_version" in data`; line 208 defaults to `mode: SessionMode = SessionMode.NORMAL`; `from_bytes` directly calls `cls.model_validate_json(blob)` at line 234; `session.py:1556` adopts `mode=record.mode`. Recommendation: Fix-now — Require an explicit supported version when parsing persisted bytes and require mode for v2; retain constructor defaults separately and add missing-field recovery/adoption tests. /fix decision: Applied
  - /fix notes:
    - `desktop/src/scribe_desktop/encounter.py` `EncounterRecord.from_bytes` now pre-parses the bytes. A blob that is not a JSON object naming `schema_version` raises `EncounterUnavailable`, which every rebuild reads as shadow (D3).
    - A v2 blob without `mode` was already refused by `_mode_by_version`.
    - The constructor defaults are kept, since `EncounterRecord(consent=…)` builds new records with them.
    - `RecursionError` was added to the caught set for the new `json.loads`.
    - Callers checked: `read_encounter_record`, which `session.py:1543` and `ui/main_window.py:1578` call. Every writer uses `to_bytes()`, which names the version, and the committed v1 fixtures name it too.
    - Tests:
      - `test_schema_versions.py`: `_unversioned()`; `test_bytes_naming_no_version_are_refused` (no mode, `normal`, `shadow`; both fixtures); `test_a_new_record_still_takes_its_defaults`; `test_an_unversioned_record_refuses_the_open` (adoption: `consent_unavailable`, Start unaffected).
      - `test_unreviewed_review.py`: the recovery checkout's parametrize gains `unversioned`, which carries mode `normal` and must still read as SHADOW and show the Transcript shadow line.
    - ruff and mypy clean; pytest pending (composer).
  - /fix date: 2026-10-04
  - /fix applied by: Claude Code (stage-1 executor, LEG 2)
- **PR-HIGH-B02** (HIGH, behavioral, `desktop/src/scribe_desktop/note_config.py:1127`): A present pilot file containing `{}` or `{"schema_version":1}` silently turns shadow mode OFF despite containing no readable setting. Subsequent recordings become normal, allowing export and learning instead of applying D3’s fail-closed behavior. — Evidence: `shadow_mode: bool = Field(default=False, strict=True)`; line 1165 parses through `PilotSettings.model_validate_json(blob)`; line 1168 returns `unreadable=False`; `ui/session_screen.py:402` maps the resulting false value to `SessionMode.NORMAL`. Recommendation: Fix-now — Require `shadow_mode` in persisted settings, return ON/unreadable when absent, and test both incomplete objects through the reader and Start funnel. /fix decision: Applied
  - /fix notes:
    - `desktop/src/scribe_desktop/note_config.py` `PilotSettings.shadow_mode` is now `Field(strict=True)` with no default. `{}` and `{"schema_version": 1}` fail validation in `read_pilot_settings` and read as shadow ON, unreadable (D3).
    - Docstring updated.
    - Callers checked: every `PilotSettings(` passes `shadow_mode` (`ui/main_window.py:361` and `tests/test_pilot_settings.py`).
    - Tests in `test_pilot_settings.py`: both blobs join the unreadable parametrize (the reader and `shadow_mode_on`), and `test_an_unreadable_setting_starts_a_shadow_recording` is parametrized over `{garbled`, `{}` and `{"schema_version": 1}` through the real Start funnel.
    - ruff and mypy clean; pytest pending (composer).
  - /fix date: 2026-10-04
  - /fix applied by: Claude Code (stage-1 executor, LEG 2)
- Verification counts (slice B): 2 claims checked, 2 confirmed, 0 dropped as unverifiable.
- **PR-LOW-C01** (LOW, test-harness, `desktop/tests/test_ui_screens.py:8510`): The clipboard test’s “saved” checkpoint can pass when shadow Save fails, leaving post-save protection untested — Evidence: `note_screen.save()` is followed only by `assert note_screen.current_note() is not None`, which the helper already asserts before Save at line 8042. `ui/note.py:2126–2130` catches save failures and returns without marking the note saved. Recommendation: Fix-now — Assert `_note_saved` or the successful saved review state before exercising the post-save copy routes. /fix decision: Applied
  - /fix notes: `desktop/tests/test_ui_screens.py`:
    - asserts `not _note_saved` before Save;
    - after Save, asserts `_note_saved` and that `message_label` starts with "Note saved.";
    - then runs the post-save copy routes. Only `NoteScreen.save` (success, :2132) and `clear` write that label on this path, and the existing `current_note() is not None` check rules out a clear.
    - Pattern siblings: none. ruff clean; pytest pending (composer).
  - /fix date: 2026-10-04
  - /fix applied by: Claude Code (stage-1 executor, LEG 2)
- Verification counts (slice C): 2 claims checked, 1 confirmed, 0 dropped as unverifiable.

PEER-ROUND-9-A RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 0).
PEER-ROUND-9-B RESULT: 2 findings (CRIT 0 / HIGH 2 / MED 0 / LOW 0).
PEER-ROUND-9-C RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 1).

ROUND-9 RESULT: 4 findings (CRIT 0 / HIGH 2 / MED 1 / LOW 1) — peer labels; verified classification pending LEG 1.

- Journal ID map (composer; the slice IDs are not journal-key grammar): PR-HIGH-B02 = PR-HIGH-052; PR-HIGH-B01 = PR-HIGH-053; PR-MED-A01 = PR-MED-054; PR-LOW-C01 = PR-LOW-055.

#### LEG 1 verified tuples

Verified 2026-10-04T11:59:04+11:00 by the stage-1 executor (`claude-opus-5-5`), by reading the current working tree. No file other than this block was edited.

- PR-HIGH-B02: peer=HIGH/behavioral → materiality=behavioral severity=med surface=production rec=Fix-now — `desktop/src/scribe_desktop/note_config.py:1127` `shadow_mode: bool = Field(default=False, strict=True)` lets `{}` or `{"schema_version":1}` validate at :1165 and return `PilotSettingsRead(shadow_mode=False, unreadable=False)` at :1168. That is a present file with no readable setting reading as OFF, against D3 and the reader's own docstring at :1150–1153.
  - Downgraded from HIGH: the app always writes the full model (`to_bytes` dumps both fields through the atomic `_write_config_file`), so only an outside edit produces such a file. The result is also visible: the Status checkbox shows unticked, and the Session tab shows no setting line.
  - In Phase 1 scope (Task 1.1). Not production-impacting: no dependency, env var, migration or deploy-config. Make the field required: every `PilotSettings(` constructor (`ui/main_window.py:361` and the tests) already passes `shadow_mode`.
- PR-HIGH-B01: peer=HIGH/behavioral → materiality=behavioral severity=low surface=production rec=Fix-now — `desktop/src/scribe_desktop/encounter.py:217` exempts `"schema_version" not in data`; with the :214 default and `mode` defaulting NORMAL at :208, bytes with neither key parse as v2 NORMAL through `from_bytes` at :234.
  - Not reachable in practice: `encounter.enc` is sealed under the session key with its own associated data. Every record this app ever wrote carries `schema_version`, because v1's and v2's `model_dump_json` include defaults, and the committed v1 bytes in `tests/test_schema_versions.py:67–79` do too. Round 6 dropped the same scenario on these grounds.
  - It is still a fail-open gap against D3 and against the class docstring at :198–200 ("a v2 record without one … is refused").
  - The fix is cheap, in `from_bytes` only: require an explicit `schema_version`, and `mode` at v2. The constructor's defaults are kept, since `EncounterRecord(consent=…)` relies on them.
  - In Phase 1 scope (Task 1.2). Not production-impacting.
- PR-MED-A01: peer=MED/test-harness → materiality=behavioral severity=med surface=test-harness rec=Fix-now — `desktop/tests/test_shadow_exits.py:85,102` collects `built` as a set of (file, scope, class), so a second `QPlainTextEdit()` in `NoteScreen.__init__` adds nothing. It is selectable by Qt default, and :119–132 only catches EXPLICIT selectable flags.
  - Likewise `:136,140` collects callers as a set of files, so a second `write_draft_note` call anywhere in `draft_write.py` passes, including one outside the `prepare_write` refusal path.
  - The guard is weaker than Task 1.5's Done-when ("so a new one fails until gated") and the module docstring at :1–2.
  - Materiality is "behavioral" for the guard only: no production code is wrong today. The current widgets and the one send were checked by hand in rounds 6–8.
  - In Phase 1 scope (Task 1.5). Not production-impacting.
- PR-LOW-C01: peer=LOW/test-harness → materiality=behavioral severity=low surface=test-harness rec=Fix-now — `desktop/tests/test_ui_screens.py:8510–8512`: after `note_screen.save()` the only checkpoint is `current_note() is not None`, which already held before Save.
  - `ui/note.py:2124–2130` returns on a failed `on_save` without setting `_note_saved` (:2131), so "saved: a normal note would copy here" is not proven reached.
  - The production refusal itself is correct in every state. The gap is that the test does not prove its own precondition.
  - In Phase 1 scope (Task 1.5). Not production-impacting.

LEG 2 /fix decisions (2026-10-04T12:04:04+11:00; tuple-block copy owner per `/fix` Step 2.9):
- PR-HIGH-B02 (journal PR-HIGH-052): /fix decision: Applied — `note_config.PilotSettings.shadow_mode` is required; `{}` and `{"schema_version":1}` read as shadow ON, unreadable.
- PR-HIGH-B01 (journal PR-HIGH-053): /fix decision: Applied — `EncounterRecord.from_bytes` refuses bytes that do not name `schema_version`; the constructor defaults are kept.
- PR-MED-A01 (journal PR-MED-054): /fix decision: Applied — `test_shadow_exits.py` counts every site; in-memory mutation tests prove each count catches an added site.
- PR-LOW-C01 (journal PR-LOW-055): /fix decision: Applied — the copy test asserts that Save succeeded before the post-save checks.

Fix-delta self-check: PASS — re-read the 9 applied hunks across 6 files. Findings: 2 production read paths changed (`note_config.py`, `encounter.py`), and every constructor and writer was checked against them. 4 test modules changed; each new case fails on the pre-fix code. No drive-by edits.

Cap verdict: accept — production-behavioral — B02 (med) and B01 (low) change production read paths (`note_config.read_pilot_settings`, `EncounterRecord.from_bytes`). They warrant one confirmation round after the fixes, and pass stage-1.p1 is at peer round 1 of cap 5, so no raise is needed. A01 and C01 are test-guard tightenings.

### Round 10 - 2026-10-04 - pilot plan Phase 1, independent cross-family codex peer-review, confirmation (pass stage-1.p1, peer round 2 of cap 5)

- Round status: Closed (0 findings; the pass converged)
- Source: Codex peer (`gpt-6-astra`, reasoning medium, read-only sandbox; composer seat, one slice X over the round-9 fix surface, leg p1-r10)
- Recorded by: the composer, verbatim from the slice's final answer (`.cursor/loops/stage-1-peer-r10X.log`)
- Baseline: `1500e2f` (HEAD) plus the uncommitted Phase 1 tree after the round-9 fix leg; the composer's re-run of the six touched modules was 675 passed.

#### Peer findings (verbatim)

- No findings.
- Verification counts (slice X): 4 claims checked, 4 confirmed, 0 dropped as unverifiable.
- Confirmation: PR-HIGH-B02 closed — `desktop/src/scribe_desktop/note_config.py:1129` requires `shadow_mode: bool = Field(strict=True)`; validation failures return shadow ON/unreadable at line 1169. `desktop/tests/test_pilot_settings.py:59` covers valid on/off; lines 403–420 cover incomplete files through Start.
- Confirmation: PR-HIGH-B01 closed — `desktop/src/scribe_desktop/encounter.py:243` requires `"schema_version" in data`, otherwise raising `EncounterUnavailable` at line 247. This parsing change adds no reader caller. `desktop/tests/test_schema_versions.py:127` covers v1 compatibility; lines 169–183 cover missing versions and constructor defaults; line 303 covers refused adoption.
- Confirmation: PR-MED-A01 closed — `desktop/tests/test_shadow_exits.py:116` increments each widget site; lines 165, 198 and 229 compare counts against nonempty expected inventories. Mutation cases at lines 170, 201 and 232 detect repeated placements, widgets and sends; empty inventories cannot pass.
- Confirmation: PR-LOW-C01 closed — `desktop/tests/test_ui_screens.py:8510` asserts `not note_screen._note_saved` before Save; lines 8515–8516 assert `_note_saved` and `"Note saved."` before the post-save copy checks. The test uses `_fake_clipboard` at line 8493.

PEER-ROUND-10-X RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

ROUND-10 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0); all four round-9 findings confirmed closed. Pass stage-1.p1 converged at peer round 2 of 5.

## Tasks
Phases are grouped for `/execute-loop`: Phase 1 is the schema and safety-boundary phase and stands alone; Phase 2 is developer-only tooling; Phase 3 is documents and two decisions. Each task defers to `Validation / Verification` for the suite run unless it says otherwise. Paths are under `desktop/src/scribe_desktop/` unless they start with another folder; line numbers are in `Key Findings`.

### Phase 1 — Shadow mode and audit v2 (build 0.2.0)

- [x] 🟩 **1.1 Pilot settings and the Status tab.** Add a pilot-settings model and accessor in `note_config.py` beside `DevSettings` (`config\pilot.json`, one field `shadow_mode`, written through `_write_config_file`); absent = off, present but unreadable = ON (D3). In `ui/main_window.py` `StatusPanel`, add a "Shadow mode (pilot)" checkbox built like the developer-writes checkbox, a line naming an unreadable file, and a line showing the app version (`__version__`). Wording follows `docs/design-system.md`.
  - Done when: tests cover absent, valid on, valid off and unreadable, each through an injected config root; the checkbox round-trips; the version line is pinned against `__version__`.
- [x] 🟩 **1.2 The mode on the session and the encounter record.** Define `SessionMode` (`normal` / `shadow`). Add it to `RecordingSession` and `EncounterRecord` (v2; v1 reads as `normal`). `SessionController.start` takes the mode from the Start funnel (`ui/session_screen._start`, for both `on_start` and `start_linked`), which reads the pilot setting at the click. Carry it through `adopt_queued`, the recovery checkout and `_open_adopted`'s construction; a session whose record cannot be read is treated as shadow (D3). Constraint 1.
  - Done when: a session started with the setting on is shadow after Start, after recovery, after `adopt_queued` and after an Unreviewed open; changing the setting mid-recording changes nothing; the `read_encounter_record` call-count spies still pass unchanged; v1 fixture bytes read as `normal`.
- [x] 🟩 **1.3 Audit row v2.** In `audit.py` add `mode` (enum) and `app_version` (pattern, optional) to `AuditRow`; `AuditLog.begin` receives both from `SessionController.start`; upgrade v1 rows in `_decode` before validation (D6, D7); add both to `CSV_COLUMNS` and `_csv_values` together. Move the tests' "newer version" fixtures from 2 to 3. State in a comment that flat tokens need no new `_PAYLOAD_SIGNATURES` entry.
  - Done when: `test_audit.py`'s constraint, forbidden-name, tripwire and CSV-header tests pass with the new fields; a stored v1 row exports with mode `normal` and an empty version; a v3 row reads as `_NEWER` without refusing Start.
- [x] 🟩 **1.4 Write refused by name.** Add `shadow_session` to `draft_write.WriteRefusalName`; refuse in `refuse_before_read` and `ui/models.write_control` beside `dev_build_writes_off` (D4); add its `WRITE_LINES` entry (no "copy" in the text) and place it deliberately in or out of `WRITE_UNCERTAIN_PREFIXED`; `MainWindow._on_write_requested` passes the session's mode.
  - Done when: for a shadow session no request is made (the transport spy sees zero calls), the Write control shows the shadow line, the audit row records the refusal name, and the pinned `WRITE_LINES` / prefix-set tests are updated in the same change.
- [x] 🟩 **1.5 Copy refused by name; the note body display-only.** In `ui/note.py` add a shadow reason separate from `_copy_ready` (D5): it disables the Copy button with its reason, makes `copy_selection` (keyboard and context menu) a refusal, keeps the note body non-selectable, and `_place_note_text` refuses as the last line. `begin_review` and `show_saved_note` receive the mode from `MainWindow`. Write's "saved" derivation is untouched.
  - The inline line editor (`_LineEditor`, a `QLineEdit` created at `ui/note.py:1730` holding the line's existing text) keeps editing in shadow but its native Copy and Cut — shortcuts and its context-menu actions — are refused and drag is off; Paste, typing, Undo and Escape are unchanged (peer round 1, PR-HIGH-001).
  - Done when: with the fake clipboard, every caller of `_place_note_text` places nothing for a shadow session and behaves exactly as before for a normal one; the body's interaction flags are display-only in shadow at every review state; the line editor's Copy, Cut, context menu and drag place nothing in shadow and work as before in normal mode; a test enumerates `_place_note_text`'s callers AND every widget class in `ui/note.py` and `ui/past_sessions.py` that can hold note text, so a new one fails until gated (Constraint 3).
- [x] 🟩 **1.6 Past sessions.** Carry the shadow flag through `KeepLabel` / `keep_label` and `MainWindow.keep_label_for` into `PastSessionLabel` v2 (v1 = not shadow); `UNKNOWN_LABEL` is shadow. `ui/past_sessions._copy_reason` / `on_copy` refuse a shadow entry with a named reason; the list marks the entry as a shadow recording.
  - Done when: a completed shadow session's entry is marked and its Copy refused; a v1 label still opens and copies; an unknown label refuses; the entry is still written and verified before the session key goes (existing custody tests unchanged).
- [x] 🟩 **1.9 No learning from a shadow Save** (peer round 2, PR-HIGH-021; practitioner decision 2026-10-04; numbered 1.9, built here). In `ui/note.py`, a Save of a shadow session writes no learned phrase (`_write_learned_phrases`, :1477), no learned rule (`_write_learned_rules`, :2047 → `append_learned_rules`) and replaces no learned wording (`replace_learned_rule_wording`, :2139); the queue lines in `ui/note_review.py` say "not learned: shadow recording" instead of "will learn … when you save". Safety-direction demotions of a rule the practitioner corrected still apply. D13.
  - Done when: after a shadow Save with an eligible typed line, an edited learned rule and a queued phrase, the cue file and the learned-rules store are byte-identical to before (except a demotion count), the Practitioner tab shows nothing new, and a following normal recording offers no proposal carrying that wording; the same three actions in a normal session learn exactly as today.
- [x] 🟩 **1.7 The Session tab says so.** `ui/session_screen.py`: a line above Start while the setting is on ("new recordings are shadow recordings: their notes cannot be copied or written to Cliniko"), and the same state shown for a live or recovered shadow recording. Add the cue to `docs/design-system.md`.
  - Done when: the line appears and disappears with the setting, and a live shadow recording stays labelled after the setting is turned off.
- [x] 🟩 **1.8 Version 0.2.0 and the two-way schema tests.** Bump every pinned version location. Add a test module that, for each of the three v2 schemas, reads committed v1 fixture bytes with the new code, and asserts the "newer than current" behaviour the older build relies on (audit `_NEWER`, label unreadable and Copy closed, encounter `EncounterUnavailable` with Start unaffected).
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
