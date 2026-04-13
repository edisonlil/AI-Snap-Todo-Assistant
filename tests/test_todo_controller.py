from pathlib import Path

from aica.models import EvidenceItem, TicketSnapshot, TicketSummaryFields, UNKNOWN_TEXT
from aica.ticket_enrichment import EnrichmentOutcome
from aica.ticket_field_resolver import TICKET_TYPE_OPTIONS
from aica.todo_controller import TodoController
from aica.todo_events import TodoDomainEvent, TodoDomainEventType
from aica.todo_store import TimelineAttachment, TimelineEvent, TodoConclusion, TodoStore


def _build_controller(tmp_path: Path) -> TodoController:
    store = TodoStore(str(tmp_path / "todos.json"))
    return TodoController(store)


class _Publisher:
    def __init__(self) -> None:
        self.events: list[TodoDomainEvent] = []

    def publish(self, event: TodoDomainEvent) -> None:
        self.events.append(event)


class _EnrichmentService:
    def enrich_for_update(self, **kwargs):
        current_fields = kwargs["current_fields"]
        return EnrichmentOutcome(
            summary_fields=TicketSummaryFields(
                group_name=current_fields.group_name,
                environment=current_fields.environment,
                product_line=current_fields.product_line,
                ticket_type=current_fields.ticket_type,
                ticket_version=current_fields.ticket_version,
                feature_point="导出模块",
                feature_point_source="auto",
                root_cause_desc="接口参数错误",
                root_cause_desc_source="auto",
                root_cause="配置错误",
                root_cause_source="auto",
            ),
            errors=[],
        )


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


def test_save_analysis_creates_todo_when_nothing_selected(tmp_path: Path):
    controller = _build_controller(tmp_path)

    result = controller.save_analysis_result(
        _snapshot("upload failed", "check whether file still exists", "customer reported upload failed"),
        "todo assistant",
    )

    assert result.action == "create"
    assert result.todo.timeline_count == 1
    assert result.todo.current_summary == "check whether file still exists"
    assert controller.selected_todo_id is None


def test_save_analysis_appends_to_selected_todo_and_clears_selection(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )
    controller.toggle_selected_todo(created.todo.id)

    result = controller.save_analysis_result(
        _snapshot(
            "new title from screenshot",
            "new summary from screenshot",
            "second follow-up",
            group_name="new-group",
            environment="staging",
        ),
        "todo assistant",
    )

    assert result.action == "append"
    assert result.todo.id == created.todo.id
    assert result.todo.timeline_count == 2
    assert result.todo.title == "upload failed"
    assert result.todo.current_summary == "initial summary"
    assert result.todo.summary_fields.group_name == "group-a"
    assert result.todo.summary_fields.environment == "prod"
    assert result.todo.timeline[-1].content == "second follow-up"
    assert controller.selected_todo_id is None


def test_save_analysis_append_backfills_unknown_fields_only(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot(
            "upload failed",
            "initial summary",
            "first follow-up",
            group_name=UNKNOWN_TEXT,
            environment=UNKNOWN_TEXT,
        ),
        "todo assistant",
    )
    controller.toggle_selected_todo(created.todo.id)

    result = controller.save_analysis_result(
        _snapshot(
            "new title from screenshot",
            "new summary from screenshot",
            "second follow-up",
            group_name="recognized-group",
            environment="staging",
        ),
        "todo assistant",
    )

    assert result.action == "append"
    assert result.todo.title == "upload failed"
    assert result.todo.current_summary == "initial summary"
    assert result.todo.summary_fields.group_name == "recognized-group"
    assert result.todo.summary_fields.environment == "staging"
    assert result.todo.summary_fields.product_line == UNKNOWN_TEXT


def test_save_analysis_append_keeps_details_in_timeline_only(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "工单跟进",
    )
    controller.toggle_selected_todo(created.todo.id)

    result = controller.save_analysis_result(
        _snapshot(
            "new title from screenshot",
            "new summary from screenshot",
            "客户补充了接口参数",
            evidence_items=[
                EvidenceItem(
                    type="request_param",
                    label="task_id",
                    value="abc123",
                    source_image_index=2,
                    scene_type="api_detail",
                )
            ],
        ),
        "参数与接口详情",
    )

    assert result.action == "append"
    assert result.todo.current_summary == "initial summary"
    assert "task_id" not in result.todo.current_summary
    assert "task_id" in result.todo.timeline[-1].content


def test_update_todo_updates_fields_and_timeline(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("title", "summary", "timeline"),
        "todo assistant",
    )

    updated = controller.update_todo(
        created.todo.id,
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
    assert updated.title == "new title"
    assert updated.current_summary == "new summary"
    assert updated.summary_fields.group_name == "new-group"
    assert updated.summary_fields.product_line == UNKNOWN_TEXT
    assert updated.summary_fields.ticket_type == TICKET_TYPE_OPTIONS[1]


def test_delete_todo_clears_selection_and_removes_item(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("title", "summary", "timeline"),
        "todo assistant",
    )
    controller.toggle_selected_todo(created.todo.id)

    assert controller.delete_todo(created.todo.id)
    assert controller.selected_todo_id is None
    assert controller.get_active_todos() == []


def test_update_todo_publishes_updated_event(tmp_path: Path):
    publisher = _Publisher()
    store = TodoStore(str(tmp_path / "todos.json"))
    controller = TodoController(store, event_publisher=publisher)
    created = controller.save_analysis_result(
        _snapshot("title", "summary", "timeline"),
        "todo assistant",
    )
    publisher.events.clear()

    controller.update_todo(created.todo.id, title="new title", current_summary="new summary")

    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event.event_type == TodoDomainEventType.UPDATED
    assert event.todo_snapshot["title"] == "new title"
    assert event.todo_snapshot["current_summary"] == "new summary"
    assert event.delta == {"changed_fields": ["title", "current_summary"]}


def test_build_manual_sync_event_uses_current_todo_snapshot(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("title", "summary", "timeline"),
        "todo assistant",
    )

    event = controller.build_manual_sync_event(created.todo.id)

    assert event is not None
    assert event.event_type == TodoDomainEventType.MANUAL_SYNC
    assert event.todo_id == created.todo.id
    assert event.delta == {"trigger": "manual"}


def test_update_todo_appends_conclusion_history_and_enrichment_fields(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    controller = TodoController(store, enrichment_service=_EnrichmentService())
    created = controller.save_analysis_result(
        _snapshot("title", "summary", "timeline"),
        "todo assistant",
    )

    updated = controller.update_todo(
        created.todo.id,
        current_summary="new summary",
        summary_fields=TicketSummaryFields(
            group_name="group-a",
            environment="prod",
            product_line="line-a",
            ticket_type=TICKET_TYPE_OPTIONS[0],
        ),
        conclusion=TodoConclusion(
            content="确认是生产配置缺失",
            updated_at="2026-04-13T12:00:00",
            attachments=[
                TimelineAttachment(
                    id="attachment-1",
                    name="evidence.png",
                    path=str(tmp_path / "evidence.png"),
                    size_bytes=32,
                )
            ],
        ),
    )

    assert updated is not None
    assert updated.summary_fields.feature_point == "导出模块"
    assert updated.summary_fields.root_cause_desc == "接口参数错误"
    assert updated.summary_fields.root_cause == "配置错误"
    assert updated.conclusion.content == "确认是生产配置缺失"
    assert updated.timeline[-1].kind == "conclusion"
    assert "确认是生产配置缺失" in updated.timeline[-1].content


def test_update_todo_does_not_duplicate_existing_conclusion_timeline_event(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("title", "summary", "timeline"),
        "todo assistant",
    )
    existing_timeline = [
        TimelineEvent(content="timeline"),
        TimelineEvent(
            kind="conclusion",
            scenario="结论更新",
            content="确认是生产配置缺失",
        ),
    ]

    updated = controller.update_todo(
        created.todo.id,
        timeline=existing_timeline,
        conclusion=TodoConclusion(
            content="确认是生产配置缺失",
            updated_at="2026-04-13T12:00:00",
        ),
    )

    assert updated is not None
    conclusion_events = [event for event in updated.timeline if event.kind == "conclusion"]
    assert len(conclusion_events) == 1


def test_update_todo_replaces_old_conclusion_event_with_latest_one(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("title", "summary", "timeline"),
        "todo assistant",
    )
    existing_timeline = [
        TimelineEvent(content="timeline"),
        TimelineEvent(
            kind="conclusion",
            scenario="结论更新",
            content="old conclusion",
        ),
    ]

    updated = controller.update_todo(
        created.todo.id,
        timeline=existing_timeline,
        conclusion=TodoConclusion(
            content="latest conclusion",
            updated_at="2026-04-13T12:00:00",
        ),
    )

    assert updated is not None
    conclusion_events = [event for event in updated.timeline if event.kind == "conclusion"]
    assert len(conclusion_events) == 1
    assert conclusion_events[0].content == "latest conclusion"
    assert updated.timeline[-1].kind == "conclusion"
