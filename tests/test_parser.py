"""单元测试：ResultParser 和 StructuredResult"""
import json
import pytest

from src.aica.models import StructuredResult
from src.aica.parser import (
    DEFAULT_ENVIRONMENT,
    DEFAULT_TICKET_TYPE,
    ENVIRONMENTS,
    MAX_TASK_DESC_LEN,
    TICKET_TYPES,
    ResultParser,
)


# ---------------------------------------------------------------------------
# StructuredResult.to_tab_row
# ---------------------------------------------------------------------------

class TestToTabRow:
    def test_returns_four_tabs(self):
        r = StructuredResult("描述", "微信", "群A", "技术", "生产")
        assert r.to_tab_row().count("\t") == 4

    def test_field_order(self):
        r = StructuredResult("desc", "platform", "group", "业务", "测试")
        parts = r.to_tab_row().split("\t")
        assert parts == ["desc", "platform", "group", "业务", "测试"]

    def test_empty_fields_still_five_parts(self):
        r = StructuredResult("", "", "", "技术", "未知")
        assert len(r.to_tab_row().split("\t")) == 5


# ---------------------------------------------------------------------------
# ResultParser.parse — 标准 JSON
# ---------------------------------------------------------------------------

class TestParseStandardJson:
    def _make_json(self, **kwargs) -> str:
        defaults = {
            "task_desc": "处理客户问题",
            "platform": "微信",
            "group_name": "客户群",
            "ticket_type": "技术",
            "environment": "生产",
        }
        defaults.update(kwargs)
        return json.dumps(defaults, ensure_ascii=False)

    def test_parses_all_fields(self):
        text = self._make_json()
        result = ResultParser.parse(text)
        assert result.task_desc == "处理客户问题"
        assert result.platform == "微信"
        assert result.group_name == "客户群"
        assert result.ticket_type == "技术"
        assert result.environment == "生产"

    def test_all_ticket_types_accepted(self):
        for t in TICKET_TYPES:
            result = ResultParser.parse(self._make_json(ticket_type=t))
            assert result.ticket_type == t

    def test_all_environments_accepted(self):
        for e in ENVIRONMENTS:
            result = ResultParser.parse(self._make_json(environment=e))
            assert result.environment == e


# ---------------------------------------------------------------------------
# ResultParser.parse — markdown 代码块
# ---------------------------------------------------------------------------

class TestParseMarkdownBlock:
    def test_json_in_backtick_block(self):
        text = '```json\n{"task_desc":"test","platform":"钉钉","group_name":"g","ticket_type":"业务","environment":"测试"}\n```'
        result = ResultParser.parse(text)
        assert result.task_desc == "test"
        assert result.platform == "钉钉"
        assert result.ticket_type == "业务"

    def test_json_in_plain_backtick_block(self):
        text = '```\n{"task_desc":"t2","platform":"飞书","group_name":"g2","ticket_type":"排查","environment":"未知"}\n```'
        result = ResultParser.parse(text)
        assert result.ticket_type == "排查"


# ---------------------------------------------------------------------------
# ResultParser.parse — 枚举默认值回退
# ---------------------------------------------------------------------------

class TestEnumFallback:
    def _make_json(self, ticket_type="技术", environment="未知") -> str:
        return json.dumps({
            "task_desc": "x", "platform": "微信", "group_name": "g",
            "ticket_type": ticket_type, "environment": environment,
        }, ensure_ascii=False)

    def test_invalid_ticket_type_falls_back(self):
        result = ResultParser.parse(self._make_json(ticket_type="未知类型"))
        assert result.ticket_type == DEFAULT_TICKET_TYPE

    def test_invalid_environment_falls_back(self):
        result = ResultParser.parse(self._make_json(environment="外网"))
        assert result.environment == DEFAULT_ENVIRONMENT

    def test_missing_ticket_type_falls_back(self):
        data = {"task_desc": "x", "platform": "微信", "group_name": "g", "environment": "生产"}
        result = ResultParser.parse(json.dumps(data))
        assert result.ticket_type == DEFAULT_TICKET_TYPE

    def test_missing_environment_falls_back(self):
        data = {"task_desc": "x", "platform": "微信", "group_name": "g", "ticket_type": "业务"}
        result = ResultParser.parse(json.dumps(data))
        assert result.environment == DEFAULT_ENVIRONMENT


# ---------------------------------------------------------------------------
# ResultParser.parse — 任务描述截断
# ---------------------------------------------------------------------------

class TestTaskDescTruncation:
    def test_long_task_desc_truncated(self):
        long_desc = "字" * 200
        data = {"task_desc": long_desc, "platform": "微信", "group_name": "g",
                "ticket_type": "技术", "environment": "未知"}
        result = ResultParser.parse(json.dumps(data))
        assert len(result.task_desc) <= MAX_TASK_DESC_LEN

    def test_exact_100_chars_not_truncated(self):
        desc = "字" * 100
        data = {"task_desc": desc, "platform": "微信", "group_name": "g",
                "ticket_type": "技术", "environment": "未知"}
        result = ResultParser.parse(json.dumps(data))
        assert len(result.task_desc) == 100


# ---------------------------------------------------------------------------
# ResultParser.parse — 纯文本降级
# ---------------------------------------------------------------------------

class TestPlainTextFallback:
    def test_plain_text_returns_default_enums(self):
        result = ResultParser.parse("这不是 JSON 格式的文本")
        assert result.ticket_type == DEFAULT_TICKET_TYPE
        assert result.environment == DEFAULT_ENVIRONMENT

    def test_plain_text_truncated_to_100(self):
        result = ResultParser.parse("字" * 200)
        assert len(result.task_desc) <= MAX_TASK_DESC_LEN

    def test_empty_string_does_not_crash(self):
        result = ResultParser.parse("")
        assert isinstance(result, StructuredResult)
