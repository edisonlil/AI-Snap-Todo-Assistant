from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.models import TicketSummaryFields
from aica.todo_detail_panel import TodoDetailPanel, _resolve_neighbor_panel_x, _StageSummaryWindow, _TodoDetailBridge
from aica.todo_models import TodoConclusion, TodoItem


def _build_bridge(attachment_root: Path) -> _TodoDetailBridge:
    return _TodoDetailBridge(
        attachment_root=attachment_root,
        environment_access_service=SimpleNamespace(
            list_project_environments=lambda _project_id: [],
        ),
    )


def _build_panel(monkeypatch) -> TodoDetailPanel:
    monkeypatch.setattr(
        "aica.todo_detail_panel.SQLiteProjectEnvironmentRepository",
        lambda: SimpleNamespace(
            list_project_environments=lambda _project_id: [],
            get_access_entry=lambda _entry_id: None,
        ),
    )
    return TodoDetailPanel()


def _notification_messages(bridge: _TodoDetailBridge) -> list[str]:
    return [str(item["message"]) for item in bridge.notificationBridge.notifications]


def _build_todo(todo_id: str = "todo-1") -> TodoItem:
    return TodoItem(
        id=todo_id,
        title="测试待办",
        current_summary="当前摘要",
        summary_fields=TicketSummaryFields(),
        conclusion=TodoConclusion(),
        timeline=[],
    )


class _FakeAvailableGeometry:
    def __init__(self, width: int = 1600, height: int = 900) -> None:
        self._width = width
        self._height = height

    def left(self) -> int:
        return 0

    def right(self) -> int:
        return self._width - 1

    def top(self) -> int:
        return 0

    def bottom(self) -> int:
        return self._height - 1

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height


class _FakeAnchorWindow:
    def __init__(self, x: int = 100, y: int = 120) -> None:
        self._x = x
        self._y = y

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def frameGeometry(self):
        return SimpleNamespace(center=lambda: object())


def test_add_timeline_entry_moves_draft_attachments_into_new_event(monkeypatch) -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    copied_targets: list[str] = []
    moved_targets: list[tuple[str, str]] = []

    def _fake_copy_attachment(file_path: str, event_id: str) -> dict[str, object]:
        copied_targets.append(event_id)
        return {
            "id": "draft-1",
            "name": Path(file_path).name,
            "path": f"/draft/{Path(file_path).name}",
            "sizeBytes": 10,
            "isImage": False,
            "isVideo": False,
            "isPreviewable": False,
            "fileUrl": "",
        }

    def _fake_move_attachment(file_path: str, event_id: str) -> dict[str, object]:
        moved_targets.append((file_path, event_id))
        return {
            "id": "final-1",
            "name": Path(file_path).name,
            "path": f"/final/{event_id}/{Path(file_path).name}",
            "sizeBytes": 10,
            "isImage": False,
            "isVideo": False,
            "isPreviewable": False,
            "fileUrl": "",
        }

    monkeypatch.setattr(bridge, "_copy_attachment", _fake_copy_attachment)
    monkeypatch.setattr(bridge, "_move_attachment_to_target", _fake_move_attachment)

    bridge.attach_files_to_draft_timeline(["note.txt"])

    assert bridge.draftTimelineAttachmentCount == 1
    assert copied_targets == ["__draft_timeline__"]

    bridge.addTimelineEntry("新增进展", "follow_up")

    assert bridge.draftTimelineAttachmentCount == 0
    assert bridge.timelineCount == 1
    event = bridge.timeline[0]
    assert event["content"] == "新增进展"
    assert event["attachmentCount"] == 1
    assert moved_targets == [("/draft/note.txt", event["id"])]
    assert event["attachments"][0]["path"] == f"/final/{event['id']}/note.txt"


def test_add_conclusion_moves_draft_attachments_into_conclusion(monkeypatch) -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())
    bridge._conclusion_attachments = [  # noqa: SLF001
        {
            "id": "existing-1",
            "name": "existing.txt",
            "path": "/final/__conclusion__/existing.txt",
            "sizeBytes": 6,
            "isImage": False,
            "isVideo": False,
            "isPreviewable": False,
            "fileUrl": "",
        }
    ]

    monkeypatch.setattr(
        bridge,
        "_copy_attachment",
        lambda file_path, event_id: {
            "id": "draft-1",
            "name": Path(file_path).name,
            "path": f"/draft/{Path(file_path).name}",
            "sizeBytes": 12,
            "isImage": False,
            "isVideo": False,
            "isPreviewable": False,
            "fileUrl": "",
        },
    )
    monkeypatch.setattr(
        bridge,
        "_move_attachment_to_target",
        lambda file_path, event_id: {
            "id": "final-1",
            "name": Path(file_path).name,
            "path": f"/final/{event_id}/{Path(file_path).name}",
            "sizeBytes": 12,
            "isImage": False,
            "isVideo": False,
            "isPreviewable": False,
            "fileUrl": "",
        },
    )

    bridge.attach_files_to_draft_timeline(["report.txt"])
    bridge.addTimelineEntry("最终结论", "conclusion")

    assert bridge.draftTimelineAttachmentCount == 0
    assert bridge.conclusionContent == "最终结论"
    assert bridge.conclusionAttachmentCount == 2
    assert bridge.timelineCount == 1
    assert bridge.timeline[0]["kind"] == "conclusion"
    assert bridge.conclusionAttachments[0]["path"] == "/final/__conclusion__/existing.txt"
    assert bridge.conclusionAttachments[1]["path"] == "/final/__conclusion__/report.txt"


def test_timeline_entry_save_requests_use_autosave_mode() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    saved: list[tuple[str, dict[str, object]]] = []
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))

    bridge.addTimelineEntry("follow up", "follow_up")

    assert len(saved) == 1
    assert saved[0][0] == "todo-1"
    assert saved[0][1]["saveMode"] == "autosave"
    assert saved[0][1]["action"] == "append_timeline_entry"
    assert saved[0][1]["event"].kind == "manual"


def test_manual_save_requests_use_manual_mode() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    saved: list[tuple[str, dict[str, object]]] = []
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))

    bridge.saveTodo()

    assert len(saved) == 1
    assert saved[0][0] == "todo-1"
    assert saved[0][1]["saveMode"] == "manual"
    assert saved[0][1]["action"] == "save_detail_form"
    assert _notification_messages(bridge)[-1] == "保存成功"


def test_log_analysis_submission_pushes_notification() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    bridge.addTimelineEntry("request_id=req-9", "log_analysis")

    assert bridge.timelineCount == 1
    assert bridge.timeline[0]["type"] == "log_analysis_command"
    assert _notification_messages(bridge)[-1] == "已提交日志分析任务，后台排查中"


def test_removing_draft_attachment_does_not_touch_existing_event_attachments(monkeypatch) -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    def _fake_copy_attachment(file_path: str, event_id: str) -> dict[str, object]:
        return {
            "id": f"{event_id}-{Path(file_path).stem}",
            "name": Path(file_path).name,
            "path": f"/{event_id}/{Path(file_path).name}",
            "sizeBytes": 8,
            "isImage": False,
            "isVideo": False,
            "isPreviewable": False,
            "fileUrl": "",
        }

    removed_paths: list[str] = []
    monkeypatch.setattr(bridge, "_copy_attachment", _fake_copy_attachment)
    monkeypatch.setattr(bridge, "_remove_attachment_file", lambda file_path: removed_paths.append(file_path))

    bridge.addTimelineEntry("已有记录", "follow_up")
    event_id = str(bridge.timeline[0]["id"])
    bridge.attach_files_to_event(event_id, ["event.txt"])
    bridge.attach_files_to_draft_timeline(["draft.txt"])
    draft_attachment_id = str(bridge.draftTimelineAttachments[0]["id"])

    bridge.removeDraftTimelineAttachment(draft_attachment_id)

    assert bridge.draftTimelineAttachmentCount == 0
    assert bridge.timeline[0]["attachmentCount"] == 1
    assert bridge.timeline[0]["attachments"][0]["path"] == f"/{event_id}/event.txt"
    assert removed_paths == ["/__draft_timeline__/draft.txt"]


def test_toggle_stage_summary_requests_once_without_saving() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    requested: list[tuple[str, dict[str, object]]] = []
    saved: list[tuple[str, object]] = []
    bridge.stageSummaryRequested.connect(lambda todo_id, payload: requested.append((todo_id, payload)))
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))

    bridge.toggleStageSummary()

    assert bridge.stageSummaryVisible is True
    assert bridge.stageSummaryBusy is True
    assert bridge.hasStageSummary is False
    assert len(requested) == 1
    assert requested[0][0] == "todo-1"
    assert isinstance(requested[0][1]["todoPayload"], dict)
    assert saved == []

    bridge.toggleStageSummary()
    bridge.toggleStageSummary()

    assert len(requested) == 1


def test_stage_summary_result_resets_when_switching_todo() -> None:
    bridge = _build_bridge(Path("unused"))
    first_todo = _build_todo("todo-1")
    second_todo = _build_todo("todo-2")
    bridge.set_todo(first_todo)

    requested: list[dict[str, object]] = []
    bridge.stageSummaryRequested.connect(lambda _todo_id, payload: requested.append(payload))

    bridge.toggleStageSummary()
    request_id = str(requested[0]["requestId"])

    assert bridge.apply_stage_summary_result("todo-1", request_id, "阶段总结内容") is True
    assert bridge.stageSummaryText == "阶段总结内容"
    assert bridge.hasStageSummary is True

    bridge.set_todo(second_todo)

    assert bridge.stageSummaryVisible is False
    assert bridge.stageSummaryBusy is False
    assert bridge.stageSummaryText == ""
    assert bridge.stageSummaryError == ""
    assert bridge.hasStageSummary is False


def test_stage_summary_rewrite_does_not_change_save_payload() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    requested: list[dict[str, object]] = []
    rewritten: list[dict[str, object]] = []
    bridge.stageSummaryRequested.connect(lambda _todo_id, payload: requested.append(payload))
    bridge.stageSummaryRewriteRequested.connect(lambda _todo_id, payload: rewritten.append(payload))

    original_payload = bridge._build_payload()  # noqa: SLF001
    assert original_payload is not None

    bridge.toggleStageSummary()
    request_id = str(requested[0]["requestId"])
    bridge.apply_stage_summary_result("todo-1", request_id, "第一版阶段总结")

    bridge.rewriteStageSummaryWithPreset("shorter")

    assert bridge.stageSummaryBusy is True
    assert len(rewritten) == 1
    assert rewritten[0]["currentText"] == "第一版阶段总结"
    assert rewritten[0]["presetKey"] == "shorter"

    current_payload = bridge._build_payload()  # noqa: SLF001
    assert current_payload["title"] == original_payload["title"]
    assert current_payload["current_summary"] == original_payload["current_summary"]
    assert current_payload["summary_fields"] == original_payload["summary_fields"]
    assert current_payload["timeline"] == original_payload["timeline"]
    assert current_payload["conclusion"].content == original_payload["conclusion"].content
    assert current_payload["conclusion"].attachments == original_payload["conclusion"].attachments


def test_stage_summary_edit_updates_rewrite_source() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    requested: list[dict[str, object]] = []
    rewritten: list[dict[str, object]] = []
    bridge.stageSummaryRequested.connect(lambda _todo_id, payload: requested.append(payload))
    bridge.stageSummaryRewriteRequested.connect(lambda _todo_id, payload: rewritten.append(payload))

    bridge.toggleStageSummary()
    request_id = str(requested[0]["requestId"])
    bridge.apply_stage_summary_result("todo-1", request_id, "第一版阶段总结")

    bridge.updateStageSummaryText("阶段现状\n客户已补充现场截图")
    bridge.rewriteStageSummaryWithPreset("customer")

    assert bridge.stageSummaryText == "阶段现状\n客户已补充现场截图"
    assert len(rewritten) == 1
    assert rewritten[0]["currentText"] == "阶段现状\n客户已补充现场截图"
    assert rewritten[0]["presetKey"] == "customer"


def test_stage_summary_window_sync_uses_default_width_and_preferred_height(monkeypatch) -> None:
    bridge = _build_bridge(Path("unused"))
    window = _StageSummaryWindow(
        bridge,
        panel_width=443,
        panel_height=632,
        screen_margin=20,
    )
    available = _FakeAvailableGeometry(height=880)
    anchor = _FakeAnchorWindow()
    moved: list[tuple[int, int, object]] = []

    monkeypatch.setattr(
        window,
        "rootObject",
        lambda: SimpleNamespace(property=lambda name: 510 if name == "preferredHeight" else None),
        raising=False,
    )
    monkeypatch.setattr(
        "aica.todo_detail_panel._screen_for_point",
        lambda _point: "screen-token",
    )
    monkeypatch.setattr(
        "aica.todo_detail_panel._resolve_available_geometry",
        lambda _screen: available,
    )
    monkeypatch.setattr(
        "aica.todo_detail_panel._resolve_neighbor_panel_x",
        lambda *_args, **_kwargs: 700,
    )
    monkeypatch.setattr(
        window,
        "_move_within_screen",
        lambda x, y, screen: moved.append((x, y, screen)),
    )

    window.show_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)

    assert window.width() == 443
    assert window.height() == 510
    assert moved == [(700, 204, "screen-token")]


def test_stage_summary_window_manual_resize_persists_until_hidden(monkeypatch) -> None:
    bridge = _build_bridge(Path("unused"))
    window = _StageSummaryWindow(
        bridge,
        panel_width=443,
        panel_height=632,
        screen_margin=20,
    )
    available = _FakeAvailableGeometry(height=880)
    anchor = _FakeAnchorWindow()

    monkeypatch.setattr(
        window,
        "rootObject",
        lambda: SimpleNamespace(property=lambda name: 500 if name == "preferredHeight" else None),
        raising=False,
    )
    monkeypatch.setattr(
        "aica.todo_detail_panel._screen_for_point",
        lambda _point: "screen-token",
    )
    monkeypatch.setattr(
        "aica.todo_detail_panel._resolve_available_geometry",
        lambda _screen: available,
    )
    monkeypatch.setattr(
        "aica.todo_detail_panel._resolve_neighbor_panel_x",
        lambda *_args, **_kwargs: 650,
    )
    monkeypatch.setattr(window, "_move_within_screen", lambda *_args, **_kwargs: None)

    window.show_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)
    window.resize(520, 560)
    window._manual_size_override = True  # noqa: SLF001
    window.update_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)

    assert window.width() == 520
    assert window.height() == 560

    window.hide()
    window.show_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)

    assert window.width() == 443
    assert window.height() == 500


def test_stage_summary_window_manual_drag_persists_until_hidden(monkeypatch) -> None:
    bridge = _build_bridge(Path("unused"))
    window = _StageSummaryWindow(
        bridge,
        panel_width=443,
        panel_height=632,
        screen_margin=20,
    )
    available = _FakeAvailableGeometry(height=880)
    anchor = _FakeAnchorWindow()

    monkeypatch.setattr(
        window,
        "rootObject",
        lambda: SimpleNamespace(property=lambda name: 500 if name == "preferredHeight" else None),
        raising=False,
    )
    monkeypatch.setattr(
        "aica.todo_detail_panel._screen_for_point",
        lambda _point: "screen-token",
    )
    monkeypatch.setattr(
        "aica.todo_detail_panel._resolve_available_geometry",
        lambda _screen: available,
    )
    monkeypatch.setattr(
        "aica.todo_detail_panel._resolve_neighbor_panel_x",
        lambda *_args, **_kwargs: 650,
    )

    window.show_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)
    window.setPosition(720, 260)
    window._manual_position_override = True  # noqa: SLF001
    window.update_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)

    assert window.x() == 720
    assert window.y() == 260

    window.hide()
    window.show_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)

    assert window.x() == 650
    assert window.y() == 204


def test_show_todo_preserve_position_keeps_current_location(monkeypatch) -> None:
    panel = _build_panel(monkeypatch)
    panel.show()
    panel.setPosition(222, 333)

    reposition_calls: list[object] = []
    move_calls: list[tuple[int, int, object]] = []

    monkeypatch.setattr(
        "aica.todo_detail_panel._screen_for_point",
        lambda _point: "screen-token",
    )
    monkeypatch.setattr(panel, "_reposition", lambda anchor_rect=None: reposition_calls.append(anchor_rect))
    monkeypatch.setattr(panel, "_move_within_screen", lambda x, y, screen: move_calls.append((x, y, screen)))

    panel.show_todo(_build_todo(), preserve_position=True)

    assert reposition_calls == []
    assert move_calls == [(222, 333, "screen-token")]


def test_show_todo_preserve_position_clamps_current_location_within_screen(monkeypatch) -> None:
    panel = _build_panel(monkeypatch)
    panel.show()
    panel.setPosition(1400, 900)
    available = _FakeAvailableGeometry(width=800, height=900)

    monkeypatch.setattr(
        "aica.todo_detail_panel._screen_for_point",
        lambda _point: "screen-token",
    )
    monkeypatch.setattr(
        "aica.todo_detail_panel._resolve_available_geometry",
        lambda _screen: available,
    )
    monkeypatch.setattr(
        panel,
        "_reposition",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not reposition")),
    )

    panel.show_todo(_build_todo(), preserve_position=True)

    assert panel.x() == 383
    assert panel.y() == 155


def test_show_todo_repositions_when_position_is_not_preserved(monkeypatch) -> None:
    panel = _build_panel(monkeypatch)
    anchor_rect = SimpleNamespace(center=lambda: object())

    reposition_calls: list[object] = []
    move_calls: list[tuple[object, ...]] = []

    monkeypatch.setattr(panel, "_reposition", lambda rect=None: reposition_calls.append(rect))
    monkeypatch.setattr(panel, "_move_within_screen", lambda *args: move_calls.append(args))

    panel.show_todo(_build_todo(), anchor_rect=anchor_rect, preserve_position=True)

    assert reposition_calls == [anchor_rect]
    assert move_calls == []


def test_resolve_neighbor_panel_x_prefers_side_with_more_space() -> None:
    x = _resolve_neighbor_panel_x(
        900,
        396,
        panel_width=443,
        available_left=0,
        available_right=1599,
        margin=20,
        gap=18,
    )

    assert x == 439


def test_resolve_neighbor_panel_x_uses_right_when_right_has_more_space() -> None:
    x = _resolve_neighbor_panel_x(
        120,
        396,
        panel_width=443,
        available_left=0,
        available_right=1599,
        margin=20,
        gap=18,
    )

    assert x == 534


def test_resolve_neighbor_panel_x_prefers_left_when_both_sides_fit_but_left_is_wider() -> None:
    x = _resolve_neighbor_panel_x(
        1000,
        396,
        panel_width=443,
        available_left=0,
        available_right=2199,
        margin=20,
        gap=18,
    )

    assert x == 539


def test_stage_summary_same_result_sets_notice() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    requested: list[dict[str, object]] = []
    rewritten: list[dict[str, object]] = []
    bridge.stageSummaryRequested.connect(lambda _todo_id, payload: requested.append(payload))
    bridge.stageSummaryRewriteRequested.connect(lambda _todo_id, payload: rewritten.append(payload))

    bridge.toggleStageSummary()
    initial_request_id = str(requested[0]["requestId"])
    bridge.apply_stage_summary_result("todo-1", initial_request_id, "第一版阶段总结")

    bridge.rewriteStageSummaryWithPreset("shorter")
    rewrite_request_id = str(rewritten[0]["requestId"])

    assert bridge.apply_stage_summary_result(
        "todo-1",
        rewrite_request_id,
        "第一版阶段总结",
        "已调用模型重写，但返回内容未变化",
    ) is True
    assert bridge.stageSummaryText == "第一版阶段总结"
    assert bridge.stageSummaryNotice == "已调用模型重写，但返回内容未变化"


def test_stage_summary_manual_edit_clears_notice() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    requested: list[dict[str, object]] = []
    rewritten: list[dict[str, object]] = []
    bridge.stageSummaryRequested.connect(lambda _todo_id, payload: requested.append(payload))
    bridge.stageSummaryRewriteRequested.connect(lambda _todo_id, payload: rewritten.append(payload))

    bridge.toggleStageSummary()
    initial_request_id = str(requested[0]["requestId"])
    bridge.apply_stage_summary_result("todo-1", initial_request_id, "第一版阶段总结")

    bridge.rewriteStageSummaryWithPreset("shorter")
    rewrite_request_id = str(rewritten[0]["requestId"])
    bridge.apply_stage_summary_result(
        "todo-1",
        rewrite_request_id,
        "第一版阶段总结",
        "已调用模型重写，但返回内容未变化",
    )

    bridge.updateStageSummaryText("第二版阶段总结")

    assert bridge.stageSummaryNotice == ""


def test_stage_summary_default_rewrite_sets_default_flag() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    requested: list[dict[str, object]] = []
    rewritten: list[dict[str, object]] = []
    bridge.stageSummaryRequested.connect(lambda _todo_id, payload: requested.append(payload))
    bridge.stageSummaryRewriteRequested.connect(lambda _todo_id, payload: rewritten.append(payload))

    bridge.toggleStageSummary()
    request_id = str(requested[0]["requestId"])
    bridge.apply_stage_summary_result("todo-1", request_id, "第一版阶段总结")

    bridge.rewriteStageSummaryDefault()

    assert len(rewritten) == 1
    assert rewritten[0]["currentText"] == "第一版阶段总结"
    assert rewritten[0]["presetKey"] == ""
    assert rewritten[0]["instruction"] == ""
    assert rewritten[0]["defaultRewrite"] is True


def test_manual_save_upserts_conclusion_timeline_item() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    saved: list[tuple[str, dict[str, object]]] = []
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))

    bridge.updateField("conclusion_content", "已补充问题结论")
    bridge.saveTodo()

    assert bridge.timelineCount == 1
    assert bridge.timeline[0]["kind"] == "conclusion"
    assert len(saved) == 1
    assert len(saved[0][1]["timeline"]) == 1
    assert saved[0][1]["timeline"][0].kind == "conclusion"


def test_add_conclusion_emits_conclusion_command() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    saved: list[tuple[str, dict[str, object]]] = []
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))

    bridge.addTimelineEntry("最终结论", "conclusion")

    assert len(saved) == 1
    assert saved[0][1]["action"] == "save_conclusion"
    assert saved[0][1]["saveMode"] == "autosave"
    assert saved[0][1]["conclusion"].content == "最终结论"
