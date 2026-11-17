#!/usr/bin/env bash
# scripts/loop-spawn-wrapper.sh — the committed /execute-loop spawn wrapper (v31.0, round-3).
#
# Spawns (or resumes) one loop-owned `claude -p` role with the full parameter
# contract the canonical skill pins (`## Backends` → Spawn wrapper), replacing
# the per-phase hand-authored heredoc that reproduced the EXIT:$EC footer bug
# in two separate observed runs (ledger-4e x2, stage-10 x2). The trap/footer
# quoting is written ONCE here and reviewed once.
#
# Probe-log contract (DR-1's ENUMERATED emission set — NOTHING else). Every
# emission beyond the legacy two is produced by CALLING the helper
# `scripts/loop-journal.py` (stdout redirected onto the wrapper's retained
# probe descriptor, fd 8, preserving the inode-pinned append) — ONE
# digest/vocabulary/clock implementation, never a bash twin:
#   1. SPAWN_WRAPPER_START ts=<iso> run=<runkey> role=<role> [resume=<id>]
#      (wrapper-native, byte-compatible, first)
#   2. ROLE: start ... phase="<phase>" role=<role> backend=claude-p
#      model=<model> leg=<leg> [effort=<level>]  (helper-emitted; for
#      wrapper-spawned roles the wrapper IS the ROLE: start emitter — and,
#      from v48.0, the emitter of the matching ROLE: end (item 5 below); the
#      composer NEVER authors a start, and writes an end only in the clean
#      close the skill text names. Through v47.0 the composer wrote the end,
#      reusing the LOOP_LEG value verbatim. Leg mint-freshness stays a
#      composer duty — a stateless wrapper cannot detect reuse; from v48.0 a
#      reused leg value gets its own per-leg files, `<leg>.2.*`)
#   3. OWNERSHIP: escape-check ... roots="<name>=<path>|<before>|<after>[; ...]" leg=<leg>
#      (helper-computed digests — sha256 over each root's `git status --short`
#      output, trailing newline stripped; before-digests captured
#      post-validation PRE-SPAWN with `git -C <abs-root>` — the cd happens
#      later — after-digests post-`wait` in the MAIN flow; ONE record, one
#      triple per LOOP_ESCAPE_ROOTS member. A FAILED pre-capture refuses
#      exit 2 with NO spawn. A FAILED post-capture is TWO cases (PR-MED-001):
#      helper exit 3 (a git-status capture failure) WRITES the
#      `refused=capture-failure` record naming the root to the probe log;
#      helper exit 2 (a `refuse()` — missing/malformed pre-state, root-set
#      mismatch) writes ONLY a stderr diagnostic — NO probe-log record. Either
#      way the wrapper folds the result to non-success; the record is never an
#      empty-string digest (F-04's bug))
#   4. OWNERSHIP: exit-census ts=<iso> run=<runkey> role=<role> leg=<leg> children=<n>
#      (helper-emitted; n = surviving processes in the child's recorded pgid
#      post-`wait` — the F-11 observed cross-check of the role's own declared
#      `emit VERIFY_OK children=<n>`; n>0 is a composer consume/anomaly and
#      NEVER a wrapper-side kill; from v33.4 the record also carries the
#      additive `rl_suppressed=<n>` — the pump's count of allowed /
#      allowed_warning rate_limit_event lines it rewrote to `USAGE_TICK …` on
#      the stdout mirror — ONLY when the pump exited clean; an absent key means
#      "not measured", never 0)
#   5. ROLE: end ts=<iso> run=<runkey> role=<role> result="<below>" leg=<leg>
#      duration=<s>  (v48.0, plan-loop-autonomy-group-2 D23; helper-emitted
#      with `--log`, so a second end for the leg is refused. Written whenever
#      THIS wrapper wrote the leg's ROLE: start — on a normal exit, a
#      post-start refusal and a signalled exit alike — directly before the
#      footer; a post-START exit that never wrote the start writes none. This
#      record and the footer are two separate appends, this one first: a
#      wrapper killed before its teardown writes neither; one killed between
#      the two, or whose footer append failed, leaves this record with no
#      footer — a missing footer never shows a missing end.
#      result= is mechanical: `exit <the footer's code>; handoff` when that
#      code is 0 and the last result event of the leg's stream ends in a
#      `ROLE: handoff ` line, else `incomplete: exit <code>; handoff|no
#      handoff`. A helper refusal there prints `SPAWN_WARN check=role-end …`
#      on stdout and never changes the exit code. The composer's verdict on
#      the leg is its CONSUME: record.)
#   6. EXIT:<code>  (wrapper-native trap footer; fires on EVERY exit path once
#      the START record exists — post-START refusals carry the EXIT:2 footer;
#      the probe log's LAST line of the spawn)
# All writes are APPEND-ONLY (>>). The wrapper never truncates, rewrites, or
# creates any other probe-log line: lock events and hygiene warnings print to
# the wrapper's OWN stdout (the composer's channel) for the composer to journal
# in composer voice (`ADOPT:` / `CLASSIFY:`), and an ABSENT EXIT footer (e.g.
# SIGKILL of the whole chain) is classified by the composer in composer voice —
# never synthesized into the probe log in the wrapper's voice.
#
# Parameter transport: LOOP_* ENVIRONMENT VARIABLES ONLY (PR-HIGH-010). The
# grant for this script is the EXACT no-argument shape
# `bash scripts/loop-spawn-wrapper.sh`, and the composer — which owns its shell
# and already sets the binary/tier authority in the environment (PR-HIGH-008) —
# sets EVERY parameter there too. The param-file transport is CLOSED: no
# path, behavioral, or identity selector is ever read from a file, so a prior
# scoped role editing a role-writable data file cannot make the later trusted
# composer invocation read, append, replace, or spawn outside the exact
# activation the composer resolved (a confused-deputy boundary). A surface that
# genuinely cannot set env cannot select the binary either, so the wrapper
# fail-closes there — the file was vestigial after PR-HIGH-008.
#
# DETECTION, not trust: if the default file (.cursor/loops/spawn-wrapper.env,
# override path via LOOP_SPAWN_ENV) EXISTS and names ANY LOOP_* key, the wrapper
# REFUSES LOUDLY (exit 2, no spawn) — such a file is stale or an attempted
# confused-deputy, never a legitimate transport. Nothing in it is ever consumed.
#
# Spawn-path dependencies (Constraint 10): python3 AND a blob-clean helper
# (`git hash-object` vs `git rev-parse HEAD:scripts/loop-journal.py` — the
# discipline the composer applies to the wrapper itself) are validated in the
# pre-spawn param block, refusing exit 2 on any mismatch. The FILE-prompt
# transport (LOOP_PROMPT_FILE) additionally requires coreutils `timeout` (or
# homebrew `gtimeout`) for the acquisition's wrapper-owned bound — validated
# fail-closed BEFORE the open (R15 PR-MED-001); inline LOOP_PROMPT carries
# no such dependency.
#
# Required:
#   LOOP_CLAUDE_BIN    absolute path of the pinned claude binary
#   LOOP_CWD           the role's pinned working directory (the worktree under
#                      isolation; the repo root otherwise) — never inherited
#   LOOP_PROBE_LOG     absolute BASE-SIDE probe-log path (append-only)
#   LOOP_ROLE_LOG      absolute BASE-SIDE role tee-log path (append-only; v33.0
#                      D8 — ROTATED at spawn, BEFORE the retained open, when the
#                      existing file exceeds 52,428,800 bytes or under
#                      LOOP_ROLE_LOG_ROTATE=leg: a no-clobber `mv` to
#                      `<stem>.leg-<YYYYMMDD-HHMMSS>[-n].log` (timestamp before
#                      the extension so /retro's `*.log` scan ingests archives;
#                      `-2`, `-3`, … on a same-second collision; refuse exit 2
#                      when no unique name exists), announced as
#                      `SPAWN_WARN check=role-log-rotated` on the wrapper's OWN
#                      stdout — never a probe-log line; the pump is untouched)
#   LOOP_RUNKEY        the run's phase-scoped runkey (stage-<N> — the helper
#                      refuses an iso-id; the F-12 domain split)
#   LOOP_ROLE          executor|architect|delegate|peer|advisor|reviewer
#   LOOP_PHASE         the phase identity for the ROLE: start phase="..." key
#   LOOP_LEG           the activation leg key (mint-fresh per activation — a
#                      composer duty; binds start/escape-check/exit-census)
#   LOOP_MODEL         --model value AND the ROLE: start model= key (REQUIRED —
#                      a model-less start would emit strict-invalid
#                      missing-model; the refuse-the-duty-but-spawn branch is
#                      deleted by design)
#   LOOP_ESCAPE_ROOTS  base=/abs/path[;<name>=/abs/path...] — the escape-check
#                      root manifest (base REQUIRED and FIRST; names lowercase
#                      [a-z0-9-]+, UNIQUE; every path absolute; members are
#                      converted 1:1 into the helper's repeatable --root args)
#   exactly one of:
#     LOOP_PROMPT_FILE absolute prompt-file path
#     LOOP_PROMPT      inline prompt text
#   Round-4 S-D: BOTH transports materialize a PRIVATE combined snapshot in
#   the child-unreachable pump workspace — the original prompt content + ONE
#   deterministic separator + the exit-contract footer with the VALIDATED
#   run/role values rendered in; the probe-log path (validated absolute +
#   opened pre-spawn) is NOT rendered — the footer carries only the fixed
#   quoted `LOOP_PROBE_LOG` environment reference the child expands at its
#   own shell boundary (R9 PR-LOW-001; the raw path never enters prompt
#   bytes). The child consumes ONLY the snapshot (stdin redirect in both
#   shapes). The caller's prompt file is NEVER modified.
#   Round-4 S-A leg 2: the wrapper prints a fixed STICKY_REREAD rehydrate
#   trigger on its wake-visible stdout PRE-CHILD (after param validation,
#   before the START write — the wrapper blocks through `wait`, so a
#   post-exit-only line arrives too late for the activation it accompanies)
#   plus an additive second copy on the post-exit result surface. NOT a
#   probe-log record (unscored transport; the scored artifact is the
#   composer's OWNERSHIP: sticky-ack receipt).
# Optional:
#   LOOP_EFFORT        --effort value (omit = inherit; no flag is passed)
#   LOOP_PROFILE_DIR   CLAUDE_CONFIG_DIR for the spawn (account profile); under
#                      router mode (below) the FALLBACK the role runs on when
#                      the router has no answer; on a LOOP_RESUME_SESSION
#                      spawn the FIRST candidate of the resume pin (v47.0 —
#                      the role runs on the folder that holds the transcript,
#                      which may be another)
#   LOOP_ROUTE_BIN     v41.0 router mode (D3) — optional; the ABSOLUTE path of
#                      claude-switch-gui's `claude-switch-route` (an executable
#                      regular file, validated like LOOP_CLAUDE_BIN; NEVER a
#                      PATH lookup). When set, the wrapper asks the router
#                      which logged-in profile folder this spawn runs under
#                      (`pick --agent=claude --run=<LOOP_ISO> --role= --phase=
#                      --model= --pid=$$ --label=<repo basename> --json`,
#                      through a bounded, isolated collector — after the escape
#                      pre-capture, before the ROLE: start emission) and exports
#                      the answer as CLAUDE_CONFIG_DIR; no answer (exit 3 + a
#                      reason word, exit 2, the 20 s deadline, an over-cap
#                      stream, non-JSON, another route_schema, a folder failing
#                      the answer rule, a command that could not be started —
#                      `other`) is NEVER fatal — the role runs on
#                      LOOP_PROFILE_DIR (on a LOOP_RESUME_SESSION spawn, v47.0:
#                      on the folder the resume pin finds, or it is refused
#                      `resume-pin` — below) and the wrapper prints
#                      `SPAWN_WARN check=router detail="<word>"` on its OWN
#                      stdout — the TWO-LINE shape (v42.0 D5/D9): when the
#                      router printed anything AFTER its reason word, or the
#                      folder check failed, a SECOND line follows at once,
#                      `SPAWN_WARN check=route-skipped detail="<text>"` — a
#                      token OUTSIDE the `check=router` prefix; <text> is the
#                      router's stderr after its first line (a diagnosing
#                      router's per-candidate `<dir> <reason>` lines, joined
#                      `; `) sanitized by the collector under the records
#                      helper's value rule (check_value_safety: every control
#                      byte, `"`, and non-space Unicode whitespace → a space,
#                      whitespace runs collapsed) and capped at 512 bytes, or
#                      the folder rule's own `<dir> <check>` (`relative` /
#                      `quote` / `control-byte` / `unicode-space` from the
#                      collector's shape rule — a lone surrogate counts as a
#                      control byte and non-space Unicode whitespace in a
#                      folder fails the answer rule, so every HONOURED folder
#                      satisfies the helper's value rule by construction
#                      (round 13 PR-MED-019/020); `no-dir`, `not-owned`, `group-writable`,
#                      `world-writable`, `unresolvable`, `inside-root` from
#                      route_dir_word; `resume-mismatch` from the resume rule
#                      — the answered folder as the collector SANITIZED and
#                      capped it on its fourth line, plus the closed check
#                      word the shell appends: the shell sanitizes nothing
#                      itself); the line is ABSENT when there is nothing to
#                      say (today's router prints no further line), the first
#                      line's closed word grammar is unchanged, and the text
#                      rides the collector's FOURTH stdout line — `route.err`
#                      is never read by the shell (the no-file-read rule).
#                      The composer journals BOTH lines as `ADOPT:`; a
#                      success prints `SPAWN_ROUTE dir="<dir>" via=pick|binding`
#                      there. All are composer-journaled lines, never
#                      probe-log records;
#                      the ROLE: start keys are unchanged (the routed folder
#                      rides the identity record: profile_dir= the EFFECTIVE
#                      folder, route_run=<LOOP_ISO>, route_phase=<LOOP_PHASE>).
#                      Requires LOOP_IDENTITY_FILE, LOOP_ISO, and
#                      LOOP_PROFILE_DIR (which must itself pass the answer
#                      rule's folder checks); refused beside LOOP_OAUTH_TOKEN_ENV
#                      and when its realpath lies inside LOOP_CWD or a
#                      LOOP_ADD_DIRS root — or when a root, or the command
#                      itself, does not resolve to a clean physical path (exit
#                      2, pre-START, no spawn — the six refusals + the topology
#                      rule, the ONE list in the validation block below). On a
#                      LOOP_RESUME_SESSION spawn (v47.0 — the resume pin, under
#                      LOOP_RESUME_SESSION below) the answer is honoured exactly
#                      when it is the HOLDER, the candidate folder with the
#                      newest transcript of the session, whatever its sticky
#                      flag — else `resume-mismatch`, and the role runs on the
#                      holder, which is no longer always LOOP_PROFILE_DIR (a
#                      resume never moves away from its transcript). Unset
#                      before the child
#                      starts: the child never sees it. A catchable
#                      cancellation (TERM / INT / HUP) reaching the collector
#                      is recorded and ends the router's group inside the same
#                      bound (`other` when recorded before the verdict) — never
#                      the default action, which would orphan a router in its
#                      own session (PR-MED-035); and the group is SWEPT at
#                      every return, a quiet descendant of an exited leader
#                      included (PR-MED-036).
#   LOOP_OAUTH_TOKEN_ENV  cloud token-pool selection (v32 TD.2 / PR-HIGH-003):
#                      the NAME of the numbered secret variable
#                      (CLAUDE_CODE_OAUTH_TOKEN_<N>, N >= 1) whose value the
#                      wrapper exports as the canonical CLAUDE_CODE_OAUTH_TOKEN
#                      by shell INDIRECTION — the token VALUE never appears in
#                      the wrapper's OWN emissions (argv, its probe-log lines,
#                      the identity record — which carries the NAME only — or
#                      any error). Validated fail-closed pre-spawn: the exact
#                      numbered grammar; LOOP_PROFILE_DIR required, its basename
#                      .claude-acct<N> matching the SAME N (the deterministic
#                      pool mapping); the named variable set non-empty. Rides
#                      fresh spawns AND resumes identically (the env transform
#                      is invocation-scoped). Whatever the selection, the exec
#                      environment is LEAST-CREDENTIAL (PR-HIGH-009): every
#                      CLAUDE_CODE_OAUTH_TOKEN_<N> and the selector itself are
#                      REMOVED before ANY subprocess — the strip runs before the
#                      prompt-file acquisition helper (r21 PR-HIGH-021), so not
#                      even the prompt reader inherits them; with a selection the
#                      prior canonical token is superseded by the selected value;
#                      with NO selection the ambient canonical is untouched (the
#                      seated-store/desktop fallback). Honest boundary (r21
#                      PR-HIGH-020): the pumped ROLE log mirrors the CHILD's
#                      stdout and the child necessarily HOLDS the canonical token
#                      to authenticate, so a child that echoes it lands those
#                      bytes there — role logs are gitignored + never committed,
#                      and the TD.5 persist secret-sweep is the backstop; the
#                      guarantee is over wrapper-authored + committed output,
#                      not child-authored log content.
#   LOOP_PERMS         scoped (default) | bypass — per-invocation tier flags:
#                      scoped renders --permission-mode acceptEdits (+ the
#                      grant list); bypass renders --dangerously-skip-permissions.
#                      Every spawn and resume, on both tiers, also renders
#                      --setting-sources user,project (v46.3); no variable
#                      changes it
#   LOOP_ALLOWED_TOOLS comma-separated close-table-confirmed grant shapes,
#                      passed verbatim as ONE --allowedTools value (scoped only)
#   LOOP_ADD_DIRS      colon-separated read roots, one --add-dir flag each
#   LOOP_RESUME_SESSION  session id — renders --resume <id> (tier flags are
#                      re-rendered on every resume; never inherited). v47.0,
#                      THE RESUME PIN: the id must be a UUID (8-4-4-4-12 hex
#                      digits; anything else is a `params` refusal), and the
#                      role is started on the profile folder that HOLDS the
#                      session's transcript, or not at all. Candidates, in tie
#                      order: LOOP_PROFILE_DIR; the router's answer when it
#                      passed the folder checks; the ambient folder (the
#                      CLAUDE_CONFIG_DIR the wrapper inherited, else
#                      ~/.claude under the wrapper's own home — for a /mnt/...
#                      Windows binary under WSL interop with no
#                      CLAUDE_CONFIG_DIR that is not the role's folder, so
#                      such a resume names its folder as LOOP_PROFILE_DIR).
#                      A relative folder is searched as the role
#                      will see it, against LOOP_CWD. The inherited variable
#                      reaches the role unchanged, so it is resolved as a
#                      native process resolves it, never by the MSYS
#                      conversion: on a Windows host a /-rooted value (a
#                      /c/... one included) lands on LOOP_CWD's drive, a
#                      drive-relative X:name under LOOP_CWD when X is its
#                      drive; on another drive the folder cannot be
#                      established and the candidate is indeterminate (a
#                      drive-relative LOOP_PROFILE_DIR likewise). Each reads one of three
#                      ways — it holds the session (a regular file
#                      projects/<any>/<id>.jsonl whose modification time was
#                      read); it does not (the folder or its projects/ does
#                      not exist or is not a folder, or every entry of
#                      projects/ was looked in and none has the file); or it is
#                      indeterminate (something on the way could not be read,
#                      or the name is there but is no regular file or is a
#                      link that resolves to nothing). ONE
#                      indeterminate candidate refuses, naming the folder — an
#                      older readable copy is never chosen over a folder that
#                      could not be searched. The holder is the candidate with
#                      the newest transcript (equal times: the earlier in the
#                      order above); the role runs on it — exported as
#                      CLAUDE_CONFIG_DIR, except an ambient holder, for which
#                      the inherited environment is left as it was — and it is
#                      read once more immediately before that. Stdout lines
#                      (composer-journaled, never probe-log records), after the
#                      first STICKY_REREAD and before ROLE: start:
#                      `SPAWN_WARN check=resume-pin detail="<holder>"` when
#                      the holder is not the folder the spawn was given
#                      (LOOP_PROFILE_DIR; the ambient folder when that is
#                      unset), and `SPAWN_WARN check=resume-pin-stale
#                      detail="<folder>[; <folder>]"` when another candidate
#                      holds a strictly older copy. The refusal is the class
#                      `SPAWN_REFUSED check=resume-pin` (exit 2) — no holder,
#                      an indeterminate candidate, a holder that fails the
#                      router answer rule's folder checks under router mode,
#                      a holder other than LOOP_PROFILE_DIR under
#                      LOOP_OAUTH_TOKEN_ENV (the pool's token is bound to that
#                      folder, v32 TD.2 — it is never started on another),
#                      or a transcript gone at the second read; its three
#                      positions are under Exit codes below.
#   LOOP_SPAWN_LOCK    per-run spawn-flock path; refusal prints SPAWN_LOCK_HELD
#                      to stdout and exits 3 with NO probe-log write
#   LOOP_IDENTITY_FILE identity-record path, written tmp -> atomic rename
#                      (v47.0: it carries `profile_dir=` on EVERY spawn — the
#                      folder the role runs on, the ambient folder when no
#                      profile was selected; left out only when that name
#                      holds a control byte or the ambient folder cannot be
#                      established); a
#                      session id recovered from the role log post-`wait`
#                      (bounded file read — the wrapper NEVER parses the live
#                      stream) lands via a SECOND atomic rename; the probe-log
#                      `IDENTITY: update` record stays helper-emitted at
#                      consume time by the composer
#   LOOP_SPAWN_ENV     override path for the CLOSED-transport detection check
#                      (the file is never consumed; a LOOP_* key in it refuses)
#   LOOP_ROLE_LOG_ROTATE  `leg` = rotate the role log at EVERY spawn (v33.0 D8);
#                      absent/empty = rotate only past the size threshold; any
#                      other value refuses (exit 2, pre-START)
#   LOOP_SURVIVE       v48.0 (plan-loop-autonomy-group-2 D16) — `on` | `off`;
#                      absent/empty = `on` where the host has os.fork (a
#                      Windows host always runs single-process); any other
#                      value refuses (exit 2, pre-START). ON: the wrapper
#                      forks twice before its validation — the first child
#                      calls setsid, forks again and exits at once; the
#                      grandchild, the SUPERVISOR, is today's wrapper with
#                      stdin from the null device and stdout / stderr appended
#                      to `<leg>.out` / `<leg>.err` beside the probe log, and
#                      it is adopted by whichever process takes orphans on the
#                      host. Where that process is above the composer, the
#                      supervisor is no longer in the composer's process tree,
#                      and a composer that dies (a TERM, a HUP, a quit, a KILL
#                      of its process — an app quit was not read) does not take
#                      the role with it; `<leg>.live` then says `survive=on`.
#                      Where the adopter is the composer or a process under it
#                      (a child subreaper), the leg still runs, the wrapper
#                      prints `SPAWN_WARN check=survive detail="…"` and
#                      `<leg>.live` says `survive=in-tree`: that leg does NOT
#                      outlive the composer's PROCESS TREE (the tree, not the
#                      composer: what ends the one need not end the other).
#                      Where it cannot be told — no
#                      decimal `CLAUDE_PID` in the environment, the composer's
#                      pid as a Claude Code session exports it, or one that is
#                      not an ancestor of the launched process — it says
#                      `survive=unverified`. The launched process becomes the TAIL: it
#                      follows those two files to its own stdout / stderr and
#                      exits with the code `<leg>.exit` records. Every recorded
#                      pid (`wrapper_pid` in the identity record, the lock's
#                      holder line, `<leg>.live`) is the SUPERVISOR's: TERM
#                      that pid to stop a role. A TERM / HUP / INT to the
#                      launched process ends the tail ALONE (exit 5,
#                      `SPAWN_DETACHED supervisor_pid=<n>`). OFF: one process,
#                      as through v47.0.
#   (not a parameter)  v48.0 — two things the wrapper does on EVERY spawn, in
#                      both modes and on every host: it writes the PER-LEG
#                      FILES beside the probe log — `<leg>.live` at start (its
#                      pid and start token; the role's pid, start token and
#                      process group added right after the launch), replaced
#                      at its end by `<leg>.exit` (those lines kept;
#                      `launched= exit= exit_ts= census=` added), on every
#                      path it returns by, refusals included (a wrapper killed
#                      outright, or signalled before START, leaves
#                      `<leg>.live`; `<leg>.2.*` … when the leg value was used
#                      before) — and it REMOVES `LOOP_SEAT`
#                      from the role's environment after closing every
#                      descriptor above 2 it inherited (D12).
#   v33.0 D4 escape-verdict inputs — PASSED THROUGH to BOTH escape-check twins
#   (pre and post) as helper flags; the helper is the single verdict owner
#   (Critical Constraint 4 — the wrapper computes nothing):
#   LOOP_EDIT_SURFACE  the spawned role's declared edit surface — a
#                      LOOP_ESCAPE_ROOTS member NAME (executor/architect/
#                      delegate under isolation: `worktree`; peers: unset) →
#                      `--edit-surface`; the record reports it as
#                      `edit_surface=<name>:<changed|unchanged>` and EXCLUDES
#                      it from `result=`. Must name a manifest root (refuse
#                      exit 2, pre-START otherwise). Absent ⇒ the all-roots
#                      verdict (today's behaviour).
#   LOOP_ALLOW_PATH    `<root>:<repo-relative path>[;<root>:<path>...]` — the
#                      paths whose git-status entries are FILTERED OUT of that
#                      root's digest (a peer's plan file + findings sidecar) →
#                      one `--allow-path` value (the helper splits on `;`;
#                      quote the value in a shell — `;` is a command separator)
#   LOOP_ISO           THIS run's iso-id → `--iso` (base-dirt attribution needs
#                      a DIFFERENT run's live marker; absent ⇒ no attribution)
#   LOOP_LIVENESS      `<minutes>|off` — the run's liveness interval (the
#                      attribution freshness window is 2x it; `off` disables
#                      attribution) → `--liveness`; absent ⇒ the helper's
#                      default 10. The composer passes the SAME resolved value
#                      to its composer-run peer twin (R2 PR-MED-005).
#   v33.0 D3 per-pass cap keys — ALL THREE or NONE (partial refuses exit 2,
#   pre-START — Critical Constraint 16); ride the wrapper-written ROLE: start
#   as `pass= peer_round= cap=`, and the helper SEQUENCES that keyed start
#   against the ACTUAL prior probe log via `--read-log "$LOOP_PROBE_LOG"` (a
#   READ-ONLY prior-record source — the sink stays the retained fd-8 write,
#   so the start still lands exactly once through the inode-bound descriptor;
#   PR-MED-003). Value rules (peer-only, `<slice>.p<N>`, consecutive rounds,
#   cap bound to the pass's recorded budget) are the helper's, never mirrored
#   here: a helper refusal is the existing post-START `check=role-start`
#   refusal (START/EXIT:2 pair, no child).
#   LOOP_PASS          the invocation-unique pass id `<phase-or-slice>.p<N>`
#   LOOP_PEER_ROUND    this activation's round within the pass (1-based)
#   LOOP_CAP           the pass's current cap
#
# Exit codes: the child's real exit code (via wait); 2 = parameter/validation
# refusal (pre-START: no probe-log write; post-START — a failed pre-capture or
# start emission, a failed keeper open on the pump FIFO, or (v33.4) a pump that
# died before the child spawn — the START/EXIT:2 pair is present, no child);
# v47.0 adds ONE refusal class to the frozen list (`params`, `param-file`,
# `escape-pre`, `role-start`, `pump-start`) — `resume-pin`, exit 2, at three
# positions: with no router configured, the LAST refusal of the validation
# block (pre-START, no probe-log write); under router mode, after the pick and
# before ROLE: start (the START/EXIT:2 pair); and the second read of the
# holder on either timing, after ROLE: start and before any child (START,
# ROLE: start, EXIT:2);
# 3 = spawn lock held (stdout event, no probe-log write); 4 = role-log pump
# failure or an unconfirmed pump on an otherwise-successful child; 129 / 130 /
# 143 = a HUP / INT / TERM the wrapper forwarded to the role's group.
# v48.0, under LOOP_SURVIVE=on, two codes of the TAIL's own (each beside one
# stdout line, which is what tells it from a role that exited 5 or 6):
# 5 = the tail was ended by a TERM / HUP / INT (`SPAWN_DETACHED
# supervisor_pid=<n>`) — the leg's state is in its files: a role that was
# running runs on, and a signal that arrives during the last forwarding of a
# leg that has already ended is answered with 5 as well, never with the leg's
# code; 6 = the supervisor is gone
# and wrote no `<leg>.exit`, so the leg's end is not known from the tail
# (`SPAWN_LOST supervisor_pid=<n> detail="…"`). In both lines `<n>` reads
# `unknown` where no supervisor's pid is known; and ONE loss does leave an
# `.exit`: a supervisor that could not be forked — the tail writes
# `launched=no exit=6` itself, and nothing was started. Every other code
# reaches the launched process through `<leg>.exit`, unchanged.
# Killing the launched process kills its watch surface, not the role: under
# LOOP_SURVIVE=on by design (the role is found again by its `<leg>.live` file),
# under `off` not necessarily — the composer's recorded identity + stall
# watchdog own that case.
#
# Structure (v42.0 D7 — the pinned parse): the executable body below is ONE
# brace group `{ … }` — opened before `set -u`, closed after the final
# `exit "$ec"`, the body not re-indented — so bash parses the file whole
# before running a line. An in-place rewrite of this file during a leg (the
# extractor's `open(out, "wb")` under `/update-workflow` — the field
# mechanism) cannot reach the running leg: it executes the bytes it parsed
# at start and the NEXT spawn runs the new bytes; a replacement by rename
# (git checkout / merge — a new inode) never could reach a running bash.
# The group's closing `}` is the file's last non-comment token (a selftest
# pin); `set -u`, the traps, `exit` inside functions, `set +m` / `set -m`,
# here-strings, the retained descriptors, and the quoted heredocs behave
# identically inside the group.

# ---------------------------------------------------------------------------
# v45.0 (plan-windows-port-and-router D2 / D13 / D14 / D31): THIS FILE IS A SHIM.
# The wrapper described by the header above is implemented ONCE, in Python,
# in `scripts/loop-spawn-wrapper.py` (the same LOOP_* contract, the same
# stdout tokens, refusal classes and order, probe-log records and exit codes —
# D7). This bash file stays so that every downstream grant shape
# `bash scripts/loop-spawn-wrapper.sh` keeps working unchanged (D13: no
# retirement machinery, no new grant). Its ONE brace group below does exactly
# four things and nothing else:
#   1. resolves `python3` (the spawn-path dependency gate — today's text; D14:
#      python3 must be on PATH on every host — on Windows the Store alias or
#      a python3.exe (bash resolves no .cmd by a bare name); the .py has no gate,
#      it runs under sys.executable) and defines `_lc`, the least-credential utility
#      boundary every external utility below runs through (round 31
#      PR-MED-001: the numbered pool variables and the selector unset in the
#      utility's own subshell — v44.0's strip-before-every-subprocess rule);
#   2. blob-verifies `loop-spawn-wrapper.py` against `HEAD:scripts/
#      loop-spawn-wrapper.py` of this file's own repository root (the
#      three-line form the v44.0 wrapper spent on the helper; the .py then
#      verifies and snapshots the helper itself);
#   3. names the .py ABSOLUTELY from its own resolved repository root
#      (`cd "$(dirname "$0")/.." && pwd`), the ROOT converted with `cygpath -m`
#      under MSYSTEM BEFORE the gate of step 2 (round 49) — the ONE path
#      conversion the shim performs: native Python cannot open a `/c/...`
#      operand, and neither can the gate's native git when the CALLER's
#      environment already carries `MSYS_NO_PATHCONV=1` (argv conversion off);
#   4. exports `MSYS_NO_PATHCONV=1` and `MSYS2_ENV_CONV_EXCL='*'` (MSYS's own
#      converters silenced — Python owns path conversion: `canon_path`, D17 /
#      D31) and `exec`s `python3 -I <dir>/loop-spawn-wrapper.py "$@"` from
#      the caller's cwd (so `LOOP_SPAWN_ENV`'s relative default keeps its
#      meaning). No environment VALUE is converted or inspected here.
# The body is still one brace group (parsed whole before a line runs) and the
# file is LF-pinned by `scripts/.gitattributes` (D25).
# ---------------------------------------------------------------------------
{
set -u

fail_usage() {
  echo "SPAWN_REFUSED check=params detail=\"$1\"" >&2
  exit 2
}

# --- 1. the spawn-path dependency gate: python3 (D14; today's gate text) ------
command -v python3 >/dev/null 2>&1 \
  || fail_usage "python3 not found — it joins the spawn path (the wrapper emits via scripts/loop-journal.py; Constraint 10)"

# --- 1b. the least-credential utility boundary (round 31 PR-MED-001) ---------
# v44.0 stripped the numbered pool variables and the selector BEFORE every
# subprocess it spawned (r21 PR-HIGH-021). Every external utility this shim
# runs — dirname, the two git gate calls, cygpath — therefore runs through _lc
# INSIDE a command substitution: the strip happens in that subshell alone
# (bash builtins only — compgen, [[ =~ ]], unset; no value in argv or any
# log), so no utility inherits a credential while the parent keeps every
# selection input for the Python wrapper's own validation and strip.
_lc() {
  local _t
  for _t in $(compgen -A export); do
    [[ "$_t" =~ ^CLAUDE_CODE_OAUTH_TOKEN_[1-9][0-9]*$ ]] && unset "$_t"
  done
  unset LOOP_OAUTH_TOKEN_ENV
  "$@"
}

# --- 2. the implementation, blob-verified against HEAD of this repo (D13) ----
# The .py is named ABSOLUTELY, from the resolved repository root (the v44.0
# HELPER form): `git -C "$_repo_root" hash-object -- <path>` resolves a
# RELATIVE operand against the repository root, not the caller's cwd, so a
# shim launched as `bash loop-spawn-wrapper.sh` from scripts/ or by any other
# relative path from outside the root would otherwise hash nothing and refuse.
_repo_root="$(cd "$(_lc dirname "$0")/.." && pwd)"
# round 49 (PC1 leg (d), run 5): under MSYS the root is spelled natively (`C:/...`)
# BEFORE the gate. `pwd` answers `/c/...`, which reaches the native git only
# through MSYS's argument conversion — and a caller whose environment already
# carries MSYS_NO_PATHCONV=1 (a common Git Bash setting) has that conversion
# OFF: `git -C /c/...` then failed and the gate refused a clean wrapper
# ("wrapper blob verification FAILED"). `cygpath` converts explicitly, whatever
# the caller exported, and a `C:/...` operand is left alone when the conversion
# is on. The .py below is built on the converted root (D31's one conversion).
if [ -n "${MSYSTEM:-}" ] && command -v cygpath >/dev/null 2>&1; then
  _repo_root="$(_lc cygpath -m "$_repo_root")"
fi
_py="$_repo_root/scripts/loop-spawn-wrapper.py"
[ -f "$_py" ] || fail_usage "wrapper implementation missing: $_py (D13 fail-closed)"
_py_wt="$(_lc git -C "$_repo_root" hash-object -- "$_py" 2>/dev/null || true)"
_py_head="$(_lc git -C "$_repo_root" rev-parse "HEAD:scripts/loop-spawn-wrapper.py" 2>/dev/null || true)"
if [ -z "$_py_wt" ] || [ -z "$_py_head" ] || [ "$_py_wt" != "$_py_head" ]; then
  fail_usage "wrapper blob verification FAILED (git hash-object vs HEAD:scripts/loop-spawn-wrapper.py) — an untracked/dirty wrapper implementation never rides a spawn (D13; Constraint 10)"
fi

# --- 3. the shim's own entrypoint path (D31): `$_py` is already native — it is
# built on the root converted above, before the gate (round 49) ---------------

# --- 4. silence MSYS's converters and hand over (from the caller's cwd) ------
export MSYS_NO_PATHCONV=1 MSYS2_ENV_CONV_EXCL='*'
exec python3 -I "$_py" "$@"
}
