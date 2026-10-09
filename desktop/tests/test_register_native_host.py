"""Privacy-professional-controls Task 4.2 (D10): ``scripts/register-native-
host.py`` writes the five per-user WER exclusions (``python.exe`` since the
development-recordings hardening, round 45; ``audacity.exe`` since the
clinic-smoke plan's D11, from the registration-owned
``WER_REGISTERED_APPLICATIONS``), verifies them by reading them back, and
``--unregister`` removes exactly those five values.

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

from scribe_desktop import exclusions, identity, install_layout

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
_NAMES = exclusions.WER_REGISTERED_APPLICATIONS


def test_the_script_uses_the_registration_superset_and_the_apps_key(
    script: ModuleType,
) -> None:
    # Clinic-smoke plan D11 (Task 1.5): every operation — write, read-back,
    # the ``wer :`` line and --unregister — goes through the superset; the
    # app's own four-name list is not imported here at all.
    assert script.WER_REGISTERED_APPLICATIONS is exclusions.WER_REGISTERED_APPLICATIONS
    assert not hasattr(script, "WER_EXCLUDED_APPLICATIONS")
    assert script.WER_EXCLUDED_KEY is exclusions.WER_EXCLUDED_KEY


def test_register_wer_writes_five_dwords_and_reads_them_back(script: ModuleType) -> None:
    registry = FakeWinreg()
    assert script.register_wer(registry) == []
    assert registry.keys[_KEY] == {name: (1, FakeWinreg.REG_DWORD) for name in _NAMES}
    # Development-recordings hardening round 45 PR-HIGH-002: python.exe, for
    # the developer tools that read a recording (they refuse without it).
    assert registry.keys[_KEY]["python.exe"] == (1, FakeWinreg.REG_DWORD)
    # Clinic-smoke plan D11: audacity.exe, which opens an exported recording.
    assert registry.keys[_KEY]["audacity.exe"] == (1, FakeWinreg.REG_DWORD)
    assert set(registry.roots) == {"HKCU"}  # per user only, never HKLM


@pytest.mark.parametrize(
    ("registry", "failed"),
    [
        (FakeWinreg(drop=("scribe-host.exe",)), ["scribe-host.exe"]),
        (FakeWinreg(rewrite={"pythonw.exe": (0, FakeWinreg.REG_DWORD)}), ["pythonw.exe"]),
        (FakeWinreg(rewrite={"scribe-app.exe": ("1", FakeWinreg.REG_SZ)}), ["scribe-app.exe"]),
        # Round 46 PR-LOW-002: the fourth value is READ BACK, not only written.
        (FakeWinreg(drop=("python.exe",)), ["python.exe"]),
        (FakeWinreg(rewrite={"python.exe": ("1", FakeWinreg.REG_SZ)}), ["python.exe"]),
        # Clinic-smoke plan D11: the fifth value is read back too.
        (FakeWinreg(drop=("audacity.exe",)), ["audacity.exe"]),
        (FakeWinreg(unreadable=True), list(_NAMES)),
    ],
)
def test_a_value_that_does_not_read_back_as_dword_1_fails(
    script: ModuleType, registry: FakeWinreg, failed: list[str]
) -> None:
    assert script.register_wer(registry) == failed


def test_unregister_wer_removes_only_its_five_values(script: ModuleType) -> None:
    registry = FakeWinreg()
    registry.keys[_KEY] = {"other.exe": (1, FakeWinreg.REG_DWORD)}
    script.register_wer(registry)
    del registry.keys[_KEY]["scribe-app.exe"]  # one already gone
    assert script.unregister_wer(registry) == [
        "pythonw.exe",
        "python.exe",
        "scribe-host.exe",
        "audacity.exe",
    ]
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
        pytest.skip("the script refuses an install folder with a space (a conservative guard)")
    venv = tmp_path / "venv"
    venv.mkdir()
    (venv / "scribe-host.exe").write_bytes(b"MZ")
    install = tmp_path / "install"
    monkeypatch.setattr(script, "INSTALL_DIR", install)
    monkeypatch.setattr(script, "MANIFEST_PATH", install / "host.json")
    monkeypatch.setattr(script, "INSTALLED_EXE", install / "scribe-host.exe")
    monkeypatch.setattr(script, "LEGACY_ARTIFACTS", ())
    # Task 3.7: the stray production registration's files, under tmp_path
    # (the real ones are computed from the real LOCALAPPDATA at load).
    production = tmp_path / "production"
    monkeypatch.setattr(
        script,
        "STRAY_PRODUCTION_FILES",
        (production / "com.scribe.cliniko_host.json", production / "scribe-host.exe"),
    )
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
    # The ``wer :`` line names all five (clinic-smoke plan D11).
    assert f"-> {', '.join(_NAMES)}\n" in out


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


# --- Task 3.7: dev-only, the stray production link, WinError 32 ----------------------


def test_the_script_registers_the_dev_channel_whatever_the_pin(script: ModuleType) -> None:
    """The tests run pinned to production (conftest); the script still names
    the dev host, origin, key and data folder — outright, not by channel."""
    assert install_layout.channel() == "production"
    assert script.HOST_NAME == identity.DEV_HOST_NAME
    assert script.ALLOWED_ORIGIN == identity.expected_origin("dev")
    assert script.REGISTRY_KEY == identity.registry_key("dev")
    assert script.INSTALL_DIR.name == install_layout.DEV_FOLDER_NAME
    assert script.STRAY_PRODUCTION_KEY == identity.REGISTRY_KEY


def test_unregister_removes_a_stray_production_link_and_only_its_two_files(
    script: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = FakeWinreg()
    _install_under(script, tmp_path, monkeypatch, registry)
    registry.keys[identity.REGISTRY_KEY] = {"": (r"C:\old\host.json", FakeWinreg.REG_SZ)}
    production = tmp_path / "production"
    production.mkdir()
    for name in ("com.scribe.cliniko_host.json", "scribe-host.exe", "app.lock", "clinics.json"):
        (production / name).write_bytes(b"x")
    assert script.unregister() == 0
    assert identity.REGISTRY_KEY not in registry.keys
    assert sorted(p.name for p in production.iterdir()) == ["app.lock", "clinics.json"]
    assert set(registry.roots) == {"HKCU"}  # the installed HKLM link is never touched
    assert f"HKCU\\{identity.REGISTRY_KEY}" in capsys.readouterr().out


def _in_use_error(winerror: int = 32) -> PermissionError:
    error = PermissionError(13, "The process cannot access the file")
    # 32 ERROR_SHARING_VIOLATION (a held file); 5 ERROR_ACCESS_DENIED (a
    # running program's image being deleted).
    error.winerror = winerror  # type: ignore[attr-defined]
    return error


def test_register_says_close_chrome_when_the_host_is_held(
    script: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = FakeWinreg()
    _install_under(script, tmp_path, monkeypatch, registry)

    def held(*args: object, **kwargs: object) -> None:
        raise _in_use_error()

    monkeypatch.setattr(script.shutil, "copy2", held)
    assert script.register() == 1
    assert (
        "Close Clinic Scribe and Chrome completely, then run this again."
        in capsys.readouterr().err
    )
    assert registry.keys == {}  # nothing registered


@pytest.mark.parametrize("winerror", [32, 5], ids=["held-open", "running-image"])
def test_unregister_says_close_chrome_when_a_file_is_held(
    script: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    winerror: int,
) -> None:
    # Round 22: deleting the host exe Chrome is RUNNING is refused with
    # ERROR_ACCESS_DENIED (5), not the sharing violation (32) a copy meets.
    registry = FakeWinreg()
    _install_under(script, tmp_path, monkeypatch, registry)
    assert script.register() == 0
    capsys.readouterr()
    original = Path.unlink

    def unlink(self: Path, missing_ok: bool = False) -> None:
        if self.name == "scribe-host.exe":
            raise _in_use_error(winerror)
        original(self, missing_ok)

    monkeypatch.setattr(Path, "unlink", unlink)
    assert script.unregister() == 1
    out = capsys.readouterr()
    assert "Close Clinic Scribe and Chrome completely" in out.err
    assert out.out.startswith("removed  : ")  # what was already removed is said


def test_a_running_image_is_in_use_only_when_deleting(
    script: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A register COPY refused with ERROR_ACCESS_DENIED is a real permission
    problem, raised as before; only a delete reads it as the running host."""
    _install_under(script, tmp_path, monkeypatch, FakeWinreg())

    def denied(*args: object, **kwargs: object) -> None:
        raise _in_use_error(5)

    monkeypatch.setattr(script.shutil, "copy2", denied)
    with pytest.raises(PermissionError):
        script.register()


def test_another_os_error_is_not_mistaken_for_in_use(
    script: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_under(script, tmp_path, monkeypatch, FakeWinreg())

    def denied(*args: object, **kwargs: object) -> None:
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(script.shutil, "copy2", denied)
    with pytest.raises(PermissionError):
        script.register()


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
