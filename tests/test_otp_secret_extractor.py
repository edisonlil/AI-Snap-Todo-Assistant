from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import aica.otp_secret_extractor as extractor  # noqa: E402


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
