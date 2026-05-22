"""QML-backed confirmation dialog for ticket snapshots."""
from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Callable, Optional

_SKIP_QT_IMPORT = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ

try:
    if _SKIP_QT_IMPORT:
        raise RuntimeError("Skip Qt import while running tests")
    from PyQt6.QtCore import QObject, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
    from PyQt6.QtGui import QColor
    from PyQt6.QtQuickWidgets import QQuickWidget
    from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout
except Exception:  # pragma: no cover - fallback for test environments without Qt runtime
    class QObject:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            pass

    class _Signal:
        def __init__(self):
            self._callbacks = []

        def connect(self, callback):
            self._callbacks.append(callback)

        def emit(self, *args, **kwargs):
            for callback in list(self._callbacks):
                callback(*args, **kwargs)

    class _SignalDescriptor:
        def __init__(self):
            self._name = ""

        def __set_name__(self, owner, name):
            self._name = f"__signal_{name}"

        def __get__(self, instance, owner):
            if instance is None:
                return self
            signal = getattr(instance, self._name, None)
            if signal is None:
                signal = _Signal()
                setattr(instance, self._name, signal)
            return signal

    def pyqtSignal(*_args, **_kwargs):  # type: ignore[no-redef]
        return _SignalDescriptor()

    def pyqtSlot(*_args, **_kwargs):  # type: ignore[no-redef]
        def _decorator(func):
            return func
        return _decorator

    def pyqtProperty(*_args, **_kwargs):  # type: ignore[no-redef]
        def _decorator(func):
            return property(func)
        return _decorator

    class Qt:  # type: ignore[no-redef]
        class WindowType:
            FramelessWindowHint = 0

        class WidgetAttribute:
            WA_TranslucentBackground = 0

    class QUrl:  # type: ignore[no-redef]
        def __init__(self, path=""):
            self._path = path

        @staticmethod
        def fromLocalFile(path):
            return QUrl(path)

    class QColor:  # type: ignore[no-redef]
        def __init__(self, *_args, **_kwargs):
            pass

    class _DummyContext:
        def setContextProperty(self, *_args, **_kwargs):
            return None

    class QQuickWidget:  # type: ignore[no-redef]
        class ResizeMode:
            SizeRootObjectToView = 0

        class Status:
            Error = "error"

        def __init__(self, *_args, **_kwargs):
            self._context = _DummyContext()

        def setClearColor(self, *_args, **_kwargs):
            return None

        def setResizeMode(self, *_args, **_kwargs):
            return None

        def rootContext(self):
            return self._context

        def setSource(self, *_args, **_kwargs):
            return None

        def status(self):
            return None

        def errors(self):
            return []

    class QApplication:  # type: ignore[no-redef]
        @staticmethod
        def screenAt(*_args, **_kwargs):
            return None

        @staticmethod
        def primaryScreen():
            return None

    class QDialog:  # type: ignore[no-redef]
        def __init__(self, *_args, **_kwargs):
            pass

        def setObjectName(self, *_args, **_kwargs):
            return None

        def setWindowTitle(self, *_args, **_kwargs):
            return None

        def setModal(self, *_args, **_kwargs):
            return None

        def setWindowFlag(self, *_args, **_kwargs):
            return None

        def setAttribute(self, *_args, **_kwargs):
            return None

        def resize(self, *_args, **_kwargs):
            return None

        def setMinimumSize(self, *_args, **_kwargs):
            return None

        def reject(self):
            return None

        def accept(self):
            return None

        def showEvent(self, *_args, **_kwargs):
            return None

    class QVBoxLayout:  # type: ignore[no-redef]
        def __init__(self, *_args, **_kwargs):
            pass

        def setContentsMargins(self, *_args, **_kwargs):
            return None

        def setSpacing(self, *_args, **_kwargs):
            return None

        def addWidget(self, *_args, **_kwargs):
            return None

from aica.analysis.metrics import AnalysisRunStats
from aica.feedback import FeedbackData
from aica.models import TicketSnapshot, TicketSummaryFields
from aica.runtime import RUNTIME_CAPABILITIES
from aica.ticket_field_resolver import (
    TICKET_TYPE_OPTIONS,
    normalize_ticket_type,
    resolve_product_line,
)
from aica.text_sanitize import sanitize_text, strip_invalid_surrogates

_UNKNOWN_TEXT = "\u672a\u77e5"
_UNCLASSIFIED_TASK = "\u672a\u5206\u7c7b\u4efb\u52a1"
_PENDING_TEXT = "\u5f85\u8865\u5145"
_SAVE_HINT = "\u4fdd\u5b58\u540e\u4f1a\u521b\u5efa\u5f85\u529e\u6216\u8ffd\u52a0\u5230\u5f53\u524d\u9009\u4e2d\u7684\u5f85\u529e\u3002"


def _clean_text(value: str, fallback: str = _UNKNOWN_TEXT) -> str:
    text = sanitize_text(value)
    return text or fallback


def _sanitize_edit_text(value: object) -> str:
    return strip_invalid_surrogates(str(value or ""))


class _ResultDialogBridge(QObject):
    dataChanged = pyqtSignal()

    closeRequested = pyqtSignal()
    saveRequested = pyqtSignal()
    feedbackRequested = pyqtSignal()

    def __init__(
        self,
        result: TicketSnapshot,
        scenario: str,
        model: str,
        show_feedback: bool,
        analysis_stats: AnalysisRunStats | None = None,
    ) -> None:
        super().__init__()
        self._scenario = scenario
        self._model = model
        self._timing_summary = analysis_stats.timing_summary if analysis_stats is not None else ""
        self._show_feedback = show_feedback
        self._fallback_title = sanitize_text(result.title) or _UNCLASSIFIED_TASK
        self._title = sanitize_text(result.title)
        self._group_name = _clean_text(result.fields.group_name)
        self._environment = _clean_text(result.fields.environment)
        self._product_line = resolve_product_line(raw_value=result.fields.product_line)
        self._recognition_conclusion = sanitize_text(result.timeline_entry) or sanitize_text(result.current_summary)
        self._ticket_type = normalize_ticket_type(
            result.fields.ticket_type,
            summary_text=self._recognition_conclusion,
        )

    @pyqtProperty(str, notify=dataChanged)
    def scenario(self) -> str:
        return self._scenario

    @pyqtProperty(str, constant=True)
    def uiFont(self) -> str:
        return RUNTIME_CAPABILITIES.ui_font

    @pyqtProperty(str, notify=dataChanged)
    def model(self) -> str:
        return self._model

    @pyqtProperty(str, notify=dataChanged)
    def timingSummary(self) -> str:
        return self._timing_summary

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
    def recognitionConclusion(self) -> str:
        return self._recognition_conclusion

    @pyqtProperty(bool, notify=dataChanged)
    def showFeedbackAction(self) -> bool:
        return self._show_feedback

    @pyqtProperty(str, constant=True)
    def saveHint(self) -> str:
        return _SAVE_HINT

    @pyqtSlot(str, str)
    def updateField(self, name: str, value: str) -> None:
        text = _sanitize_edit_text(value)
        if name == "title":
            self._title = text
        elif name == "group_name":
            self._group_name = text
        elif name == "environment":
            self._environment = text
        elif name == "product_line":
            self._product_line = resolve_product_line(raw_value=text)
        elif name == "ticket_type":
            self._ticket_type = normalize_ticket_type(text, summary_text=self._recognition_conclusion)
        elif name == "timeline_entry":
            self._recognition_conclusion = text
        else:
            return
        self.dataChanged.emit()

    def build_snapshot(self) -> TicketSnapshot:
        normalized_conclusion = self._recognition_conclusion.strip() or _PENDING_TEXT
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
                            normalized_conclusion,
                        )
                        if part
                    ),
                ),
            ),
            current_summary=normalized_conclusion,
            timeline_entry=normalized_conclusion,
            evidence_items=[],
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
        analysis_stats: AnalysisRunStats | None = None,
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
            analysis_stats=analysis_stats,
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
