import json
import sqlite3
from pathlib import Path

from aica.models import TicketSnapshot, TicketSummaryFields
from aica.storage.contracts import ProjectRecord
from aica.storage.sqlite.repositories import SQLiteProjectRepository
from aica.todo_events import TodoBindingStore
from aica.todo_store import TimelineAttachment, TodoConclusion, TodoStore


def _snapshot(
    title: str,
    summary: str,
    timeline: str,
    *,
    group_name: str = "group-a",
    environment: str = "prod",
    product_line: str = "",
    ticket_type: str = "incident",
    ach_no: str = "",
    ticket_version: str = "",
    feature_point: str = "",
    root_cause_desc: str = "",
    root_cause: str = "",
) -> TicketSnapshot:
    return TicketSnapshot(
        title=title,
        fields=TicketSummaryFields(
            group_name=group_name,
            environment=environment,
            product_line=product_line,
            ticket_type=ticket_type,
            ach_no=ach_no,
            ticket_version=ticket_version,
            feature_point=feature_point,
            root_cause_desc=root_cause_desc,
            root_cause=root_cause,
        ),
        current_summary=summary,
        timeline_entry=timeline,
    )


def test_todo_store_uses_project_snapshot_for_product_line(tmp_path: Path):
    repository = SQLiteProjectRepository(tmp_path / "aica.db")
    repository.upsert_projects(
        [
            ProjectRecord(
                id="project-1",
                project_name="Docs Platform",
                customer_name="Customer A",
                product_line="Docs",
                support_ended_at="2099-01-01T00:00:00",
                aliases=("Alpha Group",),
            )
        ]
    )

    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "summary", "timeline", group_name="  alpha   group "),
        "todo assistant",
    )

    assert todo.project_link.match_status == "matched"
    assert todo.project_link.project_id == "project-1"
    assert todo.project_link.project_snapshot["product_line"] == "Docs"
    assert todo.summary_fields.product_line == "Docs"


def test_todo_store_initializes_ticket_version_from_project_snapshot(tmp_path: Path):
    repository = SQLiteProjectRepository(tmp_path / "aica.db")
    repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Alpha Project",
            task_order_no="WO-1",
            product_version="v1.2.3",
            support_ended_at="2099-01-01T00:00:00",
            aliases=("Alpha Group",),
        )
    )

    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "summary", "timeline", group_name="Alpha Group"),
        "todo assistant",
    )

    assert todo.summary_fields.ticket_version == "v1.2.3"
    assert todo.project_link.project_snapshot["product_version"] == "v1.2.3"


def test_todo_store_persists_explicit_product_line_without_project_snapshot(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "summary", "timeline", product_line="AICA"),
        "todo assistant",
    )

    assert todo.summary_fields.product_line == "AICA"
    reloaded = store.get_todo(todo.id)
    assert reloaded is not None
    assert reloaded.summary_fields.product_line == "AICA"

    updated = store.update_todo(
        todo.id,
        summary_fields=TicketSummaryFields(
            group_name=todo.summary_fields.group_name,
            environment=todo.summary_fields.environment,
            product_line="AICA-Next",
            ticket_type=todo.summary_fields.ticket_type,
            ticket_version=todo.summary_fields.ticket_version,
        ),
    )
    assert updated is not None
    assert updated.summary_fields.product_line == "AICA-Next"

    reloaded_updated = store.get_todo(todo.id)
    assert reloaded_updated is not None
    assert reloaded_updated.summary_fields.product_line == "AICA-Next"


def test_todo_store_persists_enrichment_fields_and_conclusion(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot(
            "upload failed",
            "summary",
            "timeline",
            feature_point="导出模块",
            root_cause_desc="导出接口参数错误",
            root_cause="配置错误",
        ),
        "todo assistant",
    )

    updated = store.update_todo(
        todo.id,
        summary_fields=TicketSummaryFields(
            group_name=todo.summary_fields.group_name,
            environment=todo.summary_fields.environment,
            product_line=todo.summary_fields.product_line,
            ticket_type=todo.summary_fields.ticket_type,
            ticket_version=todo.summary_fields.ticket_version,
            feature_point="导出模块",
            feature_point_source="auto",
            root_cause_desc="导出接口参数错误",
            root_cause_desc_source="auto",
            root_cause="配置错误",
            root_cause_source="manual",
        ),
        conclusion=TodoConclusion(
            content="确认是生产配置缺失导致报错",
            updated_at="2026-04-13T12:00:00",
            attachments=[
                TimelineAttachment(
                    id="attachment-1",
                    name="evidence.png",
                    path=str(tmp_path / "evidence.png"),
                    size_bytes=128,
                )
            ],
        ),
    )

    assert updated is not None
    assert updated.summary_fields.feature_point == "导出模块"
    assert updated.summary_fields.feature_point_source == "auto"
    assert updated.summary_fields.root_cause_desc == "导出接口参数错误"
    assert updated.summary_fields.root_cause == "配置错误"
    assert updated.summary_fields.root_cause_source == "manual"
    assert updated.conclusion.content == "确认是生产配置缺失导致报错"
    assert updated.conclusion.updated_at == "2026-04-13T12:00:00"
    assert updated.conclusion.attachments[0].name == "evidence.png"


def test_legacy_json_data_migrates_to_sqlite_once(tmp_path: Path):
    todos_path = tmp_path / "todos.json"
    bindings_path = tmp_path / "todo_bindings.json"
    todos_path.write_text(
        json.dumps(
            [
                {
                    "id": "todo-1",
                    "title": "legacy todo",
                    "current_summary": "legacy summary",
                    "summary_fields": {
                        "group_name": "legacy-group",
                        "environment": "prod",
                        "product_line": "legacy-line",
                        "ticket_type": "incident",
                    },
                    "status": "open",
                    "timeline": [{"content": "legacy timeline"}],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    bindings_path.write_text(
        json.dumps(
            [
                {
                    "todo_id": "todo-1",
                    "integration_id": "company-platform",
                    "external_id": "EXT-001",
                    "last_sync_status": "ok:created",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    store = TodoStore(str(todos_path))
    binding_store = TodoBindingStore(str(bindings_path))

    todo = store.get_todo("todo-1")
    binding = binding_store.get_binding("todo-1", "company-platform")
    assert todo is not None
    assert binding is not None
    assert Path(store.path) == tmp_path / "aica.db"
    assert todo.current_summary == "legacy summary"
    assert binding.external_id == "EXT-001"

    store = TodoStore(str(todos_path))
    binding_store = TodoBindingStore(str(bindings_path))
    assert store.get_todo("todo-1") is not None
    assert binding_store.get_binding("todo-1", "company-platform") is not None

    with sqlite3.connect(tmp_path / "aica.db") as connection:
        todo_count = connection.execute("SELECT COUNT(*) FROM todos").fetchone()[0]
        binding_count = connection.execute("SELECT COUNT(*) FROM todo_bindings").fetchone()[0]

    assert todo_count == 1
    assert binding_count == 1


def test_ticket_version_migrates_from_project_snapshot_without_using_current_project(tmp_path: Path):
    db_path = tmp_path / "aica.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute(
            """
            CREATE TABLE todos (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              current_summary TEXT NOT NULL DEFAULT '',
              group_name TEXT NOT NULL DEFAULT '',
              environment TEXT NOT NULL DEFAULT '',
              ticket_type TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE todo_timeline_events (
              id TEXT PRIMARY KEY,
              todo_id TEXT NOT NULL,
              timestamp TEXT NOT NULL,
              kind TEXT NOT NULL DEFAULT 'analysis',
              scenario TEXT NOT NULL DEFAULT '',
              content TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE todo_timeline_attachments (
              id TEXT PRIMARY KEY,
              event_id TEXT NOT NULL,
              name TEXT NOT NULL,
              path TEXT NOT NULL,
              size_bytes INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL
            )
            """
        )
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
              updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE todo_bindings (
              todo_id TEXT NOT NULL,
              integration_id TEXT NOT NULL,
              external_id TEXT NOT NULL DEFAULT '',
              external_url TEXT NOT NULL DEFAULT '',
              last_event_id TEXT NOT NULL DEFAULT '',
              last_event_type TEXT NOT NULL DEFAULT '',
              last_sync_status TEXT NOT NULL DEFAULT '',
              metadata_json TEXT NOT NULL DEFAULT '{}',
              deleted_locally INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY(todo_id, integration_id)
            )
            """
        )
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
              product_version TEXT NOT NULL DEFAULT '',
              project_manager TEXT NOT NULL DEFAULT '',
              project_level TEXT NOT NULL DEFAULT 'normal',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO todos(
              id, title, current_summary, group_name, environment, ticket_type, status, created_at, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "todo-1",
                "legacy todo",
                "summary",
                "Alpha Group",
                "prod",
                "incident",
                "open",
                "2026-01-01T00:00:00",
                "2026-01-01T00:00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO todo_project_links(
              todo_id, project_id, match_status, match_reason, matched_group_name, matched_alias,
              project_snapshot_json, matched_at, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "todo-1",
                "project-1",
                "matched",
                "",
                "Alpha Group",
                "Alpha Group",
                json.dumps({"project_name": "Alpha Project", "product_version": "snapshot-v1"}, ensure_ascii=False),
                "2026-01-01T00:00:00",
                "2026-01-01T00:00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO projects(
              id, project_name, task_order_no, product_version, support_ended_at, created_at, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "project-1",
                "Alpha Project",
                "WO-1",
                "current-v9",
                "2099-01-01T00:00:00",
                "2026-01-01T00:00:00",
                "2026-01-02T00:00:00",
            ),
        )
        connection.execute("INSERT INTO schema_meta(key, value) VALUES('schema_version', '1')")

    store = TodoStore(str(db_path))
    todo = store.get_todo("todo-1")

    assert todo is not None
    assert todo.summary_fields.ticket_version == "snapshot-v1"


def test_project_repository_lists_gets_and_deletes_projects(tmp_path: Path):
    repository = SQLiteProjectRepository(tmp_path / "aica.db")
    repository.upsert_projects(
        [
            ProjectRecord(
                id="project-1",
                project_name="Alpha Project",
                task_order_no="WO-1",
                customer_name="Customer A",
                support_ended_at="2099-01-01T00:00:00",
                aliases=("Alpha Group",),
            ),
            ProjectRecord(
                id="project-2",
                project_name="Expired Project",
                task_order_no="WO-2",
                support_ended_at="2020-01-01T00:00:00",
                aliases=("Expired Group",),
            ),
        ]
    )

    active_only = repository.list_projects(include_expired=False, now="2026-04-11T10:00:00")
    queried = repository.list_projects(query="alpha", include_expired=True)
    selected = repository.get_project_by_task_order_no("WO-1")
    deleted = repository.delete_project("project-2")

    assert [item.id for item in active_only] == ["project-1"]
    assert [item.id for item in queried] == ["project-1"]
    assert selected is not None
    assert selected.aliases == ("Alpha Group",)
    assert deleted is True
    assert repository.get_project_by_task_order_no("WO-2") is None


def test_project_updates_do_not_overwrite_existing_ticket_version(tmp_path: Path):
    repository = SQLiteProjectRepository(tmp_path / "aica.db")
    repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Alpha Project",
            task_order_no="WO-1",
            product_version="v1",
            support_ended_at="2099-01-01T00:00:00",
            aliases=("Alpha Group",),
        )
    )
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("u", "s", "t", group_name="Alpha Group"),
        "todo assistant",
    )

    repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Alpha Project",
            task_order_no="WO-1",
            product_version="v2",
            support_ended_at="2099-01-01T00:00:00",
            aliases=("Alpha Group",),
        )
    )

    after = store.get_todo(todo.id)
    assert after is not None
    assert after.summary_fields.ticket_version == "v1"
    assert repository.get_project_by_task_order_no("WO-1").product_version == "v2"


def test_relink_only_backfills_empty_ticket_version_and_preserves_manual_value(tmp_path: Path):
    repository = SQLiteProjectRepository(tmp_path / "aica.db")
    store = TodoStore(str(tmp_path / "todos.json"))

    empty_version_todo = store.create_todo_from_analysis(
        _snapshot("u1", "s", "t", group_name="Alpha Group"),
        "todo assistant",
    )
    manual_version_todo = store.create_todo_from_analysis(
        _snapshot("u2", "s", "t", group_name="Other Group", ticket_version="manual-v1"),
        "todo assistant",
    )

    repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Alpha Project",
            task_order_no="WO-1",
            product_version="v2",
            support_ended_at="2099-01-01T00:00:00",
            aliases=("Alpha Group", "Manual Group"),
        )
    )

    assert store.relink_open_unresolved_todos() == 1
    filled = store.get_todo(empty_version_todo.id)
    assert filled is not None
    assert filled.summary_fields.ticket_version == "v2"

    updated_manual = store.update_todo(
        manual_version_todo.id,
        summary_fields=TicketSummaryFields(
            group_name="Manual Group",
            environment="prod",
            product_line="",
            ticket_type="incident",
            ticket_version="manual-v1",
        ),
    )

    assert updated_manual is not None
    assert updated_manual.project_link.match_status == "matched"
    assert updated_manual.summary_fields.ticket_version == "manual-v1"
    assert updated_manual.project_link.project_snapshot["product_version"] == "v2"


def test_relink_open_unresolved_todos_skips_done_and_matched_todos(tmp_path: Path):
    repository = SQLiteProjectRepository(tmp_path / "aica.db")
    repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Alpha Project",
            task_order_no="WO-1",
            support_ended_at="2099-01-01T00:00:00",
            aliases=("Alpha Group",),
        )
    )
    store = TodoStore(str(tmp_path / "todos.json"))
    unresolved = store.create_todo_from_analysis(_snapshot("u", "s", "t", group_name="Unmatched Group"), "todo assistant")
    matched = store.create_todo_from_analysis(_snapshot("m", "s", "t", group_name="Alpha Group"), "todo assistant")
    done = store.create_todo_from_analysis(_snapshot("d", "s", "t", group_name="Done Group"), "todo assistant")
    assert store.complete_todo(done.id) is True

    repository.upsert_project(
        ProjectRecord(
            id="project-2",
            project_name="Unmatched Project",
            task_order_no="WO-2",
            support_ended_at="2099-01-01T00:00:00",
            aliases=("Unmatched Group", "Done Group"),
        )
    )

    relinked_count = store.relink_open_unresolved_todos()
    unresolved_after = store.get_todo(unresolved.id)
    matched_after = store.get_todo(matched.id)
    done_after = store.get_todo(done.id)

    assert relinked_count == 1
    assert unresolved_after is not None
    assert unresolved_after.project_link.match_status == "matched"
    assert matched_after is not None
    assert matched_after.project_link.project_id == "project-1"
    assert done_after is not None
    assert done_after.project_link.match_status == "unmatched"


def test_todo_store_persists_ach_no(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "summary", "timeline", ach_no="ACH-INIT-001"),
        "todo assistant",
    )

    updated = store.update_todo(
        todo.id,
        summary_fields=TicketSummaryFields(
            group_name=todo.summary_fields.group_name,
            environment=todo.summary_fields.environment,
            product_line=todo.summary_fields.product_line,
            ticket_type=todo.summary_fields.ticket_type,
            ach_no="ACH-2026-001",
            ach_filled_at="2026-04-13T10:00:00",
            ticket_version=todo.summary_fields.ticket_version,
            feature_point=todo.summary_fields.feature_point,
            feature_point_source=todo.summary_fields.feature_point_source,
            root_cause_desc=todo.summary_fields.root_cause_desc,
            root_cause_desc_source=todo.summary_fields.root_cause_desc_source,
            root_cause=todo.summary_fields.root_cause,
            root_cause_source=todo.summary_fields.root_cause_source,
        ),
    )

    assert updated is not None
    assert updated.summary_fields.ach_no == "ACH-2026-001"
    assert updated.summary_fields.ach_filled_at == "2026-04-13T10:00:00"


def test_schema_migration_adds_ach_no_column(tmp_path: Path):
    db_path = tmp_path / "aica.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute(
            """
            CREATE TABLE todos (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              current_summary TEXT NOT NULL DEFAULT '',
              group_name TEXT NOT NULL DEFAULT '',
              environment TEXT NOT NULL DEFAULT '',
              ticket_type TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE todo_timeline_events (
              id TEXT PRIMARY KEY,
              todo_id TEXT NOT NULL,
              timestamp TEXT NOT NULL,
              kind TEXT NOT NULL DEFAULT 'analysis',
              scenario TEXT NOT NULL DEFAULT '',
              content TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE todo_timeline_attachments (
              id TEXT PRIMARY KEY,
              event_id TEXT NOT NULL,
              name TEXT NOT NULL,
              path TEXT NOT NULL,
              size_bytes INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL
            )
            """
        )
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
              updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE todo_bindings (
              todo_id TEXT NOT NULL,
              integration_id TEXT NOT NULL,
              external_id TEXT NOT NULL DEFAULT '',
              external_url TEXT NOT NULL DEFAULT '',
              last_event_id TEXT NOT NULL DEFAULT '',
              last_event_type TEXT NOT NULL DEFAULT '',
              last_sync_status TEXT NOT NULL DEFAULT '',
              metadata_json TEXT NOT NULL DEFAULT '{}',
              deleted_locally INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY(todo_id, integration_id)
            )
            """
        )
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
              product_version TEXT NOT NULL DEFAULT '',
              project_manager TEXT NOT NULL DEFAULT '',
              project_level TEXT NOT NULL DEFAULT 'normal',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute("INSERT INTO schema_meta(key, value) VALUES('schema_version', '1')")

    store = TodoStore(str(db_path))
    migrated_todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "summary", "timeline", ach_no="ACH-MIGRATE-001"),
        "todo assistant",
    )

    assert migrated_todo.summary_fields.ach_no == "ACH-MIGRATE-001"
    with sqlite3.connect(db_path) as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(todos)").fetchall()]
        stored_ach = connection.execute(
            "SELECT ach_no FROM todos WHERE id = ?",
            (migrated_todo.id,),
        ).fetchone()[0]

    assert "ach_no" in columns
    assert stored_ach == "ACH-MIGRATE-001"


def test_list_todos_search_matches_ach_no(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "summary", "timeline", ach_no="ACH-SEARCH-007"),
        "todo assistant",
    )

    matched = store.list_todos(query="search-007", status="all")

    assert [item.id for item in matched] == [todo.id]
