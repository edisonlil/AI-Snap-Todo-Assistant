from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.models import TicketSummaryFields
from aica.todo_detail_panel import _TodoDetailBridge
from aica.todo_models import TodoConclusion, TodoItem


def _build_bridge(attachment_root: Path) -> _TodoDetailBridge:
    return _TodoDetailBridge(
        attachment_root=attachment_root,
        environment_access_service=SimpleNamespace(
            list_project_environments=lambda _project_id: [],
        ),
    )


def _build_todo(todo_id: str = "todo-1") -> TodoItem:
    return TodoItem(
        id=todo_id,
        title="测试待办",
        current_summary="当前摘要",
        summary_fields=TicketSummaryFields(),
        conclusion=TodoConclusion(),
        timeline=[],
    )


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
    assert bridge.conclusionAttachments[0]["path"] == "/final/__conclusion__/existing.txt"
    assert bridge.conclusionAttachments[1]["path"] == "/final/__conclusion__/report.txt"


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
