"""In-place image translation services for screenshot toolbar."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from aica.server_api import ChattodoServerClient, ChattodoServerError


class ImageTranslationError(RuntimeError):
    """Raised when image translation fails."""


class TranslationDirection(str, Enum):
    EN_TO_ZH = "en_to_zh"
    ZH_TO_EN = "zh_to_en"

    @property
    def source_lang(self) -> str:
        return "en" if self is TranslationDirection.EN_TO_ZH else "zh"

    @property
    def target_lang(self) -> str:
        return "zh" if self is TranslationDirection.EN_TO_ZH else "en"


@dataclass(frozen=True)
class OcrTextLine:
    polygon: tuple[tuple[int, int], ...]
    bbox: tuple[int, int, int, int]
    text: str
    confidence: float
    estimated_font_height: int


@dataclass(frozen=True)
class TextBlock:
    lines: tuple[OcrTextLine, ...]
    bbox: tuple[int, int, int, int]
    source_text: str
    estimated_font_height: int


@dataclass(frozen=True)
class ImageTranslationResult:
    image_bgr: np.ndarray
    blocks: tuple[TextBlock, ...]
    warnings: tuple[str, ...] = ()


class OcrEngine(Protocol):
    def recognize(self, image_bgr: np.ndarray) -> list[OcrTextLine]:
        """Return OCR text lines with layout coordinates."""


class TranslatorBackend(Protocol):
    def translate(self, texts: list[str], direction: TranslationDirection) -> list[str]:
        """Translate texts in batch and preserve ordering."""


class RapidOcrEngine:
    """Wrapper around RapidOCR local inference."""

    def __init__(self) -> None:
        self._engine = None

    def _get_engine(self):
        if self._engine is not None:
            return self._engine
        try:
            from rapidocr import RapidOCR
        except ImportError as exc:  # pragma: no cover - depends on optional runtime install
            raise ImageTranslationError("未安装 RapidOCR 运行依赖。") from exc
        self._engine = RapidOCR()
        return self._engine

    def recognize(self, image_bgr: np.ndarray) -> list[OcrTextLine]:
        engine = self._get_engine()
        result = engine(image_bgr)
        normalized_items = self._normalize_output_items(result)
        lines: list[OcrTextLine] = []
        for item in normalized_items:
            if not self._is_sequence_like(item) or len(item) < 2:
                continue
            raw_points = item[0]
            raw_text = item[1]
            if not self._is_sequence_like(raw_points) or len(raw_points) < 4:
                continue
            polygon = tuple(
                (int(point[0]), int(point[1]))
                for point in raw_points
                if self._is_sequence_like(point) and len(point) >= 2
            )
            if len(polygon) < 4:
                continue
            xs = [point[0] for point in polygon]
            ys = [point[1] for point in polygon]
            left = min(xs)
            top = min(ys)
            right = max(xs)
            bottom = max(ys)
            text = ""
            confidence = 0.0
            if isinstance(raw_text, (list, tuple)) and raw_text:
                text = str(raw_text[0] or "").strip()
                if len(raw_text) > 1:
                    try:
                        confidence = float(raw_text[1] or 0.0)
                    except (TypeError, ValueError):
                        confidence = 0.0
            else:
                text = str(raw_text or "").strip()
            if not text:
                continue
            lines.append(
                OcrTextLine(
                    polygon=polygon,
                    bbox=(left, top, right, bottom),
                    text=text,
                    confidence=confidence,
                    estimated_font_height=max(1, bottom - top),
                )
            )
        return lines

    @staticmethod
    def _normalize_output_items(result: object) -> list[object]:
        if result is None:
            return []
        if isinstance(result, (list, tuple)):
            if result and RapidOcrEngine._looks_like_ocr_item(result[0]):
                return list(result)
            if len(result) >= 1 and isinstance(result[0], (list, tuple)):
                first = result[0]
                if first and RapidOcrEngine._looks_like_ocr_item(first[0] if isinstance(first[0], (list, tuple)) else first):
                    return list(first)
            return []

        boxes = getattr(result, "boxes", None)
        texts = getattr(result, "txts", None)
        scores = getattr(result, "scores", None)
        if boxes is None:
            boxes = getattr(result, "polys", None)
        if texts is None:
            texts = getattr(result, "texts", None)
        if scores is None:
            scores = getattr(result, "rec_scores", None)
        if texts is None:
            texts = getattr(result, "rec_texts", None)
        if boxes is None or texts is None:
            return []

        normalized: list[object] = []
        scores_list = list(scores) if isinstance(scores, (list, tuple, np.ndarray)) else []
        for index, (box, text) in enumerate(zip(list(boxes), list(texts))):
            score = scores_list[index] if index < len(scores_list) else 0.0
            normalized.append((box, (text, score)))
        return normalized

    @staticmethod
    def _looks_like_ocr_item(item: object) -> bool:
        if not RapidOcrEngine._is_sequence_like(item) or len(item) < 2:
            return False
        points = item[0]
        return RapidOcrEngine._is_sequence_like(points) and len(points) >= 4

    @staticmethod
    def _is_sequence_like(value: object) -> bool:
        return isinstance(value, (list, tuple, np.ndarray))


class ServerTranslateBackend:
    """Server-backed translation adapter for image text blocks."""

    def __init__(self, client: ChattodoServerClient) -> None:
        self._client = client

    def translate(self, texts: list[str], direction: TranslationDirection) -> list[str]:
        normalized = [str(text or "").strip() for text in texts]
        if not normalized:
            return []
        try:
            payload = self._client.translate_image_text_blocks(
                source_lang=direction.source_lang,
                target_lang=direction.target_lang,
                texts=normalized,
            )
        except ChattodoServerError as exc:
            raise ImageTranslationError(str(exc)) from exc
        translations = payload.get("translations")
        if not isinstance(translations, list):
            raise ImageTranslationError("服务端图片翻译结果格式错误。")
        return [str(item or "").strip() for item in translations]


def group_ocr_lines(lines: list[OcrTextLine]) -> list[TextBlock]:
    sorted_lines = sorted(lines, key=lambda item: (item.bbox[1], item.bbox[0]))
    blocks: list[list[OcrTextLine]] = []
    for line in sorted_lines:
        if not blocks:
            blocks.append([line])
            continue
        previous = blocks[-1][-1]
        prev_left, prev_top, prev_right, prev_bottom = previous.bbox
        left, top, right, bottom = line.bbox
        prev_height = max(1, previous.estimated_font_height)
        current_height = max(1, line.estimated_font_height)
        vertical_gap = top - prev_bottom
        height_delta = abs(prev_height - current_height)
        left_delta = abs(prev_left - left)
        right_delta = abs(prev_right - right)
        if vertical_gap <= max(prev_height, current_height) * 0.7 and height_delta <= max(prev_height, current_height) * 0.45 and (left_delta <= max(prev_height, current_height) * 1.5 or right_delta <= max(prev_height, current_height) * 1.5):
            blocks[-1].append(line)
            continue
        blocks.append([line])

    result: list[TextBlock] = []
    for block_lines in blocks:
        xs = [point for line in block_lines for point in (line.bbox[0], line.bbox[2])]
        ys = [point for line in block_lines for point in (line.bbox[1], line.bbox[3])]
        result.append(
            TextBlock(
                lines=tuple(block_lines),
                bbox=(min(xs), min(ys), max(xs), max(ys)),
                source_text="\n".join(line.text for line in block_lines if line.text.strip()),
                estimated_font_height=max(1, round(sum(line.estimated_font_height for line in block_lines) / max(1, len(block_lines)))),
            )
        )
    return result


def build_inpaint_mask(image_shape: tuple[int, ...], blocks: list[TextBlock], dilation_ratio: float = 0.2) -> np.ndarray:
    mask = np.zeros(image_shape[:2], dtype=np.uint8)
    for block in blocks:
        for line in block.lines:
            polygon = np.array(line.polygon, dtype=np.int32)
            cv2.fillPoly(mask, [polygon], 255)
    if not blocks:
        return mask
    avg_font_height = round(sum(block.estimated_font_height for block in blocks) / max(1, len(blocks)))
    kernel_size = max(3, int(round(avg_font_height * dilation_ratio)))
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    return cv2.dilate(mask, kernel, iterations=1)


def inpaint_text_regions(image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return cv2.inpaint(image_bgr, mask, 3, cv2.INPAINT_TELEA)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int) -> list[str]:
    if not text:
        return []
    paragraphs = str(text).splitlines() or [str(text)]
    wrapped_lines: list[str] = []
    for paragraph in paragraphs:
        words = paragraph.split(" ") if " " in paragraph else list(paragraph)
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip() if " " in paragraph else f"{current}{word}"
            width = draw.textbbox((0, 0), candidate, font=font)[2]
            if current and width > max_width:
                wrapped_lines.append(current)
                current = str(word)
            else:
                current = candidate
        if current:
            wrapped_lines.append(current)
        if not words:
            wrapped_lines.append("")
    return wrapped_lines or [str(text)]


def _sample_text_color(image_bgr: np.ndarray, bbox: tuple[int, int, int, int]) -> tuple[int, int, int]:
    left, top, right, bottom = bbox
    height, width = image_bgr.shape[:2]
    pad = 2
    sample_left = max(0, left - pad)
    sample_top = max(0, top - pad)
    sample_right = min(width, right + pad)
    sample_bottom = min(height, bottom + pad)
    region = image_bgr[sample_top:sample_bottom, sample_left:sample_right]
    if region.size == 0:
        return (24, 24, 24)
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    return (24, 24, 24) if brightness >= 150 else (245, 245, 245)


def _load_font(font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, font_size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_translated_text(
    image_bgr: np.ndarray,
    blocks: list[TextBlock],
    translated_texts: list[str],
    *,
    min_font_size: int = 10,
) -> tuple[np.ndarray, list[str]]:
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    canvas = Image.fromarray(image_rgb)
    draw = ImageDraw.Draw(canvas)
    warnings: list[str] = []
    for index, block in enumerate(blocks):
        translated = str(translated_texts[index] or "").strip() if index < len(translated_texts) else ""
        if not translated:
            continue
        left, top, right, bottom = block.bbox
        box_width = max(1, right - left)
        box_height = max(1, bottom - top)
        font_size = max(min_font_size, int(block.estimated_font_height))
        chosen_font = _load_font(font_size)
        wrapped = _wrap_text(draw, translated, chosen_font, box_width)
        while font_size > min_font_size:
            line_height = draw.textbbox((0, 0), "Ag", font=chosen_font)[3]
            total_height = len(wrapped) * max(1, line_height + 2)
            overflow = any(draw.textbbox((0, 0), line, font=chosen_font)[2] > box_width for line in wrapped)
            if total_height <= box_height and not overflow:
                break
            font_size -= 1
            chosen_font = _load_font(font_size)
            wrapped = _wrap_text(draw, translated, chosen_font, box_width)
        line_height = draw.textbbox((0, 0), "Ag", font=chosen_font)[3]
        total_height = len(wrapped) * max(1, line_height + 2)
        if total_height > box_height:
            max_lines = max(1, box_height // max(1, line_height + 2))
            wrapped = wrapped[:max_lines]
            warnings.append(f"文本块 {index + 1} 译文过长，已截断显示。")
        text_color = _sample_text_color(image_bgr, block.bbox)
        current_y = top
        for line in wrapped:
            draw.text((left, current_y), line, fill=text_color, font=chosen_font)
            current_y += max(1, line_height + 2)
    return cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR), warnings


class InPlaceImageTranslator:
    """Coordinates OCR, translation, inpainting, and text overlay."""

    def __init__(self, *, ocr_engine: OcrEngine, translator: TranslatorBackend) -> None:
        self._ocr_engine = ocr_engine
        self._translator = translator

    def translate(self, image_bgr: np.ndarray, direction: TranslationDirection) -> ImageTranslationResult:
        if image_bgr.size == 0:
            raise ImageTranslationError("截图内容为空。")
        ocr_lines = self._ocr_engine.recognize(image_bgr)
        if not ocr_lines:
            raise ImageTranslationError("未识别到可翻译文字。")
        blocks = group_ocr_lines(ocr_lines)
        source_texts = [block.source_text for block in blocks if block.source_text.strip()]
        if not source_texts:
            raise ImageTranslationError("未识别到可翻译文字。")
        translated_texts = self._translator.translate(source_texts, direction)
        if len(translated_texts) != len(source_texts):
            raise ImageTranslationError("翻译结果数量与 OCR 文本块数量不一致。")
        mask = build_inpaint_mask(image_bgr.shape, blocks)
        inpainted = inpaint_text_regions(image_bgr, mask)
        translated_image, warnings = draw_translated_text(inpainted, blocks, translated_texts)
        return ImageTranslationResult(
            image_bgr=translated_image,
            blocks=tuple(blocks),
            warnings=tuple(warnings),
        )
