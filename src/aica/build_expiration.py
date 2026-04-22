"""Packaged build expiration helpers."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime


_BUILD_CREATED_AT = datetime.fromisoformat("2026-04-21T00:00:00+08:00")
_BUILD_EXPIRES_AT = datetime.fromisoformat("2026-10-21T00:00:00+08:00")
_ENFORCE_EXPIRATION_ENV = "AICA_ENFORCE_EXPIRATION"


@dataclass(frozen=True)
class BuildExpirationStatus:
    created_at: datetime
    expires_at: datetime
    expired: bool


def should_enforce_build_expiration() -> bool:
    if os.getenv(_ENFORCE_EXPIRATION_ENV, "").strip() == "1":
        return True
    return bool(getattr(sys, "frozen", False))


def get_build_expiration_status(*, now: datetime | None = None) -> BuildExpirationStatus:
    current = now or datetime.now(_BUILD_EXPIRES_AT.tzinfo)
    if current.tzinfo is None:
        current = current.replace(tzinfo=_BUILD_EXPIRES_AT.tzinfo)
    return BuildExpirationStatus(
        created_at=_BUILD_CREATED_AT,
        expires_at=_BUILD_EXPIRES_AT,
        expired=current >= _BUILD_EXPIRES_AT,
    )


def build_expiration_message(*, now: datetime | None = None) -> str:
    status = get_build_expiration_status(now=now)
    return (
        "当前打包版本已到期，无法继续运行。\n\n"
        f"构建时间：{status.created_at.strftime('%Y-%m-%d')}\n"
        f"到期时间：{status.expires_at.strftime('%Y-%m-%d')}\n\n"
        "请联系维护者获取新的安装包。"
    )
