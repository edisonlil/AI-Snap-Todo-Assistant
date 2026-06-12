"""Theme configuration and token derivation."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from aica.runtime import RUNTIME_CAPABILITIES


DEFAULT_ACCENT_COLOR = "#2A313F"
DEFAULT_COMPONENT_STYLE = "soft"
DEFAULT_DENSITY = "comfortable"

COMPONENT_STYLES = frozenset({"soft", "outlined", "flat"})
DENSITIES = frozenset({"compact", "comfortable", "spacious"})

THEME_PRESETS: dict[str, dict[str, str]] = {
    "default": {
        "label": "默认",
        "base_color": "#FFFFFF",
        "accent_color": "#2A313F",
        "auxiliary_color": "#F1F1F1",
    },
    "qingyun": {
        "label": "青云",
        "base_color": "#F5F7FB",
        "accent_color": "#4F73FF",
        "auxiliary_color": "#F2F3F5",
    },
    "minimal": {
        "label": "极简",
        "base_color": "#FAFAFA",
        "accent_color": "#20242B",
        "auxiliary_color": "#F1F1F1",
    },
    "sufa": {
        "label": "素笺",
        "base_color": "#FBFAF4",
        "accent_color": "#C97933",
        "auxiliary_color": "#F1F0E7",
    },
}

_HEX_COLOR_PATTERN = re.compile(r"^#?[0-9A-Fa-f]{6}$")


@dataclass
class ThemeConfig:
    preset_id: str = "default"
    base_color: str = "#FFFFFF"
    accent_color: str = DEFAULT_ACCENT_COLOR
    component_style: str = DEFAULT_COMPONENT_STYLE
    component_radius: int = 8
    component_height: int = 36
    button_radius: int = 6
    button_height: int = 35
    radius_scale: float = 1.0
    font_scale: float = 1.0
    font_size_px: int = 12
    density: str = DEFAULT_DENSITY
    font_family: str = ""

    @classmethod
    def from_dict(cls, data: object) -> "ThemeConfig":
        if not isinstance(data, dict):
            return cls()

        preset_id = str(data.get("preset_id", "default")).strip() or "default"
        if preset_id not in THEME_PRESETS:
            preset_id = "default"

        preset_base = THEME_PRESETS[preset_id]["base_color"]
        raw_base_color = data.get("base_color", preset_base)
        preset_accent = THEME_PRESETS[preset_id]["accent_color"]
        raw_accent_color = data.get("accent_color", preset_accent)
        component_style = str(data.get("component_style", DEFAULT_COMPONENT_STYLE)).strip()
        density = str(data.get("density", DEFAULT_DENSITY)).strip()

        return cls(
            preset_id=preset_id,
            base_color=normalize_color(raw_base_color, preset_base),
            accent_color=normalize_color(raw_accent_color, preset_accent),
            component_style=component_style if component_style in COMPONENT_STYLES else DEFAULT_COMPONENT_STYLE,
            component_radius=_clamp_optional_int(data.get("component_radius"), 4, 32, 8),
            component_height=_clamp_optional_int(data.get("component_height"), 28, 56, 36),
            button_radius=_clamp_optional_int(data.get("button_radius"), 4, 32, 6),
            button_height=_clamp_optional_int(data.get("button_height"), 28, 56, 35),
            radius_scale=_clamp_float(data.get("radius_scale"), 0.75, 1.4, 1.0),
            font_scale=_clamp_float(data.get("font_scale"), 0.9, 1.15, 1.0),
            font_size_px=_clamp_int(data.get("font_size_px"), 11, 18, _font_size_default(data.get("font_scale"))),
            density=density if density in DENSITIES else DEFAULT_DENSITY,
            font_family=str(data.get("font_family", "") or "").strip(),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ThemeTokens:
    values: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return dict(self.values)


def normalize_color(value: object, default: str = "#FFFFFF") -> str:
    text = str(value or "").strip()
    if not _HEX_COLOR_PATTERN.match(text):
        return default.upper()
    if not text.startswith("#"):
        text = f"#{text}"
    return text.upper()


def preset_options() -> list[dict[str, str]]:
    return [
        {
            "id": preset_id,
            "label": preset["label"],
            "value": preset_id,
            "text": preset["label"],
            "baseColor": preset["base_color"],
            "accentColor": preset["accent_color"],
            "auxiliaryColor": preset["auxiliary_color"],
        }
        for preset_id, preset in THEME_PRESETS.items()
    ]


def component_style_options() -> list[dict[str, str]]:
    return [
        {"id": "soft", "label": "柔和", "value": "soft", "text": "柔和"},
        {"id": "outlined", "label": "描边", "value": "outlined", "text": "描边"},
        {"id": "flat", "label": "扁平", "value": "flat", "text": "扁平"},
    ]


def density_options() -> list[dict[str, str]]:
    return [
        {"id": "compact", "label": "紧凑", "value": "compact", "text": "紧凑"},
        {"id": "comfortable", "label": "舒适", "value": "comfortable", "text": "舒适"},
        {"id": "spacious", "label": "宽松", "value": "spacious", "text": "宽松"},
    ]


def build_theme_tokens(config: ThemeConfig | object | None = None) -> ThemeTokens:
    theme = config if isinstance(config, ThemeConfig) else ThemeConfig.from_dict(config)
    base = theme.base_color
    accent = theme.accent_color
    font_family = theme.font_family or RUNTIME_CAPABILITIES.ui_font
    font_css = _font_css(theme.font_family)
    mono_font_css = RUNTIME_CAPABILITIES.monospace_font_css
    font_body = int(theme.font_size_px)
    if theme.font_size_px == 12 and theme.font_scale != 1.0:
        font_body = _font_size_default(theme.font_scale)
    density_scale = {"compact": 0.88, "comfortable": 1.0, "spacious": 1.14}[theme.density]
    preset = THEME_PRESETS.get(theme.preset_id, THEME_PRESETS["default"])
    auxiliary_color = normalize_color(preset.get("auxiliary_color"), "#F1F1F1")
    line_color = _mix(base, "#D0D5DD", 0.72)
    panel_alt = auxiliary_color
    hover = _mix(base, "#EAECF0", 0.68)
    pressed = _mix(base, "#DDE2EA", 0.64)
    accent_soft = _mix(base, accent, 0.1)
    accent_tint = _mix(base, accent, 0.16)
    component_line = "transparent" if theme.component_style == "flat" else line_color
    component_fill = panel_alt if theme.component_style == "soft" else base
    fallback_component_height = _scale_int(36, density_scale)
    fallback_component_radius = _scale_int(8, theme.radius_scale)
    component_height = max(0, int(theme.component_height)) or fallback_component_height
    component_radius = max(0, int(theme.component_radius)) or fallback_component_radius
    form_field_height = component_height
    form_field_compact_height = _scale_int(28, density_scale)
    form_popup_item_height = max(32, component_height)
    form_chip_height = _scale_int(28, density_scale)
    button_primary_bg = accent
    button_primary_bg_hover = _mix(button_primary_bg, "#000000", 0.1)
    button_primary_bg_pressed = _mix(button_primary_bg, "#000000", 0.18)
    button_height = max(0, int(theme.button_height)) or component_height
    button_radius = max(0, int(theme.button_radius)) or component_radius

    tokens: dict[str, object] = {
        "presetId": theme.preset_id,
        "baseColor": base,
        "auxiliaryColor": auxiliary_color,
        "shellBg": base,
        "panelBg": base,
        "panelAltBg": panel_alt,
        "navIdle": panel_alt,
        "inputBg": "#FFFFFF",
        "fieldBg": panel_alt,
        "timelineBg": panel_alt,
        "panelLine": component_line,
        "fieldLine": line_color,
        "sectionLine": line_color,
        "titleInk": "#18202E",
        "bodyInk": "#4A5565",
        "labelInk": "#7C8795",
        "mutedInk": "#A9B1BD",
        "accent": accent,
        "accentSoft": accent_soft,
        "accentTint": accent_tint,
        "accentHover": _mix(accent, "#000000", 0.1),
        "accentPressed": _mix(accent, "#000000", 0.18),
        "accentInk": "#FFFFFF",
        "buttonPrimaryBg": button_primary_bg,
        "buttonPrimaryBgHover": button_primary_bg_hover,
        "buttonPrimaryBgPressed": button_primary_bg_pressed,
        "buttonPrimaryInk": "#FFFFFF",
        "buttonDefaultBg": "#FFFFFF",
        "buttonDefaultBgHover": hover,
        "buttonDefaultBgPressed": pressed,
        "buttonDefaultInk": "#4A5565",
        "buttonDisabledBg": _mix(base, "#EAECF0", 0.74),
        "buttonDisabledInk": "#98A2B3",
        "buttonBorder": component_line,
        "buttonRadius": button_radius,
        "buttonHeight": button_height,
        "buttonPaddingH": _scale_int(12, density_scale),
        "buttonFontSize": font_body,
        "hoverBg": hover,
        "pressedBg": pressed,
        "componentBg": component_fill,
        "componentLine": component_line,
        "componentRadius": component_radius,
        "componentHeight": component_height,
        "formFieldHeight": form_field_height,
        "formFieldCompactHeight": form_field_compact_height,
        "formFieldRadius": component_radius,
        "formFieldCompactRadius": max(4, min(component_radius, _scale_int(6, theme.radius_scale))),
        "formFieldPaddingH": _scale_int(12, density_scale),
        "formFieldPaddingV": _scale_int(8, density_scale),
        "formFieldCompactPaddingH": _scale_int(8, density_scale),
        "formFieldFontSize": font_body,
        "formFieldCompactFontSize": font_body + 1,
        "formFieldBg": "#FFFFFF",
        "formFieldBorder": component_line,
        "formFieldFocusBorder": accent,
        "formFieldPlaceholderInk": "#7C8795",
        "formPopupRadius": _scale_int(12, theme.radius_scale),
        "formPopupItemRadius": _scale_int(8, theme.radius_scale),
        "formPopupItemHeight": form_popup_item_height,
        "formPopupBg": "#FFFFFF",
        "formPopupHoverBg": hover,
        "formInlineEditHeight": form_field_compact_height,
        "formChipHeight": form_chip_height,
        "formChipRadius": _scale_int(14, theme.radius_scale),
        "formCheckSpacing": _scale_int(8, density_scale),
        "errorBg": "#FDECEC",
        "errorInk": "#B42318",
        "warningBg": "#F4EEE4",
        "warningInk": "#9A4B00",
        "successBg": "#E7F5ED",
        "successInk": "#17663A",
        "uiFont": font_family,
        "widgetFontCss": font_css,
        "monospaceFontCss": mono_font_css,
        "fontTiny": max(9, font_body - 2),
        "fontCaption": max(10, font_body - 1),
        "fontBody": font_body,
        "fontBodyLg": font_body + 1,
        "fontSection": font_body + 3,
        "fontTitle": font_body + 6,
        "fontHero": font_body + 8,
        "fontScale": theme.font_scale,
        "fontSizePx": font_body,
        "radiusXs": _scale_int(4, theme.radius_scale),
        "radiusSm": _scale_int(8, theme.radius_scale),
        "radiusMd": _scale_int(12, theme.radius_scale),
        "radiusLg": _scale_int(16, theme.radius_scale),
        "radiusCard": _scale_int(24, theme.radius_scale),
        "radiusPanel": _scale_int(26, theme.radius_scale),
        "radiusPill": 999,
        "radiusScale": theme.radius_scale,
        "spacingXs": _scale_int(4, density_scale),
        "spacingSm": _scale_int(8, density_scale),
        "spacingMd": _scale_int(12, density_scale),
        "spacingLg": _scale_int(16, density_scale),
        "spacingXl": _scale_int(20, density_scale),
        "density": theme.density,
        "componentStyle": theme.component_style,
        "overlayTextBg": _rgba("#FFFFFF", 242),
        "overlaySelectionBg": _rgba(accent, 46),
        "toolbarBg": _rgba("#FFFFFF", 244),
        "toolbarPanelBg": _rgba("#FFFFFF", 248),
        "subtleInkAlpha": _rgba("#6B7280", 128),
    }
    return ThemeTokens(tokens)


def _clamp_float(value: object, minimum: float, maximum: float, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, minimum), maximum)


def _clamp_int(value: object, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return min(max(parsed, minimum), maximum)


def _clamp_optional_int(value: object, minimum: int, maximum: int, default: int) -> int:
    text = "" if value is None else str(value).strip()
    if not text:
        return default
    if text == "0":
        return 0
    return _clamp_int(text, minimum, maximum, default)


def _font_size_default(font_scale: object) -> int:
    return _scale_int(12, _clamp_float(font_scale, 0.9, 1.15, 1.0))


def _scale_int(value: int, scale: float) -> int:
    return max(1, int(round(value * scale)))


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    normalized = normalize_color(value)
    return (
        int(normalized[1:3], 16),
        int(normalized[3:5], 16),
        int(normalized[5:7], 16),
    )


def _mix(color_a: str, color_b: str, amount_b: float) -> str:
    amount = min(max(float(amount_b), 0.0), 1.0)
    ar, ag, ab = _hex_to_rgb(color_a)
    br, bg, bb = _hex_to_rgb(color_b)
    return "#%02X%02X%02X" % (
        round(ar * (1 - amount) + br * amount),
        round(ag * (1 - amount) + bg * amount),
        round(ab * (1 - amount) + bb * amount),
    )


def _rgba(color: str, alpha: int) -> str:
    r, g, b = _hex_to_rgb(color)
    return f"rgba({r}, {g}, {b}, {max(0, min(255, int(alpha)))})"


def _font_css(font_family: str) -> str:
    if not font_family:
        return RUNTIME_CAPABILITIES.widget_font_css
    escaped = font_family.replace("'", "\\'")
    return f"'{escaped}', {RUNTIME_CAPABILITIES.widget_font_css}"
