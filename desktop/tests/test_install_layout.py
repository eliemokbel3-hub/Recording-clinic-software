"""Installation plan Phase 1: the channel and every root (Task 1.1), every
data-folder builder through ``install_layout`` (Task 1.2, with the source
scan), the remedy lines (Task 1.7) and the one version (Task 1.8).

Host state is never read (C6): ``sys.frozen`` (through the conftest's
``is_frozen`` pin, a source run unless ``use_frozen`` says otherwise),
``sys.executable`` and ``LOCALAPPDATA`` are injected per test; nothing here
touches a real data folder, model file or registry key."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType

import pytest

from conftest import REAL_CHANNEL, REAL_IS_FROZEN, use_channel, use_frozen
from scribe_desktop import (
    __version__,
    app,
    audit,
    benchmark,
    clinics,
    install_layout,
    logging_setup,
    note_config,
    past_sessions,
    practitioner_profile,
    session_store,
)
from scribe_desktop.install_layout import Channel, InstallLayoutError

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "desktop" / "src" / "scribe_desktop"


# --- Task 1.1: the channel ----------------------------------------------------------


class TestChannel:
    def test_is_frozen_reads_sys_frozen(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The real function, under the conftest pin (which replaces it).
        monkeypatch.setattr(install_layout, "is_frozen", REAL_IS_FROZEN)
        monkeypatch.delattr(sys, "frozen", raising=False)
        assert install_layout.is_frozen() is False
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        assert install_layout.is_frozen() is True

    def test_the_channel_is_production_exactly_when_frozen(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The real function, under the conftest pin (which replaces it).
        monkeypatch.setattr(install_layout, "channel", REAL_CHANNEL)
        use_frozen(monkeypatch, True)
        assert install_layout.channel() == "production"
        use_frozen(monkeypatch, False)
        assert install_layout.channel() == "dev"
        assert install_layout.channel_for(True) == "production"
        assert install_layout.channel_for(False) == "dev"

    def test_the_tests_run_pinned_to_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # D2: the conftest autouse fixture — so the pins test what ships —
        # in a source run that never reads the host's sys.frozen (C6, round
        # 11 PR-LOW-016).
        assert install_layout.channel() == "production"
        assert install_layout.folder_name() == "ClinikoScribe"
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        assert install_layout.is_frozen() is False
        assert install_layout.install_root() is None


# --- Task 1.1: the roots ---------------------------------------------------------------


class TestDataRoot:
    @pytest.mark.parametrize(
        ("which", "folder"), [("production", "ClinikoScribe"), ("dev", "ClinikoScribe-dev")]
    )
    def test_the_data_root_is_the_channels_folder(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: Channel, folder: str
    ) -> None:
        use_channel(monkeypatch, which)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert install_layout.data_root() == tmp_path / folder
        assert not (tmp_path / folder).exists()  # computing it creates nothing

    @pytest.mark.parametrize("which", ["production", "dev"])
    @pytest.mark.parametrize("value", [None, ""])
    def test_an_unset_or_empty_localappdata_falls_back_to_home(
        self, monkeypatch: pytest.MonkeyPatch, which: Channel, value: str | None
    ) -> None:
        use_channel(monkeypatch, which)
        if value is None:
            monkeypatch.delenv("LOCALAPPDATA", raising=False)
        else:
            monkeypatch.setenv("LOCALAPPDATA", value)
        assert install_layout.data_root() == Path.home() / install_layout.folder_name(which)

    @pytest.mark.parametrize("pin", ["production", "dev"])
    def test_a_named_channel_ignores_the_pin(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pin: Channel
    ) -> None:
        # Task 3.7: the dev-only registration script names its channel.
        use_channel(monkeypatch, pin)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert install_layout.data_root("dev") == tmp_path / "ClinikoScribe-dev"
        assert install_layout.data_root("production") == tmp_path / "ClinikoScribe"

    def test_the_model_pack_is_named_by_the_manifest_digest(self) -> None:
        # D5 / Task 3.5: the folder the installer looks for beside setup.exe.
        digest = "0123456789abcdef" * 4
        assert install_layout.model_pack_name(digest) == "ClinikoScribe-models-01234567"
        assert install_layout.model_pack_name(digest.upper()) == "ClinikoScribe-models-01234567"
        for bad in ("0123", "g" * 64, "0" * 65):
            with pytest.raises(ValueError):
                install_layout.model_pack_name(bad)

    def test_the_environment_is_read_on_every_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "a"))
        assert install_layout.data_root() == tmp_path / "a" / "ClinikoScribe"
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "b"))
        assert install_layout.data_root() == tmp_path / "b" / "ClinikoScribe"
        use_channel(monkeypatch, "dev")
        assert install_layout.data_root() == tmp_path / "b" / "ClinikoScribe-dev"

    def test_the_layer_variant_reads_the_layer_never_the_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class Layer:
            def __init__(self, value: str | None) -> None:
                self.value = value

            def environ(self, name: str) -> str | None:
                assert name == "LOCALAPPDATA"
                return self.value

        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "ignored"))
        layer = Layer(str(tmp_path / "layer"))
        assert install_layout.app_data_root_via(layer) == (  # type: ignore[arg-type]
            tmp_path / "layer" / "ClinikoScribe"
        )
        use_channel(monkeypatch, "dev")
        assert install_layout.app_data_root_via(layer) == (  # type: ignore[arg-type]
            tmp_path / "layer" / "ClinikoScribe-dev"
        )
        assert install_layout.app_data_root_via(Layer(None)) == (  # type: ignore[arg-type]
            Path.home() / "ClinikoScribe-dev"
        )

    @pytest.mark.parametrize("which", ["production", "dev"])
    def test_the_instance_guard_root_is_the_production_folder_for_both(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: Channel
    ) -> None:
        use_channel(monkeypatch, which)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert install_layout.instance_guard_root() == tmp_path / "ClinikoScribe"
        assert app.default_instance_lock_path() == tmp_path / "ClinikoScribe" / "app.lock"


def _real(path: Path) -> Path:
    """``path`` with links and short names resolved, as ``install_root``
    compares it."""
    return Path(os.path.realpath(path))


def _frozen_at(monkeypatch: pytest.MonkeyPatch, executable: Path) -> None:
    use_frozen(monkeypatch, True)
    monkeypatch.setattr(install_layout, "executable", lambda: str(executable))


class TestInstallRoot:
    def test_d_i1_the_one_accepted_root_is_program_files(self) -> None:
        # D-I1, decided 2026-10-02: only the Program Files install folder.
        assert install_layout.INSTALL_ROOTS == (r"C:\Program Files\ClinikoScribe",)

    def test_a_source_run_has_no_install_root(self, monkeypatch: pytest.MonkeyPatch) -> None:
        use_frozen(monkeypatch, False)
        monkeypatch.setattr(install_layout, "executable", lambda: pytest.fail("read"))
        assert install_layout.install_root() is None

    def test_a_packaged_build_runs_from_an_accepted_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _real(tmp_path) / "Install"
        _frozen_at(monkeypatch, root / "scribe-app.exe")
        assert install_layout.install_root(accepted=(str(root),)) == root
        # Windows paths compare without case or a trailing separator.
        assert install_layout.install_root(accepted=(str(root).upper() + "\\",)) == root
        monkeypatch.setattr(install_layout, "INSTALL_ROOTS", (str(root),))
        assert install_layout.install_root() == root

    def test_a_packaged_build_anywhere_else_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        base = _real(tmp_path)
        root = base / "Install"
        for elsewhere in (
            base / "Downloads" / "scribe-app.exe",
            root / "sub" / "scribe-app.exe",  # below the root is not the root
            base / "Install-evil" / "scribe-app.exe",
        ):
            _frozen_at(monkeypatch, elsewhere)
            with pytest.raises(InstallLayoutError):
                install_layout.install_root(accepted=(str(root),))
        assert issubclass(InstallLayoutError, RuntimeError)

    @pytest.mark.skipif(sys.platform != "win32", reason="directory junctions are Windows-only")
    def test_a_link_at_the_install_path_pointing_elsewhere_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import _winapi

        base = _real(tmp_path)
        target = base / "elsewhere"
        target.mkdir()
        (target / "scribe-app.exe").write_bytes(b"")
        root = base / "Install"
        _winapi.CreateJunction(str(target), str(root))
        _frozen_at(monkeypatch, root / "scribe-app.exe")
        with pytest.raises(InstallLayoutError):
            install_layout.install_root(accepted=(str(root),))


class TestModelsRoot:
    def test_frozen_the_models_are_in_the_install_folder(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _real(tmp_path) / "Install"
        _frozen_at(monkeypatch, root / "scribe-app.exe")
        monkeypatch.setattr(install_layout, "INSTALL_ROOTS", (str(root),))
        monkeypatch.delenv("LOCALAPPDATA", raising=False)  # not needed when frozen
        assert install_layout.models_root() == root / "models"
        assert benchmark.default_models_root() == root / "models"

    def test_frozen_outside_the_install_folder_the_models_root_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _frozen_at(monkeypatch, tmp_path / "Downloads" / "scribe-app.exe")
        with pytest.raises(InstallLayoutError):
            install_layout.models_root()

    @pytest.mark.parametrize(
        ("which", "folder"), [("production", "ClinikoScribe"), ("dev", "ClinikoScribe-dev")]
    )
    def test_a_source_run_keeps_the_models_under_the_channels_data_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: Channel, folder: str
    ) -> None:
        use_channel(monkeypatch, which)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert install_layout.models_root() == tmp_path / folder / "models"
        assert benchmark.default_models_root() == tmp_path / folder / "models"

    @pytest.mark.parametrize("which", ["production", "dev"])
    def test_a_source_run_without_localappdata_raises(
        self, monkeypatch: pytest.MonkeyPatch, which: Channel
    ) -> None:
        # The long-standing contract (test_language_model_runtime.py): no
        # home-folder fallback for the models.
        use_channel(monkeypatch, which)
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        with pytest.raises(RuntimeError, match="LOCALAPPDATA is not set"):
            install_layout.models_root()


# --- Task 1.2: every data-folder builder ---------------------------------------------


def _builders() -> dict[str, Path]:
    """Every default root a store, the log and the models use, by name."""
    return {
        "clinics": clinics.default_registry_path(),
        "sessions": session_store.default_sessions_root(),
        "audit": audit.default_audit_root(),
        "logs": logging_setup.default_log_dir(),
        "config": note_config.default_config_root(),
        "past_sessions": past_sessions.default_past_sessions_root(),
        "profile": practitioner_profile.default_profile_root(),
        "style": practitioner_profile.default_style_root(),
        "models": benchmark.default_models_root(),
    }


def _load_register_script() -> ModuleType:
    path = REPO / "scripts" / "register-native-host.py"
    spec = importlib.util.spec_from_file_location("register_native_host_layout", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("which", "folder"), [("production", "ClinikoScribe"), ("dev", "ClinikoScribe-dev")]
)
def test_every_store_is_under_the_channels_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: Channel, folder: str
) -> None:
    """C8: in the dev channel every store, the log, the config and the models
    are under ``ClinikoScribe-dev`` — none under the production folder. The
    registration script's install folder is the dev folder in EITHER pin: it
    is dev-only since Task 3.7."""
    use_channel(monkeypatch, which)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    roots = _builders()
    expected = {
        "clinics": "clinics.json",
        "sessions": "sessions",
        "audit": "audit",
        "logs": "logs",
        "config": "config",
        "past_sessions": "past_sessions",
        "profile": "profile",
        "style": "style",
        "models": "models",
    }
    assert roots == {name: tmp_path / folder / leaf for name, leaf in expected.items()}
    assert _load_register_script().INSTALL_DIR == tmp_path / "ClinikoScribe-dev"
    assert list(tmp_path.iterdir()) == []  # computing the roots creates nothing


def test_the_dev_registration_names_the_dev_host_and_extension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_channel(monkeypatch, "dev")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    script = _load_register_script()
    assert script.HOST_NAME == "com.scribe.cliniko_host_dev"
    assert script.REGISTRY_KEY == (
        r"Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host_dev"
    )
    assert script.MANIFEST_PATH == tmp_path / "ClinikoScribe-dev" / (
        "com.scribe.cliniko_host_dev.json"
    )
    manifest = script.generate_manifest()
    assert manifest["name"] == "com.scribe.cliniko_host_dev"
    assert manifest["allowed_origins"] == [
        "chrome-extension://pecfiifdlmdbkifmjkbkeiaflpenfejd/"
    ]
    # The pre-gate artifact it cleans up was only ever the production name's.
    assert script.LEGACY_ARTIFACTS[1].name == "com.scribe.cliniko_host.json"


# --- Task 1.2: the source scan --------------------------------------------------------

# Every non-path ``ClinikoScribe`` literal, BY NAME — the assignment it is
# the value of, or the function it is built in — with why it is not a folder.
_NON_PATH_LITERALS: dict[tuple[str, str], str] = {
    ("identity.py", "PIPE_PREFIX"): "the production pipe-name prefix (C2)",
    ("identity.py", "DEV_PIPE_PREFIX"): "the dev channel's pipe-name prefix (D3)",
    ("secure_storage.py", "_SERVICE_PREFIX"): "the Credential Manager service prefix (C2)",
    ("session_store.py", "SESSION_KEY_DESCRIPTION"): "a DPAPI key description (C2)",
    ("audit.py", "AUDIT_KEY_DESCRIPTION"): "a DPAPI key description (C2)",
    ("past_sessions.py", "PAST_SESSION_KEY_DESCRIPTION"): "a DPAPI key description (C2)",
    ("practitioner_profile.py", "PROFILE_KEY_DESCRIPTION"): "a DPAPI key description (C2)",
    ("practitioner_profile.py", "STYLE_KEY_DESCRIPTION"): "a DPAPI key description (C2)",
    ("app.py", "_single_instance_mutex_name"): "the single-instance mutex name (C2, D3)",
    ("exclusions.py", "APP_FOLDER_NAME"): (
        "a re-export of the production name, read by tests only (no folder is built)"
    ),
    ("exclusions.py", "backup_exclusions"): (
        "reads the installer's registry VALUE named BACKUP_VALUE_NAME (D6, Task 3.4); "
        "no folder is built"
    ),
}
_NAME = "clinikoscribe"
# The names that carry the folder name without spelling it: a reference to
# one outside install_layout (a read, an attribute, an import) is an offence
# too, by the same by-name allow-list (``BACKUP_VALUE_NAME``: round 13
# LOW-007, the production name under another name).
_FOLDER_NAME_REFS = frozenset(
    {"APP_FOLDER_NAME", "BACKUP_VALUE_NAME", "DEV_FOLDER_NAME", "folder_name"}
)


def _folder_name_ref(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        ref = node.id
    elif isinstance(node, ast.Attribute):
        ref = node.attr
    elif isinstance(node, ast.alias):
        ref = node.name
    else:
        return None
    return ref if ref in _FOLDER_NAME_REFS else None


def _folded_str(node: ast.AST) -> str | None:
    """A string literal, an f-string's literal parts joined, or a ``+`` of
    them, folded to one string; None for anything else."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            part.value
            for part in node.values
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _folded_str(node.left), _folded_str(node.right)
        if left is not None or right is not None:
            return (left or "") + (right or "")
    return None


def _docstrings(tree: ast.Module) -> set[int]:
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                found.add(id(body[0].value))
    return found


def _offences(
    source: str,
    module: str,
    allowed: Mapping[tuple[str, str], str] = _NON_PATH_LITERALS,
) -> list[str]:
    """Each place ``module`` spells the app's folder name outside a
    docstring, or refers to one of ``_FOLDER_NAME_REFS``, outside the
    by-name ``allowed`` list, as ``module:line (owner)``."""
    tree = ast.parse(source)
    docstrings = _docstrings(tree)
    found: list[str] = []

    def visit(node: ast.AST, owners: tuple[str, ...]) -> None:
        names = owners
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = (*owners, node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = (
                *owners,
                *(t.id if isinstance(t, ast.Name) else getattr(t, "attr", "") for t in targets),
            )
        ref = _folder_name_ref(node)
        if ref is not None and not any((module, name) in allowed for name in names):
            found.append(f"{module}:{getattr(node, 'lineno', '?')} ({ref})")
            return
        if id(node) not in docstrings:
            text = _folded_str(node)
            if text is not None and _NAME in text.casefold():
                if not any((module, name) in allowed for name in names):
                    found.append(f"{module}:{getattr(node, 'lineno', '?')} ({'.'.join(names)})")
                return  # one report per expression, not per part
        for child in ast.iter_child_nodes(node):
            visit(child, names)

    visit(tree, ())
    return found


def _scanned_files() -> list[tuple[str, Path]]:
    files = [(p.relative_to(SRC).as_posix(), p) for p in sorted(SRC.rglob("*.py"))]
    files += [(f"scripts/{p.name}", p) for p in sorted((REPO / "scripts").glob("*.py"))]
    return files


def test_no_cliniko_scribe_folder_is_built_outside_install_layout() -> None:
    """C8 / Task 1.2, the semantic surface: ANY spelling of the folder name in
    code — a literal, an f-string, a ``Path(...) / "ClinikoScribe"``, an
    ``os.path.join`` argument, a ``+`` of literals — and any reference to
    ``install_layout``'s folder-name constants or ``folder_name`` outside
    ``install_layout.py`` and the allow-list above is an offence. A source
    scan, not a proof: a name built at run time (``.format``, a join of
    variables, a placeholder that supplies part of the name, a ``getattr``
    by string) is unseen. An f-string's literal parts are joined across
    its placeholders, so ``f"Cliniko{x}Scribe"`` IS seen."""
    files = _scanned_files()
    assert len(files) > 40, "the scan found too few files to mean anything"
    offences: list[str] = []
    for module, path in files:
        if module == "install_layout.py":
            continue
        offences += _offences(path.read_text(encoding="utf-8"), module)
    assert offences == []


def test_every_allow_listed_literal_still_exists() -> None:
    """Each entry is needed: without it, its module has an offence. So the
    list never allows more than the code spells."""
    sources = {module: path.read_text(encoding="utf-8") for module, path in _scanned_files()}
    for entry in _NON_PATH_LITERALS:
        without = {key: reason for key, reason in _NON_PATH_LITERALS.items() if key != entry}
        assert _offences(sources[entry[0]], entry[0], without), entry


@pytest.mark.parametrize(
    "source",
    [
        'ROOT = Path(base) / "ClinikoScribe"\n',
        'ROOT = os.path.join(base, "ClinikoScribe", "sessions")\n',
        'def f(base):\n    return f"{base}\\\\ClinikoScribe\\\\logs"\n',
        'ROOT = base + "\\\\Cliniko" + "Scribe"\n',
        'ROOT = "Cliniko" "Scribe"\n',
        'ROOT = Path(base) / "clinikoscribe-dev"\n',
        'SESSION_KEY_DESCRIPTION = "ClinikoScribe session key"\n',  # allowed only in its module
        'def f():\n    """ClinikoScribe in a docstring."""\n    return "ClinikoScribe"\n',
        "ROOT = Path(base) / install_layout.APP_FOLDER_NAME\n",
        "from scribe_desktop.install_layout import DEV_FOLDER_NAME\n",
        "def f(base):\n    return Path(base) / folder_name()\n",
        "APP_FOLDER_NAME = install_layout.APP_FOLDER_NAME\n",  # allowed only in exclusions
        'def f(base, x):\n    return f"{base}\\\\Cliniko{x}Scribe"\n',
        "ROOT = Path(base) / install_layout.BACKUP_VALUE_NAME\n",
    ],
)
def test_the_scan_sees_every_spelling_it_claims(source: str) -> None:
    assert _offences(source, "elsewhere.py"), source


def test_the_scan_passes_docstrings_and_allowed_names() -> None:
    assert _offences('"""Under %LOCALAPPDATA%\\\\ClinikoScribe."""\n', "x.py") == []
    assert (
        _offences("APP_FOLDER_NAME: Final = install_layout.APP_FOLDER_NAME\n", "exclusions.py")
        == []
    )
    assert _offences('AUDIT_KEY_DESCRIPTION = "ClinikoScribe audit key"\n', "audit.py") == []
    assert (
        _offences(
            "def backup_exclusions(self):\n"
            "    return QueryValueEx(key, install_layout.BACKUP_VALUE_NAME)\n",
            "exclusions.py",
        )
        == []
    )
    assert (
        _offences(
            'def _single_instance_mutex_name():\n    return f"Global\\\\ClinikoScribe-app-{u}"\n',
            "app.py",
        )
        == []
    )


# --- Task 1.7: the remedy lines --------------------------------------------------------

# A source checkout's script remedy, as any string in ``src`` might spell it.
_REMEDY_PATTERN = re.compile(r"run\s+scripts[/\\]", re.IGNORECASE)


class TestRemedies:
    def test_a_source_run_names_the_setup_and_registration_scripts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        use_frozen(monkeypatch, False)
        assert install_layout.model_remedy() == (
            "run scripts/setup-models.py from a normal terminal"
        )
        assert install_layout.model_remedy("speaker-embedding") == (
            "run scripts/setup-models.py --only speaker-embedding from a normal terminal"
        )
        assert install_layout.model_remedy("language-model") == (
            "run scripts/setup-models.py --only language-model from a normal terminal"
        )
        assert install_layout.registration_remedy() == (
            "run scripts/register-native-host.py again from a normal terminal"
        )

    def test_a_packaged_build_says_reinstall(self, monkeypatch: pytest.MonkeyPatch) -> None:
        use_frozen(monkeypatch, True)
        for remedy in (
            install_layout.model_remedy(),
            install_layout.model_remedy("speaker-embedding"),
            install_layout.model_remedy("language-model"),
            install_layout.registration_remedy(),
        ):
            assert remedy == "reinstall Clinic Scribe"
            assert "scripts/" not in remedy

    def test_the_remedies_follow_frozen_not_the_channel(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The source-run models root and its remedy agree (both is_frozen).
        use_channel(monkeypatch, "production")
        use_frozen(monkeypatch, False)
        assert "scripts/setup-models.py" in install_layout.model_remedy()
        use_channel(monkeypatch, "dev")
        use_frozen(monkeypatch, True)
        assert install_layout.model_remedy() == install_layout.FROZEN_REMEDY

    def test_no_other_script_remedy_is_spelled_in_src(self) -> None:
        """Every "run scripts/…" remedy goes through ``install_layout``: each
        string in the parsed source — a literal, an f-string's literal parts,
        a ``+`` of literals, folded as the folder scan folds them — so a
        remedy split across a line or a concatenation is seen too, in any
        case and with either slash (``_REMEDY_PATTERN``)."""
        offenders = sorted(
            {
                f"{path.relative_to(SRC).as_posix()}:{getattr(node, 'lineno', '?')}"
                for path in sorted(SRC.rglob("*.py"))
                if path.name != "install_layout.py"
                for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
                if (text := _folded_str(node)) is not None and _REMEDY_PATTERN.search(text)
            }
        )
        assert offenders == []

    @pytest.mark.parametrize(
        "source",
        [
            'LINE = "missing - run " + "scripts/setup-models.py"\n',
            'LINE = "missing - run\\n" + "scripts/setup-models.py"\n',
            'LINE = f"{path}: Run scripts\\\\setup-models.py first"\n',
            'LINE = ("missing - run "\n    "scripts/setup-models.py")\n',
        ],
    )
    def test_the_remedy_scan_sees_a_split_remedy(self, source: str) -> None:
        assert any(
            (text := _folded_str(node)) is not None and _REMEDY_PATTERN.search(text)
            for node in ast.walk(ast.parse(source))
        ), source

    @pytest.mark.parametrize("frozen", [False, True])
    def test_every_model_line_carries_this_builds_remedy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen: bool
    ) -> None:
        from scribe_desktop.ui import models

        use_frozen(monkeypatch, frozen)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))  # no model is there
        if frozen:
            root = _real(tmp_path) / "Install"
            monkeypatch.setattr(install_layout, "executable", lambda: str(root / "a.exe"))
            monkeypatch.setattr(install_layout, "INSTALL_ROOTS", (str(root),))
        speaker = install_layout.model_remedy("speaker-embedding")
        assert speaker in models.speaker_model_missing_reason()
        assert speaker in models.attribution_did_not_run_reason()
        assert speaker in models.speaker_model_report_line("onnx")
        lines = models.model_file_report_lines("onnx")
        assert install_layout.model_remedy() in lines[0]
        assert install_layout.model_remedy() in lines[1]
        absent = models.language_model_absent_reason()
        if frozen:
            assert absent.endswith("not installed - reinstall Clinic Scribe")
        else:
            assert install_layout.model_remedy("language-model") in absent
            assert "AGENTS.md" in absent
        for text in (*lines, absent, models.speaker_model_missing_reason()):
            assert ("scripts/" in text) is not frozen, text


def _says(message: str, remedy: str, frozen: bool) -> None:
    """``message`` names ``remedy``; a packaged build's names no source step."""
    assert remedy in message, message
    if frozen:
        assert "scripts/" not in message and ".venv" not in message, message


@pytest.mark.parametrize("frozen", [False, True])
class TestEveryRaisedModelLineFollowsTheBuild:
    """Task 1.7, round 9 MED-002: each model or runtime error a user can see
    — the VAD, Whisper, the language model and its runtime, the speaker
    model and onnxruntime, the benchmark, the Status tab's registration line
    — names this build's remedy. Explicit ``tmp_path`` files only (C6)."""

    @pytest.fixture(autouse=True)
    def _offline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key, value in benchmark.OFFLINE_ENV.items():
            monkeypatch.setenv(key, value)
        for key in (*benchmark.FORBIDDEN_NATIVE_OVERRIDES, *benchmark.FORBIDDEN_TLS_OVERRIDES):
            monkeypatch.delenv(key, raising=False)

    def test_the_vad_and_whisper_lines(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen: bool
    ) -> None:
        from scribe_desktop import speech, transcription

        use_frozen(monkeypatch, frozen)
        with pytest.raises(speech.VadModelError) as vad:
            speech.SileroVad(model_path=tmp_path / "absent.onnx")
        _says(str(vad.value), install_layout.model_remedy(), frozen)
        with pytest.raises(transcription.TranscriptionModelError) as whisper:
            transcription.WhisperSpeechProvider(model_dir=tmp_path / "no-model")
        _says(str(whisper.value), install_layout.model_remedy(), frozen)

    def test_the_benchmark_line(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen: bool
    ) -> None:
        use_frozen(monkeypatch, frozen)
        with pytest.raises(RuntimeError) as exc:
            benchmark.run_all(tmp_path)
        _says(str(exc.value), install_layout.model_remedy(), frozen)

    def test_the_language_model_lines(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen: bool
    ) -> None:
        from scribe_desktop import language_model as lm

        use_frozen(monkeypatch, frozen)
        remedy = install_layout.model_remedy("language-model")

        def never(**_kwargs: object) -> object:
            pytest.fail("the runtime was reached")

        path = tmp_path / "model.gguf"
        with pytest.raises(lm.LanguageModelError) as absent:
            lm.LocalLanguageModel(path, llama_factory=never)
        _says(str(absent.value), remedy, frozen)
        path.write_bytes(b"gguf")
        with pytest.raises(lm.LanguageModelError, match="bytes") as size:
            lm.LocalLanguageModel(path, expected_size=5, llama_factory=never)
        _says(str(size.value), remedy, frozen)
        with pytest.raises(lm.LanguageModelError, match="pinned model") as digest:
            lm.LocalLanguageModel(
                path, expected_sha256="0" * 64, expected_size=4, llama_factory=never
            )
        _says(str(digest.value), remedy, frozen)

    def test_the_prose_runtime_line(self, monkeypatch: pytest.MonkeyPatch, frozen: bool) -> None:
        from scribe_desktop import language_model as lm

        use_frozen(monkeypatch, frozen)
        monkeypatch.setitem(sys.modules, "llama_cpp", None)  # the import fails
        with pytest.raises(lm.LanguageModelError, match="not importable") as exc:
            lm._import_llama()
        message = str(exc.value)
        if frozen:
            _says(message, install_layout.FROZEN_REMEDY, frozen)
            assert "AGENTS.md" not in message
        else:
            assert "AGENTS.md" in message

    def test_the_speaker_model_lines(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen: bool
    ) -> None:
        from scribe_desktop import speaker_embedding as se

        use_frozen(monkeypatch, frozen)
        remedy = install_layout.model_remedy("speaker-embedding")
        path = tmp_path / "speaker.onnx"
        with pytest.raises(se.SpeakerModelError) as absent:
            se.load_onnx_session(path)
        _says(str(absent.value), remedy, frozen)
        # The setup script's naming note means nothing in a packaged build.
        assert ("candidate" in str(absent.value)) is not frozen
        path.write_bytes(b"onnx")
        with pytest.raises(se.SpeakerModelError, match="pinned model") as digest:
            se.load_onnx_session(path, expected_sha256="0" * 64)
        _says(str(digest.value), remedy, frozen)
        monkeypatch.setitem(sys.modules, "onnxruntime", None)  # the import fails
        with pytest.raises(se.SpeakerModelError, match="not importable") as runtime:
            se.load_onnx_session(path)
        message = str(runtime.value)
        if frozen:
            _says(message, install_layout.FROZEN_REMEDY, frozen)
        else:
            assert "[ml]" in message

    def test_the_status_tabs_registration_line(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen: bool
    ) -> None:
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from scribe_desktop.status import RegistrationStatus
        from scribe_desktop.ui import main_window

        qapp = QApplication.instance() or QApplication([])
        use_frozen(monkeypatch, frozen)
        # Never the real registry (C6).
        monkeypatch.setattr(
            main_window,
            "read_registration_status",
            lambda layer: RegistrationStatus(None, manifest_exists=False, launcher_exists=False),
        )
        panel = main_window.StatusPanel(config_root=tmp_path / "config")
        _says(panel.registration_label.text(), install_layout.registration_remedy(), frozen)
        panel.close()
        assert qapp is not None


# --- Task 1.8: one version (D12) -------------------------------------------------------


def test_the_version_is_the_same_everywhere() -> None:
    """pyproject is the source; ``__version__``, the extension manifest and
    its package files are pinned equal to it (the lock file's two copies are
    what ``npm version`` keeps in step with ``package.json``)."""
    pyproject = tomllib.loads((REPO / "desktop" / "pyproject.toml").read_text(encoding="utf-8"))
    version = pyproject["project"]["version"]
    manifest = (REPO / "extension" / "src" / "manifest.ts").read_text(encoding="utf-8")
    manifest_versions = re.findall(r'^\s*version: "([^"]+)",$', manifest, re.MULTILINE)
    package = json.loads((REPO / "extension" / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((REPO / "extension" / "package-lock.json").read_text(encoding="utf-8"))
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    assert __version__ == version
    assert manifest_versions == [version]
    assert package["version"] == version
    assert lock["version"] == version
    assert lock["packages"][""]["version"] == version
