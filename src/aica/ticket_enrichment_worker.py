"""Qt worker wrapper for asynchronous ticket enrichment."""
from __future__ import annotations

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

from .ticket_enrichment import EnrichmentOutcome, TicketEnrichmentJob, TicketEnrichmentService


class TicketEnrichmentWorker(QThread):
    finished = pyqtSignal(str, str, object)
    error = pyqtSignal(str, str, str)

    def __init__(
        self,
        *,
        enrichment_service: TicketEnrichmentService,
        request_id: str,
        job: TicketEnrichmentJob,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._enrichment_service = enrichment_service
        self._request_id = str(request_id or "").strip()
        self._job = job

    def run(self) -> None:
        try:
            outcome = self._enrichment_service.enrich_for_update(
                previous_fields=self._job.previous_fields,
                current_fields=self._job.current_fields,
                previous_problem_desc=self._job.previous_problem_desc,
                current_problem_desc=self._job.current_problem_desc,
                previous_conclusion=self._job.previous_conclusion,
                current_conclusion=self._job.current_conclusion,
            )
        except Exception as exc:  # noqa: BLE001
            self.error.emit(self._job.todo_id, self._request_id, str(exc))
            return
        if not isinstance(outcome, EnrichmentOutcome):
            outcome = EnrichmentOutcome(summary_fields=self._job.current_fields, errors=[])
        self.finished.emit(self._job.todo_id, self._request_id, outcome)
