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
from backend.server import app, get_local_ip, set_mobile_server_controller, keyboard, stream_manager
from backend.tls import ensure_certificate, certificate_paths

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("touchkeys.gui")

HOST = "127.0.0.1"
PORT = 8000
MOBILE_HOST = "0.0.0.0"
MOBILE_PORT = 8001

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
        self._mobile_controller = MobileServerController(self)

    @property
    def mobile_controller(self) -> "MobileServerController":
        return self._mobile_controller

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
        if self._loop and self._mobile_controller.running:
            future = asyncio.run_coroutine_threadsafe(self._mobile_controller.stop(), self._loop)
            try:
                future.result(timeout=4)
            except Exception:
                logger.debug("Mobile server did not stop cleanly", exc_info=True)
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=3)
        keyboard.release_all()
        keyboard.shutdown()

    def wait_until_ready(self, timeout: float = 10.0) -> bool:
        import urllib.request
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/ip", timeout=1)
                return True
            except Exception:
                time.sleep(0.3)
        return False


class MobileServerController:
    """Start/stop the LAN server on the local monitor's event loop."""

    def __init__(self, owner: ServerThread) -> None:
        self.owner = owner
        self._server: uvicorn.Server | None = None
        self._task: asyncio.Task | None = None

    @property
    def running(self) -> bool:
        return bool(self._server and self._task and not self._task.done())

    def status(self) -> dict:
        ip = get_local_ip()
        cert_path, _ = certificate_paths(DATA_DIR)
        return {
            "running": self.running,
            "host": ip,
            "port": MOBILE_PORT,
            "url": f"https://{ip}:{MOBILE_PORT}",
            "http_url": f"http://{ip}:{MOBILE_PORT}",
            "certificate_url": f"https://{ip}:{MOBILE_PORT}/api/certificate",
            "certificate_ready": cert_path.exists(),
            "available": True,
        }

    async def start(self) -> dict:
        if self.running:
            return self.status()
        lan_ip = get_local_ip()
        try:
            cert_path, key_path = ensure_certificate(DATA_DIR, lan_ip)
        except RuntimeError as exc:
            logger.error("Could not prepare HTTPS phone server: %s", exc)
            raise
        config = uvicorn.Config(
            app,
            host=MOBILE_HOST,
            port=MOBILE_PORT,
            log_level="warning",
            ssl_certfile=str(cert_path),
            ssl_keyfile=str(key_path),
        )
        self._server = uvicorn.Server(config)
        self._task = asyncio.create_task(self._server.serve())
        for _ in range(20):
            if self._server.started:
                break
            await asyncio.sleep(0.05)
        logger.info("Mobile server started at %s", self.status()["url"])
        return self.status()

    async def stop(self) -> dict:
        if self._server:
            self._server.should_exit = True
        if self._task:
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=4)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                logger.warning("Mobile server shutdown timed out")
        self._server = None
        self._task = None
        await stream_manager.stop()
        logger.info("Mobile server stopped")
        return self.status()

def main() -> None:
    server = ServerThread()
    set_mobile_server_controller(server.mobile_controller)

    print()
    print("==============================================")
    print("  TouchKeys Desktop GUI")
    print("==============================================")
    print()
    print("  Starting server...")
    server.start()

    if server.wait_until_ready():
        ip = get_local_ip()
        print(f"  Monitor server running at http://localhost:{PORT}")
        print(f"  Monitor page  -> http://localhost:{PORT}/monitor")
        print("  Phone server  -> started from the monitor")
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
