"""Local command channel for forwarding taskbar actions to the running app."""
from __future__ import annotations

import socket
import socketserver
import threading
from collections.abc import Callable, Sequence


COMMAND_ARG = "--aica-command"
COMMAND_OPEN_PANEL = "open-panel"
COMMAND_CAPTURE = "capture"
COMMAND_QUIT = "quit"
VALID_COMMANDS = frozenset({COMMAND_OPEN_PANEL, COMMAND_CAPTURE, COMMAND_QUIT})
COMMAND_SERVER_HOST = "127.0.0.1"
COMMAND_SERVER_PORT = 48173


def parse_startup_command(argv: Sequence[str]) -> str | None:
    try:
        index = list(argv).index(COMMAND_ARG)
    except ValueError:
        return None
    if index + 1 >= len(argv):
        return None
    command = str(argv[index + 1]).strip()
    return command if command in VALID_COMMANDS else None


def send_app_command(command: str, *, timeout: float = 0.6, port: int = COMMAND_SERVER_PORT) -> bool:
    if command not in VALID_COMMANDS:
        return False
    try:
        with socket.create_connection((COMMAND_SERVER_HOST, port), timeout=timeout) as client:
            client.sendall(f"{command}\n".encode("utf-8"))
            client.settimeout(timeout)
            return client.recv(16).strip() == b"ok"
    except OSError:
        return False


class _CommandTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class AppCommandServer:
    def __init__(self, handler: Callable[[str], None], *, port: int = COMMAND_SERVER_PORT):
        self._handler = handler
        self._port = port
        self._server: _CommandTCPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._server is not None:
            return

        handler = self._handler

        class _RequestHandler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                raw = self.request.recv(128)
                command = raw.decode("utf-8", errors="ignore").strip().splitlines()[0:1]
                if not command or command[0] not in VALID_COMMANDS:
                    self.request.sendall(b"error\n")
                    return
                handler(command[0])
                self.request.sendall(b"ok\n")

        self._server = _CommandTCPServer((COMMAND_SERVER_HOST, self._port), _RequestHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="aica-command-server", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        server = self._server
        self._server = None
        if server is None:
            return
        server.shutdown()
        server.server_close()
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=0.5)
