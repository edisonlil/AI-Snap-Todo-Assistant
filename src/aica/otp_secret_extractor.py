"""OTP QR extraction helpers shared by the CLI and control panel."""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


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


def _decode_qr_with_opencv(image_path: Path) -> str:
    try:
        import cv2  # type: ignore
    except ImportError as exc:
        raise RuntimeError("opencv-python 未安装") from exc

    image = cv2.imread(str(image_path))
    if image is None:
        raise RuntimeError("OpenCV 无法读取图片文件")

    detector = cv2.QRCodeDetector()
    payload, _, _ = detector.detectAndDecode(image)
    if payload:
        return payload

    ok, decoded_list, _, _ = detector.detectAndDecodeMulti(image)
    if ok:
        for item in decoded_list:
            if item:
                return item
    raise RuntimeError("OpenCV 未识别到二维码")


def _decode_qr_with_pyzbar(image_path: Path) -> str:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow 未安装") from exc

    try:
        from pyzbar.pyzbar import decode  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pyzbar 未安装") from exc

    image = Image.open(image_path)
    decoded_items = decode(image)
    for item in decoded_items:
        if item.data:
            return item.data.decode("utf-8", errors="replace")
    raise RuntimeError("pyzbar 未识别到二维码")


def decode_qr_payload(image_path: Path) -> str:
    errors: list[str] = []
    for decoder in (_decode_qr_with_opencv, _decode_qr_with_pyzbar):
        try:
            return decoder(image_path)
        except Exception as exc:
            errors.append(f"{decoder.__name__}: {exc}")
    joined_errors = "\n".join(f"- {item}" for item in errors)
    raise RuntimeError(
        "二维码解码失败。\n"
        "可先安装以下任一方案后重试：\n"
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
