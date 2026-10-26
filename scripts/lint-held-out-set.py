"""Run the test suite with a blind held-out set in the tree (validation-run6
plan D16, Task 0.17; Constraint C12).

Whenever a script of a blind set (``validation/heldout-4`` since validation-run7
plan Task 0.5; ``validation/heldout-3`` until its cases were written after run
6) is in the tree, the composer runs pytest ONLY through this runner:

    .venv\\Scripts\\python.exe scripts\\lint-held-out-set.py validation\\heldout-4

The set folder must exist (``refused set-missing`` otherwise).

It runs pytest in a child process whose stdout and stderr go, at the operating
system level, to ``.cursor/loops/held-out-lint/lint-<set>-<timestamp>.log``
(gitignored, in a folder of its own that the composer never opens or
searches). The child starts in a console of its own (no window) and loads
``lint_held_out_plugin`` from this file's folder by its full path, so a file
of that name elsewhere cannot stand in for it, and registers it with the
plugin's ``RunnerGuard``, which refuses any configuration the runner did not
set (``config-refused``); the plugin reports to this process through a
separate report file. The set folder only names the log:
the child lints every set in the fixture's table. This process re-checks every
record and prints only fixed lines:

- ``<outcome> <node id>`` for each test that did not pass, or that recorded
  ``problems`` (every test with ``--verbose``), then ``problem <entry>`` for
  each of its entries, each one ``<id>:<code>[:<int>]`` from the closed grammar;
- ``collected <n>``, ``ran <n>``, ``passed <n> failed <n> errored <n>``,
  ``skipped <n>``;
- ``FAIL <code>`` for a run that cannot be trusted: ``collection-error``,
  ``internal-error``, ``plugin-error``, ``config-refused``,
  ``problems-malformed <node id>``, ``report-malformed``, ``count-missing``,
  ``count-short``, ``count-over``, ``nothing-ran``, ``not-finished``,
  ``exit-mismatch``, ``outcome-mismatch`` (a failed or errored test with the
  child's exit 0), ``child-killed``, ``log-exists``, ``runner-error``;
- ``exit <code>``: 9 for a child killed at the timeout; otherwise the child's
  exit status when it is not 0, else 9 when a ``FAIL`` line was printed, else
  0. This process exits with the same code.

Nothing from a test's assertion text, captured output, warnings or log records
reaches this console; those are in the log. The child keeps pytest's own
terminal report, which therefore goes only into the log: the plan's
``-p no:terminal`` was dropped on 2026-10-24 because, without that report,
pytest writes a failure's text, captured output and warnings nowhere, and the
end-to-end test could not show them diverted into the log (``-v -rA`` make
the log a complete record: every node id, and passes' output too). ``-p
no:cacheprovider`` stays, so no node id or failure list is written to a cache
folder. A lint failure goes back to the
set's author as its code, never as a script edit by the composer.

Options: ``--tests PATH ...`` (default ``tests``; an entry starting with ``-``
or ``@`` is refused, so no pytest option or argument file can be passed
through — an ini file's ``addopts`` or other key is the guard's
``config-refused``),
``--root DIR`` (the
child's working folder, default ``desktop``), ``--log-dir DIR`` (default
``.cursor/loops/held-out-lint``), ``--timeout SECONDS`` (default 3600),
``--verbose``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Final

SCRIPTS: Final = Path(__file__).resolve().parent
REPO: Final = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import lint_held_out_plugin as plugin  # noqa: E402

RUNNER_FAILURE_EXIT: Final = 9
USAGE_EXIT: Final = 2
_MAX_RECORDS: Final = 200_000
# The child: load the plugin from its full path (argv[1]), register it with
# its guard, then run pytest.
_BOOTSTRAP: Final = (
    "import importlib.util, sys\n"
    "import pytest\n"
    "spec = importlib.util.spec_from_file_location('lint_held_out_plugin', sys.argv[1])\n"
    "module = importlib.util.module_from_spec(spec)\n"
    "sys.modules['lint_held_out_plugin'] = module\n"
    "spec.loader.exec_module(module)\n"
    "guard = module.RunnerGuard(module)\n"
    "module.RUNNER_GUARD = guard\n"
    "sys.exit(pytest.main(sys.argv[2:], plugins=[module, guard]))\n"
)
_NO_WINDOW: Final = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass
class Parsed:
    """The checked records of one report file."""

    collected: int | None = None
    finished: int | None = None
    tests: list[tuple[str, str, list[str]]] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def fail(self, code: str) -> None:
        if code not in self.failures:
            self.failures.append(code)


def _count(value: object) -> int | None:
    return value if type(value) is int and 0 <= value < 10**9 else None


def parse_report(lines: Iterable[str]) -> Parsed:
    """Check each record against the plugin's shapes; anything else is
    ``report-malformed`` and is never printed."""
    parsed = Parsed()
    for number, line in enumerate(lines):
        if number >= _MAX_RECORDS:
            parsed.fail("report-malformed")
            break
        try:
            record = json.loads(line)
        except ValueError:
            parsed.fail("report-malformed")
            continue
        if type(record) is not dict:
            parsed.fail("report-malformed")
            continue
        kind = record.get("k")
        if type(kind) is not str:
            parsed.fail("report-malformed")
            continue
        keys = set(record)
        if kind == "collected" and keys == {"k", "n"} and _count(record["n"]) is not None:
            if parsed.collected is not None:
                parsed.fail("report-malformed")
            parsed.collected = record["n"]
        elif kind == "finished" and keys == {"k", "exit"} and type(record["exit"]) is int:
            if parsed.finished is not None:
                parsed.fail("report-malformed")
            parsed.finished = record["exit"]
        elif kind in plugin.FIXED_CODES and keys == {"k"}:
            parsed.fail(kind)
        elif kind == "malformed" and keys == {"k", "node"} and _node_ok(record["node"]):
            parsed.fail(f"problems-malformed {record['node']}")
        elif (
            kind == "test"
            and keys == {"k", "node", "outcome", "problems"}
            and _node_ok(record["node"])
            and type(record["outcome"]) is str
            and record["outcome"] in plugin.OUTCOMES
            and plugin.valid_problems(record["problems"]) is not None
        ):
            parsed.tests.append((record["node"], record["outcome"], list(record["problems"])))
        else:
            parsed.fail("report-malformed")
    return parsed


def _node_ok(node: object) -> bool:
    return type(node) is str and (
        node == plugin.UNKNOWN_NODE or plugin.SAFE_NODE_RE.fullmatch(node) is not None
    )


def render(
    parsed: Parsed, child_exit: int, *, killed: bool, verbose: bool
) -> tuple[list[str], int]:
    """The console lines and this process's exit code."""
    out: list[str] = []
    totals = {outcome: 0 for outcome in plugin.OUTCOMES}
    for node, outcome, problems in parsed.tests:
        totals[outcome] += 1
        if verbose or outcome != "passed" or problems:
            out.append(f"{outcome} {node}")
            out.extend(f"problem {entry}" for entry in problems)
    failures = list(parsed.failures)
    if killed:
        failures.append("child-killed")
    ran = len(parsed.tests)
    if parsed.collected is None:
        failures.append("count-missing")
    elif ran < parsed.collected:
        failures.append("count-short")
    elif ran > parsed.collected:
        failures.append("count-over")
    if ran == 0:
        failures.append("nothing-ran")
    if parsed.finished is None:
        failures.append("not-finished")
    elif parsed.finished != child_exit:
        failures.append("exit-mismatch")
    if child_exit == 0 and (totals["failed"] or totals["error"]):
        failures.append("outcome-mismatch")
    out.append(f"collected {parsed.collected if parsed.collected is not None else '-'}")
    out.append(f"ran {ran}")
    out.append(f"passed {totals['passed']} failed {totals['failed']} errored {totals['error']}")
    out.append(f"skipped {totals['skipped']}")
    out.extend(f"FAIL {code}" for code in failures)
    if killed:
        code = RUNNER_FAILURE_EXIT
    elif child_exit != 0:
        code = child_exit if 0 < child_exit < 256 else RUNNER_FAILURE_EXIT
    else:
        code = RUNNER_FAILURE_EXIT if failures else 0
    out.append(f"exit {code}")
    return out, code


def _child_env(report: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in plugin.REFUSED_ENV}
    env[plugin.REPORT_ENV] = str(report)
    return env


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("set_folder")
    parser.add_argument("--tests", nargs="+", default=["tests"])
    parser.add_argument("--root", default=str(REPO / "desktop"))
    parser.add_argument("--log-dir", default=str(REPO / ".cursor" / "loops" / "held-out-lint"))
    parser.add_argument("--timeout", type=float, default=3600.0)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    set_folder = Path(args.set_folder)
    name = set_folder.resolve().name
    if not plugin.SET_NAME_RE.fullmatch(name):
        print("refused set-name")
        return USAGE_EXIT
    if not set_folder.is_dir():
        print("refused set-missing")
        return USAGE_EXIT
    if any(test.startswith(("-", "@")) for test in args.tests):
        print("refused tests-option")
        return USAGE_EXIT
    log_dir = Path(args.log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = log_dir / f"lint-{name}-{stamp}.log"
    report_path = log_dir / f"lint-{name}-{stamp}.report"
    try:
        log = open(log_path, "xb")  # noqa: SIM115 - closed below
        report_path.open("xb").close()
    except FileExistsError:
        print("FAIL log-exists")
        print(f"exit {RUNNER_FAILURE_EXIT}")
        return RUNNER_FAILURE_EXIT
    print(f"log {log_path.name}")
    command = [
        sys.executable,
        "-c",
        _BOOTSTRAP,
        str(SCRIPTS / "lint_held_out_plugin.py"),
        "-v",
        "-rA",
        "-p",
        "no:cacheprovider",
        *args.tests,
    ]
    killed = False
    try:
        with log:
            child = subprocess.Popen(
                command,
                cwd=args.root,
                env=_child_env(report_path),
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=_NO_WINDOW,
            )
            try:
                child_exit = child.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                child.kill()
                child_exit = child.wait()
                killed = True
            except BaseException:  # an interrupt: never leave the child running
                child.kill()
                child.wait()
                raise
        try:
            with report_path.open(encoding="utf-8", errors="strict") as handle:
                parsed = parse_report(handle)
        except (OSError, UnicodeDecodeError):
            parsed = Parsed()
            parsed.fail("report-malformed")
    finally:
        report_path.unlink(missing_ok=True)
    lines, code = render(parsed, child_exit, killed=killed, verbose=args.verbose)
    for line in lines:
        print(line)
    return code


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except SystemExit:
        raise
    except BaseException:  # a traceback could carry a test's text; print a code only
        print("FAIL runner-error")
        print(f"exit {RUNNER_FAILURE_EXIT}")
        return RUNNER_FAILURE_EXIT


if __name__ == "__main__":
    sys.exit(main())
