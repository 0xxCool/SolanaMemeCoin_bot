# PyInstaller specification file for Windows executable

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['gui/main_window.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('../config.py', '.'),
        ('../trader.py', '.'),
        ('../scanner.py', '.'),
        ('../analyzer.py', '.'),
        ('../integration.py', '.'),
        ('../ai_engine.py', '.'),
        ('../auto_trader.py', '.'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'websockets',
        'aiohttp',
        'fastapi',
        'uvicorn',
        'solana',
        'solders',
        'asyncio',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SolanaTradingBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed app (no console)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/app.ico',
    version_file='version_info.txt'
)

# Optional: Create a single-folder distribution instead
# Comment out the single-file EXE above and uncomment below for folder mode
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='SolanaTradingBot'
# )
