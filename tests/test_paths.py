from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.paths import app_data_dir, asset_file, icon_file, legacy_app_data_dir, storage_paths  # noqa: E402
from aica.runtime import PLATFORM_MACOS, PLATFORM_WINDOWS  # noqa: E402


def test_icon_file_prefers_dark_macos_variant_when_requested(monkeypatch) -> None:
    assets_dir = Path("/tmp/assets")

    monkeypatch.setattr("aica.paths.runtime_root", lambda: Path("/tmp"))
    monkeypatch.setattr(Path, "exists", lambda self: self == assets_dir / "aica_icon_dark.icns")

    assert icon_file(PLATFORM_MACOS, dark_mode=True) == assets_dir / "aica_icon_dark.icns"


def test_icon_file_keeps_default_windows_variant() -> None:
    assert icon_file(PLATFORM_WINDOWS).name == "aica_icon.ico"


def test_asset_file_uses_runtime_root(monkeypatch) -> None:
    monkeypatch.setattr("aica.paths.runtime_root", lambda: Path("/tmp/bundle"))

    assert asset_file("aica_icon.png") == Path("/tmp/bundle/assets/aica_icon.png")


def test_legacy_app_data_dir_does_not_depend_on_path_home(monkeypatch) -> None:
    def _broken_home() -> Path:
        raise RecursionError("broken pathlib home")

    monkeypatch.setattr(Path, "home", _broken_home)
    monkeypatch.setenv("HOME", "/Users/customer")

    assert legacy_app_data_dir() == Path("/Users/customer/.aica")


def test_storage_paths_expands_tilde_without_path_home(monkeypatch) -> None:
    def _broken_home() -> Path:
        raise RecursionError("broken pathlib home")

    monkeypatch.setattr(Path, "home", _broken_home)
    monkeypatch.setenv("HOME", "/Users/customer")
    monkeypatch.setenv("AICA_HOME", "~/Library/Application Support/Chattodo")
    monkeypatch.delenv("AICA_DATA_DIR", raising=False)
    monkeypatch.delenv("AICA_LOG_DIR", raising=False)

    paths = storage_paths()

    assert paths.data_dir == Path("/Users/customer/Library/Application Support/Chattodo")
    assert paths.log_dir == Path("/Users/customer/Library/Application Support/Chattodo")
    assert app_data_dir() == Path("/Users/customer/Library/Application Support/Chattodo")
