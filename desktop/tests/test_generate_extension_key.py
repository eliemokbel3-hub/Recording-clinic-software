"""Round 27 PR-LOW-024: `scripts/generate-extension-key.py --out` names only
the two gitignored key files. Never reads or writes a real key: the allowed
paths are only resolved, and a refused one fails before any key I/O."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load() -> ModuleType:
    path = REPO / "scripts" / "generate-extension-key.py"
    spec = importlib.util.spec_from_file_location("generate_extension_key", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


key_script = _load()


@pytest.mark.parametrize(
    "out",
    [
        Path("extension/key.pem"),
        Path("extension/key-dev.pem"),
        Path("extension/../extension/key-dev.pem"),
        REPO / "extension" / "key.pem",
    ],
)
def test_the_two_gitignored_key_files_are_allowed(out: Path) -> None:
    assert key_script.resolve_out(out) in {
        (REPO / "extension" / "key.pem").resolve(),
        (REPO / "extension" / "key-dev.pem").resolve(),
    }


@pytest.mark.parametrize(
    "out",
    [
        Path("extension/dev-key.pem"),
        Path("key.pem"),
        Path("extension/src/key.pem"),
        Path("../key-dev.pem"),
    ],
)
def test_any_other_file_is_refused_before_key_io(
    out: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert key_script.resolve_out(out) is None
    monkeypatch.setattr(
        key_script, "load_or_create_private_key", lambda path: pytest.fail("key I/O")
    )
    with pytest.raises(SystemExit) as exc:
        key_script.main(["--out", str(out)])
    assert exc.value.code == 2
