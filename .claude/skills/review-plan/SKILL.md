---
name: review-plan
description: Review an approved native plan against the planning discussion and the real codebase, run a critique gate, propose adjustments, and save a hardened execution plan to .cursor/plans/. Shared Cursor/Codex/Claude Code workflow; invoke as /review-plan in Cursor or Claude Code, or $review-plan in Codex.
disable-model-invocation: false
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/review-plan` in Cursor or Claude Code, or `$review-plan` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

If running in Codex or Claude Code, harden a saved `.cursor/plans/plan-*.md` file using current or pasted planning context. Cursor-only references to native Plan Mode or `@Past Chats` do not apply in Codex or Claude Code. If running in a fresh Codex or Claude Code session (not the one that produced the plan), continue in the original planning session or paste the most relevant planning context before proceeding.
Execution may happen later in Codex, Cursor, or Claude Code; preserve the executor-tier assumptions in the plan.

Please review and harden the current implementation plan before execution.

This command is used after native Plan Mode has produced a draft plan, or when a plan-like discussion already exists and needs to be turned into an execution-quality saved plan.

Run this command in Agent mode.

Normally run it in the same conversation that produced the native plan so the planning discussion is still available. After approving the native plan in Plan Mode, switch the conversation to Agent mode before running `/review-plan`.

If the planning conversation became long, noisy, or confused, start a fresh Agent chat and use `@Past Chats` to bring the planning discussion back in before running `/review-plan`.

## Step 0 — Executor Capability Gate (required, runs first)

This gate runs BEFORE the planning-inputs check. It is unconditional: every hardened plan must record an Executor tier in its `Planning Extraction Summary` before any reconciliation work happens. The gate is not satisfied without a recordable answer.

If the planning conversation or saved plan has not already stated this, ask:
"Will this plan be executed entirely on a premium model, or will fast
or medium-tier models be involved?"

Record the confirmed answer verbatim; it will be written to the
hardened plan's `Planning Extraction Summary` as:

`**Executor tier:** entirely premium | fast/medium involved`

The recorded tier drives the Critique Gate (Step 1.5) executor-tier-
aware item and any fast-executor hardening additions surfaced as
proposed adjustments at Step 2.

If entirely premium, skip fast-executor-specific hardening, but still
include any specification the feature needs for correctness, review
continuity, and fresh-session handoff. Premium execution reduces the
need for defensive detail; it does not remove the need for important
design decisions, API contracts, permission matrices, or UX
requirements when those are central to the work.

**Planner/executor tier gap (within "entirely premium").** When the
answer is "entirely premium", also confirm (from the conversation, the
saved plan, or by asking) whether the plan was — or is being —
authored on a HIGHER tier than the model that will execute it — for
example the plan is written on an ultra-tier model while an Opus-class
premium model executes. A premium executor is not the planning model:
judgment the planner would apply at build time does not transfer on
its own. When such a gap exists, do not skip the fast-executor list
wholesale — apply it selectively and at lighter dosing, prioritising
locked design decisions, an edge-case inventory, API contracts,
design-doc-anchored UI specification, and per-task acceptance
criteria; surface anything the saved plan is missing on these fronts
as a proposed adjustment (Step 2). Preserve any tier-gap free text the
saved plan already carries, and record or enrich the gap as free text
appended to the hardened plan's `Executor tier:` line — no schema
change, and the value MUST keep `entirely premium` leading (downstream
commands substring-check this line; never include the literal phrase
`fast/medium involved` in the enrichment text). Worked example:

`**Executor tier:** entirely premium — planned on Fable 5; executor
Opus-class; tier-gap dosing applied (design decisions, edge-case
inventory, API contracts, acceptance criteria locked)`

If fast/medium will execute UI-bearing or specification-sensitive
work, judge what the plan needs from the same suggested list as
`/create-plan` Step 0 (anchor patterns, per-screen UI specification,
microcopy dictionary, API contract appendix, permission matrix,
per-phase files-touched manifest, per-phase Definition of Done,
premium-only task labels). Add only those elements that apply. If the
saved plan was missing anything you judge necessary, treat that as a
proposed adjustment (Step 2) and surface it under "Added for
Fresh-Session Handoff" or "Validation / Deployment / Migration
Additions" as appropriate.

Trust your judgment about what's needed. Do not pad the plan with
sections that don't apply just because the gate listed them.

## Step 0.1 — Confirm planning inputs exist
Before doing anything else, confirm that at least one planning source exists:
- an approved native Cursor plan
- the current planning conversation
- a referenced prior planning chat (for example via `@Past Chats`)

If none of these exist, stop and tell me:
- to use native Plan Mode first for significant multi-step work
- or to use `/explore` then `/create-plan` if I want the exploration-led path instead

## Step 0.5 — Gather all planning sources
Read and compare these sources before proposing any changes:

1. The approved plan
- read the native Cursor plan if one exists
- if multiple candidate plans exist, ask me which one to use

2. The original planning discussion
- review the current conversation and any referenced prior planning chat
- identify scope, constraints, edge cases, non-goals, and design choices that were discussed but may not be captured clearly in the plan

3. The real codebase and docs
- re-read the relevant code before trusting the plan
- check `AGENTS.md` for relevant `Subsystem Documentation` pointers
- consult `docs/lessons.md`, if it exists, for recurring project gotchas relevant to the plan's area
- consult `docs/design-system.md`, or the design doc named in `AGENTS.md`'s Subsystem Documentation, if one exists, for the project's recorded UI design cues when the plan touches UI
- if deeper docs exist for the area, read them before judging the plan
- identify integration points, dependencies, schemas, state changes, caller impacts, config requirements, deployment implications, and validation needs

4. Persisted exploration scratch (optional)
Apply the same **scratch-consumption rule** that `/create-plan` uses:
- discover all `.cursor/plans/explore-*.md` files
- if none exist, proceed with the three sources above
- if one or several exist, present each by its in-file header (area explored + date) and path, and ask the user to choose one, or none
- select by the in-file header date/area the user confirms — never auto-anchor on filesystem "latest by mtime" (a committed scratch travels across machines, where `git checkout` / `pull` does not preserve the original mtime)
- absorb the chosen scratch as an ADDITIONAL planning source only after the user confirms — never silently recognize a scratch, and never mix an unrelated exploration into a native-plan hardening pass
- remember whether a scratch was consumed, and which file — Step 7 offers to delete only that file after the plan is saved

Do not write code yet.

## Parallel critique (where supported)

The reconciliation pass (Step 1) and the Critique Gate (Step 1.5) are
independent lenses over the same plan + code: coverage, practicality /
feasibility, risk (edge cases, integration, migration, deployment),
and the simpler-path search. If your tool supports parallel subagents
(e.g. Cursor's Task subagents, Claude Code's Task tool), you may fan
these lenses out — one subagent each for coverage, practicality /
feasibility, risk, and simpler-path — each reading the plan plus the
real code it names and returning concrete findings (plan section or
`file:line`). Collect, dedupe, and reconcile in this session; the
Step 2 adjustment summary, Step 3 clarification, and Step 3.5 gate all
run once here, with the user.

If your tool does not support parallel subagents (e.g. Codex), run the
lenses sequentially through Steps 1 and 1.5 — the documented fallback,
which changes nothing about the critique, only how it is produced.

Subagents add lens diversity, not model diversity (they inherit this
session's model). For a true cross-model-family check on a non-trivial
plan, use the plan-aware `/peer-review` recommended at Step 7.

## Scoped mode — harden only newly-added task(s)

`/review-plan` has two modes. The default is a **full-plan** hardening
pass (Steps 0–8 below, over the whole plan). **Scoped mode** is a
narrower entry used when a plan-amending disposition has just appended
one or more 🟥 task(s) to an already-hardened, in-flight plan — for
example `/review`'s `Include in plan` or a CRIT/HIGH `Amend plan now`,
the equivalent dispositions in `/fix` and `/execute`, a `/create-plan`
gate's `Include in plan`, or a substantial `/simplify` /
`/security-review` finding. Its job is to harden ONLY the newly-added
task(s) in place, so an addition gets the same review-quality treatment
as the original plan without spawning a separate follow-up plan.

This section is the **single source of truth** for scoped behaviour.
The disposition handlers in `/review`, `/fix`, `/execute`,
`/create-plan`, `/peer-review`, and the plan template point here rather
than restating it.

### Scoped inputs
The invoking command (or the user) supplies:
- the target plan file (the active in-flight plan), and
- which task(s) to harden: the new task line(s), a finding ID from the
  Review Findings Log (e.g. `SIMP-002`, `SEC-001`, `MED-001`), or the
  source command / disposition that added them.

If the target task(s) cannot be identified, ask once — do not silently
fall back to re-hardening the whole plan.

### What scoped mode does
- **Read full plan context, harden only the named task(s).** Read the
  whole plan — `Goal`, `Agreed Scope`, `Design Decisions`, `Critical
  Constraints`, `Integration Notes`, the adjacent tasks, and `Validation
  / Verification` — plus the real code the new task(s) name. The
  addition must fit the existing plan's decisions and constraints; never
  harden it blind. Only the named task(s) are rewritten or expanded —
  existing tasks and their progress markers are left untouched.
- **Consult the design doc for UI-touching added task(s).** When any
  named task builds or changes UI, also read `docs/design-system.md` —
  or the design doc named in `AGENTS.md`'s Subsystem Documentation —
  when one exists, and anchor the task's UI expectations on its
  recorded cues (scoped mode skips the full pass's grounding walk, so
  this consult is explicit here).
- **Run the scope-aware critique on the new task(s) only** (see the
  Scoped-mode notes on Steps 1, 1.5, 3, and 3.5 below), proportional to
  the addition's size and risk (see Proportional depth).
- **Write in place via Step 6's Update-in-place path.** Reuse the
  existing-file, section-by-section edit; preserve all untouched content
  and task markers. Do NOT recreate the skeleton or rewrite the file.
- **Skip the full-pass-only ceremony.** Skip the Step 0 Executor
  Capability Gate re-ask (inherit the `Executor tier:` the in-flight
  plan already records; only flag if a new task plainly needs premium
  while the plan is `entirely premium`), and skip Step 4 (feature-name
  suggestion) and Step 5 (existing-file check) — the file and name
  already exist. Steps 7 (save) and 8 (handoff) still apply, scoped to
  confirming the in-place update.

### Proportional depth
Match effort to the size and risk of the addition:
- **Fast path** — a single trivial added task (localized, low-risk: a
  copy fix, a one-line guard, routing one call through an existing
  helper — a pattern-shaped addition is multi-surface by construction
  and never fast-path eligible; see the Step 1.5 Scoped-mode note) gets
  a bounded checklist instead of the full critique:
  re-read the new task(s) + the adjacent tasks + `Critical Constraints`
  + `Design Decisions` + the `Validation / Verification` line, confirm
  the task is self-contained per the Task Specification Standard and
  correctly ordered, and SKIP the subagent fan-out and the full
  Coverage / Practicality / Simplicity critique — unless the checklist
  surfaces a risk, in which case escalate to the full scoped critique.
- **Full scoped critique** — multiple added tasks, any MED+ severity, or
  a cross-cutting / substantial addition gets the full scope-aware
  Coverage / Practicality / Simplicity critique (Step 1.5), still
  limited to the new task(s) and their interaction with the existing
  plan.

### No-recursion guard (runs once)
Scoped mode does not nest:
1. **Own findings are not re-scoped.** If hardening the named task(s)
   surfaces its own substantial follow-on finding, log it / add it as a
   task per the normal disposition — but do NOT launch a further scoped
   `/review-plan` on that finding within this run. Scoped mode runs
   exactly once per invocation.
2. **A full-plan pass hardens its own `Include in plan` tasks in-pass.**
   When `/review-plan`'s OWN Step 3.5 Deferral Confirmation Gate records
   an `Include in plan` task during a normal FULL-plan pass, that task is
   hardened by that same full pass — it does NOT trigger a nested scoped
   sub-invocation. The scoped hook exists for dispositions recorded by
   OTHER commands against an already-hardened plan, not for a full pass
   amending itself.

## Step 1 — Reconciliation pass
Compare the approved plan against:
- the original planning discussion
- the actual code and docs

Look specifically for:
- anything discussed but missing from the plan
- anything included in the plan that conflicts with the discussion
- anything included in the plan that conflicts with the actual code or documented subsystem behaviour
- ambiguities that would force a fresh session to rediscover material context
- a choice that was discussed but deferred, or recorded as an Accepted
  Assumption, that should instead be hardened into a `[decision]` task
  (decided at execution time) — and conversely a `[decision]` task that
  is actually resolvable now
- simpler, safer, or more consistent approaches than the current plan

**Scoped mode:** reconcile only the newly-added task(s) against the
planning discussion, the real code, and the existing plan's `Design
Decisions` / `Critical Constraints` — confirm the addition fits and is
correctly ordered; do not re-reconcile the untouched tasks.

## Step 1.5 — Critique Gate (required)
Do a short adversarial review before finalising anything.

Check:
- does the plan risk scope creep?
- are any edge cases, caller impacts, integration risks, validation gaps, or deployment risks still open?
- are schema, migration, config, or environment changes fully captured?
- would a fresh session need to rediscover anything material to execute this safely?
- does the plan conflict with the original planning discussion?
- does the plan conflict with the codebase or subsystem docs?
- if `Executor tier: fast/medium involved` is recorded (from Step 0), are tasks that need premium (concurrency, auth, schema migrations, hook ordering, final UX polish) explicitly labelled `[executor: premium-only]`?

**Named critique lenses (Coverage / Practicality / Simplicity).** Run
these three lenses explicitly so the scattered checks above are
auditable rather than ad hoc:
- **Coverage** — does the task list actually deliver the `Goal` and
  every `Agreed Scope` item, with no goal-implied work left unlisted?
  Are all edge cases, caller impacts, integration points, validation
  gaps, and schema / migration / config / deployment changes captured
  (plus premium-only labels when a `fast/medium` executor is recorded)?
- **Practicality** — are the steps buildable as written, in a safe
  dependency order, and grounded in the real code? Name any material
  context a fresh session would have to rediscover, and flag steps that
  will not survive contact with the named files. Is any Accepted
  Assumption or discussed-but-deferred choice really a genuinely-uncertain
  decision that should be a `[decision]` task resolved at execution time
  — and conversely, is any `[decision]` task actually resolvable now and
  better decided during planning?
- **Simplicity** — is there a materially simpler, safer, or more
  consistent approach that still meets the `Goal`? If so, name it
  concretely and route it into Step 2 under "Simpler / Safer
  Alternative".
State the result of each lens (even if "no issue") so the gate is
auditable.

If you find a real issue:
- raise it now before finalising the plan
- ask clarifying questions only if the issue materially changes implementation
- if the issue can be resolved without user input, refine the plan directly
- make sure any surviving risk is captured in the final plan, not left only in the conversation

**Scoped mode:** run the three named lenses against the new task(s) and
their fit with the existing plan only. On the fast path (a single
trivial added task) skip this gate unless the fast-path checklist
surfaced a risk. For a **pattern-shaped addition** — the new task names
an *instance* of a broader convention (one dropdown made consistent,
one column made sortable; smoke-feedback batches routed here by
`/execute-loop` are typically this shape) — the Coverage lens
enumerates the sibling surfaces app-wide: find every other surface the
same pattern touches and fold them into the hardened task(s), or record
why a surface is exempt, so the addition covers the pattern rather than
just the named instance.

## Step 2 — Show proposed adjustments before writing
Before saving the final plan, present a concise adjustment summary using this format:

### Proposed Adjustments
- [adjustment]
- Why: [reason]
- Source: [discussion / code-docs / critique gate]

Group adjustments under these headings where relevant:
- Missing from Discussion
- Missing from Plan
- Conflicts with Discussion
- Conflicts with Code / Docs
- Added for Fresh-Session Handoff
- Validation / Deployment / Migration Additions
- Simpler / Safer Alternative

If no meaningful adjustments are needed, say so explicitly and proceed.

## Step 3 — Interactive clarification and assumption check
Before saving the hardened plan, do a final interactive clarification pass.

1. Separate what is known from what is assumed.
For each significant implementation decision in the plan:
- mark whether it is grounded in code, docs, or the planning discussion (fact)
- or whether it is an inference or assumption that has not been explicitly confirmed

2. Summarise the remaining uncertainties briefly under:
- Assumptions to confirm
- Ambiguities to resolve
- User preference decisions
- Open questions introduced by the user

3. Ask the user the highest-value clarification questions needed to lock the plan safely.
Use a conversational style. For example:
- "Before I lock this plan, I want to confirm a few things."
- "These are the remaining assumptions I'd like to validate."
- "I have a few follow-up questions so I don't harden the wrong plan."

Ask questions one at a time and provide your recommended answer for each. Wait for the user's response before asking the next. Walk down the design tree, resolving dependencies one decision at a time.

4. Continue asking follow-up questions as long as the answers materially affect:
- implementation
- scope
- architecture
- schema / data changes
- deployment / config
- validation / acceptance criteria
- sequencing or plan structure

Do not stop after a single follow-up batch if material ambiguities still remain.

5. After each user response, reassess whether:
- the ambiguity is resolved
- the user has introduced new constraints, questions, or concerns
- the plan should be updated before asking anything further

6. Before saving, explicitly invite any final user additions:
- "Is there anything else you want to clarify before I lock this plan?"
- "Are there any assumptions you want to confirm, reject, or change?"
- "Do you want anything else reflected in the plan before I save it?"

7. Only proceed to save when either:
- no material questions remain, or
- any remaining uncertainty is explicitly documented in the plan as an accepted assumption, open decision, or deferred item

**Scoped mode:** limit clarification to uncertainties the new task(s)
introduce; inherit already-confirmed plan-wide decisions and
assumptions without re-asking.

## Step 3.5 — Deferral Confirmation Gate (required)
Before saving the hardened plan, run a Deferral Confirmation Gate over every candidate that the about-to-be-saved plan would record as deferred, excluded-with-future-work, accepted, or retained. The purpose of this gate is to stop work from being silently deferred when a deferral would make the user's requested feature incomplete — especially for production-impacting items such as new dependencies, environment variables, migrations, deploy-side config, or dev/prod parity drift.

Headless mode. Under a headless / loop invocation (for example when driven by `/execute-loop`), dispose a candidate without a live prompt ONLY when it is AUTO-DISPOSABLE: its recommended disposition is do-the-work (`Fix now` / `Include in plan`) AND it is not production-impacting — apply the recommended disposition and log it. Everything else is MUST-PAUSE — pause and surface it for a human decision, never auto-deciding: a `Defer` / `Accept` recommendation, anything production-impacting (new dependency, environment variable, migration, deploy-side config, dev/prod parity drift), or genuine uncertainty about the item's impact. These candidates are planning artifacts (the about-to-be-saved plan's deferred, excluded-with-future-work, accepted, and retained items listed below), not severity-tagged findings — so key the branch on the do-the-work-vs-drop recommendation and the production-impact flag, not on a severity label. Interactive behaviour is unchanged — this branch fires only under a headless/loop invocation.

Candidates to gate:
- every Deferred Item in the hardened plan's `Planning Extraction Summary`
- every Excluded Item that implies future work (i.e. intentionally postponed rather than a true non-goal)
- every Accepted Assumption whose underlying question the user could resolve now rather than later
- every retained decision surfaced during Step 1 reconciliation or Step 1.5 critique gate that would otherwise go into Deferred / Excluded / Accepted without explicit confirmation

If no candidates accumulated, the gate is silent — do not fire it on an empty batch.

Do not double-prompt items the user has already explicitly resolved earlier in the planning discussion, in Step 2's Proposed Adjustments, or in Step 3's clarification pass. If the user clearly chose `Fix now`, `Include in plan`, `Defer`, or `Accept` for an item in conversation, record that disposition and skip the gate for that item.

For each remaining candidate, present one at a time using this shape:

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

Production-impact categories: new runtime dependency, new environment variable, database migration, deploy-side config change, dev/prod parity drift. Flag `yes` and name the category whenever a candidate hits one of these; flag `no` otherwise. The flag biases the recommendation toward `Fix now` or `Include in plan`; it does not force a disposition.

When choosing the **Recommended** disposition above, prefer `Fix now` or `Include in plan`, and reserve `Defer` for genuinely large or out-of-scope work; recommend `Accept` only when there is no benefit to fixing or a net downside.

Wait for the user's reply before moving to the next candidate. Apply the chosen disposition before continuing:
- `Fix now` — resolve the item during this hardening pass, then update the reconciliation so the resolution appears in Agreed Scope or Key Design Decisions before the plan is saved
- `Include in plan` — add the item as a new task in Agreed Scope so it appears in the final Tasks list (during a FULL-plan pass this task is hardened by THIS same pass — it does NOT trigger a nested scoped `/review-plan`; see the Scoped-mode no-recursion guard, case 2)
- `Defer` — keep the item in Deferred Items with a `Risk if deferred:` tag (security / correctness / ux-degradation / blocked-work / minor) and a `Revisit by:` date or trigger string
- `Accept` — record the item under Accepted Assumptions or Excluded Items with the user-supplied rationale and no follow-up action

If the user aborts the gate mid-flow, do not save the hardened plan with the pending dispositions applied. Pending state lives only in the conversation until the gate completes. Only finalise the hardened plan once every gated candidate has a recorded disposition or the user explicitly closes the gate.

Use `Accept` as the audited no-follow-up option; do not introduce an `Ignore` disposition.

Only proceed to Step 4 once every candidate has a recorded disposition.

**Scoped mode:** gate only the candidates the new task(s) introduce.
Per the no-recursion guard, scoped mode runs once — an `Include in
plan` task recorded here is hardened within this same scoped run, not
via a further nested scoped invocation.

## Step 4 — Suggest a feature name
Suggest 3 short lowercase kebab-case names derived from the feature goal.

Examples:
- stripe-webhook-handler
- payment-webhook
- stripe-integration

Ask me to choose one or provide my own.
Sanitise the chosen name automatically: lowercase, hyphens only, no spaces or special characters.

## Step 5 — Check for an existing saved plan file
Check whether `.cursor/plans/plan-[chosen-name].md` already exists.

If it DOES exist:
- show me the existing plan's goal and current progress percentage
- present **Update existing saved plan in place** as the default path
- explain that this is the expected option when the native draft refers to the same feature
- present Rename only as an exception for:
  - a genuinely different feature
  - a deliberate follow-up split
  - a case where the current saved filename is misleading

Suggested wording:
"A saved plan already exists for this feature. Update it in place? (default)
Only rename if this is genuinely a different feature or a deliberate follow-up split."

Do not present Update / Rename / Cancel with equal visual weight when Update is clearly the likely correct path.

Options:
  1. **Update** — revise the existing plan in place using this hardened version (default)
  2. **Rename** — keep the existing plan and choose a different name
  3. **Cancel** — stop here and change nothing

If I choose Rename, go back to Step 4.
If I choose Cancel, stop and confirm nothing changed.

## Step 6 — Write the hardened execution plan
Requirements:
- no extra scope beyond what was confirmed
- include key findings and integration notes so a fresh session can understand the reasoning without re-exploring the codebase
- include enough durable context that a fresh session, review session, or testing session can continue without rediscovering the core reasoning
- include only code-verified findings; do not paste raw exploration notes or speculative ideas
- document design decisions with reasoning and rejected alternatives
- keep the `Current State / Handoff Note` short and operational
- modular steps with clear task order
- include progress tracking using:
  - 🟥 To Do
  - 🟨 In Progress
  - 🟩 Done

### Task Specification Standard

Each task in the `Tasks` section must be written so it can be implemented without cross-referencing more than one other plan section.

For each task, include inline or as one-line sub-bullets:
- the specific file(s), symbol(s), or route(s) the task touches
- the expected behaviour or output once the task completes (one sentence)
- a pointer to the relevant Design Decision, Critical Constraint, or Integration Note only if the task is not locally obvious from the task wording itself
- whether the task includes its own verification step, or defers to the plan's Validation / Verification section

Rules:
- prefer concrete file paths and symbol names over general descriptions ("edit `src/webhooks/stripe.ts` `handleEvent`" rather than "update the webhook handler")
- do not embed pseudo-code or implementation detail that will be wrong the moment the executor reads the real file — keep task specs grounded in what the code should *do*, not how to write it
- do not duplicate content already in Design Decisions, Integration Notes, or Critical Constraints — point to it instead
- if a task genuinely cannot be made self-contained, split it into smaller tasks that can
- tasks that are obviously trivial (single-line config changes, renaming a variable) do not need the full structure — use judgment

The goal is that any executor — fast or premium — can implement each task by reading the task plus at most one referenced section, without needing to reconstruct intent from the whole plan.

Decision-point tasks (optional): when a genuinely-uncertain choice
cannot be made well until execution reduces the uncertainty, you MAY
record it as a `[decision]`-labelled task instead of forcing it into an
Accepted Assumption. Its deliverable is a recorded decision, not code,
and `/execute` treats it as an intentional, planned hard-stop. Shape it
with `Options:` plus an optional `Decide after:` and an optional
`Blocks:` note, placed AFTER the tasks that resolve the uncertainty and
BEFORE the tasks that consume the decision (see the plan template's
`Tasks` section). Keep them rare and optional — prefer deciding a choice
now when you can, and use a `Defer` for work that belongs to a later
plan. A decision point is IN-SCOPE work resolved during THIS execution,
distinct from a `Defer`, which pushes work to a later plan.

Hardening stage (optional, for large plans): when hardening a large
executable plan, consider adding a Hardening stage near the end of the
task list — `/review-loop` → `/simplify` → `/security-review` → route
findings (trivial → `/fix`; substantial → scoped `/review-plan`) →
final re-review — as documented in the plan template's `## Tasks`
section. It belongs on the executable stage / feature plan, not a master
coordination plan (use a child hardening-stage plan for a master). Keep
it optional and proportional.

Make sure the saved plan's `Planning Extraction Summary` is complete and reconciled against:
- the approved native plan
- the original planning discussion
- the actual code / docs findings

Use the exact structure from:
`.cursor/templates/implementation-plan-template.md`

Do not simplify or substitute a different format.

The content should reflect:
- the approved native plan
- the original planning discussion
- the reconciled code/doc findings
- the critique gate adjustments

### Skeleton-first incremental write
Write incrementally rather than composing the whole file in one pass:
- for a NEW plan file (no existing saved plan, or a Rename to a new name in Step 5): first write the full section skeleton — every heading from `.cursor/templates/implementation-plan-template.md`, in order — then fill and verify one section at a time
- for the Step 5 **Update in place** path (the default when a saved plan already exists): edit the existing file section-by-section in place; do NOT recreate the skeleton or rewrite the whole file — preserve task progress markers and existing content this hardening pass does not touch

Either way, populate / reconcile `Planning Extraction Summary` first, then the remaining sections.

## Step 7 — Save the plan
1. Create `.cursor/plans/` folder if it does not already exist
2. Save the hardened plan to `.cursor/plans/plan-[feature-name].md`
3. Confirm the saved file path to the user
4. If a `.cursor/plans/explore-*.md` scratch was consumed as a planning source in Step 0.5, offer to delete that one file now — an explicit prompt the user must accept; never delete automatically, and never touch any other scratch. If the user declines, leave it in place.
5. Summarise the most important adjustments that were added during review
6. Tell the user whether the plan now looks ready for `/execute`
7. For non-trivial plans, recommend an independent plan-aware
   `/peer-review` (`$peer-review` in Codex) before `/execute` — ideally
   run in a different model family for the cross-family catch-rate.
   Non-trivial = the plan involves schema or migrations, concurrency,
   auth / permissions, multi-screen UI, or records `Executor tier:
   fast/medium involved`. For a small, low-risk plan, say an
   independent peer review is optional.

## Step 8 — Canonical plan handoff
The hardened saved plan in `.cursor/plans/plan-[feature-name].md` is now the single source of truth for execution.

Tell the user:
- this hardened saved plan replaces any native draft for the purposes of `/load-plan` and `/execute`
- if an earlier saved plan for the same feature was updated in place, that file remains canonical
- if the original native draft still exists in Cursor's plan panel, it may be kept as reference or deleted — it is not the execution plan

Do not leave the user with two active execution plans pointing at the same feature without explicitly explaining which one is canonical.

Execution-pathway handoff (the mirror of `/load-plan`'s Continue split): for a **loop-suitable** saved plan — an executable feature/stage plan with buildable tasks — name both pathways by their literal commands: `/execute` (single-session build) or `/execute-loop` (multi-phase autonomous run; its setup wizard runs first). A **coordination MASTER** whose buildable tasks live in stage child plans is never offered `/execute` or `/execute-loop` — point at selecting (or creating) the stage child plan instead. A saved plan that is neither loop-suitable nor a master (rare) is handed off with the single `/execute` pathway only.

Menu-selection consent (locked skills): a user's explicit selection from this offered handoff COUNTS as explicit invocation of the selected workflow — including the locked, explicit-invocation-only `/execute-loop`: on selection, read that skill's file from disk and follow it verbatim. The lock still bars model-INITIATED invocation — no selection, no invocation; every offered option prints its literal slash command; frontmatter and `agents/openai.yaml` policies are unchanged by this rule.

This is still planning only.
Do not implement anything yet — presenting the pathways authorizes nothing until the user explicitly selects one.
