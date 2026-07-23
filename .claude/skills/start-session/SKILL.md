---
name: start-session
description: Safely start a work session by choosing local or cloud, then checking git state, syncing when appropriate, reading project context, and checking local readiness. Shared Cursor/Codex/Claude Code workflow; invoke as /start-session in Cursor or Claude Code, or $start-session in Codex.
disable-model-invocation: false
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/start-session` in Cursor or Claude Code, or `$start-session` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

Codex and Claude Code sessions are local to the CLI or IDE extension. If running in Codex or Claude Code, skip Cursor's Step 0 local/cloud session-type gate and continue with Step 1 as a local session.
Codex reads `AGENTS.md` directly; this repo ships `.codex/config.toml` with `project_doc_max_bytes = 65536` so large project docs are not silently truncated.

Please start this development session carefully.

## Step 0 — Choose session type
Ask immediately, before doing anything else:

"Is this a local desktop session or a cloud-agent session?"

1. Local desktop
2. Cloud agent

Do not run any checks, read any files, or inspect git state until the user answers.

If the user chooses Cloud agent:
- read `AGENTS.md` if it exists, then summarise:
  - what the project does
  - what was last worked on
  - current status
  - likely next priorities
  - if `AGENTS.md` does not exist, say so and continue
- read `docs/lessons.md` if it exists — recurring project gotchas recorded there apply from the first task of the session
- search `.cursor/plans/` for `plan-*.md` files (exclude `.cursor/plans/completed/`)
  - before summarising or selecting any plan, check for base-side isolation registries — `.cursor/loops/*-isolation` intent-journal files written by `/execute-loop`'s run-isolation contract. A live registry whose recorded authority is a run WORKTREE means the base copy of that plan is stale: redirect the plan read to the registry's recorded authoritative plan path, surface the isolation state (run branch, worktree path, journal state) alongside the summary, and never present the base copy as current merely because it exists. When the authoritative worktree lies outside this session's workspace, print the exact reopen/continue-in-worktree handoff (the recorded worktree path + how to resume there) instead of a stale-base summary. Validate the registry against the current base/worktree relationship (`git worktree list`, refs) before following it; on a stale or ambiguous registry, refuse to guess and ask.
  - classify each plan by its `Lifecycle State`: Active, Completed — Follow-ups Retained, or Completed — Archivable
  - if both active plans and `Completed — Follow-ups Retained` plans exist:
    - prioritise active plans in the session summary
    - mention retained-complete plans separately as optional follow-up context only
  - do not present a retained-complete plan as the current in-progress execution plan unless the user explicitly chooses it
  - if exactly one active plan exists, present:
    - the feature name
    - the Goal summary
    - the Overall Progress percentage
    - how many tasks are 🟩 Done vs 🟥 To Do vs 🟨 In Progress
    - the current 🟨 task or next 🟥 task
    - the Current State / Handoff Note
  - if the active plan's `Review History` has at least one real entry
    (ignoring the `(no reviews yet)` placeholder), surface the latest
    entry's `skew=` and `action=` fields in a single line, and — when
    there are unresolved findings to apply — recommend the route the
    classified Findings-Log line below resolves to (Source-aware:
    `/fix` for code rounds, not "fix the issues"; the owning planning
    session / a scoped `/review-plan` for plan peer-review rounds;
    both routes, unconflated, when both kinds are open). The two lines
    must never contradict — this line defers to or matches the
    classified Findings-Log summary. Keep this to one line — do not
    lecture.
    Examples (code rounds):
    - "Last review: round 2, skew=fix-induced, action=escalate. Use the matching fix workflow
       on a premium model rather than 'fix the issues'."
    - "Last review: round 1, skew=none. Use the matching fix workflow to apply findings."
    - "Last review: round 3, skew=pre-existing, action=triage-and-ship.
       No outstanding fixes."
    Examples (plan / mixed rounds):
    - "Last review: round 4, skew=none. Pending findings are plan peer-review rounds —
       route to the owning planning session or a scoped /review-plan, not /fix."
    - "Last review: round 5, skew=pre-existing. Code rounds → the matching fix workflow;
       plan peer-review rounds → the planning session / scoped /review-plan."
    If `Review History` does not exist or only has the placeholder, do
    not mention it — there is nothing to surface.
  - Additionally, check the active plan's `Review Findings Log` section
    if it exists. Count findings whose `/fix decision` is `Pending`,
    classifying each open round by its `Source:` (a `Source:` ending in
    `plan peer-review` = a plan-scoped round; anything else = a code
    round). If any are pending, surface one line per kind present:
    "Findings Log: N pending findings from round M. /fix will read these
     directly — no paste needed." (code rounds)
    "Findings Log: N pending PLAN findings from round M — plan-scoped:
     route to the owning planning session or a scoped /review-plan,
     never /fix." (plan peer-review rounds)
    Mixed rounds surface both lines without conflation. Skip this if no
    Findings Log exists or all decisions are filled.

  - Additionally, scan the active plan's `Tasks` section for unresolved
    `[decision]` tasks. If any exist, surface one line:
    "Decision points: N unresolved. Run /load-plan to see them, or
     /execute to resolve the next."
    Display-only and NOT schema-gated — surface regardless of
    `Workflow Schema:`. Skip the line if there are none.

  - **v22 plan-state surfacing** (skip these checks if the plan is pre-v22 — detected by absence of a `Workflow Schema:` line in the Planning Extraction Summary; pre-v22 plans fall back to legacy behaviour, suppressing all four checks below):

    - **Executor tier:** read the `Executor tier:` line. If the value is `fast/medium involved`, surface one line:
      "Plan executor tier: fast/medium involved. Premium-only tasks should be labelled `[executor: premium-only]`."
      If the value is `entirely premium` (default), do NOT surface — suppressed at default.

    - **Non-minor risk-tagged retained items (soft warning):** scan the plan's `Retained Follow-Up Items` and `Deferred — Actionable Later` sections for items with a `Risk if deferred:` field where the tag is anything other than `minor`. If at least one such item exists, surface one line:
      "⚠ M risk-tagged retained items need attention. Run /load-plan to triage."
      Suppress if M = 0.

    - **Overdue Revisit by (stronger cue):** for any item with `Revisit by: YYYY-MM-DD` where the date is past today's date, surface:
      "🔶 OVERDUE: K retained items past their Revisit by date. Run /load-plan."
      Suppress if K = 0.

    - **Security/correctness risk-tagged (prominent warning):** for any item with `Risk if deferred: security: ...` or `Risk if deferred: correctness: ...`, surface a SEPARATE prominent line distinct from the soft non-minor warning:
      "🛑 P retained items risk-tagged security/correctness — risk-accepted but not blocking plan lifecycle. Run /load-plan to review."
      Suppress if P = 0.

    None of these block — display + nudge only. Warnings fire on tag presence; the retained-item schema preserves tag (security/correctness/ux-degradation/blocked-work/minor), not source severity, so the surfacing cannot distinguish source severity tiers. The Release Readiness gate that would enforce blocking is deferred to v22+ (see master plan).
  - if multiple active plans exist, present a short numbered list showing feature name and progress percentage, and ask which one is relevant before summarising in detail
  - if no active saved plan exists, say so clearly and continue using `AGENTS.md` plus current branch/context only
- optionally inspect current branch / git status without pulling
- if `git log --oneline -5` or `git status --short --branch` shows a non-main branch with recent commits, mention it briefly as possible prior cloud agent work
- ask what to work on
- do not run: git pull, `.env` checks, `node_modules` checks, or first-run detection unless the user explicitly asks for them
- stop here — do not continue to Step 1

If the user chooses Local desktop:
- continue with the normal full flow starting at Step 1

## Step 1 — Check git state first
Run:
- `git status --short --branch`

Then decide what to do:
- If this is not a git repo, say so and continue without git actions.
- If the branch has no upstream, do not run `git pull`; explain that there is nothing to pull yet.
- If there are uncommitted local changes, explain the pull risk and ask whether to:
  1. continue without pulling
  2. stash first, then pull
  3. let me handle it manually

## Step 2 — Sync only if safe
If the repo is clean and has an upstream:
- run `git pull --ff-only`
- if fast-forward is not possible or conflicts appear, stop and help me safely

## Step 3 — Read project context
Read `AGENTS.md` if it exists, then summarise:
- what the project does
- what was last worked on
- current status
- likely next priorities

If `AGENTS.md` does not exist, say so and continue.

Also read `docs/lessons.md` if it exists — recurring project gotchas recorded there apply from the first task of the session.

Before summarising any plan state below (including the no-active-plan case), check for base-side isolation registries — `.cursor/loops/*-isolation` intent-journal files written by `/execute-loop`'s run-isolation contract. A live registry whose recorded authority is a run WORKTREE means the base-side plan copy is stale (or the authoritative plan exists only in the worktree): redirect the plan read to the registry's recorded authoritative plan path, surface the isolation state (run branch, worktree path, journal state) alongside the summary, and never present the base copy as current merely because it exists. When the authoritative worktree lies outside this session's workspace, print the exact reopen/continue-in-worktree handoff (the recorded worktree path + how to resume there) instead of a stale-base summary. Validate the registry against the current base/worktree relationship (`git worktree list`, refs) before following it; on a stale or ambiguous registry, refuse to guess and ask.

If no active plan exists but one or more plans are in `Completed — Follow-ups Retained` state, mention that follow-up context is available via `/load-plan`.

If an active plan exists in `.cursor/plans/` (excluding `.cursor/plans/completed/`) and that plan's `Review History` section has at least one real entry (ignoring the `(no reviews yet)` placeholder), surface the latest entry's `skew=` and `action=` fields in a single line, and — when there are unresolved findings to apply — recommend the route the classified Findings-Log line below resolves to (Source-aware: `/fix` for code rounds, not "fix the issues"; the owning planning session / a scoped `/review-plan` for plan peer-review rounds; both routes, unconflated, when both kinds are open). The two lines must never contradict — this line defers to or matches the classified Findings-Log summary. Keep this to one line — do not lecture.

Examples (code rounds):
- "Last review: round 2, skew=fix-induced, action=escalate. Use the matching fix workflow on a premium model rather than 'fix the issues'."
- "Last review: round 1, skew=none. Use the matching fix workflow to apply findings."
- "Last review: round 3, skew=pre-existing, action=triage-and-ship. No outstanding fixes."

Examples (plan / mixed rounds):
- "Last review: round 4, skew=none. Pending findings are plan peer-review rounds — route to the owning planning session or a scoped /review-plan, not /fix."
- "Last review: round 5, skew=pre-existing. Code rounds → the matching fix workflow; plan peer-review rounds → the planning session / scoped /review-plan."

If `Review History` does not exist or only has the placeholder, do not mention it — there is nothing to surface.

Additionally, check the active plan's `Review Findings Log` section if it exists. Count findings whose `/fix decision` is `Pending`, classifying each open round by its `Source:` (a `Source:` ending in `plan peer-review` = a plan-scoped round; anything else = a code round). If any are pending, surface one line per kind present:
- "Findings Log: N pending findings from round M. /fix will read these directly — no paste needed." (code rounds)
- "Findings Log: N pending PLAN findings from round M — plan-scoped: route to the owning planning session or a scoped /review-plan, never /fix." (plan peer-review rounds)

Mixed rounds surface both lines without conflation. Skip this if no Findings Log exists or all decisions are filled.

Additionally, scan the active plan's `Tasks` section for unresolved `[decision]` tasks. If any exist, surface one line:
- "Decision points: N unresolved. Run /load-plan to see them, or /execute to resolve the next."

Display-only and NOT schema-gated — surface regardless of `Workflow Schema:`. Skip the line if there are none.

**v22 plan-state surfacing** (skip these checks if the plan is pre-v22 — detected by absence of a `Workflow Schema:` line in the Planning Extraction Summary; pre-v22 plans fall back to legacy behaviour, suppressing all four checks below):

- **Executor tier:** read the `Executor tier:` line. If the value is `fast/medium involved`, surface one line:
  - "Plan executor tier: fast/medium involved. Premium-only tasks should be labelled `[executor: premium-only]`."
  - If the value is `entirely premium` (default), do NOT surface — suppressed at default.

- **Non-minor risk-tagged retained items (soft warning):** scan the plan's `Retained Follow-Up Items` and `Deferred — Actionable Later` sections for items with a `Risk if deferred:` field where the tag is anything other than `minor`. If at least one such item exists, surface one line:
  - "⚠ M risk-tagged retained items need attention. Run /load-plan to triage."
  - Suppress if M = 0.

- **Overdue Revisit by (stronger cue):** for any item with `Revisit by: YYYY-MM-DD` where the date is past today's date, surface:
  - "🔶 OVERDUE: K retained items past their Revisit by date. Run /load-plan."
  - Suppress if K = 0.

- **Security/correctness risk-tagged (prominent warning):** for any item with `Risk if deferred: security: ...` or `Risk if deferred: correctness: ...`, surface a SEPARATE prominent line distinct from the soft non-minor warning:
  - "🛑 P retained items risk-tagged security/correctness — risk-accepted but not blocking plan lifecycle. Run /load-plan to review."
  - Suppress if P = 0.

None of these block — display + nudge only. Warnings fire on tag presence; the retained-item schema preserves tag (security/correctness/ux-degradation/blocked-work/minor), not source severity, so the surfacing cannot distinguish source severity tiers. The Release Readiness gate that would enforce blocking is deferred to v22+ (see master plan).

## Step 4 — Local readiness check
Important: `.env` and `node_modules/` are normally in `.gitignore` and will not appear in the file tree or index. Use explicit terminal commands to check for them — do not rely on the file browser.

Run these checks:
```bash
echo "=== Local Environment Check ==="
test -f .env.example && echo "✅ .env.example exists" || echo "⚠️  .env.example not found"
test -f .env && echo "✅ .env exists (this is correct — it should be gitignored)" || echo "⚠️  .env missing — create from .env.example"
test -d node_modules && echo "✅ node_modules present" || echo "⚠️  node_modules missing — may need install"
ls package-lock.json yarn.lock pnpm-lock.yaml 2>/dev/null && echo "✅ Lock file found" || echo "⚠️  No lock file detected"
```

Then check:
- whether there appear to be missing environment variables (compare `.env` keys against `.env.example` if both exist)
- whether there are obvious pending migration steps or migration reminders in the repo

Report clearly:
- `.env` existing and gitignored = normal and correct
- `node_modules/` existing = normal after install
- only flag genuinely missing items or first-run indicators

First-run detection — if ALL of these are true, this is likely a new computer or first run:
- `node_modules/` (or the language-equivalent dependency folder) does not exist
- `.env` does not exist but `.env.example` does
- no lock file is present (package-lock.json, yarn.lock, pnpm-lock.yaml, etc.)

If first run is detected:
- consult `AGENTS.md`'s Local Run Steps / prerequisites (and `AGENTS.local.md` if present) first — use the recorded install and run commands when they exist
- otherwise inspect the project type
- suggest the install and run commands
- ask before running them

## Step 5 — Begin
Ask what I want to work on today.
