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
