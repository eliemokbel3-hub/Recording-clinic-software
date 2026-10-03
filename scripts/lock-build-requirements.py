r"""Generate the hashed build lock, desktop/requirements-build.txt (installation
plan Task 3.1).

The lock is what a release build installs into its clean build environment
with ``pip install --require-hashes --no-deps``: every runtime dependency of
the packaged app (desktop/pyproject.toml's dependencies and its ``[ml]``
extra, ``sounddevice``, and the prose runtime's own dependencies) plus the
build tools PyInstaller needs beside itself, each pinned to ONE version and
the SHA-256 of its Windows wheel. Two things are deliberately NOT in it:

- the prose runtime wheel itself, which stays in
  desktop/requirements-ml-prose.txt (its own hash pin, note-learning plan D8);
- PyInstaller, which is installed from its source at a pinned commit so the
  bootloader can be built here (plan D1; ``scripts/build-release.py`` holds
  that pin and checks it).

THE VERSIONS ARE NOT CHOSEN HERE. They come from a ``pip freeze --all`` of the
environment the Phase 0 spike proved (``--constraints``), plus the build
tools pinned here (``BUILD_TOOL_PINS``: the three Task 0.1's PyInstaller
install added, and PyInstaller's build backend hatchling with its
dependencies, which a build without isolation needs locked). pip resolves
the closure of the requirements under those pins and downloads one wheel for
each package; a package whose version the proven environment does not pin,
or a download that is not a wheel, is refused by name. So the lock can only
describe the environment that was proved, never a newer one.

This is a BUILD-TIME network step (pip downloads from PyPI; data-flow-map
flow 9), run by the practitioner from a normal PowerShell at the repository
root, never by the app (the freeze only reads the environment):

    .venv\Scripts\python.exe -m pip freeze --all | Out-File -Encoding utf8 "$env:TEMP\proven-freeze.txt"
    .venv\Scripts\python.exe scripts\lock-build-requirements.py --constraints "$env:TEMP\proven-freeze.txt"

Re-run it when a dependency changes, and commit the lock it writes.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PYPROJECT = REPO / "desktop" / "pyproject.toml"
LOCK_PATH = REPO / "desktop" / "requirements-build.txt"

# The build tools the proven environment's freeze does not carry, each pinned
# here (a build-tool pin is both a constraint and an allowed version, and it
# wins over the freeze's version of the same package: these run only while
# PyInstaller is installed into the build environment, never in the app).
BUILD_TOOL_PINS: Mapping[str, str] = {
    # Task 0.1 RESULT (the plan): installing PyInstaller 6.22.3 into the
    # proven environment added exactly these.
    "pyinstaller-hooks-contrib": "2026.8",
    "altgraph": "0.17.5",
    "pefile": "2024.8.26",
    # Round 31 (the first Release run): PyInstaller's source builds with the
    # hatchling backend (its pyproject's [build-system], build-release.py
    # PYINSTALLER_BUILD_REQUIRES), installed with --no-build-isolation, so the
    # backend and its runtime dependencies must be in the lock. hatchling
    # 1.32.4's Requires-Dist: packaging>=24.2 (already locked from the
    # freeze), pathspec>=0.10.1, pluggy>=1.0.0, tomlkit>=0.11.1,
    # trove-classifiers (tomli only below Python 3.11). Versions from PyPI on
    # 2026-10-03; each a py3-none-any wheel.
    "hatchling": "1.32.4",
    "pathspec": "1.1.1",
    "pluggy": "1.6.0",
    "tomlkit": "0.15.1",
    "trove-classifiers": "2026.9.21.13",
}

# Beside pyproject's runtime dependencies: what the packaged app also loads,
# and what installing PyInstaller from source needs.
EXTRA_REQUIREMENTS: tuple[str, ...] = (
    # Recording (AGENTS.md: deliberately not in pyproject).
    "sounddevice",
    # The prose runtime's own dependencies (llama-cpp-python 0.3.35's
    # Requires-Dist); the runtime wheel is installed with --no-deps.
    "typing-extensions",
    "numpy",
    "diskcache",
    "jinja2",
    # PyInstaller from source, installed with --no-deps --no-build-isolation:
    # its own Requires-Dist...
    "pyinstaller-hooks-contrib",
    "altgraph",
    "pefile",
    "pywin32-ctypes",
    "packaging",
    "setuptools",
    # ...and its build backend (round 31), whose dependencies pip resolves
    # under BUILD_TOOL_PINS.
    "hatchling",
)

# Never in a build lock: the prose runtime (its own file) and PyInstaller (its
# pinned source), and the developer tools.
NEVER_LOCKED: frozenset[str] = frozenset(
    {"llama-cpp-python", "pyinstaller", "pytest", "ruff", "mypy", "scribe-desktop", "pip"}
)

_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_PIN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*==\s*([^\s;#]+)\s*(?:[;#].*)?$")
_LOCK_ENTRY = re.compile(
    r"^([a-z0-9][a-z0-9-]*)==(\S+) \\\n    --hash=sha256:([0-9a-f]{64})$", re.MULTILINE
)


class LockError(RuntimeError):
    """The lock cannot be generated as asked; the message names why."""


def normalise(name: str) -> str:
    """PEP 503 name normalisation."""
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    match = _NAME.match(requirement)
    if match is None:
        raise LockError(f"not a requirement: {requirement!r}")
    return normalise(match.group(1))


def runtime_requirements(pyproject_text: str) -> list[str]:
    """pyproject's dependencies plus its ``[ml]`` extra, as written."""
    project = tomllib.loads(pyproject_text)["project"]
    return [*project["dependencies"], *project["optional-dependencies"]["ml"]]


def proven_pins(freeze_text: str) -> dict[str, str]:
    """``name -> version`` from a ``pip freeze --all``; editable and
    direct-URL lines (the project itself, the prose wheel) are skipped."""
    pins: dict[str, str] = {}
    for line in freeze_text.splitlines():
        match = _PIN.match(line)
        if match is not None:
            pins[normalise(match.group(1))] = match.group(2)
    return pins


def wheel_identity(filename: str) -> tuple[str, str]:
    """``(normalised name, version)`` of a wheel file name; anything that is
    not a wheel (an sdist, a stray file) is refused."""
    if not filename.endswith(".whl"):
        raise LockError(f"{filename} is not a wheel; the build lock is wheels only")
    parts = filename[: -len(".whl")].split("-")
    if len(parts) not in (5, 6):
        raise LockError(f"{filename} is not a wheel file name")
    return normalise(parts[0]), parts[1]


def render_lock(entries: Mapping[str, tuple[str, str]], *, constraints_name: str) -> str:
    """The lock text: a header, then ``name==version`` with its one hash,
    sorted by name."""
    lines = [
        "# The hashed build lock (installation plan Task 3.1). GENERATED by",
        "# scripts/lock-build-requirements.py from a `pip freeze --all` of the",
        f"# proven environment ({constraints_name}) - do not edit by hand.",
        "#",
        "# Installed by scripts/build-release.py into its clean build environment:",
        "#     python -m pip install --require-hashes --no-deps -r desktop/requirements-build.txt",
        "# Not here: llama-cpp-python (desktop/requirements-ml-prose.txt) and",
        "# PyInstaller (built from its pinned source by build-release.py, plan D1).",
        "",
    ]
    for name in sorted(entries):
        version, digest = entries[name]
        lines.append(f"{name}=={version} \\\n    --hash=sha256:{digest}")
    return "\n".join(lines) + "\n"


def parse_lock(text: str) -> dict[str, tuple[str, str]]:
    """``name -> (version, sha256)`` of every entry in a lock this script
    wrote."""
    return {m.group(1): (m.group(2), m.group(3)) for m in _LOCK_ENTRY.finditer(text)}


def missing_runtime_dependencies(lock: Mapping[str, object], pyproject_text: str) -> list[str]:
    """Each runtime dependency (pyproject, ``[ml]``, ``EXTRA_REQUIREMENTS``)
    the lock does not carry. The pywin32 marker is Windows-only, and the lock
    is a Windows build's, so every name applies."""
    wanted = [requirement_name(r) for r in runtime_requirements(pyproject_text)]
    wanted += [requirement_name(r) for r in EXTRA_REQUIREMENTS]
    return sorted({name for name in wanted if name not in lock})


Runner = Callable[[Sequence[str]], int]


def _run(command: Sequence[str]) -> int:
    return subprocess.run(list(command), check=False).returncode  # noqa: S603


def generate(
    freeze_text: str,
    pyproject_text: str,
    *,
    constraints_name: str = "the proven freeze",
    workdir: Path,
    run: Runner = _run,
    python: str = sys.executable,
) -> str:
    """Resolve, download and hash; return the lock text. ``run`` executes the
    one ``pip download`` (a fake in tests), which writes the wheels into
    ``workdir / "wheels"``."""
    pins = proven_pins(freeze_text) | dict(BUILD_TOOL_PINS)
    constraints = workdir / "constraints.txt"
    constraints.write_text(
        "".join(f"{name}=={version}\n" for name, version in sorted(pins.items())),
        encoding="utf-8",
    )
    wheels = workdir / "wheels"
    wheels.mkdir()
    requirements = [*runtime_requirements(pyproject_text), *EXTRA_REQUIREMENTS]
    command = [
        python, "-m", "pip", "download",
        "--only-binary=:all:",
        "--dest", str(wheels),
        "--constraint", str(constraints),
        *requirements,
    ]
    if run(command) != 0:
        raise LockError("pip download failed; nothing was written")
    entries: dict[str, tuple[str, str]] = {}
    for path in sorted(wheels.iterdir()):
        name, version = wheel_identity(path.name)
        if name in NEVER_LOCKED:
            raise LockError(f"{name} must not be in the build lock")
        if pins.get(name) != version:
            raise LockError(
                f"{name} {version} is not pinned by the proven environment "
                f"(pinned: {pins.get(name, 'nothing')}); add it there first"
            )
        entries[name] = (version, hashlib.sha256(path.read_bytes()).hexdigest())
    missing = missing_runtime_dependencies(entries, pyproject_text)
    if missing:
        raise LockError("the lock would miss: " + ", ".join(missing))
    return render_lock(entries, constraints_name=constraints_name)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--constraints",
        required=True,
        type=Path,
        help="a `pip freeze --all` of the proven environment (read only)",
    )
    parser.add_argument("--out", type=Path, default=LOCK_PATH, help="where to write the lock")
    args = parser.parse_args(None if argv is None else list(argv))
    freeze_text = args.constraints.read_text(encoding="utf-8-sig")
    with tempfile.TemporaryDirectory(prefix="scribe-lock-") as temp:
        try:
            text = generate(
                freeze_text,
                PYPROJECT.read_text(encoding="utf-8"),
                constraints_name=args.constraints.name,
                workdir=Path(temp),
            )
        except LockError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {len(parse_lock(text))} pinned wheels to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
