# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the standalone TouchKeys application."""

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules


PROJECT_DIR = Path(SPECPATH)
VGAMEPAD_DIR = PROJECT_DIR / ".venv" / "Lib" / "site-packages" / "vgamepad"

a = Analysis(
    [str(PROJECT_DIR / "backend" / "gui.py")],
    pathex=[str(PROJECT_DIR)],
    datas=[
        (str(PROJECT_DIR / "templates"), "templates"),
        (str(PROJECT_DIR / "static"), "static"),
        (str(PROJECT_DIR / "controller" / "default_gamepad.json"), "controller"),
        *collect_data_files("webview"),
    ],
    binaries=[
        (str(VGAMEPAD_DIR / "win" / "vigem" / "client" / "x64" / "ViGEmClient.dll"), "vgamepad/win/vigem/client/x64"),
        (str(VGAMEPAD_DIR / "win" / "vigem" / "client" / "x86" / "ViGEmClient.dll"), "vgamepad/win/vigem/client/x86"),
    ],
    hiddenimports=[
        *collect_submodules("backend"),
        *collect_submodules("controller"),
        *collect_submodules("uvicorn"),
        *collect_submodules("webview"),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="TouchKeys_v3.1",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_DIR / "static" / "favicon.png"),
)
