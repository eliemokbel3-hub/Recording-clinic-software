---
name: push
description: Review, stage, commit, and push changes safely with deployment-aware reminders. Shared Cursor/Codex/Claude Code workflow; invoke as /push in Cursor or Claude Code, or $push in Codex. Side-effecting; explicit invocation only.
disable-model-invocation: true
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/push` in Cursor or Claude Code, or `$push` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

This workflow is side-effecting. Cursor uses `disable-model-invocation: true`; Codex uses `agents/openai.yaml` with `policy.allow_implicit_invocation: false`; both require explicit user invocation.

Please help me commit and push my current work safely.

## Step 1 — Review current state
Run:
- `git status --short --branch`
- `git diff --stat`

Summarise:
- what changed
- whether I am on `main` or a feature branch
- whether pushing this branch is likely to trigger a production deployment

## Step 2 — Check upstream state safely
Run:
- `git fetch origin`

Then determine whether the current branch has an upstream or matching remote branch.

If no upstream or remote branch exists yet:
- tell me this looks like the first push for this branch
- do not run remote-ahead comparison commands yet
- continue with the normal review, staging, and commit flow
- when pushing, use `git push -u origin [current-branch]`

If a remote branch does exist:
- run `git log HEAD..origin/[current-branch] --oneline`

If the remote is ahead of local:
- tell me clearly how many commits are ahead
- explain the risk of pushing without pulling
- ask whether to pull first or continue anyway

## Step 3 — Secret and risk check
Before staging anything, explicitly check for risky files such as:
- `.env`
- `.env.*`
- key or certificate files
- dump files
- generated secrets
- anything else that clearly should not be committed

Flag anything risky and stop for confirmation if needed.

## Step 4 — Choose what to stage
Ask whether to:
1. stage only the relevant changed files you list
2. stage everything relevant
3. let me specify files manually

Do not assume `git add .` is okay.

## Step 5 — Suggest commit messages
After staging choice is clear, suggest 3 commit messages:
1. brief
2. standard
3. detailed

Ask me to choose one or write my own.

## Step 6 — Commit and push
Only after I confirm:
- stage the agreed files
- commit with the approved message
- if this branch has no upstream yet, push with `git push -u origin [branch-name]`
- otherwise push normally with `git push`

Confirm whether the push succeeded.

## Step 7 — Post-push checklist
If relevant, remind me about:
- the hosting platform's deployment logs (e.g. Railway)
- production migrations
- the platform's production variables
- the extra risk of pushing to `main`

## Step 8 — Plan file completion check
Check whether any plan files exist in `.cursor/plans/` (excluding `.cursor/plans/completed/`).

If a related saved plan appears complete, verify its `Lifecycle State`.

If the state is `Completed — Follow-ups Retained`:
- check whether `/document` has been run to migrate enduring knowledge
- remind the user that the plan is intentionally being kept as a follow-up context source
- do NOT offer archive/delete by default
- only offer archive/delete if the user explicitly says the retained follow-ups are no longer needed

If the state is `Completed — Archivable`:
- check whether `/document` has been run to migrate enduring knowledge
- then offer the normal archive/delete options:
  1. Move it to `.cursor/plans/completed/`
  2. Delete it
  3. Leave it as is
- Action the chosen option.

If the state is still Active or near-complete:
- do not offer archive/delete
