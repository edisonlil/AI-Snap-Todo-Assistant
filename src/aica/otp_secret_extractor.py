"""OTP QR extraction helpers shared by the CLI and control panel."""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import numpy as np


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class OtpSecretExtractResult:
    type: str
    secret: str
    issuer: str = ""
    account: str = ""
    algorithm: str = "SHA1"
    digits: int = 6
    period: int = 30
    label: str = ""
    raw_payload: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class QrDecoderError(RuntimeError):
    """Base QR decoder failure."""


class QrDecoderDependencyError(QrDecoderError):
    """QR decoder dependency is unavailable."""


def parse_otpauth_payload(payload: str) -> OtpSecretExtractResult:
    normalized = _normalize_text(payload)
    if not normalized:
        raise ValueError("二维码内容为空")

    if not normalized.lower().startswith("otpauth://"):
        secret_match = re.search(r"(?:^|[?&])secret=([A-Z2-7=]+)", normalized, flags=re.IGNORECASE)
        secret = _normalize_text(secret_match.group(1) if secret_match else normalized)
        return OtpSecretExtractResult(
            type="raw",
            secret=secret.replace(" ", "").replace("-", "").upper(),
            raw_payload=normalized,
        )

    parsed = urlparse(normalized)
    query = parse_qs(parsed.query)
    label = unquote(parsed.path.lstrip("/"))
    issuer = _normalize_text((query.get("issuer") or [""])[0])
    secret = _normalize_text((query.get("secret") or [""])[0]).replace(" ", "").replace("-", "").upper()
    algorithm = _normalize_text((query.get("algorithm") or ["SHA1"])[0]).upper() or "SHA1"

    try:
        digits = max(1, int(_normalize_text((query.get("digits") or ["6"])[0]) or "6"))
    except ValueError:
        digits = 6

    try:
        period = max(1, int(_normalize_text((query.get("period") or ["30"])[0]) or "30"))
    except ValueError:
        period = 30

    account = ""
    if ":" in label:
        left, right = label.split(":", 1)
        if not issuer:
            issuer = _normalize_text(left)
        account = _normalize_text(right)
    else:
        account = label

    if not secret:
        raise ValueError("二维码已解码，但未找到 OTP secret")

    return OtpSecretExtractResult(
        type=parsed.netloc or "totp",
        secret=secret,
        issuer=issuer,
        account=account,
        algorithm=algorithm,
        digits=digits,
        period=period,
        label=label,
        raw_payload=normalized,
    )


def _import_cv2():
    try:
        import cv2  # type: ignore
    except ImportError as exc:
        raise QrDecoderDependencyError("opencv-python 未安装") from exc
    return cv2


def _load_image_with_opencv(cv2: object, image_path: Path):
    try:
        image_bytes = image_path.read_bytes()
    except OSError as exc:
        raise QrDecoderError(f"无法读取图片文件: {exc}") from exc

    buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is not None:
        return image

    image = cv2.imread(str(image_path))
    if image is None:
        raise QrDecoderError("OpenCV 无法读取图片文件")
    return image


def _ensure_grayscale(cv2: object, image: object):
    if getattr(image, "ndim", 0) == 2:
        return image
    channels = int(getattr(image, "shape", [0, 0, 0])[2] or 0)
    if channels == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _add_white_border(cv2: object, image: object, border: int):
    if border <= 0:
        return image
    channels = int(getattr(image, "shape", [0, 0, 1])[2] or 1) if getattr(image, "ndim", 0) == 3 else 1
    border_value = 255 if channels == 1 else tuple([255] * channels)
    return cv2.copyMakeBorder(
        image,
        border,
        border,
        border,
        border,
        cv2.BORDER_CONSTANT,
        value=border_value,
    )


def _resize_image(cv2: object, image: object, scale: float, *, nearest: bool = False):
    if scale == 1.0:
        return image
    interpolation = cv2.INTER_NEAREST if nearest else cv2.INTER_CUBIC
    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=interpolation)


def _iter_opencv_qr_candidates(cv2: object, image: object):
    gray = _ensure_grayscale(cv2, image)
    height, width = gray.shape[:2]
    border = max(12, int(round(min(height, width) * 0.04)))

    padded_color = _add_white_border(cv2, image, border)
    padded_gray = _add_white_border(cv2, gray, border)
    blurred_gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, otsu = cv2.threshold(blurred_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    adaptive = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    inverted_otsu = cv2.bitwise_not(otsu)

    for candidate in (
        image,
        padded_color,
        gray,
        padded_gray,
        _resize_image(cv2, gray, 2.0),
        _resize_image(cv2, padded_gray, 2.0),
        otsu,
        _add_white_border(cv2, otsu, border),
        _resize_image(cv2, otsu, 2.0, nearest=True),
        adaptive,
        _resize_image(cv2, adaptive, 2.0, nearest=True),
        inverted_otsu,
        _resize_image(cv2, inverted_otsu, 2.0, nearest=True),
    ):
        yield candidate


def _extract_first_payload(payloads: object) -> str:
    if isinstance(payloads, (str, bytes)):
        payloads = [payloads]

    for item in payloads or []:
        if isinstance(item, bytes):
            decoded = item.decode("utf-8", errors="replace").strip()
        else:
            decoded = _normalize_text(item)
        if decoded:
            return decoded
    return ""


def _decode_qr_with_qrcode_detector(detector: object, image: object) -> str:
    payload = _extract_first_payload(detector.detectAndDecode(image)[0])
    if payload:
        return payload

    ok, decoded_list, _, _ = detector.detectAndDecodeMulti(image)
    if ok:
        payload = _extract_first_payload(decoded_list)
        if payload:
            return payload

    payload = _extract_first_payload(detector.detectAndDecodeCurved(image)[0])
    if payload:
        return payload
    return ""


def _decode_qr_with_opencv(image_path: Path) -> str:
    cv2 = _import_cv2()
    image = _load_image_with_opencv(cv2, image_path)

    detector = cv2.QRCodeDetector()
    if hasattr(detector, "setUseAlignmentMarkers"):
        detector.setUseAlignmentMarkers(True)

    for candidate in _iter_opencv_qr_candidates(cv2, image):
        payload = _decode_qr_with_qrcode_detector(detector, candidate)
        if payload:
            return payload

    raise QrDecoderError("OpenCV 未识别到二维码")


def _decode_qr_with_pyzbar(image_path: Path) -> str:
    try:
        from PIL import Image
    except ImportError as exc:
        raise QrDecoderDependencyError("Pillow 未安装") from exc

    try:
        from pyzbar.pyzbar import decode  # type: ignore
    except ImportError as exc:
        raise QrDecoderDependencyError("pyzbar 未安装") from exc

    image = Image.open(image_path)
    decoded_items = decode(image)
    for item in decoded_items:
        if item.data:
            return item.data.decode("utf-8", errors="replace")
    raise QrDecoderError("pyzbar 未识别到二维码")


def decode_qr_payload(image_path: Path) -> str:
    errors: list[str] = []
    available_decoder_failed = False
    for decoder in (_decode_qr_with_opencv, _decode_qr_with_pyzbar):
        try:
            return decoder(image_path)
        except Exception as exc:
            if not isinstance(exc, QrDecoderDependencyError):
                available_decoder_failed = True
            errors.append(f"{decoder.__name__}: {exc}")
    joined_errors = "\n".join(f"- {item}" for item in errors)
    if available_decoder_failed:
        raise RuntimeError(
            "二维码解码失败：未识别到有效二维码。\n"
            "请确认导入的是二维码图片，而不是界面截图或错误弹窗；如果二维码较小，可先裁剪到二维码区域后重试。\n"
            f"详细错误:\n{joined_errors}"
        )

    raise RuntimeError(
        "二维码解码失败：当前环境缺少可用的二维码解码依赖。\n"
        "可安装以下任一方案后重试：\n"
        "1. pip install opencv-python\n"
        "2. pip install pyzbar Pillow\n"
        f"详细错误:\n{joined_errors}"
    )


def extract_otp_secret_from_qr_image(image_path: str | Path) -> OtpSecretExtractResult:
    target = Path(image_path).expanduser().resolve()
    if not target.is_file():
        raise FileNotFoundError(f"文件不存在: {target}")
    payload = decode_qr_payload(target)
    return parse_otpauth_payload(payload)
