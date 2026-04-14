from aica.analysis_rules import AnalysisRuleConfig, SceneAnalysisRule, UserRuleConfig
from aica.analysis_intent import build_analysis_intent
from aica.analysis_strategy import build_analysis_prompt_bundle_from_rules, build_analysis_text_prompt
from aica.ticket_field_resolver import DEFAULT_PRODUCT_LINE


def test_analysis_prompt_changes_with_scene_type():
    prompt = build_analysis_text_prompt(
        build_analysis_intent("api_detail", focus_hint="重点提取请求参数", capture_count=1),
        context_text="当前摘要: 旧摘要",
        image_count=1,
    )

    assert "参数与接口详情" in prompt
    assert "timeline_entry" in prompt
    assert "重点提取请求参数" in prompt
    assert "字段名和字段值" in prompt


def test_analysis_prompt_mentions_sequence_for_multi_capture():
    prompt = build_analysis_text_prompt(
        build_analysis_intent("step_sequence", capture_count=3),
        context_text="",
        image_count=3,
    )

    assert "连续截图" in prompt
    assert "按顺序" in prompt


def test_analysis_prompt_does_not_request_fixed_product_line():
    prompt = build_analysis_text_prompt(
        build_analysis_intent("chat_feedback", capture_count=1),
        context_text="",
        image_count=1,
    )

    assert DEFAULT_PRODUCT_LINE not in prompt


def test_analysis_prompt_bundle_appends_user_rules_last():
    bundle = build_analysis_prompt_bundle_from_rules(
        build_analysis_intent("chat_feedback", focus_hint="先提取客户诉求", capture_count=1),
        rules_config=AnalysisRuleConfig(
            version="rules-v3",
            scene_rules={
                "chat_feedback": UserRuleConfig(items=["标题优先保留最终异常现象", "必须体现客户诉求", "补充下一步动作"]),
                "error_log": UserRuleConfig(items=["保留错误码"]),
            },
        ),
        trace_id="trace-abc",
        context_text="当前摘要：旧上下文",
        image_count=1,
    )

    assert bundle.prompt_version == "rules-v3"
    assert bundle.trace_id == "trace-abc"
    assert "【已有待办上下文】" in bundle.user_prompt
    assert bundle.user_prompt.index("【已有待办上下文】") < bundle.user_prompt.index("请仅输出 JSON")
    assert bundle.user_prompt.index("用户补充重点") < bundle.user_prompt.index("【用户规则】")
    assert "标题优先保留最终异常现象" in bundle.user_prompt
    assert "必须体现客户诉求" in bundle.user_prompt
    assert bundle.applied_rule_snapshot == {
        "items": ["标题优先保留最终异常现象", "必须体现客户诉求", "补充下一步动作"]
    }


def test_analysis_prompt_bundle_uses_scene_specific_rules():
    bundle = build_analysis_prompt_bundle_from_rules(
        build_analysis_intent("error_log", capture_count=1),
        rules_config=AnalysisRuleConfig(
            scene_rules={
                "chat_feedback": UserRuleConfig(items=["必须体现客户诉求"]),
                "error_log": UserRuleConfig(items=["保留错误码", "保留 TraceId"]),
            }
        ),
        image_count=1,
    )

    assert "保留错误码" in bundle.user_prompt
    assert "保留 TraceId" in bundle.user_prompt
    assert "必须体现客户诉求" not in bundle.user_prompt


def test_analysis_prompt_bundle_falls_back_to_legacy_scene_rules():
    bundle = build_analysis_prompt_bundle_from_rules(
        build_analysis_intent("chat_feedback", capture_count=1),
        rules_config=AnalysisRuleConfig(
            scenes={
                "chat_feedback": SceneAnalysisRule(
                    title_preference="标题优先保留最终异常现象",
                    must_include="客户诉求\n下一步动作",
                )
            }
        ),
        image_count=1,
    )

    assert "【用户规则】" in bundle.user_prompt
    assert "标题偏好：标题优先保留最终异常现象" in bundle.user_prompt
    assert "必须包含：客户诉求；下一步动作" in bundle.user_prompt
