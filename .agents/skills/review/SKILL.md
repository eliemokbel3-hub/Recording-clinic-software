---
name: review
description: Review recent work for correctness, risk, readiness, and maintainability before deployment. Shared Cursor/Codex/Claude Code workflow; invoke as /review in Cursor or Claude Code, or $review in Codex. Distinct from Codex CLI built-in /review; this workflow writes plan-aware findings to the Review Findings Log.
disable-model-invocation: false
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/review` in Cursor or Claude Code, or `$review` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

Codex also has a built-in `/review` slash command. In Codex, invoke this workflow as `$review` when you need the plan-aware review that writes structured findings to the active plan; use Codex's built-in `/review` only for native ad hoc code review outside this workflow.

/review is review-only by default. Do not edit code while reviewing
unless the user explicitly asks for "review and fix". Producing the
review output is the deliverable. Code changes belong in /fix, which
applies findings with proper sequencing, scope-locking, and
verification.

## Step 0 — Read plan context

Before reviewing, identify whether an active or recently-completed plan should inform this review.

Detection:
- check `.cursor/plans/` (excluding `.cursor/plans/completed/`) for plan files — this covers both active plans and those in `Completed — Archivable` or `Completed — Follow-ups Retained` states that have not yet been archived
- if running in the same session that produced the implementation work, the relevant plan is already known from session context — use it directly
- if exactly one plan file exists, use it
- if multiple plan files exist, prefer the one with the most recent `Last plan sync` timestamp in its `Current State / Handoff Note`, since that is typically the plan just worked on. State the choice explicitly and ask the user to confirm if the match is ambiguous (e.g. two plans synced on the same day, or the feature name does not obviously match the recent changes)
- if no plan file is found, proceed with a general review based on the code and project conventions

If a plan is identified:
- read the plan's `Goal`, `Design Decisions`, `Critical Constraints`, `Integration Notes`, and `Validation / Verification` sections
- use these as the reference point for the review, not just general code-quality standards
- flag deviations from the plan's stated decisions or constraints as review findings, not as independent style judgments
- do not flag patterns that the plan explicitly chose, even if they are unusual — flag them only if the implementation does not match what the plan described

### Detect review round

Before reviewing, read the plan's `Review History` section.

Round-counting rules:
- ignore any placeholder line such as `- (no reviews yet)` when
  counting entries
- if `Review History` does not exist in the plan file, create it
  before `## Tasks` (with the `(no reviews yet)` placeholder) and
  treat this as round 1
- only append to `Review History` after the review output is
  complete; never append for an aborted review

If `Review History` contains N real entries (excluding placeholder),
this review is round N+1.

After producing the review output below, append a one-line entry to
`Review History` in the plan file using this format:

`- YYYY-MM-DD round N: X CRIT / X HIGH / X MED / X LOW; skew=<dominant-class>; action=<recommendation>`

Where:
- `skew` is one of: `none` (round 1), `pre-existing`, `fix-induced`,
  `same-family`, or `mixed` if no clear dominant
- `action` is one of: `none`, `escalate` (mostly fix-induced),
  `strengthen-siblings` (mostly same-family), `triage-and-ship`
  (mostly pre-existing LOWs)

The classification breakdown (🆕 / ⚡ / 🔁 counts) appears in the
Round Classification section of the review body, not in the History
line. Keep the History line short — it is read by /start-session,
/fix, and Round-3 escalation logic, all of which need only `skew=`
and `action=` to act.

Example entries:
- `2026-04-29 round 1: 0 CRIT / 1 HIGH / 2 MED / 3 LOW; skew=none; action=none`
- `2026-04-29 round 2: 0 CRIT / 0 HIGH / 1 MED / 2 LOW; skew=fix-induced; action=escalate`

If no plan file is in scope, the round cannot be tracked across
sessions. In that case, look at the current conversation: if prior
/review output is visible above, treat it as round 2+; otherwise
treat as round 1. Tell the user the lack of plan file means round
tracking is conversation-only.

## Step 0.5 — Mandatory primary baseline + smart full-file read (required)

Before reviewing, establish the **primary review baseline** and read
the touched code in full. This is mandatory; do not skip it for any
review.

The primary review baseline defines the feature/change scope of this
review: which files count as user-authored sources that get read in
full, and which form the surface for the normal correctness, security,
and executor-judgment passes below. A separate **regression baseline**
is established later inside the Post-Fix Regression Check; do not
conflate the two.

Round 2+ discipline: a second or later `/review` invocation is still a
FULL review of every user-authored file in the feature/change scope,
not a fix-verification pass. The Post-Fix Regression Check below is
additive — it does not replace the main correctness, security, or
executor-judgment passes. Prior review findings are **context and
focus guidance** for what to scrutinize harder (especially pattern
siblings of earlier findings and files touched by `/fix`); they are
not a baseline and not a scope limiter, so the changed-files list
does not shrink to "files touched by the most recent `/fix`".

1. **Establish the primary review baseline.** Pick the first that
   applies:
   - **on round 2 or later**, the commit predating the plan's first
     `/execute` checkpoint (or the feature branch base if discoverable
     — e.g. `git merge-base HEAD main`). Use this regardless of
     subsequent `Last plan sync` updates so the changed-files list
     reflects the full feature/change scope, not just the fix delta
     from the most recent `/fix`. This makes the Round 2+ discipline
     note above mechanically enforceable rather than override-only.
   - changes since the plan's `Last plan sync` timestamp, if an active
     plan exists (round-1 default; also the round-2+ fallback if
     neither a `/execute`-checkpoint commit nor a feature branch base
     can be identified)
   - the most recent commit on the current branch that predates the
     current working changes
   - if none of the above applies, the working tree changes themselves
     — note this in the output so the user knows no prior baseline was
     available

2. **List every changed file** since the primary review baseline.
   State the list at the top of the review output so the user can
   confirm scope. On round 2+, this list still represents the full
   feature/change, not just files touched by the most recent `/fix`.

3. **Read every user-authored source/doc file in full** that is in the
   changed-files list. Do not rely on diff fragments alone — fragments
   miss surrounding context that often makes the difference between a
   finding and a false positive.

4. **For generated, binary, lockfile, build, or regenerated artefacts**
   (e.g. `.docx`, `*.lock`, `dist/`, `build/`, regenerated SVGs, post-
   processed outputs, minified JS, compiled CSS), record the skip
   reason in the review output and read the upstream source input
   instead. Example: skip `cursor-guide.docx` (regenerated
   from `cursor-guide.md` via `./scripts/regenerate-guide.sh`)
   and read the `.md` source.

5. **If a skipped file is directly implicated by a finding** (e.g. the
   docx exhibits a styling regression and the upstream source input
   doesn't obviously explain it), read the relevant source input plus
   any pipeline scripts that transform it.

State the primary review baseline choice, the changed-files list, and
any skip-with-reason decisions at the top of the review output.

## Findings Log append

In addition to the Review History one-liner, append the full findings
detail to the plan file's `Review Findings Log` section.

Rules:
- If `Review Findings Log` does not exist in the plan file (legacy
  plans from before v21), create it before `## Tasks` with the
  `(no findings logged yet)` placeholder, then append the round block.
- Stable IDs: assign CRIT-001, CRIT-002, HIGH-001, etc. in the order
  findings appear in the /review output. Numbering resets per round.
- Initialise every finding's `/fix decision` field to `Pending`.
- Leave `/fix notes`, `/fix date`, and `/fix applied by`
  empty for now — /fix fills them when it processes each finding.
- Set the Round status line to "Open (N pending)" where N is the total
  count of findings in this round.
- Set the Source line to where /review ran: Cursor, Claude Code, or Codex.
- CRIT/HIGH/MED findings get the full structured block matching the
  /review output above (all fields).
- LOW findings get one-line entries with the inline `Triage:` value
  and `/fix decision` set inline (e.g. `Triage: Fix-now; Decision:
  Applied`). There is no standalone `## LOW Triage` section in v22.
- Append only after the review output is complete; never append for
  an aborted review. If a Deferral Confirmation Gate batch is
  required (see below), append only after the gate has completed;
  aborted gates leave the round unappended.
- If no plan file is in scope, skip this step entirely and note in
  the review output that findings persist only in the conversation.

## Parallel independent review (where supported)

The finding-producing passes below (correctness/security, Executor
Judgment, Structural Quality, Post-Fix Regression, Missed-Issue) are
independent lenses over the same changed-files set. If your tool
supports parallel subagents, you may fan them out for breadth and
independence; if it does not, run them sequentially in this same
session — the sequential path is the default and is fully correct.

If your tool supports parallel subagents (e.g. Cursor's Task
subagents, Claude Code's Task tool):
- Spawn one subagent per lens, each given the same primary review
  baseline and changed-files list but a single focus: one for
  correctness/security, one for Executor Judgment + Structural
  Quality, one for Post-Fix Regression + Missed-Issue, and — when a
  plan is in scope — one for plan-deviation (Design Decisions /
  Critical Constraints / Integration Notes adherence).
- Each subagent applies Step 0.5 discipline (reads its files in full)
  and returns candidate findings with concrete `file:line` evidence,
  not prose summaries.
- Collect all subagent findings, then **dedupe** (same root cause at
  the same site = one finding; keep the richest write-up) and
  reconcile severities. The Finding Verification filter, Round
  Classification, Scope-Expansion Triage, the Deferral Confirmation
  Gate, and the Findings Log append then all run **once**, in this
  orchestrating session, over the merged findings — they are never
  delegated to a subagent, because the gate is interactive with the
  user.

If your tool does not support parallel subagents (e.g. Codex), run the
passes sequentially below. This is the documented fallback and changes
nothing about the findings — only how they are produced.

Subagents add **lens diversity, not model diversity**: spawned
subagents inherit this session's model, so they share its blind-spot
profile. The cross-model-family catch-rate gain still comes from
running the peer-review workflow (`/peer-review` in Cursor or Claude
Code, `$peer-review` in Codex) in a different model family — see the
Cross-tool peer-review recommendation at the end.

Perform a thorough but concise review of the recent changes.

Check for:
- correctness and likely bugs
- security issues
- missing validation or error handling
- project-appropriate logging
- production readiness
- unnecessary debug code
- TODOs or temporary shortcuts
- architectural consistency with the existing codebase

For each finding, trace what other code depends on the affected area. A fix that is correct in isolation but breaks a caller is not a safe fix.

## Executor Judgment Check

Perform this additional pass after the correctness and security checks above. This covers code-quality issues that can appear regardless of who or what wrote the code — plan deviations, duplicated logic, unnecessary complexity, and code smells — but which are easy to miss when focus is on correctness.

Check for:
- deviations from the plan's Design Decisions, Critical Constraints, or Integration Notes — flag the deviation, not the decision
- duplicated logic that already exists elsewhere in the codebase (helpers, utilities, existing middleware, shared types)
- obvious code smells — magic numbers, dead branches, over-nested conditionals, copy-pasted blocks, inconsistent error handling
- unnecessary complexity — premature abstractions, speculative features not in the plan, defensive code for impossible conditions
- plan drift — code that works but quietly does something different from what the plan specified

Boundary rule:
Only flag items that a thoughtful developer would want changed before merge. Do not suggest:
- stylistic rewrites or renaming for preference
- refactors that do not materially improve correctness, maintainability, or consistency
- abstractions that are not justified by current usage
- modernisation of working patterns that match the rest of the codebase

If this section finds nothing, say so explicitly rather than padding with minor observations.

## Structural Quality Pass (bounded, review-only)

Run this pass after the Executor Judgment Check. It widens the lens
from line-level smells to structural maintainability: prefer the
simpler shape a future maintainer would thank you for. Like the rest
of /review it is **review-only** — it never edits code, it produces
findings.

Look for:
- **Oversized units** — files, functions, or modules that have grown
  past easy comprehension (e.g. a single file approaching ~1k lines, a
  function that no longer fits on a screen). Flag the smell and name
  the natural seam to split along.
- **Structural duplication** — not just copy-pasted lines (the
  Executor Judgment pass covers those) but parallel structures that
  should share a canonical layer: two flows reimplementing the same
  pipeline, sibling components diverging only in data, repeated
  conditional ladders encoding the same decision.
- **Spaghetti conditionals** — deeply nested or steadily-accreting
  branch ladders where a dispatch table, early return, or polymorphic
  shape would make the control flow legible.
- **Boundary and type cleanliness** — leaky abstractions, primitive
  obsession where a named type would prevent whole classes of bug,
  state living in the wrong layer, modules reaching across a boundary
  they should respect.
- **Canonical-layer reuse** — new code that bypasses an existing
  canonical helper, hook, query layer, or type and reinvents it; name
  the canonical layer it should route through.

Boundary rule (same merge-bar as Executor Judgment):
- Flag a structural finding ONLY when acting on it would materially
  improve maintainability — not for taste, symmetry, or theoretical
  purity. The bar is "a thoughtful maintainer would want this changed
  before the area is next extended," not "this could be structured
  differently."
- This pass NEVER auto-applies. A structural finding is review output;
  any actual restructure happens later under /fix with its own scoping
  and verification.
- A structural finding that would require work beyond the plan's
  `Agreed Scope` (a genuinely large restructure, a new module, a
  cross-cutting refactor) is a scope-expansion finding — route it
  through the Scope-Expansion Triage matrix below by severity. Do NOT
  fold a large restructure silently into the current cycle.

Severity guidance: most structural findings are MED or LOW. Reserve
HIGH/CRIT for structure that actively causes correctness or security
risk (e.g. a duplicated invariant that will drift, a boundary leak
that exposes internal state). If this pass finds nothing worth a
maintainer's attention, say so explicitly rather than padding.

## Post-Fix Regression Check

Perform this pass on every review. Its purpose is to catch regressions
introduced by fixes applied to resolve prior review findings.

This pass is **additive** to the full feature/change review above. A
clean run here does not substitute for the correctness, security, or
executor-judgment passes — those still cover every user-authored file
in the primary review baseline regardless of whether `/fix` touched it.

Select the **regression baseline** (distinct from the primary review
baseline in Step 0.5) in this order, using the first available:
1. the pre-`/fix` state — the most recent commit or working-tree
   checkpoint that predates the fixes applied to resolve prior review
   findings; prior review findings themselves serve as a hint for
   which files and regions the fixes most likely touched
2. changes since the plan's `Last plan sync` timestamp, if an active
   plan exists and no clean pre-`/fix` checkpoint is available
3. the most recent commit on the current branch that predates the
   current working changes
4. if none of the above applies, the working tree changes themselves
   — say so explicitly in the output so the user knows no regression
   baseline was available

For each change since the regression baseline:
- identify what signatures, return values, or data shapes changed
- list callers or dependent code that may now behave differently
- flag any fix that resolved one issue by creating a subtler one elsewhere
- flag any fix that changed behaviour in a way not captured in the plan or changelog

If no fixes or meaningful changes are detectable since the regression
baseline, say so explicitly and move on. Do not manufacture findings.

## Missed-Issue Pass (unconditional, auditable)

Run this pass on every review. It is distinct from the Post-Fix
Regression Check above:

- **Post-Fix Regression Check (above)** = *fix-induced regression*
  check: "did a fix change a signature / return / shape that breaks
  callers?" Focus: what was modified by a fix.
- **Missed-Issue Pass (this section)** = *missed-finding* check: "did
  the review miss something in the touched code?" Focus: what the
  review process may have overlooked.

Both run on every applicable review. Do not collapse them into a
single check — they catch different failure modes.

Scope of the missed-issue pass:
- **Re-read files with findings.** For every file that has a finding
  from any of the passes above, re-read the relevant region and
  surrounding context with fresh eyes.
- **Re-read high-risk touched files.** Auth, transactions, schema
  migrations, concurrency, locking, hook ordering — any touched file
  in these categories gets re-read regardless of whether it has a
  finding.
- **For small changesets (≤5 changed files), re-read all changed
  files** with fresh eyes.

What to look for:
- "embarrassing-if-found" issues — the kind of finding that would be
  obvious in hindsight but is easy to miss on first pass (off-by-one,
  wrong constant, swapped argument order, inverted condition, missing
  guard, dropped error case)
- plan or doc deviations not caught in the main passes — does the
  implementation match what the plan, AGENTS.md, or any referenced
  subsystem doc says it should do?
- gaps between Issues Found and Pattern siblings — was a pattern
  flagged at one site but missed at obvious sibling sites?

**Auditable output (required).** The review output MUST include a
line naming what was re-read and the result, so the pass cannot be
satisfied performatively. Use this shape:

`Missed-issue pass: re-read <files/regions>; result: <none | finding IDs>`

If the pass surfaces new findings, list their IDs and append the
findings to Issues Found with a brief note that they came from the
missed-issue pass. If the pass surfaces nothing, state `result: none`
explicitly rather than omitting the line.

Why unconditional: the v21 round-counting basis for "self-check only
on round 1" is fragile. A multi-checkpoint `/execute` flow producing
rounds 1/2/3 may have rounds 2 and 3 reviewing fresh code that has
never been reviewed before — the round-1-only rule would skip the
missed-issue pass on exactly those rounds. The unconditional framing
removes the round-detection dependency; the cost is bounded by
changeset-size scaling.

## Finding Verification (false-positive filter, before disposition)

After all finding-producing passes above (correctness/security,
Executor Judgment, Structural Quality, Post-Fix Regression, and the
Missed-Issue Pass), run a single Verification filter over the
candidate findings BEFORE any disposition (Round Classification,
Scope-Expansion Triage, the Deferral Confirmation Gate, and the
Findings Log append). Its job is to keep the review trustworthy by
dropping or downgrading findings that do not survive a second look,
so that /fix and the user's attention are never spent on noise.

This pass is **distinct** from the two regression/missed passes above
and must not be merged with them — three separate passes:
- Post-Fix Regression Check = did a fix break a caller? (fix-induced)
- Missed-Issue Pass = did the review overlook something? (missed-finding)
- Finding Verification (this pass) = is each candidate finding *real*?
  (false-positive filter)

For each candidate finding, confirm:
1. **Concrete evidence.** The finding cites a specific `file:line` (or
   a tight region) that actually exists and actually exhibits the
   problem when re-read. A finding with no locatable `file:line`
   evidence is dropped, or downgraded to an explicit "needs
   investigation" note — it does not enter the Findings Log as a firm
   finding.
2. **The claim matches the code.** Re-read the cited lines and confirm
   the described current behaviour is what the code actually does, not
   what it looked like from a diff fragment. Surrounding context
   (guards, earlier returns, callers, types) frequently turns an
   apparent bug into a non-issue.
3. **It is not already handled.** Confirm the issue is not already
   covered by validation, a caller, a type, or a plan decision that
   the first pass missed.
4. **Severity is justified.** If the evidence supports a lower severity
   than first assigned, downgrade it here and note the downgrade.

Drop confirmed false positives from the findings list (do not log
them). Keep a one-line note for any finding that was downgraded or
that survived a genuine challenge. Record the outcome on the Summary
line:

`Finding verification: N candidates; M dropped (no matching file:line evidence); K downgraded`

Only verified findings proceed to Round Classification,
Scope-Expansion Triage, the Deferral Confirmation Gate, and the
Findings Log.

## Round Classification (round 2+ only)

If this is the second or later /review pass on the same work, classify
each finding below as one of:

- 🆕 Pre-existing — was in the code before any fix this session;
  surfaced now because the review went deeper or the fix made it visible
- ⚡ Fix-induced — introduced by a fix applied earlier in this session
- 🔁 Same family — same root cause as a prior finding, recurring at a
  different site (indicates the prior review missed a Pattern Sibling)

Use the round number detected from `Review History` above.

If most findings are ⚡, the executor is the problem — recommend
escalating the model. If most are 🔁, the prior review's Pattern
Siblings field was incomplete — strengthen this review's siblings.
If most are 🆕 LOWs, the loop is converging — LOWs default to Fix-now;
recommend Accept only when there is no benefit to fixing or a net
downside (routed through the Deferral Confirmation Gate). Once no
CRIT/HIGH/MED findings remain, consider shipping even if some LOWs
were Accepted or Deferred at the gate, rather than burning rounds on
trivia.

Skip this section on round-1 reviews.

## Scope-Expansion Triage (severity-aware disposition)

If any finding represents work outside the plan's `Agreed Scope` —
i.e. would require adding a new task, extending an existing one
beyond its written behaviour, or modifying code the plan did not name
— it is a scope-expansion finding. Scope expansion is orthogonal to
severity; a CRIT scope-expansion finding CANNOT be auto-deferred just
because it's "out of scope."

All routing decisions happen at /review's disposition step (this
section), AFTER findings enumeration is complete — not mid-enumeration.
Mid-enumeration hard-stops break /review's natural output structure
and force the user into decisions before they've seen the full
picture. The disposition is recorded on the finding in the Findings
Log (using the `Scope-expansion disposition` field in the per-finding
block) before /fix is invoked.

Routing matrix:

**CRIT scope-expansion** → /review requires an explicit user
disposition before logging, with 3 options:
  (i)  **Amend plan now** — extend the plan's `Agreed Scope` and Tasks
       to cover this finding; treat it as in-scope from here on. Harden
       the newly-added task with a proportional scoped `/review-plan`
       before it is executed (see `/review-plan`'s **Scoped mode**).
  (ii) **Downgrade severity** — if the severity-CRIT classification
       turns out to be wrong on closer inspection (e.g. the issue is
       contained, has no downstream effect, or affects an unused code
       path), reclassify and re-triage under the new severity.
  (iii) **Defer with explicit `Risk if deferred:` value** — record the
       finding as Retained with `Risk if deferred: security: ...` or
       `Risk if deferred: correctness: ...` (per the taxonomy in the
       plan template). This produces the loudest possible session
       warning via `/start-session` and `/end-session` but does NOT
       block plan lifecycle transitions in v22. (The Release
       Readiness gate that would enforce blocking is a deferred v22+
       concern; see the master plan.)

**HIGH scope-expansion** → /review requires an explicit user
disposition before logging, with 3 options:
  (i)  **Fold-in** — apply within the current /review → /fix cycle
       without amending the plan (smaller-scope addition than CRIT).
  (ii) **Open follow-up** — record as a deferred item with explicit
       `Risk if deferred:` tag (mandatory MED+).
  (iii) **Retained with explicit `Risk if deferred:` value** — same
       loud-warning-but-non-blocking behaviour as CRIT option (iii).

**MED scope-expansion** → recommended disposition is **Include in
plan** (add it as a task in `Agreed Scope` so it stays visible and
scheduled); reserve `Open follow-up` / `Defer` for genuinely large or
out-of-scope work. This is gated through the Deferral Confirmation
Gate (see the dedicated section below) before being written to the
Findings Log. The gate fires once after findings enumeration is
complete, batching all MED/LOW scope-expansion candidates together
with any `Triage: Defer` or `Triage: Accept` findings. If the user
keeps the recommended disposition, the finding is logged as `Include
in plan` (a new 🟥 task); if they choose `Fix now`, `Open follow-up`,
`Defer`, or `Accept`, log the corresponding disposition instead. A
finding logged as `Include in plan` then gets the scoped `/review-plan`
hardening described in the Deferral Confirmation Gate's `Include in
plan` outcome below.

**LOW scope-expansion** → recommended disposition follows the LOW
triage bias (default Fix-now; recommend Accept only when there is no
benefit to fixing or a net downside) — but because the finding is
outside the plan's `Agreed Scope`, "Fix-now" here means Fold-in or
Include in plan at the gate. This is gated through the Deferral
Confirmation Gate alongside MED scope-expansion candidates before
being written to the Findings Log.
Empty batches do not fire; if no MED/LOW scope-expansion and no
`Triage: Defer` / `Triage: Accept` findings accumulated, the gate is
silent.

When prompting the user for CRIT/HIGH disposition, present all 3
options clearly and wait for an explicit answer. Do not assume a
default. Record the chosen disposition on the finding's
`Scope-expansion disposition` field in the Findings Log; if the user
chooses option (iii), also populate `Risk if deferred:` with the
chosen tag and one-line explanation, and add the finding to the
plan's `Retained Follow-Up Items` section.

## Deferral Confirmation Gate (required before Findings Log append)

After findings enumeration and the Scope-Expansion Triage matrix
above have produced recommended dispositions, run a single Deferral
Confirmation Gate batch BEFORE appending the round to the plan
file's `Review Findings Log`. The gate prevents silent deferrals
when a `Defer` or `Accept` disposition would leave a real fix on the
table — especially for production-impacting items (new dependencies,
environment variables, migrations, deploy-side config, dev/prod
parity drift).

Headless mode. Under a headless / loop invocation (for example when driven by `/execute-loop`), dispose a candidate without a live prompt ONLY when it is AUTO-DISPOSABLE: its recommended disposition is do-the-work (`Fix now` / `Include in plan`) AND its severity is LOW or MED AND it is not production-impacting — apply the recommended disposition and log it. Everything else is MUST-PAUSE — pause and surface it for a human decision, never auto-deciding: `Defer` / `Accept`, any CRIT or HIGH, anything production-impacting (new dependency, environment variable, migration, deploy-side config, dev/prod parity drift), a `/fix` stop-on-failure, or genuine uncertainty. Here the candidates are the `Defer` / `Accept` and MED/LOW scope-expansion dispositions produced above. Interactive behaviour is unchanged — this branch fires only under a headless/loop invocation.

Severity-and-source precedence (apply before evaluating any other
rule below):
- If a finding's severity is CRIT or HIGH AND its `Scope-expansion
  disposition` was set via the Scope-Expansion Triage matrix above
  (any of: `Amend plan now`, `Downgrade severity`, `Defer with Risk
  if deferred`, `Fold-in`, `Open follow-up`, `Retained with Risk if
  deferred`), skip the gate for that finding regardless of which
  include rule below it might also match. Those decisions are already
  explicit; the gate must not double-prompt them.

After applying the precedence above, candidates that feed the gate:
- any finding with `Triage: Defer` or `Triage: Accept` (regardless
  of severity or scope-expansion status)
- any MED or LOW scope-expansion finding, regardless of its
  recommended disposition (`Include in plan`, `Fold-in`, `Open
  follow-up`, `Retained with Risk if deferred`, `Defer`, or `Accept`)
  — the recommendation is shown at the gate and the user confirms or
  overrides it (this matches the MED/LOW scope-expansion sections
  above, which gate every such candidate, now that the MED default is
  `Include in plan` and the LOW default is Fold-in / Include in plan)

Candidates that also do NOT feed the gate:
- findings with `Triage: Fix-now` or `Triage: Fix-now-if-tied` —
  these flow straight into the Findings Log with their existing
  disposition, since they are not silent deferrals

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

Production-impact categories: new runtime dependency, new
environment variable, database migration, deploy-side config change,
dev/prod parity drift. Flag `yes` and name the category whenever a
candidate hits one of these; flag `no` otherwise. The flag biases
the recommendation toward `Fix now` or `Include in plan`; it does
not force a disposition.

When choosing the **Recommended** disposition above, prefer `Fix now`
or `Include in plan`, and reserve `Defer` for genuinely large or
out-of-scope work; recommend `Accept` only when there is no benefit
to fixing or a net downside.

Wait for the user's reply before moving to the next candidate. Apply
the chosen disposition before continuing:
- `Fix now` — note the finding as a fix-now candidate so the
  subsequent `/fix` invocation applies it immediately (no
  scope-expansion silent path)
- `Include in plan` — add a new 🟥 task in the plan's Agreed Scope
  and log the finding with `Triage: Fix-now` so `/fix` handles it,
  then run a proportional scoped `/review-plan` on that new task
  before it is executed — see `/review-plan`'s **Scoped mode — harden
  only newly-added task(s)** section (the canonical definition; do not
  restate it), and bias toward tacking onto the active/stage plan over
  a new follow-up plan
- `Defer` — record the finding's `Scope-expansion disposition` (or
  for non-scope-expansion findings, the disposition decision) with a
  `Risk if deferred:` tag (security / correctness / ux-degradation /
  blocked-work / minor) and a `Revisit by:` date or trigger string
- `Accept` — record the user-supplied rationale; no follow-up action
  will be created

If the user aborts the gate mid-batch, do not append the round to
the Findings Log. Pending state lives only in the conversation until
the gate completes or the user explicitly closes the batch.

Use `Accept` as the audited no-follow-up option; do not introduce an
`Ignore` disposition.

Only proceed to Findings Log append once every gated candidate has a
recorded disposition.

## Output format

## Looks Good
- ...

## Issues Found
For each finding, use this structure (omit fields that don't apply):

- **[SEVERITY]** `file:line` — short title
  - Classification (round 2+ only): 🆕 / ⚡ / 🔁
  - Triage: Fix-now / Accept / Defer / Fix-now-if-tied — the agent's
    recommended disposition. Default behaviour:
    - CRIT/HIGH default to Fix-now (severity dominates; user may
      override via the scope-expansion disposition matrix below)
    - MED uses Regression risk and Pattern siblings below plus agent
      judgment to choose
    - LOW findings default to Fix-now. Recommend Accept only when
      there is no benefit to fixing or a net downside; that
      recommendation is routed through the Deferral Confirmation Gate
      so the user is prompted. Defer remains available at the gate.
      Fix-now-if-tied still applies for LOWs tied to a CRIT/HIGH/MED
      fix.
    `Defer` and `Accept` recommendations go through the Deferral
    Confirmation Gate (see section above) before being written to the
    Findings Log; `Fix-now` and `Fix-now-if-tied` are not gated.
    `/fix` may override per finding without restating the rationale.
  - Fix route: fix-on-fast / premium-only / defer / accept
  - Why it matters: as much detail as needed
  - Current behaviour: one line
  - Desired behaviour: one line
  - Pattern to follow: existing helper / convention / Design Decision
    reference, with brief context if not self-evident
  - Pattern siblings: other places in the codebase where the same
    idiom appears and likely needs the same fix; list them or write
    "none found". REQUIRED when the finding is pattern-shaped (raw
    API errors in toasts, repeated permission checks, repeated query
    invalidation, repeated transaction guards, repeated fetch-vs-helper
    drift, repeated microcopy, repeated hook patterns). Optional
    otherwise.
  - Invariant: a plain-English statement of what must be true after
    the fix. REQUIRED when the finding involves transactional ordering,
    lock acquisition, hook ordering, render-loop structure, cache
    identity, permission-check ordering, or schema-migration order.
    Example: "lockActiveOwnerOrAdminsForTeamTx must be the first DB
    call inside the transaction body. Any tx.query.* read of
    membership state must come AFTER this lock returns."
    Optional otherwise.
  - Verification: how to confirm the fix worked
  - Regression risk: which files, functions, or callers depend on this
    code and could break if it changes
  - Scope-expansion disposition (if applicable): Amend plan now /
    Downgrade severity / Defer with Risk if deferred / Fold-in / Open
    follow-up / Retained with Risk if deferred *(CRIT and HIGH
    scope-expansion findings require an explicit disposition at
    /review's enumeration completion per the Scope-Expansion Triage
    section above; MED and LOW scope-expansion dispositions go
    through the Deferral Confirmation Gate before Findings Log
    append)*

LOW entries may be emitted as one-line shorthand carrying the inline
`Triage:` value plus `/fix decision` (e.g. `- **[LOW]** file:line —
title — Triage: Fix-now; Decision: Applied`). There is NO standalone
`## LOW Triage` section in v22 — the inline `Triage:` field on each
finding replaces it (per master Critical Constraint #12: no net
command-file bloat). `/fix` allowed decision values:
`Pending / Applied / Accepted / Deferred / Follow-up retained /
Superseded / Not reproducible`. Use `Not reproducible` when `/fix`
attempts the finding but cannot reproduce the issue (fixed by an
intervening commit, environment-dependent, or finding was incorrect).

`fix-on-fast` is a review-time routing decision: this finding can be
applied on whichever fast model is active when running /fix. It is
NOT a plan task label. The plan task labels are
`[executor: premium-only]` and `[decision]`.

## Executor Judgment
Same structure as Issues Found.

## Structural Quality
Same structure as Issues Found. Reports findings from the Structural
Quality Pass (oversized units, structural duplication, spaghetti
conditionals, boundary/type cleanliness, canonical-layer reuse).
Review-only — never auto-applied; large restructures route through
Scope-Expansion Triage. If empty, state "none".

## Post-Fix Regressions
- **[SEVERITY]** `file:line` — regression
  - What changed
  - Dependent code affected
  - Recommended action
  - Regression baseline used: pre-`/fix` state / last plan sync
    fallback / recent commit / working tree only

## Recommended Fix Order
Order by dependency, not severity. For each finding:
1. [SEVERITY] file:line — short label  (fix route: fix-on-fast / premium-only / defer / accept)
2. ...

State only the order rationale (which findings depend on which) — the
issues themselves are documented above.

## Summary
- files reviewed:
- critical:
- warnings:
- executor judgment items:
- structural quality items:
- round (from Review History): N
- round classification (round 2+): N 🆕 / N ⚡ / N 🔁
- finding verification: N candidates; M dropped (no matching file:line evidence); K downgraded
- missed-issue pass: re-read <files/regions>; result: <none | finding IDs>

Severity levels: CRITICAL / HIGH / MEDIUM / LOW

## Fix-route routing

For each finding, propose a fix route using severity AND complexity,
not severity alone:

Premium-only by default:
- CRITICAL or HIGH severity (with override below)
- any finding with an Invariant field unless the invariant is trivial
- auth, security, permissions
- schema or data migrations
- transactions, concurrency, locking
- hook ordering, render-loop, cache identity issues
- cross-file helper refactors
- final UX polish

fix-on-fast candidates:
- copy fixes and microcopy alignment
- localised validation
- dead-code removal
- test additions with clear examples
- CRUD plumbing where the API contract is explicit
- mechanical import / type fixes
- single-file pattern siblings of an already-fixed pattern

Severity override: a CRITICAL or HIGH finding may be marked fix-on-fast
if the fix is genuinely mechanical (e.g. a missing import that crashes
the app). State the override reason inline.

Round-3 escalation: if this is review pass 3+ on the same work and the
prior round's `action` field was `escalate`, mark every remaining
finding as premium-only. The fast model is failing reliably enough on
this work that further attempts will burn tokens without converging.

After the review is complete, remind the user to run the project's test suite or build command if one exists — static review alone cannot catch all regressions.

## Cross-tool peer-review recommendation (model diversity)

If the findings are non-trivial — defined as **≥1 CRIT**, OR **≥2
HIGH**, OR **round-2+ with `action=escalate`** — recommend the user
runs the matching peer-review workflow next (`/peer-review` in Cursor
or `$peer-review` in Codex), AND recommend a cross-MODEL-family tool
for the peer review:

- If this review ran in Cursor on GPT 5.x, recommend `/peer-review` in
  Claude Code on Opus 4.7 for the strongest cross-family catch-rate.
- If this review ran in Codex on GPT 5.x, recommend `/peer-review` in
  Claude Code on Opus 4.7 for the strongest cross-family catch-rate.
- If this review ran on Claude Opus, recommend `/peer-review` in Cursor
  on GPT 5.4 high/xhigh or `$peer-review` in Codex on GPT 5.x.
- Same-MODEL-family fallback is acceptable only if the cross-family tool
  is unavailable.

Reasoning: same-model reviewers in different tools share the
executor's blind-spot profile, which defeats the purpose of
peer-review. Different model families have different blind-spot
profiles; that's the catch-rate gain peer-review is designed to
exploit. Tool-only diversity (e.g. Cursor on Opus → Claude Code on
Opus, or Cursor GPT-family → Codex GPT-family) is weaker than a true
cross-family peer review.

Wording: "Findings are non-trivial (≥1 CRIT / ≥2 HIGH / round 2+
escalating). Recommend running peer review next in the strongest
cross-model-family tool available, preferably Claude Code on Opus 4.7
if this review ran on GPT-family. The plan file's Findings Log is
shared between tools so no copy-paste is needed."

If findings are trivial (no CRIT, ≤1 HIGH, no escalation), do not
make the cross-tool recommendation — the friction outweighs the
expected catch-rate gain.
