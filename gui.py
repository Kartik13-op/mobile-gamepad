"""GamePad Monitor — tkinter desktop GUI for server status and live input testing."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import threading
import queue
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error

try:
    import websockets
except ImportError:
    websockets = None

WS_URL = "ws://127.0.0.1:8000/ws"
HTTP_URL = "http://127.0.0.1:8000"


class GamePadMonitor:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("GamePad Monitor")
        self.root.geometry("640x520")
        self.root.resizable(False, False)

        self.input_queue: queue.Queue = queue.Queue()
        self.client_queue: queue.Queue = queue.Queue()

        self._pressed: dict[str, bool] = {}
        self._ls_x = 0.0
        self._ls_y = 0.0
        self._rs_x = 0.0
        self._rs_y = 0.0
        self._lt_value = 0.0
        self._rt_value = 0.0

        self._build_ui()
        self._start_ws()
        self._poll_queues()

    # ------------------------------------------------------------------
    # UI Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=4, pady=4)

        self._build_server_tab(nb)
        self._build_test_tab(nb)

    # ------------------------------------------------------------------
    # Server Tab
    # ------------------------------------------------------------------

    def _build_server_tab(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="Server")

        # Status row
        status_row = ttk.Frame(f)
        status_row.pack(fill="x", pady=(0, 12))
        ttk.Label(status_row, text="Status:", font=("", 10, "bold")).pack(side="left")
        self._status_lbl = ttk.Label(status_row, text="UNKNOWN", foreground="gray")
        self._status_lbl.pack(side="left", padx=8)
        self._refresh_btn = ttk.Button(status_row, text="Refresh", command=self._check_server)
        self._refresh_btn.pack(side="right")

        self._check_server()

        # Devices list
        ttk.Label(f, text="Connected Devices:", font=("", 10, "bold")).pack(anchor="w")
        self._devices_list = tk.Listbox(f, height=6, font=("Consolas", 10))
        self._devices_list.pack(fill="x", pady=6)

        # Server controls
        ctl = ttk.Frame(f)
        ctl.pack(fill="x", pady=(12, 0))
        self._start_srv_btn = ttk.Button(ctl, text="Start Server", command=self._start_server)
        self._start_srv_btn.pack(side="left", padx=(0, 6))
        self._stop_srv_btn = ttk.Button(ctl, text="Stop Server", command=self._stop_server)
        self._stop_srv_btn.pack(side="left")

        self._server_process: Optional[subprocess.Popen] = None

    def _check_server(self) -> None:
        try:
            urllib.request.urlopen(f"{HTTP_URL}/api/clients", timeout=2)
            self._status_lbl.config(text="RUNNING", foreground="green")
        except Exception:
            self._status_lbl.config(text="STOPPED", foreground="red")

    def _poll_clients(self) -> None:
        try:
            resp = urllib.request.urlopen(f"{HTTP_URL}/api/clients", timeout=2)
            data = json.loads(resp.read())
            self._devices_list.delete(0, "end")
            for cid in data.get("clients", []):
                self._devices_list.insert("end", f"  {cid}")
            self._status_lbl.config(text="RUNNING", foreground="green")
        except Exception:
            pass
        self.root.after(3000, self._poll_clients)

    def _start_server(self) -> None:
        if self._server_process is not None and self._server_process.poll() is None:
            return
        base = Path(__file__).resolve().parent
        self._server_process = subprocess.Popen(
            [sys.executable, str(base / "server.py")],
            cwd=str(base),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.root.after(2000, self._check_server)

    def _stop_server(self) -> None:
        if self._server_process is not None:
            self._server_process.terminate()
            self._server_process = None
        self._check_server()

    # ------------------------------------------------------------------
    # Test Tab
    # ------------------------------------------------------------------

    def _build_test_tab(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="Test")

        # Top row: analog sticks
        stick_row = ttk.Frame(f)
        stick_row.pack(fill="x", pady=(0, 10))

        self._ls_canvas = self._make_stick_canvas(stick_row, "Left Stick")
        self._ls_canvas.pack(side="left", padx=(0, 20))
        self._rs_canvas = self._make_stick_canvas(stick_row, "Right Stick")
        self._rs_canvas.pack(side="left")

        self._ls_coords = ttk.Label(f, text="LS: 0.00, 0.00", font=("Consolas", 9))
        self._ls_coords.pack()
        self._rs_coords = ttk.Label(f, text="RS: 0.00, 0.00", font=("Consolas", 9))
        self._rs_coords.pack(pady=(0, 8))

        # Triggers
        trig_row = ttk.Frame(f)
        trig_row.pack(fill="x", pady=(0, 4))
        self._lt_bar = self._make_trigger_bar(trig_row, "LT")
        self._lt_bar.pack(side="left", padx=(0, 20))
        self._rt_bar = self._make_trigger_bar(trig_row, "RT")
        self._rt_bar.pack(side="left")

        trig_label_row = ttk.Frame(f)
        trig_label_row.pack(fill="x", pady=(0, 8))
        self._lt_coords = ttk.Label(trig_label_row, text="LT: 0.00", font=("Consolas", 9), width=14, anchor="w")
        self._lt_coords.pack(side="left", padx=(0, 20))
        self._rt_coords = ttk.Label(trig_label_row, text="RT: 0.00", font=("Consolas", 9), width=14, anchor="w")
        self._rt_coords.pack(side="left")

        # Bumpers
        bump_row = ttk.Frame(f)
        bump_row.pack(fill="x", pady=(0, 10))
        self._lb_lbl = self._make_btn_indicator(bump_row, "LB")
        self._lb_lbl.pack(side="left", padx=(0, 10))
        self._rb_lbl = self._make_btn_indicator(bump_row, "RB")
        self._rb_lbl.pack(side="left")

        # ABXY
        abxy_row = ttk.Frame(f)
        abxy_row.pack(fill="x", pady=(0, 10))

        abxy_inner = ttk.Frame(abxy_row)
        abxy_inner.pack(side="left", padx=(0, 30))

        y_row = ttk.Frame(abxy_inner)
        y_row.pack()
        self._y_lbl = self._make_btn_indicator(y_row, "Y")
        self._y_lbl.pack(side="left", padx=2)

        xb_row = ttk.Frame(abxy_inner)
        xb_row.pack()
        self._x_lbl = self._make_btn_indicator(xb_row, "X")
        self._x_lbl.pack(side="left", padx=2)
        self._b_lbl = self._make_btn_indicator(xb_row, "B")
        self._b_lbl.pack(side="left", padx=2)

        a_row = ttk.Frame(abxy_inner)
        a_row.pack()
        self._a_lbl = self._make_btn_indicator(a_row, "A")
        self._a_lbl.pack(side="left", padx=2)

        # HOME / BACK / START
        ctrl_row = ttk.Frame(abxy_row)
        ctrl_row.pack(side="left", padx=10)
        self._home_lbl = self._make_btn_indicator(ctrl_row, "HOME")
        self._home_lbl.pack(pady=2)
        bs_row = ttk.Frame(ctrl_row)
        bs_row.pack()
        self._back_lbl = self._make_btn_indicator(bs_row, "BACK")
        self._back_lbl.pack(side="left", padx=2)
        self._start_lbl = self._make_btn_indicator(bs_row, "START")
        self._start_lbl.pack(side="left", padx=2)

        # DPAD
        dpad_row = ttk.Frame(f)
        dpad_row.pack()
        dpad_inner = ttk.Frame(dpad_row)
        dpad_inner.pack()

        ttk.Frame(dpad_inner, height=2).pack()
        dup_row = ttk.Frame(dpad_inner)
        dup_row.pack()
        self._dpad_up = self._make_btn_indicator(dup_row, "▲")
        self._dpad_up.pack()

        dmid = ttk.Frame(dpad_inner)
        dmid.pack()
        self._dpad_left = self._make_btn_indicator(dmid, "◄")
        self._dpad_left.pack(side="left", padx=2)
        self._dpad_right = self._make_btn_indicator(dmid, "►")
        self._dpad_right.pack(side="left", padx=2)

        ddown_row = ttk.Frame(dpad_inner)
        ddown_row.pack()
        self._dpad_down = self._make_btn_indicator(ddown_row, "▼")
        self._dpad_down.pack()

    def _make_stick_canvas(self, parent: ttk.Frame, label: str) -> ttk.Frame:
        f = ttk.Frame(parent)
        ttk.Label(f, text=label, font=("", 9)).pack()
        c = tk.Canvas(f, width=120, height=120, bg="#f0f0f0",
                      highlightthickness=1, highlightbackground="#ccc")
        c.pack()
        # Crosshair
        c.create_line(60, 10, 60, 110, fill="#ccc", width=1)
        c.create_line(10, 60, 110, 60, fill="#ccc", width=1)
        c.create_oval(55, 55, 65, 65, fill="#aaa", outline="")
        # Dot
        dot = c.create_oval(55, 55, 65, 65, fill="#333", outline="", tags="dot")
        c.dot = dot
        c.center = (60, 60)
        c.radius = 50
        c.dot_x = 0.0
        c.dot_y = 0.0
        return f

    def _make_trigger_bar(self, parent: ttk.Frame, label: str) -> ttk.Frame:
        f = ttk.Frame(parent)
        ttk.Label(f, text=label, font=("", 9)).pack()
        c = tk.Canvas(f, width=120, height=24, bg="#f0f0f0",
                      highlightthickness=1, highlightbackground="#ccc")
        c.pack()
        fill = c.create_rectangle(0, 0, 0, 24, fill="#666", outline="", tags="fill")
        c.fill_rect = fill
        c.trigger_value = 0.0
        return f

    def _make_btn_indicator(self, parent: ttk.Frame, text: str) -> ttk.Label:
        lbl = ttk.Label(parent, text=text, width=6, anchor="center",
                        font=("", 9, "bold"), relief="raised", padding=4)
        lbl._pressed = False
        return lbl

    # ------------------------------------------------------------------
    # WebSocket Client
    # ------------------------------------------------------------------

    def _start_ws(self) -> None:
        self._ws_stop = threading.Event()
        t = threading.Thread(target=self._ws_run, daemon=True)
        t.start()
        self.root.after(3000, self._poll_clients)

    def _ws_run(self) -> None:
        if websockets is None:
            return
        async def _run():
            while not self._ws_stop.is_set():
                try:
                    async with websockets.connect(WS_URL, ping_interval=None) as ws:
                        while not self._ws_stop.is_set():
                            msg = await asyncio.wait_for(ws.recv(), timeout=1)
                            data = json.loads(msg)
                            if data.get("type") == "input":
                                self.input_queue.put(data)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    if not self._ws_stop.is_set():
                        await asyncio.sleep(2)
        asyncio.run(_run())

    # ------------------------------------------------------------------
    # Queue Polling
    # ------------------------------------------------------------------

    def _poll_queues(self) -> None:
        try:
            while True:
                msg = self.input_queue.get_nowait()
                self._handle_input(msg)
        except queue.Empty:
            pass
        self.root.after(30, self._poll_queues)

    def _handle_input(self, msg: dict) -> None:
        sub = msg.get("subtype", "")
        key = msg.get("key", "")

        if sub == "keydown":
            self._pressed[key] = True
            self._update_btn(key, True)
        elif sub == "keyup":
            self._pressed[key] = False
            self._update_btn(key, False)
        elif sub == "analog":
            x = msg.get("x", 0)
            y = msg.get("y", 0)
            if key == "gamepad_ls":
                self._ls_x, self._ls_y = x, y
                self._update_stick(self._ls_canvas, x, y)
                self._ls_coords.config(text=f"LS: {x:+.2f}, {y:+.2f}")
            elif key == "gamepad_rs":
                self._rs_x, self._rs_y = x, y
                self._update_stick(self._rs_canvas, x, y)
                self._rs_coords.config(text=f"RS: {x:+.2f}, {y:+.2f}")
            elif key == "gamepad_lt":
                self._lt_value = x
                self._update_trigger(self._lt_bar, x)
                self._lt_coords.config(text=f"LT: {x:.2f}")
            elif key == "gamepad_rt":
                self._rt_value = x
                self._update_trigger(self._rt_bar, x)
                self._rt_coords.config(text=f"RT: {x:.2f}")

    def _update_btn(self, key: str, pressed: bool) -> None:
        mapping = {
            "gamepad_a": self._a_lbl, "gamepad_b": self._b_lbl,
            "gamepad_x": self._x_lbl, "gamepad_y": self._y_lbl,
            "gamepad_lb": self._lb_lbl, "gamepad_rb": self._rb_lbl,
            "gamepad_lt": self._lt_bar, "gamepad_rt": self._rt_bar,
            "gamepad_home": self._home_lbl,
            "gamepad_back": self._back_lbl, "gamepad_start": self._start_lbl,
            "gamepad_dpad_up": self._dpad_up,
            "gamepad_dpad_down": self._dpad_down,
            "gamepad_dpad_left": self._dpad_left,
            "gamepad_dpad_right": self._dpad_right,
        }
        widget = mapping.get(key)
        if widget is None:
            return

        if key in ("gamepad_lt", "gamepad_rt"):
            self._update_trigger(widget, 1.0 if pressed else 0.0)
        elif isinstance(widget, ttk.Label):
            if pressed:
                widget.config(relief="sunken", background="#333", foreground="#fff")
            else:
                widget.config(relief="raised", background=self._default_bg(widget), foreground="#000")
            widget._pressed = pressed

    def _default_bg(self, widget: ttk.Label) -> str:
        try:
            return widget.tk.call("ttk::style", "lookup", widget.winfo_class(), "-background")
        except Exception:
            return "#f0f0f0"

    def _update_stick(self, frame: ttk.Frame, x: float, y: float) -> None:
        c = frame.winfo_children()[1]
        cx, cy = c.center
        r = c.radius
        dx = int(x * r)
        dy = int(y * r)
        c.coords("dot", cx + dx - 5, cy + dy - 5, cx + dx + 5, cy + dy + 5)

    def _update_trigger(self, frame: ttk.Frame, value: float) -> None:
        c = frame.winfo_children()[1]
        w = int(120 * value)
        c.coords(c.fill_rect, 0, 0, w, 24)
        c.trigger_value = value
        if value > 0:
            c.itemconfig(c.fill_rect, fill="#333")
        else:
            c.itemconfig(c.fill_rect, fill="#666")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def on_close(self) -> None:
        self._ws_stop.set()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = GamePadMonitor(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
