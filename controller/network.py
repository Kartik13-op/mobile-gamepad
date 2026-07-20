"""Network utilities and WebSocket connection management."""

from __future__ import annotations

import socket
import asyncio
import logging
from typing import Dict, Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """Detect the LAN IP address of this machine.

    Uses a UDP connect trick that doesn't actually send data,
    so it works even without internet access.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.1)
        # Connecting to a non-routable address reveals the local IP
        sock.connect(("10.255.255.255", 1))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


class ConnectionManager:
    """Track active WebSocket connections and provide send / broadcast helpers."""

    def __init__(self) -> None:
        self._connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        """Accept a new WebSocket and register it."""
        await websocket.accept()
        async with self._lock:
            self._connections[client_id] = websocket
        logger.info(
            "Client connected: %s (total: %d)", client_id, len(self._connections)
        )

    async def disconnect(self, client_id: str) -> None:
        """Unregister a WebSocket client."""
        async with self._lock:
            self._connections.pop(client_id, None)
        logger.info(
            "Client disconnected: %s (total: %d)", client_id, len(self._connections)
        )

    async def send(self, client_id: str, data: dict) -> bool:
        """Send a JSON message to a specific client. Returns True on success."""
        async with self._lock:
            ws = self._connections.get(client_id)
        if ws is None:
            return False
        try:
            await ws.send_json(data)
            return True
        except Exception as exc:
            logger.error("send to %s failed: %s", client_id, exc)
            return False

    async def broadcast(
        self, data: dict, exclude: Optional[str] = None
    ) -> None:
        """Send a JSON message to every connected client, optionally skipping one."""
        async with self._lock:
            snapshot = dict(self._connections)
        for cid, ws in snapshot.items():
            if cid == exclude:
                continue
            try:
                await ws.send_json(data)
            except Exception:
                pass

    def get_connections(self) -> list[str]:
        """Return a list of all connected client IDs."""
        return list(self._connections.keys())

    @property
    def count(self) -> int:
        """Number of currently connected clients."""
        return len(self._connections)
