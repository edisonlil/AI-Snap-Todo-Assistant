from aica.models import TicketSnapshot, summarize_issue_title


def test_summarize_issue_title_uses_problem_summary_within_20_chars():
    summary = (
        "客户需要搭建一个党建系统的多维表demo，基于模板库中的党建活动管理模板进行完善，"
        "现需进一步定制以满足客户需求。"
    )

    title = summarize_issue_title(summary)

    assert len(title) <= 20
    assert "定制" in title or "完善" in title


def test_ticket_snapshot_from_dict_prefers_summary_based_title():
    snapshot = TicketSnapshot.from_dict(
        {
            "title": "这是一段明显过长且不适合作为标题的原始描述",
            "current_summary": "用户反馈移动端登录报错，页面提示验证码失效，需要排查。",
        }
    )

    assert len(snapshot.title) <= 20
    assert "报错" in snapshot.title or "失效" in snapshot.title
