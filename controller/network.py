"""Network utilities and WebSocket connection management."""

from __future__ import annotations

import socket
import asyncio
import logging
from typing import Dict, Optional, Set
from dataclasses import dataclass

from fastapi import WebSocket

logger = logging.getLogger(__name__)

MAX_GAMEPAD_SLOTS = 4


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


@dataclass
class ClientInfo:
    """Metadata for a connected client."""
    client_id: str
    websocket: WebSocket
    device_name: str = "Unknown"
    is_active_controller: bool = False
    can_control: bool = True
    gamepad_slot: Optional[int] = None


class ConnectionManager:
    """Track active WebSocket connections with per-client metadata.

    Only one client can be the active controller at a time.
    This prevents multiple devices from controlling the same gamepad simultaneously.
    """

    def __init__(self) -> None:
        self._clients: Dict[str, ClientInfo] = {}
        self._lock = asyncio.Lock()
        self._active_controller_id: Optional[str] = None

    async def connect(self, client_id: str, websocket: WebSocket, can_control: bool = True) -> ClientInfo:
        """Accept a new WebSocket and register it with an optional gamepad slot."""
        await websocket.accept()
        async with self._lock:
            slot = self._assign_slot() if can_control else None
            client = ClientInfo(
                client_id=client_id,
                websocket=websocket,
                device_name=f"Device-{client_id[:4]}",
                is_active_controller=slot is not None and self._active_controller_id is None,
                can_control=can_control,
                gamepad_slot=slot,
            )
            self._clients[client_id] = client
            if client.is_active_controller:
                self._active_controller_id = client_id
        logger.info(
            "Client connected: %s (slot: %s, total: %d)", client_id, slot, len(self._clients)
        )
        return client

    def _assign_slot(self) -> Optional[int]:
        """Assign the next free gamepad slot (0–3). Returns None if all slots are taken."""
        used = {c.gamepad_slot for c in self._clients.values() if c.gamepad_slot is not None}
        for slot in range(MAX_GAMEPAD_SLOTS):
            if slot not in used:
                return slot
        return None

    async def disconnect(self, client_id: str) -> Optional[ClientInfo]:
        """Unregister a WebSocket client and free its gamepad slot."""
        async with self._lock:
            client = self._clients.pop(client_id, None)
            if client:
                slot = client.gamepad_slot
                was_active = client.is_active_controller
                if was_active:
                    self._active_controller_id = None
                    logger.info("Active controller client %s (slot %s) disconnected", client_id, slot)
                    # Promote first waiting client
                    for other_client in self._clients.values():
                        if other_client.can_control and not other_client.is_active_controller:
                            other_client.is_active_controller = True
                            self._active_controller_id = other_client.client_id
                            logger.info("Promoted client %s to active controller", other_client.client_id)
                            return other_client
                return client
        
        logger.info(
            "Client disconnected: %s (total: %d)", client_id, len(self._clients)
        )
        return None

    def get_gamepad_slot(self, client_id: str) -> Optional[int]:
        """Return the gamepad slot assigned to a client, or None."""
        client = self._clients.get(client_id)
        return client.gamepad_slot if client else None

    async def set_device_name(self, client_id: str, device_name: str) -> None:
        """Store a display name sent by the client."""
        async with self._lock:
            if client_id in self._clients:
                self._clients[client_id].device_name = device_name or f"Device-{client_id[:4]}"

    async def remove_client(self, client_id: str) -> Optional[ClientInfo]:
        """Close and remove a client by ID."""
        async with self._lock:
            client = self._clients.get(client_id)
        if client is None:
            return None
        try:
            await client.websocket.close(code=4000, reason="Removed by server")
        except Exception:
            pass
        return await self.disconnect(client_id)

    def get_active_controller_id(self) -> Optional[str]:
        """Get the currently active controller client ID."""
        return self._active_controller_id

    def is_active_controller(self, client_id: str) -> bool:
        """Check if a specific client is the active controller."""
        return self._active_controller_id == client_id

    def has_client(self, client_id: str) -> bool:
        """Return True when a client ID is currently connected."""
        return client_id in self._clients

    async def send(self, client_id: str, data: dict) -> bool:
        """Send a JSON message to a specific client. Returns True on success."""
        async with self._lock:
            client = self._clients.get(client_id)
        if client is None:
            return False
        try:
            await client.websocket.send_json(data)
            return True
        except Exception as exc:
            logger.error("send to %s failed: %s", client_id, exc)
            return False

    async def broadcast(
        self, data: dict, exclude: Optional[str] = None
    ) -> None:
        """Send a JSON message to every connected client, optionally skipping one."""
        async with self._lock:
            snapshot = {cid: c for cid, c in self._clients.items()}
        for cid, client in snapshot.items():
            if cid == exclude:
                continue
            try:
                await client.websocket.send_json(data)
            except Exception:
                pass

    def get_connections(self) -> list[dict]:
        """Return connection metadata for connected clients."""
        return [
            {
                "clientId": client.client_id,
                "deviceName": client.device_name,
                "isActive": client.is_active_controller,
                "canControl": client.can_control,
                "gamepadSlot": client.gamepad_slot,
            }
            for client in self._clients.values()
        ]

    @property
    def count(self) -> int:
        """Number of currently connected clients."""
        return len(self._clients)
