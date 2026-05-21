from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_macos_spec_reads_target_arch_from_environment() -> None:
    spec_text = (ROOT / "aica_macos.spec").read_text(encoding="utf-8")

    assert 'os.environ.get("AICA_TARGET_ARCH"' in spec_text
    assert "target_arch=target_arch" in spec_text


def test_macos_build_script_uses_env_not_cli_target_arch() -> None:
    script_text = (ROOT / "scripts" / "build_macos_app.sh").read_text(encoding="utf-8")

    assert 'export AICA_TARGET_ARCH="$TARGET_ARCH"' in script_text
    assert '--target-arch "$TARGET_ARCH"' not in script_text
    assert '"$PYTHON_BIN" -m PyInstaller --noconfirm --clean aica_macos.spec' in script_text
