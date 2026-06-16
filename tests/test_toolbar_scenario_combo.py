"""Regression tests for the floating toolbar's scenario dropdown.

The dropdown is implemented as a QToolButton + QMenu so that it renders
as a real menu (with proper item states, anchors, and a caret) rather
than a Qt-internal QComboBox pop-up. These tests pin down the structural
contract: the trigger button + menu widget setup, the stylesheet rules,
the per-action tooltips, and the selection state plumbing.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.analysis.intent import SCENE_OPTIONS  # noqa: E402
from aica.toolbar import _HIDDEN_SCENARIOS, _SCENARIO_TOOLTIPS  # noqa: E402


TOOLBAR_PATH = Path(__file__).resolve().parents[1] / "src" / "aica" / "toolbar.py"


@pytest.fixture(scope="session")
def qt_app():
    """Provide a single QApplication instance for the whole test session.

    Session-scoped so that QApplication is created exactly once and
    shared across modules — recreating it between modules pollutes
    C++ QObject state and breaks widgets (e.g. ``TodoPanel``) that
    depend on a stable parent chain.
    """

    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _read_toolbar_source() -> str:
    return TOOLBAR_PATH.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Module-level: tooltips cover every scene and the toolbar no longer imports  #
# the old QComboBox path.                                                     #
# --------------------------------------------------------------------------- #


def test_scenario_tooltips_cover_every_scene_type() -> None:
    scene_types = {scene_type for _label, scene_type in SCENE_OPTIONS}
    missing = scene_types - set(_SCENARIO_TOOLTIPS)
    assert not missing, f"missing scenario tooltips for: {sorted(missing)}"
    for scene_type, tooltip in _SCENARIO_TOOLTIPS.items():
        assert scene_type in scene_types, f"tooltip defined for unknown scene: {scene_type}"
        assert tooltip.strip(), f"tooltip for {scene_type} is empty"


def test_problem_conclusion_is_available_in_dropdown_options() -> None:
    assert ("问题结论", "problem_conclusion") in SCENE_OPTIONS


def test_step_sequence_hidden_from_dropdown() -> None:
    """The continuous-screenshot scenario must not be selectable from
    the toolbar's dropdown — it has been pulled from the user-facing
    surface (the analysis pipeline still accepts it for fallback)."""

    scene_types = {scene_type for _label, scene_type in SCENE_OPTIONS}
    # Sanity: step_sequence is shipped in the analysis layer so the
    # filter has something to hide.
    assert "step_sequence" in scene_types
    assert "step_sequence" in _HIDDEN_SCENARIOS

    source = _read_toolbar_source()
    # The filter must live inside set_scenarios so it runs every time
    # the scenarios list is rebuilt (not just at __init__ time).
    block = re.search(
        r"def set_scenarios\(self, scenarios: dict\) -> None:.*?(?=\n    def |\nclass )",
        source,
        flags=re.DOTALL,
    )
    assert block, "set_scenarios implementation must exist"
    body = block.group(0)
    assert "if scene_type in _HIDDEN_SCENARIOS:" in body
    assert "continue" in body


def test_qcombobox_no_longer_used_by_scenario_dropdown() -> None:
    source = _read_toolbar_source()
    assert "QComboBox" not in source, (
        "scenario dropdown was refactored to QToolButton+QMenu; "
        "QComboBox should not be referenced from toolbar.py"
    )


# --------------------------------------------------------------------------- #
# Widget setup: the trigger button + menu are wired correctly.                #
# --------------------------------------------------------------------------- #


def test_trigger_button_uses_instant_popup_mode() -> None:
    source = _read_toolbar_source()
    assert "QToolButton.ToolButtonPopupMode.InstantPopup" in source
    assert "self._scenario_button.setMenu(self._scenario_menu)" in source
    assert "self._scenario_action_group.setExclusive(True)" in source


def test_scenario_button_width_bounds_match_analyze_button() -> None:
    source = _read_toolbar_source()
    min_width = re.search(r"_scenario_button\.setMinimumWidth\((\d+)\)", source)
    max_width = re.search(r"_scenario_button\.setMaximumWidth\((\d+)\)", source)
    assert min_width and max_width, "scenario button width bounds must be set"
    min_value, max_value = int(min_width.group(1)), int(max_width.group(1))
    # The dropdown only surfaces 「工单跟进」, so the trigger can be
    # narrower than the previous "fit the 6-char label" baseline.
    # It must still fit the label + caret + a small breathing room
    # without becoming a chunky block.
    assert min_value >= 80
    assert max_value <= 140
    assert min_value < max_value


def test_dropdown_menu_uses_fixed_95px_width() -> None:
    """The popup must be pinned to a compact 95px column so the
    dropdown reads as a compact, balanced control under the toolbar."""

    source = _read_toolbar_source()
    assert "self._scenario_menu.setFixedWidth(95)" in source
    # The width-sync slot from the previous attempt must NOT exist any
    # more — we no longer tie the popup width to the trigger button.
    assert "_sync_scenario_menu_width" not in source
    assert "aboutToShow.connect(self._sync_scenario_menu_width)" not in source


def test_blocked_focus_classes_no_longer_reference_qcombobox() -> None:
    source = _read_toolbar_source()
    # Block list is used by the copy shortcut — QToolButton should replace
    # QComboBox there.
    assert "QToolButton" in source
    blocked_section = source[source.index("blocked_classes = (") :]
    assert '"QComboBox"' not in blocked_section
    assert '"QToolButton"' in blocked_section


# --------------------------------------------------------------------------- #
# Stylesheet rules: the new button + menu visual contract.                    #
# --------------------------------------------------------------------------- #


def test_scenario_button_stylesheet_handles_per_state() -> None:
    source = _read_toolbar_source()
    block = re.search(
        r"QToolButton#scenarioButton\s*\{[^}]*\}",
        source,
        flags=re.DOTALL,
    )
    assert block, "QToolButton#scenarioButton rule must exist"
    body = block.group(0)
    # The trigger button must match the QPushButton#primaryButton height
    # baseline (analyze button) so they line up in the toolbar.
    assert "min-height: 18px" in body
    assert "font-size: %(buttonFontSize)spx" in body
    assert "font-weight: 600" in body
    assert "text-align: left" in body
    # Horizontal padding must be tight — a 4/8/4/10 rhythm keeps the
    # button snug around the label + caret without an obvious empty
    # gutter on the right.
    assert "padding: 4px 8px 4px 10px" in body
    # The text colour must align with the secondary / 「继续」 button so
    # the dropdown reads as part of the same visual row, not a darker
    # standalone control.
    assert "color: %(buttonDefaultInk)s" in body
    # Hover / pressed / on / disabled sub-rules.
    assert "QToolButton#scenarioButton:hover" in source
    assert "QToolButton#scenarioButton:on" in source
    assert "QToolButton#scenarioButton:pressed" in source
    assert "QToolButton#scenarioButton:disabled" in source


def test_scenario_menu_stylesheet_uses_form_tokens() -> None:
    source = _read_toolbar_source()
    menu = re.search(
        r"QMenu#scenarioMenu\s*\{[^}]*\}",
        source,
        flags=re.DOTALL,
    )
    assert menu, "QMenu#scenarioMenu rule must exist"
    body = menu.group(0)
    assert "formPopupBg" in body
    # The popup must be borderless so it reads as a soft cloud under
    # the trigger button rather than a hard outlined card.
    assert "border: 0px none" in body
    # ``border-width: 0`` and ``outline: 0`` are belt-and-suspenders
    # for macOS, where the native popup would otherwise paint a focus
    # ring that masquerades as a hard border.
    assert "border-width: 0" in body
    assert "outline: 0" in body
    # The toolbar dropdown uses a fixed 8px radius for the tighter
    # menu shape requested by design.
    assert "border-radius: 8px" in body
    assert "radiusSm" not in body
    assert "formPopupRadius" not in body


def test_scenario_menu_forces_qt_rendering_on_macos() -> None:
    """On macOS, popup QMenu defaults to a native NSMenu wrapper that
    ignores QSS border / radius. ``WA_TranslucentBackground`` forces Qt
    to draw the menu itself so our ``border: none`` and tight-radius
    rules actually paint. ``WA_MacShowFocusRect`` must also be off on
    both the trigger button and the menu so the macOS focus ring
    doesn't draw an animated outline that looks like a hard border.
    ``NoDropShadowWindowHint`` suppresses the dark system shadow."""

    source = _read_toolbar_source()
    block = re.search(
        r"def _setup_ui\(self\) -> None:.*?(?=\n    def |\nclass )",
        source,
        flags=re.DOTALL,
    )
    assert block, "_setup_ui implementation must exist"
    body = block.group(0)
    assert "WA_TranslucentBackground" in body
    # Translucent background must be set on the menu (not just any
    # widget) so the popup itself bypasses the NSMenu wrapper.
    assert "_scenario_menu" in body
    assert "_scenario_menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground" in body
    assert "_scenario_menu.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)" in body
    # Focus rect must be disabled on both the trigger and the menu so
    # neither one paints an animated outline that the user would read
    # as a border.
    assert "_scenario_button.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect" in body
    assert "_scenario_menu.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect" in body


def test_scenario_menu_stylesheet_applied_directly_to_menu() -> None:
    """The popup QMenu becomes a top-level window when popped up, and
    on some platforms the parent's stylesheet does not propagate
    reliably. ``_apply_style`` must therefore call ``setStyleSheet``
    on the menu itself (in addition to the parent) so the QSS rules
    for ``border``, ``border-radius`` and item styling actually paint
    on the popup."""

    source = _read_toolbar_source()
    block = re.search(
        r"def _apply_style\(self\) -> None:.*?(?=\n    def |\nclass )",
        source,
        flags=re.DOTALL,
    )
    assert block, "_apply_style implementation must exist"
    body = block.group(0)
    # The stylesheet string must be assigned to a local variable so it
    # can be re-applied to the popup menu without re-running the
    # interpolation.
    assert "stylesheet = (" in body
    # The same stylesheet must be applied to both the parent toolbar
    # and the popup menu so the QSS reaches the menu on every platform.
    assert "self.setStyleSheet(stylesheet)" in body
    assert "self._scenario_menu.setStyleSheet(stylesheet)" in body


def test_scenario_menu_items_have_hover_selected_checked() -> None:
    source = _read_toolbar_source()
    item = re.search(
        r"QMenu#scenarioMenu::item\s*\{[^}]*\}",
        source,
        flags=re.DOTALL,
    )
    assert item, "QMenu#scenarioMenu::item rule must exist"
    assert "border-radius" in item.group(0)
    # Items must be slim (one line of text + a small padding) so the
    # popup is compact and matches the toolbar's visual rhythm — the
    # 96px-wide popup needs slim horizontal padding to keep the
    # "工单跟进" label legible, and must NOT add extra left padding
    # (Qt reserves its own checkmark column for checkable actions,
    # and stacking both creates empty space).
    assert "min-height: 16px" in item.group(0)
    assert "padding: 4px 10px 4px 4px" in item.group(0)

    assert "QMenu#scenarioMenu::item:selected" in source
    assert "hoverBg" in source
    assert "QMenu#scenarioMenu::item:checked" in source
    assert "accentSoft" in source
    assert "font-weight: 600" in source


# --------------------------------------------------------------------------- #
# set_scenarios plumbing: builds actions with tooltips, hooks selection.      #
# --------------------------------------------------------------------------- #


def test_set_scenarios_attaches_action_tooltips() -> None:
    """``set_scenarios`` should rebuild the menu with one QAction per
    scenario, attach the per-scene tooltip, and record the lookup map.

    Verified by source inspection so that we don't import PyQt6 (which
    would break ``tests/test_todo_panel.py``'s one-shot PyQt stub
    installer)."""

    source = _read_toolbar_source()
    block = re.search(
        r"def set_scenarios\(self, scenarios: dict\) -> None:.*?(?=\n    def |\nclass )",
        source,
        flags=re.DOTALL,
    )
    assert block, "set_scenarios implementation must exist"
    body = block.group(0)
    assert "self._scenario_menu.clear()" in body
    assert "self._scenario_labels = []" in body
    assert "self._scenario_label_to_action = {}" in body
    # The action must be created, made checkable, and given a tooltip
    # derived from the scene type.
    assert "action = QAction(label, self._scenario_menu)" in body
    assert "action.setCheckable(True)" in body
    assert "_SCENARIO_TOOLTIPS.get(scene_type, \"\")" in body
    assert "action.setToolTip(tooltip)" in body
    assert "self._scenario_menu.addAction(action)" in body
    assert "self._scenario_action_group.addAction(action)" in body
    assert "self._scenario_labels.append(label)" in body
    assert "self._scenario_label_to_action[label] = action" in body
    # Suppression flag must be toggled around the rebuild so the
    # ``triggered`` signal cannot fire while the menu is empty.
    assert "self._suppress_scenario_signal = True" in body
    assert "self._suppress_scenario_signal = False" in body


def test_set_current_scenario_marks_action_checked_and_emits_signal() -> None:
    """``set_current_scenario`` must check the matching QAction, refresh
    the trigger button text, and NOT emit ``scenario_changed``
    (programmatic updates are silent). User-initiated clicks go through
    ``_on_scenario_action_triggered`` and DO emit the signal."""

    source = _read_toolbar_source()

    def _slice(source_text: str, signature: str) -> str:
        match = re.search(
            rf"def {signature}.*?(?=\n    def |\nclass )",
            source_text,
            flags=re.DOTALL,
        )
        assert match, f"function {signature!r} must exist"
        return match.group(0)

    # Programmatic path: silent + sets checked + refreshes trigger text.
    set_current_body = _slice(source, r"set_current_scenario\(self, scenario_name: str\) -> None:")
    assert "action.setChecked(True)" in set_current_body
    assert "_refresh_scenario_button_text(action.text())" in set_current_body
    assert "self._suppress_scenario_signal = True" in set_current_body

    # User path: emits the signal and refreshes the trigger text.
    handler_body = _slice(source, r"_on_scenario_action_triggered\(self, action: QAction\) -> None:")
    assert "if self._suppress_scenario_signal:" in handler_body
    assert "return" in handler_body
    assert "self._refresh_scenario_button_text(action.text())" in handler_body
    assert "self.scenario_changed.emit(action.text())" in handler_body

    # The trigger text formatter must add a caret so the button reads as
    # a dropdown.
    formatter_body = _slice(source, r"_refresh_scenario_button_text\(self, label: str\) -> None:")
    assert "_scenario_button.setText(" in formatter_body
    assert "▾" in formatter_body
    assert "{label}" in formatter_body
