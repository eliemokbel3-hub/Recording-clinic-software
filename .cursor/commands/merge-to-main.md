---
description: Safely merge the current branch into main with preview, confirmation, and deployment reminders.
---

Please help me merge the current branch into `main` safely.

## Step 1 — Confirm branch and cleanliness
Run:
- `git branch --show-current`
- `git status --short --branch`

If I am already on `main`, say so immediately and ask whether I actually meant to push `main` instead.

If there are uncommitted changes, ask whether to:
1. commit first
2. stash first
3. stop

## Step 2 — Fetch and preview
Run:
- `git fetch origin`
- `git diff origin/main...[current-branch] --stat`

Summarise what will be merged into `main`.

If there are tests or a build command in the project, recommend running them before the merge.

## Step 3 — Confirm
Ask me:
`Ready to merge [current-branch] into main? This may trigger a production deployment (e.g. Railway).`

Wait for confirmation.

## Step 4 — Merge
Once confirmed:
- `git checkout main`
- `git pull --ff-only origin main`
- `git merge --no-ff [current-branch]`

If conflicts occur, stop and help me resolve them safely before any push.

## Step 5 — Push main
After a successful merge:
- `git push origin main`

Confirm the push and remind me to review the hosting platform's deployment logs.
Remind me that I am now on the `main` branch.

## Step 6 — Post-merge reminders
If relevant, remind me to:
- run production migrations
- add or update the platform's production variables
- delete the feature branch

Ask before deleting any branch.

## Step 7 — Plan file completion check
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
