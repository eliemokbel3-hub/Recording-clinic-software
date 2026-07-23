---
name: end-session
description: Close out a session safely by checking whether /document should run first, updating closeout notes, flagging follow-up items, and offering a closeout choice. Shared Cursor/Codex/Claude Code workflow; invoke as /end-session in Cursor or Claude Code, or $end-session in Codex. Side-effecting; explicit invocation only.
disable-model-invocation: true
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/end-session` in Cursor or Claude Code, or `$end-session` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

This workflow is side-effecting. Cursor uses `disable-model-invocation: true`; Codex uses `agents/openai.yaml` with `policy.allow_implicit_invocation: false`; both require explicit user invocation.

Please close out this session properly.

## Step 0 — Check whether /document should run first
If an active plan exists in `.cursor/plans/` or the session involved feature work beyond simple bug fixes:
- determine whether `/document` has already been run in this session or whether durable docs/plan sync still appear to need updating
- if `/document` has already been run and no new meaningful work was done afterward, say so briefly and continue directly to Step 1
- otherwise recommend running `/document` first before closeout
- explain briefly: `/document` refreshes durable docs, syncs active plans, and can migrate enduring knowledge out of completed plans
- ask whether I want to run `/document` first before continuing closeout

If I choose yes:
1. run `/document`
2. once `/document` finishes, automatically resume `/end-session` at Step 1
3. do not ask me to manually run `/end-session` again

If I choose no:
- continue directly to Step 1

If the work was small and no active plan or durable doc changes are likely, continue normally.

## Step 1 — Update project notes
Update `AGENTS.md` to reflect:
- what was built, changed, or fixed
- any new environment variables
- any database schema changes
- current status
- what should happen next session

Keep this a concise session note, not a running journal — `/end-session` should not re-bloat `AGENTS.md`:
- update the existing `Current Status` / `Last Session` blocks in place rather than stacking a new dated block above the old ones
- keep durable or bulky detail (subsystem knowledge, integration notes, long rollback/recovery or per-version history) OUT of `AGENTS.md` — that belongs in focused `docs/` via `/document`, which also runs the propose-and-confirm bloat guard
- if `AGENTS.md` already carries stacked session blocks or large embedded history, recommend `/document` to migrate it into `docs/` rather than adding more

If `AGENTS.md` does not exist, offer to create it with the standard template structure:
- Project name, What This App Does, Tech Stack table, Links, Environment Variables table, Database Notes, Local Run Steps, Current Status, Last Session, Known Issues / Next Tasks, Subsystem Documentation, Documentation Status.
Ask the user to fill in the details or help populate from what is known.

## Step 2 — Update changelog
Update `CHANGELOG.md` under `Unreleased` using only the categories that actually apply:
- Added
- Changed
- Fixed
- Removed
- Security

Keep entries concise and user-facing.

## Step 3 — Flag follow-up items
Tell me clearly if any of these still need action:
- production database migration
- the platform's production variables update
- deployment log review
- unfinished work
- local-only changes not yet committed

**v22 retained-item surfacing** (skip these checks if the active plan is pre-v22 — detected by absence of a `Workflow Schema:` line in the Planning Extraction Summary; pre-v22 plans fall back to legacy behaviour):

- **Non-minor risk-tagged retained items (soft warning):** scan the plan's `Retained Follow-Up Items` and `Deferred — Actionable Later` sections for items with a `Risk if deferred:` field where the tag is anything other than `minor`. If at least one exists:
  - "⚠ M risk-tagged retained items need attention. Run /load-plan to triage in next session."
  - Suppress if M = 0.
- **Overdue Revisit by (stronger cue):** for any item with `Revisit by: YYYY-MM-DD` past today's date:
  - "🔶 OVERDUE: K retained items past their Revisit by date. Run /load-plan."
  - Suppress if K = 0.
- **Security/correctness risk-tagged (prominent warning):** for any item with `Risk if deferred: security: ...` or `Risk if deferred: correctness: ...`, surface as a separate prominent line:
  - "🛑 P retained items risk-tagged security/correctness — risk-accepted but not blocking. Run /load-plan to review."
  - Suppress if P = 0.

None of these block closeout — display + nudge only. Warnings fire on tag presence; the retained-item schema preserves tag (security/correctness/ux-degradation/blocked-work/minor), not source severity, so the surfacing cannot distinguish source severity tiers.

## Step 4 — Offer a closeout mode
Ask me which option I want:
1. Docs only — stop after updating notes
2. Docs + local commit
3. Docs + commit + push

Do not commit or push until I choose.

## Step 5 — If I choose commit or push
Before committing:
- run `git status`
- summarise what will be committed
- warn about any risky or secret-looking files
- suggest 3 commit message options:
  1. brief
  2. standard
  3. detailed
  - all suggested messages should be professional and human-sounding — no references to AI, Cursor, Claude, or agents

Ask me to choose a message or write my own.

Stage only the relevant files unless I explicitly tell you to stage everything.

If I choose option 3 and the push succeeds:
- remind me if this may trigger a production deployment (e.g. Railway)
- remind me about migrations or the platform's production variables if relevant
