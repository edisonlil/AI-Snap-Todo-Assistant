import shutil
from pathlib import Path
import tempfile

from aica.worker import (
    PLAN_EXPORT_MODEL,
    TITLE_GENERATION_MODEL,
    append_plan_export_attachment_section,
    build_plan_export_filename,
    build_plan_export_messages,
    build_plan_export_timeline_markdown,
    ensure_plan_export_timeline_section,
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
                "attachments": [
                    {
                        "name": "export-error.png",
                        "kind": "image",
                        "sizeBytes": 2048,
                    }
                ],
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
    assert PLAN_EXPORT_MODEL == "Qwen/Qwen2.5-VL-72B-Instruct"
    assert messages[0]["role"] == "system"
    assert "Markdown 处理方案" in messages[1]["content"]
    assert "待办标题: 企业微信导出报表失败" in messages[1]["content"]
    assert "环境: 生产" in messages[1]["content"]
    assert "1. [2026-04-07T10:00:00] 工单待办助手: 客户反馈点击导出后页面报错。" in messages[1]["content"]
    assert "附件: 1. export-error.png" in messages[1]["content"]
    assert "必须包含“时间线回顾”" in messages[1]["content"]


def test_normalize_markdown_content_strips_code_fence():
    assert normalize_markdown_content("```markdown\n# 处理方案\n\n内容\n```") == "# 处理方案\n\n内容"


def test_build_plan_export_filename_replaces_invalid_chars():
    assert build_plan_export_filename('报表导出: 失败/超时?') == "报表导出_ 失败_超时_.md"


def test_build_plan_export_timeline_markdown_contains_timestamps_and_attachments():
    timeline_markdown = build_plan_export_timeline_markdown(_payload())

    assert "## 时间线回顾" in timeline_markdown
    assert "[2026-04-07T10:00:00]" in timeline_markdown
    assert "附件: 1. export-error.png" in timeline_markdown


def test_ensure_plan_export_timeline_section_appends_when_missing():
    markdown = ensure_plan_export_timeline_section("# 处理方案\n\n## 问题概述\n\n内容", _payload())

    assert "## 时间线回顾" in markdown
    assert "[2026-04-07T10:30:00]" in markdown


def test_append_plan_export_attachment_section_embeds_images_with_relative_paths():
    temp_dir = Path(tempfile.mkdtemp(prefix="plan_export_", dir="."))
    try:
        source = temp_dir / "export-error.png"
        source.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
            b"\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\x0f\x00\x01\x01\x01\x00"
            b"\x18\xdd\x8d\xb1\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        payload = _payload()
        payload["timeline"][0]["attachments"][0]["path"] = str(source)
        export_file = temp_dir / "plan.md"

        markdown = append_plan_export_attachment_section("# 处理方案", payload, export_file)

        assert "## 附件图示" in markdown
        assert "![export-error.png](plan_assets/export-error.png)" in markdown
        assert (temp_dir / "plan_assets" / "export-error.png").exists()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
