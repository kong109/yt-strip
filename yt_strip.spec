# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for building YT Strip as a macOS .app bundle."""

import shutil

block_cipher = None

# Locate ffmpeg/ffprobe so they get bundled into the app
binaries = []
for tool in ('ffmpeg', 'ffprobe'):
    path = shutil.which(tool)
    if path:
        binaries.append((path, '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=[],
    hiddenimports=['yt_dlp', 'mutagen', 'mutagen.id3', 'mutagen.mp3', 'certifi'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='YT Strip',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,               # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=True,         # macOS: allow drag-and-drop URLs onto dock icon
    target_arch=None,            # universal2 if you want Intel+ARM
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='YT Strip',
)

app = BUNDLE(
    coll,
    name='YT Strip.app',
    icon=None,                   # add an .icns file path here for a custom icon
    bundle_identifier='com.ytstrip.app',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleName': 'YT Strip',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,   # supports dark mode
    },
)
