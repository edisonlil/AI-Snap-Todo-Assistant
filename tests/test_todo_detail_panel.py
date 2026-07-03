from __future__ import annotations

from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.todo.assist_analysis import build_assist_analysis_cache_key, build_assist_todo_payload
from aica.models import TicketSummaryFields
from aica.config import ConfigManager
from aica.todo.detail_panel import (
    TodoDetailPanel,
    _AssistTroubleshootingWindow,
    _TimelineDetailWindow,
    _project_status_detail,
    _render_timeline_markdown_html,
    _resolve_neighbor_panel_x,
    _StageSummaryWindow,
    _TodoDetailBridge,
)
from aica.todo.models import TimelineAttachment, TimelineEvent, TodoConclusion, TodoItem, TodoProjectLink


def _build_bridge(attachment_root: Path, *, conclusion_only_mode: bool = False) -> _TodoDetailBridge:
    config_manager = SimpleNamespace(
        load=lambda: SimpleNamespace(
            show_todo_sync_status=True,
            enable_timeline_polish=True,
            todo_detail_conclusion_only_mode=conclusion_only_mode,
        )
    )
    return _TodoDetailBridge(
        attachment_root=attachment_root,
        environment_access_service=SimpleNamespace(
            list_project_environments=lambda _project_id: [],
            list_effective_environments=lambda _project_id: [],
        ),
        config_manager=config_manager,
    )


class _DownloadClient:
    def __init__(self) -> None:
        self.downloads: list[tuple[str, Path]] = []

    def download_workbench_file(self, file_url: str, target_path: str | Path) -> Path:
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"remote-file")
        self.downloads.append((file_url, target))
        return target


def _build_panel(monkeypatch) -> TodoDetailPanel:
    monkeypatch.setattr(
        "aica.todo.detail_panel.SQLiteProjectEnvironmentRepository",
        lambda: SimpleNamespace(
            list_project_environments=lambda _project_id: [],
            list_effective_environments=lambda _project_id: [],
            get_access_entry=lambda _entry_id: None,
        ),
    )
    return TodoDetailPanel()


def _notification_messages(bridge: _TodoDetailBridge) -> list[str]:
    return [str(item["message"]) for item in bridge.notificationBridge.notifications]


def test_detail_panel_defers_auxiliary_window_creation(monkeypatch) -> None:
    panel = _build_panel(monkeypatch)

    assert panel._stage_summary_window is None  # noqa: SLF001
    assert panel._timeline_detail_window is None  # noqa: SLF001
    assert panel._assist_troubleshooting_window is None  # noqa: SLF001


def test_timeline_draft_text_update_does_not_emit_draft_changed(tmp_path: Path) -> None:
    bridge = _build_bridge(tmp_path)
    signal_count = 0

    def _record_signal() -> None:
        nonlocal signal_count
        signal_count += 1

    bridge.timelineDraftChanged.connect(_record_signal)

    bridge.updateTimelineDraftText("正在输入中文")

    assert bridge.timelineDraftText == "正在输入中文"
    assert signal_count == 0


def test_todo_detail_bridge_reads_conclusion_only_mode_from_config(tmp_path: Path) -> None:
    bridge = _build_bridge(tmp_path, conclusion_only_mode=True)

    assert bridge.conclusionOnlyMode is True


def test_update_conclusion_content_preserves_editing_newline() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    bridge.updateField("conclusion_content", "第一行\n")

    assert bridge.conclusionContent == "第一行\n"


def test_update_current_summary_preserves_editing_newline() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    bridge.updateField("current_summary", "现状第一行\n")

    assert bridge.currentSummary == "现状第一行\n"


def test_attachment_payload_does_not_expose_docx_as_image_source() -> None:
    payload = _TodoDetailBridge._attachment_to_dict(
        TimelineAttachment(
            id="attachment-1",
            name="需求文档.docx",
            path="C:/Users/ediso/.aica/todo_attachments/todo/event/需求文档.docx",
            size_bytes=123,
        )
    )

    assert payload["kind"] == "file"
    assert payload["isImage"] is False
    assert payload["isPreviewable"] is False
    assert payload["fileUrl"] == ""
    assert payload["downloadSource"] == "C:/Users/ediso/.aica/todo_attachments/todo/event/需求文档.docx"


def test_remote_image_attachment_does_not_expose_relative_download_url_as_file_url() -> None:
    payload = _TodoDetailBridge._attachment_to_dict(
        TimelineAttachment(
            id="attachment-1",
            name="截图.png",
            path="/api/files/978/download",
            size_bytes=123,
        )
    )

    assert payload["kind"] == "image"
    assert payload["isImage"] is True
    assert payload["fileUrl"] == ""
    assert payload["downloadSource"] == "/api/files/978/download"


def test_remote_attachment_downloads_lazily_and_caches_path(tmp_path: Path) -> None:
    client = _DownloadClient()
    bridge = _TodoDetailBridge(
        attachment_root=tmp_path,
        environment_access_service=SimpleNamespace(
            list_project_environments=lambda _project_id: [],
            list_effective_environments=lambda _project_id: [],
        ),
        config_manager=SimpleNamespace(load=lambda: SimpleNamespace(server=SimpleNamespace())),
        server_client_factory=lambda _server: client,
    )
    todo = _build_todo()
    todo.timeline = [
        TimelineEvent(
            id="event-1",
            attachments=[
                TimelineAttachment(
                    id="attachment-1",
                    name="测试红头模板.docx",
                    path="/api/files/legacy/download",
                    file_object_id="file-123",
                )
            ],
        )
    ]
    saved_payloads: list[object] = []
    bridge.saveRequested.connect(lambda _todo_id, payload: saved_payloads.append(payload))
    bridge.set_todo(todo)

    local_path = bridge._ensure_local_attachment_path("file-123")  # noqa: SLF001
    cached_path = bridge._ensure_local_attachment_path("file-123")  # noqa: SLF001

    assert local_path is not None
    assert local_path == tmp_path / "todo-1" / "event-1" / "测试红头模板.docx"
    assert local_path.read_bytes() == b"remote-file"
    assert cached_path == local_path
    assert client.downloads == [("file-123", local_path)]
    assert bridge.timeline[0]["attachments"][0]["fileObjectId"] == "file-123"
    assert bridge.timeline[0]["attachments"][0]["downloadSource"] == "file-123"
    assert bridge.timeline[0]["attachments"][0]["path"] == str(local_path)
    assert saved_payloads


def _build_todo(todo_id: str = "todo-1") -> TodoItem:
    return TodoItem(
        id=todo_id,
        title="测试待办",
        current_summary="当前摘要",
        summary_fields=TicketSummaryFields(),
        conclusion=TodoConclusion(),
        timeline=[],
    )


def _with_project_product_lines(todo: TodoItem, product_line: str) -> TodoItem:
    todo.project_link = TodoProjectLink(
        todo_id=todo.id,
        project_id="project-1",
        match_status="matched",
        project_snapshot={"product_line": product_line},
    )
    return todo


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


def test_current_summary_attachments_are_saved_separately(monkeypatch) -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    monkeypatch.setattr(
        bridge,
        "_copy_attachment",
        lambda file_path, event_id: {
            "id": "summary-1",
            "name": Path(file_path).name,
            "path": f"/{event_id}/{Path(file_path).name}",
            "sizeBytes": 9,
            "isImage": False,
            "isVideo": False,
            "isPreviewable": False,
            "fileUrl": "",
        },
    )

    bridge.attach_files_to_current_summary(["evidence.txt"])

    payload = bridge._build_payload()  # noqa: SLF001

    assert bridge.currentSummaryAttachmentCount == 1
    assert payload is not None
    assert [item.name for item in payload["current_summary_attachments"]] == ["evidence.txt"]
    assert payload["timeline"] == []
    assert payload["conclusion"].attachments == []


def test_remove_current_summary_attachment_updates_only_summary_attachments(monkeypatch) -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())
    bridge._current_summary_attachments = [  # noqa: SLF001
        {
            "id": "summary-1",
            "name": "evidence.txt",
            "path": "/__current_summary__/evidence.txt",
            "sizeBytes": 9,
            "isImage": False,
            "isVideo": False,
            "isPreviewable": False,
            "fileUrl": "",
        }
    ]
    removed_paths: list[str] = []
    monkeypatch.setattr(bridge, "_remove_attachment_file", lambda file_path: removed_paths.append(file_path))

    bridge.removeCurrentSummaryAttachment("summary-1")

    assert bridge.currentSummaryAttachmentCount == 0
    assert bridge.timelineCount == 0
    assert removed_paths == ["/__current_summary__/evidence.txt"]


def test_open_current_summary_attachment_folder_falls_back_to_managed_directory(tmp_path: Path, monkeypatch) -> None:
    bridge = _build_bridge(tmp_path)
    todo = _build_todo()
    todo.current_summary_attachments = [
        TimelineAttachment(
            id="summary-1",
            name="evidence.txt",
            path="/api/files/file-123/download",
            file_object_id="file-123",
        )
    ]
    bridge.set_todo(todo)

    opened_paths: list[str] = []

    def _capture_open_url(url) -> bool:
        local_path = url.toLocalFile() if hasattr(url, "toLocalFile") else ""
        opened_paths.append(local_path or url.toString())
        return True

    monkeypatch.setattr("aica.todo.detail_panel.QDesktopServices.openUrl", _capture_open_url)

    bridge.openCurrentSummaryAttachmentFolder()

    expected_dir = tmp_path / todo.id / "__current_summary__"
    assert expected_dir.is_dir()
    assert opened_paths == [str(expected_dir)]


def test_detail_bridge_no_longer_exposes_manual_plan_export() -> None:
    bridge = _build_bridge(Path("unused"))

    assert not hasattr(bridge, "exportPlan")
    assert not hasattr(bridge, "exportPlanRequested")


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
    assert bridge.timeline[0]["content"] == bridge.conclusionContent
    assert bridge.timeline[0]["attachmentCount"] == 2
    assert [item["name"] for item in bridge.timeline[0]["attachments"]] == ["existing.txt", "report.txt"]
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


def test_detail_save_preserves_existing_ach_fields() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.summary_fields = TicketSummaryFields(
        ach_no="ACH-2026-001",
        ach_filled_at="2026-05-26T10:00:00",
        ticket_version="release_dc_v7",
    )
    bridge.set_todo(todo)

    payload = bridge._build_payload()  # noqa: SLF001
    summary_fields = payload["summary_fields"]

    assert summary_fields["ach_no"] == "ACH-2026-001"
    assert summary_fields["ach_filled_at"] == "2026-05-26T10:00:00"
    assert summary_fields["ticket_version"] == "release_dc_v7"


def test_detail_save_preserves_existing_customer_environment_fields() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.summary_fields = TicketSummaryFields(
        customer_environment_code="env-prod",
        customer_environment_value="生产环境",
        ticket_version="release_dc_v7",
    )
    bridge.set_todo(todo)

    payload = bridge._build_payload()  # noqa: SLF001
    summary_fields = payload["summary_fields"]

    assert summary_fields["customer_environment_code"] == "env-prod"
    assert summary_fields["customer_environment_value"] == "生产环境"


def test_todo_detail_issue_product_field_is_read_only() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TodoDetailPanel.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "import QtQuick.Controls" in qml_text
    assert "id: issueProductField" in qml_text
    assert "id: issueProductEdit" in qml_text
    assert "readonly property var detailBridge" in qml_text
    assert 'text: "问题所属产品"' in qml_text
    assert "issueProductEdit.text = todoDetailBridge.issueProduct" in qml_text
    assert "readOnly: true" in qml_text
    assert "selectByMouse: true" in qml_text
    assert "id: productLineField" not in qml_text
    assert "id: productLineEdit" not in qml_text
    assert "id: productLineFallbackEdit" not in qml_text


def test_todo_detail_summary_panel_uses_theme_field_background() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TodoDetailPanel.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert 'text: "当前描述"' in qml_text
    assert "color: root.fieldBg" in qml_text


def test_todo_detail_summary_attachments_use_count_and_folder_entry() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TodoDetailPanel.qml"
    qml_text = qml_path.read_text(encoding="utf-8")
    summary_actions = qml_text.split('text: "当前描述"', 1)[1].split("Column {", 1)[0]

    assert 'todoDetailBridge.currentSummaryAttachmentCount > 0' in qml_text
    assert '"添加附件（" + todoDetailBridge.currentSummaryAttachmentCount + "）"' in qml_text
    attachment_toggle_text = 'text: root.currentSummaryAttachmentManagerExpanded ? "收起列表" : "附件管理"'
    assert attachment_toggle_text in qml_text
    assert summary_actions.index(attachment_toggle_text) < summary_actions.index('text: "粘贴截图"')
    assert "property bool currentSummaryAttachmentManagerExpanded: false" in qml_text
    assert "function toggleCurrentSummaryAttachmentManager()" in qml_text
    assert "onClicked: root.toggleCurrentSummaryAttachmentManager()" in qml_text
    assert 'text: "打开目录"' in qml_text
    assert '"收起列表"' in attachment_toggle_text
    assert "visible: root.currentSummaryAttachmentManagerExpanded" in qml_text
    assert "onClicked: todoDetailBridge.openCurrentSummaryAttachmentFolder()" in qml_text
    assert "height: modelData.isImage ? 74 : 42" in qml_text
    assert "source: modelData.isImage ? modelData.fileUrl : \"\"" in qml_text
    assert 'text: "预览"' in qml_text


def test_todo_detail_external_id_visibility_follows_sync_status_toggle() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TodoDetailPanel.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert 'text: "external_id: " + todoDetailBridge.externalId' in qml_text
    assert "visible: todoDetailBridge.showSyncStatus && todoDetailBridge.hasExternalId" in qml_text


def test_todo_detail_conclusion_only_mode_qml_keeps_summary_and_assist_actions() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TodoDetailPanel.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "readonly property bool conclusionOnlyMode: detailBridge ? detailBridge.conclusionOnlyMode : false" in qml_text
    assert 'text: root.conclusionOnlyMode ? "问题结论" : "时间线历史"' in qml_text
    assert 'text: todoDetailBridge.stageSummaryVisible ? "收起阶段总结" : "阶段总结"' in qml_text
    assert 'text: "辅助排查"' in qml_text
    assert "visible: !root.conclusionOnlyMode && todoDetailBridge.timelineExpanded" in qml_text
    assert 'text: "输入问题结论"' in qml_text
    assert "property bool conclusionAttachmentManagerExpanded: false" in qml_text
    assert 'text: root.conclusionAttachmentManagerExpanded ? "收起列表" : "附件管理"' in qml_text
    assert "onClicked: root.toggleConclusionAttachmentManager()" in qml_text
    assert "todoDetailBridge.requestAttachmentSelection(root.conclusionAttachmentTarget)" in qml_text
    assert "onClicked: todoDetailBridge.openConclusionAttachmentFolder()" in qml_text
    assert 'text: "复制"' in qml_text
    assert 'text: "复制名"' in qml_text
    assert 'text: "复制路径"' in qml_text
    assert 'text: "打开"' in qml_text
    assert 'text: "下载"' in qml_text
    assert "model: todoDetailBridge.currentSummaryAttachments" in qml_text
    assert "todoDetailBridge.removeCurrentSummaryAttachment(modelData.id)" in qml_text
    assert '"当前描述附件 " + todoDetailBridge.currentSummaryAttachmentCount' not in qml_text


def test_todo_detail_product_line_does_not_follow_project_snapshot() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.summary_fields = TicketSummaryFields(product_line="手工产品线")
    bridge.set_todo(_with_project_product_lines(todo, "文档中台, 协作套件"))

    payload = bridge._build_payload()  # noqa: SLF001

    assert bridge.productLine == "手工产品线"
    assert payload["summary_fields"]["product_line"] == "手工产品线"


def test_todo_detail_empty_product_line_does_not_default_from_project_snapshot() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_with_project_product_lines(_build_todo(), "文档中台, 协作套件"))

    payload = bridge._build_payload()  # noqa: SLF001

    assert bridge.productLine == "未知"
    assert payload["summary_fields"]["product_line"] == "未知"


def test_manual_project_link_detail_prefers_project_snapshot() -> None:
    todo = _build_todo()
    todo.project_link = TodoProjectLink(
        todo_id=todo.id,
        project_id="project-1",
        match_status="manual",
        project_snapshot={"project_name": "企业知识库重构", "task_order_no": "ACH-20240630-01"},
    )

    assert _project_status_detail(todo) == "企业知识库重构 ACH-20240630-01"


def test_manual_project_link_detail_falls_back_when_snapshot_missing() -> None:
    todo = _build_todo()
    todo.project_link = TodoProjectLink(
        todo_id=todo.id,
        project_id="project-1",
        match_status="manual",
    )

    assert _project_status_detail(todo) == "当前待办使用了手动项目关联结果。"


def test_todo_detail_save_preserves_issue_product_field() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.summary_fields = TicketSummaryFields(issue_product="产品A/模块B/功能C")
    bridge.set_todo(todo)

    payload = bridge._build_payload()  # noqa: SLF001
    summary_fields = payload["summary_fields"]

    assert bridge.issueProduct == "产品A/模块B/功能C"
    assert summary_fields["issue_product"] == "产品A/模块B/功能C"


def test_log_analysis_submission_pushes_notification() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    bridge.addTimelineEntry("request_id=req-9", "log_analysis")

    assert bridge.timelineCount == 1
    assert bridge.timeline[0]["type"] == "log_analysis_command"
    assert _notification_messages(bridge)[-1] == "已提交日志分析任务，后台排查中"


def test_assist_analysis_result_exposes_case_results_without_mock_fallback() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())
    bridge._assist_analysis_pending_request_id = "req-1"  # noqa: SLF001

    bridge.apply_assist_analysis_result(
        "todo-1",
        "req-1",
        {
            "summary": "分析完成",
            "caseResults": {
                "status": "success",
                "countLabel": "检索 2 条结果",
                "items": [
                    {
                        "title": "弱相关案例",
                        "desc": "低分案例描述",
                        "text": "低分引用文本",
                        "detailUrl": "https://www.kdocs.cn/l/case-low",
                        "score": 49,
                        "scoreLabel": "契合度 49",
                        "matchReason": "仅弱相关",
                    },
                    {
                        "title": "移动端鉴权 token 未透传",
                        "desc": "历史案例描述",
                        "text": "引用文本",
                        "detailUrl": "https://www.kdocs.cn/l/case1",
                        "score": 86,
                        "scoreLabel": "契合度 86",
                        "matchReason": "现象均包含移动端鉴权 token",
                    }
                ],
            },
        },
    )

    results = bridge.assistCaseResults
    assert results["countLabel"] == "检索 1 条结果"
    assert len(results["items"]) == 1
    assert results["items"][0]["title"] == "移动端鉴权 token 未透传"
    assert results["items"][0]["detailUrl"] == "https://www.kdocs.cn/l/case1"
    assert results["items"][0]["score"] == 86
    assert results["items"][0]["scoreLabel"] == "契合度 86"
    assert results["items"][0]["matchReason"] == "现象均包含移动端鉴权 token"


def test_assist_analysis_empty_case_results_stay_empty() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())
    bridge._assist_analysis_pending_request_id = "req-1"  # noqa: SLF001

    bridge.apply_assist_analysis_result(
        "todo-1",
        "req-1",
        {
            "summary": "分析完成",
            "caseResults": {"status": "empty", "items": []},
        },
    )

    results = bridge.assistCaseResults
    assert results["countLabel"] == "暂无案例"
    assert results["items"] == []
    assert results["emptyText"] == "暂无案例"


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


def test_timeline_draft_state_is_scoped_per_todo_and_restored_on_switch(monkeypatch) -> None:
    bridge = _build_bridge(Path("unused"))

    def _fake_copy_attachment(file_path: str, event_id: str) -> dict[str, object]:
        return {
            "id": f"{event_id}-{Path(file_path).stem}",
            "name": Path(file_path).name,
            "path": f"/{bridge.todoId}/{event_id}/{Path(file_path).name}",
            "sizeBytes": 8,
            "isImage": False,
            "isVideo": False,
            "isPreviewable": False,
            "fileUrl": "",
        }

    monkeypatch.setattr(bridge, "_copy_attachment", _fake_copy_attachment)

    first_todo = _build_todo("todo-1")
    second_todo = _build_todo("todo-2")

    bridge.set_todo(first_todo)
    bridge.updateTimelineDraftText("draft for first todo")
    bridge.setTimelineDraftEntryType("conclusion")
    bridge.attach_files_to_draft_timeline(["first.txt"])

    assert bridge.timelineDraftText == "draft for first todo"
    assert bridge.timelineDraftEntryType == "conclusion"
    assert bridge.timelineDraftEntryTypeSelected is True
    assert bridge.draftTimelineAttachmentCount == 1

    bridge.set_todo(second_todo)

    assert bridge.timelineDraftText == ""
    assert bridge.timelineDraftEntryType == "follow_up"
    assert bridge.timelineDraftEntryTypeSelected is False
    assert bridge.draftTimelineAttachmentCount == 0

    bridge.set_todo(first_todo)

    assert bridge.timelineDraftText == "draft for first todo"
    assert bridge.timelineDraftEntryType == "conclusion"
    assert bridge.timelineDraftEntryTypeSelected is True
    assert bridge.draftTimelineAttachmentCount == 1
    assert bridge.draftTimelineAttachments[0]["path"] == "/todo-1/__draft_timeline__/first.txt"


def test_submitting_timeline_entry_clears_cached_draft_state(monkeypatch) -> None:
    bridge = _build_bridge(Path("unused"))

    monkeypatch.setattr(
        bridge,
        "_copy_attachment",
        lambda file_path, event_id: {
            "id": f"{event_id}-{Path(file_path).stem}",
            "name": Path(file_path).name,
            "path": f"/{bridge.todoId}/{event_id}/{Path(file_path).name}",
            "sizeBytes": 10,
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
            "id": f"{event_id}-final",
            "name": Path(file_path).name,
            "path": f"/{bridge.todoId}/{event_id}/{Path(file_path).name}",
            "sizeBytes": 10,
            "isImage": False,
            "isVideo": False,
            "isPreviewable": False,
            "fileUrl": "",
        },
    )

    first_todo = _build_todo("todo-1")
    second_todo = _build_todo("todo-2")

    bridge.set_todo(first_todo)
    bridge.updateTimelineDraftText("ready to submit")
    bridge.setTimelineDraftEntryType("follow_up")
    bridge.attach_files_to_draft_timeline(["submit.txt"])

    bridge.addTimelineEntry(bridge.timelineDraftText, bridge.timelineDraftEntryType)

    assert bridge.timelineDraftText == ""
    assert bridge.timelineDraftEntryType == "follow_up"
    assert bridge.timelineDraftEntryTypeSelected is False
    assert bridge.draftTimelineAttachmentCount == 0

    bridge.set_todo(second_todo)
    bridge.set_todo(first_todo)

    assert bridge.timelineDraftText == ""
    assert bridge.timelineDraftEntryType == "follow_up"
    assert bridge.timelineDraftEntryTypeSelected is False
    assert bridge.draftTimelineAttachmentCount == 0


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


def test_toggle_assist_troubleshooting_requests_analysis_once() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())
    requested: list[tuple[str, object]] = []
    bridge.assistAnalysisRequested.connect(lambda todo_id, payload: requested.append((todo_id, payload)))

    bridge.toggleAssistTroubleshooting()

    assert bridge.assistTroubleshootingVisible is True
    assert bridge.assistAnalysisBusy is True
    assert len(requested) == 1
    todo_id, payload = requested[0]
    assert todo_id == "todo-1"
    assert isinstance(payload, dict)
    assert payload["requestId"]
    assert payload["todoPayload"]["title"]

    bridge.closeAssistTroubleshooting()
    bridge.toggleAssistTroubleshooting()

    assert len(requested) == 1


def test_open_detail_prewarm_requests_assist_analysis_when_cache_missing() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    bridge.set_todo(todo)
    requested: list[tuple[str, object]] = []
    bridge.assistAnalysisRequested.connect(lambda todo_id, payload: requested.append((todo_id, payload)))

    bridge.prewarmAssistAnalysisIfNeeded()

    assert bridge.assistTroubleshootingVisible is False
    assert bridge.assistAnalysisBusy is False
    assert len(requested) == 1
    assert requested[0][0] == "todo-1"
    assert requested[0][1]["cacheKey"] == build_assist_analysis_cache_key(todo.id, build_assist_todo_payload(todo))


def test_open_detail_prewarm_skips_when_assist_cache_exists() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    bridge.set_todo(todo)
    cache_key = build_assist_analysis_cache_key(todo.id, build_assist_todo_payload(todo))
    bridge.cache_assist_analysis_result(
        "todo-1",
        {
            "phase": "initial",
            "shouldUpdate": True,
            "cacheKey": cache_key,
            "summary": "已有缓存建议",
            "caseResults": {"status": "empty", "items": []},
        },
    )
    requested: list[tuple[str, object]] = []
    bridge.assistAnalysisRequested.connect(lambda todo_id, payload: requested.append((todo_id, payload)))

    bridge.prewarmAssistAnalysisIfNeeded()

    assert requested == []
    assert bridge.assistAnalysisSummary == "已有缓存建议"


def test_click_assist_waits_for_existing_open_detail_prewarm_request() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    bridge.set_todo(todo)
    requested: list[tuple[str, object]] = []
    bridge.assistAnalysisRequested.connect(lambda todo_id, payload: requested.append((todo_id, payload)))

    bridge.prewarmAssistAnalysisIfNeeded()
    prewarm_request_id = str(requested[0][1]["requestId"])
    bridge.toggleAssistTroubleshooting()

    assert len(requested) == 1
    assert bridge.assistTroubleshootingVisible is True
    assert bridge.assistAnalysisBusy is True
    assert bridge.apply_assist_analysis_result(
        "todo-1",
        prewarm_request_id,
        {
            "summary": "预热请求返回的建议",
            "caseResults": {"status": "empty", "items": []},
        },
    ) is True
    assert bridge.assistAnalysisBusy is False
    assert bridge.assistAnalysisSummary == "预热请求返回的建议"


def test_toggle_assist_troubleshooting_uses_prewarmed_cache() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    bridge.set_todo(todo)
    requested: list[tuple[str, object]] = []
    bridge.assistAnalysisRequested.connect(lambda todo_id, payload: requested.append((todo_id, payload)))
    cache_key = build_assist_analysis_cache_key(todo.id, build_assist_todo_payload(todo))

    assert bridge.cache_assist_analysis_result(
        "todo-1",
        {
            "phase": "initial",
            "shouldUpdate": True,
            "cacheKey": cache_key,
            "summary": "预热完成的第一版建议",
            "caseResults": {"status": "empty", "items": []},
        },
    ) is True

    bridge.toggleAssistTroubleshooting()

    assert bridge.assistTroubleshootingVisible is True
    assert bridge.assistAnalysisBusy is False
    assert bridge.assistAnalysisSummary == "预热完成的第一版建议"
    assert requested == []


def test_review_cache_result_updates_only_when_marked_useful() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    bridge.set_todo(todo)
    cache_key = build_assist_analysis_cache_key(todo.id, build_assist_todo_payload(todo))
    bridge.cache_assist_analysis_result(
        "todo-1",
        {
            "phase": "initial",
            "shouldUpdate": True,
            "cacheKey": cache_key,
            "summary": "第一版建议",
            "caseResults": {"status": "empty", "items": []},
        },
    )

    assert bridge.cache_assist_analysis_result(
        "todo-1",
        {
            "phase": "review",
            "shouldUpdate": False,
            "cacheKey": cache_key,
            "summary": "无增益第二版",
            "caseResults": {"status": "empty", "items": []},
        },
    ) is False
    assert bridge.assistAnalysisSummary == "第一版建议"

    assert bridge.cache_assist_analysis_result(
        "todo-1",
        {
            "phase": "review",
            "shouldUpdate": True,
            "cacheKey": cache_key,
            "summary": "有增益第二版",
            "caseResults": {"status": "empty", "items": []},
        },
    ) is True
    assert bridge.assistAnalysisSummary == "有增益第二版"


def test_apply_assist_analysis_result_updates_structured_state() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())
    requested: list[dict[str, object]] = []
    bridge.assistAnalysisRequested.connect(lambda _todo_id, payload: requested.append(payload))
    bridge.toggleAssistTroubleshooting()
    request_id = str(requested[0]["requestId"])

    assert bridge.apply_assist_analysis_result(
        "todo-1",
        request_id,
        {
            "summary": "已有 demo 对比线索，但仍缺少生产请求参数和日志。",
            "informationStatus": {
                "recognized": "已识别到环境对比线索",
                "checkedDirections": [
                    {"title": "demo 已验证", "evidence": "时间线记录 demo 正常"}
                ],
            },
            "missingSupplement": {
                "directions": [
                    {"title": "生产请求参数", "reason": "用于核对参数差异"}
                ],
            },
            "upgradeSuggestion": {
                "decision": "暂不建议升级",
                "reason": "证据链不完整。",
            },
        },
    ) is True

    assert bridge.assistAnalysisBusy is False
    assert bridge.assistAnalysisSummary == "已有 demo 对比线索，但仍缺少生产请求参数和日志。"
    assert bridge.assistInformationStatus["recognized"] == "已识别到环境对比线索"
    assert bridge.assistInformationStatus["checkedDirections"][0]["title"] == "demo 已验证"
    assert bridge.assistMissingSupplement["directions"][0]["reason"] == "用于核对参数差异"
    assert bridge.assistUpgradeSuggestion["reason"] == "证据链不完整。"


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
        "aica.todo.detail_panel._screen_for_point",
        lambda _point: "screen-token",
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_available_geometry",
        lambda _screen: available,
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_neighbor_panel_x",
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
        "aica.todo.detail_panel._screen_for_point",
        lambda _point: "screen-token",
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_available_geometry",
        lambda _screen: available,
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_neighbor_panel_x",
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
        "aica.todo.detail_panel._screen_for_point",
        lambda _point: "screen-token",
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_available_geometry",
        lambda _screen: available,
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_neighbor_panel_x",
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


def test_stage_summary_window_screen_change_restores_synced_size(monkeypatch) -> None:
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
        lambda: SimpleNamespace(property=lambda name: 510 if name == "preferredHeight" else None),
        raising=False,
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._screen_for_point",
        lambda _point: "screen-token",
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_available_geometry",
        lambda _screen: available,
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_neighbor_panel_x",
        lambda *_args, **_kwargs: 700,
    )
    monkeypatch.setattr(window, "_move_within_screen", lambda *_args, **_kwargs: None)

    window.show_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)
    window.resize(900, 700)
    window._handle_screen_changed(None)  # noqa: SLF001

    assert window.width() == 443
    assert window.height() == 510


def test_toggle_assist_troubleshooting_does_not_save_detail_payload() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    saved: list[tuple[str, object]] = []
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))

    bridge.toggleAssistTroubleshooting()

    assert bridge.assistTroubleshootingVisible is True
    assert saved == []

    bridge.closeAssistTroubleshooting()

    assert bridge.assistTroubleshootingVisible is False
    assert saved == []


def test_assist_troubleshooting_window_sync_uses_default_width_and_preferred_height(monkeypatch) -> None:
    bridge = _build_bridge(Path("unused"))
    window = _AssistTroubleshootingWindow(
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
        lambda: SimpleNamespace(property=lambda name: 470 if name == "preferredHeight" else None),
        raising=False,
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._screen_for_point",
        lambda _point: "screen-token",
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_available_geometry",
        lambda _screen: available,
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_neighbor_panel_x",
        lambda *_args, **_kwargs: 710,
    )
    monkeypatch.setattr(
        window,
        "_move_within_screen",
        lambda x, y, screen: moved.append((x, y, screen)),
    )

    window.show_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)

    assert window.width() == 443
    assert window.height() == 470
    assert moved == [(710, 204, "screen-token")]


def test_assist_troubleshooting_window_manual_resize_and_drag_persist_until_hidden(monkeypatch) -> None:
    bridge = _build_bridge(Path("unused"))
    window = _AssistTroubleshootingWindow(
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
        lambda: SimpleNamespace(property=lambda name: 460 if name == "preferredHeight" else None),
        raising=False,
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._screen_for_point",
        lambda _point: "screen-token",
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_available_geometry",
        lambda _screen: available,
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_neighbor_panel_x",
        lambda *_args, **_kwargs: 640,
    )

    window.show_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)
    window.resize(620, 540)
    window.setPosition(730, 280)
    window._manual_size_override = True  # noqa: SLF001
    window._manual_position_override = True  # noqa: SLF001
    window.update_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)

    assert window.width() == 620
    assert window.height() == 540
    assert window.x() == 730
    assert window.y() == 280

    window.hide()
    window.show_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)

    assert window.width() == 443
    assert window.height() == 460
    assert window.x() == 640
    assert window.y() == 204


def test_timeline_detail_window_keeps_maximized_state_on_update(monkeypatch) -> None:
    bridge = _build_bridge(Path("unused"))
    window = _TimelineDetailWindow(
        bridge,
        panel_width=860,
        panel_height=632,
        screen_margin=20,
    )
    available = _FakeAvailableGeometry(height=880)
    anchor = _FakeAnchorWindow()
    maximize_calls: list[str] = []
    resize_calls: list[tuple[int, int]] = []

    monkeypatch.setattr(
        window,
        "rootObject",
        lambda: SimpleNamespace(property=lambda name: 510 if name == "preferredHeight" else None),
        raising=False,
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._screen_for_point",
        lambda _point: "screen-token",
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_available_geometry",
        lambda _screen: available,
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_neighbor_panel_x",
        lambda *_args, **_kwargs: 700,
    )
    monkeypatch.setattr(window, "_move_within_screen", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(window, "showMaximized", lambda: maximize_calls.append("show"))
    monkeypatch.setattr(window, "showNormal", lambda: maximize_calls.append("normal"))
    monkeypatch.setattr(window, "raise_", lambda: None)
    monkeypatch.setattr(window, "requestActivate", lambda: None)
    monkeypatch.setattr(window, "resize", lambda w, h: resize_calls.append((w, h)))
    monkeypatch.setattr(window, "_is_window_maximized", lambda: True)

    window.show_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)
    window.update_near(anchor, anchor_width=396, anchor_gap=18, top_offset=84)
    window._handle_screen_changed(None)  # noqa: SLF001

    assert maximize_calls == ["show"]
    assert resize_calls == []


def test_detail_panel_screen_change_restores_default_size(monkeypatch) -> None:
    panel = _build_panel(monkeypatch)

    panel.resize(900, 900)
    panel._handle_screen_changed(None)  # noqa: SLF001

    assert panel.width() == 396
    assert panel.height() == 724


def test_closing_detail_panel_hides_assist_troubleshooting(monkeypatch) -> None:
    panel = _build_panel(monkeypatch)
    panel.show()
    panel._bridge._assist_troubleshooting_visible = True  # noqa: SLF001
    assist_window = panel._ensure_assist_troubleshooting_window()  # noqa: SLF001
    panel._assist_troubleshooting_window_visible = True  # noqa: SLF001

    hide_calls: list[str] = []
    monkeypatch.setattr(
        assist_window,
        "hide",
        lambda: hide_calls.append("assist"),
    )

    panel._close_panel()

    assert panel._bridge.assistTroubleshootingVisible is False
    assert panel._assist_troubleshooting_window_visible is False
    assert hide_calls


def test_hiding_detail_panel_hides_auxiliary_windows(monkeypatch) -> None:
    panel = _build_panel(monkeypatch)
    panel.show()
    stage_window = panel._ensure_stage_summary_window()  # noqa: SLF001
    assist_window = panel._ensure_assist_troubleshooting_window()  # noqa: SLF001
    panel._stage_summary_window_visible = True  # noqa: SLF001
    panel._assist_troubleshooting_window_visible = True  # noqa: SLF001

    hide_calls: list[str] = []
    monkeypatch.setattr(stage_window, "hide", lambda: hide_calls.append("stage"))
    monkeypatch.setattr(assist_window, "hide", lambda: hide_calls.append("assist"))

    panel.hide()

    assert panel._stage_summary_window_visible is False
    assert panel._assist_troubleshooting_window_visible is False
    assert hide_calls == ["stage", "assist"]


def test_show_todo_restores_cached_timeline_draft_after_panel_close(monkeypatch) -> None:
    panel = _build_panel(monkeypatch)
    first_todo = _build_todo("todo-1")
    second_todo = _build_todo("todo-2")

    monkeypatch.setattr(
        panel._bridge,
        "_copy_attachment",
        lambda file_path, event_id: {
            "id": f"{event_id}-{Path(file_path).stem}",
            "name": Path(file_path).name,
            "path": f"/{panel._bridge.todoId}/{event_id}/{Path(file_path).name}",
            "sizeBytes": 9,
            "isImage": False,
            "isVideo": False,
            "isPreviewable": False,
            "fileUrl": "",
        },
    )

    panel.show_todo(first_todo)
    panel._bridge.updateTimelineDraftText("keep me")
    panel._bridge.setTimelineDraftEntryType("log_analysis")
    panel._bridge.attach_files_to_draft_timeline(["draft.txt"])

    panel._close_panel()
    panel.show_todo(first_todo)

    assert panel._bridge.timelineDraftText == "keep me"
    assert panel._bridge.timelineDraftEntryType == "log_analysis"
    assert panel._bridge.timelineDraftEntryTypeSelected is True
    assert panel._bridge.draftTimelineAttachmentCount == 1

    panel.show_todo(second_todo)

    assert panel._bridge.timelineDraftText == ""
    assert panel._bridge.timelineDraftEntryType == "follow_up"
    assert panel._bridge.timelineDraftEntryTypeSelected is False
    assert panel._bridge.draftTimelineAttachmentCount == 0


def test_show_todo_preserve_position_keeps_current_location(monkeypatch) -> None:
    panel = _build_panel(monkeypatch)
    panel.show()
    panel.setPosition(222, 333)

    reposition_calls: list[object] = []
    move_calls: list[tuple[int, int, object]] = []

    monkeypatch.setattr(
        "aica.todo.detail_panel._screen_for_point",
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
        "aica.todo.detail_panel._screen_for_point",
        lambda _point: "screen-token",
    )
    monkeypatch.setattr(
        "aica.todo.detail_panel._resolve_available_geometry",
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


def test_complete_todo_requires_conclusion() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    completed: list[str] = []
    bridge.completeRequested.connect(completed.append)

    bridge.completeTodo()

    assert completed == []
    assert "请先填写问题结论" in _notification_messages(bridge)


def test_complete_todo_allows_filled_conclusion() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    completed: list[str] = []
    bridge.completeRequested.connect(completed.append)

    bridge.updateField("conclusion_content", "已有问题结论")
    bridge.completeTodo()

    assert completed == ["todo-1"]


def test_delete_conclusion_card_disables_completion() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    saved: list[tuple[str, dict[str, object]]] = []
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))

    bridge.addTimelineEntry("已有问题结论", "conclusion")
    conclusion_id = str(bridge.timeline[0]["id"])
    saved.clear()

    bridge.deleteTimelineEntry(conclusion_id)

    assert bridge.canCompleteTodo is False
    assert bridge.conclusionContent == ""
    assert all(item["kind"] != "conclusion" for item in bridge.timeline)
    assert saved[0][1]["conclusion"].content == ""
    assert all(event.kind != "conclusion" for event in saved[0][1]["timeline"])


def test_reopened_todo_restores_hidden_conclusion_card() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.conclusion = TodoConclusion(content="旧问题结论", updated_at="2026-06-14T11:12:00")
    todo.timeline = [
        TimelineEvent(
            id="follow-up-1",
            timestamp="2026-06-01T11:00:00",
            kind="manual",
            scenario="工单跟进",
            content="普通跟进",
        )
    ]

    bridge.set_todo(todo)

    assert bridge.canCompleteTodo is True
    assert bridge.timeline[0]["kind"] == "conclusion"
    assert bridge.timeline[0]["content"] == "旧问题结论"


def test_deleting_follow_up_keeps_reopened_conclusion_visible() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.conclusion = TodoConclusion(content="旧问题结论", updated_at="2026-06-14T11:12:00")
    todo.timeline = [
        TimelineEvent(
            id="follow-up-1",
            timestamp="2026-06-01T11:00:00",
            kind="manual",
            scenario="工单跟进",
            content="普通跟进",
        )
    ]
    bridge.set_todo(todo)

    bridge.deleteTimelineCard("follow-up-1")

    assert bridge.canCompleteTodo is True
    assert bridge.timelineCount == 1
    assert bridge.timeline[0]["kind"] == "conclusion"
    assert bridge.timeline[0]["content"] == "旧问题结论"


def test_todo_detail_complete_button_is_gated_by_conclusion() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TodoDetailPanel.qml"
    qml_text = qml_path.read_text(encoding="utf-8")
    complete_button = qml_text.split("id: completeButton", 1)[1].split("Row {", 1)[0]

    assert "readonly property color buttonPrimaryBg: themeTokens.buttonPrimaryBg || accent" in qml_text
    assert (
        'readonly property color buttonPrimaryBgPressed: themeTokens.buttonPrimaryBgPressed || themeTokens.accentPressed || "#151C28"'
        in qml_text
    )
    assert "enabled: todoDetailBridge.canCompleteTodo" in complete_button
    assert (
        "color: enabled ? (completeButtonMouse.pressed ? root.buttonPrimaryBgPressed : root.buttonPrimaryBg) : \"#E1E4E8\""
        in complete_button
    )
    assert "cursorShape: completeButton.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor" in complete_button
    assert "id: completeDisabledTip" in complete_button
    assert 'text: "请先填写问题结论"' in complete_button
    assert "ToolTip." not in complete_button


def test_update_conclusion_content_keeps_payload_and_hidden_timeline_synced() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())

    bridge.updateField("conclusion_content", "仅保留结论")

    payload = bridge._build_payload()  # noqa: SLF001

    assert bridge.canCompleteTodo is True
    assert bridge.conclusionContent == "仅保留结论"
    assert bridge.timelineCount == 1
    assert bridge.timeline[0]["kind"] == "conclusion"
    assert bridge.timeline[0]["content"] == "仅保留结论"
    assert payload["conclusion"].content == "仅保留结论"
    assert payload["timeline"][0].kind == "conclusion"
    assert payload["timeline"][0].content == "仅保留结论"


def test_manual_save_preserves_legacy_conclusion_timeline_item() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.conclusion = TodoConclusion()
    todo.timeline = [
        TimelineEvent(
            id="conclusion-legacy",
            timestamp="2026-04-22T10:00:00",
            kind="conclusion",
            scenario="结论更新",
            content="已有结论内容",
        )
    ]

    saved: list[tuple[str, dict[str, object]]] = []
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))

    bridge.set_todo(todo)
    bridge.saveTodo()

    assert bridge.conclusionContent == "已有结论内容"
    assert bridge.timeline[0]["content"] == "已有结论内容"
    assert len(saved) == 1
    assert saved[0][1]["conclusion"].content == "已有结论内容"
    assert saved[0][1]["timeline"][0].content == "已有结论内容"


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


def test_conclusion_attachment_updates_keep_hidden_timeline_synced(tmp_path: Path) -> None:
    bridge = _build_bridge(tmp_path)
    bridge.set_todo(_build_todo())
    bridge.updateField("conclusion_content", "已有结论")

    source = tmp_path / "evidence.txt"
    source.write_text("attachment", encoding="utf-8")

    bridge.attach_files_to_event("__conclusion__", [str(source)])

    payload = bridge._build_payload()  # noqa: SLF001

    assert bridge.conclusionAttachmentCount == 1
    assert bridge.timeline[0]["kind"] == "conclusion"
    assert bridge.timeline[0]["attachmentCount"] == 1
    assert payload["conclusion"].content == "已有结论"
    assert len(payload["conclusion"].attachments) == 1
    assert payload["timeline"][0].attachments[0].name == "evidence.txt"

    attachment_id = str(bridge.conclusionAttachments[0]["id"])
    bridge.removeConclusionAttachment(attachment_id)

    updated_payload = bridge._build_payload()  # noqa: SLF001

    assert bridge.conclusionAttachmentCount == 0
    assert bridge.timeline[0]["content"] == "已有结论"
    assert bridge.timeline[0]["attachmentCount"] == 0
    assert updated_payload["conclusion"].content == "已有结论"
    assert updated_payload["conclusion"].attachments == []
    assert updated_payload["timeline"][0].content == "已有结论"
    assert updated_payload["timeline"][0].attachments == []


def test_clearing_conclusion_content_preserves_conclusion_attachments(tmp_path: Path) -> None:
    bridge = _build_bridge(tmp_path)
    bridge.set_todo(_build_todo())
    bridge.updateField("conclusion_content", "已有结论")

    source = tmp_path / "evidence.txt"
    source.write_text("attachment", encoding="utf-8")
    bridge.attach_files_to_event("__conclusion__", [str(source)])

    bridge.updateField("conclusion_content", "")

    payload = bridge._build_payload()  # noqa: SLF001

    assert bridge.conclusionContent == ""
    assert bridge.conclusionAttachmentCount == 1
    assert bridge.timeline[0]["kind"] == "conclusion"
    assert bridge.timeline[0]["content"] == "结论已清空"
    assert bridge.timeline[0]["attachmentCount"] == 1
    assert payload["conclusion"].content == ""
    assert len(payload["conclusion"].attachments) == 1
    assert payload["timeline"][0].attachments[0].name == "evidence.txt"


def test_removing_conclusion_attachment_with_empty_content_keeps_remaining_attachments(tmp_path: Path) -> None:
    bridge = _build_bridge(tmp_path)
    bridge.set_todo(_build_todo())
    bridge.updateField("conclusion_content", "已有结论")

    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    bridge.attach_files_to_event("__conclusion__", [str(first), str(second)])
    bridge.updateField("conclusion_content", "")

    first_id = str(bridge.conclusionAttachments[0]["id"])
    bridge.removeConclusionAttachment(first_id)

    payload = bridge._build_payload()  # noqa: SLF001

    assert bridge.conclusionAttachmentCount == 1
    assert bridge.conclusionAttachments[0]["name"] == "second.txt"
    assert bridge.timeline[0]["attachmentCount"] == 1
    assert len(payload["conclusion"].attachments) == 1
    assert payload["conclusion"].attachments[0].name == "second.txt"


def test_timeline_detail_save_preserves_raw_summary_and_detail() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.timeline = [
        TimelineEvent(
            id="event-1",
            timestamp="2026-06-14T11:00:00",
            kind="manual",
            scenario="问题反馈",
            content="原始短内容",
        )
    ]
    saved: list[tuple[str, dict[str, object]]] = []
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))
    bridge.set_todo(todo)

    bridge.openTimelineDetail("event-1")
    bridge.updateTimelineDetailText("很长的原始记录\n\n- 包含很多细节")
    bridge.saveTimelineDetail()

    event = saved[-1][1]["timeline"][0]
    assert event.content == "原始短内容"
    assert event.payload["note_mode"] == "detail"
    assert event.payload["raw_content"] == "很长的原始记录\n\n- 包含很多细节"
    assert event.payload["summary"] == "原始短内容"
    assert event.payload["polished_detail"] == "很长的原始记录\n\n- 包含很多细节"


def test_timeline_detail_save_triggers_async_summary_request() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.timeline = [
        TimelineEvent(
            id="event-1",
            timestamp="2026-06-14T11:00:00",
            kind="manual",
            scenario="问题反馈",
            content="旧摘要",
        )
    ]
    requests: list[tuple[str, dict[str, object]]] = []
    bridge.timelineSummaryRequested.connect(lambda todo_id, payload: requests.append((todo_id, payload)))
    bridge.set_todo(todo)

    bridge.openTimelineDetail("event-1")
    bridge.updateTimelineDetailText("新的详细原文")
    bridge.saveTimelineDetail()

    assert len(requests) == 1
    assert requests[0][0] == "todo-1"
    assert requests[0][1]["eventId"] == "event-1"
    assert requests[0][1]["content"] == "新的详细原文"


def test_timeline_detail_edit_does_not_persist_without_explicit_save() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.timeline = [
        TimelineEvent(
            id="event-1",
            timestamp="2026-06-14T11:00:00",
            kind="manual",
            scenario="问题反馈",
            content="旧摘要",
            payload={
                "note_mode": "detail",
                "raw_content": "旧详情",
                "summary": "旧摘要",
                "polished_detail": "旧详情",
            },
        )
    ]
    saved: list[tuple[str, dict[str, object]]] = []
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))
    bridge.set_todo(todo)

    bridge.openTimelineDetail("event-1")
    bridge.updateTimelineDetailText("未保存的新内容")

    assert saved == []
    assert bridge.timelineDetailText == "未保存的新内容"
    assert bridge.timelineDetailSummary == "旧摘要"
    assert bridge.timeline[0]["content"] == "旧摘要"
    assert bridge.timeline[0]["payload"]["raw_content"] == "旧详情"


def test_timeline_summary_result_updates_readonly_card_content_only() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.timeline = [
        TimelineEvent(
            id="event-1",
            timestamp="2026-06-14T11:00:00",
            kind="manual",
            scenario="问题反馈",
            content="旧摘要",
            payload={
                "note_mode": "detail",
                "raw_content": "原始长文",
                "summary": "旧摘要",
                "polished_detail": "原始长文",
            },
        )
    ]
    saved: list[tuple[str, dict[str, object]]] = []
    requests: list[tuple[str, dict[str, object]]] = []
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))
    bridge.timelineSummaryRequested.connect(lambda todo_id, payload: requests.append((todo_id, payload)))
    bridge.set_todo(todo)

    bridge.requestTimelineSummary("event-1")
    request_id = str(requests[0][1]["requestId"])

    assert bridge.apply_timeline_summary_result("todo-1", request_id, "event-1", "新摘要") is True

    event = saved[-1][1]["timeline"][0]
    assert event.content == "新摘要"
    assert event.payload["summary"] == "新摘要"
    assert event.payload["raw_content"] == "原始长文"
    assert event.payload["polished_detail"] == "原始长文"


def test_timeline_detail_html_updates_when_switching_events() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.timeline = [
        TimelineEvent(id="event-1", kind="manual", content="原文一"),
        TimelineEvent(id="event-2", kind="manual", content="原文二"),
    ]
    bridge.set_todo(todo)

    bridge.openTimelineDetail("event-1")
    first_html = bridge.timelineDetailHtml
    bridge.openTimelineDetail("event-2")
    second_html = bridge.timelineDetailHtml

    assert "原文一" in first_html
    assert "原文二" in second_html
    assert "原文一" not in second_html


def test_timeline_polish_result_updates_target_event_only() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.timeline = [
        TimelineEvent(id="event-1", kind="manual", content="原文一"),
        TimelineEvent(id="event-2", kind="manual", content="原文二"),
    ]
    saved: list[tuple[str, dict[str, object]]] = []
    requests: list[tuple[str, dict[str, object]]] = []
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))
    bridge.timelinePolishRequested.connect(lambda todo_id, payload: requests.append((todo_id, payload)))
    bridge.set_todo(todo)

    bridge.openTimelineDetail("event-1")
    bridge.requestTimelinePolish("event-1")
    request_id = str(requests[0][1]["requestId"])

    assert bridge.apply_timeline_polish_result("todo-1", request_id, "event-1", "摘要一", "### 详情一") is True

    events = saved[-1][1]["timeline"]
    event_by_id = {event.id: event for event in events}
    assert event_by_id["event-1"].content == "摘要一"
    assert event_by_id["event-1"].payload["raw_content"] == "### 详情一"
    assert event_by_id["event-1"].payload["summary"] == "摘要一"
    assert event_by_id["event-1"].payload["polished_detail"] == "### 详情一"
    assert event_by_id["event-2"].content == "原文二"
    assert event_by_id["event-2"].payload == {}
    assert bridge.timelineDetailSummary == "摘要一"
    assert bridge.timelineDetailText == "### 详情一"


def test_timeline_polish_error_does_not_overwrite_content() -> None:
    bridge = _build_bridge(Path("unused"))
    todo = _build_todo()
    todo.timeline = [TimelineEvent(id="event-1", kind="manual", content="原文")]
    saved: list[tuple[str, dict[str, object]]] = []
    requests: list[tuple[str, dict[str, object]]] = []
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))
    bridge.timelinePolishRequested.connect(lambda todo_id, payload: requests.append((todo_id, payload)))
    bridge.set_todo(todo)

    bridge.openTimelineDetail("event-1")
    bridge.requestTimelinePolish("event-1")
    request_id = str(requests[0][1]["requestId"])

    assert bridge.apply_timeline_polish_error("todo-1", request_id, "服务端失败") is True
    assert saved == []
    assert bridge.timeline[0]["content"] == "原文"
    assert bridge.timelineDetailError == "服务端失败"


def test_timeline_polish_request_is_blocked_when_feature_disabled() -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="todo-detail-config-", dir=Path.cwd()))
    config_manager = ConfigManager(str(temp_dir / "config.json"))
    config = config_manager.load()
    config.enable_timeline_polish = False
    config_manager.save(config)
    bridge = _TodoDetailBridge(
        attachment_root=Path("unused"),
        environment_access_service=SimpleNamespace(
            list_project_environments=lambda _project_id: [],
            list_effective_environments=lambda _project_id: [],
        ),
        config_manager=config_manager,
    )
    todo = _build_todo()
    todo.timeline = [TimelineEvent(id="event-1", kind="manual", content="原文")]
    requests: list[tuple[str, dict[str, object]]] = []
    bridge.timelinePolishRequested.connect(lambda todo_id, payload: requests.append((todo_id, payload)))
    bridge.set_todo(todo)

    bridge.openTimelineDetail("event-1")
    bridge.requestTimelinePolish("event-1")

    assert requests == []
    assert bridge.timelinePolishEnabled is False
    assert bridge.timelineDetailError == "时间线润色功能已关闭"


def test_timeline_detail_markdown_renderer_outputs_html() -> None:
    html = _render_timeline_markdown_html("1. **URL 参数控制**\n\n```json\n{}\n```")

    assert "<ol>" in html
    assert "<strong>URL 参数控制</strong>" in html
    assert "<pre><code" in html
    assert "**URL 参数控制**" not in html
