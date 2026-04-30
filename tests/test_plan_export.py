from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.config import ProviderConfig, ProviderModelConfig, TaskModelBinding, TaskModelBindings, _normalize_task_bindings
from aica.worker import build_plan_export_messages


def test_build_plan_export_messages_uses_text_only_prompt() -> None:
    payload = {
        "title": "导出方案测试",
        "current_summary": "当前已有基本结论。",
        "summary_fields": {
            "group_name": "测试群",
            "environment": "生产",
            "product_line": "智能助手",
            "ticket_type": "排查类",
        },
        "timeline": [
            {
                "timestamp": "2026-04-29T10:00:00",
                "scenario": "客户反馈",
                "content": "客户提供了截图，需要确认是否与参数缺失有关。",
                "attachments": [
                    {
                        "name": "screenshot.png",
                        "path": str(Path("unused") / "screenshot.png"),
                        "kind": "image",
                        "sizeBytes": 1024,
                    }
                ],
            }
        ],
    }

    messages = build_plan_export_messages(payload)

    assert len(messages) == 2
    assert isinstance(messages[1].content, str)
    assert "解决方案知识条目" in messages[1].content
    assert "元数据" in messages[1].content
    assert "产品线" in messages[1].content
    assert "版本号" in messages[1].content
    assert "功能点" in messages[1].content
    assert "项目名" in messages[1].content
    assert "问题描述" in messages[1].content
    assert "解决过程" in messages[1].content
    assert "问题结论" in messages[1].content
    assert "复用建议" in messages[1].content
    assert "screenshot.png" in messages[1].content
    assert "data:image/" not in messages[1].content


def test_build_plan_export_messages_includes_project_backed_metadata() -> None:
    payload = {
        "title": "login fails",
        "current_summary": "user cannot login",
        "summary_fields": {
            "group_name": "Project A support",
            "environment": "prod",
            "product_line": "Collab",
            "ticket_type": "bug",
            "feature_point": "SSO",
        },
        "project_link": {
            "match_status": "matched",
            "matched_alias": "Project A support",
            "project_snapshot": {
                "project_name": "Project A",
                "task_order_no": "TASK-1001",
                "customer_name": "Customer A",
                "product_version": "release_dc_v7",
                "project_manager": "Alice",
                "project_level": "P1",
            },
        },
        "timeline": [],
    }

    messages = build_plan_export_messages(payload)
    prompt = str(messages[1].content)

    assert "Project A" in prompt
    assert "TASK-1001" in prompt
    assert "release_dc_v7" in prompt
    assert "Alice" in prompt
    assert "SSO" in prompt


def test_normalize_task_bindings_keeps_text_only_plan_export_model() -> None:
    providers = [
        ProviderConfig(
            id="stub",
            kind="openai_compatible",
            name="stub",
            api_key="",
            base_url="https://example.invalid",
            models=[ProviderModelConfig(id="text-only", name="text-only", capabilities=["text_chat"])],
        )
    ]
    bindings = TaskModelBindings(plan_export=TaskModelBinding(provider_id="stub", model_id="text-only"))

    normalized = _normalize_task_bindings(bindings, providers, default_provider_id="stub")

    assert normalized.plan_export == TaskModelBinding(provider_id="stub", model_id="text-only")
