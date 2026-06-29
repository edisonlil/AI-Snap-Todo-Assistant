from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.case_search import (
    CaseSearchItem,
    CaseSearchRequest,
    build_case_search_result_from_server_items,
    build_server_case_search_question,
)


def test_case_item_payload_exposes_score_fields() -> None:
    payload = CaseSearchItem(
        title="编辑保存偶现失败",
        desc="关键结论：文件大小字段需按 integer 返回。",
        detail_url="https://www.kdocs.cn/l/case1",
        score=86,
        score_label="契合度 86",
        match_reason="现象均包含编辑保存失败和 20022",
    ).to_payload()

    assert payload["score"] == 86
    assert payload["scoreLabel"] == "契合度 86"
    assert payload["matchReason"] == "现象均包含编辑保存失败和 20022"
    assert "关键结论" in str(payload["text"])


def test_build_server_case_search_question_joins_title_summary_and_timeline() -> None:
    request = CaseSearchRequest(
        title="编辑保存失败",
        current_summary="客户反馈保存时报错 20022",
        timeline_text="- 已确认大文件触发\n- demo 正常",
        function_point="文档中台-编辑-保存",
    )

    question = build_server_case_search_question(request)

    assert "工单标题：编辑保存失败" in question
    assert "问题描述：客户反馈保存时报错 20022" in question
    assert "跟进记录：" in question


def test_build_case_search_result_from_server_items_maps_server_fields() -> None:
    result = build_case_search_result_from_server_items(
        [
            {
                "title": "历史工单 A",
                "description": "原始问题描述",
                "match_confidence": "High",
                "match_reason": "共同报错 20022",
                "solution": "检查参数并修复返回类型",
            },
            {
                "title": "历史工单 B",
                "description": "弱相关",
                "match_confidence": "Low",
                "match_reason": "现象相近",
                "solution": "观察",
            },
        ]
    )

    assert result.status == "success"
    assert result.count_label == "检索 1 条结果"
    assert len(result.items) == 1
    assert result.items[0].title == "历史工单 A"
    assert result.items[0].score == 85
    assert result.items[0].score_label == "高匹配"
    assert result.items[0].match_reason == "共同报错 20022"
    assert "处理方案：检查参数并修复返回类型" in result.items[0].text
