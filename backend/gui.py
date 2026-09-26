"""TouchKeys Desktop GUI — starts the server and opens the web monitor.

Usage:
    python backend/gui.py

This starts the backend server in a background thread and opens
the web-based desktop monitor (http://localhost:8000/monitor) in
a native desktop window. Press Ctrl+C to stop.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time
from pathlib import Path
   
# When this file is started as ``python backend/gui.py``, Python puts the
# backend directory on sys.path rather than the project root. Add the root so
# the sibling ``controller`` package and ``backend`` package are importable.
PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import uvicorn

try:
    import webview
except ImportError:
    webview = None

# Import the FastAPI app from server.py
from backend.server import app, get_local_ip

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("touchkeys.gui")

HOST = "0.0.0.0"
PORT = 8000

# Clean up any stale lock file from a previous run
if getattr(sys, "frozen", False):
    DATA_DIR = Path(sys.executable).parent
else:
    DATA_DIR = PROJECT_DIR
lock_file = DATA_DIR / ".server.lock"
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
        monitor_url = f"http://localhost:{PORT}/monitor"
        monitor_in_native_window = open_monitor(monitor_url)
        if monitor_in_native_window:
            print("  Opening desktop monitor window...")
        else:
            print("  Opening the monitor in your browser...")
        print()
        if monitor_in_native_window:
            print("  Close the monitor window or press Ctrl+C to stop the server.")
        else:
            print("  Press Ctrl+C to stop the server.")
        print("==============================================")
        print()

        try:
            if not monitor_in_native_window:
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


def open_monitor(url: str) -> bool:
    """Open the monitor in a native window, with a browser fallback."""
    if webview is None:
        import webbrowser
        webbrowser.open(url)
        return False

    try:
        webview.create_window(
            "TouchKeys Monitor",
            url,
            width=2046,
            height=1080,
            min_size=(1024, 700),
            resizable=True,
            confirm_close=True,
        )
        webview.start()
        return True
    except Exception as exc:
        logger.warning("pywebview could not start (%s); falling back to the browser.", exc)
        import webbrowser

        webbrowser.open(url)
        return False


if __name__ == "__main__":
    main()
