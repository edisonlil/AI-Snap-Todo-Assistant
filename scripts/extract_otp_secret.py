from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


def _parse_otpauth_payload(payload: str) -> dict[str, object]:
    normalized = _normalize_text(payload)
    if not normalized:
        raise ValueError("二维码内容为空")

    if not normalized.lower().startswith("otpauth://"):
        secret_match = re.search(r"(?:^|[?&])secret=([A-Z2-7=]+)", normalized, flags=re.IGNORECASE)
        secret = _normalize_text(secret_match.group(1) if secret_match else normalized)
        return {
            "type": "raw",
            "secret": secret.replace(" ", "").replace("-", "").upper(),
            "issuer": "",
            "account": "",
            "algorithm": "SHA1",
            "digits": 6,
            "period": 30,
            "label": "",
            "raw_payload": normalized,
        }

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

    return {
        "type": parsed.netloc or "totp",
        "secret": secret,
        "issuer": issuer,
        "account": account,
        "algorithm": algorithm,
        "digits": digits,
        "period": period,
        "label": label,
        "raw_payload": normalized,
    }


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


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从 OTP 二维码图片中提取 secret")
    parser.add_argument("image_path", help="二维码图片路径")
    parser.add_argument("--json", action="store_true", dest="as_json", help="以 JSON 输出结果")
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    image_path = Path(args.image_path).expanduser().resolve()
    if not image_path.is_file():
        print(f"文件不存在: {image_path}", file=sys.stderr)
        return 1

    try:
        payload = decode_qr_payload(image_path)
        parsed = _parse_otpauth_payload(payload)
    except Exception as exc:
        print(f"提取失败: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
        return 0

    print(f"secret: {parsed['secret']}")
    print(f"type: {parsed['type']}")
    print(f"issuer: {parsed['issuer']}")
    print(f"account: {parsed['account']}")
    print(f"algorithm: {parsed['algorithm']}")
    print(f"digits: {parsed['digits']}")
    print(f"period: {parsed['period']}")
    print(f"raw_payload: {parsed['raw_payload']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
