import json
import os
import tempfile

import pytest

from aica.prompts import DEFAULT_SCENARIO_NAME, PromptManager, PromptTemplate


@pytest.fixture
def temp_config_file():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as handle:
        temp_path = handle.name
    yield temp_path
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_prompt_manager_only_exposes_ticket_assistant(temp_config_file):
    manager = PromptManager(config_path=temp_config_file)

    scenarios = manager.list_scenarios()

    assert list(scenarios.keys()) == [DEFAULT_SCENARIO_NAME]
    assert manager.get_current_scenario_name() == DEFAULT_SCENARIO_NAME


def test_prompt_manager_ignores_non_default_scenario_switch(temp_config_file):
    manager = PromptManager(config_path=temp_config_file)

    assert not manager.set_current_scenario("代码审查")
    assert manager.set_current_scenario(DEFAULT_SCENARIO_NAME)


def test_prompt_manager_persists_single_template(temp_config_file):
    manager = PromptManager(config_path=temp_config_file)
    template = PromptTemplate(system="系统提示", user="用户提示")

    assert manager.update_scenario(DEFAULT_SCENARIO_NAME, template)

    with open(temp_config_file, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["current_scenario"] == DEFAULT_SCENARIO_NAME
    assert list(payload["scenarios"].keys()) == [DEFAULT_SCENARIO_NAME]
    assert payload["scenarios"][DEFAULT_SCENARIO_NAME]["system"] == "系统提示"


def test_prompt_manager_injects_title_focus_rules_for_loaded_prompt(temp_config_file):
    payload = {
        "current_scenario": DEFAULT_SCENARIO_NAME,
        "scenarios": {
            DEFAULT_SCENARIO_NAME: {
                "system": "系统提示",
                "user": "请仅输出 JSON。2. group_name/environment/product_line/ticket_type 缺失时填“未知”。",
                "version": "v2.1",
                "last_improved_feedback_count": 0,
            }
        },
    }
    with open(temp_config_file, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    manager = PromptManager(config_path=temp_config_file)

    prompt = manager.get_current_prompt().user
    assert "最终用户可见的异常现象" in prompt
    assert "不要概括成“上传时未勾选”" in prompt
    assert "当前固定返回“文档中台”" in prompt
    assert "排查类" in prompt and "咨询类" in prompt and "操作类" in prompt


def test_prompt_manager_falls_back_to_default_when_default_scenario_missing(temp_config_file):
    payload = {
        "current_scenario": "工单提取",
        "scenarios": {
            "工单提取": {
                "system": "旧系统提示",
                "user": "旧用户提示",
                "version": "v1.0",
                "last_improved_feedback_count": 0,
            }
        },
    }
    with open(temp_config_file, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    manager = PromptManager(config_path=temp_config_file)

    prompt = manager.get_current_prompt()
    assert prompt.system != "旧系统提示"
    assert "evidence_items" not in prompt.user
