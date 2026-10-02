# -*- mode: python ; coding: utf-8 -*-
# Installation plan Task 0.1 SPIKE — throwaway. NOT the build of record
# (that is packaging/scribe.spec, Task 3.2, one COLLECT with two EXEs).
#
# One-folder, WINDOWED scribe-app.exe whose entry is spike_app_entry.py, which
# runs the real scribe_desktop.app.main (plus the spike's guard, checks and
# benchmark-worker dispatch). No UPX. Build from the repo root, from a NORMAL
# PowerShell (packaging/spike/RUNBOOK.md, Task 0.1):
#
#   .venv\Scripts\pyinstaller.exe --noconfirm --distpath C:\scribe-spike\dist
#       --workpath C:\scribe-spike\build packaging\spike\scribe.spec
#
# Output: C:\scribe-spike\dist\scribe-app\scribe-app.exe (outside the repo).

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

SPIKE = Path(SPECPATH)  # noqa: F821 - provided by PyInstaller
REPO = SPIKE.parents[1]
SRC = REPO / "desktop" / "src"

# Package data the app reads through importlib.resources (config_defaults/*.json)
# and the ML stack's own data files.
datas = []
datas += collect_data_files("scribe_desktop")
datas += collect_data_files("faster_whisper")
# keyring discovers its backends through entry points: without its metadata a
# frozen app can silently fall back to a non-Windows backend (Task 0.1 check).
datas += copy_metadata("keyring")

# Native libraries loaded by path/ctypes rather than by import tracing.
binaries = []
binaries += collect_dynamic_libs("ctranslate2")
binaries += collect_dynamic_libs("onnxruntime")
binaries += collect_dynamic_libs("llama_cpp")  # llama_cpp/lib/*.dll

hiddenimports = []
hiddenimports += collect_submodules("scribe_desktop")
hiddenimports += [
    "keyring.backends.Windows",
    "win32com.client",
    "win32timezone",
    "spike_checks",
]

# The offline contract: no Qt networking in the bundle (Task 0.1 check).
excludes = [
    "PySide6.QtNetwork",
    "PySide6.QtWebSockets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "tkinter",
    "pytest",
]

a = Analysis(  # noqa: F821
    [str(SPIKE / "spike_app_entry.py")],
    pathex=[str(SRC), str(SPIKE)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

# Belt and braces for the Qt6Network.dll check: anything a hook still pulled
# in is removed here AND printed, so the build log says which (Task 3.2 input).
_BANNED_PREFIXES = ("qt6network", "qt6websockets")
_kept = []
for entry in a.binaries:
    if Path(entry[0]).name.lower().startswith(_BANNED_PREFIXES):
        print(f"SPIKE-FILTERED {entry[0]} (from {entry[1]})")
    else:
        _kept.append(entry)
a.binaries = _kept

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="scribe-app",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="scribe-app",
)
