from aica.models import TicketSnapshot, summarize_issue_title


def test_summarize_issue_title_uses_problem_summary_within_20_chars():
    summary = (
        "客户需要搭建一个党建系统的多维表demo，基于模板库中的党建活动管理模板进行完善，"
        "现需进一步定制以满足客户需求。"
    )

    title = summarize_issue_title(summary)

    assert len(title) <= 20
    assert "定制" in title or "完善" in title


def test_summarize_issue_title_prefers_final_visible_exception():
    summary = (
        "用户在上传文档时遇到勾选框变Q的问题，上传时未勾选，"
        "但线上勾选后重新打开就变Q了。截图显示当前使用的字体为Wingdings 2，"
        "需要确认该字体在服务器上的可用性，以解决勾选框显示异常的问题。"
    )

    title = summarize_issue_title(summary)

    assert "未勾选" not in title
    assert "勾选框" in title
    assert "Q" in title


def test_ticket_snapshot_from_dict_preserves_ai_title():
    snapshot = TicketSnapshot.from_dict(
        {
            "title": "这是一段明显过长且不适合作为标题的原始描述",
            "current_summary": "用户反馈移动端登录报错，页面提示验证码失效，需要排查。",
        }
    )

    assert snapshot.title == "这是一段明显过长且不适合作为标题的原始描述"


def test_ticket_snapshot_from_dict_preserves_short_generated_title():
    snapshot = TicketSnapshot.from_dict(
        {
            "title": "【企业微信】文档勾选框线上勾选后重新打开变成字符Q",
            "current_summary": "用户反馈文档勾选框线上勾选后重新打开变成字符Q，需要确认字体可用性。",
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
