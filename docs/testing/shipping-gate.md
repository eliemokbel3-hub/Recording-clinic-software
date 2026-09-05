# Shipping gate (Task 9.1) — rubric v1, ratified 2026-09-05

**Status: RATIFIED — rubric v1, 2026-09-05.** Drafted as Phase 3A Task 9.1a (2026-09-04); the practitioner ratified the proposed composition, rubric and pass rule UNCHANGED on 2026-09-05 (in session: "use suggested rules"), before any scoring. The numbers below are frozen for this run and are never adjusted after; a different rule would be a new rubric version, decided before its own run. This page carries no transcript or note text, and neither does the scoring sheet: scores are counts and yes/no only.

How the practitioner decides whether copy-to-Cliniko may be switched on for the Phase 3A extractive note pipeline, using the app itself as the instrument. Code: the recorded decision is `COPY_TO_CLINIKO_ENABLED` in `desktop/src/scribe_desktop/ui/models.py` (a bare `Final[bool]`, `False` today); the Note tab binds its copy affordance to it in `desktop/src/scribe_desktop/ui/note.py` (`_copy_ready`, `_apply_copy_binding`); the wiring is pinned under both outcomes in `desktop/tests/test_ui_screens.py` (`TestNoteWiring`, `TestNoteScreen`). What the sheet holds and how a decision is applied are below.

## What the gate decides

Copy-to-Cliniko enablement, and only that. It is separate from Task 9.2's completion gate (CI, the global properties, the end-to-end synthetic run), which does not depend on this outcome. A **pass** flips the flag to `True`. A **fail** leaves it `False`, copy stays off, and Phase 3A is classified honestly as internal infrastructure until Phase 3B (the local `gpt-oss-20b` note model) lands and passes a gate of its own — this rubric is drafted so it can be re-used there, but that is 3B's decision, not this page's. Either outcome is a recorded decision, not a build.

What the flag controls today, exactly as `ui/note.py` enforces it and the tests pin it: with the flag `False` the Copy button is hidden and disabled and the note body is display-only (`NoTextInteraction`) whatever the review state. With the flag `True` the button is shown but stays disabled, and the note body stays display-only, until the note is fully ratified — every proposal confirmed or declined, no blocking error, every review warning acknowledged, and the note saved — the same predicate that gates Complete (`models.complete_block_reason`), re-checked at click time. The transcript panel is display-only under both. The flag never widens what is copyable beyond the single ratified note on the Note tab.

## Preparing the transcript set

The app is the instrument: each consultation is recorded LIVE through the app as an ordinary session (Session screen: Start, Finish), transcribed locally at Finish, and generated from the Transcript screen. No import path exists and none is built, so a stored transcript or an external recording cannot be scored here.

Each consultation is MOCK (the practitioner acting both roles, as at the Phase 2 completion gate) — the ratified default — unless the practitioner expressly substitutes a consented recording for a given consultation. Retention is the app's own: the session's audio, transcript and note live under its session key and are destroyed cryptographically at Complete or Discard. A live session awaiting review is sweep-exempt, so the practitioner's Complete or Discard is what ends it; a session left behind — the app closed or crashed before Complete or Discard — becomes an unprotected recovery store, expiry-eligible at 24 h from its creation and destroyed by the next successful sweep: an eligibility bound, not a deadline (`docs/security/retention-schedule.md`). A set kept for re-use at Phase 3B's gate must be mock and falls under the Task 2.3 retention decision, still open in the plan.

Composition — ratified 2026-09-05 (rubric v1):

- 10 consultations (8 to 12 accepted) spanning new-patient and follow-up encounters.
- At least three body regions, each with one prefill seed in the practitioner's config, so prefill is exercised once per region. The run's config (three prefills, one trigger) is kept in `docs/testing/shipping-gate-config/`, with install steps in its README.
- Every axis of `PLAN.md`'s AI-quality list that the extractive path can express, at least once: negation and changing symptoms; left/right and anatomical-region distinctions; numbers, dates, medications, doses and measurements; small talk and unrelated conversation; uncertain speech and a contradictory statement; an apparent end-of-consultation and a new-patient greeting. The list's two remaining axes are not this gate's: overlapping speakers, background noise and accents are transcription properties (Phase 2's gate and Task 2.3), and a spoken prompt-injection attempt is only more transcript to the extractive provider — anything it extracts from one is scored as noise under R3 — so the axis proper, instruction-following, returns with Phase 3B's model.
- One consultation whose autofill trigger phrase is spoken by the clinician and one where only the patient speaks it. Matching is speaker-agnostic and both routes produce proposals only (`note_fill.py`); the scorer records what the proposals were worth (R5); that nothing reaches a saved note unconfirmed is held by the structure — Save is disabled while a proposal is pending — not by the rubric.
- One consultation where the clinician role must be corrected from the preselection: the "(suggested)" radio on the Transcript screen is the wrong speaker and the other is chosen.
- One three-speaker consultation — the D-S1 scenario Task 2.3 measures (a parent, carer or interpreter present). Same scenario, not the same file: this set is recorded through the app, whose audio is destroyed at Complete or Discard, while Task 2.3 takes WAV files with label tracks, so the scenario is acted again for Task 2.3 (or captured in parallel by an external recorder — the practitioner's choice, and then the Task 2.3 retention decision applies to that recording).

Give the set an id and each consultation an id (`C01`, `C02`, …) before scoring. Ids are the only reference the sheet carries.

## Running it

Per consultation, in the app (launched as `AGENTS.md`'s Local Run Steps say — never from an ephemeral terminal):

1. Record: Session screen, Start, act the consultation, Finish. Transcription runs locally at Finish and the Transcript screen opens with the transcript.
2. Confirm the clinician role (correcting the preselection where the set says so) and the template profile; choose the prefill region if one is offered. Generate is disabled until role and profile are confirmed.
3. Generate. The Note tab opens with the draft beside the full uncertainty-marked transcript.
4. Decide every proposal and acknowledge every warning, then score R1–R6 on the sheet from the Note tab at that ONE point — after the last decision and acknowledgement, before Save, Cancel or Complete. The point matters: confirming or declining a proposal re-finalises the note (`ui/note.py` `_refinalise`), so the assertions being counted change until the last decision is made, and R1–R5 scored earlier would not be reproducible. Score before leaving the review: the tab's plaintext is cleared whenever the review ends — Complete or Discard, "Cancel review and regenerate", a new transcript, a new generation — and an accepted window close ends the process (`ui/main_window.py` `closeEvent` refuses to close while a review is busy and calls no separate tab-clear); a crash leaves only the encrypted recovery store. A regeneration discards the consultation's row: score the new draft afresh. Timing for R6 starts at Generate and stops at the same scoring point — when every proposal is decided and every warning acknowledged.
5. Leave the review. Three exits exist: Save (the note is written under the session key, for a session that will be completed), "Cancel review and regenerate" (drops the draft, keeps the transcript and key), and "Delete note and complete without one". Discard is unavailable while a draft is under review, so a mock session is ended by Cancel and then Discard on the Transcript screen; a consented session that is kept ends in Complete. Mock sessions end in Discard.

The sheet is the Task 9.1 scoring table in the plan (`.cursor/plans/plan-phase3a-note-pipeline.md`: an empty skeleton sits under Task 9.1 and is filled in at the run): one row per consultation carrying the R1, R2, R3 and R5 numerators and denominators separately (the pass rule sums each over the set), the R4 count, and the R6 yes/no and minutes; a totals row; and a decision line — date, rubric version, set id, pass or fail — so the result can be recomputed from the sheet alone. Counts and yes/no only; never a transcript or note line, a name, or a quote.

## What is measured

Scored per note during review, as counts and yes/no only, at the one scoring point step 4 of "Running it" defines — after every proposal is decided and every warning acknowledged, before Save — so R1–R5 count the same note for every scorer. An "assertion" is one bullet of the note (the Note tab renders one bullet per assertion, never assembled prose), so counts are unambiguous.

- **R1 routing** = assertions in the right canonical section / assertions in the note.
- **R2 coverage** = clinically material spoken items present in the note / material items spoken, tallied from the transcript panel beside the note.
- **R3 noise** = assertions that must be deleted / assertions in the note.
- **R4 safety** = items surviving review that are wrong-side, wrong-dose, negation-flipped, or patient speculation in a clinician-owned section (assessment, diagnosis, advice and home exercise, management plan). Expected 0. "Surviving" means what the practitioner would have signed after review: a difference the checker flagged and the practitioner corrected does not count; one the checker missed, or one the practitioner acknowledged without correcting, does.
- **R5 accelerators** = proposals confirmed / proposals offered (autofill and prefill together).
- **R6 net effort** = "faster than writing this note from scratch?" yes/no, plus minutes to review.

Nothing in the app computes any of these; the practitioner tallies them by hand against the transcript panel, and the app records nothing about the scoring.

Pass rule — ratified 2026-09-05 (rubric v1):

- R4 = 0 on every note: one breach fails the gate outright.
- R6 = yes on a majority of notes.
- R1 ≥ 80 % and R3 ≤ 20 %, each over the set's totals (the sum of numerators over the sum of denominators), not averaged per note.
- R2 and R5 are recorded, not thresholded: R2 bounds what an extractive provider can reach and is the comparison baseline for Phase 3B's model; R5 measures the practitioner's config rather than the provider.

These thresholds were ratified on 2026-09-05, before any scoring, and are never adjusted after; changing them means a new rubric version and a new run.

## Custody

The run stays inside ordinary session custody: every consultation is a normal app session under its own encrypted store, and Complete or Discard destroys it as for any session, so this gate adds no row to `docs/security/retention-schedule.md`. The only artefacts that outlive a session are the sheet's numbers and the decision line, neither of which carries clinical content. Anything the practitioner keeps outside the app for re-use — a mock consultation captured by an external recorder — is not the app's custody and falls under the Task 2.3 retention decision.

## What a decision flips

The checklist is DERIVED at flip time, never copied from a list — case-insensitive, because the plan's own `Validation / Verification` line and its Task 9.1 heading capitalise the phrase:

```bash
grep -rn -i -E 'COPY_TO_CLINIKO_ENABLED|ships DISABLED|shipping gate' desktop/src desktop/tests docs PLAN.md AGENTS.md CHANGELOG.md .cursor/plans/plan-phase3a-note-pipeline.md
```

Today's hits, as EXAMPLES only — the grep is the authority: the flag and its comment in `desktop/src/scribe_desktop/ui/models.py` (and its `__all__` entry); the call-time read in `ui/main_window.py` (`_on_draft_ready`); the `ui/note.py` module docstring and `begin_review`'s default; the shipped-state pin `test_default_copy_binding_ships_disabled` in `desktop/tests/test_ui_screens.py` and the gate-naming docstrings in `desktop/tests/test_note_pipeline.py`; the "ships DISABLED" statements in `docs/design-system.md`, `docs/security/threat-model.md`, `docs/security/data-flow-map.md`, `PLAN.md`, `AGENTS.md`, `CHANGELOG.md`; the plan's Accepted Assumption on cue matching and its `Validation / Verification` shipping-gate line; and this page.

A **pass** flips `COPY_TO_CLINIKO_ENABLED` to `True`, records the decision date, set id and rubric version in the comment above it, changes the one `is False` assertion in `test_default_copy_binding_ships_disabled` to `is True` — the decision-agnostic pin `test_default_copy_binding_equals_the_recorded_flag` and both `TestNoteWiring` outcome tests need no edit — and reconciles every site the grep lists. A **fail** leaves the flag `False` and records the dated fail at the same sites. Both are applied through `/execute` of Task 9.1; neither is a build.
