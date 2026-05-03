"""SQLite cache for troubleshooting error-code documentation."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aica.paths import aica_database_file
from aica.storage.adapters import now_iso, parse_json_object
from aica.storage.sqlite.repositories import SQLiteStorageMigrator
from aica.text_sanitize import sanitize_text


@dataclass(frozen=True)
class ErrorCodeRecord:
    code: str
    title: str = ""
    message: str = ""
    meaning: str = ""
    suggestion: str = ""
    source_name: str = ""
    source_type: str = "online_doc"
    source_url: str = ""
    category: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)
    cache_status: str = "fresh"
    first_seen_at: str = ""
    last_seen_at: str = ""
    updated_at: str = ""

    def normalized(self, *, timestamp: str | None = None) -> "ErrorCodeRecord":
        now = timestamp or now_iso()
        return ErrorCodeRecord(
            code=sanitize_text(self.code),
            title=sanitize_text(self.title),
            message=sanitize_text(self.message),
            meaning=sanitize_text(self.meaning),
            suggestion=sanitize_text(self.suggestion),
            source_name=sanitize_text(self.source_name),
            source_type=sanitize_text(self.source_type) or "online_doc",
            source_url=sanitize_text(self.source_url),
            category=sanitize_text(self.category),
            raw_payload=dict(self.raw_payload or {}),
            cache_status=sanitize_text(self.cache_status) or "fresh",
            first_seen_at=sanitize_text(self.first_seen_at) or now,
            last_seen_at=sanitize_text(self.last_seen_at) or now,
            updated_at=sanitize_text(self.updated_at) or now,
        )


class SQLiteErrorCodeRepository:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else aica_database_file()
        SQLiteStorageMigrator(self._db_path).ensure_schema()

    @property
    def path(self) -> str:
        return str(self._db_path)

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def get_many(self, codes: list[str]) -> dict[str, ErrorCodeRecord]:
        normalized_codes = _dedupe_codes(codes)
        if not normalized_codes:
            return {}
        placeholders = ",".join("?" for _ in normalized_codes)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM error_codes WHERE code IN ({placeholders})",
                normalized_codes,
            ).fetchall()
        return {str(row["code"]): _record_from_row(row) for row in rows}

    def upsert_many(self, records: list[ErrorCodeRecord]) -> None:
        normalized_records = [
            record.normalized()
            for record in records
            if sanitize_text(record.code)
        ]
        if not normalized_records:
            return
        with self._connect() as connection:
            for record in normalized_records:
                existing = connection.execute(
                    "SELECT first_seen_at FROM error_codes WHERE code = ?",
                    (record.code,),
                ).fetchone()
                first_seen_at = str(existing["first_seen_at"]) if existing else record.first_seen_at
                connection.execute(
                    """
                    INSERT INTO error_codes(
                      code, title, message, meaning, suggestion, source_name,
                      source_type, source_url, category, raw_payload_json,
                      cache_status, first_seen_at, last_seen_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(code) DO UPDATE SET
                      title=excluded.title,
                      message=excluded.message,
                      meaning=excluded.meaning,
                      suggestion=excluded.suggestion,
                      source_name=excluded.source_name,
                      source_type=excluded.source_type,
                      source_url=excluded.source_url,
                      category=excluded.category,
                      raw_payload_json=excluded.raw_payload_json,
                      cache_status=excluded.cache_status,
                      last_seen_at=excluded.last_seen_at,
                      updated_at=excluded.updated_at
                    """,
                    (
                        record.code,
                        record.title,
                        record.message,
                        record.meaning,
                        record.suggestion,
                        record.source_name,
                        record.source_type,
                        record.source_url,
                        record.category,
                        json.dumps(record.raw_payload, ensure_ascii=False),
                        record.cache_status,
                        first_seen_at,
                        record.last_seen_at,
                        record.updated_at,
                    ),
                )

    def seed_builtin_if_needed(self, records: list[ErrorCodeRecord], seed_version: str) -> bool:
        normalized_seed_version = sanitize_text(seed_version)
        if not normalized_seed_version:
            return False
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM schema_meta WHERE key='error_code_seed_version'"
            ).fetchone()
            if row and str(row["value"] or "") == normalized_seed_version:
                return False
        self.upsert_many(records)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO schema_meta(key, value)
                VALUES('error_code_seed_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (normalized_seed_version,),
            )
        return True


def _record_from_row(row: sqlite3.Row) -> ErrorCodeRecord:
    return ErrorCodeRecord(
        code=str(row["code"] or ""),
        title=str(row["title"] or ""),
        message=str(row["message"] or ""),
        meaning=str(row["meaning"] or ""),
        suggestion=str(row["suggestion"] or ""),
        source_name=str(row["source_name"] or ""),
        source_type=str(row["source_type"] or "online_doc"),
        source_url=str(row["source_url"] or ""),
        category=str(row["category"] or ""),
        raw_payload=parse_json_object(row["raw_payload_json"]),
        cache_status=str(row["cache_status"] or "fresh"),
        first_seen_at=str(row["first_seen_at"] or ""),
        last_seen_at=str(row["last_seen_at"] or ""),
        updated_at=str(row["updated_at"] or ""),
    )


def _dedupe_codes(codes: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for code in codes:
        normalized = sanitize_text(code)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
