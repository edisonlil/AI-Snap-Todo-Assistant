from aica.models import TicketSnapshot, TicketSummaryFields, summarize_issue_title


def test_summarize_issue_title_uses_problem_summary_within_20_chars():
    summary = (
        "客户需要搭建一个党建系统的多维表 demo，基于模板库中的党建活动管理模板进行完善，"
        "现需进一步定制以满足客户需求。"
    )

    title = summarize_issue_title(summary)

    assert len(title) <= 20
    assert "定制" in title or "完善" in title


def test_summarize_issue_title_prefers_final_visible_exception():
    summary = (
        "用户在上传文档时遇到勾选框变 Q 的问题，上传时未勾选，"
        "但线上勾选后重新打开就变 Q 了。截图显示当前使用的字体为 Wingdings 2，"
        "需要确认该字体在服务器上的可用性，以解决勾选框显示异常的问题。"
    )

    title = summarize_issue_title(summary)

    assert "未勾选" not in title
    assert "勾选框" in title
    assert "Q" in title


def test_ticket_snapshot_from_dict_preserves_ai_title():
    snapshot = TicketSnapshot.from_dict(
        {
            "title": "这是一个明显过长但仍应保留的原始标题",
            "current_summary": "用户反馈移动端登录报错，页面提示验证码失效，需要排查。",
        }
    )

    assert snapshot.title == "这是一个明显过长但仍应保留的原始标题"


def test_ticket_snapshot_from_dict_preserves_short_generated_title():
    snapshot = TicketSnapshot.from_dict(
        {
            "title": "【企业微信】文档勾选框线上勾选后重新打开变成字符Q",
            "current_summary": "用户反馈文档勾选框线上勾选后重新打开变成字符Q，需确认字体可用性。",
        }
    )

    assert snapshot.title == "【企业微信】文档勾选框线上勾选后重新打开变成字符Q"


def test_ticket_snapshot_from_dict_falls_back_only_when_title_missing():
    snapshot = TicketSnapshot.from_dict(
        {
            "title": "",
            "current_summary": "用户反馈移动端登录报错，页面提示验证码失效，需要排查。",
        }
    )

    assert snapshot.title
    assert "验证码失效" in snapshot.title or "登录报错" in snapshot.title


def test_ticket_snapshot_from_dict_merges_evidence_into_timeline_entry():
    snapshot = TicketSnapshot.from_dict(
        {
            "title": "接口转换异常",
            "current_summary": "客户提供了请求参数和日志，需要进一步排查。",
            "timeline_entry": "客户补充了转换接口的请求参数与返回结果。",
            "evidence_items": [
                {
                    "type": "request_param",
                    "label": "task_id",
                    "value": "abc123",
                    "source_image_index": 2,
                    "scene_type": "api_detail",
                },
                {
                    "type": "trace_id",
                    "label": "TraceId",
                    "value": "trace-1",
                    "source_image_index": 2,
                    "scene_type": "error_log",
                },
            ],
        }
    )

    assert snapshot.evidence_items == []
    assert "task_id" in snapshot.timeline_entry
    assert "trace-1" in snapshot.timeline_entry


def test_ticket_snapshot_from_dict_replaces_invalid_surrogates():
    snapshot = TicketSnapshot.from_dict(
        {
            "title": "排查💡\udcaa",
            "current_summary": "摘要包含异常代理项\udcae",
            "timeline_entry": "跟进内容\udc80",
        }
    )

    assert snapshot.title == "排查💡�"
    assert snapshot.current_summary == "摘要包含异常代理项�"
    assert snapshot.timeline_entry == "跟进内容�"



def test_ticket_summary_fields_round_trip_preserves_enrichment_fields():
    fields = TicketSummaryFields(
        group_name="group-a",
        environment="prod",
        product_line="Docs",
        ticket_type="???",
        ticket_version="v1",
        feature_point="????",
        feature_point_source="auto",
        root_cause_desc="??????",
        root_cause_desc_source="manual",
        root_cause="????",
        root_cause_source="auto",
    )

    restored = TicketSummaryFields.from_dict(fields.to_dict())

    assert restored.feature_point == "????"
    assert restored.feature_point_source == "auto"
    assert restored.root_cause_desc == "??????"
    assert restored.root_cause_desc_source == "manual"
    assert restored.root_cause == "????"
    assert restored.root_cause_source == "auto"
