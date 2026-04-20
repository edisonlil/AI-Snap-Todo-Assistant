from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.paths import icon_file  # noqa: E402
from aica.runtime import PLATFORM_MACOS, PLATFORM_WINDOWS  # noqa: E402


def test_icon_file_prefers_dark_macos_variant_when_requested(monkeypatch) -> None:
    assets_dir = Path("/tmp/assets")

    monkeypatch.setattr("aica.paths.runtime_root", lambda: Path("/tmp"))
    monkeypatch.setattr(Path, "exists", lambda self: self == assets_dir / "aica_icon_dark.icns")

    assert icon_file(PLATFORM_MACOS, dark_mode=True) == assets_dir / "aica_icon_dark.icns"


def test_icon_file_keeps_default_windows_variant() -> None:
    assert icon_file(PLATFORM_WINDOWS).name == "aica_icon.ico"
