from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.single_instance import SingleInstanceGuard  # noqa: E402


def test_macos_single_instance_uses_lock_file(tmp_path: Path) -> None:
    lock_file = tmp_path / "aica.lock"
    first = SingleInstanceGuard(lock_file=lock_file, platform_id="macos")
    second = SingleInstanceGuard(lock_file=lock_file, platform_id="macos")

    assert first.acquire() is True
    assert second.acquire() is False

    first.release()

    assert second.acquire() is True
    second.release()


def test_release_without_acquire_is_safe(tmp_path: Path) -> None:
    guard = SingleInstanceGuard(lock_file=tmp_path / "unused.lock", platform_id="macos")
    guard.release()
