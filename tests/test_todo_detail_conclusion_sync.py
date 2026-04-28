from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.models import TicketSummaryFields
from aica.todo_detail_panel import _TodoDetailBridge
from aica.todo_models import TimelineEvent, TodoConclusion, TodoItem


def _build_bridge() -> _TodoDetailBridge:
    return _TodoDetailBridge(
        attachment_root=Path("unused"),
        environment_access_service=SimpleNamespace(
            list_project_environments=lambda _project_id: [],
            list_effective_environments=lambda _project_id: [],
        ),
    )


def test_manual_save_syncs_cleared_conclusion_to_timeline() -> None:
    bridge = _build_bridge()
    bridge.set_todo(
        TodoItem(
            id="todo-1",
            title="测试待办",
            current_summary="当前描述",
            summary_fields=TicketSummaryFields(),
            conclusion=TodoConclusion(content="旧结论", updated_at="2026-04-22T10:00:00"),
            timeline=[
                TimelineEvent(
                    id="conclusion-1",
                    timestamp="2026-04-22T10:00:00",
                    kind="conclusion",
                    scenario="结论更新",
                    content="旧结论",
                )
            ],
        )
    )

    saved: list[tuple[str, object]] = []
    bridge.saveRequested.connect(lambda todo_id, payload: saved.append((todo_id, payload)))

    bridge.updateField("conclusion_content", "")
    bridge.saveTodo()

    assert bridge.timelineCount == 1
    assert bridge.timeline[0]["kind"] == "conclusion"
    assert bridge.timeline[0]["content"] == "结论已清空"
    assert len(saved) == 1
