"""TouchKeys — FastAPI server entry point.

Start with:
    python backend/server.py
"""

from __future__ import annotations

import os
import sys
import uuid
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Allow ``python backend/server.py`` to import the sibling controller package.
PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from controller.keyboard import KeyboardController
from controller.layout import LayoutManager
from controller.config import ConfigManager
from controller.events import EventRouter
from controller.storage import StorageManager
from controller.network import ConnectionManager, get_local_ip
from backend.streaming import stream_manager

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

if getattr(sys, "frozen", False):
    BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    DATA_DIR = Path(sys.executable).parent
else:
    BASE_DIR = PROJECT_DIR
    DATA_DIR = PROJECT_DIR

TEMPLATE_DIR = BASE_DIR / "templates"

# ---------------------------------------------------------------------------
# Core managers (module-level singletons)
# ---------------------------------------------------------------------------

storage = StorageManager(DATA_DIR)
config_manager = ConfigManager(storage)
keyboard = KeyboardController()
layout_manager = LayoutManager(storage)
connections = ConnectionManager()
event_router = EventRouter(keyboard, layout_manager, config_manager, connections)

# ---------------------------------------------------------------------------
# Single-instance lock
# ---------------------------------------------------------------------------

_LOCK_FILE = DATA_DIR / ".server.lock"
mobile_server_controller = None


def set_mobile_server_controller(controller) -> None:
    """Attach the GUI-owned on-demand mobile server controller."""
    global mobile_server_controller
    mobile_server_controller = controller


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
    """Log server startup. Cleanup is owned by the GUI/standalone runner."""
    logger.info("TouchKeys server starting...")
    yield
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
    html_path = TEMPLATE_DIR / "mobile.html"
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


@app.get("/api/mobile-server")
async def mobile_server_status() -> dict:
    """Return the on-demand phone server state to the local monitor."""
    if mobile_server_controller is None:
        return {"running": False, "available": False}
    return mobile_server_controller.status()


@app.post("/api/mobile-server/start")
async def mobile_server_start() -> dict:
    if mobile_server_controller is None:
        raise HTTPException(status_code=503, detail="The desktop launcher is not managing a mobile server")
    return await mobile_server_controller.start()


@app.post("/api/mobile-server/stop")
async def mobile_server_stop() -> dict:
    if mobile_server_controller is None:
        raise HTTPException(status_code=503, detail="The desktop launcher is not managing a mobile server")
    return await mobile_server_controller.stop()


@app.get("/api/qr")
async def qr_code(data: str) -> Response:
    """Generate the phone QR locally so the monitor has no external dependency."""
    try:
        import qrcode
        image = qrcode.make(data)
        buffer = __import__("io").BytesIO()
        image.save(buffer, format="PNG")
        return Response(content=buffer.getvalue(), media_type="image/png")
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="QR support is not installed") from exc


@app.get("/api/certificate")
async def certificate() -> FileResponse:
    """Download the public certificate so it can be trusted on a phone."""
    from backend.tls import certificate_paths
    cert_path, _ = certificate_paths(DATA_DIR)
    if not cert_path.exists():
        raise HTTPException(status_code=404, detail="HTTPS certificate is not ready")
    return FileResponse(cert_path, media_type="application/x-x509-ca-cert", filename="touchkeys-phone.crt")


@app.get("/api/stream/status")
async def stream_status() -> dict:
    return stream_manager.status()


@app.put("/api/stream/settings")
async def stream_settings(data: dict) -> dict:
    return {"settings": stream_manager.update_settings(data)}


@app.post("/api/stream/start")
async def stream_start() -> dict:
    if not stream_manager.status()["available"]:
        raise HTTPException(status_code=503, detail="Install aiortc, mss, numpy, and Pillow to enable screen streaming")
    return stream_manager.start()


@app.post("/api/stream/stop")
async def stream_stop() -> dict:
    return await stream_manager.stop()


@app.post("/api/webrtc/offer")
async def webrtc_offer(data: dict) -> dict:
    try:
        return await stream_manager.create_answer(data)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


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
    slot = connections.get_gamepad_slot(client_id)
    event_router.release_client(client_id)
    promoted_client = await connections.remove_client(client_id)
    if slot is not None:
        keyboard.release_all(slot)
        keyboard.free_slot(slot)
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
        "pressed_keys": list(keyboard.pressed_keys()),
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

    slot = client.gamepad_slot
    try:
        await connections.send(client_id, {
            "type": "session",
            "clientId": client_id,
            "deviceName": client.device_name,
            "ip": get_local_ip(),
            "isActive": client.is_active_controller,
            "gamepadSlot": slot,
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
                "slot": slot,
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
                        "gamepadSlot": slot,
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
        if slot is not None:
            keyboard.release_all(slot)
            keyboard.free_slot(slot)
        promoted_client = await connections.disconnect(client_id)
        
        if promoted_client:
            pslot = promoted_client.gamepad_slot
            await connections.send(promoted_client.client_id, {
                "type": "controller_activated",
                "message": f"You are now the active controller",
                "slot": pslot,
            })
            await connections.broadcast({
                "type": "controller_changed",
                "activeClientId": promoted_client.client_id,
                "deviceName": promoted_client.device_name,
                "slot": pslot,
            }, exclude=promoted_client.client_id)


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print()
    print("======================================================")
    print("   TouchKeys Local Monitor")
    print("   Open locally -> http://localhost:8000/monitor")
    print("======================================================")
    print()
    if not _acquire_lock():
        raise SystemExit(1)
    try:
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    finally:
        keyboard.release_all()
        keyboard.shutdown()
        _release_lock()
