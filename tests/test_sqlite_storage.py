import json
import sqlite3
from pathlib import Path

from aica.models import TicketSnapshot, TicketSummaryFields
from aica.storage.contracts import ProjectRecord
from aica.storage.sqlite.repositories import SQLiteProjectRepository
from aica.todo_events import TodoBindingStore
from aica.todo_store import TodoStore


def _snapshot(
    title: str,
    summary: str,
    timeline: str,
    *,
    group_name: str = "group-a",
    environment: str = "prod",
    product_line: str = "",
    ticket_type: str = "鎺掓煡绫?",
) -> TicketSnapshot:
    return TicketSnapshot(
        title=title,
        fields=TicketSummaryFields(
            group_name=group_name,
            environment=environment,
            product_line=product_line,
            ticket_type=ticket_type,
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
                project_name="鏂囨。涓彴椤圭洰",
                customer_name="瀹㈡埛A",
                product_line="鏂囨。涓彴",
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
    assert todo.project_link.project_snapshot["product_line"] == "鏂囨。涓彴"
    assert todo.summary_fields.product_line == "鏂囨。涓彴"


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
                        "ticket_type": "鎺掓煡绫?",
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
