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
    assert "screenshot.png" in messages[1].content
    assert "data:image/" not in messages[1].content


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
