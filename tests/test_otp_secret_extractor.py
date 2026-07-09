from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import aica.otp_secret_extractor as extractor  # noqa: E402
import numpy as np  # noqa: E402


def test_parse_otpauth_payload_supports_otpauth_uri() -> None:
    parsed = extractor.parse_otpauth_payload(
        "otpauth://totp/demo:admin?secret=JBSWY3DPEHPK3PXP&algorithm=SHA256&digits=8&period=60"
    )

    assert parsed.type == "totp"
    assert parsed.secret == "JBSWY3DPEHPK3PXP"
    assert parsed.issuer == "demo"
    assert parsed.account == "admin"
    assert parsed.algorithm == "SHA256"
    assert parsed.digits == 8
    assert parsed.period == 60


def test_parse_otpauth_payload_supports_query_secret_and_raw_secret() -> None:
    parsed_query = extractor.parse_otpauth_payload("https://example.com?secret=JBSWY3DPEHPK3PXP")
    parsed_raw = extractor.parse_otpauth_payload("JBSWY3DPEHPK3PXP")

    assert parsed_query.secret == "JBSWY3DPEHPK3PXP"
    assert parsed_raw.secret == "JBSWY3DPEHPK3PXP"
    assert parsed_query.type == "raw"
    assert parsed_raw.type == "raw"


def test_extract_otp_secret_from_qr_image_uses_decoder(monkeypatch) -> None:
    image_path = (Path.cwd() / "requirements.txt").resolve()

    monkeypatch.setattr(
        extractor,
        "decode_qr_payload",
        lambda _path: "otpauth://totp/demo:admin?secret=JBSWY3DPEHPK3PXP",
    )

    parsed = extractor.extract_otp_secret_from_qr_image(image_path)

    assert parsed.secret == "JBSWY3DPEHPK3PXP"
    assert parsed.raw_payload.startswith("otpauth://")


def test_decode_qr_payload_retries_with_preprocessed_opencv_candidates(monkeypatch) -> None:
    payload = "otpauth://totp/demo:admin?secret=JBSWY3DPEHPK3PXP"
    image_path = (Path.cwd() / "requirements.txt").resolve()
    calls = {"count": 0}
    first_image = np.zeros((16, 16, 3), dtype=np.uint8)
    second_image = np.ones((20, 20), dtype=np.uint8)

    class _FakeDetector:
        def setUseAlignmentMarkers(self, _enabled: bool) -> None:
            return None

        def detectAndDecode(self, image):
            calls["count"] += 1
            if image is second_image:
                return (payload, None, None)
            return ("", None, None)

        def detectAndDecodeMulti(self, _image):
            return (False, (), None, ())

        def detectAndDecodeCurved(self, _image):
            return ("", None, None)

    fake_cv2 = SimpleNamespace(
        IMREAD_COLOR=1,
        INTER_NEAREST=0,
        INTER_CUBIC=1,
        THRESH_BINARY=0,
        THRESH_OTSU=0,
        ADAPTIVE_THRESH_GAUSSIAN_C=0,
        BORDER_CONSTANT=0,
        COLOR_BGR2GRAY=0,
        COLOR_BGRA2GRAY=1,
        imdecode=lambda *_args, **_kwargs: first_image,
        imread=lambda *_args, **_kwargs: first_image,
        QRCodeDetector=lambda: _FakeDetector(),
        cvtColor=lambda image, _code: image[:, :, 0],
        GaussianBlur=lambda image, *_args, **_kwargs: image,
        threshold=lambda image, *_args, **_kwargs: (None, image),
        adaptiveThreshold=lambda image, *_args, **_kwargs: image,
        bitwise_not=lambda image: image,
        resize=lambda image, *_args, **_kwargs: second_image,
        copyMakeBorder=lambda image, *_args, **_kwargs: image,
    )

    monkeypatch.setattr(extractor, "_import_cv2", lambda: fake_cv2)
    monkeypatch.setattr(extractor.Path, "read_bytes", lambda _self: b"png-bytes")

    assert extractor.decode_qr_payload(image_path) == payload
    assert calls["count"] >= 2


def test_decode_qr_payload_reports_decode_failure_without_dependency_hint(monkeypatch) -> None:
    image_path = (Path.cwd() / "requirements.txt").resolve()

    monkeypatch.setattr(
        extractor,
        "_decode_qr_with_opencv",
        lambda _path: (_ for _ in ()).throw(extractor.QrDecoderError("OpenCV 未识别到二维码")),
    )
    monkeypatch.setattr(
        extractor,
        "_decode_qr_with_pyzbar",
        lambda _path: (_ for _ in ()).throw(extractor.QrDecoderDependencyError("pyzbar 未安装")),
    )

    try:
        extractor.decode_qr_payload(image_path)
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("decode_qr_payload should fail when no decoder returns a payload")

    assert "未识别到有效二维码" in message
    assert "界面截图或错误弹窗" in message
    assert "可安装以下任一方案后重试" not in message


def test_decode_qr_payload_reports_missing_dependencies_when_none_are_available(monkeypatch) -> None:
    image_path = (Path.cwd() / "requirements.txt").resolve()

    monkeypatch.setattr(
        extractor,
        "_decode_qr_with_opencv",
        lambda _path: (_ for _ in ()).throw(extractor.QrDecoderDependencyError("opencv-python 未安装")),
    )
    monkeypatch.setattr(
        extractor,
        "_decode_qr_with_pyzbar",
        lambda _path: (_ for _ in ()).throw(extractor.QrDecoderDependencyError("pyzbar 未安装")),
    )

    try:
        extractor.decode_qr_payload(image_path)
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("decode_qr_payload should fail when dependencies are unavailable")

    assert "当前环境缺少可用的二维码解码依赖" in message
    assert "pip install opencv-python" in message
