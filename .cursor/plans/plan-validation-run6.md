# Feature Implementation Plan
**Feature:** validation-run6 — version 0.3.4, the fix that run 6 must pass before shadow mode can be turned off (`plan-pilot.md` P.5 decision (a), 2026-10-22):
- Check 4's omission warning on any uncovered clinician line;
- a new review warning where speech was detected but no words were transcribed;
- hedge scope and lexicon, through one function shared with the harness;
- the greeting gap, decided as a dated vocabulary question;
- a written decision, BEFORE run 6, on the recogniser-level and tone-level residues (rule v1 kept, or a ratified rule v2);
- a fresh held-out set by an independent author, written predictions before the build, and run 6 as the run of record.

**Overall Progress:** `18%` (6 of 33 tasks)

## Lifecycle State
- Active

## Completion Status
- Completion timestamp: —
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- **Parent plans:**
  - `plan-pilot.md`: its P.5 decided (a) on 2026-10-22 — shadow mode stays on until a validation run passes; "the fix is a new 0.3.4 plan". This is that plan. The clinic 1 exit gate's "Validation passed" also waits on it.
  - `plan-validation-pass.md` (0.3.3, Completed — Follow-ups Retained): run 5 at `1e5707d` FAILED as predicted (44 / 6; held-out 14 / 8). Its retained item "the chooser's middle-elided labels cut a front mark short" is taken here (Task 1.2). Its other four retained items stay there (Deferred below).
- **Related plans:**
  - `plan-invented-text-guard.md` (0.3.2): the suspect mark, `line_marks`, the forward-tolerant reader `unknown_review_warning`, and its C2 (constants decided once, never tuned after a run of record) — which this plan's missed-speech thresholds follow.
  - `plan-ui-refresh.md` (0.4.0, branch `claude/ui-refresh-bf9282`, its own worktree, NOT merged): its Review screen reads warning codes, the separately-acknowledged set and the chooser marks as data. **Integration note (Step 3.5, 2026-10-22: "at its merge"):** nothing here touches that branch; at its merge the Review screen adopts this plan's two new codes, their copy, their place in the separately-acknowledged set, the `[gap?]` mark and the shortened chooser marks.
  - `plan-clinic-smoke.md`: D9 (nothing tuned after a run), D12 (nothing per consultation in a tracked file). Its kept recordings are the real-speech measurement source of Task 0.2 (integers only).
  - `plan-cliniko-workflow-safeguards.md` D8: the live new-consultation warning shares `consultation_phrases`' lists (C7).
- **Follow-up plans:** none yet; candidates under Deferred / Excluded.

## Goal
Make 0.3.4 the build whose run of record (run 6) can honestly PASS the gate the practitioner ratified in Task 0.8, so that `plan-pilot.md` P.5's shadow-off question can be put again. The rule, the cue file and the scripts' facts are never changed to make a run pass (pilot Constraint 12); a rule change is allowed only as the practitioner's written, dated decision BEFORE any prediction (Task 0.7 — taken).

What failed in run 5 and the held-out run, and what this plan does about each:

| Group | Encounters (run 5 / held-out) | Cause | This plan |
|---|---|---|---|
| (1) Uncued clinician line | held-out: 5 silent omissions (F-089…); shadow use: F-100, F-101 | No cue routes the line and Check 4 flags no word in it, so nothing warns | Phase 1: the new code `clinician_line_omitted` (decision 0.3: (b)) |
| (2) Dropped clause | `syn-22` (F-087) | The recogniser dropped a clause; the words never existed in the transcript | Phase 2: the missed-speech warning (Step 3.5, 2026-10-22: Include in plan); R1 under rule v2 for what it does not catch |
| (3) Misheard word | `syn-28` (F-071, F-072); held-out: 2 one-word errors (F-091, F-097) | Recogniser accuracy | R1 under rule v2 (decision 0.7: (b)); a larger model is Excluded |
| (4) Doubt by tone or elsewhere | `syn-30`, `syn-35`; held-out: 3 hedges (F-095, F-096, F-098) | Unlisted hedge, a hedge in a neighbouring segment, or no spoken hedge at all | Phase 3: lexicon and scope (decision 0.6); R2 for doubt carried by tone only |
| (5) Unlisted greeting | `syn-38`, `syn-46`; held-out: 1 (F-092) | The greeting is not on the frozen list | Decision 0.5: (a), lists frozen, R3 (2026-10-22) |

### Honest forecast
Written before any measurement and not tuned toward:
- **Widening Check 4 changes NONE of run 5's six failures.** On the 50 seen scripts a pass can come only from decisions 0.5–0.7 (residue classes, vocabulary) and, for `syn-22`, from the missed-speech warning if the dropped clause leaves a measurable gap — unknown until Task 0.12.
- **The 50 scripts and the first held-out set are no longer blind.** This plan targets their failures, so a pass on them is regression evidence, not proof. The blind test is `validation/heldout-2/` (Task 0.10). The gate chosen in 0.8 therefore includes it.
- **The 50's ceilings are fitted.** Rule v2's ceiling of 2 per class on the 50 EQUALS run 5's R1 count (`syn-22`, `syn-28`) and R3 count (`syn-38`, `syn-46`): zero headroom, set knowing the failures. That is why the 50's pass counts for nothing on its own.
- **A `heldout-2` failure is a finding, never a tuning target.** Budget for a `heldout-3` and a 0.3.5 if it fails.
- **The first held-out set's two one-word recogniser errors** would each be R1 at best; under its ceiling of 1 they breach it unless the missed-speech warning or a review mark covers one — and for a numeric fact the review-mark term is nearly always met (D8). Stated so the ceiling is read knowing it.
- A PASS is an outcome to report, never a target.

## Planning Extraction Summary
Populated 2026-10-22 from:
- the Plan Mode draft (Opus 5.5, approved by the practitioner through ExitPlanMode);
- the planning brief from the session "0.3.4 planning" (the practitioner's scope decisions 1–5, relayed);
- a design critique of the first draft (a Plan subagent) and an exploration of the code (an Explore subagent);
- the first `/review-plan` pass (Opus 5.5; Step 3.5 gate answered by the practitioner) and the decisions 0.1–0.8 ("take all the recommendations");
- a second `/review-plan` pass on Fable 5.1 the same day: three read-only lenses (coverage, practicality, simplicity and risk) as subagents over the plan and the real code, 36 findings reconciled into this version, and one practitioner answer (the hedge scope reuses `note.ends_mid_sentence`).

Every file:line was checked against `0be35d7`; HEAD moved to `4ff5f26` during planning (a one-file edit to `plan-clinic-smoke.md`), so `desktop/src` is unchanged and every reference holds. No `/explore` scratch was consumed: the two existing ones (`explore-cliniko-integration.md`, `explore-practitioner-profile.md`) are unrelated.

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Opus 5.5 (Plan Mode and the first `/review-plan`), re-hardened on Fable 5.1 (the second `/review-plan`). The build runs through `/execute-loop`: executor `claude-opus-5-5` high, cross-family peer codex `gpt-6-astra` medium, verify=composer, isolation none. Every measurement over kept recordings, the audio diagnosis if the agent shell cannot see the models, run 6, the install and the smoke are run by the PRACTITIONER from a normal terminal (`docs/lessons.md`, MSIX). Tier-gap dosing applied: the decisions' options and outcomes, the new codes' predicates, the anchor rules, the residue classes' mechanical tests, the measurement outputs, the pin inventory and the rollback behaviour are locked here.

### Agreed Scope (Build Now — 0.3.4)
- **Phase 0:** the warning budget (0.1, taken); the measurement (0.2); six practitioner decisions (0.3–0.8, taken; 0.4's values owed after 0.2); one dated commit for the lexicons and the missed-speech constants (0.9); fixtures and lints parameterised over a set table (0.11, BEFORE the set exists); a fresh held-out set by an independent author (0.10); the diagnosis, the `h2-NN` cases and the written predictions (0.12).
- **Phase 1:** the new code `clinician_line_omitted`, its copy, acknowledgement and count line, and short chooser front marks (the P.2 observation; Step 3.5: Include in plan).
- **Phase 2:** the missed-speech warning `speech_without_words` (Step 3.5: Include in plan).
- **Phase 3:** hedge scope through one shared function, in the product and the harness (decision 0.6).
- **Phase 4:** the harness — the warned amendments, `reference_document`, the residue classifiers, rule v2's set layer, the report.
- **Phase 5:** documents and version 0.3.4, the rollback line.
- **Hardening H1–H5**, then **Phase P:** run 6 on the three sets, install and smoke, the register and the P.5 question.

### Deferred — Actionable Later
- **The practitioner's own greetings and closings** (the later amendment they described on 2026-10-13, repeated 2026-10-22). A new dated vocabulary decision with a repeated run, after they have listened for their phrases in shadow use. `Risk if deferred: minor` (Start per patient is the primary control) · `Revisit by: when the practitioner can name their phrases`.
- Carried from `plan-validation-pass.md`, unchanged and still owned there: the one-click undo of a false boundary; the transcript divider at the possible next patient (its home is the ui-refresh Review screen); the mark pairing a retracted statement with its carried correction; the carry's question-answer hop.
- **The ui-refresh adoption** of the two new codes, the `[gap?]` mark and the shortened marks — at that branch's merge (integration note in Plan Lineage). `Risk if deferred: correctness` (the Review screen would show the new codes as unknown review warnings until adopted) · `Revisit by: the ui-refresh merge`.

### Excluded — Revisit Only If Needed
- **A larger Whisper model / a new model pack** (Step 3.5, 2026-10-22: "Excluded, own plan later"). Revisit if run 6, `heldout` or `heldout-2` exceeds the R1 ceiling.
- Any edit to rule v1's file, `validation/config/section_cues.json`, or the 50 scripts' and the first held-out set's facts (C2).
- Widening the hedge list or the greeting list from the seen failures (C3: only a blind, sourced widening is allowed).
- Changing the invented-text guard's constants (its own C2).
- A turn-level carry or any change to routing (the omission is warned, never re-routed).
- Folding `clinician_line_omitted` into `high_risk_omission` with a sub-reason field: `NoteWarning` is `extra="forbid"`, so a new field would make 0.3.3 refuse every note 0.3.4 writes, and it would change what the harness's 0.3.3 `warned` comparison and the existing copy mean.
- A per-warning line number in the review list's copy: `WarningCopy` is per code and `summarise_warnings` groups by code; the anchor is shown by a mark instead (D2).

### Accepted Assumptions — Revalidate Later
- The practitioner presses Start per patient from that patient's Cliniko note (stated 2026-10-13 and 2026-10-22), so the next-patient boundary is a backstop. Revalidate if shadow use shows a forgotten switch (a register row).
- The provider routes whole segments (`note._assemble_note_request` builds one `NoteUtterance` per segment, `note.py:1338`), so "an uncovered clinician word" and "an uncovered clinician line" differ only for partly-quoted segments. Revalidate in Task 0.2's counts.
- A dropped clause usually leaves either a textless VAD segment or a gap between word timestamps. Unproven: Whisper may stretch neighbouring word stamps over the gap. Task 0.12 records whether `syn-22`'s gap is visible.
- There are enough consented kept recordings WITH an enrolled speaker to measure the clinician-line count. If fewer than 3 exist, decision 0.3's (c) test falls back to the synthetic counts, and the plan records that the budget was not tested on real speech.
- **Named residues accepted 2026-10-22 (the second pass's gate):** (i) a hedge in a same-speaker neighbour after a BARE recogniser cut (no trailing punctuation) is not "joined" under `note.ends_mid_sentence` and stays the existing named residue; (ii) a VAD segment left textless because `assign_words_to_segments` gave its words to a packed-window neighbour (`transcription.py:569`, `:606-638`) can draw a false missed-speech warning — the 0.1 budget bounds how often, and Task 2.1 pins the case.

### Key Design Decisions
D1–D10 below. Practitioner-owned choices are `[decision]` tasks 0.1 and 0.3–0.8 (all taken 2026-10-22; 0.4's two values are owed after Task 0.2).

## Key Findings

### Files / Symbols Involved
- `desktop/src/scribe_desktop/note_check.py`
  - `_omission_flag_token(text, *, first_in_segment, clinician)` :1561-1581 — any speaker: side, number, dose, strength unit, negation, medication; the clinician only: name-like words.
  - `omission_warnings(note, document)` :1584-1634 — `()` without a confirmed clinician; covered = (segment, word) pairs from each transcript assertion's `note_span.source_coords`; per segment, the uncovered non-suspect flagged words → one `NoteWarning("high_risk_omission", "review", source_coords=SourceCoords(seg, min, max))`; runs past the next-patient boundary (pinned `test_consultation_boundary.py:656`). Its docstrings at :136 and :192 describe the code list.
  - `check_note` :1830-1868 — Checks 1–4 then Check 6 (`next_patient_warnings` :1802-1818, anchored `SourceCoords(boundary, 0, len(words) - 1)`).
  - `HEDGE_PHRASES` :513-532 (16 entries); Check 1 `reconstruction_warnings` :540-613 calls `line_marks(span words, …)` at :603 and emits `hedged_source` on the assertion's own coords, the clinician excluded through `spoken_by_confirmed_clinician` (`note.py:1540`).
- `desktop/src/scribe_desktop/note.py` — `_FILLER_TOKENS` :232-234 (10 disfluencies; "okay", "yeah", "right", "no" are CONTENT) and `content_tokens(text)` :258; `NOTE_WARNING_SEVERITY` :298 (18 codes; `high_risk_omission` = review :351); `text_holds_hedge` :396-415 (contiguous whole-token match over `content_tokens`); `words_hold_hedge` :418; `line_marks(words, *, clinician)` :425-444 (span words in, no document); `SourceCoords(segment_index, first_word_index, last_word_index)` :447; `NoteWarning` :681 (`extra="forbid"`; `source_coords: SourceCoords | None`; the forward-tolerant `_read_stored_unknown_review` reader :703-727); the Clean body reads warnings :964-981; `ends_mid_sentence(words)` :1676-1688 (True only for a trailing `,` `;` `:` or dash after closing marks are peeled; "a bare cut is a named residue").
- `desktop/src/scribe_desktop/transcription.py` — `TranscriptWord` (absolute start/end seconds, probability, uncertain, suspect) :318-337; `TranscriptSegment` (one VAD segment: start/end seconds, speaker, words) :340; `segment_has_text` :372 / `words_have_text` (used to label speakers, never to filter); `assemble_transcript` :1462-1479 builds one segment per VAD segment, textless ones INCLUDED (both drivers append every segment: :1596 batch, :2522 live); `assign_words_to_segments` :606-638 gives a word to the segment holding its midpoint or the nearest one, so a word's stamps can overhang its segment; `pack_transcription_windows` :569; `GuardFeatures` / `guard_features` :1262-1320.
- `desktop/src/scribe_desktop/ui/models.py` — `WarningCopy(title, blocks, clear_hint)` :2156-2162 (per code; no line number); `WARNING_COPY["high_risk_omission"]` :2283; `WarningGroup` :2326, `summarise_warnings` :2360-2389 (groups by code); `SEPARATELY_ACKNOWLEDGED_NAMES` :2404-2414 (its `possible_next_patient` entry quotes "[after possible next patient]") / `_CODES` (4 codes); `ACKNOWLEDGE_ALL_TOOLTIP` :2419-2422; `FLAGGED_LINE_MARK` :2685, `NEXT_PATIENT_LINE_MARK` :2691; `flagged_segments` :2694-2714; `flagged_count_line` :2801-2820 (fixed wording "side, negation, number, dose, name or medication"; "replaced or partly in the note"); `eligible_utterances` :2839-2878 (`_lead_words` cuts at 60 characters; the middle elision is Qt's default); `_row_marks(document, assertion, state, *, clinician_speaker)` :3042-3071 (calls `line_marks(span, …)` at :3071; reads no warnings).
- `desktop/src/scribe_desktop/ui/note.py` — `_flagged_segments` :1262-1266, the `[flagged]` rows :1304, the count line :1821-1841, the review rows render `{group.title} ({group.count})` :2290/:2301; the module docstring :44-77 names the marks.
- `desktop/src/scribe_desktop/validation.py` — imports `_omission_flag_token` :101-121; `_Alignment` (forward and backward tables; `on_optimal`, `diagonal`, `deletion`, `insertion`) ~:780-810; `align_transcripts` :866 (ONE path; not for R1); `_FactState` 8-tuple :901; `_fact_end_states` :924-954 (walks EVERY co-optimal alignment over a fact's rows, carrying `all_matched` / `all_deleted`); `_judge` :966-991 (`credited = hedged and script_hedged and verdict == "correct"`); the segment-index credit :1337-1341; the hedge re-derivation :1350-1366 (`words_hold_hedge(marked)` on the warning's coords :1360); the `warned` predicate in `word_info` :1368-1395 (the 0.3.3 all-speaker predicate; `warned_v1` beside it is run 1's clinician-only one, `:693-696`); `script_hedged = text_holds_hedge(script.lines[fact.line].text)` :1425 → `_judge` :1433; silent omission :1460-1465 and :602-623; `PassRule` :1511 (`schema_version: Literal[1]` :1520, `extra="forbid"`); `rule_failures(rule, outcome)` :1615-1640 (per encounter); `run_passed` :1901-1904 (every encounter passes); `render_report` :1915-2058 (the one-verdict heading :1921-1923; separator `"---|" * 25` :1943; `cells = ["-"] * 18` :1956; `cells.insert(17, …)` :2009; the TOTAL row :2017-2025; the 9-column Facts table :2044-2046); `evaluate_encounter` :1761-1817; `main` :2175 (`set_dir`, `--config`, one `--rule` per run, `--template-profile`, `--allow-small`, `--prose`); `load_script`.
- `desktop/src/scribe_desktop/consultation_phrases.py` — `CLOSING_PHRASES` (14), `GREETING_PHRASES` (12), `BOUNDARY_SEGMENTS = 3`, `phrase_events`, `consultation_boundary` :244-281; `note_config.next_patient_boundary` :2907-2918 (the one accessor, C5); `voice_commands` re-exports the lists :47-55.
- `desktop/src/scribe_desktop/replay_kept.py` — `note_drift` :301-336 (runs `check_note`; counts reviews together; `clinician_speaker` comes only from `enrolled.enrolled_speaker`, :367-373, None otherwise); `_replay_entry` :339-390 (`store.read_recording` + `transcribe_in_temporary_store` for a fresh transcript); `main` :529-600 holds the refusals INLINE and in order — `install_layout.channel()`, `check_tool_wer(_windows_layer, sys.executable)`, the private `_acquire_exclusion()` / `_release_exclusion()`. `past_sessions.PastSessionStore.kept_session_ids(self) -> list[str]` :952 and `read_replay_inputs(self, session_id) -> tuple[TranscriptDocument, GeneratedNote | None]` :1494 (the OLD kept transcript and saved note; never the label).
- `validation/rules/option-a-proposed.json` — rule v1 (schema 1, `max_material_wrong` 0, `max_silent_omissions` 0, `require_uncertainty_surfaced`, `max_word_error_rate` null); amendments are recorded in prose in `docs/testing/validation-harness.md` (call 3 amended 2026-10-09; "Amended 2026-10-13 (2)" at :92) and cited in the report header (pinned `test_validation_harness.py:1198`; positional pins :1184-1209).
- `validation/heldout/` (22 scripts); `desktop/tests/fixtures/heldout_transcripts.py` (imports `validation.load_script` :59; `HELDOUT_DIR` :62; `SCRIPT_CASE_PREFIX = "hld-"` :63; `Turn`; `build_document` :85-120 — one segment per turn, 300 ms per word and 600 ms between segments, so it can never show a gap; `HeldOutCase` :130-163 with boundary, corrections and unsure expectations; `SCRIPT_CASES` :163-300 (22 hand-written, reasons quoted from script text); `EDGE_CASES` 10; `HELD_OUT_CASES` :433). `desktop/tests` has no `__init__.py`: tests import `fixtures.…` through pytest's rootdir insertion.
- `desktop/tests/test_validation_scripts.py` — `HELDOUT` :62 (also read at :464); lints :329-348 (routed uncertain clauses, no autofill trigger); the prefix asserts :354, :386, :388; `test_one_case_per_held_out_script_and_the_rest_are_edge_cases` :383-390 (one case per script stem).
- Per-set divergence dicts, each `case_id -> (expected, frozen result)`: `_PREDICTED_BOUNDARY_DIVERGENCES` `test_consultation_boundary.py:103` (7, count pinned :354), `_PREDICTED_CORRECTION_DIVERGENCES` `test_note.py:~2947`, `_PREDICTED_UNSURE_DIVERGENCES` `test_note_check.py:~2242`.
- **Note-level exact-code-list tests that change once `clinician_line_omitted` fires on a fully uncovered clinician line** (through `check_note` / `finalise_note`; each re-checked, re-pinned where the new code fires): `test_save_as_ratification.py:342`; `test_ui_screens.py:5693-5749` (`unacknowledged_reviews == 1` after Acknowledge all); `test_note_matrix`; `test_ui_models.py:1979-1985` (the tooltip, word for word) and `:2025-2055` (exact chooser labels). **Unchanged regression pins, kept as they are** (peer round 2 PR-LOW-001): `test_note_check.py:1791`, `:1828`, `:1882`, `:2291` and `test_note_schema_v2.py:893` call `omission_warnings` directly, which D1 leaves unchanged; `test_transcript_trim.py:459-483` asserts only Check 6's presence.
- Pins: `test_vocabulary.py` (lists :47-80, hedges :181-199); `test_hands_free.py:358-361`; `test_install_layout.py:867` `test_the_version_is_the_same_everywhere`; `test_pilot_docs.py` (vocabularies :112-123; the both-ways Encounter test :266-292 has no `h2-` case); `test_shadow_exits.py` (counts placements, text widgets, clipboard/drag, mode keywords, list/combo classes, sends, WAV writers and the plaintext kept-recording readers :840-852 — NOT check functions or transcript-word readers, so C11 holds for this plan).
- Version 0.3.3 in `desktop/pyproject.toml:7`, `desktop/src/scribe_desktop/__init__.py:3`, `extension/package.json:4`, `extension/package-lock.json:3` and `:9`, `extension/src/manifest.ts:29`.

### Codebase Integration Notes
- The note pipeline is compose → confirm → CHECK → write; checks are pure functions of `(note, document, config)` and run at every compose or regenerate, so a new check code needs no stored field (only `note.enc`'s `note_warnings` list gains entries). A SAVED note reopened from the Unreviewed section is shown as saved — its stored `note_warnings` kept, the checks not rerun (`ui/note.py:1018-1050`; peer round 5 PR-LOW-002).
- A build older than 0.3.4 reads each unknown REVIEW code as `unknown_review_warning`, keeping every warning's own fields (`note.py:705-727`); the review list groups them under that one code with their combined count (`ui/models.py:2360-2388`), and its Acknowledge all clears the group — so the separately-acknowledged control is lost after a rollback, though no warning is dropped (peer round 5 PR-LOW-002). The rollback line says so (Task 5.2).
- The harness evaluates through the product's own functions; any widening of the product's predicate changes what `warned` means unless the harness reads it (D7). One shared function per rule keeps product and harness from drifting (C5).
- Textless VAD segments are present in the stored document, so the missed-speech trigger 1 reads them directly (no pipeline change).
- `_row_marks` already receives the document, so the hedge scope can be computed there without a signature change; `line_marks` keeps its signature for the per-span marks and the new hedge test is a separate function.

### External / API Findings
None. No Cliniko, network or model change.

## Planned Workflow Summary

### Flow 1 — An uncued clinician line (0.3.4)
The clinician says something no cue routes and no Check 4 word flags (for example an advice line). Today: nothing warns. 0.3.4: the review list shows "A line you said is not in the note (1)"; the chooser marks the line `[flagged]`; Acknowledge all leaves it; the per-code click clears it.

### Flow 2 — Speech with no words
A stretch of detected speech holds no transcribed words (a textless VAD segment, or a gap between words inside one), longer than the frozen threshold. The review list shows "Speech was heard but no words were written for part of it (1)"; the chooser and the line editor mark the anchor line `[gap?]`; the clinician listens back or checks their memory and adds the missing fact by typing.

### Flow 3 — A hedge in the next sentence
A patient says "It was about 40 mg," then, in the next segment, "I think." The earlier segment ends in a comma, so under 0.6 (ii) the fact's line is marked `[check: unsure]`. The same two lines in a script earn the harness credit.

### Flow 4 — The practitioner's runs
Task 0.2: counts on rebuilt sets and on kept recordings (integers only) → 0.4's values → 0.9's commit → 0.11 (the fixtures ready for a second set) → `heldout-2` authored blind (0.10) → 0.12's diagnosis, cases and predictions → the build → P.1: run 6 on three sets, read against the predictions.

## Design Decisions

### D1 — Check 4 on any uncovered clinician line (decision 0.3: (b), 2026-10-22)
- **A new review code `clinician_line_omitted`.** Fires once per segment when ALL of: a confirmed clinician exists; the segment is spoken by the confirmed clinician; it holds text; no word of it is covered by any transcript assertion's `source_coords`; at least one non-suspect word is a content token (`note.content_tokens`, whose filler set is `_FILLER_TOKENS`); it does not already draw `high_risk_omission`; it lies before the next-patient boundary (`note_config.next_patient_boundary`, C5). Anchor: `SourceCoords(seg, 0, len(words) - 1)`. Severity review; separately acknowledged (added to `SEPARATELY_ACKNOWLEDGED_CODES` / `_NAMES`). `high_risk_omission` is unchanged, including over the tail.
- Why a new code: the existing copy names "a side, negation, number, dose, name or medication", which an advice line is not; a distinct code keeps the existing warning's meaning, gives honest copy, and lets the harness, the replay and the register count the two apart.
- **One-word acknowledgements fire under (b):** "okay", "yeah", "right" and "no" are content tokens. This is exactly the case option (c)'s exemptions remove, so Task 0.2 counts lines of ≤ 2 content tokens separately; (c) is added only if (b)'s real-speech counts exceed the 0.1 budget on either bound (median or maximum; peer round 1 PR-MED-003). **(c)'s two exemptions, defined now and measured exactly as written** (peer round 2 PR-MED-014): (c-q) a QUESTION line — the segment's last non-suspect word ends in `?` (Whisper's punctuation); (c-a) an ACKNOWLEDGEMENT line — the segment's non-suspect content tokens number at most 2 AND every one is in the candidate set `ACKNOWLEDGEMENT_TOKENS` = {okay, ok, alright, yeah, yes, yep, right, sure, good, great, fine, cool, thanks, thank, you, no}. Task 0.2 scores (c) as both exemptions together and each alone; under (c) the predicates and the set are frozen in Task 0.9 exactly as measured (a changed set is a new dated decision with Task 0.2 repeated).
- **Partly quoted segments** are out of scope for the new code (a segment with any covered word is the clinician's partial choice); the existing predicate still covers flagged words there.
- **Rejected:** widening `_omission_flag_token`'s clinician branch under the one code (it changes the existing warning's meaning, its copy and the harness's 0.3.3 `warned` comparison, and floods the tail); re-routing the line into a section; a sub-reason field (Excluded).

### D2 — The missed-speech warning (Step 3.5, 2026-10-22: Include in plan; constants by decision 0.4 — rule chosen 2026-10-22, values after Task 0.2)
- **Code `speech_without_words`, review severity, separately acknowledged, role-free** (speaker labels of textless segments are unreliable). Computed in `note_check.py` from the document alone (a new `missed_speech_warnings(document, config)`, run in `check_note` after Check 4 and before Check 6).
- **Triggers, per segment before the next-patient boundary:**
  Both triggers read ONE indexed view per segment (peer round 3 PR-MED-019: `segment_has_text` counts suspect words, `transcription.py:351-357`, `:372-374`): the segment's SURVIVING words — non-blank and not `suspect` — each kept with its ORIGINAL word index.
  1. a textless VAD segment — its surviving view is EMPTY (no word, only blank words, or only suspect words) — with `end_seconds - start_seconds ≥ MISSED_SPEECH_EMPTY_SECONDS`;
  2. inside a segment whose view is not empty, a gap ≥ `MISSED_SPEECH_GAP_SECONDS` between one surviving word's `end_seconds` and the NEXT SURVIVING word's `start_seconds` (suspect words between them are skipped, so a gap over them still counts), or between the segment's start and its first surviving word, or its last surviving word and its end. A negative gap (a word's stamps overhang the segment, `assign_words_to_segments`) counts as 0. ONE warning per anchor line: several textless segments that anchor on the same preceding line, or a textless segment plus an in-segment gap on the same line, give one warning (the largest gap's coordinates).
- **Anchor (no schema change), in original word indices:** a segment with a surviving view → `SourceCoords(seg, i, k)` where `i` and `k` are the ORIGINAL indices of the two surviving words around the largest gap (not necessarily adjacent: suspect words between them lie inside the span); for a leading or trailing gap, the first or last surviving word, twice; a textless segment → the nearest PRECEDING segment with a non-empty view, on its last surviving word (the following one's first surviving word if none precedes); no segment with a non-empty view → no warning (an empty transcript already says so).
- **How it is shown:** the review list's copy is per code with no line number (`WarningCopy`), so the copy reads "Speech was heard but no words were written for part of it" with a clear hint "Check the line marked [gap?]". The anchor line carries a new short mark `[gap?]`, computed by a new helper `gap_segments(warnings)` beside `flagged_segments` (the anchors' segments from the warnings' `source_coords`, carried as independent segment annotations — NOT through `_row_marks`, which returns no marks for a removed or replaced row, `ui/models.py:3043-3071`; peer round 4 PR-MED-021). It shows on every line-editor row state the omission flag shows on (`ui/models.py:2976`, `:3009`: all but `removed`), `replaced` INCLUDED, so a typed replacement never hides it; in the chooser (`eligible_utterances`) a replaced anchor segment is not offered (`ui/note.py:1250-1276` counts it present) and a removed one returns with `[gap?]`. The anchor is NOT added to `flagged_segments` ("flagged" means "not in the note", which a fully quoted anchor line is not), so the count line is untouched by this code.
- **Constants** `MISSED_SPEECH_EMPTY_SECONDS`, `MISSED_SPEECH_GAP_SECONDS` (`Final`, in `note_check.py`) are decided ONCE in 0.4 from Task 0.2's threshold-grid scores against the 0.1 budget, frozen in 0.9, and never tuned after a run of record (the guard's C2 rule; a change is a new dated decision with the measurement repeated).
- **Known limits, named:** Whisper may stretch word timestamps over a dropped clause, leaving no gap — such a drop stays silent (R1 under rule v2). A cough or noise the VAD calls speech, or a packed-window artefact that leaves a segment textless, draws a false warning; the budget bounds how often.
- **Rejected:** a decode-level signal (Whisper's `no_speech_prob`) — per decode window and already the guard's; one combined trigger ("the longest uncovered stretch ≥ T") — simpler, but it removes decision 0.4's option (x) of dropping only the in-segment trigger.

### D3 — Chooser marks that survive the elision (Step 3.5: Include in plan)
- The front marks become short, fixed tokens so Qt's middle elision cannot cut them: `FLAGGED_LINE_MARK` `[flagged]` stays; `NEXT_PATIENT_LINE_MARK` `[after possible next patient]` becomes `[next patient?]`; the new omission code reuses `[flagged]`; the missed-speech code gets `[gap?]` (D2).
- **The rename ripples:** `SEPARATELY_ACKNOWLEDGED_NAMES["possible_next_patient"]` quotes the old mark and feeds `ACKNOWLEDGE_ALL_TOOLTIP`; both are pinned word for word (`test_ui_models.py:1979-1985`, `:2025-2055`); `ui/note.py`'s module docstring :75 and three documents quote it (Task 5.1).
- `eligible_utterances` places all marks before the speaker and `_lead_words`' 60-character cut applies to the words only, after the marks. Exact strings are pinned; the design system and the review guide quote them.
- Rejected for now: turning off Qt's elision or eliding on the right — a widget change that `test_shadow_exits.py` would count (C11).

### D4 — The greeting gap (decision 0.5: (a), 2026-10-22)
- **(a)** The lists stay frozen; an unbroken next patient with an unlisted greeting is residue class R3 under rule v2 (D8). Controlled by Start per patient and the patient-change block. The practitioner's own phrases come later (Deferred).
- Rejected: (b) blind widening now (false-cut risk, C4; "morning stiffness"); (c) the practitioner's own phrases now (they cannot name them yet; a later change would force another repeated run).

### D5 — Hedges: one scope function and a blind lexicon (decision 0.6: lexicon (b), scope (ii), 2026-10-22; "joined" = `note.ends_mid_sentence`, 2026-10-22)
- **Lexicon (b):** widened by a BLIND session from named published sources (Task 0.10's author method), with a contamination note; "not sure", "i don't know" and "i reckon" are already known from the failures, so they enter only if a named source holds them. The selection rule of the 0.3.3 list (whole phrases about the speaker's own certainty; no bare modal verbs) is unchanged.
- **Scope (ii):** a segment is hedged if its own words hold a hedge, OR a same-speaker neighbour (previous or next) holds one and the two are joined mid-sentence — the EARLIER of the two satisfies the existing `note.ends_mid_sentence` (a trailing comma, semicolon, colon or dash). A bare cut with no trailing mark is not joined (an accepted residue, as the helper's docstring already says). Non-contiguous hedges ("not, I think, sure") stay a named residue. (iii) any adjacent same-speaker segment — rejected as too wide.
- **One function, two inputs.** `note.segment_hedged(document, segment_index) -> bool` (name final in Task 3.1) applies the rule over transcript segments; `validation.script_line_hedged(script, line_index) -> bool` applies the SAME rule over script lines (speaker and trailing punctuation of the earlier line), pinned against `segment_hedged` on documents built from those scripts. Callers: Check 1's `reconstruction_warnings` (`note_check.py:603`) — the segment of the assertion's coords; the line editor's `_row_marks` (`ui/models.py:3071`, already holds the document); the harness's mark re-derivation (`validation.py:1360`) AND its script term (`:1425` `script_hedged`). Without the script term a scope-(ii) mark is never credited (`_judge` :976). `line_marks` keeps its signature and its per-span uses.
- Whether (ii) fixes `syn-30` fact 0 depends on 0.12 (split off or misheard).

### D6 — The measurement before design (Task 0.2)
- **One synthetic script, two modes** (agent, in the gitignored `.cursor/loops/`): `run6-measure.py` — text mode reads scripts through `validation.load_script` and builds documents through `validation.reference_document` (D8; the fixture's turn-level builder moves there as `document_from_turns`), then `compose_draft` → `finalise_note` → `check_note`, with each Check 4 variant ((a), (b), (c)) as a scratch function (the product is not changed in Phase 0); `--audio <set folder>` transcribes a BUILT set's WAVs itself, in memory, through the harness's own path (`read_label_track`, `read_wav_pcm`, `transcribe_in_temporary_store`, as `evaluate_encounter` does at `validation.py:1768-1773`; the runner saves no transcript — peer round 2 PR-MED-012) and reads (per encounter: textless-segment durations and in-segment gaps as histograms — bucket counts only — plus the same variant counts) AND scores a GRID of candidate threshold pairs (textless 1.0–3.0 s and gap 0.5–2.0 s, 0.25 s steps) with a scratch reference of D2's exact triggers, anchoring and one-per-anchor-line de-duplication, printing per pair the combined new-warning median and maximum per encounter with each (b)/(c) variant. It also prints, for every textless threshold and every variant, the scores with trigger 2 DISABLED (trigger 1 alone, the same de-duplication), so decision 0.4's option (x) is read off a printed row, never reconstructed from combined counts (peer round 2 PR-MED-013). Histograms alone cannot choose the pair: two gaps on one anchor give one warning, on two anchors two (peer round 1 PR-MED-002). Prints per variant: uncovered clinician segments; warnings per encounter (mean, max); lines of ≤ 2 content tokens among them (D1); how many of the five held-out silent facts the variant warns; uncovered patient lines with content but no flaggable word (the next exposure). **Text-level counts are a parser-contract number, not a model number** (`docs/lessons.md` 2026-09-24): the budget is judged on the audio-level and real-speech counts; both are recorded.
- **Audio level, synthetic** (practitioner, normal terminal, developer build, installed app closed — or the agent if its shell can see the models; `docs/lessons.md`): rebuild `validation/scripts` and `validation/heldout` deterministically into empty folders outside the repository (kept until Task 0.12 ends), run `run-validation.py` on each for the premise check (its report), and `run6-measure.py --audio` on each for the measurements — two transcriptions of the same built set on the same commit and models, deterministic as the premise check against run 5 already assumes; the measurement's document lives in memory only and its temporary store is removed as the harness removes it (peer round 2 PR-MED-012).
- **Real speech, a SEPARATE script** (practitioner only): `run6-measure-kept.py` reproduces `replay_kept.main`'s refusal order — `install_layout.channel()`, `check_tool_wer(_windows_layer, sys.executable)` (exit 2 without the exclusion), the exclusion lock for its run — reads ids through `PastSessionStore.kept_session_ids`, re-transcribes each kept recording as `_replay_entry` does (`read_recording` + `transcribe_in_temporary_store`; the stored transcript cannot show fresh gaps), runs the pipeline as `note_drift` does with `--config validation\config`, and prints per session ORDINAL only integers: per-code counts per variant, the threshold-grid scores (as the synthetic `--audio` mode) and the gap/textless histograms, with the enrolled-speaker flag. **`--enrolment <WAV>` is REQUIRED** (peer round 1 PR-MED-004): the replay finds the clinician only through a supplied enrolment WAV (`replay_kept.py:213-223`, `:355-368`), so without it every session would read as not enrolled. The script refuses (exit 2) when the option is absent or the file is not a usable WAV (`replay_kept`'s `WavFormatError` / `EnrolmentError` handling), before reading any entry. The WAV is the practitioner's own enrolment WAV under the clinic 1 smoke's custody (its D14 and D16: kept in the measurement folder outside the user profile, never committed). A session whose fresh transcript has no `enrolled_speaker` despite the WAV counts as "attribution failed" and is printed as such, kept apart from "no enrolment given", which cannot occur. The (b) median is taken over enrolled sessions only; n, n(enrolled) and n(attribution failed) are recorded. No id, text or name; the record in the plan is aggregates (n, median, max) only (C1, C8). It is a separate entry point so no real-data path can share the id-printing code.
- **Never measured on `heldout-2`** (that would spend it).

### D7 — The warned amendments (harness; ratified inside decision 0.7, 2026-10-22)
- `warned` for a silent-omission fact becomes: today's predicate (the current `warned`, `validation.py:1385-1389`, the all-speaker 0.3.3 predicate) OR the fact's aligned segment carries `clinician_line_omitted` OR the deletion-edge term below. Today's `warned` is kept as a walk flag `warned_v033` (on `_WordInfo` and `_FactState`, like `warned_v1`), and the 0.3.3 silent-omission predicate is kept ACROSS EVERY ALTERNATIVE as run 1's is (`validation.py:617-623`, `:1460-1464`; peer round 2 PR-MED-016): `_Judged` gains `warned_v033`, `FactOutcome` gains `silently_omitted_v033` (any judged alternative `omitted` and not `warned_v033`) and a `silent_omission_v033` property, `EncounterMetrics` a `silent_omissions_v033` count, printed as "Silent (0.3.3 predicate)"; the ambiguity set strips `warned_v033` as it strips `warned_v1` (`:1446`); `warned_v1` stays run 1's clinician-only predicate with its existing run-1 label (`validation.py:693-696`). Pins: a patient-side omission warned by 0.3.3 but not by run 1 (peer round 1 PR-MED-006); a fact reported `wrong` whose other co-optimal alignment is omitted, silent under 0.3.3 and now warned, counts in the 0.3.3 column (peer round 2 PR-MED-016).
- **The deletion-edge term** (peer round 1 PR-MED-001; separate from D2's display anchors). `_FactState` gains two FLAGS, never histories (peer round 2 PR-MED-011: the walk stays bounded only because equal states merge, `validation.py:896-900`): `some_deleted` (at least one of the fact's reference tokens took a deletion step on that alignment) and `edge_covered` (at least one such deletion step had a covered edge). Before the walk a per-column table `deletion_edge_covered[j]` is precomputed: a deletion at alignment column `j` sits between hypothesis words `j - 1` and `j` (the edge words; at the transcript's start or end, one edge), and the entry is true when a `speech_without_words` warning's `source_coords` covers either edge word, compared in ORIGINAL `(segment, word)` coordinates through `hypothesis.consumed` (so suspect-filtered and joined tokens map back correctly); `_after_deletion` is called with `j` and reads the table. The term holds only when EVERY reached state has `some_deleted` AND `edge_covered` (a substitution-only alignment earns nothing). This covers a singleton anchor `(i, i)` on a first or last word, and an edge in another segment than the fact's. A segment-wide credit was rejected: it would count a transcribed, uncued line as warned whenever its segment also held a pause. Pins: partial deletion credited vs. substitution not credited; first-word and last-word edges; a cross-segment edge; a suspect word between the edge and the anchor; a transcribed uncued line beside a pause NOT credited; a repeated-token ambiguity case whose per-cell state count stays within 2^12 (the eight existing flags, the two above, `warned_v033` and D8's `marked`).
- These are METRIC amendments (the warning the clinician sees now covers the line), dated and cited in the report header like 2026-10-13 (2).

### D8 — Residue classes and rule v2 (decision 0.7: (b), 2026-10-22)
- **Rule v2:** `validation/rules/rule-v2.json`, `PassRule` schema 2 (`Literal[1, 2]`; schema 1 files read unchanged; a schema-1 file carrying ceiling fields is refused by `extra="forbid"` — pinned; an older `run-validation.py` refuses a schema-2 file, exit 2 — fine). It ratifies mechanical residue CLASSES — never encounter ids — each with a ceiling, and the report prints the v1 verdict beside the v2 verdict:
  - **R1 recogniser.** For a fact on which a failing predicate holds — `material_wrong` with verdict `wrong`, or `silent_omission` (reported, or on any co-optimal alternative, `validation.py:603-614`); a nonmaterial fact consumes no allowance (peer round 2 PR-MED-009): on EVERY co-optimal alignment (`_fact_end_states`: no reached state has `all_matched`) a word error falls on the fact's own tokens; AND the same pipeline gets the fact right on `reference_document(script)` (the script's own words); AND, for a `wrong` fact, the product put a review mark on the rendering judged wrong — defined over the TRANSCRIPT, never the script line (peer round 4 PR-MED-020: `fact.line` indexes the script, `validation.py:1423`, while Check 1's marks address assertion spans, `note_check.py:589-610`): `_WordInfo` gains `review_marked` (the hypothesis word lies inside the `source_coords` of a `number_source`, low-confidence, `suspect_source` or `hedged_source` warning on the measured document, compared in ORIGINAL `(segment, word)` coordinates through `hypothesis.consumed`), and `_FactState` gains one more FLAG, `marked` (some hypothesis word aligned to one of the fact's reference tokens, by match or substitution, is `review_marked`); the term holds only when EVERY reached end state judged `wrong`, across EVERY occurrence of the fact, has `marked` — one marked alternative never excuses an unmarked wrong one. **Honest limit:** `number_source` marks every line holding a number, so for a numeric fact the mark term is nearly always met — a dose error like `syn-28` always qualifies. A confidently misheard NON-numeric word on an unmarked line still FAILS.
  - **R2 tone only.** An `expect_uncertain` fact whose uncertainty is NOT surfaced (`uncertainty_surfaced is False`) and whose script line, under the D5 scope over script lines, holds no hedge from `validation.REFERENCE_HEDGES` — a harness-only reference lexicon chosen blind, frozen in 0.9, pinned as a SUPERSET of `HEDGE_PHRASES`; the membership of the phrases already known from the failures ("not too sure", "i dunno", "i reckon"…) is recorded either way. A fact whose script holds a reference hedge the product misses is NOT R2 (it fails). An already-surfaced fact is never R2 and consumes no ceiling (peer round 1 PR-HIGH-001).
  - **R3 unbroken next patient.** A MATERIAL `absent` fact judged `wrongly_present` (so `material_wrong` holds; a nonmaterial one consumes nothing — peer round 2 PR-MED-009) in a script with axis `end_and_new_patient`, whose line lies AT OR AFTER the script's reference tail start, where the product found NO boundary on the measured document (`note_config.next_patient_boundary` is None — an encounter-level fact, so no aligned segment or alternative is needed; a boundary that fired anywhere, even after the fact, leaves the fact failing, the conservative reading — peer round 3 PR-MED-018), and the frozen lists find no greeting (`phrase_events`) on the script's reference GREETING line. **Two frozen reference tables, never one** (peer round 2 PR-MED-010; peer round 3 PR-MED-017: a closing and a greeting can share a line, so the greeting line and the first withheld line differ — `heldout_transcripts.py:214-217`, `note_check.py:1805-1807`): `validation.REFERENCE_GREETING_LINES` (encounter id → the line holding the next patient's greeting) and `validation.REFERENCE_TAIL_STARTS` (encounter id → the first line withheld, equal to `HeldOutCase.boundary` wherever a held-out case has one), for every script carrying the axis (axes are per script, and neither facts nor roles mark the switch — `syn-38` and `syn-46` voice their next patient as `patient`). They are reference provenance like a fact, not class membership; the scripts and their facts are unchanged (C2). Written in Task 0.9 for the 50 and `heldout` and in Task 0.12 for `heldout-2`, before the predictions. A script with the axis and no entry in either table is a harness error, never an R3. Pins: an unrelated `absent` fact before the tail start in the same encounter is NOT R3; a boundary that fired after the fact is NOT R3; a closing and a greeting sharing one line (greeting line = tail start − 1) reads the greeting line, not the tail start.
  - **The set layer (new in the harness):** ceilings are LITERAL per-set integers in the one rule file, keyed by set name (`scripts`, `heldout`, `heldout-2`), and count FACTS, not encounters. **Each class excuses only its own failure predicates** (peer round 1 PR-HIGH-001; peer round 2 PR-MED-008): R1 clears `material_wrong` when the verdict is `wrong` AND, independently, `silent_omissions` when `silent_omission` holds — one fact reported `wrong` with a silently omitted co-optimal alternative counts in BOTH by design (`validation.py:603-614`); R2 clears `uncertainty_missed` only; R3 clears `material_wrong` (verdict `wrongly_present`) only. A fact's other failures stand: an R1 fact whose uncertainty is also unsurfaced still fails that count unless it is separately R2, and a fact meeting R2 that is also `wrong` or silently omitted still fails unless separately R1. The predicates are not all disjoint (`material_wrong` and `silent_omission` overlap), but each class names the predicates it may clear, so no ordering rule is needed; a fact counts ONCE against a class's ceiling however many of that class's predicates it clears, and once against each class it meets. **The raw counts never change** (peer round 2 PR-MED-007): `EncounterMetrics.material_wrong`, `silent_omissions` and `uncertainty_missed` stay rule-independent, because `rule_failures` (`validation.py:1629-1634`) and the report totals (`:1965-1970`) read them for the v1 verdict. The class is a field on `FactOutcome`; NEW residue-adjusted counts skip the excused facts and only schema-2 evaluation reads them. Pin: the same outcomes give v1 FAIL and v2 PASS. `run_passed` becomes: every encounter passes AND every class is within its ceiling for the named set; `rule_failures` stays per encounter and a new set-level failure names the class and its count. The report gains per-set class counts and a class column in the Facts table.
  - **Ceilings (chosen 2026-10-22):** 2 per class on the 50, 1 on `heldout`, 1 on `heldout-2` — fixed integers, not a formula (a formula over measured encounters would move if a build error lowered n). The 50's 2 equals run 5's R1 and R3 counts (Honest forecast).
- **The override, stated:** a rule change after a seen failure collides with pilot Constraint 12 and the 2026-10-09 stop rule ("the cue file and the rule are not changed to make it pass"). The practitioner overrode those lines on Task 0.7 on 2026-10-22; the v1 verdict stays printed, so nothing is hidden.
- **One turn-level builder, two adapters** (peer round 5 PR-MED-022: the fixture's `build_document` takes `tuple[Turn, ...]` and reads `.speaker` / `.text`, `heldout_transcripts.py:85-110`, and `HeldOutCase.document()` passes explicit edge-case turns, `:146-152`, so a script-only function cannot replace it): `validation.document_from_turns(turns)` is the moved builder, over any sequence of `(speaker, text)` items (a small `Protocol` the fixture's `Turn` satisfies); `validation.reference_document(script)` adapts a script's lines through it; the fixture's `build_document` becomes a thin call of `document_from_turns` (one implementation, no drift). Pin: the moved builder gives the SAME document as today's fixture for every scripted held-out case AND every explicit-turns case (compared field by field, captured before the move).
- Rejected: (a) no rule change; the reference-transcript test alone for R1 (a fact lost to a segmentation or routing change would then land in R1 with no error on its tokens); a single global ceiling (2 would loosen the blind set, 1 fails the 50).

### D9 — The pass gate (decision 0.8: all three sets, 2026-10-22)
A pass under rule v2 on all THREE sets — the 50 scripts, `heldout`, `heldout-2` — with the v1 verdict recorded beside each. Any `heldout-2` failure is a finding for a `heldout-3` / 0.3.5 cycle, never a tuning target.

### D10 — Version, runs and documents
- Version 0.3.4 in the six places (Task 5.2). Built of record after P.1 on the H4 commit (H5).
- Documents (Task 5.1): the threat model's Phase 3A surface 2 and Check 4 paragraph (:524, :532, :831, :858); data-flow flow 7 (and flow 10 where the note request's warnings are stored); "Rolling back below 0.3.4" in `docs/release/pilot-builds.md` (:73); `docs/testing/validation-harness.md` (the amendments, rule v2, `heldout-2`, the run of record); `docs/testing/shipping-gate.md:102` (the review rows cleared only by their own Acknowledge); `docs/testing/kept-recordings.md:40-52` (the replay's per-code counts); `docs/design-system.md` (:155, :169-172, :399, :409, :848 — copy, marks, the tooltip); `docs/practice/clinician-review-guide.md` (:101, :106, :113; the 0.3.4 lines, practitioner-approved); `docs/pilot/README.md:161` and the register's prose (:20, :33) for `h2-` ids; `docs/architecture/phase-history.md` (:51, :55 quote the old mark); `validation/README.md`; CHANGELOG; AGENTS.md.

## Schema / Data Changes
- **No new stored field.** Two new review codes are persisted in `note.enc`'s `note_warnings`; 0.3.2+ read them forward-tolerantly, each as an `unknown_review_warning` with its fields kept, grouped under that one code and cleared by that build's Acknowledge all (the rollback line says so).
- **`PassRule` schema 2:** a new rule file with per-set class ceilings; schema 1 files read unchanged; `extra="forbid"` kept, so a schema-1 file with ceiling fields is refused.
- **New frozen constants:** `MISSED_SPEECH_EMPTY_SECONDS`, `MISSED_SPEECH_GAP_SECONDS`; `validation.REFERENCE_HEDGES`; the widened `HEDGE_PHRASES`; under 0.3 (c) only, `ACKNOWLEDGEMENT_TOKENS` and D1's two exemption predicates, exactly as measured.
- `_FactState` gains flags for D7's terms (`some_deleted`, `edge_covered`, `warned_v033`, and D8's `marked`; at most 2^12 states per cell); `_WordInfo` gains `review_marked` (D8's R1); `_Judged` gains `warned_v033`; `FactOutcome` gains `silently_omitted_v033` (D7) and its residue-class fields (D8); `EncounterMetrics` gains `silent_omissions_v033` and the residue-adjusted counts read only under schema 2 (raw counts unchanged); `validation.REFERENCE_GREETING_LINES` and `validation.REFERENCE_TAIL_STARTS` (D8's R3); `validation.reference_document` replaces the fixture's `build_document`.

## Config / Environment / Deployment Impact
- No environment variable, network, model, model-pack or dependency change.
- Release: 0.3.4 built of record by CI's `Release` workflow on the H4 commit after P.1 (attested; a `docs/release/pilot-builds.md` row). Same AppId, in-place upgrade. Install at a pilot-allowed point (never between consultations).

## Critical Constraints
1. **C1 — The agent never opens, reads, plays or describes any real session, kept recording, transcript, note, Past-sessions entry or learned config.** Synthetic sets and integer counts only; the kept-recording measurement is a practitioner-run script that prints integers per session ordinal and is a separate entry point from the id-printing synthetic script.
2. **C2 — Rule v1's file, `validation/config/section_cues.json`, and the facts of the 50 scripts and of `validation/heldout` never change.** Rule v2 is a NEW file ratified on Task 0.7 (done) before Task 0.12; metric amendments are dated practitioner decisions before the run, pinned both ways; a bad number after a run is a finding (pilot Constraint 12, clinic-smoke D9).
3. **C3 — The lexicons and the missed-speech constants are frozen in one dated commit (Task 0.9) before `heldout-2` is authored and before 0.12's diagnosis is read.** Any later change is a new dated decision with a repeated run. The phrase lists are unchanged (0.5 (a)).
4. **C4 — Fail toward inclusion and never silently.** The new warnings never delete or re-route; they are review severity and separately acknowledged; the next-patient boundary is unchanged; a negative gap is 0, never an error.
5. **C5 — One function per rule, shared by product and harness:** the next-patient boundary (`note_config.next_patient_boundary`), the hedge scope (`segment_hedged`, with `script_line_hedged` pinned equal on built documents), "joined mid-sentence" (`note.ends_mid_sentence`), the omission predicates (imported by `validation.py` as `_omission_flag_token` is), the reference transcript (`validation.reference_document`, imported by the fixture).
6. **C6 — No import of `voice_commands` from `note`, `note_config`, `note_fill` or `note_check`.**
7. **C7 — The live new-consultation warning is unchanged** (0.5 (a)).
8. **C8 — Nothing per consultation enters a tracked file** (clinic-smoke D12). Run records are ids and counts; kept-recording measurements are aggregates (n, median, max).
9. **C9 — One `/execute-loop` at a time on `main`; isolation none.** Builds run in the main checkout (the `.venv` is an editable install of main's `desktop/src`). `main`'s version is never lowered.
10. **C10 — Practitioner-run steps run from a normal terminal with the installed app closed.** Nothing checked from an agent shell counts. Any record script that writes into this plan asserts `"\x00" not in text` and `"\r" not in text` first (`docs/lessons.md` 2026-10-03).
11. **C11 — `test_shadow_exits.py`'s counters are unchanged.** No new text widget, clipboard, drag, list, combo box or plaintext kept-recording reader; the new check functions and `note_drift`'s per-code counts fall outside every counter (verified 2026-10-22).
12. **C12 — `heldout-2` is read by no build leg before Task 0.12 and is never measured in Task 0.2.** Its author session runs in an EMPTY folder outside the repository holding only the behaviour spec and one format example, with no repository access; its transcript is kept with the set's commit as the isolation record. Task 0.11 is built before the set exists and tolerates its absence.
13. **C13 — No cloud sessions** (practitioner decision 2026-09-05). The findings register stays content-free (month dates, closed vocabularies; `test_pilot_docs.py`).

## Validation / Verification
**Suites.** `desktop/`: `ruff check . && mypy && pytest` (the composer runs the suite; verify=composer). `extension/`: `npm run qa` (version only).

**Read-only baselines** (dry-run 2026-10-22 at `4ff5f26`):

| Check | Baseline | Becomes |
|---|---|---|
| `NOTE_WARNING_SEVERITY` codes | 18 | 20 |
| `SEPARATELY_ACKNOWLEDGED_CODES` | 4 | 6 |
| `ACKNOWLEDGE_ALL_TOOLTIP` pin `test_ui_models.py:1979-1985` | quotes `[after possible next patient]` | quotes `[next patient?]` and the two new names |
| `HEDGE_PHRASES` | 16 | the 0.9 count (0.6 (b)) |
| `CLOSING_PHRASES` / `GREETING_PHRASES` | 14 / 12 | unchanged (0.5 (a)) |
| Report separator `"---|" * 25` at `validation.py:1943`; `cells = ["-"] * 18` :1956; the Facts table's 9 columns :2044 | 25 / 18 / 9 | each grows by the Phase 4 columns (counts pinned in Task 4.3) |
| `PassRule.schema_version` | `Literal[1]` | `Literal[1, 2]` |
| `SCRIPT_CASE_PREFIX` | `"hld-"` | per set: `hld-`, `h2-` |
| Held-out folders | `validation/heldout` (22) | + `validation/heldout-2` |
| Version | 0.3.3 | 0.3.4 |

**Per-phase checks.** The tests named on each task; every new predicate pinned both ways (fires / does not fire), every ceiling pinned at the boundary (n = ceiling passes, n + 1 fails), every exact-code-list test in Key Findings re-pinned deliberately (not loosened).

**Acceptance:** P.1 read against Task 0.12's written predictions, and the 0.8 gate met; the P.2 smoke on the installed 0.3.4. If either fails: the result is a recorded finding, P.5 stays (a), and the next cycle is a new plan.

## Deferred / Out of Scope
See the Planning Extraction Summary (the canonical list).
- **Deferred:** the practitioner's own phrases; the four items retained on `plan-validation-pass.md`; the ui-refresh adoption at its merge.
- **Excluded:** a larger model; edits to rule v1, the cue file or the seen scripts' facts; widening from seen failures; the guard's constants; routing changes; a sub-reason field; a per-warning line number in review copy.

## Current State / Handoff Note
- Loop config (proposed, as the last three runs): executor=claude-p model="claude-opus-5-5" effort=high profile=default; peer=codex model="gpt-6-astra" effort=medium; architect=off; cadence=every-phase; caps=review:3,peer:5; gates=executor; cap-raise=executor; high-auto=on; peer-max=12; notify=action-only; scope=all; autocommit=on; isolation=none; merge=off; perms=scoped; liveness=10; monitor-delivery=auto; verify=composer.
- **Order:** 0.2 (measure) → 0.4's two values → 0.9 (dated commit) → 0.11 (fixtures over a set table, before the set) → 0.10 (`heldout-2`, independent author, empty folder) → 0.12 (diagnosis, the `h2-NN` cases and divergence entries, predictions; frozen) → Phases 1–5 → H1–H4 → P.1 → H5 → P.2 → P.3.
- Line references were taken at `0be35d7`; `desktop/src` is unchanged at `4ff5f26`. A build leg re-locates symbols before editing.
- `[2026-10-22]` Decisions taken ("take all the recommendations"): 0.1 median ≤ 2, maximum ≤ 5; 0.3 (b), (c) only if over budget; 0.4's rule (values owed after Task 0.2); 0.5 (a); 0.6 lexicon (b), scope (ii); 0.7 (b) with the written override; 0.8 all three sets. Recorded on each task. Later the same day: "joined" = `note.ends_mid_sentence` (D5).
- `[2026-10-22]` Second `/review-plan` (Fable 5.1): 36 lens findings reconciled — the Task 0.10/0.11 order, the harness's script-side hedge term, the narrowed missed-speech credit, the `[gap?]` mark in place of a line number in copy, rule v2's set layer with literal ceilings, `reference_document` in the package, the rename ripples, the exact-code-list tests, the register and document additions, the kept-recording script's refusal order and enrolled-only median, the two lessons. Nothing built; nothing committed.
- `[2026-10-22]` Cross-family plan peer pass (codex `gpt-6-astra` high, `/peer-loop`, cap 5): rounds 1–5 recorded in the Review Findings Log; 23 build-affecting + 2 record-only findings, all verified and amended. Round 5 still found one build-affecting finding (PR-MED-022), so the pass stopped AT THE CAP; at the practitioner's word a fresh one-round pass (round 6) found NO findings — converged.
- Next: Task 0.2 (the measurement scripts), after the practitioner's word to commit the plan.

## Review History
- 2026-10-22 `/review-plan` (Opus 5.5): Plan-subagent design critique + Explore subagent + coverage, practicality, risk and simplicity lenses, every finding checked against `0be35d7` / `4ff5f26`. Plan-scoped; no code reviewed. Step 3.5 gate: missed-speech warning Include in plan; chooser mark Include in plan; ui-refresh at its merge; larger model Excluded.
- 2026-10-22 `/review-plan` (Fable 5.1): three read-only subagent lenses (coverage 12 findings, practicality 12, simplicity/risk 12) over the plan and the code at `4ff5f26`; 5 HIGH (0.11 vs C12; the script-side hedge term twice; the missed-speech credit; the copy's line number), the rest MED/LOW; all applied. One practitioner answer: "joined" reuses `note.ends_mid_sentence`. Plan-scoped; no code reviewed.
- 2026-10-22 `/peer-loop` plan pass (codex `gpt-6-astra` high, read-only, cap 5; composer Opus 5.5): Round 1 1 HIGH + 6 MED; Round 2 10 MED + 1 LOW; Round 3 3 MED; Round 4 2 MED; Round 5 1 MED + 1 LOW (record-only). Every finding verified against the code at `4ff5f26` and amended with siblings swept; no invalid findings; every round's read-only sandbox left the working tree unchanged. Ended at the cap with round 5 build-affecting; a fresh one-round pass at the practitioner's word (Round 6) found no findings — CONVERGED.

## Review Findings Log
### Round 1 — 2026-10-22
Source: Codex gpt-6-astra high plan peer-review

**PR-HIGH-001 — R2 can excuse correctness failures unrelated to tone.**  
Materiality: build-affecting  
D8 (`.cursor/plans/plan-validation-run6.md:197-199`) classifies any `expect_uncertain` fact without a reference hedge, then removes all its failure counts. Correctness and uncertainty are independent in `desktop/src/scribe_desktop/validation.py:978-991` and `:685-704`: an omitted or wrong fact that fails R1 can therefore escape through R2, while an already-correct, acoustically surfaced fact can unnecessarily consume its ceiling.  
Proposed amendment: Apply R2 only to an actual unsurfaced-uncertainty failure, preserve that fact’s wrong/omission failures, and test already-surfaced, routing-loss and misrecognition cases.

**PR-MED-001 — D2’s anchors and D7’s deletion credit are incompatible.**  
Materiality: build-affecting  
D2 (`.cursor/plans/plan-validation-run6.md:161-162`) creates singleton anchors for textless and leading/trailing gaps, whereas D7 (`:191`) requires an adjacent `(i, i + 1)` pair around the deletion. Cross-segment gaps cannot fit that pair, and skipping suspect words can leave nonadjacent original indices. Additionally, `all_deleted` means the entire fact was deleted, while `not all_matched` also includes substitutions (`desktop/src/scribe_desktop/validation.py:905-921`, `:942-948`).  
Proposed amendment: Define deletion-edge matching separately from display anchors, covering singleton, first/final, cross-segment and suspect-filtered cases with explicit deletion state and tests distinguishing partial deletion from substitution.

**PR-MED-002 — Histograms discard information needed to select the thresholds.**  
Materiality: build-affecting  
D6 (`.cursor/plans/plan-validation-run6.md:185-187`) prints duration histograms, and Task 0.4 (`:291`) selects thresholds from them, but D2 (`:161`) deduplicates warnings across triggers by anchor line. Identical histograms can describe two gaps sharing one anchor or two gaps on different anchors, yielding different combined warning counts.  
Proposed amendment: Have the practitioner’s measurement script evaluate candidate threshold pairs using the exact anchoring and deduplication rules and print aggregate combined median/maximum counts for each pair.

**PR-MED-003 — A maximum-only budget breach has no permitted resolution.**  
Materiality: build-affecting  
Task 0.1 (`.cursor/plans/plan-validation-run6.md:282`) requires median ≤2 **and** maximum ≤5, but D1 (`:152`) and Task 0.3 (`:290`) permit exemptions only when the median exceeds its bound. Counts `[0, 0, 6]` violate the fixed maximum while prohibiting exemptions; changing missed-speech thresholds cannot remove those six clinician-line warnings.  
Proposed amendment: Apply the authorized “budget exceeded” condition to either bound and define the practitioner handoff if the exempted clinician-line counts still make the combined budget infeasible.

**PR-MED-004 — The real-speech measurement omits its required enrolment input.**  
Materiality: build-affecting  
D6 and Task 0.2 (`.cursor/plans/plan-validation-run6.md:187`, `:286-288`) specify the archive and config but no enrolment source. Replay obtains enrolment only from an explicitly supplied WAV (`desktop/src/scribe_desktop/replay_kept.py:210-223`); fresh transcription does not recover the original recording’s clinician attribution (`:355-368`). Following the stated invocation can therefore produce zero enrolled sessions and incorrectly trigger the synthetic-only fallback.  
Proposed amendment: Specify the practitioner-provided enrolment input, its validation and custody requirements, and distinguish missing enrolment input from unsuccessful clinician attribution.

**PR-MED-005 — The vocabulary freeze changes behaviour before the baseline comparison.**  
Materiality: build-affecting  
Task 0.9 (`.cursor/plans/plan-validation-run6.md:299`) changes live `HEDGE_PHRASES` before Task 0.12 (`:314`) requires totals and encounter verdicts identical to run 5. Existing code immediately consumes that list through `desktop/src/scribe_desktop/note.py:405-414`, `:442` and `note_check.py:603`, so an intended vocabulary improvement can itself trigger the mandatory mismatch pause.  
Proposed amendment: Perform the baseline comparison against pinned 0.3.3 code, or capture it before activating the frozen vocabulary, then generate predictions against the approved new vocabulary separately.

**PR-MED-006 — `warned_v1` is not the 0.3.3 omission predicate.**  
Materiality: build-affecting  
D7 and Task 4.2 (`.cursor/plans/plan-validation-run6.md:191`, `:346`) identify `warned_v1` as today’s predicate and label it “Silent (0.3.3 predicate)”. In `desktop/src/scribe_desktop/validation.py:1385-1392`, current `warned` uses the widened all-speaker predicate, while `warned_v1` retains run 1’s clinician-only predicate; `:693-696` explicitly documents that distinction. Reusing it would misstate the comparison.  
Proposed amendment: Preserve current `warned` in a distinct 0.3.3 comparison field, retain accurate run-1 labelling, and pin the difference with a patient-side omission warned by 0.3.3 but not run 1.

Materiality: 7 build-affecting / 0 record-only / 0 invalid

**Dispositions (composer, Opus 5.5, 2026-10-22; each verified against the code at `4ff5f26`):**
- PR-HIGH-001 — verified (`validation.py:626-627` `material_wrong`, `:685-704` the separate counts; D8 removed a classed fact from all three counts). Accepted: each class excuses only its own failure kind (D8, Tasks 4.1, 4.3).
- PR-MED-001 — verified (`_INITIAL_STATE` / `_after_word` / `_after_deletion` `validation.py:902-921`: the flag is ALL deleted; `not all_matched` includes substitutions). Accepted: a separate deletion-edge rule in the harness (D7, Task 4.2).
- PR-MED-002 — verified against D2's de-duplication. Accepted: the measurement scores candidate threshold pairs with the exact rules (D6, Tasks 0.2, 0.4).
- PR-MED-003 — verified (Task 0.1 has two bounds; D1 and Task 0.3 named the median only). Accepted: either bound, and a pause when still infeasible (D1, Tasks 0.3, 0.4).
- PR-MED-004 — verified (`replay_kept.py:213-223`, `:355-368`: no clinician without `--enrolment`). Accepted: `--enrolment` is required (D6, Task 0.2).
- PR-MED-005 — verified (Task 0.9 changes the live `HEDGE_PHRASES` before Task 0.12's premise check). Accepted: the premise check moves to Task 0.2, before the freeze (Tasks 0.2, 0.12).
- PR-MED-006 — verified (`validation.py:1385-1392`: `warned_v1` is run 1's clinician-only predicate; `warned` is 0.3.3's). Accepted: a new comparison field from today's `warned` (D7, Task 4.2, Schema).

**/fix notes (amendments, 2026-10-22):** each amendment re-read on disk after landing. Siblings reconciled: D1's and Task 0.3's "median" → either bound; D2's "histograms" and Task 0.4 → the threshold-grid scores; Key Findings' `word_info` line, Excluded and D1's Rejected line no longer call `warned_v1` the 0.3.3 comparison; Task 4.3's "R1 < R2 < R3" → each class excuses its own count; Task 0.12's premise check → a difference check against Task 0.2; Schema gains `warned_v033` and the class fields.

### Round 2 — 2026-10-22
Source: Codex gpt-6-astra high plan peer-review

**PR-MED-007 — Residue-adjusted counters can contaminate the v1 comparison.**  
Materiality: build-affecting  
D8 (`.cursor/plans/plan-validation-run6.md:200`) directs each count to skip excused facts, but `EncounterMetrics`’ counters are rule-independent (`desktop/src/scribe_desktop/validation.py:685-704`) and shared by `rule_failures` and report totals (`:1629-1634`, `:1965-1970`). Changing those properties would also apply v2 exemptions to the printed v1 verdict.  
Proposed amendment: Preserve raw metrics and calculate adjusted counts only during schema-2 evaluation, with identical outcomes pinned to produce v1 FAIL and v2 PASS.

**PR-MED-008 — R1’s verdict-based excusal misses co-optimal silent omissions.**  
Materiality: build-affecting  
D8 (`.cursor/plans/plan-validation-run6.md:200`) associates omission excusal with verdict `omitted` and calls the failure kinds disjoint. However, `FactOutcome.silent_omission` deliberately counts an unwarned omitted alternative even when the reported verdict is `wrong` (`desktop/src/scribe_desktop/validation.py:603-614`, `:1460-1462`). One qualifying R1 fact can therefore contribute to both correctness counts.  
Proposed amendment: Apply R1 independently to the actual material-wrong and silent-omission predicates, retaining uncertainty failures, and pin a fact whose co-optimal alternatives produce both counts.

**PR-MED-009 — Nonmaterial facts can consume R1 and R3 allowances.**  
Materiality: build-affecting  
D8 admits `wrong` and qualifying `wrongly_present` facts without requiring materiality (`.cursor/plans/plan-validation-run6.md:197-200`). Materiality is independent of verdict (`desktop/src/scribe_desktop/validation.py:274-278`), and a correctness failure requires both (`:625-627`). Thus a nonmaterial fact can exhaust a ceiling despite having no failure to excuse.  
Proposed amendment: Require an applicable failing predicate before assigning R1 or R3, and pin nonmaterial wrong/wrongly-present facts as consuming no allowance.

**PR-MED-010 — R3 lacks a mechanical association between the fact and the patient switch.**  
Materiality: build-affecting  
D8 refers to “a fact with axis `end_and_new_patient`” and “the script’s greeting line” (`.cursor/plans/plan-validation-run6.md:199`). Axes belong to the whole script, while neither facts nor script lines identify a greeting or reference boundary (`desktop/src/scribe_desktop/validation.py:254-255`, `:274-278`, `:342-349`). Applying the encounter-level axis can excuse an unrelated absent fact before the switch.  
Proposed amendment: Define frozen reference greeting/tail provenance without changing existing facts, require the excused fact to belong to that tail, and pin an unrelated absent fact in the same encounter.

**PR-MED-011 — Recording deletion-edge histories removes the bounded alignment state.**  
Materiality: build-affecting  
D7 requires `_FactState` to retain edge indices for every deleted run (`.cursor/plans/plan-validation-run6.md:192`). The current walk bounds each cell to 256 states specifically by carrying eight booleans (`desktop/src/scribe_desktop/validation.py:896-900`, `:932-954`); retaining distinct edge histories prevents equivalent paths from merging and permits combinatorial growth.  
Proposed amendment: Precompute deletion-position anchor coverage through `hypothesis.consumed`, retain bounded deletion/coverage flags instead of histories, and add a repeated-token ambiguity test with a state-count bound.

**PR-MED-012 — Synthetic measurement expects transcripts the runner never saves.**  
Materiality: build-affecting  
D6 and Task 0.2 prescribe running validation, then reading the built set’s transcripts with `run6-measure.py --audio` (`.cursor/plans/plan-validation-run6.md:185-186`, `:337`). `evaluate_encounter` holds its document only in memory and returns metrics (`desktop/src/scribe_desktop/validation.py:1768-1773`, `:1808-1817`); `main` prints a report, not transcript artifacts (`:2362-2363`).  
Proposed amendment: Make measurement consume documents in memory through the harness’s transcription path and explicitly define how that transcription supplies both the premise check and threshold measurements.

**PR-MED-013 — The grid cannot establish the trigger-disabled budget.**  
Materiality: build-affecting  
D6 specifies finite threshold pairs with gap thresholds up to two seconds (`.cursor/plans/plan-validation-run6.md:185`), while Task 0.4 permits disabling trigger 2 and requires checking feasibility with it disabled (`:342-343`). Longer gaps remain active in every grid row, and aggregate combined counts cannot reconstruct the disabled result after anchor deduplication.  
Proposed amendment: Print trigger-2-disabled scores for every empty-segment threshold and omission variant, using the same deduplication and population summaries.

**PR-MED-014 — Option (c)’s two exemptions are not defined before measurement.**  
Materiality: build-affecting  
Task 0.3 names “two exemptions” (`.cursor/plans/plan-validation-run6.md:341`), and D6 requires scoring them (`:185`), but D1 supplies only acknowledgement examples, a short-line count and a later vocabulary freeze (`:152`, `:351`). Exempting all short lines and exempting only named acknowledgements produce different budgets and threshold choices.  
Proposed amendment: Specify both exemption predicates and the candidate acknowledgement vocabulary before Task 0.2, then freeze the exact measured definitions if option (c) is selected.

**PR-MED-015 — The vocabulary freeze can invalidate tests before their planned reconciliation.**  
Materiality: build-affecting  
Task 0.9 activates the widened hedge list before Task 0.11 requires a green suite (`.cursor/plans/plan-validation-run6.md:351-358`), but existing held-out tests assert the old frozen results (`desktop/tests/test_note_check.py:2220-2245`). An approved addition matching a previously missed hedge changes those results immediately; the plan names subsequent divergence reconciliation in Tasks 0.12 and 3.1.  
Proposed amendment: Reconcile the existing sets’ lexicon-only divergence predictions with the freeze commit, keeping later scope-change predictions separate and preserving the original expectations.

**PR-MED-016 — `warned_v033` alone cannot preserve the conservative comparison.**  
Materiality: build-affecting  
D7 and the schema section add `warned_v033` (`.cursor/plans/plan-validation-run6.md:191`, `:217`), but silent omission also depends on alternatives other than the reported verdict. The existing run-1 comparison therefore retains `silently_omitted_v1` across all judged states (`desktop/src/scribe_desktop/validation.py:617-623`, `:1460-1464`). A single reported warning flag cannot recover an old silent alternative that the new warning now covers.  
Proposed amendment: Preserve the 0.3.3 silent-omission predicate across every alternative, with a dedicated comparison accumulator and a pin where the reported verdict is wrong but another alignment was silently omitted under 0.3.3.

**PR-LOW-001 — The exact-code-list inventory incorrectly labels unchanged tests as requiring new expectations.**  
Materiality: record-only  
Key Findings and Task 1.1 (`.cursor/plans/plan-validation-run6.md:119`, `:377`) list direct `omission_warnings` tests as changing, although D1 explicitly leaves that function unchanged; these include `desktop/tests/test_note_check.py:1790-1791`, `:1827-1828`, `:1881-1882`, `:2290-2291` and `test_note_schema_v2.py:892-893`. The listed trim checks assert only Check 6’s presence/absence (`test_transcript_trim.py:479-483`).  
Proposed amendment: Distinguish unchanged regression pins from expectations affected by the new checks, retaining these assertions unchanged.

Materiality: 10 build-affecting / 1 record-only / 0 invalid

**Round 2 dispositions (composer, 2026-10-22; each verified against the plan and the code at HEAD before amending):**
- PR-MED-007 — verified (`validation.py:685-704` counts read by `rule_failures` :1629-1634 and the totals :1965-1970). Accepted: raw counts unchanged; residue-adjusted counts read only under schema 2 (D8, Task 4.1, 4.3, Schema).
- PR-MED-008 — verified (`silent_omission` :603-614 counts a reported-`wrong` fact's silent alternative; D8 called the kinds disjoint). Accepted: R1 clears each predicate independently, a fact counts once against R1 (D8, Task 4.1).
- PR-MED-009 — verified (`material` independent of verdict :274-278; `material_wrong` :625-627). Accepted: R1 and R3 need a failing predicate (D8, Task 4.1).
- PR-MED-010 — verified (axes per script :342-349; `syn-38` and `syn-46` voice the next patient as `patient`). Accepted: the frozen `REFERENCE_TAIL_STARTS` table and the tail condition (D8, Tasks 0.9, 0.12, 4.1, Schema).
- PR-MED-011 — verified (`_FactState` is eight flags so equal states merge, :896-954). Accepted: two flags plus a precomputed per-column edge table; a state-count pin (D7, Task 4.2, Schema).
- PR-MED-012 — verified (`evaluate_encounter` holds the document in memory :1768-1817; `main` prints a report only :2362-2363). Accepted: `--audio` transcribes in memory through the harness path; the premise check stays on `run-validation.py`'s report (D6, Task 0.2).
- PR-MED-013 — verified (D6's grid kept trigger 2 on in every row; Task 0.4's option (x)). Accepted: trigger-2-disabled rows printed (D6, Task 0.4).
- PR-MED-014 — verified (D1 gave examples and a count, no predicates). Accepted: (c-q) and (c-a) with the candidate set defined now (D1).
- PR-MED-015 — verified (`test_note_check.py:2220-2245` asserts the frozen-hedge divergences; 0.9 precedes 0.11). Accepted: lexicon-only reconciliation in the freeze commit (Task 0.9).
- PR-MED-016 — verified (`silently_omitted_v1` across alternatives :617-623, :1460-1464). Accepted: `warned_v033` as a walk flag with `silently_omitted_v033` across alternatives (D7, Task 4.2, Schema).
- PR-LOW-001 — verified (the five direct `omission_warnings` pins and the trim test's presence-only asserts). Accepted: Key Findings and Task 1.1 split changing from unchanged pins.

**/fix notes (round 2 amendments, 2026-10-22):** each amendment re-read on disk after landing. Siblings reconciled: D8's "the three failure kinds are disjoint" removed; Schema's `_FactState` / `FactOutcome` line; Task 0.4's option (x); Tasks 4.1–4.3's class wording and pins; Task 0.2's practitioner line and D6's audio paragraph agree on two separate transcriptions; Task 0.9 and 0.12 carry the tail table.

### Round 3 — 2026-10-22
Source: Codex gpt-6-astra high plan peer-review

**PR-MED-017 — R3 conflates the greeting line with the first withheld line.**  
Materiality: build-affecting  
D8 (`.cursor/plans/plan-validation-run6.md:199`) defines `REFERENCE_TAIL_STARTS` as the greeting line, tests that line for a listed greeting, and requires equality with `HeldOutCase.boundary`. These positions differ: `desktop/tests/fixtures/heldout_transcripts.py:214-217` places the greeting in segment 3 but the boundary at 4. `desktop/src/scribe_desktop/note_check.py:1805-1807` explicitly documents this distinction. Consequently, following the prescribed pin makes R3 inspect the wrong line for its greeting condition, potentially admitting a failure unrelated to an unlisted greeting.  
Proposed amendment: Freeze separate reference greeting and tail-start indices, use each for its corresponding R3 predicate, and test a closing and greeting sharing one line.

**PR-MED-018 — R3’s “fact’s aligned segment” has no defined meaning across alignment alternatives.**  
Materiality: build-affecting  
D8 and Task 4.1 (`.cursor/plans/plan-validation-run6.md:199`, `:473`) compare the detected boundary with one aligned segment. However, a fact can span multiple transcript segments, and the harness combines repeated occurrences and every co-optimal alignment (`desktop/src/scribe_desktop/validation.py:1427-1434`). `_fact_end_states` retains Boolean outcome flags and discards positions (`:924-954`); it provides no single segment for that comparison. Choosing one path would undermine the harness’s conservative treatment of alternatives.  
Proposed amendment: Define R3’s boundary condition over the note-contributing aligned words and all relevant alternatives, using the authoritative boundary and bounded flags, with tests for spanning and repeated-token facts across a boundary.

**PR-MED-019 — D2’s prescribed textless test contradicts its suspect-word exclusion.**  
Materiality: build-affecting  
D2 (`.cursor/plans/plan-validation-run6.md:159-162`) uses `not segment_has_text(segment)` while requiring suspect words to count as no words. The named helper counts every nonblank word, including suspect words (`desktop/src/scribe_desktop/transcription.py:351-357`, `:372-374`). An all-suspect segment therefore fails the textless test but has no surviving first/last words for the filtered gap calculation. Likewise, the prescribed `(i, i + 1)` anchor cannot represent surviving edges at original indices 0 and 2 after excluding index 1. This ambiguity affects both threshold measurement and shipped warnings.  
Proposed amendment: Define detection over an indexed non-suspect word view, explicitly handle an empty filtered view and display-anchor fallback, preserve original edge indices, and pin all-suspect and nonadjacent-edge cases.

Materiality: 3 build-affecting / 0 record-only / 0 invalid

**Round 3 dispositions (composer, 2026-10-22; each verified against the plan and the code at HEAD before amending):**
- PR-MED-017 — verified (`heldout_transcripts.py:214-217` `hld-11`: closing and greeting share segment 3, boundary 4; `note_check.py:1805-1807`). Accepted: two tables, the greeting line and the tail start (D8, Tasks 0.9, 0.12, 4.1, Schema).
- PR-MED-018 — verified (`_fact_end_states` keeps flags, not positions, `validation.py:924-954`; occurrences and alternatives combined :1427-1434). Accepted, by the simpler route: R3 requires NO boundary on the measured document, an encounter-level fact; a later boundary leaves the fact failing (D8, Task 4.1).
- PR-MED-019 — verified (`segment_has_text` counts suspect words, `transcription.py:351-357`, :372-374). Accepted: one indexed surviving-word view per segment, original indices for the anchor, all-suspect = textless (D2, Task 2.1).

**/fix notes (round 3 amendments, 2026-10-22):** each amendment re-read on disk after landing. Siblings reconciled: Schema names both R3 tables; Tasks 0.9, 0.12 and 4.1 carry both tables and the boundary-None condition; Task 2.1's pins carry the all-suspect and non-adjacent-edge cases; D7's deletion-edge comparison is already in original coordinates and covers a span anchor.

### Round 4 — 2026-10-22
Source: Codex gpt-6-astra high plan peer-review

**PR-MED-020 — R1’s review-mark condition remains undefined across alignment alternatives.**  
Materiality: build-affecting  
D8 (`.cursor/plans/plan-validation-run6.md:197`) requires “the fact’s line” to carry a product review mark. However, `fact.line` indexes the script (`desktop/src/scribe_desktop/validation.py:1423`), while product marks address transcript assertion spans (`desktop/src/scribe_desktop/note_check.py:589-610`). The harness evaluates every occurrence and co-optimal alignment (`validation.py:1427-1434`), potentially reaching different transcript segments, and retains flags rather than positions (`:951-954`). The plan therefore leaves undefined whether one marked alternative can excuse another unmarked, erroneous rendering; Round 3’s R3 amendment does not resolve this separate R1 condition.  
Proposed amendment: Define mark eligibility over the note-contributing transcript segments for every wrong alternative and occurrence, retain a bounded eligibility flag during the walk, and test split-segment and repeated-token cases where only one alternative is marked.

**PR-MED-021 — D2’s gap mark needs an explicit policy for replaced anchor lines.**  
Materiality: build-affecting  
D2 and Task 2.2 (`.cursor/plans/plan-validation-run6.md:157-163`, `:490`) make the warning document-only and place its `[gap?]` mark in `_row_marks`. That helper suppresses marks for replaced lines (`desktop/src/scribe_desktop/ui/models.py:3058-3059`), while replacements also remove their source segment from the chooser (`desktop/src/scribe_desktop/ui/note.py:1253-1259`). Following those existing rendering rules leaves the persistent warning pointing to a mark displayed nowhere after the clinician types a replacement—the response described in Flow 2 (`plan:139`).  
Proposed amendment: Carry gap anchors as independent segment annotations, preserve `[gap?]` on replaced source rows as omission flags already are (`ui/models.py:2977`, `:3009`), and add a replacement regression case beside the fully quoted and chooser-anchor tests.

Materiality: 2 build-affecting / 0 record-only / 0 invalid

**Round 4 dispositions (composer, 2026-10-22; each verified against the plan and the code at HEAD before amending):**
- PR-MED-020 — verified (`fact.line` indexes the script, `validation.py:1423`; Check 1's marks are per assertion `source_coords`, `note_check.py:585-612`; occurrences and alternatives combined, `validation.py:1427-1434`; the walk keeps flags, `:951-954`). Accepted: `_WordInfo.review_marked` and one more walk flag `marked`, required on every wrong end state of every occurrence (D8 R1, D7's state bound 2^12, Schema, Task 4.1's split-segment and repeated-token pins).
- PR-MED-021 — verified (`_row_marks` returns () for removed and replaced rows, `ui/models.py:3043-3071`; the omission flag is computed outside it, `:2976`, `:3009`; a replaced segment counts as present, `ui/note.py:1250-1276`). Accepted: `gap_segments(warnings)` beside `flagged_segments`, shown on every state the omission flag shows on (D2 "How it is shown", Task 2.2 and its replacement regression test).

**/fix notes (round 4 amendments, 2026-10-22):** each amendment re-read on disk after landing. Siblings reconciled: D7's pin and the Schema line both say 2^12 and name `marked`; Task 4.1 names the walk flag; Flow 2 and the P.2 mock smoke already speak of "the anchor line" and stand; D3's mark list is unchanged (the token is still `[gap?]`).

### Round 5 — 2026-10-22
Source: Codex gpt-6-astra high plan peer-review

**PR-MED-022 — Reference-document migration conflates two input contracts.**  
Materiality: build-affecting  
D6/D8 and Task 0.9 (`.cursor/plans/plan-validation-run6.md:185`, `:203`, `:474`) prescribe `reference_document(script)` while making fixture `build_document` an import of it. However, `build_document` accepts `tuple[Turn, ...]` and reads `.speaker` (`desktop/tests/fixtures/heldout_transcripts.py:85-110`); `HeldOutCase.document()` passes those turns, including explicit edge cases (`:146-152`). The prescribed direct replacement breaks these callers, while the migration pin names only scripted held-out documents.  
Proposed amendment: Preserve a shared turn-to-document builder, adapt `reference_document(script)` through it, and pin unchanged output for both scripted and explicit edge cases.

**PR-LOW-002 — Stored-note reopen and rollback descriptions overstate what happens.**  
Materiality: record-only  
Integration Notes (`.cursor/plans/plan-validation-run6.md:124-125`) says checks rerun on every reopen and unknown codes collapse into one entry. Saved-note reopening instead displays previously ratified content without rerunning checks (`desktop/src/scribe_desktop/ui/note.py:1018-1050`, `:2546-2552`). The unknown-code reader preserves each warning’s fields and changes its code (`desktop/src/scribe_desktop/note.py:705-727`); multiple warnings form one UI group with their combined count (`desktop/src/scribe_desktop/ui/models.py:2360-2388`).  
Proposed amendment: Distinguish saved-note display from active review, and describe rollback as retaining separate warnings under one grouped code rather than collapsing them into one stored entry.

Materiality: 1 build-affecting / 1 record-only / 0 invalid

**Round 5 dispositions (composer, 2026-10-22; each verified against the plan and the code at HEAD before amending):**
- PR-MED-022 — verified (`build_document(turns: tuple[Turn, ...])` reads `turn.speaker` / `turn.text`, `heldout_transcripts.py:85-110`; `HeldOutCase.document()` passes `explicit_turns`, `:140-152`). Accepted: `validation.document_from_turns` as the one builder, `reference_document` an adapter, the fixture a thin call, pinned equal for scripted and explicit cases (D8's Schema line; D6's text mode).
- PR-LOW-002 — verified (`show_saved_note` shows a saved note as saved, `ui/note.py:1018-1050`; the unknown-code reader keeps fields, `note.py:705-727`; grouping, `ui/models.py:2360-2388`). Accepted as a record correction (Integration Notes, the "No new stored field" line, Task 1.3); no build change.

**/fix notes (round 5 amendments, 2026-10-22):** each amendment re-read on disk after landing. Siblings reconciled: D6's text mode names `document_from_turns`; the Integration Notes, D-section "No new stored field" line and Task 1.3 all describe rollback as fields kept and grouped; Key Findings line 116's fixture description stays true of HEAD. This is the pass's cap round (5).

### Round 6 — 2026-10-22
Source: Codex gpt-6-astra high plan peer-review

No findings

Materiality: 0 build-affecting / 0 record-only / 0 invalid

**Round 6 disposition (composer, 2026-10-22):** a fresh one-round pass the practitioner asked for after the first pass ended at its cap. No findings; nothing to amend. The plan peer pass is CONVERGED.

## Tasks

### Phase 0 — Budget, measurement, decisions, freeze, predictions
- [x] 🟩 **0.1 The warning budget** `[decision]` — Chosen: median ≤ 2, maximum ≤ 5 new review warnings per real consultation, both new codes together (2026-10-22, the practitioner's words: "take all the recommendations"; set before any Task 0.2 number existed).
  - Practitioner, BEFORE seeing any number from Task 0.2.
  - Recommended: median ≤ 2, maximum ≤ 5 (a guess to react to, not a measured value).
- [ ] 🟥 **0.2 Measurement before design (D6)**
  - Agent: `.cursor/loops/run6-measure.py` (gitignored; text mode and `--audio <set folder>`; ids and integers only; Check 4 variants (a), (b), (c) as scratch functions; the ≤ 2-content-token count) and `.cursor/loops/run6-measure-kept.py` (the separate real-speech entry point: `replay_kept.main`'s refusal order, `kept_session_ids`, re-transcription as `_replay_entry`, `--config validation\config`, integers per session ordinal with the enrolled flag). Both read `validation.reference_document` once Task 0.9's commit moves it — until then the text mode adds `desktop/tests` to `sys.path` and imports the fixture's `build_document`.
  - Practitioner (normal terminal, developer build, installed app closed): rebuild the two sets into empty folders outside the repository (kept until 0.12 ends); run `run-validation.py --rule validation\rules\option-a-proposed.json` on each (the premise check); run `run6-measure.py --audio` on each (it transcribes in memory itself; nothing is saved); run `run6-measure-kept.py --enrolment <measurement folder>\enrolment\me.wav` over the developer and/or installed `past_sessions` folder (both builds closed).
  - **Premise check, here and not in 0.12** (peer round 1 PR-MED-005: Task 0.9 changes the live `HEDGE_PHRASES`, so a later comparison with run 5 would mismatch by design): this task runs on the unfrozen code, and its two `run-validation.py` reports must equal run 5's (totals, per-encounter verdicts, WER) and the held-out run's. A mismatch pauses for the practitioner before anything else.
  - Record on this task: the premise check's result; per set and per variant, the counts in D6 (text and audio levels, both labelled) and the threshold-grid scores; for kept recordings n, n(enrolled), n(attribution failed), median and maximum only, the (b) median over enrolled sessions. If n(enrolled) < 3, say the budget is tested on synthetic counts only.
  - Done when: the numbers are on this task and the scratch scripts are named.
- [x] 🟩 **0.3 Check 4's shape (D1)** `[decision]` — Chosen: (b), the new code `clinician_line_omitted`, with (c)'s two exemptions added ONLY if Task 0.2's real-speech counts for (b) exceed the 0.1 budget; Task 0.2's record states which applies, and under (c) the acknowledgement set joins Task 0.9 (2026-10-22, "take all the recommendations"). Rationale: honest copy, and the existing warning's meaning and harness comparison are kept. **"Exceeds the budget" means either bound** — the median above 2 OR the maximum above 5 (peer round 1 PR-MED-003; the decision named the median only, an omission, not a choice).
- [ ] 🟨 **0.4 Missed-speech constants (D2)** `[decision]` — Rule chosen 2026-10-22 ("take all the recommendations"): the SMALLEST values that keep both new codes together within the 0.1 budget on real speech, starting from textless ≥ 1.5 s and gap ≥ 1.0 s; trigger 2 dropped (option (x)) only if it alone breaks the budget, read off the grid's trigger-2-disabled rows (peer round 2 PR-MED-013). The two values are still owed: they are read off Task 0.2's threshold-grid scores (the combined median and maximum per pair, with the (b) or (c) variant 0.3 selects) and recorded here before Task 0.9.
  - **If no pair fits** (peer round 1 PR-MED-003): when even (c) with the largest grid pair, or with trigger 2 dropped, breaks either bound, the build PAUSES before Task 0.9 and the practitioner decides in writing, from these options, without the budget itself being re-set after the numbers: (1) ship both codes and record the breach as a known cost in the Honest forecast; (2) drop the missed-speech warning from 0.3.4 (Phase 2 becomes Excluded; D7's deletion-edge term and its pins go with it); (3) narrow `clinician_line_omitted` further as a new dated decision, with Task 0.2 repeated for it.
- [x] 🟩 **0.5 The greeting gap (D4)** `[decision]` — Chosen: (a), the lists stay frozen and an unbroken next patient with an unlisted greeting is residue class R3 (2026-10-22, "take all the recommendations"). Rationale: Start per patient is the primary control; the practitioner's own phrases stay the Deferred later amendment. Consequences: Task 0.9 changes no `consultation_phrases` list; C7's live warning is untouched.
- [x] 🟩 **0.6 Hedges (D5)** `[decision]` — Chosen: lexicon (b), a blind widening from named published sources; scope (ii), the line plus a same-speaker neighbour joined mid-sentence (2026-10-22, "take all the recommendations"). Later the same day: "joined" reuses `note.ends_mid_sentence` (a trailing comma, semicolon, colon or dash on the earlier line); a bare cut is not joined — the accepted residue.
- [x] 🟩 **0.7 Residues and the rule (D7, D8)** `[decision]` — Chosen: (b), rule v2 with R1, R2 and R3 (R3 applies: 0.5 is (a)), literal per-set ceilings of 2 per class on the 50, 1 on `heldout`, 1 on `heldout-2`, D7's warned amendments (the missed-speech credit narrowed to deleted tokens at the anchor pair); the v1 verdict stays printed beside the v2 verdict (2026-10-22).
  - **The written override, in the practitioner's words:** "take all the recommendations" (2026-10-22), given in reply to the plan's recommendation of (b) and its statement that (b) overrides pilot Constraint 12 and the 2026-10-09 stop rule. The reasoning adopted is D8's: the recogniser- and tone-level failures cannot be fixed by the note pipeline. Each class is mechanical and capped, never named by encounter id. The v1 verdict stays visible, so nothing is hidden. The blind `heldout-2` is the real test. The practitioner may add a sentence of their own here before Task 0.12; it is not required.
  - Consequence: Task 4.3 builds `rule-v2.json`; P.1 runs with it.
- [x] 🟩 **0.8 The P.5 pass gate (D9)** `[decision]` — Chosen: a pass under rule v2 on all three sets (the 50 scripts, `heldout`, `heldout-2`), the v1 verdict recorded beside each (2026-10-22, "take all the recommendations").
- [ ] 🟥 **0.9 The dated freeze commit (C3)**
  - Files: `note_check.HEDGE_PHRASES` (0.6 (b): a blind session given only the selection rule and named published sources; its sources and a contamination note in the commit message); `validation.REFERENCE_HEDGES` (the same blind method, harness-only, broader; pinned a superset of `HEDGE_PHRASES`; the known-failure phrases' membership recorded on this task either way); `note_check.MISSED_SPEECH_EMPTY_SECONDS` / `MISSED_SPEECH_GAP_SECONDS` (0.4's values; nothing reads them until Phase 2); the acknowledgement set (only under 0.3 (c)); `validation.document_from_turns` moved from the fixture, with `validation.reference_document` its script adapter (D8; `fixtures/heldout_transcripts.build_document` becomes a thin call of `document_from_turns`; identical documents pinned for every scripted AND every explicit-turns held-out case, captured before the move — peer round 5 PR-MED-022); `validation.REFERENCE_GREETING_LINES` and `validation.REFERENCE_TAIL_STARTS` for every `end_and_new_patient` script of the 50 and `heldout` (D8's R3; synthetic scripts only; the tail starts pinned equal to `HeldOutCase.boundary` where one exists).
  - **Lexicon-only reconciliation in the same commit** (peer round 2 PR-MED-015): a widened `HEDGE_PHRASES` can resolve a predicted held-out divergence (`test_note_check.py:2240-2244`, `hld-19` / `-20` / `-21`) and fail the suite before Task 0.11. The freeze commit re-runs the held-out unsure, boundary and correction tests and moves each entry the new phrases resolve out of `_PREDICTED_UNSURE_DIVERGENCES` into a dated record (case id → its original 0.3.3 prediction), asserted both ways (the original prediction kept as history, the case now equal to its expectation); no case expectation changes (C2, C3). Scope (ii)'s changes stay with Task 3.1. The suite is green on the freeze commit.
  - Tests: exact pins in `test_vocabulary.py`; near-miss cases for every added phrase; the superset pin.
  - Done when: reviewed, peer-checked and committed with the date BEFORE 0.10 starts.
- [ ] 🟥 **0.11 Fixtures and lints over a set table (before the set exists)**
  - `fixtures/heldout_transcripts.py`: `HELDOUT_DIR` :62 and `SCRIPT_CASE_PREFIX` :63 → a per-set table `(folder, prefix, cases)`; `HELD_OUT_CASES` concatenates the sets; a set whose folder is absent contributes nothing (so the suite is green before 0.10).
  - `test_validation_scripts.py`: `HELDOUT` :62 and :464, the prefix asserts :354 / :386 / :388, `TestHeldOutScripts` and `TestHeldOutTranscripts` parameterised over the table; the lints :329-348 run per set.
  - The divergence dicts keyed per set with their count pins (`test_consultation_boundary.py:103` / :354, `test_note.py:~2947`, `test_note_check.py:~2242`); `heldout-2`'s entries are EMPTY here and written in 0.12.
  - Done when: the suite is green with the second folder absent, and green with an empty `validation/heldout-2/` folder present.
- [ ] 🟥 **0.10 `validation/heldout-2/` by an independent author (C12)**
  - A fresh author session in an EMPTY folder outside the repository, given ONLY a behaviour spec (written by the composer, committed with the set) and one format example: uncued clinician lines (advice, plans, safety-netting) and uncued patient lines; varied greetings and closings with negatives ("morning stiffness"); hedges and non-hedges, clinician hedges included; self-corrections; a dose read aloud; a quiet trailing clause; the lint rules in plain words (every uncertain clause routed; no line that is an autofill trigger; synthetic conditions). Same script format as `validation/heldout`; ids `h2-NN`; 20–25 scripts.
  - The author never sees the frozen lists, the 50 scripts, `validation/heldout`, the register or this plan; the session transcript is kept as the isolation record.
  - The composer copies the scripts in and runs ONLY Task 0.11's lints over them (no reading of their text beyond lint output); a lint failure goes back to the author as the lint's message.
  - Done when: `validation/README.md` names it; committed with the date before 0.12.
- [ ] 🟥 **0.12 Diagnosis, the `h2-NN` cases and the predictions (the Task 0.10 shape)**
  - Rebuild all three sets deterministically (practitioner if the agent shell cannot see the models; `docs/lessons.md`); re-transcribe through `evaluate_encounter` (the stage-3 scratch method).
  - Difference check (the premise check itself ran in Task 0.2, before the freeze): the 50 and `heldout` reports at the 0.9 commit differ from Task 0.2's only where the frozen hedge list explains it — each changed verdict listed with the encounter id and whether a 0.9 phrase sits on its line (ids and yes/no only). Any other difference pauses for the practitioner.
  - A scratch reference of decisions 0.3, 0.4, 0.6 and the R1–R3 classifiers.
  - Write the `h2-NN` `HeldOutCase` entries (turns, boundary, corrections, unsure expectations), the two R3 tables' `heldout-2` entries (the tail starts equal to the cases' boundaries) and the three divergence dicts' `heldout-2` entries from the scratch reference — this is the one task that reads the set before the build.
  - Record ids and counts only: whether `syn-22`'s fact tokens are deleted and whether a gap ≥ the frozen threshold is visible; whether `syn-28`'s wrong rendering carries a review mark (D8's `marked` flag); `syn-30` fact 0 split off or misheard; R2 membership; the class of every `heldout` failure; the new codes' counts per set.
  - Write the predictions for all three sets: pass/fail under v1 and v2, residues by class, checker tallies, the new codes' counts.
  - Frozen from here. The practitioner deletes the set folders. The record script asserts no NUL and no bare CR before writing (C10).
  - Done when: the record, the cases and the predictions are committed on this task.

### Phase 1 — Check 4 widened and the chooser marks (`note_check.py`, `note.py`, `ui/models.py`)
- [ ] 🟥 **1.1 The checker (D1)**
  - `note_check.clinician_line_omissions(note, document, config)` inside `check_note` after `omission_warnings`; `note.NOTE_WARNING_SEVERITY["clinician_line_omitted"] = "review"`; `__all__`; the code-list docstrings (`note_check.py:136`, `:192`).
  - Tests (`test_note_check.py`, a sibling of `TestCheck4Omission`): fires on a wholly uncovered clinician line; not on a partly quoted one, a filler-only line, a patient line, a line that already draws `high_risk_omission`, a line past the boundary, or with no confirmed clinician; a one-word acknowledgement fires under (b) and not under (c); the tail pin `test_consultation_boundary.py:656` unchanged; `test_note_matrix`; the five held-out silent cases asserted per 0.12's predictions; every note-level exact-code-list test in Key Findings re-checked and re-pinned deliberately where the new code fires (`test_save_as_ratification.py:342`, `test_ui_screens.py:5693-5749`); the direct `omission_warnings` pins (`test_note_check.py:1791/:1828/:1882/:2291`, `test_note_schema_v2.py:893`) and `test_transcript_trim.py:459-483` stay unchanged as regression pins (peer round 2 PR-LOW-001).
- [ ] 🟥 **1.2 The copy, acknowledgement, count line and chooser marks (D1, D3)**
  - `ui/models.py`: `WARNING_COPY["clinician_line_omitted"]` ("A line you said is not in the note"); `SEPARATELY_ACKNOWLEDGED_CODES` / `_NAMES` and `ACKNOWLEDGE_ALL_TOOLTIP` (the rename ripple); `flagged_segments` reads both omission codes; `flagged_count_line`'s wording rewritten to cover both ("a line you said, or a side, negation, number, dose, name or medication someone said"); `eligible_utterances` front marks short (D3: `[next patient?]`), marks before the speaker, the 60-character cut on the words only; `ui/note.py`'s docstring :44-77.
  - Tests: `test_ui_models` (the separately-acknowledged set, the tooltip :1979-1985, the count line, the exact labels :2025-2055), `test_ui_screens` `WARNING_COPY` parity; `test_shadow_exits.py` unchanged.
- [ ] 🟥 **1.3 Forward tolerance** — a pin that a note holding `clinician_line_omitted` reads on the stored-note path and that the 0.3.3 reader's behaviour (each new-code warning read as an `unknown_review_warning`, fields kept, grouped as one code) is what the rollback line describes.

### Phase 2 — The missed-speech warning (`note_check.py`, `ui/models.py`)
- [ ] 🟥 **2.1 The detector (D2)**
  - `note_check.missed_speech_warnings(document, config)` reading the 0.9 constants; in `check_note` after Check 4, before Check 6; `NOTE_WARNING_SEVERITY["speech_without_words"] = "review"`.
  - Tests both ways: a textless segment at and just under the threshold; an in-segment gap, a leading and a trailing gap at and under the threshold; a negative (overhang) gap is 0; suspect words count as no words; an all-suspect segment counts as textless (peer round 3 PR-MED-019); a gap across a suspect word anchors on the non-adjacent surviving words at their original indices; ONE warning per anchor line (two textless segments on one anchor; a textless segment plus an in-segment gap); past the boundary none; no worded segment → none; the anchor rules (preceding, then following); the packed-window artefact case (a textless segment whose words sit in a neighbour) documented as a residue in the test name.
- [ ] 🟥 **2.2 Copy, mark and acknowledgement** — `WARNING_COPY["speech_without_words"]` ("Speech was heard but no words were written for part of it"; clear hint "Check the line marked [gap?]"); separately acknowledged; the `[gap?]` mark from a new `gap_segments(warnings)` helper beside `flagged_segments` (the anchors' `source_coords`, never inside `_row_marks`), on every row state the omission flag shows on — `replaced` included — and in `eligible_utterances`; `flagged_segments` and the count line UNCHANGED by this code; tests as 1.2 plus the mark on a fully quoted anchor line, a REPLACED anchor row still marked `[gap?]`, and a removed anchor's segment back in the chooser with `[gap?]`.
- [ ] 🟥 **2.3 `replay_kept` per-code counts** — `note_drift` gains per-code review counts for the two new codes (integers, code names only), so the practitioner's replay and `docs/testing/kept-recordings.md` can follow them; the numbers-only output pin extended; `test_shadow_exits.py` unchanged.

### Phase 3 — Hedge scope (`note.py`, `note_check.py`, `ui/models.py`, `validation.py`)
- [ ] 🟥 **3.1 One scope rule, two inputs (D5)**
  - `note.segment_hedged(document, segment_index)` using `words_hold_hedge` and `ends_mid_sentence`; `validation.script_line_hedged(script, line_index)` with the same rule over script lines, pinned equal to `segment_hedged` on `reference_document(script)` for every `heldout` script.
  - Callers: Check 1's `reconstruction_warnings` (`note_check.py:603`), `_row_marks` (`ui/models.py:3071`; no signature change), the harness's `:1360` re-derivation and `:1425` `script_hedged`. `line_marks` unchanged.
  - Tests: `test_note`, `test_note_check` (joined by a comma yes; after a full stop no; a bare cut no; other speaker no; the clinician excluded as today), `test_ui_models` (the editor row's mark agrees with Check 1), the per-set unsure divergence entries, a harness test that a scope-(ii) mark is credited and a scope-(iii) one is not.

### Phase 4 — The harness (`validation.py`, `validation/rules/`, `docs/testing/validation-harness.md`), its own dated commit before run 6
- [ ] 🟥 **4.1 The residue classifiers (D8)** — R1 through `_fact_end_states` (no `all_matched` state) plus the `reference_document` run plus the review-mark term over the walk's `marked` flag on every wrong end state of every occurrence (its numeric near-emptiness documented); R2 only on an unsurfaced fact, through `script_line_hedged` over `REFERENCE_HEDGES`; R3 (axis, the fact at or after `REFERENCE_TAIL_STARTS`, no boundary on the measured document, no listed greeting on the `REFERENCE_GREETING_LINES` line). Each class a field on `FactOutcome` that clears ONLY its own failure predicates, through residue-adjusted counts (D8). Pins both ways for each condition, plus: an already-surfaced fact is not R2 and uses no ceiling; an R2 fact that is also `omitted` still fails `silent_omissions` unless R1; an R1 fact with an unsurfaced uncertainty still fails `uncertainty_missed` unless R2; a fact reported `wrong` with a silently omitted alternative cleared from BOTH counts by one R1 and counted once against R1; a nonmaterial `wrong` or `wrongly_present` fact consuming no allowance; a split-segment fact and a repeated-token fact where only ONE wrong alternative is marked NOT R1, and both marked R1; an unrelated `absent` fact before the tail start not R3; a boundary that fired after the fact not R3; a shared closing-and-greeting line read as the greeting line; a script with the axis and no entry in either table a harness error; the raw counts unchanged, the same outcomes giving v1 FAIL and v2 PASS. `align_transcripts` not used.
- [ ] 🟥 **4.2 The warned amendments (D7)** — `warned` reads `clinician_line_omitted` on the fact's segment and D7's deletion-edge term (`some_deleted` on every reached state, an edge word covered in original coordinates); today's `warned` carried as the walk flag `warned_v033`, with `silently_omitted_v033` across every alternative, printed as "Silent (0.3.3 predicate)" (D7); `warned_v1` unchanged and still labelled as run 1's; `_FactState`'s new fields; the report header cites the amendments (`test_validation_harness.py:1198`); D7's pins (partial deletion vs substitution, first/last-word edges, cross-segment, suspect-filtered, a transcribed uncued line beside a pause NOT credited, a patient-side omission warned by 0.3.3 and not by run 1, a reported-`wrong` fact with a 0.3.3-silent alternative, the repeated-token state-count bound).
- [ ] 🟥 **4.3 Rule v2, the set layer and the report** — `PassRule` `Literal[1, 2]` with per-set literal ceilings keyed by set name; `validation/rules/rule-v2.json`; each class clearing only its own failure predicates through the residue-adjusted counts, the raw counts and the v1 verdict untouched (D8); `run_passed`'s set-level check and a set-level failure line; `main` takes the set name (from the folder or a flag) to pick the ceilings; report: per-set class counts, a class column in the Facts table, the v1 verdict line beside the v2 verdict, the one-verdict heading replaced; every positional pin re-pinned (`"---|" * 25`, `cells = ["-"] * 18`, `cells.insert(17, …)`, the TOTAL row, `test_validation_harness.py:1184-1209`); ceilings pinned at n and n + 1; a schema-1 file with ceiling fields refused; a schema-2 file refused by a `Literal[1]` reader (documented, not tested here).
- [ ] 🟥 **4.4 The harness document** — `docs/testing/validation-harness.md`: the amendments (dated), the rule v2 section with its override text (verbatim from Task 0.7) and the set layer, `heldout-2`, the three-set gate, the fitted-ceiling statement.

### Phase 5 — Documents and version
- [ ] 🟥 **5.1 Documents (D10)** — as D10 lists; exact on-screen strings quoted from `ui/models.py`; the review guide's 0.3.4 lines marked as awaiting the practitioner's approval; a sweep of `docs/` for "high_risk_omission", "omission warning", "after possible next patient", "Acknowledge all" and "hedge" reconciled and recorded here. `test_pilot_docs.py` green.
- [ ] 🟥 **5.2 Version 0.3.4 and the rollback line** — the six version places (`npm version 0.3.4 --no-git-tag-version` needs npm; a leg without it sets them by hand); "Rolling back below 0.3.4" in `docs/release/pilot-builds.md`: the two new codes read as ONE newer-build review warning on 0.3.3, cleared by its Acknowledge all, so the separately-acknowledged control is lost there; nothing else changes on disk. Done when: `test_install_layout.py:867` green; `npm run qa`.

### Hardening stage
- [ ] 🟥 **H1** `/review-loop` to convergence over the whole run.
- [ ] 🟥 **H2** `/simplify`: trivial → `/fix`, substantial → scoped `/review-plan`.
- [ ] 🟥 **H3** `/security-review`: the new warnings' anchors (no content in a code), the kept-recording measurement script's refusals and integer-only output, the harness's handling of the reference transcript.
- [ ] 🟥 **H4** Final cross-family `/peer-review` (codex `gpt-6-astra` medium), documents included (`docs/lessons.md`: a docs-only phase still draws peer findings).
- [ ] 🟥 **H5** 0.3.4 built of record after P.1 on the H4 commit: the `Release` workflow, `gh attestation verify`, the `docs/release/pilot-builds.md` row, CI green. If P.1 forces a code change, H1–H4 and P.1 run again before H5.

### Phase P — Practitioner (normal terminal, developer build, installed app closed; C1, C8, C10)
- [ ] 🟥 **P.1 Run 6, the run of record**
  - From a clean, committed checkout at the H4 commit: check the voice baseline; build `validation/scripts`, `validation/heldout` and `validation/heldout-2` into empty folders outside the repository; run each with `.venv\Scripts\python.exe scripts\run-validation.py <set> --config validation\config --rule validation\rules\rule-v2.json` (the set name selects its ceilings).
  - Record in `validation-harness.md` "Runs of record" and `plan-pilot.md` P.3: commit, manifest hash, voices, rule and cue blobs, the amendments in force, both verdicts, the residue counts by class, the new codes' counts.
  - Read against Task 0.12's predictions; anything outside them is a finding, never a rule edit.
  - Delete the folders; check `%TEMP%` for `scribe-speaker-eval-*`.
- [ ] 🟥 **P.2 Install 0.3.4 and smoke it**
  - Verify (`gh attestation verify`, hashes) and install at a pilot-allowed point; reload the extension; restart Chrome.
  - Mock smoke (desktop-started, no patient, shadow on, no development tick, Discarded): an uncued clinician advice line shows "A line you said is not in the note", Acknowledge all leaves it, the per-code click clears it; a deliberate pause mid-sentence shows the missed-speech warning with `[gap?]` on the right line, or is recorded as not shown; a hedge after a comma-cut line shows `[check: unsure]`; the chooser's `[flagged]` / `[next patient?]` / `[gap?]` marks are readable; the count line reads correctly; the Status tab shows 0.3.4.
  - Done when: the result is on this task and AGENTS.md says 0.3.4 is installed.
- [ ] 🟥 **P.3 The register and the P.5 question**
  - Move rows to `resolved` ("0.3.4 (commit <H4 short hash>)") or keep them `controlled` (control text ≤ 200 characters) by the run's result; new rows from `heldout-2` as `h2-NN` — the Encounter cell pattern in `test_pilot_docs.py` gains `h2-NN` with a both-ways case (:266-292), and the register's prose (:20, :33) and `docs/pilot/README.md:161` name the third id form.
  - Put the P.5 question (shadow off?) to the practitioner as a dated decision on `plan-pilot.md`.
  - Done when: `test_pilot_docs.py` green and committed.

## Retained Follow-Up Items
None yet.

## Follow-Up Continuation Notes
- If `heldout-2` fails: record the findings, keep P.5 (a), and plan `heldout-3` with a 0.3.5 fix — never tune 0.3.4's constants, lists or ceilings to it.
- If run 6 exceeds the R1 ceiling: the larger-model plan (Excluded here) becomes the next candidate.

---
_Plan hardened by `/review-plan` 2026-10-22 (Opus 5.5, then Fable 5.1). Planning only: nothing built, nothing committed._
