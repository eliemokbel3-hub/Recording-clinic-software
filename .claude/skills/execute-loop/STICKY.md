# /execute-loop — STICKY (every-wake rehydrate card)

Read this card, then the plan's `Current State / Handoff Note` (including its `Loop config:` line), at run start, on EVERY wake (any shell notification, monitor return, a watch arm's expiry notice, sentinel firing, a nudge timer's firing — under an away grant only: §7's use-time check FIRST, and a STALE firing runs no wake duty and cancels only its own timer, SKILL → `## Away mode` → The nudge — or user message that resumes orchestration), and after any suspected context loss. Before acting you must be able to state: runkey, phase, and the immediate next action. If you cannot, you have lost context — re-read the handoff note; if still unsure, run the Resume contract (SKILL.md → `## Visibility + run-state`, the Resume-contract bullet) instead of guessing. Never act from remembered intent. The RUN-START read is RECEIPTED, never merely performed: BEFORE the first spawn, emit `python3 scripts/loop-journal.py emit OWNERSHIP:sticky-ack --run <runkey> --role composer --repo <checkout> --log <probe-log>` into the run's FIRST stage probe log — the tool byte-compares both STICKY mirrors and computes `sticky_hash=` itself; the ack line must precede the file's first spawn boundary — `SPAWN_WRAPPER_START` or a non-composer `ROLE: start` — (canonical: the Preflight-tail gate; the oracle's `missing-sticky-ack` duty). A wrapper `STICKY_REREAD` line on any spawn's stdout is this card's RE-READ TRIGGER — re-read before consuming that spawn's events; re-acks after a re-read are additive, never required. Context pressure: you are the run's ONLY long-lived seat — executors/reviewers/peers are always fresh — and compaction is SURVIVABLE by construction (this card + the Resume contract recover from disk truth), so NEVER recommend abandoning or restarting the run mid-run for context reasons; re-read, lean on disk state, and at worst hand the composer seat over between phases via the Resume contract — the run continues.

This card COMPRESSES the canonical skill (`SKILL.md`, same directory) for wake-time use; it never overrides it — on any divergence the SKILL text wins. Section pointers below name canonical `##` titles verbatim.

The skill's own text is now `SKILL.md` (the core) with `references/s*.md`; this card's former detail is in `references/c*.md`, word for word. The `c` files compress the skill as this card does — on any divergence the `s` files win. A line below says what to check and names the file that says how (`c01` is `references/c01-role-and-wake.md`, and so on): open it before you act on what the line covers. A short line is a pointer, never the authority. A section a pointer names is on the file list in `SKILL.md`; a paragraph named in bold, in `references/index.md`.

Every wake owes these:
- before acting: the away check and the gates attestation read (§7);
- an interrupted consume finished before any new work (§3);
- the idle check before any new spawn, and a hung watcher healed (§3);
- before an executor or architect spawn, the spawn guard (§4); before any spawn or resume of a role, the seat line (§7).

## 1. You are the COMPOSER — orchestrator ONLY

- You spawn and coordinate; spawned roles do the work. You NEVER run `/execute`, `/review`, `/review-loop`, `/fix`, or `/peer-review` yourself, and you NEVER edit phase code, tests, or deliverable docs yourself.
- STOP THE LINE: if you are about to edit a phase file, or "just quickly fix" anything an executor built — stop. That is a role violation (the SIMP-001 class). Spawn or resume the executor and route the work there.
- Smoke feedback from the user: batch it and RELAY it to the executor verbatim. Relay is the whole duty — never implement feedback yourself.
- A fix brief routes, never designs: pointers only — plan path, round, finding keys; a verify-then-fix leg has the one leg-1 brief with its fixed mode line — c01.
- Relay an executor's handoff, assessment or MUST-PAUSE brief by printing the artifact verbatim through a tool call, never from memory; a summary and a menu go around it, never in its place. A gate's ask begins with the executor's recommendation, then yours; option 1 is the executor's — c01.
- Yours, never a role's: `/document`, commits (under `autocommit=on`), wake arming, the spawn guard, MUST-PAUSE surfacing. No spawned role commits or moves a ref: snapshot commit, ref and reflog state at each executor activation and around each default-seat peer spawn, and compare at every ownership transition and peer exit. Each commit gets its helper-written record; a UI-bearing phase's commit is refused before its smoke-pass record — c01.
- The configured review/peer cadence is CONFIG, not discretion: `cadence=every-phase` means every phase — "throwaway content" or "small phase" never licenses skipping `/review-loop`/`/peer-loop` (observed skipped live; the config or the user decides, never you).

## 2. Three duties are NEVER asks — do them, never offer them

1. **Wake/monitor arming** — armed at every CLI-role spawn, always. "Want me to start polling?" is a violation.
2. **`/document`** — run it at each phase close. Never a menu item.
3. Under `scope=all`, closing a finished phase or release group (the group close) and spawning the next phase's executor is performed, never offered — no question at a group boundary. An open `[operator]` task never holds a phase open — c01.

MUST-PAUSE gates, live-user smoke, usage-exhaustion choices, and Termination stops remain legitimate waits — those belong to the user; the three duties above never do. Except under a bound away grant — see SKILL → `## Away mode` (§7's away paragraph): there the composer disposes most of those waits itself, and the waits that section keeps — the four stops, the always-the-operator's items, and the others it names (its production hold among them) — still wait.

## 3. Wake — NON-OPTIONAL while any composer-owned CLI executor/architect is live

Detail: c01. Canonical: `references/s22-visibility-wake.md`, `references/s23-visibility-records.md`.

- Layer 1, the exit wake: the wake line preflight resolved is the mode authority for both layers and for delivery — arm exactly what it resolved; a mid-run delivery change re-runs Preflight step 10, and the new line prints before the next arm. Anchor patterns, host surfaces — c01.
- "Background shell" is the host tool's background mode, which notifies you; a raw shell background job notifies nothing and is a violation for a watched role or sentinel — c01.
- Layer 2: the monitor by default, a sentinel only when a monitor cannot arm. Consume every return in the same turn by the numbered checklist of tool calls: the monitor's record verified, verify-then-classify with the consume record, then the exit branch or the live branch (update, fresh re-arm). One live watcher per role. Every wake, liveness on, role live: if the newer of the watcher's arm time and its last return is older than about 1.5 times the interval, cancel it and re-arm fresh, with its armed line — c01.
- A launcher leg (§4 step 8): the launcher writes its start, escape-check record and end — you write none, except in the clean close. Watch the launcher, not its child; consume only once the launcher is positively dead; its exit line can only add a pause; on a launcher leg you kill nothing — c01.
- A wrapper leg: the wrapper writes its own end; you write the leg-bound consume verdict and no end, except the clean close, which the helper admits only when the leg reads `over`. `live` → watch it, never close it, never spawn beside it; `unknown` → the operator's attestation — c01.
- The waiting rules: every background spawn call carries an explicit timeout above the leg's expected length; a watch arm ends, and its expiry notice is a wake; exit 5, exit 6, or a background task that ended while the leg's live file stands, is not the role's exit and never a reason to spawn; a headless composer never ends its turn while a leg reads `live` — c01.
- Stopping a role: TERM to its recorded pid, only while its live file stands with no exit file and the pid answers; where the pid may now be another process's, send nothing — c01.
- Anchors are advisory: parse rate-limit events, reject the allowed statuses, and always verify at consume time — c01.
- At a role's exit, a launcher leg's apart, a live child, a killed-task record in the current activation's terminal window, or a missing or non-terminal handoff line, classifies it incomplete; recovery routes by the authenticated child kind (a bound peer child: §6) — c01.
- Consume-completeness, every wake: find the current activation's most recent event — a monitor exit or anchor, or a Layer-1 completion you know of — and check the records after it; finish an interrupted consume first, idempotently. On a launcher or wrapper leg an end with no later consume for that leg is the interrupted exit — c01.
- The idle check, every wake, before any new spawn: the tool computes the gap and decides; on a fired checkpoint reconcile every open role activation, closing a role only on positive death evidence — c01.
- Every `ts=` is a real clock read, local ISO with offset — never UTC, never composed — c01.
- An armed line describes only a wake mechanism that exists for the resolved mode; one printed without the mechanism is a violation. Its grammar — c01.
- Every composer-voice record goes through the records helper, never by hand; canonical line prefixes are reserved; narration goes to chat, never the probe log — c01.
- `layer2=none` on a composer-owned outer role is legal in two cases only: a real arm failure, named in its reason, or the resolved liveness-off case. A live outer role with no armed wake: fix the arming, foreground-wait it, or MUST-PAUSE — never continue dark — c01.

## 4. Spawn guard — mechanical, before EVERY executor/architect spawn

Detail: `references/c02-spawn.md` (c02). Canonical: loop step 1, `references/s10-loop-steps-1-3.md`; the wrapper: `references/s05-backends.md`.

1. Look up the prior executor's recorded identity — its shell id or pid, never a process-name pattern — c02.
2. Verify that identity dead; a quiet log is not dead. For a wrapper leg the role-liveness reader decides: this run's count must read `live:0` — a live leg is watched, an unknown leg pauses for the operator unless closed on their attestation; with no run worktree the count proves nothing, so read the leg's own files conservatively. First, the stop's wake rule (§7): a seat line reading `mark=yes` means no spawn, no resume — c02.
3. Spawn only on a confirmed-dead result, and record the new identity. The wrapper writes a wrapper-spawned role's start and end; you mint a fresh leg value per activation, never a reused one — c02.
4. Retry only on confirmed-absent, under the per-run spawn lock: probe for the first attempt's effects first; a held lock → adopt this run's own holder or surface a foreign one, never spawn beside it — c02.
5. Spawn and arming are one act: one message states steps 1–2's results, configures the watch, arms Layer 2 and prints the armed line — c02.
6. One computed escape-check record per headless activation — the wrapper's, the launcher's, or the helper's pre and post pair around any other headless spawn; no peer window unbracketed — c02.
7. After every wrapper spawn closes, read its escape-check result and exit-census child count: clean → proceed; dirty unattributed, or a capture failure → MUST-PAUSE in every gate mode; dirty with a fresh attribution → proceed with its records under `gates=executor`, else surface; children above 0 → an anomaly consume — c02.
8. The codex peer launcher is the route for every composer-seat codex peer round on a run with a run worktree: it runs one round and writes that round's records; start it from the base checkout, in a background shell, every parameter in the environment; do not edit the plan until it exits. Recipe, status lines, exit codes — c02.
9. Router mode (only under `router=on`): the route binary, the identity file and the role's fallback profile folder ride every wrapper spawn but a pinned leg's; on a resume the profile folder follows c02's resume-root rule and a routed identity's phase is its record's; the resume pin — c02. A routed role dead on a limit: `references/s20-usage-commit-coordination.md`.

## 5. Spawn-prompt invariants (carry in EVERY executor spawn)

Write every executor spawn prompt from c02 — never from this line. It carries, in full: absolute paths, and under `isolation=worktree` the worktree as every role's cwd, peers included; the task scope, the settings line's role rows (the peer row on an opt-in run only), the wall-clock anchor, and under `perms=scoped` on `claude -p` the grant shapes verbatim; the peer topology; the two exit rules — nothing the role started still running when its turn ends, and the validated exit declaration, then the handoff line, last; plain shapes for granted commands; the probe log's path as literal text; real clock reads; no commit and no ref moved; an open gate recorded, then the role ends; the brief written into the plan's handoff note.

## 6. Peer-orphan recovery — take over, never ask

The composer seat is the default: you drive each peer round and route its findings to the executor's resumable session in two serialized legs — leg 1 verifies and writes the tuples (fixing in the same activation only under a briefed verify-then-fix where every finding qualified); leg 2, once, carries every finding routed to fixing. Never a cold spawn while a resumable session exists. An opt-in executor that dies inside its own peer pass: take the pass over at once from the Findings Log — never ask, never restart at round 1, never mark an interrupted round converged; run the history checker first — c02.

## 7. Autonomy ceiling — composer seat, config-governed

Detail and record shapes: `references/c03-dispositions-and-records.md` (c03). Caps: `references/s21-termination.md`.

- The settings line's gate keys govern the composer seat only; absent or malformed, they fail closed to `strict`, `ask`, `off`. A disposition is never delegated to a spawned role — c03.
- Executor-verified triage is the routing authority: dispose from the round's verified-tuple record, never the peer's labels. Read the leg-route line first: after verify-then-fix the fix is applied and you write the same disposition pairs; that line beside a tuple that did not qualify is a review-integrity pause. A verified CRIT always pauses; a regression is never silently accepted or deferred — c03.
- A cap has three legal outcomes — raise, surface and ask, or (under `follow` or `executor` only) the recorded accept-close — never a silent close. Under `executor` the leg-1 cap verdict decides, after the pinned order's surfacing items and within its budget. Mint the pass id at each peer-pass start; a peer start carries the three pass keys, a cap transition its two-key bundle — c03.
- Gate mode is config. Under `executor`: follow the executor-verified recommendation, act and inform; the residual MUST-PAUSE list pauses — read it in `references/s12-safety-gates.md`, never from memory. Executor mode is attested; not bound, or revoked → behave as `strict` — c03.
- Away mode, every wake, before acting: the away check and the gates attestation read. Only a bound grant beside a bound executor attestation, in a run whose mode is `gates=executor`, is a grant: re-read the departure file, act under Away mode's own text — `references/s15-away-grant-and-stops.md` to `references/s17-away-fix-cycle-nudge-watcher.md`, never memory — and end every reply with the reminder line. Any other state is no grant. The same line prints holds, parks and pre-approvals: an open hold parks its release act before any start; an unknown reading parks — c03.
- A nudge firing: its prompt's grant number and hash must be the pair the away check reads as bound, else it is stale — run no wake duty, cancel only that timer. A composer record refused `seat-held`: a watcher takeover is this run's composer, you are not — do nothing until the operator's stop — c03.
- The stop's wake rule, grant or none: before every spawn and resume of a role read the seat line; `mark=yes` (not the mark of the takeover-only stop you have just run yourself at the operator's "back") → spawn and resume nothing, consume what has ended, write the must-pause pair, cancel the nudge without the identity write, wait for the operator's word. At a Resume read the seat line before the identity write. Closing the session is not a stop — c03.
- Every record is one helper invocation: you supply the judgment values, the tool the format; a record that gates an act is written before the act — c03.

At every composer-seat disposition, every severity and route, the pair is owed by the disposition:

1. One invocation emits the pair — auto-disposition on an auto route, must-pause where it fails closed. Record the pause first, with the log flag, then put the ask in chat from the block the helper prints; never emit the pair again to get the block — c03.
2. A finding-route gate key is tool-built from the round and finding id, never hand-composed — c03.
3. Severity is required on every finding-id route, a differing verified class beside it; a HIGH auto-route adds its attestation pair; a scope-expansion route copies the executor's impact value — c03.
4. A classify record with findings pending lists their ids; each id gets its own item-1 pair — c03.
5. Never journal `/document` or invent a line-start for bookkeeping — c03.

- Phase boundary and every Termination stop path: flush queued notices before the commit record and before ending — c03.
- An operator's decision on a surfaced gate is a gate-disposition record; on a gate not yet surfaced, its must-pause pair first — c03.
- A mid-run settings change: rewrite the line (replace, never stack) and one config-change record per key; "autonomy off" ends an open away grant first; a `high-auto` disable is revoke-first — c03.
- Phase close, in order: the smoke-pass record where a live smoke passed; the close-mode history check; the flush; the commit record; never a push; at run end the persist order under `persist=on`, then the mechanical close — no run is complete without its run-close record; then the chat-only progress line — c03.
- On a resume, pending notices come from the records by a dry-run flush, never memory — c03.

## 8. Paths

Every path and its rules: `references/c04-paths-and-coordination.md` (c04). In short:

- The plan: under worktree isolation the worktree copy is authoritative; a release stamp may have archived it — the close skill's plan resolution finds it.
- Logs: the run's base-side log folder; never copy a tee'd role log.
- The spawn wrapper (every `claude -p` spawn, respawn, resume) and the peer launcher: composer-only, parameters in the environment only; before relying on either, check its bytes against its committed blob from outside the script — untracked, dirty or different: do not invoke.
- The watcher script: yours are identity, seat, the read-only tick and, at the operator's word, stop — never its watch loop or an acting tick.
- A run's control files are never edited or hand-removed while the run is live (the mark apart, where the identity line itself says `mark=clear-failed`); on a worktree run a newly added phase is entered in the isolation journal's phase range before its spawn; a finished run is closed by the `/close-run` skill, the one carve-out from never pushing.

## 9. Coordinating with other runs

Before any merge or deploy: find the other live runs and whether their plans touch the same files, migrations or release lane; where they overlap, agree who goes first; never wait on another agent indefinitely. The standing prompt — c04.
