"""Installation plan Task 3.6: ``.github/workflows/release.yml``, as text.

The workflow cannot run from a test (it needs a push and GitHub); its first
green, attested run is the practitioner's step. Pinned here: a manual run on
main only, least-privilege permissions, the fixed runner image, Task 0.1's
Python, the Inno Setup 6.7.3 pin checked by SHA-256 and by the build's banner
check, the build WITHOUT the model pack, the attestation and the upload. The
action pins that need the network are placeholders that fail closed; the
test that checks they became commit SHAs SKIPS BY NAME until they do."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "release.yml"
TEXT = WORKFLOW.read_text(encoding="utf-8")
# The pins read the workflow as GitHub does: full-line comments removed, so a
# step named in a comment can never stand in for the step itself.
BODY = "\n".join(line for line in TEXT.splitlines() if not line.lstrip().startswith("#"))
CI = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
_USES = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)@(\S+)\s*$", re.MULTILINE)


def _uses(text: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in _USES.finditer(text)}


def _steps() -> list[str]:
    """Each step of the one job, from its ``- `` line to the next."""
    steps = BODY.split("\n    steps:\n", 1)[1]
    return [s for s in re.split(r"^      - ", steps, flags=re.MULTILINE) if s.strip()]


def _step(name: str) -> str:
    """The one step whose first line is ``name: <name>…``."""
    [step] = [s for s in _steps() if s.startswith(f"name: {name}")]
    return step


def test_a_manual_run_on_main_only() -> None:
    assert re.search(r"^on:\n  workflow_dispatch:\n\n", BODY, re.MULTILINE)
    assert "push:" not in BODY and "pull_request" not in BODY and "schedule:" not in BODY
    assert "if: github.ref == 'refs/heads/main'" in BODY


def test_permissions_are_least_privilege() -> None:
    top = BODY.split("jobs:", 1)[0]
    assert "permissions:\n  contents: read\n" in top
    job = BODY.split("jobs:", 1)[1]
    block = job.split("permissions:", 1)[1].split("steps:", 1)[0]
    assert sorted(line.strip() for line in block.strip().splitlines()) == [
        "attestations: write",
        "contents: read",
        "id-token: write",
    ]
    assert "write-all" not in BODY and "contents: write" not in BODY
    assert "persist-credentials: false" in _steps()[0]


def test_the_runner_python_and_inno_are_pinned() -> None:
    assert "runs-on: windows-2025" in BODY
    assert 'python-version: "3.14.6"' in BODY
    inno = _step("Install Inno Setup")
    assert '$version = "6.7.3"' in inno
    assert "Get-FileHash $installer -Algorithm SHA256" in inno
    # The build itself refuses any other compiler (its banner check).
    spec = importlib.util.spec_from_file_location(
        "build_release_for_workflow", REPO / "scripts" / "build-release.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert module.INNO_VERSION == "6.7.3"


def test_the_build_skips_the_model_pack_and_uses_the_pinned_source() -> None:
    build = _step("Build the installer")
    assert "python scripts/build-release.py --pyinstaller-src" in build
    assert "--model-pack" not in BODY and "--write-manifest" not in BODY
    assert "--no-defender" not in BODY
    assert "--branch v6.22.3" in _step("PyInstaller source")


def test_the_installer_and_its_sums_are_attested_and_uploaded() -> None:
    attest = _step("Attest build provenance")
    assert "uses: actions/attest-build-provenance@" in attest
    assert "release/installer/*.exe" in attest and "release/installer/SHA256SUMS.txt" in attest
    upload = _step("Upload the installer")
    assert "uses: actions/upload-artifact@" in upload
    assert "if-no-files-found: error" in upload


def test_the_ci_actions_are_reused_at_ci_ymls_pins() -> None:
    ci = _uses(CI)
    for action in ("actions/checkout", "actions/setup-python", "actions/setup-node"):
        assert _uses(BODY)[action] == ci[action]


def test_an_unrecorded_inno_hash_fails_closed() -> None:
    step = _step("Install Inno Setup")
    assert "if ($expected -notmatch '^[0-9a-fA-F]{64}$')" in step
    # The refusal comes BEFORE the download, and the hash compare after it.
    assert step.index("throw") < step.index("Invoke-WebRequest") < step.index("-ne $expected")


def test_a_step_named_only_in_a_comment_is_not_found() -> None:
    """The step lookup is not fooled by the header comment, which also says
    "Install Inno Setup"."""
    assert '"Install Inno Setup"' in TEXT.split("name: Release", 1)[0]
    assert _step("Install Inno Setup").startswith("name: Install Inno Setup 6.7.3")
    with pytest.raises(ValueError):
        _step("Install Inno Setup\" step")


@pytest.mark.skipif(
    "PIN-REQUIRED" in BODY,  # the header comment's own mention never keeps it skipped
    reason="release.yml's action and Inno Setup pins are not recorded yet - Task 3.6's "
    "practitioner/composer step (needs the network)",
)
def test_every_new_action_is_pinned_to_a_commit() -> None:
    """The release job holds an OIDC token: every action it adds beyond the
    three ci.yml already trusts is pinned to a full commit SHA."""
    ci = _uses(CI)
    for action, ref in _uses(BODY).items():
        if action not in ci:
            assert re.fullmatch(r"[0-9a-f]{40}", ref), action
