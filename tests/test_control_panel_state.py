import json

import pytest

from aica.config import build_default_config
from aica.control_panel_state import (
    build_script_integration,
    load_integration_config,
    persist_control_panel_config,
    replace_script_integrations,
    save_integration_config,
    script_integration_display_path,
    update_script_integration_path,
)


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


def test_build_script_integration_uses_python_launcher_for_py_files(tmp_path):
    script_path = tmp_path / "sync_todo.py"
    script_path.write_text("print('ok')", encoding="utf-8")

    integration = build_script_integration(str(script_path), {"sync-todo"})

    assert integration["id"] == "sync-todo-2"
    assert integration["command"] == "py"
    assert integration["args"] == [str(script_path.resolve())]
    assert integration["cwd"] == str(tmp_path.resolve())
    assert script_integration_display_path(integration) == str(script_path.resolve())


def test_update_script_integration_path_supports_powershell_scripts(tmp_path):
    first_script = tmp_path / "sync_todo.py"
    first_script.write_text("print('ok')", encoding="utf-8")
    second_script = tmp_path / "sync_todo.ps1"
    second_script.write_text("Write-Host ok", encoding="utf-8")

    integration = build_script_integration(str(first_script))
    updated = update_script_integration_path(integration, str(second_script))

    assert updated["command"] == "powershell"
    assert updated["args"] == [
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(second_script.resolve()),
    ]
    assert updated["name"] == "sync_todo"
    assert script_integration_display_path(updated) == str(second_script.resolve())


def test_replace_and_save_script_integrations_preserves_other_entries(tmp_path):
    config_path = tmp_path / "integrations.json"
    save_integration_config(
        config_path,
        {
            "todo_event_integrations": [
                {
                    "id": "webhook-a",
                    "type": "webhook",
                    "url": "https://example.com/hook",
                }
            ]
        },
    )

    script_path = tmp_path / "sync_todo.exe"
    script_path.write_text("", encoding="utf-8")
    updated_payload = replace_script_integrations(
        load_integration_config(config_path),
        [build_script_integration(str(script_path))],
    )
    save_integration_config(config_path, updated_payload)

    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert len(saved["todo_event_integrations"]) == 2
    assert saved["todo_event_integrations"][0]["type"] == "script"
    assert saved["todo_event_integrations"][1]["type"] == "webhook"
