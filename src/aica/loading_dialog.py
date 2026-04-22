"""Frameless loading dialog shown during screenshot analysis."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import QApplication, QDialog, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout

from aica.paths import asset_file
from aica.runtime import RUNTIME_CAPABILITIES


class LoadingDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._movie: QMovie | None = None
        self._anchor_widget = None

        self.setWindowTitle("正在分析中")
        self.setModal(False)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(286, 58)

        self._setup_ui()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        surface = QFrame(self)
        surface.setObjectName("loadingSurface")
        surface_layout = QHBoxLayout(surface)
        surface_layout.setContentsMargins(4, 8, 10, 8)
        surface_layout.setSpacing(4)

        gif_wrap = QFrame(surface)
        gif_wrap.setObjectName("loadingGifWrap")
        gif_layout = QVBoxLayout(gif_wrap)
        gif_layout.setContentsMargins(0, 0, 0, 0)
        gif_layout.setSpacing(0)

        self._gif_label = QLabel(gif_wrap)
        self._gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gif_label.setFixedSize(42, 42)
        gif_layout.addWidget(self._gif_label, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        gif_layout.addStretch(1)
        surface_layout.addWidget(gif_wrap, 0, Qt.AlignmentFlag.AlignTop)

        text_wrap = QFrame(surface)
        text_wrap.setObjectName("loadingContent")
        text_layout = QHBoxLayout(text_wrap)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        body_label = QLabel("正在识别截图内容，请稍候…", text_wrap)
        body_label.setObjectName("loadingBody")
        body_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        body_label.setWordWrap(False)
        text_layout.addWidget(body_label)

        surface_layout.addWidget(text_wrap, 1)

        close_button = QPushButton("×", surface)
        close_button.setObjectName("loadingClose")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setFixedSize(20, 20)
        close_button.clicked.connect(self.hide_loading)
        surface_layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignTop)

        root_layout.addWidget(surface)

        self.setStyleSheet(
            """
            QFrame#loadingSurface {
                background-color: #FFFFFF;
                border: none;
                border-radius: 18px;
            }
            QFrame#loadingContent {
                background: transparent;
                border: none;
            }
            QFrame#loadingGifWrap {
                background: transparent;
                border: none;
                min-width: 52px;
                max-width: 52px;
            }
            QLabel {
                background: transparent;
                color: #4A5565;
                font-family: %s;
            }
            QLabel#loadingTitle {
                color: #2A313F;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#loadingBody {
                color: #667085;
                font-size: 12px;
                font-weight: 400;
            }
            QPushButton#loadingClose {
                background-color: transparent;
                border: none;
                border-radius: 9px;
                color: #98A2B3;
                font-size: 14px;
                font-weight: 400;
            }
            QPushButton#loadingClose:hover {
                background-color: #F3F4F6;
                color: #4A5565;
            }
            """
            % RUNTIME_CAPABILITIES.widget_font_css
        )

        movie_path = asset_file("aica_loading.gif")
        if movie_path.exists():
            self._movie = QMovie(str(movie_path))
            self._movie.setScaledSize(self._gif_label.size())
            self._gif_label.setMovie(self._movie)

    def show_loading(self, anchor_widget=None) -> None:
        self._anchor_widget = anchor_widget
        if anchor_widget is not None and hasattr(anchor_widget, "set_top_reserved_space"):
            anchor_widget.set_top_reserved_space(self.height() + 12)
        if self._movie is not None:
            self._movie.start()
        if anchor_widget is not None:
            self._place_above_widget(anchor_widget)
        else:
            self._place_top_right()
        self.show()
        self.raise_()

    def hide_loading(self) -> None:
        if self._movie is not None:
            self._movie.stop()
        if self._anchor_widget is not None and hasattr(self._anchor_widget, "set_top_reserved_space"):
            self._anchor_widget.set_top_reserved_space(0)
        self._anchor_widget = None
        self.hide()

    def _place_top_right(self) -> None:
        screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        margin = 18
        x = available.right() - self.width() - margin
        y = available.top() + margin
        self.move(x, y)

    def _place_above_widget(self, widget) -> None:
        frame_geometry = getattr(widget, "frameGeometry", None)
        if callable(frame_geometry):
            geometry = frame_geometry()
            global_top_left = geometry.topLeft()
            target_width = geometry.width()
        else:
            global_top_left = widget.mapToGlobal(QPoint(0, 0))
            target_width = widget.width()

        screen = QApplication.screenAt(global_top_left) or QApplication.primaryScreen()
        if screen is None:
            self._place_top_right()
            return

        available = screen.availableGeometry()
        self.setFixedSize(max(240, target_width), 58)

        x = global_top_left.x() + max(0, (target_width - self.width()) // 2)
        y = global_top_left.y() - self.height() - 2

        x = max(available.left() + 12, min(x, available.right() - self.width() - 12))
        y = max(available.top() + 12, y)
        self.move(x, y)
