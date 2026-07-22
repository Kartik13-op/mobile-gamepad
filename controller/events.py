"""WebSocket event routing — dispatches incoming messages to handlers."""

from __future__ import annotations

import asyncio
import time
import logging
import math
from typing import Any, Awaitable, Callable, Dict

from controller.keyboard import KeyboardController
from controller.layout import LayoutManager
from controller.config import ConfigManager
from controller.network import ConnectionManager

logger = logging.getLogger(__name__)

Handler = Callable[[str, Dict[str, Any]], Awaitable[None]]


class EventRouter:
    """Routes WebSocket messages by their ``type`` field to registered handlers."""

    def __init__(
        self,
        keyboard: KeyboardController,
        layout: LayoutManager,
        config: ConfigManager,
        connections: ConnectionManager,
    ) -> None:
        self.keyboard = keyboard
        self.layout = layout
        self.config = config
        self.connections = connections
        self._pressed_by_client: Dict[str, set[str]] = {}
        self._analog_by_client: Dict[str, Dict[str, tuple[float, float, float]]] = {}

        self._handlers: Dict[str, Handler] = {
            "keydown": self._on_keydown,
            "keyup": self._on_keyup,
            "analog": self._on_analog,
            "ping": self._on_ping,
            "save_layout": self._on_save_layout,
            "load_layout": self._on_load_layout,
            "update_layout": self._on_update_layout,
            "save_settings": self._on_save_settings,
            "load_settings": self._on_load_settings,
            "export_layout": self._on_export_layout,
            "import_layout": self._on_import_layout,
            "undo": self._on_undo,
            "redo": self._on_redo,
            "add_button": self._on_add_button,
            "update_button": self._on_update_button,
            "delete_button": self._on_delete_button,
            "duplicate_button": self._on_duplicate_button,
            "add_page": self._on_add_page,
            "delete_page": self._on_delete_page,
            "rename_page": self._on_rename_page,
            "set_active_page": self._on_set_active_page,
        }

    def release_client(self, client_id: str) -> None:
        """Forget per-client de-duplication state after disconnect/removal."""
        self._pressed_by_client.pop(client_id, None)
        self._analog_by_client.pop(client_id, None)

    async def route(self, client_id: str, message: Dict[str, Any]) -> None:
        """Dispatch a message to its handler based on the ``type`` field."""
        msg_type = message.get("type")
        handler = self._handlers.get(msg_type)
        if handler is not None:
            await handler(client_id, message)
        else:
            logger.warning("Unknown message type from %s: %s", client_id, msg_type)

    # ------------------------------------------------------------------
    # Input handlers
    # ------------------------------------------------------------------

    async def _on_keydown(self, client_id: str, msg: Dict[str, Any]) -> None:
        if not self.connections.is_active_controller(client_id):
            logger.debug("Ignored keydown from non-active client %s", client_id)
            return
        key = str(msg.get("key", "")).lower().strip()
        if key:
            pressed = self._pressed_by_client.setdefault(client_id, set())
            if key in pressed:
                return
            pressed.add(key)
            self.keyboard.ensure_controller()
            self.keyboard.press_key(key)
            asyncio.create_task(self.connections.broadcast({
                "type": "input", "subtype": "keydown", "key": key,
            }, exclude=client_id))

    async def _on_keyup(self, client_id: str, msg: Dict[str, Any]) -> None:
        if not self.connections.is_active_controller(client_id):
            logger.debug("Ignored keyup from non-active client %s", client_id)
            return
        key = str(msg.get("key", "")).lower().strip()
        if key:
            pressed = self._pressed_by_client.setdefault(client_id, set())
            if key not in pressed:
                return
            pressed.discard(key)
            self.keyboard.release_key(key)
            asyncio.create_task(self.connections.broadcast({
                "type": "input", "subtype": "keyup", "key": key,
            }, exclude=client_id))

    async def _on_analog(self, client_id: str, msg: Dict[str, Any]) -> None:
        if not self.connections.is_active_controller(client_id):
            logger.debug("Ignored analog from non-active client %s", client_id)
            return
        key = str(msg.get("key", "")).lower().strip()
        try:
            x = float(msg.get("x", 0))
            y = float(msg.get("y", 0))
        except (TypeError, ValueError):
            return
        if key:
            analog = self._analog_by_client.setdefault(client_id, {})
            now = time.monotonic()
            last = analog.get(key)
            if last is not None:
                last_x, last_y, last_time = last
                is_neutral = math.isclose(x, 0.0, abs_tol=0.001) and math.isclose(y, 0.0, abs_tol=0.001)
                last_is_neutral = math.isclose(last_x, 0.0, abs_tol=0.001) and math.isclose(last_y, 0.0, abs_tol=0.001)
                tiny_move = abs(x - last_x) < 0.01 and abs(y - last_y) < 0.01
                if tiny_move and not is_neutral and now - last_time < 0.05:
                    return
                if tiny_move and is_neutral and last_is_neutral:
                    return
            analog[key] = (x, y, now)
            self.keyboard.ensure_controller()
            self.keyboard.move_analog(key, x, y)
            asyncio.create_task(self.connections.broadcast({
                "type": "input", "subtype": "analog", "key": key, "x": x, "y": y,
            }, exclude=client_id))

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    async def _on_ping(self, client_id: str, msg: Dict[str, Any]) -> None:
        await self.connections.send(client_id, {
            "type": "pong",
            "timestamp": msg.get("timestamp", 0),
            "serverTime": int(time.time() * 1000),
        })

    # ------------------------------------------------------------------
    # Layout persistence
    # ------------------------------------------------------------------

    async def _on_save_layout(self, client_id: str, msg: Dict[str, Any]) -> None:
        data = msg.get("data")
        if data:
            self.layout.set_layout(data)
        success = self.layout.save()
        await self.connections.send(client_id, {
            "type": "save_result",
            "success": success,
        })

    async def _on_load_layout(self, client_id: str, msg: Dict[str, Any]) -> None:
        await self.connections.send(client_id, {
            "type": "layout",
            "data": self.layout.get_layout(),
        })

    async def _on_update_layout(self, client_id: str, msg: Dict[str, Any]) -> None:
        data = msg.get("data")
        if data:
            self.layout.set_layout(data)
            if self.config.config.autoSave:
                self.layout.save()
            await self.connections.broadcast(
                {"type": "layout", "data": self.layout.get_layout()},
                exclude=client_id,
            )

    async def _on_export_layout(self, client_id: str, msg: Dict[str, Any]) -> None:
        await self.connections.send(client_id, {
            "type": "export_layout",
            "data": self.layout.get_layout(),
        })

    async def _on_import_layout(self, client_id: str, msg: Dict[str, Any]) -> None:
        data = msg.get("data")
        if data and self.layout.validate_layout(data):
            self.layout.set_layout(data)
            self.layout.save()
            await self.connections.send(client_id, {
                "type": "layout",
                "data": self.layout.get_layout(),
            })
        else:
            await self.connections.send(client_id, {
                "type": "error",
                "message": "Invalid layout data",
            })

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    async def _on_undo(self, client_id: str, msg: Dict[str, Any]) -> None:
        layout = self.layout.undo()
        if layout:
            await self.connections.broadcast({"type": "layout", "data": layout})

    async def _on_redo(self, client_id: str, msg: Dict[str, Any]) -> None:
        layout = self.layout.redo()
        if layout:
            await self.connections.broadcast({"type": "layout", "data": layout})

    # ------------------------------------------------------------------
    # Button CRUD
    # ------------------------------------------------------------------

    async def _on_add_button(self, client_id: str, msg: Dict[str, Any]) -> None:
        page_id = msg.get("pageId")
        button_data = msg.get("data", {})
        if page_id:
            self.layout.add_button(page_id, button_data)
            if self.config.config.autoSave:
                self.layout.save()
            await self.connections.broadcast(
                {"type": "layout", "data": self.layout.get_layout()}
            )

    async def _on_update_button(self, client_id: str, msg: Dict[str, Any]) -> None:
        page_id = msg.get("pageId")
        button_id = msg.get("buttonId")
        updates = msg.get("data", {})
        if page_id and button_id:
            self.layout.update_button(page_id, button_id, updates)
            if self.config.config.autoSave:
                self.layout.save()
            await self.connections.broadcast(
                {"type": "layout", "data": self.layout.get_layout()},
                exclude=client_id,
            )

    async def _on_delete_button(self, client_id: str, msg: Dict[str, Any]) -> None:
        page_id = msg.get("pageId")
        button_id = msg.get("buttonId")
        if page_id and button_id:
            self.layout.delete_button(page_id, button_id)
            if self.config.config.autoSave:
                self.layout.save()
            await self.connections.broadcast(
                {"type": "layout", "data": self.layout.get_layout()}
            )

    async def _on_duplicate_button(self, client_id: str, msg: Dict[str, Any]) -> None:
        page_id = msg.get("pageId")
        button_id = msg.get("buttonId")
        if page_id and button_id:
            self.layout.duplicate_button(page_id, button_id)
            if self.config.config.autoSave:
                self.layout.save()
            await self.connections.broadcast(
                {"type": "layout", "data": self.layout.get_layout()}
            )

    # ------------------------------------------------------------------
    # Page CRUD
    # ------------------------------------------------------------------

    async def _on_add_page(self, client_id: str, msg: Dict[str, Any]) -> None:
        name = msg.get("name", "New Page")
        self.layout.add_page(name)
        if self.config.config.autoSave:
            self.layout.save()
        await self.connections.broadcast(
            {"type": "layout", "data": self.layout.get_layout()}
        )

    async def _on_delete_page(self, client_id: str, msg: Dict[str, Any]) -> None:
        page_id = msg.get("pageId")
        if page_id:
            self.layout.delete_page(page_id)
            if self.config.config.autoSave:
                self.layout.save()
            await self.connections.broadcast(
                {"type": "layout", "data": self.layout.get_layout()}
            )

    async def _on_rename_page(self, client_id: str, msg: Dict[str, Any]) -> None:
        page_id = msg.get("pageId")
        name = msg.get("name")
        if page_id and name:
            self.layout.rename_page(page_id, name)
            if self.config.config.autoSave:
                self.layout.save()
            await self.connections.broadcast(
                {"type": "layout", "data": self.layout.get_layout()}
            )

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    async def _on_save_settings(self, client_id: str, msg: Dict[str, Any]) -> None:
        data = msg.get("data", {})
        self.config.update(data)
        self.config.save()
        await self.connections.broadcast(
            {"type": "settings", "data": self.config.get_dict()}
        )

    async def _on_load_settings(self, client_id: str, msg: Dict[str, Any]) -> None:
        await self.connections.send(client_id, {
            "type": "settings",
            "data": self.config.get_dict(),
        })

    async def _on_set_active_page(self, client_id: str, msg: Dict[str, Any]) -> None:
        index = msg.get("index", 0)
        self.layout.set_active_page(index)
        await self.connections.broadcast(
            {"type": "active_page", "index": index}
        )
