---
description: Safely revert a bad deployment by identifying the problem commit and reverting it with a staged review before committing.
---

Please help me roll back a bad deployment safely.

## Step 1 — Understand the problem
Ask me:
- What is broken?
- When did it start breaking?
- Do I know which commit or deployment caused it?

## Step 2 — Show recent commits
Run:
- `git log --oneline -10`

Help me identify which commit introduced the problem.

## Step 3 — Explain rollback options
Present the three options clearly:

1. **Revert a single commit** — creates a new commit that undoes one specific change. Safe. Keeps full history.
2. **Revert a merge commit** — undoes an entire branch that was merged. Use when a whole feature needs to be rolled back.
3. **Redeploy a previous version** — if the code is correct but the deployment is broken, trigger the hosting platform (e.g. Railway) to redeploy an earlier build without changing the code.

Ask me which approach fits the situation.

## Step 4 — Stage the revert for review
Once I choose option 1 or 2:
- run `git revert --no-commit [commit-hash]`
- run `git diff --cached --stat` to show me exactly what will be undone
- explain clearly what the revert will change

Do not commit yet. Wait for my confirmation.

## Step 5 — Commit the revert
Once I confirm:
- commit with a message like: `Revert: [short description of what was undone]`
- push to origin main

## Step 6 — Post-rollback checklist
After the revert is pushed, remind me to check:
- the hosting platform's deployment logs to confirm the rollback deployed
- whether any database migrations need to be reversed
- whether any of the platform's production variables need to be restored or changed
- whether any users were affected and need to be notified
