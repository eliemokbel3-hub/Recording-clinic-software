# Feature Implementation Plan
**Feature:** note-routing-omissions (stop silent omissions in note routing: the practitioner's cue file layered over the shipped cues, Check 4 widened to sides, negations and doses from either speaker, the flagged lines made findable in review; version 0.3.1; the validation run of record repeated as the acceptance check)
**Overall Progress:** `17%` (3 of 18 tasks — Phase 0's three decisions)

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: `plan-pilot.md` (its Task P.3 run 1 FAILED 2026-10-09; this plan is the "routing fix" its amended stop rule names) and `plan-clinic-smoke.md` (its P.3 is the same run).
- Related: `plan-phase3a-note-pipeline.md` (Task 5.4 defined Check 4's clinician-only scope — amended here), `plan-practitioner-profile.md` (D6 whole-file cue replacement — narrowed here to the file, not routing), `plan-ui-refresh.md` (0.4.0; adopts the "Edit the note" group this plan edits — coordination in C10), `plan-past-sessions-backup.md` (also claims 0.4.0).
- Follow-up plans: None yet (candidates in Deferred).

## Goal
### Why this plan
The validation run of record (2026-10-09, run 1 — `docs/testing/validation-harness.md` "Runs of record"; pilot plan Task P.3; findings F-001…F-058) failed 49 of 50 synthetic encounters, 47 of them on silent omissions: 99 of 162 facts, at a word error rate of 0.031. The cause is routing, not transcription: `ExtractiveNoteProvider` quotes an utterance only when a cue of the config's own file matches it as a contiguous token run (`note.py:1372`, `:1628`); the practitioner's 26-phrase file (`validation/config/section_cues.json`) replaces the shipped cues as a whole, so most sentences match nothing; and Check 4 (`note_check.omission_warnings`, `:1478`) warns only on the confirmed clinician's segments and only for numbers, names and medications — never a side or a negation, never patient speech. P.4's shadow consultations may start under shadow mode (the stop rule amended 2026-10-09, `plan-pilot.md:1939`); P.5 and the exit gate's "Validation passed" wait for a repeated run.

### What the practitioner decided (2026-10-09)
- Plan Mode: the recommended design; `/review-plan` run on Fable 5.1; "go with recommended" for Phase 0: 0.1 layered cues YES; 0.2 option (b) — the harness's `warned` reads Check 4's new predicate, recorded as a metric amendment before run 2; 0.3 install point before P.4's first eligible score if P.4 has not started, else after its tenth.
- At `/review-plan`: carry-over DROPPED and deferred (the simulation shows it adds nothing once cues are layered and Check 4 is widened); an emptied section routing again under layering ACCEPTED; the review surface keeps transcript order, marks flagged lines and adds a "Show flagged lines only" filter; the plan is named `note-routing-omissions`.

### What done looks like
A build of record 0.3.1 under which a material fact said in an uncued sentence either reaches a section (the practitioner's cues first, the shipped cues as a fallback) or has its side, negation, number, dose, name or medication flagged by a review warning whose lines the clinician reviews (the chooser's mark and filter) before acknowledging the warning group — one per-code acknowledgement clears the group; per-line resolution stays deferred — and run 2 of the validation harness, from a clean checkout at this plan's hardening commit under rule v1 as amended 2026-10-09 (rule file, cue file, scripts and thresholds untouched), reports NO silent omission beyond the one named residue, with every remaining failure (the six next-patient encounters and run 1's non-routing findings) entered in the register as a named follow-up.

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Opus 5.5 (Plan Mode) and hardened on Fable 5.1 (`claude-fable-5-1`); the agent-built phases run through `/execute-loop` (executor Opus-class, cross-family peer codex `gpt-6-astra`); the validation run, the install and the smoke are run by the PRACTITIONER from a normal terminal and the installed app, never by an agent shell (`docs/lessons.md`, MSIX). Tier-gap dosing applied: D1–D9, the pin inventory (C-rules and each phase's named test changes), the predicate's exact composition and the acceptance numbers are locked here so the executor rediscovers nothing.

Planning sources: the parent session's brief (2026-10-09); the approved native plan (Plan Mode, Opus 5.5, same day); a text-level simulation of routing options over the 50 scripts (scratchpad only — ids and numbers; its baseline reproduces run 1: 101 simulated silent omissions against run 1's 99); one Plan-agent critique at Plan Mode and four parallel `/review-plan` lenses (coverage, practicality, risk, simplicity) over the code; `docs/testing/validation-harness.md`, `docs/pilot/findings-register.md`, the threat model's Phase 3A and pilot sections, `docs/design-system.md`. No `explore-*.md` scratch was consumed (both existing ones cover other areas; the practitioner chose none).

### Agreed Scope (Build Now — 0.3.1)
- Layered cues: the extractive provider routes by the config's own cues first (all sections, in order), then by the shipped cues for an utterance the own cues do not route — the ownership rule in both passes (D1).
- Check 4 widened with its own predicate — the structured-claim classes (side, number, dose, strength unit, negation) and the medication lexicon for EVERY speaker, name-like tokens for clinician segments only — over every speaker's segments once a role is confirmed; `_is_high_risk_token` untouched (D2).
- The ONE harness change, in the same commit as D2: `encounter_metrics`'s `warned` reads the new predicate, and the report adds a "silent (run-1 predicate)" column so run 2 is also readable in run 1's terms (D3, decision 0.2 (b)).
- The review surface: "Acknowledge all review warnings" no longer clears `high_risk_omission` (its existing per-code Acknowledge does); the Line chooser keeps transcript order, suffixes a mark on each flagged line and gains a "Show flagged lines only" checkbox; new warning copy (D4).
- Documents (D6) and version 0.3.1 in all six strings (D5); hardening H1–H5; the validation run repeated (P.1) and the install with its smoke (P.2).

### Deferred — Actionable Later
- **Carry-over of an uncued utterance into the preceding cued utterance's section** (dropped at `/review-plan`, practitioner 2026-10-09).
  - Why deferred: the simulation over the 50 scripts — own cues only: 101 silent / 48 encounters; layered + widened Check 4, no carry: 1 silent / 6 encounters; the same with a one-hop carry: 1 silent / 6 encounters, one more wrongly-present fact (`syn-43`) — so carry-over adds nothing measurable and brings edge cases (a spoken instruction or injection line quoted after a cued line, the inverted question/answer roles, the next patient after a cued greeting).
  - Intended future outcome: if P.4/P.5 review shows uncued, non-high-risk facts being missed in real consultations, a bounded one-hop rule (a cued question's answer by the other speaker; never into `CLINICIAN_OWNED_SECTIONS`; "no cue in any layer or section, ownership ignored" through a new `any_cue_matches` helper; a dropped line breaks the chain; an empty-text utterance is transparent).
  - Relevant files / subsystems: `note.py` `ExtractiveNoteProvider.generate_sections`; `test_note_matrix.py` cells `ex-numbers-meds-doses`, `ex-uncertain-omitted`, `ex-spoken-injection`, `ex-greeting-and-close`; `test_ui_screens.py` `_EDIT_TURNS`.
  - Dependencies / prerequisites: run 2's numbers; the P.5 reviewed consultations' findings.
  - Recommended next action: re-run the scratch simulation with the carry variants against the then-current cue file before planning.
  - Risk if deferred: `ux-degradation`: an uncued sentence with no structured-claim word (`syn-48`'s "it is better") stays a silent omission the clinician must catch from the transcript panel.
  - Revisit by: the clinic 1 exit gate (pilot plan P.6) or a P.5 finding of category `omission`, whichever first.
- **New-patient (end-of-consultation) detection** — the six-encounter residue (`syn-06`, `syn-20`, `syn-21`, `syn-38`, `syn-43`, `syn-46`): the next patient's first line carries a shipped cue in a section anyone may fill, so it is quoted whatever the transcription quality.
  - Why deferred: needs a detector the pipeline does not have (validation-harness.md "End of consultation and new patient"); out of this fix's scope.
  - Intended future outcome: a boundary after which no utterance is routed, or a review-time "ends here" control.
  - Relevant files / subsystems: `note.py` routing; `context_rules.py` (the pause rule covers only a Chrome navigation before the next patient speaks); the Note tab.
  - Dependencies / prerequisites: run 2 confirming these six as the only routing residue.
  - Recommended next action: plan it with the P.5 findings in hand; until then the control is review (the transcript beside the note with speaker labels) and, for P.4, shadow mode.
  - Risk if deferred: `correctness`: in a non-shadow consultation a second patient's words can reach the first patient's draft if the clinician does not remove the line (Check 4 then flags the removal's high-risk words — acknowledgeable).
  - Revisit by: before pilot plan P.5 (shadow off).
- **Run 1's non-routing failure kinds** — uncertainty not surfaced (6 encounters), unsupported clinical lines (2), material wrong (2).
  - Why deferred: transcription and checker work, not routing; the harness doc's Known limits already name their shapes.
  - Intended future outcome: each a register row with its own control or fix.
  - Relevant files / subsystems: `transcription.py` (uncertainty marks), `note_check.py` Checks 1–2, the scripts' `expect_uncertain` flags.
  - Dependencies / prerequisites: run 2's per-encounter table.
  - Recommended next action: triage after run 2; a finding, never a rule change (pilot plan Constraint 12).
  - Risk if deferred: `blocked-work`: P.5 and the exit gate's "Validation passed" wait on a passing run.
  - Revisit by: run 2's record.
- **Spoken instructions to the scribe** ("Scribe, don't record the following") — the app honours none; under layering an instruction line or the content it fences can be quoted when it carries a shipped cue (the `scribe_instruction` scripts' `absent` facts).
  - Why deferred: PLAN.md's own list; a feature, not this fix. Risk if deferred: `minor`: fenced-off content reaching a draft is caught at review; in run 2 it is a counted `wrongly_present` finding. Revisit by: a P.5 finding or PLAN.md Phase 3B.
- **A per-line "leave out" resolution** for flagged lines, if P.4/P.5 shows the single Acknowledge is rubber-stamped. Risk if deferred: `ux-degradation`. Revisit by: the clinic 1 exit gate.
- **A per-section "off" switch** (a section emptied in the practitioner's file stays unrouted — no shipped fallback for it). Accepted-not-wanted for 0.3.1 (practitioner 2026-10-09); plan only if the practitioner asks. Risk if deferred: `minor`.

### Excluded — Revisit Only If Needed
- An in-note "Unsorted" / "Other things said" section (every uncued utterance quoted for review). Why excluded: the simulation puts 12 material `absent` facts into the note (fenced-off content, next-patient lines) and 14 non-material ones — every leak becomes a `wrongly_present` failure, and the note stops excluding small talk (PLAN.md). When to revisit: never for the extractive provider; a 3B model with a classifier is a different design.
- Counting an unplaced-but-flagged utterance as "warned" without a structured-claim word. Why excluded: degenerate — a provider that routes nothing would pass. The widened predicate stays a closed class of structured-claim words.
- Changing rule v1, the pass thresholds, the cue file `validation/config/section_cues.json`, the scripts or the metric's definitions beyond D3 (pilot plan Constraint 12; clinic-smoke D9). A failure is a finding.

### Accepted Assumptions — Revalidate Later
- Warning volume is bearable with the filter: roughly a third to a half of a patient's lines carry a side, negation or number (spelled numbers included — "one" as a pronoun counts), so a 20-minute consultation may flag 20–60 lines under ONE warning row.
  - Why accepted for now: the review surface shows one `WarningGroup` row per code and the chooser filter isolates the lines; the existing per-CODE Acknowledge of the group (`ui/note.py:2154-2158`) is the control — one click clears the whole group once the lines have been reviewed (PR-LOW-005).
  - Risk if assumption becomes false: the warning is rubber-stamped → the deferred "leave out" resolution, or a narrower class (the pronoun "one").
  - Trigger for revisit: P.2's smoke count (recorded as a NUMBER in the off-repository pilot log) or a P.4 observation.
  - Recommended next action: measure before narrowing anything; a predicate change is a new metric amendment, never silent.
- The learner's "already a cue" check and the Practitioner tab's learned-phrase list read the OWN file only; with layering a shipped phrase learned into another section wins routing (pass 1) but is filtered out of the "learned" list (`note_config.load_learned_phrases`).
  - Why accepted for now: routing follows the practitioner's intent; only the tab's listing is incomplete. Risk: `minor`. Trigger: a practitioner report of a phrase "not shown as learned". Recommended next action: list such phrases with a "(replaces a built-in cue)" note.
- The script lints in `test_validation_scripts.py` dry-run OWN cues only and stay a lower bound of real routing (a clause they call unrouted may route by the shipped layer). Why accepted: they exist to guarantee routability of `expect_uncertain` and consent facts, which layering only strengthens. Trigger: a lint rewrite.
- `is_interrogative` and `section_admits_utterance` are unchanged; the shipped file's completeness rule (`_parse_shipped_section_cues`) guarantees every section has fallback cues. Trigger: a change to either.

### Key Design Decisions
- D1–D9 below (Design Decisions). Still apply to follow-up work: Yes, all.

## Key Findings

### Files / Symbols Involved
- Routing: `desktop/src/scribe_desktop/note.py` — `first_matching_section` :1372 (unchanged), `ExtractiveNoteProvider` :1598 (`__init__` :1608 takes `cues` only; `_route` :1618; `generate_sections` :1628), `DEFAULT_SECTION_CUES` :1268, `_parse_shipped_section_cues` :1209 (every section has shipped cues), `section_admits_utterance` :1338, `CLINICIAN_OWNED_SECTIONS` :167, the protocol-conformance constant at :2611. The one app construction site: `ui/models.py:2836-2843` `extractive_provider_from_config` (also used by `validation.py:1352` and `replay_kept.py:314`; identity pinned at `test_validation_harness.py:559`). The learner's dry-run: `ui/note_review.py:405-425` (`consider_learning` builds its own cue mapping and calls `first_matching_section`).
- Check 4: `note_check.py` docstring :124-138; `_is_high_risk_token` :1472; `omission_warnings` :1478-1521 (the `continue` on non-clinician segments at :1505); classes `_LATERALITY_TOKENS` :274, `_MEDICATION_LEXICON` :305, `_STRENGTH_UNITS` :364 (a dict), `_dose_quantity(token)` :751, `_polarity_mark(token)` :1583 (defined below `omission_warnings`, fine at call time); `transcription.is_number_token` :413 (self-normalising), `is_name_like_token(text, *, first_in_segment)` :425 (needs RAW case); `check_note` :1686 (:1722 calls Check 4).
- Harness: `validation.py` imports :94-104 (`_is_high_risk_token` at :102, the four structured classes at :99-103); `is_structured_claim_word` :481-494; `encounter_metrics` :979 (`warned` at :1048-1050; `note.clinician_speaker` is the label-derived cluster, `compose_draft(..., clinician_speaker=clinician)` :1392); `render_report` :1514 (a 20-column table whose metric-cell array holds 14 entries — `silent`/`warned` at :1558-1559, totals :1597; the comparison column makes it 21 columns and 15 metric cells, with the header, separator, measured and unmeasured rows and totals kept aligned — PR-LOW-013).
- Review surface: `ui/note.py` — `_acknowledge_all` :1114-1123, the button :662 (visibility :2161), `_refresh_warnings` :2128-2161 (ONE row per code with its own Acknowledge button :2154-2158), `eligible_utterances` :1155-1163, `_rebuild_edit_controls` :1683-1697 (the chooser rebuilt on every re-finalise), `edit_group` :626-634; `ui/models.py` — `WARNING_COPY["high_risk_omission"]` :2139-2144, `UtteranceChoice` / `eligible_utterances` :2466-2502, `summarise_warnings` :2194 (`WarningGroup.section_keys` — Check 4 sets no section, so the group cannot point at lines); `ui/note_review.review_counts` :440 keeps Save blocked while a review warning is unacknowledged; `complete_block_reason` `ui/models.py:2246`.
- Version (six strings, five files, pinned equal by `desktop/tests/test_install_layout.py:867-882`): `desktop/pyproject.toml:7`, `desktop/src/scribe_desktop/__init__.py:3`, `extension/src/manifest.ts:29`, `extension/package.json:4`, `extension/package-lock.json:3` and `:9`. Derived, no edit: `packaging/scribe.iss:43` (from `scripts/build-release.py:163`), the Status tab (`ui/main_window.py:308`), the audit row's `app_version` (`session.py:596`). `test_past_sessions.py:2440`'s "0.3.0" is fixture data.
- Register: `docs/pilot/findings-register.md:90-147` rows F-001…F-058 (`controlled`, shadow mode, 2026-10); `desktop/tests/test_pilot_docs.py:123-145` (Status vocabulary; Control-or-fix ≤200 chars, no quotation marks, no id-shaped run; a build version such as "0.3.1" passes).

### Codebase Integration Notes
- `config_digest` (`note_config.py:899`) hashes the RESOLVED config, the own cue file included; the shipped cues are package data, bound by the commit (harness: `validation.py:1497` commit + models-manifest hash; app: the audit row's `app_version`). After D1 "what routed this note" = config digest + app version (+ commit in the harness). D7's "every note is bound to the cue set that routed it" (`note_config.py:59-63`) is narrowed accordingly.
- With no user cue file, `load_note_config` parses the packaged `section_cues.json` and `normalised_cues()` applies the same `content_tokens` derivation as `DEFAULT_SECTION_CUES` — equal by VALUE, not identity (a learned-sidecar append makes them differ): the no-op test compares outputs, never `is`. `append_user_cues` seeds the user file from the shipped default (`note_config.py:1981-1985`), so for a learner-created file pass 2 is a no-op; deleting a shipped phrase from the own file does NOT disable its shipped fallback, but it can change the WINNING section when another own cue, or the cross-section override D1 allows, competes in pass 1 (PR-LOW-006).
- `test_shadow_exits.py` pins text widgets (`_TEXT_WIDGETS` :57) and the built-widget counts (`_BUILT_WIDGETS` :106-115) in `ui/note.py`; a `QLabel` or `QCheckBox` is not counted, and the chooser stays the existing `NoCopyComboBox` — nothing in this plan touches a pin there (C2).
- The chooser's label pins use `startswith(f"{index + 1}. {speaker}: ")` (`test_ui_models.py:1321`, `test_ui_screens.py:5515`) and transcript order (`:1318`, `:5502-5511`): a label SUFFIX and unchanged order keep every one.
- `NoteWarning` carries code, severity, section, id and coordinates only; `AuditModels` has no warning field; `note_warnings` / `note_warning_code` are log tripwires — a flagged patient segment reaches no log or audit row (the count label is an integer).
- The replay tool (`replay_kept.py`): "Drift WER" (:293) is transcription-only and stays comparable with P.3's 0.000; "Check reviews" (:328) WILL move under D2 — expected, not a finding; "Sections missing" (:311-329) is computed from section presence under the SHIPPED config, where layering is a no-op, so it is NOT expected to change and any observed change needs an explanation (`docs/testing/kept-recordings.md:35-40`; PR-LOW-007).
- `/execute-loop` phasing: Phase 1 (routing + checker + harness) is the invariant-bearing phase — one review boundary; Phase 2 (UI) and Phase 3 (docs + version) are low-risk. Shared helper: `note.layered_section` (Task 1.1) is reused by the learner (1.3).

### External / API Findings
- N/A — no network, no new dependency.

## Planned Workflow Summary

### Flow 1 — A consultation on 0.3.1
- Generate: each utterance tries the practitioner's cues, then the shipped cues; the ownership rule holds in both. Review: ONE "…not in the note" warning row (count) with its own Acknowledge; the Line chooser in transcript order, flagged lines marked " — flagged: not in the note", a "Show flagged lines only" tick to see just those; the clinician adds a line or acknowledges; "Acknowledge all" clears every OTHER review warning. Save, Copy and Write unchanged.

### Flow 2 — Run 2 of the validation harness (practitioner)
- From a clean checkout at this plan's H4 commit: build the 50 scripts, run the harness under rule v1 as amended 2026-10-09; the report's omission columns now read `silent` (the amended predicate) and `silent (run-1 predicate)`; record both, the commit, the manifest hash, the voices and the cue file's blob; enter each remaining failure in the register; set F-001…F-058 per the result.

### Flow 3 — Install (practitioner)
- Verify, install the build of record current at the install point (0.3.1, or 0.4.0 if it has landed on `main` — it carries this change), reload the extension, restart Chrome; smoke one shadow consultation; D15's "before" hash paste AFTER the install.

## Design Decisions
- **D1 — Layered cues: two passes, own then shipped, inside `ExtractiveNoteProvider` (`fallback_cues=DEFAULT_SECTION_CUES`, defaulted).** `_route` calls `first_matching_section` with the config's cues; only when that returns None does it call it again with the fallback cues — both calls under the ownership rule and the question test. The order matters: a merged per-section list would be ONE pass in section order, so a shipped cue in an EARLIER section ("sore" → Presenting complaint) would beat the practitioner's own cue in a later one ("exercises" → Advice) and put the clinician's line in a patient section; two passes let the practitioner's phrase win wherever it sits. Consequences, stated: a user file no longer switches a section off by emptying it (accepted); deleting a shipped phrase from the own file leaves its shipped fallback in force but may change the winning section (Codebase Integration Notes); the shipped layer is bound by the build, not the config digest. Alternatives rejected: a merged mapping with no provider change (wrong precedence, above); changing `load_note_config`'s whole-file replacement (the file semantics, D6 of the profile plan, stay; only routing layers).
- **D2 — Check 4 widened by a NEW predicate, `_is_high_risk_token` untouched.** `_omission_flag_token(text, *, first_in_segment, clinician)`: normalise once; True when the token is in `_LATERALITY_TOKENS`, or `is_number_token`, or `_dose_quantity(token) is not None`, or in `_STRENGTH_UNITS`, or `_polarity_mark(token) is not None`, or in `_MEDICATION_LEXICON`; else `clinician and is_name_like_token(text, first_in_segment=...)`. Composition, not a re-spelled class list, so it is by construction a superset of `_is_high_risk_token` on clinician segments and of `validation.is_structured_claim_word` on every segment (pinned). `omission_warnings` drops the clinician-only `continue`, passes `clinician=segment.speaker == note.clinician_speaker`, and still emits nothing with no confirmed role. Why names stay clinician-only: a mid-segment "I" is name-like, so patient speech would flag on nearly every line. Alternatives rejected: widening `_is_high_risk_token` in place (hides the metric change behind a function the pilot plan recorded as "read, not changed"; the harness needs an edit either way for the clinician flag).
- **D3 — The ONE harness change, decision 0.2 (b), in the SAME commit as D2.** `validation.py:1050` reads `_omission_flag_token(..., clinician=segments[i].speaker == note.clinician_speaker)` (the import at :102 swapped); `warned` still requires the note's OWN `high_risk_omission` on the segment, so a provider is never credited for a flag it did not raise. The report adds a `silent (run-1 predicate)` column computed with `_is_high_risk_token` and the clinician-only scope, so run 2 is reported in run 1's terms as well. Recorded in `validation-harness.md` as "metric amendment 2026-10-09 (decision 0.2 (b), before run 2)" with: the superset test, the route-nothing-provider test (such a provider still fails rule v1 — every omitted material fact without a token `_omission_flag_token` accepts for its speaker stays silent; medications and clinician-name tokens are in the predicate but outside `is_structured_claim_word`, so the fixture fact carries none of them — PR-MED-004), and that rule v1's lines are unchanged. Why not (a): D2's flags would be measured as silent (about 25 remain) and P.5 would stay blocked on a control that exists. Constraint 12: Check 4 is a review warning, not an enforcing control; the amendment is dated before the run and visible in the report.
- **D4 — The review surface: findable, not reordered; one click no longer clears it.** `_acknowledge_all` skips `high_risk_omission` and the button's visibility ignores it (else it stays up with nothing to do); the existing per-code Acknowledge (`ui/note.py:2154-2158`) is the control, and `review_counts` keeps Save/Complete/Copy gated until it is clicked. `eligible_utterances(..., flagged=)` suffixes " — flagged: not in the note" (label pins use `startswith`; order unchanged); a `QCheckBox` "Show flagged lines only" in `edit_group` filters the chooser (rebuilt in `_rebuild_edit_controls`; its state survives a rebuild like the current choice does); one `QLabel` count line. Copy: "A side, negation, number, dose, name or medication someone said is not in the note" + "Check the transcript beside the note (a line you removed can raise this too), tick 'Show flagged lines only' to find them, then acknowledge." Alternatives rejected: flagged-first ordering (rewrites the order pins, breaks the transcript-order mental model); a new count line AND a new Acknowledge (both exist already).
- **D5 — Version 0.3.1, a build of record; the install is whichever build of record is current at the install point.** No schema, audit-field or config-format change, so no "Rolling back below 0.3.1" section (a 0.3.0 reinstall reads everything). `npm version 0.3.1 --no-git-tag-version` in `extension/` (never a blind replace — the lock has `@vitejs/devtools ^0.3.0`), then `extension/src/manifest.ts:29` (a literal) and the two Python strings by hand (PR-LOW-010). This plan lands on `main` BEFORE ui-refresh's 0.4.0 cut; if 0.4.0 has already landed when Phase 3 starts, Task 3.2 does NOT set 0.3.1 — the practitioner re-decides this plan's version (the next patch above `main`'s, coordinated with ui-refresh's claimed 0.4.1) by a dated note on this decision before Task 3.2, and the acceptance/release sequence is renumbered with it; `main`'s version is never reset downward (PR-MED-008). Install point (decision 0.3): before P.4's first eligible score if P.4 has not started (P.4 is 🟥 with no eligible score; P.1's two mock rows are never eligible), else after the tenth; if 0.4.0 (ui-refresh) has landed on `main` by then, that one install carries this change — the run record names `app_version` for C01–C10 either way. The `provider_name` stays `extractive-v1`: nothing displays it, the audit row's `app_version` distinguishes the builds, and a rename would be three test pins for no reader.
- **D6 — Documents: the contracts this plan changes are amended in their canonical places only** (Task 3.1's list), and the two closed plans that recorded the old contracts get DATED amendment lines, never edits to their Done blocks.
- **D7 — Acceptance is run 2 read against this plan's residue list, not "PASS".** Expected: silent omissions ≤ 1 (`syn-48`), the six next-patient encounters failing on `material_wrong`/`wrongly_present`, run 1's non-routing failures unchanged or fewer. Any OTHER silent omission, or a new unexpected checker failure (more quoted lines mean more Check 2 comparisons and more chances of an unsupported line), is a finding for this plan's hardening, never a reason to touch the rule.
- **D8 — The learner's dry-run tells the truth under layering.** `consider_learning` routes the proposed cue set through `note.layered_section(own, fallback, …)` (the provider's exact two-pass rule, one function), so "an earlier section would still win" and "a shipped cue already routes this line" are computed over what will actually route. The script lints keep reading own cues only (an accepted lower bound).
- **D9 — Nothing per consultation enters a tracked file** (clinic-smoke D12): the smoke's flagged-line count and any real-consultation observation go to the off-repository pilot log as numbers; the register rows stay content-free.

## Schema / Data Changes
- None. `note.enc`, the audit row (`note_provider` stays `extractive-v1`; `app_version` 0.3.1), the encounter record and the Past-sessions entry are unchanged. The harness report gains one column (a developer-tool output, not a stored record).

## Config / Environment / Deployment Impact
- No env vars, no config-file format change. `validation/config/*`, `validation/scripts/*`, `validation/rules/*` untouched (C1).
- Release: 0.3.1 built of record by CI's `Release` workflow (attested; `docs/release/pilot-builds.md` row; the model pack unchanged — `models-manifest.json` untouched). Installer: same `AppId`, in-place upgrade; no rollback section needed (D5).
- Order of landing (authoritative — PR-MED-003): Phase 1 (one commit for D2+D3, one for D1) → Phase 2 → Phase 3 INCLUDING all six version strings (Task 3.2) → H1–H4 → the practitioner's P.1 on the H4 commit → H5 releasing THAT EXACT commit (H5 adds only the release record; it changes no version and no code) → P.2. Any code change after P.1 goes back through hardening and a new acceptance run.

## Critical Constraints
1. **C1 — Not changed, ever, by this plan:** `validation/rules/option-a-proposed.json`, `validation/config/section_cues.json` and `autofill_rules.json`, the 50 scripts, the harness's pass thresholds and fixed failures, Check 2's severity contract, the refusal filter and the connective allow-list (pilot plan Constraint 12; clinic-smoke D9). The ONE harness change is D3, in one named commit, dated before run 2.
2. **C2 — `test_shadow_exits.py` passes UNCHANGED:** no new text widget, list, combo box, clipboard, drag or selectable-text flag in `ui/note.py`; the chooser stays `NoCopyComboBox`; the new controls are one `QCheckBox` and one `QLabel`.
3. **C3 — The ownership rule holds in every pass:** `section_admits_utterance` / `CLINICIAN_OWNED_SECTIONS` / the confirmed role gate both cue layers; with no confirmed role the clinician-owned sections stay blank and Check 4 emits nothing.
4. **C4 — The predicate is a superset, pinned:** `_omission_flag_token` ⊇ `_is_high_risk_token` on clinician segments and ⊇ `validation.is_structured_claim_word` on every segment; `_is_high_risk_token` is not edited.
5. **C5 — `first_matching_section` and `_route`'s cue-only semantics are unchanged;** layering is a second call, never a merged mapping (D1).
6. **C6 — Shadow mode, Copy and Write are untouched;** the Acknowledge-all exclusion changes WHICH button clears the warning, never what a saved, copied or written note needs (`review_counts`, `complete_block_reason`, `_copy_ready`).
7. **C7 — Nothing checked from an agent shell counts for Phase P** (`docs/lessons.md`): the run, the install and the smoke are the practitioner's from a normal terminal; the run is from a clean, committed checkout.
8. **C8 — No real patient content in any file, commit, register row or plan line** (D9); the simulation script stays in the scratchpad.
9. **C9 — The version bump goes through `npm version` for the package and lockfile strings, then the manifest literal `extension/src/manifest.ts:29` and the two Python strings by hand;** `test_install_layout.py:867-882` pins all six equal. **Never lower `main`'s version:** Task 3.2 sets 0.3.1 only while `main` is still at 0.3.0 (PR-MED-008).
10. **C10 — Coordination with `plan-ui-refresh.md`:** both edit `ui/note.py`'s `edit_group` contents and `_acknowledge_all`; ui-refresh adopts `edit_group` WHOLE (its D6), so the checkbox and label travel with it. This plan is intended to land FIRST (D5); whichever lands second rebases its line references AND the overlapping behaviour (the Acknowledge-all exclusion, the chooser mark and filter inside the adopted `edit_group`), and never lowers the version (PR-MED-008); the two never build at once in the same checkout (one `/execute-loop` run at a time on `main`).

## Validation / Verification
- Desktop: `ruff check . && mypy && pytest` in `desktop/` green at every phase close (the suite is ~6 900 tests; the real-ML legs skip without models). Extension: `npm run qa` (the version bump touches it).
- Phase 1 pins named in Tasks 1.1–1.3; Phase 2's in 2.1–2.3.
- P.1 — run 2 of the validation harness, read against D7: silent ≤ 1 (`syn-48`); `silent (run-1 predicate)` recorded beside it; the six next-patient encounters; no new unexpected checker failure; no `scribe-speaker-eval-*` folder left in `%TEMP%`.
- P.2 — the installed smoke: the warning row shows the count; "Acknowledge all" leaves it; the tick filters the chooser; the per-code Acknowledge clears it; Status tab shows 0.3.1 (or 0.4.0); the audit CSV's `app_version` column shows the build.

## Deferred / Out of Scope
- See Planning Extraction Summary (the Deferred and Excluded lists are canonical; nothing is restated here).

## Current State / Handoff Note
- Last completed step: `/review-plan` hardening (2026-10-09, Fable 5.1): four parallel lenses over the code; carry-over dropped on the simulation's numbers; the practitioner's four hardening answers recorded above. Then the cross-family plan peer pass (`/peer-loop hardened plan astra medium`, the practitioner's word, 2026-10-09): codex `gpt-6-astra` medium rounds 1–3 (`.cursor/loops/note-routing-peer-r{1,2,3}.log`, composer-recorded), 7 → 4 → 2 findings (build-affecting 4 → 2 → 0; no CRIT/HIGH), every one verified against the code and applied as an amendment; CONVERGED at round 3 (zero new build-affecting; the two record-only findings applied). The plan file is UNCOMMITTED — commit on the practitioner's word.
- Current in-progress step: None.
- Immediate next action: `/execute-loop` from Phase 1 (its setup wizard first; nothing blocks Phase 1). Land this plan before ui-refresh's 0.4.0 cut (C10, D5).
- Open blockers / open questions: none for Phase 1. Phase P needs the practitioner (C7).
- Last plan sync: 2026-10-09.

## Review History
- 2026-10-09 round 1: 0 CRIT / 0 HIGH / 4 MED / 3 LOW; skew=none; action=fix (plan peer-review round 1, codex gpt-6-astra medium, composer-recorded; Materiality 4 build-affecting / 3 record-only / 0 invalid; all seven verified and applied as plan amendments — the flagged-segment locator for typed-replaced lines, register rows reconciled by failure kind, the version-then-H5 order, the route-nothing fixture's predicate, three record-only wordings)
- 2026-10-09 round 2: 0 CRIT / 0 HIGH / 1 MED / 3 LOW; skew=none; action=fix (plan peer-review round 2, codex gpt-6-astra medium, composer-recorded; Materiality 2 build-affecting / 2 record-only / 0 invalid; all four verified and applied — the never-lower-the-version rule and landing order, the matrix inventory corrected with ex-small-talk kept unchanged, the manifest literal named in D5/C9, the normalised_cues docstring added to Task 3.1; not converged: two NEW build-affecting findings)
- 2026-10-09 round 3: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=docs-only; action=none (plan peer-review round 3, codex gpt-6-astra medium, composer-recorded; Materiality 0 build-affecting / 2 record-only / 0 invalid; both verified and applied — the provider factory's docstring, the report's column arithmetic; CONVERGED: zero new build-affecting findings at round 3 of cap 5)

## Review Findings Log

### Round 1 - 2026-10-09 - note-routing-omissions plan, independent cross-family codex plan peer-review (round 1)
Source: Codex plan peer-review
Peer: codex gpt-6-astra medium, read-only sandbox
Scope: as above
Materiality: 4 build-affecting / 3 record-only / 0 invalid
Severity: 0 CRIT / 0 HIGH / 4 MED / 3 LOW
Round status: Closed (composer-recorded round — the peer's read-only sandbox cannot append; transcribed verbatim from `.cursor/loops/note-routing-peer-r1.log`; every finding verified against the code by the planning session and dispositioned below)

#### Findings

**PR-MED-001 — Flagged-only chooser cannot locate every omission warning**
- Severity: MED
- Materiality: build-affecting
- Plan challenged: D4; Task 2.2.
- Evidence: `desktop/src/scribe_desktop/ui/note.py:1150-1163`; `desktop/src/scribe_desktop/ui/models.py:2483-2489`; `desktop/src/scribe_desktop/note_check.py:1493-1518`.
- Defect: A typed replacement retains its original segment in the chooser’s excluded “already in note” set, but Check 4 does not credit typed assertions as transcript coverage. Replacing a numbered transcript line can therefore produce a counted omission warning that the proposed flagged-only chooser cannot display; partial coordinate coverage has the same mismatch.
- Concrete amendment: “Task 2.2 exposes a locator for every flagged segment, including represented or typed-replaced segments, without permitting duplicate Add operations. Mark the existing editable row where possible and identify remaining flagged segments by transcript line number in the plain-text label. Add typed-replacement and partial-coverage regression cases proving every counted flagged segment remains locatable.”
- /fix decision: Applied (2026-10-09, planning session, verified: `ui/note.py:1146-1152` adds a typed-replaced segment to the chooser's excluded set while Check 4 credits no typed line) — Task 2.2 now marks the editable row of a flagged replaced or partly-covered line and has the count label name, by transcript line number, every flagged segment the chooser does not offer; the typed-replacement and partial-coverage regression cases added. Materiality verified: build-affecting.

**PR-MED-002 — Register resolution must follow each row’s failure kind**
- Severity: MED
- Materiality: build-affecting
- Plan challenged: Task P.1.
- Evidence: `.cursor/plans/plan-note-routing-omissions.md:211`; `.cursor/plans/plan-pilot.md:1938`; `docs/testing/validation-harness.md:81`; `docs/pilot/findings-register.md:55-65`.
- Defect: P.1 directs F-001…F-058 to become resolved where the encounter’s omission disappears, although those rows cover several failure kinds. An encounter whose omission disappears but whose uncertainty, unsupported-line or material-wrong failure remains could have that separate finding incorrectly resolved.
- Concrete amendment: “Reconcile each existing row against run 2 using both Encounter and failure kind. Resolve an omission row only when its omission failure is gone; resolve uncertainty, unsupported-line and material-wrong rows only when their respective failure is gone. Otherwise retain the applicable control, with Control or fix and Closed populated according to the register contract.”
- /fix decision: Applied (verified: the register holds one row per failing encounter AND failure kind — `validation-harness.md:81`) — P.1 reconciles each row by Encounter and Category; an `omission` row resolves only when that encounter's silent omission is gone, the other kinds only when theirs is. Materiality verified: build-affecting.

**PR-MED-003 — Version and release ordering contradict the acceptance commit**
- Severity: MED
- Materiality: build-affecting
- Plan challenged: Config / Environment / Deployment Impact; Tasks 3.2, H4, H5 and P.1.
- Evidence: `.cursor/plans/plan-note-routing-omissions.md:143`, `:200`, `:207-211`; `scripts/build-release.py:163-168`; `desktop/tests/test_install_layout.py:867-882`.
- Defect: The overview places the version bump in the H5 commit and orders H5 before P.1, while H5 explicitly waits for P.1 and releases the H4 commit. Following the overview would leave the acceptance/release commit without the intended version or require releasing a different commit.
- Concrete amendment: “The authoritative order is Phase 1 → Phase 2 → Phase 3, including all six version strings → H1–H4 → practitioner P.1 on the H4 commit → H5 releasing that exact commit → P.2. H5 adds only the release record; it does not change the version. Any required code change after P.1 returns through hardening and a new acceptance run.”
- /fix decision: Applied (verified: the Config section put the version bump in the H5 commit while H5 waited for P.1 on the H4 commit) — the authoritative order is Phase 1 → 2 → 3 (all six version strings, Task 3.2) → H1–H4 → P.1 on the H4 commit → H5 releasing that exact commit (record only) → P.2; a post-P.1 code change re-runs hardening and acceptance. Materiality verified: build-affecting.

**PR-MED-004 — Route-nothing regression specifies an insufficient negative condition**
- Severity: MED
- Materiality: build-affecting
- Plan challenged: D3; Task 1.2.
- Evidence: `.cursor/plans/plan-note-routing-omissions.md:128-129`, `:188`; `desktop/src/scribe_desktop/validation.py:481-494`; `desktop/src/scribe_desktop/note_check.py:305-310`.
- Defect: “Without a structured-claim word” does not imply unwarned under D2: medications and clinician-name tokens are outside `is_structured_claim_word` but inside the proposed omission predicate. A medication-only fact therefore defeats the stated universal claim and is unsuitable as the proposed negative fixture.
- Concrete amendment: “The route-nothing-provider regression uses a material fact containing no token accepted by `_omission_flag_token` for that speaker. With no carriage or credited warning, it must remain silent and fail rule v1. Replace ‘every fact without a structured-claim word stays silent’ with ‘every omitted material fact without a credited omission-predicate token stays silent.’”
- /fix decision: Applied (verified: `_MEDICATION_LEXICON` and clinician name-like tokens are inside the proposed predicate and outside `is_structured_claim_word`, `validation.py:481-494`) — D3 and Task 1.2 now define the route-nothing fixture as a material fact carrying no token `_omission_flag_token` accepts for its speaker. Materiality verified: build-affecting.

**PR-LOW-005 — Goal overstates acknowledgement granularity**
- Severity: LOW
- Materiality: record-only
- Plan challenged: Goal, “What done looks like”; Accepted Assumptions.
- Evidence: `.cursor/plans/plan-note-routing-omissions.md:27`, `:81`, `:130`; `desktop/src/scribe_desktop/ui/note.py:2154-2158`; `desktop/src/scribe_desktop/ui/note_review.py:450-457`.
- Defect: The goal promises warnings cleared “line by line” and the assumption calls the existing control “per-line Acknowledge.” D4 deliberately preserves one acknowledgement for the entire warning code.
- Concrete amendment: “Replace both claims with ‘review the flagged lines, then acknowledge the omission-warning group.’ State that one per-code acknowledgement clears the group; individual line-resolution controls remain deferred.”
- /fix decision: Applied — the Goal and the Accepted Assumption now say the lines are reviewed and the warning GROUP acknowledged once per code (`ui/note.py:2154-2158`); per-line resolution stays deferred. Materiality verified: record-only.

**PR-LOW-006 — Deleting a shipped phrase is not always a routing no-op**
- Severity: LOW
- Materiality: record-only
- Plan challenged: D1; Codebase Integration Notes.
- Evidence: `.cursor/plans/plan-note-routing-omissions.md:85`, `:105`, `:127`; `desktop/src/scribe_desktop/note.py:1387-1393`.
- Defect: Removing a shipped phrase from the own layer can allow another own cue to win before fallback, or undo the cross-section override explicitly accepted at line 85. The shipped phrase remains available, but the winning section can change.
- Concrete amendment: “Deleting a phrase from the own file does not disable its shipped fallback. It may change the winning section when another own cue or a cross-section override competes.”
- /fix decision: Applied — D1 and the Codebase Integration Notes now say a deleted shipped phrase keeps its fallback but may change the winning section when another own cue or the cross-section override competes. Materiality verified: record-only.

**PR-LOW-007 — Replay documentation attributes section drift to the checker**
- Severity: LOW
- Materiality: record-only
- Plan challenged: Codebase Integration Notes; Task 3.1’s kept-recordings documentation amendment.
- Evidence: `.cursor/plans/plan-note-routing-omissions.md:109`, `:199`; `desktop/src/scribe_desktop/replay_kept.py:311-329`.
- Defect: The plan says “Sections missing” will move under D2, but replay computes it solely from generated and saved section presence. D2 changes checker warnings; with shipped defaults in both routing passes, D1 does not itself change the regenerated sections either.
- Concrete amendment: “Document that Check reviews may change under widened Check 4; Drift WER remains comparable. Sections missing is not expected to change from D2 or identical shipped-cue layering alone, and any observed change requires explanation.”
- /fix decision: Applied (verified: `replay_kept.note_drift` :311-329 builds the provider from the shipped config, where layering is a no-op) — "Check reviews" may change, "Sections missing" is not expected to, "Drift WER" comparable; Task 3.1's kept-recordings line matches. Materiality verified: record-only.

Coverage: PR-MED-001.
Practicality / feasibility / sequencing: PR-MED-003.
Unstated assumptions: PR-LOW-005, PR-LOW-006, PR-LOW-007.
Simpler / safer alternatives: PR-MED-001 — reuse existing rows and the plain-text label for missing locators.
Missing verification / rollback / migration: PR-MED-002, PR-MED-004.

### Round 2 - 2026-10-09 - note-routing-omissions plan, independent cross-family codex plan peer-review (round 2)
Source: Codex plan peer-review
Peer: codex gpt-6-astra medium, read-only sandbox
Scope: as above
Materiality: 2 build-affecting / 2 record-only / 0 invalid
Severity: 0 CRIT / 0 HIGH / 1 MED / 3 LOW
Round status: Closed (composer-recorded round — the peer's read-only sandbox cannot append; transcribed verbatim from `.cursor/loops/note-routing-peer-r2.log`; every finding verified against the code by the planning session and dispositioned below)

#### Findings

**PR-MED-008 — Coordination permits a version downgrade**
- Severity: MED
- Materiality: build-affecting
- Plan challenged: C10; D5; Task 3.2.
- Evidence: `.cursor/plans/plan-note-routing-omissions.md:131`, `:155`, `:278`; `desktop/tests/test_install_layout.py:867-882`.
- Defect: C10 permits either plan to land second, but Task 3.2 unconditionally sets 0.3.1. If ui-refresh 0.4.0 lands first, this task lowers the version; the equality test passes, and D5’s assertion that the already-landed 0.4.0 carries these changes is false.
- Concrete amendment: “Land note-routing-omissions 0.3.1 before ui-refresh 0.4.0. If 0.4.0 has already landed, revise the release version and acceptance/release sequence before Task 3.2; never reset main’s version to 0.3.1. Rebase overlapping behavior as well as line references.”
- /fix decision: Applied (verified: Task 3.2 set 0.3.1 unconditionally while C10 let either plan land second) — D5, C9 and C10 now say this plan lands before ui-refresh's 0.4.0 cut; if 0.4.0 has already landed, the practitioner re-decides the version by a dated note before Task 3.2 and the release sequence is renumbered; `main`'s version is never lowered; overlapping behaviour, not only line references, is rebased. Materiality verified: build-affecting.

**PR-LOW-009 — The matrix pin inventory prescribes an unjustified count change**
- Severity: LOW
- Materiality: build-affecting
- Plan challenged: Task 1.2.
- Evidence: `.cursor/plans/plan-note-routing-omissions.md:266`; `desktop/tests/test_note_matrix.py:464`, `:469-475`.
- Defect: Task 1.2 says to re-fixture `ex-small-talk :464`, but line 464 belongs to the preceding fixture. The actual small-talk fixture’s patient names remain outside D2’s patient predicate, and its clinician small-talk line gains no accepted token; neither widened Check 4 nor identical shipped-cue layering justifies changing its review count.
- Concrete amendment: “Keep `ex-small-talk` unchanged as a regression for patient names without structured tokens. Correct the fixture ID/line inventory, and change review-count expectations only where an added predicate class accepts an uncovered token.”
- /fix decision: Applied (verified: `test_note_matrix.py:469` is `ex-small-talk`; its patient line carries only a name-like token and its clinician line none the predicate accepts) — Task 1.2 keeps `ex-small-talk` unchanged as the regression for patient names without structured tokens, corrects the inventory (:469, :845, :867) and makes the two adversarial cells verified candidates rather than pre-declared count changes. Materiality verified: build-affecting.

**PR-LOW-010 — Version summaries omit the manifest edit**
- Severity: LOW
- Materiality: record-only
- Plan challenged: D5; C9.
- Evidence: `.cursor/plans/plan-note-routing-omissions.md:131`, `:154`, `:278`; `desktop/tests/test_install_layout.py:873-882`.
- Defect: D5 and C9 describe `npm version` followed by only the two Python edits, omitting the separately maintained manifest literal. Task 3.2 correctly includes it, so the implementation task is complete but the governing summaries disagree.
- Concrete amendment: “Use `npm version` for the package and lockfile strings, then edit `extension/src/manifest.ts` and both Python version strings.”
- /fix decision: Applied — D5 and C9 now name `extension/src/manifest.ts:29` beside `npm version` and the two Python strings, matching Task 3.2. Materiality verified: record-only.

**PR-LOW-011 — The accessor documentation retains the superseded routing contract**
- Severity: LOW
- Materiality: record-only
- Plan challenged: Task 3.1.
- Evidence: `desktop/src/scribe_desktop/note_config.py:884-889`; `.cursor/plans/plan-note-routing-omissions.md:277`.
- Defect: `normalised_cues()` explicitly says an absent section causes the provider to route nothing there. D1 invalidates that statement, but neither Task 3.1’s named module-docstring edits nor its prescribed search patterns capture it.
- Concrete amendment: “Include `normalised_cues()` in Task 3.1: an absent section has no own-layer cues, but the provider may route to it through shipped fallback cues.”
- /fix decision: Applied (verified: `note_config.py:884-889` says an absent section routes nothing) — Task 3.1 now includes the `normalised_cues()` docstring. Materiality verified: record-only.

Coverage: PR-LOW-011.
Practicality / feasibility / sequencing: PR-MED-008.
Unstated assumptions: PR-LOW-010.
Simpler / safer alternatives: no finding verified.
Missing verification / rollback / migration: PR-LOW-009.

### Round 3 - 2026-10-09 - note-routing-omissions plan, independent cross-family codex plan peer-review (round 3)
Source: Codex plan peer-review
Peer: codex gpt-6-astra medium, read-only sandbox
Scope: as above
Materiality: 0 build-affecting / 2 record-only / 0 invalid
Severity: 0 CRIT / 0 HIGH / 0 MED / 2 LOW
Round status: Closed (composer-recorded round — the peer's read-only sandbox cannot append; transcribed verbatim from `.cursor/loops/note-routing-peer-r3.log`; every finding verified against the code by the planning session and dispositioned below)

#### Findings

**PR-LOW-012 — Provider factory docstring retains the old routing contract**

- Severity: LOW
- Materiality: record-only
- Plan challenged: D1; Task 3.1.
- Evidence: `desktop/src/scribe_desktop/ui/models.py:2837-2840`; `.cursor/plans/plan-note-routing-omissions.md:330`.
- Defect: The factory docstring explicitly says routing uses the config’s own, digest-bound cues, “never the module defaults.” D1 invalidates that statement, but Task 3.1 neither names this docstring nor supplies search patterns that capture it.
- Concrete amendment: “Update `extractive_provider_from_config`’s docstring alongside Task 1.1: routing tries the resolved own cues first, then the shipped fallback; the config digest binds the own layer and the build binds the shipped layer.”
- /fix decision: Applied (verified: `ui/models.py:2837-2840` says "never the module defaults") — Task 1.1 now rewrites that docstring with the layering change (own cues first, shipped fallback; the digest binds the own layer, the build the shipped one). Materiality verified: record-only.

**PR-LOW-013 — Report-width description confuses metric cells with complete rows**

- Severity: LOW
- Materiality: record-only
- Plan challenged: Key Findings, harness entry; Task 1.2.
- Evidence: `.cursor/plans/plan-note-routing-omissions.md:98`, `:319`; `desktop/src/scribe_desktop/validation.py:1531-1535`, `:1548`, `:1566-1590`.
- Defect: The existing report has 20 complete table columns, of which 14 come from the metric-cell array. Adding the comparison column produces 21 complete columns and 15 metric cells; the plan’s “14 cells per row” description conflates those counts.
- Concrete amendment: “The metric-cell array grows from 14 to 15 entries; the complete report table grows from 20 to 21 columns. Keep the header, separator, measured and unmeasured rows, and totals aligned.”
- /fix decision: Applied (verified: `validation.py:1531-1535` is a 20-column table and :1548 a 14-entry metric-cell array) — Key Findings and Task 1.2 now say 14 → 15 metric cells and 20 → 21 columns, header, separator, unmeasured row and totals aligned. Materiality verified: record-only.

Coverage: PR-LOW-012.
Practicality / feasibility / sequencing: no finding verified.
Unstated assumptions: PR-LOW-013.
Simpler / safer alternatives: no finding verified.
Missing verification / rollback / migration: no finding verified.

## Tasks

### Phase 0 — Decisions (practitioner, 2026-10-09) — all taken
- [x] 🟩 **0.1 Layered cues** `[decision]` — Chosen: YES (2026-10-09, "go with recommended"); rationale: the practitioner's phrase wins, the shipped cues only rescue; the simulation's largest single gain (101 → 41 silent). Consequence accepted the same day at `/review-plan`: an emptied section routes again by the shipped cues (no per-section off switch in 0.3.1).
- [x] 🟩 **0.2 Does the harness count the widened Check 4?** `[decision]` — Chosen: (b) (2026-10-09); rationale: D3 — rule v1's lines unchanged, `warned` still needs the note's own warning, the predicate a pinned superset, the run-1 column kept beside it; under (a) about 25 silent omissions would remain and P.5 would stay blocked on a control that exists.
- [x] 🟩 **0.3 Install point** `[decision]` — Chosen (2026-10-09): before P.4's first eligible score if P.4 has not started, otherwise after its tenth; the build installed is the build of record current then (D5).

### Phase 1 — Routing, checker and the one harness change (`note.py`, `note_check.py`, `validation.py`, `ui/models.py`, `ui/note_review.py`)
- [ ] 🟥 **1.1 Layered routing.** `note.py`: a public `layered_section(cues, fallback_cues, tokens, section_keys, *, speaker, clinician_speaker, question) -> NoteSectionKey | None` = `first_matching_section` over `cues`, else over `fallback_cues` (D1, C5); `ExtractiveNoteProvider.__init__(cues=DEFAULT_SECTION_CUES, fallback_cues=DEFAULT_SECTION_CUES)` and `_route` calls `layered_section`; `provider_name` unchanged. `ui/models.extractive_provider_from_config` passes `fallback_cues=DEFAULT_SECTION_CUES` (:2843) and its docstring (:2837-2840, "never the module defaults") is rewritten in the same change: routing tries the resolved own cues first, then the shipped fallback; the config digest binds the own layer and the build binds the shipped layer (PR-LOW-012) — the harness and `replay_kept` inherit it (identity pin `test_validation_harness.py:559` holds). Export `layered_section` in `__all__`. Tests (`test_note.py`): own cue wins over a shipped cue in an earlier section (the "exercises"/"sore" case, clinician speaking → Advice, not Presenting complaint); an utterance no own cue routes takes the shipped cue's section; a patient's shipped diagnosis cue is still refused (ownership in pass 2); a question is refused in pass 2 as in pass 1; with no user file the provider's output EQUALS the single-cue provider's (by value — `normalised_cues()` of the shipped file vs `DEFAULT_SECTION_CUES`, never `is`); bare `ExtractiveNoteProvider()` unchanged (the 25 bare test sites need no edit). Done when: the tests pass and `test_note_matrix.py`'s faithful cells are unchanged (the matrix fixtures use the shipped cues both ways).
- [ ] 🟥 **1.2 Check 4 widened + the harness amendment — ONE commit.** `note_check.py`: `_omission_flag_token` exactly as D2; `omission_warnings` over every speaker's segments with `clinician=segment.speaker == note.clinician_speaker`, nothing with `note.clinician_speaker is None`; docstring :124-138 rewritten (patient speech now flags structured-claim words; names stay clinician-only; the stated limit kept — a heuristic, not a materiality classifier). `validation.py`: import `_omission_flag_token` (keep `_is_high_risk_token` imported for the run-1 column); `_WordInfo` gains `warned_v1`; `encounter_metrics` computes `warned` with the new predicate (clinician-ness from `segments[i].speaker == note.clinician_speaker`) and `warned_v1` with the old predicate AND the old clinician-only scope; `EncounterMetrics` gains `silent_omissions_v1` (the same rule over `warned_v1`); `render_report` adds the column `silent (run-1 predicate)` after `silent` — the metric-cell array 14 → 15 entries, the table 20 → 21 columns, the header, separator, the unmeasured `["-"] * N` row and the totals all aligned (PR-LOW-013); the rule reads `silent_omissions` only (C1). Tests: `test_note_check.py:1782-1790` becomes two cases — patient small talk WITHOUT a structured-claim word draws nothing; patient small talk with a side/negation/number draws one warning; the superset tests (C4: parametrised over `test_validation_metrics.py:225-226`'s structured-word list and over clinician-segment tokens); the route-nothing-provider test in `test_validation_metrics.py` (a provider returning no sections still fails rule v1 on a material fact none of whose tokens `_omission_flag_token` accepts for its speaker — no side, number, dose, unit, negation, medication, nor a name-like token on a clinician line — and `silent_omissions_v1 ≥ silent_omissions`); the hand case: a side-only omitted patient fact is `warned` and silent under the run-1 column; `test_validation_metrics.py:287-300` (`test_empty_note`) updated; `test_note_schema_v2.py:892` branch case still passes (its registry entry `note_check.py:omission_warnings` :956 unchanged); matrix review counts (`test_note_matrix.py`): `ex-small-talk` (:469) stays UNCHANGED — its patient line carries only a name-like token and its clinician line none the predicate accepts, so it is the regression for "patient names without structured tokens" (PR-LOW-009); `ab-over-omission` (:845) and `ab-malformed` (:867) are CANDIDATES whose expected review counts change only where an added predicate class accepts an uncovered token of their turns — verified cell by cell, never pre-declared (each cell keeps its CLASS); `test_save_as_ratification.py:340`; `test_validation_harness.py` report-shape pins if any. Done when: the suite is green and the report prints both columns.
- [ ] 🟥 **1.3 The learner under layering (D8).** `ui/note_review.consider_learning` (:405-425): the "already a cue" check stays over own cues; the dry-run `winner` comes from `note.layered_section(proposed, DEFAULT_SECTION_CUES, …)`; a third message when the shipped layer routes the line elsewhere today: "Today a built-in cue sends this line to <T>; your phrase will take it to <S>." Tests in `test_note_review.py`: the two existing messages unchanged; the new one. Done when: green.
- Phase 1 close: `ruff`, `mypy`, full `pytest`; the `/execute-loop` boundary review.

### Phase 2 — The review surface (`ui/models.py`, `ui/note.py`)
- [ ] 🟥 **2.1 Acknowledge-all excludes the omission warning (D4, C6).** `_acknowledge_all` skips `high_risk_omission`; the `acknowledge_all_button` is shown only when an unacknowledged review warning OTHER than it exists (:2161); its tooltip says so. The per-code Acknowledge row is unchanged. Tests: `test_ui_screens.py:5636-5657` and `:6714-6723` switch from `_acknowledge_all()` to the per-code `_acknowledge("high_risk_omission")`; a new case: Acknowledge-all with only an omission warning open leaves Save closed and the button hidden; with a mixed set it clears the others and leaves the omission open; Complete's `complete_block_reason` still names the unacknowledged warning.
- [ ] 🟥 **2.2 The chooser's mark and filter.** `models.eligible_utterances(document, *, clinician_speaker, in_note, flagged: Collection[int] = ())` — a flagged segment's label gets the suffix " — flagged: not in the note" (order unchanged; `UtteranceChoice` gains `flagged: bool`). `NoteScreen.eligible_utterances` passes the segment indexes of the note's `high_risk_omission` warnings (`self._note.note_warnings`; `()` before finalisation). In `edit_group`: `self.flagged_only_checkbox = QCheckBox("Show flagged lines only")` beside the Line row (never pre-ticked; cleared in `clear()`), and `self.flagged_count_label` (`QLabel`, PlainText): "N lines with a side, negation, number, dose, name or medication are not in the note." (hidden at 0). `_rebuild_edit_controls` filters the chooser when the box is ticked and keeps the current choice as today; ticking rebuilds. EVERY flagged segment stays locatable (PR-MED-001): the chooser excludes a segment a typed line REPLACED (`_segments_in_note` :1146-1152) although Check 4 credits no typed line, so such a segment can carry the warning and never appear in the chooser — therefore (i) the editable row of a replaced or routed line whose segment is flagged (partial coverage included) gets the same " — flagged: not in the note" suffix on its label (`editable_lines`), and (ii) the count label names, by transcript line number, every flagged segment the chooser does NOT offer ("…; also lines 7, 12 (replaced or partly in the note)") — never a duplicate Add. Tests: `test_ui_models.py` (suffix on flagged, none otherwise, order and `startswith` pins :1318-1321 untouched); `test_ui_screens.py` (the count label, the filter, the choice kept across a rebuild, `clear()` resets the box; `_eligible` :5076 unchanged; the typed-replacement case: replace a numbered line, the warning appears, its segment is absent from the chooser and named by the count label and marked on its row; the partial-coverage case likewise). C2: `test_shadow_exits.py` unchanged.
- [ ] 🟥 **2.3 Copy.** `ui/models.py:2139-2144` as D4 (keeps "a line you removed" — `test_ui_models.py:1384`). Done when: green.
- Phase 2 close: the loop's boundary review; the practitioner's optional developer-build look at the Note tab (no clinical content: the `_NOTE_TURNS`-style mock).

### Phase 3 — Documents and version (D5, D6)
- [ ] 🟥 **3.1 Documents.** `docs/testing/validation-harness.md`: :73 ("replaces the shipped cues as a whole" → for the harness's config folder; routing layers the shipped cues under it since 0.3.1); :54 and :58 the metric amendment paragraph (dated, (b), the superset and route-nothing pins, both columns' meaning); :94 the Known-limits bullet rewritten (what is now placed or flagged; the `syn-48`-shaped residue; the six next-patient encounters). `docs/security/threat-model.md:476-500` (Check 4's scope and classes; the Note-tab residue for the next patient; "what routed this note" = config digest + app version). `docs/design-system.md:54-56` (Check 4) and :326 (the two-button acknowledgement rule). `note_config.py:35-39, 59-63` docstring (file replacement vs routing layering) and the `normalised_cues()` docstring (:884-889) — an absent section has no own-layer cues, but the provider may still route to it through the shipped fallback (PR-LOW-011). `docs/security/data-flow-map.md:432` (one clause). `docs/testing/kept-recordings.md:35-40` ("Check reviews" may change from 0.3.1 under the widened Check 4; "Drift WER" comparable; "Sections missing" not expected to change — a change needs an explanation). `docs/testing/shipping-gate.md:44` unchanged (provider name kept). Dated amendment lines (no Done-block edits): `plan-phase3a-note-pipeline.md` Task 5.4 (:1294), `plan-practitioner-profile.md` D6 (:149), `plan-pilot.md:998` and its Task P.3 ("routing fix planned" → this plan), `plan-clinic-smoke.md` (its P.3 pointer). `CHANGELOG.md` "Version 0.3.1" bullet under `[Unreleased]`; `PLAN.md` Phase 7 note; `AGENTS.md` Current Status (after P.2: "0.3.1 installed"). Done when: `test_pilot_docs.py` green and every statement of the OLD contract found by `grep -rn "as a whole\|clinician-attributed\|numbers, names, medications"` over `docs/` and `desktop/src` is reconciled or deliberately kept (the sweep is recorded on the task).
- [ ] 🟥 **3.2 Version 0.3.1 (C9).** `cd extension && npm version 0.3.1 --no-git-tag-version` (updates `package.json:4` and `package-lock.json:3,9`), then by hand `extension/src/manifest.ts:29` (a literal, not derived — verified 2026-10-09), `desktop/pyproject.toml:7`, `desktop/src/scribe_desktop/__init__.py:3`; `test_install_layout.py:867-882` green; `npm run qa`. Done when: all six strings read 0.3.1.
- Phase 3 close: the loop's boundary review (documents).

### Hardening stage
- [ ] 🟥 **H1** `/review-loop` to convergence over Phases 1–3 (whole-stage sweep: the predicate's composition, the two-pass precedence, the report columns, the pins).
- [ ] 🟥 **H2** `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`.
- [ ] 🟥 **H3** `/security-review` — the threat model's Phase 3A and pilot sections against the diff (patient-segment warnings carry coordinates only; nothing new in logs or the audit row; C8).
- [ ] 🟥 **H4** cross-family `/peer-review` (codex `gpt-6-astra`) to convergence; the H4 commit is run 2's run-of-record commit.
- [ ] 🟥 **H5** 0.3.1 built of record: after P.1 has run on the H4 commit, the `Release` workflow on THAT commit (the version strings already read 0.3.1 from Task 3.2; H5 changes nothing in code), `gh attestation verify`, the `docs/release/pilot-builds.md` row ("no schema change; a 0.3.0 reinstall reads everything"), CI green. Done when: the row is committed. If P.1 forces a code change, H1–H4 and P.1 run again before H5.

### Phase P — Practitioner (normal terminal; C7)
- [ ] 🟥 **P.1 Run 2 of the validation harness — THE acceptance check (D7).** From a clean, committed checkout at the H4 commit, developer build, installed app closed, `docs/pilot/README.md` step 3 as for run 1: list the voices (baseline unchanged), build the 50 scripts into an empty set folder outside the repository, run with `--rule validation\rules\option-a-proposed.json`, keep the report. Record under "rule v1 as amended 2026-10-09" in `validation-harness.md` "Runs of record" and pilot Task P.3: both silent columns, the totals, the commit, the manifest hash, the voices, the cue file's blob (unchanged `c7f7b53…`), the rule's blob (unchanged `ec6c38d…`), PASS/FAIL as reported. Acceptance: silent ≤ 1 (`syn-48` only), no new unexpected checker failure; the six next-patient encounters and run 1's non-routing failures each a register row (`open` or `controlled`, category per kind, Part of the app `note-routing`/`transcription`/`checker`, Stage `validation`). F-001…F-058 (one row per failing ENCOUNTER AND FAILURE KIND — PR-MED-002): reconcile each row by its Encounter and its Category — an `omission` row becomes `resolved` (Control-or-fix "0.3.1 (commit <H4 short hash>)", Closed 2026-10) only when run 2 shows THAT encounter's silent omission gone; an `uncertainty`, `unsupported` or `quality` (material wrong) row only when ITS failure kind is gone; every other row keeps its `controlled` control as recorded. Delete the set folder; check `%TEMP%` for `scribe-speaker-eval-*`. Done when: both records are committed in one commit and the register's test is green. A result outside D7's residue list is a finding for H1, never a rule change (C1).
- [ ] 🟥 **P.2 Install and smoke (decision 0.3, D5).** Verify and install the build of record current at the install point; reload the extension; restart Chrome; D15's "before" hash paste AFTER this install if P.4 has not started. Smoke on one mock shadow consultation (no patient): the warning row with its count; "Acknowledge all" leaves it and Save closed; the tick filters the chooser to the flagged lines; the per-code Acknowledge clears it; Status tab version; the audit CSV's `app_version`. Record the flagged-line COUNT of the smoke in the off-repository pilot log (D9) as the fatigue baseline. Done when: the smoke line is on this task and AGENTS.md says which build is installed.

## Retained Follow-Up Items
- N/A until completion.

## Follow-Up Continuation Notes
- First: whichever of the deferred items run 2 or P.5 makes real — carry-over, new-patient detection, the non-routing failure kinds — each planned from the then-current numbers, never from this plan's simulation alone.
- Out of scope for any follow-up here: rule v1, the cue file, the scripts (C1).
- Still applies: D1 (two passes, own first), D2/D3 (any predicate change is a dated metric amendment with both columns kept), D4 (the omission warning is never cleared by Acknowledge-all), D9.
- Do not rediscover: the version is six strings in five files via `npm version`; `test_shadow_exits.py` counts text widgets only; the chooser pins use `startswith` and transcript order; `config_digest` does not cover the shipped cues.

---
*Plan saved to: .cursor/plans/plan-note-routing-omissions.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
