"""Keyboard simulation using pynput with thread-safe key tracking.
Also handles analog stick data (mouse movement)."""

from __future__ import annotations

import math
import threading
import logging
from typing import Dict, Optional, Set

from pynput.keyboard import Controller as PynputController, Key, KeyCode
from pynput.mouse import Controller as MouseController

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Key name → pynput object mapping
# ---------------------------------------------------------------------------

KEY_MAP: Dict[str, object] = {}

# Letters a–z
for _ch in "abcdefghijklmnopqrstuvwxyz":
    KEY_MAP[_ch] = KeyCode.from_char(_ch)

# Digits 0–9
for _dg in "0123456789":
    KEY_MAP[_dg] = KeyCode.from_char(_dg)

# Gamepad button aliases → keyboard keys
_GAMEPAD_MAP: Dict[str, str] = {
    "gamepad_a": "enter",
    "gamepad_b": "escape",
    "gamepad_x": "space",
    "gamepad_y": "tab",
    "gamepad_lb": "shift",
    "gamepad_rb": "ctrl",
    "gamepad_lt": "q",
    "gamepad_rt": "e",
    "gamepad_dpad_up": "up",
    "gamepad_dpad_down": "down",
    "gamepad_dpad_left": "left",
    "gamepad_dpad_right": "right",
    "gamepad_home": "esc",
    "gamepad_back": "backspace",
    "gamepad_start": "enter",
    "gamepad_ls": "shift",
    "gamepad_rs": "ctrl",
}

# Special / modifier keys
_SPECIAL_KEYS: Dict[str, Key] = {
    "shift": Key.shift,
    "lshift": Key.shift,
    "rshift": Key.shift_r,
    "ctrl": Key.ctrl,
    "control": Key.ctrl,
    "lctrl": Key.ctrl,
    "rctrl": Key.ctrl_r,
    "alt": Key.alt,
    "lalt": Key.alt,
    "ralt": Key.alt_r,
    "space": Key.space,
    "tab": Key.tab,
    "enter": Key.enter,
    "return": Key.enter,
    "escape": Key.esc,
    "esc": Key.esc,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "del": Key.delete,
    "insert": Key.insert,
    "ins": Key.insert,
    "home": Key.home,
    "end": Key.end,
    "pageup": Key.page_up,
    "page_up": Key.page_up,
    "pagedown": Key.page_down,
    "page_down": Key.page_down,
    "capslock": Key.caps_lock,
    "caps_lock": Key.caps_lock,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "win": Key.cmd,
    "windows": Key.cmd,
    "cmd": Key.cmd,
    "super": Key.cmd,
    "menu": Key.menu,
    "printscreen": Key.print_screen,
    "scrolllock": Key.scroll_lock,
    "pause": Key.pause,
    "numlock": Key.num_lock,
}

# Function keys F1–F24
for _i in range(1, 25):
    _fkey = getattr(Key, f"f{_i}", None)
    if _fkey is not None:
        _SPECIAL_KEYS[f"f{_i}"] = _fkey

KEY_MAP.update(_SPECIAL_KEYS)

# Numpad keys
_NUMPAD_VK: Dict[str, int] = {
    "numpad0": 0x60,
    "numpad1": 0x61,
    "numpad2": 0x62,
    "numpad3": 0x63,
    "numpad4": 0x64,
    "numpad5": 0x65,
    "numpad6": 0x66,
    "numpad7": 0x67,
    "numpad8": 0x68,
    "numpad9": 0x69,
    "numpadadd": 0x6B,
    "numpadsubtract": 0x6D,
    "numpadmultiply": 0x6A,
    "numpaddivide": 0x6F,
    "numpaddecimal": 0x6E,
    "numpadenter": 0x0D,
}

for _name, _vk in _NUMPAD_VK.items():
    KEY_MAP[_name] = KeyCode.from_vk(_vk)

# Common symbol keys
_SYMBOLS: Dict[str, KeyCode] = {
    "-": KeyCode.from_char("-"),
    "=": KeyCode.from_char("="),
    "[": KeyCode.from_char("["),
    "]": KeyCode.from_char("]"),
    "\\": KeyCode.from_char("\\"),
    ";": KeyCode.from_char(";"),
    "'": KeyCode.from_char("'"),
    ",": KeyCode.from_char(","),
    ".": KeyCode.from_char("."),
    "/": KeyCode.from_char("/"),
    "`": KeyCode.from_char("`"),
}
KEY_MAP.update(_SYMBOLS)

# Add gamepad aliases as KeyCode references to their mapped keys
for _gp_name, _mapped_key in _GAMEPAD_MAP.items():
    if _mapped_key in KEY_MAP:
        KEY_MAP[_gp_name] = KEY_MAP[_mapped_key]


class AnalogState:
    """Per-stick state for EMA smoothing, sub-pixel accumulation, and acceleration."""

    __slots__ = ("smooth_x", "smooth_y", "accum_x", "accum_y")

    def __init__(self) -> None:
        self.smooth_x = 0.0
        self.smooth_y = 0.0
        self.accum_x = 0.0
        self.accum_y = 0.0


class KeyboardController:
    """Thread-safe keyboard simulator wrapping pynput.
    Also handles analog stick → mouse movement with smoothing and acceleration.
    """

    # EMA smoothing factor (0=no smoothing, 1=instant). 0.35 balances responsiveness vs jitter.
    EMA_ALPHA = 0.35
    # Power-curve exponent — values < 1 amplify large deflections for quick turns.
    CURVE_EXP = 0.65
    # Pixels per second at full deflection (scaled by frame-like increments).
    SENSITIVITY = 15.0
    # Safety dead zone — ignore values below this.
    SAFE_DEAD_ZONE = 0.02

    def __init__(self) -> None:
        self._controller = PynputController()
        self._mouse = MouseController()
        self._pressed: Set[str] = set()
        self._lock = threading.Lock()
        self._analog_states: Dict[str, AnalogState] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve(key_name: str) -> Optional[object]:
        """Map a human-readable key name to a pynput key object."""
        normalized = key_name.lower().strip()
        mapped = KEY_MAP.get(normalized)
        if mapped is not None:
            return mapped
        if len(normalized) == 1:
            return KeyCode.from_char(normalized)
        logger.warning("Unknown key name: '%s'", key_name)
        return None

    @staticmethod
    def _apply_curve(value: float, exponent: float) -> float:
        """Apply a power curve preserving sign."""
        return math.copysign(abs(value) ** exponent, value) if abs(value) > 1e-9 else 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def press_key(self, key_name: str) -> bool:
        """Simulate a key-down event. Returns True on success."""
        key = self._resolve(key_name)
        if key is None:
            return False
        normalized = key_name.lower().strip()
        with self._lock:
            if normalized in self._pressed:
                return True
            try:
                self._controller.press(key)
                self._pressed.add(normalized)
                return True
            except Exception as exc:
                logger.error("press_key('%s') failed: %s", key_name, exc)
                return False

    def release_key(self, key_name: str) -> bool:
        """Simulate a key-up event. Returns True on success."""
        key = self._resolve(key_name)
        if key is None:
            return False
        normalized = key_name.lower().strip()
        with self._lock:
            try:
                self._controller.release(key)
                self._pressed.discard(normalized)
                return True
            except Exception as exc:
                logger.error("release_key('%s') failed: %s", key_name, exc)
                return False

    def release_all(self) -> None:
        """Release every key that is currently held."""
        with self._lock:
            for name in list(self._pressed):
                key = self._resolve(name)
                if key is not None:
                    try:
                        self._controller.release(key)
                    except Exception:
                        pass
            self._pressed.clear()
        self._analog_states.clear()

    def move_analog(self, stick_name: str, x: float, y: float) -> None:
        """Move mouse based on analog stick input with smoothing and acceleration."""
        # Safety dead zone
        mag = math.sqrt(x * x + y * y)
        if mag < self.SAFE_DEAD_ZONE:
            x = y = 0.0

        # Get or create per-stick state
        if stick_name not in self._analog_states:
            self._analog_states[stick_name] = AnalogState()
        state = self._analog_states[stick_name]

        # EMA smoothing
        a = self.EMA_ALPHA
        state.smooth_x += a * (x - state.smooth_x)
        state.smooth_y += a * (y - state.smooth_y)

        # Power-curve acceleration
        cx = self._apply_curve(state.smooth_x, self.CURVE_EXP)
        cy = self._apply_curve(state.smooth_y, self.CURVE_EXP)

        # Sub-pixel accumulation
        state.accum_x += cx * self.SENSITIVITY
        state.accum_y += cy * self.SENSITIVITY

        dx = int(state.accum_x)
        dy = int(state.accum_y)
        state.accum_x -= dx
        state.accum_y -= dy

        if dx != 0 or dy != 0:
            self._mouse.move(dx, dy)

    @property
    def pressed_keys(self) -> Set[str]:
        """Snapshot of currently-held key names."""
        with self._lock:
            return self._pressed.copy()

    @staticmethod
    def supported_keys() -> list[str]:
        """Return a sorted list of all recognised key names."""
        return sorted(KEY_MAP.keys())
