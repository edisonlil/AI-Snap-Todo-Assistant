from aica.models import TicketSummaryFields
from aica.todo_detail_panel import _TodoDetailBridge
from aica.todo_store import TimelineEvent, TodoItem


def test_add_timeline_entry_expands_empty_timeline_and_persists() -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[],
        )
    )

    assert bridge.timelineCount == 0
    assert bridge.timelineExpanded is False

    captured: dict[str, object] = {}

    def _capture(todo_id: str, payload: object) -> None:
        captured["todo_id"] = todo_id
        captured["payload"] = payload

    bridge.saveRequested.connect(_capture)
    bridge.addTimelineEntry("manual follow-up")

    assert bridge.timelineCount == 1
    assert bridge.timelineExpanded is True
    assert bridge.timeline[0]["content"] == "manual follow-up"
    assert bridge.timeline[0]["kind"] == "manual"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    timeline = payload["timeline"]
    assert isinstance(timeline, list)
    assert timeline[-1].content == "manual follow-up"


def test_commit_timeline_content_persists_manual_edits() -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[TimelineEvent(content="initial record", scenario="assistant")],
        )
    )

    captured: dict[str, object] = {}

    def _capture(todo_id: str, payload: object) -> None:
        captured["todo_id"] = todo_id
        captured["payload"] = payload

    bridge.saveRequested.connect(_capture)
    bridge.addTimelineEntry("manual follow-up")
    manual_id = bridge.timeline[0]["id"]
    bridge.commitTimelineContent(manual_id, "manual follow-up updated")

    payload = captured["payload"]
    assert isinstance(payload, dict)
    timeline = payload["timeline"]
    assert isinstance(timeline, list)
    assert timeline[-1].content == "manual follow-up updated"
    assert timeline[-1].kind == "manual"


def test_delete_timeline_entry_persists_removal() -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[
                TimelineEvent(content="first record", scenario="assistant"),
                TimelineEvent(content="second record", scenario="assistant"),
            ],
        )
    )

    event_id = bridge.timeline[0]["id"]
    captured: dict[str, object] = {}

    def _capture(todo_id: str, payload: object) -> None:
        captured["todo_id"] = todo_id
        captured["payload"] = payload

    bridge.saveRequested.connect(_capture)
    bridge.deleteTimelineEntry(event_id)

    assert bridge.timelineCount == 1
    payload = captured["payload"]
    assert isinstance(payload, dict)
    timeline = payload["timeline"]
    assert isinstance(timeline, list)
    assert len(timeline) == 1
