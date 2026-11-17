#!/usr/bin/env python3
"""loop-run-bounded.py — the composer's bounded runner for /execute-loop
(v46.0, plan .cursor/plans/plan-windows-updater-fixes.md, D5).

WHY ITS OWN SCRIPT: the runner runs whatever command follows its `--`. In
v45.0 and v45.1 it was a subcommand of the records helper
(`scripts/loop-journal.py run-bounded`), so a permission written for the
helper's records also pre-approved any command. Here it has its own name and
its own permission: `Bash(python3 scripts/loop-run-bounded.py:*)` is the
any-command grant — the composer's, never proposed for a spawned role — and no
argument to `scripts/loop-journal.py` names a command for it to run.

THE ROLE GUARD (v46.1, plan .cursor/plans/plan-runner-permission-offer.md,
D2): a permission line is not enough to keep the runner the composer's — a
line in the main checkout's local settings file can also be read by a
`claude -p` role in one of the repo's worktrees. So when LOOP_ROLE is set and
non-empty in the environment (the spawn wrapper requires it on every spawn and
passes its whole environment to the role), this script writes ONE stderr line

  REFUSE: loop-run-bounded is the composer's runner — LOOP_ROLE is set in this environment, which marks a spawned role's shell; nothing was run

and exits 2, before it loads the helper or reads an argument. An empty
LOOP_ROLE is unset; `--role` on the command line is not consulted. This is a
guard against ACCIDENTAL use, not a boundary: a role that clears the variable
in front of the command, or that runs an edited copy of this file, is not
stopped by it. The one full statement of its limits is the execute-loop
skill's, at Preflight step 15.

INVOCATION (the composer only — a shell without LOOP_ROLE; without -I, as the
helper subcommand was run):

  python3 scripts/loop-run-bounded.py [--run <runkey> --role <role>]
          --timeout <s> [--kill-after <s>] [--cwd </abs/dir>] -- <cmd> [args...]

WHAT IT DOES: nothing of its own. It loads the records helper found BESIDE
this file (`loop-journal.py`, by path, writing no bytecode), sets UTF-8 + LF
on the standard streams the way the helper's own entry point does, and calls
the helper's `cmd_run_bounded` with its arguments. The one implementation of
the runner stays in the helper; the grammar, the refusals (`REFUSE:`, exit
2, nothing run), the verbatim replay (stdout, then stderr) and the summary
line LAST on stderr

  run-bounded: exit=<n> elapsed=<s> timed_out=yes|no killed=yes|no

are the helper's. It writes no record.

EXIT CODES: 0 or the command's own; 124 timed out; 137 killed after the
grace; 125 the runner's own failure; 126 found but not executable; 127 not
found; 2 a refused argument, or the role guard's refusal (LOOP_ROLE set —
checked first, so it is 2 whatever the arguments are and even with no helper
beside this file). 125 is also this script's own failure: the sibling helper
is missing, cannot be loaded, or lacks a name this script calls (an install
where only one of the two files was updated) — ONE stderr line naming the
helper's path and the fault, nothing run.

TRUST: the helper file on disk is loaded as it is, with no snapshot-and-hash
check — the trust the composer gave it when it ran that same file directly.
"""
import importlib.util
import os
import sys
from pathlib import Path

HELPER_NAME = "loop-journal.py"
RUNTIME_NAMES = ("cmd_run_bounded", "_configure_std_streams")
ROLE_REFUSAL = ("REFUSE: loop-run-bounded is the composer's runner — LOOP_ROLE is set in this environment, "
                "which marks a spawned role's shell; nothing was run")


def _stderr_line(line):
    """Write one line to stderr as UTF-8 bytes with LF — the helper, whose
    stream setup the runner otherwise uses, is not loaded at either caller."""
    try:
        sys.stderr.flush()
        sys.stderr.buffer.write((line + "\n").encode("utf-8", "replace"))
        sys.stderr.buffer.flush()
    except (OSError, ValueError, AttributeError):
        pass


def _fail(helper_path, fault):
    """This script's own failure: one stderr line, exit 125."""
    _stderr_line("loop-run-bounded: %s: %s" % (helper_path, fault))
    sys.exit(125)


def load_helper(helper_path):
    """Load the records helper by path under a module name that is not
    `__main__`, with no bytecode written beside it (the load would otherwise
    create scripts/__pycache__/). Returns the module; any failure — a missing
    file, a file that does not import, a missing name — ends in _fail."""
    saved_dwb = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("loop_journal_runtime", helper_path)
        if spec is None or spec.loader is None:
            raise ImportError("no import spec")
        rt = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rt)
    except (Exception, SystemExit) as e:
        sys.dont_write_bytecode = saved_dwb
        _fail(helper_path, "the records helper could not be loaded (%s: %s)" % (type(e).__name__, " ".join(str(e).split())[:160]))
    sys.dont_write_bytecode = saved_dwb
    missing = [n for n in RUNTIME_NAMES if not callable(getattr(rt, n, None))]
    if missing:
        _fail(helper_path, "the records helper lacks %s — it is not the version this script was installed with" % ", ".join(missing))
    return rt


def main(argv):
    # the role guard (D2): first, so a role gets this line whatever follows
    # the script's name, and an install missing its helper still refuses
    if os.environ.get("LOOP_ROLE"):
        _stderr_line(ROLE_REFUSAL)
        return 2
    helper_path = str(Path(__file__).resolve().parent / HELPER_NAME)
    rt = load_helper(helper_path)
    # the load and the name check above are the only steps the 125 handler
    # covers: a fault inside the runner keeps the runner's own code
    rt._configure_std_streams()
    return rt.cmd_run_bounded(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
