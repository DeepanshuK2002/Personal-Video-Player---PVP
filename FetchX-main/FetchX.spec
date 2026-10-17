# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['vlc']
hiddenimports += collect_submodules('M3U8Sites')


a = Analysis(
    ['FetchX_Desktop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/fetchx.ico', 'assets'),
        ('assets/fonts/SF Pro', 'assets/fonts/SF Pro'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'unittest',
        'email.test',
        'test',
        'pydoc',
        'pdb',
        'doctest',
        'difflib',
    ],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FetchX',
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
    icon='assets/fetchx.ico',
)

