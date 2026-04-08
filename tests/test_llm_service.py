from aica.config import AppConfig, ProviderConfig, ProviderModelConfig, TaskModelBinding, TaskModelBindings
from aica.llm.service import LLMService, ModelResolutionError


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
            title_generation=TaskModelBinding(provider_id="gemini", model_id="flash"),
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
