# /execute-loop — index of named paragraphs

Generated with the skill's reference files; do not edit by hand. Each file below lists, in its own order, the section headings it carries and every paragraph that opens with a name in bold. To find a named paragraph, search this file for the name, then open the file it is listed under.

## references/s01-overview-and-dispatch.md

- section: What it does / does NOT do
- section: Roles
- Composer
- Executor
- Delegate (optional)
- Peer
- section: Argument dispatch (TOTAL — resolved before the wizard)
- No argument
- Exact `probe`
- Exact `accounts`
- Any OTHER argument
- section: The accounts probe submode (`probe` — strictly read-only)
- The pre-call liveness line — IMMEDIATELY, BEFORE any subprocess:
- The roster line:
- The one table:
- section: Account management (`accounts` — interactive-only)
- Add (standalone branch).
- Delete (interactive-only; quarantine, never removal).

## references/s02-wizard-probe-and-triage.md

- section: Setup wizard (interactive, before preflight)
- The structured-question contract
- Step 0 — probe available models (mandatory, first; canonical definition).
- `codex`
- Cursor subagents
- `claude`
- `claude` account profiles:
- The account router — `claude-switch-route` (v41.0 router mode; detection in wizard prose on BOTH paths — the probe script never runs it, so the manual path and the script path do exactly this):
- (a) Reuse lookup:
- (b) Defaults feasibility:
- Q1 — opening triage (one message; show only the feasible options).
- Q1C — cloud host? (asked on every CONFIGURING path — presets and custom — immediately after the Q1 choice; the reuse-last and defaults paths revalidate a stored `cloud=` key instead of re-asking, absence = ask once).
- Q1R — keep or switch (the reuse-last/defaults interstitial; fixed placement between Q1 and the close table).

## references/s03-wizard-questions.md

- Q1 presets — the two quick-setup flows.
- Architect OFF preset:
- Architect ON preset:
- Ephemeral-host persistence item (both presets, conditional-applicable):
- Monitor delivery item (both presets, conditional-applicable — v32.2):
- Router item (both presets, conditional-applicable — v41.0):
- Delegation item (both presets, conditional-applicable — v43.0):
- Away mode item (both presets — v34.0; default yes from v36.0):
- Q2 — architect mode (the custom branch opens here).
- Q3 — executor (or architect) menus, fixed batching.
- Q3b advisor item (both branches — the executor/architect role only).
- Q4 — peer menus.
- Q5 — run settings (one compact message, defaults pre-filled).

## references/s04-wizard-close.md

- Close — mandatory on every path (custom, presets, defaults, and reuse).
- Persistence.

## references/s05-backends.md

- section: Backends (capability-conditional)
- Cursor subagent (Task tool)
- `codex exec`
- `claude -p`
- Live session (executor only)
- `cursor-agent` is not a backend
- Spawn wrapper (SHIPPED default — `scripts/loop-spawn-wrapper.sh`).

## references/s06-architect-and-advisor.md

- section: Optional delegating executor ("architect")
- Delegation posture (the run-settings key `delegation=conservative|broad`, the wizard's Q3d answer, carried to a spawned architect on its spawn prompt (a live-session architect reads it from the plan's `Loop config:` line); the rails per posture are stated ONCE here — the wizard, the close table, loop step 1, STICKY, and `/retro` point).
- Delegable under `conservative`:
- NOT delegable under `conservative` (architect-held beyond the triad):
- Log every delegation — per-shape channel.
- section: Optional advisor (any backend)
- Mechanism N — native `--advisor` (auto-preferred when eligible).
- Mechanism C — the workflow consult role (every other combination).
- Consult triggers + the per-phase budget (Mechanism C).
- The consult package (bounded by construction).
- Mechanism-C transport matrix.
- Composer-driven consult fallback (any advised backend whose in-executor spawn fails or is ungranted):
- Degradation + reuse.

## references/s07-preflight-1-14.md

- section: Preflight (before the first phase)
- Load the plan.
- Cross-repo read roots (re-derived each run; no `Loop config:` key).
- Run isolation + ownership claim (a lettered sub-step, deliberately not a renumber — steps 3–11 keep their numbers; dry-run-aware).
- State the caps and scope
- Establish the executor's model family.
- Confirm each chosen backend is installed and authenticated
- Harness probe (CLI executor backends only).
- Validate cross-family.
- Filesystem-escape baseline.
- Tee-log rotation.
- Wake-mode resolution (the `Wake:` artifact).
- Usage baseline (warn-only).
- Lessons consult (appended step — steps 1–11 keep their numbers).
- Authorization attestation (the `high-auto=` authority boundary; appended step — steps 1–12 keep their numbers; the SUCCESSOR of the v31 label snapshot — the `[gates: high-auto-ok]` label grammar and the `OWNERSHIP: label-snapshot` record are RETIRED at v32: recognize historical records on replay, never emit either forward — D1/PR-HIGH-002).
- Notification-policy rendering (appended step — steps 1–13 keep their numbers; THE ONE owner of the `LOOP_NOTIFY` render — every other site points here).

## references/s08-preflight-15-17.md

- Router mode preflight (appended step — steps 1–14 keep their numbers; THE ONE owner of the composer-side bounded runner and its per-call disposition table — Step 0's router probe, the re-pick and the manual switch of Usage-exhaustion recovery, the release of Mechanical close enforcement, and the host rehearsals point here and never restate it).
- The composer runner (the ONE statement — v46.0: `scripts/loop-run-bounded.py`, on every host; in v45.0 and v45.1 it was the helper's `run-bounded` subcommand, which the helper now refuses — exit 2, a `REFUSE:` line naming the script, nothing run; v46.1: the runner itself refuses under a spawned role's environment — The runner's permission, below).
- The runner's permission (the ONE statement; a Claude Code composer only).
- Role settings shield (appended step — steps 1–15 keep their numbers; THE ONE statement of what a spawned `claude -p` role reads).
- Composer identity and the watcher (appended step — steps 1–16 keep their numbers; THE ONE statement of the identity write, of the `watcher:` line, and of the watcher script's permission — the Resume contract, the pre-departure check, and the companion card point here).
- What it writes.
- What it prints
- The exit code is read, three ways.
- What the record is for, and its limit.
- The watcher script's permission (a Claude Code composer only — the runner's rule of step 15, by pointer, with this script's line).
- Setup-remediation classification (one rule for every wizard/preflight readiness or probe failure).

## references/s09-run-isolation.md

- section: Run isolation (worktree-per-run)
- The isolation-run ID (`<iso-id>`).
- Per-run log root (worktree runs).
- Backend-keyed worktree location
- Creation order at sub-step 2b (worktree mode; pinned).
- The registry is an ATOMIC INTENT JOURNAL
- Release groups (the plan's release boundary; stated ONCE, here).
- Phase-range extension (`phases=` currency).
- The ownership marker (every editing mode — worktree AND `branch`/`none`).
- Authority + the per-close-path outcomes (stated ONCE — here).
- Verified merge-back
- Green close, merge disabled
- A non-final group's merge
- Pause / crash / resume
- Pre-creation failure
- Any non-green close
- Merge-back preconditions (`merge=auto`; composer-run; LOCAL only).
- Mechanical close enforcement (the run-close helper).
- `branch` and `none` are NON-ISOLATING.

## references/s10-loop-steps-1-3.md

- section: The per-phase loop
- Spawn a fresh executor
- Build the phase
- Converge

## references/s11-loop-steps-4-9.md

- Cross-check
- Composer seat (DEFAULT — every backend): the composer drives `/peer-loop`
- Executor seat (documented OPT-IN — `peer-seat=executor`, validated peer-spawn-route backends only): the executor runs `/peer-loop` in-session
- Opt-in failure falls back to the composer seat:
- Peer spawns run foregrounded — never background-and-end-turn.
- Composer takeover mid-pass (the opt-in seat's recovery; its TWO-LEG resume path is also the default seat's canonical per-round routing).
- Escape checks follow the spawning session:
- Per-pass cap keys (MECHANIZED on the `ROLE: start role=peer` record; the composer supplies the values).
- MUST-PAUSE inside an in-executor peer pass (the opt-in seat):
- Smoke
- Pause if needed
- Document
- Commit (default ON)
- Discard + advance
- section: Phase detection + bounded discretion
- Unit = a phase
- Plan-time grouping decides where reviews happen
- Run-time discretion is add-only:
- Release groups:

## references/s12-safety-gates.md

- section: Safety gates — the loop PAUSES, it never bypasses
- MUST-PAUSE (headless auto-disposition contract).
- Composer-seat gate policy (`gates=` / `cap-raise=` / `high-auto=` — Loop-config-scoped, additive key-groups).
- Executor-verified triage is the gate-routing authority (composer seat).
- Notify-at-gate (durable, deduped, PAIRED, tiered).
- Live-user-smoke pause (mandatory).
- Premium boundary.
- Never auto-push.
- Filesystem-escape check.
- MUST-PAUSE surfacing from a spawned executor.
- Inconclusive over unsafe.
- Composer-shell failure — probe the degraded surface before pausing.
- Composer duties are never asks.
- The composer's own questions (stated once, here).

## references/s13-away-entry.md

- section: Away mode
- What it is.
- Record grammar.
- The state.
- The read
- The CI verdict
- The census
- Entry.
- Precondition.
- Which scope tokens can be offered.
- Starting it.

## references/s14-away-departure.md

- The pre-departure check.
- Blocking / you can unblock now
- The batch and the departure file.
- Call 1 — what the operator can unblock now:
- Call 2 — after call 1's answers:

## references/s15-away-grant-and-stops.md

- The grant.
- The use-time check.
- What stops, what waits, and what is decided while a grant is bound.
- The four stops.
- Always the operator's.
- "The composer decides"
- Production hold.
- The operator's word wins — a hold is a record.
- The away live smoke
- Who:
- What:
- How:
- What is observed must be this phase's build.
- Record:
- Failure:
- Checklists:

## references/s16-away-release-work.md

- Release work
- Order at the end of the run.
- After the green close
- Staging before a merge that releases to production
- Staging after the merge
- Production
- Admitted on the path.
- (a) Before every production act — the shared prerequisites, in this order, before the irreversible step:
- (b) Before a dispatched step only — after (a), in this order:
- (c) After every production act — the receipt, then the check.
- A merge that itself releases to production
- Final admission to a production act (stated ONCE, here; (a), (b), the merge bullet above, the foreign-merge check's allow clause, Records → A foreign clear and a coordinated wait, `/close-run` item 7, and the Production hold point).
- The foreign-merge check — an unattended production act never ships another run's unreleased work.
- A failure after the merge
- After the merge nothing is written to the base checkout

## references/s17-away-fix-cycle-nudge-watcher.md

- The fix cycle — one reviewed cycle for a pull request that cannot merge.
- When:
- The run's state is unchanged.
- The cycle:
- Prepare first — nothing is recorded until the cycle's shape is known.
- Spawn dependencies, through the whole cycle.
- The cycle count per close
- The nudge (a timer in the composer's own session, armed ONLY while a grant is bound).
- What it is for.
- Which composer arms it.
- The interval is 30 minutes
- What it costs
- The prompt is fixed text in which four validated values vary
- Arming
- Cancelling
- A firing.
- The watcher and the seat (what continues a run whose composer is gone, and what keeps two composers from writing its records).
- The watcher
- A takeover composer is the composer
- The seat

## references/s18-away-stop-and-end.md

- Stopping an away run (ONE protocol, three ways in. A grant is ended only as Ending the grant states — "back" / "away off", "autonomy off" or a `config-revoke key=gates`, a widening's end of the grant it replaces, and the automatic ends; an ordinary message never ends one, and the stop command ends none).
- The stop command
- "back" or "away off"
- "autonomy off"
- The composer's side of the stop command — the wake rule.
- Ending the grant, messages while away, and the report.
- The belated end (stated ONCE, here).
- The report after an end.
- Widening
- The reminder line.

## references/s19-away-records.md

- Records for acts on the operator's behalf
- Keys on existing records.
- A decision with no open pause
- A decision that closes an open pause
- An agent-run smoke
- A release act
- A push-fired deploy
- The guard detects a missed start; it does not prevent the act.
- The CI verdict.
- A hold.
- A set refresh.
- A pre-approval.
- A re-baseline (helper-written, unpaired).
- A foreign clear and a coordinated wait (Release work item 5's foreign-merge check; the records and the mechanics, stated once here).
- The effective set and accepted versions (stated ONCE, here; every reader of "the departure file's" release machinery set points here).
- A park
- Flush.
- The report

## references/s20-usage-commit-coordination.md

- section: Usage-exhaustion recovery (claude pools)
- Wait
- Switch account
- Continue in composer
- section: Auto-commit (git-safety)
- Commit authority is COMPOSER-SEAT ONLY (mechanical, all permission tiers).
- section: Coordinating with other runs

## references/s21-termination.md

- section: Termination
- Group end (the group close; stated ONCE, here; not a stop — the run continues).
- Group done
- Stalemate
- Cap reached
- MUST-PAUSE
- Review-integrity failure
- User stop
- Isolation close (every stop path above).
- Persist-before-close (the CANONICAL close-contract order; runs on every run whose resolved config carries `persist=on` with the compatibility invariant holding — `isolation=worktree|branch` AND `autocommit=on`, the Q5 item's applicability rule; `persist=off` runs skip straight to the isolation-close resolution).
- Flush queued records
- Run `/retro` while the plan is still Active
- Secret-pattern sweep
- Materialize ONE bounded tracked evidence file
- Plan pointer update
- Commit on the run branch
- Lifecycle close/cleanup

## references/s22-visibility-wake.md

- section: Visibility + run-state
- Per-role visibility.
- Progress heartbeat (two-tier).
- Wake arming artifacts (wake grammar, three REQUIRED families — canonical definition; the OPTIONAL journal family on the next bullet is additive and separate).
- Writers:

## references/s23-visibility-records.md

- Journal line family (ADDITIVE, optional-emit — admitted from two observed harness runs).
- Stall watchdog (check-then-classify).
- Usage checkpoint (warn-only).
- `ROLE:` log lines (canonical definition).
- `ROLE: handoff` exit sentinel (same `ROLE:` family — no new prefix).

## references/s24-visibility-resume-config.md

- Run-state persistence.
- Sticky rehydrate (the every-wake companion card — REQUIRED composer duty).
- Resume contract (composer context loss ≠ run over — canonical recovery sequence).
- `Loop config:` line (wizard-config persistence).

## STICKY.md

- section: 1. You are the COMPOSER — orchestrator ONLY
- section: 2. Three duties are NEVER asks — do them, never offer them
- Wake/monitor arming
- `/document`
- section: 3. Wake — NON-OPTIONAL while any composer-owned CLI executor/architect is live
- section: 4. Spawn guard — mechanical, before EVERY executor/architect spawn
- section: 5. Spawn-prompt invariants (carry in EVERY executor spawn)
- section: 6. Peer-orphan recovery — take over, never ask
- section: 7. Autonomy ceiling — composer seat, config-governed
- section: 8. Paths
- section: 9. Coordinating with other runs

## references/c01-role-and-wake.md

- Fix briefs ROUTE, never design.
- Relay fidelity is BIDIRECTIONAL and mechanical.
- `scope=all` auto-advance
- Layer 1 (exit wake):
- Under `delivery=fg`:
- "Background shell" means the host TOOL's background mode
- Layer 2 (quiet-window + exit watch): default `monitor`
- Launcher legs.
- Wrapper legs (v48.0 — the wrapper writes the end of its own leg).
- The waiting rules (canonical: SKILL → loop step 1 → The waiting rules — what was read is said there).
- Stopping a role:
- Anchor discriminator (mechanical):
- Exit-classify child-kind routing:
- Consume-completeness, on EVERY wake (with the rehydrate):
- Idle re-entry checkpoint (D8) — run `idle-check` on EVERY wake, unconditionally, BEFORE any new spawn:
- Journal grammar (canonical admission: OPTIONAL; this card MANDATES emission for composers following it) — MECHANIZED: every composer-voice record is TOOL-EMITTED via `python3 scripts/loop-journal.py emit <TYPE> --run <runkey> --role <role> [--log <probe-log>] key=value …` (unknown types/subtypes/enum values REFUSE — invention is structurally impossible on tool-written lines), and mechanized shapes are NEVER hand-authored (Constraint 8: models supply values, tools supply format; a hand-typed line where a tool emission exists is the violation):

## references/c02-spawn.md

- Retry only on confirmed-absent, under a lock.
- Spawn and arming are ONE act.
- Escape-check record — ONE per HEADLESS ACTIVATION, COMPUTED, never hand-typed (F-04).
- Consume the wrapper's evidence after every wrapper spawn closes:
- The codex peer launcher — the route for EVERY composer-seat codex peer round on a run with a run worktree.
- Router mode (only while the `Loop config:` line carries `router=on`; otherwise nothing here applies).

## references/c03-dispositions-and-records.md

- Executor-verified triage is the routing authority (operator-set):
- Cap raises (`cap-raise=ask|auto-plus-one|follow|executor`; DEFAULT `executor`, operator-set — v33.0 D2; absent/malformed → `ask`):
- Away mode (the every-wake use-time check).
- Per-event record emission — every record below is ONE `loop-journal.py` invocation: you supply the JUDGMENT values (`severity=`/`verified=`/`choice=`/`reason=`/`detail=`); the tool owns format, keys, `mode=`, `class=`, the desktop notice, and pair atomicity
- DISPOSITION-TIME — at EVERY composer-seat disposition, EVERY severity, EVERY route; the pair is owed BY THE DISPOSITION — it fires even when no verify leg ran:
- PHASE-BOUNDARY + EVERY Termination stop path — flush BEFORE the commit record and BEFORE ending:
- GATE-DECISION — the operator closes a surfaced gate
- MID-RUN-CHANGE — ANY `Loop config:` key, at the change event:
- PHASE-CLOSE:
- Gate identity + resume:

## references/c04-paths-and-coordination.md

- (no named paragraph)
