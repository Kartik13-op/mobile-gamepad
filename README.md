# Mobile GamePad

Turn any phone, tablet, or touch device on the same WiFi into a **gamepad controller** for your PC. All buttons, analog sticks, and triggers are fully customizable — resize, reposition, and configure them in real-time from the browser.

![screenshot](https://img.shields.io/badge/status-stable-brightgreen)

---

## Features

- **Xbox-style gamepad** — A/B/X/Y, D-pad, bumpers, triggers, analog sticks, HOME/BACK/START
- **Analog LT/RT triggers** — press and drag to control 0–1 values with smooth interpolation
- **Dual analog sticks** — dead-zone filtering, throttle, EMA smoothing, power-curve response
- **Multi-touch** — press multiple buttons and move both sticks simultaneously
- **Real-time layout editor** — drag, resize, rename, re-layer every control with undo/redo
- **Multiple pages** — create separate controller pages for different games
- **Desktop monitor** — bundled tkinter GUI to see live input state (server status, test panel)
- **Xbox 360 controller emulation** – games see a real gamepad via ViGEmBus virtual driver; no cursor interference
- **Ultra low latency** – WebSocket transport with 16ms throttle and change-threshold filtering
- **Edit mode** – toggle between **PLAY** (inputs active) and **EDIT** (arrange controls)
- **Save / Load / Import / Export** – layouts persist and are shareable as JSON files
- **PWA ready** – add to home screen for fullscreen, no chrome
- **Black & white design** – no animations except white flash on press, no distractions

---

## Quick Start

### Prerequisites

- **Windows 10/11** (uses ViGEmBus virtual gamepad driver + SendInput)
- **Python 3.9+**
- Your phone/tablet and PC on the **same WiFi network**

### Install & Run

```bash
# 1. Clone the repo
git clone https://github.com/Kartik13-op/mobile-gamepad.git
cd mobile-gamepad

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. (First time only) Install the ViGEmBus virtual driver
#    vgamepad will prompt you to install it automatically on first import,
#    or download from: https://github.com/nefarius/ViGEmBus/releases

# 4. Start the server
python server.py

# 5. Open on your phone
#    The server prints the URL, e.g. http://192.168.1.100:8000
#    Open this URL in Chrome/Safari on your phone
```

### Desktop Monitor (optional)

```bash
python gui.py
```

Opens a tkinter window showing server status, connected devices, and a live test panel with stick crosshairs, trigger bars, and button indicators.

---

## User Guide

### Modes

| Mode | Button | What it does |
|------|--------|--------------|
| **PLAY** | `PLAY` (top-left) | Touch inputs are sent to the PC as keyboard/gamepad events |
| **EDIT** | `EDIT` (top-left) | Touch inputs are disabled; tap, drag, resize controls on screen |

### Toolbar

| Button | Action |
|--------|--------|
| PLAY | Switch to play mode |
| EDIT | Switch to edit mode |
| + ADD | Add a new control (button, analog stick, or trigger) |
| UNDO / REDO | Undo/redo layout changes |
| SAVE | Save layout to `layout.json` |
| SET | Open settings panel |
| ⚙ (cog) | Toggle toolbar visibility on mobile |

### Controls Reference

| Control | Touch behavior |
|---------|---------------|
| **A, B, X, Y** | Tap = press, release = release |
| **LB, RB** | Tap = press, release = release |
| **LT, RT** | Press = keydown, drag anywhere = analog value (0–1), release = keyup + zero |
| **D-Pad (▲◄►▼)** | Tap = press, release = release |
| **HOME, BACK, START** | Tap = press, release = release |
| **LS, RS (Left/Right Stick)** | Drag thumb = analog X/Y, release snaps to center |

### Editing Controls

1. Switch to **EDIT** mode
2. **Tap** a control to select it (blue border)
3. **Drag** the control to move it
4. **Drag the bottom-right resize handle** to resize
5. The **Properties Panel** opens on the right — edit name, keybind, type, size, opacity, and layer
6. Press **Delete** key or use context menu to remove a control
7. Use **UNDO / REDO** to revert changes
8. Press **SAVE** to persist

### Settings

| Setting | Description |
|---------|-------------|
| Snap to grid | Align controls to grid cells |
| Grid size | Grid cell size in pixels |
| Show grid | Toggle grid overlay visibility |
| Haptic feedback | Vibrate on button press (mobile) |
| Auto-save | Automatically save on changes |

### Keyboard Shortcuts (on PC)

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save layout |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+D` | Duplicate selected control |
| `Delete` | Delete selected control |

---

## Supported Keybinds

| Category | Keys |
|----------|------|
| Letters | A–Z |
| Numbers | 0–9 |
| Function | F1–F24 |
| Modifiers | Shift, Ctrl, Alt, Win |
| Navigation | Up, Down, Left, Right, Home, End, PageUp, PageDown |
| Editing | Backspace, Delete, Insert |
| Whitespace | Space, Tab, Enter |
| Control | Escape, CapsLock, PrintScreen, Pause, ScrollLock |
| Numpad | Numpad0–9, Add, Subtract, Multiply, Divide, Decimal |
| Gamepad | `gamepad_a`, `gamepad_b`, `gamepad_x`, `gamepad_y` |
| | `gamepad_lb`, `gamepad_rb`, `gamepad_lt`, `gamepad_rt` |
| | `gamepad_ls`, `gamepad_rs` |
| | `gamepad_dpad_up/down/left/right` |
| | `gamepad_home`, `gamepad_back`, `gamepad_start` |

Gamepad keys are treated as virtual gamepad buttons (not keyboard keys) and are exposed to the desktop monitor and any automation software that listens to WebSocket input broadcasts.

---

## Architecture

```
┌──────────────────────┐      WebSocket       ┌──────────────────────┐
│   Mobile Browser     │ ──────────────────→  │   PC Server          │
│   (index.html)       │   keydown/keyup/     │   (server.py)        │
│                      │   analog             │                      │
│  ┌────────────────┐  │                      │  ┌────────────────┐  │
│  │ Controller.js  │──│─────────────────────│→│  events.py      │  │
│  │ Touch handlers │  │                      │  └───────┬────────┘  │
│  └────────────────┘  │                      │          │           │
│  ┌────────────────┐  │                      │  ┌───────▼────────┐  │
│  │ Layout Editor  │  │                      │  │ keyboard.py    │  │
│  │ (editor.js)    │  │                      │  │ (vgamepad +    │  │
│  └────────────────┘  │                      │  │  SendInput)    │  │
│  ┌────────────────┐  │                      │  └───────┬────────┘  │
│  │ Layout State   │──│──HTTP POST/GET──────│──────────│────────── │
│  │ (layout.js)    │  │                      │          │           │
│  └────────────────┘  │                      │  ┌───────▼────────┐  │
│  ┌────────────────┐  │                      │  │ ViGEmBus      │  │
│  │ WebSocket.js   │  │                      │  │ (Xbox 360     │  │
│  └────────────────┘  │                      │  │  virtual HID) │  │
│                      │                      │  └───────┬────────┘  │
│                      │                      │          │           │
│                      │                      │  ┌───────▼────────┐  │
│                      │                      │  │ network.py     │  │
│                      │                      │  └────────────────┘  │
└──────────────────────┘                      └──────────────────────┘
```

### Data Flow

1. User touches a control on the mobile browser
2. `controller.js` determines the touch type (button press, analog stick drag, trigger drag)
3. A JSON message is sent via WebSocket:
   - `{type: "input", subtype: "keydown", key: "gamepad_a"}`
   - `{type: "input", subtype: "analog", key: "gamepad_ls", x: 0.45, y: -0.82}`
4. `server.py` receives the message and passes it to `events.py`
5. `events.py` routes to `keyboard.py` which applies EMA smoothing and drives the virtual Xbox 360 controller via `vgamepad` (ViGEmBus driver)
6. Gamepad button presses (A, B, X, Y, LB, RB, D-Pad, etc.) are sent as Xbox controller button presses
7. Analog stick movements (LS, RS) are sent as Xbox joystick axis values
8. Trigger drags (LT, RT) set the Xbox trigger analog value 0–1
9. Regular keyboard keys (W, Space, etc.) use `SendInput` with virtual key codes
10. All input messages are broadcast (fire-and-forget) to other WebSocket clients (gui.py monitor)

### Network

- Server runs on `0.0.0.0:8000`
- WebSocket endpoint: `ws://<pc-ip>:8000/ws`
- HTTP endpoints: `/` (UI), `/api/clients`, `/api/keys`
- Broadcast: all input events are forwarded to every connected WebSocket client
- Fire-and-forget: broadcasts use `asyncio.create_task` to never block the hot path

### Latency Pipeline

```
Touch → elementsFromPoint → dead-zone check → throttle (16ms)
→ change-threshold → WS send → server receive → fire-and-forget broadcast
→ EMA (α=0.35) → vgamepad/SendInput → ViGEmBus driver → game
```

---

## Project Structure

```
mobile-gamepad/
├── server.py              # FastAPI + WebSocket server entry point
├── gui.py                 # tkinter desktop monitor (optional)
├── requirements.txt       # Python dependencies
├── layout.json            # Saved control layout
├── settings.json          # Application settings (snap, grid, haptic)
├── .gitignore
├── README.md
│
├── controller/            # Backend modules
│   ├── __init__.py
│   ├── keyboard.py        # vgamepad (Xbox 360) + SendInput input simulation
│   ├── layout.py          # Layout CRUD, undo/redo, page management
│   ├── config.py          # Settings load/save
│   ├── events.py          # WebSocket message routing + broadcast
│   ├── storage.py         # JSON file I/O with locking
│   ├── network.py         # LAN IP detection + connection tracker
│   └── utils.py           # Shared helpers
│
├── templates/
│   └── index.html         # Single-page application HTML
│
└── static/
    ├── css/
    │   └── main.css       # All styles (black-and-white design)
    └── js/
        ├── app.js         # App entry point, wiring, keyboard shortcuts
        ├── websocket.js   # WebSocket client with reconnection
        ├── controller.js  # Touch handling, analog sticks, triggers
        ├── editor.js      # Layout editor (select, drag, resize, properties)
        ├── layout.js      # Client-side layout state, control CRUD, pages
        ├── ui.js          # Mode management, modals, toasts, context menu
        ├── settings.js    # Settings panel logic
        └── utils.js       # Event bus, debounce, throttle helpers
```

---

## Installation Methods

### 1. Direct (pip)

```bash
git clone https://github.com/Kartik13-op/mobile-gamepad.git
cd mobile-gamepad
pip install -r requirements.txt
python server.py
```

### 2. Virtual Environment (recommended)

```bash
git clone https://github.com/Kartik13-op/mobile-gamepad.git
cd mobile-gamepad
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate
pip install -r requirements.txt
python server.py
```

### 3. Portable (USB stick)

Install dependencies on your PC, copy the entire `mobile-gamepad` folder to a USB drive, and run `python server.py` on any Windows machine with Python installed.

### 4. Run as Background Service (advanced)

Use `nssm` or `pyw` to run `server.py` as a background process that starts on boot.

---

## Desktop Monitor (gui.py)

The tkinter monitor has two tabs:

**Server tab** — shows connection status, connected device IDs, Start/Stop server buttons.

**Test tab** — live visualization of all inputs:
- LS/RS crosshairs with draggable dots
- LT/RT analog fill bars with numeric readout
- LB/RB, A/B/X/Y, HOME/BACK/START, D-Pad button state indicators

---

## Development

### Running with hot-reload for frontend

The static files are served directly; just edit CSS/JS and refresh the browser.

### Running the server with auto-restart

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `vgamepad` / ViGEmBus not working | Run as Administrator once, or install ViGEmBus from https://github.com/nefarius/ViGEmBus/releases |
| Phone can't connect | Ensure both devices are on the **same WiFi** and Windows Firewall allows port 8000 |
| Input lag | Use a 5 GHz WiFi network; keep the server PC wired via Ethernet |
| Sticks not centering | Release all touches and re-engage |
| Layout lost after refresh | Click **SAVE** before refreshing; auto-save must be enabled in settings |

---

## Games Tested

- Rocket League(Easy Anticheat Turned OFF)

## License

MIT
