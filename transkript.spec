# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for transkript

import os
import sys
from pathlib import Path

block_cipher = None

# Find textual CSS files
src_dir = Path('src/transkript')
css_files = [(str(src_dir / 'styles' / 'app.tcss'), 'transkript/styles')]

# Find faster_whisper assets (VAD ONNX model)
import importlib
try:
    fw_path = Path(importlib.import_module('faster_whisper').__file__).parent
    fw_assets = str(fw_path / 'assets' / '*')
except Exception:
    fw_assets = ''

a = Analysis(
    ['src/transkript/__main__.py'],
    pathex=[],
    binaries=[],
    datas=css_files + ([(fw_assets, 'faster_whisper/assets')] if fw_assets else []),
    hiddenimports=[
        'transkript.app',
        'transkript.audio',
        'transkript.transcriber',
        'textual',
        'sounddevice',
        'faster_whisper',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='transkript',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='transkript',
)
