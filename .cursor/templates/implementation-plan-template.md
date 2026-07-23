# Feature Implementation Plan
**Feature:** [feature-name]
**Overall Progress:** `0%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: None
- Follow-up plans: None

## Goal
[Short plain English summary]

## Planning Extraction Summary
Populate this during plan creation or plan hardening.

**Workflow Schema:** v22 *(legacy detection marker — `/start-session`, `/load-plan`, `/document`, and `/end-session` read this line; pre-v22 plans omit it and commands fall back to legacy schema, suppressing v22-only fields below)*

**Executor tier:** entirely premium | fast/medium involved *(answer the Step 0 Executor Capability Gate in `/create-plan` and `/review-plan`; mandatory — the gate is not satisfied without a recordable answer; when the plan is authored on a higher tier than the intended executor, optionally enrich the answer with tier-gap free text that keeps `entirely premium` leading, e.g. `entirely premium — planned on Fable 5; executor Opus-class; tier-gap dosing applied (design decisions, edge-case inventory, API contracts, acceptance criteria locked)`)*

### Agreed Scope (Build Now)
- [confirmed in-scope item]

### Deferred — Actionable Later
- [item]
  - Why deferred:
  - Intended future outcome:
  - Relevant files / subsystems:
  - Dependencies / prerequisites:
  - Recommended next action:
  - Risk if deferred: *(mandatory for MED+ items, optional for LOW; format = `<tag>: <one-line explanation>` where tag ∈ {security, correctness, ux-degradation, blocked-work, minor})*
  - Revisit by: *(optional; format = `YYYY-MM-DD` OR trigger string — date items get an overdue check in `/start-session` and `/end-session`; trigger items surface as `revisit-when: <string>`)*

### Excluded — Revisit Only If Needed
- [item]
  - Why excluded:
  - When to revisit:
  - Relevant files / subsystems:
  - Recommended next action (if any):

### Accepted Assumptions — Revalidate Later
- [assumption]
  - Why accepted for now:
  - Risk if assumption becomes false:
  - Trigger for revisit:
  - Recommended next action:

### Key Design Decisions
- [decision]
  - Why:
  - Alternatives rejected:
  - Still applies to follow-up work: Yes / No

## Key Findings

### Files / Symbols Involved
- Specific files, routes, functions, components, tables, jobs involved

### Codebase Integration Notes
- Existing patterns this should follow
- Important dependencies / callers / data flows
- Repo-specific gotchas to avoid

### External / API Findings
(Only if relevant)
- Endpoints, behaviours, limits, quirks, test results

## Planned Workflow Summary

### Flow 1 — [name]
- Plain English description

### Flow 2 — [name]
- Plain English description

## Design Decisions
- Decision 1 — [chosen approach] because [why]
  Alternatives considered: [rejected option and why]

## Schema / Data Changes
(Only if relevant)
- New tables / columns / relationships / backfills

## Config / Environment / Deployment Impact
(Only if relevant)
- Env vars
- Hosting platform production variables
- Migration/deploy ordering
- Release risks

## Critical Constraints
- Non-negotiable implementation rules
- Safety boundaries
- Compatibility requirements

## Validation / Verification
- Tests to run
- Manual checks
- Expected success criteria

## Deferred / Out of Scope
Capture only items discussed during planning or execution that are intentionally not part of the current implementation.

For each item, state:
- what it is
- why it is deferred or excluded
- whether it is likely future work, a true non-goal, or an accepted assumption
- what later session context would be needed to pick it up safely

## Current State / Handoff Note
- Last completed step: Planning complete
- Current in-progress step: None
- Immediate next action: Start Task 1 via `/execute`
- Open blockers / open questions: None
- Last plan sync: [date]

## Review History
Each /review invocation appends a one-line entry here. /review uses
this section to detect which round it is. Ignore the placeholder line
when counting rounds.

- (no reviews yet)

Format /review will append:
- YYYY-MM-DD round N: X CRIT / X HIGH / X MED / X LOW; skew=<class>; action=<rec>

## Review Findings Log
Each /review invocation appends a detailed findings block here, with
/fix updating per-finding Decision and Notes as it processes each one.

Findings carry stable IDs within a round (CRIT-001, HIGH-001,
MED-001, LOW-001, etc.) so they can be referenced across sessions
and tools without copy-paste.

/fix reads from this section when a round has pending decisions.
/start-session reads this section to surface unprocessed-findings
count alongside the Review History one-liner.

Plan peer-review rounds — the canonical `Source:` contract: a headless
`/peer-loop` plan-review pass (its token-gated plan-review mode — the
tokens are defined in `/peer-loop` and `/peer-review` only) writes its
plan critique as a normal round here with the mode-distinct
`Source: <Tool> plan peer-review`, i.e. `Cursor plan peer-review` /
`Claude Code plan peer-review` / `Codex plan peer-review`. These
rounds are PLAN-scoped: /fix NEVER ingests them — its Step 0 round selection excludes any round
whose `Source:` ends in `plan peer-review`; the amendment route is the
owning planning session applying `/review-plan`-style amendments (or a
scoped `/review-plan`), with per-finding dispositions marked on the
round. Code-review rounds (any other `Source:`) keep the normal /fix
route. The value deliberately ends in `peer-review` so consumers using
the `… peer-review` suffix rule (e.g. `/peer-review`'s skip-back set)
exclude plan rounds even when they do not know the specific value.

- (no findings logged yet)

Format /review will append per round:

### Round N — YYYY-MM-DD
Round status: Open (X pending) / Closed / Superseded
Source: Cursor / Claude Code / Codex / pasted

#### CRIT-001: `file:line` — short title
- Classification (round 2+ only): 🆕 / ⚡ / 🔁
- Triage: Fix-now / Accept / Defer / Fix-now-if-tied *(agent's recommended disposition; CRIT/HIGH default Fix-now; MED uses existing per-finding fields below + agent judgment; LOW defaults to Fix-now — recommend Accept only when there is no benefit to fixing or a net downside, routed through the Deferral Confirmation Gate, with Fix-now-if-tied for LOWs tied to a CRIT/HIGH/MED fix. `/fix` may override per finding without restating the rationale.)*
- Fix route: fix-on-fast / premium-only / defer / accept
- Why it matters: [from /review output]
- Current behaviour: [from /review output]
- Desired behaviour: [from /review output]
- Pattern to follow: [from /review output]
- Pattern siblings: [from /review output]
- Invariant: [from /review output if present]
- Verification: [from /review output]
- Regression risk: [from /review output]
- Scope-expansion disposition (if applicable): Amend plan now / Downgrade severity / Defer with Risk if deferred / Fold-in / Open follow-up / Retained with Risk if deferred *(CRIT and HIGH scope-expansion findings require an explicit disposition at /review's enumeration completion; MED and LOW scope-expansion dispositions go through the Deferral Confirmation Gate before Findings Log append — MED's recommended disposition is Include in plan (recorded via the gate as a new task + `Triage: Fix-now`, not a value of this field), reserving Open follow-up / Defer for genuinely large work; a new task created via `Include in plan` or `Amend plan now` is hardened by a scoped `/review-plan` before execution — see `/review-plan`'s Scoped mode)*
- /fix decision: Pending / Applied / Accepted / Deferred / Follow-up retained / Superseded / Not reproducible *(Not reproducible = /fix attempted the finding but could not reproduce the issue, e.g. fixed by an intervening commit, environment-dependent, or finding was incorrect)*
- /fix notes: [filled by /fix — what was done, sibling sites touched]
- /fix date: [filled by /fix]
- /fix applied by: Cursor / Claude Code / Codex

#### HIGH-001: ... (same structure)
#### MED-001: ... (same structure)

LOW entries are one line each rather than the full block. The inline
`Triage:` value (Fix-now / Accept / Defer / Fix-now-if-tied) captures
the disposition recommendation directly on the entry; LOWs default to
Fix-now, and any Accept / Defer is gated at the Deferral Confirmation
Gate. There is NO standalone `## LOW Triage` section in v22 — the
inline `Triage:` field
on each entry replaces it (per master Critical Constraint #12: no net
command-file bloat).

#### LOW-001: `file:line` — short title — Triage: Fix-now; Decision: Applied; applied by: Cursor
#### LOW-002: `file:line` — short title — Triage: Accept; Decision: Accepted (no benefit to fixing — changing it would diverge from the surrounding file convention); applied by: Claude Code

The Round status line is derived/computed:
- "Open (N pending)" — at least one finding has Decision: Pending
- "Closed" — no findings have Decision: Pending; each finding has been resolved (Applied / Accepted / Deferred / Follow-up retained / Superseded). The per-finding decisions carry the actual outcome detail.
- "Superseded" — a later round's findings have made this round's findings obsolete (set manually only when this is the case)

## Tasks
Tasks may carry an executor label:
- no label = default; runs on whatever model is active
- `[executor: premium-only]` = must run on a premium reasoning model;
  /execute hard-stops at the boundary

Where the dependency graph permits, cluster premium-only tasks
adjacent to each other to reduce model-switching. Do not reorder
dependencies to achieve clustering.

If this plan may be built with `/execute-loop`, group tasks into
**phases** intentionally: the loop runs `/review-loop` + a cross-family
peer pass at each phase boundary, so isolate foundational, security,
schema, or shared-invariant tasks into their own early phase and batch
contiguous low-risk tasks together.

A task may also be a **decision-point task (optional)**. A
decision-point task carries a `[decision]` label and its deliverable is
a *recorded decision*, not code. Use one only when a genuinely-uncertain
choice cannot be made well until execution reduces the uncertainty —
decide it at execution time instead of baking a premature assumption
into the plan. If the choice can be made now, decide it now; if it
belongs to a later plan, use a `Defer` instead. Decision points are
optional and should stay rare — prefer resolving a choice over deferring
it. `/execute` treats a `[decision]` task as an intentional, planned
hard-stop: it presents the framed choice and waits, rather than building
anything.

Shape of an undecided decision-point task:
- `[decision]` label on the task line
- `Options:` — the candidate choices
- `Decide after:` *(optional)* — what must be true or known before deciding
- `Blocks:` *(optional, human-readable)* — the downstream tasks that depend on it

Place a decision-point task AFTER the tasks that resolve its uncertainty
and BEFORE the tasks that consume the decision. When the decision is
made, record the outcome inline on the task and mark it 🟩:
- `Chosen: <option> (YYYY-MM-DD); rationale: <one line>`

- [ ] 🟥 Step 1: ...
  - [ ] 🟥 Subtask ...
- [ ] 🟥 Step 2: ...
- [ ] 🟥 Step N: Premium polish & E2E pass         [executor: premium-only]
- [ ] 🟥 Step D: Choose the cache backend           [decision]
  - Options: Redis / in-memory / file-based
  - Decide after: Step 2 load test shows the hit-rate profile
  - Blocks: Step N cache-layer implementation

### Hardening stage (optional, for large plans)
For a large plan, add a **Hardening stage** near the end of the
executable task list — a reusable sequence that raises quality before
the work ships:
1. run `/review-loop` (or `/review` → `/fix`) to convergence
2. run `/simplify` (propose-only) — log findings to the Review Findings Log
3. run `/security-review` (propose-only) — log findings the same way
4. route the simplify / security findings by impact: trivial → `/fix`;
   substantial → a plan-amending disposition that appends task(s) to
   THIS plan, then a scoped `/review-plan` on them (see `/review-plan`'s
   **Scoped mode**)
5. finish with a final `/review` (or cross-family `/peer-review`) re-check

Keep it optional and proportional — a small plan does not need a formal
hardening stage. Put the Hardening stage on the executable **stage /
feature** plan, never on a master coordination plan: a master's tasks
are stages and it must not be `/execute`d directly, so when a master
needs hardening, create or use a child hardening-stage plan instead.

- [ ] 🟥 Step H: Hardening pass
  - [ ] 🟥 H1: `/review-loop` (or `/review` → `/fix`) to convergence
  - [ ] 🟥 H2: `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`
  - [ ] 🟥 H3: `/security-review` — log findings; same impact-tiered routing
  - [ ] 🟥 H4: final `/review` (or cross-family `/peer-review`) re-check to confirm convergence

## Retained Follow-Up Items
Use this section when the plan is in `Completed — Follow-ups Retained` state.

This section should be derived from the earlier `Planning Extraction Summary` through a mechanical completion review.

For each deferred / excluded / accepted-assumption item from the `Planning Extraction Summary`, classify it as one of:
- Resolved
- Carried Forward
- Superseded
- Re-deferred

Only `Carried Forward` and `Re-deferred` items should remain actionable here.

### Deferred — Actionable Later
- [item]
  - Status: Carried Forward / Re-deferred
  - Why retained:
  - Intended future outcome:
  - Relevant files / subsystems:
  - Dependencies / prerequisites:
  - Recommended next action:
  - Risk if deferred: *(mandatory for MED+ items, optional for LOW; format = `<tag>: <one-line explanation>` where tag ∈ {security, correctness, ux-degradation, blocked-work, minor})*
  - Revisit by: *(optional; format = `YYYY-MM-DD` OR trigger string — date items get an overdue check in `/start-session` and `/end-session`; trigger items surface as `revisit-when: <string>`)*
  - Reconciliation notes:

### Excluded — Revisit Only If Needed
- [item]
  - Status: Carried Forward / Superseded
  - Why retained or superseded:
  - When to revisit:
  - Relevant files / subsystems:
  - Recommended next action (if any):
  - Reconciliation notes:

### Accepted Assumptions — Revalidate Later
- [assumption]
  - Status: Carried Forward / Superseded
  - Why retained or superseded:
  - Risk if assumption becomes false:
  - Trigger for revisit:
  - Recommended next action:
  - Reconciliation notes:

## Follow-Up Continuation Notes
When follow-up work is resumed later:
- what should the next follow-up focus on first
- what should remain out of scope
- which design decisions from this plan still apply
- which findings or constraints a fresh session must not rediscover

---
*Plan saved to: .cursor/plans/plan-[feature-name].md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
*Sections marked (Only if relevant) can be omitted when genuinely not applicable, but never omit decisions, constraints, verification steps, or integration knowledge that a fresh session would otherwise have to rediscover.*
*For lightweight plans, plans with fewer than 5 tasks, or plans created without a preceding `/explore` discussion, sections with no real content should be marked `N/A — simple feature` rather than padded with placeholder structure.*
