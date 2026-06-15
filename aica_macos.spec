# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from PyInstaller.building.osx import BUNDLE
from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPEC).resolve().parent
target_arch = os.environ.get("AICA_TARGET_ARCH", "").strip() or None
hiddenimports = (
    collect_submodules("pynput")
    + collect_submodules("pyperclip")
    + collect_submodules("PyQt6.QtWebEngineCore")
    + collect_submodules("PyQt6.QtWebEngineQuick")
    + collect_submodules("rapidocr")
)
icon_path = project_root / "assets" / "aica_icon.icns"
datas = [
    (str(project_root / "src" / "aica" / "qml"), "aica/qml"),
    (str(project_root / "src" / "aica" / "storage" / "sqlite" / "schema.sql"), "aica/storage/sqlite"),
    (str(project_root / "assets"), "assets"),
]
info_plist = {
    "CFBundleDisplayName": "Chattodo",
    "CFBundleName": "Chattodo",
    "CFBundleIdentifier": "com.aica.snap.todo.assistant",
    "CFBundleShortVersionString": "1.0.0",
    "CFBundleVersion": "1.0.0",
    "NSInputMonitoringUsageDescription": "Chattodo 需要监听你设置的全局截图快捷键，用于快速开始截图。",
    "LSUIElement": True,
}


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
    [],
    exclude_binaries=True,
    name="Chattodo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=target_arch,
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

app = BUNDLE(
    coll,
    name="Chattodo.app",
    icon=str(icon_path),
    bundle_identifier="com.aica.snap.todo.assistant",
    info_plist=info_plist,
)
