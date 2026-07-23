---
name: document
description: Reconcile project documentation with the real code, route durable knowledge into the right long-term docs, and sync or retire active plans. Shared Cursor/Codex/Claude Code workflow; invoke as /document in Cursor or Claude Code, or $document in Codex. Side-effecting.
disable-model-invocation: false
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/document` in Cursor or Claude Code, or `$document` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

This workflow is side-effecting but agent-invocable: Cursor uses `disable-model-invocation: false` and Codex uses `agents/openai.yaml` with `policy.allow_implicit_invocation: true`, so an agent may invoke it automatically (for example inside a loop) and you can still invoke it explicitly. Safety comes from this workflow's in-skill gates rather than from invocation-locking.

This workflow reads and writes the same `.cursor/plans/` files as Cursor and Claude Code, so no copy-paste handoff is needed when switching tools.

Please update the project documentation carefully.

Scale effort to the scope of the changes. If the work was a small fix with no active plan and no durable subsystem knowledge, update `AGENTS.md` and `CHANGELOG.md` and stop. For larger work, continue through all steps.

Hosting preflight — unconditional, before the small-work stop above can end the run: whenever `AGENTS.md` has a Tech Stack Hosting row, classify each of its targets exactly once per the Hosting-evidence rule in Step 4 and surface any resulting proposal; whenever `AGENTS.md` has a Tech Stack table but NO Hosting row at all, treat the missing row as the same unknown (s1) — run the rule's discovery scan once and surface the evidence-derived row ADDITION it proposes under the same three-way contract (zero evidence → the ask with NO default; the row is written only through the rule's interactive confirmation gate) — a nudge-driven `/document` on an otherwise clean repo still gets its Hosting review. The small-work fast path otherwise skips the later steps unchanged.

## Step 1 — Identify what changed
Use git status, diff, and recent commits to identify the files, features, and subsystems affected.

## Step 2 — Verify against code
Read the current implementation.
Do not trust older docs if the code now says something different.
For `AGENTS.md`'s Tech Stack Hosting row, "the code" includes the repo's hosting config: verify each recorded hosting target against current config evidence per the Hosting-evidence rule in Step 4.

## Step 3 — Classify the knowledge before writing docs
Decide where each piece of information belongs:

- `AGENTS.md`
  - concise project briefing
  - short current status / next priorities
  - conditional pointers to deeper docs
  - example: "If working on bank feeds, read `docs/integrations/aciss-bank-feeds.md`"
  - the project's shared, repo-wide dev-run / test / lint / build commands, DB-access and migration commands, and non-obvious gotchas — the runnable knowledge a fresh contributor needs (keep machine-specific values out — see `AGENTS.local.md`)
  - the smoke recipe as it surfaces: the start command, the local URL, and what a healthy response looks like — plus dev/test account pointers by env-var *name* only (values only ever in the local `.env`)
  - the Tech Stack Hosting row is evidence-classified, never free-form: every target `/document` records carries a provenance marker (`source=config:<repo-relative-path>` or `source=user-confirmed:<YYYY-MM-DD>`), and a pre-existing unmarked value is an unevidenced claim — see the Hosting-evidence rule in Step 4
- `AGENTS.local.md` (gitignored — never commit it)
  - machine-specific or developer-specific runnable knowledge: local absolute paths, personal DB connection details, machine-local ports, per-developer env quirks
  - NEVER secrets (API keys, tokens, passwords, credentialed connection strings) — those belong only in the local `.env`
  - referenced from `AGENTS.md` with a brief pointer where it helps (e.g. "machine-specific run notes live in `AGENTS.local.md`")
- `docs/integrations/*.md`
  - durable external API / provider / integration knowledge
  - observed quirks, behaviour, conventions, and gotchas
- `docs/testing/*.md`
  - repeatable test and verification procedures
  - local vs live/staging validation flows
- `docs/build/*.md` or `docs/architecture/*.md`
  - durable feature or subsystem notes worth keeping beyond the plan
- `docs/lessons.md`
  - the curated lessons store: recurring, run-evidenced workflow/process gotchas confirmed via the lessons distillation step (Step 6.5 below)
  - NOT runnable commands (those belong in `AGENTS.md`), NOT external integration knowledge (`docs/integrations/`), NOT one-off incidents
- `docs/design-system.md`
  - the project's UI design cues: visual/interaction conventions (surfaces, dialogs, dropdowns, view patterns, spacing/color/type tokens, microcopy taste), each anchored to a canonical code example (a file or component reference)
  - NOT external integration knowledge (`docs/integrations/`), NOT workflow/process lessons (`docs/lessons.md`)
- `.cursor/plans/plan-*.md`
  - active execution state and temporary implementation history only
- `CHANGELOG.md`
  - concise project-facing summary of what changed

## Step 4 — Update durable docs in the right place
Update:
- `AGENTS.md`
- `AGENTS.local.md` — only when there is machine-specific / developer-specific runnable knowledge to capture (create it if needed; it is gitignored)
- `CHANGELOG.md`
- any focused docs under `docs/` that should hold durable knowledge

Rules:
- keep `AGENTS.md` concise — do not dump detailed subsystem or integration notes into it
- when deeper detail is needed, create or update a focused doc under `docs/` and reference it briefly from `AGENTS.md`
- make those AGENTS references conditional where appropriate
- route machine-specific / developer-specific runnable knowledge (local absolute paths, personal DB endpoints, machine-local ports) to `AGENTS.local.md`, not `AGENTS.md`; keep shared, repo-wide commands and gotchas in `AGENTS.md`, and add a brief `AGENTS.md` pointer to `AGENTS.local.md` where it helps a fresh contributor
- when the session's work executed another repo's plan tasks or materially changed another repo, also refresh the `Last Session` block — and any status lines the work has invalidated (e.g. a stale "NOT yet deployed" claim) — of EVERY repo touched, not just the repo the session is rooted in: a cross-repo session that documents only its root repo leaves the other repo's briefing stale, and the next plan drafted there inherits the stale claim (observed live: caught only by a later `/review-plan` reconciliation)
- capture the smoke recipe (start command + local URL + what healthy looks like) and dev/test account pointers by env-var *name* into `AGENTS.md` as they surface — values only ever in the local `.env`
- when the session's diff includes UI work, capture the project's design cues into `docs/design-system.md`: record new or changed visual/interaction conventions (surfaces, dialogs, dropdowns, view patterns, spacing/color/type tokens, microcopy taste), each anchored to a canonical code example (a file or component reference); replace cues superseded by this session's verified changes rather than stacking new ones; a supersession is only clean when the old pattern is verifiably gone from the code — when the CODE still holds two live conflicting patterns for the same convention (whether or not both are recorded in the doc), surface the conflict propose-and-confirm instead of overwriting the recorded cue — never silently pick a winner. Prefer values-live-in-code: point a cue at the token/source file that owns the literal values (e.g. "spacing tokens live in `styles/tokens.css` — that file wins") rather than duplicating the values into the doc, where they go stale on the next value change. Before creating anything, check whether the repo already maintains a canonical design doc — an `AGENTS.md` Subsystem Documentation pointer to one, or a `docs/**` file whose name/content marks it as the design-language doc (e.g. `docs/architecture/design-language.md`); if found, treat THAT file as the design-cues store and update it in place — never create a competing `docs/design-system.md` — and, when the adopted doc has no `AGENTS.md` pointer, add/normalize the conditional Subsystem Documentation pointer as part of adoption (the pointer is what lets the plan-time and build-time consults find the adopted doc). Only when no existing design doc is found: on first use, create the file with a light suggested-sections hint (surfaces & layout; dialogs/modals; dropdowns/menus; forms & inputs; view/settings patterns; tokens — spacing/color/type; microcopy taste) and add a conditional `AGENTS.md` Subsystem Documentation pointer (e.g. "If doing UI work, read `docs/design-system.md`"). Headless/loop invocations apply code-verified supersessions only and surface conflict-resolution candidates for the next interactive run.
- Hosting-evidence rule: never assert or record a hosting platform without config evidence or explicit user confirmation — `AGENTS.md`'s Tech Stack Hosting row is a claim to verify, not a fact to restate. Evaluate each Hosting target independently (a multi-target row is evaluated target by target; sibling rows and their existing markers are preserved byte-for-byte): a blank target is unknown — resolve the discovery scan below and propose from its evidence, never leaving a seeded guess in place; a MISSING Hosting row (a Tech Stack table with no Hosting row at all) is the same unknown — resolve the same discovery scan and propose an evidence-derived row ADDITION under the same three-way contract, serialized exactly as below and inserted into the Tech Stack table with every existing row byte-preserved (written ONLY on interactive confirmation; a headless run surfaces the proposed addition and writes nothing); a non-blank target with NO `source=` marker is an unevidenced CLAIM — check it against the discovery scan's current config evidence and flag it propose-and-confirm, never silently rewriting it and never restating it as fact; a `source=config:<repo-relative-path>` marker is REVALIDATED against the current repo — when its path is missing, renamed, or no longer supports the recorded label, the target is STALE and re-flags exactly like an unevidenced claim; a `source=user-confirmed:<YYYY-MM-DD>` marker is durable — never re-challenged by freshness checks; a validly marked target contradicted by NEW target-specific current config evidence is surfaced propose-and-confirm (a user-confirmed target is surfaced as information, never re-flagged as unevidenced; the mere coexistence of another platform's config is not a contradiction); a malformed, unknown-token, multiple-marker, or absolute/non-repo-relative-path marker is treated as unmarked (fail closed) — it never counts as valid and never suppresses the evidence review. Evidence discovery is deterministic, shared shape-for-shape with the installer's hosting stack step: candidates are git-TRACKED files only (ignored and untracked files never count), matched by signal filename at any depth — the CLOSED high-confidence single-platform set with its pinned labels: railway.toml → Railway, fly.toml → Fly.io, render.yaml → Render, vercel.json → Vercel, netlify.toml → Netlify, wrangler.toml → Cloudflare Workers/Pages, amplify.yml → AWS Amplify (an unlisted platform-specific filename is NEVER high-confidence — it classifies as generic/ambiguous evidence at most, so no branch ever silently proposes from it), plus the generic/ambiguous signals (Dockerfile, docker-compose.yml, Procfile, app.yaml, `terraform/`, and deploy-shaped `.github/workflows/` files — a `.github/workflows/` file is deploy-shaped iff the case-insensitive substring "deploy" appears in a job identifier, a step `name:`, or a `uses:` action reference, nowhere else; `terraform/` is a candidate iff at least one git-tracked file exists under a directory named `terraform/`, the directory path being the recorded candidate — git tracks no directory entries) — EXCLUDING paths under `node_modules/`, `vendor/`, `dist/`, `build/`, `.git/`, and directories named `test`, `tests`, `fixtures`, `examples`, or `archive`; any path whose realpath resolves outside the repo is excluded; duplicate realpaths dedup to ONE candidate; signal filenames and exclusion-directory names match case-sensitively; order candidates by `LC_ALL=C` repo-relative lexical path order, a duplicate realpath retaining its FIRST alias in that order (the retained alias is the `source=config:` path); resolve this ordered candidate set BEFORE any proposal or question. Then decide three-way — no branch ever silently chooses a provider: ZERO evidence → ask which platform hosts the project, offering NO default; exactly ONE unambiguous single-platform signal → show the evidence (the candidate path and its label) and propose that platform for confirmation; MULTIPLE, generic-only, or conflicting evidence → enumerate everything found and ask the user to confirm one or SEVERAL targets (a split deployment records one Hosting row per target). On the user's confirmation of a proposed hosting correction, write the corrected row and select its marker by BASIS OF EVIDENCE: `source=config:<repo-relative-path>` when the confirmed label is unambiguously supported by that current config signal — the user's approval authorizes the write but does not change its basis (the marker stays `config:` and remains freshness-checkable), and several config-supported targets each keep their OWN `source=config:<its-path>`; `source=user-confirmed:<YYYY-MM-DD>` ONLY when the label comes from the user's own knowledge or choice (config absent, generic, conflicting, or deliberately overridden). Serialize one Hosting table row per target, of exactly the form `| Hosting | <target> | [<free-text note>; ]source=config:<repo-relative-path> |` or `| Hosting | <target> | [<free-text note>; ]source=user-confirmed:<YYYY-MM-DD> |` — the marker token exactly once per row, LAST in the Notes cell, the path always repo-relative (verbatim, spaces stay verbatim inside the cell, never machine-absolute); before writing, any dynamic field (target text, note, or marker path) containing a `|`, a `source=` substring, or a line break/control character is handled deterministically — user-sourced text is rejected and re-asked (never escaped or silently stripped), and a config path containing such characters is never serialized into a `source=config:` marker (show the evidence anyway; on interactive confirmation record `source=user-confirmed:<date>` instead). ALL Hosting row/marker writes are interactive-confirmation-gated. Headless/loop invocations NEVER mutate a Hosting row and NEVER write a provenance marker — they verify evidence, classify each target, and surface every proposed row/marker change for the next interactive run.
- NEVER write secrets (API keys, tokens, passwords, credentialed connection strings) into `AGENTS.md`, `AGENTS.local.md`, or any other doc — secrets belong only in the local `.env`
- create `docs/` subdirectories if they do not exist
- keep all documentation concise, practical, grammatical, code-verified, and free of fluff

If `CLAUDE.md` exists at the project root, do not modify it during `/document`. It is a thin bridge that imports `AGENTS.md` — content updates belong in AGENTS.md only.

## Step 5 — Sync any active plans
Search `.cursor/plans/` for active `plan-*.md` files (exclude `.cursor/plans/completed/`).

If active plans exist:
- prefer plans whose feature area overlaps the files changed in git diff / status
- if multiple active plans appear relevant, ask me which one should be synced before updating anything
- do not sync a plan based on progress percentage alone

For the relevant active plan:
- update task statuses, overall progress percentage, and `Current State / Handoff Note`
- when updating the `Current State / Handoff Note`, preserve any existing `Retro report:` pointer line verbatim — the lessons distillation step (Step 6.5) reads it after this sync runs
- add any newly confirmed design decisions, key findings, constraints, or verification steps
- keep updates concise, code-verified, and implementation-relevant
- do not implement new product code as part of this step

## Step 6 — Check for completed or near-complete plans
If a plan appears complete or near completion, verify it against the current codebase.
Use more than one signal:
- overall progress percentage
- task status pattern (all or nearly all 🟩)
- completion timestamp
- whether the recently changed files overlap the feature area the plan refers to
- the plan's `Lifecycle State`

**Detect plan schema (v22):** read the plan's `Planning Extraction Summary` for a `Workflow Schema:` line. If present, the plan is v22 (or later); retained items may carry `Risk if deferred:` and `Revisit by:` fields. If absent, the plan is pre-v22 / legacy; retained items won't have those fields. This affects how items are migrated below — see the v22 pass-through rule in the Completed — Follow-ups Retained handling.

If a qualifying plan is found, classify it as one of:
- `Completed — Follow-ups Retained`
- `Completed — Archivable`
- near-complete but still active

If the plan is `Completed — Follow-ups Retained`:
- do a reconciliation pass against the current code and the retained follow-up sections
- validate retained follow-up items against the current codebase before preserving them as-is
- identify whether each retained item:
  1. still clearly applies
  2. partially applies and needs re-scoping
  3. may no longer apply because the code or architecture changed

If anything changed materially:
- add an inline reconciliation note next to the retained item using this format:
  `[YYYY-MM-DD reconciliation] Still valid — no relevant code changes`
  or
  `[YYYY-MM-DD reconciliation] Needs re-evaluation — [short reason]`
  or
  `[YYYY-MM-DD reconciliation] Superseded — [short reason]`

Then:
- migrate enduring knowledge into durable docs where appropriate
- keep `AGENTS.md` concise and pointer-based
- update `CHANGELOG.md` if needed
- **v22 pass-through:** if the plan uses Workflow Schema v22, preserve `Risk if deferred:` and `Revisit by:` fields verbatim on any retained items migrated into AGENTS.md or `docs/known-issues.md` — pass-through only, no transform. Do NOT assign stable IDs (`retained-NNN`) — that remains deferred (see master plan `Deferred — Actionable Later`). The generic `AGENTS.md` bloat guard (Step 7 below) now applies — graduated in v27.0.
- do NOT recommend archiving or deleting the plan unless the user explicitly asks to close out the retained follow-ups
- tell the user the plan remains loadable as a retained follow-up context source

If the plan is `Completed — Archivable`:
- ask whether to run a plan-to-docs reconciliation pass
- if the user agrees:
  - read the plan and current code
  - migrate enduring knowledge into the appropriate durable docs
  - keep `AGENTS.md` brief and pointer-based
  - update `CHANGELOG.md` if needed
  - tell the user what was migrated and where
  - tell the user whether the plan can now be archived or deleted

If the plan is near-complete but still active:
- sync progress, findings, constraints, and handoff state normally
- do not archive or delete

## Step 6.5 — Lessons distillation (propose-and-confirm)
Distill recurring, run-evidenced gotchas into the curated lessons store at `docs/lessons.md`. This step is propose-and-confirm only — a lesson is NEVER written without explicit user confirmation.

Resolve inputs, in this order:
- the active plan's `Current State / Handoff Note` for a `Retro report:` pointer line — read that report if present
- otherwise glob `.cursor/loops/retro-*.md` for run reports
- plus session evidence: recurring patterns visible in this session's work, the plan's `Review Findings Log`, and recorded gotchas in existing docs
Retro reports are gitignored and transient — their absence is normal, never an error; session evidence alone is a valid input.

Curation bar (anti-cruft) — propose a candidate lesson only when it is:
- recurring (seen more than once across runs/sessions) or clearly general (obviously applies beyond the single incident), AND
- not already housed where it belongs (`AGENTS.md` runnable knowledge, `docs/integrations/`, or another durable doc) — never duplicate existing docs into the store

For each qualifying candidate, one at a time:
- present the proposed lesson with its evidence (which report, round, or session event it comes from)
- on confirmation: write it to `docs/lessons.md`, creating the file on first use and adding a brief pointer to it in `AGENTS.md` (e.g. under Subsystem Documentation); merge near-duplicates into the existing entry rather than stacking a new one
- on decline: the candidate leaves no trace — do not record it anywhere
Also propose retiring existing lessons that have stopped recurring or have been promoted into a durable doc — retirement is propose-and-confirm too.

If nothing qualifies, say so in one line, end this lessons-distillation step, and continue to Step 7 — do not propose lessons on thin evidence.

Headless / loop invocations NEVER write the store: collect qualifying candidates and surface them (in the run summary or plan handoff note) for the next interactive `/document` to propose. There is deliberately no AUTO-DISPOSABLE branch here — lessons are human-confirmed by definition.

## Step 7 — AGENTS.md bloat guard (propose-and-confirm)
After updating the docs, run a lightweight bloat check on `AGENTS.md`. This keeps the project briefing lean across repos. It is propose-and-confirm only — never auto-migrate.

Trigger the guard only when BOTH a structural smell AND a high size threshold are present (structural-smells-primary, so a lean downstream `AGENTS.md` is never nagged):
- structural smells: stacked session blocks (several `Last Session` / `Previous Session` / `Earlier Session` / `Older Session` entries); repeated or duplicated `Documentation Status` blocks; an oversized `Current Status` that has accreted multiple releases; large per-version rollback/recovery or release-history dumps embedded directly in `AGENTS.md`
- size threshold: `AGENTS.md` is well beyond a lean briefing (rough guide: many hundreds of lines / tens of KB). A small `AGENTS.md` (e.g. under ~150 lines) is presumed healthy even if a mild smell is present.

If the guard does not trigger, say so in one line and stop — do not propose migrations on a healthy file.

If it triggers, propose (do NOT perform yet) migrating the stale or bulky content into the repo's existing `docs/` layout, reusing the same migrate-on-confirm pattern as the Step 6 archivable path:
- name the specific blocks to move and the target doc(s) under `docs/` (create a focused doc if none fits)
- leave a concise pointer stub in `AGENTS.md` where each block was
- NEVER move `CHANGELOG.md` (it is already the separate history surface) and NEVER move durable subsystem docs that belong where they are
- migrate verbatim — preserve any commands, code-checkout lines, `Risk if deferred:` / `Revisit by:` fields, and rollback instructions exactly

Only on the user's confirmation: perform the migration, leave the pointers, and tell the user what moved and where. The deep periodic doc audit (accuracy + placement across all docs) is a separate, heavier pass and is out of scope for this in-run guard.
