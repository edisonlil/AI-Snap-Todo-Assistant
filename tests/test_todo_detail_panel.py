from aica.models import TicketSummaryFields
from aica.todo_detail_panel import _TodoDetailBridge, _attachment_kind, _coerce_dropped_file_paths
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


def test_save_todo_persists_live_timeline_edits_without_blur() -> None:
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
    event_id = bridge.timeline[0]["id"]
    bridge.updateTimelineContent(event_id, "edited without blur")
    bridge.saveTodo()

    payload = captured["payload"]
    assert isinstance(payload, dict)
    timeline = payload["timeline"]
    assert isinstance(timeline, list)
    assert timeline[-1].content == "edited without blur"


def test_add_timeline_attachment_copies_file_and_persists(tmp_path) -> None:
    source = tmp_path / "evidence.txt"
    source.write_text("hello attachment", encoding="utf-8")

    bridge = _TodoDetailBridge(attachment_root=tmp_path / "attachments")
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
    event_id = bridge.timeline[0]["id"]
    bridge.attach_files_to_event(event_id, [str(source)])

    assert bridge.timeline[0]["attachmentCount"] == 1
    attachments = bridge.timeline[0]["attachments"]
    assert isinstance(attachments, list)
    copied_path = attachments[0]["path"]
    assert copied_path != str(source)
    payload = captured["payload"]
    assert isinstance(payload, dict)
    timeline = payload["timeline"]
    assert isinstance(timeline, list)
    assert timeline[-1].attachments[0].name == "evidence.txt"


def test_coerce_dropped_file_paths_normalizes_file_urls_and_deduplicates() -> None:
    paths = _coerce_dropped_file_paths(
        [
            "file:///C:/Temp/evidence.txt",
            "C:\\Temp\\evidence.txt",
            "file:///C:/Temp/second.log",
        ]
    )

    assert paths == ["C:/Temp/evidence.txt", "C:/Temp/second.log"]


def test_attachment_kind_classifies_previewable_types() -> None:
    assert _attachment_kind("demo.png") == "image"
    assert _attachment_kind("video.mp4") == "video"
    assert _attachment_kind("archive.zip") == "file"


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
