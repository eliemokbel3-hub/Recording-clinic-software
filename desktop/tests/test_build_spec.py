"""Installation plan Task 3.2: ``packaging/scribe.spec``, read as source.

The spec runs only under PyInstaller (it calls ``Analysis``/``EXE``/
``COLLECT``, which PyInstaller provides), so it is pinned here through its
syntax tree: two windowed programs in one COLLECT, no UPX, no windowed
traceback box (Phase 2 round 13 MED-003), the version resource, the module
search path, the network exclusions and the Qt-network filter — the last
executed from the spec's own source and checked equal to the build audit's
rule. Whether the spec BUILDS is the integration gate: the practitioner's
PyInstaller run and ``build-release.py --audit`` (Task 3.5)."""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import ModuleType
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
PACKAGING = REPO / "packaging"
SPEC = PACKAGING / "scribe.spec"
SRC = REPO / "desktop" / "src"


def _tree() -> ast.Module:
    return ast.parse(SPEC.read_text(encoding="utf-8"))


def _calls(name: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name
    ]


def _kwargs(call: ast.Call) -> dict[str, ast.expr]:
    return {kw.arg: kw.value for kw in call.keywords if kw.arg is not None}


def _constant(node: ast.expr) -> Any:
    return ast.literal_eval(node)


def _assigned(name: str) -> ast.expr:
    for node in _tree().body:
        if isinstance(node, ast.Assign) and [
            t.id for t in node.targets if isinstance(t, ast.Name)
        ] == [name]:
            return node.value
    raise AssertionError(f"{name} is not assigned at the spec's top level")


def _load_release() -> ModuleType:
    path = REPO / "scripts" / "build-release.py"
    spec = importlib.util.spec_from_file_location("build_release_for_spec", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves a string annotation through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _spec_function(name: str) -> Any:
    """One top-level function of the spec, executed on its own."""
    for node in _tree().body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            namespace: dict[str, Any] = {}
            exec(compile(ast.Module([node], []), str(SPEC), "exec"), namespace)  # noqa: S102
            return namespace[name]
    raise AssertionError(f"{name} is not defined in the spec")


class TestTheTwoPrograms:
    def test_two_windowed_exes_in_one_collect(self) -> None:
        exes = _calls("EXE")
        assert sorted(_constant(_kwargs(e)["name"]) for e in exes) == ["scribe-app", "scribe-host"]
        for exe in exes:
            kwargs = _kwargs(exe)
            assert _constant(kwargs["console"]) is False
            assert _constant(kwargs["upx"]) is False
            assert _constant(kwargs["exclude_binaries"]) is True
            # Round 13 MED-003 (C3): never PyInstaller's traceback box.
            assert _constant(kwargs["disable_windowed_traceback"]) is True
            assert "version" in kwargs  # D12's version resource
        [collect] = _calls("COLLECT")
        assert _constant(_kwargs(collect)["upx"]) is False
        assert _constant(_kwargs(collect)["name"]) == _load_release().COLLECT_NAME
        names = {a.id for a in collect.args if isinstance(a, ast.Name)}
        assert {"app_exe", "host_exe"} <= names

    def test_each_entry_runs_the_real_main(self) -> None:
        [app, host] = sorted(_calls("Analysis"), key=lambda c: ast.unparse(c.args[0]))
        assert "entry_app.py" in ast.unparse(app.args[0])
        assert "entry_host.py" in ast.unparse(host.args[0])
        app_entry = (PACKAGING / "entry_app.py").read_text(encoding="utf-8")
        host_entry = (PACKAGING / "entry_host.py").read_text(encoding="utf-8")
        assert "from scribe_desktop.app import main" in app_entry
        assert "from scribe_desktop.native_host import main" in host_entry
        assert "sys.exit(main())" in app_entry and "sys.exit(main())" in host_entry

    def test_the_version_comes_from_pyproject(self) -> None:
        """D12, on the semantic surface (round 22): ``VERSION`` is read from
        pyproject's ``[project] version``, every program's resource is built
        by ``_version_info``, and that function — executed with recording
        stand-ins for PyInstaller's classes — puts ``VERSION`` and nothing
        else in every version field."""
        expected = ast.parse(
            'tomllib.loads((REPO / "desktop" / "pyproject.toml")'
            '.read_text(encoding="utf-8"))["project"]["version"]'
        ).body[0]
        assert isinstance(expected, ast.Expr)
        assert ast.unparse(_assigned("VERSION")) == ast.unparse(expected.value)
        for exe in _calls("EXE"):
            call = _kwargs(exe)["version"]
            assert isinstance(call, ast.Call) and ast.unparse(call.func) == "_version_info"
        [node] = [
            n for n in _tree().body if isinstance(n, ast.FunctionDef) and n.name == "_version_info"
        ]
        namespace: dict[str, Any] = {
            "VERSION": "7.8.9",
            "StringStruct": lambda key, value: (key, value),
            "StringTable": lambda _lang, strings: strings,
            "StringFileInfo": lambda tables: tables,
            "VarStruct": lambda *args: args,
            "VarFileInfo": lambda structs: structs,
            "FixedFileInfo": lambda **fields: fields,
            "VSVersionInfo": lambda **fields: fields,
        }
        exec(compile(ast.Module([node], []), str(SPEC), "exec"), namespace)  # noqa: S102
        info = namespace["_version_info"]("Clinic Scribe", "scribe-app.exe")
        assert info["ffi"] == {"filevers": (7, 8, 9, 0), "prodvers": (7, 8, 9, 0)}
        [[strings], _var] = info["kids"]
        fields = dict(strings)
        assert fields["FileVersion"] == fields["ProductVersion"] == "7.8.9"


class TestTheBundleScope:
    def test_the_module_search_path_is_the_app_source_only(self) -> None:
        # Task 0.1: the spike's search path had the repository root first.
        assert ast.unparse(_assigned("PATHEX")) == "[str(SRC)]"
        assert ast.unparse(_assigned("SRC")) == "REPO / 'desktop' / 'src'"
        for analysis in _calls("Analysis"):
            assert ast.unparse(_kwargs(analysis)["pathex"]) == "PATHEX"
            assert ast.unparse(_kwargs(analysis)["excludes"]) == "EXCLUDES"

    def test_network_qt_modules_are_excluded(self) -> None:
        excludes = _constant(_assigned("EXCLUDES"))
        for module in (
            "PySide6.QtNetwork",
            "PySide6.QtWebSockets",
            "PySide6.QtWebEngineCore",
            "PySide6.QtWebEngineWidgets",
        ):
            assert module in excludes

    def test_no_excluded_module_is_imported_by_the_app(self) -> None:
        """An excluded module the app imports would break the frozen app:
        none of the trimmed names is imported anywhere in ``scribe_desktop``
        (a source scan, as a guard; the practitioner's build and Task 0.1's
        checks are the proof)."""
        excludes = set(_constant(_assigned("EXCLUDES")))
        offenders = []
        for path in sorted((SRC / "scribe_desktop").rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module, *(f"{node.module}.{a.name}" for a in node.names)]
                for name in names:
                    if any(name == e or name.startswith(e + ".") for e in excludes):
                        offenders.append(f"{path.name}: {name}")
        assert offenders == []

    def test_task_0_1s_hidden_imports_are_kept(self) -> None:
        source = ast.unparse(_assigned("HIDDENIMPORTS"))
        for name in ("keyring.backends.Windows", "win32com.client", "win32timezone"):
            assert repr(name) in source
        assert "APP_MODULES" in source  # native_host and speaker_eval among them
        app_modules = ast.unparse(_assigned("APP_MODULES"))
        assert "PACKAGE.rglob('*.py')" in app_modules

    def test_both_analyses_are_filtered(self) -> None:
        source = SPEC.read_text(encoding="utf-8")
        for analysis in ("app_a", "host_a"):
            for field in ("binaries", "datas"):
                assert f"{analysis}.{field} = _without_qt_network({analysis}.{field})" in source


_NAMES = [
    "PySide6/Qt6Network.dll",
    "PySide6/Qt6NetworkAuth.dll",
    "PySide6/Qt6QmlNetwork.dll",
    "PySide6/Qt6WebSockets.dll",
    "PySide6/QtNetwork.pyd",
    "PySide6/QtWebSockets.pyd",
    "PySide6/plugins/tls/qschannelbackend.dll",
    "PySide6/plugins/networkinformation/qnetworklistmanager.dll",
    "PySide6/Qt6Core.dll",
    "PySide6/Qt6Widgets.dll",
    "PySide6/plugins/platforms/qwindows.dll",
    "network_helper.dll",
    "llama_cpp/lib/llama.dll",
]


class TestTheQtNetworkRule:
    @pytest.mark.parametrize("name", _NAMES)
    def test_the_spec_and_the_audit_share_one_rule(self, name: str) -> None:
        spec_rule = _spec_function("is_qt_network_file")
        audit_rule = _load_release().is_qt_network_file
        windows = PureWindowsPath(*PurePosixPath(name).parts)
        assert spec_rule(PurePosixPath(name)) == audit_rule(PurePosixPath(name))
        assert spec_rule(windows) == audit_rule(windows)

    def test_the_rule_catches_every_qt_networking_file(self) -> None:
        rule = _load_release().is_qt_network_file
        caught = [n for n in _NAMES if rule(PurePosixPath(n))]
        assert caught == _NAMES[:8]

    def test_the_spec_rule_is_written_once(self) -> None:
        source = SPEC.read_text(encoding="utf-8")
        assert len(re.findall(r"^def is_qt_network_file\(", source, re.MULTILINE)) == 1
