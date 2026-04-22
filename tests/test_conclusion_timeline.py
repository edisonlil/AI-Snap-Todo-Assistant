from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.conclusion_timeline import build_conclusion_timeline_content, sync_conclusion_timeline
from aica.todo_models import TimelineAttachment, TimelineEvent, TodoConclusion


def test_build_conclusion_timeline_content_includes_attachment_suffix() -> None:
    content = build_conclusion_timeline_content(
        "已定位根因",
        ["report.txt", "screen.png"],
    )

    assert content == "已定位根因\n附件: report.txt, screen.png"


def test_sync_conclusion_timeline_appends_conclusion_event() -> None:
    timeline = [
        TimelineEvent(
            id="progress-1",
            timestamp="2026-04-22T10:00:00",
            kind="manual",
            scenario="问题跟进",
            content="先收集日志",
        )
    ]

    updated = sync_conclusion_timeline(
        timeline,
        TodoConclusion(
            content="已定位为配置缺失",
            updated_at="2026-04-22T11:00:00",
            attachments=[TimelineAttachment(name="detail.txt")],
        ),
    )

    assert [event.kind for event in updated] == ["manual", "conclusion"]
    assert updated[-1].scenario == "结论更新"
    assert updated[-1].content == "已定位为配置缺失\n附件: detail.txt"


def test_sync_conclusion_timeline_preserves_existing_conclusion_event_id_when_cleared() -> None:
    timeline = [
        TimelineEvent(
            id="progress-1",
            timestamp="2026-04-22T10:00:00",
            kind="manual",
            scenario="问题跟进",
            content="先收集日志",
        ),
        TimelineEvent(
            id="conclusion-1",
            timestamp="2026-04-22T11:00:00",
            kind="conclusion",
            scenario="结论更新",
            content="旧结论",
        ),
    ]

    updated = sync_conclusion_timeline(
        timeline,
        TodoConclusion(
            content="",
            updated_at="2026-04-22T12:00:00",
            attachments=[],
        ),
    )

    assert [event.kind for event in updated] == ["manual", "conclusion"]
    assert updated[-1].id == "conclusion-1"
    assert updated[-1].content == "结论已清空"
