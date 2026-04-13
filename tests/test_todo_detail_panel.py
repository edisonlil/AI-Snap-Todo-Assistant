from aica import todo_detail_panel as module
from aica.models import TicketSummaryFields
from aica.todo_detail_panel import (
    _CONCLUSION_SCENARIO,
    _ENTRY_TYPE_CONCLUSION,
    _ENTRY_TYPE_FOLLOW_UP,
    _MANUAL_SCENARIO,
    _TodoDetailBridge,
    _attachment_kind,
    _clamp_panel_position,
    _coerce_dropped_file_paths,
    _resolve_available_geometry,
    _screen_for_point,
    _virtual_available_geometry,
)
from aica.todo_models import TodoProjectLink
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
    bridge.addTimelineEntry("manual follow-up", _ENTRY_TYPE_FOLLOW_UP)

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


def test_add_timeline_entry_sanitizes_invalid_surrogates() -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[],
        )
    )

    captured: dict[str, object] = {}

    def _capture(todo_id: str, payload: object) -> None:
        captured["todo_id"] = todo_id
        captured["payload"] = payload

    bridge.saveRequested.connect(_capture)
    bridge.addTimelineEntry("manual \udcaa follow-up", _ENTRY_TYPE_FOLLOW_UP)

    assert bridge.timeline[0]["content"] == "manual \ufffd follow-up"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    timeline = payload["timeline"]
    assert isinstance(timeline, list)
    assert timeline[-1].content == "manual \ufffd follow-up"


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
    bridge.addTimelineEntry("manual follow-up", _ENTRY_TYPE_FOLLOW_UP)
    manual_id = bridge.timeline[0]["id"]
    bridge.commitTimelineContent(manual_id, "manual follow-up updated")

    payload = captured["payload"]
    assert isinstance(payload, dict)
    timeline = payload["timeline"]
    assert isinstance(timeline, list)
    assert timeline[-1].content == "manual follow-up updated"
    assert timeline[-1].kind == "manual"


def test_set_todo_keeps_latest_conclusion_single_and_pinned_to_top() -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[
                TimelineEvent(content="first follow-up", kind="manual", scenario="手动跟进"),
                TimelineEvent(content="old conclusion", kind="conclusion", scenario="结论更新"),
                TimelineEvent(content="second follow-up", kind="manual", scenario="手动跟进"),
                TimelineEvent(content="latest conclusion", kind="conclusion", scenario="结论更新"),
            ],
        )
    )

    assert bridge.timelineCount == 3
    assert bridge.timeline[0]["kind"] == "conclusion"
    assert bridge.timeline[0]["content"] == "latest conclusion"
    assert bridge.timeline[0]["scenario"] == _CONCLUSION_SCENARIO
    assert [item["content"] for item in bridge.timeline[1:]] == ["second follow-up", "first follow-up"]


def test_add_follow_up_keeps_existing_conclusion_at_top() -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[
                TimelineEvent(content="latest conclusion", kind="conclusion", scenario="结论更新"),
            ],
        )
    )

    bridge.addTimelineEntry("manual follow-up", _ENTRY_TYPE_FOLLOW_UP)

    assert bridge.timeline[0]["kind"] == "conclusion"
    assert bridge.timeline[0]["content"] == "latest conclusion"
    assert bridge.timeline[1]["kind"] == "manual"
    assert bridge.timeline[1]["scenario"] == _MANUAL_SCENARIO


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


def test_screen_for_point_prefers_screen_at(monkeypatch) -> None:
    primary = object()
    secondary = object()

    monkeypatch.setattr(module.QGuiApplication, "screenAt", staticmethod(lambda _point: secondary))
    monkeypatch.setattr(module.QApplication, "primaryScreen", staticmethod(lambda: primary))

    assert _screen_for_point(object()) is secondary


def test_virtual_available_geometry_unites_screens(monkeypatch) -> None:
    class _Geometry:
        def __init__(self, left: int, top: int, right: int, bottom: int) -> None:
            self._left = left
            self._top = top
            self._right = right
            self._bottom = bottom

        def availableGeometry(self):
            return self

        def left(self) -> int:
            return self._left

        def top(self) -> int:
            return self._top

        def right(self) -> int:
            return self._right

        def bottom(self) -> int:
            return self._bottom

        def united(self, other: "_Geometry") -> "_Geometry":
            return _Geometry(
                min(self._left, other.left()),
                min(self._top, other.top()),
                max(self._right, other.right()),
                max(self._bottom, other.bottom()),
            )

    class _Screen:
        def __init__(self, geometry: _Geometry) -> None:
            self._geometry = geometry

        def availableGeometry(self):
            return self._geometry

    screens = [
        _Screen(_Geometry(0, 0, 1919, 1079)),
        _Screen(_Geometry(1920, 0, 3839, 1079)),
    ]

    monkeypatch.setattr(module.QApplication, "screens", staticmethod(lambda: screens))
    monkeypatch.setattr(module.QApplication, "primaryScreen", staticmethod(lambda: screens[0]))

    available = _virtual_available_geometry()

    assert available.left() == 0
    assert available.top() == 0
    assert available.right() == 3839
    assert available.bottom() == 1079


def test_update_panel_drag_keeps_continuous_virtual_coordinates(monkeypatch) -> None:
    class _Geometry:
        def __init__(self, left: int, top: int, right: int, bottom: int) -> None:
            self._left = left
            self._top = top
            self._right = right
            self._bottom = bottom

        def availableGeometry(self):
            return self

        def left(self) -> int:
            return self._left

        def top(self) -> int:
            return self._top

        def right(self) -> int:
            return self._right

        def bottom(self) -> int:
            return self._bottom

        def united(self, other: "_Geometry") -> "_Geometry":
            return _Geometry(
                min(self._left, other.left()),
                min(self._top, other.top()),
                max(self._right, other.right()),
                max(self._bottom, other.bottom()),
            )

    class _Screen:
        def __init__(self, geometry: _Geometry) -> None:
            self._geometry = geometry

        def availableGeometry(self):
            return self._geometry

    class _CursorPos:
        def __init__(self, x: int, y: int) -> None:
            self._x = x
            self._y = y

        def x(self) -> int:
            return self._x

        def y(self) -> int:
            return self._y

    class _Panel:
        def __init__(self) -> None:
            self._drag_active = True
            self._drag_offset_x = 20
            self._drag_offset_y = 10
            self._screen_margin = 20
            self._calls: list[tuple[int, int]] = []

        def width(self) -> int:
            return 396

        def height(self) -> int:
            return 724

        def setPosition(self, x: int, y: int) -> None:
            self._calls.append((x, y))

        def _move_within_screen(self, x: int, y: int, screen) -> None:
            available = _resolve_available_geometry(screen)
            target_x, target_y = _clamp_panel_position(
                int(x),
                int(y),
                panel_width=self.width(),
                panel_height=self.height(),
                available_left=available.left(),
                available_top=available.top(),
                available_right=available.right(),
                available_bottom=available.bottom(),
                margin=self._screen_margin,
            )
            self.setPosition(target_x, target_y)

    screens = [
        _Screen(_Geometry(0, 0, 1919, 1079)),
        _Screen(_Geometry(1920, 0, 3839, 1079)),
    ]
    panel = _Panel()

    monkeypatch.setattr(module.QApplication, "screens", staticmethod(lambda: screens))
    monkeypatch.setattr(module.QApplication, "primaryScreen", staticmethod(lambda: screens[0]))
    monkeypatch.setattr(module.QCursor, "pos", staticmethod(lambda: _CursorPos(2400, 120)))

    module.TodoDetailPanel._update_panel_drag(panel)

    assert panel._calls == [(2380, 110)]


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


def test_set_todo_exposes_sync_status_and_external_id() -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[],
        ),
        sync_records=[
            {
                "integration_id": "company-platform",
                "external_id": "EXT-001",
                "updated_at": "2026-04-10T12:30:00",
                "last_event_type": "manual_sync",
                "last_sync_status": "ok:updated",
            }
        ],
    )

    assert bridge.syncIntegrationId == "company-platform"
    assert bridge.syncStatus == "已同步"
    assert bridge.syncStatusDetail == "ok:updated"
    assert bridge.syncEventLabel == "manual_sync"
    assert bridge.syncUpdatedAtLabel == "04-10 12:30"
    assert bridge.externalId == "EXT-001"
    assert bridge.hasExternalId is True
    assert bridge.syncRecordCount == 1
    assert bridge.syncRecords[0]["eventType"] == "manual_sync"


def test_copy_external_id_writes_to_clipboard(monkeypatch) -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[],
        ),
        sync_records=[
            {
                "integration_id": "company-platform",
                "external_id": "EXT-001",
                "last_sync_status": "ok:created",
            }
        ],
    )

    captured: dict[str, str] = {}

    class _Clipboard:
        def setText(self, text: str) -> None:
            captured["text"] = text

    from aica import todo_detail_panel as module

    monkeypatch.setattr(module.QApplication, "clipboard", staticmethod(lambda: _Clipboard()))
    bridge.copyExternalId()

    assert captured["text"] == "EXT-001"


def test_request_manual_sync_emits_current_todo_id() -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            id="todo-123",
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[],
        )
    )
    captured: list[str] = []
    bridge.manualSyncRequested.connect(captured.append)

    bridge.requestManualSync()

    assert captured == ["todo-123"]


def test_save_todo_emits_conclusion_and_root_cause_payload() -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            id="todo-123",
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[],
        )
    )
    captured: dict[str, object] = {}

    def _capture(todo_id: str, payload: object) -> None:
        captured["todo_id"] = todo_id
        captured["payload"] = payload

    bridge.saveRequested.connect(_capture)
    bridge.updateField("root_cause_desc", "接口参数错误")
    bridge.updateField("root_cause", "配置错误")
    bridge.updateField("conclusion_content", "确认是生产配置缺失")
    bridge.saveTodo()

    payload = captured["payload"]
    assert isinstance(payload, dict)
    summary_fields = payload["summary_fields"]
    assert summary_fields["root_cause_desc"] == "接口参数错误"
    assert summary_fields["root_cause_desc_source"] == "manual"
    assert summary_fields["root_cause"] == "配置错误"
    assert summary_fields["root_cause_source"] == "manual"
    conclusion = payload["conclusion"]
    assert conclusion.content == "确认是生产配置缺失"


def test_add_timeline_entry_with_conclusion_type_updates_conclusion_only() -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            id="todo-123",
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[],
        )
    )

    captured: dict[str, object] = {}

    def _capture(todo_id: str, payload: object) -> None:
        captured["todo_id"] = todo_id
        captured["payload"] = payload

    bridge.saveRequested.connect(_capture)
    bridge.addTimelineEntry("确认是生产配置缺失", _ENTRY_TYPE_CONCLUSION)

    assert bridge.timelineCount == 0
    assert bridge.conclusionContent == "确认是生产配置缺失"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    conclusion = payload["conclusion"]
    assert conclusion.content == "确认是生产配置缺失"
    assert payload["timeline"] == []


def test_add_timeline_entry_strips_conclusion_command_prefix() -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            id="todo-123",
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[],
        )
    )

    captured: dict[str, object] = {}

    def _capture(todo_id: str, payload: object) -> None:
        captured["todo_id"] = todo_id
        captured["payload"] = payload

    bridge.saveRequested.connect(_capture)
    bridge.addTimelineEntry("/问题结论 确认是生产配置缺失", _ENTRY_TYPE_FOLLOW_UP)

    assert bridge.conclusionContent == "确认是生产配置缺失"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    conclusion = payload["conclusion"]
    assert conclusion.content == "确认是生产配置缺失"


def test_add_timeline_entry_ignores_command_without_body() -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            id="todo-123",
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[],
        )
    )

    captured: list[object] = []
    bridge.saveRequested.connect(lambda _todo_id, payload: captured.append(payload))

    bridge.addTimelineEntry("/问题结论", _ENTRY_TYPE_CONCLUSION)

    assert captured == []
    assert bridge.timelineCount == 0
    assert bridge.conclusionContent == ""


def test_set_todo_exposes_project_match_status_fields() -> None:
    bridge = _TodoDetailBridge()
    bridge.set_todo(
        TodoItem(
            title="title",
            summary_fields=TicketSummaryFields(),
            current_summary="summary",
            timeline=[],
            project_link=TodoProjectLink(
                match_status="matched",
                project_snapshot={
                    "project_name": "项目A",
                    "task_order_no": "WO-1",
                    "project_manager": "张三",
                },
            ),
        )
    )

    assert bridge.projectMatchStatus == "已关联项目"
    assert bridge.projectMatchDetail == "项目A · WO-1"
    assert bridge.projectName == "项目A"
    assert bridge.projectTaskOrderNo == "WO-1"
    assert bridge.projectManager == "张三"
