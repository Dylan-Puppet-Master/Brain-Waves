"""PyInstaller build: one file per platform, named for the platform it runs on.

    pyinstaller brainwaves.spec

The name carries the platform because `brainwaves.update` picks the release asset whose
name mentions the platform it is running on.
"""

import sys
from pathlib import Path

PLATFORM = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
ICON = {"win32": Path("build/icon.ico"), "darwin": Path("build/icon.icns")}.get(sys.platform)

analysis = Analysis(  # noqa: F821 - PyInstaller injects these names
    ["brainwaves/__main__.py"],
    pathex=["."],
    hiddenimports=["brainwaves.app.main"],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.Qt3DCore", "matplotlib", "numpy"],
    noarchive=False,
)
archive = PYZ(analysis.pure)  # noqa: F821

executable = EXE(  # noqa: F821
    archive,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    name=f"brainwaves-{PLATFORM}",
    console=False,
    onefile=True,
    upx=False,
    icon=str(ICON) if ICON else None,
)
