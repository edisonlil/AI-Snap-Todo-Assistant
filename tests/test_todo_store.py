import json
from pathlib import Path

from aica.models import EvidenceItem, TicketSnapshot, TicketSummaryFields, UNKNOWN_TEXT
from aica.ticket_field_resolver import DEFAULT_PRODUCT_LINE, TICKET_TYPE_OPTIONS
from aica.todo_store import TimelineEvent, TodoStore


def _snapshot(
    title: str,
    summary: str,
    timeline: str,
    *,
    group_name: str = "group-a",
    environment: str = "prod",
    product_line: str = "line-a",
    ticket_type: str = TICKET_TYPE_OPTIONS[0],
    evidence_items: list[EvidenceItem] | None = None,
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
        evidence_items=evidence_items or [],
    )


def test_create_todo_from_analysis_persists_structured_item(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))

    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "check whether file still exists", "customer reported upload failed"),
        "todo assistant",
    )

    todos = store.list_active_todos()
    assert len(todos) == 1
    assert todos[0].id == todo.id
    assert todos[0].title == "upload failed"
    assert todos[0].summary_fields.group_name == "group-a"
    assert todos[0].current_summary == "check whether file still exists"
    assert todos[0].timeline[0].content == "customer reported upload failed"


def test_append_analysis_preserves_existing_title_and_summary(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "initial summary", "first record"),
        "todo assistant",
    )

    updated = store.append_analysis_to_todo(
        todo.id,
        _snapshot(
            "new title from screenshot",
            "new summary from screenshot",
            "new follow-up: observed http 500",
            group_name="new-group",
            environment="staging",
        ),
        "todo assistant",
    )

    assert updated is not None
    assert updated.timeline_count == 2
    assert updated.title == "upload failed"
    assert updated.current_summary == "initial summary"
    assert updated.summary_fields.group_name == "group-a"
    assert updated.summary_fields.environment == "prod"
    assert updated.timeline[-1].content == "new follow-up: observed http 500"


def test_append_analysis_backfills_unknown_fields_only(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot(
            "upload failed",
            "initial summary",
            "first record",
            group_name=UNKNOWN_TEXT,
            environment=UNKNOWN_TEXT,
        ),
        "todo assistant",
    )

    updated = store.append_analysis_to_todo(
        todo.id,
        _snapshot(
            "new title from screenshot",
            "new summary from screenshot",
            "new follow-up: observed http 500",
            group_name="recognized-group",
            environment="staging",
        ),
        "todo assistant",
    )

    assert updated is not None
    assert updated.summary_fields.group_name == "recognized-group"
    assert updated.summary_fields.environment == "staging"
    assert updated.summary_fields.product_line == DEFAULT_PRODUCT_LINE


def test_legacy_evidence_is_folded_into_timeline_when_loading(tmp_path: Path):
    path = tmp_path / "todos.json"
    payload = [
        {
            "id": "1",
            "title": "接口异常",
            "current_summary": "已有摘要",
            "status": "open",
            "timeline": [
                {
                    "content": "客户补充接口详情",
                    "evidence_items": [
                        {
                            "type": "request_param",
                            "label": "task_id",
                            "value": "abc123",
                        }
                    ],
                }
            ],
        }
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    store = TodoStore(str(path))
    todo = store.get_todo("1")

    assert todo is not None
    assert "客户补充接口详情" in todo.timeline[0].content
    assert "task_id" in todo.timeline[0].content
    assert "abc123" in todo.timeline[0].content


def test_update_todo_persists_fields_and_timeline(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("original title", "original summary", "original timeline"),
        "todo assistant",
    )

    updated = store.update_todo(
        todo.id,
        title="new title",
        current_summary="new summary",
        summary_fields=TicketSummaryFields(
            group_name="new-group",
            environment="test",
            product_line="new-line",
            ticket_type=TICKET_TYPE_OPTIONS[1],
        ),
        timeline=[TimelineEvent(content="edited timeline")],
    )

    assert updated is not None
    reloaded = store.get_todo(todo.id)
    assert reloaded is not None
    assert reloaded.title == "new title"
    assert reloaded.current_summary == "new summary"
    assert reloaded.summary_fields.product_line == DEFAULT_PRODUCT_LINE
    assert reloaded.summary_fields.ticket_type == TICKET_TYPE_OPTIONS[1]
    assert reloaded.timeline[0].content == "edited timeline"


def test_legacy_summary_json_is_migrated(tmp_path: Path):
    path = tmp_path / "todos.json"
    legacy_payload = [
        {
            "id": "1",
            "title": "legacy todo",
            "summary": json.dumps(
                {
                    "group_name": "legacy-group",
                    "environment": "prod",
                    "product_line": "legacy-line",
                    "ticket_type": TICKET_TYPE_OPTIONS[0],
                    "current_summary": "legacy summary",
                },
                ensure_ascii=False,
            ),
            "status": "open",
            "timeline": [{"summary": "legacy timeline"}],
        }
    ]
    path.write_text(json.dumps(legacy_payload, ensure_ascii=False), encoding="utf-8")

    store = TodoStore(str(path))
    todo = store.get_todo("1")

    assert todo is not None
    assert todo.summary_fields.group_name == "legacy-group"
    assert todo.summary_fields.product_line == DEFAULT_PRODUCT_LINE
    assert todo.summary_fields.ticket_type == TICKET_TYPE_OPTIONS[0]
    assert todo.current_summary == "legacy summary"
    assert todo.timeline[0].content == "legacy timeline"
