from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.app_commands import (  # noqa: E402
    COMMAND_SERVER_HOST,
    COMMAND_ARG,
    COMMAND_CAPTURE,
    COMMAND_OPEN_PANEL,
    COMMAND_QUIT,
    AppCommandServer,
    parse_startup_command,
    send_app_command,
)


def _free_port() -> int:
    import socket

    with socket.socket() as sock:
        sock.bind((COMMAND_SERVER_HOST, 0))
        return sock.getsockname()[1]


def test_parse_startup_command_accepts_known_commands() -> None:
    assert parse_startup_command(["app", COMMAND_ARG, COMMAND_CAPTURE]) == COMMAND_CAPTURE
    assert parse_startup_command(["app", COMMAND_ARG, COMMAND_OPEN_PANEL]) == COMMAND_OPEN_PANEL
    assert parse_startup_command(["app", COMMAND_ARG, COMMAND_QUIT]) == COMMAND_QUIT


def test_parse_startup_command_rejects_missing_or_unknown_commands() -> None:
    assert parse_startup_command(["app"]) is None
    assert parse_startup_command(["app", COMMAND_ARG]) is None
    assert parse_startup_command(["app", COMMAND_ARG, "bad"]) is None


def test_app_command_server_receives_forwarded_command() -> None:
    received: list[str] = []
    port = _free_port()
    server = AppCommandServer(received.append, port=port)
    server.start()
    try:
        assert send_app_command(COMMAND_CAPTURE, port=port) is True
    finally:
        server.stop()

    assert received == [COMMAND_CAPTURE]


def test_send_app_command_rejects_unknown_command() -> None:
    assert send_app_command("bad") is False
