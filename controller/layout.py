"""Layout management with undo/redo and full CRUD for pages and buttons."""

from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Optional

from controller.utils import generate_id
from controller.storage import StorageManager

logger = logging.getLogger(__name__)

LAYOUT_FILE = "layout.json"

DEFAULT_CONTROL: Dict[str, Any] = {
    "id": "",
    "name": "Button",
    "type": "button",
    "keybind": "",
    "x": 0.5,
    "y": 0.5,
    "width": 60,
    "height": 60,
    "opacity": 1.0,
    "fontSize": 16,
    "layer": 0,
    "visible": True,
}


class LayoutManager:
    """Manages the full layout state including pages, buttons, and history."""

    MAX_HISTORY: int = 50

    def __init__(self, storage: StorageManager) -> None:
        self.storage = storage
        self._layout: Dict[str, Any] = self._load()
        self._history: List[Dict[str, Any]] = []
        self._redo_stack: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> Dict[str, Any]:
        """Load layout from disk or return minimal defaults."""
        data = self.storage.read_json(LAYOUT_FILE)
        if data and self.validate_layout(data):
            return data
        return self._default_layout()

    @classmethod
    def _default_layout(cls) -> Dict[str, Any]:
        template = cls._load_default_controls_static()
        return {
            "version": "2.0",
            "activePageIndex": 0,
            "pages": [
                {"id": generate_id(), "name": "Gamepad", "buttons": template}
            ],
        }

    def save(self) -> bool:
        """Persist the current layout to disk."""
        return self.storage.write_json(LAYOUT_FILE, self._layout)

    # ------------------------------------------------------------------
    # History (undo / redo)
    # ------------------------------------------------------------------

    def _push_history(self) -> None:
        """Snapshot the current layout before a mutation."""
        if len(self._history) >= self.MAX_HISTORY:
            self._history.pop(0)
        self._history.append(copy.deepcopy(self._layout))
        self._redo_stack.clear()

    def undo(self) -> Optional[Dict[str, Any]]:
        """Revert to the previous layout state."""
        if not self._history:
            return None
        self._redo_stack.append(copy.deepcopy(self._layout))
        self._layout = self._history.pop()
        return self.get_layout()

    def redo(self) -> Optional[Dict[str, Any]]:
        """Re-apply the last undone change."""
        if not self._redo_stack:
            return None
        self._history.append(copy.deepcopy(self._layout))
        self._layout = self._redo_stack.pop()
        return self.get_layout()

    # ------------------------------------------------------------------
    # Layout getters / setters
    # ------------------------------------------------------------------

    def get_layout(self) -> Dict[str, Any]:
        """Return a deep copy of the current layout."""
        return copy.deepcopy(self._layout)

    def set_layout(self, data: Dict[str, Any]) -> None:
        """Replace the entire layout (with history snapshot)."""
        self._push_history()
        self._layout = copy.deepcopy(data)

    # ------------------------------------------------------------------
    # Page helpers
    # ------------------------------------------------------------------

    def _find_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        for page in self._layout.get("pages", []):
            if page["id"] == page_id:
                return page
        return None

    def add_page(self, name: str) -> Dict[str, Any]:
        """Create a new page initialized with controls from default_gamepad.json."""
        self._push_history()
        template = self._load_default_controls()
        page: Dict[str, Any] = {
            "id": generate_id(),
            "name": name,
            "buttons": template,
        }
        self._layout["pages"].append(page)
        return page

    @staticmethod
    def _load_default_controls_static() -> list[Dict[str, Any]]:
        import json
        from pathlib import Path
        path = Path(__file__).parent / "default_gamepad.json"
        if path.exists():
            try:
                controls = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(controls, list):
                    for ctrl in controls:
                        ctrl["id"] = generate_id()
                    return controls
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def _load_default_controls(self) -> list[Dict[str, Any]]:
        return self._load_default_controls_static()

    def delete_page(self, page_id: str) -> bool:
        """Delete a page by ID. At least one page must remain."""
        pages = self._layout.get("pages", [])
        if len(pages) <= 1:
            return False
        self._push_history()
        self._layout["pages"] = [p for p in pages if p["id"] != page_id]
        if self._layout["activePageIndex"] >= len(self._layout["pages"]):
            self._layout["activePageIndex"] = len(self._layout["pages"]) - 1
        return True

    def rename_page(self, page_id: str, name: str) -> bool:
        """Rename an existing page."""
        page = self._find_page(page_id)
        if page is None:
            return False
        page["name"] = name
        return True

    def get_active_page_id(self) -> str | None:
        pages = self._layout.get("pages", [])
        idx = self._layout.get("activePageIndex", 0)
        if pages and 0 <= idx < len(pages):
            return pages[idx].get("id")
        return None

    def set_active_page(self, index: int) -> None:
        """Switch the active page by index."""
        pages = self._layout.get("pages", [])
        if 0 <= index < len(pages):
            self._layout["activePageIndex"] = index

    # ------------------------------------------------------------------
    # Button/Control CRUD
    # ------------------------------------------------------------------

    def add_button(
        self, page_id: str, button_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Add a control to the specified page. Returns the new control or None."""
        page = self._find_page(page_id)
        if page is None:
            return None
        self._push_history()
        control = {**DEFAULT_CONTROL, **button_data, "id": generate_id()}
        page["buttons"].append(control)
        return control

    def update_button(
        self, page_id: str, button_id: str, updates: Dict[str, Any]
    ) -> bool:
        """Merge partial updates into an existing control."""
        page = self._find_page(page_id)
        if page is None:
            return False
        for btn in page["buttons"]:
            if btn["id"] == button_id:
                self._push_history()
                btn.update(updates)
                return True
        return False

    def delete_button(self, page_id: str, button_id: str) -> bool:
        """Remove a control from a page."""
        page = self._find_page(page_id)
        if page is None:
            return False
        original_len = len(page["buttons"])
        page["buttons"] = [b for b in page["buttons"] if b["id"] != button_id]
        if len(page["buttons"]) < original_len:
            self._push_history()
            return True
        return False

    def duplicate_button(
        self, page_id: str, button_id: str
    ) -> Optional[Dict[str, Any]]:
        """Clone a control with an offset and return the copy."""
        page = self._find_page(page_id)
        if page is None:
            return None
        for btn in page["buttons"]:
            if btn["id"] == button_id:
                self._push_history()
                clone = copy.deepcopy(btn)
                clone["id"] = generate_id()
                clone["x"] += 20
                clone["y"] += 20
                clone["name"] = f"{btn['name']} copy"
                page["buttons"].append(clone)
                return clone
        return None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_layout(data: Any) -> bool:
        """Return True if *data* looks like a valid layout structure."""
        if not isinstance(data, dict):
            return False
        pages = data.get("pages")
        if not isinstance(pages, list):
            return False
        for page in pages:
            if not isinstance(page, dict):
                return False
            if "id" not in page or "name" not in page:
                return False
            buttons = page.get("buttons")
            if not isinstance(buttons, list):
                return False
        return True
