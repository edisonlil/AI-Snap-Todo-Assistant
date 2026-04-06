"""提示词管理系统的单元测试"""
import os
import json
import tempfile
import pytest
from pathlib import Path

from aica.prompts import PromptManager, PromptTemplate, PromptsConfig


@pytest.fixture
def temp_config_file():
    """创建临时配置文件"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name
    yield temp_path
    # 清理
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def prompt_manager(temp_config_file):
    """创建 PromptManager 实例"""
    return PromptManager(config_path=temp_config_file)


def test_init_default_scenarios(prompt_manager):
    """测试初始化时有默认场景"""
    scenarios = prompt_manager.list_scenarios()
    assert len(scenarios) >= 4
    assert "工单提取" in scenarios
    assert "代码审查" in scenarios
    assert "数据提取" in scenarios
    assert "界面审计" in scenarios


def test_get_current_prompt(prompt_manager):
    """测试获取当前场景的提示词"""
    prompt = prompt_manager.get_current_prompt()
    assert isinstance(prompt, PromptTemplate)
    assert len(prompt.system) > 0
    assert len(prompt.user) > 0


def test_get_prompt_by_scenario(prompt_manager):
    """测试按场景名称获取提示词"""
    prompt = prompt_manager.get_prompt("代码审查")
    assert prompt is not None
    assert "代码" in prompt.system or "代码" in prompt.user


def test_set_current_scenario(prompt_manager):
    """测试切换场景"""
    assert prompt_manager.set_current_scenario("代码审查")
    assert prompt_manager.get_current_scenario_name() == "代码审查"
    
    # 测试设置不存在的场景
    assert not prompt_manager.set_current_scenario("不存在的场景")


def test_add_scenario(prompt_manager):
    """测试添加新场景"""
    new_template = PromptTemplate(
        system="测试系统提示",
        user="测试用户提示"
    )
    prompt_manager.add_scenario("测试场景", new_template)
    
    assert prompt_manager.is_scenario_exists("测试场景")
    prompt = prompt_manager.get_prompt("测试场景")
    assert prompt.system == "测试系统提示"
    assert prompt.user == "测试用户提示"


def test_update_scenario(prompt_manager):
    """测试更新场景"""
    new_template = PromptTemplate(
        system="更新后的系统提示",
        user="更新后的用户提示"
    )
    
    # 先添加一个场景
    prompt_manager.add_scenario("待更新场景", new_template)
    
    # 再更新它
    updated_template = PromptTemplate(
        system="最新的系统提示",
        user="最新的用户提示"
    )
    assert prompt_manager.update_scenario("待更新场景", updated_template)
    
    prompt = prompt_manager.get_prompt("待更新场景")
    assert prompt.system == "最新的系统提示"
    assert prompt.user == "最新的用户提示"


def test_update_nonexistent_scenario(prompt_manager):
    """测试更新不存在的场景"""
    template = PromptTemplate(system="test", user="test")
    assert not prompt_manager.update_scenario("不存在的场景", template)


def test_delete_scenario(prompt_manager):
    """测试删除场景"""
    # 添加一个新场景
    new_template = PromptTemplate(system="test", user="test")
    prompt_manager.add_scenario("待删除场景", new_template)
    assert prompt_manager.is_scenario_exists("待删除场景")
    
    # 删除它
    assert prompt_manager.delete_scenario("待删除场景")
    assert not prompt_manager.is_scenario_exists("待删除场景")


def test_cannot_delete_current_scenario(prompt_manager):
    """测试不能删除当前场景"""
    current = prompt_manager.get_current_scenario_name()
    assert not prompt_manager.delete_scenario(current)


def test_delete_nonexistent_scenario(prompt_manager):
    """测试删除不存在的场景"""
    assert not prompt_manager.delete_scenario("不存在的场景")


def test_persistence(temp_config_file):
    """测试数据持久化"""
    # 创建第一个管理器实例并修改数据
    pm1 = PromptManager(config_path=temp_config_file)
    new_template = PromptTemplate(system="持久化测试", user="测试用户提示")
    pm1.add_scenario("持久化场景", new_template)
    pm1.set_current_scenario("持久化场景")
    
    # 创建第二个管理器实例，加载相同的配置文件
    pm2 = PromptManager(config_path=temp_config_file)
    
    # 验证数据已保存
    assert pm2.is_scenario_exists("持久化场景")
    assert pm2.get_current_scenario_name() == "持久化场景"
    prompt = pm2.get_prompt("持久化场景")
    assert prompt.system == "持久化测试"


def test_config_file_format(temp_config_file):
    """测试配置文件的 JSON 格式"""
    pm = PromptManager(config_path=temp_config_file)
    new_template = PromptTemplate(system="test", user="test")
    pm.add_scenario("格式测试", new_template)
    
    # 直接读取并验证 JSON 格式
    with open(temp_config_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    assert "current_scenario" in data
    assert "scenarios" in data
    assert "格式测试" in data["scenarios"]
    assert data["scenarios"]["格式测试"]["system"] == "test"


def test_get_current_scenario_name(prompt_manager):
    """测试获取当前场景名称"""
    original = prompt_manager.get_current_scenario_name()
    assert isinstance(original, str)
    assert len(original) > 0
    
    # 切换场景后再检查
    prompt_manager.set_current_scenario("代码审查")
    assert prompt_manager.get_current_scenario_name() == "代码审查"


def test_is_scenario_exists(prompt_manager):
    """测试场景是否存在的检查"""
    assert prompt_manager.is_scenario_exists("工单提取")
    assert not prompt_manager.is_scenario_exists("不存在的场景")


def test_list_scenarios_returns_copy(prompt_manager):
    """测试 list_scenarios() 返回的是副本"""
    scenarios = prompt_manager.list_scenarios()
    original_count = len(scenarios)
    
    # 修改返回的字典
    scenarios["临时场景"] = PromptTemplate(system="test", user="test")
    
    # 确保原始数据未被修改
    new_scenarios = prompt_manager.list_scenarios()
    assert len(new_scenarios) == original_count


def test_empty_template(prompt_manager):
    """测试空的提示词模板"""
    empty_template = PromptTemplate(system="", user="")
    prompt_manager.add_scenario("空模板场景", empty_template)
    
    prompt = prompt_manager.get_prompt("空模板场景")
    assert prompt.system == ""
    assert prompt.user == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
