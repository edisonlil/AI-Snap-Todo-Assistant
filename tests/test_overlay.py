"""Unit tests for overlay geometry helpers."""
from PyQt6.QtCore import QPoint, QRect

from src.aica.overlay import normalize_rect, resize_rect_within_bounds, translate_rect_within_bounds


class TestNormalizeRect:
    def test_top_left_to_bottom_right(self):
        r = normalize_rect(QPoint(10, 20), QPoint(100, 200))
        assert r.left() == 10
        assert r.top() == 20
        assert r.width() == 90
        assert r.height() == 180

    def test_bottom_right_to_top_left(self):
        r = normalize_rect(QPoint(100, 200), QPoint(10, 20))
        assert r.left() == 10
        assert r.top() == 20
        assert r.width() == 90
        assert r.height() == 180

    def test_top_right_to_bottom_left(self):
        r = normalize_rect(QPoint(100, 20), QPoint(10, 200))
        assert r.left() == 10
        assert r.top() == 20

    def test_bottom_left_to_top_right(self):
        r = normalize_rect(QPoint(10, 200), QPoint(100, 20))
        assert r.left() == 10
        assert r.top() == 20

    def test_left_always_le_right(self):
        cases = [
            (QPoint(0, 0), QPoint(50, 50)),
            (QPoint(50, 50), QPoint(0, 0)),
            (QPoint(200, 10), QPoint(5, 300)),
        ]
        for p1, p2 in cases:
            r = normalize_rect(p1, p2)
            assert r.left() <= r.right(), f"left > right for {p1}, {p2}"

    def test_top_always_le_bottom(self):
        cases = [
            (QPoint(0, 0), QPoint(50, 50)),
            (QPoint(50, 50), QPoint(0, 0)),
            (QPoint(200, 10), QPoint(5, 300)),
        ]
        for p1, p2 in cases:
            r = normalize_rect(p1, p2)
            assert r.top() <= r.bottom(), f"top > bottom for {p1}, {p2}"

    def test_same_point_gives_zero_size(self):
        r = normalize_rect(QPoint(50, 50), QPoint(50, 50))
        assert r.width() == 0
        assert r.height() == 0


class TestTranslateRectWithinBounds:
    def test_moves_rect_when_space_is_available(self):
        bounds = QRect(0, 0, 400, 300)
        rect = QRect(50, 60, 100, 80)

        moved = translate_rect_within_bounds(rect, QPoint(40, 25), bounds)

        assert moved == QRect(90, 85, 100, 80)

    def test_clamps_rect_to_top_left_boundary(self):
        bounds = QRect(0, 0, 400, 300)
        rect = QRect(50, 60, 100, 80)

        moved = translate_rect_within_bounds(rect, QPoint(-100, -200), bounds)

        assert moved == QRect(0, 0, 100, 80)

    def test_clamps_rect_to_bottom_right_boundary(self):
        bounds = QRect(0, 0, 400, 300)
        rect = QRect(320, 240, 100, 80)

        moved = translate_rect_within_bounds(rect, QPoint(100, 80), bounds)

        assert moved == QRect(300, 220, 100, 80)


class TestResizeRectWithinBounds:
    def test_expands_from_top_left_when_space_is_available(self):
        bounds = QRect(0, 0, 400, 300)
        rect = QRect(100, 80, 120, 90)

        resized = resize_rect_within_bounds(rect, "top_left", QPoint(60, 40), bounds, min_size=5)

        assert resized == QRect(60, 40, 160, 130)

    def test_keeps_same_size_when_bottom_right_handle_is_not_moved(self):
        bounds = QRect(0, 0, 400, 300)
        rect = QRect(50, 60, 100, 80)

        resized = resize_rect_within_bounds(rect, "bottom_right", QPoint(149, 139), bounds, min_size=5)

        assert resized == rect

    def test_clamps_resize_to_bounds(self):
        bounds = QRect(0, 0, 400, 300)
        rect = QRect(50, 60, 100, 80)

        resized = resize_rect_within_bounds(rect, "bottom_right", QPoint(500, 500), bounds, min_size=5)

        assert resized == QRect(50, 60, 350, 240)

    def test_clamps_resize_to_min_size(self):
        bounds = QRect(0, 0, 400, 300)
        rect = QRect(100, 80, 120, 90)

        resized = resize_rect_within_bounds(rect, "top_left", QPoint(300, 200), bounds, min_size=5)

        assert resized == QRect(215, 165, 5, 5)
