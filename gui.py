"""TouchKeys Desktop Monitor — customtkinter GUI."""

from __future__ import annotations

import asyncio
import json
import threading
import queue
import urllib.request
import urllib.error
from pathlib import Path

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

WS_URL = "ws://127.0.0.1:8000/ws?role=monitor"
HTTP_URL = "http://127.0.0.1:8000"

try:
    import websockets
except ImportError:
    websockets = None


class TouchKeysMonitor(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TouchKeys Monitor")
        self.geometry("920x680")
        self.minsize(700, 500)

        self.input_queue: queue.Queue = queue.Queue()
        self._ws_stop = threading.Event()
        self._pressed: dict[str, bool] = {}
        self._ls_x = self._ls_y = 0.0
        self._rs_x = self._rs_y = 0.0
        self._lt_val = self._rt_val = 0.0

        self._build_ui()
        self._start_ws()
        self.after(100, self._poll_queues)
        self.after(2000, self._poll_server)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Server status bar
        status_f = ctk.CTkFrame(self, corner_radius=0, height=40)
        status_f.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        status_f.grid_columnconfigure(3, weight=1)

        self._status_lbl = ctk.CTkLabel(status_f, text="● STOPPED", text_color="red", font=("", 13, "bold"))
        self._status_lbl.grid(row=0, column=0, padx=(12, 4), pady=8)

        self._ip_lbl = ctk.CTkLabel(status_f, text="", font=("Consolas", 11))
        self._ip_lbl.grid(row=0, column=1, padx=4)

        self._ctrl_count = ctk.CTkLabel(status_f, text="Controllers: 0", font=("", 11))
        self._ctrl_count.grid(row=0, column=2, padx=12)

        self._refresh_btn = ctk.CTkButton(status_f, text="REFRESH", width=80, height=28, command=self._poll_server)
        self._refresh_btn.grid(row=0, column=4, padx=8, pady=4, sticky="e")

        # Tabview for sections
        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        self._build_input_tab()
        self._build_devices_tab()

    # ------------------------------------------------------------------
    # Input Test Tab
    # ------------------------------------------------------------------

    def _build_input_tab(self) -> None:
        tab = self._tabs.add("Input Test")

        # Analog sticks
        sticks_f = ctk.CTkFrame(tab)
        sticks_f.pack(fill="x", padx=8, pady=8)
        for i, (label, attr) in enumerate([("Left Stick (LS)", "_ls"), ("Right Stick (RS)", "_rs")]):
            f = ctk.CTkFrame(sticks_f)
            f.grid(row=0, column=i, padx=(0, 20) if i == 0 else 0, pady=4)
            ctk.CTkLabel(f, text=label, font=("", 11)).pack()
            c = ctk.CTkCanvas(f, width=130, height=130, bg="#1a1a2e", highlightthickness=0)
            c.pack()
            c.create_line(65, 10, 65, 120, fill="#333355", width=1)
            c.create_line(10, 65, 120, 65, fill="#333355", width=1)
            c.create_oval(60, 60, 70, 70, fill="#555577", outline="")
            dot = c.create_oval(60, 60, 70, 70, fill="#4a9eff", outline="", tags="dot")
            c.dot = dot
            c.center = (65, 65)
            c.radius = 55
            setattr(self, f"{attr}_canvas", c)

            coord = ctk.CTkLabel(sticks_f, text=f"{label[:2]}: 0.00, 0.00", font=("Consolas", 10))
            coord.grid(row=1, column=i, padx=(0, 20) if i == 0 else 0, pady=(0, 4))
            setattr(self, f"{attr}_coord", coord)

        # Triggers
        trig_f = ctk.CTkFrame(tab)
        trig_f.pack(fill="x", padx=8, pady=4)
        for i, label in enumerate(["LT", "RT"]):
            f = ctk.CTkFrame(trig_f)
            f.grid(row=0, column=i, padx=(0, 20) if i == 0 else 0, pady=4)
            ctk.CTkLabel(f, text=label, font=("", 11)).pack()
            c = ctk.CTkCanvas(f, width=130, height=24, bg="#1a1a2e", highlightthickness=0)
            c.pack()
            fill = c.create_rectangle(0, 0, 0, 24, fill="#4a9eff", outline="", tags="fill")
            c.fill_rect = fill
            setattr(self, f"_{label.lower()}_bar", c)

            coord = ctk.CTkLabel(trig_f, text=f"{label}: 0.00", font=("Consolas", 10))
            coord.grid(row=1, column=i, padx=(0, 20) if i == 0 else 0)
            setattr(self, f"_{label.lower()}_coord", coord)

        # Buttons grid
        btn_f = ctk.CTkFrame(tab)
        btn_f.pack(fill="both", expand=True, padx=8, pady=8)
        btn_f.grid_columnconfigure((0, 1, 2), weight=1)

        # ABXY
        abxy = ctk.CTkFrame(btn_f)
        abxy.grid(row=0, column=0, padx=4, pady=4, sticky="n")
        ctk.CTkLabel(abxy, text="ABXY", font=("", 10, "bold")).pack()
        self._btn_y = self._btn_widget(abxy, "Y")
        self._btn_y.pack()
        row = ctk.CTkFrame(abxy)
        row.pack()
        self._btn_x = self._btn_widget(row, "X")
        self._btn_x.pack(side="left", padx=2)
        self._btn_b = self._btn_widget(row, "B")
        self._btn_b.pack(side="left", padx=2)
        self._btn_a = self._btn_widget(abxy, "A")
        self._btn_a.pack()

        # Controls
        ctrl = ctk.CTkFrame(btn_f)
        ctrl.grid(row=0, column=1, padx=4, pady=4, sticky="n")
        ctk.CTkLabel(ctrl, text="Controls", font=("", 10, "bold")).pack()
        self._btn_home = self._btn_widget(ctrl, "HOME")
        self._btn_home.pack(pady=2)
        row = ctk.CTkFrame(ctrl)
        row.pack()
        self._btn_back = self._btn_widget(row, "BACK")
        self._btn_back.pack(side="left", padx=2)
        self._btn_start = self._btn_widget(row, "STAR")
        self._btn_start.pack(side="left", padx=2)
        row2 = ctk.CTkFrame(ctrl)
        row2.pack()
        self._btn_lb = self._btn_widget(row2, "LB")
        self._btn_lb.pack(side="left", padx=2)
        self._btn_rb = self._btn_widget(row2, "RB")
        self._btn_rb.pack(side="left", padx=2)

        # DPad
        dpad = ctk.CTkFrame(btn_f)
        dpad.grid(row=0, column=2, padx=4, pady=4, sticky="n")
        ctk.CTkLabel(dpad, text="DPad", font=("", 10, "bold")).pack()
        self._btn_dup = self._btn_widget(dpad, "▲", 5)
        self._btn_dup.pack()
        row = ctk.CTkFrame(dpad)
        row.pack()
        self._btn_dleft = self._btn_widget(row, "◄", 5)
        self._btn_dleft.pack(side="left", padx=2)
        self._btn_dright = self._btn_widget(row, "►", 5)
        self._btn_dright.pack(side="left", padx=2)
        self._btn_ddown = self._btn_widget(dpad, "▼", 5)
        self._btn_ddown.pack()

    def _btn_widget(self, parent, text, width=6) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            parent, text=text, width=width * 14,
            font=("", 11, "bold"),
            fg_color="#2a2a3e", corner_radius=6,
        )

    # ------------------------------------------------------------------
    # Devices Tab
    # ------------------------------------------------------------------

    def _build_devices_tab(self) -> None:
        tab = self._tabs.add("Devices")

        self._dev_list = ctk.CTkTextbox(tab, font=("Consolas", 11))
        self._dev_list.pack(fill="both", expand=True, padx=8, pady=8)

    def _update_devices(self, clients: list) -> None:
        self._dev_list.delete("0.0", "end")
        if not clients:
            self._dev_list.insert("0.0", "  (No devices connected)\n")
            return
        for i, c in enumerate(clients, 1):
            name = c.get("deviceName") or c.get("clientId", "?")
            cid = c.get("clientId", "")
            status = "ACTIVE" if c.get("isActive") else ("Monitor" if c.get("canControl") is False else "Waiting")
            self._dev_list.insert("end", f"  {i}. {name}  [{status}]\n     {cid}\n\n")

    # ------------------------------------------------------------------
    # Server polling
    # ------------------------------------------------------------------

    def _poll_server(self) -> None:
        try:
            resp = urllib.request.urlopen(f"{HTTP_URL}/api/clients", timeout=2)
            data = json.loads(resp.read())
            self._status_lbl.configure(text="● RUNNING", text_color="#4ade80")
            self._update_devices(data.get("clients", []))
        except Exception:
            self._status_lbl.configure(text="● STOPPED", text_color="red")
            self._ctrl_count.configure(text="Controllers: 0")
        try:
            resp2 = urllib.request.urlopen(f"{HTTP_URL}/api/debug", timeout=2)
            dbg = json.loads(resp2.read())
            self._ctrl_count.configure(text=f"Controllers: {dbg.get('controller_count', 0)}")
        except Exception:
            pass
        try:
            resp3 = urllib.request.urlopen(f"{HTTP_URL}/api/ip", timeout=2)
            ip = json.loads(resp3.read()).get("ip", "")
            self._ip_lbl.configure(text=ip)
        except Exception:
            pass
        self.after(3000, self._poll_server)

    # ------------------------------------------------------------------
    # WebSocket listener
    # ------------------------------------------------------------------

    def _start_ws(self) -> None:
        if websockets is None:
            return
        t = threading.Thread(target=self._ws_run, daemon=True)
        t.start()

    def _ws_run(self) -> None:
        async def _run():
            while not self._ws_stop.is_set():
                try:
                    async with websockets.connect(WS_URL, ping_interval=None) as ws:
                        while not self._ws_stop.is_set():
                            msg = await asyncio.wait_for(ws.recv(), timeout=1)
                            data = json.loads(msg)
                            if data.get("type") == "session":
                                await ws.send(json.dumps({"type": "hello", "deviceName": "Desktop Monitor"}))
                            elif data.get("type") == "input":
                                self.input_queue.put(data)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    if not self._ws_stop.is_set():
                        await asyncio.sleep(2)
        asyncio.run(_run())

    def _poll_queues(self) -> None:
        try:
            while True:
                msg = self.input_queue.get_nowait()
                self._handle_input(msg)
        except queue.Empty:
            pass
        self.after(30, self._poll_queues)

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
                self._ls_coord.configure(text=f"LS: {x:+.2f}, {y:+.2f}")
            elif key == "gamepad_rs":
                self._rs_x, self._rs_y = x, y
                self._update_stick(self._rs_canvas, x, y)
                self._rs_coord.configure(text=f"RS: {x:+.2f}, {y:+.2f}")
            elif key == "gamepad_lt":
                self._lt_val = x
                self._update_trigger(self._lt_bar, x)
                self._lt_coord.configure(text=f"LT: {x:.2f}")
            elif key == "gamepad_rt":
                self._rt_val = x
                self._update_trigger(self._rt_bar, x)
                self._rt_coord.configure(text=f"RT: {x:.2f}")

    def _update_btn(self, key: str, pressed: bool) -> None:
        m = {
            "gamepad_a": self._btn_a, "gamepad_b": self._btn_b,
            "gamepad_x": self._btn_x, "gamepad_y": self._btn_y,
            "gamepad_lb": self._btn_lb, "gamepad_rb": self._btn_rb,
            "gamepad_home": self._btn_home,
            "gamepad_back": self._btn_back, "gamepad_start": self._btn_start,
            "gamepad_dpad_up": self._btn_dup,
            "gamepad_dpad_down": self._btn_ddown,
            "gamepad_dpad_left": self._btn_dleft,
            "gamepad_dpad_right": self._btn_dright,
        }
        w = m.get(key)
        if w:
            w.configure(fg_color="#4a9eff" if pressed else "#2a2a3e")

    def _update_stick(self, c: ctk.CTkCanvas, x: float, y: float) -> None:
        cx, cy = c.center
        r = c.radius
        c.coords("dot", cx + int(x * r) - 5, cy + int(y * r) - 5, cx + int(x * r) + 5, cy + int(y * r) + 5)

    def _update_trigger(self, c: ctk.CTkCanvas, value: float) -> None:
        c.coords(c.fill_rect, 0, 0, int(130 * value), 24)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        self._ws_stop.set()
        self.destroy()


if __name__ == "__main__":
    TouchKeysMonitor().mainloop()
