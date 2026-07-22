"""TouchKeys — FastAPI server entry point.

Start with:
    python server.py
"""

from __future__ import annotations

import os
import sys
import uuid
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from controller.keyboard import KeyboardController
from controller.layout import LayoutManager
from controller.config import ConfigManager
from controller.events import EventRouter
from controller.storage import StorageManager
from controller.network import ConnectionManager, get_local_ip

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("touchkeys")

# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"

# ---------------------------------------------------------------------------
# Core managers (module-level singletons)
# ---------------------------------------------------------------------------

storage = StorageManager(BASE_DIR)
config_manager = ConfigManager(storage)
keyboard = KeyboardController()
layout_manager = LayoutManager(storage)
connections = ConnectionManager()
event_router = EventRouter(keyboard, layout_manager, config_manager, connections)

# ---------------------------------------------------------------------------
# Single-instance lock
# ---------------------------------------------------------------------------

_LOCK_FILE = BASE_DIR / ".server.lock"


def _acquire_lock() -> bool:
    """Prevent multiple server instances by creating a lock file with PID."""
    if _LOCK_FILE.exists():
        try:
            pid = int(_LOCK_FILE.read_text().strip())
            if os.name == "nt":
                import ctypes
                handle = ctypes.windll.kernel32.OpenProcess(0x0400, False, pid)
                if handle:
                    ctypes.windll.kernel32.CloseHandle(handle)
                    logger.warning("Server already running (PID %d). Exiting.", pid)
                    return False
            else:
                try:
                    os.kill(pid, 0)
                    logger.warning("Server already running (PID %d). Exiting.", pid)
                    return False
                except OSError:
                    pass
        except (ValueError, OSError):
            pass
        # Stale lock — clean it
        _LOCK_FILE.unlink(missing_ok=True)
    _LOCK_FILE.write_text(str(os.getpid()))
    return True


def _release_lock() -> None:
    try:
        _LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Print the connection URL on startup and release keys on shutdown."""
    if not _acquire_lock():
        sys.exit(1)
    ip = get_local_ip()
    logger.info("TouchKeys server starting...")
    logger.info("Open on your phone -> http://%s:8000", ip)
    keyboard.ensure_controller()
    logger.info("Virtual Xbox 360 gamepad ready")
    yield
    keyboard.release_all()
    keyboard.shutdown()
    _release_lock()
    logger.info("TouchKeys server stopped.")


app = FastAPI(title="TouchKeys", lifespan=lifespan)

# Serve static assets (CSS / JS / icons / themes)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Serve the main controller page."""
    html_path = TEMPLATE_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/monitor", response_class=HTMLResponse)
async def monitor() -> HTMLResponse:
    """Serve the desktop monitor page (WebSocket-based live input viewer)."""
    html_path = TEMPLATE_DIR / "monitor.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/ip")
async def get_ip() -> dict:
    """Return the LAN IP so the client can display it."""
    return {"ip": get_local_ip()}


@app.get("/api/keys")
async def get_keys() -> dict:
    """Return the list of supported key names for the UI dropdown."""
    return {"keys": keyboard.supported_keys()}


@app.get("/api/clients")
async def get_clients() -> dict:
    """Return the list of connected client IDs."""
    clients = connections.get_connections()
    return {"clients": clients, "count": len(clients)}


@app.delete("/api/clients/{client_id}")
async def remove_client(client_id: str) -> dict:
    """Remove a connected device from the active session."""
    if not connections.has_client(client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    was_active = connections.is_active_controller(client_id)
    event_router.release_client(client_id)
    promoted_client = await connections.remove_client(client_id)
    if was_active:
        keyboard.release_all()
    if promoted_client:
        await connections.send(promoted_client.client_id, {
            "type": "controller_activated",
            "message": "You are now the active controller",
        })
        await connections.broadcast({
            "type": "controller_changed",
            "activeClientId": promoted_client.client_id,
            "deviceName": promoted_client.device_name,
        }, exclude=promoted_client.client_id)
    return {"success": True}


@app.get("/api/debug")
async def get_debug() -> dict:
    """Return diagnostic info about the server state."""
    return {
        "controller_count": keyboard.controller_count,
        "connections": connections.count,
        "pressed_keys": list(keyboard.pressed_keys),
    }


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Persistent bidirectional channel for input events and layout sync."""
    client_id = uuid.uuid4().hex[:8]
    role = websocket.query_params.get("role", "controller")
    client = await connections.connect(client_id, websocket, can_control=(role != "monitor"))

    try:
        await connections.send(client_id, {
            "type": "session",
            "clientId": client_id,
            "deviceName": client.device_name,
            "ip": get_local_ip(),
            "isActive": client.is_active_controller,
        })
        await connections.send(client_id, {
            "type": "layout",
            "data": layout_manager.get_layout(),
        })
        await connections.send(client_id, {
            "type": "settings",
            "data": config_manager.get_dict(),
        })

        if client.is_active_controller:
            await connections.broadcast({
                "type": "controller_changed",
                "activeClientId": client_id,
                "deviceName": client.device_name,
            }, exclude=client_id)

        while True:
            data = await websocket.receive_json()
            if data.get("type") == "hello":
                device_name = str(data.get("deviceName", ""))[:50].strip()
                if device_name:
                    await connections.set_device_name(client_id, device_name)
                    await connections.send(client_id, {
                        "type": "device_updated",
                        "clientId": client_id,
                        "deviceName": device_name,
                        "isActive": connections.is_active_controller(client_id),
                    })
                continue

            await event_router.route(client_id, data)

    except WebSocketDisconnect:
        logger.info("Client %s disconnected normally", client_id)
    except Exception as exc:
        logger.error("WebSocket error for %s: %s", client_id, exc)
    finally:
        was_active_controller = connections.is_active_controller(client_id)
        event_router.release_client(client_id)
        if was_active_controller or connections.count <= 1:
            keyboard.release_all()
        promoted_client = await connections.disconnect(client_id)
        
        # If a waiting client was promoted to active, notify it
        if promoted_client:
            await connections.send(promoted_client.client_id, {
                "type": "controller_activated",
                "message": f"You are now the active controller",
            })
            await connections.broadcast({
                "type": "controller_changed",
                "activeClientId": promoted_client.client_id,
                "deviceName": promoted_client.device_name,
            }, exclude=promoted_client.client_id)


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    ip = get_local_ip()
    print()
    print("======================================================")
    print("   TouchKeys Server")
    print(f"   Open on your phone -> http://{ip}:8000")
    print("======================================================")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
