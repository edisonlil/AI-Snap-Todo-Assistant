"""QML-backed dialog for optional analysis focus hints."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout


class _FocusHintBridge(QObject):
    dataChanged = pyqtSignal()
    closeRequested = pyqtSignal()
    confirmRequested = pyqtSignal()
    clearRequested = pyqtSignal()

    def __init__(self, initial_text: str) -> None:
        super().__init__()
        self._hint_text = str(initial_text or "").strip()

    @pyqtProperty(str, notify=dataChanged)
    def hintText(self) -> str:
        return self._hint_text

    @pyqtProperty(bool, notify=dataChanged)
    def hasContent(self) -> bool:
        return bool(self._hint_text.strip())

    @pyqtSlot(str)
    def updateHint(self, text: str) -> None:
        self._hint_text = str(text or "")
        self.dataChanged.emit()

    @pyqtSlot()
    def closeDialog(self) -> None:
        self.closeRequested.emit()

    @pyqtSlot()
    def confirmDialog(self) -> None:
        self.confirmRequested.emit()

    @pyqtSlot()
    def clearHint(self) -> None:
        self._hint_text = ""
        self.dataChanged.emit()
        self.clearRequested.emit()


class FocusHintDialog(QDialog):
    def __init__(self, initial_text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._bridge = _FocusHintBridge(initial_text)
        self._positioned = False

        self.setWindowTitle("补充重点")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(460, 248)
        self.setMinimumSize(420, 228)

        self._setup_ui()

        self._bridge.closeRequested.connect(self.reject)
        self._bridge.confirmRequested.connect(self.accept)
        self._bridge.clearRequested.connect(self._noop)

    @property
    def hint_text(self) -> str:
        return self._bridge.hintText.strip()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        self._view = QQuickWidget(self)
        self._view.setClearColor(QColor(0, 0, 0, 0))
        self._view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._view.rootContext().setContextProperty("focusHintBridge", self._bridge)
        self._view.setSource(
            QUrl.fromLocalFile(
                str(Path(__file__).with_name("qml").joinpath("FocusHintDialog.qml"))
            )
        )
        self._ensure_qml_loaded()
        layout.addWidget(self._view)

    def _ensure_qml_loaded(self) -> None:
        if self._view.status() != QQuickWidget.Status.Error:
            return
        errors = "\n".join(error.toString() for error in self._view.errors())
        raise RuntimeError(f"Failed to load FocusHintDialog.qml:\n{errors}")

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._positioned:
            self._fit_within_screen()
            self._positioned = True

    def _fit_within_screen(self) -> None:
        screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        margin = 20
        self.resize(
            min(self.width(), available.width() - margin * 2),
            min(self.height(), available.height() - margin * 2),
        )
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    @staticmethod
    def _noop() -> None:
        return None
