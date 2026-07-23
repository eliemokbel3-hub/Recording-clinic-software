---
name: review-loop
description: Drive /review, /fix, and re-review in a loop to convergence within bounded safety gates. Auto-cycles Fix-now findings but pauses at the Deferral Confirmation Gate, /fix stop-on-failure, CRIT/HIGH scope-expansion hard-stops, and a max-round cap (default 3). Shared Cursor/Codex/Claude Code workflow; invoke as /review-loop in Cursor or Claude Code, or $review-loop in Codex. Side-effecting; explicit invocation only.
disable-model-invocation: true
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/review-loop` in Cursor or Claude Code, or `$review-loop` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

This workflow is side-effecting. Cursor uses `disable-model-invocation: true`; Codex uses `agents/openai.yaml` with `policy.allow_implicit_invocation: false`; both require explicit user invocation.

This workflow reads and writes the same `.cursor/plans/` files as Cursor and Claude Code, so no copy-paste handoff is needed when switching tools.

`/review-loop` is an orchestrator: it drives the existing `/review` and
`/fix` workflows in a loop to convergence. It introduces NO new review
logic and NO new fix logic of its own — every finding is produced by
`/review` and every code change is applied by `/fix`, with all of their
gates, scope-locking, pattern-sibling propagation, and verification
intact. `/review-loop` only decides when to run the next round and when
to stop.

## What it does

Run `/review` → `/fix` → re-`/review` repeatedly on the work in scope
until the review converges or a stop condition fires. The work in scope
is whatever `/review` would review — the active plan's changed-files
baseline, or the working-tree changes if no plan is in scope.

The loop is **semi-autonomous**: it automates the round-to-round cycle
for `Fix-now` findings so the user does not have to re-issue `/review`
and `/fix` by hand, but it never bypasses an interactive safety gate.
"Loops until cleared" means it automates the cycle, not that it skips
the gates.

## Before starting

A saved plan with a `Review Findings Log` is strongly recommended: the
loop reads `Review History` to count rounds and detect `skew=`, and
`/fix` reads the Findings Log to know what to apply. Without a plan,
round tracking is conversation-only — keep the cap at 1–2 rounds and
tell the user the loop cannot track `skew` across sessions.

State the active max-round cap at the start of the run.

## Safety gates — the loop PAUSES, it never bypasses

`/review-loop` stops and hands control back to the user at every one of
these. It must never auto-resolve them. (Under a headless/loop invocation
— e.g. driven by `/execute-loop` — the composed `/review` and `/fix` gates
apply their headless AUTO-DISPOSABLE branch: LOW/MED, non-production,
do-the-work candidates are applied and logged, while every MUST-PAUSE case
still surfaces. This applies wherever this skill says the loop "pauses" at
a Deferral gate — that phrasing describes the interactive path.)

1. **Deferral Confirmation Gate.** When `/review` or `/fix` surfaces a
   `Defer` / `Accept` candidate (or a MED/LOW scope-expansion
   candidate), the loop pauses for the user's gate disposition exactly
   as the underlying workflow defines it. Interactively, only `Fix-now` /
   `Fix-now-if-tied` findings flow through automatically; under a
   headless/loop invocation the composed gate's AUTO-DISPOSABLE branch
   also auto-applies + logs LOW/MED, non-production, do-the-work
   candidates (e.g. `Include in plan`), while `Defer` / `Accept` and
   other MUST-PAUSE cases still surface.
2. **`/fix` stop-on-failure.** If `/fix` hits a verification failure or
   a fix-introduced issue, it stops mid-round per its own contract. The
   loop does not start another round over the failure — it surfaces the
   failure and waits.
3. **CRIT/HIGH scope-expansion hard-stops.** Any CRIT or HIGH
   scope-expansion finding requires the explicit user disposition that
   `/review` mandates before the loop continues.
4. **Max-round cap.** The loop runs at most N rounds (default N = 3).
   On reaching the cap it stops and reports, even if findings remain.

If any gate is open, the loop is paused — not failed. It resumes only
on the user's reply.

## The loop

Each round is one `/review` followed by one `/fix`, then a termination
check. Start at round 1 with the active cap (default 3).

1. **Run `/review`** for this round on the work in scope — the full
   workflow (all finding-producing passes, the Finding Verification
   filter, Round Classification, Scope-Expansion Triage, and the append
   to the plan's `Review Findings Log`). `/review`'s own Deferral
   Confirmation Gate fires here for any `Defer` / `Accept` / MED-LOW
   scope-expansion candidate, and CRIT/HIGH scope-expansion findings
   hard-stop for an explicit disposition — the loop pauses for both
   (interactive path; headless, `/review`'s gate auto-applies + logs
   AUTO-DISPOSABLE candidates and pauses only MUST-PAUSE cases).
   **Integrity check (plan-tracked runs):** assert that this round's
   `/review` appended a NEW parseable `Review History` line — the
   `X CRIT / X HIGH / X MED / X LOW` counts, `skew=`, and `action=`
   must be readable. If the line is absent or unparseable, STOP the
   loop and surface it — a silent append failure otherwise disables
   skew and escalation detection. Report the check result each round
   (e.g. "Review History integrity: OK") so an orchestrating composer
   can verify it ran; the assertion itself runs in every plan-tracked
   `/review-loop`, standalone or orchestrated. On a no-plan run
   (conversation-only tracking, see Before starting) there is no
   `Review History` to assert against — skip the check.

   **`ROLE:` line (loop-log context only):** on runs with a loop-log
   context — an `.cursor/loops/` run in progress or a user-named run
   key — append one per-round `ROLE: round` line for the round's
   reviewing model/backend to the run's loop logs (e.g.
   `ROLE: round ts=<iso> run=<runkey> role=reviewer
   backend=<live-session|...> model="<slug>" round=<N>`); shape and
   writer contract per `/execute-loop`'s Visibility + run-state
   section (the canonical `ROLE:` definition). Standalone runs with
   no loop-log context skip it — the plan's `Review History` already
   records rounds.

2. **If this round's `/review` found zero actionable findings**, the
   loop is converged — go to **Convergence actions** and stop.

3. **Run `/fix`** on this round's `Fix-now` / `Fix-now-if-tied`
   findings, one at a time, with `/fix`'s stop-on-failure and
   per-finding verification. `/fix`'s Step 1.5 Deferral Confirmation
   Gate fires for any skip candidate — the loop pauses for it on the
   interactive path (headless, `/fix`'s gate auto-disposes AUTO-DISPOSABLE
   candidates and pauses only MUST-PAUSE cases). If `/fix`
   stops on a verification failure, the loop pauses there.

4. **Termination check** (after the fix):
   - **Converged → stop, success.** If this round's `/review` found no
     CRIT, HIGH, or MED findings — and, on round 2+, Round
     Classification shows convergence (findings mostly 🆕 LOWs) — the
     loop is done, even if some LOWs were Accepted or Deferred at the
     gate. The Fix-now LOWs were just applied in step 3; do not start
     another round chasing the remaining LOWs. Go to **Convergence
     actions**.
   - **Fix-induced skew → stop, escalate.** If `skew=fix-induced`
     (`action=escalate`), stop and recommend a premium model before any
     further rounds — the executor is introducing regressions, so more
     same-model rounds burn tokens without converging. See **Model
     escalation**.
   - **Cap reached → stop, report.** If this was round N (the cap), stop
     and report the remaining findings; offer to raise the cap for one
     more round or to escalate the model.
   - **Otherwise → next round.** Increment the round counter and return
     to step 1. The next `/review`'s Post-Fix Regression Check and Round
     Classification verify this round's fixes and catch any regressions
     they introduced.

## Round cap (default 3, overridable)

The default max-round cap is **3**. The user may override it per
invocation (e.g. "`/review-loop` max 5", or "one round only"). A cap of
1 makes `/review-loop` a single `/review` + `/fix` pass with a
termination check — still useful, but no auto-looping. Never silently
exceed the cap; reaching it is a stop condition, not a failure.

## Convergence actions (on successful termination)

When the loop terminates converged, before declaring done:
- Report the rounds run and the final `Review History` line.
- **Cross-family peer pass (recommended by default).** After every
  `/review-loop` convergence, recommend a final cross-MODEL-family peer
  pass by default — offer to chain into the full `/peer-loop`
  (`$peer-loop` in Codex), the automated cross-family peer-review loop
  (headless cross-family peer → executor verifies → `/fix` → fresh peer,
  to convergence), as the primary option; a single one-shot
  `/peer-review` (`$peer-review` in Codex) stays available as the
  lighter-touch alternative. Accepting `/peer-loop` flows review → fix →
  cross-family peer-loop end-to-end from this one `/review-loop`
  invocation. It is default-on because a "clean" same-family review
  often misses HIGH/MED issues a cross-family peer catches; it is
  explicitly skippable for genuinely trivial changes (one-liners,
  comment- or format-only edits) where the peer cost is not worth it.
  Separately, if the tool supports parallel subagents, also offer the
  `/review` "Parallel independent review (where supported)" subagent
  pass — but subagents add lens diversity, not model diversity, so they
  do not substitute for the cross-family peer pass that catches the
  blind spots the looping session shares.
- **Menu-selection consent (locked skills):** the offer above chains
  into the locked, explicit-invocation-only `/peer-loop`. A user's
  explicit acceptance of that offered option COUNTS as explicit
  invocation: on acceptance, read `/peer-loop`'s skill file from disk
  and follow it verbatim. The lock still bars model-INITIATED
  invocation — no acceptance, no invocation (the explicit skip for
  genuinely trivial changes above is unchanged); the offer always
  prints the literal slash command; frontmatter and `agents/openai.yaml`
  policies are unchanged by this rule.
- Remind the user to run the project's test suite or build command —
  static review and per-fix verification cannot catch everything.

## Model escalation

On `skew=fix-induced` / `action=escalate`, or after two failed `/fix`
verification attempts on the same finding:
- **In Cursor:** recommend switching to a premium model before the next
  round; do not keep looping on the model that produced the
  regressions.
- **In Codex or Claude Code:** the loop runs on whichever model the CLI
  or IDE extension is configured for. Suggest `/model` to switch to a
  higher-tier model if available, or switching to Claude Code / Cursor
  for a fresh attempt. Do not try to detect the active model yourself —
  the user is the source of truth.

## What `/review-loop` does NOT do

- bypass a MUST-PAUSE gate — `Defer` / `Accept` deferrals, `/fix`
  stop-on-failure, or CRIT/HIGH scope-expansion hard-stops — these always
  pause for the user (interactive and headless alike; the headless
  AUTO-DISPOSABLE branch only auto-flows LOW/MED, non-production,
  do-the-work candidates)
- invent findings or fixes of its own — `/review` and `/fix` own that,
  with all their existing discipline
- loop past the max-round cap, or past a `skew=fix-induced` stop,
  without explicit user direction
- auto-apply `Defer` / `Accept` findings — those are gated like any
  other skip candidate
- replace `/peer-review` — cross-model-family review is a separate,
  recommended pass, not something the loop performs itself
