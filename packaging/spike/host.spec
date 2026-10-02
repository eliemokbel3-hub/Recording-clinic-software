# -*- mode: python ; coding: utf-8 -*-
# Installation plan Task 0.2 SPIKE — throwaway. NOT the build of record.
#
# One-folder, WINDOWED scribe-host.exe whose entry is spike_host_entry.py,
# which applies the stdio adaptation (a no-op when the streams are present)
# and then runs the real, unchanged scribe_desktop.native_host.main. Built
# with the SAME interpreter Task 0.1 settled on. No UPX. From the repo root,
# from a NORMAL PowerShell (packaging/spike/RUNBOOK.md, Task 0.2):
#
#   .venv\Scripts\pyinstaller.exe --noconfirm --distpath C:\scribe-spike\dist
#       --workpath C:\scribe-spike\build packaging\spike\host.spec
#
# Output: C:\scribe-spike\dist\scribe-host\scribe-host.exe (outside the repo).

from pathlib import Path

SPIKE = Path(SPECPATH)  # noqa: F821 - provided by PyInstaller
REPO = SPIKE.parents[1]
SRC = REPO / "desktop" / "src"

a = Analysis(  # noqa: F821
    [str(SPIKE / "spike_host_entry.py")],
    pathex=[str(SRC), str(SPIKE)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6.QtNetwork", "PySide6.QtWebSockets", "tkinter", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="scribe-host",
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
    name="scribe-host",
)
