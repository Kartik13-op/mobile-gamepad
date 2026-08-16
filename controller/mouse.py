"""Keyboard & mouse simulation via pyautogui (KBM pipeline).

Gamepad (XInput) simulation keeps using vgamepad / ViGEmBus. This module
handles everything that should reach the real OS: keyboard keys and the
mouse cursor / clicks / scrolling.
"""

from __future__ import annotations

import logging
from typing import Dict

import pyautogui

logger = logging.getLogger(__name__)

# Valid pyautogui key names. UI-facing keys are prefixed with ``key_``.
KEYBOARD_KEYS: list[str] = [
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "space", "enter", "tab", "esc", "backspace", "delete", "insert",
    "home", "end", "pageup", "pagedown",
    "up", "down", "left", "right",
    "shift", "shiftleft", "shiftright", "ctrl", "ctrlleft", "ctrlright",
    "alt", "altleft", "altright", "capslock", "numlock", "scrolllock",
    "printscreen", "pause", "win",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10",
    "f11", "f12", "f13", "f14", "f15", "f16", "f17", "f18", "f19", "f20",
    "f21", "f22", "f23", "f24",
]

# Punctuation uses the literal character as the pyautogui key name.
_PUNCT_MAP: Dict[str, str] = {
    "minus": "-",
    "equals": "=",
    "leftbracket": "[",
    "rightbracket": "]",
    "backslash": "\\",
    "semicolon": ";",
    "apostrophe": "'",
    "grave": "`",
    "comma": ",",
    "period": ".",
    "slash": "/",
}

KEYBOARD_MAP: Dict[str, str] = {f"key_{k}": k for k in KEYBOARD_KEYS}
KEYBOARD_MAP.update({f"key_{name}": ch for name, ch in _PUNCT_MAP.items()})

# Delta cap per move/scroll event (client sends small per-frame deltas).
_MAX_DELTA = 200


class MouseController:
    """pyautogui-backed simulation for keyboard keys and the mouse."""

    def __init__(self) -> None:
        pyautogui.PAUSE = 0.0
        pyautogui.FAILSAFE = False

    # ------------------------------------------------------------------
    # Keyboard keys
    # ------------------------------------------------------------------

    def press_keyboard(self, key_name: str) -> bool:
        """Hold a keyboard key down by its ``key_*`` name."""
        key = KEYBOARD_MAP.get(key_name.lower().strip())
        if key is None:
            logger.warning("Unknown keyboard key: '%s'", key_name)
            return False
        try:
            pyautogui.keyDown(key)
            return True
        except Exception as exc:  # pragma: no cover - OS dependent
            logger.error("pyautogui.keyDown(%r) failed: %s", key, exc)
            return False

    def release_keyboard(self, key_name: str) -> bool:
        """Release a held keyboard key by its ``key_*`` name."""
        key = KEYBOARD_MAP.get(key_name.lower().strip())
        if key is None:
            return False
        try:
            pyautogui.keyUp(key)
            return True
        except Exception as exc:  # pragma: no cover - OS dependent
            logger.error("pyautogui.keyUp(%r) failed: %s", key, exc)
            return False

    def release_all_keyboard(self) -> None:
        """Release every key we may have pressed (safety net)."""
        for key_name in KEYBOARD_MAP:
            self.release_keyboard(key_name)

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

    def handle(self, action: str, msg: Dict[str, object]) -> None:
        """Dispatch a ``mouse`` WebSocket action to the right pyautogui call."""
        action = (action or "").lower()
        dx = self._delta(msg.get("dx"))
        dy = self._delta(msg.get("dy"))

        try:
            if action == "move":
                if dx or dy:
                    pyautogui.moveRel(dx, dy)
            elif action == "scroll":
                if dy:
                    pyautogui.vscroll(int(dy))
                if dx:
                    pyautogui.hscroll(int(dx))
            elif action == "leftclick":
                pyautogui.click(button="left")
            elif action == "rightclick":
                pyautogui.click(button="right")
            elif action == "middledown":
                pyautogui.mouseDown(button="middle")
            elif action == "middleup":
                pyautogui.mouseUp(button="middle")
            else:
                logger.warning("Unknown mouse action: '%s'", action)
        except Exception as exc:  # pragma: no cover - OS dependent
            logger.error("pyautogui %s failed: %s", action, exc)

    @staticmethod
    def _delta(value: object) -> int:
        """Clamp an incoming delta so one event cannot teleport the cursor."""
        try:
            val = int(float(value))
        except (TypeError, ValueError):
            return 0
        return max(-_MAX_DELTA, min(_MAX_DELTA, val))