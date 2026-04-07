from aica.models import TicketSnapshot, TicketSummaryFields
from aica.todo_controller import TodoController
from aica.todo_store import TimelineEvent, TodoItem


def test_extract_incremental_timeline_entry_keeps_only_new_follow_up() -> None:
    todo = TodoItem(
        title="勾选框变Q",
        summary_fields=TicketSummaryFields(),
        current_summary="用户在金山文档中遇到勾选框变Q的问题，上传时未勾选，线上勾选后重新打开变为字符Q，需要排查此问题，确认是否为线上勾选导致。",
        timeline=[
            TimelineEvent(content="用户在金山文档中遇到勾选框变Q的问题，上传时未勾选，线上勾选后重新打开变为字符Q，需要排查此问题，确认是否为线上勾选导致。"),
            TimelineEvent(content="当前跟进内容为确认字体类型，并检查服务器是否缺少该字体。"),
        ],
    )

    cumulative_timeline = (
        "用户在金山文档中遇到勾选框变Q的问题，上传时未勾选，线上勾选后重新打开变为字符Q。"
        "当前截图显示勾选框使用的字体为Wingdings 2，需要进一步确认该字体在服务器上的可用性，以排查是否因字体缺失导致问题。"
    )

    incremental = TodoController._extract_incremental_timeline_entry(todo, cumulative_timeline)

    assert incremental == "当前截图显示勾选框使用的字体为Wingdings 2，需要进一步确认该字体在服务器上的可用性，以排查是否因字体缺失导致问题"


def test_normalize_snapshot_for_append_preserves_summary_but_dedups_timeline() -> None:
    todo = TodoItem(
        title="勾选框变Q",
        summary_fields=TicketSummaryFields(),
        current_summary="已有摘要",
        timeline=[TimelineEvent(content="第一条跟进")],
    )
    snapshot = TicketSnapshot(
        title="新标题",
        fields=TicketSummaryFields(product_line="企业微信"),
        current_summary="已有摘要 + 新观察",
        timeline_entry="第一条跟进，当前跟进内容为确认字体类型，并检查服务器是否缺少该字体。",
    )

    normalized = TodoController._normalize_snapshot_for_append(todo, snapshot)

    assert normalized.current_summary == "已有摘要 + 新观察"
    assert normalized.timeline_entry == "当前跟进内容为确认字体类型，并检查服务器是否缺少该字体"
