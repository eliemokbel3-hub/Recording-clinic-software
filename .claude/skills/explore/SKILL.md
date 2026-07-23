---
name: explore
description: Deep investigation of a feature or codebase area. Use when native Plan Mode feels too shallow or when you want facts before trusting any plan. Shared Cursor/Codex/Claude Code workflow; invoke as /explore in Cursor or Claude Code, or $explore in Codex.
disable-model-invocation: false
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/explore` in Cursor or Claude Code, or `$explore` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

Do not implement anything yet.

## Step 1 — Check whether a description was provided
Look at the message that triggered this command.

- If the user typed `/explore` followed by a description (e.g. `/explore Stripe payment webhook handler`),
  use that description as the area to explore and proceed to Step 2.
- If the user typed `/explore` with nothing after it, ask:
  "Please describe the feature or area you would like me to explore.
  I will read the relevant code, map out how it currently works, what it connects to,
  and what questions I need answered before we decide what to do next."
  Then wait for the response before proceeding.

## Step 2 — Explore the requested area
Your job is to explore and understand the requested work.

Please:
- check `AGENTS.md` for any `Subsystem Documentation` pointers relevant to the requested area
- if relevant deeper docs exist, read them as part of the exploration before forming your analysis
- analyse the relevant parts of the codebase
- identify integration points, dependencies, edge cases, and constraints
- list ambiguities or questions
- separate facts you found in the code from assumptions

Do not write code yet.
When you finish the analysis, ask only the questions you genuinely need answered before proceeding.

Before finishing exploration, produce a compact **Exploration Summary** structured to match the `Planning Extraction Summary` section names, field order, and category meanings used by `/create-plan` and the plan template at `.cursor/templates/implementation-plan-template.md`. This lets `/create-plan` absorb the summary verbatim into the plan file without restructuring.

Exploration Summary categories (in this order, same names as Planning Extraction Summary):

- Agreed Scope (Build Now)
  - what appears confirmed to be built now

- Deferred — Actionable Later
  - things discussed and explicitly postponed
  - include the reason they were deferred

- Excluded — Revisit Only If Needed
  - things intentionally left out for a lighter initial version
  - include the rationale for exclusion

- Accepted Assumptions — Revalidate Later
  - things treated as true to keep planning manageable
  - include the risk if they are wrong

- Key Design Decisions
  - choices made during exploration that constrain implementation
  - include rejected alternatives where relevant

Rules:
- separate facts found in the code from assumptions
- keep this summary compact and structured
- do not turn it into a full plan
- this summary is a handoff anchor for `/create-plan` or native Plan Mode — `/create-plan` should be able to copy this block into the plan's `Planning Extraction Summary` verbatim
- do NOT include `Workflow Schema:` or `Executor tier:` lines here — those are written by `/create-plan`'s Step 0 Executor Capability Gate, not during exploration
- if the exploration conversation touches on executor-tier concerns (e.g. work that fast models would reliably miss), record those concerns inside `Key Design Decisions` so `/create-plan` Step 0 has them as context when recording the `Executor tier:` answer

## Step 3 — Persist the exploration to a scratch file
After producing the Exploration Summary, also save it to a committed scratch file so the exploration survives context resets, session switches, or moving to another machine — and so `/create-plan` or `/review-plan` can consume it later without re-deriving it.

This scratch write is `/explore`'s only side effect; `/explore` stays read-mostly — it persists exploration NOTES, not code, and "do not implement anything yet" still holds.

Write the scratch as follows:
- derive a short kebab-case slug from the explored area (e.g. `stripe-webhook-handler`)
- create `.cursor/plans/` if it does not already exist (an exploration often precedes any saved plan, so the directory may not be there yet)
- save to `.cursor/plans/explore-[slug].md`; if that file already exists, append `-2`, `-3`, … so an earlier exploration is never overwritten
- the `explore-` prefix is deliberate: plan-scanning workflows (`/load-plan`, `/start-session`, `/document`, `/peer-review`) match `plan-*.md`, so an `explore-*.md` scratch is never mistaken for an execution plan

The scratch file contains, in this order:
1. a header line naming the area explored and the date
2. the code-verified **Key Findings** — files / symbols involved, codebase integration notes, and external / API findings (if any) — using the same section names as the plan template's `Key Findings`
3. the full 5-category **Exploration Summary** block from Step 2 (Agreed Scope / Deferred / Excluded / Accepted Assumptions / Key Design Decisions), so `/create-plan` can copy it into `Planning Extraction Summary` verbatim

Do NOT add `Workflow Schema:` or `Executor tier:` lines to the scratch — those belong to `/create-plan`'s Step 0 gate, exactly as for the in-conversation summary.

After writing the file, report the saved path, remind the user to commit the scratch if they want the exploration to survive across machines, and keep the Exploration Summary in the conversation as well — the scratch supplements the conversation, it does not replace it.
