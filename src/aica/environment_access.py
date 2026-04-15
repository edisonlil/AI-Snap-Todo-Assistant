"""Domain models and services for project environment access."""
from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from aica.text_sanitize import sanitize_text

if TYPE_CHECKING:
    from aica.storage.contracts import ProjectEnvironmentRepository


def _normalize_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    text = sanitize_text(value).casefold()
    return text in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class ProjectEnvironmentRecord:
    id: str
    project_id: str
    env_name: str
    env_type: str = ""
    sort_order: int = 0
    is_active: bool = True
    note: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class EnvironmentAccessEntryRecord:
    id: str
    environment_id: str
    access_name: str
    access_type: str = ""
    url_or_host: str = ""
    username: str = ""
    password_encrypted: str = ""
    otp_secret_encrypted: str = ""
    requires_otp: bool = False
    note: str = ""
    open_command: str = ""
    sort_order: int = 0
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class ProjectEnvironmentBundle:
    environment: ProjectEnvironmentRecord
    entries: tuple[EnvironmentAccessEntryRecord, ...] = ()


@dataclass(frozen=True)
class EnvironmentAccessLaunchResult:
    entry: EnvironmentAccessEntryRecord
    username: str = ""
    password: str = ""
    otp_code: str = ""
    otp_remaining_seconds: int = 0

    @property
    def has_password(self) -> bool:
        return bool(self.password)

    @property
    def has_otp(self) -> bool:
        return bool(self.otp_code)


class EnvironmentSecretCipher(Protocol):
    def encrypt(self, value: str) -> str:
        """Encode a secret before persistence."""

    def decrypt(self, value: str) -> str:
        """Decode a persisted secret."""


class PassthroughSecretCipher:
    """Placeholder secret adapter for MVP before real encryption lands."""

    def encrypt(self, value: str) -> str:
        return sanitize_text(value)

    def decrypt(self, value: str) -> str:
        return sanitize_text(value)


class TotpService:
    def __init__(self, *, digits: int = 6, period_seconds: int = 30) -> None:
        self._digits = max(6, int(digits))
        self._period_seconds = max(1, int(period_seconds))

    @property
    def period_seconds(self) -> int:
        return self._period_seconds

    def generate(self, secret: str, *, for_timestamp: int | None = None) -> tuple[str, int]:
        normalized_secret = sanitize_text(secret).replace(" ", "").replace("-", "").upper()
        if not normalized_secret:
            return "", 0
        try:
            key = base64.b32decode(normalized_secret, casefold=True)
        except Exception:
            return "", 0

        current_ts = int(for_timestamp if for_timestamp is not None else time.time())
        counter = current_ts // self._period_seconds
        message = struct.pack(">Q", counter)
        digest = hmac.new(key, message, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        binary = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
        code = str(binary % (10 ** self._digits)).zfill(self._digits)
        remaining = self._period_seconds - (current_ts % self._period_seconds)
        return code, remaining if remaining > 0 else self._period_seconds


class EnvironmentAccessService:
    def __init__(
        self,
        repository: "ProjectEnvironmentRepository",
        *,
        secret_cipher: EnvironmentSecretCipher | None = None,
        totp_service: TotpService | None = None,
    ) -> None:
        self._repository = repository
        self._secret_cipher = secret_cipher or PassthroughSecretCipher()
        self._totp_service = totp_service or TotpService()

    def list_project_environments(self, project_id: str) -> list[ProjectEnvironmentBundle]:
        normalized_project_id = sanitize_text(project_id)
        if not normalized_project_id:
            return []
        return self._repository.list_project_environments(normalized_project_id)

    def prepare_login(self, entry_id: str) -> EnvironmentAccessLaunchResult | None:
        entry = self._repository.get_access_entry(sanitize_text(entry_id))
        if entry is None:
            return None
        password = self._secret_cipher.decrypt(entry.password_encrypted)
        otp_code = ""
        otp_remaining_seconds = 0
        if entry.requires_otp:
            otp_code, otp_remaining_seconds = self._resolve_otp(entry)
        return EnvironmentAccessLaunchResult(
            entry=entry,
            username=entry.username,
            password=password,
            otp_code=otp_code,
            otp_remaining_seconds=otp_remaining_seconds,
        )

    def get_password(self, entry_id: str) -> str:
        entry = self._repository.get_access_entry(sanitize_text(entry_id))
        if entry is None:
            return ""
        return self._secret_cipher.decrypt(entry.password_encrypted)

    def get_otp_code(self, entry_id: str) -> tuple[str, int]:
        entry = self._repository.get_access_entry(sanitize_text(entry_id))
        if entry is None or not entry.requires_otp:
            return "", 0
        return self._resolve_otp(entry)

    def get_otp_remaining_seconds(self, entry_id: str) -> int:
        _, remaining = self.get_otp_code(entry_id)
        return remaining

    def encrypt_secret(self, value: str) -> str:
        return self._secret_cipher.encrypt(value)

    def _resolve_otp(self, entry: EnvironmentAccessEntryRecord) -> tuple[str, int]:
        secret = self._secret_cipher.decrypt(entry.otp_secret_encrypted)
        if not secret:
            return "", 0
        return self._totp_service.generate(secret)
