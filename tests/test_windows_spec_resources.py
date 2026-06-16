from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_spec_collects_rapidocr_data_files() -> None:
    spec_text = (ROOT / "aica.spec").read_text(encoding="utf-8")

    assert 'collect_data_files("rapidocr")' in spec_text


def test_windows_spec_collects_onnxruntime_runtime() -> None:
    spec_text = (ROOT / "aica.spec").read_text(encoding="utf-8")

    assert 'collect_submodules("onnxruntime")' in spec_text
    assert 'collect_dynamic_libs("onnxruntime")' in spec_text


def test_windows_onefile_spec_collects_ocr_runtime_resources() -> None:
    spec_text = (ROOT / "aica_onefile.spec").read_text(encoding="utf-8")

    assert 'collect_data_files("rapidocr")' in spec_text
    assert 'collect_submodules("rapidocr")' in spec_text
    assert 'collect_submodules("onnxruntime")' in spec_text
    assert 'collect_dynamic_libs("onnxruntime")' in spec_text


def test_requirements_include_onnxruntime_for_image_translation() -> None:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "onnxruntime" in requirements
