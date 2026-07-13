from __future__ import annotations

from pathlib import Path


QML_DIR = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml"


def _qml(name: str) -> str:
    return (QML_DIR / name).read_text(encoding="utf-8")


def test_selectable_text_is_read_only_and_supports_mouse_and_keyboard_selection() -> None:
    qml_text = _qml("SelectableText.qml")

    assert "readOnly: true" in qml_text
    assert "selectByMouse: true" in qml_text
    assert "selectByKeyboard: true" in qml_text
    assert "property alias selectedText: textEdit.selectedText" in qml_text
    assert "textEdit.copy()" in qml_text


def test_detail_field_does_not_cover_display_text_with_an_edit_mouse_area() -> None:
    qml_text = _qml("DetailField.qml")

    assert "sourceComponent: selectableTextComponent" in qml_text
    assert "id: editAction" in qml_text
    assert "onClicked: fieldRoot.clicked()" in qml_text
    assert "enabled: fieldRoot.editable && !fieldRoot.saving && !fieldRoot.actionBusy" not in qml_text
    assert "editableTextComponent" not in qml_text
    assert "HoverHandler" in qml_text


def test_cascade_fields_keep_text_selection_and_move_editing_to_the_action_icon() -> None:
    for file_name in ("SingleSelectCascadeField.qml", "RootCauseCascadeField.qml"):
        qml_text = _qml(file_name)

        display_block = qml_text.split("visible: !rootField.editing", 1)[1].split(
            "ColumnLayout {", 1
        )[0]
        assert "SelectableText" in display_block
        assert "HoverHandler" in display_block
        assert "onClicked: rootField.clicked()" in display_block


def test_project_version_table_uses_selectable_text_for_data_cells() -> None:
    qml_text = _qml("ProjectsSection.qml")
    version_table = qml_text.split("id: projectVersionTableView", 1)[1].split(
        "ColumnLayout {", 1
    )[0]

    assert version_table.count("SelectableText {") == 4
    assert "text: modelData.version || \"未填写\"" in version_table
    assert "wrapMode: TextEdit.NoWrap" in version_table
