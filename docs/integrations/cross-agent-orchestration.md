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
- **A Windows-native host (inventoried read-only over SSH, 2026-11-08 — v45.0):**
  Windows 11 Enterprise 10.0.22631; Python 3.13.14 (`python3` and `python` both
  resolve — the Microsoft Store alias); Git 2.51.0.windows.1 with Git Bash 5.2.37
  (`MSYSTEM=MINGW64`; `cygpath`, `timeout`, and `mktemp` present, `flock` and `setsid`
  absent); Claude Code 2.1.216; Codex CLI 0.144.4; system git config
  `core.autocrlf=true`. Python there has no directory-descriptor operations and no
  `O_NOFOLLOW`, writes a piped stdout as cp1252 unless told otherwise, and can create
  symlinks for an administrator. `C:\Windows\System32\bash.exe` is WSL's, not Git's.
  What runs there, and what does not: Host setup → A Windows-native loop host.

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
- **The bounded runner's permission line (v46.1; Claude Code composer hosts with
  the account router).** The composer's bounded runner, `scripts/loop-run-bounded.py`,
  is called for router work only, so only a host where `claude-switch-route` is
  detected ever needs its permission line,
  `Bash(python3 scripts/loop-run-bounded.py:*)` — a host without the router, and
  every Windows-native host, makes no runner call and needs no line. On a router
  host a Claude Code composer reads the settings files before its first runner
  call and, when the line is missing, asks ONE question — only from a session whose
  checkout is the main checkout, with no away grant bound; anywhere else it prints
  the line for the operator to add by hand. On `add` it writes the one line to the
  main checkout's untracked `.claude/settings.local.json` with one published
  command — never to a tracked or a user-level file (the bootstrap itself still
  ships and edits no settings file).
  What that file reaches: on Claude Code from 2.1.211, off Windows, a Claude Code
  session started in the checkout or in any worktree of the repo reads the MAIN
  checkout's local settings file and holds every allow rule in it — this line,
  and any broad rule beside it. From v46.3 a role the loop spawns is started with
  `--setting-sources user,project` — by the wrapper, on both tiers and on every
  resume — and reads no local settings file. The runner still refuses under a
  spawned role's environment (a non-empty `LOOP_ROLE`: one `REFUSE:` line, exit 2,
  nothing run): the refusal remains for a runner line a role holds some other
  way. That refusal is a guard against accidental use, not a boundary — a role
  that clears the variable in front of the command, or runs an edited copy of the
  script, gets past it. The shield is no boundary for the runner either: it does
  not cover a rule in the profile's settings or in a committed settings file, a
  run that grants a broad interpreter shape such as `Bash(python3:*)`, or
  `perms=bypass`. The normative text, with the read, the question, the command's
  contract, and the full list of the guard's limits, is `/execute-loop` →
  Preflight step 15 → The runner's permission. The shield's normative text is
  Preflight step 16 (the observations behind it: What a spawned `claude -p` role
  reads, below).
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

### A Windows-native loop host (v45.0)

From v45.0 the loops run on a Windows-native host — Claude Code in Git Bash with
Windows Python — as well as on Linux, macOS, and WSL. The skills are the normative
text (`/execute-loop` → Step 0's host sentence, Backends → the Spawn wrapper
paragraph, Preflight step 15's composer runner); this is the host owner's map.

- **What the host needs.** `python3` on PATH, resolvable from Git Bash — the
  Microsoft Store alias, or a `python3.exe` there (a copy of the installed
  `python.exe` under that name is enough); a host answering only to `python` or `py`
  does not satisfy it, and neither does a `python3.cmd` wrapper, because bash resolves
  no `.cmd` by a bare name (from v45.0 `python3` is required on EVERY host) — and Git
  for Windows: its Git Bash runs the `bash scripts/loop-spawn-wrapper.sh` grant
  shape, and WSL's `System32\bash.exe` is not it. Nothing else is installed:
  the bounded runner is `scripts/loop-run-bounded.py` (its own script from v46.0;
  it runs the helper's runner, and the helper refuses `run-bounded` as a
  subcommand; from v46.1 it refuses to run under a spawned role's environment —
  exit 2, nothing run; an accident guard, not a boundary: Host setup, above), so
  coreutils `timeout` is not relied on even where Git Bash ships it.
- **The shim and the Python wrapper.** `scripts/loop-spawn-wrapper.sh` is a thin exec
  shim on every host: it resolves `python3`, checks `scripts/loop-spawn-wrapper.py`
  against its committed blob, silences MSYS's own path conversion
  (`MSYS_NO_PATHCONV=1`, `MSYS2_ENV_CONV_EXCL='*'`), and `exec`s `python3 -I` on the
  `.py` — the ONE implementation, with v44.0's `LOOP_*` contract, stdout tokens,
  records, refusal order, and exit codes. Python owns path conversion: spell every
  `LOOP_*` path `C:/Users/…` (forward slashes and a drive letter; a Git Bash `/c/…`
  spelling is converted, any other `/`-rooted spelling — a UNC path included — is
  refused by name), and separate `LOOP_ADD_DIRS` members with `;`. Identity records,
  escape baselines, and the journal carry that one spelling.
- **Process groups are Job Objects.** Windows has no process-group id, so the
  wrapper's child, the launcher's peer, and a command run through
  `scripts/loop-run-bounded.py` (the composer's runner — from v46.1 it refuses
  under a spawned role's environment and runs nothing, an accident guard and
  not a boundary) each run inside a
  Job Object that is killed when its owner closes it; the exit census is the Job's
  process list (`children=0` only when the query succeeded). One accepted gap: the
  child is assigned to its Job right after it starts, so a grandchild forked in that
  instant would escape the census and the kill. A second, observed on the acceptance
  host: a process started through a Microsoft Store (packaged) app alias — the Store
  `python3.exe` among them — outlived its Job's kill together with its own child,
  while an installed program (`cmd.exe` running `ping`) died with the Job; treat
  whatever a role starts through a Store-packaged program as outside the kill, and
  assume it is outside the census too. The residual belongs to the Store package,
  not to Python: with the python.org build on the same host (v45.1), killing the
  same leg's wrapper took its `.cmd` stub and the Python child and grandchild with
  the Job, and the leg's scratch folders were removed. From v45.0 (T4.5) Step 0
  reads the interpreter the tooling will run — `python3`'s `sys.executable` and
  `sys.base_prefix`, not the alias stub — and when the base prefix lies under
  `\WindowsApps\` prints one warning
  naming that residual and asks whether the agent should fix it now (the python.org
  build via winget with its non-interactive agreement flags — the package puts its
  directories ahead of the alias directory on the user PATH — a `python3.exe` beside
  the installed `python.exe`, then a re-check of the base prefix from a fresh Git
  Bash; only if that still names `\WindowsApps\`, the user turns off the
  `python.exe` / `python3.exe` App Execution Aliases), continue as is, or stop; a
  headless or away run only warns. The
  normative text is `/execute-loop` → Setup wizard → Step 0 → Store-packaged Python.
- **Locks, output, and line endings.** The spawn lock is one locked byte at a fixed
  far offset of the lock file (a Windows byte-range lock blocks reads too, so the
  holder line sits outside the locked range); the helper, the wrapper, and the
  launcher write UTF-8 with LF on every host; three one-line `.gitattributes`
  payloads keep the shim, the rehydrate hook, and the install marker LF under
  `core.autocrlf=true` (Git for Windows' default). `scripts/.gitattributes` is a
  bootstrap-owned file from v45.0 — a project with its own file there merges the
  one line by hand.
- **What is different there.** `Router: UNAVAILABLE — Windows-native host`: router
  mode needs the dashboard's process census and private-cache checks, which have no
  Windows leg, so every role runs on its Profile answer. Architect mode's
  `fold-delegation` containment has no `O_NOFOLLOW` and no directory-descriptor walk
  to stand on: it refuses a symlink or a junction by a status check before each open
  and binds the file's identity after it — a documented residual, never the POSIX
  guarantee. The check is of the name being opened, not of the folders above it: a
  folder that passed the walk and is replaced by a link before a later open beneath
  it IS followed (observed on the acceptance host — the fold read and retired a
  record outside the run's folders). The loop-observer harness (`scripts/loop-observer/watch-loop-run.sh`;
  `docs/testing/loop-dogfood-harness.md`) is LINUX-ONLY — bash over `/proc` with
  `notify-send` — and is not ported.
- **What the Windows evidence is.** v45.0's Windows acceptance is SCRIPTED — legs
  run over SSH with stub children (the helper, wrapper, and launcher suites' Windows
  baselines, a stub spawn through the shim, the CRLF checkout), each leg's result
  recorded in the release's plan and summarised in `CHANGELOG.md`. A real unattended
  `/execute-loop` run on a Windows-native host has not been observed yet — treat the
  first one as a field test and read its log root with `/retro`.

## Per-CLI headless invocation (verified from live runs)

| CLI | Family | Headless invocation | Auth | Notes / gotchas |
|---|---|---|---|---|
| `claude` | Claude | `claude -p "PROMPT" --output-format text [--permission-mode acceptEdits] [--allowedTools "Bash(<scoped>)"] --setting-sources user,project </dev/null` (or pipe the prompt via stdin) | Works headless | Reads AND writes a WSL-path worktree via interop. `--permission-mode acceptEdits` is the **least-danger write mode and is sufficient** for file edits — no `--dangerously-skip-permissions` needed. Default `-p` mode already allows reads. Edits allowed under `acceptEdits`; UNGRANTED approval-gated shell is HEURISTIC — host-, version-, and config-dependent, with NO established allowed/denied command-class boundary (v27 Stage 8 C2 observed an `npm ...` denial on an earlier version; at 2.1.201 on the source host, 2026-07-10, several ungranted safe commands were auto-approved under `auto`/`acceptEdits` while the one observed denial was an out-of-workspace write — the auto-approval mechanism was not isolated, so treat attribution as inference and never key routing on assumed denials) — an orchestrating composer runs smoke/verification when the preflight harness probe or the grant set says so; scoped `--allowedTools` patterns are the DETERMINISTIC always-allow layer (verified 2026-07-02: `--allowedTools "Bash(npm --version)"` executed headless under `acceptEdits`). **`perms=bypass` recipe (user-opt-in tier, close-table-confirmed):** `--dangerously-skip-permissions` replaces `--permission-mode acceptEdits` AND any `--allowedTools` list (observed live 2026-07-10, 2.1.201: init `permissionMode: bypassPermissions`; ungated Write + unprompted shell with zero grants; the `.claude/` config-dir write-gating is LIFTED); the tier is INVOCATION-SCOPED — every `--resume` must re-pass the flag (a resume without it came up `permissionMode: auto`; the init event's `permissionMode` field is the deterministic per-invocation tier detector). Prefer narrow patterns (`Bash(npm run typecheck)`, `Bash(npx vitest run:*)`) over blanket `bash`; background long-lived processes (`npm run dev &`) or the session stalls; pipe/auto-confirm interactive prompts. **Live mid-run visibility:** `--output-format text` buffers the narrative to exit (a tee log can sit unchanged for a whole multi-minute run and flush at the end, and lines land out of chronological order) — for an orchestrated role, spawn with `--output-format stream-json --verbose` teed instead (verified 2026-07-03: events arrive as JSON lines in real time — init, per-turn assistant messages, tool-use `task_started`/`task_notification`, `result`; the stream also carries a live `rate_limit_event` line with `status` and `resetsAt`, usable for immediate limit-death detection). **Long-prompt shape (v29.2):** write a long spawn prompt to a gitignored file (e.g. `.cursor/loops/<runkey>-<role>-prompt.txt`) and deliver it via stdin redirect — `claude -p < promptfile`, the other flags unchanged — quoting-proof through any host interop layer that flattens or re-expands argv (the recorded `wsl.exe` class: embedded newlines flattened, the line re-expanded once before the inner shell runs, `$VAR`s arriving empty); observed live 2026-07-10: 7/7 incident-free long-prompt spawns in run lr291. |
| `codex` | GPT | `codex exec [-s read-only\|workspace-write] "PROMPT" </dev/null` | "Logged in using ChatGPT" | **stdin MUST be redirected** (`</dev/null` or a pipe) or it hangs on `Reading additional input from stdin...`. `--skip-git-repo-check` optional. Uses **bundled bubblewrap** for the sandbox (warns if `bubblewrap` not on PATH — optional `apt install bubblewrap` silences it). Prints a git diff of its edits. **`perms=bypass` recipe (user-opt-in tier, close-table-confirmed):** `--dangerously-bypass-approvals-and-sandbox` replaces the `-s` sandbox flag (verbatim from `codex exec --help`, codex 0.144.1; throwaway run observed live 2026-07-10 with run-header `approval: never` + `sandbox: danger-full-access` — the codex-side tier-verification surface); `codex exec resume` carries its OWN bypass flag and exposes NO `-s/--sandbox` option, so the tier is re-rendered per invocation, never inherited from the prior process. **The `workspace-write` sandbox denies localhost network** (observed live 2026-07-03: EPERM connecting to `127.0.0.1`) — a codex peer/role cannot run DB-backed or server-hitting suites; keep DB verification executor/composer-side, and peer reviews should state that split rather than reporting unrun DB suites as a gap. **Native multi-agent orchestration under `exec` works at 0.147.0 (probed 2026-08-29) — see the codex orchestration matrix below.** **From v34.1 a composer-seat peer round on an `/execute-loop` run with a run worktree is started through the shipped peer launcher, not typed by hand — see "The codex peer launcher (v34.1)" below.** |
| `cursor-agent` | GPT | `cursor-agent -p "PROMPT" --output-format text` | **Headless BLOCKED** | Requires `CURSOR_API_KEY` (or `agent login`); the interactive login that `cursor-agent status` reports is **not** sufficient for `-p`. The thin-orchestrator topology avoids needing it. |

All three support single-shot and resumable multi-turn; transport is a composer
ergonomics choice, not a capability gap. The spike used single-shot.

**Headless `claude -p` CAN delegate natively (verified 2026-07-02):** a `-p` session
carries Claude Code's `Agent` subagent tool — a child spawned headless ran and
replied to a sentinel — so a headless architect can delegate without any shell
nesting or allowlisting. A child spawned with no agent definition inherits the
parent's model and effort; the loop's delegate runs at the **model AND effort its
agent definition pins** (v43.0 — `model: <full ID>` and `effort: <level>` in its
frontmatter, the effort field omitted for inherit; the spawn passes neither
parameter; a shell-invoked delegate takes `--model` and `--effort` instead).
**Pin contract revised at v31.1 (observed live
2026-08-03):** the tool's per-invocation `model` parameter is an ALIAS-ONLY
closed enum (`sonnet | opus | haiku | fable`), ACCOUNT-RESOLVED — an alias pin
silently substituted a wrong tier in a live run, and a full model ID is rejected
at parameter validation — so the delegate pin is an AGENT DEFINITION (frontmatter
`model: <full ID>`, and from v43.0 `effort: <level>`, omitted for inherit)
selected via `subagent_type` with NO `model` and NO `effort` parameter passed,
verified per run by the `execute-loop` skill's Preflight step 6 probe (the
delegate's model from the probe's `modelUsage`, its effort from the subagent
transcript) and at each leg's exit consume (the first real delegation's
`modelUsage` MODEL read; the EFFORT read of every delegate of the activation —
the skill owns the reader and the selection rule; this doc names the duties);
the full contract lives in the `execute-loop` skill's **Optional delegating
executor** section (the subagent precedence orders, current since CLI 2.1.251,
are stated once there — the v31.1 arrow-form sentence is superseded).
Model alias note: `--model fable` = `claude-fable-5`
(`fable-5` is rejected as an unknown slug). Ungranted headless shell approval
is HEURISTIC — host-, version-, and config-dependent (see the per-CLI table
row) — so the composer runs the smokes when the preflight harness probe or the
grant set says so; scoped `--allowedTools` grants (verified; see the per-CLI
table row) let the architect run its own gates deterministically, and a
`perms=bypass` executor needs no grant list at all (see the permission-tiers
bullet below). Keep grants narrow and background long-lived processes.

**Codex CAN orchestrate subagents natively under `exec` (probed 2026-08-29,
codex-cli 0.147.0):** the `multi_agent` feature is stable and enabled at this
version (`multi_agent_v2` — thread orchestration — stays disabled), and the
orchestration surface works headless under `codex exec` with stdin redirected.
Every row below is VERSION EVIDENCE for the pinned 0.147.0, never a durable
capability fact — re-probe on any CLI update before relying on a row.
Provenance: OFFICIAL = stated by the official docs; PROBED = observed live on
this host 2026-08-29; SELF-REPORT marks rows whose evidence is the child
agent's own reply rather than an independent log surface.

| Capability (codex-cli 0.147.0) | Result | Provenance / evidence class |
|---|---|---|
| Feature flags | `multi_agent stable true`; `multi_agent_v2 stable false`; `multi_agent_mode removed false` | PROBED (`codex features list`) |
| Orchestration tool census | six tools, names verbatim from a read-only `exec` census: `collaboration.spawn_agent`, `collaboration.send_message`, `collaboration.followup_task`, `collaboration.wait_agent`, `collaboration.list_agents`, `collaboration.interrupt_agent` | PROBED (tool names are version evidence, not a contract) |
| Child interrupt primitive (no close/teardown tool) | `collaboration.interrupt_agent` interrupts a running child's ACTIVE TURN — the probed census statement: "interrupts a running child agent; no separate termination tool is available" — and the callable tool contract leaves the interrupted agent ADDRESSABLE for later messages/follow-up tasks; 0.147.0 exposes NO agent-teardown/close primitive, so exit-census expectations key on OBSERVED active-turn status via the probed `interrupt_agent`, never an assumed `close_agent` — a turn-interrupt is never read as lifecycle close | PROBED (census statement) + PEER-CONFIRMED tool contract (round-9 codex peer, same pinned version) |
| Custom-agent discovery | project-scoped `.codex/agents/` discovery works under non-interactive `exec` and the user-level `~/.codex/agents` dir is also consulted; NOT v2-gated. The OFFICIAL contract is STANDALONE TOML definitions — required `name`/`description`/`developer_instructions`, optional `model`/`model_reasoning_effort`/`sandbox_mode`/`mcp_servers`; the `name` field, not the filename, is the source of truth; markdown-frontmatter is NOT a documented format (developers.openai.com/codex/multi-agent, fetched 2026-08-29). Separately, a PROBED-ONLY 0.147.0 compatibility observation: a YAML-frontmatter `.codex/agents/*.md` fixture WAS discovered (and its frontmatter pins honored — the pin row) — version-pinned behavior, never the official recipe; the deferred architect/delegate work starts from the TOML contract | OFFICIAL (docs — dir locations + the TOML contract) + PROBED (discovery; the `.md` acceptance is PROBED-only) |
| Model / effort pins | frontmatter `model:` + `model_reasoning_effort:` honored on spawn — a non-default `model: gpt-5.4` / effort `low` pin came back from the child verbatim | PROBED — SELF-REPORT (no session-log/header surface exposed the child's resolved model under `exec`; treat as weaker than a log-verified pin) |
| Nested spawn (depth 2) | parent → child → grandchild chain returned the sentinel | PROBED — SELF-REPORT for the grandchild (its existence rests on the child's report; the transcript shows only the parent's wait) |
| Non-interactive `exec` inheritance | children inherit the parent sandbox/approval policy; a fresh-approval action fails back to the parent — probed: a child write under `-s read-only` errored `Read-only file system`, the exact error text routed to parent stdout, no file landed (the parent process surfaced overall exit 2) | OFFICIAL (inherited sandbox/approvals + fresh-approval failure are documented) + PROBED (the error-routing shape) |

Consequences for this workflow: the five review-family skills' fan-out clause
(v32.3) is capability-AND-authority probe-shaped, so a codex peer that finds
these tools exposed and delegation authorized may fan its review lenses out
inside its one `exec` activation, falling back to the documented sequential
path on any spawn/approval failure — fail-safe by construction (only the
speed win is lost). The `/execute-loop` architect/advisor/peer-seat role
menus stay codex-free in v32.3 on a SCOPE rationale, not a capability one:
the end-to-end `/execute-loop` codex backend route is not implemented or
field-validated in v32.3 (the probe verifies the primitives, not the route).
First-use watch items for the first fan-out field round: approval errors in
the peer's log, and exit-census survivors judged on OBSERVED active-turn
status — `interrupt_agent` is the probed active-turn interrupt primitive (an
interrupted agent remains addressable; 0.147.0 exposes no agent-teardown/
close primitive, so a census never claims teardown from an interrupt).

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
implemented by the shipped probe script `.cursor/bootstrap/probe-models.py`
(stdlib-only python 3; JSON-only stdout with `probe_schema: 1`; per-probe timeouts +
statuses; usage and advisor-capability probes behind the explicit `--usage` /
`--probe-advisor` flags — the latter is billed; exit 0 whenever JSON was emitted;
read-only in every probe mode — its one write-capable path, the env-gated
`--consume-codex-reset` mode of v33.6, is never invoked by the wizard or a loop step) —
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
  (full names also accepted by the CLI `--model` flag, e.g. `claude-fable-5` —
  NOT by the subagent tool's `model` parameter, which is alias-only; see the
  v31.1 delegate-pin note above). Effort choices are enumerated
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
- Native-subagent delegate (a `claude -p` architect, v43.0): `effort: <level>` in
  the agent definition's frontmatter, omitted for inherit; the spawn passes no
  `effort` parameter (the `execute-loop` skill's pin contract).

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
  From v33.6 the script also runs one separate exchange per eligible
  `CODEX_HOME` for its `codex.accounts[]` entries, each sending
  `account/read` (email, plan, workspace routing), this rate-limit read,
  and `account/usage/read` (daily token buckets); there is no global
  deadline — the codex leg's worst case is
  `ceil(homes / workers) × (max(--timeout, 30) + ~16 s shutdown ladder)`
  plus one such exchange for `codex.usage` (see the v33.6 document
  additions below).
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
  worked — the install unlocks the full capability surface (executor-run
  smokes, and the `peer-seat=executor` opt-in's in-executor `/peer-loop` —
  from v31 the composer seat drives the peer pass by default either way, so
  the opt-in is what the install unlocks, not the default topology), not just
  profile selection. An agent may run the
  install only after explicit user confirmation, and only after checking WSL
  node/npm exist (absent → hand the user the install instruction instead). The
  inline `WSLENV` prefix (see the WSL interop caveat below) is a
  workaround-grade fallback for runs that must stay on the Windows shim;
  continuing degraded means default account only, composer-run verification,
  and no in-executor peer pass (the composer-seat default is unaffected).
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
  script never writes here (read-only in every probe mode; its only
  write-capable path, the env-gated `--consume-codex-reset` of v33.6, is
  never reached from this flow). The safe shape: resolve an exact enumerated
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

### Router mode (v41.0)

`/execute-loop`'s `router=on` run setting hands the per-spawn choice of profile
folder to claude-switch-gui's **account router** — the `claude-switch-route`
command — instead of the fixed `profile_dir` above. The skills are the
normative text (the Q5 Router item, the Spawn wrapper paragraph, Preflight
step 15, Usage-exhaustion recovery's router branch, Mechanical close
enforcement's release); this subsection is the downstream reader's one-page
map of the whole contract and the host it needs.

- **What routes and what does not.** Every `claude -p` role the composer
  spawns through `scripts/loop-spawn-wrapper.sh` — the executor or architect
  (its native-subagent delegate rides inside that session), a `claude -p`
  peer, and every respawn or resume of them — and the composer-seat codex
  peer spawned through `scripts/loop-peer-launcher.py`. NOT routed: the
  advisor and consult rows and an in-executor codex peer under
  `peer-seat=executor` (they spawn directly, on their fixed profile — the
  close table names them), and every spawn made without `LOOP_ROUTE_BIN`
  (a `router=off` run, a pinned leg — below). The router works at SPAWN
  time only: it never moves a running session.
- **The contract** is the consumer's `docs/integrations/account-router.md`
  (`claude-switch-gui`, `route_schema` 1): `pick --agent claude|codex --run ID
  [--model ID] [--role R] [--phase P] [--pid N] [--label TEXT] [--failed DIR]...
  [--json]`, `release --run ID [--role R] [--phase P]`, `status [--json]`,
  `--version` → `route_schema 1`. An answer is exit 0 and one JSON object
  (`route_schema`, `dir`, `short`, `class`, `sticky`, `record`, `why`); no
  answer is exit 3, nothing on stdout, and the reason word as the FIRST stderr
  line — the contract's eleven: `cache-dir-not-private`, `lock-timeout`,
  `records-unreadable`, `bound-account-gone`, `no-snapshot`, `router-off`,
  `no-server`, `stale-snapshot`, `records-full`, `records-unwritable`,
  `no-candidate`; a usage error is exit 2 with argparse prose (an empty value,
  a value over 128 characters, or one read as a flag — hence the
  `--flag=value` forms). The caller's rule: a missing command, a non-zero
  exit, empty output, or a folder that does not exist all mean "no answer";
  the router never makes a run stop. The same `(agent, run, role, phase)`
  gets the same folder back (the binding) until `release`, `--failed` for
  that folder, or 24 hours; `--failed DIR` rests the folder's whole pool for
  30 minutes for every run on the host. The scripts add their own no-answer
  words for what they observed themselves: `usage` (exit 2), `timeout` (the
  20 s deadline), `overflow` (a stream past 4096 bytes), `bad-json`,
  `bad-schema`, `no-dir`, `bad-dir` (the answer rule's folder checks),
  `resume-mismatch` (the wrapper's resume rule — from v47.0: the answer is
  not the folder that holds the resumed session's transcript), and `other` (anything
  else — a word outside the eleven, a signal, a router that could not
  start, a collector failure). From v42.0 (D5) the scripts also RELAY what
  a diagnosing router prints after its reason word: the wrapper's
  `SPAWN_WARN check=route-skipped detail="<text>"` — a second line right
  after `SPAWN_WARN check=router`, a token outside the `check=router`
  prefix — and the launcher's second note `router: skipped - <text>`; the
  text is the router's remaining stderr lines (`<dir> <reason>` per
  candidate, joined `; `) or the scripts' own `<dir> <check>` for a folder
  they refused (`no-dir`, `not-owned`, `group-writable`, `world-writable`,
  `unresolvable`, `inside-root`; the shape rule's `relative`, `quote`,
  `control-byte`, `unicode-space`; the wrapper's `resume-mismatch`),
  sanitized under the records helper's value rule and capped at 512 bytes
  by the collector (the router text and the folder; the wrapper then
  appends the closed check word AFTER that cap, so its line can exceed
  512 bytes by one word, while the launcher caps the whole note — the
  wrapper's usage header is the rule's owner), absent when there is
  nothing to say. A router from claude-switch-gui's 2026-11-08 change on
  prints one `<dir> <reason>` line per candidate it set aside after
  `no-candidate`, and its `status --json` carries the same as a top-level
  `skipped` map keyed by class (additive on `route_schema` 1 — the wizard's
  `Router:` line prints it as `skipped: …`, v45.0); an older router prints no
  further line. The composer journals BOTH lines as `ADOPT:`.
- **The call shapes** (`--flag=value`, every value byte-for-byte from the
  variables that feed the `ROLE: start` record — never trimmed, a flag
  omitted when its variable is empty): the wrapper's
  `pick --agent=claude --run=<LOOP_ISO> --role=<LOOP_ROLE> --phase=<LOOP_PHASE>
  --model=<LOOP_MODEL> --pid=$$ --label=<repo basename> --json` (after the
  spawn lock and the escape pre-capture, before `ROLE: start`); the
  launcher's `pick --agent=codex --run=<LOOP_ISO> --role=peer
  --phase=<LOOP_PHASE> --model=<LOOP_MODEL> --pid=<its own pid>
  --label=<base basename> --json` (after the pre escape capture, before the
  keyed start). Both run the ONE collector (from v45.0 the records helper's
  `route_collect`, which the wrapper and the launcher import from a
  blob-verified snapshot of `scripts/loop-journal.py`): the router in its own
  session with stdin from the null device and the evidence descriptors
  closed, both pipes drained concurrently with at most 4096 bytes of each
  retained, no file-size limit on the router, a 20 s deadline ending in a
  group kill, the readers joined under the same bound, a catchable
  cancellation (TERM / INT / HUP) a terminal condition, the router's group
  swept at every return, and its identity held until the last signal (the
  leader observed, never reaped, until the sweep; one reap after it; the
  default SIGCHLD disposition set before the router starts — the launcher
  restoring its entry disposition once the router is released, before the
  role child starts — and an ECHILD from the observation a lost reservation
  — released at once, nothing signalled, no answer; on a python3 without `os.waitid` — CPython on macOS,
  and Windows Python, where the wizard prints `Router: UNAVAILABLE — Windows-native host` up front (v45.0)
  — no router is started at all: the pick takes the `other` fallback before
  any identity is acquired, so router mode never routes there, and every
  spawn runs on its Profile answer) — `LOOP_ROUTE_BIN`
  (the command's absolute realpath; never a PATH lookup) is the only
  switch, set by the composer under `router=on`, refused by the wrapper
  without `LOOP_IDENTITY_FILE`, `LOOP_ISO`, or `LOOP_PROFILE_DIR`, beside a
  token pool, with a fallback folder failing the answer rule, or when its
  realpath lies inside an executor-writable root — or a root or the
  command itself does not resolve to a clean physical path (the wrapper's
  usage header and the launcher's docstring hold the full lists). The answer
  rule: `route_schema` an integer equal to 1, `dir` absolute with no control
  byte or `"`, `sticky` a boolean; the folder exists, is owned by the user,
  not group- or world-writable, outside the executor-writable roots.
- **What the composer sees.** The wrapper prints `SPAWN_ROUTE dir="<dir>"
  via=pick|binding` on an honoured answer and `SPAWN_WARN check=router
  detail="<word>"` on no answer — and (v42.0) the `SPAWN_WARN
  check=route-skipped` line right after it when there is a reason to relay
  — on its OWN stdout — every line composer-journaled as `ADOPT:`, never a
  probe-log record; the `ROLE: start` keys are unchanged.
  The launcher reports through `note()` on standard error (its stdout
  shapes are pinned). The identity files carry the truth: the wrapper's
  `profile_dir=` is the EFFECTIVE folder (the router's literal `dir`, else
  the fallback — on a resume, from v47.0, the folder the resume pin found
  holding the transcript) plus `route_run=<LOOP_ISO>` and `route_phase=<LOOP_PHASE>`
  on every spawn made with `LOOP_ROUTE_BIN` set; the launcher's
  `codex_home=` is the effective home (the pick, else the inherited
  `CODEX_HOME` verbatim, else `<HOME>/.codex`) plus the same two keys.
  Readers look keys up by name. The composer COPIES these values into its
  resumes and re-picks and never retypes them.
- **Resumes and the manual switch** (a map, not the rule — the owner is
  `/execute-loop` → The per-phase loop, step 1, with the Switch account
  option of Usage-exhaustion recovery). A resume inside a phase lands in the
  folder that holds its transcript: the composer passes the identity
  record's `profile_dir` as `LOOP_PROFILE_DIR` — and (v42.0 D6) the record's
  `route_phase=` as `LOOP_PHASE`, byte for byte, on a routed identity: the
  binding is keyed by `(agent, run, role, phase)`, so a re-worded phase label
  mints a fresh record and reads `resume-mismatch` whenever that pick is not
  the folder holding the transcript (the field cause of every mismatch seen in
  2026-10: three kount resumes re-worded the phase, while 34 machines resumes
  on stable phase slugs had none); a pinned
  identity (no `route_run=`) keeps the phase label, the first pinned leg
  after a routed one carrying the routed record's `route_phase=`; the
  composer prints the record's lines before every resume and copies from
  them (the owner is `/execute-loop` → Visibility + run-state, the Resume
  contract). **The resume pin (v47.0).** The wrapper no longer trusts the
  folder it is handed: on a `LOOP_RESUME_SESSION` spawn it searches
  `LOOP_PROFILE_DIR`, the router's answer, and the ambient folder for
  `projects/*/<session>.jsonl` and starts the role on the folder holding the
  newest copy. It honours the router exactly when its answer IS that holder,
  whatever its `sticky` flag (else `resume-mismatch`, and the role runs on the
  holder); it prints `SPAWN_WARN check=resume-pin detail="<holder>"` when the
  holder is not the folder passed and `SPAWN_WARN check=resume-pin-stale` for
  older copies elsewhere; and it refuses the spawn — `SPAWN_REFUSED
  check=resume-pin`, a new class in the wrapper's frozen refusal list — when
  no candidate holds the transcript, or one could not be searched (the owner:
  the wrapper's usage header; `/execute-loop` → Backends). The identity
  record's `profile_dir=` is written on every spawn from v47.0, the ambient
  folder included. A manual switch of a ROUTED
  role (its identity record carries `route_run=`) drops the binding with
  `pick --failed` first and resumes without `LOOP_ROUTE_BIN`, which pins the
  role for the rest of the phase; a role already pinned switches with no
  pick and stays pinned.
- **The re-pick (a limit failure)** — a map, not the procedure: every step,
  bound, and disposition is stated ONCE in `/execute-loop` →
  Usage-exhaustion recovery, the router branch (the `claude -p` peer's and
  the codex peer's branches beside it), under the composer runner Preflight
  step 15 publishes. In one sentence: a role DEAD on a limit whose identity
  record carries `route_run=` is re-picked by the composer — reserved first
  on the existing `key=profile-fallback` decision record, `--failed` the
  failed folder read from that role's identity record (the wrapper's
  `profile_dir=`; the launcher's `codex_home=` — sent only when that value
  is an absolute path, since the launcher records a relative inherited home
  verbatim), the answer held to the answer rule and verified per backend,
  then the existing switch, a fresh respawn, or a fresh launcher round —
  three per run on one counter, the unasked `profile-fallback=` dir the
  Claude roles' last resort and, for the codex peer, the launcher's
  inherited home only when it differs from the failed home, else the pause.
- **The release** — a map: after the helper's FINAL-route `run-close`
  reports `complete` or `already-closed`, `release --run=<iso-id>` runs
  whenever the command resolves, and never on the group route, at a park,
  or at a group end; the one statement, which `/close-run`'s call sites
  point at, is `/execute-loop` → Run isolation → Mechanical close
  enforcement (the router release).
- **The codex peer's runtime dir (v42.0 D8).** The launcher creates a private
  per-launch directory `<TMPDIR, else /tmp>/loop-peer-xdg.<random>` (mode
  0700), exports it to the codex child as `XDG_RUNTIME_DIR` — a writable
  runtime dir inside codex's `workspace-write` sandbox — and removes it once
  the child and its group are gone (restoring owner permissions on owned,
  non-symlink directories a child left unreadable, and reporting on standard
  error any residue it cannot remove, never claiming removal);
  `XDG_CONFIG_HOME` and `XDG_CACHE_HOME` are NOT redirected (git reads the
  operator's config from the former). The launcher's docstring is the owner;
  `/peer-loop`'s invariant (e) is the prompt-side companion (the suites a
  sandboxed peer must not run).
- **The host.** `claude-switch-route` is installed from the consumer's main
  checkout by `bin/claude-switch-gui --install-cli` (two symlinks in
  `~/.local/bin`, which must be on the loop shell's PATH); the dashboard
  must run in background mode with the router switched ON in it (`router-off`
  otherwise); every candidate profile must be logged in and swept (the
  snapshot goes stale after 660 s without a sweep). **The folder rule, as a
  host requirement (the one operator-facing statement; the wrapper's usage
  header is the rule's owner):** every folder a routed role can run under
  must be owned by the user and neither group- nor world-writable — the
  wrapper's answer-rule FOLDER checks, mirrored by the launcher (the rule's
  other checks — absolute, existing, no control byte or `"`, a clean
  physical path, outside `LOOP_CWD` and every `LOOP_ADD_DIRS` root — must
  hold as well; the remedy below addresses the write bits only, and the
  wrapper's usage header is the complete rule). It is
  applied to every ANSWER the router gives (a Claude candidate or a codex
  home) and, as the wrapper's refusal 6, to each `claude -p` role's Profile
  folder — its fallback; the launcher's inherited codex home is not held to
  it. From v42.0 the wizard's close table and Preflight step 15 (g) check
  every CANDIDATE folder the router may pick too — every entry of
  `status --json`'s `order` lists, for claude AND codex — naming each
  failing folder with its check (`chmod go-w` the remedy for a write-bit
  failure; any other check is the dashboard's pool to fix), at the confirm,
  at preflight, and on every resume (the field case: eleven codex rounds
  across kount and machines fell back on `bad-dir` in 2026-10 because
  `~/.codex` was mode 775 while the Claude folders had been fixed — the
  launcher's first note read `bad-dir` and nothing named the folder). What
  fails where: a fallback failing the rule stops the wizard's confirm
  (`Router: UNAVAILABLE — <role>'s profile_dir fails the folder rule`, the
  close table; a failing candidate renders its own `UNAVAILABLE` line there
  and a WARNING at preflight); an answer failing it is `bad-dir` (`no-dir`
  for a folder that does not exist) — the
  wrapper's `SPAWN_WARN check=router detail="bad-dir"` line, the launcher's
  `note()`, each followed from v42.0 by the second line / note naming
  `<dir> <check>` —
  and the role runs on its fallback (the codex peer on its inherited home) —
  on EVERY spawn of that (run, role, phase), because the router records the
  binding before the wrapper tests the folder and answers it again (sticky)
  until the run's `release`, a `--failed` on it, or 24 hours, and the wrapper
  sends neither; a pool of such folders routes nothing while the dashboard
  shows the run bound. Where every folder a role could run under ACTUALLY
  carries a group or world write bit, changing the Profile item cannot help
  (on this repo's own host, 2026-10-27, `umask 0002` had left all five
  Claude profile folders mode 775 — rehearsal A's finding; the validators
  read each folder's own mode, never the umask, so an existing 0700 or 0755
  folder passes on any host). The remedy is `chmod go-w` on each failing
  folder — the fallbacks AND every candidate in the dashboard's pools, the
  Claude folders and the codex homes alike — before router mode is
  switched on; the rule itself is not loosened for a user-private group (a
  Deferred item of the v41.0 plan). The per-account lever is the
  dashboard's EXCLUSION switch (an excluded account is never a NEW pick;
  a run's existing binding to it keeps answering until `release`, `--failed`,
  or its 24 hours — the router answers the binding before the gates) — there
  is no per-role pinning in the loops. The record store
  `~/.cache/claude-switch-gui/leases.json` is shared by every run on the
  host (about two records per routed phase; 256 unexpired bindings is the
  cap); an unreadable store answers `records-unreadable` to every request
  and is reset only by removing the file by hand — every binding in it is
  lost. The Phase 4 rehearsals (one routed wrapper spawn with the re-pick
  tail on a scratch `--cache-dir`; one launcher round under a routed
  `CODEX_HOME`) are the recorded proof on this host; the selftests use
  fakes only and never touch the real cache dir.

## Cloud VM token pools (Cursor Cloud; v32)

Cursor Cloud environments cannot store browser-login credentials — VM teardown
destroys everything not committed. The proven pattern (6 pools verified live
2026-08-10, CLI 2.1.226) seats per-account **setup-token secrets** at boot and
addresses them as numbered pools:

- **Seating (boot script, kount-side `agent-cli-auth.sh`):** per-account
  Secrets `CLAUDE_CODE_OAUTH_TOKEN_1..8` (from `claude setup-token`) are
  seated into per-pool config stores `~/.claude-acct<N>` on boot. The
  `<N>` binding is DETERMINISTIC: `~/.claude-acctN` ⇔
  `CLAUDE_CODE_OAUTH_TOKEN_N`, and every consumer (wrapper validation,
  probes, identity markers) keys on that mapping.
- **Spawn recipe:** headless spawns prefix BOTH variables —
  `CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN_N"` AND
  `CLAUDE_CONFIG_DIR=~/.claude-acctN` (per-dir `.credentials.json` outranks
  env auth in 2.1.x, so the pair is belt-and-braces; the interactive
  `/usage` panel probe is the one seated-store-only exception below).
  Loop-spawned roles carry this via the spawn wrapper's
  `LOOP_OAUTH_TOKEN_ENV` input (v32 TD.2): the composer passes the
  numbered secret's NAME, the wrapper validates it fail-closed (exact
  numbered grammar; the acct<N> mapping against `LOOP_PROFILE_DIR`; the
  named variable set non-empty) and exports the canonical variable by
  shell INDIRECTION — the token value never appears in the wrapper's OWN
  emissions (argv, its probe-log lines, the identity record, or any
  wrapper error), and the child environment is least-credential (every
  numbered pool variable + the selector removed; identical on fresh
  spawns and resumes). Honest boundary (v32 PR-HIGH-020): the enforced
  zero-token-bytes guarantee covers wrapper-authored output, the probe
  log, and the secret-swept committed evidence — NOT the tee'd role log,
  which mirrors the child's stdout; the child necessarily holds the
  canonical token to authenticate, so a child that echoes it lands those
  bytes in the role log. Role logs are gitignored + never committed, and
  the persist-before-close secret sweep is the backstop — treat a
  transient role log as potentially token-bearing, never secret-free.
- **Auth-status shape (setup tokens):** a setup-token credential has no
  refresh token and no `user:profile` scope, so `claude auth status`
  reports **`Login: Expired — log in again` with `email: null` while
  inference WORKS** — never read that status line alone as an auth
  failure. Verify a pool with ONE cheap `-p` call (e.g.
  `CLAUDE_CONFIG_DIR=~/.claude-acctN "<pinned claude>" -p "ok"
  --output-format text </dev/null`); the wizard surfaces such pools as
  identity-DEGRADED rows, listed and selectable, never dropped.
- **Usage probes (both, layered — print-mode `/usage` returns exact quota
  lines on CLI 2.1.278 (verified live 2026-09-20) and returned none at
  2.1.226 on these VMs, both auth modes; from v33.3 `probe-models.py`'s
  `probe_usage()` tries the one-call print path FIRST — recipe 2's
  stream-json call, whose result text carries the exact lines where
  print-mode works — and falls back to the tmux panel, recipe 1, only
  where print-mode is dark, a parsed panel outranking the threshold
  evidence; accounts are probed in parallel, so a sweep is typically
  ~5–15 s on a nine-profile host where print-mode is exact (4.8 s
  measured 2026-09-20) and, where it is dark, grows with the number of
  worker batches, the stream-json retries, and the 45 s panel deadline;
  from v33.5 `--print-only` pins the sweep to that first layer, so the
  panel never launches; the call bound is separate — one stream-json
  call per account plus two independent single retries, one when that
  call times out or fails and one when the result then classifies
  `degraded` on a logged-in store (the second OR the third call), so
  one to three calls per account):**
  1. **Interactive-panel probe (unbilled; exact at every usage level; the
     only exact source where print-mode is dark).** Scripted tmux TTY:
     throwaway private-socket session running the pinned CLI, send
     `/usage`, capture-pane, parse the panel (line-wrapped bars parse
     across lines; "Per-model breakdown unavailable (rate limited)" can
     coexist with valid bars; press `r` once to retry a panel missing the
     week line). **Answer the workspace-trust prompt by explicit
     selection, never a bare `Enter`:** CLI 2.1.278 lists and highlights
     "No, exit" first (2.1.226 highlighted "Yes, I trust this folder"),
     so the probe sends `Down` then `Enter` only when it recognizes a
     highlighted "No, exit" with "Yes" listed below it, `Enter` alone
     only on a highlighted "Yes", and re-captures — never confirms — an
     unrecognized frame; 2.1.278 also drops the `? for shortcuts` idle
     hint (the probe keys readiness on the permission-mode status line
     as well) and can show a first-launch "Chrome extension detected"
     interstitial, which the probe declines. The script runs the pane
     (and its print-mode call) from its neutral cwd — the first usable
     temp dir, normally shared and world-writable — so the trust answer
     trusts THAT directory and the CLI may record it in the probed store
     (CLI behaviour, not verified here); on a multi-user host whose other
     local users are not trusted, point `TMPDIR` at an existing private
     directory before running `--usage` (the script's resolver honours it
     ahead of `/tmp`). **Token-env-suppresses-
     bars gotcha: launch with the SEATED STORE ONLY — a
     `CLAUDE_CODE_OAUTH_TOKEN` in the environment suppresses the quota
     bars**, so the panel probe strips the canonical token (plus every
     numbered pool variable) from its pane environment.
     `probe-models.py`'s layered `probe_usage()` implements exactly this
     as its SECOND layer (usage_source `panel`, usage_quality `exact`) —
     skipped entirely under `--print-only` (v33.5).
  2. **One-call stream-json probe (billed, minimal; the script's FIRST
     layer from v33.3).** One
     `-p "/usage" --output-format stream-json --verbose` call: where
     print-mode works its result text carries the anchored quota lines
     (`Current session:` / `Current week (all models):` — usage_source
     `print`, usage_quality `exact`; a bare `%` line such as the
     contribution stats is never exact evidence), and where it is dark
     the stream's `rate_limit_event` is the evidence, carrying
     `rate_limit_info.{status,utilization,resetsAt,rateLimitType,isUsingOverage}`;
     statuses rank `allowed > allowed_warning > rejected`, and exact
     utilization only appears past the ~75% warning threshold — below it
     treat `allowed` as healthy headroom, never a percentage
     (usage_quality `threshold`; the probe never renders threshold
     evidence as a percentage). Gate it behind the existing lazy
     `--usage` timing. From v33.5 a `degraded` classification on a store
     whose identity probe reported `auth_state` `logged-in` is re-run
     ONCE and re-classified (max 2 attempts on that branch); a
     logged-out or indeterminate store never pays it, having no quota
     lines to recover.
  **v33.5 document additions (`probe_schema` stays 1; every field
  additive-optional in both skew directions).** Each claude usage object
  also carries `week_model_pct`, `week_model_name` and
  `week_model_resets`, read from the FIRST `Current week (<name>):` line
  (print) or block (panel) that is NOT the all-models one — the name
  stripped of its parentheses, the resets text verbatim and null when the
  line carries no resets clause, later model lines ignored, all three null when no model line
  exists. The anchors are unchanged: a model line is NEVER substituted
  into `week_pct` / `week_resets`, and a model line ALONE is never exact
  evidence. Each account row also carries `org_id` (the `auth status`
  JSON `orgId`, on a logged-in answer only, else null — the key for
  grouping seats that share one weekly pool, which usage evidence alone
  cannot distinguish) and `auth_state` — `logged-in` | `logged-out` |
  `indeterminate`, where a timed-out or absent `auth status` is
  `indeterminate` and NEVER a logout. The `capabilities` list gains the
  informational tokens `week-model`, `org-id` and `print-only`; detect
  the FLAG itself via `--help`, never by reading a token out of a
  document you did not run.
  **v33.6 document additions (`probe_schema` stays 1; every field
  additive-optional in both skew directions; ONE additive status value).**
  `codex.accounts` is ALWAYS emitted (possibly `[]`): one entry per
  eligible `CODEX_HOME` — a real directory (never a symlink) at
  `~/.codex` or `~/.codex-cut<digits>`, not a `*.lock` control dir or a
  quarantine-marked dir, holding an `auth.json` file, its parent
  realpathing to `$HOME`. Unlike the claude profile predicate a symlinked
  home is INELIGIBLE and never spawned, so a symlinked `~/.codex` is itself
  never listed while every other eligible home still is (`[]` only when
  none exists), and `is_default` is realpath equality with `~/.codex` — a
  link that targets an eligible cut home makes THAT entry the default.
  Consumer fallback: `codex.accounts == []` with `codex.usage.status ==
  "ok"` (a symlinked default and no other eligible home) → render the
  legacy `codex.usage` row. Entry keys, every key in every entry and null
  when unknown: `home`, `is_default`, `status` (`ok` | `degraded` |
  `failed` | `timeout` | `logged-out` | `skipped` — `logged-out`, a null
  `account/read` account, is the additive value, used by this list only),
  `error`, `email`, `plan`, `account_id`, `session_pct` /
  `session_resets_at`, `week_pct` / `week_resets_at` (the `codex.usage`
  window rules, epoch seconds verbatim), `reset_credits`
  (`available_count` + `items`), `daily_tokens`, `additional_limits`
  (null, reserved); null-vs-empty passes through untouched, and `ok`
  needs all three reads as parsed results (else `degraded` naming the
  read and the cause). Homes are probed only behind `--usage` and never
  under `--profile-dir` (entries `skipped` otherwise). The repeatable
  `--codex-home DIR` replaces enumeration with the requested homes in
  argument order and SKIPS the Claude leg (`claude.status` `skipped`, the
  report line `claude SKIPPED (--codex-home)`; with `--profile-dir` it is
  a usage error); an ineligible DIR is its own entry `failed` "ineligible
  home" — with or without `--usage` — and is never spawned; `codex.usage`
  is probed under `--codex-home` only when `~/.codex` is among the
  selected homes, and is otherwise the v33.5 `skipped` shape — its bytes
  are unchanged from v33.5 wherever it is probed. Every per-home child
  gets `CODEX_HOME` SET to its home (the script's own ambient
  `CODEX_HOME` is ignored there, still inherited by `codex.usage` and the
  models catalog) and `OPENAI_API_KEY` / `CODEX_API_KEY` /
  `CODEX_ACCESS_TOKEN` removed by name — the binary honours them as an
  auth source ahead of the home's `auth.json`. Verified 2026-09-26 on
  codex-cli 0.157.0: an empty scratch `CODEX_HOME` answered `account:
  null` plus two `-32600` authentication errors with no bleed from the
  logged-in default home, and the server WROTE state files into the home
  it was pointed at (`installation_id`, `skills/`, several `*.sqlite`
  databases) — why the predicate runs before every spawn. **Consume mode**
  (the script's ONLY write-capable mode): `--consume-codex-reset` with
  `--codex-home DIR`, `--credit-id ID`, and `--idempotency-key KEY` —
  every argument exactly once, `ID` / `KEY` matching
  `[A-Za-z0-9_-]{1,128}`, abbreviations never expanded, and none of
  `--usage` / `--profile-dir` / `--print-only` / `--probe-advisor`
  (`--workers` / `--plans-dir` are accepted and inert; `--timeout` sets
  only the exchange ceiling `max(--timeout, 30)`).
  Any violation of that grammar is a usage error — exit 2, NO JSON, no
  process — and so is every invocation made without the environment
  variable `PROBE_ALLOW_CONSUME` set to exactly `1` (checked FIRST among
  the semantic checks, so a well-formed mis-invocation reveals only "not
  enabled", and re-checked by the runner before any spawn). Otherwise it
  prints `{"probe_schema": 1, "consume": {"home",
  "status": "ok" | "failed" | "timeout", "outcome": "reset" |
  "nothingToReset" | "noCredit" | "alreadyRedeemed" | null, "error"}}`
  at exit 0 — an ineligible DIR answers `failed` "ineligible home"
  without a spawn, an internal error `failed` "internal: …". A `timeout`
  or `failed` returned AFTER the request was written is INDETERMINATE,
  never "not consumed": re-read `account/rateLimits/read` before retrying
  with the SAME idempotency key (the probe itself never retries). Run it
  only from the consumer, on the user's explicit instruction — never from
  a test, a review, an acceptance run, or this repo; no runnable recipe
  is published here. **Session persistence:** where the pinned CLI's
  `--help` advertises `--no-session-persistence`, both print-mode calls
  (the stream-json `/usage` call on every attempt and the billed advisor
  call) carry it, so a sweep no longer writes a session log per call
  (verified 2026-09-26 on Claude Code 2.1.282: +0 `projects/` logs
  flagged, +1 unflagged, the quota lines parsed exact both ways);
  `claude.help.no_session_persistence` records the detection. The
  `capabilities` list gains `codex-homes` (always) and
  `no-session-persistence` (a support token: present whenever the flag
  is advertised, whether or not this run made a print-mode call).
  Do NOT build on `api.anthropic.com/api/oauth/usage` — it 429s from
  shared cloud egress IPs.
  **v33.7 (Claude Code 2.1.286; no new field, `probe_schema` stays 1).**
  Print-mode `/usage` itself reads that endpoint: the quota lines come
  from the CLI's own `GET /api/oauth/usage` (5 s timeout), answered from
  a snapshot in the store's `.claude.json` for 60 s and seeded from it for
  up to an hour when the read fails. Past that the CLI OMITS the quota
  lines and prints only its subscription banner ("You are currently using
  your subscription …") plus its "What's contributing to your limits
  usage?" report (verified live and from the 2.1.286 bundle 2026-10-02).
  The probe classifies that failed-read shape as `degraded` with a fixed,
  percentage-free headline instead of the report text, keeps the v33.5
  logged-in retry, and ends the tmux panel as soon as it shows "Failed to
  load usage data" (the panel reads the same endpoint, so the 45 s
  deadline is no longer spent). The exact headline now carries
  quota-shaped lines only. The same stream-json call's assistant event
  carries a structured twin, `usage_report.rate_limits.limits[]`
  (`kind` `session` | `weekly_all` | `weekly_scoped`, `percent`,
  `resets_at` ISO); when the text has no anchored line the probe reads it
  as exact print evidence (text always first; resets as a local ISO
  minute string), which shields the parse from a reworded print line.
  It is null on the failed-read shape too, so no CLI surface recovers
  the percentages while that endpoint is failing.
- **Identity mapping + the seat-sharing caveat:** two pools can be seats
  on ONE underlying plan pool — identical week percentages with
  to-the-minute-identical resets are the signature — and usage evidence
  alone cannot distinguish them, so treat same-plan seats as ONE budget
  when picking pools. The labeling channel is the optional
  `CLAUDE_PROFILE_EMAILS` secret (`"1:email,2:email,…"`) which the boot
  script materializes as one-line `~/.claude-acctN/profile-email.txt`
  markers (writer: kount-side follow-up); the probe/wizard reads them
  under the pinned bounded safe-read contract (v32 TD.3:
  `read_profile_email_marker()` — no-follow regular-file open, one short
  UTF-8 line, pinned email grammar, fail-silent degradation) and renders
  marker-sourced labels (`ops@example.com [marker]`).
- **Evidence persistence:** `.cursor/loops/` is gitignored and dies with
  the VM — a run that should leave evidence uses the wizard's
  `persist=on` ephemeral-host answer, whose persist-before-close order
  commits ONE bounded secret-swept evidence file under `docs/retros/` on
  the run branch before lifecycle close (the `/execute-loop` close
  contract; v32 TD.5).

## Cross-repo read roots (`--add-dir` / `additionalDirectories`)

When a plan references a second repo (a companion project, a reference
checkout), a spawned role needs an explicit read root — nothing inherits it:

- **`claude -p`: `--add-dir <path>` is per-spawn.** The flag grants access to a
  directory outside the working repo for that invocation only. Account profiles
  (`CLAUDE_CONFIG_DIR`) control auth/billing ONLY — they never widen file
  roots — so the flag must ride every executor/architect spawn that needs the
  root (`/execute-loop` derives the read-root list at preflight, re-derived each
  run, and carries the flags on the spawn invocation in loop step 1).
- **Persistent alternative, for interactive sessions only:**
  `.claude/settings.local.json` `permissions.additionalDirectories` — per-project
  and gitignored, so it never ships with the repo. A spawned `claude -p` role
  does not read that file (v46.3 — What a spawned `claude -p` role reads,
  below); its read roots ride `--add-dir`.
- **Read-only by default:** a confirmed read root is reference material — the
  spawn prompt states it must not be edited (a plan-scoped, user-confirmed
  cross-repo write is the only exception), and the orchestrator's
  filesystem-escape check extends to each external git root (`git status
  --short` before/after spawns — an added root is an accessible filesystem
  surface for the spawned role, so read-only intent is verified, never
  assumed); a non-git root has no escape-check surface — treat it as an
  explicit user-confirmed exception.
- **Native-subagent delegates** run inside the architect's session and inherit
  its roots and its permission context (the `execute-loop` skill's Grants rule:
  the architect's confirmed grant set is the delegate's too) — no separate flag.
- **Peers stay current-repo-only by default** — a peer reviews this repo's
  changes; extend a peer's roots only when a phase's review genuinely needs the
  reference repo.
- **Backend limits:** a Cursor subagent is workspace-bound (no equivalent
  flag); codex is confined to its sandbox roots.

### What a spawned `claude -p` role reads (v46.3)

From v46.3 the spawn wrapper starts every `claude -p` role with
`--setting-sources user,project` — on both tiers, on every spawn and every
resume, from a constant with no input — and the shipped example command lines
carry the same flag. The normative text — what the shield is, what it is not,
and the preflight lines — is `/execute-loop` → Preflight step 16. This section
holds the observations behind it.

Each item marked "probed" was read on 2026-11-11 with Claude Code 2.1.322 on
Linux (model haiku, the default profile) in a scratch repository: a main
checkout with a committed `.claude/settings.json` (one allow rule, a
`SessionStart` hook) and an untracked `.claude/settings.local.json` (an allow
rule, a deny rule, an `env` map that also set `LOOP_ROLE` to an empty value, a
`SessionStart` hook), and a sibling worktree with its own untracked local file.
Every run carried `--permission-mode acceptEdits` and a two-shape
`--allowedTools` list unless the item says otherwise, and was started from an
emptied environment (`env -i` with `HOME`, `PATH` and `LOOP_ROLE` set) — so the
items show what a role loads from a settings file, not what it inherits from
the process that starts it. Each item marked "docs"
was read in Claude Code's documentation and changelog on the same day, with
2.1.322 current, and was not probed.

- **F1 — the flag closes the leak** (probed 2026-11-11, 2.1.322). Without the
  flag, a role in the worktree ran the command that only the main checkout's
  local file allowed. With `--setting-sources user,project` that command was
  refused, in the worktree and in the main checkout. The `--allowedTools`
  shapes ran in every run.
- **F2 — the flag drops everything else in the local file too** (probed
  2026-11-11, 2.1.322). The local deny rule stopped applying: the denied command
  ran through its command-line allow. The local `env` map and the local hook
  stopped applying. Without the flag the local `env` map reached the role; what
  it did to a variable the process already held differed with how the role was
  started. In these probes — a role started directly from the emptied
  environment — the map replaced `LOOP_ROLE`: it read empty in the role's
  shell. The bounded runner refuses only on a non-empty `LOOP_ROLE`, so on that
  path one line in the file is enough to get past its refusal with no action by
  the role. Read again on 2026-11-11 at 2.1.322 through the v46.2 spawn wrapper
  (no flag) started from a composer's shell, the map added a key the process
  did not hold and left `LOOP_ROLE` as the wrapper gave it, with an empty local
  value and with a non-empty one; through the v46.3 wrapper the added key was
  absent. What separates the two readings was not isolated. Both agree on what
  the shield rests on: without the flag the local `env` map reaches the role,
  and with the flag it does not. The worktree's own local file is read without
  the flag and dropped with it.
- **F3 — the bypass tier** (probed 2026-11-11, 2.1.322). With
  `--dangerously-skip-permissions --setting-sources user,project` the local
  `env` map and the local hook did not apply.
- **F4 — resume** (probed 2026-11-11, 2.1.322). A session started without the
  flag, in which the local rule ran, and resumed with it was shielded: the local
  rule was refused, the command-line shape ran, `LOOP_ROLE` was intact, and the
  local hook did not run.
- **F5 — subagents** (probed 2026-11-11, 2.1.322). A general-purpose subagent
  started inside a shielded role was refused the local rule and ran the
  command-line shape. Without the flag the subagent ran the local rule.
- **F6 — a command-line deny beats a local allow** (probed 2026-11-11,
  2.1.322). `--disallowedTools` naming the local-allowed command refused it with
  no shield. The loop passes no such list today.
- **F7 — committed allow rules in an untrusted workspace** (probed 2026-11-11,
  2.1.322). Each run printed `Ignoring 1 permissions.allow entry from
  .claude/settings.json: this workspace has not been trusted`; the local file's
  allow rule was honoured without trust. The committed project hook ran in every
  run, with the flag or without it.
- **F8 — the flag's history** (docs, read 2026-11-11 at 2.1.322; not probed).
  The changelog has no "added" entry for `--setting-sources`; its earliest
  mention is 2.0.24. 2.1.211 moved the local file a worktree session reads to
  the main checkout's root. 2.1.314: "Fixed a settings file excluded with
  `--setting-sources` still supplying some settings". No environment variable
  equals the flag. `--settings` adds a layer and removes none. An unknown flag
  is reported on stderr before the run starts.
- **F9 — what the source list does not govern** (docs, read 2026-11-11 at
  2.1.322; not probed). The worktree rule does not apply on Windows: there the
  local file stays in the starting folder. Managed settings and `--settings`
  apply whatever the source list. In `claude -p`, project-scoped MCP servers
  load without the approval prompt. `CLAUDE.local.md` is skipped when `local`
  is excluded.

Standing limits (Preflight step 16 is their normative statement):

- The wrapper passes the flag; the exclusion is Claude Code's. It was probed
  complete for allow rules, deny rules, `env` and hooks at 2.1.322 only, and the
  changelog names a fix at 2.1.314 — below that version an excluded file may
  still supply some settings, and preflight prints one line saying so.
- The profile's user settings, the checkout's committed `.claude/settings.json`
  and managed settings still reach a role. A composer-only rule placed in any
  of them reaches every role.
- On a run that grants a broad interpreter shape such as `Bash(python3:*)`, or
  runs `perms=bypass`, no grant boundary exists for the bounded runner or the
  full records helper, with the shield or without it.
- A Claude Code session started by hand in the checkout or a worktree, and a
  loop older than v46.3, still read the local file. A Cursor-subagent executor
  and a live-session leg run in the composer's own session and read what it
  reads; a `codex` role reads no Claude Code settings.
- Deny rules, ask rules, `env` values, hooks and extra read folders that live
  only in the local file are no longer loaded by a role. Preflight step 16 names
  them at every run; what a role must keep moves to the committed project file
  or the profile's settings.
- The flag governs what a role loads, not what it inherits. The wrapper passes
  its whole environment to the role, so a variable the spawning session already
  holds — one a Claude Code composer's own session took from the local file's
  `env` map included — still reaches the role that way. Nor does the flag hide
  the file: a role can open a local settings file as a file wherever its tools
  and grants reach it, so a secret written there is not kept from a role.

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
  and never backgrounded by the composer with a raw `&`, `nohup` or disown —
  with the output watch configured AT SPAWN on the
  full Tier-1 anchor set (every `ROLE:` / `DELEGATION:` line plus the
  limit/error strings, not just the handoff sentinel). The shell's completion
  notification wakes the composer the moment the role exits: handoff, crash,
  and limit-death detected in seconds, for free. (v48.0) What that shell holds
  is the spawn wrapper's TAIL. On a POSIX host with survival on, the wrapper
  itself forks twice — `os.fork` and `os.setsid()`, never `nohup` or the
  `setsid` binary — and the grandchild, the leg's supervisor, is in a new
  session and, where `<leg>.live` says `survive=on`, outside the composer's
  process tree. The launched process stays in the shell,
  mirrors the leg's output, and exits with the leg's code once the leg has
  ended. So the completion notification is still
  the exit wake, except for two codes of the tail's own, each beside one
  stdout line: 5 with `SPAWN_DETACHED supervisor_pid=<n>` (a TERM, HUP or INT
  ended the tail alone — a role that was running runs on) and 6 with
  `SPAWN_LOST supervisor_pid=<n> …` (the supervisor is gone and wrote no
  `<leg>.exit`). Neither is the role's exit; the leg's state is then read from
  its files. Under the split, ending that shell is therefore not a way to
  stop a role — a signal that reaches only the tail leaves the role running —
  and the stop is a TERM to the `wrapper_pid` its `<leg>.live` records
  (Roles that outlive the composer, below). **The anti-pattern: a spawn
  wrapper exiting 0 is not a watched executor** — if the wrapper detaches the
  PID and returns, the composer has nothing to watch and nothing to be woken
  by (the v48.0 split is not that shape: the launched process returns only
  when the leg has ended, the supervisor is lost, or a signal ends it).
  Host-conditional: a headless composer dies at turn end — it foreground-waits
  the spawn or uses the sleep-sentinel fallback; peers are always
  foreground-and-waited regardless (the loop's foregrounded-peer rule is
  unchanged).
- **Layer 2 — the monitor subagent (default-on for CLI executor backends on
  hosts with background subagents).** At spawn the composer also arms a
  background monitor subagent with an explicit contract: executor
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
  cover when the native watch fails. (v48.0) A role that outlives the shell
  that launched it is no longer an exception with a rule of its own: on a
  POSIX host with survival on, every wrapper spawn is built that way. While
  the tail's shell lives, both layers are armed as the `Wake:` line resolved
  them. A role whose shell is gone — a tail ended with code 5, a composer
  restarted — has no Layer-1 surface: a returning composer finds it by its
  `<leg>.live` file and re-arms a watch under the Resume contract, which is
  then a Layer-2 watch, and where none can be armed the rule under Return
  handling below applies (foreground-waited or MUST-PAUSEd, never dark).
  **Two implementation shapes, one slot (v29.2):** `layer2=monitor`
  is the abstraction, not one implementation — a PERSISTENT harness-native
  watch tool fills the same slot: it emits per-event notifications instead of
  returning, needs NO re-arm PER EVENT (its single spawn-time `WATCH: armed`
  line plus the continuing notifications ARE the arm/liveness proof), writes
  the SAME `MONITOR:` snapshot grammar per event — and it does not end at an
  event by itself, so the exit-branch teardown (below) is mandatory for it.
  Its arm is not unbounded in time (v48.0): where read, a Monitor arm ended
  at 10 minutes, and that expiry notice is a wake on which a live role's
  watch is armed again. Either implementation
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
  so a bare limit-string match wakes on healthy traffic. From v33.4 the spawn
  wrapper moves that allowed-status discrimination into its stdout mirror — an
  `allowed` / `allowed_warning` event is rewritten there to a non-anchor
  `USAGE_TICK …` line while the role log keeps it byte-verbatim — but the
  composer-side status rule stays MANDATORY (an older wrapper still mirrors
  those events, a monitor tailing the role log still sees every one, and a
  healthy `allowed` event routinely carries `"overageStatus":"rejected"` too,
  so a bare `rejected` match is never the limit test). Text anchors
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
  Wake: run=<runkey> layer1=<bg-shell|subagent-harness|fg-wait|native> layer2=<monitor|sentinel|none> [interval=<minutes>m] [delivery=<fg|bg>] [reason="<required when layer2=none>"]
  WATCH: armed ts=<iso> run=<runkey> role=<executor|architect|delegate|peer|advisor> layer1=<...> layer2=<...> [delivery=<fg|bg>] [reason="<required for layer2=none and for any mechanism-change line>"]
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
  would have written the claim), while the persistent watch needs NO re-arm
  per event — its single spawn-time `WATCH: armed` line plus its continuing
  notifications ARE the arm/liveness proof (the two-shape clause above, which
  also says what its arm's expiry is, from v48.0).
  Return handling is ATOMIC and CONDITIONAL: a non-exit return is not fully
  processed until the update is posted AND the next watch is armed in the same
  handling turn; an exit return is VERIFIED with its required `CONSUME:`
  verdict recorded, and the leg's `ROLE: end` is written once, by the leg's
  one writer. (v48.0) For a leg started through the spawn wrapper that writer
  is the WRAPPER: whenever it wrote the leg's `ROLE: start` it emits the
  `ROLE: end` through the helper when the role exits, before its `EXIT:`
  footer — so the composer verifies, writes the `CONSUME:` verdict, which
  carries all of its judgment, and writes no end (with `--log` the helper
  refuses a second end for a closed leg). The composer writes such a leg's
  end in ONE case, the clean close: the leg has a start and no end, and the
  helper admits the end only once the role-liveness reader says `over` for
  the leg (Roles that outlive the composer, below). A launcher leg, v34.1 — a
  composer-seat codex peer round through the shipped peer launcher — has the
  same order: the launcher has already written the end when its
  shell exits, so the composer verifies, writes the `CONSUME:` verdict
  carrying that `leg=`, and writes no second end — canonical:
  `/execute-loop` → Visibility + run-state → the `ROLE:` definition →
  Launcher legs. Only an activation whose records are hand-written — neither
  the wrapper nor the launcher started it — keeps the reconciled v32.5
  order: the `CONSUME:` verdict, then the role's `ROLE: end` first among the
  closure records. In every case the exit branch then runs the
  terminal classification, does NOT re-arm (the role is closed — never a
  watch on a dead PID), and CANCELS every still-armed wake mechanism for that
  role that did not self-terminate with the exit return (v29.2) — an
  armed-but-unreturned monitor when Layer 1 fired first, a pending sentinel
  timer, and a persistent harness watch tool alike: a mechanism outliving its
  closed role emits false events against the frozen log (observed live
  2026-07-10: two post-exit false stalls); a live role with NO Layer-2
  mechanism and NO Layer-1 surface is foreground-waited or MUST-PAUSEd — it
  never continues dark.
  **Delivery (v32.2).** Both lines MAY carry the optional `delivery=<fg|bg>`
  key — the preflight-resolved Layer-2 DELIVERY mode, resolved at step 10 from
  the persisted `monitor-delivery=fg|auto` `Loop config:` key (absence or a
  malformed value = `auto`, fail-closed; the artifacts carry only the RESOLVED
  value, never `auto`): `bg` = host-ordinary background return delivery; `fg` =
  the composer consumes the resolved Layer-2 watch foreground-synchronously
  over the existing chunked-poll contract — bounded polls of up to
  min(liveness interval, ~10 min) re-entered until the return (~10 min flat
  under liveness OFF — the composer-seat bound, v32.5; the monitor child
  foreground-polled, the sentinel shell
  foreground-awaited), each return consumed AND the next watch armed in the
  same handling turn, scoped to delivery-fg Layer-2 consumes only (background
  executor watches untouched). Drift policing rides a MONOTONIC delivery
  epoch: before a file's first delivery-bearing `Wake:`, key absence is legal
  everywhere and key presence on a `WATCH: armed` is a no-authority violation;
  after it, every Layer-2-consume `Wake:` carries resolved delivery (omission
  never resets the epoch), a post-epoch `layer2=none` `Wake:` is a NO-ARM
  state, every comparable `WATCH: armed` carries an agreeing value, and
  `reason=` never excuses delivery absence or mismatch — a legitimate delivery
  change lands as a NEW step-10 `Wake:` before the next arm. A `layer2=none`
  line never carries the key.
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
  and re-arm with a dark-window log check (v48.0, by who wrote the leg's
  start: a wrapper-spawned role that is still running is found by its
  `<leg>.live` file and gets its watch re-armed, not a respawn; an exited
  wrapper-spawned leg already has the end its wrapper wrote and gets its
  `CONSUME:`, never a second end; one with a start and no end gets a
  composer-written end only in the clean close — the helper admits it once
  the role-liveness reader says `over`, and for a leg that reads `unknown`
  only when `result=` names the operator's attestation by the word
  `owner-dead`; a launcher leg already has the end its launcher wrote and
  gets its leg-bound `CONSUME:` instead, never a second end; an exited
  activation whose records are hand-written gets `ROLE: end` written FIRST,
  as before); then resume from what the plan and logs prove. The
  `[<runkey>]` breadcrumb prefix on composer-posted status lines is the
  chat-side anchor back into the run. Canonical definition: `/execute-loop` →
  Visibility + run-state → Resume contract.

### Roles that outlive the composer: survival, the seat, the watcher (v48.0)

From v48.0 the spawn wrapper runs each role under a supervisor it means to
place outside the composer's process tree, and a watcher the operator starts
can notify about a run whose composer is gone and, under an away grant,
continue it. Roles are built to outlive a TERM, a quit and a kill of the
composer's process, and an app quit was not read (the last bullet). The
normative text is the `execute-loop` skill pair and `/close-run`; the code-side
contracts are the header docstrings of `scripts/loop-spawn-wrapper.py` (its
v48.0 item) and `scripts/loop-watchdog.py` and, in `scripts/loop-journal.py`,
`run_legs`, `leg_end_refusal`, `seat_admit` and `signal_authority`. This
section is the map, and the observations behind it.

- **Survival — the split wrapper.** On a host with `os.fork` (POSIX), unless
  `LOOP_SURVIVE=off`, the launching process claims `<leg>.live` and forks
  twice. The first child calls `os.setsid()`, forks again and leaves at once;
  the launching process reaps it. The grandchild is the SUPERVISOR — the
  wrapper as it was through v47.0, in that new session, its stdin the null
  device, its stdout and stderr appended to `<leg>.out` and `<leg>.err` — and
  every pid the wrapper records (`wrapper_pid` in the identity record, in the
  lock's holder line and in `<leg>.live`) is the supervisor's. The launching
  process becomes the TAIL: it only forwards those two files to its own stdout
  and stderr, and exits with the code `<leg>.exit` records. Neither `nohup`
  nor the `setsid` binary is used. `LOOP_SURVIVE=off` restores the single
  process (unset is on; any other value is a `params` refusal); a host
  without `os.fork` — Windows — always runs one process; a host that refuses
  the first fork runs one process and prints `SPAWN_WARN check=survive`.
- **`survive=` in the leg file says how far that went.** The double fork gives
  the supervisor a new parent — whichever process adopts orphans there — and
  that is outside the composer's tree only where the adopter is above the
  composer. Before it records itself or starts a role, the supervisor reads
  its own ancestors and compares them with the composer's pid (`CLAUDE_PID`
  from the inherited environment). `survive=on`: the composer is not among
  them — the only value that means survival is established. `survive=in-tree`:
  it still is; the leg runs, prints one `SPAWN_WARN check=survive` line, and
  will not outlive the composer's process tree. `survive=unverified`: it
  cannot be told — no `CLAUDE_PID` (any composer that is not Claude Code), one
  that is not an ancestor of the launching process, or a chain that could not
  be read; the split was taken and nothing more is claimed. `survive=off`: the
  single process.
- **The per-leg files** sit beside the probe log, in both modes and on every
  host (`<leg>.out` and `<leg>.err` under the split only). `<leg>.live` is
  claimed first, before the validation's first side effect — `ts run role leg
  wrapper_pid wrapper_start survive`, then `role_pid role_start role_pgid` once
  the role is launched — and no role is started without it. As the wrapper's
  last act, on every path it returns by, it becomes `<leg>.exit`, which adds
  `launched=no|yes|unknown exit=<code> exit_ts= census=`. A leg value used
  twice gets `<leg>.2.live` and so on; a reader goes by the `leg=` line
  inside. A wrapper that does not return — killed outright, or ended by a
  signal before START — leaves `<leg>.live` as it stood. `.exit` says the
  wrapper finished; it does not say the role's work has stopped.
- **The tail's two codes.** A TERM, HUP or INT to the launched process ends
  the tail alone: exit 5 and one line `SPAWN_DETACHED supervisor_pid=<n>`; a
  role that is running runs on. A supervisor that is gone with no `<leg>.exit`
  — or one that never recorded itself inside the tail's 30-second bound —
  gives exit 6 and one line `SPAWN_LOST supervisor_pid=<n> detail="…"` (in
  both lines `<n>` reads `unknown` where no supervisor's pid is known; a
  supervisor that could not be forked is the one loss that leaves an `.exit`
  — the tail writes `launched=no exit=6` itself).
  129 / 130 / 143 keep their meaning (a HUP / INT / TERM the supervisor
  forwarded to the role), and a role that itself exits 5 or 6 is told apart
  only by the line's absence. Stopping a role is a TERM to the `wrapper_pid`
  in its `<leg>.live` — exit 143, with the end and the footer written — sent
  by hand only while that `.live` stands with no `.exit` beside it and the
  pid is alive. Those conditions are necessary, not proof: a wrapper killed
  outright can leave a `.live` whose pid number is another process's now, and
  where that cannot be excluded NOTHING is sent to the pid by hand — the
  full rule is the skill's (`/execute-loop` → Visibility + run-state → the
  Stall watchdog bullet → Stopping a wrapper leg). The stop command below
  sends it for every leg of a run that is not over, and compares the recorded
  start token before each signal.
- **The leg's end.** Whenever the wrapper wrote the leg's `ROLE: start` it
  writes the leg's `ROLE: end` — through the helper, with `--log`, before the
  `EXIT:` footer, which stays the log's last line — on a normal exit and on a
  forwarded-signal one. Its `result=` is mechanical: `exit <code>; handoff`
  when the footer's code is 0 and the last result event of the leg's stream
  ends in a `ROLE: handoff ` line, else `incomplete: exit <code>; handoff` or
  `incomplete: exit <code>; no handoff`; `duration=` is whole seconds since
  the start was written. A post-START exit that never wrote the start writes
  no end; a wrapper killed before its teardown writes neither the end nor the
  footer; one stopped between the two, or whose footer append failed, leaves
  the end with no footer — they are separate appends, the end first, so the
  absence of one never shows the absence of the other, and a leg's end is
  read from the log itself; a helper refusal of the end prints `SPAWN_WARN
  check=role-end` and leaves the exit code as it was. The composer's judgment is its `CONSUME:` record. The
  clean close is a helper check, not only text: `emit ROLE:end --log`, for a
  leg whose log folder holds leg evidence, admits the leg's own wrapper (the
  caller's parent process is the recorded `wrapper_pid`) and otherwise only a
  leg whose every file reads `over`; `live` refuses; `unknown` refuses unless
  `result=` names the operator's attestation by the word `owner-dead`. It is
  a mis-attribution guard, not caller authentication.
- **The role-liveness reader** (`run_legs`) gives each leg one of three words,
  from its `.exit` file, else its `.live` file, else — a leg from before
  v48.0 — its identity record. `live`: the wrapper runs under its recorded
  start token, or the recorded role does, or a process remains in the role's
  group. `over`: `.exit` records that no role was launched, or the role is
  dead and its group is empty (and, without an `.exit`, the wrapper is dead
  too). `unknown`: everything else — a wrapper that died before it recorded a
  role, a pid whose start token cannot be compared, a group that could not be
  tested, a file that cannot be read; a dead wrapper alone is never `over`.
  On a Windows host a launched leg's `.exit` reads `over` and a leg in flight
  reads `unknown`. Four callers: the watcher's verdict; `stop`; the close's
  live-role guard (a `run-close` cell that tears down refuses a `live` leg
  whatever was attested, and an `unknown` one unless `--attest owner-dead` —
  and, as an `unknown` one, a journal whose `log_root=` is there and cannot
  be used: the folder the run's legs are in is then not established);
  and the clean close above. The watcher's verdict, `stop` and the close's
  guard read a journal's `log_root=` by ONE rule: a key that is absent is the
  default folder `<base>/.cursor/loops/<iso>`; a key that is there names the
  folder when its value is a usable absolute path — whether or not anything
  is there — and otherwise (empty, unsafe, not an absolute path) establishes
  no folder at all, never the default. Its reach: it reads wrapper legs — a launcher
  leg, a Cursor-subagent role and a hand-route activation write no per-leg
  file and are seen by none of the four — and `over` is positive for the
  recorded role process and its own process group; a descendant that left
  that group for a session of its own is not seen. Liveness is not authority to signal: a number
  read from a file is signalled only when that file records its process's
  start token and the process still runs under it (`signal_authority`) — a
  group only while its LEADER does.
- **The composer identity record and the seat.** Five files beside the run's
  journal, in `<base>/.cursor/loops/`:
  - `<iso>-composer` — the identity record (`session pid pid_start entrypoint
    exec config_dir cwd host nudge ts`), written by `python3
    scripts/loop-watchdog.py identity --base <base> --iso <iso>` from the
    session's own environment. A host that exposes no session id, or no
    process id for the session, writes `host=unknown`, and no takeover is
    offered for it.
  - `<iso>-seat` — a takeover holds an exclusive lock on it for its whole
    life: taken by the watcher, inherited by the takeover's process, released
    by the kernel when that process ends. Its bytes name the holder (`nonce=`,
    `ts=`, `watcher_pid=`, then `pgid=` with `stage_start=`) and stay there
    between takeovers, so only the lock says the seat is held.
  - `<iso>-seat.gate` — a short lock that serialises every protected write
    and the watcher's acquisition.
  - `<iso>-notakeover` — the operator's durable no-takeover mark: `stop`
    writes it, and only an interactive composer's `identity` write — one made
    without `LOOP_SEAT` — clears it.
  - `<iso>-takeovers` — the run's takeover ledger (the stall in progress, its
    attempts and steps, the day's attempt times). An acting tick creates it
    for a stalled run, so the limits are the run's, whichever watcher counts.

  `identity` creates the seat and gate files when they are missing and never
  removes either — and creates none for a run with no journal (a run with no
  run worktree) or with one that does not establish its log folder — it
  cannot be read, it says nothing (an empty file, one cut short ahead of its
  `state=`), or its `log_root=` is there and cannot be used (empty, unsafe,
  not an absolute path); the run listing reads all three `unreadable`:
  `seat=none(log-root)`. No
  script retires the five at a close (the one file a script ever removes is
  the mark, which an interactive `identity` write lifts): the helper's close
  leaves them, and `/close-run` retires them itself after a verified close —
  the seat file before its gate, and only when the `seat` read says `free` or
  `none`.
- **What the seat protects, and what it does not.** It protects the run's
  records and release acts: every helper write made on the composer's behalf
  — `emit` under `--role composer` with `--log`, `idle-check`, `flush` (not
  its dry run), `away grant | end | ci-verdict`, `run-close`,
  `fold-delegation` — and `loop-watchdog.py identity`. Under the gate, a write
  is admitted on a free seat when its caller carries no `LOOP_SEAT`, and on a
  held seat only when the caller's `LOOP_SEAT` equals the recorded nonce; a
  caller that carries `LOOP_SEAT` is admitted only as the holder, and while
  the no-takeover mark stands a holder's writes are refused too. A refusal
  carries its class word in parentheses: `seat-held`, `seat-not-holder`,
  `seat-unknown` (the seat file could not be opened or tested),
  `seat-gate-busy` (the gate was not free within 30 seconds),
  `seat-gate-missing` (a seat file with no gate beside it). Never gated: the
  records a role's wrapper or the peer launcher writes, every `escape-check`,
  a role's own `VERIFY_OK` and `ROLE:round`, every read-only subcommand, and
  a composer-flagged `emit` with no `--log` (it prints to stdout and the
  helper writes nothing). `LOOP_SEAT` is the takeover's nonce, in its own
  environment: the wrapper removes it from the role's environment, it never
  reaches the launcher's peer, and both close every descriptor above 2 they
  inherited, so neither the nonce nor the lock crosses a role boundary. The
  seat does not protect file edits or the transcript. It is a
  mis-attribution guard, never caller authentication, and record-then-act is
  what turns a refused record into a stopped act. There is no seat, and so no
  takeover, on a Windows host, on a filesystem that takes no file locks, for
  a run whose journal names a `log_root=` other than
  `<base>/.cursor/loops/<iso>`, and for a run with no journal (a run with no
  run worktree) or with one that does not establish its log folder (it
  cannot be read, says nothing, or carries a `log_root=` that cannot be
  used); a run with no `<iso>-seat` file is admitted as before v48.0.
- **The watcher** is started by the operator outside any agent session — a
  user service or a terminal: `python3 scripts/loop-watchdog.py watch --base
  <repo> [--base …] --profile-dir <dir> [--profile-dir …] [--exec <file> …]`.
  It sleeps and, each round (60 seconds by default), runs
  `<base>/scripts/loop-watchdog.py tick --base <base> --act` as a child for
  each base, so every repository is judged by its own installed helper; it
  writes a `heartbeat` file in its own state folder, from which `identity`
  prints one `watcher:` line. `tick` without `--act` is read-only: it prints
  each run's verdict and writes nothing. `watch` and `tick --act` refuse
  inside an agent session, and every subcommand refuses when `LOOP_ROLE` is
  set (exit 2 — accident guards, not boundaries). The verdict per live run,
  first match wins: `closed`, `unreadable`, `parked`, `release-in-flight`,
  `leg-running` (`leg-quiet` once no file under the log folder has been
  written for 45 minutes), `leg-unknown`, `progressing` (advancement inside
  the stall window, 15 minutes by default — or, while the composer's process
  is alive, activity inside the window and advancement within the last three
  nudge intervals, 30 minutes each by default; or, while the composer's
  process is alive, a leg that ended inside the stall window — its `ROLE:
  end` record — which the composer is about to consume), `stalled`
  (everything else).
- **Notify always; take over only under an away grant, under limits.** All
  of it with `--act` only. `unreadable`, `leg-quiet` and `leg-unknown` get
  one notice each and never a
  takeover. `stalled` gets one urgent notice per stall naming the run and the
  stop command, at the stall's start and again 5, 15, then 45 minutes after
  the notice before — four at most, and not a promise of four: while a
  takeover waits its own back-off a notice that falls due is held and sent
  with the next attempt, and once a takeover limit is reached the give-up
  notice is sent and no stall notice follows it. That schedule is the
  notice's own, and a notice's number says nothing of how many takeovers
  were tried or when the next one is: a notice spends no takeover, so a
  takeover that becomes possible later in the same stall (the composer's
  process dies) starts at the next tick, whatever notices went before, and
  may start with no notice beside it; and an acquisition that started
  nothing spends no step. A takeover is
  started only when ALL of these hold: the composer's recorded process is
  gone (alive, or not provably gone, is never enough); the run's away grant
  is bound; the grant's departure file digests to the grant's `departure=`,
  holds at least one `Watcher takeover:` line, and every such line says `on`
  (no line at all reads as off); the identity passes its
  checks (a UUID session, a known host, a `cwd` that is the base or a live
  run's worktree, a `config_dir` on the `--profile-dir` list that holds the
  transcript, an executable on the `--exec` list or, with no `--exec` given,
  `claude` on the watcher's PATH); the seat is free and the no-takeover mark absent; and the limits
  allow — three takeovers per stall, the next step 5, 15, then 45 minutes
  after the one before ended, six per run per 24 hours, then one urgent
  notice and no further attempt. Otherwise the run's line says which did not
  hold (`why=<word>`) and the notice is all that happens. The takeover is one
  child, `<exec> -p --resume <session>` with one fixed prompt, in the
  identity's directory and on its config folder, with `LOOP_SEAT=<its
  nonce>`; the rest of its environment is the watcher's own, less every
  `LOOP_*` and session variable, so start the watcher from the environment
  the composer's sessions are started from. Its command line never carries a
  permission-bypass flag, and under `LOOP_SEAT` the helper refuses an away
  production start (`takeover-production-start`): a takeover never starts a
  production act. Its wall-clock bound, 240 minutes by default, ends the
  takeover's own process and nothing else.
- **The stop command.** `python3 scripts/loop-watchdog.py stop --iso <iso>
  [--base <base>] [--takeover-only]` writes the no-takeover mark; while the
  seat is held, signals the group the seat file publishes — TERM, then KILL
  (the group's leader, the takeover's stage, outlives the TERM for as long as
  its takeover lives — it passes the signal on and waits — so the group still
  proves itself for the KILL) —
  and waits, bounded, for the seat to come free; and, unless
  `--takeover-only` (which leaves the roles running), sends a TERM to the
  wrapper and to the role's group of every leg the reader does not call
  `over`. Each number is signalled only on its own evidence
  (`signal_authority`, above). It exits 0 only when the seat is free and —
  without `--takeover-only`, which does not read the legs — every leg reads
  `over`; anything else is a `stop: NOT COMPLETE — …` line with the pids, and
  exit 3. The legs are read from the folder the run's journal establishes
  (`<base>/.cursor/loops/<iso>`, or its `log_root=`): a run with no journal —
  a run with no run worktree, whose leg files are in the flat loops root,
  where a leg's file cannot be tied to one run — has none, so there `stop`
  reads no leg, signals nothing, says so on one `NOT COMPLETE` line and exits
  3; where the journal does not establish that folder — it cannot be read,
  it says nothing (an empty file, one cut short), or its `log_root=` is there
  and cannot be used (empty, unsafe, not an absolute path) — it reads the
  default folder, stops what proves itself there, and still exits 3 with a
  line saying the folder is not established. Without `--base` it reads the checkout the script sits in: from a
  run worktree's copy that is a refusal (`no run … pass --base`), so name the
  base. It ends no grant and signals no interactive composer: a composer
  session that is still open wakes on its stopped role's exit and honours the
  stop by a rule of its own — before every spawn and every resume it reads
  the `seat` line, and on `mark=yes` it resumes and spawns
  nothing, writes the must-pause pair under `<runkey>-operator-stop`, and
  waits for the operator's word. At a Resume that read comes BEFORE the
  identity write, and on `mark=yes` no identity is written until the
  operator's word — the write would lift the mark before the pause is on
  the log; an `identity:` line that still reads `mark=cleared` or
  `mark=clear-failed` (a mark written between the read and the write) is
  honoured the same way. That is skill text, not a check: no script
  refuses a spawn while the mark stands. What `stop` does NOT do besides: it
  does not end a
  role's orphaned group. A group whose leader is gone while a process remains
  in it still reads `live` — a takeover and a close stay refused beside it —
  but nothing recorded ties that group to the run, so `stop` names it,
  signals nothing, and exits 3; looking at that group and ending it is the
  operator's. The proof is per target, never per leg: on a leg whose word is
  `unknown` a wrapper or a group that proves itself may still be signalled,
  and one that does not is left alone. On a Windows host no start token can
  be read, so no target proves itself — a leg in flight reads `unknown` there
  — and by the code's reading `stop` writes the mark and reports (not run
  there).
- **What was read, and what was not** (2026-11-15; Linux, Claude Code 2.1.321
  to 2.1.325; the readings are the dated T5.1–T5.4 lines of
  `plan-loop-autonomy-group-2.md`). Read:
  - The session's `claude` process signals every process in its task's tree
    on a TERM, a HUP or a deliberate quit, whatever session, process group or
    cgroup the process is in — read as a TERM on a terminal `claude` and on a
    stand-in for a desktop session (the app's bundled binary, without the
    app's control protocol), as a deliberate quit ("Exit and stop tasks"),
    and as a TERM and a HUP on a `claude -p` composer. A plain child, a fork
    with `os.setsid()` and a live parent, and a `systemd-run --user --scope`
    marker were all ended.
  - A supervisor that has left the tree by a double fork survives those, and
    a KILL: the double-fork marker, and an emulation under the `claude -p`
    composer whose supervisor had left the composer's tree. On a KILL every
    shape survived. Under the `claude -p` composer each surviving leg was
    left unconsumed, for a later composer.
  - A recurring session timer stays listed after a turn that failed with an
    HTTP 403 (a local proxy answering it), and its next firing ran a full
    turn once the proxy forwarded again — on a terminal session, measured
    twice.
  - A headless `claude -p --resume <id>` continues a desktop-created session,
    with `--fork-session` and, on a byte copy, without. Without a bypass mode
    a tool call that would prompt is refused and an allowed shape runs; a
    descriptor the session inherits stays with the `claude` process and does
    not reach its tool shells.

  Not read: an app quit and an app crash; any host but Linux on Claude Code
  2.1.321 to 2.1.325; the timer on a desktop-app session; the re-attach case
  (the session id and the pid after the app re-attaches a session whose
  process died, and whether `SessionStart` fires with `resume`). And not
  exercised when this section was written: the BUILT wrapper under a real
  composer's death — the readings above are of markers and of an emulation,
  and the built split has run under its selftest only, on Linux — a real
  `claude` as the takeover, and the watcher on macOS or Windows.

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
  `autocommit=on`; conflicts always stop; never a push — the ONE carve-out is
  `/close-run`, stated in the skill's Run-isolation section). A dry-run prints the
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
  crash; from v33.2 `retained-green` — or `merged` after a refused teardown, or
  `active` under `--attest owner-dead` — reaches `merged → cleaned` through the
  helper's squash-aware `run-close --outcome merged --merge-commit <sha>` entry
  into the verified-merge cell, the `/close-run` path; from v40.0 a non-final
  release group's merge keeps `active` and appends `merged_stage_<N>=` then
  `ff_stage_<N>=` through `run-close --outcome group-merged` — the
  `group-merge` and `group-ff` cells, no teardown — and a tagged plan's
  journal carries the creation-time `groups=` key beside `phases=`)
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
  (`retained-green`) and the handoff stating the continuation — from v33.2 that
  continuation is `/close-run`: the condensed close transition is
  `retained-green | merged (re-entry) | active (attested) → merged → cleaned`,
  verified by the helper against the FETCHED remote base — the local ref only
  where no remote ref exists — (the tip an ancestor of it — the fast path — else `git merge-tree --write-tree <sha>^1 <tip>` equal to
  `<sha>^{tree}`; plain tree equality below git 2.38; fail closed otherwise),
  `merged="<ts> <sha>"` written first, then the existing verified-merge teardown
  with `branch -D` on every `--merge-commit` close (`-d` stays on the flag-less
  legacy ancestry path only); a non-final release group's merge (v40.0 — the
  group close inside a live run, `/close-run --group stage-<N>`) → the
  helper's `run-close --run stage-<N> --outcome group-merged --merge-commit
  <sha>`: the journal stays `active` → `active`, `merged_stage_<N>="<ts> <sha>
  <tag>"` appended after the merge-parent binding (the sha in the fetched base,
  on the base branch's first-parent chain, two parents, `<sha>^2` the run tip),
  then `ff_stage_<N>="<ts> <sha>"` once both the base checkout and the worktree
  are fast-forwarded to the one fetched sha of `origin/<base-branch>` — the
  `group-merge` and `group-ff` records, no teardown, the run continuing into
  the next group (under a bound away grant the call carries `--grant <n>
  --away-check <h>` and the `group-ff` leg writes a `rebaselined` record into
  the stage probe log before `ff_stage_<N>`, its replay repairing a missing
  record — `/execute-loop` → Run isolation → Mechanical close enforcement →
  The re-baseline, v44.0);
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
  mislabeled `crashed/recovery-needed`); cleanup is idempotent; never a push (the
  ONE carve-out is `/close-run`, after its confirm table or, from v34.0, on a bound
  away grant — the skill's Run-isolation section).
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

## v33.0 composer-seat autonomy — condensed forms (loop-autonomy + hygiene release)

Condensed reference for the v33.0 contracts; the canonical text is the `execute-loop`
skill pair (`SKILL.md` → Safety gates / Termination / The per-phase loop; `STICKY.md`
§4/§6/§7). Every value here is helper-validated (`scripts/loop-journal.py`) and
oracle-admitted — nothing in this section is a new line-start, enum value, class, or
state; the v33.0 delta is additive keys plus a widened attestation key.

**Gate modes (D1).** `gates=strict|fix-biased|executor`, wizard default `executor`
(absent/malformed → `strict`); `cap-raise=ask|auto-plus-one|follow|executor`, wizard
default `executor` (absent → `ask`); `high-auto=on|off`, wizard default `on` (absent →
`off`). `gates=executor` requires `high-auto=on` — the wizard writes both; an explicit
`executor` beside `off` is a preflight `config-conflict` must-pause (emitted as the
must-pause pair with `key=config-conflict`; the helper binds every must-pause owner to
`class=must-pause`). Under `executor` the composer follows the executor-verified
recommendation act-and-inform for MED-and-below Fix-now/Accept/Defer/Include-in-plan,
docs-only/invalid below CRIT, and HIGH Fix-now (with the `high-auto` attestation pair);
the residual MUST-PAUSE list is stated ONCE, in the SKILL's composer-seat policy bullet
— never restated here. Attestation: executor mode adds a second run-start
`config-snapshot key=gates value=executor` record (per-key hash
`iso|plan|epoch|gates=<value>`, FIRST-wins per key, its own `config-revoke key=gates`
stream); legacy modes write none. The read is
`python3 scripts/loop-journal.py attest-check --run <runkey> --role composer --policy-log <abs> --iso <iso> --plan <plan> --key gates`
(exit 0 = bound + unrevoked; exit 3 names `absent | malformed | wrong-identity |
off-at-start | revoked`). The operator's "autonomy on|off" is a MID-RUN-CHANGE mode
selection bounded by that run-start authority — never a revoke, and "on" is legal only
for a run that started in executor mode.

**Cap verdict + budget (D2/D3).** Under `cap-raise=executor` every LEG-1 verify brief
ends with `Cap verdict: raise <+n> | accept | defer-residue — <production-behavioral |
test-harness | docs-only> — <evidence>`; at cap the composer runs `follow`'s pinned
total order with the verdict as the recommendation input and the tail signature
DECIDED by the verdict (accept ⇒ `cap-accept=close`). One `cap-raise=+1` record per cap
event (`+1` stays the only raise token) within a +3 per-pass budget; then `peer-max`
(default 12) surfaces once per pass. `defer-residue` ⇒ `cap-accept=close … residue=deferred`.
The v32.3 pre-cap early tail accept-close is NOT evaluated under `executor` (neither
closes nor surfaces — its predicate is `fix-biased`+`follow` only); a mid-pass tail
signature continues to the next round and the verdict decides at cap.
The cap is per PASS: every orchestrated peer `ROLE: start role=peer` carries
`pass=<slice>.p<N> peer_round=<k> cap=<N>` (all three or none — wrapper
`LOOP_PASS`/`LOOP_PEER_ROUND`/`LOOP_CAP`, validated through `--read-log`; from v34.1
composer-seat codex peers through the same three variables on the peer launcher, below;
hand-route codex peers via `emit ROLE:start … --log`), sequenced by the helper against the prior log
(`peer_round ≤ cap`, consecutive rounds with the inconclusive-retry exception, `cap=`
bound to the seed plus recorded same-pass transitions; a pass with no prior keyed
start grandfathers its seed). Cap transitions carry the `pass=`+`cap=` bundle (both or
neither) and need `--log` when keyed. A raise never rewrites `Loop config:`'s `caps=`.

**Escape verdict + attribution (D4).** `escape-check` gains `--edit-surface <root>`
(wrapper `LOOP_EDIT_SURFACE` — `worktree` for executor/architect/delegate; peers none),
`--allow-path <root>:<path>` (wrapper `LOOP_ALLOW_PATH`, `;`-joined — quote it in a shell, `;` is a command
separator — a peer's plan file + `findings-*.md` sidecar, filtered from the digest), `--iso <this run>` (`LOOP_ISO`) and
`--liveness <min>|off` (`LOOP_LIVENESS`). `result=clean|dirty` is computed over the
non-edit-surface roots; the record reports `edit_surface=<root>:<changed|unchanged>`
and, on a base/external-only `dirty`, the advisory `attributed=<foreign iso>
attributed_age=<min>` when a LIVE concurrent run's `-active` marker claims the changed
checkout (no `.complete-*` sibling, `checkout=` realpath-equal, newest genuine
`stage-*-probe.log` within 2× liveness; liveness off ⇒ never attributed). Composer rule:
unattributed `dirty` ⇒ MUST-PAUSE in every mode; attributed `dirty` ⇒ under
`gates=executor` auto-proceed act-and-inform (`OWNERSHIP: auto-disposition …
key=escape-attributed-<leg>`), otherwise surface with the attribution. Pre-state is the
5-field `name|path|digest|edit-flag|allow-list` file (legacy 3-field ⇒ the all-roots
verdict); a pre/post mismatch writes the exit-3 `refused=capture-failure` record. Every
spawned role's cwd under worktree isolation is the worktree — peers included.
Post-v33.0 field datum (v33.2 rider): on the two source-repo runs since the verdict
shipped, every `dirty` verdict of the v33.0 build run was the own-worktree shape,
composer-verified root by root, and the v33.1 run's 14/14 checks were clean — zero
escape MUST-PAUSEs reached the operator (`AGENTS.md`, the v33.0/v33.1 run records).

**The codex peer launcher (v34.1).** A composer-seat codex peer round on a run with a run
worktree is no longer a per-run hand-written `codex exec … | tee` script with separate
helper calls around it. The composer starts the shipped `scripts/loop-peer-launcher.py` —
as exactly `python3 -I scripts/loop-peer-launcher.py`, from the base checkout, every
parameter a `LOOP_*` environment variable — and the launcher runs the one round and writes
its records itself, through the helper, in a fixed order: the keyed `ROLE: start` (marked
`via=launcher`), the one `OWNERSHIP: escape-check` record, and the `ROLE: end`, whose
`result=` is computed from codex's exit code and the round census. Its standard output is
three status-line shapes only; codex's own output goes to the peer log. The composer
writes the leg's `CONSUME:` verdict — carrying `leg=` and the verdict text that used to
sit on the end — and never the pair. The launcher serves runs with a run worktree only: a
standalone `/peer-loop` pass, Cursor subagent peers, `peer-seat=executor` rounds, a run
with no worktree, and inline fallbacks keep the hand-written records. The recipe is
published once, on the `/execute-loop` STICKY card (§4 step 8). Who writes what, the three
states of a leg whose launcher has exited, the quiet-leg rule, and the retry rule are
canonical in `/execute-loop` → Visibility + run-state → the `ROLE:` definition → Launcher
legs; the script's own header is the code-side contract.

**Notify tiers (D5).** Helper-computed from `class=`: `must-pause` (every reason, a
surfaced cap included) and `config-conflict` → `notify-send -u critical
"execute-loop: operator needed"`; every other class → `-u normal -t 20000
"execute-loop: <runkey> — done"` (macOS/Windows degrade to the title split).
`docs-only`/`invalid` are `mode=queued` (delivered in the phase batch); cap classes and
HIGH auto-routes stay `mode=immediate`. `notify=action-only` (`LOOP_NOTIFY`, rendered per
preflight step 14 at run start and re-rendered at every resume and `notify=` change — an
explicit `all` on an absent/malformed key; the helper reads only the environment; a running
observer keeps its startup policy until restarted) mutes only the batch desktop notice — members settle
as `batch-flushed detail="policy-suppressed notify=action-only"`. A must-pause re-fire
for a still-open key inside the liveness window (`--liveness`, default 10, needs
`--log`) refuses the whole pair. The observer (`scripts/loop-observer/watch-loop-run.sh`)
applies the same tiers: gates/append violations `critical`, the poll-driven categories
`normal -t 20000` and muted under `LOOP_NOTIFY=action-only`.

**Recommendation-first asks + `rec=` (D6), `PROGRESS` (D10), `profile-fallback=` (D11),
role-log rotation (D8).** Every surfaced ask leads with `Executor recommendation:` and
`Composer recommendation:` (option 1 = the executor's); `must-pause` and
`gate-disposition` carry the optional `rec=<executor|composer>:<disposition>`. The
phase-close `[<runkey>] Progress: …` line is chat-only (not log-derivable — `/retro`
names the gap). `profile-fallback="<profile_dir>"` records the fallback DECISION as
`auto-disposition key=profile-fallback` (queued) before the existing `profile-switch`
transaction, once per run (counter = the decision records); under `router=on` (v41.0)
the automatic fallback is the router's re-pick of a ROUTED role (its identity record
carries `route_run=`; a pinned role goes to the pause) — the same decision record,
written before the pick as the reservation — three per run on one counter across the
roles, `profile-fallback=` the Claude roles' last resort and, for the codex peer, the
launcher's inherited home only when it differs from the failed home, else the pause
(the owner of every admission: the execute-loop SKILL's Usage-exhaustion recovery, the
router branch; the map: Router mode, above). The spawn wrapper rotates an
oversized role log (> 50 MB, or every leg under `LOOP_ROLE_LOG_ROTATE=leg`) to
`<stem>.leg-<TS>[-n].log` before its retained open, announced as `SPAWN_WARN
check=role-log-rotated` on its own stdout.

**Rehydrate surfaces (D7).** The request-path rehydrate has two seats and no per-turn
injection: a marker-gated, seat-gated clause in `project-workflow.mdc` (`alwaysApply`) for
Cursor composers, and the shipped `.claude/hooks/loop-rehydrate.sh` for Claude Code
composers, wired by the DOCUMENTED `SessionStart` (`compact`, `resume`) settings snippet
below — the bootstrap never writes a settings file (guide §1 carries the same snippet):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact|resume",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/loop-rehydrate.sh --session" }
        ]
      }
    ]
  }
}
```

The hook (invoked via `bash`, no exec bit needed; `--session` is its only mode) prints
NOTHING when `LOOP_ROLE`/`LOOP_RUNKEY` is set (a spawned role) or when no LIVE run claims
the current root; it resolves the base checkout via `git rev-parse --git-common-dir`,
scans `<base>/.cursor/loops/*-active` with the mode-specific live predicate (worktree ⇒
its `-isolation` journal at `state=active`; branch/none ⇒ the marker alone; any
`.complete-*` sibling ⇒ closed), and matches the current root against the marker's
`checkout=` or the journal's `worktree=`. On a match it prints a CONDITIONAL pointer
("if this session is the run's composer, re-read STICKY + the handoff note; if not,
ignore"), listing every matching run; only `iso`/`mode`/`plan`/`worktree` are echoed,
each charset-validated and length-capped (`withheld` otherwise) — marker text is data,
never program text. From v48.0 it prints one line more, for a run it has just listed
that has a seat file: it asks the base checkout's watcher script, read-only
(`python3 <base>/scripts/loop-watchdog.py seat --base <base> --iso <iso>`), and when
that answer says `state=held` it says a watcher takeover holds the run's composer seat
and names the stop command — fixed text and the validated iso only, nothing of the
answer echoed; in a session that carries `LOOP_SEAT` (the takeover's own) it prints
nothing, and it still writes nothing. `/start-session` prints a one-line nudge when the hook reports a live
run and neither `.claude/settings.json` nor `.claude/settings.local.json` names
`loop-rehydrate.sh` (silent when neither file exists).

**Away mode and coordination (v34.0; v35.0; v35.1; v36.0; v37.0; v38.0) — pointer.** `/execute-loop` gains
`## Away mode`: ONE recorded grant per executor-mode run, written and read only through
the helper's composer-only `away` subcommand (`grant` / `end` / `check` / `report`, and
from v35.1 `ci-verdict`; the `away-grant` / `away-end` records live in the run's policy
log), under which the run stops only for the skill's **The four stops.**, keeps its
**Always the operator's.** waits, disposes the rest on the executor's recommendation or
a recorded composer decision, runs the live smoke itself, and — through `/close-run`'s
`## Under an away grant (v34.0)` — merges on green CI and deploys as far as the grant's
scope and the skill's **Release work** allow. From v35.0 the departure is one summary
plus one two-call question batch through the host's structured-question tool (**The
batch and the departure file**), `production` is proposed by default where eligible, and
production also runs on a departure-accepted unpinned step, and a merge that is itself
the production act with no pre-merge staging runs on its path's acceptance whatever its
class — both only through Release work item 5. From v35.1 the pre-merge CI gate is the
helper's, not the composer's: `/close-run` item 6 runs `away ci-verdict`, which reads the
pull request and the commit-bound check inventory itself (its only network calls — three
read-only `gh` reads it builds by kind), appends one `ci-verdict` record, and prints ONE
verdict line the composer routes; and `emit` refuses an away `merge` `choice=start` that
has no fresh admitting verdict for its `tip=` in the same log — a true late start, a
backdated record repair, is the one exception (the recipe, the verdict's rules, and the
admission rule: **Away mode → Record grammar → The CI verdict**). An
operator's hold on a named release act is an `OWNERSHIP: hold` record that `away check`
prints (`holds=` / `held=`) at every act and every wake until the operator clears it by
name (**The use-time check → Holds**; **Records → A hold**).
From v36.0 a plan that ships as several pull requests tags its phase headings with
release groups (`/execute-loop` → Run isolation → **Release groups**); from v40.0 ONE run
builds every group of the plan — one worktree, one branch, one grant, one preflight —
with the group close between groups (`/execute-loop` → Termination → **Group end**:
the group's pull request opened and merged from inside the run, the helper's
`run-close --outcome group-merged` record and its fast-forward of the base and the
worktree, the group's `[operator]` 🟩 write, then the next group's executor in the same
worktree), performed, never offered, under a bound grant or after the operator's merge
click; the run never stops at a group boundary, never ends its grant there, and asks
nothing (the v36.0–v38.0 boundary machinery — the run started from a close, the
answers carried between runs, `/close-run`'s next-release-group question — is retired).
The wizard and both presets recommend the answers that keep
a run moving — the away item `(default yes)`, the fallback profile picked by the
ranker's own rule, a candidate menu on a multi-plan cold start (**Setup wizard**;
**Safety gates** → The composer's own questions); the departure batch is scope-aware —
items 6–7 and the ungated-merge answer are printed, asked, and written only when the
scope carries `merge` or `production`, so a build-only grant's batch asks the scope
question and — from v47.0 — the usage fallback where the run has none set: every
departure file, whatever its scope, carries one `Usage fallback:` line, and `away grant`
refuses a file without it, the one departure check that refuses (**The pre-departure
check**, item 5; **The grant**); `Ungated merge: merge` admits a no-checks merge only when no
pull-request-class or run-branch-push workflow watches the diff, and every bounded wait
ends at the first read that settles it (both in `/close-run` item 6; the general wait
sentence: **Visibility + run-state** → the chunked-poll heartbeat); and an unattended
production act clears a docs-only foreign commit, coordinates with the run whose
unreleased commit it would ship under the `foreign-merge` pre-approval, and otherwise
parks on a foreign merge (Release work item 5 → **The foreign-merge check**; from
v44.0 **Records → A foreign clear and a coordinated wait**). From v37.0 many live runs
may each hold a bound grant: the read-only
`away census` verb lists them, the grant ends at the sites where its release work ends
with the helper refusing an automatic end while a release act is in flight, and a grant
left bound on a closed run is ended through `/close-run --iso` (**Away mode → Record
grammar → The census**; **Ending the grant → The belated end**). From v38.0 a
`scope=one-phase` run with phases left prints one nudge line (Preflight step 1); the
v38.0 re-arm of a release-machinery park under a new grant is retired at v44.0 (below).
From v40.0 one grant covers every release group of the plan:
`away end reason=release-done` on the modern recipe (with `--log-root`) requires
`--base` and is admitted only on a closed journal (`merged` / `cleaned` /
`retained-green`), and a park at any group keeps the grant
bound and the run waits for the operator's clear or a hand merge (**Ending the
grant**; **Termination → Group end**). From v44.0 the rails proceed and record where
they used to park: `/close-run` items 4 and 5 re-read a changed release-machinery file
and record it as an accepted version — or write an audit record for a file or heading
gone — and never park (**Records → The effective set and accepted versions**, the
relocated owner of the effective set, the comparison contract, the accepted versions,
and the applicable-procedure rule); the group close under a grant passes `--grant <n>
--away-check <h>` and the helper's `group-ff` leg writes a `rebaselined` record at the
group's MERGE COMMIT before `ff_stage_<N>` (**Records → A re-baseline**; Run isolation
→ **Mechanical close enforcement → The re-baseline**); the operator's standing answers
are pre-approvals — the departure classes offered ON as the grant's `allows=` kv (four
from v44.0; from v47.0 a fifth, `operator-merge`, asked only when the departure file
lists a merge as the operator's, and checked by the helper at that merge's start —
**Record grammar → The listing check**), per-task `agent` answers and mid-run chat
instructions as `pre-approval` records, one fold printing ` allows=` on the `away:` line
(**The use-time check → Pre-approvals** — six classes in all; **Records → A
pre-approval**); stop 2 narrows to a CRIT or production-impacting scope
expansion read from the route record's `impact=` (**The four stops**); clean
merge-forwards repeat up to ten times per close (**The fix cycle**); and `away grant`
warns about a Markdown file in the set with no heading — from v46.4 not about one the
departure file records whole on purpose, as `heading none (whole file)` (**The
grant**). From v47.0: `emit` checks every away merge start against the bound grant
and the departure file's merge-stop lines, and that start takes three more flags
(**Record grammar → The listing check**); the release pass sits inside the close,
before the merge — `/close-run`'s release stamp, which on a final close also archives
a Completed plan (`/close-run` Step 6, step 2a); a merge-forward confined to records
files is forwarded clean or, on a conflict, takes a light cycle, classified by the
helper's read-only `records-delta` (**The fix cycle**); a peer round of plain MED and
LOW fixes takes one verify-then-fix leg (The per-phase loop, step 4); a pre-cap
docs-only LOW round closes its pass with no confirm round (`/peer-loop` step 4); and a
widening is one `away grant … widens=<n>` call (**Ending the grant → Widening**).
Both lists, the
records, the verdict's rules, the hold, the release rules,
the release groups, and the group close are stated in those two skills only; this
doc does not restate them. v34.0 also added the
skill's `## Coordinating with other runs` prompt (identical in STICKY §9 and in
`/close-run` before Step 6), and the rehydrate hook above gains a second trigger: a
base-side `<iso-id>-policy.log` whose LAST `OWNERSHIP: away-` line is an `away-grant`,
for a run whose journal names this checkout, prints one pointer line even after the run
has closed — a text test that decides nothing (`away check` decides).

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
each task (**never auto-push** — the ONE carve-out is the explicit `/close-run`,
v33.2, stated in the skill's Run-isolation section). ralphex stays a useful reference impl + fallback if
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
  never auto-pushes (the ONE carve-out is the explicit `/close-run`, v33.2 — the
  skill's Run-isolation section).
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
  **[SUPERSEDED for SPAWNED architects at v32.2, 2026-08-13 — delegation-record transport:**
  the v28.0 sentence above — one destination "for spawned and live-session architects alike" —
  is HISTORICAL: stdout is not a record transport for a spawned architect, because the mandatory
  `--output-format stream-json` spawn shape JSON-escapes the tee (the text survives; the
  line-start record shape `/retro` parses does not). Current contract (v32.2): a SPAWNED
  architect appends its plain-text `DELEGATION:` records to its activation's COMPOSER-PRE-CREATED
  leg-keyed STAGING file `stage-<N>-delegation.<leg>.log` (worktree runs under
  `<worktree>/.cursor/loops/`; `branch`/`none` runs at the flat base log root), and at that
  activation's exit consume — BEFORE any teardown and BEFORE any generic worktree-record copy —
  the composer runs `python3 scripts/loop-journal.py fold-delegation` to PROMOTE the staging
  bytes to the canonical `<log-root>/stage-<N>-delegation.log`: the tool is the canonical file's
  ONLY writer (validated, bounded, activation-keyed append-once under durable receipts;
  composer-only at the grant layer — spawned-role grants carry only the narrowed emission
  shapes), a MISSING staging file at exit consume REFUSES (retained + surfaced, never read as
  zero work; the pre-created still-empty file is the explicit zero case), and a VERIFIED fold
  RETIRES that activation's staging file to a non-corpus name so `/retro` sees each admitted
  record exactly once. A LIVE-SESSION architect keeps the direct role-log append above,
  unchanged. The record grammar is the CLOSED variant matrix `decision|outcome|roi|smoke-addendum`
  — normative owner: the `DELEGATION_VARIANTS` constant in `scripts/loop-journal.py`, generated
  and verified from the checked-in `scripts/fixtures/delegation-variants.json`; this doc is a
  downstream representation (a selftest row asserts this variant list matches the constant).
  See `/execute-loop` → Optional delegating executor.**]**
  **[UPDATED v43.0, 2026-10-31 — the delegate's gates and effort pin:** the architect writes each
  unit's EXACT executable gate commands, with their working directory, into the unit spec from
  the repo's documented gates (never the close table's permission patterns, which are not
  commands); the delegate runs only those, verbatim, under the architect's permission context —
  the close table's Grants proposal is its grant set, so the patterns must cover the quoted
  commands (the skill's Grants rule). Under `verify=composer` the architect quotes no gate
  commands and the unit's `DELEGATION: outcome` carries the existing free `smoke=` value as
  `smoke=composer-run`, the `smoke-addendum` carrying the composer's result — the variant matrix
  above is unchanged. The delegate's effort is pinned in its agent definition's frontmatter
  beside the model and verified per run by Preflight step 6's probe. The run's delegation
  posture — the `Loop config:` key `delegation=conservative|broad`, a wizard answer shown on the
  close table, absent read as `conservative`, carried to the architect on its spawn prompt —
  decides what the architect hands over (`broad` includes security/auth and API-contract
  implementation once specified; design decisions, the plan's Critical Constraints, and the diff
  verification stay architect-held under both); the record grammar does not change with it. See
  `/execute-loop` → Optional delegating executor (the gate rule, the pin contract, and the
  posture rails, each stated once).**]**
  **[UPDATED v28.2, 2026-07-02 — diagnostics:** the loop recipe's observability gap is closed.
  Every role activation now gets a parseable `ROLE: start`/`end` pair (backend, model, best-effort
  `turns≈`/`tokens≈`/duration where the backend exposes them) in the run's `.cursor/loops/` logs —
  authored canonically in `/execute-loop` → Visibility + run-state, with pointer additions in
  `/peer-loop` (per peer round) and `/review-loop` (per-round `ROLE: round` line, loop-log context
  only; from v34.1 that line is emitted through the records helper — `emit ROLE:round`, the recipe
  in `/review-loop` — never appended by hand). The new propose-only `/retro` skill (20th) reads those logs (`ROLE:` + `DELEGATION:` +
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
  — there `--model <full ID>` is REQUIRED on every invocation and `--effort <level>`
  rides beside it when a level is pinned (v43.0 — the shell path is the one place
  delegate effort is a flag; for inherit the account default applies, not the
  architect's effort) (see `/execute-loop` → Optional delegating executor).
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
