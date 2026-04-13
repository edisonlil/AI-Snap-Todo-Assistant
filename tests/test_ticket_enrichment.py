from aica.models import TicketSummaryFields
from aica.ticket_enrichment import FeaturePointResult, TicketEnrichmentService


class _Provider:
    def resolve(self, *, product_line: str, problem_desc: str) -> FeaturePointResult:
        assert product_line == "Docs"
        assert problem_desc == "导出失败"
        return FeaturePointResult(value="导出模块", matched=True, provider_name="test")


class _LLMService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run_task(self, task_name, *, messages, temperature=0.3, timeout=None):
        self.calls.append(messages[0].content)
        if "总结一句简洁的根因描述" in messages[0].content:
            return "接口参数错误"
        return "配置问题/配置项缺失"


def test_ticket_enrichment_service_populates_auto_fields():
    llm_service = _LLMService()
    service = TicketEnrichmentService(feature_point_provider=_Provider(), llm_service=llm_service)

    outcome = service.enrich_for_update(
        previous_fields=TicketSummaryFields(product_line="Docs"),
        current_fields=TicketSummaryFields(product_line="Docs"),
        previous_problem_desc="",
        current_problem_desc="导出失败",
        previous_conclusion="",
        current_conclusion="确认是生产配置缺失",
    )

    assert outcome.summary_fields.feature_point == "导出模块"
    assert outcome.summary_fields.feature_point_source == "auto"
    assert outcome.summary_fields.root_cause_desc == "接口参数错误"
    assert outcome.summary_fields.root_cause_desc_source == "auto"
    assert outcome.summary_fields.root_cause == "配置问题/配置项缺失"
    assert outcome.summary_fields.root_cause_source == "auto"
    assert outcome.errors == []
