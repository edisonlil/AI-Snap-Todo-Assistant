from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from .runtime import RUNTIME_CAPABILITIES
from .theme_controller import ThemeController
from .analysis.intent import SCENE_OPTIONS, build_analysis_intent, scene_type_from_label
from .paths import asset_file


class FloatingToolbar(QWidget):
    summarize_clicked = pyqtSignal()
    translate_clicked = pyqtSignal(str)
    continue_capture_clicked = pyqtSignal()
    copy_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()
    scenario_changed = pyqtSignal(str)
    edit_mode_changed = pyqtSignal(str)
    undo_clicked = pyqtSignal()
    clear_annotations_clicked = pyqtSignal()

    _LOADING_FRAMES = ["分析中", "分析中.", "分析中..", "分析中..."]
    _EDIT_MODE_ITEMS = (
        ("移", "move", "移动选区"),
        ("框", "rect", "矩形标注"),
        ("箭", "arrow", "箭头标注"),
        ("字", "text", "文字标注"),
    )

    def __init__(self, parent=None, *, theme_controller: ThemeController | None = None):
        super().__init__(parent)
        self._theme_controller = theme_controller or ThemeController()
        self._loading = False
        self._loading_frame = 0
        self._toolbar_mode = "single"
        self._timer = QTimer(self)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self._tick_loading)
        self._updating_combo = False
        self._updating_edit_mode = False
        self._edit_buttons: dict[str, QPushButton] = {}
        self._copy_shortcuts: list[QShortcut] = []

        self._setup_ui()
        self._apply_style()
        self._theme_controller.themeChanged.connect(self._apply_style)
        self.set_single_capture_mode()

    def _setup_ui(self) -> None:
        self.setWindowFlags(RUNTIME_CAPABILITIES.floating_tool_window_flags(Qt.WindowType))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self._surface = QFrame()
        self._surface.setObjectName("toolbarSurface")
        surface_layout = QHBoxLayout(self._surface)
        surface_layout.setContentsMargins(8, 6, 8, 6)
        surface_layout.setSpacing(6)

        self._status_label = QLabel("")
        self._status_label.setObjectName("statusLabel")
        self._status_label.hide()
        surface_layout.addWidget(self._status_label)

        self._scenario_combo = QComboBox()
        self._scenario_combo.setObjectName("scenarioCombo")
        self._scenario_combo.setMinimumWidth(110)
        self._scenario_combo.setMaximumWidth(144)
        self._scenario_combo.currentTextChanged.connect(self._on_scenario_changed)
        self._scenario_combo.setToolTip("选择分析场景")
        surface_layout.addWidget(self._scenario_combo)

        self._btn_translate = QPushButton("")
        self._btn_translate.setObjectName("iconGhostButton")
        self._btn_translate.setAccessibleName("原位替换")
        self._btn_translate.setToolTip("将截图中的文字直接贴回原图")
        self._btn_translate.setIcon(QIcon(str(asset_file("image-translate.svg"))))
        self._btn_translate.setIconSize(QSize(16, 16))
        self._btn_translate.clicked.connect(self._emit_translate_clicked)
        self._btn_translate.hide()

        self._btn_summarize = QPushButton("分析")
        self._btn_summarize.setObjectName("primaryButton")
        self._btn_summarize.setToolTip("分析当前截图内容")
        self._btn_summarize.clicked.connect(self.summarize_clicked)
        surface_layout.addWidget(self._btn_summarize)

        self._btn_continue = QPushButton("继续")
        self._btn_continue.setObjectName("secondaryButton")
        self._btn_continue.setToolTip("保留当前内容并继续添加截图")
        self._btn_continue.clicked.connect(self.continue_capture_clicked)
        surface_layout.addWidget(self._btn_continue)

        surface_layout.addWidget(self._create_separator())

        self._edit_group = QButtonGroup(self)
        self._edit_group.setExclusive(True)
        for label, mode, tooltip in self._EDIT_MODE_ITEMS:
            button = QPushButton(label)
            button.setObjectName("modeButton")
            button.setCheckable(True)
            button.setToolTip(tooltip)
            if mode == "move":
                button.setText("")
                button.setIcon(QIcon(str(asset_file("move.svg"))))
                button.setIconSize(QSize(16, 16))
            elif mode == "rect":
                button.setText("")
                button.setIcon(QIcon(str(asset_file("rect.svg"))))
                button.setIconSize(QSize(16, 16))
            elif mode == "arrow":
                button.setText("")
                button.setIcon(QIcon(str(asset_file("arrow.svg"))))
                button.setIconSize(QSize(16, 16))
            elif mode == "text":
                button.setText("")
                button.setIcon(QIcon(str(asset_file("text.svg"))))
                button.setIconSize(QSize(16, 16))
            button.clicked.connect(
                lambda checked, current_mode=mode: self._on_edit_mode_clicked(current_mode, checked)
            )
            self._edit_group.addButton(button)
            self._edit_buttons[mode] = button
            surface_layout.addWidget(button)

        surface_layout.addWidget(self._create_separator())

        self._btn_copy = QPushButton("")
        self._btn_copy.setObjectName("iconGhostButton")
        self._btn_copy.setAccessibleName("复制")
        self._btn_copy.setToolTip("复制当前截图到剪贴板")
        self._btn_copy.setIcon(QIcon(str(asset_file("copy.svg"))))
        self._btn_copy.setIconSize(QSize(16, 16))
        self._btn_copy.clicked.connect(self.copy_clicked)
        surface_layout.addWidget(self._btn_copy)

        surface_layout.addWidget(self._btn_translate)

        self._btn_undo = QPushButton("")
        self._btn_undo.setObjectName("iconGhostButton")
        self._btn_undo.setAccessibleName("撤销")
        self._btn_undo.setToolTip("撤销上一步标注")
        self._btn_undo.setIcon(QIcon(str(asset_file("return.svg"))))
        self._btn_undo.setIconSize(QSize(16, 16))
        self._btn_undo.clicked.connect(self.undo_clicked)
        surface_layout.addWidget(self._btn_undo)

        self._btn_clear = QPushButton("清空")
        self._btn_clear.setObjectName("ghostButton")
        self._btn_clear.setToolTip("清空所有标注")
        self._btn_clear.clicked.connect(self.clear_annotations_clicked)
        surface_layout.addWidget(self._btn_clear)

        self._btn_cancel = QPushButton("×")
        self._btn_cancel.setObjectName("iconGhostButton")
        self._btn_cancel.setAccessibleName("取消")
        self._btn_cancel.setToolTip("退出当前截图")
        self._btn_cancel.clicked.connect(self.cancel_clicked)
        surface_layout.addWidget(self._btn_cancel)

        for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(self._trigger_copy_shortcut)
            self._copy_shortcuts.append(shortcut)

        root_layout.addWidget(self._surface)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(15, 23, 42, 42))
        self._surface.setGraphicsEffect(shadow)

        self.set_scenarios(dict(SCENE_OPTIONS))
        self.reset_analysis_inputs()
        self.set_edit_mode("move")

    def _create_separator(self) -> QFrame:
        separator = QFrame()
        separator.setObjectName("toolbarSeparator")
        separator.setFixedWidth(1)
        separator.setFixedHeight(16)
        return separator

    def _apply_style(self) -> None:
        theme = self._theme_controller.tokens
        self.setStyleSheet(
            """
            QWidget {
                background: transparent;
                color: %(titleInk)s;
                font-family: %(widgetFontCss)s;
            }
            QFrame#toolbarSurface {
                background-color: %(toolbarBg)s;
                border: 1px solid %(panelLine)s;
                border-radius: %(radiusMd)spx;
            }
            QFrame#toolbarSeparator {
                background-color: %(panelLine)s;
                border: none;
            }
            QLabel#statusLabel {
                color: %(accent)s;
                background-color: %(accentSoft)s;
                border: 1px solid %(accentTint)s;
                border-radius: %(radiusSm)spx;
                padding: 2px 7px;
                font-size: %(fontTiny)spx;
                font-weight: 700;
            }
            QComboBox#scenarioCombo {
                background-color: %(inputBg)s;
                color: %(titleInk)s;
                border: 1px solid %(panelLine)s;
                border-radius: %(radiusSm)spx;
                padding: 4px 22px 4px 8px;
                font-size: %(fontCaption)spx;
                min-height: 18px;
            }
            QComboBox#scenarioCombo:hover {
                border: 1px solid %(fieldLine)s;
            }
            QComboBox#scenarioCombo:focus {
                border: 1px solid %(accent)s;
            }
            QComboBox#scenarioCombo::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: %(toolbarPanelBg)s;
                color: %(titleInk)s;
                border: 1px solid %(panelLine)s;
                border-radius: %(radiusMd)spx;
                outline: none;
                padding: 4px;
                selection-background-color: %(accentTint)s;
            }
            QPushButton {
                border-radius: %(buttonRadius)spx;
                padding: 5px 10px;
                font-size: %(buttonFontSize)spx;
                font-weight: 600;
                min-height: 18px;
            }
            QPushButton#primaryButton {
                color: %(buttonPrimaryInk)s;
                background-color: %(buttonPrimaryBg)s;
                border: 1px solid %(buttonPrimaryBg)s;
                min-width: 56px;
            }
            QPushButton#primaryButton:hover {
                background-color: %(buttonPrimaryBgHover)s;
                border: 1px solid %(buttonPrimaryBgHover)s;
            }
            QPushButton#primaryButton:pressed {
                background-color: %(buttonPrimaryBgPressed)s;
                border: 1px solid %(buttonPrimaryBgPressed)s;
            }
            QPushButton#secondaryButton {
                color: %(buttonDefaultInk)s;
                background-color: %(buttonDefaultBg)s;
                border: 1px solid %(buttonBorder)s;
                min-width: 52px;
            }
            QPushButton#secondaryButton:hover {
                background-color: %(buttonDefaultBgHover)s;
                border: 1px solid %(fieldLine)s;
            }
            QPushButton#secondaryButton:pressed {
                background-color: %(buttonDefaultBgPressed)s;
            }
            QPushButton#modeButton {
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                padding: 0;
                color: %(bodyInk)s;
                background-color: transparent;
                border: 1px solid transparent;
            }
            QPushButton#modeButton:hover {
                background-color: %(hoverBg)s;
                border: 1px solid %(panelLine)s;
            }
            QPushButton#modeButton:checked {
                color: %(accent)s;
                background-color: %(accentSoft)s;
                border: 1px solid %(accentTint)s;
            }
            QPushButton#ghostButton {
                color: %(bodyInk)s;
                background-color: transparent;
                border: 1px solid transparent;
                min-width: 42px;
            }
            QPushButton#ghostButton:hover {
                background-color: %(hoverBg)s;
                border: 1px solid %(panelLine)s;
            }
            QPushButton#ghostButton:pressed {
                background-color: %(pressedBg)s;
            }
            QPushButton#iconGhostButton {
                color: %(bodyInk)s;
                background-color: transparent;
                border: 1px solid transparent;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                padding: 0;
                font-size: %(fontBodyLg)spx;
                font-weight: 600;
            }
            QPushButton#iconGhostButton:hover {
                color: %(titleInk)s;
                background-color: %(hoverBg)s;
                border: 1px solid %(panelLine)s;
            }
            QPushButton#iconGhostButton:pressed {
                background-color: %(pressedBg)s;
                border: 1px solid %(fieldLine)s;
            }
            QPushButton:disabled {
                color: %(buttonDisabledInk)s;
                background-color: %(buttonDisabledBg)s;
                border: 1px solid %(buttonBorder)s;
            }
            """
            % {
                **theme,
                "widgetFontCss": str(theme.get("widgetFontCss") or RUNTIME_CAPABILITIES.widget_font_css),
            }
        )

    def set_single_capture_mode(self) -> None:
        self._toolbar_mode = "single"
        self._status_label.hide()
        self._btn_summarize.setText("分析")
        self._btn_continue.setText("继续")
        self._btn_continue.setToolTip("保留当前内容并继续添加截图")
        self._btn_copy.show()
        self.set_edit_mode("move")

    def set_multi_capture_mode(self, capture_count: int) -> None:
        self._toolbar_mode = "multi"
        self._status_label.setText(f"{capture_count} 张")
        self._status_label.show()
        self._btn_summarize.setText("完成")
        self._btn_continue.setText("继续")
        self._btn_continue.setToolTip("继续添加下一张截图")
        self._btn_copy.hide()
        self.set_edit_mode("move")

    def attach_to_overlay(self, overlay: QWidget | None) -> None:
        was_visible = self.isVisible()
        self.hide()

        if overlay is None:
            self.setParent(None)
            self.setWindowFlags(RUNTIME_CAPABILITIES.floating_tool_window_flags(Qt.WindowType))
        else:
            self.setParent(overlay)
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)

        if was_visible:
            self.show()
            self.raise_()

    def show_at(self, rect: QRect) -> None:
        self.adjustSize()

        anchor = rect.bottomRight()
        screen = QApplication.screenAt(anchor) or QApplication.primaryScreen()
        screen_geo = (
            screen.availableGeometry()
            if screen
            else QApplication.primaryScreen().availableGeometry()
        )

        x = rect.right() - self.width()
        y = rect.bottom() + 10

        if y + self.height() > screen_geo.bottom():
            y = rect.top() - self.height() - 10
        min_x = screen_geo.left() + 10
        max_x = max(min_x, screen_geo.right() - self.width() - 10)
        min_y = screen_geo.top() + 10
        max_y = max(min_y, screen_geo.bottom() - self.height() - 10)
        x = min(max(x, min_x), max_x)
        y = min(max(y, min_y), max_y)

        if self.parentWidget() is not None:
            parent_top_left = self.parentWidget().geometry().topLeft()
            self.move(QPoint(x, y) - parent_top_left)
        else:
            self.move(x, y)
        self.show()
        self.raise_()

    def set_scenarios(self, scenarios: dict) -> None:
        self._updating_combo = True
        self._scenario_combo.clear()
        for label in scenarios.keys():
            self._scenario_combo.addItem(label)
        self._updating_combo = False

    def set_current_scenario(self, scenario_name: str) -> None:
        self._updating_combo = True
        target = scenario_name or next(iter(dict(SCENE_OPTIONS).keys()), "")
        index = self._scenario_combo.findText(target)
        if index >= 0:
            self._scenario_combo.setCurrentIndex(index)
        self._updating_combo = False

    def set_scenario_selector_visible(self, visible: bool) -> None:
        self._scenario_combo.setVisible(visible)

    def get_current_scenario(self) -> str:
        return self._scenario_combo.currentText()

    def get_current_scene_type(self) -> str:
        return scene_type_from_label(self.get_current_scenario())

    def reset_analysis_inputs(self) -> None:
        self.set_current_scenario(next(iter(dict(SCENE_OPTIONS).keys()), ""))

    def build_analysis_intent(self, capture_count: int):
        scene_type = self.get_current_scene_type()
        if not scene_type:
            return None
        return build_analysis_intent(
            scene_type,
            capture_count=capture_count,
        )

    def set_edit_mode(self, mode: str) -> None:
        button = self._edit_buttons.get(mode)
        if button is None:
            return
        self._updating_edit_mode = True
        button.setChecked(True)
        self._updating_edit_mode = False

    def is_loading(self) -> bool:
        return self._loading

    def set_loading(self, loading: bool) -> None:
        self._loading = loading
        self._scenario_combo.setEnabled(not loading)
        self._btn_translate.setEnabled(not loading)
        self._btn_continue.setEnabled(not loading)
        self._btn_copy.setEnabled(not loading)
        self._btn_cancel.setEnabled(not loading)
        self._btn_undo.setEnabled(not loading)
        self._btn_clear.setEnabled(not loading)
        for button in self._edit_buttons.values():
            button.setEnabled(not loading)

        if loading:
            self._loading_frame = 0
            self._btn_summarize.setEnabled(False)
            self._btn_summarize.setText(self._LOADING_FRAMES[0])
            self._timer.start()
        else:
            self._timer.stop()
            self._btn_summarize.setEnabled(True)
            if self._toolbar_mode == "multi":
                self._btn_summarize.setText("完成")
            else:
                self._btn_summarize.setText("分析")

    def set_translation_visible(self, visible: bool) -> None:
        self._btn_translate.setVisible(visible)

    def current_translation_direction(self) -> str:
        return "en_to_zh"

    def _on_scenario_changed(self, scenario_name: str) -> None:
        if not self._updating_combo:
            self.scenario_changed.emit(scenario_name)

    def _on_edit_mode_clicked(self, mode: str, checked: bool) -> None:
        if checked and not self._updating_edit_mode:
            self.edit_mode_changed.emit(mode)

    def _tick_loading(self) -> None:
        self._loading_frame = (self._loading_frame + 1) % len(self._LOADING_FRAMES)
        self._btn_summarize.setText(self._LOADING_FRAMES[self._loading_frame])

    def _trigger_copy_shortcut(self) -> None:
        if not self._can_trigger_copy_shortcut():
            return
        self.copy_clicked.emit()

    def _can_trigger_copy_shortcut(self) -> bool:
        if self._loading or self._toolbar_mode != "single":
            return False
        if not self.isVisible() or not self._btn_copy.isVisible() or not self._btn_copy.isEnabled():
            return False
        active_window = QApplication.activeWindow()
        valid_windows = {self.window()}
        parent = self.parentWidget()
        if parent is not None:
            valid_windows.add(parent.window())
        if active_window is not None and active_window not in valid_windows:
            return False
        focus_widget = QApplication.focusWidget()
        if focus_widget is None:
            return True
        blocked_classes = (
            "QLineEdit",
            "QTextEdit",
            "QPlainTextEdit",
            "QComboBox",
            "QAbstractSpinBox",
        )
        return not any(focus_widget.inherits(class_name) for class_name in blocked_classes)

    def _emit_translate_clicked(self) -> None:
        self.translate_clicked.emit(self.current_translation_direction())
