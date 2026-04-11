"""Helpers for sanitizing invalid Unicode surrogates in text payloads."""
from __future__ import annotations

from typing import Any


def strip_invalid_surrogates(value: str) -> str:
    if not value:
        return ""
    return "".join(char if not 0xD800 <= ord(char) <= 0xDFFF else "\uFFFD" for char in value)


def sanitize_text(value: Any) -> str:
    return strip_invalid_surrogates(str(value or "")).strip()


def sanitize_json_like(value: Any) -> Any:
    if isinstance(value, str):
        return strip_invalid_surrogates(value)
    if isinstance(value, dict):
        return {
            strip_invalid_surrogates(str(key)): sanitize_json_like(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_json_like(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_json_like(item) for item in value]
    return value


def find_invalid_surrogate_paths(value: Any, path: str = "$") -> list[str]:
    matches: list[str] = []
    if isinstance(value, str):
        for index, char in enumerate(value):
            if 0xD800 <= ord(char) <= 0xDFFF:
                matches.append(f"{path}[{index}]=U+{ord(char):04X}")
        return matches
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = strip_invalid_surrogates(str(key))
            matches.extend(find_invalid_surrogate_paths(item, f"{path}.{key_text}"))
        return matches
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            matches.extend(find_invalid_surrogate_paths(item, f"{path}[{index}]"))
        return matches
    return matches
