import pytest

from aica.config import build_default_config
from aica.control_panel_state import persist_control_panel_config


class _DummyConfigManager:
    def __init__(self):
        self.saved_config = None
        self.save_calls = 0

    def save(self, config):
        self.saved_config = config
        self.save_calls += 1


def test_persist_control_panel_config_rejects_invalid_binding_without_saving():
    manager = _DummyConfigManager()
    config = build_default_config()
    config.providers[0].api_key = "siliconflow-key"
    config.task_model_bindings.analysis.model_id = "missing-model"

    with pytest.raises(ValueError):
        persist_control_panel_config(
            manager,
            config,
            capture_hotkey="Alt+A",
            max_image_megabytes="4",
        )

    assert manager.save_calls == 0
    assert manager.saved_config is None


def test_persist_control_panel_config_saves_normalized_hotkey():
    manager = _DummyConfigManager()
    config = build_default_config()
    config.providers[0].api_key = "siliconflow-key"

    saved = persist_control_panel_config(
        manager,
        config,
        capture_hotkey="ctrl+shift+a",
        max_image_megabytes="5",
    )

    assert manager.save_calls == 1
    assert saved.hotkeys.capture == "Ctrl+Shift+A"
    assert saved.max_image_bytes == 5 * 1024 * 1024
