"""QML-backed confirmation dialog for ticket snapshots."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout

from aica.feedback import FeedbackData
from aica.models import TicketSnapshot, TicketSummaryFields
from aica.ticket_field_resolver import (
    TICKET_TYPE_OPTIONS,
    normalize_ticket_type,
    resolve_product_line,
)

_UNKNOWN_TEXT = "\u672a\u77e5"
_UNCLASSIFIED_TASK = "\u672a\u5206\u7c7b\u4efb\u52a1"
_PENDING_TEXT = "\u5f85\u8865\u5145"
_SAVE_HINT = "\u4fdd\u5b58\u540e\u4f1a\u521b\u5efa\u5f85\u529e\u6216\u8ffd\u52a0\u5230\u5f53\u524d\u9009\u4e2d\u7684\u5f85\u529e\u3002"


def _clean_text(value: str, fallback: str = _UNKNOWN_TEXT) -> str:
    text = str(value or "").strip()
    return text or fallback


class _ResultDialogBridge(QObject):
    dataChanged = pyqtSignal()

    closeRequested = pyqtSignal()
    saveRequested = pyqtSignal()
    feedbackRequested = pyqtSignal()

    def __init__(self, result: TicketSnapshot, scenario: str, model: str, show_feedback: bool) -> None:
        super().__init__()
        self._scenario = scenario
        self._model = model
        self._show_feedback = show_feedback
        self._fallback_title = result.title.strip() or _UNCLASSIFIED_TASK
        self._title = result.title.strip()
        self._group_name = _clean_text(result.fields.group_name)
        self._environment = _clean_text(result.fields.environment)
        self._product_line = resolve_product_line(raw_value=result.fields.product_line)
        self._ticket_type = normalize_ticket_type(result.fields.ticket_type, summary_text=result.current_summary)
        self._current_summary = result.current_summary.strip()
        self._timeline_entry = result.timeline_entry.strip()

    @pyqtProperty(str, notify=dataChanged)
    def scenario(self) -> str:
        return self._scenario

    @pyqtProperty(str, notify=dataChanged)
    def model(self) -> str:
        return self._model

    @pyqtProperty(str, notify=dataChanged)
    def title(self) -> str:
        return self._title

    @pyqtProperty(str, notify=dataChanged)
    def groupName(self) -> str:
        return self._group_name

    @pyqtProperty(str, notify=dataChanged)
    def environment(self) -> str:
        return self._environment

    @pyqtProperty(str, notify=dataChanged)
    def productLine(self) -> str:
        return self._product_line

    @pyqtProperty(str, notify=dataChanged)
    def ticketType(self) -> str:
        return self._ticket_type

    @pyqtProperty("QVariantList", constant=True)
    def ticketTypeOptions(self):  # noqa: ANN201
        return list(TICKET_TYPE_OPTIONS)

    @pyqtProperty(str, notify=dataChanged)
    def currentSummary(self) -> str:
        return self._current_summary

    @pyqtProperty(bool, notify=dataChanged)
    def showFeedbackAction(self) -> bool:
        return self._show_feedback

    @pyqtProperty(str, constant=True)
    def saveHint(self) -> str:
        return _SAVE_HINT

    @pyqtSlot(str, str)
    def updateField(self, name: str, value: str) -> None:
        text = str(value)
        if name == "title":
            self._title = text
        elif name == "group_name":
            self._group_name = text
        elif name == "environment":
            self._environment = text
        elif name == "product_line":
            self._product_line = resolve_product_line(raw_value=text)
        elif name == "ticket_type":
            self._ticket_type = normalize_ticket_type(text, summary_text=self._current_summary)
        elif name == "current_summary":
            self._current_summary = text
        else:
            return
        self.dataChanged.emit()

    def build_snapshot(self) -> TicketSnapshot:
        normalized_summary = self._current_summary.strip() or _PENDING_TEXT
        normalized_title = self._title.strip() or self._fallback_title
        return TicketSnapshot(
            title=normalized_title,
            fields=TicketSummaryFields(
                group_name=_clean_text(self._group_name),
                environment=_clean_text(self._environment),
                product_line=resolve_product_line(raw_value=self._product_line),
                ticket_type=normalize_ticket_type(
                    self._ticket_type,
                    summary_text="\n".join(
                        part
                        for part in (
                            normalized_title,
                            normalized_summary,
                            self._timeline_entry,
                        )
                        if part
                    ),
                ),
            ),
            current_summary=normalized_summary,
            # Confirmation dialog hides timeline editing, so preserve the AI-generated follow-up entry.
            timeline_entry=self._timeline_entry or normalized_summary,
        )

    @pyqtSlot()
    def closeDialog(self) -> None:
        self.closeRequested.emit()

    @pyqtSlot()
    def saveDialog(self) -> None:
        self.saveRequested.emit()

    @pyqtSlot()
    def feedbackDialog(self) -> None:
        if self._show_feedback:
            self.feedbackRequested.emit()


class ResultDialog(QDialog):
    """Displays a structured ticket snapshot for review before saving."""

    def __init__(
        self,
        result: TicketSnapshot,
        scenario: str,
        model: str,
        feedback_callback: Optional[Callable] = None,
        save_callback: Optional[Callable] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._original_result = result
        self._scenario = scenario
        self._model = model
        self._feedback_callback = feedback_callback
        self._save_callback = save_callback
        self._positioned = False

        self._bridge = _ResultDialogBridge(
            result=result,
            scenario=scenario,
            model=model,
            show_feedback=feedback_callback is not None,
        )

        self.setObjectName("resultDialog")
        self.setWindowTitle(f"\u5de5\u5355\u5f85\u529e\u786e\u8ba4 - {scenario}")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(740, 560)
        self.setMinimumSize(660, 500)

        self._setup_ui()

        self._bridge.closeRequested.connect(self.reject)
        self._bridge.saveRequested.connect(self._on_save)
        self._bridge.feedbackRequested.connect(self._on_feedback)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)

        self._view = QQuickWidget(self)
        self._view.setClearColor(QColor(0, 0, 0, 0))
        self._view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._view.rootContext().setContextProperty("resultDialogBridge", self._bridge)
        self._view.setSource(
            QUrl.fromLocalFile(
                str(Path(__file__).with_name("qml").joinpath("ResultDialog.qml"))
            )
        )
        self._ensure_qml_loaded()
        layout.addWidget(self._view)

    def _ensure_qml_loaded(self) -> None:
        if self._view.status() != QQuickWidget.Status.Error:
            return
        errors = "\n".join(error.toString() for error in self._view.errors())
        raise RuntimeError(f"Failed to load ResultDialog.qml:\n{errors}")

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

    def _build_snapshot(self) -> TicketSnapshot:
        return self._bridge.build_snapshot()

    def _on_save(self) -> None:
        snapshot = self._build_snapshot()
        if self._save_callback:
            self._save_callback(snapshot)
        self.accept()

    def _on_feedback(self) -> None:
        snapshot = self._build_snapshot()
        feedback_data = FeedbackData(
            scenario=self._scenario,
            model=self._model,
            ai_output=self._original_result.to_dict(),
            user_edited=(snapshot.to_dict() != self._original_result.to_dict()),
            original_result=str(self._original_result),
            edited_result=str(snapshot),
            feedback_status="incorrect",
        )
        if self._feedback_callback:
            self._feedback_callback(snapshot, feedback_data)
        self.reject()
