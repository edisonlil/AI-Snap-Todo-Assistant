from aica.models import TicketSnapshot, TicketSummaryFields
from aica.ticket_field_resolver import (
    infer_ticket_type,
    normalize_ticket_type,
    resolve_product_line,
)


def test_product_line_preserves_raw_value():
    fields = TicketSummaryFields(product_line="企业微信")

    assert fields.product_line == "企业微信"


def test_resolve_product_line_can_fall_back_to_source_payload():
    assert resolve_product_line(source_payload={"productLine": "文档中台"}) == "文档中台"


def test_normalize_ticket_type_maps_legacy_values():
    assert normalize_ticket_type("技术") == "排查类"
    assert normalize_ticket_type("配置咨询") == "咨询类"
    assert normalize_ticket_type("操作") == "操作类"


def test_infer_ticket_type_from_description():
    assert infer_ticket_type("用户反馈页面报错 500，当前无法提交，需要排查") == "排查类"
    assert infer_ticket_type("请问导出能力是否支持按产品线筛选？") == "咨询类"
    assert infer_ticket_type("麻烦帮忙开通导出权限，并同步下历史数据") == "操作类"


def test_ticket_snapshot_from_dict_preserves_product_line_and_infers_ticket_type():
    snapshot = TicketSnapshot.from_dict(
        {
            "title": "导出失败",
            "product_line": "任意旧值",
            "ticket_type": "",
            "current_summary": "用户反馈导出报错，当前无法下载文件，需要排查原因",
        }
    )

    assert snapshot.fields.product_line == "任意旧值"
    assert snapshot.fields.ticket_type == "排查类"
