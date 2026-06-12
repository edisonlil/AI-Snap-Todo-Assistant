"""QML-backed feedback dialog for reviewing and saving corrections."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout

from aica.feedback import FeedbackCollector, FeedbackData
from aica.runtime import RUNTIME_CAPABILITIES
from aica.theme_controller import ThemeController


class _FeedbackPanelBridge(QObject):
    dataChanged = pyqtSignal()
    closeRequested = pyqtSignal()
    saveRequested = pyqtSignal()

    def __init__(self, *, scenario: str, model: str, result_text: str, notes_text: str) -> None:
        super().__init__()
        self._scenario = scenario
        self._model = model
        self._result_text = result_text
        self._notes_text = notes_text

    @pyqtProperty(str, constant=True)
    def uiFont(self) -> str:
        return RUNTIME_CAPABILITIES.ui_font

    @pyqtProperty(str, constant=True)
    def monospaceFont(self) -> str:
        return RUNTIME_CAPABILITIES.monospace_font

    @pyqtProperty(str, constant=True)
    def scenario(self) -> str:
        return self._scenario

    @pyqtProperty(str, constant=True)
    def model(self) -> str:
        return self._model

    @pyqtProperty(str, notify=dataChanged)
    def resultText(self) -> str:
        return self._result_text

    @pyqtProperty(str, notify=dataChanged)
    def notesText(self) -> str:
        return self._notes_text

    @pyqtProperty(bool, constant=True)
    def saveEnabled(self) -> bool:
        return True

    @pyqtSlot(str)
    def updateResultText(self, text: str) -> None:
        self._result_text = text
        self.dataChanged.emit()

    @pyqtSlot(str)
    def updateNotesText(self, text: str) -> None:
        self._notes_text = text
        self.dataChanged.emit()

    @pyqtSlot()
    def savePanel(self) -> None:
        self.saveRequested.emit()

    @pyqtSlot()
    def closePanel(self) -> None:
        self.closeRequested.emit()


class FeedbackPanel(QDialog):
    """Collects user feedback on AI recognition results."""

    def __init__(
        self,
        result_str: str,
        feedback_data: FeedbackData,
        scenario: str,
        model: str,
        save_callback: Optional[Callable] = None,
        parent=None,
        theme_controller: ThemeController | None = None,
    ):
        super().__init__(parent)
        self._theme_controller = theme_controller or ThemeController()
        self._result_str = result_str
        self._feedback_data = feedback_data
        self._scenario = scenario
        self._model = model
        self._save_callback = save_callback
        self._collector = FeedbackCollector()
        self._positioned = False

        self._bridge = _FeedbackPanelBridge(
            scenario=scenario,
            model=model,
            result_text=result_str,
            notes_text=feedback_data.notes,
        )

        self.setObjectName("feedbackDialog")
        self.setWindowTitle("\u53cd\u9988\u4fee\u6b63")
        self.resize(780, 580)
        self.setMinimumSize(620, 460)
        self.setSizeGripEnabled(True)

        self._setup_ui()

        self._bridge.closeRequested.connect(self.reject)
        self._bridge.saveRequested.connect(self._on_save_feedback)

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._view = QQuickWidget(self)
        self._theme_controller.apply_to_context(self._view.rootContext())
        self._view.rootContext().setContextProperty("feedbackPanelBridge", self._bridge)
        self._view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._view.setSource(
            QUrl.fromLocalFile(
                str(Path(__file__).with_name("qml").joinpath("FeedbackPanel.qml"))
            )
        )
        self._ensure_qml_loaded()
        root_layout.addWidget(self._view)

    def _ensure_qml_loaded(self) -> None:
        if self._view.status() != QQuickWidget.Status.Error:
            return
        errors = "\n".join(error.toString() for error in self._view.errors())
        raise RuntimeError(f"Failed to load FeedbackPanel.qml:\n{errors}")

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._positioned:
            self._fit_within_screen()
            self._positioned = True

    def _fit_within_screen(self) -> None:
        screen = QApplication.screenAt(self.pos()) or QApplication.screenAt(
            self.mapToGlobal(self.rect().center())
        )
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        margin = 16
        max_width = max(620, available.width() - margin * 2)
        max_height = max(460, available.height() - margin * 2)

        self.setMaximumSize(max_width, max_height)
        self.resize(
            min(self.width(), max_width),
            min(self.height(), max_height),
        )

        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        x = max(
            available.left() + margin,
            min(frame.left(), available.right() - frame.width() - margin + 1),
        )
        y = max(
            available.top() + margin,
            min(frame.top(), available.bottom() - frame.height() - margin + 1),
        )
        self.move(x, y)

    def _prepare_feedback_data(self) -> None:
        edited_ai_result = self._bridge.resultText
        self._feedback_data.user_edited = edited_ai_result != self._result_str
        self._feedback_data.original_result = self._result_str
        self._feedback_data.edited_result = edited_ai_result
        self._feedback_data.notes = self._bridge.notesText
        self._feedback_data.problem_tags = []
        self._collector.save_feedback(self._feedback_data)

    def _on_save_feedback(self) -> None:
        self._prepare_feedback_data()

        if self._save_callback:
            self._save_callback(self._feedback_data)

        self.accept()
