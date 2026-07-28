# Project lessons

Recurring gotchas that bind from the first task of every session. Keep entries short, factual, and actionable.

## Agent shells are MSIX-virtualized on this host (2026-07-28)
All agent/composer shells on this machine run inside the Claude desktop app package (`Claude_pzs8sxrjxfjjc`). Writes to `%LOCALAPPDATA%` (and similar known folders) are silently redirected into the package's `LocalCache`, leaving links at the real path that user-launched processes cannot traverse. Consequences:
- Anything meant for the user-visible `%LOCALAPPDATA%\ClinikoScribe\` (model downloads via `scripts/setup-models.py`, host registration artifacts) must be run by the user from a normal terminal or Explorer, never from an agent shell.
- Agent-run tests cannot detect this divergence — they see the virtualized view and pass. Only a live user launch verifies user-context filesystem state.
- Symptom signature: a path exists for agent shells but raises `FileNotFoundError` for Explorer-launched apps. Fix pattern: user-context copy out of `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local\...` (see plan round 22, Phase 2 plan).

## Ephemeral terminal launchers kill GUI children (2026-07-28)
The chat Run button's throwaway terminal kills `scribe-app.exe` when it closes. Launch the desktop app via Explorer double-click or a persistent terminal only. Document user-facing launch methods in AGENTS.md (Step 12, Phase 2 plan).
