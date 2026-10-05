# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

root_dir = Path.cwd().resolve()

# Bundled data files
datas = [
    (str(root_dir / 'frontend'), 'frontend'),
    (str(root_dir / 'backend' / 'app'), 'backend/app'),
]

# Collect package data files (e.g. imageio-ffmpeg binaries, yt-dlp metadata)
try:
    datas += collect_data_files('imageio_ffmpeg')
except Exception:
    pass

try:
    datas += collect_data_files('yt_dlp')
except Exception:
    pass

# Explicit hidden imports for FastAPI, Uvicorn, Starlette, and dependencies
hiddenimports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.protocols.websockets.wsproto_impl',
    'uvicorn.lifespan',
    'uvicorn.lifespan.auto',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'h11',
    'fastapi',
    'fastapi.staticfiles',
    'starlette',
    'starlette.routing',
    'starlette.responses',
    'starlette.middleware',
    'starlette.staticfiles',
    'sse_starlette',
    'sse_starlette.sse',
    'pydantic',
    'pydantic_core',
    'anyio',
    'anyio._backends._asyncio',
    'multipart',
    'python_multipart',
    'platformdirs',
    'requests',
    'imageio_ffmpeg',
    'ctypes',
    'ctypes.wintypes',
]

# Dynamically collect submodules for comprehensive bundling
for pkg in ['uvicorn', 'fastapi', 'starlette', 'sse_starlette', 'yt_dlp', 'platformdirs']:
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

hiddenimports = sorted(list(set(hiddenimports)))

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
