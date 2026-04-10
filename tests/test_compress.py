from io import BytesIO

from PIL import Image

from src.aica.image_utils import compress_if_needed, encode_image_for_api

MAX_BYTES = 4 * 1024 * 1024


def _make_png_bytes(width: int, height: int, *, noisy: bool = False) -> bytes:
    if noisy:
        img = Image.effect_noise((width, height), 100).convert("RGB")
    else:
        img = Image.new("RGB", (width, height), color=(100, 149, 237))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_small_image_stays_png():
    data = _make_png_bytes(100, 100)

    encoded = encode_image_for_api(data)

    assert encoded.mime_type == "image/png"
    assert encoded.data_url.startswith("data:image/png;base64,")
    assert encoded.byte_size <= len(data)


def test_large_image_can_switch_to_jpeg_and_stay_valid():
    data = _make_png_bytes(2200, 1600, noisy=True)

    encoded = encode_image_for_api(data, max_image_bytes=120 * 1024)

    assert encoded.mime_type in {"image/png", "image/jpeg"}
    assert encoded.byte_size <= 120 * 1024
    raw = compress_if_needed(data, max_bytes=120 * 1024)
    image = Image.open(BytesIO(raw))
    assert image.size[0] > 0 and image.size[1] > 0


def test_image_count_uses_stronger_compression_for_large_batches():
    data = _make_png_bytes(2200, 1600, noisy=True)

    single = encode_image_for_api(data, image_count=1, max_image_bytes=MAX_BYTES)
    many = encode_image_for_api(data, image_count=7, max_image_bytes=MAX_BYTES)

    assert many.byte_size <= single.byte_size


def test_custom_max_bytes_limit_is_respected():
    data = _make_png_bytes(1500, 1100, noisy=True)
    tiny_limit = 80 * 1024

    encoded = encode_image_for_api(data, max_image_bytes=tiny_limit)

    assert encoded.byte_size <= tiny_limit
