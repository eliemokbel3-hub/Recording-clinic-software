# Feature Implementation Plan
**Feature:** answers-follow-question (a patient's uncued reply joins the note beside the clinician's in-note question; version 0.3.7 only on a GO; validation run 10 only if gate-capable)
**Overall Progress:** `0%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: None. It continues `.cursor/plans/plan-suggestion-repair.md` (Completed — Follow-ups Retained): its Deferred item "Answers follow their question", TRIGGERED by S.4 on 2026-11-15, and its Follow-Up Continuation Note 1. "SR" below means that plan; "NCD" means `.cursor/plans/plan-note-content-design.md`.
- Follow-up plans: None.

## Goal
Decide, on measured numbers, whether a deterministic rule can close the class that failed validation run 9 (patients' uncued replies, 23 of 24 silent omissions on the blind `heldout-6`), and build it only if it can. The rule: a patient's uncued reply to a clinician's question that is in the note joins the note beside that question; when the clinician's line is itself left out, its existing warning also covers the reply, which is shown `[flagged]`. No language model. The rule is simulated at audio level and on real speech before any product code changes. Three exits: gate-capable (build, then validation run 10 on a fresh blind `heldout-7`), improvement (build, shadow mode stays on, no blind set spent), or close with no change.

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
- **`heldout-7` and rule v7 sites** (gate-capable exit; for Task 0.7): NCD's F.2 list (`plan-note-content-design.md:2044-2060`) plus `test_pilot_docs.py:132`, `:341`; `scripts/lint_held_out_plugin.py:88` and `scripts/lint-held-out-set.py`'s docstring; `docs/pilot/findings-register.md`'s id rule; `test_validation_harness.py:3427-3461` (`rule-v7-test` becomes `rule-v8-test` when a `v7` label branch lands); `.github/workflows/ci.yml:65-82`; `docs/pilot/README.md`. Template edits: `ncd-brief-leak.py` (`OUT`, `RUNNER_PROMPT`, `EDITS` line 1 and h2 → h7, the `:96-113` guard; `SOURCE` stays `validation/heldout-2`), the author prompt (`h6-01.json` → `h7-01.json`), `ncd-heldout6-author-run.sh:2-9`, `ncd-heldout6-tails.py:21`, `:27`, `:57-61`. The brief's behaviour text is a Task 0.7 question (`validation/heldout-6/SPEC.md:9` tells the author an uncued line "can be left out").
- **The six version strings:** `desktop/pyproject.toml:7`, `desktop/src/scribe_desktop/__init__.py:3`, `extension/package.json:4`, `extension/package-lock.json:3` and `:9`, `extension/src/manifest.ts:29`. No desktop test pins 0.3.6.
- **Line endings:** plans and `test_pilot_docs.py` are LF; `AGENTS.md`, `CHANGELOG.md`, `docs/testing/validation-harness.md`, `docs/security/threat-model.md`, `docs/security/data-flow-map.md`, `validation.py` and several test files are CRLF in the working tree. Check `git ls-files --eol` before any byte-level edit.
- **Lessons that apply** (`docs/lessons.md`, `AGENTS.md` "Pattern worth knowing"): the agent shell reads the developer models folder but its writes under `%LOCALAPPDATA%` are virtualised; every Python call takes `< /dev/null` (a heredoc on stdin hangs); long runs in the background, mains power, lid open, the installed app closed; a scoped executor leg runs no Python and cannot read a folder outside the repository, so the composer runs the scratch and copies outputs into a git-ignored `.cursor/loops/afq-out/`; bash redirection writes UTF-8 with CRLF and PowerShell's `>` writes UTF-16; paths in record scripts are raw strings or forward slashes; a top-level `C:\` folder cannot be deleted from the agent shell; a codex pass is sliced (at most about 15 files) and documents are their own slice; a re-run reproduces counts and verdicts, not words.

### Shared helpers (used by more than one phase)
- `.cursor/loops/afq_lib.py` — the rule variants, the credit variants and the counters: Tasks 0.1–0.4b, and Phase 1's one-off comparison.
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
After Finish, the note holds the patient's reply right after the clinician's question it answers, as a verbatim quoted line with the usual check marks. Where the clinician's own line was left out, its warning is unchanged and the Line list shows both that line and its reply `[flagged]`.

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
- **D10 — Rule v7 (gate-capable exit only).** Rule v6's predicates and ceilings with the set schedule moved (`heldout-6` a reported row counting marked R1; `heldout-7` rule v6's `heldout-6` row field for field), and the reply credit listed as that cycle's loosening with its second verdict (D5). Every set runs `--suggestions confirm-all --prose`. The pre-registration follows the `heldout-5` model (falsifiers, bands, outcomes fixed in advance) and says beforehand that run 10 may fail on the next-patient count alone: the boundary is unchanged, and where none is found the hop can quote a next patient's reply.
  Still applies to follow-up work: Yes.
- **D11 — The freeze and the blind rule (gate-capable exit).** Rule v7, predictions v7 and the pre-registration are one commit before `heldout-7` exists. From then to run 10 nothing under `desktop/src/` or `scripts/` changes beyond the named plumbing. While the set is blind the suite runs only through `scripts\lint-held-out-set.py validation\heldout-7`; the executor never opens the folder; the author session is launched by the practitioner from a normal terminal.
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
- **C6 — The blind rule and the freeze** (D11), on the gate-capable exit.
- **C7 — Host and conduct.** This Windows host only, never the cloud. Commits and pushes only on the practitioner's word (autocommit off, builds on `main`). Long runs in the background with `< /dev/null`, mains power, lid open; the installed app closed while a model or transcription run is in progress; one build open at a time.
- **C8 — Line endings are kept** as each file has them; plans are LF.

## Validation / Verification
- **Baseline, dry-run 2026-11-15 at `50a8a2b`** (tree clean): in `desktop/`, `ruff check .` — "All checks passed!"; `mypy` — "Success: no issues found in 67 source files"; `pytest -q -p no:cacheprovider` — 10836 passed, 9 skipped (511 s).
- **Phase 0:** the premise (0 mismatches against the shipped harness, replay mode, all seven sets; the text-mode equality); the scratch's self-test counts; the off baseline rows equal to the named report files with the Rule column masked; each table tied to a commit, the whisper model and the built set's folder; the kept-recordings script's dry run over the synthetic pickles and its refusal smoke (no `--enrolment`: exit 2).
- **Build (on a GO):** `ruff check . && mypy && pytest` in `desktop/`, composer-run, after every code task; every changed expectation listed with its reason; the built product replayed over the saved documents equal to the scratch projection (exact, minutes, no audio).
- **Phase M:** improvement exit — the replay above in the gate configuration re-confirms D8's improvement line. Gate-capable exit — the seven sets re-run in full; a masked diff against the confirm baselines; transcript-level cells identical (Status, Segments, Ref words, WER, Spelling-normalised words, Suspect segments, the two attribution-seconds columns, the reference-boundary line); every other differing row is an encounter where the replay lists a join, a credited reply or changed suggestion cells. A seen set that differs unexplained is re-run once at the same commit.
- **Gate-capable exit:** rule v7, predictions v7 and the pre-registration committed before `heldout-7` exists; the suite green through the blind runner; CI green; the release attested (`gh attestation verify`; from an agent shell read its exit code); run 10's verdicts and every column recorded against predictions v7.
- **Install smoke (either building exit):** a mock with a cued clinician question and its reply beside it in the note; a left-out clinician question with its reply `[flagged]`; nothing extra in Copy; the audit CSV's `app_version`.
- Side-effecting commands (set builds, transcription and harness runs, the kept-recordings script, the release, the author session) were inspected, not run, during planning.

## Deferred / Out of Scope
See "Deferred — Actionable Later", "Excluded — Revisit Only If Needed" and "Accepted Assumptions — Revalidate Later" in the Planning Extraction Summary (the canonical lists).

Named now, and not this plan's to decide: if even the best harm-free form is not gate-capable, the zero-silent-omission gate may be out of reach for patients' uncued lines by any rule already tried or rejected. What turns shadow mode off would then be a pilot-level decision for the practitioner (`plan-pilot.md`, the 2026-10-09 stop rule and Constraint 12).

## Current State / Handoff Note
- Last completed step: Planning complete (native plan approved, hardened by `/review-plan` 2026-11-15). Nothing built, nothing committed; this file is untracked.
- Current in-progress step: None.
- Immediate next action: Task 0.1 via `/execute-loop` (its wizard first) or `/execute`. The codex plan peer-review is done: four rounds on 2026-11-15, converged at round 4 (15 findings in all, every one verified and applied; Review Findings Log).
- Open blockers / open questions: None. Pauses to expect: the practitioner's run at 0.4b, the decision at 0.6, every commit and push.
- Critique gate (2026-11-15, three parallel lenses, every finding dispositioned in this plan):
  - Coverage and risk: 1 CRIT (`h5-18`: the first-line rule quotes a non-material line that must stay out → the practitioner's decision, D8's harm line and guard G); 4 HIGH (the flag's harm side → a reported column; the suggestion policy → D7; the loosening convention → D5 and D10; unnamed pins → Key Findings); 9 MED and 2 LOW (D4's form, the fixture mechanism, the real-speech fallthrough, Check 2 errors, documents, the improvement exit, `heldout-7` sites, residues, harm attribution, `provider_name`) → applied.
  - Practicality: 2 HIGH (the real-speech script reviewed and dry-run before it runs → Task 0.4a and C5; which cue file → the practitioner's "Both"); 6 MED and 3 LOW (the script's shape, the simulation recipe, the comparison mechanism, Phase 1's dependence on 0.6, the Phase M comparison, the host split, time, the no-change proof, the scratch's own document entry) → applied.
  - Simplicity: adopted — join and credit measured separately then combined; a joined answer may be followed by one carried piece (no separate comma variant; made its own guarded row of D1's table by peer round 1); S as a counter; V4t text-only; a report line instead of a new column; later phases in outline; Phase M as a replay on the improvement exit; the Phase M decision replaced by a stop rule. Kept as planned — the scratch location, the new helper, the persistence rule, the version order, the install decision after the build.
- Last plan sync: 2026-11-15

## Review History
- 2026-11-15 round 1: 0 CRIT / 1 HIGH / 7 MED / 1 LOW; skew=plan peer-review (codex); action=all nine verified and applied
- 2026-11-15 round 2: 0 CRIT / 0 HIGH / 2 MED / 1 LOW; skew=plan peer-review (codex); action=round 1's nine confirmed; all three new verified and applied
- 2026-11-15 round 3: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=plan peer-review (codex); action=round 2's three confirmed; both new verified and applied
- 2026-11-15 round 4: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=plan peer-review (codex); action=round 3's two confirmed; the one record-only finding applied; CONVERGED

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

## Tasks

### Phase 0 — The simulation and the decision (no product change; C2)

- [ ] 🟥 **0.1 The synthetic scratch and its premise.**
  - Files (new, git-ignored): `.cursor/loops/afq_lib.py` (the D1 rule as a provider subclass with reach V1 / V3 / V4, guard G on or off, switch S, and V4t for text mode; `replies_after` with D4's four sub-variants; the counters), `.cursor/loops/afq-transcribe.py` (from `run8-p3-transcribe.py`: `RULES` rule v6, the seven sets, its `:142-144` dropped; one pickle per encounter), `.cursor/loops/afq-measure.py` (text mode over `validation.reference_document`; `--docs` over the saved pickles; prints ids, counts and section keys only), outputs under `.cursor/loops/afq-out/`.
  - Follows: the simulation recipe in Codebase Integration Notes; D1, D2, D4.
  - Behaviour once done: with no hop and the shipped credit, the scratch reproduces the shipped outcome.
  - Done when: text mode's equality holds on all seven sets (0 mismatches), recorded here with the commit. The replay premise is Task 0.3's.
  - The executor writes; the composer runs (C7; the executor runs no Python).
- [ ] 🟥 **0.2 The self-test at text level.**
  - Run `afq-measure.py` in text mode over the seven sets with `--config validation\config`.
  - Record here (ids and counts only): silent facts before (expected 25 on `heldout-2`, 26 on `heldout-6`, 0 elsewhere); V1 recovered (expected 11) and V4t recovered (expected 17) with what each quotes that must stay out (expected: V4t `hld-17`; V1 without G `h5-18` line 3; with G to be read); joins per set.
  - Done when: each expected count is reproduced, or the difference is explained on this task (the planning counts were estimates). This is a self-test, not a decision table.
- [ ] 🟥 **0.3 The audio-level tables.**
  - Build the seven sets into `C:\afq-sets\<set>` (voices checked first), transcribe each once with `afq-transcribe.py` (each script's clinician enrolled), keep the built folders.
  - Premise: the replay equals each pickled outcome (0 mismatches), and the baseline rows equal `stage-2-c6-off-<set>.md` (and `stage-4-f1-off-heldout-2.md`) with the Rule column masked; if transcript cells differ, re-transcribe that set once and record it. `heldout-6` has no off baseline: record its row.
  - Tables, per set (off, no prose): (1) the join table — V1 / V3 / V4, each with G off and on (V3 printed only where it differs from both): silent facts and failing encounters after, facts recovered, lines that must stay out quoted (material / not), next-patient joins with no boundary found, new unsupported clinical lines, new review marks and new error-grade warnings, joins per encounter, joins across a wordless segment, joins whose reply label disagrees with the label track, carries after a join; (2) the S counter (windows only S would open); (3) the credit table — D4's four sub-variants: facts credited, extra flagged lines, lines that must stay out newly flagged (material / not / at or after the reference tail).
  - The shortlist, mechanical: rank the six forms (three reaches, G off and on) that meet D8's harm line at off by the fewest silent facts on `heldout-2` + `heldout-6` at off under the widest credit (any clinician line, whole turn); ties go to the smaller reach, then to G on. The top three are the finalists; S is added to each if D2's condition holds. If no form meets the harm line at off, the one with the least harm is the only finalist, ordered by, in turn: material lines that must stay out quoted; non-material ones; new unsupported clinical lines; new error-grade warnings and checker failures; sets pushed over their next-patient ceiling; the 50 failing; then the smaller reach, then G on.
  - Each finalist form is composed once in the gate configuration over the saved documents (one model pass, about an hour for the seven sets). From that one composed note the metric walk is repeated for each of D4's four credit sub-variants and for the chooser's wider predicate (the recipe's re-invocation), so every credit configuration has its full D8 lines, with the join-only figures beside.
  - Done when: the tables are on this task with the commit, the whisper model and the folder; each D8 line is marked met or not met per finalist.
- [ ] 🟥 **0.4a The real-speech script, reviewed before it runs** (C1, C5).
  - Files (new, git-ignored): `.cursor/loops/afq-measure-kept.py`, modelled on `run7-measure-kept.py`: `--list` (decrypts nothing; prints n); `--enrolment <WAV>` required; `--config <folder>` required; the refusal order of `replay_kept.py:576-647` (dev channel, enrolment, folder, entries, the crash-report exclusion, the single-instance lock held to the end, offline environment, models, config); ordinals oldest first; each recording re-transcribed in memory (`read_recording`, then `transcribe_in_temporary_store(..., persist_key=False)`), never the stored transcript; all forms read the one in-memory document through the same per-document function as the synthetic entry; an outer by-type error handler.
  - Prints, per ordinal and per finalist form: joined lines; review-severity warnings on a joined line; new error-grade warnings; the net change in review warnings; extra flagged lines; whether the clinician was enrolled. Then one aggregate block: recordings expected (the `--list` count), measured, failed (with the count per error type name), a status line `COMPLETE` (failed 0 and measured equal to expected) or `INCOMPLETE`, n enrolled, n not enrolled, and each median and maximum over the enrolled recordings only (D8). The exit code is 0 only on `COMPLETE`. A custody stop or an interrupt prints its one fixed line (naming the temporary folder to look for, as the precedent does at `run7-measure-kept.py:331-339`) and no aggregate block.
  - Also: the threat model's MEASUREMENT SCRATCH entry (`docs/security/threat-model.md:4864-4898`) and `docs/testing/kept-recordings.md:7` name this script (documents only; needed on every exit).
  - Review: `/review-loop`, then one codex slice over `afq-measure-kept.py` and `afq_lib.py` only (the refusal order, the by-type errors, the print surface).
  - Composer checks: a dry run of the same per-document function over the synthetic pickles; the refusal smoke (no `--enrolment`: exit 2); the two files' SHA-256 recorded here.
  - Done when: the review converged, both checks are recorded, and the hashes are on this task.
- [ ] 🟥 **0.4b The practitioner's run** (practitioner, normal PowerShell, developer build, both builds closed).
  - First `--list` to learn n. Then pass 1 with `--config validation\config` and pass 2 with `--config "$env:LOCALAPPDATA\ClinikoScribe\config"`, each over `"$env:LOCALAPPDATA\ClinikoScribe\past_sessions"`, no `>` redirect. About 15 min per recording per pass.
  - The executor writes the exact commands for the practitioner here after 0.4a (single-quoted Python bodies, the measurement folder's enrolment WAV).
  - Done when: both passes ended `COMPLETE` and their aggregate blocks are on this task (expected, measured, failed, the status line, n enrolled, n not enrolled, the medians and maxima over enrolled recordings; nothing per recording). A pass that ended `INCOMPLETE` or printed no block is re-run after the cause (named by its error type) is fixed under 0.4a; if it still cannot complete, the task records "incomplete" and D8 reads that pass as unmeasured. If n enrolled < 3, record "unmeasured" (D8).
- [ ] 🟥 **0.5 The numbers reviewed.** `/review-loop` over this plan's records of 0.2–0.4b (each figure against the scratch outputs in `.cursor/loops/afq-out/`), then the codex peer pass with the records as their own slice.
  - Done when: the pass converged and any corrected figure is recorded.
- [ ] 🟥 **0.6 The exit, the form and the residues** `[decision]`
  - Options: GATE-CAPABLE (build, then run 10); IMPROVEMENT — "build as an improvement" or "close with no change"; NO-GO — close with no change. With a building exit: the reach and guard (D2), the credit sub-variant and whether the chooser's wider predicate also credits (D4), and the practitioner's word on each reported residue (D8's "Reported for the practitioner's word" bullet).
  - Decide after: 0.3, 0.4b and 0.5. The composer presents the D8 table with the recommended option first; D8 decides which exits are open. Only a configuration with its own gate-configuration D8 lines in 0.3's tables can be authorised; if the practitioner prefers one that was not run that way, the composer runs it over the saved documents and returns before the choice is recorded.
  - Blocks: 0.7 and every later phase.
  - Record with the choice: the chosen form's state table and credit definition (they supersede D1's and D4's measured alternatives for Phase 1), and the base commit for D13.
- [ ] 🟥 **0.7 The chosen exit's phases hardened.** A scoped `/review-plan` over the phases the exit keeps (Phase 1 onward), from the outlines below, 0.6's record and Key Findings' pin and site lists. On the gate-capable exit it also settles the `heldout-7` brief (recommended: `heldout-2`'s brief with only the ids changed, so the set stays comparable; its digest committed in F.1).
  - Done when: each kept task meets the Task Specification Standard and the phases the exit drops are marked NOT BUILT with a dated line.
- [ ] 🟥 **0.8 The simulation recorded** (every exit). `docs/testing/validation-harness.md` gains "Answer-hop simulation" (the method, the tables as ids and counts, the decision); `AGENTS.md` and `CHANGELOG.md` per `/document`. On a no-change exit: SR's Deferred item and NCD's question-and-answer item get dated reconciliation lines, the plan closes, and the practitioner deletes `C:\afq-sets\`.
  - Done when: the documents hold the record and, on a no-change exit, the lifecycle state reads Completed.

### Phase 1 — The build (outline; hardened at 0.7; GATE-CAPABLE or "build as an improvement")
- [ ] 🟥 **1.1 The answer hop.** `note.py` `ExtractiveNoteProvider.generate_sections` and its class docstring, in the form 0.6 recorded; `desktop/tests/fixtures/answer_hops.py` (plain expectations); `TestAnswerHop` in `test_note.py` (every guard and state rule, both directions; a patient's "don't write this down" as a first reply pinned as quoted, a named residue); the matrix registry and lint in `test_note_matrix.py`; the predicted held-out divergences in their per-set tables; one test that a joined assertion is field for field a carried one. Then the composer's one-off `afq-pin.py` (scratch against product over the matrix, the seven reference documents and the saved documents), its difference count recorded.
- [ ] 🟥 **1.2 The reply flag and the credit.** `ui/models.py` `replies_after` and `flagged_segments` (D4), the count line and hint (D5); `validation.py` `word_info`'s separate credit term, the second full metrics computation without it (D5) with its verdict and report line, the dated amendment sentence; tests beside `TestFlaggedLineCredit` and `TestJoinedRunCredit` (credit ⊆ `[flagged]`; undo restores; the no-warning count line; a suggested line's `m` assertion; "Acknowledge all" unchanged); the moved pins in Key Findings.
- [ ] 🟥 **1.3 Consumers.** Check 2 in each direction with a reply that names what it negates (a joined "No numbness." against a pre-filled line: error grade; a low-confidence one: review grade), and a bare "No." pinned as drawing no contradiction (the named residue); a recorded reading for the learners, `note_fill`, `note_suggest` and the prose frame.
- Each task: `ruff check . && mypy && pytest` in `desktop/` (composer-run).

### Phase V — Version and hardening (outline)
- [ ] 🟥 **V.1** The six version strings to 0.3.7; `CHANGELOG.md`.
- [ ] 🟥 **Step H: Hardening pass**
  - [ ] 🟥 H1: `/review-loop` to convergence
  - [ ] 🟥 H2: `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`
  - [ ] 🟥 H3: `/security-review` — log findings; same routing (the residues to read: a wrong speaker label, a false question by its opening word, a next patient's reply where no boundary is found, a spoken instruction as a reply, a third speaker, learned-cue amplification)
  - [ ] 🟥 H4: codex peer re-check, whole surface in slices

### Phase M — The built rule measured (outline)
- [ ] 🟥 **M.1** Improvement exit: the built product replayed over the saved documents in the gate configuration; D8's improvement line re-confirmed; harm read as the per-fact difference against Phase 0's saved no-hop projection in the same configuration. Gate-capable exit: the seven sets re-run in full at the hardened tree under rule v6 with `--suggestions confirm-all --prose` (background, about 3.5–5 h), compared as Validation / Verification says; the reports are predictions v7's source.
  - Stop rule (no decision task): M reproduces the finalist's D8 lines and the plan continues; any difference pauses for the practitioner, with D13 available.

### Phase D — Documents (outline)
- [ ] 🟥 **D.1** `docs/security/threat-model.md`: Phase 3A surface 2 gains THE ANSWER HOP with its residues; the sentences it makes false are restated (`:354-357`, `:531-534`, `:698-700`, `:712-720`, `:771-772`, the Check 4 text `:522-547`, surface 5's readers of a suspect word `:958-971`). `docs/security/data-flow-map.md` flows 7, 10, 17, 26, 27, 29. `docs/design-system.md` (the flag's reach, the wording). `docs/testing/validation-harness.md` (the amendment as a loosening; Known limits: "Material facts in an uncued sentence", "Section placement is not measured", "Small talk and spoken instructions", "End of consultation and new patient", "Spoken contradictions"). `docs/testing/shipping-gate.md` (a 0.3.7 note: what the app does, not a rubric change). `docs/testing/kept-recordings.md` (expected drift). `docs/practice/` — the clinician review guide's 0.3.7 lines and the README's approval record (the practitioner approves before the install decision). `docs/pilot/README.md`; `docs/pilot/exit-gate.md` (a dated rule-v7 line on the gate-capable exit; stated unchanged otherwise). `docs/release/pilot-builds.md` ("Rolling back below 0.3.7"). `PLAN.md`'s delivery note; `docs/architecture/phase-history.md`; `AGENTS.md` (the carry and suspect-reader pointers, Current Status). Then the cross-family peer pass on the documents, each claim checked against the code.

### Phase F — The freeze and the build of record (outline)
- [ ] 🟥 **F.1** (gate-capable only) `validation/rules/rule-v7.json`, the `v7` label branch with its loosening sentence and second verdict, `TestRuleV7`, the harness document's "Rule v7" section with its ceiling table, predictions v7 from M.1's reports, and the pre-registration (D10) — one commit before the set exists.
- [ ] 🟥 **F.2** (gate-capable only) `heldout-7`'s plumbing (Key Findings' site list) and blind authoring from the edited templates, launched by the practitioner; copy-in unread, checked by `sha256sum -c`; the tails rows by script. From here the suite runs only through the blind runner (C6).
- [ ] 🟥 **F.3** (either building exit) The build of record: push on the practitioner's word, CI green, the `Release` run, the attestation checks, `docs/release/pilot-builds.md`.

### Phase P — The practitioner (outline)
- [ ] 🟥 **P.1** (gate-capable only) Validation run 10 at the build-of-record commit (or a later documents-only commit), recorded against predictions v7.
- [ ] 🟥 **P.2 Shadow mode** `[decision]` (gate-capable only)
  - Options: keep shadow on; off for clinic 1's reviewed consultations (only on a passed run 10; the pilot plan's stop rule).
  - Decide after: P.1.
- [ ] 🟥 **P.3 Installing 0.3.7** `[decision]` (either building exit)
  - Options: install with shadow mode on (or as P.2 decided), then the smoke; do not install (0.3.6 stays).
  - Decide after: M.1 and the review guide's approval (improvement exit), or P.2 (gate-capable exit).
- [ ] 🟥 **P.4** (gate-capable only) The `h7-` cases and the diagnosis; the blind period ends; the suite plain again.
- [ ] 🟥 **P.5** Records and close: the findings register (F-155's dated line; a row per residue the measurement shows, within the closed vocabularies), `AGENTS.md`, `CHANGELOG.md`, the lifecycle state and Retained Follow-Up Items, `/document`. The practitioner deletes `C:\afq-sets\` and, if authored, `C:\heldout7-author\`.

## Retained Follow-Up Items
N/A — the plan is Active.

## Follow-Up Continuation Notes
N/A — the plan is Active.

---
*Plan saved to: .cursor/plans/plan-answers-follow-question.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
*Sections marked (Only if relevant) can be omitted when genuinely not applicable, but never omit decisions, constraints, verification steps, or integration knowledge that a fresh session would otherwise have to rediscover.*
*For lightweight plans, plans with fewer than 5 tasks, or plans created without a preceding `/explore` discussion, sections with no real content should be marked `N/A — simple feature` rather than padded with placeholder structure.*
*State-once convention (new plans): state each cross-section contract — a critical constraint, design decision, invariant, or other normative rule — once in its canonical section, and have every other section point to it rather than restate it. Scope guard: this governs cross-section normative duplication only — the Task Specification Standard (in `/create-plan` and `/review-plan`) and task-local detail are untouched, and a plan recording `fast/medium involved` in its Executor tier may keep extra restatement where it helps the fast executor. It applies to new plans as they are written; never retroactively rewrite an existing plan to conform.*
_Plan drafted in Plan Mode and hardened by `/review-plan` on 2026-11-15 (Fable 5.2; exploration began on Opus 5.5 before the practitioner switched the model). Critique gate: three parallel lenses (Coverage and risk / Practicality / Simplicity), every finding dispositioned in the plan. Phase 0 is hardened in full; Phases 1–P are outlines hardened at Task 0.7 (the practitioner's choice). Planning only: nothing built, nothing committed._
