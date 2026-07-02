"""SQLite-backed repositories for Todo, bindings, and projects."""
from __future__ import annotations

import json
import sqlite3
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from aica.models import TicketSnapshot, TicketSummaryFields, is_unknown_text, merge_summary_fields_for_append
from aica.paths import aica_database_file, todo_bindings_file, todos_file
from aica.project_management import is_project_active, split_project_product_lines
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
from aica.storage.contracts import ProjectMatchCandidate, ProjectMatchResult, ProjectRecord, ProjectVersionRecord
from aica.text_sanitize import sanitize_text
from aica.todo.models import TimelineAttachment, TimelineEvent, TodoConclusion, TodoItem, TodoProjectLink, TodoStatus
from aica.todo.conclusion_timeline import sync_conclusion_timeline
from aica.analysis.intent import SCENE_PROBLEM_CONCLUSION


SCHEMA_VERSION = "19"
_INITIALIZED_DATABASES: set[str] = set()


def _is_problem_conclusion_scenario(scenario: str) -> bool:
    return sanitize_text(scenario) == "问题结论" or sanitize_text(scenario) == SCENE_PROBLEM_CONCLUSION


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
        project_manager=str(payload.get("project_manager") or ""),
        project_level=str(payload.get("project_level") or "normal"),
        aliases=aliases,
        created_at=str(payload.get("created_at") or now_iso()),
        updated_at=str(payload.get("updated_at") or now_iso()),
    )


def _build_project_version_record(row: sqlite3.Row | dict[str, Any]) -> ProjectVersionRecord:
    payload = dict(row)
    return ProjectVersionRecord(
        id=str(payload.get("id") or ""),
        project_id=str(payload.get("project_id") or ""),
        issue_product=str(payload.get("issue_product") or ""),
        environment=str(payload.get("environment") or ""),
        version=str(payload.get("version") or ""),
        created_at=str(payload.get("created_at") or now_iso()),
        updated_at=str(payload.get("updated_at") or now_iso()),
    )


def _subsequence_score(source: str, keyword: str) -> int:
    source_text = sanitize_text(source).casefold()
    keyword_text = sanitize_text(keyword).casefold()
    if not source_text or not keyword_text:
        return 0
    source_index = 0
    matched = 0
    gaps = 0
    for char in keyword_text:
        char_index = source_text.find(char, source_index)
        if char_index < 0:
            return 0
        if matched > 0:
            gaps += max(0, char_index - source_index)
        source_index = char_index + 1
        matched += 1
    return max(1, matched * 10 - gaps)


def _candidate_score(text: str, keyword: str) -> int:
    source = sanitize_text(text).casefold()
    target = sanitize_text(keyword).casefold()
    if not source or not target:
        return 0
    if source == target:
        return 500
    if target in source:
        return 400 + max(0, 100 - abs(len(source) - len(target)))
    return _subsequence_score(source, target)


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

    def _cache_key(self) -> str:
        try:
            return str(self._db_path.resolve())
        except Exception:
            return str(self._db_path)

    def _mark_initialized(self) -> None:
        _INITIALIZED_DATABASES.add(self._cache_key())

    def _is_initialized(self) -> bool:
        return self._cache_key() in _INITIALIZED_DATABASES

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def ensure_schema(self) -> None:
        if self._is_initialized():
            return
        with self._connect() as connection:
            self._preflight_legacy_tables(connection)
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
        self._mark_initialized()

    def _preflight_legacy_tables(self, connection: sqlite3.Connection) -> None:
        preflight_columns = {
            "todos": {
                "sort_order": "INTEGER NOT NULL DEFAULT 0",
            },
            "projects": {
                "support_ended_at": "TEXT NOT NULL DEFAULT ''",
                "task_order_no": "TEXT NOT NULL DEFAULT ''",
            },
            "project_environments": {
                "scope": "TEXT NOT NULL DEFAULT 'project'",
                "sort_order": "INTEGER NOT NULL DEFAULT 0",
            },
            "environment_access_entries": {
                "sort_order": "INTEGER NOT NULL DEFAULT 0",
            },
        }
        for table_name, columns in preflight_columns.items():
            if not _table_info(connection, table_name):
                continue
            for column_name, column_def in columns.items():
                if not _has_column(connection, table_name, column_name):
                    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")

    def _migrate_schema(self, connection: sqlite3.Connection) -> None:
        if not _has_column(connection, "todos", "ticket_version"):
            connection.execute(
                "ALTER TABLE todos ADD COLUMN ticket_version TEXT NOT NULL DEFAULT ''"
            )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS project_versions (
              id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL,
              issue_product TEXT NOT NULL DEFAULT '',
              environment TEXT NOT NULL DEFAULT '',
              version TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_project_versions_key ON project_versions(project_id, issue_product, environment)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_project_versions_project ON project_versions(project_id, updated_at DESC, created_at DESC)"
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
            "sort_order": "INTEGER NOT NULL DEFAULT 0",
            "product_line": "TEXT NOT NULL DEFAULT ''",
            "product_module": "TEXT NOT NULL DEFAULT ''",
            "reproduction_probability": "TEXT NOT NULL DEFAULT '未知'",
            "ach_no": "TEXT NOT NULL DEFAULT ''",
            "ach_filled_at": "TEXT NOT NULL DEFAULT ''",
            "customer_environment_code": "TEXT NOT NULL DEFAULT ''",
            "customer_environment_value": "TEXT NOT NULL DEFAULT ''",
            "issue_product": "TEXT NOT NULL DEFAULT ''",
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
        attachment_columns = {
            "todo_timeline_attachments": {
                "file_object_id": "TEXT NOT NULL DEFAULT ''",
            },
            "todo_conclusion_attachments": {
                "file_object_id": "TEXT NOT NULL DEFAULT ''",
            },
            "todo_current_summary_attachments": {
                "file_object_id": "TEXT NOT NULL DEFAULT ''",
            },
        }
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS todo_current_summary_attachments (
              id TEXT PRIMARY KEY,
              todo_id TEXT NOT NULL,
              name TEXT NOT NULL,
              path TEXT NOT NULL,
              size_bytes INTEGER NOT NULL DEFAULT 0,
              file_object_id TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              FOREIGN KEY(todo_id) REFERENCES todos(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_current_summary_attachments_todo ON todo_current_summary_attachments(todo_id)"
        )
        for table_name, columns in attachment_columns.items():
            if not _table_info(connection, table_name):
                continue
            for column_name, column_def in columns.items():
                if not _has_column(connection, table_name, column_name):
                    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
        if not _has_column(connection, "todos", "sort_order"):
            return
        connection.execute(
            """
            UPDATE todos
            SET sort_order = COALESCE(
              (
                SELECT COUNT(*)
                FROM todos AS newer
                WHERE newer.status = todos.status
                  AND (
                    newer.updated_at > todos.updated_at
                    OR (newer.updated_at = todos.updated_at AND newer.id > todos.id)
                  )
              ),
              0
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_todos_open_sort_order ON todos(status, sort_order, updated_at DESC)"
        )
        self._migrate_environment_sort_order_columns(connection)
        self._migrate_project_environments_scope(connection)
        connection.execute(
            """
            UPDATE environment_access_entries
            SET access_type = 'web'
            WHERE TRIM(LOWER(COALESCE(access_type, ''))) IN ('', 'http', 'https', 'web')
            """
        )
        self._migrate_projects_without_product_version(connection)
        self._repair_project_foreign_keys_after_projects_rebuild(connection)

    def _migrate_projects_without_product_version(self, connection: sqlite3.Connection) -> None:
        columns = _table_info(connection, "projects")
        if not columns or not _has_column(connection, "projects", "product_version"):
            return
        legacy_table_name = "projects_rebuild_old"
        suffix = 0
        while connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
            (legacy_table_name,),
        ).fetchone() is not None:
            suffix += 1
            legacy_table_name = f"projects_rebuild_old_{suffix}"
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(f"ALTER TABLE projects RENAME TO {legacy_table_name}")
        connection.execute(
            """
            CREATE TABLE projects (
              id TEXT PRIMARY KEY,
              project_name TEXT NOT NULL,
              customer_name TEXT NOT NULL DEFAULT '',
              task_order_no TEXT NOT NULL DEFAULT '',
              follow_up_started_at TEXT NOT NULL DEFAULT '',
              support_ended_at TEXT NOT NULL DEFAULT '',
              product_line TEXT NOT NULL DEFAULT '',
              project_manager TEXT NOT NULL DEFAULT '',
              project_level TEXT NOT NULL DEFAULT 'normal',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO projects(
              id, project_name, customer_name, task_order_no,
              follow_up_started_at, support_ended_at, product_line,
              project_manager, project_level, created_at, updated_at
            )
            SELECT
              id, project_name, COALESCE(customer_name, ''), COALESCE(task_order_no, ''),
              COALESCE(follow_up_started_at, ''), COALESCE(support_ended_at, ''), COALESCE(product_line, ''),
              COALESCE(project_manager, ''), COALESCE(project_level, 'normal'),
              COALESCE(created_at, ''), COALESCE(updated_at, '')
            FROM %s
            """
            % legacy_table_name
        )
        connection.execute(f"DROP TABLE {legacy_table_name}")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_projects_support_end ON projects(support_ended_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_projects_project_name ON projects(project_name)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_projects_task_order_no ON projects(task_order_no)")
        connection.execute("PRAGMA foreign_keys = ON")

    def _repair_project_foreign_keys_after_projects_rebuild(self, connection: sqlite3.Connection) -> None:
        def _needs_project_fk_repair(table_name: str, expected_tables: set[str]) -> bool:
            try:
                rows = connection.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
            except sqlite3.OperationalError:
                return False
            actual_tables = {str(row["table"] or "") for row in rows}
            return actual_tables != expected_tables

        needs_project_group_aliases = _needs_project_fk_repair("project_group_aliases", {"projects"})
        needs_todo_project_links = _needs_project_fk_repair("todo_project_links", {"todos", "projects"})
        needs_project_versions = _needs_project_fk_repair("project_versions", {"projects"})
        needs_project_environments = _needs_project_fk_repair("project_environments", {"projects"})
        if not any(
            (
                needs_project_group_aliases,
                needs_todo_project_links,
                needs_project_versions,
                needs_project_environments,
            )
        ):
            return

        connection.execute("PRAGMA foreign_keys = OFF")

        if needs_project_group_aliases:
            connection.execute("ALTER TABLE project_group_aliases RENAME TO project_group_aliases_old")
            connection.execute(
                """
                CREATE TABLE project_group_aliases (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  alias_name TEXT NOT NULL,
                  alias_name_normalized TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                INSERT INTO project_group_aliases(
                  id, project_id, alias_name, alias_name_normalized, created_at, updated_at
                )
                SELECT
                  id, project_id, alias_name, alias_name_normalized,
                  COALESCE(created_at, ''), COALESCE(updated_at, '')
                FROM project_group_aliases_old
                """
            )
            connection.execute("DROP TABLE project_group_aliases_old")
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_project_group_aliases_normalized ON project_group_aliases(alias_name_normalized, project_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_project_group_alias_lookup ON project_group_aliases(alias_name_normalized)"
            )

        if needs_todo_project_links:
            connection.execute("ALTER TABLE todo_project_links RENAME TO todo_project_links_old")
            connection.execute(
                """
                CREATE TABLE todo_project_links (
                  todo_id TEXT PRIMARY KEY,
                  project_id TEXT,
                  match_status TEXT NOT NULL,
                  match_reason TEXT NOT NULL DEFAULT '',
                  matched_group_name TEXT NOT NULL DEFAULT '',
                  matched_alias TEXT NOT NULL DEFAULT '',
                  project_snapshot_json TEXT NOT NULL DEFAULT '{}',
                  matched_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(todo_id) REFERENCES todos(id) ON DELETE CASCADE,
                  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO todo_project_links(
                  todo_id, project_id, match_status, match_reason,
                  matched_group_name, matched_alias, project_snapshot_json,
                  matched_at, updated_at
                )
                SELECT
                  todo_id, project_id, match_status, COALESCE(match_reason, ''),
                  COALESCE(matched_group_name, ''), COALESCE(matched_alias, ''),
                  COALESCE(project_snapshot_json, '{}'),
                  COALESCE(matched_at, ''), COALESCE(updated_at, '')
                FROM todo_project_links_old
                """
            )
            connection.execute("DROP TABLE todo_project_links_old")

        if needs_project_versions:
            connection.execute("ALTER TABLE project_versions RENAME TO project_versions_old")
            connection.execute(
                """
                CREATE TABLE project_versions (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL,
                  issue_product TEXT NOT NULL DEFAULT '',
                  environment TEXT NOT NULL DEFAULT '',
                  version TEXT NOT NULL DEFAULT '',
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                INSERT INTO project_versions(
                  id, project_id, issue_product, environment, version, created_at, updated_at
                )
                SELECT
                  id, project_id, COALESCE(issue_product, ''), COALESCE(environment, ''),
                  COALESCE(version, ''), COALESCE(created_at, ''), COALESCE(updated_at, '')
                FROM project_versions_old
                """
            )
            connection.execute("DROP TABLE project_versions_old")
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_project_versions_key ON project_versions(project_id, issue_product, environment)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_project_versions_project ON project_versions(project_id, updated_at DESC, created_at DESC)"
            )

        if needs_project_environments:
            connection.execute("ALTER TABLE project_environments RENAME TO project_environments_old_fkfix")
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
                  CASE
                    WHEN COALESCE(scope, 'project') = 'global' OR TRIM(COALESCE(project_id, '')) = '' THEN NULL
                    ELSE project_id
                  END,
                  env_name, COALESCE(scope, 'project'),
                  COALESCE(env_type, ''), COALESCE(sort_order, 0), COALESCE(is_active, 1),
                  COALESCE(note, ''), COALESCE(created_at, ''), COALESCE(updated_at, '')
                FROM project_environments_old_fkfix
                """
            )
            connection.execute("DROP TABLE project_environments_old_fkfix")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_project_environments_project ON project_environments(project_id, scope, is_active, sort_order, updated_at DESC)"
            )

        connection.execute("PRAGMA foreign_keys = ON")

    def _migrate_environment_sort_order_columns(self, connection: sqlite3.Connection) -> None:
        environment_columns = _table_info(connection, "project_environments")
        if environment_columns:
            if not _has_column(connection, "project_environments", "sort_order"):
                connection.execute(
                    "ALTER TABLE project_environments ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_project_environments_project ON project_environments(project_id, scope, is_active, sort_order, updated_at DESC)"
            )
        entry_columns = _table_info(connection, "environment_access_entries")
        if entry_columns:
            if not _has_column(connection, "environment_access_entries", "sort_order"):
                connection.execute(
                    "ALTER TABLE environment_access_entries ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_environment_access_entries_environment ON environment_access_entries(environment_id, is_active, sort_order, updated_at DESC)"
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
        if self._is_initialized():
            return
        self.ensure_schema()
        with self._connect() as connection:
            self._migrate_legacy_todos(connection)
            self._migrate_legacy_bindings(connection)
            self._backfill_ticket_versions(connection)
        self._mark_initialized()

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
              SELECT COALESCE(NULLIF(project_versions.version, ''), '')
              FROM todo_project_links
              JOIN project_versions
                ON project_versions.project_id = todo_project_links.project_id
               AND project_versions.issue_product = COALESCE(todos.issue_product, '')
               AND project_versions.environment = COALESCE(todos.environment, '')
              WHERE todo_project_links.todo_id = todos.id
              LIMIT 1
            )
            WHERE EXISTS (
              SELECT 1
              FROM todo_project_links
              JOIN project_versions
                ON project_versions.project_id = todo_project_links.project_id
               AND project_versions.issue_product = COALESCE(todos.issue_product, '')
               AND project_versions.environment = COALESCE(todos.environment, '')
              WHERE todo_project_links.todo_id = todos.id
            )
              AND COALESCE(todos.ticket_version, '') = ''
              AND COALESCE(
                (
                  SELECT NULLIF(project_versions.version, '')
                  FROM todo_project_links
                  JOIN project_versions
                    ON project_versions.project_id = todo_project_links.project_id
                   AND project_versions.issue_product = COALESCE(todos.issue_product, '')
                   AND project_versions.environment = COALESCE(todos.environment, '')
                  WHERE todo_project_links.todo_id = todos.id
                  LIMIT 1
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
                      project_manager, project_level,
                      created_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      project_name=excluded.project_name,
                      customer_name=excluded.customer_name,
                      task_order_no=excluded.task_order_no,
                      follow_up_started_at=excluded.follow_up_started_at,
                      support_ended_at=excluded.support_ended_at,
                      product_line=excluded.product_line,
                      project_manager=excluded.project_manager,
                      project_level=excluded.project_level,
                      created_at=excluded.created_at,
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
                  project_manager, project_level,
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
                    project.project_manager,
                    *project.aliases,
                ]
                if not any(normalized_query in str(item or "").casefold() for item in haystacks):
                    continue
            projects.append(project)
        return projects

    def list_product_lines(
        self,
        *,
        include_expired: bool = False,
        now: str | None = None,
    ) -> list[str]:
        product_lines: list[str] = []
        seen: set[str] = set()
        for project in self.list_projects(include_expired=include_expired, now=now):
            for product_line in split_project_product_lines(project.product_line):
                normalized = product_line.casefold()
                if normalized in seen:
                    continue
                product_lines.append(product_line)
                seen.add(normalized)
        return product_lines

    def latest_issue_product_for_project(self, project_id: str) -> str:
        normalized_project_id = sanitize_text(project_id)
        if not normalized_project_id:
            return ""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT todos.issue_product
                FROM todos
                JOIN todo_project_links ON todo_project_links.todo_id = todos.id
                WHERE todo_project_links.project_id = ?
                  AND todo_project_links.match_status IN ('matched', 'manual', 'expired')
                  AND TRIM(todos.issue_product) <> ''
                ORDER BY todos.created_at DESC, todos.updated_at DESC, todos.id DESC
                LIMIT 1
                """,
                (normalized_project_id,),
            ).fetchone()
        if row is None:
            return ""
        return sanitize_text(row["issue_product"])

    def latest_environment_for_project(self, project_id: str) -> str:
        normalized_project_id = sanitize_text(project_id)
        if not normalized_project_id:
            return ""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT todos.environment
                FROM todos
                JOIN todo_project_links ON todo_project_links.todo_id = todos.id
                WHERE todo_project_links.project_id = ?
                  AND todo_project_links.match_status IN ('matched', 'manual', 'expired')
                  AND TRIM(todos.environment) <> ''
                ORDER BY todos.created_at DESC, todos.updated_at DESC, todos.id DESC
                LIMIT 1
                """,
                (normalized_project_id,),
            ).fetchone()
        if row is None:
            return ""
        environment = sanitize_text(row["environment"])
        return "" if is_unknown_text(environment) else environment

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
                  project_manager, project_level,
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

    def get_project_by_id(self, project_id: str) -> ProjectRecord | None:
        sanitized_project_id = sanitize_text(project_id)
        if not sanitized_project_id:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                  id, project_name, customer_name, task_order_no,
                  follow_up_started_at, support_ended_at, product_line,
                  project_manager, project_level,
                  created_at, updated_at
                FROM projects
                WHERE id = ?
                LIMIT 1
                """,
                (sanitized_project_id,),
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
                (sanitized_project_id,),
            ).fetchall()
        aliases = tuple(str(item["alias_name"] or "") for item in alias_rows if str(item["alias_name"] or ""))
        return _build_project_record(row, aliases=aliases)

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

    def search_project_candidates_by_group_name(
        self,
        group_name: str,
        *,
        now: str | None = None,
        limit: int = 5,
        include_expired: bool = False,
    ) -> list[ProjectMatchCandidate]:
        normalized = normalize_group_alias(group_name)
        keyword = sanitize_text(group_name)
        if not normalized or not keyword:
            return []
        current_time = sanitize_text(now) or now_iso()
        candidates: dict[str, dict[str, Any]] = {}
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                  projects.id AS project_id,
                  projects.project_name,
                  projects.customer_name,
                  projects.task_order_no,
                  projects.support_ended_at,
                  projects.follow_up_started_at,
                  projects.product_line,
                  projects.project_manager,
                  projects.project_level,
                  project_group_aliases.alias_name
                FROM projects
                LEFT JOIN project_group_aliases ON project_group_aliases.project_id = projects.id
                ORDER BY projects.updated_at DESC, projects.created_at DESC, projects.id DESC, project_group_aliases.created_at ASC
                """
            ).fetchall()
        for row in rows:
            project_id = str(row["project_id"] or "")
            if not project_id:
                continue
            project_name = str(row["project_name"] or "")
            task_order_no = str(row["task_order_no"] or "")
            customer_name = str(row["customer_name"] or "")
            project_snapshot = _build_project_record(
                {
                    "id": row["project_id"],
                    "project_name": row["project_name"],
                    "customer_name": row["customer_name"],
                    "task_order_no": row["task_order_no"],
                    "follow_up_started_at": row["follow_up_started_at"],
                    "support_ended_at": row["support_ended_at"],
                    "product_line": row["product_line"],
                    "project_manager": row["project_manager"],
                    "project_level": row["project_level"],
                }
            ).to_snapshot()
            alias_name = str(row["alias_name"] or "")
            alias_normalized = normalize_group_alias(alias_name)
            support_ended_at = sanitize_text(row["support_ended_at"])
            is_expired = not _is_project_active(support_ended_at, now=current_time)
            if is_expired and not include_expired:
                continue
            score = 0
            match_reason = ""
            if alias_normalized and alias_normalized == normalized:
                score = 1000
                match_reason = "alias_exact"
            else:
                project_name_score = _candidate_score(project_name, keyword)
                task_order_score = _candidate_score(task_order_no, keyword)
                alias_score = _candidate_score(alias_name, keyword)
                customer_score = _candidate_score(customer_name, keyword)
                score = max(project_name_score, task_order_score, alias_score, customer_score)
                if score == project_name_score and project_name_score > 0:
                    match_reason = "project_name_match"
                elif score == task_order_score and task_order_score > 0:
                    match_reason = "task_order_match"
                elif score == alias_score and alias_score > 0:
                    match_reason = "alias_match"
                elif score == customer_score and customer_score > 0:
                    match_reason = "customer_match"
            if score <= 0:
                continue
            existing = candidates.get(project_id)
            if existing is None or score > int(existing["score"]):
                candidates[project_id] = {
                    "score": score,
                    "project_name": project_name,
                    "task_order_no": task_order_no,
                    "customer_name": customer_name,
                    "matched_alias": alias_name,
                    "match_reason": match_reason,
                    "is_expired": is_expired,
                    "project_snapshot": project_snapshot,
                }
            elif score == int(existing["score"]) and match_reason == "alias_exact":
                existing["matched_alias"] = alias_name
                existing["match_reason"] = match_reason
                existing["project_snapshot"] = project_snapshot
        result = [
            ProjectMatchCandidate(
                project_id=project_id,
                project_name=str(item["project_name"] or ""),
                task_order_no=str(item["task_order_no"] or ""),
                customer_name=str(item["customer_name"] or ""),
                matched_alias=str(item["matched_alias"] or ""),
                match_reason=str(item["match_reason"] or ""),
                match_score=int(item["score"]),
                is_expired=bool(item["is_expired"]),
                project_snapshot=dict(item["project_snapshot"] or {}),
            )
            for project_id, item in candidates.items()
        ]
        result.sort(
            key=lambda candidate: (
                candidate.match_score,
                1 if candidate.match_reason == "alias_exact" else 0,
                0 if candidate.is_expired else 1,
                candidate.project_name.casefold(),
                candidate.task_order_no.casefold(),
            ),
            reverse=True,
        )
        return result[: max(0, int(limit))]

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

    def list_project_versions(self, project_id: str) -> list[ProjectVersionRecord]:
        normalized_project_id = sanitize_text(project_id)
        if not normalized_project_id:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, issue_product, environment, version, created_at, updated_at
                FROM project_versions
                WHERE project_id = ?
                ORDER BY updated_at DESC, created_at DESC, id DESC
                """,
                (normalized_project_id,),
            ).fetchall()
        return [_build_project_version_record(row) for row in rows]

    def get_project_version(
        self,
        project_id: str,
        issue_product: str,
        environment: str,
    ) -> ProjectVersionRecord | None:
        normalized_project_id = sanitize_text(project_id)
        normalized_issue_product = sanitize_text(issue_product)
        normalized_environment = sanitize_text(environment)
        if not normalized_project_id or not normalized_issue_product or not normalized_environment:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, project_id, issue_product, environment, version, created_at, updated_at
                FROM project_versions
                WHERE project_id = ? AND issue_product = ? AND environment = ?
                LIMIT 1
                """,
                (normalized_project_id, normalized_issue_product, normalized_environment),
            ).fetchone()
        if row is None:
            return None
        return _build_project_version_record(row)

    def upsert_project_version(
        self,
        project_id: str,
        issue_product: str,
        environment: str,
        version: str,
    ) -> ProjectVersionRecord | None:
        normalized_project_id = sanitize_text(project_id)
        normalized_issue_product = sanitize_text(issue_product)
        normalized_environment = sanitize_text(environment)
        normalized_version = sanitize_text(version)
        if not normalized_project_id or not normalized_issue_product or not normalized_environment or not normalized_version:
            return None
        stamp = now_iso()
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT id, created_at
                FROM project_versions
                WHERE project_id = ? AND issue_product = ? AND environment = ?
                LIMIT 1
                """,
                (normalized_project_id, normalized_issue_product, normalized_environment),
            ).fetchone()
            record_id = str(existing["id"]) if existing is not None else str(uuid.uuid4())
            created_at = str(existing["created_at"]) if existing is not None else stamp
            connection.execute(
                """
                INSERT INTO project_versions(
                  id, project_id, issue_product, environment, version, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, issue_product, environment) DO UPDATE SET
                  version=excluded.version,
                  updated_at=excluded.updated_at
                """,
                (
                    record_id,
                    normalized_project_id,
                    normalized_issue_product,
                    normalized_environment,
                    normalized_version,
                    created_at,
                    stamp,
                ),
            )
        return self.get_project_version(normalized_project_id, normalized_issue_product, normalized_environment)

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
        self._repair_missing_project_link_ids()

    @property
    def path(self) -> str:
        return str(self._db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _apply_latest_project_field_defaults(
        self,
        connection: sqlite3.Connection,
        todo_id: str,
        project_id: str,
    ) -> None:
        normalized_todo_id = sanitize_text(todo_id)
        normalized_project_id = sanitize_text(project_id)
        if not normalized_todo_id or not normalized_project_id:
            return
        current_row = connection.execute(
            """
            SELECT environment, product_line, product_module,
                   customer_environment_code, customer_environment_value, issue_product
                   , ticket_version
            FROM todos
            WHERE id = ?
            """,
            (normalized_todo_id,),
        ).fetchone()
        if current_row is None:
            return
        previous_environment = self._latest_project_field_value(
            connection,
            project_id=normalized_project_id,
            todo_id=normalized_todo_id,
            field_name="environment",
            include_unknown=False,
        )
        previous_product_line = self._latest_project_field_value(
            connection,
            project_id=normalized_project_id,
            todo_id=normalized_todo_id,
            field_name="product_line",
            include_unknown=False,
        )
        previous_product_module = self._latest_project_field_value(
            connection,
            project_id=normalized_project_id,
            todo_id=normalized_todo_id,
            field_name="product_module",
        )
        previous_customer_environment_code = self._latest_project_field_value(
            connection,
            project_id=normalized_project_id,
            todo_id=normalized_todo_id,
            field_name="customer_environment_code",
        )
        previous_customer_environment_value = self._latest_project_field_value(
            connection,
            project_id=normalized_project_id,
            todo_id=normalized_todo_id,
            field_name="customer_environment_value",
        )
        previous_issue_product = self._latest_project_field_value(
            connection,
            project_id=normalized_project_id,
            todo_id=normalized_todo_id,
            field_name="issue_product",
        )

        current_environment = sanitize_text(current_row["environment"])
        current_product_line = sanitize_text(current_row["product_line"])
        current_product_module = sanitize_text(current_row["product_module"])
        current_customer_environment_code = sanitize_text(current_row["customer_environment_code"])
        current_customer_environment_value = sanitize_text(current_row["customer_environment_value"])
        current_issue_product = sanitize_text(current_row["issue_product"])
        current_ticket_version = sanitize_text(current_row["ticket_version"]) if "ticket_version" in current_row.keys() else ""

        updated_environment = previous_environment if is_unknown_text(current_environment) else current_environment
        updated_product_line = previous_product_line if is_unknown_text(current_product_line) else current_product_line
        updated_product_module = current_product_module or previous_product_module
        updated_customer_environment_code = current_customer_environment_code or previous_customer_environment_code
        updated_customer_environment_value = current_customer_environment_value or previous_customer_environment_value
        updated_issue_product = current_issue_product or previous_issue_product
        project_version = self._project_repository.get_project_version(
            normalized_project_id,
            updated_issue_product,
            updated_environment,
        )
        updated_ticket_version = current_ticket_version or (project_version.version if project_version is not None else "")

        if (
            updated_environment == current_environment
            and updated_product_line == current_product_line
            and updated_product_module == current_product_module
            and updated_customer_environment_code == current_customer_environment_code
            and updated_customer_environment_value == current_customer_environment_value
            and updated_issue_product == current_issue_product
            and updated_ticket_version == current_ticket_version
        ):
            return

        connection.execute(
            """
            UPDATE todos
            SET environment = ?, product_line = ?, product_module = ?,
                customer_environment_code = ?, customer_environment_value = ?, issue_product = ?,
                ticket_version = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                updated_environment,
                updated_product_line,
                updated_product_module,
                updated_customer_environment_code,
                updated_customer_environment_value,
                updated_issue_product,
                updated_ticket_version,
                now_iso(),
                normalized_todo_id,
            ),
        )

    def _latest_project_field_value(
        self,
        connection: sqlite3.Connection,
        *,
        project_id: str,
        todo_id: str,
        field_name: str,
        include_unknown: bool = True,
    ) -> str:
        normalized_project_id = sanitize_text(project_id)
        normalized_todo_id = sanitize_text(todo_id)
        normalized_field_name = sanitize_text(field_name)
        allowed_fields = {
            "environment",
            "product_line",
            "product_module",
            "customer_environment_code",
            "customer_environment_value",
            "issue_product",
        }
        if not normalized_project_id or not normalized_todo_id or normalized_field_name not in allowed_fields:
            return ""
        row = connection.execute(
            f"""
            SELECT todos.{normalized_field_name} AS value
            FROM todos
            JOIN todo_project_links ON todo_project_links.todo_id = todos.id
            WHERE todo_project_links.project_id = ?
              AND todo_project_links.todo_id <> ?
              AND todo_project_links.match_status IN ('matched', 'manual')
              AND TRIM(COALESCE(todos.{normalized_field_name}, '')) <> ''
            ORDER BY COALESCE(todos.updated_at, todos.created_at) DESC, todos.created_at DESC, todos.id DESC
            """,
            (normalized_project_id, normalized_todo_id),
        ).fetchall()
        for item in row:
            value = sanitize_text(item["value"])
            if not value:
                continue
            if not include_unknown and is_unknown_text(value):
                continue
            return value
        return ""

    def _upsert_project_version_from_todo(
        self,
        todo_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        normalized_todo_id = sanitize_text(todo_id)
        if not normalized_todo_id:
            return
        owns_connection = connection is None
        active_connection = connection or self._connect()
        try:
            project_link = self._repair_missing_project_link_project_id(
                normalized_todo_id,
                connection=active_connection,
            )
            row = active_connection.execute(
                """
                SELECT
                  todos.environment,
                  todos.issue_product,
                  todos.ticket_version,
                  todo_project_links.project_id,
                  todo_project_links.match_status
                FROM todos
                LEFT JOIN todo_project_links ON todo_project_links.todo_id = todos.id
                WHERE todos.id = ?
                LIMIT 1
                """,
                (normalized_todo_id,),
            ).fetchone()
            if row is None:
                return
            project_id = sanitize_text(project_link.project_id if project_link is not None else row["project_id"])
            match_status = sanitize_text(project_link.match_status if project_link is not None else row["match_status"])
            environment = sanitize_text(row["environment"])
            issue_product = sanitize_text(row["issue_product"])
            ticket_version = sanitize_text(row["ticket_version"])
            if match_status not in {"matched", "manual"}:
                return
            self._project_repository.upsert_project_version(project_id, issue_product, environment, ticket_version)
        finally:
            if owns_connection:
                active_connection.close()

    def _refresh_ticket_version_from_project_version(
        self,
        todo_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        normalized_todo_id = sanitize_text(todo_id)
        if not normalized_todo_id:
            return
        owns_connection = connection is None
        active_connection = connection or self._connect()
        try:
            project_link = self._repair_missing_project_link_project_id(
                normalized_todo_id,
                connection=active_connection,
            )
            row = active_connection.execute(
                """
                SELECT
                  todos.ticket_version,
                  todos.environment,
                  todos.issue_product,
                  todo_project_links.project_id,
                  todo_project_links.match_status
                FROM todos
                LEFT JOIN todo_project_links ON todo_project_links.todo_id = todos.id
                WHERE todos.id = ?
                LIMIT 1
                """,
                (normalized_todo_id,),
            ).fetchone()
            if row is None:
                return
            current_ticket_version = sanitize_text(row["ticket_version"])
            if current_ticket_version:
                return
            project_id = sanitize_text(project_link.project_id if project_link is not None else row["project_id"])
            match_status = sanitize_text(project_link.match_status if project_link is not None else row["match_status"])
            if match_status not in {"matched", "manual"}:
                return
            environment = sanitize_text(row["environment"])
            issue_product = sanitize_text(row["issue_product"])
            if not environment or not issue_product or not project_id:
                return
            project_version = self._project_repository.get_project_version(project_id, issue_product, environment)
            version = sanitize_text(project_version.version) if project_version is not None else ""
            if not version:
                return
            active_connection.execute(
                "UPDATE todos SET ticket_version = ?, updated_at = ? WHERE id = ?",
                (version, now_iso(), normalized_todo_id),
            )
        finally:
            if owns_connection:
                active_connection.close()

    def _resolve_project_for_broken_link(
        self,
        link: TodoProjectLink,
        *,
        group_name: str = "",
    ) -> ProjectRecord | None:
        snapshot = dict(link.project_snapshot or {})
        snapshot_project_id = sanitize_text(snapshot.get("project_id"))
        if snapshot_project_id:
            project = self._project_repository.get_project_by_id(snapshot_project_id)
            if project is not None:
                return project
        snapshot_task_order_no = sanitize_text(snapshot.get("task_order_no"))
        if snapshot_task_order_no:
            project = self._project_repository.get_project_by_task_order_no(snapshot_task_order_no)
            if project is not None:
                return project
        candidate_group_name = sanitize_text(link.matched_group_name) or sanitize_text(group_name)
        if not candidate_group_name:
            return None
        match_result = self._project_repository.match_project_by_group_name(candidate_group_name)
        if sanitize_text(match_result.status) not in {"matched", "manual"}:
            return None
        return self._project_repository.get_project_by_id(match_result.project_id)

    def _repair_missing_project_link_project_id(
        self,
        todo_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> TodoProjectLink | None:
        normalized_todo_id = sanitize_text(todo_id)
        if not normalized_todo_id:
            return None
        owns_connection = connection is None
        active_connection = connection or self._connect()
        try:
            row = active_connection.execute(
                """
                SELECT
                  todo_project_links.todo_id,
                  todo_project_links.project_id,
                  todo_project_links.match_status,
                  todo_project_links.match_reason,
                  todo_project_links.matched_group_name,
                  todo_project_links.matched_alias,
                  todo_project_links.project_snapshot_json,
                  todo_project_links.matched_at,
                  todo_project_links.updated_at,
                  todos.group_name
                FROM todo_project_links
                JOIN todos ON todos.id = todo_project_links.todo_id
                WHERE todo_project_links.todo_id = ?
                LIMIT 1
                """,
                (normalized_todo_id,),
            ).fetchone()
            if row is None:
                return None
            link = build_project_link(
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
            if link.project_id or link.match_status not in {"matched", "manual"}:
                return link
            project = self._resolve_project_for_broken_link(
                link,
                group_name=str(row["group_name"] or ""),
            )
            if project is None:
                return link
            repaired_snapshot = project.to_snapshot()
            repaired_link = TodoProjectLink(
                todo_id=normalized_todo_id,
                project_id=project.id,
                match_status=link.match_status,
                match_reason=link.match_reason or "repair_missing_project_id",
                matched_group_name=link.matched_group_name or sanitize_text(row["group_name"]),
                matched_alias=link.matched_alias,
                project_snapshot=repaired_snapshot,
                matched_at=link.matched_at or now_iso(),
                updated_at=now_iso(),
            )
            active_connection.execute(
                """
                UPDATE todo_project_links
                SET project_id = ?, match_status = ?, match_reason = ?,
                    matched_group_name = ?, matched_alias = ?, project_snapshot_json = ?,
                    matched_at = ?, updated_at = ?
                WHERE todo_id = ?
                """,
                (
                    repaired_link.project_id,
                    repaired_link.match_status,
                    repaired_link.match_reason,
                    repaired_link.matched_group_name,
                    repaired_link.matched_alias,
                    json.dumps(repaired_link.project_snapshot, ensure_ascii=False),
                    repaired_link.matched_at,
                    repaired_link.updated_at,
                    normalized_todo_id,
                ),
            )
            return repaired_link
        finally:
            if owns_connection:
                active_connection.close()

    def _repair_missing_project_link_ids(self) -> None:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT todo_id
                FROM todo_project_links
                WHERE COALESCE(TRIM(project_id), '') = ''
                  AND match_status IN ('matched', 'manual')
                """
            ).fetchall()
            for row in rows:
                self._repair_missing_project_link_project_id(
                    str(row["todo_id"] or ""),
                    connection=connection,
                )

    def list_todos(self, *, query: str = "", status: str = TodoStatus.OPEN) -> list[TodoItem]:
        normalized_query = sanitize_text(query).lower()
        normalized_status = sanitize_text(status).lower() or TodoStatus.OPEN
        if normalized_status not in {TodoStatus.OPEN, TodoStatus.DONE, "all", "done_missing_ach", "today_done"}:
            normalized_status = TodoStatus.OPEN

        sql = """
            SELECT DISTINCT
              todos.id, todos.title, todos.current_summary, todos.group_name, todos.environment,
              todos.ticket_type, todos.reproduction_probability, todos.customer_environment_code, todos.customer_environment_value,
              todos.ach_no, todos.ach_filled_at, todos.ticket_version,
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
                OR LOWER(todos.reproduction_probability) LIKE ?
                OR LOWER(todos.customer_environment_value) LIKE ?
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
            params.extend([pattern] * 15)
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
                       product_line, product_module, ticket_type, reproduction_probability, customer_environment_code, customer_environment_value, issue_product,
                       ach_no, ach_filled_at, ticket_version,
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
            project_link = self._repair_missing_project_link_project_id(
                sanitize_text(todo_id),
                connection=connection,
            )
            project_id = sanitize_text(project_link.project_id if project_link is not None else "")
            match_status = sanitize_text(project_link.match_status if project_link is not None else "")
            if project_id and match_status in {"matched", "manual"}:
                self._apply_latest_project_field_defaults(connection, sanitize_text(todo_id), project_id)
                row = connection.execute(
                    """
                    SELECT id, title, current_summary, group_name, environment,
                           product_line, product_module, ticket_type, reproduction_probability, customer_environment_code, customer_environment_value, issue_product,
                           ach_no, ach_filled_at, ticket_version,
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
        stamp = now_iso()
        ach_no = sanitize_text(snapshot.fields.ach_no)
        ach_filled_at = sanitize_text(snapshot.fields.ach_filled_at) or (stamp if ach_no else "")
        is_problem_conclusion = _is_problem_conclusion_scenario(scenario)
        conclusion = TodoConclusion(
            content=sanitize_text(snapshot.timeline_entry),
            updated_at=stamp,
        ) if is_problem_conclusion else TodoConclusion()
        timeline = (
            sync_conclusion_timeline([], conclusion)
            if is_problem_conclusion
            else [
                TimelineEvent(
                    scenario=scenario,
                    content=snapshot.timeline_entry,
                )
            ]
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO todos(
                  id, title, current_summary, group_name,
                  environment, product_line, product_module, ticket_type, reproduction_probability, customer_environment_code, customer_environment_value,
                  issue_product,
                  ach_no, ach_filled_at, ticket_version,
                  feature_point, feature_point_source,
                  root_cause_desc, root_cause_desc_source,
                  root_cause, root_cause_source,
                  conclusion_content, conclusion_updated_at,
                  status, created_at, completed_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    todo_id,
                    sanitize_text(snapshot.title),
                    sanitize_text(snapshot.current_summary),
                    sanitize_text(snapshot.fields.group_name),
                    sanitize_text(snapshot.fields.environment),
                    sanitize_text(snapshot.fields.product_line),
                    sanitize_text(snapshot.fields.product_module),
                    sanitize_text(snapshot.fields.ticket_type),
                    sanitize_text(snapshot.fields.reproduction_probability),
                    sanitize_text(snapshot.fields.customer_environment_code),
                    sanitize_text(snapshot.fields.customer_environment_value),
                    sanitize_text(snapshot.fields.issue_product),
                    ach_no,
                    ach_filled_at,
                    sanitize_text(snapshot.fields.ticket_version),
                    sanitize_text(snapshot.fields.feature_point),
                    sanitize_text(snapshot.fields.feature_point_source),
                    sanitize_text(snapshot.fields.root_cause_desc),
                    sanitize_text(snapshot.fields.root_cause_desc_source),
                    sanitize_text(snapshot.fields.root_cause),
                    sanitize_text(snapshot.fields.root_cause_source),
                    sanitize_text(conclusion.content),
                    sanitize_text(conclusion.updated_at),
                    TodoStatus.OPEN,
                    stamp,
                    "",
                    stamp,
                ),
            )
            for event in timeline:
                self._insert_timeline_event(connection, todo_id, event)
        self._refresh_project_link(todo_id, snapshot.fields.group_name, snapshot.project_link)
        self._upsert_project_version_from_todo(todo_id)
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
                       product_line, product_module, ticket_type, reproduction_probability, customer_environment_code, customer_environment_value, issue_product,
                       ach_no, ach_filled_at, ticket_version,
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
            is_problem_conclusion = _is_problem_conclusion_scenario(scenario)
            connection.execute(
                """
                UPDATE todos
                SET group_name = ?, environment = ?, product_line = ?, product_module = ?, ticket_type = ?, reproduction_probability = ?, customer_environment_code = ?, customer_environment_value = ?, issue_product = ?, ach_no = ?, ach_filled_at = ?, ticket_version = ?,
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
                    sanitize_text(merged_fields.product_module),
                    sanitize_text(merged_fields.ticket_type),
                    sanitize_text(merged_fields.reproduction_probability),
                    sanitize_text(merged_fields.customer_environment_code),
                    sanitize_text(merged_fields.customer_environment_value),
                    sanitize_text(merged_fields.issue_product),
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
            if is_problem_conclusion:
                updated_conclusion = TodoConclusion(
                    content=sanitize_text(snapshot.timeline_entry),
                    updated_at=now_iso(),
                    attachments=list(current_todo.conclusion.attachments),
                )
                updated_timeline = sync_conclusion_timeline(list(current_todo.timeline), updated_conclusion)
                connection.execute(
                    """
                    UPDATE todos
                    SET conclusion_content = ?, conclusion_updated_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        sanitize_text(updated_conclusion.content),
                        sanitize_text(updated_conclusion.updated_at),
                        now_iso(),
                        sanitized_id,
                    ),
                )
                connection.execute(
                    "DELETE FROM todo_timeline_events WHERE todo_id = ?",
                    (sanitized_id,),
                )
                for event in updated_timeline:
                    self._insert_timeline_event(connection, sanitized_id, event)
            else:
                self._insert_timeline_event(
                    connection,
                    sanitized_id,
                    TimelineEvent(
                        scenario=scenario,
                        content=snapshot.timeline_entry,
                    ),
                )
        self._refresh_project_link(sanitized_id, merged_fields.group_name, snapshot.project_link)
        self._upsert_project_version_from_todo(sanitized_id)
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
        current_summary_attachments: list[TimelineAttachment] | None = None,
        summary_fields: TicketSummaryFields | None = None,
        timeline: list[TimelineEvent] | None = None,
        conclusion: TodoConclusion | None = None,
    ) -> TodoItem | None:
        sanitized_id = sanitize_text(todo_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, current_summary, group_name, environment,
                       product_line, product_module, ticket_type, reproduction_probability, customer_environment_code, customer_environment_value, issue_product,
                       ach_no, ach_filled_at, ticket_version,
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
            updated_product_line = (
                sanitize_text(summary_fields.product_line)
                if summary_fields is not None
                else str(row["product_line"])
            )
            updated_product_module = (
                sanitize_text(summary_fields.product_module)
                if summary_fields is not None
                else str(row["product_module"])
            )
            updated_ticket_type = sanitize_text(summary_fields.ticket_type) if summary_fields is not None else str(row["ticket_type"])
            updated_reproduction_probability = (
                sanitize_text(summary_fields.reproduction_probability)
                if summary_fields is not None
                else str(row["reproduction_probability"])
            )
            updated_customer_environment_code = (
                sanitize_text(summary_fields.customer_environment_code)
                if summary_fields is not None
                else str(row["customer_environment_code"])
            )
            updated_customer_environment_value = (
                sanitize_text(summary_fields.customer_environment_value)
                if summary_fields is not None
                else str(row["customer_environment_value"])
            )
            updated_issue_product = (
                sanitize_text(summary_fields.issue_product)
                if summary_fields is not None
                else str(row["issue_product"])
            )
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
            requested_ticket_version = (
                sanitize_text(summary_fields.ticket_version)
                if summary_fields is not None
                else str(row["ticket_version"])
            )
            updated_ticket_version = requested_ticket_version
            if summary_fields is not None and not requested_ticket_version:
                project_link = self._project_repository.get_project_link(sanitized_id)
                project_id = sanitize_text(project_link.project_id if project_link is not None else "")
                match_status = sanitize_text(project_link.match_status if project_link is not None else "")
                if project_id and match_status in {"matched", "manual"} and updated_environment and updated_issue_product:
                    project_version = self._project_repository.get_project_version(
                        project_id,
                        updated_issue_product,
                        updated_environment,
                    )
                    if project_version is not None:
                        updated_ticket_version = sanitize_text(project_version.version)
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
                SET title = ?, current_summary = ?, group_name = ?, environment = ?, product_line = ?, product_module = ?, ticket_type = ?, reproduction_probability = ?, customer_environment_code = ?, customer_environment_value = ?, issue_product = ?, ach_no = ?, ach_filled_at = ?, ticket_version = ?,
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
                    updated_product_module,
                    updated_ticket_type,
                    updated_reproduction_probability,
                    updated_customer_environment_code,
                    updated_customer_environment_value,
                    updated_issue_product,
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
            if current_summary_attachments is not None:
                connection.execute(
                    "DELETE FROM todo_current_summary_attachments WHERE todo_id = ?",
                    (sanitized_id,),
                )
                for attachment in current_summary_attachments:
                    self._insert_current_summary_attachment(connection, sanitized_id, attachment)
            if conclusion is not None:
                connection.execute(
                    "DELETE FROM todo_conclusion_attachments WHERE todo_id = ?",
                    (sanitized_id,),
                )
                for attachment in conclusion.attachments:
                    self._insert_conclusion_attachment(connection, sanitized_id, attachment)
        if summary_fields is not None and updated_group_name != str(row["group_name"]):
            self._refresh_project_link(sanitized_id, updated_group_name)
        if summary_fields is not None:
            self._upsert_project_version_from_todo(sanitized_id)
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
                "UPDATE todos SET product_line = '', product_module = '', ticket_version = '', updated_at = ? WHERE id = ?",
                (stamp, sanitized_id),
            )
        return self.get_todo(sanitized_id)

    def upsert_imported_todo(self, todo: TodoItem) -> TodoItem | None:
        if not sanitize_text(todo.id):
            return None
        with self._connect() as connection:
            _upsert_todo(connection, todo)
            self._repair_missing_project_link_project_id(todo.id, connection=connection)
        return self.get_todo(todo.id)

    def _build_todo_from_row(self, connection: sqlite3.Connection, row: sqlite3.Row) -> TodoItem:
        row_payload = dict(row)
        project_link = self._project_repository.get_project_link(str(row["id"]))
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
                  todo_timeline_attachments.file_object_id,
                  todo_timeline_attachments.created_at
                FROM todo_timeline_attachments
                JOIN todo_timeline_events ON todo_timeline_events.id = todo_timeline_attachments.event_id
                WHERE todo_timeline_events.todo_id = ?
                ORDER BY todo_timeline_attachments.created_at ASC, todo_timeline_attachments.id ASC
                """,
                (str(row["id"]),),
            ).fetchall()
        ]
        current_summary_attachment_rows = [
            dict(item)
            for item in connection.execute(
                """
                SELECT id, todo_id, name, path, size_bytes, file_object_id, created_at
                FROM todo_current_summary_attachments
                WHERE todo_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (str(row["id"]),),
            ).fetchall()
        ]
        conclusion_attachment_rows = [
            dict(item)
            for item in connection.execute(
                """
                SELECT id, todo_id, name, path, size_bytes, file_object_id, created_at
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
            current_summary_attachment_rows=current_summary_attachment_rows,
            conclusion_attachment_rows=conclusion_attachment_rows,
            project_link_row=project_link.to_dict() if project_link is not None else None,
        )

    def _load_todo(self, connection: sqlite3.Connection, todo_id: str) -> TodoItem:
        row = connection.execute(
            """
            SELECT id, title, current_summary, group_name, environment,
                   product_line, product_module, ticket_type, reproduction_probability, customer_environment_code, customer_environment_value,
                   ach_no, ach_filled_at, ticket_version,
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
              id, event_id, name, path, size_bytes, file_object_id, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sanitize_text(attachment.id) or str(uuid.uuid4()),
                sanitize_text(event_id),
                sanitize_text(attachment.name),
                sanitize_text(attachment.path),
                max(0, int(attachment.size_bytes)),
                sanitize_text(attachment.file_object_id),
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
              id, todo_id, name, path, size_bytes, file_object_id, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sanitize_text(attachment.id) or str(uuid.uuid4()),
                sanitize_text(todo_id),
                sanitize_text(attachment.name),
                sanitize_text(attachment.path),
                max(0, int(attachment.size_bytes)),
                sanitize_text(attachment.file_object_id),
                now_iso(),
            ),
        )

    def _insert_current_summary_attachment(
        self,
        connection: sqlite3.Connection,
        todo_id: str,
        attachment: TimelineAttachment,
    ) -> None:
        connection.execute(
            """
            INSERT INTO todo_current_summary_attachments(
              id, todo_id, name, path, size_bytes, file_object_id, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sanitize_text(attachment.id) or str(uuid.uuid4()),
                sanitize_text(todo_id),
                sanitize_text(attachment.name),
                sanitize_text(attachment.path),
                max(0, int(attachment.size_bytes)),
                sanitize_text(attachment.file_object_id),
                now_iso(),
            ),
        )

    def _refresh_project_link(self, todo_id: str, group_name: str, project_link_payload: dict[str, Any] | None = None) -> None:
        payload = project_link_payload if isinstance(project_link_payload, dict) else {}
        project_id = sanitize_text(payload.get("project_id") or payload.get("projectId"))
        if project_id:
            project = self._project_repository.get_project_by_id(project_id)
            if project is not None:
                match_result = ProjectMatchResult(
                    status="manual",
                    reason=str(payload.get("match_reason") or payload.get("matchReason") or "manual_project_selection"),
                    project_id=project.id,
                    matched_group_name=sanitize_text(group_name),
                    matched_alias=str(payload.get("matched_alias") or payload.get("matchedAlias") or ""),
                    project_snapshot=project.to_snapshot(),
                )
                self._project_repository.bind_todo_to_project(todo_id, match_result)
                with self._connect() as connection:
                    self._apply_latest_project_field_defaults(connection, todo_id, project.id)
                return
        match_result = self._project_repository.match_project_by_group_name(group_name)
        self._project_repository.bind_todo_to_project(todo_id, match_result)
        if sanitize_text(match_result.project_id) and sanitize_text(match_result.status) in {"matched", "manual"}:
            with self._connect() as connection:
                self._apply_latest_project_field_defaults(connection, todo_id, match_result.project_id)

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
          product_line, product_module, ticket_type, reproduction_probability, customer_environment_code, customer_environment_value,
          issue_product, ach_no, ach_filled_at, ticket_version,
          feature_point, feature_point_source,
          root_cause_desc, root_cause_desc_source,
          root_cause, root_cause_source,
          conclusion_content, conclusion_updated_at,
          status, created_at, completed_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          title=excluded.title,
          current_summary=excluded.current_summary,
          group_name=excluded.group_name,
          environment=excluded.environment,
          product_line=excluded.product_line,
          product_module=excluded.product_module,
          ticket_type=excluded.ticket_type,
          reproduction_probability=excluded.reproduction_probability,
          customer_environment_code=excluded.customer_environment_code,
          customer_environment_value=excluded.customer_environment_value,
          issue_product=excluded.issue_product,
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
            sanitize_text(todo.summary_fields.product_module),
            sanitize_text(todo.summary_fields.ticket_type),
            sanitize_text(todo.summary_fields.reproduction_probability),
            sanitize_text(todo.summary_fields.customer_environment_code),
            sanitize_text(todo.summary_fields.customer_environment_value),
            sanitize_text(todo.summary_fields.issue_product),
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
    connection.execute("DELETE FROM todo_current_summary_attachments WHERE todo_id = ?", (sanitize_text(todo.id),))
    connection.execute("DELETE FROM todo_conclusion_attachments WHERE todo_id = ?", (sanitize_text(todo.id),))
    repository = SQLiteTodoRepository.__new__(SQLiteTodoRepository)
    for event in todo.timeline:
        SQLiteTodoRepository._insert_timeline_event(repository, connection, todo.id, event)
    for attachment in todo.current_summary_attachments:
        SQLiteTodoRepository._insert_current_summary_attachment(repository, connection, todo.id, attachment)
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
