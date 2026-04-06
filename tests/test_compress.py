"""单元测试：compress_if_needed 图像压缩函数"""
from io import BytesIO

import pytest
from PIL import Image

from src.aica.image_utils import compress_if_needed

MAX_BYTES = 4 * 1024 * 1024  # 4MB


def _make_png_bytes(width: int, height: int) -> bytes:
    """生成指定尺寸的纯色 PNG 字节流"""
    img = Image.new("RGB", (width, height), color=(100, 149, 237))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestCompressIfNeeded:
    def test_small_image_unchanged(self):
        """小于 4MB 的图像直接返回原始字节，不做任何处理"""
        data = _make_png_bytes(100, 100)
        assert len(data) < MAX_BYTES
        result = compress_if_needed(data)
        assert result == data

    def test_exact_limit_unchanged(self):
        """恰好等于 4MB 时不压缩"""
        data = b"x" * MAX_BYTES
        result = compress_if_needed(data, max_bytes=MAX_BYTES)
        assert result == data

    def test_large_image_compressed_below_limit(self):
        """超过 4MB 的大图压缩后应小于 4MB"""
        # 4000x3000 PNG 通常远超 4MB（未压缩约 34MB）
        data = _make_png_bytes(4000, 3000)
        result = compress_if_needed(data, max_bytes=MAX_BYTES)
        assert len(result) <= MAX_BYTES

    def test_compressed_result_is_valid_image(self):
        """压缩后的字节流应仍是合法图像"""
        data = _make_png_bytes(4000, 3000)
        result = compress_if_needed(data, max_bytes=MAX_BYTES)
        img = Image.open(BytesIO(result))
        assert img.size[0] > 0 and img.size[1] > 0

    def test_custom_max_bytes(self):
        """支持自定义 max_bytes 阈值"""
        data = _make_png_bytes(500, 500)
        tiny_limit = 10 * 1024  # 10KB
        result = compress_if_needed(data, max_bytes=tiny_limit)
        assert len(result) <= tiny_limit
