---
name: create-plan
description: Turn confirmed exploration findings into a clear implementation plan with visible progress tracking saved to .cursor/plans/. Exploration-led planning path. Shared Cursor/Codex/Claude Code workflow; invoke as /create-plan in Cursor or Claude Code, or $create-plan in Codex.
disable-model-invocation: false
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/create-plan` in Cursor or Claude Code, or `$create-plan` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

If running in Codex or Claude Code, use the current conversation, prior exploration output, or pasted planning context as the planning source. If text below mentions Cursor native Plan Mode, treat that as Cursor-only guidance.
Execution may happen later in Codex, Cursor, or Claude Code; record executor-tier assumptions for the tool the user expects to use.

Based on our confirmed discussion, write a concise implementation plan in markdown.

This command creates a new saved plan.
It does not resume or revise an existing saved plan in place — use `/load-plan` to resume, or `/review-plan` when hardening a native plan for a feature that already has a saved execution plan.

This is the exploration-led planning path.
Use it when:
- native Plan Mode was skipped
- `/explore` was used first
- deeper manual discovery is needed before planning
- you explicitly want the manual planning workflow

## Step 0 — Executor Capability Gate (required, runs first)

This gate runs BEFORE Discussion Extraction. It is unconditional: every plan must record an Executor tier in its `Planning Extraction Summary` before any plan content is written. The gate is not satisfied without a recordable answer.

If the planning conversation has not already stated this, ask:
"Will this plan be executed entirely on a premium model, or will fast
or medium-tier models be involved?"

Record the confirmed answer verbatim; it will be written to the plan's
`Planning Extraction Summary` as:

`**Executor tier:** entirely premium | fast/medium involved`

If entirely premium, skip fast-executor-specific hardening below, but
still include any specification the feature needs for correctness,
future review, fresh-session handoff, or user approval. Premium
execution reduces the need for defensive detail; it does not remove
the need for important design decisions, API contracts, permission
matrices, or UX requirements when those are central to the work. The
plan is not only for the executor — it is also for review continuity
and preventing future disagreement about scope.

**Planner/executor tier gap (within "entirely premium").** When the
answer is "entirely premium", also ask (or confirm from the
conversation) whether the plan is being authored on a HIGHER tier
than the model that will execute it — for example the plan is written
on an ultra-tier model while an Opus-class premium model executes. A
premium executor is not the planning model: judgment the planner
would apply at build time does not transfer on its own. When such a
gap exists, do not skip the fast-executor list below wholesale —
apply it selectively and at lighter dosing, prioritising locked
design decisions, an edge-case inventory, API contracts,
design-doc-anchored UI specification, and per-task acceptance
criteria; add the heavier items (microcopy dictionary, permission
matrix, files-touched manifest) only when the work itself demands
them. Record the gap as free text appended to the existing
`Executor tier:` line — no schema change, and the value MUST keep
`entirely premium` leading (downstream commands substring-check this
line; never include the literal phrase `fast/medium involved` in the
enrichment text). Worked example:

`**Executor tier:** entirely premium — planned on Fable 5; executor
Opus-class; tier-gap dosing applied (design decisions, edge-case
inventory, API contracts, acceptance criteria locked)`

Otherwise (fast/medium involved): the plan must give a fast executor
enough specification to work without inventing design, copy, or
contracts. Use your judgment about which of the following this
specific plan needs. Include the ones that apply, skip the ones that
don't, and add anything else the work needs that isn't on the list.

Common additions that help fast executors:

- Anchor patterns by file path — point at existing files the executor
  should imitate ("follow the layout of `client/src/pages/dashboard-settings.tsx`").
  This is the single highest-leverage addition for any plan with UI
  surface; do this even when nothing else on the list applies.

- Per-screen UI specification — for visual surfaces that need empty /
  loading / error / 403 states, mobile behaviour at 375 / 768 / 1280,
  or design-system anchoring beyond a single layout reference — anchor
  to the cues recorded in `docs/design-system.md`, or the design doc
  named in `AGENTS.md`'s Subsystem Documentation, when one exists.

- Microcopy dictionary — when the same kind of string appears in
  multiple places (toasts, errors, empty states, button labels).

- API contract appendix — when new endpoints need request and response
  shapes the executor would otherwise invent. Compact pseudo-Zod is fine.

- Permission matrix — when the feature has role-based UI behaviour;
  every (role × resource × action) cell with the expected result.

- Per-phase files-touched manifest — when scope creep or surface
  expansion is a real risk.

- Per-phase Definition of Done — when verification is more involved
  than running tests.

- Premium-only tasks — for work fast models reliably miss
  (cross-cutting polish, concurrency, auth, schema migrations,
  hook-ordering-sensitive UI). Where the dependency graph permits,
  cluster premium-only tasks adjacent to each other in the task list
  to reduce model-switching. Do not reorder dependencies to achieve
  clustering. The Critique Gate (Step 0.5) confirms these labels are
  in place before the plan is finalised.

The goal is specification adequacy for the executor and for downstream
review/handoff, not checklist completeness. A plan for a backend
refactor probably needs none of the above. A plan for a multi-screen
feature with role-based UI probably needs most of them. A plan for
one new endpoint and a checkbox probably needs an API contract and
nothing else.

If you find yourself adding a section because this list named it
rather than because the plan needs it, skip it. The premium model
running this gate is trusted to make these calls; the list above is
to remind you of options, not to mandate them.

These additions go in the plan's existing sections (Integration Notes,
Design Decisions, Validation / Verification, Tasks) — do not add new
top-level headings.

## Step 0.1 — Discussion Extraction (required)
Before writing any plan content, scan the current conversation and any immediately relevant prior planning context.

Extract and organise these categories:

- Agreed Scope
  - what the user confirmed should be built now

- Deferred Items
  - things discussed and explicitly postponed
  - include the reason they were deferred

- Excluded Items
  - things the user or agent intentionally left out for a lighter initial version
  - include the rationale for exclusion

- Accepted Assumptions
  - things treated as true to keep planning manageable
  - include the risk if they turn out false

- Key Design Decisions
  - decisions made during exploration that constrain implementation
  - include rejected alternatives where relevant

Rules:
- do not infer extra scope beyond what was actually discussed
- separate facts from assumptions
- if an `Exploration Summary` from `/explore` is present in the current conversation, use it as the primary extraction anchor
- also apply the **scratch-consumption rule** below — a prior `/explore` may have persisted its findings to a `.cursor/plans/explore-*.md` scratch even when the summary is no longer in the conversation
- if no summary or scratch exists, or the chosen source appears incomplete relative to the discussion, tell the user and reconstruct from the conversation directly before continuing
- verify the final extraction against both the discussion and the code
- always show this extraction to the user before writing the final plan
- ask for confirmation or correction before proceeding
- if the user corrects the extraction, update it and show the revised version for final confirmation before proceeding
- do not start writing the plan until the extraction is explicitly confirmed

**Scratch-consumption rule (persisted `/explore` findings).**
A prior `/explore` may have saved its findings to a committed `.cursor/plans/explore-*.md` scratch file. Before finalising the extraction:
- discover all `.cursor/plans/explore-*.md` files
- if none exist, use the in-conversation discussion / Exploration Summary as usual
- if exactly one exists, show its in-file header (area explored + date) and path, and ask the user to confirm using it as the extraction anchor (or decline)
- if several exist, list each by its in-file header date + area + path and ask the user to choose one, or none
- select by the in-file header date/area the user confirms — never auto-anchor on filesystem "latest by mtime" (a committed scratch travels across machines, where `git checkout` / `pull` does not preserve the original mtime)
- absorb the chosen scratch as the primary extraction anchor only after the user confirms; if the user picks none (or none exist), fall back to the conversation
- never silently mix in an unrelated scratch
- remember whether a scratch was consumed, and which file — Step 4 offers to delete only that file after the plan is saved

Only proceed once this extraction is complete and confirmed.

## Step 0.3 — Verify exploration completeness
Before writing the formal plan, re-read the relevant parts of the codebase and review our conversation so far.
Check whether we have adequately covered:
- Where this feature should live and how it integrates with existing code
- Key dependencies, data flows, schemas, or state changes
- Important edge cases, constraints, and error-handling needs
- Any open architectural or design decisions
- Recurring project gotchas recorded in `docs/lessons.md`, if it exists, that are relevant to the work being planned
- The project's UI design cues recorded in `docs/design-system.md`, or the design doc named in `AGENTS.md`'s Subsystem Documentation, if one exists, when the planned work touches UI

If anything significant is missing, unclear, or under-explored (or if /explore was not run), list the gaps now and ask me clarifying questions.

When asking clarifying questions, ask them one at a time and provide your recommended answer for each. Wait for my response before asking the next. Walk down the design tree, resolving dependencies one decision at a time.

If you see a simpler, cleaner, or safer approach, flag it before we lock in the plan.
Only proceed once you are confident the scope is clear and complete.

## Step 0.5 — Critique Gate (required)
Before writing the formal plan, do a short adversarial review.
Try to break the proposed scope and approach.

Check:
- Does this plan risk scope creep?
- Are any edge cases, caller impacts, integration risks, or deployment risks still open?
- Are there hidden dependencies?
- Are there missing validation steps?
- Are there forgotten deployment or schema impacts?
- Are there places where the scope is still too broad or too vague?
- Are there assumptions that should be made explicit?
- Are there any deferred or excluded items that actually need to be in scope now?
- Is any Accepted Assumption actually a genuinely-uncertain choice that
  should be a `[decision]` task (decided at execution time when details
  are clearer) rather than a baked-in assumption — and conversely, is any
  `[decision]` task actually resolvable now and should simply be decided?
- Would a fresh session need to rediscover anything material to implement this safely?
- If `Executor tier: fast/medium involved` is recorded (from Step 0), are tasks that need premium (concurrency, auth, schema migrations, hook ordering, final UX polish) explicitly labelled `[executor: premium-only]`?

**Named critique lenses (Coverage / Practicality / Simplicity).** Run
the three named lenses exactly as `/review-plan` Step 1.5 ("Named
critique lenses") defines them — that section is the canonical
definition; do not restate it here — applied to the confirmed
extraction and proposed approach rather than to a saved plan. State
the result of each lens explicitly (even if "no issue") so the gate
is auditable rather than ad hoc.

**Parallel critique (where supported).** As in `/review-plan`'s
"Parallel critique (where supported)" section: if your tool supports
parallel subagents (e.g. Cursor's Task subagents, Claude Code's Task
tool), you may fan the critique lenses out — one subagent each — each
reading the confirmed extraction plus the real code it names and
returning concrete findings (extraction item or `file:line`).
Collect, dedupe, and reconcile in this session; the gap-raising and
clarification below run once here, with the user. If your tool does
not support parallel subagents (e.g. Codex), run the lenses
sequentially — the documented fallback, which changes nothing about
the critique, only how it is produced. Subagents add lens diversity,
not model diversity (they inherit this session's model); for a true
cross-model-family check on a non-trivial plan, use the follow-on
review recommended at Step 4.

If you find a real gap or risk:
- raise it now before finalising the plan
- ask clarifying questions only if the gap materially affects implementation
- if the issue can be resolved without new user input, refine the plan directly
- if the plan lacks context a fresh session would need, add it to `Key Findings`, `Codebase Integration Notes`, or `Design Decisions` now — do not leave it only in conversation
- make sure any surviving risk is captured in `Design Decisions`, `Critical Constraints`, `Validation / Verification`, `Deferred (Out of Scope)`, or `Config / Environment / Deployment Impact`

## Step 0.6 — Deferral Confirmation Gate (required)
Before writing the formal plan, run a Deferral Confirmation Gate over the candidates extracted in Step 0.1. The purpose of this gate is to stop work from being silently deferred when a deferral would make the user's requested feature incomplete — especially for production-impacting items such as new dependencies, environment variables, migrations, deploy-side config, or dev/prod parity drift.

Headless mode. Under a headless / loop invocation (for example when driven by `/execute-loop`), dispose a candidate without a live prompt ONLY when it is AUTO-DISPOSABLE: its recommended disposition is do-the-work (`Fix now` / `Include in plan`) AND it is not production-impacting — apply the recommended disposition and log it. Everything else is MUST-PAUSE — pause and surface it for a human decision, never auto-deciding: a `Defer` / `Accept` recommendation, anything production-impacting (new dependency, environment variable, migration, deploy-side config, dev/prod parity drift), or genuine uncertainty about the item's impact. These candidates are planning artifacts (the Step 0.1 deferred, excluded-with-future-work, and accepted-assumption items listed below), not severity-tagged findings — so key the branch on the do-the-work-vs-drop recommendation and the production-impact flag, not on a severity label. Interactive behaviour is unchanged — this branch fires only under a headless/loop invocation.

Candidates to gate:
- every Deferred Item from Step 0.1
- every Excluded Item that implies future work (i.e. intentionally postponed rather than a true non-goal)
- every Accepted Assumption whose underlying question the user could resolve now rather than later

If no candidates accumulated, the gate is silent — do not fire it on an empty batch.

Do not double-prompt items the user has already explicitly resolved earlier in the discussion. If the user clearly stated an item is permanently out of scope, or already chose `Fix now`, `Include in plan`, `Defer`, or `Accept` for it in the conversation, record that disposition and skip the gate for that item.

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
- `Fix now` — resolve the item in this planning pass, then update the Step 0.1 extraction so the resolution appears in Agreed Scope or Key Design Decisions before the plan is written
- `Include in plan` — add the item as a new task in Agreed Scope so it appears in the final Tasks list (initial-plan authoring: this task is part of the plan being created and is hardened by the plan's normal `/review-plan` pass — it does NOT trigger a separate scoped `/review-plan`, mirroring the full-pass in-pass exception in `/review-plan`'s Scoped-mode no-recursion guard)
- `Defer` — keep the item in Deferred Items with a `Risk if deferred:` tag (security / correctness / ux-degradation / blocked-work / minor) and a `Revisit by:` date or trigger string
- `Accept` — record the item under Accepted Assumptions or Excluded Items with the user-supplied rationale and no follow-up action

If the user aborts the gate mid-flow, do not commit pending dispositions to disk. Pending state lives only in the conversation until the gate completes. Only update the Step 0.1 extraction once every gated candidate has a recorded disposition or the user explicitly closes the gate.

Use `Accept` as the audited no-follow-up option; do not introduce an `Ignore` disposition.

Only proceed to Step 1 once every candidate has a recorded disposition.

## Step 1 — Suggest a feature name

Ask the user to choose one or provide their own.
Sanitise the chosen name automatically: lowercase, hyphens only, no spaces or special characters.

## Step 2 — Check for an existing plan file
Check whether `.cursor/plans/plan-[chosen-name].md` already exists.

If it DOES exist:
- Show the user the existing plan's goal and current progress percentage
- Ask what they want to do:
  1. **Overwrite** — replace the existing plan entirely and start fresh
  2. **Rename** — keep the existing plan, choose a different name for this new one
  3. **Cancel** — stop here, do not create anything

If the user chooses Rename, go back to Step 1.
If the user chooses Cancel, stop and confirm nothing was changed.
Only proceed to Step 3 if the user chooses Overwrite or no conflict was found.

## Step 3 — Write the plan
Requirements:
- no extra scope beyond what was confirmed
- treat the initial saved plan as the baseline checkpoint for this feature
- include key exploration findings and integration notes so a fresh session can understand the reasoning without re-exploring the codebase
- include enough durable context that a fresh session, review session, or testing session can continue without rediscovering the core reasoning
- include only code-verified findings; do not paste raw exploration notes or speculative ideas
- document design decisions with reasoning and rejected alternatives
- keep the `Current State / Handoff Note` short and operational — it is a status checkpoint, not a narrative summary
- modular steps
- clear task order
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

Hardening stage (optional, for large plans): for a large executable
plan, consider adding a Hardening stage near the end of the task list —
`/review-loop` → `/simplify` → `/security-review` → route findings
(trivial → `/fix`; substantial → scoped `/review-plan`) → final
re-review — as documented in the plan template's `## Tasks` section. Put
it on the executable stage / feature plan, never on a master
coordination plan (use a child hardening-stage plan for a master). Keep
it optional and proportional.

The final saved plan must populate the `Planning Extraction Summary` section from the confirmed discussion extraction step.

This means:
- agreed scope is recorded explicitly
- deferred / excluded / accepted-assumption items are captured from the start
- key design decisions are preserved so a fresh session does not need to rediscover them

Use the exact structure from:
`.cursor/templates/implementation-plan-template.md`

Do not simplify or substitute a different format.

### Skeleton-first incremental write
Write the plan to disk incrementally rather than composing the whole file in a single pass:
1. first write the full section skeleton — every heading from `.cursor/templates/implementation-plan-template.md`, in order, with brief placeholders
2. then fill and verify one section at a time, editing the file section-by-section
3. populate `Planning Extraction Summary` from the confirmed Step 0.1 extraction (including the consumed scratch, if any) before the narrative sections

This keeps the template structure complete and correct from the first write and leaves a partially-written plan recoverable if the session is interrupted. It satisfies the "use the exact template structure" requirement above.

## Step 4 — Save the plan
1. Create `.cursor/plans/` folder if it does not already exist
2. Save the plan to `.cursor/plans/plan-[feature-name].md`
3. Confirm the saved file path to the user
4. If a `.cursor/plans/explore-*.md` scratch was consumed as the extraction anchor in Step 0.1, offer to delete that one file now — an explicit prompt the user must accept; never delete automatically, and never touch any other scratch. If the user declines, leave it in place.
5. Remind the user:
   - This plan file is the single source of truth for /execute
   - If context gets full mid-build: run /document, close the session,
     open a fresh Agent, run /start-session, then run /load-plan to resume
   - Commit this file to GitHub so it transfers between computers
6. For non-trivial plans, recommend a follow-on review before
   `/execute`: a `/review-plan` hardening pass over the saved plan
   (it reconciles against the real code and runs the full critique
   and deferral gates), and/or an independent plan-aware
   `/peer-review` (`$peer-review` in Codex) — ideally run in a
   different model family for the cross-family catch-rate.
   Non-trivial = the plan involves schema or migrations, concurrency,
   auth / permissions, multi-screen UI, or records `Executor tier:
   fast/medium involved` — the same definition `/review-plan` Step 7
   uses. For a small, low-risk plan, say a follow-on review is
   optional.

This is still planning only.
Do not implement anything yet.
