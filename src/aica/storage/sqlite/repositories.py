"""SQLite-backed repositories for Todo, bindings, and projects."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from aica.models import TicketSnapshot, TicketSummaryFields, merge_summary_fields_for_append
from aica.paths import aica_database_file, todo_bindings_file, todos_file
from aica.project_management import is_project_active
from aica.log_analysis.models import LogAnalysisTask
from aica.storage.adapters import (
    build_project_link,
    build_todo_item,
    deserialize_legacy_todo_item,
    normalize_group_alias,
    now_iso,
    parse_json_object,
    sanitize_string_dict,
)
from aica.storage.contracts import ProjectMatchResult, ProjectRecord
from aica.text_sanitize import sanitize_text
from aica.todo.models import TimelineAttachment, TimelineEvent, TodoConclusion, TodoItem, TodoProjectLink, TodoStatus


SCHEMA_VERSION = "13"


def _resolve_database_path(path_hint: str | None = None) -> Path:
    if not path_hint:
        return aica_database_file()
    candidate = Path(path_hint)
    if candidate.suffix.lower() == ".db":
        return candidate
    return candidate.parent / "aica.db"


def _resolve_legacy_todos_path(path_hint: str | None = None) -> Path | None:
    if not path_hint:
        return todos_file()
    candidate = Path(path_hint)
    if candidate.suffix.lower() == ".json":
        return candidate
    return None


def _resolve_legacy_bindings_path(path_hint: str | None = None) -> Path | None:
    if not path_hint:
        return todo_bindings_file()
    candidate = Path(path_hint)
    if candidate.suffix.lower() == ".json":
        return candidate
    return None


def _load_schema_sql() -> str:
    return Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")


def _has_column(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(str(row["name"] or "") == column_name for row in rows)


def _table_info(connection: sqlite3.Connection, table_name: str) -> list[sqlite3.Row]:
    return list(connection.execute(f"PRAGMA table_info({table_name})").fetchall())


def _is_project_active(support_ended_at: str, *, now: str | None = None) -> bool:
    return is_project_active(support_ended_at, now=now)


def _build_project_record(
    row: sqlite3.Row | dict[str, Any],
    aliases: tuple[str, ...] = (),
) -> ProjectRecord:
    payload = dict(row)
    return ProjectRecord(
        id=str(payload.get("id") or ""),
        project_name=str(payload.get("project_name") or ""),
        customer_name=str(payload.get("customer_name") or ""),
        task_order_no=str(payload.get("task_order_no") or ""),
        follow_up_started_at=str(payload.get("follow_up_started_at") or ""),
        support_ended_at=str(payload.get("support_ended_at") or ""),
        product_line=str(payload.get("product_line") or ""),
        product_version=str(payload.get("product_version") or ""),
        project_manager=str(payload.get("project_manager") or ""),
        project_level=str(payload.get("project_level") or "normal"),
        aliases=aliases,
        created_at=str(payload.get("created_at") or now_iso()),
        updated_at=str(payload.get("updated_at") or now_iso()),
    )


class SQLiteStorageMigrator:
    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        legacy_todos_path: str | Path | None = None,
        legacy_bindings_path: str | Path | None = None,
    ) -> None:
        self._db_path = Path(db_path) if db_path is not None else aica_database_file()
        self._legacy_todos_path = Path(legacy_todos_path) if legacy_todos_path is not None else None
        self._legacy_bindings_path = Path(legacy_bindings_path) if legacy_bindings_path is not None else None

    @property
    def path(self) -> str:
        return str(self._db_path)

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(_load_schema_sql())
            self._migrate_schema(connection)
            connection.execute(
                """
                INSERT INTO schema_meta(key, value)
                VALUES('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (SCHEMA_VERSION,),
            )

    def _migrate_schema(self, connection: sqlite3.Connection) -> None:
        if not _has_column(connection, "todos", "ticket_version"):
            connection.execute(
                "ALTER TABLE todos ADD COLUMN ticket_version TEXT NOT NULL DEFAULT ''"
            )
        timeline_columns = {
            "event_type": "TEXT NOT NULL DEFAULT 'default'",
            "payload_json": "TEXT NOT NULL DEFAULT '{}'",
            "status": "TEXT NOT NULL DEFAULT ''",
        }
        for column_name, column_def in timeline_columns.items():
            if not _has_column(connection, "todo_timeline_events", column_name):
                connection.execute(f"ALTER TABLE todo_timeline_events ADD COLUMN {column_name} {column_def}")
        log_analysis_columns = {
            "current_step": "TEXT NOT NULL DEFAULT ''",
        }
        for column_name, column_def in log_analysis_columns.items():
            if not _has_column(connection, "log_analysis_tasks", column_name):
                connection.execute(f"ALTER TABLE log_analysis_tasks ADD COLUMN {column_name} {column_def}")
        todo_columns = {
            "product_line": "TEXT NOT NULL DEFAULT ''",
            "ach_no": "TEXT NOT NULL DEFAULT ''",
            "ach_filled_at": "TEXT NOT NULL DEFAULT ''",
            "feature_point": "TEXT NOT NULL DEFAULT ''",
            "feature_point_source": "TEXT NOT NULL DEFAULT ''",
            "root_cause_desc": "TEXT NOT NULL DEFAULT ''",
            "root_cause_desc_source": "TEXT NOT NULL DEFAULT ''",
            "root_cause": "TEXT NOT NULL DEFAULT ''",
            "root_cause_source": "TEXT NOT NULL DEFAULT ''",
            "conclusion_content": "TEXT NOT NULL DEFAULT ''",
            "conclusion_updated_at": "TEXT NOT NULL DEFAULT ''",
            "completed_at": "TEXT NOT NULL DEFAULT ''",
        }
        for column_name, column_def in todo_columns.items():
            if not _has_column(connection, "todos", column_name):
                connection.execute(f"ALTER TABLE todos ADD COLUMN {column_name} {column_def}")
        self._migrate_project_environments_scope(connection)
        connection.execute(
            """
            UPDATE environment_access_entries
            SET access_type = 'web'
            WHERE TRIM(LOWER(COALESCE(access_type, ''))) IN ('', 'http', 'https', 'web')
            """
        )

    def _migrate_project_environments_scope(self, connection: sqlite3.Connection) -> None:
        columns = _table_info(connection, "project_environments")
        if not columns:
            return
        has_scope = any(str(row["name"] or "") == "scope" for row in columns)
        project_id_info = next((row for row in columns if str(row["name"] or "") == "project_id"), None)
        project_id_not_null = bool(project_id_info["notnull"]) if project_id_info is not None else False
        if has_scope and not project_id_not_null:
            connection.execute(
                "UPDATE project_environments SET scope='project' WHERE TRIM(COALESCE(scope, '')) = ''"
            )
            return

        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("ALTER TABLE environment_access_entries RENAME TO environment_access_entries_old")
        connection.execute("ALTER TABLE project_environments RENAME TO project_environments_old")
        connection.execute(
            """
            CREATE TABLE project_environments (
              id TEXT PRIMARY KEY,
              project_id TEXT DEFAULT '',
              env_name TEXT NOT NULL,
              scope TEXT NOT NULL DEFAULT 'project',
              env_type TEXT NOT NULL DEFAULT '',
              sort_order INTEGER NOT NULL DEFAULT 0,
              is_active INTEGER NOT NULL DEFAULT 1,
              note TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              CHECK(scope IN ('global', 'project')),
              CHECK((scope = 'global' AND (project_id = '' OR project_id IS NULL)) OR (scope = 'project' AND project_id <> '')),
              FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            INSERT INTO project_environments(
              id, project_id, env_name, scope, env_type, sort_order,
              is_active, note, created_at, updated_at
            )
            SELECT
              id,
              COALESCE(project_id, ''),
              env_name,
              'project',
              COALESCE(env_type, ''),
              COALESCE(sort_order, 0),
              COALESCE(is_active, 1),
              COALESCE(note, ''),
              COALESCE(created_at, ''),
              COALESCE(updated_at, '')
            FROM project_environments_old
            """
        )
        connection.execute(
            """
            CREATE TABLE environment_access_entries (
              id TEXT PRIMARY KEY,
              environment_id TEXT NOT NULL,
              access_name TEXT NOT NULL,
              access_type TEXT NOT NULL DEFAULT '',
              url_or_host TEXT NOT NULL DEFAULT '',
              username TEXT NOT NULL DEFAULT '',
              password_encrypted TEXT NOT NULL DEFAULT '',
              otp_secret_encrypted TEXT NOT NULL DEFAULT '',
              requires_otp INTEGER NOT NULL DEFAULT 0,
              note TEXT NOT NULL DEFAULT '',
              open_command TEXT NOT NULL DEFAULT '',
              sort_order INTEGER NOT NULL DEFAULT 0,
              is_active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(environment_id) REFERENCES project_environments(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            INSERT INTO environment_access_entries(
              id, environment_id, access_name, access_type, url_or_host,
              username, password_encrypted, otp_secret_encrypted,
              requires_otp, note, open_command, sort_order, is_active,
              created_at, updated_at
            )
            SELECT
              id, environment_id, access_name, COALESCE(access_type, ''), COALESCE(url_or_host, ''),
              COALESCE(username, ''), COALESCE(password_encrypted, ''), COALESCE(otp_secret_encrypted, ''),
              COALESCE(requires_otp, 0), COALESCE(note, ''), COALESCE(open_command, ''), COALESCE(sort_order, 0),
              COALESCE(is_active, 1), COALESCE(created_at, ''), COALESCE(updated_at, '')
            FROM environment_access_entries_old
            """
        )
        connection.execute("DROP TABLE environment_access_entries_old")
        connection.execute("DROP TABLE project_environments_old")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_project_environments_project ON project_environments(project_id, scope, is_active, sort_order, updated_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_environment_access_entries_environment ON environment_access_entries(environment_id, is_active, sort_order, updated_at DESC)"
        )
        connection.execute("PRAGMA foreign_keys = ON")

    def get_schema_version(self) -> str:
        self.ensure_schema()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()
        return str(row["value"]) if row is not None else ""

    def migrate_json_to_sqlite(self) -> None:
        self.ensure_schema()
        with self._connect() as connection:
            self._migrate_legacy_todos(connection)
            self._migrate_legacy_bindings(connection)
            self._backfill_ticket_versions(connection)

    def _meta_value(self, connection: sqlite3.Connection, key: str) -> str:
        row = connection.execute(
            "SELECT value FROM schema_meta WHERE key=?",
            (key,),
        ).fetchone()
        return str(row["value"]) if row is not None else ""

    def _set_meta_value(self, connection: sqlite3.Connection, key: str, value: str) -> None:
        connection.execute(
            """
            INSERT INTO schema_meta(key, value)
            VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, value),
        )

    def _migrate_legacy_todos(self, connection: sqlite3.Connection) -> None:
        if self._meta_value(connection, "legacy_todos_migrated") == "1":
            return
        legacy_path = self._legacy_todos_path
        if legacy_path is not None and legacy_path.exists():
            try:
                payload = json.loads(legacy_path.read_text(encoding="utf-8"))
            except Exception:
                payload = []
            if isinstance(payload, list):
                for item in payload:
                    if not isinstance(item, dict):
                        continue
                    todo = deserialize_legacy_todo_item(item)
                    _upsert_todo(connection, todo)
        self._set_meta_value(connection, "legacy_todos_migrated", "1")

    def _migrate_legacy_bindings(self, connection: sqlite3.Connection) -> None:
        if self._meta_value(connection, "legacy_bindings_migrated") == "1":
            return
        legacy_path = self._legacy_bindings_path
        if legacy_path is not None and legacy_path.exists():
            try:
                payload = json.loads(legacy_path.read_text(encoding="utf-8"))
            except Exception:
                payload = []
            if isinstance(payload, list):
                for item in payload:
                    if not isinstance(item, dict):
                        continue
                    todo_id = sanitize_text(item.get("todo_id", ""))
                    integration_id = sanitize_text(item.get("integration_id", ""))
                    if not todo_id or not integration_id:
                        continue
                    todo_exists = connection.execute(
                        "SELECT 1 FROM todos WHERE id=?",
                        (todo_id,),
                    ).fetchone()
                    if todo_exists is None:
                        continue
                    metadata_text = json.dumps(
                        sanitize_string_dict(parse_json_object(item.get("metadata", {}))),
                        ensure_ascii=False,
                    )
                    connection.execute(
                        """
                        INSERT INTO todo_bindings(
                          todo_id, integration_id, external_id, external_url,
                          last_event_id, last_event_type, last_sync_status,
                          metadata_json, deleted_locally, created_at, updated_at
                        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(todo_id, integration_id) DO UPDATE SET
                          external_id=excluded.external_id,
                          external_url=excluded.external_url,
                          last_event_id=excluded.last_event_id,
                          last_event_type=excluded.last_event_type,
                          last_sync_status=excluded.last_sync_status,
                          metadata_json=excluded.metadata_json,
                          deleted_locally=excluded.deleted_locally,
                          updated_at=excluded.updated_at
                        """,
                        (
                            todo_id,
                            integration_id,
                            sanitize_text(item.get("external_id", "")),
                            sanitize_text(item.get("external_url", "")),
                            sanitize_text(item.get("last_event_id", "")),
                            sanitize_text(item.get("last_event_type", "")),
                            sanitize_text(item.get("last_sync_status", "")),
                            metadata_text,
                            1 if bool(item.get("deleted_locally", False)) else 0,
                            sanitize_text(item.get("created_at", "")) or now_iso(),
                            sanitize_text(item.get("updated_at", "")) or now_iso(),
                        ),
                    )
        self._set_meta_value(connection, "legacy_bindings_migrated", "1")

    def _backfill_ticket_versions(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            UPDATE todos
            SET ticket_version = (
              SELECT COALESCE(
                NULLIF(
                  json_extract(
                    COALESCE(todo_project_links.project_snapshot_json, '{}'),
                    '$.product_version'
                  ),
                  ''
                ),
                ''
              )
              FROM todo_project_links
              WHERE todo_project_links.todo_id = todos.id
            )
            WHERE EXISTS (
              SELECT 1
              FROM todo_project_links
              WHERE todo_project_links.todo_id = todos.id
            )
              AND COALESCE(todos.ticket_version, '') = ''
              AND COALESCE(
                (
                  SELECT NULLIF(
                    json_extract(
                      COALESCE(todo_project_links.project_snapshot_json, '{}'),
                      '$.product_version'
                    ),
                    ''
                  )
                  FROM todo_project_links
                  WHERE todo_project_links.todo_id = todos.id
                ),
                ''
              ) <> ''
            """
        )


class SQLiteProjectRepository:
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

    def upsert_projects(self, projects: list[ProjectRecord]) -> list[ProjectRecord]:
        if not projects:
            return []
        with self._connect() as connection:
            for project in projects:
                created_at = sanitize_text(project.created_at) or now_iso()
                updated_at = sanitize_text(project.updated_at) or now_iso()
                connection.execute(
                    """
                    INSERT INTO projects(
                      id, project_name, customer_name, task_order_no,
                      follow_up_started_at, support_ended_at, product_line,
                      product_version, project_manager, project_level,
                      created_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      project_name=excluded.project_name,
                      customer_name=excluded.customer_name,
                      task_order_no=excluded.task_order_no,
                      follow_up_started_at=excluded.follow_up_started_at,
                      support_ended_at=excluded.support_ended_at,
                      product_line=excluded.product_line,
                      product_version=excluded.product_version,
                      project_manager=excluded.project_manager,
                      project_level=excluded.project_level,
                      updated_at=excluded.updated_at
                    """,
                    (
                        sanitize_text(project.id),
                        sanitize_text(project.project_name),
                        sanitize_text(project.customer_name),
                        sanitize_text(project.task_order_no),
                        sanitize_text(project.follow_up_started_at),
                        sanitize_text(project.support_ended_at),
                        sanitize_text(project.product_line),
                        sanitize_text(project.product_version),
                        sanitize_text(project.project_manager),
                        sanitize_text(project.project_level) or "normal",
                        created_at,
                        updated_at,
                    ),
                )
        for project in projects:
            self.replace_project_aliases(project.id, list(project.aliases))
        return projects

    def upsert_project(self, project: ProjectRecord) -> ProjectRecord:
        saved = self.upsert_projects([project])
        return saved[0]

    def list_projects(
        self,
        query: str = "",
        *,
        include_expired: bool = True,
        now: str | None = None,
    ) -> list[ProjectRecord]:
        normalized_query = sanitize_text(query).casefold()
        current_time = sanitize_text(now) or now_iso()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                  id, project_name, customer_name, task_order_no,
                  follow_up_started_at, support_ended_at, product_line,
                  product_version, project_manager, project_level,
                  created_at, updated_at
                FROM projects
                ORDER BY updated_at DESC, created_at DESC, id DESC
                """
            ).fetchall()
            alias_rows = connection.execute(
                """
                SELECT project_id, alias_name
                FROM project_group_aliases
                ORDER BY created_at ASC, id ASC
                """
            ).fetchall()

        aliases_by_project: dict[str, list[str]] = {}
        for alias_row in alias_rows:
            project_id = str(alias_row["project_id"] or "")
            alias_name = str(alias_row["alias_name"] or "")
            if not project_id or not alias_name:
                continue
            aliases_by_project.setdefault(project_id, []).append(alias_name)

        projects: list[ProjectRecord] = []
        for row in rows:
            project = _build_project_record(
                row,
                aliases=tuple(aliases_by_project.get(str(row["id"]), [])),
            )
            if not include_expired and not _is_project_active(project.support_ended_at, now=current_time):
                continue
            if normalized_query:
                haystacks = [
                    project.project_name,
                    project.customer_name,
                    project.task_order_no,
                    project.product_line,
                    project.product_version,
                    project.project_manager,
                    *project.aliases,
                ]
                if not any(normalized_query in str(item or "").casefold() for item in haystacks):
                    continue
            projects.append(project)
        return projects

    def get_project_by_task_order_no(self, task_order_no: str) -> ProjectRecord | None:
        normalized_task_order = sanitize_text(task_order_no)
        if not normalized_task_order:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                  id, project_name, customer_name, task_order_no,
                  follow_up_started_at, support_ended_at, product_line,
                  product_version, project_manager, project_level,
                  created_at, updated_at
                FROM projects
                WHERE task_order_no = ?
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT 1
                """,
                (normalized_task_order,),
            ).fetchone()
            if row is None:
                return None
            alias_rows = connection.execute(
                """
                SELECT alias_name
                FROM project_group_aliases
                WHERE project_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (str(row["id"]),),
            ).fetchall()
        aliases = tuple(str(item["alias_name"] or "") for item in alias_rows if str(item["alias_name"] or ""))
        return _build_project_record(row, aliases=aliases)

    def replace_project_aliases(self, project_id: str, aliases: list[str]) -> list[str]:
        sanitized_project_id = sanitize_text(project_id)
        normalized_aliases: list[str] = []
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM project_group_aliases WHERE project_id=?",
                (sanitized_project_id,),
            )
            for alias in aliases:
                alias_name = sanitize_text(alias)
                alias_name_normalized = normalize_group_alias(alias_name)
                if not alias_name or not alias_name_normalized or alias_name_normalized in normalized_aliases:
                    continue
                normalized_aliases.append(alias_name_normalized)
                stamp = now_iso()
                connection.execute(
                    """
                    INSERT INTO project_group_aliases(
                      id, project_id, alias_name, alias_name_normalized, created_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        sanitized_project_id,
                        alias_name,
                        alias_name_normalized,
                        stamp,
                        stamp,
                    ),
                )
        return normalized_aliases

    def delete_project(self, project_id: str) -> bool:
        sanitized_project_id = sanitize_text(project_id)
        if not sanitized_project_id:
            return False
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM projects WHERE id = ?",
                (sanitized_project_id,),
            )
        return cursor.rowcount > 0

    def match_project_by_group_name(
        self,
        group_name: str,
        *,
        now: str | None = None,
    ) -> ProjectMatchResult:
        normalized = normalize_group_alias(group_name)
        if not normalized:
            return ProjectMatchResult(
                status="unmatched",
                reason="missing_group_name",
                matched_group_name=sanitize_text(group_name),
            )
        active_matches: list[sqlite3.Row] = []
        expired_matches: list[sqlite3.Row] = []
        current_time = sanitize_text(now) or now_iso()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                  projects.id AS project_id,
                  projects.project_name,
                  projects.customer_name,
                  projects.task_order_no,
                  projects.follow_up_started_at,
                  projects.support_ended_at,
                  projects.product_line,
                  projects.product_version,
                  projects.project_manager,
                  projects.project_level,
                  project_group_aliases.alias_name
                FROM project_group_aliases
                JOIN projects ON projects.id = project_group_aliases.project_id
                WHERE project_group_aliases.alias_name_normalized = ?
                ORDER BY projects.updated_at DESC
                """,
                (normalized,),
            ).fetchall()
        if not rows:
            return ProjectMatchResult(
                status="unmatched",
                reason="no_project_alias_match",
                matched_group_name=sanitize_text(group_name),
            )
        for row in rows:
            support_ended_at = sanitize_text(row["support_ended_at"])
            if not _is_project_active(support_ended_at, now=current_time):
                expired_matches.append(row)
            else:
                active_matches.append(row)

        if len(active_matches) == 1:
            match = active_matches[0]
            project = _build_project_record(
                {
                    "id": match["project_id"],
                    "project_name": match["project_name"],
                    "customer_name": match["customer_name"],
                    "task_order_no": match["task_order_no"],
                    "follow_up_started_at": match["follow_up_started_at"],
                    "support_ended_at": match["support_ended_at"],
                    "product_line": match["product_line"],
                    "product_version": match["product_version"],
                    "project_manager": match["project_manager"],
                    "project_level": match["project_level"],
                }
            )
            return ProjectMatchResult(
                status="matched",
                project_id=project.id,
                matched_group_name=sanitize_text(group_name),
                matched_alias=str(match["alias_name"] or ""),
                project_snapshot=project.to_snapshot(),
            )

        if len(active_matches) > 1:
            names = " / ".join(str(row["project_name"] or "") for row in active_matches[:3])
            return ProjectMatchResult(
                status="conflict",
                reason=f"multiple_active_projects:{names}",
                matched_group_name=sanitize_text(group_name),
            )

        expired = expired_matches[0]
        expired_project = _build_project_record(
            {
                "id": expired["project_id"],
                "project_name": expired["project_name"],
                "customer_name": expired["customer_name"],
                "task_order_no": expired["task_order_no"],
                "follow_up_started_at": expired["follow_up_started_at"],
                "support_ended_at": expired["support_ended_at"],
                "product_line": expired["product_line"],
                "product_version": expired["product_version"],
                "project_manager": expired["project_manager"],
                "project_level": expired["project_level"],
            }
        )
        return ProjectMatchResult(
            status="expired",
            reason="matched_project_expired",
            matched_group_name=sanitize_text(group_name),
            matched_alias=str(expired["alias_name"] or ""),
            project_snapshot=expired_project.to_snapshot(),
        )

    def get_project_link(self, todo_id: str) -> TodoProjectLink | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                  todo_id, project_id, match_status, match_reason,
                  matched_group_name, matched_alias, project_snapshot_json,
                  matched_at, updated_at
                FROM todo_project_links
                WHERE todo_id = ?
                """,
                (sanitize_text(todo_id),),
            ).fetchone()
        if row is None:
            return None
        return build_project_link(
            {
                "todo_id": row["todo_id"],
                "project_id": row["project_id"] or "",
                "match_status": row["match_status"] or "",
                "match_reason": row["match_reason"] or "",
                "matched_group_name": row["matched_group_name"] or "",
                "matched_alias": row["matched_alias"] or "",
                "project_snapshot": parse_json_object(row["project_snapshot_json"]),
                "matched_at": row["matched_at"] or "",
                "updated_at": row["updated_at"] or "",
            }
        )

    def bind_todo_to_project(self, todo_id: str, match_result: ProjectMatchResult) -> TodoProjectLink:
        stamp = now_iso()
        project_id = sanitize_text(match_result.project_id) if match_result.status in {"matched", "manual"} else ""
        snapshot_json = json.dumps(
            sanitize_string_dict(match_result.project_snapshot),
            ensure_ascii=False,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO todo_project_links(
                  todo_id, project_id, match_status, match_reason,
                  matched_group_name, matched_alias, project_snapshot_json,
                  matched_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(todo_id) DO UPDATE SET
                  project_id=excluded.project_id,
                  match_status=excluded.match_status,
                  match_reason=excluded.match_reason,
                  matched_group_name=excluded.matched_group_name,
                  matched_alias=excluded.matched_alias,
                  project_snapshot_json=excluded.project_snapshot_json,
                  matched_at=excluded.matched_at,
                  updated_at=excluded.updated_at
                """,
                (
                    sanitize_text(todo_id),
                    project_id or None,
                    sanitize_text(match_result.status),
                    sanitize_text(match_result.reason),
                    sanitize_text(match_result.matched_group_name),
                    sanitize_text(match_result.matched_alias),
                    snapshot_json,
                    stamp,
                    stamp,
                ),
            )
        return self.get_project_link(todo_id) or TodoProjectLink(todo_id=sanitize_text(todo_id))


class SQLiteTodoRepository:
    def __init__(self, path_hint: str | None = None) -> None:
        self._db_path = _resolve_database_path(path_hint)
        self._legacy_todos_path = _resolve_legacy_todos_path(path_hint)
        if path_hint and Path(path_hint).suffix.lower() == ".json":
            self._legacy_bindings_path = Path(path_hint).with_name("todo_bindings.json")
        else:
            self._legacy_bindings_path = _resolve_legacy_bindings_path(path_hint)
        self._migrator = SQLiteStorageMigrator(
            self._db_path,
            legacy_todos_path=self._legacy_todos_path,
            legacy_bindings_path=self._legacy_bindings_path,
        )
        self._migrator.migrate_json_to_sqlite()
        self._project_repository = SQLiteProjectRepository(self._db_path)

    @property
    def path(self) -> str:
        return str(self._db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def list_todos(self, *, query: str = "", status: str = TodoStatus.OPEN) -> list[TodoItem]:
        normalized_query = sanitize_text(query).lower()
        normalized_status = sanitize_text(status).lower() or TodoStatus.OPEN
        if normalized_status not in {TodoStatus.OPEN, TodoStatus.DONE, "all", "done_missing_ach", "today_done"}:
            normalized_status = TodoStatus.OPEN

        sql = """
            SELECT DISTINCT
              todos.id, todos.title, todos.current_summary, todos.group_name, todos.environment,
              todos.ticket_type, todos.ach_no, todos.ach_filled_at, todos.ticket_version,
              todos.feature_point, todos.feature_point_source,
              todos.root_cause_desc, todos.root_cause_desc_source,
              todos.root_cause, todos.root_cause_source,
              todos.conclusion_content, todos.conclusion_updated_at,
              todos.status, todos.created_at, todos.completed_at, todos.updated_at
            FROM todos
            LEFT JOIN todo_project_links ON todo_project_links.todo_id = todos.id
            WHERE 1 = 1
        """
        params: list[object] = []
        if normalized_status != "all":
            if normalized_status == "done_missing_ach":
                sql += " AND todos.status = ? AND TRIM(COALESCE(todos.ach_no, '')) = ''"
                params.append(TodoStatus.DONE)
            elif normalized_status == "today_done":
                sql += " AND todos.status = ? AND SUBSTR(COALESCE(todos.completed_at, ''), 1, 10) = ?"
                params.extend([TodoStatus.DONE, datetime.now().strftime("%Y-%m-%d")])
            else:
                sql += " AND todos.status = ?"
                params.append(normalized_status)
        if normalized_query:
            sql += """
              AND (
                LOWER(todos.title) LIKE ?
                OR LOWER(todos.current_summary) LIKE ?
                OR LOWER(todos.group_name) LIKE ?
                OR LOWER(todos.environment) LIKE ?
                OR LOWER(todos.ticket_type) LIKE ?
                OR LOWER(todos.ach_no) LIKE ?
                OR LOWER(todos.ticket_version) LIKE ?
                OR LOWER(todos.feature_point) LIKE ?
                OR LOWER(todos.root_cause_desc) LIKE ?
                OR LOWER(todos.root_cause) LIKE ?
                OR LOWER(COALESCE(todo_project_links.matched_alias, '')) LIKE ?
                OR LOWER(COALESCE(todo_project_links.match_reason, '')) LIKE ?
                OR LOWER(COALESCE(todo_project_links.project_snapshot_json, '')) LIKE ?
              )
            """
            pattern = f"%{normalized_query}%"
            params.extend([pattern] * 13)
        sql += " ORDER BY todos.updated_at DESC, todos.created_at DESC, todos.id DESC"

        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
            return [self._load_todo(connection, str(row["id"])) for row in rows]

    def list_active_todos(self) -> list[TodoItem]:
        return self.list_todos(status=TodoStatus.OPEN)

    def relink_open_unresolved_todos(self) -> int:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT todos.id, todos.group_name
                FROM todos
                LEFT JOIN todo_project_links ON todo_project_links.todo_id = todos.id
                WHERE todos.status = ?
                  AND (
                    todo_project_links.match_status IS NULL
                    OR todo_project_links.match_status IN ('unmatched', 'conflict', 'expired')
                  )
                ORDER BY todos.updated_at DESC, todos.created_at DESC, todos.id DESC
                """,
                (TodoStatus.OPEN,),
            ).fetchall()
        return self._relink_rows(rows)

    def relink_open_unresolved_todos_by_aliases(self, aliases: list[str]) -> int:
        normalized_aliases = {
            normalize_group_alias(alias)
            for alias in aliases
            if normalize_group_alias(alias)
        }
        if not normalized_aliases:
            return 0
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT todos.id, todos.group_name
                FROM todos
                LEFT JOIN todo_project_links ON todo_project_links.todo_id = todos.id
                WHERE todos.status = ?
                  AND (
                    todo_project_links.match_status IS NULL
                    OR todo_project_links.match_status IN ('unmatched', 'conflict', 'expired')
                  )
                ORDER BY todos.updated_at DESC, todos.created_at DESC, todos.id DESC
                """,
                (TodoStatus.OPEN,),
            ).fetchall()
        filtered_rows = [
            row
            for row in rows
            if normalize_group_alias(str(row["group_name"] or "")) in normalized_aliases
        ]
        return self._relink_rows(filtered_rows)

    def get_todo(self, todo_id: str) -> TodoItem | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, current_summary, group_name, environment,
                       product_line, ticket_type, ach_no, ach_filled_at, ticket_version,
                       feature_point, feature_point_source,
                       root_cause_desc, root_cause_desc_source,
                       root_cause, root_cause_source,
                       conclusion_content, conclusion_updated_at,
                       status, created_at, completed_at, updated_at
                FROM todos
                WHERE id = ?
                """,
                (sanitize_text(todo_id),),
            ).fetchone()
            if row is None:
                return None
            return self._build_todo_from_row(connection, row)

    def create_todo_from_analysis(self, snapshot: TicketSnapshot, scenario: str) -> TodoItem:
        todo_id = str(uuid.uuid4())
        event = TimelineEvent(
            scenario=scenario,
            content=snapshot.timeline_entry,
        )
        stamp = now_iso()
        ach_no = sanitize_text(snapshot.fields.ach_no)
        ach_filled_at = sanitize_text(snapshot.fields.ach_filled_at) or (stamp if ach_no else "")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO todos(
                  id, title, current_summary, group_name,
                  environment, product_line, ticket_type, ach_no, ach_filled_at, ticket_version,
                  feature_point, feature_point_source,
                  root_cause_desc, root_cause_desc_source,
                  root_cause, root_cause_source,
                  conclusion_content, conclusion_updated_at,
                  status, created_at, completed_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    todo_id,
                    sanitize_text(snapshot.title),
                    sanitize_text(snapshot.current_summary),
                    sanitize_text(snapshot.fields.group_name),
                    sanitize_text(snapshot.fields.environment),
                    "",
                    sanitize_text(snapshot.fields.ticket_type),
                    ach_no,
                    ach_filled_at,
                    sanitize_text(snapshot.fields.ticket_version),
                    sanitize_text(snapshot.fields.feature_point),
                    sanitize_text(snapshot.fields.feature_point_source),
                    sanitize_text(snapshot.fields.root_cause_desc),
                    sanitize_text(snapshot.fields.root_cause_desc_source),
                    sanitize_text(snapshot.fields.root_cause),
                    sanitize_text(snapshot.fields.root_cause_source),
                    "",
                    "",
                    TodoStatus.OPEN,
                    stamp,
                    "",
                    stamp,
                ),
            )
            self._insert_timeline_event(connection, todo_id, event)
        self._refresh_project_link(todo_id, snapshot.fields.group_name)
        return self.get_todo(todo_id) or TodoItem(id=todo_id)

    def append_analysis_to_todo(
        self,
        todo_id: str,
        snapshot: TicketSnapshot,
        scenario: str,
    ) -> TodoItem | None:
        sanitized_id = sanitize_text(todo_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, current_summary, group_name, environment,
                       product_line, ticket_type, ach_no, ach_filled_at, ticket_version,
                       feature_point, feature_point_source,
                       root_cause_desc, root_cause_desc_source,
                       root_cause, root_cause_source,
                       conclusion_content, conclusion_updated_at,
                       status, created_at, completed_at, updated_at
                FROM todos
                WHERE id = ?
                """,
                (sanitized_id,),
            ).fetchone()
            if row is None:
                return None
            current_todo = self._build_todo_from_row(connection, row)
            merged_fields = merge_summary_fields_for_append(current_todo.summary_fields, snapshot.fields)
            merged_fields.product_line = current_todo.summary_fields.product_line
            if merged_fields.ach_no and not merged_fields.ach_filled_at and not current_todo.summary_fields.ach_no:
                merged_fields.ach_filled_at = now_iso()
            connection.execute(
                """
                UPDATE todos
                SET group_name = ?, environment = ?, product_line = ?, ticket_type = ?, ach_no = ?, ach_filled_at = ?, ticket_version = ?,
                    feature_point = ?, feature_point_source = ?,
                    root_cause_desc = ?, root_cause_desc_source = ?,
                    root_cause = ?, root_cause_source = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    sanitize_text(merged_fields.group_name),
                    sanitize_text(merged_fields.environment),
                    sanitize_text(merged_fields.product_line),
                    sanitize_text(merged_fields.ticket_type),
                    sanitize_text(merged_fields.ach_no),
                    sanitize_text(merged_fields.ach_filled_at),
                    sanitize_text(merged_fields.ticket_version),
                    sanitize_text(merged_fields.feature_point),
                    sanitize_text(merged_fields.feature_point_source),
                    sanitize_text(merged_fields.root_cause_desc),
                    sanitize_text(merged_fields.root_cause_desc_source),
                    sanitize_text(merged_fields.root_cause),
                    sanitize_text(merged_fields.root_cause_source),
                    now_iso(),
                    sanitized_id,
                ),
            )
            self._insert_timeline_event(
                connection,
                sanitized_id,
                TimelineEvent(
                    scenario=scenario,
                    content=snapshot.timeline_entry,
                ),
            )
        self._refresh_project_link(sanitized_id, merged_fields.group_name)
        return self.get_todo(sanitized_id)

    def complete_todo(self, todo_id: str) -> bool:
        completed_at = now_iso()
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE todos SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?",
                (TodoStatus.DONE, completed_at, completed_at, sanitize_text(todo_id)),
            )
        return cursor.rowcount > 0

    def reopen_todo(self, todo_id: str) -> bool:
        updated_at = now_iso()
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE todos SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?",
                (TodoStatus.OPEN, "", updated_at, sanitize_text(todo_id)),
            )
        return cursor.rowcount > 0

    def delete_todo(self, todo_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM todos WHERE id = ?",
                (sanitize_text(todo_id),),
            )
        return cursor.rowcount > 0

    def update_todo(
        self,
        todo_id: str,
        *,
        title: str | None = None,
        current_summary: str | None = None,
        summary_fields: TicketSummaryFields | None = None,
        timeline: list[TimelineEvent] | None = None,
        conclusion: TodoConclusion | None = None,
    ) -> TodoItem | None:
        sanitized_id = sanitize_text(todo_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, current_summary, group_name, environment,
                       product_line, ticket_type, ach_no, ach_filled_at, ticket_version,
                       feature_point, feature_point_source,
                       root_cause_desc, root_cause_desc_source,
                       root_cause, root_cause_source,
                       conclusion_content, conclusion_updated_at,
                       status, created_at, completed_at, updated_at
                FROM todos
                WHERE id = ?
                """,
                (sanitized_id,),
            ).fetchone()
            if row is None:
                return None
            updated_title = sanitize_text(title) or str(row["title"])
            updated_summary = sanitize_text(current_summary) if current_summary is not None else str(row["current_summary"])
            updated_group_name = sanitize_text(summary_fields.group_name) if summary_fields is not None else str(row["group_name"])
            updated_environment = sanitize_text(summary_fields.environment) if summary_fields is not None else str(row["environment"])
            updated_product_line = str(row["product_line"])
            updated_ticket_type = sanitize_text(summary_fields.ticket_type) if summary_fields is not None else str(row["ticket_type"])
            updated_ach_no = (
                sanitize_text(summary_fields.ach_no)
                if summary_fields is not None
                else str(row["ach_no"])
            )
            current_ach_no = str(row["ach_no"])
            current_ach_filled_at = str(row["ach_filled_at"])
            updated_ach_filled_at = current_ach_filled_at
            if summary_fields is not None:
                requested_ach_filled_at = sanitize_text(summary_fields.ach_filled_at)
                if requested_ach_filled_at:
                    updated_ach_filled_at = requested_ach_filled_at
                elif not updated_ach_no:
                    updated_ach_filled_at = ""
                elif not sanitize_text(current_ach_no):
                    updated_ach_filled_at = now_iso()
            updated_ticket_version = (
                sanitize_text(summary_fields.ticket_version)
                if summary_fields is not None
                else str(row["ticket_version"])
            )
            updated_feature_point = (
                sanitize_text(summary_fields.feature_point)
                if summary_fields is not None
                else str(row["feature_point"])
            )
            updated_feature_point_source = (
                sanitize_text(summary_fields.feature_point_source)
                if summary_fields is not None
                else str(row["feature_point_source"])
            )
            updated_root_cause_desc = (
                sanitize_text(summary_fields.root_cause_desc)
                if summary_fields is not None
                else str(row["root_cause_desc"])
            )
            updated_root_cause_desc_source = (
                sanitize_text(summary_fields.root_cause_desc_source)
                if summary_fields is not None
                else str(row["root_cause_desc_source"])
            )
            updated_root_cause = (
                sanitize_text(summary_fields.root_cause)
                if summary_fields is not None
                else str(row["root_cause"])
            )
            updated_root_cause_source = (
                sanitize_text(summary_fields.root_cause_source)
                if summary_fields is not None
                else str(row["root_cause_source"])
            )
            updated_conclusion_content = (
                sanitize_text(conclusion.content)
                if conclusion is not None
                else str(row["conclusion_content"])
            )
            updated_conclusion_at = (
                sanitize_text(conclusion.updated_at) or now_iso()
                if conclusion is not None
                else str(row["conclusion_updated_at"])
            )
            connection.execute(
                """
                UPDATE todos
                SET title = ?, current_summary = ?, group_name = ?, environment = ?, product_line = ?, ticket_type = ?, ach_no = ?, ach_filled_at = ?, ticket_version = ?,
                    feature_point = ?, feature_point_source = ?,
                    root_cause_desc = ?, root_cause_desc_source = ?,
                    root_cause = ?, root_cause_source = ?,
                    conclusion_content = ?, conclusion_updated_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    updated_title,
                    updated_summary,
                    updated_group_name,
                    updated_environment,
                    updated_product_line,
                    updated_ticket_type,
                    updated_ach_no,
                    updated_ach_filled_at,
                    updated_ticket_version,
                    updated_feature_point,
                    updated_feature_point_source,
                    updated_root_cause_desc,
                    updated_root_cause_desc_source,
                    updated_root_cause,
                    updated_root_cause_source,
                    updated_conclusion_content,
                    updated_conclusion_at,
                    now_iso(),
                    sanitized_id,
                ),
            )
            if timeline is not None:
                connection.execute(
                    "DELETE FROM todo_timeline_events WHERE todo_id = ?",
                    (sanitized_id,),
                )
                for event in timeline:
                    self._insert_timeline_event(connection, sanitized_id, event)
            if conclusion is not None:
                connection.execute(
                    "DELETE FROM todo_conclusion_attachments WHERE todo_id = ?",
                    (sanitized_id,),
                )
                for attachment in conclusion.attachments:
                    self._insert_conclusion_attachment(connection, sanitized_id, attachment)
        if summary_fields is not None and updated_group_name != str(row["group_name"]):
            self._refresh_project_link(sanitized_id, updated_group_name)
        return self.get_todo(sanitized_id)

    def unlink_todo_project(self, todo_id: str) -> TodoItem | None:
        sanitized_id = sanitize_text(todo_id)
        if not sanitized_id:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM todos WHERE id = ?",
                (sanitized_id,),
            ).fetchone()
            if row is None:
                return None
            stamp = now_iso()
            connection.execute(
                "DELETE FROM todo_project_links WHERE todo_id = ?",
                (sanitized_id,),
            )
            connection.execute(
                "UPDATE todos SET product_line = '', ticket_version = '', updated_at = ? WHERE id = ?",
                (stamp, sanitized_id),
            )
        return self.get_todo(sanitized_id)

    def _build_todo_from_row(self, connection: sqlite3.Connection, row: sqlite3.Row) -> TodoItem:
        row_payload = dict(row)
        project_link = self._project_repository.get_project_link(str(row["id"]))
        row_payload = self._repair_project_backed_fields(connection, row_payload, project_link)
        timeline_rows = [
            dict(item)
            for item in connection.execute(
                """
                SELECT id, todo_id, timestamp, kind, scenario, event_type, payload_json, status, content, created_at
                FROM todo_timeline_events
                WHERE todo_id = ?
                ORDER BY timestamp ASC, created_at ASC, id ASC
                """,
                (str(row["id"]),),
            ).fetchall()
        ]
        attachment_rows = [
            dict(item)
            for item in connection.execute(
                """
                SELECT
                  todo_timeline_attachments.id,
                  todo_timeline_attachments.event_id,
                  todo_timeline_attachments.name,
                  todo_timeline_attachments.path,
                  todo_timeline_attachments.size_bytes,
                  todo_timeline_attachments.created_at
                FROM todo_timeline_attachments
                JOIN todo_timeline_events ON todo_timeline_events.id = todo_timeline_attachments.event_id
                WHERE todo_timeline_events.todo_id = ?
                ORDER BY todo_timeline_attachments.created_at ASC, todo_timeline_attachments.id ASC
                """,
                (str(row["id"]),),
            ).fetchall()
        ]
        conclusion_attachment_rows = [
            dict(item)
            for item in connection.execute(
                """
                SELECT id, todo_id, name, path, size_bytes, created_at
                FROM todo_conclusion_attachments
                WHERE todo_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (str(row["id"]),),
            ).fetchall()
        ]
        return build_todo_item(
            todo_row=row_payload,
            timeline_rows=timeline_rows,
            attachment_rows=attachment_rows,
            conclusion_attachment_rows=conclusion_attachment_rows,
            project_link_row=project_link.to_dict() if project_link is not None else None,
        )

    def _repair_project_backed_fields(
        self,
        connection: sqlite3.Connection,
        row_payload: dict[str, Any],
        project_link: TodoProjectLink | None,
    ) -> dict[str, Any]:
        if project_link is None or project_link.match_status not in {"matched", "manual", "expired"}:
            return row_payload

        snapshot = project_link.project_snapshot
        current_product_line = sanitize_text(row_payload.get("product_line", ""))
        current_ticket_version = sanitize_text(row_payload.get("ticket_version", ""))
        snapshot_product_line = sanitize_text(snapshot.get("product_line", ""))
        snapshot_ticket_version = sanitize_text(snapshot.get("product_version", ""))
        next_ticket_version = current_ticket_version or snapshot_ticket_version

        if current_product_line == snapshot_product_line and current_ticket_version == next_ticket_version:
            return row_payload

        connection.execute(
            "UPDATE todos SET product_line = ?, ticket_version = ?, updated_at = ? WHERE id = ?",
            (
                snapshot_product_line,
                next_ticket_version,
                now_iso(),
                sanitize_text(row_payload.get("id", "")),
            ),
        )
        row_payload["product_line"] = snapshot_product_line
        row_payload["ticket_version"] = next_ticket_version
        return row_payload

    def _load_todo(self, connection: sqlite3.Connection, todo_id: str) -> TodoItem:
        row = connection.execute(
            """
            SELECT id, title, current_summary, group_name, environment,
                   product_line, ticket_type, ach_no, ach_filled_at, ticket_version,
                   feature_point, feature_point_source,
                   root_cause_desc, root_cause_desc_source,
                   root_cause, root_cause_source,
                   conclusion_content, conclusion_updated_at,
                   status, created_at, completed_at, updated_at
            FROM todos
            WHERE id = ?
            """,
            (sanitize_text(todo_id),),
        ).fetchone()
        if row is None:
            raise KeyError(f"Todo not found: {todo_id}")
        return self._build_todo_from_row(connection, row)

    def _insert_timeline_event(
        self,
        connection: sqlite3.Connection,
        todo_id: str,
        event: TimelineEvent,
    ) -> None:
        created_at = now_iso()
        event_id = sanitize_text(event.id) or str(uuid.uuid4())
        connection.execute(
            """
            INSERT INTO todo_timeline_events(
              id, todo_id, timestamp, kind, scenario, event_type, payload_json, status, content, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                sanitize_text(todo_id),
                sanitize_text(event.timestamp) or now_iso(),
                sanitize_text(event.kind) or "analysis",
                sanitize_text(event.scenario),
                sanitize_text(event.event_type) or "default",
                json.dumps(event.payload or {}, ensure_ascii=False),
                sanitize_text(event.status),
                sanitize_text(event.content),
                sanitize_text(event.created_at) or created_at,
            ),
        )
        for attachment in event.attachments:
            self._insert_attachment(connection, event_id, attachment)

    def _insert_attachment(
        self,
        connection: sqlite3.Connection,
        event_id: str,
        attachment: TimelineAttachment,
    ) -> None:
        connection.execute(
            """
            INSERT INTO todo_timeline_attachments(
              id, event_id, name, path, size_bytes, created_at
            ) VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                sanitize_text(attachment.id) or str(uuid.uuid4()),
                sanitize_text(event_id),
                sanitize_text(attachment.name),
                sanitize_text(attachment.path),
                max(0, int(attachment.size_bytes)),
                now_iso(),
            ),
        )

    def _insert_conclusion_attachment(
        self,
        connection: sqlite3.Connection,
        todo_id: str,
        attachment: TimelineAttachment,
    ) -> None:
        connection.execute(
            """
            INSERT INTO todo_conclusion_attachments(
              id, todo_id, name, path, size_bytes, created_at
            ) VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                sanitize_text(attachment.id) or str(uuid.uuid4()),
                sanitize_text(todo_id),
                sanitize_text(attachment.name),
                sanitize_text(attachment.path),
                max(0, int(attachment.size_bytes)),
                now_iso(),
            ),
        )

    def _refresh_project_link(self, todo_id: str, group_name: str) -> None:
        match_result = self._project_repository.match_project_by_group_name(group_name)
        self._project_repository.bind_todo_to_project(todo_id, match_result)
        self._synchronize_project_fields(todo_id, match_result)

    def _synchronize_project_fields(self, todo_id: str, match_result: ProjectMatchResult) -> None:
        snapshot = match_result.project_snapshot if match_result.status in {"matched", "manual", "expired"} else {}
        product_line = sanitize_text(snapshot.get("product_line", ""))
        ticket_version = sanitize_text(snapshot.get("product_version", ""))
        with self._connect() as connection:
            row = connection.execute(
                "SELECT product_line, ticket_version FROM todos WHERE id = ?",
                (sanitize_text(todo_id),),
            ).fetchone()
            if row is None:
                return
            current_product_line = sanitize_text(row["product_line"])
            current_ticket_version = sanitize_text(row["ticket_version"])
            next_ticket_version = current_ticket_version or ticket_version
            if current_product_line == product_line and current_ticket_version == next_ticket_version:
                return
            connection.execute(
                "UPDATE todos SET product_line = ?, ticket_version = ?, updated_at = ? WHERE id = ?",
                (
                    product_line,
                    next_ticket_version,
                    now_iso(),
                    sanitize_text(todo_id),
                ),
            )

    def _relink_rows(self, rows: list[sqlite3.Row]) -> int:
        relinked_count = 0
        for row in rows:
            todo_id = str(row["id"] or "")
            if not todo_id:
                continue
            previous_link = self._project_repository.get_project_link(todo_id)
            previous_payload = previous_link.to_dict() if previous_link is not None else {}
            self._refresh_project_link(todo_id, str(row["group_name"] or ""))
            current_link = self._project_repository.get_project_link(todo_id)
            current_payload = current_link.to_dict() if current_link is not None else {}
            if current_payload != previous_payload:
                relinked_count += 1
        return relinked_count


class SQLiteLogAnalysisTaskRepository:
    def __init__(self, path_hint: str | None = None) -> None:
        self._db_path = _resolve_database_path(path_hint)
        binding_hint = str(Path(path_hint).parent / "todos.json") if path_hint else None
        self._legacy_todos_path = _resolve_legacy_todos_path(binding_hint)
        self._legacy_bindings_path = _resolve_legacy_bindings_path(path_hint)
        self._migrator = SQLiteStorageMigrator(
            self._db_path,
            legacy_todos_path=self._legacy_todos_path,
            legacy_bindings_path=self._legacy_bindings_path,
        )
        self._migrator.migrate_json_to_sqlite()

    @property
    def path(self) -> str:
        return str(self._db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_task(self, task: LogAnalysisTask) -> LogAnalysisTask:
        created_at = sanitize_text(task.created_at) or now_iso()
        updated_at = sanitize_text(task.updated_at) or created_at
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO log_analysis_tasks(
                  id, todo_id, timeline_entry_id, status, current_step, raw_command,
                  parsed_focus_json, attachment_snapshot_json,
                  investigation_context_json, evidence_bundle_json,
                  result_summary, result_payload_json, error_message,
                  model_binding_used, started_at, completed_at, failed_at,
                  created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    sanitize_text(task.todo_id),
                    sanitize_text(task.timeline_entry_id),
                    sanitize_text(task.status) or "queued",
                    sanitize_text(task.current_step),
                    sanitize_text(task.raw_command),
                    json.dumps(task.parsed_focus_json or {}, ensure_ascii=False),
                    json.dumps(task.attachment_snapshot_json or [], ensure_ascii=False),
                    json.dumps(task.investigation_context_json or {}, ensure_ascii=False),
                    json.dumps(task.evidence_bundle_json or {}, ensure_ascii=False),
                    sanitize_text(task.result_summary),
                    json.dumps(task.result_payload_json or {}, ensure_ascii=False),
                    sanitize_text(task.error_message),
                    sanitize_text(task.model_binding_used),
                    sanitize_text(task.started_at),
                    sanitize_text(task.completed_at),
                    sanitize_text(task.failed_at),
                    created_at,
                    updated_at,
                ),
            )
        return self.get_task(task.id) or task

    def get_task(self, task_id: str) -> LogAnalysisTask | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM log_analysis_tasks WHERE id = ?",
                (sanitize_text(task_id),),
            ).fetchone()
        return LogAnalysisTask.from_row(dict(row)) if row is not None else None

    def get_task_by_timeline_entry(self, todo_id: str, timeline_entry_id: str) -> LogAnalysisTask | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM log_analysis_tasks
                WHERE todo_id = ? AND timeline_entry_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (sanitize_text(todo_id), sanitize_text(timeline_entry_id)),
            ).fetchone()
        return LogAnalysisTask.from_row(dict(row)) if row is not None else None

    def list_recent_tasks(self, todo_id: str, limit: int = 10) -> list[LogAnalysisTask]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM log_analysis_tasks
                WHERE todo_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (sanitize_text(todo_id), max(1, int(limit))),
            ).fetchall()
        return [LogAnalysisTask.from_row(dict(row)) for row in rows]

    def list_task_status_by_timeline_ids(self, todo_id: str, timeline_ids: list[str]) -> dict[str, dict[str, Any]]:
        normalized_ids = [sanitize_text(item) for item in timeline_ids if sanitize_text(item)]
        if not normalized_ids:
            return {}
        placeholders = ", ".join("?" for _ in normalized_ids)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                  id, todo_id, timeline_entry_id, status, current_step, raw_command,
                  parsed_focus_json, attachment_snapshot_json,
                  investigation_context_json, evidence_bundle_json,
                  result_summary, result_payload_json, error_message,
                  model_binding_used, started_at, completed_at, failed_at,
                  created_at, updated_at
                FROM log_analysis_tasks
                WHERE todo_id = ? AND timeline_entry_id IN ({placeholders})
                ORDER BY created_at DESC, id DESC
                """,
                [sanitize_text(todo_id), *normalized_ids],
            ).fetchall()
        payload: dict[str, dict[str, Any]] = {}
        for row in rows:
            task = LogAnalysisTask.from_row(dict(row))
            timeline_entry_id = task.timeline_entry_id
            if not timeline_entry_id or timeline_entry_id in payload:
                continue
            status = str(task.status or "").strip() or "queued"
            payload[timeline_entry_id] = {
                "taskId": task.id,
                "taskStatus": status,
                "taskStatusLabel": self._status_label(status),
                "taskType": "log_analysis",
                "taskStatusDetail": str(task.error_message or task.result_summary or ""),
                "uiStatus": self._ui_status(status),
                "currentStep": task.current_step,
                "rawCommand": task.raw_command,
                "parsedFocus": task.parsed_focus_json,
                "attachmentSnapshot": task.attachment_snapshot_json,
                "investigationContext": task.investigation_context_json,
                "evidenceBundle": task.evidence_bundle_json,
                "resultSummary": task.result_summary,
                "resultPayload": task.result_payload_json,
                "errorMessage": task.error_message,
            }
        return payload

    def mark_running(self, task_id: str, *, started_at: str, current_step: str = "") -> LogAnalysisTask | None:
        return self._update_task_fields(
            task_id,
            status="running",
            current_step=sanitize_text(current_step),
            started_at=sanitize_text(started_at) or now_iso(),
            error_message="",
            failed_at="",
        )

    def update_progress(self, task_id: str, *, current_step: str, status: str = "running") -> LogAnalysisTask | None:
        return self._update_task_fields(
            task_id,
            status=sanitize_text(status) or "running",
            current_step=sanitize_text(current_step),
        )

    def update_context(
        self,
        task_id: str,
        *,
        investigation_context_json: dict[str, Any],
        evidence_bundle_json: dict[str, Any],
        model_binding_used: str = "",
    ) -> LogAnalysisTask | None:
        return self._update_task_fields(
            task_id,
            investigation_context_json=json.dumps(investigation_context_json or {}, ensure_ascii=False),
            evidence_bundle_json=json.dumps(evidence_bundle_json or {}, ensure_ascii=False),
            model_binding_used=sanitize_text(model_binding_used),
        )

    def mark_completed(
        self,
        task_id: str,
        *,
        result_summary: str,
        result_payload_json: dict[str, Any],
        investigation_context_json: dict[str, Any],
        evidence_bundle_json: dict[str, Any],
        model_binding_used: str,
        completed_at: str,
    ) -> LogAnalysisTask | None:
        return self._update_task_fields(
            task_id,
            status="completed",
            result_summary=sanitize_text(result_summary),
            result_payload_json=json.dumps(result_payload_json or {}, ensure_ascii=False),
            investigation_context_json=json.dumps(investigation_context_json or {}, ensure_ascii=False),
            evidence_bundle_json=json.dumps(evidence_bundle_json or {}, ensure_ascii=False),
            model_binding_used=sanitize_text(model_binding_used),
            completed_at=sanitize_text(completed_at) or now_iso(),
            current_step="",
            error_message="",
            failed_at="",
        )

    def mark_failed(self, task_id: str, *, error_message: str, failed_at: str) -> LogAnalysisTask | None:
        return self._update_task_fields(
            task_id,
            status="failed",
            error_message=sanitize_text(error_message),
            failed_at=sanitize_text(failed_at) or now_iso(),
        )

    def _update_task_fields(self, task_id: str, **fields: object) -> LogAnalysisTask | None:
        normalized_task_id = sanitize_text(task_id)
        if not normalized_task_id or not fields:
            return self.get_task(normalized_task_id)
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = list(fields.values())
        values.extend([now_iso(), normalized_task_id])
        with self._connect() as connection:
            connection.execute(
                f"UPDATE log_analysis_tasks SET {assignments}, updated_at = ? WHERE id = ?",
                values,
            )
        return self.get_task(normalized_task_id)

    @staticmethod
    def _status_label(status: str) -> str:
        mapping = {
            "queued": "排队中",
            "running": "分析中",
            "completed": "已完成",
            "failed": "失败",
        }
        return mapping.get(sanitize_text(status), "排队中")

    @staticmethod
    def _ui_status(status: str) -> str:
        normalized = sanitize_text(status)
        if normalized in {"queued", "running"}:
            return "running"
        if normalized in {"completed", "success"}:
            return "success"
        if normalized == "failed":
            return "failed"
        return ""


class SQLiteBindingRepository:
    def __init__(self, path_hint: str | None = None) -> None:
        self._db_path = _resolve_database_path(path_hint)
        binding_hint = str(Path(path_hint).parent / "todos.json") if path_hint else None
        self._legacy_todos_path = _resolve_legacy_todos_path(binding_hint)
        self._legacy_bindings_path = _resolve_legacy_bindings_path(path_hint)
        self._migrator = SQLiteStorageMigrator(
            self._db_path,
            legacy_todos_path=self._legacy_todos_path,
            legacy_bindings_path=self._legacy_bindings_path,
        )
        self._migrator.migrate_json_to_sqlite()

    @property
    def path(self) -> str:
        return str(self._db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def list_bindings(self, todo_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM todo_bindings
                WHERE todo_id = ? AND external_id != ''
                ORDER BY updated_at DESC
                """,
                (sanitize_text(todo_id),),
            ).fetchall()
        return [self._row_payload(row) for row in rows]

    def list_records(self, todo_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM todo_bindings
                WHERE todo_id = ?
                ORDER BY updated_at DESC
                """,
                (sanitize_text(todo_id),),
            ).fetchall()
        return [self._row_payload(row) for row in rows]

    def get_binding(self, todo_id: str, integration_id: str) -> dict[str, Any] | None:
        record = self.get_record(todo_id, integration_id)
        if record is None or not str(record.get("external_id", "")).strip():
            return None
        return record

    def get_record(self, todo_id: str, integration_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM todo_bindings
                WHERE todo_id = ? AND integration_id = ?
                """,
                (sanitize_text(todo_id), sanitize_text(integration_id)),
            ).fetchone()
        return self._row_payload(row) if row is not None else None

    def has_binding(self, todo_id: str, integration_id: str) -> bool:
        return self.get_binding(todo_id, integration_id) is not None

    def upsert_binding(
        self,
        todo_id: str,
        integration_id: str,
        external_id: str,
        *,
        external_url: str = "",
        event_id: str = "",
        event_type: str = "",
        sync_status: str = "",
        metadata: dict[str, Any] | None = None,
        deleted_locally: bool | None = None,
    ) -> dict[str, Any] | None:
        cleaned_external_id = sanitize_text(external_id)
        if not cleaned_external_id:
            return None
        todo_id = sanitize_text(todo_id)
        integration_id = sanitize_text(integration_id)
        with self._connect() as connection:
            todo_exists = connection.execute(
                "SELECT 1 FROM todos WHERE id = ?",
                (todo_id,),
            ).fetchone()
            if todo_exists is None:
                return None
            exists = connection.execute(
                "SELECT created_at FROM todo_bindings WHERE todo_id = ? AND integration_id = ?",
                (todo_id, integration_id),
            ).fetchone()
            created_at = str(exists["created_at"]) if exists is not None else now_iso()
            connection.execute(
                """
                INSERT INTO todo_bindings(
                  todo_id, integration_id, external_id, external_url,
                  last_event_id, last_event_type, last_sync_status,
                  metadata_json, deleted_locally, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(todo_id, integration_id) DO UPDATE SET
                  external_id=excluded.external_id,
                  external_url=excluded.external_url,
                  last_event_id=excluded.last_event_id,
                  last_event_type=excluded.last_event_type,
                  last_sync_status=excluded.last_sync_status,
                  metadata_json=excluded.metadata_json,
                  deleted_locally=excluded.deleted_locally,
                  updated_at=excluded.updated_at
                """,
                (
                    todo_id,
                    integration_id,
                    cleaned_external_id,
                    sanitize_text(external_url),
                    sanitize_text(event_id),
                    sanitize_text(event_type),
                    sanitize_text(sync_status),
                    json.dumps(metadata or {}, ensure_ascii=False),
                    1 if bool(deleted_locally) else 0,
                    created_at,
                    now_iso(),
                ),
            )
        return self.get_record(todo_id, integration_id)

    def update_sync_status(
        self,
        todo_id: str,
        integration_id: str,
        *,
        event_id: str = "",
        event_type: str = "",
        sync_status: str = "",
        metadata: dict[str, Any] | None = None,
        deleted_locally: bool | None = None,
        external_url: str = "",
    ) -> dict[str, Any] | None:
        todo_id = sanitize_text(todo_id)
        integration_id = sanitize_text(integration_id)
        with self._connect() as connection:
            todo_exists = connection.execute(
                "SELECT 1 FROM todos WHERE id = ?",
                (todo_id,),
            ).fetchone()
            if todo_exists is None:
                return None
            existing = connection.execute(
                "SELECT * FROM todo_bindings WHERE todo_id = ? AND integration_id = ?",
                (todo_id, integration_id),
            ).fetchone()
            created_at = str(existing["created_at"]) if existing is not None else now_iso()
            current_external_id = str(existing["external_id"]) if existing is not None else ""
            current_external_url = str(existing["external_url"]) if existing is not None else ""
            current_deleted_locally = bool(existing["deleted_locally"]) if existing is not None else False
            current_metadata = parse_json_object(existing["metadata_json"]) if existing is not None else {}
            connection.execute(
                """
                INSERT INTO todo_bindings(
                  todo_id, integration_id, external_id, external_url,
                  last_event_id, last_event_type, last_sync_status,
                  metadata_json, deleted_locally, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(todo_id, integration_id) DO UPDATE SET
                  external_url=excluded.external_url,
                  last_event_id=excluded.last_event_id,
                  last_event_type=excluded.last_event_type,
                  last_sync_status=excluded.last_sync_status,
                  metadata_json=excluded.metadata_json,
                  deleted_locally=excluded.deleted_locally,
                  updated_at=excluded.updated_at
                """,
                (
                    todo_id,
                    integration_id,
                    current_external_id,
                    sanitize_text(external_url) or current_external_url,
                    sanitize_text(event_id),
                    sanitize_text(event_type),
                    sanitize_text(sync_status),
                    json.dumps(metadata if metadata is not None else current_metadata, ensure_ascii=False),
                    1 if (deleted_locally if deleted_locally is not None else current_deleted_locally) else 0,
                    created_at,
                    now_iso(),
                ),
            )
        return self.get_record(todo_id, integration_id)

    @staticmethod
    def _row_payload(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "todo_id": str(row["todo_id"]),
            "integration_id": str(row["integration_id"]),
            "external_id": str(row["external_id"] or ""),
            "external_url": str(row["external_url"] or ""),
            "created_at": str(row["created_at"] or ""),
            "updated_at": str(row["updated_at"] or ""),
            "last_event_id": str(row["last_event_id"] or ""),
            "last_event_type": str(row["last_event_type"] or ""),
            "last_sync_status": str(row["last_sync_status"] or ""),
            "metadata": parse_json_object(row["metadata_json"]),
            "deleted_locally": bool(row["deleted_locally"]),
        }


def _upsert_todo(connection: sqlite3.Connection, todo: TodoItem) -> None:
    connection.execute(
        """
        INSERT INTO todos(
          id, title, current_summary, group_name, environment,
          product_line, ticket_type, ach_no, ach_filled_at, ticket_version,
          feature_point, feature_point_source,
          root_cause_desc, root_cause_desc_source,
          root_cause, root_cause_source,
          conclusion_content, conclusion_updated_at,
          status, created_at, completed_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          title=excluded.title,
          current_summary=excluded.current_summary,
          group_name=excluded.group_name,
          environment=excluded.environment,
          product_line=excluded.product_line,
          ticket_type=excluded.ticket_type,
          ach_no=excluded.ach_no,
          ach_filled_at=excluded.ach_filled_at,
          ticket_version=excluded.ticket_version,
          feature_point=excluded.feature_point,
          feature_point_source=excluded.feature_point_source,
          root_cause_desc=excluded.root_cause_desc,
          root_cause_desc_source=excluded.root_cause_desc_source,
          root_cause=excluded.root_cause,
          root_cause_source=excluded.root_cause_source,
          conclusion_content=excluded.conclusion_content,
          conclusion_updated_at=excluded.conclusion_updated_at,
          status=excluded.status,
          completed_at=excluded.completed_at,
          updated_at=excluded.updated_at
        """,
        (
            sanitize_text(todo.id),
            sanitize_text(todo.title),
            sanitize_text(todo.current_summary),
            sanitize_text(todo.summary_fields.group_name),
            sanitize_text(todo.summary_fields.environment),
            sanitize_text(todo.summary_fields.product_line),
            sanitize_text(todo.summary_fields.ticket_type),
            sanitize_text(todo.summary_fields.ach_no),
            sanitize_text(todo.summary_fields.ach_filled_at),
            sanitize_text(todo.summary_fields.ticket_version),
            sanitize_text(todo.summary_fields.feature_point),
            sanitize_text(todo.summary_fields.feature_point_source),
            sanitize_text(todo.summary_fields.root_cause_desc),
            sanitize_text(todo.summary_fields.root_cause_desc_source),
            sanitize_text(todo.summary_fields.root_cause),
            sanitize_text(todo.summary_fields.root_cause_source),
            sanitize_text(todo.conclusion.content),
            sanitize_text(todo.conclusion.updated_at),
            sanitize_text(todo.status) or TodoStatus.OPEN,
            sanitize_text(todo.created_at) or now_iso(),
            sanitize_text(todo.completed_at),
            sanitize_text(todo.updated_at) or now_iso(),
        ),
    )
    connection.execute("DELETE FROM todo_timeline_events WHERE todo_id = ?", (sanitize_text(todo.id),))
    connection.execute("DELETE FROM todo_conclusion_attachments WHERE todo_id = ?", (sanitize_text(todo.id),))
    repository = SQLiteTodoRepository.__new__(SQLiteTodoRepository)
    for event in todo.timeline:
        SQLiteTodoRepository._insert_timeline_event(repository, connection, todo.id, event)
    for attachment in todo.conclusion.attachments:
        SQLiteTodoRepository._insert_conclusion_attachment(repository, connection, todo.id, attachment)
    if todo.project_link.match_status:
        connection.execute(
            """
            INSERT INTO todo_project_links(
              todo_id, project_id, match_status, match_reason,
              matched_group_name, matched_alias, project_snapshot_json,
              matched_at, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(todo_id) DO UPDATE SET
              project_id=excluded.project_id,
              match_status=excluded.match_status,
              match_reason=excluded.match_reason,
              matched_group_name=excluded.matched_group_name,
              matched_alias=excluded.matched_alias,
              project_snapshot_json=excluded.project_snapshot_json,
              matched_at=excluded.matched_at,
              updated_at=excluded.updated_at
            """,
            (
                sanitize_text(todo.id),
                sanitize_text(todo.project_link.project_id) or None,
                sanitize_text(todo.project_link.match_status),
                sanitize_text(todo.project_link.match_reason),
                sanitize_text(todo.project_link.matched_group_name),
                sanitize_text(todo.project_link.matched_alias),
                json.dumps(todo.project_link.project_snapshot, ensure_ascii=False),
                sanitize_text(todo.project_link.matched_at) or now_iso(),
                sanitize_text(todo.project_link.updated_at) or now_iso(),
            ),
        )
