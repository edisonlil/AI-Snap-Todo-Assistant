from pathlib import Path

import aica.paths as path_helpers
from aica.config import ConfigManager


def test_storage_paths_use_locator_file(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr(path_helpers.Path, "home", lambda: home_dir)

    saved = path_helpers.save_storage_paths(
        data_dir=str(tmp_path / "data_drive" / "aica"),
        log_dir=str(tmp_path / "log_drive" / "aica_logs"),
    )

    assert saved.data_dir == tmp_path / "data_drive" / "aica"
    assert saved.log_dir == tmp_path / "log_drive" / "aica_logs"
    assert path_helpers.app_data_dir() == saved.data_dir
    assert path_helpers.aica_database_file() == saved.data_dir / "aica.db"
    assert path_helpers.error_log_file() == saved.log_dir / "error.log"
    assert path_helpers.storage_config_file() == home_dir / ".aica" / "storage.json"


def test_config_manager_default_path_follows_updated_storage_dir(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr(path_helpers.Path, "home", lambda: home_dir)

    path_helpers.save_storage_paths(data_dir=str(tmp_path / "custom_data"), log_dir=str(tmp_path / "custom_logs"))

    manager = ConfigManager()

    assert Path(manager.path) == tmp_path / "custom_data" / "config.json"
