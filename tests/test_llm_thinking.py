from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.config import (
    AppConfig,
    ProviderConfig,
    ProviderModelConfig,
    TaskModelBinding,
    TaskModelBindings,
)
from aica.llm import service as llm_service_module
from aica.llm.service import LLMService, strip_thinking_blocks
from aica.llm.types import Message, ProviderResponse


class _StubProvider:
    def __init__(self, text: str):
        self._text = text

    def generate(self, **_kwargs):  # noqa: ANN001
        return ProviderResponse(text=self._text, attempts=1)


def _config() -> AppConfig:
    return AppConfig(
        default_provider_id="stub",
        providers=[
            ProviderConfig(
                id="stub",
                kind="openai_compatible",
                name="Stub",
                api_key="key",
                base_url="https://example.com",
                models=[ProviderModelConfig(id="model", name="model", capabilities=["vision_chat", "text_chat"])],
            )
        ],
        task_model_bindings=TaskModelBindings(
            analysis=TaskModelBinding(provider_id="stub", model_id="model"),
            log_analysis=TaskModelBinding(provider_id="stub", model_id="model"),
            plan_export=TaskModelBinding(provider_id="stub", model_id="model"),
            context_summary=TaskModelBinding(provider_id="stub", model_id="model"),
        ),
    )


def test_strip_thinking_blocks_removes_closed_and_unclosed_tags() -> None:
    text = "前文\n<think>\n推理过程\n</think>\n答案\n<THINK>未闭合"

    assert strip_thinking_blocks(text) == "前文\n\n答案"


def test_llm_service_strips_thinking_by_default(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        llm_service_module,
        "create_provider",
        lambda _kind: _StubProvider("<think>过程</think>\n最终答案"),
    )

    result = LLMService(_config()).run_task("context_summary", messages=[Message(role="user", content="hi")])

    assert result == "最终答案"


def test_llm_service_keeps_thinking_when_explicitly_requested(monkeypatch) -> None:  # noqa: ANN001
    raw = "<think>过程</think>\n最终答案"
    monkeypatch.setattr(llm_service_module, "create_provider", lambda _kind: _StubProvider(raw))

    result = LLMService(_config()).run_task(
        "context_summary",
        messages=[Message(role="user", content="hi")],
        include_thinking=True,
    )

    assert result == raw


def test_llm_service_detailed_keeps_thinking_when_explicitly_requested(monkeypatch) -> None:  # noqa: ANN001
    raw = "<think>过程</think>\n最终答案"
    monkeypatch.setattr(llm_service_module, "create_provider", lambda _kind: _StubProvider(raw))

    result = LLMService(_config()).run_task_detailed(
        "context_summary",
        messages=[Message(role="user", content="hi")],
        include_thinking=True,
    )

    assert result.text == raw
