from aica.worker import (
    TITLE_GENERATION_MODEL,
    build_plan_export_filename,
    build_plan_export_messages,
    normalize_markdown_content,
)


def _payload() -> dict[str, object]:
    return {
        "title": "企业微信导出报表失败",
        "current_summary": "客户反馈生产环境导出报表时报错，当前仍未恢复。",
        "summary_fields": {
            "group_name": "客户支持群",
            "environment": "生产",
            "product_line": "企业微信",
            "ticket_type": "问题排查",
        },
        "timeline": [
            {
                "timestamp": "2026-04-07T10:00:00",
                "scenario": "工单待办助手",
                "content": "客户反馈点击导出后页面报错。",
            },
            {
                "timestamp": "2026-04-07T10:30:00",
                "scenario": "工单待办助手",
                "content": "已确认仅生产环境复现，测试环境正常。",
            },
        ],
    }


def test_build_plan_export_messages_contains_required_context():
    messages = build_plan_export_messages(_payload())

    assert TITLE_GENERATION_MODEL == "Qwen/Qwen3-8B"
    assert messages[0]["role"] == "system"
    assert "Markdown 处理方案" in messages[1]["content"]
    assert "待办标题: 企业微信导出报表失败" in messages[1]["content"]
    assert "环境: 生产" in messages[1]["content"]
    assert "1. [2026-04-07T10:00:00] 工单待办助手: 客户反馈点击导出后页面报错。" in messages[1]["content"]


def test_normalize_markdown_content_strips_code_fence():
    assert normalize_markdown_content("```markdown\n# 处理方案\n\n内容\n```") == "# 处理方案\n\n内容"


def test_build_plan_export_filename_replaces_invalid_chars():
    assert build_plan_export_filename('报表导出: 失败/超时?') == "报表导出_ 失败_超时_.md"
