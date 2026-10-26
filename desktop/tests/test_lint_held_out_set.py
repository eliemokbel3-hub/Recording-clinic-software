"""The held-out lint runner and its plugin (validation-run6 plan D16, Task 0.17).

While a blind set is in the tree the suite runs only through
``scripts/lint-held-out-set.py``: a child pytest writes everything to a log
file, and the plugin ``scripts/lint_held_out_plugin.py`` hands back node ids,
outcomes and grammar-checked ``problems`` codes only. These tests pin that
boundary three ways:

- the plugin fed constructed reports that carry a sentinel word in every place
  a report can hold text — none of it reaches the report file;
- the runner end to end over a generated test module whose assertion,
  ``print``, ``warnings.warn``, ``logging``, parametrize ``ids=`` callback and
  appended helper result each carry the sentinel — absent from the console,
  present in the log;
- three abnormal runs (a collection error, a plugin fault, a killed child), a
  timeout and a refused configuration, each failing with a fixed code.

The conftest's guard that refuses a bare pytest while a blind set has a script
in the tree is pinned here too (security-review round 33).
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

import test_validation_scripts as lints
from conftest import (
    BLIND_RUN_REFUSAL,
    LINT_PLUGIN_NAME,
    LINT_REPORT_ENV,
    blind_run_refusal,
    lint_runner_active,
)
from fixtures.heldout_transcripts import HELD_OUT_SETS

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
RUNNER = SCRIPTS / "lint-held-out-set.py"
S = "zqxsentinelwordqz"


def _load(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


plugin = _load("lint_held_out_plugin", "lint_held_out_plugin.py")
runner = _load("lint_held_out_set_runner", "lint-held-out-set.py")


# ---------------------------------------------------------------------------
# The grammar is one grammar.
# ---------------------------------------------------------------------------


class TestGrammar:
    def test_the_plugin_ships_the_lints_codes_and_pattern(self) -> None:
        assert plugin.CODES == lints.PROBLEM_CODES
        assert plugin.PROBLEM_RE.pattern == lints.PROBLEM_RE.pattern

    @pytest.mark.parametrize(
        "entry",
        [
            "h3-01:fact-unrouted",
            "h3-01:fact-unrouted:9999",
            "heldout-3:size-out-of-bounds:30",
            "h4-01:fact-unrouted",
            "heldout-4:size-out-of-bounds:19",
        ],
    )
    def test_a_grammar_entry_is_valid(self, entry: str) -> None:
        assert plugin.valid_problems([entry]) == [entry]

    def test_no_fifth_set_id_is_in_the_grammar(self) -> None:
        # Validation-run7 Task 0.5: h4- joined the grammar; h5- is not in it.
        assert plugin.valid_problems(["h5-01:fact-unrouted"]) is None
        assert plugin.safe_node_id("tests/t.py::test_a[h5-01]", 3) == "tests/t.py::test_a[#3]"
        assert plugin.safe_node_id("tests/t.py::test_a[h4-01]", 3) == "tests/t.py::test_a[h4-01]"

    @pytest.mark.parametrize(
        "value",
        [
            "h3-01:fact-unrouted",
            ["h3-01:fact-unrouted:10000"],
            [f"h3-01:{S}"],
            [f"{S}:fact-unrouted"],
            ["h3-01:fact-unrouted", S],
            [1],
            None,
            {"h3-01:fact-unrouted"},
        ],
        ids=lambda v: type(v).__name__,
    )
    def test_anything_else_is_malformed(self, value: object) -> None:
        assert plugin.valid_problems(value) is None

    def test_a_str_subclass_is_malformed(self) -> None:
        class Sly(str):
            pass

        assert plugin.valid_problems([Sly("h3-01:fact-unrouted")]) is None

    @pytest.mark.parametrize(
        ("nodeid", "index", "safe"),
        [
            ("tests/t.py::T::test_a", 0, "tests/t.py::T::test_a"),
            ("tests/t.py::test_a[heldout-3]", 4, "tests/t.py::test_a[heldout-3]"),
            ("tests/t.py::test_a[h3-07]", 4, "tests/t.py::test_a[h3-07]"),
            ("tests/t.py::test_a[heldout-2-syn-01]", 4, "tests/t.py::test_a[heldout-2-syn-01]"),
            (f"tests/t.py::test_a[{S}]", 5, "tests/t.py::test_a[#5]"),
            ("tests/t.py::test_a[unnamed]", 6, "tests/t.py::test_a[#6]"),
            ("tests/t.py::test_a[path3]", 7, "tests/t.py::test_a[#7]"),
            (f"tests/{S} x.py::test_a", 8, "node[#8]"),
        ],
    )
    def test_a_node_id_keeps_only_ids_and_set_names(
        self, nodeid: str, index: int, safe: str
    ) -> None:
        assert plugin.safe_node_id(nodeid, index) == safe
        assert plugin.SAFE_NODE_RE.fullmatch(safe)


# ---------------------------------------------------------------------------
# The plugin, fed constructed reports.
# ---------------------------------------------------------------------------


def _report(
    nodeid: str,
    when: str,
    outcome: str,
    props: list[tuple[str, object]] | None = None,
    *,
    longrepr: str | None = None,
    sections: tuple[tuple[str, str], ...] = (),
) -> pytest.TestReport:
    return pytest.TestReport(
        nodeid=nodeid,
        location=(f"{S}.py", 0, S),
        keywords={S: 1},
        outcome=outcome,  # type: ignore[arg-type]
        longrepr=longrepr,
        when=when,  # type: ignore[arg-type]
        sections=sections,
        user_properties=props,
    )


def _phases(nodeid: str, outcome: str, props: list[tuple[str, object]]) -> list[pytest.TestReport]:
    noisy = (
        ("Captured stdout call", f"{S} printed {S}"),
        ("Captured log call", f"WARNING gen {S} logged {S}"),
        ("Captured stderr call", f"{S}"),
    )
    longrepr = f"{S} assert {S}" if outcome == "failed" else None
    return [
        _report(nodeid, "setup", "passed", props),
        _report(nodeid, "call", outcome, props, longrepr=longrepr, sections=noisy),
        _report(nodeid, "teardown", "passed", props, sections=noisy),
    ]


def _feed(nodeids: list[str], reports: list[pytest.TestReport]) -> tuple[str, list[Any]]:
    stream = io.StringIO()
    reporter = plugin.LintReporter(stream)
    reporter.pytest_collection_finish(
        SimpleNamespace(items=[SimpleNamespace(nodeid=n) for n in nodeids])
    )
    for report in reports:
        reporter.pytest_runtest_logreport(report)
    reporter.pytest_sessionfinish(1)
    text = stream.getvalue()
    return text, [json.loads(line) for line in text.splitlines()]


class TestPlugin:
    def test_no_report_text_reaches_the_report_file(self) -> None:
        failed = f"tests/t.py::test_a[{S}]"
        kept = "tests/t.py::test_b[heldout-3]"
        inside = "tests/t.py::test_c"
        mutated = "tests/t.py::test_d"
        not_a_list = "tests/t.py::test_e"
        helper_result = ["h3-02:no-conditions"]
        reports = [
            *_phases(
                failed,
                "failed",
                [("note", f"{S} other {S}"), ("problems", ["h3-01:fact-unrouted:2"])],
            ),
            *_phases(kept, "passed", [("problems", ("heldout-3:size-out-of-bounds:30",))]),
            *_phases(inside, "passed", [("problems", [f"h3-01:fact-unrouted {S}"])]),
        ]
        # A helper result changed after ``record_property`` stored it: the
        # teardown report holds the same list object, so the change shows.
        mutated_reports = _phases(mutated, "passed", [("problems", helper_result)])
        helper_result.append(f"{S} appended {S}")
        reports += mutated_reports
        reports += _phases(not_a_list, "failed", [("problems", "h3-01:bad-id")])
        text, records = _feed([failed, kept, inside, mutated, not_a_list], reports)

        assert S not in text
        assert records == [
            {"k": "collected", "n": 5},
            {
                "k": "test",
                "node": "tests/t.py::test_a[#0]",
                "outcome": "failed",
                "problems": ["h3-01:fact-unrouted:2"],
            },
            {
                "k": "test",
                "node": kept,
                "outcome": "passed",
                "problems": ["heldout-3:size-out-of-bounds:30"],
            },
            {"k": "malformed", "node": inside},
            {"k": "test", "node": inside, "outcome": "passed", "problems": []},
            {"k": "malformed", "node": mutated},
            {"k": "test", "node": mutated, "outcome": "passed", "problems": []},
            {"k": "malformed", "node": not_a_list},
            {"k": "test", "node": not_a_list, "outcome": "failed", "problems": []},
            {"k": "finished", "exit": 1},
        ]

    def test_setup_and_teardown_failures_are_errors(self) -> None:
        a, b = "t.py::test_a", "t.py::test_b"
        reports = [
            _report(a, "setup", "failed", longrepr=S),
            _report(a, "teardown", "passed"),
            _report(b, "setup", "passed"),
            _report(b, "call", "passed"),
            _report(b, "teardown", "failed", longrepr=S),
        ]
        text, records = _feed([a, b], reports)
        assert S not in text
        assert [(r["node"], r["outcome"]) for r in records if r["k"] == "test"] == [
            (a, "error"),
            (b, "error"),
        ]

    def test_a_setup_that_ran_no_test_is_an_error(self) -> None:
        """Codex round 34 PR-MED-046: ``--setup-only`` sends no call report;
        a passed setup alone is never a pass."""
        a, b = "t.py::test_a", "t.py::test_b"
        reports = [
            _report(a, "setup", "passed"),
            _report(a, "teardown", "passed"),
            _report(b, "setup", "skipped"),
            _report(b, "teardown", "passed"),
        ]
        _, records = _feed([a, b], reports)
        assert [(r["node"], r["outcome"]) for r in records if r["k"] == "test"] == [
            (a, "error"),
            (b, "skipped"),
        ]

    def test_a_refused_configuration_is_named(self) -> None:
        """Codex rounds 34-35 (PR-MED-043, 048, 049): every refused option, an
        ini key outside the allowed two, a pytest variable, or pytest's ini
        table missing refuses the configuration; the defaults do not."""

        def config(ini: object = None, **option: object) -> Any:
            table = {} if ini is None else ini
            return SimpleNamespace(option=SimpleNamespace(**option), _inicfg=table)

        allowed = {"testpaths": ["tests"], "markers": []}
        assert not plugin.refused_configuration(config(), {})
        assert not plugin.refused_configuration(
            config(allowed, keyword="", deselect=None, debug=None, noconftest=False),
            {"PYTEST_ADDOPTS": ""},
        )
        for name in plugin.REFUSED_OPTIONS:
            assert plugin.refused_configuration(config(**{name: "x"}), {}), name
        for key in ("addopts", "log_file", "python_files", "python_functions", "norecursedirs"):
            assert plugin.refused_configuration(config({**allowed, key: "x"}), {}), key
        for name in plugin.REFUSED_ENV:
            assert plugin.refused_configuration(config(), {name: "x"}), name
        assert plugin.refused_configuration(config([("testpaths", 1)]), {})
        assert plugin.refused_configuration(SimpleNamespace(option=SimpleNamespace()), {})

    def test_the_guard_checks_the_run_before_it_starts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Codex round 35 PR-MED-048: the plugin blocked under its name, or a
        refused configuration, is ``config-refused`` with pytest's usage-error
        exit; a run that passes is marked checked."""
        report = tmp_path / "r.report"
        monkeypatch.setenv(plugin.REPORT_ENV, str(report))
        for name in plugin.REFUSED_ENV:
            monkeypatch.delenv(name, raising=False)

        def config(registered: object, **option: object) -> Any:
            manager = SimpleNamespace(get_plugin=lambda name: registered)
            return SimpleNamespace(
                pluginmanager=manager, option=SimpleNamespace(**option), _inicfg={}
            )

        for registered, option in ((None, {}), (object(), {}), (plugin, {"xmlpath": "j.xml"})):
            guard = plugin.RunnerGuard(plugin)
            assert guard.pytest_cmdline_main(config(registered, **option)) == (
                pytest.ExitCode.USAGE_ERROR
            )
            assert not guard.checked
        assert report.read_text(encoding="utf-8") == '{"k": "config-refused"}\n' * 3
        guard = plugin.RunnerGuard(plugin)
        assert guard.pytest_cmdline_main(config(plugin)) is None
        assert guard.checked

    def test_the_plugin_starts_only_after_the_guard_checked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Codex round 35 PR-MED-050: loaded by hand, with the variable set,
        the plugin refuses before it opens the report."""
        report = tmp_path / "r.report"
        monkeypatch.setenv(plugin.REPORT_ENV, str(report))
        unchecked = plugin.RunnerGuard(plugin)
        for guard in (None, unchecked):
            monkeypatch.setattr(plugin, "RUNNER_GUARD", guard)
            with pytest.raises(pytest.UsageError):
                plugin.pytest_configure(SimpleNamespace())
        assert not report.exists()

    def test_the_worst_of_several_call_reports_wins(self) -> None:
        """Round 32 MED-002: pytest's ``subtests`` send one call report each;
        a skip followed by a failure is a failure."""
        a, b = "t.py::test_a", "t.py::test_b"
        reports = [
            _report(a, "setup", "passed"),
            _report(a, "call", "skipped"),
            _report(a, "call", "failed", longrepr=S),
            _report(a, "teardown", "passed"),
            _report(b, "setup", "passed"),
            _report(b, "call", "failed", longrepr=S),
            _report(b, "call", "passed"),
            _report(b, "teardown", "passed"),
        ]
        _, records = _feed([a, b], reports)
        assert [(r["node"], r["outcome"]) for r in records if r["k"] == "test"] == [
            (a, "failed"),
            (b, "failed"),
        ]

    def test_the_reporter_implements_no_hook_that_reads_text(self) -> None:
        hooks = {name for name in vars(plugin.LintReporter) if name.startswith("pytest_")}
        assert hooks == {
            "pytest_collection_finish",
            "pytest_collectreport",
            "pytest_runtest_logreport",
            "pytest_internalerror",
            "pytest_sessionfinish",
        }
        module_hooks = {name for name in vars(plugin) if name.startswith("pytest_")}
        assert module_hooks == {"pytest_configure", "pytest_unconfigure"}
        guard_hooks = {name for name in vars(plugin.RunnerGuard) if name.startswith("pytest_")}
        assert guard_hooks == {"pytest_cmdline_main"}

    def test_a_hook_fault_is_a_fixed_code(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom(_: object) -> None:
            raise RuntimeError(f"{S} fault {S}")

        monkeypatch.setattr(plugin, "problems_of", boom)
        text, records = _feed(["t.py::test_a"], _phases("t.py::test_a", "passed", []))
        assert S not in text
        assert {"k": "plugin-error"} in records
        assert not [r for r in records if r["k"] == "test"]

    def test_a_failed_collection_is_a_fixed_code(self) -> None:
        stream = io.StringIO()
        reporter = plugin.LintReporter(stream)
        reporter.pytest_collectreport(
            pytest.CollectReport(f"{S}.py", "failed", f"{S} error {S}", [], sections=[(S, S)])
        )
        assert stream.getvalue() == '{"k": "collection-error"}\n'


# ---------------------------------------------------------------------------
# The runner's own checks of the report file.
# ---------------------------------------------------------------------------


class TestBlindRunGuard:
    """Security-review round 33 SEC-001: a bare pytest refuses to start while
    a blind set has a script in the tree (``conftest.pytest_configure``)."""

    @staticmethod
    def _set(*, cases_written: bool, scripts: int) -> SimpleNamespace:
        paths = [Path(f"h3-{n:02d}.json") for n in range(1, scripts + 1)]
        return SimpleNamespace(cases_written=cases_written, script_paths=lambda: paths)

    def test_the_variable_and_name_are_the_plugins(self) -> None:
        assert LINT_REPORT_ENV == plugin.REPORT_ENV
        assert LINT_PLUGIN_NAME == plugin.__name__

    def test_a_blind_script_outside_the_runner_is_refused(self) -> None:
        """Codex round 34 PR-MED-045: a variable left set in a shell, with
        no plugin registered, is refused too."""
        sets = [self._set(cases_written=True, scripts=3), self._set(cases_written=False, scripts=1)]
        assert blind_run_refusal(sets, {}, False) == BLIND_RUN_REFUSAL
        assert blind_run_refusal(sets, {LINT_REPORT_ENV: ""}, True) == BLIND_RUN_REFUSAL
        assert blind_run_refusal(sets, {LINT_REPORT_ENV: "r.report"}, False) == BLIND_RUN_REFUSAL
        assert blind_run_refusal(sets, {}, True) == BLIND_RUN_REFUSAL

    @pytest.mark.parametrize(
        ("cases_written", "scripts", "environ", "plugin_active"),
        [
            (False, 1, {LINT_REPORT_ENV: "r.report"}, True),
            (False, 0, {}, False),
            (True, 5, {}, False),
        ],
    )
    def test_otherwise_the_run_goes_ahead(
        self, cases_written: bool, scripts: int, environ: dict[str, str], plugin_active: bool
    ) -> None:
        sets = [self._set(cases_written=cases_written, scripts=scripts)]
        assert blind_run_refusal(sets, environ, plugin_active) is None

    def test_the_runner_is_active_only_with_its_guard_checked(self) -> None:
        """Codex round 35 PR-MED-050: the plugin registered by hand has no
        checked guard registered beside it."""

        def manager(registered: object, *guards: object) -> Any:
            return SimpleNamespace(
                get_plugin=lambda name: registered if name == LINT_PLUGIN_NAME else None,
                is_registered=lambda obj: any(obj is g for g in guards),
            )

        checked = SimpleNamespace(checked=True)
        unchecked = SimpleNamespace(checked=False)
        assert not lint_runner_active(manager(None))
        assert not lint_runner_active(manager(SimpleNamespace()))
        assert not lint_runner_active(manager(SimpleNamespace(RUNNER_GUARD=None)))
        assert not lint_runner_active(manager(SimpleNamespace(RUNNER_GUARD=unchecked), unchecked))
        assert not lint_runner_active(manager(SimpleNamespace(RUNNER_GUARD=checked)))
        assert lint_runner_active(manager(SimpleNamespace(RUNNER_GUARD=checked), checked))

    def test_heldout_4_is_the_one_blind_set(self) -> None:
        # Validation-run6 plan Task P.4 (2026-10-25): heldout-3's cases were
        # written after run 6 (no set was blind until validation-run7 Task
        # 0.5 put heldout-4 in the table, its cases unwritten until its P.4);
        # another blind set is a pin change.
        assert [s.name for s in HELD_OUT_SETS if not s.cases_written] == ["heldout-4"]


class TestRunnerChecks:
    def test_a_record_off_the_shapes_is_never_printed(self) -> None:
        lines = [
            '{"k": "collected", "n": 1}',
            f"{S} not json",
            json.dumps({"k": "test", "node": f"t.py::{S}[", "outcome": "passed", "problems": []}),
            json.dumps({"k": "test", "node": "t.py::a", "outcome": "passed", "problems": [], S: 1}),
            json.dumps({"k": "test", "node": "t.py::a", "outcome": S, "problems": []}),
            json.dumps({"k": "test", "node": "t.py::a", "outcome": "passed", "problems": [S]}),
            json.dumps({"k": ["test"]}),
            json.dumps([S]),
            json.dumps({"k": "malformed", "node": S + "["}),
            json.dumps({"k": "test", "node": "t.py::a", "outcome": "passed", "problems": []}),
            '{"k": "finished", "exit": 0}',
        ]
        parsed = runner.parse_report(lines)
        out, code = runner.render(parsed, 0, killed=False, verbose=True)
        assert S not in "\n".join(out)
        assert out == [
            "passed t.py::a",
            "collected 1",
            "ran 1",
            "passed 1 failed 0 errored 0",
            "skipped 0",
            "FAIL report-malformed",
            "exit 9",
        ]
        assert code == 9

    def test_a_second_collected_or_finished_record_is_malformed(self) -> None:
        for twice in ('{"k": "collected", "n": 0}', '{"k": "finished", "exit": 0}'):
            records = ['{"k": "collected", "n": 0}', '{"k": "finished", "exit": 0}', twice]
            out, code = runner.render(runner.parse_report(records), 0, killed=False, verbose=False)
            assert "FAIL report-malformed" in out and code == 9

    @pytest.mark.parametrize(
        ("child_exit", "records", "expected"),
        [
            (0, ['{"k": "collected", "n": 1}', '{"k": "finished", "exit": 0}'], 9),
            (1, ['{"k": "collected", "n": 0}', '{"k": "finished", "exit": 1}'], 1),
            (3221225786, ['{"k": "collected", "n": 0}'], 9),
            (-15, [], 9),
        ],
    )
    def test_the_exit_code(self, child_exit: int, records: list[str], expected: int) -> None:
        _, code = runner.render(
            runner.parse_report(records), child_exit, killed=False, verbose=False
        )
        assert code == expected

    @pytest.mark.parametrize("outcome", ["failed", "error"])
    def test_a_failure_under_exit_zero_is_a_mismatch(self, outcome: str) -> None:
        """Codex round 34 PR-MED-047."""
        records = [
            '{"k": "collected", "n": 1}',
            json.dumps({"k": "test", "node": "t.py::a", "outcome": outcome, "problems": []}),
            '{"k": "finished", "exit": 0}',
        ]
        out, code = runner.render(runner.parse_report(records), 0, killed=False, verbose=False)
        assert "FAIL outcome-mismatch" in out
        assert (out[-1], code) == ("exit 9", 9)

    def test_an_interrupt_kills_the_child_and_removes_the_report(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Security-review round 33 SEC-002: an interrupt during the wait
        never leaves the child running or the report file behind."""
        children: list[Any] = []

        class Child:
            def __init__(self, *args: object, **kwargs: object) -> None:
                self.killed = False
                self.waits = 0
                children.append(self)

            def wait(self, timeout: float | None = None) -> int:
                self.waits += 1
                if self.waits == 1:
                    raise KeyboardInterrupt
                return 1

            def kill(self) -> None:
                self.killed = True

        monkeypatch.setattr(runner.subprocess, "Popen", Child)
        (tmp_path / "heldout-3").mkdir()
        logs = tmp_path / "logs"
        with pytest.raises(KeyboardInterrupt):
            runner.run([str(tmp_path / "heldout-3"), "--log-dir", str(logs)])
        assert [(child.killed, child.waits) for child in children] == [(True, 2)]
        assert [p.suffix for p in logs.iterdir()] == [".log"]

    def test_a_clean_run_exits_zero_and_prints_only_counts(self) -> None:
        records = [
            '{"k": "collected", "n": 1}',
            json.dumps({"k": "test", "node": "t.py::a", "outcome": "passed", "problems": []}),
            '{"k": "finished", "exit": 0}',
        ]
        out, code = runner.render(runner.parse_report(records), 0, killed=False, verbose=False)
        assert (out, code) == (
            ["collected 1", "ran 1", "passed 1 failed 0 errored 0", "skipped 0", "exit 0"],
            0,
        )


# ---------------------------------------------------------------------------
# The runner end to end.
# ---------------------------------------------------------------------------

_SINKS = ("assert", "print", "warn", "log", "ids", "appended")


def _marker(sink: str) -> str:
    return f"{S}-{sink}"


def _spread(sink: str) -> str:
    """The sink's marker at the start, middle and end of one message."""
    m = _marker(sink)
    return f"{m} start {m} middle {m}"


_GENERATED = textwrap.dedent(
    f'''
    import logging
    import warnings

    import pytest


    def _helper():
        return ["h3-01:fact-unrouted:1"]


    @pytest.mark.parametrize("v", [1, 2], ids=lambda v: "{_spread("ids")}" + str(v))
    def test_ids(v):
        assert v


    def test_problem_on_a_pass(record_property):
        record_property("problems", _helper())


    def test_every_sink_on_a_failure(record_property):
        record_property("problems", ["h3-02:no-conditions"])
        print("{_spread("print")}")
        warnings.warn("{_spread("warn")}")
        logging.getLogger("gen").warning("{_spread("log")}")
        assert "{_spread("assert")}" == "other"


    def test_mutated_after_record(record_property):
        problems = _helper()
        record_property("problems", problems)
        problems.append("{_spread("appended")}")
        print(problems)
    '''
)


def _run(
    tmp_path: Path,
    module: str,
    *,
    conftest: str | None = None,
    extra: tuple[str, ...] = (),
    set_name: str = "heldout-9",
    stand_in: str | None = None,
    ini: str = "",
) -> tuple[int, bytes, bytes]:
    """Run the runner from ``tmp_path`` with a relative ``--log-dir``;
    ``stand_in`` is written as a ``lint_held_out_plugin.py`` in the child's
    working folder, ``ini`` below the ``pytest.ini`` header."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "pytest.ini").write_text(f"[pytest]\n{ini}", encoding="utf-8")
    (project / "test_gen.py").write_text(module, encoding="utf-8")
    if conftest is not None:
        (project / "conftest.py").write_text(conftest, encoding="utf-8")
    if stand_in is not None:
        (project / "lint_held_out_plugin.py").write_text(stand_in, encoding="utf-8")
    set_folder = tmp_path / set_name
    set_folder.mkdir()
    logs = tmp_path / "logs"
    done = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            str(set_folder),
            "--root",
            str(project),
            "--tests",
            "test_gen.py",
            "--log-dir",
            "logs",
            *extra,
        ],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=300,
        check=False,
    )
    console = done.stdout + done.stderr
    found = sorted(logs.glob("*")) if logs.exists() else []
    log_bytes = b""
    if found:
        assert [p.name for p in found] == [p.name for p in found if p.suffix == ".log"]
        assert len(found) == 1
        assert re.fullmatch(rf"lint-{set_name}-\d{{8}}-\d{{6}}\.log", found[0].name)
        log_bytes = found[0].read_bytes()
    return done.returncode, console, log_bytes


def _lines(console: bytes) -> list[str]:
    return console.decode("ascii").splitlines()[1:]  # the first line names the log


class TestRunnerEndToEnd:
    def test_no_sink_reaches_the_console_and_every_one_reaches_the_log(
        self, tmp_path: Path
    ) -> None:
        code, console, log = _run(tmp_path, _GENERATED, extra=("--verbose",))
        assert S.encode() not in console
        for sink in _SINKS:
            assert _marker(sink).encode() in log, sink
        assert _lines(console) == [
            "passed test_gen.py::test_ids[#0]",
            "passed test_gen.py::test_ids[#1]",
            "passed test_gen.py::test_problem_on_a_pass",
            "problem h3-01:fact-unrouted:1",
            "failed test_gen.py::test_every_sink_on_a_failure",
            "problem h3-02:no-conditions",
            "passed test_gen.py::test_mutated_after_record",
            "collected 5",
            "ran 5",
            "passed 4 failed 1 errored 0",
            "skipped 0",
            "FAIL problems-malformed test_gen.py::test_mutated_after_record",
            "exit 1",
        ]
        assert code == 1

    def test_a_collection_error_fails_with_a_fixed_code(self, tmp_path: Path) -> None:
        module = f'raise RuntimeError("{_spread("collect")}")\n'
        code, console, log = _run(tmp_path, module)
        assert S.encode() not in console
        assert _marker("collect").encode() in log
        lines = _lines(console)
        assert "FAIL collection-error" in lines
        assert "FAIL nothing-ran" in lines
        assert lines[-1] == f"exit {code}"
        assert code != 0

    def test_a_plugin_fault_fails_with_a_fixed_code(self, tmp_path: Path) -> None:
        conftest = textwrap.dedent(
            f'''
            import lint_held_out_plugin


            def _boom(_):
                raise RuntimeError("{_spread("fault")}")


            lint_held_out_plugin.problems_of = _boom
            '''
        )
        module = "def test_one():\n    assert True\n"
        code, console, _ = _run(tmp_path, module, conftest=conftest)
        assert S.encode() not in console
        lines = _lines(console)
        assert "FAIL plugin-error" in lines
        assert "FAIL count-short" in lines
        assert lines[-1] == "exit 9"
        assert code == 9

    def test_a_killed_child_fails_with_a_fixed_code(self, tmp_path: Path) -> None:
        module = textwrap.dedent(
            f"""
            import os
            import signal


            def test_dies():
                print("{_spread("killed")}")
                os.kill(os.getpid(), signal.SIGTERM)
            """
        )
        code, console, _ = _run(tmp_path, module)
        assert S.encode() not in console
        lines = _lines(console)
        assert "FAIL not-finished" in lines
        assert "FAIL count-short" in lines
        assert code != 0

    def test_a_timeout_kills_the_child(self, tmp_path: Path) -> None:
        module = "import time\n\n\ndef test_sleeps():\n    time.sleep(120)\n"
        code, console, _ = _run(tmp_path, module, extra=("--timeout", "5"))
        lines = _lines(console)
        assert "FAIL child-killed" in lines
        assert "FAIL not-finished" in lines
        assert lines[-1] == "exit 9"
        assert code == 9

    def test_a_pytest_option_in_tests_is_refused(self, tmp_path: Path) -> None:
        """An argument file too (codex round 34 PR-MED-043): pytest expands
        ``@file`` into options."""
        for n, option in enumerate(("--tests=--junitxml=j.xml", "--tests=-x", "--tests=@a.txt")):
            folder = tmp_path / f"case-{n}"
            folder.mkdir()
            code, console, log = _run(folder, "def test_one():\n    pass\n", extra=(option,))
            assert console.decode("ascii").splitlines() == ["refused tests-option"]
            assert (code, log) == (2, b"")

    @pytest.mark.parametrize(
        ("ini", "written"),
        [
            ("addopts = --junitxml=j.xml\n", "j.xml"),
            ("log_file = l.txt\n", "l.txt"),
            ("addopts = --setup-only\n", None),
            ("addopts = -k one\n", None),
            ("addopts = -p no:lint_held_out_plugin --noconftest --junitxml=j.xml\n", "j.xml"),
            ("addopts = -o log_file=l.txt\n", "l.txt"),
            ("addopts = --ignore=test_gen.py\n", None),
            ("python_files = nothing_*.py\n", None),
        ],
    )
    def test_an_ini_option_the_runner_refuses_is_a_fixed_code(
        self, tmp_path: Path, ini: str, written: str | None
    ) -> None:
        """Codex rounds 34-35 (PR-MED-043, 048, 049): an ini file's
        reporter, selection or collection setting, or a ``-p no:`` of the
        plugin itself, is refused before collection, and no report file is
        written."""
        module = f'def test_one():\n    assert "{_spread("ini")}" == "x"\n'
        code, console, _ = _run(tmp_path, module, ini=ini)
        assert S.encode() not in console
        lines = _lines(console)
        assert "FAIL config-refused" in lines
        assert lines[-1] == f"exit {code}"
        assert code not in (0, 1)
        if written is not None:
            assert not (tmp_path / "project" / written).exists()

    def test_the_child_has_the_plugin_registered(self, tmp_path: Path) -> None:
        """What ``conftest``'s guard asks for (PR-MED-045, PR-MED-050): the
        plugin under its name, with the runner's guard registered and
        checked."""
        conftest = textwrap.dedent(
            f'''
            def pytest_configure(config):
                manager = config.pluginmanager
                guard = manager.get_plugin("{LINT_PLUGIN_NAME}").RUNNER_GUARD
                assert guard.checked is True and manager.is_registered(guard)
            '''
        )
        code, console, _ = _run(tmp_path, "def test_one():\n    pass\n", conftest=conftest)
        assert (_lines(console)[-1], code) == ("exit 0", 0)

    def test_the_plugin_loaded_by_hand_is_refused(self, tmp_path: Path) -> None:
        """Codex round 35 PR-MED-050: ``-p lint_held_out_plugin`` with the
        variable set never starts a run."""
        project = tmp_path / "project"
        project.mkdir()
        (project / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        module = f'def test_one():\n    print("{_spread("by-hand")}")\n'
        (project / "test_gen.py").write_text(module, encoding="utf-8")
        report = tmp_path / "r.report"
        env = {k: v for k, v in os.environ.items() if k not in plugin.REFUSED_ENV}
        env[plugin.REPORT_ENV] = str(report)
        env["PYTHONPATH"] = str(SCRIPTS)
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "lint_held_out_plugin"]
            + ["-p", "no:cacheprovider", "-s", "test_gen.py"],
            cwd=project,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=300,
            check=False,
        )
        assert done.returncode == int(pytest.ExitCode.USAGE_ERROR)
        assert S.encode() not in done.stdout + done.stderr
        assert not report.exists()

    def test_a_stand_in_plugin_in_the_working_folder_is_not_loaded(self, tmp_path: Path) -> None:
        stand_in = f'raise SystemExit("{_spread("stand-in")}")\n'
        code, console, log = _run(tmp_path, "def test_one():\n    pass\n", stand_in=stand_in)
        assert S.encode() not in console and S.encode() not in log
        assert _lines(console) == [
            "collected 1",
            "ran 1",
            "passed 1 failed 0 errored 0",
            "skipped 0",
            "exit 0",
        ]
        assert code == 0

    def test_a_set_folder_outside_the_grammar_is_refused(self, tmp_path: Path) -> None:
        code, console, log = _run(tmp_path, "def test_one():\n    pass\n", set_name=S)
        assert S.encode() not in console
        assert console.decode("ascii").splitlines() == ["refused set-name"]
        assert (code, log) == (2, b"")
