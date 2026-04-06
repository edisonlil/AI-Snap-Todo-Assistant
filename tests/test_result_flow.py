from aica.feedback import FeedbackData
from aica.result_flow import ResultFlowCoordinator, SavedTodoResult


def test_build_saved_todo_message_for_created_todo():
    message = ResultFlowCoordinator.build_saved_todo_message(
        SavedTodoResult(action="create", todo_title="新待办")
    )

    assert "已创建待办" in message
    assert "新待办" in message


def test_build_saved_todo_message_for_appended_todo():
    message = ResultFlowCoordinator.build_saved_todo_message(
        SavedTodoResult(action="append", todo_title="已有待办")
    )

    assert "已追加到待办" in message
    assert "已有待办" in message


def test_populate_feedback_data_sets_result_fields():
    feedback = FeedbackData()

    populated = ResultFlowCoordinator.populate_feedback_data(
        result={"raw": "before"},
        edited_result="after",
        feedback_data=feedback,
        feedback_image_base64="abc123",
    )

    assert populated.original_result == "{'raw': 'before'}"
    assert populated.edited_result == "after"
    assert populated.user_edited is True
    assert populated.image_base64 == "abc123"
    assert populated.correction == {"raw": "after"}
