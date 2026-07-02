from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.config import ConfigManager, build_default_config  # noqa: E402
from aica.theme_controller import ThemeController  # noqa: E402
from aica.theme import ThemeConfig, build_theme_tokens, normalize_color, preset_options  # noqa: E402


def test_theme_config_defaults_when_missing_from_existing_config(tmp_path: Path) -> None:
    payload = asdict(build_default_config())
    payload.pop("theme", None)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    loaded = ConfigManager(str(config_path)).load()

    assert loaded.theme == ThemeConfig()


def test_theme_config_normalizes_hex_colors() -> None:
    theme = ThemeConfig.from_dict(
        {
            "preset_id": "qingyun",
            "base_color": "F5F7FB",
            "accent_color": "1677ff",
        }
    )

    assert theme.base_color == "#F5F7FB"
    assert theme.accent_color == "#1677FF"
    assert normalize_color("not-a-color", "#FFFFFF") == "#FFFFFF"


def test_theme_config_sanitizes_invalid_values() -> None:
    theme = ThemeConfig.from_dict(
        {
            "preset_id": "missing",
            "base_color": "xxx",
            "accent_color": "bad",
            "component_style": "glass",
            "component_radius": 99,
            "component_height": 3,
            "button_radius": 99,
            "button_height": 3,
            "radius_scale": 9,
            "font_scale": 0.1,
            "density": "huge",
        }
    )

    assert theme.preset_id == "default"
    assert theme.base_color == "#FFFFFF"
    assert theme.accent_color == "#2A313F"
    assert theme.component_style == "soft"
    assert theme.component_radius == 32
    assert theme.component_height == 28
    assert theme.button_radius == 32
    assert theme.button_height == 28
    assert theme.radius_scale == 1.4
    assert theme.font_scale == 0.9
    assert theme.density == "comfortable"


def test_theme_tokens_include_base_presets_and_scaled_values() -> None:
    preset_map = {item["id"]: item for item in preset_options()}
    assert preset_map["qingyun"]["baseColor"] == "#F5F7FB"
    assert preset_map["qingyun"]["accentColor"] == "#4F73FF"
    assert preset_map["qingyun"]["auxiliaryColor"] == "#F2F3F5"
    assert preset_map["minimal"]["baseColor"] == "#FAFAFA"
    assert preset_map["minimal"]["accentColor"] == "#20242B"
    assert preset_map["minimal"]["auxiliaryColor"] == "#F1F1F1"
    assert preset_map["sufa"]["baseColor"] == "#FBFAF4"
    assert preset_map["sufa"]["accentColor"] == "#C97933"
    assert preset_map["sufa"]["auxiliaryColor"] == "#F1F0E7"
    assert preset_map["default"]["baseColor"] == "#FFFFFF"
    assert preset_map["default"]["auxiliaryColor"] == "#F1F1F1"

    tokens = build_theme_tokens(
        ThemeConfig(
            preset_id="qingyun",
            base_color="#F5F7FB",
            accent_color="#1677FF",
            component_radius=10,
            component_height=40,
            button_radius=22,
            button_height=42,
            radius_scale=1.25,
            font_scale=1.1,
            density="spacious",
        )
    ).to_dict()

    assert tokens["shellBg"] == "#F5F7FB"
    assert tokens["panelBg"] == "#F5F7FB"
    assert tokens["auxiliaryColor"] == "#F2F3F5"
    assert tokens["panelAltBg"] == "#F2F3F5"
    assert tokens["fieldBg"] == "#F2F3F5"
    assert tokens["timelineBg"] == "#F2F3F5"
    assert tokens["inputBg"] != "#FFFFFF"
    assert tokens["formFieldBg"] == tokens["inputBg"]
    assert tokens["formPopupBg"] != "#FFFFFF"
    assert tokens["buttonDefaultBg"] == tokens["inputBg"]
    assert tokens["accent"] == "#1677FF"
    assert tokens["accentSoft"] != tokens["accent"]
    assert tokens["hoverBg"] != "#F3F4F6"
    assert tokens["buttonRadius"] == 22
    assert tokens["buttonHeight"] == 42
    assert tokens["buttonPaddingH"] >= 14
    assert tokens["buttonFontSize"] == tokens["fontBody"]
    assert tokens["componentRadius"] == 10
    assert tokens["componentHeight"] == 40
    assert tokens["radiusCard"] == 30
    assert tokens["fontBody"] == 13
    assert tokens["spacingMd"] > 12
    assert tokens["formFieldHeight"] == 40
    assert tokens["formFieldRadius"] == 10
    assert tokens["formFieldFontSize"] == tokens["fontBody"]
    assert tokens["formFieldBorder"] == tokens["componentLine"]
    assert tokens["formFieldFocusBorder"] == tokens["accent"]
    assert tokens["formPopupItemHeight"] > 38


def test_theme_tokens_include_form_defaults() -> None:
    tokens = build_theme_tokens(ThemeConfig()).to_dict()

    assert tokens["componentHeight"] == 36
    assert tokens["componentRadius"] == 8
    assert tokens["formFieldHeight"] == 36
    assert tokens["formFieldCompactHeight"] == 28
    assert tokens["formFieldRadius"] == 8
    assert tokens["formFieldPaddingH"] == 12
    assert tokens["formFieldPaddingV"] == 8
    assert tokens["formFieldFontSize"] == 12
    assert tokens["formFieldBg"] == tokens["inputBg"]
    assert tokens["formPopupBg"] == "#FFFFFF"
    assert tokens["formFieldBorder"] == tokens["componentLine"]
    assert tokens["formFieldFocusBorder"] == tokens["accent"]
    assert tokens["formPopupRadius"] == 12
    assert tokens["formPopupItemHeight"] == 36
    assert tokens["formChipHeight"] == 28
    assert tokens["buttonRadius"] == 8
    assert tokens["buttonHeight"] == 36


def test_theme_tokens_fall_back_from_independent_to_common_component_values() -> None:
    tokens = build_theme_tokens(
        {
            "component_radius": 12,
            "component_height": 40,
            "button_radius": 0,
            "button_height": 0,
        }
    ).to_dict()

    assert tokens["componentRadius"] == 12
    assert tokens["componentHeight"] == 40
    assert tokens["formFieldRadius"] == 12
    assert tokens["formFieldHeight"] == 40
    assert tokens["buttonRadius"] == 12
    assert tokens["buttonHeight"] == 40


def test_theme_presets_drive_accent_and_auxiliary_colors() -> None:
    qingyun = ThemeConfig.from_dict({"preset_id": "qingyun", "base_color": "F5F7FB"})
    sufa = ThemeConfig.from_dict({"preset_id": "sufa", "base_color": "FBFAF4"})
    minimal = ThemeConfig.from_dict({"preset_id": "minimal", "base_color": "FAFAFA"})
    default = ThemeConfig.from_dict({"preset_id": "default", "base_color": "FFFFFF"})

    qingyun_tokens = build_theme_tokens(qingyun).to_dict()
    sufa_tokens = build_theme_tokens(sufa).to_dict()
    minimal_tokens = build_theme_tokens(minimal).to_dict()
    default_tokens = build_theme_tokens(default).to_dict()

    assert qingyun.accent_color == "#4F73FF"
    assert sufa.accent_color == "#C97933"
    assert qingyun_tokens["accent"] == "#4F73FF"
    assert sufa_tokens["accent"] == "#C97933"
    assert qingyun_tokens["auxiliaryColor"] == "#F2F3F5"
    assert sufa_tokens["auxiliaryColor"] == "#F1F0E7"
    assert minimal_tokens["auxiliaryColor"] == "#F1F1F1"
    assert default_tokens["auxiliaryColor"] == "#F1F1F1"
    assert qingyun_tokens["panelAltBg"] == "#F2F3F5"
    assert sufa_tokens["panelAltBg"] == "#F1F0E7"
    assert minimal_tokens["panelAltBg"] == "#F1F1F1"
    assert default_tokens["panelAltBg"] == "#F1F1F1"
    assert qingyun_tokens["accentSoft"] != sufa_tokens["accentSoft"]
    assert qingyun_tokens["accentTint"] != sufa_tokens["accentTint"]
    assert qingyun_tokens["accentHover"] != sufa_tokens["accentHover"]


def test_theme_is_saved_to_config_json(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    manager = ConfigManager(str(config_path))
    config = manager.load()
    config.theme = ThemeConfig.from_dict(
        {
            "preset_id": "sufa",
            "base_color": "FBFAF4",
            "accent_color": "3355AA",
            "component_radius": 9,
            "component_height": 34,
            "button_radius": 22,
            "button_height": 36,
            "density": "compact",
        }
    )

    manager.save(config)
    payload = json.loads(config_path.read_text(encoding="utf-8"))

    assert payload["theme"]["preset_id"] == "sufa"
    assert payload["theme"]["base_color"] == "#FBFAF4"
    assert payload["theme"]["accent_color"] == "#3355AA"
    loaded_theme = ConfigManager(str(config_path)).load().theme
    assert loaded_theme.density == "compact"
    assert loaded_theme.component_radius == 9
    assert loaded_theme.component_height == 34
    assert loaded_theme.button_radius == 22
    assert loaded_theme.button_height == 36


def test_theme_controller_skips_deleted_qml_contexts() -> None:
    class _DeletedContext:
        def setContextProperty(self, *_args, **_kwargs):
            raise RuntimeError("wrapped C/C++ object of type QQmlContext has been deleted")

    controller = ThemeController()
    deleted = _DeletedContext()
    controller._contexts.append(deleted)  # type: ignore[attr-defined]

    controller.set_config(ThemeConfig.from_dict({"preset_id": "qingyun"}))

    assert controller._contexts == []  # type: ignore[attr-defined]


def test_key_qml_windows_consume_theme_tokens() -> None:
    qml_dir = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml"
    key_files = [
        "ControlPanel.qml",
        "TodoPanel.qml",
        "TodoDetailPanel.qml",
        "AssistTroubleshootingWindow.qml",
        "StageSummaryWindow.qml",
        "ResultDialog.qml",
        "FeedbackPanel.qml",
        "AppNotificationWindow.qml",
        "AppNotificationCenter.qml",
    ]

    for file_name in key_files:
        source = (qml_dir / file_name).read_text(encoding="utf-8")
        assert "theme" in source, file_name
        assert any(token in source for token in ("themeTokens", "property var theme", "theme:")), file_name


def test_control_panel_theme_color_uses_segmented_slider_without_unimplemented_modes() -> None:
    source = (Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "ControlPanel.qml").read_text(
        encoding="utf-8"
    )

    assert "主题选择" not in source
    assert "浅色" not in source
    assert "深色" not in source
    assert "跟随系统" not in source
    assert "selectedIndex" in source
    assert "modelData.accentColor" in source
    assert "implicitHeight: providerForm.implicitHeight + 40" in source
    assert "implicitHeight: taskBindingColumn.implicitHeight + 40" in source
    assert "color: root.panelAltBg" in source
    assert 'text: "通用组件样式"' in source
    assert 'tokenPath: "component.Common.radius"' in source
    assert 'tokenPath: "component.Common.height"' in source
    assert 'text: "按钮样式"' in source
    assert 'text: "主按钮背景"' not in source
    assert 'text: "主按钮悬停"' not in source
    assert 'text: "主按钮按下"' not in source
    assert 'tokenPath: "component.Button.radius"' in source
    assert 'tokenPath: "component.Button.height"' in source
    assert "controlPanelBridge.themeConfig.button_radius || 8" in source
    assert "controlPanelBridge.themeConfig.button_height || 36" in source
    assert 'component PixelInput: ControlPanelPixelInput' in source
    assert 'controlPanelBridge.updateThemeNumberField("component_radius", value)' in source
    assert 'controlPanelBridge.updateThemeNumberField("component_height", value)' in source
    assert 'controlPanelBridge.updateThemeNumberField("button_radius", value)' in source
    assert 'controlPanelBridge.updateThemeNumberField("button_height", value)' in source


def test_control_panel_navigation_selection_uses_compact_rect_style() -> None:
    source = (Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "ControlPanel.qml").read_text(
        encoding="utf-8"
    )

    assert "readonly property bool selected: root.currentSection === modelData.id" in source
    assert "Layout.preferredHeight: 40" in source
    assert "radius: 6" in source
    assert 'color: selected || navItemMouse.containsMouse ? root.accentSoft : "transparent"' in source
    assert "color: selected || navItemMouse.containsMouse ? root.accent : root.titleInk" in source
    assert "font.pixelSize: 13" in source
