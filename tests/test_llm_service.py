from aica.config import AppConfig, ProviderConfig, ProviderModelConfig, TaskModelBinding, TaskModelBindings
from aica.llm.service import LLMService, ModelResolutionError
from aica.llm.types import Message, ProviderResponse


def _config() -> AppConfig:
    return AppConfig(
        default_provider_id="gemini",
        providers=[
            ProviderConfig(
                id="gemini",
                kind="gemini",
                name="Google Gemini",
                api_key="gemini-key",
                models=[
                    ProviderModelConfig(id="flash", name="gemini-2.5-flash", capabilities=["vision_chat", "text_chat"]),
                ],
            ),
        ],
        task_model_bindings=TaskModelBindings(
            analysis=TaskModelBinding(provider_id="gemini", model_id="flash"),
            plan_export=TaskModelBinding(provider_id="gemini", model_id="flash"),
            prompt_optimization=TaskModelBinding(provider_id="gemini", model_id="flash"),
        ),
    )


def test_resolve_task_model_returns_display_name():
    service = LLMService(_config())

    assert service.describe_task_model("analysis") == "Google Gemini / gemini-2.5-flash"


def test_resolve_task_model_rejects_capability_mismatch():
    config = _config()
    config.providers[0].models[0].capabilities = ["text_chat"]
    service = LLMService(config)

    try:
        service.resolve_task_model("analysis")
    except ModelResolutionError as exc:
        assert "vision_chat" in str(exc)
    else:
        raise AssertionError("expected ModelResolutionError")


def test_run_task_detailed_uses_single_attempt_for_analysis(monkeypatch):
    calls = []

    class _Provider:
        def generate(self, **kwargs):
            calls.append(kwargs["max_attempts"])
            return ProviderResponse(text="ok", attempts=1)

    monkeypatch.setattr("aica.llm.service.create_provider", lambda _kind: _Provider())
    service = LLMService(_config())

    result = service.run_task_detailed(
        "analysis",
        messages=[Message(role="user", content="ping")],
        timeout=12,
    )

    assert calls == [1]
    assert result.text == "ok"
    assert result.attempts == 1
    assert result.reference.model_name == "gemini-2.5-flash"


def test_run_task_detailed_keeps_retries_for_background_tasks(monkeypatch):
    calls = []

    class _Provider:
        def generate(self, **kwargs):
            calls.append(kwargs["max_attempts"])
            return ProviderResponse(text="ok", attempts=2)

    monkeypatch.setattr("aica.llm.service.create_provider", lambda _kind: _Provider())
    service = LLMService(_config())

    result = service.run_task_detailed(
        "plan_export",
        messages=[Message(role="user", content="ping")],
        timeout=12,
    )

    assert calls == [3]
    assert result.attempts == 2
