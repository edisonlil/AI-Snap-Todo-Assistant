from __future__ import annotations

from pathlib import Path


QML_DIR = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml"


def _qml(file_name: str) -> str:
    return (QML_DIR / file_name).read_text(encoding="utf-8")


def test_project_list_uses_page_runtime_without_migrating_detail_form() -> None:
    qml_text = _qml("ProjectsSection.qml")

    assert "PageRuntime {" in qml_text
    assert "filterContent: RowLayout" in qml_text
    assert "actionContent: RowLayout" in qml_text
    assert "listContent: RowLayout" in qml_text
    assert "visible: theme.projectViewMode === \"list\"" in qml_text
    assert "visible: theme.projectViewMode === \"detail\"" in qml_text
    assert qml_text.index("PageRuntime {") < qml_text.index("visible: theme.projectViewMode === \"detail\"")


def test_environment_list_uses_page_runtime_without_migrating_detail_manager() -> None:
    qml_text = _qml("EnvironmentsSection.qml")

    assert "PageRuntime {" in qml_text
    assert "filterContent: ColumnLayout" in qml_text
    assert "actionContent: RowLayout" in qml_text
    assert "listContent: Item" in qml_text
    assert "listFramed: false" in qml_text
    assert "Flickable {" in qml_text
    assert "GridLayout {" in qml_text
    assert "id: environmentGrid" in qml_text
    assert "readonly property int gridColumns: width >= 1076 ? 4 : (width >= 796 ? 3 : (width >= 532 ? 2 : 1))" in qml_text
    assert "readonly property real gridCardWidth" in qml_text
    assert "visible: root.environmentViewMode === \"list\"" in qml_text
    assert "EnvironmentManagerSection {" in qml_text
    assert qml_text.index("PageRuntime {") < qml_text.index("EnvironmentManagerSection {")


def test_control_panel_settings_pages_keep_native_layouts() -> None:
    qml_text = _qml("ControlPanel.qml")

    assert "PageRuntime {" not in qml_text
    assert 'visible: root.currentSection === "models"' in qml_text
    assert 'visible: root.currentSection === "theme"' in qml_text
    assert 'visible: root.currentSection === "analysis_rules"' in qml_text
