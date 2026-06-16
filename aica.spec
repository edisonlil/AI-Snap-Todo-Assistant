# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules


project_root = Path(SPEC).resolve().parent
hiddenimports = (
    collect_submodules("pynput")
    + collect_submodules("pyperclip")
    + collect_submodules("PyQt6.QtWebEngineCore")
    + collect_submodules("PyQt6.QtWebEngineQuick")
    + collect_submodules("rapidocr")
    + collect_submodules("onnxruntime")
)
binaries = collect_dynamic_libs("onnxruntime")
icon_path = project_root / "assets" / "aica_icon.ico"
version_file = project_root / "aica_version_info.txt"
datas = [
    (str(project_root / "src" / "aica" / "qml"), "aica/qml"),
    (str(project_root / "src" / "aica" / "resources"), "aica/resources"),
    (str(project_root / "src" / "aica" / "storage" / "sqlite" / "schema.sql"), "aica/storage/sqlite"),
    (str(project_root / "assets"), "assets"),
] + collect_data_files("rapidocr")


a = Analysis(
    ["run_aica.py"],
    pathex=[str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Chattodo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=[str(icon_path)],
    version=str(version_file),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Chattodo",
)
