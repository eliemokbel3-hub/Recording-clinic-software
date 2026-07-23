# Cross-Agent Headless Orchestration (v27 Stage 4 keystone-spike recipe)

*This document is shipped and maintained by the bootstrap (`bootstrap.md`); it
contains observations verified on the source host (a WSL2 machine) — re-verify
host-specific details (binary paths, interop behaviour) on your own machine.*

The reproducible recipe + decisions from the v27 Stage 4 keystone spike
(`.cursor/plans/plan-workflow-v27-stage4-keystone-spike.md`). It proves the one
unproven primitive in the v27 program — **cross-agent headless orchestration** —
so Stage 5 (peer-review loop) and Stage 7 (execute-loop capstone) can be built on
evidence rather than a guess. Read this before building either loop; it tells you
the engine, the topology, the exact CLI invocations, the non-interactive peer
contract, the three-way gate-candidate classification, and the open risks.

**Go/no-go: GO.** Primitive A (build our own thin orchestrator) was proven
end-to-end, cross-family, with convergence, on 2026-06-29. Spike code was
throwaway (a git worktree + a synthetic fixture, since discarded); this doc is the
only durable artefact.

## TL;DR decisions

- **Build our own (A), don't adopt ralphex (B).** A is thin, reuses our existing
  `$peer-review` / `/fix` skills and `.cursor/plans/` Findings-Log schema natively,
  and keeps our review semantics (per-finding schema, executor-verifies-before-fix,
  the 3-way auto-disposition gate, the run-time cross-family rule) first-class.
  Borrow ralphex's proven *patterns* (below), not its binary.
- **Topology:** thin orchestrator (composer) → cross-family **peer** headless runs
  `$peer-review` non-interactively → writes findings to the plan's Review Findings
  Log → the **live executor** (the session that holds execution context) verifies
  each finding against the code and applies `/fix` → a **fresh peer** re-reviews the
  post-fix scope → repeat until zero findings / stalemate / cap 3.
- **Cross-family is computed at run time** from the *live executor's* model family.
  The peer family MUST differ from the executor family. Do not hardcode "claude is
  the peer" — that only holds when the executor is GPT-family.
- **A non-interactive peer contract is mandatory** because the headless CLIs are
  single-shot (no mid-run input). The contract suppresses the peer's interactive
  prompts and forces always-log + fresh-scope review.
- **The three-way gate-candidate classification runs correctly headless:** auto-apply
  only AUTO-DISPOSABLE findings (logged); never auto-decide a MUST-PAUSE.

## Environment verified (2026-06-29)

- OS: WSL2 (`linux …-microsoft-standard-WSL2`).
- `cursor-agent` 2026.04.08-a41fba1 (`/home/pc_1/.local/bin/cursor-agent`).
- `codex` 0.142.2 (`/home/pc_1/.local/bin/codex`), default model `gpt-5.5`, effort `xhigh`.
- `claude` 2.1.195 (`/mnt/c/Users/PC 1/AppData/Roaming/npm/claude` — Windows npm via
  WSL interop).

## Host setup — hardening a WSL loop host (v29.2)

Loop runs stress a WSL host in ways ordinary editing does not: tee logs append at
MB/min (a file-watcher storm), long-lived background shells and monitor subagents
hold resources for hours, and an editor's WSL bridge multiplies the watcher load.
Observed upstream (Cursor forum, fetched 2026-07-10): staff attribute WSL-remote
disconnects to in-distro server resource exhaustion (thread 155169; fix = explicit
`.wslconfig` limits), and a nightly-regression thread (160930) carries the inotify
watcher-exhaustion warning. One-time host setup before running long loops on WSL:

- **inotify limits (inside the distro) — BASELINE-FIRST.** An editor indexing a
  loop repo can exhaust `max_user_watches`, but distros and WSL kernels ship
  different defaults — probe the current value
  (`sysctl fs.inotify.max_user_watches`) and record it BEFORE touching anything:
  a host may already sit at or above a recipe's number (observed 2026-07-11: one
  reference WSL host's unconfigured baseline was already `524288`), and writing a
  fixed universal value can silently no-op — or REDUCE a higher-limit host. Raise
  only when the chosen target EXCEEDS the recorded baseline: persist via
  `/etc/sysctl.d/` (e.g. a `90-inotify-loops.conf` containing
  `fs.inotify.max_user_watches=<target>`), apply with `sysctl --system`, and
  verify the live value equals the target; if the baseline already has headroom,
  record no-change-needed instead of writing a file.
- **`.wslconfig` (Windows side, `%UserProfile%\.wslconfig`) — explicit resource
  limits.** The defaults, per Microsoft's WSL configuration reference: `memory` =
  50% of host RAM, and `autoMemoryReclaim` = `dropCache` (instant cache release) —
  automatic reclamation is NOT absent by default. The template's `gradual` is a
  DELIBERATE default change: slower, steadier reclaim, chosen for long loop runs.
  Give WSL explicit limits in the exact TWO-SECTION shape (`memory`/`processors`
  live under `[wsl2]`, `autoMemoryReclaim` under `[experimental]` — a reclaim key
  under `[wsl2]` is silently ignored):

  ```ini
  [wsl2]
  memory=24GB
  processors=8

  [experimental]
  autoMemoryReclaim=gradual
  ```

  Size `memory=`/`processors=` to leave the Windows side comfortable (the values
  above suit a ~64GB host). MERGE key-by-key with any existing `.wslconfig` — never
  replace the file; unrelated user settings must survive. **Apply gotcha:** the file
  takes effect only after `wsl --shutdown`, which kills ALL running WSL sessions —
  active agent sessions included — so apply it at a safe moment, never mid-run.
- **Editor watcher + search exclusions for `.cursor/loops/**`** — universal to ANY
  repo running loops: tee logs append at MB/min and storm the file watcher and the
  search indexer. In VS Code/Cursor workspace settings (`.vscode/settings.json`),
  add `**/.cursor/loops/**` to both `files.watcherExclude` and `search.exclude`;
  committing that file makes the exclusions travel with the repo.
- **PATH pinning for version-managed toolchains (v29.3).** A headless spawn's
  non-interactive shell skips the interactive init that version managers (nvm and
  kin) rely on — under WSL a spawned role can see NO `node`/`npm` (or a different
  version than the interactive shell sees) while the composer's own shell works
  fine, and node-dependent gates die `command not found`. Spawn prompts and
  committed gate wrappers PIN the toolchain: the absolute versioned bin path
  (e.g. `/home/<user>/.nvm/versions/node/<version>/bin/…` — resolve the version
  manager's location once and carry the literal resolved path; a `~`-prefixed
  value is NOT absolute and can cross argv/JSON harness boundaries unexpanded)
  or an explicit `PATH=<versioned bin>:$PATH` line inside the wrapper — the same
  pin-the-binary discipline the loop already applies to `claude` itself,
  extended to the repo's own toolchain (downstream run lesson, 2026-07-19).
- **Layer-2 watch-tool allowlist (v29.3; composer hosts with a harness-native
  watch tool).** Where the composer harness exposes a persistent watch tool
  (e.g. a `Monitor` tool) as the run's Layer-2 mechanism, the tool must be
  PERMITTED before the run starts — on a Claude Code composer host that means a
  project-level `.claude/settings.json` permissions entry, e.g.
  `"permissions": { "allow": ["Monitor"] }` — or every arm prompts/denies, which
  is not viable for an autonomous run. This is DOCS-ONLY guidance for the host
  owner: the bootstrap never ships or edits settings files (the v29.2
  workspace-settings precedent) — the fix is one-per-repo, written by the user
  or by a composer with an explicit confirm, never a payload. `/execute-loop`'s
  preflight step 10 runs the matching Layer-2 VIABILITY check — tool permitted?
  first call/arm succeeds? — resolving `layer2=sentinel` up front when the tool
  is gated (and preferring the sentinel outright on hosts with observed monitor
  fragility), so a gated tool degrades loudly at preflight, never silently at
  first spawn.
- **Editor release track: stable.** Nightly builds have shipped WSL-remote
  regressions (observed upstream 2026-07-10, thread 160930: a 3.5.8 nightly broken
  where 3.3 worked) — loop hosts should ride the stable track.
- **Composer architecture for long runs (lr291-evidenced ranking):** a fully
  WSL-native CLI composer (no Windows↔WSL bridge in the loop) > a native-side CLI
  composer making stateless `wsl.exe` crossings per command > an editor's WSL-plugin
  persistent-server bridge. The lr291 run (7.5h — Windows-native CLI composer,
  stateless `wsl.exe` crossings, WSL-native repo) finished with zero infra
  incidents, vs the recorded editor-bridge composer incidents on comparable runs (a
  composer-shell death mid-run; an unwatched-executor incident) — the persistent
  bridge is the fragile piece, not the model. The bridge remains fine for
  interactive work once the mitigations above are applied.

## Per-CLI headless invocation (verified from live runs)

| CLI | Family | Headless invocation | Auth | Notes / gotchas |
|---|---|---|---|---|
| `claude` | Claude | `claude -p "PROMPT" --output-format text [--permission-mode acceptEdits] [--allowedTools "Bash(<scoped>)"] </dev/null` (or pipe the prompt via stdin) | Works headless | Reads AND writes a WSL-path worktree via interop. `--permission-mode acceptEdits` is the **least-danger write mode and is sufficient** for file edits — no `--dangerously-skip-permissions` needed. Default `-p` mode already allows reads. Edits allowed under `acceptEdits`; UNGRANTED approval-gated shell is HEURISTIC — host-, version-, and config-dependent, with NO established allowed/denied command-class boundary (v27 Stage 8 C2 observed an `npm ...` denial on an earlier version; at 2.1.201 on the source host, 2026-07-10, several ungranted safe commands were auto-approved under `auto`/`acceptEdits` while the one observed denial was an out-of-workspace write — the auto-approval mechanism was not isolated, so treat attribution as inference and never key routing on assumed denials) — an orchestrating composer runs smoke/verification when the preflight harness probe or the grant set says so; scoped `--allowedTools` patterns are the DETERMINISTIC always-allow layer (verified 2026-07-02: `--allowedTools "Bash(npm --version)"` executed headless under `acceptEdits`). **`perms=bypass` recipe (user-opt-in tier, close-table-confirmed):** `--dangerously-skip-permissions` replaces `--permission-mode acceptEdits` AND any `--allowedTools` list (observed live 2026-07-10, 2.1.201: init `permissionMode: bypassPermissions`; ungated Write + unprompted shell with zero grants; the `.claude/` config-dir write-gating is LIFTED); the tier is INVOCATION-SCOPED — every `--resume` must re-pass the flag (a resume without it came up `permissionMode: auto`; the init event's `permissionMode` field is the deterministic per-invocation tier detector). Prefer narrow patterns (`Bash(npm run typecheck)`, `Bash(npx vitest run:*)`) over blanket `bash`; background long-lived processes (`npm run dev &`) or the session stalls; pipe/auto-confirm interactive prompts. **Live mid-run visibility:** `--output-format text` buffers the narrative to exit (a tee log can sit unchanged for a whole multi-minute run and flush at the end, and lines land out of chronological order) — for an orchestrated role, spawn with `--output-format stream-json --verbose` teed instead (verified 2026-07-03: events arrive as JSON lines in real time — init, per-turn assistant messages, tool-use `task_started`/`task_notification`, `result`; the stream also carries a live `rate_limit_event` line with `status` and `resetsAt`, usable for immediate limit-death detection). **Long-prompt shape (v29.2):** write a long spawn prompt to a gitignored file (e.g. `.cursor/loops/<runkey>-<role>-prompt.txt`) and deliver it via stdin redirect — `claude -p < promptfile`, the other flags unchanged — quoting-proof through any host interop layer that flattens or re-expands argv (the recorded `wsl.exe` class: embedded newlines flattened, the line re-expanded once before the inner shell runs, `$VAR`s arriving empty); observed live 2026-07-10: 7/7 incident-free long-prompt spawns in run lr291. |
| `codex` | GPT | `codex exec [-s read-only\|workspace-write] "PROMPT" </dev/null` | "Logged in using ChatGPT" | **stdin MUST be redirected** (`</dev/null` or a pipe) or it hangs on `Reading additional input from stdin...`. `--skip-git-repo-check` optional. Uses **bundled bubblewrap** for the sandbox (warns if `bubblewrap` not on PATH — optional `apt install bubblewrap` silences it). Prints a git diff of its edits. **`perms=bypass` recipe (user-opt-in tier, close-table-confirmed):** `--dangerously-bypass-approvals-and-sandbox` replaces the `-s` sandbox flag (verbatim from `codex exec --help`, codex 0.144.1; throwaway run observed live 2026-07-10 with run-header `approval: never` + `sandbox: danger-full-access` — the codex-side tier-verification surface); `codex exec resume` carries its OWN bypass flag and exposes NO `-s/--sandbox` option, so the tier is re-rendered per invocation, never inherited from the prior process. **The `workspace-write` sandbox denies localhost network** (observed live 2026-07-03: EPERM connecting to `127.0.0.1`) — a codex peer/role cannot run DB-backed or server-hitting suites; keep DB verification executor/composer-side, and peer reviews should state that split rather than reporting unrun DB suites as a gap. |
| `cursor-agent` | GPT | `cursor-agent -p "PROMPT" --output-format text` | **Headless BLOCKED** | Requires `CURSOR_API_KEY` (or `agent login`); the interactive login that `cursor-agent status` reports is **not** sufficient for `-p`. The thin-orchestrator topology avoids needing it. |

All three support single-shot and resumable multi-turn; transport is a composer
ergonomics choice, not a capability gap. The spike used single-shot.

**Headless `claude -p` CAN delegate natively (verified 2026-07-02):** a `-p` session
carries Claude Code's `Agent` subagent tool — a child spawned headless ran and
replied to a sentinel — and the tool takes a **per-invocation `model` parameter**
(enum `sonnet | opus | haiku | fable`), so a headless architect can pin its
delegates' model without any shell nesting or allowlisting. Children **inherit the
parent session's model unless explicitly overridden** — a delegating architect must
pin `model:` on every spawn or its delegates silently run on the architect's
(promo/metered) model. Model alias note: `--model fable` = `claude-fable-5`
(`fable-5` is rejected as an unknown slug). Ungranted headless shell approval
is HEURISTIC — host-, version-, and config-dependent (see the per-CLI table
row) — so the composer runs the smokes when the preflight harness probe or the
grant set says so; scoped `--allowedTools` grants (verified; see the per-CLI
table row) let the architect run its own gates deterministically, and a
`perms=bypass` executor needs no grant list at all (see the permission-tiers
bullet below). Keep grants narrow and background long-lived processes.

## Verification grants: wrapper scripts + the preflight harness probe

Scoped `--allowedTools` grants (per-CLI table above) let a headless `claude -p`
role run its own gates — but the grant SHAPE matters, and a grant that looks
right can still fail at run time. Observed live 2026-07-04 on a downstream
`/execute-loop` run:

- **Wrapper-script pattern (the recommended grant shape):** an exact-match
  grant like `Bash(npm run typecheck)` does NOT match the env-prefixed command
  form a repo may document (`TMPDIR=/tmp PATH=... npm run typecheck`) —
  observed live: nine denied attempts (~$4.50 of executor time) in one phase
  before discovery. Commit a wrapper script (e.g. `scripts/gates/typecheck.sh`)
  holding the env prefix + command, and grant the wrapper path instead:
  exact-match-friendly, injection-resistant (the granted string names one
  auditable committed file), and the env quirks live in one committed place.
- **`simple_expansion` hook gotcha:** a hook can block headless commands
  containing `$PATH`-style expansions (rejected with "Contains
  simple_expansion"); literal values work, and wrapper scripts sidestep the
  issue entirely.
- **Preflight harness probe (the recipe):** before the first real phase, spawn
  a ~30-second throwaway executor on the chosen CLI backend and have it run
  `git status` plus the run's exact verification commands (for `claude -p`,
  the grants confirmed on the wizard close table; for `codex`, the same
  documented gate commands — no grant mechanism, but the sandbox or a hook
  can still block them) — both must succeed. On failure, record
  composer-run verification up front
  (`/execute-loop` writes the optional `verify=composer` run-settings key) and
  offer the wrapper-script fix — discovering the breakage in a throwaway probe
  is strictly cheaper than nine denied attempts inside a paid phase. Skip it
  under dry-run and for live-session / Cursor-subagent executors. Canonical
  definition: `/execute-loop` → Preflight.
- **Permission tiers (v29.1): grants and wrappers are SCOPED-tier machinery.**
  Everything above describes `perms=scoped` — the shipped default. Under
  `/execute-loop`'s user-opt-in `perms=bypass` (wizard Q5; close-table-confirmed;
  offered only for backends with a supported rendering — `claude -p` / `codex`),
  the executor spawn renders the backend's bypass flag instead (the exact
  per-CLI recipes are in the invocation table above: claude
  `--dangerously-skip-permissions`, observed live 2026-07-10 at 2.1.201; codex
  `--dangerously-bypass-approvals-and-sandbox`, verbatim from `codex exec
  --help` at 0.144.1), NO grant list rides the spawn, and the preflight harness
  probe tests RAW command execution instead of grant shapes. The tier is
  re-rendered on EVERY invocation including resumes (claude `--resume` must
  re-pass the flag; `codex exec resume` carries its own bypass flag) — it never
  survives implicitly from the prior process. Bypass removes tool permission
  prompts — and WAIVES the close-table injection gate (the single close-table
  confirm is the entire gate) — but NEVER workflow gates: MUST-PAUSE gates, the
  live-user-smoke pause, the filesystem-escape baseline, and cross-repo
  read-root confirms all stand (the latter two are permission-tier-independent).
  Canonical definition: `/execute-loop` → Setup wizard Q5 + Backends.
- **Bypass host-gating + the one-pause scoped fallback (v29.3).** The wizard
  close-table confirm is a WORKFLOW gate, not a host grant — the COMPOSER host's
  own permission layer can still block the bypass spawn it tries to launch.
  Observed asymmetry (host/version-qualified, claude 2.1.201, 2026-07-20): a
  **Claude Code composer** BLOCKED the bypass spawn at its named "auto mode
  classifier" (category `[Create Unsafe Agents]`; attribution
  observed-with-named-mechanism — the classifier itself stated its
  mode/settings-conditional escape hatches), while a **Cursor composer** RAN the
  identical spawn ungated. Q5 marks bypass **likely-blocked** on a host observed
  to classifier-gate it — a wizard-time ADVISORY only, never the gate: the
  preflight harness probe (step 6, testing the actual bypass spawn shape) is the
  SOLE operative gate on every host. A probe spawn BLOCKED at the spawn level
  (the host refuses the bypass shape itself — distinct from verification
  commands failing inside a healthy spawn) routes to the ONE-pause ATOMIC scoped
  fallback, never a dead end: show the amended SCOPED Grants/`Permissions:`
  line, the user confirms ONCE, the resolved tier AND the persisted
  `Loop config:` `perms=` group normalize to `scoped` in that same transition
  (every later spawn AND resume re-renders scoped — bypass can never silently
  re-enable; re-enabling it is a fresh user decision at a future wizard), the
  harness probe re-runs on the actual scoped spawn shape, and the run proceeds
  only from that proven state; a scoped spawn STILL blocked at the spawn level
  is MUST-PAUSE — `verify=composer` covers only verification-command failure
  AFTER a successful executor spawn and never masks a spawn-level block.
  Canonical definition: `/execute-loop` → Setup wizard Q5 (the host-gate
  marking) + Preflight step 6 (the probe + fallback).

Effort: `codex` caps at `xhigh`; `claude --effort` supports up to `max` (Claude-only).
"Always max" = max-on-Claude/Cursor, xhigh-on-Codex.

## Model probes (wizard-time catalog discovery)

The `/execute-loop` setup wizard (Step 0) builds its per-role model menus from live
probes instead of hardcoded lists. **Script-first (v29.1):** the probes below are
implemented by the shipped read-only probe script `.cursor/bootstrap/probe-models.py`
(stdlib-only python 3; JSON-only stdout with `probe_schema: 1`; per-probe timeouts +
statuses; usage and advisor-capability probes behind the explicit `--usage` /
`--probe-advisor` flags — the latter is billed; exit 0 whenever JSON was emitted) —
wizard Step 0 runs the script first and falls back to the manual probes only when
the host has no python 3; the bullets below remain the canonical probe
definitions — the script is their deterministic executor, not their
replacement. Manual shapes verified 2026-07-03 on this host (WSL2;
codex-cli 0.142.4; claude 2.1.198 via Windows-npm interop):

- **`codex debug models`** — returns JSON `{"models": [...]}` with per-model `slug`,
  `display_name`, `default_reasoning_level`, `supported_reasoning_levels` (each an
  `effort` + description), and `visibility` (`"list"` = user-visible, `"hide"` =
  internal; offer only `"list"`). Probe cost ~0.6 s. Current visible catalog:
  gpt-5.5, gpt-5.4, gpt-5.4-mini (defaults medium), gpt-5.3-codex-spark (default
  high); all support low/medium/high/xhigh. **Stability caveat:** this is a *debug*
  subcommand — the JSON shape may change across codex versions; degrade to free-text
  model entry if it fails or misparses.
- **`claude`** — no model-catalog command exists. Curated aliases per `--model` help
  examples + the native subagent tool enum: `fable`, `opus`, `sonnet`, `haiku`
  (full names also accepted, e.g. `claude-fable-5`). Effort choices are enumerated
  in `claude --help` under `--effort`: low, medium, high, xhigh, max.
- **Cursor subagents** — no shell probe; enumerate the composer's in-context allowed
  slugs. Effort is encoded in the slug variant (e.g. `-thinking-xhigh`).
- **`cursor-agent --list-models`** — exists but returns "No models available for
  this account" headless (auth-blocked, consistent with the known `-p` block); not
  a usable probe target.

Per-run effort syntax (default = inherit; pass no effort flag unless explicitly
chosen, or you silently override the user's own CLI config, e.g. a
`model_reasoning_effort` pin in `~/.codex/config.toml`):

- `codex exec -m <slug> -c model_reasoning_effort=<level>`
- `claude -p --model <alias> --effort <level>`
- Cursor subagent: effort is the slug choice; no separate flag.

## Usage / rate-limit probes (warn-only checkpoint surfaces)

`/execute-loop`'s usage checkpoint reports account-pool percentages between phases
(warn-only — the loop never acts on the numbers). Neither CLI has a first-party
headless usage command; these are the best available surfaces, both verified live
2026-07-03 on this host, both degrading to "not exposed" on any failure:

- **claude** — `"<pinned claude>" -p "/usage" --output-format text </dev/null`
  (~2–7 s, no model call; per-profile: prefix with the profile's
  `CLAUDE_CONFIG_DIR` — plus `WSLENV=CLAUDE_CONFIG_DIR/p` through a Windows shim,
  see the multi-account section). The headline lines — `Current session: N% used ·
  resets …`, `Current week (all models): N% …`, per-model weekly lines — are
  official server-side percentages; the "Approximate, based on local sessions"
  caveat applies only to the contribution breakdown BELOW the headline. No
  machine-readable alternative exists yet (anthropics/claude-code#30764 tracks
  `claude usage --json`); recognize the headline text format.
- **codex** — the `app-server` JSON-RPC method `account/rateLimits/read`
  (~10 s, codex 0.142.4). Verified pipeline (stdin must stay open briefly or the
  server exits before the response flushes — a fully-piped one-shot that closes
  stdin immediately returns nothing):

  ```bash
  { printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"probe","title":"probe","version":"0.0.1"}}}'; \
    sleep 2; \
    printf '%s\n' '{"jsonrpc":"2.0","id":2,"method":"account/rateLimits/read","params":{}}'; \
    sleep 8; } | timeout 30 codex app-server
  ```

  The `id:2` response carries `rateLimits.primary` (5h window: `usedPercent`,
  `windowDurationMins: 300`, `resetsAt`) and `.secondary` (weekly:
  `windowDurationMins: 10080`), plus a per-limit breakdown and `planType`.
  **Stability caveat:** `app-server` is an experimental subcommand — treat the
  shape as version-dependent; `/status` remains TUI-only and there is no official
  headless status command (openai/codex#10233, #15281 track it).
- **Cursor subagents** — no usage surface is exposed to a composer; report
  "not exposed".

## Claude multi-account profiles (`CLAUDE_CONFIG_DIR`)

`CLAUDE_CONFIG_DIR` redirects Claude Code's entire config root — credentials,
settings, history, plugins — and is the official multi-account mechanism.
Per-profile login persists, and it works for `-p` headless, so one host can run
roles under different Anthropic accounts/orgs:

- **Pin the binary first (two-install failure mechanics, observed on this host
  2026-07-03):** hosts can carry TWO `claude` installs — e.g. a Windows npm shim
  at `/mnt/c/.../npm/claude` and a WSL-native nvm binary — and which one bare
  `claude` resolves depends on PATH order, which can differ between shells and
  sessions. A Windows exe launched from WSL receives no WSL env vars unless
  whitelisted in `WSLENV`, so `CLAUDE_CONFIG_DIR` silently no-ops through the
  shim: in the incident, probes, login, and post-login verification ALL hit the
  same wrong Windows-side store and agreed with each other — a login "for" a new
  profile actually re-wrote the default account's store, and every read-side
  check lied consistently. **Pin rule (v2 — enumerate, prefer native,
  probe-arbitrated):** enumerate the candidate binaries (`which -a claude` plus
  the known nvm bin paths, e.g. `~/.nvm/versions/node/*/bin/claude`) and prefer
  the **environment-native** candidate — the preference keys on the composer's
  execution environment, not the project's location: under WSL a Linux binary
  beats a `/mnt/c/...` Windows npm shim even for a project on `/mnt/c/...`,
  while on native Windows the npm shim IS the native binary. The bogus-dir
  isolation probe (below) arbitrates: pin the preferred PASSING candidate and
  use that absolute path in every probe, login command, and spawn of the run;
  warn about candidates that fail the probe — never silently pin a failing one.
  (The earlier resolve-once guidance — take whatever single binary `command -v
  claude` returns — is superseded: it pins whatever PATH resolves first, which
  is exactly how the shim got pinned in the incident above.) **Per-binary
  default identity:** the default account differs per binary — observed live:
  the shim's default account ≠ the Linux binary's default account — so after
  any pin or re-pin, re-show the pinned binary's default-account identity
  (`<pinned claude> auth status`); never assume it carried over from a prior
  run, a stored config line, or another binary.
- **No candidate passes the probe — the fix path (environment-readiness
  pause):** `/execute-loop`'s wizard MUST-PAUSEs here (Step 0). The PRIMARY fix
  is installing the environment-native binary — under WSL:
  `npm install -g @anthropic-ai/claude-code` with WSL node/npm — then
  re-probing. Observed live (2026-07-04, a downstream run): the host's only
  claude was the probe-failing Windows npm shim; after the WSL-native install,
  the bogus-dir probe PASSED, profiles enumerated, headless scoped
  `--allowedTools` shell grants worked, and a nested `codex exec` peer spawn
  worked — the install unlocks the cheap topology (in-executor `/peer-loop`,
  executor-run smokes), not just profile selection. An agent may run the
  install only after explicit user confirmation, and only after checking WSL
  node/npm exist (absent → hand the user the install instruction instead). The
  inline `WSLENV` prefix (see the WSL interop caveat below) is a
  workaround-grade fallback for runs that must stay on the Windows shim;
  continuing degraded means default account only, composer-run verification,
  and no in-executor peer pass.
- **List profiles:** the **default account** (no `CLAUDE_CONFIG_DIR` prefix;
  identity via the pinned binary's `auth status`) is always a choice — its
  config root may live outside `~/.claude*` (on this host it is Windows-side).
  Additional profiles: enumerate dirs matching `~/.claude*`, applying the
  probe script's eligibility predicate by hand — skip `*.lock` control dirs,
  `.quarantined-*` stores, and malformed/non-directory entries (a
  credential-less stub stays listed — the script emits it as a degraded
  row, and the manual path shows it identity-degraded the same way) — and
  realpath-dedup against the resolved default root so an aliased store
  lists once. **Show identities,
  not dir names:** `CLAUDE_CONFIG_DIR=<dir> <pinned claude> auth status`
  reports the bound email/org — present that, since the user picks by
  organisation.
- **Add a new profile:** create the dir → run
  `CLAUDE_CONFIG_DIR=<dir> <pinned claude> auth login` (plus the inline
  `WSLENV` prefix through a Windows shim) → the user completes the browser
  OAuth with the target org account (the one irreducibly human step) → verify the
  binding via `auth status` and echo the org → **artifact check:** require
  `.credentials.json` to exist inside the target config dir before declaring the
  profile ready. A login that wrote to the wrong store still passes `auth
  status` (it reads the same wrong store) but fails the artifact check —
  verified 2026-07-03: a correct profile login leaves `.credentials.json` in the
  profile dir.
- **Delete (quarantine) a profile:** interactive-only, via `/execute-loop
  accounts` — the skill's account-management menu owns the flow; the probe
  script stays strictly read-only. The safe shape: resolve an exact enumerated
  NON-default profile dir via the shared eligibility predicate (`.lock`/control
  dirs, already-quarantined dirs, and malformed entries are never candidates);
  the default store is never deletable — and since the predicate excludes only
  the BUILT-IN default root, independently refuse any target whose canonical
  realpath equals the CURRENT environment-resolved default config root (an
  ambient `CLAUDE_CONFIG_DIR` can make the default alias an otherwise-eligible
  `~/.claude*` dir); scan for LIVE references — Active
  plans' operative `Loop config:` lines, isolation journals plus each journal's
  authoritative worktree plan, and foreign repo roots resolved from the
  profile's own `projects/` entries via authoritative metadata only (the munged
  name alone never resolves a root; historical configs in completed/archived
  plans never veto) — plus live-use evidence (a `.lock` sibling dir, a
  very-recent `projects/` mtime); any live reference refuses, and an incomplete
  scan proceeds only through a stronger confirmation naming the unscanned
  roots. Then quarantine-RENAME to `<dir>.quarantined-<YYYY-MM-DD-HHMMSS>` —
  resolved unique and displayed before the final target-specific confirm;
  no-clobber (an existing destination refuses, never a silent re-target); never
  permanent removal. The `.quarantined-` marker excludes the store from every
  enumeration surface at once. Restore = the exact reverse rename, refused on a
  collision with an existing eligible dir. Never echo credential content to
  stdout or logs.
- **Recent-repos activity (read-only observation):** each profile's config root
  carries `projects/<munged-cwd>/` entries (every non-alphanumeric character →
  `-`; lossy by construction — never resolve a repo from the munged name alone)
  whose mtimes enumerate cross-repo activity read-only; an entry younger than
  ~10 minutes is an in-use-right-now heuristic. Observation safety: snapshot
  `projects/` metadata BEFORE any `/usage` invocation and treat the pre-probe
  snapshot as the SOLE advisory input — a usage run itself adds a probe-cwd
  entry, updates the `projects/` dir mtime, and the CLI's start-time cleanup
  can delete stale empty `memory/` subdirs (changing entry mtimes mid-probe) —
  and exclude the probe's own cwd entries from any advisory. `probe-models.py`
  implements both: a pass-1 snapshot before any usage subprocess, plus
  munged-name self-exclusion with content-aware parent handling (a parent
  entry is excluded only when it is memory-only; transcript-bearing entries
  stay visible). Account-state note: an authenticated `/usage` probe can also
  trigger the CLI's own identity-preserving OAuth token rotation — a
  `.credentials.json` refresh-rewrite, observed conditional on token expiry —
  so read-only tooling must attribute that incidental class rather than assume
  credential byte-identity on live stores; account binding, login identity,
  and plan tier are unchanged by it.
- **Per-invocation use:** prefix the spawn with the profile's config-dir path
  (the invocable value — not the display identity), e.g.
  `CLAUDE_CONFIG_DIR=<profile dir> <pinned claude> -p "PROMPT" ...`.
- **Session transfer across accounts (live-verified 2026-07-03, during the
  v28.6 dogfood):** a Claude Code session's transcript is local disk state
  under the profile's config root —
  `<profile>/projects/<cwd-hash>/<session-id>.jsonl` plus a session-env
  entry — separate from auth. A mid-run session can therefore continue
  under a DIFFERENT account: (1) create + bind the new profile (browser
  OAuth) and verify it (`auth status` identity + the `.credentials.json`
  artifact check) BEFORE transferring; (2) copy the session transcript
  jsonl (its filename is the session id) and the session-env entry from
  the old profile's `projects/` store into the new profile's matching
  paths; (3) `--resume <session-id>` under the new profile's
  `CLAUDE_CONFIG_DIR` — verified to pick up the full session context, not
  start fresh (a 3.3MB transcript carried over cleanly); (4) run a short
  alive-check before trusting the resumed session. Use the same pinned
  binary throughout. Fallback if the resume is rejected: start a fresh
  session from the on-disk state (plan file, code, findings) — with the
  loop workflows' file-based handoff, no work is lost. This is the
  mechanism behind `/execute-loop`'s usage-exhaustion recovery
  "switch account" option.
- **Isolation probe (THE canonical definition; run per candidate binary as the
  pin arbiter — see the pin rule above — and before offering a profile
  selector):** `CLAUDE_CONFIG_DIR=/nonexistent-dir <pinned claude> auth status`
  MUST report logged-out (`"loggedIn": false`). If it still reports the default
  account, the env var is not reaching the binary and profile selection is inert
  — the profile question is still asked, downgraded: warn, name the fixes, and
  offer the default account + free-text entry. The selector is never silently
  removed. The bogus-dir shape is deliberate: a read-side "does the env var
  change the answer" check is defeated once a login has already written to the
  wrong store (the wrong store then shows the "right" answer); demanding
  logged-out from a nonexistent dir is deterministic and catches the whole
  failure class.
- **WSL interop caveat (observed on this host, 2026-07-03):** with claude installed
  via Windows npm and invoked through WSL interop, a bare WSL-side env var does NOT
  cross the interop boundary — `CLAUDE_CONFIG_DIR=/tmp/... claude auth status`
  still reported the default account and created no profile dir. **Verified
  workaround (same day, this host): an inline per-invocation prefix crosses
  cleanly —**
  `WSLENV=CLAUDE_CONFIG_DIR/p CLAUDE_CONFIG_DIR=<dir> <pinned claude> ...` — WSL reads
  `WSLENV` from the process environment at interop launch, and `/p` translates the
  WSL profile path for the Windows binary (probe: `auth status` reported
  `loggedIn: false` and config files were created inside the WSL-path profile
  dir). No persistent Windows-side env var is required. **Rule of thumb
  (updated 2026-07-04):** the PRIMARY fix on WSL is a WSL-native claude
  install, pinned per the v2 pin rule above — it removes the interop boundary
  entirely and unlocks the full headless topology (see the readiness-pause fix
  path above). The inline `WSLENV` prefix is
  WORKAROUND-GRADE: verified for env-var crossing on this host, but it is
  per-invocation (one forgotten prefix silently hits the wrong store again)
  and keeps every operation on a Windows binary crossing the interop boundary.
  Use it only while a native install is not an option.
- **Host verification (2026-07-03, this host):** a full second-account login
  round-trip PASSED using the inline prefix — `WSLENV=CLAUDE_CONFIG_DIR/p
  CLAUDE_CONFIG_DIR=~/.claude-work claude auth login` completed a browser OAuth
  and bound the profile to a second Max org (verified via the profile's
  `.claude.json` `oauthAccount`), while the default Windows-side config remained
  untouched (distinct userID, original install metadata). Two simultaneous-capable
  isolated profiles now exist on this host: the default (`jmadvisory` org) and
  `~/.claude-work` (`kount` org).
- **Simultaneous multi-org use — drop shared junctions:** a reviewed Windows-side
  profile-switcher script (`Setup-ClaudeWork.ps1`) shares session history between
  accounts via a `projects/` junction, which its own header scopes to
  NON-simultaneous use. For simultaneous multi-org roles, profiles must be fully
  isolated — no shared history junction.

## Cross-repo read roots (`--add-dir` / `additionalDirectories`)

When a plan references a second repo (a companion project, a reference
checkout), a spawned role needs an explicit read root — nothing inherits it:

- **`claude -p`: `--add-dir <path>` is per-spawn.** The flag grants access to a
  directory outside the working repo for that invocation only. Account profiles
  (`CLAUDE_CONFIG_DIR`) control auth/billing ONLY — they never widen file
  roots — so the flag must ride every executor/architect spawn that needs the
  root (`/execute-loop` derives the read-root list at preflight, re-derived each
  run, and carries the flags on the spawn invocation in loop step 1).
- **Persistent alternative for interactive sessions:**
  `.claude/settings.local.json` `permissions.additionalDirectories` — per-project
  and gitignored, so it never ships with the repo.
- **Read-only by default:** a confirmed read root is reference material — the
  spawn prompt states it must not be edited (a plan-scoped, user-confirmed
  cross-repo write is the only exception), and the orchestrator's
  filesystem-escape check extends to each external git root (`git status
  --short` before/after spawns — an added root is an accessible filesystem
  surface for the spawned role, so read-only intent is verified, never
  assumed); a non-git root has no escape-check surface — treat it as an
  explicit user-confirmed exception.
- **Native-subagent delegates** run inside the architect's session and inherit
  its roots — no separate flag.
- **Peers stay current-repo-only by default** — a peer reviews this repo's
  changes; extend a peer's roots only when a phase's review genuinely needs the
  reference repo.
- **Backend limits:** a Cursor subagent is workspace-bound (no equivalent
  flag); codex is confined to its sandbox roots.

## Optional advisor (v29.1: native `--advisor` + the workflow consult role)

`/execute-loop`'s wizard (Q3b) can attach a higher-tier **advisor** to the
executor/architect role — the "plan big, execute small" upgrade, persisted as
the additive `Loop config:` `advisor=` role group. One wizard concept, TWO
mechanisms, auto-selected from the advised backend + the advisor row (canonical
definition: `/execute-loop` → Optional advisor (any backend)):

- **Mechanism N — native `--advisor <model>` (Claude Code).** Eligible iff the
  advised role is `claude -p` AND the advisor is an Anthropic model with a
  matrix-valid pairing AND native support is observed. Detection is
  ACCEPTANCE-based, never help-grep: the flag is registered but HIDDEN from
  `--help` at 2.1.201 (observed live 2026-07-10 — a genuinely unknown flag
  fails fast while `--advisor opus` runs clean), so the probe script's billed
  `--probe-advisor` leg owns the check. Full-conversation quality: the advisor
  sees the advised session's context, not a bounded package. **Billing: N runs
  inside the advised session and bills ITS pool** — a quality lift, not pool
  arbitrage (an advisored trivial run cost ~2.3× its unadvised control,
  observed 2026-07-10). N is UNCAPPED by design — the native tool exposes no
  cap surface; its burn is the usage checkpoint's job.
- **Mechanism C — the workflow consult role (every other combination).** Any
  advised backend × any spawnable advisor backend: ONE bounded, one-shot,
  foregrounded, non-interactive advisor spawn (`role=advisor` on the `ROLE:`
  grammar) returning bounded advice TEXT to the advised role, budgeted per
  phase (default 3, failed spawns included) via the append-only
  `CONSULT: reserve`/`outcome`/`refused` ledger with a pinned reserve-then-invoke
  cap check. An advisor MAY be same-family — higher tier is the guidance; only
  the PEER pass requires family diversity. **Billing: C bills the advisor
  backend's OWN account/profile — the cross-pool "plan big, execute small"
  claim attaches to Mechanism C only.**

**Pairing matrix (docs 2026-07; native advisor v2.1.98+, Fable pairing
v2.1.170+):** the advisor must be at least as capable as the main model; haiku
never advises; a fable main pairs only with a fable advisor. **The matrix is
WORKFLOW-enforced, not CLI-enforced** — the two rejection shapes observed live
2026-07-10 at 2.1.201:

- opus←haiku: **hard error, the spawn dies** — exit 1, stderr verbatim:
  `Error: The model "haiku" cannot be used as an advisor.`
- fable←sonnet: **SILENT soft-strip, the run continues UNADVISED** — exit 0,
  stderr-only warning verbatim: `"sonnet" cannot advise "claude-fable-5" (the
  advisor must be at least as capable as the main model). The advisor will not
  be used for the main model.` On stdout the stripped run is indistinguishable
  from a healthy unadvised run.

Consequences: advised spawns tee stderr (`2>&1`) so a strip warning lands in
the role log; the deterministic post-hoc engagement check is the advisor model
present in the result event's `modelUsage`; and engagement is OPPORTUNISTIC —
the main model consults its advisor at its own judgment, so the ABSENCE of
engagement on an arbitrary prompt proves nothing (any check that claims to
verify engagement must use an engagement-forcing prompt; the probe script's
advisor leg does). A pairing rejection or strip on a close-table-confirmed
advisor is a CONFIG ERROR — re-ask or user-confirm the drop, then respawn;
never a silent degradation.

## Executor wake mechanics (attached spawn + monitor probes)

The composer-goes-dark failure (observed live, 2026-07-05, downstream runs): an
executor was spawned via a wrapper that exited 0 with the PID detached — the
composer owned no watchable shell, the `ROLE: handoff` exit sentinel sat unread
for hours, the 10-minute liveness line never fired, and one composer improvised
a 90-second live-turn polling loop to compensate. The fix is a two-layer wake
contract, both layers default-on where the host supports them (canonical prose:
the `execute-loop` skill's Visibility + run-state and loop step 1):

- **Layer 1 — attached spawn + output watch (the exit wake).** On a persistent
  composer with a background-shell watch surface (e.g. a Cursor composer), the
  CLI executor/architect runs as a composer-owned background shell — teed,
  never `nohup`-detached — with the output watch configured AT SPAWN on the
  full Tier-1 anchor set (every `ROLE:` / `DELEGATION:` line plus the
  limit/error strings, not just the handoff sentinel). The shell's completion
  notification wakes the composer the moment the role exits: handoff, crash,
  and limit-death detected in seconds, for free. **The anti-pattern: a spawn
  wrapper exiting 0 is not a watched executor** — if the wrapper detaches the
  PID, the composer has nothing to watch and nothing to be woken by.
  Host-conditional: a headless composer dies at turn end — it foreground-waits
  the spawn or uses the sleep-sentinel fallback; peers are always
  foreground-and-waited regardless (the loop's foregrounded-peer rule is
  unchanged).
- **Layer 2 — the monitor subagent (default-on for CLI executor backends on
  hosts with cheap background subagents).** At spawn the composer also arms a
  cheap-model background monitor subagent with an explicit contract: executor
  PID, tee-log path, plan path, the Tier-1 anchor regexes, the liveness
  window, and the current watch baseline (tee-log offset / last-seen anchor
  plus the plan task-marker snapshot at arm time). It polls its inputs every
  ~60–90 seconds and RETURNS on the first NEW Tier-1 anchor (past its
  baseline), executor exit, or liveness-window expiry, carrying a one-line
  snapshot (current task + time-in-state, log growth, last event age). Each
  return is a composer wake; the composer posts the update/liveness line and
  re-arms a fresh monitor with an updated baseline — return-per-event, never
  one long-lived poller (a long-lived monitor accumulates context and wakes
  the composer only once), and a re-arm never re-fires on an already-handled
  anchor (rotation guards prior-run anchors; the baseline guards this run's).
  Snapshots append to `.cursor/loops/<runkey>-probe.log` (gitignored; monitor
  probes are not `ROLE:` activations). Liveness-window-expiry returns and the
  chat liveness line follow the run's Q5 liveness setting — OFF disables the
  quiet-window wake (stall observation narrows to anchor/exit detection),
  never the anchor/exit returns. Layer 2 adds what the watch alone
  cannot: semantic snapshots, the stall watchdog's observation input, and
  cover when the native watch fails — and it is REQUIRED for the one
  legitimate detached-spawn exception (a spawn that must survive composer
  restart). **Two implementation shapes, one slot (v29.2):** `layer2=monitor`
  is the abstraction, not one implementation — a PERSISTENT harness-native
  watch tool fills the same slot: it emits per-event notifications instead of
  returning, needs NO re-arm (its single spawn-time `WATCH: armed` line plus
  the continuing notifications ARE the arm/liveness proof), writes the SAME
  `MONITOR:` snapshot grammar per event — and it never self-terminates, so
  the exit-branch teardown (below) is mandatory for it. Either implementation
  resolves as `monitor` at preflight; the `Wake:`/`WATCH:` grammar stays
  `monitor|sentinel|none`.
- **Sleep-sentinel fallback (hosts without subagents):** a backgrounded
  sleep-N-minutes-then-print-sentinel shell whose output wakes the composer to
  run the quiet-window check. Any liveness or watchdog rule needs a concrete
  wake path — a quiet-window rule with no wake mechanism is a no-op.
- **Stream-json anchor discriminator (v29.2).** In a repo whose own content
  documents the anchor vocabulary (quoted `ROLE:` / limit-string prose in
  skills or docs), tee-log anchor matches from tool-result echoes are expected
  false positives — and a stream-json tee log makes the real/echo distinction
  concrete: a REAL event is an unescaped line-start JSON object
  (`{"type":"rate_limit_event"` at column 0), while a quoted echo inside
  tool-result content rides mid-line with escaped quotes
  (`\"type\":\"rate_limit_event\"`). Filter EVENT-shaped anchors — the
  `rate_limit_event` / error-event family, in the watch regexes and the
  monitor's snapshot classification alike — on the unescaped line-start form,
  and treat a `rate_limit_event` as a limit wake only on a non-`allowed`
  status — the healthy stream emits routine `"status":"allowed"` rate-limit
  events (e.g. `{"type":"rate_limit_event","rate_limit_info":{"status":"allowed",…`),
  so a bare limit-string match wakes on healthy traffic. Text anchors
  (`ROLE:` / `DELEGATION:` lines) live inside message JSON on both the real
  and echoed paths — line-start filtering does NOT apply to them; in
  echo-prone repos they stay ADVISORY per the canonical meta-repo caveat
  (exit keys on the shell's completion notification plus the role's own
  final line). Observed live
  2026-07-10 (run lr291-0): two false limit-string wakes before the retune,
  zero after, for the rest of a 7.5h run.
- **Arming is declared at preflight and proven by artifact (v29.1).** Wake
  predicates are resolved ONCE at preflight — never re-assessed ad hoc at spawn
  time — and the contract's state is carried by THREE required greppable
  artifact families (alongside `ROLE:` lines):

  ```text
  Wake: run=<runkey> layer1=<bg-shell|subagent-harness|fg-wait|native> layer2=<monitor|sentinel|none> [interval=<minutes>m] [reason="<required when layer2=none>"]
  WATCH: armed ts=<iso> run=<runkey> role=<executor|architect|delegate|peer|advisor> layer1=<...> layer2=<...> [reason="<required for layer2=none and for any mechanism-change line>"]
  MONITOR: ts=<iso> run=<runkey> role=<...> event=<anchor|liveness|anomaly|exit|dead-at-spawn> task="<current task + time-in-state>" log=<growth> last=<age> detail="<one-liner>"
  ```

  The `Wake:` declaration prints in chat at preflight and as line 1 of each
  phase's `<runkey>-probe.log` at that phase's first arm (a dry-run prints to
  chat only); every CLI-role spawn prints a `WATCH: armed` line whose
  layer-state fields are MANDATORY — `layer2=none` requires a `reason="..."`,
  so degradation is loud by construction (there is no separate `degraded`
  verb); the monitor writes every `MONITOR:` snapshot itself — the
  return-per-event subagent as its last act before returning, a persistent
  watch tool per event notification (no return exists) — and continued-arm
  proof is implementation-shaped: the subagent's re-arm is proven by the
  PRESENCE of the next `MONITOR:` return, not by a composer-written claim
  (no `rearmed` verb — the party that failed to re-arm is the party that
  would have written the claim), while the persistent watch needs NO re-arm —
  its single spawn-time `WATCH: armed` line plus its continuing notifications
  ARE the arm/liveness proof (the two-shape clause above).
  Return handling is ATOMIC and CONDITIONAL: a non-exit return is not fully
  processed until the update is posted AND the next watch is armed in the same
  handling turn; an exit return writes the role's `ROLE: end` FIRST, runs the
  terminal classification, does NOT re-arm (the role is closed — never a
  watch on a dead PID), and CANCELS every still-armed wake mechanism for that
  role that did not self-terminate with the exit return (v29.2) — an
  armed-but-unreturned monitor when Layer 1 fired first, a pending sentinel
  timer, and a persistent harness watch tool alike: a mechanism outliving its
  closed role emits false events against the frozen log (observed live
  2026-07-10: two post-exit false stalls); a live role with NO Layer-2
  mechanism and NO Layer-1 surface is foreground-waited or MUST-PAUSEd — it
  never continues dark.
  Canonical definition (writers, worked example, the full return-handling
  duty): `/execute-loop` → Visibility + run-state → Wake arming artifacts.
- **Log rotation protects the anchors.** Tee logs append and run keys get
  reused: a stale `ROLE: handoff` from a prior run in a reused log is a false
  wake anchor (observed live). `/execute-loop`'s preflight rotates any
  existing `.cursor/loops/` logs matching the run's key prefixes
  (timestamp-suffix rename) so the watch — and `/retro` — see only this run's
  lines.
- **Composer-shell failure ≠ run over.** When the composer's own shell stops
  executing (distinct from an executor failure), a working subagent shell is a
  legitimate degraded surface for composer-owned duties — exact
  composer-specified commands only, every gate preserved, the degradation
  recorded in the run state; pause only when both surfaces are dead (canonical
  prose: the `execute-loop` skill's Safety gates; observed live 2026-07-05 — a
  shell subagent performed the authorized phase commit after the session shell
  died).
- **Composer context loss ≠ run over (v29.1).** A compacted or restarted
  composer — or one that simply cannot state the current runkey, phase, and
  immediate next action (the inability IS the detector) — recovers from disk
  truth, never remembered intent: re-read the loop skill's run-mechanics
  sections (plus its Optional-advisor section when the parsed `Loop config:`
  carries an `advisor=` group — not the wizard, whose result is already
  persisted); re-read the plan's `Current State / Handoff Note` and parse
  `Loop config:` (and, when advised, the phase's `CONSULT:` ledger — dangling
  reservations classified before any new consult, an in-flight advice return
  re-delivered over its pinned route, never re-billed); re-resolve wake modes
  and re-arm with a dark-window log check (an exited role gets `ROLE: end`
  written FIRST); then resume from what the plan and logs prove. The
  `[<runkey>]` breadcrumb prefix on composer-posted status lines is the
  chat-side anchor back into the run. Canonical definition: `/execute-loop` →
  Visibility + run-state → Resume contract.

## Run isolation: the worktree-per-run lifecycle (v29.3)

Reference mirror — the canonical contract is the `execute-loop` skill's **Run
isolation (worktree-per-run)** section; this summary exists so a loop host can
reason about the on-disk artifacts without the skill open.

- **Why per-run worktrees:** an editing loop that builds in the base checkout
  leaves nothing between an autonomous overnight run and the user's own tree.
  `isolation=worktree` (Q5; the recommended default for editing runs) builds in
  a per-run git worktree on a run branch created at preflight sub-step 2b; the
  base checkout stays untouched, and the run branch reaches the base only via
  an explicit, LOCAL, opt-in merge-back (`merge=auto`, legal only with
  `autocommit=on`; conflicts always stop; never a push). A dry-run prints the
  resolved isolation actions and intended log rotations and creates/renames
  NOTHING.
- **The iso-ID keys everything:** a collision-resistant ISOLATION-RUN ID is
  minted at wizard close — DISTINCT from the phase-scoped `<runkey>`
  (`stage-<N>`, which recurs across runs) — and derives the intent journal
  (`.cursor/loops/<iso-id>-isolation`, no `.log` suffix so rotation never
  touches it), the ownership marker (`<iso-id>-active`), the run branch, the
  worktree path, and the per-run LOG ROOT `.cursor/loops/<iso-id>/` (unchanged
  `stage-<N>-<role>.log` names inside; rotation, wake/probe paths, and
  `/retro` ingestion route through it via absolute paths in spawn prompts, so
  two concurrent runs sharing a `stage-1` phase never rotate, wake on, or
  ingest each other's files). The `ROLE:` `run=<runkey>` grammar is untouched;
  the journal records the phase-key family for recovery mapping.
- **Worktree location is backend-keyed:** CLI executors (cwd-pinnable
  anywhere) → a sibling dir outside the base, default
  `<base-parent>/<repo>-wt/<iso-id>`; workspace-bound executors (Cursor
  subagent / live session) → the nested gitignored `.cursor/loops/wt/<iso-id>`
  (legal git; invisible to base status). A backend that cannot reach its keyed
  location = worktree UNAVAILABLE for that backend — an explicit confirmed
  fallback (switch backend or `none`), never a silent base-checkout build.
  Executor spawns are cwd-pinned to the worktree; logs stay base-side.
- **The registry is an atomic INTENT JOURNAL, not a status file:** greppable
  `key=value` lines — one key per line, string values quoted with
  backslash-escaped quotes/backslashes/newlines (paths may carry spaces;
  `base_status` stores the full `git status --short` output as one escaped
  value, empty when clean), compared byte-for-byte on recovery and the merge
  preflight — written via write-then-atomic-rename BEFORE any git
  mutation; it carries the base realpath/branch/HEAD/status baseline plus a
  state field (`intent → created → active → merging → merged → cleaned`, with
  durable outcomes `retained-green` / `paused` / `crashed/recovery-needed` /
  `merge-failed` — the orderly conflicted-or-failed-merge stop, distinct from a
  crash)
  and ORDERED writes — authority/sync/outcome before marker removal, `merged`
  before any cleanup, the journal retained until cleanup is verified. Recovery
  keys on journal facts + reconciled git state (`git worktree list`, refs, the
  base) — never marker absence or plan prose; ambiguity retains every artifact
  and stops without touching the base. Fresh-session entry (`/execute-loop`
  resume step 0, plus the `/start-session` / `/load-plan` registry clauses)
  reads these journals from the base checkout and follows worktree authority
  to the recorded plan copy.
- **Ownership markers cover the non-isolating modes too:** EVERY editing mode
  (worktree AND `branch`/`none`) claims the checkout via
  `.cursor/loops/<iso-id>-active` — liveness identity keyed to the
  RUN-LIFETIME owner (the composer/orchestrating session; a per-phase
  executor PID is at most a refreshed secondary field, so a dead child
  between phases never makes a live run look stale), a serialized
  create-then-rescan claim whose rescan gates activation (scan-clean
  proceeds; seeing ANY contender surfaces for explicit confirm — the
  deterministic iso-ID tie-break only orders the surfaced arbitration, so at
  most one run ever proceeds unconfirmed), and CONSERVATIVE stale
  reconciliation (unknown liveness warns or refuses, never delete-as-stale
  by guess). A resumed `branch`/`none` run re-validates and adopts its own
  marker before editing continues — journal absence is those modes' steady
  state, so marker reconciliation is never skipped on resume. A journal-less
  marker recording `mode=worktree` marks the pre-journal crash window (claim
  made, journal never renamed — no branch or worktree exists yet): a
  live/unknown owner retains + stops; a conclusively dead owner with zero
  matching git/isolation artifacts has only the ownership-proven marker
  removed; any artifact found is retained + surfaced. Pre-journal refusal
  paths remove their own marker before returning. The `branch`/`none`
  concurrent-edit warn keys on these markers — never broad `pgrep` or stale
  log prefixes. `branch` = the `none` path plus a named branch: non-isolating,
  no journal, no merge-back lifecycle.
- **Source state is gated BEFORE creation:** all relevant non-ignored base
  dirt is classified, tracked AND untracked — non-plan tracked changes or
  named untracked plan inputs REFUSE worktree isolation unless the user picks
  a reversible, journaled copy into the worktree (base copies preserved) or a
  mode switch; ignored `.cursor/loops/` content is never swept into a
  transfer; an uncommitted active plan transfers COPY-not-move (base copy
  retained, sync status journaled) or the spawn refuses; `merge=auto` never
  starts over base dirt that dooms the clean-base merge precondition
  (normalize to `merge=off` with a note, or re-ask at close). Pre-creation
  failures leave no partial artifacts and an unchanged base.
- **Close paths (the one canonical table lives in the skill):** verified
  merge-back → base authoritative + cleanup may proceed; green merge-disabled
  → retain worktree/branch/journal with the worktree plan authoritative
  (`retained-green`) and the handoff stating the continuation;
  pause/crash/resume keep worktree authority under the journal contract; every
  non-green close retains a recoverable worktree/branch. Merge-back runs only
  under a base-scoped close lock (`.cursor/loops/close.lock`, atomic-create,
  naming its holder iso-ID) with the clean/UNMOVED-base predicate RE-READ
  after acquisition (HEAD at the recorded baseline; a contended or stale
  lock — or a post-lock predicate failure — retains the run and stops, never
  touching the base); an extant lock recovers by validated-holder
  disposition — a same-live-owner resume adopts its own lock; a
  provably-dead holder reconciles under exclusive recovery (pre-merge with
  the base unchanged → release safely; a `merging` record whose merge
  provably never started — baseline-matched base, no merge residue —
  releases or resumes under the recovery ownership; a proved-complete merge
  → persist `merged` + authority, then release; ambiguous/dirty/mid-merge →
  retain + stop), and removal is always ownership-checked, never age-based; a failed or
  conflicted merge is aborted with the base restored byte/status-identical and
  the journal records the `merge-failed` outcome (never left `merging`, never
  mislabeled `crashed/recovery-needed`); cleanup is idempotent; never a push.
- **Escape baselines split under isolation:** the worktree's `git status` is
  the per-spawn edit-surface baseline; the base's status is recorded
  separately as the non-interference + merge-precondition proof. Composer-run
  duties (verification suites, smoke, `/document`, auto-commit staging on the
  run branch) execute against the worktree; `/retro` reads base-side logs +
  the worktree plan.

## The cross-family rule (run-time, not hardcoded)

Peer-review's catch-rate comes from model-family diversity. The peer family must
differ from the **live executor's** family:

- live executor is **GPT-family** (`cursor-agent` / `codex`) → peer = `claude`.
- live executor is **Claude-family** (e.g. Cursor on Claude Opus, or Claude Code) →
  peer = `codex` (GPT).

In this spike the live `/execute` session was Claude Opus 4.8, so the cross-family
peer was **`codex` (GPT-5.5)**, not `claude`. Stage 5/7 must detect or be told the
executor's family and pick a cross-family peer accordingly.

**Fallback matrix:** if the chosen cross-family CLI is unavailable (e.g. `claude`
WSL-interop failure), try a same-family-as-needed model via another tool; if no
cross-family peer can run, **mark the run inconclusive — never silently substitute a
same-family peer** (that destroys the property the loop exists for).

## The non-interactive peer contract

The headless peer runs `$peer-review` with a prompt-level override (the shipped
skill is NOT edited in the spike) that:

1. **suppresses** the Step 0 sub-step 6 proceed prompt (`Proceed with auto-detected
   inputs? (y / show menu)`) — run start-to-finish, never wait for input;
2. **suppresses** the model-diversity warning (cross-family is composer-enforced);
3. **forces path (b)** (always write findings to the Review Findings Log) — no
   (a)/(b) handoff choice;
4. **forces a fresh review of the composer-supplied scope, in the token-selected
   mode** — by default (sentinel alone) a fresh CODE review of the specific files +
   plan path, reading the files directly — this avoids two traps: (i) an empty
   Findings Log otherwise routes peer-review into **plan-review mode**; (ii) a later
   iteration would otherwise target the stale prior round instead of the post-fix
   code (`peer-review/SKILL.md:19`);
5. **sets the correct `Source:` attribution** for the tool it ran in.

**Plan-review mode (v29.3) — the second control-header token.** The contract's
mode is read from the invocation prompt's CONTROL HEADER (its first nonblank
line) alone; token text anywhere else in the prompt is inert content. The token
truth table is TOTAL: `PEER_LOOP_NONINTERACTIVE PEER_LOOP_PLAN_REVIEW` (both
tokens on the header) = headless PLAN review; `PEER_LOOP_NONINTERACTIVE` alone =
headless CODE review (the contract exactly as written above); no control header
= interactive; a header carrying `PEER_LOOP_PLAN_REVIEW` WITHOUT the sentinel is
INVALID — the peer refuses loudly with a precise error naming the missing
sentinel and writes NOTHING (an interactive plan review remains `/peer-review`'s
own plan-review mode, invoked directly, never via the loop token). Under both
tokens the peer critiques the PLAN only — scope is plan-only and the
filesystem-escape baseline is plan-file-only — and WRITES its findings as a
normal Findings Log round with the mode-distinct `Source:`
**`<Tool> plan peer-review`** (`Cursor plan peer-review` / `Claude Code plan
peer-review` / `Codex plan peer-review` — deliberately ending in `peer-review`
so suffix-rule consumers exclude plan rounds even on stale downstream copies).
The amendment route branches with the mode: `/fix` NEVER ingests a
`… plan peer-review` round (its Step 0 predicate excludes them) — the owning
planning session applies accepted findings as `/review-plan`-style amendments
(or via a scoped `/review-plan`), marking per-finding dispositions on the round;
convergence is measured on plan-diff + finding status, not code diffs. Canonical
definition: `/peer-review` → the non-interactive contract (the truth-table
paragraph + points 4–5) and `/peer-loop` → loop step 2.

**Stage 5 prerequisite (confirmed bug):** path (b) hard-codes
`Source: Cursor peer-review` at `.agents/skills/peer-review/SKILL.md:304` (and its
`.claude` mirror), regardless of the tool actually running. The override worked
around it (emitting `Codex peer-review` / `Claude Code peer-review`); Stage 5 must
fix the skill to emit the active tool's attribution, mirroring `/review`'s
"set Source to where it ran".

The contract was validated over 4 fresh headless runs (2 × `claude`, 2 × `codex`),
all non-interactive, all producing a correctly-shaped Round block. **Reproducible
caveat:** the count + log *shape* are stable, but **severity labels are
non-deterministic across runs** (the same 3 bugs came back as 2 CRIT/1 HIGH one run
and 0 CRIT/3 HIGH another). Therefore key convergence + auto-disposition on finding
**presence/verification**, not on exact severity counts.

## The loop (reproducible)

Composer logic (thin — a shell loop or the Cursor SDK):

1. **Supply scope.** Build an explicit review scope: the files just changed + the
   plan path. (Don't rely on the peer's auto-detect; the composer already knows.)
2. **Spawn the cross-family peer headless** with the non-interactive contract; it
   appends a Round block to the plan's Review Findings Log and exits.
3. **Executor verifies + fixes.** The live executor session reads each logged
   finding, verifies it against the code (its session memory catches peer false
   positives), and applies `/fix`. (Interactive `/fix` is fine while the executor is
   the live session; a headless-executor `/fix` works too — see the gate section.)
   **Plan-review mode (v29.3) routes differently:** `/fix` never ingests a
   `… plan peer-review` round — the owning planning session verifies each plan
   finding against the plan (plus the code it names) and applies the accepted
   amendments `/review-plan`-style (or via a scoped `/review-plan`), marking
   per-finding dispositions on the round.
4. **Re-review.** Spawn a *fresh* peer on the *post-fix* scope (fresh-scope contract,
   not the old round; in plan-review mode, the post-amendment PLAN — convergence is
   measured on plan-diff + finding status, not code diffs). It auto-numbers the next
   round and reports.
5. **Terminate** on zero findings (converged), stalemate detection, or cap 3.

Proven run (fixture `calc.py` with planted bugs): Round 1 (peer, codex) logged the
bugs → executor (live Claude) verified both as true positives and fixed them →
spec asserts passed → Round 2 (fresh codex peer) returned **0 findings → Closed
(converged)**. One fix iteration; cap 3 not reached. Every run recorded the main
checkout `git status` before/after (filesystem-escape check) and it never changed.

## Three-way gate-candidate classification (headless auto-disposition)

When `/fix` runs headless (Stage 5/7), each finding is classified and routed; this
ran correctly headless in the spike (`applied=1 paused=2`):

- **MECHANICAL** — the peer's own proceed / handoff / model-diversity confirmations.
  Auto-resolved by the non-interactive contract.
- **AUTO-DISPOSABLE** — direction is do-the-work (`Fix-now` / `Include in plan`)
  **and** severity is LOW or MED **and** not production-impacting. The agent applies
  its own recommendation headless and **logs** it. This is the only class acted on
  without a human.
- **MUST-PAUSE** — ANY of: `Defer` / `Accept`; CRIT / HIGH; production-impacting (new
  dependency / env var / migration / deploy-config / parity drift); a `/fix`
  stop-on-failure; or genuine uncertainty. **Surface to the user; never auto-decide
  or auto-apply.**

Spike evidence: a LOW/Fix-now/non-prod finding was auto-applied (added `__all__`); a
CRIT/production finding and a MED/Defer/production finding were both paused with the
code left untouched; the spec still passed; every disposition was logged. This is
the `MUST-PAUSE` half of the headless mode the Stage 1 forward-reference stub
points at — Stage 4/5 authors the full policy prose into the 5 gate sections
against this proven mechanism.

## Build-vs-adopt: A (build) vs ralphex (B)

ralphex (https://ralphex.com/docs/, reviewed 2026-06-29) is a mature standalone Go
binary that orchestrates Claude Code / codex: fresh session per task; 4-phase
pipeline (task+validate+commit → 5-agent parallel review → codex external review w/
stalemate detection → 2-agent final review → optional finalize); SIGQUIT steering
(pause → edit plan → resume fresh; **not on Windows**); `--worktree` + Docker
isolation; auto branch + auto-commit; plan-move to `completed/`; web dashboard;
notifications; `--codex` executor.

**Decision: BUILD our own (A); BORROW ralphex's patterns.** Why:

- A is proven sufficient + reproducible this spike.
- A reuses our existing `$peer-review` / `/fix` skills and `.cursor/plans/`
  Findings-Log schema natively. Adopting ralphex means its `docs/plans/` +
  `### Task N:` checkbox schema + its own review agents — losing our per-finding
  schema, executor-verifies-before-fix, the 3-way auto-disposition gate, and the
  run-time cross-family rule (or paying a brittle adapter tax).
- A is thin (≈2 shell scripts + prompt files, or the Cursor SDK) with no Go binary
  and no Docker dependency.
- In this WSL/Windows env, ralphex's SIGQUIT steering is unavailable and its default
  Claude mode uses `claude --print` (Agent-SDK billing exposure).

**Patterns to borrow into Stage 7:** fresh-session-per-task; stalemate detection;
a completion signal; a steering pause; plan-move-to-`completed/`; auto-commit after
each task (**never auto-push**). ralphex stays a useful reference impl + fallback if
our own loop proves hard to maintain.

**Agent-composer vs thin-orchestrator:** the thin-shell-orchestrator arm works and
is genuinely thin. The agent-composer arm (`cursor-agent` driving the loop) is
blocked on headless auth here and adds a paid agent layer for no benefit when the
executor is already the live session. **Recommend the thin orchestrator** (a shell
loop now; the Cursor SDK — see the `sdk` skill — for the Stage 7 capstone).

## Recommended engine + topology for Stages 5 & 7

- **Engine:** our own thin orchestrator. Stage 5 (peer-review loop) can be a shell
  loop. Stage 7 (execute-loop capstone) was originally scoped to the Cursor SDK for
  fresh-session orchestration (or a shell loop) — but **as DELIVERED (v27.7) it is
  skill-embedded prose with no committed script** (matching `/peer-loop`), which
  supersedes the SDK/shell suggestion: the loop spawns a fresh per-phase executor via
  the setup wizard's chosen backend (Cursor subagent / `codex` / `claude -p` / live
  session), keeping the capstone portable via the bootstrap with no new artifact type,
  dependency, or API-key surface.
- **Stage 5 peer-review loop:** composer → cross-family peer headless (non-interactive
  contract) → Findings Log → executor verifies + `/fix` → fresh peer → repeat;
  terminate on zero/stalemate/cap 3. Prerequisites: fix the `Source:` hardcode; add
  the peer's non-interactive contract to the shipped skill behind an explicit
  headless flag/sentinel (interactive `/peer-review` unchanged).
  **[DELIVERED v27.6, 2026-07-01:** shipped as the new locked `/peer-loop` shared skill;
  both prerequisites done — the `/peer-review` path-(b) `Source:` hardcode is fixed and the
  non-interactive contract ships behind the `PEER_LOOP_NONINTERACTIVE` sentinel; `/fix` gained
  a verify-peer-findings fallback and `/review-loop` chains into `/peer-loop`. Dogfooded live
  with 2 fresh `codex exec` headless peer runs of the shipped contract (found 2 MED → fixed →
  converged 0). See `/peer-loop` + `/peer-review`.**]**
- **Stage 7 execute-loop:** per-stage execute → review-loop → peer-loop → smoke →
  mandatory live-user-smoke pause for UI/UX → document → auto-commit → **fresh
  session** → next. Inherits all gates incl. the 3-way auto-disposition policy;
  never auto-pushes.
  **[DELIVERED v27.7, 2026-07-01:** shipped as the new locked `/execute-loop` shared skill — a
  skill-embedded (no committed script) per-phase loop composing `/execute` + `/review-loop` +
  `/peer-loop` + `/document`, with pluggable role backends (Cursor subagent / `codex` / `claude -p` /
  live session) chosen at a setup wizard, an optional delegating "architect" executor + inline effort
  right-sizing, and the 3-way headless auto-disposition policy authored into the 5 gate skills' 6 dormant
  stubs. `/review-loop`'s cross-family peer pass is now default-on after every convergence. See
  `/execute-loop`.**]**
  **[UPDATED v28.0, 2026-07-02 — delegation v2:** the architect rails are rescoped from
  bulk-mechanical offload to **spec + diff-verifiability keying** — the architect designs,
  specifies, and reviews; the same-family delegate implements against the approved spec,
  including UI *implementation* from the architect's design spec (UI *design* stays
  architect-held). The architect verifies every delegate diff against its spec and logs misses
  rather than silently patching; the phase-smoke half of verification is backend-capability-split
  (a spawn-capable architect runs the smoke itself; for a headless architect the composer runs it
  and feeds the result into the outcome log). Every delegation decision + outcome is a
  `DELEGATION:`-prefixed line in `.cursor/loops/stage-<N>-executor.log`, for spawned and
  live-session architects alike. Delegating mode raises the cross-family peer pass's importance —
  everything is one-family until the peer runs. See `/execute-loop` → Optional delegating
  executor.**]**
  **[UPDATED v28.2, 2026-07-02 — diagnostics:** the loop recipe's observability gap is closed.
  Every role activation now gets a parseable `ROLE: start`/`end` pair (backend, model, best-effort
  `turns≈`/`tokens≈`/duration where the backend exposes them) in the run's `.cursor/loops/` logs —
  authored canonically in `/execute-loop` → Visibility + run-state, with pointer additions in
  `/peer-loop` (per peer round) and `/review-loop` (per-round `ROLE: round` line, loop-log context
  only). The new propose-only `/retro` skill (20th) reads those logs (`ROLE:` + `DELEGATION:` +
  per-role tees) plus the plan's `Review History` / `Review Findings Log` and writes a structured
  run report to `.cursor/loops/retro-<runkey>-<date>.md` + one plan pointer line — after any loop
  run, one command answers "what happened, what did it cost, what failed and why". See `/retro`.**]**
  **[UPDATED v29.0, 2026-07-07 — smoke-feedback routing:** the live-user-smoke pause gains a
  triage contract — feedback is never applied ad hoc. The composer batches ALL user feedback
  items and relays the batch to the executor (`--resume` for CLI backends); the batch runs the
  Deferral Confirmation Gate as one compact table (single confirm, per-item overrides;
  `Include in plan` recommended for anything UI-touching or potentially multi-surface),
  `Include in plan` items become provenance-tagged plan task(s), and the batch gets ONE scoped
  `/review-plan` with a mandatory design-doc consult + app-wide sibling-surface enumeration
  (feedback names an instance of a pattern; the hardening enumerates the pattern) before the
  executor implements via `/execute` and the user re-smokes. See `/execute-loop` → the per-phase
  loop, step 6.**]**
  **[UPDATED v29.1, 2026-07-10 — run reliability + advisor + permission tiers:** wake arming is
  now declared at preflight and proven by artifact — the 3-family `Wake:` / `WATCH: armed` /
  `MONITOR:` grammar with mandatory layer-state fields, monitor-written re-arm proof, and the
  atomic conditional return-handling duty (see the wake-mechanics section's v29.1 bullets); a
  canonical composer RESUME contract recovers a compacted composer from disk truth (`Loop config:`
  + the plan handoff note + the `CONSULT:` ledger + wake re-resolution; see "Composer context loss
  ≠ run over"); the smoke pause gains a routing DEFAULT (any user message during the pause is
  feedback-to-relay after two precedence checks) + the composer-never-implements prohibition; the
  wizard's Step 0 probes are SCRIPT-FIRST via the new `.cursor/bootstrap/probe-models.py` payload
  (see Model probes); an optional per-role ADVISOR lands with per-mechanism billing and the
  workflow-enforced pairing matrix (see the new advisor subsection); and an executor PERMISSION
  TIER (`perms=scoped|bypass`, close-table-confirmed, per-invocation rendering incl. resumes)
  lands with per-CLI bypass recipes (see the per-CLI rows + the verification-grants
  permission-tiers bullet). Both `perms=` and `advisor=` are additive `Loop config:` keys —
  `Workflow Schema:` stays v22. See `/execute-loop`.**]**
  **[UPDATED v29.2, 2026-07-10 — run polish (lr291 retro + WSL host investigation):** the wake
  contract's `layer2=monitor` slot now explicitly admits BOTH implementation shapes — the
  return-per-event monitor subagent and a persistent harness-native watch tool (per-event
  notifications, no re-arm, same `MONITOR:` grammar; grammar stays `monitor|sentinel|none`) — and
  the exit branch CANCELS every still-armed wake mechanism on role close (post-exit false stalls
  observed live); the anchor watch gains the stream-json unescaped-vs-escaped discriminator plus
  the non-`allowed` status filter (false limit-string wakes retuned to zero mid-run); long
  `claude -p` spawn prompts ride a gitignored prompt file via stdin redirect (`claude -p <
  promptfile` — quoting-proof through interop layers, 7/7 clean in lr291); the cap-reached stop
  gains residue routing (raise +1 for unconfirmed MED+ code/prose residue, accept-and-close for
  records-only); and the NEW host-setup section (top of doc) hardens WSL loop hosts — inotify
  limits, the two-section `.wslconfig` template with the merge rule and shutdown gotcha,
  `.cursor/loops/**` editor exclusions, stable-track guidance, and the lr291-evidenced
  composer-architecture ranking. See `/execute-loop` + the wake-mechanics bullets above.**]**
  **[UPDATED v29.3, 2026-07-20 — Stage A loop hardening (v30 program):** the loop gains per-run
  WORKTREE ISOLATION — additive `isolation=worktree|branch|none` + `merge=auto|off`
  `Loop config:` key-groups (wizard Q5; `Workflow Schema:` stays v22) with the full
  composer-managed lifecycle: the collision-resistant iso-ID + per-run log root, the atomic
  base-side intent journal, rescan-gated ownership markers with run-lifetime liveness, the
  pre-creation source-state gate, backend-keyed worktree locations, worktree-plan authority
  with per-close-path outcomes, and LOCAL-only opt-in merge-back that conflicts always stop
  (see the Run isolation section); the bypass tier gains HOST-GATING + the one-pause ATOMIC
  scoped fallback with the step-6 probe as sole operative gate (see the verification-grants
  bullet above); preflight step 10 gains the Layer-2 VIABILITY check (a gated Monitor tool
  resolves `layer2=sentinel` up front; see Host setup's allowlist bullet); the composer now
  consults `docs/lessons.md` at preflight and carries run-relevant items into spawn prompts,
  with eleven kount run-lessons folded at their natural sites (cwd pinning, no broad `pgrep`
  kills, live-log rotation + double-spawn guards, exact-path staging, bounded polls, PATH
  pinning, port advisory, probe-failure visibility, the foreground-wait generalization); every
  readiness/probe failure now classifies agent-fixable vs user-fixable with exact remediation
  steps (the setup-remediation contract); and the non-interactive peer contract + loop recipe
  above gain the PLAN-REVIEW mode branch (`PEER_LOOP_PLAN_REVIEW` beside the sentinel; the
  total token truth table; plan-only scope; the mode-distinct `<Tool> plan peer-review`
  Source; planning-session amendments, never `/fix`). Skill-side, the fresh-session entry
  points (`/start-session`, `/load-plan`) become isolation-registry-aware; `/load-plan` gains
  the `/execute` vs `/execute-loop` menu split (mirrored at `/review-plan`'s post-save
  handoff); and the locked-skill menu-consent contract lands in the three menu-bearing
  workflows (`/load-plan`, `/review-plan`, `/review-loop`). See `/execute-loop` + `/peer-loop` +
  `/peer-review`.**]**

## Open risks / watch-items

- **`cursor-agent` headless auth** needs `CURSOR_API_KEY`; resolve before relying on
  cursor-agent as a headless composer/executor. Thin orchestrator avoids it.
  (Re-verified still blocked 2026-07-02: `cursor-agent -p` on 2026.04.08-a41fba1
  returns "Authentication required. Please run 'agent login' first, or set
  CURSOR_API_KEY" — the interactive IDE login does not carry over.)
- **Nested-spawn depth for the delegating architect** — **RESOLVED for depth 2 on this
  host (probed live 2026-07-02):** a Cursor Task-tool subagent carries the full parent
  toolset *including Task*, and successfully spawned its own child (composer → subagent
  → sub-subagent; the child ran as a real agent with its own agent ID and replied to a
  sentinel prompt). A per-phase executor subagent can therefore act as a delegating
  architect directly — the preferred multi-phase topology (thin composer → fresh
  Fable-class architect subagent per phase → same-family delegate sub-subagents) is
  viable. Depth 3+ remains unprobed; re-verify after Cursor platform updates. A
  single-shot CLI executor still cannot spawn Cursor subagents mid-run — but any
  shell-capable architect (live session, subagent, or CLI) can instead delegate **by
  shell**: invoking `claude -p` as the delegate backend needs no Task tool at all,
  and routes delegate tokens to the Anthropic subscription pool instead of Cursor's
  (see `/execute-loop` → Optional delegating executor).
- **cursor-app-control `move_agent_to_root` auto-commits a checkpoint** (observed
  2026-07-02, v27 Stage 8 C2 live run) — account for it in filesystem-escape
  `git status` baselines and git-history expectations when a run moves the agent
  between workspace roots.
- **WSL workspace-root flapping** (observed 2026-07-03, a live downstream loop
  run): a Cursor host on WSL intermittently re-anchored the workspace between
  WSL and Windows paths mid-run — once breaking shell spawn entirely
  (`/bin/bash` ENOENT) and repeatedly making file-edit tools report "unable to
  read file" AFTER each edit had actually applied. Mitigation: **verify after
  edit** (grep the file for the applied change) whenever the workspace flaps,
  before re-applying anything — re-application duplicates content (same failure
  class as the tool-failure recovery lesson in `docs/lessons.md`).
- **`claude` WSL interop** works today (exec + file read/write on a WSL-path
  worktree); re-check if the Windows npm install or interop changes.
- **Anthropic Agent-SDK billing** (re-verified 2026-06-29): the separate-credit-pool
  split for `claude -p` / Agent SDK is **PAUSED** (paused on its 2026-06-15 effective
  date; programmatic usage still draws from subscription limits). It is officially
  announced and could return with advance notice. Hedge: route the headless
  executor/peer through **codex** (GPT — outside Anthropic's pool; already the
  cross-family peer when the executor is Claude), or a `claude -p`-compatible wrapper
  (fya / agentrun) that drives interactive Claude under subscription limits.
- **Severity non-determinism** across peer runs — see the contract section; converge
  on finding presence, not severity counts.
- **A single headless success is not sufficient** — single-shot agents can partially
  comply; require ≥2 fresh runs of a stable contract before trusting it.
- **A worktree is not a filesystem sandbox** under dangerous flags. Prefer
  least-danger flags (`codex -s workspace-write` / `read-only`, `claude
  --permission-mode acceptEdits`, `cursor-agent --sandbox enabled`); record the main
  checkout `git status` before/after every run; use real OS/container isolation for
  any run that genuinely needs danger-full-access.

## Reproduction notes (sandbox discarded)

The spike ran in a throwaway `git worktree` of this repo (so the installed workflow
skills resolved for the headless peer) seeded with a synthetic buggy `calc.py` + a
fixture plan carrying a Review Findings Log. The composer + harness were small shell
scripts driving `claude -p` / `codex exec` with the contract embedded in prompt
files. The worktree and harness were discarded after the spike; the invocations,
flags, contract, and decisions above are the durable output. Re-derive the harness
from this doc if Stage 5/7 needs to re-prove anything.
