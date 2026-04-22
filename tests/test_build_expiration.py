from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.build_expiration import (  # noqa: E402
    build_expiration_message,
    get_build_expiration_status,
    should_enforce_build_expiration,
)


def test_get_build_expiration_status_marks_future_time_as_active() -> None:
    status = get_build_expiration_status(now=datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc))

    assert status.expired is False


def test_build_expiration_message_contains_expiration_date() -> None:
    message = build_expiration_message(now=datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc))

    assert "2026-10-21" in message
    assert "已到期" in message


def test_should_enforce_build_expiration_uses_env_override(monkeypatch) -> None:
    monkeypatch.setenv("AICA_ENFORCE_EXPIRATION", "1")

    assert should_enforce_build_expiration() is True


def test_should_enforce_build_expiration_defaults_to_false(monkeypatch) -> None:
    monkeypatch.delenv("AICA_ENFORCE_EXPIRATION", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert should_enforce_build_expiration() is False


def test_get_build_expiration_status_marks_expired_after_cutoff() -> None:
    status = get_build_expiration_status(now=datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc))

    assert status.expired is True
