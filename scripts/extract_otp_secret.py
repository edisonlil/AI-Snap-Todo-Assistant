from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aica.otp_secret_extractor import extract_otp_secret_from_qr_image


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
        parsed = extract_otp_secret_from_qr_image(image_path)
    except Exception as exc:
        print(f"提取失败: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(parsed.to_dict(), ensure_ascii=False, indent=2))
        return 0

    print(f"secret: {parsed.secret}")
    print(f"type: {parsed.type}")
    print(f"issuer: {parsed.issuer}")
    print(f"account: {parsed.account}")
    print(f"algorithm: {parsed.algorithm}")
    print(f"digits: {parsed.digits}")
    print(f"period: {parsed.period}")
    print(f"raw_payload: {parsed.raw_payload}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
