from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.product_catalog import canonical_product_line, normalize_product_module, product_line_options, product_module_options  # noqa: E402


def test_product_line_options_include_excel_values() -> None:
    options = product_line_options()

    assert any(item["value"] == "PC Office" for item in options)
    assert any(item["value"] == "WPS会议" for item in options)


def test_product_module_options_follow_product_line_mapping() -> None:
    options = product_module_options("PC Office")

    values = [item["value"] for item in options]
    assert "PC Office-文字" in values
    assert "PC Office-表格" in values
    assert "WPS会议" not in values


def test_normalize_product_module_rejects_mismatched_module() -> None:
    assert normalize_product_module("PC Office", "PC Office-文字") == "PC Office-文字"
    assert normalize_product_module("WPS会议", "PC Office-文字") == ""


def test_legacy_product_line_alias_maps_to_catalog_modules() -> None:
    assert canonical_product_line("私网文档中台") == "私有云文档"
    values = [item["value"] for item in product_module_options("私网文档中台")]
    assert "文档中台" in values
