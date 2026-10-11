# Feature Implementation Plan
**Feature:** validation-pass — the leftovers of validation run 3, version 0.3.3:
- a next-patient boundary, so the note stops at a possible next patient;
- the clinician's removal of the next patient's speech from the recording;
- a self-correction carry;
- a speaker-unsure mark, with a dated metric amendment, if the practitioner chooses it;
- the `syn-28` decision;
- a held-out synthetic set and a repeated validation run as the acceptance check.

**Overall Progress:** `0%` (0 of 30 tasks)

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- **Parent plans:**
  - `plan-pilot.md`: its Task P.3 run 3 FAILED on 2026-10-12. Its P.5 (shadow off) and the clinic 1 exit gate's "Validation passed" wait for a run that passes.
  - `plan-note-routing-omissions.md`: its retained follow-ups are new-patient detection and the question-answer hop of the carry. This plan takes the first; the second stays deferred.
- **Related plans:**
  - `plan-invented-text-guard.md` (0.3.2): lands FIRST, built on `main` in the session "Build the invented-words guard (0.3.2)". This plan builds on its mark convention (`line_marks`, `[check: …]`), its per-line codes, its D6 reader changes and its primer.
  - `plan-ui-refresh.md` (0.4.0): replaces the Transcript and Note tabs with one Review screen and adopts this plan's codes, chooser marks and Transcript-tab action as data.
  - `plan-past-sessions-backup.md` (0.4.0).
  - `plan-cliniko-workflow-safeguards.md`: its D8 new-consultation warning shares this plan's phrase lists.
  - `plan-clinic-smoke.md`: D9, nothing tuned after a run; D12, nothing per consultation in a tracked file.
- **Follow-up plans:** None yet; candidates are under Deferred.

## Goal
Plan the fixes that stand between validation run 3 (37 of 50 passed) and a PASS under rule v1 as amended 2026-10-09. Rule v1, the practitioner's cue file and the scripts' facts never change. A residue that cannot be fixed honestly is recorded as one, and the P.5 question then goes to the practitioner as a dated pilot-level decision.

The run 3 leftovers:

| Group | Encounters | Cause |
|---|---|---|
| (1) Next patient | `syn-06`, `-20`, `-21`, `-38`, `-46` | Each fails on its material `absent` fact. There is no end-of-consultation boundary, so the next patient's cued line is quoted. |
| (2) `syn-28` | `syn-28` | The recogniser lost "naproxen", so the dose fact is `wrong`. |
| (3) `syn-48` | `syn-48` | Silent omission. The patient's correction "Actually no, it is better…" became its own uncued segment after a full stop. The carry does not fire, so the note keeps the retracted "Worse since last session" and drops the correction. |
| (4) Uncertainty | `syn-12`, `-30`, `-35`, `-41`, `-44`, `-49` | 9 of the 10 `expect_uncertain` facts are never surfaced. The harness credits only recogniser confidence below 0.60, and clean synthetic speech is confident. 9 of the 10 facts sit in patient lines with a SPOKEN hedge. |

While here, the next patient's speech is also taken out of this patient's stored record, on the clinician's explicit action (Step 3.5 gate, 2026-10-12: Include in plan).

### Honest forecast
This is written before the run and not tuned toward:
- Groups (1) and (3) are fixable by product changes that have a clinical purpose.
- Group (4) is fixable only by a new mark PLUS a third dated metric amendment that overrides pilot interpretation 7. That is the practitioner's decision 0.1.
- Group (2) is recogniser accuracy. It passes only if the 0.3.2 primer happens to recover the word, or if decision 0.4 (b) is taken.
- `syn-35`'s "50 degrees" is a clinician line at 0 dB with no hedge, so it stays acoustic-only.

A PASS is an outcome to report, never a target.

## Planning Extraction Summary
Populated 2026-10-12 from:
- the Plan Mode draft (Opus 5.5, approved by the practitioner);
- the planning conversation;
- one design critique of the first draft;
- the four-lens `/review-plan` pass: coverage, practicality and risk, simplicity, and the reconciliation in this session.

Every finding was checked against the code at `8e5e571`, which equals `main` at planning time; nothing from 0.3.2 is built there yet. No `/explore` scratch was consumed: the two existing ones are unrelated, declined 2026-10-12.

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Opus 5.5 (Plan Mode and `/review-plan`; the practitioner's usual planning model is Fable). The build runs through `/execute-loop`: Opus-class executor, cross-family peer codex `gpt-6-astra` medium. The diagnosis, the held-out audio run, this plan's run of record, the install and the smoke are run by the PRACTITIONER from a normal terminal and the app, never from an agent shell (`docs/lessons.md`, MSIX). Tier-gap dosing applied: the decisions' options and recommendations, the boundary rule, the carry rule, the credit rule, the pin inventory, the acceptance predictions and the rollback behaviour are locked here.

### Agreed Scope (Build Now — 0.3.3)
- **Phase 0:** seven practitioner decisions (0.1–0.7); one dated vocabulary commit; a held-out synthetic set written from a behaviour spec by a session that has not seen the vocabulary; the diagnosis on the synthetic set at the guard's hardening commit, with the run predictions written down.
- **Phase 1:** the next-patient boundary.
  - One role-free pure function in a new leaf module, shared with the live new-consultation warning's lists.
  - The provider request cut at the boundary; autofill and prefill limited to it.
  - Check 6 `possible_next_patient` (review, separately acknowledged).
  - Chooser rows after the boundary marked.
  - A fixture lint.
- **Phase 2:** the self-correction carry, if decision 0.3 is taken.
- **Phase 3:** the `hedged_source` mark and the third metric amendment, if decision 0.1 (a).
- **Phase 4:** the clinician's "Remove lines N–end from this recording" on the Transcript tab, through `write_transcript`, with the kept-recording rule from decision 0.6.
- **Phase 5:** documents, the rollback line, version 0.3.3; hardening H1–H5.
- **Phase P:** this plan's run of record plus the held-out run, the install, the smoke, the register.

### Deferred — Actionable Later
- **A one-click undo of a false boundary** (a "use the whole transcript" tick on the Transcript tab before Generate). Step 3.5 gate, 2026-10-12: Defer.
  - Why deferred: the Note tab has no regenerate path (`ui/note.py:2424-2433`; generation lives in `ui/transcript.py:797-845`). Check 6 recomputes from `(note, document, config)` (`note_check.py:1719-1756`), so it re-fires after an override unless a flag is persisted. `NoteDraft` is `extra="forbid"` (`note.py:2333`). The chooser already restores lines.
  - Intended future outcome: a pre-Generate tick, with the flag carried on the in-memory `NoteGenerationResult` (`ui/models.py:2334`), never on a persisted model. Check 6's wording stays true in both modes. The prefill limit is kept, to avoid `PrefillSelectionAmbiguousError` (`note_fill.py:306-312`).
  - Relevant files: `ui/transcript.py` `generate`, `ui/models.py` `build_note_generator` (`:2957`), the three fakes in `test_ui_screens.py` (`:7451`, `:8050`, `:9595`).
  - Dependencies: Phase 1 as built.
  - Recommended next action: plan it if P.4/P.5 shadow use meets a false boundary.
  - Risk if deferred: `ux-degradation`: a false mid-consultation boundary costs one chooser click per withheld line.
  - Revisit by: the first false boundary in shadow use, or the clinic 1 exit gate.
- **A divider in the transcript view at the possible next patient.** Step 3.5 gate: Defer.
  - Why deferred: chooser rows are already marked; the ui-refresh Review screen is its natural home.
  - Intended future outcome: a marked line in `format_transcript_text` (`ui/models.py:1754`) or the Review screen.
  - Risk if deferred: `minor`.
  - Revisit by: the ui-refresh Review screen task.
- **A review mark pairing a retracted statement with its carried correction.** Step 3.5 gate: Defer.
  - Why deferred: after Phase 2 both lines are in the note, in order.
  - Risk if deferred: `minor`.
  - Revisit by: a P.5 finding of a retracted line kept.
- **The question-answer hop of the carry** (carried from `plan-note-routing-omissions.md`; that plan's gate disposition stands).
  - Why deferred: no run 3 leftover needs it, and its known harm (`syn-43` wrongly present) may vanish once the boundary withholds the next patient.
  - Risk if deferred: `ux-degradation`: an uncued answer to a cued question with no structured-claim word stays silent.
  - Revisit by: a P.5 finding of category `omission`.

### Excluded — Revisit Only If Needed
- **Raising `UNCERTAINTY_THRESHOLD`.** It tunes a gate against the acceptance set (pilot Constraint 12) and touches every note's review load. When to revisit: never for this purpose.
- **Option (c) for uncertainty:** a rule version counting uncertainty missed only on non-`correct` facts (foreseen at `plan-pilot.md:1892`). It is a rule change after runs, needs no app feature, and is exactly the "masks a regression" shape the guard plan rejected (`plan-invented-text-guard.md:61`). When to revisit: only as a new ratified rule by the practitioner, never to unblock this plan's run.
- **Editing scripts, the cue file or rule v1.** These are the hard rules.
- **Signalling the boundary through `high_risk_omission`.**
  - Check 4 fires only on claim tokens (`note_check.py:1485-1505`), so a greeting line may draw nothing.
  - Its copy would be false.
  - The harness reads it as `warned` (`validation.py:1287-1316`), which would contaminate the omission metric.
- **A turn-carry without markers** (carry within one speaker's turn across a short gap). It reverses D11's narrow design, and nobody plans to build it.
- **A larger Whisper model, or a music or speaker model.** These change the model pack; out of scope.

### Accepted Assumptions — Revalidate Later
- **A1 — The synthetic held-out set exercises the mechanisms honestly enough.**
  - Why accepted: its author never sees the vocabulary or the scripts' wording, and it is recorded, never tuned to.
  - Risk if false: a real-speech false boundary or false carry is missed.
  - Trigger for revisit: P.4/P.5 shadow use.
  - Recommended next action: record any false boundary in the register.
- **A2 — In the app every generation has a confirmed clinician** (`build_note_generator(clinician_speaker: str)`, `ui/models.py:2957-2959`; Generate needs a role, `ui/transcript.py:801-804`).
  - Why accepted: the code says so; only the replay tool and fixtures have no role.
  - Risk if false: the role-scoped hedge mark misses lines.
  - Trigger: a change to Generate's role requirement.
- **A3 — Vocabulary contamination is disclosed, not avoided.** The planner has read the scripts, and the hedge and greeting wording in this plan reflects them (practicality lens M-8).
  - Why accepted: the vocabulary is frozen in a dated commit with an outside source where possible, and the held-out set is the honest check.
  - Risk if false: run 5 passes for script-shaped reasons.
  - Trigger: held-out results.

### Key Design Decisions
D1–D12 below, under Design Decisions, each with its rejected alternatives. They still apply to follow-up work: Yes (all).

## Key Findings

### Files / Symbols Involved
All references are at `8e5e571`, under `desktop/src/scribe_desktop/` unless prefixed.
- **Routing.**
  - `note.py` `ExtractiveNoteProvider.generate_sections` (`:1725-1777`): D11's carry conjuncts are at `:1746-1755`.
  - Helpers: `ends_mid_sentence` (`:1437-1449`); `any_cue_matches` (`:1452-1470`, role-free and question-free, False on empty tokens); `content_tokens` (`:256-264`, fillers `_FILLER_TOKENS` `:230-232`, which do not include "well"); `normalise_token`.
  - `_assemble_note_request` (`:1107-1148`, its only caller is `note_config.build_note_request` `:2856-2897`). The AST guard pins exactly one call node (`test_note_config.py:535-539`, counting at `:610-618`), so a new keyword does not move it.
  - `NoteRequest.words_for_coords` resolves a FILTERED request by absolute segment index (`:1090-1104`), and so does `note_check._words_for_coords` (`:438-441`).
- **Proposals.**
  - `note_fill._first_phrase_match` (`:147-171`) is the ONE segment walk.
  - Its callers: `autofill_proposals` (`:194`, `:209`) and `_earliest_keyword_match` (`:233`, `:239`). `detect_prefill_candidates` (`:250`, `:264`) and `prefill_proposals` (`:281`, internal calls `:306` and `:321`) reach it through those.
  - External callers: `compose_draft` (`note.py:2538-2539`), `ui/transcript.py:563` (the prefill drop-down), `validation.first_detected_prefill` (`:1618-1623`), and Check 3 `autofill_trigger_absent` (`note_check.py:1421`, whole transcript).
- **Checks.**
  - `check_note` (`note_check.py:1719-1756`) runs Checks 1–4.
  - Check 1 is `reconstruction_warnings` (`:490-544`).
  - Check 4 is `omission_warnings` (`:1508-1554`). It returns `()` when no clinician is confirmed (`:1521-1522`) and flags uncovered words passing `_omission_flag_token` (`:1485-1505`) per segment.
  - `NoteWarning` (`note.py:577-608`; `_check_code` refuses unregistered codes); `NOTE_WARNING_SEVERITY` (`note.py:292-340`, 14 codes).
- **Review UI.**
  - `ui/models.py`: `WarningCopy` (`:2042`, static `title`, `blocks`, `clear_hint`); `WARNING_COPY` (`:2054-2161`, parity with the severity map pinned at `test_ui_screens.py:4470`); `_fallback_copy` (`:2195`); `summarise_warnings` (`:2199-2228`, one row per code, in first-appearance order); `SEPARATELY_ACKNOWLEDGED_CODES` (`:2235`, pinned `== {"high_risk_omission"}` at `test_ui_models.py:1551`); `acknowledge_all_codes` (`:2238-2248`); `flagged_segments` and `flagged_count_line` (`:2501-2541`); `eligible_utterances` (`:2559-2588`).
  - `ui/note.py`: the warning rows (`:2215-2251`); `cancel_review` (`:2424-2433`).
  - `ui/note_review.py`: `review_counts` (`:475-493`).
- **Transcript tab.** `ui/transcript.py`: `generate` (`:797-845`, under `controller.begin_generation()`); `keep_generated` (`:918-934`, replaces `generated.enc`); the prefill detection (`:539-564`).
- **Storage.**
  - `transcription.write_transcript` (`:1058-1110`): the ONE atomic transcript writer. It unlinks a stale `note.enc` first, fail-closed.
  - `session_store.complete_session` (`:1272-1420`): archives `transcript_plain` and `note_plain` as they are. The archived note's `transcript_digest` must equal the transcript's (`:779`, `:1550`).
  - `session.SessionController._complete_locked` (`:1168-1200`, `kept=` drives `keep_audio`).
  - `past_sessions.PastSessionStore.write_entry` (`:673-700`).
- **Live warning.**
  - `voice_commands.py`: `NEW_CONSULTATION_WINDOWS = 3` (counts live WINDOWS); `CLOSING_PHRASES` and `GREETING_PHRASES` (`:67-96`); `phrase_tokens` (`:104`); `_tokens` (`:121-129`); `NewConsultationWatcher` (`:190-230`), fed at `ui/main_window.py:1610`.
  - Exact pins: `test_hands_free.py:331-363`; window and near-miss pins: `:374-400`.
  - `voice_commands` imports `session` (`:50`), and `session` → `draft_write` → `note_config` (`session.py:66`, `draft_write.py:140`). So `note_config`, `note_fill` and `note_check` must NOT import `voice_commands`.
- **Harness.** `validation.py`:
  - `_WordInfo` (`:694-721`); the fact walk (`_FactState` `:872-886`, `_fact_end_states` `:894-924`, `_judge` `:935-950`);
  - `encounter_metrics` (`:1228-1403`), which reads `low_confidence_source` coords at `:1292-1299`;
  - `render_report` (`:1804-1931`, header `:1823-1828`, separator 22 columns `:1829`, unmeasured row `:1842`, totals `:1891-1898`, tally `:1905`).
  - Report-shape pins: `test_validation_harness.py:1109-1165`. Script lints: `test_validation_scripts.py` (hardwired to `validation/scripts`, `:38`).
- **Replay.** `replay_kept.note_drift` (`:297-330`) regenerates through `compose_draft`, `first_detected_prefill`, `finalise_note` and `check_note`, so the boundary, Check 6, the carry and the hedge mark all change its "Sections missing" and "Check reviews". The role is unknown without `--enrolment` (`:362`).
- **Register rows this plan moves** (`docs/pilot/findings-register.md`):

  | Group | Rows |
  |---|---|
  | Next patient | F-061 `syn-06`, F-068 `syn-20`, F-085 `syn-21`, F-078 `syn-38`, F-083 `syn-46` |
  | `syn-28` | F-071, F-072 |
  | `syn-48` | F-055 |
  | Uncertainty | F-013 `syn-12`, F-033 `syn-30`, F-038 `syn-35`, F-047 `syn-41`, F-051 `syn-44`, F-057 `syn-49` |

  `syn-43` (F-049, resolved) is predicted to gain the boundary. Status vocabulary is `open|resolved|controlled` only, control text 200 characters or fewer with no quotation marks (`test_pilot_docs.py:236`).

### Codebase Integration Notes
- **Shared-helpers inventory** (cross-phase):
  - `consultation_phrases.py` (new leaf module, D1): the phrase lists, `phrase_tokens`, the phrase-event helper and `consultation_boundary(document_or_segments, cues, fallback_cues)`.
  - `note.any_cue_matches` and `note.content_tokens` (D2, D3).
  - The guard's `line_marks` and `line_marks_by_assertion` (D7).
  - `transcription.write_transcript` (D9).
  - `SEPARATELY_ACKNOWLEDGED_CODES` (D5).
- **0.3.2 lands first.** Rebase onto it as built:
  - its `line_marks(words)` and the marks rendering (`_clean_lines`, `assertion_label`, `EditableLine.marks`);
  - its Check 4 suspect-word exclusion;
  - its `_first_phrase_match` suspect skip (composes with D3's limit);
  - its `voice_commands._tokens` suspect exclusion (moved into the leaf module and shared by the boundary, D1/D2);
  - its harness column (22 → 23);
  - its forward-tolerant `NoteWarning` reader (practitioner decision 2026-10-12, confirmed by the guard session): an unknown review-severity code reads as a generic review warning and an unknown error code is still refused. A note carrying this plan's two review codes therefore reads on 0.3.2.
- **Phase-tag pitfall:** no string constant `"wave"` anywhere in the package (`test_shadow_exits.py:790`).
- **Build venv:** the main `.venv` is an editable install of the MAIN folder's `desktop/src`. A build in a worktree must use a venv bound to its own checkout, or run the suites in the main checkout.

### External / API Findings
- Not relevant: no network, no new model, no new dependency.

## Planned Workflow Summary

### Flow 1 — A recording that runs into the next patient (0.3.3)
1. **Before Generate.** The Transcript tab shows "A possible next patient starts at line N" when the boundary rule fires. The clinician may press "Remove lines N–end from this recording…" behind a confirmation, which trims the transcript (Phase 4). Or they generate as is.
2. **Generate.** The note stops before line N. The Note tab shows the review row "The note stops where a new patient may have arrived" with its own Acknowledge; Acknowledge all leaves it.
3. **Reviewing the withheld tail.** Check 4 still flags withheld claim words, so chooser rows from line N carry " — after possible next patient", flagged or not. Any line that belongs to this patient is added back from the chooser.
4. **Save and Complete as today.** With the tail removed (the trim also removes any earlier `generated.enc`, D9), the Past-sessions entry, its generated note and any replay hold only lines before N. The kept recording follows decision 0.6.

### Flow 2 — A self-correction split by the recogniser
- "Worse since last session." is cue-routed. "Actually no, it is better…" is uncued, from the same speaker, and opens with a marker.
- It is carried into the same section, so both lines are quoted in order (D4).

### Flow 3 — A hedged patient line (if 0.1 (a))
- A quoted line from a speaker who is not the clinician, holding a hedge phrase, shows `[check: unsure]`.
- The review row "A quoted line says the speaker was unsure" is cleared by Acknowledge all.
- Copy omits the mark (guard decision 0.5).

### Flow 4 — The practitioner's runs
- **Diagnosis (Task 0.10):** at the guard's hardening commit.
- **Held-out audio run, then this plan's run of record (P.1):** at this plan's H4 commit, both read against the written predictions.

## Design Decisions

### D1 — One leaf module holds the phrases and the boundary rule
**Decision.** New `consultation_phrases.py` imports only `note` and `transcription`. It holds:
- `CLOSING_PHRASES` and `GREETING_PHRASES` (moved from `voice_commands`, which re-exports them so `test_hands_free.py:44-47` keeps importing from there);
- `phrase_tokens`, and the word-to-token function `_tokens` (with the guard's suspect-word exclusion as built, D2);
- one phrase-event helper used by `NewConsultationWatcher` and by `consultation_boundary`;
- `BOUNDARY_SEGMENTS = 3`, a separate constant: the watcher's `NEW_CONSULTATION_WINDOWS` counts live windows, the boundary counts non-transparent segments.

**Why:** `voice_commands` is in an import cycle with the note modules (Key Findings). One list feeds both the live warning and the offline boundary, so they never disagree on vocabulary.

**Rejected alternatives:**
- the boundary in `voice_commands` (the cycle);
- in `note.py` (it would need `phrase_tokens`, which lives beside the lists);
- separate lists per consumer (drift).

### D2 — The boundary rule (role-free, deterministic)
**The rule.** `consultation_boundary` returns the absolute index of the FIRST non-transparent segment S such that ALL of these hold:
1. S holds a greeting phrase. A single-word greeting such as "hi" or "hello" counts only as the first token of the segment or of a sentence after `.?!`, AND followed by punctuation or the segment's end.
2. A closing phrase occurs earlier in S, or in one of the `BOUNDARY_SEGMENTS` preceding non-transparent segments.
3. Some non-transparent segment BEFORE that closing satisfies `any_cue_matches(cues, fallback_cues, content_tokens(text))`. This is the head-case guard: a recording started while the previous patient leaves is never cut.

**Edge cases.**
- The returned index is always the FIRST SEGMENT TO WITHHOLD, and it is always a non-transparent segment.
- When the closing and the greeting sit in the SAME segment, the boundary is the NEXT NON-TRANSPARENT segment, failing toward inclusion; when no such segment follows (the pair is at the end of the document, or only transparent segments follow), the function returns None. (Peer round 1 PR-MED-003.)
- Transparent segments (no words or empty text) are skipped.

**Suspect words (the guard's D6; peer round 2 PR-MED-006).** The boundary reads its phrase tokens through the SAME token function as the live watcher — `voice_commands._tokens` as the guard builds it (Task 2.4: suspect words excluded), moved into the leaf module with the phrase-event helper — so a suspect word can never supply a closing or a greeting, and the live warning and the boundary cannot disagree on it. The guard marks every word of a suspect segment, so a wholly suspect greeting or closing segment contributes no phrase at all. Suspect segments stay non-transparent (D2's segment counting and the head-case cue rule are unchanged), and the watcher's live behaviour is unchanged (C7). Named residue: if that function drops suspect words rather than breaking the token run, a phrase could in principle straddle a suspect segment; it fails toward a boundary only when a real closing and a real greeting surround it.

**Inputs.** `cues` is the canonical config's own cues (`config.normalised_cues()`); `fallback_cues` is `DEFAULT_SECTION_CUES`. Every consumer computes the boundary from `(document, config)` itself (D3), so all agree. A test pins the agreement.

**Vocabulary.** Decision 0.2 adds the practitioner's own phrases, frozen in Task 0.8. No bare time-of-day word, no "welcome", no "how are you going".

**Why.**
- The existing lists (workflow-safeguards D8, 2026-09-28) predate the scripts (2026-10-07), so they are script-blind.
- On the 50 script lines they fire on `syn-06`, `-20`, `-21` and `-43` and nowhere else; they miss `syn-38` and `-46`.
- The first-position rule rejects "…in the morning." (`syn-03`, `-38`, `-49`).
- `any_cue_matches` is D11's own role-free test.
- The FIRST pair is used. Task 0.10 simulates first against last; changing it needs a dated note.

**Rejected alternatives:**
- "punctuation or end of utterance" (matches sentence-final "morning");
- "the second half of the recording" (breaks on a long tail);
- a speaker-role-based guard (`note_fill` and the Transcript tab have no role);
- K segments with no cue test (named in Task 0.10's simulation only).

### D3 — Where the cut applies
- **The provider request.** `note_config.build_note_request` computes the boundary and passes `boundary: int | None` into the one `_assemble_note_request` call. That function enumerates `document.transcript_segments` and keeps indices below the boundary, so indices stay absolute. It is never truncated through `model_copy`, which skips the order validator (`note.py:1073-1088`). `transcript_digest` stays the whole document's.
- **Autofill and prefill.** `note_fill`'s public entry points (`autofill_proposals`, `detect_prefill_candidates`, `prefill_proposals`) compute the boundary themselves and pass `limit=` to `_first_phrase_match`. `compose_draft`, `ui/transcript.py:563` and `validation.first_detected_prefill` are therefore unchanged. This composes with the guard's suspect-word skip.
- **Stays whole-transcript (recorded):**
  - Check 3's `autofill_trigger_absent` (`note_check.py:1421`): the safe direction.
  - `speaker_role` and `speaker_quotations` (role preselection; the harness takes the role from the label track, so runs are unaffected).
  - Check 2: it reads only quoted lines (`note_check.py:1309`), so it stops seeing the next patient automatically.

**Why:** every consumer already holds `(document, config)`, and the request cut reaches every provider, including a future LLM.

**Rejected alternatives:**
- cutting inside `generate_sections` (future providers would miss it);
- threading `limit` from `compose_draft` (more call sites);
- the "prose stage sees no tail" claim (the prose stage never reads the transcript).

### D4 — The self-correction carry (if decision 0.3)
**Rule.** D11's carry condition at `note.py:1746-1755` becomes `(prev_open or opens_with_correction(words))`. Every other conjunct is unchanged: previous cue-routed, same speaker, not `CLINICIAN_OWNED_SECTIONS`, no cue in any layer, one hop.

`opens_with_correction`: the utterance's content tokens START with a marker, optionally after a leading "well". The markers (frozen in Task 0.8; recommendation) are "actually", "i mean", "i meant" and "correction".

**Why:**
- Without it, a retracted statement stays in the note while its correction is dropped.
- The `contradictory` axis is this shape.
- The smallest change.

**Named residues:**
- an "Actually, …" opener of unrelated content is carried (misplaced, not lost; the harness does not measure placement);
- a fenced-off clause after a marker is quoted, as D11's comma residue already is.

**Rejected alternatives:**
- "sorry no" and "no wait" (they carry "Sorry, no, don't write this");
- "within the first two content tokens" (it matches "Yes actually…");
- broadening `ends_mid_sentence` to full stops (reverses D11).

### D5 — Check 6 `possible_next_patient`
**What it is.** A REVIEW-severity warning, once per note, with coords on the whole boundary segment: `SourceCoords(segment, 0, len-1)`. The boundary segment is the first segment withheld (D2), which need NOT hold the greeting (the same-segment case points at the segment after the pair); it is valid because D2 only ever returns a non-transparent segment, which has at least one word. `section_key` follows Check 4's convention for a warning with no assertion. It is appended last in `check_note`, and it is role-free: tested with no confirmed clinician, although the app always has one (A2).

**Copy.** Static `WARNING_COPY`, landing in ONE commit with `NOTE_WARNING_SEVERITY`. Title: "The note stops where a new patient may have arrived". Hint: "later lines were left out — add back any that belong with Add line, or remove them from the recording on the Transcript tab".

**Acknowledgement.** The code joins `SEPARATELY_ACKNOWLEDGED_CODES`: rare, and it withholds content.

**Why.**
- Review severity, because an error would deadlock Complete (`note.py:282-290`).
- Static copy, because `WarningCopy` is per code.
- A distinct code (see Excluded).

**Rejected alternatives:**
- dynamic "line N" copy (a new rendering seam; the chooser marks name the lines);
- `error` severity.

### D6 — Check 4 over the withheld tail (decision 0.5; recommendation)
**Recommendation.** Check 4 stays unchanged: the withheld tail's claim words still draw `high_risk_omission`, which is fail-safe and never silent. Chooser rows at or after the boundary are labelled " — after possible next patient" by `eligible_utterances`, composed after the routing plan's `[flagged]` front mark and the guard's suffix order, so the clinician is never steered blindly to the other person's lines.

**Alternative (b).** Exclude segments at or after the boundary from Check 4. This is quieter, but a false boundary then has only Check 6. It is also a harness-reading change (`warned` needs the warning), so it would need its own dated line.

### D7 — The hedge mark and the third metric amendment (if decision 0.1 (a))
**App side.**
- `note_check.HEDGE_PHRASES` is a closed tuple, frozen in Task 0.8 from an outside hedging lexicon where possible; contamination is disclosed (A3). Typographic apostrophes are folded first, as Check 5 does (`note_check.py:1570-1571`).
- The guard's `line_marks` gains a keyword `clinician: bool` and the mark "unsure" for a NON-clinician line holding a hedge.
- Check 1 emits `hedged_source` (review) once per quoted line, with LINE-span coords, the guard's `number_source` convention, after the reconstruction check. An invalid or mismatched line draws none.
- The editor's `EditableLine.marks` passes `segment.speaker == clinician_speaker`, so it agrees with Check 1 (the editor cannot read warnings).
- The rendered note's marks come from the WARNINGS, not the words: the guard's `line_marks_by_assertion(note)` gains `hedged_source` → "unsure" beside its two codes, and its `section_marks_line` counts unsure lines in the prose section summary ("…; N lines check: unsure"). So a freshly generated note and a note reloaded from `note.enc` show the same `[check: unsure]` in Clean and verbatim and the same count under prose (peer round 3 PR-MED-007).
- Not in `SEPARATELY_ACKNOWLEDGED_CODES`. Copy omits the mark (the guard's `check_marks=False`), and the Cliniko Write stays bare, as for the guard's marks.
- A single-cluster transcript (the only speaker is the clinician) gets no mark. This is recorded on decision 0.1.

**Harness side.** Its own commit, dated before this plan's run of record, titled "rule v1 as amended 2026-10-xx (2)", in the call-3 style. It overrides interpretation 7 (`plan-pilot.md:1892`) and answers the guard plan's "widening masks a regression" objection in writing.
- `_WordInfo` gains `hedged` (OR-merged), filled from `hedged_source` coords as `low_confidence` is (`validation.py:1292-1299`).
- The fact walk gains one state flag beside `surfaced`.
- `_judge` credits `hedged` ONLY when the verdict is `correct`, the fact's SCRIPT line holds a `HEDGE_PHRASES` phrase, AND the marked segment's own words hold one (re-derived, as `warned` re-derives `_omission_flag_token`). Surfacing still requires every equal-cost alternative.
- New columns: "Surfaced (acoustic only)" (the old predicate) and "Hedge marks on unhedged segments" (expected 0). 23 → 25 columns after the guard's.

**Pins, both ways:**
- a hedged correct fact with a mark reads surfaced;
- an unhedged script line with a mark reads not surfaced;
- a mark on a segment without a hedge gives no credit and counts in the new column;
- a hedged fact with no mark reads not surfaced;
- a stub marking every line gains credit only where both the script and the segment hedge, and its other marks show in the count;
- `low_confidence` alone still surfaces;
- the acoustic column equals runs 1–3's predicate.

**Stated coarseness:** in `syn-30`, `-41` and `-49` the hedge may be about a neighbouring clause.

**Rejected alternatives:**
- per-hedge-word coords (they never meet the fact walk without a second alignment pass);
- crediting the verbatim hedge with no app change (masks);
- folding into `low_confidence_source` (its copy says the recogniser was unsure, and the acoustic column would become impossible).

### D8 — `syn-28` (decision 0.4)
- **(a) A recorded recogniser residue.** The control is the guard's `[check: number]` on the dose line plus review.
- **(b) A script-blind medication cluster in the primer.** The generic names come from `note_check._MEDICATION_LEXICON` (`:312-319`, added 2026-08-11, which predates the scripts), selected by a written rule: names the real tokenizer splits into three or more tokens, within the 193-of-~210 token budget (`transcription.py:160-170`). It obeys the guard's D1 (no number, no cue).

Option (b) is possible ONLY inside the guard plan's Task 1.1, before its Task 3.1 measurement, because the primer-echo feature reads the primer. The decision must reach that session before its Task 3.1. Recommended: (a).

### D9 — Removing the tail from the recording (Phase 4; Step 3.5 gate: Include in plan; design confirmed 2026-10-12)
**The action.** An explicit, confirmed clinician action on the Transcript tab: "Remove lines N–end from this recording…". It is shown only when the boundary rule fires, never automatic: a false boundary must never delete real content that is kept for 7 years.

It writes a `TranscriptDocument` holding segments before N through the ONE writer `transcription.write_transcript`. That writer unlinks a stale `note.enc` first, so the saved note and its `transcript_digest` stay consistent with the transcript.

**`generated.enc` is invalidated too (peer round 1 PR-HIGH-001).** `write_transcript` does NOT touch `generated.enc` (`session_store.py:41-45`; `keep_generated` replaces it only on a later generation, `ui/transcript.py:918-934`), and Complete copies it into the Past-sessions entry (`session_store.py:1390-1395`). An earlier generation that quoted the tail (Generate → Cancel review → trim → Complete with no regeneration) would otherwise archive removed text for 7 years. So the trim removes `generated.enc` fail-closed BEFORE the transcript write, and refuses the trim (nothing changed but any marker, below) when the removal or the check that it is gone fails. After a trim, the Past-sessions entry and any replay hold only lines before N; the entry's generated note is the next generation's, or none.

**Custody and order (peer round 1 PR-HIGH-002).** The trim is ONE controller-owned operation on `SessionController` (never a direct store call from the tab), under the session lock, which re-checks at execution: the same session id the confirmation named, no generation lease, no saved note, and not a session in recovery handling. Its steps, in this order, each durable before the next:
1. under decision 0.6 (a), write the content-free no-audio marker (atomic write, then confirm it reads back); a write or inspection error refuses the trim with nothing else changed;
2. remove `generated.enc` and confirm it is gone; a failure refuses the trim, KEEPING the marker;
3. `write_transcript` with the shortened document; a failure leaves the marker in place and the old transcript.

A marker is never removed once written: the fail-safe direction is "no audio kept", so a failure after step 1 costs the kept recording, never privacy. Under decision 0.6 (b), step 1 is the audio trim's own committed state instead, under the same rule (Task 4.2 specifies it).

**The trimmed transcript is authoritative across restart.** Recovery never re-transcribes a session that already has a transcript (`ui/recovery.py:6-9`, `:207`), so it cannot restore the removed tail from `audio.enc`; Task 4.2 pins this (trim → restart → recovery reads the trimmed transcript and offers no re-transcription). An unreadable trimmed transcript is handled as any unreadable transcript is today (fail closed; no tail restored).

**When it is enabled.** Only when no review is open (no generation lease) and no note has been saved. After Save, it is refused with copy saying to Cancel or Discard. Confirmation copy follows the design system's destructive-confirmation style.

**The kept recording** follows decision 0.6.
- (a), recommended: a trimmed session keeps NO audio at Complete. A content-free marker in the session directory, written FIRST in the trim's ordered steps (above), makes `_complete_locked` pass `kept=False` on every Complete path, live and recovered; the audit row then shows "not kept" by its existing facts.
- (b): trim `audio.enc` to the chunks ending before the boundary's start time.

**What is not recorded.** No audit field records the trim (content-free; it is an edit within an open session). The threat model names this.

**Rejected alternatives:**
- automatic truncation at Complete (silently deletes on a false boundary, and breaks the note's digest);
- trimming only the archive copy (digest mismatch at `session_store.py:779`/`:1550`).

### D10 — Held-out synthetic set
**What.** Invented scripts in `validation/heldout/` under the id prefix `hld-` (the loader's id rule permits it). The author is a session given only the behaviour SPEC, never the vocabulary, this plan's phrase lists or the 50 scripts. Committed and dated before Phase 1.

**Cases:**
- boundary negatives: "Morning stiffness…"; a phone call "hello … bye" then the consultation resumes; a family member or receptionist arriving; "see you next week" then "hey, that's good"; "You're welcome" after a closing followed by dictation; "how are you going with…" after "take care"; a recording started as the previous patient leaves;
- boundary positives: Australian greetings; the next patient speaking first; closing and greeting in one segment;
- correction negatives: "Sorry, don't write this down"; "Wait, I need to sit down";
- hedges outside the vocabulary: "I reckon".

**Uses.** It also becomes transcript-level unit fixtures. `test_validation_scripts.py` lints the folder (loads, synthetic, voice slots); the axis-count lints stay on the run-of-record set. It is run by the practitioner as audio beside this plan's run of record, and the result is recorded, never tuned to.

### D11 — Runs, predictions and version
**Runs.** Refer by name: "the guard's run of record" (expected run 4) and "this plan's run of record" (expected run 5). Numbers are assigned when each run happens (decision 0.7).

**Predictions.** Task 0.10 writes them before Phase 1:
- `possible_next_patient` on exactly `syn-06`, `-20`, `-21`, `-38`, `-43`, `-46`, subject to 0.2's vocabulary;
- the checker tally on those six gains the tail's `high_risk_omission`;
- residues: `syn-28` under 0.4 (a); `syn-35`'s acoustic fact unless surfaced; `syn-38` and `-46` if 0.2 adds nothing; the hedged facts under 0.1 (b); hedged facts whose hedge falls in another segment;
- nothing else fails.

**Version.** 0.3.3, after 0.3.2 and before 0.4.0. If 0.4.0 lands first, a dated note re-decides; `main` is never lowered.

**Rollback.** 0.3.2's forward-tolerant reader reads this plan's two review codes. Below 0.3.2, the guard's widened "Rolling back below 0.3.2" section covers saved notes; Task 5.2 adds this plan's codes and the trimmed transcript (an ordinary, shorter document, readable everywhere) to it as one line.

### D12 — Documents
- **Threat model:**
  - rewrite NEXT-PATIENT RESIDUE (`docs/security/threat-model.md:502-512`);
  - update HANDS-FREE AND WARNINGS (`:2575-2625`): the lists now also withhold content, and they changed;
  - cross-reference Chrome residue (5) (`:2734`);
  - new residues: a false boundary withholds content behind a sticky warning; a boundary inside one segment; a phone call; the window counts segments; a suspect closing or greeting supplies no phrase (the guard's D6, through the shared token function, D2) and fails toward inclusion; the unconsented tail is kept unless the clinician removes it; the trim leaves no audit fact; the trim removes an earlier generated note, and a trim that fails after its marker is written still keeps no audio (fail-safe toward privacy); the correction-carry residues; the hedge mark's scope and coarseness.
- **Data-flow map:** flow 7 (the request cut), flow 14 / `:552` (the live lists), the trim on the transcript flow.
- **Retention schedule:** the transcript row (the clinician may remove a next patient's lines before Complete).
- **`docs/testing/validation-harness.md`:**
  - the End-of-consultation limit;
  - Material facts (the correction carry);
  - Section placement (a third cause);
  - the `uncertainty_surfaced` definition (`:55`) and the Expected-uncertainty limit (`:105`), under 0.1 (a);
  - the amendment;
  - the held-out set;
  - the review-code list.
- **`docs/testing/kept-recordings.md`:** Checks 1–4 → 1–4 and 6, and a 0.3.3 paragraph: "Sections missing" may rise or fall; "Check reviews" rises.
- **Pilot documents:** `docs/pilot/exit-gate.md:16-17` and `docs/pilot/README.md:83-86` name the amendment under 0.1 (a).
- **Design and practice:**
  - `docs/design-system.md`: the code, the chooser label, the Transcript-tab action and its confirmation, the mark;
  - `docs/practice/clinician-review-guide.md`: the note stops at a possible next patient; how to remove the tail; the unsure mark.
- **Repository and planning records:**
  - `validation/README.md`: `heldout/`;
  - CHANGELOG 0.3.3, PLAN.md Phase 7 note, AGENTS.md (Current Status, a subsystem pointer for the boundary and phrase module);
  - dated lines on `plan-pilot.md`, `plan-note-routing-omissions.md` (its deferred item taken), `plan-cliniko-workflow-safeguards.md` D8, `plan-invented-text-guard.md` and `plan-ui-refresh.md` (D10's "no record field" is stale);
  - `docs/architecture/phase-history.md`.

## Schema / Data Changes
- **No new stored field.** Two new review warning codes are persisted in `note.enc`'s `note_warnings`; 0.3.2 and later read them, and below that the guard's rollback section applies.
- **The trim** writes a shorter `TranscriptDocument` through the existing writer, in the same schema, after removing any `generated.enc` (D9).
- **The marker** (decision 0.6 (a)) is a content-free file inside the session directory, written first in the trim and never removed once written. It dies with the directory.

## Config / Environment / Deployment Impact
- No environment variable, network, model or dependency change.
- The model pack is unchanged.
- Release: 0.3.3 is built of record by CI's `Release` workflow on the H4 commit after P.1 (attested; a `docs/release/pilot-builds.md` row). Same AppId, in-place upgrade.
- Install at a pilot-allowed point (never between consultations).

## Critical Constraints
1. **C1 — The agent never opens, reads, plays or describes any real session, kept recording, transcript, note, Past-sessions entry or learned config.** Synthetic sets and counts only.
2. **C2 — Rule v1, `validation/rules/option-a-proposed.json`, `validation/config/section_cues.json` and the 50 scripts' facts never change.** Metric amendments only as dated practitioner decisions before the run, pinned both ways; a bad number is a finding (pilot Constraint 12, clinic-smoke D9).
3. **C3 — The vocabulary (phrases, markers, hedges) is frozen in one dated commit (Task 0.8) before the held-out set is authored and before the diagnosis is read.** Any later change is a new dated decision with a repeated run.
4. **C4 — Fail toward inclusion and never silently.**
   - The boundary never deletes content; only the clinician's confirmed action trims.
   - The head-case guard holds.
   - A same-segment closing and greeting cut at the NEXT non-transparent segment, or not at all when none follows.
   - Check 6 is review severity, separately acknowledged, and role-free.
5. **C5 — One boundary function, computed from `(document, config)` by every consumer.** Agreement pinned by a test; the `_assemble_note_request` call count stays 1; indices stay absolute.
6. **C6 — No import of `voice_commands` from `note`, `note_config`, `note_fill` or `note_check`.** The phrase module is a leaf.
7. **C7 — The live warning's behaviour changes only by the vocabulary commit.** Its exact list pins move in that commit, with near-miss cases for every added word.
8. **C8 — Nothing per consultation enters a tracked file** (clinic-smoke D12). Run records are ids and counts.
9. **C9 — One `/execute-loop` at a time on `main`.** This plan's Phase 1 starts after the guard plan's hardening commit; under decision 0.7 (a) also after the guard's run of record, while under 0.7 (b) the guard's run-of-record acceptance moves to the combined run at this plan's H4 commit and Task 0.10 uses a deterministic rebuild instead (peer round 1 PR-MED-004). `main`'s version is never lowered.
10. **C10 — Practitioner-run steps run from a normal terminal with the installed app closed.** Nothing checked from an agent shell counts.
11. **C11 — `test_shadow_exits.py`'s existing counters are unchanged.** No new text widget, clipboard, drag or list outside `ui/lists.py`; no `"wave"` constant.

## Validation / Verification
**Suites.** `desktop/`: `ruff check . && mypy && pytest`, in a venv bound to the building checkout. `extension/`: `npm run qa` (version only).

**Read-only baselines** (dry-run 2026-10-12 at `8e5e571`):

| Check | Baseline | Becomes |
|---|---|---|
| `NOTE_WARNING_SEVERITY` codes | 14 | 16 after the guard, 18 after this plan under 0.1 (a) |
| `test_ui_models.py:1551` | `{"high_risk_omission"}` | gains `possible_next_patient` (and the guard's codes) |
| `test_hands_free.py:333-334` | exact list pins | move in Task 0.8 |
| Report separator `"---|" * 22` at `validation.py:1829` | 22 columns | 23 after the guard, 25 after Task 3.2 |
| `desktop/pyproject.toml` version | 0.3.1 | 0.3.3 (0.3.2 first) |

**Per-phase checks.** These are the tests named on each task.

**Acceptance:**
- the held-out audio run and this plan's run of record (P.1), read against Task 0.10's written predictions;
- the P.2 smoke on the installed 0.3.3.

## Deferred / Out of Scope
See the Planning Extraction Summary (the canonical list).
- **Deferred:** the undo tick, the transcript divider, the "corrected" pairing mark, the question-answer hop.
- **Excluded:** the threshold change, option (c), script/cue/rule edits, the `high_risk_omission` reuse, the turn carry, a larger model.

## Current State / Handoff Note
- Last completed step: `/review-plan` hardening 2026-10-12.
  - Four lenses ran.
  - The Step 3.5 gate decided: undo tick Defer, tail privacy Include in plan, divider Defer, corrected mark Defer.
  - The practitioner confirmed: clinician-initiated removal; kept audio left as decision 0.6; decisions 0.1–0.7 left open with recommendations.
- Current in-progress step: None.
- Immediate next action:
  1. The practitioner takes decisions 0.1–0.7. Decision 0.4 goes first if (b) is wanted: tell the guard session before its Task 3.1.
  2. After the guard plan's hardening commit: Task 0.8, the vocabulary commit.
  3. Task 0.9, a fresh session writes the held-out set.
  4. Under decision 0.7 (a) after the guard's run of record, under (b) straight away: Task 0.10, then `/execute-loop` from Phase 1.
- Open blockers: the guard plan (0.3.2) must land first (its hardening commit; under decision 0.7 (a) also its run of record); decisions 0.1–0.7.
- Last plan sync: 2026-10-12 (after the cross-family plan peer pass: `/peer-loop` codex `gpt-6-astra` medium, rounds 1-4, converged; Review Findings Log).

## Review History
- 2026-10-12 `/review-plan`: four parallel read-only lenses (coverage, practicality and risk, simplicity, plus the first-draft design critique), every finding checked against `8e5e571`. Plan-scoped; no code reviewed.
- 2026-10-12 `/peer-loop` (plan review, codex `gpt-6-astra` medium, read-only): round 1 — 4 build-affecting (2 HIGH, 2 MED), all applied (one HIGH partly invalid: recovery never re-transcribes a transcript-present session, now a pin).
- 2026-10-12 `/peer-loop` round 2 — 2 build-affecting (2 MED), both applied: Phase 0's decisions may precede the guard's hardening commit while 0.8 onward wait for it; the boundary shares the watcher's suspect-excluding token function.
- 2026-10-12 `/peer-loop` round 3 — 1 build-affecting MED, applied: the hedge mark is rendered through the guard's warning-to-mark mapping and prose summary.
- 2026-10-12 `/peer-loop` round 4 — 0 findings; the plan-review pass CONVERGED (4 rounds: 4 → 2 → 1 → 0 build-affecting, all applied).

## Review Findings Log
### Round 1 - 2026-10-12 - validation-pass plan, independent cross-family codex plan peer-review (round 1)

- Source: Codex plan peer-review
- Peer: codex gpt-6-astra medium, read-only sandbox
- Scope: the plan file, the guard plan's D3–D6, D9 and Phase 2, and the named code, test and document ranges (prompt `.cursor/loops/validation-pass-peer-r1-prompt.txt`)
- Recorded by: the planning session (composer-recorded round; the read-only peer printed the block, transcribed verbatim from the LAST `### Round 1` header of `.cursor/loops/validation-pass-peer-r1.log`, with dispositions added)
- Materiality: 4 build-affecting / 0 record-only / 0 invalid
- Severity: 0 CRIT / 2 HIGH / 2 MED / 0 LOW
- Round status: Closed (4 fixed)

#### Findings

**PR-HIGH-001 — Tail removal leaves an earlier generated-note copy eligible for archiving**

- Materiality: build-affecting
- Challenges: D9; Flow 1 step 4; Task 4.1.
- Evidence: `.cursor/plans/plan-validation-pass.md:361`; `desktop/src/scribe_desktop/transcription.py:1083–1092`; `desktop/src/scribe_desktop/ui/transcript.py:918–934`; `desktop/src/scribe_desktop/session_store.py:1390–1395`.
- Defect: `write_transcript` invalidates the saved note but does not invalidate the generated-note copy. If an earlier generation included the tail—for example, before upgrading from 0.3.2—Cancel review → trim → Complete can archive that earlier body alongside the shortened transcript; regeneration also has an explicitly documented best-effort cleanup failure residue.
- Concrete amendment: "Before committing a trim, invalidate the previous generated-note copy fail-closed under session custody. If invalidation fails, refuse the trim. Add coverage for an earlier generation containing the tail → Cancel → trim → Complete without regeneration, and trim → regeneration with a generated-body write failure; neither path may archive removed text."
- /fix decision: Applied. Verified VALID: `generated.enc` is documented as replaced only on regeneration (`session_store.py:41-45`) and copied by Complete (`:1390-1395`). D9 gains "`generated.enc` is invalidated too": the trim removes it fail-closed before the transcript write and refuses on failure; Flow 1 step 4, Schema / Data Changes, D12's residues and Task 4.1's tests reconciled. Landed + siblings reconciled.

**PR-HIGH-002 — The trim marker needs an explicit crash-safe transaction and recovery contract**

- Materiality: build-affecting
- Challenges: D9 option (a); Tasks 4.1–4.2.
- Evidence: `.cursor/plans/plan-validation-pass.md:366`, `:604`; `desktop/src/scribe_desktop/transcription.py:1061–1081`, `:1091`; `desktop/src/scribe_desktop/session.py:1178–1197`; `desktop/src/scribe_desktop/ui/transcript.py:805–838`.
- Defect: Writing the marker "in the same step" does not establish ordering between two separate files: committing the shortened transcript before a failed marker write can leave recovered Complete permitted to archive the full audio. The plan also leaves unspecified how recovery treats the retained original audio, although the transcript writer explicitly supports overwriting transcripts during resumed processing.
- Concrete amendment: "Perform trimming through controller-owned custody, rechecking session identity, review state and recovery state at execution. Durably commit the no-audio marker before changing the transcript; refuse on marker-write or inspection errors and retain the marker if a later operation fails. Define the shortened transcript as authoritative across restart: recovery must not restore its removed tail from original audio. Add failure injection around each durable write and live/recovered Complete, plus a trim → restart → recovery/retry test; unreadable trimmed state must fail closed."
- /fix decision: Applied, VALID in part. The ordering and custody gap is real: D9 now names ONE `SessionController` operation under the session lock with re-checks, and the order marker → `generated.enc` removal → `write_transcript`, each durable, the marker never removed (fail-safe = no audio kept); Complete treats an undeterminable marker as present (Task 4.2). The recovery-restores-the-tail path is NOT reachable in today's code: recovery never re-transcribes a session that has a transcript (`ui/recovery.py:6-9`, `:207`); that becomes a pin (trim → restart → recovery reads the trimmed transcript, no re-transcription) rather than new logic. Tasks 4.1–4.2 gain the failure-injection and live/recovered Complete tests. Landed + siblings reconciled (Schema / Data Changes, D12 residues).

**PR-MED-003 — Same-segment boundaries contradict Check 6's coordinate assumption**

- Materiality: build-affecting
- Challenges: D2, D5; Tasks 1.1, 1.3 and 4.1.
- Evidence: `.cursor/plans/plan-validation-pass.md:240–247`, `:301`, `:601`; `desktop/src/scribe_desktop/note_check.py:442–447`.
- Defect: D2 moves a same-segment closing/greeting boundary to the next segment, while D5 assumes the returned segment necessarily contains a greeting and therefore valid words. That next segment can be empty or absent; after trimming, the triggering closing/greeting segment remains last, exposing the same undefined end-of-document case.
- Concrete amendment: "Define the returned boundary as the first actual non-transparent segment to withhold. For a same-segment closing/greeting, use the next non-transparent segment, returning None if none exists. Check 6 points to that withheld segment without assuming it contains the greeting. Pin same-segment pairs followed by empty segments, pairs at end of document, and trim → recompute → Generate with no Check 6."
- /fix decision: Applied. D2's edge cases now define the return as the first segment to withhold, always non-transparent, with None when no non-transparent segment follows a same-segment pair; D5's coords rationale rewritten; the C4 restatement, Task 1.1's shapes and Task 4.1's tests reconciled. Landed + siblings reconciled.

**PR-MED-004 — The combined-run option cannot follow the stated execution prerequisites**

- Materiality: build-affecting
- Challenges: Decision 0.7(b), C9, Task 0.10 and handoff sequencing.
- Evidence: `.cursor/plans/plan-validation-pass.md:450`, `:488`, `:532–547`.
- Defect: Decision 0.7(b) offers one combined run at this plan's H4 commit, but C9 requires the guard's run of record before this plan starts. Task 0.10 also requires that prior run's set or report figures, so the offered alternative has no executable prerequisite path.
- Concrete amendment: "Make C9 and Task 0.10 conditional on decision 0.7. Under (a), retain the separate guard-run prerequisite. Under (b), require the guard hardening commit and a separately recorded diagnostic baseline before Phase 1, explicitly define its comparison inputs, and defer both plans' run-of-record acceptances to the combined H4 run."
- /fix decision: Applied. C9, Task 0.7 (what each option requires; the guard session must agree under (b)), Task 0.10's input and the handoff's next action and open blockers are now conditional on 0.7. Landed + siblings reconciled.

Coverage: PR-HIGH-001.
Practicality / feasibility / sequencing: PR-HIGH-002, PR-MED-003, PR-MED-004.
Unstated assumptions: PR-HIGH-001, PR-MED-003.
Simpler / safer alternatives: no finding verified.
Missing verification / rollback / migration: PR-HIGH-002, PR-MED-003, PR-MED-004.

### Round 2 - 2026-10-12 - validation-pass plan, independent cross-family codex plan peer-review (round 2)
- Source: Codex plan peer-review
- Peer: codex gpt-6-astra medium, read-only sandbox
- Scope: the plan file at `f539fae`, the round 1 block as fix notes, and the named code and test ranges (prompt `.cursor/loops/validation-pass-peer-r2-prompt.txt`)
- Recorded by: the planning session (composer-recorded round; transcribed verbatim from the LAST `### Round 2` header of `.cursor/loops/validation-pass-peer-r2.log`, with dispositions added)
- Materiality: 2 build-affecting / 0 record-only / 0 invalid
- Severity: 0 CRIT / 0 HIGH / 2 MED / 0 LOW
- Round status: Closed (2 fixed)

#### Findings

**PR-MED-005 — The blanket phase prerequisite still blocks the early primer option**

- Severity: MED
- Materiality: build-affecting
- Challenges: Tasks preamble; decision 0.4(b); handoff sequencing.
- Evidence: `.cursor/plans/plan-validation-pass.md:564`, `:585–588`, `:353–357`, `:496–500`.
- Class: Re-raises round 1’s **option without an executable prerequisite path** class.
- Defect: The Tasks preamble says **no phase** starts before the guard’s hardening commit, which includes Phase 0. Decision 0.4(b), however, must amend the guard’s Task 1.1 before its Task 3.1 measurement; the handoff correctly puts that decision first, leaving contradictory execution instructions.
- Concrete amendment: “Phase 0 decisions may precede the guard’s hardening commit. If 0.4(b) is selected, coordinate the guard Task 1.1 amendment before its Task 3.1 measurement. Phase 1 retains C9’s prerequisites, and Task 0.10 retains its decision-0.7-dependent inputs.” Replace the blanket sentence and reconcile its restatements.
- Verification: Trace the documented 0.4(b) path through decision → guard primer amendment → measurement → hardening → diagnosis → Phase 1, with no circular prerequisite.
- /fix decision: Applied. Verified VALID: the Tasks preamble blocked every phase, Phase 0 included, while 0.4 (b) must precede the guard's Task 3.1. The preamble now lets decisions 0.1–0.7 be taken at any time (0.4 (b) before the guard's Task 3.1) and holds every task that commits to `main` — 0.8 onward — until the guard's hardening commit (the guard's Task 2.4 edits `voice_commands._tokens`, which 0.8 moves; C9); the handoff's next-action list follows. Traced: decision 0.4 (b) → guard Task 1.1 → guard Task 3.1 → guard hardening → 0.8 → 0.9 → 0.10 → Phase 1, no cycle. Landed + siblings reconciled.

**PR-MED-006 — Suspect phrase exclusion is claimed but absent from the boundary’s operational contract**

- Severity: MED
- Materiality: build-affecting
- Challenges: D1–D2; D12; Task 1.1.
- Evidence: `.cursor/plans/plan-validation-pass.md:225–250`, `:416`, `:627–629`; `.cursor/plans/plan-invented-text-guard.md:124`, `:198`; `desktop/src/scribe_desktop/voice_commands.py:121–129`, `:210–217`.
- Class: Re-raises round 1’s **contradictory assumptions between decisions** class.
- Defect: D12 claims a suspect greeting is skipped, but D2’s rule and Task 1.1 never require suspect-word exclusion. The guard’s exclusion belongs to the live watcher’s `_tokens` path; sharing phrase-event detection does not establish that the new document-based boundary uses that filtered evidence, so a literal D2 implementation can withhold real content after a suspect closing or greeting.
- Concrete amendment: “For boundary detection, closing and greeting matches must contain only non-suspect words; a suspect word breaks a phrase match. This restriction does not make suspect segments transparent or change the head-case cue rule. Preserve the live watcher’s existing semantics under C7.” Add this to D2 and Task 1.1, with tests for suspect closing, suspect greeting, a phrase interrupted by a suspect word, and the corresponding non-suspect positive cases.
- Verification: Pin that suspect phrase evidence cannot create a boundary or Check 6, and include these fixtures in the request-cut, proposal-limit and Check 6 agreement test.
- /fix decision: Applied. Verified VALID: D2 never named its token source, while the guard's D6 excludes suspect words only in `voice_commands._tokens` (`:121-129`). Fixed by ONE token function rather than a second rule: the boundary reads phrase tokens through the watcher's `_tokens` as the guard builds it, moved into the leaf module (D1, D2's new "Suspect words" paragraph), so the live warning and the boundary cannot disagree (C7 unchanged); suspect segments stay non-transparent and the head-case cue rule is unchanged; the straddle case is named as a residue. Task 1.1 gains suspect closing/greeting tests with non-suspect twins, Task 1.2's agreement test includes them, D12's residue line and the 0.3.2 rebase list reconciled. Landed + siblings reconciled.

Coverage: PR-MED-006.  
Practicality / feasibility / sequencing: PR-MED-005.  
Unstated assumptions: PR-MED-006.  
Simpler / safer alternatives: no finding verified.  
Missing verification / rollback / migration: PR-MED-005, PR-MED-006.

### Round 3 - 2026-10-12 - validation-pass plan, independent cross-family codex plan peer-review (round 3)
- Source: Codex plan peer-review
- Peer: codex gpt-6-astra medium, read-only sandbox
- Scope: the plan file at `ac71682`, the round 1-2 blocks as fix notes, and the named code and test ranges (prompt `.cursor/loops/validation-pass-peer-r3-prompt.txt`)
- Recorded by: the planning session (composer-recorded round; transcribed verbatim from the LAST `### Round 3` header of `.cursor/loops/validation-pass-peer-r3.log`, with dispositions added)
- Materiality: 1 build-affecting / 0 record-only / 0 invalid
- Severity: 0 CRIT / 0 HIGH / 1 MED / 0 LOW
- Round status: Closed (1 fixed)

#### Findings

**PR-MED-007 — The hedge mark needs the persisted-warning rendering path extended**

- Severity: MED
- Materiality: build-affecting
- Challenges: D7; Task 3.1; inherited guard D5 and Task 2.6.
- Evidence: `.cursor/plans/plan-validation-pass.md:328–331`, `:700–702`; `.cursor/plans/plan-invented-text-guard.md:123`, `:200`.
- Defect: The guard’s `line_marks_by_assertion(note)` maps its two warning codes separately from the word-based `line_marks` helper, and its prose section summary enumerates those marks. Task 3.1 extends the word helper, checker and editor but never extends that warning-to-mark mapping or specifies the prose summary for `hedged_source`; its named Clean/verbatim tests cover only part of this inherited rendering contract.
- Concrete amendment: “Extend `line_marks_by_assertion` with `hedged_source` → `unsure`, and extend `section_marks_line` to include the unsure-line count. Use that canonical mapping for freshly generated and reloaded notes. Pin Clean, verbatim and prose display, including a line carrying multiple marks; Copy and Cliniko Write continue omitting check marks.”
- Verification: A note carrying persisted `hedged_source` renders the unsure mark after reload in Clean and verbatim styles and includes it in the prose section summary; the editor agrees, and exported note text omits the mark.
- /fix decision: Applied. Verified VALID against the guard plan's D5 and Task 2.6: rendered marks come from `line_marks_by_assertion(note)` (warnings), not from the word helper, and `section_marks_line` enumerates the guard's codes. D7 now extends both for `hedged_source` → "unsure", and states Copy and the Cliniko Write stay bare; Task 3.1 names the two extensions and adds fresh-versus-reloaded display in Clean, verbatim and prose, a line with both `number` and `unsure`, Copy and the Write body. Landed + siblings reconciled (Flow 3 and P.2 step 3 already name the mark as displayed).

Coverage: PR-MED-007.  
Practicality / feasibility / sequencing: no finding verified.  
Unstated assumptions: PR-MED-007.  
Simpler / safer alternatives: no finding verified.  
Missing verification / rollback / migration: PR-MED-007.

### Round 4 - 2026-10-12 - validation-pass plan, independent cross-family codex plan peer-review (round 4)
- Source: Codex plan peer-review
- Peer: codex gpt-6-astra medium, read-only sandbox
- Scope: the plan file at `a9a043b`, the round 1-3 blocks as fix notes, and the named code and test ranges (prompt `.cursor/loops/validation-pass-peer-r4-prompt.txt`)
- Recorded by: the planning session (composer-recorded round; transcribed verbatim from the LAST `### Round 4` header of `.cursor/loops/validation-pass-peer-r4.log`)
- Materiality: 0 build-affecting / 0 record-only / 0 invalid
- Severity: 0 CRIT / 0 HIGH / 0 MED / 0 LOW
- Round status: Closed (converged: a round >= 2 with zero new build-affecting findings)

#### Findings

No new findings this round.

Coverage: no finding verified.  
Practicality / feasibility / sequencing: no finding verified.  
Unstated assumptions: no finding verified.  
Simpler / safer alternatives: no finding verified.  
Missing verification / rollback / migration: no finding verified.

## Tasks
Phased for `/execute-loop` (one phase = one review boundary). The practitioner's steps carry "(practitioner)". The decisions 0.1–0.7 need no code and may be taken at any time (0.4 (b) MUST be, before the guard's Task 3.1, because it lands in the guard's Task 1.1). Every task that commits to `main` — 0.8 onward — waits for the guard plan's hardening commit (C9: one writer on `main`; the guard's Task 2.4 edits `voice_commands._tokens`, which 0.8 moves). Phase 1 additionally waits on C9's decision-0.7 prerequisites, and Task 0.10's input follows decision 0.7 (peer round 2 PR-MED-005).

### Phase 0 — Decisions, vocabulary, held-out set, diagnosis
- [ ] 🟥 **0.1 Uncertainty** `[decision]`
  - Options:
    - (a) the `hedged_source` mark plus the third metric amendment (D7);
    - (b) record the 9 hedged facts as a ratified residue (F-013, F-033, F-047, F-051, F-057 and the hedged part of F-038 stay `controlled`).
  - Excluded: the threshold change and option (c).
  - Recommended: (a). It surfaces spoken uncertainty for review, which PLAN.md asks for ("presenting uncertain potentially clinical content for review"). The override of interpretation 7 is stated openly.
  - Decide after: nothing. Blocks: Phase 3; Task 0.8's hedge list.
  - Record: `Chosen: … (date); rationale: …`, plus the single-cluster rule (recommended: no mark).
- [ ] 🟥 **0.2 Next-patient vocabulary** `[decision]`
  - Options: (a) the existing D8 lists only; (b) add the practitioner's OWN greetings and closings (their words, as with the cue file).
  - Recommended: (b), with the D2 first-position rule for single words, and without bare time-of-day words, "welcome" or "how are you going".
  - Record the overfit honestly: `syn-38` and `-46` depend on it, and the held-out set tests the mechanism.
  - The live new-consultation warning gains the same words (C7).
  - Blocks: Task 0.8.
- [ ] 🟥 **0.3 Self-correction carry** `[decision]`
  - Options: (a) D4's marker carry with the markers "actually", "i mean", "i meant", "correction", optionally after "well"; (b) accept `syn-48` as the named residue (F-055 stays controlled).
  - Recommended: (a).
  - Blocks: Phase 2; Task 0.8's marker list.
- [ ] 🟥 **0.4 `syn-28`** `[decision]`
  - Options: D8's (a) and (b).
  - Recommended: (a).
  - (b) must be decided and sent to the guard session BEFORE that plan's Task 3.1 (it lands in guard Task 1.1).
  - Record also: F-071 and F-072 stay `controlled` under (a).
- [ ] 🟥 **0.5 Check 4 over the withheld tail** `[decision]`
  - Options: D6's (a) unchanged plus chooser labels; (b) exclude the tail.
  - Recommended: (a).
- [ ] 🟥 **0.6 The kept recording after a trim** `[decision]`
  - Options: D9's (a) no audio kept (content-free marker); (b) trim `audio.enc` to the chunks before the boundary.
  - Recommended: (a). Development consent was given for the first patient only, and (a) adds no encrypted-store code.
  - Blocks: Task 4.2.
- [ ] 🟥 **0.7 Runs** `[decision]`
  - Options: (a) the guard's run of record, then this plan's; (b) one combined run at this plan's H4 commit, read against both acceptances.
  - Recommended: (a). Each plan keeps its own acceptance, and Task 0.10 reads the 0.3.2 code's output.
  - What each option requires (peer round 1 PR-MED-004): under (a), Phase 1 waits for the guard's run of record and Task 0.10 reads its set folder; under (b), Phase 1 waits only for the guard's hardening commit, Task 0.10's baseline is a deterministic rebuild at that commit (no run-of-record figures exist to check it against, so its own Segments and WER are recorded on Task 0.10 as the baseline), and BOTH plans' run-of-record acceptances are read on the one combined run at this plan's H4 commit (the guard's P-phase acceptance then waits for it, which that session must agree to).
  - Blocks: Task 0.10's input; Phase 1's start (C9).
- [ ] 🟥 **0.8 Vocabulary commit (C3)**
  - Files: `consultation_phrases.py` lists and constants (D1, D2), `note.py` correction markers (D4), `note_check.HEDGE_PHRASES` (D7; an outside lexicon named in the commit message where used).
  - Also: the moved `test_hands_free.py:331-363` exact pins, and near-miss tests for every added word ("Morning stiffness", "hi-fi", "You're welcome", "how are you going with…").
  - Dated commit, with a contamination note (A3).
  - Done when: green.
- [ ] 🟥 **0.9 Held-out set (D10)**
  - A fresh session started with only the behaviour spec (D2's and D4's behaviours stated in words, never their vocabulary) writes `validation/heldout/hld-*.json`, plus transcript-level fixtures in `desktop/tests/fixtures/heldout_transcripts.py` (or the matrix's shape).
  - `test_validation_scripts.py` gains the folder lint (load, synthetic, voice slots; axis-count lints stay on `validation/scripts`).
  - `validation/README.md` gains the `heldout/` entry.
  - Done when: committed with a date, before Phase 1.
- [ ] 🟥 **0.10 Diagnosis and predictions** (composer, synthetic only; the practitioner runs it if the agent shell cannot see the developer models — `docs/lessons.md`)
  - Input, by decision 0.7:
    - (a): the guard run of record's set folder (kept by agreement with the guard session); or rebuild it deterministically at the guard's hardening commit (`scripts\build-validation-set.py`, `encounter_seed`, `validation_set.py:264-275`), checking that Segments and WER equal the guard run's report;
    - (b): the deterministic rebuild at the guard's hardening commit, with its Segments and WER recorded here as the diagnostic baseline (there is no earlier run to compare against).
  - Method: re-transcribe through `evaluate_encounter`'s steps from a scratchpad script, at the guard's hardening commit, with Task 0.8's vocabulary applied text-level.
  - Record (ids and counts only, on this task):
    - per next-patient encounter: the closing and greeting segments, whether D2 fires, and first against last;
    - every closing→greeting pair across the 50, and how many pass the head-case guard;
    - `syn-48`: whether the correction is its own segment and opens with a marker;
    - per `expect_uncertain` fact: whether a hedge is in the SAME segment, whether that segment's speaker is the resolved clinician (`syn-30`'s run-2 inversion), and which fact was already surfaced;
    - `syn-28`: whether the medication word was deleted or substituted.
  - Then write D11's predictions here.
  - Done when: recorded, and the practitioner has deleted the folder. A failed premise pauses for the practitioner.

### Phase 1 — The next-patient boundary (`consultation_phrases.py`, `voice_commands.py`, `note.py`, `note_config.py`, `note_fill.py`, `note_check.py`, `ui/models.py`)
- [ ] 🟥 **1.1 The leaf module and the rule (D1, D2, C5, C6)**
  - Build `consultation_boundary`, with `voice_commands` re-exporting the lists and the watcher using the shared phrase-event helper (its live pins `test_hands_free.py:374-400` unchanged).
  - Tests: the D2 shapes (head case; same segment; same segment followed only by empty segments, and at the end of the document — None; closing without greeting; greeting without closing; phone call; transparency; first-position rule; a suspect closing, a suspect greeting and their non-suspect twins — the suspect ones give no boundary and no Check 6), the held-out transcript fixtures, an import-cycle test (importing `note_config` does not import `voice_commands`).
  - Done when: green.
- [ ] 🟥 **1.2 The request cut and the proposals (D3)**
  - `build_note_request` passes `boundary=` to `_assemble_note_request`; the `note_fill` public entry points limit `_first_phrase_match`.
  - Tests: absolute coords resolve through `words_for_coords` and `_words_for_coords`; proposals ignore a trigger after the boundary; Check 3 stays whole; the AST guard (`test_note_config.py:535-539`) green; one test that the request cut, `note_fill` and Check 6 agree on the boundary for the held-out fixtures and the suspect-phrase fixtures (D2).
  - Done when: green.
- [ ] 🟥 **1.3 Check 6 and its copy (D5)**
  - `NOTE_WARNING_SEVERITY` and `WARNING_COPY` in one commit; `check_note` appends; the code joins `SEPARATELY_ACKNOWLEDGED_CODES` (`test_ui_models.py:1551` moves).
  - Tests: once per note; with no confirmed clinician; Acknowledge all leaves it and the per-code click clears it; `complete_block_reason` names it; `test_ui_screens.py:4470` parity.
  - Done when: green.
- [ ] 🟥 **1.4 Chooser labels (D6 (a); skip if 0.5 = (b), then add the Check 4 exclusion with its dated harness line instead)**
  - `eligible_utterances` labels rows at or after the boundary " — after possible next patient", in the documented order with the routing plan's `[flagged]` front mark and the guard's suffixes.
  - Tests: label order; `startswith` pins (`test_ui_models.py:1318-1321`, `test_ui_screens.py:5515`) hold.
  - Done when: green.
- [ ] 🟥 **1.5 Fixture lint (M-6)**
  - `test_note_matrix.py` runs `consultation_boundary` over every `EXTRACTIVE_CELLS` document and the UI turn fixtures (`_EDIT_TURNS` and siblings), asserting None except in declared boundary cells; add one declared cell per failure mode (positive, head case, same segment).
  - Done when: green, with no current cell moved.

### Phase 2 — Self-correction carry (`note.py`; skip if 0.3 = (b))
- [ ] 🟥 **2.1 `opens_with_correction` and the carry disjunct (D4)**
  - Tests in `TestBoundedCarry` (`test_note.py:2354`): the `syn-48` shape; the other speaker; an owned section; a second hop; "well, actually"; "Yes actually…" not carried; the fenced residue pinned; held-out negatives.
  - The matrix carry lint (`test_note_matrix.py:694-721`) declares a correction cell, and its opener check is extended.
  - Docstring updated.
  - Done when: green.

### Phase 3 — Hedge mark and the amendment (skip if 0.1 = (b))
- [ ] 🟥 **3.1 App (D7)**
  - `line_marks(words, *, clinician)` with "unsure"; Check 1 emits `hedged_source`; `WARNING_COPY` row; `EditableLine.marks` passes the role; `line_marks_by_assertion` maps `hedged_source` → "unsure" and `section_marks_line` counts unsure lines (the guard's D5 and Task 2.6, as built).
  - Tests: per line; a clinician line is not marked; a single cluster is not marked; an invalid line draws none; the editor agrees with Check 1; Clean, verbatim and prose display of a fresh note AND of the same note reloaded from `note.enc`, including a line carrying both `number` and `unsure`; Copy (no `[check:`) and the Cliniko Write body without the mark; `test_note_matrix.py` multisets where a patient line hedges (e.g. `:1402`); `test_ui_screens.py:4470` parity.
  - Done when: green.
- [ ] 🟥 **3.2 Harness amendment (D7, C2)** — its own commit, dated before the run of record
  - `_WordInfo.hedged`, the walk flag, `_judge`'s credit rule, the two columns (`render_report` header, separator, unmeasured row, totals).
  - `test_validation_harness.py:1109-1165` shape pins and the D7 pins in `test_validation_metrics.py`.
  - `validation-harness.md`: the amendment, the definition at `:55`, the limit at `:105`, the review-code list.
  - Done when: green.

### Phase 4 — Removing the tail from the recording (`ui/transcript.py`, `ui/models.py`, `transcription.py` caller, `session.py` / `session_store.py` under 0.6)
- [ ] 🟥 **4.1 The Transcript-tab line and action (D9)**
  - The line "A possible next patient starts at line N" and "Remove lines N–end from this recording…" behind a confirmation. Enabled only with no open review and no saved note; refusal copy otherwise.
  - Trims through ONE `SessionController` operation under the session lock (D9's custody and order: re-check session id, no lease, no saved note, not in recovery; then marker (0.6 (a)), `generated.enc` removal, `write_transcript` — stale `note.enc` unlinked first).
  - The view, chooser and prefill drop-down refresh.
  - Tests (screen-level fakes): shown only when the rule fires; the confirmation's cancel changes nothing; trim then Generate gives no Check 6 and a note whose digest matches; refused during review and after Save; refused when the session changed between confirmation and execution; a shadow session behaves the same.
  - Tests (controller and store, peer round 1 PR-HIGH-001 / PR-HIGH-002 / PR-MED-003): an earlier generation that quoted the tail → Cancel review → trim → Complete with no regeneration archives no removed text (no generated note in the entry); trim → regeneration with a `generated.enc` write failure archives no removed text; failure injected at each step (marker write, marker read-back, `generated.enc` removal, transcript write) leaves the documented state (refused before the marker: nothing changed; after it: marker kept, old transcript); a same-segment pair followed only by empty segments and a pair at the end of the document give no boundary and no action; trim → recompute → Generate gives no Check 6.
  - Done when: green, with `test_shadow_exits.py` unchanged (C11).
- [ ] 🟥 **4.2 The kept recording (decision 0.6)**
  - Under (a): the content-free marker written FIRST in the trim and never removed; `_complete_locked`'s `kept` is False when it is present, and when its presence cannot be determined (fail closed; every Complete path, `test_shadow_exits.py` `_CONSENT_KEYWORD` pins unchanged); the audit shows "not kept"; tests on the live and recovered Complete paths, including a marker written but a later trim step failed.
  - Under (b): the chunk-level trim as the trim's first committed step, with its own verification and failure rule (a failure refuses the trim, or falls back to (a)'s marker).
  - Both: trim → restart → recovery reads the trimmed transcript and offers no re-transcription (`ui/recovery.py:6-9`, `:207`).
  - Done when: green.

### Phase 5 — Documents and version
- [ ] 🟥 **5.1 Documents (D12)**
  - Done when: `test_pilot_docs.py` green; the sweep over `docs/` for "new-patient detection", "no new-patient", "next patient" and "carry" is reconciled and recorded on this task.
- [ ] 🟥 **5.2 Version 0.3.3 and the rollback line (D11)**
  - `npm version 0.3.3 --no-git-tag-version` in `extension/`; then `extension/src/manifest.ts:29`, `desktop/pyproject.toml` and `desktop/src/scribe_desktop/__init__.py` by hand, only while `main` is below 0.3.3.
  - One line in `docs/release/pilot-builds.md`'s rollback section.
  - Done when: `test_install_layout.py:867-882` green; `npm run qa`.

### Hardening stage
- [ ] 🟥 **H1** `/review-loop` to convergence.
- [ ] 🟥 **H2** `/simplify`: log findings; trivial → `/fix`, substantial → scoped `/review-plan`.
- [ ] 🟥 **H3** `/security-review`: same routing. The trim action, the marker and the boundary's privacy effect are in scope.
- [ ] 🟥 **H4** Final cross-family `/peer-review` (codex `gpt-6-astra` medium).
- [ ] 🟥 **H5** 0.3.3 built of record after P.1 on the H4 commit: the `Release` workflow, `gh attestation verify`, the `docs/release/pilot-builds.md` row, CI green. If P.1 forces a code change, H1–H4 and P.1 run again before H5.

### Phase P — Practitioner (normal terminal; C1, C8, C10)
- [ ] 🟥 **P.1 The held-out run and this plan's run of record (D10, D11, C2)**
  - From a clean, committed checkout at the H4 commit: build `validation/heldout` and `validation/scripts` into empty folders outside the repository and run each with `--rule validation\rules\option-a-proposed.json`.
  - Record in `validation-harness.md` "Runs of record" and pilot Task P.3: commit, manifest hash, voices, cue and rule blobs, the amendment(s) in force, the totals, PASS/FAIL as reported, and the held-out numbers beside them.
  - Read against Task 0.10's predictions. Anything outside them is a finding for H1, never a rule edit.
  - Delete the set folders; check `%TEMP%` for `scribe-speaker-eval-*`.
  - Done when: the record is committed.
- [ ] 🟥 **P.2 Install 0.3.3 and the smoke**
  - Verify and install at a pilot-allowed point; reload the extension; restart Chrome.
  - Mock smoke (developer-style desktop recording, no patient):
    1. A closing, a greeting, then a second "patient": the Transcript tab names the line; Generate stops the note there; Check 6 is shown; Acknowledge all leaves it and the per-code click clears it; a chooser row labelled "after possible next patient" can be added back.
    2. A second mock: Remove lines…, then Generate gives a note with no Check 6.
    3. A hedged patient line shows `[check: unsure]` (if 0.1 (a)).
    4. The Status tab shows 0.3.3.
  - Done when: the counts are on this task and AGENTS.md says 0.3.3 is installed.
- [ ] 🟥 **P.3 Register**
  - Move the rows in Key Findings to `resolved` ("0.3.3 (commit <H4 short hash>)") or keep them `controlled` with control text of 200 characters or fewer, by the run's result.
  - If any residue remains, the P.5 question goes to the practitioner as a dated decision on `plan-pilot.md`.
  - Done when: `test_pilot_docs.py` green and committed.

## Retained Follow-Up Items
Not yet applicable — the plan is Active.

## Follow-Up Continuation Notes
- **First:** the open Phase 0 decisions, then the guard plan's landing.
- **Still applies:**
  - D2: role-free, first pair, head case, next-segment rule;
  - D3: one function, every consumer, absolute indices;
  - D5: review severity, separately acknowledged;
  - D9: clinician-initiated only;
  - C2, C3: nothing tuned after a run.
- **Do not rediscover:**
  - the import cycle through `voice_commands`;
  - the watcher counts windows and the boundary counts segments;
  - the Note tab cannot regenerate;
  - `check_note` recomputes from the note, document and config;
  - the prose stage never reads the transcript;
  - the archived note's digest must equal the archived transcript's;
  - `test_shadow_exits.py` counts the constant "wave".

---
*Plan saved to: .cursor/plans/plan-validation-pass.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
*Sections marked (Only if relevant) can be omitted when genuinely not applicable, but never omit decisions, constraints, verification steps, or integration knowledge that a fresh session would otherwise have to rediscover.*
