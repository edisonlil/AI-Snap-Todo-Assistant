from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_spec_collects_rapidocr_data_files() -> None:
    spec_text = (ROOT / "aica.spec").read_text(encoding="utf-8")

    assert 'collect_data_files("rapidocr")' in spec_text
