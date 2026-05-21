from __future__ import annotations

from pathlib import Path
import importlib.util
import sys


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "chattodo-cross-packager" / "scripts" / "package_chattodo.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("package_chattodo", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_skill_metadata_mentions_git_and_zip_packaging() -> None:
    skill = (ROOT / "chattodo-cross-packager" / "SKILL.md").read_text(encoding="utf-8")

    assert "git clone" in skill
    assert ".zip" in skill
    assert "windows-onefile" in skill
    assert "macos-x86_64" in skill


def test_validate_request_rejects_wrong_host_for_windows(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "host_platform", lambda: "macos")

    args = module.parse_args(
        [
            "--source-method",
            "git",
            "--repo-url",
            "https://example.com/repo.git",
            "--target",
            "windows-onefile",
            "--workspace",
            "/tmp/chattodo",
        ]
    )

    try:
        module.validate_request(args)
    except SystemExit as exc:
        assert "Windows targets must be built on Windows." in str(exc)
    else:
        raise AssertionError("validate_request should reject Windows targets on macOS")


def test_validate_request_requires_repo_or_zip() -> None:
    module = _load_module()

    git_args = module.parse_args(
        [
            "--source-method",
            "git",
            "--target",
            "windows-onedir",
            "--workspace",
            "C:/tmp/chattodo",
        ]
    )
    zip_args = module.parse_args(
        [
            "--source-method",
            "zip",
            "--target",
            "windows-onedir",
            "--workspace",
            "C:/tmp/chattodo",
        ]
    )

    for args, expected in (
        (git_args, "--repo-url is required"),
        (zip_args, "--zip-path is required"),
    ):
        try:
            module.validate_request(args)
        except SystemExit as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"validate_request should fail with {expected}")
