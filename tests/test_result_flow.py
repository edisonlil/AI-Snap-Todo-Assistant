from aica.feedback import FeedbackData
from aica.models import TicketSnapshot, TicketSummaryFields
from aica.result_flow import ResultFlowCoordinator, SavedTodoResult


def _snapshot(summary: str) -> TicketSnapshot:
    return TicketSnapshot(
        title="上传失败",
        fields=TicketSummaryFields(
            group_name="客户群",
            environment="生产",
            product_line="AI-SNAP",
            ticket_type="问题排查",
        ),
        current_summary=summary,
        timeline_entry="跟进记录",
    )


def test_build_saved_todo_message_for_created_todo():
    message = ResultFlowCoordinator.build_saved_todo_message(
        SavedTodoResult(action="create", todo_title="新待办")
    )

    assert "已创建待办" in message


def test_build_saved_todo_message_for_appended_todo():
    message = ResultFlowCoordinator.build_saved_todo_message(
        SavedTodoResult(action="append", todo_title="已有待办")
    )

    assert "已追加到待办" in message


def test_populate_feedback_data_sets_structured_result_fields():
    feedback = FeedbackData()
    original = _snapshot("旧摘要")
    edited = _snapshot("新摘要")

    populated = ResultFlowCoordinator.populate_feedback_data(
        result=original,
        edited_result=edited,
        feedback_data=feedback,
        feedback_image_base64="abc123",
        prompt_trace_id="trace-001",
        prompt_version="rules-v2",
    )

    assert "旧摘要" in populated.original_result
    assert "新摘要" in populated.edited_result
    assert populated.user_edited is True
    assert populated.image_base64 == "abc123"
    assert populated.correction["current_summary"] == "新摘要"
    assert populated.prompt_trace_id == "trace-001"
    assert populated.prompt_version == "rules-v2"
