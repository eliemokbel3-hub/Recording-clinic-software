# Feature Implementation Plan
**Feature:** validation-run8 — rule v5 (the review-controlled class named and reported on the blind set), the clinician review guide's control in plain words, a fresh blind `heldout-5`, validation run 8 as the run of record, and the practitioner's shadow-off decision. No version change: developer tooling, a blind set, documents and a decision — no app code, no build of record, no install. Shadow mode is turned off, if it is, on the installed 0.3.5 by the Status tab's tick.

**Overall Progress:** `93%` (2026-11-07: 13 of 14 buildable tasks done — 0.1, 0.2a, 0.2b, 0.3, 0.4, 0.5, 1.1, 1.2, H1–H4 and P.1 (run 8 recorded and committed `5edcefa`, 🟩: the practitioner's cleanup is owed). P.3 is 🟨 for its commit only (the diagnosis, the overlap value 10, `h5-17/f0`'s class — the recogniser's, a dropped word with no mark — and the suite, 9836 passed plain and through the runner, recorded). Dropped: P.4′, not applicable — P.2 chose keep shadow on (2026-11-07), so it leaves the count, as the larger-model plan's dropped tasks did. P.2 🟩 (Chosen: keep shadow on, 2026-11-07; its register rows and approvals written, committed with P.3). The 14: 0.1, 0.2a, 0.2b, 0.3, 0.4, 0.5, 1.1, 1.2, H1–H4, P.1, P.3; the `[decision]` entries 0.0 and P.2 are outside the count, the 0.3.4 convention. Phase P is done but the commit)

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- **Parent plans:**
  - `plan-pilot.md`: P.5 decided (a) on 2026-10-22, 2026-11-04 and, by application, 2026-11-06 — shadow mode stays on until a validation run passes; the exit gate's "Validation passed" (`docs/pilot/exit-gate.md:16-27`) waits on it. This plan is the next cycle. Its D7 is the P.5 decision's shape.
  - `plan-larger-model.md` (Completed — Follow-ups Retained, 2026-11-06): Task 0.6 decided No change (`medium` stays; register F-148); its Follow-Up Continuation Notes name this plan's question ("the review guide and the harness's R1 ceiling as the honest home of the residue"); its retained item "`heldout-5` and rule v4 stay planned, without a run" (`:723`) is taken over here (Task 1.2 writes the dated line); its D5 (rule v4), D6 (`heldout-5`, the isolated author) and D7 (predictions = the measurement, frozen) are the shapes D1, D4 and D5 follow.
  - `plan-validation-run7.md` (Completed — Follow-ups Retained): run 7 failed rule v3's gate on R1 alone (P.1, P.4); its D4 (rule v3's R1 exemption) and C15 (the predicate fixed before any re-read) are the precedent for a new rule version decided before its run; its two retained smoke items are re-deferred here (Deferred).
- **Related plans:** `plan-invented-text-guard.md` (C2: constants decided once — D6 freezes them; the `[check: number]` mark's ubiquity is rule v3's "Honest limit"); `plan-validation-pass.md` (the frozen vocabulary; its four retained items stay there); `plan-clinic-smoke.md` (D12: nothing per consultation in a tracked file — C8 here; the pilot's P.4 ten shadow consultations are its Phase P); `plan-ui-refresh.md` (branch `claude/ui-refresh-bf9282`, not merged, untouched); **`plan-gpu-decoding.md`** (Active; committed `9bdafa7` on 2026-11-06 by another session, peer-converged; not visible when this plan was drafted): it ALSO plans `heldout-5` (pre-registered, the same author), predictions v4 and "validation run 8" under rule v4 unchanged with `large-v3@cuda` (its outcome (i)), version 0.3.6, and a decode change that falls inside this plan's C17 window; its continuation note reads "never a rule or ceiling change" and its C11 leaves the review guide and the rule ceilings to this session. Both cannot own `heldout-5` and run 8: the order is the practitioner's Task 0.0 `[decision]` (peer round 1 PR-HIGH-001), and the chosen option is written as a dated line on BOTH plans' lineage. **2026-11-06 — Task 0.0 decided A: this plan first.** Run 8 is this plan's — `heldout-5` under rule v5 with `medium` on CPU; the GPU plan's run, if its Task D reaches outcome (i), is run 9 on a fresh `heldout-6` pre-registered first; its decode change lands only after this plan's P.1, so C17 holds with base `170345d`; the files both plans edit are this plan's first and the GPU plan re-bases onto them. The GPU plan's own line is its session's.
- **Follow-up plans:** none yet; candidates under Deferred (the distinct mark for a low-confidence number; the practitioner's own phrases).

## Goal
Answer, on a rule fixed BEFORE any prediction and before the blind set is written, what turns shadow mode off now that a larger speech model is ruled out — and put the decision to the practitioner with its acceptance in plain words.

What run 7 and the larger-model measurement left, and what this plan does about each (ids and counts only):

| What | Run 7 / 2026-11-05 | Cause | This plan |
|---|---|---|---|
| R1 marked wrong — a misheard material fact under a review mark | `heldout-4`: 2 (`h4-01/f5`, `h4-07/f0`) over a ceiling of 1; 5 over the five sets (`syn-28/f1`, `hld-07/f0`, `h3-03/f0`, `h4-01/f5`, `h4-07/f0`); a larger model no better | The recogniser; the mark is the product's control | D1: rule v5 reports the class on the blind set under a pre-registered band with a consequence (D7); D2: the review guide names the control with the measured counts |
| R1 silent — a recogniser misrendering that left a fact out unwarned | 1 (`syn-22/f2`, the 50) | The recogniser; nothing in the review surfaces it | Stays ceilinged (D1) |
| Confident errors with no mark | 2 (`hld-14/f1`, `hld-21/f3`; `heldout`) | The recogniser below the mark | Stays a falsifier (D4) |
| R3 unbroken next patient | `heldout-4` 0 of 7 reached a note; `heldout-3` 2 under the old lists | The lists (30 / 26) | Frozen (D6); ceiling 1 stays |
| R2 tone only | `heldout-4` 4 + 1 bare modal, reported | Hedges outside the frozen list | Frozen; reported |
| 64 register rows controlled by "Shadow mode on" | every `controlled` row but one | Shadow mode is the control on paper | D7: the acceptance stated per class; the rows re-worded in one commit when shadow is decided off |

### Honest forecast
Written before anything is measured and not tuned toward:
- **The 50 PASS** (as under rule v3 and v4: R1 2 / R2 1 / R3 2 at or under the fitted ceilings; rule v5 leaves the 50's row's reading as it is).
- **`heldout-5` is a real test.** Under rule v5 these still fail it: R3 above 1 (the author model's phrasing decides; `heldout-3` had 2 of 10 reach a note under the old lists, `heldout-4` 0 of 7 under the widened ones); a confident recogniser error without a mark (`heldout` had 2; the three later sets 0); a silent material fact after R1 (0 on every blind set so far); a wrongly present fact outside R3 (0 so far); an unsupported clinical line the exemption does not excuse (0–1); a checker failure (0 so far). A PASS is likelier than not and is an outcome to report, never a target.
- **Marked R1 on `heldout-5` is expected at 0–3 facts** and is reported whatever it is; each is a `controlled` register row; above 3 the band rule (D7) makes "keep shadow on" the recommended P.5 option.
- **A rule-v5 pass is evidence about the gated sets only.** `heldout-2` (25 silent facts on unrouted patient lines, outside every plan's scope since 0.3.4) and `heldout` still FAIL and are reported; their rows' controls move to the review guide with the rest (D7).
- **What a rule-v5 pass means and does not mean (peer round 1 PR-MED-003).** It means, on the blind set: no material fact wrong without a review mark on its line; at most ONE silent R1 fact (a recogniser misrendering that left a material fact out unwarned — `max_r1_facts 1`); at most ONE encounter whose next patient reached the note (`max_r3_encounters 1`); uncertainty reported and not gated on that row; R2 at any count; no unsupported clinical line the exemption does not excuse; no checker failure. It does NOT mean "nothing reached the note unseen" — those allowances are part of the acceptance (D7). It does not mean the marks are a strong control: `[check: number]` sits on EVERY quoted number (rule v3's "Honest limit"), and the mark may sit on another word of the same line, so the clinician must read every number, unit and spoken abbreviation against memory. The review guide's new lines say so, and the practitioner accepts that when deciding shadow off.
- **Author-model independence is weaker than "fresh blind set" sounds**: the same author, the same brief with four lines changed. The author decides how many spoken-letter abbreviations and dose lines exist — the class under test — so the author-model qualifier covers R1 as well as R3 (D4).
- **Nondeterminism.** Run 7 matched predictions v3 and the 2026-11-05 reproduction matched run 7 line for line; the seen sets are expected to equal predictions v5 exactly; a difference is a finding before anything else is read.

## Planning Extraction Summary
Populated 2026-11-06 from:
- the Plan Mode draft (Fable 5.1; approved by the practitioner through ExitPlanMode), written after reading `AGENTS.md`, `plan-larger-model.md` (Goal, D1–D10, Tasks 0.1–0.6, Retained Follow-Up Items, Follow-Up Continuation Notes), `plan-validation-run7.md` (D4, D5, C1–C15, Acceptance, P.4, Retained Follow-Up Items), `plan-pilot.md` (Constraint 12, P.4, P.5, P.6), `docs/testing/validation-harness.md`, `docs/pilot/exit-gate.md`, `docs/pilot/findings-register.md` (F-087–F-148), `docs/pilot/README.md`, `docs/practice/clinician-review-guide.md`, `docs/practice/README.md`, `docs/lessons.md`, `validation/rules/rule-v3.json`, `rule-v4.json`, `validation/README.md`, `validation/heldout-4/SPEC.md`, the harness code (`validation.py`: the R1 class `:2177-2206`, `_FactState` `:1325-1371`, `SetCeilings` / `PassRule` `:2275-2395`, `rule_v2_counterpart` `:2439-2457`, `class_counts` `:2690-2716`, `_verdict_lines` `:3203-3267`, the heading and amendments `:3285-3346`, `_residue_section` `:3558-3660`) and `.cursor/loops/run7-reports/` (ids and counts);
- a read-only Plan-subagent critique of the first draft (23 findings — 3 HIGH, 11 MED, 9 LOW — all applied before the practitioner was asked anything: `rule_v2_counterpart` would read "differs" on every seen set; `_check_sets` refuses the exemption on schema 4; the `== 3` site inventory; the both-case R1 precedence; the unmarked wrong facts are `hld-14/f1` and `hld-21/f3`; the three standing policy sentences need override lines; the agent-shell run-of-record option removed; the CRLF list);
- the practitioner's decisions in chat, 2026-11-06 (Key Design Decisions below);
- this `/review-plan` pass (Fable 5.1): three read-only lens subagents — coverage (10 findings), practicality (9), simplicity and risk (17) — every finding checked against the code at `4d6f7a1` (tree clean) and reconciled in place; the world-state re-probe (Validation / Verification).
- No `/explore` scratch was consumed (the practitioner, 2026-11-06: "None (Recommended)" — the two in `.cursor/plans/` are unrelated).

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable 5.1 (the practitioner's answer 2026-11-06: "Entirely premium (Recommended)"); the build runs through `/execute-loop` with executor `claude-opus-5-5` high, cross-family peer codex `gpt-6-astra` medium, verify=composer, isolation none; the blind authoring's launch, run 8, the register's shadow-off commit and every P-task are PRACTITIONER-run from a normal terminal (`docs/lessons.md`, MSIX; C10). Tier-gap dosing applied: rule v5's predicate, rows and schema, the fourth verdict's semantics, the report-line inventory, the derivation rule for predictions v5, the pre-registration's falsifiers, bands and the band rule, the override lines' wording and the review guide's claims are locked here.

### Agreed Scope (Build Now)
- **Phase 0:** the order decision against `plan-gpu-decoding.md` (0.0); this plan's commit (C16); rule v5 — schema 4, the per-row field, the file, the loader pins (0.2a); the reading, the fourth verdict, the report's new line and the string changes (0.2b); predictions v5 derived from run 7's reports by a scratch that reproduces run 7 first (0.3); `heldout-5`'s pre-registration with the band rule (0.4); the blind authoring (0.5).
- **Phase 1:** the clinician review guide and the practice README (1.1); the harness, pilot and security documents, the scripts' docstrings, the stale task cites, the four override lines, the plans, `AGENTS.md`, `CHANGELOG.md` (1.2).
- **Hardening H1–H4** (no H5: nothing to build).
- **Phase P (practitioner):** run 8 on six sets (P.1); the register, the P.5 decision and the approvals, with the shadow-off register commit if decided off (P.2); the `heldout-5` diagnosis (P.3); shadow off on the installed app, after the pilot's P.4 (P.4′).

### Deferred — Actionable Later
- **A distinct, stronger mark for a LOW-CONFIDENCE number in the app** (the practitioner 2026-11-06: "Defer with trigger (Recommended)").
  - Why deferred: it is app code — a version, a build of record, an install and a smoke — and run 8 would then measure two changes at once.
  - Intended future outcome: a low-confidence number is marked apart from the `[check: number]` every quoted number carries, so the mark carries information again.
  - Relevant files / subsystems: `note.line_marks` / `section_marks_line`, `ui/models.py` `SEPARATELY_ACKNOWLEDGED_CODES`, Check 1's `number_source` / `low_confidence_source`, the review guide.
  - Dependencies / prerequisites: run 8's marked-R1 count and class breakdown (P.3).
  - Recommended next action: a new plan when the trigger fires.
  - Risk if deferred: ux-degradation — the clinician reads every number with the same mark; the misheard-marked rate is about 5 facts in 139 invented consultations.
  - Revisit by: the band rule firing (marked R1 above 3 on `heldout-5`, D7); run 8 failing on a confident unmarked error; or marked numbers passed over during the reviewed consultations.
- **The practitioner's own goodbyes and greetings** (asked 2026-10-13, 2026-10-25, 2026-11-04; 2026-11-06: "Not yet (Recommended)").
  - Why deferred: run 8 measures one change (the rule); a second would muddy it; the phrases cannot be named yet.
  - Intended future outcome: the phrases join the lists in one dated commit under run-7 D2's rules 1–5, with `test_vocabulary.py`'s exact pins moving; the live new-consultation warning widens with them.
  - Relevant files / subsystems: `consultation_phrases.py`, `test_vocabulary.py`.
  - Dependencies / prerequisites: the reviewed consultations on 0.3.5.
  - Recommended next action: ask again at the next plan.
  - Risk if deferred: minor — Start per patient is the primary control.
  - Revisit by: when the practitioner can name their phrases.
- **The leftover status-bar message** (0.3.5's P.2 take 3; 2026-11-06: "Defer to the next install smoke (Recommended)"). Why deferred: no build in this plan to smoke it on. Intended outcome: the call that sets the text and what should clear it found; a fix or a register row. Files: `ui/main_window.py`'s status bar, the new-consultation warning. Recommended next action: reproduce on two mocks in a row at the next install smoke. Risk if deferred: minor — the warning never acts. Revisit by: the next install smoke.
- **The joined-hedge `[check: unsure]` mark never exercised live** (2026-11-06: "Defer to the next install smoke (Recommended)"). Why deferred: the same. Intended outcome: one live take with a long comma pause, or a kept recording's replay, shows the mark. Files: `note.segment_hedged`. Risk if deferred: minor — it rests on the suite's pins. Revisit by: the next install smoke.
- **The stale "schema 3" docstring words in `validation.py`** (recorded 2026-11-06 by H1 review round 19 LOW-002; the deferral itself was Task 0.2b's, peer round 7, forced by C17 (b)). Why deferred: C17 (b) bars any `validation.py` hunk outside its symbol list until run 8, and these sit outside it. Intended outcome: ONE docstring-only commit naming schema 4 where the text still calls schema 3 the newest or the last — `EncounterMetrics` (two docstrings), `RULE_V2_RATIFIED`, `rule_failures`, `run_passed` ("a schema-2 or schema-3 rule") and `evaluate_encounter` (Task 0.2b deviation (iv)). Files: `desktop/src/scribe_desktop/validation.py` alone. Risk if deferred: minor — docstrings only; the behaviour is schema 4's and pinned. Revisit by: after P.1 is committed, when C17 lapses (before P.3's commit, or as its own).
- Carried from `plan-validation-pass.md`, unchanged and still owned there: the one-click undo of a false boundary; the transcript divider at the possible next patient; the mark pairing a retracted statement with its carried correction; the carry's question-answer hop.

### Excluded — Revisit Only If Needed
- **Any ceiling for marked R1 other than "reported"** (an integer fitted to the failure; a rate ceiling). Why excluded: Constraint 12's spirit even under a new version. When to revisit: never as a fitted number; a future rule that gates the class decides its ceiling before its own blind set.
- **Reporting ALL of R1.** Why excluded: it un-gates the silent recogniser omission, which nothing in the review surfaces. When to revisit: never.
- **Run 8 under rule v4 unchanged.** Why excluded: offered to the practitioner 2026-11-06 and not chosen — a coin flip on the review-controlled class. When to revisit: never for run 8.
- **A sealed `heldout-6` authored now** (2026-11-06: "Accept exclusion (Recommended)"). Why: the next brief depends on run 8's findings; an unlinted sealed set can hide an authoring error. When to revisit: a later plan that needs a blind set — pre-registered first; under Task 0.0's option A the GPU plan's run 9 is that plan, and `heldout-6` is ITS to pre-register, after this plan's P.1.
- **A change to `UNCERTAINTY_THRESHOLD`, the guard's constants, the primer or any decode parameter; a fourth speech model.** Why: each is its own dated decision with its measurement repeated (`plan-invented-text-guard.md` C2); the model question is closed (F-148). When to revisit: run 8 failing on R1 silent or on a confident unmarked error (Follow-Up Continuation Notes).
- **Any edit to rule v1's file (`option-a-proposed.json`), `rule-v2.json`, `rule-v3.json`, `rule-v4.json`, `validation/config` or a seen script's facts** (C2).

### Accepted Assumptions — Revalidate Later
- **Nothing between `170345d` (the 2026-11-05 reproduction) and run 8's commit changes `medium`'s decoding or routing.** Why accepted: `git log 170345d..4d6f7a1 -- desktop/src validation/config validation/scripts scripts/run-validation.py scripts/build-validation-set.py` is empty (verified 2026-11-06), and this plan's code touches only the rule and report regions of `validation.py` and a docstring (C17). Risk if false: run 8's seen sets differ from predictions v5 — read as a finding before anything else. Trigger: C17's diff review at every commit; Task 0.0's option (under option B the GPU-decoding plan's decode change lands first, this assumption is void, D5 with it, and C17 (a) is read from that plan's last decode-affecting commit).
- **Run 7's five reports in `.cursor/loops/run7-reports/` are byte-identical to run 7** (the composer's `cmp` of 2026-11-05) and print enough per fact — Verdict, Ambiguous, Residue class — to derive each R1 member's kind (D5). Risk if false: predictions v5 are wrong on a line; the scratch's byte-for-byte reproduction of run 7's verdict and residue lines under rule v3 (Task 0.3) is the check.
- **The isolated `claude -p` invocation's flags (`--restricted --safe-mode --strict-mcp-config --disallowedTools WebSearch Agent --permission-mode acceptEdits --model claude-opus-5-5`) are still accepted by the installed CLI.** Risk if false: the author fails to launch. Trigger: a throwaway `claude -p` with the same flags before Task 0.5 (`docs/lessons.md`: preflight the CLI itself).
- **The pilot's P.4 has fewer than five of its ten eligible shadow scores at planning** (the practitioner, 2026-11-06, as an aggregate). Risk if false: none — P.4′ waits on the tenth whatever the count. Trigger: P.2.
- **The installed 0.3.5 (`c985857`) and run 8's commit decode alike for `medium`.** Between them `e06fbe6` added the mel-filter check after a Whisper load and `0641c08` the harness's `--model` flag; the 2026-11-05 reproduction at `170345d` printed run 7's reports line for line. Risk if false: the validated pipeline is not the installed one. Holds under Task 0.0's option A (decided 2026-11-06: the GPU plan's install, if any, comes after this plan's P.1); it would have been void under option B (i) or (ii) (PR-HIGH-002). Trigger: P.1's record (D7's sentence).

### Key Design Decisions
D1–D8 below. The practitioner's decisions, all 2026-11-06, in chat, each the recommended option: the rule — "Rule v5: report marked misheard facts (Recommended)" (D1); own goodbye and greeting phrases — "Not yet (Recommended)" (Deferred); plan name `plan-validation-run8.md`; executor tier "Entirely premium (Recommended)"; the band rule — "Yes: above the band → keep shadow on (Recommended)" (D7); the register's shadow-controlled rows — "Yes, one commit at shadow-off (Recommended)" (D7); no explore scratch consumed; the shadow-score count recorded as "fewer than five of ten at planning"; the four gate dispositions (Deferred / Excluded above).

## Key Findings

### Files / Symbols Involved
- `desktop/src/scribe_desktop/validation.py` (4216 lines at `4d6f7a1`): `RULE_SCHEMA_VERSION` `:208`; `FactOutcome` (`silent_omission` `:902-913`, `material_wrong_v2` / `silent_omission_v2` `:938-947`); `EncounterMetrics.r1_facts` `:1112-1113` (a metric property — the encounter table `:3364-3372` prints no R1 column; the class counts print in the residue section; stays combined); `_WordInfo.review_marked` `:1155-1156`; `_FactState` `:1325-1371` (`marked`: some aligned word under a review mark); `REVIEW_MARK_CODES` `:1738-1740`; `_excused_by_r1` `:1757-1782`; the R1 / R2 / R3 assignment `:2177-2206`; the checker tally `:2219-2225`; `_RULE_CONFIG` `:2264` (`extra="forbid", frozen=True`); `ResidueClass` / `RESIDUE_CLASSES` / `RESIDUE_CLASS_NAMES` `:2266-2272`; `SetCeilings` `:2275-2291`; `PassRule` `:2294-2395` (`_check_sets` `:2327-2350`, `label` `:2360-2371`, `exempts_r1_lines` `:2373-2375`, `without_r1_exemption` `:2377-2383`, `set_row` `:2385-2395`); `RULE_V2_RATIFIED` `:2404-2435`; `rule_v2_counterpart` `:2439-2457`; `rule_failures` `:2635-2657`; `ClassCount` `:2674-2687`; `class_counts` `:2690-2716`; `class_breaches` `:2719-2724`; `run_passed` `:3121-3136`; `_verdict_lines` `:3203-3267` (line 1's gate / reported lists `:3234-3240`; line 2 and the counterpart `:3242-3259`); the heading `:3285-3302`; the amendments paragraph `:3303-3346` (the rule-v3 history `:3314-3328` gated `== 3`; the rule-v4 sentence `:3331-3337` gated `label == "v4"`); the run-information line `:3350-3362`; `_fact_classes` `:3538-3548`; `_residue_section` `:3558-3660` (the heading `:3580-3582`, the table `:3587-3603`, the after-classes line `:3608`, the excused-lines line `:3614-3628` gated `== 3`); `set_level` `:3219-3224`; `_parser`'s `--set` help `:3780-3787`; `main` `:3843` (docstring `:3850`, the refusals `:3905`, `:3911`); `REFERENCE_TAIL_STARTS` `:668-678` (the `h5-` rows land after `"h4-21": None`).
- `validation/rules/rule-v4.json` (six rows; `heldout-5` gate); `rule-v5.json` NEW.
- Tests: `desktop/tests/test_validation_metrics.py` (`:3071-3072` comment; `:3121` the schema-4 refusal pin; `:3126, :3132, :3138, :3144, :3187` the exemption messages; `_RULE_V2` / `_RULE_V3` fixtures `:3319-3323`; `TestRuleV3` `:3395` with `:3448` `RULE_SCHEMA_VERSION == 3`; `TestRuleV4` `:3548`; the label tests `:3639-3690`; `TestR1Exemption` `:3693`); `desktop/tests/test_validation_harness.py` (`TestRunValidationMain` `:1072`, the refusal wording `:1352`, the `--set` help test `:1444-1461`; `TestHarnessDocument` `:2024-2055`; `TestReport` `:2058` with the whole-report pins `:2513-2552` (`test_a_rule_v4_report_says_rule_v4_at_every_label_site`, parametrised over `scripts` / `heldout-4` / `heldout-5`; `tail[11]` the after-classes line `:2543`), `:2553-2581` (`test_a_rule_v3_report_prints_none_of_rule_v4`) and `:2673-2857` (`test_a_heldout_4_report_under_rule_v3_is_pinned_at_its_counts`, the whole rule-v3 report)); `desktop/tests/test_lint_held_out_set.py` (`:86` grammar; `:455-460` the blind pin `["heldout-5"]`); `desktop/tests/test_validation_scripts.py` (`:24-25, :137, :640, :653-656, :733`); `desktop/tests/fixtures/heldout_transcripts.py` (`:75-80`, `:944-946` `HELDOUT_5_CASES = ()`, `:1011-1020` the `heldout-5` row); `desktop/tests/conftest.py:98-106` (`blind_run_refusal`); `desktop/tests/test_pilot_docs.py` (`:26` the id-shaped pattern — 16+ hex or 7+ digits over every `docs/pilot/*.md`; `:100-149` the register's vocabularies and the control cell's ≤200 chars / no quotes / no id shape; `:117, :297` `h5-` admitted); stale task cites in `test_consultation_boundary.py:162-163`, `test_note_check.py:2758-2759`, `test_note.py:3349-3350`.
- Scratch (gitignored `.cursor/loops/`): `run7-reports/` (five reports, UTF-8 BOM — decode `utf-8-sig`); `run8-reports/` (the 2026-11-05 MEASUREMENT: `medium`, `medium-rule-v3`, `large-v3-turbo`, `distil-large-v3`, `guard` — never the run of record's folder); `run7-brief-leak.py` (`SOURCE`, `OUT`, `EDITS` at brief lines 1 / 5 / 56 / 65, the asserts; `LISTS` = closings, greetings, markers, the two hedge lists — NOT the primer); `validation-run7-heldout4-tails.py` (`SET` `:13`, the glob `:19`, the asserts `:36-37`, `TARGET` = `validation.py`); `validation-run7-heldout4-author-run.sh` (`cd /c/heldout4-author` `:2-4`, the log / done / prompt paths `:9`); `validation-run7-heldout4-author-prompt.txt` (`h4-01.json`); `run7-predict.py` is NOT reusable (pickles under `C:/run7-sets`, `RULES` holds rule v3 only, refuses `heldout-4`). Folders outside the repository still present at planning (agent-shell `ls`): `C:\run7-sets\`, `C:\heldout4-author\`; `C:\scribe-run7\` and `C:\run7-p4\` absent from the agent shell — the practitioner confirms from their own terminal.
- Documents: `docs/testing/validation-harness.md` (CRLF; the policy lines `:42-47, :55, :70, :77, :126`; `## Rule v3` `:161`; `:183-185`; `## Runs of record` `:187`; the run-7 entry `:220-237` with `:237`'s "never to a rule or predicate change"; the 2026-11-05 entry `:238-247`); `validation/README.md` (CRLF); `docs/pilot/README.md:115-120, :128-134`; `docs/pilot/findings-register.md:37-38` and the 64 rows whose control opens "Shadow mode on for every recording"; `docs/pilot/exit-gate.md:5-8, :16-27, :54-56`; `docs/security/threat-model.md:4054-4061`; `docs/security/data-flow-map.md:1289, :1314`; `scripts/README.md` (CRLF; `:92-94, :146-147, :160-161`); `scripts/run-validation.py:13-16`; `scripts/lint-held-out-set.py:4-9`; `.github/workflows/ci.yml:64-78`; `docs/practice/clinician-review-guide.md` (CRLF; header `:8-18`, "Reading the transcript" `:45-50`, step 4 `:95-115`, "A shadow recording" `:189-194`) and `docs/practice/README.md` (CRLF; header `:9-20`, rules `:68-72`, the findings list `:77-89`); `.cursor/plans/plan-pilot.md` (LF; Constraint 12 `:219`; `## Review Findings Log` `:327`; `## Tasks` `:1818`; the stop rule `:1941`; P.4 `:1958-1960`; P.5 `:1963-1985`); `.cursor/plans/plan-larger-model.md` (LF; `:723`, `:730`); `AGENTS.md` (CRLF; step 12 `:53` "under the ratified rule v1"; `:101-121`); `CHANGELOG.md` (CRLF; `:9-17`).

### Codebase Integration Notes
- **R1's two kinds are already distinguishable from the existing flags.** `residue_r1` holds on `verdict == "wrong"` (every wrong state `marked`) or on a silent omission (`:2181-2190`); `silent_omission` for a `wrong` verdict reduces to `silently_omitted_somewhere` (`:860`, set when some equal-cost alignment omits unwarned, `:2150-2152`), and such a fact is necessarily `Ambiguous = yes` (`:2136-2147`). So the split is two properties, no new walk flag, and the Facts table derives it for an unambiguous member (D5; an ambiguous R1 member is refused, not inferred — PR-MED-001).
- **The per-row override pattern exists** (`require_uncertainty_surfaced: bool | None`, D17) and the schema-tied field pattern exists (`unsupported_line_r1_exemption`, both-ways checks in `_check_sets`); `ClassCount.within` already treats `ceiling None` as reported (R2). `extra="forbid"` plus the older-harness refusal precedent forces the schema bump.
- **Frozen pydantic models**: `model_copy(update=...)` skips validation and is already relied on (`:2383`, `:2454-2456`); rows are frozen too, so a copy with every row's field changed copies each row (`{name: row.model_copy(update={...}) for name, row in self.sets.items()}` keeps key order, which `set_row` and the help test rely on).
- **`rule_v2_counterpart` compares rows with only `gate` neutralised** (`:2453-2457`) against `RULE_V2_RATIFIED`, whose schema-2 rows hold `None` for any new field — so the new field's `False` and `None` must compare equal (both neutralised to `None`) while a `True` row stays a substantive difference → `differs` (peer round 1 PR-MED-002).
- **`class_counts` → `class_breaches` → `run_passed` / `set_level`** is the only gate path; the residue table and `_fact_classes` read the same `ClassCount`s. A defaulted trailing `NamedTuple` field leaves every downstream reader untouched.
- **The whole-report pins index lines** (`tail[11]` is the after-classes line in the rule-v4 label pin, `:2543`), so the position of any new residue line is fixed at planning (D1) and the rule-v3 / rule-v4 reports must print no new line.
- **The amendments paragraph is HISTORY**: rule v3's sentence (`== 3`) and rule v4's (`label == "v4"`) must keep printing under schema 4 (as `>= 3` and `schema 4 or label v4`), with one more sentence for label v5 — the larger-model D5 reading, extended.
- **The report label** derives from `rule_name` (`rule-v5`, schema 4 → "v5"); nothing to change.
- **`heldout-5`'s blind machinery is already in the tree**: the fixture row (`cases_written=False`), `HELDOUT_5_CASES = ()`, the lints' grammar (`h5`), the blind pin, `conftest.blind_run_refusal` (fires on the first `h5-*.json`), CI's argument with the `heldout-4` fallback (flips by itself when the folder exists). Task 0.5 adds only the presence pin, the scripts and the documents.
- **`RULE_SCHEMA_VERSION` has no reader outside the harness** (`validation.py:208`, `__all__`, `test_validation_metrics.py:3448`); `test_schema_versions.py` is the app's record schemas.
- **`test_pilot_docs.py` forbids 16+ hex runs in every `docs/pilot/*.md`**: rule blobs and pre-registration hashes live in `validation-harness.md` and the plans, never in `exit-gate.md` or the pilot README; commits there are 7-char.
- **`plan-pilot.md`'s edits straddle its Review Findings Log** (`:219` before `:327`; `:1941` and P.5 after `:1818`): line-anchored byte edits, never a find / replace over the file (`docs/lessons.md`).
- **CRLF**: `AGENTS.md`, `CHANGELOG.md`, `validation-harness.md`, `clinician-review-guide.md`, `docs/practice/README.md`, `scripts/README.md`, `validation/README.md` are CRLF in the working tree (`git ls-files --eol`, 2026-11-06); the plans and `docs/pilot/*.md` are LF.
- **Shared helpers across phases**: `PassRule.label`, `rule_v2_counterpart`, `class_counts`, `_residue_section`, `_verdict_lines` (0.2b and 0.3's scratch); the id-only tail script and the leak check (0.5); `test_pilot_docs.py`'s rules (1.2, P.2).

### External / API Findings
N/A — no network; the isolated author is the installed `claude` CLI (`/c/Users/eliem/AppData/Roaming/npm/claude`), launched by the practitioner.

## Planned Workflow Summary

### Flow 1 — The rule before anything else (Phase 0)
0.0 the order against `plan-gpu-decoding.md` decided → 0.1 the plan committed → 0.2a rule v5's schema and file → 0.2b its reading and report → 0.3 predictions v5 from run 7's reports (reproduce first) → 0.4 the pre-registration with the band rule → 0.5 `heldout-5` authored blind (from here the suite runs only through the runner).

### Flow 2 — The documents and the hardening (Phase 1, H)
1.1 the review guide's lines (awaiting approval) → 1.2 every document, the override lines, the stale cites → H1–H4.

### Flow 3 — Run 8 and the decision (Phase P)
P.1 run 8 on six sets from a clean checkout → P.2 the register, the P.5 decision (the band rule read first), the approvals, the shadow-off register commit if decided off → P.3 the `heldout-5` diagnosis (the blind rule ends) → P.4′ shadow off on the installed app after the pilot's P.4 tenth eligible score.

### Flow 4 — Run 8 fails
P.1's record names the class; P.5 stays (a); P.3 still diagnoses; the next plan by the class (Follow-Up Continuation Notes). No rule is edited.

## Design Decisions

### D1 — Rule v5: the review-controlled class is reported on the blind set (decided 2026-11-06, before predictions and before `heldout-5` exists; C16)
- **What the code calls R1** (`:2177-2206`): a material fact the reference reading gets right, no alignment matching every word, and EITHER (i) verdict `wrong` with every wrong state `marked` — SOME word aligned to the fact's span inside a review mark of any of four codes (`number_source`, `low_confidence_source`, `suspect_source`, `hedged_source`), not the misheard word itself (`:1948-1950`: a `number_source` mark "makes this term nearly always hold for a numeric fact") — OR (ii) a silent omission (the mark term vacuous). Two kinds, two controls: **R1 marked wrong** — the mark and the clinician's reading of every marked number, unit and abbreviation (D2); **R1 silent** — nothing in the review surfaces it. A `wrong` fact silently omitted on another equal-cost alignment is BOTH; it counts as silent (precedence).
- **File:** `validation/rules/rule-v5.json`, `rule_name` `rule-v5`, **schema 4**, LF. Top-level fields = rule v4's (`max_material_wrong 0`, `max_silent_omissions 0`, `require_uncertainty_surfaced true`, `max_word_error_rate null`, `unsupported_line_r1_exemption true`). Rows in rule v4's key order: `scripts` (gate 2 / 2 / 2, fitted, not lowered), `heldout`, `heldout-2`, `heldout-3`, `heldout-4` exactly rule v4's, each with `r1_marked_reported: false`; `heldout-5` gate, `max_r1_facts 1`, `max_r3_encounters 1`, `require_uncertainty_surfaced false`, `r1_marked_reported: true`.
- **The field:** `SetCeilings.r1_marked_reported: bool | None = None`. Schema 4 REQUIRES it non-None on every row; schemas 1–3 REFUSE it non-None (both ways in `_check_sets`, the exemption's pattern). `_check_sets`'s exemption gate becomes `schema_version >= 3` (today's `== 3 … elif` would refuse rule v5's `true`). `PassRule.schema_version: Literal[1, 2, 3, 4]`; `RULE_SCHEMA_VERSION` → 4.
- **The reading:** `FactOutcome.residue_r1_silent` (= `residue_r1 and silent_omission`) and `residue_r1_marked` (= `residue_r1 and verdict == "wrong" and not silent_omission`). `ClassCount` gains a fifth, defaulted field `reported_members: tuple[tuple[str, int | None], ...] = ()`; `class_counts` fills it for R1 only where `row.r1_marked_reported is True`, leaving `total` / `members` silent-only there — `class_breaches`, `run_passed`, `set_level` and the residue table read the same four fields as today. `EncounterMetrics.r1_facts` (a metric property; no table column) stays combined. `material_wrong_v2` / `silent_omission_v2` unchanged (R1 excuses the fact's own failure as before; only the set-level ceiling reads the split).
- **The report, schema 4 only** (a schema-3 report prints byte for byte as today, pinned): the residue table's R1 row reads `R1 recogniser (silent only; marked R1 reported below)` with its ceiling where the row reports, else as today; immediately after the `- R1: …` members line (`:3603`) one new line on EVERY schema-4 row — `- R1 marked wrong (reported, no ceiling): n — members` where the row reports, `- R1 marked wrong (counted under the ceiling): n — members` where it does not — so predictions v5 for the seen sets carry the split the report prints; `_fact_classes` still prints `R1` for both kinds.
- **The fourth verdict.** `PassRule.counting_marked_r1()` returns a copy with every row's `r1_marked_reported` False (row-wise `model_copy`; `self` when no row reports, the `without_r1_exemption` shape). The heading and `_verdict_lines` print FOUR verdicts on the same outcomes: `rule v5`; `rule <label> with marked R1 counted` — the name from `PassRule.label` like every other verdict line (`:3217`, `:3234`, `:3290`: "v5" for `rule-v5.json`; `vN` or `v<schema>` for another schema-4 name — peer round 2 PR-LOW-002, pinned on a schema-4 rule named `rule-v6-test`), the heading prints NO "= rule v4's verdict" claim (peer round 1 PR-MED-002: the loader admits any schema-4 thresholds and rows, for which the claim would be false — one marked R1 fact under a custom ceiling of 0 fails where rule v4's 2 passes); for `rule-v5.json` the equality holds by C18, is pinned equal to `run_passed(rule_v4_from_file, …)` on invented outcomes and to verdict 1 on the five seen rows, and is STATED in the harness document's Rule v5 section, never printed; `rule v5 without the R1 exemption` (marked R1 still reported; `rule_v2_counterpart` compares `r1_marked_reported` with `False` and `None` as equal (both neutralised to `None`) and a `True` row as a substantive difference → `differs` (PR-MED-002; pinned both ways on a hand-built schema-4 rule — `True` on `scripts` → `differs`), so rule v5's four v2 sets read `= rule v2's verdict on this set` and `heldout-4` / `heldout-5` read `no_row`); `rule v1`.
- **The amendments paragraph:** rule v3's history prints for `schema_version >= 3`; rule v4's schedule sentence for `label == "v4" or schema_version >= 4` (history); one appended sentence for `label == "v5"`: rule v5 (schema 4; validation-run8 D1, decided 2026-11-06) keeps rule v4's predicates and ceilings, and on a row that reports marked R1 counts only the silent R1 facts under the R1 ceiling, printing the marked ones beside it; the verdict with marked R1 counted is printed beside it. The excused-lines line's gate (`:3614`) becomes `>= 3`. The strings "schema-2 or schema-3" (`--set` help `:3785-3786`, `main`'s docstring `:3850`, the refusal `:3905`) read "schema 2 or later"; `:3911`'s f-string prints "schema-4" unchanged.
- **Loosening (6), disclosed plainly:** on the blind row a misheard material fact under a review mark no longer fails the R1 ceiling at any count. **This IS a loosening decided after run 7 failed on exactly this class** — the third such cycle (rule v2 after run 5, rule v3 after run 6, rule v5 after run 7). It is kept honest by: fixed before predictions v5 and before the blind set exists (C16); the earlier reading printed beside it (the fourth verdict); every count reported and every marked fact a register row; the class controlled by the review guide (D2) and the band rule (D7); the larger-model answer the earlier sentences pointed to measured and no better (F-148). Constraint 12's "nothing is tuned after a run" stays true in its narrow sense — a rule that has been run is never edited — and the override lines say that sense explicitly. Listed with (1)–(5) in `validation-harness.md`'s "Rule v5" section (which also names the three-cycle pattern) and as DATED OVERRIDE LINES in the practitioner's words ("Rule v5: report marked misheard facts (Recommended)", 2026-11-06) at every standing sentence: `plan-pilot.md` Constraint 12 (`:219`) and the stop rule's "the rule is not changed to make it pass" (`:1941`); `validation-harness.md:237`; `plan-larger-model.md:730`. **Honest limit, re-stated:** the worst case is a wrong dose under `[check: number]`, a mark every quoted number carries, possibly on another word of the line.
- **Every marked R1 fact on any set is a register row** (`controlled`; category `wrong-dose` for a dose fact, `quality` otherwise; the control: the mark and the clinician's check of every marked number, unit and abbreviation; never `resolved` by a run). Run 7's five already have rows (F-071/F-072 `syn-28`; F-102 `hld-07`; F-130 `h3-03` — the excused-line row is its row, re-worded to rule v5; F-141 `h4-01`; F-142 `h4-07`); F-087 (`syn-22`) is the R1-silent exemplar.
- **Alternatives rejected:** `heldout-5` at `max_r1_facts 2` or any integer or rate (fitted); reporting all of R1 (un-gates the silent kind); a rule-level field (cannot say "blind row only"); a nullable `max_r1_facts` (the R2 pattern; un-gates silent R1 too); rule v4 unchanged (not chosen).

### D2 — The clinician review guide: the control in plain words, with the measured counts (dated 2026-11, awaiting the practitioner's approval at P.2)
Plain English, no file names or identifiers beyond the app's own screen words, no promise the app cannot keep (`docs/practice/README.md:68-72`); dated clauses in the guide's header (`:8-18`) and the README's header (`:9-20`) — without a version ("after validation run 7 and the larger-model measurement, 2026-11") — and a second bullet in the README's findings list (`:77-89`, the 2026-10 finding's shape). Both files CRLF.
- **"Reading the transcript":** the speech software can mishear a number, a unit (milligrams, weeks) or an abbreviation said letter by letter and write a different one. In the program's own testing (139 invented consultations read aloud by computer voices in a quiet room) 7 facts came out wrong: for 5 the line carried a mark — `[word?]` on a word, or the line marked `[check: number]`, `[check: unsure]` or `[check: possibly not speech]` — and 2 carried no mark at all. Real speech, accents and background noise were not measured, so the true rate may be higher. A larger speech model was measured and did no better, so these marks and your reading are the control. A mark does not point at the wrong word: `[check: number]` is on every quoted number, and a `[word?]` may be on another word of the same line. Read every number, unit and abbreviation against what you remember, marked or not. (The counts re-read from run 7's reports at Task 1.1 and refreshed with run 8's at P.2.)
- **Step 4 (Marked lines):** "a misheard number, unit or abbreviation is the known class; check each marked line against the transcript AND against what you remember, because the transcript can be wrong too".
- **"A shadow recording":** once shadow mode is turned off (after a validation run passes), Write and Copy work, and your review is the only check between the app's draft and your Cliniko draft note — the checks above are what the testing relied on.
- Not written: "a `[word?]` on a short word in capitals is most likely an abbreviation" (an inference the app does not make); "every misheard word is marked" (2 of 7 were not).

### D3 — The gate for run 8
A rule v5 PASS on the 50 (fitted; regression evidence) and on the blind `heldout-5`; `heldout`, `heldout-2`, `heldout-3`, `heldout-4` built, run and reported in full. A `heldout-5` pass is reported with its qualifiers — patient facts routed by rule; the author model, for R3 AND R1 — and with the marked-R1 count and the band rule's reading beside it.

### D4 — `heldout-5`: pre-registered first, the same isolated author, blind (larger-model D6 carried)
- **Brief** = `validation/heldout-4/SPEC.md` (LF) with exactly four lines changed — line 1 (set 5, this plan, Task 0.5, the date), lines 5, 56 and 65 (`h4` → `h5`) — by the leak-check copy `run8-brief-leak.py`, whose `LISTS` gain the primer's terms (`transcription.CLINICAL_INITIAL_PROMPT` split on `.` and `,`, vocabulary only; 0 hits expected) beside the closings, greetings, correction markers and both hedge lists; output `.cursor/loops/heldout-5-brief/`; the refusal names `validation/heldout-5`; the asserts read `"h5"` / `"set 5"` / `h5-01.json`.
- **Author:** the same isolated `claude -p` invocation (`--restricted --safe-mode --strict-mcp-config --disallowedTools WebSearch Agent --permission-mode acceptEdits --model claude-opus-5-5`; preflighted with a throwaway call), launched by the practitioner from `validation-run8-heldout5-author-run.sh` in a NEW empty folder outside the repository (never `C:\heldout4-author\`, which still holds run 7's content); `author-session.jsonl` kept with the user name redacted; `AUTHOR-NOTES.md` read only at P.3; the `h5-` rows of `REFERENCE_TAIL_STARTS` by `validation-run8-heldout5-tails.py` (`SET` `heldout-5`, glob `h5-*.json`, anchor `'    "h4-21": None,\n}\n'`, assert `'"h5-' not in text`).
- **Pre-registration (Task 0.4), committed BEFORE the author runs.** Falsifiers that fail the gate: R1 silent > 1 fact; a silently omitted material fact after R1 (expected 0); a material fact `wrong` without a review mark (0–2); R3 > 1 encounter (0–2); a wrongly present material fact outside R3 (0); an unsupported clinical line not excused (0–1); a checker failure (0). Bands, reported — outside one is a finding, never a rule edit: **marked R1 0–3 facts, with the band rule (D7)**; the `clinician_line_omitted` load median 0–2 / maximum ≤ 5; surfaced doubt 15–40%; reference-boundary mismatches 0–6; boundaries found of role tails 20–80%; false cuts 0–1; R2 any count; **author overlap** — the count of `h5-` material-fact statements whose canonical token sequence appears in any seen set's facts, any value reported; COMPUTED AT P.3, not before (peer round 1 PR-MED-004: the computation reads the statements' tokens, so it waits for the blind rule's end; a count-only script whose output is one integer); P.1 records this band "pending P.3".
- **Blind (C12):** from the set commit until P.3 the desktop suite runs ONLY through `scripts\lint-held-out-set.py validation\heldout-5` (the conftest refuses a bare run); Task 0.5 adds the file-name-only presence pin, removed at P.3.

### D5 — Predictions v5 = run 7's reports re-read by the harness's own functions, frozen (no re-transcription before run 8)
- Nothing that touches decoding or routing lands in this plan (C17), and `medium` reproduced run 7's five reports line for line on 2026-11-05 at `170345d`, so the seen sets' rule-v5 lines are derived from `.cursor/loops/run7-reports/` by a NEW scratch `.cursor/loops/run8-predict.py` (not `run7-predict.py`): it parses the five reports (decode `utf-8-sig`) into outcome objects sufficient for `class_counts`, `_verdict_lines` and `_residue_section`, asserts it reproduces run 7's rule-v3 verdict lines and residue section byte for byte, then prints rule v5's — ids, counts and verdicts only.
- **The per-fact rule, exact (peer round 1 PR-MED-001):** an R1 member with Verdict `wrong` and Ambiguous `no` is marked; Verdict `omitted` is silent; an R1 member with Verdict `wrong` and Ambiguous `yes` is NOT resolvable from the report — the encounter table's "Silent omissions" column sums every fact of the encounter (`validation.py:1052`) and the Facts table prints `ambiguous` but not `silently_omitted_somewhere` (`:3519-3531`) — so the scratch REFUSES on such a member (exit 2, its id printed) instead of inferring, and that set's predictions would then need the harness itself re-run on the set's pickled outcomes under rule v5 (none expected). Run 7: `syn-28/f1`, `hld-07/f0`, `h3-03/f0`, `h4-01/f5`, `h4-07/f0` are `wrong` / Ambiguous `no`; `syn-22/f2` is `omitted`, Warned `no` — all six unambiguous, so the refusal is not expected to fire; the scratch asserts exactly these six members by id before it prints anything.
- **Frozen on Task 0.3 and committed before the pre-registration:** per seen set the four verdicts, every failing id and reason, every residue member with R1's split, the after-class and excused counts, surfaced / expected, the load's total / median / maximum, Check 6 per axis script.
- **The lines that legitimately differ from run 7's reports, listed in full:** the run-information line; the heading's rule label and verdict list (four, not three); verdict line 1's label, gate / reported set lists and `heldout-4`'s role (`:3234-3240`, `:3216`); the second verdict line (new); the third verdict line's label; the amendments paragraph; the residue heading's label AND `heldout-4`'s role (`:3580-3582`); the after-classes line's label (`:3608`); the R1 table row's name where a row reports; the new marked-R1 line. The excused-lines line, the encounter table's cells and the Facts table do not differ. Any other difference at run 8 is a finding read before anything else. The 2026-11-05 `medium` rule-v4 reports in `.cursor/loops/run8-reports/medium/` corroborate the derivation (they differ from run 7's by the label and gate lines only) and are never a source of record.

### D6 — What stays frozen
`medium`; the primer; the guard's constants and `UNCERTAINTY_THRESHOLD`; `CLOSING_PHRASES` / `GREETING_PHRASES` / the hedges / the markers; rule v1's file (`option-a-proposed.json`), `rule-v2.json`, `rule-v3.json`, `rule-v4.json`, `validation/config`, every seen script's facts (C2); the metric amendments; the attribution policy; `test_shadow_exits.py`'s counters (no app code).

### D7 — Shadow off: the stop rule, the band rule, the acceptance, the register, the sequence
- **Rule v5 is the rule in force for run 8** — a dated decision before the run (D1's override lines). The exit gate's "Validation passed" line cites the rule the harness document names, with a rule-v3 parenthetical approved 2026-11-04, so a rule-v5 reading is a dated PROPOSAL on `docs/pilot/exit-gate.md`, approved at P.2, never a quiet edit (7-char commits only there).
- **The band rule (the practitioner 2026-11-06: "Yes: above the band → keep shadow on (Recommended)"), fixed in the pre-registration commit and the Rule v5 section:** a marked-R1 count on `heldout-5` above 3 makes the RECOMMENDED P.5 option "keep shadow on" and triggers the distinct-mark plan (Deferred); 0–3 makes "off" the recommended option. A decision rule for the recommendation, never a gate; the practitioner decides either way.
- **If run 8 PASSES:** P.2 puts P.5's question as a dated decision on `plan-pilot.md` with the band rule's reading first and the acceptance in plain words for EVERY class the shadow-controlled register rows hold — misheard facts under a mark (the mark and the clinician's reading of every marked number, unit and abbreviation); doubt in words outside the frozen list (the clinician's own judgement of what the patient was sure of); patient lines no cue routes (an incomplete note, never a wrong one; the clinician reads the transcript); a next patient greeted in other words (the end of every transcript checked); the two confident unmarked errors of `heldout` (the transcript read against memory) — with the marked-R1 count on `heldout-5`, the validated-commit sentence (Accepted Assumptions) and the allowances a rule-v5 PASS keeps (PR-MED-003: up to one silent R1 fact and one R3 encounter on the blind set; uncertainty reported, not gated, there; R2 at any count) stated as part of the acceptance. **On "off", in the same P.2 commit (the practitioner 2026-11-06: "Yes, one commit at shadow-off (Recommended)"):** every `controlled` row whose control opens "Shadow mode on for every recording" (64 at planning) is re-worded to its class's review-guide control within `test_pilot_docs.py`'s rules (≤200 chars, no quotes, no id shape; `Closed` month unchanged — the control changes, the finding does not close); `docs/pilot/README.md:128-134` (the per-consultation tick) reads the same way. **Then (P.4′):** the practitioner leaves "Shadow mode (pilot)" UNTICKED on the installed 0.3.5's Status tab from the first REVIEWED consultation, which starts only after the pilot's P.4 tenth eligible shadow score and its one commit (Task 9.1's table; fewer than five of ten at planning, 2026-11-06) — the exit gate's order (`exit-gate.md:5-8`). The month is recorded on P.5 (C8). No build, no install: the mode is fixed at Start per recording (`session_mode.py`).
- **If run 8 FAILS:** a recorded finding, P.5 stays (a), the register rows keep their shadow control; the next plan by the class (Follow-Up Continuation Notes). A marked R1 fact cannot fail the R1 CEILING under rule v5; two residual paths can still fail its encounter and are kept as falsifiers (D4): an unsupported clinical line `_excused_by_r1` does not excuse (the flagged word itself unmarked, or an inserted word) and a checker failure a misheard dose or side raises. A failure on R1 silent or on a confident error without a mark is the recogniser WITHOUT a mark — the low-confidence threshold's territory, a new dated decision with the measurement repeated, not this plan.

### D8 — Documents (Phase 1), every claim checked against the code before the peer pass
`docs/testing/validation-harness.md` (CRLF): the policy lines `:42-47, :55, :70, :77, :126` ("schema 2 or later"); a NEW H2 `## Rule v5` between `## Rule v3` (`:161`) and `## Runs of record` (`:187`) — rule v4 has no H2 and `TestHarnessDocument` splits on the v3 heading — with the six-row ceiling table pinned equal to the file, the split, the fourth verdict, loosening (6) with the three-cycle sentence, the band rule, the pre-registration once committed; `:183-185`'s excluded-lines sentence extended per D5; the override line at `:237`; run 8's placeholder under "Runs of record" (`:247`'s "no run 8" is history, superseded by a dated line, not edited). `validation/README.md` (CRLF): the rules bullet; the `heldout-5` entry to the authored state at Task 0.5. `docs/pilot/README.md:115-120` (the rule-v5 paragraph replaces the rule-v4 one). `docs/pilot/findings-register.md:37-38` (`h5-NN` rows "entered after run 8"). `docs/pilot/exit-gate.md` (the dated rule-v5 proposal; approved text at P.2). `docs/security/threat-model.md:4054-4061` (four verdicts under schema 4; the marked-R1 residue named) and `docs/security/data-flow-map.md:1289, :1314` (schema 4). `scripts/README.md:92-94, :146-147, :160-161` and `scripts/run-validation.py:13-16` (rule v5, six sets; the docstring only — C17). Stale cites of the larger-model plan's dropped Tasks 0.11 / P.4 re-cited to this plan's 0.5 / P.3 (comments only): `scripts/lint-held-out-set.py:4-9`; `desktop/tests/fixtures/heldout_transcripts.py:75-80, :944-945, :1011-1012`; `desktop/tests/test_lint_held_out_set.py:456-459`; `desktop/tests/test_validation_scripts.py:24-25, :653-656, :733`; `desktop/tests/test_consultation_boundary.py:162-163`; `desktop/tests/test_note_check.py:2758-2759`; `desktop/tests/test_note.py:3349-3350`; `.github/workflows/ci.yml:68-73` (the step unchanged). `docs/practice/clinician-review-guide.md` and `docs/practice/README.md` (D2). `.cursor/plans/plan-pilot.md`: Constraint 12 (`:219`) and the stop rule (`:1941`) override lines; P.5's dated line (`:1985` is history) — line-anchored byte edits. `.cursor/plans/plan-larger-model.md:723` (a dated "taken over by `plan-validation-run8.md`" line) and `:730` (the override line). `AGENTS.md` (CRLF): Current Status (replaced; "no run 8" at `:109, :112, :115` superseded), Last Session, the harness pointer ("rule v5"), step 12 `:53` ("under the ratified rule v1" → the rule in force). `CHANGELOG.md` (CRLF): Unreleased (`:16-17`'s "no run 8" is history). No change to `docs/release/pilot-builds.md` (no build).

## Schema / Data Changes
None in the app. The harness's pass-rule schema gains version 4 (D1); a schema-1, -2 or -3 file still reads unchanged; a 0.3.5 harness refuses a schema-4 file by its `Literal[1, 2, 3]`. `heldout-5`'s scripts are script schema 1.

## Config / Environment / Deployment Impact
- No environment variable; no runtime network; no build, no pack, no install; the installed 0.3.5 is unchanged — shadow off is its Status-tab tick (D7).
- CI: the held-out step's fallback branch goes dead (harmless) once `validation/heldout-5` exists; the suite runs through the runner from Task 0.5 to P.3.
- Disk: six set folders outside the repository for run 8 (synthetic only, deleted after; `heldout-5`'s kept until P.3 is committed).

## Critical Constraints
1. **C1 — The agent never opens, reads, plays or describes any real session, kept recording, transcript, note or Past-sessions entry.** Synthetic sets, ids and counts only; the register and every record content-free.
2. **C2 — Rule v1–v4's files, `validation/config`, and the facts of every seen script never change.** Rule v5 is a NEW file (Task 0.2a); a bad number after a run is a finding (pilot Constraint 12).
3. **C3 — Vocabulary, hedges and markers frozen** (D6; the practitioner's phrases deferred).
4. **C8 — Nothing per consultation enters a tracked file** (clinic-smoke D12): run records are ids and counts; the shadow-score count is an aggregate; the shadow-off month, never the day.
5. **C9 — One `/execute-loop` at a time on `main`; isolation none.**
6. **C10 — Practitioner-run steps run from a normal terminal with the installed app closed; the run of record is NEVER agent-run** (`validation-harness.md:33`; the 2026-11-05 agent-run measurement is recorded as not a run of record). Record scripts assert `"\x00" not in text` and no bare `\r`; CRLF files (Codebase Integration Notes; re-read from `git ls-files --eol` at each document task) are edited byte-level keeping CRLF; `plan-pilot.md` by line-anchored byte edits.
7. **C11 — `test_shadow_exits.py`'s counters are unchanged** (no app code).
8. **C12 — `heldout-5`'s CONTENT is examined by no one before P.3** (peer round 2 PR-LOW-003 wording). Before P.3 the set is read only by machines that print no statement: the lints through the runner, the tail script (parses the scripts in process, prints ids and integers — run 7's Task 0.8 reading), the file-name-only presence pin (`script_paths()`), and P.1's builder and harness, whose report prints verdicts, ids and classes, never a script's words; the practitioner's P.1 reading of that report is content-free. The author-overlap count (D4) and every examination of a script's words — the diagnosis — are P.3.
9. **C13 — No cloud sessions.** The register content-free (`test_pilot_docs.py`); hashes never in `docs/pilot/`.
10. **C14 — The harness's attribution policy is unchanged.**
11. **C16 — D1's predicate and rule v5's rows are fixed in this plan's commit and in Task 0.2a's commit BEFORE predictions v5 (0.3), BEFORE the pre-registration (0.4) and BEFORE any `h5-` script exists (0.5); the band rule is fixed in 0.4's commit; a run never edits any of them.**
12. **C17 — Nothing that touches decoding or routing lands between Task 0.3 and run 8.** Checked at every commit with the C17 BASE `170345d` (Task 0.0 decided A on 2026-11-06; under option B it would have been the commit Task 0.0 recorded, for (a), (b) and (c) alike — PR-HIGH-002), as: (a) `git log 170345d..HEAD --stat -- desktop/src validation/config validation/scripts scripts/build-validation-set.py ':(exclude)desktop/src/scribe_desktop/validation.py'` empty; (b) `git diff 170345d..HEAD -- desktop/src/scribe_desktop/validation.py` read and recorded on the task as confined to `SetCeilings` / `PassRule` / `_check_sets` / `counting_marked_r1` / `rule_v2_counterpart`, the two `FactOutcome` properties, `ClassCount` / `class_counts`, `_verdict_lines` / the heading / the amendments / `_residue_section`, the `_parser` and `main` strings, and the `h5-` rows of `REFERENCE_TAIL_STARTS` — never `evaluate_encounter`, the alignment, `_FactState`, the reference reading, the metric amendments or `UNCERTAINTY_THRESHOLD`; (c) `scripts/run-validation.py`'s diff docstring-only.
13. **C18 — Rule v5 un-gates ONE class, the marked misheard material fact, and only on the blind row**; every other predicate, ceiling and the 50's row are rule v4's — pinned by a test comparing rule v5's file to rule v4's field by field with `r1_marked_reported` excluded on both sides (rule v4's rows hold `None`).

## Validation / Verification
**Suites.** `desktop/`: `ruff check . && mypy && pytest` — plain through Task 0.4, then ONLY through `scripts\lint-held-out-set.py validation\heldout-5` until P.3 (C12; CI's step already does this). No extension change.

**Read-only baselines** (re-probed 2026-11-06 at `4d6f7a1`, tree clean):

| Check | Baseline | Becomes |
|---|---|---|
| `RULE_SCHEMA_VERSION` / `PassRule.schema_version` / refused schema (`test_validation_metrics.py:3121`) | 3 / `Literal[1, 2, 3]` / 4 | 4 / `Literal[1, 2, 3, 4]` / 5 |
| Rule files | four (`option-a-proposed`, v2, v3, v4 — six rows, `heldout-5` gate) | + `rule-v5.json` (six rows; `r1_marked_reported` true on `heldout-5` only) |
| `ClassCount` fields | 4 | 5 (`reported_members`, defaulted) |
| Verdicts a report prints | 3 (schema 3) | 4 (schema 4); 3 unchanged (schema 3) |
| `test_lint_held_out_set.py:460` blind pin | `["heldout-5"]` | unchanged until P.3 (`[]`) |
| `HELDOUT_5_CASES` / the fixture row | `()` / `cases_written=False` | unchanged until P.3 |
| `validation/heldout-5/` | absent | 20–25 `h5-` scripts (Task 0.5) |
| `REFERENCE_TAIL_STARTS` rows | through `"h4-21"` | + the `h5-` axis rows |
| Decode-path log since the C17 base `170345d` (Task 0.0: A; C17 (a)) | empty | empty |
| `.cursor/loops/run7-reports/` | five reports (BOM) | unchanged |
| Shadow-controlled register rows | 64 of 65 `controlled` | re-worded at P.2 only if P.5 is decided off |
| CRLF files | `AGENTS.md`, `CHANGELOG.md`, `validation-harness.md`, `clinician-review-guide.md`, `docs/practice/README.md`, `scripts/README.md`, `validation/README.md` | unchanged |

**Per-phase checks.** Every new predicate pinned both ways; every ceiling at n and n + 1; the both-case precedence; rule v3's and rule v4's reports byte-unchanged on invented outcomes (the existing whole-report pins, plus the mirror pin "no `v5`, no marked-R1 line" in the rule-v4 report); a whole `heldout-5` report on invented outcomes, every line; the fourth verdict equal to the real rule-v4 file's verdict; `rule_v2_counterpart` on every rule-v5 row; C18's field-by-field equality; the document's rule-v5 table equal to the file; Task 0.3's scratch reproducing run 7's lines byte for byte before it prints rule v5's.

**Acceptance:** Task 0.0 decided before 0.2a; rule v5 committed before predictions v5, before the pre-registration and before any `h5-` script exists; the band rule in the pre-registration commit; `heldout-5`'s content examined by no one before P.3 (C12's permitted machine reads only — peer round 3 PR-LOW-004); run 8 practitioner-run from a clean checkout; the gate = a rule v5 PASS on the 50 and `heldout-5`; the P.5 question put as a dated decision with the band rule's reading and the acceptance per class, whether the run passes or fails; on "off", the register's shadow controls re-worded in the same commit.

## Deferred / Out of Scope
See the Planning Extraction Summary (Deferred, Excluded, Accepted). In short: the distinct mark for a low-confidence number (deferred with the band-rule trigger), the practitioner's phrases, the two install-smoke items (deferred to the next build); a fitted ceiling, reporting all of R1, rule v4 unchanged, a sealed `heldout-6`, any decode or model change (excluded); the four validation-pass items (owned there).

## Current State / Handoff Note
- **COMPOSER RUN-STATE (2026-11-06 21:55, PAUSED at Phase P — MUST-PAUSE `run8-p1`: the practitioner runs P.1, run 8; the earlier `heldout5-author-launch` was answered by the practitioner's launch, EXIT:0):** `/execute-loop` run iso `validation-run8-20261106-144633-d8ae` (ownership marker `.cursor/loops/validation-run8-20261106-144633-d8ae-active`, isolation none, builds on `main` from `9884f04`), composer = Claude Code desktop session `local_325ca34f`'s side session; started at Task 0.2a. Commits so far: Task 0.2a `ba71ff5`; Task 0.2b `d15a28f`; Task 0.3 `431a38e`; Task 0.4 (THE pre-registration) `edd1a7d`; Task 0.5's preparation `4e0d550`; Task 0.5 itself (the authored set, `edd1a7d` carried) `2228b25`; Phase 1 (Tasks 1.1 and 1.2) `60d553d`; the hardening stage (H1–H4) the commit after it — THE H4 commit P.1 runs from. Stage-5's prep converged: `/review-loop` round 14 (1 LOW), codex peer rounds 15 (1 LOW, record-only, fixed) and 16 (0 findings). The composer created `C:\heldout5-author` holding the regenerated `SPEC.md` alone (SHA-256 `819be450…994f54` re-checked after the copy); the practitioner launched the author (EXIT:0, `DONE 22`); the set copied in unread; stage-5 closed. Stage-6 (Phase 1) closed: `/review-loop` round 17, codex peer round 18 (0 findings). Stage-7 (H1–H4) closed: rounds 19–21, codex H4 rounds 22–30 (converged: documents at 29, code at 30). Next: Phase P, practitioner-owned — the loop is paused. Stage map: stage-1 = Task 0.2a, stage-2 = 0.2b, stage-3 = 0.3, stage-4 = 0.4, stage-5 = 0.5 up to the practitioner's author launch, stage-6 = Phase 1, stage-7 = H1–H4. Helpers `.cursor/loops/vr8-spawn.sh` / `vr8-peer-run.sh`; policy log `.cursor/loops/validation-run8-20261106-144633-d8ae-policy.log` (high-auto `816c39ef6949`, gates `3aac04e88393`).
- Loop config: executor=claude-p model="claude-opus-5-5" effort=high profile=default; peer=codex model="gpt-6-astra" effort=medium; architect=off; cadence=every-phase; caps=review:3,peer:5; gates=executor; cap-raise=executor; high-auto=on; peer-max=12; notify=action-only; scope=all; autocommit=on; isolation=none; merge=off; perms=scoped; liveness=10; monitor-delivery=auto; verify=composer
- **2026-11-07T10:23:43+11:00 — stage-7 executor (leg px5), the fifth register row WRITTEN; the suite through the runner owed (composer).** Operator brief:
  - **The practitioner's answer** (2026-11-07): "Add the fifth row (Recommended)" — F-153: `h5-10`, high, cross-patient, note-routing, controlled by shadow mode, like F-132. Quoted on P.2.
  - **Done** (documents and the plans only): F-153 in `docs/pilot/findings-register.md`, with F-132's control text (under 200 characters, unquoted, id-free; Found and Closed 2026-11). Run 8's rows are now five, F-149–F-153, in P.2's record, `plan-pilot.md`'s register-after-run-8 line, `CHANGELOG.md` and `AGENTS.md`. The px4 bullet's open question is marked answered. CRLF kept in `AGENTS.md` and `CHANGELOG.md`.
  - **Composer results since px4:** `test_pilot_docs.py` over px4's register, 11 passed.
  - **Next (composer):**
    1. Run `test_pilot_docs.py` and the full suite through the runner.
    2. Make the P.3 and P.2 commits on the practitioner's word.
    3. Run `/document` and close the loop.
    4. Start the next plan (Plan Mode, with Fable), Follow-Up Continuation Notes 1.
- **2026-11-07T09:30:47+11:00 — stage-7 executor (leg px4), P.2 RECORDED (🟩, Chosen: keep shadow on); Phase P done but the P.3 and P.2 commits; the suite through the runner owed (composer).** Operator brief:
  - **The practitioner's answers** (2026-11-07, each the recommended option): register "(a) One row each"; review guide "Approve; hold shadow-off"; exit gate "Leave as a proposal". Quoted in full on P.2.
  - **Done** (documents and the plans only; no code, test, fixture, rule file or CI change):
    - the register: F-149–F-152 and F-130's re-wording;
    - the review guide's draft-history clause and counts (161 / 9 / 6 / 3);
    - the practice README's counts and approval status;
    - `plan-pilot.md`'s register-after-run-8 line;
    - `AGENTS.md`, `CHANGELOG.md`;
    - this plan: P.2, P.3's suite, P.4′ dropped, Overall Progress.
    - `docs/pilot/exit-gate.md` is unchanged (the proposal stays). Its proposal still says "a draft for the practitioner's approval at that plan's Task P.2". It was left as written, because P.2 chose to keep it a proposal and the brief said to leave the file alone.
  - **Not a MUST-PAUSE:** nothing fixed (C16) was touched, and no row needed a test change. The register cells match `test_pilot_docs.py`'s closed vocabularies (read, not run).
  - **Open for the composer (not asked; `rec=`):** `h5-10`, R3 at its ceiling, is a next patient's fact that reached a note — a `cross-patient` class. The register's Severity rule makes any `cross-patient` finding high. The answer's four rows do not name it. `[2026-11-07T10:23:43+11:00, leg px5]` ANSWERED by the practitioner: "Add the fifth row (Recommended)" — F-153.
    - Options: (a) add a fifth row (`h5-10`, high, cross-patient, note-routing, controlled, as F-132 for `h3-17`); (b) leave it on P.3's record only.
    - `rec=a`: the register's rule is "every finding of the pilot", and the answer's form ("one row each") reads as one row per class finding.
    - Ask the practitioner before the commit.
  - **Constraints:** C1 held. `.cursor/loops/held-out-lint/` and `.cursor/loops/run8-reports/` were not opened. CRLF kept: `AGENTS.md`, `CHANGELOG.md` and both practice files have the same `\r` and line counts.
  - **Custody (after the commits):** `C:\run8\`, `C:\run8-p3\`, `.cursor/loops/run8-p3/` and `.cursor/loops/held-out-lint/` may be deleted; P.1's earlier cleanup items stay owed.
  - **Next (composer):**
    1. Run the suite through the runner.
    2. Ask the practitioner the `h5-10` question.
    3. Make the P.3 and P.2 commits on the practitioner's word.
    4. Run `/document` and close the loop.
    5. Start the next plan (Plan Mode, with Fable), Follow-Up Continuation Notes 1.
- **2026-11-07T09:13:38+11:00 — stage-7 executor (leg px3), P.3's transcript-dependent classes SETTLED (P.3 stays 🟨); records only; the suite (composer, running) and the commit owed.** Operator brief:
  - **Read:** the dumps the composer copied byte for byte to `.cursor/loops/run8-p3/heldout-5/` (`h5-01`, `-02`, `-04`, `-07`, `-08`, `-12`, `-13`, `-17`, `-19`, `-20`, `-22`) and `report-rule-v5.md`; `h5-12`'s script for its line count. Synthetic encounters only.
  - **`h5-17/f0`: (i), the recogniser's.** Segment 9 (speaker_2, quoted) drops the fact's fifth word, the body part; the side ("right") was heard right; no word aligned to the fact carries a mark (the one nearby `{u}`, 0.47, is on the next word). Not split, so (ii) is not taken. Its misrendered word's class is other, not side.
  - **`h5-01/f4`: an abbreviation** (`A &E`, a word lost), under the line's number mark from the number of the same fact, heard right.
  - **Re-checked against the dumps:** R2's seven (four hedges outside the list, joined at a comma or inside the segment; three doubts in segments of their own) and surfaced 1 / 11 (`h5-20/f1` by a 0.12 `{u}` on its number) stand. `h5-12`: 17 joined clinician runs, four of them the missed next patient's; no comma split or bare cut adds to the six. Which runs drew the six is not in the dump, so the split-line share stays uncounted (finding 4).
  - **Report equality:** confirmed by this leg's own read of the verdict, residue, load and Facts lines (the composer's diff found only the progress lines, one blank line and the commit).
  - **The overlap:** 10, recorded on P.3 and in the harness document with the script's definition; "contiguously inside" is named as the script's reading of D4's "appears in".
  - **Written** (uncommitted): P.3's record (dated px3 lines; findings item 1 now Follow-Up Continuation Notes 1, the recogniser without a mark — the threshold and the mark's reach, a new dated decision with the measurements repeated; never a rule change); the harness document's run-8 diagnosis sub-bullets (CRLF); `plan-pilot.md`'s P.3 line; `AGENTS.md`'s P.3 bullet (CRLF). `validation/README.md` unchanged (nothing it says moved). No test, fixture or CI change; no class needed one, so no MUST-PAUSE.
  - **Constraints:** C1 held. C16: nothing fixed was edited — the finding points to the next plan. `.cursor/loops/held-out-lint/` and `.cursor/loops/run8-reports/` not opened; nothing under `.cursor/loops/` edited.
  - **Open P.2 questions (recorded, not asked; each `rec=`), refreshing px2's:**
    1. **The register rows.** Options (a) and (b) as px2's. `rec=a`, with `h5-17/f0`'s row now the recogniser's (category `quality`; control: the review guide's reading of every material line, shadow mode on; the threshold and mark-reach question for the next plan), and `h5-01/f4`'s a `controlled` abbreviation row under D1's category rule.
    2. **The review guide's lines.** `rec=approve the misheard-word lines with run 8's counts refreshed` — `h5-01/f4` is an abbreviation under a mark on another word of its line, which the guide's "may be on another word of the same line" already covers, and `h5-17/f0` is a word lost with no mark on it, which its "carried no mark at all" covers; `rec=hold the shadow-mode-off line` (shadow stays on, D7).
    3. **The exit gate's rule-v5 proposal.** `rec=leave as a proposal` (no run has passed under it).
  - **Custody:** as px2's bullet; add `.cursor/loops/run8-p3/` (the copied dumps) to what may go after P.3's commit.
  - **Next (composer):** the suite plain and through the runner; then P.3's commit on the practitioner's word; then P.2's three questions.
- **2026-11-07T09:05:48+11:00 — stage-7 executor (leg px2), P.3 the `heldout-5` diagnosis WRITTEN (🟨); the overlap run and the suite are owed (composer).** Operator brief:
  - **The practitioner's answer** (2026-11-07): "Keep shadow on (Recommended), start P.3". Recorded on `plan-pilot.md` P.5 (a dated DECISION line) and on P.2 here, with "register, approvals pending". Nothing else was recorded as decided.
  - **Done:** the 22 cases; the divergence entries (boundary 5, corrections 0, unsure 10) and their count pins; rule 4 over `heldout-5`; the blind pins at `[]` and the presence test removed; CI's comments; `validation/README.md`, the fixture's docstring, the harness document's diagnosis sub-bullets, `plan-pilot.md` (the P.5 decision and the P.3 diagnosis line) and `AGENTS.md` (CRLF kept); the count-only `.cursor/loops/run8-p3-overlap.py`. Run 7's P.4 commit had no `CHANGELOG.md` line, so this leg adds none. The full record is on P.3.
  - **Not read: `C:\run8-p3\` was refused** (no permission outside the working directory, as run 7's `C:\run7-p4` was). So the composer's `report-rule-v5.md` is NOT confirmed equal to run 8's report here, and `h5-17/f0`'s WHERE is narrowed but not decided. Ruled out: (iii), the script or reference reading. Left: (i), the recogniser dropped a word or misheard one outside every quoted line, with no mark; or (ii), the fact split across a quoted and an unquoted segment. The P.3 record names exactly what in `h5-17.txt` decides it.
  - **Not a MUST-PAUSE:** the class is a P.3 finding, not a decision on a fixed record, and nothing in C16 or C17 was touched (no product code, rule file or script fact).
  - **Constraints:** C1 held (nothing under `%LOCALAPPDATA%`, no real session). `.cursor/loops/held-out-lint/` and `.cursor/loops/run8-reports/` not opened. No product code, rule file, script fact or version field changed.
  - **Open P.2 questions (recorded, not asked; each `rec=`):**
    1. **The register rows, now that the classes are known.** Options:
       - (a) one `controlled` row each — `h5-17/f0` (the failure, category by its side class, `quality` until the transcript decides (i) or (ii)), `h5-01/f4` (marked R1, D1's category rule), the seven R2 facts, the two bare modals, `h5-10` (R3, the missed next patient), and the two out-of-band readings (the load maximum, surfaced doubt);
       - (b) as (a) without the two band readings, which stay on P.3's record only.
       `rec=a`: the pre-registration says outside a band "is a finding", and run 7's P.4 entered its bare-modal fact as a row.
    2. **The review guide's misheard number / unit / abbreviation lines and its shadow-mode-off line.** Options: approve with run 8's counts refreshed / revise / hold. `rec=hold the shadow-mode-off line` (shadow stays on, D7) and `rec=approve the misheard-word lines with run 8's counts refreshed` — they still hold: `h5-01/f4` is that class under a mark. But they should say that a word can also go wrong with NO mark: `h5-17/f0` is unmarked whichever of (i) and (ii) the transcript shows. The guide's line that 2 of the 7 "carried no mark at all" already says so, and its counts move with run 8's.
    3. **The exit gate's rule-v5 proposal.** Options: approve / leave as a proposal / withdraw. `rec=leave as a proposal`. No validation run has passed under it, so approving its wording changes nothing on the gate yet. It is approved, if at all, when a run passes.
  - **Custody (after P.3's commit):** `C:\run8\` (the `set-heldout-5` folder), `C:\run8-p3\` and `.cursor/loops/held-out-lint/` may be deleted; `%TEMP%` checked for `scribe-speaker-eval-*` from the practitioner's terminal. P.1's earlier cleanup items stay owed.
  - **Next (composer):**
    1. Run `.venv/Scripts/python.exe .cursor/loops/run8-p3-overlap.py < /dev/null` and put its one integer in place of `<pending composer run>`, on P.3 and in the harness document.
    2. Read `C:\run8-p3\heldout-5\h5-17.txt`, or give a resumed leg permission to read it, to decide `h5-17/f0`'s (i) or (ii). Also check `report-rule-v5.md` against run 8's report.
    3. Run the desktop suite plain AND through the runner.
    4. Then P.3's commit on the practitioner's word, and P.2's three questions.
- **2026-11-07T08:20:57+11:00 — stage-7 executor (leg px1), P.1 RECORDED: run 8 did NOT meet rule v5's gate; documents and this plan only.** Operator brief:
  - **The result.** At `72256f4` the 50 pass. The blind `heldout-5` fails on one encounter, `h5-17`, where one material fact is `wrong` without a review mark (`h5-17/f0`, falsifier 3). The other six falsifiers did not fire. Marked R1 is 1 (`h5-01/f4`), inside its band. Two bands are outside: the load maximum is 6, and surfaced doubt is 1 / 11. The author overlap is pending P.3. Every seen set equals predictions v5, and only D5's lines differ from run 7's reports. The full record is on P.1.
  - **Written:**
    - `docs/testing/validation-harness.md`: run 8's entry replaces the placeholder (CRLF kept: 339 of 339 lines);
    - `plan-pilot.md` P.3: a RUN line (LF kept);
    - `CHANGELOG.md` Unreleased: one entry (CRLF kept: 249 of 249);
    - this plan: P.1 🟩 with its as-built line, Overall Progress, and the lines below.
  - **Untouched:** no code, test, rule file or anything under `.cursor/loops/`. C12: nothing under `validation/heldout-5/`, `.cursor/loops/held-out-lint/` or `.cursor/loops/run8-reports/` was opened, and no `h5-` row of `REFERENCE_TAIL_STARTS` was read. Only `h5-` ids the reports print are named.
  - **The suite:** `TestHarnessDocument` reads the harness document's Rule v5 table and the rule-v3 split, not "Runs of record", and `test_pilot_docs.py` reads `docs/pilot/*.md`, which did not change. So no suite is owed for these edits. A full runner pass before the record commit is the composer's choice.
  - **No MUST-PAUSE; no Deferral Confirmation Gate candidates.**
  - **Open practitioner questions (recorded, not asked; each `rec=`):**
    1. **P.2, the P.5 decision.** Options: keep shadow on / shadow off. `rec=keep-shadow-on`. D7 fixes it after a FAIL: "a recorded finding, P.5 stays (a)", whatever the band rule's reading. "Off" would need a new dated decision against D7, which this plan does not offer.
    2. **The register rows (P.2, with the `h5-` rows after P.3 as P.2's task line says).** Options: (a) one `controlled` row each, entered at P.3 by class: the failure `h5-17/f0`; the marked R1 fact `h5-01/f4` (D1's category rule); and the two out-of-band readings (the load maximum, `h5-12`; surfaced doubt, 1 / 11). Every row keeps the shadow control (D7). (b) The failure and the marked R1 fact as rows, with the two band readings on P.3's record only. `rec=a`: the pre-registration says outside a band "is a finding".
    3. **P.3, the diagnosis of `h5-17/f0`.** It is classed by its own words (number, unit, abbreviation, side, negation, other). Options:
       - (i) the recogniser's: a confident misrendering with no mark;
       - (ii) the script's or the reference reading's: a harness finding, not the product's;
       - (iii) a boundary matter: `h5-17`'s reference boundary 14 against its tail start 15.
       `rec=classify-by-its-own-words`, with no class presumed before P.3 reads it. The P.3 record also reads the two out-of-band bands and computes the author overlap.
    4. **The next plan, by P.3's class.** Options:
       - (i) the recogniser without a mark: the low-confidence threshold (0.60) and the mark's reach, a new dated decision with the guard and threshold measurements repeated (`plan-invented-text-guard.md` C2; Follow-Up Continuation Notes 1);
       - (ii) a harness or reference finding: a harness plan, with a fresh pre-registered blind set before any re-run;
       - (iii) `plan-gpu-decoding.md`'s run 9 on a fresh `heldout-6` (Task 0.0 A), if the practitioner wants that order.
       `rec=(i)` if P.3 classes it as the recogniser's, otherwise `rec=(ii)`. Never a rule change (C16, D7).
  - **Next (composer):** the record commit on the practitioner's word, then Phase P's P.2 and P.3. The practitioner's cleanup is owed (P.1's as-built line).
- **2026-11-06T21:44:32+11:00 — stage-7 executor (leg x5), peer round 28's one LOW applied; plan records only.** Operator brief:
  - **Round 28 PR-LOW-001: CONFIRMED** (🔁, a sibling leg x4's sweep missed). Round 8's Scope line said "permitted-symbol compliance" unqualified over the 0.2b diff, which also changes `render_report`'s docstring. A dated qualification now sits under it.
  - **One further search** over the Review History, the Findings Log and the handoff notes: `symbol compliance`, `symbol-level`, `permitted-symbol`, `permitted symbol`, `C17 held`, `C17 hold`, `C17 unchanged`, `C17 text`, `unchanged C17`, `C17 boundar`, `C17 compliance`, `compliance` / `complies` / `compliant`, `C17 remain`, `C17(b)`, `C17 … confirmed`, and every Review History line naming C17. Hits and dispositions:
    - Round 8 Scope ("permitted-symbol compliance") → QUALIFIED (the docstring).
    - Round 5 Scope ("C17 boundaries", 0 findings over Task 0.2a) → QUALIFIED (`RULE_SCHEMA_VERSION`). This is a sibling the peer did not name.
    - Round 7's finding and its fix notes (`C17(b)`, "permitted-symbol list", "symbol-level check") → the peer's own finding, kept as history; its fix notes were qualified in leg x4.
    - Round 6's "confined to the permitted symbols" → already qualified (leg x4).
    - Rounds 22, 26, 27 and 28 (the quoted findings, "compliance claim/record") and their Review History lines (rounds 7, 22, 27, 28) → peer quotes and summaries of findings, kept.
    - Round 23's Scope ("C16 and C17 remain unchanged", about the constraint TEXT) and the peer Scope lines of rounds 24–29 ("constraint text unchanged", "both exceptions correctly identified") → true; nothing to qualify.
    - The scoped `/review-plan` History line ("C16–C18 unchanged", the text) → true; kept.
    - "C17 holds" in the lineage line, Task 0.0 and the stage-3 handoff → the base or no package change; true.
    - The stage-1 and stage-2 leg x1 handoffs' "C17 holds" → already qualified (leg x4).
    - The leg x4 bullet's and round 26's sweep lists → the search terms; kept, and corrected for the count.
  - **Counts corrected:** nine records qualified in legs x4–x5, not seven — in round 26's `/fix` notes, round 22's pointer, round 27's `/fix` decision and the leg x4 bullet.
  - Round 28 is closed (0 pending). Round 29 converged with 0 findings.
  - Only this plan changed: no code, test or document. C17's text is unchanged. C12: `validation/heldout-5/` not opened, listed or searched.
  - **No MUST-PAUSE; no Deferral Confirmation Gate candidates.**
  - **Next (composer):** the last codex re-check the cap allows (peer round 5 of 5), if the loop config asks; then close H4 and make the H4 commit, which P.1 runs from.
- **2026-11-06T21:38:57+11:00 — stage-7 executor (leg x4), peer rounds 26–27's one LOW applied by an exhaustive sweep; plan records only.** Operator brief:
  - Rounds 26 and 27 (PR-LOW-001 in each) are one defect, CONFIRMED (🔁 round 22's family). Round 22's fix had qualified three records, and more unqualified claims that the run's `validation.py` diff fits C17 (b)'s list remained.
  - **The sweep:** the whole plan, for `permitted list`, `C17 (b) holds`, `C17 (b):`, `every hunk`, `inside the permitted`, `confined to`, `sits in`, `within C17`, `inside C17`, `C17 (b)'s list`, `permitted symbols`, `C17 (b) as recorded`, `C17 (b) for`, `C17 holds`, `(b) nothing`, `(b) no`, and every `C17` mention, each hit read in full.
  - **Qualified, dated, beside the record**, naming the exception(s) that apply — `RULE_SCHEMA_VERSION` and its comment (Task 0.2a) and/or `render_report`'s docstring (Task 0.2b):
    1. the stage-2 leg x3 handoff;
    2. the stage-2 leg x1 handoff;
    3. the stage-1 leg x1 handoff;
    4. Round 4's C17 (b) line;
    5. Round 6's "**C17 (b).**" line;
    6. Round 7's verify notes ("19 hunks, every one");
    7. Task 0.2b's composer Closed record.
  - **Pointers added:** the stage-7 leg x2 handoff and round 22's verification notes, where "three records" is now incomplete.
  - **Already qualified** by round 22's fix: round 19, the stage-1 leg x2 handoff, and Task 0.2b's "supersedes" record (which also covers the leg-x1 task-line enumeration).
  - **Checked, nothing to qualify:**
    - C17's text;
    - Task 0.2a's own C17 line and Closed record (they name the constant);
    - the stage-2 leg x2 handoff (`evaluate_encounter` untouched — true);
    - the lineage line and Task 0.0 (the base, not the list);
    - the stage-3 handoff (no package change);
    - the per-stage "(b) nothing changed" lines of stages 3–7;
    - the H4 peer instruction;
    - the "Reviewed: every hunk" scope lines;
    - the peer quotes;
    - the Deferred bullet and round 20.
  - The full table is in round 26's `/fix` notes. Both rounds closed (0 pending).
  - `[2026-11-06T21:44:32+11:00, peer round 28 PR-LOW-001]` "Exhaustive" was wrong. The sweep missed two round summaries: Round 8's Scope line ("permitted-symbol compliance") and Round 5's ("C17 boundaries", 0 findings). Leg x5 qualified both: nine records in all, not seven.
  - Only this plan changed: no code, test or document. C17's text is unchanged. C12: `validation/heldout-5/` not opened, listed or searched.
  - **No MUST-PAUSE; no Deferral Confirmation Gate candidates.**
  - **Next (composer):** a codex re-check if the loop config asks for one; then close H4 and make the H4 commit, which P.1 runs from.
- **2026-11-06T21:33:33+11:00 — stage-7 executor (leg x3), the re-check's one LOW applied; plan records only.** Operator brief:
  - Rounds 24 and 25 (PR-LOW-001 in each) are one defect, CONFIRMED. The stage-7 leg x1 handoff bullet below still called an extra count-only scan of `author-session.jsonl` C12-permitted, and said the log was redacted. Round 23 had fixed round 21 but missed this copy (🔁).
  - A dated correction now sits under that bullet: no scan before P.3, and the one count was Task 0.5's copy-in (0 identifying forms found, log copied unchanged).
  - Sibling sweep: no other uncorrected copy in the plan (round 24's `/fix` notes list the hits and why each stands).
  - Both rounds closed (0 pending). Only this plan changed. C12 unchanged; `validation/heldout-5/` not opened, listed or searched.
  - No MUST-PAUSE; no Deferral Confirmation Gate candidates.
  - **Next (composer):** a codex re-check if the loop config asks for one; then close H4 and make the H4 commit, which P.1 runs from.
- **2026-11-06T21:28:43+11:00 — stage-7 executor (leg x2), H4's two peer findings verified and applied; plan records only.** Operator brief:
  - **Round 22 PR-LOW-001: confirmed.** Two inert, task-authorised hunks lie outside C17 (b)'s literal list: `RULE_SCHEMA_VERSION`'s value and comment (Task 0.2a) and `render_report`'s docstring (Task 0.2b). Three records said every hunk was inside it, and each is corrected in place, dated: round 19, the stage-1 leg x2 handoff, and Task 0.2b's record. (`[2026-11-06]` Not exhaustive: peer rounds 26–27 found more siblings. Leg x4 qualified every one; its handoff bullet lists them.)
    - C17's text is unchanged, so no MUST-PAUSE. Its purpose (nothing decodes or routes) holds. The code cannot be conformed: the constant is Task 0.2a's own requirement and is pinned, and the docstring is correct.
    - Neither hunk belongs in the post-P.1 docstring commit, because both are already correct.
  - **Round 23 PR-LOW-001: confirmed.** Round 21's note wrongly called an extra count-only scan of `author-session.jsonl` C12-permitted. It now says no further scan is made before P.3. It also names the one count already made at Task 0.5's copy-in: 0 identifying forms, so the log was copied unchanged. C12 is unchanged.
  - Both rounds are closed (0 pending). Only this plan changed: no code, test or document. ruff and mypy were not re-run, since nothing they read changed. C12: `validation/heldout-5/` was not opened, listed or searched.
  - **No MUST-PAUSE; no Deferral Confirmation Gate candidates.**
  - **Next (composer):** a codex re-check of the two corrections, if the loop config asks for one. Then close H4 and make the H4 commit, which P.1 runs from.
- **2026-11-06T21:11:57+11:00 — stage-7 executor (leg x1), hardening H1–H3 DONE over the whole run; H4 is the composer's codex pass.** Operator brief:
  - **Scope.** One pass over `git diff 9884f04 HEAD -- . ':(exclude)validation/heldout-5'`: 28 files, Tasks 0.2a to Phase 1.
  - **H1, `/review-loop` round 19:** converged on its first round, with 2 LOWs, both applied.
    - LOW-001: `validation-harness.md`'s "The gate for run 8" said only `heldout` and `heldout-2` still fail. Predictions v5 have `heldout-4` failing too, so it is now named.
    - LOW-002: the one docstring-only `validation.py` commit owed after P.1 was recorded only in round 7's log. It is now a Deferred bullet, with its symbols and the trigger "after P.1, when C17 lapses".
  - **H2, `/simplify` round 20:** 0 findings. Five candidates were left alone, each plan-chosen or barred by C17 (b).
  - **H3, `/security-review` round 21:** 0 findings (portable checklist). One note for the composer, not a finding: `validation/heldout-5/author-session.jsonl` is in the public repository with only the user name redacted, and C12 kept this round from opening it. A count-only check (integers, no statement) is within C12 if you want that assurance before the push; otherwise P.3 is its first examination.
    - `[2026-11-06T21:33:33+11:00, corrected by peer rounds 24–25 PR-LOW-001, as round 23 corrected round 21]` Both claims above are wrong.
      - No further scan is made before P.3: C12 names its readers, and a count-only check is not one of them.
      - The log was not redacted. At Task 0.5's copy-in the composer counted the identifying forms (the Windows user name, the account name, the e-mail domain and the user-profile path forms) and found 0, so the log was copied unchanged (Task 0.5's Closed sub-bullet, item 1).
      - P.3 is the log's first examination. C12's text is unchanged.
  - **What changed.** One line of `docs/testing/validation-harness.md` (CRLF kept: 0 LF-only lines, 0 bare `\r`) and this plan. No code or test. ruff passes; mypy reports no issues in 66 source files. pytest not run (C12).
  - **Constraints.** C12: nothing under `validation/heldout-5/` or `.cursor/loops/held-out-lint/` opened, listed or searched. C16: no fixed record touched. C17 (a) empty since `170345d`; (b) no `validation.py` change in this stage; (c) unchanged.
  - **No MUST-PAUSE; no Deferral Confirmation Gate candidates** (both LOWs were do-the-work, LOW and non-production).
  - **Next (composer):**
    1. The suite ONLY through `scripts\lint-held-out-set.py validation\heldout-5`. `TestHarnessDocument` reads the edited document; its tables are unchanged.
    2. **H4, the codex peer re-check, in two slices** (run 7's rounds 26–27 shape):
       - **Code slice:** `validation.py` (the 0.2b hunks: the `FactOutcome` partition against `__post_init__`, `class_counts`' split, `counting_marked_r1`, `rule_v2_counterpart`'s neutralisation, the heading, `_verdict_lines`, the amendments' gates, `_residue_section`'s two marked-line branches), `rule-v5.json`, `test_validation_metrics.py` and `test_validation_harness.py`. Ask it to check for vacuous or mis-indexed pins, and that C17 (b)'s symbol list covers every hunk.
       - **Documents slice, one evidence line per document:** `validation-harness.md` (the Rule v5 section against the code and Task 0.3's predictions, including round 19's LOW-001 line), `validation/README.md`, `docs/pilot/README.md`, `exit-gate.md` (still a proposal), `findings-register.md`, `docs/practice/clinician-review-guide.md` and `README.md` (still awaiting approval; the counts against run 7's reports), `threat-model.md`, `data-flow-map.md`, `scripts/README.md`, the two launchers' docstrings, `ci.yml`'s comment, the comment-only test edits, `AGENTS.md`, `CHANGELOG.md`, `plan-pilot.md`'s override and P.5 lines, `plan-larger-model.md`'s two lines, and this plan's round 19–21 records and the new Deferred bullet.
       - Both slices bound by C12: no read of `validation/heldout-5/`, and no `h5-` id named.
    3. Close H4, then commit. This is the H4 commit P.1 runs from.
- **2026-11-06T20:48:39+11:00 — stage-6 executor (leg x1), Phase 1 BUILT and REVIEWED, converged; the suite is owed (composer).** Operator brief:
  - **Done.**
    - Task 1.1 🟩: the review guide's misheard-number, unit and abbreviation lines and its shadow-mode-off line, and the practice README. Both are marked "awaiting the practitioner's approval", with counts re-read from run 7's reports and no ids.
    - Task 1.2 🟨: every D8 document, the new `## Rule v5` in the harness document, the four override lines in the practitioner's words, the stale cites, `AGENTS.md` and `CHANGELOG.md`. Detail is on the tasks.
    - 24 tracked files change, plus this plan.
  - **One deviation from D2's draft, by the code.** The draft said the set was read "in a quiet room", but 8 of the 50 scripts mix a steady hiss in. The guide says so, and the record is on Task 1.1.
  - **Review.** `/review-loop` round 17 converged on its first round: four record-level LOWs (wording), all applied. ruff passes; mypy reports no issues in 66 source files. pytest was not run (C12).
  - **Constraints held.**
    - C17 (a) is empty since `170345d`; (b) nothing under `desktop/src` changed; (c) `run-validation.py` changed in its docstring only.
    - C12: nothing under `validation/heldout-5/` or `.cursor/loops/held-out-lint/` was opened or listed.
    - CRLF is kept in every CRLF file, including two outside the state table's list: `docs/security/threat-model.md` and `data-flow-map.md`.
  - **No MUST-PAUSE; no Deferral Confirmation Gate candidates.** D1's override words were in the plan, so nothing was worded for the practitioner.
  - **Next (composer):**
    1. Run the suite ONLY through `scripts\lint-held-out-set.py validation\heldout-5`. It covers `test_pilot_docs.py` and the new `TestHarnessDocument.test_the_rule_v5_ceiling_table_is_the_files`.
    2. Run the codex peer pass over Phase 1. The documents form their own slice, with one evidence line per document.
    3. Close Task 1.2, then commit.
    4. Then stage-7 = H1–H4.
- **2026-11-06T20:13:00+11:00 — stage-5 executor (leg x4), Task 0.5: the author has run, and the README and presence pin are written; the copy-in, tails and runner are owed (composer).** Operator brief:
  - The practitioner's launch is answered: `.done` holds `EXIT:0`.
  - The composer checked names and hashes only:
    - 22 scripts, `h5-01` to `h5-22` with no gap, plus `AUTHOR-NOTES.md` and `SPEC.md`;
    - `SPEC.md`'s hash unchanged;
    - the session ended `success` / `DONE 22`.
  - Written while `validation/heldout-5` is absent; the author folder was never listed or read:
    - `validation/README.md`'s `heldout-5/` bullet, in the authored state of `heldout-4`'s authoring shape (CRLF kept, one line changed);
    - the temporary presence pin `test_the_blind_held_out_set_is_present` (file names only; removed at P.3).
  - ruff and mypy are green. pytest was not run: the pin fails until the set is copied in.
  - `REFERENCE_TAIL_STARTS` is not touched.
  - No MUST-PAUSE; no Deferral Confirmation Gate candidates.
  - Next, in order (the composer):
    1. Copy the set in unread, and byte-check each copy.
    2. Run `validation-run8-heldout5-tails.py`.
    3. Run the suite ONLY through `scripts\lint-held-out-set.py validation\heldout-5`.
    4. Make the Task 0.5 commit with `edd1a7d`.
- **2026-11-06T17:12:09+11:00 — stage-5 executor (leg x3), peer round 15 routed: PR-LOW-001 CONFIRMED and applied (record-only).**
  - Codex flagged that the leak record had which closing phrase was new the wrong way round, copied from run 7's Task 0.7 record. `see you next week` has been listed since 2026-09-28 (`consultation_phrases.py:90`); `see you` is the phrase `de8f5da` added (`:111`).
  - Task 0.5's leak record now says so. Round 14's LOW-001, which copied the same mistake, gets a dated pointer. Run 7's plan is not edited.
  - The disposition does not change. The line-48 hit was already present for the earlier authors, and the newer `see you` match lies inside that same phrase. So the brief goes to the author unchanged. No MUST-PAUSE.
  - The brief, the prompt and the four tools are unchanged, so the leak run's hashes stand.
  - Round 15 is closed (0 pending). No Deferral Confirmation Gate candidates.
  - The practitioner's step below is unchanged.
- **2026-11-06T17:07:37+11:00 — stage-5 executor (leg x2), Task 0.5 PREP REVIEWED, converged. STOP: the practitioner launches the author.**
  - **Where things stand.** The leak run exited 0 with the same 10 hits as run 7 on the same lines, no new phrase and 0 primer hits. Its hashes are recorded on Task 0.5:
    - `SPEC.md` `819be450…994f54`;
    - `author-prompt.txt` `77584132…8103d5`.
  - The runner's prompt equals the generated one. The CLI preflight with D4's flags passed: Claude Code 2.1.282, `PREFLIGHT_OK`, exit 0. `/review-loop` round 14 converged on its first round with one record-only LOW, applied. `validation/heldout-5` is absent.
  - **What the practitioner does.** Use a NORMAL terminal (Git Bash), never an agent shell or a chat Run button.
    1. Confirm that `C:\heldout5-author` holds the regenerated `SPEC.md` ALONE. `ls -A /c/heldout5-author` should print only `SPEC.md`. `sha256sum /c/heldout5-author/SPEC.md` should print `819be45027db4e9dfa2f5dd5e74e0b7a8447effae22c173ff2e1c525da994f54`.
    2. From the repository root (`cd "/c/Recording clinic software"`), run `bash ".cursor/loops/validation-run8-heldout5-author-run.sh"`.
    3. Wait for `.cursor/loops/validation-run8-heldout5-author.done`. It holds `EXIT:<code>`, and the author's last line should be `DONE <number of scripts>`. Do not open the scripts, `AUTHOR-NOTES.md` or the log.
    4. If the script returns at once and no `.done` file appears, the `cd` into `/c/heldout5-author` failed (exit 9). Check that the folder exists and run the script again.
  - **What happens after (the composer resumes Task 0.5).**
    - The scripts are copied into `validation/heldout-5/` UNREAD, with `SPEC.md` and `author-prompt.txt` from the regenerated brief, `AUTHOR-NOTES.md` and the session log as `author-session.jsonl` with the user name redacted. Each copy is byte-checked against its source.
    - `.cursor/loops/validation-run8-heldout5-tails.py` writes the `h5-` rows of `REFERENCE_TAIL_STARTS` (ids and integers only).
    - The file-name-only presence pin is added.
    - The suite and lints run ONLY through `scripts\lint-held-out-set.py validation\heldout-5` (C12). A lint failure goes back to the author as its code, never as a script edit.
    - `validation/README.md`'s entry moves to the authored state.
    - The commit carries the pre-registration hash `edd1a7d`.
- **2026-11-06T17:04:06+11:00 — stage-5 executor (leg x1), Task 0.5 PREP BUILT; the leak run is owed (composer).** Operator brief:
  - Task 0.5 is 🟨. The four git-ignored tools are written in `.cursor/loops/`, and none was run:
    - `run8-brief-leak.py`;
    - `validation-run8-heldout5-author-prompt.txt`;
    - `validation-run8-heldout5-author-run.sh`;
    - `validation-run8-heldout5-tails.py`.
  - Each differs from its run-7 original by D4's edits. Five small extras are listed and justified on the task; none changes what the author sees.
  - The tails anchor `"h4-21": None` is the current last row at `edd1a7d`.
  - No MUST-PAUSE and no Deferral Confirmation Gate candidates.
  - `validation/heldout-5` is absent. Nothing tracked changed but this plan.
  - Next, in order:
    1. The composer runs `.venv/Scripts/python.exe .cursor/loops/run8-brief-leak.py`. Expected: exit 0, `changed 4`, primer 33 terms with 0 hits, `[prompt] … yes`.
    2. The composer runs the CLI preflight.
    3. This executor is resumed to record both hashes and run `/review-loop`.
    4. `C:\heldout5-author` is created with `SPEC.md` alone, and the PRACTITIONER launches the runner.
- **2026-11-06T16:57:06+11:00 — stage-4 executor (leg x1), Task 0.4 PRE-REGISTRATION BUILT and REVIEWED, converged; the commit is owed (composer).** Operator brief:
  - `heldout-5`'s pre-registration is on Task 0.4, the only change, in this plan alone. The set does not exist, nothing names an `h5-` id, and no rule file, script or `desktop/` file changed (C2, C12, C16).
  - It holds:
    - D4's seven gate falsifiers, each with D4's expected range and the rule-v5 `heldout-5` field it trips;
    - D4's eight bands, with Task 0.3's seen numbers beside them;
    - D7's band rule, verbatim, as the P.5 recommendation, never a gate;
    - the author-overlap band, "pending P.3" at P.1;
    - D3's qualifiers and the Goal's;
    - the prediction for the four verdicts, the Goal's and D7's, with no rule-v1 forecast added.
  - `/review-loop` round 12 converged on its first round: 0 CRIT / 0 HIGH / 0 MED / 6 LOW, all record-only and applied. Review History integrity: OK.
  - Two notes for the practitioner, neither a pause:
    - The plan holds no fraction for the role-tails band's seen values, so none is written. The run-7 Task 0.7 fractions were not imported.
    - The Goal's "0 on every blind set so far" for a silent fact after R1 does not count `heldout-2`'s 25, which the Goal names separately. D4's expected 0 is unchanged.
  - No MUST-PAUSE; no Deferral Confirmation Gate candidates.
  - Next: the codex peer pass (cadence every-phase) or the 0.4 commit ALONE, as the composer runs it. Then the commit's hash goes on Task 0.5 before Task 0.5 starts.
- **2026-11-06T16:45+11:00 — stage-3 executor (leg x3), peer round 10 routed: PR-LOW-001 and PR-LOW-002 CONFIRMED and applied; script re-run owed.** Operator brief:
  - **PR-LOW-001 (record):** Task 0.3's run line now keeps the first run as history (its kept copy `run8-predict-out.r1.txt`). It adds the round-9 re-run's facts (158 lines, script `1d838bef…`, output `41bd1c65…`, five blank lines only) and a "Re-run after peer round 10 (owed, composer)" line.
  - **PR-LOW-002 (script):** the render-difference check now builds, from each rule-v3 line, exactly what D5 lets the rule-v5 line become: labels, roles, the gate / reported lists, the heading's one added verdict, the run information extended, and the R1 row's name only where the row reports. It also allows exactly two inserted lines. Any other change — a count, a removed or an extra line — is "other" (exit 6).
  - No frozen prediction changes, and D5's text is untouched. The printed summary is expected byte-identical to the round-9 output.
  - The composer re-runs `.venv/Scripts/python.exe .cursor/loops/run8-predict.py > .cursor/loops/run8-predict-out.txt`. Its exit code, line count, script and output SHA-256, and its `diff` against the round-9 output go on Task 0.3's "Re-run after peer round 10 (owed, composer)" line.
  - No MUST-PAUSE; no Deferral Confirmation Gate candidates.
  - Next: that re-run, a peer re-check if the loop config asks, then the 0.3 commit.
- **2026-11-06T16:37+11:00 — stage-3 executor (leg x2), Task 0.3 PREDICTIONS FROZEN and REVIEWED, converged; script re-run owed.** Operator brief:
  - The composer's run exited 0. The R1 assertion and the rule-v3 reproduction passed on all five sets.
  - Predictions v5 are frozen on Task 0.3 from `run8-predict-out.txt`: per set the four verdicts, failing ids and reasons, residue members with R1's split, the after-class and excused counts, surfaced / expected, the load and Check 6. The method, the hashes, the corroboration (corroboration only) and C17 are recorded with them.
  - Headline: `scripts` PASS on rule v5. `heldout`, `heldout-2` and `heldout-4` FAIL. `heldout-3` PASS (FAIL without the R1 exemption). On every seen set rule v5's verdict equals its counted-R1 verdict.
  - `/review-loop` round 9 converged on its first round: 0 CRIT / 0 HIGH / 0 MED / 2 LOW, both in the script and applied:
    - the missing blank line before each residue section;
    - the difference check's categories were broader than D5's (a changed rule-v1 line or a seen-set R1 row now counts as "other").
  - Neither changes a printed prediction. The script changed, so the composer re-runs it: expected exit 0 and 158 lines, the five extra being blank. The record is then re-checked against the new output.
  - No MUST-PAUSE; no Deferral Confirmation Gate candidates.
  - Next: the re-run, then the codex peer pass or the 0.3 commit as the loop config says. Overall Progress is updated at the composer's close.
- **2026-11-06T16:33+11:00 — stage-3 executor (leg x1), Task 0.3 SCRIPT WRITTEN, run owed.** Operator brief:
  - `.cursor/loops/run8-predict.py` is written. It is the only file created; the tree is otherwise clean.
  - It asserts D5's six R1 members first: an R1 member `wrong` with Ambiguous `yes` → exit 2. Any other membership or kind → exit 4.
  - It then rebuilds the outcomes with the harness's own types and asserts that HEAD's `render_report` under rule v3 reproduces each run-7 report → exit 3 on a difference, naming the set, the line number and the region. The heading, verdict lines and residue section must match byte for byte. The run information, checker warnings, Facts table and encounter rows are also compared, less four unrebuildable columns.
  - Only then does it print rule v5's lines per seen set, Check 6 per axis script, and the rule-v5 vs rule-v3 differences by D5's categories (exit 6 if one falls outside them).
  - Exit codes and design notes are on the task line. C17 holds. ruff and mypy green (no package change). No MUST-PAUSE: the reports print what D5 says (Verdict, Ambiguous, Residue class per fact; no Ambiguous `yes` fact anywhere), and the R1 class cells name exactly the six.
  - No Deferral Confirmation Gate candidates.
  - Next: the composer runs `.venv/Scripts/python.exe .cursor/loops/run8-predict.py > .cursor/loops/run8-predict-out.txt` and resumes this executor with the output or the refusal. Then come the fixes, the frozen predictions on Task 0.3 and `/review-loop`.
- **2026-11-06T16:08+11:00 — stage-2 executor (leg x3), peer round 7 routed: PR-LOW-001 CONFIRMED and applied; suite re-run owed.**
  - The composer's suite after round 6: 9614 passed, 0 failed, 9 skipped (697 s); C17 (a) empty.
  - The finding was right as a literal C17 (b) check: a new helper and five docstring and comment edits sat outside its symbol list, though none touches decoding or routing.
  - The fix keeps C17's text unchanged:
    - `_r1_marked_members` is folded into `class_counts` / `_residue_section`;
    - the `EncounterMetrics` ×2, `RULE_V2_RATIFIED`, `rule_failures` and `run_passed` edits are reverted to `ba71ff5`.
  - Every `validation.py` hunk since `ba71ff5` is now in C17 (b)'s list. Behaviour is unchanged. (`[2026-11-06, peer rounds 26–27 PR-LOW-001]` But for `render_report`'s docstring (Task 0.2b), which sits in the heading's hunk. C17 (b)'s literal list names the heading and the amendments, not the docstring. It is inert, and C17's text is unchanged; see round 22's `/fix` notes.)
  - Not taken: amending C17 (b) to admit the helper and the inert docstrings. That needs the practitioner's word on a Critical Constraint, for a LOW with no decode or routing effect. rec=conform-the-code (done). The stale "schema 3" docstring words, `evaluate_encounter`'s with them, wait for one docstring-only commit after P.1.
  - ruff and mypy green. Next: the composer re-runs `desktop full pytest`, then the 0.2b commit ALONE (or a peer re-check by the loop config).
- **2026-11-06T15:52+11:00 — stage-2 executor (leg x2), Task 0.2b REVIEWED, converged; suite re-run owed.**
  - The composer's suite on the leg-x1 build: 9613 passed, 0 failed, 9 skipped (712 s); C17 (a) empty.
  - `/review-loop` round 6 (Review Findings Log): 0 CRIT / 0 HIGH / 0 MED / 2 LOW, converged on the loop's first round. Every check the composer named holds: the both-case precedence, schema-3 reports byte-unchanged, no printed equality with rule v4, the counterpart's neutralisation both ways, silent-only gating on a reporting row, and every new line on every schema-4 row and none on schema 3.
  - LOW-001 adds one test, so the composer re-runs `desktop full pytest` before the 0.2b commit. The test pins that a schema-3 file named `rule-v5-test` prints no rule-v5 sentence. LOW-002 re-words the Overall Progress line (record-only).
  - ruff and mypy green. C17 (b) as recorded on the task line: `evaluate_encounter` untouched.
  - Next: the suite re-run, the 0.2b commit ALONE, then the codex peer pass (cadence every-phase) or stage-3 as the composer runs it.
- **2026-11-06T15:37+11:00 — stage-2 executor (leg x1), Task 0.2b BUILT, suite owed.** Operator brief: rule v5's reading and report are in — R1's two kinds (`FactOutcome.residue_r1_silent` / `residue_r1_marked`, the both-case silent), `ClassCount.reported_members`, `class_counts` counting only silent R1 under the ceiling where a row reports marked R1, `PassRule.counting_marked_r1()`, `rule_v2_counterpart` reading `False` as rule v2's `None` and `True` as `differs`, the fourth verdict ("rule {label} with marked R1 counted", named by `PassRule.label`, no "= rule v4" claim) in the heading and the verdict lines, the amendments' history gates and the rule-v5 sentence, the residue section's R1 row name and the new marked-R1 line on every schema-4 row, the excused-lines gate `>= 3`, "schema-2 or later" in the help / docstring / refusal; tests in `test_validation_metrics.py` (`TestRuleV5Reading`) and `test_validation_harness.py` (whole `heldout-5` and `heldout-4` rule-v5 reports, the `rule-v6-test` label pin, the mirror pin, the rule-v5 `main` pin, the help test on rule v5). ruff and mypy green; pytest NOT run (verify=composer). Rule v3 / v4 whole-report pins byte-unchanged. C17 holds (the task line's record; `validation.py` the only decode-path file changed since `170345d`). (`[2026-11-06, peer rounds 26–27 PR-LOW-001]` C17's purpose holds, but C17 (b)'s literal list does not cover two inert, task-authorised hunks: `RULE_SCHEMA_VERSION` and its comment (Task 0.2a), and `render_report`'s docstring (Task 0.2b). C17's text is unchanged; see round 22's `/fix` notes.) Four trivial deviations on the task line — the most notable: `evaluate_encounter`'s stale docstring word left alone because C17 (b) forbids touching it (rec: leave it; fix after P.1). No MUST-PAUSE; no Deferral Confirmation Gate candidates. Next: the composer runs `desktop full pytest`, then resumes this executor for fixes and `/review-loop` (the first build round is 6 — `loop-history-check.py` to confirm), then the 0.2b commit ALONE.
- **2026-11-06T15:10+11:00 — stage-1 executor (leg x2), Task 0.2a REVIEWED, converged; suite re-run owed.** The composer's suite on the leg-x1 build: 9471 passed, 0 failed, 9 skipped (720 s); C17 (a) empty. `/review-loop` round 4 (Review Findings Log): 0 CRIT / 0 HIGH / 0 MED / 1 LOW — the `SetCeilings` docstring's opening ("a schema-2 or later rule"), applied; converged on the loop's first round. ruff and mypy green after the fix; it is docstring-only, but it is a code change, so the composer re-runs `desktop full pytest` before the 0.2a commit. **C17 (b) for Task 0.2a:** `git diff 170345d -- desktop/src/scribe_desktop/validation.py` touches only the `RULE_SCHEMA_VERSION` comment and value (named by the task; no decode or routing), `SetCeilings` (docstring, the `r1_marked_reported` field), `PassRule`'s docstring and `schema_version`, and `_check_sets` — inside C17 (b)'s permitted list (`[2026-11-06, peer round 22 PR-LOW-001]` but for the `RULE_SCHEMA_VERSION` comment and value, which Task 0.2a names and C17 (b)'s literal list does not; inert); never `evaluate_encounter`, the alignment, `_FactState`, the reference reading, the metric amendments or `UNCERTAINTY_THRESHOLD`. C17 (c): `scripts/run-validation.py` unchanged. Next: the suite re-run, the rule's blob on the task, the 0.2a commit ALONE, then the codex peer pass (cadence every-phase) or stage-2 as the composer runs it.
- **2026-11-06T14:54+11:00 — stage-1 executor (leg x1), Task 0.2a BUILT, suite owed.** Operator brief: rule v5 is in — schema 4 (`RULE_SCHEMA_VERSION` 4, `Literal[1, 2, 3, 4]`), `SetCeilings.r1_marked_reported` required non-None on every schema-4 row and refused non-None below schema 4, the exemption gate `>= 3`, `validation/rules/rule-v5.json` (D1's rows exactly; LF; rule v4's key order), and the loader pins in `test_validation_metrics.py` (`TestRuleV5`, C18's field-by-field equality, the schema-5 refusal, the re-pinned exemption messages, the label pins). ruff and mypy green; pytest NOT run (verify=composer). C17 holds (the task line's record). (`[2026-11-06, peer rounds 26–27 PR-LOW-001]` But for `RULE_SCHEMA_VERSION` and its comment, which Task 0.2a names and C17 (b)'s literal list does not. It is inert, and C17's text is unchanged; see round 22's `/fix` notes.) No MUST-PAUSE: a schema-4 file loads and renders under the pre-0.2b report code without a crash (the task line says what it prints meanwhile). Nothing touched outside `validation.py`, the new rule file, `test_validation_metrics.py` and this plan; rule v1–v4's files unchanged (C2). No Deferral Confirmation Gate candidates. Next: the composer runs the full desktop suite (`cd desktop && ../.venv/Scripts/python.exe -m pytest`), records the rule's blob on the task, then resumes this executor for fixes and `/review-loop` (first build round 4 — `loop-history-check.py` OK: 3 findings-log rounds), then the 0.2a commit ALONE.
- Last completed step: Task 0.3 — closed and committed alone (`431a38e`, the composer, 2026-11-06T16:50+11:00). Before it: Task 0.2b — closed and committed alone (`d15a28f`, the composer, 2026-11-06T16:25+11:00). Before it: Task 0.2a — closed and committed alone (`ba71ff5`, the composer, 2026-11-06). Before that: Task 0.1 — the plan committed on the practitioner's word (2026-11-06). Before that: planning — the Plan Mode draft approved through ExitPlanMode (2026-11-06), hardened by this `/review-plan` pass (three lenses, 36 findings reconciled); the practitioner's decisions recorded (Key Design Decisions); the codex plan peer pass (2026-11-06, gpt-6-astra high, cap 5): round 1 — 1 HIGH, 4 MED, 1 LOW; round 2 — 1 HIGH, 2 LOW; round 3 — 1 record-only LOW, converged; every finding applied. Nothing built, nothing committed.
- Current in-progress step: the hardening stage ✅ (2026-11-06T21:55+11:00) — H1–H3 (stage-7 leg x1: rounds 19–21) and H4, the codex re-check in two slices: the documents slice converged at round 29, the code slice at round 30 (rounds 22–30; every finding a LOW about the plan's own records, fixed record-only by legs x2–x5; C12's and C17's text and the code unchanged). The runner green after H1–H3 (9660 passed / 0 failed / 9 skipped); plan-only edits since. Committed as the H4 commit. Next: Phase P (practitioner) — P.1, run 8, from a clean checkout at this commit.
  - `[2026-11-07T08:20:57+11:00, leg px1]` P.1 ran (practitioner, 2026-11-06 → 2026-11-07) and is recorded (🟩): run 8 at `72256f4` did NOT meet rule v5's gate (`heldout-5` falsifier 3, `h5-17/f0`). Its record commit is owed. `[2026-11-07, leg px2]` Committed `5edcefa`; P.5 answered "Keep shadow on (Recommended), start P.3"; P.3 written (🟨), its overlap value, suite and commit owed. `[2026-11-07T09:13:38+11:00, leg px3]` P.3's overlap value (10) and transcript classes recorded; suite and commit owed. `[2026-11-07T09:30:47+11:00, leg px4]` The suite green over P.3 (9836 passed); P.2 recorded 🟩 (keep shadow on); P.4′ not applicable. Phase P is done but the P.3 and P.2 commits.
- Immediate next action (2026-11-07T09:30:47+11:00, leg px4): the composer's desktop suite through the runner over px4's register and document edits (`test_pilot_docs.py` reads the register); then the practitioner's word on the P.3 and P.2 commits; then `/document` and the loop's close; then the next plan (Plan Mode, with Fable) by `h5-17/f0`'s class — Follow-Up Continuation Notes 1. Custody after the commits: `C:\run8\`, `C:\run8-p3\`, `.cursor/loops/run8-p3/` and `.cursor/loops/held-out-lint/` may be deleted. ~~(2026-11-07T09:13:38+11:00, leg px3): the composer's desktop suite, plain and through the runner, over px2's test edits (px3 changed records only); then P.3's commit on the practitioner's word, then P.2's register rows and approvals (the three questions on the px3 handoff bullet).~~ (suite green; P.2 answered 2026-11-07) ~~(2026-11-07T09:05:48+11:00, leg px2): the composer runs `.cursor/loops/run8-p3-overlap.py` and fills its value, decides `h5-17/f0`'s (i) or (ii) from `C:\run8-p3\heldout-5\h5-17.txt` (refused to this leg), and runs the desktop suite plain and through the runner. Then P.3's commit on the practitioner's word, then P.2's register rows and approvals (the three questions on the px2 handoff bullet).~~ (the overlap run, the `h5-17.txt` read and the report check done: px3) ~~The practitioner's word on P.1's record commit (the composer commits the harness document, `plan-pilot.md`, `CHANGELOG.md` and this plan). Then P.2 (P.5 stays (a) by D7's FAIL branch; the register rows; the approvals) and P.3 (the `heldout-5` diagnosis, which ends the blind rule), with the open questions on the px1 handoff bullet.~~ (P.1 committed `5edcefa`; P.5 answered 2026-11-07) ~~The PRACTITIONER — P.1, run 8, the run of record (the Phase P line: a clean committed checkout at the H4 commit, a normal terminal, the installed app closed, lid open). The loop stops here (MUST-PAUSE `run8-p1`).~~ (done 2026-11-07)
- Open blockers / open questions: the GPU plan's half of Task 0.0's Done-when (its session). Owed from the practitioner, in order: ~~the `/execute-loop` start; the launch of the isolated author (Task 0.5); run 8 (P.1);~~ (done) ~~the word on P.1's record commit~~ (done, `5edcefa`) and P.1's cleanup (its as-built line); ~~the P.5 decision~~ (answered 2026-11-07: keep shadow on) ~~and the register rows and approvals (P.2)~~ (answered 2026-11-07, each the recommended option; recorded on P.2); the word on the P.3 and P.2 commits. The untick (P.4′) will not happen after a FAIL (D7): not applicable. ~~One question for the composer, on the px4 handoff bullet: whether `h5-10`'s next patient (R3) also gets a row.~~ (answered 2026-11-07: "Add the fifth row (Recommended)", F-153)
- Last plan sync: 2026-11-07T10:23:43+11:00 (stage-7 executor leg px5: F-153 added on the practitioner's "Add the fifth row (Recommended)", run 8's rows now F-149–F-153 in every record; at 2026-11-07T09:30:47+11:00 stage-7 executor leg px4: P.2 recorded 🟩, Chosen keep shadow on — F-149–F-152 and F-130 re-worded in the register, the review guide's misheard-word lines approved with run 8's counts (161 / 9 / 6 / 3), the shadow-mode-off line and the exit gate's proposal left as they were; P.3's suite recorded; P.4′ dropped as not applicable; `plan-pilot.md`, `AGENTS.md` and `CHANGELOG.md` brought up to date; at 2026-11-07T09:13:38+11:00 stage-7 executor leg px3: P.3's transcript-dependent classes settled from the copied dumps — `h5-17/f0` the recogniser's (a dropped word, no mark on the fact), `h5-01/f4` an abbreviation under the number mark, R2's seven and surfaced 1 / 11 confirmed, `h5-12`'s runs counted; the report equality confirmed; the overlap 10 recorded; records only; at 2026-11-07T09:05:48+11:00 stage-7 executor leg px2: P.3 written, 🟨 — the 22 cases, the divergence pins, rule 4 over `heldout-5`, the blind pins at `[]`, CI's comments, the past-tense records and the overlap script; `C:\run8-p3\` refused; P.5 answered "Keep shadow on"; at 2026-11-07T08:20:57+11:00 stage-7 executor leg px1: P.1 recorded — run 8 did not meet the gate; the harness document, `plan-pilot.md` P.3 and `CHANGELOG.md` written; at 2026-11-06T21:55+11:00 H4 closed by the composer: round 30 converged; the H4 commit; at 21:44:32 stage-7 executor leg x5: peer round 28's LOW applied — Rounds 8 and 5 qualified, nine records in all; round 28 closed, round 29 converged; at 21:38:57 stage-7 executor leg x4: peer rounds 26–27's one LOW applied by an exhaustive sweep, seven C17 (b) records qualified, both rounds closed; at 21:33:33 stage-7 executor leg x3: peer rounds 24–25's one LOW applied to the leg x1 handoff, both rounds closed; at 21:28:43 stage-7 executor leg x2: peer rounds 22–23's two LOWs verified and applied to the records, both rounds closed; at 21:11:57 stage-7 executor: H1–H3 done, rounds 19–21; at 21:05 Phase 1 closed by the composer: runner green, codex round 18 converged, committed; at 20:20 Task 0.5 closed by the composer: copy-in, tails, runner green, committed; at 20:13 Task 0.5: the author ran, the README entry and the presence pin written, the copy-in owed; at 17:12 peer round 15's PR-LOW-001 applied, record-only, round closed; at 17:07 Task 0.5's leak run and preflight recorded, review round 14 converged, the author launch owed; at 17:04 Task 0.5's prep built, the leak run owed; at 17:00 Task 0.4 committed `edd1a7d`; at 16:57 Task 0.4's pre-registration written, review round 12 converged, commit owed; at 16:50 Task 0.3 closed and committed `431a38e`; at 16:45 peer round 10's two LOWs applied, script re-run owed; at 16:37 Task 0.3's predictions frozen, review round 9 converged, script re-run owed; at 16:33 Task 0.3's script written, run owed; at 16:25 Task 0.2b closed and committed `d15a28f`; at 16:08 peer round 7's PR-LOW-001 applied, suite re-run owed; at 15:52 Task 0.2b reviewed, round 6 converged; at 15:37 built, suite owed; before it Task 0.2a committed `ba71ff5` after round 4 and peer round 5 converged; Task 0.1 committed and Task 0.0 decided A)

## Review History
- 2026-11-06 — Round 1 — codex gpt-6-astra high plan peer-review (`/peer-loop` plan-review, cap 5; composer-recorded from the read-only peer's log) — 1 HIGH, 4 MED, 1 LOW; all six accepted and applied; not converged.
- 2026-11-06 — Round 2 — codex gpt-6-astra high plan peer-review (composer-recorded) — five round-1 fixes confirmed, PR-HIGH-001 reopened as PR-HIGH-002; 1 HIGH, 2 LOW new; all applied; not converged.
- 2026-11-06 — Round 3 — codex gpt-6-astra high plan peer-review (composer-recorded) — round 2's three fixes confirmed (one sibling owed, fixed as PR-LOW-004); 0 build-affecting / 1 record-only; applied; **CONVERGED**.
- 2026-11-06 — scoped `/review-plan` (Fable 5.1, fast path) over Task 0.0's order-A amendments (the Chosen line, the lineage line, C17's base, the baseline-table row, the installed-configuration assumption, the `heldout-6` exclusion, the handoff): the Lifecycle State is Active; the edits fit D1/D4/D5/D7 and C16–C18 unchanged; no operative sentence still reads a parametrised base commit or an open order; 0.2a's dependency on the GPU plan's half is stated on 0.0 and in the handoff; no risk surfaced, so no lens fan-out.
- 2026-11-06 round 4: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=none
- 2026-11-06 — Round 5 — codex gpt-6-astra medium cross-family peer (pass stage-1.p1, peer round 1 of cap 5; composer-recorded from the read-only peer's log) over Task 0.2a — 0 findings (6 claims checked, 6 confirmed); **CONVERGED**.
- 2026-11-06 round 6: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=none; action=none
- 2026-11-06 — Round 7 — codex gpt-6-astra medium cross-family peer (pass stage-2.p1, peer round 1 of cap 5; composer-recorded from the read-only peer's log) over Task 0.2b — 1 LOW (PR-LOW-001, docs-only: the C17 (b) record vs C17's permitted-symbol list; 1 claim checked, 1 confirmed); routed to the executor's verify and /fix; not converged.
- 2026-11-06 — Round 8 — codex gpt-6-astra medium cross-family peer re-check (pass stage-2.p1, peer round 2 of cap 5; composer-recorded from the read-only peer's log) over Task 0.2b after Round 7's fix — 0 findings (8 claims checked, 8 confirmed); **CONVERGED**.
- 2026-11-06 round 9: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=none; action=none
- 2026-11-06 — Round 10 — codex gpt-6-astra medium cross-family peer (pass stage-3.p1, peer round 1 of cap 5; composer-recorded from the read-only peer's log) over Task 0.3 — 2 LOW (PR-LOW-001 docs-only: the record's pre-fix hashes and line count; PR-LOW-002 test-harness: the allowed-to-differ check classifies by line prefix; 2 claims checked, 2 confirmed); routed to the executor's verify and /fix; not converged.
- 2026-11-06 — Round 11 — codex gpt-6-astra medium cross-family peer re-check (pass stage-3.p1, peer round 2 of cap 5; composer-recorded from the read-only peer's log) over Task 0.3 after Round 10's fixes — 0 findings (8 claims checked, 8 confirmed); **CONVERGED**.
- 2026-11-06 round 12: 0 CRIT / 0 HIGH / 0 MED / 6 LOW; skew=none; action=none
- 2026-11-06 — Round 13 — codex gpt-6-astra medium cross-family peer (pass stage-4.p1, peer round 1 of cap 5; composer-recorded from the read-only peer's log) over Task 0.4 — 0 findings (13 claims checked, 13 confirmed); **CONVERGED**.
- 2026-11-06 round 14: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=none
- 2026-11-06 — Round 15 — codex gpt-6-astra medium cross-family peer (pass stage-5.p1, peer round 1 of cap 5; composer-recorded from the read-only peer's log) over Task 0.5's preparation — 1 LOW (PR-LOW-001 docs-only: the leak disposition's provenance of the two closing phrases reversed, carried from run 7's record; 1 claim checked, 1 confirmed); routed to the executor's verify and /fix; not converged.
- 2026-11-06 — Round 16 — codex gpt-6-astra medium cross-family peer re-check (pass stage-5.p1, peer round 2 of cap 5; composer-recorded from the read-only peer's log) over Task 0.5's preparation after Round 15's fix — 0 findings (8 claims checked, 8 confirmed); **CONVERGED**.
- 2026-11-06 round 17: 0 CRIT / 0 HIGH / 0 MED / 4 LOW; skew=none; action=none
- 2026-11-06 — Round 18 — codex gpt-6-astra medium cross-family peer (pass stage-6.p1, peer round 1 of cap 5; composer-recorded from the read-only peer's log) over Phase 1's documents, one evidence line per document — 0 findings (25 file-level claims checked, 25 confirmed); **CONVERGED**.
- 2026-11-06 round 19: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=none; action=none
- 2026-11-06 round 20: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none
- 2026-11-06 round 21: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none
- 2026-11-06 — Round 22 — codex gpt-6-astra medium cross-family peer, H4 code slice (pass stage-7.p1, peer round 1 of cap 5; composer-recorded from the read-only peer's log) over the run's code — 1 LOW (PR-LOW-001 docs-only: C17 (b)'s literal list omits `RULE_SCHEMA_VERSION` and `render_report`'s docstring; 5 claims checked, 5 confirmed); routed to the executor's verify and /fix; not converged.
- 2026-11-06 — Round 23 — codex gpt-6-astra medium cross-family peer, H4 documents slice (pass stage-7.p2, peer round 1 of cap 5; composer-recorded from the read-only peer's log) over the run's documents, one evidence line per document — 1 LOW (PR-LOW-001 docs-only: round 21's note presents an extra count-only scan of the author log as within C12; 1 claim checked, 1 confirmed); routed to the executor's verify and /fix; not converged.
- 2026-11-06 — Round 24 — codex gpt-6-astra medium cross-family peer re-check, H4 code slice (pass stage-7.p1, peer round 2 of cap 5; composer-recorded from the read-only peer's log) over round 22's fix — round 22's fix confirmed; 1 LOW (PR-LOW-001 docs-only: the stage-7 leg x1 handoff bullet still carries round 21's corrected advice); routed to the executor's /fix; not converged.
- 2026-11-06 — Round 25 — codex gpt-6-astra medium cross-family peer re-check, H4 documents slice (pass stage-7.p2, peer round 2 of cap 5; composer-recorded from the read-only peer's log) over round 23's fix — the same LOW as round 24 (the leg x1 handoff duplicate); routed to the executor's /fix; not converged.
- 2026-11-06 — Round 26 — codex gpt-6-astra medium cross-family peer re-check, H4 code slice (pass stage-7.p1, peer round 3 of cap 5; composer-recorded from the read-only peer's log) over rounds 22 and 24's fixes — the C12 duplicate confirmed fixed; 1 LOW (PR-LOW-001 docs-only: Task 0.2b's composer Closed record still confines `render_report`'s change to the heading and amendments); routed to the executor's /fix; not converged.
- 2026-11-06 — Round 27 — codex gpt-6-astra medium cross-family peer re-check, H4 documents slice (pass stage-7.p2, peer round 3 of cap 5; composer-recorded from the read-only peer's log) over rounds 23 and 25's fixes — 1 LOW (PR-LOW-001 docs-only: two more unqualified C17 (b) compliance claims, Round 4's and Task 0.2b's Closed record); routed to the executor's /fix; not converged.
- 2026-11-06 — Round 28 — codex gpt-6-astra medium cross-family peer re-check, H4 code slice (pass stage-7.p1, peer round 4 of cap 5; composer-recorded from the read-only peer's log) over rounds 26–27's sweep — every qualified record confirmed; 1 LOW (PR-LOW-001 docs-only: Round 8's "permitted-symbol compliance" left unqualified); routed to the executor's /fix; not converged.
- 2026-11-06 — Round 29 — codex gpt-6-astra medium cross-family peer re-check, H4 documents slice (pass stage-7.p2, peer round 4 of cap 5; composer-recorded from the read-only peer's log) over rounds 26–27's sweep — 0 findings (18 claims checked, 18 confirmed); **CONVERGED** (pass stage-7.p2).
- 2026-11-06 — Round 30 — codex gpt-6-astra medium cross-family peer re-check, H4 code slice (pass stage-7.p1, peer round 5 of cap 5; composer-recorded from the read-only peer's log) over round 28's fix and a whole-plan sibling search — 0 findings (20 claims checked, 20 confirmed); **CONVERGED** (pass stage-7.p1). H4 converged on both slices.

## Review Findings Log

### Round 1 — 2026-11-06
Source: codex gpt-6-astra high plan peer-review (composer-recorded verbatim from the read-only peer's log `.cursor/loops/validation-run8-plan-peer-r1.log`; the peer's sandbox cannot append — v32 recovery)

**PR-HIGH-001 — Both active plans claim the same blind set and run**
Materiality: build-affecting

`.cursor/plans/plan-validation-run8.md:185,213,274,277` claims run 8 on `heldout-5`, rule v5, unchanged `medium`, and shadow-off on installed 0.3.5. `.cursor/plans/plan-gpu-decoding.md:177,202,411,451` claims the same set and run under rule v4 with `large-v3@cuda`, potentially changed guard/threshold constants, version 0.3.6, and different failure/P.5 dispositions. Running one loop at a time does not resolve this. CPU-first consumes the blind set; GPU-first also invalidates C17’s empty-history check and requires reassessing the run-7 derivation and installed-pipeline assumptions. GPU outcomes (ii)/(iii) avoid its run-number claim but still require C17 reconciliation.

Proposed amendment: Add a blocking practitioner `[decision]`, cross-linked in both plans, establishing execution order, run numbering, ownership of one shared pre-registered blind evaluation used once or a later fresh set, the applicable rule and decoding freeze, and the installed-version/register/P.5 handoff.

**PR-MED-001 — The report-derived ambiguity rule cannot identify silent R1 reliably**
Materiality: build-affecting

D5 at `.cursor/plans/plan-validation-run8.md:177` classifies an ambiguous wrong R1 fact as silent when the encounter’s silent count exceeds its omitted R1 members. However, `desktop/src/scribe_desktop/validation.py:1052` counts silent omissions across **all** facts, while the Facts renderer at `:3519–3531` omits `silently_omitted_somewhere`. An unrelated non-R1 omission can therefore cause a false silent classification; multiple ambiguous R1 facts also cannot be individually distinguished from the aggregate. Reproducing rule-v3 totals does not establish the individual split because v3 combines both R1 kinds. The six claimed run-7 members are unambiguous, so this unsupported fallback is unnecessary.

Proposed amendment: Have Task 0.3 assert the claimed unambiguous R1 membership and reconcile encounter totals, refusing any unresolved ambiguous assignment instead of inferring it from aggregate counts.

**PR-MED-002 — Counterfactual equivalence labels discard meaningful rule differences**
Materiality: build-affecting

D1 and Task 0.2b (`.cursor/plans/plan-validation-run8.md:153,261`) prescribe an unconditional “= rule v4’s verdict” label and neutralise `r1_marked_reported` on both sides of `rule_v2_counterpart`. The generic loader accepts other thresholds and rows (`desktop/src/scribe_desktop/validation.py:2318–2350`). Resetting report flags cannot make those thresholds equal v4’s: one marked R1 fact fails a custom zero ceiling while passing v4’s ceiling of two. Likewise, neutralising `True` on a v2-known row hides a substantive counting difference from the comparison at `:2439–2457`. The six fixed v5 rows themselves are compatible.

Proposed amendment: Guard historical-equivalence labels with comparisons of verdict-relevant fields, normalising `False` and `None` together but retaining `True` as a substantive difference, and pin both mismatching cases.

**PR-MED-003 — The stated meaning of PASS exceeds the fixed rule**
Materiality: build-affecting

`.cursor/plans/plan-validation-run8.md:42` says a pass means every recogniser-wrong fact was marked and nothing reached the note unseen. D1 at `:149–151` nevertheless permits one silent R1 fact and one R3 encounter, reports uncertainty without gating it on the blind row, and gates material wrong facts rather than every fact. The actual gate preserves these allowances through `material_wrong_v2`, `silent_omission_v2` and class ceilings (`desktop/src/scribe_desktop/validation.py:937–946,2619–2626,3131–3136`). The categorical assurance therefore misstates the acceptance being presented for shadow-off.

Proposed amendment: Replace that assurance with the exact material-fact guarantees and explicitly include the permitted silent-R1, R3 and reported-uncertainty residues in the PASS explanation and P.5 acceptance.

**PR-MED-004 — Author-overlap reporting precedes its specified computation**
Materiality: build-affecting

`.cursor/plans/plan-validation-run8.md:172` defines overlap using material-fact token sequences “by the id-only script”; P.1 at `:274` requires every band outcome recorded, but P.3 at `:276` reserves the overlap read and diagnosis until later. Computing overlap necessarily reads fact tokens; count-only output does not make the input read id-only. This is a missing computation/sequence contract, not evidence that a pre-run blindness breach has already occurred.

Proposed amendment: Specify the count-only overlap calculation at P.3, distinguish its content-reading input from its output, and mark the P.1 overlap result pending until that task completes.

**PR-LOW-001 — The report and test-location map contains incorrect descriptions**
Materiality: record-only

`.cursor/plans/plan-validation-run8.md:108,118,261` reverses the report-pin identities: `desktop/tests/test_validation_harness.py:2513` is the v4 label test, including `tail[11]` at `:2543`; `:2673` is the whole v3 `heldout-4` report. Separately, plan lines `:106,151` describe `EncounterMetrics.r1_facts` as an encounter-table count, but the complete table headers at `desktop/src/scribe_desktop/validation.py:3364–3372` contain no R1 column. Neither mistake requires changing the intended report layout.

Proposed amendment: Correct the v3/v4 test labels and describe `r1_facts` as the combined metric property, with printed class counts located in the residue section.

Materiality: 5 build-affecting / 1 record-only / 0 invalid

**Dispositions (the planning session, 2026-11-06; every finding verified against the plan and the code at `9bdafa7`):**
- PR-HIGH-001 — ACCEPTED, verified (`plan-gpu-decoding.md:2, 177, 202, 411, 451` read; it claims `heldout-5`, predictions v4, run 8, 0.3.6 and a decode change). Amended: Task 0.0 `[decision]` (options A / B, blocks 0.2a–P.4′), the Plan Lineage line, the Agreed Scope, Flow 1, the Accepted Assumption's trigger, the Acceptance and the handoff note. The GPU plan's own lineage line is NOT written here (another session's committed plan — owed with the decision).
- PR-MED-001 — ACCEPTED, verified (`validation.py:1052` sums every fact; the Facts renderer `:3519-3531` prints `ambiguous`, never `silently_omitted_somewhere`). Amended: D5's per-fact rule refuses an ambiguous R1 member instead of inferring; the scratch asserts the six members by id first; Task 0.3 and the Codebase Integration Note on the split updated.
- PR-MED-002 — ACCEPTED, verified (`rule_v2_counterpart` `:2453-2457` neutralises `gate` only; `PassRule` admits any schema-4 thresholds). Amended: the fourth verdict prints `rule v5 with marked R1 counted` with no "= rule v4" claim (the equality is C18's pin and a document statement); `rule_v2_counterpart` treats `False` / `None` as equal and `True` as `differs`, pinned both ways; D1, the integration note and Task 0.2b updated.
- PR-MED-003 — ACCEPTED, verified (`rule_failures` `:2619-2626`, `run_passed` `:3131-3136`, rule v4's `heldout-5` row). Amended: the Honest forecast's "what a pass means" lists the exact guarantees and the kept allowances; D7's acceptance per class carries them.
- PR-MED-004 — ACCEPTED, verified (the tail script parses each script in process; a token overlap reads the statements). Amended: D4 computes the author-overlap band at P.3 by a count-only script; P.1 records it "pending P.3"; C12 names the tail script's in-process reading.
- PR-LOW-001 — ACCEPTED, verified (`test_validation_harness.py:2513` is the rule-v4 label test with `tail[11]` at `:2543`; `:2673` is the rule-v3 `heldout-4` report; the encounter table `:3364-3372` has no R1 column). Amended: Files / Symbols, the integration note, D1 and Task 0.2b corrected.
- Amendment-application discipline: each edit re-read from disk after writing (a single exact match, replaced once); contradicted siblings swept — the "(= rule v4's verdict)" string at its three sites, the "neutralised to None on both sides" claim at its three sites, the pin identities at four sites, the author-overlap wording at D4 / C12 / P.1 / P.3, the pass-meaning sentence and D7's acceptance.
- Round verdict: 6 findings, 5 build-affecting / 1 record-only / 0 invalid; all applied. Not converged (round 1 never converges); round 2 confirms the amendments and attacks the classes (the two-plan collision; report-derived predictions; label and counterpart equivalence claims; pass-meaning over-statement; blind-set reads; pin-location errors).


### Round 2 — 2026-11-06
Source: codex gpt-6-astra high plan peer-review (composer-recorded verbatim from the read-only peer's log `.cursor/loops/validation-run8-plan-peer-r2.log`)

- **PR-HIGH-001: not fixed —** Task 0.0 exists, but its completion condition releases execution before the operative cross-plan conflicts are reconciled; see PR-HIGH-002.
- **PR-MED-001: confirmed** — D5 refuses ambiguous wrong R1 members and asserts the six expected members before prediction.
- **PR-MED-002: confirmed** — the unconditional printed equality is removed; counterpart comparison preserves `True` as a substantive difference.
- **PR-MED-003: confirmed** — the forecast and D7 disclose the retained PASS allowances.
- **PR-MED-004: confirmed** — overlap computation waits until P.3, with P.1 recording it as pending.
- **PR-LOW-001: confirmed** — the report-pin identities and `r1_facts` description are corrected.

**PR-HIGH-002 — Task 0.0 can unblock execution before the selected order is executable**  
Materiality: build-affecting

`.cursor/plans/plan-validation-run8.md:316` requires only a recorded choice and two lineage lines. Under B(i), however, the promised later rebase must replace tasks that still require six rows, an unused `heldout-5`, run-7-derived predictions and installed 0.3.5 (`:176`, `:212`, `:318–322`, `:335`). Under B(ii)/(iii), only C17(a)’s baseline changes; C17(b)/(c) still compare against `170345d` and prohibit retained harness changes (`:213`). GPU D6 also permits changed shared constants and final CPU measurements, which require reconciling the run-7 prediction and installed-pipeline assumptions (`.cursor/plans/plan-gpu-decoding.md:177`).

Under A, the GPU plan’s operative run still names rule v4, run 8 and `heldout-5` (`plan-gpu-decoding.md:411`). A lineage sentence does not update its successor set, rule rows, blind-set machinery, predictions or document handoff. C9 serializes loops; it does not reconcile these dependencies.

Proposed amendment: Keep Task 0.0 blocking until both plans’ operative contracts are amended and reviewed for the chosen order, including successor set/run ownership, prediction sources, all C17 comparisons, shared-file changes and the validated installed configuration; make B explicitly pause-and-replan after the GPU outcome.

**PR-LOW-002 — The new verdict label is hardcoded despite supporting other schema-4 rule names**  
Materiality: build-affecting

`.cursor/plans/plan-validation-run8.md:153,319` prescribes `rule v5 with marked R1 counted` on every schema-4 report. The unchanged `PassRule.label` returns `v5` for `rule-v5`, but `v4` for an otherwise named schema-4 rule and `v6` for `rule-v6` (`desktop/src/scribe_desktop/validation.py:2367–2370`). Existing report sites use that derived label (`:3217`, `:3234`, `:3290`); implementing the prescribed literal would mix rule names within a supported report.

Proposed amendment: Derive the new verdict’s name from `rule.label` and add a schema-4 report pin with a non-v5 label.

**PR-LOW-003 — C12 excludes machine reads that P.1 requires**  
Materiality: record-only

`.cursor/plans/plan-validation-run8.md:209` permits only the lint runner and tail script to read the set before P.3, while P.1 explicitly builds and evaluates it (`:332`); P.3 additionally calls itself the “ONE task that reads it” (`:334`). This contradicts the prescribed workflow, rather than establishing a blindness breach. The presence check only enumerates filenames (`desktop/tests/fixtures/heldout_transcripts.py:975–977`), and the report prints classifications rather than script statements (`desktop/src/scribe_desktop/validation.py:3519–3531`).

Proposed amendment: Explicitly permit P.1’s builder/harness reads and the practitioner’s content-free report review, while reserving examination of script content and diagnosis for P.3.

Verification notes:

- No additional D5 finding survives: excused identities, per-encounter warning loads, uncertainty denominators and raw counts are recoverable from the report; aggregate-backed prediction objects avoid inventing unprinted alignment flags.
- Returning `self` when no row reports marked R1 is consistent with an unchanged counterfactual verdict.
- The historical amendments paragraph and repository-file equality pin do not establish another unsupported equivalence claim.
- The 139-consultation count is correct: 50 + 22 + 22 + 23 + 22. “About 700 facts” is absent from this plan. The register phrase count is 64.

Ten additional locator checks, all accurate:

1. `validation.py:2360` — rule-label property.
2. `validation.py:2377` — `without_r1_exemption`.
3. `validation.py:2385` — `set_row`.
4. `validation.py:2674` — `ClassCount`.
5. `validation.py:2690` — `class_counts`.
6. `validation.py:3121` — `run_passed`.
7. `test_validation_metrics.py:3395` — `TestRuleV3`.
8. `heldout_transcripts.py:1011–1020` — blind `heldout-5` fixture row.
9. `conftest.py:98–106` — `blind_run_refusal`.
10. `test_pilot_docs.py:117` — `h5-` register admission.

Review was read-only at `9bdafa7`; no tests or builds ran. A stale GPU-plan line-range read included excluded findings-log text; that material was not used as evidence.

Materiality: 2 build-affecting / 1 record-only / 0 invalid

**Dispositions (the planning session, 2026-11-06; verified against the plan and the code at `9bdafa7`):**
- PR-HIGH-002 — ACCEPTED, verified (Task 0.0's Done-when released 0.2a on a recorded choice; C17 (b)/(c) still read `170345d`; the installed-configuration assumption ignored option B). Amended: Task 0.0's Done-when now requires BOTH plans' operative tasks amended and reviewed for the chosen order (run / set ownership, prediction sources, every C17 base, the installed configuration, the ten shared files), option B = `Paused` and re-planned after the GPU plan's Task D; C17's base parametrised for (a), (b), (c); the Accepted Assumption on 0.3.5 voided under B (i)/(ii). PR-HIGH-001 thereby closed.
- PR-LOW-002 — ACCEPTED, verified (`PassRule.label` `:2367-2370`; the derived label at `:3217`, `:3234`, `:3290`). Amended: the fourth verdict's name comes from `PassRule.label`; a non-v5 schema-4 report pin added (D1, Task 0.2b).
- PR-LOW-003 — ACCEPTED, verified (`script_paths()` `:975-977` globs file names; the Facts renderer prints no statement). Amended: C12 re-worded to content examination, naming P.1's machine reads and the content-free report review; P.3 "examines its content".
- Amendment-application discipline: each edit re-read from disk (one exact match, replaced once); siblings swept — `170345d` at C17 and the baseline table (the Accepted Assumption and D5 keep it as the dated reproduction commit, which is history, not the base); the fourth verdict's name at D1 and 0.2b; "reads it" at P.3.
- Round verdict: 3 new findings, 2 build-affecting / 1 record-only / 0 invalid; all applied; five round-1 fixes confirmed, PR-HIGH-001 superseded by PR-HIGH-002 and closed with it. Not converged (new build-affecting findings); round 3 confirms.

### Round 3 — 2026-11-06
Source: codex gpt-6-astra high plan peer-review (composer-recorded verbatim from the read-only peer's log `.cursor/loops/validation-run8-plan-peer-r3.log`)

- **PR-HIGH-002: confirmed** — Task 0.0 requires both plans’ operative amendments and reviews before release (`.cursor/plans/plan-validation-run8.md:381`); all C17 comparisons use the selected base (`:213`), and the installed-configuration assumption is explicitly conditional (`:98`).
- **PR-LOW-002: confirmed** — D1 and Task 0.2b derive the fourth verdict’s label and require a non-v5 schema-4 report pin (`:153`, `:384`).
- **PR-LOW-003: not fixed —** C12 and P.3 are corrected, but Acceptance retains the superseded “read by no leg” requirement (`:238`).

**PR-LOW-004 — Acceptance retains contradictory blindness wording**  
Materiality: record-only

`.cursor/plans/plan-validation-run8.md:238` requires “`heldout-5` read by no leg before run 8,” while C12 explicitly permits machine reads (`:209`) and Task 0.5 requires the tail script and lint runner before that run (`:387`). The operative workflow is clear; its acceptance summary still contradicts it.

Proposed amendment: Replace that Acceptance phrase with a reference to C12’s permitted machine reads and reservation of content examination for P.3.

No additional build-affecting finding survived verification across sequencing, report contracts, constraints, or cross-plan dependencies.

Review limitation: a broad GPU-plan search returned excluded findings-log lines; they were not used as evidence. No files changed, and no tests or builds ran.

Materiality: 0 build-affecting / 1 record-only / 0 invalid

**Dispositions (the planning session, 2026-11-06):**
- PR-LOW-004 — ACCEPTED, verified (the Acceptance line kept round 0's "read by no leg" after C12 was re-worded in round 2). Amended: the Acceptance cites C12's permitted machine reads and P.3's content examination. Siblings swept: no other "read by no leg" remains; D4's "Blind (C12)" line and Task 0.5 already name the runner and the tail script.
- PR-LOW-003 — closed with it (round 2's amendment stands; its last sibling fixed here).
- Round verdict: 0 build-affecting / 1 record-only / 0 invalid; the record-only finding applied. **CONVERGED** (round 3, under the cap of 5): zero new build-affecting findings on a round that confirmed every prior amendment. The pass ends here; nothing committed — Task 0.0 and the plan's commit are the practitioner's.

### Round 4 — 2026-11-06
Source: Claude Code (`/review-loop` round 1 of cap 3, stage-1 executor leg x2, `claude-opus-5-5`) — Task 0.2a only; the first build round of run `validation-run8-20261106-144633-d8ae`.
Primary baseline: `9884f04` (HEAD; the 0.2a work is uncommitted). Changed files: `desktop/src/scribe_desktop/validation.py`, `desktop/tests/test_validation_metrics.py`, `validation/rules/rule-v5.json` (new), this plan (bookkeeping; only its 0.2a lines reviewed). The diff read in full; the touched regions of `validation.py` (`RULE_SCHEMA_VERSION`, `SetCeilings`, `PassRule` through `set_row`, `rule_v2_counterpart`) and of the test file (`TestRuleV2`'s refusal table and both-ways tests, the fixtures, `TestRuleV3`'s file test, `TestRuleV4`'s label tests, `TestRuleV5`) read in full. Composer-run suite on the build: 9471 passed, 0 failed, 9 skipped.
Round status: Closed (0 pending)
Checked: rule-v5.json against D1 and rule-v4.json key by key (top level identical but `schema_version` 3 → 4 and `rule_name`; every row rule v4's with `r1_marked_reported` appended — `false` × 5, `true` on `heldout-5`; LF, no NUL; C18's test excludes the field on both sides); C2 — no older rule file, `validation/config` or script in the diff; every new predicate both ways — the exemption at schema 4 refused missing / null and accepted true / false, the new field refused non-null on schemas 2–3 and accepted null there, required on every schema-4 row (absent, null, a second row missing it) and accepted true / false, a non-bool refused; schema 1 refused by "holds no set ceilings" before the field is read (a schema-1 rule holds no row); the old "a schema-3 rule needs …" pins still match the f-string; `>= 3` / `>= 4` against `Literal[1, 2, 3, 4]`; no reader of `schema_version` outside `validation.py` in `desktop/src` or `scripts/`; a schema-4 rule under the pre-0.2b report code — `_verdict_lines`, the heading, the amendments, `_residue_section`, `main`'s refusals — takes no schema-3 branch and raises nothing (the suite green); nothing of 0.2b started (no `FactOutcome` property, no `ClassCount` field, no `counting_marked_r1`, no `rule_v2_counterpart` change, no report string) — the docstrings 0.2b's task line lists (`set_row`'s "schema-2 or schema-3", `exempts_r1_lines`'s "schema 3") left for 0.2b; the `SetCeilings` docstring describing the reading 0.2b builds is the planned two-commit split, recorded on the task line, not a finding. C17 (b): `validation.py`'s hunks since `170345d` are the `RULE_SCHEMA_VERSION` comment and value (named by Task 0.2a; not decode or routing), `SetCeilings` (docstring and field), `PassRule`'s docstring and `schema_version`, `_check_sets` — inside the permitted list. (`[2026-11-06, peer rounds 26–27 PR-LOW-001]` But for the `RULE_SCHEMA_VERSION` comment and value, which C17 (b)'s literal list does not name. Task 0.2a authorised them, they are inert, and C17's text is unchanged; see round 22's `/fix` notes.)
Round classification: 1 🆕 / 0 ⚡ / 0 🔁.
- **[LOW]** LOW-001: `desktop/src/scribe_desktop/validation.py:2277` — the `SetCeilings` docstring opened "One set's row of a schema-2 rule" above the new sentence on schema 4's field (the opening predates rule v3; the task names this docstring) — 🆕 — Triage: Fix-now; Decision: Applied ("of a schema-2 or later rule", rewrapped).
Missed-issue pass: re-read `_check_sets`'s order of checks (exemption, schema 1, the set count, then per row: name, the new field, R2) and `_RULE_V5`'s construction (`_RULE_V3`'s dump with every row's field set; the fixture test pins it back to `_RULE_V3`'s rows); result: none.
Finding verification: 1 candidate; 0 dropped; 0 downgraded.
/fix notes: applied 2026-11-06 by the stage-1 executor (leg x2); ruff and mypy green after; docstring only, pytest composer-owned.

**CONVERGED (round 4: no CRIT / HIGH / MED; one 🆕 LOW, applied).** `/review-loop` converged on its first round (plan round 4; cap 3). Next by the loop config: the composer's suite re-run, then the codex peer pass (cadence every-phase).

### Round 5 - 2026-11-06 - Stage-1 (Task 0.2a rule v5 loader), independent cross-family codex peer review (pass stage-1.p1)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Task 0.2a working-tree diff against 9884f04; rule-v5.json against D1 and rules v3/v4; schema validation, loader tests, current report compatibility, C17 boundaries, and Round 4's applied fix. Static reading only; no tests run or files written. Task 0.2b's explicitly deferred behavior excluded.
  - `[2026-11-06T21:44:32+11:00, peer round 28 PR-LOW-001 sweep]` The round's 0 findings over "C17 boundaries" passed the `RULE_SCHEMA_VERSION` comment and value. Task 0.2a authorised them, but C17 (b)'s literal list does not name them. They are inert, and C17's text is unchanged; see round 22's `/fix` notes.

#### Findings
- Verification counts: 6 claims checked, 6 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

**CONVERGED (round 5: 0 findings; transcribed by the composer from the peer's log, `.cursor/loops/stage-1-peer-r5.log`).**

### Round 6 — 2026-11-06
Source: Claude Code (`/review-loop` round 1 of cap 3, stage-2 executor leg x2, `claude-opus-5-5`) — Task 0.2b only.
Primary baseline: `ba71ff5` (HEAD; the 0.2b work is uncommitted). Changed files: `desktop/src/scribe_desktop/validation.py`, `desktop/tests/test_validation_harness.py`, `desktop/tests/test_validation_metrics.py`, this plan (bookkeeping; only its 0.2b lines reviewed). `git diff ba71ff5 -- desktop/src/scribe_desktop/validation.py` read in full, hunk by hunk; the new tests read in full. Composer-run suite on the build: 9613 passed, 0 failed, 9 skipped (712 s).
Round status: Closed (0 pending)
Checked:
- **The both-case precedence.** `residue_r1_silent` is `residue_r1 and silent_omission`. `residue_r1_marked` adds `verdict == "wrong" and not silent_omission`. `residue_r1` requires material and (wrong or silent omission), so every R1 fact is exactly one kind, and a wrong fact silently omitted on another alignment is silent. Pinned on `_R1_BOTH`: counted under both row kinds and never reported.
- **Schema-3 reports byte-unchanged.** Every new branch is gated `schema_version >= 4`, on a row's `r1_marked_reported is True` (always None below schema 4), or `label == "v5" and schema_version >= 4`. The `== 3` → `>= 3` sites are equal for schema 3. The v4 sentence's added `or schema_version >= 4` is false for schema 3. The `listed()` refactor prints the old members string. The rule-v3 / rule-v4 whole-report and label pins are unchanged, and the mirror pin covers rule v3 / v4 reports on outcomes holding both kinds.
- **No printed equality with rule v4.** The second verdict line and the heading name `rule {label} with marked R1 counted` only. The `heldout-5` whole-report pin covers every line, and the `rule-v6-test` pin asserts no "= rule v4". The equality is held in tests only (`test_marked_r1_counted_is_rule_v4s_verdict`, 15 shapes × six rows).
- **`rule_v2_counterpart` both ways.** `gate` is neutralised on both sides, and a `False` `r1_marked_reported` becomes `None` on both sides. Rule v2's rows are None, so `False` → `same`. `True` stays `True` vs `None` → `differs`. Pinned on rule v5 (`same` × 4 / `no_row` × 2) and on a hand-built `scripts` `True` / `False`, in the function and in the report's wording.
- **Silent-only gating on a reporting row.** `class_breaches` → `class_counts` (`split` excludes marked members), which `run_passed` and `_verdict_lines`' `set_level` read. Rule failures per encounter are unchanged (R1 excuses its own fact as before). Pinned: the reporting row's ceiling at 1 and 2 silent facts with 0–5 marked; the blind row's report set-level at 1 and 2 silent facts with 3 marked.
- **Every new line on every schema-4 row and none on schema 3.** The marked line is gated `>= 4` alone ("counted under the ceiling" on seen rows, "reported, no ceiling" on the blind one). The R1 row's name changes only where the row reports (D1). The fourth verdict and its heading entry are gated `>= 4`. Pinned on `heldout-5`, `heldout-4`, `scripts` (True) and the nothing-measured case.
- **D5's allowed-to-differ list.** On `heldout-4` the rule-v5 report equals rule v3's on the same outcomes at the tables, the checker tally and the Facts table (`lines[8:27] == v3_lines[7:26]`). In the residue section only the heading, the marked line and the after-classes label differ. The excused-lines line is the same.
- **C16.** `rule-v5.json` and rules v1–v4 are untouched (no diff).
- **C17 (b).** The hunks are confined to the permitted symbols, plus docstrings Task 0.2b names: `EncounterMetrics` ×2, `rule_failures`, `run_passed`. `evaluate_encounter` is untouched (the task-line note). (`[2026-11-06, peer rounds 26–27 PR-LOW-001]` Not so. Peer round 7 found a helper and five docstring and comment edits outside the list; they were reverted or folded. `render_report`'s docstring, Task 0.2b's, also sits outside C17 (b)'s literal list, which names the heading and the amendments. It is inert, and C17's text is unchanged; see round 22's `/fix` notes.)
- **C18.** Pinned by 0.2a's field-by-field test, unchanged.
- **No logging.** No new log or print call.
Round classification: 2 🆕 / 0 ⚡ / 0 🔁.
- **[LOW]** LOW-001: `desktop/src/scribe_desktop/validation.py` (render_report's rule-v5 sentence gate) — the leg-x1 deviation (ii), `label == "v5" and schema_version >= 4`, was pinned on one side only: schema 4 named v5 prints it, schema 4 named v6 does not. Nothing pinned that a schema-3 file labelled "v5" prints no schema-4 claim, so the gate's "every predicate both ways" rule was unmet — 🆕 — Triage: Fix-now; Decision: Applied (`test_a_schema_3_rule_named_v5_prints_no_rule_v5_sentence`: a schema-3 `rule-v5-test` from `rule-v4.json` prints rule v3's history alone, no "schema 4", no "marked R1", three verdict lines).
- **[LOW]** LOW-002: `.cursor/plans/plan-validation-run8.md:4` — leg x1's edit to the Overall Progress line put "0.2b built, suite owed —" before the list of the 15 buildable tasks, so it read as if that list were what was built — 🆕 — Triage: Fix-now (record-only); Decision: Applied ("2 of 15 buildable tasks done — 0.1 and 0.2a; 0.2b built and in review, not counted. The 15: …").
Missed-issue pass: re-read `counting_marked_r1` (a `sets` None rule is returned as is; key order kept; the input never mutated), `_r1_marked_members` (skips measured-less outcomes; fact order), the heading's and `_verdict_lines`' separate `counting_marked_r1()` calls (the same outcomes, the same result; the existing `without_r1_exemption` pattern), and the v5 sentence's `set_row(set_name)` (only reached with `set_name` given); result: none.
Finding verification: 3 candidates; 1 dropped (`residue_r1_marked`'s docstring "under a review mark on every alignment" — it matches `FactOutcome`'s own class docstring and D1's wording; the honest limit is stated in D1, not overstated here); 0 downgraded.
/fix notes: applied 2026-11-06 by the stage-2 executor (leg x2). ruff and mypy green after. LOW-001 is a new test, so the composer re-runs `desktop full pytest`.

**CONVERGED (round 6: no CRIT / HIGH / MED; two 🆕 LOWs, applied).** `/review-loop` converged on its first round (plan round 6; cap 3). Next by the loop config: the composer's suite re-run, then the codex peer pass (cadence every-phase).

### Round 7 - 2026-11-06 - Stage-2 (Task 0.2b rule v5 reading and report), independent cross-family codex peer review (pass stage-2.p1)

- Round status: Closed (0 pending) — PR-LOW-001 confirmed and applied by the stage-2 executor, leg x3, 2026-11-06T16:08+11:00
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Task 0.2b working-tree diff against ba71ff5, named rule files, permitted neighbours and plan sections; Round 6’s two fixes verified landed. Read-only; no tests run.

#### Findings

- **PR-LOW-001** (LOW, docs-only, `.cursor/plans/plan-validation-run8.md:479`): The C17 compliance record exceeds C17(b)’s explicit permitted-symbol list. The new standalone `_r1_marked_members` helper is outside that list, as are the changed `EncounterMetrics`, `rule_failures` and `run_passed` docstrings and `RULE_V2_RATIFIED` comment. These changes do not alter decoding or routing, but the stated symbol-level check does not pass literally. - Evidence: C17(b), `:213`, requires the diff be “confined to” its enumerated symbols; the task record lists “`ClassCount` / `_r1_marked_members` / `class_counts`”; `desktop/src/scribe_desktop/validation.py:2756` adds `def _r1_marked_members(...)`. Recommendation: Fix-now - Reconcile C17(b) with the report-only helper and explicitly bounded comment/docstring edits, preserving every prohibited region. /fix decision: **(PR-LOW-001, CONFIRMED, 🆕 LOW record-and-code, Fix-now — conform the diff to C17 (b) as written; C17's text unchanged)**. Verified 2026-11-06T16:08+11:00 by the stage-2 executor (leg x3) against the working tree. C17 (b) lists `SetCeilings` / `PassRule` / `_check_sets` / `counting_marked_r1` / `rule_v2_counterpart`, the two `FactOutcome` properties, `ClassCount` / `class_counts`, `_verdict_lines` / the heading / the amendments / `_residue_section`, the `_parser` and `main` strings and the `h5-` rows. Outside that list, the diff held:
  - the module-level helper `_r1_marked_members`;
  - the `EncounterMetrics` docstrings (two hunks);
  - the `RULE_V2_RATIFIED` comment;
  - the `rule_failures` and `run_passed` docstrings.

  The finding is real as a literal check, though none of these touches decoding or routing. Changing C17 (b)'s list is a practitioner decision, so the diff was made to fit the list instead:
  - the helper is folded into the two permitted readers: `class_counts` collects the marked facts in its own loop, and `_residue_section` derives them inline on a counting row;
  - the five out-of-list docstring and comment edits are reverted, byte for byte, to `ba71ff5`. They stay stale ("schema 3" as the newest), with `evaluate_encounter`'s, for one docstring-only commit after P.1, when C17 lapses.

  Behaviour is unchanged. `git diff ba71ff5 -- desktop/src/scribe_desktop/validation.py` now holds 19 hunks, every one in C17 (b)'s list. ruff and mypy green; the suite re-run is owed. (`[2026-11-06, peer rounds 26–27 PR-LOW-001]` But for `render_report`'s docstring, which sits in the heading's hunk. C17 (b)'s literal list names the heading and the amendments, not the docstring. It is inert, and C17's text is unchanged; see round 22's `/fix` notes.)

- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 8 - 2026-11-06 - Stage-2 (Task 0.2b rule v5 reading and report, re-check), independent cross-family codex peer review (pass stage-2.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Task 0.2b diff against ba71ff5, named rule files, permitted neighbours and plan sections. Confirmed Round 6–7 fixes, unchanged C17 text, permitted-symbol compliance, behavior-preserving helper fold, R1 split and ceilings, comparison verdicts, schema-3 report preservation, schema-4 output and test assertions. Static reading only; no files written, tests run or network commands.
  - `[2026-11-06T21:44:32+11:00, peer round 28 PR-LOW-001]` "Permitted-symbol compliance" was not literally true. The `render_report` heading hunk of the 0.2b diff also changes the function's docstring (Task 0.2b), and C17 (b)'s literal list names the heading and the amendments, not the docstring. The docstring is inert, and C17's text is unchanged; see round 22's `/fix` notes. `RULE_SCHEMA_VERSION` (Task 0.2a) lies outside this round's diff against `ba71ff5`.

#### Findings

- Verification counts: 8 claims checked, 8 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 9 — 2026-11-06
Source: Claude Code (`/review-loop` round 1 of cap 3, stage-3 executor leg x2, `claude-opus-5-5`) — Task 0.3 only.
Primary baseline: `d15a28f` (HEAD; the tree is clean but for this plan, and the script is git-ignored). Reviewed: `.cursor/loops/run8-predict.py` read in full; `.cursor/loops/run8-predict-out.txt` (the composer's run: exit 0, 153 lines); Task 0.3's record on this plan; D5, Task 0.3's line, C12, C17. Read only for the cross-check: run 7's five reports and HEAD's `render_report`, `_verdict_lines`, `_residue_section`, `class_counts`, `FactOutcome`, `EncounterMetrics`.
Round status: Closed (0 pending)
Checked:
- **The record matches the output.** Every verdict, failing id and reason, residue member, ceiling, within, after-class and excused count, surfaced / expected, load figure, Check 6 entry and mismatch list on Task 0.3 was re-read against `run8-predict-out.txt` lines 9–152, set by set. The six R1 kinds, the hashes and the commit were also checked against lines 3–6. No difference.
- **The parse cannot silently pass a misread the predictions rely on.** Every input to the rule-v5 lines is in a compared region of the rule-v3 reproduction:
  - each fact's kind, material, verdict, warned, surfaced, not-transcribed, ambiguous and classes — the Facts table, byte for byte;
  - each encounter's unsupported lines, checker failure count, fact counts, silent omissions, uncertainty missed and Rule cell — the encounter rows;
  - the tally (the load and Check 6's count) — the checker warnings;
  - the excused lines, the references and the joined-run totals — the residue section;
  - the set-level errors — the heading and verdict lines.

  The four masked columns and the TOTAL seconds are read by no rule and no rule-v5 line. `silently_omitted_v1` / `_v033` / the acoustic flag are not inputs to `class_counts`, `_verdict_lines` or `_residue_section`. The R1 split reads `silent_omission`, whose only unprinted input (`silently_omitted_somewhere`) is pinned by the unmasked "Silent omissions" cell and by the deficit refusal.
- **The refusals are real.**
  - `assert_r1_members` raises exit 2 on an R1 member `wrong` with Ambiguous `yes` before any object is built.
  - It compares the found `{(id, index): kind}` to D5's six by EXACT equality (a seventh, a missing or a re-kinded member → exit 4; a duplicate → exit 4).
  - `assert_kinds` re-reads every R1 fact through `residue_r1_silent` / `residue_r1_marked`.
  - Nothing prints before all three steps and the reproduction pass.
- **Nothing printed carries a script's words.** The printed lines are:
  - HEAD's rendered heading, verdict and residue lines (ids under `ID`'s pattern, codes, integers, fixed text);
  - Check 6 (ids, integers);
  - the category summary (fixed names, line numbers);
  - hashes, the commit, and Stop messages (fixed text, set names, ids, line numbers — never a line's text or an exception message).
- **C12 / C17.** No path under `validation/heldout-5`, `run8-reports/` or a pickle is opened (the only reads are `REPORTS / report-<set>.md` for the five seen names and the two rule files). `git status --short` shows this plan alone; C17 (a) is empty since `170345d` (composer).
Round classification: 2 🆕 / 0 ⚡ / 0 🔁.
- **[LOW]** LOW-001: `.cursor/loops/run8-predict.py` (`predictions`) — the rule-v5 verdict lines and the `### Residue classes` heading print with no blank line between them (the render's blank at `residue_at - 1` was skipped), so the output's Markdown runs the heading into a list — 🆕 — Triage: Fix-now; Decision: Applied (`print()` before the residue lines; the output gains one blank line per set).
- **[LOW]** LOW-002: `.cursor/loops/run8-predict.py` (`category`) — the render-difference check was broader than D5's list. A changed rule-v1 verdict line would have counted as a listed "verdict line" (D5 lists verdict lines 1–3 only). A changed R1 row on a seen set would have counted as a listed "R1 row" (D5 lists it only where the row reports). Either difference would have passed exit 6 unflagged. On this run neither occurred: the changed lines are 1, 3, 4, 5, 8 and three residue lines, with no rule-v1 line and no R1 row — 🆕 — Triage: Fix-now; Decision: Applied (`category(line, r1_row_listed)` returns `other` for `- Rule v1 verdict ` and for `| R1 recogniser` unless `rule_v5.set_row(name).r1_marked_reported is True`; the docstring updated). No printed prediction changes.
Missed-issue pass: re-read `parse_tally` (order failing → expected, as the renderer), the Facts loop's bounds (`facts_at + 4` to `residue_at - 1`, the renderer's blank), `edit_distance` (WER never gated; both rules' threshold null, refused otherwise), the credit placement (`min(facts_left, material)`), `read_report`'s CRLF split (a lone LF or CR → exit 5), the mask range (rows and TOTAL only); result: none.
Finding verification: 3 candidates; 1 dropped (the header line's "byte for byte" over CRLF-split lines — the line contents are compared exactly and the terminator is the file's transport, stated on Task 0.3's record); 0 downgraded.
/fix notes: applied 2026-11-06T16:37+11:00 by the stage-3 executor (leg x2). The script changed, so the composer re-runs it and the record is re-checked against the new output. Expected: five more blank lines, the same predictions, exit 0.

**CONVERGED (round 9: no CRIT / HIGH / MED; two 🆕 LOWs, applied).** `/review-loop` converged on its first round (plan round 9; cap 3). Next: the composer's re-run of the script, then the codex peer pass (cadence every-phase) or the 0.3 commit as the loop config says.

### Round 10 - 2026-11-06 - Stage-3 (Task 0.3 predictions v5), independent cross-family codex peer review (pass stage-3.p1)

- Round status: Closed (0 pending) — PR-LOW-001 and PR-LOW-002 confirmed and applied by the stage-3 executor, leg x3, 2026-11-06T16:45+11:00; the script's re-run is owed (composer)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Task 0.3 script, current output and plan record against the five named run-7 reports, rules v3/v5 and permitted harness symbols; read-only review, no execution.

#### Findings

- **PR-LOW-001** (LOW, docs-only, `.cursor/plans/plan-validation-run8.md:601`): The run record still identifies the pre-fix artifacts. The current output has 158 lines; current SHA-256 values are script `1d838bef51194fc97383ec093465c7c10c948262ea450bccb88547df2cb9f95b` and output `41bd1c6591d1f4f020f6dc688cae931214bf700c69e1b95ee5e18ad0d0fdb94a`. The frozen prediction values match, but their artifact provenance is stale. - Evidence: “153 lines; script SHA-256 `83a8aa781d55b7ed905603b8cdf356408ce1f47b9f9feeafb4579b288997e777`, output SHA-256 `83df6f5e534458946d2dbac50f4dcd027f008f7409122e9ab3bf2db77c7e4a7d`”. Recommendation: Fix-now - Append the completed rerun record with current hashes and line count, preserving the earlier run as history. /fix decision: **(PR-LOW-001, CONFIRMED, 🆕 LOW record-only, Fix-now — applied)**. Verified 2026-11-06T16:45+11:00 by the stage-3 executor (leg x3): Task 0.3's run line named the first run only (153 lines, script `83a8aa78…`, output `83df6f5e…`), while the current output is the round-9 re-run (158 lines, `1d838bef…` / `41bd1c65…`, composer). Applied: the first run is kept as history and names its kept copy `run8-predict-out.r1.txt`; a "Re-run after review round 9" line records the current facts and the five-blank-lines `diff`; a "Re-run after peer round 10 (owed, composer)" line is the place for the next re-run's facts, since PR-LOW-002's fix changes the script.

- **PR-LOW-002** (LOW, test-harness, `.cursor/loops/run8-predict.py:652`): The allowed-difference check still admits changes outside D5’s precise allowances. It classifies whole replacement lines by prefix: changing an after-class count passes even though D5 permits only that line’s label to change. It also checks removed lines only when the old block is longer, so replacing an unlisted line with a listed line can conceal the removal. The current predictions show neither defect, but the guard does not enforce its stated contract. - Evidence: `changed.setdefault(category(v5[j], r1_row_listed), []).append(j + 1)` and `range(max(0, (i2 - i1) - (j2 - j1)))`; line 106 allows `("- After the classes ", "after-classes line")`, whereas plan line 179 permits “the after-classes line's label”. Recommendation: Fix-now - Compare both sides after normalising only D5’s permitted substitutions and accounting explicitly for the two permitted inserted lines; reject other changed values or removals. /fix decision: **(PR-LOW-002, CONFIRMED, 🆕 LOW scratch-tool, Fix-now — applied; no prediction changes)**. Verified 2026-11-06T16:45+11:00 by the stage-3 executor (leg x3) against `run8-predict.py`. Both defects were real.
  - **Prefix classification.** The check classified each changed rule-v5 line by its opening (`category(v5[j], …)`), so a changed count on the after-classes line, the residue heading or verdict line 1 or 3 would have passed as a listed line.
  - **Hidden removals.** It counted removed rule-v3 lines only when a replace block's old side was longer, so an unlisted line replaced by a listed one hid the removal.
  - Round 9's LOW-002 had narrowed the categories, not the comparison.
  - The current predictions are unaffected: the composer's `diff` and the re-run show the same eight lines.

  Applied: the difflib / prefix check (`D5_CATEGORIES`, `category`) is replaced by `d5_matchers` + `d5_differences`. Each rule-v3 line becomes one matcher, built from D5's permitted substitutions only:
  - **The heading:** the rule name and labels; its one added verdict `, rule v5 with marked R1 counted PASS|FAIL` must appear exactly once, before the without-exemption verdict, and is removed before an exact comparison.
  - **Verdict line 1:** the label and role, and the gate / reported sentence rebuilt from each rule's own rows as `_verdict_lines` prints it.
  - **Verdict line 3:** the label.
  - **The run information:** rule v5's must START with rule v3's and be longer (the amendments appended).
  - **The residue heading:** the label and role.
  - **The R1 row:** its name, only where the row reports.
  - **The after-classes line:** the label.
  - **Inserted:** exactly two lines — verdict line 2 by its fixed opening after verdict line 1, and the marked-R1 line (`counted under the ceiling` / `reported, no ceiling` by the row) after `- R1:`.
  - **Everything else** must be equal.

  A substitution whose old text is not in its line exactly once matches nothing. A line count other than D5's is "other". Every number in a transformed line is compared exactly. The printed category names, counts and line numbers are unchanged, so the output should be byte-identical to the round-9 output (exit 0). The composer re-runs it; the facts go on Task 0.3's "Re-run after peer round 10" line.

- Verification counts: 2 claims checked, 2 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 11 - 2026-11-06 - Stage-3 (Task 0.3 predictions v5, re-check), independent cross-family codex peer review (pass stage-3.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Task 0.3 script, output and frozen record; Rounds 9–10 fixes; five named run-7 reports, rules v3/v5, permitted harness symbols, D5/C12/C17 and working-tree status. Read-only verification; no script or test execution.

#### Findings

- Verification counts: 8 claims checked, 8 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 12 — 2026-11-06
Source: Claude Code (`/review-loop` round 1 of cap 3, stage-4 executor leg x1, `claude-opus-5-5`) — Task 0.4 only (plan text; no suite).
Primary baseline: `431a38e` (HEAD; the 0.4 record is uncommitted, and `git status --short` shows this plan alone). Reviewed: Task 0.4's record, read in full from disk against D1's `heldout-5` row and `validation/rules/rule-v5.json`, D3, D4, D7, the Goal (Honest forecast, the PR-MED-003 paragraph, the run-7 table), C12, C16, Task 0.3's frozen record and `.cursor/loops/run8-predict-out.txt`, and run 7's Task 0.7 (the shape). For the falsifier-to-reason mapping, `validation.py`'s `_encounter_failures`, `rule_failures`, `FactOutcome.material_wrong_v2` / `silent_omission_v2` and `_excused_by_r1` were also read.
Round status: Closed (0 pending)
Checked:
- **D4's falsifiers — all seven, in D4's order, with D4's ranges exactly.** R1 silent > 1 (no range; none added); silent after R1 (0); wrong without a mark (0–2); R3 > 1 (0–2); wrongly present outside R3 (0); unexcused unsupported line (0–1); checker failure (0). Each is mapped to the rule-v5 field or fixed failure it trips: `max_r1_facts 1` silent-only on a reporting row; `max_silent_omissions 0`; `max_material_wrong 0` (R3 alone excuses a wrongly present fact, R1 a `wrong` one — `material_wrong_v2`); `max_r3_encounters 1`; `unsupported_clinical_line` and `checker_failure` at any count (`_encounter_failures`).
- **D4's bands — all eight, in D4's order, with D4's numbers exactly:** marked R1 0–3; load median 0–2 / maximum ≤ 5; surfaced doubt 15–40%; mismatches 0–6; role tails 20–80%; false cuts 0–1; R2 any count; author overlap computed at P.3, "pending P.3" at P.1. No band was added and none was dropped.
- **The band rule equals D7's text character for character.** It is placed as the decision-rule reading for P.5, never a gate.
- **Every seen number equals Task 0.3's record and the frozen output.** Checked: R1 silent / marked per set; after-class silent and wrong; R3; excused lines; R2; median / maximum; surfaced / expected; the mismatch lists; the Check 6 reading for false cuts (no axis script with a tail of none has a boundary). No number was computed from them: no rate, and no role-tail fraction.
- **C12.** Nothing names an `h5-` id: the prefix appears only in the author-overlap band's D4 quote and the header. `validation/heldout-5` and `.cursor/loops/held-out-lint/` were not opened.
- **C16.** D4, D7 and every rule file are unchanged; `git diff` touches this plan only.
- **The qualifiers and the PASS allowances** are quoted from D3, the Goal and D7.
- **The prediction lines are the Goal's and D7's**, and the four verdicts' logic matches D1 (the counted verdict = rule v4's on this file, C18; without the exemption = `no_row` on `heldout-5`).
Round classification: 6 🆕 / 0 ⚡ / 0 🔁.
- **[LOW]** LOW-001: Task 0.4's rule-v1 line said "expected FAIL", a forecast neither the Goal nor D7 makes (run 7's Task 0.7 made one; this plan did not) — 🆕 — Triage: Fix-now (record-only); Decision: Applied ("the plan forecasts no rule-v1 verdict, and none is added here"; what fails rule v1 and the seen FAIL ×5 kept).
- **[LOW]** LOW-002: falsifier 2 said the Goal's "0 on every blind set so far" "sets `heldout-2` apart", which attributes an intent the Goal does not state; the Goal names `heldout-2`'s 25 separately — 🆕 — Triage: Fix-now (record-only); Decision: Applied (worded as the fact, quoting the Goal's "silent facts on unrouted patient lines, outside every plan's scope since 0.3.4", with "D4's expected 0 is unchanged by it").
- **[LOW]** LOW-003: falsifier 4's seen R3 for `heldout-3` (1, run 7 under the widened lists) sat beside the Goal's "`heldout-3` had 2 … under the old lists" with nothing saying which lists each reads — 🆕 — Triage: Fix-now (record-only); Decision: Applied (both labelled).
- **[LOW]** LOW-004: the rule-v5 prediction said "It FAILs only if a falsifier above fires", but `_encounter_failures` also fails an unmeasured encounter (`harness_error`, `role_unresolved`) — 🆕 — Triage: Fix-now (record-only); Decision: Applied ("Of the measured outcomes, only a falsifier above fails it", plus the run-failure sentence; `prose_unavailable` needs `--prose`, which P.1 does not pass). No falsifier was added.
- **[LOW]** LOW-005: the header's provenance sentence named D4, D7, D3, the Goal and Task 0.3, but the record also writes D1's row values and Task 0.2a's blob — 🆕 — Triage: Fix-now (record-only); Decision: Applied.
- **[LOW]** LOW-006: the Commit line put the hash on Task 0.5 while the task line reads "its hash on this task", with no word on why — 🆕 — Triage: Fix-now (record-only); Decision: Applied (a commit cannot carry its own hash; run 7's 0.7 → 0.8 precedent).
Missed-issue pass: re-read each D4 / D7 / D3 / Goal quote against its source for a dropped clause; the "two residual paths" sentence against D7's; `_excused_by_r1`'s three conditions against the falsifier-6 wording; whether any band carried a number not in D4; whether the without-exemption line's "FAILs wherever rule v5 fails" holds (its failures are a superset: the exemption off only adds `unsupported_clinical_line`); result: none.
Finding verification: 7 candidates; 1 dropped (the role-tails band cites run 7's Task 0.7 for its definition rather than D4 — a definition pointer, not a number; D4 carries the band unchanged from that precedent); 0 downgraded.
/fix notes: applied 2026-11-06 by the stage-4 executor (leg x1), record-only; each edit re-read from disk. No code changed, so there is no suite.

**CONVERGED (round 12: no CRIT / HIGH / MED; six 🆕 record-only LOWs, applied).** `/review-loop` converged on its first round (plan round 12; cap 3). Next by the loop config: the codex peer pass (cadence every-phase) or the 0.4 commit ALONE, as the composer runs it.

### Round 13 - 2026-11-06 - Stage-4 (Task 0.4 heldout-5 pre-registration), independent cross-family codex peer review (pass stage-4.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Task 0.4’s working-tree diff against 431a38e, checked against the specified plan sections, rule-v5.json, frozen prediction output, Round 12’s six fixes, and run 7’s Task 0.7 precedent; read-only, no suite or network.

#### Findings

- Verification counts: 13 claims checked, 13 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 14 — 2026-11-06
Source: Claude Code (`/review-loop` round 1 of cap 3, stage-5 executor leg x2, `claude-opus-5-5`, 2026-11-06T17:07:37+11:00) — Task 0.5's prep only: the four git-ignored `.cursor/loops/` tools against their run-7 originals and D4, plus the plan record. No suite: no tracked code changed.
Primary baseline: `edd1a7d` (HEAD). `git status --short` shows this plan alone.
Reviewed:
- `run8-brief-leak.py`, `validation-run8-heldout5-author-prompt.txt`, `validation-run8-heldout5-author-run.sh` and `validation-run8-heldout5-tails.py`, each read in full and diffed against its run-7 original (`git diff --no-index`);
- the generated `heldout-5-brief/SPEC.md` and `author-prompt.txt`, diffed against `validation/heldout-4/`;
- `run8-brief-leak-out.txt`;
- run 7's Task 0.7 leak record and Task 0.8 records;
- D4, C12, and Task 0.5's line and records.
Round status: Closed (0 pending)
Checked:
- **The brief's four changed lines and nothing else.** `git diff --no-index -U0 validation/heldout-4/SPEC.md .cursor/loops/heldout-5-brief/SPEC.md` shows exactly four hunks: line 1 (set 5, validation-run8 plan, Task 0.5, 2026-11-06) and lines 5, 56 and 65 (`h4` → `h5`). The generated prompt differs from heldout-4's by `h4-01.json` → `h5-01.json` alone, and `git diff --no-index --stat` against the runner's prompt is empty.
- **The primer terms are really in `LISTS`.** `"primer term": PRIMER_TERMS` is built from `CLINICAL_INITIAL_PROMPT` split on `.` and `,` (`transcription.py:211-220`). The run printed `primer term: 33`, which matches a hand count of the primer's parts, with 0 primer hits.
- **The refusal.** `validation/heldout-5` existing → exit 2, before any read or write.
- **The runner's flags equal D4's** character for character, plus run 7's output flags and closed stdin. The folder is `/c/heldout5-author`, and the composer's `diff` confirms the only differences are the folder and the three file names.
- **The tails script.** The anchor `'    "h4-21": None,\n}\n'` occurs once in `validation.py` at HEAD (`:678-679`), and `"h5-` occurs nowhere there. The guard is `assert '"h5-' not in text`. Otherwise it is run 7's script with `SET` and the glob re-pointed: it prints ids and integers only (C12).
- **No frozen-list phrase that run 7 had not accepted.** The 10 hits match run 7's Task 0.7 record line for line (`i think` ×2 :40; `see you next week` / `see you` :48; `uncertain` ×4 :67 :87; `doubtful` ×2 in the prompt). There is no greeting, no correction marker and no primer term.
- **The hashes on the task equal the output file's**, and the "before the author runs" prefix `819be450…994f54` matches.
Round classification: 1 🆕 / 0 ⚡ / 0 🔁.
- **[LOW]** LOW-001: the leak record's disposition gave only the cue-table and hedge reasons. It left out run 7's reason for accepting `see you next week` — every match already matched the listed `see you` — which is what makes "no phrase run 7 had not accepted" hold for line 48 — 🆕 — Triage: Fix-now (record-only); Decision: Applied (run 7's reason quoted, its commit `de8f5da` named). [Round 15 PR-LOW-001, 2026-11-06T17:12:09+11:00: this finding copied run 7's reversed provenance. `see you next week` is the long-listed phrase and `see you` the one `de8f5da` added. The record is corrected on Task 0.5; this entry is history and is kept as written.]
Missed-issue pass. Each was checked and found sound:
- whether the leak script writes the brief before its asserts: no, every assert precedes the write;
- whether exit 3 on a prompt mismatch could still leave a usable-looking brief: it writes, but the composer re-checks both hashes before the launch, as recorded;
- whether `phrase_tokens` could hide a primer hit: both sides go through the same function;
- whether the record's `lines 112` vs run 7's "111 lines" is a real difference: no — `rg` counts 111 lines, and `split("\n")` adds the empty piece after the final newline;
- whether the runner's `cd … || exit 9` leaves no `.done` file: it does, as in run 7. That is named in the practitioner's step, not a code change.
Result: none.
Finding verification: 2 candidates; 1 dropped (the runner's missing `.done` on exit 9 is run 7's behaviour and outside D4's edits; it is covered in the handoff's practitioner step instead); 0 downgraded.
/fix notes: applied 2026-11-06 by the stage-5 executor (leg x2), record-only, and re-read from disk. None of the four tools changed, so the leak run and its hashes stand.

**CONVERGED (round 14: no CRIT / HIGH / MED; one 🆕 record-only LOW, applied).** `/review-loop` converged on its first round (plan round 14; cap 3).

### Round 15 - 2026-11-06 - Stage-5 (Task 0.5 author prep), independent cross-family codex peer review (pass stage-5.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Task 0.5 author-preparation tools, generated brief and prompt, leak output, permitted plan records, run-7 precedents, and named code definitions; read-only verification.

#### Findings

- **PR-LOW-001** (LOW, docs-only, `.cursor/plans/plan-validation-run8.md:924`): The leak disposition reverses which closing phrase was added in `de8f5da`, perpetuating an error in run 7’s record. `see you next week` was already listed; `see you` was added by that commit. The unchanged brief remains supported, but its recorded provenance is inaccurate. - Evidence: “`see you next week` (closing, new in `de8f5da`)” and “the long-listed `see you`”; `desktop/src/scribe_desktop/consultation_phrases.py:90` places `"see you next week"` in the original block, while lines 104–111 place `"see you"` under “Validation-run7 plan Task 0.4 (c)”; the named commit’s diff confirms `+    "see you",`. Recommendation: Fix-now - Correct the provenance and explain that the additional shorter-phrase hit occurs within the already-present follow-up cue; preserve the accepted disposition and author inputs. /fix decision: Applied — LEG-1 verified tuple (PR-LOW-001, CONFIRMED, LOW docs-only / record-only, rec=Fix-now).
    - Evidence: `consultation_phrases.py:89-103` (the shipped 2026-09-28 block) holds `"see you next week"` at `:90`. `:104` opens the `# Validation-run7 plan Task 0.4 (c)` block, and `"see you"` is at `:111`. `git show de8f5da -- desktop/src/scribe_desktop/consultation_phrases.py` adds `+    "see you",` and does not add `see you next week`.
    - Disposition unchanged, so no MUST-PAUSE. The line-48 cue row was already a hit (`see you next week`) for the heldout-3 and heldout-4 authors. The newer `see you` hit lies inside that same phrase and adds no word. C2 keeps the row equal to the cue file.
    - /fix notes: `.cursor/plans/plan-validation-run8.md` only.
      - Task 0.5's leak record: the provenance sentence is replaced by the corrected two-phrase account, with a dated correction note naming run 7's reversed record (run 7's plan is not edited).
      - Sibling: Round 14 LOW-001 copied the same reversal. It gets a dated bracketed pointer and is kept as history.
      - Other siblings swept (`long-listed`, `new in de8f5da`, `old-listed`, `already matched the listed`): none left.
      - The brief, the prompt and the four tool files are unchanged, so the leak run's hashes stand.
    - /fix date: 2026-11-06. /fix applied by: Claude Code (stage-5 executor leg x3).

- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 16 - 2026-11-06 - Stage-5 (Task 0.5 author prep, re-check), independent cross-family codex peer review (pass stage-5.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Round 15’s correction; named preparation tools, generated author inputs, hashes and leak output; permitted plan records, run-7 precedents, code definitions and provenance commit; static read-only verification.

#### Findings

- Verification counts: 8 claims checked, 8 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 17 — 2026-11-06
Source: Claude Code (`/review-loop` round 1 of cap 3, stage-6 executor leg x1, `claude-opus-5-5`, 2026-11-06) — Phase 1 (Tasks 1.1 and 1.2), the documents, against D1, D2, D8 and C17 (c), every claim checked against the code. No pytest (the suite runs only through the `heldout-5` runner, composer-run).
Primary baseline: `2228b25` (HEAD). `git status --short`: 24 tracked files changed, this plan's own bookkeeping besides.
Reviewed: every hunk of `git diff` over the 24 files; D1, D2, D8, C12, C16, C17; Task 0.3's frozen record and Task 0.4's pre-registration; run 7's five reports (`.cursor/loops/run7-reports/`, the Facts tables and residue sections); `rule-v5.json`; and the code the documents describe — `validation.py` (`REVIEW_MARK_CODES`, `_check_sets`, `_verdict_lines`, `render_report`'s heading and amendments, `_residue_section`, `--model`, the encounter table's Rule column), `note.py` (`line_marks`, `LINE_MARK_CODES`), `transcription.py` (`mark_words`, `UNCERTAINTY_THRESHOLD`), `ui/models.py` (`_segment_words`, `SEPARATELY_ACKNOWLEDGED_NAMES`), `validation_set.py` (`add_noise`), `conftest.blind_run_refusal` and `TestHarnessDocument`.
Round status: Closed (0 pending)
Checked:
- **D2's counts re-read from run 7's reports, not copied.** The Facts tables hold exactly 7 `wrong` material facts over 139 encounters (50 + 22 + 22 + 23 + 22): 5 with class `R1` (`syn-28/f1`, `hld-07/f0`, `h3-03/f0`, `h4-01/f5`, `h4-07/f0`) and 2 with none (`hld-14/f1`, `hld-21/f3`). The guide and the practice README carry the counts with no id.
- **The guide's mark wording holds against the code.** `[word?]` marks a word below `UNCERTAINTY_THRESHOLD` 0.60, a number or a name-like word (`mark_words`), the same threshold as Check 1's `low_confidence_source`. The note's three line marks are `[check: number]` (any number token on a quoted line), `[check: possibly not speech]` and `[check: unsure]` (`LINE_MARK_CODES`). R1's mark term reads all four codes on SOME aligned word, so "a mark does not point at the wrong word" holds.
- **D2 corrected where the code contradicts it (deviation, recorded):** D2's draft "read aloud by computer voices in a quiet room" is not what the set does — 8 of the 50 scripts carry `snr_db`, and the builder mixes Gaussian noise in (`validation_set.add_noise`). The guide and the README say "a few with a steady hiss mixed in" and "Real voices and accents and everyday background sound were not measured". D2's other claims are kept as written.
- **D1's override lines are in the practitioner's words**, quoted from the plan ("Rule v5: report marked misheard facts (Recommended)", 2026-11-06), at all four standing sentences: `plan-pilot.md` Constraint 12 and the stop rule (a sub-bullet under the stop rule's line), `validation-harness.md`'s run-7 sentence, `plan-larger-model.md`'s Follow-Up Continuation line. Each states Constraint 12's narrow sense. `plan-larger-model.md`'s `heldout-5` item gains its dated "taken over" line, and `plan-pilot.md` P.5 a dated line after the `[2026-11-06]` larger-model line, which is kept as history.
- **The report text the documents quote equals the code's.** The heading's four verdicts, the second verdict line's parenthesis, the R1 row name `R1 recogniser (silent only; marked R1 reported below)`, the marked line `- R1 marked wrong (reported, no ceiling): <n> - <members>` (ASCII ` - `, Task 0.2b's deviation (i)) and its counted form, rule v2's counterpart readings, the amendments sentences and the schema-4 loader rule in `_check_sets`.
- **The Rule v5 ceiling table equals `rule-v5.json`**, and a new pin says so (`TestHarnessDocument.test_the_rule_v5_ceiling_table_is_the_files`, six rows in the file's order). The rule-v3 table's pin still reads only its own section: the split ends at the next `## `, which is `## Rule v5`.
- **The pilot documents pass `test_pilot_docs.py`'s rules by inspection:** no carriage return, no 16+ hex run and no 7+ digit run in `docs/pilot/*.md` (Grep, 0 hits). Commits there are 7-char. The register's vocabularies are untouched (no row changed).
- **C17 (c):** `git diff -- scripts/run-validation.py` is docstring-only. C17 (a) `git diff --stat 170345d` over the C17 paths, `validation.py` excluded, is empty. `lint-held-out-set.py`'s change is its docstring only (D8).
- **C12:** nothing under `validation/heldout-5/` or `.cursor/loops/held-out-lint/` was opened, listed or searched. No `h5-` id is named, only the prefix and the README's existing range form.
- **CRLF:** the seven listed files, plus `docs/security/threat-model.md`, `docs/security/data-flow-map.md`, `scripts/lint-held-out-set.py`, `.github/workflows/ci.yml` and the seven edited test files, which are CRLF too, have 0 LF-only lines and 0 bare `\r` (multiline Grep). The LF files (the plans, `docs/pilot/*.md`, `scripts/run-validation.py`) hold no `\r`.
Round classification: 4 🆕 / 0 ⚡ / 0 🔁.
- **[LOW]** LOW-001: the guide's "7 facts came out wrong" reads as every wrong fact, but R3's next-patient facts reached the notes too (wrongly present), and the sentence is about mishearing — 🆕 — Triage: Fix-now; Decision: Applied ("came out wrong this way").
- **[LOW]** LOW-002: the exit gate's proposal said the marked facts are "reported beside the gate"; the report prints them beside R1's ceiling — 🆕 — Triage: Fix-now; Decision: Applied ("beside R1's ceiling, each a findings-register row").
- **[LOW]** LOW-003: `validation-harness.md` described `heldout-4` in the present tense as blind until run 7 and had no paragraph for `heldout-5`, whose blind rule (the suite only through the runner, the presence test, the machine readers) is now in force — 🆕 — Triage: Fix-now (scope: D8's harness document; LOW, documents only, auto-disposable); Decision: Applied (a dated "SEEN since run 7's P.4" sentence on `heldout-4`, as `heldout-3`'s has, and "The fifth held-out set" paragraph in C12's wording).
- **[LOW]** LOW-004: the practice README said the guide asks for numbers "to be read against what was said"; the guide says "against what you remember" — 🆕 — Triage: Fix-now; Decision: Applied.
Missed-issue pass. Each was checked and found sound:
- whether "a larger speech model … did no better" overstates F-148: no — 8 and 16 facts wrong against `medium`'s 7;
- whether the guide's "Once shadow mode is turned off … Write and Copy work" promises more than the app does: no — Write is still for linked recordings (said above it in the guide), and the line names the condition without claiming the app enforces it;
- whether "under a schema-4 rule … the Rule column and the TOTAL verdict are rule v5's" holds: yes, the encounter table's Rule column reads `rule_failures(rule, …)` for the rule in use;
- whether the new harness-document sentences break `TestHarnessDocument`'s rule-v3 split: no — no `| \`` row lies between `## Rule v3 ` and the next `## `, which is `## Rule v5`;
- whether `scripts/README.md`'s "with no such script in the tree … a bare run goes ahead" holds: yes, `blind_run_refusal` fires only on a not-yet-written set that has a script;
- whether `evaluate_encounter`'s stale docstring word (Task 0.2b deviation (iv)) belongs here: no — C17 (b) still bars it until P.1.
Result: none.
Finding verification: 4 candidates; 0 dropped; 0 downgraded.
/fix notes: applied 2026-11-06 by the stage-6 executor (leg x1), documents only, each re-read and its line endings re-checked (0 LF-only lines, 0 bare `\r`; the pilot documents 0 id-shaped runs).

**CONVERGED (round 17: no CRIT / HIGH / MED; four 🆕 LOWs, all applied).** `/review-loop` converged on its first round (plan round 17; cap 3).

### Round 18 - 2026-11-06 - Stage-6 (Phase 1 documents), independent cross-family codex peer review (pass stage-6.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Read-only review of the 25-file working-tree diff against HEAD `2228b25`, using the permitted evidence. Verification by reading only; no tests, scripts, network commands or writes.
  - `docs/practice/clinician-review-guide.md`: checked D2 wording, approval status and counts; 139 encounters, seven misheard facts, five marked and two unmarked agree with run 7. Dated, awaiting approval, and no encounter ids.
  - `docs/practice/README.md`: checked testing summary, date, approval qualification and memory-based review instruction; consistent with D2 and the guide, with no encounter ids.
  - `docs/testing/validation-harness.md`: checked schema-4 policy, six ceiling rows, split precedence, four verdicts, predictions, bands, override and run placeholder; consistent with the rule files, code and permitted plan records.
  - `docs/pilot/README.md`: checked run 8’s rule, six sets and four verdicts; matches rule v5.
  - `docs/pilot/exit-gate.md`: checked proposal status and acceptance wording; clearly awaits P.2 approval and does not replace the approved line.
  - `docs/pilot/findings-register.md`: checked marked-R1 registration policy and existing referenced rows; consistent with D1, with register rows and vocabularies unchanged.
  - `docs/security/threat-model.md`: checked schema-4 verdicts, identifier-only output and marked-R1 residue; matches the report implementation and D1.
  - `docs/security/data-flow-map.md`: checked schema-4 set selection and added report outputs; matches the loader and report code.
  - `scripts/README.md`: checked six-set rule description and blind-runner lifecycle; consistent with D1 and C12.
  - `validation/README.md`: checked rule-v4 history and rule-v5 schema, schedule and output description; matches both rule files.
  - `AGENTS.md`: checked changed run instructions, rule summary, blind-set restriction and next-step account; consistent with the scoped records.
  - `CHANGELOG.md`: checked developer-tooling scope, rule change, verdicts, band and pending document approval; consistent with the implementation and records.
  - `.github/workflows/ci.yml`: checked authorship and blind-set comments; correctly identifies `heldout-5`, describes `heldout-4` as seen, and changes no executable step.
  - `scripts/run-validation.py`: checked example and schema references; rule v5 and six sets are correct, with docstring-only changes.
  - `scripts/lint-held-out-set.py`: checked authorship and diagnosis references; Tasks 0.5 and P.3 preserve C12.
  - `desktop/tests/fixtures/heldout_transcripts.py`: checked three citation edits; correctly assigns authorship and case writing without changing fixtures.
  - `desktop/tests/test_consultation_boundary.py`: checked diagnosis citation; correctly points to validation-run8 P.3.
  - `desktop/tests/test_lint_held_out_set.py`: checked blind-set citation and assertion; P.3 reference corrected and blind pin unchanged.
  - `desktop/tests/test_note.py`: checked diagnosis citation; correctly points to validation-run8 P.3.
  - `desktop/tests/test_note_check.py`: checked diagnosis citation; correctly points to validation-run8 P.3.
  - `desktop/tests/test_validation_scripts.py`: checked authorship, case-writing and metadata comments; corrected references leave assertions unchanged.
  - `desktop/tests/test_validation_harness.py`: checked the new table test and its loader; it reads the actual rule-v5 file and compares row order and every table field. A changed ceiling would fail the comparison.
  - `.cursor/plans/plan-pilot.md`: checked both override quotations, run ownership and shadow-off sequencing; quotations match D1 verbatim and the band remains a recommendation.
  - `.cursor/plans/plan-larger-model.md`: checked takeover and override additions; preserves historical outcomes and quotes D1 verbatim.
  - `.cursor/plans/plan-validation-run8.md`: checked permitted Phase 1 records and Round 17 fixes; the quiet-room departure is recorded and supported by eight `snr_db` metadata entries. The diff does not loosen C12, C16 or C17, change runtime sources/rules/config/scripts data, or introduce a specific blind-set id beyond the existing range form.

#### Findings

- Verification counts: 25 file-level claims checked, 25 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 19 — 2026-11-06
Source: Claude Code (`/review-loop` round 1 of cap 3 — the hardening stage's H1, stage-7 executor leg x1, `claude-opus-5-5`; ONE pass over the whole run as one change, `git diff 9884f04 HEAD -- . ':(exclude)validation/heldout-5'` — Tasks 0.2a `ba71ff5`, 0.2b `d15a28f`, 0.3 `431a38e`, 0.4 `edd1a7d`, 0.5 prep `4e0d550`, 0.5 `2228b25`, Phase 1 `60d553d` — bound by C1, C12, C16 and C17; no pytest, the suite runs only through the `heldout-5` runner, composer-run).
Primary baseline: `9884f04` (the run's base). 28 files changed (`git diff --stat`), `validation/heldout-5/` excluded and never opened, listed or searched; `.cursor/loops/` not opened.
Reviewed: every hunk of `validation.py` (the two `FactOutcome` properties against `FactOutcome.__post_init__`'s R1 invariant; `SetCeilings`; `PassRule._check_sets`, `counting_marked_r1`, `set_row`; `rule_v2_counterpart`'s `comparable`; `ClassCount` / `class_counts`; `class_breaches` → `run_passed`; `_verdict_lines`; `render_report`'s heading and amendments; `_residue_section`; `_parser` / `main` strings) read in full context; `rule-v5.json`; every added test in `test_validation_metrics.py` (`TestRuleV2`'s rows, `TestRuleV5`, `TestRuleV5Reading`) and `test_validation_harness.py` (`TestRunValidationMain`, `TestHarnessDocument`, `TestReport`'s rule-v5 pins) for vacuous or mis-indexed pins; the comment-only test, fixture, CI and launcher edits; every document and plan hunk (Rounds 17–18 had read the Phase 1 slice; this round re-read it as part of the whole); `conftest.blind_run_refusal` against `scripts/README.md`'s bare-run sentence; `test_pilot_docs.py`'s Category vocabulary against the register's marked-R1 row rule.
Round status: Closed (0 pending)
Checked:
- **Every R1 fact is exactly one kind, by construction.** `FactOutcome.__post_init__` refuses `residue_r1` unless `material and (verdict == "wrong" or silent_omission)`, so `residue_r1_silent` (`residue_r1 and silent_omission`) and `residue_r1_marked` (`residue_r1 and verdict == "wrong" and not silent_omission`) partition R1; the both-case is silent (D1's precedence). Pinned both ways (`test_each_r1_fact_is_exactly_one_kind`).
- **The gate path reads the split in one place.** `class_counts` alone moves a marked fact to `reported_members` on a row whose `r1_marked_reported is True`; `class_breaches`, `run_passed`, `set_level` and the residue table read `total` / `ceiling` unchanged. Per-encounter predicates are untouched: `material_wrong_v2` / `silent_omission_v2` still excuse every R1 fact. C17 (b) holds for the diff except for two inert hunks the tasks themselves authorised (corrected 2026-11-06 by peer round 22 PR-LOW-001; this round first said "holds for the diff"): the `RULE_SCHEMA_VERSION` value and its comment (Task 0.2a: "`RULE_SCHEMA_VERSION` → 4") and the docstring lines of `render_report`'s heading hunk (Task 0.2b) lie outside C17 (b)'s literal list, and neither decodes nor routes. Every other hunk — the 0.2b record's list and the composer's `h5-` rows of `REFERENCE_TAIL_STARTS`, which this round did not re-derive — is inside it.
- **The loader both ways:** schema 4 requires the field non-None on every row (a missing row field, an explicit `null`, and one of two rows missing it are all refused); schemas 2–3 refuse it non-None and accept `null`; the exemption gate reads `>= 3`; schema 5 and 0 refused. Lax bool coercion matches the existing row and top-level flags; the repository file is pinned value for value and byte-shape (`test_the_file_is_lf_in_rule_v4s_key_order`).
- **`counting_marked_r1`** copies rows in order and returns `self` when no row reports; `rule_v2_counterpart` neutralises `False` to rule v2's `None` and keeps `True` as `differs` (pinned both ways, in the metric and the report).
- **The report pins are line-exact, not vacuous:** the whole `heldout-5` and `heldout-4` rule-v5 reports index every line; the `heldout-4` pin also compares its tables to the rule-v3 report's offset by the one new verdict line; the mirror pins assert no `v5`, no `marked R1` and three verdict lines on rule v3's and rule v4's reports over outcomes holding both kinds.
- **The documents against the code and the frozen records:** the Rule v5 section's table, split, four verdicts, counterpart readings and report lines equal the code's; the bare-run sentence in `scripts/README.md` equals `blind_run_refusal` ("such script" = a script of a set whose cases are not written); the register's marked-R1 categories (`wrong-dose`, `quality`) are in `test_pilot_docs.py`'s Category vocabulary; no `h5-` id is named beyond `validation/README.md`'s existing range form.
- **C16:** no edit to rule v5, predictions v5, the pre-registration, D4 or D7; **C17 (a)** empty since `170345d` (no decode-path file in the diff besides `validation.py`); **(c)** `scripts/run-validation.py` docstring-only.
Round classification: 2 🆕 / 0 ⚡ / 0 🔁 (the first `/review`-class round over the whole run; both pre-existing in the run's commits).
- **[LOW]** LOW-001: `docs/testing/validation-harness.md:206` — "The gate for run 8" said a pass is evidence about the gated sets only because "`heldout` and `heldout-2` still fail", carried from the Goal's forecast (written before predictions v5); predictions v5 (Task 0.3, the same section's line 220) have `heldout-4` FAIL too, on R1 2 over its reported row's ceiling of 1 — the sentence read as if `heldout-4` passed. Pattern siblings: searched `still fail` and `still FAIL` over the tracked files (C12's paths excluded) — the plan's Goal (`:41`, a forecast written before any measurement, left as written) and this line; none other. — 🆕 — Triage: Fix-now (documents only; LOW, non-production, auto-disposable); Decision: Applied ("`heldout`, `heldout-2` and `heldout-4` are predicted to fail (predictions v5, below) and are reported").
- **[LOW]** LOW-002: `.cursor/plans/plan-validation-run8.md` (Deferred — Actionable Later) — the one docstring-only `validation.py` commit owed after P.1 (the stale "schema 3" words in `EncounterMetrics` ×2, `RULE_V2_RATIFIED`, `rule_failures`, `run_passed` and `evaluate_encounter`, reverted or left by Task 0.2b under C17 (b), peer round 7) was recorded only in Round 7's log text and Task 0.2b's record, on no task, Deferred entry or retained item, so the plan's close could drop it. — 🆕 — Triage: Fix-now (record only; the deferral was already decided by C17, this records where the close finds it); Decision: Applied (a dated Deferred bullet with its symbols, file, risk `minor` and trigger "after P.1 is committed, when C17 lapses").
Missed-issue pass: re-read `validation.py`'s `_residue_section` (both branches of the marked line with nothing measured, `listed`'s empty text), the heading's verdict order against `_verdict_lines`', the rule-v4 history sentence's gate (`label == "v4" or schema_version >= 4`, so a schema-4 rule of any name prints it — D1's reading), `PassRule.label` for schema-4 names (`relaxed` → `v4`, the existing derivation, plan-chosen at peer round 2), the CI comment's tense, and LOW-001's document region; result: none beyond LOW-001 and LOW-002.
Finding verification: 2 candidates; 0 dropped; 0 downgraded.
/fix notes: applied 2026-11-06 by the stage-7 executor (leg x1), one at a time, each re-read after applying. LOW-001: one line of a CRLF file, edited inside the line; 0 LF-only lines and 0 bare `\r` after (multiline Grep); the Rule v5 ceiling table, which `TestHarnessDocument` reads, untouched. LOW-002: the plan (LF) holds 0 `\r` after.

**CONVERGED (round 19: no CRIT / HIGH / MED; two 🆕 LOWs, both applied).** `/review-loop` converged on its first round (plan round 19; cap 3).

### Round 20 — 2026-11-06
Source: Claude Code simplify (the hardening stage's H2, stage-7 executor leg x1, `claude-opus-5-5`; the same scope as round 19 — `git diff 9884f04 HEAD`, `validation/heldout-5` excluded; propose-only, under the conservatism guard; bound by C1, C12 and C17 (b), which bars any `validation.py` hunk outside its symbol list until run 8).
Round status: Closed (0 findings)
Scope: the code hunks of round 19's list read in full context (`FactOutcome`, `SetCeilings`, `PassRule`, `rule_v2_counterpart`, `ClassCount` / `class_counts`, `_verdict_lines`, `render_report`, `_residue_section`), the new tests and `rule-v5.json`; the documents for redundant restatement only.
Simplifications found: none — no simplifications worth a maintainer's attention.
Consciously left alone (each fails the conservatism guard or is plan-chosen):
- `_residue_section` re-derives the marked members from the facts on a row that counts them, while `class_counts` holds them as `reported_members` only on a row that reports — D1 fixes `reported_members` "for R1 only where `row.r1_marked_reported is True`", and peer round 7 folded the would-be shared helper into these two sites to keep C17 (b); a shared helper is a symbol C17 (b) does not list.
- `FactOutcome.residue_r1_silent` has no production reader (only `residue_r1_marked` is read) — D1 names both properties and the test pins them as a partition; removing it saves four lines and loses the stated invariant.
- The heading and `_verdict_lines` each compute the counted verdict — the existing shape of the without-exemption verdict since rule v3; folding both is a refactor of the report's structure for no behaviour change.
- `counting_marked_r1` and `without_r1_exemption` share a "return `self` when nothing changes" shape — two short methods, each with its own field; no duplication worth a layer.
- The documents restate the split in the harness document, the threat model, the pilot README and `CHANGELOG.md` — each for its own reader; the harness document is the canonical one and the others point to it.
Summary: 0 findings (0 CRIT / 0 HIGH / 0 MED / 0 LOW); round 20.

### Round 21 — 2026-11-06
Source: Claude Code security-review (the hardening stage's H3, stage-7 executor leg x1, `claude-opus-5-5`; the portable threat-model checklist in this session — no native subagent was spawned; the scope of round 19; references: the threat model's "The pilot" (harness residues) and its new marked-R1 residue, data-flow flow 26; bound by C1 and C12).
Round status: Closed (0 findings)
Trust boundaries examined: the rule file (a tracked, practitioner-ratified input read through `load_pass_rule`'s 64 KiB cap and `model_validate_json`); the report on standard output (the run of record's only output, copied to `.cursor/loops/` and recorded in tracked documents as ids and counts); the blind set's process controls (C12: the conftest refusal, the presence pin, the tails script's output in `REFERENCE_TAIL_STARTS`); the public repository's documents (the register's content-free rules, `docs/pilot/`'s no-hash rule).
Checked and clean:
- **Injection and taint into the report:** every new printed field is a pattern-checked encounter id, a fact index (an int), a rule label derived from the pattern-checked `rule_name`, or a set name the rule's pattern admits; the new `ValueError` texts carry only the schema's digit; `hide_input_in_errors` stays on the rule models, so a refused rule file's values are not echoed.
- **Deserialization:** `extra="forbid"` and `frozen` unchanged; the new field is `bool | None`, its lax coercion the same as the existing `gate`, `require_uncertainty_surfaced` and `unsupported_line_r1_exemption`; the repository's `rule-v5.json` is pinned value for value. A hand-edited rule file is the practitioner's own input, not a trust boundary the threat model names.
- **Sensitive data:** no transcript, note, script or name text enters a new line; the marked-R1 line prints `<id>/f<n>` only, as the threat model's new paragraph says. The two SHA-256s in `validation/README.md` (the brief and the prompt) are integrity records of public files, and `docs/pilot/` carries no 16+ hex run (round 17's Grep, unchanged by this stage).
- **C12 (the blind set as a confidentiality control):** nothing in the diff prints an `h5-` script's words; the presence pin reads file names only; the `h5-` rows are ids and integers; the CI comment changes no executable step. `validation/heldout-5/` holds `author-session.jsonl`, committed to the public repository after Task 0.5's redaction step (the identifying forms counted, 0 found, the log copied unchanged); this round did NOT open it (C12) and makes no claim about its other content. `[2026-11-06, corrected by peer round 23 PR-LOW-001]` This round first said that a further count-only check would be "within C12's permitted machine reads". It is not: C12 names its readers (the lints through the runner, the tail script, the presence pin, P.1's builder and harness), and a further scan is none of them. The one count is the one Task 0.5's own copy-in step already made. Before copying the log, the composer counted the identifying forms in it — the Windows user name, the account name, the e-mail domain and the user-profile path forms — and found 0 (Task 0.5's Closed sub-bullet), so the log was copied unchanged. No further read of the log or the set is made before P.3, which is its first examination. C12's text is unchanged.
- **Resource and availability:** no new unbounded input; the rule-size cap, the label-track cap and the script cap are unchanged.
- **Dependencies and config:** no new dependency, environment variable or runtime network; no change to the offline guards.
Summary: 0 findings (0 CRIT / 0 HIGH / 0 MED / 0 LOW); round 21 — no security issues found in scope. The project's own security tests run in the suite (composer, through the `heldout-5` runner).

### Round 22 - 2026-11-06 - Stage-7 (H4 code slice), independent cross-family codex peer review (pass stage-7.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Specified code/test diff against `9884f04`, permitted supporting code, rules and plan sections; static reading only, no execution or writes.
  - job 1: checked the R1 predicate, `FactOutcome.__post_init__` and both partition properties; every valid R1 fact belongs to exactly one side, with the both-case counted as silent (`desktop/src/scribe_desktop/validation.py:900`, `:959`, `:2204`).
  - job 2: checked row-controlled splitting, reported members, counted-rule copying and counterpart neutralisation; D1 is implemented and the repository rule’s counted verdict equals rule v4 by construction (`desktop/src/scribe_desktop/validation.py:2432`, `:2518`, `:2762`).
  - job 3: checked headings, verdict lines, amendment gates and both marked-line branches; schema-3 report output remains unchanged by the diff (`desktop/src/scribe_desktop/validation.py:3329`, `:3392`, `:3420`, `:3734`).
  - job 4: checked fixtures, parametrization, report indexes, ceiling boundaries and table comparison; no vacuous pin found. Both R1 readings exercise n/n+1 and both-case precedence; changing a ceiling alone changes the table test’s expected cells and fails equality (`desktop/tests/test_validation_metrics.py:2963`, `:3370`, `:3467`; `desktop/tests/test_validation_harness.py:2097`).
  - job 5: checked every `validation.py` hunk against C17(b); the schema-version constant/comment and `render_report` docstring are outside its literal list, as detailed below.

#### Findings

- **PR-LOW-001** (LOW, docs-only, `.cursor/plans/plan-validation-run8.md:214`): C17(b)’s explicit permitted list still does not cover every code hunk, despite the compliance claim. It omits `RULE_SCHEMA_VERSION` and its comment (`desktop/src/scribe_desktop/validation.py:205`), and names only the report heading/amendments rather than the changed `render_report` docstring (`:3383`). These implement task-authorised schema/report changes, but the literal confinement check does not pass. - Evidence: C17(b) requires the diff be “confined to” its list, including “`_verdict_lines` / the heading / the amendments / `_residue_section`”; the diff changes `RULE_SCHEMA_VERSION: Final = 4` and adds “four verdict lines and the marked-R1 line in that section” to `render_report`’s docstring. Task 0.2a explicitly requires “`RULE_SCHEMA_VERSION` → 4” (`:967`), while Round 19 states “C17 (b) holds for the diff” (`:921`). Recommendation: Fix-now - Reconcile C17(b) with these narrowly bounded, already-authorised hunks and correct the compliance record, preserving all decoding/routing prohibitions. /fix decision: Applied — verified tuple (PR-LOW-001, CONFIRMED, 🆕 pre-existing since Tasks 0.2a / 0.2b, Fix-now record-only; no C17 amendment).
  - Verification (stage-7 executor leg x2, 2026-11-06T21:28:43+11:00): `git diff 9884f04 HEAD -- desktop/src/scribe_desktop/validation.py` holds 25 hunks. The first (`@@ -202,10`) is `RULE_SCHEMA_VERSION`'s comment and value, which Task 0.2a names ("`RULE_SCHEMA_VERSION` → 4") and C17 (b)'s list (Critical Constraints, C17) does not. The `@@ -3281,14` hunk changes `render_report`'s docstring with its heading; the list names "the heading / the amendments", not the docstring. Neither touches decoding or routing. Three records over-claimed: round 19 ("C17 (b) holds for the diff"), the stage-1 leg x2 handoff ("inside C17 (b)'s permitted list"), and Task 0.2b's record ("19 hunks, all inside C17 (b)'s list"); Task 0.2a's own C17 line names the constant and makes no such claim. (`[2026-11-06]` "Three" was not exhaustive: peer rounds 26–27 found seven more unqualified siblings, qualified by the stage-7 executor leg x4. Round 26's `/fix` notes list them. Peer round 28 found two more round summaries, Rounds 8 and 5, qualified by leg x5: nine in all.)
  - Disposition: the records corrected, not C17. C17 (b)'s purpose — nothing that decodes or routes between Task 0.3 and run 8 — holds. Conforming the code is not open: the constant's value is Task 0.2a's own requirement and is pinned (`TestRuleV5`), and the docstring is correct. So an amendment to C17's text adds nothing a practitioner would decide differently, and it is not raised (no MUST-PAUSE). Neither hunk belongs in the post-P.1 docstring commit (Deferred, round 19 LOW-002): both are already correct for schema 4, and that commit is for stale words.
  - /fix notes: applied 2026-11-06T21:28:43+11:00 by the stage-7 executor (leg x2), plan records only. Round 19's Checked bullet is corrected in place, with the date and this round named. Dated `[2026-11-06, peer round 22 PR-LOW-001]` corrections are added to the stage-1 leg x2 handoff and under Task 0.2b's "supersedes" record. No code, test or document changed.

- Verification counts: 5 claims checked, 5 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 23 - 2026-11-06 - Stage-7 (H4 documents slice), independent cross-family codex peer review (pass stage-7.p2)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Documents diff against `9884f04`, including working-tree changes; verified by reading permitted evidence only. No writes, scripts, suites or network commands.
  - `docs/testing/validation-harness.md`: checked schema 4, ceiling table, split precedence, four verdicts, predictions, bands and run placeholder; consistent with code, rules and records. Round-19 LOW-001 correctly includes `heldout-4`.
  - `validation/README.md`: checked rule history, six-set schedule and blind-set lifecycle; consistent with records, with blind identifiers limited to the range form.
  - `docs/pilot/README.md`: checked run-8 rule, gate sets and verdict descriptions; matches rule v5.
  - `docs/pilot/exit-gate.md`: checked approval boundary; rule-v5 wording remains a dated proposal explicitly leaving the approved line operative.
  - `docs/pilot/findings-register.md`: checked marked-R1 policy, categories and referenced rows; consistent with D1 and the test vocabulary.
  - `docs/practice/clinician-review-guide.md`: checked measured counts and approval status; 139 encounters, seven misheard facts, five marked and two unmarked match run-7 reports. Dated, awaiting approval, without encounter ids.
  - `docs/practice/README.md`: checked testing summary and approval qualification; matches the reports and D2, without encounter ids.
  - `docs/security/threat-model.md`: checked fourth verdict, identifier-only output and marked-R1 residue; matches implementation and D1.
  - `docs/security/data-flow-map.md`: checked schema-4 set selection and added report fields; matches implementation.
  - `scripts/README.md`: checked rule-v5 description and blind-runner lifecycle; preserves the P.3 boundary.
  - `scripts/run-validation.py`: checked docstring example and six-set description; correct, with no executable changes.
  - `scripts/lint-held-out-set.py`: checked docstring lifecycle references; correctly names Tasks 0.5 and P.3.
  - `.github/workflows/ci.yml`: checked comments; identifies `heldout-5` as blind and `heldout-4` as seen, without changing executable steps.
  - `desktop/tests/fixtures/heldout_transcripts.py`: checked citation edits; authorship and case-writing references correctly identify this plan.
  - `desktop/tests/test_consultation_boundary.py`: checked diagnosis citation; correctly points to validation-run8 P.3.
  - `desktop/tests/test_lint_held_out_set.py`: checked blind-set comment; P.3 citation is correct and assertion unchanged.
  - `desktop/tests/test_note.py`: checked diagnosis citation; correctly points to validation-run8 P.3.
  - `desktop/tests/test_note_check.py`: checked diagnosis citation; correctly points to validation-run8 P.3.
  - `desktop/tests/test_validation_scripts.py`: checked authorship, case-writing and presence-test descriptions; consistent with the documented lifecycle.
  - `AGENTS.md`: checked changed rule summary, next steps and noise count; consistent with records and eight `snr_db` metadata entries.
  - `CHANGELOG.md`: checked tooling-only scope, split, verdicts, band and pending approvals; consistent with implementation and records.
  - `.cursor/plans/plan-pilot.md`: checked both override quotations and P.5 sequencing; quotations match D1 verbatim, with the band remaining advisory.
  - `.cursor/plans/plan-larger-model.md`: checked takeover and override lines; preserves the historical outcome and quotes D1 verbatim.
  - `.cursor/plans/plan-validation-run8.md`: checked rounds 19–21 and LOW-002’s Deferred entry; both round-19 fixes are recorded, but round 21 overstates C12’s permitted reads as detailed below. C16 and C17 remain unchanged.

#### Findings

- **PR-LOW-001** (LOW, docs-only, `.cursor/plans/plan-validation-run8.md:957`): Round 21 incorrectly presents an additional pre-P.3 author-log scan as already permitted by C12. C12 enumerates the permitted machine readers; an arbitrary count-only scan is not among them. This advice could lead the composer to expand blind-set access without a recorded constraint decision. - Evidence: line 957 says a count-only check “is within C12's permitted machine reads”; C12 at line 210 permits “the lints through the runner, the tail script … the file-name-only presence pin … and P.1's builder and harness.” Task 0.4 also explicitly postpones another count-only computation, author overlap, until P.3. Recommendation: Fix-now - Correct the round-21 advice to defer this additional scan until P.3 rather than assert existing authorization; keep C12 unchanged. /fix decision: Applied — verified tuple (PR-LOW-001, CONFIRMED, ⚡ introduced by round 21's own note, Fix-now record-only).
  - Verification (stage-7 executor leg x2, 2026-11-06T21:28:43+11:00): C12 (Critical Constraints) names its readers: the lints through the runner, the tail script, the file-name-only presence pin, and P.1's builder and harness. An extra count-only scan of `author-session.jsonl` is not among them, and D4 defers the one other count-only reading, author overlap, to P.3. Round 21's "is within C12's permitted machine reads" was wrong.
  - /fix notes: applied 2026-11-06T21:28:43+11:00 by the stage-7 executor (leg x2), plan records only. Round 21's note is corrected in place, dated. There is no further scan before P.3. The one count already made is Task 0.5's own copy-in redaction step: the identifying forms were counted, 0 were found, and the log was copied unchanged (Task 0.5's Closed sub-bullet, item 1, re-read). Round 21's "with the user name redacted" now reads as that record does. C12's text is unchanged, and this leg did not open, list or search `validation/heldout-5/`.

- Verification counts: 1 defect claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 24 - 2026-11-06 - Stage-7 (H4 code slice re-check), independent cross-family codex peer review (stage-7.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Requested plan and harness-document diffs, corrected records and `validation.py` diff against `9884f04`; static reads only.
  - Round 19: checked the corrected C17 claim against every code hunk; both literal-list exceptions are accurately identified.
  - Stage-1 leg x2 / Task 0.2a: checked the constant/comment exception against task authorization and C17; correction is accurate.
  - Task 0.2b: checked the dated correction against `render_report`; its docstring is correctly distinguished from the permitted heading and amendments.
  - Round 21 / Task 0.5: checked the corrected scan advice and copy-in account against C12 and the task’s Closed record; consistent, without independently examining the log.
  - Round 22: checked verification and disposition; the two exceptions are accurately recorded without changing C17.
  - Round 23: checked fix notes; the Round 21 correction is present, but its handoff duplicate remains incorrect.
  - New handoff: checked the correction summary; accurate, but contradicted by the preceding leg’s retained advice.
  - C12 / C16 / C17: checked the plan diff; constraint text unchanged and no individual blind-case identifier added.
  - Harness document: checked the one-line correction; consistent with the recorded predictions.

#### Findings

- **PR-LOW-001** (LOW, docs-only, `.cursor/plans/plan-validation-run8.md:261`): The stage-7 leg x1 handoff retains the incorrect C12 permission and redaction account corrected in Round 21. This leaves contradictory operational advice in the handoff. - Evidence: “A count-only check (integers, no statement) is within C12 if you want that assurance before the push” and “with only the user name redacted”; the corrected Round 21 explicitly rejects that permission, and Task 0.5 records zero identifying occurrences and an unchanged copy. Recommendation: Fix-now - Add a dated correction to this duplicate handoff bullet, deferring further examination until P.3 and accurately recording the unchanged copy; preserve C12. /fix decision: Applied — verified tuple (PR-LOW-001, CONFIRMED, 🔁 same family as round 23 PR-LOW-001 — a sibling copy that round's fix missed, Fix-now record-only); one defect with round 25 PR-LOW-001.
  - /fix notes (stage-7 executor leg x3, 2026-11-06T21:33:33+11:00):
    - Line 261's two quoted sentences were re-read and confirmed. A dated correction now sits under that handoff bullet, kept as history: no scan before P.3, and the one count was Task 0.5's copy-in (0 found, log copied unchanged).
    - Sibling sweep over the plan, searching `within C12`, `user name redacted` and `only the user name redacted`. No other uncorrected copy was found. The other hits are:
      - D4 (C16-fixed) and Task 0.5's spec, which name the redaction STEP, not its result;
      - the stage-5 leg x2 handoff, which planned that step before it ran;
      - the peer rounds' own quotes;
      - round 21, already corrected.
    - C12's text is unchanged, and `validation/heldout-5/` was not opened, listed or searched.

- Verification counts: 1 defect claim checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 25 - 2026-11-06 - Stage-7 (H4 documents slice re-check), independent cross-family codex peer review (stage-7.p2)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Requested plan and harness-document diffs, corrected records, constraints and `validation.py` diff; static inspection only.
  - Round 19: checked the corrected C17 claim against the code diff; both literal-list exceptions are accurately identified.
  - Stage-1 leg x2 / Task 0.2a: checked the constant/comment qualification against the task and C17; correction is accurate.
  - Task 0.2b: checked the dated qualification against `render_report`; its changed docstring is correctly distinguished from the permitted heading and amendments.
  - Round 21: checked the corrected scan advice against C12; the additional scan is now deferred until P.3.
  - Task 0.5: checked the copy-in record; it records zero identifying-form matches and an unchanged log copy, supporting the corrected account.
  - Rounds 22–23 / new handoff: checked fix notes against corrected entries; those entries support the notes, but the earlier stage-7 handoff retains contradictory advice.
  - C12 / C16 / C17: checked the plan diff; constraint text remains unchanged, with no new specific blind-set identifier.
  - Harness-document LOW-001: checked the one-line correction against recorded predictions; correctly includes `heldout-4`.

#### Findings

- **PR-LOW-001** (LOW, docs-only, `.cursor/plans/plan-validation-run8.md:261`): Round 23’s correction missed the duplicate advice in the stage-7 leg-x1 handoff. It still presents an additional pre-P.3 scan as C12-permitted and incorrectly says the user name was redacted, contradicting the corrected Round 21 and Task 0.5 record. - Evidence: “A count-only check (integers, no statement) is within C12 if you want that assurance before the push”; “with only the user name redacted”. C12 enumerates permitted readers without this additional scan; Task 0.5 records “0 occurrences, so the log is copied unchanged”. Recommendation: Fix-now - Add a dated correction at this duplicate handoff entry, deferring the additional scan until P.3 and accurately recording the unchanged copy; preserve C12. /fix decision: Applied — verified tuple (PR-LOW-001, CONFIRMED, 🔁 same family as round 23 PR-LOW-001, Fix-now record-only); the same defect as round 24 PR-LOW-001, fixed once (round 24's `/fix` notes; the dated correction under line 261's bullet, 2026-11-06T21:33:33+11:00).

- Verification counts: 1 defect claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 26 - 2026-11-06 - Stage-7 (H4 code slice re-check), independent cross-family codex peer review (stage-7.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Requested plan and harness-document diffs, corrected records, constraints and `validation.py` diff against `9884f04`; read-only inspection.
  - Round 19: checked the corrected confinement claim; both literal-list exceptions match the code.
  - Stage-1 leg x2 / Task 0.2a: checked the constant/comment qualification; accurate.
  - Task 0.2b: checked the dated docstring qualification; accurate, but the separate Closed record retains the narrower, incorrect hunk description.
  - Round 21 / Task 0.5: checked scan advice and copy-in account; consistent with C12 and the recorded zero occurrences, without examining the log.
  - Rounds 22–23: checked fix notes against corrected entries; the named corrections are present.
  - Stage-7 leg x1: checked the new dated correction; explicitly withdraws both incorrect claims.
  - Stage-7 legs x2–x3 / Rounds 24–25: checked correction summaries; the C12 duplicate is fixed.
  - Plan-wide sibling check: checked permission, redaction and confinement claims; one remaining confinement-record duplicate identified below.
  - C12 / C16 / C17: checked the plan diff; constraint text unchanged, with no new individual blind-case identifier.
  - Harness document: checked the one-line correction; correctly includes `heldout-4` among predicted failures.

#### Findings

- **PR-LOW-001** (LOW, docs-only, `.cursor/plans/plan-validation-run8.md:1122`): Task 0.2b’s separate Closed record still claims every hunk fits a list restricting `render_report` changes to its heading and amendments. The dated correction above qualifies the earlier executor record, but this subsequent composer record repeats the inaccurate description without qualification. - Evidence: “every hunk … sits in … `render_report` (the heading and the amendments)”; the code diff also changes its docstring to include “four verdict lines and the marked-R1 line in that section”. Recommendation: Fix-now - Add the same dated docstring exception to this Closed record, preserving C17’s text and the code. /fix decision: Applied — verified tuple (PR-LOW-001, CONFIRMED, 🔁 same family as round 22 PR-LOW-001, whose fix missed these siblings; Fix-now record-only; no C17 amendment, no code change). The same defect as round 27 PR-LOW-001.
  - Verification (stage-7 executor leg x4, 2026-11-06T21:38:57+11:00): Task 0.2b's composer Closed record says every hunk of `git diff ba71ff5` sits in its list with `render_report` limited to "(the heading and the amendments)". The `@@ -3281,14` hunk also changes `render_report`'s docstring. Confirmed, and likewise Round 4's record (round 27).
  - /fix notes (exhaustive sweep). I searched the whole plan for `permitted list`, `C17 (b) holds`, `C17 (b):`, `every hunk`, `inside the permitted`, `confined to`, `sits in`, `within C17`, `inside C17`, `C17 (b)'s list`, `permitted symbols`, `C17 (b) as recorded`, `C17 (b) for`, `C17 holds`, `(b) nothing`, `(b) no`, and every `C17` mention. Each hit was read in full.
    - **QUALIFIED, dated `[2026-11-06, peer rounds 26–27 PR-LOW-001]`, beside the record, the record kept:**
      - the stage-2 leg x3 handoff, "Every `validation.py` hunk since `ba71ff5` is now in C17 (b)'s list" (`render_report`'s docstring);
      - the stage-2 leg x1 handoff, "C17 holds (the task line's record …)" (both hunks);
      - the stage-1 leg x1 handoff, "C17 holds (the task line's record)" (`RULE_SCHEMA_VERSION`);
      - Round 4's C17 (b) line, "inside the permitted list" (`RULE_SCHEMA_VERSION`);
      - Round 6's "**C17 (b).** The hunks are confined to the permitted symbols …" (round 7's corrections and the docstring);
      - Round 7's verify notes, "19 hunks, every one in C17 (b)'s list" (the docstring);
      - Task 0.2b's composer Closed record, "every hunk … sits in …" (the docstring).
    - **POINTERS added** where "three records" is now incomplete: the stage-7 leg x2 handoff and round 22's verification notes.
    - **ALREADY QUALIFIED** (rounds 22–23's fix): round 19's Checked bullet; the stage-1 leg x2 handoff ("inside C17 (b)'s permitted list"); Task 0.2b's "supersedes" record, "19 hunks, all inside C17 (b)'s list". The dated sub-bullet under the last also covers the leg-x1 task-line enumeration it supersedes ("`render_report` (heading, amendments)").
    - **CHECKED, no claim to qualify:**
      - C17's own text (left as is);
      - Task 0.2a's own C17 line and its composer Closed record: they name the constant explicitly ("confined to the `RULE_SCHEMA_VERSION` comment and value, …") and claim nothing about C17 (b)'s list;
      - the stage-2 leg x2 handoff, "C17 (b) as recorded on the task line: `evaluate_encounter` untouched": true, and it refers to that record;
      - the lineage line and Task 0.0, "C17 holds" with base `170345d` / "as written": the base, not the hunk list;
      - the stage-3 handoff's "C17 holds": Task 0.3 changed no package file;
      - every stage record whose "(b)" says nothing under `desktop/src` or no `validation.py` changed in that stage (stages 3–7): true;
      - the instruction to the H4 peer, "covers every hunk";
      - the "Reviewed: every hunk" scope lines of rounds 17 and 19;
      - the peer rounds' own quotes (rounds 7, 22, 26, 27): kept as history;
      - the Deferred bullet (round 19 LOW-002) and round 20's C17 (b) references: about the bar, not a confinement claim.
    - C17's text and the code are unchanged. No document changed.
    - `[2026-11-06T21:44:32+11:00, peer round 28 PR-LOW-001]` The sweep above was NOT exhaustive. It searched confinement wordings and missed two round summaries:
      - Round 8's Scope line ("permitted-symbol compliance"), qualified by leg x5 (the `render_report` docstring);
      - Round 5's Scope line ("C17 boundaries" with 0 findings), qualified by leg x5 (`RULE_SCHEMA_VERSION`).
      - So NINE records were qualified in legs x4–x5, not seven. Leg x5's one further search (round-summary and compliance wordings, listed in its handoff bullet) found no others.

- Verification counts: 1 defect claim checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 27 - 2026-11-06 - Stage-7 (H4 documents slice re-check), independent cross-family codex peer review (stage-7.p2)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Requested plan and harness-document diffs, corrected records, whole-plan sibling search and `validation.py` diff against `9884f04`; read-only inspection.
  - Round 19: checked the qualified C17 claim against the code diff; both exceptions accurately identified.
  - Stage-1 leg x2 / Task 0.2a: checked the constant/comment qualification; accurate.
  - Task 0.2b: checked the dated docstring qualification; accurate, but its Closed record retains the narrower claim.
  - Round 21: checked scan advice against C12; further examination correctly deferred until P.3.
  - Task 0.5: checked the Closed copy-in record; zero identifying-form matches and an unchanged copy support the correction.
  - Rounds 22–23: checked fix notes against corrected entries; the named corrections are present.
  - Stage-7 leg x1 / Round 25: checked the new dated correction; both incorrect claims are explicitly superseded.
  - Stage-7 legs x2–x3: checked correction summaries; consistent with the amended entries.
  - C12 / C16 / C17: checked the working-tree diff; constraint text unchanged, with no newly added individual blind-case identifier.
  - Harness-document LOW-001: checked the one-line correction against recorded predictions; correctly includes `heldout-4`.

#### Findings

- **PR-LOW-001** (LOW, docs-only, `.cursor/plans/plan-validation-run8.md:601`): The C17 correction still has unqualified sibling claims elsewhere in the plan. Round 4 includes `RULE_SCHEMA_VERSION` in hunks declared inside the permitted list; Task 0.2b’s Closed record at line 1122 still confines `render_report` changes to its heading and amendments. Neither record carries the dated qualification applied to the other copies. - Evidence: line 601 lists “the `RULE_SCHEMA_VERSION` comment and value” and concludes “inside the permitted list”; line 1122 says “every hunk” sits in its enumeration including “`render_report` (the heading and the amendments)”. C17 at line 214 omits the constant and report docstring, while the code diff changes both. Recommendation: Fix-now - Add dated qualifications to these two historical records, preserving C17 and the already-correct code. /fix decision: Applied — verified tuple (PR-LOW-001, CONFIRMED, 🔁 same family as round 22 PR-LOW-001, Fix-now record-only; no C17 amendment, no code change). This is the same defect as round 26 PR-LOW-001 and was fixed once in one exhaustive sweep. Round 4's line and Task 0.2b's composer Closed record are qualified, together with five more siblings the sweep found (`[2026-11-06]` and, after peer round 28, Rounds 8 and 5 by leg x5); round 26's `/fix` notes list every location checked and what was done at each (stage-7 executor leg x4, 2026-11-06T21:38:57+11:00).

- Verification counts: 1 defect claim checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 28 - 2026-11-06 - Stage-7 (H4 code slice re-check), independent cross-family codex peer review (stage-7.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Requested plan and harness-document diffs, corrected records, whole-plan sibling search and `validation.py` diff against `9884f04`; read-only inspection.
  - Stage-2 leg x3: checked the qualification; accurately identifies the report-docstring exception.
  - Stage-2 leg x1: checked both exceptions against the code and tasks; accurate.
  - Stage-1 leg x1: checked the constant/comment exception; accurate.
  - Round 4: checked the permitted-list qualification; accurate.
  - Round 6: checked the correction against the subsequent fold/reversions and remaining docstring exception; accurate.
  - Round 7: checked the qualified nineteen-hunk claim; accurately excludes the report docstring.
  - Task 0.2b Closed record: checked the new qualification; accurate.
  - Round 19: checked both recorded exceptions against the code diff; accurate.
  - Stage-1 leg x2 / Task 0.2a: checked the qualification and explicit constant authorization; consistent.
  - Task 0.2b superseding record: checked the dated docstring exception; accurate.
  - Round 21 / Task 0.5: checked scan advice against C12 and the recorded copy-in result; no further scan permitted, zero matches and unchanged copy recorded.
  - Stage-7 leg x1: checked the dated correction; both incorrect claims explicitly withdrawn.
  - Stage-7 legs x2–x4 / Rounds 22–27: checked correction summaries and pointers; listed corrections present, but the exhaustive-sweep claim misses Round 8.
  - Whole-plan sibling search: checked confinement and scan-permission claims; one unqualified compliance claim remains below.
  - C12 / C16 / C17: checked the working-tree diff; constraint text unchanged, with no newly added individual blind-case identifier.
  - Harness-document LOW-001: checked the one-line correction against recorded predictions; correctly includes `heldout-4`.

#### Findings

- **PR-LOW-001** (LOW, docs-only, `.cursor/plans/plan-validation-run8.md:706`): Round 8 retains an unqualified confirmation of permitted-symbol compliance, despite the report-docstring exception now acknowledged in the surrounding records. The seven-record sweep missed this sibling. - Evidence: “Confirmed Round 6–7 fixes, unchanged C17 text, permitted-symbol compliance”. C17 names “the heading / the amendments”, while the code diff also changes `render_report`’s docstring to describe “four verdict lines and the marked-R1 line in that section”. Recommendation: Fix-now - Add a dated qualification to Round 8 naming the task-authorised docstring exception, and update the sweep record; preserve C17 and the code. /fix decision: Applied — verified tuple (PR-LOW-001, CONFIRMED, 🔁 same family as round 22 PR-LOW-001, a sibling leg x4's sweep missed; Fix-now record-only; no C17 amendment, no code change).
  - Verification (stage-7 executor leg x5, 2026-11-06T21:44:32+11:00): Round 8's Scope line reads "Confirmed Round 6–7 fixes, unchanged C17 text, permitted-symbol compliance". Its diff was Task 0.2b's against `ba71ff5`, whose `render_report` heading hunk also changes the docstring that C17 (b)'s literal list does not name. The claim is unqualified: confirmed. The constant is Task 0.2a's, outside that diff, so it is not named for Round 8.
  - /fix notes:
    - A dated qualification now sits under Round 8's Scope line (the docstring).
    - The one further search, plan-wide, over the Review History, the Findings Log and the Current State / Handoff Note: `symbol compliance`, `symbol-level`, `permitted-symbol`, `permitted symbol`, `C17 held`, `C17 hold`, `C17 unchanged`, `C17 text`, `unchanged C17`, `C17 boundar`, `C17 compliance`, `compliance`, `complies`, `compliant`, `C17 remain`, `C17(b)`, `C17 … confirmed` / `confirmed … C17`, and every Review History line holding `C17`. It found ONE more sibling: Round 5's Scope ("C17 boundaries", 0 findings, over Task 0.2a), now qualified (`RULE_SCHEMA_VERSION`).
    - The counts are corrected — nine records in legs x4–x5, not seven — in round 26's `/fix` notes, round 22's verification pointer, round 27's `/fix` decision and the leg x4 handoff bullet.
    - Every other hit is listed in the leg x5 handoff bullet, with what was done at each.
    - C17's text and the code are unchanged. No document changed.

- Verification counts: 1 defect claim checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 29 - 2026-11-06 - Stage-7 (H4 documents slice re-check), independent cross-family codex peer review (stage-7.p2)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Requested plan and harness-document diffs, corrected records, whole-plan sibling search and `validation.py` diff against `9884f04`; read-only inspection.
  - Stage-2 leg x3 handoff: checked the qualification against the report hunk; correctly identifies the docstring exception.
  - Stage-2 leg x1 handoff: checked both exceptions against task authorization and C17; accurately qualified.
  - Stage-1 leg x1 handoff: checked the constant/comment exception; accurately qualified.
  - Round 4: checked its permitted-list claim; the adjacent correction explicitly excludes the constant/comment.
  - Round 6: checked its confinement claim; the correction distinguishes the reverted edits from the remaining report-docstring exception.
  - Round 7 verification notes: checked the “every one” claim; the adjacent docstring qualification corrects it.
  - Task 0.2b Closed record: checked the heading/amendments enumeration; its new qualification explicitly includes the omitted docstring.
  - Stage-1 leg x2 handoff: checked the earlier constant/comment correction; accurate.
  - Task 0.2b superseding record: checked the earlier docstring correction and its relationship to the initial task record; accurate.
  - Round 19: checked the qualified compliance claim against the code diff; both literal-list exceptions are correctly identified.
  - Round 21: checked the corrected scan advice against C12 and Task 0.5; no additional scan is authorized before P.3.
  - Stage-7 leg x1 handoff: checked the duplicate scan/redaction advice; its dated correction explicitly withdraws both incorrect claims.
  - Task 0.5: checked the copy-in record; zero identifying-form matches and an unchanged copy support the corrected account.
  - Stage-7 legs x2–x4 handoffs: checked correction summaries and the expanded sibling list; consistent with the amended records.
  - Rounds 22–27 fix records: checked correction locations and dispositions; the named qualifications are present, and historical finding quotations remain distinguishable from operative claims.
  - Whole-plan sibling search: checked confinement, permission and redaction wording; no remaining unqualified copy of either corrected claim found.
  - C12 / C16 / C17: checked the working-tree changes; constraint text and frozen decisions remain unchanged, with no newly introduced individual blind-case identifier.
  - Harness-document LOW-001: checked the one-line correction against recorded predictions; correctly includes `heldout-4` among predicted failures.

#### Findings

- Verification counts: 18 claims checked, 18 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

### Round 30 - 2026-11-06 - Stage-7 (H4 code slice re-check), independent cross-family codex peer review (stage-7.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Specified plan and harness-document diffs, corrected records, whole-plan sibling search and `validation.py` diff against `9884f04`; read-only inspection, no writes or execution.
  - Stage-2 leg x3 handoff: checked the confinement qualification; correctly identifies the report-docstring exception.
  - Stage-2 leg x1 handoff: checked both exceptions against the code and task records; accurate.
  - Stage-1 leg x1 handoff: checked the constant/comment qualification; accurate.
  - Round 4: checked the permitted-list correction; correctly excludes the constant/comment.
  - Round 5: checked the new scope qualification; accurately identifies Task 0.2a’s constant/comment exception.
  - Round 6: checked the corrected confinement claim; distinguishes reverted edits from the remaining docstring exception.
  - Round 7 verification notes: checked the qualified nineteen-hunk claim; accurately identifies the remaining docstring exception.
  - Round 8: checked the new qualification; correctly withdraws literal permitted-symbol compliance and distinguishes its baseline from Task 0.2a.
  - Task 0.2b Closed record: checked the heading/amendments enumeration; the adjacent qualification covers the docstring.
  - Stage-1 leg x2 handoff: checked the constant/comment correction against Task 0.2a; accurate.
  - Task 0.2b superseding record: checked the dated docstring correction; accurate.
  - Round 19: checked both exceptions against the code diff; accurately qualified.
  - Round 21: checked scan advice against C12; no additional scan authorized before P.3.
  - Stage-7 leg x1 handoff: checked the dated correction; both incorrect permission and redaction claims explicitly withdrawn.
  - Task 0.5: checked the copy-in record; records zero identifying-form matches and an unchanged copy, without independently examining the log.
  - Rounds 22–28 fix records: checked dispositions and correction pointers; named corrections are present.
  - Stage-7 legs x2–x5 handoffs: checked correction summaries and sweep accounting; nine additional qualified records match the enumerated locations.
  - Whole-plan sibling search: checked compliance, confinement, scan-permission and redaction claims; no remaining unqualified copy of either corrected claim found.
  - C12 / C16 / C17: checked constraint text against HEAD; identical, with no new individual blind-case identifier introduced by the edits.
  - Harness-document LOW-001: checked the one-line correction against recorded predictions; correctly includes `heldout-4`.

#### Findings

- Verification counts: 20 claims checked, 20 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-11-06

## Tasks

### Phase 0 — The rule, the predictions, the blind set (the order is the point; C16)
- [x] ✅ **0.0 The order against `plan-gpu-decoding.md`** `[decision]` (practitioner; peer rounds 1–2 PR-HIGH-001 / PR-HIGH-002) — Options: **(A) this plan first** — run 8 is THIS plan's: `heldout-5` under rule v5 with `medium` on CPU; the GPU-decoding plan's run, if its Task D reaches outcome (i), becomes run 9 on a FRESH blind set (`heldout-6`, pre-registered first — `heldout-5` is used once), and its decode change lands only after this plan's P.1 (C17 holds as written); **(B) the GPU-decoding plan first** — this plan goes `Lifecycle State: Paused` (Paused reason: waiting on `plan-gpu-decoding.md` Task D) and is RE-PLANNED after that outcome: under its (i) `heldout-5`, predictions v4 and run 8 are ITS, and this plan's rule v5 is re-based onto ITS re-measured reports (D5's run-7 source void; this plan's run is run 9 on a fresh set); under its (ii) the installed build becomes 0.3.6 with the GPU as a speed setting, so the seen sets are re-measured on the installed configuration and D5 is re-based; under its (iii) this plan resumes as (A) with every C17 base moved to that plan's last decode-affecting commit. Decide before: 0.2a. Blocks: 0.2a–P.4′. **Done when ALL of:** `Chosen: … (date)` on this line; a dated line on BOTH plans' Plan Lineage (the GPU plan's by its own session or the practitioner — never by this plan's executor); for the chosen order BOTH plans' operative tasks amended and reviewed (this plan's by a scoped `/review-plan` over the amended tasks; the GPU plan's by its session) on: run and blind-set ownership (which run is 8 and on which set; the other run 9 on `heldout-6`), the prediction sources (D5), every C17 comparison's base commit ((a), (b) and (c) alike), the validated installed configuration (D7's sentence; the Accepted Assumption on 0.3.5), and the files BOTH plans edit — `validation.py`'s `REFERENCE_TAIL_STARTS` `h5-` rows, `heldout_transcripts.py`'s `heldout-5` row, `test_lint_held_out_set.py`'s blind pin, `validation/README.md`, `validation-harness.md`, `plan-pilot.md` P.5, the findings register, `AGENTS.md`, `CHANGELOG.md`, `.github/workflows/ci.yml` — whichever plan runs second inherits the first's edits and re-bases its task text. Until then 0.2a is refused: C9 serialises the loops, it does not reconcile these (PR-HIGH-002). **Chosen: A (2026-11-06)** — the practitioner's words, relayed by the top session: "A, and close the four old runs". This plan's half of the Done-when is in (the lineage line below; C17's base `170345d`; the installed-configuration assumption holds; the scoped `/review-plan` fast-path checklist, Review History); the GPU plan's half (its dated lineage line; its run renamed run 9 on a fresh pre-registered `heldout-6`; its decode change after this plan's P.1) is being written by ITS session (`local_23bac8ee`), never from here. That half landed in `6fb6676` (2026-11-06, with its scoped `/review-plan` in its Review History), so 0.2a is unblocked.
- [x] ✅ **0.1 The plan's commit** (practitioner's word, 2026-11-06: "commit", after the converged peer pass and BEFORE Task 0.0 was decided — 0.0 still blocks 0.2a; the hash is recorded at 0.2a) — this file alone; it holds D1–D8 and C16–C18 (the untracked skeleton of 2026-11-06 is this file). Done when: committed on the practitioner's word.
- [x] ✅ **0.2a Rule v5: schema 4, the field, the file, the loader pins** (D1; C2, C16, C18) — `RULE_SCHEMA_VERSION` → 4 (`validation.py:208`, its comment); `PassRule.schema_version: Literal[1, 2, 3, 4]` (`:2318`) and the docstring (`:2308-2314`); `SetCeilings.r1_marked_reported: bool | None = None` with its docstring (`:2275-2291`); `_check_sets` (`:2327-2350`): the exemption gate `>= 3`, the new field required non-None on schema 4 and refused non-None below it; `validation/rules/rule-v5.json` (D1's rows, LF). Tests (`test_validation_metrics.py`): the schema-5 refusal replaces `{"schema_version": 4}` at `:3121`; `:3448` → 4; the comment `:3071-3072`; the exemption messages re-pinned (`:3126, :3132, :3138, :3144, :3187` — `pytest.raises(match=…)`); the new field refused on schemas 1–3 and required on 4; the exemption accepted on schema 4; a `_RULE_V5` fixture beside `_RULE_V2` / `_RULE_V3` (`:3319-3323`); `TestRuleV5` — six rows in rule v4's key order, C18's field-by-field equality with `rule-v4.json` excluding `r1_marked_reported` on both sides, `heldout-5` the only `true`, `label == "v5"`, gate names exactly `{"scripts", "heldout-5"}`; `test_every_repository_rules_label` (`:3639-3652`) gains `rule-v5.json` → "v5". Its own dated commit. Done when: ruff, mypy, the plain suite green; the rule's blob recorded here.
  - **Built, suite owed (2026-11-06T14:54+11:00, stage-1 executor leg x1; ruff and mypy green, pytest composer-run).** `validation.py`: `RULE_SCHEMA_VERSION` 4 and its comment; `SetCeilings.r1_marked_reported` and its docstring; `PassRule` schema-4 docstring paragraph and `Literal[1, 2, 3, 4]`; `_check_sets` — exemption gate `>= 3`, its messages `a schema-{n} rule needs unsupported_line_r1_exemption` / `only a schema-3 or later rule takes unsupported_line_r1_exemption`; per row, schema `>= 4` requires `r1_marked_reported` (`a schema-{n} rule needs r1_marked_reported on every set`), below it a non-None value is refused (`only a schema-4 or later rule takes r1_marked_reported`; a schema-1 rule is refused earlier by "holds no set ceilings"). `validation/rules/rule-v5.json` NEW (LF, rule v4's key order, `r1_marked_reported` last in each row). Tests (`test_validation_metrics.py`): the schema-5 and schema-0 refusals; the two "only a schema-3 or later" pins; schema-4 rows for the exemption (missing, null, no sets) and the new field (refused on schemas 1–3, required on every schema-4 row incl. a second row missing it, a non-bool refused); `test_below_schema_4_only_a_non_null_marked_field_is_refused` (schemas 2–3 × None/True/False); `test_schema_4_takes_the_exemption_and_the_marked_field_either_way` (2 × 2); `_RULE_V5` beside `_RULE_V3`; `TestRuleV5` (the file equal field by field, row order, gates exactly `{"scripts", "heldout-5"}`, `label == "v5"`, `RULE_SCHEMA_VERSION == 4`; `heldout-5` the only `true`; C18's equality with `rule-v4.json` excluding `r1_marked_reported` on both sides; the raw file LF / no NUL / rule v4's key order; the fixture); `test_every_repository_rules_label` gains `rule-v5.json` → "v5"; the label derivation gains five schema-4 rows (`rule-v6-test` → "v6"). Trivial deviation, noted: the `RULE_SCHEMA_VERSION` pin moved from `TestRuleV3`'s file test (now `rule.schema_version == 3` and no row carrying the field) to `TestRuleV5`; `TestRuleV2`'s file test also pins no row carrying the field. **Between 0.2a and 0.2b (by design, nothing reads the field yet):** a schema-4 rule loads and renders under the existing report code without a schema-4 branch — two verdict lines, rule v2's amendments sentence, marked R1 counted under the R1 ceiling (rule v4's verdict) — no crash; `rule_v2_counterpart(rule-v5, "scripts")` reads `differs` (row `False` vs `None`) until 0.2b neutralises it; the `SetCeilings` docstring states the reading 0.2b implements. **C17 (stage-1):** `git diff --stat 170345d -- desktop/src validation/config validation/scripts scripts/build-validation-set.py scripts/run-validation.py` (working tree) lists `validation.py` only; its diff is confined to the `RULE_SCHEMA_VERSION` comment and value, `SetCeilings`, `PassRule`'s docstring / `schema_version` and `_check_sets`; `scripts/run-validation.py` unchanged. Rule blob: owed — the composer records it at the commit.
  - **Suite and review (2026-11-06T15:10+11:00, leg x2):** composer suite 9471 passed / 0 failed / 9 skipped; `/review-loop` round 4 converged — one LOW (the `SetCeilings` docstring's opening), applied; ruff and mypy green; the suite re-run owed for that docstring change.
  - **Closed (2026-11-06T15:26+11:00, composer):** suite re-run 9471 passed / 0 failed / 9 skipped; codex peer round 5 (pass stage-1.p1) 0 findings, converged; C17 (a) empty since `170345d`; C17 (b) recorded by leg x2 (the `validation.py` changes confined to `SetCeilings` / `PassRule` / `_check_sets` / `RULE_SCHEMA_VERSION`); the rule's blob `validation/rules/rule-v5.json` = `3f3bb7acf6f16074d2e0e37767fa387a7f37c015`; committed alone (the commit's hash is recorded at 0.2b and in the run-state bullet).
- [x] ✅ **0.2b Rule v5: the reading, the fourth verdict, the report** (D1; C16, C18) — `FactOutcome.residue_r1_silent` / `residue_r1_marked` (`:938-947` region; the both-case precedence); `ClassCount.reported_members` (fifth, defaulted; `:2674-2687`) and `class_counts` (`:2690-2716`: `row.r1_marked_reported is True` → R1 `total` / `members` silent-only, `reported_members` the marked); `PassRule.counting_marked_r1()` (row-wise `model_copy`; `self` when no row reports); `rule_v2_counterpart` comparing `r1_marked_reported` `False` / `None` as equal and `True` as `differs` (`:2453-2457`); the heading (`:3285-3302`) and `_verdict_lines` (`:3203-3267`) printing the fourth verdict `rule {label} with marked R1 counted` on schema 4 (the name from `PassRule.label`; a schema-4 report pin with a non-v5 name, `rule-v6-test` → "v6" — PR-LOW-002; no printed "= rule v4" claim — PR-MED-002); the amendments paragraph's gates (`:3314` → `>= 3`; `:3331` → `label == "v4" or schema_version >= 4`; the v5 sentence); `_residue_section` (`:3587-3603`: the R1 row's name where the row reports; the new line after `- R1: …` on every schema-4 row; `:3614` → `>= 3`); the strings `:3785-3786`, `:3850`, `:3905`; docstrings `:974, :1127-1134, :1958, :2374, :2386, :2400, :2640-2643, :3130, :3206-3212, :3283` where they say "schema 3" is the newest. Tests: the split both ways on hand-built outcomes (a marked wrong R1 fact counts under `false`, is reported under `true`; a silent R1 fact counts under both; the both-case counts and is not reported); `rule_v2_counterpart` `same` × 4 / `no_row` × 2 on rule v5 and `differs` on a hand-built schema-4 rule with `True` on `scripts`; `counting_marked_r1()` equal to rule v4's `run_passed` on invented outcomes and to verdict 1 on the five seen rows; a whole `heldout-5` report on invented outcomes, every line (four verdict lines and no fifth; the R1 row's name and ceiling; the new line; the Facts column's `R1` on both kinds; `set_level`'s silent-only count); a whole seen-row (`heldout-4`) rule-v5 report (the "counted under the ceiling" line); the rule-v4 label pin and the rule-v3 whole-report pins unchanged (`test_validation_harness.py:2513-2581`, `:2673-2857`) plus the mirror pin "no `v5`, no marked-R1 line" in the rule-v4 report; the help test `:1444-1461` moved to rule v5's six names and the refusal wording `:1352`; a `main` pin "a schema-4 rule needs --set". Done when: ruff, mypy, the plain suite green; C17's diff review recorded here.
  - **Built, suite owed (2026-11-06T15:37+11:00, stage-2 executor leg x1; ruff and mypy green, pytest composer-run).** `validation.py`: `FactOutcome.residue_r1_silent` (`residue_r1 and silent_omission`) / `residue_r1_marked` (`residue_r1 and verdict == "wrong" and not silent_omission`) — every R1 fact exactly one kind, the both-case silent; `ClassCount.reported_members` (fifth, defaulted `()`); a helper `_r1_marked_members(outcomes)` (read by `class_counts` and `_residue_section`); `class_counts` — on a row with `r1_marked_reported is True` R1's `total` / `members` silent-only and the marked facts in `reported_members`, empty everywhere else; `PassRule.counting_marked_r1()` (row-wise `model_copy`, key order kept, `self` when no row reports); `rule_v2_counterpart` compares rows with `gate` neutralised and a `False` `r1_marked_reported` set to `None` (so `False` = rule v2's `None`, `True` → `differs`); the heading prints four verdicts on schema 4 (`rule {label} {v}, rule {label} with marked R1 counted {v}, rule {label} without the R1 exemption {v}, rule v1 {v}`) and `_verdict_lines` the new second line `- Rule {label} with marked R1 counted verdict (the same outcomes, every marked R1 fact counted under the R1 ceiling): …` (no "= rule v4" claim) — verdict lines 1, 3 and 4 print as under schema 3 but for the label (D5); the amendments — rule v3's history `>= 3`, rule v4's sentence `label == "v4" or schema_version >= 4`, rule v5's sentence; `_residue_section` — the R1 row `R1 recogniser (silent only; marked R1 reported below)` where the row reports, the new line after `- R1: …` on every schema-4 row, the excused-lines gate `>= 3`; "schema-2 or later" in the `--set` help, `main`'s docstring and the `--set` refusal (`:3911`'s `schema-{n}` f-string unchanged); the docstrings that called schema 3 the newest (`EncounterMetrics` ×2, `exempts_r1_lines`, `set_row`, the `RULE_V2_RATIFIED` comment, `rule_failures`, `run_passed`, `_verdict_lines`, `render_report`, `_residue_section`). Tests — `test_validation_metrics.py` `TestRuleV5Reading` (the split both ways incl. the both-case and four non-R1 facts; counted under `false` / reported under `true` / silent under both / both-case never reported; a schema-3 row counts all; the reporting row's ceiling at 1 and 2 silent with 0–5 marked, the counting row's at 1 and 2; `counting_marked_r1()` on `rule-v5.json` and `self` on rules v1–v4; the exemption off keeps the field; `counting_marked_r1()` = the real `rule-v4.json`'s `run_passed` on 15 invented shapes × six rows, and = rule v5's own verdict on the five seen rows; `heldout-5` alone reads differently; `rule_v2_counterpart` `same` × 4 / `no_row` × 2 on rule v5, `differs` with `True` on `scripts`, `same` with `False`); `test_validation_harness.py` — a whole `heldout-5` report (every line, the run-information line in full; four verdict lines then a blank; the R1 row's name and silent-only count; the marked line; `R1` on both kinds), the blind row's set-level at 1 and 2 silent facts, a whole `heldout-4` report under rule v5 (every line; equal to rule v3's report on the same outcomes but for D5's lines), the `rule-v6-test` schema-4 label pin (no `v5` anywhere, no "= rule v4"), the `True`-on-`scripts` report reading "not rule v2's verdict", the marked line with nothing measured, the mirror pin over rule v3 / rule v4 reports (no `v5`, no "marked R1", R1 under its old name, three verdict lines), the refusal wording, `test_the_repository_rule_v5_needs_one_of_its_six_sets` ("a schema-4 rule needs --set …"), the help test renamed to rule v5's six names (`_repository_rule_v5`). The rule-v3 and rule-v4 whole-report pins are byte-unchanged. **Trivial deviations, noted:** (i) the new residue line's separator is ASCII ` - ` (`- R1 marked wrong (reported, no ceiling): 2 - syn-001/f0, syn-003/f1`), not D1's "—", keeping every report string ASCII as the rest are; (ii) rule v5's sentence is gated `label == "v5" and schema_version >= 4` (a schema-3 file named `rule-v5…` never claims schema 4) and names the row's reading, "(this set reports them)" / "(this set counts them under the ceiling)" — the exemption sentence's "(applied under this rule)" shape; its text: "Rule v5 (schema 4; validation-run8 D1, decided 2026-11-06) keeps rule v4's predicates and ceilings and, on a row that reports marked R1, counts only the silent R1 facts under the R1 ceiling and prints the marked ones (a misheard material fact under a review mark) beside it with no ceiling (…); the verdict with marked R1 counted is printed beside it."; (iii) the strings read "schema-2 or later" (hyphenated, as 0.2a's "schema-3 or later"); (iv) **`evaluate_encounter`'s docstring line (`:1958` at planning, "read only by a schema-3 rule") is NOT edited**: the task line names it but C17 (b) says "never `evaluate_encounter`", and a Critical Constraint wins — the one stale word stays until C17 lapses after P.1 (rec: leave it; a one-line docstring fix in a post-P.1 commit). **C17 (stage-2):** (a)/(c) `git diff --stat 170345d -- desktop/src validation/config validation/scripts scripts/build-validation-set.py scripts/run-validation.py` (working tree) lists `validation.py` only; `scripts/run-validation.py` unchanged. (b) `git diff ba71ff5 -- desktop/src/scribe_desktop/validation.py` read hunk by hunk: `FactOutcome` (the two properties), `EncounterMetrics` (two docstrings, task-named), `PassRule` (`exempts_r1_lines` docstring, `counting_marked_r1`, `set_row` docstring), the `RULE_V2_RATIFIED` comment, `rule_v2_counterpart`, `rule_failures` and `run_passed` (docstrings only, task-named), `ClassCount` / `_r1_marked_members` / `class_counts`, `_verdict_lines`, `render_report` (heading, amendments), `_residue_section`, `_parser`'s help, `main`'s docstring and refusal — never `evaluate_encounter`, the alignment, `_FactState`, the reference reading, the metric amendments or `UNCERTAINTY_THRESHOLD`. No `h5-` `REFERENCE_TAIL_STARTS` row (Task 0.5's). No logging added; the report prints ids, counts and fixed text only.
  - **Suite and review (2026-11-06T15:52+11:00, leg x2):** composer suite 9613 passed / 0 failed / 9 skipped (712 s); C17 (a) empty (composer). `/review-loop` round 6 converged on its first round: two LOWs, both applied. One is a new test pinning the rule-v5 sentence's schema-3 side (`test_a_schema_3_rule_named_v5_prints_no_rule_v5_sentence`); the other the Overall Progress line's wording. ruff and mypy green; the suite re-run is owed for the new test.
  - **Peer round 7 (2026-11-06T16:08+11:00, leg x3):** suite 9614 passed / 0 failed / 9 skipped (697 s). Codex round 7's PR-LOW-001 (C17 (b) vs the record) was confirmed and applied by making the diff fit C17 (b) as written; behaviour is unchanged:
    - `_r1_marked_members` is folded into `class_counts` and `_residue_section`;
    - the `EncounterMetrics` ×2, `RULE_V2_RATIFIED`, `rule_failures` and `run_passed` docstring and comment edits are reverted to `ba71ff5`.

    **This supersedes the leg-x1 record above in two places:**
    - the task-named docstrings at `:974`, `:1127-1134`, `:2400`, `:2640-2643` and `:3130` are NOT edited in 0.2b. With `:1958` (deviation (iv)), they are left for one docstring-only commit after P.1, where C17 lapses;
    - C17 (b)'s hunk list now reads `FactOutcome` (the two properties), `PassRule` (`exempts_r1_lines` and `set_row` docstrings, `counting_marked_r1`), `rule_v2_counterpart`, `ClassCount` / `class_counts`, `_verdict_lines`, `render_report` (heading, amendments), `_residue_section`, `_parser`'s help, and `main`'s docstring and refusal — 19 hunks, all inside C17 (b)'s list.
    - `[2026-11-06, peer round 22 PR-LOW-001]` Not quite: the `render_report` heading hunk also changes the function's docstring (the "four verdict lines and the marked-R1 line" sentence), and C17 (b)'s list names the heading and the amendments, not the docstring. That docstring is correct and inert (no decoding or routing). With Task 0.2a's `RULE_SCHEMA_VERSION` value and comment, it is one of the two task-authorised hunks outside C17 (b)'s literal list. C17's own text is unchanged (round 22's `/fix` notes).

    ruff and mypy green; the suite re-run is owed.
  - **Closed (2026-11-06T16:25+11:00, composer):** suite re-run after the fold 9614 passed / 0 failed / 9 skipped (651 s); codex peer round 8 (pass stage-2.p1, re-check) 0 findings, converged; C17 (a) empty since `170345d`; C17 (b) read by the composer — every hunk of `git diff ba71ff5 -- desktop/src/scribe_desktop/validation.py` sits in `FactOutcome` / `PassRule` / `rule_v2_counterpart` / `ClassCount` / `class_counts` / `_verdict_lines` / `render_report` (the heading and the amendments) / `_residue_section` / `_parser` / `main`, and peer round 8 confirmed the same (`[2026-11-06, peer rounds 26–27 PR-LOW-001]` but for `render_report`'s docstring, which the heading's hunk also changes and C17 (b)'s literal list does not name. It is inert, and C17's text is unchanged; see round 22's `/fix` notes); C16: `rule-v5.json` unchanged since Task 0.2a (`ba71ff5`). Task 0.2a's commit is `ba71ff5`; 0.2b is committed alone.
- [x] ✅ **0.3 Predictions v5** (D5; C17) — `.cursor/loops/run8-predict.py` (NEW; `utf-8-sig`): parses the five run-7 reports into outcome objects, asserts the rule-v3 verdict lines and residue section reproduce byte for byte, then prints each seen set's rule-v5 lines (ids, counts, verdicts); the per-fact rule applied — the six R1 members asserted by id and listed with their kind, an ambiguous R1 member refused (PR-MED-001); the C17 check recorded. Frozen on this task and committed. Done when: on the task and committed.
  - **Script written, run owed (2026-11-06T16:33+11:00, stage-3 executor leg x1).** `.cursor/loops/run8-predict.py` (NEW, git-ignored, imported by nothing). It reads only the five `run7-reports/report-<set>.md` (decoded `utf-8-sig`; CRLF split, a NUL or a stray line break refused) and `validation/rules/rule-v3.json` / `rule-v5.json` through `validation.load_pass_rule`; it never reads `run8-reports/`, `validation/heldout-5` or any pickle. In order, each step only once the one before holds:
    1. **Parse** the run information, the encounter table, the checker warnings (tally, `failing:`, `expected but absent:`), the Facts table, the excused lines (`<id>/line n (segment i)`), the joined-run credit totals and the reference-boundary record.
    2. **The R1 members, FIRST:** an R1 member `wrong` with Ambiguous `yes` is refused (exit 2, its id printed); then the members must be exactly D5's six by id, `wrong` / Ambiguous `no` marked and `omitted` silent (exit 4 otherwise, the ids printed).
    3. **The outcome objects** (`FactOutcome` / `EncounterMetrics` / `EncounterOutcome`, the harness's own types). An encounter whose "Silent omissions" cell exceeds its material omitted unwarned facts holds a silent omission the report cannot place on a fact, so it is refused (exit 2, its id) — the per-fact rule's sibling for a non-R1 fact (none expected: no report holds an Ambiguous `yes` fact). The six kinds are re-read through the harness's `residue_r1_silent` / `residue_r1_marked` (exit 4 on a difference).
    4. **The reproduction:** `render_report` at HEAD under rule v3 must equal each report line for line — the heading, the three verdict lines and the residue section byte for byte; as a check of the parse also the run information, the checker warnings, the Facts table and the encounter rows, less the four columns no rule reads and the report cannot rebuild (WER, the run-1 and 0.3.3 silent columns, Surfaced (acoustic only)) and the TOTAL row's two seconds totals (rounded per row). Exit 3 otherwise, naming the set, the report's line number and the region, never the line's text.
    5. **Only then the predictions**, per seen set, from `render_report` under rule v5: the heading with its four verdicts; the four verdict lines (every failing id and reason); the residue section (every member, R1's split on the marked line, the after-class and excused counts, surfaced / expected, the `clinician_line_omitted` total / median / maximum, the reference-boundary record); Check 6 per next-patient axis script (id: `possible_next_patient` count, reference boundary, tail start, R3); and the lines rule v5's render changes against rule v3's on the same outcomes, by D5's categories (heading, verdict line, run information, residue heading, R1 row, R1 marked line, after-classes line). Exit 6 if a line outside D5's list differs, after the sets print. Also printed: the harness commit (`validation.read_commit`) and the SHA-256 of both rules and the five reports.
  - Exit codes: 0 printed; 2 refused (D5); 3 rule v3 not reproduced; 4 the R1 members are not D5's six; 5 an input unreadable or not in the shape expected; 6 a difference outside D5's list.
  - Design notes. WER is rebuilt only to the report's three decimals; the script refuses either rule if it holds a WER threshold (both are null). The joined-run credit totals are placed on the first measured encounter (printed as totals only; 0 on every run-7 set). Non-axis encounters carry no `ReferenceReading` (the report reads it only for axis scripts).
  - **C17 (stage-3):** `git status --short` empty (the script is git-ignored); `git diff --stat 170345d -- desktop/src validation/config validation/scripts scripts/build-validation-set.py scripts/run-validation.py` lists `validation.py` only (Tasks 0.2a / 0.2b, recorded above). Nothing under `desktop/src`, `validation/`, `scripts/` changed in this task. ruff and mypy green (no package change). Run by the composer: `.venv/Scripts/python.exe .cursor/loops/run8-predict.py > .cursor/loops/run8-predict-out.txt`.
  - **Run (2026-11-06, composer):** exit 0, stderr empty, 153 lines; script SHA-256 `83a8aa781d55b7ed905603b8cdf356408ce1f47b9f9feeafb4579b288997e777`, output SHA-256 `83df6f5e534458946d2dbac50f4dcd027f008f7409122e9ab3bf2db77c7e4a7d`; harness commit `d15a28f8227f7cb723af7730f979736590c55c0c`. Rules (SHA-256): `rule-v3.json` `b4c280b63e6ea50c84d621ba4e6922a699f1b2f4ba7980c0266afa625f206414`, `rule-v5.json` `0783cd85268a10d978fd6b4a62f114a2b84d060aea5e4648924f7b3d9bc05fd1`. Run 7's reports (SHA-256): `scripts` `1e434678d5771f96c75889f85d0956fb913f2851668272172bfddfa6ea65d477`; `heldout` `2363612309d172f736643f84c7d73a309e183b3c256495c04f43285604ccdf44`; `heldout-2` `bd36a11e8b9bd12f07c4bcd9876a52f2148dc70c467ac33f8f5067556720096d`; `heldout-3` `97bd8db2a47cc8c72982cd07f60c060b0ee86e384b7cacd2b001de13a0ab8af9`; `heldout-4` `d90b06d86889c095fc296dee3174cd20dea7165f6cc0b005a09f8681b2a6ec00`. This first run's output is kept as `.cursor/loops/run8-predict-out.r1.txt`.
    - **Re-run after review round 9 (2026-11-06, composer; peer round 10 PR-LOW-001):** exit 0, stderr empty, 158 lines. Script SHA-256 `1d838bef51194fc97383ec093465c7c10c948262ea450bccb88547df2cb9f95b`, output SHA-256 `41bd1c6591d1f4f020f6dc688cae931214bf700c69e1b95ee5e18ad0d0fdb94a`. `diff` against the first run's output shows five added blank lines only; no prediction changed. The rules', reports' and commit's hashes are unchanged.
    - **Re-run after peer round 10 (2026-11-06T16:47+11:00, composer):** the script changed again (PR-LOW-002: the difference check compares each line under D5's substitutions only). Exit 0, stderr empty, 158 lines; script SHA-256 `a0eca2713a8a509c06f62a5100748aca2f13d45ed58807abbea4ffa5fd37dc88`, output SHA-256 `41bd1c6591d1f4f020f6dc688cae931214bf700c69e1b95ee5e18ad0d0fdb94a`; `cmp` against the round-9 output (kept as `run8-predict-out.r2.txt`): byte-identical, as expected. Only the script's hash differs.
    - **The six R1 members**, asserted by id before anything else and each unambiguous; the kind read by the harness's `residue_r1_silent` / `residue_r1_marked`: `syn-22/f2` silent; `syn-28/f1`, `hld-07/f0`, `h3-03/f0`, `h4-01/f5`, `h4-07/f0` marked. Neither refusal fired.
    - **The reproduction** under rule v3 at HEAD: OK on all five sets. The heading, verdict lines and residue section match byte for byte (line contents; the reports' CRLF terminators split off). The run information, checker warnings, Facts table and encounter rows also match, less WER, the run-1 and 0.3.3 silent columns, Surfaced (acoustic only) and the TOTAL seconds. Every per-fact and per-encounter value the rule-v5 lines below read is in a compared region; the "Silent omissions" column (unmasked) pins every fact's silent flag.
    - **The render difference** (rule v5's against rule v3's, on the same outcomes): 8 lines on every set. They are the heading, verdict lines 1–3 (rule-v5 report lines 3, 4 and 5), the run information, the residue heading, the R1 marked line and the after-classes line. Rule v1's verdict line, the R1 row, the tables, the Facts table, the excused line and every other residue line are equal. Nothing differs outside D5's list.
    - **Corroboration only** (D5: never a source of record), the composer's CRLF-normalised `diff` of each run-7 report against `.cursor/loops/run8-reports/medium/report-<set>.md` (the 2026-11-05 `medium` rule-v4 measurement): on every set exactly 6 lines differ on each side. They are the first `[run ]` line, the run information, the heading, the first two verdict lines (label / gate), the residue heading and the after-classes line. No table, Facts or encounter line differs.
    - **C17 (a)** (composer): `git log 170345d..HEAD` over the C17 paths is empty; nothing uncommitted there.
  - **PREDICTIONS v5 — FROZEN (2026-11-06T16:37+11:00; transcribed from `run8-predict-out.txt`; ids, counts and verdicts only).** Verdicts are in the order rule v5 / rule v5 with marked R1 counted / rule v5 without the R1 exemption / rule v1. "Failing" lists encounters (reasons); "set-level" lists class breaches; set-level errors are 0 on every set. Check 6 is per next-patient axis script, as id: `possible_next_patient` warnings, reference boundary, tail start, R3.
    - **`scripts`** (a gate set; 50 encounters, 50 measured):
      - Verdicts: PASS / PASS / PASS (= rule v2's verdict on this set) / FAIL.
      - Failing under the first three: none; set-level none.
      - Failing under rule v1: syn-22 (silent_omission); syn-28 (material_wrong); syn-35 (uncertainty_not_surfaced); syn-38 (material_wrong); syn-46 (material_wrong).
      - Residue: R1 2 facts, ceiling 2, within — syn-22/f2 (silent), syn-28/f1 (marked); R1 marked wrong (counted under the ceiling) 1 — syn-28/f1. R2 1 fact, ceiling 2, within — syn-35/f2. R3 2 encounters, ceiling 2, within — syn-38, syn-46.
      - After the classes: material wrong 0 (raw 3), silent omissions 0 (raw 1), uncertainty missed 0 (raw 1). Excused lines 0 (raw 0): none.
      - Surfaced / expected 9 / 10 (required). `clinician_line_omitted` total 41, median 1, maximum 3. Credited by the run only: segments 0, facts 0.
      - Check 6: syn-06: 1, 4, 4, no; syn-20: 1, 4, 4, no; syn-21: 1, 4, 4, no; syn-38: 0, none, 4, yes; syn-43: 1, 6, 6, no; syn-46: 0, none, 4, yes. Reference mismatches: none.
    - **`heldout`** (a reported set; 22 encounters, 22 measured):
      - Verdicts: FAIL / FAIL / FAIL (= rule v2's verdict on this set) / FAIL.
      - Failing under the first three: hld-14 (material_wrong); hld-21 (material_wrong); set-level R2 4 over the ceiling of 1.
      - Failing under rule v1: hld-07 (material_wrong); hld-14 (material_wrong); hld-19 (uncertainty_not_surfaced); hld-20 (uncertainty_not_surfaced); hld-21 (material_wrong, uncertainty_not_surfaced).
      - Residue: R1 1 fact, ceiling 1, within — hld-07/f0 (marked); R1 marked wrong (counted under the ceiling) 1 — hld-07/f0. R2 4 facts, ceiling 1, NOT within — hld-19/f2, hld-20/f2, hld-21/f1, hld-21/f2. R3 1 encounter, ceiling 1, within — hld-14.
      - After the classes: material wrong 2 (raw 4), silent omissions 0 (raw 0), uncertainty missed 0 (raw 4). Excused lines 0 (raw 0): none.
      - Surfaced / expected 2 / 6 (required). `clinician_line_omitted` total 9, median 0, maximum 2. Credited by the run only: 0, 0.
      - Check 6: hld-01: 0, none, none, no; hld-02: 0, none, none, no; hld-03: 0, none, none, no; hld-04: 0, none, none, no; hld-05: 0, none, none, no; hld-06: 0, none, none, no; hld-07: 0, none, none, no; hld-08: 0, none, none, no; hld-09: 0, none, 5, no; hld-10: 1, 5, 4, no; hld-11: 1, 4, 4, no; hld-12: 0, none, 5, no; hld-13: 1, 5, 5, no; hld-14: 0, none, 5, yes. Reference mismatches: hld-10.
    - **`heldout-2`** (a reported set; 22 encounters, 22 measured):
      - Verdicts: FAIL / FAIL / FAIL (= rule v2's verdict on this set) / FAIL.
      - Failing under the first three: h2-01 (uncertainty_not_surfaced); h2-03 (silent_omission); h2-04 (silent_omission); h2-07 (silent_omission); h2-08 (silent_omission); h2-09 (silent_omission); h2-11 (silent_omission); h2-13 (silent_omission); h2-14 (silent_omission); h2-17 (silent_omission, uncertainty_not_surfaced); h2-18 (silent_omission, uncertainty_not_surfaced); h2-19 (silent_omission); h2-20 (silent_omission); h2-21 (silent_omission); h2-22 (silent_omission); set-level R2 9 over the ceiling of 1.
      - Failing under rule v1: h2-01 (uncertainty_not_surfaced); h2-03 (silent_omission, uncertainty_not_surfaced); h2-04 (silent_omission); h2-05 (uncertainty_not_surfaced); h2-07 (silent_omission); h2-08 (silent_omission, uncertainty_not_surfaced); h2-09 (silent_omission); h2-10 (uncertainty_not_surfaced); h2-11 (silent_omission); h2-12 (uncertainty_not_surfaced); h2-13 (silent_omission, uncertainty_not_surfaced); h2-14 (silent_omission); h2-15 (uncertainty_not_surfaced); h2-17 (silent_omission, uncertainty_not_surfaced); h2-18 (silent_omission, uncertainty_not_surfaced); h2-19 (silent_omission); h2-20 (silent_omission); h2-21 (silent_omission, uncertainty_not_surfaced); h2-22 (silent_omission).
      - Residue: R1 0 facts, ceiling 1, within — none; R1 marked wrong (counted under the ceiling) 0 — none. R2 9 facts, ceiling 1, NOT within — h2-03/f1, h2-05/f0, h2-08/f7, h2-10/f1, h2-12/f2, h2-13/f2, h2-15/f0, h2-18/f1, h2-21/f4. R3 0 encounters, ceiling 1, within — none.
      - After the classes: material wrong 0 (raw 0), silent omissions 25 (raw 25), uncertainty missed 3 (raw 12). Excused lines 0 (raw 0): none.
      - Surfaced / expected 1 / 13 (required). `clinician_line_omitted` total 23, median 1, maximum 4. Credited by the run only: 0, 0.
      - Check 6: h2-01: 0, none, 13, no; h2-02: 0, none, none, no; h2-04: 0, none, none, no; h2-05: 1, 12, 12, no; h2-06: 0, none, none, no; h2-07: 0, none, 10, no; h2-09: 1, 9, 9, no; h2-10: 0, none, none, no; h2-11: 1, 12, 12, no; h2-13: 0, none, none, no; h2-14: 0, 9, 8, no; h2-16: 0, none, none, no; h2-17: 1, 10, 10, no; h2-21: 0, none, none, no; h2-22: 0, none, 10, no. Reference mismatches: h2-14.
    - **`heldout-3`** (a reported set; 23 encounters, 23 measured):
      - Verdicts: PASS / PASS / FAIL (= rule v2's verdict on this set) / FAIL.
      - Failing under rule v5 and with marked R1 counted: none; set-level none.
      - Failing without the R1 exemption: h3-03 (unsupported_clinical_line); set-level none.
      - Failing under rule v1: h3-03 (unsupported_clinical_line, material_wrong); h3-10 (uncertainty_not_surfaced); h3-12 (uncertainty_not_surfaced); h3-14 (uncertainty_not_surfaced); h3-17 (material_wrong); h3-19 (uncertainty_not_surfaced); h3-20 (uncertainty_not_surfaced); h3-21 (uncertainty_not_surfaced).
      - Residue: R1 1 fact, ceiling 1, within — h3-03/f0 (marked); R1 marked wrong (counted under the ceiling) 1 — h3-03/f0. R2 5 facts, no ceiling (reported), within — h3-10/f2, h3-12/f0, h3-14/f1, h3-20/f0, h3-21/f2. R3 1 encounter, ceiling 1, within — h3-17.
      - After the classes: material wrong 0 (raw 2), silent omissions 0 (raw 0), uncertainty missed 1 (raw 6). Excused lines 1 (raw 1): h3-03/line 1 (segment 3).
      - Surfaced / expected 2 / 8 (reported, not required). `clinician_line_omitted` total 26, median 1, maximum 3. Credited by the run only: 0, 0.
      - Check 6: h3-01: 1, 10, 11, no; h3-02: 1, 9, 10, no; h3-03: 0, none, none, no; h3-04: 0, none, none, no; h3-05: 0, none, none, no; h3-06: 0, none, none, no; h3-07: 0, none, none, no; h3-08: 0, none, none, no; h3-09: 0, none, 6, no; h3-10: 0, none, 13, no; h3-11: 0, none, 11, no; h3-12: 1, 10, 11, no; h3-13: 0, none, 10, no; h3-17: 0, none, 8, yes; h3-18: 0, 8, 9, no; h3-20: 0, none, 8, no; h3-23: 0, none, none, no. Reference mismatches: h3-01, h3-02, h3-12, h3-18.
    - **`heldout-4`** (a reported set under rule v5; 22 encounters, 22 measured):
      - Verdicts: FAIL / FAIL / FAIL (rule v2 has no row for this set) / FAIL.
      - Failing under the first three: none; set-level R1 2 over the ceiling of 1.
      - Failing under rule v1: h4-01 (material_wrong, uncertainty_not_surfaced); h4-04 (uncertainty_not_surfaced); h4-07 (material_wrong); h4-14 (uncertainty_not_surfaced); h4-15 (uncertainty_not_surfaced); h4-22 (uncertainty_not_surfaced).
      - Residue: R1 2 facts, ceiling 1, NOT within — h4-01/f5, h4-07/f0 (both marked); R1 marked wrong (counted under the ceiling) 2 — h4-01/f5, h4-07/f0. R2 4 facts, no ceiling (reported), within — h4-01/f2, h4-04/f0, h4-14/f2, h4-15/f1. R3 0 encounters, ceiling 1, within — none.
      - After the classes: material wrong 0 (raw 2), silent omissions 0 (raw 0), uncertainty missed 1 (raw 5). Excused lines 0 (raw 0): none.
      - Surfaced / expected 2 / 7 (reported, not required). `clinician_line_omitted` total 29, median 1, maximum 3. Credited by the run only: 0, 0.
      - Check 6: h4-01: 0, none, none, no; h4-02: 0, 6, 7, no; h4-04: 0, none, none, no; h4-05: 1, 9, 10, no; h4-06: 0, none, none, no; h4-07: 0, none, 7, no; h4-08: 0, none, none, no; h4-09: 0, none, none, no; h4-10: 0, none, none, no; h4-11: 0, none, 8, no; h4-13: 1, 4, 4, no; h4-16: 0, none, 8, no; h4-20: 0, none, 9, no; h4-21: 0, none, none, no. Reference mismatches: h4-02, h4-05.
    - **Reading (not a prediction):** on every seen set rule v5's verdict equals its verdict with marked R1 counted, as C18 and D1 intend — no seen row reports marked R1. `heldout-4` fails as a reported set under rule v4's row (2 marked R1 over 1), which no gate reads. Rule v5's gate on the seen sets is the 50's PASS. At run 8 each seen set's rule-v5 report must print exactly these lines. Against run 7's report, only D5's listed lines may differ; any other difference is a finding read before anything else (D5).
  - **Review round 9 (2026-11-06T16:37+11:00, leg x2):** two LOWs in the script, both applied — the output's missing blank line before each residue section (LOW-001), and the difference check's categories admitting a changed rule-v1 verdict line or a changed R1 row on a seen set (LOW-002; both now "other", and so exit 6). Neither changes a printed prediction: on this run no rule-v1 line and no R1 row differed (the line numbers above). The composer re-runs the script; the record is re-checked against the new output, which should differ only by those five blank lines and the script's hash.
  - **Closed (2026-11-06T16:50+11:00, composer):** the predictions above are FROZEN as of this commit (C16, D5): the script `.cursor/loops/run8-predict.py` (git-ignored scratch) SHA-256 `a0eca2713a8a509c06f62a5100748aca2f13d45ed58807abbea4ffa5fd37dc88`, its output SHA-256 `41bd1c6591d1f4f020f6dc688cae931214bf700c69e1b95ee5e18ad0d0fdb94a` (158 lines, exit 0), harness `d15a28f`; `/review-loop` round 9 (2 LOW, applied), codex peer round 10 (2 LOW, applied) and round 11 (0 findings) converged; C17 (a) empty since `170345d` and nothing under the C17 paths changed in this task; committed alone (plan only — the script and its output stay in the git-ignored `.cursor/loops/`).
- [x] ✅ **0.4 `heldout-5` pre-registration** (D4, D7) — the falsifiers, the bands (marked R1 0–3 WITH the band rule; the author-overlap band), the qualifiers (patient facts routed by rule; the author model for R3 and R1), committed alone; its hash on this task. Done when: committed before 0.5 starts.
  - `[2026-11-06T16:53:29+11:00, stage-4 executor (leg x1) — THE PRE-REGISTRATION for heldout-5; the set does not exist and is unread, so nothing names an id; built, review and commit owed]` Fixed before any `h5-` script exists (C16), after rule v5 (Task 0.2a, `ba71ff5`; blob `3f3bb7acf6f16074d2e0e37767fa387a7f37c015`) and predictions v5 (Task 0.3, `431a38e`). Every number below is the plan's own: D1's `heldout-5` row (equal to `rule-v5.json`), D4's, D7's, the Goal's, or Task 0.2a's and Task 0.3's records. Nothing was measured for it, and D4, D7 and every rule file are unchanged (C16). The brief, its leak check, the author runner and the tail script are Task 0.5's.
  - **The row it is read against** — `heldout-5` in `validation/rules/rule-v5.json`: `gate true`; `max_r1_facts 1`, counting the SILENT R1 kind only, because `r1_marked_reported true` prints the marked kind beside it with no ceiling; `max_r3_encounters 1`; `require_uncertainty_surfaced false` (uncertainty reported, not gated); no `max_r2_facts` (R2 reported). The rule's top-level fields: `max_material_wrong 0`, `max_silent_omissions 0`, `unsupported_line_r1_exemption true`, `max_word_error_rate null`. The gate for run 8 is a rule-v5 PASS on this row and on the 50's (`scripts`) row (D3); the 50's lines are predictions v5 (Task 0.3).
  - **The seen numbers** beside each line come from Task 0.3's frozen record (run 7's reports re-read under rule v5), always in the order `scripts` / `heldout` / `heldout-2` / `heldout-3` / `heldout-4`.
  - **Gate falsifiers — each one FAILS rule v5 on `heldout-5`** (D4's list, in D4's order; the failure reason is the harness's, in brackets):
    1. **R1 silent > 1 fact** — fails the row's `max_r1_facts 1` (set level: "R1 n over the ceiling of 1"). Expected: D4 states no range, and none is added here. Seen R1 silent: 1 (`syn-22/f2`) / 0 / 0 / 0 / 0.
    2. **A silently omitted material fact after R1** — fails `max_silent_omissions 0` (`silent_omission`). Expected 0 (D4). Seen after the classes: 0 / 0 / 25 / 0 / 0. The Goal's "0 on every blind set so far" does not count `heldout-2`, whose 25 the Goal names separately as "silent facts on unrouted patient lines, outside every plan's scope since 0.3.4". D4's expected 0 is unchanged by it.
    3. **A material fact `wrong` without a review mark** (a confident recogniser error) — fails `max_material_wrong 0` (`material_wrong`). Expected 0–2 (D4). Seen material wrong after the classes: 0 / 2 / 0 / 0 / 0. `heldout`'s two are the confident unmarked errors `hld-14/f1` and `hld-21/f3` (the Goal's table: "`heldout` had 2; the three later sets 0").
    4. **R3 > 1 encounter** — fails the row's `max_r3_encounters 1` (set level: "R3 n over the ceiling of 1"). Expected 0–2 (D4). Seen R3 (run 7's, under the widened lists): 2 / 1 / 0 / 1 / 0 (the 50's ceiling is 2). The Goal, whose `heldout-3` figure is under the old lists: "the author model's phrasing decides; `heldout-3` had 2 of 10 reach a note under the old lists, `heldout-4` 0 of 7 under the widened ones".
    5. **A wrongly present material fact outside R3** — fails `max_material_wrong 0` (`material_wrong`; R3 alone excuses a wrongly present fact). Expected 0 (D4; the Goal: "0 so far"). Seen: no after-class material-wrong fact on the seen sets other than falsifier 3's two.
    6. **An unsupported clinical line not excused** — fails at any count (`unsupported_clinical_line`). `unsupported_line_r1_exemption true` excuses only a flagged word `_excused_by_r1` reads as a material R1 fact's own misrendering, inserted on no optimal alignment and itself under a review mark (validation-run7 D4). D7 names what it does not excuse: "the flagged word itself unmarked, or an inserted word". Expected 0–1 (D4; the Goal). Seen: no `unsupported_clinical_line` failure under rule v5 on any seen set. Lines the exemption excuses: 0 / 0 / 0 / 1 (`h3-03/line 1 (segment 3)`) / 0.
    7. **A checker failure** — fails at any count (`checker_failure`; no rule field). Expected 0 (D4; the Goal: "0 so far"). Seen: no `checker_failure` in any failing list, under any of the four verdicts, on any seen set. D7: "a checker failure a misheard dose or side raises".
    - Falsifiers 6 and 7 are the "two residual paths" by which a marked R1 fact can still fail its encounter (D7). A marked R1 fact cannot fail the R1 CEILING under rule v5 (D7).
  - **Bands — reported, not gating; outside one is a finding, never a rule edit** (D4's list, in D4's order):
    1. **Marked R1: 0–3 facts, with the band rule (D7).** Seen marked R1 (counted under each seen row's ceiling): 1 (`syn-28/f1`) / 1 (`hld-07/f0`) / 0 / 1 (`h3-03/f0`) / 2 (`h4-01/f5`, `h4-07/f0`). **The band rule — the decision-rule reading, fixed in this commit (D7, verbatim):** "a marked-R1 count on `heldout-5` above 3 makes the RECOMMENDED P.5 option "keep shadow on" and triggers the distinct-mark plan (Deferred); 0–3 makes "off" the recommended option. A decision rule for the recommendation, never a gate; the practitioner decides either way." Every marked R1 fact, whatever the count, is a `controlled` register row (D1).
    2. **The `clinician_line_omitted` load per measured encounter: median 0–2, maximum ≤ 5.** Seen median / maximum: 1 / 3; 0 / 2; 1 / 4; 1 / 3; 1 / 3.
    3. **Surfaced doubt 15–40%.** Seen surfaced / expected (fractions as Task 0.3 holds them; no rate is computed here): 9 / 10; 2 / 6; 1 / 13; 2 / 8; 2 / 7. On `heldout-5` it is reported, not required (`require_uncertainty_surfaced false`).
    4. **Reference-boundary mismatches 0–6.** Seen mismatches: none / `hld-10` / `h2-14` / `h3-01`, `h3-02`, `h3-12`, `h3-18` / `h4-02`, `h4-05`.
    5. **Boundaries found of role tails 20–80%** (the band as validation-run7 Task 0.7 defined it). Seen: Task 0.3's Check 6 entries per axis script (reference boundary, tail start). This plan holds no fraction for them, so none is written here.
    6. **False cuts 0–1.** Seen: no next-patient script in Task 0.3's records has a reference boundary set where its tail start is none. A script without the axis is not in those records, so this reading covers the negatives only.
    7. **R2: any count, reported.** Seen R2: 1 / 4 / 9 / 5 / 4.
    8. **Author overlap** — "the count of `h5-` material-fact statements whose canonical token sequence appears in any seen set's facts, any value reported; COMPUTED AT P.3, not before" (D4, peer round 1 PR-MED-004), by a count-only script whose output is one integer. The computation reads the statements' tokens, so it waits for the end of the blind rule (C12). **P.1 records this band "pending P.3".** There is no seen number.
  - **The qualifiers** (in the plan's own words):
    - D3: "A `heldout-5` pass is reported with its qualifiers — patient facts routed by rule; the author model, for R3 AND R1 — and with the marked-R1 count and the band rule's reading beside it."
    - The Goal: "Author-model independence is weaker than "fresh blind set" sounds: the same author, the same brief with four lines changed. The author decides how many spoken-letter abbreviations and dose lines exist — the class under test — so the author-model qualifier covers R1 as well as R3 (D4)."
    - The Goal: "A rule-v5 pass is evidence about the gated sets only."
    - What a rule-v5 PASS means and does not mean is the Goal's paragraph (peer round 1 PR-MED-003). Its allowances are part of the acceptance (D7): up to one silent R1 fact and one R3 encounter on the blind set; uncertainty reported, not gated, there; R2 at any count.
  - **The prediction for `heldout-5`, stated in advance** (the Goal's Honest forecast and D7; no number beyond theirs):
    - **Rule v5:** a PASS is "likelier than not and is an outcome to report, never a target" (the Goal). Of the measured outcomes, only a falsifier above fails it. An encounter the harness could not measure (`harness_error`, `role_unresolved`) also fails any row — a run failure, not a D4 falsifier. `prose_unavailable` needs `--prose`, which P.1's command does not pass. Marked R1 is "expected at 0–3 facts and is reported whatever it is" (the Goal).
    - **Rule v5 with marked R1 counted:** the same outcomes with every marked R1 fact counted under the R1 ceiling of 1. It FAILs whenever the silent and marked R1 facts together exceed 1, or a falsifier fires. With marked R1 expected at 0–3, the plan forecasts it neither way. For `rule-v5.json` it is rule v4's verdict (C18; D1: pinned in the suite and to be STATED in the harness document's Rule v5 section at Task 1.2, never printed). It is reported, never the gate.
    - **Rule v5 without the R1 exemption:** rule v5's failures plus every unsupported clinical line the exemption excuses. Marked R1 is still reported (D1), and the line reads "rule v2 has no row for this set" (D1: `no_row`). It FAILs wherever rule v5 fails, and also on any excused line (seen: one in five sets, `h3-03`).
    - **Rule v1:** the plan forecasts no rule-v1 verdict, and none is added here. Rule v1 reads the raw counts with the rule's top-level fields, so it FAILs on any R1 fact of either kind, any R2 fact (uncertainty is required at the top level), any R3 encounter or any excused line; a PASS needs none of them at all. Seen: FAIL on all five sets (Task 0.3).
    - **Fixed in advance (D7, Follow-Up Continuation Notes):**
      - A FAIL is a recorded finding: P.5 stays (a), the register rows keep their shadow control, and no rule is edited.
      - A FAIL on R1 silent or on a confident error without a mark is "the recogniser WITHOUT a mark — the low-confidence threshold's territory, a new dated decision with the measurement repeated, not this plan".
      - A FAIL on R3 leads to the practitioner's own phrases and a further widening, as its own dated decision with another blind set (`heldout-6`, pre-registered first).
      - Marked R1 above 3 fires the band rule and the distinct-mark plan (Deferred).
      - P.3 classes every failure and every marked R1 fact by its own words.
    - **The seen sets** are expected to equal predictions v5 exactly. A difference is a finding read before anything else (the Goal's "Nondeterminism"; D5).
  - **Commit:** this record and the plan's bookkeeping, committed ALONE by the composer. The composer records the commit's hash on Task 0.5 before the author runs (Task 0.5 commits "with the pre-registration hash"). A commit cannot carry its own hash, so Task 0.4's "its hash on this task" is met there, as run 7's Task 0.7 hash was recorded on its 0.8. The harness document's Rule v5 section repeats the band rule and this pre-registration at Task 1.2 (D7, D8).
  - **C12 / C17 (this leg):** `git status --short` shows only this plan. Nothing under `validation/`, `desktop/` or `scripts/` was touched, and `validation/heldout-5` and `.cursor/loops/held-out-lint/` were not opened. The only scratch read was `.cursor/loops/run8-predict-out.txt`: every seen number above equals it and Task 0.3's record.
  - **Closed (2026-11-06T17:01+11:00, composer):** `/review-loop` round 12 (6 LOW, wording, applied) and codex peer round 13 (0 findings, 13 claims checked) converged; plan text only, no suite; nothing under `validation/`, `desktop/` or `scripts/` changed, `validation/heldout-5` absent; C17 (a) empty since `170345d`. THE pre-registration commit is this one, committed ALONE; its hash is recorded on Task 0.5 before the author runs (a commit cannot name itself).
- [x] ✅ **0.5 Blind authoring of `heldout-5`** (D4; C12) — `run8-brief-leak.py` (the copy with D4's edits and the primer in `LISTS`; the brief's hash recorded), `validation-run8-heldout5-author-run.sh` and `...-author-prompt.txt` (the copies with D4's edits; the CLI preflighted), the practitioner launches the author in a NEW empty folder outside the repository; the scripts copied in unread with `SPEC.md`, `AUTHOR-NOTES.md`, `author-prompt.txt`, the redacted log; `validation-run8-heldout5-tails.py` writes the `h5-` tail rows; the file-name-only presence pin (`held_out_set("heldout-5").script_paths()` non-empty); lints ONLY through `scripts\lint-held-out-set.py validation\heldout-5` (a lint failure goes back to the author as its code, never a script edit); `validation/README.md`'s entry to the authored state (`heldout-4`'s shape). Done when: the runner is green; committed with the pre-registration hash. From here every suite run goes through the runner.
  - **The pre-registration commit (2026-11-06T17:00+11:00, composer):** Task 0.4 is `edd1a7d6eecd01d7839569e3615e7125b6f1298e` (`edd1a7d`), committed alone before any `h5-` script exists; `validation/heldout-5` absent at that commit. Task 0.5's commit carries this hash.
  - **Prep built, leak run owed (2026-11-06T17:04:06+11:00, stage-5 executor leg x1).** Four NEW files in the git-ignored `.cursor/loops/`, none run by the executor. Each was checked against its run-7 original with `git diff --no-index`.
    - `run8-brief-leak.py` (from `run7-brief-leak.py`). D4's edits:
      - `SOURCE` is `validation/heldout-4` and `OUT` is `.cursor/loops/heldout-5-brief`.
      - `EDITS` change brief lines 1, 5, 56 and 65 only. Line 1 becomes `# Held-out set 5 — the author's brief (validation-run8 plan, Task 0.5, 2026-11-06)`. Lines 5, 56 and 65 change `h4` to `h5`. Each old string is asserted to occur exactly once on its line. In `author-prompt.txt`, `h4-01.json` becomes `h5-01.json`.
      - `LISTS` gain `"primer term"`: `CLINICAL_INITIAL_PROMPT` split on `.` and `,`, stripped, with empty parts dropped. That gives 33 terms, used as vocabulary only, and 0 hits are expected. The five run-7 lists are unchanged.
      - The refusal is `validation/heldout-5` exists → exit 2.
    - The leak script's asserts:
      - no bare `\r` in the source brief;
      - no `h4` and no `set 4` left in the brief, and exactly 6 `h5` and 1 `set 5` (lines 1, 5, 56 and 65; the source has exactly 6 `h4` and 1 `set 4`, all on those lines);
      - the source prompt holds exactly one `h4` (its `h4-01.json`), and the result holds exactly one `h5-01.json` and no `h4`.
    - What it prints, all inherited from run 7 except the last two items:
      - `[brief] lines N, changed 4`;
      - `[lists]` counts per list;
      - `[hit] <file>:<line> <list>: '<LISTED phrase>'` (line numbers and listed phrases only);
      - `[leak] hits N` (run 7's brief had 10, from the frozen lists);
      - the two outputs' SHA-256 (`[sha256] SPEC.md …` and `[sha256] author-prompt.txt …`), as the spawn asks;
      - `[prompt] equals validation-run8-heldout5-author-prompt.txt: yes|no`, with exit 3 on `no`.
    - `validation-run8-heldout5-author-prompt.txt` (from `validation-run7-heldout4-author-prompt.txt`): `h4-01.json` → `h5-01.json`, the only change. LF, one trailing newline. Run 7's prompt and `validation/heldout-4/author-prompt.txt` have the same blob (`0d76591`), so this file should equal the leak script's generated `author-prompt.txt` byte for byte. The script's `[prompt]` line checks that.
    - `validation-run8-heldout5-author-run.sh` (from `validation-run7-heldout4-author-run.sh`):
      - the folder is `cd /c/heldout5-author || exit 9`, never `/c/heldout4-author`;
      - the log, prompt and done paths are `validation-run8-heldout5-author{.log,-prompt.txt,.done}`;
      - the flags are D4's exactly (`--restricted --safe-mode --strict-mcp-config --disallowedTools WebSearch Agent --permission-mode acceptEdits --model claude-opus-5-5`) plus run 7's `--output-format stream-json --verbose`, stdin closed;
      - LF (the `*.sh` attribute).
      - As in run 7, the folder is created EMPTY by the composer or practitioner and given the regenerated `SPEC.md` alone before the launch. The runner does not create it.
    - `validation-run8-heldout5-tails.py` (from `validation-run7-heldout4-tails.py`): `SET` is `heldout-5`, the glob `h5-*.json`, the guard `assert '"h5-' not in text`, and the anchor `'    "h4-21": None,\n}\n'`. That anchor is checked as the CURRENT last row of `REFERENCE_TAIL_STARTS` at `edd1a7d` (`validation.py:678-679`, one occurrence, no `"h5-` in the file). It is NOT run before the set exists.
    - **Differences beyond D4's named edits (justified here; none changes what the author sees):**
      - (a) Both docstrings are re-pointed to this plan and task.
      - (b) The refusal message reads "absent until Task 0.5's copy-in".
      - (c) There are positive set-5 count asserts beside run 7's re-pointed negative ones. This is the reading taken of "the asserts read `"h5"` / `"set 5"` / `h5-01.json`". A brief with a stray or missing `h5` then fails before it is written.
      - (d) The two SHA-256 lines, as the spawn names.
      - (e) The `[prompt]` equality line with exit 3. It reads only the runner's own prompt file and guards deliverable 2's byte-equality, so a mismatch stops before the author runs (run 7's tool had no such check).
      - No MUST-PAUSE: nothing D4 does not cover changes the brief, the prompt or the invocation.
    - **C12 / C1 / C2 / C17 (this leg):** `validation/heldout-5` was not created and `.cursor/loops/held-out-lint/` was not opened. No `h4-*.json`, `AUTHOR-NOTES.md`, `author-session.jsonl` or set script was opened; only `validation/heldout-4/SPEC.md` and `author-prompt.txt` were read. Nothing under `desktop/`, `scripts/`, `validation/` or the rules changed. `git status --short` shows only this plan (the `.cursor/loops/` files are git-ignored).
    - **Owed (composer):**
      1. Run `.venv/Scripts/python.exe .cursor/loops/run8-brief-leak.py`. Expected: exit 0, `changed 4`, `primer term: 33`, 0 primer hits, `[prompt] … yes`. Record both SHA-256 values here.
      2. Run the CLI preflight (a throwaway `claude -p` with D4's flags).
      3. Run `/review-loop` (this executor, resumed).
      4. Then create `C:\heldout5-author` empty, holding `SPEC.md` alone. The PRACTITIONER launches `bash .cursor/loops/validation-run8-heldout5-author-run.sh`.
  - **The leak run and the preflight (recorded 2026-11-06T17:06:32+11:00, stage-5 executor leg x2, from the composer's results).**
    - **The leak run (composer, 2026-11-06T17:05+11:00).** Command: `.venv/Scripts/python.exe .cursor/loops/run8-brief-leak.py > .cursor/loops/run8-brief-leak-out.txt`. It exited 0 with `validation/heldout-5` absent.
      - It printed `[brief] lines 112, changed 4 (1, 5, 56, 65)`.
      - The lists: closings 30, greetings 26, correction markers 4, `HEDGE_PHRASES` 33, `REFERENCE_HEDGES` 52, primer terms 33.
    - **The hits: `[leak] hits 10`, the same 10 on the same lines as run 7's Task 0.7 record** (`plan-validation-run7.md`, the leak-check line under Task 0.7):
      - `i think` ×2 (SPEC.md:40, the diagnosis cue row);
      - `see you next week` and `see you` (SPEC.md:48, the follow-up cue row);
      - `uncertain` ×4 (SPEC.md:67 and :87, the axis tag and the format example);
      - `doubtful` ×2 (author-prompt.txt:1).
      - The `lines 112` count is `split("\n")` over 111 newline-ended lines, so it includes the empty piece after the final newline. Run 7's record counted the same file shape as 111 lines. heldout-4's SPEC is heldout-3's with lines 1, 5, 56 and 65 changed, so every hit line number matches run 7's.
      - **No hit is new.** No greeting and no correction marker occurs. **The primer terms: 0 hits.**
      - Run 7's disposition carries over unchanged: kept unreworded.
        - The cue table must repeat `validation/config/section_cues.json` exactly (C2).
        - The hedge hits (`i think`, `uncertain`, `doubtful`) were accepted when heldout-3 was authored.
        - The two closing hits on SPEC.md:48 (the follow-up cue row, which repeats the cue file under C2):
          - `see you next week` has been listed since 2026-09-28 (`consultation_phrases.py:90`, the first closing). It is the cue row's own phrase, so it was already a hit when heldout-3 and heldout-4 were authored.
          - `see you` is the phrase added by `de8f5da` (2026-10-26, validation-run7 Task 0.4 (c); `consultation_phrases.py:111`). Its one match on that line lies inside that same, already-listed `see you next week`. It adds no word to the brief and no hit on any other line.
          - So the line steers the author to nothing the heldout-3 and heldout-4 authors were not shown, and the disposition (kept unreworded) stands.
          - Correction (2026-11-06T17:12:09+11:00, codex peer round 15 PR-LOW-001): run 7's Task 0.7 record reverses which phrase was new. It calls `see you` closing 0 and listed since 2026-09-28, and `see you next week` closing 20 and new in `de8f5da`. This record had carried that over. Run 7's plan is closed history and is not edited.
        - Nothing an author reads holds a frozen-list phrase that run 7 had not already accepted.
    - **The hashes.** `SPEC.md` `819be45027db4e9dfa2f5dd5e74e0b7a8447effae22c173ff2e1c525da994f54`; `author-prompt.txt` `7758413210fbd24ee05e57b46f02120dc8e478e915935078767e4154908103d5`.
    - `[prompt] equals validation-run8-heldout5-author-prompt.txt: yes`. The runner's prompt equals the generated prompt byte for byte.
    - **The CLI preflight (composer, 2026-11-06).** The CLI is Claude Code 2.1.282. A throwaway `claude -p` used D4's flags exactly (`--restricted --safe-mode --strict-mcp-config --disallowedTools WebSearch Agent --permission-mode acceptEdits --model claude-opus-5-5`) and ran from a new empty scratch folder outside the repository. It replied `PREFLIGHT_OK`, exited 0 and left the folder empty. The Accepted Assumption on the flags holds.
    - **The runner.** The composer's `diff` shows `validation-run8-heldout5-author-run.sh` differing from run 7's only in the folder (`/c/heldout5-author`) and the three run8/heldout5 file names.
    - **Before the author runs:** the brief is regenerated by `run8-brief-leak.py` with `validation/heldout-5` absent. Both SHA-256 values must equal the two above, and a mismatch stops Task 0.5 before the launch (run 7's Task 0.8 shape). `C:\heldout5-author` is created empty and given the regenerated `SPEC.md` alone, its hash equal to `819be450…994f54`.
  - **The author session and the repository edits (recorded 2026-11-06T20:13:00+11:00, stage-5 executor leg x4; written while `validation/heldout-5` is absent — the author folder and the set were neither listed nor read).**
    - **The launch (practitioner, 2026-11-06; MUST-PAUSE `heldout5-author-launch` answered).** From a normal terminal they confirmed `C:\heldout5-author` held `SPEC.md` ALONE, with SHA-256 `819be45027db4e9dfa2f5dd5e74e0b7a8447effae22c173ff2e1c525da994f54` (equal to the brief's). They ran `.cursor/loops/validation-run8-heldout5-author-run.sh` through Git Bash's `bash.exe`. `.cursor/loops/validation-run8-heldout5-author.done` holds `EXIT:0`.
    - **The composer's check** used FILE NAMES, HASHES and the shape of the result line only. No script, `AUTHOR-NOTES.md` or log text was read.
      - The author folder holds 22 scripts, `h5-01.json` … `h5-22.json` with no gap, plus `AUTHOR-NOTES.md` and `SPEC.md`. That is within D4's 20–25.
      - `SPEC.md`'s SHA-256 is unchanged.
      - The session's result line is `success` after 25 turns, and its last line is `DONE 22`.
      - No lint has run yet, so nothing has gone back to the author.
    - **This leg wrote:**
      - (1) `validation/README.md`, its `heldout-5/` bullet only. The file is CRLF in the working tree, and the one-line edit keeps CRLF: `git diff --stat` shows 1 insertion and 1 deletion. The bullet moves from the larger-model plan's "not yet written" wording to the authored state, in `heldout-4`'s shape from its authoring (`8d0caf7`):
        - this plan, Task 0.5 and D4;
        - 22 scripts `h5-01` to `h5-22` (the range form `heldout-4`'s bullet used, with no other id);
        - the brief as `heldout-4`'s with four lines changed, and its full SHA-256;
        - the leak check in Task 0.5 against every frozen list and the primer's terms;
        - the pre-registration, Task 0.4 commit `edd1a7d`;
        - `author-prompt.txt`'s full SHA-256 and the redacted `author-session.jsonl` as the isolation record;
        - `AUTHOR-NOTES.md` read only from Task P.3;
        - the fixtures since larger-model Task 0.1 (d);
        - the temporary presence test from Task 0.5 to Task P.3;
        - "nobody examines its content before Task P.3", followed by C12's machine readers (the lints, the tails script, the presence test, run 8's builder and harness);
        - the suite only through the runner;
        - expected outcomes after run 8 (Task P.3);
        - the voices and builder.
        - It describes no script's content. Run 7's P.4 maps to this plan's P.3, which is the task that examines the content and ends the blind rule. Nothing else in the README changed; the `rules/` bullet is untouched.
      - (2) The presence pin `TestHeldOutScripts::test_the_blind_held_out_set_is_present` in `desktop/tests/test_validation_scripts.py`. It sits right after `test_the_first_held_out_set_is_present`, where `8d0caf7` placed `heldout-4`'s (`4746127` removed that one).
        - It asserts `held_out_set("heldout-5").script_paths()` is non-empty. `script_paths()` is `sorted(self.folder.glob("*.json"))`, so it reads file names only.
        - Its docstring is re-pointed: "TEMPORARY — added at validation-run8 Task 0.5 (D4), removed at Task P.3, which ends the blind rule".
        - The CI clause matches what the step does now: `ci.yml:77-78` falls back to `validation/heldout-4` while `heldout-5` is absent, so it names "`heldout-4`'s log". Run 7's docstring said `heldout-3`'s.
        - 9 insertions, no other line changed.
      - ruff: All checks passed. mypy: Success, no issues in 66 source files. pytest was NOT run. The pin fails until the composer copies the set in, which is by design.
    - **Not touched:** `REFERENCE_TAIL_STARTS` (the composer's tails script writes the `h5-` rows), the fixtures, `test_lint_held_out_set.py`'s blind pin (`["heldout-5"]` until P.3), `ci.yml`, every rule file and `validation/config`. C17 is unchanged: no `desktop/src` file was touched.
    - **Owed (composer), in order:**
      1. Copy the set into `validation/heldout-5/` UNREAD: the 22 scripts and `AUTHOR-NOTES.md` from the author folder; `SPEC.md` and `author-prompt.txt` from `.cursor/loops/heldout-5-brief/`; the session log as `author-session.jsonl` with the user name redacted. Byte-check each copy against its source.
      2. Run `.venv/Scripts/python.exe .cursor/loops/validation-run8-heldout5-tails.py` (ids and integers only).
      3. Run the suite ONLY through `scripts\lint-held-out-set.py validation\heldout-5`. A lint failure goes back to the author as its code, never as a script edit.
      4. Make the Task 0.5 commit with the pre-registration hash `edd1a7d`.
  - **Closed (2026-11-06T20:20+11:00, composer):** the owed steps, in order.
    1. Copied in UNREAD, each copy byte-checked with `cmp` against its source (0 mismatches): the 22 scripts and `AUTHOR-NOTES.md` from `C:\heldout5-author`; `SPEC.md` and `author-prompt.txt` from `.cursor/loops/heldout-5-brief/` (SHA-256 `819be450…994f54` and `77584132…8103d5`, re-checked in the set folder; the author folder's `SPEC.md` is byte-equal too); the stream-json session log `.cursor/loops/validation-run8-heldout5-author.log` as `author-session.jsonl`, as run 7's was. Redaction: counts only, over the Windows user name, the account name, the e-mail domain and the user-profile path forms — 0 occurrences, so the log is copied unchanged (run 7's held one). 26 files, LF, none with a carriage return.
    2. `.venv/Scripts/python.exe .cursor/loops/validation-run8-heldout5-tails.py` (SHA-256 `c52fd07d…f97b70`, unchanged) exited 0 and printed ids and integers only: 7 rows, every one with a `next_patient` tail (no None row). `REFERENCE_TAIL_STARTS` gains those 7 rows (7 insertions in `validation.py`; the state table's "+ the `h5-` axis rows").
    3. The suite ONLY through `scripts\lint-held-out-set.py validation\heldout-5`: collected 9668, passed 9659, failed 0, errored 0, skipped 9, exit 0. No lint failed, so nothing went back to the author. ruff: All checks passed; mypy: no issues in 66 source files. C17 (a) is empty since `170345d`.
    4. Committed with the pre-registration hash `edd1a7d` (Task 0.4). Nobody read a script, `AUTHOR-NOTES.md` or the author's log text; `heldout-5` stays blind until P.3 (C12). From here every suite run goes through the runner.

### Phase 1 — Documents (D2, D8)
- [x] 🟩 **1.1 The review guide and the practice README** (D2) — the dated clauses and lines, marked "awaiting the practitioner's approval"; the counts re-read from run 7's reports (ids never in the guide); CRLF kept. Done when: in, byte-checked for CRLF and no bare `\r`.
  - **Built and reviewed (2026-11-06, stage-6 executor leg x1).** `docs/practice/clinician-review-guide.md`: the header clause ("the misheard number, unit and abbreviation lines and the shadow-mode-off line added after validation run 7 and the larger-model measurement, 2026-11, with no new version, awaiting the practitioner's approval"); a new "Reading the transcript" bullet (D2's paragraph); step 4's sentence; the "A shadow recording" lines. `docs/practice/README.md`: the header clause, and a second bullet in "What the drafts rely on", "The program's own testing (2026-11; not external research)", in the 2026-10 finding's shape; its lead-in now names both. The counts were re-read from run 7's Facts tables: 139 encounters; 7 `wrong` material facts, 5 class R1 and 2 with no class. No id is in either file.
  - **Deviation from D2's draft, by the code (review round 17):** "read aloud by computer voices in a quiet room" became "a few with a steady hiss mixed in", because 8 of the 50 scripts mix Gaussian noise in (`snr_db`, `validation_set.add_noise`). "Real speech, accents and background noise were not measured" became "Real voices and accents and everyday background sound were not measured". The other D2 claims are as drafted. The lines stay "awaiting the practitioner's approval"; their counts are refreshed with run 8's at P.2.
  - CRLF: 0 LF-only lines and 0 bare `\r` in both files (multiline Grep).
- [x] ✅ **1.2 The harness, pilot and security documents, the scripts' docstrings, the stale cites, the four override lines, the plans, `AGENTS.md`, `CHANGELOG.md`** (D1's override lines in the practitioner's words; D8's list). Done when: `test_pilot_docs.py` green; every claim checked against the code; C17 (c) holds.
  - **Built and reviewed, suite owed (2026-11-06, stage-6 executor leg x1; ruff and mypy green, pytest composer-run through the `heldout-5` runner).**
    - `docs/testing/validation-harness.md`:
      - the policy lines: run 8's six `--set` runs, `--model`, the schema-4 exit status, "schema-2 or later" in the refusals, the Model policy, the Residue class column, schema 4 in the rule-file paragraph ("this harness refuses schema 5"), and the residue classes' schema-4 reader;
      - a NEW `## Rule v5` between `## Rule v3` and `## Runs of record`: the file and rule v4 named; the six-row ceiling table with a Marked R1 column; the split; the gate for run 8; the override; loosening (6) with the three-cycle sentence; what a pass means; the register rows; the band rule; the pre-registration; predictions v5 with D5's lines that may differ; the report under rule v5; the pins;
      - `:183`'s sentence extended to point at D5's list;
      - the dated override line under run 7's "never to a rule or predicate change";
      - a dated line superseding `:247`'s "no run 8" (left as written);
      - run 8's placeholder under "Runs of record";
      - review round 17: `heldout-4` dated SEEN, and "The fifth held-out set" paragraph.
    - The new pin `TestHarnessDocument.test_the_rule_v5_ceiling_table_is_the_files`.
    - `validation/README.md`'s rules bullet: rule v4 "planned as the rule of run 8", and rule v5 added.
    - `docs/pilot/`:
      - README: the rule-v5 paragraph replaces the rule-v4 one.
      - findings register: the `h5-NN` line; and in Severity, rule v5 from run 8 and the marked-R1 row rule (D1).
      - exit gate: the dated rule-v5 proposal, for approval at P.2.
    - `docs/security/`: the threat model (schema 4, four verdicts, the marked-R1 line and the named residue) and the data-flow map (`--set` under schema 4; the fourth verdict and the marked facts by id and index only).
    - `scripts/README.md` (rule v5; `heldout-5`'s authorship; the bare-run sentence).
    - The docstrings: `scripts/run-validation.py` (docstring only, C17 (c)) and `scripts/lint-held-out-set.py`.
    - Stale cites re-cited to Tasks 0.5 / P.3, comments only:
      - `heldout_transcripts.py` (the module docstring, `HELDOUT_5_CASES`, the `heldout-5` row);
      - `test_lint_held_out_set.py`;
      - `test_validation_scripts.py` ×3;
      - `test_consultation_boundary.py`, `test_note_check.py` and `test_note.py`;
      - `ci.yml`'s comment (the step unchanged).
    - The four override lines in the practitioner's words: `plan-pilot.md` Constraint 12 and the stop rule; `validation-harness.md`; `plan-larger-model.md`. Also: `plan-pilot.md`'s run-8 line under P.3 and P.5's dated line; `plan-larger-model.md`'s "taken over" line.
    - `AGENTS.md`:
      - step 12 ("the rule in force for that run");
      - the harness pointer (rule v5);
      - Current Status: a dated line superseding "no run 8", the validation-run8 paragraph, NEXT;
      - Last Session, and Documentation Status.
    - `CHANGELOG.md`: one Unreleased entry.
    - No change to `docs/release/pilot-builds.md` (no build).
  - **Two trivial deviations, noted.**
    - `docs/security/threat-model.md` and `docs/security/data-flow-map.md` are CRLF too (outside the state table's list). Both were kept CRLF, as were the CRLF test files, `ci.yml` and `lint-held-out-set.py`.
    - The findings register's Severity paragraph gained the marked-R1 sentence. D8 names only `:37-38`, but D1 fixes the row rule, and run 7's precedent put the exemption's row rule in the same paragraph.
  - **C17 (stage-6):**
    - (a) `git diff --stat 170345d -- desktop/src validation/config validation/scripts scripts/build-validation-set.py ':(exclude)desktop/src/scribe_desktop/validation.py'` (working tree) is empty.
    - (b) nothing under `desktop/src` changed in this task.
    - (c) `git diff -- scripts/run-validation.py` is docstring-only.
  - **C12:** nothing under `validation/heldout-5/` or `.cursor/loops/held-out-lint/` was opened, listed or searched.
  - **Owed (composer):** the suite ONLY through `scripts\lint-held-out-set.py validation\heldout-5`. It pins `test_pilot_docs.py` and the new rule-v5 table pin.
  - **Closed (2026-11-06T21:05+11:00, composer):** the suite ONLY through `scripts\lint-held-out-set.py validation\heldout-5`: ran 9669, passed 9660, failed 0, errored 0, skipped 9, exit 0 (`test_pilot_docs.py` and `test_the_rule_v5_ceiling_table_is_the_files` among them). Line endings checked by `git ls-files --eol` on every changed file: none mixed, the CRLF files still CRLF. No `h5-NN` id in the diff. C17 (a) empty since `170345d`. Codex peer round 18 (pass stage-6.p1) converged with 0 findings over all 25 files, one evidence line per document. Committed by the composer; Phase 1 closed. Next: stage-7 = H1–H4.

### Hardening stage
- [x] ✅ **H1** `/review-loop` to convergence · [x] ✅ **H2** `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan` · [x] ✅ **H3** `/security-review` — same routing · [x] ✅ **H4** final cross-family `/peer-review` re-check (documents as their own slice, one evidence line per document). No H5: nothing to build.
  - **H1–H3 done (2026-11-06T21:10+11:00, stage-7 executor leg x1)** over the whole run, `git diff 9884f04 HEAD -- . ':(exclude)validation/heldout-5'`: H1 `/review-loop` round 19 converged on its first round (2 LOW, both applied — the harness document's "The gate for run 8" sentence now names `heldout-4` among the sets predictions v5 have failing; the owed post-P.1 docstring commit recorded under Deferred); H2 `/simplify` round 20, 0 findings (five candidates consciously left alone, each plan-chosen or C17-barred); H3 `/security-review` round 21, 0 findings (portable checklist). Only a document and this plan changed; no code or test. ruff and mypy green. C12: nothing under `validation/heldout-5/` or `.cursor/loops/held-out-lint/` opened, listed or searched. C16: no fixed record touched. C17 (a) empty since `170345d`; (b) no `validation.py` change in this stage; (c) unchanged.

### Phase P — Practitioner (normal terminal, developer build, installed app closed; C1, C8, C10)
- [x] 🟩 **P.1 Run 8, the run of record** — from a clean committed checkout at the H4 commit (`git status --short` empty); the voice baseline printed and checked; six sets built into empty folders outside the repository (synthetic only); each `.venv\Scripts\python.exe scripts\run-validation.py <set> --config validation\config --rule validation\rules\rule-v5.json --set <name>`, exit codes PRINTED (15–55 min a set as measured 2026-11-05, lid OPEN — a closed lid slows it several-fold; roughly 1.5–5.5 h plus the builds); the reports copied byte for byte to `.cursor/loops/run8-of-record/` (NOT `run8-reports/`, the measurement's folder); read against predictions v5 (every printed line but D5's listed ones) and the pre-registration; recorded in `validation-harness.md` "Runs of record", `plan-pilot.md` P.3 and `CHANGELOG.md` (commit, manifest hash, voices, rule blob, the four verdict lines per set with the gate sets named, the residue counts by class with R1's split, the excused lines, surfaced / expected, the load, each falsifier's and band's outcome (the author-overlap band "pending P.3"), the band rule's reading, the validated-commit sentence); the set folders deleted except `heldout-5`'s (kept until P.3 is committed), with `C:\run7-sets\`, `C:\heldout4-author\` and — confirmed from the practitioner's terminal — `C:\scribe-run7\`, `C:\run7-p4\`; `%TEMP%` checked for `scribe-speaker-eval-*` from the practitioner's own terminal. Done when: recorded and committed on the practitioner's word.
  - `[2026-11-07T08:20:57+11:00, stage-7 executor (leg px1) — AS BUILT: run 8 RECORDED; the gate is NOT met; the record commit and the cleanup are owed]`
    - **The run (practitioner, 2026-11-06 → 2026-11-07, as reported to the composer):**
      - a clean checkout at the H4 commit `72256f4` (not pushed), with `Get-Process scribe-app` empty;
      - the voices printed as the baseline;
      - rule v5 blob `3f3bb7ac…`, rule v1 `ec6c38d4…`, cue file `c7f7b53d…`; manifest `10a83493…` (run 7's);
      - six sets built into `C:\run8\set-<name>`, every build exit 0;
      - exit codes printed: the 50 0, `heldout` 1, `heldout-2` 1, `heldout-3` 0, `heldout-4` 1, `heldout-5` 1;
      - the six reports copied byte for byte to `.cursor/loops/run8-of-record/` (UTF-16 LE with a BOM; their SHA-256s are in the harness document's entry), with UTF-8 reading copies in its `utf8/`.
    - **Read against predictions v5 (Task 0.3):** every seen set matches on every printed line. Against run 7's reports, only D5's listed lines differ. The encounter tables, Facts tables and checker warnings are identical, so the validated-commit sentence (Accepted Assumptions) holds and is recorded.
    - **Read against the pre-registration (Task 0.4):**
      - **Gate:** NOT met. The 50 pass. `heldout-5` fails all three rule-v5 verdicts on one encounter, `h5-17` (material_wrong).
      - **Falsifiers:** ONE FIRED — falsifier 3, a material fact `wrong` without a review mark: 1 (`h5-17/f0`; expected 0–2, and it fails at any count). The other six did not fire: R1 silent 0; silent after R1 0; R3 1 (`h5-10`, at the ceiling); wrongly present outside R3 0; unexcused lines 0; checker failures 0.
      - **Bands:** marked R1 1 (`h5-01/f4`), inside. Load maximum 6 (`h5-12`), OUTSIDE; median 1, inside. Surfaced 1 / 11, OUTSIDE. Mismatches 2 (`h5-01`, `-17`), inside. Boundaries found 3 of 7, inside. False cuts 0, inside. R2 7, reported. The author overlap is pending P.3.
      - **The band rule's reading:** marked R1 is inside 0–3, so on its own the rule would recommend "off". The gate failed, so D7's FAIL branch governs and P.5 stays (a).
      - **Also reported:** `h5-17/f0` is also one of the 3 uncertainty-missed facts outside every class, reported and not gated (the others are `h5-10/f1` and `h5-14/f2`).
    - **Recorded in:** `docs/testing/validation-harness.md` "Runs of record" (CRLF kept), `plan-pilot.md` P.3 (a RUN line) and `CHANGELOG.md` Unreleased (CRLF kept). ids and counts only. No rule, code or test changed (C16, C17), and nothing under `validation/heldout-5/` was opened (C12).
    - **The record commit is the composer's, made on the practitioner's word.**
    - **Owed by the practitioner, NOT done:**
      - delete `C:\run8\set-scripts`, `-heldout`, `-heldout-2`, `-heldout-3` and `-heldout-4`, keeping `C:\run8\set-heldout-5` until P.3 is committed;
      - delete `C:\run7-sets\` and `C:\heldout4-author\`, and from their own terminal confirm and delete `C:\scribe-run7\` and `C:\run7-p4\`;
      - check `%TEMP%` for `scribe-speaker-eval-*` from their own terminal.
  - `[2026-11-07, leg px2]` The record is committed: `5edcefa` (the composer, on the practitioner's word). The cleanup above is still owed; since P.3 the custody line on the px2 handoff bullet lists what may go after P.3's commit.
- [x] 🟩 **P.2 The register, the P.5 decision, the approvals, the shadow-off register commit** `[decision]` — Chosen: keep shadow on (2026-11-07). Options: shadow off / keep shadow on. Decide after: P.1, with the band rule's reading first. Blocks: P.4′. The P.5 question as a dated decision on `plan-pilot.md` with D7's acceptance per class; rows from run 8 by class (`h5-` after P.3; every marked R1 fact a `controlled` row by D1's category rule; `resolved` only where a run shows a class gone — none expected; F-130 re-worded to rule v5); the review guide's lines (counts refreshed with run 8's) and the exit gate's rule-v5 wording applied once approved; on "off", every shadow-controlled row re-worded in this same commit (D7) and `docs/pilot/README.md:128-134`; `AGENTS.md`. Done when: `test_pilot_docs.py` green and committed; `Chosen: … (date)` on this line.
  - `[2026-11-07, the practitioner, in chat]` The P.5 answer: "Keep shadow on (Recommended), start P.3". Run 8 at `72256f4` did not meet rule v5's gate (falsifier 3, `h5-17/f0`); D7 fixes (a) after a FAIL, whatever the band rule reads, and no rule is changed (C16). Recorded as a dated decision on `plan-pilot.md` P.5. **Register, approvals pending:** the register rows (now that P.3 has classed the failures), the review guide's lines and the exit gate's rule-v5 proposal are not yet answered, so this line carries no `Chosen:` (its Done-when is not met).
  - `[2026-11-07T09:30:47+11:00, as built — stage-7 executor (leg px4); the commit is the composer's, on the practitioner's word]` **The three answers** (the practitioner, in chat, 2026-11-07; each the recommended option):
    1. Register rows — asked: "h5-17/f0 failed because the speech recogniser dropped a word of a fact (the body part a side belongs to) with no review mark; h5-01/f4 was a misheard spoken abbreviation under a number mark. Which form?" Answer: "(a) One row each (Recommended)" — a row for the failure (recogniser, quality), the marked abbreviation (controlled), and each of the two out-of-band readings (left-out-line load 6 on `h5-12`; surfaced doubt 1 of 11); every row keeps the shadow-mode control.
    2. Review guide — "Approve; hold shadow-off (Recommended)": the misheard number / unit / abbreviation lines approved as written, their counts refreshed with run 8's; the shadow-mode-off line stays awaiting approval.
    3. Exit gate — "Leave as a proposal (Recommended)": the rule-v5 wording stays a dated draft; the approved rule-v3 line stays the one read.
    (P.5, answered earlier — "Keep shadow on (Recommended)" — is on `plan-pilot.md` P.5 from leg px2.)
  - **Written** (uncommitted; ids and counts only):
    - `docs/pilot/findings-register.md`: F-149 (`h5-17`, high, quality, transcription), F-150 (`h5-01`, high, quality, transcription — D1's category rule: not a dose), F-151 (`h5-12`, medium, workflow, checker — as F-139 / F-140 for the left-out-line warning), F-152 (`—`, high, uncertainty, checker — a set-level reading, so no one encounter, as F-148), all `controlled`, Found and Closed 2026-11, every control under 200 characters, unquoted and id-free. F-130 re-worded to rule v5 (its Closed month kept, as run 7 kept it). The Encounter column's `h5-NN` note in the past tense. No row `resolved`; no row re-worded for shadow off.
    - **Seen sets:** no row. Run 8's seen sets equal predictions v5 (P.1), derived from run 7's reports, so they show no class new to the register.
    - **Not rowed by the answer's form:** the seven R2 facts and the two bare modals are inside F-152's set-level row. `h5-10`, R3 at its ceiling — a next patient's fact that reached a note — is a `cross-patient` class the answer did not list; F-132 (`h3-17`) holds the same class from run 6. Open for the composer (below). `[2026-11-07T10:23:43+11:00, leg px5]` **4. A fifth row** — asked: "Run 8's blind set had one encounter (h5-10) where the next patient's fact reached the note (R3, within its ceiling of 1). The register rule grades every cross-patient finding high, and run 6 had a row for its equivalent (F-132, h3-17). Add a fifth register row for it?" Answer: "Add the fifth row (Recommended)". Written: F-153 (`h5-10`, high, cross-patient, note-routing, `controlled`, F-132's control text, Found and Closed 2026-11). Run 8's rows are F-149–F-153.
    - `docs/practice/clinician-review-guide.md` (CRLF): the draft-history clause split — the misheard number, unit and abbreviation lines "approved by the practitioner on 2026-11-07, their counts refreshed with validation run 8's", the shadow-mode-off line "awaiting the practitioner's approval". The counts, by D2's method over run 8's Facts tables: 161 consultations (139 + `heldout-5`'s 22), 9 material facts `wrong`, 6 under a review mark (class R1: run 7's five and `h5-01/f4`) and 3 with none (`hld-14/f1`, `hld-21/f3`, `h5-17/f0`); `h5-10/f5` is `wrongly_present` (R3), not `wrong`. Nothing else changed.
    - `docs/practice/README.md` (CRLF): the program's-testing bullet's counts (161, 9, 6, 3) and the guide's approval status. Nothing else changed.
    - `docs/pilot/exit-gate.md`: UNCHANGED — the rule-v5 proposal stays a dated proposal, its rule-v3 line the one read.
    - `.cursor/plans/plan-pilot.md`: a dated "register after run 8" line under P.5, as run 7's `1f638b3` added one, and a pointer from the 2026-11-07 decision's "still open" to it.
    - `AGENTS.md` (CRLF) and `CHANGELOG.md` (CRLF; its run-8 bullet extended and its Phase 1 bullet's approval clause updated, as `1f638b3` updated run 7's).
  - **Suite owed:** `test_pilot_docs.py` reads the register (the composer runs the desktop suite through the runner).
- [ ] 🟨 **P.3 The `heldout-5` diagnosis** — the ONE task that examines its content: `HELDOUT_5_CASES` (`cases_written=True`), the divergence entries and count pins, the tails against the case boundaries (ids and integers), every failure and every marked-R1 fact classed by its own words (number, unit, abbreviation, side, negation, other) as run 7's P.4 classed `heldout-4`'s; the author-overlap count computed by a count-only script and recorded against its band (PR-MED-004); the presence pin removed; the blind rule ends (`validation/README.md` in the past tense; `test_lint_held_out_set.py:460` → `[]`); the set folder and `.cursor/loops/held-out-lint/` deleted. Done when: committed on the practitioner's word.
  - `[2026-11-07T09:05:48+11:00, as built — stage-7 executor (leg px2); the overlap run, the commit and the deletions are the composer's, on the practitioner's word]` **Record (ids and counts only).** The blind rule ends here (the practitioner's go, 2026-11-07: "Keep shadow on (Recommended), start P.3").
    - **Sources:**
      - the 22 scripts, `SPEC.md`, `AUTHOR-NOTES.md` and the `h5-` rows of `REFERENCE_TAIL_STARTS` (the author's prompt and session log were not needed);
      - run 8's `report-heldout-5.md`, read from its UTF-8 copy in `.cursor/loops/run8-of-record/utf8/`;
      - the product over the scripts' reference documents, read off the code (the frozen phrase lists, the correction markers, `HEDGE_PHRASES`, both cue layers, the boundary and Check 4 code) — not run: every value below is pinned in the suite, which the composer runs.
    - **Not read by this leg:** `C:\run8-p3\heldout-5\` (the composer's re-transcription, its two reports and the 22 dumps). Read and Grep there were refused (no permission outside the working directory), as run 7's `C:\run7-p4` was. So:
      - its `report-rule-v5.md` is NOT confirmed equal to run 8's report here;
      - no transcript was read, so `h5-17/f0`'s WHERE is narrowed but not decided (below), `h5-01/f4`'s misrendered word is not named, and the load's split-line share is not measured.
      - `[2026-11-07T09:13:38+11:00, leg px3]` Superseded: the composer copied them byte for byte to `.cursor/loops/run8-p3/heldout-5/` (git-ignored), and leg px3 read them there — see "The transcripts (leg px3)" below.
    - **What was written** (uncommitted):
      - `HELDOUT_5_CASES`: 22 cases. The set row is `cases_written=True` (the default), `tails_by_role=True`, `routed_material=True`.
      - Divergence entries:

        | Axis | Count | Ids | Reason |
        |---|---|---|---|
        | Boundary | 5 | `h5-03`, `-06`, `-10`, `-12`, `-14` | Four uncut (one closing not listed, three greetings not listed); `h5-14` cut one segment late (its welcome line also holds a listed closing, so the same-segment pairing cuts at the next). |
        | Corrections | 0 | — | No line opens with a frozen marker; every fix is a clinician's (`h5-02`, `-11`, `-18`), routes on its own cue (`h5-06`, `-08`) or follows a line no cue routes (`h5-21`). |
        | Unsure | 10 | `h5-02`, `-04`, `-07`, `-08`, `-10`, `-13`, `-14`, `-19`, `-20`, `-22` | Four hedges outside the frozen list (one a contraction of a listed one), three doubts on a line of their own, two bare modals, one more hedge outside the list; `h5-17`'s line holds a listed hedge and matches. |

      - The count pins are now 4 / 4 / 6 / 4 / 5 (boundary), 2 / 4 / 2 / 1 / 0 (corrections) and 3 / 10 / 7 / 6 / 10 (unsure).
      - D2 rule 4 over the set read after its run: a new test, `test_rule_4_holds_on_heldout_5_read_after_run_8` — 22 items (15 negatives, all without the axis; 7 positives), no false cut, no earlier cut, no lost match. The widening changed `h5-14` and `-17`, each from None (`_BOUNDARY_CHANGES_ON_HELDOUT_5`); `h5-17` now matches and `h5-14` is its recorded divergence. The widened-lists record test reads `heldout-5`'s changes as their own record, as `heldout-4`'s (`_SETS_READ_AFTER_THEIR_RUN`).
      - The lint's blind-set pin is now `[]`; the set-table pin reads no blind set and 22 cases; the temporary presence test is removed, as its docstring said.
      - `.github/workflows/ci.yml`: the comments above the runner step now say no set is blind (the step is unchanged and the runner has no blind-set dependency) — run 7's stale-comment item is not left this time.
      - In the past tense: `validation/README.md`'s `heldout-5` bullet (and its "user name redacted" corrected to "copied unchanged", as Task 0.5 records), the fixture's docstring. The harness document's run-8 entry gains the diagnosis sub-bullets.
      - NEW, git-ignored: `.cursor/loops/run8-p3-overlap.py`, the count-only overlap script (its definition in its docstring). Not run by this leg.
      - ruff and mypy green (below). **pytest owed:** the composer runs it plain (no set is blind) and through the runner.
      - `[2026-11-07T09:30:47+11:00, leg px4]` **Suite (the composer, over px2's and px3's changes, uncommitted):** plain `pytest -q` 9836 passed, 9 skipped, exit 0 (8m55s); through `scripts\lint-held-out-set.py validation\heldout-5`: ran 9845, passed 9836, failed 0, errored 0, skipped 9, exit 0. P.3 stays 🟨 only for its commit, which the composer makes on the practitioner's word together with P.2's.
    - **Tails against the cases' boundaries** (boundary / tail): `h5-01` 11 / 12, `-03` 6 / 7, `-06` 8 / 9, `-10` 9 / 10, `-12` 15 / 16, `-14` 8 / 9, `-17` 14 / 15.
      - All seven are one apart: the clinician's welcome has a line of its own.
      - Negatives: the 15 scripts without the axis have no tail row and draw no boundary. There is no axis negative: every axis script has a next patient, so the false-cut band reads no negative.
      - On the scripts' own words the product finds `h5-01` (11, its case boundary), `h5-14` (9, one past its case boundary and equal to its tail) and `h5-17` (14, its case boundary).
      - Reconciled with the report: its "3 of 7 (`h5-01`, `h5-14`, `h5-17`)" counts those three. Its mismatches `h5-01` (11 / 12) and `h5-17` (14 / 15) are the welcome offset, not a fault; `h5-14`'s reference boundary equals its tail. On the measured transcripts Check 6 fired on `h5-14` alone; why `h5-01`'s and `-17`'s boundaries were not found there needs the transcripts (their next patients' lines hold no cue, so nothing reached a note).
      - Why the four were missed, by the widened lists: closing not listed `h5-03`; greeting not listed `h5-06`, `-10`, `-12`; neither 0; a bare time-of-day word 0. One reached a note: `h5-10`'s next patient opens with a cue phrase (R3 1, at its ceiling). `h5-03`'s, `-06`'s and `-12`'s next patients' lines hold no cue.
      - Under the 2026-09-28 lists the product finds `h5-01` alone (1 / 7, 14%). Two of the three were found only through the dated widening of 2026-10-26, made before the set was written.
    - **Every failure, classed by its own words:**
      - **`h5-17/f0` FIRST (falsifier 3):** class **side** (leg px3, on the transcript: the misrendered word is **other**, a body part; the side was heard right — below) — a laterality fact on a long patient line that names both sides, its doubt about the side mid-line (the author's design). WHERE it went wrong:
        - **(iii) the script or reference reading: RULED OUT.** The fact's tokens are on its line, the line routes on the validation config's cue (the set's routing lint passed), and the product on the script's own words quotes the whole line, so the reference reading gets the fact right; the harness's `wrong` reads word coverage and matching, never the side's meaning.
        - **What the report shows:** verdict `wrong`, Warned no, surfaced no, not ambiguous, class `-`; the encounter has 0 unsupported clinical lines and 0 other unsupported words inside note lines, and 0 suspect segments. So no fact word was misheard inside a quoted line (any substitution there is counted as unsupported), and no side word of the fact was transcribed as a side and left unquoted (a side word left out draws an omission warning, which would have made it Warned).
        - **Two readings remain**, which the report cannot tell apart:
          - (i) the recogniser's: a word of the fact dropped, or misheard outside every quoted line as a word that is not a side, with no `{u}` / `{s}` mark (no low-confidence mark on any aligned word — surfaced no);
          - (ii) the note's: the fact's five words split across a quoted segment and an unquoted one — a bare cut the carry does not join — with the side heard right.
        - **What is missing to decide:** from the run's transcript of `h5-17` (the dump `C:\run8-p3\heldout-5\h5-17.txt`): the segments line 5 became (their indices, speakers and the cut points against the fact's five words); which of them the note quotes (the `EncounterOutcome`'s note lines); and, per fact word, whether it is present and its `{u}` / `{s}` flag. A word missing or misrendered there is (i); all five present and split across a quoted and an unquoted segment is (ii).
        - `[2026-11-07T09:13:38+11:00, leg px3]` **DECIDED: (i), the recogniser's.** Segment 9 (speaker_2, the patient, quoted by its cue) holds the fact's first four words, the side among them ("right", heard right), and DROPS the fifth, the body part the side belongs to (one deletion; the encounter 228 reference / 227 transcribed words). A dropped word has no transcribed word to carry a mark, and no word aligned to the fact has a `{u}` or `{s}` flag; the one mark nearby is `{u}` on the word after the gap (0.47, under the 0.60 threshold), outside the fact's words, so the harness's `marked` is false and the fact is not R1. (ii) is ruled out: no fact word is in another segment. The line's doubt about the side is in segment 11 (speaker_2), a later segment the note does not quote; the encounter has 0 suspect segments. The misrendered word's class is therefore **other** (a body part); the fact's kind stays laterality, and the side itself was right.
      - **`h5-01/f4`, the marked R1 fact:** a clinician's safety-net instruction holding a number and a spoken letter abbreviation, under the number mark its line carries (`number_source`). Class: **number or abbreviation**; which word was misrendered needs the transcript. Its encounter has about one wrong word in 177. `[2026-11-07T09:13:38+11:00, leg px3]` **DECIDED: abbreviation.** Segment 20 (speaker_1, the clinician): the number is heard right (`{u}` 0.95); the spoken "A and E" came out `A &E`, its middle word lost (one deletion; 177 / 176). The mark that makes it R1 is the line's `number_source` from that number, a fact word of the same fact — not a mark on the abbreviation.
      - **Rule v1's 11 failing encounters, by class:** `h5-01` (the marked R1 fact); `h5-10` (R3 `h5-10/f5`, the next patient's fact; and `h5-10/f1`'s doubt, a bare modal); `h5-17` (falsifier 3; and its doubt behind the wrong fact); `h5-14` (`h5-14/f2`'s doubt, a bare modal); and the seven R2 encounters.
      - **R2 7:** hedge outside the list `h5-04/f0`, `h5-07/f1` (a contraction of a listed hedge), `h5-13/f1`, `h5-22/f1`; doubt on its own line `h5-02/f0`, `h5-08/f1`, `h5-19/f0`; self-question 0; bare modal 0 (the two bare modals are not R2: the harness's reference list holds them).
      - **R3 `h5-10`:** its greeting is not listed, and the next patient opens with a cue phrase, so the next patient's fact reached the note.
      - **The raw material-wrong 3:** `h5-01/f4` excused by R1 (marked); `h5-10/f5` excused by R3; `h5-17/f0` excused by nothing.
      - **The two out-of-band readings:**
        - the `clinician_line_omitted` maximum 6, `h5-12`: the longest script (19 lines; 42 segments on the measured transcript), whose next patient was missed (its greeting is not listed), so its two later clinician lines sit inside the note's range. The split-line share under the joined run is NOT measured (no transcript read). `[2026-11-07T09:13:38+11:00, leg px3]` On the transcript: the clinician's speech is 17 joined runs (pieces ending in a comma joined), four of them from the next patient's two clinician lines, each two sentences (segments 33–34 and 36 from the first, whose last word was labelled speaker_2; 39 and 40 from the second). Check 4's second code counts once per joined run, so no comma split adds to the six, and no clinician line has a bare cut. The dump records no quoted segment, so which runs drew the six — and the split-line share — stays uncounted; a piece of a partly quoted line can here only be one sentence of a several-sentence line.
        - surfaced doubt 1 / 11: the 10 unsurfaced are the 7 R2 facts, the two bare modals (`h5-10/f1`, `h5-14/f2`; in the harness's reference list only) and `h5-17/f0` (its hedge is listed, so its line would draw `[check: unsure]` on the script's own words, but the fact came out wrong, so no hedge credit applies, and no word was low-confidence). The one surfaced, `h5-20/f1`, was surfaced by the recogniser's own mark alone; its hedge is outside the list.
    - `[2026-11-07T09:13:38+11:00, leg px3]` **The transcripts (leg px3).** Read: the dumps `h5-01`, `-02`, `-04`, `-07`, `-08`, `-12`, `-13`, `-17`, `-19`, `-20`, `-22` and `report-rule-v5.md` in `.cursor/loops/run8-p3/heldout-5/` (synthetic encounters only; nothing quoted here beyond a side word and a misrendered token).
      - **Report equality:** the composer found `report-rule-v5.md` (at `5edcefa`) equal to run 8's `report-heldout-5.md` on every line except the `[run ]` progress lines, one blank line and the commit. Confirmed by this leg's own read of its verdict lines (the four verdicts; `h5-17 (material_wrong)`; rule v1's 11), its residue section (R1 none; marked R1 `h5-01/f4`; R2's seven; R3 `h5-10`; excused 0), its load line (28 / 1 / 6) and its Facts rows for `h5-01/f4` (R1) and `h5-17/f0` (`wrong`, class `-`).
      - **R2's seven, re-checked:** every doubt was transcribed. Joined to the fact's segment at a comma or inside it: `h5-04`, `-07`, `-13`, `-22` (hedges outside the list); in its own segments after a full stop: `h5-02`, `-08`, `-19`. px2's split stands, and none is a hedge the recogniser lost.
      - **Surfaced 1 / 11, re-checked:** `h5-20/f1`'s credit is a `{u}` mark (0.12) on the fact's number; `h5-17/f0` drew no mark on its words (above). The 10 unsurfaced stand.
    - **The pre-registration (`edd1a7d`) re-read:** falsifiers 1, 2, 4, 5, 6 and 7 inside; falsifier 3 FIRED (1, inside its expected 0–2, and it fails at any count). Bands: marked R1 (1) inside; load median inside, maximum OUTSIDE; surfaced OUTSIDE; mismatches, boundaries found and false cuts inside; R2 reported; the author overlap 10 (reported; below). **Not pre-registered:** no axis negative exists in the set, so the false-cut band reads no negative; `h5-14` is cut one segment after its expected boundary by a widened closing inside its welcome line (D2 rule 4 admits it, and here it made the reference boundary equal the tail); the failed fact's line names both sides by the author's design; the marked R1 fact holds two of the misrendering classes at once.
    - **The author-overlap band (D4, PR-MED-004):** `.cursor/loops/run8-p3-overlap.py`, count-only, one integer. The value: **10** (the composer's run, exit 0, 2026-11-07; any value is reported; the band has no range). The script's definition: a `heldout-5` material fact whose canonical token sequence is contiguously inside, or equal to, any seen set's fact. "Contiguously inside" is the script's reading of D4's "appears in".
    - **Findings for the next plan** (never a rule change, C16, D7):
      1. **`h5-17/f0`, the failure, by its class once the transcript decides it:** if (i), the recogniser without a mark — the low-confidence threshold (0.60) and the mark's reach, a new dated decision with the guard and threshold measurements repeated (`plan-invented-text-guard.md` C2; Follow-Up Continuation Notes 1). If (ii), a split line the carry does not join — a note-side routing change of its own, a new dated decision with a fresh pre-registered blind set before any re-run. The composer's read of `h5-17.txt` (or a resumed leg with its permission) decides which. `[2026-11-07T09:13:38+11:00, leg px3]` **Decided (i):** the recogniser dropped a fact word with no mark on the fact (its one nearby mark on the next word, 0.47). So the first finding is Follow-Up Continuation Notes 1: the recogniser without a mark — the low-confidence threshold (0.60) and the mark's reach, as a new dated decision with the guard and threshold measurements repeated (`plan-invented-text-guard.md` C2); never a rule change (C16, D7). Its open question for that plan: a DROPPED word cannot carry a mark at all, so a mark's reach to a neighbouring word, not a threshold alone, is what could have surfaced this one. The (ii) branch is not taken.
      2. **The doubt the review does not surface (1 of 11):** four hedges outside the frozen list, three doubts on their own line, two bare modals. Any widening of `HEDGE_PHRASES` is a new dated decision (validation-pass C3) with a repeated run.
      3. **The next-patient greetings:** three of the four misses are an unlisted greeting, one reached a note (`h5-10`, R3 at its ceiling) — the practitioner's own phrases (Deferred) and any further widening as its own dated decision with `heldout-6`, pre-registered first.
      4. **The left-out-line load:** its maximum (6, `h5-12`) is outside the band; the share from split lines and from the missed next patient's lines should be measured (a report-only count) before any change. (Leg px3: on the transcript four of `h5-12`'s 17 clinician runs are the next patient's and no comma split or bare cut can add to the count; which runs drew the six needs that count.)
      5. **The marked R1 fact (`h5-01/f4`)** stays a `controlled` register row (D1); the review guide's misheard-number and abbreviation line is its control. (Leg px3: an abbreviation, under the number mark of the same line.)
- [x] ⬜ **NOT DONE: not applicable — P.2 chose keep shadow on (2026-11-07; D7).** **P.4′ Shadow off (practitioner; only if P.2 chose "off")** — after the pilot's P.4 tenth eligible shadow score and its one commit: leave "Shadow mode (pilot)" unticked on the installed app's Status tab from the first reviewed consultation; confirm the Status tab shows it off; the month recorded on `plan-pilot.md` P.5 and `AGENTS.md` (C8). Done when: recorded. (A recording started with the box ticked stays shadow — the mode is fixed at Start.)

## Retained Follow-Up Items
N/A — the plan is Active.

## Follow-Up Continuation Notes
- If run 8 fails on R1 silent or on a confident error without a mark: the recogniser without a mark — the low-confidence threshold (0.60) and the mark's reach, as a new dated decision with the guard and threshold measurements repeated (`plan-invented-text-guard.md` C2); never a rule change.
- If run 8 fails on R3: the practitioner's own phrases (Deferred) and a further widening as its own dated decision with another blind set (`heldout-6`, pre-registered first).
- If the band rule fires (marked R1 above 3) or marked numbers are passed over in the reviewed consultations: the distinct-mark plan (Deferred), then its own run.
- If run 8 passes and P.5 is decided "off": the exit gate's remaining lines (ten shadow and twenty reviewed consultations; the independent review of `docs/practice/`; the deferred timing item) are the pilot plan's own; F-088's ten-consultation count continues; the register's controls now read the review guide's — a new finding class in reviewed use is a new row, never a quiet edit of those.
- Design decisions that still apply: D1 (the class split and the fourth verdict), D5 (predictions from the reports when nothing decodes differently), D7 (the band rule and the acceptance per class); C16–C18.

---
*Plan saved to: .cursor/plans/plan-validation-run8.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
*Sections marked (Only if relevant) can be omitted when genuinely not applicable, but never omit decisions, constraints, verification steps, or integration knowledge that a fresh session would otherwise have to rediscover.*
*For lightweight plans, plans with fewer than 5 tasks, or plans created without a preceding `/explore` discussion, sections with no real content should be marked `N/A — simple feature` rather than padded with placeholder structure.*
*State-once convention (new plans): state each cross-section contract — a critical constraint, design decision, invariant, or other normative rule — once in its canonical section, and have every other section point to it rather than restate it. Scope guard: this governs cross-section normative duplication only — the Task Specification Standard (in `/create-plan` and `/review-plan`) and task-local detail are untouched, and a plan recording `fast/medium involved` in its Executor tier may keep extra restatement where it helps the fast executor. It applies to new plans as they are written; never retroactively rewrite an existing plan to conform.*
_Plan hardened by `/review-plan` 2026-11-06 (Fable 5.1); codex plan peer pass (3 rounds) applied and converged 2026-11-06. Planning only: nothing built, nothing committed._
