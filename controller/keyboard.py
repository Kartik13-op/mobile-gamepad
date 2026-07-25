"""Multiple virtual Xbox 360 gamepads using vgamepad (ViGEmBus)."""

from __future__ import annotations

import logging
from typing import Dict, Optional, Set

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

MAX_SLOTS = 4


class KeyboardController:
    """Multiple virtual Xbox 360 gamepads (up to 4 slots)."""

    def __init__(self) -> None:
        self._devs: Dict[int, vg.VX360Gamepad] = {}
        self._pressed: Dict[int, Set[str]] = {}

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def ensure_controller(self, slot: int) -> vg.VX360Gamepad:
        if slot not in self._devs:
            pad = vg.VX360Gamepad()
            pad.reset()
            pad.update()
            self._devs[slot] = pad
            self._pressed[slot] = set()
            logger.info("Created virtual Xbox 360 gamepad for slot %d", slot)
        return self._devs[slot]

    def free_slot(self, slot: int) -> None:
        """Release and remove a gamepad for a specific slot."""
        dev = self._devs.pop(slot, None)
        self._pressed.pop(slot, None)
        if dev is not None:
            try:
                dev.reset()
                dev.update()
            except Exception:
                pass
            logger.info("Freed gamepad slot %d", slot)

    @property
    def controller_count(self) -> int:
        return len(self._devs)

    def allocated_slots(self) -> Set[int]:
        return set(self._devs.keys())

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def press_key(self, slot: int, key_name: str) -> bool:
        dev = self._devs.get(slot)
        if dev is None:
            return False
        normalized = key_name.lower().strip()
        pressed = self._pressed[slot]
        if normalized in pressed:
            return True
        btn = XUSB_MAP.get(normalized)
        if btn is not None:
            dev.press_button(button=btn)
            dev.update()
            pressed.add(normalized)
            logger.info("[Slot %d] PRESS %s (btn 0x%04X)", slot, normalized, btn)
            return True
        if normalized in _TRIGGER_KEYS:
            if normalized == "gamepad_lt":
                dev.left_trigger(value=_TRIGGER_RANGE)
            else:
                dev.right_trigger(value=_TRIGGER_RANGE)
            dev.update()
            pressed.add(normalized)
            return True
        logger.warning("Unknown gamepad input: '%s'", key_name)
        return False

    def release_key(self, slot: int, key_name: str) -> bool:
        dev = self._devs.get(slot)
        if dev is None:
            return False
        normalized = key_name.lower().strip()
        pressed = self._pressed[slot]
        btn = XUSB_MAP.get(normalized)
        if btn is not None:
            dev.release_button(button=btn)
            dev.update()
            pressed.discard(normalized)
            logger.info("[Slot %d] RELEASE %s", slot, normalized)
            return True
        if normalized in _TRIGGER_KEYS:
            if normalized == "gamepad_lt":
                dev.left_trigger(value=0)
            else:
                dev.right_trigger(value=0)
            dev.update()
            pressed.discard(normalized)
            return True
        logger.warning("Unknown gamepad input: '%s'", key_name)
        return False

    def move_analog(self, slot: int, stick_name: str, x: float, y: float) -> None:
        dev = self._devs.get(slot)
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

    def release_all(self, slot: Optional[int] = None) -> None:
        if slot is not None:
            dev = self._devs.get(slot)
            if dev is not None:
                try:
                    dev.reset()
                    dev.update()
                except Exception:
                    pass
                self._pressed[slot].clear()
            return
        for s, dev in self._devs.items():
            try:
                dev.reset()
                dev.update()
            except Exception:
                pass
            self._pressed[s].clear()

    def shutdown(self) -> None:
        for slot in list(self._devs.keys()):
            self.free_slot(slot)

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def pressed_keys(self, slot: Optional[int] = None) -> Set[str]:
        if slot is not None:
            return self._pressed.get(slot, set()).copy()
        result: Set[str] = set()
        for s in self._pressed.values():
            result.update(s)
        return result

    @staticmethod
    def supported_keys() -> list[str]:
        return sorted(_ALL_KEYS)
