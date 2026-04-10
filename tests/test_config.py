from dataclasses import asdict

from aica.config import (
    DEFAULT_CAPTURE_HOTKEY,
    ProviderModelConfig,
    _app_config_from_dict,
    _migrate_legacy_config,
    build_default_config,
    default_task_model_bindings,
)


def test_load_migrates_legacy_schema():
    config = _migrate_legacy_config(
        {
            "api_key": "legacy-key",
            "model": "legacy/vision",
            "title_generation_model": "legacy/title",
            "plan_export_model": "legacy/plan",
            "api_base_url": "https://legacy.example/v1/chat/completions",
            "timeout_seconds": 45,
            "max_image_bytes": 2048,
        }
    )

    assert config.providers[0].api_key == "legacy-key"
    assert config.providers[0].base_url == "https://legacy.example/v1/chat/completions"
    assert config.task_model_bindings.analysis.model_id == "analysis-model"
    assert config.task_model_bindings.plan_export.model_id == "plan-export-model"
    assert config.hotkeys.capture == DEFAULT_CAPTURE_HOTKEY
    persisted = asdict(config)
    assert "providers" in persisted
    assert "hotkeys" in persisted
    assert persisted["hotkeys"]["capture"] == DEFAULT_CAPTURE_HOTKEY
    assert "title_generation" not in persisted["task_model_bindings"]


def test_default_config_includes_minmax_provider():
    config = build_default_config()

    minmax = next((provider for provider in config.providers if provider.id == "minmax"), None)
    assert minmax is not None
    assert minmax.kind == "openai_compatible"
    assert minmax.base_url == "https://api.minimax.io/v1/chat/completions"
    assert [model.id for model in minmax.models] == ["minimax-m2-5", "minimax-m2-5-highspeed"]


def test_default_config_includes_dashscope_provider():
    config = build_default_config()

    dashscope = next((provider for provider in config.providers if provider.id == "dashscope"), None)
    assert dashscope is not None
    assert dashscope.kind == "openai_compatible"
    assert dashscope.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    assert [model.id for model in dashscope.models] == ["qwen-vl-max-latest", "qwen-plus-latest"]


def test_minmax_default_bindings_keep_vision_tasks_on_vision_model():
    bindings = default_task_model_bindings("minmax")

    assert bindings.analysis.provider_id == "siliconflow"
    assert bindings.analysis.model_id == "qwen25-vl-72b"
    assert bindings.plan_export.provider_id == "siliconflow"
    assert bindings.prompt_optimization.provider_id == "siliconflow"


def test_dashscope_default_bindings_use_dashscope_vision_model():
    bindings = default_task_model_bindings("dashscope")

    assert bindings.analysis.provider_id == "dashscope"
    assert bindings.analysis.model_id == "qwen-vl-max-latest"
    assert bindings.plan_export.provider_id == "dashscope"
    assert bindings.prompt_optimization.provider_id == "dashscope"


def test_save_and_reload_preserves_hotkey_and_image_limit():
    config = build_default_config()
    config.hotkeys.capture = "Ctrl+Shift+A"
    config.max_image_bytes = 6 * 1024 * 1024

    reloaded = _app_config_from_dict(asdict(config))

    assert reloaded.hotkeys.capture == "Ctrl+Shift+A"
    assert reloaded.max_image_bytes == 6 * 1024 * 1024


def test_save_and_reload_preserves_custom_provider_models():
    config = build_default_config()
    config.providers[0].models.append(
        ProviderModelConfig(
            id="deepseek-ai/deepseek-vl2",
            name="deepseek-ai/deepseek-vl2",
            capabilities=["vision_chat", "text_chat"],
        )
    )

    reloaded = _app_config_from_dict(asdict(config))
    siliconflow = next(provider for provider in reloaded.providers if provider.id == "siliconflow")

    assert any(model.id == "deepseek-ai/deepseek-vl2" for model in siliconflow.models)
