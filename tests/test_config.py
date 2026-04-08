import json

from aica.config import ConfigManager


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
