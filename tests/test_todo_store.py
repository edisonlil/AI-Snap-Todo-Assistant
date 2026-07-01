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
from aica.storage.sqlite.repositories import (
    SCHEMA_VERSION,
    SQLiteProjectRepository,
    SQLiteStorageMigrator,
    SQLiteTodoRepository,
    _INITIALIZED_DATABASES,
)
from aica.todo.models import TimelineAttachment, TodoProjectLink, TodoStatus


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
            customer_environment_code="env-prod",
            customer_environment_value="生产环境",
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
    assert linked.summary_fields.product_line == "未知"
    assert linked.summary_fields.ticket_version == ""
    assert linked.summary_fields.customer_environment_code == "env-prod"
    assert linked.summary_fields.customer_environment_value == "生产环境"

    updated = repository.unlink_todo_project(todo.id)

    assert updated is not None
    assert updated.project_link.match_status == ""
    assert updated.project_link.project_snapshot == {}
    assert updated.summary_fields.product_line == "未知"
    assert updated.summary_fields.ticket_version == ""
    assert updated.summary_fields.customer_environment_code == "env-prod"
    assert updated.summary_fields.customer_environment_value == "生产环境"
    with sqlite3.connect(repository.path) as connection:
        link_rows = connection.execute(
            "SELECT todo_id FROM todo_project_links WHERE todo_id = ?",
            (todo.id,),
        ).fetchall()
        todo_row = connection.execute(
            "SELECT product_line, product_module, ticket_version, customer_environment_code, customer_environment_value FROM todos WHERE id = ?",
            (todo.id,),
        ).fetchone()

    assert link_rows == []
    assert todo_row == ("", "", "", "env-prod", "生产环境")


def test_linked_todo_keeps_snapshot_selected_product_line_option() -> None:
    db_path = _make_db_path("todo-product-option")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="WPS协作, 文档中台",
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


def test_linked_todo_keeps_manual_product_line_outside_project_snapshot() -> None:
    db_path = _make_db_path("todo-product-manual-override")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="文档中台",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    repository = SQLiteTodoRepository(str(db_path))
    snapshot = _build_snapshot("todo-product-manual-override")
    snapshot.fields.product_line = "私网文档中台"
    snapshot.fields.product_module = "文档中台"
    todo = repository.create_todo_from_analysis(snapshot, "analysis")

    linked = repository.get_todo(todo.id)

    assert linked is not None
    assert linked.project_link.match_status == "matched"
    assert linked.summary_fields.product_line == "私网文档中台"
    assert linked.summary_fields.product_module == "文档中台"


def test_project_link_inherits_latest_customer_environment_when_current_is_empty() -> None:
    db_path = _make_db_path("todo-customer-environment-inherit")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="WPS协作",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    repository = SQLiteTodoRepository(str(db_path))

    first = repository.create_todo_from_analysis(_build_snapshot("todo-first"), "analysis")
    assert first.summary_fields.customer_environment_code == "env-prod"
    assert first.summary_fields.customer_environment_value == "生产环境"

    second_snapshot = _build_snapshot("todo-second")
    second_snapshot.fields.customer_environment_code = ""
    second_snapshot.fields.customer_environment_value = ""
    second = repository.create_todo_from_analysis(second_snapshot, "analysis")

    assert second.summary_fields.customer_environment_code == "env-prod"
    assert second.summary_fields.customer_environment_value == "生产环境"


def test_create_todo_inherits_latest_project_fields_when_current_values_are_default_empty() -> None:
    db_path = _make_db_path("todo-project-latest-defaults")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="WPS协作",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    repository = SQLiteTodoRepository(str(db_path))

    first_snapshot = _build_snapshot("todo-first-with-history")
    first_snapshot.fields.environment = "生产"
    first_snapshot.fields.product_line = "PC Office"
    first_snapshot.fields.product_module = "PC Office-文字"
    first_snapshot.fields.customer_environment_code = "env-prod"
    first_snapshot.fields.customer_environment_value = "生产环境"
    first_snapshot.fields.issue_product = "产品A/模块B/功能C"
    first = repository.create_todo_from_analysis(first_snapshot, "analysis")

    second_snapshot = _build_snapshot("todo-second-inherit")
    second_snapshot.fields.environment = ""
    second_snapshot.fields.product_line = ""
    second_snapshot.fields.product_module = ""
    second_snapshot.fields.customer_environment_code = ""
    second_snapshot.fields.customer_environment_value = ""
    second_snapshot.fields.issue_product = ""
    second = repository.create_todo_from_analysis(second_snapshot, "analysis")

    assert first.project_link.project_id == "project-1"
    assert second.project_link.project_id == "project-1"
    assert second.summary_fields.environment == "生产"
    assert second.summary_fields.product_line == "PC Office"
    assert second.summary_fields.product_module == "PC Office-文字"
    assert second.summary_fields.customer_environment_code == "env-prod"
    assert second.summary_fields.customer_environment_value == "生产环境"
    assert second.summary_fields.issue_product == "产品A/模块B/功能C"


def test_create_todo_keeps_fields_empty_without_previous_project_todo() -> None:
    db_path = _make_db_path("todo-project-no-history-defaults")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="WPS协作",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    repository = SQLiteTodoRepository(str(db_path))

    snapshot = _build_snapshot("todo-first-no-history")
    snapshot.fields.environment = ""
    snapshot.fields.product_line = ""
    snapshot.fields.product_module = ""
    snapshot.fields.customer_environment_code = ""
    snapshot.fields.customer_environment_value = ""
    snapshot.fields.issue_product = ""
    todo = repository.create_todo_from_analysis(snapshot, "analysis")

    assert todo.project_link.project_id == "project-1"
    assert todo.summary_fields.environment == "未知"
    assert todo.summary_fields.product_line == "未知"
    assert todo.summary_fields.product_module == ""
    assert todo.summary_fields.customer_environment_code == ""
    assert todo.summary_fields.customer_environment_value == ""
    assert todo.summary_fields.issue_product == ""


def test_project_relink_inherits_latest_project_fields_only_for_default_empty_values() -> None:
    db_path = _make_db_path("todo-project-relink-defaults")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="WPS协作",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    repository = SQLiteTodoRepository(str(db_path))

    first_snapshot = _build_snapshot("todo-history")
    first_snapshot.fields.environment = "生产"
    first_snapshot.fields.product_line = "PC Office"
    first_snapshot.fields.product_module = "PC Office-文字"
    first_snapshot.fields.customer_environment_code = "env-prod"
    first_snapshot.fields.customer_environment_value = "生产环境"
    first_snapshot.fields.issue_product = "产品A/模块B/功能C"
    repository.create_todo_from_analysis(first_snapshot, "analysis")

    second_snapshot = _build_snapshot("todo-relink")
    second_snapshot.fields.group_name = "unmatched-group"
    second_snapshot.fields.environment = ""
    second_snapshot.fields.product_line = ""
    second_snapshot.fields.product_module = ""
    second_snapshot.fields.customer_environment_code = ""
    second_snapshot.fields.customer_environment_value = ""
    second_snapshot.fields.issue_product = ""
    second = repository.create_todo_from_analysis(second_snapshot, "analysis")
    assert second.project_link.project_id == ""

    updated = repository.update_todo(
        second.id,
        summary_fields=TicketSummaryFields(
            group_name="test-group",
            environment="",
            product_line="",
            product_module="",
            ticket_type=second.summary_fields.ticket_type,
            customer_environment_code="",
            customer_environment_value="",
            issue_product="",
        ),
    )

    assert updated is not None
    assert updated.project_link.project_id == "project-1"
    assert updated.summary_fields.environment == "生产"
    assert updated.summary_fields.product_line == "PC Office"
    assert updated.summary_fields.product_module == "PC Office-文字"
    assert updated.summary_fields.customer_environment_code == "env-prod"
    assert updated.summary_fields.customer_environment_value == "生产环境"
    assert updated.summary_fields.issue_product == "产品A/模块B/功能C"


def test_create_todo_does_not_override_existing_project_fields_with_latest_history() -> None:
    db_path = _make_db_path("todo-project-existing-values")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="WPS协作",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    repository = SQLiteTodoRepository(str(db_path))

    first_snapshot = _build_snapshot("todo-history")
    first_snapshot.fields.environment = "生产"
    first_snapshot.fields.product_line = "PC Office"
    first_snapshot.fields.product_module = "PC Office-文字"
    first_snapshot.fields.customer_environment_code = "env-prod"
    first_snapshot.fields.customer_environment_value = "生产环境"
    first_snapshot.fields.issue_product = "产品A/模块B/功能C"
    repository.create_todo_from_analysis(first_snapshot, "analysis")

    second_snapshot = _build_snapshot("todo-current-values")
    second_snapshot.fields.environment = "预发"
    second_snapshot.fields.product_line = "WPS会议"
    second_snapshot.fields.product_module = "会议室"
    second_snapshot.fields.customer_environment_code = "env-uat"
    second_snapshot.fields.customer_environment_value = "预发环境"
    second_snapshot.fields.issue_product = "产品X/模块Y/功能Z"
    second = repository.create_todo_from_analysis(second_snapshot, "analysis")

    assert second.summary_fields.environment == "预发"
    assert second.summary_fields.product_line == "WPS会议"
    assert second.summary_fields.product_module == "会议室"
    assert second.summary_fields.customer_environment_code == "env-uat"
    assert second.summary_fields.customer_environment_value == "预发环境"
    assert second.summary_fields.issue_product == "产品X/模块Y/功能Z"


def test_create_todo_does_not_inherit_defaults_from_expired_project_history() -> None:
    db_path = _make_db_path("todo-project-expired-history-defaults")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Expired Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="WPS协作",
            project_manager="Alice",
            support_ended_at="2024-01-01T00:00:00",
            aliases=("test-group",),
        )
    )
    repository = SQLiteTodoRepository(str(db_path))

    history_snapshot = _build_snapshot("todo-expired-history")
    history_snapshot.fields.environment = "生产"
    history_snapshot.fields.product_line = "PC Office"
    history_snapshot.fields.product_module = "PC Office-文字"
    history_snapshot.fields.customer_environment_code = "env-prod"
    history_snapshot.fields.customer_environment_value = "生产环境"
    history_snapshot.fields.issue_product = "产品A/模块B/功能C"
    history_todo = repository.create_todo_from_analysis(history_snapshot, "analysis")

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            UPDATE todo_project_links
            SET project_id = NULL, match_status = 'expired', match_reason = 'matched_project_expired'
            WHERE todo_id = ?
            """,
            (history_todo.id,),
        )
        connection.commit()

    next_snapshot = _build_snapshot("todo-next")
    next_snapshot.fields.environment = ""
    next_snapshot.fields.product_line = ""
    next_snapshot.fields.product_module = ""
    next_snapshot.fields.customer_environment_code = ""
    next_snapshot.fields.customer_environment_value = ""
    next_snapshot.fields.issue_product = ""
    next_todo = repository.create_todo_from_analysis(next_snapshot, "analysis")

    assert next_todo.project_link.project_id == ""
    assert next_todo.summary_fields.environment == "未知"
    assert next_todo.summary_fields.product_line == "未知"
    assert next_todo.summary_fields.product_module == ""
    assert next_todo.summary_fields.customer_environment_code == ""
    assert next_todo.summary_fields.customer_environment_value == ""
    assert next_todo.summary_fields.issue_product == ""


def test_update_todo_ticket_version_upserts_project_version_record() -> None:
    db_path = _make_db_path("todo-project-version-upsert")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="PC Office",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    repository = SQLiteTodoRepository(str(db_path))
    todo = repository.create_todo_from_analysis(_build_snapshot("todo-version-upsert"), "analysis")

    updated = repository.update_todo(
        todo.id,
        summary_fields=TicketSummaryFields.from_dict(
            {
                **todo.summary_fields.to_dict(),
                "issue_product": "产品A/模块B/功能C",
                "environment": "prod",
                "ticket_version": "release_2026_07",
            }
        ),
    )

    assert updated is not None
    version_record = project_repository.get_project_version("project-1", "产品A/模块B/功能C", "prod")
    assert version_record is not None
    assert version_record.version == "release_2026_07"


def test_update_todo_environment_backfills_ticket_version_from_project_version() -> None:
    db_path = _make_db_path("todo-project-version-backfill-environment")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="PC Office",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    project_repository.upsert_project_version("project-1", "产品A/模块B/功能C", "prod", "release_2026_07")
    repository = SQLiteTodoRepository(str(db_path))
    todo = repository.create_todo_from_analysis(_build_snapshot("todo-version-backfill-environment"), "analysis")

    updated = repository.update_todo(
        todo.id,
        summary_fields=TicketSummaryFields.from_dict(
            {
                **todo.summary_fields.to_dict(),
                "issue_product": "产品A/模块B/功能C",
                "environment": "prod",
                "ticket_version": "",
            }
        ),
    )

    assert updated is not None
    assert updated.summary_fields.ticket_version == "release_2026_07"


def test_update_todo_issue_product_backfills_ticket_version_from_project_version() -> None:
    db_path = _make_db_path("todo-project-version-backfill-issue-product")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="PC Office",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    project_repository.upsert_project_version("project-1", "产品X/模块Y/功能Z", "prod", "release_2026_08")
    repository = SQLiteTodoRepository(str(db_path))
    todo = repository.create_todo_from_analysis(_build_snapshot("todo-version-backfill-issue-product"), "analysis")

    updated = repository.update_todo(
        todo.id,
        summary_fields=TicketSummaryFields.from_dict(
            {
                **todo.summary_fields.to_dict(),
                "issue_product": "产品X/模块Y/功能Z",
                "environment": "prod",
                "ticket_version": "",
            }
        ),
    )

    assert updated is not None
    assert updated.summary_fields.ticket_version == "release_2026_08"


def test_create_todo_inherits_environment_from_latest_non_unknown_project_history() -> None:
    db_path = _make_db_path("todo-project-latest-non-unknown-environment")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="WPS协作",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    repository = SQLiteTodoRepository(str(db_path))

    first_snapshot = _build_snapshot("todo-history-env")
    first_snapshot.fields.environment = "正式环境"
    first_snapshot.fields.issue_product = "产品A/模块B/功能C"
    repository.create_todo_from_analysis(first_snapshot, "analysis")

    second_snapshot = _build_snapshot("todo-history-unknown")
    second_snapshot.fields.environment = ""
    second_snapshot.fields.issue_product = ""
    repository.create_todo_from_analysis(second_snapshot, "analysis")

    third_snapshot = _build_snapshot("todo-current")
    third_snapshot.fields.environment = ""
    third_snapshot.fields.issue_product = ""
    third = repository.create_todo_from_analysis(third_snapshot, "analysis")

    assert third.summary_fields.environment == "正式环境"
    assert third.summary_fields.issue_product == "产品A/模块B/功能C"


def test_get_todo_repairs_environment_from_latest_updated_project_history() -> None:
    db_path = _make_db_path("todo-project-get-repairs-environment")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="WPS协作",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    repository = SQLiteTodoRepository(str(db_path))

    first_snapshot = _build_snapshot("todo-real-latest")
    first_snapshot.fields.environment = "正式环境"
    first = repository.create_todo_from_analysis(first_snapshot, "analysis")

    second_snapshot = _build_snapshot("todo-created-later")
    second_snapshot.fields.environment = ""
    second = repository.create_todo_from_analysis(second_snapshot, "analysis")

    current_snapshot = _build_snapshot("todo-current-empty")
    current_snapshot.fields.environment = ""
    current = repository.create_todo_from_analysis(current_snapshot, "analysis")

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE todos SET updated_at = ? WHERE id = ?",
            ("2026-07-01T11:50:09.967894", first.id),
        )
        connection.execute(
            "UPDATE todos SET updated_at = ? WHERE id = ?",
            ("2026-06-29T17:03:21.911987", second.id),
        )
        connection.execute(
            "UPDATE todos SET environment = ?, updated_at = ? WHERE id = ?",
            ("", "2026-07-01T15:34:39.793219", current.id),
        )

    repaired = repository.get_todo(current.id)

    assert repaired is not None
    assert repaired.summary_fields.environment == "正式环境"


def test_update_todo_repairs_matched_link_without_project_id_before_upserting_project_version() -> None:
    db_path = _make_db_path("todo-project-version-repair")
    project_repository = SQLiteProjectRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="PC Office",
            project_manager="Alice",
            aliases=("test-group",),
        )
    )
    repository = SQLiteTodoRepository(str(db_path))
    todo = repository.create_todo_from_analysis(_build_snapshot("todo-version-repair"), "analysis")

    broken_link = TodoProjectLink(
        todo_id=todo.id,
        project_id="",
        match_status="matched",
        matched_group_name="test-group",
        matched_alias="test-group",
        project_snapshot=project_repository.get_project_by_id("project-1").to_snapshot(),  # type: ignore[union-attr]
    )
    imported = repository.upsert_imported_todo(
        todo.__class__(
            id=todo.id,
            title=todo.title,
            summary_fields=todo.summary_fields,
            current_summary=todo.current_summary,
            current_summary_attachments=todo.current_summary_attachments,
            created_at=todo.created_at,
            updated_at=todo.updated_at,
            completed_at=todo.completed_at,
            status=todo.status,
            timeline=todo.timeline,
            conclusion=todo.conclusion,
            project_link=broken_link,
        )
    )
    assert imported is not None
    assert imported.project_link.project_id == "project-1"

    updated = repository.update_todo(
        todo.id,
        summary_fields=TicketSummaryFields.from_dict(
            {
                **todo.summary_fields.to_dict(),
                "issue_product": "产品A/模块B/功能C",
                "environment": "prod",
                "ticket_version": "release_2026_07",
            }
        ),
    )

    assert updated is not None
    assert updated.project_link.project_id == "project-1"
    version_record = project_repository.get_project_version("project-1", "产品A/模块B/功能C", "prod")
    assert version_record is not None
    assert version_record.version == "release_2026_07"


def test_create_todo_from_problem_conclusion_saves_into_conclusion() -> None:
    repository = SQLiteTodoRepository(str(_make_db_path("todo-problem-conclusion-create")))

    todo = repository.create_todo_from_analysis(_build_snapshot("问题结论待办"), "问题结论")

    assert todo.conclusion.content == "问题结论待办 timeline"
    assert todo.conclusion.updated_at
    assert len(todo.timeline) == 1
    assert todo.timeline[0].kind == "conclusion"
    assert todo.timeline[0].scenario == "结论更新"
    assert todo.timeline[0].content == "问题结论待办 timeline"


def test_append_problem_conclusion_updates_conclusion_instead_of_follow_up() -> None:
    repository = SQLiteTodoRepository(str(_make_db_path("todo-problem-conclusion-append")))
    todo = repository.create_todo_from_analysis(_build_snapshot("原始待办"), "工单跟进")
    original_timeline_count = len(todo.timeline)

    updated = repository.append_analysis_to_todo(
        todo.id,
        _build_snapshot("新的问题结论"),
        "问题结论",
    )

    assert updated is not None
    assert updated.conclusion.content == "新的问题结论 timeline"
    assert updated.conclusion.updated_at
    assert len(updated.timeline) == original_timeline_count + 1
    assert updated.timeline[-1].kind == "conclusion"
    assert updated.timeline[-1].scenario == "结论更新"
    assert updated.timeline[-1].content == "新的问题结论 timeline"
    assert updated.timeline[0].scenario == "工单跟进"


def test_update_todo_persists_current_summary_attachments() -> None:
    repository = SQLiteTodoRepository(str(_make_db_path("todo-summary-attachments")))
    todo = repository.create_todo_from_analysis(_build_snapshot("带描述附件"), "analysis")

    updated = repository.update_todo(
        todo.id,
        current_summary_attachments=[
            TimelineAttachment(
                id="summary-att-1",
                name="screen.png",
                path="/tmp/screen.png",
                size_bytes=128,
                file_object_id="file-123",
            )
        ],
    )

    assert updated is not None
    assert len(updated.current_summary_attachments) == 1
    assert updated.current_summary_attachments[0].name == "screen.png"
    reloaded = repository.get_todo(todo.id)
    assert reloaded is not None
    assert len(reloaded.current_summary_attachments) == 1
    assert reloaded.current_summary_attachments[0].file_object_id == "file-123"


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
    assert "customer_environment_code" in columns
    assert "customer_environment_value" in columns
    assert "product_module" in columns


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

    assert SCHEMA_VERSION == "18"
    assert version == "18"
    assert "error_codes" in tables
    assert "idx_error_codes_category" in indexes
    assert "idx_error_codes_last_seen" in indexes


def test_schema_migration_repairs_project_related_foreign_keys_after_projects_rebuild() -> None:
    db_path = _make_db_path("todo-project-fk-repair")
    migrator = SQLiteStorageMigrator(str(db_path))
    migrator.ensure_schema()

    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = OFF;
            ALTER TABLE projects RENAME TO projects_old;
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
            );
            INSERT INTO projects(
              id, project_name, customer_name, task_order_no,
              follow_up_started_at, support_ended_at, product_line,
              product_version, project_manager, project_level, created_at, updated_at
            ) VALUES(
              'project-1', 'Demo Project', 'Demo Customer', 'WO-001',
              '', '', 'PC Office', 'legacy_version', 'Alice', 'normal', '2026-07-01T00:00:00', '2026-07-01T00:00:00'
            );
            ALTER TABLE project_group_aliases RENAME TO project_group_aliases_old;
            CREATE TABLE project_group_aliases (
              id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL,
              alias_name TEXT NOT NULL,
              alias_name_normalized TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(project_id) REFERENCES "projects_old"(id) ON DELETE CASCADE
            );
            INSERT INTO project_group_aliases VALUES(
              'alias-1', 'project-1', 'test-group', 'test-group', '2026-07-01T00:00:00', '2026-07-01T00:00:00'
            );
            DROP TABLE project_group_aliases_old;
            ALTER TABLE todo_project_links RENAME TO todo_project_links_old;
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
              FOREIGN KEY(project_id) REFERENCES "projects_old"(id) ON DELETE SET NULL
            );
            DROP TABLE todo_project_links_old;
            ALTER TABLE project_versions RENAME TO project_versions_old;
            CREATE TABLE project_versions (
              id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL,
              issue_product TEXT NOT NULL DEFAULT '',
              environment TEXT NOT NULL DEFAULT '',
              version TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(project_id) REFERENCES "projects_old"(id) ON DELETE CASCADE
            );
            DROP TABLE project_versions_old;
            ALTER TABLE project_environments RENAME TO project_environments_old;
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
              FOREIGN KEY(project_id) REFERENCES "projects_old"(id) ON DELETE CASCADE
            );
            DROP TABLE project_environments_old;
            PRAGMA foreign_keys = ON;
            """
        )

    repair_migrator = SQLiteStorageMigrator(str(db_path))
    _INITIALIZED_DATABASES.discard(repair_migrator._cache_key())  # noqa: SLF001
    repair_migrator.ensure_schema()

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        group_fk = connection.execute("PRAGMA foreign_key_list(project_group_aliases)").fetchall()
        link_fk = connection.execute("PRAGMA foreign_key_list(todo_project_links)").fetchall()
        versions_fk = connection.execute("PRAGMA foreign_key_list(project_versions)").fetchall()
        environments_fk = connection.execute("PRAGMA foreign_key_list(project_environments)").fetchall()

    assert {row["table"] for row in group_fk} == {"projects"}
    assert {row["table"] for row in link_fk} == {"todos", "projects"}
    assert {row["table"] for row in versions_fk} == {"projects"}
    assert {row["table"] for row in environments_fk} == {"projects"}
