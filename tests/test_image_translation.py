from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.image_translation import (  # noqa: E402
    OcrTextLine,
    RapidOcrEngine,
    ServerTranslateBackend,
    TextBlock,
    TranslationDirection,
    build_inpaint_mask,
    draw_translated_text,
    group_ocr_lines,
)


class _RapidOcrOutput:
    def __init__(self) -> None:
        self.boxes = [
            [(10, 10), (60, 10), (60, 28), (10, 28)],
            [(12, 34), (72, 34), (72, 52), (12, 52)],
        ]
        self.txts = ["Error", "retry"]
        self.scores = [0.98, 0.96]


class _RapidOcrArrayOutput:
    def __init__(self) -> None:
        self.boxes = np.array(
            [
                [[10, 10], [60, 10], [60, 28], [10, 28]],
                [[12, 34], [72, 34], [72, 52], [12, 52]],
            ],
            dtype=np.float32,
        )
        self.txts = np.array(["Error", "retry"], dtype=object)
        self.scores = np.array([0.98, 0.96], dtype=np.float32)


def test_group_ocr_lines_merges_visually_aligned_lines() -> None:
    lines = [
        OcrTextLine(
            polygon=((10, 10), (100, 10), (100, 28), (10, 28)),
            bbox=(10, 10, 100, 28),
            text="Error saving",
            confidence=0.99,
            estimated_font_height=18,
        ),
        OcrTextLine(
            polygon=((12, 34), (120, 34), (120, 52), (12, 52)),
            bbox=(12, 34, 120, 52),
            text="please retry",
            confidence=0.97,
            estimated_font_height=18,
        ),
    ]

    blocks = group_ocr_lines(lines)

    assert len(blocks) == 1
    assert blocks[0].source_text == "Error saving\nplease retry"


def test_rapidocr_engine_accepts_object_output_shape() -> None:
    engine = RapidOcrEngine()
    normalized = engine._normalize_output_items(_RapidOcrOutput())

    assert len(normalized) == 2
    assert normalized[0][1][0] == "Error"


def test_rapidocr_engine_accepts_numpy_box_output() -> None:
    engine = RapidOcrEngine()
    engine._engine = lambda _image: _RapidOcrArrayOutput()

    lines = engine.recognize(np.zeros((80, 120, 3), dtype=np.uint8))

    assert len(lines) == 2
    assert lines[0].text == "Error"
    assert lines[0].bbox == (10, 10, 60, 28)


def test_server_translate_backend_uses_server_client() -> None:
    class _Client:
        def translate_image_text_blocks(self, *, source_lang: str, target_lang: str, texts: list[str]) -> dict[str, object]:
            assert source_lang == "en"
            assert target_lang == "zh"
            assert texts == ["save failed", "please retry"]
            return {"translations": ["保存失败", "请重试"]}

    backend = ServerTranslateBackend(_Client())  # type: ignore[arg-type]
    translated = backend.translate(["save failed", "please retry"], TranslationDirection.EN_TO_ZH)

    assert translated == ["保存失败", "请重试"]


def test_build_inpaint_mask_marks_text_area() -> None:
    block = TextBlock(
        lines=(
            OcrTextLine(
                polygon=((8, 8), (32, 8), (32, 24), (8, 24)),
                bbox=(8, 8, 32, 24),
                text="Hello",
                confidence=0.98,
                estimated_font_height=16,
            ),
        ),
        bbox=(8, 8, 32, 24),
        source_text="Hello",
        estimated_font_height=16,
    )

    mask = build_inpaint_mask((40, 40, 3), [block])

    assert mask[16, 16] > 0


def test_draw_translated_text_returns_warning_when_box_too_small() -> None:
    image = np.full((40, 80, 3), 255, dtype=np.uint8)
    block = TextBlock(
        lines=(),
        bbox=(5, 5, 40, 18),
        source_text="hello",
        estimated_font_height=14,
    )

    translated_image, warnings = draw_translated_text(image, [block], ["这是一个非常长非常长的中文句子"])

    assert translated_image.shape == image.shape
    assert warnings
