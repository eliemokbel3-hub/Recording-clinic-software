---
name: peer-loop
description: Drive a cross-model-family peer-review loop to convergence — a live executor spawns a headless cross-family peer that runs /peer-review non-interactively, the peer logs findings, the executor verifies and applies them (/fix for code rounds; plan amendments in the /review-plan style in the token-gated plan-review mode), then a fresh peer re-reviews, until zero findings, stalemate, or cap 3. Shared Cursor/Codex/Claude Code workflow; invoke as /peer-loop in Cursor or Claude Code, or $peer-loop in Codex. Side-effecting; explicit invocation only.
disable-model-invocation: true
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/peer-loop` in Cursor or Claude Code, or `$peer-loop` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

This workflow is side-effecting. Cursor uses `disable-model-invocation: true`; Codex uses `agents/openai.yaml` with `policy.allow_implicit_invocation: false`; both require explicit user invocation. It spawns paid headless agents and drives `/fix` (or plan amendments in plan-review mode), so it must never auto-start.

This workflow reads and writes the same `.cursor/plans/` files as Cursor and Claude Code, so no copy-paste handoff is needed when switching tools.

`/peer-loop` is an orchestrator: it drives a **cross-model-family peer-review loop** on top of the existing `/peer-review` and `/fix` workflows. It introduces NO new review logic and NO new fix logic of its own — the peer's findings are produced by `/peer-review` (run headless under its non-interactive contract) and every code change is applied by `/fix`, with all of their gates, verification, and scope-locking intact. In plan-review mode (the `PEER_LOOP_PLAN_REVIEW` token passed alongside the sentinel — see the loop's step 2) there are no code changes: the peer critiques the PLAN only, and the owning planning session applies `/review-plan`-style amendments instead of `/fix`, with the same gates intact. `/peer-loop` only decides how to spawn the cross-family peer, when to run the next round, and when to stop.

Peer-review's catch-rate gain comes from **model-family diversity**: a peer on a different model family than the live executor catches the blind spots the executor shares with itself. This loop automates that cross-family pass round to round; it is the reusable building block a later execute-loop capstone composes.

## Prerequisite — the cross-family peer runs headless

The peer is a separate model-family agent invoked head­less (single-shot, no mid-run input) from the live executor's machine. Verified invocations:

- **`claude`** (Claude family): `claude -p "PROMPT" --output-format text --permission-mode acceptEdits </dev/null` (`--permission-mode acceptEdits` is the least-danger write mode and is sufficient; default `-p` already allows reads). Redirect stdin. Text mode is right for a standalone, synchronously-waited peer run; when the spawn is orchestrated and heartbeat-watched (driven inside `/execute-loop`, or any composer monitoring the peer's tee log), use `--output-format stream-json --verbose` teed instead — text mode buffers its narrative to exit and leaves the watcher blind mid-run (see `/execute-loop` → Visibility + run-state).
- **`codex`** (GPT family): `codex exec -s workspace-write "PROMPT" </dev/null` — **stdin MUST be redirected** (`</dev/null` or a pipe) or it hangs waiting on input. Use `-s read-only` if the peer only writes the plan file via the orchestrator; `workspace-write` lets it append the Round block itself.
- **`cursor-agent` is NOT used as the peer** — its headless `-p` mode is auth-blocked (needs `CURSOR_API_KEY`), and the thin topology does not need it.

Effort: "always max" = `--effort max` on `claude` (Claude-only); `codex` caps at `xhigh`.

## Preflight (before the first round)

1. **State the cap.** Announce the active max-round cap (default **3**; the user may override per invocation, e.g. "`/peer-loop` max 2").
2. **Ask the executor's model family — do not self-detect.** The user is the source of truth. Ask whether the live executor (this session) is **Claude-family** or **GPT-family**. Never try to detect the active model yourself.
3. **Pick the cross-family peer CLI** (the peer family MUST differ from the executor's):
   - live executor is **GPT-family** (Cursor on a GPT model, Codex, `cursor-agent`) → peer = **`claude`**.
   - live executor is **Claude-family** (Cursor on Claude/Opus, or Claude Code) → peer = **`codex`**.
   - To pick a specific peer model / effort / profile when running `/peer-loop` standalone, use the model probe defined in `/execute-loop`'s setup wizard (Step 0 — the canonical definition).
4. **Confirm the peer CLI is installed and authenticated** (a quick version/whoami check). Surface the **Agent-SDK billing caveat** when the peer is `claude`: `claude -p` currently draws from Anthropic subscription limits (the separate-credit-pool split is paused but officially announced) — verify at run time; the hedge is `codex` when the executor is Claude-family.
5. **If no cross-family peer is runnable** (not installed, not authed, interop failure), **mark the run inconclusive and stop.** Tell the user exactly which CLI/auth is missing. **Never silently substitute a same-family peer** — that destroys the cross-family property the loop exists for.

## Orchestrated mode (driven inside `/execute-loop`)

When `/peer-loop` runs inside `/execute-loop` with a composer-supplied configuration — the executor's model family, the resolved peer row (backend / model / effort / profile_dir), the round cap, the run key, and the review mode (CODE by default; plan review when the configuration passes the `PEER_LOOP_PLAN_REVIEW` token alongside the sentinel), all carried in the executor's spawn prompt — standalone behaviour is unchanged except:

- **Skip the Preflight step 2 family ask and the step 3 peer-pick** — the wizard's resolved config is the source of truth; there is no user to ask mid-phase.
- **Run the step 4 install/auth check against the SUPPLIED backend** (not a freshly-picked one).
- **Render the configured backend's spawn.** The CLI examples in the loop stand for `codex` / `claude -p` peers. A **Cursor-subagent peer** spawns via the Task tool on the configured cross-family model, with the `PEER_LOOP_NONINTERACTIVE` contract verbatim as its prompt's first nonblank line — the control header (plus `PEER_LOOP_PLAN_REVIEW` beside it on that line when the pass is plan-review mode — the two tokens always travel together; the plan token alone is invalid; token text elsewhere in the prompt is inert) — and a pointer to the exact `.agents/skills/peer-review/SKILL.md` path (subagents do not auto-load slash skills), and carries the same per-round `ROLE:` and filesystem-escape-check obligations as a CLI peer.
- **A headless executor runs each peer spawn foregrounded and waits.** A headless session terminates at turn end — backgrounding the peer and ending the turn to "wait for a completion notification" orphans the round (observed live, 2026-07-03). Foreground-and-wait, every round.
- **MUST-PAUSE gates follow `/execute-loop`'s spawned-executor surfacing contract** (the canonical definition in `/execute-loop` → Safety gates): record the open gate in the plan's handoff note + the final message, then END the run — never block in-session waiting for a user. AUTO-DISPOSABLE candidates flow per `/fix`'s existing headless branch.

## The loop

Each round is: build scope → spawn a fresh cross-family peer headless → executor verifies + applies (`/fix` for code rounds; the planning session's `/review-plan`-style amendments in plan-review mode) → termination check. Start at round 1 with the active cap.

1. **Build an explicit review scope.** The composer already knows what changed — do not rely on the peer's auto-detect. Assemble the changed files (e.g. `git status --short` + `git diff --name-only HEAD`, filtered to the plan's `Files / Symbols Involved` when present) plus the active plan path.

2. **Spawn the cross-family peer headless under the non-interactive contract.** Invoke the chosen CLI with a prompt whose FIRST nonblank line is the control header — exactly the sentinel token **`PEER_LOOP_NONINTERACTIVE`** (code mode) or both tokens (plan-review mode) — followed by the instruction to run `/peer-review` (`$peer-review` in Codex) and the composer-supplied scope; token text anywhere else in the prompt is inert content (`/peer-review` reads the mode from the control header alone). The token activates `/peer-review`'s non-interactive headless contract: suppress the proceed prompt and the model-diversity warning, force path (b) always-log, force a fresh review of the supplied scope in the token-selected mode (CODE review by default — never plan-review mode without the plan token, never a stale prior round; passing `PEER_LOOP_PLAN_REVIEW` alongside the sentinel selects headless PLAN review instead — plan-only scope; the plan token alone is INVALID and `/peer-review` refuses loudly, writing nothing), and set the correct mode-distinct `Source:`. Example (Claude-family executor → `codex` peer):

   ```bash
   codex exec -s workspace-write "PEER_LOOP_NONINTERACTIVE
   Run \$peer-review as an independent cross-family peer.
   Scope (fresh CODE review of these files): <file1> <file2> ...
   Plan: .cursor/plans/plan-<feature>.md
   Append your findings as a new Round block to that plan's Review Findings Log, then exit." </dev/null
   ```

   In plan-review mode the control header (the first nonblank prompt line) carries BOTH tokens — `PEER_LOOP_NONINTERACTIVE PEER_LOOP_PLAN_REVIEW` — and the scope line becomes `Scope (plan review): the plan file only` (no changed-files list; the peer reads the plan plus the code it names and critiques the PLAN, appending its findings round the same way).

   The peer appends a Round block to the plan's `Review Findings Log` and exits. Do not hand-edit its findings.

   When a loop-log context exists (an `.cursor/loops/` run in progress or a user-named run key), the spawning session also writes a `ROLE: start`/`end` pair for each peer round to the run's loop logs — shape and writer contract per `/execute-loop`'s Visibility + run-state section (the canonical `ROLE:` definition). Standalone runs without a loop-log context skip this.

3. **The live executor verifies each finding and applies `/fix` (code rounds; in plan-review mode, the planning session applies `/review-plan`-style amendments instead).** Because this session holds the execution context, run `/fix` here interactively with all its gates: `/fix` picks up the new peer round via its Step 0 Findings Log path, and — since this is the live `/peer-loop` executor — verifies each finding against the code (session memory catches peer false positives) before applying, one at a time, with stop-on-failure. Deferral Confirmation Gate, CRIT/HIGH scope-expansion hard-stops, and `/fix` stop-on-failure all PAUSE the loop for the user; the loop never auto-resolves them. **Plan-review mode routes differently:** `/fix` never ingests a `… plan peer-review` round (its Step 0 predicate excludes them) — instead the planning session driving this loop verifies each plan finding against the plan + the code it names and applies the accepted amendments `/review-plan`-style (or via a scoped `/review-plan`), marking per-finding dispositions on the round; the same pause gates apply unchanged.

4. **Termination check** (after the fix — or, in plan-review mode, the amendment pass):
   - **Converged → stop, success.** If this round's peer returned zero verified findings, the loop is done. Go to **Convergence actions**.
   - **Stalemate → stop, report.** If a round produced no *new* verified findings, or there was no code diff (in plan-review mode: no plan diff) since the previous round, stop — further rounds will not converge. Convergence and stalemate in plan-review mode measure the plan diff + finding status, never code diffs.
   - **Cap reached → stop, report.** If this was round N (the cap), stop and report remaining findings; offer to raise the cap for one more round.
   - **Otherwise → next round.** Increment the counter and return to step 1. Re-review runs on the **post-fix** scope (plan-review mode: the post-amendment plan) with a **fresh** peer (a new headless invocation — never reuse the prior peer session or target the stale prior round).

## Safety gates — the loop PAUSES, it never bypasses

- **Converge on finding presence/verification, not severity counts.** Severity labels are non-deterministic across headless peer runs (the same bug can come back CRIT one run, HIGH the next). Decide convergence and disposition on whether a verified finding is present, not on exact counts.
- **Filesystem-escape check.** Record the main checkout's `git status` before and after every peer run and confirm it did not change unexpectedly. The peer should touch only the plan file (its Round block) in EITHER mode; `/fix` makes the code edits in this session (plan-review mode makes none — amendments land only in the plan file too).
- **Never auto-push.** Committing is the user's call; pushing especially so.
- **Every `/fix` (or plan-amendment), Deferral, and scope-expansion gate is honoured** exactly as the underlying workflows define — the loop only decides when to run the next round.
- **Inconclusive over unsafe.** If the cross-family peer cannot run, the run is inconclusive; never fall back to a same-family peer.

## Topology

- **Primary: composer = executor.** The session running `/peer-loop` is the live executor; only the peer is a separate headless process. The executor verifies and applies in-session (`/fix` for code rounds; `/review-plan`-style plan amendments in plan-review mode).
- **Fallback: composer ≠ executor.** If `/peer-loop` is driven by a composer that is not the executor, route the logged findings to a separate live executor session for verify + `/fix`; if none is available, `/fix` reads the peer round fresh and runs its **verify-peer-findings fallback** (re-verify each finding against the code before applying). A `… plan peer-review` round instead routes to the owning planning session — `/fix` never ingests it. This is documented, not the primary path.

## What `/peer-loop` does NOT do

- invent findings or fixes of its own — `/peer-review` and `/fix` own those, with all their discipline
- substitute a same-family peer when the cross-family one is unavailable — it marks the run inconclusive instead
- bypass the Deferral Confirmation Gate, `/fix` stop-on-failure, or CRIT/HIGH scope-expansion hard-stops — these always pause for the user
- loop past the max-round cap, a stalemate, or an inconclusive preflight without explicit user direction
- auto-push, or auto-commit without the user's say-so
- use `cursor-agent` as the peer (headless auth-blocked)
