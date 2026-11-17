# Feature Implementation Plan
**Feature:** answers-follow-question (a patient's uncued reply joins the note beside the clinician's in-note question; version 0.3.7 only on a GO; validation run 10 only if gate-capable)
**Overall Progress:** `100%` (all 23 tasks this exit keeps are done; the NOT BUILT tasks are not counted. CLOSED 2026-11-17, Completed — Follow-ups Retained (leg px1): P.3 DONE, the practitioner's "Install, shadow on (Recommended)", 0.3.7 re-verified from a normal terminal and installed over 0.3.6 with shadow mode on, the install smoke PASS on all four checks; P.5 DONE, the register (F-155 dated, F-170 and F-171 added), `AGENTS.md`, `CHANGELOG.md`, `docs/release/pilot-builds.md` and `docs/architecture/phase-history.md` per `/document`; 0.8 closed. The close is uncommitted. The record before the close follows. F.3 DONE 2026-11-17 (leg fx1): 0.3.7 is a build of record at `e79be57` (CI run 44030371305 green; `Release` run 44031862110; both files attested, exit 0 from the agent shell; every hash matches; models manifest unchanged), recorded in `docs/release/pilot-builds.md`; not yet installed. Ahead: P.3 (the practitioner's install decision, the normal-terminal re-verify first), P.5, and 0.8 at the close. The F.3 record is uncommitted. The record before F.3 follows. Phase D DONE 2026-11-17 (leg dx4). D.4 is done: the approvals are recorded, and the codex document pass converged (slice A at round 22, slice B at round 24, both 0 findings). Ahead: the commit of Phase M and Phase D (the composer's, on the practitioner's recorded word; not pushed), F.3, P.3 and P.5, and 0.8 at the close. The record before D.4's close follows. D.4's codex document pass 2026-11-17: slice A round 22 converged (0 findings); slice B round 23's one LOW (PR-LOW-040) fixed in leg dx3, its confirmation round 24 owed; D.4 counts as done after it. D.4's approvals recorded 2026-11-17 (leg dx2: all three approved or accepted as drafted, the commit after the peer pass); D.4 stays open for the codex document pass. Phase D's D.1–D.3 DONE 2026-11-17 (leg dx1; review rounds 19–21 converged; documents only, uncommitted; the composer's suite gate owed). Ahead: the composer's gate, D.4 (the practitioner's approvals and the codex document pass, with the commit of Phase M and D asked there), F.3, P.3 and P.5, and 0.8 at the close. The record before Phase D follows. Phase M DONE 2026-11-17: M.1 at the hardened commit `4a0081d` reproduced Task 0.3's V4gs QT gate lines with `M1 DIFFERENCES TOTAL: 0` over the seven seen sets (agent-run, 14533 s; uncommitted plan edits). Phase 1 and V are committed as `4a0081d`. Ahead: D (D.1–D.4, with the commit of Phase M and D asked at D.4), F.3, P.3 and P.5, and 0.8 at the close. The record before Phase M follows. Phase 0: eight of nine done (0.1–0.7, committed `a00685c`); 0.8 is written at the close. 0.4b is recorded UNMEASURED, with n enrolled 2 < 3. 0.6: IMPROVEMENT, V4gs under QT, the real-speech line overridden by name, four residues accepted. 0.7 hardened the kept phases and marked the gate-capable ones NOT BUILT. Phase 1: all four tasks done 2026-11-17 (1.1–1.4), gate-green at 10933 passed, 9 skipped; the scratch pin found 0 differences; uncommitted and not yet smoked (P.3). Phase V: V.1 and H1 DONE (gate green; H1 converged at round 13); H2 DONE (round 14, no change); H3 DONE (round 15, 2 MED applied; gate green at 10935 passed, 9 skipped); H4 CONVERGED (rounds 16–18: slice A 0 findings; slice B's 2 LOW missing regression tests fixed, then 0 findings), so Step H and Phase V are DONE, gate-green at 10937 passed, 9 skipped. Phase 1 and V are still uncommitted on `a00685c`. Ahead: the one commit, now due by the practitioner's "Commit after hardening (Recommended)"; then M.1 (the seven seen sets at the hardened commit under rule v6 with `--suggestions confirm-all --prose`, run in the background overnight, compared against Task 0.3's V4gs QT lines), D (D.1–D.4), F.3, P.3 and P.5.)

## Lifecycle State
- Completed — Follow-ups Retained

## Completion Status
- Completion timestamp: 2026-11-17T20:53+11:00
- Main implementation complete: Yes — the improvement exit (Task 0.6): 0.3.7 built (Phases 1 and V), measured on the built product (M.1, 0 differences), documented (D), built of record (F.3, `e79be57`) and installed on this computer 2026-11-17 with shadow mode on (P.3, smoke PASS on all four checks). The gate-capable tasks (F.1, F.2, P.1, P.2, P.4) are NOT BUILT by that exit.
- Ready for archive: No — follow-ups retained (below)

## Plan Lineage
- Parent plan: None. It continues `.cursor/plans/plan-suggestion-repair.md` (Completed — Follow-ups Retained): its Deferred item "Answers follow their question", TRIGGERED by S.4 on 2026-11-15, and its Follow-Up Continuation Note 1. "SR" below means that plan; "NCD" means `.cursor/plans/plan-note-content-design.md`.
- Follow-up plans: None.

## Goal
Decide, on measured numbers, whether a deterministic rule can close the class that failed validation run 9 (patients' uncued replies, 23 of 24 silent omissions on the blind `heldout-6`), and build it only if it can. The rule: a patient's uncued reply to a clinician's question that is in the note joins the note beside that question; when the clinician's line is itself left out, its existing warning also covers the reply, which is shown `[flagged]` (as chosen at Task 0.6: when that line is a question). No language model. The rule is simulated at audio level and on real speech before any product code changes. Three exits: gate-capable (build, then validation run 10 on a fresh blind `heldout-7`), improvement (build, shadow mode stays on, no blind set spent), or close with no change.

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable 5.2 (the practitioner's answer 2026-11-15: "Entirely premium (Recommended)"); executor Opus-class (`claude-opus-5-5` under `/execute-loop`, codex `gpt-6-astra` peer; SR's shape); tier-gap dosing applied (design decisions D1–D13 locked, the simulation's recipe and report fixed in the tasks, the thresholds fixed before any audio-level number, per-task "Done when")

**The practitioner's decisions (2026-11-15, in chat; the quoted words are the option labels they chose):**
- Fresh evidence: "One blind set, run 10 (Recommended)" (no separate check set; the seven seen sets are read as an upper bound).
- Reply reach: "Measure variants, then decide (Recommended)".
- Real speech: "Yes, before building (Recommended)".
- Executor: "Entirely premium (Recommended)".
- Blind run: "Only if gate-capable (Recommended)".
- Thresholds: "Accept these (Recommended)" (D8).
- Small talk on a joined line: "Count every one, measure a guard (Recommended)" (D8's harm line; guard G in D2).
- Real-speech cue file: "Both (Recommended)" (Task 0.4b).
- Hardening depth: "Phase 0 in full, the rest in outline (Recommended)" (Task 0.7).
- Saved exploration notes: "Neither (Recommended)".
- Deferral gate: both candidates "Defer (Recommended)"; "Nothing more, save it (Recommended)" closed the clarification.
- The native plan was approved the same day.

### Agreed Scope (Build Now)
- Phase 0: a scratch simulation of the rule at text level, at audio level over the seven seen sets, and on the practitioner's consented kept recordings; the decision (Task 0.6).
- Only on a GO, and only after Task 0.7 re-hardens them: the answer hop and the reply flag (Phase 1), version 0.3.7 and hardening (V), the built rule measured (M), documents (D), the build of record (F.3), the install decision and close (P).
- Only on the gate-capable exit: rule v7, predictions v7, the pre-registration, the blind `heldout-7`, validation run 10 and its diagnosis (F.1, F.2, P.1–P.4).
  - NOT BUILT (2026-11-17): Task 0.6 chose the improvement exit (Task 0.7 marked F.1, F.2, P.1, P.2 and P.4).

### Deferred — Actionable Later
- **Adding a left-out question from the Line list also adds its reply.**
  - Why deferred: the practitioner's "Defer (Recommended)" (2026-11-15). It is a Note-tab behaviour change with its own design and review; D4 keeps the reply `[flagged]` after such an Add.
  - Intended future outcome: an answer follows its question into the note on a hand Add as it does at generation.
  - Relevant files / subsystems: `ui/note.py` (the Add handler, `:1545`, `:1571-1577`), `ui/models.py` `working_draft`, `validation.py` `suggestion_pass` (the harness would mirror it), `docs/design-system.md`.
  - Dependencies / prerequisites: the hop built (Phase 1).
  - Recommended next action: a small plan with `docs/design-system.md` cues.
  - Risk if deferred: ux-degradation: after a hand Add of a question its reply stays out until it is added too; it stays flagged but no warning holds the note back.
  - Revisit by: Task 0.3's count of facts credited only through a hand-added or suggested question being above 0 on a gate set, or shadow use showing replies left behind after a hand Add.
- **A mark or warning for a long reply's later lines, beyond the reach that joins.**
  - Why deferred: the practitioner's "Defer (Recommended)" (2026-11-15). It adds one review warning per joined answer, and that load on real speech is unmeasured.
  - Intended future outcome: a fact in the second or later sentence of an answer is never silently left out.
  - Relevant files / subsystems: `note_check.py` (a new review code), `ui/models.py`, `validation.py` `warned`.
  - Dependencies / prerequisites: Task 0.3's table (where the remaining silent facts sit) and Task 0.4b's counts.
  - Recommended next action: read at Task 0.6; if the remaining silent facts sit on those lines, its own plan with the warning load measured first.
  - Risk if deferred: correctness: such a fact stays silently left out, and the zero-silent-omission gate stays out of reach for that residue.
  - Revisit by: Task 0.6.
- **A single derived question-and-answer line** ("No pins and needles"). Unchanged: NCD's Deferred item (a new assertion kind spanning two speakers; not chosen 2026-11-07). This plan quotes the reply as its own verbatim line.
- **Window-edge carry and an "add all suggested lines" control.** Unchanged: SR's Deferred items; the suggestion stage is not touched here.

### Excluded — Revisit Only If Needed
- **Replies to in-note STATEMENTS.**
  - Why excluded: measured at text level: it recovers nothing and quotes one line that must stay out (`syn-05`).
  - When to revisit: only on a new measurement.
  - Relevant files / subsystems: `note.py` `generate_sections`.
- **A clinician's answer to a patient's question (inverted roles); a reply joined when no clinician is confirmed.**
  - Why excluded: the rule is the confirmed clinician's question and another speaker's reply; anything else fails toward leaving the line out.
  - When to revisit: only if real-speech attribution makes the confirmed-clinician test miss most questions (Task 0.4b's attribution line).
  - 2026-11-17: Task 0.4b's script prints no attribution line, so this trigger cannot be evaluated: neither met nor ruled out. On the two recordings every finalist joined 0, cause unknown (round 8 MED-001). The question goes to the practitioner at Task 0.6.
- **The next-patient boundary and the practitioner's own goodbyes and greetings.**
  - Why excluded: the practitioner's standing decision (SR, 2026-11-14: "Keep it out, say so before the run"). D10 pre-registers the consequence.
  - When to revisit: run 10 fails on the next-patient count alone, or the practitioner asks. It stays the validation-run8 plan's retained item.
  - Relevant files / subsystems: `consultation_phrases.py`.
- **Cue changes; a warning on every left-out patient line; the recogniser; any model; changes to `is_interrogative`'s word lists or any frozen vocabulary.**
  - Why excluded: the first two were rejected by the practitioner (2026-10-23, 2026-11-14); the rest are not this plan's subject.
  - When to revisit: only on a new dated decision with its own run.
- **`provider_name` (`extractive-v1`) is not bumped.**
  - Why excluded: it was not bumped for either carry, about 50 test literals pin it, and the audit row's `app_version` tells builds apart.
  - When to revisit: only if a consumer needs to tell routing versions apart without the app version.
  - Relevant files / subsystems: `note.py:2230`, `session_store.py:1254`, `:1287`, `audit.py:250-256`.

### Accepted Assumptions — Revalidate Later
- **The seven seen sets are an upper bound, not a check.**
  - Why accepted for now: `heldout-2` is spent and `heldout-6` is seen; the practitioner chose no separate check set. The variant is chosen on them, and `heldout-7` shares their author brief, so the choice is in-distribution.
  - Risk if assumption becomes false: a gate-capable reading at Task 0.6 fails at run 10.
  - Trigger for revisit: run 10 (the test), on the gate-capable exit only.
  - Recommended next action: none before run 10.
- **The planning cross-checks are estimates, not records.**
  - Why accepted for now: two planning agents ran in-memory text-level simulations of their own reading of the draft rule (nothing written). They reproduce the known counts (51 silent; the first line recovers 11) and add: join plus credit leaves about 6–12 silent facts on `heldout-2` and 1–4 on `heldout-6`; `h5-18` line 3 is quoted by the first-line rule; the reply flag lands on about 17 (questions only) to 39 (any clinician line) lines that must stay out.
  - Risk if assumption becomes false: the plan's expectations (not gate-capable) are wrong in either direction.
  - Trigger for revisit: Task 0.2 (the scratch's own counts replace them).
  - Recommended next action: record any difference on Task 0.2.
- **Text level stands in for nothing here.** D8 is read at audio level, in the gate configuration. Text level is the scratch's self-test only.
- **The blind-authoring templates are still on disk** (git-ignored `.cursor/loops/`: `ncd-heldout6-author-run.sh`, `ncd-heldout6-author-prompt.txt`, `ncd-heldout6-tails.py`, `ncd-brief-leak.py`, `heldout-6-brief/`; seen 2026-11-15).
  - Risk if assumption becomes false: F.2 rebuilds them from NCD's F.2 record (`plan-note-content-design.md:372-380`, `:2061-2075`).
  - Trigger for revisit: F.2's first step.
- **At least three kept recordings with the clinician enrolled exist.**
  - Why accepted for now: the practitioner keeps consented recordings (n = 2 on 2026-10-23). The agent cannot and must not look.
  - Risk if assumption becomes false: D8's real-speech line is unmeasured and no build starts without the practitioner's named override.
  - Trigger for revisit: Task 0.4b's `--list` (decrypts nothing).
  - FALSE 2026-11-17 (Task 0.4b): `--list` printed `kept recordings: 2`, and both passes measured n enrolled 2. D8's real-speech line is unmeasured, and no build starts without the practitioner's explicit, named override (D8's "Real speech" bullet).

### Key Design Decisions
See "Design Decisions" (D1–D13); each says whether it still applies to follow-up work.

## Key Findings

### Files / Symbols Involved (code-verified 2026-11-15 at `main` `50a8a2b`, tree clean)
- `desktop/src/scribe_desktop/note.py`
  - `ExtractiveNoteProvider.generate_sections` (`:2243-2305`): branch (0) a wordless utterance is transparent (`:2259-2260`); (1) cue-routed, sets the carry state `prev_key`, `prev_cued`, `prev_speaker`, `prev_clean`, `prev_open` (`:2262-2269`); (2) the same-speaker one-hop carry, comma or correction (`:2270-2286`); (3) dropped, the chain breaks (`:2287-2290`). The state is local variables: there is no hook, so a scratch subclass re-implements the whole loop.
  - `_route` (`:2232-2241`) passes `question=is_interrogative(...)`; `provider_name` `extractive-v1` (`:2230`).
  - `is_interrogative` (`:1667-1677`): a trailing `?`, or a first token in `_WH_OPENERS`, or an auxiliary followed by a subject pronoun. It is read per piece: when the recogniser splits a question at a comma, the last piece qualifies by its `?` and the first only by its opening words, so either, both or neither piece may be a question.
  - `CLINICIAN_OWNED_SECTIONS` (`:170`); `section_admits_utterance` (`:1697-1709`): a question never enters an owned section; `spoken_by_confirmed_clinician` (`:1688`); `any_cue_matches` (`:1950-1968`); `ends_mid_sentence` (`:1824-1836`); `opens_with_correction` (`:1806-1821`); `words_hold_suspect`; `joined_run` (`:1905-1947`, same speaker only); `covered_words` (`:1876-1893`); `wholly_uncovered` (`:1896`).
  - `whole_utterance_assertion` (`:1983-2009`) and `provider_assertion_id` (`x0000`, `:1971`); `manual_assertion_id` (`m0000`, `:1976-1980`) marks a line the clinician added.
  - `NoteRequest.clinician_speaker` (`:1390`); `NoteUtterance` (`:1351-1359`); the request is already cut at the next-patient boundary (`:1461-1471`).
  - `GeneratedNote` schema 2, `extra="forbid"`: a new field or provenance would need schema 3. None is added (D3).
- `desktop/src/scribe_desktop/note_check.py`: `clinician_line_omissions` (`:1681-1740`, the confirmed clinician's wholly uncovered runs before the boundary; a left-out question draws it; a patient's line never does); `omission_warnings` (`:1639-1678`); Check 1's line marks (`:654-667`: number, possibly not speech, unsure for a non-clinician); Check 2 `_structured_quoted` (`:1292-1316`), error-grade `contradiction` (`:1319-1333`) and exclusive dose (`:1456-1461`); Check 3 `role_unconfirmed` (`:1562-1599`).
- `desktop/src/scribe_desktop/ui/models.py`: `omission_anchors` (`:2732`), `flagged_runs` (`:2744-2770`), `flagged_segments` (`:2773-2784`), read only by `NoteScreen._flagged_segments` (`ui/note.py:1445-1452`), which feeds the chooser mark, the row mark and the filter with its count line (`flagged_count_line`, `:2890`; `FLAGGED_FILTER_LABEL` "Show flagged or suggested lines only", `:2877`). The warning's copy: title and hint (`:2304-2309`), short form (`:2428`), count line (`:2909-2913`). The default provider is built at `:3465-3467` (`cues=config.normalised_cues()`, `fallback_cues=DEFAULT_SECTION_CUES`).
- `desktop/src/scribe_desktop/validation.py`: `credited_segments` (`:1893-1902`, equal to `flagged_runs`), read as a module global in `encounter_metrics` (`:2077`); `word_info`'s `warned` (`:2110-2142`); the run-only counts (`:2083-2086`, `:2264-2278`); `HarnessInputs.note_provider_factory` (`:3123-3125`, `Callable[[NoteConfig], NoteModelProvider]`), called in `_compose_draft` (`:3165`) for the reference reading (`:3305`) and the transcript note (`:3379`, `:3383`); `suggestion_pass` (`:3215-3290`, adds accepted lines under `manual_assertion_id`); `facts_wrongly_present_via_suggestion` (`:1064-1068`) through `suggested_segments` (`:2182-2190`, `:2308-2319`); the report table (28 columns plus the six suggestion columns, `:3876-3887`, `:3910`); the amendment sentences and per-rule label branches (`:3784-3852`); `EncounterOutcome` (`:2748`, a frozen dataclass).
- `desktop/src/scribe_desktop/replay_kept.py` and `scripts/replay-kept-recordings.py`: the refusal order (`:576-647`), the enrolled speaker (`:400`), the default config (shipped defaults from an empty folder, `:84-87`, `:686-687`).
- Scratch precedents in the git-ignored `.cursor/loops/` (open by exact name; the folder holds about 6,800 files, so never list it): `run8-p3-transcribe.py` (keeps the enrolled document and pickles it), `run7-measure-kept.py` and `run6-measure-kept.py` (the kept-recordings shape), `run7_measure_lib.py`. `run7-predict.py` is stale apart from three pieces (Codebase Integration Notes); `run9-p5-transcribe.py` adds the prose and suggestion stages and must not be the model.

### Codebase Integration Notes
- **Nothing records that a line was carried**, in the data, the checks or the UI: a carried line is the same `transcript` assertion as a cued one. A joined answer is built the same way (D3). Lines in a section stay in transcript order, so the reply sits right after its question.
- **Downstream of a joined patient line (read, no change expected):** Check 1 marks it like any quoted line; Check 2 gains quoted evidence, so a reply that names what it negates ("No numbness.") can contradict a pre-filled or typed line at error grade (counted in Phase 0, D8), while a bare "No." carries no claim of its own — Check 2 parses each line separately, takes no evidence from a question (`note_check.py:1132-1133`) and needs the negated word in the same line (`:1212-1229`) — so a bare "No." beside its question is never checked against an authored line (a named residue); Check 3 cannot fire (a question never sits in an owned section); Check 4's `high_risk_omission` on that reply disappears once it is covered; Check 6 reads the document only; `note_fill` reads the document only; both learners in `ui/note_review.py` test `spoken_by_confirmed_clinician` first (`:311`, `:392`), so a joined patient line teaches nothing; `note_suggest` sees a joined line as placed context, not an asked line; more sections become other-voice, so the prose styles frame them "Pt" (`prose_style.py:264-266`) and `section_input_digest` changes; `replay_kept.note_drift` shows drift against 0.3.6 replays.
- **Learned-cue amplification (a named residue):** a phrase learned from a clinician's added question (`ui/note_review.py:374-470`) later cue-routes that question, and the hop then also pulls in its reply.
- **The simulation recipe (works at HEAD; the precedent scripts are partly stale):**
  - Provider: a scratch subclass of `ExtractiveNoteProvider` built as the default is (`cues=config.normalised_cues()`, `fallback_cues=DEFAULT_SECTION_CUES`), keeping `provider_name`, passed as `HarnessInputs.note_provider_factory`. It reaches the reference reading and the transcript note.
  - Credit: patch `validation.credited_segments` to return `flagged_runs(note, document) | replies`.
  - Three evaluations per encounter and variant: **A** the default provider and the shipped credit (the premise); **B** the variant and the shipped credit (join recovered = A − B); **C** the variant and the patched credit (credit recovered = B − C). Never report the run-only counts from C (they inflate).
  - Harm is a per-fact difference, never the `suggested_segments` counter (that counter reads material facts only, `validation.py:2308-2319`, and counts facts, not lines). For every `absent` fact, material or not: `correctly_absent` in the no-hop run and `wrongly_present` in the variant run of the SAME configuration is one newly quoted fact. Facts are de-duplicated into lines as distinct (encounter, `fact.line`) pairs, split material / not. In the gate configuration the difference includes anything a changed suggestion adds; that is what turning the hop on costs, and it is what D8 counts.
  - Capture each call's arguments by wrapping `validation.encounter_metrics` (the transcript call is the one with `reference=`) and re-invoke it under each credit patch, so one composed note serves every credit sub-variant. Capture notes by wrapping `validation._compose_note` (the reference call comes first).
  - Replay without audio: pickle as `run8-p3-transcribe.py:222-229` (`encounter_id`, `commit`, `whisper_model`, `clinician`, `outcome`, `document`); keep the built set folder (the script copy and `<id>.txt` are read); patch `validation.transcribe_in_temporary_store = lambda *a, **k: (doc, doc)` and `validation.read_wav_pcm = lambda _p: b""`; `HarnessInputs(provider=None, frame_probability=None, config=…, attribution="enrolment", enrolments={slot: object()}, now=<fixed>)` (the dummy enrolment is required).
  - Premise object: `replayed == data["outcome"]` (`EncounterOutcome` equality). Text mode has no shipped outcome: the no-join subclass's sections equal `ExtractiveNoteProvider`'s and `encounter_metrics` is equal, composed as `reference_reading` does (`:3304-3306`).
  - Save a plain projection per encounter and variant (per fact: verdict, warned, silent; counts; joined and credited segment indices), because pickled outcomes stop comparing by `==` once Phase 1 changes the harness.
- **Building the sets** (none of the earlier builds exists): check the voices first — `.venv/Scripts/python.exe -c "from scribe_desktop.validation_set import sapi_voices; [print(i, v) for i, v in enumerate(sapi_voices())]" < /dev/null`, baseline 0 David, 1 Hazel, 2 Zira (`docs/testing/validation-harness.md:21`, `:37-39`); then `.venv/Scripts/python.exe scripts/build-validation-set.py validation/<set> C:/afq-sets/<set> < /dev/null` for `scripts`, `heldout`, `heldout-2` … `heldout-6`.
- **Baselines on disk** (git-ignored `.cursor/loops/`): off, no prose — `stage-2-c6-off-<set>.md` for the 50, `heldout`, `heldout-3`, `-4`, `-5`, and `stage-4-f1-off-heldout-2.md`; confirm-all with prose, all at `6c1901d`, labelled rule v5 — `stage-4-f1-confirm-{scripts,heldout,heldout-3,heldout-4,heldout-5}.md` and `stage-4-f1-confirm2-heldout-2.md` (never `confirm-heldout-2.md`, the one-off transcript). `heldout-6` has only what `docs/testing/validation-harness.md` records for run 9.
- **Timings to plan around:** an off, no-prose run of six sets took about 66 min (706 / 436 / 753 / 709 / 716 / 661 s); confirm-all with prose 2298 / 1265 / 2006 / 1814 / 1550 / 1602 s for six, about 3.5–5 h for seven; model seconds per set about 270–520 (a replay over saved documents with the suggestion and prose stages on is about 8 min a set); a kept recording re-transcribes at about 0.6× real time (about 15 min per 25-minute consultation). Session speed has drifted up to 1.5×.
- **Pins a build would move** (for Task 0.7 and Phase 1; the list is from the critique's read of the suite):
  - The held-out unsure pin: `test_note_check.py` `test_the_held_out_unsure_lines[h5-17]` (`:2661-2673`) goes from `(5,)` to `(3, 5)` under the first-line rule; it is recorded as a predicted divergence in `_PREDICTED_UNSURE_DIVERGENCES_BY_SET` (`:2773-2784`), count 10 → 11 (`:2683`), never edited away. The corrections pin and all 17 `EXTRACTIVE_CELLS` do not change.
  - `flagged_segments` exact pins, which move under "any clinician line": `fixtures/joined_runs.py` `SplitCase.flagged` ("comma-split", "speaker-change"); `test_ui_models.py:1976-1997`, `:2028-2053`, `:2085-2092`; `test_ui_screens.py:5546`, `:5890`; `test_note_check.py:2114`; `test_validation_metrics.py:1353-1360`. They hold under "questions only".
  - `credited == flagged_runs` (`test_validation_metrics.py:1387-1395`) stays true only if the reply credit is a separate term (D4).
  - Copy pins: `test_ui_models.py:1522`, `:1529`, `:2100-2116`, `:2269`, `:3068`; `test_ui_screens.py:5806-5834`, `:5968`.
  - Report shape: `test_validation_harness.py:2300`, `:2345-2388`, `:2975-2997`, `:3069-3146`, `:3231`, `:3367`; the full amendment sentence `:2349-2360`, `:3080-3094`.
  - The matrix: `test_note_matrix.py:833-866` (the hop needs its own registry and "only a declared join" lint beside `test_every_carry_cell_is_registered`); `test_validation_scripts.py:894-924` ("a hedged line routes, or is a correction" gains a third arm).
  - Not touched: `test_shadow_exits.py` (its "ONE call per path" pin counts the guard's two mark functions only), `test_vocabulary.py`, `test_note_config.py`'s construction guard. No test reads the security or design documents; the harness document is pinned only by the rule ceiling tables (`test_validation_harness.py:2183-2262`).
- **`heldout-7` and rule v7 sites** (gate-capable exit; NOT BUILT 2026-11-17: the improvement exit touches none of them, and the brief's behaviour text needs no answer): NCD's F.2 list (`plan-note-content-design.md:2044-2060`) plus `test_pilot_docs.py:132`, `:341`; `scripts/lint_held_out_plugin.py:88` and `scripts/lint-held-out-set.py`'s docstring; `docs/pilot/findings-register.md`'s id rule; `test_validation_harness.py:3427-3461` (`rule-v7-test` becomes `rule-v8-test` when a `v7` label branch lands); `.github/workflows/ci.yml:65-82`; `docs/pilot/README.md`. Template edits: `ncd-brief-leak.py` (`OUT`, `RUNNER_PROMPT`, `EDITS` line 1 and h2 → h7, the `:96-113` guard; `SOURCE` stays `validation/heldout-2`), the author prompt (`h6-01.json` → `h7-01.json`), `ncd-heldout6-author-run.sh:2-9`, `ncd-heldout6-tails.py:21`, `:27`, `:57-61`. The brief's behaviour text is a Task 0.7 question (`validation/heldout-6/SPEC.md:9` tells the author an uncued line "can be left out").
- **The six version strings:** `desktop/pyproject.toml:7`, `desktop/src/scribe_desktop/__init__.py:3`, `extension/package.json:4`, `extension/package-lock.json:3` and `:9`, `extension/src/manifest.ts:29`. No desktop test pins 0.3.6.
- **Line endings:** plans and `test_pilot_docs.py` are LF; `AGENTS.md`, `CHANGELOG.md`, `docs/testing/validation-harness.md`, `docs/security/threat-model.md`, `docs/security/data-flow-map.md`, `validation.py` and several test files are CRLF in the working tree. Check `git ls-files --eol` before any byte-level edit.
- **Lessons that apply** (`docs/lessons.md`, `AGENTS.md` "Pattern worth knowing"): the agent shell reads the developer models folder but its writes under `%LOCALAPPDATA%` are virtualised; every Python call takes `< /dev/null` (a heredoc on stdin hangs); long runs in the background, mains power, lid open, the installed app closed; a scoped executor leg runs no Python and cannot read a folder outside the repository, so the composer runs the scratch and copies outputs into a git-ignored `.cursor/loops/afq-out/`; bash redirection writes UTF-8 with CRLF and PowerShell's `>` writes UTF-16; paths in record scripts are raw strings or forward slashes; a top-level `C:\` folder cannot be deleted from the agent shell; a codex pass is sliced (at most about 15 files) and documents are their own slice; a re-run reproduces counts and verdicts, not words.

### Shared helpers (used by more than one phase)
- `.cursor/loops/afq_lib.py` — the rule variants, the credit variants and the counters: Tasks 0.1–0.4b, and, imported unchanged, Task 1.4's `afq-pin.py` and Task M.1's `afq-measure-built.py`.
- The saved documents and projections under `C:\afq-sets\` — Tasks 0.2–0.3, the end-of-Phase-1 comparison, and the improvement exit's Phase M.
- `desktop/tests/fixtures/answer_hops.py` (Phase 1) — the committed fixture matrix `TestAnswerHop` reads.

### External / API Findings
N/A — no external service and no model call. The suggestion and prose stages run unchanged (`suggest-v1`, `narrative-v7`) where the gate configuration needs them.

## Planned Workflow Summary

### Flow 1 — Simulating the rule
The composer builds the seven synthetic sets, transcribes each once and saves the transcripts. A scratch copy of the note router, with the answer hop added in each measured form, composes each note; the shipped harness scores it. The tables show, per form, what is recovered, what is wrongly added, and what the reply flag lands on.

### Flow 2 — Real speech
The practitioner runs one reviewed script over their consented kept recordings, from a normal terminal with both builds closed, once per cue file. It prints whole numbers by recording ordinal: joined lines, new review marks, extra flagged lines. Only the totals are recorded.

### Flow 3 — The decision
The tables are read against thresholds fixed beforehand. The practitioner chooses gate-capable, improvement or no change, and the form of the rule.

### Flow 4 — In the app (only on a GO)
After Finish, the note holds the patient's reply right after the clinician's question it answers, as a verbatim quoted line with the usual check marks. Where the clinician's own line was left out, its warning is unchanged and the Line list shows both that line and its reply `[flagged]`. Under Task 0.6's QT credit (2026-11-17), the reply is flagged only when that left-out line is a question, and the whole reply turn is flagged.

## Design Decisions
- **D1 — The answer hop is a third way into the note, after the cue route and the same-speaker carry.** In `generate_sections`, an utterance U that no cue routes and the carry does not take joins the previous non-transparent utterance P's section when all hold:
  (a) P entered the note by a cue route, was spoken by the CONFIRMED clinician (no join when `request.clinician_speaker` is None), is a question (`is_interrogative`) and holds no suspect word;
  (b) U's speaker is not the confirmed clinician;
  (c) U holds no suspect word, is not itself a question, and carries no cue of either layer in any section (`any_cue_matches`);
  (d) the section is not clinician-owned (automatic for a question; tested anyway).
  The transition table, frozen before Task 0.1 (the scratch and, on a GO, the product implement exactly this). A window opens after P with a budget of joined lines (D2: 1, 2 or unlimited). For each next utterance U, the first matching row applies:
  1. U has no words or no text → transparent: nothing changes (the loop's existing first step).
  2. A cue routes U → emitted as today; the window closes.
  3. The window is open, its budget is not spent, U meets (b) and (c), and — from the second joined line on — U's speaker is the first joined line's speaker → U joins; the budget falls by one.
  4. The line before U was joined by row 3, U has the same speaker, that joined line ended mid-sentence (`ends_mid_sentence`) or U opens with a correction (`opens_with_correction`), and U meets (c) → U is carried. A carried piece does not use the budget, carries nothing further, and leaves the window as it was.
  5. Anything else → U follows today's branches (the existing same-speaker carry from a cue-routed line, or dropped); the window closes.
  So: "Yes." is never kept while "Actually no…" is dropped; a reply the recogniser split at a comma is not quoted as half a sentence; a reply or a continuation that is itself a question, or holds a suspect word, is never quoted by the hop and closes the window (row 4 applies (c), which the existing carry does not: `test_note.py:3119-3121` pins that the existing carry takes a question, and that stays true only for a carry from a cue-routed line). A joined answer does not set the existing carry state. `_route` stays cue-only. `is_interrogative` and every frozen vocabulary are unchanged.
  Alternatives considered: a model (SR, NO-GO); a turn-level rule whose window survives the reply speaker's own cued lines (recovers 17 at text level but quotes `hld-17`'s "don't write this down" line); two opposite state rules plus a separate comma variant (more rules, same reach).
  Still applies to follow-up work: Yes.
- **D2 — Reach and guard are measured, then chosen (Task 0.6).**
  - Reach is D1's budget: **V1** one joined line; **V3** two; **V4** unlimited (until row 2 or 5 applies; row 1 stays transparent). Carried pieces (row 4) never count.
  - Guard **G**, on or off: the window opens only when P's last sentence is itself a question and alone routes to P's section. Sentences are cut after any word whose text, with closing quotes and brackets peeled off (`_CLOSING_MARKS`, as `ends_mid_sentence` does), ends in `.`, `?` or `!`; a line with no such word is one sentence; the last sentence must pass `is_interrogative` and `layered_section` over its own tokens (same arguments as `_route`) must return P's section. No abbreviation handling: "Dr." cuts a sentence. That usually makes G refuse, but it can also leave a last fragment that opens like a question and still holds the cue ("… Tell Dr. how my left knee is sore."), which G then passes (a second named limit of G). A line that opens with a question and ends with a statement fails G only where the recogniser wrote the sentence boundary; with no sentence-ending mark between them the line is one sentence, G repeats D1's own tests and passes it (a named limit of G).
  - **V4t** (a turn-level rule: the window also survives the reply speaker's own cue-routed lines) is a text-level row only, as the scratch's self-test.
  - **S** (a question split by the recogniser: P is a cue-routed line plus its one carried piece, a question if either piece is; with G, the two pieces are read as one line) is counted first. It is simulated on the finalists if, and only if, at least one silently lost material fact on any set sits on a reply that only an S window reaches. Between otherwise equal forms, S off wins.
  Alternatives considered: fixing the first line now (leaves about 6 facts silent with no evidence on the others); fixing the whole reply (known harm).
  Still applies to follow-up work: Yes.
- **D3 — A joined line is an ordinary quoted line.** Same `transcript` assertion and `x` id as a cued or carried line; no new field, provenance or schema version; nothing at rest changes shape, so 0.3.6 reads every 0.3.7 record and rolling back needs no data step. `provider_name` is not bumped (Excluded).
  Alternatives considered: a "joined" provenance or flag (schema 3, a rollback rule, and every reader of a stored note changes).
  Still applies to follow-up work: Yes.
- **D4 — The reply flag is one helper with two readers.** `replies_after(run)` = the wholly uncovered, text-bearing lines of a speaker other than the confirmed clinician directly after the run, before the next-patient cut, limited by the chosen sub-variant (questions only or any clinician line; first line or whole turn). The harness credit = replies after `flagged_runs`' runs, added as its own term in `word_info`; `flagged_runs` and `credited_segments` are not widened. The chooser's mark = that credit, plus replies after a confirmed-clinician line that is in the note solely through the clinician's own Add (its `m` assertion), so the mark does not vanish when the question is added by hand. A reply is credited only while its clinician run still carries the warning.
  Named consequences: a reply can be `[flagged]` with no warning row behind it (Save is not held back); after a cue-routed question a refused reply is unflagged while after a hand-added one it is flagged; "credit ⊆ `[flagged]`" holds by the shared helper and a test.
  Alternatives considered: widening `flagged_runs` (breaks its exact pins and the run-only counts); folding the reply into `joined_run` (it is same-speaker by definition); one predicate for chooser and harness (it would credit a reply with no warning in the note — Task 0.3 reports how many facts only that branch would credit, and Task 0.6 may choose it); no persistence (the mark vanishes on the first Add while the harness credits it).
  Still applies to follow-up work: Yes.
- **D5 — The reply credit is a dated metric amendment and a named loosening.** `warned` also holds on a credited reply. It was decided after run 9 failed on this class, and every record says so. The report gains no column, so every unaffected row stays byte-comparable with earlier reports. The harness computes each encounter's metrics twice from the same finalised note, with and without the reply credit (no model runs again): the second, complete set — its residue classes and exemptions included, since removing a credit can change a fact's R1 standing (`validation.py:2283-2291`, `:995-1005`) — gives the rule's verdict without the reply credit, and the difference gives a report-only line (segments and material facts, in how many encounters, credited by the reply only). An aggregate second walk (the validation-run7 D1 pattern) is not enough for that verdict. Under rule v7 the report prints both verdicts. The copy changes are the count line's parenthesis and one clause of the hint; the wording is the practitioner's (Phase D).
  Alternatives considered: a `warned_v036` flag and a 29th column (a fifth flag threaded through about a dozen sites; the table's pins all move).
  Still applies to follow-up work: Yes.
- **D6 — Scratch only before the decision.** Phase 0 changes no product code and no tracked tool. The scratch lives in the git-ignored `.cursor/loops/` (`afq_lib.py`, `afq-transcribe.py`, `afq-measure.py`, `afq-measure-kept.py`); the synthetic and real-speech entry points are separate files, so no real-data path shares id-printing code. Phase 1's tests read a committed fixture matrix of plain expectations; scratch-against-product equality is a recorded one-off comparison (`afq-pin.py`), never a tracked test. A divergence is a finding against the scratch.
  Alternatives considered: a harness `--answer-hop` flag (changes shipped code before the decision); extending `scripts/measure-suggestions.py` (a tracked, model-centred tool that would have to be unwound on a no-go).
  Still applies to follow-up work: Yes.
- **D7 — Sets and configurations.** The grid runs with suggestions off and no prose over saved transcripts of the seven seen sets. The finalists then run once in the gate configuration (`--suggestions confirm-all --prose`) over the same saved transcripts, because rule v6 gates only there and a suggested clinician question removes its reply's credit. Real speech: the practitioner's kept recordings, two passes (the validation cue file, then the installed app's own). The gate set, `heldout-7`, is authored only on a gate-capable result and run once.
  Still applies to follow-up work: No.
- **D8 — The thresholds, fixed 2026-11-15 before any audio-level number.** Read on the finalists' gate-configuration run; the off run and the join-only figures are printed beside.
  - Harm, all seven sets: 0 lines the script says must stay out (`absent` facts, material or not) quoted on a joined line; no new unsupported clinical line; no new checker failure and no new error-grade warning; the 50 still pass; no set pushed over its rule-v6 next-patient ceiling.
  - Choice: among configurations with no harm, the fewest silent facts on `heldout-2` + `heldout-6`; a tie goes to the smaller reach, then to the guard on, then to S off, then to the earlier credit in this fixed order (the two credit choices are not nested, so the order is stated, not derived): questions only, first line; questions only, whole turn; any clinician line, first line; any clinician line, whole turn — each first without, then with, the chooser's wider predicate also crediting.
  - GATE-CAPABLE: 0 encounters failing on silent omission on both `heldout-2` and `heldout-6`.
  - IMPROVEMENT: not gate-capable, but silent facts at least halved on each of the two sets against the same run's no-hop baseline.
  - Real speech, each pass, over the recordings whose clinician was enrolled ONLY (the hop joins nothing without a confirmed clinician, so an unenrolled recording would add a zero; those are counted and reported apart, as `run7-measure-kept.py:412-446` does): new review marks per recording (review-severity warnings on a joined line) median ≤ 2 and maximum ≤ 5; any new error-grade warning, or a budget exceeded, comes back to the practitioner (narrow the reach, or stop). A pass counts only if it ended `COMPLETE` (every recording measured, none failed; Task 0.4a). Fewer than 3 recordings with the clinician enrolled, or a pass that did not complete, means unmeasured: no build starts without the practitioner's explicit, named override.
  - Reported for the practitioner's word at 0.6, with no threshold: lines that must stay out and are newly `[flagged]` (material / not / at or after the reference tail); joined lines and extra flagged lines per recording; that no seen script has a patient's "don't write this down" as the FIRST reply to an in-note question, so that case is clean by absence.
  - NO-GO is every remaining case: no measured configuration is free of harm (unless the practitioner, shown the table, accepts a named residue), or the best harm-free configuration is neither gate-capable nor an improvement.
  - A configuration is judged only on its own gate-configuration run: the exact reach, guard, S setting and credit (D4's sub-variant, and the chooser's wider predicate if it is to credit) that Task 0.6 would authorise.
  Still applies to follow-up work: Yes.
- **D9 — Three exits at Task 0.6.**
  - GATE-CAPABLE → Phases 1, V, M, D, F, P (rule v7, `heldout-7`, run 10).
  - IMPROVEMENT → the practitioner chooses "build as an improvement" (Phases 1, V, M as a replay, D, F.3, then the install decision; no rule v7, no `heldout-7`, no run 10; shadow mode stays on) or "close with no change".
  - NO-GO → close with no change.
  On the improvement exit: Phase M's reports are measurements, not runs of record; rule v6's verdict of record stays run 9's; the amendment is logged in the harness document as a loosening the next rule inherits; `docs/pilot/exit-gate.md` is unchanged and that is stated; the register's F-155 gets a dated control line and stays `controlled`.
  Still applies to follow-up work: No.
- **D10 — Rule v7 (gate-capable exit only; NOT APPLIED 2026-11-17: Task 0.6 chose the improvement exit).** Rule v6's predicates and ceilings with the set schedule moved (`heldout-6` a reported row counting marked R1; `heldout-7` rule v6's `heldout-6` row field for field), and the reply credit listed as that cycle's loosening with its second verdict (D5). Every set runs `--suggestions confirm-all --prose`. The pre-registration follows the `heldout-5` model (falsifiers, bands, outcomes fixed in advance) and says beforehand that run 10 may fail on the next-patient count alone: the boundary is unchanged, and where none is found the hop can quote a next patient's reply.
  Still applies to follow-up work: Yes.
- **D11 — The freeze and the blind rule (gate-capable exit; NOT APPLIED 2026-11-17: improvement exit, so no set is blind and the suite runs plain throughout).** Rule v7, predictions v7 and the pre-registration are one commit before `heldout-7` exists. From then to run 10 nothing under `desktop/src/` or `scripts/` changes beyond the named plumbing. While the set is blind the suite runs only through `scripts\lint-held-out-set.py validation\heldout-7`; the executor never opens the folder; the author session is launched by the practitioner from a normal terminal.
  Still applies to follow-up work: Yes.
- **D12 — Version 0.3.7 on either building exit; installing it is a decision on the outcome, not a default.** The models do not change, so no model pack is needed.
  Still applies to follow-up work: No.
- **D13 — The no-change exit** (Task 0.6 NO-GO or "close", and Phase M's stop). Before Phase 1 nothing needs restoring. After it, every product change is reversed to the base commit Task 0.6 records: `git diff --stat <base> -- desktop extension scripts validation config_defaults packaging protocol CHANGELOG.md` is empty, no "0.3.7" in the six version files, no untracked file under `desktop/`, the suite at its baseline. If Phase 1 or V was committed, the exit is a revert commit on the practitioner's word. The simulation's record stays in the documents (Task 0.8).
  Still applies to follow-up work: No.

## Schema / Data Changes
None. No record, audit field, stored file or schema version changes (D3). New tracked files only on a GO: `desktop/tests/fixtures/answer_hops.py`; on the gate-capable exit also `validation/rules/rule-v7.json` and `validation/heldout-7/`.

## Config / Environment / Deployment Impact
- No environment variable, dependency, model or config-file change.
- 0.3.7 (either building exit) is a new installer build from the CI `Release` workflow, attested; the existing model pack stays valid.
- Rolling back from 0.3.7 to 0.3.6 needs no data step; `docs/release/pilot-builds.md` still gets its "Rolling back below 0.3.7" section saying so.

## Critical Constraints
- **C1 — No real clinical content.** The agent never reads a kept recording, transcript, note or the installed app's data folder. `afq-measure-kept.py` is practitioner-run, requires `--enrolment`, reproduces `replay_kept`'s refusal order, re-transcribes in memory, and prints integers by recording ordinal only (no id, text or name; errors by type name). Only aggregates (n, median, maximum) enter a tracked file. The practitioner pastes the aggregate block only.
- **C2 — Phase 0 changes no product code and no tracked tool** (D6). Scratch outputs hold synthetic content only and stay in git-ignored or out-of-repository folders.
- **C3 — Frozen things stay frozen:** the phrase lists, markers, hedges and `is_interrogative`'s word lists; the cue files; every existing held-out set and fixture; rules v1–v6; the suggestion and prose stages. A predicted fixture divergence is recorded in its per-set table, never edited away.
- **C4 — A gate is a finding, never a tuning reason.** D8 is not edited after any audio-level number; predictions are written before the run they judge; a rule that has been run is never edited.
- **C5 — The reviewed real-speech script is the one that runs.** `afq-measure-kept.py` and `afq_lib.py` are frozen by SHA-256 between their review (Task 0.4a) and the practitioner's run (0.4b); a change repeats 0.4a.
- **C6 — The blind rule and the freeze** (D11), on the gate-capable exit. Not in force: Task 0.6 chose the improvement exit (2026-11-17).
- **C7 — Host and conduct.** This Windows host only, never the cloud. Commits and pushes only on the practitioner's word (autocommit off, builds on `main`). Long runs in the background with `< /dev/null`, mains power, lid open; the installed app closed while a model or transcription run is in progress; one build open at a time.
- **C8 — Line endings are kept** as each file has them; plans are LF.

## Validation / Verification
- **Baseline, dry-run 2026-11-15 at `50a8a2b`** (tree clean): in `desktop/`, `ruff check .` — "All checks passed!"; `mypy` — "Success: no issues found in 67 source files"; `pytest -q -p no:cacheprovider` — 10836 passed, 9 skipped (511 s).
- **Phase 0:** the premise (0 mismatches against the shipped harness, replay mode, all seven sets; the text-mode equality); the scratch's self-test counts; the off baseline rows equal to the named report files with the Rule column masked; each table tied to a commit, the whisper model and the built set's folder; the kept-recordings script's dry run over the synthetic pickles and its refusal smoke (no `--enrolment`: exit 2).
- **Build (on a GO):** `ruff check . && mypy && pytest` in `desktop/`, composer-run, after every code task; every changed expectation listed with its reason; the built product replayed over the saved documents equal to the scratch projection (exact, minutes, no audio).
- **Phase M:** improvement exit — the replay above in the gate configuration re-confirms D8's improvement line. Gate-capable exit — the seven sets re-run in full; a masked diff against the confirm baselines; transcript-level cells identical (Status, Segments, Ref words, WER, Spelling-normalised words, Suspect segments, the two attribution-seconds columns, the reference-boundary line); every other differing row is an encounter where the replay lists a join, a credited reply or changed suggestion cells. A seen set that differs unexplained is re-run once at the same commit.
- **Gate-capable exit** (NOT BUILT 2026-11-17, improvement exit; kept for the record): rule v7, predictions v7 and the pre-registration committed before `heldout-7` exists; the suite green through the blind runner; CI green; the release attested (`gh attestation verify`; from an agent shell read its exit code); run 10's verdicts and every column recorded against predictions v7.
- **Install smoke (either building exit):** a mock with a cued clinician question and its reply beside it in the note; a left-out clinician question with its reply `[flagged]`; nothing extra in Copy; the audit CSV's `app_version`.
- Side-effecting commands (set builds, transcription and harness runs, the kept-recordings script, the release, the author session) were inspected, not run, during planning.

## Deferred / Out of Scope
See "Deferred — Actionable Later", "Excluded — Revisit Only If Needed" and "Accepted Assumptions — Revalidate Later" in the Planning Extraction Summary (the canonical lists).

Named now, and not this plan's to decide: if even the best harm-free form is not gate-capable, the zero-silent-omission gate may be out of reach for patients' uncued lines by any rule already tried or rejected. What turns shadow mode off would then be a pilot-level decision for the practitioner (`plan-pilot.md`, the 2026-10-09 stop rule and Constraint 12).

## Current State / Handoff Note
- Loop config: executor=claude-p model="claude-opus-5-5" effort=high profile=default; peer=codex model="gpt-6-astra" effort=medium; architect=off; cadence=every-phase; caps=review:3,peer:5; gates=executor; cap-raise=executor; high-auto=on; peer-max=12; notify=action-only; scope=all; autocommit=off; isolation=none; merge=off; perms=scoped; liveness=10; monitor-delivery=auto; verify=composer
- COMPOSER RUN-STATE (2026-11-15T19:31+11:00): `/execute-loop` run `answers-follow-question-20261115-192900-2af4` (isolation none, builds on `main`, autocommit off; the practitioner's wizard answers, every one the recommended option, confirmed at the close table with the plan's own C7 overriding the preset's autocommit and worktree). Runkeys: stage-0 = Phase 0 (Tasks 0.1-0.8), stage-1 = Phase 1, stage-2 = V, stage-3 = M, stage-4 = D, stage-5 = F, stage-6 = P. Spawn helper `.cursor/loops/afq-spawn.sh`; peer runner `.cursor/loops/afq-peer-run.sh`; probe log `.cursor/loops/stage-0-probe.log`; policy log `.cursor/loops/answers-follow-question-20261115-192900-2af4-policy.log`. Now: preflight harness probe (leg ah1), then the stage-0 executor for Task 0.1.
- Last completed step:
  - The close verified 2026-11-17 (leg px2). The composer's gate over leg px1's documents (`.cursor/loops/stage-6-px1-gate.txt`): ruff "All checks passed!", mypy "Success: no issues found in 67 source files", pytest "10937 passed, 9 skipped in 471.43s (0:07:51)", every return code 0, so gate-green. Codex round 25 (pass `stage-6-p5.p1`, peer round 1 of cap 5, the close documents; escape-check clean, refs unchanged): 0 findings, Closed, CONVERGED.
  - P.5 DONE 2026-11-17 (stage-6, leg px1): the register (F-155 dated, F-170 and F-171 added), `AGENTS.md` (the paragraph closed, the full one moved to `docs/architecture/phase-history.md`), `CHANGELOG.md`, `docs/release/pilot-builds.md`, a reconciliation in `plan-suggestion-repair.md`, Task 0.8 closed, the Retained Follow-Up Items and Continuation Notes written; the lifecycle state is Completed — Follow-ups Retained. Uncommitted.
  - P.3 DONE 2026-11-17 (recorded in leg px1): "Install, shadow on (Recommended)"; the practitioner re-verified the download from a normal terminal with the composer's install script and installed 0.3.7 over 0.3.6, shadow mode on; the install smoke PASSED on all four checks.
  - F.3's record committed as `5e83b4a` (not pushed).
  - F.3 DONE 2026-11-17 (stage-5, leg fx1): the push (`bf1cb7f..e79be57`) on the practitioner's "Push and build 0.3.7 (Recommended)", CI run 44030371305 green, `Release` run 44031862110 at `e79be57`, `tree=clean`, every hash matching, both files attested (exit 0, agent shell), models manifest unchanged. 0.3.7 is a build of record in `docs/release/pilot-builds.md`, not yet installed. The F.3 record (this plan, `docs/release/pilot-builds.md`, `AGENTS.md`) is uncommitted.
  - Phases M and D committed as `e79be57` (the composer's, on the practitioner's "Commit after the peer pass (Recommended)").
  - Phase D DONE 2026-11-17 (stage-4, legs dx1–dx4). D.4 is done: the approvals and SEC-001's acceptance are recorded in the practitioner's words (dx2). The codex document pass converged: slice A at round 22 (0 findings), slice B at round 24 (0 findings) after round 23's PR-LOW-040 was fixed in dx3. The composer's gate over that fix was green (10937 passed, 9 skipped). Phase D's edits are uncommitted.
  - Phase D's D.1–D.3 DONE 2026-11-17 (stage-4, leg dx1): the 13 documents written, every claim checked against the code at `4a0081d`; `/review-loop` rounds 19–21 (5 LOW applied, converged at round 21). Documents only, uncommitted. The documents quote the DRAFT count line and hint and change with them at D.4.
  - Phase M DONE 2026-11-17 (stage-3, legs mx1–mx2). M.1's script (`.cursor/loops/afq-measure-built.py`) ran at `4a0081d` from the agent shell. The self-test on `heldout-5` came out 0 differences in 1892 s; the full run over the seven sets came out rc=0, every `SET <set> DIFFERENCES: 0`, D8 cells 0, and `M1 DIFFERENCES TOTAL: 0` in 14533 s. The product reproduces Task 0.3's V4gs QT lines, so the plan continues (the stop rule). The edits are uncommitted.
  - Phase 1 and V committed as `4a0081d` (the hardened commit), on the practitioner's "Commit after hardening (Recommended)".
  - Phase V DONE 2026-11-17 (stage-2, legs cx1–cx5), gate-green and uncommitted on `a00685c`.
    - V.1: version 0.3.7 and the CHANGELOG entry.
    - Step H: H1 converged at round 13 (2 LOW applied), H2 at round 14 (no change) and H3 at round 15 (2 MED applied: a test pin and plan records). H4 (codex) converged over rounds 16–18: slice A had 0 findings, and slice B's 2 LOW (two missing regression tests) were fixed and then confirmed.
    - No product defect was found in Step H. The product code changed only by round 13's copy hint and docstring.
    - The composer's last gate: ruff and mypy clean, pytest 10937 passed, 9 skipped (`.cursor/loops/stage-2-cx4-gate.txt`). `npm run qa` was last run at V.1: 313 tests passed, `scribe-extension@0.3.7`.
  - Phase 1 DONE 2026-11-17 (stage-1, legs bx1–bx5), gate-green and uncommitted on `a00685c`:
    - 1.1 the answer hop (V4gs);
    - 1.2 the reply flag and credit (QT);
    - 1.3 Check 2's joined-reply tests and the consumers' reading;
    - 1.4 the scratch pin, 0 differences over 384 encounters.
    - The composer's last full gate: ruff and mypy clean, pytest 10933 passed, 9 skipped (`.cursor/loops/stage-1-bx4-full.txt`). The baseline at `a00685c` was 10836 passed.
    - Its reviews are Phase V's Step H (H1–H4 over Phase 1 and V's whole diff against `22feec4`), and its live smoke is the install smoke (P.3). Neither has run yet.
  - Task 0.7 DONE (2026-11-17, leg ax11): the scoped `/review-plan` hardened the improvement exit's phases and marked the gate-capable ones NOT BUILT (Round 12). Before it, Task 0.6 DONE the same leg, when the practitioner answered "Accept all three (Recommended)".
  - Task 0.6's decision recorded, pending three residue words (2026-11-17, leg ax10). The practitioner's "yes, record QT": V4gs under QT as an improvement (0.3.7, shadow on, no run 10), with the real-speech line overridden by name and the `h5-17` residue accepted by name. Before it, codex round 11 reviewed the five open points (0 findings).
  - Task 0.5, DONE 2026-11-17 (leg ax9):
    - Codex round 10 over the records and numbers found 1 LOW (PR-LOW-006, fixed). Its jobs 1–5 found every figure, D8 reading and 0.6 option consistent with the outputs.
    - The executor's sweep settled D8's "don't write this down" first-reply check.
    - The five open points were not in round 10's slice (handoff).
  - Before it, Task 0.5's first half (2026-11-17, leg ax8): the executor's `/review-loop` over the records of Tasks 0.2–0.4b. Each figure was checked against `afq-text-2.txt`, `afq-docs-3.txt`, `afq-gate-3.txt` and the 0.4b blocks. It converged in rounds 8–9 with 0 CRIT / 0 HIGH / 1 MED / 1 LOW; no recorded number was wrong.
  - Before it, Task 0.4b, recorded UNMEASURED (2026-11-17): both passes COMPLETE, n enrolled 2 < 3, joined 0 under every form and config.
  - Before that, Task 0.3's two gate-configuration flagged columns, replaced from `afq-gate-3.txt` (2026-11-16, leg ax7). The composer's comparison found it equal to `afq-gate-2.txt` outside those columns and the timing cells. With that, Task 0.3 is DONE: its tables are recorded with the commit, the whisper model and the folder, and each D8 line is marked met or not met per finalist. Before that, leg ax6 recorded Task 0.3's gate-configuration lines from `afq-gate-2.txt` (2026-11-16): the join table, the S counter, the credit table, the replay premise (0 problems), D8 met / not met per finalist and per line, and the `h5-17` diagnosis (no scratch defect). Before that, Task 0.3's off part (2026-11-15, at `22feec4`, whisper `medium`, `C:\afq-sets\`): the builds, the transcriptions, the replay premise (0 problems), the baseline check (no table cell differs; `heldout-5`'s R1 row reads differently by rule v6's design), the join table, the S counter (holds: `h6-01:f2`), the credit table and the mechanical shortlist (finalists V4gs, V4s, V3gs), recorded on the task. Then Task 0.4a, DONE 2026-11-16 (the review converged in rounds 5–7; the composer's dry run `COMPLETE` 183 / 183, the refusal smokes and the two hashes are on the task). Task 0.2's and Task 0.3's flagged columns are replaced from `afq-text-2.txt` and `afq-docs-3.txt` (PR-MED-012). Before them: Tasks 0.1 and 0.2 (done 2026-11-15). Planning was committed in `22feec4` (not pushed).
- Current in-progress step: none: every kept task is done (stage-6's P.3 and P.5, 2026-11-17, leg px1); the composer's gate over the close is green and codex round 25 converged (leg px2). The close's edits are uncommitted on `5e83b4a`.
- Immediate next action:
  1. The close commit, by the composer on the practitioner's word (C7; not pushed). It sits on `5e83b4a` (F.3's record, already committed) and holds this close: the plan, `.cursor/plans/plan-suggestion-repair.md`, `AGENTS.md`, `CHANGELOG.md`, `docs/release/pilot-builds.md`, `docs/pilot/findings-register.md` and `docs/architecture/phase-history.md`.
  2. The run close (`/execute-loop`'s close sequence: the phase-close history gate, the flush, `/retro`, `run-close`).
  3. The practitioner's own words, outside the run: the push of `5e83b4a` and the close commit; deleting `C:\afq-sets\` (synthetic only).
  - Previous next action (done): the composer's suite gate (green) and the codex document pass (round 25, 0 findings), after P.3 and P.5.
- Executor handoff (leg px1, 2026-11-17T20:53:41+11:00; stage-6, P.3's record and P.5, documents and plan records only):
  - Recorded P.3 from the practitioner's words relayed by the composer (aggregates and outcomes only; the synthetic mock's lines by gist), and P.5 per its task text, with Task 0.8 closed, the lifecycle state Completed — Follow-ups Retained, Overall Progress 100% (23 of 23 kept tasks), and the Retained Follow-Up Items and Continuation Notes.
  - Residue rows: F-170 (`h5-17`) and F-171 (stay-out lines newly flagged), the two residues M.1 shows. Residues (2) and (3) and D.4's SEC-001 have no row, since neither M.1 nor the smoke shows them; they are Retained items. Every new cell is in `test_pilot_docs.py`'s closed vocabularies; each control is under 200 characters, unquoted, with no 7-digit run.
  - Files changed, each with its line endings kept (`git ls-files --eol` before and after): `.cursor/plans/plan-answers-follow-question.md` (LF, no NUL); `.cursor/plans/plan-suggestion-repair.md` (LF; two dated reconciliation lines); `AGENTS.md` (CRLF); `CHANGELOG.md` (CRLF); `docs/release/pilot-builds.md` (CRLF); `docs/pilot/findings-register.md` (LF); `docs/architecture/phase-history.md` (LF; the moved paragraph and a dated closing line).
  - `/document` (headless, so propose-only items are surfaced, not written): lessons, one candidate for the next interactive `/document` (a mock install smoke may need a second take when the speaker labels merge; recorded only as an AGENTS.md Last Session pattern, once, so not yet recurring). The AGENTS.md bloat guard triggers (Last Session's "Next priority" and "Worked on" stack many dated "Earlier:" entries; the file is tens of KB): a candidate to move the older entries to `docs/architecture/phase-history.md`, for the practitioner's confirmation. Findings-log compaction: this plan has no sidecar, and a loop run never creates one; a candidate for an interactive run. The consolidation offer for retained plans is likewise interactive-only.
  - `python3 scripts/loop-history-check.py --phase-close` on this plan: 24 round entries + 24 findings-log round headings, unique and strictly increasing, OK.
  - No code, test or product file changed; no commit, push or ref change; `C:\afq-sets\`, `%LOCALAPPDATA%` and `C:\scribe-release\` were not opened.
  - Owed (the composer): the suite gate (expected 10937 passed, 9 skipped), the codex document pass over this diff, then the close commit on the practitioner's word.
- Executor handoff (leg px2, 2026-11-17T21:08:58+11:00; stage-6, the close's verification records, plan records only):
  - Recorded the composer's gate over leg px1's documents (gate-green: 10937 passed, 9 skipped; ruff and mypy clean).
  - Transcribed codex round 25 verbatim from `.cursor/loops/stage-6-peer-r25.log` (opened by exact path; from its last `### Round 25` header, line 2006, to its `PEER-ROUND-25 RESULT` line, 2025; the log echoes the block twice), with a composer-recorded note (pass `stage-6-p5.p1`, peer round 1 of cap 5), and its Review History line. 0 findings, so nothing to fix.
  - Updated the last completed step, the current step and the next action: the close commit on the practitioner's word, then the run close; the push and deleting `C:\afq-sets\` stay the practitioner's.
  - `python3 scripts/loop-history-check.py --phase-close` on this plan: 25 round entries + 25 findings-log round headings, unique and strictly increasing, OK.
  - Only this plan changed in this leg (LF kept, no NUL); no commit, push or ref change.
- Executor handoff (leg fx1, 2026-11-17T17:43:50+11:00; stage-5, Task F.3's record, documents and plan records only):
  - Recorded F.3 from the composer's facts (the push, CI, the `Release` run, `BUILD-INFO.txt`, the hashes, the attestation exits and JSON), and marked F.3 and Phase F's build-of-record part done; F.1 and F.2 stay NOT BUILT. Overall Progress 87% (20 of 23). This leg did not open `C:\scribe-release\`.
  - `docs/release/pilot-builds.md` (CRLF kept): the 0.3.7 row after 0.3.6's, in its shape. "Rolling back below 0.3.7" no longer says 0.3.7 has no build of record. The sibling "Rolling back below 0.3.6" said the same of 0.3.6, which was built 2026-11-10 and installed by 2026-11-14; it is corrected too (LOW, record-only, auto-disposed Fix-now). Not changed: the table's "newest first" instruction, though every row runs oldest first (the new row follows that practice).
  - `AGENTS.md` (CRLF kept): the answers-follow-question paragraph gains an F.3 bullet, and its NEXT bullet is now P.3 then P.5. No other line names the latest build of record; the lines saying 0.3.6 is installed stay true until P.3.
  - `python3 scripts/loop-history-check.py` on this plan: 24 round entries + 24 findings-log round headings, unique and strictly increasing, OK. No code, test or product file changed; no commit or ref change; the plan stays LF.
  - For P.3. Step 1, re-verify from a normal PowerShell (not an agent shell), in the release folder:
    ```powershell
    cd C:\scribe-release\0.3.7
    gh attestation verify .\ClinikoScribe-0.3.7-setup.exe --repo eliemokbel3-hub/Recording-clinic-software --signer-workflow eliemokbel3-hub/Recording-clinic-software/.github/workflows/release.yml --source-ref refs/heads/main
    gh attestation verify .\SHA256SUMS.txt --repo eliemokbel3-hub/Recording-clinic-software --signer-workflow eliemokbel3-hub/Recording-clinic-software/.github/workflows/release.yml --source-ref refs/heads/main
    Get-FileHash .\ClinikoScribe-0.3.7-setup.exe -Algorithm SHA256
    ```
    Each `gh` line must print "Verification succeeded!". The hash must equal `6ac7747fbdea16a5e0c8c40103ba695a96ec3156e29013a421d2cb72d48136d2`, the `.exe` line of `SHA256SUMS.txt` and the table's row (ignore capitals). If any check fails, do not install.
  - Step 2, install (only on "install"): close Clinic Scribe and Chrome completely; run `ClinikoScribe-0.3.7-setup.exe` (no model pack needed: the models are unchanged); in `chrome://extensions` reload Clinic Scribe Companion from `C:\Program Files\ClinikoScribe\extension`, then fully restart Chrome; open Clinic Scribe from the Start menu. On the Status tab, check that shadow mode is still on.
  - Step 3, the install smoke, in plain words (one or two mock consultations; with a computer voice, start your own lines with "So", "And" or "Well", or a left-out line can show as a different warning):
    1. Ask a question that one of your section cues sends into the note, and have the "patient" answer without any cue word. The answer should appear in the note right beside your question, as a quoted line.
    2. Ask a question the note leaves out (no cue word). You should see the warning "A line you said is not in the note", and on the line chooser the patient's answer after it should be marked `[flagged]`.
    3. Press Copy. With shadow mode on, Copy is refused, so nothing reaches the clipboard; check that no `[flagged]` mark or extra line appears anywhere outside the line chooser.
    4. Export the audit record as CSV and check the new rows read `app_version` 0.3.7.
  - Then P.5, the records and the close.
- Executor handoff (leg dx4, 2026-11-17T17:15:57+11:00; stage-4, Phase D's close, plan records only):
  - Recorded the composer's gate on round 23 (`.cursor/loops/stage-4-dx3-gate.txt`: ruff and mypy clean over 67 source files, pytest 10937 passed, 9 skipped in 474.40s, every return code 0).
  - Transcribed round 24 verbatim from `.cursor/loops/stage-4-peer-r24.log`, from its last `### Round 24` header (the log echoes the block twice) to its `PEER-ROUND-24 RESULT` line. Added a composer-recorded note (pass `stage-4-d4b.p1`, peer round 2 of cap 5) and its Review History line.
  - Marked D.4 and Phase D done, and updated Overall Progress (83%, 19 of 23), the last completed step, the current step and the next action.
  - `loop-history-check.py --phase-close`: 24 round entries + 24 findings-log round headings, unique and strictly increasing, OK.
  - No code, test or document changed; only this plan was edited (LF kept). No commit or ref change.
- Executor handoff (leg dx3, 2026-11-17T17:04+11:00 resume; stage-4, D.4's codex pass leg 1: verification and fix):
  - Transcribed rounds 22 and 23 verbatim into the Review Findings Log (each from its log's last `### Round N` header to its `PEER-ROUND-N RESULT` line, opened by exact path), with composer-recorded notes, and added both to Review History.
  - PR-LOW-040 verified against `note.py` `generate_sections` and `replay_kept._present_sections` / `note_drift`: real (`materiality=real severity=LOW surface=documentation rec=Fix-now`). The code agrees with the finding, not with the document, so no MUST-PAUSE. A join only lands in the open window's section, and a window opens only after an emitted cue-routed line (or its carried piece, same section), so section presence and `sections_missing` are unchanged by the hop.
  - Fixed (documents only, CRLF kept): `docs/testing/kept-recordings.md`'s "From 0.3.7" first bullet, with a dated correction note. Siblings reconciled with dated correction lines in this plan: Task D.2's record and Task 1.3's `replay_kept` reading. No other Phase D document, AGENTS.md, PLAN.md or CHANGELOG.md states the expectation.
  - Item (c): `desktop/src/scribe_desktop/ui/models.py` (CRLF kept): the two comments beside `WARNING_COPY["clinician_line_omitted"]` (`:2307-2309`) and in `flagged_count_line` (`:3049-3051`) now say the wording was approved as drafted by the practitioner on 2026-11-17 (D.4). Comments only: no string or code changed (`git diff --stat -- desktop`: 1 file, 3 insertions, 4 deletions).
  - D.4 stays 🟥: round 24 (slice B confirmation) is owed; it is marked done after that round converges.
  - `loop-history-check.py`: 23 round entries and 23 findings-log headings, unique and strictly increasing, OK.
  - No Python other than the history check; no commit, stash or ref change; scratch scripts untouched.
- Executor handoff (leg dx2, 2026-11-17T16:57+11:00 resume; stage-4, D.4's approvals applied, documents and plan records only):
  - Recorded on Task D.4 the practitioner's three approvals and the commit answer, verbatim and dated 2026-11-17; D.4 stays 🟥 until the codex document pass converges.
  - Applied (each file's line endings kept; Edit-tool edits only):
    - `docs/practice/clinician-review-guide.md`: both "(draft, awaiting your approval)" markers → "(approved 2026-11-17)"; the draft-history line's "awaiting the practitioner's approval" → "approved by the practitioner on 2026-11-17".
    - `docs/practice/README.md`: "these lines await the practitioner's approval" → "these lines approved by the practitioner on 2026-11-17".
    - `docs/security/threat-model.md`: THE ANSWER HOP residue (2) "awaiting the practitioner's word at D.4, recommended accepted as a named residue" → "accepted by the practitioner 2026-11-17 as a named residue (Task D.4)" (lines re-wrapped); THE REPLY FLAG "(draft copy until the practitioner's approval at D.4)" → "(wording approved by the practitioner 2026-11-17, Task D.4)".
    - `docs/testing/validation-harness.md` ("Small talk and spoken instructions"): "awaiting the practitioner's word at its Task D.4" → "accepted by the practitioner 2026-11-17 as a named residue at its Task D.4".
    - `docs/design-system.md`: the Flagged bullet's "are DRAFT copy until the practitioner approves or rewords them" → "were approved as drafted by the practitioner on 2026-11-17"; the hint list's "draft copy until the practitioner's approval" → "approved by the practitioner on 2026-11-17"; the hint quote's "draft copy until the practitioner approves or rewords it" → "approved as drafted by the practitioner on 2026-11-17".
    - `docs/security/data-flow-map.md` flow 10: "(draft wording until the practitioner's approval)" → "(wording approved by the practitioner 2026-11-17)".
    - `AGENTS.md` Current Status: the Phase M / D bullet records D.4's approvals; the NEXT bullet is the codex pass, the commit, then F.3 on the word to push.
    - This plan: D.1's task note and its SEC-001 residue line gain dated approval lines; D.4's record; the current step and next action.
  - Grep hits for "awaiting", "draft" and "D.4", reconciled:
    - Changed: the eight document phrases above, AGENTS.md's two bullets, and the plan's D.1 note and residue line.
    - Left, historical or unrelated: `docs/architecture/phase-history.md` :55, :69, :77, :85, :120 (earlier plans' paragraphs, moved verbatim); `docs/testing/shipping-gate.md` :21 and `docs/release/pilot-builds.md` :328 ("awaiting review/recovery", not approvals); `docs/security/README.md` :24 and PLAN.md :158 (the independent review of `docs/practice/`, still owed); the review guide's other "draft" hits (Cliniko's draft note, the app's draft); CHANGELOG's hits are earlier entries (its 0.3.7 entry has no draft wording); this plan's earlier handoff bullets, Findings Log rounds and Phase 1 / V task records that say "draft until D.4" (dated records of their time, not edited).
    - NOT changed, product code (this leg's rules forbid it): two code comments in `desktop/src/scribe_desktop/ui/models.py` still call the copy "the executor's wording, a draft until D.4" (beside `WARNING_COPY["clinician_line_omitted"]` and at `:3051`, beside `flagged_count_line`). The strings themselves are the approved wording. A comment-only edit is left to the composer or a code leg (it needs the suite); recommended: make it with the Phase M and D commit, or with F.3.
  - `loop-history-check.py`: 21 round entries and 21 findings-log headings, unique and strictly increasing, OK.
  - No review round added (these replacements enact the practitioner's recorded words; the codex pass reads them). No Python other than the history check; no code, test or scratch change; no commit or ref change.
- Executor handoff (leg dx1, 2026-11-17T16:35+11:00 spawn; stage-4, Phase D's Tasks D.1–D.3, documents only):
  - Written: D.1–D.3's 13 documents (the list on each task). No product code, test, scratch script, `docs/pilot/exit-gate.md` or `docs/pilot/findings-register.md` changed; `CHANGELOG.md` read and left unchanged (still accurate). Line endings kept (`git ls-files --eol`: CRLF files still w/crlf, `docs/pilot/README.md`, `docs/architecture/phase-history.md` and this plan still w/lf; no mixed file).
  - Pins relied on: `test_validation_harness.py` `TestHarnessDocument` (it splits on `## Rule v3 `, `## Rule v5 `, `## Rule v6 ` and reads their `` | ` `` rows; those sections are untouched, and the new material is a paragraph before `## Rule v1` and its own `## Answer-hop simulation …` section); `test_pilot_docs.py` (no id-shaped string, no lone CR, on `docs/pilot/*.md`). No test reads the security, design, practice or release documents.
  - `/review-loop` rounds 19–21 (cap 3): 5 LOW applied (units, qualifiers and one variant's name), converged at round 21. `loop-history-check.py`: 21 round entries and 21 findings-log headings, unique and strictly increasing, OK.
  - FOR D.4, verbatim:
    1. The shipped count line (`ui/models.py` `flagged_count_line`), its parenthesis: "(a line you said, an answer to a question you asked, or a side, negation, number, dose, name or medication someone said)". The `clinician_line_omitted` hint (`WARNING_COPY`), its clause, after "to find it": "(if it was a question, its answer is flagged too)". The full hint: "Check the transcript beside the note, tick 'Show flagged or suggested lines only' to find it (if it was a question, its answer is flagged too), add it with Add line to section if it belongs, then acknowledge." The tooltip's short form is unchanged: "a line you said that is not in the note (check its flagged lines)". Recommended: approve as drafted.
    2. The clinician review guide's draft 0.3.7 lines:
       - in step 2: "**From version 0.3.7 (draft, awaiting your approval):** when you ask a question the app placed under a heading, the other person's answer is usually placed straight after it, under the same heading, even if none of your headings' phrases is in it — often several lines, up to where someone else speaks. Read it as carefully as any line: the answer stays under your question's heading even where it belongs elsewhere; if the speakers were mixed up, a line of yours may be placed as the answer; a bare "No" means nothing without its question; and anything the patient asks you not to write down is placed too — remove it. It is never placed under the assessment, diagnosis, advice or management plan headings. If the app did not spot a next patient, the next patient's answer can be placed this way: check the end of the transcript."
       - in step 6: "**From version 0.3.7 (draft, awaiting your approval):** when a left-out line of yours is a question, the other person's answer after it is marked `[flagged]` too, and so is the answer to a question you added back yourself; the hint says "if it was a question, its answer is flagged too". A flagged answer has no warning of its own and never stops you saving: add it if it belongs. A flagged line can be one that must stay out — small talk, or the next patient's words — so leave those out."
       Recommended: approve as drafted (the "(draft, awaiting your approval)" words and the draft-history line's "awaiting the practitioner's approval", and the practice README's "these lines await the practitioner's approval", are then replaced by the approval date).
    3. The SEC-001 residue sentence, as written in the threat model (THE ANSWER HOP, residue (2)): "(2) given as a LATER line of the same reply turn it is quoted too (Phase V review round 15 SEC-001; pinned) — awaiting the practitioner's word at D.4, recommended accepted as a named residue of the same class as (1) and the carry's CONTINUATION RESIDUE; the app honours no spoken instruction, and the clinician-owned sections are never joined into;". The same point is in the harness document's "Small talk and spoken instructions" limit ("awaiting the practitioner's word at its Task D.4"). Recommended: accept it as a named residue; on acceptance both "awaiting" phrases become the dated acceptance.
  - No MUST-PAUSE: no real decision arose; every document could be made true without a code change.
  - Hand-back: reason=composer-run, with the gate above. No Python other than the history check; no commit, stash or ref change.
- Executor handoff (leg mx2, 2026-11-17T16:31+11:00 resume; stage-3, M.1's record, plan records only):
  - Read `.cursor/loops/afq-m1.txt` by exact path and recorded on Task M.1: the run line, the per-set difference counts, the two D8 rows cell by cell, each set's pinned items, the product's reference rows and the timing. Each figure was checked against the file, and every line matches the task's "Expected" text. The file has no `refused` or `error ` line.
  - Marked M.1 and Phase M done; the stop rule's "M reproduces the finalist's lines and the plan continues" applies.
  - Recorded the run as agent-run, plainly. This plan's C7 is about host and conduct (this host, background runs with `< /dev/null`, mains power, lid open, the installed app closed) and has no clause about agent-shell checks, so nothing more is claimed.
  - Updated Overall Progress (65%: 15 of the 23 kept tasks), the last completed step, the current step (stage-4, D.1) and the next action. Phase M's edits are uncommitted; the commit is asked at D.4.
  - `loop-history-check.py`: 18 round entries and 18 findings-log headings, unique and strictly increasing, OK (no review round was added by this leg).
  - No code, test, document or scratch script changed; only this plan (LF, no NUL). No Python other than the history check; no commit or ref change.
- Executor handoff (leg mx1, 2026-11-17T09:27+11:00 spawn; stage-3, Phase M's Task M.1 script only):
  - Written: `.cursor/loops/afq-measure-built.py` (git-ignored, synthetic only, LF). It imports `afq_lib.py` unchanged. `afq_lib.py` and `afq-measure-kept.py` are untouched (C5).
  - Recorded on Task M.1: what the script runs and compares, its refusals, the composer's self-test and overnight commands, and the expected outcome of each. M.1 stays 🟥 until the overnight run is recorded.
  - Three readings to know before reading its output:
    1. The no-hop baseline is re-run in the gate configuration through Task 0.3's own route. "New error-grade warnings" needs the no-hop note's warnings, which the saved projections lack. The re-run doubles the model time (two compositions per encounter, about four hours for the seven sets) and checks itself against the saved `none.json`. Harm is still computed against the saved `none.json`.
    2. The product's joins are derived from its note (provider-placed segments the baseline does not place), since the product keeps no join record.
    3. The flagged columns are compared twice: QT (the harness credit) against the gate's QT column, and the product chooser's mark against the gate's QT+m column.
  - None of these is a decision: each follows from M.1's words and Task 0.6's recorded reading. If the composer prefers to skip the re-run, the error-grade item cannot be measured from the saved files; that WOULD be a decision.
  - Checked without Python: HEAD is `4a0081d`; `git status --porcelain -- desktop` is empty; the script is under the ignored `.cursor/loops/`. Every harness name the script and `afq_lib` use exists at `4a0081d` (read in `validation.py`, `note.py` and `ui/models.py`).
  - Not run: the script has never been executed (verify=composer). The self-test on `heldout-5` is the first run. A Python error there is a script defect for the next leg, not a measurement.
  - No product code, test or document changed; only this plan (LF, no NUL) and the new scratch script. No commit or ref change.
- Executor handoff (leg cx5, 2026-11-17T09:23+11:00 resume; stage-2, Phase V's close, plan records only):
  - Recorded: the composer's gate on leg cx4 (`.cursor/loops/stage-2-cx4-gate.txt`: ruff and mypy clean, pytest 10937 passed, 9 skipped, every return code 0) on round 17.
  - Transcribed round 18 verbatim from `.cursor/loops/stage-2-peer-r18.log` (its last `### Round 18` header to its `PEER-ROUND-18 RESULT` line), with the composer-recorded line: pass `stage-2-h4b.p1`, peer round 2 of cap 5. Round 18 had 0 findings and confirmed both of round 17's fixes. It is added to Review History.
  - Marked done: H4 (slice A at round 16, slice B at round 18), Step H (H1 at round 13, H2 at 14, H3 at 15, H4 at 16–18) and Phase V. Updated Overall Progress (55%), the last completed step, the current step and the next action.
  - `loop-history-check.py`: 18 round entries and 18 findings-log headings, unique and strictly increasing, OK.
  - No code or test was changed; only this plan, which stays LF with no NUL. No Python was run apart from the history check, and no commit or ref change was made.
- Executor handoff (leg cx4, 2026-11-17T09:12+11:00 resume; stage-2, the fix leg for round 17):
  - `/fix` on round 17, one finding at a time. Both were LOW Fix-now and test-harness only, so headless auto-disposable. Both are Applied, and round 17 is Closed; the tuple block's decision lines are updated.
    - PR-LOW-020: `fixtures/answer_hops.py` (LF) gains `s-a-suspect-carried-piece-opens-nothing`: the S lines with `suspect=(1,)`, placed `((0, RED), (1, RED))`. It adds one parametrised test; the joining set is unchanged.
    - PR-LOW-021: `test_validation_metrics.py` (CRLF kept) gains `TestReplyCredit.test_a_partly_quoted_reply_is_passed_over`: segment 2 quoted at word 0, `replies_after == {1, 3}`.
  - Neither test needed a product change. The product as built behaves as each asserts (leg cx3's evidence, re-read before writing), so there is no MUST-PAUSE.
  - Fix-delta self-check: PASS.
  - Changed: the two test files and this plan, which stays LF. No product code, `docs/` or frozen file was touched. No Python was run, and no commit or ref change was made.
  - The gate for the composer, from `C:\Recording clinic software`: `cd desktop && ../.venv/Scripts/python.exe -m ruff check . < /dev/null && ../.venv/Scripts/python.exe -m mypy < /dev/null && ../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider < /dev/null`
    - Expected: ruff "All checks passed!"; mypy "Success: no issues found in 67 source files"; pytest 10937 passed, 9 skipped (10935 plus one parametrised case and one test).
  - Nothing under `extension/` changed, so `npm run qa` is not owed. `afq-pin.py` is not owed either: no router or credit code changed.
- Executor handoff (leg cx3, 2026-11-17T09:07+11:00 resume; stage-2, verification-only: the gate record, H3's close, H4's rounds 16–17):
  - Recorded: the composer's gate on leg cx2 (`.cursor/loops/stage-2-cx2-gate.txt`: ruff and mypy clean, pytest 10935 passed, 9 skipped, every return code 0) on round 15, and H3 is CLOSED (🟩).
  - Transcribed verbatim as rounds 16 and 17: each from the last `### Round N` header to the `PEER-ROUND-N RESULT` line of `.cursor/loops/stage-2-peer-r16.log` and `stage-2-peer-r17.log`, each with a composer-recorded line (its log, pass id `stage-2-h4a.p1` / `stage-2-h4b.p1`, peer round 1 of cap 5, the two slices in parallel). Both rounds were added to Review History.
  - Round 16 (slice A, the product): 0 findings.
  - Round 17 (slice B), both verified against the code and the fixture, and both rated `materiality=regression severity=LOW surface=test-harness rec=Fix-now`, with the originals kept beside them:
    - PR-LOW-020: the S twin with a suspect carried piece. The product carries the piece (`prev_clean` reads only the previous line), and `_opens_answer_window` refuses the window (`note.py:2330`), so the reply is dropped. The proposed expectation `((0, RED), (1, RED))` holds today.
    - PR-LOW-021: a partly covered reply. `_reply_turn` takes only `wholly_uncovered` lines and walks on, so the proposed expectation (no credit on the partly covered line, credit on the later uncovered one) holds today.
  - No product defect, so no MUST-PAUSE.
  - No code or test was changed in this leg; only this plan. It stays LF. No Python was run, and no commit or ref change was made.
  - For the fix leg: put the PR-LOW-020 twin after `s-the-cue-routed-piece-is-the-question` in `fixtures/answer_hops.py` (LF), with `suspect=(1,)` and `placed=((0, RED), (1, RED))`. Check whether `test_both_directions_are_exercised`'s sets need it. Put PR-LOW-021 in `test_validation_metrics.py` (keep that file's line endings) beside `test_the_whole_reply_turn_and_where_it_ends`, with a one-word `Span` on segment 2. The expected suite after the fix is 10937 passed, 9 skipped: one parametrised case and one test.
- Executor handoff (leg cx2, 2026-11-17T08:51+11:00 resume; stage-2, the gate record, H2 and H3):
  - Recorded: the composer's gate on leg cx1 (`.cursor/loops/stage-2-cx1-gate.txt`) on V.1 (now 🟩) and on round 13, and H1 is CONVERGED at round 13.
  - H2, round 14 (`/simplify`): no simplification worth a maintainer's attention. Seven candidates were left alone with their reasons, and nothing changed.
  - H3, round 15 (`/security-review`, the portable checklist): 2 MED, both Fix-now and applied.
    - SEC-001: under V4, a spoken instruction given as a LATER line of the reply turn is quoted, beyond accepted residue (3)'s first reply.
      - Behaviour is unchanged (Task 0.6 fixed V4). The case is now pinned: the fixture case `joins-a-later-reply-dont-write-this-down` and `test_a_later_reply_dont_write_this_down_is_quoted`.
      - `test_the_first_reply_dont_write_this_down_is_quoted` now selects its case by exact name, since its old `endswith` filter would match both cases.
      - The practitioner's word on it is placed at D.4, with the recommendation "accept as a named residue". It is not a MUST-PAUSE: no behaviour changes, shadow mode stays on, and D.4 is before P.3's install decision.
    - SEC-002: D.1's threat-model residue list now also names:
      - a wrong speaker label;
      - a false question by its opening word;
      - a next patient's whole reply turn where no boundary is found, and the reply flag's same cut;
      - a third speaker;
      - the `h5-17` quote.
  - No product code changed in this leg. Changed files: `desktop/tests/fixtures/answer_hops.py` (one case), `desktop/tests/test_note.py` (a joining-set entry, the exact-name filter and one new test), and this plan. `docs/` is untouched (Phase D).
  - Line endings are kept: `test_note.py` CRLF; `answer_hops.py` and the plan LF.
  - No Python was run, and no commit or ref change was made.
  - Commands for the composer, each from `C:\Recording clinic software`:
    1. `cd desktop && ../.venv/Scripts/python.exe -m ruff check . < /dev/null && ../.venv/Scripts/python.exe -m mypy < /dev/null && ../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider < /dev/null`
       - Expected: ruff "All checks passed!"; mypy "Success: no issues found in 67 source files"; pytest 10935 passed, 9 skipped (10933 plus one parametrised fixture case and one new test).
    2. Optional, narrow first: `cd desktop && ../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_note.py -k TestAnswerHop < /dev/null`
    3. `cd extension && npm run qa < /dev/null`, only if the composer wants it: nothing under `extension/` changed in this leg.
  - `afq-pin.py` is not owed: no router or credit code changed, and the pin reads `EXTRACTIVE_CELLS` and the sets, not `fixtures/answer_hops.py`.
- Executor handoff (leg cx1, 2026-11-17T08:34+11:00 spawn; stage-2, Task V.1 and H1 round 1):
  - V.1: the six version fields read 0.3.7, each read before and after its edit:
    - `desktop/pyproject.toml:7`;
    - `desktop/src/scribe_desktop/__init__.py:3`;
    - `extension/package.json:4`;
    - `extension/package-lock.json:3` and `:9`;
    - `extension/src/manifest.ts:29`.
  - No test or document pins the literal. `test_install_layout.py:907-917` and `test_build_release.py:624-626` compare the fields with each other, and `scripts/README.md:112`'s "since 0.3.6" is history.
  - `CHANGELOG.md`'s 0.3.7 entry is at the top of Added, with CRLF kept. It covers the hop, the reply flag and the QT credit, the improvement exit, shadow mode on, no run 10, the measured numbers, and the draft copy pending D.4.
  - Not done: the 0.3.6 version commit's `git log -S`, because this leg's grants cover `git status` and `git diff` only. The search above stands in for it.
  - H1 round 13 (round 1 of cap 3): 0 CRIT / 0 HIGH / 0 MED / 2 LOW, both applied. The round is in the Review Findings Log, and the history check passed (13 entries, 13 headings).
    - LOW-001: the hint's draft bracket now reads "(if it was a question, its answer is flagged too)", with its one pin in `test_ui_models.py`.
    - LOW-002: the hop docstring now names the source of each residue.
    - Nothing in Task 0.6's specification was found to diverge, and there is no MUST-PAUSE. By `/review-loop`'s rule round 13 is converged (no CRIT, HIGH or MED), so a round 2 is needed only if the gate fails.
  - Files this leg changed:
    - the six version fields and `CHANGELOG.md`;
    - `ui/models.py` (the hint), `note.py` (the docstring) and `test_ui_models.py` (the pin);
    - this plan.
  - Line endings are kept: CRLF everywhere, except `test_ui_models.py` (LF) and this plan (LF). No Python was run, and no commit or ref change was made.
  - Commands for the composer, each from `C:\Recording clinic software`:
    1. `cd desktop && ../.venv/Scripts/python.exe -m ruff check . < /dev/null && ../.venv/Scripts/python.exe -m mypy < /dev/null && ../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider < /dev/null`
       - Expected: ruff "All checks passed!"; mypy "Success: no issues found in 67 source files"; pytest 10933 passed, 9 skipped (no test added or removed; one pin moved).
    2. `cd extension && npm run qa < /dev/null`. The manifest's version moved, so a build or manifest test may read it.
  - `afq-pin.py` is not owed: neither fix touches the router's behaviour or the credit, only a docstring and a copy string.
- Executor handoff (leg bx5, 2026-11-17T08:10+11:00 resume):
  - Phase 1 is complete and gate-green, all four tasks 🟩, uncommitted on `a00685c`.
    - 1.3 is DONE: the 4 new Check 2 tests (64 passed in `TestCheck2Contradictions`), the recorded reading, and the full gate at 10933 passed, 9 skipped.
    - 1.4 is DONE: `afq-pin.py` exited 0 with `PIN differences total: 0` over 384 encounters (`.cursor/loops/afq-pin-1.txt`). That agrees with the product leaving out D1's row 4.
  - This leg changed only the plan: Tasks 1.3 and 1.4, Overall Progress, Last completed step and this note. It ran no Python, made no commit or ref change, and the plan stays LF.
  - Not yet run, and owed by later steps:
    - Phase 1's reviews (Step H's H1–H4, over Phase 1 and V's whole diff against `22feec4`);
    - the live smoke (P.3, the install smoke);
    - Task 0.8's documents (D.2 and P.5);
    - the copy wording (D.4).
  - Uncommitted files: the plan; `desktop/src/scribe_desktop/note.py`, `ui/models.py`, `validation.py`; the tests `test_note.py`, `test_note_check.py`, `test_note_matrix.py`, `test_ui_models.py`, `test_ui_screens.py`, `test_validation_harness.py`, `test_validation_metrics.py`, `test_validation_scripts.py`; and the new `desktop/tests/fixtures/answer_hops.py`. The git-ignored `.cursor/loops/afq-pin.py` is not part of any commit.
  - Next: the composer asks the practitioner whether to commit Phase 1 now as a checkpoint. Then Phase V (V.1, Step H) runs under stage-2 with a fresh executor.
- Executor handoff (leg bx3, 2026-11-17T07:28+11:00 resume; written 2026-11-17T07:43+11:00):
  - (a) Task 1.1 marked 🟩 DONE with the composer's counts (10899 passed, 9 skipped), the one held-out divergence `h5-17` `(5,)` → `(3, 5)` and its join, no matrix cell moved, the new tests, and the row-4 note (unreachable under V4; Task 1.4 checks it).
  - (b) Task 1.2, what was built (no Python run by the executor; verify=composer):
    - `ui/models.py`:
      - `flagged_runs` is unchanged in behaviour. It now reads two private helpers: `_flagged_end` (the cut) and `_flagged_run_ranges` (one range per run, in anchor order, without repeats; their union is `flagged_runs`).
      - New `_reply_turn`: the scratch's `replies_after` with `whole_turn=True`, line for line. A textless segment is passed over; the first text-bearing speaker must not be the confirmed clinician, and with none confirmed there is no reply; every wholly uncovered line of that speaker's turn is taken, a covered one is passed over, and a speaker change ends the turn.
      - New `_added_only_clinician_lines`: the scratch's `manual_only_clinician_lines`, with the `m` test written as `assertion_id == manual_assertion_id(segment_index)` rather than the scratch's `startswith("m")`. The two agree on every note the app or the harness makes.
      - New public `replies_after(note, document, *, added_questions=False)`: the ONE helper (D4).
        - Questions only: a run counts when any piece is interrogative.
        - The reply turn after each counting run.
        - With `added_questions` (the chooser only), also the turn after an added interrogative question before the cut: the scratch's `+m`.
      - `flagged_segments` = the anchors ∪ `flagged_runs` ∪ `replies_after(..., added_questions=True)`. `replies_after` is in `__all__`.
      - Copy (both marked in a code comment as "the executor's wording, a draft until D.4"):
        - the count line's parenthesis is now "(a line you said, an answer to a question you asked, or a side, negation, number, dose, name or medication someone said)";
        - the `clinician_line_omitted` hint gains "(an answer to it is flagged too)" after "to find it".
        - The short form in `SEPARATELY_ACKNOWLEDGED_NAMES` is unchanged: the plan names only the parenthesis and one hint clause.
    - `validation.py`:
      - `encounter_metrics(..., reply_credit=True)`: `replies = replies_after(note, document)` (no `+m`), its own third term in `word_info`'s `warned`, non-suspect only.
        - The 0.3.4 walk reads that term too, so the run-only counts stay the joined run's alone.
        - `credited_segments`, `credited` and the run-only counts are untouched.
      - D5's second complete computation: `encounter_metrics(..., reply_credit=False)`, from the same note.
        - It runs only with a `reference` reading and a credit that reached a segment (otherwise the two are equal), the same gating as the run-only counts. With its residue classes and exemptions, it is stored as `EncounterMetrics.without_reply_credit` (one level, the same facts; validated).
        - It adds `segments_credited_by_reply_only` and `facts_credited_by_reply_only`. The second counts facts silently omitted without the credit and not with it.
        - New public `without_reply_credit(outcome)`.
      - The report:
        - The residue section's new line, after the run-only line: "- Reply credit (the reply to a flagged question, metric amendment 2026-11-17, answers-follow-question D4, D5; the counts reported, read by no rule): segments credited by the reply only N, material facts credited by the reply only M, in E encounters. Verdict without the reply credit (every metric computed again without it): PASS|FAIL. Failing encounters: …; set-level: …."
        - The line names no rule label, so the same outcomes print the same line under any rule.
        - The heading and the table keep the verdict with the credit (rule v6's form), and no column is added. `_residue_section` takes the run's `errors`.
      - The dated amendment sentence, appended to the shared amendments after the run credit's: "It also holds on the reply to a flagged line that holds a question (the other speaker's wholly uncovered lines through the turn that follows it, before the next-patient boundary), metric amendment 2026-11-17 (answers-follow-question D4, D5): a loosening decided after run 9 failed on this class."
        - A set report adds: "The verdict without the reply credit, and what it alone credits, is the residue section's reply-credit line."
      - No rule file changes.
    - New tests:
      - `test_validation_metrics.py` `TestReplyCredit`, beside `TestJoinedRunCredit`:
        - the reply flagged and credited; a statement run credits none (QT); no warning, no credit; the whole turn (a covered line passed over, a speaker change ends it); the cut; the clinician's own next line is no reply; a suspect reply word is never credited;
        - an added (or suggested: the same `manual_assertion_id`) question keeps its reply flagged but not credited, with and without the warning row. Without it, the reply is flagged with no warning behind it;
        - Add then undo restores the mark; only a question in the note solely by an Add marks its reply (not a provider line, not both, not an added statement); no confirmed clinician;
        - "Acknowledge all" unchanged; credit ⊆ `[flagged]` and `credited_segments == flagged_runs` over `SPLIT_CASES`;
        - D5's second computation (the counts 1 / 1, equal to a direct `reply_credit=False` call, the verdict with it passing and without it failing on `silent_omission`); none where the credit reached nothing or there is no reference; its validation.
      - `test_validation_harness.py`: a `_reply_line` helper and `test_the_reply_credit_line_sums_and_gives_the_verdict_without_it`.
  - Every moved pin, each with its reason:
    - Copy, the drafted wording (draft until D.4):
      - `test_ui_models.py` `clinician_line_omitted`'s `clear_hint` (`:1524-1531`);
      - `test_the_count_line_counts_and_names_the_lines_the_chooser_cannot_offer` (`:2097-2104`);
      - `test_the_count_line_carries_the_suggestion_clause` (`:3072-3075`);
      - `test_ui_screens.py` `test_a_flagged_line_is_marked_in_place_and_counted` (`:5805-5809`) and the replaced-line count label (`:5968-5970`).
    - The report shape (the new sentence and the new residue line):
      - `test_validation_harness.py` `_RUN_INFORMATION` gains the two sentences;
      - the exact residue-section lists gain `_reply_line(...)` after `_run_only_line(...)`: `test_a_schema_2_report_names_both_verdicts_and_the_set_layer`, the rule-v3 `heldout-4` pin, the `heldout-5` rule-v5 pin and the `heldout-4` rule-v5 pin;
      - `test_a_residue_section_with_nothing_measured_reads_dash`'s `tail[11]` is the new line, reading `-` and `FAIL` with its one failing outcome, and the boundary record moves to `tail[12]`.
    - Not moved, on a static read:
      - the legacy header's substring pins (`:2349-2360`): the new sentence follows them;
      - the short-form pins (`:1529`, `:2273`);
      - every `flagged_segments` exact pin: no fixture question there has a reply after it (`fixtures/joined_runs.py` holds no `?`; the screens' and suggestions' fixtures end on statements or end with the question). The composer's run is the check, and a moved one is a finding.
  - Line endings: `ui/models.py`, `validation.py`, `test_validation_metrics.py`, `test_validation_harness.py` and `test_ui_screens.py` stay CRLF throughout. `test_ui_models.py` stays LF, as it already was (`git ls-files --eol`).
  - Commands for the composer, in order (each from `C:\Recording clinic software`):
    1. Narrow first: `cd desktop && ../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_validation_metrics.py tests/test_validation_harness.py tests/test_ui_models.py tests/test_ui_screens.py tests/test_ui_suggestions.py tests/test_note_check.py < /dev/null`
    2. Then the full gate: `cd desktop && ../.venv/Scripts/python.exe -m ruff check . < /dev/null && ../.venv/Scripts/python.exe -m mypy < /dev/null && ../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider < /dev/null`
    - Expected:
      - ruff "All checks passed!" and mypy "Success: no issues found in 67 source files".
      - pytest about 10929 passed, 9 skipped: 10899 plus about 30 new, the `SPLIT_CASES` parametrisation adding one per case.
      - Please paste every failing node id with its assertion lines.
- Executor handoff (leg bx2, 2026-11-17T07:18+11:00 resume):
  - The composer's leg bx1 run: ruff clean; mypy clean (67 files); pytest 1 failed, 10898 passed, 9 skipped (494 s). The one failure: `test_note_check.py::TestCheck1HedgeMark::test_the_held_out_unsure_lines[h5-17]`, got `(3, 5)` against the expectation `(5,)`. No correction divergence and no other fixture moved.
  - Recorded as C3 says, the expectation unchanged: `h5-17: ((5,), (3, 5))` in `_PREDICTED_UNSURE_DIVERGENCES_BY_SET["heldout-5"]`, the count 10 → 11.
  - The join that explains it, read from the code and `validation/heldout-5/h5-17.json`:
    - segment 2, the clinician's "When did it start?", routes to History through the validation cue `did it start`;
    - it is a question, and its one sentence routes there alone, so guard G passes and the window opens;
    - segment 3, the patient's "Maybe a fortnight ago, maybe longer.", has no cue in either layer and is not a question, so it joins History;
    - its "maybe" is a listed hedge, so Check 1 marks it.
    This is Key Findings' predicted "`h5-17` (5,) → (3, 5)". It holds under V4gs as well, because the clinician's next cued question (segment 4) closes the window.
  - Command for the composer: the full gate only, `cd desktop && ../.venv/Scripts/python.exe -m ruff check . < /dev/null && ../.venv/Scripts/python.exe -m mypy < /dev/null && ../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider < /dev/null`. Expected: ruff and mypy clean as before; pytest 10899 passed, 9 skipped.
- Executor handoff (leg bx1, 2026-11-17T06:55+11:00 spawn; stage-1, Task 1.1 only):
  - What was built (no Python run by the executor; verify=composer):
    - `note.py`: `ExtractiveNoteProvider.generate_sections` gains branch (4), the answer hop, with V4gs fixed (unlimited reach, guard G, switch S); new private methods `_question_routes_alone` (G), `_opens_answer_window` (D1 (a) and (d), S's either-piece test, G over the pieces as one line), `_answer_is_clean` (D1 (c)); new module helper `_last_sentence_text` with `_SENTENCE_END_MARKS` (D2's cut: `.`, `?`, `!`, closing marks peeled, no abbreviation handling, as the scratch's `sentences`). The class docstring gains the hop's paragraph with its named residues. `_route`, `is_interrogative`, every frozen vocabulary and `provider_name` are unchanged.
    - New `desktop/tests/fixtures/answer_hops.py`: 27 cases (`ANSWER_HOP_CASES`) — rows 1, 2, 3 and 5 both ways, G's refusals and both named limits, S's either-piece and the guard over both pieces, an unconfirmed clinician, the joined line closing the carry chain, and the first-reply "don't write this down" pinned as quoted.
    - `test_note.py`: `TestAnswerHop` (the cases; both directions; residue (3); `_route` stays cue-only; D1 (d) on the window test itself; D3 field for field against a carried line, with reconstruction; the sentence cut).
    - `test_note_matrix.py`: `ExtractiveCell.joins` (the hop registry), one declared cell `ex-answer-joined`, the lint `test_only_a_declared_join_follows_a_clinician_question` and `test_every_join_cell_is_registered`. No existing cell has a confirmed clinician's question, so none moves.
    - `test_validation_scripts.py`: the third arm "or it is joined" (`_hop_joined_lines`: placed by the shipped provider under the validation config, no route of its own, not the bounded carry of the same speaker's cue-routed line).
  - Finding for the composer (no behaviour change; recommendation: accept as built): under the chosen unlimited reach, D1's row 4 (one carried piece after a joined reply) can never fire. Every piece row 4 would carry also meets row 3: the same non-clinician speaker, who is the first reply's speaker; the same reply tests; the window still open; no budget. The scratch's row-4 branch is therefore unreachable for V4gs, and the product leaves it out, saying so in a comment and the docstring. A comma-split reply's second half and a correction after a reply are pinned as joined (`joins-a-reply-split-at-a-comma`, `joins-a-correction-after-a-reply`). Task 1.4's comparison against the scratch's V4gs checks the equality.
  - Line endings: `note.py`, `test_note.py`, `test_note_matrix.py`, `test_validation_scripts.py` stay CRLF throughout (checked); the new fixture is LF (git normalises it).
  - The held-out tables (`_PREDICTED_CORRECTION_DIVERGENCES_BY_SET` in `test_note.py`, `_PREDICTED_UNSURE_DIVERGENCES_BY_SET` in `test_note_check.py`) are NOT yet touched: their moved entries come from the composer's run (they read the real held-out scripts). Expected: a joined reply that opens with a correction marker becomes a "carried correction" in `_held_out_corrections`, and a joined hedged reply becomes an unsure line, so some `test_the_held_out_corrections[...]` / `test_the_held_out_unsure_lines[...]` cases and the two count tests may fail. Also possible: UI and note-level fixtures elsewhere that hold a confirmed clinician's cue-routed question followed by an uncued reply.
  - Commands for the composer, in order (each from `C:\Recording clinic software`):
    1. Narrow first: `cd desktop && ../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_note.py tests/test_note_matrix.py tests/test_validation_scripts.py tests/test_note_check.py < /dev/null`
    2. Then the full gate: `cd desktop && ../.venv/Scripts/python.exe -m ruff check . < /dev/null && ../.venv/Scripts/python.exe -m mypy < /dev/null && ../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider < /dev/null`
    - Expected: ruff "All checks passed!"; mypy "Success: no issues found in 67 source files"; pytest about 10836 + about 70 new passed, 9 skipped, apart from any held-out or fixture failures above. Please paste every failing node id with its assertion lines (the `got` / `predicted` / `expected` values), so each moved entry can be recorded with its join.
- Executor handoff (leg ax11, 2026-11-17T06:45+11:00 resume):
  - Recorded in leg ax11:
    - Task 0.6 DONE, with the composer's question and the practitioner's label verbatim, "Accept all three (Recommended)". The three reported residues are now accepted by name, beside the `h5-17` residue, the named real-speech override and AT's declined load.
    - Task 0.7 DONE, a scoped `/review-plan` (Review Findings Log Round 12). The improvement exit's phases are hardened in place:
      - Phase 1: 1.1 the hop, 1.2 the flag and credit, 1.3 consumers, and a new 1.4 for scratch against product;
      - V: V.1 and Step H, with Task 0.6's residues on H3's read list;
      - M.1: the built product replayed over the saved documents in the gate configuration, compared encounter for encounter with Task 0.3's V4gs QT gate projections;
      - D: split into D.1–D.4, with the practitioner's copy wording and review-guide approvals at D.4;
      - F.3, and P.3 and P.5.
    - The gate-capable phases are marked NOT BUILT with dated lines.
    - Task 0.8 stays 🟥: on this exit its parts are written with D.2 and at P.5.
    - Tracked changes: this plan, plus leg ax3–ax4's two document edits. No scratch file changed, so the hashes stand. No product code changed (D6). No Python run by the executor.
  - MUST-PAUSE from Task 0.7: none. Three points for the composer:
    - The copy wording (D5) is placed at D.4 as a practitioner approval; Phase 1 builds a marked draft.
    - The plan has no "M.2". M.1's stop rule is its only decision point, unchanged: any difference from Task 0.3's lines pauses for the practitioner, with D13.
    - M.1's time: Task 0.3's gate run took 7.9 h for four configurations and M.1 replays one. It is still planned as an overnight background job of up to about eight hours.
  - Leg ax8's record, unchanged: Task 0.4b recorded UNMEASURED (n enrolled 2 < 3), and the Accepted Assumption on three recordings now FALSE.
  - Task 0.4b's observations, recorded on the task:
    - On real speech no finalist joined or carried any line, under either config. The hop's real-speech cost and benefit are both nil on this sample, and why is not observable from what the script prints (unknown).
    - The Excluded item on inverted roles has an unevaluable trigger: there is no attribution line (round 8 MED-001).
    - The reply credit's real-speech load, the same for every form:
      - pass 1 extra flagged lines Q1 median 2-3 (total 5), QT 11-15 (26), A1 12-26 (38), AT 115-127 (242);
      - pass 2 the same except AT 115-126 (241).
  - The `h5-17` finding (leg ax6) stands. It is a named harm residue for the practitioner's word at 0.6: "an indirect next-patient quote through the suggestion stage, not on a joined line".
  - Next actions, in order:
    1. The composer's close of Phase 0: the practitioner's word on a commit of Phase 0's records.
    2. Phase 1 under stage-1 (Tasks 1.1–1.4), then V, M.1, D.1–D.4, F.3, P.3 and P.5.
  - HISTORICAL — the options presented at Task 0.6, as leg ax8 wrote them. Decided 2026-11-17: option 1 ("yes, record QT"); see Task 0.6.
    - Every building exit needs, besides the choices below, the practitioner's explicit, named override of D8's unmeasured real-speech line (n enrolled 2 < 3).
    - On this sample the hop joined nothing on real speech. So in clinical use the build's only visible change there would be the reply credit's `[flagged]` marks.
    1. Recommended (REVISED in leg ax8 from "V4gs under AT"): accept the named `h5-17` residue, decline AT's real-speech load as a reported residue, and take V4gs under QT. That is the configuration D8's choice rule picks once AT and AT+m are set aside: QT's gate-pair silent count is 4 + 8. V4s ties and is broken by "G on". QT comes before QT+m.
       - Its reading: IMPROVEMENT (25 → 4 and 24 → 8 silent, 2 and 7 encounters failing), not GATE-CAPABLE.
       - Its cost, from `afq-gate-3.txt` (no threshold): extra flagged lines on `heldout-5` / `heldout-6` 15 / 30, and stay-out newly flagged 0/1/0 and 1/1/1.
       - On real speech: QT's extra flagged lines per recording, median 11-15, max 15 (total 26), in both passes.
       - Why the revision: AT would flag median 115-127 extra lines per real recording, against QT's 11-15. That is about nine times QT's load by the passes' totals (242 against 26), for 1 + 5 more facts recovered on the synthetic gate pair (AT 3 / 3 against QT 4 / 8).
       - The credit marks those lines `warned` in the harness, which claims the clinician was pointed to each one. At over a hundred extra flags in one consultation that claim is weak, and the mark stops singling anything out. QT's load keeps the claim plausible while still meeting IMPROVEMENT.
       - What does not change: every harm sub-line except the `h5-17` residue is met, and the case for accepting that residue is the same as before. The quote is not on a joined line (D8's own words). It arises under `confirm-all`, the harness's worst case, whereas in the app a suggestion is added only when the clinician accepts it. Its class is already registered (F-155–F-169, F-132).
    2. V4gs under AT, the configuration D8's choice rule picks if the practitioner accepts both the `h5-17` residue and AT's real-speech load.
       - IMPROVEMENT: 3 / 3 silent, 1 / 3 failing.
       - Synthetic cost: extra flagged 50 / 78 on `heldout-5` / `heldout-6`, stay-out newly flagged 2/2/2 on each.
       - Real-speech load: AT median 115-127, max 127 (total 242) in pass 1; 115-126 (241) in pass 2.
    3. The reply credit alone, no hop (`none` under AT or AT+m). It is harm-free under the recipe's measure and reads IMPROVEMENT (9 / 8 silent, 3 / 7 failing).
       - Its cost: AT's synthetic load (51 / 75 extra flagged, 3/2/3 and 2/2/2 stay-out newly flagged) and AT's real-speech load above.
       - No other credit with no hop reads IMPROVEMENT: QT reaches 10 / 13 against the halves 12.5 / 12.
       - Whether D8's configurations include a credit with no hop is the practitioner's reading of the plan, not the executor's.
    4. NO-GO: close with no change and record the numbers, as the suggestion-repair plan did. Its case is stronger since 0.4b: real speech is unmeasured, and on the two recordings the hop did nothing.
  - Lesson (run time): the gate configuration (`--gate`, suggestions confirm-all and prose, three forms, the seven saved sets) takes about EIGHT hours on this laptop, not the one hour the plan and leg ax3 estimated. Each set was about an hour, the 50 longer. Plan any re-run of it as an overnight job, never beside a practitioner run.
  - Open points (the executor's readings where D1 / D2 / D4 leave a choice; none changes a premise), checked against Task 0.3's audio-level output — keep all five. REVIEWED 2026-11-17 by codex round 11 (the composer routed them to one more slice before 0.6), 0 findings: points 1, 4 and 5 match D1 / D2 as written; points 2 and 3 are consistent with D4's words, and their numerical share of QT's 4 / 8 is not isolable. They are now part of Task 0.6's chosen definition:
    1. After a joined line or a carried piece the existing carry's chain is closed (`prev_cued` False), as when that line was dropped before the hop, so row 5's existing carry never reaches across a reply. Now exercised: carries after a join under V1 are 2, 3, 2, 1, 1, 3, 5 by set (`scripts` … `heldout-6`), with no line that must stay out quoted.
    2. "Questions only" counts a run as a question when any piece passes `is_interrogative` (S's "a question if either piece is"). Runs of two pieces now exist (S candidates on five sets); the tables do not separate this reading's effect. The peer may ask for a one-off count.
    3. `replies_after` skips textless segments (transparent, row 1) and, in "whole turn", passes over a covered line of the reply speaker without crediting it. Joins across a wordless segment are still 0 at audio level. The whole-turn reading is exercised (QT and AT credit more facts than Q1 and A1 on both gate sets).
    4. V4t's window survives a cue-routed line of the first joined speaker, or of any non-clinician before the first join. Text-only by D2, exercised at Task 0.2.
    5. The S counter counts, with S off, each existing carry of a confirmed-clinician piece after which S would open a window, and the S-only reach is measured by composing the `s` form (`joins_only`). At audio level: candidates on five sets, one S-only line (`heldout-6`, holding `h6-01:f2`), so S is on the finalists.
  - The scratch: three files written in leg ax1 (2026-11-15T19:31+11:00 spawn) and a fourth, `afq-measure-kept.py`, in leg ax3, all git-ignored under `.cursor/loops/` (synthetic content only, except a measuring run of the fourth, which is the practitioner's; every printed surface is ids or ordinals, script-line and segment indices, counts and section keys).
    - `afq_lib.py` — `HopProvider` (an `ExtractiveNoteProvider` subclass re-implementing `generate_sections` with D1's five-row table; `Form` / `parse_form`: `none`, `V1` / `V3` / `V4`, suffixes `g` (guard G, D2's sentence cut and alone-routes test), `s` (switch S), `t` (V4t, text only)); `JoinRecord` (joined reply → its question, carried pieces, joins across a wordless segment, windows, S windows, S candidates, V4t survivals); D4's credit (`Credit`, `credited`, `replies_after`, `flagged_run_ranges`, `manual_only_clinician_lines`; names `Q1` `QT` `A1` `AT`, `+m` for the chooser's wider predicate, `CREDIT_ORDER` as D8's tie-break); the recipe's patches (`credit_patch` over `validation.credited_segments`, `capturing` over `_compose_note` / `encounter_metrics`, `replaying` over `transcribe_in_temporary_store` / `read_wav_pcm`, an alignment cache over `validation._Alignment` — one alignment per document, since only the note changes between forms); `text_encounter`, `replay_encounter` (the shipped `evaluate_encounter`, dummy enrolment, fixed `now`), `joins_only`; the counters (`newly_quoted` as the per-fact verdict difference, `note_counters` — the one per-note function 0.4a's real-speech entry will share — `next_patient_joins`, `label_disagreements`, `stay_out_newly_flagged`, `extra_flagged`, `fact_segments`, `segment_script_lines`, `projection`).
    - `afq-transcribe.py` — `run8-p3-transcribe.py` with `RULES` rule v6 only, the seven seen sets, its `:142-144` C12 block dropped; one pickle per encounter (`encounter_id`, `commit`, `whisper_model`, `clinician`, `outcome`, `document`) and `report-rule-v6.md`.
    - `afq-measure.py` — `--self-test` (Task 0.1's premise), `--text` (Task 0.2: the join table, the S counter, the credit table per set, D8 across the sets, the mechanical shortlist), `--docs <root> --built <root>` (Task 0.3: the replay premise against each pickle first, `--premise-only` to stop there, then the same tables; writes `report-none-rule-v6.md` per set for the masked baseline diff), `--gate` (the finalists in `--suggestions confirm-all --prose`, all eight credits). Outputs: `.cursor/loops/afq-out/<mode>-summary.md` and per set and form a JSON projection.
    - `afq-measure-kept.py` (leg ax3; Task 0.4a) — modes `--list` (prints n; decrypts nothing), a measuring run (`<past_sessions folder> --enrolment <WAV> --config <folder> [--forms V4gs,V4s,V3gs]`, the finalists by default), and `--dry-run-docs <root> --config <folder>` (the synthetic pickles). Per ordinal and form it prints joined, carried, review on hop, error on hop, new error, review net and extra flagged lines under Q1 / QT / A1 / AT, then the aggregate block. It is described in its docstring and in the threat model's MEASUREMENT SCRATCH.
- Open blockers / open questions: None. Pauses to expect:
  - Phase 0's commit;
  - any M.1 difference (its stop rule);
  - D.4's two approvals (the copy wording, the review guide's 0.3.7 lines);
  - F.3's push;
  - P.3's install decision;
  - every commit and push.
- Critique gate (2026-11-15, three parallel lenses, every finding dispositioned in this plan):
  - Coverage and risk: 1 CRIT (`h5-18`: the first-line rule quotes a non-material line that must stay out → the practitioner's decision, D8's harm line and guard G); 4 HIGH (the flag's harm side → a reported column; the suggestion policy → D7; the loosening convention → D5 and D10; unnamed pins → Key Findings); 9 MED and 2 LOW (D4's form, the fixture mechanism, the real-speech fallthrough, Check 2 errors, documents, the improvement exit, `heldout-7` sites, residues, harm attribution, `provider_name`) → applied.
  - Practicality: 2 HIGH (the real-speech script reviewed and dry-run before it runs → Task 0.4a and C5; which cue file → the practitioner's "Both"); 6 MED and 3 LOW (the script's shape, the simulation recipe, the comparison mechanism, Phase 1's dependence on 0.6, the Phase M comparison, the host split, time, the no-change proof, the scratch's own document entry) → applied.
  - Simplicity: adopted — join and credit measured separately then combined; a joined answer may be followed by one carried piece (no separate comma variant; made its own guarded row of D1's table by peer round 1); S as a counter; V4t text-only; a report line instead of a new column; later phases in outline; Phase M as a replay on the improvement exit; the Phase M decision replaced by a stop rule. Kept as planned — the scratch location, the new helper, the persistence rule, the version order, the install decision after the build.
- Last plan sync: 2026-11-15
- Retro report: .cursor/loops/retro-answers-follow-question-20261115-192900-2af4-2026-11-17.md (2026-11-17)

## Review History
- 2026-11-15 round 1: 0 CRIT / 1 HIGH / 7 MED / 1 LOW; skew=plan peer-review (codex); action=all nine verified and applied
- 2026-11-15 round 2: 0 CRIT / 0 HIGH / 2 MED / 1 LOW; skew=plan peer-review (codex); action=round 1's nine confirmed; all three new verified and applied
- 2026-11-15 round 3: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=plan peer-review (codex); action=round 2's three confirmed; both new verified and applied
- 2026-11-15 round 4: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=plan peer-review (codex); action=round 3's two confirmed; the one record-only finding applied; CONVERGED
- 2026-11-15 round 5: 0 CRIT / 0 HIGH / 2 MED / 3 LOW; skew=none; action=none
- 2026-11-15 round 6: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=pre-existing; action=triage-and-ship
- 2026-11-15 round 7: 0 CRIT / 0 HIGH / 2 MED / 1 LOW; skew=build peer review (codex); action=all three verified and applied
- 2026-11-17 round 8: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=records review (Task 0.5); action=MED recorded for 0.6 (C5 forbids the fix), LOW applied; no number corrected
- 2026-11-17 round 9: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=records review (Task 0.5); action=none; CONVERGED
- 2026-11-17 round 10: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=records peer review (codex, Task 0.5); action=verified and applied, with a sibling sweep (one more stale 0.4b line; D8's first-reply check settled); CONVERGED
- 2026-11-17 round 11: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=open-points peer review (codex, Task 0.5); action=none; the five open points reviewed
- 2026-11-17 round 12: scoped /review-plan (Task 0.7); 7 adjustments (Coverage 5, Practicality 2) plus the NOT BUILT marking and sibling sweep; action=all applied in place; no MUST-PAUSE
- 2026-11-17 round 13: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=none; action=both applied (H1 round 1, Phase 1 and V.1's diff against `22feec4`); gate green; CONVERGED
- 2026-11-17 round 14: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=simplify (H2); action=none; seven candidates left alone by the conservatism guard
- 2026-11-17 round 15: 0 CRIT / 0 HIGH / 2 MED / 0 LOW; skew=security-review (H3); action=both applied (a test pin, D.1's residue list, D.4's practitioner question); no product code changed; gate green (10935 passed, 9 skipped); H3 closed
- 2026-11-17 round 16: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=build peer review (codex, H4 slice A `stage-2-h4a.p1`, peer round 1 of cap 5); action=none
- 2026-11-17 round 17: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=build peer review (codex, H4 slice B `stage-2-h4b.p1`, peer round 1 of cap 5); action=both verified (regression, test-harness; no product defect) and applied in the fix leg cx4 (a fixture case and a test; no product code); gate green (10937 passed, 9 skipped)
- 2026-11-17 round 18: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=build peer review (codex, H4 slice B confirmation `stage-2-h4b.p1`, peer round 2 of cap 5); action=none; round 17's two fixes confirmed; H4 CONVERGED
- 2026-11-17 round 19: 0 CRIT / 0 HIGH / 0 MED / 4 LOW; skew=none; action=all four applied (documents only, Phase D's diff, leg dx1)
- 2026-11-17 round 20: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=applied; round 19's four fixes confirmed
- 2026-11-17 round 21: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none; round 20's fix confirmed; CONVERGED
- 2026-11-17 round 22: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=documents peer review (codex, D.4 slice A `stage-4-d4a.p1`, peer round 1 of cap 5); action=none; slice A CONVERGED
- 2026-11-17 round 23: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=documents peer review (codex, D.4 slice B `stage-4-d4b.p1`, peer round 1 of cap 5); action=PR-LOW-040 verified real and applied in leg dx3 (kept-recordings.md and two plan siblings; documents only); slice B confirmation owed (round 24)
- 2026-11-17 round 24: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=documents peer review (codex, D.4 slice B confirmation `stage-4-d4b.p1`, peer round 2 of cap 5); action=none; PR-LOW-040's fix confirmed; slice B CONVERGED; D.4 done
- 2026-11-17 round 25: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=documents peer review (codex, the close documents `stage-6-p5.p1`, peer round 1 of cap 5); action=none; CONVERGED; P.5's close documents confirmed

## Review Findings Log
### Round 1 — 2026-11-15
Round status: Closed
Source: Codex (gpt-6-astra high) plan peer-review
Materiality: 8 build-affecting / 1 record-only / 0 invalid
Composer-recorded: the peer ran in a read-only sandbox and printed this round as its final message (`.cursor/loops/answers-follow-question-plan-peer-r1.log`, git-ignored; HEAD `50a8a2b`, the plan untracked; `git status` equal before and after). The planning session transcribed it from the last `### Round 1` header, verified each finding against the code, and applied the amendments under `/review-plan`'s amendment-application discipline (each landed, siblings swept). The peer also spot-checked 34 cites: 33 confirmed, one contradicted (PR-LOW-001).

#### PR-HIGH-001: `plan-answers-follow-question.md` simulation recipe — the harm counter misses non-material lines
- Materiality: build-affecting (verified at `validation.py:2308-2319`: the `suggested_segments` attribution requires `outcome.material`, and counts facts)
- Why it matters: D8 counts every line that must stay out, material or not; the recipe's counter could not see `h5-18`, the case that motivated the rule.
- /fix decision: Applied
- /fix notes: the recipe now measures harm as a per-fact verdict difference between the no-hop run and the variant run in the same configuration, for every `absent` fact, de-duplicated into (encounter, line) pairs. Siblings: Phase M's harm reading (M.1) now uses the same difference; Task 0.3's columns already asked for lines, material / not.
- /fix date: 2026-11-15
- /fix applied by: Claude Code

#### PR-MED-001: D1 — the existing carry could bypass "a reply that is a question closes the window"
- Materiality: build-affecting (verified at `note.py:2270-2286` and `test_note.py:3119-3121`: the existing carry takes a question, and tests no suspect word on the carried line)
- Why it matters: a joined answer ending in a comma would have carried the patient's next question or a suspect continuation; V3's budget did not say whether carried pieces count.
- /fix decision: Applied
- /fix notes: D1 now holds a five-row transition table frozen before Task 0.1: the hop's own carry row applies guard (c), a carried piece never uses the budget and carries nothing further, and a joined answer does not set the existing carry state. D2's reach is that budget. Sibling: the handoff note's simplicity line.
- /fix date: 2026-11-15
- /fix applied by: Claude Code

#### PR-MED-002: D5 — an aggregate second walk cannot give the verdict without the reply credit
- Materiality: build-affecting (verified at `validation.py:2261-2291`: the run-7 pattern keeps one aggregate count, while R1 reads each fact's silent state)
- Why it matters: the comparison verdict D5 and D10 promise needs per-fact residue classes.
- /fix decision: Applied
- /fix notes: D5 now computes the encounter's metrics twice from the same finalised note, with and without the reply credit; the second complete set gives the verdict, the difference gives the report line. Sibling: Task 1.2.
- /fix date: 2026-11-15
- /fix applied by: Claude Code

#### PR-MED-003: Tasks 0.3 / 0.6 — a credit configuration could be authorised without its gate-configuration measurement
- Materiality: build-affecting (verified against the plan's own text: only the narrowest and widest credit ran in the gate configuration)
- Why it matters: a suggested clinician question removes the warning that anchors the credit, so an off result does not establish a configuration's D8 lines.
- /fix decision: Applied
- /fix notes: each finalist's one composed note now gives full D8 lines for all four credit sub-variants and the chooser's wider predicate (the recipe re-invokes the metric walk per credit patch); D8 says a configuration is judged only on its own gate-configuration run; Task 0.6 says the same.
- /fix date: 2026-11-15
- /fix applied by: Claude Code

#### PR-MED-004: Task 0.3 — the shortlist, S's trigger and "least harm" left judgment open
- Materiality: build-affecting (verified against the plan's own text)
- Why it matters: the composer would have chosen finalists by a rule defined on results that did not exist yet.
- /fix decision: Applied
- /fix notes: Task 0.3 now ranks the six forms at off under the widest credit with fixed tie-breaks, gives a fixed lexicographic least-harm order, and D2 gives S an exact trigger (a silently lost material fact only an S window reaches) and tie-break (S off).
- /fix date: 2026-11-15
- /fix applied by: Claude Code

#### PR-MED-005: D8 — no exit for a harm-free form that recovers too little
- Materiality: build-affecting (verified against the plan's own text)
- Why it matters: a harmless 40% reduction met no stated exit.
- /fix decision: Applied
- /fix notes: D8 now makes NO-GO every remaining case, keeping the practitioner's named-residue override.
- /fix date: 2026-11-15
- /fix applied by: Claude Code

#### PR-MED-006: D2 — guard G was not executable consistently
- Materiality: build-affecting (verified at `note.py:1675-1677`, `:1824-1836`: a line can be a question by its opening words and end with a statement; no sentence rule existed)
- Why it matters: the main harm guard depended on an implementation choice made during measurement.
- /fix decision: Applied
- /fix notes: D2 now fixes the sentence cut (a word ending in `.`, `?` or `!` once closing marks are peeled), requires the last sentence to be a question and to route alone to P's section, and states the missing-punctuation, abbreviation and question-then-statement cases (each fails toward refusing).
- /fix date: 2026-11-15
- /fix applied by: Claude Code

#### PR-MED-007: Key Findings / Task 1.3 — Check 2 cannot find a contradiction in a bare "No."
- Materiality: build-affecting (verified at `note_check.py:1132-1133`, `:1212-1229`, `:1307-1312`)
- Why it matters: Task 1.3's tests would have asserted behaviour the checker does not have.
- /fix decision: Applied
- /fix notes: the downstream note and Task 1.3 now use a reply that names what it negates, and pin a bare "No." as an unchecked residue.
- /fix date: 2026-11-15
- /fix applied by: Claude Code

- **[LOW]** PR-LOW-001: Key Findings — "a split question is a question only in its last piece" overstated — Materiality: record-only (verified at `note.py:1675-1677`) — Decision: Applied (the note now says either, both or neither piece may qualify); applied by: Claude Code

### Round 2 — 2026-11-15
Round status: Closed
Source: Codex (gpt-6-astra high) plan peer-review
Materiality: 2 build-affecting / 1 record-only / 0 invalid
Composer-recorded: a fresh peer, read-only, on the post-amendment plan (`.cursor/loops/answers-follow-question-plan-peer-r2.log`; HEAD `50a8a2b`; `git status` equal before and after). It confirmed all nine of round 1's findings fixed (PR-HIGH-001, PR-MED-001 to -007, PR-LOW-001), and spot-checked 40 cites, all confirmed — among them that every fact, non-material absent ones included, gets an outcome (`validation.py:2198-2247`, `:2305`), and that suggestions and prose run before the metric credit, so one composed note serves every credit configuration (`validation.py:3376-3404`).

#### PR-MED-008: D8 — the final credit tie-break was not a complete ordering
- Materiality: build-affecting (verified against the plan's own text: "questions only, whole turn" and "any clinician line, first line" contain neither the other, and the chooser's wider predicate is a third dimension)
- Why it matters: equal measured recovery would have left the recommended configuration to an unstated preference.
- /fix decision: Applied
- /fix notes: D8's choice rule now ends in a fixed, stated order of the four credit sub-variants, each first without and then with the chooser's wider predicate crediting. Sibling: Task 0.3's shortlist ranks under the widest credit, the last in that order; no other statement asserted an ordering.
- /fix date: 2026-11-15
- /fix applied by: Claude Code

#### PR-MED-009: D8 / Tasks 0.4a, 0.4b — the real-speech budget had no stated denominator
- Materiality: build-affecting (verified: the hop joins nothing without a confirmed clinician, so unenrolled recordings add zeros; the precedent `.cursor/loops/run7-measure-kept.py:412-446` computes its budget over enrolled sessions only)
- Why it matters: three enrolled recordings over budget plus four unenrolled zeros would have passed an all-recording median.
- /fix decision: Applied
- /fix notes: D8's real-speech line, Task 0.4a's aggregate block and Task 0.4b's Done-when now read the median and maximum over enrolled recordings only, with the unenrolled count reported apart.
- /fix date: 2026-11-15
- /fix applied by: Claude Code

- **[LOW]** PR-LOW-002: D2 — guard G's description overstated refusal when punctuation is missing — Materiality: record-only (verified at `note.py:1675-1677`, `:2232-2240`: a line with no sentence-ending mark is one sentence, and G then repeats D1's own tests) — Decision: Applied (D2 now says a question-then-statement line fails G only where the recogniser wrote the boundary, and names the fused line as a limit of G; round 1's PR-MED-006 note "each fails toward refusing" is superseded for that one case); applied by: Claude Code

### Round 3 — 2026-11-15
Round status: Closed
Source: Codex (gpt-6-astra high) plan peer-review
Materiality: 1 build-affecting / 1 record-only / 0 invalid
Composer-recorded: a fresh peer, read-only, on the plan as amended after round 2 (`.cursor/loops/answers-follow-question-plan-peer-r3.log`; HEAD `50a8a2b`; `git status` equal before and after). It confirmed round 2's three findings fixed (PR-MED-008, PR-MED-009, PR-LOW-002) and spot-checked 44 cites, all confirmed. Its closing line: Phase 0 needs the completion-contract amendment before it is fully ready.

#### PR-MED-010: Tasks 0.4a / 0.4b — a partial real-speech run could satisfy the completion criteria
- Materiality: build-affecting (verified at `.cursor/loops/run7-measure-kept.py:318-343`: the precedent continues after a recording's error, prints aggregates over the successful ones and only then returns 1; `docs/testing/kept-recordings.md` makes "no failed recording" the replay's success condition)
- Why it matters: three successful enrolled recordings could have met D8 while another failed, with the failure absent from the only block the practitioner pastes.
- /fix decision: Applied
- /fix notes: Task 0.4a's aggregate block now carries expected, measured and failed counts (failures by error type name) and a `COMPLETE` / `INCOMPLETE` status, with exit 0 only on `COMPLETE`; Task 0.4b's Done-when needs both passes `COMPLETE`, else a re-run or a recorded "incomplete". Sibling: D8's real-speech line now says a pass counts only if it completed.
- /fix date: 2026-11-15
- /fix applied by: Claude Code

- **[LOW]** PR-LOW-003: D2 — "a cut at an abbreviation can only make G refuse" overstated — Materiality: record-only (verified at `note.py:1675-1677`, `:1756-1784`: a last fragment opening with a question word and holding the cue passes both of G's tests) — Decision: Applied (D2 names it as a second limit of G; G itself unchanged); applied by: Claude Code

### Round 4 — 2026-11-15
Round status: Closed
Source: Codex (gpt-6-astra high) plan peer-review
Materiality: 0 build-affecting / 1 record-only / 0 invalid
Composer-recorded: a fresh peer, read-only, on the plan as amended after round 3 (`.cursor/loops/answers-follow-question-plan-peer-r4.log`; HEAD `50a8a2b`; `git status` equal before and after). It confirmed round 3's two findings fixed (PR-MED-010, PR-LOW-003) and spot-checked 40 cites, all confirmed. Its closing line: ready to execute from Task 0.1. CONVERGED: a round after the first with no new build-affecting finding.

- **[LOW]** PR-LOW-004: D2 — V4's stopping words "until a row other than 3 or 4 applies" took in row 1, which D1's table makes transparent — Materiality: record-only (verified at D1 row 1 and `note.py:2259-2260`: a wordless line changes nothing) — Decision: Applied (D2 now reads "until row 2 or 5 applies; row 1 stays transparent"; D1's table unchanged, no sibling restates the old words); applied by: Claude Code

### Round 5 — 2026-11-15
Round status: Closed
Source: Claude Code (`/review-loop` round 1 of cap 3, executor leg ax3; Task 0.4a's Review line)
Scope: `.cursor/loops/afq-measure-kept.py` (new) and the `afq_lib.py` functions it reaches (`parse_form`, `measure_document`, `compose_off`, `note_counters`, `credited`, `replies_after`, `flagged_run_ranges`, `factory_for` / `HopProvider`, `load_pickle`); git-ignored scratch, read in full. Baseline: HEAD `22feec4` (the scratch is untracked).

#### MED-001: `afq_lib.note_counters` — "new error-grade warnings" was a net count
- Where: `afq_lib.py`, `note_counters` (`error_new`).
- Why it matters: D8 sends any new error-grade warning back to the practitioner. A form that removed one error-grade warning and added another scored 0, and the synthetic tables' "New error-grade" column reads the same function.
- /fix decision: Applied
- /fix notes: `error_new` now counts the form's error-grade warnings that the no-hop note lacks, keyed by code and segment. It can only rise against the old count. Consequence: the off tables (`afq-docs-1.txt`) and the gate run started at 21:46 (`afq-gate-1.txt`) used the net count, so the leg ax3 handoff asks for both to be re-run before the D8 lines are read.
- /fix date: 2026-11-15
- /fix applied by: Claude Code

#### MED-002: the real-speech pass 2 names a config the premise never saw
- Where: `afq_lib.py` `measure_document`; `afq-measure-kept.py`.
- Why it matters: Task 0.1's premise (the scratch's no-hop note equals the shipped one) was proven under `validation/config` only, while pass 2 composes under the installed app's own config folder.
- /fix decision: Applied
- /fix notes: `measure_document` composes the shipped provider's note (the default factory) beside the scratch's no-hop note, per document, and raises `PremiseMismatchError` on any difference. The kept script counts that as the recording's failure by type, so the pass reads `INCOMPLETE`. The real-speech entry is self-checking on every document under its own config.
- /fix date: 2026-11-15
- /fix applied by: Claude Code

- **[LOW]** LOW-001: "review on hop" counts warnings on carried pieces as well as joined lines, where D8 names "a joined line" — Triage: Fix-now; Decision: Applied (the reading is recorded in the script's docstring: both are quoted only by the hop, so the count is the higher one; the synthetic tables' "Review marks on hop lines" reads the same); applied by: Claude Code
- **[LOW]** LOW-002: `afq_lib.joins_only` repeated `compose_off`'s body — Triage: Fix-now; Decision: Applied (`joins_only` returns `compose_off(...)[1]`; same composition, same record); applied by: Claude Code
- **[LOW]** LOW-003: an unused `REPO` in `afq-measure-kept.py` — Triage: Fix-now; Decision: Applied (removed); applied by: Claude Code

### Round 6 — 2026-11-15
Round status: Closed
Source: Claude Code (`/review-loop` round 2 of cap 3, executor leg ax3)
Scope: the same files in full after round 5's fixes, with the two document edits (`docs/security/threat-model.md` MEASUREMENT SCRATCH, `docs/testing/kept-recordings.md` after line 7) checked against the script. Post-fix regression check: round 5's five fixes verified in place, none introducing a new path that prints text or an id. CONVERGED: no CRIT, HIGH or MED.

- **[LOW]** LOW-001: `--list` was refused by an invalid `--forms` value, though the documents say it checks only the channel and the folder — Triage: Fix-now; Decision: Applied (the `--list` dispatch now precedes the forms check); applied by: Claude Code

### Round 7 — 2026-11-15
Round status: Closed
Source: Codex — codex gpt-6-astra medium — build peer review (stage-0-t04a.p1)
Composer-recorded: Task 0.4a's codex slice over `afq-measure-kept.py` and `afq_lib.py` with the two document diffs, read-only, static only (`.cursor/loops/stage-0-peer-r7.log`, from its last `### Round 7` header; peer round 1 of cap 5; 17 files inspected, 5 jobs evidenced). The peer confirmed in place round 5's two MED fixes, the refusal order, the lock, the custody and interrupt paths, and the `persist_key=False` teardown. The executor (leg ax4) verified each finding against the code and disposed it as `/fix` does.

#### PR-MED-011: `afq-measure-kept.py` — a nonexistent `--config` folder measures the shipped defaults
- Materiality: build-affecting (verified at `note_config.py:948-957`: `_read_config_blob` treats `FileNotFoundError` as "use the shipped default", and `load_note_config:1017-1031` reads all four files that way without checking the root, so an absent folder loads cleanly as the defaults; the per-document premise compares two notes built from the same config and cannot see it)
- Why it matters: a mistyped installed-config path at Task 0.4b's pass 2 would measure the validation-like defaults and could end `COMPLETE`.
- Triage: Fix-now
- /fix decision: Applied
- /fix notes: `_config_dir` refuses (exit 2) when `--config` is absent or not an existing folder. It runs in the measuring run's argument checks, before the archive is touched or any config or model loads, and in the dry run before anything is read. A missing file inside an existing folder stays the loader's ordinary default. Siblings: `afq-measure.py` and `afq-transcribe.py` now refuse the same way. Every run recorded so far named the existing `validation/config`, so no recorded number is affected. The threat model's MEASUREMENT SCRATCH entry and `docs/testing/kept-recordings.md` now say "an existing config folder" (CRLF kept).
- /fix date: 2026-11-15
- /fix applied by: Claude Code

#### PR-MED-012: `afq_lib.py` — "extra flagged" subtracted the harness credit, not the chooser's shipped mark
- Materiality: build-affecting for the records, not for any exit (verified at `ui/models.py:2773-2784`: the chooser marks `omission_anchors | flagged_runs`, so a patient's `high_risk_omission` line is already `[flagged]`; `validation.credited_segments` is `flagged_runs` only, clinician lines, `:1893-1902`; the scratch subtracted the latter)
- Why it matters: a reply already marked by its own anchor was counted as a new flag, so the counts over-stated what the reply flag adds.
- Triage: Fix-now
- /fix decision: Applied
- /fix notes: one helper, `afq_lib.newly_flagged`, gives the credit's segments minus `ui.models.flagged_segments`, and all three readers use it:
  - `extra_flagged`: the synthetic credit table's "Extra flagged lines" column in the text, docs and gate modes;
  - `stay_out_newly_flagged`: the credit table's "Stay-out newly flagged mat/other/at-or-after tail" column, also in all three modes;
  - `measure_document`: the kept script's "extra flagged Q1 … AT" columns, per ordinal and in the aggregate.

  No other column, the D8-across-sets table or the shortlist reads them (the shortlist ranks silent facts and orders least harm by quoted lines). D8 sets no threshold on them: they are its "Reported for the practitioner's word at 0.6, with no threshold" line (lines that must stay out and are newly `[flagged]`; extra flagged lines per recording), so no exit moves. Each printed name now says what it counts (newly `[flagged]`, beyond the shipped mark). No separate harness-credit metric was added, because "Facts credited" already reports what the credit changes in the metrics.

  The counts recorded at Task 0.2 (17 / 18 / 39 / 40) and at Task 0.3 (the extra-flagged and stay-out-newly-flagged lines) were taken under the old reading. They are marked on their tasks and replaced from the composer's re-runs (leg ax4 handoff). Replaced: Task 0.2 from `afq-text-2.txt`, Task 0.3's off part from `afq-docs-3.txt`, and its gate configuration from `afq-gate-3.txt` (leg ax7, 2026-11-16).
- /fix date: 2026-11-15
- /fix applied by: Claude Code

- **[LOW]** PR-LOW-005: `afq-measure-kept.py` grouped `PastSessionError` failures by `replay_kept._reason` reason codes, where C1, Task 0.4a and the documents say by type name — Materiality: record-only (verified: the three handlers read `_reason`, which returns the allow-listed `exc.reason`; content-free either way) — Triage: Fix-now; Decision: Applied (all three now use `validation._error_type`; the measuring loop's separate `PastSessionError` branch is folded into the by-type handler; the docstring states the by-type rule); /fix date: 2026-11-15; applied by: Claude Code

### Round 8 — 2026-11-17
Round status: Closed
Source: Claude Code (`/review-loop` round 1 of cap 3, executor leg ax8; Task 0.5's first half)
Scope: this plan's records of Tasks 0.2, 0.3 (off part and gate configuration) and 0.4b, every figure checked against the composer's outputs, opened by name only:
- `.cursor/loops/afq-text-2.txt`: Task 0.2's join table, credit table, flagged columns and the text-level D8 and shortlist lines;
- `afq-docs-3.txt`: Task 0.3 off, the join table, S counter, credit table, flagged columns and their sums, replay premise, the D8 table and the shortlist;
- `afq-gate-3.txt`: the gate join table, credit table, flagged columns, replay premise and D8 rows, which equal `afq-gate-2.txt` outside the flagged and timing cells;
- the 0.4b aggregate blocks as pasted.

`afq_lib.py`'s `credited`, `replies_after`, `flagged_run_ranges`, `newly_flagged` and `measure_document` were read, not changed, for the 0.4b reading. Every recorded count, sum, ranking and verdict matched its source; no number is corrected.

#### MED-001: the Excluded item's revisit trigger names an output no task produces
- Where: Excluded — Revisit Only If Needed, "A clinician's answer to a patient's question (inverted roles) …": "When to revisit: only if real-speech attribution makes the confirmed-clinician test miss most questions (Task 0.4b's attribution line)".
- Why it matters: Task 0.4a's specification and `afq-measure-kept.py` print no attribution line, no question count and no refused-condition count. On real speech every finalist joined 0 under both configs, and the trigger cannot be evaluated: it is neither met nor ruled out. Task 0.6 would read an absent number as no evidence.
- Triage: Record-and-defer. Measuring attribution would change the hashed scripts (C5) and need another practitioner run. That is a choice for the practitioner, not a fix.
- /fix decision: Recorded, not changed. Task 0.4b's observation 1 states the trigger is unevaluable and the cause of joined 0 unknown, and the handoff's 0.6 options carry it.
- /fix date: 2026-11-17
- /fix applied by: Claude Code

- **[LOW]** LOW-001: Task 0.3's gate record attributed the no-hop R3 2 / 1 on `heldout-3`, `heldout-5` and `heldout-6` to the suggestion stage "as run 9 found", which is not cited and not established for `heldout-3` — Triage: Fix-now; Decision: Applied. The line now cites the off comparison, R3 1 / 1 on all three in `afq-docs-3.txt`, and the elimination: the prose stage only counts sections. Applied by: Claude Code.

### Round 9 — 2026-11-17
Round status: Closed
Source: Claude Code (`/review-loop` round 2 of cap 3, executor leg ax8)
Scope: round 8's fix in place. Then the leg's new text against its sources: Task 0.4b's record and observations against the pasted blocks and `afq_lib.py`; the handoff's revised 0.6 options against `afq-gate-3.txt`'s credit rows; and the Accepted Assumption's dated line.
- The QT reading checked out: V4gs and V4s QT at 4 / 8 silent and 2 / 7 failing; V3gs QT at 5 / 8; IMPROVEMENT against the halves 12.5 / 12; QT with no hop at 10 / 13, not an improvement.
- The choice-rule order with AT and AT+m set aside gives V4gs under QT.
- No per-recording value is recorded.
- CONVERGED: no CRIT, HIGH or MED; 0 findings.

### Round 10 — 2026-11-17
Round status: Closed
Source: Codex — codex gpt-6-astra medium — build peer review (stage-0-t05.p1)
Composer-recorded: Task 0.5's codex slice over the records and numbers, read-only (`.cursor/loops/stage-0-peer-r10.log`, from its last `### Round 10` header; peer round 1 of cap 5; 5 files read, 1,014 table rows checked, 5 / 5 jobs evidenced).
- Jobs 1–3 found every recorded figure, total and ranking, the D8 readings and both real-speech aggregate blocks consistent with `afq-text-2.txt`, `afq-docs-3.txt` and `afq-gate-3.txt`, with gate-2 against gate-3 sampled. No per-recording value appears.
- Jobs 4–5 found the decision options' disclosures sound, with one current-status contradiction.
- The executor (leg ax9) verified the finding against the plan and disposed it as `/fix` does.

- **[LOW]** PR-LOW-006: Overall Progress (`:3`) and the expected pauses (the handoff's "Open blockers" line) still listed the practitioner's 0.4b run as future work, though Task 0.4b is DONE, recorded UNMEASURED — Materiality: record-only (verified: `:3` read "the practitioner's real-speech run (0.4b) … ahead" and the pauses line "the practitioner's run at 0.4b") — Triage: Fix-now; Decision: Applied.
  - /fix notes: both lines now drop 0.4b from pending work and keep its UNMEASURED result and the named-override requirement.
  - The sibling sweep, every line naming 0.4b, found one more: Task 0.3's D8 line "Real speech: owed (Task 0.4b)", now UNMEASURED with the override. The same line still left D8's "don't write this down" first-reply check "owed to Task 0.5's records". It is now settled on Task 0.3: a phrase search over every script under `validation/` finds one line, `hld-17` line 2, a second reply that no finalist quotes or newly flags. The search's limit is stated there.
  - The sweep also found the five open points marked "the codex peer to review them at 0.5", outside round 10's slice. Their routing is left to the composer in the handoff, with a recommendation; they are not marked reviewed.
  - /fix date: 2026-11-17; applied by: Claude Code

### Round 11 — 2026-11-17
Round status: Closed
Source: Codex — codex gpt-6-astra medium — build peer review (stage-0-t05.p2)
Composer-recorded: the composer routed the five open points to one more codex slice before Task 0.6, rather than to Task 0.7 (`.cursor/loops/stage-0-peer-r11.log`, from its last `### Round 11` header; peer round 2 of cap 5; 6 scoped files read, 5 / 5 jobs evidenced, static only). Its readings, one per point:
- Point 1 (carry-state closure): matches D1, and the shipped `note.py:2286-2289` also clears the carry state after a carry or a dropped utterance, so row 5 cannot carry across a reply.
- Point 2 (`run_is_question`'s any-piece reading on D4's question-only credit): consistent with D4, which does not prescribe classifying the concatenated text. It can credit more than a concatenated predicate would, but the tables do not isolate that difference.
- Point 3 (whole-turn traversal past a covered line): consistent with D4. A speaker change ends the turn; coverage only filters what is included. V4gs Q1 → QT is 14 → 4 silent on `heldout-2` and 16 → 8 on `heldout-6`, combining all later-line credit, so any share that crosses a covered line is not isolable. No change to the recommended 4 / 8 is established.
- Point 4 (V4t): unreachable for V4gs, V4s and V3gs (it needs the `t` suffix); the gate tables report zero survival.
- Point 5 (the S counter and composition): matches D2's potential-window definition; `joins_only` isolates S.

Findings: none.

### Round 12 — 2026-11-17
Round status: Closed
Source: Claude Code (scoped `/review-plan`, Task 0.7, executor leg ax11; `.claude/skills/review-plan/SKILL.md` "Scoped mode", full scoped critique, since the addition is multi-task and cross-cutting)
Scope:
- The tasks hardened: the improvement exit's kept phases, read against Task 0.6's record, D1–D13, C1–C8, Key Findings' pin and site lists and Validation / Verification.
- The real code read at HEAD `22feec4`, whose product tree equals `50a8a2b`, the commit Key Findings verified (`git diff --stat 50a8a2b 22feec4` over the product paths is empty):
  - `note.py` `generate_sections` and the class docstring;
  - `ui/models.py` `omission_anchors`, `flagged_runs`, `flagged_segments`, `flagged_count_line` and the `clinician_line_omitted` copy;
  - `validation.py` `credited_segments`, the run-only counts and `word_info`;
  - `test_note_matrix.py`'s carry lint and registry;
  - the predicted-divergence tables in `test_note_check.py` and `test_note.py`;
  - `TestFlaggedLineCredit` and `TestJoinedRunCredit`'s locations.
- Executor tier inherited (entirely premium).

The three lenses:
- Coverage: five gaps, all applied in place.
  - (1) M.1 had no named tool or exact comparison target. It now names `afq-measure-built.py` and compares against Task 0.3's V4gs QT gate projections, encounter for encounter.
  - (2) D5 gives the copy's wording to the practitioner in Phase D, but Phase 1 builds the copy. Resolved without a new decision: Task 1.2 lands a marked draft and D.4 takes the practitioner's wording before F.3.
  - (3) The scratch-against-product comparison sat in 1.1, before the credit exists. It is now its own Task 1.4, after 1.2 and 1.3.
  - (4) D5 says what the report prints under rule v7 only. Task 1.2 now states rule v6's form: the verdict with the credit, the second verdict in the report-only line, and no column.
  - (5) Task 0.6's accepted residues are now pinned or read: residue (3) as a `TestAnswerHop` case, and the `h5-17` quote and residue (3) on H3's read list. F-155's control line is in P.5.
- Practicality: two applied.
  - D.1 was one task over about fifteen documents. It is now D.1–D.4: security and design; testing; practice, pilot, release and project; approvals and the peer pass.
  - Every line cite in the hardened tasks was checked at HEAD; the threat model's cites are re-located by search, since that file changed after `50a8a2b`. Key Findings' `h5-17` prediction was made for the first-line rule, so Task 1.1 takes the V4gs entries from the suite.
- Simplicity: no simpler approach meets the goal. M.1 replays one configuration over the saved documents, not a full re-run, so the comparison is exact and free of transcription noise. That is what Validation / Verification already said.

The NOT BUILT marking (Task 0.7's done-when), following `plan-suggestion-repair.md`'s convention (the tasks stay 🟥 for the record under a dated NOT BUILT line):
- F.1, F.2, P.1, P.2 and P.4;
- M.1's gate-capable variant;
- D10 and D11 (NOT APPLIED), and C6 (not in force);
- Agreed Scope's gate-capable bullet, Validation's gate-capable line, and Key Findings' `heldout-7` sites.

Amendment-application discipline:
- Each edit was confirmed landed by a fresh read or search.
- Contradicted siblings were reconciled:
  - the Goal and Flow 4 now say the reply is flagged only after a left-out question (QT);
  - Shared helpers names the two new scratch files;
  - Task 0.8 says when its parts are written on this exit;
  - the plan footer points to this round.
- A sibling left as is, with its reason: Planning Extraction's "Hardening depth" line, which records the 2026-11-15 choice.

MUST-PAUSE: none surfaced. Every open item resolves within D1–D13 or is already placed with the practitioner (D.4's two approvals; P.3).

Findings: none beyond the seven adjustments above (Coverage 5, Practicality 2), all applied in place, plus the NOT BUILT marking and the sibling sweep.

### Round 13 — 2026-11-17
Round status: Closed
Source: Claude Code (`/review-loop` round 1 of cap 3, Step H's H1, executor leg cx1, stage-2)
Scope: Phase 1 and Task V.1's whole diff against `22feec4` (`git diff 22feec4 -- desktop extension CHANGELOG.md`, 16 files, plus the untracked `desktop/tests/fixtures/answer_hops.py`), read in full:
- `note.py`'s hop (`generate_sections`, `_opens_answer_window`, `_question_routes_alone`, `_answer_is_clean`, `_last_sentence_text`);
- `ui/models.py`'s `replies_after`, `_reply_turn`, `_added_only_clinician_lines`, `_flagged_run_ranges`, `_flagged_end`, `flagged_segments` and the two draft copy strings;
- `validation.py`'s reply-credit term, D5's second computation, `without_reply_credit`, the residue line and the amendment sentence;
- the new and moved tests, and the six version strings.

Read against Task 0.6's state table and credit definition, D1–D5, the accepted residues and `docs/lessons.md`. What was checked, each holding:
- The branch order is D1's: transparent first, then a cue route, the join (row 3), the existing carry, dropped. The join comes before the carry, and the two cannot both apply, since the carry needs the clinician and the join refuses the clinician.
- A join, a carry and a drop each leave the window as D1 says. S's `cue_words` is always the line directly before, because the carry needs `prev_cued`.
- G calls `layered_section` with `_route`'s arguments. `NoteUtterance.text` is `reconstruct_span_text(words)`, so G and `_route` read the same text.
- Row 4 is subsumed at V4, as Task 1.1 records and Task 1.4 measured.
- `replies_after` is QT as Task 0.6 defines it: any piece interrogative, the whole turn, a covered line passed over, a speaker change ends it, the cut. The `+m` case is in the chooser only.
- Credit ⊆ `[flagged]` holds by construction, and `credited_segments` is unchanged.
- D5's second computation:
  - it reaches the 0.3.4 walk as its comment says;
  - it recurses one level only;
  - its reference reading is unaffected, because `facts_right` reads verdicts and the credit changes only `warned`;
  - `facts_credited_by_reply_only` counts material facts only, since `silent_omission` requires `material`.
- `run_passed` takes `errors=`.
- Line endings are kept in every touched file (`git ls-files --eol`: no mixed file).
- No test or document pins "0.3.6" beyond the six version fields. `test_install_layout.py:907-917` and `test_build_release.py:624-626` compare the fields with each other, not with a literal.

- **[LOW]** LOW-001: the `clinician_line_omitted` hint's draft bracket "(an answer to it is flagged too)" is shown on every such warning, but under QT an answer is flagged only after a left-out QUESTION. On a left-out statement the hint claims a flag that is not there — Triage: Fix-now; Decision: Applied. It now reads "(if it was a question, its answer is flagged too)" (`ui/models.py` `WARNING_COPY`), with its one pin (`test_ui_models.py:1524-1530`). It stays a draft until D.4. No other pin holds the string (search). Applied by: Claude Code. /fix date: 2026-11-17.
- **[LOW]** LOW-002: `ExtractiveNoteProvider`'s docstring credited all four of its named residues to Task 0.6. Only the first-reply "don't write this down" is Task 0.6's accepted residue (3). The bare "No." and learned-cue amplification are the Codebase Integration Notes' residues, and the "Dr." cut is D2's named limit of G — Triage: Fix-now; Decision: Applied. The docstring now names each one's source (`note.py`, docstring only). Applied by: Claude Code. /fix date: 2026-11-17.

Fix-delta self-check: PASS. Re-read the two applied hunks in context: the copy string's concatenation still reads as one sentence, and the pin matches it byte for byte; the docstring edit is prose only. Verification is the composer's gate (verify=composer): the executor ran no Python.

Verification (recorded in leg cx2): the composer's gate over both fixes was green (`.cursor/loops/stage-2-cx1-gate.txt`): ruff and mypy clean, pytest 10933 passed, 9 skipped, `npm run qa` clean. H1 is CONVERGED at this round.

### Round 14 — 2026-11-17
Round status: Closed
Source: Claude Code simplify (Step H's H2, executor leg cx2, stage-2; `.claude/skills/simplify/SKILL.md`)
Scope: the same surface as round 13 (Phase 1 and V.1's diff against `22feec4`, plus the untracked `desktop/tests/fixtures/answer_hops.py`), every in-scope file read in full. D1–D5, Task 0.6's state table and credit definition, C5 and D6's scratch-equality rule were read as fixed shapes. A simplification that moved the product from the scratch's behaviour (Task 1.4's 0 differences) would not have been applied.

Simplifications found: none. No candidate is worth a maintainer's attention.

Consciously left alone (the conservatism guard), each with its reason:
- `flagged_segments` computes `covered_words` and the cut twice, through `flagged_runs` and `replies_after`. Merging the two saves one walk of the note per chooser refresh, a small cost, and would couple the chooser's two readers that D4 keeps apart. Marginal.
- `_segment_line` is a one-line wrapper over `reconstruct_span_text` with two call sites. Taste only.
- The two `window_key = key if self._opens_answer_window(...) else None` assignments in `generate_sections` could become one method returning the key or None. An equivalent idiom; marginal.
- `segments_credited_by_reply_only = len(replies - credited)`. The two sets are disjoint by construction (a reply is never the confirmed clinician's, and every `flagged_runs` segment is). `len(replies)` would be equal, but the subtraction states the intent and survives a future change to either set. Left.
- `_reply_turn`'s two loops (skip textless, then walk the turn) could be one loop with a state flag, which would be less legible. Left.
- `_flagged_run_ranges`' `run not in runs` de-duplication over a list (quadratic in the run count, which is at most the segment count). It keeps the anchor order; no measurable cost. Left.
- The two test helpers `_hop_joined` (`test_note.py`) and `_hop_joined_lines` (`test_validation_scripts.py`) answer different questions: the fixture's own cases, and the held-out scripts under the validation config with the bounded carry excluded. Not duplication.

Summary: round 14, 0 findings (0 CRIT / 0 HIGH / 0 MED / 0 LOW), no change.

### Round 15 — 2026-11-17
Round status: Closed
Source: Claude Code security-review (Step H's H3, executor leg cx2, stage-2; `.claude/skills/security-review/SKILL.md`, the portable checklist run in this session, no native subagent)
Scope: the same surface as rounds 13–14, read against:
- `docs/security/threat-model.md` Phase 3A surface 2 (`:477-754`: Check 4's two codes, NEXT PATIENT, THE TRIM, the bounded carry's CONTINUATION RESIDUE, THE CORRECTION CARRY, THE UNSURE MARK);
- the "Phase 3B (coverage)" section (`:2166-2376`, ENFORCED and residues (s1)–(s5));
- Step H's residue list: a wrong speaker label, a false question by its opening word, a next patient's reply where no boundary is found, a spoken instruction as a reply (accepted residue (3) included), a third speaker, learned-cue amplification and the `h5-17` suggestion-stage quote.

Trust boundaries examined:
- transcript text into the note (the hop places verbatim transcript lines only, the same `transcript` assertion, rebuilt by Check 1);
- the ownership rule (a question never sits in a clinician-owned section, and `_opens_answer_window` refuses one anyway);
- the next-patient cut (the request is cut before the provider, and `_flagged_end` is the same cut);
- the reply flag (indices only; it adds nothing to the note and blocks nothing);
- the harness credit (synthetic only).
`validation/heldout/hld-17.json` was read, a synthetic script and not blind, to check how the unlimited reach meets a spoken instruction.

#### SEC-001 (MED): a spoken instruction given as a LATER line of the reply turn is quoted, beyond accepted residue (3)
- Severity: MED (no exploit path beyond what the clinician reviews; a scope-of-acceptance gap on patient-privacy content).
- Where: `note.py` `ExtractiveNoteProvider.generate_sections`, the hop branch (4). With the unlimited reach (V4), every line of the reply speaker's turn joins while it meets D1 (c).
- Why it matters:
  - Task 0.6's accepted residue (3) names a "don't write this down" given as the FIRST reply, which D8 singled out as clean by absence. Under V4, the same instruction as a second or later line also joins whenever the first reply is uncued.
  - `hld-17` line 2 escaped only because its first reply (line 1) is cue-routed, which closes the window (row 2).
  - The practitioner's acceptance (2026-11-17) covered the first-reply case by name. The later-line case was neither pinned nor named.
- Current behaviour: quoted, unpinned. Desired: behaviour unchanged (Task 0.6 fixed V4), pinned and named, with the practitioner's word on it.
- Triage: Fix-now (pin and record; no behaviour change). Fix route: fix-on-fast.
- /fix decision: Applied.
- /fix notes:
  - A new fixture case `joins-a-later-reply-dont-write-this-down` (`fixtures/answer_hops.py`: the question, "No, none at all.", then "And please don't write this down."; each reply word checked absent from the shipped cue file) and `TestAnswerHop.test_a_later_reply_dont_write_this_down_is_quoted`.
  - `test_both_directions_are_exercised`'s joining set gains the case.
  - `test_the_first_reply_dont_write_this_down_is_quoted` now selects its case by exact name: its `endswith` filter would have matched both cases and broken its one-element unpack.
  - D.1's threat-model residue list names it, and D.4 asks the practitioner, with the recommendation to accept it as a named residue (the class of residue (3) and of the bounded carry's CONTINUATION RESIDUE). Declining needs a new dated guard decision with its own measurement (Task 0.6's "Decline (3)" route).
  - Pattern siblings: the bounded carry and the correction carry already carry this class, named (CONTINUATION RESIDUE, THE CORRECTION CARRY); there is no other route into the note. Search: `generate_sections`' branches (1)–(4), the only placement code.
- /fix date: 2026-11-17. Applied by: Claude Code.

#### SEC-002 (MED): D.1's threat-model residue list omits five residues the hop and flag have as built
- Severity: MED (a threat model that understates cross-patient and misattribution reach; documentation only).
- Where: Task D.1, which listed "Task 0.6's four accepted residues, the bare 'No.', and learned-cue amplification".
- Why it matters: H3's list names more, and each holds in the code:
  - a wrong speaker label (D1 (a), (b) key on the label: a patient's question labelled as the clinician opens a window, and a clinician's line labelled as another speaker joins as a reply);
  - a false question by its opening word (`is_interrogative`'s WH-opener and auxiliary-with-pronoun rules; G repeats them on the last sentence);
  - a next patient's reply where no boundary is found (the request is cut only at a detected boundary, so a next patient's whole reply turn joins: wider than the bounded carry's one hop, NEXT PATIENT residue (a)). The reply flag's `_flagged_end` likewise stops only at a detected cut;
  - a third speaker as the reply speaker (D1 (b); pinned `joins-another-speakers-reply`);
  - the `h5-17` quote, recorded beside (s3).
  Documents belong to Phase D, so `docs/` is not edited now.
- Triage: Fix-now (plan record). /fix decision: Applied. D.1's bullet now lists each residue, and SEC-001's, with its source.
- /fix date: 2026-11-17. Applied by: Claude Code.

Checked and clean:
- Injection and taint: no new sink. The hop quotes verbatim transcript words through `whole_utterance_assertion`, no model reads them, and no text leaves `replies_after` (indices only).
- Ownership: a joined line never enters a clinician-owned section (`_opens_answer_window` refuses the key; a question never routes there), and the chooser still applies `admissible_sections`.
- Next-patient cut: the provider's request is already cut, and `_flagged_end` reads the same `next_patient_segment`.
- Secrets and logs: no logger or log call added, and no new field or persisted shape (D3). The tripwire signatures are unchanged.
- Copy and write: a joined line is copied and written like any quoted line, under the same gates (shadow mode refuses both). Check marks stay out of copies.
- Suspect words: the hop refuses a suspect question or reply (D1 (a), (c)), the harness credit skips suspect words, and the chooser may flag a suspect reply. Flagging adds nothing, and an Add goes through Check 1's marks.
- Resource: `replies_after` is linear in the segments per run; `_flagged_run_ranges` is quadratic in the run count, bounded by the segment count; no unbounded allocation.
- Dependencies and config: none changed. The frozen vocabularies, cue files, held-out sets and rules are unchanged.
- Learned-cue amplification: named in the docstring and on D.1. The learners still test `spoken_by_confirmed_clinician` first (Task 1.3's reading), so a joined patient line teaches nothing.

Summary: round 15, 0 CRIT / 0 HIGH / 2 MED / 0 LOW, both Fix-now and applied (a pin and two plan records); no product code changed. A recommendation that stands: the project's own security tests (`test_shadow_exits.py`, `test_integration_no_sockets.py`) run in the composer's full gate.

Fix-delta self-check: PASS. Re-read the three test hunks in context:
- The new fixture case's tuple is well-formed under ruff's 100-column limit.
- The first-reply test's exact-name filter selects one case.
- The new test expects segments {1, 2}: `_hop_joined` counts uncued, non-clinician placed lines, and both replies are such.
- No product hunk was applied.

Verification (recorded in leg cx3): the composer's gate over round 15's changes was green (`.cursor/loops/stage-2-cx2-gate.txt`): ruff "All checks passed!"; mypy "Success: no issues found in 67 source files"; pytest "10935 passed, 9 skipped in 477.93s (0:07:57)" (10933 plus the new fixture case and the new test, as expected); every return code 0. H3 is CLOSED at this round.

### Round 16 — 2026-11-17
Composer-recorded (transcribed in leg cx3): from `.cursor/loops/stage-2-peer-r16.log`, its last `### Round 16` header to its `PEER-ROUND-16 RESULT` line; pass id `stage-2-h4a.p1` (slice A, the three product files); peer round 1 of cap 5; slices A and B ran in parallel. Transcribed verbatim below.

Source: Codex — codex gpt-6-astra medium — build peer review (stage-2-h4a.p1, slice A: product code)
Status: Closed (0 pending)

Scope:

- job 1: checked the hop against Task 0.6 and scratch V4gs: guards, G, S, transparent lines, unlimited reach, cue precedence, speaker changes and carry closure match. `note.py:2406` sets `prev_cued = False` after a join; the existing carry remains one-hop. Scratch row 4 is subsumed by the unlimited clean-reply branch. No ordering defect or double placement found.
- job 2: checked QT credit, chooser-only `m` replies and D5 recomputation. `ui/models.py:2886` tests questions across the run; `_reply_turn` passes covered lines and stops at speaker changes and the cut. `flagged_segments` includes `replies_after(..., added_questions=True)`, while the harness uses its default, preserving credit ⊆ `[flagged]`. `validation.py:2398` recursively recomputes metrics with `reply_credit=False`, including residue classes and exemptions; the report uses those outcomes and forwards set-level errors. No defect found.
- job 3: checked empty/textless inputs, absent clinician, final replies, cuts within turns, suspect words, third speakers and quoted-line marks. Bounds checks prevent end-of-transcript indexing; request assembly excludes segments at the boundary (`note.py:1470`). Suspect replies close the hop window; harness credit excludes suspect words. Joined assertions retain full source coordinates and ordinary transcript provenance, preserving number/unsure mark inputs. Third-speaker behavior matches the specified rule. No new failure found.
- job 4: checked all three product diffs against `22feec4`: existing frozen vocabularies, cues and interrogative rules are unchanged. No persisted note field, schema or provenance was added; the new metrics fields implement D5. Reviewed rounds 13–15 as prior findings, not proof; their addressed issues are not repeated.

Findings: none.

Verification: 5 files read (3 product files, specified plan sections, exact-path reference); 4 jobs evidenced. Static inspection only; no scripts, tests, network commands or writes performed.

PEER-ROUND-16 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 17 — 2026-11-17
Composer-recorded (transcribed in leg cx3): from `.cursor/loops/stage-2-peer-r17.log`, its last `### Round 17` header to its `PEER-ROUND-17 RESULT` line; pass id `stage-2-h4b.p1` (slice B, tests, fixture, version and CHANGELOG); peer round 1 of cap 5; slices A and B ran in parallel. Transcribed verbatim below; the executor's verification follows the result line.
Round status: Closed (leg cx4 applied both findings; the peer's own `Status:` line below is as transcribed in leg cx3).

Source: Codex — codex gpt-6-astra medium — build peer review (stage-2-h4b.p1, slice B: tests, fixture, version, changelog)
Status: Open (2 pending)

Scope:
- job 1: checked the hop matrix and reply-credit tests against the state table. Main join/refusal, G, S, cut, whole-turn, covered-line, manual-Add and credit-subset cases are present; two failing-direction gaps remain below.
- job 2: checked every moved expectation. `h5-17: ((5,), (3, 5))` and heldout-5’s 10 → 11 match Task 1.1’s recorded join. The reader still asserts `case.unsure == expected`; the frozen expectation was not edited away. UI changes are the recorded draft-copy changes.
- job 3: checked fixture expectations, parameter lists, selectors, placement assertions and the third arm. No contradictory fixture expectation or tautological product assertion found. Exact-name selectors unpack one case; fixture-registry checks supplement actual product assertions.
- job 4: checked all six version fields: 0.3.7. No stale literal 0.3.6 pin found in the reviewed test files. CHANGELOG distinguishes pre-build measurements from release status, retains shadow mode, states no run 10, and identifies copy as draft pending D.4. Measurements were not rerun.

Findings:
- **PR-LOW-020** (LOW, test coverage, `desktop/tests/fixtures/answer_hops.py:273`): Switch S lacks a negative case where its carried piece contains a suspect word. The single-piece suspect-question case cannot detect a regression that checks only the cue-routed piece when opening an S window. Evidence: `"s-the-cue-routed-piece-is-the-question"` expects `placed=((0, RED), (1, RED), (2, RED))`, without a suspect twin; the product contract says `"no piece holds a suspect word"` (`note.py:2325`). Recommendation: Fix-now — add a twin with a suspect word in the comma-carried piece, asserting that the piece remains carried but the patient’s reply does not join.

- **PR-LOW-021** (LOW, test coverage, `desktop/tests/test_validation_metrics.py:1719`): The reply-credit coverage test exercises a fully quoted reply, but not a partly quoted reply. It therefore does not pin “wholly uncovered” against a regression that credits the uncovered remainder of a partly covered line. Evidence: `note = _note(document, 2, warnings=[_warning(*self._QUESTION_WARNING)])` followed by `assert replies_after(note, document) == frozenset({1, 3})`; the specification requires `"wholly uncovered, text-bearing lines"` (plan:1159). Recommendation: Fix-now — add partial coverage on reply segment 2 and assert that it receives no reply credit while the later uncovered reply remains credited.

Verification:
- 19 files read through scoped diffs or relevant sections, including the complete new fixture.
- 4 jobs evidenced.
- Static review only; no scripts, suites, network operations or writes performed.

PEER-ROUND-17 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 2).

Executor verification (leg cx3, verification-only: no `/fix`, no code or test changed). Each finding was read against `fixtures/answer_hops.py`, `test_note.py`, `test_validation_metrics.py`, `note.py` and `ui/models.py`, and the product was checked for how it behaves on each proposed test's input:
- PR-LOW-020 — original: LOW, test coverage, Fix-now.
  - `materiality=regression severity=LOW surface=test-harness rec=Fix-now (test-only, owed to the fix leg) — the twin's expectation holds on the product as built, so it is a missing regression guard, not a defect.`
  - Evidence: the carry (branch (2), `note.py:2407-2433`) tests only the previous line's suspect state (`prev_clean`, set at `:2382`), so a suspect carried piece IS carried into RED. `_opens_answer_window` (`:2330`) then refuses on any suspect piece of `(cue_words, words)`, so `window_key` is None. The reply reaches branch (2) with `prev_cued` False and is dropped (3). The twin's `placed=((0, RED), (1, RED))` therefore passes today. The existing cases pin suspect state only on a single cue-routed question (`a-suspect-question-opens-nothing`) and on a reply (`a-suspect-reply-closes`); neither reaches `:2330` with a suspect second piece, so a regression that tested only `cue_words` would go unseen. The gap is real.
  - /fix decision: Applied (leg cx4). /fix notes: `desktop/tests/fixtures/answer_hops.py` (LF kept) gains `s-a-suspect-carried-piece-opens-nothing` right after `s-the-cue-routed-piece-is-the-question`: the same three lines, `suspect=(1,)`, `placed=((0, RED), (1, RED))`. `TestAnswerHop.test_the_case_places_its_lines` parametrises it, so that is one more test. `test_both_directions_are_exercised`'s joining set is unchanged: the case joins nothing, because its only uncued placed line (1) is the clinician's, which `_hop_joined` excludes. No other reader counts the cases (search). The re-read before writing agrees with leg cx3's evidence. Product unchanged; verification is the composer's gate. Pattern siblings: none named. /fix date: 2026-11-17. /fix applied by: Claude Code.
- PR-LOW-021 — original: LOW, test coverage, Fix-now.
  - `materiality=regression severity=LOW surface=test-harness rec=Fix-now (test-only, owed to the fix leg) — a partly covered reply is passed over by `_reply_turn`'s `wholly_uncovered` test, so the proposed assertion holds on the product as built.`
  - Evidence: `_reply_turn` (`ui/models.py:2824-2831`) adds a same-speaker, text-bearing segment only when `wholly_uncovered` (`note.py:1919-1925`: no word in `covered`), and walks on past one that is not. A reply with one covered word gets no credit, and a later uncovered line of the same turn stays credited. `test_the_whole_reply_turn_and_where_it_ends` (`test_validation_metrics.py:1707-1720`) quotes segment 2 wholly (`_note(document, 2, …)`), so a regression from "wholly uncovered" to "not wholly covered" would leave it green. `_note` takes any `Span`, so a partial span on segment 2 is expressible with the existing helpers. The gap is real.
  - /fix decision: Applied (leg cx4). /fix notes: `desktop/tests/test_validation_metrics.py` (CRLF kept: 5111 lines, every one CRLF) gains `TestReplyCredit.test_a_partly_quoted_reply_is_passed_over`, right after `test_the_whole_reply_turn_and_where_it_ends`. The question, the reply, "not since tuesday." and "maybe once."; the note quotes only word 0 of segment 2 (`(2, 0, 0)`) under the question's `clinician_line_omitted`. The test asserts `replies_after == {1, 3}`: segment 2 is passed over, its uncovered remainder included, and the turn runs on to 3. It uses the existing helpers only. Product unchanged; verification is the composer's gate. Pattern siblings: none named. /fix date: 2026-11-17. /fix applied by: Claude Code.
- No product defect: neither proposed test would fail on the current product, so neither is a MUST-PAUSE. Both are test additions for the fix leg (the two-leg peer shape's leg 2), after which the composer's gate and the next peer round re-check them.

Fix-delta self-check: PASS. I re-read the 2 applied hunks across 2 test files:
- The fixture case is well-formed and under 100 columns, and its name is unique among the cases.
- The new test's span is a valid `Span` (`(segment, first, last)`, as `test_a_partly_covered_line_is_not_credited` uses).
- The anchor run is segment 0 alone, since it ends with "?", and the question warning's words 0–4 match its five words.
- No product, other test or frozen file was touched.

Verification (recorded in leg cx5): the composer's gate over both fixes was green (`.cursor/loops/stage-2-cx4-gate.txt`): ruff "All checks passed!"; mypy "Success: no issues found in 67 source files"; pytest "10937 passed, 9 skipped in 498.91s (0:08:18)" (10935 plus the new fixture case and the new test, as expected); every return code 0.

### Round 18 — 2026-11-17
Composer-recorded (transcribed in leg cx5): from `.cursor/loops/stage-2-peer-r18.log`, its last `### Round 18` header to its `PEER-ROUND-18 RESULT` line; pass id `stage-2-h4b.p1` (slice B's confirmation of round 17's fixes); peer round 2 of cap 5. Transcribed verbatim below.

Source: Codex — codex gpt-6-astra medium — build peer review (stage-2-h4b.p1, peer round 2: slice B confirmation)
Status: Closed (0 pending)

Scope:

- job 1: checked PR-LOW-020 against the fixture, parametrised reader and S window. Confirmed fixed: `suspect=(1,)` marks the carried piece; the clean, comma-ended cue piece permits carrying it. S then checks `(cue_words, words)` and closes the window. Expected `placed=((0, RED), (1, RED))` is correct. Checking only the cue piece would join segment 2 and fail the exact placement assertion.
- job 2: checked PR-LOW-021 against the span helper and reply-credit definition. Confirmed fixed: `(2, 0, 0)` quotes only “not” from “not since tuesday.” Segment 2 is partially covered and therefore receives no credit; the turn continues to segment 3. Expected `{1, 3}` is correct. Crediting the uncovered remainder would add segment 2 and fail the assertion.
- job 3: checked the fix delta for weakened assertions, parametrisation, naming and registry compatibility. No new defect found. The fixture name is unique and automatically parametrised; its carried clinician line does not enter `_hop_joined`, so the joining registry remains correct. Exact assertions remain intact. Fixture LF and metrics-test CRLF are consistent; scoped `git diff --check` passed.

Findings: none.

Verification:

- 6 files read, including the complete fixture and scoped plan sections.
- 3 jobs evidenced.
- Static review only; no tests, scripts, network operations or writes performed. Matrix lint was not executed.

PEER-ROUND-18 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 19 — 2026-11-17
Round status: Closed
Source: Claude Code (`/review-loop` round 1 of cap 3, Phase D, executor leg dx1, stage-4)
Scope: Phase D's document diff (`git diff` of the 13 documents D.1–D.3 touch: the threat model, the data-flow map, the design system, the harness, shipping-gate and kept-recordings documents, the clinician review guide and the practice README, the pilot README, the release document, PLAN.md, the phase history and AGENTS.md), each new claim read against the code at `4a0081d`: `note.py` `generate_sections`, `_opens_answer_window`, `_question_routes_alone`, `_answer_is_clean`, `is_interrogative`, `_last_sentence_text`; `ui/models.py` `replies_after`, `_reply_turn`, `_flagged_run_ranges`, `flagged_segments`, `OMISSION_CODES`, `WARNING_COPY["clinician_line_omitted"]`, `flagged_count_line`; `validation.py` `encounter_metrics` (the reply-credit term, `reply_credit`'s default, the second computation), the amendment and set-report sentences and the residue line; `note_check.contradiction_warnings`; the tests `TestReplyCredit` and the `ANSWER_HOP_CASES` names; and against Tasks 0.2–0.6 and M.1's records. What was checked, each holding: the branch order (hop before carry; a join closes the carry's chain, a carry re-opens under S); the window's four opening conditions and G; the reply's conditions; QT's run, turn and cut; the chooser's `+m`; the harness credit's term, its suspect rule and its second computation only with a reference reading; Check 2 reading the note's quoted lines (so a joined line is compared); the draft strings quoted byte for byte; every figure against the plan's records; the test pins (`TestHarnessDocument`'s three rule sections untouched; `test_pilot_docs.py`'s id shape and lone-CR rules on `docs/pilot/README.md`); line endings (`git ls-files --eol`: no mixed file).

- **[LOW]** LOW-001: the threat model's reply-flag residue (c) and the harness document's simulation section gave the stay-out counts (2 / 9 / 3) as LINES, but Task 0.2's record says the unit is one per `absent` fact on a newly flagged line — Triage: Fix-now; Decision: Applied. Both now say "counted per fact that must stay out on a newly flagged line" (the harness: per `absent` fact). Applied by: Claude Code. /fix date: 2026-11-17.
- **[LOW]** LOW-002: the harness document's "Material facts in an uncued sentence" 0.3.7 sentence listed "a cue of its own" among what keeps a reply silent; a reply whose cue routes it is placed, not silent — Triage: Fix-now; Decision: Applied. Now "one the hop refuses: after a question guard G refuses, or holding a suspect word, a question of its own or a cue that routes it nowhere". Applied by: Claude Code. /fix date: 2026-11-17.
- **[LOW]** LOW-003: `docs/testing/kept-recordings.md`'s "From 0.3.7" named "Check reviews" only; the replay confirms every proposal, and Check 2 compares a confirmed proposal with every quoted line, a joined one included, so "Check errors" can rise too — Triage: Fix-now; Decision: Applied. Applied by: Claude Code. /fix date: 2026-11-17.
- **[LOW]** LOW-004: two precision qualifiers missing: the "clean by absence" first-reply finding and the one seen `hld-17` line rest on a phrase search (Task 0.6's record, "for the phrasings searched"), and `h6-01` f2 is S's case under the widest credit only — Triage: Fix-now; Decision: Applied. The threat model's residue (1) and the harness document's Known limit and simulation section now say so. Applied by: Claude Code. /fix date: 2026-11-17.

Fix-delta self-check: PASS. Each applied hunk re-read in context; no figure changed, only its unit or qualifier; line endings kept.

### Round 20 — 2026-11-17
Round status: Closed
Source: Claude Code (`/review-loop` round 2 of cap 3, Phase D, executor leg dx1, stage-4)
Scope: round 19's four fixes (Post-Fix Regression Check) and a second full read of the threat model's THE ANSWER HOP and THE REPLY FLAG paragraphs against the code. Round 19's fixes: all four confirmed, no regression.

- **[LOW]** LOW-005: the threat model's reply-flag residue (d) called AT "the whole-answer variant"; AT is the variant that follows ANY left-out clinician line (whole turn), not only a question, as Task 0.3 defines it; and residue (e) said "the next patient's reply turn is flagged" where it is flagged only after a flagged question — Triage: Fix-now; Decision: Applied. Both now say so; two over-long lines in residues (1) and (6) re-wrapped. Applied by: Claude Code. /fix date: 2026-11-17.

Fix-delta self-check: PASS (prose only).

### Round 21 — 2026-11-17
Round status: Closed
Source: Claude Code (`/review-loop` round 3 of cap 3, Phase D, executor leg dx1, stage-4)
Scope: round 20's fix confirmed, and the documents re-read for any claim the fixes made false. 0 findings. CONVERGED within the cap. Verification is the composer's gate (verify=composer): no Python was run by this leg but the history check, and no product code or test changed.

### Round 22 — 2026-11-17
Composer-recorded (transcribed in leg dx3): from `.cursor/loops/stage-4-peer-r22.log`, its last `### Round 22` header to its `PEER-ROUND-22 RESULT` line; pass id `stage-4-d4a.p1` (Task D.4's codex document pass, slice A); peer round 1 of cap 5. Transcribed verbatim below.

Source: Codex — codex gpt-6-astra medium — documents peer review (stage-4-d4a.p1, peer round 1: slice A security and design)

Status: Closed (0 pending)

Scope:
- job 1: checked THE ANSWER HOP and THE REPLY FLAG against the provider, chooser, Task 0.6 and SEC-001/SEC-002; rules and named residues match, including SEC-001’s acceptance dated 2026-11-17.
- job 2: checked the threat model’s restated Check 4, NEXT PATIENT, carry, correction, surface 3, suspect-reader, rollback and coverage-residue sentences; no contradictory claim found.
- job 3: checked changed flows 7, 10, 11, 17, 26, 27 and 29 against routing, metrics, prose, suggestions and replay code; no defect found. Historical measurement claims were checked against the permitted plan records; prohibited scratch files were not accessed.
- job 4: checked the design system’s flag reach, count-line wording and hint against `ui/models.py`; quoted copy matches, and approval dates match D.4.
- job 5: checked the slice for additional overclaims, stale current citations and formatting damage; none found. All three documents retain consistent CRLF endings; scoped `git diff --check` passed.

Findings: none.

Verification:
- Files read: 14, using scoped excerpts and diffs.
- Jobs evidenced: 5/5.
- Code baseline confirmed: HEAD `4a0081d`.
- Static review only; no scripts, suites, network commands or file writes.

PEER-ROUND-22 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 23 — 2026-11-17
Composer-recorded (transcribed in leg dx3): from `.cursor/loops/stage-4-peer-r23.log`, its last `### Round 23` header to its `PEER-ROUND-23 RESULT` line; pass id `stage-4-d4b.p1` (Task D.4's codex document pass, slice B); peer round 1 of cap 5. Transcribed verbatim below, then the executor's leg-1 verification and fix.

Source: Codex — codex gpt-6-astra medium — documents peer review (stage-4-d4b.p1, peer round 1: slice B testing, practice and project documents)
Status: Open (1 pending)

Scope:
- job 1: checked the metric amendment, five Known limits, simulation figures, M.1 result, SEC-001 acceptance and `TestHarnessDocument` section splits; consistent with the plan and HEAD implementation.
- job 2: checked both approved clinician-guide additions and the practice README against answer placement, ownership restrictions, reply flags and warning behavior; approval dates, plain-English wording and review banner retained.
- job 3: checked shipping, replay, pilot, rollback and project-document claims; found one incorrect replay expectation below. The ordinary assertion representation supports rollback compatibility; shadow mode and the no-run-10 decision remain consistent.
- job 4: checked the remaining scoped changes for inconsistent numbers, stale claims, prohibited pilot identifier shapes and formatting defects; no additional defect found. `git diff --check` passed.

Findings:
- **PR-LOW-040** (low, documentation correctness, `docs/testing/kept-recordings.md:68`): The answer hop cannot reduce “Sections missing”: it adds answers to a section already populated by the question that opened its window. The stated expected decrease could incorrectly excuse unrelated replay drift. Evidence: **“‘Sections missing’ can FALL”** and **“a section the reply alone fills in the clinician's saved note may now be present.”** At HEAD, `generate_sections` emits the cue-routed question before joining replies with `key = window_key`; `replay_kept.note_drift` measures only `len(_present_sections(saved) - _present_sections(note))`, not section content completeness. Recommendation: **Fix-now** — State that the answer hop leaves section presence, and therefore “Sections missing,” unchanged for identical replay inputs; reconcile the matching expectation in Task D.2.

Verification:
- Files read: 17 distinct scoped files.
- Jobs evidenced: 4/4.
- Finding verification: 1 candidate confirmed; 0 dropped; 0 downgraded.
- Static review only; no scripts, suites, network operations or writes performed.

PEER-ROUND-23 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 1).

Executor verification (leg dx3, leg 1 of the peer two-leg shape): PR-LOW-040 — `materiality=real severity=LOW surface=documentation rec=Fix-now` — CONFIRMED against the code. In `note.py` `generate_sections`, `window_key` is set only in branch (1) (a cue-routed line, which is then emitted into `key` by `whole_utterance_assertion`, reachable for every non-transparent line) and in branch (2) (the carry, which emits its piece into `prev_key`, the cue-routed line's own section); branch (4) assigns `key = window_key`, so every joined line lands in a section that the same note's cue-routed question already populated. Branch (3) only drops, and a join closes no carry that would otherwise happen (a carry needs the same speaker as the previous line, and a reply is never the clinician's). `replay_kept._present_sections` keys on `section.note_assertions` being non-empty, and `note_drift` counts `_present_sections(saved) - _present_sections(note)`, so the hop cannot change `sections_missing`. The code agrees with the finding (no MUST-PAUSE). Decision: Applied (`/fix`, documentation only). `docs/testing/kept-recordings.md`'s "From 0.3.7" first bullet now says "Sections missing" is unchanged by the hop, with a dated correction note (CRLF kept). Siblings reconciled (grep of the Phase D documents, AGENTS.md, PLAN.md, CHANGELOG.md and this plan for "Sections missing" / `sections_missing` / "can fall" / "may now be present"): this plan's Task D.2 record and Task 1.3's `replay_kept` reading each gain a dated correction line (left in place as the record of their time); no other document states the expectation (the threat model and flow 27 say only that the note numbers drift by design, still true through "Check reviews" and "Check errors"; kept-recordings.md's 0.3.3 and 0.3.5 "can fall" lines are about other columns). Applied by: Claude Code. /fix date: 2026-11-17. Fix-delta self-check: PASS (prose only; the bullet's other claims unchanged). Owed: one slice-B confirmation round (round 24, the composer's).

Verification (recorded in leg dx4): the composer's gate over leg dx3's fix and comment change was green (`.cursor/loops/stage-4-dx3-gate.txt`). Ruff: "All checks passed!". Mypy: "Success: no issues found in 67 source files". Pytest: 10937 passed, 9 skipped in 474.40s. Every return code was 0, so PR-LOW-040's fix and the comment change are gate-green.

### Round 24 — 2026-11-17
_Composer-recorded (leg dx4): transcribed verbatim from `.cursor/loops/stage-4-peer-r24.log`, from its last `### Round 24` header to its `PEER-ROUND-24 RESULT` line; pass id `stage-4-d4b.p1`, peer round 2 of cap 5 (slice B's confirmation of leg dx3's fix delta). Escape-check clean; refs unchanged._

Source: Codex — codex gpt-6-astra medium — documents peer review (stage-4-d4b.p1, peer round 2: slice B confirmation)
Status: Closed (0 pending)

Scope:

- job 1: checked PR-LOW-040 and its executor verification against `note.py:2375–2448` and `replay_kept.py:281–359`; correction is true. Replies use `key = window_key`, whose section already holds the question; missing sections count presence only.
- job 2: checked Task 1.3 and Task D.2; both retain their historical wording with explicit dated corrections stating that `sections_missing` is unchanged. Neither leaves the old expectation current.
- job 3: searched the specified Phase D documents for section-missing claims and decrease variants; no remaining current sibling found. The `ui/models.py` diff changes two comments only: no executable code, strings or line-ending conversion.
- job 4: checked the fix delta for stale claims and formatting damage; none found. `git diff --check` passed. Kept-recordings and models remain uniformly CRLF; the plan remains uniformly LF, without stray carriage returns.

Findings: none.

Verification:

- Files read: 6 distinct files through targeted reads, diffs or matching excerpts; additionally searched the specified document corpus.
- Jobs evidenced: 4/4.
- Static review only; no scripts, suites, network operations or writes performed.

PEER-ROUND-24 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 25 — 2026-11-17
_Composer-recorded (leg px2): transcribed verbatim from `.cursor/loops/stage-6-peer-r25.log`, from its last `### Round 25` header to its `PEER-ROUND-25 RESULT` line; pass id `stage-6-p5.p1`, peer round 1 of cap 5 (the close documents of leg px1). Escape-check clean; refs unchanged._

Source: Codex — codex gpt-6-astra medium — close documents peer review (stage-6-p5.p1, peer round 1)
Status: Closed (0 pending)

Scope:

- job 1: checked P.3, leg px1 and the install-record updates; the reported decision, normal-terminal verification, four smoke checks and discarded first take agree. No clinical content or real recording identifiers added.
- job 2: checked F-155, F-170 and F-171 against the register rules, test vocabularies, Task 0.6 and M.1; cells conform, claims match the records, and the omitted residue rows have explicit retained dispositions consistent with the close’s measurement scope.
- job 3: checked AGENTS.md, CHANGELOG.md, pilot-builds.md and phase-history.md; current install records identify 0.3.7 on 2026-11-17 with shadow mode on. The historical paragraph was moved faithfully; historical install statements remain distinguishable. D.4 approval and no rule v7 / heldout-7 / run 10 agree with the plan.
- job 4: checked lifecycle, completion, task markers, 0.8, P.5, retained items and both suggestion-repair reconciliation notes; 23 kept tasks are complete, five tasks remain explicitly NOT BUILT, and outstanding deletion, commit and push work is retained. No broken table or whitespace defect found.

Findings: none.

Verification:

- 9 scoped files read; 4 jobs evidenced.
- HEAD confirmed as `5e83b4a`; scoped `git diff --check` passed.
- Static review only; no scripts, suites, network commands or writes performed.

PEER-ROUND-25 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

## Tasks

### Phase 0 — The simulation and the decision (no product change; C2)

- [x] 🟩 **0.1 The synthetic scratch and its premise.** DONE 2026-11-15 at `22feec4` (the scratch written in executor leg ax1, run by the composer): text mode's premise holds with 0 mismatches on all seven sets (`afq-measure.py --self-test`: `scripts` 50, `heldout` 22, `heldout-2` 22, `heldout-3` 23, `heldout-4` 22, `heldout-5` 22, `heldout-6` 22 encounters; note, metrics, reference reading, credit mirror and errors all 0; `PREMISE mismatches total: 0`). `heldout-3` has 23 scripts, not the 22 leg ax1's handoff expected. The replay premise stays Task 0.3's.
  - Files (new, git-ignored): `.cursor/loops/afq_lib.py` (the D1 rule as a provider subclass with reach V1 / V3 / V4, guard G on or off, switch S, and V4t for text mode; `replies_after` with D4's four sub-variants; the counters), `.cursor/loops/afq-transcribe.py` (from `run8-p3-transcribe.py`: `RULES` rule v6, the seven sets, its `:142-144` dropped; one pickle per encounter), `.cursor/loops/afq-measure.py` (text mode over `validation.reference_document`; `--docs` over the saved pickles; prints ids, counts and section keys only), outputs under `.cursor/loops/afq-out/`.
  - Follows: the simulation recipe in Codebase Integration Notes; D1, D2, D4.
  - Behaviour once done: with no hop and the shipped credit, the scratch reproduces the shipped outcome.
  - Done when: text mode's equality holds on all seven sets (0 mismatches), recorded here with the commit. The replay premise is Task 0.3's.
  - The executor writes; the composer runs (C7; the executor runs no Python).
- [x] 🟩 **0.2 The self-test at text level.** DONE 2026-11-15 at `22feec4` (the composer's run: `afq-measure.py --text --per-encounter --config validation/config`, exit 0, 72 s; `.cursor/loops/afq-text-1.txt`, `afq-out/text-summary.md`, `afq-out/text/`).
  - Run `afq-measure.py` in text mode over the seven sets with `--config validation\config`.
  - Record here (ids and counts only): silent facts before (expected 25 on `heldout-2`, 26 on `heldout-6`, 0 elsewhere); V1 recovered (expected 11) and V4t recovered (expected 17) with what each quotes that must stay out (expected: V4t `hld-17`; V1 without G `h5-18` line 3; with G to be read); joins per set.
  - Done when: each expected count is reproduced, or the difference is explained on this task (the planning counts were estimates). This is a self-test, not a decision table.
  - Recorded (shipped credit unless named; ids, script-line numbers and counts only):
    - Silent facts before (no hop): `heldout-2` 25 (14 failing encounters), `heldout-6` 26 (16 failing), 0 on the other five. As expected.
    - V1 recovered 11 (`heldout-2` 3: `h2-09` 3 → 1, `h2-18` 4 → 3; `heldout-6` 8: `h6-01` 2 → 1, `h6-02` 2 → 0, `h6-04` 2 → 0, `h6-08` 3 → 2, `h6-09` 1 → 0, `h6-21` 2 → 1; `h6-19` joins once and stays at 2). V1g the same 11. As expected. V3 / V4 (G off or on) recover 14 (`heldout-2` 6, `heldout-6` 8); V3 is equal to V4 on every set.
    - V4t recovered 17 (`heldout-2` 8, `heldout-6` 9, the ninth `h6-16` 3 → 2). As expected.
    - Quoted that must stay out (material / not): V4t `hld-17` line 2 (material), `hld-18` line 5 (not) and `h5-18` line 3 (not); V1, V3 and V4 without G `h5-18` line 3 (not material) only; with G (V1g, V3g, V4g) none. The expected `hld-17` and `h5-18` line 3 reproduce; the two others are V4t's own, outside the planning list, which named only the material one. G removes `h5-18`'s quote, the case it was written for.
    - Joins per set (V1 / V1g / V3 / V3g / V4 / V4g / V4t): `scripts` 7 every form (`syn-09`, `syn-10`, `syn-13`, `syn-24` twice, `syn-29`, `syn-40`); `heldout` 2 every reach (`hld-15`, `hld-22`), V4t 11; `heldout-2` 2 / 2 / 4 / 4 / 4 / 4 / 9; `heldout-3` 0, V4t 2 (`h3-07`, `h3-12`); `heldout-4` 0, V4t 1 (`h4-12`); `heldout-5` 3 without G, 2 with G (`h5-12`, `h5-17`; `h5-18` the one G stops), V4t 5 (adds `h5-02`, `h5-16`); `heldout-6` 8 / 8 / 9 / 9 / 9 / 9 / 11. At most 2 joins per encounter (V4t 3 on `heldout`).
    - Read beside them, all 0 on every set and form: newly silent facts, next-patient joins with no boundary found, new unsupported clinical lines, new error-grade warnings, new checker failures, sets pushed over R3, the 50 newly failing, carries after a join, joins across a wordless segment, label disagreements, S candidates. Review marks on hop lines: `scripts` 1, `heldout` 1 (V4t 3), `heldout-2` 0 (V4t 2), `heldout-5` 1, `heldout-6` 3 (V1) / 4 (V3, V4) / 5 (V4t), else 0.
  - Against the planning estimates (Accepted Assumptions, "The planning cross-checks are estimates"):
    - "Join plus credit leaves about 6–12 silent facts on `heldout-2` and 1–4 on `heldout-6`": V1 (G off or on) leaves 6 (QT, AT) to 12 (Q1, A1) on `heldout-2` and 1 (AT) to 4 (Q1) on `heldout-6`, inside both. V3 / V4 leave 3–9 on `heldout-2` (1–4 on `heldout-6`), below the low end: the estimate was the first-line reach's, and the wider reach joins 2 more lines on `heldout-2` (3 more facts).
    - "`h5-18` line 3 is quoted by the first-line rule": reproduced (not material), and G stops it.
    - "The reply flag lands on about 17 (questions only) to 39 (any clinician line) lines that must stay out". REPLACED 2026-11-16 from `.cursor/loops/afq-text-2.txt`, after peer round 7 PR-MED-012. The column now subtracts the chooser's shipped `[flagged]` mark, `ui.models.flagged_segments`. The first reading (17, 18, 39, 40 from `afq-text-1.txt`) subtracted only the harness credit, so it counted lines already flagged by a patient's own `high_risk_omission` anchor.
      - Corrected, summed over the seven sets with no hop: Q1 8, QT 8, A1 19, AT 19. Of the A1 19, 10 are material and 8 sit at or after the reference tail.
      - Per set, Q1; A1, material / other / tail (QT equals Q1 and AT equals A1 on every set): `scripts` 0/5/0; 3/5/0 — `heldout` 0/0/0; 0/0/0 — `heldout-2` 0/0/0; 1/1/1 — `heldout-3` 1/0/1; 2/1/2 — `heldout-4` 1/1/2; 1/1/2 — `heldout-5` 0/0/0; 2/0/2 — `heldout-6` 0/0/0; 1/1/1.
      - Extra flagged lines with no hop, Q1 / QT / A1 / AT: `scripts` 7 / 7 / 11 / 11; `heldout` 1 / 1 / 3 / 3; `heldout-2` 5 / 9 / 14 / 18; `heldout-3` 5 / 5 / 18 / 18; `heldout-4` 6 / 6 / 24 / 24; `heldout-5` 4 / 5 / 17 / 18; `heldout-6` 8 / 10 / 23 / 25.
      - Against the estimate: the corrected counts are about half of it. The first reading matched the estimate exactly (17 and 39), so the planning cross-check most likely made the same subtraction.
      - The unit is one per `absent` fact on a newly `[flagged]` line, not distinct lines; Task 0.5's review checks it.
      - `afq-text-2.txt` differs from `afq-text-1.txt` in these two columns only (none rose) and the per-encounter lines' added `np=` (0 throughout), as the composer compared.
    - Not exercised at text level (the reference document has no recogniser splits, no wordless segments and labels taken from the script): S (0 candidates), the carry after a join (0), joins across a wordless segment (0) and label disagreement (0). Task 0.3 reads them at audio level.
  - The text-level D8 section in the output (harm line met only by `none` and the three G forms; no form gate-capable; the mechanical shortlist V3g, V4g, V1g at 4, 4 and 7 silent on `heldout-2` + `heldout-6` under AT) is a self-test reading on the scripts' own words, at most an upper bound on what audio level can show; D8 is read at Task 0.6 on Task 0.3's audio-level numbers, and nothing here is decided.
- [x] 🟩 **0.3 The audio-level tables.** DONE 2026-11-16 at `22feec4`, whisper `medium`, `C:\afq-sets\`. The off part was recorded 2026-11-15. The finalists' gate-configuration lines and each D8 line's met / not met come from `afq-gate-2.txt` (leg ax6); the two flagged columns from `afq-gate-3.txt` (leg ax7). All are below.
  - Build the seven sets into `C:\afq-sets\<set>` (voices checked first), transcribe each once with `afq-transcribe.py` (each script's clinician enrolled), keep the built folders.
  - Premise: the replay equals each pickled outcome (0 mismatches), and the baseline rows equal `stage-2-c6-off-<set>.md` (and `stage-4-f1-off-heldout-2.md`) with the Rule column masked; if transcript cells differ, re-transcribe that set once and record it. `heldout-6` has no off baseline: record its row.
  - Tables, per set (off, no prose): (1) the join table — V1 / V3 / V4, each with G off and on (V3 printed only where it differs from both): silent facts and failing encounters after, facts recovered, lines that must stay out quoted (material / not), next-patient joins with no boundary found, new unsupported clinical lines, new review marks and new error-grade warnings, joins per encounter, joins across a wordless segment, joins whose reply label disagrees with the label track, carries after a join; (2) the S counter (windows only S would open); (3) the credit table — D4's four sub-variants: facts credited, extra flagged lines, lines that must stay out newly flagged (material / not / at or after the reference tail).
  - The shortlist, mechanical: rank the six forms (three reaches, G off and on) that meet D8's harm line at off by the fewest silent facts on `heldout-2` + `heldout-6` at off under the widest credit (any clinician line, whole turn); ties go to the smaller reach, then to G on. The top three are the finalists; S is added to each if D2's condition holds. If no form meets the harm line at off, the one with the least harm is the only finalist, ordered by, in turn: material lines that must stay out quoted; non-material ones; new unsupported clinical lines; new error-grade warnings and checker failures; sets pushed over their next-patient ceiling; the 50 failing; then the smaller reach, then G on.
  - Each finalist form is composed once in the gate configuration over the saved documents (one model pass; planned as about an hour for the seven sets, measured at about eight on this laptop, 2026-11-16). From that one composed note the metric walk is repeated for each of D4's four credit sub-variants and for the chooser's wider predicate (the recipe's re-invocation), so every credit configuration has its full D8 lines, with the join-only figures beside.
  - Done when: the tables are on this task with the commit, the whisper model and the folder; each D8 line is marked met or not met per finalist.
  - Recorded, off and no prose (ids and counts only; every table at commit `22feec4`, whisper `medium`, built and saved under `C:\afq-sets\`; the composer's runs, logs `.cursor/loops/afq-build-<set>.txt`, `afq-transcribe-<set>.txt`, `afq-replay-premise-1.txt`, `afq-docs-1.txt`, `afq-baseline-diff-1.txt`):
    - Built: voices 0 David, 1 Hazel, 2 Zira as the baseline; each set "built N encounter(s); 0 error(s)" (50, 22, 22, 23, 22, 22, 22) into `C:\afq-sets\<set>`. Transcribed once each with `afq-transcribe.py` (19:57–21:41), pickles in `C:\afq-sets\docs\<set>`; every set exit 0, no `[error]`, `[custody]` or `[refused]` line; rule v6 PASS on `scripts` and `heldout-3`, FAIL on the other five.
    - Replay premise: 0 problems on all seven sets (encounters 50, 22, 22, 23, 22, 22, 22; incomplete, missing pickles, errors and mismatches all 0).
    - Baseline: each set's no-hop report (`afq-out/docs/<set>/report-none-rule-v6.md`) against `stage-2-c6-off-<set>.md`, and `heldout-2` also against `stage-4-f1-off-heldout-2.md` (CR stripped, `[run ]` lines dropped, rule names masked), checked line by line. The only differing lines are the title and verdict lines (rule v5 → v6 wording; the gate-set list `heldout-5`, `scripts` → `heldout-6`, `scripts`; `heldout-5` "a gate set" → "a reported set"), the run paragraph (the commit; rule v6's added sentence; `heldout-5`'s "this set reports them" → "counts them under the ceiling"), the residue-class heading and the "After the classes" line's wording (its counts equal), and on `heldout-5` alone the residue-class R1 row (0 → 1, "R1: none" → "R1: `h5-01/f4`", "reported, no ceiling" → "counted under the ceiling"). That row is rule v6's set schedule by design (`heldout-5` now counts its one marked R1, the same `h5-01/f4`, under its ceiling; the same FAIL on `h5-17`). No per-encounter table cell and no count differs, so no set is re-transcribed. The failing-encounter lists are equal on every set. `heldout-6` has no off baseline; its row: rule v6 FAIL, 17 failing encounters (16 on silent omission; `h6-13` material wrong only), silent facts 26, material wrong 2 (raw 5), uncertainty missed 0 (raw 7), one unsupported clinical line (`h6-09`), R3 1 / 1.
    - (1) The join table, shipped credit (G on or off gives the same counts on every set; it changes only the windows opened on `heldout-6`, 14 → 13). V1 / V3 / V4:
      - `heldout-2`: silent 25 → 22 / 22 / 19 (failing 14 → 14 / 14 / 13); recovered 3 / 3 / 6 (`h2-09` 3 → 1, → 0 under V4; `h2-18` 4 → 3, → 1 under V4; `h2-11` joins once and stays at 1); joins 6 / 8 / 11; carries after a join 2 / 0 / 0; review marks on hop lines 1.
      - `heldout-6`: silent 26 → 21 / 20 / 20 (failing 16 → 15 / 14 / 14); recovered 5 / 6 / 6 (`h6-02` 2 → 1, → 0 under V3 and V4; `h6-04` 2 → 0; `h6-08` 3 → 2; `h6-09` 2 → 1; `h6-01` and `h6-19` join and stay at 2); joins 7 / 13 / 17; carries 5 / 1 / 0; review marks on hop lines 1 / 3 / 4.
      - The other five (silent 0 before and after): joins `scripts` 10 / 13 / 13, `heldout` 6 / 9 / 9, `heldout-3` 3 / 4 / 4, `heldout-4` 3 / 4 / 4, `heldout-5` 4 / 7 / 7; carries under V1 2, 3, 1, 1, 3 (0 under V3 and V4); review marks on hop lines 4, 1, 0, 0, 2.
      - Next-patient joins with no boundary found: 1 on `scripts` under every form, none elsewhere. `scripts` stays PASS with R3 2 / 2 as at no hop. The encounter is not named by this run's per-encounter line; the line names it from leg ax3 on (`np=`).
      - 0 on every set and form: lines that must stay out quoted (material / not), newly silent facts, new unsupported clinical lines, new error-grade warnings (0 also under round 5 MED-001's strict count: the re-run `afq-docs-2.txt` differs from `afq-docs-1.txt` only in its timing cells), new checker failures, joins across a wordless segment, replies labelled the clinician, questions labelled another speaker. Joins per encounter: median 0 on every set; maximum 2 under V1, up to 3 under V3 (4 on `scripts`), and under V4 4 on `scripts` and `heldout-2` and 5 on `heldout-6`. Every set's rule v6 verdict is unchanged by every form.
    - (2) The S counter: S candidates (windows only S would open) `heldout` 4, `heldout-2` 1, `heldout-3` 1, `heldout-4` 1, `heldout-6` 1, else 0, the same under every form. Only `heldout-6`'s has an S-only hop line, and it holds one silent material fact under the widest credit, `h6-01:f2`. D2's condition (a silently lost material fact on any set on a reply only an S window reaches) therefore holds, and S is added to each finalist. The composer's reading is confirmed.
    - (3) The credit table, D4's four sub-variants (silent facts / failing encounters on the gate pair; `+m` equals its base at off, where no clinician Add exists):
      - `heldout-2`: no hop Q1 20 / 11, QT 10 / 4, A1 20 / 11, AT 9 / 3; V1 and V3 (G either) 17 / 11, 7 / 4, 17 / 11, 6 / 3; V4 (G either) 14 / 9, 4 / 2, 14 / 9, 3 / 1. Facts credited 5, 15, 5, 16.
      - `heldout-6`: no hop Q1 23 / 14, QT 15 / 11, A1 22 / 14, AT 10 / 8; V1 18 / 13, 10 / 9, 17 / 13, 5 / 5; V3 and V4 17 / 12, 9 / 8, 16 / 12, 4 / 4. Facts credited 3, 11, 4, 16.
      - The two flagged columns, REPLACED 2026-11-16 from `.cursor/loops/afq-docs-3.txt` (peer round 7 PR-MED-012: they now subtract the chooser's shipped `[flagged]` mark, `ui.models.flagged_segments`, not the harness credit). Against `afq-docs-2.txt` only these two columns and the timing cells changed, and none rose (the composer's comparison, 329 cells). The silent, failing and facts-credited counts above and the shortlist do not read them and stand. Both are equal under every form, as before.
        - Extra flagged lines, Q1 / QT / A1 / AT: `scripts` 7 / 21 / 16 / 33; `heldout` 2 / 3 / 7 / 11; `heldout-2` 10 / 32 / 23 / 58; `heldout-3` 6 / 12 / 25 / 53; `heldout-4` 10 / 16 / 30 / 53; `heldout-5` 5 / 16 / 26 / 59; `heldout-6` 9 / 30 / 34 / 81.
        - Lines that must stay out newly `[flagged]`, material / other / at or after the reference tail (one per `absent` fact on a newly flagged line), Q1; QT; A1; AT:
          - `scripts` 0/2/0; 0/5/0; 3/2/0; 3/5/0
          - `heldout` 0/0/0 under all four
          - `heldout-2` 0/1/0; 0/1/0; 0/1/0; 2/3/2
          - `heldout-3` 0/0/0; 0/0/0; 0/0/0; 2/1/2
          - `heldout-4` 1/1/2 under all four
          - `heldout-5` 0/1/0; 1/1/1; 1/1/1; 4/2/4
          - `heldout-6` 0/0/0; 1/1/1; 0/0/0; 3/2/3
        - Over the seven sets: 6 (1 material), 12 (3), 10 (5), 29 (15). The first reading gave 10, 21, 20 and 52. At text level the corrected column gives 8, 8, 19 and 19 (Task 0.2); audio level reorders them because the recogniser's runs differ from the script's lines.
    - The shortlist, mechanical: all six forms meet D8's harm line at off (0 lines that must stay out quoted, no new unsupported line, error-grade warning or checker failure, the 50 pass, no set over its next-patient ceiling). Ranked by silent facts on `heldout-2` + `heldout-6` under AT: V4g 7 (3 + 4), V4 7, V3g 10, V3 10, V1g 11, V1 11. V4g and V4 tie and share a reach, so G on ranks V4g first. Finalists: V4g, V4 and V3g, each with S (condition above): V4gs, V4s, V3gs. Their gate-configuration run (`--gate --forms V4gs,V4s,V3gs`): `afq-gate-1.txt` (21:46, the old net error count) was stopped as obsolete. `afq-gate-2.txt` (started 22:00, round 5's counter, the old flagged reading) is the record for the D8 lines. `afq-gate-3.txt` is the record for the two flagged columns; it equals gate-2 in every other cell. Each run takes about eight hours, not one.
    - The gate configuration, recorded 2026-11-16 (leg ax6) from `.cursor/loops/afq-gate-2.txt`:
      - Run: the composer's gate run of the three finalists (suggestions confirm-all and prose) over the saved documents. Commit `22feec4`, whisper `medium`, `C:\afq-sets\`. Started 2026-11-15 22:00, ended 2026-11-16 05:56:39, exit 0, 513 lines. Set times (s): 6075, 3274, 4252, 4129, 3411, 3707, 3749, about 7.9 h in all.
      - Round 5's error counter. `afq-gate-2.txt` ran before PR-MED-012, so its two flagged columns ("Extra flagged lines", "Stay-out newly flagged") were the old reading, an upper bound. The practitioner chose to re-run: "Rerun now, 0.4b waits" (2026-11-16, in chat).
      - The re-run, `.cursor/loops/afq-gate-3.txt` (recorded 2026-11-16, leg ax7), is the record for the two flagged columns under (3).
        - It ran at HEAD `22feec4`, whisper `medium`, `C:\afq-sets\`, with the same three forms and `--config validation/config`, round 5's counter and the PR-MED-012 flagged reading. It started 05:56:43, ended 13:49:47 and exited 0; 513 lines.
        - Set times (s): 5997, 3251, 4234, 4102, 3409, 3701, 3687.
        - The composer's column comparison against `afq-gate-2.txt` gives the same 513 lines and 375 changed cells. All 375 are in the two flagged columns, and none rose. The other changes are the seven "Seconds" cells. Every other line and cell is identical, including the per-encounter lines and the D8 lines.
        - So every count above and below other than the flagged columns reads the same from either file.
      - Replay premise in this configuration: 0 problems on all seven sets (incomplete, missing pickles and errors 0; mismatches not compared here, since the pickles hold the off outcome).
      - (1) The join table, shipped credit, V4gs / V4s / V3gs:
        - `heldout-2`: silent 25 → 19 / 19 / 19 (failing 14 → 13 / 13 / 13); recovered 6; joins 11 / 11 / 8; review marks on hop lines 1. `h2-09` 3 → 0 / 0 / 1; `h2-18` 4 → 1 / 1 / 0; `h2-11` stays 1.
        - `heldout-6`: silent 24 → 19 / 19 / 19 (failing 15 → 14 / 14 / 14); recovered 5; joins 18 / 18 / 14; carries 0 / 0 / 1; review marks 4 / 4 / 3. `h6-01` 2 → 1, `h6-04` 2 → 0, `h6-08` 3 → 2, `h6-09` 2 → 1; `h6-19` stays 2.
        - The no-hop baseline here is not the off one: `heldout-6` 24 silent over 15 failing (26 and 16 at off), because the suggestion stage itself recovers two.
        - The other five, silent 0 before and after: joins `scripts` 13, `heldout` 9, `heldout-3` 4, `heldout-4` 4, `heldout-5` 7, the same under all three; review marks 4, 1, 0, 0, 2.
        - Next-patient joins with no boundary found: 1 on `scripts`, now named, `syn-38` (all three forms). `scripts` stays PASS with R3 2 / 2.
        - Lines that must stay out quoted, material / other: `heldout-5` 1 / 0 (`h5-17` line 15, material, all three forms; diagnosis below), 0 / 0 elsewhere.
        - 0 on every set and form: newly silent, new unsupported, new error-grade (strict count), new checker failures, joins across a wordless segment, label disagreements. Every set's rule v6 verdict is unchanged by the hop.
        - `heldout-3`, `heldout-5` and `heldout-6` read R3 2 / 1 already with no hop in this configuration, against 1 / 1 at off (`afq-docs-3.txt`). The suggestion stage is the only stage that differs between the two no-hop runs and could move it: the prose stage only counts sections. None is pushed over by a finalist.
      - (2) The S counter: 0 S candidates, 0 S-only hop lines and 0 silent material facts on them, on every set and finalist. S is on in all three finalists. Windows opened (V4gs / V4s / V3gs): `scripts` and `heldout` 36, `heldout-2` 20, `heldout-3` 21, `heldout-4` 18, `heldout-5` 18, `heldout-6` 14 / 15 / 14.
      - (3) The credit table on the gate pair, silent / failing (`+m` gives the same silent and failing counts as its base on every row):
        - `heldout-2`, no hop: shipped 25 / 14, Q1 20 / 11, QT 10 / 4, A1 20 / 11, AT 9 / 3. V4gs and V4s: 19 / 13, 14 / 9, 4 / 2, 14 / 9, 3 / 1. V3gs: 19 / 13, 15 / 10, 5 / 3, 15 / 10, 4 / 2. Facts credited (Q1, QT, A1, AT): V4 5, 15, 5, 16; V3gs 4, 14, 4, 15.
        - `heldout-6`, no hop: 24 / 15, 21 / 13, 13 / 10, 20 / 13, 8 / 7. All three finalists: 19 / 14, 16 / 11, 8 / 7, 15 / 11, 3 / 3. Facts credited 3, 11, 4, 16.
        - The two flagged columns, from `afq-gate-3.txt` (PR-MED-012's reading). Extra flagged lines are given under Q1 / QT / A1 / AT, with `+m` in brackets where it differs. Then stay-out newly flagged, as material / other / at-or-after the tail, under Q1, QT, A1 and AT (`+m` equal on every row). No hop and the three finalists are equal unless named:
          - `scripts`: 7 / 21 / 16 / 33; 0/2/0, 0/5/0, 3/2/0, 3/5/0.
          - `heldout`: 2 / 3 / 7 / 11; 0/0/0 under all four.
          - `heldout-2`: no hop, V4gs and V4s 10 / 32 / 22 (23) / 55 (58); V3gs 9 / 31 / 21 (22) / 54 (57). All read 0/1/0, 0/1/0, 0/1/0, 2/3/2.
          - `heldout-3`: 5 / 9 / 23 (24) / 45 (49); 0/0/0, 0/0/0, 0/0/0, 2/1/2.
          - `heldout-4`: 8 / 12 (13) / 26 (28) / 44 (50); 1/1/2 under all four.
          - `heldout-5`:
            - no hop 5 / 16 / 21 (25) / 51 (57), with 0/1/0, 1/1/1, 0/1/0, 3/2/3;
            - the finalists 5 / 15 / 21 (25) / 50 (56), with 0/1/0, 0/1/0, 0/1/0, 2/2/2.
          - `heldout-6`: no hop 9 / 30 / 31 (34) / 75 (80); the finalists 9 / 30 / 32 (34) / 78 (80). All read 0/0/0, 1/1/1, 0/0/0, 2/2/2.
          - Against `afq-gate-2.txt`'s old reading, every cell fell or stayed equal; for example, AT on `heldout-6` fell from 107 to 78 for the finalists.
      - D8, per finalist and per line, exactly as the scratch reads D8 (its "D8 across the sets" table); D8 decides nothing here (Task 0.6):
        - Harm: 0 lines that must stay out quoted — NOT met by V4gs, V4s or V3gs under any credit (1 material, `h5-17` line 15; met by every no-hop row). No new unsupported clinical line — met (0). No new checker failure and no new error-grade warning — met (0). The 50 still pass — met (0 newly failing). No set pushed over its rule-v6 next-patient ceiling — met (0 pushed).
        - GATE-CAPABLE (0 encounters failing on silent omission on both `heldout-2` and `heldout-6`): not met by any configuration. The fewest are V4gs and V4s under AT, 1 and 3 failing.
        - IMPROVEMENT (silent at least halved on each gate set against the same run's no-hop, 25 and 24): met for all three finalists under QT, QT+m, AT and AT+m (V4gs and V4s QT 4 / 8, AT 3 / 3; V3gs QT 5 / 8, AT 4 / 3). Not met under shipped, Q1, Q1+m, A1 or A1+m. With no hop, the reply credit alone meets it under AT and AT+m (9 / 8) and under no other credit.
        - Real speech: UNMEASURED (Task 0.4b, 2026-11-17: both passes COMPLETE, n enrolled 2 < 3). Any building exit needs the practitioner's explicit, named override.
        - Reported with no threshold: the two flagged columns, above from `afq-gate-3.txt`. They change no D8 reading, since D8 sets no threshold on them and gate-3's D8 lines equal gate-2's.
        - The "don't write this down" first-reply check, settled 2026-11-17 (leg ax9, Task 0.5):
          - The search: a case-insensitive phrase search over every script under `validation/` (the seven sets), for "don't / do not / please don't / no need to" with "write / put / record / note" and "this / that / it", plus "off the record" and "leave that / this / it out of".
          - It finds one line, `hld-17` line 2. That line is the patient's SECOND line after the clinician's question at line 0, with the patient's line 1 between them, so it is not a first reply. It is the `absent` material fact that V4t quoted at text level (Task 0.2).
          - No finalist quotes it: `heldout` reads 0/0 quoted, and 0/0/0 stay-out newly flagged under every credit, both at off and in the gate configuration.
          - So D8's "clean by absence" holds for the phrasings searched. A request worded otherwise would be missed by the search.
      - The `h5-17` line-15 quote, diagnosed from code and the synthetic script (`validation/heldout-5/h5-17.json`, not blind since validation-run8 P.3):
        - What line 15 is: the next patient's line, after the clinician's greeting at line 14. Its only fact is `absent` and material, and the script's last fact.
        - The hop's joins are the same two segments (6 and 7) at off and here. That is in the projections (`afq-out/docs/heldout-5/V4g.json` and `afq-out/gate/heldout-5/V4gs.json`, `h5-17` `joined`), and the off run quotes nothing. So line 15 is not quoted on a joined line.
        - What differs is the suggestion stage. Under `--suggestions confirm-all` the harness asks the suggestions from the draft and adds every accepted line before the one finalisation (`validation.py:3376-3387`). The prose stage runs on the finished note and only counts sections (`:3388-3394`), so it cannot change a fact's verdict.
        - Line 15's fact reads `wrongly_present` in the variant's note and not in the same configuration's no-hop note. The joins are identical to off's, and off quotes nothing; the prose stage cannot move a verdict. The one stage left that differs is the suggestion pass, asked over a draft that the joins on segments 6–7 have changed. That is an inference by elimination; no suggestion's text or line numbers are read here. The same encounter's facts 1–3, on clinician lines 7, 8 and 9, read `correct` here against `omitted` (warned) at off.
        - Not a scratch defect: the plan's recipe defines harm as the per-fact verdict difference between the no-hop and the variant run in the same configuration, for every `absent` fact (Review Findings Log PR-HIGH-001), and the scratch counts exactly that. It does attribute to the hop an effect that reaches the note through the suggestion stage.
        - D8's harm line says "quoted on a joined line", so the two readings part here. This is a named harm residue for the practitioner's word at Task 0.6: "an indirect next-patient quote through the suggestion stage". D8 already allows it: NO-GO "unless the practitioner, shown the table, accepts a named residue". The same class is register F-155–F-169's suggestion-stage next-patient additions, and F-132's cross-patient class.
- [x] 🟩 **0.4a The real-speech script, reviewed before it runs** (C1, C5). DONE 2026-11-16.
  - Built in leg ax3 (2026-11-15): `afq-measure-kept.py`, which per document calls `afq_lib.measure_document`; that function counts with `note_counters` and checks the no-hop note against the shipped provider's. It has a `--dry-run-docs` mode, and the two documents are edited (CRLF kept).
  - Review converged: `/review-loop` rounds 5–6 (2 MED and 4 LOW), then the codex slice, round 7 (2 MED and 1 LOW). All were verified and applied (Review Findings Log).
  - The composer's checks, after round 7's fixes, with the files unchanged since (last modified 2026-11-15 22:09):
    - `py_compile` of the four scratch files: exit 0.
    - The dry run over the synthetic pickles (`.cursor/loops/afq-kept-dry-2.txt`): `[dry-run] synthetic saved documents: 183`, expected 183, measured 183, failed 0, `COMPLETE`, exit 0. Against the pre-round-7 dry run (`afq-kept-dry-1.txt`, also `COMPLETE` 183 / 183, exit 0), the 549 per-ordinal rows differ only in the four "extra flagged" columns, none rising (PR-MED-012). Every other line is identical.
    - The refusal smoke with no `--enrolment`: `[refused] --enrolment is required (give the path to your enrolment WAV)`, exit 2.
    - The two PR-MED-011 smokes, a nonexistent `--config` on the measuring run and on the dry run: each `[refused] --config: not an existing folder (give the config folder for this pass)`, exit 2.
  - SHA-256 (the files Task 0.4b runs):
    - `98dd3d3ee1c9622bcaaff85f1856fb0a1dd381140ae56d42c575704ee7f47643` `.cursor/loops/afq-measure-kept.py`
    - `cbd991620f940e60b7da394bdc37050f2537749eb38afa7155739274b9fc2138` `.cursor/loops/afq_lib.py`
  - Files (new, git-ignored): `.cursor/loops/afq-measure-kept.py`, modelled on `run7-measure-kept.py`: `--list` (decrypts nothing; prints n); `--enrolment <WAV>` required; `--config <folder>` required; the refusal order of `replay_kept.py:576-647` (dev channel, enrolment, folder, entries, the crash-report exclusion, the single-instance lock held to the end, offline environment, models, config); ordinals oldest first; each recording re-transcribed in memory (`read_recording`, then `transcribe_in_temporary_store(..., persist_key=False)`), never the stored transcript; all forms read the one in-memory document through the same per-document function as the synthetic entry; an outer by-type error handler.
  - Prints, per ordinal and per finalist form: joined lines; review-severity warnings on a joined line; new error-grade warnings; the net change in review warnings; extra flagged lines; whether the clinician was enrolled. Then one aggregate block: recordings expected (the `--list` count), measured, failed (with the count per error type name), a status line `COMPLETE` (failed 0 and measured equal to expected) or `INCOMPLETE`, n enrolled, n not enrolled, and each median and maximum over the enrolled recordings only (D8). The exit code is 0 only on `COMPLETE`. A custody stop or an interrupt prints its one fixed line (naming the temporary folder to look for, as the precedent does at `run7-measure-kept.py:331-339`) and no aggregate block.
  - Also: the threat model's MEASUREMENT SCRATCH entry (`docs/security/threat-model.md:4864-4898`) and `docs/testing/kept-recordings.md:7` name this script (documents only; needed on every exit).
  - Review: `/review-loop`, then one codex slice over `afq-measure-kept.py` and `afq_lib.py` only (the refusal order, the by-type errors, the print surface).
  - Composer checks: a dry run of the same per-document function over the synthetic pickles; the refusal smoke (no `--enrolment`: exit 2); the two files' SHA-256 recorded here.
  - Done when: the review converged, both checks are recorded, and the hashes are on this task.
- [x] 🟩 **0.4b The practitioner's run** (practitioner, normal PowerShell, developer build, both builds closed). DONE 2026-11-17, recorded UNMEASURED (n enrolled 2 < 3; D8), as this task's done-when allows. The record is below the commands.
  - First `--list` to learn n. Then pass 1 with `--config validation\config` and pass 2 with `--config "$env:LOCALAPPDATA\ClinikoScribe\config"`, each over `"$env:LOCALAPPDATA\ClinikoScribe\past_sessions"`, no `>` redirect. About 15 min per recording per pass.
  - The executor writes the exact commands for the practitioner here after 0.4a (single-quoted Python bodies, the measurement folder's enrolment WAV).
  - The commands (written 2026-11-16, leg ax5). YOU run every line yourself, in a normal Windows PowerShell window opened from the Start menu, never an agent shell (an agent shell cannot unwrap your keys or prove anything here, `docs/lessons.md`). No Python body is needed. Do not add a `>` redirect: watch the window and copy from it.
    0. Before you start:
       - The composer has told you that the gate run (`afq-gate-2.txt`) has ended; the two would compete for the processor.
       - Clinic Scribe is closed, BOTH builds: the installed app and the developer build. The script refuses otherwise.
       - The laptop is on mains power with the lid open.
       - Your enrolment WAV is in place: `enrolment\me.wav` in your measurement folder, the one set up for the clinic 1 smoke (its path on this computer is in the git-ignored `AGENTS.local.md`, "measurement folder"). Below it is written `<measurement folder>`; type your folder's path there.
    1. Go to the repository: `cd "C:\Recording clinic software"`
    2. Check the two script files are the reviewed ones. Each line must print `True`; if either prints `False`, STOP and tell the composer:
       - `(Get-FileHash -Algorithm SHA256 .cursor\loops\afq-measure-kept.py).Hash -eq '98dd3d3ee1c9622bcaaff85f1856fb0a1dd381140ae56d42c575704ee7f47643'`
       - `(Get-FileHash -Algorithm SHA256 .cursor\loops\afq_lib.py).Hash -eq 'cbd991620f940e60b7da394bdc37050f2537749eb38afa7155739274b9fc2138'`
    3. How many recordings are kept (decrypts nothing): `.\.venv\Scripts\python.exe .cursor\loops\afq-measure-kept.py "$env:LOCALAPPDATA\ClinikoScribe\past_sessions" --list`
       - Expected one line, `kept recordings: N`. Each pass then takes about 15 minutes per recording (N × 15 min), and there are two passes.
    4. Pass 1, the repository's validation config: `.\.venv\Scripts\python.exe .cursor\loops\afq-measure-kept.py "$env:LOCALAPPDATA\ClinikoScribe\past_sessions" --enrolment "<measurement folder>\enrolment\me.wav" --config validation\config; "exit=$LASTEXITCODE"`
    5. Pass 2, the installed app's own config: `.\.venv\Scripts\python.exe .cursor\loops\afq-measure-kept.py "$env:LOCALAPPDATA\ClinikoScribe\past_sessions" --enrolment "<measurement folder>\enrolment\me.wav" --config "$env:LOCALAPPDATA\ClinikoScribe\config"; "exit=$LASTEXITCODE"`
       - Both passes measure the three finalists (V4gs, V4s, V3gs) by default; add no `--forms`.
       - Each prints `[start]`, a table header, one row per recording and form (ordinals, form names and numbers only), then `## Aggregate`.
    6. What to paste back, per pass: ONLY the block from the line `## Aggregate (integers only; …)` to its end, plus the `exit=` line. Never the per-recording rows above it.
    7. If something goes wrong:
       - The aggregate says `INCOMPLETE` (exit 1): paste the block anyway (its `failed:` line names each failure by type only) and do not re-run. The cause is fixed under Task 0.4a first.
       - A line starting `[refused]` (exit 2): nothing was measured. Paste that one line. It names its own remedy:
         - close Clinic Scribe;
         - the enrolment WAV not a file: check the path;
         - crash reports not excluded for this interpreter: re-run `scripts\register-native-host.py` from a normal terminal, `AGENTS.md` run step 5.

         Then run the pass again once the cause is gone.
       - A line starting `[custody]` or `[stopped]` (exit 1, no aggregate block): paste that one line. Then look in `%TEMP%` for the `scribe-speaker-eval-*` folder it names and delete it.
       - Any other `[error] the run stopped (<type>)` line: paste it.
  - Recorded 2026-11-17 (leg ax8). The practitioner ran these commands in a normal PowerShell on the developer build. The scripts were the files hashed at Task 0.4a (unchanged since 2026-11-15 22:09), at the commit `22feec4`. AGGREGATES ONLY: the per-recording rows the practitioner also pasted are recorded nowhere (D8, C1).
    - The hash checks: both lines printed `True`, so the two files are the reviewed ones (C5).
    - `--list`: `kept recordings: 2`.
    - Pass 1, `--config validation\config`, `exit=0`:
      - recordings expected: 2; measured: 2; failed: 0; status: COMPLETE; n enrolled: 2; n not enrolled: 0.
      - For each of V4gs, V4s and V3gs (identical):
        - joined median 0, max 0, total 0; carried 0/0/0;
        - review on hop 0/0/0; error on hop 0/0/0; new error 0/0/0; review net 0/0/0;
        - extra flagged Q1 median 2-3, max 3, total 5; QT median 11-15, max 15, total 26; A1 median 12-26, max 26, total 38; AT median 115-127, max 127, total 242.
    - Pass 2, `--config "$env:LOCALAPPDATA\ClinikoScribe\config"` (the installed app's own config), `exit=0`:
      - recordings expected: 2; measured: 2; failed: 0; status: COMPLETE; n enrolled: 2; n not enrolled: 0.
      - For each of V4gs, V4s and V3gs (identical):
        - joined 0/0/0; carried 0/0/0;
        - review on hop 0/0/0; error on hop 0/0/0; new error 0/0/0; review net 0/0/0;
        - extra flagged Q1 median 2-3, max 3, total 5; QT median 11-15, max 15, total 26; A1 median 12-26, max 26, total 38; AT median 115-126, max 126, total 241.
    - With n = 2 the script prints a median as the range of the two middle values ("2-3"). The figures above are as printed, with nothing derived per recording.
    - The per-document premise held on every document of both passes: the scratch's no-hop note equalled the shipped provider's under each pass's config, including the installed app's own, since a mismatch would have read failed, not COMPLETE (round 5 MED-002).
    - D8's reading, in D8's words (its "Real speech" bullet): both passes ended `COMPLETE`, but there are "Fewer than 3 recordings with the clinician enrolled" (n enrolled 2). The real-speech line is therefore UNMEASURED: "no build starts without the practitioner's explicit, named override". The budget figures, new review marks per recording median ≤ 2 and maximum ≤ 5, are not read as met. Joined 0 and review on hop 0 are reported, not counted.
    - What these two recordings show for Task 0.6, as observations only:
      1. On real speech no finalist joined or carried any line under either config (joined 0, carried 0), so the hop added no review mark, no error and no quoted line. Its real-speech cost and its real-speech benefit are both nil on this sample, and the three forms are indistinguishable on it.
         - The reply credit does act here: the extra flagged lines are above 0 under every credit. The scratch counts a credit's extra line only as another speaker's wholly uncovered line after a warned, left-out run of the CONFIRMED clinician (`afq_lib.credited` / `flagged_run_ranges` / `replies_after`, minus the shipped mark).
         - So on these recordings the confirmed-clinician test does find left-out clinician lines followed by another speaker. The hop reads a different place: the reply after a CUE-ROUTED, in-note clinician question (D1 (a)).
         - Why the hop found none is NOT observable here. The script prints no count of cue-routed clinician questions, no attribution figure and no count of which D1 condition refused a candidate. The cause is unknown, and no reason is offered.
         - The Excluded item "A clinician's answer to a patient's question (inverted roles); a reply joined when no clinician is confirmed" (Excluded — Revisit Only If Needed) is revisited "only if real-speech attribution makes the confirmed-clinician test miss most questions (Task 0.4b's attribution line)". This run has no attribution line, so its trigger is neither met nor ruled out. The item stays excluded, and the question is open for the practitioner at 0.6.
      2. The credit's real-speech load, which D8 reports with no threshold. It is the same under every form, since nothing joined:
         - pass 1: Q1 median 2-3 (total 5), QT 11-15 (26), A1 12-26 (38), AT 115-127 (242);
         - pass 2: equal except AT 115-126 (241).
         - Against it, the synthetic gate configuration flags 78 extra lines under AT over all 22 encounters of `heldout-6` for the finalists (Task 0.3, `afq-gate-3.txt`).
         - Task 0.3's leading 0.6 option, V4gs under AT, carries this load. Its effect on that option is set out in the handoff's 0.6 options.
  - Done when: both passes ended `COMPLETE` and their aggregate blocks are on this task (expected, measured, failed, the status line, n enrolled, n not enrolled, the medians and maxima over enrolled recordings; nothing per recording). A pass that ended `INCOMPLETE` or printed no block is re-run after the cause (named by its error type) is fixed under 0.4a; if it still cannot complete, the task records "incomplete" and D8 reads that pass as unmeasured. If n enrolled < 3, record "unmeasured" (D8).
- [x] 🟩 **0.5 The numbers reviewed.** DONE 2026-11-17. The `/review-loop` converged in rounds 8–9, and the codex pass in round 10, with its one LOW fixed; no recorded figure was corrected. D8's first-reply check is settled on Task 0.3. The five open points were not in round 10's slice: see the handoff. `/review-loop` over this plan's records of 0.2–0.4b (each figure against the scratch outputs in `.cursor/loops/afq-out/`), then the codex peer pass with the records as their own slice.
  - Done when: the pass converged and any corrected figure is recorded.
- [x] 🟩 **0.6 The exit, the form and the residues** `[decision]`. DONE 2026-11-17: IMPROVEMENT, "build as an improvement", V4gs under QT, D8's real-speech line overridden by name, and the `h5-17` residue and the three reported residues accepted by name. The record is below.
  - Options: GATE-CAPABLE (build, then run 10); IMPROVEMENT — "build as an improvement" or "close with no change"; NO-GO — close with no change. With a building exit: the reach and guard (D2), the credit sub-variant and whether the chooser's wider predicate also credits (D4), and the practitioner's word on each reported residue (D8's "Reported for the practitioner's word" bullet).
  - Decide after: 0.3, 0.4b and 0.5. The composer presents the D8 table with the recommended option first; D8 decides which exits are open. Only a configuration with its own gate-configuration D8 lines in 0.3's tables can be authorised; if the practitioner prefers one that was not run that way, the composer runs it over the saved documents and returns before the choice is recorded.
  - Blocks: 0.7 and every later phase.
  - Record with the choice: the chosen form's state table and credit definition (they supersede D1's and D4's measured alternatives for Phase 1), and the base commit for D13.
  - Recorded 2026-11-17 (leg ax10).
    - How it went:
      - Before the decision, the five open points were reviewed by codex round 11 (0 findings).
      - The composer presented the options, recommendation first (the handoff).
      - The practitioner asked: "do you suggest QT or AT? Take the third recording out of the factor".
      - The composer recommended QT. Its reasons: AT's extra recovery rests on a credit that, at 115-127 extra flags per real consultation, no longer means the clinician was pointed to the line; on real speech the flags are the whole visible change; QT keeps most of the gain.
      - The composer proposed recording: "build V4gs under QT as an improvement (0.3.7, shadow mode stays on, no run 10), overriding D8's unmeasured real-speech line by name and accepting the h5-17 next-patient quote as a named residue".
    - The practitioner's words, verbatim: "yes, record QT".
    - The decision, as so worded:
      - Exit: IMPROVEMENT, "build as an improvement" (D9). The phases kept are 1, V, M as a replay, D, F.3, then the install decision. There is no rule v7, no `heldout-7` and no run 10; shadow mode stays on; the version is 0.3.7.
      - Form: V4gs, that is reach V4 (unlimited), guard G on and switch S on.
      - Credit: QT, questions only, whole turn.
      - D8's real-speech line, UNMEASURED (Task 0.4b: n enrolled 2 < 3), is overridden by the practitioner's explicit, named override, in the words proposed and accepted: "overriding D8's unmeasured real-speech line by name".
      - The `h5-17` residue is accepted by name: "accepting the h5-17 next-patient quote as a named residue". That is the leg ax6 residue "an indirect next-patient quote through the suggestion stage, not on a joined line".
      - AT's real-speech load (median 115-127 extra flagged lines per recording) is declined, which is why the credit is QT.
      - The chooser's wider predicate (`+m`), D4's remaining sub-choice. D4 as written makes the chooser's mark the credit plus the `m` replies, and the harness credit is QT without `+m`. D8's tie-break also puts each credit first without, then with, the wider predicate. QT and QT+m read the same silent and failing counts on every set in the gate tables, and extra flagged lines differ only on `heldout-4` (12 against 13). Recorded reading: the harness credits QT without `+m`; the chooser's mark adds the `m` replies, as D4 says.
    - The chosen form's state table, superseding D1's and D2's measured alternatives for Phase 1:
      - D1's five rows, conditions (a)–(d) and the sentence after the table, unchanged.
      - The budget of row 3 is unlimited (V4): the window stays open, joining every line that meets row 3, until row 2 or row 5 applies. Row 1 stays transparent. Carried pieces (row 4) never count.
      - Guard G on: the window opens only when P's last sentence is itself a question and alone routes to P's section. This uses D2's sentence cut, `_CLOSING_MARKS` peeled, no abbreviation handling, `is_interrogative` and `layered_section` over the sentence's own tokens with `_route`'s arguments. D2's two named limits of G stand.
      - Switch S on: P may also be a cue-routed line plus its one carried piece. It is a question if either piece is, and with G the two pieces are read as one line.
      - V4t is not chosen: the window does not survive the reply speaker's own cue-routed lines.
      - The scratch's readings, peer-reviewed in round 11, are part of this definition:
        - after a joined line or a carried piece the existing carry's chain is closed (point 1);
        - the S counter and composition (point 5);
        - V4t is unreachable (point 4).
    - The credit definition, superseding D4's measured alternatives for Phase 1:
      - `replies_after(run)` is the wholly uncovered, text-bearing lines of the one speaker other than the confirmed clinician that directly follows a `flagged_runs` run, before the next-patient cut.
      - Questions only: a run counts when any of its pieces passes `is_interrogative` (round 11 point 2).
      - Whole turn: the lines run on through that speaker's turn. Textless segments are transparent, and a covered line is passed over without being credited; a speaker change ends the turn (round 11 point 3).
      - The harness credit is those lines, as their own term in `word_info`. A reply is credited only while its clinician run still carries the warning.
      - The chooser's mark is that credit plus the same replies after a confirmed-clinician question that is in the note solely through the clinician's own Add (its `m` assertion); the harness does not credit those (no `+m`).
      - D4's named consequences stand.
    - Base commit for D13: `22feec4` (HEAD at the decision; tree with the three uncommitted Phase 0 record edits only).
    - The phases this exit drops are marked NOT BUILT at Task 0.7, as its done-when assigns ("the phases the exit drops are marked NOT BUILT with a dated line"); they are not marked here.
    - MUST-PAUSE (leg ax10). Task 0.6 asks for "the practitioner's word on each reported residue (D8's 'Reported for the practitioner's word' bullet)". The words above cover the `h5-17` residue and AT's load, but not the three items below, all reported for V4gs under QT. They are left undecided. ONE question, with three named items:
      - (1) Lines that must stay out and are newly `[flagged]`, the gate configuration, summed over the seven sets: 2 material, 9 other, 3 at or after the reference tail (`afq-gate-3.txt`).
        - Per set, material / other / tail: `scripts` 0/5/0, `heldout` 0/0/0, `heldout-2` 0/1/0, `heldout-3` 0/0/0, `heldout-4` 1/1/2, `heldout-5` 0/1/0, `heldout-6` 1/1/1.
        - No hop under QT reads 3 / 9 / 4, so the hop adds none.
      - (2) The real-speech load of the chosen credit: QT median 11-15 extra flagged lines per recording, max 15, total 26, in both passes; joined lines 0.
      - (3) "Clean by absence": no seen script has a patient's "don't write this down" as the FIRST reply to an in-note question. The only such line, `hld-17` line 2, is a second reply (Task 0.3). Task 1.1 pins that a first-reply "don't write this down" IS quoted, as a named residue.
      - Recommended: "Accept all three as named residues".
        - For (1) and (2): a `[flagged]` mark only points the clinician to a line on the Line list. It puts nothing in the note, and Save is not held back (D4), so a flagged line that must stay out enters only by the clinician's own Add.
        - For (2) also: it is the composer's own reason for QT over AT.
        - For (3): no seen script has the case, it is pinned and named, and the clinician reviews every note under shadow mode.
      - Alternative, "Decline (1) or (2)": then no building configuration remains under the chosen form. Q1 is not an IMPROVEMENT, at 14 / 16 silent against the halves 12.5 / 12, so the exit becomes NO-GO.
      - Alternative, "Decline (3)": this needs a new guard against the case, a new dated design decision with its own measurement, before Phase 1.
    - The answer, 2026-11-17 (in chat; recorded in leg ax11).
      - The composer's question, verbatim: "To close Task 0.6, D8 needs your word on three costs of V4gs under QT. (1) Lines that must stay out of the note get newly [flagged]: 2 material, 9 other, 3 at or after the next-patient tail, across the seven synthetic sets. The QT credit with no hop gives 3 / 9 / 4, so the hop adds none. (2) On real speech, about 11-15 extra [flagged] lines per consultation. (3) No seen script has a patient's 'don't write this down' as a first reply, but if one were, the hop would quote it; Phase 1 pins that as a named residue. A [flagged] mark only points to a line in the Line list: it adds nothing to the note and doesn't block Save. Accept these as named residues?"
      - The practitioner's chosen label, verbatim: "Accept all three (Recommended)".
      - The composer checked item (1)'s totals against `afq-gate-3.txt`: V4gs QT 2/9/3, no hop QT 3/9/4.
      - So all three are named residues accepted by the practitioner:
        - (1) stay-out lines newly `[flagged]` under QT;
        - (2) QT's real-speech load;
        - (3) a first-reply "don't write this down" quoted by the hop, pinned by Task 1.1.
      - Every item of D8's "Reported for the practitioner's word" bullet and of this task's "the practitioner's word on each reported residue" now has it, and the MUST-PAUSE above is closed.
- [x] 🟩 **0.7 The chosen exit's phases hardened.** DONE 2026-11-17 (leg ax11; Review Findings Log Round 12).
  - The improvement exit's phases are hardened in place: Phase 1 (1.1–1.4), V (V.1, Step H), M.1, D (D.1–D.4), F.3, and P's improvement path (P.3, P.5).
  - The gate-capable phases are marked NOT BUILT with dated lines: F.1, F.2, P.1, P.2, P.4, M.1's gate-capable variant, D10, D11, C6, the Validation line, and Key Findings' `heldout-7` sites.
  - The `heldout-7` brief question does not arise. A scoped `/review-plan` over the phases the exit keeps (Phase 1 onward), from the outlines below, 0.6's record and Key Findings' pin and site lists. On the gate-capable exit it also settles the `heldout-7` brief (recommended: `heldout-2`'s brief with only the ids changed, so the set stays comparable; its digest committed in F.1).
  - Done when: each kept task meets the Task Specification Standard and the phases the exit drops are marked NOT BUILT with a dated line.
- [x] 🟩 **0.8 The simulation recorded** (every exit). DONE 2026-11-17 (leg px1, at P.5). `docs/testing/validation-harness.md` gains "Answer-hop simulation" (the method, the tables as ids and counts, the decision); `AGENTS.md` and `CHANGELOG.md` per `/document`. On a no-change exit: SR's Deferred item and NCD's question-and-answer item get dated reconciliation lines, the plan closes, and the practitioner deletes `C:\afq-sets\`.
  - Done when: the documents hold the record and, on a no-change exit, the lifecycle state reads Completed.
  - On this exit (improvement, 2026-11-17), the "Answer-hop simulation" section is written with D.2, beside M.1's measurement. `AGENTS.md` and `CHANGELOG.md` are updated at P.5's `/document`. Nothing of 0.8 is placed before Phase 1, and it stays 🟥 until then.
  - 2026-11-17 (leg dx1): the "Answer-hop simulation" section is written (D.2). 0.8 stays 🟥 until P.5's `/document`.
  - 2026-11-17 (leg px1, P.5's `/document`): `AGENTS.md` (the Current Status paragraph closed, the full one moved to `docs/architecture/phase-history.md`) and `CHANGELOG.md` (the 0.3.7 entry: built of record, installed, the copy approved, M.1, the register rows) hold the record beside the harness document's section. This is the improvement exit, so the no-change reconciliation lines do not apply. Done.

### Phase 1 — The build (hardened 2026-11-17 at Task 0.7 for the improvement exit: V4gs under QT, Task 0.6)
Phase 1 builds exactly Task 0.6's record: "The chosen form's state table" and "The credit definition". Those two blocks are the canonical specification and supersede D1's, D2's and D4's measured alternatives. Code-verified against HEAD `22feec4`, whose product tree equals Key Findings' `50a8a2b`. Every task ends with the composer's `ruff check . && mypy && pytest` in `desktop/` (C7; the executor runs no Python). Every changed expectation is listed in the task's record with its reason, and a predicted fixture divergence goes in its per-set table, never edited away (C3).
- [x] 🟩 **1.1 The answer hop in the router.** DONE 2026-11-17 (legs bx1–bx3). The composer's full gate at HEAD `a00685c` with the uncommitted edits: ruff "All checks passed!"; mypy "Success: no issues found in 67 source files"; pytest 10899 passed, 9 skipped (492.92 s; `.cursor/loops/stage-1-bx2-full.txt`). The baseline was 10836 passed, 9 skipped.
  - Moved expectations, each with its reason:
    - The one held-out divergence, recorded per C3 with the expectation unchanged: `h5-17` unsure `(5,)` → `(3, 5)` in `_PREDICTED_UNSURE_DIVERGENCES_BY_SET["heldout-5"]`, the count 10 → 11.
      - The join: segment 2, the clinician's "When did it start?", routes to History by the validation cue `did it start`, and guard G passes, so the window opens.
      - Segment 3, the patient's "Maybe a fortnight ago, maybe longer.", is uncued and not a question, so it joins. Its listed hedge "maybe" is then marked.
      - Key Findings had predicted this.
    - No correction divergence moved. No `EXTRACTIVE_CELLS` cell moved (none has a confirmed clinician's question). No other fixture moved.
  - New tests: `TestAnswerHop` (27 fixture cases in `fixtures/answer_hops.py`, plus five single tests and nine sentence-cut cases); the matrix's `joins` registry with the cell `ex-answer-joined`, the lint `test_only_a_declared_join_follows_a_clinician_question` and `test_every_join_cell_is_registered`; and the third arm "or it is joined" in `test_validation_scripts.py`.
  - Row 4 note: under the unlimited reach, D1's row 4 is unreachable, because row 3 takes every piece it would carry. The product leaves the branch out and says so. Task 1.4 checks equality with the scratch's V4gs.
  - Files:
    - `desktop/src/scribe_desktop/note.py`: `ExtractiveNoteProvider.generate_sections` (`:2243-2305`) and the class docstring (`:2172-2216`). The hop is a fourth branch beside (1) cue-routed, (2) the same-speaker carry and (3) dropped. It applies D1's five rows with the unlimited V4 budget, guard G and switch S exactly as Task 0.6's state table says. `_route`, `is_interrogative` and every frozen vocabulary stay unchanged (C3), and `provider_name` stays `extractive-v1` (Excluded).
    - New `desktop/tests/fixtures/answer_hops.py`: plain expectations, one case per D1 row and per G / S condition, each with its turns and the expected section per segment.
    - `desktop/tests/test_note.py`: new `TestAnswerHop`, reading the fixture. It covers:
      - every row in both directions (joins / does not join);
      - G's two named limits (D2);
      - S's either-piece question;
      - a reply that is itself a question, or holds a suspect word, closing the window;
      - an unconfirmed clinician (no join);
      - a joined line closing the existing carry's chain (Task 0.6, round 11 point 1);
      - one test that a joined assertion is field for field a carried one (D3: same `transcript` assertion, `x` id, no new field);
      - a patient's "don't write this down" given as the FIRST reply, pinned as QUOTED. That is accepted residue (3), Task 0.6, 2026-11-17; the test's docstring names it.
    - `desktop/tests/test_note_matrix.py` (`:832-868`): a hop registry and an "only a declared join" lint beside `test_every_carry_cell_is_registered`, so no `EXTRACTIVE_CELLS` oracle starts joining by accident. A cell whose expectation moves is examined: a join by design is declared in the registry and listed with its reason, and anything else is a finding.
    - `desktop/tests/test_validation_scripts.py:894-924` ("a hedged line routes, or is a correction") gains its third arm, "or is joined".
  - Held-out fixtures (`desktop/tests/fixtures/heldout_transcripts.py` readers):
    - The tables are `_PREDICTED_UNSURE_DIVERGENCES_BY_SET` (`test_note_check.py:2728`) and `_PREDICTED_CORRECTION_DIVERGENCES_BY_SET` (`test_note.py:3353`).
    - Each assertion the hop moves goes into its per-set table with the count line updated, as C3 says. Key Findings' "`h5-17` (5,) → (3, 5)" was predicted for the first-line rule, so the V4gs entries are whatever the suite shows, each explained by a join.
  - Done when: the composer's suite is green with every moved expectation listed with its reason.
- [x] 🟩 **1.2 The reply flag (chooser) and the reply credit (harness).** DONE 2026-11-17 (legs bx3–bx4). The composer's gate at HEAD `a00685c` with the uncommitted edits:
  - narrow run, 2289 passed;
  - ruff "All checks passed!" and mypy "Success: no issues found in 67 source files";
  - pytest 10929 passed, 9 skipped (497.92 s; `.cursor/loops/stage-1-bx3-full.txt`).
  - No `flagged_segments` exact pin moved.
  - Moved pins, each with its reason (the leg bx3 handoff has the list in full):
    - The copy pins, for the executor's drafted wording (a draft until D.4):
      - `test_ui_models.py`: the `clinician_line_omitted` hint and two count-line pins;
      - `test_ui_screens.py`: two count-label pins.
    - The report-shape pins, for the new amendment sentences and the residue section's reply-credit line:
      - `test_validation_harness.py` `_RUN_INFORMATION`;
      - five exact residue-section lists, the nothing-measured one among them (its boundary record moves to `tail[12]`).
    - Not moved: the short-form pins and the legacy header's substring pins.
  - One deviation from the scratch, recorded: the `m` test is `assertion_id == manual_assertion_id(segment_index)`, not the scratch's `startswith("m")`. The two agree on every note the app or the harness makes, and Task 1.4's comparison is the check.
  - Files:
    - `desktop/src/scribe_desktop/ui/models.py`:
      - a new `replies_after` beside `flagged_runs` (`:2744-2770`), the ONE helper both readers use (D4), implementing Task 0.6's credit definition (questions only, whole turn, before the next-patient cut);
      - `flagged_segments` (`:2773-2784`) adds the replies after `flagged_runs`' question runs, and the replies after a confirmed-clinician question in the note solely through its `m` assertion (the chooser's wider mark; D4);
      - `flagged_count_line` (`:2890-2927`): the count line's parenthesis (`:2910-2912`) also names an answer to a question you asked;
      - the `clinician_line_omitted` hint (`:2304-2309`) gains one clause, pointing to the answer flagged after the line.
      - The two copy strings are the executor's DRAFT. The practitioner's wording replaces them at D.4 (D5), with their pins, before F.3.
    - `desktop/src/scribe_desktop/validation.py`:
      - `encounter_metrics`: the reply credit as its own term in `word_info`'s `warned` (`:2110-2142`), computed through `replies_after` WITHOUT the `m` replies (Task 0.6: QT, no `+m`). `credited_segments` (`:1893-1902`) and the run-only counts (`:2078-2086`) stay exactly as they are, so `credited == flagged_runs` holds (`test_validation_metrics.py:1387-1395`).
      - D5's second complete metrics computation without the reply credit (residue classes and exemptions included), its verdict, and the report-only line: segments and material facts credited by the reply only, in how many encounters.
        - Under rule v6 (this exit; D5's "both verdicts" wording is rule v7's), the report's verdict is the one with the credit. The report-only line also states the verdict without it, and no column is added, so every unaffected row stays byte-comparable (D5).
      - The dated amendment sentence among the per-rule sentences (`:3784-3852`), which says the reply credit is a loosening decided after run 9 failed on this class.
      - No rule file changes, and rule v6's verdict of record stays run 9's (D9).
  - Tests:
    - New tests beside `TestFlaggedLineCredit` (`test_validation_metrics.py:1117`) and `TestJoinedRunCredit` (`:1318`): credit ⊆ `[flagged]`; an Add then undo restores the mark; a reply flagged with no warning row behind it; a suggested line's `m` assertion keeps its reply flagged; a non-question run credits no reply (QT); "Acknowledge all" unchanged.
    - The moved pins in Key Findings ("Pins a build would move"):
      - the copy pins and the report-shape pins move, and are listed;
      - the `flagged_segments` exact pins are expected to hold under questions only, and a moved one is a finding.
  - Done when: the composer's suite is green, every moved pin is listed with its reason, and the copy is marked "draft until D.4" in the code comment beside it.
- [x] 🟩 **1.3 Consumers.** DONE 2026-11-17 (legs bx4–bx5). No product code changed. The composer's runs at HEAD `a00685c` with the uncommitted edits:
  - `pytest -q tests/test_note_check.py -k TestCheck2Contradictions`: 64 passed, 442 deselected, the 4 new tests among them;
  - the full gate: ruff "All checks passed!", mypy "Success: no issues found in 67 source files", pytest 10933 passed, 9 skipped (484.66 s; `.cursor/loops/stage-1-bx4-full.txt`). That is 10929 plus the 4 new tests, with nothing else moving.
  - Tests (`test_note_check.py` `TestCheck2Contradictions`, after `test_a_question_is_not_an_affirmation`). Each reply is placed by the shipped provider: its question routes to Red flags, the reply has no route of its own, and both land in Red flags.
    - `test_a_joined_reply_that_names_what_it_negates_contradicts_at_error`, run with a pre-filled line and with a typed line. A joined "No numbness." against "Numbness reported." draws `contradiction` at error grade on the authored line, with the evidence on the reply's two words, `SourceCoords(1, 0, 1)`.
    - `test_a_low_confidence_joined_reply_contradicts_at_review`: the same pair with "numbness." at probability 0.3 draws `contradiction_low_confidence` at review grade.
    - `test_a_bare_no_beside_its_question_draws_no_contradiction`: a joined bare "No." draws no warning, pinned as the named residue.
  - Recorded reading (leg bx4, from the code; no change needed). A joined line is an ordinary quoted line of a speaker who is not the confirmed clinician (D1 (b), D3), so each reader sees it like this:
    - The two learners (`ui/note_review.py:300` for typed shorthand, `:391` for added or moved lines) test `spoken_by_confirmed_clinician` before anything else. Moving or retyping a joined line therefore teaches nothing and says "not attributed" (`LEARNING_NOT_ATTRIBUTED_NOTE`). The hop never places a clinician line, because its question was already cue-routed.
    - `note_fill` (autofill's `_first_phrase_match`, prefill detection) and Check 6 (`note_check.next_patient_warnings`) read only the document, the config and the boundary, never the sections, so the hop cannot move them.
    - `note_suggest` sees a joined line as a placed context line (`[placed: <key>]`, `note_suggest.py:19-20`), not an asked one, so it asks about fewer lines.
    - The prose stage:
      - A section that gains a joined line becomes other-voice (`note.section_other_voice`, `ProseInput.other_voice`, `prose_style.py:263-271`). It then gets Check 5's "Pt" frame and the prompt's `Speaker` line.
      - `section_input_digest` (`note.py:1112`) folds that flag and the texts, so a rendering made before the join is no longer bound to it.
    - `replay_kept.note_drift` (`replay_kept.py:325-368`) regenerates through `extractive_provider_from_config` and `check_note`, so a 0.3.7 replay joins too. Against a 0.3.6 replay of the same recording:
      - `sections_missing` can fall; `[2026-11-17 correction, leg dx3, review round 23 PR-LOW-040]` it cannot: the window opens only after an emitted cue-routed line (or its carried piece, in the same section), so a join only adds lines to a section already present, and `_present_sections` counts presence only — `sections_missing` is unchanged by the hop;
      - `reviews` can move either way (a reply's `high_risk_omission` goes once it is covered, and Check 1's marks on a joined line come);
      - `clinician_lines_omitted` does not change, because no clinician line is joined.
      - That drift is by design (Codebase Integration Notes).
  - Check 2 (`note_check.py` `_structured_quoted` `:1292-1316`, `contradiction` `:1319-1333`), tested in `test_note_check.py` `TestCheck2Contradictions` (`:417`):
    - a joined reply that names what it negates ("No numbness.") against a pre-filled or typed line draws error grade, and a low-confidence one review grade;
    - a bare "No." beside its question draws no contradiction, pinned as the named residue (Codebase Integration Notes).
  - A one-paragraph recorded reading on this task (no code change expected) for:
    - the two learners (`ui/note_review.py:311`, `:392`: a joined patient line teaches nothing);
    - `note_fill` and Check 6 (they read the document only);
    - `note_suggest` (a joined line is placed context);
    - the prose frame (`prose_style.py:264-266`, "Pt", and `section_input_digest` changes);
    - `replay_kept.note_drift` (drift against 0.3.6).
  - Done when: the composer's suite is green and the reading is on this task.
- [x] 🟩 **1.4 Scratch against product, once** (D6; composer-run, minutes, no model). DONE 2026-11-17 (script written in leg bx4, run by the composer, recorded in leg bx5). The count is 0.
  - Command (repository root, at HEAD `a00685c` with Phase 1's uncommitted edits): `.venv/Scripts/python.exe .cursor/loops/afq-pin.py --docs C:/afq-sets/docs --config validation/config < /dev/null`. Exit 0 in 14 s; output `.cursor/loops/afq-pin-1.txt`.
  - The product against the scratch's `V4gs` under credit QT (off), by population. Every row reads 0 sections, 0 credit and 0 flag differences, 0 skipped and 0 errors:

    | Population | Encounters |
    |---|---|
    | cells (`EXTRACTIVE_CELLS`) | 18 |
    | `scripts` text / docs | 50 / 50 |
    | `heldout` text / docs | 22 / 22 |
    | `heldout-2` text / docs | 22 / 22 |
    | `heldout-3` text / docs | 23 / 23 |
    | `heldout-4` text / docs | 22 / 22 |
    | `heldout-5` text / docs | 22 / 22 |
    | `heldout-6` text / docs | 22 / 22 |

    That is 384 encounters (18 cells and 183 documents in each mode), then "(no difference)" and `PIN differences total: 0`.
  - Row 4: the product leaves out D1's row 4 (Task 1.1's note), while the scratch's `HopProvider` keeps it. On all 384 encounters the two place every section the same, which agrees with Task 1.1's argument that row 3 takes every piece row 4 would carry. That argument is the general proof; this run is its measurement over the seen populations.
  - The `m`-assertion deviation recorded on Task 1.2 does not arise here: off, no note holds an `m` line.
  - The executor writes `.cursor/loops/afq-pin.py`, git-ignored and synthetic only. It imports `afq_lib.py` without changing it (C5) and compares:
    - the product's sections against the scratch's `V4gs` sections, encounter by encounter, over the `EXTRACTIVE_CELLS` turns, the seven sets' reference documents, and the saved documents under `C:\afq-sets\docs` (off, no suggestions, no prose);
    - the product harness's reply credit against `afq_lib.credited(..., QT)`;
    - the product's `flagged_segments` against the scratch's shipped mark plus `newly_flagged(QT)` (no `m` lines exist at off).
  - It prints the difference count per set: ids and counts only.
  - Done when: the count is recorded here and is 0. Any difference is a finding against the scratch or the product (D6), disposed before Phase V.

### Phase V — Version and hardening
- [x] 🟩 **V.1 Version 0.3.7.** DONE 2026-11-17 (leg cx1; gate recorded in leg cx2). The composer's gate (`.cursor/loops/stage-2-cx1-gate.txt`):
  - ruff "All checks passed!" and mypy "Success: no issues found in 67 source files";
  - pytest "10933 passed, 9 skipped in 478.73s (0:07:58)";
  - `npm run qa` in `extension/`: typecheck and lint clean, vitest "Test Files 13 passed (13)" and "Tests 313 passed (313)", package `scribe-extension@0.3.7`;
  - every return code 0.

  Build record: The six fields read 0.3.7, each read before and after its edit; no test or document pins the literal (search; the 0.3.6 version commit's own `git log -S` was not run, since the leg's grants cover `git status` and `git diff` only). `CHANGELOG.md` gains the 0.3.7 entry at the top of Added (CRLF kept). The six strings (Key Findings: `desktop/pyproject.toml:7`, `desktop/src/scribe_desktop/__init__.py:3`, `extension/package.json:4`, `extension/package-lock.json:3` and `:9`, `extension/src/manifest.ts:29`) and a `CHANGELOG.md` entry (CRLF kept, C8): the hop, the reply flag and credit, the improvement exit, shadow mode on, no run 10. Verification: the composer's desktop suite and `npm run qa` in `extension/`.
- [x] 🟩 **Step H: Hardening pass** over Phase 1 and V's whole diff against `22feec4`. DONE 2026-11-17 (legs cx1–cx5): H1 at round 13, H2 at round 14, H3 at round 15, H4 at rounds 16–18. The composer's last gate: ruff and mypy clean, pytest 10937 passed, 9 skipped (`.cursor/loops/stage-2-cx4-gate.txt`). With it, Phase V is DONE.
  - [x] 🟩 H1: `/review-loop` to convergence. CONVERGED at round 13 (round 1 of cap 3, leg cx1): 0 CRIT / 0 HIGH / 0 MED / 2 LOW, both applied. The composer's gate was green over both fixes (V.1's record: ruff and mypy clean, pytest 10933 passed, 9 skipped, `npm run qa` clean).
  - [x] 🟩 H2: `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`. DONE 2026-11-17 (leg cx2), round 14: 0 findings, seven candidates left alone by the conservatism guard, no change.
  - [x] 🟩 H3: `/security-review` — log findings; same routing. DONE 2026-11-17: round 15 (leg cx2), 2 MED, both Fix-now and applied (SEC-001 a test pin plus D.4's practitioner question; SEC-002 D.1's residue list), no product code changed. The composer's gate was green over the new test (`.cursor/loops/stage-2-cx2-gate.txt`: ruff and mypy clean, pytest 10935 passed, 9 skipped). The residues read were:
    - a wrong speaker label;
    - a false question by its opening word;
    - a next patient's reply where no boundary is found;
    - a spoken instruction as a reply, including accepted residue (3);
    - a third speaker;
    - learned-cue amplification;
    - the suggestion stage's indirect next-patient quote (`h5-17`).
  - [x] 🟩 H4: codex peer re-check, whole surface in slices (at most about 15 files a slice). CONVERGED 2026-11-17 (codex `gpt-6-astra` medium).
    - Slice A (the three product files) converged at round 16 with 0 findings.
    - Slice B (tests, fixture, version and CHANGELOG) found 2 LOW at round 17: PR-LOW-020 and PR-LOW-021, verified in leg cx3 as missing regression tests with no product defect.
    - Both were applied in leg cx4 (a fixture case and a test), and the composer's gate was green at 10937 passed, 9 skipped.
    - Slice B converged at round 18 (peer round 2 of cap 5) with 0 findings, both fixes confirmed.

### Phase M — The built rule measured (improvement exit)
Phase M DONE 2026-11-17: M.1 reproduced Task 0.3's V4gs QT lines with 0 differences (stage-3, legs mx1–mx2). Its plan edits are uncommitted (autocommit off); the commit is asked at D.4, together with Phase D.
- [x] 🟩 **M.1 The built rule replayed in the gate configuration.** DONE 2026-11-17 (script in leg mx1, both runs by the composer, recorded in leg mx2). `M1 DIFFERENCES TOTAL: 0`: the product reproduces the finalist's lines, so under the stop rule the plan continues. The record is at the end of this task.
  - What it runs:
    - The hardened commit's product over the seven seen sets' saved documents (`C:\afq-sets\docs`, transcribed at `22feec4`, whisper `medium`), with no re-transcription.
    - Rule v6 with `--suggestions confirm-all --prose`, the configuration rule v6 gates in.
    - The executor writes `.cursor/loops/afq-measure-built.py`, git-ignored and synthetic only. It uses `afq_lib.py`'s replay patches and projection unchanged, but the PRODUCT provider and the product harness credit: no `HopProvider`, no credit patch.
  - Who and when: the composer, in the background with `< /dev/null`, on mains power with the lid open and the installed app closed (C7). Plan it as an overnight job of up to about eight hours. Task 0.3's gate run took 7.9 h for four configurations; this is one.
  - What it compares against: Task 0.3's V4gs QT gate lines (`afq-gate-3.txt`), encounter for encounter, through the per-encounter projections `afq-out/gate/<set>/V4gs.json` under QT. Equal means:
    - every fact's verdict, `warned` and silent flag;
    - silent facts and failing encounters per set: `heldout-2` 4 / 2, `heldout-6` 8 / 7, 0 elsewhere;
    - the `h5-17` line-15 quote as the one line quoted that must stay out;
    - new unsupported, new error-grade and new checker failures 0, the 50 still passing, no set pushed over its R3 ceiling;
    - the two flagged columns under QT.
    - Harm is the per-fact difference against Phase 0's saved no-hop gate projection, as in Task 0.3.
  - Stop rule (no decision task, unchanged): M reproduces the finalist's lines and the plan continues; any difference pauses for the practitioner, with D13 available. M's reports are measurements, not runs of record (D9).
  - The script, written 2026-11-17 (leg mx1; no Python run by the executor): `.cursor/loops/afq-measure-built.py`, git-ignored, synthetic only. It imports `afq_lib.py` unchanged and uses its `replaying` / `capturing` patches, alignment cache, `projection`, `note_counters`, `fact_segments`, `next_patient_joins` and `label_disagreements`.
    - Per encounter it runs two compositions in the gate configuration, with the language model loaded once:
      - the PRODUCT: the shipped `evaluate_encounter` with the harness's default provider factory and the product harness credit (no `HopProvider`, no credit patch); its verdict without the reply credit is `validation.without_reply_credit`;
      - the no-hop baseline, RE-RUN through Task 0.3's own route (`afq_lib.replay_encounter(..., NO_HOP, stages)`). The saved projections hold no note warnings, so "new error-grade warnings" needs the no-hop note itself. Its projections are also compared with the saved `none.json`, so any drift in the replay or the model is a counted difference. Harm stays the per-fact difference against the SAVED `none.json`, as M.1 says.
    - The product keeps no join record, so its joins are derived: the segments its note places through a provider id (`x<n>`) that the baseline note does not. Each join's question is the nearest earlier provider-placed segment that is not itself joined. The count the baseline places and the product does not is printed and not compared.
    - The flagged columns: QT is the harness credit less the shipped mark (anchors and `flagged_runs`), compared with the gate's QT column; QT+m is the product chooser's `flagged_segments` less the shipped mark, compared with the gate's QT+m column (Task 0.6's recorded reading: the chooser adds the `m` replies, the harness does not). `afq_lib.newly_flagged` is not used: it subtracts `flagged_segments`, which is the product's own mark since Task 1.2.
    - It compares, and counts every difference by name (ids, fact indices and column names only):
      - each encounter's projection under QT and under `shipped` against `afq-out/gate/<set>/V4gs.json` (each fact's material, verdict, `warned` and silent flag; the counts; the joins; the scratch's credit and the product harness credit), and the baseline's against `none.json`;
      - the gate-table shape of `afq-gate-3.txt`: the join table (shipped credit) and the credit table's QT and QT+m rows, cell for cell against the gate's `none` and `V4gs` rows. Windows, V4t survived, S candidates and the QT+m row's metric cells print `n/a` and are not compared;
      - D8 across the sets (QT) against the gate's `none | QT` and `V4gs | QT` rows, when all seven sets ran;
      - M.1's pinned items per set: silent / failing (`heldout-2` 4/2, `heldout-6` 8/7, 0/0 elsewhere), the stay-out lines quoted (`h5-17:L15m` on `heldout-5`, none elsewhere), new unsupported / error-grade / checker failures 0/0/0, not pushed over R3, and the 50 PASS.
    - It refuses (exit 2) when HEAD does not start with `4a0081d` (`--expect-commit`), when `desktop/` has uncommitted changes, when `--out` is inside `afq-out/gate`, or when the gate projections or `afq-gate-3.txt` are missing. Output: `<out>/<set>/product.json`, `<out>/<set>/none-rerun.json` and `<out>/built-summary.md` (default `--out` is `.cursor/loops/afq-out/built`). One progress line per encounter goes to stderr. Exit 0 only when the last line reads `M1 DIFFERENCES TOTAL: 0`.
  - The composer's commands, from the repository root at `4a0081d`, with the installed app closed, on mains power, lid open:
    1. The quick self-test, one set (about 30 minutes: two compositions per encounter, against Task 0.3's 3701 s for four):
       `.venv/Scripts/python.exe .cursor/loops/afq-measure-built.py --docs C:/afq-sets/docs --built C:/afq-sets --config validation/config --sets heldout-5 --out .cursor/loops/afq-out/built-selftest < /dev/null > .cursor/loops/afq-m1-selftest.txt 2> .cursor/loops/afq-m1-selftest-progress.txt`
       - Expected: exit 0; `SET heldout-5 DIFFERENCES: 0` and `M1 DIFFERENCES TOTAL: 0`; the pinned items all `yes`, with the stay-out line `h5-17:L15m`; the product's credit row QT 0 silent / 0 failing, extra flagged 15, stay-out newly flagged `0/1/0`, FAIL, R3 `2/1`; the D8 section reads "(compared only when all seven sets ran)".
    2. The overnight run, all seven sets, in the background (about four hours: half of Task 0.3's 7.9 h, since two compositions run per encounter, not four):
       `.venv/Scripts/python.exe .cursor/loops/afq-measure-built.py --docs C:/afq-sets/docs --built C:/afq-sets --config validation/config < /dev/null > .cursor/loops/afq-m1.txt 2> .cursor/loops/afq-m1-progress.txt`
       - Expected: exit 0; every `SET <set> DIFFERENCES: 0`; the D8 row `product | QT` equal to the gate's `V4gs | QT` row (harm met no, quoted 1/0, new unsupported 0, new errors 0, pushed over R3 0, the 50 newly failing 0, silent h2 4 and h6 8, failing h2 2 and h6 7, GATE-CAPABLE no, IMPROVEMENT yes); last line `M1 DIFFERENCES TOTAL: 0`.
    - Any difference, or any `[refused]` or `error` line, pauses for the practitioner under the stop rule above (D13 available); the named differences say where. M.1 is done only when the overnight run is recorded here.
  - Recorded 2026-11-17 (leg mx2), from `.cursor/loops/afq-m1.txt` (293 lines, ids and counts only), read by exact path:
    - How it ran: both runs were made by the composer from the AGENT shell, at `4a0081d` with `desktop/` clean, the installed app closed, on mains power with the lid open, in the background with `< /dev/null` (C7's conduct items).
      - The script reads the saved documents under `C:\afq-sets\` and the developer models folder, and writes only under `.cursor/loops/`. That the agent shell reads that models folder is recorded in `AGENTS.md`'s Last Session (2026-11-06: only writes there are virtualised).
      - This plan's C7 has no rule against agent-run measurements, so this is recorded plainly as agent-run.
    - The self-test (`--sets heldout-5`, `.cursor/loops/afq-m1-selftest.txt`): exit 0, `SET heldout-5 DIFFERENCES: 0`, `M1 DIFFERENCES TOTAL: 0`, stay-out quote `h5-17:L15m`, 1892 s, as expected. Then the practitioner chose "Start it now (Recommended)" for the full run (2026-11-17).
    - The full run (`.cursor/loops/afq-m1.txt`, progress in `afq-m1-progress.txt`): started about 10:15 and finished 14:44, rc=0.
      - The run line: HEAD `4a0081dc0428928681746ce4905bbb82058ac24a`, desktop clean; rule v6; suggestions confirm-all; prose narrative; config `validation/config`; the seven sets. Every set's saved documents read "whisper medium at `22feec42deb8868146e786ddaa55524486f3a28e`" (50, 22, 22, 23, 22, 22, 22), and every encounter was measured.
      - Per set: encounter-level differences 0, gate-table cell differences 0, pinned-item differences 0, and 0 segments placed by the baseline but not by the product. `SET <set> DIFFERENCES: 0` for all seven. The file holds no `refused` or `error ` line.
    - D8 across the sets (QT), every cell. Columns: harm met; quoted mat/other; new unsupported; new errors; sets pushed over R3; the 50 newly failing; silent h2, h6; failing h2, h6; GATE-CAPABLE; IMPROVEMENT.
      - `none (re-run) | QT`: yes; 0/0; 0; 0; 0; 0; 10, 13; 4, 10; no; no.
      - `product | QT`: no; 1/0; 0; 0; 0; 0; 4, 8; 2, 7; no; yes.
      - "D8 cell differences (vs afq-gate-3.txt rows none QT and V4gs QT): 0".
    - Pinned items per set, expected / product, each read `yes`:
      - silent facts / failing encounters (QT): `scripts`, `heldout`, `heldout-3`, `heldout-4` and `heldout-5` 0/0; `heldout-2` 4/2; `heldout-6` 8/7;
      - stay-out lines quoted: `heldout-5` `h5-17:L15m`; `-` on the other six;
      - new unsupported / error-grade / checker failures: 0/0/0 on all seven;
      - pushed over its R3 ceiling: no on all seven;
      - the 50 pass (rule v6, QT): PASS.
    - The product's rows, for reference (each equal to the gate's `V4gs` row, by the comparison):
      - Joins (join table): `scripts` 13 (1 next-patient join), `heldout` 9, `heldout-2` 11, `heldout-3` 4, `heldout-4` 4, `heldout-5` 7, `heldout-6` 18; carries 0 everywhere.
      - Credit row QT, silent / failing / facts credited / extra flagged / stay-out newly flagged mat/other/tail / Rule v6 / R3:
        - `heldout-2` 4/2/15/32/0/1/0/FAIL/0/1;
        - `heldout-5` 0/0/0/15/0/1/0/FAIL/2/1;
        - `heldout-6` 8/7/11/30/1/1/1/FAIL/2/1.
      - QT+m extra flagged differs from QT only on `heldout-4`, 13 against 12.
    - Timing (s): `scripts` 3067, `heldout` 1669, `heldout-2` 2159, `heldout-3` 2099, `heldout-4` 1750, `heldout-5` 1886, `heldout-6` 1903. That is 14533 s, about 4.0 h, as planned for two compositions per encounter.
    - Against the "Expected" text: every line matches. The self-test's figures and the overnight D8 row `product | QT` read exactly as written above them, and the last line is `M1 DIFFERENCES TOTAL: 0`. No line in the file differs from the expectation.
    - So D8's improvement line is re-confirmed on the built product (the Validation section's "Phase M: improvement exit"). M's reports are measurements, not runs of record (D9).
  - The gate-capable variant of M.1 (the seven sets re-run in full as predictions v7's source): NOT BUILT, improvement exit (Task 0.6, 2026-11-17).

### Phase D — Documents
Phase D DONE 2026-11-17 (stage-4, legs dx1–dx4): D.1–D.3 written and converged in review rounds 19–21. D.4's approvals are recorded in the practitioner's words, and the codex document pass converged: slice A at round 22, slice B at round 24 after round 23's LOW was fixed. Its edits are uncommitted (autocommit off). The commit of Phase M and Phase D together is the composer's next act, on the practitioner's "Commit after the peer pass (Recommended)".
Each document's line endings are kept (C8; check `git ls-files --eol` first). No document claims anything the code does not do.
- [x] 🟩 **D.1 Security and design documents.** DONE 2026-11-17 (leg dx1; review rounds 19–21, converged). The documents quote the DRAFT count line and hint (`ui/models.py`), and change with them at D.4. [2026-11-17, leg dx2] Approved as drafted at D.4, so the quoted wording stands and the documents now record it as approved.
  - Where each restated threat-model sentence sits now (re-located by search at this leg; the plan's `:NNN` cites below are as written at Task 0.7): the config paragraph's D11 carry clause `:354-363` (a 0.3.7 clause added); Check 4's second code `:528-578`, its "an uncued patient line with no flagged word stays unwarned" sentence at `:564-568` (a 0.3.7 parenthesis); NEXT PATIENT `:579-666`; THE TRIM `:667-704`; the bounded carry's next-patient widening `:705-711` (a 0.3.7 parenthesis) and its CONTINUATION RESIDUE after it; THE CORRECTION CARRY `:722-740` (a 0.3.7 sentence at `:737-740`); THE UNSURE MARK `:741-767`; THE ANSWER HOP `:768-829` and THE REPLY FLAG `:830-862` (new, with residues (1)–(10) and (a)–(f)); item 3's "an uncued line of another speaker's … still unflagged" `:878-884` (a 0.3.7 clause); surface 5's "Readers that no longer act on a suspect word" `:1069-1086` (a 0.3.7 clause at `:1077-1080`) and "Rolling back" `:1087-1107` (a 0.3.7 sentence at `:1104-1107`); "Phase 3B (coverage)" residue (s3) `:2469-2490` (the `h5-17` sentence at `:2483-2490`). MEASUREMENT SCRATCH already named `afq-measure-kept.py` (unchanged).
  - `docs/security/data-flow-map.md`: flow 7's suspect-reader sentence; flow 10 a new subsection "The answer hop and the reply flag (… 0.3.7)"; flow 11's cue clause (a sibling of flow 10); flow 17's `other_voice` sentence; flow 26's reply credit, second computation and residue line; flow 27's REPLAY drift by design and MEASUREMENT SCRATCH's `afq-measure-kept.py`; flow 29's joined lines as placed context and the `h5-17` case.
  - `docs/design-system.md`: the "Flagged lines are findable" bullet (the reply flag's reach, the draft count line) and both `clinician_line_omitted` hint quotes (the draft clause; the tooltip's short form unchanged).
  - `docs/security/threat-model.md`: Phase 3A surface 2 gains THE ANSWER HOP and THE REPLY FLAG, with every named residue: Task 0.6's four accepted residues, the bare "No.", and learned-cue amplification.
    - Also the residues review round 15 (Step H's H3, SEC-001 and SEC-002) found in the code, each a consequence of D1 (b), D1 (a) and the unlimited reach as built:
      - a spoken instruction given as a LATER line of the reply turn is quoted too, beyond residue (3)'s first reply (pinned `joins-a-later-reply-dont-write-this-down`; the practitioner's word at D.4 — accepted as a named residue 2026-11-17);
      - a wrong speaker label: a patient's cue-routed question labelled as the clinician opens a window and the real clinician's reply joins; a clinician's own uncued line labelled as another speaker joins as a "reply";
      - a false question by its opening word (a WH-opener statement, or an auxiliary with a pronoun) opens a window when guard G's routing passes;
      - where no next-patient boundary is found, a next patient's whole reply turn joins after the clinician's cued question. That is wider than the bounded carry's one hop (NEXT PATIENT residue (a)), and the reply flag likewise stops only at a detected cut;
      - a third speaker (a carer, an interpreter) may be the reply speaker (D1 (b); only the first reply's speaker joins after that);
      - the `h5-17` suggestion-stage quote, beside "Phase 3B (coverage)" residue (s3).
    - The sentences the build makes false are restated (`:354-357`, `:531-534`, `:698-700`, `:712-720`, `:771-772`, the Check 4 text `:522-547`, surface 5's readers of a suspect word `:958-971`), re-located by search first, since the file changed after `50a8a2b`.
  - `docs/security/data-flow-map.md` flows 7, 10, 17, 26, 27 and 29.
  - `docs/design-system.md`: the flag's reach and the copy.
- [x] 🟩 **D.2 Testing documents.** DONE 2026-11-17 (leg dx1; review rounds 19–21). `docs/testing/validation-harness.md`: "Metric amendment 2026-11-17" after the 2026-11-09 amendment (a loosening decided after run 9; the next rule inherits it; no rule file changes; rule v6's verdict of record stays run 9's; `docs/pilot/exit-gate.md` unchanged; pins `TestReplyCredit`, `TestReport`); the five Known limits each gain a 0.3.7 sentence; a new section "Answer-hop simulation (answers-follow-question plan, 2026-11-15 → 2026-11-17)" before "Custody and privacy" holds Task 0.8's method, tables (ids and counts), the decision and M.1's measurement — no row starting `` | ` `` inside the three rule sections `TestHarnessDocument` splits on. `docs/testing/shipping-gate.md`: "Addendum — version 0.3.7" (what the app does, not a rubric change). `docs/testing/kept-recordings.md`: "From 0.3.7" (the expected drift by design: "Sections missing" can fall, "Check reviews" and "Check errors" can move, "Clinician lines omitted" unchanged). `[2026-11-17, leg dx3, review round 23 PR-LOW-040]` Corrected: "Sections missing" is unchanged by the hop (it adds lines only to a section its question already fills, and the column counts presence only).
  - `docs/testing/validation-harness.md`:
    - the reply credit logged as a loosening the next rule inherits (D9);
    - the Known limits "Material facts in an uncued sentence", "Section placement is not measured", "Small talk and spoken instructions", "End of consultation and new patient", "Spoken contradictions";
    - M.1's measurement.
  - `docs/testing/shipping-gate.md`: a 0.3.7 note on what the app does, not a rubric change.
  - `docs/testing/kept-recordings.md`: the expected drift.
- [x] 🟩 **D.3 Practice, pilot, release and project documents.** DONE 2026-11-17 (leg dx1; review rounds 19–21). The clinician review guide's two 0.3.7 lines (steps 2 and 6), each marked "draft, awaiting your approval", and its draft-history line; the practice README's dated line says they await the practitioner's approval. `docs/pilot/README.md` step 3: 0.3.7 has no validation run, shadow on, no run 10, `exit-gate.md` unchanged. `docs/pilot/exit-gate.md` UNCHANGED (D9), as this plan and the harness document's amendment and simulation section say. `docs/release/pilot-builds.md`: "Rolling back below 0.3.7" (no data step). PLAN.md: a delivery note under Phase 3; `docs/architecture/phase-history.md`: a short "Answers follow their question" section (the Current Status paragraph moves there at P.5); `AGENTS.md`: the carry/next-patient pointer and the suspect-reader pointer, and Current Status (a Phase M / Phase D bullet and the NEXT bullet). `CHANGELOG.md`'s 0.3.7 entry was read against the documents and left unchanged (still accurate). `docs/pilot/findings-register.md` untouched (P.5's).
  - `docs/practice/`: the clinician review guide's 0.3.7 lines and the README's approval record.
  - `docs/pilot/README.md`.
  - `docs/pilot/exit-gate.md` is UNCHANGED, and the plan and the harness document say so (D9).
  - `docs/release/pilot-builds.md`: "Rolling back below 0.3.7", no data step.
  - `PLAN.md`'s delivery note, `docs/architecture/phase-history.md`, and `AGENTS.md` (the carry and suspect-reader pointers, Current Status).
- [x] 🟩 **D.4 Approvals and the documents' peer pass.** DONE 2026-11-17 (legs dx2–dx4). Both approvals and SEC-001's acceptance are recorded in the practitioner's words (leg dx2). The codex document pass converged: slice A at round 22 (0 findings); slice B at round 24 (0 findings), after round 23's one LOW (PR-LOW-040) was fixed in leg dx3. The composer's gate over that fix and the comment change was green: 10937 passed, 9 skipped (`.cursor/loops/stage-4-dx3-gate.txt`).
  - The practitioner approves or rewords the count line's parenthesis and the hint clause (D5). Any rewording is applied in `ui/models.py` with its pins, and the composer's suite runs.
  - The practitioner approves the review guide's 0.3.7 lines before P.3.
  - The practitioner's word on review round 15 SEC-001: a spoken instruction given as a LATER line of the reply turn is quoted. Recommended: accept it as a named residue, the class of residue (3) and of the bounded carry's CONTINUATION RESIDUE. The app honours no spoken instruction, the clinician reviews every note, and shadow mode stays on. Declining needs a new dated guard decision with its own measurement (Task 0.6's "Decline (3)" route).
  - Then the cross-family codex pass on D.1–D.3, the documents as their own slices, each claim checked against the code.
  - Done when: both approvals are recorded in the practitioner's words and the peer pass has converged.
  - Recorded 2026-11-17 (leg dx2). The practitioner answered in chat on 2026-11-17; the composer asked each item with the text quoted in the leg dx1 handoff. Their words, verbatim:
    1. The app wording (the count line's parenthesis and the hint clause): "Approve as drafted (Recommended)". No rewording, so `ui/models.py` and its pins are unchanged and no suite run is owed for it.
    2. The clinician review guide's two draft 0.3.7 lines: "Approve as drafted (Recommended)".
    3. Review round 15 SEC-001 (a spoken instruction given as a LATER line of the reply turn is quoted): "Accept as a named residue (Recommended)".
    4. The commit: "Commit after the peer pass (Recommended)": Phase M and Phase D are committed together on `main` once the codex document pass converges; not pushed; the composer commits.
  - Applied in the documents (leg dx2): the review guide's two inline markers read "(approved 2026-11-17)" and its draft-history line "approved by the practitioner on 2026-11-17"; the practice README "these lines approved by the practitioner on 2026-11-17"; the threat model's THE ANSWER HOP residue (2) "accepted by the practitioner 2026-11-17 as a named residue (Task D.4)" and THE REPLY FLAG's wording "approved by the practitioner 2026-11-17, Task D.4"; the harness document's "Small talk and spoken instructions" limit "accepted by the practitioner 2026-11-17 as a named residue at its Task D.4"; the design system's three draft markers and flow 10 of the data-flow map recorded as approved 2026-11-17; AGENTS.md's Current Status.
  - Remaining: the cross-family codex pass on D.1–D.3 (and these dx2 replacements). D.4 stays 🟥 until it converges.
  - The codex document pass (2026-11-17): slice A, round 22 (`stage-4-d4a.p1`), 0 findings, CONVERGED; slice B, round 23 (`stage-4-d4b.p1`), 1 LOW, PR-LOW-040, verified real and fixed in leg dx3 (kept-recordings.md's "Sections missing" expectation; two plan siblings). Leg dx3 also changed the two `ui/models.py` comments that called the copy "a draft until D.4" (comments only). Remaining: the composer's suite gate over the comment change, then round 24, slice B's confirmation of the fix delta. D.4 is marked 🟩 only after round 24 converges.
  - [2026-11-17, leg dx4] The composer's gate was green (ruff and mypy clean, pytest 10937 passed, 9 skipped). Round 24 (`stage-4-d4b.p1`, peer round 2 of cap 5) found 0 findings: it confirmed PR-LOW-040's fix, both plan siblings' dated corrections, that no sibling remains, and that the `ui/models.py` diff changes comments only. Slice B CONVERGED, so D.4 is done.

### Phase F — The build of record
- **NOT BUILT — 2026-11-17, Task 0.6's improvement exit (D9).** F.1 and F.2 stay 🟥 for the record and are not executed in this plan, and `heldout-7` is never created, so the blind rule (D11, C6) never applies.
- **The build-of-record part (F.3) DONE 2026-11-17 (stage-5, leg fx1).** F.1 and F.2 stay NOT BUILT.
- [ ] 🟥 **F.1** NOT BUILT (gate-capable only): rule v7, the `v7` label branch, `TestRuleV7`, the harness document's "Rule v7", predictions v7 and the pre-registration (D10).
- [ ] 🟥 **F.2** NOT BUILT (gate-capable only): `heldout-7`, its plumbing (Key Findings' site list), the blind authoring and the blind period.
- [x] 🟩 **F.3 The build of record** (either building exit). DONE 2026-11-17 (stage-5; the composer's steps from the agent shell, recorded by leg fx1).
  - On the practitioner's word (C7): push, CI green, the `Release` run, and the attestation checks (`gh attestation verify`; from an agent shell, read its exit code).
  - `docs/release/pilot-builds.md` records 0.3.7 as a build of record.
  - Done when: the release is attested and recorded.
  - Recorded 2026-11-17 (leg fx1). The practitioner's word to push: "Push and build 0.3.7 (Recommended)" (2026-11-17). The composer then, from the agent shell:
    - `git push origin main`: `bf1cb7f..e79be57`.
    - CI run 44030371305 on `e79be57`: success (desktop Python 3.12, desktop Python 3.14, extension).
    - `Release` run 44031862110 (`workflow_dispatch` on `main`, head `e79be57401b2b49af172e98e463ec09f1d48a6a3`): success. The artifacts are in `C:\scribe-release\0.3.7\` (flat, as 0.3.6's folder): `ClinikoScribe-0.3.7-setup.exe`, `SHA256SUMS.txt`, `BUILD-INFO.txt`, `models-manifest.json`, `attest-exe.json` and `attest-sums.json`.
    - `BUILD-INFO.txt`: `version=0.3.7`, `commit=e79be57401b2b49af172e98e463ec09f1d48a6a3`, `tree=clean`.
    - `SHA256SUMS.txt`, checked with `tr -d '\r' < SHA256SUMS.txt | sha256sum -c -`: all three OK. Installer `6ac7747fbdea16a5e0c8c40103ba695a96ec3156e29013a421d2cb72d48136d2`; `models-manifest.json` `10a834937fe8c783d3e387dcdb4c2b74c3c290db97c626e38be4deba3fa9930a`, byte-identical to 0.3.6's, so the existing model pack serves it.
    - `gh attestation verify` for the installer and for `SHA256SUMS.txt`: exit 0 each (agent shell, so the exit code is the evidence). `--format json`: source `refs/heads/main`, digest `e79be57`, run 44031862110 attempt 1.
  - `e79be57` is the hardened commit `4a0081d` plus documents, the plan and two code comments only.
  - `docs/release/pilot-builds.md` (leg fx1): the 0.3.7 row (in the 0.3.6 row's shape; "Not yet installed (the answers-follow-question plan's P.3)"); "Rolling back below 0.3.7" now says the build exists and is not yet installed. The sibling "Rolling back below 0.3.6" still said 0.3.6 had no build of record; it now says built of record 2026-11-10 and installed by 2026-11-14 (a LOW record-only fix of the same class, auto-disposed Fix-now in this leg).
  - Not done here: the re-verify from a normal terminal, which comes first at P.3.

### Phase P — The practitioner (improvement path)
- **NOT BUILT — 2026-11-17, Task 0.6's improvement exit (D9).** P.1, P.2 and P.4, the gate-capable path, stay 🟥 for the record and are not executed in this plan. Shadow mode stays on.
- [ ] 🟥 **P.1** NOT BUILT (gate-capable only): validation run 10 against predictions v7.
- [ ] 🟥 **P.2** NOT BUILT (gate-capable only): the shadow-mode decision on a passed run 10.
- [x] 🟩 **P.3 Installing 0.3.7** `[decision]`. DONE 2026-11-17: installed with shadow mode on, smoke PASS on all four checks (recorded in leg px1 from the practitioner's words, relayed by the composer; a synthetic mock only, nothing clinical).
  - Options: install with shadow mode on, then the install smoke (Validation / Verification); or do not install, and 0.3.6 stays.
  - Decide after: M.1 and the review guide's approval (D.4).
  - The decision, the practitioner's chosen label verbatim: "Install, shadow on (Recommended)".
  - Re-verify and install. The practitioner's answer: "Ran the install script". It was a composer-written PowerShell script (git-ignored, not a repository file), run from a normal terminal. It checked `BUILD-INFO.txt` (version 0.3.7, commit `e79be57`, `tree=clean`), ran `gh attestation verify` on the installer and on `SHA256SUMS.txt` (each had to exit 0), and compared the installer's SHA-256 with the recorded hash and with `SHA256SUMS.txt`, stopping before `setup.exe` on any failure. All passed; then `setup.exe` ran (no model pack needed). 0.3.7 is installed on this computer 2026-11-17, over 0.3.6, with shadow mode on.
  - The install smoke, one synthetic mock consultation (the practitioner's own voice for the clinician, a computer voice for the patient). A first take was discarded because speaker labelling put both voices under one label: the known labelling weakness (`AGENTS.md` Known Issues, "Diarization quality tuning"), not new in 0.3.7. The second take labelled the two voices apart, with one clinician fragment under the other speaker's label.
    1. The reply beside its question: PASS. A cue-routed clinician question in Presenting complaint was followed in the note by the patient's two uncued reply lines.
    2. The `[flagged]` reply after a left-out question: PASS. An uncued clinician question drew "A line you said is not in the note (1)" with the approved hint clause "(if it was a question, its answer is flagged too)". The chooser's count line read 3 flagged lines with the approved parenthesis; with "Show flagged or suggested lines only" ticked, exactly three lines were `[flagged]`: the question and the patient's two replies after it.
    3. Nothing extra in Copy: PASS. Copy note and Write draft to Cliniko were refused with the shadow-recording message; no `[flagged]` mark or extra line in the note panel.
    4. The audit CSV's `app_version`: PASS. The newest row reads 0.3.7.
  - Also observed: an ordinary cue-routed line (Objective examination) routed as before; the Narrative prose rendered both sections (14.2 s) with the joined reply and the existing number mark carried ("[includes 1 line check: number]", the word "first" read as a number: existing Check 1 behaviour); the suggestion stage said "No suggestions."; the session was ended with Delete note and complete without one.
  - Recorded in `docs/release/pilot-builds.md` (the 0.3.7 row and "Rolling back below 0.3.7"), `AGENTS.md`, `CHANGELOG.md` and `docs/architecture/phase-history.md`.
- [ ] 🟥 **P.4** NOT BUILT (gate-capable only): the `h7-` cases, the diagnosis and the end of the blind period.
- [x] 🟩 **P.5 Records and close.** DONE 2026-11-17 (leg px1; the record below the task text).
  - The findings register:
    - F-155 gets a dated control line and stays `controlled` (D9);
    - a row per accepted residue the measurement shows, within the closed vocabularies (`test_pilot_docs.py`).
  - `AGENTS.md`, `CHANGELOG.md`, the lifecycle state and the Retained Follow-Up Items, then `/document`.
  - The practitioner deletes `C:\afq-sets\` (synthetic only).
  - Done when: the plan's lifecycle state reads Completed (or Completed — Follow-ups Retained).
  - Recorded 2026-11-17 (leg px1):
    - The findings register (`docs/pilot/findings-register.md`), within `test_pilot_docs.py`'s closed vocabularies, month-only and id-free:
      - F-155's control line rewritten with its date: since 0.3.7 (2026-11) a reply joins its in-note question or is flagged, and other uncued lines stay unwarned. It stays `controlled` (D9).
      - F-170 (`h5-17`, high, `cross-patient`, `note-routing`, controlled): the `h5-17` residue, a line of the next patient added through a suggested section in the gate configuration, not on a joined line. M.1 shows it (`h5-17:L15m` on `heldout-5`). The category and part follow F-165 and F-168.
      - F-171 (`—`, medium, `workflow`, `checker`, controlled): residue (1), lines that must stay out newly `[flagged]` under QT, 2 material / 9 other / 3 at or after the tail over the seven sets. M.1 shows it (equal to `afq-gate-3.txt`'s V4gs QT rows). Medium, not high: a flag adds nothing to the note and does not hold Save back (D4), so no wrong content enters without the clinician's own Add.
      - No row for residue (2), QT's real-speech load: it was measured by Task 0.4b, not by M.1 or the smoke (whose three flagged lines were the question and its two replies, the expected flag). No row for residue (3), a first-reply "don't write this down": clean by absence on the seen sets, so nothing shows it; Task 1.1 pins it. Both stay Retained Follow-Up Items below. D.4's later-reply residue (SEC-001) is likewise unshown and retained.
    - `AGENTS.md`: the Current Status paragraph closed and shortened, the full one moved verbatim to `docs/architecture/phase-history.md` with a dated closing line; Tech Stack and Local Run Steps name 0.3.7 installed since 2026-11-17; Last Session (worked on, a pattern, next priority), the Diarization Known Issue's dated smoke observation and Documentation Status updated.
    - `CHANGELOG.md`: the 0.3.7 entry says built of record and installed 2026-11-17 with shadow mode on, and that the copy was approved at D.4 (its "draft until D.4" sentence was stale), with M.1 and the register rows.
    - `docs/release/pilot-builds.md`: the 0.3.7 row's install and smoke, in the 0.3.6 row's shape; "Rolling back below 0.3.7" says installed.
    - `/document`'s sweep for 0.3.7's install state also found `.cursor/plans/plan-suggestion-repair.md` (its retained "Answers follow their question" item and its note that 0.3.7 "will not exist"): dated reconciliation lines added. `docs/pilot/README.md` and the practice and security documents name no installed version; the pilot plan's P.5 lines are dated records (its 2026-11-10 line says 0.3.6 was installed then) and stay as written, and this exit adds no P.5 decision (shadow mode stays on).
    - The lifecycle state is Completed — Follow-ups Retained.

## Retained Follow-Up Items
- **The four residues Task 0.6 accepted by name** (and D.4's fifth). Each is named in the threat model's THE ANSWER HOP / THE REPLY FLAG and the harness document's limits.
  - (a) The `h5-17` next-patient quote through the suggestion stage, not on a joined line: register F-170.
  - (b) Residue (1), lines that must stay out newly `[flagged]` under QT (2 material / 9 other / 3 at or after the tail over the seven sets): register F-171.
  - (c) Residue (2), QT's real-speech load (median 11-15 extra flagged lines per recording on Task 0.4b's two recordings): no register row, since neither M.1 nor the smoke shows it.
  - (d) Residue (3), a first-reply "don't write this down" is quoted: clean by absence on the seen sets, pinned by Task 1.1; no register row.
  - (e) D.4's SEC-001: a later-reply "don't write this down" is quoted too; no register row.
  - Recommended next action: watch for them in shadow use; a flag load or a quoted instruction seen there is a new register row.
  - Risk if deferred: ux-degradation: extra `[flagged]` lines to read past; correctness for (a), (d), (e) only through the clinician's own Add or a missed review, with shadow mode on.
  - Revisit by: shadow consultations on 0.3.7, or the next plan that touches routing.
- **D8's real-speech line, unmeasured** (Task 0.4b: n enrolled 2 < 3), overridden by the practitioner by name at Task 0.6. On the two recordings the hop joined 0 lines, cause unknown (Excluded's dated line).
  - Recommended next action: re-run `afq-measure-kept.py` (frozen, C5) once at least three kept recordings have the clinician enrolled, if a later plan needs the real-speech numbers.
  - Risk if deferred: correctness: the hop's reach on real speech is unknown.
  - Revisit by: three enrolled kept recordings, or the next routing plan.
- **The Deferred items above** stay deferred, unchanged: a left-out question added from the Line list does not bring its reply; a long reply's later lines get no mark; the single derived question-and-answer line; the window-edge carry and "add all suggested lines".
- **The speaker-labelling observation from the P.3 smoke**: a first take put both voices under one label, and the second still put one clinician fragment under the other. This is the existing Known Issue (`AGENTS.md`, "Diarization quality tuning", with a dated 2026-11-17 observation), not a new item; its revisit point is unchanged.
- **The practitioner deletes `C:\afq-sets\`** (synthetic only; the agent must not, C7). The git-ignored scratch under `.cursor/loops/` (`afq_lib.py`, the measurement scripts and their outputs) may go with it.
  - Risk if deferred: minor (disk space).
  - Revisit by: the next session.
- **The close commit and the push, on the practitioner's word** (C7). `5e83b4a` (F.3's record) is committed and not pushed; P.3's and P.5's records are uncommitted. The composer runs the suite gate and the codex document pass first.
  - Risk if deferred: minor: the close lives only on this computer until pushed.
  - Revisit by: this close.

## Follow-Up Continuation Notes
1. **What turns shadow mode off is still open.** 0.3.7 is an improvement, not gate-capable: in the gate configuration `heldout-2` keeps 4 silent facts in 2 encounters and `heldout-6` 8 in 7. The plan's "Deferred / Out of Scope" note stands: the zero-silent-omission gate may be out of reach for patients' uncued lines by any rule tried so far, and what turns shadow mode off would then be a pilot-level decision for the practitioner (`plan-pilot.md`, the 2026-10-09 stop rule and Constraint 12). A next routing plan would start from where the remaining silent facts sit (Task 0.3's tables; the Deferred "later lines" item).
2. **Any change to the hop's form or the reply credit** is a new dated decision with the simulation repeated (D1, D4; the harness document's "Answer-hop simulation"). The scratch under `.cursor/loops/` is the method's record until it is deleted; the method is also written in the harness document.
3. **A blind run of this rule** needs a fresh held-out set and rule v7 (D10 and D11 as written, never applied): `heldout-2` is spent and `heldout-6` is seen.

---
*Plan saved to: .cursor/plans/plan-answers-follow-question.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
*Sections marked (Only if relevant) can be omitted when genuinely not applicable, but never omit decisions, constraints, verification steps, or integration knowledge that a fresh session would otherwise have to rediscover.*
*For lightweight plans, plans with fewer than 5 tasks, or plans created without a preceding `/explore` discussion, sections with no real content should be marked `N/A — simple feature` rather than padded with placeholder structure.*
*State-once convention (new plans): state each cross-section contract — a critical constraint, design decision, invariant, or other normative rule — once in its canonical section, and have every other section point to it rather than restate it. Scope guard: this governs cross-section normative duplication only — the Task Specification Standard (in `/create-plan` and `/review-plan`) and task-local detail are untouched, and a plan recording `fast/medium involved` in its Executor tier may keep extra restatement where it helps the fast executor. It applies to new plans as they are written; never retroactively rewrite an existing plan to conform.*
_Plan drafted in Plan Mode and hardened by `/review-plan` on 2026-11-15 (Fable 5.2; exploration began on Opus 5.5 before the practitioner switched the model). Critique gate: three parallel lenses (Coverage and risk / Practicality / Simplicity), every finding dispositioned in the plan. Phase 0 is hardened in full; Phases 1–P are outlines hardened at Task 0.7 (the practitioner's choice). Planning only: nothing built, nothing committed._ _Task 0.7 (2026-11-17, executor leg ax11, a scoped `/review-plan`) hardened the improvement exit's phases and marked the gate-capable ones NOT BUILT: Review Findings Log Round 12._
