# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the backend sidecar (one file, no console window).

PyInstaller is GPLv2+ with the bootloader exception — explicitly whitelisted
for this project (protocol v2.5.1, §20).
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
root = Path(SPECPATH).resolve().parent  # SPECPATH is backend/packaging -> repo backend/
sys.path.insert(0, str(root))

a = Analysis(
    [str(root / "app" / "__main__.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "app" / "schemas_json"), "app/schemas_json")],
    # Heavy OSS wheels are imported lazily by adapters, so they are collected
    # explicitly only when the corresponding feature is packaged.
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        *collect_submodules("uvicorn"),
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "ruff", "mypy", "matplotlib", "PIL"],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="cutting-edge-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
# One-file build: Tauri's `externalBin` copies exactly one executable next to the
# shell, so a onedir COLLECT tree would be silently dropped from the installer.
