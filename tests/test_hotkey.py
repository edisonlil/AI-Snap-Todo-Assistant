import pytest

from aica.hotkey import hotkey_to_pynput_expression, normalize_hotkey


def test_normalize_hotkey_orders_and_normalizes_tokens():
    assert normalize_hotkey(" alt + a ") == "Alt+A"
    assert normalize_hotkey("shift+ctrl+a") == "Ctrl+Shift+A"


def test_hotkey_to_pynput_expression_builds_listener_binding():
    assert hotkey_to_pynput_expression("Alt+A") == "<alt>+a"
    assert hotkey_to_pynput_expression("Ctrl+Shift+A") == "<ctrl>+<shift>+a"


@pytest.mark.parametrize(
    "raw_hotkey",
    [
        "",
        "A",
        "Ctrl++A",
        "Ctrl+Alt",
        "Ctrl+Ctrl+A",
    ],
)
def test_normalize_hotkey_rejects_invalid_values(raw_hotkey):
    with pytest.raises(ValueError):
        normalize_hotkey(raw_hotkey)
