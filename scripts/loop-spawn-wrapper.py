#!/usr/bin/env python3
"""scripts/loop-spawn-wrapper.py — the /execute-loop spawn wrapper (v45.0; the
Python implementation of plan-windows-port-and-router D2 / D7 / D13–D20 / D30–D32).

ONE cross-platform implementation of what `scripts/loop-spawn-wrapper.sh`
implemented in bash through v44.0. The `.sh` stays as a thin exec SHIM (D13):
every downstream grant shape `bash scripts/loop-spawn-wrapper.sh` keeps
working — the shim resolves `python3`, blob-verifies THIS file against
`HEAD:scripts/loop-spawn-wrapper.py`, silences MSYS's path converter and
`exec`s `python3 -I scripts/loop-spawn-wrapper.py` from the caller's cwd.
The shim's usage header is the parameter contract's documentation of record
(the 32 `LOOP_*` variables — `LOOP_SURVIVE` the 32nd, from v48.0 — their
grammar and every refusal); this module
restates only what the port CHANGES in mechanism. The CONTRACT is frozen (D7):
the same `LOOP_*` environment transport, the same stdout tokens with the
same key sets and order, the same `SPAWN_REFUSED` classes and refusal ORDER
(`params`, `param-file`, `escape-pre`, `role-start`, `pump-start` — and, from
v47.0, ONE more: `resume-pin`, the first change to that list since the
freeze; its three positions are in the v47.0 item below),
the same probe-log records (SPAWN_WRAPPER_START, the helper-emitted ROLE:
start / OWNERSHIP: escape-check / OWNERSHIP: exit-census, EXIT:<code>) and
the same exit codes (the child's code — 126 / 127 when it cannot be executed,
bash's background-job codes; 1 when LOOP_CWD cannot be entered post-START;
2 refusal; 3 lock held; 4 the fold-in on a successful child; 129/130/143 a
forwarded HUP/INT/TERM). v48.0 ADDS to that contract, and changes none of
it: one probe-log record — the wrapper's own `ROLE: end`, before the footer
— one `LOOP_*` variable (`LOOP_SURVIVE`), the per-leg files, two
`SPAWN_WARN` check words (`role-end`, `survive`), and, under the split, two stdout lines
(`SPAWN_DETACHED`, `SPAWN_LOST`) with two exit codes of the tail's own (5,
6); the v48.0 item below has each.

WHAT CHANGES IN MECHANISM (D15 / D17 / D18 / D19 / D20 / D30)
  * The shared RUNTIME is imported from the blob-verified SNAPSHOT of the
    records helper (`scripts/loop-journal.py` copied into the private
    workspace and re-verified against HEAD — the v44.0 snapshot discipline,
    now also the import source, D30): the route collector `route_collect`
    with its constants, the folder rule `route_dir_word`, the sanitizer
    `route_skipped_text`, the process-group / Job primitive `group_launch` /
    `group_members` / `group_stop` / `group_close` + `exit_census`, and
    `canon_path` / `path_inside`. The checkout copy is never imported after
    the spawn starts, so an `/update-workflow` mid-run cannot change a running
    spawn's runtime (the property the bash brace group gave; a Python program
    is compiled whole before it runs, so the in-place rewrite guarantee holds
    for this file by construction).
  * The PRE-IMPORT validations (everything up to the helper gate) run on a
    wrapper-local BOOT TWIN of the lexical path policy — `_boot_spell`
    (≡ `canon_path(p, resolve=False)`: `\\` → `/`, the MSYS `/c/…` → `C:/`
    conversion under MSYSTEM, an upper-case drive letter; SPELLING only, no
    normpath) and `_boot_inside` (≡ `path_inside`: `/` the separator) with
    `os.path.realpath` for the route block's physical resolution — pinned to
    the runtime's functions by the selftest's shared case table. After the
    import the runtime's `canon_path` runs once over every value and every
    later consumer uses the runtime's functions. No refusal moves.
  * The spawn lock is wrapper-local (D19 / D32): `fcntl.flock` on POSIX;
    `msvcrt.locking` of ONE byte at the fixed far offset 0x7FFFFFFE on
    Windows (appends never reach it; the holder line is written unlocked and
    read bounded to st_size).
  * The role-log pump is ONE design on every host, wrapper-private (D18): a
    pipe plus a reader thread writing the append-opened role-log descriptor
    and mirroring to stdout with the v33.4 wake-noise filter — the same
    byte-immediacy, closed-mirror (EPIPE → /dev/null), oversized-line,
    fail-open classification and last-resort passthrough rules as the v44.0
    `PUMP_SRC`; the FIFO, the keeper descriptor, `/dev/fd` and the separate
    pump process are gone, so the FIFO-only refusal classes `pump-writer` /
    `pump-start` retire (the thread-start refusal keeps the `pump-start`
    name). The rewrite count never leaves the process (no count file). A
    pump that does not drain within the bound after the child exits (an
    orphan holding the pipe's write end) is abandoned and folded exactly as
    today (`unconfirmed`, rc 4); a failed role-log sink is sticky and exits
    the pump 3 (rc 4 on a successful child).
  * The child runs inside the runtime's group — a new session on POSIX (its
    pid the pgid), a Job Object with KILL_ON_JOB_CLOSE on Windows — and the
    exit census is the runtime's (`ps -eo pgid=,pid=` / the Job's process
    list; `children=0` only when the census succeeded — D20). On Windows the
    Job dies with the wrapper (D28), so survivors do not outlive it there.
  * The prompt-file acquisition is in-process: the file is opened O_NONBLOCK,
    type-checked on the OPENED DESCRIPTOR (never the pathname again) and read
    whole; a FIFO or a directory fails the regular-file check at once, so no
    bound tool (`timeout` / `gtimeout`) exists and no subprocess ever sees
    the prompt bytes.
  * `LOOP_ADD_DIRS` splits on `;` on a Windows-native host and on `:`
    elsewhere (D31); every helper call is `sys.executable -I <snapshot>`
    (D14 — never a PATH lookup of `python3`); the standard streams are
    UTF-8 + LF at this entrypoint (guarded; never through an imported
    module's main()).
  * v46.3 (plan-spawn-time-shield D2): the invocation build renders
    `--setting-sources user,project` on EVERY command line — both tiers, a
    fresh spawn and a resume, exactly once, directly after `--verbose` — so
    the role is started without the `local` settings source
    (`.claude/settings.local.json` is not among the sources the command line
    names; the profile's user settings and the checkout's committed
    `.claude/settings.json` stay loaded). What the flag keeps out is the
    CLI's to honour — in full from Claude Code 2.1.314 by its changelog; an
    older CLI may still take some settings from the excluded file. The value
    is a constant of this source: no `LOOP_*` variable, file or plan text
    reads, changes or removes it. The rendered command line is no part of
    the frozen contract above, and nothing reads it back.
  * v46.4 (plan-loop-field-review-fixes D1): the identity record's `session=`
    comes from the bytes added to the role log since THIS LEG opened it.
    Every leg of a role appends to one role log unless the log is rotated, so
    the wrapper records the log's size once it has opened it for the leg
    (after any rotation, before the child starts) and the post-wait
    session-id read is at most 262,144 bytes from that offset — never the
    file's head, which holds the first leg's id. Those bytes are the leg's
    own unless another writer appends to the same file meanwhile (a second
    wrapper on one role log — what the optional `LOOP_SPAWN_LOCK` rules out).
    When they carry no `"session_id"` the record gets no `session=` line. No
    record, stdout token or exit code changes.
  * v47.0 (plan-loop-autonomy-group-2 D10): THE RESUME PIN. A
    `LOOP_RESUME_SESSION` spawn is started on the profile folder that holds
    the session's transcript, or it is not started. The id must be a UUID
    (8-4-4-4-12 hex digits; anything else is a `params` refusal). The
    CANDIDATES, in tie order: `LOOP_PROFILE_DIR`; the router's answer, when
    the router gave one and it passed the answer rule's folder checks; the
    AMBIENT folder — the `CLAUDE_CONFIG_DIR` this wrapper inherited, else
    `~/.claude` under THIS process's home (one known limit: a Windows binary
    started through WSL interop — a `/mnt/…` `LOOP_CLAUDE_BIN` — with no
    `CLAUDE_CONFIG_DIR` keeps its transcripts under the Windows profile, which
    is not that folder; such a resume must name the folder as
    `LOOP_PROFILE_DIR`, or it is refused as held nowhere — and a FRESH such
    spawn with no profile records this same default as `profile_dir=`, which
    there is not the folder the role ran on). A relative folder (`LOOP_PROFILE_DIR` or the inherited
    variable) is searched as the role will see it — against `LOOP_CWD`, never
    this wrapper's own working directory — and is named by that path; two
    candidates that name one path are one. The inherited variable reaches the
    role UNCHANGED, so it is resolved as a native process resolves it, never
    by the MSYS conversion (which only a value the wrapper exports gets): on
    a Windows host a `/`-rooted value — a `/c/…` one included — lands on
    `LOOP_CWD`'s drive, and a drive-relative `X:name` under `LOOP_CWD` when X
    is its drive; on any other drive the folder cannot be established from
    here, and the candidate is indeterminate (the same holds for a
    drive-relative `LOOP_PROFILE_DIR`). Each candidate reads one of three
    ways:
      - it HOLDS the session: some `projects/<any>/<session>.jsonl` under it is
        a regular file whose modification time was read (the newest, when more
        than one project folder has the file);
      - it DOES NOT: the folder or its `projects/` does not exist (or is not a
        folder), or every entry of `projects/` was looked in and none has the
        file;
      - it is INDETERMINATE: the folder, `projects/` or one of its entries
        could not be read, or the name is there but is no regular file, is a
        link that resolves to nothing, or its time could not be read — or
        the folder itself cannot be established (above).
    ONE indeterminate candidate refuses the spawn, naming the folder — an
    older readable copy is never chosen over a folder that could not be
    searched. Among the holders the HOLDER is the one with the newest
    transcript; equal times go to the earlier candidate in the order above.
    No holder refuses. Under router mode a holder that is not the router's
    answer must pass the answer rule's folder checks, or the spawn is refused
    (the newest copy is never passed over for one in an acceptable folder).
    Under a token-pool selection (`LOOP_OAUTH_TOKEN_ENV`) the holder must be
    `LOOP_PROFILE_DIR` itself, or the spawn is refused the same way: the
    pool's token is bound to that folder (v32 TD.2), so it is never started
    on another one, and an older copy in `LOOP_PROFILE_DIR` is never chosen
    over a newer one elsewhere.
    The role is started on the holder: the holder exported as
    `CLAUDE_CONFIG_DIR` — except an ambient holder, for which the inherited
    environment is left exactly as it was. The holder is read ONCE MORE
    immediately before that export; a transcript that no longer reads as held
    refuses. The refusal is `SPAWN_REFUSED check=resume-pin`, exit 2, at one
    of three positions: (1) with no router configured, the LAST refusal of
    the validation block — before START, no probe-log write; (2) under router
    mode, after the pick and before `ROLE: start` — the START / EXIT:2 pair
    (the `escape-pre` shape); (3) the second read, on either timing — after
    `ROLE: start`, before any child (START, `ROLE: start`, EXIT:2 — the
    `pump-start` shape). Two stdout lines, both after the first
    STICKY_REREAD and before `ROLE: start`: `SPAWN_WARN check=resume-pin
    detail="<holder>"` when the holder is not the folder the spawn was given
    (`LOOP_PROFILE_DIR`; the ambient folder when that is unset), and
    `SPAWN_WARN check=resume-pin-stale detail="<folder>[; <folder>]"` when
    another candidate holds a strictly older copy. Under router mode the
    answer is honoured (`SPAWN_ROUTE`) exactly when it is the holder —
    whatever its `sticky` flag; an answer that is not the holder is the
    existing `check=router detail="resume-mismatch"` pair, and the role runs
    on the holder, which is no longer always `LOOP_PROFILE_DIR`. A folder
    name is printed with control bytes and double quotes turned into spaces.
    The identity record carries `profile_dir=` on EVERY spawn, a fresh one
    included: the folder the role runs on, the ambient folder when nothing
    else was selected (the line is left out only when that name holds a
    control byte, which one line cannot carry, or when the ambient folder
    cannot be established). A fresh spawn's command line,
    environment, stdout lines and probe-log records are unchanged.
  * v48.0 (plan-loop-autonomy-group-2 D16 / D23 / D12): ROLES THAT OUTLIVE
    THE COMPOSER. Three things, the first two on every host and in every
    mode.
    (1) THE PER-LEG FILES, beside the probe log. At the top of run() —
    before the validation's first side effect — the launching process
    claims `<leg>.live` by creating it exclusively (`<leg>.2.live` … when a
    file of that name is there: a leg value used twice never overwrites the
    earlier leg's evidence; a reader goes by the `leg=` line inside). It
    holds `ts run role leg wrapper_pid wrapper_start survive` (`survive=` is
    `off`, `on`, `unverified` or `in-tree` — round 42, below); right after
    the role is launched it is replaced atomically to add `role_pid
    role_start role_pgid`; and as the wrapper's LAST act, on every path it
    returns by — a refusal, a held lock and a forwarded-signal end included
    — it becomes `<leg>.exit`, which keeps those lines and adds
    `launched=no|yes|unknown exit=<code> exit_ts= census=<survivors>|failed|
    none`. A wrapper that does NOT return — killed outright, or ended by a
    signal before START, when its handlers are not yet installed — leaves
    `<leg>.live` as it stood: the reader then goes by the processes, and a
    wrapper that died before it recorded a role reads `unknown`. `.exit` says the
    WRAPPER finished; whether the role's work has stopped is the runtime's
    role-liveness reader's to say (`run_legs` in the helper), which the
    close's guard and the watcher ask. The start tokens are the runtime's
    `proc_start_token` — and, for this wrapper's own token and the tail's
    test, its boot twin `_boot_start_token` (pre-import; pinned to the
    runtime's by the selftest). The claim needs names it can build from the
    raw environment: an absolute LOOP_PROBE_LOG in an existing folder and
    a LOOP_RUNKEY / LOOP_LEG of `[A-Za-z0-9._-]`. A spawn without them —
    or whose log folder refuses the new file, or whose leg value was used
    99 times — writes no per-leg file, runs single-process and is REFUSED
    before START: by the validation's own earlier refusal where one applies
    (each keeps its place and text), else by a `params` refusal once the
    logs are open. NO ROLE IS STARTED WITHOUT ITS `<leg>.live`.
    (2) THE END OF THE LEG (D23). Whenever this wrapper wrote the leg's
    `ROLE: start` it writes its `ROLE: end` — through the helper, with
    `--log` (so a second end for the leg is refused), before the `EXIT:`
    footer, which stays the log's last line, and before the helper snapshot
    is removed; on a normal exit and on a forwarded-signal one. The end and
    the footer are two separate appends, the end first: a wrapper killed
    before its teardown writes neither — the leg then has a start and no
    end, the composer's clean-close case — and one killed between the two,
    or whose footer append failed (that error is passed over), leaves the
    end with no footer; a missing footer never shows a missing end, and
    `<leg>.exit` is written later still. `result=` is
    mechanical: `exit <the footer's code>; handoff` when the code is 0 and
    the LAST result event of this leg's stream ends in a `ROLE: handoff `
    line, else `incomplete: exit <code>; handoff|no handoff`; `duration=`
    is whole seconds since the start was written. A post-START exit that
    never wrote the start writes no end. A helper refusal there prints
    `SPAWN_WARN check=role-end …` and never changes the exit code. The
    composer's judgment is its `CONSUME:` record.
    (3) THE SPLIT (POSIX; wherever `os.fork` exists; `LOOP_SURVIVE=off`
    restores the single process — the same records, the per-leg files and
    the end included). After the claim the process forks TWICE. The first
    child calls `os.setsid()`, forks again and leaves at once by `os._exit`
    — it writes nothing and opens nothing, and the launching process reaps
    it. The grandchild is the SUPERVISOR: today's wrapper, a member (not
    the leader) of that new session and, its parent gone, the child of
    whichever process adopts orphans there — the host's first process, or
    a nearer ancestor that asked for them. Where that adopter is ABOVE the
    composer, the supervisor is no longer in the composer's process tree,
    and a composer's `claude`, which on a TERM, a HUP or a deliberate quit
    signals every process of its task's tree by parent pid, does not reach
    it (read 2026-11-15 on Linux, Claude Code 2.1.321–2.1.325; an app quit
    and an app crash were NOT read, and a one-fork supervisor in its own
    session with a live parent was seen to die). Where the adopter is the
    composer or a process under it, the supervisor is still in that tree:
    `<leg>.live`'s `survive=` says which it is (round 42, below). Its stdin is the null device and its stdout / stderr are appended
    to `<leg>.out` / `<leg>.err`, so a dead host cannot break a helper
    call's output. Every pid this wrapper records — `wrapper_pid` in the
    identity record, the lock's holder line and `<leg>.live`, the router's
    `--pid` — is the supervisor's; a TERM / INT / HUP to that pid stops the
    role exactly as before (143 / 130 / 129, the footer, the end).
    The launching process becomes the TAIL: it only follows the two files to
    its own stdout / stderr. The supervisor is not its child, so it does not
    wait for it: it exits with the code `<leg>.exit` records once that file
    appears; a supervisor whose start token has gone with no `.exit` gives
    the tail ONE fixed code of its own, 6, and one line `SPAWN_LOST
    supervisor_pid=<n> detail="…"` ("128 + the signal" cannot be read for a
    process that is not one's child). In both closing lines `<n>` reads
    `unknown` where no supervisor's pid is known — one that could not be
    forked (there the TAIL writes `<leg>.exit` itself, `launched=no
    exit=6`: nothing was started), one that never recorded itself. A TERM,
    HUP or INT to the tail ends
    the TAIL ALONE — exit 5 and one line `SPAWN_DETACHED
    supervisor_pid=<n>` — whatever the leg is doing: a role that is
    running runs on, and a signal that arrives during the last forwarding
    of a leg that has already ended (or been lost) is answered the same
    way, never with the leg's code (round 42) — code 5 says the tail was
    ended by a signal, and the leg's state is in its files; 129 / 130 /
    143 keep their meaning. A role that exits 5 or 6 is told apart by that
    line's absence.
    A host that refuses the first fork gets the single process and one line,
    `SPAWN_WARN check=survive detail="…"`; a supervisor that cannot create
    its two output files or record itself in `<leg>.live` starts nothing
    (the tail's `SPAWN_LOST`, after its 30 s bound).
    Round 41 made three things of the split exact. THE HANDSHAKE: every
    blockable signal is blocked across the two forks, so the first child is
    never ended or interrupted between its fork and its exit by a signal
    aimed at the tree; its status is 0 or one fixed code (its setsid or
    fork raised), and the tail writes `launched=no` on that code ALONE — a
    first child that was killed, or whose status is not known inside a
    bound, proves nothing and writes nothing; and the supervisor neither
    records itself nor runs the leg until its parent is no longer the
    first child (past a bound it starts nothing), so no role is ever
    started by a process whose parent is still the first child (whether
    the NEW parent is outside the composer's tree is round 42's rule,
    below). A
    TERMINATED SUPERVISOR THAT NOBODY REAPS (a zombie keeps its pid and
    its start token) is lost to the tail like one that is gone — the same
    `SPAWN_LOST`, after the same one more read of `<leg>.exit`; the
    reader's rule that a zombie still holds its pid and its group is
    unchanged. THE MIRRORS: the tail never writes to its own stdout or
    stderr — a thread per mirror does, behind a bounded queue — so a
    launcher that keeps a pipe open and stops reading cannot keep the tail
    from returning the leg's code or from ending on a signal; the last
    forwarding is given up once a mirror has accepted nothing for five
    seconds, and what a mirror did not take is in `<leg>.out` /
    `<leg>.err`.
    Round 42 added two rules. WHAT `survive=` MAY SAY (PR-MED-028): a new
    parent is not yet a place outside the composer's tree — an orphan is
    given to the nearest living ancestor that adopts orphans (a child
    subreaper), and only failing one to the host's first process. So,
    once re-parented and before it records itself or starts a role, the
    supervisor reads its own ancestors and compares them with the
    composer's pid — `CLAUDE_PID` from the inherited environment, when it
    is a decimal pid and an ancestor of the launching process. `<leg>.live`
    then says `survive=on` only when that is ESTABLISHED (the composer is
    not among the supervisor's ancestors); `survive=in-tree` when the
    composer still is — the leg RUNS, still split (the launched process is
    the tail, and a signal to it still ends the tail alone),
    and says so in one stdout line, `SPAWN_WARN check=survive detail="the
    supervisor was re-parented to pid <n>, …"`: it will not outlive the
    composer's process tree; and `survive=unverified` when it cannot be
    told (no `CLAUDE_PID` — any composer but Claude Code — or one that is
    not an ancestor of the launching process, or a chain that could not be
    read): the split was taken and nothing more is claimed. `survive=off`
    is the single process. THE CLOSING LINE AND THE LAST FORWARDING
    (PR-MED-029): the last forwarding looks at the tail's signals on every
    turn and stops at once — a TERM, HUP or INT then gets code 5 and
    `SPAWN_DETACHED`, not the leg's code; and the tail's own closing line
    (`SPAWN_DETACHED`, `SPAWN_LOST`) is bounded in wall time, not by a
    mirror's progress: what is queued gets half a second, what is still
    unwritten is dropped (it is in the per-leg file), and the line, alone
    on the queue and at a line start, gets two seconds.
    Round 43 made that rule one for every wait of the tail (PR-LOW-014).
    A signal is acted on only where the tail next looks at what its
    handler caught, so each of its waits either looks on every turn and
    ends at once — the wait for the first child's status, the last
    forwarding, both waits of a `SPAWN_LOST` line, the poll, the probes of
    the supervisor where they are a `ps` run — or is one of the two
    bounded waits of the `SPAWN_DETACHED` line itself; and every way out
    that is not a signal's takes one last look immediately before it
    returns. So a TERM, HUP or INT the tail has SEEN by that look is
    answered with code 5 and `SPAWN_DETACHED` — also when the tail had
    already decided on 6, and then a `SPAWN_LOST` line that was already
    on its way out may stand above the `SPAWN_DETACHED` one; a signal that
    lands after the look finds a process already ending with its code. A
    signal changes the tail's code and line, and withholds no record the
    tail has the evidence for: a failed fork whose status the tail has
    read keeps its `launched=no` in `<leg>.exit` either way (the status
    is read once even when a signal is already caught; a first child that
    has not exited by then leaves it unknown, and nothing is written).
    Round 44 took the same rule to every blocking call on the split's
    paths (PR-LOW-015). A leg record's own start token, once it has been
    read, is KEPT with its pid — the launching process reads it for the
    claim, the supervisor (another pid) for its `<leg>.live` — so no later
    record of that process runs a `ps` for it; where none was kept (the
    read gave no token: an answer of unknown is asked again), the
    record's writer takes its caller's signal test (the tail's look, the
    supervisor's latch of a forwarded signal) and starts NO `ps` once that
    is true: the record is written all the same, with
    `wrapper_start=unknown`. A `ps` that was killed is waited for one
    second at most, and the ancestor chain has one 20 s bound for all of
    its `ps` runs. What stays outside any bound this wrapper can give:
    the kernel's own calls on the leg's regular files and its start of
    `ps`; and the role's token is read once, at the launch, by the
    helper's reader.
    Round 45 closed the rule over the tail's LOOPS (PR-LOW-016): the
    forwarding of the two files to the mirrors looks before every 64 KiB
    chunk and moves one batch (a queue's worth) per stream and call, so a
    signal caught while a backlog goes out to a consumer that keeps pace
    is answered before the next read, and a stdout that keeps growing
    cannot hold stderr, the read of `<leg>.exit` or the supervisor's
    probes; a batch that ended on its count is followed at once, without
    the poll's sleep, so nothing is forwarded more slowly. Every wait and
    every loop of the tail now either looks on every turn or has a fixed
    bound — a count or a wall-time limit; the one wait that is neither,
    the start of the two mirror threads, is taken before the split's mask
    is lifted, while every signal is still held.
    Before any of this every descriptor above 2 the process inherited is
    closed, and `LOOP_SEAT` is removed from the role's environment (D12: a
    takeover's seat never crosses a role boundary).

Usage: python3 -I scripts/loop-spawn-wrapper.py   (through the shim:
       bash scripts/loop-spawn-wrapper.sh) — no argument; every parameter is
       a LOOP_* environment variable (the shim's header lists them).
"""

import datetime
import errno
import importlib.util
import json
import os
import queue
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time

ROLE_LOG_ROTATE_BYTES = 52428800
PUMP_BOUND_S = 5.0            # the bounded wait on the pump after the child exits (v44.0's watchdog)
LOCK_FAR_OFFSET = 0x7FFFFFFE  # D32: the ONE locked byte on Windows — appends never reach it
IDENTITY_REPLACE_TRIES = 5    # a held-open identity file on Windows: 5 x 200 ms, then the warning
HELPER_NAME = "loop-journal.py"
RUNTIME_NAMES = ("route_collect", "route_dir_word", "route_skipped_text", "group_launch",
                 "group_members", "group_stop", "group_close", "exit_census", "canon_path", "path_inside",
                 "ROUTE_WORDS", "ROUTE_VERDICT_WORDS", "proc_start_token")
# v48.0 D16 — the split wrapper. The two codes are the TAIL's own: the role's
# code, 2 / 3 / 4 and 129 / 130 / 143 keep their meaning, and each of these
# two is told apart from a role that happened to exit 5 or 6 by the stdout
# line printed beside it.
TAIL_DETACHED_CODE = 5        # a TERM / HUP / INT ended the tail alone: `SPAWN_DETACHED supervisor_pid=<n>`
TAIL_LOST_CODE = 6            # the supervisor is gone and wrote no `<leg>.exit`: `SPAWN_LOST supervisor_pid=<n> …`
TAIL_RECORD_BOUND_S = 30.0    # how long the tail waits for the supervisor to record itself in `<leg>.live`
TAIL_POLL_FAST_S = 0.02       # the tail's poll for the first two seconds (a refusal relays at once)
TAIL_POLL_S = 0.1             # … and after them
# round 41 PR-MED-025: the fork handshake. The first child leaves by exit 0 once
# its fork returned, or by THIS code when its setsid / fork raised — the one
# status that proves no supervisor exists. Any other status proves nothing.
SPLIT_FORK_FAILED = 71
SPLIT_ORPHAN_BOUND_S = 10.0   # how long the supervisor waits to stop being the first child's child; past it, it starts nothing
SPLIT_REAP_BOUND_S = 10.0     # how long the tail waits for the first child's status before treating it as unknown
# round 41 PR-MED-027: the tail's two mirrors (its own stdout / stderr). Each is
# written by its own thread behind a bounded queue, so a consumer that stops
# reading can never hold the tail: at most this much is held per mirror, and the
# final drain gives up once a mirror has accepted nothing for the stall bound.
MIRROR_QUEUE_CHUNKS = 16      # x 64 KiB
MIRROR_STALL_S = 5.0
# round 42 PR-MED-029: the tail's CLOSING line (`SPAWN_DETACHED` / `SPAWN_LOST`) has
# bounds of its own, in wall time — never renewed by a mirror's progress: a grace
# for what is already queued, then the queue is dropped (those bytes stay in the
# per-leg file) and the line alone is given this long.
MIRROR_GRACE_S = 0.5
MIRROR_CLOSE_S = 2.0
# round 45 PR-LOW-016: how many 64 KiB chunks one relay() call forwards per stream
# before it returns to its caller's look and other checks (one full queue's worth)
RELAY_BATCH_CHUNKS = MIRROR_QUEUE_CHUNKS
# round 42 PR-MED-028: how far up the supervisor reads its own ancestors, and the
# largest pid a C `int` holds (a number above it names no process)
ANCESTOR_STEPS = 64
PID_MAX = 2147483647
# round 43 PR-LOW-014: where a process's stat line is read (one name, so the `ps`
# path can be exercised on a host that has a procfs), and how a `ps` is run — for
# at most PS_BOUND_S, and, when the caller gives a stop test (the tail's two
# probes), in slices of PS_SLICE_S with the test read after each
PROC_STAT = "/proc/%d/stat"
PS_BOUND_S = 20.0
PS_SLICE_S = 0.05
PS_REAP_S = 1.0               # round 44: how long a killed `ps` is waited for before it is left to the host
LEG_NAME_RE = re.compile(r"\A[A-Za-z0-9._-]+\Z")   # ≡ the helper's LEG_RE: what may name a file in the log root
LEG_STEM_TRIES = 99           # `<leg>`, then `<leg>.2` … `<leg>.99` when the name is taken
LEG_LIVE, LEG_EXIT, LEG_OUT, LEG_ERR = ".live", ".exit", ".out", ".err"   # the four per-leg files beside the probe log
END_READ_BYTES = 4194304      # D23: how much of the leg's own role-log bytes the end's handoff read takes (the last 4 MiB)
TOKEN_POOL_RE = re.compile(r"\ACLAUDE_CODE_OAUTH_TOKEN_[1-9][0-9]*\Z")
SESSION_RE = re.compile(rb'"session_id":"([^"]*)"')
# v47.0 D10: a resumed session's id — also what makes it safe as one path component
RESUME_UUID_RE = re.compile(r"\A[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z")
PIN_LABELS = {"profile": "LOOP_PROFILE_DIR", "answer": "the router's answer",
              "ambient": "the ambient folder — CLAUDE_CONFIG_DIR, else ~/.claude"}
FOOTER_SEP = "----- /execute-loop spawn-wrapper footer (S-D; wrapper-rendered exit contract — values validated at spawn) -----"

# The boot twin's host switch — `os.name == "nt"` like the helper's
# HOST["is_windows"]; the selftest flips it on the imported module to drive
# the Windows spelling legs on Linux.
_BOOT_WINDOWS = os.name == "nt"

# How a helper-emitted record reaches the probe log (round 39 HIGH-001). POSIX:
# O_APPEND belongs to the open file description, so a helper child that INHERITS
# the retained descriptor appends atomically (v44.0's `>&8`). Windows: O_APPEND
# is emulated by the C runtime of the process that OPENED the file — an
# inherited handle writes at its shared, stale file pointer and overwrites what
# another process appended since (measured on Windows 11 / Python 3.13: the
# role's exit declaration replaced by the post-wait records) — so there the
# record is CAPTURED and written by this process through the same descriptor.
# The selftest flips this on the imported module to drive the capture leg on Linux.
_INHERIT_APPEND = os.name != "nt"
# Every retained append descriptor is BINARY (round 39 MED-001): without
# O_BINARY a Windows descriptor is in text mode and os.write turns each LF into
# CRLF — the role log would no longer be the child's bytes, the wrapper-native
# records and the lock's holder line would carry a CR. 0 on POSIX (no such flag).
_O_BINARY = getattr(os, "O_BINARY", 0)


# --- the exceptions that carry an exit --------------------------------------

class _Refuse(Exception):
    """A refusal: `SPAWN_REFUSED check=<check> detail="<detail>"` on stderr, exit 2."""
    def __init__(self, check, detail):
        Exception.__init__(self, detail)
        self.check = check
        self.detail = detail


class _LockHeld(Exception):
    """The spawn lock is held: exit 3, no probe-log write."""


class _Signalled(Exception):
    """A forwarded TERM / INT / HUP: exit 143 / 130 / 129 with the footer."""
    def __init__(self, code):
        Exception.__init__(self, code)
        self.code = code


def fail_usage(detail):
    raise _Refuse("params", detail)


# --- output -----------------------------------------------------------------

def _configure_std_streams():
    """UTF-8 + LF on this entrypoint's text streams (T1.4's form, guarded)."""
    for name in ("stdout", "stderr"):
        s = getattr(sys, name, None)
        if s is None or not hasattr(s, "reconfigure"):
            continue
        try:
            s.reconfigure(encoding="utf-8", newline="\n")
        except Exception:
            pass


def _write_fd(fd, text):
    """One line on a standard descriptor, as UTF-8 bytes (surrogateescape for
    undecodable path bytes), best effort — a dead mirror never ends the spawn."""
    data = (text + "\n").encode("utf-8", "surrogateescape")
    try:
        view = memoryview(data)
        while len(view):
            view = view[os.write(fd, view):]
    except OSError:
        pass


def say(line):
    """The wrapper's OWN stdout (the composer's channel): raw bytes on fd 1 —
    the same descriptor the pump mirrors to, written whole per line."""
    _write_fd(1, line)


def err(line):
    _write_fd(2, line)


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


# --- the boot twin of the lexical path policy (D30 / D31) -------------------

def _boot_spell(v):
    """≡ canon_path(v, resolve=False): the SPELLING form — identity on POSIX;
    on a Windows host `\\` → `/`, a UNC spelling refused by name, the MSYS
    `/c/…` → `C:/` conversion under MSYSTEM (no subprocess — D31), any other
    `/`-rooted spelling refused by name, the drive letter upper-cased. No
    normpath: every component the composer typed survives to the file tests
    and to realpath (PR-MED-001 round 10)."""
    if not _BOOT_WINDOWS:
        return v
    s = v.replace("\\", "/")
    if s.startswith("//"):
        fail_usage("path %s is a UNC spelling — the loop's canonical spelling is a drive path (`C:/...`); a UNC share is refused by name (path-rule)" % v[:120])
    m = re.match(r"\A/([A-Za-z])(/|\Z)", s)
    if m and os.environ.get("MSYSTEM"):
        s = m.group(1).upper() + ":/" + s[len(m.group(0)):]
    elif s.startswith("/"):
        fail_usage("path %s is a `/`-rooted spelling on a Windows-native host — spell it as a drive path (`C:/...`)%s"
                   % (v[:120], "" if os.environ.get("MSYSTEM") else " (the MSYS `/c/...` form converts under MSYSTEM only)"))
    if len(s) >= 2 and s[1] == ":" and s[0].isalpha():
        s = s[0].upper() + s[1:]
    return s


def _boot_inside(path, root):
    """≡ path_inside: THE containment predicate over canonical values — `/`
    the separator on every host (never os.sep); equality inside; a root
    already ending in `/` (POSIX `/`, a drive root `C:/`) used as is."""
    if path == root:
        return True
    prefix = root if root.endswith("/") else root + "/"
    return path.startswith(prefix)


def _boot_real(p):
    """The route block's physical resolution (v44.0's route_real): the
    resolved path in the canonical spelling, or None when it does not resolve
    or carries a control byte (byte-exact; fail closed — PR-MED-023)."""
    try:
        r = os.path.realpath(_boot_spell(p))
    except (OSError, ValueError):
        return None
    if not r:
        return None
    if _BOOT_WINDOWS:
        r = r.replace("\\", "/")
        if len(r) >= 2 and r[1] == ":" and r[0].isalpha():
            r = r[0].upper() + r[1:]
    if _has_control(r):
        return None
    return r


def _has_control(v):
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in v)


def _is_graph_token(v):
    """`[[:graph:]]` only — no whitespace, no control byte (require_token)."""
    return not any(ch.isspace() or not ch.isprintable() for ch in v)


def _record_safe(text):
    """A free text made safe for a record's quoted value (the helper's value
    rule: no control byte, no double quote, no non-space Unicode whitespace —
    each becomes a space; runs collapsed). round 29 PR-MED-004."""
    chars = [(" " if (ord(ch) < 32 or ord(ch) == 127 or ch == '"' or (ch != " " and ch.isspace())) else ch) for ch in text]
    return " ".join("".join(chars).split())


# --- v48.0 D16: the boot twin of the runtime's start token, and the tail ------

def _ps_read(column, pid, stop=None, bound=None):
    """`LC_ALL=C ps -o <column>= -p <pid>` — `(returncode, stdout, stderr)`, or
    None when it could not be run, did not end inside its bound, or (round 43
    PR-LOW-014) `stop()` turned true while it ran. With no `stop` it is one
    wait of the bound, as before; with one — a caller's signal test — the
    wait is taken in slices of PS_SLICE_S and the test is read after each,
    so a signal caught while a `ps` runs is not held for as long as that
    `ps` takes. Either way a `ps` that is not waited for to its end is
    killed and reaped here. Round 44 PR-LOW-015: NO `ps` is started when the
    test is already true, or when no time is left; `bound` (seconds; None =
    PS_BOUND_S) lets a caller that makes several runs give them one bound
    between them; and the reap of a killed `ps` is itself bounded
    (PS_REAP_S) — one the kernel does not let die is left to the host."""
    if (stop is not None and stop()) or (bound is not None and bound <= 0):
        return None
    try:
        proc = subprocess.Popen(["ps", "-o", column + "=", "-p", str(pid)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, env=dict(os.environ, LC_ALL="C"))
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    end = time.monotonic() + (PS_BOUND_S if bound is None else bound)
    try:
        while True:
            left = end - time.monotonic()
            try:
                out, errs = proc.communicate(timeout=max(0.0, left if stop is None else min(left, PS_SLICE_S)))
                return proc.returncode, out or "", errs or ""
            except subprocess.TimeoutExpired:
                if left <= 0 or (stop is not None and stop()):
                    return None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    finally:
        if proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass
        for pipe in (proc.stdout, proc.stderr):
            try:
                if pipe is not None:
                    pipe.close()
            except OSError:
                pass
        try:
            proc.wait(timeout=PS_REAP_S)
        except (OSError, subprocess.SubprocessError):
            pass


def _boot_start_token(pid, stop=None):
    """≡ the runtime's proc_start_token(pid) — `(state, token)`, the state one
    of "alive" / "gone" / "unknown": field 22 of /proc/<pid>/stat parsed after
    the last `)` on Linux; `LC_ALL=C ps -o lstart= -p <pid>` on any other
    POSIX host; unknown on a Windows host. A boot twin because both of its
    users run before, or without, the runtime import: the wrapper's own token
    in `<leg>.live`, written at start, and the tail's test that the
    supervisor has gone (the tail never imports the helper — it would need a
    verified snapshot of its own). Pinned to the runtime's function by the
    wrapper selftest on live and dead pids; the token is opaque and only ever
    compared for equality. `stop` (round 43; the tail's signal test, else
    None) ends a `ps` run early — the answer is then "unknown"."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 or os.name == "nt":
        return "unknown", None
    stat_path = PROC_STAT
    try:
        with open(stat_path % pid, "rb") as fh:
            data = fh.read(4096)
    except (FileNotFoundError, ProcessLookupError):
        if os.path.exists(stat_path % os.getpid()):
            return "gone", None
        data = None
    except OSError:
        return "unknown", None
    if data is not None:
        fields = data.rpartition(b")")[2].split()
        if len(fields) > 19 and fields[19].isdigit():
            return "alive", fields[19].decode("ascii")
        return "unknown", None
    r = _ps_read("lstart", pid, stop)
    if r is None:
        return "unknown", None
    returncode, out, errs = r
    token = " ".join(out.split())
    if returncode == 0 and token:
        return "alive", token
    if returncode == 1 and not token and not errs.strip():
        return "gone", None
    return "unknown", None


def _boot_terminated(pid, stop=None):
    """round 41 PR-MED-026 — has process `pid` TERMINATED without being reaped
    (a zombie)? The TAIL's question alone, asked beside the start token: a
    zombie still has its pid, its group and its start token — so the token
    twin above, like the runtime's proc_start_token and group_any, reads it
    alive, and that stays their contract (a zombie leader still reserves its
    group's number) — but it can write no further record, so a tail that
    waited on the token would wait for as long as nobody reaps it. True when
    the process's state is Z (or X, dead) — the first field after the last
    `)` of /proc/<pid>/stat on Linux, `ps -o stat= -p <pid>` on any other
    POSIX host; False for a running process, a pid that is gone (the token's
    answer) and whenever the state cannot be read — a `ps` run that `stop`
    (round 43; the tail's signal test, else None) ended early included."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 or os.name == "nt":
        return False
    stat_path = PROC_STAT
    try:
        with open(stat_path % pid, "rb") as fh:
            fields = fh.read(4096).rpartition(b")")[2].split()
        return fields[:1] in ([b"Z"], [b"X"], [b"x"])
    except (FileNotFoundError, ProcessLookupError):
        if os.path.exists(stat_path % os.getpid()):
            return False
    except OSError:
        return False
    r = _ps_read("stat", pid, stop)
    return r is not None and r[0] == 0 and r[1].strip()[:1] in ("Z", "X")


def _pid_of(text):
    """A pid written as text — ASCII decimal digits, 1 … PID_MAX — as an int,
    else None. `str.isdigit` alone admits digits `int` refuses (a superscript
    two) and lengths no pid has; a leg file or an environment value that is
    not a pid is never a crash and never a number (round 42 PR-LOW-013's
    class, on the wrapper's own reads)."""
    if not text or len(text) > 10 or not (text.isascii() and text.isdigit()):
        return None
    n = int(text)
    return n if 0 < n <= PID_MAX else None


def _boot_ancestors(pid):
    """round 42 PR-MED-028 — the ancestors of process `pid`, nearest first
    (its parent, that one's parent, … down to pid 1), or None when the chain
    cannot be read to its end inside ANCESTOR_STEPS. The parent pid is field 4
    of /proc/<pid>/stat on Linux (the second field after the last `)`), `ps -o
    ppid= -p <pid>` on any other POSIX host. Read twice by the split: by the
    launching process for its own chain, and by the supervisor once it has
    been re-parented. Round 44: where the parent is a `ps` run, the WHOLE
    chain has one bound, PS_BOUND_S — not one per step — and a chain not
    read inside it is None, like any chain that could not be read (the
    supervisor reads its own with every signal held, before it has
    recorded itself)."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 or os.name == "nt":
        return None
    chain, stat_path = [], PROC_STAT
    procfs = os.path.exists(stat_path % os.getpid())
    end = time.monotonic() + PS_BOUND_S
    for _step in range(ANCESTOR_STEPS):
        if pid <= 1:
            return chain
        parent = None
        if procfs:
            try:
                with open(stat_path % pid, "rb") as fh:
                    fields = fh.read(4096).rpartition(b")")[2].split()
                if len(fields) > 1:
                    parent = 0 if fields[1] == b"0" else _pid_of(fields[1].decode("ascii", "replace"))
            except OSError:
                return None
        else:
            r = _ps_read("ppid", pid, bound=end - time.monotonic())
            if r is None:
                return None
            text = r[1].strip()
            parent = 0 if text == "0" else _pid_of(text) if r[0] == 0 else None
        if parent is None:
            return None
        if parent == 0:
            return chain                # a process with no parent in this namespace: the chain's end
        chain.append(parent)
        pid = parent
    return None


class _MirrorLine(bytes):
    """The tail's own closing line on a mirror's queue: written at a line start."""


class _Mirror(object):
    """round 41 PR-MED-027 — ONE of the tail's two mirrors (its own stdout or
    stderr). Every write to the descriptor is made by this object's daemon
    thread, from a bounded queue; the tail itself never writes to a mirror,
    so a consumer that keeps the pipe open and stops reading can block this
    thread and nothing else — the tail still reads `<leg>.exit`, still acts
    on a TERM, and exits with the thread parked (a daemon thread does not
    hold the interpreter). `written` counts the bytes the descriptor took:
    the drain's measure of progress. A descriptor that REFUSES a write (a
    closed pipe) is `closed` from then on and takes nothing more, as before.
    What a mirror did not take is in the per-leg file, the durable copy.
    Round 42 PR-MED-029: `close_with` is how the tail's own closing line
    goes out — whatever is queued and not yet written is dropped first, so
    the line is never kept waiting behind output the consumer has not
    taken, and it is written at a line start."""
    def __init__(self, fd):
        self.fd = fd
        self.queue = queue.Queue(MIRROR_QUEUE_CHUNKS)
        self.closed = False
        self.written = 0
        self.last = b"\n"           # the last byte written: a closing line starts a line of its own
        thread = threading.Thread(target=self._run, name="loop-tail-mirror-%d" % fd)
        thread.daemon = True
        try:
            thread.start()
        except RuntimeError:
            self.closed = True      # no thread: no mirror; the per-leg file still holds everything

    def _run(self):
        while True:
            chunk = self.queue.get()
            if not self.closed:
                if isinstance(chunk, _MirrorLine) and self.last != b"\n":
                    chunk = b"\n" + chunk
                try:
                    view = memoryview(chunk)
                    while len(view):
                        n = os.write(self.fd, view)
                        if n:
                            self.last = bytes(view[n - 1:n])
                        view = view[n:]
                        self.written += n
                except OSError:
                    self.closed = True
            self.queue.task_done()

    def close_with(self, line):
        """Drop every chunk that is queued and not yet being written — it stays
        in the per-leg file — and queue `line` (bytes, newline included) as the
        mirror's last item. Never a wait. Called a second time only for the
        tail's detach line after a loss line a signal overtook (round 43): a
        loss line still unwritten is then dropped like any queued chunk."""
        while True:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
            self.queue.task_done()
        self.offer(_MirrorLine(line))

    def offer(self, chunk):
        """Queue `chunk` if there is room: True when it was taken (or the
        mirror is closed and takes nothing), False when the queue is full —
        never a wait."""
        if self.closed:
            return True
        try:
            self.queue.put_nowait(chunk)
        except queue.Full:
            return False
        return True

    def idle(self):
        return self.closed or self.queue.unfinished_tasks == 0


def _read_leg_file(path):
    """A per-leg file's key=value lines (first wins), or {} when it is absent
    or unreadable. The tail's one read of `<leg>.live` / `<leg>.exit`."""
    try:
        with open(path, "rb") as fh:
            data = fh.read(65536)
    except OSError:
        return {}
    kv = {}
    for line in data.decode("utf-8", "replace").split("\n"):
        key, sep, value = line.partition("=")
        if sep and key and key not in kv:
            kv[key] = value
    return kv


def _close_inherited_fds():
    """D12 / D16: every descriptor above 2 this process inherited is closed
    before the wrapper opens one of its own — so nothing a caller held open
    (a takeover's seat lock, a pipe of the host) rides into the supervisor or
    the role. POSIX only: a Windows child inherits no descriptor beside its
    three standard handles. The open descriptors are listed where the host
    has a listing (/proc/self/fd, /dev/fd); otherwise the range up to the
    soft limit (capped) is closed."""
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


def _native_folder(value, cwd):
    """v47.0 D10 (round 16 PR-MED-022): the folder a NATIVE child started in
    `cwd` resolves the spelling `value` to — text only, nothing is read — or
    "" when that cannot be established from here. This is how the role's own
    process will read a folder name it is handed UNCHANGED, so it never
    applies the MSYS `/c/…` conversion (`_boot_spell` does that for a value
    the wrapper then exports in the converted spelling; a native process gets
    no such conversion of what it inherits). POSIX: an absolute path as it is,
    a relative one under `cwd`. A Windows host: `\\` → `/`; a UNC path and a
    drive-absolute path as they are (the drive letter upper-cased); a
    `/`-rooted path on `cwd`'s drive; a drive-relative `X:name` under `cwd`
    when X is `cwd`'s drive, and "" on any other drive (that drive's own
    working directory belongs to the role's process and is not known here);
    a plain relative path under `cwd`."""
    base = cwd if cwd.endswith("/") else cwd + "/"
    if not _BOOT_WINDOWS:
        return value if value.startswith("/") else base + value
    s = value.replace("\\", "/")
    if s.startswith("//"):
        return s
    cwd_drive = cwd[:2].upper() if re.match(r"\A[A-Za-z]:", cwd) else ""
    m = re.match(r"\A([A-Za-z]):(.*)\Z", s, re.S)
    if m:
        drive, rest = m.group(1).upper() + ":", m.group(2)
        if rest.startswith("/"):
            return drive + rest
        if not cwd_drive or drive != cwd_drive:
            return ""
        return base + rest if rest else cwd
    if s.startswith("/"):
        return cwd_drive + s if cwd_drive else ""
    return base + s


def _os_error_word(exc):
    return errno.errorcode.get(exc.errno, "error") if exc.errno else "error"


def _pin_probe(folder, session):
    """v47.0 D10: how ONE candidate profile folder reads for a resumed
    session — `(word, mtime_ns, why)`:
      ("holds", <ns>, "")        some `projects/<any>/<session>.jsonl` is a regular
                                 file whose modification time was read (the newest
                                 of them)
      ("absent", None, "")       the folder or its `projects/` does not exist, or
                                 every entry of `projects/` was looked in and none
                                 has the file
      ("indeterminate", None, <why>)  something on the way could not be read
    Missing evidence is never negative evidence: only a not-found answer (the
    path, or a non-directory on the way to it) reads as absent; every other
    error — and a name that is there but is no regular file, or resolves to
    nothing — is indeterminate. A LINK that resolves to nothing is such a
    name at every level (Step HA1, round 26 LOW-012): the transcript, a
    project entry, `projects/`, or the folder itself — a profile folder
    linked to a volume that is not mounted may hold the newest copy, and is
    never passed over for an older one elsewhere. `session` is a validated
    UUID (one path component). Reads only; nothing is opened."""
    try:
        os.stat(folder)
    except (FileNotFoundError, NotADirectoryError):
        if os.path.islink(folder):
            return "indeterminate", None, "the folder resolves to nothing (a broken link)"
        return "absent", None, ""
    except OSError as e:
        return "indeterminate", None, "the folder could not be read (%s)" % _os_error_word(e)
    projects = os.path.join(folder, "projects")
    try:
        names = os.listdir(projects)
    except (FileNotFoundError, NotADirectoryError):
        if os.path.islink(projects):
            return "indeterminate", None, "its projects/ resolves to nothing (a broken link)"
        return "absent", None, ""
    except OSError as e:
        return "indeterminate", None, "its projects/ could not be listed (%s)" % _os_error_word(e)
    newest = None
    for name in names:
        path = os.path.join(projects, name, session + ".jsonl")
        try:
            st = os.stat(path)
        except (FileNotFoundError, NotADirectoryError):
            if os.path.lexists(path):
                return "indeterminate", None, "the transcript under projects/%s resolves to nothing (a broken link)" % _record_safe(name)[:80]
            entry = os.path.join(projects, name)
            if os.path.islink(entry) and not os.path.exists(entry):
                return "indeterminate", None, "projects/%s resolves to nothing (a broken link)" % _record_safe(name)[:80]
            continue
        except OSError as e:
            return "indeterminate", None, "the transcript under projects/%s could not be read (%s)" % (_record_safe(name)[:80], _os_error_word(e))
        if not stat.S_ISREG(st.st_mode):
            return "indeterminate", None, "the transcript under projects/%s is not a regular file" % _record_safe(name)[:80]
        if newest is None or st.st_mtime_ns > newest:
            newest = st.st_mtime_ns
    if newest is None:
        return "absent", None, ""
    return "holds", newest, ""


def _acct_dir_matches(profile_dir, acct_n):
    """v32 TD.2's deterministic mapping, judged on the SPELLED profile dir:
    `…/.claude-acct<N>` for pool <N> — so a Windows `C:\\Users\\x\\.claude-acct2`
    matches pool 2 exactly as `/home/x/.claude-acct2` does (the spelling form
    turns `\\` into `/` on a Windows host; identity on POSIX). At most ONE
    trailing `/` is removed — v44.0's `${LOOP_PROFILE_DIR%/}` — so `…acct2//`
    refuses as it always did (round 34 PR-LOW-002)."""
    spelled = _boot_spell(profile_dir)
    if spelled.endswith("/"):
        spelled = spelled[:-1]
    return spelled.endswith("/.claude-acct" + acct_n)


def _boot_dir_word(folder, roots):
    """The answer rule's FOLDER checks for the PRE-IMPORT consumer (router-mode
    refusal 6 on LOOP_PROFILE_DIR, which precedes the helper gate): the same
    (word, check) results as the runtime's route_dir_word, computed with the
    boot twin (realpath + _boot_inside). Pinned equal by the selftest."""
    if not folder.startswith("/"):
        return "bad-dir", "relative"
    if '"' in folder:
        return "bad-dir", "quote"
    if _has_control(folder):
        return "bad-dir", "control-byte"
    if not os.path.isdir(folder):
        return "no-dir", "no-dir"
    try:
        st = os.stat(folder)
    except OSError:
        return "bad-dir", "unresolvable"
    if not _BOOT_WINDOWS:
        if st.st_uid != os.getuid():
            return "bad-dir", "not-owned"
        if st.st_mode & 0o020:
            return "bad-dir", "group-writable"
        if st.st_mode & 0o002:
            return "bad-dir", "world-writable"
    resolved = _boot_real(folder)
    if not resolved:
        return "bad-dir", "unresolvable"
    if any(_boot_inside(resolved, root) for root in roots):
        return "bad-dir", "inside-root"
    return "", ""


# --- the role-log pump (D18; the v33.4 wake-noise filter, in-process) ---------
# ROLE LOG   every chunk, byte-verbatim, the moment it is read. A write failure
#            is STICKY: stop writing that sink, keep draining and mirroring to
#            EOF (the child is never stranded behind a full pipe), exit 3.
# MIRROR     assembled per complete line (remainder bounded at 1 MiB — past it
#            the line passes through verbatim, unclassified). A line that starts
#            with the rate_limit_event prefix AND parses as that event with
#            status allowed|allowed_warning becomes ONE `USAGE_TICK status=
#            window= util=` line with whitelisted values only; every other line
#            is verbatim. Fails OPEN per line: a classification error emits that
#            line raw, a dead mirror (EPIPE — or any other fd 1 write error) is
#            swapped for /dev/null with assembly state and the count untouched, a
#            last-resort assembly error degrades to raw chunk passthrough.
# COUNT      ST.count — the rewrite count, read by the wrapper at CLEAN EOF only.
PUMP_PREFIX = b'{"type":"rate_limit_event"'
PUMP_LIMIT = 1048576
PUMP_WINDOW_RE = re.compile(r"[a-z_]{1,40}")


class PumpState(object):
    def __init__(self):
        self.remainder = b""
        self.passthrough = False
        self.count = 0
        self.sink_failed = False
        self.mirror_broken = False


ST = PumpState()
PUMP_ROLE_FD = [None]   # the role-log descriptor the pump writes (set by pump_run)


def pump_reset(role_fd):
    global ST
    ST = PumpState()
    PUMP_ROLE_FD[0] = role_fd


def read_chunk(fd):
    return os.read(fd, 65536)


def write_all(fd, buf):
    view = memoryview(buf)
    while len(view):
        view = view[os.write(fd, view):]


def emit(buf):
    # The ONE owner of fd 1 inside the pump. Never raises, never replays.
    try:
        write_all(1, buf)
    except OSError:
        # EPIPE-BRANCH-MARKER: a dead mirror (EPIPE, or any fd 1 write error) is
        # swapped for /dev/null; ST (assembly state + the count) stays untouched.
        try:
            nul = os.open(os.devnull, os.O_WRONLY)
            os.dup2(nul, 1)
            os.close(nul)
        except OSError:
            pass


def render_util(info, raw_window):
    util = info.get("utilization")
    if isinstance(util, bool) or not isinstance(util, (int, float)):
        util = None
        windows = info.get("unifiedWindows")
        if isinstance(windows, dict) and isinstance(raw_window, str):
            entry = windows.get(raw_window)
            if isinstance(entry, dict):
                util = entry.get("utilization")
    if isinstance(util, bool) or not isinstance(util, (int, float)):
        return "-"
    try:
        value = float(util)
    except (OverflowError, ValueError):
        return "-"
    if value != value or abs(value) > 1000000.0:
        return "-"
    text = ("%.3f" % value).rstrip("0").rstrip(".")
    return text or "0"


def classify(line):
    # One COMPLETE line in, the mirror bytes for it out. Any exception here is
    # caught by the caller, which falls back to the raw line BEFORE any output.
    if len(line) > PUMP_LIMIT or not line.startswith(PUMP_PREFIX):
        return line
    obj = json.loads(line.decode("utf-8"))
    if not isinstance(obj, dict) or obj.get("type") != "rate_limit_event":
        return line
    info = obj.get("rate_limit_info")
    if not isinstance(info, dict):
        return line
    status = info.get("status")
    if not isinstance(status, str) or status not in ("allowed", "allowed_warning"):
        return line
    raw_window = info.get("rateLimitType")
    window = "-"
    if (isinstance(raw_window, str) and PUMP_WINDOW_RE.fullmatch(raw_window)
            and "rate_limit" not in raw_window):
        window = raw_window
    out = "USAGE_TICK status=%s window=%s util=%s\n" % (
        status, window, render_util(info, raw_window))
    out = out.encode("ascii")
    ST.count += 1
    return out


def assemble(chunk):
    if ST.passthrough:
        cut = chunk.find(b"\n")
        if cut < 0:
            emit(chunk)
            return
        emit(chunk[:cut + 1])
        ST.passthrough = False
        chunk = chunk[cut + 1:]
        if not chunk:
            return
    head, sep, tail = (ST.remainder + chunk).rpartition(b"\n")
    oversized = b""
    if len(tail) > PUMP_LIMIT:
        oversized = tail
        ST.remainder = b""
        ST.passthrough = True
    else:
        ST.remainder = tail
    if sep:
        for line in head.split(b"\n"):
            line += b"\n"
            try:
                out = classify(line)
            except BaseException:
                out = line
            emit(out)
    if oversized:
        emit(oversized)


def mirror(chunk):
    if not ST.mirror_broken:
        try:
            assemble(chunk)
        except BaseException:
            # last resort: which bytes of this chunk were committed is
            # unknowable here, so nothing more is emitted for it (no replay);
            # every later chunk goes out raw, unassembled and uncounted.
            ST.mirror_broken = True
        return
    try:
        emit(chunk)
    except BaseException:
        pass


def pump_run(in_fd, role_fd):
    """Drain `in_fd` (the pipe's read end) to EOF: 0 clean; 3 a failed role-log
    sink (at EOF) or an unreadable input (at once). ST.count is the rewrite
    count, valid on 0 only."""
    pump_reset(role_fd)
    while True:
        try:
            chunk = read_chunk(in_fd)
        except OSError:
            return 3
        if not chunk:
            break
        if not ST.sink_failed:
            try:
                write_all(role_fd, chunk)
            except OSError as exc:
                ST.sink_failed = True
                try:
                    os.write(2, ("PUMP_WARN role-log write failed errno=%d\n"
                                 % (exc.errno or 0)).encode("ascii"))
                except OSError:
                    pass
        mirror(chunk)
    if ST.remainder and not ST.mirror_broken:
        try:
            emit(ST.remainder)
        except BaseException:
            pass
    if ST.sink_failed:
        return 3
    return 0


class Pump(object):
    """The wrapper-private pump thread over one pipe."""
    def __init__(self, role_fd):
        self.read_fd, self.write_fd = os.pipe()
        self.role_fd = role_fd
        self.status = [None]
        self.thread = threading.Thread(target=self._run, name="loop-role-log-pump")
        self.thread.daemon = True

    def _run(self):
        try:
            self.status[0] = pump_run(self.read_fd, self.role_fd)
        except BaseException:
            self.status[0] = 3
        finally:
            # round 29 PR-MED-003: the reader's OWN termination releases the pipe's
            # read end — a stopped drain (a read error, an unexpected exception)
            # must never keep a producer blocked on a full pipe while the main
            # thread waits on it; the producer gets EPIPE instead. Closed ONLY
            # here: a reader still blocked in read (the orphan-holder timeout)
            # keeps its descriptor — never a close under a blocked read.
            try:
                os.close(self.read_fd)
            except OSError:
                pass

    def start(self):
        self.thread.start()

    def close_writer(self):
        if self.write_fd is not None:
            try:
                os.close(self.write_fd)
            except OSError:
                pass
            self.write_fd = None

    def wait(self, bound):
        """The pump's status after it drained, or "timeout" past the bound."""
        self.thread.join(bound)
        if self.thread.is_alive():
            return "timeout"
        return self.status[0] if self.status[0] is not None else 3


# --- the wrapper --------------------------------------------------------------

class Wrapper(object):
    def __init__(self):
        self.env = os.environ
        self.tmpd = None
        self.snapd = None             # the snapshot workspace under this repo's git directory (round 43 PR-MED-001)
        self.lock_fd = None
        self.role_fd = None
        self.role_log_start = None    # v46.4 D1: the role log's size once it is open for THIS leg
        self.probe_fd = None
        self.helper = None            # the SNAPSHOT path once taken
        self.rt = None                # the runtime module
        self.started = False          # the START record is on the probe log
        self.pre_created = False
        self.post_ran = False
        self.prestate = None
        self.group = None             # the child's group handle
        self.pump = None
        self.interruptible = False
        self.pending_code = None
        self.cancel = []              # the collector's cancellation list
        self.token_env_name = ""
        self.route_enabled = False
        self.route_dir = ""
        self.route_via = ""
        self.route_roots = []         # literal (spelled) roots: LOOP_CWD + LOOP_ADD_DIRS
        self.rootargs = []
        self.escargs = []
        self.pass_kv = []
        self.start_flags = []
        self.add_dirs = []
        self.prompt_bytes = None
        self.eff_profile_dir = ""
        self.profile_dir = ""         # LOOP_PROFILE_DIR in the canonical spelling ("" when unset)
        self.ambient_dir = ""         # v47.0 D10: the folder a role with NO selection runs on (read before any export; "" = not establishable)
        self.ambient_raw = ""         # the inherited CLAUDE_CONFIG_DIR (else ~/.claude) as the role inherits it
        self.identity_dir = ""        # v47.0 D10: the folder the role runs on — the identity record's profile_dir=
        self.resume = ""              # LOOP_RESUME_SESSION ("" on a fresh spawn)
        self.pin = None               # v47.0 D10: the resolved resume pin — {"kind", "holder", "stale"}
        self.perms = "scoped"         # LOOP_PERMS normalised (unset or empty → scoped)
        self.child_pid = None
        self.leg_base = None          # v48.0 D16: `<log root>/<stem>` once `<stem>.live` is claimed (None: no per-leg files)
        self.survive = "off"          # v48.0 D16: `<leg>.live`'s survive= — off | on | unverified | in-tree (round 42 PR-MED-028)
        self.launch_chain = None      # round 42 PR-MED-028: the launching process's ancestors, read before the split
        self.role_token = None        # v48.0 D16: the role's start token, read once at the launch
        self.own_token = None         # round 44 PR-LOW-015: (pid, this process's own start token) — kept once read, used only by that pid
        self.role_started = False     # v48.0 D23: THIS wrapper wrote the leg's ROLE: start
        self.role_start_time = None   # … and when (the end's duration=)
        self.launched = "no"          # v48.0 D16: `<leg>.exit`'s launched= — no | yes | unknown
        self.census = "none"          # … and its census= — none | <survivors> | failed

    # -- small helpers ---------------------------------------------------------
    def v(self, name):
        return self.env.get(name, "")

    def require_token(self, name, value):
        if not _is_graph_token(value):
            fail_usage("%s contains whitespace/control bytes — a forged-record lever on a native probe line (Constraint 13)" % name)
        if '"' in value:
            fail_usage("%s contains a double quote — an injection lever (Constraint 13)" % name)

    def require_line_safe(self, name, value):
        if _has_control(value):
            fail_usage("%s contains control bytes — a forged identity/record lever (Constraint 13)" % name)

    def require_abs(self, name, value):
        spelled = _boot_spell(value)
        # absolute in the CANONICAL spelling, by the host flag (never os.path.isabs,
        # which is the running interpreter's flavour): a drive-rooted `X:/…` on a
        # Windows host (UNC and other `/`-rooted spellings refused by _boot_spell
        # already; a drive-relative `C:foo` fails here), a `/`-rooted path elsewhere
        absolute = re.match(r"\A[A-Za-z]:/", spelled) is not None if _BOOT_WINDOWS else spelled.startswith("/")
        if not absolute:
            fail_usage("%s must be an ABSOLUTE path (got '%s') — a relative path re-resolves under cd/PATH" % (name, value))
        return spelled

    def root_arg(self, member):
        """One LOOP_ESCAPE_ROOTS member as the helper's `--root` operand:
        `name=<the path in the boot spelling>` (round 43 PR-MED-002). The path
        half is validated by require_abs AND its returned spelling is what
        crosses the process boundary — the helper judges the operand with the
        native isabs and no MSYS conversion, so a `/c/...` root this wrapper
        admitted would otherwise be refused there (or, on an older Windows
        Python, denote another object). Identity on POSIX."""
        name, path = member.split("=", 1)
        return "%s=%s" % (name, self.require_abs("LOOP_ESCAPE_ROOTS", path))

    def helper_argv(self, *args):
        return [sys.executable, "-I", self.helper] + list(args)

    def helper_to_probe(self, *args):
        """Run ONE helper call whose record lands on the probe log through the
        RETAINED descriptor, and return the helper's exit code (round 39
        HIGH-001). Where an inherited descriptor appends (_INHERIT_APPEND —
        POSIX) the helper writes it itself, exactly as v44.0's `>&8`. Elsewhere
        (Windows) the record is captured and written HERE, by the process whose
        runtime owns the descriptor's append mode — never at a stale inherited
        file pointer, over another writer's bytes. Returns `(code, landed)`:
        the helper's exit code, and whether its record reached the probe log —
        always True on the inherited leg (the helper wrote it, and says so
        through its code); False when a CAPTURED record could not be appended,
        whole or in part (round 43 PR-LOW-001: the helper's code says what the
        helper decided, never that this process persisted its bytes — a
        refusal exit 3 beside a failed append is NOT a record on the log)."""
        if _INHERIT_APPEND:
            return subprocess.run(self.helper_argv(*args), stdin=subprocess.DEVNULL, stdout=self.probe_fd).returncode, True
        r = subprocess.run(self.helper_argv(*args), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE)
        if r.stdout:
            try:
                write_all(self.probe_fd, r.stdout)
            except OSError:
                return r.returncode, False
        return r.returncode, True

    # -- v48.0 D16: the per-leg files, the split, the tail -------------------------
    def leg_text(self, extra=(), stop=None):
        """The `<leg>.live` / `<leg>.exit` body: this process's pid and start
        token, then the role's identity once it is launched, then `extra`.

        Round 44 PR-LOW-015 — this process's OWN token is read once and kept
        WITH THE PID it was read for: a later record of the same process
        reuses it (a process's start never changes), and a process with
        another pid — the supervisor, after the two forks — never uses its
        parent's: it reads its own. Only a token that was read is kept; an
        answer of "unknown" is asked again at the next record. So where the
        token is a `ps` run, a record written after the first costs none —
        the launching process read its token for the claim, the supervisor
        for its `<leg>.live`. `stop` (a caller's signal test, else None) is
        for the read that is still needed: no `ps` is started once it is
        true, and the record says `wrapper_start=unknown`."""
        env = self.env
        me = os.getpid()
        if self.own_token is not None and self.own_token[0] == me:
            token = self.own_token[1]
        else:
            state, token = _boot_start_token(me, stop)
            if state == "alive":
                self.own_token = (me, token)
            else:
                token = "unknown"
        lines = ["ts=%s" % now_iso(), "run=%s" % env["LOOP_RUNKEY"]]
        if LEG_NAME_RE.match(env.get("LOOP_ROLE", "")):
            lines.append("role=%s" % env["LOOP_ROLE"])
        lines += ["leg=%s" % env["LOOP_LEG"], "wrapper_pid=%d" % me,
                  "wrapper_start=%s" % token,
                  "survive=%s" % self.survive]
        if self.child_pid is not None:
            if self.role_token is None:
                # read ONCE, right after the launch (the runtime's reader) and kept:
                # `.exit` is written when the role is gone and has no token to read
                rstate, rtoken = self.rt.proc_start_token(self.child_pid)
                self.role_token = rtoken if rstate == "alive" else "unknown"
            # the role is the leader of its own session (group_launch): its group is its pid
            lines += ["role_pid=%d" % self.child_pid, "role_start=%s" % self.role_token, "role_pgid=%d" % self.child_pid]
        return ("".join(l + "\n" for l in lines + list(extra))).encode("utf-8")

    def leg_claim(self):
        """Claim this leg's files by creating `<stem>.live` EXCLUSIVELY — the
        stem is the leg, or `<leg>.2` … when a file of that name is already
        there (a leg value used twice: the earlier leg's evidence is never
        overwritten, and a reader goes by the `leg=` line, not the name). Run
        once, by the launching process, before any fork; the descriptor is
        closed at once. The names come from the RAW environment, so the claim
        is made only when LOOP_PROBE_LOG is an absolute path in an existing
        folder and LOOP_RUNKEY / LOOP_LEG can each name a file. Any other
        spawn — and one whose folder refuses the file, or whose leg value was
        used LEG_STEM_TRIES times — runs single-process with no per-leg file
        and is REFUSED before START: by the validation's own earlier checks
        where one applies, else by prepare()'s check that the claim was made
        (a `params` refusal). No role is ever started without its
        `<leg>.live`."""
        env = self.env
        run, leg, raw = env.get("LOOP_RUNKEY", ""), env.get("LOOP_LEG", ""), env.get("LOOP_PROBE_LOG", "")
        if not (raw and LEG_NAME_RE.match(run) and LEG_NAME_RE.match(leg)):
            return
        try:
            probe = _boot_spell(raw)
        except _Refuse:
            return
        if _has_control(probe) or not (re.match(r"\A[A-Za-z]:/", probe) if _BOOT_WINDOWS else probe.startswith("/")):
            return
        log_root = os.path.dirname(probe)
        if not os.path.isdir(log_root):
            return
        for n in range(1, LEG_STEM_TRIES + 1):
            base = os.path.join(log_root, leg if n == 1 else "%s.%d" % (leg, n))
            if any(os.path.lexists(base + s) for s in (".live", ".exit", ".out", ".err")):
                continue
            try:
                fd = os.open(base + ".live", os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_BINARY, 0o666)
            except FileExistsError:
                continue
            except OSError:
                return
            try:
                write_all(fd, self.leg_text())
            except OSError:
                pass
            finally:
                os.close(fd)
            self.leg_base = base
            return

    def leg_write(self, suffix, extra=(), stop=None):
        """Write `<stem>.live` or `<stem>.exit` whole: a temporary file beside
        it, then one atomic replace (the identity record's bounded retry on a
        held-open destination). Best effort — a per-leg file that cannot be
        written never changes the spawn's exit code; the reader then calls the
        leg `unknown`, never `over`. `stop` is leg_text()'s (round 44): it
        can keep a `ps` from being started for this record, never the record
        from being written."""
        if self.leg_base is None:
            return False
        dst = self.leg_base + suffix
        tmp = "%s.tmp.%d" % (dst, os.getpid())
        try:
            with open(tmp, "wb") as fh:
                fh.write(self.leg_text(extra, stop))
            last = None
            for _ in range(IDENTITY_REPLACE_TRIES):
                try:
                    os.replace(tmp, dst)
                    last = None
                    break
                except PermissionError as e:
                    last = e
                    time.sleep(0.2)
            if last is not None:
                raise last
            return True
        except OSError:
            try:
                os.remove(tmp)
            except OSError:
                pass
            return False

    def leg_write_exit(self, ec, stop=None):
        """The wrapper's LAST act, on every path: `<stem>.exit` — the role's
        identity kept, the exit code, the time and the census result added —
        then `<stem>.live` removed. `stop` is leg_text()'s (round 44
        PR-LOW-015): every caller that may hold a caught signal gives its
        test — the tail's look for a failed fork's record, the supervisor's
        latch at its end. Written after the role's group handle is
        closed (on Windows that ends the Job and every member with it — what
        lets the reader call a Windows `.exit` `over`), and after this
        wrapper's own hold on the spawn lock is given up: under survival the
        tail returns the moment `.exit` appears, while this process is still
        exiting — a caller that spawns again at once must not find the lock
        held by a wrapper that has finished (a role that still holds the
        inherited descriptor keeps the lock, as before)."""
        if self.lock_fd is not None:
            try:
                os.close(self.lock_fd)
            except OSError:
                pass
            self.lock_fd = None
        if self.child_pid is not None and self.role_token is None:
            # round 66 LOW-005: the role's start token is read ONCE, at the launch, by the record written there. Where
            # that record could not be written (its temporary file refused) the token was never read — and it is NOT
            # read now: the role is gone, and its pid may be another process's by this time, whose token would be
            # recorded as the role's and proved "live" by every reader. Not read at the launch is `unknown` for good.
            self.role_token = "unknown"
        if self.leg_write(LEG_EXIT, ["launched=%s" % self.launched, "exit=%d" % ec, "exit_ts=%s" % now_iso(),
                                     "census=%s" % self.census], stop):
            try:
                os.remove(self.leg_base + LEG_LIVE)
            except OSError:
                pass

    def split(self):
        """D16 — the double fork. Returns None in the SUPERVISOR (which goes
        on to run the leg) and the exit code in the TAIL (the launching
        process). The FIRST child calls os.setsid() and forks again, then
        leaves at once by os._exit: it writes nothing and opens nothing, and
        the tail reaps it. The grandchild is the supervisor — a member (never
        the leader, so it can acquire no controlling terminal) of the session
        the first child made, and, its parent gone, the child of whichever
        process adopts orphans there: where that is a process above the
        composer, the tree walk a dying composer makes does not reach it
        (T5.1 / T5.4); survival() says, before anything is recorded or
        started, whether that is so (round 42). A host that refuses the first fork
        (a process limit) gets the single process, said in one stdout line —
        the leg is not lost to it, and the claimed `<leg>.live` already
        names this process.

        THE HANDSHAKE (round 41 PR-MED-025) — three rules, so that a first
        child that dies or is interrupted can never stand as proof that no
        supervisor exists. (1) Every blockable signal is BLOCKED from before
        the first fork: the first child lives its whole short life with the
        mask on, so a TERM / HUP / INT aimed at the tree cannot end it, or
        raise in it, between its fork and its exit; the tail restores the
        mask once its handlers are installed, the supervisor once it has
        left the tree and recorded itself. (2) The first child's exit status
        is 0 (its fork returned) or SPLIT_FORK_FAILED (its setsid or fork
        raised: no supervisor exists) — and the tail writes `launched=no`
        on SPLIT_FORK_FAILED alone; any other status (a KILL, a child that
        is stopped) is UNKNOWN and writes nothing. (3) The supervisor does
        not record itself or run the leg while its parent is still the
        first child: it waits until it has been re-parented, and past
        SPLIT_ORPHAN_BOUND_S it starts nothing."""
        self.launch_chain = _boot_ancestors(os.getpid())    # round 42 PR-MED-028: read before the fork, compared after it
        blocked = None
        try:
            blocked = signal.pthread_sigmask(signal.SIG_BLOCK, signal.valid_signals())
        except (AttributeError, OSError, ValueError):
            pass                    # no mask on this host: rules (2) and (3) still hold
        try:
            pid = os.fork()
        except OSError as e:
            self.unblock(blocked)
            say('SPAWN_WARN check=survive detail="the split could not be forked (%s) — this leg runs single-process, as under LOOP_SURVIVE=off: it does not outlive the launching process tree"'
                % _record_safe(_os_error_word(e)))
            return None
        if pid == 0:
            first = os.getpid()
            try:
                os.setsid()
                child = os.fork()
            except BaseException:
                os._exit(SPLIT_FORK_FAILED)
            if child != 0:
                os._exit(0)
            # --- the supervisor. First: out of the launching tree. Its parent is
            # the first child until that process has exited; only then is it
            # nobody's child there, and only then may it start anything. ---
            deadline = time.monotonic() + SPLIT_ORPHAN_BOUND_S
            while os.getppid() == first:
                if time.monotonic() > deadline:
                    os._exit(1)
                time.sleep(0.001)
            # --- stdin from the null device, stdout / stderr
            # appended to the two per-leg files (a dead host cannot break a
            # helper call's output), nothing else inherited ---
            try:
                fds = [os.open(os.devnull, os.O_RDONLY)]
                for suffix in (LEG_OUT, LEG_ERR):
                    # created HERE and exclusively: the claim saw neither name, so a
                    # file (or a link) that appeared since is not this leg's and is
                    # never appended to
                    fds.append(os.open(self.leg_base + suffix,
                                       os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o666))
                for target, fd in enumerate(fds):
                    os.dup2(fd, target)
                for fd in fds:
                    if fd > 2:
                        os.close(fd)
            except BaseException:
                os._exit(1)
            # round 42 PR-MED-028: a new parent is not yet a place outside the
            # composer's tree — say which of the three it is, before anything is
            # recorded as surviving and before any role exists
            self.survive, adopter, composer = self.survival()
            if self.survive == "in-tree":
                say('SPAWN_WARN check=survive detail="the supervisor was re-parented to pid %d, which is the composer (pid %d) or a process under it — this leg does NOT outlive the composer\'s process tree; it runs split all the same, and %s says survive=in-tree"'
                    % (adopter, composer, os.path.basename(self.leg_base) + LEG_LIVE))
            # the supervisor's own pid and token — what the tail watches and what a
            # reader tests. A supervisor that cannot record itself starts nothing:
            # no role may run under a wrapper nobody can find (the tail then gives
            # its SPAWN_LOST once the bound has passed).
            if not self.leg_write(LEG_LIVE):
                os._exit(1)
            self.unblock(blocked)
            return None
        return self.tail(pid, blocked)

    def survival(self):
        """round 42 PR-MED-028 — what the supervisor may say of itself once it
        has a new parent: `(word, adopter pid, composer pid)`. An orphan is
        given to the NEAREST living ancestor that asked for orphans (a child
        subreaper) and only failing one to the host's first process — and
        that ancestor is always an ancestor of the launching process too, the
        user's service manager in the ordinary case. So a new parent alone
        says nothing; only the composer's own pid tells "above the composer"
        from "at or below it". The composer's pid is `CLAUDE_PID` from the
        inherited environment when it is a decimal pid (what a Claude Code
        session exports to its tool shells; the source the watcher's identity
        record uses). The words:
          `on`         — ESTABLISHED: the composer is an ancestor of the
                         launching process and is NOT an ancestor of the
                         supervisor;
          `in-tree`    — the composer is still among the supervisor's
                         ancestors: the leg runs, and does not outlive the
                         composer's process tree (the caller says so in one
                         `SPAWN_WARN check=survive` line);
          `unverified` — it cannot be told: no composer pid (any composer but
                         Claude Code), a pid that is not an ancestor of the
                         launching process, or a chain that could not be
                         read. The split was taken; nothing more is claimed."""
        composer = _pid_of(self.env.get("CLAUDE_PID", ""))
        chain = _boot_ancestors(os.getpid())
        if composer is None or chain is None or self.launch_chain is None or composer not in self.launch_chain:
            return "unverified", None, composer
        if composer in chain:
            return "in-tree", chain[0], composer
        return "on", (chain[0] if chain else 0), composer

    @staticmethod
    def unblock(mask):
        """Put back the signal mask split() saved (None: none was set)."""
        if mask is not None:
            try:
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)
            except (AttributeError, OSError, ValueError):
                pass

    def tail(self, first_child, blocked=None):
        """The launching process after the split: it only FOLLOWS the two
        per-leg files to its own stdout and stderr. The supervisor is not its
        child, so it cannot wait for it: the end is `<stem>.exit` appearing —
        the tail exits with the code that file records — or the supervisor's
        start token going away with no `.exit` (TAIL_LOST_CODE and one
        `SPAWN_LOST` line). A TERM, HUP or INT ends the TAIL ALONE:
        TAIL_DETACHED_CODE and one `SPAWN_DETACHED supervisor_pid=<n>` line —
        never 129 / 130 / 143, which stay the supervisor's (a signal to the
        recorded `wrapper_pid` stops the role, as before).

        Round 41, three rules of the tail. PR-MED-025: only the first
        child's SPLIT_FORK_FAILED status closes the leg's file with
        `launched=no`; any other status but 0 is unknown and the tail goes
        on to its ordinary wait for the supervisor to record itself (the
        wait for that status is itself bounded). PR-MED-026: a supervisor
        that has TERMINATED and is not reaped (_boot_terminated) is lost
        like one that is gone — after the one more read of `<leg>.exit`.
        PR-MED-027: the tail never writes to its own stdout or stderr; two
        _Mirror threads do, behind bounded queues, so neither `<leg>.exit`
        nor a signal waits on a consumer — the last forwarding is given up
        once a mirror has accepted nothing for MIRROR_STALL_S. Round 42
        PR-MED-029: that forwarding also stops at once on a signal — the
        tail then returns its own code 5 with `SPAWN_DETACHED`, never the
        leg's code — and the tail's closing line is bounded in wall time
        (MIRROR_GRACE_S for what is queued, MIRROR_CLOSE_S for the line).

        Round 43 PR-LOW-014 — the rule for EVERY wait of the tail, since a
        signal is acted on only where the tail next looks at what its
        handler caught. A wait is one of two kinds. It LOOKS on every turn
        and ends at once on a signal, its caller then detaching: the wait
        for the first child's status, the last forwarding, both waits of a
        `SPAWN_LOST` line, the poll (the look is at the loop's top) and the
        two probes of the supervisor where they are a `ps` run (the run is
        ended and reaped). Or it is one of detached()'s own two, entered
        once a signal IS the outcome: bounded in wall time, never looking
        again, so a second signal changes nothing. And every way out that
        is not a signal's — the leg's code, the loss, the fork that failed —
        goes through leave(): ONE LAST LOOK immediately before the return.
        What is promised is exactly that: a TERM, HUP or INT the tail has
        seen by that look gets code 5 and `SPAWN_DETACHED`, whatever the
        tail had decided or written; one that lands after it finds a
        process already ending with its code. A signal changes the tail's
        code and line, and withholds no record the tail has the evidence
        for: a failed fork whose status the tail has READ still leaves
        `launched=no` in `<leg>.exit` — written before the look, never
        rewritten — and that status is read once even when a signal is
        already caught (a first child that has not exited by then leaves
        it unknown, as any unread status is: nothing is written). The
        one write the tail does not interrupt is that file's: a replace,
        retried for at most a second where it is refused. Round 44
        PR-LOW-015: the record's own token costs no wait — it is the one
        this process read for the claim, kept with its pid (leg_text); where
        none was kept the read is given the look, and no `ps` is started
        for it once a signal is caught (`wrapper_start=unknown`).

        Round 45 PR-LOW-016 — the rule covers every LOOP as well as every
        wait: the forwarding itself, relay(), is a loop, and until this
        round it had neither a look nor a count (the rounds above fixed the
        waits around it). Now every wait and every loop of the tail either
        LOOKS at the caught signals on every turn — relay() before every
        chunk — or has a FIXED BOUND, a count or a wall-time limit:
        detached()'s two waits, a relay() batch (RELAY_BATCH_CHUNKS chunks
        per stream), the replace retry, a `ps` run and its reap, the drain
        of a queue before a closing line (the queue's 16 items), the lines
        of one 64 KiB read of a leg file, and the few loops over a fixed
        pair or triple. So a signal caught while a backlog
        is forwarded to a consumer that keeps pace ends the batch before
        the next read, and no stream's forwarding can hold the other
        stream, the read of `<leg>.exit` or the supervisor's probes for
        more than one batch. One wait is neither, and is kept out of a
        caught signal's way instead: the start of the two mirror threads,
        taken while the split's mask still holds every signal (where the
        host gave the split no mask it is the interpreter's own wait for a
        thread to begin). What no bound of the wrapper's reaches is round
        44's floor: the kernel's own calls on the leg's regular files and
        its start of `ps`."""
        caught = []
        for name in ("SIGTERM", "SIGINT", "SIGHUP"):
            sig = getattr(signal, name, None)
            if sig is not None:
                try:
                    if signal.getsignal(sig) is signal.SIG_IGN:
                        continue          # a launcher that had it ignored (nohup) keeps that: the tail stays
                    signal.signal(sig, lambda signum, frame: caught.append(signum))
                except (ValueError, OSError):
                    pass

        def signalled():
            """THE LOOK: has a TERM, HUP or INT been caught? The handler only
            appends to `caught`, so a signal is acted on where the tail next
            calls this — which is why every wait below either calls it on every
            turn or is one of detached()'s own two (round 43 PR-LOW-014)."""
            return bool(caught)

        # round 45: the two mirror threads are started HERE — the handlers in
        # place, the split's mask still on — so the start of a thread (the
        # interpreter's own wait for it to begin) is never a wait a CAUGHT
        # signal can fall into: a signal is still held, and is caught only
        # once the mask is lifted, below. (The threads keep the mask: a signal
        # sent to the process is delivered to this, the main thread.)
        offsets = {LEG_OUT: 0, LEG_ERR: 0}
        mirrors = {LEG_OUT: _Mirror(1), LEG_ERR: _Mirror(2)}
        self.unblock(blocked)                 # the handlers are in place: a signal held since the split lands in `caught`
        # the first child's status, waited for inside a bound (it exits at once
        # unless something holds it): None = not known. Round 43: the status is
        # READ once before the first look, so a signal that is already caught —
        # one held since the split — does not cost a failed fork its record; the
        # WAIT for a status that is not there yet ends at once on a signal.
        status = None
        deadline = time.monotonic() + SPLIT_REAP_BOUND_S
        while True:
            try:
                reaped, st = os.waitpid(first_child, os.WNOHANG)
            except OSError:
                break                         # reaped elsewhere (an inherited SIGCHLD handler): the files decide
            if reaped == first_child:
                status = st
                break
            if signalled() or time.monotonic() > deadline:
                break
            time.sleep(0.001)

        def relay():
            """Move what the two per-leg files gained into the mirrors' queues —
            as much as each queue has room for, never a wait. Round 45
            PR-LOW-016: ONE BATCH per stream and call — at most
            RELAY_BATCH_CHUNKS chunks — and THE LOOK before every chunk: a
            signal caught while a batch is forwarded ends it before the next
            read, and a stdout that keeps growing while its consumer keeps pace
            cannot hold stderr, the read of `<leg>.exit` or the supervisor's
            probes for longer than one batch. The offset moves only for a chunk
            the mirror took; what is not forwarded stays in the file for the
            next call. Returns True when a batch ended on its COUNT — more may
            be waiting, and the caller goes round again WITHOUT its sleep (with
            its own look and its other checks first), so forwarding is as fast
            as it was — and False when every stream ended on its file's end, a
            full queue, a refused offer, a closed mirror or a signal."""
            more = False
            for suffix in (LEG_OUT, LEG_ERR):
                mirror = mirrors[suffix]
                if mirror.closed:
                    continue                  # a closed mirror: keep following for the code
                try:
                    with open(self.leg_base + suffix, "rb") as fh:
                        fh.seek(offsets[suffix])
                        for _ in range(RELAY_BATCH_CHUNKS):
                            if signalled() or mirror.queue.full():
                                break
                            chunk = fh.read(1 << 16)
                            if not chunk or not mirror.offer(chunk):
                                break
                            offsets[suffix] += len(chunk)
                        else:
                            more = True       # the count ended the batch, nothing else did
                except OSError:
                    pass                      # not created yet
            return more

        def settle():
            """The last forwarding, once the files no longer grow (the supervisor
            is finished or gone): until both files are read to their end and both
            queues are empty. Bounded by PROGRESS — it gives up once neither
            mirror has accepted a byte for MIRROR_STALL_S; a consumer that is slow
            keeps it going, one that has stopped does not — and INTERRUPTIBLE
            (round 42 PR-MED-029): it looks at `caught` on every turn and stops at
            once. Returns True when a signal ended it — the caller then detaches,
            whatever it was about to return — and False when the forwarding is
            done or was given up. Round 45: a turn forwards one relay() batch;
            when that batch ended on its count the next turn follows without
            the sleep."""
            seen, since = None, time.monotonic()
            while True:
                if signalled():
                    return True
                more = relay()
                behind = False
                for suffix, mirror in mirrors.items():
                    if mirror.closed:
                        continue
                    if not mirror.idle():
                        behind = True
                    else:
                        try:
                            behind = behind or os.path.getsize(self.leg_base + suffix) > offsets[suffix]
                        except OSError:
                            pass
                if not behind:
                    return False
                now = (mirrors[LEG_OUT].written, mirrors[LEG_ERR].written)
                if now != seen:
                    seen, since = now, time.monotonic()
                elif time.monotonic() - since > MIRROR_STALL_S:
                    return False
                if not more:
                    time.sleep(0.01)

        def wait_idle(which, bound, heed):
            """Wait, for at most `bound` seconds of wall time, until every mirror
            in `which` has written what it was given. With `heed` it LOOKS on
            every turn, before anything else, and returns True at once when a
            signal has been caught (round 43); otherwise, and always without
            `heed`, False."""
            end = time.monotonic() + bound
            while True:
                if heed and signalled():
                    return True
                if time.monotonic() >= end or all(mirror.idle() for mirror in which):
                    return False
                time.sleep(0.01)

        def last_line(line, heed):
            """The tail's own closing line (round 42 PR-MED-029: bounded in WALL
            time, whatever the mirrors are doing). What is already queued gets
            MIRROR_GRACE_S; what is still unwritten then is dropped — it is in the
            per-leg files — and the line, alone on stdout's queue, gets
            MIRROR_CLOSE_S. A mirror nobody reads costs the tail those two bounds
            and no more. Round 43: with `heed` (a line that is NOT the signal's
            own) both waits look, and True is returned the moment a signal has
            been caught — before the line is queued, or after it; the caller
            then detaches. Without `heed` (detached()'s line) nothing looks."""
            if wait_idle(mirrors.values(), MIRROR_GRACE_S, heed):
                return True
            mirrors[LEG_OUT].close_with((line + "\n").encode("utf-8", "surrogateescape"))
            return wait_idle([mirrors[LEG_OUT]], MIRROR_CLOSE_S, heed)

        def detached():
            """A TERM, HUP or INT reached the tail: its own code and line, on
            EVERY path — while the leg runs, during the last forwarding of a
            leg that has ended or been lost, and while the tail was writing a
            `SPAWN_LOST` line of either kind (the leg's state is in its files).
            Entered once, by a `return`: its two waits are bounded in wall time
            and do not look again, so a second signal neither restarts nor
            lengthens them and prints no second line. A `SPAWN_LOST` line that
            was already handed to the mirror when the signal came is not
            unprinted — it gets the grace like any queued output, and this line
            follows it."""
            last_line("SPAWN_DETACHED supervisor_pid=%s" % (sup_pid if sup_pid is not None else "unknown"), False)
            return TAIL_DETACHED_CODE

        def leave(code, line=None):
            """EVERY way out of the tail that is not a signal's (round 43
            PR-LOW-014): the closing `line`, if this way out has one, then THE
            LAST LOOK. `code` is returned only when no signal has been caught by
            that look; otherwise the tail detaches — whatever it had decided, and
            whatever it had already written to the leg's files. A signal that
            lands after this look finds a process that is already ending with
            its code: it is not seen."""
            if line is not None and last_line(line, True):
                return detached()
            if signalled():
                return detached()
            return code

        sup_pid, sup_token = None, None     # bound before the first way out: detached() reads sup_pid
        if status is not None and os.WIFEXITED(status) and os.WEXITSTATUS(status) == SPLIT_FORK_FAILED:
            # the ONE status that proves no supervisor was ever forked (the first
            # child's setsid or fork raised): nothing runs under this leg, and the
            # tail — the only process left that knows it — closes the leg's file
            # itself (launched=no, its own code). Any other status proves nothing
            # and writes nothing: the loop below then waits for the supervisor to
            # record itself, as for a clean exit. The file is written FIRST and
            # whatever has been caught (it is the one true record of this leg, and
            # it claims nothing about a running role); a signal seen after it
            # changes the tail's code and line, never that file.
            self.leg_write_exit(TAIL_LOST_CODE, signalled)
            return leave(TAIL_LOST_CODE,
                         'SPAWN_LOST supervisor_pid=unknown detail="the supervisor could not be forked — nothing was started; %s records launched=no"'
                         % (os.path.basename(self.leg_base) + LEG_EXIT))
        me = os.getpid()
        began = time.monotonic()
        # the supervisor's token is one small file read where the host has a
        # procfs; elsewhere it is a `ps` run, so it is asked every two seconds
        # only (`<leg>.exit` is still read at every poll)
        token_every = 0.0 if os.path.exists(PROC_STAT % me) else 2.0
        token_at = 0.0
        lost = None
        while True:
            more = relay()
            if signalled():
                return detached()
            ended = _read_leg_file(self.leg_base + LEG_EXIT)
            code = ended.get("exit", "")
            if code.isascii() and code.isdigit() and len(code) <= 3:
                if sup_pid is None:
                    sup_pid = _pid_of(ended.get("wrapper_pid", ""))   # for the closing line, should a signal end the forwarding
                if settle():
                    return detached()         # a signal during the last forwarding is not turned into the leg's code
                return leave(int(code))
            if lost is not None:
                if settle():
                    return detached()
                return leave(TAIL_LOST_CODE,
                             'SPAWN_LOST supervisor_pid=%s detail="%s — no %s was written, so the leg\'s end is not known from here: read the leg with the role-liveness reader before any respawn"'
                             % (sup_pid if sup_pid is not None else "unknown", lost, os.path.basename(self.leg_base) + LEG_EXIT))
            elapsed = time.monotonic() - began
            if sup_pid is None:
                kv = _read_leg_file(self.leg_base + LEG_LIVE)
                wpid = _pid_of(kv.get("wrapper_pid", ""))
                if wpid is not None and wpid != me:
                    sup_pid, sup_token = wpid, kv.get("wrapper_start", "")
                elif elapsed > TAIL_RECORD_BOUND_S:
                    lost = "the supervisor did not record itself within %d s" % TAIL_RECORD_BOUND_S
                    continue
            elif elapsed - token_at >= token_every:
                token_at = elapsed
                # round 43: both probes are given THE LOOK — where they are a `ps`
                # run, a signal ends the run (the answer is then unknown / False,
                # and the loop's top detaches)
                state, token = _boot_start_token(sup_pid, signalled)
                if state == "gone" or (state == "alive" and sup_token not in ("", "unknown") and token != sup_token):
                    # gone: `.exit` is read ONCE more above before the loss is declared
                    # (the supervisor writes it as its last act, then exits)
                    lost = "the supervisor (pid %d) is gone" % sup_pid
                    continue
                if state == "alive" and _boot_terminated(sup_pid, signalled):
                    # round 41 PR-MED-026: terminated and not reaped — its token is
                    # still there, and it will write nothing more; the same one more
                    # read of `.exit`, then the loss
                    lost = "the supervisor (pid %d) has terminated and has not been reaped" % sup_pid
                    continue
            if not more:
                # round 45: a batch that ended on its count is followed at once —
                # the look, `<leg>.exit` and the probes above were taken in between
                time.sleep(TAIL_POLL_FAST_S if elapsed < 2.0 else TAIL_POLL_S)

    def survive_wanted(self):
        """The split is taken where `os.fork` exists, the per-leg files are
        claimed, and LOOP_SURVIVE is not `off` (unset is on; any other value is
        refused by the validation, in the supervisor)."""
        return hasattr(os, "fork") and self.leg_base is not None and self.env.get("LOOP_SURVIVE", "") != "off"

    # -- the run ---------------------------------------------------------------
    def run(self):
        if hasattr(signal, "SIGCHLD"):
            # an inherited SIG_IGN would have the kernel reap every child at once
            # (Popen.wait would fabricate 0); bash always owned SIGCHLD itself
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        # v48.0 (D12 / D16): nothing inherited rides on — then the leg's files
        # are claimed and, under survival, the process splits: all of it before
        # the validation's first side effect, and before this wrapper creates a
        # thread, a lock or a descriptor of its own.
        _close_inherited_fds()
        self.leg_claim()
        if self.survive_wanted():
            code = self.split()
            if code is not None:
                return code                   # the tail
        # round 44 PR-LOW-015: the end's record gives leg_text() a stop test — the
        # latch of a signal this wrapper caught and forwarded; an interrupt or a
        # crash counts as one. It matters only where this process's token was
        # never read (the start's read failed): no `ps` is then started for it.
        try:
            ec = self.run_leg()
        except SystemExit as e:
            self.leg_write_exit(e.code if isinstance(e.code, int) else 1, self.interrupted)
            raise
        except BaseException:
            self.leg_write_exit(1, lambda: True)
            raise
        self.leg_write_exit(ec, self.interrupted)
        return ec

    def interrupted(self):
        """Has this wrapper caught a TERM, INT or HUP (install_signals' latch)?"""
        return bool(self.cancel)

    def run_leg(self):
        try:
            self.validate()
            self.prepare()
            self.write_start()
        except _Refuse as r:
            err('SPAWN_REFUSED check=%s detail="%s"' % (r.check, r.detail))
            self.rm_tmpd()
            return 2
        except _LockHeld:
            return 3
        self.started = True
        self.install_signals()
        ec = 1
        try:
            ec = self.post_start()
        except _Refuse as r:
            err('SPAWN_REFUSED check=%s detail="%s"' % (r.check, r.detail))
            ec = 2
        except _Signalled as s:
            ec = s.code
        except SystemExit as e:
            ec = e.code if isinstance(e.code, int) else 1
        except BaseException:
            import traceback
            traceback.print_exc()
            ec = 1
        finally:
            self.interruptible = False
            self.footer_and_teardown(ec)
        return ec

    # -- validation (refusals happen BEFORE any probe-log write) -----------------
    def validate(self):
        env = self.env
        # --- closed param-file transport detection (PR-HIGH-010) ---
        # round 29 PR-MED-001: an explicit LOOP_SPAWN_ENV in the boot spelling
        # (D31 — MSYS converts no environment value); the relative default as is
        param_file = _boot_spell(env["LOOP_SPAWN_ENV"]) if env.get("LOOP_SPAWN_ENV") else ".cursor/loops/spawn-wrapper.env"
        if os.path.isfile(param_file):
            try:
                with open(param_file, "rb") as fh:
                    for raw in fh.read().split(b"\n"):
                        line = raw.decode("utf-8", "surrogateescape")
                        if line == "" or line.startswith("#"):
                            continue
                        # round 31 PR-LOW-001: the exact twin of v44.0's `LOOP_[A-Z_]*=*` case
                        # pattern — ONE class character after the prefix, then anything up
                        # to an `=` (a glob star is `.*`, not a class repeat)
                        if re.match(r"\ALOOP_[A-Z_].*=", line):
                            raise _Refuse("param-file", "the param-file transport is CLOSED (PR-HIGH-010) — parameters are environment-only; a LOOP_* key in %s is stale or tampering, refusing" % param_file)
            except OSError:
                pass
        # --- the required block ---
        for name in ("LOOP_CLAUDE_BIN", "LOOP_CWD", "LOOP_PROBE_LOG", "LOOP_ROLE_LOG", "LOOP_RUNKEY", "LOOP_ROLE"):
            if not env.get(name):
                fail_usage("%s unset" % name)
        if not env.get("LOOP_PHASE"):
            fail_usage("LOOP_PHASE unset (ROLE: start phase= is required — F-07)")
        if not env.get("LOOP_LEG"):
            fail_usage("LOOP_LEG unset (the activation leg key is required)")
        if not env.get("LOOP_MODEL"):
            fail_usage("LOOP_MODEL unset (a model-less start would emit strict-invalid missing-model)")
        if not env.get("LOOP_ESCAPE_ROOTS"):
            fail_usage("LOOP_ESCAPE_ROOTS unset (the escape-check root manifest is required — F-09)")
        # --- token-pool selection + the least-credential env (v32 TD.2) ---
        sel = env.get("LOOP_OAUTH_TOKEN_ENV", "")
        if sel:
            if not TOKEN_POOL_RE.match(sel):
                fail_usage("LOOP_OAUTH_TOKEN_ENV must NAME a numbered pool variable (CLAUDE_CODE_OAUTH_TOKEN_<N>, N >= 1) — the selection grammar is exact (v32 TD.2)")
            if not env.get("LOOP_PROFILE_DIR"):
                fail_usage("LOOP_OAUTH_TOKEN_ENV requires LOOP_PROFILE_DIR — the numbered token maps deterministically onto ~/.claude-acct<N> (v32 TD.2)")
            acct_n = sel[len("CLAUDE_CODE_OAUTH_TOKEN_"):]
            if not _acct_dir_matches(env["LOOP_PROFILE_DIR"], acct_n):
                fail_usage("LOOP_OAUTH_TOKEN_ENV names pool %s but LOOP_PROFILE_DIR does not end in .claude-acct%s — the acct<N> <-> TOKEN_<N> mapping is deterministic; a mismatch refuses (v32 TD.2)" % (acct_n, acct_n))
            if not env.get(sel):
                fail_usage("LOOP_OAUTH_TOKEN_ENV names %s but that variable is unset or empty — a missing pool credential refuses, never a silent seated-store fallback (v32 TD.2)" % sel)
            self.token_env_name = sel
            env["CLAUDE_CODE_OAUTH_TOKEN"] = env[sel]   # indirection; supersedes any ambient canonical
        for key in [k for k in list(env) if TOKEN_POOL_RE.match(k)]:
            del env[key]
        env.pop("LOOP_OAUTH_TOKEN_ENV", None)
        # --- the prompt transports ---
        if env.get("LOOP_PROMPT_FILE") and env.get("LOOP_PROMPT"):
            fail_usage("LOOP_PROMPT_FILE and LOOP_PROMPT are mutually exclusive")
        if not env.get("LOOP_PROMPT_FILE") and not env.get("LOOP_PROMPT"):
            fail_usage("one of LOOP_PROMPT_FILE / LOOP_PROMPT is required")
        if env.get("LOOP_PROMPT_FILE"):
            # round 29 PR-MED-001: the file is opened by its boot spelling (a
            # `/c/...` or `C:\...` value on a Windows host; identity on POSIX) —
            # the conversion precedes the filesystem operation it governs; the
            # absolute-path contract on the same value runs below, unmoved
            self.prompt_bytes = self.acquire_prompt(_boot_spell(env["LOOP_PROMPT_FILE"]))
        # round 31 PR-LOW-002: unset OR empty is `scoped` (v44.0's `${LOOP_PERMS:-scoped}`)
        # — normalised ONCE here, read by the argv build; empty never means bypass
        self.perms = env.get("LOOP_PERMS") or "scoped"
        if self.perms not in ("scoped", "bypass"):
            fail_usage("LOOP_PERMS must be scoped or bypass")
        # v48.0 D16: unset or empty is `on` (where the host can fork); the split
        # itself was decided before this block, from the same value
        if env.get("LOOP_SURVIVE", "") not in ("", "on", "off"):
            fail_usage("LOOP_SURVIVE must be 'on', 'off' or unset (unset = on where the host has os.fork; off = today's single process — v48.0 D16)")
        if env.get("LOOP_ROLE_LOG_ROTATE", "") not in ("", "leg"):
            fail_usage("LOOP_ROLE_LOG_ROTATE must be 'leg' or unset (absent = size-threshold rotation only; v33.0 D8)")
        # --- native-value safety (R16 PR-HIGH-002; Constraint 13) ---
        self.require_token("LOOP_RUNKEY", env["LOOP_RUNKEY"])
        self.require_token("LOOP_ROLE", env["LOOP_ROLE"])
        self.require_token("LOOP_LEG", env["LOOP_LEG"])
        if env.get("LOOP_RESUME_SESSION"):
            self.require_token("LOOP_RESUME_SESSION", env["LOOP_RESUME_SESSION"])
            # v47.0 D10: a session id is a UUID — the pin looks for a file of that name
            if not RESUME_UUID_RE.match(env["LOOP_RESUME_SESSION"]):
                fail_usage("LOOP_RESUME_SESSION must be a session UUID (8-4-4-4-12 hex digits) — the resume pin looks for projects/*/<id>.jsonl under the profile folders, and no other shape names a transcript (v47.0 D10)")
            self.resume = env["LOOP_RESUME_SESSION"]
        self.require_line_safe("LOOP_CWD", env["LOOP_CWD"])
        self.require_line_safe("LOOP_MODEL", env["LOOP_MODEL"])
        self.require_line_safe("LOOP_PHASE", env["LOOP_PHASE"])
        if env.get("LOOP_EFFORT"):
            self.require_line_safe("LOOP_EFFORT", env["LOOP_EFFORT"])
        self.profile_dir = ""
        if env.get("LOOP_PROFILE_DIR"):
            self.require_line_safe("LOOP_PROFILE_DIR", env["LOOP_PROFILE_DIR"])
            # the ONE spelled value every later consumer reads (D17): the router
            # folder rule, CLAUDE_CONFIG_DIR, the identity's profile_dir= — the
            # identity on POSIX; `C:/...` on a Windows host whatever was typed
            self.profile_dir = _boot_spell(env["LOOP_PROFILE_DIR"])
        # --- the absolute-path contract (PR-MED-042), on the boot spelling ---
        self.claude_bin = self.require_abs("LOOP_CLAUDE_BIN", env["LOOP_CLAUDE_BIN"])
        if not os.access(self.claude_bin, os.X_OK):   # bash's `[ -x ]`: the same test, the same refusal
            fail_usage("LOOP_CLAUDE_BIN is not an executable file: %s" % env["LOOP_CLAUDE_BIN"])
        self.cwd = self.require_abs("LOOP_CWD", env["LOOP_CWD"])
        if not os.path.isdir(self.cwd):
            fail_usage("LOOP_CWD is not a directory: %s" % env["LOOP_CWD"])
        self.ambient_dir = self.ambient_folder()   # v47.0 D10: read here, before any CLAUDE_CONFIG_DIR export
        self.probe_log = self.require_abs("LOOP_PROBE_LOG", env["LOOP_PROBE_LOG"])
        self.role_log = self.require_abs("LOOP_ROLE_LOG", env["LOOP_ROLE_LOG"])
        self.prompt_file = self.require_abs("LOOP_PROMPT_FILE", env["LOOP_PROMPT_FILE"]) if env.get("LOOP_PROMPT_FILE") else ""
        self.identity_file = self.require_abs("LOOP_IDENTITY_FILE", env["LOOP_IDENTITY_FILE"]) if env.get("LOOP_IDENTITY_FILE") else ""
        self.spawn_lock = self.require_abs("LOOP_SPAWN_LOCK", env["LOOP_SPAWN_LOCK"]) if env.get("LOOP_SPAWN_LOCK") else ""
        self.add_dirs = []
        if env.get("LOOP_ADD_DIRS"):
            sep = ";" if _BOOT_WINDOWS else ":"
            for member in env["LOOP_ADD_DIRS"].split(sep):
                if member:
                    self.add_dirs.append(self.require_abs("LOOP_ADD_DIRS", member))
        # --- v41.0 D3: router mode — LOOP_ROUTE_BIN's parameter contract (the ONE list) ---
        if env.get("LOOP_ROUTE_BIN"):
            self.route_bin = self.require_abs("LOOP_ROUTE_BIN", env["LOOP_ROUTE_BIN"])
            if not (os.path.isfile(self.route_bin) and os.access(self.route_bin, os.X_OK)):
                fail_usage("LOOP_ROUTE_BIN is not an executable regular file: %s (router mode refusal 1 — v41.0 D3)" % env["LOOP_ROUTE_BIN"])
            if not env.get("LOOP_IDENTITY_FILE"):
                fail_usage("LOOP_ROUTE_BIN requires LOOP_IDENTITY_FILE — the identity record carries the routed folder and the re-pick's identity values (router mode refusal 2 — v41.0 D3/D5)")
            if not env.get("LOOP_ISO"):
                fail_usage("LOOP_ROUTE_BIN requires LOOP_ISO — the router's --run is this run's iso-id, unique per run; a run without one is not routable (router mode refusal 3 — v41.0 D3)")
            if not env.get("LOOP_PROFILE_DIR"):
                fail_usage("LOOP_ROUTE_BIN requires LOOP_PROFILE_DIR — the explicit fallback the role runs on when the router has no answer (router mode refusal 4 — v41.0 D3)")
            if self.token_env_name:
                fail_usage("LOOP_ROUTE_BIN and LOOP_OAUTH_TOKEN_ENV are mutually exclusive — a token pool binds the profile dir to .claude-acct<N>, router mode selects a logged-in folder (router mode refusal 5 — v41.0 D3)")
            roots = []
            cwd_real = _boot_real(self.cwd)
            if cwd_real is None:
                fail_usage("LOOP_CWD could not be resolved to a clean physical path (realpath / readlink -f failed, or the resolved path carries a control byte): %s — an executor-writable root the topology rule cannot compare byte-exactly refuses router mode (round 10 PR-MED-023 — v41.0 D3)" % env["LOOP_CWD"])
            roots.append(cwd_real)
            for root in self.add_dirs:
                rr = _boot_real(root)
                if rr is None or not os.path.exists(root):
                    fail_usage("LOOP_ADD_DIRS root could not be resolved to a clean physical path (realpath / readlink -f failed, or the resolved path carries a control byte): %s — an executor-writable root the topology rule cannot compare byte-exactly refuses router mode (round 10 PR-MED-023 — v41.0 D3)" % root)
                roots.append(rr)
            bin_real = _boot_real(self.route_bin)
            if bin_real is None:
                fail_usage("LOOP_ROUTE_BIN could not be resolved to a clean physical path (realpath / readlink -f failed, or the resolved path carries a control byte): %s (router mode topology rule — v41.0 D3; PR-MED-023)" % env["LOOP_ROUTE_BIN"])
            if any(_boot_inside(bin_real, r) for r in roots):
                fail_usage("LOOP_ROUTE_BIN resolves inside an executor-writable root (LOOP_CWD or a LOOP_ADD_DIRS root): %s — a selector a spawned role could rewrite is never run (router mode topology rule — v41.0 D3)" % bin_real)
            word, check = _boot_dir_word(self.profile_dir, roots)
            if word:
                fail_usage("LOOP_PROFILE_DIR fails the router answer rule's folder checks (%s) while LOOP_ROUTE_BIN is set: %s — under router mode the fallback is held to the same rule as an answer (router mode refusal 6 — v41.0 D3; the failing check: %s)" % (word, env["LOOP_PROFILE_DIR"], check))
            self.route_enabled = True
            self.route_roots = [self.cwd] + list(self.add_dirs)
        # --- LOOP_ESCAPE_ROOTS members: name=/abs/path, base FIRST ---
        eroots = env["LOOP_ESCAPE_ROOTS"].split(";")
        self.rootargs = []
        for member in eroots:
            if not member:
                fail_usage("LOOP_ESCAPE_ROOTS has an empty member")
            if "=" not in member or not member.split("=", 1)[1]:
                fail_usage("LOOP_ESCAPE_ROOTS member '%s' is not name=/abs/path" % member)
            self.rootargs += ["--root", self.root_arg(member)]
        if not eroots[0].startswith("base="):
            fail_usage("LOOP_ESCAPE_ROOTS: base= is REQUIRED and FIRST")
        # --- v33.0 D4 escape-verdict inputs → the helper's flags (both twins) ---
        self.escargs = []
        if env.get("LOOP_EDIT_SURFACE"):
            self.require_line_safe("LOOP_EDIT_SURFACE", env["LOOP_EDIT_SURFACE"])
            if env["LOOP_EDIT_SURFACE"] not in [m.split("=", 1)[0] for m in eroots]:
                fail_usage("LOOP_EDIT_SURFACE '%s' must name a LOOP_ESCAPE_ROOTS member (the spawned role's edit surface is one of the manifest roots — v33.0 D4)" % env["LOOP_EDIT_SURFACE"])
            self.escargs += ["--edit-surface", env["LOOP_EDIT_SURFACE"]]
        if env.get("LOOP_ALLOW_PATH"):
            self.require_line_safe("LOOP_ALLOW_PATH", env["LOOP_ALLOW_PATH"])
            self.escargs += ["--allow-path", env["LOOP_ALLOW_PATH"]]
        if env.get("LOOP_ISO"):
            self.require_token("LOOP_ISO", env["LOOP_ISO"])
            self.escargs += ["--iso", env["LOOP_ISO"]]
        if env.get("LOOP_LIVENESS"):
            self.require_token("LOOP_LIVENESS", env["LOOP_LIVENESS"])
            self.escargs += ["--liveness", env["LOOP_LIVENESS"]]
        # --- v33.0 D3 per-pass cap keys: all three or none (Constraint 16) ---
        present = sum(1 for k in ("LOOP_PASS", "LOOP_PEER_ROUND", "LOOP_CAP") if env.get(k))
        self.pass_kv = []
        if present == 3:
            self.require_token("LOOP_PASS", env["LOOP_PASS"])
            self.require_token("LOOP_PEER_ROUND", env["LOOP_PEER_ROUND"])
            self.require_token("LOOP_CAP", env["LOOP_CAP"])
            self.pass_kv = ["pass=%s" % env["LOOP_PASS"], "peer_round=%s" % env["LOOP_PEER_ROUND"], "cap=%s" % env["LOOP_CAP"]]
        elif present != 0:
            fail_usage("LOOP_PASS / LOOP_PEER_ROUND / LOOP_CAP ride together or not at all (partial-pass-keys — absence is the standalone shape; v33.0 D3, Critical Constraint 16)")
        # --- the spawn-path dependency gate (Constraint 10): a blob-clean helper ---
        # (the python3 gate is the SHIM's — D14; this file runs under sys.executable)
        here = os.path.dirname(os.path.abspath(__file__))
        self.checkout_helper = os.path.join(here, HELPER_NAME)
        self.repo_root = os.path.dirname(here)
        if not os.path.isfile(self.checkout_helper):
            fail_usage("helper missing: %s (Constraint 10 fail-closed)" % self.checkout_helper)
        wt = self.blob_of(self.checkout_helper)
        self.helper_head = self.head_blob("scripts/" + HELPER_NAME)
        if not wt or not self.helper_head or wt != self.helper_head:
            fail_usage("helper blob verification FAILED (git hash-object vs HEAD:scripts/loop-journal.py) — an untracked/dirty helper never rides a spawn (Constraint 10)")
        # --- v47.0 D10: the resume pin, the NO-ROUTER timing — the last refusal of
        # this block (every earlier refusal keeps its place). Under router mode the
        # router's answer is a candidate, so the search runs after the pick
        # (route_block), post-START. ---
        if self.resume and not self.route_enabled:
            self.pin_resolve()

    def acquire_prompt(self, path):
        """R14 PR-MED-001: SINGLE-OPEN prompt acquisition at the validation
        boundary — ONE open (non-blocking, so a writer-less FIFO never parks),
        the regular-file check on the OPENED DESCRIPTOR, the bytes read whole.
        A non-regular object, an unreadable or vanished source refuses; the
        trailing newlines are stripped as the v44.0 command substitution did."""
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOCTTY", 0)
        fd = None
        try:
            fd = os.open(path, flags)
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):
                raise OSError(errno.EINVAL, "not a regular file")
            chunks = []
            while True:
                chunk = os.read(fd, 1 << 16)
                if not chunk:
                    break
                chunks.append(chunk)
        except OSError:
            fail_usage("LOOP_PROMPT_FILE capture FAILED at single-open acquisition (non-regular object at open, unreadable, vanished, or a blocked non-regular open past the bound): %s — a child never spawns on unverified prompt bytes (R14 PR-MED-001)" % path)
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        return b"".join(chunks).replace(b"\x00", b"").rstrip(b"\n")

    # -- v47.0 D10: the resume pin ---------------------------------------------------
    def ambient_folder(self):
        """The folder a role started with NO profile selection runs on: the
        CLAUDE_CONFIG_DIR this wrapper inherited, else `~/.claude` — resolved
        as the NATIVE child will resolve the value it inherits UNCHANGED
        (`_native_folder` against LOOP_CWD; round 16 PR-MED-022 — never the
        MSYS conversion, which the child does not get). "" when that folder
        cannot be established (a Windows drive-relative spelling on another
        drive than LOOP_CWD's). NEVER refuses — it is computed on every
        spawn, a fresh one included; the value as inherited is kept in
        self.ambient_raw."""
        self.ambient_raw = self.env.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
        return _native_folder(self.ambient_raw, self.cwd)

    def role_path(self, folder):
        """A profile folder as the ROLE will see it (`_native_folder` against
        LOOP_CWD — the directory the role is started in, never this wrapper's
        own working directory), or "" when it cannot be established. For
        LOOP_PROFILE_DIR `folder` is the spelled value the wrapper exports;
        for the ambient folder it is the value the role inherits as it is."""
        return _native_folder(folder, self.cwd)

    def pin_resolve(self, answer="", dir_check=None):
        """The holder search (the module docstring's v47.0 item is the rule).
        `answer` is the router's answer when it passed the folder checks;
        `dir_check(folder) -> (word, check)` is the answer rule's folder
        check, given under router mode. Sets self.pin or raises the
        `resume-pin` refusal; prints nothing. A candidate is SEARCHED, named
        and compared by its role_path; `holder` keeps the spelling it was given
        in (what is exported and recorded, as on a fresh spawn)."""
        session = self.resume
        cands = []   # (kind, the folder as given, its role_path)
        for kind, folder in (("profile", self.profile_dir), ("answer", answer), ("ambient", self.ambient_raw)):
            if not folder:
                continue
            path = self.role_path(folder)
            if not path:
                # round 16 PR-MED-022: a spelling whose folder cannot be established is an
                # INDETERMINATE candidate — never searched somewhere else in its place
                raise _Refuse("resume-pin", "the profile folder %s (%s) cannot be placed for session %s: a drive-relative spelling on another drive than LOOP_CWD's names a folder only the role's own process can resolve — a folder that cannot be searched is never passed over for a copy elsewhere; spell it as a full drive path (C:/...), or name the folder as LOOP_PROFILE_DIR (v47.0 D10)"
                              % (_record_safe(folder), PIN_LABELS[kind], session))
            if path not in [p for _k, _f, p in cands]:
                cands.append((kind, folder, path))
        held = []
        for kind, folder, path in cands:
            word, mtime, why = _pin_probe(path, session)
            if word == "indeterminate":
                raise _Refuse("resume-pin", "the profile folder %s (%s) could not be searched for session %s: %s — a folder that cannot be searched is never passed over for a copy elsewhere; make it readable (or move the unreadable entry out of its projects/) and spawn again, or start a fresh leg (v47.0 D10)"
                              % (_record_safe(path), PIN_LABELS[kind], session, why))
            if word == "holds":
                held.append((mtime, kind, folder, path))
        if not held:
            raise _Refuse("resume-pin", "no profile folder holds session %s (no projects/*/%s.jsonl) — searched: %s — pass the folder that holds the transcript as LOOP_PROFILE_DIR, or start a fresh leg; a resume is never started where its transcript is not (v47.0 D10)"
                          % (session, session, "; ".join("%s (%s)" % (_record_safe(p), PIN_LABELS[k]) for k, _f, p in cands)))
        newest = max(h[0] for h in held)
        _m, kind, holder, path = next(h for h in held if h[0] == newest)   # equal times: the earlier candidate
        if self.token_env_name and kind != "profile":
            # round 14 MED-001: a token-pool selection binds the pool's token to
            # LOOP_PROFILE_DIR (the validation block's acct<N> <-> TOKEN_<N> rule,
            # v32 TD.2) — the pin never starts that credential on another folder
            raise _Refuse("resume-pin", "the newest transcript of session %s is in %s (%s), not in LOOP_PROFILE_DIR — under LOOP_OAUTH_TOKEN_ENV the role runs on LOOP_PROFILE_DIR only (the pool's token is bound to that folder; v32 TD.2), and an older copy there is never chosen instead; move the transcript into LOOP_PROFILE_DIR (the transfer recipe), or resume without the pool (v47.0 D10)"
                          % (session, _record_safe(path), PIN_LABELS[kind]))
        if dir_check is not None and kind != "answer":
            word, check = dir_check(path)
            if word:
                raise _Refuse("resume-pin", "the newest transcript of session %s is in %s (%s), which fails the router answer rule's folder checks (%s: %s) — under router mode a role is started only on a folder that passes them, and an older copy elsewhere is never chosen instead; correct the folder, or spawn without LOOP_ROUTE_BIN (v47.0 D10)"
                              % (session, _record_safe(path), PIN_LABELS[kind], word, check))
        self.pin = {"kind": kind, "holder": holder, "path": path, "stale": [h[3] for h in held if h[0] < newest]}

    def pin_say(self):
        """The pin's two stdout lines (the composer's channel; never a probe-log
        record): the holder when it is not the folder the spawn was given, and
        every candidate that holds a strictly older copy."""
        if self.pin is None:
            return
        given = "profile" if self.profile_dir else "ambient"
        if self.pin["kind"] != given:
            say('SPAWN_WARN check=resume-pin detail="%s"' % _record_safe(self.pin["path"]))
        if self.pin["stale"]:
            say('SPAWN_WARN check=resume-pin-stale detail="%s"' % "; ".join(_record_safe(p) for p in self.pin["stale"]))

    def pin_recheck(self):
        """The second read, immediately before the role's environment is built:
        the holder must still read as holding the session."""
        word, _mtime, why = _pin_probe(self.pin["path"], self.resume)
        if word != "holds":
            raise _Refuse("resume-pin", "the transcript of session %s no longer reads as held by %s (%s) — it was there when the folders were searched; spawn again, or start a fresh leg (v47.0 D10)"
                          % (self.resume, _record_safe(self.pin["path"]), why or "projects/*/%s.jsonl is gone" % self.resume))

    def git_argv(self, *args):
        return [shutil.which("git") or "git", "-C", self.repo_root] + list(args)

    def blob_of(self, path):
        try:
            r = subprocess.run(self.git_argv("hash-object", "--", path), stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except OSError:
            return ""
        return r.stdout.decode("ascii", "replace").strip() if r.returncode == 0 else ""

    def head_blob(self, rel):
        try:
            r = subprocess.run(self.git_argv("rev-parse", "HEAD:" + rel), stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except OSError:
            return ""
        return r.stdout.decode("ascii", "replace").strip() if r.returncode == 0 else ""

    def make_snapshot_dir(self):
        """round 43 PR-MED-001: a fresh private (0700) directory under the git
        directory of this file's own repository (`git rev-parse
        --absolute-git-dir` — a linked worktree's or a submodule's own git
        directory included), or None when it cannot be resolved or created —
        the caller refuses with the existing snapshot refusal."""
        try:
            r = subprocess.run(self.git_argv("rev-parse", "--absolute-git-dir"), stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except OSError:
            return None
        if r.returncode != 0:
            return None
        git_dir = os.fsdecode(r.stdout).rstrip("\r\n")
        if not git_dir or not os.path.isdir(git_dir):
            return None
        try:
            return tempfile.mkdtemp(prefix="loop-spawn-snap.", dir=git_dir)
        except OSError:
            return None

    # -- the pre-START preparation: the lock, the logs, the workspace, the snapshot, the import, the prompt snapshot
    def prepare(self):
        env = self.env
        # --- Round-4 S-A leg 2: the rehydrate trigger (post-validation, pre-START) ---
        say('STICKY_REREAD run=%s role=%s detail="rehydrate: re-read STICKY.md + the plan\'s Current State / Handoff Note (Loop config: included) before acting on this spawn\'s events"' % (env["LOOP_RUNKEY"], env["LOOP_ROLE"]))
        # --- the spawn lock (D19 / D32) ---
        if self.spawn_lock:
            self.take_lock()
        # --- the required-log OPEN (PR-MED-021 / PR-MED-026): a non-regular target refuses before the open ---
        for name, path in (("LOOP_ROLE_LOG", self.role_log), ("LOOP_PROBE_LOG", self.probe_log)):
            if os.path.exists(path) and not os.path.isfile(path):
                fail_usage("%s exists but is not a regular file (device/FIFO/directory?): %s" % (name, path))
        # --- v33.0 D8: spawn-time role-log rotation BEFORE the open ---
        self.rotate_role_log()
        # (round 34 PR-LOW-001: created with 0o666 so the UMASK decides the mode, as
        # v44.0's `exec 7>>` / `exec 8>>` did — never a fixed 0644; round 39 MED-001:
        # binary on every host — the bytes written are the bytes given)
        try:
            self.role_fd = os.open(self.role_log, os.O_WRONLY | os.O_APPEND | os.O_CREAT | _O_BINARY, 0o666)
        except OSError:
            fail_usage("LOOP_ROLE_LOG is not an appendable file (directory/device/broken symlink?): %s" % self.role_log)
        # v46.4 (D1): where the bytes THIS leg adds begin — read here, after any
        # rotation and before the child starts. Every leg of a role appends to
        # this one file unless it is rotated, so the post-wait session-id read
        # starts at this offset (the leg's own bytes, unless another writer
        # appends to the file meanwhile); an unreadable size leaves it None and
        # that read is skipped (no `session=` line — never an earlier leg's id).
        try:
            self.role_log_start = os.fstat(self.role_fd).st_size
        except OSError:
            self.role_log_start = None
        try:
            self.probe_fd = os.open(self.probe_log, os.O_WRONLY | os.O_APPEND | os.O_CREAT | _O_BINARY, 0o666)
        except OSError:
            fail_usage("LOOP_PROBE_LOG is not an appendable file (directory/device/broken symlink?): %s" % self.probe_log)
        for name, path in (("LOOP_ROLE_LOG", self.role_log), ("LOOP_PROBE_LOG", self.probe_log)):
            if not os.path.isfile(path):
                fail_usage("%s did not resolve to a regular file: %s" % (name, path))
        # v48.0 D16 / D17: NO ROLE WITHOUT ITS EVIDENCE. Every refusal above kept
        # its place; a spawn that reached this point with its logs open and no
        # claimed `<leg>.live` (the log folder refused the file, its name holds a
        # control byte, LOOP_RUNKEY / LOOP_LEG cannot name a file, or the leg
        # value was used LEG_STEM_TRIES times) is refused here — the close's
        # guard and the watcher read a leg they cannot see as no leg at all.
        if self.leg_base is None:
            fail_usage("the per-leg files (<leg>.live / <leg>.exit) could not be claimed beside LOOP_PROBE_LOG (%s) — the folder refused a new file, the path or LOOP_RUNKEY / LOOP_LEG cannot name one ([A-Za-z0-9._-] only), or the leg value was used %d times; no role is started without its liveness evidence (v48.0 D16)"
                       % (_record_safe(self.probe_log), LEG_STEM_TRIES))
        # --- the private pump directory (v44.0's `$tmpd`, its refusal and its place in
        # the refusal order unchanged — D7). From round 43 PR-MED-001 it holds NOTHING
        # executable and nothing role-steering: TMPDIR and the host temp root are
        # writable by a sandboxed same-user peer of another run, and a helper
        # snapshot there was re-opened for every helper call across the role's whole
        # lifetime (reproduced: a replaced copy was executed post-wait, exit 0, no
        # warning). The two snapshots live in the snapshot workspace below. ---
        try:
            self.tmpd = tempfile.mkdtemp(prefix="loop-wrapper-pump.", dir=env.get("TMPDIR") or tempfile.gettempdir())
        except OSError:
            self.tmpd = None
        if not self.tmpd or not os.path.isdir(self.tmpd):
            self.tmpd = None
            fail_usage("could not create the private pump directory (TMPDIR unwritable?) — refusing rather than spawning without a waitable role-log pump")
        # --- the snapshot workspace (round 43 PR-MED-001): a private directory under
        # the GIT DIRECTORY of this file's own repository — the object store the
        # helper's blob is verified against, so the snapshot sits behind the SAME
        # trust anchor as the check (whoever can write there already controls
        # `HEAD:`); never TMPDIR, never a caller-supplied directory. Removed at
        # teardown with the pump directory. ---
        self.snapd = self.make_snapshot_dir()
        # --- the helper snapshot (R18 PR-HIGH-001, R19 PR-MED-001): verify-then-copy-then-reverify ---
        snapshot = os.path.join(self.snapd, HELPER_NAME) if self.snapd else ""
        try:
            if not self.snapd:
                raise OSError(errno.ENOENT, "no snapshot workspace")
            shutil.copyfile(self.checkout_helper, snapshot)
        except OSError:
            fail_usage("could not snapshot the verified helper into the private workspace (R18 PR-HIGH-001) — refusing rather than re-invoking a child-replaceable helper post-wait")
        snap_blob = self.blob_of(snapshot)
        if not snap_blob or snap_blob != self.helper_head:
            fail_usage("helper SNAPSHOT blob verification FAILED (git hash-object of the $tmpd copy != HEAD:scripts/loop-journal.py) — the check-to-cp window was raced; refusing (R19 PR-MED-001)")
        self.helper = snapshot
        # --- the runtime import FROM THE SNAPSHOT (D30) ---
        # (round 43 PR-MED-001: no bytecode beside the snapshot — the workspace
        # holds the verified copy and the prompt snapshot, nothing derived; the
        # launcher's runtime_import does the same)
        saved_dwb = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec = importlib.util.spec_from_file_location("loop_journal_runtime", snapshot)
            rt = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(rt)
        except BaseException as e:
            sys.dont_write_bytecode = saved_dwb
            fail_usage("the helper snapshot could not be imported as the runtime (%s: %s) — refusing (D30)" % (type(e).__name__, str(e)[:160]))
        sys.dont_write_bytecode = saved_dwb
        missing = [n for n in RUNTIME_NAMES if not hasattr(rt, n)]
        if missing:
            fail_usage("the helper snapshot lacks the v45.0 runtime (%s) — a helper older than the wrapper never rides a spawn (D15 / D30)" % ", ".join(missing))
        self.rt = rt
        # the canonical spelling of every recorded path value (identity on POSIX — D17)
        self.cwd = rt.canon_path(self.cwd, resolve=False)
        self.probe_log = rt.canon_path(self.probe_log, resolve=False)
        self.role_log = rt.canon_path(self.role_log, resolve=False)
        if self.identity_file:
            self.identity_file = rt.canon_path(self.identity_file, resolve=False)
        # --- prompt-template hygiene (F1) — warn-only; the inline transport binds here ---
        if not self.prompt_file:
            self.prompt_bytes = os.fsencode(env["LOOP_PROMPT"])
        if not self.prompt_bytes.strip(b" \t\n\r\x0b\x0c"):
            fail_usage("captured caller prompt has NO non-whitespace content (zero-byte/newline-only/whitespace-only source: %s) — a child never receives a footer-only snapshot (R9 PR-HIGH-004 / R11 PR-HIGH-006)" % (env.get("LOOP_PROMPT_FILE") or "inline"))
        if b"execute-loop-cx" in self.prompt_bytes:
            say('SPAWN_WARN check=fork-label detail="prompt names the deprecated execute-loop-cx fork — stale template?"')
        if env["LOOP_RUNKEY"].encode("utf-8") not in self.prompt_bytes:
            say('SPAWN_WARN check=runkey-missing detail="prompt does not name runkey %s — reused scaffold from another run?"' % env["LOOP_RUNKEY"])
        # --- Round-4 S-D: the PRIVATE combined prompt snapshot ---
        # (round 43 PR-MED-001: beside the helper snapshot — the role's stdin is read
        # from this file, so it must not sit where a sandboxed peer may rewrite it)
        self.snapshot_path = os.path.join(self.snapd, "prompt.snapshot")
        footer = [
            FOOTER_SEP,
            "EXIT RULES for this spawned role (run=%s role=%s):" % (env["LOOP_RUNKEY"], env["LOOP_ROLE"]),
            "- ATOMIC final step: immediately before your final message run exactly one validated declaration — python3 scripts/loop-journal.py emit VERIFY_OK --run %s --role %s --log \"$LOOP_PROBE_LOG\" children=<your actual still-live child count> (LOOP_PROBE_LOG is inherited in your environment — expand it in your shell exactly as written, never retype the path; invoke the helper by its path in your working checkout; the tool owns the format, you supply the count). Any count > 0 means KEEP WAITING, never exit." % (env["LOOP_RUNKEY"], env["LOOP_ROLE"]),
            "- Your LITERAL last output line is the exit sentinel: ROLE: handoff ts=<real date -Iseconds read> run=%s reason=<phase-complete|composer-run|must-pause> [gate=\"<one-liner>\"]" % env["LOOP_RUNKEY"],
        ]
        try:
            with open(self.snapshot_path, "wb") as fh:
                fh.write(self.prompt_bytes + b"\n")
                fh.write(("\n".join(footer) + "\n").encode("utf-8"))
        except OSError:
            fail_usage("could not materialize the private prompt snapshot under the pump workspace (S-D fail-closed)")

    def take_lock(self):
        # round 34 PR-LOW-001: POSIX opens the lock WRITE-ONLY for append — v44.0's
        # `exec 9>>` — so a writable lock file needs no read permission (flock, the
        # holder-line write and fstat all work on it; the held path's holder read is
        # its own guarded open below). The Windows byte-range lock keeps read-write.
        # Created with 0o666: the umask decides the mode, as the shell's `>>` did.
        access = os.O_RDWR if os.name == "nt" else os.O_WRONLY
        try:
            fd = os.open(self.spawn_lock, access | os.O_APPEND | os.O_CREAT | _O_BINARY, 0o666)
        except OSError:
            fail_usage("LOOP_SPAWN_LOCK could not be opened: %s" % self.spawn_lock)
        held = False
        try:
            if os.name == "nt":
                import msvcrt
                os.lseek(fd, LOCK_FAR_OFFSET, 0)
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                except OSError:
                    held = True
            else:
                import fcntl
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    held = True
        except (ImportError, OSError):
            held = True
        if held:
            holder = "unknown"
            try:
                size = os.fstat(fd).st_size
                with open(self.spawn_lock, "rb") as fh:
                    fh.seek(max(0, size - 4096))
                    tail = fh.read(min(size, 4096)).rstrip(b"\n").split(b"\n")
                last = tail[-1][:200].decode("utf-8", "replace") if tail and tail[-1] else ""
                holder = last or "unknown"
            except OSError:
                pass
            say('SPAWN_LOCK_HELD run=%s role=%s holder="%s"' % (self.env["LOOP_RUNKEY"], self.env["LOOP_ROLE"], holder))
            try:
                os.close(fd)
            except OSError:
                pass
            raise _LockHeld()
        self.lock_fd = fd
        try:
            os.write(fd, ("wrapper_pid=%d ts=%s run=%s role=%s\n" % (os.getpid(), now_iso(), self.env["LOOP_RUNKEY"], self.env["LOOP_ROLE"])).encode("utf-8"))
        except OSError:
            pass
        say("SPAWN_LOCK_ACQUIRED run=%s role=%s" % (self.env["LOOP_RUNKEY"], self.env["LOOP_ROLE"]))

    def rotate_role_log(self):
        reason = ""
        if os.path.isfile(self.role_log):
            try:
                size = os.stat(self.role_log).st_size
            except OSError:
                fail_usage("could not read the size of LOOP_ROLE_LOG for the v33.0 D8 rotation decision: %s" % self.role_log)
            if self.env.get("LOOP_ROLE_LOG_ROTATE", "") == "leg":
                reason = "policy=leg size=%d" % size
            elif size > ROLE_LOG_ROTATE_BYTES:
                reason = "policy=size size=%d threshold=%d" % (size, ROLE_LOG_ROTATE_BYTES)
        if not reason:
            return
        stem = self.role_log[:-4] if self.role_log.endswith(".log") else self.role_log
        ts = time.strftime("%Y%m%d-%H%M%S")
        if not re.match(r"\A\d{8}-\d{6}\Z", ts):
            fail_usage("could not read a YYYYMMDD-HHMMSS timestamp for the role-log archive name (date failed?)")
        archive = ""
        for n in range(1, 100):
            cand = "%s.leg-%s.log" % (stem, ts) if n == 1 else "%s.leg-%s-%d.log" % (stem, ts, n)
            if os.path.exists(cand):
                continue
            # NO-CLOBBER: link-then-unlink on POSIX (EEXIST if the name appeared),
            # rename on Windows (FileExistsError there); verified moved
            try:
                if os.name == "nt":
                    os.rename(self.role_log, cand)
                else:
                    os.link(self.role_log, cand)
                    os.unlink(self.role_log)
            except OSError:
                continue
            if not os.path.exists(self.role_log) and os.path.isfile(cand):
                archive = cand
                break
        if not archive:
            fail_usage("role-log rotation could not create a unique archive name for %s (every %s.leg-%s[-n].log up to -99 exists) — refusing rather than overwrite an earlier leg's evidence (v33.0 D8, PR-MED-008); nothing was moved" % (self.role_log, stem, ts))
        say('SPAWN_WARN check=role-log-rotated detail="role log rotated before open: %s archive=%s (v33.0 D8; the new leg starts on a fresh %s)"' % (reason, archive, self.role_log))

    def write_start(self):
        line = "SPAWN_WRAPPER_START ts=%s run=%s role=%s" % (now_iso(), self.env["LOOP_RUNKEY"], self.env["LOOP_ROLE"])
        if self.env.get("LOOP_RESUME_SESSION"):
            line += " resume=%s" % self.env["LOOP_RESUME_SESSION"]
        try:
            write_all(self.probe_fd, (line + "\n").encode("utf-8"))
        except OSError:
            fail_usage("LOOP_PROBE_LOG write failed on the SPAWN_WRAPPER_START record: %s" % self.probe_log)

    # -- signals: forwarded to the recorded child group; the footer carries the code
    def install_signals(self):
        codes = {}
        for name, code in (("SIGTERM", 143), ("SIGINT", 130), ("SIGHUP", 129)):
            sig = getattr(signal, name, None)
            if sig is not None:
                codes[sig] = code

        def handler(signum, frame):
            code = codes.get(signum, 143)
            self.forward_signal(signum)
            self.pending_code = code
            self.cancel.append(signum)
            if self.interruptible:
                raise _Signalled(code)
        for sig in codes:
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass

    def honour_latch(self):
        """round 29 PR-MED-002: a teardown the handler recorded while no child
        existed ends the spawn here, on its documented code (129 / 130 / 143,
        the footer written by the one teardown owner) — before a role starts."""
        if self.pending_code is not None:
            raise _Signalled(self.pending_code)

    def forward_signal(self, signum):
        if self.group is None:
            return
        try:
            if os.name == "nt":
                self.rt.group_stop(self.group, kill=False)
            else:
                os.killpg(self.group["proc"].pid, signum)
        except (OSError, ValueError):
            pass

    # -- post-START ---------------------------------------------------------------
    def post_start(self):
        env = self.env
        rt = self.rt
        run, role, leg = env["LOOP_RUNKEY"], env["LOOP_ROLE"], env["LOOP_LEG"]
        # --- DR-1 emission 3 (pre leg): the before-digests, PRE-SPAWN ---
        log_root = os.path.dirname(self.probe_log)
        self.prestate = os.path.join(log_root, "%s-escape-%s.pre" % (run, leg))
        esc_base = ["escape-check", "--run", run, "--role", role]
        r = subprocess.run(self.helper_argv(*(esc_base + ["--capture", "pre", "--leg", leg, "--log-root", log_root] + self.rootargs + self.escargs)),
                           stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            raise _Refuse("escape-pre", "pre-spawn escape-check capture failed — refusing (exit 2, no spawn; F-04 fail-closed)")
        self.pre_created = True
        # round 29 PR-MED-002: a cancellation the handler LATCHED while a pre-child
        # helper ran (the handler never raises outside the principal wait) is
        # honoured before any further step — v44.0's trap exited at once; no
        # role is started after a recorded teardown
        self.honour_latch()
        # --- v41.0 D3/D4/D6: the pick — after the pre-capture, before ROLE: start ---
        if self.route_enabled:
            self.route_block()
            self.honour_latch()
        # --- v47.0 D10: the resume pin's stdout lines (both timings print here —
        # after the first STICKY_REREAD, before ROLE: start; nothing on a fresh spawn) ---
        self.pin_say()
        # --- DR-1 emission 2: the wrapper-owned ROLE: start, via the helper ---
        start_kv = ["phase=%s" % env["LOOP_PHASE"], "backend=claude-p", "model=%s" % env["LOOP_MODEL"], "leg=%s" % leg]
        if env.get("LOOP_EFFORT"):
            start_kv.append("effort=%s" % env["LOOP_EFFORT"])
        start_flags = []
        if self.pass_kv:
            start_kv += self.pass_kv
            start_flags = ["--read-log", self.probe_log]
        if self.helper_to_probe("emit", "ROLE:start", "--run", run, "--role", role, *(start_flags + start_kv)) != (0, True):
            raise _Refuse("role-start", "the helper refused the ROLE: start emission — refusing (exit 2, no spawn)")
        # v48.0 D23: the start is on the log, so this wrapper owes the leg's end
        # (footer_and_teardown writes it on every path from here)
        self.role_started = True
        self.role_start_time = time.monotonic()
        self.honour_latch()   # round 29 PR-MED-002: the last read before the launch
        # --- the invocation build ---
        argv = [self.claude_bin, "-p", "--output-format", "stream-json", "--verbose"]
        # v46.3 (plan-spawn-time-shield D2): the settings shield — a constant, on both tiers, a fresh spawn and a resume
        argv += ["--setting-sources", "user,project"]
        if self.perms == "bypass":
            argv.append("--dangerously-skip-permissions")
        else:
            argv += ["--permission-mode", "acceptEdits"]
            if env.get("LOOP_ALLOWED_TOOLS"):
                argv += ["--allowedTools", env["LOOP_ALLOWED_TOOLS"]]
        argv += ["--model", env["LOOP_MODEL"]]
        if env.get("LOOP_EFFORT"):
            argv += ["--effort", env["LOOP_EFFORT"]]
        for root in self.add_dirs:
            argv += ["--add-dir", root]
        if env.get("LOOP_RESUME_SESSION"):
            argv += ["--resume", env["LOOP_RESUME_SESSION"]]
        # v41.0 D3/D4: the EFFECTIVE profile folder — the router's answer, else the fallback.
        # v47.0 D10: on a resume, the HOLDER — read once more first (a transcript gone
        # since the search refuses; no child exists yet); an ambient holder leaves the
        # inherited environment exactly as it was (no export).
        if self.pin is not None:
            self.pin_recheck()
            self.eff_profile_dir = "" if self.pin["kind"] == "ambient" else self.pin["holder"]
        else:
            self.eff_profile_dir = self.route_dir or self.profile_dir
        self.identity_dir = self.eff_profile_dir or self.ambient_dir
        if self.eff_profile_dir:
            env["CLAUDE_CONFIG_DIR"] = self.eff_profile_dir
            if self.claude_bin.startswith("/mnt/"):
                env["WSLENV"] = (env["WSLENV"] + ":" if env.get("WSLENV") else "") + "CLAUDE_CONFIG_DIR/p"
        try:
            os.chdir(self.cwd)
        except OSError:
            return 1
        # --- the role-log pump: a pipe + a reader thread (D18) ---
        self.pump = Pump(self.role_fd)
        try:
            self.pump.start()
        except RuntimeError:
            raise _Refuse("pump-start", "the role-log pump thread could not be started — refusing (no child started, nothing stranded)")
        # --- the spawn: the child inside the runtime's group, the snapshot on stdin ---
        child_env = dict(env)
        child_env.pop("SHELLOPTS", None)
        # round 43 PR-MED-002: what the ROLE inherits across this boundary —
        # (a) LOOP_PROBE_LOG in the canonical spelling this wrapper itself uses (the
        # footer tells the role to expand exactly this variable for its exit
        # declaration; a raw `/c/...` value would not name the same file to a
        # native program — identity on POSIX); (b) NEITHER of the shim's two
        # MSYS exports: they silence Git Bash's conversion for the shim → wrapper
        # hand-over only, and inherited by the role they would switch off argument
        # conversion for every native command it runs (measured on PC1: with the
        # export a `/c/Users` argument reaches a native program unconverted).
        # The helper subprocesses above keep them — they take canonical operands.
        child_env["LOOP_PROBE_LOG"] = self.probe_log
        child_env.pop("MSYS_NO_PATHCONV", None)
        child_env.pop("MSYS2_ENV_CONV_EXCL", None)
        # v48.0 D12: a takeover's seat nonce never crosses a role boundary — a
        # role's helper call under the composer's flag is refused like anyone's
        child_env.pop("LOOP_SEAT", None)
        ec = None
        setup_failed = None
        try:
            with open(self.snapshot_path, "rb") as stdin_fh:
                try:
                    # round 33 PR-MED-001: on POSIX the role inherits the spawn lock's
                    # descriptor (v44.0's fd 9) — the lock's open file description lives
                    # as long as the role or any descendant holding it, so a second spawn
                    # on the same lock is refused while the role runs, even after this
                    # wrapper's own signal exit; the evidence descriptors stay closed in
                    # the child. On Windows the byte-range lock is per process and the Job
                    # dies with the wrapper, so nothing is handed over there.
                    lock_fds = (self.lock_fd,) if (self.lock_fd is not None and os.name != "nt") else ()
                    self.group = rt.group_launch(argv, stdout=self.pump.write_fd, stderr=self.pump.write_fd,
                                                 stdin=stdin_fh, env=child_env, pass_fds=lock_fds)
                except OSError as e:
                    if isinstance(e, getattr(rt, "_GroupSetupError", ())):
                        # round 29 PR-MED-004: the group primitive's OWN failure after
                        # a child may already have started (a Windows Job assignment;
                        # the primitive names the pid and its kill / reap outcome) —
                        # the survivor count is UNKNOWN, so the census below is the
                        # capture-failure form carrying that text, never children=0
                        setup_failed = "group setup failed: " + _record_safe(getattr(e, "strerror", None) or str(e))[:160]
                        ec = 126
                        self.launched = "unknown"   # v48.0 D16: a child may run outside the group — never `launched=no`
                    else:
                        # the exec failed: bash's background job would have exited 126 / 127
                        ec = 127 if isinstance(e, FileNotFoundError) else 126
        finally:
            self.pump.close_writer()
        if self.group is not None:
            self.child_pid = self.group["proc"].pid
            # v48.0 D16: the role's pid, start token and group join `<leg>.live`
            # at once — from here a reader can test the role itself, whatever
            # becomes of this wrapper
            self.launched = "yes"
            self.leg_write(LEG_LIVE, stop=self.interrupted)
            if self.cancel:
                # round 29 PR-MED-002: a cancellation that landed DURING the launch
                # (before ownership was recorded, so the handler could forward
                # nothing) is forwarded to the group now that it is ours, and the
                # spawn ends on the documented code — never a wait on a child the
                # teardown never reached
                self.forward_signal(self.cancel[-1])
                raise _Signalled(self.pending_code)
        # --- the identity record: write-tmp -> atomic rename (F5) ---
        if self.identity_file:
            self.write_identity("")
        # --- wait ---
        if self.group is not None:
            self.interruptible = True
            try:
                # round 30 PR-MED-001: a cancellation latched between the post-handle
                # read and this point (the identity write) is consumed INSIDE the
                # armed boundary — an earlier latch ends the spawn here through the
                # same _Signalled → footer owner, a later one raises from the handler;
                # the wait never depends on the forwarded signal being honoured
                self.honour_latch()
                rc = self.group["proc"].wait()
            finally:
                self.interruptible = False
            ec = 128 + (-rc) if rc < 0 else rc
        # --- the exit census (ORDER PINNED: before the pump wait) ---
        census_ok = setup_failed is None   # round 29 PR-MED-004: an unknown survivor count is never zero
        children = 0
        if self.group is not None:
            children = rt.exit_census(self.group)
            if children is None:
                census_ok = False
            elif children > 0:
                time.sleep(1)
                children = rt.exit_census(self.group)
                if children is None:
                    census_ok = False
            # v48.0 D16: `<leg>.exit`'s census= — the survivor count, `failed` when the
            # census could not count, `none` when none was taken (no role, or a signalled end)
            self.census = "%d" % children if census_ok else "failed"
        # --- the BOUNDED wait on the pump ---
        pump_status = self.pump.wait(PUMP_BOUND_S)
        rl_kv = []
        if pump_status == 0:
            rl_kv = ["rl_suppressed=%d" % ST.count]
        # --- DR-1 emission 3 (post leg): the after-digests, MAIN flow ---
        post_rc, post_landed = self.helper_to_probe(*(esc_base + ["--capture", "post", "--leg", leg, "--log-root", log_root] + self.rootargs + self.escargs))
        if not post_landed:
            # round 43 PR-LOW-001: the capture leg's append failed — whatever the helper
            # decided, its record is NOT (or not wholly) on the probe log; say so
            say('SPAWN_WARN check=escape-post detail="post escape-check record could NOT be appended to the probe log (helper exit %d) — the mandatory post-spawn escape record is MISSING or incomplete for this activation; composer disposition"' % post_rc)
            if ec == 0:
                ec = 4
        elif post_rc == 3:
            say('SPAWN_WARN check=escape-post detail="post-capture failed (exit 3) — the helper\'s refusal record naming the root is on the probe log; composer disposition"')
            if ec == 0:
                ec = 4
        elif post_rc != 0:
            say('SPAWN_WARN check=escape-post detail="post escape-check REFUSED (exit %d) — NO probe-log record was written (diagnostic on stderr); the mandatory post-spawn escape record is MISSING for this activation; composer disposition"' % post_rc)
            if ec == 0:
                ec = 4
        self.post_ran = True
        try:
            os.remove(self.prestate)
        except OSError:
            pass
        # --- DR-1 emission 4: the exit census record, via the helper ---
        if census_ok:
            if self.helper_to_probe("emit", "OWNERSHIP:exit-census", "--run", run, "--role", role,
                                    "leg=%s" % leg, "children=%d" % children, *rl_kv) != (0, True):
                say('SPAWN_WARN check=exit-census detail="exit-census emission failed (children=%d unrecorded)"' % children)
            if children > 0:
                say('SPAWN_WARN check=exit-census detail="%d surviving process(es) in the child\'s pgid — composer disposition (never a wrapper kill)"' % children)
        else:
            detail = (setup_failed + "; survivor count unconfirmed") if setup_failed else "census command failed; survivor count unconfirmed"
            if self.helper_to_probe("emit", "OWNERSHIP:exit-census", "--run", run, "--role", role,
                                    "leg=%s" % leg, "refused=capture-failure", *(rl_kv + ["detail=" + detail])) != (0, True):
                say('SPAWN_WARN check=exit-census detail="census refusal record emission failed"')
            say('SPAWN_WARN check=exit-census-capture detail="process census FAILED (ps/pipeline) — survivor count unconfirmed; composer classification required"')
            if ec == 0:
                ec = 4
        # --- session-id enrichment: a bounded read of the role-log FILE post-wait —
        # v46.4 (D1): of the bytes added since this leg opened it (from the offset
        # recorded at the open), never the file's head, which is the role's first
        # leg's ---
        if self.identity_file and self.role_log_start is not None and os.path.isfile(self.role_log):
            session_id = ""
            try:
                with open(self.role_log, "rb") as fh:
                    fh.seek(self.role_log_start)
                    head = fh.read(262144)
                m = SESSION_RE.search(head)
                if m:
                    session_id = m.group(1).decode("utf-8", "surrogateescape")
            except OSError:
                session_id = ""
            if session_id:
                if not _has_control(session_id):
                    self.write_identity(session_id)
                else:
                    say('SPAWN_WARN check=session-id detail="child-reported session_id carries control bytes — enrichment SKIPPED (forged-identity-line lever; Constraint 13); input-derived identity retained"')
        # --- the pump fold-in (Constraint 10) ---
        if pump_status == 0:
            pass
        elif pump_status == "timeout":
            say('SPAWN_WARN check=role-pump detail="role-log pump did not drain within the bound (an orphan may hold the FIFO writer) — killed the wrapper\'s OWN pump; capture unconfirmed"')
            if ec == 0:
                ec = 4
        else:
            say('SPAWN_WARN check=role-pump detail="role-log pump exited %s — capture may be incomplete"' % pump_status)
            if ec == 0:
                ec = 4
        say('STICKY_REREAD run=%s role=%s detail="rehydrate: re-read STICKY.md + the plan\'s Current State / Handoff Note (Loop config: included) before consuming this spawn\'s result"' % (run, role))
        if self.pending_code is not None:
            return self.pending_code
        return ec

    def route_block(self):
        env = self.env
        rt = self.rt
        if hasattr(signal, "SIGCHLD"):
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)   # the ownership rule's prerequisite (PR-MED-041)
        route_roots = [rt.canon_path(p) for p in self.route_roots]
        if not hasattr(os, "waitid"):
            # round 38 PR-MED-038: no router is started without the non-reaping observation
            word, sticky, ans, kept_out, kept_err, local = "other", False, "", b"", b"no-waitid\n", ""
        else:
            route_argv = [self.route_bin, "pick", "--agent=claude", "--run=%s" % env["LOOP_ISO"]]
            if env.get("LOOP_ROLE"):
                route_argv.append("--role=%s" % env["LOOP_ROLE"])
            if env.get("LOOP_PHASE"):
                route_argv.append("--phase=%s" % env["LOOP_PHASE"])
            if env.get("LOOP_MODEL"):
                route_argv.append("--model=%s" % env["LOOP_MODEL"])
            route_argv += ["--pid=%d" % os.getpid(), "--label=%s" % os.path.basename(self.repo_root), "--json"]
            word, sticky, ans, kept_out, kept_err, local = rt.route_collect(route_argv, cancel=self.cancel)
        if word not in rt.ROUTE_VERDICT_WORDS:
            word = "other"
        skipped = ""
        answer = ""   # the router's answer once it has passed the folder checks
        if word == "ok":
            dir_word, check = rt.route_dir_word(ans, route_roots)
            if dir_word:
                word = dir_word
                skipped = "%s %s" % (rt.route_skipped_text(b"", ans), check)
            else:
                answer = ans
        else:
            skipped = rt.route_skipped_text(kept_err, local)
        env.pop("LOOP_ROUTE_BIN", None)
        # v47.0 D10: on a resume the HOLDER decides — the answer is honoured exactly
        # when it is the folder holding the newest transcript (whatever its sticky
        # flag); an answer that is not the holder is `resume-mismatch`, and the
        # role runs on the holder. The search runs whatever the router said: with
        # no answer the candidates are the given profile folder and the ambient one.
        pin_refusal = None
        if self.resume:
            try:
                self.pin_resolve(answer, lambda folder: rt.route_dir_word(folder, route_roots))
            except _Refuse as r:
                pin_refusal = r
            else:
                if answer and self.pin["holder"] != answer:
                    word = "resume-mismatch"
                    skipped = "%s resume-mismatch" % rt.route_skipped_text(b"", answer)
                    answer = ""
        if answer and pin_refusal is None:
            self.route_dir = answer
            self.route_via = "binding" if sticky else "pick"
            say('SPAWN_ROUTE dir="%s" via=%s' % (self.route_dir, self.route_via))
        elif word != "ok":
            # (an answer that passed its checks beside a refused pin prints no router
            # line: the role is not started, so neither line would be true)
            say('SPAWN_WARN check=router detail="%s"' % word)
            if skipped:
                say('SPAWN_WARN check=route-skipped detail="%s"' % skipped)
        if pin_refusal is not None:
            raise pin_refusal

    def write_identity(self, session):
        env = self.env
        lines = ["ts=%s" % now_iso(), "run=%s" % env["LOOP_RUNKEY"], "role=%s" % env["LOOP_ROLE"], "leg=%s" % env["LOOP_LEG"],
                 "wrapper_pid=%d" % os.getpid(), "claude_pid=%d" % (self.child_pid or 0), "cwd=%s" % self.cwd,
                 "model=%s" % env["LOOP_MODEL"]]
        # v47.0 D10: on EVERY spawn — the folder the role runs on, the ambient folder
        # when nothing else was selected (left out only when that name holds a control
        # byte: one line cannot carry it — Constraint 13 — or when the ambient folder
        # cannot be established: round 16 PR-MED-022)
        if self.identity_dir and not _has_control(self.identity_dir):
            lines.append("profile_dir=%s" % self.identity_dir)
        if self.route_enabled:
            lines.append("route_run=%s" % env["LOOP_ISO"])
            lines.append("route_phase=%s" % env["LOOP_PHASE"])
        if self.token_env_name:
            lines.append("token_env=%s" % self.token_env_name)
        if env.get("LOOP_RESUME_SESSION"):
            lines.append("resume=%s" % env["LOOP_RESUME_SESSION"])
        if session:
            lines.append("session=%s" % session)
        tmp = "%s.tmp.%d" % (self.identity_file, os.getpid())
        try:
            with open(tmp, "wb") as fh:
                fh.write(("".join(l + "\n" for l in lines)).encode("utf-8", "surrogateescape"))
            last = None
            for _ in range(IDENTITY_REPLACE_TRIES):
                try:
                    os.replace(tmp, self.identity_file)
                    last = None
                    break
                except PermissionError as e:
                    last = e   # Windows: the destination held open by a reader — bounded retry
                    time.sleep(0.2)
            if last is not None:
                raise last
        except OSError:
            try:
                os.remove(tmp)
            except OSError:
                pass
            say('SPAWN_WARN check=identity-write detail="identity record not written to %s"' % self.identity_file)

    # -- v48.0 D23: the wrapper writes the end of its own leg -----------------------
    def handoff_seen(self):
        """Does the LAST result event of THIS leg's stream end in the handoff
        line? Read from the role log's bytes since this leg opened it (at most
        the last END_READ_BYTES of them): the last line that parses as a JSON
        object with `"type": "result"` decides — its `result` text, trailing
        blanks dropped, must have a last line starting `ROLE: handoff `. No
        such event, an unreadable log, or a result that is not text: False."""
        if self.role_log_start is None:
            return False
        try:
            start = max(self.role_log_start, os.path.getsize(self.role_log) - END_READ_BYTES)
            with open(self.role_log, "rb") as fh:
                fh.seek(start)
                data = fh.read(END_READ_BYTES)
        except OSError:
            return False
        for line in reversed(data.split(b"\n")):
            if b'"result"' not in line or b'"type"' not in line:
                continue
            try:
                obj = json.loads(line.decode("utf-8", "replace"))
            except ValueError:
                continue
            if isinstance(obj, dict) and obj.get("type") == "result":
                text = obj.get("result")
                if not isinstance(text, str):
                    return False
                return text.rstrip().rsplit("\n", 1)[-1].strip().startswith("ROLE: handoff ")
        return False

    def write_role_end(self, ec):
        """Whenever this wrapper wrote the leg's `ROLE: start`, it writes the
        `ROLE: end` — through the helper, with `--log` so a second end for the
        leg is refused — before the `EXIT:` footer (which stays the log's last
        line) and before the helper snapshot is removed, on a normal exit and
        on a signalled one. `result=` is MECHANICAL: `exit <the footer's
        code>; handoff` when that code is 0 and the last result event of the
        stream ends in the handoff line, else `incomplete: exit <code>;
        handoff|no handoff` — the word the same-round retry rule reads. The
        composer's judgment is its `CONSUME:` record. A helper refusal here is
        reported on stdout and never changes the exit code."""
        if not self.role_started:
            return
        env = self.env
        handoff = self.handoff_seen()
        result = "exit %d; %s" % (ec, "handoff" if handoff else "no handoff")
        if ec != 0 or not handoff:
            result = "incomplete: " + result
        duration = int(time.monotonic() - self.role_start_time) if self.role_start_time is not None else 0
        try:
            rc = subprocess.run(self.helper_argv("emit", "ROLE:end", "--run", env["LOOP_RUNKEY"], "--role", env["LOOP_ROLE"],
                                                 "--log", self.probe_log, "result=%s" % result, "leg=%s" % env["LOOP_LEG"],
                                                 "duration=%d" % duration),
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL).returncode
        except OSError:
            rc = 127
        if rc != 0:
            say('SPAWN_WARN check=role-end detail="this leg\'s ROLE: end was NOT written (helper exit %d; its reason is on stderr) — the leg has a start and no end, and the exit code is unchanged; composer disposition"' % rc)

    # -- the footer and the teardown (every exit path once the START exists) -----
    def footer_and_teardown(self, ec):
        self.write_role_end(ec)
        try:
            write_all(self.probe_fd, ("EXIT:%d\n" % ec).encode("ascii"))
        except (OSError, TypeError):
            pass
        if self.pre_created and not self.post_ran and self.prestate:
            try:
                os.remove(self.prestate)
            except OSError:
                pass
        if self.group is not None and self.rt is not None:
            try:
                self.rt.group_close(self.group)
            except Exception:
                pass
        self.rm_tmpd()

    def rm_tmpd(self):
        if self.tmpd:
            shutil.rmtree(self.tmpd, ignore_errors=True)
            self.tmpd = None
        if self.snapd:   # round 43 PR-MED-001: the snapshot workspace goes with it, on every path
            # round 49 (PC1 leg (d), run 5): a BOUNDED retry. On Windows a member of the
            # group closed just above can hold the prompt snapshot it inherited for a
            # moment after the kill, and a file that is open cannot be removed there —
            # ONE rmtree with its errors ignored then left the directory, and the
            # prompt's bytes, under the git directory for good, silently. The step is
            # the identity write's (0.2 s); a holder OUTSIDE the group still outlives
            # the bound (the Job residual the orchestration doc names). On POSIX the
            # first pass removes it and the loop ends at once.
            for _attempt in range(_SNAP_RM_TRIES):
                shutil.rmtree(self.snapd, ignore_errors=True)
                if not os.path.lexists(self.snapd):
                    break
                time.sleep(0.2)
            self.snapd = None


_SNAP_RM_TRIES = 15   # round 49: the snapshot workspace's removal bound — 15 passes, 0.2 s apart (about 3 s)


def ensure_std_fds():
    """round 32 PR-MED-001: a closed fd 0 / 1 / 2 would be handed to the next
    file this wrapper opens — the role log, the probe log or the spawn lock —
    and the pump's mirror (`emit` → fd 1) and the status lines (`say` / `err`)
    would then land in that evidence file (v44.0 kept its evidence on fixed fds
    7 / 8 / 9). Point any closed standard descriptor at the null device before
    anything else is opened; an open-but-broken one keeps its EPIPE handling."""
    for fd in (0, 1, 2):
        try:
            os.fstat(fd)
        except OSError:
            try:
                os.open(os.devnull, os.O_RDWR)   # the lowest free descriptor IS the closed one
            except OSError:
                pass


def main():
    ensure_std_fds()
    _configure_std_streams()
    if len(sys.argv) > 1:
        err('SPAWN_REFUSED check=params detail="the wrapper takes no argument — every parameter is a LOOP_* environment variable"')
        return 2
    return Wrapper().run()


if __name__ == "__main__":
    sys.exit(main())
