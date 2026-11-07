# Review findings — validation run 8

Companion to `plan-validation-run8.md`. It holds the FULL review round blocks that the plan carries only as digests.

**Lifecycle:** this file and its companion plan are ONE unit — move, archive or delete them together. A round present here must have its digest (or, mid-recovery, its full copy) in the plan; a round digest in the plan must have its full block here.

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
