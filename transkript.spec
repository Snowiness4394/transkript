# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for transkript

import os
import sys
from pathlib import Path

block_cipher = None

# Find textual CSS files
src_dir = Path('src/transkript')
css_files = [(str(src_dir / 'styles' / 'app.tcss'), 'transkript/styles')]

a = Analysis(
    ['src/transkript/__main__.py'],
    pathex=[],
    binaries=[],
    datas=css_files,
    hiddenimports=[
        'transkript.app',
        'transkript.audio',
        'transkript.transcriber',
        'textual',
        'sounddevice',
        'faster_whisper',
        'numpy',
        'scipy',
        'scipy.signal',
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
    console=True,  # Keep console for Textual TUI
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
