from pathlib import Path
import shutil

from aica.analysis_rules import (
    AnalysisRuleConfig,
    AnalysisRulesManager,
    PromptDebugStore,
    SceneAnalysisRule,
    UserRuleConfig,
    build_rule_section_text,
)


def test_analysis_rules_manager_persists_scene_user_rules_and_debug_settings():
    path = Path("tests") / "_tmp_analysis_rules.json"
    try:
        if path.exists():
            path.unlink()
        manager = AnalysisRulesManager(path)

        manager.update_scene_user_rules(
            "chat_feedback",
            UserRuleConfig(
                items=[
                    "标题保留最终异常",
                    "必须体现客户诉求",
                ]
            )
        )
        manager.update_scene_user_rules(
            "error_log",
            UserRuleConfig(items=["保留错误码", "保留 TraceId", "不要省略关键报错词"])
        )
        manager.update_debug_config(enabled=True, max_records=12)
        saved = manager.save()

        reloaded = AnalysisRulesManager(path).config

        assert saved.version != "built-in"
        assert reloaded.debug.enabled is True
        assert reloaded.debug.max_records == 12
        assert reloaded.scene_rules["chat_feedback"].to_lines() == [
            "标题保留最终异常",
            "必须体现客户诉求",
        ]
        assert reloaded.scene_rules["error_log"].to_lines() == [
            "保留错误码",
            "保留 TraceId",
            "不要省略关键报错词",
        ]
    finally:
        if path.exists():
            path.unlink()


def test_prompt_debug_store_prunes_old_records():
    temp_dir = Path("tests") / "_tmp_prompt_debug_store"
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
        store = PromptDebugStore(temp_dir)

        for index in range(3):
            store.write_record(
                {
                    "trace_id": f"trace-{index}",
                    "timestamp": f"2026-04-12T00:00:0{index}",
                    "status": "success",
                    "scene_label": "工单跟进",
                    "model": "provider/model",
                },
                max_records=2,
            )

        records = store.list_records(limit=10)

        assert [item["traceId"] for item in records] == ["trace-2", "trace-1"]
        assert store.load_record("trace-0") is None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_build_rule_section_text_formats_dynamic_user_rules():
    text = build_rule_section_text(
        UserRuleConfig(items=["标题直接写最终异常", "保留错误码", "不要猜测"])
    )

    assert "【用户规则】" in text
    assert "2. 保留错误码" in text
    assert "3. 不要猜测" in text


def test_analysis_rule_config_tolerates_invalid_payload():
    config = AnalysisRuleConfig.from_dict({"debug": {"enabled": True, "max_records": "bad"}})

    assert config.debug.enabled is True
    assert config.debug.max_records == 100
    assert "chat_feedback" in config.scenes


def test_analysis_rule_config_derives_scene_user_rules_from_global_rules_payload():
    config = AnalysisRuleConfig.from_dict(
        {
            "rules": {
                "items": [
                    "标题优先保留最终异常",
                    "必须体现客户诉求",
                ]
            }
        }
    )

    assert config.scene_rules["chat_feedback"].to_lines() == [
        "标题优先保留最终异常",
        "必须体现客户诉求",
    ]
    assert config.scene_rules["error_log"].to_lines() == [
        "标题优先保留最终异常",
        "必须体现客户诉求",
    ]


def test_analysis_rule_config_derives_scene_user_rules_from_legacy_scene_payload():
    config = AnalysisRuleConfig.from_dict(
        {
            "scenes": {
                "chat_feedback": {
                    "title_preference": "标题优先保留最终异常",
                    "must_include": "客户诉求\n下一步动作",
                },
                "error_log": {
                    "must_include": "错误码\nTraceId",
                }
            }
        }
    )

    assert config.scene_rules["chat_feedback"].to_lines() == [
        "标题偏好：标题优先保留最终异常",
        "必须包含：客户诉求；下一步动作",
    ]
    assert config.scene_rules["error_log"].to_lines() == ["必须包含：错误码；TraceId"]
