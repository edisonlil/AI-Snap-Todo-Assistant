from __future__ import annotations

from datetime import datetime, timedelta
import os
import sqlite3
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.models import TicketSnapshot, TicketSummaryFields
from aica.storage.contracts import ProjectRecord
from aica.storage.sqlite.repositories import SCHEMA_VERSION, SQLiteProjectRepository, SQLiteStorageMigrator, SQLiteTodoRepository
from aica.todo.models import TodoStatus


def _make_db_path(name: str) -> Path:
    fd, raw_path = tempfile.mkstemp(prefix=f"{name}-", suffix=".db", dir=Path.cwd())
    os.close(fd)
    path = Path(raw_path)
    path.unlink(missing_ok=True)
    return path


def _build_snapshot(title: str) -> TicketSnapshot:
    return TicketSnapshot(
        title=title,
        fields=TicketSummaryFields(
            group_name="test-group",
            environment="prod",
            ticket_type="investigation",
        ),
        current_summary=f"{title} summary",
        timeline_entry=f"{title} timeline",
    )


def test_todo_completed_at_defaults_to_empty() -> None:
    repository = SQLiteTodoRepository(str(_make_db_path("todo-default")))

    todo = repository.create_todo_from_analysis(_build_snapshot("todo-one"), "analysis")

    assert todo.status == TodoStatus.OPEN
    assert todo.completed_at == ""


def test_complete_todo_sets_completed_at() -> None:
    repository = SQLiteTodoRepository(str(_make_db_path("todo-complete")))
    todo = repository.create_todo_from_analysis(_build_snapshot("todo-two"), "analysis")

    assert repository.complete_todo(todo.id) is True

    updated = repository.get_todo(todo.id)
    assert updated is not None
    assert updated.status == TodoStatus.DONE
    assert updated.completed_at
    assert updated.updated_at == updated.completed_at


def test_reopen_todo_clears_completed_at() -> None:
    repository = SQLiteTodoRepository(str(_make_db_path("todo-reopen")))
    todo = repository.create_todo_from_analysis(_build_snapshot("todo-reopen"), "analysis")
    old_completed_at = "2026-04-20T10:00:00"

    with sqlite3.connect(repository.path) as connection:
        connection.execute(
            "UPDATE todos SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?",
            (TodoStatus.DONE, old_completed_at, old_completed_at, todo.id),
        )

    assert repository.reopen_todo(todo.id) is True

    updated = repository.get_todo(todo.id)
    assert updated is not None
    assert updated.status == TodoStatus.OPEN
    assert updated.completed_at == ""
    assert updated.updated_at
    assert updated.updated_at != old_completed_at


def test_today_done_uses_completed_at_instead_of_updated_at() -> None:
    repository = SQLiteTodoRepository(str(_make_db_path("todo-filter")))
    today_todo = repository.create_todo_from_analysis(_build_snapshot("done-today"), "analysis")
    stale_todo = repository.create_todo_from_analysis(_build_snapshot("done-earlier"), "analysis")

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    old_day = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    with sqlite3.connect(repository.path) as connection:
        connection.execute(
            "UPDATE todos SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?",
            (TodoStatus.DONE, f"{today}T10:00:00", f"{old_day}T09:00:00", today_todo.id),
        )
        connection.execute(
            "UPDATE todos SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?",
            (TodoStatus.DONE, f"{old_day}T10:00:00", f"{today}T09:00:00", stale_todo.id),
        )

    today_done = repository.list_todos(status="today_done")

    assert [todo.id for todo in today_done] == [today_todo.id]


def test_unlink_todo_project_removes_link_and_clears_project_fields() -> None:
    db_path = _make_db_path("todo-unlink-project")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="WPS协作",
            product_version="release_dc_v7",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    repository = SQLiteTodoRepository(str(db_path))
    todo = repository.create_todo_from_analysis(_build_snapshot("todo-linked"), "analysis")

    linked = repository.get_todo(todo.id)
    assert linked is not None
    assert linked.project_link.match_status == "matched"
    assert linked.project_link.project_snapshot["project_name"] == "Demo Project"
    assert linked.summary_fields.product_line == "WPS协作"
    assert linked.summary_fields.ticket_version == "release_dc_v7"

    updated = repository.unlink_todo_project(todo.id)

    assert updated is not None
    assert updated.project_link.match_status == ""
    assert updated.project_link.project_snapshot == {}
    assert updated.summary_fields.product_line == "未知"
    assert updated.summary_fields.ticket_version == ""
    with sqlite3.connect(repository.path) as connection:
        link_rows = connection.execute(
            "SELECT todo_id FROM todo_project_links WHERE todo_id = ?",
            (todo.id,),
        ).fetchall()
        todo_row = connection.execute(
            "SELECT product_line, ticket_version FROM todos WHERE id = ?",
            (todo.id,),
        ).fetchone()

    assert link_rows == []
    assert todo_row == ("", "")


def test_project_repair_preserves_selected_product_line_option() -> None:
    db_path = _make_db_path("todo-product-option")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="WPS协作, 文档中台",
            product_version="release_dc_v7",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    repository = SQLiteTodoRepository(str(db_path))
    snapshot = _build_snapshot("todo-product-option")
    snapshot.fields.product_line = "文档中台"
    todo = repository.create_todo_from_analysis(snapshot, "analysis")

    linked = repository.get_todo(todo.id)

    assert linked is not None
    assert linked.project_link.match_status == "matched"
    assert linked.summary_fields.product_line == "文档中台"


def test_schema_migration_adds_completed_at_column() -> None:
    db_path = _make_db_path("legacy-todo")
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute(
            """
            CREATE TABLE todos (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              current_summary TEXT NOT NULL DEFAULT '',
              group_name TEXT NOT NULL DEFAULT '',
              environment TEXT NOT NULL DEFAULT '',
              product_line TEXT NOT NULL DEFAULT '',
              ticket_type TEXT NOT NULL DEFAULT '',
              ach_no TEXT NOT NULL DEFAULT '',
              ach_filled_at TEXT NOT NULL DEFAULT '',
              ticket_version TEXT NOT NULL DEFAULT '',
              feature_point TEXT NOT NULL DEFAULT '',
              feature_point_source TEXT NOT NULL DEFAULT '',
              root_cause_desc TEXT NOT NULL DEFAULT '',
              root_cause_desc_source TEXT NOT NULL DEFAULT '',
              root_cause TEXT NOT NULL DEFAULT '',
              root_cause_source TEXT NOT NULL DEFAULT '',
              conclusion_content TEXT NOT NULL DEFAULT '',
              conclusion_updated_at TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )

    SQLiteStorageMigrator(db_path).ensure_schema()

    with sqlite3.connect(db_path) as connection:
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(todos)").fetchall()
        }

    assert "completed_at" in columns


def test_schema_migration_creates_error_codes_table_and_updates_version() -> None:
    db_path = _make_db_path("error-codes-schema")

    SQLiteStorageMigrator(db_path).ensure_schema()

    with sqlite3.connect(db_path) as connection:
        tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        indexes = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        }
        version = connection.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        ).fetchone()[0]

    assert SCHEMA_VERSION == "15"
    assert version == "15"
    assert "error_codes" in tables
    assert "idx_error_codes_category" in indexes
    assert "idx_error_codes_last_seen" in indexes
