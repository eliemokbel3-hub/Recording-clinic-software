r"""Build a Clinic Scribe release: the installer, the model pack and the build
audit (installation plan Tasks 3.3 and 3.5, D1/D5/D7/D12).

FOUR MODES, each run by the practitioner from a normal PowerShell at the
repository root (or by the CI release job, Task 3.6, for the build itself):

1. ``--write-manifest --models DIR`` (Task 3.3, once, and again only when a
   model pin changes): reads the models in DIR - read only - checks every
   pinned one against its pin, and writes packaging/models-manifest.json:
   each file's path, size and SHA-256 (silero; every file of whisper
   ``medium``; the speaker model and its attribution notice, D-I2; the
   language model). Commit the manifest it writes.

2. ``--model-pack --models DIR --out DIR``: copies exactly the manifest's
   files into ``<out>\ClinikoScribe-models-<sha8>\`` (the name the installer
   looks for, beside setup.exe), checking each against the manifest before
   anything is copied and again after.

3. ``--audit DIST``: checks a PyInstaller bundle (``<out>\dist\scribe``):
   the two programs, the shipped config, the native ML libraries, NO Qt
   networking file, and the packaged app's offline self-check
   (``scribe-app.exe --self-check-offline``, run with hostile variables set,
   must exit 0); then a Defender custom scan where one can run.

4. The build (no mode flag): ``--pyinstaller-src DIR --out DIR``.
   Stage one (this interpreter, Python 3.14, standard library only): a CLEAN
   build environment in ``<out>\build-venv`` from the hashed lock
   (desktop/requirements-build.txt) and the prose wheel; PyInstaller from its
   source checkout at the pinned commit, which must be a CLEAN clone (no
   changed, extra or ignored file), built with the LOCKED build backend
   (hatchling; no build isolation, so nothing unhashed is fetched; the lock
   must carry it), with the bootloader built here (D1;
   the C++ build tools must be installed); ``pip check``. Stage two (the
   build environment's interpreter): PyInstaller over packaging/scribe.spec,
   the host manifest, the extension (``npm ci`` and
   ``npm run build -- --mode release``) into the bundle's ``extension``
   folder, THEN the bundle and extension audits (so no npm code runs after
   them, round 26 SEC-001) and the Defender scan, then Inno Setup over
   packaging/scribe.iss with the version from
   desktop/pyproject.toml (D12) and the manifest's hashes compiled in,
   BUILD-INFO.txt (this checkout's commit and whether its tree was clean: a
   local build may carry uncommitted work, D7) and SHA256SUMS.txt over every
   output. ``--audit`` exits 1 on any failure, a Defender detection included.

The build needs the network for the lock install, ``npm ci`` and the
PyInstaller source (build-time only, data-flow-map flow 9); the app never
does. Nothing here touches %LOCALAPPDATA% or the registry.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import ModuleType
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "desktop" / "src"
PYPROJECT = REPO / "desktop" / "pyproject.toml"
LOCK = REPO / "desktop" / "requirements-build.txt"
PROSE_LOCK = REPO / "desktop" / "requirements-ml-prose.txt"
SPEC = REPO / "packaging" / "scribe.spec"
ISS = REPO / "packaging" / "scribe.iss"
MANIFEST_PATH = REPO / "packaging" / "models-manifest.json"
ATTRIBUTION_SOURCE = REPO / "packaging" / "speaker-model-ATTRIBUTION.txt"
EXTENSION = REPO / "extension"

# Task 0.1 RESULT: the interpreter the frozen build was proved on (3.14.6;
# any 3.14 shares its wheels). D1: PyInstaller from source at this exact
# commit, with the bootloader rebuilt here — its shipped windowed bootloader
# had this SHA-256, so a build whose runw.exe still has it was not rebuilt.
BUILD_PYTHON = (3, 14)
PYINSTALLER_VERSION = "6.22.3"
PYINSTALLER_COMMIT = "ecd7993d65c43b254f4e3f718e36d5b4a70a3ed5"
SHIPPED_RUNW_SHA256 = "2291f269c3a3804fde1079462239e09a8b32fffbeeaa8f628a531faf5be77d41"
RUNW = Path("PyInstaller") / "bootloader" / "Windows-64bit-intel" / "runw.exe"
PYINSTALLER_CLONE = (
    f"git clone --depth 1 --branch v{PYINSTALLER_VERSION} "
    "https://github.com/pyinstaller/pyinstaller.git <an empty folder>"
)
# Round 31 (the first Release run failed on it): the pinned source's
# pyproject.toml declares `[build-system] requires = ["hatchling"]`,
# `build-backend = "hatchling.build"`. It is installed with
# --no-build-isolation (no unhashed fetch), so every name here must be in the
# build lock (lock-build-requirements.py BUILD_TOOL_PINS; pinned equal by
# test). preflight checks the source still declares no more than this, so a
# PyInstaller bump forces a re-check.
PYINSTALLER_BUILD_REQUIRES = ("hatchling",)
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")

# Task 3.6 / handoff open item 2: Inno Setup 6.7.3 on both sides (the
# practitioner's local copy; CI installs it). OPEN until the practitioner
# confirms the pin and the licence question ("Non-commercial use only").
INNO_VERSION = "6.7.3"
INNO_BANNER = f"Compiler engine version: Inno Setup {INNO_VERSION}"
DEFAULT_ISCC = Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")

COLLECT_NAME = "scribe"  # packaging/scribe.spec's COLLECT: <out>\dist\scribe
APP_EXE = "scribe-app.exe"
HOST_EXE = "scribe-host.exe"
INTERNAL = "_internal"
SELF_CHECK_FLAG = "--self-check-offline"
# Each holds a native library the app loads by path (Task 0.1's checks).
NATIVE_LIBRARY_DIRS = ("ctranslate2", "onnxruntime/capi", "llama_cpp/lib")
# The packaged app must clear or override each of these itself (the offline
# kill-switches and the two refused overrides, benchmark.OFFLINE_ENV and
# FORBIDDEN_*): the self-check runs with them all set wrong.
HOSTILE_ENV: Mapping[str, str] = {
    "HF_HUB_OFFLINE": "0",
    "TRANSFORMERS_OFFLINE": "0",
    "HF_HUB_DISABLE_TELEMETRY": "0",
    "SSLKEYLOGFILE": r"C:\audit-not-a-file\keys.log",
    "LLAMA_CPP_LIB_PATH": r"C:\audit-not-a-folder",
}
SUMS_NAME = "SHA256SUMS.txt"
BUILD_INFO_NAME = "BUILD-INFO.txt"
DEFENDER_DETECTED = "Defender reported a detection in the bundle (C10: never an exclusion)"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
MANIFEST_VERSION = 1
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
# A manifest path: forward slashes, relative, no dot segments, and nothing an
# Inno Setup script would read as a constant or a quote.
_MANIFEST_PATH_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]*$")
WHISPER_PACK_SUFFIXES = (".bin", ".json", ".txt")


class ReleaseError(RuntimeError):
    """A release step refused; the message names what and why."""


# --- this checkout's app package (the pins, identity, layout) ---------------------------


def _use_this_checkout() -> None:
    """Import ``scribe_desktop`` from this checkout's source, so the build
    environment (which installs the app's dependencies, not the app) and a
    plain interpreter read the same pins."""
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))


def _load_setup_models() -> ModuleType:
    path = REPO / "scripts" / "setup-models.py"
    spec = importlib.util.spec_from_file_location("setup_models_for_release", path)
    if spec is None or spec.loader is None:
        raise ReleaseError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def app_version() -> str:
    """D12: desktop/pyproject.toml's version, the one source."""
    version = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ReleaseError(f"version {version!r} is not X.Y.Z")
    return str(version)


# --- the models manifest (Task 3.3) -----------------------------------------------------


@dataclass(frozen=True)
class ModelPins:
    """What the manifest checks the models against: the runtime's and the
    setup script's existing pins (one source each)."""

    silero_path: str
    silero_sha256: str
    speaker_path: str
    speaker_size: int
    speaker_sha256: str
    language_path: str
    language_size: int
    language_sha256: str
    attribution_path: str
    attribution_source: Path


def model_pins() -> ModelPins:
    _use_this_checkout()
    from scribe_desktop import language_model, speaker_embedding

    setup_models = _load_setup_models()
    speaker = f"{speaker_embedding.SPEAKER_MODEL_SUBDIR}/{speaker_embedding.SPEAKER_MODEL_NAME}"
    return ModelPins(
        silero_path="silero-vad/silero_vad.onnx",
        silero_sha256=setup_models.SILERO_VAD_SHA256,
        speaker_path=f"{speaker}.onnx",
        speaker_size=speaker_embedding.SPEAKER_MODEL_SIZE_BYTES,
        speaker_sha256=speaker_embedding.SPEAKER_MODEL_SHA256,
        language_path=f"{language_model.LANGUAGE_MODEL_SUBDIR}/"
        f"{language_model.LANGUAGE_MODEL_FILENAME}",
        language_size=language_model.LANGUAGE_MODEL_SIZE_BYTES,
        language_sha256=language_model.LANGUAGE_MODEL_SHA256,
        attribution_path=f"{speaker_embedding.SPEAKER_MODEL_SUBDIR}/ATTRIBUTION.txt",
        attribution_source=ATTRIBUTION_SOURCE,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(path: str, file: Path) -> dict[str, Any]:
    return {"path": path, "size": file.stat().st_size, "sha256": sha256_file(file)}


def _whisper_files(models: Path) -> list[str]:
    _use_this_checkout()
    # H.3 SIMP-001: the pack ships the app's own default model, named once.
    from scribe_desktop.benchmark import SHIPPED_WHISPER_MODEL, whisper_snapshot_missing

    folder = models / "whisper" / SHIPPED_WHISPER_MODEL
    missing = whisper_snapshot_missing(folder)
    if missing:
        raise ReleaseError(
            f"whisper/{SHIPPED_WHISPER_MODEL} is incomplete ({', '.join(missing)}); "
            f"fetch it with scripts/setup-models.py --only {SHIPPED_WHISPER_MODEL}"
        )
    found = []
    for file in sorted(folder.rglob("*")):
        relative = file.relative_to(models)
        # huggingface_hub's own bookkeeping (.cache) is never part of the model.
        if not file.is_file() or any(part.startswith(".") for part in relative.parts):
            continue
        if file.suffix in WHISPER_PACK_SUFFIXES:
            found.append(relative.as_posix())
    return found


def build_manifest(models: Path, pins: ModelPins | None = None) -> dict[str, Any]:
    """The manifest of the pack's files under ``models`` — read only. Every
    pinned file must match its pin; whisper ``medium`` (pinned by commit
    only, no per-file hashes) must be complete."""
    pins = pins or model_pins()

    def pinned(path: str, size: int | None, sha256: str) -> dict[str, Any]:
        file = models / path
        if not file.is_file():
            raise ReleaseError(f"{path} is missing under {models}")
        entry = _entry(path, file)
        if size is not None and entry["size"] != size:
            raise ReleaseError(f"{path} is {entry['size']} bytes, not the pinned {size}")
        if entry["sha256"] != sha256:
            raise ReleaseError(f"{path} does not match its pinned SHA-256")
        return entry

    files = [
        pinned(pins.silero_path, None, pins.silero_sha256),
        pinned(pins.speaker_path, pins.speaker_size, pins.speaker_sha256),
        pinned(pins.language_path, pins.language_size, pins.language_sha256),
        _entry(pins.attribution_path, pins.attribution_source),
        *(_entry(path, models / path) for path in _whisper_files(models)),
    ]
    manifest = {"version": MANIFEST_VERSION, "files": sorted(files, key=lambda f: f["path"])}
    validate_manifest(manifest)
    return manifest


def manifest_bytes(manifest: Mapping[str, Any]) -> bytes:
    """The manifest's one canonical form — what ``--write-manifest`` writes
    and what its digest is taken over (so a checkout's line endings never
    change the pack's name)."""
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manifest_sha256(manifest: Mapping[str, Any]) -> str:
    return hashlib.sha256(manifest_bytes(manifest)).hexdigest()


def validate_manifest(manifest: Any) -> None:
    if not isinstance(manifest, dict) or set(manifest) != {"version", "files"}:
        raise ReleaseError("the manifest must hold exactly 'version' and 'files'")
    if manifest["version"] != MANIFEST_VERSION:
        raise ReleaseError(f"manifest version {manifest['version']!r} is not {MANIFEST_VERSION}")
    files = manifest["files"]
    if not isinstance(files, list) or not files:
        raise ReleaseError("the manifest lists no files")
    paths = []
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "size", "sha256"}:
            raise ReleaseError(f"manifest entry {entry!r} is not path, size and sha256")
        path, size, digest = entry["path"], entry["size"], entry["sha256"]
        parts = PurePosixPath(path).parts if isinstance(path, str) else ()
        if (
            not isinstance(path, str)
            or len(parts) < 2
            or "\\" in path
            or path.startswith("/")
            or str(PurePosixPath(path)) != path
            or not all(_MANIFEST_PATH_PART.match(part) for part in parts)
        ):
            raise ReleaseError(f"manifest path {path!r} is not a plain relative model path")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ReleaseError(f"manifest size for {path} is not a byte count")
        if not isinstance(digest, str) or not _HEX64.match(digest):
            raise ReleaseError(f"manifest SHA-256 for {path} is not 64 lowercase hex")
        paths.append(path)
    if paths != sorted(set(paths)):
        raise ReleaseError("manifest paths must be unique and sorted")


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    # The default is read at call time, never bound at definition, so a test's
    # stand-in for MANIFEST_PATH is the one every caller loads (C6).
    if path is None:
        path = MANIFEST_PATH
    if not path.is_file():
        raise ReleaseError(
            f"{path.relative_to(REPO) if path.is_relative_to(REPO) else path} does not exist; "
            "write it first with --write-manifest (Task 3.3)"
        )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    return dict(manifest)


def model_pack_name(manifest: Mapping[str, Any]) -> str:
    _use_this_checkout()
    from scribe_desktop import install_layout

    return install_layout.model_pack_name(manifest_sha256(manifest))


# --- the model pack (Task 3.5 --model-pack) ---------------------------------------------


def _check_file(file: Path, entry: Mapping[str, Any]) -> None:
    if not file.is_file():
        raise ReleaseError(f"{entry['path']} is missing ({file})")
    if file.stat().st_size != entry["size"]:
        raise ReleaseError(f"{entry['path']} is not {entry['size']} bytes ({file})")
    if sha256_file(file) != entry["sha256"]:
        raise ReleaseError(f"{entry['path']} does not match the manifest's SHA-256 ({file})")


def make_model_pack(
    models: Path, out: Path, manifest: Mapping[str, Any], pins: ModelPins | None = None
) -> Path:
    """Copy exactly the manifest's files into ``out / <pack name>``. Every
    source is checked first, so a refusal writes nothing; every copy is
    checked again."""
    pins = pins or model_pins()
    pack = out / model_pack_name(manifest)
    if pack.exists():
        raise ReleaseError(f"{pack} already exists; remove it or choose another --out")

    def source(entry: Mapping[str, Any]) -> Path:
        if entry["path"] == pins.attribution_path:
            return pins.attribution_source
        return models.joinpath(*PurePosixPath(entry["path"]).parts)

    for entry in manifest["files"]:
        _check_file(source(entry), entry)
    for entry in manifest["files"]:
        target = pack.joinpath(*PurePosixPath(entry["path"]).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source(entry), target)
        _check_file(target, entry)
    return pack


# --- the bundle audit (Task 3.5 --audit) ------------------------------------------------


def is_qt_network_file(relative: PurePosixPath | PureWindowsPath | Path) -> bool:
    """Whether a bundled file is Qt networking: a Qt module or library whose
    name says network or websockets (``Qt6Network.dll``, ``Qt6NetworkAuth``,
    ``Qt6QmlNetwork``, ``QtNetwork.pyd``, ``Qt6WebSockets.dll``, ...), or a
    plugin from Qt's ``tls`` or ``networkinformation`` folders. The same
    rule as packaging/scribe.spec's filter (pinned equal by test)."""
    parts = [part.lower() for part in relative.parts]
    name = parts[-1] if parts else ""
    if name.startswith("qt") and ("network" in name or "websocket" in name):
        return True
    return "plugins" in parts and any(p in {"tls", "networkinformation"} for p in parts)


@dataclass
class Completed:
    returncode: int
    stdout: str = ""
    stderr: str = ""


Runner = Callable[..., Completed]

# Round 23: the return code ``_run`` reports when a command was stopped at its
# time limit (``subprocess.run`` kills it) — no real process exits with it.
TIMED_OUT = -999
# A frozen app that fails at start shows the windowed bootloader's error box,
# which nobody clicks on a build runner; the self-check is bounded instead.
SELF_CHECK_TIMEOUT_S = 120


def _run(
    command: Sequence[str | os.PathLike[str]],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    capture: bool = False,
    timeout: float | None = None,
) -> Completed:
    try:
        result = subprocess.run(  # noqa: S603 - fixed argv lists built here
            [str(part) for part in command],
            cwd=cwd,
            env=None if env is None else dict(env),
            check=False,
            capture_output=capture,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return Completed(TIMED_OUT)
    except OSError as exc:
        # Round 23: a tool that is not there (ISCC, git, …) is a refusal with
        # its name, never a raw traceback.
        raise ReleaseError(
            f"could not start {command[0]} ({exc.strerror or type(exc).__name__}); "
            "is it installed, and is the path right?"
        ) from exc
    return Completed(result.returncode, result.stdout or "", result.stderr or "")


def audit_bundle(bundle: Path, run: Runner = _run) -> list[str]:
    """Every audit failure of the PyInstaller bundle at ``bundle`` (empty:
    passed)."""
    failures: list[str] = []
    for exe in (APP_EXE, HOST_EXE):
        if not (bundle / exe).is_file():
            failures.append(f"{exe} is missing")
    internal = bundle / INTERNAL
    defaults = sorted((SRC / "scribe_desktop" / "config_defaults").glob("*.json"))
    for file in defaults:
        if not (internal / "scribe_desktop" / "config_defaults" / file.name).is_file():
            failures.append(f"the shipped config {file.name} is missing")
    for folder in NATIVE_LIBRARY_DIRS:
        if not list((internal / folder).glob("*.dll")):
            failures.append(f"no native library in {INTERNAL}/{folder}")
    if bundle.is_dir():
        for file in sorted(bundle.rglob("*")):
            relative = file.relative_to(bundle)
            if file.is_file() and is_qt_network_file(relative):
                failures.append(f"Qt networking is bundled: {relative.as_posix()}")
    if (bundle / APP_EXE).is_file():
        result = run(
            [bundle / APP_EXE, SELF_CHECK_FLAG],
            env=dict(os.environ) | dict(HOSTILE_ENV),
            timeout=SELF_CHECK_TIMEOUT_S,
        )
        if result.returncode == TIMED_OUT:
            failures.append(
                f"the offline self-check did not finish within {SELF_CHECK_TIMEOUT_S} s "
                "(a start-up error box waiting for a click?)"
            )
        elif result.returncode != 0:
            failures.append(
                f"the offline self-check exited {result.returncode} "
                "(1: the offline variables; 2: a Qt networking module is importable)"
            )
    return failures


def defender_scan(bundle: Path, run: Runner = _run) -> str:
    """``clean``, ``detected`` or ``not run`` — a Defender custom scan of the
    bundle, then the detections that name it. Where Defender cannot run (no
    module, not permitted) the scan is reported as not run, never as clean."""
    folder = str(bundle)
    # H.4 SEC-004: PowerShell also ends a single-quoted string at the curly
    # single quotes U+2018–U+201B, so they are refused with the plain one.
    if any(quote in folder for quote in "'‘’‚‛"):
        return "not run (the path holds a quote)"
    script = (
        f"Start-MpScan -ScanType CustomScan -ScanPath '{folder}' -ErrorAction Stop; "
        "$found = Get-MpThreatDetection -ErrorAction Stop | Where-Object "
        f"{{ \"$($_.Resources)\" -match [regex]::Escape('{folder}') }}; "
        "if ($found) { exit 3 } else { exit 0 }"
    )
    result = run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script])
    if result.returncode == 0:
        return "clean"
    if result.returncode == 3:
        return "detected"
    return f"not run (exit {result.returncode})"


def audit_extension(folder: Path) -> list[str]:
    """The release extension: present, the release build (not the dev
    channel's name or host)."""
    _use_this_checkout()
    from scribe_desktop import identity

    manifest = folder / "manifest.json"
    if not manifest.is_file():
        return ["the extension's manifest.json is missing"]
    failures = []
    if "(dev)" in json.loads(manifest.read_text(encoding="utf-8")).get("name", ""):
        failures.append("the extension is the dev build")
    texts = [p.read_bytes() for p in folder.rglob("*") if p.is_file()]
    if any(identity.DEV_HOST_NAME.encode() in text for text in texts):
        failures.append("the extension names the dev host")
    if not any(identity.HOST_NAME.encode() in text for text in texts):
        failures.append("the extension does not name the installed host")
    return failures


# --- the installer's inputs ----------------------------------------------------------


def host_manifest() -> dict[str, object]:
    """The installed Chrome link's manifest (production identities, C2), at
    the D-I1 install folder — beside scribe-host.exe in the bundle."""
    _use_this_checkout()
    from scribe_desktop import identity, install_layout

    return {
        "name": identity.host_name("production"),
        "description": "Clinic Scribe Chrome link",
        "path": str(PureWindowsPath(install_layout.INSTALL_ROOTS[0]) / HOST_EXE),
        "type": "stdio",
        "allowed_origins": [identity.expected_origin("production")],
    }


def host_manifest_name() -> str:
    _use_this_checkout()
    from scribe_desktop import identity

    return f"{identity.host_name('production')}.json"


def inno_includes(manifest: Mapping[str, Any], pack: str) -> tuple[str, str]:
    """The two files packaging/scribe.iss includes: the ``[Files]`` entries
    that copy each model from the pack beside setup.exe, and the ``[Code]``
    procedure that lists each model's SHA-256 for the install-time check."""
    validate_manifest(manifest)
    files = ["; GENERATED by scripts/build-release.py from packaging/models-manifest.json"]
    code = [
        "// GENERATED by scripts/build-release.py from packaging/models-manifest.json",
        "procedure AddModelFiles();",
        "begin",
    ]
    for entry in manifest["files"]:
        windows = str(PureWindowsPath(*PurePosixPath(entry["path"]).parts))
        folder = str(PureWindowsPath(windows).parent)
        files.append(
            f'Source: "{{src}}\\{pack}\\{windows}"; DestDir: "{{app}}\\models\\{folder}"; '
            "Flags: external ignoreversion; Check: ModelsNeedCopy"
        )
        code.append(f"  AddModelFile('{windows}', '{entry['sha256']}');")
    code.append("end;")
    return "\n".join(files) + "\n", "\n".join(code) + "\n"


def write_sums(folder: Path) -> Path:
    """``SHA256SUMS.txt`` (``<sha256>  <name>``, sha256sum's format) over
    every other file in ``folder``."""
    lines = [
        f"{sha256_file(file)}  {file.name}"
        for file in sorted(folder.iterdir())
        if file.is_file() and file.name != SUMS_NAME
    ]
    sums = folder / SUMS_NAME
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sums


# --- the build: stage one (clean environment, PyInstaller from source) -------------------


def _venv_python(out: Path) -> Path:
    return out / "build-venv" / "Scripts" / "python.exe"


def _must(result: Completed, what: str) -> Completed:
    if result.returncode != 0:
        raise ReleaseError(f"{what} failed (exit {result.returncode})")
    return result


def preflight(
    pyinstaller_src: Path,
    out: Path,
    *,
    run: Runner = _run,
    version_info: Sequence[int] = sys.version_info,
    platform: str = sys.platform,
) -> None:
    if platform != "win32":
        raise ReleaseError("a release is built on Windows")
    if tuple(version_info[:2]) != BUILD_PYTHON:
        raise ReleaseError(
            f"build with Python {BUILD_PYTHON[0]}.{BUILD_PYTHON[1]} (Task 0.1's interpreter), "
            f"not {version_info[0]}.{version_info[1]}"
        )
    if not LOCK.is_file():
        raise ReleaseError(
            "desktop/requirements-build.txt does not exist; generate it with "
            "scripts/lock-build-requirements.py (Task 3.1)"
        )
    # Round 31: the source is installed without build isolation, so its build
    # backend must come from the lock — checked here, before any install.
    lock_text = LOCK.read_text(encoding="utf-8")
    locked = {
        _normalise(m.group(1))
        for m in re.finditer(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==", lock_text, re.MULTILINE)
    }
    for name in PYINSTALLER_BUILD_REQUIRES:
        if name not in locked:
            raise ReleaseError(
                f"desktop/requirements-build.txt lacks {name}, the build backend of "
                "PyInstaller's source; generate the lock again with "
                "scripts/lock-build-requirements.py (Task 3.1)"
            )
    load_manifest()  # the installer compiles its hashes in
    if out.exists() and any(out.iterdir()):
        raise ReleaseError(f"{out} is not empty; a release builds into an empty folder")
    head = run(["git", "-C", pyinstaller_src, "rev-parse", "HEAD"], capture=True)
    if head.returncode != 0 or head.stdout.strip() != PYINSTALLER_COMMIT:
        raise ReleaseError(
            f"{pyinstaller_src} is not PyInstaller {PYINSTALLER_VERSION} at commit "
            f"{PYINSTALLER_COMMIT}"
        )
    # Round 20 PR-HIGH-001: the pin is the SOURCE, not only its commit — a
    # changed, extra or ignored file (an earlier bootloader build's output
    # among them) would be built into the release. Checked here, before waf,
    # which rewrites the tracked bootloader.
    status = run(
        [
            "git", "-C", pyinstaller_src,
            "status", "--porcelain", "--untracked-files=all", "--ignored",
        ],
        capture=True,
    )
    if status.returncode != 0 or status.stdout.strip():
        raise ReleaseError(
            f"{pyinstaller_src} has local changes or extra files (an earlier build's among "
            f"them); clone it again into an empty folder: {PYINSTALLER_CLONE}"
        )
    declared = pyinstaller_build_requires(pyinstaller_src)
    if not set(declared) <= set(PYINSTALLER_BUILD_REQUIRES):
        raise ReleaseError(
            f"PyInstaller's source declares the build requirements {', '.join(declared)}, "
            f"but this build expects only {', '.join(PYINSTALLER_BUILD_REQUIRES)}: add the new "
            "ones to PYINSTALLER_BUILD_REQUIRES and the lock's build-tool pins (Task 3.1)"
        )


def _normalise(name: str) -> str:
    """PEP 503 name normalisation (the lock script's rule)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def pyinstaller_build_requires(pyinstaller_src: Path) -> list[str]:
    """The normalised names in the source's ``[build-system] requires``. A
    source with no readable pyproject is refused, never taken as needing
    nothing."""
    pyproject = pyinstaller_src / "pyproject.toml"
    try:
        requires = tomllib.loads(pyproject.read_text(encoding="utf-8"))["build-system"][
            "requires"
        ]
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        raise ReleaseError(
            f"{pyproject} does not declare its build requirements ({type(exc).__name__})"
        ) from exc
    names = []
    for requirement in requires:
        match = _REQUIREMENT_NAME.match(requirement) if isinstance(requirement, str) else None
        if match is None:
            raise ReleaseError(f"{pyproject} has a build requirement that is not a name")
        names.append(_normalise(match.group(1)))
    return names


def stage_one(
    pyinstaller_src: Path,
    out: Path,
    iscc: Path,
    *,
    defender: bool,
    run: Runner = _run,
) -> None:
    preflight(pyinstaller_src, out, run=run)
    out.mkdir(parents=True, exist_ok=True)
    python = _venv_python(out)
    _must(run([sys.executable, "-m", "venv", out / "build-venv"]), "making the build venv")
    pip = [python, "-m", "pip", "install", "--require-hashes", "--no-deps", "-r"]
    _must(run([*pip, LOCK]), "installing the build lock")
    _must(run([*pip, PROSE_LOCK]), "installing the prose runtime wheel")
    _must(
        run([python, "./waf", "all", "--target-arch=64bit"], cwd=pyinstaller_src / "bootloader"),
        "building the bootloader (needs the C++ build tools)",
    )
    if sha256_file(pyinstaller_src / RUNW) == SHIPPED_RUNW_SHA256:
        raise ReleaseError("the windowed bootloader was not rebuilt (it is still the shipped one)")
    _must(
        run([python, "-m", "pip", "install", "--no-deps", "--no-build-isolation", pyinstaller_src]),
        "installing PyInstaller from its source",
    )
    _must(run([python, "-m", "pip", "check"]), "pip check")
    stage_two_args = [python, Path(__file__).resolve(), "--continue-build", "--out", out]
    stage_two_args += ["--iscc", iscc] + ([] if defender else ["--no-defender"])
    _must(run(stage_two_args), "the build's second stage")


# --- the build: stage two (in the build environment) -------------------------------------


def build_extension(target: Path, run: Runner = _run) -> None:
    if target.exists():
        raise ReleaseError(f"{target} already exists")
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    _must(run([npm, "ci"], cwd=EXTENSION), "npm ci")
    _must(run([npm, "run", "build", "--", "--mode", "release"], cwd=EXTENSION), "the extension build")
    shutil.copytree(EXTENSION / "dist", target)


def compile_installer(
    bundle: Path, work: Path, out: Path, iscc: Path, run: Runner = _run
) -> Path:
    manifest = load_manifest()
    pack = model_pack_name(manifest)
    files_text, code_text = inno_includes(manifest, pack)
    includes = work / "installer"
    includes.mkdir(parents=True, exist_ok=True)
    (includes / "models-files.iss").write_text(files_text, encoding="utf-8")
    (includes / "models-code.iss").write_text(code_text, encoding="utf-8")
    installer = out / "installer"
    installer.mkdir(parents=True, exist_ok=False)
    result = run(
        [
            iscc,
            f"/DAppVersion={app_version()}",
            f"/DDistDir={bundle}",
            f"/DModelPackDir={pack}",
            f"/DModelsFiles={includes / 'models-files.iss'}",
            f"/DModelsCode={includes / 'models-code.iss'}",
            f"/O{installer}",
            ISS,
        ],
        capture=True,
    )
    if result.returncode != 0 or INNO_BANNER not in result.stdout:
        # The output was captured for the banner check: show it, or a refused
        # compile would say only its exit code (the build's own files only —
        # paths and script lines, never a person's data).
        sys.stderr.write(result.stdout + result.stderr)
    _must(result, "Inno Setup")
    if INNO_BANNER not in result.stdout:
        for stray in installer.iterdir():
            stray.unlink()
        raise ReleaseError(f"the installer was not compiled by Inno Setup {INNO_VERSION}")
    setups = sorted(installer.glob("*.exe"))
    if len(setups) != 1:
        raise ReleaseError(f"expected one setup program, found {len(setups)}")
    shutil.copyfile(MANIFEST_PATH, installer / MANIFEST_PATH.name)
    return setups[0]


def source_state(run: Runner = _run) -> tuple[str, str]:
    """Round 20 (PR-HIGH-001's sibling): ``(commit, tree)`` of THIS checkout,
    recorded with every build — the commit, and ``clean`` or ``DIRTY`` (or
    ``unknown`` where git cannot say). Recorded, not refused: D7's local
    builds serve spikes and the model pack, which may carry uncommitted work;
    the build of record is CI's clean checkout."""
    head = run(["git", "-C", REPO, "rev-parse", "HEAD"], capture=True)
    commit = head.stdout.strip() if head.returncode == 0 else ""
    status = run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture=True)
    if status.returncode != 0:
        tree = "unknown"
    else:
        tree = "DIRTY" if status.stdout.strip() else "clean"
    return (commit if _HEX40.match(commit) else "unknown"), tree


def write_build_info(folder: Path, commit: str, tree: str) -> Path:
    """``BUILD-INFO.txt`` beside the setup program (and so in its sums): the
    version, the commit and whether the tree was clean."""
    info = folder / BUILD_INFO_NAME
    info.write_text(
        f"version={app_version()}\ncommit={commit}\ntree={tree}\n", encoding="utf-8"
    )
    return info


def stage_two(out: Path, iscc: Path, *, defender: bool, run: Runner = _run) -> int:
    commit, tree = source_state(run)
    dist, work = out / "dist", out / "work"
    _must(
        run(
            [
                sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                "--distpath", dist, "--workpath", work, SPEC,
            ]
        ),
        "PyInstaller",
    )
    bundle = dist / COLLECT_NAME
    (bundle / host_manifest_name()).write_text(
        json.dumps(host_manifest(), indent=2) + "\n", encoding="utf-8"
    )
    # H.4 SEC-001: the extension's build (third-party npm code, with write
    # access to the bundle) runs BEFORE the bundle audit, so nothing it could
    # change in the program goes unaudited into the installer.
    build_extension(bundle / "extension", run)
    failures = audit_bundle(bundle, run)
    failures += audit_extension(bundle / "extension")
    if failures:
        raise ReleaseError("the bundle audit failed: " + "; ".join(failures))
    scan = defender_scan(bundle, run) if defender else "not run (--no-defender)"
    if scan == "detected":
        raise ReleaseError(DEFENDER_DETECTED)
    setup = compile_installer(bundle, work, out, iscc, run)
    write_build_info(setup.parent, commit, tree)
    write_sums(setup.parent)
    print(f"version  : {app_version()}")
    print(f"source   : {commit} ({tree})")
    if tree != "clean":
        print("WARNING  : not built from a clean checkout - never the build of record (D7)")
    print(f"installer: {setup}")
    print(f"sha256   : {sha256_file(setup)}")
    print(f"models   : {model_pack_name(load_manifest())} (manifest {MANIFEST_PATH.name})")
    print(f"defender : {scan}")
    return 0


# --- the command line ----------------------------------------------------------------


def _print_failures(title: str, failures: Sequence[str]) -> int:
    for failure in failures:
        print(f"FAIL     : {failure}")
    print(f"{title}: {'FAIL' if failures else 'OK'}")
    return 1 if failures else 0


def main(argv: Sequence[str] | None = None, *, run: Runner = _run) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write-manifest", action="store_true", help="write the models manifest")
    mode.add_argument("--model-pack", action="store_true", help="make the model pack")
    mode.add_argument("--audit", type=Path, metavar="DIST", help="audit a PyInstaller bundle")
    mode.add_argument("--continue-build", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--models", type=Path, help="the models folder (read only)")
    parser.add_argument("--out", type=Path, help="an empty output folder")
    parser.add_argument("--pyinstaller-src", type=Path, help="PyInstaller's source checkout")
    parser.add_argument("--iscc", type=Path, default=DEFAULT_ISCC, help="Inno Setup's ISCC.exe")
    parser.add_argument("--no-defender", action="store_true", help="skip the Defender scan")
    args = parser.parse_args(argv)
    try:
        if args.write_manifest:
            if args.models is None:
                parser.error("--write-manifest needs --models")
            manifest = build_manifest(args.models)
            MANIFEST_PATH.write_bytes(manifest_bytes(manifest))
            print(f"wrote {MANIFEST_PATH} ({len(manifest['files'])} files)")
            print(f"pack name: {model_pack_name(manifest)}")
            return 0
        if args.model_pack:
            if args.models is None or args.out is None:
                parser.error("--model-pack needs --models and --out")
            pack = make_model_pack(args.models, args.out, load_manifest())
            print(f"model pack: {pack} (verified against {MANIFEST_PATH.name})")
            return 0
        if args.audit is not None:
            code = _print_failures("audit", audit_bundle(args.audit, run))
            if not args.no_defender:
                scan = defender_scan(args.audit, run)
                print(f"defender : {scan}")
                # Round 20 PR-HIGH-002: a detection fails the audit, as it
                # fails the build (stage_two).
                if scan == "detected":
                    print(f"FAIL     : {DEFENDER_DETECTED}")
                    code = 1
            return code
        if args.out is None:
            parser.error("the build needs --out")
        if args.continue_build:
            return stage_two(args.out, args.iscc, defender=not args.no_defender, run=run)
        if args.pyinstaller_src is None:
            parser.error("the build needs --pyinstaller-src")
        stage_one(args.pyinstaller_src, args.out, args.iscc, defender=not args.no_defender, run=run)
        return 0
    except ReleaseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
