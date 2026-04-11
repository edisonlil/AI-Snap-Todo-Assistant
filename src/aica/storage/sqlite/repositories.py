"""SQLite-backed repositories for Todo, bindings, and projects."""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from aica.models import TicketSnapshot, TicketSummaryFields, merge_summary_fields_for_append
from aica.paths import aica_database_file, todo_bindings_file, todos_file
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
from aica.todo_models import TimelineAttachment, TimelineEvent, TodoItem, TodoProjectLink, TodoStatus


SCHEMA_VERSION = "1"


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


def _is_project_active(support_ended_at: str, *, now: str | None = None) -> bool:
    normalized_end = sanitize_text(support_ended_at)
    current_time = sanitize_text(now) or now_iso()
    return not normalized_end or normalized_end >= current_time


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
            connection.execute(
                """
                INSERT INTO schema_meta(key, value)
                VALUES('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (SCHEMA_VERSION,),
            )

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

    def list_active_todos(self) -> list[TodoItem]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, current_summary, group_name, environment,
                       ticket_type, status, created_at, updated_at
                FROM todos
                WHERE status = ?
                ORDER BY updated_at DESC
                """,
                (TodoStatus.OPEN,),
            ).fetchall()
            return [self._load_todo(connection, str(row["id"])) for row in rows]

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
                       ticket_type, status, created_at, updated_at
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
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO todos(
                  id, title, current_summary, group_name,
                  environment, ticket_type, status, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    todo_id,
                    sanitize_text(snapshot.title),
                    sanitize_text(snapshot.current_summary),
                    sanitize_text(snapshot.fields.group_name),
                    sanitize_text(snapshot.fields.environment),
                    sanitize_text(snapshot.fields.ticket_type),
                    TodoStatus.OPEN,
                    stamp,
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
                       ticket_type, status, created_at, updated_at
                FROM todos
                WHERE id = ?
                """,
                (sanitized_id,),
            ).fetchone()
            if row is None:
                return None
            current_todo = self._build_todo_from_row(connection, row)
            merged_fields = merge_summary_fields_for_append(current_todo.summary_fields, snapshot.fields)
            connection.execute(
                """
                UPDATE todos
                SET group_name = ?, environment = ?, ticket_type = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    sanitize_text(merged_fields.group_name),
                    sanitize_text(merged_fields.environment),
                    sanitize_text(merged_fields.ticket_type),
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
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE todos SET status = ?, updated_at = ? WHERE id = ?",
                (TodoStatus.DONE, now_iso(), sanitize_text(todo_id)),
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
    ) -> TodoItem | None:
        sanitized_id = sanitize_text(todo_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, current_summary, group_name, environment,
                       ticket_type, status, created_at, updated_at
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
            updated_ticket_type = sanitize_text(summary_fields.ticket_type) if summary_fields is not None else str(row["ticket_type"])
            connection.execute(
                """
                UPDATE todos
                SET title = ?, current_summary = ?, group_name = ?, environment = ?, ticket_type = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    updated_title,
                    updated_summary,
                    updated_group_name,
                    updated_environment,
                    updated_ticket_type,
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
        if summary_fields is not None:
            self._refresh_project_link(sanitized_id, updated_group_name)
        return self.get_todo(sanitized_id)

    def _build_todo_from_row(self, connection: sqlite3.Connection, row: sqlite3.Row) -> TodoItem:
        timeline_rows = [
            dict(item)
            for item in connection.execute(
                """
                SELECT id, todo_id, timestamp, kind, scenario, content, created_at
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
        project_link = self._project_repository.get_project_link(str(row["id"]))
        return build_todo_item(
            todo_row=dict(row),
            timeline_rows=timeline_rows,
            attachment_rows=attachment_rows,
            project_link_row=project_link.to_dict() if project_link is not None else None,
        )

    def _load_todo(self, connection: sqlite3.Connection, todo_id: str) -> TodoItem:
        row = connection.execute(
            """
            SELECT id, title, current_summary, group_name, environment,
                   ticket_type, status, created_at, updated_at
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
              id, todo_id, timestamp, kind, scenario, content, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                sanitize_text(todo_id),
                sanitize_text(event.timestamp) or now_iso(),
                sanitize_text(event.kind) or "analysis",
                sanitize_text(event.scenario),
                sanitize_text(event.content),
                created_at,
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

    def _refresh_project_link(self, todo_id: str, group_name: str) -> None:
        match_result = self._project_repository.match_project_by_group_name(group_name)
        self._project_repository.bind_todo_to_project(todo_id, match_result)

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
          ticket_type, status, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          title=excluded.title,
          current_summary=excluded.current_summary,
          group_name=excluded.group_name,
          environment=excluded.environment,
          ticket_type=excluded.ticket_type,
          status=excluded.status,
          updated_at=excluded.updated_at
        """,
        (
            sanitize_text(todo.id),
            sanitize_text(todo.title),
            sanitize_text(todo.current_summary),
            sanitize_text(todo.summary_fields.group_name),
            sanitize_text(todo.summary_fields.environment),
            sanitize_text(todo.summary_fields.ticket_type),
            sanitize_text(todo.status) or TodoStatus.OPEN,
            sanitize_text(todo.created_at) or now_iso(),
            sanitize_text(todo.updated_at) or now_iso(),
        ),
    )
    connection.execute("DELETE FROM todo_timeline_events WHERE todo_id = ?", (sanitize_text(todo.id),))
    repository = SQLiteTodoRepository.__new__(SQLiteTodoRepository)
    for event in todo.timeline:
        SQLiteTodoRepository._insert_timeline_event(repository, connection, todo.id, event)
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
