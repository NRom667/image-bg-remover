from __future__ import annotations

from pathlib import Path
from typing import Iterable

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
datas += [(str(PROJECT_ROOT / 'images'), 'images')]

excluded_modules = [
    'Pythonwin',
    'pywin32_system32',
    'pythoncom',
    'pywintypes',
    'win32',
    'win32api',
    'win32com',
    'win32con',
    'win32ui',
]


def _should_exclude_toc_entry(dest_name: str) -> bool:
    normalized = dest_name.replace('\\', '/').lower()
    excluded_prefixes = (
        'pythonwin/',
        'pywin32_system32/',
        'win32/',
        'win32com/',
    )
    excluded_names = (
        'pil/_avif.cp314-win_amd64.pyd',
        'pil/_webp.cp314-win_amd64.pyd',
        'pyside6/plugins/imageformats/qicns.dll',
        'pyside6/plugins/imageformats/qpdf.dll',
        'pyside6/plugins/imageformats/qsvg.dll',
        'pyside6/plugins/imageformats/qtga.dll',
        'pyside6/plugins/imageformats/qtiff.dll',
        'pyside6/plugins/imageformats/qwbmp.dll',
        'pyside6/plugins/imageformats/qwebp.dll',
    )
    return normalized.startswith(excluded_prefixes) or any(normalized.endswith(name) for name in excluded_names)


def _filter_toc_entries(entries: Iterable[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    return [entry for entry in entries if not _should_exclude_toc_entry(entry[0])]

a = Analysis(
    [str(main_script)],
    pathex=[str(PROJECT_ROOT), str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
a.binaries = _filter_toc_entries(a.binaries)
a.datas = _filter_toc_entries(a.datas)
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

