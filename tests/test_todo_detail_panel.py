from aica.models import TicketSummaryFields
from aica.todo_detail_panel import (
    _MANUAL_SCENARIO,
    _TodoDetailBridge,
    _attachment_kind,
    _clamp_panel_position,
    _coerce_dropped_file_paths,
    _resolve_available_geometry,
)
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
    assert bridge.timeline[0]["scenario"] == _MANUAL_SCENARIO
    payload = captured["payload"]
    assert isinstance(payload, dict)
    timeline = payload["timeline"]
    assert isinstance(timeline, list)
    assert timeline[-1].content == "manual follow-up"
    assert timeline[-1].scenario == _MANUAL_SCENARIO


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


def test_clamp_panel_position_keeps_panel_inside_available_area() -> None:
    x, y = _clamp_panel_position(
        2000,
        -20,
        panel_width=396,
        panel_height=724,
        available_left=0,
        available_top=0,
        available_right=1440,
        available_bottom=900,
        margin=20,
    )

    assert x == 1024
    assert y == 20


def test_begin_update_finish_panel_drag_emit_bridge_signals() -> None:
    bridge = _TodoDetailBridge()
    captured: list[tuple[str, tuple[object, ...]]] = []

    bridge.panelDragStarted.connect(lambda x, y: captured.append(("start", (x, y))))
    bridge.panelDragMoved.connect(lambda: captured.append(("move", ())))
    bridge.panelDragFinished.connect(lambda: captured.append(("finish", ())))

    bridge.beginPanelDrag(18, 24)
    bridge.updatePanelDrag()
    bridge.finishPanelDrag()

    assert captured == [
        ("start", (18.0, 24.0)),
        ("move", ()),
        ("finish", ()),
    ]


def test_resolve_available_geometry_accepts_screen_like_object() -> None:
    class _Geometry:
        pass

    class _Screen:
        def __init__(self):
            self.geometry = _Geometry()

        def availableGeometry(self):
            return self.geometry

    screen = _Screen()

    assert _resolve_available_geometry(screen) is screen.geometry
    assert _resolve_available_geometry(screen.geometry) is screen.geometry


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


def test_activate_attachment_routes_image_to_copy(tmp_path) -> None:
    attachment = tmp_path / "demo.png"
    attachment.write_bytes(b"fake-image")
    bridge = _TodoDetailBridge()
    captured: list[Path] = []

    bridge._copy_image_attachment = lambda path: captured.append(path)  # type: ignore[method-assign]
    bridge._copy_file_to_clipboard = lambda path: captured.append(Path("video"))  # type: ignore[method-assign]
    bridge._download_attachment = lambda source, name: captured.append(Path("download"))  # type: ignore[method-assign]

    bridge.activateAttachment(str(attachment), True, False, attachment.name)

    assert captured == [attachment]


def test_activate_attachment_routes_video_to_clipboard_file(tmp_path) -> None:
    attachment = tmp_path / "demo.mp4"
    attachment.write_bytes(b"fake-video")
    bridge = _TodoDetailBridge()
    captured: list[Path] = []

    bridge._copy_image_attachment = lambda path: captured.append(Path("image"))  # type: ignore[method-assign]
    bridge._copy_file_to_clipboard = lambda path: captured.append(path)  # type: ignore[method-assign]
    bridge._download_attachment = lambda source, name: captured.append(Path("download"))  # type: ignore[method-assign]

    bridge.activateAttachment(str(attachment), False, True, attachment.name)

    assert captured == [attachment]


def test_activate_attachment_routes_other_files_to_download(tmp_path) -> None:
    attachment = tmp_path / "demo.zip"
    attachment.write_bytes(b"fake-archive")
    bridge = _TodoDetailBridge()
    captured: list[tuple[Path, str]] = []

    bridge._copy_image_attachment = lambda path: None  # type: ignore[method-assign]
    bridge._copy_file_to_clipboard = lambda path: None  # type: ignore[method-assign]
    bridge._download_attachment = lambda source, name: captured.append((source, name))  # type: ignore[method-assign]

    bridge.activateAttachment(str(attachment), False, False, attachment.name)

    assert captured == [(attachment, "demo.zip")]
