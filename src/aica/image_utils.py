"""Image encoding helpers for screenshot analysis."""
from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from io import BytesIO

MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4MB
MEGABYTE = 1024 * 1024
_JPEG_QUALITIES = (85, 75, 65, 55, 45)


@dataclass(frozen=True)
class EncodedImage:
    data_url: str
    mime_type: str
    byte_size: int
    preprocess_ms: int


def _target_limits(image_count: int, max_image_bytes: int) -> tuple[int, int]:
    if image_count <= 3:
        return 1600, int(1.5 * MEGABYTE)
    if image_count <= 6:
        return 1280, int(0.9 * MEGABYTE)
    return 1024, int(0.6 * MEGABYTE)


def _resize_if_needed(image, max_edge: int):  # noqa: ANN001
    from PIL import Image as PILImage

    width, height = image.size
    longest_edge = max(width, height)
    if longest_edge <= max_edge:
        return image
    scale = max_edge / float(longest_edge)
    resampling = getattr(PILImage, "Resampling", PILImage).LANCZOS
    resized = image.resize(
        (max(1, round(width * scale)), max(1, round(height * scale))),
        resampling,
    )
    return resized


def _save_png(image) -> bytes:  # noqa: ANN001
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _flatten_for_jpeg(image):  # noqa: ANN001
    image_module = image.__class__
    if image.mode in {"RGBA", "LA"}:
        background = image_module.new("RGB", image.size, (255, 255, 255))
        background.paste(image.convert("RGB"), mask=image.getchannel("A"))
        return background
    if image.mode == "P" and "transparency" in image.info:
        converted = image.convert("RGBA")
        background = image_module.new("RGB", converted.size, (255, 255, 255))
        background.paste(converted.convert("RGB"), mask=converted.getchannel("A"))
        return background
    return image.convert("RGB")


def _save_jpeg(image, quality: int) -> bytes:  # noqa: ANN001
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def encode_image_for_api(
    img_bytes: bytes,
    *,
    image_count: int = 1,
    max_image_bytes: int = MAX_IMAGE_BYTES,
) -> EncodedImage:
    from PIL import Image

    started_at = time.perf_counter()
    max_edge, strategy_limit = _target_limits(max(1, int(image_count)), max_image_bytes)
    target_bytes = max(1, min(int(max_image_bytes), strategy_limit))

    with Image.open(BytesIO(img_bytes)) as source_image:
        working = source_image.copy()

    working = _resize_if_needed(working, max_edge)
    png_bytes = _save_png(working)
    if len(png_bytes) <= target_bytes:
        preprocess_ms = round((time.perf_counter() - started_at) * 1000)
        encoded = base64.b64encode(png_bytes).decode("utf-8")
        return EncodedImage(
            data_url=f"data:image/png;base64,{encoded}",
            mime_type="image/png",
            byte_size=len(png_bytes),
            preprocess_ms=preprocess_ms,
        )

    jpeg_source = _flatten_for_jpeg(working)
    current_image = jpeg_source
    last_jpeg = b""
    while True:
        for quality in _JPEG_QUALITIES:
            jpeg_bytes = _save_jpeg(current_image, quality)
            last_jpeg = jpeg_bytes
            if len(jpeg_bytes) <= target_bytes:
                preprocess_ms = round((time.perf_counter() - started_at) * 1000)
                encoded = base64.b64encode(jpeg_bytes).decode("utf-8")
                return EncodedImage(
                    data_url=f"data:image/jpeg;base64,{encoded}",
                    mime_type="image/jpeg",
                    byte_size=len(jpeg_bytes),
                    preprocess_ms=preprocess_ms,
                )
        current_longest_edge = max(current_image.size)
        if current_longest_edge <= 128:
            break
        overflow_ratio = min(0.9, max(0.45, (target_bytes / max(1, len(last_jpeg))) ** 0.5))
        next_edge = max(128, round(current_longest_edge * overflow_ratio))
        if next_edge >= current_longest_edge:
            next_edge = max(128, current_longest_edge - 64)
        current_image = _resize_if_needed(current_image, next_edge)

    payload = last_jpeg or png_bytes
    mime_type = "image/jpeg" if last_jpeg else "image/png"
    preprocess_ms = round((time.perf_counter() - started_at) * 1000)
    encoded = base64.b64encode(payload).decode("utf-8")
    return EncodedImage(
        data_url=f"data:{mime_type};base64,{encoded}",
        mime_type=mime_type,
        byte_size=len(payload),
        preprocess_ms=preprocess_ms,
    )


def compress_if_needed(img_bytes: bytes, max_bytes: int = MAX_IMAGE_BYTES) -> bytes:
    encoded = encode_image_for_api(img_bytes, max_image_bytes=max_bytes)
    return base64.b64decode(encoded.data_url.split(",", 1)[1])
