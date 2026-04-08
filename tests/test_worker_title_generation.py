from aica.models import TicketSnapshot, TicketSummaryFields
from aica.worker import TITLE_GENERATION_MODEL, _BaseVisionWorker


def _snapshot() -> TicketSnapshot:
    return TicketSnapshot(
        title="旧标题",
        fields=TicketSummaryFields(
            group_name="台X省能源测试交付群",
            environment="测试",
            product_line="企业微信",
            ticket_type="技术",
        ),
        current_summary=(
            "用户在上传文档时遇到勾选框变Q的问题，上传时未勾选，"
            "但线上勾选后重新打开就变Q了。"
        ),
        timeline_entry="当前截图显示勾选框使用的字体为Wingdings 2，需要确认服务器字体可用性。",
    )


def test_normalize_generated_title_supports_plain_text_and_prefixed_output():
    assert _BaseVisionWorker._normalize_generated_title("标题：文档勾选框线上勾选后重新打开变成字符Q") == (
        "文档勾选框线上勾选后重新打开变成字符Q"
    )
    assert _BaseVisionWorker._normalize_generated_title("```text\n文档勾选框线上勾选后重新打开变成字符Q\n```") == (
        "文档勾选框线上勾选后重新打开变成字符Q"
    )


def test_normalize_generated_title_supports_json_output():
    assert _BaseVisionWorker._normalize_generated_title(
        '{"title":"【企业微信】文档勾选框线上勾选后重新打开变成字符Q"}'
    ) == "【企业微信】文档勾选框线上勾选后重新打开变成字符Q"


def test_build_title_generation_messages_contains_required_context():
    messages = _BaseVisionWorker._build_title_generation_messages(_snapshot())

    assert TITLE_GENERATION_MODEL == "Qwen/Qwen3-8B"
    assert messages[0]["role"] == "system"
    assert "最终用户可见的异常现象" in messages[1]["content"]
    assert "产品线: 文档中台" in messages[1]["content"]
    assert "工单类型: 排查类" in messages[1]["content"]
    assert "当前摘要:" in messages[1]["content"]


def test_resolve_title_generation_model_allows_config_override():
    worker = _BaseVisionWorker()
    worker._title_generation_model = "custom/title-model"

    assert worker._resolve_title_generation_model() == "custom/title-model"
