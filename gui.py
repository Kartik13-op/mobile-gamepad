"""TouchKeys Desktop GUI — starts the server and opens the web monitor.

Usage:
    python gui.py

This starts the backend server in a background thread and opens
the web-based desktop monitor (http://localhost:8000/monitor)
in your default browser. Press Ctrl+C to stop.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

# Import the FastAPI app from server.py
from server import app, get_local_ip

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("touchkeys.gui")

HOST = "0.0.0.0"
PORT = 8000

# Clean up any stale lock file from a previous run
lock_file = Path(__file__).parent / ".server.lock"
lock_file.unlink(missing_ok=True)


class ServerThread:
    """Runs uvicorn serving the FastAPI app in a background thread."""

    def __init__(self) -> None:
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        config = uvicorn.Config(app, host=HOST, port=PORT, log_level="info")
        self._server = uvicorn.Server(config)
        self._loop.run_until_complete(self._server.serve())

    def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=3)

    def wait_until_ready(self, timeout: float = 10.0) -> bool:
        import urllib.request
        import urllib.error
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/ip", timeout=1)
                return True
            except Exception:
                time.sleep(0.3)
        return False


def main() -> None:
    server = ServerThread()

    print()
    print("==============================================")
    print("  TouchKeys Desktop GUI")
    print("==============================================")
    print()
    print("  Starting server...")
    server.start()

    if server.wait_until_ready():
        ip = get_local_ip()
        print(f"  Server running at http://{ip}:{PORT}")
        print(f"  Monitor page  -> http://localhost:{PORT}/monitor")
        print(f"  Phone URL     -> http://{ip}:{PORT}")
        print()
        print("  Opening desktop monitor in your browser...")
        webbrowser.open(f"http://localhost:{PORT}/monitor")
        print()
        print("  Press Ctrl+C to stop the server.")
        print("==============================================")
        print()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  Shutting down...")
        finally:
            server.stop()
    else:
        print("  [ERROR] Server failed to start in time.")
        server.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
