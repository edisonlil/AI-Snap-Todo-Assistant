from __future__ import annotations

import pytest

from aica.models import TicketSnapshot, TicketSummaryFields
from aica.project_management import (
    build_project_template_content,
    import_projects_from_file,
    project_record_from_payload,
    split_project_aliases,
)
from aica.storage.contracts import ProjectRecord
from aica.storage.sqlite.repositories import SQLiteProjectRepository
from aica.todo_store import TodoStore


def _snapshot(group_name: str) -> TicketSnapshot:
    return TicketSnapshot(
        title="demo",
        fields=TicketSummaryFields(
            group_name=group_name,
            environment="prod",
            product_line="",
            ticket_type="排查类",
        ),
        current_summary="summary",
        timeline_entry="timeline",
    )


def test_split_project_aliases_normalizes_and_deduplicates() -> None:
    aliases = split_project_aliases(" Alpha Group ;alpha   group\n客户群A，客户群A ")

    assert aliases == ("Alpha Group", "客户群A")


def test_project_record_from_payload_requires_business_key() -> None:
    with pytest.raises(ValueError):
        project_record_from_payload({"projectName": "示例项目"})


def test_import_projects_from_csv_upserts_by_task_order_no_and_relinks(tmp_path) -> None:
    repository = SQLiteProjectRepository(tmp_path / "aica.db")
    repository.upsert_project(
        ProjectRecord(
            id="existing-project",
            project_name="旧项目",
            task_order_no="WO-1",
            customer_name="旧客户",
            support_ended_at="2099-01-01T00:00:00",
            aliases=("Old Group",),
        )
    )

    store = TodoStore(str(tmp_path / "todos.json"))
    store.create_todo_from_analysis(_snapshot("New Group"), "todo assistant")
    csv_path = tmp_path / "projects.csv"
    csv_path.write_text(
        (
            "task_order_no,project_name,customer_name,product_line,product_version,"
            "project_manager,follow_up_started_at,support_ended_at,project_level,group_aliases\n"
            "WO-1,新项目名称,新客户,客服中台,v3,张三,2026-01-01T09:00:00,2099-01-01T00:00:00,normal,New Group\n"
        ),
        encoding="utf-8-sig",
    )

    result = import_projects_from_file(csv_path, repository, store)
    saved = repository.get_project_by_task_order_no("WO-1")
    todos = store.list_active_todos()

    assert result.created_count == 0
    assert result.updated_count == 1
    assert result.relinked_count == 1
    assert saved is not None
    assert saved.id == "existing-project"
    assert saved.project_name == "新项目名称"
    assert saved.aliases == ("New Group",)
    assert todos[0].project_link.match_status == "matched"
    assert todos[0].project_link.project_snapshot["task_order_no"] == "WO-1"


def test_import_projects_from_csv_reports_alias_conflicts_without_dirty_write(tmp_path) -> None:
    repository = SQLiteProjectRepository(tmp_path / "aica.db")
    repository.upsert_project(
        ProjectRecord(
            id="project-a",
            project_name="项目A",
            task_order_no="WO-A",
            support_ended_at="2099-01-01T00:00:00",
            aliases=("Shared Group",),
        )
    )
    store = TodoStore(str(tmp_path / "todos.json"))
    csv_path = tmp_path / "projects.csv"
    csv_path.write_text(
        (
            "task_order_no,project_name,support_ended_at,group_aliases\n"
            "WO-B,项目B,2099-01-01T00:00:00,Shared Group\n"
        ),
        encoding="utf-8-sig",
    )

    result = import_projects_from_file(csv_path, repository, store)

    assert result.created_count == 0
    assert len(result.alias_conflicts) == 1
    assert repository.get_project_by_task_order_no("WO-B") is None


def test_import_projects_from_xlsx_is_supported_when_openpyxl_available(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    repository = SQLiteProjectRepository(tmp_path / "aica.db")
    store = TodoStore(str(tmp_path / "todos.json"))
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "task_order_no",
            "project_name",
            "customer_name",
            "product_line",
            "product_version",
            "project_manager",
            "follow_up_started_at",
            "support_ended_at",
            "project_level",
            "group_aliases",
        ]
    )
    sheet.append(
        ["WO-XLSX", "Excel项目", "客户A", "客服中台", "v1", "李四", "", "2099-01-01T00:00:00", "normal", "Excel Group"]
    )
    xlsx_path = tmp_path / "projects.xlsx"
    workbook.save(xlsx_path)

    result = import_projects_from_file(xlsx_path, repository, store)
    saved = repository.get_project_by_task_order_no("WO-XLSX")

    assert result.created_count == 1
    assert saved is not None
    assert saved.project_name == "Excel项目"
    assert saved.aliases == ("Excel Group",)


def test_build_project_template_content_includes_required_headers() -> None:
    template = build_project_template_content()

    assert "task_order_no" in template
    assert "project_name" in template
    assert "group_aliases" in template
