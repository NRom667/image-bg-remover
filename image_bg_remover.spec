from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

from image_bg_remover.paths import PROJECT_ROOT

block_cipher = None

src_dir = PROJECT_ROOT / 'src'
main_script = PROJECT_ROOT / 'main.py'
icon_file = PROJECT_ROOT / 'images' / 'icon.ico'

hiddenimports = []
hiddenimports += collect_submodules('sam2')
hiddenimports += collect_submodules('hydra')
hiddenimports += collect_submodules('omegaconf')
hiddenimports += collect_submodules('iopath')
hiddenimports += collect_submodules('antlr4')

datas = []
datas += collect_data_files('sam2')
datas += [(str(PROJECT_ROOT / 'models'), 'models')]

a = Analysis(
    [str(main_script)],
    pathex=[str(PROJECT_ROOT), str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='ImageBGRemover',
    icon=str(icon_file),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
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
    name='ImageBGRemover',
)

