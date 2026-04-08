from PyQt6.QtCore import QPoint, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
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

from .analysis_intent import SCENE_OPTIONS, build_analysis_intent, scene_type_from_label
from .focus_hint_dialog import FocusHintDialog


class FloatingToolbar(QWidget):
    summarize_clicked = pyqtSignal()
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self._loading_frame = 0
        self._toolbar_mode = "single"
        self._timer = QTimer(self)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self._tick_loading)
        self._updating_combo = False
        self._updating_edit_mode = False
        self._edit_buttons: dict[str, QPushButton] = {}
        self._focus_hint = ""

        self._setup_ui()
        self._apply_style()
        self.set_single_capture_mode()

    def _setup_ui(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
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

        self._btn_focus = QPushButton("重点")
        self._btn_focus.setObjectName("ghostButton")
        self._btn_focus.setToolTip("补充本次提取重点")
        self._btn_focus.clicked.connect(self._edit_focus_hint)
        surface_layout.addWidget(self._btn_focus)

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
            button.clicked.connect(
                lambda checked, current_mode=mode: self._on_edit_mode_clicked(current_mode, checked)
            )
            self._edit_group.addButton(button)
            self._edit_buttons[mode] = button
            surface_layout.addWidget(button)

        surface_layout.addWidget(self._create_separator())

        self._btn_copy = QPushButton("⧉")
        self._btn_copy.setObjectName("iconGhostButton")
        self._btn_copy.setAccessibleName("复制")
        self._btn_copy.setToolTip("复制当前截图到剪贴板")
        self._btn_copy.clicked.connect(self.copy_clicked)
        surface_layout.addWidget(self._btn_copy)

        self._btn_undo = QPushButton("↶")
        self._btn_undo.setObjectName("iconGhostButton")
        self._btn_undo.setAccessibleName("撤销")
        self._btn_undo.setToolTip("撤销上一步标注")
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
        self.setStyleSheet(
            """
            QWidget {
                background: transparent;
                color: #111827;
                font-family: 'Segoe UI Variable Text', 'Microsoft YaHei UI', sans-serif;
            }
            QFrame#toolbarSurface {
                background-color: rgba(255, 255, 255, 244);
                border: 1px solid rgba(17, 24, 39, 0.08);
                border-radius: 10px;
            }
            QFrame#toolbarSeparator {
                background-color: rgba(17, 24, 39, 0.08);
                border: none;
            }
            QLabel#statusLabel {
                color: #1677ff;
                background-color: rgba(22, 119, 255, 0.08);
                border: 1px solid rgba(22, 119, 255, 0.18);
                border-radius: 7px;
                padding: 2px 7px;
                font-size: 10px;
                font-weight: 700;
            }
            QComboBox#scenarioCombo {
                background-color: rgba(255, 255, 255, 0.98);
                color: #111827;
                border: 1px solid #e5e7eb;
                border-radius: 7px;
                padding: 4px 22px 4px 8px;
                font-size: 11px;
                min-height: 18px;
            }
            QComboBox#scenarioCombo:hover {
                border: 1px solid #d0d5dd;
            }
            QComboBox#scenarioCombo:focus {
                border: 1px solid #1677ff;
            }
            QComboBox#scenarioCombo::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(255, 255, 255, 248);
                color: #111827;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                outline: none;
                padding: 4px;
                selection-background-color: rgba(22, 119, 255, 0.24);
            }
            QPushButton {
                border-radius: 7px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
                min-height: 18px;
            }
            QPushButton#primaryButton {
                color: #ffffff;
                background-color: #1677ff;
                border: 1px solid #1677ff;
                min-width: 56px;
            }
            QPushButton#primaryButton:hover {
                background-color: #2b85ff;
                border: 1px solid #2b85ff;
            }
            QPushButton#primaryButton:pressed {
                background-color: #0e63d6;
                border: 1px solid #0e63d6;
            }
            QPushButton#secondaryButton {
                color: #374151;
                background-color: #f3f4f6;
                border: 1px solid #e5e7eb;
                min-width: 52px;
            }
            QPushButton#secondaryButton:hover {
                background-color: #eceff3;
                border: 1px solid #d0d5dd;
            }
            QPushButton#secondaryButton:pressed {
                background-color: #e5e7eb;
            }
            QPushButton#modeButton {
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                padding: 0;
                color: #4b5563;
                background-color: transparent;
                border: 1px solid transparent;
            }
            QPushButton#modeButton:hover {
                background-color: rgba(17, 24, 39, 0.04);
                border: 1px solid #e5e7eb;
            }
            QPushButton#modeButton:checked {
                color: #1677ff;
                background-color: rgba(22, 119, 255, 0.1);
                border: 1px solid rgba(22, 119, 255, 0.28);
            }
            QPushButton#ghostButton {
                color: #374151;
                background-color: transparent;
                border: 1px solid transparent;
                min-width: 42px;
            }
            QPushButton#ghostButton:hover {
                background-color: rgba(17, 24, 39, 0.04);
                border: 1px solid #e5e7eb;
            }
            QPushButton#ghostButton:pressed {
                background-color: rgba(17, 24, 39, 0.08);
            }
            QPushButton#iconGhostButton {
                color: #475467;
                background-color: transparent;
                border: 1px solid transparent;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                padding: 0;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#iconGhostButton:hover {
                color: #111827;
                background-color: rgba(17, 24, 39, 0.04);
                border: 1px solid #e5e7eb;
            }
            QPushButton#iconGhostButton:pressed {
                background-color: rgba(17, 24, 39, 0.08);
                border: 1px solid #d0d5dd;
            }
            QPushButton:disabled {
                color: rgba(107, 114, 128, 0.5);
                background-color: rgba(243, 244, 246, 0.9);
                border: 1px solid rgba(229, 231, 235, 0.9);
            }
            """
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
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
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

    def get_focus_hint(self) -> str:
        return self._focus_hint

    def reset_analysis_inputs(self) -> None:
        self._focus_hint = ""
        self.set_current_scenario(next(iter(dict(SCENE_OPTIONS).keys()), ""))
        self._refresh_focus_button()

    def build_analysis_intent(self, capture_count: int):
        scene_type = self.get_current_scene_type()
        if not scene_type:
            return None
        return build_analysis_intent(
            scene_type,
            focus_hint=self._focus_hint,
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

    def _on_scenario_changed(self, scenario_name: str) -> None:
        if not self._updating_combo:
            self.scenario_changed.emit(scenario_name)

    def _on_edit_mode_clicked(self, mode: str, checked: bool) -> None:
        if checked and not self._updating_edit_mode:
            self.edit_mode_changed.emit(mode)

    def _tick_loading(self) -> None:
        self._loading_frame = (self._loading_frame + 1) % len(self._LOADING_FRAMES)
        self._btn_summarize.setText(self._LOADING_FRAMES[self._loading_frame])

    def _edit_focus_hint(self) -> None:
        dialog = FocusHintDialog(self._focus_hint, parent=self.window())
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self._focus_hint = dialog.hint_text
        self._refresh_focus_button()

    def _refresh_focus_button(self) -> None:
        has_focus = bool(self._focus_hint)
        self._btn_focus.setText("重点*" if has_focus else "重点")
        self._btn_focus.setToolTip(self._focus_hint or "补充本次提取重点")
