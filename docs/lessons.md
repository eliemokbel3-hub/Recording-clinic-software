# Project lessons

Recurring gotchas that bind from the first task of every session. Keep entries short, factual, and actionable.

## Agent shells are MSIX-virtualized on this host (2026-07-28)
All agent/composer shells on this machine run inside the Claude desktop app package (`Claude_pzs8sxrjxfjjc`). Writes to `%LOCALAPPDATA%` (and similar known folders) are silently redirected into the package's `LocalCache`, leaving links at the real path that user-launched processes cannot traverse. Consequences:
- Anything meant for the user-visible `%LOCALAPPDATA%\ClinikoScribe\` (model downloads via `scripts/setup-models.py`, host registration artifacts) must be run by the user from a normal terminal or Explorer, never from an agent shell.
- Agent-run tests cannot detect this divergence — they see the virtualized view and pass. Only a live user launch verifies user-context filesystem state.
- Symptom signature: a path exists for agent shells but raises `FileNotFoundError` for Explorer-launched apps. Fix pattern: user-context copy out of `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local\...` (see plan round 22, Phase 2 plan).

## A spawned agent must not end its turn while its children run (2026-08-02)
Four executors in the Phase 2 loop run spawned work — codex peer rounds, review-lens subagents — and then ended their turn waiting for it. A headless role terminates at turn end, so the children are orphaned and their results are never consumed; the composer had to salvage each one (stage-2 peer round 3, stage-3 round 8, stage-10 and stage-12 lens fleets). Foreground every child and wait synchronously in the same turn; if one wait cannot span the work, re-enter bounded waits in that same turn rather than ending it.

## Give executors facts, not a big document to read (2026-08-02)
A stage-11 executor was watchdog-killed after 600 s having done nothing but read a 656-line plan. The retry succeeded because the composer located the relevant code itself and inlined the facts (file, symbol, the exact loop to change) plus a "read only these two sections" instruction. Plans grow across a long run; spawn prompts should carry the extracted facts and point at specific sections, never "read the plan top-to-bottom".

## Give codex peers a basetemp outside the repo (2026-08-04)
Two of four peer rounds in the Phase 3A stage-1 run ran pytest and left temp directories INSIDE the repo (`.pytest-peer-review-round3/`, `desktop/.pytest-tmp-peer-round4/`, `desktop/tmpjsi6ocul/`) with ACLs that no agent shell can read or delete — `Get-ChildItem`, `takeown /R /D Y` and `icacls /grant` were all denied, so they became a manual cleanup task for the user. Round 3's happened to self-clean on exit; round 4's did not, so do not rely on it. Put in every peer prompt: do not create files or directories inside the repository, and if you run pytest at all pass `--basetemp` outside it. Better still, tell the peer not to run the suite — the executor's results are already recorded and review, not re-validation, is the peer's job. Stating this in round 6's prompt prevented a third occurrence.

## The escape check is blind to unreadable directories (2026-08-04)
`OWNERSHIP: escape-check` digests the **stdout** of `git status --short`, but git reports a directory it cannot open on **stderr** (`warning: could not open directory '…': Permission denied`). A peer-created directory with a restrictive DACL therefore leaves the digest unchanged and the record reads `result=clean` while a new, unreadable directory sits in the working tree. It was caught only by reading stderr. When a spawned role may create in-repo paths, check `git status` stderr as well as the escape-check verdict — the mechanical check alone is not sufficient evidence that nothing was created.

## Put the round-bookkeeping contract in the peer and fix prompts (2026-08-04)
`loop-history-check.py` stopped the stage-1 loop twice on bookkeeping, not code: once because a round block was PREPENDED (rounds must append in strictly increasing file order), once because a closed round had no `Review History` line (the seat that finishes a round owns its summary line — and when a line already exists from an earlier seat, it is UPDATED IN PLACE, never appended alongside). Each cost a full executor activation to repair. Stating all three rules in the round-6 peer prompt and the fix-leg prompt prevented further failures. Note the checker earned its keep: an executor misplaced a history line in the same run and its own re-run caught it before exit.

## Ephemeral terminal launchers kill GUI children (2026-07-28)
The chat Run button's throwaway terminal kills `scribe-app.exe` when it closes. Launch the desktop app via Explorer double-click or a persistent terminal only. Document user-facing launch methods in AGENTS.md (Step 12, Phase 2 plan).
