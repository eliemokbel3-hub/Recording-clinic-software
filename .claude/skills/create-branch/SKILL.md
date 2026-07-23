---
name: create-branch
description: Suggest and create a branch name safely before feature or fix work. Shared Cursor/Codex/Claude Code workflow; invoke as /create-branch in Cursor or Claude Code, or $create-branch in Codex. Side-effecting; explicit invocation only.
disable-model-invocation: true
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/create-branch` in Cursor or Claude Code, or `$create-branch` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

This workflow is side-effecting. Cursor uses `disable-model-invocation: true`; Codex uses `agents/openai.yaml` with `policy.allow_implicit_invocation: false`; both require explicit user invocation.

Please help me create a branch for the work I am starting.

## Step 1 — Check current state
Run:
- `git status --short --branch`

If there are uncommitted changes, explain the situation and ask which path I want:
1. Create the new branch now and keep the current changes on it
2. Commit first, then create the branch
3. Stash first, then create the branch
4. Stop and let me handle it manually

## Step 2 — Ask what I am working on
Ask me: `What are you working on?`

## Step 3 — Suggest branch names
After I answer, suggest 3 branch names using the best prefix:
- `feature/`
- `fix/`
- `hotfix/`
- `chore/`

Rules:
- lowercase only
- hyphens instead of spaces
- short and descriptive

## Step 4 — Confirm and create
Ask me to choose one or type my own.
Once confirmed:
- run `git checkout -b [chosen-branch]`
- confirm the new branch
- remind me that pushing this branch will not normally deploy unless our workflow says otherwise
