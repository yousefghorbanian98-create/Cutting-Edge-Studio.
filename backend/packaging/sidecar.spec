# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the backend sidecar (onedir, no console window).

PyInstaller is GPLv2+ with the bootloader exception — explicitly whitelisted
for this project (protocol v2.5.1, §20).
"""

from pathlib import Path

import sys

block_cipher = None
root = Path(SPECPATH).resolve().parents[1]  # backend/
sys.path.insert(0, str(root))

a = Analysis(
    [str(root / "app" / "__main__.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[],
    # Heavy OSS wheels are imported lazily by adapters, so they are collected
    # explicitly only when the corresponding feature is packaged.
    hiddenimports=["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "ruff", "mypy"],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="cutting-edge-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="cutting-edge-backend",
)
