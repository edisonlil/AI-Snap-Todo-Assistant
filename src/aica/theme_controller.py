"""Qt-facing theme controller."""
from __future__ import annotations

try:
    from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal
except Exception:  # pragma: no cover - test fallback for non-Qt environments
    class QObject:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            super().__init__()

    class _Signal:
        def connect(self, *_args, **_kwargs):
            return None

        def emit(self, *_args, **_kwargs):
            return None

    def pyqtSignal(*_args, **_kwargs):  # type: ignore[no-redef]
        return _Signal()

    def pyqtProperty(*_args, **_kwargs):  # type: ignore[no-redef]
        def decorator(func):
            return property(func)

        return decorator

from aica.theme import ThemeConfig, build_theme_tokens


class ThemeController(QObject):
    themeChanged = pyqtSignal()

    def __init__(self, config: ThemeConfig | object | None = None, parent=None) -> None:
        super().__init__(parent)
        self._config = config if isinstance(config, ThemeConfig) else ThemeConfig.from_dict(config)
        self._tokens = build_theme_tokens(self._config).to_dict()
        self._contexts: list[object] = []

    @pyqtProperty("QVariantMap", notify=themeChanged)
    def config(self):  # noqa: ANN201
        return self._config.to_dict()

    @pyqtProperty("QVariantMap", notify=themeChanged)
    def tokens(self):  # noqa: ANN201
        return dict(self._tokens)

    def set_config(self, config: ThemeConfig | object) -> None:
        next_config = config if isinstance(config, ThemeConfig) else ThemeConfig.from_dict(config)
        if next_config.to_dict() == self._config.to_dict():
            return
        self._config = next_config
        self._tokens = build_theme_tokens(self._config).to_dict()
        self._sync_contexts()
        self.themeChanged.emit()

    def apply_to_context(self, context) -> None:
        if not any(item is context for item in self._contexts):
            self._contexts.append(context)
        if not self._apply_theme_to_context(context):
            self._contexts = [item for item in self._contexts if item is not context]

    def _sync_contexts(self) -> None:
        live_contexts = []
        for context in self._contexts:
            if self._apply_theme_to_context(context):
                live_contexts.append(context)
        self._contexts = live_contexts

    def _apply_theme_to_context(self, context) -> bool:
        try:
            context.setContextProperty("theme", self.tokens)
        except (RuntimeError, ReferenceError):
            return False
        return True
