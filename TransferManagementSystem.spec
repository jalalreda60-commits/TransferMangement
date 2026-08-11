# -*- mode: python ; coding: utf-8 -*-
"""
TransferManagementSystem.spec
--------------------------------
PyInstaller build spec, used both by build_exe.py locally and by the
GitHub Actions workflow (.github/workflows/build-windows-exe.yml).

Produces a one-folder Windows application (dist/TransferManagementSystem/)
- one-folder mode starts faster and is easier to troubleshoot on shared
machines than a single .exe.
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

hidden_imports = (
    collect_submodules("matplotlib.backends")
    + collect_submodules("sqlalchemy.dialects.sqlite")
    + [
        "matplotlib.backends.backend_qtagg",
        "PySide6.QtSvg",
        "PySide6.QtPrintSupport",
    ]
)

datas = [
    ("resources/icons/app_icon.png", "resources/icons"),
]
datas += collect_data_files("matplotlib")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TransferManagementSystem",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="resources/icons/app_icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TransferManagementSystem",
)
