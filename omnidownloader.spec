# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

block_cipher = None

root_dir = Path.cwd().resolve()

# Bundled data files
datas = [
    (str(root_dir / 'frontend'), 'frontend'),
    (str(root_dir / 'backend' / 'app'), 'backend/app'),
]

# Hidden imports for FastAPI, Uvicorn, and yt-dlp dynamic modules
hiddenimports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespans',
    'uvicorn.lifespans.on',
    'fastapi',
    'starlette',
    'sse_starlette',
    'yt_dlp',
    'yt_dlp.extractor',
    'yt_dlp.postprocessor',
    'platformdirs',
    'requests',
    'imageio_ffmpeg',
]

a = Analysis(
    ['launcher.py'],
    pathex=[str(root_dir), str(root_dir / 'backend')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OmniDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed standalone desktop app - no black CMD window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
