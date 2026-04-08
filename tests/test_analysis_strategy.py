from aica.analysis_intent import build_analysis_intent
from aica.analysis_strategy import build_analysis_text_prompt


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
