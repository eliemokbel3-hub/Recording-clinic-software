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
# A trailing comment (``@<sha> # v2.1.0``, the usual way to pin) is allowed,
# so a pinned line is never skipped by the pin check (round 22 MED-001).
_USES = re.compile(r"^\s*(?:-\s+)?uses:\s*([^\s@]+)@(\S+)\s*(?:#.*)?$", re.MULTILINE)
# Every action the release workflow runs — each pinned to a commit, ci.yml's
# three included (H.4 SEC-002: the build of record runs them).
RELEASE_ACTIONS = {
    "actions/checkout",
    "actions/setup-python",
    "actions/setup-node",
    "actions/attest-build-provenance",
    "actions/download-artifact",
    "actions/upload-artifact",
}


def _uses(text: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in _USES.finditer(text)}


def _jobs() -> dict[str, str]:
    """Each job's text by its id (the two-space keys under ``jobs:``)."""
    body = BODY.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([A-Za-z0-9_-]+):\n", body, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


def _permissions(job: str) -> list[str]:
    block = _jobs()[job].split("permissions:", 1)[1].split("steps:", 1)[0]
    return sorted(line.strip() for line in block.strip().splitlines())


def _steps(job: str = "build") -> list[str]:
    """Each step of ``job``, from its ``- `` line to the next."""
    steps = _jobs()[job].split("\n    steps:\n", 1)[1]
    return [s for s in re.split(r"^      - ", steps, flags=re.MULTILINE) if s.strip()]


def _step(name: str, job: str = "build") -> str:
    """The one step of ``job`` whose first line is ``name: <name>…``."""
    [step] = [s for s in _steps(job) if s.startswith(f"name: {name}")]
    return step


def test_a_manual_run_on_main_only() -> None:
    assert re.search(r"^on:\n  workflow_dispatch:\n\n", BODY, re.MULTILINE)
    assert "push:" not in BODY and "pull_request" not in BODY and "schedule:" not in BODY
    assert "if: github.ref == 'refs/heads/main'" in _jobs()["build"]
    # The attest job runs only after that build (so only on main).
    assert "needs: build" in _jobs()["attest"]


def test_permissions_are_least_privilege() -> None:
    top = BODY.split("jobs:", 1)[0]
    assert "permissions:\n  contents: read\n" in top
    assert set(_jobs()) == {"build", "attest"}
    # Round 22: the build runs third-party code, so it holds no OIDC token;
    # only the attest job, which runs nothing but two pinned actions, does.
    assert _permissions("build") == ["contents: read"]
    assert _permissions("attest") == [
        "attestations: write",
        "contents: read",
        "id-token: write",
    ]
    assert BODY.count("id-token: write") == 1
    assert [step.split("\n", 1)[0] for step in _steps("attest")] == [
        "name: Download the installer",
        "name: Attest build provenance",
    ]
    assert "run:" not in _jobs()["attest"]
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
    upload = _step("Upload the installer")
    assert "uses: actions/upload-artifact@" in upload
    assert "if-no-files-found: error" in upload
    assert "path: ${{ runner.temp }}/release/installer/" in upload
    # The attest job attests exactly the artifact the build uploaded.
    download = _step("Download the installer", job="attest")
    assert "uses: actions/download-artifact@" in download
    assert "name: clinic-scribe-installer" in upload and "name: clinic-scribe-installer" in download
    assert "path: installer" in download
    attest = _step("Attest build provenance", job="attest")
    assert "uses: actions/attest-build-provenance@" in attest
    assert "installer/*.exe" in attest and "installer/SHA256SUMS.txt" in attest


def test_the_release_job_never_runs_a_tag_or_restores_a_cache() -> None:
    """H.4 SEC-002: ci.yml's tags are not reused here — every action is a
    commit pin or the fail-closed placeholder — and no shared npm cache is
    restored into the job that builds the release."""
    for action, ref in _uses(BODY).items():
        assert ref == "PIN-REQUIRED" or re.fullmatch(r"[0-9a-f]{40}", ref), action
    assert "cache:" not in BODY and "actions/cache" not in BODY


def test_an_unrecorded_inno_hash_fails_closed() -> None:
    step = _step("Install Inno Setup")
    assert "if ($expected -notmatch '^[0-9a-fA-F]{64}$')" in step
    # The refusal comes BEFORE the download, and the hash compare after it.
    assert step.index("throw") < step.index("Invoke-WebRequest") < step.index("-ne $expected")


def test_a_failed_inno_install_fails_the_step() -> None:
    """Round 23: the silent install's exit code is checked, and the compiler
    must be where the build's default ``--iscc`` looks — never a pass that
    leaves the build to fail later with the wrong reason."""
    step = _step("Install Inno Setup")
    assert "-Wait -PassThru" in step
    assert "if ($setup.ExitCode -ne 0)" in step
    assert r"${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" in step
    spec = importlib.util.spec_from_file_location(
        "build_release_for_inno_path", REPO / "scripts" / "build-release.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    assert str(module.DEFAULT_ISCC) == r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"


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
def test_every_action_is_pinned_to_a_commit() -> None:
    """The workflow attests the build of record: every action it runs is
    pinned to a full commit SHA (H.4 SEC-002: ci.yml's three too)."""
    pins = _uses(BODY)
    assert set(pins) == RELEASE_ACTIONS  # none slips past the pattern unchecked
    for action, ref in pins.items():
        assert re.fullmatch(r"[0-9a-f]{40}", ref), action


def test_the_uses_pattern_reads_a_commented_pin() -> None:
    """Round 22 MED-001: ``@<sha> # v2.1.0`` is how a pin is usually written;
    the pattern must read it, or the pin check would check nothing."""
    sha = "0" * 40
    assert _uses(f"      - uses: actions/upload-artifact@{sha} # v4.6.2\n") == {
        "actions/upload-artifact": sha
    }
    assert _uses("        uses: actions/attest-build-provenance@v2 # tag\n") == {
        "actions/attest-build-provenance": "v2"
    }


def test_every_action_is_known() -> None:
    """Runs now, pins or not: the set the pin check walks is exactly the
    workflow's actions, so a new action cannot go unchecked — and the pattern
    finds every ``uses:`` line (none is missed by its shape)."""
    assert set(_uses(BODY)) == RELEASE_ACTIONS
    assert len(_uses(BODY)) == len(re.findall(r"^\s*(?:-\s+)?uses:", BODY, re.MULTILINE))
