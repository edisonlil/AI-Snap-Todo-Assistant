from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_macos_build_script_supports_explicit_target_arches() -> None:
    script = (ROOT / "scripts" / "build_macos_app.sh").read_text(encoding="utf-8")

    assert "--target-arch" in script
    assert "arm64|x86_64|universal2" in script
    assert "PyInstaller target arch" in script


def test_readme_documents_intel_macos_packaging() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "支持 Apple Silicon 与 Intel" in readme
    assert "./scripts/build_macos_app.sh --target-arch x86_64" in readme
    assert "./scripts/build_macos_app.sh --target-arch universal2" in readme
