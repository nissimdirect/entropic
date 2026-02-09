# -*- mode: python ; coding: utf-8 -*-
"""
Entropic — PyInstaller Build Spec
Build with: pyinstaller entropic.spec

Produces: dist/Entropic.app (~81 MB)
"""

import os
import sys
from pathlib import Path

block_cipher = None

# Project root
ROOT = os.path.dirname(os.path.abspath(SPEC))

# Collect all data files
datas = [
    # UI static files
    (os.path.join(ROOT, 'ui'), 'ui'),
    # User presets directory (will be created at runtime if missing)
    (os.path.join(ROOT, 'user_presets'), 'user_presets'),
]

# Collect all effect modules
hiddenimports = [
    'effects',
    'effects.pixelsort',
    'effects.channelshift',
    'effects.scanlines',
    'effects.bitcrush',
    'effects.color',
    'effects.distortion',
    'effects.texture',
    'effects.temporal',
    'effects.modulation',
    'effects.enhance',
    'effects.destruction',
    'effects.ascii',
    'effects.sidechain',
    'effects.dsp_filters',
    'effects.adsr',
    'effects.physics',
    'core',
    'core.video_io',
    'core.export_models',
    'core.safety',
    'core.region',
    'core.automation',
    'core.analysis',
    'core.preview',
    'core.real_datamosh',
    'packages',
    'presets',
    'server',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'pydantic',
    'starlette',
    'multipart',
    'webview',
]

# Exclude modules we don't need (saves ~100MB+)
excludes = [
    'tkinter',
    'test',
    'unittest',
    'numpy.tests',
    'PIL.tests',
    'setuptools',
    'pip',
    'ensurepip',
    # Unused transitive deps pulled in by opencv/numpy
    'scipy',
    'matplotlib',
    'matplotlib.backends',
    'contourpy',
    'kiwisolver',
    'cycler',
    'fonttools',
    'mpl_toolkits',
    '_soundfile_data',
    'soundfile',
    'IPython',
    'jupyter',
    'notebook',
    'pandas',
    'docutils',
    'sphinx',
    'pygments',
    'xmlrpc',
    'sqlite3',
    'lib2to3',
    'pydoc',
    'ctypes.test',
]

a = Analysis(
    [os.path.join(ROOT, 'desktop.py')],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[os.path.join(ROOT, 'hooks')],
    hooksconfig={},
    runtime_hooks=[os.path.join(ROOT, 'hooks', 'rthook_cv2.py')],
    excludes=excludes,
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
    name='Entropic',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX breaks code signing on macOS
    console=False,  # No Terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,  # Strip debug symbols from .so/.dylib (saves ~10-15%)
    upx=False,
    name='Entropic',
)

app = BUNDLE(
    coll,
    name='Entropic.app',
    icon=None,  # TODO: Add .icns icon file
    bundle_identifier='com.popchaoslabs.entropic',
    info_plist={
        'CFBundleName': 'Entropic',
        'CFBundleDisplayName': 'Entropic',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,  # Support dark mode
        'LSMinimumSystemVersion': '11.0',
    },
)
