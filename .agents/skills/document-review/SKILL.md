---
name: document-review
description: Deep periodic documentation audit across every repo doc — accuracy, placement, bloat, and staleness — followed by a single-session propose-and-confirm migration/fix pass. The heavy counterpart to /document's in-run bloat guard. Shared Cursor/Codex/Claude Code workflow; invoke as /document-review in Cursor or Claude Code, or $document-review in Codex. Side-effecting; explicit invocation only.
disable-model-invocation: true
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/document-review` in Cursor or Claude Code, or `$document-review` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

This workflow is side-effecting. Cursor uses `disable-model-invocation: true`; Codex uses `agents/openai.yaml` with `policy.allow_implicit_invocation: false`; both require explicit user invocation.

This workflow reads and writes the same repository documentation across all three tools, so no copy-paste handoff is needed when switching tools.

`/document-review` is the **heavy, periodic, all-docs audit** that `/document`'s
in-run Step 7 bloat guard explicitly defers to. `/document` runs after a unit of
work and reconciles only the docs that work touched; `/document-review` is run on
its own, occasionally, to audit EVERY doc in the repo against the current code
and against where knowledge should live. Reach for it when documentation has
drifted, when `AGENTS.md` has bloated across several releases, or on a periodic
cadence — not after every change.

It scans read-only first (in parallel where the tool supports it), consolidates
in one session, then proposes migrations and fixes and applies only what the
user confirms.

## Boundary — docs only

- Audits and edits documentation only: `AGENTS.md`, `AGENTS.local.md` (if
  present), `README.md`, everything under `docs/**`, and the `CLAUDE.md` bridge.
- NEVER edits product code.
- NEVER changes plan lifecycle state or task markers — that stays in `/document`
  (Steps 5–6). `/document-review` may FLAG a stale plan-file pointer that a doc
  references, but it does not edit `.cursor/plans/` files.
- NEVER moves `CHANGELOG.md` content — it is the separate project history
  surface. Audit it for accuracy and pointer correctness only; never use it as a
  migration source or target.
- All writes happen in this one orchestrating session, after explicit
  confirmation. Any subagents used for the audit are READ-ONLY.

## Step 0 — Scope the audit

Enumerate the documentation surface and state it at the top of the output so the
user can confirm scope before anything is read in depth:

- `AGENTS.md` — the canonical project briefing.
- `AGENTS.local.md` — only if present. It is gitignored and machine-specific
  (local paths, personal DB endpoints, machine-local ports). Audit it for
  placement and confirm it holds no secrets; NEVER propose moving its
  machine-specific content into a committed doc.
- `README.md`.
- every `docs/**/*.md`.
- the `CLAUDE.md` bridge — it should only import `AGENTS.md` (e.g. `@AGENTS.md`);
  confirm it carries no duplicated content and do not add content to it.
- the `AGENTS.md` Subsystem Documentation pointers — confirm each points at a doc
  that still exists and is current.
- `CHANGELOG.md` — accuracy and pointer correctness only; never a migration
  source or target.

Active plans under `.cursor/plans/` are pointer targets only — verify that docs
reference them correctly; do not audit them as docs and do not edit them.

## Step 1 — Parallel read-only audit (four lenses)

Audit every in-scope doc against the current code through four independent
lenses. This step is READ-ONLY — it produces candidate findings and changes
nothing.

- **Accuracy** — does the doc match what the code actually does now? Read the
  implementation; do not trust an older doc over current code. Flag statements
  the code contradicts: wrong commands, renamed or removed files, dropped
  features, outdated counts or version numbers. Design cues in
  `docs/design-system.md` are verified against the current UI code like any
  other doc claim; two live conflicting patterns recorded as the same
  convention is an Accuracy/Staleness finding.
- **Placement** — is each piece of knowledge in the right doc for the project's
  layering (`AGENTS.md` = concise briefing + conditional pointers;
  `docs/integrations/*` = external/API/integration knowledge; `docs/testing/*` =
  repeatable test procedures; `docs/architecture/*` or `docs/build/*` = durable
  subsystem notes; `AGENTS.local.md` = machine-specific)? Flag content sitting in
  the wrong layer, e.g. deep subsystem detail inlined in `AGENTS.md`.
- **Bloat** — has any doc, especially `AGENTS.md`, accreted content that should
  be migrated out: stacked `Last Session` / `Previous Session` blocks, repeated
  or duplicated `Documentation Status`, an oversized `Current Status` spanning
  several releases, large per-version rollback/recovery or release-history dumps?
  This is the `/document` Step 7 guard applied across ALL docs and more deeply.
- **Staleness** — dead pointers, references to removed code or files, superseded
  version numbers, links to docs that no longer exist, and "next steps" that were
  completed long ago.

If your tool supports parallel subagents (e.g. Cursor's Task subagents, Claude
Code's Task tool), you may fan the four lenses out — one READ-ONLY subagent per
lens, each given the same enumerated doc set from Step 0. Each subagent reads its
docs and the relevant code in full and returns candidate findings with concrete
`file:line` evidence (the doc path and line, plus the code `file:line` that
proves or disproves the doc), not prose summaries. Subagents never edit docs. If
your tool does not support parallel subagents (e.g. Codex), run the four lenses
sequentially in this same session — the sequential path is the documented
fallback and produces the same findings, only slower.

Subagents add lens diversity, not model diversity: they inherit this session's
model and blind-spot profile, and only parallelise the read.

## Step 2 — Consolidate in a single session

Collect all candidate findings (from the subagents or the sequential passes) and
consolidate ONCE in this orchestrating session:

- dedupe — the same issue at the same site is one finding; keep the richest
  write-up.
- drop any finding that lacks a concrete, locatable `file:line` evidence pair
  (the doc location AND the code or correct-home location). A finding with no
  matching evidence is dropped, or downgraded to an explicit "needs
  investigation" note — it does not become a migration proposal. (This mirrors
  `/review`'s Finding Verification false-positive filter.)
- group the surviving findings by lens and by target doc.

Consolidation and every subsequent write happen only in this session — never
delegated to a subagent.

## Step 3 — Propose migrations and fixes (propose-and-confirm)

Present the surviving findings as concrete proposals. Do NOT perform them yet.
Reuse the `/document` Step 6/7 migrate-on-confirm pattern. For each proposal:

- name the specific block or lines and the exact change — fix in place, or
  migrate from doc A to doc B.
- for a migration, name the target doc under `docs/` (or propose a focused new
  doc if none fits) and the pointer stub that will be left behind.
- group related proposals so the user can confirm in batches rather than one
  edit at a time.

Every proposal MUST obey these rules:

- NEVER move `CHANGELOG.md` content, and NEVER relocate a durable subsystem doc
  that already belongs where it is.
- migrate VERBATIM — preserve commands, code-checkout lines, `Risk if deferred:`
  / `Revisit by:` fields, and rollback instructions exactly. A migration moves
  text; it does not reword it.
- never surface secrets, and never propose moving machine-specific
  `AGENTS.local.md` content into a committed doc.
- leave a concise pointer stub in the source doc wherever a block is migrated
  out, so the knowledge stays findable.

Wait for explicit confirmation. Apply nothing without it.

## Step 4 — Apply confirmed changes in one session

Apply only the confirmed proposals, all in this session:

- perform each fix and migration verbatim.
- leave the pointer stubs where content moved.
- RE-VERIFY nothing was dropped: every migrated block exists at its destination
  with its commands, `Risk if deferred:` / `Revisit by:` fields, and rollback
  text intact, and every source location holds either the corrected text or a
  pointer stub.
- report what changed and what moved where (source → destination), and note
  anything you deliberately left alone and why.
- record any substantive finding the user chose NOT to action now as a follow-up
  (in the active plan's deferred items or `docs/known-issues.md`) rather than
  losing it.

If `CLAUDE.md` exists, do not add content to it — it is the thin `@AGENTS.md`
bridge.

This skill audits and migrates docs only. It does not run `/document`'s
plan-sync and lifecycle steps, and it never touches product code — for
per-change doc reconciliation and plan syncing, use `/document`.
