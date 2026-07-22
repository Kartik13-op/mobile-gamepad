"""TouchKeys Desktop Companion.

A production-ready customtkinter control panel that sits alongside server.py.
It does NOT spin up a second server or duplicate any state — it imports
server.py directly and drives the same FastAPI `app` object (and the same
ConnectionManager / KeyboardController / EventRouter singletons) from a
background thread, so everything shown here reflects exactly what the
mobile clients are doing, in real time.

Place this file next to server.py (same folder) and run:

    python desktop_control.py

Tabs:
  - Server           : start/stop the server, the exact URL to type into a
                        phone's browser (with one-click copy), live status
                        (uptime, client count, active controller), and a log.
  - Devices          : connected phones/tablets, roles, and a Remove action.
  - Controller Test  : live Xbox 360 gamepad diagram at ~60fps with precise
                        numeric readouts for both sticks and both triggers.

Requires:  pip install customtkinter
(plus whatever server.py itself already needs: fastapi, uvicorn, vgamepad, ...)
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
from typing import Optional

import customtkinter as ctk
import uvicorn

# Reuse the real app + singletons defined in server.py — do not re-create them.
import server as touchkeys_server

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

HOST = "0.0.0.0"
PORT = 8000

# Pull the accent color from the app's own settings.json (config.py) so the
# desktop panel visually matches whatever the phone UI is themed with.
try:
    _ACCENT = touchkeys_server.config_manager.get_dict().get("accentColor", "#4a9eff")
except Exception:
    _ACCENT = "#4a9eff"

# -- palette ----------------------------------------------------------------
ACCENT = _ACCENT
COLOR_BG = "#111214"
COLOR_PANEL = "#1a1b1e"
COLOR_CARD = "#212226"
COLOR_CANVAS_BG = "#17181b"
COLOR_IDLE = "#2c2d31"
COLOR_ACTIVE = "#22c55e"
COLOR_OUTLINE = "#43444a"
COLOR_STICK_RING = "#3a3b40"
COLOR_TEXT_DIM = "#9a9ba1"
COLOR_TEXT = "#eaeaec"
COLOR_DANGER = "#ef4444"
COLOR_DANGER_HOVER = "#c0342f"

DIGITAL_BUTTONS = (
    "gamepad_a", "gamepad_b", "gamepad_x", "gamepad_y",
    "gamepad_lb", "gamepad_rb", "gamepad_back", "gamepad_start",
    "gamepad_ls", "gamepad_rs",
    "gamepad_dpad_up", "gamepad_dpad_down", "gamepad_dpad_left", "gamepad_dpad_right",
)

CONTROLLER_FPS_MS = 16   # ~60fps for the live controller test
STATUS_POLL_MS = 250     # server status / devices / log


# ---------------------------------------------------------------------------
# Logging -> GUI textbox bridge
# ---------------------------------------------------------------------------

class QueueLogHandler(logging.Handler):
    """Pushes formatted log records into a thread-safe queue for the GUI to drain."""

    def __init__(self, log_queue: "queue.Queue[tuple[str, int]]") -> None:
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.log_queue.put_nowait((self.format(record), record.levelno))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Background server runner
# ---------------------------------------------------------------------------

class ServerThread:
    """Runs uvicorn serving touchkeys_server.app on its own event loop/thread."""

    def __init__(self, host: str = HOST, port: int = PORT) -> None:
        self.host = host
        self.port = port
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.uvicorn_server: Optional[uvicorn.Server] = None
        self.started_at: Optional[float] = None
        self.last_error: Optional[str] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return (
            self._thread is not None
            and self._thread.is_alive()
            and self.uvicorn_server is not None
            and self.uvicorn_server.started
        )

    @property
    def is_starting(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and not self.is_running

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self.last_error = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        config = uvicorn.Config(
            touchkeys_server.app,
            host=self.host,
            port=self.port,
            log_level="info",
            loop="asyncio",
        )
        self.uvicorn_server = uvicorn.Server(config)
        self.started_at = time.monotonic()
        try:
            self.loop.run_until_complete(self.uvicorn_server.serve())
        except Exception as exc:  # e.g. port already in use
            self.last_error = str(exc)
            logging.getLogger("touchkeys").error("Server failed to start: %s", exc)
        finally:
            self.started_at = None
            self.loop.close()
            self.loop = None
            self.uvicorn_server = None

    def stop(self) -> None:
        if self.uvicorn_server is None:
            return
        self.uvicorn_server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=5)

    def run_coro(self, coro):
        """Schedule a coroutine on the server's own event loop from any thread."""
        if self.loop is None:
            return None
        return asyncio.run_coroutine_threadsafe(coro, self.loop)


# ---------------------------------------------------------------------------
# Small reusable UI atoms
# ---------------------------------------------------------------------------

class StatPill(ctk.CTkFrame):
    """A small labeled stat card, e.g. 'Uptime  →  00:04:12'."""

    def __init__(self, master, title: str, value: str = "—") -> None:
        super().__init__(master, fg_color=COLOR_CARD, corner_radius=10)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=title.upper(), font=("Segoe UI", 10, "bold"),
                     text_color=COLOR_TEXT_DIM).pack(anchor="w", padx=12, pady=(10, 0))
        self.value_label = ctk.CTkLabel(self, text=value, font=("Segoe UI", 16, "bold"),
                                         text_color=COLOR_TEXT)
        self.value_label.pack(anchor="w", padx=12, pady=(0, 10))

    def set(self, value: str) -> None:
        self.value_label.configure(text=value)


class StatusBadge(ctk.CTkFrame):
    """Colored pill: '● Running' / '● Stopped' / '● Starting…'."""

    def __init__(self, master) -> None:
        super().__init__(master, fg_color=COLOR_CARD, corner_radius=14, height=28)
        self.dot = ctk.CTkLabel(self, text="●", text_color=COLOR_TEXT_DIM, font=("Segoe UI", 13))
        self.dot.pack(side="left", padx=(12, 4), pady=4)
        self.text = ctk.CTkLabel(self, text="Stopped", font=("Segoe UI", 12, "bold"))
        self.text.pack(side="left", padx=(0, 12), pady=4)

    def set_state(self, state: str) -> None:
        colors = {
            "running": (COLOR_ACTIVE, "Running"),
            "starting": ("#eab308", "Starting…"),
            "stopped": (COLOR_TEXT_DIM, "Stopped"),
            "error": (COLOR_DANGER, "Error"),
        }
        color, label = colors.get(state, (COLOR_TEXT_DIM, "Stopped"))
        self.dot.configure(text_color=color)
        self.text.configure(text=label)


# ---------------------------------------------------------------------------
# Controller test canvas
# ---------------------------------------------------------------------------

class ControllerCanvas(ctk.CTkCanvas):
    """Draws an Xbox 360 pad and lights up / moves whatever vgamepad reports."""

    STICK_DEADZONE_DISPLAY = 0.0  # display raw values; no cosmetic deadzone

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, width=560, height=340, bg=COLOR_CANVAS_BG,
                          highlightthickness=0, **kwargs)
        self._layout = {
            "gamepad_lb": (60, 46, 160, 74),
            "gamepad_rb": (400, 46, 500, 74),
            "gamepad_back": (250, 160, 13),
            "gamepad_start": (310, 160, 13),
            "gamepad_a": (430, 205, 17),
            "gamepad_b": (468, 160, 17),
            "gamepad_x": (392, 160, 17),
            "gamepad_y": (430, 115, 17),
            "gamepad_ls": (160, 160, 44),
            "gamepad_rs": (430, 270, 44),
        }
        self._lt_bar = (60, 18, 160, 40)
        self._rt_bar = (400, 18, 500, 40)
        self._dpad_center = (160, 270)
        self._last_state: tuple = None
        self.render(pressed=set(), analog={})

    def render(self, pressed: set[str], analog: dict[str, tuple[float, float, float]]) -> None:
        # Skip redraw entirely if nothing changed — keeps things smooth and cheap.
        signature = (
            frozenset(pressed),
            tuple(sorted((k, round(v[0], 4), round(v[1], 4)) for k, v in analog.items())),
        )
        if signature == self._last_state:
            return
        self._last_state = signature

        self.delete("all")
        self.create_rectangle(10, 4, 550, 336, outline=COLOR_OUTLINE, width=2)

        for key, (x1, y1, x2, y2) in (
            ("gamepad_lb", self._layout["gamepad_lb"]),
            ("gamepad_rb", self._layout["gamepad_rb"]),
        ):
            fill = COLOR_ACTIVE if key in pressed else COLOR_IDLE
            self.create_rectangle(x1, y1, x2, y2, fill=fill, outline=COLOR_OUTLINE)
            self.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=key.split("_")[-1].upper(),
                              fill=COLOR_TEXT, font=("Segoe UI", 10, "bold"))

        self._draw_trigger("gamepad_lt", self._lt_bar, analog, pressed)
        self._draw_trigger("gamepad_rt", self._rt_bar, analog, pressed)

        for key in ("gamepad_back", "gamepad_start"):
            cx, cy, r = self._layout[key]
            fill = COLOR_ACTIVE if key in pressed else COLOR_IDLE
            self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline=COLOR_OUTLINE)

        for key, label in (
            ("gamepad_a", "A"), ("gamepad_b", "B"),
            ("gamepad_x", "X"), ("gamepad_y", "Y"),
        ):
            cx, cy, r = self._layout[key]
            fill = COLOR_ACTIVE if key in pressed else COLOR_IDLE
            self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline=COLOR_OUTLINE)
            self.create_text(cx, cy, text=label, fill=COLOR_TEXT, font=("Segoe UI", 13, "bold"))

        self._draw_dpad(pressed)
        self._draw_stick("gamepad_ls", analog, pressed)
        self._draw_stick("gamepad_rs", analog, pressed)

    def _draw_trigger(self, key: str, box, analog, pressed) -> None:
        x1, y1, x2, y2 = box
        self.create_rectangle(x1, y1, x2, y2, outline=COLOR_OUTLINE)
        value = analog.get(key)
        if value is not None:
            frac = max(0.0, min(1.0, abs(value[0])))
        elif key in pressed:
            frac = 1.0
        else:
            frac = 0.0
        if frac > 0:
            fill_x = x1 + (x2 - x1) * frac
            self.create_rectangle(x1, y1, fill_x, y2, fill=ACCENT, outline="")
        self.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=key.split("_")[-1].upper(),
                          fill=COLOR_TEXT, font=("Segoe UI", 9, "bold"))

    def _draw_dpad(self, pressed) -> None:
        cx, cy = self._dpad_center
        arm, thick = 22, 18
        dirs = {
            "gamepad_dpad_up": (cx - thick / 2, cy - arm * 2, cx + thick / 2, cy - thick / 2),
            "gamepad_dpad_down": (cx - thick / 2, cy + thick / 2, cx + thick / 2, cy + arm * 2),
            "gamepad_dpad_left": (cx - arm * 2, cy - thick / 2, cx - thick / 2, cy + thick / 2),
            "gamepad_dpad_right": (cx + thick / 2, cy - thick / 2, cx + arm * 2, cy + thick / 2),
        }
        self.create_rectangle(cx - thick / 2, cy - thick / 2, cx + thick / 2, cy + thick / 2,
                               fill=COLOR_IDLE, outline=COLOR_OUTLINE)
        for key, box in dirs.items():
            fill = COLOR_ACTIVE if key in pressed else COLOR_IDLE
            self.create_rectangle(*box, fill=fill, outline=COLOR_OUTLINE)

    def _draw_stick(self, key: str, analog, pressed) -> None:
        cx, cy, r = self._layout[key]
        self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=COLOR_STICK_RING, width=2)
        # crosshair for a precise visual reference
        self.create_line(cx - r, cy, cx + r, cy, fill=COLOR_STICK_RING, dash=(2, 3))
        self.create_line(cx, cy - r, cx, cy + r, fill=COLOR_STICK_RING, dash=(2, 3))

        x, y = 0.0, 0.0
        value = analog.get(key)
        if value is not None:
            x, y = value[0], value[1]
        # Raw x/y already match screen convention (server negates y before
        # sending to vgamepad specifically to flip it INTO XInput's up-positive
        # axis), so we plot them directly: no extra inversion here.
        dot_x = cx + max(-1.0, min(1.0, x)) * (r - 11)
        dot_y = cy + max(-1.0, min(1.0, y)) * (r - 11)
        dot_r = 9
        dot_fill = ACCENT if key in pressed else "#c9c9cc"
        self.create_oval(dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r,
                          fill=dot_fill, outline="")
        self.create_text(cx, cy + r + 16, text=key.split("_")[-1].upper(),
                          fill=COLOR_TEXT, font=("Segoe UI", 9, "bold"))


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class TouchKeysControlPanel(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TouchKeys Control Panel")
        self.geometry("760x680")
        self.minsize(680, 560)
        self.configure(fg_color=COLOR_BG)

        self.server = ServerThread(HOST, PORT)
        self.log_queue: "queue.Queue[tuple[str, int]]" = queue.Queue()
        self._attach_log_handler()
        self._autoscroll = ctk.BooleanVar(value=True)

        self._device_rows: dict[str, ctk.CTkFrame] = {}

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(STATUS_POLL_MS, self._status_tick)
        self.after(CONTROLLER_FPS_MS, self._controller_tick)

    # -- setup -------------------------------------------------------

    def _attach_log_handler(self) -> None:
        handler = QueueLogHandler(self.log_queue)
        handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s",
                                                 datefmt="%H:%M:%S"))
        logging.getLogger("touchkeys").addHandler(handler)
        logging.getLogger("uvicorn").addHandler(handler)
        logging.getLogger("uvicorn.error").addHandler(handler)
        logging.getLogger("uvicorn.access").addHandler(handler)

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 10))
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="🎮  TouchKeys", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Mobile gamepad server control panel",
                     font=("Segoe UI", 11), text_color=COLOR_TEXT_DIM).pack(anchor="w")

        self.status_badge = StatusBadge(header)
        self.status_badge.pack(side="right", pady=4)
        self.clients_badge = ctk.CTkLabel(header, text="0 devices",
                                           font=("Segoe UI", 12), text_color=COLOR_TEXT_DIM)
        self.clients_badge.pack(side="right", padx=14)

        self.tabs = ctk.CTkTabview(self, fg_color=COLOR_PANEL,
                                    segmented_button_selected_color=ACCENT)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.tabs.add("Server")
        self.tabs.add("Devices")
        self.tabs.add("Controller Test")

        self._build_server_tab(self.tabs.tab("Server"))
        self._build_devices_tab(self.tabs.tab("Devices"))
        self._build_controller_tab(self.tabs.tab("Controller Test"))

    def _build_server_tab(self, tab) -> None:
        # -- connection card -------------------------------------------------
        conn_card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12)
        conn_card.pack(fill="x", pady=(10, 12))

        ctk.CTkLabel(conn_card, text="TYPE THIS ADDRESS INTO YOUR PHONE'S BROWSER",
                     font=("Segoe UI", 10, "bold"), text_color=COLOR_TEXT_DIM).pack(
            anchor="w", padx=18, pady=(16, 2))

        url_row = ctk.CTkFrame(conn_card, fg_color="transparent")
        url_row.pack(fill="x", padx=18, pady=(0, 6))
        self.url_label = ctk.CTkLabel(url_row, text="Server is not running",
                                       font=("Consolas", 22, "bold"), text_color=ACCENT,
                                       anchor="w")
        self.url_label.pack(side="left", fill="x", expand=True)
        self.copy_button = ctk.CTkButton(url_row, text="Copy", width=70, height=30,
                                          fg_color=COLOR_IDLE, hover_color=COLOR_OUTLINE,
                                          command=self._copy_url, state="disabled")
        self.copy_button.pack(side="right")

        ctk.CTkLabel(conn_card, text="Your phone must be connected to the same Wi-Fi network as this computer.",
                     text_color=COLOR_TEXT_DIM, font=("Segoe UI", 11)).pack(
            anchor="w", padx=18, pady=(0, 16))

        # -- start / stop -----------------------------------------------------
        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 12))
        self.start_button = ctk.CTkButton(controls, text="▶  Start Server", width=160, height=38,
                                           fg_color=ACCENT, command=self._on_start_clicked)
        self.start_button.pack(side="left", padx=(0, 10))
        self.stop_button = ctk.CTkButton(controls, text="⏹  Stop Server", width=160, height=38,
                                          fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER,
                                          command=self._on_stop_clicked, state="disabled")
        self.stop_button.pack(side="left")
        self.error_label = ctk.CTkLabel(controls, text="", text_color=COLOR_DANGER,
                                         font=("Segoe UI", 11, "bold"))
        self.error_label.pack(side="left", padx=14)

        # -- status stats ------------------------------------------------------
        stats = ctk.CTkFrame(tab, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 14))
        stats.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="stat")
        self.stat_status = StatPill(stats, "Server")
        self.stat_status.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.stat_uptime = StatPill(stats, "Uptime")
        self.stat_uptime.grid(row=0, column=1, sticky="ew", padx=6)
        self.stat_devices = StatPill(stats, "Devices connected")
        self.stat_devices.grid(row=0, column=2, sticky="ew", padx=6)
        self.stat_active = StatPill(stats, "Active controller")
        self.stat_active.grid(row=0, column=3, sticky="ew", padx=(6, 0))

        # -- log -----------------------------------------------------------
        log_header = ctk.CTkFrame(tab, fg_color="transparent")
        log_header.pack(fill="x")
        ctk.CTkLabel(log_header, text="Server Log", font=("Segoe UI", 13, "bold")).pack(side="left")
        ctk.CTkCheckBox(log_header, text="Autoscroll", variable=self._autoscroll,
                         width=20).pack(side="right")
        ctk.CTkButton(log_header, text="Clear", width=70, height=24, fg_color=COLOR_IDLE,
                      hover_color=COLOR_OUTLINE, command=self._clear_log).pack(side="right", padx=8)

        self.log_box = ctk.CTkTextbox(tab, fg_color=COLOR_CARD, font=("Consolas", 11),
                                       corner_radius=10)
        self.log_box.pack(fill="both", expand=True, pady=(6, 4))
        self.log_box.configure(state="disabled")
        for tag, color in (("INFO", COLOR_TEXT_DIM), ("WARNING", "#eab308"),
                            ("ERROR", COLOR_DANGER), ("CRITICAL", COLOR_DANGER)):
            self.log_box.tag_config(tag, foreground=color)

    def _build_devices_tab(self, tab) -> None:
        header = ctk.CTkFrame(tab, fg_color="transparent")
        header.pack(fill="x", pady=(10, 6))
        self.devices_header_label = ctk.CTkLabel(header, text="Connected devices (0)",
                                                  font=("Segoe UI", 14, "bold"))
        self.devices_header_label.pack(side="left")

        self.devices_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.devices_frame.pack(fill="both", expand=True)
        self.no_devices_label = ctk.CTkLabel(
            self.devices_frame,
            text="No devices connected.\nStart the server, then open the address above on your phone.",
            text_color=COLOR_TEXT_DIM, justify="center")
        self.no_devices_label.pack(pady=40)

    def _build_controller_tab(self, tab) -> None:
        header = ctk.CTkFrame(tab, fg_color="transparent")
        header.pack(fill="x", pady=(10, 6))
        ctk.CTkLabel(header, text="Live Controller Input", font=("Segoe UI", 14, "bold")).pack(side="left")
        self.gamepad_ready_label = ctk.CTkLabel(header, text="● Gamepad not initialized",
                                                 text_color=COLOR_TEXT_DIM, font=("Segoe UI", 11))
        self.gamepad_ready_label.pack(side="right")

        canvas_wrap = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12)
        canvas_wrap.pack(pady=(4, 12))
        self.controller_canvas = ControllerCanvas(canvas_wrap)
        self.controller_canvas.pack(padx=10, pady=10)

        readout = ctk.CTkFrame(tab, fg_color="transparent")
        readout.pack(fill="x")
        readout.grid_columnconfigure((0, 1), weight=1, uniform="ro")

        self.ls_readout = self._make_readout_card(readout, "Left Stick (LS)")
        self.ls_readout["frame"].grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=4)
        self.rs_readout = self._make_readout_card(readout, "Right Stick (RS)")
        self.rs_readout["frame"].grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=4)
        self.lt_readout = self._make_readout_card(readout, "Left Trigger (LT)", single=True)
        self.lt_readout["frame"].grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=4)
        self.rt_readout = self._make_readout_card(readout, "Right Trigger (RT)", single=True)
        self.rt_readout["frame"].grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=4)

        pressed_card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=10)
        pressed_card.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(pressed_card, text="PRESSED BUTTONS", font=("Segoe UI", 10, "bold"),
                     text_color=COLOR_TEXT_DIM).pack(anchor="w", padx=14, pady=(10, 0))
        self.pressed_label = ctk.CTkLabel(pressed_card, text="(none)", font=("Consolas", 13),
                                           anchor="w")
        self.pressed_label.pack(anchor="w", padx=14, pady=(0, 10))

    def _make_readout_card(self, master, title: str, single: bool = False) -> dict:
        frame = ctk.CTkFrame(master, fg_color=COLOR_CARD, corner_radius=10)
        ctk.CTkLabel(frame, text=title.upper(), font=("Segoe UI", 10, "bold"),
                     text_color=COLOR_TEXT_DIM).pack(anchor="w", padx=14, pady=(10, 2))
        if single:
            value = ctk.CTkLabel(frame, text="0 / 255", font=("Consolas", 15, "bold"))
            value.pack(anchor="w", padx=14, pady=(0, 10))
            return {"frame": frame, "value": value}
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(anchor="w", padx=14, pady=(0, 10))
        x_val = ctk.CTkLabel(row, text="X:  0.000", font=("Consolas", 14, "bold"))
        x_val.pack(side="left", padx=(0, 16))
        y_val = ctk.CTkLabel(row, text="Y:  0.000", font=("Consolas", 14, "bold"))
        y_val.pack(side="left")
        return {"frame": frame, "x": x_val, "y": y_val}

    # -- server actions ------------------------------------------------

    def _on_start_clicked(self) -> None:
        self.server.start()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.error_label.configure(text="")

    def _on_stop_clicked(self) -> None:
        self.stop_button.configure(state="disabled")
        threading.Thread(target=self.server.stop, daemon=True).start()

    def _on_close(self) -> None:
        if self.server.is_running or self.server.is_starting:
            self.server.stop()
        self.destroy()

    def _kick_device(self, client_id: str) -> None:
        if self.server.loop is None:
            return
        self.server.run_coro(touchkeys_server.connections.remove_client(client_id))

    def _copy_url(self) -> None:
        if not self.server.is_running:
            return
        ip = touchkeys_server.get_local_ip()
        url = f"http://{ip}:{PORT}"
        self.clipboard_clear()
        self.clipboard_append(url)

    def _clear_log(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # -- polling loops ----------------------------------------------------

    def _status_tick(self) -> None:
        self._drain_logs()
        self._update_status()
        self._update_devices()
        self.after(STATUS_POLL_MS, self._status_tick)

    def _controller_tick(self) -> None:
        self._update_controller()
        self.after(CONTROLLER_FPS_MS, self._controller_tick)

    def _drain_logs(self) -> None:
        drained = False
        while True:
            try:
                line, levelno = self.log_queue.get_nowait()
            except queue.Empty:
                break
            drained = True
            tag = "ERROR" if levelno >= logging.ERROR else (
                "WARNING" if levelno >= logging.WARNING else "INFO")
            self.log_box.configure(state="normal")
            self.log_box.insert("end", line + "\n", tag)
            self.log_box.configure(state="disabled")
        if drained and self._autoscroll.get():
            self.log_box.see("end")

    def _update_status(self) -> None:
        if self.server.is_running:
            state = "running"
            ip = touchkeys_server.get_local_ip()
            url = f"http://{ip}:{PORT}"
            self.url_label.configure(text=url)
            self.copy_button.configure(state="normal")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            uptime = time.monotonic() - (self.server.started_at or time.monotonic())
            self.stat_uptime.set(self._format_uptime(uptime))
        elif self.server.is_starting:
            state = "starting"
            self.url_label.configure(text="Starting…")
            self.copy_button.configure(state="disabled")
            self.stat_uptime.set("—")
        else:
            state = "error" if self.server.last_error else "stopped"
            self.url_label.configure(text="Server is not running")
            self.copy_button.configure(state="disabled")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.stat_uptime.set("—")
            if self.server.last_error:
                self.error_label.configure(text=f"⚠ {self.server.last_error}")

        self.status_badge.set_state(state)
        self.stat_status.set(state.capitalize())

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        seconds = int(seconds)
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _update_devices(self) -> None:
        if not self.server.is_running:
            clients = []
        else:
            try:
                clients = touchkeys_server.connections.get_connections()
            except Exception:
                clients = []

        self.clients_badge.configure(text=f"{len(clients)} device{'s' if len(clients) != 1 else ''}")
        self.devices_header_label.configure(text=f"Connected devices ({len(clients)})")
        self.stat_devices.set(str(len(clients)))
        active = next((c["deviceName"] for c in clients if c["isActive"]), "—")
        self.stat_active.set(active)

        seen_ids = set()
        for client in clients:
            cid = client["clientId"]
            seen_ids.add(cid)
            row = self._device_rows.get(cid)
            if row is None:
                row = self._make_device_row(cid)
                self._device_rows[cid] = row
            self._refresh_device_row(row, client)

        for cid in list(self._device_rows.keys()):
            if cid not in seen_ids:
                self._device_rows.pop(cid).destroy()

        if self._device_rows:
            self.no_devices_label.pack_forget()
        else:
            self.no_devices_label.pack(pady=40)

    def _make_device_row(self, client_id: str) -> ctk.CTkFrame:
        row = ctk.CTkFrame(self.devices_frame, fg_color=COLOR_CARD, corner_radius=10)
        row.pack(fill="x", pady=4)
        row.accent_bar = ctk.CTkFrame(row, width=4, fg_color=COLOR_ACTIVE, corner_radius=0)
        row.accent_bar.pack(side="left", fill="y", padx=(0, 12), pady=8)
        text_box = ctk.CTkFrame(row, fg_color="transparent")
        text_box.pack(side="left", fill="both", expand=True, pady=10)
        row.name_label = ctk.CTkLabel(text_box, text="", font=("Segoe UI", 13, "bold"), anchor="w")
        row.name_label.pack(anchor="w")
        row.sub_label = ctk.CTkLabel(text_box, text="", font=("Consolas", 10),
                                      text_color=COLOR_TEXT_DIM, anchor="w")
        row.sub_label.pack(anchor="w")
        row.badge_label = ctk.CTkLabel(row, text="", font=("Segoe UI", 10, "bold"))
        row.badge_label.pack(side="left", padx=10)
        row.kick_button = ctk.CTkButton(row, text="Remove", width=80, height=28,
                                         fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER,
                                         command=lambda: self._kick_device(client_id))
        row.kick_button.pack(side="right", padx=12, pady=8)
        return row

    def _refresh_device_row(self, row: ctk.CTkFrame, client: dict) -> None:
        row.name_label.configure(text=client["deviceName"])
        row.sub_label.configure(text=f"ID {client['clientId']}")
        if client["isActive"]:
            row.badge_label.configure(text="ACTIVE CONTROLLER", text_color=COLOR_ACTIVE)
            row.accent_bar.configure(fg_color=COLOR_ACTIVE)
        elif not client["canControl"]:
            row.badge_label.configure(text="MONITOR", text_color=COLOR_TEXT_DIM)
            row.accent_bar.configure(fg_color=COLOR_TEXT_DIM)
        else:
            row.badge_label.configure(text="WAITING", text_color="#eab308")
            row.accent_bar.configure(fg_color="#eab308")

    def _update_controller(self) -> None:
        if not self.server.is_running:
            pressed: set[str] = set()
            analog: dict[str, tuple[float, float, float]] = {}
            self.gamepad_ready_label.configure(text="● Gamepad not initialized", text_color=COLOR_TEXT_DIM)
        else:
            try:
                pressed = set(touchkeys_server.keyboard.pressed_keys)
                ready = touchkeys_server.keyboard.controller_count > 0
            except Exception:
                pressed, ready = set(), False
            analog = self._latest_analog_state()
            if ready:
                self.gamepad_ready_label.configure(text="● Virtual Xbox 360 controller ready",
                                                    text_color=COLOR_ACTIVE)
            else:
                self.gamepad_ready_label.configure(text="● Gamepad not initialized",
                                                    text_color=COLOR_TEXT_DIM)

        self.controller_canvas.render(pressed, analog)

        ls = analog.get("gamepad_ls", (0.0, 0.0, 0.0))
        rs = analog.get("gamepad_rs", (0.0, 0.0, 0.0))
        lt = analog.get("gamepad_lt", (0.0, 0.0, 0.0))
        rt = analog.get("gamepad_rt", (0.0, 0.0, 0.0))
        self.ls_readout["x"].configure(text=f"X: {ls[0]:+.3f}")
        self.ls_readout["y"].configure(text=f"Y: {ls[1]:+.3f}")
        self.rs_readout["x"].configure(text=f"X: {rs[0]:+.3f}")
        self.rs_readout["y"].configure(text=f"Y: {rs[1]:+.3f}")
        self.lt_readout["value"].configure(text=f"{round(abs(lt[0]) * 255):3d} / 255")
        self.rt_readout["value"].configure(text=f"{round(abs(rt[0]) * 255):3d} / 255")

        label = ", ".join(sorted(k.split("_")[-1].upper() for k in pressed)) or "(none)"
        self.pressed_label.configure(text=label)

    def _latest_analog_state(self) -> dict[str, tuple[float, float, float]]:
        """Merge per-client analog readings, keeping whichever is most recent per key."""
        latest: dict[str, tuple[float, float, float]] = {}
        try:
            per_client = touchkeys_server.event_router._analog_by_client
        except Exception:
            return latest
        for readings in per_client.values():
            for key, value in readings.items():
                current = latest.get(key)
                if current is None or value[2] > current[2]:
                    latest[key] = value
        return latest


if __name__ == "__main__":
    app = TouchKeysControlPanel()
    app.mainloop()