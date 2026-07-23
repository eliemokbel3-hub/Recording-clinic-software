---
name: fix
description: Apply review findings one at a time, with re-read, verification, and stop-on-failure between each fix. Use after /review. Shared Cursor/Codex/Claude Code workflow; invoke as /fix in Cursor or Claude Code, or $fix in Codex. Side-effecting.
disable-model-invocation: false
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/fix` in Cursor or Claude Code, or `$fix` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

This workflow is side-effecting but agent-invocable: Cursor uses `disable-model-invocation: false` and Codex uses `agents/openai.yaml` with `policy.allow_implicit_invocation: true`, so an agent may invoke it automatically (for example inside a loop) and you can still invoke it explicitly. Safety comes from this workflow's in-skill gates rather than from invocation-locking.

This workflow reads and writes the same `.cursor/plans/` files as Cursor and Claude Code, so no copy-paste handoff is needed when switching tools.

Please apply findings from the most recent /review output.

## Step 0 — Identify the review baseline

Look for findings to apply in this order:

1. **Findings Log preferred.** Check the plan file's `Review Findings
   Log` section for any round whose Round status is `Open (X pending)`
   — i.e., at least one finding has `/fix decision: Pending` —
   EXCLUDING any round whose `Source:` ends in `plan peer-review`
   (`Cursor plan peer-review` / `Claude Code plan peer-review` /
   `Codex plan peer-review`): those rounds are plan-scoped — the
   owning planning session applies them as `/review-plan`-style plan
   amendments, and `/fix` never ingests them. If the only open
   round(s) are plan-review-sourced, say so and point to the planning
   route instead of selecting one. If exactly one eligible round
   exists, use it. If multiple, ask the user which round to apply.

2. **Conversation fallback.** If no plan file is in scope, the
   Findings Log doesn't exist, or the most recent round in the Log
   is fully applied but a /review output is visible in the current
   conversation, use the conversation output. Before processing,
   write the findings into the Findings Log (creating the section if
   missing) so /fix can update per-finding state durably.

3. **Paste fallback.** If neither source is available, stop and ask
   the user to paste a /review output or run /review first.

If the round being applied (from the Findings Log or pasted) has an
`action=escalate` entry in `Review History`, recommend escalating to
a premium model before proceeding. Do not start fixing on the model
that produced the fix-induced regressions.

**Peer-review rounds — verify findings before applying when outside
the live loop.** When the selected round's `Source:` is peer-review-
sourced (`Cursor peer-review`, `Claude Code peer-review`, or `Codex
peer-review` — this is the detectable discriminator; the Findings Log
records `Source:`, not whether a live executor already verified the
findings, so do NOT gate on an unobservable "no live executor
session"), decide whether this session must re-verify the findings
against the code before applying:

- **Live `/peer-loop` executor** — if this `/fix` was invoked in-loop
  by `/peer-loop` in the same live session that already verified the
  peer's findings against the code (or the user confirms this is that
  session), proceed straight to Step 1 with the normal flow; the
  in-session verification already happened.
- **Fresh or ambiguous invocation** — if `/fix` was invoked standalone
  (a new chat, a different day, a different machine) or it is unclear,
  ask once: `This round is peer-review-sourced. Is this the live
  /peer-loop executor that already verified these findings, or should I
  verify each finding against the code first? (verified / verify-now)`.
  If the user answers `verified`, proceed normally; otherwise (the
  default) run the verify-peer-findings fallback below.

Verify-peer-findings fallback: before Step 2 application, re-read the
cited `file:line` for each peer finding and confirm the described issue
is real in the current code, dropping or downgrading any that do not
hold — this substitutes for the live executor's session-memory check
that catches peer-review false positives. Then apply the surviving
findings through the normal Step 1 → Step 2 flow. This is a pre-apply
screen, not a replacement for Step 2's per-fix verification.

## Step 1 — Confirm scope and order
Use the review's Recommended Fix Order if present.

For each finding, confirm the Fix route field:
- premium-only → if the active model is fast/medium, hard-stop and ask
  the user to confirm a premium model is loaded before proceeding
- fix-on-fast → current model is fine
- defer → skip candidate; route through Step 1.5 Deferral Confirmation
  Gate before honouring the skip, then ensure the confirmed deferral
  lands in the plan's Deferred section
- accept → skip candidate; route through Step 1.5 Deferral
  Confirmation Gate before honouring the skip. Once confirmed, add to
  CHANGELOG only if it represents a user-visible behaviour change, an
  API or deployment trade-off, a security-relevant decision, or an
  explicit product decision. For internal style or code-smell LOWs,
  do not touch CHANGELOG — leave the LOW in the review output and the
  plan's triage record.

`fix-on-fast` is a routing decision for /fix only. It is NOT a plan
task label.

Apply the LOW triage from /review:
- LOWs default to Fix-now; apply them like any other Fix-now finding.
  Only LOWs the user confirmed for Accept / Defer at the Step 1.5
  Deferral Confirmation Gate are skipped — those dispositions stay
  gated, never silent
- if the review did not include LOW triage, default the LOWs to
  Fix-now and route any Accept (no benefit / net downside) or Defer
  recommendation through the Step 1.5 gate before skipping

Ask the user to confirm or override the order and the routing split.

**Scope-expansion findings: read disposition from Findings Log, do
not auto-defer.** In v22, `/review` routes scope-expansion findings
severity-aware and records the chosen disposition on each finding's
`Scope-expansion disposition` field in the Findings Log. `/fix` reads
that disposition and acts accordingly:

- **Amend plan now** (CRIT) → extend the plan's `Agreed Scope` and
  `Tasks` to cover this finding, then apply the fix in this /fix
  cycle as if it had always been in scope. Update the plan file
  before applying. If the amend instead adds task(s) deferred to later
  execution (not applied in this same `/fix` cycle), harden them first
  with a proportional scoped `/review-plan` (see `/review-plan`'s
  **Scoped mode**).
- **Downgrade severity** (CRIT) → re-classify the finding under the
  new severity in the Findings Log; re-apply the routing matrix at
  the lower severity. Do not just silently drop the original
  severity.
- **Defer with Risk if deferred** (CRIT) / **Retained with Risk if
  deferred** (HIGH/MED) → do not fix. Record the finding in the
  plan's `Retained Follow-Up Items` with the `Risk if deferred:`
  tag and explanation already populated by /review; mark the
  Findings Log entry's `/fix decision: Follow-up retained`.
- **Fold-in** (HIGH) → apply within this /fix cycle without amending
  the plan's `Agreed Scope`; the smaller-scope addition is absorbed
  silently.
- **Open follow-up** (HIGH option (ii); also selectable for MED, though MED now defaults to Include in plan) → do not fix. Capture in the
  plan's `Deferred / Out of Scope` (Planning Extraction Summary's
  Deferred — Actionable Later subsection) with the `Risk if
  deferred:` tag (mandatory for MED+). Mark `/fix decision:
  Deferred`.
- **LOW scope-expansion (no `Scope-expansion disposition` set — legacy
  v21 plans)** → a LOW finding that reaches `/fix` with no
  `Scope-expansion disposition` field pre-dates v22.4's Deferral
  Confirmation Gate. Apply the LOW flip: it defaults to Fix-now (here,
  outside `Agreed Scope`, "Fix-now" means Fold-in or Include in plan).
  Do NOT silently capture it as a Retained Follow-Up Item — route it
  through the Step 1.5 Deferral Confirmation Gate so any Accept / Defer
  is user-confirmed, never silent. Under v22.4+, LOW scope-expansion
  findings already reach `/fix` with an explicit disposition recorded
  by `/review`'s gate; that disposition takes precedence over this
  fallback.
- **No disposition set + non-LOW** (legacy / pre-v22 plans, or
  fresh review where /review didn't surface the finding as scope-
  expansion) → /fix may identify the finding as scope-expansion
  now and prompt the user for the appropriate disposition before
  acting. Do not silently auto-defer — the v21 auto-defer behaviour
  is replaced by this explicit disposition step.

`/fix` may also OVERRIDE the inline `Triage:` recommendation that
/review set per finding (CRIT/HIGH/MED/LOW dispositions) — per the
v22 Triage field spec, /fix has the override per finding without
restating the rationale. If overriding to a more aggressive
disposition (e.g. /review recommended Defer, /fix overrides to
Fix-now), capture a one-line override reason in `/fix notes`. If
overriding to a less aggressive disposition (e.g. /review recommended
Fix-now, /fix overrides to Defer or Accept), the override is itself a
new silent-deferral candidate and must be routed through the Step 1.5
Deferral Confirmation Gate before being recorded.

## Step 1.5 — Deferral Confirmation Gate (required before honouring skips)

Before applying or skipping the confirmed scope from Step 1, run a
Deferral Confirmation Gate over every finding whose disposition would
skip current fixing. This is the safety net against silent
deferrals — particularly important when /fix is reading a legacy
Findings Log, a pasted /review output, or a round whose dispositions
were set on a pre-v22.4 install where /review did not gate Defer /
Accept / MED-LOW scope-expansion silent paths.

Headless mode. Under a headless / loop invocation (for example when driven by `/execute-loop`), dispose a candidate without a live prompt ONLY when it is AUTO-DISPOSABLE: its recommended disposition is do-the-work (`Fix now` / `Include in plan`) AND its severity is LOW or MED AND it is not production-impacting — apply the recommended disposition and log it. Everything else is MUST-PAUSE — pause and surface it for a human decision, never auto-deciding: `Defer` / `Accept`, any CRIT or HIGH, anything production-impacting (new dependency, environment variable, migration, deploy-side config, dev/prod parity drift), a `/fix` stop-on-failure, or genuine uncertainty. Here the candidates are the Step 1 findings whose disposition would skip current fixing. Interactive behaviour is unchanged — this branch fires only under a headless/loop invocation.

Severity-and-source precedence (apply before evaluating any other
rule below):
- If a finding's severity is CRIT or HIGH AND its `Scope-expansion
  disposition` was set via /review's explicit 3-option Scope-Expansion
  Triage prompt (any of: `Amend plan now`, `Downgrade severity`,
  `Defer with Risk if deferred`, `Fold-in`, `Open follow-up`,
  `Retained with Risk if deferred`), skip the gate for that finding
  regardless of which include rule below it might also match. Those
  decisions are already explicit; the gate must not double-prompt them.

After applying the precedence above, candidates that feed the gate:
- any finding with Fix route `defer` or `accept` from Step 1
- any finding whose `Scope-expansion disposition` is `Defer with Risk
  if deferred`, `Open follow-up`, `Retained with Risk if deferred`,
  or a LOW scope-expansion finding with no disposition set (legacy)
- any /fix override that would change the inline `Triage:` value from
  `Fix-now` / `Fix-now-if-tied` to `Defer` or `Accept`

Candidates that also do NOT feed the gate:
- findings already marked `Applied` in a prior /fix invocation

If no candidates accumulated, the gate is silent — do not fire it on
an empty batch.

Present each candidate one at a time using this shape:

```text
Item N of M: <one-line point>
Recommended: <Fix now | Include in plan | Defer | Accept> — <reason>
App impact if not fixed now: <one or two lines>
Production-impact flag: <yes/no, category if yes>

1. Fix now — apply immediately before continuing
2. Include in plan — add as a new task in Agreed Scope
3. Defer — record as Deferred — Actionable Later
4. Accept — record with rationale; no follow-up action

Reply with 1, 2, 3, or 4.
```

Production-impact categories: new runtime dependency, new environment
variable, database migration, deploy-side config change, dev/prod
parity drift. Flag `yes` and name the category whenever a candidate
hits one of these; flag `no` otherwise. The flag biases the
recommendation toward `Fix now` or `Include in plan`; it does not
force a disposition.

When choosing the **Recommended** disposition above, prefer `Fix now`
or `Include in plan`, and reserve `Defer` for genuinely large or
out-of-scope work; recommend `Accept` only when there is no benefit
to fixing or a net downside.

Wait for the user's reply before moving to the next candidate. Apply
the chosen disposition before continuing:
- `Fix now` — flip the finding's effective Fix route to fix-now,
  remove it from the skip list, and queue it for Step 2 application
- `Include in plan` — append a new 🟥 task in the plan's Agreed Scope
  with a pointer to the finding, mark the finding's `/fix decision:
  Follow-up retained` with notes referencing the new task, and remove
  it from the current fixing queue; then run a proportional scoped
  `/review-plan` on that new task before it is executed — see
  `/review-plan`'s **Scoped mode — harden only newly-added task(s)**
  section (the canonical definition; do not restate it), biasing toward
  tacking onto the active/stage plan over a new follow-up plan
- `Defer` — keep the skip; ensure the finding lands under `Deferred
  — Actionable Later` with a `Risk if deferred:` tag (security /
  correctness / ux-degradation / blocked-work / minor) and a `Revisit
  by:` date or trigger string; record `/fix decision: Deferred`
- `Accept` — keep the skip and record `/fix decision: Accepted` with
  the user-supplied rationale

If the user aborts the gate mid-batch, do not apply any fixes from
the round and do not update `/fix decision` fields on the gated
findings. Pending state lives only in the conversation until the
gate completes or the user explicitly closes the batch. Findings Log
entries already marked `Applied` from a previous /fix invocation
remain untouched.

Use `Accept` as the audited no-follow-up option; do not introduce an
`Ignore` disposition.

Only proceed to Step 2 once every gated candidate has a recorded
disposition.

## Step 2 — Apply one finding at a time
For each confirmed finding:

1. **Pre-fix re-read.** Read the target file(s) fresh from disk. Do not
   rely on memory of the code from earlier in the session.

2. **Constrain scope to:**
   - the file/line in the finding
   - callers explicitly named in Regression Risk
   - sites listed in Pattern Siblings
   - any files explicitly allowed by the finding

   Do not modify anything else.

3. **NO DRIVE-BY CHANGES.** This is the single most important rule of
   this command. Do not refactor unrelated code. Do not introduce new
   helpers, abstractions, or files unless the finding explicitly
   requested them. Do not "improve" nearby code while you are there.
   Drive-by changes are the #1 source of fix-induced regressions and
   will force another review round. If you find yourself wanting to
   tidy something else, stop, and add it as a separate follow-up
   item — do not slip it into this fix.

4. **Apply the fix exactly as the review described.** The Desired
   behaviour and Pattern to follow fields are the spec. If those
   fields are ambiguous, stop and ask — do not improvise.

5. **Honour the Invariant.** If the finding has an Invariant field,
   re-read the file with the fix applied and verify the invariant
   verbatim. The invariant — not just "the fix compiled" — is the
   acceptance bar. For ordering invariants ("lock must be first
   inside tx"), check the actual statement order in the resulting
   code, not just that the call exists.

6. **Apply to all Pattern Siblings.** If the finding has Pattern
   Siblings, apply the same fix to every site listed, or explicitly
   defer each with a one-line reason. Do not partially apply
   patterns — that is what creates 🔁 same-family regressions in
   the next review.

7. **Verify before moving on.** Run the verification step from the
   finding. If the finding has no Verification field, run the
   project's test or build command on the affected area. If the
   change touches a function signature, return type, or schema,
   additionally re-read each caller listed under Regression Risk
   and confirm it still compiles and passes type checks.

   On Windows PowerShell, run verification commands separately or
   check `$LASTEXITCODE` between them; chained `;` will mask
   earlier failures. See the guide's verification section.

8. **Stop on failure.** If verification fails, OR you find an issue
   the fix introduced, do NOT move to the next finding. Report the
   failure and ask whether to revert, retry, or escalate this
   finding to a premium model. Do not silently continue.

9. **Log it.** After each successful fix, update the corresponding
   finding's entry in the plan file's Review Findings Log:
   - set `/fix decision` to `Applied`
   - fill `/fix notes` with: file changed, what was verified,
     sibling sites touched (or "none" if no Pattern Siblings field),
     any deferred sibling sites with one-line reason
   - fill `/fix date` with today's date
   - fill `/fix applied by` with the tool this `/fix` ran in — `Cursor`, `Claude Code`, or `Codex` (do not hardcode Cursor; matches `/review`'s and `/peer-review`'s "set to where it ran" convention and the template's allowed values)

   For findings routed to Accept, Defer, Follow-up retained, or
   Superseded rather than Applied, still update the Findings Log
   entry with the corresponding Decision and a one-line Notes
   explaining why.

   **Not reproducible decision (v22).** If /fix attempts the fix but
   cannot reproduce the underlying issue — the finding appears to
   have been resolved by an intervening commit, is environment-
   dependent and doesn't manifest in the current setup, or the
   review's claim was incorrect on re-inspection — set `/fix
   decision: Not reproducible`. Capture a one-line `/fix notes`
   stating which of the three causes applies (intervening commit
   ref / environment-dependent context / review claim incorrect).
   Do not apply a speculative fix to make the symptom plausibly go
   away; that's a drive-by change in disguise. The full allowed
   set of `/fix decision` values is: Pending, Applied, Accepted,
   Deferred, Follow-up retained, Superseded, Not reproducible.

   After updating, check whether the round still has any
   `/fix decision: Pending` findings. If yes, leave the Round status
   as `Open (X pending)` with X decremented. If no, update Round
   status to `Closed`.

   If the round was sourced from a paste rather than from the Log,
   the entries were written into the Log at Step 0 — this step
   updates those entries.

## Step 3 — Wrap up
Once all confirmed findings are applied (or skipped):
- summarise what was done by walking the Round in the Findings Log
- list anything skipped, deferred, accepted, or escalated, including
  the Step 1.5 Deferral Confirmation Gate outcome for any gated
  candidate (which choice the user made, and where the resulting
  entry was recorded — Deferred — Actionable Later, Accepted
  Assumptions, Excluded Items, or as a new 🟥 task in Agreed Scope
  that will be scoped-`/review-plan`-hardened before execution)
- if more than 3 fixes were applied OR any fix changed a signature,
  schema, or invariant, recommend a follow-up /review — its Post-Fix
  Regression Check and Round Classification will catch cross-file
  regressions this command's per-fix verification cannot see
- if the active model failed on any finding, escalate per the
  model-tier rules in the guide — do not retry on the same model

## What this command does NOT do
- batch fixes and verify at the end
- introduce new code paths or abstractions the review did not request
- expand scope beyond the plan — new features, product decisions, or
  scope expansions go to the plan's `Deferred / Out of Scope` section
  or a new plan, not into /fix
- continue past a verification failure
- redo the /review's job — its findings are the spec, not a starting point
- ignore the Deferral Confirmation Gate — LOWs default to Fix-now, but
  any the user Accepted or Deferred at the gate stay skipped
- silently mutate plan task labels
