# TouchKeys — Mobile Gamepad

Turn any phone or tablet into a **virtual Xbox 360 gamepad** for your PC. Fully customizable controls with a real-time layout editor, analog sticks, and triggers.

---

## Features

- **Xbox 360 controller emulation** — single virtual controller via vgamepad + ViGEmBus; games see a real gamepad
- **A/B/X/Y, D-pad, LB/RB, LS/RS, LT/RT, BACK/START** — all standard Xbox controls
- **Analog triggers** — touch and drag for smooth 0–1 analog values
- **Dual analog sticks** — dead-zone filtering, throttle, change-threshold filtering
- **Multi-touch** — press multiple buttons and move both sticks simultaneously
- **Real-time layout editor** — drag, resize, re-layer every control with undo/redo
- **Multiple pages** — create different layouts per game, all sharing one virtual controller
- **Desktop monitor** — bundled customtkinter GUI with live input visualization
- **PWA ready** — add to home screen for fullscreen
- **Ultra low latency** — WebSocket transport with 16ms throttle
- **Save / Load / Import / Export** — layouts persist as JSON files

---

## Quick Start

### Prerequisites

- **Windows 10/11** (requires ViGEmBus driver)
- **Python 3.9+**
- Phone and PC on the **same WiFi**

### Install & Run

```bash
pip install -r requirements.txt
python server.py
```

Open the printed URL (e.g. `http://192.168.1.100:8000`) on your phone. The first page is pre-populated with a full gamepad layout.

### Desktop Monitor

```bash
python gui.py
```

Connects as a WebSocket monitor — shows live stick crosshairs, trigger bars, button indicators, and connected devices.

---

## User Guide

### Modes

| Mode | Button | Behavior |
|------|--------|----------|
| **PLAY** | `PLAY` | Touch inputs drive the virtual Xbox 360 controller |
| **EDIT** | `EDIT` | Touch inputs disabled; tap, drag, resize controls |

### Toolbar

| Button | Action |
|--------|--------|
| PLAY / EDIT | Toggle mode |
| + BTN / + STICK / + TRIG | Quick-add a button, analog stick, or trigger |
| UNDO / REDO | Undo/redo layout edits |
| SAVE | Save layout to `layout.json` |
| SET | Settings panel |

### Editing

1. Switch to **EDIT** mode
2. Tap a control to select it → ☰ hamburger appears top-right
3. Tap ☰ to open the properties panel
4. Drag to move, drag corner handles to resize
5. `Ctrl+Z`/`Ctrl+Y` to undo/redo
6. `Ctrl+S` to save

### Controls

| Control | Behavior |
|---------|----------|
| Buttons (A, B, X, Y, LB, RB, D-pad, BACK, START) | Tap to press, release to release |
| LT / RT | Touch and drag — analog value 0–1 based on drag distance |
| LS / RS | Drag — analog X/Y, snaps to center on release |

---

## Architecture

```
Phone Browser                    PC Server
┌──────────────┐   WebSocket    ┌──────────────────┐
│ controller.js │ ──────────→  │ events.py         │
│ layout.js     │   keydown/    │   ↓               │
│ editor.js     │   analog      │ keyboard.py       │
└──────────────┘               │   (vgamepad)       │
                                │   ↓               │
                                │ ViGEmBus driver   │
                                │   ↓               │
                                │ game sees Xbox 360│
                                └──────────────────┘
```

### Data Flow

1. Touch on phone → `controller.js` determines type (button, stick, trigger)
2. JSON message sent via WebSocket (`keydown` / `analog`)
3. `events.py` routes to `keyboard.py`
4. `keyboard.py` sends button/axis state to vgamepad → ViGEmBus → XInput
5. All input broadcast to other WebSocket clients (monitors)

---

## Project Structure

```
TouchKeys/
├── server.py              # FastAPI + WebSocket server
├── gui.py                 # customtkinter monitor (optional)
├── requirements.txt
├── layout.json            # Saved layout (auto-created)
├── settings.json          # App settings
│
├── controller/
│   ├── keyboard.py        # Single virtual Xbox 360 gamepad
│   ├── layout.py          # Layout CRUD, undo/redo, pages
│   ├── events.py          # WebSocket message routing
│   ├── config.py          # Settings
│   ├── storage.py         # JSON file I/O
│   ├── network.py         # LAN IP, connection manager
│   ├── utils.py
│   └── default_gamepad.json  # Template for new pages
│
├── templates/
│   └── index.html         # SPA frontend
│
└── static/
    ├── css/main.css
    └── js/
        ├── app.js         # Entry point
        ├── websocket.js   # WebSocket client
        ├── controller.js  # Touch handling
        ├── editor.js      # Layout editor
        ├── layout.js      # Client layout state
        ├── ui.js          # Modals, toasts, mode
        ├── settings.js
        └── utils.js
```

---

## Requirements

- `fastapi`, `uvicorn` — Web server
- `vgamepad` — Xbox 360 virtual controller via ViGEmBus
- `websockets` — WebSocket client (optional, for gui.py)
- `customtkinter` — Desktop monitor (optional)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Phone can't connect | Same WiFi? Windows Firewall blocking port 8000? |
| Controller not detected | Run `python server.py` and check `joy.cpl` while server is running |
| ViGEmBus not installed | vgamepad installs it automatically; or download from ViGEmBus releases |
| Input lag | 5 GHz WiFi; wired Ethernet for server PC |

---

## License

MIT
