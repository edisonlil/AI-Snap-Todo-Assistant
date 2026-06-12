from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, sin

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QPainter, QPen, QPixmap, QPolygon, QScreen
from PyQt6.QtWidgets import QApplication, QLineEdit, QWidget

from .runtime import RUNTIME_CAPABILITIES
from .theme_controller import ThemeController


def normalize_rect(p1: QPoint, p2: QPoint) -> QRect:
    """Normalize any two points into a top-left/bottom-right QRect."""
    return QRect(
        min(p1.x(), p2.x()),
        min(p1.y(), p2.y()),
        abs(p2.x() - p1.x()),
        abs(p2.y() - p1.y()),
    )


def translate_rect_within_bounds(rect: QRect, delta: QPoint, bounds: QRect) -> QRect:
    """Move a QRect by delta while keeping the whole rect inside bounds."""
    max_x = bounds.left() + max(0, bounds.width() - rect.width())
    max_y = bounds.top() + max(0, bounds.height() - rect.height())
    x = min(max(rect.x() + delta.x(), bounds.left()), max_x)
    y = min(max(rect.y() + delta.y(), bounds.top()), max_y)
    return QRect(x, y, rect.width(), rect.height())


def resize_rect_within_bounds(
    rect: QRect,
    handle: str,
    point: QPoint,
    bounds: QRect,
    min_size: int = 1,
) -> QRect:
    """Resize a QRect from one corner while keeping it inside bounds."""
    min_size = max(1, min_size)
    left = rect.left()
    top = rect.top()
    right = rect.left() + rect.width()
    bottom = rect.top() + rect.height()
    bounds_left = bounds.left()
    bounds_top = bounds.top()
    bounds_right = bounds.left() + bounds.width()
    bounds_bottom = bounds.top() + bounds.height()
    drag_x = point.x() + (1 if handle in {"top_right", "bottom_right"} else 0)
    drag_y = point.y() + (1 if handle in {"bottom_left", "bottom_right"} else 0)

    if handle == "top_left":
        new_left = min(max(drag_x, bounds_left), right - min_size)
        new_top = min(max(drag_y, bounds_top), bottom - min_size)
        return QRect(new_left, new_top, right - new_left, bottom - new_top)
    if handle == "top_right":
        new_right = min(max(drag_x, left + min_size), bounds_right)
        new_top = min(max(drag_y, bounds_top), bottom - min_size)
        return QRect(left, new_top, new_right - left, bottom - new_top)
    if handle == "bottom_left":
        new_left = min(max(drag_x, bounds_left), right - min_size)
        new_bottom = min(max(drag_y, top + min_size), bounds_bottom)
        return QRect(new_left, top, right - new_left, new_bottom - top)
    if handle == "bottom_right":
        new_right = min(max(drag_x, left + min_size), bounds_right)
        new_bottom = min(max(drag_y, top + min_size), bounds_bottom)
        return QRect(left, top, new_right - left, new_bottom - top)
    return QRect(rect)


@dataclass
class TextAnnotation:
    position: QPoint
    text: str


@dataclass
class ArrowAnnotation:
    start: QPoint
    end: QPoint


class InlineTextEdit(QLineEdit):
    commit_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.commit_requested.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class OverlayWindow(QWidget):
    """Single-screen capture overlay with post-selection editing."""

    selection_complete = pyqtSignal(QRect, object)
    selection_changed = pyqtSignal(QRect)
    cancelled = pyqtSignal()

    _MIN_SELECTION_PX = 5
    _EDIT_MODES = {"move", "rect", "arrow", "text"}
    _TEXT_PLACEHOLDER = "输入文字"
    _SELECTION_COLOR = QColor(22, 119, 255)
    _SELECTION_PENDING_COLOR = QColor(144, 202, 249)
    _SELECTION_MASK_COLOR = QColor(0, 0, 0, 76)
    _ANNOTATION_COLOR = QColor(255, 77, 79)
    _HANDLE_FILL_COLOR = QColor(255, 255, 255, 244)
    _HANDLE_SIZE = 8
    _HANDLE_CURSORS = {
        "top_left": Qt.CursorShape.SizeBDiagCursor,
        "top_right": Qt.CursorShape.SizeFDiagCursor,
        "bottom_left": Qt.CursorShape.SizeFDiagCursor,
        "bottom_right": Qt.CursorShape.SizeBDiagCursor,
    }

    def __init__(self, screen: QScreen, parent=None, *, theme_controller: ThemeController | None = None):
        super().__init__(parent)
        self._theme_controller = theme_controller or ThemeController()
        self._screen_key = self._make_screen_key(screen)
        self.setWindowFlags(RUNTIME_CAPABILITIES.overlay_window_flags(Qt.WindowType))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._bg_pixmap: QPixmap | None = None
        self._start: QPoint | None = None
        self._end: QPoint | None = None
        self._selection_rect: QRect | None = None
        self._dragging = False
        self._drag_mode: str | None = None
        self._selection_locked = False
        self._edit_mode = "move"
        self._move_start: QPoint | None = None
        self._move_origin_rect: QRect | None = None
        self._resize_handle: str | None = None
        self._resize_origin_rect: QRect | None = None
        self._rects: list[QRect] = []
        self._texts: list[TextAnnotation] = []
        self._arrows: list[ArrowAnnotation] = []
        self._history: list[tuple[str, object]] = []
        self._text_editor_origin: QPoint | None = None
        self._text_editor = InlineTextEdit(self)
        self._text_editor.hide()
        self._text_editor.setPlaceholderText(self._TEXT_PLACEHOLDER)
        self._text_editor.setFrame(False)
        self._text_editor.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self._theme_controller.themeChanged.connect(self._apply_text_editor_style)
        self._apply_text_editor_style()
        self._text_editor.commit_requested.connect(self._commit_pending_text_annotation)
        self._text_editor.cancel_requested.connect(self._cancel_pending_text_annotation)
        self._text_editor.editingFinished.connect(self._on_text_editor_editing_finished)
        self._text_editor.textChanged.connect(self._resize_text_editor)

    def _apply_text_editor_style(self) -> None:
        theme = self._theme_controller.tokens
        self._text_editor.setStyleSheet(
            """
            QLineEdit {
                color: %(titleInk)s;
                background-color: %(overlayTextBg)s;
                border: 1px solid %(accent)s;
                border-radius: %(radiusSm)spx;
                padding: 5px 8px;
                selection-background-color: %(overlaySelectionBg)s;
                font-size: %(fontBody)spx;
                font-family: %(widgetFontCss)s;
            }
            """
            % {
                **theme,
                "widgetFontCss": str(theme.get("widgetFontCss") or RUNTIME_CAPABILITIES.widget_font_css),
            }
        )

    @staticmethod
    def _make_screen_key(screen: QScreen) -> str:
        geometry = screen.geometry()
        return (
            f"{screen.name()}|{geometry.x()}|{geometry.y()}|"
            f"{geometry.width()}|{geometry.height()}"
        )

    def _resolve_screen(self) -> QScreen | None:
        screens = QApplication.screens()
        if not screens:
            return None

        for screen in screens:
            if self._make_screen_key(screen) == self._screen_key:
                return screen

        target_name = self._screen_key.split("|", 1)[0]
        for screen in screens:
            if screen.name() == target_name:
                self._screen_key = self._make_screen_key(screen)
                return screen

        fallback = QApplication.primaryScreen()
        if fallback is not None:
            self._screen_key = self._make_screen_key(fallback)
        return fallback

    def screen_geometry(self) -> QRect:
        screen = self._resolve_screen()
        if screen is None:
            return QRect()
        return screen.geometry()

    def show_overlay(self) -> None:
        screen = self._resolve_screen()
        if screen is None:
            return

        self.hide()
        self.setWindowState(Qt.WindowState.WindowNoState)
        self._bg_pixmap = screen.grabWindow(0)
        self._reset_editor_state()
        self.setGeometry(screen.geometry())

        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def dismiss_overlay(self) -> None:
        self._reset_editor_state()
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.setWindowState(Qt.WindowState.WindowNoState)
        self.hide()

    def suspend_overlay(self) -> None:
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.hide()

    def resume_overlay(self) -> None:
        if self._bg_pixmap is None:
            return
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        self._update_hover_cursor()
        self.update()

    def has_selection(self) -> bool:
        return self._selection_rect is not None

    def lock_selection(self) -> None:
        if self._selection_rect is None:
            self._selection_rect = self._current_rect()
        self._selection_locked = self._selection_rect is not None
        self._dragging = False
        self._drag_mode = None
        self._move_start = None
        self._move_origin_rect = None
        self._resize_handle = None
        self._resize_origin_rect = None
        self._edit_mode = "move"
        self._update_hover_cursor()
        self.update()

    def set_edit_mode(self, mode: str) -> None:
        if mode not in self._EDIT_MODES:
            return
        if self._edit_mode == "text" and mode != "text":
            self._commit_pending_text_annotation()
        self._edit_mode = mode
        self._update_hover_cursor()

    def undo_last_annotation(self) -> None:
        if self._text_editor.isVisible():
            self._cancel_pending_text_annotation()
            return
        if not self._history:
            return
        kind, _payload = self._history.pop()
        if kind == "rect" and self._rects:
            self._rects.pop()
        elif kind == "text" and self._texts:
            self._texts.pop()
        elif kind == "arrow" and self._arrows:
            self._arrows.pop()
        self.update()

    def clear_annotations(self) -> None:
        self._cancel_pending_text_annotation()
        self._rects.clear()
        self._texts.clear()
        self._arrows.clear()
        self._history.clear()
        self._start = None
        self._end = None
        self._dragging = False
        self._drag_mode = None
        self._resize_handle = None
        self._resize_origin_rect = None
        self.update()

    def current_global_selection(self) -> QRect | None:
        if self._selection_rect is None:
            return None
        return self._selection_rect.translated(self.geometry().topLeft())

    def export_selection_pixmap(self) -> QPixmap:
        self._commit_pending_text_annotation()
        cropped = self._crop_selection_pixmap()
        if cropped is None:
            return QPixmap()

        annotated = QPixmap.fromImage(cropped.toImage())
        annotated.setDevicePixelRatio(1.0)

        painter = QPainter(annotated)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        dpr = cropped.devicePixelRatio() or 1.0
        if dpr != 1.0:
            painter.scale(dpr, dpr)
        self._paint_annotations(painter)
        painter.end()
        return annotated

    def _reset_editor_state(self) -> None:
        self._start = None
        self._end = None
        self._selection_rect = None
        self._dragging = False
        self._drag_mode = None
        self._selection_locked = False
        self._edit_mode = "move"
        self._move_start = None
        self._move_origin_rect = None
        self._resize_handle = None
        self._resize_origin_rect = None
        self._rects.clear()
        self._texts.clear()
        self._arrows.clear()
        self._history.clear()
        self._cancel_pending_text_annotation()

    def _current_rect(self) -> QRect | None:
        if self._start is None or self._end is None:
            return None
        rect = normalize_rect(self._start, self._end)
        if rect.width() < self._MIN_SELECTION_PX or rect.height() < self._MIN_SELECTION_PX:
            return None
        return rect

    def _active_rect(self) -> QRect | None:
        if self._selection_rect is not None:
            return self._selection_rect
        return self._current_rect()

    def _crop_selection_pixmap(self) -> QPixmap | None:
        if self._bg_pixmap is None or self._selection_rect is None:
            return None

        rect = self._selection_rect
        dpr = self._bg_pixmap.devicePixelRatio() or 1.0
        if dpr != 1.0:
            scaled_rect = QRect(
                int(round(rect.x() * dpr)),
                int(round(rect.y() * dpr)),
                max(1, int(round(rect.width() * dpr))),
                max(1, int(round(rect.height() * dpr))),
            )
            cropped = self._bg_pixmap.copy(scaled_rect)
            cropped.setDevicePixelRatio(dpr)
            return cropped
        return self._bg_pixmap.copy(rect)

    def _selection_local_point(self, point: QPoint) -> QPoint:
        if self._selection_rect is None:
            return QPoint()
        x = min(max(point.x() - self._selection_rect.left(), 0), self._selection_rect.width())
        y = min(max(point.y() - self._selection_rect.top(), 0), self._selection_rect.height())
        return QPoint(x, y)

    def _update_hover_cursor(self) -> None:
        if not self._selection_locked:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            return

        local_pos = self.mapFromGlobal(QCursor.pos())
        handle = self._selection_handle_at(local_pos)
        if handle is not None:
            cursor = self._HANDLE_CURSORS[handle]
        elif self._selection_rect and self._selection_rect.contains(local_pos):
            if self._edit_mode == "move":
                cursor = Qt.CursorShape.OpenHandCursor
            elif self._edit_mode == "text":
                cursor = Qt.CursorShape.IBeamCursor
            else:
                cursor = Qt.CursorShape.CrossCursor
        else:
            cursor = Qt.CursorShape.ArrowCursor
        self.setCursor(QCursor(cursor))

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self._bg_pixmap:
            painter.drawPixmap(0, 0, self._bg_pixmap)

        rect = self._active_rect()
        if rect is not None:
            self._paint_mask(painter, rect)
            self._paint_selection_frame(painter, rect)

            if self._selection_locked:
                painter.save()
                painter.setClipRect(rect)
                painter.translate(rect.topLeft())
                self._paint_annotations(painter)
                painter.restore()
        else:
            painter.fillRect(self.rect(), self._SELECTION_MASK_COLOR)

        painter.end()

    def _paint_mask(self, painter: QPainter, rect: QRect) -> None:
        painter.fillRect(QRect(0, 0, self.width(), rect.top()), self._SELECTION_MASK_COLOR)
        painter.fillRect(QRect(0, rect.top(), rect.left(), rect.height()), self._SELECTION_MASK_COLOR)
        painter.fillRect(
            QRect(rect.right() + 1, rect.top(), self.width() - rect.right() - 1, rect.height()),
            self._SELECTION_MASK_COLOR,
        )
        painter.fillRect(
            QRect(0, rect.bottom() + 1, self.width(), self.height() - rect.bottom() - 1),
            self._SELECTION_MASK_COLOR,
        )

    def _paint_selection_frame(self, painter: QPainter, rect: QRect) -> None:
        border_color = self._SELECTION_COLOR if self._selection_locked else self._SELECTION_PENDING_COLOR
        border_pen = QPen(border_color, 2)
        border_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(border_pen)
        painter.drawRect(rect)
        self._paint_size_badge(painter, rect)
        if self._selection_locked:
            self._paint_selection_handles(painter, rect)

    def _paint_size_badge(self, painter: QPainter, rect: QRect) -> None:
        if rect.width() <= 0 or rect.height() <= 0:
            return

        label = f"{rect.width()} × {rect.height()}"
        painter.save()
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        badge_rect = metrics.boundingRect(label).adjusted(-8, -4, 8, 4)
        x = min(max(rect.left(), 8), max(8, self.width() - badge_rect.width() - 8))
        y = rect.top() - badge_rect.height() - 8
        if y < 8:
            y = min(rect.top() + 8, self.height() - badge_rect.height() - 8)
        badge_rect.moveTo(x, y)

        painter.setPen(QPen(QColor(255, 255, 255, 34), 1))
        painter.setBrush(QColor(17, 24, 39, 224))
        painter.drawRoundedRect(badge_rect, 6, 6)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()

    def _paint_selection_handles(self, painter: QPainter, rect: QRect) -> None:
        handle_pen = QPen(self._SELECTION_COLOR, 1)
        painter.save()
        painter.setPen(handle_pen)
        painter.setBrush(self._HANDLE_FILL_COLOR)
        for handle_rect in self._selection_handle_rects(rect).values():
            painter.drawRoundedRect(handle_rect, 3, 3)
        painter.restore()

    def _selection_handle_rects(self, rect: QRect | None = None) -> dict[str, QRect]:
        if rect is None:
            rect = self._selection_rect
        if rect is None:
            return {}

        half = self._HANDLE_SIZE // 2
        points = {
            "top_left": QPoint(rect.left(), rect.top()),
            "top_right": QPoint(rect.right(), rect.top()),
            "bottom_left": QPoint(rect.left(), rect.bottom()),
            "bottom_right": QPoint(rect.right(), rect.bottom()),
        }
        return {
            name: QRect(
                point.x() - half,
                point.y() - half,
                self._HANDLE_SIZE,
                self._HANDLE_SIZE,
            )
            for name, point in points.items()
        }

    def _selection_handle_at(self, point: QPoint) -> str | None:
        if self._selection_rect is None:
            return None

        for name, handle_rect in self._selection_handle_rects(self._selection_rect).items():
            if handle_rect.contains(point):
                return name
        return None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            event.accept()
            return

        if not self._selection_locked:
            self._start = event.pos()
            self._end = event.pos()
            self._dragging = True
            self._drag_mode = "select"
            event.accept()
            return

        handle = self._selection_handle_at(event.pos())
        if handle is not None:
            self._commit_pending_text_annotation()
            self._dragging = True
            self._drag_mode = "resize"
            self._move_start = None
            self._move_origin_rect = None
            self._resize_handle = handle
            self._resize_origin_rect = QRect(self._selection_rect)
            self.setCursor(QCursor(self._HANDLE_CURSORS[handle]))
            event.accept()
            return

        if self._selection_rect is None or not self._selection_rect.contains(event.pos()):
            event.accept()
            return

        if self._edit_mode == "text":
            self._start_inline_text_edit(self._selection_local_point(event.pos()))
            event.accept()
            return

        self._dragging = True
        if self._edit_mode == "move":
            self._drag_mode = "move"
            self._move_start = event.pos()
            self._move_origin_rect = QRect(self._selection_rect)
            self._resize_handle = None
            self._resize_origin_rect = None
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        else:
            local_point = self._selection_local_point(event.pos())
            self._drag_mode = "annotate"
            self._start = local_point
            self._end = local_point
            self._resize_handle = None
            self._resize_origin_rect = None
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging and self._drag_mode == "select":
            self._end = event.pos()
            self.update()
            event.accept()
            return

        if self._dragging and self._drag_mode == "move":
            if (
                self._selection_rect is not None
                and self._move_start is not None
                and self._move_origin_rect is not None
            ):
                delta = event.pos() - self._move_start
                moved = translate_rect_within_bounds(self._move_origin_rect, delta, self.rect())
                if moved != self._selection_rect:
                    self._selection_rect = moved
                    global_rect = self.current_global_selection()
                    if global_rect is not None:
                        self.selection_changed.emit(global_rect)
                    self.update()
            event.accept()
            return

        if self._dragging and self._drag_mode == "resize":
            if self._selection_rect is not None and self._resize_handle and self._resize_origin_rect is not None:
                resized = resize_rect_within_bounds(
                    self._resize_origin_rect,
                    self._resize_handle,
                    event.pos(),
                    self.rect(),
                    self._MIN_SELECTION_PX,
                )
                if resized != self._selection_rect:
                    self._selection_rect = resized
                    global_rect = self.current_global_selection()
                    if global_rect is not None:
                        self.selection_changed.emit(global_rect)
                    self.update()
            event.accept()
            return

        if self._dragging and self._drag_mode == "annotate":
            self._end = self._selection_local_point(event.pos())
            self.update()
            event.accept()
            return

        self._update_hover_cursor()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or not self._dragging:
            event.accept()
            return

        self._dragging = False

        if self._drag_mode == "select":
            self._end = event.pos()
            self._selection_rect = self._current_rect()
            self._drag_mode = None
            self.update()

            global_rect = self.current_global_selection()
            if global_rect is not None and self._bg_pixmap is not None:
                self.selection_complete.emit(global_rect, self.export_selection_pixmap())
            event.accept()
            return

        if self._drag_mode == "move":
            self._drag_mode = None
            self._move_start = None
            self._move_origin_rect = None
            self._update_hover_cursor()
            self.update()
            event.accept()
            return

        if self._drag_mode == "resize":
            self._drag_mode = None
            self._resize_handle = None
            self._resize_origin_rect = None
            self._update_hover_cursor()
            self.update()
            event.accept()
            return

        if self._drag_mode == "annotate":
            self._end = self._selection_local_point(event.pos())
            if self._edit_mode == "arrow":
                if (
                    self._start is not None
                    and self._end is not None
                    and (self._start - self._end).manhattanLength() >= 12
                ):
                    annotation = ArrowAnnotation(self._start, self._end)
                    self._arrows.append(annotation)
                    self._history.append(("arrow", annotation))
            else:
                rect = self._current_annotation_rect()
                if rect.width() >= 8 and rect.height() >= 8:
                    self._rects.append(rect)
                    self._history.append(("rect", rect))
            self._start = None
            self._end = None
            self._drag_mode = None
            self.update()
            event.accept()
            return

        self._drag_mode = None
        event.accept()

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.accept()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if self._text_editor.isVisible() and event.key() == Qt.Key.Key_Escape:
            self._cancel_pending_text_annotation()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def _start_inline_text_edit(self, local_point: QPoint) -> None:
        if self._selection_rect is None:
            return

        self._commit_pending_text_annotation()

        editor_height = self._text_editor.sizeHint().height()
        available_width = max(48, self._selection_rect.width() - 8)
        min_width = min(
            max(120, self._text_editor.fontMetrics().horizontalAdvance(self._TEXT_PLACEHOLDER) + 28),
            available_width,
        )
        origin_x = min(max(local_point.x(), 4), max(4, self._selection_rect.width() - min_width - 4))
        origin_y = min(max(local_point.y(), 4), max(4, self._selection_rect.height() - editor_height - 4))
        self._text_editor_origin = QPoint(origin_x, origin_y)

        self._text_editor.clear()
        self._resize_text_editor()
        self._text_editor.show()
        self._text_editor.raise_()
        self._text_editor.setFocus(Qt.FocusReason.MouseFocusReason)

    def _resize_text_editor(self) -> None:
        if self._selection_rect is None or self._text_editor_origin is None:
            return

        font_metrics = self._text_editor.fontMetrics()
        content = self._text_editor.text() or self._text_editor.placeholderText() or self._TEXT_PLACEHOLDER
        base_width = font_metrics.horizontalAdvance(content) + 28
        available_width = max(48, self._selection_rect.width() - 8)
        min_width = min(
            max(120, font_metrics.horizontalAdvance(self._TEXT_PLACEHOLDER) + 28),
            available_width,
        )
        max_width = max(min_width, self._selection_rect.width() - self._text_editor_origin.x() - 4)
        width = min(max(base_width, min_width), max_width)
        height = self._text_editor.sizeHint().height()
        top_left = self._selection_rect.topLeft() + self._text_editor_origin
        self._text_editor.setGeometry(top_left.x(), top_left.y(), width, height)

    def _on_text_editor_editing_finished(self) -> None:
        if self._text_editor.isVisible():
            self._commit_pending_text_annotation()

    def _commit_pending_text_annotation(self) -> None:
        if not self._text_editor.isVisible() or self._text_editor_origin is None:
            return

        text = self._text_editor.text().strip()
        origin = QPoint(self._text_editor_origin)
        self._text_editor.blockSignals(True)
        self._text_editor.hide()
        self._text_editor.clear()
        self._text_editor.blockSignals(False)
        self._text_editor_origin = None

        if text:
            annotation = TextAnnotation(origin, text)
            self._texts.append(annotation)
            self._history.append(("text", annotation))

        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.update()

    def _cancel_pending_text_annotation(self) -> None:
        if not self._text_editor.isVisible():
            self._text_editor_origin = None
            return

        self._text_editor.blockSignals(True)
        self._text_editor.hide()
        self._text_editor.clear()
        self._text_editor.blockSignals(False)
        self._text_editor_origin = None
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.update()

    def _current_annotation_rect(self) -> QRect:
        if self._start is None or self._end is None:
            return QRect()
        return QRect(
            min(self._start.x(), self._end.x()),
            min(self._start.y(), self._end.y()),
            abs(self._end.x() - self._start.x()),
            abs(self._end.y() - self._start.y()),
        )

    def _paint_annotations(self, painter: QPainter) -> None:
        pen = QPen(self._ANNOTATION_COLOR, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        for rect in self._rects:
            painter.drawRoundedRect(rect, 2, 2)

        for arrow in self._arrows:
            self._draw_arrow(painter, arrow.start, arrow.end)

        if self._drag_mode == "annotate" and self._start is not None and self._end is not None:
            if self._edit_mode == "arrow":
                self._draw_arrow(painter, self._start, self._end)
            else:
                preview_rect = self._current_annotation_rect()
                if not preview_rect.isNull():
                    painter.drawRoundedRect(preview_rect, 2, 2)

        for item in self._texts:
            self._paint_text_annotation(painter, item, pen)

    def _paint_text_annotation(
        self,
        painter: QPainter,
        item: TextAnnotation,
        default_pen: QPen,
    ) -> None:
        painter.save()
        text_rect = painter.fontMetrics().boundingRect(item.text).adjusted(-8, -5, 8, 5)
        text_rect.moveTopLeft(item.position)
        painter.setPen(QPen(self._ANNOTATION_COLOR, 1))
        painter.setBrush(QColor(255, 255, 255, 220))
        painter.drawRoundedRect(text_rect, 6, 6)
        painter.setPen(self._ANNOTATION_COLOR)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, item.text)
        painter.restore()
        painter.setPen(default_pen)

    def _draw_arrow(self, painter: QPainter, start: QPoint, end: QPoint) -> None:
        painter.drawLine(start, end)
        angle = atan2(end.y() - start.y(), end.x() - start.x())
        arrow_size = 12
        left = QPoint(
            int(end.x() - arrow_size * cos(angle - 0.45)),
            int(end.y() - arrow_size * sin(angle - 0.45)),
        )
        right = QPoint(
            int(end.x() - arrow_size * cos(angle + 0.45)),
            int(end.y() - arrow_size * sin(angle + 0.45)),
        )
        painter.save()
        painter.setBrush(self._ANNOTATION_COLOR)
        painter.drawPolygon(QPolygon([end, left, right]))
        painter.restore()
