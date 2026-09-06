---
description: Present a simple git menu for the most common workflows.
---

Ask me which git task I want.

Menu:
1. Create a new branch
2. Review, commit, and push changes (`/push`)
3. Merge current branch into main (`/merge-to-main`)
4. Check current status
5. Pull latest changes safely
6. View recent commits
7. Roll back a bad deployment (`/rollback`)
8. Something else

If I choose:
- 1 → check `git status --short --branch` first (if there are uncommitted changes, ask whether to carry them onto the new branch, commit first, or stash first), ask what I'm working on, suggest 2–3 names following the project branch-naming conventions in `project-workflow.mdc` (`feature/` / `fix/` / `hotfix/` / `chore/` prefix, lowercase, hyphens, short and descriptive), then run `git checkout -b <chosen-name>` and confirm
- 2 → use the push workflow
- 3 → use the merge-to-main workflow
- 4 → show branch, status, and whether there are unpushed commits
- 5 → first check if the working tree is clean before pulling
- 6 → show recent commits clearly
- 7 → use the rollback workflow
- 8 → let me describe what I need
