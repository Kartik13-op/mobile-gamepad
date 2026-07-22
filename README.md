# TouchKeys

Turn any phone or tablet into a **virtual Xbox 360 gamepad** for your PC. Zero installation on the phone — just open a URL in the browser. Fully customizable controls, dual analog sticks, analog triggers, and multi-touch support.

---

## Features

- **Xbox 360 controller emulation** — single virtual controller via `vgamepad` + ViGEmBus; games see a real gamepad
- **All standard buttons** — A, B, X, Y, D-pad, LB/RB, LT/RT, LS/RS, BACK, START, HOME
- **Analog triggers** — touch and drag for smooth 0–1 analog input
- **Dual analog sticks** — dead-zone filtering, 16ms throttle, change-threshold filtering
- **Multi-touch** — press any combination of buttons while moving both sticks simultaneously
- **Low latency** — WebSocket transport with 16ms input throttle
- **Haptic feedback** — vibration on button press (supported devices)
- **Auto-reconnect** — WebSocket reconnects with exponential backoff
- **Single-page app** — everything in one HTML file, zero external dependencies at runtime
- **PWA ready** — add to home screen for fullscreen playback
- **Layout persistence** — layouts are saved to `layout.json` on the server
- **Desktop monitor** — live input visualization at `/monitor` or via `gui.py`

---

## Quick Start

### Prerequisites

- **Windows 10/11** (requires ViGEmBus driver, installed automatically by `vgamepad`)
- **Python 3.9+**
- **Phone and PC on the same WiFi network**

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
python server.py
```

Or use the launcher with a desktop monitor GUI:

```bash
python gui.py
```

The server prints a URL like `http://192.168.1.100:8000`. Open it on your phone. That's it — a full gamepad layout appears automatically.

### Desktop Monitor

Open `http://<pc-ip>:8000/monitor` on your PC browser for a live dashboard showing stick crosshairs, trigger levels, button indicators, and connected devices.

---

## Usage

### Controls

| Control | Action |
|---------|--------|
| Buttons (A, B, X, Y, etc.) | Tap to press, release to release |
| LT / RT | Touch and drag — analog value scales with drag distance |
| LS / RS | Drag to move — returns to center on release |
| Cog icon | Toggle toolbar and page tabs visibility |
| SET | Open settings (haptic toggle, fullscreen) |

### Multiple Pages

The default layout has a single page. Use the desktop dashboard (or the `+` page tab) to add more pages — each can have its own control layout, shared across one virtual controller.

---

## Architecture

```
Phone Browser                      PC Server (FastAPI)
┌──────────────────────┐           ┌───────────────────────────┐
│  index.html          │ WebSocket │  server.py                │
│  ┌────────────────┐  │ ────────→ │  ├── events.py (routing)  │
│  │ TK.* namespace  │  │ keydown/  │  ├── layout.py (CRUD)    │
│  │  - WebSocket    │  │ analog   │  ├── keyboard.py          │
│  │  - Touch Input  │  │ ←─────── │  │   └── vgamepad         │
│  │  - Layout Render│  │ layout   │  │        └── ViGEmBus    │
│  └────────────────┘  │          │  │             └── XInput │
└──────────────────────┘           │  ├── storage.py (I/O)     │
                                    │  ├── network.py          │
                                    │  └── config.py           │
                                    └───────────────────────────┘
```

### Data Flow

1. **Touch event** on phone → `GamepadController` classifies it (button tap, stick drag, trigger drag)
2. **JSON message** sent over WebSocket (`keydown` / `keyup` / `analog`)
3. **Server** routes the message to `keyboard.py` which drives the virtual Xbox 360 controller via `vgamepad`
4. **Layout data** is sent from server to phone on connection, rendering the controls
5. **All input** is broadcast to other WebSocket clients (monitors)

---

## Project Structure

```
TouchKeys/
├── server.py                 # FastAPI + WebSocket server entry point
├── gui.py                    # Desktop monitor launcher (optional)
├── requirements.txt          # Python dependencies
├── layout.json               # Saved control layout (auto-created)
│
├── controller/
│   ├── keyboard.py           # Virtual Xbox 360 gamepad driver
│   ├── layout.py             # Layout CRUD, undo/redo, pages
│   ├── events.py             # WebSocket message routing
│   ├── config.py             # App configuration
│   ├── storage.py            # JSON file I/O
│   ├── network.py            # LAN IP detection, connection manager
│   └── utils.py              # Shared utilities
│
├── templates/
│   └── index.html            # Single-page mobile app (all JS/CSS inlined)
│
└── static/
    ├── css/main.css          # Stylesheet reference
    └── js/                   # Modular JS source files
```

---

## Configuration

Edit `layout.json` to customize the default control layout. The format is:

```json
{
  "pages": [
    {
      "id": "page-uuid",
      "name": "Standard",
      "buttons": [
        {
          "id": "btn-uuid",
          "name": "A",
          "keybind": "a",
          "type": "button",
          "x": 0.5,
          "y": 0.5,
          "width": 0.15,
          "height": 0.15
        }
      ]
    }
  ]
}
```

Coordinates (`x`, `y`) and dimensions (`width`, `height`) are **ratios** (0–1) relative to the viewport. `type` can be `button`, `analog_stick`, or `trigger`.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Phone can't connect | Same WiFi? Windows Firewall blocking port 8000? Check the IP printed on server start. |
| Controller not detected in game | Run `python server.py` and check `joy.cpl` — a virtual Xbox 360 controller should appear. |
| Buttons don't fit screen | The layout was designed for a specific aspect ratio. Use the desktop dashboard to adjust. |
| Input lag | Use 5 GHz WiFi; wired Ethernet for the server PC is ideal. |
| ViGEmBus errors | Run `pip install vgamepad` — it installs ViGEmBus automatically. Reboot if needed. |

---

## Development

The frontend is a single HTML file (`templates/index.html`) with all JavaScript and CSS inlined. The modular source files in `static/js/` serve as reference. To modify the frontend, edit `index.html` directly.

### Server API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Mobile gamepad page |
| `/monitor` | GET | Desktop monitor page |
| `/ws` | WebSocket | Real-time control and layout data |
| `/api/ip` | GET | Server LAN IP address |
| `/api/debug` | GET | Debug state |
| `/api/clients` | GET | Connected clients |
| `/api/keys` | GET | Active key states |
| `/static/*` | GET | Static assets |

---

## Dependencies

- **fastapi** — Web framework
- **uvicorn** — ASGI server
- **vgamepad** — Virtual Xbox 360 controller via ViGEmBus
- **websockets** — WebSocket support (optional, for `gui.py`)
- **customtkinter** — Desktop monitor GUI (optional)

All on-device dependencies are zero — the phone only needs a modern web browser.

---

## License

MIT
