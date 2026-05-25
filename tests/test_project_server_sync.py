from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.project_management import split_project_product_lines, sync_projects_from_server  # noqa: E402
from aica.storage.contracts import ProjectRecord  # noqa: E402


class _FakeClient:
    def __init__(self, items: list[dict[str, object]]) -> None:
        self.items = items

    def fetch_my_latest_projects(self, *, page_size: int = 200, max_pages: int = 100) -> list[dict[str, object]]:
        return list(self.items)


class _FakeProjectRepository:
    def __init__(self, projects: list[ProjectRecord]) -> None:
        self.projects = {project.task_order_no: project for project in projects}
        self.saved: list[ProjectRecord] = []

    def list_projects(self, *, include_expired: bool = True) -> list[ProjectRecord]:
        return list(self.projects.values())

    def upsert_project(self, project: ProjectRecord) -> ProjectRecord:
        self.projects[project.task_order_no] = project
        self.saved.append(project)
        return project


class _FakeTodoStore:
    def __init__(self) -> None:
        self.relink_count = 0

    def relink_open_unresolved_todos(self) -> int:
        self.relink_count += 1
        return 3


def test_sync_projects_from_server_updates_existing_but_preserves_product_version() -> None:
    existing = ProjectRecord(
        id="local-project",
        project_name="old project",
        customer_name="old customer",
        task_order_no="TASK-001",
        follow_up_started_at="2026-01-01T09:00:00",
        support_ended_at="2026-12-31T23:59:59",
        product_line="old product",
        product_version="old version",
        project_manager="old manager",
        project_level="important",
        aliases=("local-group", "shared-group"),
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-02T00:00:00",
    )
    repository = _FakeProjectRepository([existing])
    todo_store = _FakeTodoStore()
    client = _FakeClient(
        [
            {
                "task_order_no": "TASK-001",
                "project_name": "new project",
                "customer_name": "new customer",
                "product_line": "new product",
                "product_version": "v2",
                "project_manager": "Alice",
                "follow_up_started_at": "2026-02-01T09:00:00",
                "support_ended_at": "2027-12-31T23:59:59",
                "project_level": "normal",
                "created_at": "2026-02-01T00:00:00",
                "updated_at": "2026-02-02T00:00:00",
                "chat_group_names": ["shared-group", "remote-group", "remote-group"],
            },
            {
                "taskOrderNo": "TASK-002",
                "projectName": "created project",
                "customerName": "created customer",
                "productLine": "product b",
                "productVersion": "v1",
                "projectManager": "Bob",
                "followUpStartedAt": "2026-03-01T09:00:00",
                "supportEndedAt": "2028-12-31T23:59:59",
                "projectLevel": "important",
                "createdAt": "2026-03-01T00:00:00",
                "chatGroupNames": ["created-group"],
            },
            {
                "task_order_no": "",
                "project_name": "invalid project",
            },
        ]
    )

    result = sync_projects_from_server(client, repository, todo_store)

    assert result.created_count == 1
    assert result.updated_count == 1
    assert result.skipped_count == 1
    assert result.relinked_count == 3
    assert todo_store.relink_count == 1
    updated = repository.projects["TASK-001"]
    assert updated.id == "local-project"
    assert updated.project_name == "new project"
    assert updated.customer_name == "new customer"
    assert updated.product_line == "new product"
    assert updated.product_version == "old version"
    assert updated.project_manager == "Alice"
    assert updated.follow_up_started_at == "2026-02-01T09:00:00"
    assert updated.support_ended_at == "2027-12-31T23:59:59"
    assert updated.project_level == "normal"
    assert updated.created_at == "2026-02-01T00:00:00"
    assert updated.updated_at == "2026-02-02T00:00:00"
    assert updated.aliases == ("local-group", "shared-group", "remote-group")
    assert [project.task_order_no for project in repository.saved] == ["TASK-001", "TASK-002"]
    created = repository.projects["TASK-002"]
    assert created.project_name == "created project"
    assert created.aliases == ("created-group",)


def test_split_project_product_lines_deduplicates_comma_separated_values() -> None:
    assert split_project_product_lines("文档中台, 协作套件，文档中台;  ") == ("文档中台", "协作套件")
