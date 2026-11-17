#!/usr/bin/env python3
"""The /execute-loop codex peer launcher (v34.1).

Runs ONE composer-seat codex peer round and writes that round's records
itself, through the records helper, in a fixed order. It replaces the per-run
hand-written peer script (`codex exec ... | tee`) and the composer's separate
helper calls for the start record, the escape-check pair, and the end record.

SEAT AND INVOCATION
  Run by the composer only, as exactly

      python3 -I scripts/loop-peer-launcher.py

  with no argument. Every parameter is a LOOP_* environment variable. It
  refuses a start that is not in Python's isolated mode. It is never granted
  to a spawned role.

TOPOLOGY IT SERVES
  A run with a run worktree: the tools and the logs on the base side, the peer
  in the worktree. The peer-writable roots are LOOP_CWD, the host's temp
  directory (/tmp on POSIX; the configured temp directory on Windows — v45.0),
  and TMPDIR (when set). After symlinks are resolved, each of these must lie outside
  every one of them: this script's directory (it holds both tools); the probe
  log and its folder; the peer log; the identity file; the interpreter and its
  standard library (sys.executable, sys.prefix, sys.base_prefix); the git the
  tools will run; and, under LOOP_ROUTE_BIN, the router command (ROUTER MODE
  below). Any other topology is refused (check=topology). A resolved
  peer-writable root of `/` contains every absolute path.
  What was checked is what is used: the log folder, the probe log (through
  its last component), the identity file, the interpreter, the git binary,
  and the tools' PATH entries are used in their resolved form, so a link
  sitting inside a peer-writable root - a path component, or a hop in the
  chain a final link follows - cannot be repointed while the peer runs. The
  resolved git's own directory leads the tools' PATH; a git that resolves to
  a file not named git cannot be pinned that way and is refused (check=git).

TOOLS
  It calls two tools found beside itself, each as `<this interpreter> -I
  <tool>`: loop-journal.py (the records helper) and loop-history-check.py (the
  round census). Before anything is written each must equal its committed copy
  (`git hash-object` against `HEAD:scripts/<name>`); the two blob ids are kept
  and ride the start record as tool_ids=. Immediately before each tool call
  made after codex was started, that tool is hashed again and compared with
  the kept id (never with HEAD). On a mismatch neither tool is called again.
  Every tool call (and this script's own git calls) gets this process's
  environment with PATH rebuilt: an entry that is relative, or that resolves
  inside a peer-writable root, is dropped; git must be found on what is left.
  Nothing is spawned through a shell.
  v45.0 (D15 / D30): the helper is ALSO this launcher's runtime — once the two
  tools are verified, the helper is copied into a private snapshot directory
  in the probe log's folder (base side — never a peer-writable root; removed
  as soon as the import returns),
  the copy re-verified against the pinned id and imported (route_collect, the
  folder rule, the second note's sanitizer, the process-group / Job primitive,
  canon_path / path_inside); the checkout copy is never imported, and the
  helper's CLI keeps running from the checkout under the hash gate above.
  The child's process group is the runtime's (a new session on POSIX; a Job
  Object on Windows, where SIGHUP, SIGCHLD, os.killpg and os.getuid do not
  exist — the stop ladder, the group check and the owner check speak to the
  handle). Standard output and error are UTF-8 + LF at this entrypoint.

PARAMETERS (environment only)
  Required:
    LOOP_CODEX_BIN      absolute path; resolved, an executable regular file
    LOOP_CWD            absolute path of an existing directory (the run
                        worktree): the child's working directory and -C value
    LOOP_PROBE_LOG      absolute path of the phase's probe log (an existing
                        regular file); its folder is the escape --log-root
    LOOP_PEER_LOG       absolute path; its folder exists; absent or a regular
                        file. codex's stdout and stderr are appended to it
    LOOP_IDENTITY_FILE  absolute path that must not exist (fresh per launch)
    LOOP_PROMPT_FILE    absolute path of a regular file holding at least one
                        non-whitespace character; opened once - that open file
                        is the child's stdin
    LOOP_PLAN           absolute path of the plan file; resolved, inside
                        LOOP_CWD
    LOOP_RUNKEY         the phase-scoped run key
    LOOP_PHASE          the phase identity (phase=)
    LOOP_LEG            the activation's leg key, fresh per launch: a leg the
                        probe log already holds a ROLE: start for under this
                        run key is refused
    LOOP_MODEL          the -m value and model=; [A-Za-z0-9][A-Za-z0-9._-]{0,63}
    LOOP_ESCAPE_ROOTS   base=/abs[;<name>=/abs...] - one --root per member
    LOOP_PASS, LOOP_PEER_ROUND, LOOP_CAP   the pass keys, all three
  Optional (set but empty counts as unset):
    LOOP_EFFORT         -c model_reasoning_effort=<value> and effort=;
                        [a-z]{1,12}
    LOOP_ALLOW_PATH, LOOP_ISO, LOOP_LIVENESS   passed to both escape captures
    LOOP_ROUTE_BIN      v41.0 router mode (D8): absolute path of
                        claude-switch-route; resolved, an executable regular
                        file whose resolved path holds no control character;
                        outside every peer-writable root; requires LOOP_ISO;
                        routes the round (ROUTER MODE below). With it set, the
                        inherited CODEX_HOME - or HOME when CODEX_HOME is unset
                        - must hold no newline or control character (the
                        identity record carries the effective home); one of the
                        two must be set
  Must not be set:
    LOOP_EDIT_SURFACE   a peer declares no edit surface
  Every rule the helper owns (run-key form, pass-key forms and sequencing, the
  roots grammar, record-value safety) stays the helper's: the value is passed
  through and a helper refusal is this launcher's refusal. A refusal names the
  variable and the rule; it never prints the value.

OUTPUT PATHS ARE KEPT APART
  The launcher writes the peer log, the identity file, and the identity
  file's temporary name (<identity file>.tmp). With folders resolved, each
  must differ from the other two and from: the probe log, the plan, the prompt
  file, the launch's escape pre-state path (<log folder>/<runkey>-escape-
  <leg>.pre), this script, the two tools, the interpreter, the git binary, and
  the codex binary. An existing peer log must have a link count of 1. The
  temporary name must not exist. A collision is refused before the pre capture
  and before any file is opened for writing.
  It also creates, per launch (v42.0 D8), the child's private runtime
  directory <TMPDIR, else /tmp>/loop-peer-xdg.<random> (mode 0700, mkdtemp's
  default) - a write under a peer-writable root BY DESIGN (the topology rule
  checks the tools and the logs, never this dir) - exported to the child as
  XDG_RUNTIME_DIR and removed once the child and its group are gone (the
  could-not-start path included): the removal restores owner permissions on
  the tree's OWNED, non-symlink directories a child left unreadable or
  unwritable and retries (never following a link, never another owner's
  mode); a tree that still cannot be removed is REPORTED on standard error
  (`the runtime dir could not be removed (<reason>) - left at <path>`),
  never claimed removed (round 13 PR-MED-021); a runtime dir the child
  REPLACED with a symlink or a file is never walked or chmodded through -
  the bare entry is unlinked and the replacement noted (`the runtime dir was
  replaced by a <symlink|non-directory> - the entry unlinked, nothing
  followed`; round 29 PR-MED-001). It is allocated inside step 5's
  could-not-start boundary, after the keyed start: an allocation failure (a
  missing, unwritable, or full TMPDIR) starts no child, notes `the runtime
  dir could not be created (<error class>) - treated as exit code 127`, and
  runs steps 6-10 exactly as a codex that could not be started does.
  XDG_CONFIG_HOME and XDG_CACHE_HOME are NOT redirected (git reads the
  operator's config from the former).

THE CHILD
  <LOOP_CODEX_BIN> exec -s workspace-write -m <model>
      [-c model_reasoning_effort=<effort>] -C <LOOP_CWD>
  stdin: the prompt file. stdout and stderr: appended to the peer log.
  Environment: this process's, minus every variable whose name starts with
  LOOP_, CLAUDE_CODE_OAUTH_TOKEN, or ANTHROPIC_ - plus CODEX_HOME=<the
  router's answer> when the pick of ROUTER MODE was honoured, plus
  XDG_RUNTIME_DIR=<the private per-launch directory of OUTPUT PATHS> (v42.0
  D8 - a writable runtime dir inside codex's workspace-write sandbox). It
  runs in its own session, so it and whatever it starts form one process
  group. No time limit.
  v48.0 (D12 - the composer seat): LOOP_SEAT, a watcher takeover's nonce, is
  one of those LOOP_ variables and so never reaches the peer; and before the
  launcher opens a file of its own it closes every descriptor above 2 that
  it inherited (close_inherited_fds - POSIX; a Windows child inherits none),
  so a takeover's seat lock is never kept open by this process. The
  launcher's OWN records ride --role peer and are never gated by the seat.

ROUTER MODE (v41.0, LOOP_ROUTE_BIN - the plan's D8; the answer rule is D3's)
  Set, the launcher asks claude-switch-gui's account router which logged-in
  codex home this round runs under - after the pre escape capture and before
  the keyed start, as

      <resolved LOOP_ROUTE_BIN> pick --agent=codex --run=<LOOP_ISO> --role=peer
          --phase=<LOOP_PHASE> --model=<LOOP_MODEL> --pid=<this process>
          --label=<the base checkout's folder name> --json

  (every value as --flag=value, byte for byte from the variables that feed
  the start record; the router runs with the tools' PATH, on which python3
  must be found - absent, the pick is not attempted). The call goes through
  the COLLECTOR — v45.0: the ONE implementation in the records helper's
  runtime (`route_collect`), imported from the verified snapshot, the same
  procedure the Python spawn wrapper runs:
  the router in its own session with stdin from the null device and every
  other descriptor closed; both pipes drained concurrently, at most 4096 bytes
  of each retained and the rest discarded (a producer never blocks on a full
  pipe; NO file-size limit is ever placed on the router - its own lease-store
  writes stay free); a stream past the cap ends the router's process group at
  once -> overflow; a 20 s deadline -> SIGTERM on the group, a 2 s grace,
  SIGKILL, reap -> timeout; after the leader exits the readers get 1 s to reach
  EOF, then the group is killed (a descendant holding a pipe) and both readers
  are joined under one further grace; the cleanup follows the terminal
  condition, so an over-cap or expired call ends the group even when the
  leader has already exited and the readers are at EOF. A signal this
  launcher's handler records during the pick (TERM / INT / HUP) is a terminal
  condition too: the group ended at once - never at the router's natural end
  - the verdict other, the launch then refused (check=signal); and the group
  is SWEPT at every return, success included, so a quiet same-group
  descendant of an exited leader never outlives the collector (PR-MED-036).
  The group's IDENTITY is held through all of it (PR-MED-037): the leader's
  exit is OBSERVED (waitid / WNOWAIT), never reaped, until the last group
  signal, so every killpg names a number the zombie leader still reserves;
  the ONE reap follows the sweep and releases the identity, and nothing is
  signalled after it (the exception boundary included); on a python3 without
  os.waitid (CPython on macOS) NO router is started - the pick is not
  attempted, no answer (other), the inherited environment stands (round 38
  PR-MED-038: never a reaping observation on any routed path); the rule's
  prerequisite is ESTABLISHED, not assumed (round 39 PR-MED-041): the launcher
  sets the default SIGCHLD disposition before the pick (an inherited SIG_IGN
  would have the kernel reap the exited leader at once) and RESTORES its entry
  disposition once the router is released, before the keyed start, so the
  codex role child and every later helper child inherit exactly what the
  launcher inherited - with routing on, skipped, or off (round 40 PR-LOW-017:
  the normalisation is scoped to the router window; on a SIG_IGN entry the
  role child's status is then Popen's fabricated 0, the pre-v41 contract), and
  an ECHILD from the observation is a LOST reservation - released on the
  spot, nothing signalled through that number from any site (the reader-grace
  kill and the sweep included), the verdict other (the exit status is
  unknowable).
  THE ANSWER RULE: exit 0 and one JSON object with route_schema an integer
  (not a boolean) equal to 1, dir a string, sticky a boolean; dir absolute,
  no control character (a lone surrogate the decoder admits counts as one),
  no double quote, no non-space Unicode whitespace (round 13 PR-MED-019/020
  - so every honoured folder satisfies the records helper's value rule and
  the composer can journal it); the folder exists, is owned by this
  user, is not group- or world-writable, resolves to a clean physical path
  (no control character - realpath is byte-exact), and lies outside every
  peer-writable root. Honoured: CODEX_HOME=<dir> (the literal dir, never
  resolved) in the child's environment; a note on standard error names it and
  via=pick|binding (binding when sticky is true).
  NO ANSWER (never fatal - the contract's caller rule; the inherited
  environment stands and a note names the word): exit 3 -> the first stderr
  line, one of the contract's eleven words (anything else -> other); exit 2
  -> usage; the deadline -> timeout; a stream past the cap -> overflow; empty
  or non-JSON output -> bad-json; another schema -> bad-schema; a folder that
  does not exist -> no-dir; one failing another folder check -> bad-dir;
  any other exit, a signal, a router that could not start, or any failure of
  the collector's own after the router is live (its group ended first - one
  ownership boundary from the spawn to the verdict) -> other.
  THE TWO NOTES (v42.0 D5/D9): the no-answer note `router: no answer (<word>)
  - the inherited environment stands (stdout_bytes=<n> stderr_bytes=<n>)` is
  unchanged; when the router printed anything AFTER its reason word, or the
  folder check failed, a SECOND note follows at once: `router: skipped -
  <text>` - the router's stderr after its first line (a diagnosing router's
  per-candidate `<dir> <reason>` lines, joined `; `), or the folder rule's
  own `<dir> <check>` (`relative` / `quote` / `control-byte` /
  `unicode-space` from the shape rule; `no-dir`, `not-owned`, `group-writable`, `world-writable`,
  `unresolvable`, `inside-root` from the folder checks - the same check words
  the wrapper prints) - sanitized under the records helper's value rule
  (check_value_safety: every control character, `"`, and non-space Unicode
  whitespace -> a space, whitespace runs collapsed) and capped at 512 bytes:
  the ONE rule, stated in full in the spawn wrapper's usage header
  (LOOP_ROUTE_BIN) and implemented by the runtime's route_skipped_text()
  (ROUTE_SKIP_CAP = 512 in the helper; v45.0). The second note is
  absent when there is nothing to say (today's router prints no further
  line). The composer journals both notes as `ADOPT:`.
  THE IDENTITY FILE on every launch made with LOOP_ROUTE_BIN set (both
  constructions, the closing-mark fallback included) gains codex_home=<the
  EFFECTIVE home> - the router's literal dir, else the inherited CODEX_HOME
  verbatim (never resolved; a relative value as it is), else <HOME>/.codex -
  plus route_run=<LOOP_ISO> and route_phase=<LOOP_PHASE>. The inherited value
  and the HOME-derived default are admitted only when they hold no newline or
  control character; otherwise the launch is refused (check=param) before
  anything is written. Without LOOP_ROUTE_BIN none of this runs and the
  identity file is unchanged. Refusals (exit 2, the probe log unchanged):
  LOOP_ROUTE_BIN relative, holding a control character, not resolving to an
  executable regular file, or resolving to a path with a control character
  (check=param); set without LOOP_ISO (check=param); a peer-writable root
  (LOOP_CWD, /tmp, TMPDIR) resolving to a path with a control character
  (check=param - the roots the containment comparison consumes are clean
  physical paths too); resolving inside a peer-writable root
  (check=topology); an output path equal to the resolved router
  (check=output-path). A signal that arrives during the pick refuses
  the launch as one before the start does; a binding the router saved is
  harmless - the next ask reuses it and the run's final close releases it.

ORDER OF OPERATIONS
   1. Refuse any argument and a non-isolated start; check the parameters, the
      topology, and the output paths; verify the two tools.
   2. Baseline: `loop-history-check.py --round-census <plan>` -> findings_max.
   3. Pre escape capture (a pre-state file in the log folder; no record).
      Under LOOP_ROUTE_BIN, then the router's pick (ROUTER MODE) - no record.
   4. The keyed start, through the helper: ROLE: start ... backend=codex
      via=launcher baseline=<N> tool_ids=<helper id>,<checker id> pass=
      peer_round= cap=. Helper exit 0: written. Exit 2: refused before any
      write - the pre-state is discarded and the launch is refused. Anything
      else: the start may or may not be in the log - nothing is started, the
      pre-state is kept, start=uncertain, exit 1.
   5. Create the child's runtime dir (OUTPUT PATHS; v42.0 D8), start codex;
      write the identity file (ts= run= role= leg= launcher_pid= codex_pid=
      pgid= cwd= model=, plus codex_home= route_run= route_phase= under
      LOOP_ROUTE_BIN; a temporary file renamed into place); print
      PEER_LAUNCH_START; wait for the child.
   6. Child reaped: stop anything left in its process group (SIGTERM, a
      bounded wait, SIGKILL); remove the runtime dir. From here on SIGTERM,
      SIGINT, and SIGHUP are ignored. Rewrite the identity file with two more
      lines: tokens=<total|unknown> (PEER TOKENS below; v47.0), then
      closing=<ts> - the closing mark, the file's last line. If the mark
      cannot be written, no tool is called again: go to step 10.
   7. Post escape capture with --log: the one OWNERSHIP: escape-check record.
   8. `loop-history-check.py --expect-new-round-since <N> <plan>`.
   9. The end, through the helper: ROLE: end result="<below>" leg= duration=.
  10. Print PEER_LAUNCH_EXIT and exit.
  Steps 1-3 failing, and a helper refusal at step 4, leave the probe log
  unchanged. Once the start is written, steps 6-10 are always attempted. This
  script appends nothing to the probe log itself: every record is the
  helper's. An exit code is never read as proof of a record.

PEER TOKENS (v47.0; plan-loop-autonomy-group-2 D21)
  codex prints its token total for a run as two lines - a line that is
  exactly `tokens used`, then a line holding the number, such as `85,548` -
  and then repeats its final message. After the child is reaped and step 6
  has dealt with its group (a census that could not be read is the unknown
  case below; the read does not depend on every member being gone - it is
  bounded), the launcher reads the bytes THIS leg
  appended to the peer log (from the log's size just before the spawn - an
  existing peer log's earlier legs are never read) and takes the LAST such
  pair: a line that is `tokens used` (nothing before it; trailing blanks
  ignored) directly followed by a line that is a number - digits only, or
  digits in comma-separated groups of three (`548`, `85548`, `85,548`), at
  most 18 digits - each of the two lines ended by a newline. The step-6
  rewrite writes it as tokens=<the digits, commas removed> directly before
  closing=. It writes tokens=unknown instead when the leg's bytes hold no
  such pair (a heading followed by anything else is not one), when codex
  was not started, when the survivor census is unknown (the leg's bytes are
  not known to be complete; nothing is read), when the leg's bytes exceed
  64 MiB (nothing is scanned), or when the peer log could not be read or is
  no longer a regular file (it is opened without blocking). The read is
  BOUNDED: the log's size is taken once, from the opened descriptor, and no
  byte past it is read - a process still appending to the log can never
  keep the launcher from its closing mark - and a line that size cuts short
  has no newline, so it is never taken for a number. /retro reads the
  line. It is a reading of what codex printed, not a measurement: a final
  message that itself holds such a pair on two lines of its own, after the
  real one, is taken for the total. A line longer than 4096 bytes (its
  newline counted) is never part of a pair. No status line, no record and
  no exit code carries or depends on it, and an identity file closed by the
  composer's clean close (the launcher died first) has no tokens= line.

THE END'S result=
  round check exit 0 with `NEW-ROUND OK: findings_max=<M>` -> exit <rc>; new round <M>
  a violation line starting NO-NEW-ROUND:                 -> inconclusive: exit <rc>; no new round
  anything else                                           -> inconclusive: exit <rc>; census failed
  When this launcher stopped the child on a signal and no new round landed,
  the string is prefixed `incomplete: stopped by <signal name>; `. <rc> is
  codex's exit code; a child ended by a signal is 128 + the signal number; a
  child that could not be started is 127. duration= is whole seconds from
  just before the spawn to the child's exit.

SIGNALS (SIGTERM, SIGINT, SIGHUP)
  Handlers are installed before step 3; a signal that arrives while a tool
  call is in flight is acted on when that call returns. Before the start is
  written: the pre-state, if taken, is discarded and the launch is refused.
  After the start and before the spawn: the spawn is skipped (127) and steps
  6-10 run. While codex runs: the child's process group gets SIGTERM, a
  bounded wait, then SIGKILL, and steps 6-10 run. During steps 6-10: ignored.

STANDARD OUTPUT - exactly these line shapes, nothing else
  PEER_LAUNCH_REFUSED check=<token> detail="<text>"
  PEER_LAUNCH_START leg=<leg> pass=<pass> peer_round=<k> cap=<n> baseline=<N> pid=<pid> pgid=<pgid> peer_log=<path>
  PEER_LAUNCH_EXIT rc=<codex rc|none> start=<written|uncertain> round=<new:<M>|none|unknown> escape=<helper exit code|none> end=<written|failed|none> group=<clean|killed|none> tools=<ok|changed> duration=<s> leg=<leg>
  Each is flushed as printed. After the start is written a failed print is
  ignored. codex's output goes to the peer log only; the tools' own output is
  forwarded to standard error.
  check= is one of: argv, isolated, param, leg, git, topology, output-path,
  tools, baseline, escape-pre, start, signal.

EXIT CODES
  0  codex exited 0, a new round was appended, the post capture's helper exit
     was 0, the end call exited 0, and the tools were unchanged
  2  refused; the probe log is unchanged
  1  anything else
"""

import datetime
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
# kept as ONE bare line (v45.0): the fault-injection selftest patches anchor on it
import threading
import time

SELF_CMD = "python3 -I scripts/loop-peer-launcher.py"
HELPER_NAME = "loop-journal.py"
CHECKER_NAME = "loop-history-check.py"

MODEL_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
EFFORT_RE = re.compile(r"\A[a-z]{1,12}\Z")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
BLOB_ID_RE = re.compile(r"\A[0-9a-f]{40,64}\Z")
CENSUS_RE = re.compile(
    r"\AROUND-CENSUS plan=.* findings_max=(\d+) history_max=\d+ history_rounds=\d+ findings_rounds=\d+\Z")
NEW_ROUND_RE = re.compile(r"\ANEW-ROUND OK: findings_max=(\d+) > baseline=\d+\Z")
NO_NEW_ROUND_RE = re.compile(r"\A\s+NO-NEW-ROUND:")

# The bounded wait between SIGTERM and SIGKILL when a process group is stopped.
STOP_GRACE_S = 5.0
WAIT_POLL_S = 0.2

# Router mode (v41.0 D8): the collector's caps and the contract's no-answer
# words live in the helper's runtime (ROUTE_CAP / ROUTE_DEADLINE / ROUTE_GRACE /
# ROUTE_READER_GRACE / ROUTE_WORDS / ROUTE_SKIP_CAP) - ONE list, imported from
# the verified snapshot (v45.0 D15; the selftests pin the launcher's use to it).

# The catchable stop signals THIS host provides: SIGHUP is absent on Windows
# (v45.0 T2.5); SIGBREAK, where it exists, is not a stop request to a peer.
SIGNALS = tuple(s for s in (getattr(signal, n, None) for n in ("SIGTERM", "SIGINT", "SIGHUP")) if s is not None)
PENDING = []  # the signals received, in arrival order (handler-appended)


# --- output -------------------------------------------------------------------

def ensure_std_fds():
    """A closed fd 0/1/2 would be handed to the next file this script opens.
    Point any closed one at the null device before anything else is opened."""
    for fd in (0, 1, 2):
        try:
            os.fstat(fd)
        except OSError:
            try:
                os.open(os.devnull, os.O_RDWR)
            except OSError:
                pass


def close_inherited_fds():
    """v48.0 (D12): every descriptor above 2 this process inherited is closed
    before the launcher opens one of its own - so nothing a caller held open
    (a watcher takeover's seat lock among them) is kept for the round's life
    by this process. The spawn wrapper does the same. POSIX only: a Windows
    child inherits no descriptor beside its three standard handles. The open
    descriptors are listed where the host has a listing (/proc/self/fd,
    /dev/fd); otherwise the range up to the soft limit (capped) is closed."""
    if os.name == "nt":
        return
    for listing in ("/proc/self/fd", "/dev/fd"):
        try:
            names = os.listdir(listing)
        except OSError:
            continue
        for name in names:
            if name.isdigit() and int(name) > 2:
                try:
                    os.close(int(name))
                except OSError:
                    pass                 # the listing's own descriptor, already closed
        return
    try:
        import resource
        limit = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
    except (ImportError, OSError, ValueError):
        limit = 1024
    os.closerange(3, max(3, min(limit if limit > 0 else 1024, 65536)))


def say(line):
    """Print one status line, flushed. Best effort: a closed or broken standard
    output never stops a step and never changes the exit code."""
    out = sys.stdout
    if out is None:
        return
    try:
        out.write(line + "\n")
        out.flush()
    except (OSError, ValueError):
        # Python flushes standard output again at exit; a still-broken stream
        # would turn that into exit 120. Point fd 1 at the null device.
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 1)
            os.close(devnull)
        except OSError:
            pass


def note(text):
    """A diagnostic on standard error, best effort."""
    err = sys.stderr
    if err is None:
        return
    try:
        err.write("loop-peer-launcher: %s\n" % text)
        err.flush()
    except (OSError, ValueError):
        pass


def forward(data):
    """Forward a tool's captured output to standard error, best effort."""
    if not data:
        return
    err = sys.stderr
    if err is None:
        return
    try:
        err.write(data.decode("utf-8", "replace"))
        err.flush()
    except (OSError, ValueError):
        pass


def refuse(check, detail):
    say('PEER_LAUNCH_REFUSED check=%s detail="%s"' % (check, detail))
    sys.exit(2)


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


# --- paths --------------------------------------------------------------------

def _spell(path):
    """The launcher's BOOT twin of the runtime's spelling form (v45.0 D17 /
    D30 / D31; round 29 PR-MED-001 — the whole form, as canon_path(p,
    resolve=False)): identity on POSIX; on a Windows host `\\` -> `/`, a UNC
    spelling refused by name, the MSYS `/c/...` -> `C:/` conversion under
    MSYSTEM (no subprocess), any other `/`-rooted spelling refused by name,
    an upper-case drive letter — so every canonical value below is
    `C:/...`-spelled and the `/`-separator predicate `inside()` matches it.
    No normpath. Pinned equal to the runtime's by the selftests' shared
    case table."""
    if not _WINDOWS:
        return path
    s = path.replace("\\", "/")
    if s.startswith("//"):
        refuse("param", "path %s is a UNC spelling - the loop's canonical spelling is a drive path (`C:/...`); a UNC share is refused by name (path-rule)" % path[:120])
    m = re.match(r"\A/([A-Za-z])(/|\Z)", s)
    if m and os.environ.get("MSYSTEM"):
        s = m.group(1).upper() + ":/" + s[len(m.group(0)):]
    elif s.startswith("/"):
        refuse("param", "path %s is a `/`-rooted spelling on a Windows-native host - spell it as a drive path (`C:/...`)%s"
               % (path[:120], "" if os.environ.get("MSYSTEM") else " (the MSYS `/c/...` form converts under MSYSTEM only)"))
    if len(s) >= 2 and s[1] == ":" and s[0].isalpha():
        s = s[0].upper() + s[1:]
    return s


def _absolute(spelled):
    """Absolute in the CANONICAL spelling, by the host flag (never
    os.path.isabs, the running interpreter's flavour): a drive-rooted `X:/...`
    on a Windows host, a `/`-rooted path elsewhere (round 29 PR-MED-001)."""
    if _WINDOWS:
        return re.match(r"\A[A-Za-z]:/", spelled) is not None
    return spelled.startswith("/")


def real(path):
    return _spell(os.path.realpath(path))


def real_in_folder(path):
    """The path with its folder resolved and its last component kept."""
    return _spell(os.path.join(os.path.realpath(os.path.dirname(path)), os.path.basename(path)))


def inside(path, root):
    """True when the resolved `path` is `root` or lies beneath it — the
    launcher's BOOT twin of the runtime's path_inside (v45.0 T1.3 / T2.5,
    PR-MED-001 round 4): `/` is the separator on every host, never os.sep (`\\`
    on Windows would never prefix-match a `C:/...` value). A root of `/` (or a
    drive root `C:/`) yields itself as the prefix, so it contains every
    absolute path (the filesystem-root boundary case). Kept launcher-local
    because the plan admission and the topology refusal run BEFORE the tools
    verification and the runtime import; pinned equal to the runtime's by the
    selftests' shared case table."""
    if path == root:
        return True
    prefix = root if root.endswith("/") else root + "/"
    return path.startswith(prefix)


_WINDOWS = os.name == "nt"   # the host flag the selftest flips on the imported module (T2.6)
GIT_NAMES_WINDOWS = frozenset(("git.exe", "git"))
GIT_NAMES_POSIX = frozenset(("git",))


def git_admitted(basename):
    """The git basenames the tools' PATH may be pinned to (v45.0 T2.5;
    PR-HIGH-001 round 1): `git` on POSIX; `git.exe` or `git` on Windows."""
    return basename in (GIT_NAMES_WINDOWS if _WINDOWS else GIT_NAMES_POSIX)


def _host_tmp():
    """The host's default temp directory as a peer-writable root (v45.0 T2.5):
    `/tmp` on POSIX (tempfile.gettempdir() would follow TMPDIR, which is its
    own root), tempfile.gettempdir() on Windows (there is no /tmp)."""
    if _WINDOWS:
        return tempfile.gettempdir()
    return "/tmp"


def _owner_ok(st):
    """The owner check: st_uid against this user on POSIX; on Windows the
    POSIX uid model does not apply (always this user's — the launcher runs
    unprivileged in the operator's session) — v45.0 T2.5."""
    if _WINDOWS:
        return True
    return st.st_uid == os.getuid()


def _configure_std_streams():
    """UTF-8 + LF on the launcher's own text streams, at the executable
    boundary only (v45.0 T1.4 / T2.5; guarded, never through an imported
    module's main()): say() / note() / forward() write a non-ASCII admitted
    path (PEER_LAUNCH_START's peer_log=) intact under Windows Python's piped
    cp1252."""
    for name in ("stdout", "stderr"):
        s = getattr(sys, name, None)
        if s is None or not hasattr(s, "reconfigure"):
            continue
        try:
            s.reconfigure(encoding="utf-8", newline="\n")
        except Exception:
            pass


# --- router mode (v41.0 D8; v45.0 D15 / D30): the collector is the RUNTIME's ------
# The v41.0 launcher carried its own copy of the spawn wrapper's route collector
# (RouteStream / route_drain / route_leader_exited / route_end_group /
# route_shape / route_dir_word / route_skipped_text / route_collect). v45.0
# keeps ONE implementation, in scripts/loop-journal.py's runtime section
# (`route_collect`, `route_dir_word`, `route_skipped_text`, the constants
# ROUTE_WORDS / ROUTE_CAP / ROUTE_DEADLINE / ROUTE_GRACE / ROUTE_READER_GRACE /
# ROUTE_SKIP_CAP), imported here from the blob-verified SNAPSHOT of the helper
# once per invocation (runtime_import below) — the same bytes the tools
# verification pinned as tool_ids=. The notes this launcher prints from the
# collector's results (`router: pick honoured …`, `router: no answer (<word>)
# …`, `router: skipped - <text>` — the second note's text is the runtime's
# route_skipped_text(), ROUTE_SKIP_CAP = 512 bytes) are unchanged.

RT = [None]   # the imported runtime module, set by runtime_import()
RUNTIME_NAMES = ("route_collect", "route_dir_word", "route_skipped_text", "group_launch", "group_members",
                 "group_alive", "group_stop", "group_close", "canon_path", "path_inside", "ROUTE_WORDS")


def runtime_import(snapshot_path):
    """Import the runtime from the helper SNAPSHOT (D30) — never the checkout
    copy. Returns the module, or raises (the caller refuses check=tools)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("loop_journal_runtime", snapshot_path)
    module = importlib.util.module_from_spec(spec)
    # no bytecode beside the snapshot: a __pycache__ would outlive the one
    # file + one directory the snapshot owner removes
    saved = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = saved
    missing = [n for n in RUNTIME_NAMES if not hasattr(module, n)]
    if missing:
        raise RuntimeError("the helper lacks the v45.0 runtime: %s" % ", ".join(missing))
    RT[0] = module
    return module


# --- parameters ---------------------------------------------------------------

def req(name):
    value = os.environ.get(name, "")
    if value == "":
        refuse("param", "%s is required and is not set" % name)
    return value


def opt(name):
    value = os.environ.get(name, "")
    return value if value != "" else None


def req_path(name):
    """A required path parameter in the boot SPELLING (round 29 PR-MED-001):
    the control-byte check on the raw value, the spelling form applied
    (identity on POSIX), absoluteness judged on the spelled value by the host
    flag, and the SPELLED value returned to every consumer."""
    value = req(name)
    if CONTROL_RE.search(value):
        refuse("param", "%s holds a newline or control character" % name)
    value = _spell(value)
    if not _absolute(value):
        refuse("param", "%s must be an absolute path" % name)
    return value


def spell_roots(value):
    """LOOP_ESCAPE_ROOTS with the PATH half of each `name=path` member in the
    boot SPELLING (round 43 PR-MED-002): the helper judges a `--root` operand
    with the native isabs and no MSYS conversion, so a `/c/...` root — a
    spelling this launcher admits for every other path parameter — would be
    refused there. Identity on POSIX (the value is returned byte-for-byte). A
    member with no `=`, an empty path, or a control character is passed
    through untouched: the helper owns that refusal and its text."""
    members = []
    for member in value.split(";"):
        if "=" in member and not CONTROL_RE.search(member):
            name, path = member.split("=", 1)
            if path:
                member = "%s=%s" % (name, _spell(path))
        members.append(member)
    return ";".join(members)


def leg_has_start(probe_log, runkey, leg):
    """True when the probe log already holds a ROLE: start for this run key and
    leg, under any role."""
    with open(probe_log, "rb") as fh:
        data = fh.read()
    run_tokens = ("run=%s" % runkey, 'run="%s"' % runkey)
    leg_tokens = ("leg=%s" % leg, 'leg="%s"' % leg)
    for raw in data.split(b"\n"):
        line = raw.decode("utf-8", "replace")
        if not line.startswith("ROLE: start "):
            continue
        tokens = line.split(" ")
        if any(t in tokens for t in run_tokens) and any(t in tokens for t in leg_tokens):
            return True
    return False


# --- tools --------------------------------------------------------------------

def tools_path(roots):
    """PATH for every tool call: relative entries and entries that resolve
    inside a peer-writable root are dropped, and each kept entry is used in
    its resolved form (an entry that is a symlink sitting inside a
    peer-writable root could otherwise be repointed while the peer runs)."""
    kept = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry or not os.path.isabs(entry):
            continue
        native = os.path.realpath(entry)
        if _WINDOWS and native.replace("\\", "/").startswith("//"):
            # round 39 LOW-001: an entry on a UNC share (a literal one, or a mapped
            # network drive resolved to its share) is DROPPED like any entry the
            # tools must not use — _spell's UNC refusal is for a PARAMETER path,
            # never for a PATH entry the operator did not pass to this launch
            continue
        resolved = _spell(native)
        if any(inside(resolved, root) for root in roots):
            continue
        kept.append(resolved)
    return os.pathsep.join(kept)


def run_tool(argv, env):
    """Run one tool call with an argument list (never a shell). Returns
    (exit code, stdout bytes, stderr bytes); a call that could not be started
    is 127, and one ended by a signal is 128 + the signal number."""
    try:
        done = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=env)
    except OSError as e:
        return 127, b"", ("cannot run %s: %s\n" % (os.path.basename(argv[0]), e)).encode("utf-8", "replace")
    rc = done.returncode
    if rc < 0:
        rc = 128 - rc
    return rc, done.stdout, done.stderr


def blob_id(git, repo, path, env):
    """`git hash-object -- <path>` in `repo`, or None."""
    rc, out, _err = run_tool([git, "-C", repo, "hash-object", "--", path], env)
    value = out.decode("ascii", "replace").strip()
    if rc != 0 or not BLOB_ID_RE.match(value):
        return None
    return value


def committed_id(git, repo, name, env):
    """`git rev-parse HEAD:scripts/<name>` in `repo`, or None."""
    rc, out, _err = run_tool([git, "-C", repo, "rev-parse", "HEAD:scripts/%s" % name], env)
    value = out.decode("ascii", "replace").strip()
    if rc != 0 or not BLOB_ID_RE.match(value):
        return None
    return value


# --- the identity file --------------------------------------------------------

REPLACE_TRIES = 5          # v45.0 T2.5: os.replace onto a held-open destination (Windows PermissionError)
REPLACE_RETRY_S = 0.2      # is retried 5 x 200 ms, then refused with named text


def write_identity(path, lines):
    """Write the identity file whole: a temporary file renamed into place.
    Raises OSError when it cannot be written. A destination another process
    holds open (Windows: PermissionError from os.replace) is retried within a
    bound, then the failure is raised with its reason named."""
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        # newline="\n" (round 39 MED-001): the default would write CRLF on a Windows
        # host, and a value the composer copies out of this file would carry a CR
        with os.fdopen(fd, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as fh:
            fh.write("".join(line + "\n" for line in lines))
            fh.flush()
            os.fsync(fh.fileno())
        for attempt in range(REPLACE_TRIES):
            try:
                os.replace(tmp, path)
                break
            except PermissionError as e:
                if attempt == REPLACE_TRIES - 1:
                    raise PermissionError(e.errno, "the identity file is held open by another process - %d replace attempts over %.1f s refused" % (REPLACE_TRIES, REPLACE_TRIES * REPLACE_RETRY_S), path)
                time.sleep(REPLACE_RETRY_S)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# --- the peer's token total (v47.0 D21) -----------------------------------------

TOKENS_HEAD = b"tokens used"
TOKENS_TOTAL_RE = re.compile(rb"\A(?:[0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)\Z")
TOKENS_MAX_DIGITS = 18
TOKENS_LINE_CAP = 4096     # a longer line is read in pieces and is never part of a pair
TOKENS_SCAN_CAP = 67108864  # 64 MiB: a leg whose bytes exceed it is not scanned (round 16 PR-MED-023)


def peer_tokens(path, start):
    """The token total codex printed during THIS leg (PEER TOKENS in the usage
    text): the digits of the LAST `tokens used` / number pair among the bytes
    appended to the peer log from offset `start`, or "unknown" - no such pair,
    no offset, or a log that could not be read. Bounded memory: lines are read
    in pieces of at most TOKENS_LINE_CAP bytes, and only a line read whole AND
    ended by a newline counts as a heading or a number. Bounded WORK (round 16
    PR-MED-023): the log's size is taken ONCE, from the opened descriptor, and
    no byte past it is read - a writer still appending can never keep this
    read, which stands before the closing mark, from ending; a line the size
    cuts short has no newline and so is never taken for a number; a leg with
    more than TOKENS_SCAN_CAP bytes is `unknown` without a scan."""
    if start is None:
        return "unknown"
    total = None
    try:
        # opened non-blocking and judged on the OPENED descriptor: a path that is
        # no longer a regular file (a FIFO would park a plain open for good, and
        # this runs before the closing mark) reads `unknown`, never a wait
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOCTTY", 0) | getattr(os, "O_BINARY", 0))
        try:
            st = os.fstat(fd)
            left = st.st_size - start if stat.S_ISREG(st.st_mode) else None
        except OSError:
            left = None
        if left is None or left > TOKENS_SCAN_CAP:
            os.close(fd)
            return "unknown"
        with os.fdopen(fd, "rb") as fh:
            fh.seek(start)
            armed = False      # the previous whole line was the heading
            fresh = True       # the next piece starts a line
            while left > 0:
                piece = fh.readline(min(TOKENS_LINE_CAP, left))
                if not piece:
                    break
                left -= len(piece)
                ended = piece.endswith(b"\n")
                whole = fresh and ended
                fresh = ended
                if not whole:
                    armed = False
                    continue
                line = piece.rstrip(b" \t\r\n")
                if armed and TOKENS_TOTAL_RE.match(line):
                    digits = line.replace(b",", b"")
                    if len(digits) <= TOKENS_MAX_DIGITS:
                        total = digits.decode("ascii")
                armed = line == TOKENS_HEAD
    except OSError:
        return "unknown"
    return total if total is not None else "unknown"


# --- signals and the child's process group -------------------------------------

def on_signal(signum, _frame):
    PENDING.append(signum)


# v45.0 T2.5: the child's process group is the RUNTIME's group primitive (a new
# session on POSIX, a Job Object on Windows — the helper's group_launch /
# group_members / group_stop / group_close): os.killpg / os.getpgid / os.waitid
# have no Windows counterpart, so the stop ladder below speaks to the handle.

def census_members(handle):
    """The post-exit survivor census as a launcher-local READING (round 32
    PR-MED-002): the runtime's `group_members`, ONE bounded retry on None;
    `[]` gone, a non-empty list alive, None UNKNOWN — an unknown census is
    neither proof that a numeric group is still ours nor proof that cleanup
    completed, so the caller issues no stop on it and names it."""
    members = RT[0].group_members(handle)
    if members is None:
        time.sleep(0.2)
        members = RT[0].group_members(handle)
    return members


def stop_group(handle, kill=False):
    """TERM (or KILL) the whole group through the runtime: True when the stop
    was issued (a group already gone counts — the runtime swallows that);
    False, with ONE note naming the runtime's text, when the host REFUSED the
    termination (round 30 PR-MED-002: a failed TerminateJobObject is an error
    the runtime raises on purpose — never a silent "stopped")."""
    try:
        RT[0].group_stop(handle, kill=kill)
        return True
    except (OSError, ValueError) as e:
        note("the group could not be stopped (%s: %s) - the %s is unconfirmed" % (e.__class__.__name__, str(e)[:200], "kill" if kill else "stop"))
        return False


def remove_runtime_dir(path):
    """v42.0 D8 (round 13 PR-MED-021): remove the per-leg runtime dir a child
    may have left with unreadable or unwritable descendants (a sandboxed
    suite's permission fixture). Each pass restores OWNER permissions (0700)
    on the tree's directories that are this user's and not symlinks - never a
    link followed, never another owner's mode; a file needs no mode change to
    be unlinked, its parent's does - then removes the tree; up to eight
    passes (one unlistable level per pass). The ROOT is re-checked at every
    pass (round 29 PR-MED-001): a runtime dir the child REPLACED with a
    symlink or a file is never walked or chmodded through - os.walk would
    list a symlinked top's target, followlinks=False guarding child descent
    only - the bare entry is unlinked (the name this launcher created; a link
    is never followed) and the replacement noted; a directory reached through
    a swapped ancestor (its real path outside the root's) is never chmodded
    either. Returns None once the path is gone, else a one-line reason: the
    caller REPORTS it and never claims the removal."""
    real_root = [None]
    rt = RT[0]

    def restore(p):
        try:
            st = os.lstat(p)
        except OSError:
            return
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode) or not _owner_ok(st):
            return
        # round 29 PR-MED-001: inside the root's REAL tree only - a path whose
        # ancestor the child swapped for a link resolves elsewhere and is skipped
        # (v45.0 T2.5: both operands canonical, the runtime's containment predicate)
        rp = rt.canon_path(p)
        if real_root[0] is None or not rt.path_inside(rp, real_root[0]):
            return
        try:
            os.chmod(p, 0o700)
        except OSError:
            pass
    for _pass in range(8):
        try:
            top = os.lstat(path)
        except FileNotFoundError:
            return None
        except OSError as e:
            return "the runtime dir could not be inspected (%s)" % e.__class__.__name__
        if stat.S_ISLNK(top.st_mode) or not stat.S_ISDIR(top.st_mode):
            # round 29 PR-MED-001: the child replaced the launcher's directory -
            # never walk or chmod through it; remove the bare entry, follow nothing
            what = "symlink" if stat.S_ISLNK(top.st_mode) else "non-directory"
            note("the runtime dir was replaced by a %s - the entry unlinked, nothing followed" % what)
            try:
                os.unlink(path)
            except OSError:
                pass
            return None if not os.path.lexists(path) else "replaced by a %s that could not be unlinked" % what
        if not _owner_ok(top):
            return "the runtime dir is no longer this user's"
        real_root[0] = rt.canon_path(path)
        restore(path)
        for root, dirs, _files in os.walk(path, topdown=True, followlinks=False,
                                          onerror=lambda e: restore(getattr(e, "filename", None) or "")):
            for d in dirs:
                restore(os.path.join(root, d))
        shutil.rmtree(path, ignore_errors=True)
        if not os.path.lexists(path):
            return None
    return "a descendant could not be removed after eight passes"


def wait_group_state(handle, seconds):
    """round 33 PR-MED-002: the post-TERM wait as a READING — `gone` ([] seen),
    `alive` (members still listed at the deadline), `unknown` (the census
    answered None twice in a row, 0.2 s apart) — so the escalation to KILL
    rests on an observed survivor, never on failed observations after TERM
    may already have emptied the group."""
    deadline = time.monotonic() + seconds
    while True:
        members = RT[0].group_members(handle)
        if members is None:
            time.sleep(0.2)
            members = RT[0].group_members(handle)
            if members is None:
                return "unknown"
        if not members:
            return "gone"
        if time.monotonic() >= deadline:
            return "alive"
        time.sleep(0.05)


# --- main ---------------------------------------------------------------------

def main():
    ensure_std_fds()
    close_inherited_fds()
    _configure_std_streams()

    # ---- step 1: argument, isolated start, parameters, topology, tools ----
    if len(sys.argv) > 1:
        refuse("argv", "the launcher takes no argument - every parameter is a LOOP_* environment variable")
    if not sys.flags.isolated:
        refuse("isolated", "the launcher runs only in Python's isolated mode - start it as: %s" % SELF_CMD)

    codex_bin = req_path("LOOP_CODEX_BIN")
    cwd = req_path("LOOP_CWD")
    probe_log = req_path("LOOP_PROBE_LOG")
    peer_log = req_path("LOOP_PEER_LOG")
    identity_file = req_path("LOOP_IDENTITY_FILE")
    prompt_file = req_path("LOOP_PROMPT_FILE")
    plan = req_path("LOOP_PLAN")
    runkey = req("LOOP_RUNKEY")
    phase = req("LOOP_PHASE")
    leg = req("LOOP_LEG")
    model = req("LOOP_MODEL")
    escape_roots = spell_roots(req("LOOP_ESCAPE_ROOTS"))   # round 43 PR-MED-002: the spelled members reach the helper
    pass_key = req("LOOP_PASS")
    peer_round = req("LOOP_PEER_ROUND")
    cap = req("LOOP_CAP")
    effort = opt("LOOP_EFFORT")
    allow_path = opt("LOOP_ALLOW_PATH")
    iso = opt("LOOP_ISO")
    liveness = opt("LOOP_LIVENESS")
    route_bin = opt("LOOP_ROUTE_BIN")
    if opt("LOOP_EDIT_SURFACE") is not None:
        refuse("param", "LOOP_EDIT_SURFACE must not be set - a peer declares no edit surface")

    # Router mode (v41.0 D8): the selector's parameter contract. The literal
    # path is held to the LOOP_CODEX_BIN shape (absolute, no control character,
    # resolving to an executable regular file); the RESOLVED path must hold no
    # control character either (fail closed - the containment comparison below
    # is only ever made between clean physical paths); LOOP_ISO is required
    # (the router's --run is this run's iso-id); the effective home the
    # identity record will carry is admitted here, before anything is written.
    route_real_path = None
    inherited_home = None
    if route_bin is not None:
        if CONTROL_RE.search(route_bin):
            refuse("param", "LOOP_ROUTE_BIN holds a newline or control character")
        route_bin = _spell(route_bin)   # round 29 PR-MED-001: the same spelling policy as req_path
        if not _absolute(route_bin):
            refuse("param", "LOOP_ROUTE_BIN must be an absolute path")
        if iso is None:
            refuse("param", "LOOP_ROUTE_BIN requires LOOP_ISO - the router's --run is this run's iso-id, unique per run; a run without one is not routable")
        route_real_path = real(route_bin)
        if not os.path.isfile(route_real_path) or not os.access(route_real_path, os.X_OK):
            refuse("param", "LOOP_ROUTE_BIN must resolve to an executable regular file")
        if CONTROL_RE.search(route_real_path):
            refuse("param", "LOOP_ROUTE_BIN resolves to a path holding a newline or control character - a selector the topology rule cannot compare byte-exactly is never run")
        if "CODEX_HOME" in os.environ:
            inherited_home = os.environ["CODEX_HOME"]
            if CONTROL_RE.search(inherited_home):
                refuse("param", "CODEX_HOME holds a newline or control character - under LOOP_ROUTE_BIN the identity record carries the effective codex home and cannot represent it")
        elif "HOME" in os.environ:
            inherited_home = os.path.join(os.environ["HOME"], ".codex")
            if CONTROL_RE.search(inherited_home):
                refuse("param", "HOME holds a newline or control character - under LOOP_ROUTE_BIN with CODEX_HOME unset the identity record carries <HOME>/.codex and cannot represent it")
        else:
            refuse("param", "neither CODEX_HOME nor HOME is set - under LOOP_ROUTE_BIN the identity record carries the effective codex home and cannot name it")

    if not MODEL_RE.match(model):
        refuse("param", "LOOP_MODEL must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    if effort is not None and not EFFORT_RE.match(effort):
        refuse("param", "LOOP_EFFORT must match [a-z]{1,12}")

    codex_real = real(codex_bin)
    if not os.path.isfile(codex_real) or not os.access(codex_real, os.X_OK):
        refuse("param", "LOOP_CODEX_BIN must resolve to an executable regular file")
    if not os.path.isdir(cwd):
        refuse("param", "LOOP_CWD must be an existing directory")
    if not os.path.isfile(probe_log):
        refuse("param", "LOOP_PROBE_LOG must be an existing regular file")
    log_folder = os.path.dirname(probe_log)
    if not os.path.isdir(os.path.dirname(peer_log)):
        refuse("param", "LOOP_PEER_LOG must sit in an existing folder")
    peer_log_exists = os.path.lexists(peer_log)
    if peer_log_exists and not os.path.isfile(peer_log):
        refuse("param", "LOOP_PEER_LOG must be absent or a regular file")
    if os.path.lexists(identity_file):
        refuse("param", "LOOP_IDENTITY_FILE must not exist - a fresh path per launch")
    if not os.path.isdir(os.path.dirname(identity_file)):
        refuse("param", "LOOP_IDENTITY_FILE must sit in an existing folder")
    if not os.path.isfile(plan):
        refuse("param", "LOOP_PLAN must be an existing regular file")
    cwd_real = real(cwd)
    plan_real = real(plan)
    if plan_real == cwd_real or not inside(plan_real, cwd_real):
        refuse("param", "LOOP_PLAN must lie inside LOOP_CWD - the sandboxed peer can write nowhere else")
    if not os.path.isfile(prompt_file):
        refuse("param", "LOOP_PROMPT_FILE must be a regular file")
    try:
        prompt_fh = open(prompt_file, "rb")
        prompt_empty = prompt_fh.read().strip() == b""
        prompt_fh.seek(0)
    except OSError:
        refuse("param", "LOOP_PROMPT_FILE cannot be read")
    if prompt_empty:
        refuse("param", "LOOP_PROMPT_FILE must hold at least one non-whitespace character")
    try:
        leg_used = leg_has_start(probe_log, runkey, leg)
    except OSError:
        refuse("param", "LOOP_PROBE_LOG cannot be read")
    if leg_used:
        refuse("leg", "LOOP_LEG already has a ROLE: start in the probe log under this run key - mint a fresh leg per launch")

    # The peer-writable roots, the tools' PATH, and the git the tools will run.
    host_tmp = _host_tmp()
    root_sources = [("LOOP_CWD", cwd_real), (host_tmp, real(host_tmp))]
    tmpdir = opt("TMPDIR")
    if tmpdir is not None:
        root_sources.append(("TMPDIR", real(tmpdir)))
    roots = [resolved for _label, resolved in root_sources]
    if route_bin is not None:
        # Router mode (round 15 PR-LOW-004): the containment comparison is only
        # ever made between clean physical paths - a resolved peer-writable root
        # holding a control character refuses router mode (fail closed: the
        # selector's and the folder's rule applied to the roots too; Python
        # compares the bytes exactly either way, so unrouted launches and the
        # comparison itself are unchanged - this is the contract, not a bypass).
        for label, resolved in root_sources:
            if not resolved or CONTROL_RE.search(resolved):
                refuse("param", "%s resolves to a path holding a newline or control character - a peer-writable root the router topology rule cannot compare byte-exactly refuses router mode" % label)
    tool_env = dict(os.environ)
    tool_env["PATH"] = tools_path(roots)
    git = shutil.which("git", path=tool_env["PATH"])
    if git is None:
        refuse("git", "no git on the tools' PATH (relative and peer-writable PATH entries are dropped)")

    self_file = real(os.path.abspath(__file__))
    scripts_dir = os.path.dirname(self_file)
    repo_root = os.path.dirname(scripts_dir)
    helper = os.path.join(scripts_dir, HELPER_NAME)
    checker = os.path.join(scripts_dir, CHECKER_NAME)
    interpreter = real(sys.executable)
    git_real = real(git)
    probe_real = real(probe_log)
    peer_log_real = real(peer_log) if peer_log_exists else real_in_folder(peer_log)
    identity_real = real_in_folder(identity_file)
    identity_tmp_real = identity_real + ".tmp"
    # round 45 (PC1 leg (d)): the join is SPELLED like every path it is compared
    # with — on a Windows host os.path.join puts a `\` after the `C:/...` folder,
    # so the unspelled value never equalled an output path and the collision
    # check below missed (an identity file written over the pre-state: escape=2)
    prestate_real = _spell(os.path.join(real(log_folder), "%s-escape-%s.pre" % (runkey, leg)))

    topology = (
        ("the launcher's directory", scripts_dir),
        ("LOOP_PROBE_LOG", probe_real),
        ("the probe log's folder", real(log_folder)),
        ("LOOP_PEER_LOG", peer_log_real),
        ("LOOP_IDENTITY_FILE", identity_real),
        ("the interpreter", interpreter),
        ("the interpreter's prefix", real(sys.prefix)),
        ("the interpreter's base prefix", real(sys.base_prefix)),
        ("git", git_real),
    )
    if route_real_path is not None:
        topology += (("LOOP_ROUTE_BIN", route_real_path),)
    for label, path in topology:
        if any(inside(path, root) for root in roots):
            refuse("topology", "%s lies inside a peer-writable root (LOOP_CWD, %s, or TMPDIR) - the launcher serves a run whose tools and logs are on the base side and whose peer is in the run worktree" % (label, host_tmp))

    # Output paths are kept apart.
    relied_on = (
        ("the probe log", probe_real),
        ("the plan", plan_real),
        ("the prompt file", real(prompt_file)),
        ("the launch's escape pre-state path", prestate_real),
        ("the launcher", self_file),
        ("the records helper", real(helper)),
        ("the history checker", real(checker)),
        ("the interpreter", interpreter),
        ("git", git_real),
        ("the codex binary", codex_real),
    )
    if route_real_path is not None:
        relied_on += (("the router", route_real_path),)
    outputs = (
        ("LOOP_PEER_LOG", peer_log_real),
        ("LOOP_IDENTITY_FILE", identity_real),
        ("LOOP_IDENTITY_FILE's temporary name", identity_tmp_real),
    )
    for i, (label, path) in enumerate(outputs):
        for other_label, other in outputs[i + 1:]:
            if path == other:
                refuse("output-path", "%s and %s are the same path" % (label, other_label))
        for other_label, other in relied_on:
            if path == other:
                refuse("output-path", "%s is the path of %s" % (label, other_label))
    if peer_log_exists:
        try:
            links = os.stat(peer_log).st_nlink
        except OSError:
            refuse("output-path", "LOOP_PEER_LOG cannot be examined")
        if links != 1:
            refuse("output-path", "LOOP_PEER_LOG exists with more than one link - it may be a hard link to another file")
    if os.path.lexists(identity_file + ".tmp"):
        refuse("output-path", "LOOP_IDENTITY_FILE's temporary name already exists")

    # What was checked is what is used. The rules above were checked on resolved
    # paths; a path that reaches the base side THROUGH a symlink sitting inside
    # a peer-writable root passes them, and the peer could repoint that link
    # while it runs. So every path this script uses once codex has started -
    # the log folder, the probe log, the identity file, the interpreter, git -
    # is used in the resolved form (tools_path does the same for PATH).
    # The probe log is pinned through its LAST component too (it may itself be
    # a link); the log folder stays the resolved folder of the path as given,
    # which is where the escape pre-state lives and where recovery looks.
    log_folder = real(log_folder)
    probe_log = probe_real
    identity_file = identity_real
    # git: this script's own calls run the resolved binary, and the tools run
    # a bare `git` found on PATH - so the resolved binary's own directory leads
    # the tools' PATH. That pins the lookup only when the binary is named git
    # (v45.0 T2.5, PR-HIGH-001 round 1: `git.exe` on a Windows host, where the
    # Git for Windows executable carries the extension and PATHEXT resolves it).
    if not git_admitted(os.path.basename(git_real)):
        refuse("git", "the git on the tools' PATH resolves to a file that is not named git - the tools' lookup cannot be pinned to it; put the real git's directory on PATH")
    git = git_real
    tool_env["PATH"] = os.path.dirname(git_real) + os.pathsep + tool_env["PATH"]

    # The two tools: present, and each equal to its committed copy.
    tool_ids = {}
    for name, path in ((HELPER_NAME, helper), (CHECKER_NAME, checker)):
        if not os.path.isfile(path):
            refuse("tools", "%s is missing beside the launcher" % name)
        working = blob_id(git, repo_root, path, tool_env)
        committed = committed_id(git, repo_root, name, tool_env)
        if working is None or committed is None or working != committed:
            refuse("tools", "%s differs from its committed copy (git hash-object against HEAD:scripts/%s) - commit the tooling before a launch" % (name, name))
        tool_ids[name] = working

    def tool_unchanged(name, path):
        return blob_id(git, repo_root, path, tool_env) == tool_ids[name]

    # v45.0 (D15 / D30): the runtime — imported ONCE from a private SNAPSHOT of
    # the verified helper: copy, re-verify the copy against the pinned id,
    # import (a rewrite of the checkout copy between its check and the import
    # cannot change what is imported). The snapshot lives in the PROBE LOG'S
    # FOLDER (round 39 MED-002) — a base-side directory the topology rule above
    # has already refused inside every peer-writable root — never under the
    # default temp directory: TMPDIR and the host temp root ARE peer-writable
    # roots, and a file this process imports must not sit where a sandboxed
    # peer of another run (or a survivor of an earlier round) may write
    # between the blob check and the import. The pre/post blob comparison and
    # tools=ok|changed above and below are unchanged — the snapshot serves
    # this process's own calls (the group primitive, the collector, the
    # containment predicate), while the helper's CLI keeps running from the
    # checkout under its hash gate.
    snap_dir = None
    snapshot = None

    def drop_snapshot():
        # the snapshot is imported ONCE and never re-read: it goes the moment the
        # import has either succeeded or failed (one file, one directory — no
        # tree walk, so a selftest that disables rmtree still sees it gone)
        if snap_dir is not None:
            cache = os.path.join(snap_dir, "__pycache__")
            if os.path.isdir(cache):   # defence: an interpreter that wrote bytecode regardless
                for name in os.listdir(cache):
                    try:
                        os.remove(os.path.join(cache, name))
                    except OSError:
                        pass
                try:
                    os.rmdir(cache)
                except OSError:
                    pass
        for path, fn in ((snapshot, os.remove), (snap_dir, os.rmdir)):
            if path is not None:
                try:
                    fn(path)
                except OSError:
                    pass
    try:
        snap_dir = tempfile.mkdtemp(prefix="loop-peer-snap.", dir=log_folder)
        snapshot = os.path.join(snap_dir, HELPER_NAME)
        shutil.copyfile(helper, snapshot)
        if blob_id(git, repo_root, snapshot, tool_env) != tool_ids[HELPER_NAME]:
            raise RuntimeError("the snapshot copy differs from the verified helper (the copy was raced)")
        rt = runtime_import(snapshot)
    except (Exception, SystemExit) as e:
        # a helper that is not import-safe (one that runs or exits at module
        # level) is not a runtime: refused, never an escaped exit
        drop_snapshot()
        refuse("tools", "%s could not be snapshotted and imported as the v45.0 runtime (%s: %s) - commit a helper of this release beside the launcher" % (HELPER_NAME, e.__class__.__name__, str(e)[:160]))
    drop_snapshot()

    py = [interpreter, "-I"]

    # ---- step 2: the baseline ----
    rc, out, err = run_tool(py + [checker, "--round-census", plan], tool_env)
    baseline = None
    if rc == 0:
        for line in out.decode("utf-8", "replace").splitlines():
            m = CENSUS_RE.match(line)
            if m:
                baseline = int(m.group(1))
    if baseline is None:
        forward(out)
        forward(err)
        refuse("baseline", "the round census could not be taken - the plan cannot be read, or its round history already has a violation (the checker's lines are on standard error)")

    # ---- step 3: the pre escape capture ----
    for signum in SIGNALS:
        signal.signal(signum, on_signal)
    # The collector's ownership rule has a PREREQUISITE, established here
    # before the pick (round 39 PR-MED-041): an exited child stays a waitable
    # zombie only under the default SIGCHLD disposition - an inherited SIG_IGN
    # (it survives exec) makes the kernel reap it at once, and the router's
    # number would be gone before the last group signal. A no-op on a
    # default-disposition host. The normalisation is SCOPED to the router window
    # (round 40 PR-LOW-017): the entry disposition is saved here and restored
    # once the router is released, before the keyed start, so the role child and
    # every later helper child inherit exactly what this launcher inherited.
    # v45.0 T2.5: SIGCHLD has no Windows counterpart — no disposition to
    # normalise there (the Job's process list is the non-reaping observation).
    entry_sigchld = None
    if hasattr(signal, "SIGCHLD"):
        entry_sigchld = signal.getsignal(signal.SIGCHLD)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)

    escape_args = ["--run", runkey, "--role", "peer", "--leg", leg, "--log-root", log_folder]
    for member in escape_roots.split(";"):
        escape_args += ["--root", member]
    if allow_path is not None:
        escape_args += ["--allow-path", allow_path]
    if iso is not None:
        escape_args += ["--iso", iso]
    if liveness is not None:
        escape_args += ["--liveness", liveness]

    def discard_prestate():
        # The post capture with no --log consumes the pre-state and writes
        # nothing to the probe log; its output is dropped.
        run_tool(py + [helper, "escape-check", "--capture", "post"] + escape_args, tool_env)

    rc, out, err = run_tool(py + [helper, "escape-check", "--capture", "pre"] + escape_args, tool_env)
    forward(err)
    if rc != 0:
        refuse("escape-pre", "the pre escape capture failed (the helper's message is on standard error)")
    if PENDING:
        discard_prestate()
        refuse("signal", "stopped by %s before the start was written" % signal.Signals(PENDING[0]).name)

    # ---- step 3, router mode: the pick (v41.0 D8) ----
    # After the pre capture, before the keyed start. The four identity values
    # ride as --flag=value from the SAME variables that feed the start record
    # (never trimmed or normalised); --pid is this process, which lives through
    # the child's wait; --label is the base checkout's folder name. The checked
    # (resolved) selector is what is run. Outcomes go through note(): the
    # launcher's standard output shapes are pinned. A note that carries the dir
    # is diagnostic - the identity file (written byte-exact) is the record.
    route_dir = None
    route_via = None
    if route_bin is not None:
        if shutil.which("python3", path=tool_env["PATH"]) is None:
            route_word = "other"
            note("router: python3 is not on the tools' PATH - the router (a python3 script) could not start, so the pick is not attempted: no answer (other); the inherited environment stands")
        elif not hasattr(os, "waitid"):
            # round 38 PR-MED-038: the collector's ownership rule needs a
            # non-reaping observation of the leader's exit (os.waitid / WNOWAIT
            # - absent from CPython on macOS); without it NO router is started
            # - never the reaping poll that would signal a released number.
            route_word = "other"
            note("router: this python3 has no os.waitid (the non-reaping observation the collector's ownership rule needs), so the pick is not attempted: no answer (other); the inherited environment stands")
        else:
            route_argv = [route_real_path, "pick", "--agent=codex", "--run=%s" % iso, "--role=peer",
                          "--phase=%s" % phase, "--model=%s" % model, "--pid=%d" % os.getpid(),
                          "--label=%s" % os.path.basename(repo_root), "--json"]
            route_word, route_sticky, route_ans, kept_out, kept_err, route_reason = rt.route_collect(route_argv, env=tool_env, cancel=PENDING)
            if route_word == "ok":
                dir_word, dir_check = rt.route_dir_word(route_ans, roots)
                if dir_word:
                    route_word = dir_word
                    route_reason = "%s %s" % (route_ans, dir_check)   # `<dir> <check>` - the second note (D9)
            if route_word == "ok":
                route_dir = route_ans
                route_via = "binding" if route_sticky else "pick"
                note('router: pick honoured - CODEX_HOME="%s" via=%s' % (route_dir, route_via))
            else:
                note("router: no answer (%s) - the inherited environment stands (stdout_bytes=%d stderr_bytes=%d)"
                     % (route_word, len(kept_out), len(kept_err)))
                # v42.0 D5: the SECOND note - the router's reasons beyond its
                # word, or the folder rule's `<dir> <check>` - only when there
                # is something to say; the first note is byte-identical to v41.0
                skipped = rt.route_skipped_text(kept_err, route_reason)
                if skipped:
                    note("router: skipped - %s" % skipped)
        if PENDING:
            discard_prestate()
            refuse("signal", "stopped by %s before the start was written" % signal.Signals(PENDING[0]).name)
    # The router window is CLOSED here: route_collect reaps and releases the
    # router on every path before it returns, and the gates above never start
    # one - so the entry SIGCHLD disposition comes back now, before the keyed
    # start (round 40 PR-LOW-017): the role child and every later helper child
    # inherit what this launcher inherited, with routing on, skipped, or off.
    # Never inside the window (PR-MED-041 would reopen), never a preexec_fn
    # (the collector's daemon readers may still be alive). A default entry
    # needs no call.
    if entry_sigchld is not None and entry_sigchld == signal.SIG_IGN:
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    # ---- step 4: the keyed start ----
    start_args = ["emit", "ROLE:start", "--run", runkey, "--role", "peer", "--log", probe_log,
                  "phase=%s" % phase, "backend=codex", "model=%s" % model, "leg=%s" % leg]
    if effort is not None:
        start_args.append("effort=%s" % effort)
    start_args += ["via=launcher", "baseline=%d" % baseline,
                   "tool_ids=%s,%s" % (tool_ids[HELPER_NAME], tool_ids[CHECKER_NAME]),
                   "pass=%s" % pass_key, "peer_round=%s" % peer_round, "cap=%s" % cap]
    rc, out, err = run_tool(py + [helper] + start_args, tool_env)
    forward(err)
    if rc == 2:
        discard_prestate()
        refuse("start", "the helper refused the keyed start (its message is on standard error)")
    if rc != 0:
        note("the start call exited %d without a clean refusal - the start may or may not be in the probe log; nothing is started and the pre-state is kept" % rc)
        say("PEER_LAUNCH_EXIT rc=none start=uncertain round=unknown escape=none end=none group=none tools=ok duration=0 leg=%s" % leg)
        return 1

    # ---- step 5: codex ----
    child = None
    handle = None           # the runtime's group handle (v45.0 T2.5)
    xdg_dir = None          # the child's private XDG_RUNTIME_DIR (v42.0 D8), once created
    pgid = None
    codex_rc = 127          # a child that could not be started
    stopped_by = None       # the signal this launcher stopped the child on
    duration = 0
    identity_lines = None   # what step 5 wrote, when it wrote
    peer_log_start = None   # v47.0 D21: the peer log's size just before the spawn - where THIS leg's bytes begin
    if PENDING:
        note("%s arrived before the spawn - codex is not started" % signal.Signals(PENDING[0]).name)
    else:
        argv = [codex_bin, "exec", "-s", "workspace-write", "-m", model]
        if effort is not None:
            argv += ["-c", "model_reasoning_effort=%s" % effort]
        argv += ["-C", cwd]
        child_env = dict((k, v) for k, v in os.environ.items()
                         if not k.startswith(("LOOP_", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_")))
        if route_dir is not None:
            child_env["CODEX_HOME"] = route_dir
        started = time.monotonic()
        try:
            # v42.0 D8: a private per-leg runtime dir for the sandboxed peer -
            # mkdtemp's 0700 under TMPDIR, else /tmp (peer-writable roots by
            # design; the topology rule checks tools, not this dir), exported
            # as XDG_RUNTIME_DIR, removed after the child exits (the finally
            # below). Allocated INSIDE the could-not-start boundary: a missing,
            # unwritable, or full TMPDIR takes the no-child route - the note,
            # no child, 127 on the end record, the closing mark and the census
            # - never an uncaught exception after the keyed start (round 1
            # PR-MED-005). XDG_CONFIG_HOME / XDG_CACHE_HOME are NOT redirected
            # (git reads the operator's config from the former).
            xdg_dir = tempfile.mkdtemp(prefix="loop-peer-xdg.", dir=os.environ.get("TMPDIR") or host_tmp)
            child_env["XDG_RUNTIME_DIR"] = xdg_dir
            log_fd = os.open(peer_log, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
            try:
                # round 39 HIGH-001 (the launcher's sibling): the child INHERITS this
                # descriptor. On POSIX O_APPEND travels with it. On Windows it does
                # not — the child writes at the handle's file pointer, which an
                # os.open leaves at 0 — so an existing peer log would be overwritten
                # from its first byte. Seek to the end first: inert under POSIX
                # O_APPEND, and on Windows the child (the log's sole writer while it
                # runs) starts where the log ends.
                # v47.0 D21: that end is also where this leg's bytes begin - the
                # token read after the child exits starts there, so an existing
                # peer log's earlier legs are never read as this leg's total.
                peer_log_start = os.lseek(log_fd, 0, os.SEEK_END)
                # v45.0 T2.5: the runtime's group — a new session on POSIX, a
                # Job Object on Windows (the leader assigned after Popen)
                handle = rt.group_launch(argv, cwd=cwd, stdout=log_fd, stderr=log_fd, stdin=prompt_fh, env=child_env)
                child = handle["proc"]
            finally:
                os.close(log_fd)
        except OSError as e:
            if xdg_dir is None:
                note("the runtime dir could not be created (%s) - treated as exit code 127" % e.__class__.__name__)
            else:
                reason = e.__class__.__name__
                if isinstance(e, getattr(rt, "_GroupSetupError", ())):
                    # round 29 PR-MED-004: the group primitive's OWN failure after the
                    # child may have started — its text (the pid, the kill / reap
                    # outcome) is kept in the note, never reduced to the class name
                    reason = "%s: %s" % (reason, (getattr(e, "strerror", None) or str(e))[:200])
                note("codex could not be started (%s) - treated as exit code 127" % reason)
    prompt_fh.close()

    # The identity record's router-mode keys (D8): on EVERY launch made with
    # LOOP_ROUTE_BIN set - the no-answer launch too - codex_home= is the
    # EFFECTIVE home (the router's literal dir, else the inherited CODEX_HOME
    # verbatim, else <HOME>/.codex), beside route_run= and route_phase=; the
    # composer copies these into its re-pick and never retypes them. Without
    # LOOP_ROUTE_BIN the record is unchanged.
    route_lines = []
    if route_bin is not None:
        route_lines = ["codex_home=%s" % (route_dir if route_dir is not None else inherited_home),
                       "route_run=%s" % iso, "route_phase=%s" % phase]

    group = "none"
    census_unknown = False   # round 32 PR-MED-002: the post-exit census could not be read
    try:
        if child is not None:
            # the leader IS the group (a new session: pgid = pid; a Job: the
            # leader's pid names it) — v45.0 T2.5
            pgid = child.pid
            identity_lines = ["ts=%s" % now_iso(), "run=%s" % runkey, "role=peer", "leg=%s" % leg,
                              "launcher_pid=%d" % os.getpid(), "codex_pid=%d" % child.pid,
                              "pgid=%d" % pgid, "cwd=%s" % cwd, "model=%s" % model] + route_lines
            try:
                write_identity(identity_file, identity_lines)
            except OSError as e:
                identity_lines = None
                note("the identity file could not be written (%s) - the child is still held; recovery has no recorded identity for this leg" % e.__class__.__name__)
            say("PEER_LAUNCH_START leg=%s pass=%s peer_round=%s cap=%s baseline=%d pid=%d pgid=%d peer_log=%s"
                % (leg, pass_key, peer_round, cap, baseline, child.pid, pgid, peer_log))

            while True:
                try:
                    child.wait(timeout=WAIT_POLL_S)
                    break
                except subprocess.TimeoutExpired:
                    pass
                if PENDING:
                    stopped_by = signal.Signals(PENDING[0]).name
                    stop_group(handle)
                    try:
                        child.wait(timeout=STOP_GRACE_S)
                    except subprocess.TimeoutExpired:
                        stop_group(handle, kill=True)
                        try:
                            # round 30 PR-MED-002: the post-KILL reap is BOUNDED — a leader the
                            # host could not terminate never strands this owner before the
                            # finally that closes the group handle (KILL_ON_JOB_CLOSE, the
                            # last sweep); its exit is reported unknown, never fabricated
                            child.wait(timeout=STOP_GRACE_S)
                        except subprocess.TimeoutExpired:
                            note("the leader did not exit within %.0f s of the kill - it may survive; the group handle's close is the last sweep" % STOP_GRACE_S)
                    break
            duration = int(time.monotonic() - started)
            codex_rc = child.returncode   # None when the leader outlived the bounded reap (round 30 PR-MED-002)
            if codex_rc is not None and codex_rc < 0:
                codex_rc = 128 - codex_rc

        # ---- step 6: the group, the signals, the closing mark ----
        if child is not None:
            group = "clean"
            # round 32 PR-MED-002: the survivor census is READ, never assumed —
            # unknown (None after one retry) issues no stop on an unobserved group
            # and is named; the Job handle's close in the finally stays the last
            # sweep on Windows
            members = census_members(handle)
            if members is None:
                census_unknown = True
                note("the exit census failed - survivors unknown; no stop issued on an unobserved group; cleanup unconfirmed")
            elif members:
                group = "killed"
                stop_group(handle)
                # round 33 PR-MED-002: the post-TERM wait and the escalation read the
                # same gone / alive / unknown state — KILL only on an OBSERVED survivor
                state = wait_group_state(handle, STOP_GRACE_S)
                if state == "alive":
                    stop_group(handle, kill=True)
                    state = wait_group_state(handle, STOP_GRACE_S)
                if state == "unknown":
                    census_unknown = True
                    note("the exit census failed after the stop - survivors unknown; cleanup unconfirmed")
    finally:
        if handle is not None:
            try:
                rt.group_close(handle)   # the Job handle released (KILL_ON_JOB_CLOSE sweeps a Windows survivor); a no-op on POSIX
            except Exception:
                pass
        # v42.0 D8: the runtime dir goes once the child and its group are gone
        # (the could-not-start path too - the dir was created before the Popen
        # failed); only when it was created, never a path this launcher did
        # not make. The identity file, the records, and the exit line are
        # unchanged by it.
        if xdg_dir is not None:
            residue = remove_runtime_dir(xdg_dir)   # round 13 PR-MED-021: restore owned descendants' modes, retry, report a residue
            if residue is not None:
                note("the runtime dir could not be removed (%s) - left at %s" % (residue, xdg_dir))
    for signum in SIGNALS:
        signal.signal(signum, signal.SIG_IGN)

    escape = "none"
    end = "none"
    tools = "ok"
    round_field = "unknown"
    new_round = None

    if identity_lines is None:
        identity_lines = ["ts=%s" % now_iso(), "run=%s" % runkey, "role=peer", "leg=%s" % leg,
                          "launcher_pid=%d" % os.getpid(), "cwd=%s" % cwd, "model=%s" % model] + route_lines
    # v47.0 D21: the leg's token total, read from the leg's own bytes of the peer
    # log now that the child and its group are gone - one more identity line,
    # directly before the closing mark, in this one rewrite. `unknown` when codex
    # was not started, printed no total, or the log could not be read; nothing
    # else (no status line, record or exit code) carries or depends on it.
    # round 16 PR-MED-023: also `unknown`, with no read at all, when the survivor
    # census is unknown - the leg's bytes are not known to be complete then.
    tokens = peer_tokens(peer_log, peer_log_start) if (child is not None and not census_unknown) else "unknown"
    marked = True
    try:
        write_identity(identity_file, identity_lines + ["tokens=%s" % tokens, "closing=%s" % now_iso()])
    except OSError as e:
        marked = False
        note("the closing mark could not be written (%s) - no tool is called again and the leg is left open" % e.__class__.__name__)

    if marked:
        # ---- step 7: the post escape capture ----
        if not tool_unchanged(HELPER_NAME, helper):
            tools = "changed"
        else:
            rc, out, err = run_tool(py + [helper, "escape-check", "--capture", "post", "--log", probe_log]
                                    + escape_args, tool_env)
            forward(out)
            forward(err)
            escape = "%d" % rc

        # ---- step 8: was a round appended? ----
        verdict = None
        if tools == "ok":
            if not tool_unchanged(CHECKER_NAME, checker):
                tools = "changed"
            else:
                rc, out, err = run_tool(py + [checker, "--expect-new-round-since", "%d" % baseline, plan], tool_env)
                lines = out.decode("utf-8", "replace").splitlines()
                if rc == 0:
                    for line in lines:
                        m = NEW_ROUND_RE.match(line)
                        if m:
                            new_round = int(m.group(1))
                # round 30 PR-MED-002: a leader that outlived the bounded reap has no exit
                # code — the verdict says so in words (the same free-text field), never
                # a fabricated number
                exit_word = ("%d" % codex_rc) if codex_rc is not None else "unknown (the leader did not exit within the stop bound; it may survive)"
                if new_round is not None:
                    verdict = "exit %s; new round %d" % (exit_word, new_round)
                    round_field = "new:%d" % new_round
                elif rc == 1 and any(NO_NEW_ROUND_RE.match(line) for line in lines):
                    verdict = "inconclusive: exit %s; no new round" % exit_word
                    round_field = "none"
                else:
                    verdict = "inconclusive: exit %s; census failed" % exit_word
                if new_round is None:
                    forward(out)
                    forward(err)
                    if stopped_by is not None:
                        verdict = "incomplete: stopped by %s; %s" % (stopped_by, verdict)
                if census_unknown:
                    # round 32 PR-MED-002: the uncertainty rides the same free-text field
                    verdict += "; survivor census unknown"

        # ---- step 9: the end ----
        if tools == "ok":
            if not tool_unchanged(HELPER_NAME, helper):
                tools = "changed"
            else:
                rc, out, err = run_tool(py + [helper, "emit", "ROLE:end", "--run", runkey, "--role", "peer",
                                              "--log", probe_log, "result=%s" % verdict, "leg=%s" % leg,
                                              "duration=%d" % duration], tool_env)
                forward(err)
                end = "written" if rc == 0 else "failed"

    # ---- step 10: the exit line ----
    say("PEER_LAUNCH_EXIT rc=%s start=written round=%s escape=%s end=%s group=%s tools=%s duration=%d leg=%s"
        % ("none" if child is None or codex_rc is None else "%d" % codex_rc, round_field, escape, end, group, tools, duration, leg))
    if (child is not None and codex_rc == 0 and new_round is not None and escape == "0"
            and end == "written" and tools == "ok" and not census_unknown):   # round 32 PR-MED-002: unconfirmed cleanup is never success
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
