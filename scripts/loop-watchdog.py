#!/usr/bin/env python3
"""loop-watchdog.py — the /execute-loop watcher (v48.0, plan
.cursor/plans/plan-loop-autonomy-group-2.md, D11-D14, D18, D19).

WHAT IT IS. One script, five subcommands. Three are the composer's and the
operator's hand tools; two are the watcher itself, which the OPERATOR starts
outside any agent session (a user service or a terminal):

  identity  the composer writes its identity record and, the first time, the
            run's seat files (D11, D12)                         [composer]
  seat      read-only: who holds the run's seat, the no-takeover mark, the
            watcher's heartbeat                                 [composer]
  stop      the operator's one stop command for an away run (D12, D14)
  tick      judge every live run of ONE base once; with --act, notify and
            take over under the limits (D13, D14)
  watch     the long-lived process: sleep, and each round run
            `<base>/scripts/loop-watchdog.py tick --base <base> --act` as a
            child for each base (D18)

THE ROLE GUARD. This script is composer-only: it is on no role's grant list.
When LOOP_ROLE is set and non-empty in the environment (the spawn wrapper
requires it on every spawn and passes it to the role), every subcommand
writes ONE stderr line

  REFUSE: loop-watchdog is the composer's and the operator's tool — LOOP_ROLE is set in this environment, which marks a spawned role's shell; nothing was done

and exits 2, before it loads the helper or reads an argument (the v46.1
runner's guard, with the same limits: a guard against ACCIDENTAL use, not a
boundary — a role that clears the variable is not stopped by it).

THE SESSION GUARD. `watch`, and `tick --act`, refuse to start inside an agent
session (CLAUDE_CODE_SESSION_ID, CLAUDECODE, CLAUDE_PID or LOOP_SEAT in the
environment): a watcher started there would die with that session's process
tree, and its takeovers would be that session's children. `tick` without
--act is read-only and runs anywhere.

USAGE

  python3 scripts/loop-watchdog.py identity --base </abs/base> --iso <iso-id>
          [--nudge-tag <tag> --nudge-grant <n>] [--state-dir </abs/dir>]
  python3 scripts/loop-watchdog.py seat --base </abs/base> --iso <iso-id>
          [--state-dir </abs/dir>]
  python3 scripts/loop-watchdog.py stop --iso <iso-id> [--base </abs/base>]
          [--takeover-only]
  python3 scripts/loop-watchdog.py tick --base </abs/base> [--act]
          [--profile-dir </abs/dir> ...] [--exec </abs/file> ...] [limits]
  python3 scripts/loop-watchdog.py watch --base </abs/repo> [--base ...]
          --profile-dir </abs/dir> [--profile-dir ...] [--exec </abs/file> ...]
          [--interval-s <s>] [--ticks <n>] [limits]

  limits (tick and watch; minutes may be fractional):
    --state-dir </abs/dir>      the watcher's own folder (default below)
    --stall-min <m>             15   no advancement for this long = a stall
    --leg-quiet-min <m>         45   a running leg with no file written
    --nudge-min <m>             30   the composer's nudge interval (D15)
    --nudge-margin-min <m>      5    the margin of D13's second clause
    --backoff-min <a,b,c>       5,15,45   the waits between a stall's steps
    --max-per-stall <n>         3    takeovers per stall
    --max-per-day <n>           6    takeovers per run per 24 hours
    --takeover-max-min <m>      240  a takeover's wall-clock bound

  `stop` without --base reads the checkout this script sits in. `identity`
  and `seat` take --state-dir only to find the watcher's heartbeat (when the
  operator started `watch` with one).

THE IDENTITY RECORD (D11): `<base>/.cursor/loops/<iso>-composer`, key=value
lines — session, pid, pid_start, entrypoint, exec, config_dir, cwd, host,
nudge, ts — written from the session's OWN environment
(CLAUDE_CODE_SESSION_ID, CLAUDE_PID, CLAUDE_CODE_ENTRYPOINT,
CLAUDE_CONFIG_DIR). A host that exposes no session id, or no process id for
the session, writes host=unknown, and no takeover is ever offered for it.
`identity` also creates the run's `<iso>-seat` and `<iso>-seat.gate` files
when they are missing — only on a host with file locks, only on a filesystem
that takes them (asked on a private probe file of its own, before either
shared file exists), and only when the run's journal establishes its log
folder as `<base>/.cursor/loops/<iso>` (the seat is found beside that
folder; a run with another log_root=, a run with no journal — a run with no
run worktree, whose logs are in the flat loops root — and one whose journal
does not establish that folder get no seat, `seat=none(log-root)`, and are
never taken over: a journal that cannot be read, one that says nothing (an
empty file, one cut short ahead of its state), and one whose log_root= is
THERE and cannot be used — empty, unsafe, or not an absolute path; the
listing reads all three `unreadable`. A log_root= that is absent is the
documented default; one that is there is followed or not trusted, never
replaced by the default). It completes a
pair that is half there and NEVER removes either file: the two names are the
run's lock identities for its whole life, and a lock somebody holds is proof
that locks work, never a reason to delete its path. The write is one of the seat's protected writes: under a held seat it
is refused unless made by the holder, and an identity write made WITHOUT
LOOP_SEAT — an interactive composer's — clears the no-takeover mark; a
takeover's own never does. The record is written FIRST and the mark removed
only after that write has returned, both under the one gate: a write that
fails leaves the mark and the record that stood as they were (exit 3), and
a mark that then cannot be removed is said (`mark=clear-failed`, exit 3 —
the record is written, takeover stays off). EVERY record this script keeps
is written whole or its write fails (_write_all): a write cut short never
replaces a record, and is never followed by what depends on it — a notice,
a stage, the go byte. It prints `identity: ...` and one `watcher: ...`
line (the heartbeat: the start command when it is absent or stale, "restart
the watcher" when its script differs from the installed one, and — when the
watcher runs but its LAST tick on this base did not end 0 — that it failed,
with the word for how: `exit-<n>`, `signal-<n>`, `timeout`, `not-started`,
`no-script`. `watch` writes that word into the heartbeat as one
`tick_failed=<word> <base>` line per such base, each round; the line never
reads `fresh … watching this base` for a base whose ticks fail). Neither
blocks.

THE VERDICT (D13), per live run, first match wins:

  closed            no live marker, or a terminal journal state
  unreadable        a journal, marker, log or policy log could not be read —
                    notify once, never a takeover (evidence that cannot be
                    read is never "nothing there"). Also a run whose log
                    folder NO journal establishes — no journal at all, one
                    that says nothing (empty, cut short), or one whose
                    log_root= is there and cannot be used (empty, unsafe,
                    not an absolute path): it is never judged from a
                    folder that was only guessed
  parked            an open must-pause in any stage log, or an open hold
  release-in-flight a release act with a start and no outcome
  leg-running       the role-liveness reader says `live` for a leg
  leg-quiet         the same, and no file under the log folder was written
                    for --leg-quiet-min: one notice
  leg-unknown       the reader says `unknown` for a leg: one notice, never a
                    takeover, however long it lasts
  progressing       advancement inside the stall window — a record that shows
                    the run moved, or the run's journal or marker WRITTEN
                    inside it (a run just created, a group just closed);
                    or — the composer's process alive — activity inside the
                    window and advancement within the last three nudge
                    intervals. Where the identity records a nudge, that
                    second clause's window is one nudge interval plus the
                    margin; or — the composer's process alive — a leg that
                    ENDED inside the stall window (its `ROLE: end` record,
                    by the record's own clock): the composer is about to
                    consume it, and the run is not called stalled in
                    between. With the composer gone a leg's end is no
                    advancement, and the stall is acted on at once
  stalled           everything else

ACTIVITY and ADVANCEMENT are the helper's two predicates (run_activity,
run_advancement): a `Wake:` line, a watch, the idle checkpoint or a notice is
activity and never advancement. A canonical `Wake:` line carries no clock, so
with --act each tick stores every stage log's length in the watcher's folder,
and a clock-less line counts as activity inside a window when it lies beyond
the OLDEST sample taken inside that window. File and transcript times are
neither — a log or a transcript merely touched is nothing — with the one
exception named above: the write time of the run's own journal and marker,
which the loop writes only when a run is created or its state changes.
`tick` without --act prints the verdicts and writes nothing at all; no form
of `tick` writes under a run's log root. With --act, a run that is stalled
gets ONE file beside its journal, its takeover ledger (FILES, below).

UNDER A LOCK, `tick --act` ACTS ONLY ON WHAT IT READ UNDER IT, THE TIME
INCLUDED. It takes its own lock (`tick.lock`, one acting tick per base and
state folder) BEFORE it lists the runs. For a run that has anything to count
it takes the run's ledger lock and THEN lists the runs again and judges the
run again, on a clock read then; the judgement made before that lock decides
only whether the ledger is opened. And the acquisition, under the seat's
gate, lists and judges once more, on a clock read under the gate. So an
attempt another watcher admitted a moment ago is never folded against a seat
read before it, and no wait is counted from a time read before a lock.
A lock the filesystem REFUSES is not a lock somebody HOLDS: a refused tick
lock is an environment failure — one line naming the lock, exit 3, no run
judged — and is never reported as another tick; a state folder that cannot
be created or opened is the same kind of failure (`problem=state-dir`, one
line, exit 3); a refused ledger lock is `ledger-nolock` (below).

ACTING ON `stalled` (D14), with --act only. A stall is one episode: it begins
at the first `stalled` verdict and ends only on advancement or a verdict of
parked, leg-running, leg-quiet or closed — a run that merely looks busy again
(activity alone) keeps its stall, its attempts and its steps.
  - Always: one urgent notice per stall naming the run and the stop command,
    at the stall's start and again 5, 15, then 45 minutes after the notice
    before — FOUR AT MOST, never a promise of four: while a takeover waits
    its own back-off a notice that falls due is held and goes out with the
    next attempt, and once a takeover limit is reached the give-up notice
    is sent and no stall notice follows it. A notice's number says nothing
    of how many takeovers were tried, or when the next one is.
  - Composer's process alive, or not provably gone: nothing else — except,
    where the identity records a nudge, ONE notice that the nudge is not
    working once three nudge intervals pass without advancement.
  - Composer's process gone: a takeover at once, when ALL hold — the run's
    away grant is bound; the grant's departure file digests to the grant's
    departure= and says `Watcher takeover: on` on every such line; the
    identity passes its checks; the seat is free and the no-takeover mark is
    absent; the limits allow. Otherwise the line says which did not
    (`why=<word>`), and the notice is all that happens.
  - The notice's schedule and the takeover's are TWO, kept apart: a stall
    that was only notified about — its composer alive — has spent no
    takeover, so when the composer then dies the first takeover starts at
    once, whatever notices went before and whenever the next one is due;
    an acquisition that started nothing spends no step; and no stall
    notice is sent beyond its four, a takeover beside it or not.
The identity's checks: session is a UUID; host is not unknown; cwd is the
base or the worktree of one of its live runs' journals; config_dir is on the
--profile-dir list (with no --profile-dir nothing can be taken over); the
transcript `projects/*/<session>.jsonl` exists there; exec is an existing
executable file on the --exec list or, with no --exec given, `claude` on the
watcher's PATH. No identity field that failed a check reaches a command.

THE TAKEOVER is one child: `<exec> -p --resume <session> <the fixed prompt>`
in the identity's cwd, on the identity's config folder, with standard input
from the null device, the settings sources of an interactive session, and
NEVER a permission-bypass flag — a command it is not allowed is refused
there, and its composer parks the run as a must-pause. Its ENVIRONMENT is the
watcher's own — minus every LOOP_* variable and every session variable, plus
LOOP_SEAT and the identity's CLAUDE_CONFIG_DIR — so a token, a key or a proxy
setting exported where the watcher was started is the takeover's too: start
the watcher from the environment the composer's sessions are started from.
The prompt is fixed
text in which only the validated run id varies (TAKEOVER_PROMPT). Its output
goes to the watcher's own folder. Its wall-clock bound (--takeover-max-min)
ENDS THE COMPOSER ALONE: the stage sends TERM, then KILL, to the takeover's
own process and to nothing else — under the split wrapper a role's supervisor
is outside that process's tree and runs on to its own end; the leg is then
unconsumed, which is a new stall.
A takeover SUCCEEDED only if, measured from the stage logs' lengths when the
attempt started, the run shows advancement, or its verdict has become parked,
leg-running, leg-quiet or closed. One that wrote its `Wake:` line and failed
has not succeeded: the stall is the same stall and the attempt counts.
Limits: three takeovers per stall (the next step 5, 15, then 45 minutes after
the one before ended); six per run per 24 hours; then ONE urgent notice and
no further attempt. A failed spawn counts as an attempt. THE LIMITS ARE THE
RUN'S: the stall, its attempts and steps and the day's attempt times are kept
in the run's ledger beside its journal, not in a watcher's folder, so two
watchers over one base — or one restarted with another --state-dir — share
one count; a ledger another watcher holds this instant, or one that cannot
be parsed, means nothing is counted and nothing is started (`why=ledger-busy`
/ `ledger-unreadable`); a ledger whose lock the filesystem REFUSES — no lock
service, which is not "somebody holds it" — is used without one, the notices
go on, and no takeover is started (`why=ledger-nolock`): the limits are
counted under the lock or not spent. What stays per watcher is the notices' dedupe for the
notify-only verdicts and the length samples.

A SIDE EFFECT IS TAKEN ONLY AFTER THE STATE THAT LIMITS IT IS WRITTEN. Every
notice has a reservation — a notify-only verdict's dedupe key (the watcher's
folder), the nudge's once-per-stall flag, the give-up's `done`, the stall
notice's own step (the ledger; beside it, where a takeover is allowed, the
attempt) — and the reservation is written BEFORE the notice is sent, as an
attempt always was before its spawn. State that cannot be written is therefore never a
notice at every tick: the run's line reads `action=error why=state-save`,
nothing is sent or started for it, the other runs are judged, and the tick
exits 3 with one `problem=state-save` line (the heartbeat then says the
base's last tick failed). A ledger that cannot be opened or parsed is the
same failed tick. The other side of the order, stated: a reservation that
was written and a notice the process died before sending is one notice
lost, never one repeated.

THE SEAT (D12; the helper holds the admission routine). The acquisition, in
order, all under the run's gate: judge the eligibility AGAIN, all of it — the
run listed again, its verdict and its plan taken again through the same two
functions, going on only when the verdict is still `stalled` and the plan is
the same plan, the identity's hash included (the grant still bound and its
departure file still saying `on`, no stop, no release act, no leg, the run
not closed, the composer still gone, the seat free, no mark); take the seat's
lock and write a fresh nonce; start the takeover HELD — a stage of this
script in its own session, holding the seat's descriptor, that does nothing
until it reads one byte from the watcher and exits if that pipe closes
first; write the stage's group AND THE STAGE'S START TOKEN into the seat
file; read the mark once more; then send the byte (or, the mark standing,
end the stage); then release the gate. A watcher killed or stopped before
the byte leaves a held stage that exits by itself. The takeover runs with
LOOP_SEAT=<its nonce>. A gated write is either on the log before that second
judgement or waits for the gate; a ROLE's own record takes no gate, and what
it starts in that instant is the next tick's to see.

ONE RULE FOR EVERY SIGNAL SENT TO A NUMBER READ FROM A FILE (signal_verified,
over the helper's signal_authority): the file must record the start token of
that number's process, and the runtime's identity test must say `live` for
THAT target immediately before the signal — a process running under its
recorded token; a group whose LEADER runs under its recorded token, and no
other group. PRESENCE IS ENOUGH TO REFUSE AND NEVER ENOUGH TO SIGNAL (round
53 PR-MED-035): a group whose leader is gone while a process remains in it
still reads `live` to the role-liveness reader — a takeover and a close stay
refused beside it — but it is NOT signalled: with the leader gone there is
no process to compare the recorded token with, and the group may be the
run's own orphans or another group that took the number and lost its
leader. `stop` names that group, says so, and exits 3; ending it is the
operator's. A lock
being held, a leg's overall word, or another process of the same record
being alive authorises nothing. Three targets are signalled this way and no
other number from a file is signalled at all: a leg's wrapper, a leg's role
group, the takeover's group. Every other signal in this script goes to a
child its sender started and has not reaped. The floor, stated: the instant
between the identity read and the signal.

STOP — `stop --iso <iso>`: (1) take the gate (a bounded wait) and write the
durable mark `<iso>-notakeover`; if the gate cannot be had, write the mark
anyway; (2) while the seat is held, signal the group the seat file publishes
— TERM, then KILL after a few seconds — each by the rule above, and wait,
bounded, for the kernel to free the seat. The KILL can be sent because the
group's leader, the takeover's STAGE, outlives the TERM for as long as its
takeover lives: it passes the signal on to the takeover, gives it the grace
and then its own KILL, and only then ends — so the group still proves itself
when the stop command asks again (a stage that had ended at the TERM would
leave a takeover that outlasts it in a leaderless group, which is never
signalled). A held seat whose record does not prove its group (no token
yet, a record left by an earlier takeover, a number that is another
process's now, a group whose leader is gone) is NOT signalled and is
reported; (3) unless --takeover-only,
stop each leg the role-liveness reader does not call `over`: a TERM to its
wrapper and a TERM to its role's group, each by the rule above and each on
its own evidence, read once from the leg's file. It exits 0 only when all of
it is done: the seat is free and every leg reads `over`. Anything else — a
seat still held (by an acquisition in progress, by a record it could not
prove, or by a group that would not die), a permission error, a leg not
`over` — is said, with the pids, and the exit is 3. It never reports a stop
it did not complete.
THE LEGS ARE READ FROM A FOLDER THE RUN'S JOURNAL ESTABLISHES —
`<base>/.cursor/loops/<iso>`, or the journal's log_root=. A run with no
journal has none: a run with no run worktree keeps its leg files in the flat
loops root, where a leg's file cannot be tied to one run. There (3) reads no
leg and signals nothing, says so on one NOT COMPLETE line, and the exit is 3
— each role is the operator's to stop, by a TERM to the wrapper pid its own
leg's file records. A journal that cannot be read — or that says nothing
(an empty file, one cut short ahead of its state), or whose log_root= is
there and cannot be used (empty, unsafe, not an absolute path) — leaves the
default folder as a guess: (3) reads it, stops what proves itself there,
and says on one
NOT COMPLETE line that a role whose files are elsewhere was not seen — exit
3. The mark (1) and the takeover (2) are done on every run all the same, and
--takeover-only, which reads no leg, is unchanged.

WHAT IT NEVER DOES. It runs no git and no gh; it runs no command taken from
any file it reads; it puts no text from a log, a plan or a departure file
into a prompt, a command or a notice (a notice names the run id, numbers and
fixed words); it takes no spawn lock; it writes nothing under any run's log
root; it never acts on a run without a bound away grant beyond notifying;
it never starts a takeover while the composer's process is alive or not
provably gone, or while the seat is held.

FILES. Beside the run's journal: `<iso>-composer`, `<iso>-seat`,
`<iso>-seat.gate`, `<iso>-notakeover`, and `<iso>-takeovers` — the run's
takeover ledger, which an acting tick creates for a run that is stalled. In
the watcher's own folder (`$XDG_STATE_HOME/loop-watchdog`, else
`~/.local/state/loop-watchdog`; on Windows `%LOCALAPPDATA%\\loop-watchdog`;
--state-dir overrides): `heartbeat`, and per base `<key>/<iso>.json` (the
length samples and the notify-only verdicts' dedupe state),
`<key>/<iso>/takeover-<n>.log` and `.result`, `<key>/tick.lock`.

EXIT CODES: 0 done; 2 a refused argument, the role guard, the session guard,
or a refused identity write; 3 a stop that could not finish, or an
environment failure; 125 the helper beside this script is missing or lacks a
name this script calls.

HOSTS. Verdicts and notices run on every host. A takeover needs POSIX file
locks and sessions: on a Windows host no seat file is created and no
takeover is offered.
"""
import datetime
import errno
import hashlib
import importlib.util
import json
import os
import re
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

try:
    import fcntl
except ImportError:          # a host without POSIX file locks: verdicts and notices only
    fcntl = None

HELPER_NAME = "loop-journal.py"
SCRIPT_NAME = "loop-watchdog.py"
RUNTIME_NAMES = (
    "watch_runs", "run_legs", "leg_signal_targets", "signal_authority", "proc_alive", "proc_start_token", "group_any",
    "watch_read", "watch_line_class", "watch_line_time", "run_activity", "run_advancement",
    "run_open_stops", "watch_away", "seat_supported", "seat_paths", "seat_state", "seat_gate_take",
    "seat_gate_release", "seat_admit", "fire_notice", "now_iso", "canon_path", "_configure_std_streams",
)
ROLE_REFUSAL = ("REFUSE: loop-watchdog is the composer's and the operator's tool — LOOP_ROLE is set in this environment, "
                "which marks a spawned role's shell; nothing was done")
SESSION_ENV = ("CLAUDE_CODE_SESSION_ID", "CLAUDECODE", "CLAUDE_PID", "LOOP_SEAT")
SEAT_ENV = "LOOP_SEAT"

# --- the named constants (D13, D14, D15, D18); the limits have flags (LIMIT_FLAGS) ---
STALL_MIN = 15.0             # no advancement for this long is a stall; also what a takeover waits for
LEG_QUIET_MIN = 45.0         # a live leg with no file written under the log folder
NUDGE_MIN = 30.0             # D15's one interval — the composer's nudge timer
NUDGE_MARGIN_MIN = 5.0       # D13's second clause: one nudge interval plus this
NUDGE_INTERVALS = 3          # ... and advancement within this many intervals (90 minutes)
BACKOFF_MIN = (5.0, 15.0, 45.0)
MAX_PER_STALL = 3
MAX_PER_DAY = 6
TAKEOVER_MAX_MIN = 240.0     # the takeover's wall-clock bound: it ends the composer alone
TAKEOVER_TERM_GRACE_S = 30.0
WATCH_INTERVAL_S = 60.0
TICK_TIMEOUT_S = 300.0
HEARTBEAT_STALE_S = 300.0
HEARTBEAT_FAILED = "tick_failed="        # one heartbeat line per base whose last tick did not end 0: `tick_failed=<word> <base>`
# A lock call refused because the lock is HELD. Any other failure of the call is "no lock service here" — never evidence
# that somebody holds it (round 49 PR-MED-032 / PR-MED-033, round 50 PR-LOW-017): one test for the probe, the ledger and
# the tick lock.
LOCK_BUSY_ERRNOS = (errno.EWOULDBLOCK, errno.EAGAIN, errno.EACCES)
ACQUIRE_GATE_WAIT_S = 5.0    # the watcher queues this long behind one protected write
STOP_GATE_WAIT_S = 10.0      # stop's bounded wait for the gate
STOP_WAIT_S = 20.0           # stop's bounded wait for the seat, and then for the legs
STOP_KILL_AFTER_S = 8.0      # TERM, then KILL, to a published group — each only while its leader (the stage) proves itself
DAY_S = 86400.0

UUID_RE = re.compile(r"\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")
ISO_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*\Z")
TOKEN_RE = re.compile(r"\A[A-Za-z0-9._-]{1,64}\Z")
NONCE_RE = re.compile(r"\A[0-9a-f]{32}\Z")
IDENTITY_KEYS = ("session", "pid", "pid_start", "entrypoint", "exec", "config_dir", "cwd", "host", "nudge", "ts")
IDENTITY_CAP = 8192

# The takeover's ONE prompt. Fixed text: the only thing that varies is the run
# id, validated against ISO_ID_RE before it is placed. Nothing read from a
# log, a plan or a departure file ever reaches it.
TAKEOVER_PROMPT = (
    "This message comes from the loop watcher (scripts/loop-watchdog.py), not from the operator. It is not an answer and it "
    "approves nothing. The composer process of /execute-loop run %s ended while the run's away grant was bound; you are that "
    "run's composer, restarted headlessly under the same grant. Re-read the execute-loop STICKY card and the plan's Current "
    "State / Handoff Note, write your identity (Preflight), then continue the run from its records as the Resume contract says. "
    "Waiting rule: wait for a leg by a background call with an explicit timeout above the leg's expected length, or by a "
    "Monitor that you re-arm when it expires; print a new Wake: line (Preflight step 10); and do not end your turn while a leg "
    "of the run reads live. Never start a production act. A question owed to the operator, and a command you are not allowed "
    "to run, is written as a must-pause."
)


# --------------------------------------------------------------------------- output
def _configure_std_streams():
    """UTF-8 + LF on this entrypoint's text streams — the helper's form,
    guarded the same way. `watch` calls it (round 75): it loads no helper, so
    the helper's own setup never runs for it, and its lines went out in the
    host's code page — on a Windows host cp1252 for a pipe or a file, in a
    stream its `tick` children write as UTF-8; under a page with no em-dash
    the line could not be written and `watch` ended on its first failed
    tick. Every other subcommand takes the helper's setup, after its load."""
    for name in ("stdout", "stderr"):
        s = getattr(sys, name, None)
        if s is None or not hasattr(s, "reconfigure"):
            continue
        try:
            s.reconfigure(encoding="utf-8", newline="\n")
        except Exception:
            pass


def _out(line):
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _stderr_line(line):
    """One stderr line as UTF-8 bytes with LF — the helper's stream setup is
    not loaded at every caller."""
    try:
        sys.stderr.flush()
        sys.stderr.buffer.write((line + "\n").encode("utf-8", "replace"))
        sys.stderr.buffer.flush()
    except (OSError, ValueError, AttributeError):
        pass


def _refuse(msg, code=2):
    _stderr_line("REFUSE: %s" % msg)
    return code


def _word(text, limit=80):
    """A value from a file or the environment as ONE printable token for a
    status line: anything outside a plain path alphabet becomes `?`."""
    text = "%s" % (text,)
    return "".join(ch if (ch.isascii() and (ch.isalnum() or ch in "._-/:@+~,=")) else "?" for ch in text[:limit]) or "none"


def _shell(path):
    """A path as ONE shell word for a printed command (a hint the operator
    copies) — quoted; a path holding a control character is not printed."""
    import shlex
    if any(ord(ch) < 0x20 or ord(ch) == 0x7f for ch in path):
        return "<a path holding a control character>"
    return shlex.quote(path)


# --------------------------------------------------------------------------- the helper's runtime
def load_helper(helper_path):
    """Load the records helper found BESIDE this script, by path, under a
    module name that is not `__main__`, writing no bytecode — the way the
    spawn wrapper and the bounded runner take their runtime. A missing file,
    one that does not import, or one that lacks a name this script calls is
    this script's own failure: one stderr line, exit 125."""
    saved = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("loop_journal_runtime", helper_path)
        if spec is None or spec.loader is None:
            raise ImportError("no import spec")
        rt = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rt)
    except (Exception, SystemExit) as e:
        sys.dont_write_bytecode = saved
        _stderr_line("loop-watchdog: %s: the records helper could not be loaded (%s: %s)"
                     % (helper_path, type(e).__name__, " ".join(str(e).split())[:160]))
        sys.exit(125)
    sys.dont_write_bytecode = saved
    missing = [n for n in RUNTIME_NAMES if not callable(getattr(rt, n, None))]
    if missing:
        _stderr_line("loop-watchdog: %s: the records helper lacks %s — it is not the version this script was installed with"
                     % (helper_path, ", ".join(missing)))
        sys.exit(125)
    return rt


def _quiet(fn, *args, **kwargs):
    """Call a helper function and CATCH its exits: the helper's writers end
    the process on a refusal (exit 2) or an environment failure (exit 3); the
    watcher must never die of a run's malformed record. Returns
    `(value, None)` or `(None, "<what happened>")`."""
    try:
        return fn(*args, **kwargs), None
    except SystemExit as e:
        return None, "helper exit %s" % (e.code,)
    except Exception as e:      # a reader that raised on one run's files is that run's problem
        return None, "%s" % type(e).__name__


# --------------------------------------------------------------------------- argv
class Usage(Exception):
    pass


LIMIT_FLAGS = ("--state-dir", "--stall-min", "--leg-quiet-min", "--nudge-min", "--nudge-margin-min", "--backoff-min",
               "--max-per-stall", "--max-per-day", "--takeover-max-min")
SUB_FLAGS = {
    "identity": {"value": ("--base", "--iso", "--nudge-tag", "--nudge-grant", "--state-dir"), "multi": (), "bool": ()},
    "seat": {"value": ("--base", "--iso", "--state-dir"), "multi": (), "bool": ()},
    "stop": {"value": ("--base", "--iso"), "multi": (), "bool": ("--takeover-only",)},
    "tick": {"value": ("--base",) + LIMIT_FLAGS, "multi": ("--profile-dir", "--exec"), "bool": ("--act",)},
    "watch": {"value": ("--interval-s", "--ticks") + LIMIT_FLAGS, "multi": ("--base", "--profile-dir", "--exec"), "bool": ()},
}


def parse_args(sub, argv):
    """`{flag: value | [values] | True}` for one subcommand's argv; every
    token is a known flag of that subcommand or the parse refuses."""
    g = SUB_FLAGS[sub]
    out = {}
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in g["bool"]:
            out[tok] = True
        elif tok in g["value"] or tok in g["multi"]:
            if i + 1 >= len(argv):
                raise Usage("%s needs a value" % tok)
            if tok in g["multi"]:
                out.setdefault(tok, []).append(argv[i + 1])
            elif tok in out:
                raise Usage("duplicate flag %s" % tok)
            else:
                out[tok] = argv[i + 1]
            i += 1
        else:
            raise Usage("%r is not accepted by `%s` (accepted: %s)"
                        % (tok[:60], sub, " ".join(sorted(g["value"] + g["multi"] + g["bool"]))))
        i += 1
    return out


def _abs_dir(value, flag):
    if not os.path.isabs(value):
        raise Usage("%s must be an absolute path" % flag)
    if any(ord(ch) < 0x20 or ord(ch) == 0x7f for ch in value):
        raise Usage("%s holds a control character" % flag)
    return value


def _minutes(value, flag, zero_ok=False):
    try:
        m = float(value)
    except ValueError:
        raise Usage("%s must be a number of minutes" % flag)
    if m != m or m in (float("inf"), float("-inf")) or m < 0 or (m == 0 and not zero_ok) or m > 525600:
        raise Usage("%s must be a number of minutes between 0 and one year" % flag)
    return m


def _count(value, flag):
    if not (value.isascii() and value.isdigit()) or len(value) > 6:
        raise Usage("%s must be a whole number" % flag)
    return int(value)


class Config(object):
    """One tick's whole configuration — the allow-lists, the limits, the
    state folder. `watch` validates it once and hands it to every `tick`
    child as separate argument-vector elements (to_argv)."""

    def __init__(self, flags, rt=None):
        self.act = bool(flags.get("--act"))
        self.state_dir = _abs_dir(flags["--state-dir"], "--state-dir") if "--state-dir" in flags else default_state_dir()
        self.stall_min = _minutes(flags.get("--stall-min", "%r" % STALL_MIN), "--stall-min")
        self.leg_quiet_min = _minutes(flags.get("--leg-quiet-min", "%r" % LEG_QUIET_MIN), "--leg-quiet-min")
        self.nudge_min = _minutes(flags.get("--nudge-min", "%r" % NUDGE_MIN), "--nudge-min")
        self.nudge_margin_min = _minutes(flags.get("--nudge-margin-min", "%r" % NUDGE_MARGIN_MIN), "--nudge-margin-min", zero_ok=True)
        parts = flags["--backoff-min"].split(",") if "--backoff-min" in flags else ["%r" % b for b in BACKOFF_MIN]
        if not parts or len(parts) > 12:
            raise Usage("--backoff-min is a comma-joined list of minutes")
        self.backoff_min = tuple(_minutes(p, "--backoff-min", zero_ok=True) for p in parts)
        self.max_per_stall = _count(flags.get("--max-per-stall", "%d" % MAX_PER_STALL), "--max-per-stall")
        self.max_per_day = _count(flags.get("--max-per-day", "%d" % MAX_PER_DAY), "--max-per-day")
        self.takeover_max_min = _minutes(flags.get("--takeover-max-min", "%r" % TAKEOVER_MAX_MIN), "--takeover-max-min")
        canon = rt.canon_path if rt is not None else os.path.realpath
        self.profile_dirs = [canon(_abs_dir(d, "--profile-dir")) for d in flags.get("--profile-dir", [])]
        self.execs = [canon(_abs_dir(p, "--exec")) for p in flags.get("--exec", [])]
        self.given_profile_dirs = list(flags.get("--profile-dir", []))
        self.given_execs = list(flags.get("--exec", []))

    def to_argv(self):
        """The configuration as argv elements for a `tick` child — every
        allow-list entry and every limit, each its own element."""
        argv = ["--state-dir", self.state_dir, "--stall-min", "%r" % self.stall_min, "--leg-quiet-min", "%r" % self.leg_quiet_min,
                "--nudge-min", "%r" % self.nudge_min, "--nudge-margin-min", "%r" % self.nudge_margin_min,
                "--backoff-min", ",".join("%r" % b for b in self.backoff_min),
                "--max-per-stall", "%d" % self.max_per_stall, "--max-per-day", "%d" % self.max_per_day,
                "--takeover-max-min", "%r" % self.takeover_max_min]
        for d in self.given_profile_dirs:
            argv += ["--profile-dir", d]
        for p in self.given_execs:
            argv += ["--exec", p]
        return argv


# --------------------------------------------------------------------------- the watcher's own folder
def default_state_dir():
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(root, "loop-watchdog")
    root = os.environ.get("XDG_STATE_HOME", "")
    if not os.path.isabs(root):
        root = os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(root, "loop-watchdog")


def base_key(base):
    return hashlib.sha256(os.path.realpath(base).encode("utf-8", "surrogateescape")).hexdigest()[:12]


def _read_small(path, cap=IDENTITY_CAP):
    """A small regular file's bytes, read without following a link at the
    leaf, or None."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        data = os.read(fd, cap + 1)
        return data if len(data) <= cap else None
    except OSError:
        return None
    finally:
        os.close(fd)


def _write_all(fd, data):
    """Write EVERY byte of `data` to `fd`, or raise (round 52 PR-LOW-020). A
    short write is legal for a regular file — at a size limit, as storage
    fills — and `os.write` reports it by what it RETURNS, not by an error;
    a record whose write was cut short must never be taken for a whole one.
    Partial progress is continued; no progress at all is an error. THE ONE
    way this script writes a record: by replacement (_write_atomic) and in
    place (the seat's two records, the ledger)."""
    view = memoryview(data)
    done = 0
    while done < len(view):
        n = os.write(fd, view[done:])
        if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
            raise OSError(errno.EIO, "a write made no progress after %d of %d bytes" % (done, len(view)))
        done += n


def _write_atomic(path, data):
    """Write `data` to `path` by a temporary name beside it and one replace.
    The replace happens only after EVERY byte is written and synced (round 52
    PR-LOW-020): a write that is cut short or fails raises, the temporary
    file is removed, and the record that stood at `path` stands unchanged."""
    tmp = "%s.tmp.%d" % (path, os.getpid())
    # never THROUGH a link (round 69 SEC-005): the temporary name is predictable, and a link planted at it would send this
    # write — the mark, the identity record, the watcher's state — into the link's target
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0), 0o644)
    try:
        try:
            _write_all(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _kv_lines(data):
    """key=value lines (first wins); a value is the rest of its line."""
    kv = {}
    for line in data.decode("utf-8", "replace").splitlines():
        k, sep, v = line.partition("=")
        if sep and re.match(r"\A[a-z][a-z0-9_]*\Z", k) and k not in kv:
            kv[k] = v
    return kv


def state_path(cfg, base, iso):
    return os.path.join(cfg.state_dir, base_key(base), "%s.json" % iso)


def load_state(cfg, base, iso):
    data = _read_small(state_path(cfg, base, iso), cap=4 << 20)
    try:
        st = json.loads(data.decode("utf-8")) if data else {}
    except ValueError:
        st = {}
    return st if isinstance(st, dict) else {}


class StateSaveFailed(Exception):
    """State the watcher must keep could not be written (round 51
    PR-LOW-019). A side effect — a notice, a takeover — is taken only AFTER
    the state that limits it is durable, so this error always means: no
    notice was sent and no takeover started without its record written
    first. `tick` turns it into `why=state-save` on that run's line and its
    own exit 3; it is never swallowed as a tick that succeeded."""

    def __init__(self, path, error):
        Exception.__init__(self, "%s (%s)" % (path, getattr(error, "strerror", None) or error))
        self.path, self.error = path, error


def save_state(cfg, base, iso, st):
    """Write the watcher's OWN state for one run — never the run's counts,
    which are the ledger's (`stall` and `day` are dropped here, whatever the
    caller's dict holds). A write that fails is StateSaveFailed."""
    path = state_path(cfg, base, iso)
    own = dict((k, v) for k, v in st.items() if k not in ("stall", "day"))
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _write_atomic(path, json.dumps(own, sort_keys=True).encode("utf-8"))
    except OSError as e:
        raise StateSaveFailed(path, e)


# --------------------------------------------------------------------------- the heartbeat (D18)
def script_hash(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return "unknown"


def heartbeat_path(state_dir):
    return os.path.join(state_dir, "heartbeat")


def write_heartbeat(state_dir, own_hash, bases, now_text, interval_s=WATCH_INTERVAL_S, failed=None):
    """`failed` (round 50 PR-LOW-017): {base: word} for each base whose LAST
    tick did not end 0 — `exit-<n>`, `signal-<n>`, `timeout`, `not-started`,
    `no-script` — written as one `tick_failed=<word> <base>` line each, a
    line kind an older reader skips. A base with no such line either had its
    last tick end 0 or has had none yet."""
    os.makedirs(state_dir, exist_ok=True)
    lines = ["ts=%s" % now_text, "epoch=%d" % int(time.time()), "pid=%d" % os.getpid(), "script_sha256=%s" % own_hash,
             "interval_s=%d" % int(interval_s)]
    lines += ["base=%s" % b for b in bases]
    lines += ["%s%s %s" % (HEARTBEAT_FAILED, (failed or {})[b], b) for b in bases if b in (failed or {})]
    _write_atomic(heartbeat_path(state_dir), ("\n".join(lines) + "\n").encode("utf-8", "surrogateescape"))


def heartbeat_line(state_dir, base, config_dir=None):
    """The ONE `watcher:` line Preflight and the pre-departure message read:
    the start command when the heartbeat is absent or stale, `restart the
    watcher` when it carries another script's hash than the installed one,
    what is missing when it does not watch this base, and — round 50
    PR-LOW-017 — that the watcher runs but its last tick on this base FAILED,
    with the word the heartbeat carries for it: a base whose ticks fail is
    never called `fresh … watching this base`. Advisory — the caller never
    blocks on it. "Fresh" says the watch process wrote the heartbeat lately
    and the last tick it ran for this base ended 0 (or it has run none yet);
    a tick that ends 0 behind another tick's lock counts as one that ran."""
    start = ("python3 scripts/%s watch --base %s --profile-dir %s"
             % (SCRIPT_NAME, _shell(base), _shell(config_dir) if config_dir else "<the composer's config folder>"))
    data = _read_small(heartbeat_path(state_dir), cap=1 << 16)
    if data is None:
        return "watcher: not running (no heartbeat in %s) — start it outside any agent session: %s" % (_word(state_dir, 200), start)
    kv = _kv_lines(data)
    bases = [line[len("base="):] for line in data.decode("utf-8", "replace").splitlines() if line.startswith("base=")]
    try:
        age = int(time.time()) - int(kv.get("epoch", ""))
        stale_s = max(HEARTBEAT_STALE_S, 3 * int(kv.get("interval_s", "0")))      # a slow watcher is not a stopped one
    except ValueError:
        age, stale_s = None, HEARTBEAT_STALE_S
    if age is None or age > stale_s or age < -HEARTBEAT_STALE_S:
        return ("watcher: heartbeat stale (%s s) — start it outside any agent session: %s"
                % ("unknown" if age is None else "%d" % age, start))
    installed = script_hash(os.path.join(base, "scripts", SCRIPT_NAME))
    if kv.get("script_sha256") != installed:
        return "watcher: restart the watcher — it runs a script that differs from the installed one (heartbeat %d s old)" % age
    if os.path.realpath(base) not in [os.path.realpath(b) for b in bases]:
        return "watcher: running, but it does not watch this base — restart it with --base %s as well" % _shell(base)
    for line in data.decode("utf-8", "replace").splitlines():
        if line.startswith(HEARTBEAT_FAILED):
            word, _sep, where = line[len(HEARTBEAT_FAILED):].partition(" ")
            if where and os.path.realpath(where) == os.path.realpath(base):
                return ("watcher: running, but its last tick on this base FAILED (%s) — this base is not being watched as it should be; "
                        "read the watcher's own output for that tick's lines (heartbeat %d s old)" % (_word(word, 24), age))
    return "watcher: heartbeat fresh (%d s) — watching this base" % age


# --------------------------------------------------------------------------- identity (D11)
def _proc_link(pid, name):
    try:
        return os.readlink("/proc/%d/%s" % (pid, name))
    except (OSError, ValueError):
        return None


def read_identity(loops, iso):
    """`(kv, raw bytes)` of the run's composer identity record, or
    `(None, None)`."""
    data = _read_small(os.path.join(loops, iso + "-composer"))
    if data is None:
        return None, None
    return _kv_lines(data), data


def build_identity(rt, env, nudge, cwd):
    """The identity record's key=value pairs, in IDENTITY_KEYS order, from the
    session's own environment. `host` is `claude-code` when the environment
    names a session id and a process id for it, else `unknown`."""
    session = env.get("CLAUDE_CODE_SESSION_ID", "")
    pid_text = env.get("CLAUDE_PID", "")
    pid = int(pid_text) if (pid_text.isascii() and pid_text.isdigit() and 0 < len(pid_text) <= 10) else None
    state, token = rt.proc_start_token(pid) if pid else ("unknown", None)
    known = bool(UUID_RE.match(session)) and pid is not None and state != "gone"
    exe = _proc_link(pid, "exe") if pid else None
    proc_cwd = _proc_link(pid, "cwd") if pid else None
    config_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return [("session", session if UUID_RE.match(session) else "none"),
            ("pid", "%d" % pid if pid else "none"),
            ("pid_start", token or "unknown"),
            ("entrypoint", env.get("CLAUDE_CODE_ENTRYPOINT") or "unknown"),
            ("exec", exe or "unknown"),
            ("config_dir", config_dir),
            ("cwd", proc_cwd or cwd),
            ("host", "claude-code" if known else "unknown"),
            ("nudge", nudge),
            ("ts", rt.now_iso())]


def _locks_work(loops, iso):
    """Does this filesystem take file locks at all? Asked on a PRIVATE probe
    file (round 49 PR-MED-032) — created exclusively under a name of this
    process's own, locked through one descriptor, tested through a second,
    removed — and asked BEFORE the run's shared seat files are created. The
    shared files are never part of the question: a lock somebody else holds
    on one of them is proof that locks work, never a reason to touch it."""
    if fcntl is None:
        return False
    probe = os.path.join(loops, "%s-seat.probe.%d.%s" % (iso, os.getpid(), secrets.token_hex(4)))
    first = second = None
    try:
        first = os.open(probe, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0), 0o600)
        second = os.open(probe, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
        fcntl.flock(first, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            fcntl.flock(second, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except OSError as e:
            return e.errno in LOCK_BUSY_ERRNOS    # refused as BUSY: the lock is enforced
        return False                              # a second lock beside an exclusive one: locks are not enforced here
    except OSError:
        return False
    finally:
        for fd in (first, second):
            if fd is not None:
                os.close(fd)
        try:
            os.unlink(probe)
        except OSError:
            pass


def cmd_identity(rt, flags):
    for req in ("--base", "--iso"):
        if req not in flags:
            return _refuse("identity requires --base </abs/base> --iso <iso-id>")
    base, iso = _abs_dir(flags["--base"], "--base"), flags["--iso"]
    if not ISO_ID_RE.match(iso):
        return _refuse("--iso is not a filename-safe iso-id")
    # every argument is checked BEFORE the first write (round 70 PR-LOW-030): read after the record was written and the
    # mark lifted, a --state-dir that is no absolute path was a usage refusal over a run whose control state had changed
    state_dir = _abs_dir(flags["--state-dir"], "--state-dir") if "--state-dir" in flags else default_state_dir()
    if ("--nudge-tag" in flags) != ("--nudge-grant" in flags):
        return _refuse("--nudge-tag and --nudge-grant travel together (the live timer's tag and the grant it was armed under), or neither (nudge=none)")
    nudge = "none"
    if "--nudge-tag" in flags:
        tag, grant = flags["--nudge-tag"], flags["--nudge-grant"]
        if not TOKEN_RE.match(tag) or not (grant.isascii() and grant.isdigit() and 0 < len(grant) <= 6 and int(grant) >= 1):
            return _refuse("--nudge-tag is a token of [A-Za-z0-9._-] (1 to 64) and --nudge-grant a grant number from 1")
        nudge = "%s:%d" % (tag, int(grant))
    loops = os.path.join(base, ".cursor", "loops")
    runs, problem = rt.watch_runs(base)
    run = next((r for r in runs if r["iso"] == iso), None)
    if problem or run is None:
        return _refuse("no run %s under %s (no journal and no marker of that name) — wrong --iso or wrong --base?" % (_word(iso), _word(loops, 200)))
    pairs = build_identity(rt, os.environ, nudge, os.getcwd())
    for key, value in pairs:
        if any(ord(ch) < 0x20 or ord(ch) == 0x7f for ch in value):
            return _refuse("the session's %s holds a control character — the identity record is not written" % key)
    paths = rt.seat_paths(loops, iso)
    seat = "none(host)"
    if rt.seat_supported():
        if not run["default_root"]:
            seat = "none(log-root)"
        elif not (os.path.lexists(paths["seat"]) or os.path.lexists(paths["gate"])) and not _locks_work(loops, iso):
            # a filesystem that takes no file lock: with seat files on it every composer write would be refused as
            # untestable — so none is created, the run is admitted as before, and it is never taken over
            seat = "none(no-locks)"
        else:
            # create what is missing and NEVER remove either (round 49 PR-MED-032): the two names are the run's lock
            # identities for its whole life — another writer may hold one this instant. A pair that is half there is
            # completed, the file that is there left exactly as it is.
            seat = "present"
            for kind in ("gate", "seat"):
                try:
                    os.close(os.open(paths[kind], os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0), 0o644))
                    seat = "created"
                except FileExistsError:
                    pass
                except OSError as e:
                    return _refuse("the run's seat file %s could not be created (%s)" % (_word(paths[kind], 200), e.strerror), 3)
    gate, why = rt.seat_admit(loops, iso)
    if why is not None:
        return _refuse(why)
    mark, mark_error = "none", None
    try:
        # THE ORDER (round 52 PR-MED-034): the new record FIRST, and the mark removed only after that write has returned —
        # both under the one gate. The mark holds a takeover off; it is lifted by the record that replaces the dead
        # composer's, never before it. A write that fails leaves the mark and the record that stood exactly as they were.
        try:
            _write_atomic(paths["composer"], "".join("%s=%s\n" % p for p in pairs).encode("utf-8", "surrogateescape"))
        except OSError as e:
            return _refuse("the identity record %s could not be written (%s) — nothing was changed: the record that stood and the "
                           "no-takeover mark, if there is one, stand as they were" % (_word(paths["composer"], 200), e.strerror), 3)
        if os.path.lexists(paths["mark"]):
            mark = "stands"
            if not os.environ.get(SEAT_ENV):
                # an interactive composer's identity write — the one thing that clears the mark
                try:
                    os.unlink(paths["mark"])
                    mark = "cleared"
                except OSError as e:
                    mark, mark_error = "clear-failed", e
    finally:
        rt.seat_gate_release(gate)
    kv = dict(pairs)
    _out("identity: iso=%s host=%s session=%s pid=%s entrypoint=%s nudge=%s seat=%s mark=%s"
         % (iso, kv["host"], kv["session"][:8] if kv["session"] != "none" else "none", kv["pid"], _word(kv["entrypoint"]),
            kv["nudge"], seat, mark))
    _out(heartbeat_line(state_dir, base, kv["config_dir"]))
    if mark_error is not None:
        # said, never passed over (round 52 PR-MED-034): the record IS written, and takeover stays off
        return _refuse("the identity record was written, but the no-takeover mark %s could not be removed (%s) — takeover stays OFF for "
                       "this run while it stands; remove it, or run identity again" % (_word(paths["mark"], 200), mark_error.strerror), 3)
    return 0


def cmd_seat(rt, flags):
    for req in ("--base", "--iso"):
        if req not in flags:
            return _refuse("seat requires --base </abs/base> --iso <iso-id>")
    base, iso = _abs_dir(flags["--base"], "--base"), flags["--iso"]
    if not ISO_ID_RE.match(iso):
        return _refuse("--iso is not a filename-safe iso-id")
    state_dir = _abs_dir(flags["--state-dir"], "--state-dir") if "--state-dir" in flags else default_state_dir()   # before the first line
    loops = os.path.join(base, ".cursor", "loops")
    paths = rt.seat_paths(loops, iso)
    word, kv = rt.seat_state(paths)
    extra = ""
    if word == "held":
        extra = " pgid=%s since=%s watcher_pid=%s" % (_word(kv.get("pgid", "unpublished")), _word(kv.get("ts", "unknown")),
                                                      _word(kv.get("watcher_pid", "unknown")))
    _out("seat: iso=%s state=%s%s mark=%s" % (iso, word, extra, "yes" if os.path.lexists(paths["mark"]) else "no"))
    ident, _raw = read_identity(loops, iso)
    _out(heartbeat_line(state_dir, base, (ident or {}).get("config_dir")))
    return 0


# --------------------------------------------------------------------------- stop (D12, D14)
def _pid_of(text):
    if not text or not (text.isascii() and text.isdigit()) or len(text) > 10:
        return None
    n = int(text)
    return n if 1 < n <= 2147483647 else None


def signal_verified(rt, kind, pid, token, sig, pgid=None):
    """THE one place this script signals a number it read from a FILE (round
    49 PR-HIGH-005 / PR-HIGH-006) — a leg's wrapper, a leg's role group, the
    takeover's group the seat file publishes. The helper's signal_authority
    is asked immediately before the signal, for THIS target and on its own
    recorded start token; only `live` is signalled. Returns `signalled`, or
    the word that refused it — `over` (gone, or the number is another
    process's now), `unknown` (no token in the record, it could not be read,
    or — round 53 PR-MED-035 — a group whose leader is gone while a process
    remains in it: present, and so not provable). Never this process or its
    own group. Every other signal in this
    script goes to a child the sender started and has not yet reaped."""
    word = rt.signal_authority(kind, pid, token, pgid)
    if word != "live":
        return word
    try:
        if kind == "group":
            if pgid == os.getpgrp():
                return "unknown"
            os.killpg(pgid, sig)
        else:
            if pid == os.getpid():
                return "unknown"
            os.kill(pid, sig)
    except ProcessLookupError:
        return "over"
    return "signalled"


def _orphan_note(rt, word, pgid):
    """What `stop` adds to its line when a group it did not signal is one
    whose LEADER IS GONE while a process remains in it (round 53 PR-MED-035).
    Presence is enough to refuse and never enough to signal: with the leader
    gone there is no process to compare the recorded start token with, and
    the group may be the run's own orphans or another group that took the
    number and lost its leader. Only words — nothing is decided here."""
    if word != "unknown" or not isinstance(pgid, int) or isinstance(pgid, bool):
        return ""
    try:
        if rt.proc_start_token(pgid)[0] != "gone" or not rt.group_any(pgid):
            return ""
    except Exception:
        return ""
    return (". The leader of group %d is gone and a process remains in it: it may be this run's own orphans or another group that has taken "
            "the number — nothing was signalled; look at group %d before you signal it yourself" % (pgid, pgid))


def _leg_stem(name):
    """A leg file's STEM: its name without `.live` / `.exit`. One wrapper has
    one stem for its whole life, and the reader gives one entry per stem —
    the wrapper's `<stem>.live` BECOMES its `<stem>.exit` when it ends (the
    one written, then the other removed), so a leg is followed across its
    wrapper's end by the stem and never by the file's name. An identity
    record (a leg from before v48.0) has neither suffix and is its own stem."""
    for suffix in (".live", ".exit"):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def cmd_stop(rt, flags):
    if "--iso" not in flags:
        return _refuse("stop requires --iso <iso-id> [--base </abs/base>] [--takeover-only]")
    iso = flags["--iso"]
    if not ISO_ID_RE.match(iso):
        return _refuse("--iso is not a filename-safe iso-id")
    base = _abs_dir(flags["--base"], "--base") if "--base" in flags else str(Path(__file__).resolve().parent.parent)
    loops = os.path.join(base, ".cursor", "loops")
    runs, problem = rt.watch_runs(base)
    run = next((r for r in runs if r["iso"] == iso), None)
    if problem or run is None:
        return _refuse("no run %s under %s (no journal and no marker of that name) — pass --base </abs/base> for the base checkout that holds the run"
                       % (_word(iso), _word(loops, 200)))
    paths = rt.seat_paths(loops, iso)
    failed = []
    # (1) the mark, under the gate when it can be had in the bounded wait
    gate, gate_word = None, "none"
    try:
        gate = rt.seat_gate_take(paths, wait_s=STOP_GATE_WAIT_S)
        gate_word = "taken" if gate is not None else "none"
    except Exception:
        gate_word = "busy"
    try:
        try:
            _write_atomic(paths["mark"], ("ts=%s\nby=stop\n" % rt.now_iso()).encode("utf-8"))
            mark = "written"
        except OSError as e:
            mark = "FAILED"
            failed.append("the no-takeover mark %s could not be written (%s)" % (_word(paths["mark"], 200), e.strerror))
    finally:
        rt.seat_gate_release(gate)
    # (2) a live takeover: signal the group the seat file publishes — only once that record PROVES the group is the
    # holder's (signal_verified) — and wait for the kernel to free the seat
    takeover, pgid, watcher_pid, signalled, killed, proof = "none", None, None, None, False, None
    deadline = time.monotonic() + STOP_WAIT_S
    while True:
        word, kv = rt.seat_state(paths)
        if word != "held":
            if word == "unknown":
                takeover = "unknown"
                failed.append("the seat file %s could not be tested" % _word(paths["seat"], 200))
            elif takeover != "none":
                takeover = "ended"
            break
        takeover = "held"
        pgid, watcher_pid = _pid_of(kv.get("pgid", "")), _pid_of(kv.get("watcher_pid", ""))
        if pgid is not None:
            sig = signal.SIGTERM if signalled is None else (
                signal.SIGKILL if not killed and time.monotonic() - signalled >= STOP_KILL_AFTER_S else None)
            if sig is not None:
                try:
                    proof = signal_verified(rt, "group", pgid, kv.get("stage_start"), sig, pgid)
                except OSError as e:
                    failed.append("the takeover's group %d could not be signalled (%s)" % (pgid, e.strerror))
                    break
                if proof == "signalled":
                    signalled, killed = (signalled or time.monotonic()), sig == signal.SIGKILL
        if time.monotonic() >= deadline:
            break
        time.sleep(0.1)
    if takeover == "held":
        if pgid is None:
            failed.append("the seat is still held by an acquisition whose group is not published (watcher pid %s) — the mark is written, so "
                          "no takeover begins work; the seat frees when that watcher resumes or ends"
                          % ("%d" % watcher_pid if watcher_pid else "unknown"))
        elif signalled is None:
            failed.append("the seat is held and its record names group %d, which could NOT be proved to be the holder's (its start "
                          "token reads %s) — nothing was signalled: a held lock says somebody holds the file, never whose group the "
                          "text names. The mark is written, so no takeover begins work; watcher pid %s%s"
                          % (pgid, proof or "unknown", "%d" % watcher_pid if watcher_pid else "unknown", _orphan_note(rt, proof, pgid)))
        else:
            failed.append("the seat is still held after TERM%s to the takeover's group %d (watcher pid %s) — deal with that group"
                          % (" and KILL" if killed else "", pgid, "%d" % watcher_pid if watcher_pid else "unknown"))
    _out("stop: iso=%s mark=%s gate=%s takeover=%s%s" % (iso, mark, gate_word, takeover, " pgid=%d" % pgid if pgid else ""))
    # (3) the run's legs: each target on its OWN evidence, read once from the leg's file and proved at the signal.
    # The folder they are read from is the RUN'S only when a journal that could be read says so (HB0, round 56 MED-002).
    # A run with no journal has none: a run with no run worktree keeps its leg files in the flat loops root, where a
    # leg's file cannot be tied to THIS run (its run= is a phase runkey every run reuses) — no leg is read there and
    # nothing is signalled. A journal that cannot be read — or that says nothing (an empty file, one cut short: round 71
    # PR-MED-038), or whose `log_root=` is there and cannot be used (empty, unsafe, not an absolute path: round 72
    # PR-MED-039), each of which the listing reads `unreadable` too — leaves the default folder as a guess: what proves
    # itself there is still stopped, and a role whose files are elsewhere was not seen. Either way `done` is never said.
    # A folder the journal NAMES is the run's whether or not anything is there: one that is missing holds no leg.
    read_legs = not flags.get("--takeover-only")
    if read_legs and run["journal"] == "none":
        read_legs = False
        failed.append("run %s has no journal, so the folder its legs' files are in is not established — a run with no run worktree keeps "
                      "them in the flat %s root, where a leg's file cannot be tied to this run. No leg was read and no role was signalled: "
                      "stop each role by a TERM to the wrapper pid its own leg's file records" % (iso, _word(loops, 200)))
    if read_legs:
        legs = [l for l in rt.run_legs(run["log_root"]) if l["word"] != "over"]
        waiting = []
        for leg in legs:
            name = _word(leg["leg"])
            targets = rt.leg_signal_targets(run["log_root"], leg)
            wrapper, group = ("changed", "changed") if targets is None else ("unknown", "unknown")
            try:
                if targets is not None:
                    wrapper = signal_verified(rt, "pid", targets["wrapper"][0], targets["wrapper"][1], signal.SIGTERM)
                    group = signal_verified(rt, "group", targets["group"][0], targets["group"][1], signal.SIGTERM, targets["group"][2])
            except OSError as e:
                failed.append("leg %s could not be signalled (%s)" % (name, e.strerror))
            waiting.append((leg, name, wrapper, group, targets["group"][2] if targets is not None else None))
        # The word a leg reads AFTERWARDS is looked up by its file's STEM, never by the file's name (round 66 MED-001): a
        # wrapper that is signalled forwards the TERM, does not wait for a role that ignores it, writes `<stem>.exit` and
        # removes `<stem>.live` — so the name this leg was listed under is gone the moment its wrapper ends, whatever its
        # role is doing. And a leg with no entry left is `unknown`, never `over`: nothing there proves the role ended.
        def words_now():
            return dict((_leg_stem(l["file"]), l["word"]) for l in rt.run_legs(run["log_root"]))

        leg_deadline = time.monotonic() + STOP_WAIT_S
        while time.monotonic() < leg_deadline:
            now_words = words_now()
            if all(now_words.get(_leg_stem(leg["file"]), "unknown") == "over" for leg, _n, w, g, _p in waiting if "signalled" in (w, g)):
                break
            time.sleep(0.2)
        now_words = words_now()
        for leg, name, wrapper, group, rpgid in waiting:
            after = now_words.get(_leg_stem(leg["file"]), "unknown")
            _out("stop: leg=%s was=%s wrapper=%s group=%s now=%s" % (name, leg["word"], wrapper, group, after))
            if after != "over":
                failed.append("leg %s reads %s (%s) — not stopped: its wrapper read %s and its role's group %s; a number from a leg's file "
                              "is signalled only when its own start token proves it is still that process%s"
                              % (name, after, leg["pids"], wrapper, group, _orphan_note(rt, group, rpgid)))
        if run["journal"] == "unreadable":
            failed.append("run %s's journal could not be read — or says nothing that names its log folder (it is empty or cut short), or "
                          "names it by a log_root= that cannot be used (empty, unsafe, or not an absolute path) — so "
                          "the folder its legs' files are in is not established — the legs under "
                          "%s were read and are reported above; a role whose files are elsewhere was neither read nor signalled"
                          % (iso, _word(run["log_root"], 200)))
    if failed:
        for why in failed:
            _out("stop: NOT COMPLETE — %s" % why)
        return 3
    _out("stop: done — takeover is off for run %s until an interactive composer writes its identity; %s"
         % (iso, "its roles were left running" if flags.get("--takeover-only") else "its live roles were stopped"))
    return 0


# --------------------------------------------------------------------------- the verdict (D13)
def sample_for(st, now_ts, window_s):
    """The stored length sample to measure a window against: the OLDEST one
    taken inside `[now - window, now]`. A record lying beyond it was written
    inside the window (the strict side: a line written in the window before
    that sample was taken is not counted). None when no sample is that
    recent."""
    inside = [s for s in st.get("samples", []) if isinstance(s, dict) and now_ts - window_s <= s.get("t", 0) <= now_ts]
    return min(inside, key=lambda s: s["t"]).get("lens", {}) if inside else None


def _newest_write(log_root):
    """The newest modification time of a regular file directly under the
    run's log folder (epoch seconds), or None."""
    newest = None
    try:
        names = os.listdir(log_root)
    except OSError:
        return None
    for name in names:
        try:
            st = os.lstat(os.path.join(log_root, name))
        except OSError:
            continue
        if stat.S_ISREG(st.st_mode) and (newest is None or st.st_mtime > newest):
            newest = st.st_mtime
    return newest


def run_written(loops, iso):
    """When the run's journal or its marker was last WRITTEN (epoch seconds,
    the newer of the two), or None. The loop writes these two files only
    when a run is created and when its state changes — a group closed, a
    close — so this is the one file time the verdict reads as advancement:
    without it a run that has just been created, and has no record yet,
    would read `stalled` at its first tick."""
    newest = None
    for suffix in ("-isolation", "-active"):
        try:
            m = os.lstat(os.path.join(loops, iso + suffix)).st_mtime
        except OSError:
            continue
        newest = m if newest is None or m > newest else newest
    return newest


def judge(rt, cfg, base, run, st, now):
    """One run's verdict and the facts behind it — a dict the caller prints
    and acts on. Reads only; every helper call is caught."""
    loops = os.path.join(base, ".cursor", "loops")
    iso, log_root = run["iso"], run["log_root"]
    j = {"iso": iso, "verdict": "stalled", "composer": "unknown", "grant": None, "takeover": None, "seat": "none",
         "legs": {"live": 0, "unknown": 0, "over": 0}, "lens": {}, "records": [], "problems": 0, "nudge": False,
         "ident": None, "ident_hash": None, "away": None}
    if run["closed"]:
        j["verdict"] = "closed"
        return j
    ident, raw = read_identity(loops, iso)
    j["ident"], j["ident_hash"] = ident, hashlib.sha256(raw).hexdigest() if raw is not None else None
    if ident is not None:
        pid = _pid_of(ident.get("pid", ""))
        word = rt.proc_alive(pid, ident.get("pid_start")) if pid else "unknown"
        j["composer"] = {"live": "live", "dead": "dead"}.get(word, "unknown")
        j["nudge"] = ident.get("nudge", "none") not in ("none", "")
    seat, err = _quiet(rt.seat_state, rt.seat_paths(loops, iso))
    j["seat"] = seat[0] if seat else "unknown"
    # The run is judged from its log folder only when a journal ESTABLISHES that folder (round 71 PR-MED-038, the class
    # of HB0): `unreadable` — which the listing also gives a journal that says nothing, and (round 72 PR-MED-039) one
    # whose `log_root=` is there and cannot be used — and `none` are each a problem,
    # so the verdict is `unreadable`. A run with no journal keeps its records in the flat loops root; read from a
    # `<loops>/<iso>` folder that merely happens to exist it could be called `stalled` over records nobody read.
    problems = 0 if run["journal"] not in ("none", "unreadable") and run["marker"] != "unreadable" else 1
    stops, err = _quiet(rt.run_open_stops, log_root, iso)
    if err:
        stops, problems = [], problems + 1
    else:
        stops, stop_problems = stops
        problems += len(stop_problems)
    away, err = _quiet(rt.watch_away, os.path.join(loops, "%s-policy.log" % iso), iso, run["plan"] or "", log_root)
    if err or away is None:
        away, problems = {"state": "unreadable", "grant": None, "check": None, "takeover": None, "release": [], "problems": []}, problems + 1
    problems += len(away["problems"])
    j["away"], j["grant"], j["takeover"] = away, away["grant"], away["takeover"]
    read, err = _quiet(rt.watch_read, log_root)
    if err:
        records, lens, problems = [], {}, problems + 1
    else:
        records, lens, read_problems = read
        problems += len(read_problems)
    j["records"], j["lens"], j["problems"] = records, lens, problems
    legs, err = _quiet(rt.run_legs, log_root)
    if err:
        legs, problems = [], problems + 1
        j["problems"] = problems
    for leg in legs:
        j["legs"][leg["word"] if leg["word"] in j["legs"] else "unknown"] += 1
    if problems:
        j["verdict"] = "unreadable"
    elif stops:
        j["verdict"] = "parked"
    elif away["release"]:
        j["verdict"] = "release-in-flight"
    elif j["legs"]["live"]:
        newest = _newest_write(log_root)
        quiet = newest is None or now.timestamp() - newest >= cfg.leg_quiet_min * 60
        j["verdict"] = "leg-quiet" if quiet else "leg-running"
    elif j["legs"]["unknown"]:
        j["verdict"] = "leg-unknown"
    else:
        now_ts = now.timestamp()

        def advanced(minutes):
            return rt.run_advancement(records, since=now - datetime.timedelta(minutes=minutes), base=sample_for(st, now_ts, minutes * 60))

        def active(minutes):
            return rt.run_activity(records, since=now - datetime.timedelta(minutes=minutes), base=sample_for(st, now_ts, minutes * 60))

        def leg_ended(minutes):
            # D13's Step HB clause (round 66 MED-003): a leg's END — a `ROLE: end` record, placed by its own clock —
            # inside the window. Read for the VERDICT only, and only beside a composer whose process is alive: the
            # moment a wrapper ends no leg is live any more, and the newest advancing record is that leg's own start —
            # older than the window for any long leg — so the tick that lands before the composer's `CONSUME:` read a
            # run whose composer was about to consume as `stalled`, and sent its urgent notice. With the composer GONE
            # the same instant is D14's takeover at once and this is not asked. It is no advancement for the success
            # test or for a stall's end, which stay on run_advancement alone.
            since = now - datetime.timedelta(minutes=minutes)
            for _name, _end, raw in records:
                if raw.startswith("ROLE: end "):
                    t = _quiet(rt.watch_line_time, raw)[0]
                    if t is not None and t >= since:
                        return True
            return False

        written = run_written(loops, iso)
        if advanced(cfg.stall_min) or (written is not None and 0 <= now_ts - written < cfg.stall_min * 60):
            j["verdict"] = "progressing"
        elif j["composer"] == "live":
            window = cfg.nudge_min + cfg.nudge_margin_min if j["nudge"] else cfg.stall_min
            if leg_ended(cfg.stall_min) or (active(window) and advanced(NUDGE_INTERVALS * cfg.nudge_min)):
                j["verdict"] = "progressing"
    return j


def rejudge(rt, cfg, base, iso, st, now):
    """List the base's runs AGAIN and judge run `iso` AGAIN: `(runs, run, j)`,
    or None when the listing fails or no longer holds the run. THE ONE RULE
    for every lock the watcher acts under (round 49 PR-MED-030 at the seat's
    gate, round 50 PR-LOW-018 at the run's ledger): under a lock, act only on
    what was read under it — the listing, the judgement and the time `now`
    alike. This is the read both locks repeat; a caller that gets None acts
    on nothing, never on what it read before the lock."""
    listed, _err = _quiet(rt.watch_runs, base)
    runs, problem = listed or ([], "the run listing failed")
    run = next((r for r in runs if r["iso"] == iso), None)
    if problem or run is None:
        return None
    return runs, run, judge(rt, cfg, base, run, st, now)


# --------------------------------------------------------------------------- the identity's checks (D14)
def takeover_plan(rt, cfg, base, runs, run, j):
    """May this run be taken over, and with what: `(plan, None)` or
    `(None, "<word>")`. Every identity field is checked here and nowhere
    else; a plan holds only values that passed."""
    if not cfg.act:
        return None, "read-only"
    if not rt.seat_supported() or fcntl is None or not hasattr(os, "fork"):
        return None, "host-unsupported"
    away = j["away"] or {}
    if away.get("state") != "bound":
        return None, "not-bound"
    if j["takeover"] != "on":
        return None, {"off": "takeover-off", "malformed": "takeover-malformed"}.get(j["takeover"], "departure-mismatch")
    ident = j["ident"]
    if ident is None:
        return None, "no-identity"
    if j["composer"] != "dead":
        return None, "composer-alive" if j["composer"] == "live" else "composer-unknown"
    if ident.get("host") != "claude-code":
        return None, "host-unknown"
    session = ident.get("session", "")
    if not UUID_RE.match(session):
        return None, "session-malformed"
    if not run["default_root"] or j["seat"] == "none":
        return None, "no-seat"
    if j["seat"] != "free":
        return None, "seat-held" if j["seat"] == "held" else "seat-unknown"
    loops = os.path.join(base, ".cursor", "loops")
    if os.path.lexists(rt.seat_paths(loops, run["iso"])["mark"]):
        return None, "mark"
    cwd = ident.get("cwd", "")
    allowed = [rt.canon_path(base)] + [rt.canon_path(r["worktree"]) for r in runs if r["worktree"] and not r["closed"]]
    if not os.path.isabs(cwd) or not os.path.isdir(cwd) or rt.canon_path(cwd) not in allowed:
        return None, "cwd-off-list"
    config_dir = ident.get("config_dir", "")
    if not cfg.profile_dirs:
        return None, "no-allow-list"
    if not os.path.isabs(config_dir) or rt.canon_path(config_dir) not in cfg.profile_dirs:
        return None, "profile-off-list"
    if not _transcript_exists(config_dir, session):
        return None, "transcript-missing"
    if cfg.execs:
        exe = ident.get("exec", "")
        if not os.path.isabs(exe) or rt.canon_path(exe) not in cfg.execs:
            return None, "exec-off-list"
        exe = rt.canon_path(exe)
    else:
        exe = shutil.which("claude")
        if not exe:
            return None, "exec-missing"
        exe = os.path.abspath(exe)
    if not os.path.isfile(exe) or not os.access(exe, os.X_OK):
        return None, "exec-missing"
    # the directory the takeover is started in is the one that was CHECKED — its physical form, never the record's own
    # spelling, which a link could carry elsewhere between this check and the start (round 69 SEC-005)
    return {"session": session, "cwd": rt.canon_path(cwd), "config_dir": config_dir, "exec": exe, "ident_hash": j["ident_hash"],
            "pid": _pid_of(ident.get("pid", "")), "pid_start": ident.get("pid_start")}, None


def _transcript_exists(config_dir, session):
    projects = os.path.join(config_dir, "projects")
    try:
        names = os.listdir(projects)
    except OSError:
        return False
    for name in names:
        try:
            if stat.S_ISREG(os.lstat(os.path.join(projects, name, session + ".jsonl")).st_mode):
                return True
        except OSError:
            continue
    return False


# --------------------------------------------------------------------------- the acquisition (D12) and the stage
def takeover_argv(plan, iso):
    """The takeover's command: validated fields only, the fixed prompt, and
    never a permission-bypass flag or a settings-source flag."""
    if not ISO_ID_RE.match(iso) or not UUID_RE.match(plan["session"]):
        raise ValueError("unvalidated takeover field")
    return [plan["exec"], "-p", "--resume", plan["session"], TAKEOVER_PROMPT % iso]


def takeover_env(plan, nonce):
    """The takeover's environment: the watcher's own, with every LOOP_*
    variable and every session variable removed, LOOP_SEAT set to the
    takeover's nonce, and CLAUDE_CONFIG_DIR naming the identity's folder —
    left unset when that folder is the default one, as it is for the
    interactive session being continued."""
    env = dict((k, v) for k, v in os.environ.items() if not k.startswith("LOOP_") and k not in SESSION_ENV)
    env[SEAT_ENV] = nonce
    default = os.path.join(os.path.expanduser("~"), ".claude")
    if os.path.realpath(plan["config_dir"]) == os.path.realpath(default):
        env.pop("CLAUDE_CONFIG_DIR", None)
    else:
        env["CLAUDE_CONFIG_DIR"] = plan["config_dir"]
    return env


def acquire(rt, cfg, base, run, plan, out_base, hook=None, now=None, st=None, clock=None):
    """D12's acquisition, all of it under the run's gate. Returns one word:
      `started`              the byte was sent — a takeover is running
      `spawn-failed`         the held stage could not be started (COUNTED as
                             an attempt by the caller)
      `gate-busy` `no-seat` `mark` `eligibility-changed` `seat-held`
      `seat-unknown` `stopped`   nothing was started and nothing is counted
    THE ELIGIBILITY IS JUDGED AGAIN UNDER THE GATE, ALL OF IT (round 49
    PR-MED-030): the runs are listed again, this run's verdict is taken again
    (`judge`) and so is its plan (`takeover_plan`) — the grant still bound,
    its departure file still digesting to it and still saying `on`, no stop
    open, no release act in flight, no leg live or unknown, the run not
    closed, the composer's process still gone, the seat free, no mark. It
    goes on only when the verdict is still `stalled` and the plan is THE SAME
    plan the caller judged, the identity's hash included; anything else is
    `eligibility-changed` (the mark keeps its own word). Only readers run
    here, so the gate is never taken twice. A gated write — an interactive
    composer's `away end`, a must-pause, a release start — is either on the
    log before this read, and refuses the takeover, or waits for the gate
    until the takeover holds the seat, and is refused. What the gate does not
    order is a ROLE's own record, which takes no gate: a leg a role-owned
    write starts in this instant is seen by the next tick, not here.
    `st` is the tick's stored length samples. The TIME of this judgement is
    read under the gate as well (round 50 PR-LOW-018): `clock`, the tick's
    clock function, is called here — the real clock outside the selftest;
    `now` is a fixed time for a caller that has no clock to hand over, and
    with neither the real clock is read here.
    `hook(point)` is called at `eligible`, `seated`, `staged` and
    `published` — a seam for the selftest's interleavings; a hook that
    raises is a spawn that failed at that point. Every way out releases what
    it took: a seat this call locked is unlocked unless the byte was sent,
    and a stage that was never released ends when its pipe closes."""
    loops, iso = os.path.join(base, ".cursor", "loops"), run["iso"]
    paths = rt.seat_paths(loops, iso)
    try:
        gate = rt.seat_gate_take(paths, wait_s=ACQUIRE_GATE_WAIT_S)
    except Exception:
        return "gate-busy"
    if gate is None:
        return "no-seat"
    seat_fd, go_r, go_w, stage, log_fh = None, None, None, None, None
    try:
        # the eligibility, judged again under the gate — every D14 condition, through the same two functions
        if os.path.lexists(paths["mark"]):
            return "mark"
        try:
            # the time is read HERE, under the gate, like the rest (round 50 PR-LOW-018): the journal's write time counts
            # as advancement only when it is not later than the clock, so a clock read before the wait for the gate
            # would drop a state change written by the very writer this call queued behind
            when = clock() if clock is not None else (now or datetime.datetime.now().astimezone())
            fresh = rejudge(rt, cfg, base, iso, st or {}, when)
            if fresh is None:
                return "eligibility-changed"
            runs_now, run_now, j_now = fresh
            plan_now, _why = takeover_plan(rt, cfg, base, runs_now, run_now, j_now)
        except Exception:
            return "eligibility-changed"
        if j_now["verdict"] != "stalled" or plan_now is None or plan_now != plan:
            return "eligibility-changed"

        def at(point):
            if hook is not None:
                hook(point)

        try:
            at("eligible")
        except Exception:
            return "spawn-failed"
        try:
            seat_fd = os.open(paths["seat"], os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
        except OSError:
            return "seat-unknown"
        try:
            fcntl.flock(seat_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return "seat-held"
        try:
            nonce = secrets.token_hex(16)
            os.ftruncate(seat_fd, 0)
            os.lseek(seat_fd, 0, os.SEEK_SET)
            # the holder's record, WHOLE, before the stage is started (round 52 PR-LOW-020): a nonce cut short is not the
            # one the takeover carries, and every write it made would be refused
            _write_all(seat_fd, ("nonce=%s\nts=%s\nwatcher_pid=%d\n" % (nonce, rt.now_iso(), os.getpid())).encode("ascii"))
            os.fsync(seat_fd)
            at("seated")
            os.makedirs(os.path.dirname(out_base), exist_ok=True)
            log_fh = open(out_base + ".log", "ab")
            go_r, go_w = os.pipe()
            stage_argv = [sys.executable, os.path.abspath(__file__), "_stage", "--seat-fd", "%d" % seat_fd, "--go-fd", "%d" % go_r,
                          "--bound-s", "%r" % (cfg.takeover_max_min * 60), "--grace-s", "%r" % TAKEOVER_TERM_GRACE_S,
                          "--result", out_base + ".result", "--cwd", plan["cwd"], "--"] + takeover_argv(plan, iso)
            stage = subprocess.Popen(stage_argv, stdin=subprocess.DEVNULL, stdout=log_fh, stderr=subprocess.STDOUT,
                                     start_new_session=True, pass_fds=(seat_fd, go_r), env=takeover_env(plan, nonce), cwd=plan["cwd"])
            at("staged")
            # publication: the stage leads its own session, so its group is its pid — and with the number goes the stage's
            # START TOKEN (round 49 PR-HIGH-006), read while the stage is this process's own unreaped child: the one thing
            # that lets a later reader prove the group the text names is still this takeover's before it signals it
            _state, stage_token = rt.proc_start_token(stage.pid)
            # WHOLE, before the go byte (round 52 PR-LOW-020): a token cut short never proves the group, and a takeover
            # released behind it could not be stopped
            _write_all(seat_fd, ("pgid=%d\nstage_start=%s\n" % (stage.pid, stage_token or "unknown")).encode("ascii"))
            os.fsync(seat_fd)
            at("published")
        except Exception:
            return "spawn-failed"                 # at any point from the nonce to the publication: counted, nothing released
        if os.path.lexists(paths["mark"]):       # the mark's LAST read: after publication, before the byte
            return "mark"
        try:
            os.write(go_w, b"1")
        except OSError:
            return "stopped"                      # the held stage is gone — a stop signalled its published group
        stage = None                              # released: it is the takeover now, and no longer this call's to end
        return "started"
    finally:
        for fd in (go_w, go_r):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        if stage is not None:                     # never released: its pipe is closed, so it exits by itself
            try:
                stage.wait(timeout=10)
            except Exception:
                try:
                    os.killpg(stage.pid, signal.SIGKILL)
                    stage.wait(timeout=10)
                except Exception:
                    pass
        if seat_fd is not None:
            try:
                os.close(seat_fd)                 # this call's copy; a released takeover holds its own
            except OSError:
                pass
        if log_fh is not None:
            log_fh.close()
        rt.seat_gate_release(gate)


def cmd_stage(argv):
    """The takeover's HELD stage (internal — started by acquire, never by
    hand). It holds the seat's descriptor and does nothing until it reads one
    byte from the watcher; if that pipe closes first it exits, having started
    nothing. On the byte it starts the takeover as its one foreground child —
    the child inherits the seat's descriptor and the stage closes its own
    copy, so the seat's lock lives exactly as long as the takeover's process
    — waits for it under the wall-clock bound, and at the bound ends THAT
    process alone (TERM, a grace, KILL). A TERM, HUP or INT to the stage
    once it has read the byte is handled the same way — passed on to the
    takeover, the grace, the KILL — and the stage ends only after it: the
    group's leader stays for as long as the takeover lives (round 69
    SEC-003). Its handlers are installed BEFORE the takeover is started
    (round 70 PR-MED-036): a signal caught before the spawn starts nothing,
    and no takeover exists for an instant without them."""
    try:
        split = argv.index("--")
        opts = dict(zip(argv[0:split:2], argv[1:split:2]))
        seat_fd, go_fd = int(opts["--seat-fd"]), int(opts["--go-fd"])
        bound, grace = float(opts["--bound-s"]), float(opts["--grace-s"])
        result, cwd, cmd = opts["--result"], opts["--cwd"], argv[split + 1:]
        os.fstat(seat_fd)
        os.fstat(go_fd)
    except (ValueError, KeyError, OSError):
        return _refuse("_stage is the takeover's held stage — it is started by the watcher's acquisition, never by hand")
    if not cmd or not os.environ.get(SEAT_ENV):
        return _refuse("_stage is the takeover's held stage — it is started by the watcher's acquisition, never by hand")

    def finish(rc, detail):
        try:
            _write_atomic(result, ("rc=%d\ndetail=%s\nended=%s\n" % (rc, detail, datetime.datetime.now().astimezone().isoformat(timespec="seconds"))).encode("utf-8"))
        except OSError:
            pass
        return rc

    try:
        byte = b""
        while True:
            try:
                byte = os.read(go_fd, 1)
                break
            except InterruptedError:
                continue
    except OSError:
        byte = b""
    os.close(go_fd)
    if byte != b"1":
        return 0                                  # never released: nothing was started
    # THE STAGE OUTLIVES A TERM, HUP OR INT FOR AS LONG AS ITS TAKEOVER LIVES (round 69 SEC-003). It is the leader of the
    # takeover's group, and the stop command signals that group only while its LEADER proves itself (signal_authority):
    # a stage that died at the first TERM left a takeover that outlasts the TERM in a leaderless group — never sent the
    # KILL, the seat still held, and this function's own wall-clock bound gone with it. So a signal to the stage is
    # PASSED ON to the takeover (the group's TERM has reached it too) and the stage goes on waiting: the takeover gets
    # the grace, then this stage's own KILL; and the stop command's KILL to the group, which no process can catch,
    # still ends both at once.
    # THE HANDLERS ARE IN PLACE BEFORE A TAKEOVER CAN EXIST (round 70 PR-MED-036). Installed after the spawn, they left
    # the interval between the two: a signal there ended the stage by default while the takeover it had just started
    # lived on. Now they go in after the go byte and before the spawn. Up to the byte the stage keeps the default — a
    # held stage that is signalled, or whose pipe closes, ends having started nothing — and so does a signal whose
    # handler is not yet in: no takeover exists then. A signal CAUGHT before the spawn starts nothing either. One
    # caught at or after it finds this stage alive to end its takeover and reap it. No mask is used, so the takeover
    # inherits none; a caught signal's disposition is reset to the default by the takeover's own exec.
    caught = []
    for _name in ("SIGTERM", "SIGHUP", "SIGINT"):
        _sig = getattr(signal, _name, None)
        if _sig is not None:
            try:
                signal.signal(_sig, lambda signum, frame: caught.append(signum))
            except (ValueError, OSError):
                pass
    if caught:
        os.close(seat_fd)
        return finish(128 + caught[0], "a signal reached the stage before the takeover was started — nothing was started")
    try:
        child = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL, pass_fds=(seat_fd,))
    except OSError as e:
        os.close(seat_fd)
        return finish(127, "the takeover could not be started (%s)" % (e.strerror or type(e).__name__))
    os.close(seat_fd)                             # the lock is the takeover's own from here
    detail, how = "exited", None
    deadline = time.monotonic() + bound
    while True:
        try:
            rc = child.wait(timeout=0.2)
            break
        except subprocess.TimeoutExpired:
            pass
        if caught:
            how = "by a signal to the stage"
        elif time.monotonic() >= deadline:
            how = "at the wall-clock bound"
        if how is not None:
            detail = "ended %s (TERM)" % how
            child.terminate()
            try:
                rc = child.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                detail = "ended %s (KILL)" % how
                child.kill()
                rc = child.wait()
            break
    return finish(rc if rc >= 0 else 128 - rc, detail)


# --------------------------------------------------------------------------- acting (D14)
STOP_RECIPE = "python3 scripts/loop-watchdog.py stop --iso %s"


def notice_text(kind, iso, minutes=None):
    """A notice's whole body: fixed words, the validated run id, a number.
    Nothing read from a log, a plan or a departure file is ever placed."""
    stop = STOP_RECIPE % iso
    if kind == "stall":
        return ("run %s is stalled — no advancing record for %d min. Quitting the app does not stop an away run; to stop "
                "automatic continuation: %s" % (iso, minutes or 0, stop))
    if kind == "nudge":
        # what the watcher tests is a RECORDED nudge, a live composer and no advancement — it cannot see whether the
        # timer fired, so the text does not say it did (round 66 LOW-001)
        return ("run %s: the composer's nudge is not working — a nudge is recorded for this run and the run has not advanced "
                "for %d min. The composer's process is alive; it needs you. To stop automatic continuation: %s" % (iso, minutes or 0, stop))
    if kind == "give-up":
        return ("run %s: the watcher has stopped trying to continue it — the takeover limit is reached and the run is still "
                "stalled. It needs you. To stop automatic continuation: %s" % (iso, stop))
    if kind == "leg-quiet":
        return "run %s: a leg is running and has written nothing for %d min. To stop it: %s" % (iso, minutes or 0, stop)
    if kind == "leg-unknown":
        return ("run %s: a leg's state cannot be read (its process cannot be tied to the role) — nothing is continued until "
                "you look. To stop the run's roles: %s" % (iso, stop))
    return "run %s: its records could not be read — nothing is judged or continued until they can. To stop it: %s" % (iso, stop)


def send_notice(rt, kind, iso, minutes=None):
    sent, err = _quiet(rt.fire_notice, iso, notice_text(kind, iso, minutes), "must-pause")
    return "sent" if sent and not err else "failed"


def _backoff_s(cfg, step):
    """Seconds to wait after step `step` (from 0) before the next one; None
    when the steps are used up."""
    return cfg.backoff_min[step] * 60 if step < len(cfg.backoff_min) else None


LEDGER_CAP = 1 << 20


class Ledger(object):
    """The run's takeover ledger, `<base>/.cursor/loops/<iso>-takeovers`
    (round 49 PR-MED-033): the stall in progress — its start, its attempts,
    the takeover's step and when the next one is due, and the stall
    notice's own step and due time — and the times of the day's
    attempts, as one JSON object `{"day": [...], "stall": {...} | null}`.
    D14's limits belong to the RUN, so they are kept beside the run's
    journal and not in a watcher's own folder: two watchers over one base
    with different `--state-dir`s, or a watcher restarted with another one,
    read and write the same counts. An acting tick holds an exclusive lock
    on the file from before it reads the counts until after it has written
    them back, taken without waiting — a second watcher that finds it held
    leaves the run alone for that tick. The file is written in place through
    the locked descriptor (a replace would swap the inode under the lock).
    It is beside the run's log folder, never under it. A ledger that is
    there and cannot be parsed is never treated as empty: nothing is
    counted from it and nothing is started. `locked` says whether the lock
    is really held: where the filesystem refuses the lock call itself (or
    the host has no file locks) the ledger is read and written without one
    — that is not "another watcher holds it" — and act_on then sends the
    notices and starts no takeover."""

    def __init__(self, loops, iso):
        self.path = os.path.join(loops, iso + "-takeovers")
        self.fd = None
        self.locked = False                       # True only while this object holds the exclusive lock
        self.data = {"day": [], "stall": None}
        self.raw = b""

    @staticmethod
    def _parse(raw):
        if not raw.strip():
            return {"day": [], "stall": None}
        data = json.loads(raw.decode("utf-8"))
        if (not isinstance(data, dict) or not isinstance(data.get("day", []), list)
                or not all(isinstance(t, (int, float)) and not isinstance(t, bool) for t in data.get("day", []))
                or not (data.get("stall") is None or isinstance(data.get("stall"), dict))):
            raise ValueError("not a takeover ledger")
        stall = data.get("stall")
        if stall is not None and not isinstance(stall.get("attempts", []), list):
            raise ValueError("not a takeover ledger")
        return {"day": list(data.get("day", [])), "stall": stall}

    def peek_stall(self):
        """Does the ledger hold a stall in progress? Read without the lock,
        for the one question of whether a closed run still needs a line."""
        raw = _read_small(self.path, cap=LEDGER_CAP)
        try:
            return raw is not None and self._parse(raw)["stall"] is not None
        except (ValueError, AttributeError):
            return True

    def open(self):
        """Create the ledger if it is not there, lock it and read it:
        `ok`, `busy` (another watcher is acting on this run) or `unreadable`."""
        try:
            self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0), 0o644)
        except OSError:
            return "unreadable"
        try:
            if not stat.S_ISREG(os.fstat(self.fd).st_mode):
                return "unreadable"
            if fcntl is not None:
                try:
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.locked = True
                except OSError as e:
                    if e.errno in LOCK_BUSY_ERRNOS:
                        return "busy"             # HELD: another watcher is acting on this run this instant
                    # the lock call itself was refused — no lock service on this filesystem. That is not "somebody holds
                    # it", and reading it so would silence the run for good: go on unlocked, as on a host with no file
                    # locks; the caller sends its notices and starts no takeover (`ledger-nolock`)
            raw = os.read(self.fd, LEDGER_CAP + 1)
            if len(raw) > LEDGER_CAP:
                return "unreadable"
            self.data = self._parse(raw)
            self.raw = raw                        # the last complete record: what a failed write puts back
            return "ok"
        except (OSError, ValueError, AttributeError):
            return "unreadable"

    def save(self, st):
        """Write the run's counts back through the locked descriptor. A write
        that fails is StateSaveFailed (round 51 PR-LOW-019): the caller has
        taken no side effect that these counts limit, and takes none."""
        body = json.dumps({"day": st.get("day", []), "stall": st.get("stall")}, sort_keys=True).encode("utf-8")
        try:
            self._write(body)
        except OSError as e:
            raise StateSaveFailed(self.path, e)

    def _write(self, body):
        """The in-place write, WHOLE or failed (round 52 PR-LOW-020). A write
        that is cut short or fails would leave the new record's head over
        the old one's tail — a ledger no later tick can read, or the old
        record taken for the new. So on any failure the last complete record
        (what `open` read, or the last save that succeeded) is put back,
        best effort, before the error is raised: the record that stood still
        stands, and the run can be handled again when a write succeeds."""
        try:
            self._put(body)
        except OSError:
            try:
                self._put(self.raw)
            except OSError:
                pass
            raise
        self.raw = body

    def _put(self, body):
        os.lseek(self.fd, 0, os.SEEK_SET)
        _write_all(self.fd, body)
        os.ftruncate(self.fd, len(body))
        os.fsync(self.fd)

    def close(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
        self.locked = False


def act_on(rt, cfg, base, runs, run, j, st, now, ledger=None, clock=None, save_own=None):
    """Apply D14 to one judged run and keep its state `st` (mutated in
    place). Returns `(action, why)` for the run's line. Called with --act
    only. `st["stall"]` and `st["day"]` are the RUN's counts, read from its
    ledger by the caller and written back by it; `ledger` is that ledger,
    open, whenever the verdict is `stalled` — and locked, or no takeover is
    started (`ledger-nolock`). When a ledger is handed in, `runs`, `run`,
    `j` and `now` are what the caller read AFTER it took that ledger's lock
    (round 50 PR-LOW-018): an attempt read under the lock is never folded
    against a seat, a verdict or a time read before it. `clock` is the
    tick's clock function, handed on to the acquisition.
    A SIDE EFFECT IS TAKEN ONLY AFTER THE STATE THAT LIMITS IT IS DURABLE
    (round 51 PR-LOW-019). Each notice has a reservation — the dedupe key of
    a notify-only verdict, the nudge's once-per-stall flag, `done` for the
    give-up, the notice's OWN step for the stall notice (round 70
    PR-MED-037; where a takeover is allowed the attempt is reserved beside
    it, for the spawn) — and that reservation is set, WRITTEN, and only then is
    the notice sent: `save_own` writes the watcher's own state for this run
    (the notify-only dedupe lives there), the ledger writes the run's
    counts. A write that fails raises StateSaveFailed out of this function:
    nothing is sent or started for what could not be recorded, so a state
    folder or a ledger that cannot be written never turns into the same
    notice at every tick. A reservation that was written and a delivery
    that then failed reads `(failed)` and is not retried, as before."""
    iso, now_ts, verdict = run["iso"], now.timestamp(), j["verdict"]
    notices = st.setdefault("notices", {})
    actions, why = [], None

    def keep_own():
        if save_own is not None:
            save_own()

    def keep_counts():
        if ledger is not None:
            ledger.save(st)
    stall = st.get("stall")
    last = stall["attempts"][-1] if stall and stall.get("attempts") else None
    # the success test of an attempt that was started (D14)
    if last is not None and last.get("result") in ("open", "starting"):
        moved = rt.run_advancement(j["records"], base=last.get("base", {}))
        if moved or verdict in ("parked", "leg-running", "leg-quiet", "closed"):
            last["result"] = "success"
            actions.append("takeover:succeeded")
        elif j["seat"] != "held":
            last["result"], last["ended"] = "failed", now_ts
            wait = _backoff_s(cfg, len(stall["attempts"]) - 1)
            stall["next_at"] = now_ts + (wait if wait is not None else 0)
            stall["step"] = len(stall["attempts"])
            actions.append("takeover:failed")
        else:
            actions.append("takeover:running")
    # a stall ends only on advancement or one of these verdicts
    if stall is not None and (verdict in ("parked", "leg-running", "leg-quiet", "closed")
                              or rt.run_advancement(j["records"], base=stall.get("base", {}))):
        st.pop("stall", None)
        stall = None
    for kind in ("leg-quiet", "leg-unknown", "unreadable"):
        if verdict == kind:
            if kind not in notices:
                notices[kind] = now_ts
                keep_own()                        # the dedupe is durable BEFORE the notice it limits
                actions.append("notice:%s(%s)" % (kind, send_notice(rt, kind, iso, int(cfg.leg_quiet_min))))
        else:
            notices.pop(kind, None)
    if verdict != "stalled":
        return "+".join(actions) or "none", None
    if stall is None:
        stall = st["stall"] = {"since": now_ts, "base": j["lens"], "attempts": [], "step": 0, "next_at": now_ts,
                               "nudge_noticed": False, "done": False,
                               "notice_step": 0, "notice_at": now_ts, "notices_done": False}
    stalled_min = int((now_ts - stall["since"]) // 60 + cfg.stall_min)
    # the nudge-not-working notice: the composer alive, a nudge recorded, three intervals without advancement
    if (j["composer"] == "live" and j["nudge"] and not stall.get("nudge_noticed")
            and not rt.run_advancement(j["records"], since=now - datetime.timedelta(minutes=NUDGE_INTERVALS * cfg.nudge_min),
                                       base=sample_for(st, now_ts, NUDGE_INTERVALS * cfg.nudge_min * 60))):
        stall["nudge_noticed"] = True
        keep_counts()                             # once per stall: the flag is durable BEFORE the notice
        actions.append("notice:nudge(%s)" % send_notice(rt, "nudge", iso, int(NUDGE_INTERVALS * cfg.nudge_min)))
    attempts = stall["attempts"]
    if attempts and attempts[-1].get("result") in ("open", "starting"):
        return "+".join(actions) or "none", "takeover-live"
    plan, why = takeover_plan(rt, cfg, base, runs, run, j)
    if plan is not None and ledger is not None and not ledger.locked:
        # D14's limits are counted under the ledger's lock or not spent: where that lock cannot be had at all (the
        # filesystem refused the call) the notices go on and no takeover is started — the rule that gives a
        # filesystem without locks no seat
        plan, why = None, "ledger-nolock"
    # TWO SCHEDULES, NEVER ONE (round 70 PR-MED-037). The stall NOTICE has its own — `notice_step`, `notice_at`,
    # `notices_done`: four sendings AT MOST, 5, 15 and 45 minutes apart (a due one waits for an attempt in back-off, and
    # the give-up ends them — round 71 PR-LOW-032) — and the TAKEOVER has its own — `step`,
    # `next_at`, written only when an attempt that BEGAN has ended, and `done`, the give-up at the limits. As one
    # schedule, a stall that had only been notified about (its composer alive) had spent the steps a takeover needs: once
    # its four notices were out, `done` refused the first takeover for good when the composer then died, and before
    # that a notice's wait delayed it — against D14's "a takeover at once". A notice never spends a takeover, a takeover
    # that did not begin never spends a step, and neither schedule is reset by the other.
    if stall.get("done"):
        return "+".join(actions) or "none", why or "steps-done"
    notice_due = not stall.get("notices_done") and now_ts >= stall.get("notice_at", 0)
    if plan is None:
        if not notice_due:
            return "+".join(actions) or "none", why or ("backoff" if not stall.get("notices_done") else "steps-done")
    elif now_ts < stall.get("next_at", 0):
        return "+".join(actions) or "none", why or "backoff"
    # one step of the stall: the notice when one is due, and a takeover when one is allowed
    day = [t for t in st.get("day", []) if now_ts - t < DAY_S]
    st["day"] = day
    limit = None
    if plan is not None:
        if len(attempts) >= cfg.max_per_stall:
            limit = "per-stall-limit"
        elif len(day) >= cfg.max_per_day:
            limit = "per-day-limit"
    if limit is not None:
        plan, why = None, limit
        stall["done"] = True
        keep_counts()                             # ONE give-up notice: `done` is durable BEFORE it
        actions.append("notice:give-up(%s)" % send_notice(rt, "give-up", iso))
        return "+".join(actions), why

    def notice_step():
        # one sending of the stall notice spent: the next is due after the wait, and after the last wait none is
        wait = _backoff_s(cfg, stall.get("notice_step", 0))
        if wait is None:
            stall["notices_done"] = True
        else:
            stall["notice_at"], stall["notice_step"] = now_ts + wait, stall.get("notice_step", 0) + 1

    # the step's reservations, durable BEFORE its notice and BEFORE any spawn: the attempt where a takeover is allowed
    # (counted even if this tick is killed mid-acquisition), and the notice's own step where a notice is due
    if plan is not None:
        attempt = {"t": now_ts, "base": j["lens"], "result": "starting"}
        attempts.append(attempt)
        day.append(now_ts)
    if notice_due:
        notice_step()
    keep_counts()
    if notice_due:
        actions.append("notice:stall(%s)" % send_notice(rt, "stall", iso, stalled_min))
    if plan is not None:
        out_base = os.path.join(cfg.state_dir, base_key(base), iso, "takeover-%d" % int(now_ts))
        word = acquire(rt, cfg, base, run, plan, out_base, now=now, st=st, clock=clock)
        if word == "started":
            attempt["result"] = "open"
            actions.append("takeover:started")
            return "+".join(actions), None
        if word == "spawn-failed":
            attempt["result"], attempt["ended"] = "spawn-failed", now_ts
            wait = _backoff_s(cfg, len(attempts) - 1)
            stall["next_at"], stall["step"] = now_ts + (wait if wait is not None else 0), len(attempts)
            actions.append("takeover:spawn-failed")
            return "+".join(actions), None
        attempts.pop()                            # nothing was started and nothing is counted — and no step is spent:
        day.pop()                                 # the takeover's schedule moves only when an attempt that began has ended
        why = word
    return "+".join(actions) or "none", why


def _prune_samples(cfg, st, now_ts):
    keep = max(NUDGE_INTERVALS * cfg.nudge_min, cfg.stall_min, cfg.nudge_min + cfg.nudge_margin_min) * 60 + 600
    st["samples"] = [s for s in st.get("samples", []) if isinstance(s, dict) and now_ts - s.get("t", 0) <= keep][-2000:]


def tick(rt, cfg, base, now=None, out=_out):
    """Judge every live run of one base once; with cfg.act, act on each and
    keep the watcher's state. Prints one line per live run (and one for a
    run this watcher was tracking that has since closed). Returns the exit
    code.
    UNDER A LOCK, ACT ONLY ON WHAT WAS READ UNDER IT — THE TIME INCLUDED
    (round 50 PR-LOW-018; `rejudge` is the read, the acquisition keeps the
    same rule at the seat's gate). The tick lock is taken first and the runs
    are listed after it. For a run that has anything to count — it reads
    `stalled`, or it has a ledger — the ledger's lock is taken, and THEN the
    runs are listed again and the run judged again, on a clock read then;
    `act_on` is handed only that. The judgement made before the ledger keeps
    one use: deciding whether there is anything to count, that is whether
    the ledger is opened at all (a run that is not `stalled` and has no
    ledger reaches no shared count). So an attempt another watcher admitted
    a moment ago is never folded against a seat this tick read before it,
    and no wait runs from a time this tick read before the lock.
    `now` is the selftest's injected clock — a fixed time, or a function
    returning one; left out, each read above is the real clock.
    A tick lock that cannot be taken is two different things (round 50
    PR-LOW-017): HELD — another tick is acting on this base, nothing is
    done, exit 0; REFUSED — the filesystem took no lock at all: that is an
    environment failure, said on one line naming the lock, exit 3, and never
    reported as another tick.
    STATE THAT CANNOT BE KEPT IS A FAILED TICK, NEVER A NOTICE (round 51
    PR-LOW-019). `act_on` writes each reservation before the side effect it
    limits; a write that fails there, or in this function's own saves after
    it, is StateSaveFailed: that run's line reads `why=state-save` — with
    `action=error` when nothing was done, with what `act_on` did when only
    the last saves failed — no notice was sent and no takeover started
    without its record written first, the runs after it are still judged,
    and the tick ends with one `problem=state-save` line and exit 3. A ledger that cannot be
    opened or parsed is the same failure (`why=ledger-unreadable`, exit 3);
    a ledger another watcher holds this instant is not (`ledger-busy`)."""
    if callable(now):
        clock = now
    elif now is not None:
        clock = lambda: now                                       # noqa: E731 — the injected, fixed clock
    else:
        clock = lambda: datetime.datetime.now().astimezone()     # noqa: E731
    unsaved = []                          # (iso, path, reason) for each run whose state could not be kept (round 51 PR-LOW-019)
    lock = None
    if cfg.act:
        folder = os.path.join(cfg.state_dir, base_key(base))
        lock_path = os.path.join(folder, "tick.lock")
        try:
            os.makedirs(folder, exist_ok=True)
            if fcntl is not None:
                lock = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0), 0o644)
        except OSError as e:
            # an environment failure, said on one line with exit 3 like a refused lock — never a traceback (round 66 LOW-006)
            out("tick: base=%s problem=state-dir — the watcher's state folder %s could not be created or opened (%s). No run was "
                "judged and nothing was written; give --state-dir a folder this user can write"
                % (_word(base, 200), _word(folder, 200), e.strerror or "errno %s" % e.errno))
            return 3
        if lock is not None:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as e:
                os.close(lock)
                if e.errno in LOCK_BUSY_ERRNOS:
                    out("tick: base=%s another tick is acting on this base — nothing was done" % _word(base, 200))
                    return 0
                out("tick: base=%s problem=tick-lock — the state lock %s could not be taken (%s): the lock call itself was refused, which "
                    "is not another tick holding it. No run was judged and nothing was written; give --state-dir a folder on a filesystem "
                    "that takes file locks" % (_word(base, 200), _word(lock_path, 200), e.strerror or "errno %s" % e.errno))
                return 3
    try:
        runs, problem = _quiet(rt.watch_runs, base)[0] or ([], "the helper's run listing failed")
        if problem:
            out("tick: base=%s problem=listing — the loops directory could not be listed; no run was judged" % _word(base, 200))
            return 3
        for run in runs:
            iso = run["iso"]
            st = load_state(cfg, base, iso)
            st.pop("stall", None)                 # the run's counts are the ledger's, never this folder's
            st.pop("day", None)
            ledger = Ledger(os.path.join(base, ".cursor", "loops"), iso)
            tracked = bool(st.get("notices")) or (cfg.act and ledger.peek_stall())
            if run["closed"] and not tracked:
                continue
            acted = None                          # what act_on did for this run, once it has returned
            try:
                when = clock()
                j = judge(rt, cfg, base, run, st, when)
                listed = runs
                action, why = "read-only", None
                if cfg.act:
                    counted = j["verdict"] == "stalled" or os.path.lexists(ledger.path)
                    opened = ledger.open() if counted else "ok"
                    if opened == "ok":
                        if counted:
                            # the ledger's lock is held from here: everything acted on below is read NOW, never before it
                            when = clock()
                            fresh = rejudge(rt, cfg, base, iso, st, when)
                            if fresh is None:
                                out("run: iso=%s verdict=unreadable action=error why=listing" % iso)
                                continue
                            listed, run, j = fresh
                            st["day"] = ledger.data["day"]
                            if ledger.data["stall"] is not None:
                                st["stall"] = ledger.data["stall"]
                        action, why = act_on(rt, cfg, base, listed, run, j, st, when, ledger if counted else None, clock=clock,
                                             save_own=lambda: save_state(cfg, base, iso, st))
                        acted = action
                        if counted:
                            ledger.save(st)
                    else:
                        # another watcher holds the run's ledger this instant, or it cannot be parsed: nothing is
                        # counted and nothing is started — never a second budget beside the first
                        action, why = "none", "ledger-" + opened
                        if opened == "unreadable":
                            # a ledger that cannot be opened or parsed is state this tick cannot keep (round 51
                            # PR-LOW-019): nothing is sent — nothing could be recorded — and the tick is a FAILED one
                            unsaved.append((iso, _word(ledger.path, 200), "it cannot be opened or parsed"))
                    st.pop("stall", None)
                    st.pop("day", None)
                    if j["verdict"] == "closed":
                        st = {}
                    else:
                        st.setdefault("samples", []).append({"t": when.timestamp(), "lens": j["lens"]})
                        _prune_samples(cfg, st, when.timestamp())
                    save_state(cfg, base, iso, st)
                elif j["verdict"] == "stalled":
                    _plan, why = takeover_plan(rt, cfg, base, listed, run, j)
            except StateSaveFailed as e:
                # state this run needs kept could not be written (round 51 PR-LOW-019). No notice was sent and no takeover
                # started without its record written first; the runs after this one are still judged, and the tick as a
                # whole is a failed one. Where the failure came AFTER act_on had returned — this function's own last
                # saves — what act_on did was recorded before it was done, and stays on the run's line.
                unsaved.append((iso, _word(e.path, 200), getattr(e.error, "strerror", None) or "%s" % (e.error,)))
                if acted is None:
                    out("run: iso=%s verdict=%s action=error why=state-save" % (iso, j["verdict"]))
                    continue
                action, why = acted, "state-save"
            except Exception as e:
                # one run's files must never keep the runs after it from being judged
                out("run: iso=%s verdict=unreadable action=error why=%s" % (iso, type(e).__name__))
                continue
            finally:
                ledger.close()
            out("run: iso=%s verdict=%s composer=%s grant=%s takeover=%s seat=%s legs=live:%d,unknown:%d,over:%d problems=%d action=%s%s"
                % (iso, j["verdict"], j["composer"], "none" if j["grant"] is None else "%d" % j["grant"], j["takeover"] or "none",
                   j["seat"], j["legs"]["live"], j["legs"]["unknown"], j["legs"]["over"], j["problems"], action,
                   " why=%s" % why if why else ""))
    finally:
        if lock is not None:
            os.close(lock)
    if unsaved:
        iso, path, reason = unsaved[0]
        out("tick: base=%s problem=state-save — the watcher's state could not be kept for %d run(s); first, run %s: %s (%s). No notice "
            "was sent and no takeover started for them without its record written first; every other run was judged"
            % (_word(base, 200), len(unsaved), iso, path, reason))
        return 3
    return 0


def cmd_tick(rt, flags):
    if "--base" not in flags:
        return _refuse("tick requires --base </abs/base>")
    base = _abs_dir(flags["--base"], "--base")
    if not os.path.isdir(base):
        return _refuse("--base is not a directory", 3)
    cfg = Config(flags, rt)
    if cfg.act and session_guard():
        return 2
    return tick(rt, cfg, base)


# --------------------------------------------------------------------------- watch (D18)
def session_guard():
    """True (after one stderr line) when this process sits inside an agent
    session — where `watch` and `tick --act` never start."""
    held = [name for name in SESSION_ENV if os.environ.get(name)]
    if held:
        _refuse("the watcher is started by the operator OUTSIDE any agent session (a user service or a terminal) — %s is set in this "
                "environment; a watcher started here would die with this session's process tree and its takeovers would be this "
                "session's children. Nothing was started" % held[0])
    return bool(held)


_WATCH = {"stop": False}


def _watch_signal(signum, frame):
    _WATCH["stop"] = True


def cmd_watch(flags):
    if session_guard():
        return 2
    bases = [_abs_dir(b, "--base") for b in flags.get("--base", [])]
    if not bases:
        return _refuse("watch requires at least one --base </abs/repo> (and a --profile-dir for any takeover)")
    for b in bases:
        if not os.path.isdir(b):
            return _refuse("--base is not a directory: %s" % _word(b, 200), 3)
    cfg = Config(flags)
    try:
        interval = float(flags.get("--interval-s", "%r" % WATCH_INTERVAL_S))
        ticks = int(flags.get("--ticks", "0"))
    except ValueError:
        raise Usage("--interval-s is a number of seconds and --ticks a whole number")
    if not (0 < interval <= 86400) or ticks < 0:
        raise Usage("--interval-s is between 0 and one day; --ticks is 0 (forever) or more")
    own_hash = script_hash(os.path.abspath(__file__))
    for signum in (signal.SIGTERM, signal.SIGINT) + ((signal.SIGHUP,) if hasattr(signal, "SIGHUP") else ()):
        signal.signal(signum, _watch_signal)
    rounds = 0
    failed = {}                           # base -> the word for its LAST tick, while that tick did not end 0 (round 50 PR-LOW-017)

    def beat():
        try:
            write_heartbeat(cfg.state_dir, own_hash, bases, datetime.datetime.now().astimezone().isoformat(timespec="seconds"), interval,
                            failed)
        except OSError as e:
            _out("watch: the heartbeat could not be written (%s)" % e.strerror)

    beat()                                # before the first round: a composer that asks at once is told the watcher runs
    while not _WATCH["stop"]:
        for base in bases:
            if _WATCH["stop"]:
                break
            script = os.path.join(base, "scripts", SCRIPT_NAME)
            if not os.path.isfile(script):
                _out("watch: base=%s has no scripts/%s — not judged this round" % (_word(base, 200), SCRIPT_NAME))
                failed[base] = "no-script"
                continue
            # every repository is judged by its OWN installed script and helper; the whole configuration rides argv
            argv = [sys.executable, script, "tick", "--base", base, "--act"] + cfg.to_argv()
            try:
                child = subprocess.Popen(argv, stdin=subprocess.DEVNULL)
            except OSError as e:
                _out("watch: base=%s tick could not be started (%s)" % (_word(base, 200), e.strerror))
                failed[base] = "not-started"
                continue
            deadline = time.monotonic() + TICK_TIMEOUT_S
            ended_by = None
            while child.poll() is None:
                if _WATCH["stop"] or time.monotonic() >= deadline:
                    ended_by = "stop" if _WATCH["stop"] else "timeout"
                    child.terminate()
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()
                    break
                time.sleep(0.05)
            # the base's last tick result, for the heartbeat: a tick this watcher ended because it is itself stopping says
            # nothing about the base, so the result before it stands — and so does a tick that died of the very signal
            # that is stopping this watcher (a Ctrl-C reaches the whole foreground group)
            if ended_by is None and _WATCH["stop"] and child.returncode != 0:
                ended_by = "stop"
            if ended_by == "timeout":
                failed[base] = "timeout"
            elif ended_by is None and child.returncode == 0:
                failed.pop(base, None)
            elif ended_by is None:
                failed[base] = "exit-%d" % child.returncode if child.returncode > 0 else "signal-%d" % -child.returncode
            if ended_by != "stop" and base in failed:
                _out("watch: base=%s its tick ended %s — that base was not judged as it should be this round (the tick's own lines say "
                     "what failed); the heartbeat says so until a tick of it ends 0"
                     % (_word(base, 200), failed[base]))
        beat()
        rounds += 1
        if ticks and rounds >= ticks:
            break
        wake = time.monotonic() + interval
        while not _WATCH["stop"] and time.monotonic() < wake:
            time.sleep(min(0.2, max(0.0, wake - time.monotonic())))
    _out("watch: stopped after %d round(s)" % rounds)
    return 0


# --------------------------------------------------------------------------- entry
def main(argv):
    # the role guard: first, so a role gets this line whatever follows the
    # script's name, and an install missing its helper still refuses
    if os.environ.get("LOOP_ROLE"):
        _stderr_line(ROLE_REFUSAL)
        return 2
    if argv and argv[0] == "_stage":
        return cmd_stage(argv[1:])
    if not argv or argv[0] in ("--help", "-h"):
        sys.stdout.write("usage: python3 scripts/%s identity | seat | stop | tick | watch  [flags]\n" % SCRIPT_NAME
                         + "".join("  %s: %s\n" % (sub, " ".join(sorted(g["value"] + g["multi"] + g["bool"])))
                                   for sub, g in SUB_FLAGS.items()))
        return 0 if argv else 2
    sub = argv[0]
    if sub not in SUB_FLAGS:
        return _refuse("unknown subcommand %r — identity | seat | stop | tick | watch" % sub[:40])
    try:
        flags = parse_args(sub, argv[1:])
        if sub == "watch":
            _configure_std_streams()      # no helper is loaded for `watch`: its lines are UTF-8 with LF by this call
            return cmd_watch(flags)
        rt = load_helper(str(Path(__file__).resolve().parent / HELPER_NAME))
        rt._configure_std_streams()
        return {"identity": cmd_identity, "seat": cmd_seat, "stop": cmd_stop, "tick": cmd_tick}[sub](rt, flags)
    except Usage as e:
        return _refuse(str(e))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
