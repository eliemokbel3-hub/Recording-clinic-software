# -*- mode: python ; coding: utf-8 -*-
# Installation plan Task 3.2 (D1): THE build of record's PyInstaller spec.
#
# One folder, two WINDOWED programs in ONE COLLECT: scribe-app.exe (the app)
# and scribe-host.exe (Chrome's native host), sharing one _internal folder.
# No UPX. A version resource from desktop/pyproject.toml (D12). Built by
# scripts/build-release.py inside its clean build environment, with
# PyInstaller built from its pinned source (bootloader built here, D1):
#
#   python -m PyInstaller --noconfirm --clean --distpath <out>\dist
#       --workpath <out>\work packaging\scribe.spec
#
# Output: <out>\dist\scribe\ (scribe-app.exe, scribe-host.exe, _internal\).
# Started from Task 0.1's proven spike spec (packaging/spike/scribe.spec);
# what changed and why is on Task 3.2 in the plan.

import tomllib
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

PACKAGING = Path(SPECPATH)  # noqa: F821 - provided by PyInstaller
REPO = PACKAGING.parent
SRC = REPO / "desktop" / "src"
PACKAGE = SRC / "scribe_desktop"

# D12: pyproject is the one version.
VERSION = tomllib.loads((REPO / "desktop" / "pyproject.toml").read_text(encoding="utf-8"))[
    "project"
]["version"]

# Task 0.1: the module search path is the app's source ONLY — the spike's
# had the repository root first, where a stray module could shadow a bundled
# one.
PATHEX = [str(SRC)]

# The app's own modules, enumerated from the source tree (not imported), and
# the shipped default config it reads through importlib.resources.
APP_MODULES = sorted(
    ".".join(path.relative_to(SRC).with_suffix("").parts).removesuffix(".__init__")
    for path in PACKAGE.rglob("*.py")
)
APP_DATAS = [
    (str(path), "scribe_desktop/config_defaults")
    for path in sorted((PACKAGE / "config_defaults").glob("*.json"))
]

# Task 0.1's hidden imports, all needed: the app's modules (native_host and
# speaker_eval among them), keyring's Windows backend (its entry points are
# lost when frozen), win32timezone and win32com.client (SAPI).
HIDDENIMPORTS = [*APP_MODULES, "keyring.backends.Windows", "win32com.client", "win32timezone"]

# The offline contract: no Qt networking in the bundle. Plus Task 0.1's bloat
# that nothing the app runs imports: the type checker the pydantic hook drags
# in, and setuptools (reached only through cffi's build-time integration).
# NOT trimmed, because the app imports them at run time: huggingface_hub and
# av (faster_whisper imports both at module level), httpx/anyio/certifi
# (huggingface_hub's client), jinja2 and sqlite3 (llama_cpp's chat format and
# diskcache), lxml (python-docx).
EXCLUDES = [
    "PySide6.QtNetwork",
    "PySide6.QtWebSockets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "tkinter",
    "pytest",
    "mypy",
    "pydantic.mypy",
    "pydantic.v1.mypy",
    "setuptools",
    "pkg_resources",
    "_distutils_hack",
]

# LOAD-BEARING (Task 0.1): a PySide6 hook adds Qt6Network.dll even with
# PySide6.QtNetwork excluded, so the files themselves are filtered here AND
# the build audit refuses a bundle that still holds one. The rule is
# scripts/build-release.py's ``is_qt_network_file`` (pinned equal by
# desktop/tests/test_build_spec.py): a Qt file whose name says network or
# websockets, or a plugin from Qt's tls / networkinformation folders.
def is_qt_network_file(relative):
    parts = [part.lower() for part in relative.parts]
    name = parts[-1] if parts else ""
    if name.startswith("qt") and ("network" in name or "websocket" in name):
        return True
    return "plugins" in parts and any(p in {"tls", "networkinformation"} for p in parts)


def _without_qt_network(entries):
    kept = []
    for entry in entries:
        if is_qt_network_file(Path(entry[0])):
            print(f"FILTERED {entry[0]} (from {entry[1]})")
        else:
            kept.append(entry)
    return kept


def _version_info(description, filename):
    numbers = tuple(int(part) for part in VERSION.split(".")) + (0,)
    strings = [
        StringStruct("CompanyName", "Clinic Scribe"),
        StringStruct("FileDescription", description),
        StringStruct("FileVersion", VERSION),
        StringStruct("InternalName", filename.removesuffix(".exe")),
        StringStruct("OriginalFilename", filename),
        StringStruct("ProductName", "Clinic Scribe"),
        StringStruct("ProductVersion", VERSION),
    ]
    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=numbers, prodvers=numbers),
        kids=[
            StringFileInfo([StringTable("040904B0", strings)]),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )


app_a = Analysis(  # noqa: F821
    [str(PACKAGING / "entry_app.py")],
    pathex=PATHEX,
    binaries=[
        *collect_dynamic_libs("ctranslate2"),
        *collect_dynamic_libs("onnxruntime"),
        *collect_dynamic_libs("llama_cpp"),
    ],
    datas=[*APP_DATAS, *collect_data_files("faster_whisper"), *copy_metadata("keyring")],
    hiddenimports=HIDDENIMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)
app_a.binaries = _without_qt_network(app_a.binaries)
app_a.datas = _without_qt_network(app_a.datas)

host_a = Analysis(  # noqa: F821
    [str(PACKAGING / "entry_host.py")],
    pathex=PATHEX,
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)
host_a.binaries = _without_qt_network(host_a.binaries)
host_a.datas = _without_qt_network(host_a.datas)

app_pyz = PYZ(app_a.pure)  # noqa: F821
host_pyz = PYZ(host_a.pure)  # noqa: F821

# disable_windowed_traceback=True on both (Phase 2 review round 13 MED-003):
# with False, an exception escaping main shows PyInstaller's windowed box
# with the full traceback, against C3's type-name-only rule.
app_exe = EXE(  # noqa: F821
    app_pyz,
    app_a.scripts,
    [],
    exclude_binaries=True,
    name="scribe-app",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=True,
    version=_version_info("Clinic Scribe", "scribe-app.exe"),
)

host_exe = EXE(  # noqa: F821
    host_pyz,
    host_a.scripts,
    [],
    exclude_binaries=True,
    name="scribe-host",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=True,
    version=_version_info("Clinic Scribe Chrome link", "scribe-host.exe"),
)

coll = COLLECT(  # noqa: F821
    app_exe,
    app_a.binaries,
    app_a.datas,
    host_exe,
    host_a.binaries,
    host_a.datas,
    strip=False,
    upx=False,
    name="scribe",
)
