---
name: execute
description: Build the approved saved plan step by step within agreed scope. Use after /review-plan or /create-plan. Shared Cursor/Codex/Claude Code workflow; invoke as /execute in Cursor or Claude Code, or $execute in Codex. Side-effecting.
disable-model-invocation: false
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/execute` in Cursor or Claude Code, or `$execute` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

This workflow is side-effecting but agent-invocable: Cursor uses `disable-model-invocation: false` and Codex uses `agents/openai.yaml` with `policy.allow_implicit_invocation: true`, so an agent may invoke it automatically (for example inside a loop) and you can still invoke it explicitly. Safety comes from this workflow's in-skill gates rather than from invocation-locking.

If running in Codex or Claude Code, execution uses the model configured in the CLI or IDE extension. For `[executor: premium-only]` tasks, hard-stop once and ask the user to confirm they are on the intended higher-tier model before continuing; do not use Cursor's fast/medium return prompt in Codex or Claude Code.
Plan files are shared across all three tools. Handoff is through disk state, the plan file, and git, not conversation memory.

Implement the confirmed plan carefully.

Before starting:
- locate plan files in `.cursor/plans/` — look for `plan-*.md` files (exclude `.cursor/plans/completed/`)
- if no plan file exists, suggest the user run /load-plan to find an existing plan, or use native Plan Mode followed by /review-plan, or /create-plan to create one
- if multiple plan files are found, present a numbered list with feature name and progress percentage, and ask the user to choose one before proceeding
- read the plan's `Lifecycle State`
- if the selected plan is `Completed — Follow-ups Retained`, do not resume it like a normal active execution plan
  - instead, tell the user the main implementation is already complete and ask whether to create a follow-up plan now or review retained items only
- read the full plan file to understand:
  - goal
  - key findings / integration notes
  - design decisions already made
  - critical constraints
  - schema / data changes
  - config / environment / deployment impact
  - validation / verification steps
  - deferred / out-of-scope items
  - current state / handoff note
  - current progress
- consult `docs/lessons.md`, if it exists, for recurring project gotchas relevant to the plan's area
- identify the current 🟨 task if one exists, otherwise the first task still marked 🟥
- if another top-level task is already marked 🟨, do not start a second one unless the plan explicitly marks those tasks as parallel-safe
- if the plan does not explicitly allow parallel work, finish, pause, or re-mark the existing 🟨 task before proceeding

## Default execution mode — continuous until a hard stop

After the plan is selected, continue executing tasks in order by default.

Do not stop after every successfully completed task just to ask whether to continue.

For each task:
1. mark the task 🟨 before starting
2. implement only that task's approved scope
3. run the relevant verification for that task
4. update the plan file on disk
5. mark the task 🟩 only when verified
6. write a short rolling checkpoint in the conversation
7. immediately continue to the next eligible 🟥 task

Exception — decision-point tasks: a task labelled `[decision]` is not
built. Detect it at selection (before step 1) and handle it as a
planned hard-stop (Hard-stop condition #1, "Decision-point tasks") —
present the choice, wait, then record the decision and mark it 🟩.
Skip the build/verify steps (2–3) for it.

A rolling checkpoint is not a stop. It should be brief:
- task completed
- verification run / result
- plan updated
- next task starting

Only stop and wait for the user in the hard-stop conditions below, or
pause-and-offer at the recommended checkpoints.

## Hard-stop conditions

Stop and wait for the user only when one of these applies. Implementation does not resume until the user replies.

1. **User decision needed**
   - scope is ambiguous after re-reading the plan and the relevant code
   - the plan conflicts with the actual code
   - a product or design choice is required that the plan did not lock in
   - implementation would require expanding scope (apply the
     severity-aware scope-expansion routing matrix below before
     hard-stopping)
   - a task cannot be implemented as written, is unnecessary because
     the code already handles it, or needs to be reordered or split
     based on something discovered during implementation

   Don't trigger this for stylistic preference, naming choices, or
   details a careful re-read of the plan and code would resolve.
   Re-read first; ask only if the answer materially affects implementation.

   **Decision-point tasks (planned `[decision]` hard-stops).**
   A task labelled `[decision]` is an intentional, planned hard-stop
   whose deliverable is a recorded decision, not code. Detect the label
   at task selection, BEFORE marking the task 🟨 (see the pre-🟨 checks
   further below). Do not implement anything for it. Instead:
   - present the framed choice: the task's `Options`, any `Decide after:`
     condition, and the relevant context discovered so far during
     execution
   - wait for the user's choice — this is a hard-stop; execution does
     not resume until the user replies
   - on the user's decision: record `Chosen: <option> (YYYY-MM-DD);
     rationale: <one line>` onto the task, mark it 🟩, update the
     `Current State / Handoff Note`, and continue to the next task
   - if the user is not ready to decide (defers or splits the decision,
     or needs more information): never auto-pick an option. Leave the
     task unresolved (🟥, or 🟨 if it was partially explored), record the
     open question under the handoff note's open blockers, and either
     stop or adapt the plan (the adapt-the-plan rule below)
   - if the chosen option changes downstream tasks, adapt the plan first
     (the adapt-the-plan rule below); if the decision is architecturally
     durable, also record it under `Design Decisions` (the
     durable-reasoning rule below)
   - dependent ordering is handled by task order plus the existing
     "needs to be reordered or split" hard-stop above: the planner
     places a `[decision]` task before its dependents, and an optional
     `Blocks:` note on the task is a human-readable aid, not
     machine-enforced
   - a decision-point hard-stop is a natural pause point, so flush any
     pending Deferral Confirmation Gate batch here per the gate's
     natural-pause-point rule
   - headless mode: under a headless / loop invocation, a `[decision]`
     task is MUST-PAUSE — it still hard-stops for the user and a decision
     is never auto-picked — UNLESS the plan has pre-recorded the choice on
     the task (a `Chosen:` line), in which case record it and proceed. The
     rest of the decision-point flow is unchanged.

   **Scope-expansion during execution (v22 severity-aware routing).**
   When scope expansion surfaces DURING execution (not during /review),
   apply the same severity-aware routing matrix that /review uses,
   classifying severity by impact:
   - **CRIT** (auth/security/correctness regression; would break a
     stated invariant) → hard-stop and prompt the user with 3 options:
     (i) Amend plan now and continue (harden the added task with a
     proportional scoped `/review-plan` before building it — see
     `/review-plan`'s **Scoped mode**); (ii) Downgrade severity if
     reclassification on closer look is justified; (iii) Defer with
     explicit `Risk if deferred:` tag (security or correctness),
     captured as a Retained Follow-Up Item before continuing execution.
   - **HIGH** (significant correctness/UX impact; touches a non-trivial
     subsystem) → hard-stop and prompt the user with 3 options:
     (i) Fold-in (apply within current task); (ii) Open follow-up
     (capture as Deferred — Actionable Later with `Risk if deferred:`
     tag, mandatory MED+); (iii) Retained with explicit `Risk if
     deferred:` value.
   - **MED** → accumulate as a pending Deferral Confirmation Gate
     candidate (see the dedicated section below); do NOT silently
     record as `Deferred — Actionable Later`; continue execution and
     present the candidate at the next natural pause point. The
     recommended disposition is `Include in plan`, reserving `Defer`
     for genuinely large or out-of-scope work. The user's gate
     disposition (`Fix now` / `Include in plan` / `Defer` / `Accept`)
     determines whether the item becomes a new task, a `Deferred —
     Actionable Later` entry with a `Risk if deferred:` tag, or an
     Accepted Assumption / Excluded Item with rationale.
   - **LOW** → accumulate as a pending Deferral Confirmation Gate
     candidate alongside MED items; do NOT silently capture as a
     Retained Follow-Up Item; present at the next natural pause point.
     LOW defaults to `Fix now`; recommend `Accept` only when there is
     no benefit to fixing or a net downside. `Include in plan` /
     `Defer` remain available at the gate.

   The Deferral Confirmation Gate replaces the prior MED-silent-default
   and LOW-silent-capture behaviour. The gate is batched at natural
   pause points (recommended-checkpoint, hard-stop, or end-of-plan),
   not fired mid-task for every candidate, to avoid prompt fatigue
   while preventing silent deferrals. The CRIT/HIGH hard-stop contract
   is preserved unchanged — those continue to interrupt execution
   immediately. If no MED/LOW candidates have accumulated by the next
   pause point, the gate is silent — empty batches do not fire.

2. **Premium boundary**
   - entering a `[executor: premium-only]` task
   - in Cursor: hard-stop and ask the user to confirm a premium model is active before marking the task in progress
   - in Codex: hard-stop once and ask the user to confirm the CLI or IDE extension is on the intended higher-tier model before continuing
   - leaving a contiguous premium-only block and returning to default tasks in Cursor only; Codex has no fast/medium return prompt inside this workflow

3. **Verification failure**
   - the same relevant test, build, typecheck, or targeted verification
     fails twice on the current task
   - after two failed verification attempts, hard-stop before continuing
   - in Cursor: recommend escalating to a premium model before retrying
   - in Codex: suggest `/model` to switch to a higher-tier model if available, or switch to Claude Code / Cursor for a fresh attempt
   - do not escalate based only on vague difficulty, uncertainty, or a
     feeling that the task is complex

4. **Safety boundary** (stop before applying, not after)
   - destructive database migration
   - production-impacting config or deployment change not already
     approved in the plan
   - secret or environment variable uncertainty
   - risky git operation (force push, history rewrite, branch deletion
     with unmerged work)

5. **Context / handoff**
   - context window is filling and the next task would be safer in a
     fresh session
   - before recommending a session reset or model switch

6. **Plan-mandated review pause**
   - the plan file explicitly marks a `/review` / `$review` pause point at this position

7. **Completion handoff** (triggers the completion-state decision pass below, not a single-reply wait)
   - no 🟥 or 🟨 implementation tasks remain
   - all in-scope tasks are 🟩 or explicitly deferred / out of scope

## Recommended checkpoints — pause and offer

These are soft checkpoints, not hard stops. Pause briefly, state the
recommendation, ask whether to run it now or continue, and accept
either answer.

Do not silently skip past them, but do not treat them as blocking
implementation decisions unless the user chooses to run the recommended
action.

Trigger conditions:
- a logical phase boundary in the plan is complete and the next phase
  depends on this one being correct
- 3–5 meaningful tasks have completed on a medium/large feature
  without a review pass
- a task that changed schema, auth, permissions, payments, transactions,
  locking, migration, or shared invariants has just completed
- UI-bearing work has reached a point where final UX polish would be
  expensive to redo later
- the plan was materially adapted during execution
- verification passed, but the agent can name a concrete structural
  risk that tests may not cover

At a recommended checkpoint, briefly state what was done and the
recommended action (usually the matching review workflow: `/review` in Cursor or `$review` in Codex). If the user says continue,
record that the checkpoint was deferred and do not re-ask for the
same checkpoint category until a materially new phase, risk, or
review trigger appears.

If one or more Deferral Confirmation Gate candidates have accumulated
by the time a recommended checkpoint is reached, process the gate
batch before returning to execution — see the dedicated section
below.

## Deferral Confirmation Gate — batched at natural pause points

When MED or LOW scope expansion surfaces during execution, accumulate
the candidate as a pending Deferral Confirmation Gate item rather
than silently recording it. Do not interrupt mid-task for every
candidate — present the accumulated batch at the next natural pause
point.

Headless mode. Under a headless / loop invocation (for example when driven by `/execute-loop`), dispose a candidate without a live prompt ONLY when it is AUTO-DISPOSABLE: its recommended disposition is do-the-work (`Fix now` / `Include in plan`) AND its severity is LOW or MED AND it is not production-impacting — apply the recommended disposition and log it. Everything else is MUST-PAUSE — pause and surface it for a human decision, never auto-deciding: `Defer` / `Accept`, any CRIT or HIGH, anything production-impacting (new dependency, environment variable, migration, deploy-side config, dev/prod parity drift), a `/fix` stop-on-failure, or genuine uncertainty. Here the candidates are the MED/LOW scope-expansion items accumulated during execution. Interactive behaviour is unchanged — this branch fires only under a headless/loop invocation.

Natural pause points are:
- a recommended checkpoint (see above)
- any hard-stop that occurs for another reason
- end-of-plan, when no 🟥 / 🟨 tasks remain and the completion-state
  decision pass below is about to begin

At a pause point with one or more pending candidates, present them
one at a time using this shape:

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
- `Fix now` — apply the change immediately, then resume the
  interrupted task or pause-point handling
- `Include in plan` — append a new 🟥 task to the active plan inside
  Agreed Scope, then run a proportional scoped `/review-plan` on that
  new task before resuming execution — see `/review-plan`'s **Scoped
  mode — harden only newly-added task(s)** section (the canonical
  definition; do not restate it), biasing toward tacking onto the
  active/stage plan over a new follow-up plan
- `Defer` — record under `Deferred — Actionable Later` with a `Risk
  if deferred:` tag (security / correctness / ux-degradation /
  blocked-work / minor) and a `Revisit by:` date or trigger string;
  this becomes a Retained Follow-Up Item at plan completion
- `Accept` — record under Accepted Assumptions or Excluded Items
  with the user-supplied rationale and no follow-up action

If the user aborts the gate mid-batch, do not commit pending
dispositions to disk. Pending state lives only in the conversation
until the gate completes or the user explicitly closes the batch.
Resume execution only after the batch is fully answered or closed.

Empty batches are silent. If no MED/LOW candidates have accumulated
by the time a pause point is reached, do not fire the gate.

CRIT/HIGH scope-expansion candidates are handled by the hard-stop
contract in Hard-stop condition #1 and do not enter the gate batch —
they prompt immediately with their own three-option selection. Use
`Accept` as the audited no-follow-up option; do not introduce an
`Ignore` disposition.

## Not reasons to stop

- a task completed cleanly
- the plan file was updated
- a few files were changed
- mild uncertainty about a local implementation detail — re-read the
  relevant code first; that usually resolves it
- the next task is in a different file
- a generic "want to confirm before continuing" instinct
- the rolling checkpoint feels like a natural pause point — that's by
  design, not a signal to stop

Before implementing the selected task:
- re-read the relevant local code to confirm the referenced files, functions, routes, schemas, or components still exist and still match the plan
- check whether the task touches files, flows, or subsystems that have dedicated docs referenced from the `Subsystem Documentation` section in `AGENTS.md`
- if so, read that documentation before starting the task
- if reading that documentation reveals constraints or impacts that expand scope beyond the current plan, stop, flag it, and update the plan before proceeding
- if the task builds or changes UI, also read `docs/design-system.md` — or the design doc named in `AGENTS.md`'s Subsystem Documentation — first, when one exists, and follow its recorded cues
- if the codebase has changed enough that the plan is no longer accurate, stop, explain the mismatch, and update the plan to reflect the current codebase before continuing
- if the mismatch is trivial and does not affect scope or design, note the discrepancy in the plan and proceed
- before changing the selected task from 🟥 to 🟨, check whether it is a
  decision-point task labelled `[decision]`. If yes, do NOT implement
  code and do NOT mark it 🟨 as ordinary in-progress work — it is an
  intentional, planned hard-stop whose deliverable is a recorded
  decision. Run the decision-point flow in Hard-stop condition #1
  ("Decision-point tasks") instead.
- before changing the selected task from 🟥 to 🟨, check whether it is
  labelled `[executor: premium-only]`. If yes, hard-stop before marking
  the task in progress. In Cursor, ask the user to confirm a premium
  model is active. In Codex, say: "This task is labelled
  `[executor: premium-only]`. Codex is already running on whichever
  model your CLI or IDE extension is configured for; if you have a
  higher-tier model available, confirm you're on it before I continue.
  Reply `continue` to proceed or `pause` to switch model first."
  Do not attempt to detect the active model yourself; the human is the
  source of truth.
- if the current task has no `[executor: premium-only]` label, and the
  immediately previous completed task in this plan was labelled
  `[executor: premium-only]`, hard-stop once before marking the task
  🟨 in Cursor and tell the user: "Premium phase complete. You can
  switch back to a fast model now if you want, or stay on premium.
  Reply `continue` to proceed." Do not fire this transition warning in
  Codex; there is no fast/medium return prompt inside this workflow.
  Do not fire this transition warning when the current task is also
  `[executor: premium-only]` — that case is handled by the premium-entry
  hard-stop above, which is sufficient.
- if the same relevant test, build, typecheck, or targeted verification
  has failed twice in a row on the current task (per the failure
  definition in `project-workflow.mdc`), hard-stop. In Cursor, recommend
  escalating to a premium model and ask whether to update the task label
  to `[executor: premium-only]` before retrying. In Codex, tell the user:
  "Verification has failed twice on this task. You can try `/model` to
  switch to a higher-tier model, or pause this Skill and switch tools
  for a fresh attempt." Only update the plan label if the user confirms.
  Do not silently mutate plan labels based on agent inference. After the
  user confirms the model/tool choice, retry the task.
- if the task is still valid, update it in the plan file from 🟥 to 🟨 before starting work

Rules:
- stick to the approved scope only — the plan file is the single source of truth
- treat `Critical Constraints` and `Deferred (Out of Scope)` as mandatory
- follow existing project patterns and the integration notes captured in the plan
- write clear, maintainable code
- use comments only where they add real value
- never make drive-by changes while implementing a task. Modify only
  what the task explicitly requires. If you find yourself wanting to
  "tidy" or "improve" nearby code, stop and add it as a separate
  follow-up item — drive-by changes are the single biggest source of
  fix-induced regressions in subsequent review rounds.
- if new scope appears, apply the severity-aware scope-expansion routing matrix in Hard-stop condition #1 above — CRIT/HIGH hard-stop with explicit disposition; MED/LOW accumulate as pending Deferral Confirmation Gate candidates fired at the next natural pause point (see the Deferral Confirmation Gate section). Never silently expand the work without classifying.
- if a task cannot be implemented as written, is unnecessary because the code already handles it, or needs to be reordered or split due to something discovered during implementation:
  - explain what you found
  - propose the adaptation
  - update the plan file to reflect the approved change
  - do not silently deviate from the plan

Verification rules:
- use the plan's `Validation / Verification` section as the default checklist for what to run or check
- if the current step produces runnable or testable changes, run the relevant checks before marking it 🟩
- perform a brief manual smoke test for runnable changes when appropriate
- for scaffolding or partial steps that are not independently testable, continue only if there is a grounded reason the step is safe and complete
- never mark a task 🟩 if you have any reason to believe it is broken or could introduce regressions

As work progresses:
- treat each meaningful implementation step as a rolling checkpoint per the continuous-execution policy above — write a brief checkpoint in the conversation, then continue
- update the plan file on disk after each meaningful step — do not only update the conversation
- update task status from 🟥 → 🟨 → 🟩 in the file
- update the overall progress percentage in the file
- update `Current State / Handoff Note` in the file after each meaningful step:
  - Last completed step
  - Current in-progress step
  - Immediate next action
  - Open blockers / open questions
  - Last plan sync
- if implementation reveals new durable reasoning, add it to the relevant section of the plan concisely:
  - Design Decisions
  - Key Findings
  - Critical Constraints
  - Validation / Verification
  - Config / Environment / Deployment Impact
  - Schema / Data Changes
- if the plan includes schema, environment, migration, or deployment impact, surface those items during implementation rather than waiting until the end
- update `AGENTS.md` and `CHANGELOG.md` at meaningful milestones, not only at the very end
- flag any new environment variables or migration steps immediately
- after a successful task checkpoint, continue to the next eligible task automatically unless a hard-stop or recommended-checkpoint condition applies

Before any session switch, context reset, or handoff:
- bring the active plan file fully up to date first
- make sure `Current State / Handoff Note` reflects the real current state
- ensure any unfinished task is marked 🟨 if work has started, otherwise leave it 🟥
- do not rely on the conversation alone for the next step

When all main implementation tasks are 🟩:
- update overall progress to 100%
- add a completion timestamp to the plan file
- update `Current State / Handoff Note` to reflect that the main implementation is complete

Then do a completion-state decision pass before recommending archive/delete.

1. Review the plan's:
- Planning Extraction Summary
- Deferred / Out of Scope items
- Retained Follow-Up Items (if present)
- Accepted assumptions that may still need later action
- Excluded items that were intentionally postponed rather than true non-goals

2. Walk the `Planning Extraction Summary` line by line.
For each deferred / excluded / accepted-assumption item, classify it as one of:
- **Resolved** — completed during implementation or no longer relevant
- **Carried Forward** — still relevant, move into `Retained Follow-Up Items` with updated context
- **Superseded** — replaced by a later implementation decision
- **Re-deferred** — still valid, but intentionally postponed again after completion review

If the `Planning Extraction Summary` contains 5 or fewer total deferred / excluded / accepted-assumption items:
- present the proposed classifications inline and ask for confirmation in one pass

If it contains more than 5 total items:
- group them by category
- let the user confirm each category rather than each individual item
- only drill into item-by-item confirmation if the user questions a category-level grouping

3. Ask the user:
- Do you want to continue with any follow-up items now?
- Do you want to retain follow-up items for later?
- Or is this plan fully complete and ready for normal archive / deletion handling?

If the user chooses **Continue now**:
- identify which retained items should move into active follow-up work
- create a new saved plan such as:
  `.cursor/plans/plan-[feature]-followup-1.md`
- if a follow-up file for this feature already exists, increment the suffix:
  `followup-2`, `followup-3`, etc.

Before writing the new follow-up plan, use the carry-forward checklist:
- original feature goal as background
- relevant deferred items → new task list
- key constraints and design decisions that still apply
- findings a fresh session must not rediscover
- what remains explicitly out of scope
- accepted assumptions that still require later validation

The new follow-up plan must get its own fresh `Planning Extraction Summary`:
- `Agreed Scope` = only the retained items selected for this follow-up
- `Deferred` = empty unless something is explicitly re-deferred during follow-up planning
- `Excluded` = only exclusions relevant to this follow-up
- `Accepted Assumptions` = inherit only if still applicable
- `Key Design Decisions` = inherit only the still-applicable ones from the parent

Update lineage in both plans:
- parent plan adds the follow-up filename
- child plan records the parent filename

Set the current plan's lifecycle state to:
`Completed — Follow-ups Retained`

Tell the user the original plan remains the context source and the new follow-up plan is now the active execution plan.

If the user chooses **Retain follow-up items for later**:
- set the current plan's lifecycle state to:
  `Completed — Follow-ups Retained`
- make sure retained items are fully populated with enough context for a fresh session
- suggest `/document` for durable doc sync
- do NOT say the plan is ready for archive/delete yet

If the user chooses **Fully complete**:
- set the current plan's lifecycle state to:
  `Completed — Archivable`
- suggest running `/document` to migrate any enduring knowledge before archive/delete
- tell the user the plan can be archived or deleted once anything still unique to the plan has been migrated
