import json

from aica.config import ConfigManager, build_default_config, default_task_model_bindings


def test_load_migrates_legacy_schema(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "api_key": "legacy-key",
                "model": "legacy/vision",
                "title_generation_model": "legacy/title",
                "plan_export_model": "legacy/plan",
                "api_base_url": "https://legacy.example/v1/chat/completions",
                "timeout_seconds": 45,
                "max_image_bytes": 2048,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manager = ConfigManager(str(config_file))
    config = manager.load()

    assert config.providers[0].api_key == "legacy-key"
    assert config.providers[0].base_url == "https://legacy.example/v1/chat/completions"
    assert config.task_model_bindings.analysis.model_id == "analysis-model"
    assert config.task_model_bindings.title_generation.model_id == "title-model"
    assert config.task_model_bindings.plan_export.model_id == "plan-export-model"
    persisted = json.loads(config_file.read_text(encoding="utf-8"))
    assert "providers" in persisted
    assert "api_key" not in persisted


def test_default_config_includes_minmax_provider():
    config = build_default_config()

    minmax = next((provider for provider in config.providers if provider.id == "minmax"), None)
    assert minmax is not None
    assert minmax.kind == "openai_compatible"
    assert minmax.base_url == "https://api.minimax.io/v1/chat/completions"
    assert [model.id for model in minmax.models] == ["minimax-m2-5", "minimax-m2-5-highspeed"]


def test_minmax_default_bindings_keep_vision_tasks_on_vision_model():
    bindings = default_task_model_bindings("minmax")

    assert bindings.analysis.provider_id == "siliconflow"
    assert bindings.analysis.model_id == "qwen25-vl-72b"
    assert bindings.title_generation.provider_id == "minmax"
    assert bindings.title_generation.model_id == "minimax-m2-5"
    assert bindings.plan_export.provider_id == "siliconflow"
    assert bindings.prompt_optimization.provider_id == "siliconflow"
