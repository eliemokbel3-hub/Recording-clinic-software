"""The pytest plugin behind ``scripts/lint-held-out-set.py`` (validation-run6
plan D16, Task 0.17).

Only the runner loads it — its child's bootstrap registers this module and a
``RunnerGuard`` with ``pytest.main(plugins=...)`` — in a child pytest whose
own stdout and stderr go to a log file the composer never opens. The plugin is
the ONE channel back to the runner: a JSON-lines report file named by the
environment variable ``SCRIBE_LINT_REPORT``. Each line carries only

- ``collected`` with a count, once collection is done;
- ``test`` with a sanitised node id, an outcome and the ``problems`` entries
  that pass the closed grammar (read from the teardown report only, since
  pytest copies ``user_properties`` onto every phase);
- ``malformed`` with a node id, when a ``problems`` value is anything but a
  list or tuple of grammar entries;
- the fixed codes ``collection-error``, ``internal-error``,
  ``plugin-error`` and ``config-refused``;
- ``finished`` with the exit status.

A test whose setup passed but that sent no call report (``--setup-only``) is
an ``error``, never a pass (codex round 34 PR-MED-046).

The guard checks the configuration once pytest has parsed it and before
anything is configured or collected (a ``tryfirst`` ``pytest_cmdline_main``),
and refuses with ``config-refused`` and pytest's usage-error exit when this
module is not registered under its name (an ini file's ``-p no:`` blocked
it), when an ini key other than ``testpaths`` and ``markers`` is set — so no
``addopts``, ``-o`` override, ``log_file`` or ``python_files`` reaches the
run — when ``PYTEST_ADDOPTS`` or ``PYTEST_PLUGINS`` is set, or when any
option in ``REFUSED_OPTIONS`` is set (codex rounds 34-35, PR-MED-043, 048,
049). pytest registers the guard under its default name for an object, the
object's id, which no ``-p no:`` can name in advance. This module's
``pytest_configure`` refuses to start unless the guard has checked the run,
so a plugin loaded by hand (``-p lint_held_out_plugin``) never reports
(PR-MED-050).

A report's longrepr, captured sections, keywords, other user properties,
warnings and log records are never read. A node id's parameter part is kept
only when it is made of encounter ids and set names; anything else becomes the
item's collection index. Every hook catches its own exception and records
``plugin-error`` instead, so a fault here fails the run with a fixed code
rather than a traceback.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable, Mapping, Sequence
from types import ModuleType
from typing import Any, Final, TextIO

import pytest

REPORT_ENV: Final = "SCRIBE_LINT_REPORT"
_STREAM: Final = pytest.StashKey[TextIO]()

# The closed problem grammar. ``desktop/tests/test_validation_scripts.py``
# defines the same codes and pattern; ``test_lint_held_out_set.py`` pins the
# two equal, so a new code is added in both places together.
CODES: Final[frozenset[str]] = frozenset(
    {
        "load-error",
        "bad-id",
        "duplicate-id",
        "no-conditions",
        "slot-out-of-range",
        "no-material-fact",
        "fact-borders-edge",
        "uncertain-unrouted",
        "fact-unrouted",
        "trigger-spoken",
        "facts-out-of-bounds",
        "size-out-of-bounds",
        "next-patient-without-axis",
        "tail-disagrees",
        "missing-tail-row",
        "row-without-axis",
        "fact-in-tail-not-absent",
        "absent-fact-before-tail",
        "tail-out-of-range",
        "boundary-disagrees",
        "reference-mismatch",
        "render-mismatch",
    }
)
_STEM = r"(?:syn|hld|h2|h3)-\d{2}"
_SET_NAME = r"(?:heldout(?:-\d{1,2})?|scripts)"
SET_NAME_RE: Final = re.compile(_SET_NAME)
PROBLEM_RE: Final = re.compile(
    rf"(?:{_STEM}|{_SET_NAME}):(?:{'|'.join(sorted(map(re.escape, CODES)))})"
    r"(?::\d{1,4})?"
)

_TOKEN = rf"(?:{_STEM}|{_SET_NAME})"
_PARAM_RE: Final = re.compile(rf"{_TOKEN}(?:-{_TOKEN})*")
_BASE = r"[A-Za-z0-9_./-]+(?:::[A-Za-z0-9_]+)*"
_BASE_RE: Final = re.compile(_BASE)
SAFE_NODE_RE: Final = re.compile(rf"{_BASE}(?:\[(?:{_PARAM_RE.pattern}|#\d{{1,6}})\])?")
UNKNOWN_NODE: Final = "unknown-node"
# A test may send several call reports (pytest's ``subtests``); the worst wins.
_CALL_RANK: Final = {"passed": 0, "skipped": 1, "failed": 2}
OUTCOMES: Final[frozenset[str]] = frozenset({"passed", "failed", "skipped", "error"})
FIXED_CODES: Final[frozenset[str]] = frozenset(
    {"collection-error", "internal-error", "plugin-error", "config-refused"}
)
# ``config.option`` names whose value, when set, refuses the run (PR-MED-043,
# PR-MED-049). The runner's own command line sets none of them.
REFUSED_OPTIONS: Final = (
    "xmlpath",
    "log_file",
    "debug",
    "pastebin",
    "deselect",
    "keyword",
    "markexpr",
    "setuponly",
    "setupplan",
    "collectonly",
    "usepdb",
    "trace",
    "noconftest",
    "ignore",
    "ignore_glob",
    "override_ini",
)
# The only ini keys a run may set (``desktop/pyproject.toml`` sets these two);
# any other, ``addopts`` above all, refuses it (PR-MED-048, PR-MED-049).
ALLOWED_INI: Final[frozenset[str]] = frozenset({"testpaths", "markers"})
REFUSED_ENV: Final = ("PYTEST_ADDOPTS", "PYTEST_PLUGINS")


def safe_node_id(nodeid: str, index: int) -> str:
    """The node id the runner may print: the path and names as pytest built
    them, and a parameter part only when it is ids and set names."""
    base, bracket, rest = nodeid.partition("[")
    if not _BASE_RE.fullmatch(base):
        return f"node[#{index}]"
    if not bracket:
        return base
    if rest.endswith("]") and _PARAM_RE.fullmatch(rest[:-1]):
        return f"{base}[{rest[:-1]}]"
    return f"{base}[#{index}]"


def valid_problems(value: object) -> list[str] | None:
    """The entries of one ``problems`` value, or None when any part of it is
    outside the grammar (the runner then prints ``problems-malformed``)."""
    if type(value) not in (list, tuple):
        return None
    entries: Sequence[object] = value  # type: ignore[assignment]
    out: list[str] = []
    for entry in entries:
        if type(entry) is not str or not PROBLEM_RE.fullmatch(entry):
            return None
        out.append(entry)
    return out


def problems_of(user_properties: Iterable[object]) -> list[str] | None:
    """Every ``problems`` entry of one report; None when one is malformed.
    Properties under any other name are skipped unread."""
    found: list[str] = []
    for prop in user_properties:
        if type(prop) is not tuple or not prop:
            continue
        name = prop[0]
        if type(name) is not str or name != "problems":
            continue
        if len(prop) != 2:
            return None
        entries = valid_problems(prop[1])
        if entries is None:
            return None
        found.extend(entries)
    return found


class LintReporter:
    """Writes the report file. One instance per child run."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream
        self._safe: dict[str, str] = {}
        self._outcome: dict[str, str] = {}
        self._called: set[str] = set()

    def _emit(self, record: dict[str, Any]) -> None:
        self._stream.write(json.dumps(record, sort_keys=True) + "\n")
        self._stream.flush()

    def _fault(self) -> None:
        try:
            self._emit({"k": "plugin-error"})
        except Exception:  # the runner fails on a missing finish anyway
            pass

    def _node(self, nodeid: str) -> str:
        return self._safe.get(nodeid, UNKNOWN_NODE)

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        try:
            items = list(session.items)
            self._safe = {item.nodeid: safe_node_id(item.nodeid, i) for i, item in enumerate(items)}
            self._emit({"k": "collected", "n": len(items)})
        except Exception:
            self._fault()

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        try:
            if report.failed:
                self._emit({"k": "collection-error"})
        except Exception:
            self._fault()

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        try:
            self._logreport(report)
        except Exception:
            self._fault()

    def _logreport(self, report: pytest.TestReport) -> None:
        nodeid = report.nodeid
        if report.when == "setup":
            if report.failed:
                self._outcome[nodeid] = "error"
            elif report.skipped:
                self._outcome[nodeid] = "skipped"
            else:
                self._outcome[nodeid] = "passed"
            return
        if report.when == "call":
            self._called.add(nodeid)
            current = self._outcome.get(nodeid)
            if current in _CALL_RANK:
                new = "failed" if report.failed else "skipped" if report.skipped else "passed"
                self._outcome[nodeid] = max(current, new, key=_CALL_RANK.__getitem__)
            return
        # teardown: the one report per test that carries the final outcome
        outcome = self._outcome.pop(nodeid, "error")
        called = nodeid in self._called
        self._called.discard(nodeid)
        if outcome == "passed" and not called:  # a setup that ran no test
            outcome = "error"
        if report.failed and outcome != "failed":
            outcome = "error"
        node = self._node(nodeid)
        problems = problems_of(report.user_properties)
        if problems is None:
            self._emit({"k": "malformed", "node": node})
            problems = []
        self._emit({"k": "test", "node": node, "outcome": outcome, "problems": problems})

    def pytest_internalerror(self) -> None:
        try:
            self._emit({"k": "internal-error"})
        except Exception:
            self._fault()

    def pytest_sessionfinish(self, exitstatus: int | pytest.ExitCode) -> None:
        try:
            self._emit({"k": "finished", "exit": int(exitstatus)})
        except Exception:
            self._fault()


def refused_configuration(config: pytest.Config, environ: Mapping[str, str]) -> bool:
    """Whether the run sets anything the runner refuses: a pytest variable,
    an option of ``REFUSED_OPTIONS`` or an ini key outside ``ALLOWED_INI``
    (``-o`` overrides are merged into pytest's ini table)."""
    if any(environ.get(name) for name in REFUSED_ENV):
        return True
    if any(getattr(config.option, name, None) for name in REFUSED_OPTIONS):
        return True
    ini = getattr(config, "_inicfg", None)
    if not isinstance(ini, Mapping):  # pytest's own table changed: fail closed
        return True
    return not set(ini) <= ALLOWED_INI


class RunnerGuard:
    """Created and registered by the runner's child bootstrap only, beside
    this module; ``checked`` is set once the configuration has passed."""

    def __init__(self, plugin: ModuleType) -> None:
        self._plugin = plugin
        self.checked = False

    @pytest.hookimpl(tryfirst=True)
    def pytest_cmdline_main(self, config: pytest.Config) -> pytest.ExitCode | None:
        try:
            registered = config.pluginmanager.get_plugin(self._plugin.__name__) is self._plugin
            refused = not registered or refused_configuration(config, os.environ)
        except Exception:
            refused = True
        if not refused:
            self.checked = True
            return None
        try:
            path = os.environ.get(REPORT_ENV)
            if path:
                with open(path, "a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"k": "config-refused"}) + "\n")
        except Exception:  # the runner fails on a missing count anyway
            pass
        return pytest.ExitCode.USAGE_ERROR


# Set by the runner's child bootstrap to the guard it registered.
RUNNER_GUARD: RunnerGuard | None = None


def pytest_configure(config: pytest.Config) -> None:
    path = os.environ.get(REPORT_ENV)
    guard = RUNNER_GUARD
    if not path or guard is None or not guard.checked:
        raise pytest.UsageError("the lint plugin runs only under the lint runner")
    stream = open(path, "a", encoding="utf-8")  # closed at unconfigure
    config.stash[_STREAM] = stream
    config.pluginmanager.register(LintReporter(stream), "lint-held-out-reporter")


def pytest_unconfigure(config: pytest.Config) -> None:
    stream = config.stash.get(_STREAM, None)
    if stream is not None:
        stream.close()
