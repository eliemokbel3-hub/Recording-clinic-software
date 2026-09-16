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
#      wrapper-spawned roles the wrapper IS the ROLE: start emitter — the
#      composer writes the matching ROLE: end reusing the LOOP_LEG value
#      verbatim and NEVER authors a start; leg mint-freshness stays a
#      composer duty — a stateless wrapper cannot detect reuse)
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
#      NEVER a wrapper-side kill)
#   5. EXIT:<code>  (wrapper-native trap footer; fires on EVERY exit path once
#      the START record exists — post-START refusals carry the EXIT:2 footer)
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
#   LOOP_PROFILE_DIR   CLAUDE_CONFIG_DIR for the spawn (account profile)
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
#                      PR-HIGH-020): the tee'd ROLE log mirrors the CHILD's
#                      stdout and the child necessarily HOLDS the canonical token
#                      to authenticate, so a child that echoes it lands those
#                      bytes there — role logs are gitignored + never committed,
#                      and the TD.5 persist secret-sweep is the backstop; the
#                      guarantee is over wrapper-authored + committed output,
#                      not child-authored log content.
#   LOOP_PERMS         scoped (default) | bypass — per-invocation tier flags:
#                      scoped renders --permission-mode acceptEdits (+ the
#                      grant list); bypass renders --dangerously-skip-permissions
#   LOOP_ALLOWED_TOOLS comma-separated close-table-confirmed grant shapes,
#                      passed verbatim as ONE --allowedTools value (scoped only)
#   LOOP_ADD_DIRS      colon-separated read roots, one --add-dir flag each
#   LOOP_RESUME_SESSION  session id — renders --resume <id> (tier flags are
#                      re-rendered on every resume; never inherited)
#   LOOP_SPAWN_LOCK    per-run spawn-flock path; refusal prints SPAWN_LOCK_HELD
#                      to stdout and exits 3 with NO probe-log write
#   LOOP_IDENTITY_FILE identity-record path, written tmp -> atomic rename; a
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
# start emission — the START/EXIT:2 pair is present, no child); 3 = spawn lock
# held (stdout event, no probe-log write); 4 = role-log pump failure or an
# unconfirmed pump on an otherwise-successful child. Killing the wrapper kills
# its watch surface, not the child necessarily — the composer's recorded
# identity + stall watchdog own that case.

set -u
# Job control OFF for the wrapper's own group (r2-B1): an inherited
# SHELLOPTS=monitor would otherwise re-enable it at startup and the tee pump
# below would anchor its own process group instead of the wrapper's.
set +m

fail_usage() {
  echo "SPAWN_REFUSED check=params detail=\"$1\"" >&2
  exit 2
}

# --- closed param-file transport detection (PR-HIGH-010) ---------------------
# The param-file transport is CLOSED: parameters are environment-only. The file
# is NEVER read for values — a scoped role editing it cannot influence this
# composer spawn. It IS scanned for detection: if it exists and names ANY LOOP_*
# key, that is a stale file or an attempted confused-deputy, so the wrapper
# REFUSES rather than proceed. (The scan strips a leading comment/blank; a
# bare `#` or empty file is fine.)
PARAM_FILE="${LOOP_SPAWN_ENV:-.cursor/loops/spawn-wrapper.env}"
if [ -f "$PARAM_FILE" ]; then
  while IFS= read -r _pline || [ -n "$_pline" ]; do
    case "$_pline" in
      ''|'#'*) continue ;;
      LOOP_[A-Z_]*=*)
        echo "SPAWN_REFUSED check=param-file detail=\"the param-file transport is CLOSED (PR-HIGH-010) — parameters are environment-only; a LOOP_* key in $PARAM_FILE is stale or tampering, refusing\"" >&2
        exit 2 ;;
      *) continue ;;
    esac
  done < "$PARAM_FILE"
fi

# --- validation (refusals happen BEFORE any probe-log write) -----------------
[ -n "${LOOP_CLAUDE_BIN:-}" ] || fail_usage "LOOP_CLAUDE_BIN unset"
[ -n "${LOOP_CWD:-}" ] || fail_usage "LOOP_CWD unset"
[ -n "${LOOP_PROBE_LOG:-}" ] || fail_usage "LOOP_PROBE_LOG unset"
[ -n "${LOOP_ROLE_LOG:-}" ] || fail_usage "LOOP_ROLE_LOG unset"
[ -n "${LOOP_RUNKEY:-}" ] || fail_usage "LOOP_RUNKEY unset"
[ -n "${LOOP_ROLE:-}" ] || fail_usage "LOOP_ROLE unset"
# DR-1 item 2: LOOP_PHASE / LOOP_LEG / LOOP_MODEL join the REQUIRED block —
# the wrapper's ONE uniform refusal semantics (fail_usage, exit 2, NO spawn);
# the refuse-the-duty-but-still-spawn branch was deleted by design (it
# re-opened F-07 and a model-less start emits strict-invalid missing-model).
[ -n "${LOOP_PHASE:-}" ] || fail_usage "LOOP_PHASE unset (ROLE: start phase= is required — F-07)"
[ -n "${LOOP_LEG:-}" ] || fail_usage "LOOP_LEG unset (the activation leg key is required)"
[ -n "${LOOP_MODEL:-}" ] || fail_usage "LOOP_MODEL unset (a model-less start would emit strict-invalid missing-model)"
[ -n "${LOOP_ESCAPE_ROOTS:-}" ] || fail_usage "LOOP_ESCAPE_ROOTS unset (the escape-check root manifest is required — F-09)"

# --- token-pool selection + least-credential env (v32 TD.2; PR-HIGH-003/009) --
# PLACEMENT (r21 PR-HIGH-021): runs BEFORE the prompt-file acquisition helper
# and every other subprocess/child, so NO wrapper-spawned process — not even
# the `timeout … cat` prompt reader — inherits the numbered pool credentials
# or the selector. Validation is fail-closed BEFORE any probe/child effect;
# the token value moves ONLY by indirection — never interpolated into argv,
# any log line, the identity record, or an error message.
_token_env_name=""
if [ -n "${LOOP_OAUTH_TOKEN_ENV:-}" ]; then
  [[ "$LOOP_OAUTH_TOKEN_ENV" =~ ^CLAUDE_CODE_OAUTH_TOKEN_[1-9][0-9]*$ ]] \
    || fail_usage "LOOP_OAUTH_TOKEN_ENV must NAME a numbered pool variable (CLAUDE_CODE_OAUTH_TOKEN_<N>, N >= 1) — the selection grammar is exact (v32 TD.2)"
  [ -n "${LOOP_PROFILE_DIR:-}" ] \
    || fail_usage "LOOP_OAUTH_TOKEN_ENV requires LOOP_PROFILE_DIR — the numbered token maps deterministically onto ~/.claude-acct<N> (v32 TD.2)"
  _acct_n="${LOOP_OAUTH_TOKEN_ENV#CLAUDE_CODE_OAUTH_TOKEN_}"
  case "${LOOP_PROFILE_DIR%/}" in
    */.claude-acct"$_acct_n") ;;
    *) fail_usage "LOOP_OAUTH_TOKEN_ENV names pool $_acct_n but LOOP_PROFILE_DIR does not end in .claude-acct$_acct_n — the acct<N> <-> TOKEN_<N> mapping is deterministic; a mismatch refuses (v32 TD.2)" ;;
  esac
  [ -n "${!LOOP_OAUTH_TOKEN_ENV:-}" ] \
    || fail_usage "LOOP_OAUTH_TOKEN_ENV names $LOOP_OAUTH_TOKEN_ENV but that variable is unset or empty — a missing pool credential refuses, never a silent seated-store fallback (v32 TD.2)"
  _token_env_name="$LOOP_OAUTH_TOKEN_ENV"
  export CLAUDE_CODE_OAUTH_TOKEN="${!_token_env_name}"  # indirection; supersedes any ambient canonical
fi
# Least-credential strip (unconditional): every numbered pool variable and the
# selector leave the exec environment; with no selection the ambient canonical
# CLAUDE_CODE_OAUTH_TOKEN stays (seated-store/desktop behaviour, unchanged).
for _tok in $(compgen -A export); do
  [[ "$_tok" =~ ^CLAUDE_CODE_OAUTH_TOKEN_[1-9][0-9]*$ ]] && unset "$_tok"
done
unset LOOP_OAUTH_TOKEN_ENV

if [ -n "${LOOP_PROMPT_FILE:-}" ] && [ -n "${LOOP_PROMPT:-}" ]; then
  fail_usage "LOOP_PROMPT_FILE and LOOP_PROMPT are mutually exclusive"
fi
if [ -z "${LOOP_PROMPT_FILE:-}" ] && [ -z "${LOOP_PROMPT:-}" ]; then
  fail_usage "one of LOOP_PROMPT_FILE / LOOP_PROMPT is required"
fi
if [ -n "${LOOP_PROMPT_FILE:-}" ]; then
  # R14 PR-MED-001 (subsumes the R8 -f/-r pathname pre-test): SINGLE-OPEN
  # prompt ACQUISITION at the validation boundary — validation IS the
  # acquisition. ONE open; the regular-file check runs on the OPENED
  # DESCRIPTOR (/dev/fd), never the pathname again; the bytes delivered are
  # exactly the opened object's. This closes the R8-era seam where pathname
  # validation and the authoritative read were separate operations: a raced
  # type swap can no longer deliver non-regular bytes, and a raced FIFO can
  # no longer park a bare `cat` open — the wrapper-owned bound terminates a
  # blocked open, and the placement BEFORE the spawn flock / probe channels /
  # pump workspace means a blocked or failed acquisition holds nothing and
  # dies recordless-by-design (nothing yet claims a spawn). The bound's tool
  # is a DECLARED file-transport dependency (R15 PR-MED-001): coreutils
  # `timeout`, or homebrew coreutils' `gtimeout` on macOS — with NEITHER
  # present the wrapper fails CLOSED here, BEFORE any open (the r14 silent
  # unbounded fallback was itself the r15 finding; a dark hang must be an
  # EXPLAINED refusal). Inline LOOP_PROMPT carries no such dependency.
  # Honest residual: a regular-to-regular content swap BEFORE the single
  # open is undetectable here — the pathname is composer-owned (trusted);
  # delivered bytes are the single opened object's. Trailing-newline
  # semantics: the pinned S-D command-substitution form, unchanged.
  if command -v timeout >/dev/null 2>&1; then
    _pf_tool="timeout"
  elif command -v gtimeout >/dev/null 2>&1; then
    _pf_tool="gtimeout"
  else
    fail_usage "file-prompt acquisition requires coreutils 'timeout' (or homebrew 'gtimeout') for its wrapper-owned bound — a DECLARED dependency of the LOOP_PROMPT_FILE transport (R15 PR-MED-001); install coreutils or use the inline LOOP_PROMPT transport"
  fi
  if ! prompt_text="$("$_pf_tool" 10 bash -c 'exec 3<"$1" || exit 9; [ -f /dev/fd/3 ] || exit 8; cat <&3' _ "$LOOP_PROMPT_FILE" 2>/dev/null)"; then
    fail_usage "LOOP_PROMPT_FILE capture FAILED at single-open acquisition (non-regular object at open, unreadable, vanished, or a blocked non-regular open past the bound): $LOOP_PROMPT_FILE — a child never spawns on unverified prompt bytes (R14 PR-MED-001)"
  fi
fi
case "${LOOP_PERMS:-scoped}" in
  scoped|bypass) ;;
  *) fail_usage "LOOP_PERMS must be scoped or bypass" ;;
esac
# v33.0 D8: the rotation policy is a closed two-value grammar — `leg` (rotate
# the role log at EVERY spawn) or absent/empty (rotate only when the target
# already exceeds the size threshold). Any other value refuses here, pre-START.
case "${LOOP_ROLE_LOG_ROTATE:-}" in
  ''|leg) ;;
  *) fail_usage "LOOP_ROLE_LOG_ROTATE must be 'leg' or unset (absent = size-threshold rotation only; v33.0 D8)" ;;
esac

# --- absolute-path contract (PR-MED-042): the wrapper pins the binary, cwd,
# prompts, and evidence paths ONCE — a RELATIVE input resolves to a DIFFERENT
# resource after `cd "$LOOP_CWD"` (the child validated-before-cd differs from
# the one read/written after), and a bare binary re-resolves through PATH (the
# multi-install class the canonical `claude -p` pin forbids). Validate BEFORE
# the flock, the START write, and any child — reject relative/ambiguous inputs
# (exit 2, zero probe/child effects) so the resource used before and after cd
# is the exact same absolute path.
require_abs() {
  case "$2" in
    /*) ;;
    *) fail_usage "$1 must be an ABSOLUTE path (got '$2') — a relative path re-resolves under cd/PATH" ;;
  esac
}
# --- native-value safety (R16 PR-HIGH-002; Critical Constraint 13) -----------
# Every value reaching a wrapper-NATIVE probe-log line (the START record) or
# the identity file is validated BEFORE the flock, the START write, and any
# child — the one emission path that bypasses loop-journal.py, whose
# check_value_safety() is the CANONICAL contract these checks mirror (DR-2
# pins exactly four helper subcommands, so the shared contract is mirrored
# here rather than a fifth validate surface; reject structural bytes only,
# never over-constrain — real session IDs/paths keep their safe punctuation).
# require_token: START-line fields (run/role/resume) are single printable
# tokens — an embedded space would inject bare tokens/forged key=value pairs
# into the record, a newline/C0 would forge a SECOND physical record (the
# reproduced OWNERSHIP: smoke-pass forgery), and the quote grammar has no
# escape.
require_token() {
  case "$2" in
    *[![:graph:]]*) fail_usage "$1 contains whitespace/control bytes — a forged-record lever on a native probe line (Constraint 13)" ;;
    *'"'*) fail_usage "$1 contains a double quote — an injection lever (Constraint 13)" ;;
  esac
}
# require_line_safe: identity-file values (one key per line) may hold spaces
# (paths), never control bytes — a newline/CR forges identity records.
require_line_safe() {
  case "$2" in
    *[[:cntrl:]]*) fail_usage "$1 contains control bytes — a forged identity/record lever (Constraint 13)" ;;
  esac
}
# line_safe: the NON-FATAL predicate form (R17) for a LATE-BOUND value read
# post-`wait` from the child-controlled role log — a refusal there would
# discard a completed run, so the caller SKIPS the enrichment and keeps the
# input-derived identity instead. Same control-byte contract; returns 0 safe.
line_safe() {
  case "$1" in
    *[[:cntrl:]]*) return 1 ;;
  esac
  return 0
}
require_token LOOP_RUNKEY "$LOOP_RUNKEY"
require_token LOOP_ROLE "$LOOP_ROLE"
require_token LOOP_LEG "$LOOP_LEG"
[ -z "${LOOP_RESUME_SESSION:-}" ] || require_token LOOP_RESUME_SESSION "$LOOP_RESUME_SESSION"
require_line_safe LOOP_CWD "$LOOP_CWD"
require_line_safe LOOP_MODEL "$LOOP_MODEL"
require_line_safe LOOP_PHASE "$LOOP_PHASE"
[ -z "${LOOP_EFFORT:-}" ] || require_line_safe LOOP_EFFORT "$LOOP_EFFORT"
[ -z "${LOOP_PROFILE_DIR:-}" ] || require_line_safe LOOP_PROFILE_DIR "$LOOP_PROFILE_DIR"
require_abs LOOP_CLAUDE_BIN "$LOOP_CLAUDE_BIN"
[ -x "$LOOP_CLAUDE_BIN" ] || fail_usage "LOOP_CLAUDE_BIN is not an executable file: $LOOP_CLAUDE_BIN"
require_abs LOOP_CWD "$LOOP_CWD"
[ -d "$LOOP_CWD" ] || fail_usage "LOOP_CWD is not a directory: $LOOP_CWD"
require_abs LOOP_PROBE_LOG "$LOOP_PROBE_LOG"
require_abs LOOP_ROLE_LOG "$LOOP_ROLE_LOG"
[ -z "${LOOP_PROMPT_FILE:-}" ] || require_abs LOOP_PROMPT_FILE "$LOOP_PROMPT_FILE"
[ -z "${LOOP_IDENTITY_FILE:-}" ] || require_abs LOOP_IDENTITY_FILE "$LOOP_IDENTITY_FILE"
[ -z "${LOOP_SPAWN_LOCK:-}" ] || require_abs LOOP_SPAWN_LOCK "$LOOP_SPAWN_LOCK"
if [ -n "${LOOP_ADD_DIRS:-}" ]; then
  IFS=':' read -r -a _absroots <<< "$LOOP_ADD_DIRS"
  for _absroot in "${_absroots[@]}"; do
    [ -z "$_absroot" ] || require_abs LOOP_ADD_DIRS "$_absroot"
  done
fi
# LOOP_ESCAPE_ROOTS members (grammar pinned at DR-1 item 3): name=/abs/path,
# ';'-separated, base FIRST; the wrapper checks shape + absoluteness and
# converts members 1:1 into --root args — the helper is the single deep
# validation owner (names, uniqueness, delimiter/control rejection).
_rootargs=()
IFS=';' read -r -a _eroots <<< "$LOOP_ESCAPE_ROOTS"
for _er in "${_eroots[@]}"; do
  [ -n "$_er" ] || fail_usage "LOOP_ESCAPE_ROOTS has an empty member"
  case "$_er" in
    *=/*) ;;
    *) fail_usage "LOOP_ESCAPE_ROOTS member '$_er' is not name=/abs/path" ;;
  esac
  require_abs LOOP_ESCAPE_ROOTS "${_er#*=}"
  _rootargs+=(--root "$_er")
done
case "${_eroots[0]}" in
  base=*) ;;
  *) fail_usage "LOOP_ESCAPE_ROOTS: base= is REQUIRED and FIRST" ;;
esac
# --- v33.0 D4 escape-verdict inputs → the helper's flags (both twins) --------
# The wrapper checks only what it already owns (the manifest's member NAMES;
# control bytes on a value it forwards) and forwards everything else verbatim —
# the helper is the single deep-validation owner (allow-path grammar, iso
# shape, liveness domain) and the ONLY verdict computer (Constraint 4).
_escargs=()
if [ -n "${LOOP_EDIT_SURFACE:-}" ]; then
  require_line_safe LOOP_EDIT_SURFACE "$LOOP_EDIT_SURFACE"
  _es_ok=0
  for _er in "${_eroots[@]}"; do
    [ "${_er%%=*}" = "$LOOP_EDIT_SURFACE" ] && _es_ok=1
  done
  [ "$_es_ok" = "1" ] || fail_usage "LOOP_EDIT_SURFACE '$LOOP_EDIT_SURFACE' must name a LOOP_ESCAPE_ROOTS member (the spawned role's edit surface is one of the manifest roots — v33.0 D4)"
  _escargs+=(--edit-surface "$LOOP_EDIT_SURFACE")
fi
if [ -n "${LOOP_ALLOW_PATH:-}" ]; then
  require_line_safe LOOP_ALLOW_PATH "$LOOP_ALLOW_PATH"
  _escargs+=(--allow-path "$LOOP_ALLOW_PATH")
fi
if [ -n "${LOOP_ISO:-}" ]; then
  require_token LOOP_ISO "$LOOP_ISO"
  _escargs+=(--iso "$LOOP_ISO")
fi
if [ -n "${LOOP_LIVENESS:-}" ]; then
  require_token LOOP_LIVENESS "$LOOP_LIVENESS"
  _escargs+=(--liveness "$LOOP_LIVENESS")
fi
# --- v33.0 D3 per-pass cap keys: all three or none (Constraint 16) ----------
_pass_kv=()
_pass_present=0
for _pk in LOOP_PASS LOOP_PEER_ROUND LOOP_CAP; do
  [ -n "$(eval "printf %s \"\${$_pk:-}\"")" ] && _pass_present=$((_pass_present + 1))
done
if [ "$_pass_present" -eq 3 ]; then
  require_token LOOP_PASS "$LOOP_PASS"
  require_token LOOP_PEER_ROUND "$LOOP_PEER_ROUND"
  require_token LOOP_CAP "$LOOP_CAP"
  _pass_kv=("pass=$LOOP_PASS" "peer_round=$LOOP_PEER_ROUND" "cap=$LOOP_CAP")
elif [ "$_pass_present" -ne 0 ]; then
  fail_usage "LOOP_PASS / LOOP_PEER_ROUND / LOOP_CAP ride together or not at all (partial-pass-keys — absence is the standalone shape; v33.0 D3, Critical Constraint 16)"
fi

# --- spawn-path dependency gate (Constraint 10): python3 + blob-clean helper -
command -v python3 >/dev/null 2>&1 \
  || fail_usage "python3 not found — it joins the spawn path (the wrapper emits via scripts/loop-journal.py; Constraint 10)"
HELPER="$(cd "$(dirname "$0")" && pwd)/loop-journal.py"
[ -f "$HELPER" ] || fail_usage "helper missing: $HELPER (Constraint 10 fail-closed)"
_repo_root="$(cd "$(dirname "$0")/.." && pwd)"
_helper_wt="$(git -C "$_repo_root" hash-object -- "$HELPER" 2>/dev/null || true)"
_helper_head="$(git -C "$_repo_root" rev-parse "HEAD:scripts/loop-journal.py" 2>/dev/null || true)"
if [ -z "$_helper_wt" ] || [ -z "$_helper_head" ] || [ "$_helper_wt" != "$_helper_head" ]; then
  fail_usage "helper blob verification FAILED (git hash-object vs HEAD:scripts/loop-journal.py) — an untracked/dirty helper never rides a spawn (Constraint 10)"
fi

# --- Round-4 S-A leg 2 (DR4-1): the signal-carried rehydrate trigger ---------
# Printed on the wrapper's OWN stdout (the composer-consumed wake surface)
# AFTER param validation and BEFORE the START write/child launch — pre-child
# because the wrapper blocks through `wait`. Fixed text, validated tokens
# only (require_token ran above); never a probe-log write (fd 8 untouched).
echo "STICKY_REREAD run=$LOOP_RUNKEY role=$LOOP_ROLE detail=\"rehydrate: re-read STICKY.md + the plan's Current State / Handoff Note (Loop config: included) before acting on this spawn's events\""

# --- spawn flock (loop step 1 invariant (ii); lock events -> composer ADOPT:) -
if [ -n "${LOOP_SPAWN_LOCK:-}" ]; then
  exec 9>>"$LOOP_SPAWN_LOCK"
  if ! flock -n 9; then
    # The CURRENT holder's info is the LAST appended line (acquisitions append).
    holder="$(tail -n 1 "$LOOP_SPAWN_LOCK" 2>/dev/null | head -c 200)"
    echo "SPAWN_LOCK_HELD run=$LOOP_RUNKEY role=$LOOP_ROLE holder=\"${holder:-unknown}\""
    exit 3
  fi
  printf 'wrapper_pid=%s ts=%s run=%s role=%s\n' "$$" "$(date -Iseconds)" \
    "$LOOP_RUNKEY" "$LOOP_ROLE" >&9
  echo "SPAWN_LOCK_ACQUIRED run=$LOOP_RUNKEY role=$LOOP_ROLE"
fi

# --- required-log OPEN (PR-MED-021, strengthens PR-MED-018): the probe + role
# logs are the exit-classification and liveness evidence surfaces; a child must
# not exist until BOTH are actually OPEN as retained descriptors (a stat-only
# check passes a directory/broken-symlink target, whose tee then silently fails
# while the child runs — the dark-child class). The open IS the validation
# (TOCTOU-free): a directory/device/broken-symlink/missing-parent target fails
# the open -> REFUSE (exit 2, no child, no success footer). Done AFTER the flock
# so a lock refusal leaves no log file; the ROLE log opens FIRST so a role-open
# failure never creates the probe file. The child's stream attaches to the
# validated role-log descriptor (/dev/fd/7 via the pump), and every probe-log
# emission rides the probe descriptor (fd 8) — both by inode, so a post-open
# path swap cannot detach the child from its evidence.
# An existing NON-REGULAR target is rejected BEFORE the open (PR-MED-026): a
# device sink (/dev/null discards all evidence, /dev/full fails only on write)
# and a FIFO (which would BLOCK the append-open) all pass a bare open — only a
# regular evidence file is a valid audit channel. A broken symlink is absent to
# `-e`, so it falls through to the open, which fails and refuses.
for _lv in LOOP_ROLE_LOG LOOP_PROBE_LOG; do
  _lp=$(eval "printf %s \"\$$_lv\"")
  if [ -e "$_lp" ] && [ ! -f "$_lp" ]; then
    fail_usage "$_lv exists but is not a regular file (device/FIFO/directory?): $_lp"
  fi
done

# --- v33.0 D8: spawn-time role-log rotation — BEFORE the `exec 7>>` open ------
# One role log appended across 109 legs reached 1 GB in the field (88% executor
# tee). The bound is applied at the ONE moment the file is provably not held by
# THIS wrapper's pump — before the retained descriptor opens (the pump below is
# byte-untouched: Critical Constraint 8) — after the OPTIONAL spawn flock above
# (when LOOP_SPAWN_LOCK is passed, two spawns never race one rotation; without
# it the no-clobber move + verify below is the only race guard, and the loser
# simply lands on the next suffix). Policy: rotate when the existing REGULAR
# target exceeds 52,428,800 bytes, or at every spawn under
# LOOP_ROLE_LOG_ROTATE=leg. Archive name `<stem>.leg-<YYYYMMDD-HHMMSS>[-n].log`
# — the timestamp goes BEFORE the `.log` extension so `/retro`'s existing
# `*.log` role-log scan ingests every archive unchanged and orders legs by name
# (R3 PR-MED-006). NO-CLOBBER (PR-MED-008): the destination is chosen only
# where nothing exists, moved with `mv -n`, and VERIFIED moved (a raced or
# skipped move falls through to the next deterministic suffix `-2`, `-3`, …);
# when no unique name can be created within the bound the spawn REFUSES (exit
# 2, nothing moved) — rotation never replaces an earlier leg's evidence.
# A `mv` renames by inode: a stray writer still holding the OLD inode keeps
# appending to the ARCHIVE, never to the fresh log — append-only is preserved
# on both files. The announcement is a SPAWN_WARN on the wrapper's OWN stdout
# (the composer's channel; open `check=` vocabulary) — never a probe-log line.
ROLE_LOG_ROTATE_BYTES=52428800
_rotate_reason=""
if [ -f "$LOOP_ROLE_LOG" ]; then
  _rl_size="$(stat -c %s "$LOOP_ROLE_LOG" 2>/dev/null || stat -f %z "$LOOP_ROLE_LOG" 2>/dev/null || wc -c < "$LOOP_ROLE_LOG" 2>/dev/null)"
  _rl_size="${_rl_size//[[:space:]]/}"
  case "$_rl_size" in
    ''|*[!0-9]*) fail_usage "could not read the size of LOOP_ROLE_LOG for the v33.0 D8 rotation decision: $LOOP_ROLE_LOG" ;;
  esac
  if [ "${LOOP_ROLE_LOG_ROTATE:-}" = "leg" ]; then
    _rotate_reason="policy=leg size=$_rl_size"
  elif [ "$_rl_size" -gt "$ROLE_LOG_ROTATE_BYTES" ]; then
    _rotate_reason="policy=size size=$_rl_size threshold=$ROLE_LOG_ROTATE_BYTES"
  fi
fi
if [ -n "$_rotate_reason" ]; then
  _rl_stem="${LOOP_ROLE_LOG%.log}"
  _rl_ts="$(date +%Y%m%d-%H%M%S)"
  case "$_rl_ts" in
    [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]) ;;
    *) fail_usage "could not read a YYYYMMDD-HHMMSS timestamp for the role-log archive name (date failed?)" ;;
  esac
  _rl_archive=""
  _rl_n=1
  while [ "$_rl_n" -le 99 ]; do
    if [ "$_rl_n" -eq 1 ]; then
      _rl_cand="$_rl_stem.leg-$_rl_ts.log"
    else
      _rl_cand="$_rl_stem.leg-$_rl_ts-$_rl_n.log"
    fi
    if [ ! -e "$_rl_cand" ] && mv -n -- "$LOOP_ROLE_LOG" "$_rl_cand" 2>/dev/null \
       && [ ! -e "$LOOP_ROLE_LOG" ] && [ -f "$_rl_cand" ]; then
      _rl_archive="$_rl_cand"
      break
    fi
    # the candidate existed, or the no-clobber move was skipped/raced: the
    # source is untouched — try the next deterministic suffix
    _rl_n=$((_rl_n + 1))
  done
  if [ -z "$_rl_archive" ]; then
    fail_usage "role-log rotation could not create a unique archive name for $LOOP_ROLE_LOG (every $_rl_stem.leg-$_rl_ts[-n].log up to -99 exists) — refusing rather than overwrite an earlier leg's evidence (v33.0 D8, PR-MED-008); nothing was moved"
  fi
  echo "SPAWN_WARN check=role-log-rotated detail=\"role log rotated before open: $_rotate_reason archive=$_rl_archive (v33.0 D8; the new leg starts on a fresh $LOOP_ROLE_LOG)\""
fi

if ! { exec 7>>"$LOOP_ROLE_LOG"; } 2>/dev/null; then
  fail_usage "LOOP_ROLE_LOG is not an appendable file (directory/device/broken symlink?): $LOOP_ROLE_LOG"
fi
if ! { exec 8>>"$LOOP_PROBE_LOG"; } 2>/dev/null; then
  fail_usage "LOOP_PROBE_LOG is not an appendable file (directory/device/broken symlink?): $LOOP_PROBE_LOG"
fi
# Post-open regular-file re-check: a symlink resolving to a device, or a target
# swapped between the -e test and the open, is caught here before any spawn.
for _lv in LOOP_ROLE_LOG LOOP_PROBE_LOG; do
  _lp=$(eval "printf %s \"\$$_lv\"")
  [ -f "$_lp" ] || fail_usage "$_lv did not resolve to a regular file: $_lp"
done

# --- pump workspace (r2-B1/r3-B1): a private mktemp -d holds the role-log
# FIFO (and the tee-timeout marker), with UNCONDITIONAL removal in the EXIT
# trap. Established (and refused-if-impossible) BEFORE any probe write or
# child — the waitable-pump invariant cannot be dropped (PR-MED-033's
# fail-closed stance carries; the _teestat sink it protected is RETIRED — the
# pump status now comes from `wait "$tee_pid"` directly).
tmpd="$(mktemp -d "${TMPDIR:-/tmp}/loop-wrapper-pump.XXXXXX" 2>/dev/null || true)"
if [ -z "$tmpd" ] || [ ! -d "$tmpd" ]; then
  fail_usage "could not create the private pump directory (TMPDIR unwritable?) — refusing rather than spawning without a waitable role-log pump"
fi
fail_pre_trap() {
  # R12-LOW-003: ONE owner for the pre-trap refusal path — every refusal
  # between pump-workspace creation and the EXIT-trap arming tears the
  # workspace down here (the R14-LOW-001 convention, mechanized: a per-site
  # remembered `rm` is exactly what the next added refusal forgets, and that
  # leak is silent).
  rm -rf "$tmpd"
  fail_usage "$1"
}
if ! mkfifo "$tmpd/pump.fifo" 2>/dev/null; then
  fail_pre_trap "could not create the pump FIFO under $tmpd"
fi
# --- helper snapshot (R18 PR-HIGH-001, hardened R19 PR-MED-001): the helper
# was blob-VERIFIED pre-spawn (Constraint 10), but the child spawns below with
# repo-edit perms and could rewrite scripts/loop-journal.py mid-run — and the
# wrapper RE-INVOKES the helper POST-`wait` (escape-check post, exit-census)
# for the very evidence meant to detect that tampering (a circular defeat if
# it ran the child's bytes). Copy the helper ONCE into the private $tmpd
# (child-unreachable — the path is never exported) and point $HELPER at the
# snapshot for EVERY call (pre- and post-`wait` alike). VERIFY-then-COPY-then-
# REVERIFY: the pre-spawn blob-verify at :280-283 checked the ORIGINAL, but
# that check and this cp are non-atomic — a concurrent writer between them
# could copy in unverified bytes — so re-blob-verify the SNAPSHOT itself
# against HEAD after the cp; only bytes provably equal to the committed helper
# are ever invoked. (R18's original wording "one verify, no TOCTOU window" was
# IMPRECISE — the window moved from post-`wait` to check-to-cp; this reverify
# closes it.) Cleaned up with $tmpd by the EXIT trap; any failure fails CLOSED.
if ! cp "$HELPER" "$tmpd/loop-journal.py" 2>/dev/null; then
  fail_pre_trap "could not snapshot the verified helper into the private workspace (R18 PR-HIGH-001) — refusing rather than re-invoking a child-replaceable helper post-wait"
fi
_snap_wt="$(git -C "$_repo_root" hash-object -- "$tmpd/loop-journal.py" 2>/dev/null || true)"
if [ -z "$_snap_wt" ] || [ "$_snap_wt" != "$_helper_head" ]; then
  fail_pre_trap "helper SNAPSHOT blob verification FAILED (git hash-object of the \$tmpd copy != HEAD:scripts/loop-journal.py) — the check-to-cp window was raced; refusing (R19 PR-MED-001)"
fi
HELPER="$tmpd/loop-journal.py"

# --- prompt-template self-identification hygiene (F1) — warn-only, stdout ----
# (R14 PR-MED-001: the old `prompt_text=""` set-u initializer here CLOBBERED
# the validation-boundary capture — the file transport's value is already
# bound; only the inline branch assigns below.)
# R8 PR-HIGH-002 → R14 PR-MED-001: the file-transport prompt was captured at
# the VALIDATION boundary above (single-open, descriptor-verified, bounded),
# pre-flock and pre-workspace, so no capture path can block or fail here.
# (The R8-era comment here claimed a raced non-file target necessarily
# reached the refusal branch — OVERBROAD, corrected at r14: pre-R14 a raced
# FIFO blocked the bare `cat` open, dark, holding the spawn flock
# pre-START/pre-trap. The single-open acquisition owns that whole class
# now.) The inline transport binds here; the semantic-empty check below
# covers BOTH transports (R9 PR-HIGH-004 / R11 PR-HIGH-006).
if [ -z "${LOOP_PROMPT_FILE:-}" ]; then
  prompt_text="$LOOP_PROMPT"
fi
# R9 PR-HIGH-004 + R11 PR-HIGH-006: the captured caller prompt must contain
# AT LEAST ONE NON-WHITESPACE CHARACTER (the R11-refined invariant — R9's
# "nonempty" wording was satisfiable by whitespace bytes, the family's
# defensive tail) — a zero-byte, newline-only, or spaces/tabs-only source
# reads successfully and would otherwise materialize a footer-only snapshot;
# both transports share this predicate. INSPECTION-ONLY: accepted prompt
# bytes are never trimmed or rewritten. POST-capture placement covers races
# and normalization.
case "$prompt_text" in
  *[![:space:]]*) ;;
  *)
    fail_pre_trap "captured caller prompt has NO non-whitespace content (zero-byte/newline-only/whitespace-only source: ${LOOP_PROMPT_FILE:-inline}) — a child never receives a footer-only snapshot (R9 PR-HIGH-004 / R11 PR-HIGH-006)" ;;
esac
case "$prompt_text" in
  *execute-loop-cx*)
    echo "SPAWN_WARN check=fork-label detail=\"prompt names the deprecated execute-loop-cx fork — stale template?\"" ;;
esac
case "$prompt_text" in
  *"$LOOP_RUNKEY"*) ;;
  *)
    echo "SPAWN_WARN check=runkey-missing detail=\"prompt does not name runkey $LOOP_RUNKEY — reused scaffold from another run?\"" ;;
esac

# --- Round-4 S-D: the PRIVATE combined prompt snapshot -----------------------
# BOTH transports render ONE snapshot in the child-unreachable pump workspace:
# the original prompt content + one deterministic separator + the
# exit-contract footer with the VALIDATED run/role values rendered in; the
# probe-log path stays UNRENDERED — the footer carries the fixed quoted
# `LOOP_PROBE_LOG` environment reference (escaped `\$` below), which the
# child expands from its inherited environment, so the raw path never enters
# prompt bytes (R9 PR-LOW-001 documenting the R8 PR-HIGH-003 form; the path
# itself is still validated absolute + opened as fd 8 pre-spawn). The child
# consumes ONLY the snapshot (stdin redirect in both shapes below); the
# caller's prompt file is NEVER modified. Determinism note:
# $(cat) command substitution strips trailing newlines, so `printf '%s\n'`
# yields exactly one newline boundary before the separator whether or not the
# source ended with one (the empty-final-newline case). A failed snapshot
# write refuses pre-START (fail-closed, workspace removed).
snapshot="$tmpd/prompt.snapshot"
if ! {
  printf '%s\n' "$prompt_text"
  printf '%s\n' "----- /execute-loop spawn-wrapper footer (S-D; wrapper-rendered exit contract — values validated at spawn) -----"
  printf '%s\n' "EXIT RULES for this spawned role (run=$LOOP_RUNKEY role=$LOOP_ROLE):"
  printf '%s\n' "- ATOMIC final step: immediately before your final message run exactly one validated declaration — python3 scripts/loop-journal.py emit VERIFY_OK --run $LOOP_RUNKEY --role $LOOP_ROLE --log \"\$LOOP_PROBE_LOG\" children=<your actual still-live child count> (LOOP_PROBE_LOG is inherited in your environment — expand it in your shell exactly as written, never retype the path; invoke the helper by its path in your working checkout; the tool owns the format, you supply the count). Any count > 0 means KEEP WAITING, never exit."
  printf '%s\n' "- Your LITERAL last output line is the exit sentinel: ROLE: handoff ts=<real date -Iseconds read> run=$LOOP_RUNKEY reason=<phase-complete|composer-run|must-pause> [gate=\"<one-liner>\"]"
} > "$snapshot" 2>/dev/null; then
  fail_pre_trap "could not materialize the private prompt snapshot under the pump workspace (S-D fail-closed)"
fi

# --- DR-1 emission 1: the START line now; the trap footer on EVERY exit ------
start_line="SPAWN_WRAPPER_START ts=$(date -Iseconds) run=$LOOP_RUNKEY role=$LOOP_ROLE"
if [ -n "${LOOP_RESUME_SESSION:-}" ]; then
  start_line="$start_line resume=$LOOP_RESUME_SESSION"
fi
# The START write must SUCCEED before the child exists (PR-MED-026): a probe
# channel that cannot take the START record is not a valid audit channel.
# R14-LOW-001: this is the one refusal window after the pump workspace exists
# and before the EXIT trap owns cleanup — remove it here, never leak it.
if ! echo "$start_line" >&8; then
  rm -rf "$tmpd" 2>/dev/null
  fail_usage "LOOP_PROBE_LOG write failed on the SPAWN_WRAPPER_START record: $LOOP_PROBE_LOG"
fi
# Trap discipline (DR-1): the trap installs IMMEDIATELY after the START write —
# closing the START-with-no-EXIT gap a mid-sequence refusal would open — and
# its body is a FUNCTION (`trap 'on_exit' EXIT`). Footer quoting rule
# (canonical `## Backends`): $? is read at TRAP-FIRE time in the shell that
# owns the status; fd 8 is the retained, validated probe-log descriptor
# (PR-MED-021). The normal path runs the after-captures + census post-`wait`
# in the MAIN flow so the footer is never delayed behind fallible work; the
# trap keeps only a minimal bounded fallback for abnormal paths (kill the
# wrapper's OWN tee — never the child or its orphans — remove the private
# pump dir, drop an unconsumed pre-state this invocation created).
on_exit() {
  ec_trap=$?
  # v33.0 T2.1 (the TB.1 double-EXIT flake — recurred once on leg
  # phase1-verify-r13-1 WITH the watchdog's `trap - EXIT` in place): the footer
  # and the pump-dir teardown belong to the MAIN wrapper process ONLY. Bash
  # documents that subshells reset caught traps, yet the field shape (an
  # EXIT:0 written BEFORE the post-capture, the pump dir gone under the live
  # helper, then the real EXIT:4) is exactly an inherited trap firing in a
  # forked shell (command substitution / `( ) &` / pipeline element) — and a
  # bounded probe on this host reproduced NONE of those paths deliberately, so
  # the mechanism is unidentified. Rather than chase the path, make EVERY
  # forked-shell firing inert BY CONSTRUCTION: $BASHPID is the executing
  # process's pid while $$ stays the main shell's, so a subshell running this
  # body returns before touching fd 8 or $tmpd. (bash < 4 has no BASHPID —
  # the guard degrades to the pre-v33.0 behaviour there, never to a refusal.)
  if [ "${BASHPID:-$$}" != "$$" ]; then
    return 0
  fi
  echo "EXIT:$ec_trap" >&8
  if [ -n "${tee_pid:-}" ]; then
    kill "$tee_pid" 2>/dev/null
  fi
  if [ "${_pre_created:-0}" = "1" ] && [ "${_post_ran:-0}" = "0" ]; then
    rm -f "$_prestate" 2>/dev/null
  fi
  rm -rf "${tmpd:-}" 2>/dev/null
  return 0
}
trap 'on_exit' EXIT
# SIGNALS (r2-B1): composer teardown forwards to the recorded child pgid, so
# group-directed signals still reach the isolated child tree.
on_signal() {
  if [ -n "${child_pgid:-}" ]; then
    kill -s "$1" -- "-$child_pgid" 2>/dev/null
  fi
  exit "$2"
}
trap 'on_signal TERM 143' TERM
trap 'on_signal INT 130' INT
trap 'on_signal HUP 129' HUP

# --- DR-1 emission 3 (pre leg): before-digests captured post-validation,
# PRE-SPAWN, via the helper (`git -C <abs-root>` — the cd happens later; the
# pre-state file lands under the log root, outside the probe-log grammar). A
# FAILED pre-capture refuses: exit 2, NO spawn (the START/EXIT:2 pair is on
# the probe log — the trap is already armed).
log_root="${LOOP_PROBE_LOG%/*}"
_prestate="$log_root/$LOOP_RUNKEY-escape-$LOOP_LEG.pre"
if ! python3 "$HELPER" escape-check --run "$LOOP_RUNKEY" --role "$LOOP_ROLE" \
    --capture pre --leg "$LOOP_LEG" --log-root "$log_root" "${_rootargs[@]}" \
    ${_escargs[@]+"${_escargs[@]}"}; then
  echo "SPAWN_REFUSED check=escape-pre detail=\"pre-spawn escape-check capture failed — refusing (exit 2, no spawn; F-04 fail-closed)\"" >&2
  exit 2
fi
_pre_created=1
_post_ran=0

# --- DR-1 emission 2: the wrapper-owned ROLE: start, via the helper ----------
_start_kv=("phase=$LOOP_PHASE" backend=claude-p "model=$LOOP_MODEL" "leg=$LOOP_LEG")
if [ -n "${LOOP_EFFORT:-}" ]; then
  _start_kv+=("effort=$LOOP_EFFORT")
fi
# v33.0 D3: a KEYED peer start carries pass=/peer_round=/cap= and is SEQUENCED
# by the helper against the actual prior log through the READ-ONLY --read-log
# (the validated absolute probe-log PATHNAME — a re-open by path, NOT a read
# of fd 8: the read side is the composer-owned pathname trust class, the same
# residual the prompt-file pathname carries, while the EVIDENCE side stays
# inode-bound); the emission's SINK stays this retained-descriptor write (>&8),
# so the start lands exactly once and a path swap cannot detach it
# (PR-MED-003). An unkeyed start passes no --read-log (the helper refuses it
# on an unkeyed shape).
_start_flags=()
if [ "${#_pass_kv[@]}" -ne 0 ]; then
  _start_kv+=("${_pass_kv[@]}")
  _start_flags=(--read-log "$LOOP_PROBE_LOG")
fi
if ! python3 "$HELPER" emit ROLE:start --run "$LOOP_RUNKEY" --role "$LOOP_ROLE" \
    ${_start_flags[@]+"${_start_flags[@]}"} "${_start_kv[@]}" >&8; then
  echo "SPAWN_REFUSED check=role-start detail=\"the helper refused the ROLE: start emission — refusing (exit 2, no spawn)\"" >&2
  exit 2
fi

# --- invocation build (per-invocation tier rendering; nothing inherited) -----
# Round-4 S-D: no argv prompt in EITHER transport — the child reads the
# private combined snapshot on stdin (built above), so the footer rides every
# spawn shape and the caller's prompt file/inline text is never the delivery.
argv=("$LOOP_CLAUDE_BIN" -p)
argv+=(--output-format stream-json --verbose)
if [ "${LOOP_PERMS:-scoped}" = "bypass" ]; then
  argv+=(--dangerously-skip-permissions)
else
  argv+=(--permission-mode acceptEdits)
  if [ -n "${LOOP_ALLOWED_TOOLS:-}" ]; then
    argv+=(--allowedTools "$LOOP_ALLOWED_TOOLS")
  fi
fi
argv+=(--model "$LOOP_MODEL")
if [ -n "${LOOP_EFFORT:-}" ]; then
  argv+=(--effort "$LOOP_EFFORT")
fi
if [ -n "${LOOP_ADD_DIRS:-}" ]; then
  IFS=':' read -r -a _roots <<< "$LOOP_ADD_DIRS"
  for _root in "${_roots[@]}"; do
    [ -n "$_root" ] && argv+=(--add-dir "$_root")
  done
fi
if [ -n "${LOOP_RESUME_SESSION:-}" ]; then
  argv+=(--resume "$LOOP_RESUME_SESSION")
fi
if [ -n "${LOOP_PROFILE_DIR:-}" ]; then
  export CLAUDE_CONFIG_DIR="$LOOP_PROFILE_DIR"
  case "$LOOP_CLAUDE_BIN" in
    /mnt/*) export WSLENV="${WSLENV:+$WSLENV:}CLAUDE_CONFIG_DIR/p" ;;
  esac
fi

cd "$LOOP_CWD" || exit 1

# --- the role-log pump (r2-B1 restructure; r3-B1 made the lifecycle TOTAL) ---
# The wrapper opens a KEEPER read-write fd on the FIFO FIRST (an RW open never
# blocks — the open protocol is TOTAL: the tee's reader never blocks on a
# missing writer, and a child whose writer side fails cannot strand it —
# closing the keeper yields EOF), then starts the tee in the WRAPPER'S OWN
# group (job control is OFF here — the set +m at the top holds even under an
# inherited SHELLOPTS=monitor). `tee -a /dev/fd/7` appends to the validated
# role-log descriptor by inode and still mirrors to the wrapper's stdout.
if ! { exec 5<>"$tmpd/pump.fifo"; } 2>/dev/null; then
  echo "SPAWN_REFUSED check=pump-writer detail=\"keeper open failed on the pump FIFO — refusing (no reader started, nothing stranded)\"" >&2
  exit 2
fi
# The tee starts with the keeper fd CLOSED in its own fd table (5>&-) — an
# inherited keeper copy would hold the FIFO writer open inside the reader
# itself and EOF could never arrive.
tee -a /dev/fd/7 < "$tmpd/pump.fifo" 5>&- &
tee_pid=$!

# --- spawn (DR-1): job control is SCOPED to the spawn line (`set -m` then
# restored) so the child anchors its OWN recorded pgid (= its pid) containing
# only the child's process tree — the tee is outside it by construction.
# `env -u SHELLOPTS` scrubs the inherited monitor option from the CHILD's
# environment so a bash descendant does not re-group its own children outside
# the recorded census domain (the r1-P1/r2-B1 class). `wait "$child"` keeps
# the real exit code (NO setsid — it empirically breaks exit-code fidelity
# and PID capture under inherited job control).
set -m
# Round-4 S-D: BOTH transports deliver the private combined snapshot on stdin
# (the caller's prompt file is read-only source material, never the delivery).
env -u SHELLOPTS "${argv[@]}" < "$snapshot" >&5 2>&1 &
child=$!
set +m
child_pgid="$child"

# --- identity record: write-tmp -> atomic rename (F5), $$-suffixed tmp -------
write_identity() {
  idtmp="$LOOP_IDENTITY_FILE.tmp.$$"
  {
    printf 'ts=%s\n' "$(date -Iseconds)"
    printf 'run=%s\n' "$LOOP_RUNKEY"
    printf 'role=%s\n' "$LOOP_ROLE"
    printf 'leg=%s\n' "$LOOP_LEG"
    printf 'wrapper_pid=%s\n' "$$"
    printf 'claude_pid=%s\n' "$child"
    printf 'cwd=%s\n' "$LOOP_CWD"
    printf 'model=%s\n' "$LOOP_MODEL"
    [ -n "${LOOP_PROFILE_DIR:-}" ] && printf 'profile_dir=%s\n' "$LOOP_PROFILE_DIR"
    [ -n "$_token_env_name" ] && printf 'token_env=%s\n' "$_token_env_name"
    [ -n "${LOOP_RESUME_SESSION:-}" ] && printf 'resume=%s\n' "$LOOP_RESUME_SESSION"
    [ -n "${1:-}" ] && printf 'session=%s\n' "$1"
    true
  } > "$idtmp" && mv -f "$idtmp" "$LOOP_IDENTITY_FILE" \
    || echo "SPAWN_WARN check=identity-write detail=\"identity record not written to $LOOP_IDENTITY_FILE\""
}
if [ -n "${LOOP_IDENTITY_FILE:-}" ]; then
  write_identity ""
fi

wait "$child"
ec=$?

# --- exit census (DR-1 item 4; ORDER PINNED: census BEFORE any potentially-
# blocking pump wait). Post-`wait` the child is reaped, so every process still
# in the recorded pgid is a survivor. One short settle retry gives a
# just-exiting process a moment; survivors are the composer's disposition —
# already reported by the census record — never a wrapper-side kill.
# R16 PR-MED-001: a FAILED census is never a clean zero — `children=0` means
# the census COMMAND succeeded and observed zero matching processes. A failed
# `ps`, a failed pipeline stage, or malformed output returns nonzero here and
# the caller records the admitted refusal shape + folds the wrapper result
# (the role-log pump's fail-closed fold-in pattern), never a fabricated 0.
census_pgid() {
  _psout="$(ps -eo pgid=,pid= 2>/dev/null)" || return 1
  [ -n "$_psout" ] || return 1
  _n="$(printf '%s\n' "$_psout" | awk -v pg="$1" '$1+0 == pg+0 { n++ } END { print n+0 }')" || return 1
  case "$_n" in
    ''|*[!0-9]*) return 1 ;;
  esac
  printf '%s\n' "$_n"
}
census_ok=1
if ! children="$(census_pgid "$child_pgid")"; then
  census_ok=0
  children=""
fi
if [ "$census_ok" = "1" ] && [ "$children" -gt 0 ]; then
  sleep 1
  if ! children="$(census_pgid "$child_pgid")"; then
    census_ok=0
    children=""
  fi
fi

# --- close the keeper, then BOUNDED wait on the tee (r3-B1): past the bound
# (an orphan holds the FIFO writer) the wrapper kills ITS OWN tee — never the
# orphan — and folds the pump as unconfirmed-nonsuccess. On the normal path
# `wait "$tee_pid"` returns the pump's status DIRECTLY (the _teestat temp-file
# machinery is RETIRED; its fail-closed fold-in semantics are preserved below).
exec 5>&-
# TB.1 (v32): the watchdog subshell opens with `trap - EXIT` — an inherited
# on_exit firing here emits a second EXIT: record and rm -rf's the pump dir
# while $HELPER still lives in it, losing the post escape-check + exit-census
# (observed live: stage-0-verify-r6 double EXIT:0/EXIT:4, intermittent).
# Defensive mitigation: bash normally resets EXIT traps in subshells, but the
# reproduced flake says not reliably on every path — clear it explicitly.
( trap - EXIT; sleep 5; : > "$tmpd/tee-timeout"; kill "$tee_pid" 2>/dev/null ) &
_teewd=$!
wait "$tee_pid"
tee_status=$?
kill "$_teewd" 2>/dev/null
wait "$_teewd" 2>/dev/null
# R14-MED-001: the timeout classification requires the marker AND a NONZERO
# tee status — a watchdog firing in the wait->kill race window after a CLEAN
# pump exit (marker touched, kill lands on a dead pid) must not reclassify a
# healthy 0 into timeout/rc-4; a genuinely killed tee waits 143.
if [ -e "$tmpd/tee-timeout" ] && [ "$tee_status" != "0" ]; then
  tee_status="timeout"
fi

# --- DR-1 emission 3 (post leg): after-digests post-`wait`, MAIN flow. A
# failed post-capture is TWO distinct helper exit codes (R13 H4 PR-MED-001):
#   exit 3 = a status_digest capture failure — the helper WROTE the
#            `refused=capture-failure` record naming the root to the probe log;
#   exit 2 = a `refuse()` (missing/malformed pre-state, root set/order shrink) —
#            the helper wrote ONLY `REFUSE:` to STDERR, NO probe-log record.
# The warning must match the code (never claim a record that does not exist),
# and EITHER failure folds the wrapper result to non-success on an otherwise-
# successful child (the exit-census fold-in twin: a mandatory post-spawn
# escape record that did not land is never a silent success — the escape-check
# is a MUST-PAUSE safety gate).
python3 "$HELPER" escape-check --run "$LOOP_RUNKEY" --role "$LOOP_ROLE" \
    --capture post --leg "$LOOP_LEG" --log-root "$log_root" "${_rootargs[@]}" \
    ${_escargs[@]+"${_escargs[@]}"} >&8
esc_ec=$?
if [ "$esc_ec" -eq 3 ]; then
  echo "SPAWN_WARN check=escape-post detail=\"post-capture failed (exit 3) — the helper's refusal record naming the root is on the probe log; composer disposition\""
  [ "$ec" -eq 0 ] && ec=4
elif [ "$esc_ec" -ne 0 ]; then
  echo "SPAWN_WARN check=escape-post detail=\"post escape-check REFUSED (exit $esc_ec) — NO probe-log record was written (diagnostic on stderr); the mandatory post-spawn escape record is MISSING for this activation; composer disposition\""
  [ "$ec" -eq 0 ] && ec=4
fi
_post_ran=1
rm -f "$_prestate" 2>/dev/null

# --- DR-1 emission 4: the exit census record, via the helper ----------------
# R16 PR-MED-001: census failure emits the ADMITTED refusal shape (never a
# fabricated children=0) and folds an otherwise-successful child to
# non-success — unavailable evidence is never numerically indistinguishable
# from a clean census.
if [ "$census_ok" = "1" ]; then
  if ! python3 "$HELPER" emit OWNERSHIP:exit-census --run "$LOOP_RUNKEY" --role "$LOOP_ROLE" \
      "leg=$LOOP_LEG" "children=$children" >&8; then
    echo "SPAWN_WARN check=exit-census detail=\"exit-census emission failed (children=$children unrecorded)\""
  fi
  if [ "$children" -gt 0 ]; then
    echo "SPAWN_WARN check=exit-census detail=\"$children surviving process(es) in the child's pgid — composer disposition (never a wrapper kill)\""
  fi
else
  if ! python3 "$HELPER" emit OWNERSHIP:exit-census --run "$LOOP_RUNKEY" --role "$LOOP_ROLE" \
      "leg=$LOOP_LEG" refused=capture-failure "detail=census command failed; survivor count unconfirmed" >&8; then
    echo "SPAWN_WARN check=exit-census detail=\"census refusal record emission failed\""
  fi
  echo "SPAWN_WARN check=exit-census-capture detail=\"process census FAILED (ps/pipeline) — survivor count unconfirmed; composer classification required\""
  [ "$ec" -eq 0 ] && ec=4
fi

# --- session-id enrichment (DR-1): the wrapper NEVER parses the live stream —
# post-`wait` it MAY do a bounded read of the role-log FILE for the init
# event's session_id, enriching the identity FILE via a second atomic rename.
# The probe-log `IDENTITY: update` record stays helper-emitted at consume time
# by the composer (and the helper refuses a session-less IDENTITY record —
# F-01 closed by refusal).
if [ -n "${LOOP_IDENTITY_FILE:-}" ] && [ -f "$LOOP_ROLE_LOG" ]; then
  session_id="$(head -c 262144 "$LOOP_ROLE_LOG" 2>/dev/null | grep -o '"session_id":"[^"]*"' | head -n 1 | cut -d'"' -f4)"
  # R17 (executor-verified peer signal): the session_id is CHILD-CONTROLLED
  # bytes read LATE from the role log — the `[^"]*` grep class admits \r and
  # other C0 controls, so an unvalidated value forges an extra key=value line
  # in the identity file (the Constraint-13 class PR-HIGH-002 closed for the
  # START-line INPUTS, re-opened on this late-bound WRITE). Validate through
  # the same control-byte contract; on unsafe input SKIP the enrichment and
  # keep the input-derived identity (write_identity "" already ran pre-`wait`)
  # rather than writing a forged line — a completed run is never discarded for
  # a hostile session id. A real UUID/session id is never over-constrained.
  if [ -n "$session_id" ]; then
    if line_safe "$session_id"; then
      write_identity "$session_id"
    else
      echo "SPAWN_WARN check=session-id detail=\"child-reported session_id carries control bytes — enrichment SKIPPED (forged-identity-line lever; Constraint 13); input-derived identity retained\""
    fi
  fi
fi

# --- pump fold-in (Constraint 10: a pump failure still makes a successful
# child a non-success wrapper result, now via the waited pump directly) ------
case "$tee_status" in
  0) ;;  # pump confirmed clean
  timeout)
    echo "SPAWN_WARN check=role-pump detail=\"role-log tee did not drain within the bound (an orphan may hold the FIFO writer) — killed the wrapper's OWN tee; capture unconfirmed\""
    [ "$ec" -eq 0 ] && ec=4 ;;
  *)
    echo "SPAWN_WARN check=role-pump detail=\"role-log tee exited $tee_status — capture may be incomplete\""
    [ "$ec" -eq 0 ] && ec=4 ;;
esac
# Round-4 S-A leg 2: the ADDITIVE second trigger copy on the post-exit result
# surface (the pre-child copy above is the activation-accompanying signal).
echo "STICKY_REREAD run=$LOOP_RUNKEY role=$LOOP_ROLE detail=\"rehydrate: re-read STICKY.md + the plan's Current State / Handoff Note (Loop config: included) before consuming this spawn's result\""
exit "$ec"
