"""Helpers for local data and bundled resource paths."""
from __future__ import annotations

import sys
from pathlib import Path


def app_data_dir() -> Path:
    return Path.home() / ".aica"


def config_file() -> Path:
    return app_data_dir() / "config.json"


def prompts_file() -> Path:
    return app_data_dir() / "prompts.json"


def todos_file() -> Path:
    return app_data_dir() / "todos.json"


def todo_bindings_file() -> Path:
    return app_data_dir() / "todo_bindings.json"


def integrations_file() -> Path:
    return app_data_dir() / "integrations.json"


def feedback_dir() -> Path:
    return app_data_dir() / "feedback"


def feedback_images_dir() -> Path:
    return feedback_dir() / "images"


def prompt_history_dir() -> Path:
    return app_data_dir() / "prompt_history"


def error_log_file() -> Path:
    return app_data_dir() / "error.log"


def analysis_metrics_file() -> Path:
    return app_data_dir() / "analysis_metrics.json"


def todo_attachments_dir() -> Path:
    return app_data_dir() / "todo_attachments"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def runtime_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", project_root()))


def qml_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return runtime_root() / "aica" / "qml"
    return Path(__file__).resolve().with_name("qml")


def icon_file() -> Path:
    return runtime_root() / "assets" / "aica_icon.png"
