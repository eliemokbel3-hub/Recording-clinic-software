---
name: simplify
description: Surface behavior-preserving, clearly-valuable simplification opportunities in recent work and write them as findings. Propose-only — never auto-edits. Shared Cursor/Codex/Claude Code workflow; invoke as /simplify in Cursor or Claude Code, or $simplify in Codex.
disable-model-invocation: false
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/simplify` in Cursor or Claude Code, or `$simplify` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

`/simplify` is a focused, propose-only pass: it surfaces simplification opportunities and writes them as `/review`-compatible findings, then routes them — it NEVER edits code itself. Producing the findings is the deliverable; applying a simplification belongs to `/fix` (trivial, localized changes) or to a plan-amending disposition plus a scoped `/review-plan` (substantial, cross-cutting refactors). It is the deliberate "make this simpler" counterpart to `/review`'s broad correctness pass — reach for it when code works but feels more complex than it needs to be.

This workflow is propose-only and agent-invocable: it carries `disable-model-invocation: false` (Cursor + Claude Code) and NO `agents/openai.yaml` (Codex), so an agent may invoke it automatically — for example inside a Hardening stage or a review loop — and you can still invoke it explicitly. Because it only writes findings and never edits code, agent invocation cannot mutate code or docs; the apply step is always a separate, human-gated `/fix`.

Plan files are shared across all three tools. Handoff is through disk state, the plan file, and git, not conversation memory.

## The conservatism guard (mandatory — read first)

Simplification is high-risk precisely because it touches working code for non-correctness reasons. Apply this guard to EVERY candidate before it becomes a finding:

- **Behavior-preserving only.** A simplification must not change observable behaviour, outputs, error handling, performance characteristics, or public contracts. If you cannot show it is behaviour-preserving, it is not a `/simplify` finding — at most it is a `/review` correctness question.
- **Clearly value-positive.** Surface a finding only when a thoughtful maintainer would agree the simpler shape is meaningfully better: less code to reason about, one canonical path instead of several, a removed needless abstraction.
- **Bias to "leave it alone."** On any marginal, stylistic, or taste-level call, do nothing and say nothing. Renames for preference, reformatting, swapping one equivalent idiom for another, speculative future-proofing, and "I would have written it differently" are NOT findings. When in doubt, leave it alone.
- **No drive-by scope.** Do not bundle behaviour changes, bug fixes, or new features into a "simplification." Those are `/review` / `/fix` / plan work, not this pass.

If after the pass nothing clears this bar, say so explicitly — "no simplifications worth a maintainer's attention" is a valid and common result. Do not pad with marginal suggestions.

## Step 0 — Read plan context and scope

Establish what to look at and the reference for severity, mirroring `/review` Step 0:

- check `.cursor/plans/` (excluding `.cursor/plans/completed/`) for a plan file; if running in the same session that produced the work, use that plan; if multiple, prefer the most recent `Last plan sync`; if none, proceed against the code and project conventions and note that findings persist only in the conversation.
- if a plan is in scope, read its `Goal`, `Design Decisions`, `Critical Constraints`, and `Integration Notes`. Do NOT flag a shape the plan deliberately chose — a documented decision overrides a generic "simpler" instinct.
- establish the scope to simplify: by default the changed files since the plan's `Last plan sync` (or the feature/change baseline), or an explicit target the user named.
- read every in-scope user-authored file in full before judging it — do not rely on diff fragments, which hide the surrounding context that separates a real simplification from a behaviour change. Skip generated/regenerated artefacts and read their upstream source instead.

## Step 1 — Find simplification opportunities

Look for behavior-preserving structural simplifications. This overlaps `/review`'s Structural Quality and "unnecessary complexity" lenses, focused exclusively on making working code simpler:

- **Needless complexity** — premature abstractions, indirection with a single caller, speculative configurability, defensive code for impossible conditions, dead branches.
- **Duplication collapsible to a canonical path** — two flows reimplementing the same pipeline; a local reimplementation of an existing helper, hook, query layer, or type. Name the canonical layer it should route through.
- **Over-built control flow** — deeply nested conditionals or accreting branch ladders that an early return, guard clause, or dispatch table would make legible.
- **Redundant state / data shuffling** — values recomputed that already exist, intermediate structures that add no clarity, manual loops a single expression would replace.
- **Removable indirection** — wrappers, adapters, or layers that no longer earn their keep.

Every candidate must pass the conservatism guard above.

## Step 2 — Verify candidates (false-positive filter)

Before logging anything, re-read the cited lines for each surviving candidate and confirm, mirroring `/review`'s Finding Verification pass:

1. **Concrete evidence** — a real `file:line` (or tight region) that exists and exhibits the complexity.
2. **Behaviour-preserving** — re-confirm the proposed simpler shape produces identical behaviour, including error paths and edge cases. If you cannot confirm this, drop it.
3. **Not already handled / not plan-chosen** — confirm the current shape isn't required by a caller, a type, a Critical Constraint, or a Design Decision.
4. **Severity justified** — size the finding by the value and reach of the simplification (see routing below).

Drop anything that fails. Keep a one-line note for any candidate consciously dropped as marginal, so the pass is auditable.

## Step 3 — Severity routing and Findings Log

Assign each surviving finding a severity using the existing `/review` severity vocabulary (no parallel taxonomy). Simplification findings skew **MED / LOW**; reserve HIGH/CRIT for complexity that actively causes a correctness or security risk (e.g. a duplicated invariant that will drift). Route by reach:

- **trivial / localized** (single-site, self-contained: collapse a redundant conditional, delete dead code, route one call through an existing helper) → `Triage: Fix-now`. `/fix` applies it with re-read + verification + stop-on-failure.
- **substantial / cross-cutting** (a real refactor: extract a shared layer, restructure a flow, change a shape touched in several places) → it is a scope-expansion-shaped finding. Route it through a **plan-amending disposition**: append a 🟥 task to the CURRENT plan (bias toward tacking onto the active/stage plan over spawning a new follow-up plan), then run a **scoped `/review-plan`** on just that new task before it is executed. The scoped behaviour is defined once in `/review-plan`'s scoped-mode section — point there; do not restate it.

Write findings to the plan's `Review Findings Log` as a `/review`-compatible round so `/fix` ingests them unchanged:

- append a `### Round N — YYYY-MM-DD` block, where N continues the plan's existing Review History / Findings Log round count; also append the one-line `Review History` entry for the round.
- set `Source:` to where this ran plus the skill: `Cursor simplify` / `Claude Code simplify` / `Codex simplify`.
- assign stable IDs with the `SIMP-` prefix in finding order: `SIMP-001`, `SIMP-002`, … (numbering resets per round). Each finding still carries its severity (CRIT/HIGH/MED/LOW) as a field.
- use the full per-finding block from `.cursor/templates/implementation-plan-template.md` (Triage, Fix route, Why it matters, Current/Desired behaviour, Pattern to follow, Verification, Regression risk, `/fix decision: Pending`, etc.). A substantial finding becomes a new 🟥 task in the plan, logged with `Triage: Fix-now` so `/fix` ingests it — the same representation `/review` uses for an `Include in plan` outcome (`Include in plan` is NOT a `Scope-expansion disposition` field value; use only the values the template documents for that field). The scoped `/review-plan` then hardens that new task.
- findings recommended for `Defer` or `Accept` run through the Deferral Confirmation Gate exactly as in `/review`; `Triage: Fix-now` findings (including a substantial finding logged as a new Fix-now task) are not gated.
- append only after the pass is complete; never for an aborted pass. If no plan file is in scope, skip the log and report findings in the conversation only.

## Output format

Mirror `/review`'s shape, scoped to simplification:

- **Scope** — files read, baseline used, any skips.
- **Simplifications found** — one entry per finding with its `SIMP-NNN` ID, severity, `file:line`, the current shape, the simpler shape, why it is behaviour-preserving and value-positive, and its route (Fix-now → `/fix`, or Include in plan → scoped `/review-plan`).
- **Consciously left alone** — a short list of marginal/stylistic candidates the conservatism guard rejected, so the user can see the bar was applied (or "none").
- **Summary** — counts by severity and by route, plus the round number; state "no simplifications worth a maintainer's attention" if that is the honest result.

After logging substantial findings as new tasks, remind the user that those tasks get a scoped `/review-plan` before `/execute`, and that `/fix` handles the Fix-now findings.
