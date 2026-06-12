from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, sin

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QKeySequence, QPainter, QPen, QPixmap, QPolygon, QShortcut
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .runtime import RUNTIME_CAPABILITIES
from .theme_controller import ThemeController


@dataclass
class TextAnnotation:
    position: QPoint
    text: str


@dataclass
class ArrowAnnotation:
    start: QPoint
    end: QPoint


class AnnotationCanvas(QWidget):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        normalized_image = pixmap.toImage()
        dpr = pixmap.devicePixelRatio() or 1.0
        if dpr != 1.0:
            device_size = pixmap.deviceIndependentSize().toSize()
            normalized_image = normalized_image.scaled(
                max(1, device_size.width()),
                max(1, device_size.height()),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._pixmap = QPixmap.fromImage(normalized_image)
        self._pixmap.setDevicePixelRatio(1.0)
        self._display_width = max(1, self._pixmap.width())
        self._display_height = max(1, self._pixmap.height())
        self._display_pixmap = self._pixmap
        self._rects: list[QRect] = []
        self._texts: list[TextAnnotation] = []
        self._arrows: list[ArrowAnnotation] = []
        self._history: list[tuple[str, object]] = []
        self._mode = "rect"
        self._start: QPoint | None = None
        self._end: QPoint | None = None
        self._dragging = False
        self.setFixedSize(self._display_width, self._display_height)
        self.setMouseTracking(True)

    def set_mode(self, mode: str) -> None:
        self._mode = mode

    def clear_annotations(self) -> None:
        self._rects.clear()
        self._texts.clear()
        self._arrows.clear()
        self._history.clear()
        self._start = None
        self._end = None
        self._dragging = False
        self.update()

    def undo_last_annotation(self) -> None:
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

    def export_pixmap(self) -> QPixmap:
        annotated = self._pixmap.copy()
        painter = QPainter(annotated)
        self._paint_annotations(painter)
        painter.end()
        return annotated

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._display_pixmap)
        self._paint_annotations(painter)
        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._mode == "text":
            text, ok = QInputDialog.getText(self, "文字标注", "输入标注内容")
            if ok and text.strip():
                annotation = TextAnnotation(event.pos(), text.strip())
                self._texts.append(annotation)
                self._history.append(("text", annotation))
                self.update()
            return

        self._start = event.pos()
        self._end = event.pos()
        self._dragging = True

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging:
            self._end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or not self._dragging:
            return
        self._dragging = False
        self._end = event.pos()

        if self._mode == "arrow":
            if self._start is not None and self._end is not None and (self._start - self._end).manhattanLength() >= 12:
                annotation = ArrowAnnotation(self._start, self._end)
                self._arrows.append(annotation)
                self._history.append(("arrow", annotation))
        else:
            rect = self._normalized_rect(self._start, self._end)
            if rect.width() >= 8 and rect.height() >= 8:
                self._rects.append(rect)
                self._history.append(("rect", rect))

        self._start = None
        self._end = None
        self.update()

    def _normalized_rect(self, p1: QPoint | None, p2: QPoint | None) -> QRect:
        if p1 is None or p2 is None:
            return QRect()
        return QRect(
            min(p1.x(), p2.x()),
            min(p1.y(), p2.y()),
            abs(p2.x() - p1.x()),
            abs(p2.y() - p1.y()),
        )

    def _paint_annotations(self, painter: QPainter) -> None:
        pen = QPen(QColor(239, 68, 68), 3)
        painter.setPen(pen)

        for rect in self._rects:
            painter.drawRect(rect)

        for arrow in self._arrows:
            self._draw_arrow(painter, arrow.start, arrow.end)

        if self._dragging and self._start is not None and self._end is not None:
            if self._mode == "arrow":
                self._draw_arrow(painter, self._start, self._end)
            else:
                preview_rect = self._normalized_rect(self._start, self._end)
                if not preview_rect.isNull():
                    painter.drawRect(preview_rect)

        for item in self._texts:
            text_rect = painter.fontMetrics().boundingRect(item.text).adjusted(-8, -6, 8, 6)
            text_rect.moveTopLeft(item.position)
            painter.fillRect(text_rect, QColor(239, 68, 68, 220))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, item.text)
            painter.setPen(pen)

    def _draw_arrow(self, painter: QPainter, start: QPoint, end: QPoint) -> None:
        painter.drawLine(start, end)
        angle = atan2(end.y() - start.y(), end.x() - start.x())
        arrow_size = 14
        left = QPoint(
            int(end.x() - arrow_size * cos(angle - 0.45)),
            int(end.y() - arrow_size * sin(angle - 0.45)),
        )
        right = QPoint(
            int(end.x() - arrow_size * cos(angle + 0.45)),
            int(end.y() - arrow_size * sin(angle + 0.45)),
        )
        painter.setBrush(QColor(239, 68, 68))
        painter.drawPolygon(QPolygon([end, left, right]))
        painter.setBrush(Qt.BrushStyle.NoBrush)


class AnnotationDialog(QDialog):
    def __init__(
        self,
        pixmap: QPixmap,
        parent=None,
        *,
        theme_controller: ThemeController | None = None,
    ):
        super().__init__(parent)
        self._theme_controller = theme_controller or ThemeController()
        self._canvas = AnnotationCanvas(pixmap, self)
        self._annotated_pixmap: QPixmap | None = None
        self._setup_ui()
        self._setup_shortcuts()
        self._theme_controller.themeChanged.connect(self._apply_style)
        self.setWindowTitle("标注截图")
        self.resize(
            min(max(self._canvas.width() + 56, 420), 1280),
            min(max(self._canvas.height() + 160, 320), 920),
        )

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        toolbar = QFrame()
        toolbar.setObjectName("annotToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 10, 12, 10)
        toolbar_layout.setSpacing(8)

        hint = QLabel("拖动可画重点框或箭头，点“文字标注”后再点图上位置可添加文字，Ctrl+Z 可撤销")
        hint.setObjectName("hintLabel")
        toolbar_layout.addWidget(hint)
        toolbar_layout.addStretch()

        btn_rect = QPushButton("框选标注")
        btn_rect.clicked.connect(lambda: self._canvas.set_mode("rect"))
        toolbar_layout.addWidget(btn_rect)

        btn_arrow = QPushButton("箭头标注")
        btn_arrow.clicked.connect(lambda: self._canvas.set_mode("arrow"))
        toolbar_layout.addWidget(btn_arrow)

        btn_text = QPushButton("文字标注")
        btn_text.clicked.connect(lambda: self._canvas.set_mode("text"))
        toolbar_layout.addWidget(btn_text)

        btn_undo = QPushButton("撤销")
        btn_undo.clicked.connect(self._canvas.undo_last_annotation)
        toolbar_layout.addWidget(btn_undo)

        btn_clear = QPushButton("清空")
        btn_clear.clicked.connect(self._canvas.clear_annotations)
        toolbar_layout.addWidget(btn_clear)

        layout.addWidget(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._canvas)
        layout.addWidget(scroll, 1)

        footer = QFrame()
        footer.setObjectName("annotFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 10, 12, 10)
        footer_layout.addStretch()

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(btn_cancel)

        btn_apply = QPushButton("完成标注")
        btn_apply.setObjectName("primaryButton")
        btn_apply.clicked.connect(self._on_apply)
        footer_layout.addWidget(btn_apply)

        layout.addWidget(footer)

        self._apply_style()

    def _apply_style(self) -> None:
        theme = self._theme_controller.tokens
        self.setStyleSheet(
            """
            QDialog {
                background-color: %(panelAltBg)s;
                color: %(titleInk)s;
                font-family: %(widgetFontCss)s;
            }
            QFrame#annotToolbar, QFrame#annotFooter {
                background-color: %(panelBg)s;
                border: 1px solid %(panelLine)s;
                border-radius: %(radiusMd)spx;
            }
            QLabel#hintLabel {
                color: %(bodyInk)s;
                font-size: %(fontCaption)spx;
            }
            QPushButton {
                border-radius: %(buttonRadius)spx;
                padding: 6px 10px;
                font-size: %(buttonFontSize)spx;
                font-weight: 600;
                min-height: 16px;
                color: %(buttonDefaultInk)s;
                background-color: %(buttonDefaultBg)s;
                border: 1px solid %(buttonBorder)s;
            }
            QPushButton:hover {
                background-color: %(buttonDefaultBgHover)s;
                border: 1px solid %(panelLine)s;
            }
            QPushButton:pressed {
                background-color: %(buttonDefaultBgPressed)s;
            }
            QPushButton#primaryButton {
                color: %(buttonPrimaryInk)s;
                background-color: %(buttonPrimaryBg)s;
                border: 1px solid %(buttonPrimaryBg)s;
            }
            QPushButton#primaryButton:hover {
                background-color: %(buttonPrimaryBgHover)s;
                border: 1px solid %(buttonPrimaryBgHover)s;
            }
            QPushButton#primaryButton:pressed {
                background-color: %(buttonPrimaryBgPressed)s;
                border: 1px solid %(buttonPrimaryBgPressed)s;
            }
            QScrollArea {
                background-color: %(panelBg)s;
                border: 1px solid %(panelLine)s;
                border-radius: %(radiusMd)spx;
            }
            """
            % {
                **theme,
                "widgetFontCss": str(theme.get("widgetFontCss") or RUNTIME_CAPABILITIES.widget_font_css),
            }
        )

    def _setup_shortcuts(self) -> None:
        undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_shortcut.activated.connect(self._canvas.undo_last_annotation)

    def _on_apply(self) -> None:
        self._annotated_pixmap = self._canvas.export_pixmap()
        self.accept()

    def get_annotated_pixmap(self) -> QPixmap | None:
        return self._annotated_pixmap
