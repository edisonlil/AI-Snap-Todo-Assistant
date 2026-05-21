"""SQLite-backed repositories for project/global environment access."""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from aica.environment_access import (
    EnvironmentAccessEntryRecord,
    ProjectEnvironmentBundle,
    ProjectEnvironmentRecord,
    normalize_access_type,
    normalize_environment_scope,
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


def _normalize_merge_key(value: object) -> str:
    return sanitize_text(value).casefold()


def _build_environment_record(row: sqlite3.Row | dict[str, object]) -> ProjectEnvironmentRecord:
    payload = dict(row)
    return ProjectEnvironmentRecord(
        id=str(payload.get("id") or ""),
        project_id=str(payload.get("project_id") or ""),
        env_name=str(payload.get("env_name") or ""),
        scope=normalize_environment_scope(payload.get("scope")),
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
        scope=normalize_environment_scope(payload.get("scope"), default=""),
        source_scope=normalize_environment_scope(payload.get("source_scope") or payload.get("scope"), default=""),
        is_project_override=_normalize_bool(payload.get("is_project_override")),
        access_type=normalize_access_type(payload.get("access_type")),
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

    def _list_scoped_environments(
        self,
        *,
        scope: str,
        project_id: str = "",
        include_inactive: bool = False,
    ) -> list[ProjectEnvironmentBundle]:
        normalized_scope = normalize_environment_scope(scope)
        normalized_project_id = sanitize_text(project_id)
        with self._connect() as connection:
            if normalized_scope == "global":
                environment_rows = connection.execute(
                    """
                    SELECT
                      id, project_id, env_name, scope, env_type, sort_order,
                      is_active, note, created_at, updated_at
                    FROM project_environments
                    WHERE scope = 'global'
                      AND (? = 1 OR is_active = 1)
                    ORDER BY sort_order ASC, updated_at DESC, id DESC
                    """,
                    (1 if include_inactive else 0,),
                ).fetchall()
                entry_rows = connection.execute(
                    """
                    SELECT
                      environment_access_entries.id,
                      environment_access_entries.environment_id,
                      environment_access_entries.access_name,
                      project_environments.scope,
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
                    WHERE project_environments.scope = 'global'
                      AND (? = 1 OR environment_access_entries.is_active = 1)
                    ORDER BY environment_access_entries.sort_order ASC,
                             environment_access_entries.updated_at DESC,
                             environment_access_entries.id DESC
                    """,
                    (1 if include_inactive else 0,),
                ).fetchall()
            else:
                if not normalized_project_id:
                    return []
                environment_rows = connection.execute(
                    """
                    SELECT
                      id, project_id, env_name, scope, env_type, sort_order,
                      is_active, note, created_at, updated_at
                    FROM project_environments
                    WHERE scope = 'project'
                      AND project_id = ?
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
                      project_environments.scope,
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
                    WHERE project_environments.scope = 'project'
                      AND project_environments.project_id = ?
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
                    source_scope=environment.scope,
                    entries=tuple(entries_by_environment.get(environment.id, [])),
                )
            )
        return bundles

    def list_global_environments(
        self,
        *,
        include_inactive: bool = False,
    ) -> list[ProjectEnvironmentBundle]:
        return self._list_scoped_environments(scope="global", include_inactive=include_inactive)

    def list_project_environments(
        self,
        project_id: str,
        *,
        include_inactive: bool = False,
    ) -> list[ProjectEnvironmentBundle]:
        return self._list_scoped_environments(
            scope="project",
            project_id=project_id,
            include_inactive=include_inactive,
        )

    def list_effective_environments(
        self,
        project_id: str,
        *,
        include_inactive: bool = False,
    ) -> list[ProjectEnvironmentBundle]:
        global_bundles = self.list_global_environments(include_inactive=include_inactive)
        project_bundles = self.list_project_environments(project_id, include_inactive=include_inactive)
        if not project_bundles:
            return global_bundles

        project_by_name = {
            _normalize_merge_key(bundle.environment.env_name): bundle
            for bundle in project_bundles
            if _normalize_merge_key(bundle.environment.env_name)
        }

        merged: list[ProjectEnvironmentBundle] = []
        seen_names: set[str] = set()
        for bundle in project_bundles:
            env_key = _normalize_merge_key(bundle.environment.env_name)
            if not env_key:
                continue
            matching_global = next(
                (
                    item
                    for item in global_bundles
                    if _normalize_merge_key(item.environment.env_name) == env_key
                ),
                None,
            )
            if matching_global is None:
                merged.append(bundle)
                seen_names.add(env_key)
                continue

            project_entry_map = {
                _normalize_merge_key(entry.access_name): entry
                for entry in bundle.entries
                if _normalize_merge_key(entry.access_name)
            }
            effective_entries: list[EnvironmentAccessEntryRecord] = []
            for global_entry in matching_global.entries:
                entry_key = _normalize_merge_key(global_entry.access_name)
                if entry_key in project_entry_map:
                    continue
                effective_entries.append(
                    EnvironmentAccessEntryRecord(
                        **{
                            **global_entry.__dict__,
                            "source_scope": "global",
                            "is_project_override": False,
                        }
                    )
                )
            effective_entries.extend(
                EnvironmentAccessEntryRecord(
                    **{
                        **project_entry.__dict__,
                        "source_scope": "project",
                        "is_project_override": any(
                            _normalize_merge_key(item.access_name) == _normalize_merge_key(project_entry.access_name)
                            for item in matching_global.entries
                        ),
                    }
                )
                for project_entry in bundle.entries
            )
            effective_entries.sort(key=lambda item: (item.sort_order, item.updated_at or "", item.id))
            merged.append(
                ProjectEnvironmentBundle(
                    environment=ProjectEnvironmentRecord(
                        **{
                            **bundle.environment.__dict__,
                            "scope": "project",
                        }
                    ),
                    source_scope="project",
                    is_project_override=True,
                    entries=tuple(effective_entries),
                )
            )
            seen_names.add(env_key)

        for bundle in global_bundles:
            env_key = _normalize_merge_key(bundle.environment.env_name)
            if not env_key or env_key in seen_names or env_key in project_by_name:
                continue
            merged.append(bundle)
            seen_names.add(env_key)
        return merged

    def get_project_environment(self, environment_id: str) -> ProjectEnvironmentRecord | None:
        normalized_environment_id = sanitize_text(environment_id)
        if not normalized_environment_id:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                  id, project_id, env_name, scope, env_type, sort_order,
                  is_active, note, created_at, updated_at
                FROM project_environments
                WHERE id = ?
                LIMIT 1
                """,
                (normalized_environment_id,),
            ).fetchone()
        return _build_environment_record(row) if row is not None else None

    def get_access_entry(self, entry_id: str) -> EnvironmentAccessEntryRecord | None:
        normalized_entry_id = sanitize_text(entry_id)
        if not normalized_entry_id:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                  environment_access_entries.id,
                  environment_access_entries.environment_id,
                  environment_access_entries.access_name,
                  project_environments.scope,
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
                WHERE environment_access_entries.id = ?
                LIMIT 1
                """,
                (normalized_entry_id,),
            ).fetchone()
        return _build_access_entry_record(row) if row is not None else None

    def upsert_project_environment(self, environment: ProjectEnvironmentRecord) -> ProjectEnvironmentRecord:
        created_at = sanitize_text(environment.created_at) or now_iso()
        updated_at = sanitize_text(environment.updated_at) or now_iso()
        environment_id = sanitize_text(environment.id) or str(uuid.uuid4())
        normalized_scope = normalize_environment_scope(environment.scope)
        normalized_project_id = sanitize_text(environment.project_id) if normalized_scope == "project" else None
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO project_environments(
                  id, project_id, env_name, scope, env_type, sort_order,
                  is_active, note, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  project_id=excluded.project_id,
                  env_name=excluded.env_name,
                  scope=excluded.scope,
                  env_type=excluded.env_type,
                  sort_order=excluded.sort_order,
                  is_active=excluded.is_active,
                  note=excluded.note,
                  updated_at=excluded.updated_at
                """,
                (
                    environment_id,
                    normalized_project_id,
                    sanitize_text(environment.env_name),
                    normalized_scope,
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
            project_id=sanitize_text(normalized_project_id),
            env_name=sanitize_text(environment.env_name),
            scope=normalized_scope,
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
        environment = self.get_project_environment(normalized_environment_id)
        if environment is None:
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
                        normalize_access_type(entry.access_type),
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
                        scope=environment.scope,
                        source_scope=environment.scope,
                        access_type=normalize_access_type(entry.access_type),
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

    def delete_project_environment(self, environment_id: str) -> bool:
        normalized_environment_id = sanitize_text(environment_id)
        if not normalized_environment_id:
            return False
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM project_environments WHERE id = ?",
                (normalized_environment_id,),
            )
        return bool(cursor.rowcount)
