"""Single virtual Xbox 360 gamepad using vgamepad (ViGEmBus)."""

from __future__ import annotations

import logging
from typing import Dict, Set

import vgamepad as vg

logger = logging.getLogger(__name__)

XUSB_MAP: Dict[str, int] = {
    "gamepad_a": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "gamepad_b": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "gamepad_x": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "gamepad_y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    "gamepad_lb": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "gamepad_rb": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    "gamepad_back": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    "gamepad_start": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    "gamepad_ls": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    "gamepad_rs": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    "gamepad_home": vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
    "gamepad_dpad_up": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    "gamepad_dpad_down": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    "gamepad_dpad_left": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    "gamepad_dpad_right": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
}

_TRIGGER_KEYS = frozenset({"gamepad_lt", "gamepad_rt"})

_ALL_KEYS: Set[str] = set()
_ALL_KEYS.update(XUSB_MAP.keys(), _TRIGGER_KEYS)

_STICK_RANGE = 32767
_TRIGGER_RANGE = 255


class KeyboardController:
    """Single virtual Xbox 360 gamepad for all pages."""

    def __init__(self) -> None:
        self._dev: vg.VX360Gamepad | None = None
        self._pressed: Set[str] = set()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def ensure_controller(self) -> vg.VX360Gamepad:
        if self._dev is None:
            pad = vg.VX360Gamepad()
            pad.reset()
            pad.update()
            self._dev = pad
            logger.info("Created virtual Xbox 360 gamepad")
        return self._dev

    @property
    def controller_count(self) -> int:
        return 1 if self._dev is not None else 0

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def press_key(self, key_name: str) -> bool:
        dev = self._dev
        if dev is None:
            return False
        normalized = key_name.lower().strip()
        if normalized in self._pressed:
            return True
        btn = XUSB_MAP.get(normalized)
        if btn is not None:
            dev.press_button(button=btn)
            dev.update()
            self._pressed.add(normalized)
            logger.info("PRESS %s (btn 0x%04X)", normalized, btn)
            return True
        if normalized in _TRIGGER_KEYS:
            if normalized == "gamepad_lt":
                dev.left_trigger(value=0)
            else:
                dev.right_trigger(value=0)
            dev.update()
            self._pressed.add(normalized)
            return True
        logger.warning("Unknown gamepad input: '%s'", key_name)
        return False

    def release_key(self, key_name: str) -> bool:
        dev = self._dev
        if dev is None:
            return False
        normalized = key_name.lower().strip()
        btn = XUSB_MAP.get(normalized)
        if btn is not None:
            dev.release_button(button=btn)
            dev.update()
            self._pressed.discard(normalized)
            logger.info("RELEASE %s", normalized)
            return True
        if normalized in _TRIGGER_KEYS:
            if normalized == "gamepad_lt":
                dev.left_trigger(value=0)
            else:
                dev.right_trigger(value=0)
            dev.update()
            self._pressed.discard(normalized)
            return True
        logger.warning("Unknown gamepad input: '%s'", key_name)
        return False

    def move_analog(self, stick_name: str, x: float, y: float) -> None:
        dev = self._dev
        if dev is None:
            return
        normalized = stick_name.lower().strip()

        if normalized == "gamepad_lt":
            dev.left_trigger(value=max(0, min(_TRIGGER_RANGE, int(abs(x) * _TRIGGER_RANGE))))
            dev.update()
            return
        if normalized == "gamepad_rt":
            dev.right_trigger(value=max(0, min(_TRIGGER_RANGE, int(abs(x) * _TRIGGER_RANGE))))
            dev.update()
            return
        if normalized == "gamepad_ls":
            dev.left_joystick(
                x_value=int(x * _STICK_RANGE),
                y_value=int(-y * _STICK_RANGE),
            )
            dev.update()
            return
        if normalized == "gamepad_rs":
            dev.right_joystick(
                x_value=int(x * _STICK_RANGE),
                y_value=int(-y * _STICK_RANGE),
            )
            dev.update()
            return

    def release_all(self) -> None:
        dev = self._dev
        if dev is None:
            return
        try:
            dev.reset()
            dev.update()
        except Exception:
            pass
        self._pressed.clear()

    def shutdown(self) -> None:
        self.release_all()
        self._dev = None

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    @property
    def pressed_keys(self) -> Set[str]:
        return self._pressed.copy()

    @staticmethod
    def supported_keys() -> list[str]:
        return sorted(_ALL_KEYS)
