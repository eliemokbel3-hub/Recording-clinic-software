---
name: load-plan
description: Load a previously saved plan from .cursor/plans/ and resume work or review progress. Shared Cursor/Codex/Claude Code workflow; invoke as /load-plan in Cursor or Claude Code, or $load-plan in Codex.
disable-model-invocation: false
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/load-plan` in Cursor or Claude Code, or `$load-plan` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

This workflow reads and writes the same `.cursor/plans/` files as Cursor and Claude Code, so no copy-paste handoff is needed when switching tools.

## Step 1 — Find available plans
Search `.cursor/plans/` for `plan-*.md` files.
Exclude anything inside `.cursor/plans/completed/`.

Before listing, summarising, or selecting any plan, check for base-side isolation registries — `.cursor/loops/*-isolation` intent-journal files written by `/execute-loop`'s run-isolation contract. A live registry whose recorded authority is a run WORKTREE means the base copy of that plan is stale: redirect the plan read to the registry's recorded authoritative plan path, surface the isolation state (run branch, worktree path, journal state) alongside the listing, and never present the base copy as current merely because it exists. When the authoritative worktree lies outside this session's workspace, print the exact reopen/continue-in-worktree handoff (the recorded worktree path + how to resume there) instead of a stale-base summary. Validate the registry against the current base/worktree relationship (`git worktree list`, refs) before following it; on a stale or ambiguous registry, refuse to guess and ask.

Classify each saved plan by its `Lifecycle State`:
- Active
- Completed — Follow-ups Retained
- Completed — Archivable
- Unknown / missing state

If no plan files are found:
- tell the user no saved plans were found
- suggest native Plan Mode first, or `/explore` followed by `/create-plan`
- stop here

## Step 2 — Present the list
Present plans in two groups:

### Active Plans
Normal in-progress execution plans.

### Completed Plans With Retained Follow-Ups
Completed feature plans that still hold actionable deferred / excluded / assumption follow-up context.

For each plan file found, read and extract:
- feature name
- Goal summary
- Lifecycle State
- Overall Progress percentage
- how many tasks are 🟩 Done vs 🟥 To Do vs 🟨 In Progress
- whether the plan includes:
  - Critical Constraints
  - Validation / Verification
  - Schema / Data Changes
  - Config / Environment / Deployment Impact
  - Retained Follow-Up Items
  - Plan Lineage

If a plan is `Completed — Follow-ups Retained`, show that label clearly in the list.

If a plan has a parent plan or follow-up plans in `Plan Lineage`, show that relationship directly in the plan list.

Examples:
- `plan-auth-followup-1.md` (follow-up from `plan-auth.md`)
- `plan-auth.md` — Completed — Follow-ups Retained → `plan-auth-followup-1.md`

Do not keep lineage as hidden metadata only — surface it so the user can understand the relationship without opening every plan.

Ask the user to choose a number, or type `cancel` to exit.

## Step 3 — After selection
If the selected plan is **Active**:
- read the full contents of the chosen plan file
- **detect plan schema:** read the `Planning Extraction Summary` for a `Workflow Schema:` line. If present, the plan is v22 (or later); enable the v22 surfacing below. If absent, the plan is pre-v22 / legacy; skip the v22 surfacing.
- check for consistency:
  - if all tasks are 🟩 but progress is not 100%, flag the mismatch
  - if progress is 100% but unfinished tasks remain, flag the mismatch
  - if a completion timestamp exists, tell the user the plan appears complete
  - if the `Current State / Handoff Note` clearly conflicts with task markers, flag the mismatch
- show the user in this order:
  1. Goal
  2. Current State / Handoff Note
  3. Key Findings summary
  4. Design Decisions
  5. Critical Constraints
  6. Validation / Verification
  7. Schema / Config / Deployment impact (if present)
  8. Task progress summary
  9. Current 🟨 task, otherwise next 🟥 task; plus, from a scan of the `Tasks` section, the count and titles of any unresolved `[decision]` tasks ("N unresolved decision point(s)") so the user sees what choices the plan is waiting on. Display-only and NOT schema-gated — this Tasks-section scan works on any plan regardless of `Workflow Schema:`, so it stays here at item 9 rather than under the v22-only item 10.
  10. **v22-only:** Executor tier (suppressed at default `entirely premium`); non-minor risk-tagged retained-item summary; overdue Revisit-by-date count; security/correctness risk-tagged prominent warning. Same surfacing rules and visual cues as `/start-session`'s v22 plan-state surfacing block. None block; all are display + nudge. Warnings fire on tag presence (the retained-item schema preserves tag, not source severity).

Then ask what they would like to do. The Continue option is shaped by the plan itself:

For a **loop-suitable** plan — an executable feature/stage plan with buildable tasks — split Continue into the two execution pathways:
  1. Continue — run /execute to resume building from where the plan left off (single-session)
  2. Continue autonomously — run /execute-loop for a multi-phase autonomous run (fresh per-phase executors, reviews, cross-family peer passes; its setup wizard runs first)
  3. Review — show the full plan in detail
  4. Run /document first — refresh durable docs and sync the plan before continuing
  5. Cancel — exit without doing anything

For a **coordination MASTER** plan — one whose buildable tasks live in stage child plans — never offer /execute or /execute-loop on the master itself; offer a stage-selection pointer instead:
  1. Open a stage — list the child/stage plans from Plan Lineage and load the chosen one
  2. Review — show the full master plan in detail
  3. Run /document first — refresh durable docs and sync the plan before continuing
  4. Cancel — exit without doing anything

For an Active plan that is NEITHER loop-suitable NOR a coordination master (rare — no buildable tasks, e.g. decision-only), present the loop-suitable menu WITHOUT the /execute-loop option, renumbered — the single-session Continue shape.

Menu-selection consent (locked skills): a user's explicit selection from this menu COUNTS as explicit invocation of the selected workflow — including a locked, explicit-invocation-only one such as `/execute-loop`: on selection, read that skill's file from disk and follow it verbatim. The lock still bars model-INITIATED invocation — no selection, no invocation; every menu option that would invoke a workflow prints its literal slash command; frontmatter and `agents/openai.yaml` policies are unchanged by this rule.

If the selected plan is **Completed — Follow-ups Retained**:
- **detect plan schema:** read the `Planning Extraction Summary` for a `Workflow Schema:` line. If present, the plan is v22; surface each retained item's `Risk if deferred:` tag and `Revisit by:` date when presenting them below. If absent, the plan is pre-v22; retained items won't have these fields — present them as-is.
- present:
  - the original feature goal
  - confirmation that main implementation is complete
  - summary of retained follow-up categories:
    - actionable deferred items
    - excluded items worth revisiting
    - accepted assumptions to revalidate
  - **v22-only:** for each retained item with a `Risk if deferred:` field, surface the tag (security / correctness / ux-degradation / blocked-work / minor) and one-line explanation. For each item with a `Revisit by:` field, surface the date or trigger string; flag dates in the past as `OVERDUE`.
  - the Follow-Up Continuation Notes
  - the Plan Lineage

Then ask:
1. Continue now — create a new follow-up execution plan and carry forward the relevant retained context
2. Review retained follow-up items only
3. No action now

If the user chooses Continue now:
- ask which retained items should be included now, unless the choice is already obvious
- create a new saved plan such as:
  `.cursor/plans/plan-[feature]-followup-1.md`
- if a follow-up file for this feature already exists, increment the suffix:
  `followup-2`, `followup-3`, etc.

Carry forward only the relevant retained context, not the entire old task list.

Minimum carry-forward checklist:
- original feature goal (as background, not as the new goal)
- relevant deferred items that now become the new task list
- key constraints and design decisions that still apply
- findings that a fresh session must not rediscover
- what is explicitly still out of scope for the follow-up
- any accepted assumptions that still need later validation

The new follow-up plan must get its own fresh `Planning Extraction Summary`:
- `Agreed Scope` = only the retained items selected for this follow-up
- `Deferred` = empty unless something is explicitly re-deferred during follow-up planning
- `Excluded` = only exclusions relevant to this follow-up
- `Accepted Assumptions` = inherit only if still applicable
- `Key Design Decisions` = inherit only the still-applicable ones from the parent

Update plan lineage:
- parent plan gets:
  `Follow-up plans: plan-[feature]-followup-1.md`
- follow-up plan gets:
  `Parent plan: plan-[feature].md`

Keep the original completed plan unchanged as the historical context source unless the user explicitly wants it updated.

If the user chooses Review retained follow-up items only:
- show them clearly and stop
- do not create a new plan

If the user chooses No action now:
- confirm nothing was changed
- leave the retained-complete plan in place
