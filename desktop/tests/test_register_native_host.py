"""Privacy-professional-controls Task 4.2 (D10): ``scripts/register-native-
host.py`` writes the three per-user WER exclusions, verifies them by reading
them back, and ``--unregister`` removes exactly those three values.

The script is loaded through ``importlib`` (hyphenated, outside any package),
as ``test_setup_scripts.py`` loads its scripts. ``winreg`` is a FAKE in every
test (C6: the real registry is never touched — and on this machine an agent
shell's registry is virtualized anyway, so only the practitioner's own run
proves anything; P.3), and every file path points under ``tmp_path``."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from scribe_desktop import exclusions

REPO = Path(__file__).resolve().parents[2]


def _load_script() -> ModuleType:
    path = REPO / "scripts" / "register-native-host.py"
    spec = importlib.util.spec_from_file_location("register_native_host", path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script() -> ModuleType:
    return _load_script()


class _Handle:
    def __init__(self, registry: FakeWinreg, path: str) -> None:
        self.registry = registry
        self.path = path

    def __enter__(self) -> _Handle:
        return self

    def __exit__(self, *exc: object) -> None:
        pass


class FakeWinreg:
    """The slice of ``winreg`` the script uses, over a dict of keys. Every
    root a call names is recorded, so a test can prove nothing went to HKLM.
    ``drop`` names values a write silently loses (a virtualized write, as an
    agent shell sees it); ``rewrite`` stores a different value or type."""

    HKEY_CURRENT_USER = "HKCU"
    HKEY_LOCAL_MACHINE = "HKLM"
    REG_SZ = 1
    REG_DWORD = 4
    KEY_SET_VALUE = 0x0002

    def __init__(
        self,
        *,
        drop: tuple[str, ...] = (),
        rewrite: dict[str, tuple[object, int]] | None = None,
        unreadable: bool = False,
    ) -> None:
        self.keys: dict[str, dict[str, tuple[object, int]]] = {}
        self.roots: list[str] = []
        self.drop = set(drop)
        self.rewrite = dict(rewrite or {})
        self.unreadable = unreadable

    def CreateKey(self, root: str, path: str) -> _Handle:  # noqa: N802 - winreg's name
        self.roots.append(root)
        self.keys.setdefault(path, {})
        return _Handle(self, path)

    def OpenKey(  # noqa: N802
        self, root: str, path: str, reserved: int = 0, access: int = 0
    ) -> _Handle:
        self.roots.append(root)
        if path not in self.keys:
            raise FileNotFoundError(path)
        if self.unreadable and not access:
            raise PermissionError(path)
        return _Handle(self, path)

    def SetValueEx(  # noqa: N802
        self, key: _Handle, name: str, reserved: int, kind: int, value: object
    ) -> None:
        if name in self.drop:
            return
        self.keys[key.path][name] = self.rewrite.get(name, (value, kind))

    def QueryValueEx(self, key: _Handle, name: str) -> tuple[object, int]:  # noqa: N802
        values = self.keys[key.path]
        if name not in values:
            raise FileNotFoundError(name)
        return values[name]

    def DeleteValue(self, key: _Handle, name: str) -> None:  # noqa: N802
        values = self.keys[key.path]
        if name not in values:
            raise FileNotFoundError(name)
        del values[name]

    def DeleteKey(self, root: str, path: str) -> None:  # noqa: N802
        self.roots.append(root)
        if path not in self.keys:
            raise FileNotFoundError(path)
        del self.keys[path]


_KEY = exclusions.WER_EXCLUDED_KEY
_NAMES = exclusions.WER_EXCLUDED_APPLICATIONS


def test_the_script_uses_the_apps_own_names_and_key(script: ModuleType) -> None:
    assert script.WER_EXCLUDED_APPLICATIONS is exclusions.WER_EXCLUDED_APPLICATIONS
    assert script.WER_EXCLUDED_KEY is exclusions.WER_EXCLUDED_KEY


def test_register_wer_writes_three_dwords_and_reads_them_back(script: ModuleType) -> None:
    registry = FakeWinreg()
    assert script.register_wer(registry) == []
    assert registry.keys[_KEY] == {name: (1, FakeWinreg.REG_DWORD) for name in _NAMES}
    assert set(registry.roots) == {"HKCU"}  # per user only, never HKLM


@pytest.mark.parametrize(
    ("registry", "failed"),
    [
        (FakeWinreg(drop=("scribe-host.exe",)), ["scribe-host.exe"]),
        (FakeWinreg(rewrite={"pythonw.exe": (0, FakeWinreg.REG_DWORD)}), ["pythonw.exe"]),
        (FakeWinreg(rewrite={"scribe-app.exe": ("1", FakeWinreg.REG_SZ)}), ["scribe-app.exe"]),
        (FakeWinreg(unreadable=True), list(_NAMES)),
    ],
)
def test_a_value_that_does_not_read_back_as_dword_1_fails(
    script: ModuleType, registry: FakeWinreg, failed: list[str]
) -> None:
    assert script.register_wer(registry) == failed


def test_unregister_wer_removes_only_its_three_values(script: ModuleType) -> None:
    registry = FakeWinreg()
    registry.keys[_KEY] = {"other.exe": (1, FakeWinreg.REG_DWORD)}
    script.register_wer(registry)
    del registry.keys[_KEY]["scribe-app.exe"]  # one already gone
    assert script.unregister_wer(registry) == ["pythonw.exe", "scribe-host.exe"]
    assert registry.keys[_KEY] == {"other.exe": (1, FakeWinreg.REG_DWORD)}  # key kept
    assert script.unregister_wer(registry) == []
    assert set(registry.roots) == {"HKCU"}


def test_unregister_wer_with_no_key_does_nothing(script: ModuleType) -> None:
    registry = FakeWinreg()
    assert script.unregister_wer(registry) == []
    assert registry.keys == {}


def _install_under(
    script: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, registry: FakeWinreg
) -> None:
    """Every path the script writes points under ``tmp_path``; ``winreg`` is
    the fake (the script imports it inside ``register`` / ``unregister``)."""
    if " " in str(tmp_path):
        pytest.skip("the script refuses an install folder with a space (Chrome's rule)")
    venv = tmp_path / "venv"
    venv.mkdir()
    (venv / "scribe-host.exe").write_bytes(b"MZ")
    install = tmp_path / "install"
    monkeypatch.setattr(script, "INSTALL_DIR", install)
    monkeypatch.setattr(script, "MANIFEST_PATH", install / "host.json")
    monkeypatch.setattr(script, "INSTALLED_EXE", install / "scribe-host.exe")
    monkeypatch.setattr(script, "LEGACY_ARTIFACTS", ())
    monkeypatch.setattr(script, "venv_executable", lambda: venv / "scribe-host.exe")
    monkeypatch.setitem(sys.modules, "winreg", registry)


def test_register_verifies_the_host_and_the_exclusions(
    script: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = FakeWinreg()
    _install_under(script, tmp_path, monkeypatch, registry)
    assert script.register() == 0
    out = capsys.readouterr().out
    assert "verified : OK" in out
    assert "agent shell" in out
    assert registry.keys[_KEY] == {name: (1, FakeWinreg.REG_DWORD) for name in _NAMES}


def test_register_fails_loudly_when_an_exclusion_does_not_read_back(
    script: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = FakeWinreg(drop=("pythonw.exe",))
    _install_under(script, tmp_path, monkeypatch, registry)
    assert script.register() == 1
    captured = capsys.readouterr()
    assert "verified : FAIL" in captured.out
    assert "pythonw.exe" in captured.err


def test_unregister_removes_the_exclusions_too(
    script: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = FakeWinreg()
    _install_under(script, tmp_path, monkeypatch, registry)
    assert script.register() == 0
    capsys.readouterr()
    assert script.unregister() == 0
    out = capsys.readouterr().out
    for name in _NAMES:
        assert f"WER exclusion {name}" in out
    assert registry.keys[_KEY] == {}


def test_the_docs_say_an_agent_shell_proves_nothing(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """lessons.md: agent shells are MSIX-virtualized for %LOCALAPPDATA% AND
    HKCU — the module docs and ``--help`` both say a run there proves nothing."""
    doc: Any = script.__doc__
    assert "agent shell" in doc and "proves nothing" in doc
    monkeypatch.setattr(sys, "argv", ["register-native-host.py", "--help"])
    with pytest.raises(SystemExit):
        script.main()
    assert "agent shell proves nothing" in " ".join(capsys.readouterr().out.split())
