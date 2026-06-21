# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata


PROJECT_ROOT = Path(SPECPATH).resolve()
TKINTERDND2_DATAS = collect_data_files('tkinterdnd2')
RUNTIME_METADATA_DATAS = [
    *copy_metadata('Pillow'),
    *copy_metadata('PyMuPDF'),
    *copy_metadata('pypdf'),
    *copy_metadata('tkinterdnd2'),
]
LEGAL_NOTICE_DATAS = [
    (str(PROJECT_ROOT / 'LICENSE'), '.'),
    (str(PROJECT_ROOT / 'THIRD_PARTY_NOTICES.txt'), '.'),
    (str(PROJECT_ROOT / 'about.txt'), '.'),
    (str(PROJECT_ROOT / 'licenses' / 'tkdnd' / 'license.terms'), 'licenses/tkdnd'),
]

a = Analysis(
    [str(PROJECT_ROOT / 'pdf_splitter' / 'main.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[*TKINTERDND2_DATAS, *RUNTIME_METADATA_DATAS, *LEGAL_NOTICE_DATAS],
    hiddenimports=['tkinterdnd2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'pandas', 'matplotlib', 'setuptools'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='j3PdfSplit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory='lib',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='j3PdfSplit',
)
