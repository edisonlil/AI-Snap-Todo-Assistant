"""SQLite-backed repositories for project environment access."""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from aica.environment_access import (
    EnvironmentAccessEntryRecord,
    ProjectEnvironmentBundle,
    ProjectEnvironmentRecord,
)
from aica.paths import aica_database_file
from aica.storage.adapters import now_iso
from aica.storage.sqlite.repositories import SQLiteStorageMigrator
from aica.text_sanitize import sanitize_text


def _sanitize_int(value: object, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    try:
        return int(value) != 0
    except (TypeError, ValueError):
        return bool(value)


def _build_environment_record(row: sqlite3.Row | dict[str, object]) -> ProjectEnvironmentRecord:
    payload = dict(row)
    return ProjectEnvironmentRecord(
        id=str(payload.get("id") or ""),
        project_id=str(payload.get("project_id") or ""),
        env_name=str(payload.get("env_name") or ""),
        env_type=str(payload.get("env_type") or ""),
        sort_order=_sanitize_int(payload.get("sort_order"), default=0),
        is_active=_normalize_bool(payload.get("is_active")),
        note=str(payload.get("note") or ""),
        created_at=str(payload.get("created_at") or ""),
        updated_at=str(payload.get("updated_at") or ""),
    )


def _build_access_entry_record(row: sqlite3.Row | dict[str, object]) -> EnvironmentAccessEntryRecord:
    payload = dict(row)
    return EnvironmentAccessEntryRecord(
        id=str(payload.get("id") or ""),
        environment_id=str(payload.get("environment_id") or ""),
        access_name=str(payload.get("access_name") or ""),
        access_type=str(payload.get("access_type") or ""),
        url_or_host=str(payload.get("url_or_host") or ""),
        username=str(payload.get("username") or ""),
        password_encrypted=str(payload.get("password_encrypted") or ""),
        otp_secret_encrypted=str(payload.get("otp_secret_encrypted") or ""),
        requires_otp=_normalize_bool(payload.get("requires_otp")),
        note=str(payload.get("note") or ""),
        open_command=str(payload.get("open_command") or ""),
        sort_order=_sanitize_int(payload.get("sort_order"), default=0),
        is_active=_normalize_bool(payload.get("is_active")),
        created_at=str(payload.get("created_at") or ""),
        updated_at=str(payload.get("updated_at") or ""),
    )


class SQLiteProjectEnvironmentRepository:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else aica_database_file()
        SQLiteStorageMigrator(self._db_path).ensure_schema()

    @property
    def path(self) -> str:
        return str(self._db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def list_project_environments(
        self,
        project_id: str,
        *,
        include_inactive: bool = False,
    ) -> list[ProjectEnvironmentBundle]:
        normalized_project_id = sanitize_text(project_id)
        if not normalized_project_id:
            return []
        with self._connect() as connection:
            environment_rows = connection.execute(
                """
                SELECT
                  id, project_id, env_name, env_type, sort_order,
                  is_active, note, created_at, updated_at
                FROM project_environments
                WHERE project_id = ?
                  AND (? = 1 OR is_active = 1)
                ORDER BY sort_order ASC, updated_at DESC, id DESC
                """,
                (normalized_project_id, 1 if include_inactive else 0),
            ).fetchall()
            entry_rows = connection.execute(
                """
                SELECT
                  environment_access_entries.id,
                  environment_access_entries.environment_id,
                  environment_access_entries.access_name,
                  environment_access_entries.access_type,
                  environment_access_entries.url_or_host,
                  environment_access_entries.username,
                  environment_access_entries.password_encrypted,
                  environment_access_entries.otp_secret_encrypted,
                  environment_access_entries.requires_otp,
                  environment_access_entries.note,
                  environment_access_entries.open_command,
                  environment_access_entries.sort_order,
                  environment_access_entries.is_active,
                  environment_access_entries.created_at,
                  environment_access_entries.updated_at
                FROM environment_access_entries
                JOIN project_environments
                  ON project_environments.id = environment_access_entries.environment_id
                WHERE project_environments.project_id = ?
                  AND (? = 1 OR environment_access_entries.is_active = 1)
                ORDER BY environment_access_entries.sort_order ASC,
                         environment_access_entries.updated_at DESC,
                         environment_access_entries.id DESC
                """,
                (normalized_project_id, 1 if include_inactive else 0),
            ).fetchall()

        entries_by_environment: dict[str, list[EnvironmentAccessEntryRecord]] = {}
        for row in entry_rows:
            entry = _build_access_entry_record(row)
            if not entry.environment_id:
                continue
            entries_by_environment.setdefault(entry.environment_id, []).append(entry)

        bundles: list[ProjectEnvironmentBundle] = []
        for row in environment_rows:
            environment = _build_environment_record(row)
            bundles.append(
                ProjectEnvironmentBundle(
                    environment=environment,
                    entries=tuple(entries_by_environment.get(environment.id, [])),
                )
            )
        return bundles

    def get_access_entry(self, entry_id: str) -> EnvironmentAccessEntryRecord | None:
        normalized_entry_id = sanitize_text(entry_id)
        if not normalized_entry_id:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                  id, environment_id, access_name, access_type, url_or_host,
                  username, password_encrypted, otp_secret_encrypted,
                  requires_otp, note, open_command, sort_order,
                  is_active, created_at, updated_at
                FROM environment_access_entries
                WHERE id = ?
                LIMIT 1
                """,
                (normalized_entry_id,),
            ).fetchone()
        return _build_access_entry_record(row) if row is not None else None

    def upsert_project_environment(self, environment: ProjectEnvironmentRecord) -> ProjectEnvironmentRecord:
        created_at = sanitize_text(environment.created_at) or now_iso()
        updated_at = sanitize_text(environment.updated_at) or now_iso()
        environment_id = sanitize_text(environment.id) or str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO project_environments(
                  id, project_id, env_name, env_type, sort_order,
                  is_active, note, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  project_id=excluded.project_id,
                  env_name=excluded.env_name,
                  env_type=excluded.env_type,
                  sort_order=excluded.sort_order,
                  is_active=excluded.is_active,
                  note=excluded.note,
                  updated_at=excluded.updated_at
                """,
                (
                    environment_id,
                    sanitize_text(environment.project_id),
                    sanitize_text(environment.env_name),
                    sanitize_text(environment.env_type),
                    int(environment.sort_order),
                    1 if environment.is_active else 0,
                    sanitize_text(environment.note),
                    created_at,
                    updated_at,
                ),
            )
        return ProjectEnvironmentRecord(
            id=environment_id,
            project_id=sanitize_text(environment.project_id),
            env_name=sanitize_text(environment.env_name),
            env_type=sanitize_text(environment.env_type),
            sort_order=int(environment.sort_order),
            is_active=bool(environment.is_active),
            note=sanitize_text(environment.note),
            created_at=created_at,
            updated_at=updated_at,
        )

    def replace_access_entries(
        self,
        environment_id: str,
        entries: list[EnvironmentAccessEntryRecord],
    ) -> list[EnvironmentAccessEntryRecord]:
        normalized_environment_id = sanitize_text(environment_id)
        if not normalized_environment_id:
            return []
        saved_entries: list[EnvironmentAccessEntryRecord] = []
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM environment_access_entries WHERE environment_id = ?",
                (normalized_environment_id,),
            )
            for entry in entries:
                created_at = sanitize_text(entry.created_at) or now_iso()
                updated_at = sanitize_text(entry.updated_at) or now_iso()
                entry_id = sanitize_text(entry.id) or str(uuid.uuid4())
                connection.execute(
                    """
                    INSERT INTO environment_access_entries(
                      id, environment_id, access_name, access_type, url_or_host,
                      username, password_encrypted, otp_secret_encrypted,
                      requires_otp, note, open_command, sort_order,
                      is_active, created_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry_id,
                        normalized_environment_id,
                        sanitize_text(entry.access_name),
                        sanitize_text(entry.access_type),
                        sanitize_text(entry.url_or_host),
                        sanitize_text(entry.username),
                        sanitize_text(entry.password_encrypted),
                        sanitize_text(entry.otp_secret_encrypted),
                        1 if entry.requires_otp else 0,
                        sanitize_text(entry.note),
                        sanitize_text(entry.open_command),
                        int(entry.sort_order),
                        1 if entry.is_active else 0,
                        created_at,
                        updated_at,
                    ),
                )
                saved_entries.append(
                    EnvironmentAccessEntryRecord(
                        id=entry_id,
                        environment_id=normalized_environment_id,
                        access_name=sanitize_text(entry.access_name),
                        access_type=sanitize_text(entry.access_type),
                        url_or_host=sanitize_text(entry.url_or_host),
                        username=sanitize_text(entry.username),
                        password_encrypted=sanitize_text(entry.password_encrypted),
                        otp_secret_encrypted=sanitize_text(entry.otp_secret_encrypted),
                        requires_otp=bool(entry.requires_otp),
                        note=sanitize_text(entry.note),
                        open_command=sanitize_text(entry.open_command),
                        sort_order=int(entry.sort_order),
                        is_active=bool(entry.is_active),
                        created_at=created_at,
                        updated_at=updated_at,
                    )
                )
        return saved_entries
