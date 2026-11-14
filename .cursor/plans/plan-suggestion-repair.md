# Feature Implementation Plan
**Feature:** suggestion-repair (the section suggestions for patients' uncued lines; version 0.3.7; validation run 10)
**Overall Progress:** `4%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: None. It continues `.cursor/plans/plan-note-content-design.md` (Completed — Follow-ups Retained), Follow-Up Continuation Note 1 and its P.5 diagnosis of validation run 9. "NCD" below means that plan.
- Follow-up plans: None.

## Goal
Make the local section-suggestion step propose a section for patients' lines that no cue routes — the class that failed validation run 9 (23 of 24 silent omissions on the blind `heldout-6`). Measure first why it proposes nothing, repair it on those numbers, ship it as 0.3.7, and test it with validation run 10 under a new rule v7 on a fresh blind `heldout-7`. Shadow mode stays on unless run 10 passes.

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable 5.2 (the practitioner's answer 2026-11-14: "Entirely premium (Recommended)"); executor Opus-class (`claude-opus-5-5` under `/execute-loop`, codex `gpt-6-astra` peer; the note-content-design shape); tier-gap dosing applied (design decisions D1–D15 locked, the parser's bounds and the tool's report fixed in the tasks, per-task "Done when", the go / no-go shape fixed before any number)

**The practitioner's decisions (2026-11-14, in chat; the quoted words are the option labels they chose):**
- Approach: "Repair the AI suggestions first" (over "Answers follow their question (Recommended)", "Warn on every left-out patient line", "Add more cue phrases").
- The suggestion step: "Measure only, decide after (Recommended)".
- The next patient: "Keep it out, say so before the run (Recommended)".
- Executor: "Entirely premium (Recommended)".
- Timings: "Paired ratio, same session (Recommended)" (this settles NCD's retained "drift question" for this plan).
- Saved exploration notes: "Neither (Recommended)".
- Window-edge carry: "Defer (Recommended)". An add-all-suggested control: "Defer (Recommended)".
- The native plan was approved the same day and "Nothing more, save it (Recommended)" closed the clarification.

**Because of "Measure only, decide after": Phase 0 is fixed; Phases S to P are the agreed shape and are re-confirmed at Task 0.4 on Phase 0's numbers.**

### Agreed Scope (Build Now)
- A developer-only, synthetic-only measurement script that shows what the suggestion model answers and how the parser reads it (Phase 0).
- The repair of `note_suggest.py`, in tiers, cheapest first, as Task 0.4 decides (Phase S).
- A go / no-go on a held-back check set before any blind set is authored (S.3, S.4).
- Version 0.3.7 and code hardening (Phase V).
- The audio-level cost over the seven seen sets, once, which also supplies predictions v7 (Phase M).
- Documents (Phase D).
- Rule v7, predictions v7, the blind `heldout-7`, the build of record (Phase F).
- Validation run 10, the shadow-mode and install decisions, the `h7-` cases and diagnosis, the close (Phase P).

### Deferred — Actionable Later
- **"Answers follow their question" (the named fallback; no model).** A patient's uncued reply joins the note beside a clinician's question that is in the note; a left-out clinician line's existing warning covers its reply.
  - Why deferred: the practitioner chose the suggestion repair first.
  - Intended future outcome: a deterministic route for replies, with no added warning load.
  - Relevant files / subsystems: `note.py` `ExtractiveNoteProvider.generate_sections` (the carry), `note_check.py` `clinician_line_omissions`, `validation.py` `warned` (a dated metric amendment), the chooser's `[flagged]` mark.
  - Dependencies / prerequisites: an audio-level simulation before building (the 2026-10-23 lesson: a text-level premise did not survive audio).
  - Recommended next action: its own plan. This session's read-only text-level count (scripts' own words, `validation/config`, code at `526913f`): joining only the FIRST reply line to an in-note QUESTION recovers 11 of the 51 silently lost material facts on `heldout-2` + `heldout-6` with no wrongly-present fact on any of the seven sets; the whole reply recovers 17 with one wrongly-present (`hld-17`); joining replies to in-note statements recovers nothing and adds one (`syn-05`), so questions only; sharing a left-out clinician line's warning covers the other 34 and adds no warning.
  - Risk if deferred: correctness: if the repair falls short, patients' replies stay silently left out until this is built.
  - Revisit by: S.4 or M.2 "no-go", or run 10 failing on silent omissions, whichever first.
- **Window-edge carry** (a reply shown its question when the two fall in different 40-line windows).
  - Why deferred: no synthetic script is longer than 21 lines (the 50 max 9, `heldout-2` max 20, `heldout-6` max 21) against `SUGGESTION_WINDOW_SEGMENTS = 40`, so it cannot be measured or tuned on any set.
  - Intended future outcome: no reply loses its question's context on a long consultation.
  - Relevant files / subsystems: `note_suggest.py` `run_suggestion_stage`, `_fit_window`.
  - Dependencies / prerequisites: a long synthetic input, or content-free counts from real shadow consultations.
  - Recommended next action: measure before designing.
  - Risk if deferred: ux-degradation: on long consultations a few replies may get no suggestion at a window edge.
  - Revisit by: shadow consultations on 0.3.7 showing replies with no suggestion at a window edge, or a long synthetic input existing.
- **An "add all suggested lines" control.**
  - Why deferred: a new Note-tab control with its own design and review; adding everything at once also adds any wrongly suggested line.
  - Intended future outcome: one action accepts every pending suggestion.
  - Relevant files / subsystems: `ui/note.py` (the chooser), `ui/models.py` `eligible_utterances`, `test_shadow_exits.py`.
  - Dependencies / prerequisites: 0.3.7 in use.
  - Recommended next action: a small plan with `docs/design-system.md` cues.
  - Risk if deferred: ux-degradation: each suggestion needs its own Add.
  - Revisit by: the practitioner's request after 0.3.7 is in use, or P.3's smoke showing more marks than is comfortable one by one.

### Excluded — Revisit Only If Needed
- **The next-patient boundary and the practitioner's own goodbyes and greetings.**
  - Why excluded: the practitioner's decision ("Keep it out, say so before the run").
  - When to revisit: run 10 fails on the next-patient count (R3) alone, or the practitioner asks. It stays the validation-run8 plan's retained item.
  - Relevant files / subsystems: `consultation_phrases.py`.
  - Recommended next action (if any): its own plan and dated decision.
- **Cue changes; a warning on every left-out patient line.**
  - Why excluded: rejected by the practitioner today; the second was also rejected on 2026-10-23 (about 110 such lines per real consultation).
  - When to revisit: only on a new measurement that changes those numbers.
  - Relevant files / subsystems: the cue files; `note_check.py`.
- **Short answer codes instead of section keys; accepting extra words after an answer.**
  - Why excluded: codes would rewrite the answer channel NCD D6 / D7 fix (and digit codes collide with line numbers); extra words let an echoed transcript line choose a section.
  - When to revisit: only if Task 0.3's table shows no other repair can work.
  - Relevant files / subsystems: `note_suggest.py`.
- **The recogniser; the prose prompt; `_prompt_safe` on the prose builder; the prose model on the GPU; question-and-answer derived lines.**
  - Why excluded: not this plan's subject; each is owned by NCD's retained items.
  - When to revisit: as those items say.
- **Exposing the model's finish reason.**
  - Why excluded: a product-code change for a developer measurement; the tool infers truncation instead (D2).
  - When to revisit: only if the inference proves unreliable at Task 0.3.

### Accepted Assumptions — Revalidate Later
- **Text level stands in for audio level while tuning.**
  - Why accepted for now: 22 of run 9's 23 routing omissions are left out on the script's own words too (NCD P.5), and a text-level run takes minutes.
  - Risk if assumption becomes false: a repair that looks good on scripts' words does less on transcripts.
  - Trigger for revisit: Task 0.3's first gate (the tool must reproduce run 9's silence under `suggest-v1`), then M.1.
  - Recommended next action: read M.1 against S.3 before the freeze.
- **`heldout-2` is a held-back SEEN check, not an untouched one.**
  - Why accepted for now: it is the only other set that shows the class. It was contaminated in three ways, recorded here: this session's read-only count over its scripts' own words shaped the "an answer belongs with its question" candidate; its failing ids are in predictions v6; `heldout-6` and `heldout-7` are authored from its brief, so the check is in-distribution.
  - Risk if assumption becomes false: the go / no-go is optimistic.
  - Trigger for revisit: S.4 reads it as an upper bound; run 10 is the test.
  - Recommended next action: none before run 10.
- **The model call is greedy (temperature 0), so a text-level attempt repeats.**
  - Why accepted for now: `language_model.py:360`.
  - Risk if assumption becomes false: tuning tables differ between identical runs.
  - Trigger for revisit: two runs of one attempt differing; then re-run once and record (NCD F.1's reading rule).
- **The blind-authoring templates are still on disk** (`.cursor/loops/ncd-heldout6-author-run.sh`, `ncd-heldout6-author-prompt.txt`, `ncd-heldout6-tails.py`, `ncd-brief-leak.py`, `heldout-6-brief/`; git-ignored; seen 2026-11-14).
  - Risk if assumption becomes false: F.2 rebuilds them from NCD's F.2 record and the validation-run8 plan's Task 0.4 / 0.5.
  - Trigger for revisit: F.2's first step.

### Key Design Decisions
See "Design Decisions" (D1–D15); each says whether it still applies to follow-up work.

## Key Findings

### Files / Symbols Involved (code-verified 2026-11-14 at `main` `526913f`, tree clean)
- `desktop/src/scribe_desktop/note_suggest.py` — the whole stage. `SUGGEST_PROMPT_VERSION = "suggest-v1"` (`:84`, reporting only, never persisted); `SUGGESTION_WINDOW_SEGMENTS = 40` (`:90`); `SUGGESTION_MAX_SECONDS = 240.0` (`:92`); `_ANSWER_TOKENS_PER_LINE = 8`, `_ANSWER_BASE_TOKENS = 16` (`:97-98`); labels `clinician` / `other` / `speaker N` (`:100-102`, `:244-249`); `_SECTION_MEANINGS`, `_OWNER_HINTS`, `_CLINICIAN_ONLY_HINT` (`:106-133`); `SUGGEST_INSTRUCTION` (`:141-156`); `SuggestionInput.from_request` (`:221`); `build_window_prompt` (`:266`); `_ANSWER_RE` (`:288`); `parse_suggestions` (`:291`); `_fit_window` (`:352`); `run_suggestion_stage` (`:374`; every asked number of a parsed window is marked assessed at `:466`, whatever was read).
- `desktop/src/scribe_desktop/language_model.py` — the `LanguageModel` protocol (`:145-157`: `model_id`, `complete(system_text=, user_text=, max_tokens=)`, `count_tokens`); `LocalLanguageModel` (`:272-376`: offline env asserted, size and SHA-256 verified, a smoke generation, one lock, greedy at `:360`; `complete` returns the content only, no finish reason).
- `desktop/src/scribe_desktop/ui/models.py` — `build_suggestion_stage(model_factory=, cache=, available=)` (`:4313-4347`); `SuggestionStage` protocol (`:4298-4310`); `placed_segments` (`:2961`); `eligible_utterances` (`:2975`, where a suggestion is accepted: the key in the line's allowed sections, the line not in the note, before the boundary).
- `desktop/src/scribe_desktop/validation.py` — `reference_document` (`:565`); `load_script` (`:471`); `find_encounters` (`:762`, needs `.json` + `.wav` + `.txt`, so not usable on a script folder); `REFERENCE_TAIL_STARTS` (`:624-716`); `HarnessInputs` (`:3107`); `_compose_draft` (`:3156`), `_compose_note` (`:3174`); `suggestion_pass` (`:3215`; its input at `:3235-3241`); `reference_reading` (`:3293`); `evaluate_encounter` (`:3315`; with the stage None it composes the note bare and never touches `note_suggest`); the report's rule-label branches (`:3822`, `:3836`); the `--set` help; the stage built only under `confirm-all` (`:4616`).
- `desktop/src/scribe_desktop/note.py` — `CLINICIAN_OWNED_SECTIONS` (`:170-172`: assessment, diagnosis, advice_home_exercise, management_plan — the only sections closed to a patient's line); `is_interrogative` (`:1667`); `admissible_sections` (`:1697-1728`).
- `scripts/measure-prose-fixtures.py` — the precedent: a `RecordingModel` wrapper in the SCRIPT (`:85-102`) and `--verbose`.
- `desktop/src/scribe_desktop/guard_eval.py` `:426-445` — the synthetic-only refusal (`script.conditions is None`, text-free, naming the id).
- Tests: `desktop/tests/test_note_suggest.py` (prompt pins `:326-375`, the version pin `:342`, the parser from `:376`, windows from `:447`, the call-site pin `:757-781`), `test_ui_suggestions.py`, `test_validation_harness.py` `TestSuggestions`, `test_integration_no_sockets.py` (two suggestion children), `test_setup_scripts.py:69` (how a script is loaded by a test, through importlib). `suggest-v1` also appears in `test_ui_models.py`, `test_validation_harness.py` and `docs/security/threat-model.md`.
- The six version strings (the 0.3.6 bump was commit `6c1901d`): `desktop/pyproject.toml:7`, `desktop/src/scribe_desktop/__init__.py:3`, `extension/package.json:4`, `extension/package-lock.json:3` and `:9`, `extension/src/manifest.ts:29`.

### Codebase Integration Notes
- **No filter by speaker keeps a patient's line out.** A pre-boundary line with words goes into the prompt whoever said it, with the stage's existing exclusions: a line spelling a list marker is withheld (`note_suggest.py:403-406`), a single line that alone overflows the window is not assessed (`:437-441`), and lines past the cap or an abort are not reached. A line not in the note is asked (`<n>? <speaker> <text>`), a line in the note is context (`<n> <speaker> [placed: <key>] <text>`). Acceptance closes only the four clinician-owned sections to a patient. So run 9's silence is in the model's answers or how they are read.
- **Candidate causes (none measured yet; no model text is kept):** (1) the patient is labelled `other` while the hints say "usually the patient's words"; (2) "Answer none for a greeting, small talk or a line no section fits" may swallow a short reply; (3) the parser drops an echoed `3? key`, a trailing full stop, a capital or any extra word, and such a line still counts as assessed; (4) the answer budget may be smaller than long keys need, so a completion is cut and the window's later lines are lost; (5) window edges (deferred: not measurable).
- **What run 9 recorded** (`docs/testing/validation-harness.md`, run 9): on `heldout-6` suggestions were added in 3 of 22 encounters (`h6-02`, `h6-10`, `h6-14`; W 13, U 4, dropped 2); in the 15 encounters failing on silent omissions W, U and dropped were all 0; lines not assessed 0 everywhere. On the 50: W 0, U 3.
- **The turn structure of the lost facts** (this session's count, scripts' own words): all 51 silently lost material facts on `heldout-2` (25, in 14 encounters) and `heldout-6` (26) sit in the patient's turn after a clinician line; 48 follow a question (`is_interrogative`); in 17 the question is in the note, in 34 the clinician's line is itself left out.
- **The call-site pin.** `test_note_suggest.py:757-781` counts every `.complete(..., system_text=...)` call under the package and asserts exactly `note_suggest.py: 1, prose_style.py: 1, language_model.py: 1` (NCD C7; the threat model says "exactly three"). A recorder inside the package would be a fourth site and would ship in the installer; a recorder in a script is outside the scan (D2).
- **Building the tool's input exactly as the harness does:** `document = reference_document(script)`; `draft = _compose_draft(document, speaker_eval.CLINICIAN_LABEL, inputs, now)`; `placed = placed_segments(draft.note_sections)`; `request = build_note_request(document, config, draft.template_profile_id, clinician_speaker=clinician)`; `SuggestionInput.from_request(request, in_note=placed, clinician_speaker=clinician)`; then `suggestion_pass` / `_compose_note(additions=…)` / `encounter_metrics` for the facts. `HarnessInputs` needs `provider` and `frame_probability`: pass stubs that raise. `note_suggest.CLINICIAN_LABEL` is a different constant with the same value. Importing `validation`'s private `_compose_draft` / `_compose_note` matches convention (`guard_eval.py:102-110`).
- **One model for a whole run:** build one `LocalLanguageModel()` after `apply_offline_env()` and pass `model_factory=lambda: recorder, cache=None`; the default factory with `cache=None` reloads the 2.3 GiB model per encounter.
- **Test guards a new script's tests meet:** every test gets an empty models root (`conftest.py:267-290`), so the script's `main` takes a model factory seam (tests pass `MockLanguageModel`); the production-channel pin (`conftest.py:166-180`) applies to anything that refuses outside the developer build.
- **Timings to plan around** (run 9, seconds per set, order the 50, `heldout`, `-2`, `-3`, `-4`, `-5`, `-6`): `confirm-all --prose` 2328 / 1302 / 1837 / 1766 / 1581 / 1663 / 1748 (about 3 h 24 min); model seconds only 515 / 273 / 449 / 413 / 408 / 417 / 452, so a text-level set is about 8 minutes and one tuning attempt on `heldout-6` + the 50 about 16.
- **The built sets are gone** (`C:\ncd-c6`, `C:\ncd-run9` deleted). Rebuild: check the installed voices first (slots 0–2 David, Hazel, Zira; `docs/testing/validation-harness.md:37-40`), then `.venv/Scripts/python.exe scripts/build-validation-set.py validation/<set> C:/<out>/<set> < /dev/null`.
- **Comparison files still on disk** (git-ignored `.cursor/loops/`): `stage-2-c6-confirm-<set>.md`, and the F.1 re-run reports that are M.1's baselines: `stage-4-f1-confirm-<set>.md` for the 50, `heldout`, `heldout-3`, `heldout-4` and `heldout-5`, and `stage-4-f1-confirm2-heldout-2.md` for `heldout-2` (its SECOND F.1 run, the one of record, SHA-256 `758e711f…`; the first run did not reproduce and is never the baseline). Run 9's own copies are deleted; for `heldout-6` only the recorded TOTAL row and hash remain (`docs/testing/validation-harness.md:382-403`).
- **Line endings:** `AGENTS.md`, `CHANGELOG.md`, `docs/testing/validation-harness.md`, `docs/security/threat-model.md`, `docs/security/data-flow-map.md`, `validation.py` and several test files are CRLF in the working tree; plans and `test_pilot_docs.py` are LF. Check `git ls-files --eol` before any byte-level edit.
- **Lessons that apply** (`docs/lessons.md`, `AGENTS.md` "Pattern worth knowing"): the agent shell reads the developer models folder but its writes there are virtualised; every Python call takes `< /dev/null`; long runs in the background, lid open, mains power; a report written by PowerShell's `>` is UTF-16 (bash redirection is UTF-8 with CRLF); a re-run reproduces counts and verdicts, not words; a top-level `C:\` folder cannot be deleted from the agent shell; a codex pass over documents is its own slice.

### Shared helpers (used by more than one phase)
- `scripts/measure-suggestions.py` — Phase 0 (v1 baseline), S.2 (each attempt), S.3 (the check), and the paired timing.
- The detached worktree of `526913f` (D7) — the v1 side of every paired timing.
- NCD's F.2 site list (`plan-note-content-design.md`, Task F.2, "The plumbing BUILT" sub-bullets) — the model for this plan's F.2.

### External / API Findings
N/A — no external service. The model is the pinned local Qwen3-4B-Instruct-2507 (unchanged; no model-pack change).

## Planned Workflow Summary

### Flow 1 — Measuring the silence
The developer runs the measurement script on a synthetic set folder. For each script it builds the note the app would build from the script's own words, asks the suggestion model about every left-out line through the shipped stage, records the raw answers in memory, and prints numbers only: how each answer line was shaped, how the parser read it, and what happened to the lines that carry a silently lost fact.

### Flow 2 — A patient's reply gets a section
In the app, after the note is drafted, the suggestion job asks the model about left-out lines. With the repair, a patient's uncued reply comes back with a section; the chooser shows `[suggested: <title>]` with that section pre-selected; the clinician adds it or not. Nothing else about the flow changes: no model text is kept, acceptance goes through the ownership rule, and every exit still stops the job.

### Flow 3 — Measured before it ships
Tuning runs at text level on `heldout-6` and the 50. The frozen repair is read once on `heldout-2`; the practitioner decides go or no-go. Then the seven seen sets run once at audio level (the cost, and predictions v7), rule v7 is written, `heldout-7` is authored blind, and run 10 is the test.

## Design Decisions
- **D1 — Repair the suggestion step, measured first.** The practitioner's choice. The repair's content is decided at Task 0.4 on Task 0.3's table.
  Alternatives considered: "Answers follow their question" (deterministic; recorded as the named fallback with its numbers); a warning on every left-out patient line (about 110 per real consultation); more cue phrases (cannot cover a blind author's wording).
  Still applies to follow-up work: Yes.
- **D2 — The measurement is ONE script, `scripts/measure-suggestions.py`, with the recorder in the script.** It runs the shipped stage unchanged through a wrapper around the real model (the `measure-prose-fixtures.py` pattern), at text level on `validation.reference_document`. It is developer-only and synthetic-only, prints numbers only by default, writes no file, and holds completions in memory for the run only. `--verbose` prints raw completions (synthetic text) to the console and is run in the foreground. A completion "cut at its budget" is INFERRED (`count_tokens(raw) >= max_tokens - 1` and a trailing asked number unanswered) and the report says so.
  Alternatives considered: a package module `suggest_eval.py` (a fourth model call site against the C7 pin, and shipped in the installer); extending the harness's `SuggestionCounts` (the stage's result carries ids, keys and counts only, and the report's columns are pinned and compared line by line with predictions); exposing a finish reason (product code for a developer tool).
  Still applies to follow-up work: Yes.
- **D3 — The repair is built in tiers, cheapest first; a higher tier only when the lower leaves Task 0.4's threshold unmet on the tuning sets.**
  - Tier A (no prompt change): the parser and the answer budget.
  - Tier B (prompt change): the speaker label or the hint wording, the "none" wording, and the instruction that an answer belongs with its question and that a short reply to a clinical question is not small talk.
  - Which items of each tier are built is Task 0.4's decision.
  Alternatives considered: all at once (cannot tell which change helped; a larger prompt change than needed); short answer codes and extra-word leniency (Excluded); window-edge carry (Deferred).
  Still applies to follow-up work: Yes.
- **D4 — The answer channel does not change (NCD D6 / D7).** An answer is a window line number and a canonical section key or `none`. Tier A is a dated amendment to D7's regex with these bounds, each pinned by a test: the number is one of the window's asked numbers; after it come at most one `?`, then at most one of `.`, `)`, `:`, `-`; the key or `none` is the FIRST token after that, compared after ASCII case-folding, with trailing punctuation only; no prefix or partial match of a key; the first valid answer per number wins; an echo of any prompt line shape (`<n>? <speaker> <text>` or `<n> <speaker> [placed: <key>] <text>`) never yields an answer; the marker-echo and think-tag refusals are unchanged. No model text reaches the note, a log, the audit row or a report.
  Alternatives considered: free-form answers with key search (a transcript word could choose a section).
  Still applies to follow-up work: Yes.
- **D5 — `SUGGEST_PROMPT_VERSION` becomes `"suggest-v2"` with the first behaviour change to the stage (parser, budget or prompt), and moves again with any later one.** It stays reporting-only; nothing persists it. M.1 and P.1 record it with their commit.
  Alternatives considered: bump only on a prompt-text change (a tier-A-only build would report `suggest-v1` while behaving differently).
  Still applies to follow-up work: Yes.
- **D6 — Sets.** Tuning: `heldout-6` (it carries the class) and the 50 (regression and cost; they carry almost none of the class). Check: `heldout-2`, a held-back seen check (Accepted Assumptions), read ONCE at text level after the stage is frozen. A failed check spends it: there is no retune-and-recheck. The executor does not open or run `heldout-2` before S.3.
  Alternatives considered: no check before the blind set (a predicted failure would cost a blind set and a practitioner run); tuning on both (nothing left to check on).
  Still applies to follow-up work: No.
- **D7 — Timings are read as a paired ratio in one session** ("Paired ratio, same session (Recommended)"): old and new stage timed back to back on one constructed window of 40 asked lines (scripts' reference lines joined until 40 are asked; C.0's method), v2 seconds over v1 seconds. The v1 side runs from a detached worktree of `526913f` outside the repository (the `C:\ncd-v2-baseline` precedent), which the practitioner deletes at the close. The SAME script (from the main checkout; it does not exist at `526913f`) takes `--source-root <folder>`, prepended to the import path before `scribe_desktop` is imported (the `measure-prose-fixtures.py:42-44` pattern; default: its own repository's `desktop/src`); `--timing` prints the imported `note_suggest` module's file path, its `SUGGEST_PROMPT_VERSION` and a SHA-256 of the constructed window's lines (segment text and placement, before the stage's instruction), and a pair counts only when the two paths differ as intended, the versions are the expected ones and the two hashes are equal. The script therefore uses only package APIs that exist at `526913f`.
  Alternatives considered: absolute seconds against the cap (a slow session fails a good prompt).
  Still applies to follow-up work: Yes.
- **D8 — The window size (40) and the one 240 s cap do not change** (NCD D9: a change is a new dated decision with C.6 repeated). A larger answer budget is a ceiling, not a time cost; S.1 confirms `_fit_window` does not halve more often on the tuning sets.
  Still applies to follow-up work: Yes.
- **D9 — Whether "assessed" changes is Task 0.4's decision.** Today an asked line counts as assessed when its window's completion parsed at all, even if no valid answer for that line was read. Counting only lines with a valid answer is more honest, but it changes the harness's "Lines not assessed" column (a dated metric amendment, so M.1's comparison lines change), the Note tab's line (`ui/models.py:4363-4366`) and `docs/design-system.md`.
  Still applies to follow-up work: Yes.
- **D10 — The audio-level cost is measured once, at the hardened commit, under rule v6 with `--suggestions confirm-all --prose`, over the seven seen sets; `--suggestions off` is not re-run.** With the stage None the harness never calls `note_suggest`, so `off` reports cannot change (pinned by the reference-path test in `test_validation_harness.py`); M.1 records `git diff --stat 526913f..HEAD -- desktop/src` and, if it names any file but `note_suggest.py` and `__init__.py`'s version line, `off` is owed for the sets that file can reach. M.1's reports are also predictions v7's source.
  Alternatives considered: the draft's "off must equal run 8" (not checkable as written: run 8 used rule v5 without `--prose`, rule v5 has no `heldout-6` row, run 9's copies are deleted); measuring before hardening (a second seven-set pass, as NCD needed).
  Still applies to follow-up work: Yes.
- **D11 — Rule v7 is rule v6 with the set schedule moved and nothing else.** `validation/rules/rule-v7.json` (schema 4): `heldout-6`, spent since NCD P.5, becomes a reported row that counts marked R1 under its ceiling (rule v6's `heldout-5` row, field for field); an eighth row `heldout-7` is rule v6's `heldout-6` row field for field, the blind gate row reporting marked R1. The gate for run 10: a rule v7 pass on the 50 and on `heldout-7`; `heldout` to `heldout-6` are built, run and reported. Every set runs with `--suggestions confirm-all --prose`. `heldout-7` is authored from `heldout-2`'s brief (as `heldout-6` was) and run once. Rule v6 and every earlier rule are never edited. The report needs a `v7` label branch and its own history sentence in `validation.py` (F.1).
  Alternatives considered: re-using rule v6 (it has no `heldout-7` row and has been run).
  Still applies to follow-up work: Yes.
- **D12 — The next patient is out of scope, and that is pre-registered.** `heldout-7`'s pre-registration says, before the set exists: run 10 may fail on the next-patient count (R3) alone, since the boundary is unchanged and a better-recall suggestion step can add a next patient's reply; such a result is still blind evidence on the repair, read from the silent-omission columns.
  Still applies to follow-up work: Yes.
- **D13 — Version 0.3.7. Installing it is a decision on run 10's outcome (P.3), not a default.** The build of record is owed before P.3. The installed app's models do not change, so no model pack is needed for the upgrade.
  Alternatives considered: install by default (NCD's P.3 had to be re-decided after run 9 failed).
  Still applies to follow-up work: No.
- **D14 — The freeze.** From predictions v7's commit to run 10, nothing under `desktop/src/` or `scripts/` changes but F.1's and F.2's named lists and F.3's content-free `h7-` rows in `REFERENCE_TAIL_STARTS`. A behaviour-changing fix to `note_suggest.py` after S.3 voids the check-set read and repeats M.1; it needs the practitioner's word first (a pause, never the executor's call). Run 10 runs at the build-of-record commit or at a later commit shown to change documents and plans only (`git diff --stat` naming 0 paths under `desktop/`, `scripts/`, `validation/`, `config_defaults/`, `packaging/`, `extension/`, `protocol/`).
  Still applies to follow-up work: Yes.

- **D15 — The no-change exit** (S.4 "NO-GO, close" and M.2 "stop"). Every repair-dependent change is restored to its state before S.1: `note_suggest.py`, its tests and every `suggest-v1` pin, D9's sites if they changed (`ui/models.py`, `validation.py`, `docs/design-system.md`), and — at M.2 — the six version strings and the opened `CHANGELOG.md` entry. The measurement script and its tests are kept as developer tooling (they must pass against the restored `suggest-v1` stage). Verified by the suite and by a `git diff --stat` against the commit before S.1 naming only the script, its test file, documents and plans. The plan then closes with NO CHANGE, as the larger-model and GPU-decoding plans did.
  Still applies to follow-up work: No.

## Schema / Data Changes
None persisted. No record, audit field or stored file changes. New tracked files: `scripts/measure-suggestions.py`, its test file, `validation/rules/rule-v7.json`, `validation/heldout-7/`.

## Config / Environment / Deployment Impact
- No environment variable, dependency, model or config-file change.
- 0.3.7 is a new installer build (the CI `Release` workflow, attested); the existing model pack stays valid.
- Rolling back from 0.3.7 to 0.3.6 needs no data step (nothing persisted changes); Phase D records that in `docs/release/pilot-builds.md`.

## Critical Constraints
- **C1 — No real clinical content.** The agent never reads `%LOCALAPPDATA%` except to READ the developer models folder, and never any kept recording, transcript or note. Nothing per consultation enters a tracked file.
- **C2 — The measurement script is synthetic-only and developer-only.** It refuses a set holding any script without synthetic conditions (text-free, naming the id), writes no file, and calls no logger.
- **C3 — No model text is kept by the product** (NCD D7, C9): the answer channel and its refusals are D4's; the log-tripwire names (`asked_lines`, `suggestion_text`) stay.
- **C4 — The model call-site pin stays at exactly three** (`test_note_suggest.py` `TestTheOneCallSite`). Nothing in this plan edits it.
- **C5 — Frozen things stay frozen:** the phrase vocabularies, the cue files, every existing held-out set and its fixtures, rules v1–v6, the window size and the cap (D8).
- **C6 — The freeze** (D14).
- **C7 — The blind rule.** From the moment `validation/heldout-7/` holds scripts until P.4 writes its cases, the desktop suite runs ONLY through `scripts\lint-held-out-set.py validation\heldout-7`; the executor never opens the folder's scripts, `SPEC.md` output or `AUTHOR-NOTES.md`; the author session is launched by the PRACTITIONER from a normal terminal, never by the agent.
- **C8 — A gate is a finding, never a tuning reason; a rule that has been run is never edited.** Thresholds (0.4) and predictions (F.1) are written before the numbers they judge.
- **C9 — Host and conduct.** All work on this Windows host, never in the cloud. Commits and pushes only on the practitioner's word. Long runs in the background with `< /dev/null` on every Python call, mains power, lid open; the installed app closed while a model run is in progress; one build open at a time. `--verbose` only in the foreground.
- **C10 — Line endings are kept** as each file has them (Key Findings).
- **C11 — `heldout-2` is not opened or run before S.3** (D6).

## Validation / Verification
- **Baseline, dry-run 2026-11-14 at `526913f`:** in `desktop/`, `ruff check .` — "All checks passed!"; `mypy` — "no issues found in 67 source files"; `pytest -q -p no:cacheprovider` — 10782 passed, 9 skipped (494 s).
- **Every code task:** `ruff check . && mypy && pytest` in `desktop/` (through the blind runner once C7 applies).
- **Phase 0:** the script's tests (the shape classifier, the synthetic-only refusal, the input equal to `suggestion_pass`'s); Task 0.3's first gate.
- **Phase S:** `test_note_suggest.py`, `test_ui_suggestions.py`, `TestSuggestions`, the no-sockets children; each attempt's table; the check-set table read once.
- **Phase M:** each `confirm-all --prose` report compared with its named baseline file (the six; Key Findings' "Comparison files still on disk") or run 9's retained record (`heldout-6`); a differing seen set whose difference is not explained by the repair is re-run once at the same commit.
- **Phase F:** rule v7 and predictions v7 committed before `heldout-7` exists; the suite green through the blind runner; CI green; the release attested (`gh attestation verify`; from an agent shell read its exit code).
- **Phase P:** run 10's four verdicts and every column recorded against predictions v7; the install smoke line.
- Side-effecting commands (set builds, harness runs, the release) were inspected, not run, during planning.

## Deferred / Out of Scope
See "Deferred — Actionable Later" and "Excluded — Revisit Only If Needed" in the Planning Extraction Summary (the canonical lists).

## Current State / Handoff Note
- Last completed step: Planning complete; Task 0.1 (the decisions) recorded.
- Current in-progress step: None.
- Immediate next action: Task 0.2 (the measurement script) via `/execute` or `/execute-loop`. Commit this plan first, on the practitioner's word.
- Open blockers / open questions: None. Next practitioner decision: Task 0.4, after Task 0.3's table.
- Plan peer pass (codex `gpt-6-astra` high, 2026-11-14): rounds 1–5, 14 findings (2 MED, 12 LOW), all verified and applied; round 6 (the cap raised by one on the practitioner's word) brought no new finding but judged PR-LOW-012 (the answer-budget table in Task 0.2) not fixed; its three gaps were then closed, and THAT completion has not been seen by a further round. Everything else was confirmed by a later round.
- Last plan sync: 2026-11-14

## Review History
- 2026-11-14 round 1: 0 CRIT / 0 HIGH / 1 MED / 6 LOW; skew=plan peer-review (codex); action=all seven verified and applied
- 2026-11-14 round 2: 0 CRIT / 0 HIGH / 1 MED / 2 LOW; skew=plan peer-review (codex); action=round 1's seven confirmed; all three new verified and applied
- 2026-11-14 round 3: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=plan peer-review (codex); action=round 2's three confirmed; both new verified and applied
- 2026-11-14 round 4: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=plan peer-review (codex); action=round 3's two confirmed; the one new verified and applied
- 2026-11-14 round 5: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=plan peer-review (codex); action=round 4's one confirmed; the one new verified and applied; cap of 5 reached, unconverged (the last amendment unreviewed)
- 2026-11-14 round 6: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=plan peer-review (codex); action=no new finding; PR-LOW-012 judged not fixed and completed; cap (raised to 6 on the practitioner's word) reached, that completion unreviewed

## Review Findings Log
### Round 1 — 2026-11-14
Round status: Closed
Source: Codex (gpt-6-astra high) plan peer-review
Materiality: 5 build-affecting / 2 record-only / 0 invalid
Composer-recorded: the peer ran in a read-only sandbox and printed this round as its final message (`.cursor/loops/suggestion-repair-plan-peer-r1.log`, git-ignored; plan at `b80cdae`); the planning session transcribed it from the last `### Round 1` header, verified each finding against the code, and applied the amendments under `/review-plan`'s amendment-application discipline (each landed, siblings swept). The peer also spot-checked 31 cites, all verified.

#### PR-MED-001: `plan-suggestion-repair.md` Task M.1 — an exhaustive comparison without its baseline
- Materiality: build-affecting (verified)
- Why it matters: M.1 asked for every changed encounter row on `heldout-6`, but run 9's `heldout-6` report copies are deleted; only the harness record's totals, failing ids and diagnosis remain.
- /fix decision: Applied
- /fix notes: M.1 now compares `heldout-6` only with run 9's retained record (verdicts, TOTAL row, failing encounters, residue members, suggestion counts, wrongly-present facts, the diagnosis's classes) and reports any other row as "not comparable". Sibling: Key Findings' "Comparison files still on disk" already said so; no other statement asserted the old contract.
- /fix date: 2026-11-14
- /fix applied by: Claude Code

- **[LOW]** PR-LOW-001: Tasks S.4 / M.2 — the no-change exits named only `note_suggest.py` — Materiality: build-affecting (verified: the version pin at `test_note_suggest.py:342` and V.1's strings would be left behind) — Decision: Applied (new D15 states the exit once; S.4 and M.2 point to it; the D1–D14 range became D1–D15 in both places); applied by: Claude Code
- **[LOW]** PR-LOW-002: D14 — the freeze excluded F.3's tail rows — Materiality: build-affecting (verified) — Decision: Applied (D14 names F.3's content-free `h7-` rows in `REFERENCE_TAIL_STARTS`; F.3's Done-when already agreed); applied by: Claude Code
- **[LOW]** PR-LOW-003: Task P.4 — `heldout-7`'s historical boundary comparison unnamed — Materiality: build-affecting (verified at `test_consultation_boundary.py:556-575`: a set in `_SETS_READ_AFTER_THEIR_RUN` is excluded from the shared assertion and checked by its own `_BOUNDARY_CHANGES_ON_HELDOUT_<n>` block) — Decision: Applied (P.4 names the `_7` table, its assertion block and rule-4 test); applied by: Claude Code
- **[LOW]** PR-LOW-004: Task F.1 — no positive tests of the new v7 report branches — Materiality: build-affecting (verified: the four v6 tests named exist in `test_validation_harness.py`) — Decision: Applied (F.1 lists the four v7 counterparts, with the kept history sentences and older-rule isolation asserted); applied by: Claude Code
- **[LOW]** PR-LOW-005: Key Findings — "every pre-boundary line" overstated — Materiality: record-only (verified at `note_suggest.py:403-406`, `:437-441`) — Decision: Applied (the note now says no filter by speaker, with the marker, overflow and cap / abort exclusions); applied by: Claude Code
- **[LOW]** PR-LOW-006: Task F.2 — the runner's docstring missing from the blind-period edits — Materiality: record-only (verified at `scripts/lint-held-out-set.py:5-13`) — Decision: Applied (F.2 lists the docstring, words only); applied by: Claude Code

### Round 2 — 2026-11-14
Round status: Closed
Source: Codex (gpt-6-astra high) plan peer-review
Materiality: 3 build-affecting / 0 record-only / 0 invalid
Composer-recorded, as round 1 (`.cursor/loops/suggestion-repair-plan-peer-r2.log`; the plan's working-tree copy after round 1's amendments). Round 1's seven findings: all `confirmed`. Each new finding was verified against the code and the earlier plan's record, then applied under the amendment-application discipline.

#### PR-MED-002: `plan-suggestion-repair.md` Task M.1 — the wrong `heldout-2` baseline
- Materiality: build-affecting (verified)
- Why it matters: M.1 named `stage-4-f1-confirm-<set>.md` for every set, but for `heldout-2` that is F.1's FIRST run, which did not reproduce (68 lines differ); the run of record is `stage-4-f1-confirm2-heldout-2.md` (`plan-note-content-design.md:1957`; both files are on disk). The first would have charged a known transcription difference to the repair.
- /fix decision: Applied
- /fix notes: M.1, Key Findings' "Comparison files still on disk" and Validation / Verification's Phase M line now name the baseline per set, with `confirm2` for `heldout-2`; M.1 checks each baseline's existence and SHA-256 against NCD's F.1 record first, and a missing or mismatching one is a pause. Siblings swept: no other statement names a baseline file.
- /fix date: 2026-11-14
- /fix applied by: Claude Code

- **[LOW]** PR-LOW-007: Task 0.2's report — gate inputs missing — Materiality: build-affecting (verified: accepted W / U, dropped and not-assessed come from `suggestion_pass` and `SuggestionStageResult`, not from answer shapes) — Decision: Applied (the report adds accepted W / U, dropped, lines asked, lines not assessed, model calls and a defined "split windows" count; S.1's Done-when reads that count against 0.3's baseline); applied by: Claude Code
- **[LOW]** PR-LOW-008: D7 / Task 0.2 — the v1 timing had no import-isolation contract — Materiality: build-affecting (verified: the editable install imports the main checkout, and the script does not exist at `526913f`) — Decision: Applied (D7 defines `--source-root`, the three identity lines `--timing` prints and when a pair counts; Task 0.2's `--timing` line points to it); applied by: Claude Code

### Round 3 — 2026-11-14
Round status: Closed
Source: Codex (gpt-6-astra high) plan peer-review
Materiality: 2 build-affecting / 0 record-only / 0 invalid
Composer-recorded, as rounds 1 and 2 (`.cursor/loops/suggestion-repair-plan-peer-r3.log`). Round 2's three findings: all `confirmed` (the peer also confirmed that NCD's F.1 records a hash for all six baselines and that the channel and models-root resolution do not depend on the package's checkout location). Both new findings verified against `note_suggest.py` and applied.

- **[LOW]** PR-LOW-009: Task 0.2's report — "split windows" could miss real halving — Materiality: build-affecting (verified at `note_suggest.py:437-442`: a halved prefix holding only context lines makes no call and its asked lines come again, so model calls need not exceed the slices; counting encounters also hid repeats) — Decision: Applied (the report now counts **fit reductions** in the recorder from the stage's own token counts of window texts, as a total; tests cover a context-only fitted prefix and repeated reductions in one encounter; S.1's Done-when reads that count); applied by: Claude Code
- **[LOW]** PR-LOW-010: Task 0.2's classifier — some completion lines have no speaker to attribute — Materiality: build-affecting (verified at `note_suggest.py:314`: a number outside the window's asked numbers is rejected, so such a line belongs to no asked line) — Decision: Applied (the W / U and role splits apply only through the window's asked-number map; every other completion line is counted once as **unattributable**; tests cover a malformed line and an out-of-window number); applied by: Claude Code

### Round 4 — 2026-11-14
Round status: Closed
Source: Codex (gpt-6-astra high) plan peer-review
Materiality: 1 build-affecting / 0 record-only / 0 invalid
Composer-recorded, as rounds 1 to 3 (`.cursor/loops/suggestion-repair-plan-peer-r4.log`). Round 3's two findings: both `confirmed`, no residue outside the round blocks. The peer attacked every other count Task 0.2 promises and reported that each survived; ten further cites checked, all verified. The one new finding verified against `note_suggest.py` and applied.

- **[LOW]** PR-LOW-011: Tasks 0.2 / 0.4 — bare-key token costs do not establish the answer-line budget — Materiality: build-affecting (verified: the budget `answer_token_budget` covers the WHOLE completion of numbered lines, `note_suggest.py:261-263` and `:453`, and a key's count alone leaves out the number, the separator, the newline and the tokenisation context) — Decision: Applied (Task 0.2 measures each key as a full answer line and complete answer sequences up to 40 lines beside `answer_token_budget`; Task 0.4 sets the constant so the budget covers the costliest complete answer at every window size up to 40); applied by: Claude Code

### Round 5 — 2026-11-14
Round status: Closed
Source: Codex (gpt-6-astra high) plan peer-review
Materiality: 1 build-affecting / 0 record-only / 0 invalid
Composer-recorded, as rounds 1 to 4 (`.cursor/loops/suggestion-repair-plan-peer-r5.log`). PR-LOW-011: `confirmed`. The peer checked the evidence behind each decision task (0.4, S.4, M.2, P.2, P.3) and found it sufficient but for the finding below; its final whole-plan pass found no further executor blocker, uncheckable Done-when, contradiction or C1–C11 breach. Its readiness line: "no — amend its budget-evidence contract before implementing the measurement script"; that amendment is applied here. **This was the pass's fifth and last round under the default cap, and it brought a new build-affecting finding, so the pass stops at the cap UNCONVERGED: the amendment below has not been seen by a further peer round.**

- **[LOW]** PR-LOW-012: Tasks 0.2 / 0.4 / S.2 — four sampled answer sizes in the plain format do not bound the budget — Materiality: build-affecting (verified: `build_window_prompt` numbers context lines too, `note_suggest.py:275`, so a few asked lines can all carry two-digit numbers; nothing shows token cost is linear between samples; the `?`, capital and punctuation variants tier A may admit cost more than the plain form) — Decision: Applied (Task 0.2 measures the worst-case complete answer for EVERY asked count 1 to 40 — the costliest key, the highest window numbers, each admitted answer variant — beside `answer_token_budget(n)`; Task 0.4 sets the constants so the budget covers that worst case at every n; S.2 repeats the table before an attempt counts whenever the requested answer format or the admitted variants change); applied by: Claude Code

### Round 6 — 2026-11-14
Round status: Closed
Source: Codex (gpt-6-astra high) plan peer-review
Materiality: 0 build-affecting / 0 record-only / 0 invalid
Composer-recorded, as rounds 1 to 5 (`.cursor/loops/suggestion-repair-plan-peer-r6.log`). The practitioner raised the cap by one for this round ("One more round (Recommended)"). **No new finding.** PR-LOW-012 was judged `not fixed`: the round-5 amendment landed in all three places, but its table had no justified upper bound. The peer found no contradiction with D2, D8, `_fit_window` or S.1, and confirmed the calculation needs only `count_tokens`. Its readiness line: "no — correct PR-LOW-012's budget-evidence recipe first"; the correction is applied here and has NOT been seen by a further round (the cap is reached again).

- **[LOW]** PR-LOW-012 (completed): Tasks 0.2 / 0.4 — the budget table's three gaps — verified: the parser already admits one of `.`, `)`, `:`, `-` after the number (`note_suggest.py:288`), which the listed variants left out; "the highest window numbers" and "the costliest key" were asserted to be the worst case, not shown; and `complete` passes the budget as `max_tokens` and returns the content only (`language_model.py:359-376`), so the text's token count leaves out whatever closes the completion — Decision: Applied (Task 0.2 defines the finite set of bounded answer forms with the separators and their combinations, takes the per-line maximum by token count over every key, every window number 1 to 40 and every form instead of assuming it, and prints the bound with a measured cross-check; Task 0.4 adds an explicit closing allowance and requires the budget to cover the bound plus that allowance at every n); applied by: Claude Code

## Tasks
Markers: 🟥 To Do, 🟨 In Progress, 🟩 Done. A `[decision]` task is a planned stop for the practitioner. "Suite" means `ruff check . && mypy && pytest` in `desktop/`.

### Phase 0 — Decisions and the measurement (no product behaviour changes)
- [x] 🟩 **0.1 The planning decisions recorded** (2026-11-14): the eight answers under "The practitioner's decisions" in the Planning Extraction Summary, in their own words.
- [ ] 🟥 **0.2 The measurement script.** New `scripts/measure-suggestions.py` and `desktop/tests/test_measure_suggestions.py` (the script loaded through importlib, as `test_setup_scripts.py:69` does). Design: D2; constraints C2–C4. Nothing under `desktop/src/` changes.
  - Arguments: one or more set folders (`validation\<set>`), `--config validation\config`, `--verbose`, `--timing`; `main` takes a model-factory seam so tests pass `MockLanguageModel`.
  - Scripts: list `*.json` whose stem matches the encounter-id pattern, `load_script` each; refuse the whole set (exit 2, a fixed line naming the id) when any `script.conditions is None`.
  - Per script: build the input exactly as Codebase Integration Notes' "Building the tool's input" says; run the shipped stage once through the recorder (one model for the run); then accept every suggestion as `suggestion_pass` does and judge the facts with `encounter_metrics`.
  - Classify each completion line into one shape: valid key; valid `none`; number followed by `?`; unknown key; capitals or trailing punctuation on an otherwise valid key; extra words after a key; not an answer line. A line is attributed to a speaker ONLY through the window's asked-number map (its leading number is one of that window's asked numbers); every other line — no leading number, or a number that window did not ask — is counted once as **unattributable**, in no W / U or role column. Per window also: asked numbers with no answer line at all; "cut at budget" (D2's inference); completion refused (marker echo or think tag).
  - Report (numbers-only Markdown to stdout): per set, the shape counts split by the confirmed clinician's lines (W) and others' (U), with U split by script role (`patient`, `next_patient`, any other); for the lines holding a material fact the reference reading leaves out silently — how many got a key, `none`, an unread answer, no answer; the facts still silent after accepting every suggestion, as facts and as encounters; facts wrongly present via a suggestion; suggestions accepted at or after the reference tail start where no boundary was detected; replies whose preceding clinician line is neither in the note nor suggested; the answer-budget evidence — the model's token count of each of the 17 keys and of `none` written as a FULL answer line (`<n> <key>` with its line break, at a one-digit and at a two-digit number), and the **budget table**, computed with `count_tokens` alone. The bounded answer forms are a FINITE set: a window number, then optionally `?`, then optionally one of `.`, `)`, `:`, `-` (the parser admits these today), then a space, then a key or `none` in lower case, with a capital first letter or in capitals, then optionally a full stop, then the line break — every combination. **L** is the largest token count of any such full line over every key and `none`, every window number 1 to 40 (a window numbers its context lines too, so a few asked lines can all carry two-digit numbers) and every form: the maximum is TAKEN by count, never assumed from digit length or a named key. The table prints, for every asked count n from 1 to 40, the bound n × L, a measured cross-check (the token count of a complete answer of n copies of the line that gave L, which must not exceed the bound; if it does, the larger figure is the bound and the report says so), and `answer_token_budget(n)`, naming the largest shortfall. It prints L for each tier A choice separately (the forms a given choice would admit), so 0.4 can size the budget for what it chooses. A casing outside the three named forms stays parseable but is not bounded; a completion that still runs out is caught by "cut at budget"; the stage's own counts as `suggestion_pass` and `SuggestionStageResult` give them — suggestions accepted from the clinician's lines (W) and from others' (U), suggestions dropped at acceptance, lines asked, lines not assessed, model calls, and **fit reductions** — every time `_fit_window` shortens a candidate, counted in the recorder from the stage's own `count_tokens` calls on window texts (within one candidate's fit, each token count after the first is one reduction), reported as a total per set, so a halved prefix that holds only context lines (no model call) and repeated reductions in one encounter are both counted; the stage's version, the model id, seconds.
  - `--timing`: D7's constructed window of 40 asked lines, one completion, seconds and completion tokens printed, with D7's three identity lines (module path, stage version, input hash); `--source-root` as D7 defines it.
  - `--verbose`: also prints each window's raw completion (synthetic text) to the console.
  - Done when: tests cover the classifier (one case per shape, plus an echo of each prompt line shape, a malformed line and an out-of-window number counted unattributable), the fit-reductions count (a context-only fitted prefix; two reductions in one encounter), the refusal, the input's equality with `suggestion_pass`'s on a fixture script, and `--verbose` off printing no line or completion text; the suite passes; the C4 pin is untouched.
- [ ] 🟥 **0.3 The `suggest-v1` baseline.** Run the script at the current commit on `validation\heldout-6` and `validation\scripts` (agent-runnable; C9), plain first, then `--verbose` in the foreground for `heldout-6`; `--timing` once. Not `heldout-2` (C11).
  - First gate: on `heldout-6` the v1 stage must give a key to about none of the silently lost patients' lines, and its W / U totals should be near run 9's (W 13, U 4). If instead it suggests most of them, the cause is in the audio-level path, not the model: stop and report (a pause for the practitioner).
  - Done when: both tables, the timing line and a short reading of the cause (which shapes dominate; whether the budget cuts completions; what the model answers for replies) are recorded on this task — counts and shapes only, no line or completion text.
- [ ] 🟥 **0.4 The repair, the thresholds and the shape of the rest** `[decision]`
  - Options, each chosen on 0.3's table and written here BEFORE any repair number exists:
    - which tier A items are built (the `?` after the number; case-folding; trailing punctuation; the answer budget constants, set so that `answer_token_budget(n)` is at least 0.3's bound for the forms chosen here PLUS a closing allowance at EVERY n from 1 to 40 — the allowance, a stated number of tokens for whatever ends the completion (the model call passes the budget as `max_tokens` and returns the content only, so the text's count leaves it out), is chosen and written here with the derivation);
    - which tier B items are allowed if tier A falls short (the speaker label: `patient` or a neutral wording — a `patient` label would also name a partner, a carer or an undetected next patient, so 0.3's split of U by role is read first; the hint wording; the "none" wording; "an answer belongs with its question");
    - D9: "assessed" stays as it is, or counts only lines with a valid answer;
    - the go / no-go numbers for S.4, on `heldout-2` at text level, where today's count is 25 silently lost material facts in 14 encounters: **E** = encounters still holding a silent material omission after every suggestion is accepted. GO, gate-capable: E = 0. GO only on the practitioner's word: 0 < E ≤ E_max and facts remaining ≤ F_max, with run 10 then pre-registered as expected to fail on silent omissions. NO-GO: anything else. Either GO also needs: facts wrongly present via a suggestion ≤ H_max; suggestions on a next patient's lines with no boundary detected ≤ T_max; the paired timing ratio ≤ R_max and no line unassessed. (Suggested at planning: E_max 3, F_max 12, H_max 1, T_max 1, R_max 1.5 — the practitioner sets them.)
    - M.2's bound, also fixed here: for every wrongly-present-via-suggestion or newly `material_wrong` fact that run 9's reports lack, at least N silent facts removed across the seven sets (N set here), and no seen set flipping PASS to FAIL beyond what the repair's own additions explain;
    - whether Phases S to P stand as written.
  - Decide after: 0.3.
  - Blocks: S.1 onward.

### Phase S — The repair
- [ ] 🟥 **S.1 Tier A.** `desktop/src/scribe_desktop/note_suggest.py`: `_ANSWER_RE` and `parse_suggestions` to D4's bounds (only the items 0.4 chose), `_ANSWER_TOKENS_PER_LINE` as 0.4 set it, `SUGGEST_PROMPT_VERSION = "suggest-v2"` (D5), and D9's change if 0.4 chose it (then also `ui/models.py`'s unassessed line, `validation.py`'s count and `docs/design-system.md`). Tests in `desktop/tests/test_note_suggest.py` (parser block, the version pin at `:342`) and every other `suggest-v1` pin (`test_ui_models.py`, `test_validation_harness.py`).
  - Done when: one test per D4 bound, including that an echo of each prompt line shape yields no answer and that a key is never matched by prefix; `_fit_window` halves no more often on the tuning sets than before (the script's fit-reductions total no higher than 0.3's baseline); the suite passes; the C4 pin is untouched.
- [ ] 🟥 **S.2 Tune on the tuning sets only** (`heldout-6`, the 50; D6). Attempt 1 is tier A alone, measured with the script. Whenever an attempt changes the answer format the instruction asks for, or the variants the parser admits, the script's budget table (Task 0.2) is re-run first and the budget must still cover its bound plus 0.4's closing allowance at every n before that attempt's numbers count. A tier B item is built (in `SUGGEST_INSTRUCTION`, `_OWNER_HINTS`, the labels, with their pins at `test_note_suggest.py:326-375`) only if the lower tier leaves 0.4's thresholds unmet on the tuning sets, one item or one coherent group per attempt. At most five attempts; each attempt's table and its paired timing (D7; create the detached worktree of `526913f` outside the repository before the first) recorded on this task.
  - Done when: an attempt meets 0.4's thresholds on the tuning sets, or five attempts are spent (then stop: S.4 is decided on the best attempt, named as such); the suite passes at the chosen attempt.
- [ ] 🟥 **S.3 Freeze, then the check.** Record the frozen stage's commit-ready state; run the script ONCE on `validation\heldout-2` at text level, plain (no `--verbose`).
  - Done when: the table is recorded here with E, the facts remaining, the harm counts and the timing ratio, beside 0.4's thresholds. `heldout-2` is now spent as a check (D6).
- [ ] 🟥 **S.4 Go / no-go** `[decision]`
  - Options: GO (continue to Phase V); GO on the practitioner's word with run 10 pre-registered as expected to fail on silent omissions; NO-GO — build the named fallback as its own plan, or close this plan with no change (D15).
  - Decide after: S.3, read against 0.4's thresholds. Text level is an upper bound on audio level.
  - Blocks: Phase V onward.

### Phase V — Version and code hardening (before the audio-level measurement, D10)
- [ ] 🟥 **V.1 Version 0.3.7.** The six version strings (Key Findings) and `npm version` for the extension's two files; `CHANGELOG.md`'s 0.3.7 entry opened.
  - Done when: the version tests pass; the suite passes.
- [ ] 🟥 **Step H: Hardening pass over the code diff** (`note_suggest.py`, the script, their tests, any D9 sites)
  - [ ] 🟥 H1: `/review-loop` (or `/review` → `/fix`) to convergence
  - [ ] 🟥 H2: `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`
  - [ ] 🟥 H3: `/security-review` — the parser's bounds (D4), the script's custody of completions (C2), the unchanged refusals; same routing
  - [ ] 🟥 H4: a cross-family codex pass to convergence (agent-driven; evidence line per file)
  - A fix here that changes the stage's behaviour is D14's case: pause for the practitioner (the check-set read is void).

### Phase M — The cost at audio level
- [ ] 🟥 **M.1 The seven seen sets, once.** At the hardened commit, clean tree. Check the installed voices against the voice baseline; rebuild the seven sets into `C:\sr-m1\<set>` with `scripts/build-validation-set.py`; run each as `scripts/run-validation.py C:/sr-m1/<set> --config validation/config --rule validation/rules/rule-v6.json --set <set> --suggestions confirm-all --prose` in the background (C9), reports by bash redirection into the git-ignored `.cursor/loops/sr-m1/` with their SHA-256. `off` is not re-run; record D10's `git diff --stat` line.
  - Compare each of the six older sets with its baseline in `.cursor/loops/`: `stage-4-f1-confirm-<set>.md` for the 50, `heldout`, `heldout-3`, `heldout-4` and `heldout-5`, and `stage-4-f1-confirm2-heldout-2.md` for `heldout-2` (its SECOND F.1 run, the one of record, SHA-256 `758e711f…`; the first run did not reproduce and is never the baseline). Before comparing, check each baseline exists and that its SHA-256 equals the one NCD's Task F.1 records for it; a missing or mismatching baseline is a pause (the practitioner chooses a `suggest-v1` baseline re-run of that set from the detached worktree, or comparison with the harness record only, as for `heldout-6`). List every changed encounter row, fact verdict and verdict line. `heldout-6` has no retained report (run 9's copies are deleted), so it is compared ONLY with run 9's retained record in `docs/testing/validation-harness.md` and NCD's P.2 / P.5: the four verdicts, the TOTAL row, the failing encounters with their reasons, the residue members, the three encounters with suggestions and their counts, the wrongly-present-via-suggestion facts and the diagnosis's fact classes; a difference in a row that record does not hold is reported as "not comparable", never attributed. A set that differs where the repair cannot explain it is re-run once at the same commit.
  - Done when: per set, the four verdicts, the TOTAL row, the suggestion columns, the silent facts removed and every newly wrong or wrongly-present fact are recorded here (ids, counts and verdicts only), with the stage's version and the commit.
- [ ] 🟥 **M.2 The cost decided** `[decision]`
  - Options: keep the repair as measured; narrow it (a named change — D14: this repeats M.1, and `heldout-2` cannot be re-read); stop (the fallback as its own plan, or close with no change — D15, which here also restores V.1's version strings).
  - Decide after: M.1, read against the bound fixed at 0.4.
  - Blocks: Phases D, F, P.

### Phase D — Documents
- [ ] 🟥 **D.1 Documents whose claims change** (line endings per file, C10): `CHANGELOG.md` (0.3.7; the measurement script); `AGENTS.md` (Current Status paragraph, a Local Run Steps line for the script, the section-suggestions pointer); `scripts/README.md`; `docs/testing/validation-harness.md` (the script, 0.3's and S.2–S.3's tables, M.1's record; D9's metric amendment if chosen); `docs/security/threat-model.md` "Phase 3B (coverage)" (what the prompt shows, D4's parser bounds as the enforced list, the script as a synthetic-only developer flow; the "exactly three" call sites restated unchanged) and flow 29 of `docs/security/data-flow-map.md`; `docs/security/retention-schedule.md`'s in-memory suggestion row only if a claim changes; `docs/release/pilot-builds.md` ("Rolling back below 0.3.7": no data step); `docs/design-system.md` if D9 changed the unassessed line; the clinician review guide's suggestion lines and `docs/practice/README.md` only if their wording changes (then the practitioner's approval before P.3); `PLAN.md`'s Phase 3B line if it names the suggestion prompt.
  - Done when: each named document is either edited or recorded here as "no claim changed" with the line checked; the document tests pass.
- [ ] 🟥 **D.2 A codex pass over the documents alone** (their own slice, one evidence entry per document), to convergence.

### Phase F — The freeze
- [ ] 🟥 **F.1 Rule v7 and predictions v7.** First confirm nothing under `desktop/src/` or `scripts/` changed since M.1's commit (else M.1 is repeated for the sets that change reaches). Then: `validation/rules/rule-v7.json` (D11; covered by `.gitattributes`' `validation/rules/*.json text eol=lf`); in `desktop/src/scribe_desktop/validation.py` the `v7` label branch and its history sentence beside the kept v5 / v6 ones (`:3822`, `:3836`) and the docstring that lists rule versions; tests — a `TestRuleV7` beside the untouched v5 / v6 classes, the label tables in `test_validation_metrics.py`, the negative pin `rule-v7-test` → `rule-v8-test` in `test_validation_harness.py`, and in that file the positive v7 counterparts of four v6 tests, each beside its untouched original: the repository rule needing one of its eight sets (`test_the_repository_rule_v6_needs_one_of_its_seven_sets`), the ceiling table equal to the file's (`test_the_rule_v6_ceiling_table_is_the_files`), a `heldout-7` gate-set report (`test_a_heldout_6_report_under_rule_v6`) and a `heldout-6` report counting marked R1 (`test_a_heldout_5_report_under_rule_v6_counts_marked_r1`) — the last two asserting that the v5 and v6 history sentences are kept and that a v5 or v6 report prints no v7 sentence; `docs/testing/validation-harness.md` gains "## Rule v7" (the ceiling table, the gate for run 10, the known cost from M.1, predictions v7 with the list of report lines allowed to differ, the one-run residue and the re-run rule); `CHANGELOG.md`.
  - Predictions v7 are M.1's reports read under rule v7's labels and schedule: ids, counts and verdicts only.
  - Done when: the suite passes; rule v7 and predictions v7 are in ONE commit (on the practitioner's word) made before `validation/heldout-7/` exists. D14's freeze starts at that commit.
- [ ] 🟥 **F.2 `heldout-7`: pre-registration and plumbing** (the folder still absent). Model: NCD Task F.2's "The plumbing BUILT" list, site for site with `h7` / `heldout-7` in place of `h6` / `heldout-6` — re-locate every site by name, not by line number:
  - `desktop/tests/fixtures/heldout_transcripts.py` (`HELDOUT_7_CASES = ()`; the `HeldOutSet("heldout-7", "h7-", …, cases_written=False, tails_by_role=True, script_count=(20, 25))` row, `routed_material` left False);
  - the lint grammar `_STEM` in `scripts/lint_held_out_plugin.py` and `desktop/tests/test_validation_scripts.py`, with that file's set-list, prefix, role-set / blind tests and the refused id moved to `h8-01`;
  - `desktop/tests/test_lint_held_out_set.py` (admit `h7-`; refuse `h8-`; the blind pin `["heldout-7"]`);
  - the three per-set divergence tables and their count pins gain an empty `heldout-7` entry (`test_note_check.py`, `test_note.py`, `test_consultation_boundary.py`);
  - `desktop/tests/test_pilot_docs.py` (the Encounter pattern admits `h7-`; the refused id moves to `h8-01`) and the findings register's legend if it names the sets;
  - `validation.py` (the `--set` help literal; `rule_v2_counterpart`'s docstring) and `test_validation_harness.py`'s help pin moved to rule v7's eight names;
  - `.github/workflows/ci.yml` (`$folder = "validation/heldout-7"`, falling back to `validation/heldout-6` while the folder is absent);
  - `validation/README.md`, `scripts/README.md`, `AGENTS.md` Local Run Steps step 15, `docs/pilot/README.md`;
  - `scripts/lint-held-out-set.py`'s docstring (words only, no behaviour): it names `heldout-7` the blind set and its command from the moment the set is authored (NCD's F.2 left this out and noted the gap).
  - The pre-registration, written into this task and `docs/testing/validation-harness.md` before the set exists: the brief (`heldout-2`'s with only its set number and id forms changed, generated and leak-checked by the `ncd-brief-leak.py` method); the falsifiers; D12's next-patient expectation; S.4's expectation on silent omissions; that the set is run once and the one-run residue applies.
  - Done when: the suite passes plain (the folder absent); the commit is made on the practitioner's word before any authoring.
- [ ] 🟥 **F.3 `heldout-7` authored blind** (C7). The executor prepares the author folder `C:\heldout7-author` holding the brief alone and the author script and prompt from the templates (Accepted Assumptions), and preflights a throwaway `claude -p` with the recorded flags. **Pause: the PRACTITIONER launches the author script from a normal terminal.** Then the executor copies the set in unread (`sha256sum -c`), counts identifying forms in the author log, writes `REFERENCE_TAIL_STARTS`' `h7-` rows with the ids-and-integers script (`ncd-heldout6-tails.py`'s method), adds the temporary presence pin, and records the two SHA-256 in `validation/README.md`.
  - Done when: the suite passes through `scripts\lint-held-out-set.py validation\heldout-7` (from here the only way it runs); nothing under `desktop/src/` or `scripts/` beyond F.1's and F.2's lists and the tail rows changed since F.1 (D14); the commit is made on the practitioner's word.
- [ ] 🟥 **F.4 A codex pass over Phase F's diff** (the rule, the label code, the plumbing; never the set's scripts), to convergence.
- [ ] 🟥 **H5 The build of record.** On the practitioner's word: push; CI green (it routes the suite through the blind runner); the `Release` workflow at F.3's commit (or F.4's, if it changed anything); `gh attestation verify` and the hash check; `docs/release/pilot-builds.md`'s row.
  - Done when: 0.3.7 is a build of record at the run-of-record commit. A code or rule change after this means a new run-of-record commit and H5 again.

### Phase P — The practitioner
- [ ] 🟥 **P.1 Run 10.** On the practitioner's word, from a clean checkout at the run-of-record commit (D14's documents-only allowance, shown by `git diff --stat`): build and run the 50 and `heldout-7` (once) under `validation/rules/rule-v7.json` with `--suggestions confirm-all --prose`; then the six reported sets from M.1's builds, the same day (non-blocking for the gate's outcome).
  - Done when: the four verdicts, every column of each TOTAL row, the residue lines, the suggestion columns and the comparison with predictions v7 are recorded here and in `docs/testing/validation-harness.md` ("Runs of record", run 10), with the stage's version and the commit; the gate's outcome is named. No rule is edited (C8).
- [ ] 🟥 **P.2 Shadow mode decided on run 10's outcome** `[decision]`
  - Options: keep shadow on; off for clinic 1's reviewed consultations (only on a passed run 10; pilot D7).
  - Decide after: P.1.
  - Done when: the practitioner's words are here and on `plan-pilot.md` P.5.
- [ ] 🟥 **P.3 Installing 0.3.7** `[decision]`
  - Options: install with shadow as P.2 decided, then the smoke; do not install (0.3.6 stays).
  - Decide after: P.2. If installing: re-verify the download from a normal terminal, install, reload the extension, restart Chrome; one mock shadow consultation of MORE than 40 transcript lines — a `[suggested: …]` mark on a patient's reply with its pre-selected section, Add clearing it, Save while marks pend, nothing in Copy, the audit CSV's `app_version`.
  - Done when: the decision and, if installed, the smoke line are here and `AGENTS.md` names the installed build.
- [ ] 🟥 **P.4 The `h7-` cases and the diagnosis** (the blind period ends with P.1's record). `heldout_transcripts.py`'s 22-odd cases and `cases_written`; the three per-set tables read off the shipped code; in `test_consultation_boundary.py`, `heldout-7` joins `_SETS_READ_AFTER_THEIR_RUN` AND gets its own `_BOUNDARY_CHANGES_ON_HELDOUT_7` table with the before / after phrase-list assertion block that `_BOUNDARY_CHANGES_ON_HELDOUT_6` has (so its historical comparison is checked, not only excluded) and its own rule-4 test; the blind pin back to `[]` and the presence pin removed; CI's and the runner's comments; `validation/README.md`, `scripts/README.md`, `AGENTS.md` step 15. The diagnosis by NCD P.5's method (each failing fact classed against the reference reading; word-level observations attributed to the diagnostic re-run).
  - Done when: the suite passes plain and through the runner; the diagnosis is recorded here and in the harness document.
- [ ] 🟥 **P.5 Records and close.** Findings-register rows (run 10's `h7-` findings; F-155's dated status line; a row per wrongly-present-via-suggestion kind), `AGENTS.md`, `CHANGELOG.md`, this plan's lifecycle state and Retained Follow-Up Items, `/document`. The practitioner deletes `C:\sr-m1\`, `C:\heldout7-author\` and the detached worktree (the agent shell cannot delete a top-level `C:\` folder).
  - Done when: the plan reads Completed — Follow-ups Retained (or Archivable) with its follow-up items reconciled.

## Retained Follow-Up Items
(Filled at the close.)

## Follow-Up Continuation Notes
(Filled at the close.)

---
*Plan saved to: .cursor/plans/plan-suggestion-repair.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
*Sections marked (Only if relevant) can be omitted when genuinely not applicable, but never omit decisions, constraints, verification steps, or integration knowledge that a fresh session would otherwise have to rediscover.*
*For lightweight plans, plans with fewer than 5 tasks, or plans created without a preceding `/explore` discussion, sections with no real content should be marked `N/A — simple feature` rather than padded with placeholder structure.*
*State-once convention (new plans): state each cross-section contract — a critical constraint, design decision, invariant, or other normative rule — once in its canonical section, and have every other section point to it rather than restate it. Scope guard: this governs cross-section normative duplication only — the Task Specification Standard (in `/create-plan` and `/review-plan`) and task-local detail are untouched, and a plan recording `fast/medium involved` in its Executor tier may keep extra restatement where it helps the fast executor. It applies to new plans as they are written; never retroactively rewrite an existing plan to conform.*
_Plan drafted in Plan Mode and hardened by `/review-plan` on 2026-11-14 (Fable 5.2; exploration began on Opus 5.5 before the practitioner switched the model). Critique gate: three parallel lenses (Coverage and risk / Practicality / Simplicity), every finding dispositioned in the plan. Planning only: nothing built._
