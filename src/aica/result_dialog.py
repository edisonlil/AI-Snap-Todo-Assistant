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
from aica.models import TicketSnapshot, TicketSummaryFields, is_unknown_text
from aica.runtime import RUNTIME_CAPABILITIES
from aica.storage.contracts import ProjectMatchCandidate, ProjectMatchResult
from aica.storage.sqlite.repositories import SQLiteProjectRepository
from aica.theme_controller import ThemeController
from aica.ticket_field_resolver import (
    TICKET_TYPE_OPTIONS,
    normalize_ticket_type,
)
from aica.text_sanitize import sanitize_text, strip_invalid_surrogates
from aica.window_effects import disable_windows_window_border

_UNKNOWN_TEXT = "\u672a\u77e5"
_UNCLASSIFIED_TASK = "\u672a\u5206\u7c7b\u4efb\u52a1"
_PENDING_TEXT = "\u5f85\u8865\u5145"
_SAVE_HINT = "\u4fdd\u5b58\u540e\u4f1a\u521b\u5efa\u5f85\u529e\u6216\u8ffd\u52a0\u5230\u5f53\u524d\u9009\u4e2d\u7684\u5f85\u529e\u3002"


def _clean_text(value: str, fallback: str = _UNKNOWN_TEXT) -> str:
    text = sanitize_text(value)
    return text or fallback


def _sanitize_edit_text(value: object) -> str:
    return strip_invalid_surrogates(str(value or ""))


def _call_candidate_provider(provider, group_name: str) -> object:  # noqa: ANN001
    try:
        return provider(group_name)
    except TypeError:
        return provider()


class _ResultDialogBridge(QObject):
    dataChanged = pyqtSignal()

    closeRequested = pyqtSignal()
    saveRequested = pyqtSignal()
    dragRequested = pyqtSignal()
    projectCandidateSelected = pyqtSignal()

    def __init__(
        self,
        result: TicketSnapshot,
        scenario: str,
        model: str,
        analysis_stats: AnalysisRunStats | None = None,
        project_candidate_provider=None,
        latest_issue_product_provider=None,
        latest_environment_provider=None,
        project_match_provider=None,
    ) -> None:
        super().__init__()
        self._project_candidate_provider = project_candidate_provider
        self._latest_issue_product_provider = latest_issue_product_provider
        self._latest_environment_provider = latest_environment_provider
        self._project_match_provider = project_match_provider
        self._scenario = scenario
        self._model = model
        self._timing_summary = analysis_stats.timing_summary if analysis_stats is not None else ""
        self._fallback_title = sanitize_text(result.title) or _UNCLASSIFIED_TASK
        self._title = sanitize_text(result.title)
        self._group_name = _clean_text(result.fields.group_name)
        self._environment = _clean_text(result.fields.environment)
        self._environment_manual = not is_unknown_text(result.fields.environment)
        self._product_line = sanitize_text(result.fields.product_line)
        self._issue_product = sanitize_text(result.fields.issue_product)
        self._issue_product_manual = bool(self._issue_product.strip())
        self._product_line_error = ""
        self._project_candidates: list[dict[str, object]] = []
        self._selected_project_candidate: dict[str, object] = {}
        self._recognition_conclusion = sanitize_text(result.timeline_entry) or sanitize_text(result.current_summary)
        self._ticket_type = normalize_ticket_type(
            result.fields.ticket_type,
            summary_text=self._recognition_conclusion,
        )
        self._refresh_project_candidates()
        self._apply_matched_project_issue_product_default()

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
    def issueProduct(self) -> str:
        return self._issue_product

    @pyqtProperty(str, notify=dataChanged)
    def productLineError(self) -> str:
        return self._product_line_error

    @pyqtProperty("QVariantList", notify=dataChanged)
    def projectCandidates(self):  # noqa: ANN201
        return list(self._project_candidates)

    @pyqtProperty("QVariantMap", notify=dataChanged)
    def selectedProjectCandidate(self):  # noqa: ANN201
        return dict(self._selected_project_candidate)

    @pyqtProperty(bool, notify=dataChanged)
    def hasProjectCandidateSelection(self) -> bool:
        return bool(self._selected_project_candidate)

    @pyqtProperty(str, notify=dataChanged)
    def ticketType(self) -> str:
        return self._ticket_type

    @pyqtProperty("QVariantList", constant=True)
    def ticketTypeOptions(self):  # noqa: ANN201
        return list(TICKET_TYPE_OPTIONS)

    @pyqtProperty(str, notify=dataChanged)
    def recognitionConclusion(self) -> str:
        return self._recognition_conclusion

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
            self._refresh_project_candidates()
            self._apply_matched_project_environment_default()
            self._apply_matched_project_issue_product_default()
        elif name == "environment":
            self._environment = text
            self._environment_manual = not is_unknown_text(text)
        elif name == "issue_product":
            self._issue_product = text
            self._issue_product_manual = bool(text.strip())
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
        project_link = {}
        if self._selected_project_candidate:
            project_snapshot = dict(self._selected_project_candidate.get("projectSnapshot") or {})
            project_link = {
                "project_id": str(self._selected_project_candidate.get("projectId") or ""),
                "projectId": str(self._selected_project_candidate.get("projectId") or ""),
                "project_name": str(self._selected_project_candidate.get("projectName") or ""),
                "projectName": str(self._selected_project_candidate.get("projectName") or ""),
                "matched_alias": str(self._selected_project_candidate.get("matchedAlias") or ""),
                "matchedAlias": str(self._selected_project_candidate.get("matchedAlias") or ""),
                "match_reason": str(self._selected_project_candidate.get("matchReason") or ""),
                "matchReason": str(self._selected_project_candidate.get("matchReason") or ""),
                "match_status": "manual",
                "matchStatus": "manual",
                "project_snapshot": project_snapshot,
                "projectSnapshot": project_snapshot,
            }
        return TicketSnapshot(
            title=normalized_title,
            fields=TicketSummaryFields(
                group_name=_clean_text(self._group_name),
                environment=_clean_text(self._environment),
                product_line=self._product_line,
                issue_product=self._issue_product.strip(),
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
            project_link=project_link,
        )

    @pyqtSlot()
    def closeDialog(self) -> None:
        self.closeRequested.emit()

    @pyqtSlot()
    def saveDialog(self) -> None:
        self.saveRequested.emit()

    @pyqtSlot("QVariantMap")
    def chooseProjectCandidate(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        project_id = sanitize_text(payload.get("projectId") or payload.get("project_id"))
        if not project_id:
            return
        matched = next(
            (candidate for candidate in self._project_candidates if str(candidate.get("projectId") or "") == project_id),
            None,
        )
        if matched is None:
            return
        self._selected_project_candidate = dict(matched)
        preferred_group_name = sanitize_text(matched.get("matchedAlias") or matched.get("matched_alias"))
        if not preferred_group_name:
            preferred_group_name = sanitize_text(matched.get("projectName") or matched.get("project_name"))
        if preferred_group_name:
            self._group_name = preferred_group_name
        self._apply_environment_default(str(matched.get("projectId") or ""))
        self._apply_issue_product_default(str(matched.get("projectId") or ""))
        self.dataChanged.emit()

    def _apply_environment_default(self, project_id: str) -> None:
        if self._environment_manual and sanitize_text(self._environment).strip():
            return
        provider = self._latest_environment_provider
        if not callable(provider):
            return
        normalized_project_id = sanitize_text(project_id)
        if not normalized_project_id:
            return
        try:
            latest_environment = sanitize_text(provider(normalized_project_id))
        except Exception:
            latest_environment = ""
        if latest_environment and not is_unknown_text(latest_environment):
            self._environment = latest_environment
            self._environment_manual = False

    def _apply_issue_product_default(self, project_id: str) -> None:
        if self._issue_product_manual and self._issue_product.strip():
            return
        provider = self._latest_issue_product_provider
        if not callable(provider):
            return
        normalized_project_id = sanitize_text(project_id)
        if not normalized_project_id:
            return
        try:
            latest_issue_product = sanitize_text(provider(normalized_project_id))
        except Exception:
            latest_issue_product = ""
        if latest_issue_product:
            self._issue_product = latest_issue_product
            self._issue_product_manual = False

    def _apply_matched_project_environment_default(self) -> None:
        project_id = self._resolve_issue_product_default_project_id()
        if project_id:
            self._apply_environment_default(project_id)

    def _apply_matched_project_issue_product_default(self) -> None:
        project_id = self._resolve_issue_product_default_project_id()
        if project_id:
            self._apply_issue_product_default(project_id)

    def _resolve_issue_product_default_project_id(self) -> str:
        provider = self._project_match_provider
        if callable(provider):
            try:
                match_result = provider(self._group_name)
            except Exception:
                match_result = None
            if isinstance(match_result, ProjectMatchResult):
                if sanitize_text(match_result.status) == "matched":
                    return sanitize_text(match_result.project_id)
        if len(self._project_candidates) == 1:
            return sanitize_text(self._project_candidates[0].get("projectId") or "")
        return ""

    def _refresh_project_candidates(self) -> None:
        repository_provider = getattr(self, "_project_candidate_provider", None)
        candidates: list[dict[str, object]] = []
        if callable(repository_provider):
            try:
                raw_candidates = _call_candidate_provider(repository_provider, self._group_name)
            except Exception:
                raw_candidates = []
            if isinstance(raw_candidates, list):
                for item in raw_candidates:
                    if isinstance(item, ProjectMatchCandidate):
                        candidates.append(item.to_dict())
                    elif isinstance(item, dict):
                        candidates.append(
                            {
                                "projectId": sanitize_text(item.get("projectId") or item.get("project_id")),
                                "projectName": sanitize_text(item.get("projectName") or item.get("project_name")),
                                "taskOrderNo": sanitize_text(item.get("taskOrderNo") or item.get("task_order_no")),
                                "customerName": sanitize_text(item.get("customerName") or item.get("customer_name")),
                                "matchedAlias": sanitize_text(item.get("matchedAlias") or item.get("matched_alias")),
                                "matchReason": sanitize_text(item.get("matchReason") or item.get("match_reason")),
                                "matchScore": int(item.get("matchScore") or item.get("match_score") or 0),
                                "isExpired": bool(item.get("isExpired") or item.get("is_expired")),
                                "projectSnapshot": dict(item.get("projectSnapshot") or item.get("project_snapshot") or {}),
                            }
                        )
        self._project_candidates = candidates
        if self._selected_project_candidate:
            selected_id = str(self._selected_project_candidate.get("projectId") or "")
            if not any(str(item.get("projectId") or "") == selected_id for item in candidates):
                self._selected_project_candidate = {}

    @pyqtSlot()
    def startWindowDrag(self) -> None:
        self.dragRequested.emit()


class ResultDialog(QDialog):
    """Displays a structured ticket snapshot for review before saving."""

    def __init__(
        self,
        result: TicketSnapshot,
        scenario: str,
        model: str,
        analysis_stats: AnalysisRunStats | None = None,
        save_callback: Optional[Callable] = None,
        project_candidate_provider=None,
        latest_issue_product_provider=None,
        latest_environment_provider=None,
        project_match_provider=None,
        parent=None,
        theme_controller: ThemeController | None = None,
    ):
        super().__init__(parent)
        self._theme_controller = theme_controller or ThemeController()
        self._original_result = result
        self._scenario = scenario
        self._model = model
        self._save_callback = save_callback
        self._product_line_repository = (
            None
            if callable(latest_issue_product_provider)
            else SQLiteProjectRepository()
        )
        self._latest_issue_product_provider = (
            latest_issue_product_provider
            if callable(latest_issue_product_provider)
            else self._product_line_repository.latest_issue_product_for_project
        )
        self._latest_environment_provider = (
            latest_environment_provider
            if callable(latest_environment_provider)
            else self._product_line_repository.latest_environment_for_project
        )
        self._project_match_provider = (
            project_match_provider
            if callable(project_match_provider)
            else self._product_line_repository.match_project_by_group_name
        )
        self._positioned = False

        self._bridge = _ResultDialogBridge(
            result=result,
            scenario=scenario,
            model=model,
            analysis_stats=analysis_stats,
            project_candidate_provider=project_candidate_provider
            if callable(project_candidate_provider)
            else getattr(self._product_line_repository, "search_project_candidates_by_group_name", None),
            latest_issue_product_provider=self._latest_issue_product_provider,
            latest_environment_provider=self._latest_environment_provider,
            project_match_provider=self._project_match_provider,
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
        self._bridge.dragRequested.connect(self._start_system_move)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._view = QQuickWidget(self)
        self._view.setClearColor(QColor(0, 0, 0, 0))
        self._view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._theme_controller.apply_to_context(self._view.rootContext())
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
        disable_windows_window_border(self)
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

    def _start_system_move(self) -> None:
        window_handle = self.windowHandle()
        if window_handle is None:
            self.activateWindow()
            return
        try:
            window_handle.startSystemMove()
        except AttributeError:
            self.activateWindow()

    def _build_snapshot(self) -> TicketSnapshot:
        return self._bridge.build_snapshot()

    def _on_save(self) -> None:
        snapshot = self._build_snapshot()
        if self._save_callback:
            self._save_callback(snapshot)
        self.accept()
