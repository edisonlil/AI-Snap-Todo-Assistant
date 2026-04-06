"""图像处理工具：压缩、Base64 编码等（无 Qt 依赖，便于单元测试）"""
from __future__ import annotations

from io import BytesIO

MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4MB


def compress_if_needed(img_bytes: bytes, max_bytes: int = MAX_IMAGE_BYTES) -> bytes:
    """
    若 img_bytes 超过 max_bytes，用 Pillow 以 JPEG 格式循环压缩直到满足大小要求。
    每轮质量降低 10%，最低降至 10%；若仍超限则缩小分辨率到 50%。
    Requirements: 5.4
    """
    if len(img_bytes) <= max_bytes:
        return img_bytes

    from PIL import Image

    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    quality = 50

    while quality >= 10:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        compressed = buf.getvalue()
        if len(compressed) <= max_bytes:
            return compressed
        quality -= 10

    # 兜底：缩小分辨率到 50%
    w, h = img.size
    img = img.resize((w // 2, h // 2), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=10)
    return buf.getvalue()
