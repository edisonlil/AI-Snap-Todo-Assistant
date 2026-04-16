"""Qt worker wrapper for log analysis tasks."""
import os
import sys

_SKIP_QT_IMPORT = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ

try:
    if _SKIP_QT_IMPORT:
        raise RuntimeError("Skip Qt import while running tests")
    from PyQt6.QtCore import QThread, pyqtSignal
except Exception:  # pragma: no cover
    class QThread:  # type: ignore[no-redef]
        def __init__(self, parent=None):
            self._parent = parent

        def start(self):
            return None

        def deleteLater(self):
            return None

    def pyqtSignal(*_args, **_kwargs):  # type: ignore[no-redef]
        return None

from .log_analysis_orchestrator import LogAnalysisOrchestrator


class LogAnalysisWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str, str)

    def __init__(self, *, orchestrator: LogAnalysisOrchestrator, task_id: str, parent=None) -> None:
        super().__init__(parent)
        self._orchestrator = orchestrator
        self._task_id = task_id

    def run(self) -> None:
        try:
            self._orchestrator.run_task(self._task_id)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(self._task_id, str(exc))
            return
        self.finished.emit(self._task_id)
