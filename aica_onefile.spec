# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPEC).resolve().parent
hiddenimports = collect_submodules("pynput") + collect_submodules("pyperclip")
icon_path = project_root / "assets" / "aica_icon.ico"
version_file = project_root / "aica_version_info.txt"
datas = [
    (str(project_root / "src" / "aica" / "qml"), "aica/qml"),
    (str(project_root / "assets"), "assets"),
]


a = Analysis(
    ["run_aica.py"],
    pathex=[str(project_root / "src")],
    binaries=[],
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
    a.binaries,
    a.datas,
    [],
    name="AICA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=[str(icon_path)],
    version=str(version_file),
)
