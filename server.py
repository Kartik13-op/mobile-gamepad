"""TouchKeys — FastAPI server entry point.

Start with:
    python server.py
"""

from __future__ import annotations

import uuid
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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

# ---------------------------------------------------------------------------
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
# Application lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Print the connection URL on startup and release keys on shutdown."""
    ip = get_local_ip()
    logger.info("TouchKeys server starting...")
    logger.info("Open on your phone -> http://%s:8000", ip)
    yield
    keyboard.release_all()
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
    return {"clients": connections.get_connections()}


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Persistent bidirectional channel for input events and layout sync."""
    client_id = uuid.uuid4().hex[:8]
    await connections.connect(client_id, websocket)

    try:
        # Send initial state
        await connections.send(client_id, {
            "type": "connected",
            "clientId": client_id,
            "ip": get_local_ip(),
        })
        await connections.send(client_id, {
            "type": "layout",
            "data": layout_manager.get_layout(),
        })
        await connections.send(client_id, {
            "type": "settings",
            "data": config_manager.get_dict(),
        })

        # Message loop
        while True:
            data = await websocket.receive_json()
            await event_router.route(client_id, data)

    except WebSocketDisconnect:
        logger.info("Client %s disconnected normally", client_id)
    except Exception as exc:
        logger.error("WebSocket error for %s: %s", client_id, exc)
    finally:
        keyboard.release_all()
        await connections.disconnect(client_id)


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
