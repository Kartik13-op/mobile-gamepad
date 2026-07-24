<div align="center">

# TouchKeys — Mobile Gamepad

### Turn any phone or tablet into a virtual Xbox 360 gamepad for your PC

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue)](https://github.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/)

**No installation on the phone. No app stores. No ads. Just a URL and a browser.**

[Features](#features) • [Quick Start](#quick-start) • [Usage](#usage) • [Dynamic Joysticks](#dynamic-joysticks) • [Architecture](ARCHITECTURE.md) • [Configuration](#configuration) • [API Reference](#api-reference) • [Development](#development)

</div>

---

## Why TouchKeys?

Traditional phone-as-gamepad solutions require installing proprietary apps, dealing with bloatware, or paying for premium features. TouchKeys is different:

- **Zero-install client** — your phone needs nothing but a browser. Open a URL, and you have a full gamepad.
- **Real Xbox 360 emulation** — games see a genuine Xbox 360 controller via ViGEmBus driver. No key-mapping hacks, no compatibility layers.
- **Full analog control** — real analog sticks with dead-zone filtering, analog triggers with pressure-sensitive input.
- **Multi-touch** — press A, move the right stick, and pull the left trigger simultaneously. All at once.
- **Customizable layout** — every button, stick, and trigger can be positioned, resized, and themed. Multiple pages per game.
- **Ultra low latency** — WebSocket transport with 16 ms throttle. Feels like a wired controller on a good WiFi network.
- **Open source** — MIT licensed. Fork it, hack it, embed it.

---

## Features

### Gamepad Emulation
- **Complete Xbox 360 controller** — A, B, X, Y, D-pad (up/down/left/right), LB, RB, LT, RT, LS, RS, BACK, START, HOME (Guide)
- **Analog triggers** — touch-and-drag for smooth 0–1 analog range; games see real trigger axis input
- **Dual analog sticks** — with configurable dead zone (default 15%), 16 ms throttle, and change-threshold filtering for jitter-free control
- **Virtual controller via ViGEmBus** — appears as a genuine Xbox 360 controller in `joy.cpl` and every XInput-compatible game

### Dynamic Joysticks
- **Touch-centering** — each joystick centers itself exactly where your finger first lands, not at a fixed element midpoint. This eliminates precision loss from off-center starting positions.
- **Visual ring + dot** — a glowing green circular ring appears at the initial touch point, with a bright dot following your finger. The ring's glow intensity indicates the stick's displacement magnitude.
- **Clamped to boundary** — the dot is constrained within the ring's radius. Pushing to the edge saturates the axis at ±1.0.
- **15 % inner dead zone** — tiny accidental movements near center are filtered out. Configurable via `ANALOG_DEAD_ZONE` constant in `controller.js`.
- **~60 updates / sec** — throttled via `ANALOG_THROTTLE_MS` (16 ms). Change-threshold filtering (`ANALOG_CHANGE_THRESHOLD = 0.04`) prevents redundant sends when the stick is stationary.
- **Clean release** — lifting your finger instantly centers the stick (sends `{x:0, y:0}`) and removes the ring and dot. No phantom input.

### Client Experience
- **Zero-install web app** — open a URL; no app store, no APK, no sideloading
- **Fast single-page app** — all JavaScript is served as ES modules (~6 KB gzipped total)
- **Multi-touch** — unlimited simultaneous touches (device-dependent); press any combination of controls
- **Haptic feedback** — vibration on button press (devices that support `navigator.vibrate`)
- **PWA ready** — "Add to Home Screen" for fullscreen standalone mode with no browser chrome
- **Auto-reconnect** — WebSocket reconnects with exponential backoff (500 ms → 8 s)
- **Latency display** — real-time round-trip time in the toolbar badge

### Layout System
- **Fully customizable** — every control is positionable by ratio (0–1) relative to viewport
- **Three control types** — buttons (momentary), analog sticks (2-axis drag), and analog triggers (1-axis drag)
- **Multiple pages** — create different layouts for different games, all sharing one virtual controller
- **Undo / Redo** — unlimited history for layout edits via the desktop monitor
- **Save / Load / Import / Export** — layouts persist as `layout.json`; share layouts as JSON files

### Server & Monitoring
- **Desktop monitor** — live dashboard at `/monitor` showing stick crosshairs, trigger bars, button states, and connected devices
- **Layout Editor** — drag-and-drop canvas with resize handles, property sliders (x, y, w, h, opacity, layer, font size), page tabs with add/delete, undo/redo, add-button modal. All changes sync live to connected phones.
- **Input Monitor** — 15-button grid with live press highlighting, dual analog stick canvases with crosshairs and coordinate display, analog trigger bars with fill percentage
- **REST API** — programmatic access to server state, connections, and diagnostics
- **Multi-client** — one active controller; monitors and passive clients can observe live input
- **Auto-promotion** — when the active controller disconnects, the next waiting client takes over instantly

---

## Quick Start

### One-click Setup

Right-click `setup.ps1` → **Run with PowerShell**. That's it.

The script automatically:
1. Checks for Python 3.9+ — downloads and installs it silently if missing
2. Creates a virtual environment (`.venv/`)
3. Installs all dependencies from `requirements.txt`
4. Offers to launch the server

If PowerShell blocks execution, run this once:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Manual Setup

| Requirement | Notes |
|-------------|-------|
| **Windows 10/11** | ViGEmBus kernel driver (installed automatically by `vgamepad`) |
| **Python 3.9+** | Tested with 3.9–3.13 |
| **WiFi network** | Phone and PC must be on the same LAN |
| **Modern phone browser** | Chrome, Safari, Edge, Firefox — any browser from the last 3 years |

```powershell
# Clone or extract the project, then:
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

Or double-click `start.ps1` after the first setup — it runs `gui.py`, which starts the server and opens the desktop monitor in your browser.

The server prints a URL like:
```
http://192.168.1.100:8000
```

Open that URL on your phone. A complete Xbox 360 gamepad layout appears automatically. Every button, stick, and trigger works immediately.

### What to Expect

1. **Phone**: Open the URL → toolbar shows **OFF** → changes to **ON** when connected → controls appear
2. **PC**: Press a button on the phone → check `joy.cpl` → the virtual Xbox 360 controller responds
3. **Game**: Launch any XInput-compatible game → the virtual controller is recognized as Gamepad #1

### QR Code Connection

The dashboard displays a QR code encoding the server URL. Scan it with your phone's camera to open the controller instantly — no need to type the IP address manually. Access the QR code at `http://<server-ip>:8000/monitor` (Dashboard tab).

---

## Usage

### Controls Reference

| Control | Touch Action | Network Message | Gamepad Effect |
|---------|-------------|-----------------|----------------|
| **A, B, X, Y** | Tap (press), release | `keydown` / `keyup` | Button press/release |
| **D-pad (▲▼◄►)** | Tap | `keydown` / `keyup` | D-pad press/release |
| **LB, RB** | Tap | `keydown` / `keyup` | Shoulder button |
| **LT, RT** | Touch + drag up/down | `analog` (x = 0–1) | Trigger axis |
| **LS, RS** | Touch anywhere + drag | `analog` (x = -1..1, y = -1..1) | Joystick axis |
| **BACK, START** | Tap | `keydown` / `keyup` | Back / Start |
| **HOME** | Tap | `keydown` / `keyup` | Guide button |
| **Cog (⚙)** | Tap | — | Toggle toolbar visibility |
| **SET** | Tap | — | Open settings (haptic, fullscreen) |

### Dynamic Joysticks — How They Work

Analog sticks use a **dynamic centering** model that's different from traditional fixed-center virtual joysticks:

1. **Touch anywhere** — put your finger down anywhere inside the stick's dashed outline area. A glowing green ring appears, centered exactly on your touch point.
2. **Drag from center** — as you drag, a bright green dot follows your finger. The offset from the initial touch point determines the axis values. The dot is clamped to the ring's boundary.
3. **Visual feedback** — the ring glows brighter as the stick is displaced. The dot position maps 1:1 to the analog x/y values sent over the wire.
4. **Release resets** — lift your finger. The ring and dot disappear instantly. The stick sends `{x: 0, y: 0}` to the server, centering the virtual controller's thumbstick.

This design means:
- **No precision loss** — the first touch always produces `(0, 0)`, regardless of where you start within the control area.
- **No centering guesswork** — you don't need to find a fixed center point before dragging.
- **Works in any thumb position** — comfortable whether you're holding the phone with two thumbs or one finger.

### Desktop Monitor (`/monitor`)

Open `http://<server-ip>:8000/monitor` on any desktop browser for a full control center:

| Tab | Features |
|-----|----------|
| **Dashboard** | QR code for one-scan phone connection, live stat cards (server status, client count, active controller, active device), quick actions (ping, disconnect all), usage guide |
| **Devices** | Live list of connected clients with role tags (CONTROLLER / CONNECTED / MONITOR), force-disconnect (KICK) per device, server info panel |
| **Layout Editor** | Drag-and-drop canvas with resize handles, property sliders (x, y, w, h, opacity, layer, font size), page tabs with add/delete, undo/redo, add-button modal. All changes sync live to connected phones over WebSocket. |
| **Input Monitor** | 15-button grid with live press highlighting, dual analog stick canvases with crosshairs and coordinate display, analog trigger bars with fill percentage |

### Button Logic

Every button on the phone sends two WebSocket messages:
- **`keydown`** when pressed (finger down)
- **`keyup`** when released (finger up)

The server deduplicates rapid presses per-client and broadcasts input events to the monitor for live visualization. Analog controls (sticks, triggers) send `analog` messages with continuous x/y values at ~60 updates/sec per finger.

### Multi-Touch

TouchKeys handles any number of simultaneous touches. You can:
- Hold **A** while dragging the **right stick** and pulling **RT**
- Press **LB + RB** simultaneously
- Move **both sticks** at the same time

Each touch is tracked by its `touch.identifier` across start/move/end events. The stick state is stored in a `Map<touchId, StickState>`, so each finger independently controls its own stick instance.

### Fullscreen Mode

- **Browser**: Tap the **SET** button, then **FULLSCREEN**
- **Safari (iOS)**: Add to Home Screen for a fullscreen PWA experience with no browser chrome
- **Chrome (Android)**: "Add to Home Screen" works similarly

---

## Configuration

### Settings File

The server stores application settings in `settings.json` at the project root:

```json
{
  "theme": "dark",
  "gridSize": 20,
  "snapToGrid": true,
  "showGrid": true,
  "hapticFeedback": true,
  "autoSave": true,
  "autoSaveInterval": 5000
}
```

### Layout JSON Format

The server reads and writes `layout.json` in the project root. This file contains all pages and their controls. Edit it directly to customize the default layout, or use the desktop monitor's Layout Editor for visual editing.

**Full structure:**

```json
{
  "version": "2.0",
  "activePageIndex": 0,
  "pages": [
    {
      "id": "p1",
      "name": "Standard",
      "buttons": [
        {
          "id": "b01",
          "name": "A",
          "keybind": "gamepad_a",
          "type": "button",
          "x": 0.76,
          "y": 0.78,
          "width": 54,
          "height": 54,
          "opacity": 0.90,
          "fontSize": 16,
          "layer": 1,
          "visible": true
        }
      ]
    }
  ]
}
```

### Control Types

| Type | CSS Class | Behavior |
|------|-----------|----------|
| `button` | `.ctrl-btn` | Momentary press; flashes white on touch |
| `analog_stick` | `.ctrl-analog` | Circular drag zone with dynamic centering; returns to center on release |
| `trigger` | `.ctrl-trigger` | Linear drag; analog value proportional to drag distance from initial touch point |

### Control Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Unique identifier (server-generated) |
| `name` | string | Display label shown on the control |
| `keybind` | string | Gamepad action this control maps to (see keybind reference) |
| `type` | string | One of `button`, `analog_stick`, `trigger` |
| `x` | number | Horizontal position ratio (0 = left, 1 = right edge) |
| `y` | number | Vertical position ratio (0 = top, 1 = bottom edge) |
| `width` | number | Width in CSS pixels |
| `height` | number | Height in CSS pixels |
| `opacity` | number | Opacity 0–1 (applied as CSS opacity) |
| `fontSize` | number | Label font size in CSS pixels |
| `layer` | number | Z-index layer for stacking order |
| `visible` | boolean | Whether the control is shown |

### Keybind Reference

| Keybind | Gamepad Control |
|---------|----------------|
| `gamepad_a` | A button |
| `gamepad_b` | B button |
| `gamepad_x` | X button |
| `gamepad_y` | Y button |
| `gamepad_lb` | Left shoulder |
| `gamepad_rb` | Right shoulder |
| `gamepad_lt` | Left trigger (analog) |
| `gamepad_rt` | Right trigger (analog) |
| `gamepad_ls` | Left stick (analog) |
| `gamepad_rs` | Right stick (analog) |
| `gamepad_back` | Back button |
| `gamepad_start` | Start button |
| `gamepad_home` | Guide / Home button |
| `gamepad_dpad_up` | D-pad up |
| `gamepad_dpad_down` | D-pad down |
| `gamepad_dpad_left` | D-pad left |
| `gamepad_dpad_right` | D-pad right |

### Coordinate System

- **Positions** (`x`, `y`) are ratios from 0–1 relative to viewport width/height, accurate to 6 decimal places
- **Dimensions** (`width`, `height`) are in **CSS pixels** (e.g., 54, 60, 90)
- **Origin**: (0, 0) is top-left; (1, 1) is bottom-right
- **Minimum size**: Controls are clamped to 40 px minimum on each axis

---

## API Reference

### HTTP Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Mobile gamepad single-page application |
| GET | `/monitor` | Desktop live-input monitor dashboard |
| GET | `/api/ip` | Server LAN IP address |
| GET | `/api/keys` | List of supported keybind names |
| GET | `/api/clients` | Connected clients and their IDs |
| GET | `/api/debug` | Server diagnostic state |
| DELETE | `/api/clients/{id}` | Force-disconnect a client |

### WebSocket Endpoint

**`ws://<server-ip>:8000/ws`**

Full protocol specification, message types, and lifecycle: see [ARCHITECTURE.md](ARCHITECTURE.md#websocket-protocol).

---

## Project Structure

```
TouchKeys/
│
├── server.py                 # FastAPI application entry point (ASGI)
├── gui.py                    # Desktop monitor launcher (customtkinter)
├── requirements.txt          # Python dependencies
├── layout.json               # Saved control layout (auto-generated)
├── settings.json             # Application settings (auto-generated)
├── setup.ps1                 # One-click setup: installs Python + deps + launches server
├── start.ps1                 # Quick-launch: runs gui.py which starts the server and opens the browser
├── .gitignore                # Git ignore rules
├── .server.lock              # Single-instance lock file (auto-generated)
├── IMPROVEMENTS.md           # Development notes and ideas
├── ARCHITECTURE.md           # System architecture documentation
├── LICENSE                   # MIT license
├── README.md                 # This file
│
├── controller/               # Python server modules
│   ├── __init__.py
│   ├── keyboard.py           # Virtual Xbox 360 gamepad driver (vgamepad wrapper)
│   ├── layout.py             # Layout CRUD, undo/redo stack, page management
│   ├── events.py             # WebSocket message routing & input deduplication
│   ├── config.py             # Application configuration manager
│   ├── storage.py            # Atomic JSON file read/write with locking
│   ├── network.py            # Connection manager, client tracking, LAN IP detection
│   └── utils.py              # Shared Python utilities
│
├── templates/                # Jinja2 / server-rendered HTML
│   ├── index.html            # Mobile SPA shell (loads JS/CSS from static/)
│   └── monitor.html          # Desktop control center (dashboard, layout editor, input monitor)
│
├── static/
│   ├── css/
│   │   └── main.css          # Application stylesheet (517 lines)
│   └── js/                   # Modular ES6 JavaScript source
│       ├── app.js            # Application bootstrap, WebSocket event wiring, lifecycle
│       ├── controller.js     # Touch/pointer input handling, gamepad state machine
│       ├── layout.js         # Layout rendering, control element creation, page tabs
│       ├── ui.js             # Toolbar, connection badge, toast notifications
│       ├── utils.js          # EventBus, generateId, clamp, debounce, throttle, snapToGrid
│       └── websocket.js      # WebSocket connection manager, auto-reconnect, heartbeat
│
└── __pycache__/              # Python bytecode cache (gitignored)
```

### Module Responsibilities

#### Client (`static/js/`)

| Module | File | Responsibility |
|--------|------|----------------|
| **App** | `app.js` | Bootstraps all modules, wires WebSocket events to handlers, manages lifecycle |
| **GamepadController** | `controller.js` | Touch/pointer event capture, button press/release, analog stick tracking (dynamic centering, ring + dot creation), trigger tracking, throttle/dead-zone filtering, WebSocket message send |
| **LayoutManager** | `layout.js` | Receives layout data from server, creates/removes `.ctrl-*` DOM elements, renders page tabs, handles page switching |
| **UIManager** | `ui.js` | Updates toolbar connection badge, device name/status, latency display, toast notifications |
| **WebSocketManager** | `websocket.js` | Connect/disconnect, JSON serialization, heartbeat/ping-pong, latency measurement, exponential-backoff reconnect, message routing to EventBus |
| **Utils** | `utils.js` | `EventBus` (pub/sub), `generateId` (crypto-random), `clamp`, `debounce`, `throttle`, `snapToGrid` |

#### Server (`controller/`)

| Module | File | Responsibility |
|--------|------|----------------|
| **EventRouter** | `events.py` | Dispatches incoming WebSocket messages to handler functions, deduplicates rapid key events, broadcasts state changes to all connected clients |
| **KeyboardController** | `keyboard.py` | Wraps `vgamepad` — manages virtual Xbox 360 controller state, maps keybinds to gamepad buttons/axes/triggers, handles stick normalization (±32767) |
| **LayoutManager** | `layout.py` | CRUD operations on layout data, undo/redo stack (unlimited history), page management, version migration |
| **ConfigManager** | `config.py` | Reads/writes application settings, provides defaults for unset keys |
| **StorageManager** | `storage.py` | Atomic JSON file read/write with file locking to prevent corruption |
| **ConnectionManager** | `network.py` | Tracks connected WebSocket clients, manages active controller promotion/demotion, detects LAN IP |

---

## Troubleshooting

### Connection Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Phone shows **OFF** in toolbar | WebSocket not connected | Check WiFi — both devices must be on the same network |
| Page doesn't load | Network unreachable | Verify the IP printed by `server.py` matches your PC's LAN IP |
| Connection drops repeatedly | WiFi interference | Use 5 GHz band; move closer to router |
| "Only one usage of each socket address" | Server already running | Kill the old process with Task Manager on port 8000 |
| `.server.lock` error | Stale lock file | Delete `.server.lock` and restart |

### Controller Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Game doesn't respond | Wrong controller number | Check `joy.cpl` — touchkeys controller should appear; reorder if needed |
| Buttons press but don't release | Touch event not captured | Ensure `touch-action: none` is set on `.workspace` (default configuration) |
| Analog sticks jittery | Dead zone too low | Increase `ANALOG_DEAD_ZONE` in `controller.js` (default 0.15 = 15 %) |
| Analog sticks feel sluggish | Throttle too high | Decrease `ANALOG_THROTTLE_MS` (default 16 ms → ~60 updates/sec) |
| Stick ring / dot not visible | Missing `--accent` CSS variable | The `:root` block in `main.css` must define `--accent` (e.g., `#7dff9b`). Verify the variable is present. |
| No vibration | Device or browser limitation | Check `navigator.vibrate` support; haptic may not work on all devices |
| ViGEmBus driver error | Driver not installed | `pip install vgamepad` installs it; reboot if needed |

### Layout Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Buttons off-screen | Aspect ratio mismatch | Edit `layout.json` — positions are ratios; reduce `x` / `y` values |
| Buttons too small | Viewport too large | Minimum size is 40 × 40 px; check the config values |
| Buttons not updating | Server cache | Restart the server to reload `layout.json` |

---

## Development

### Frontend Architecture

The frontend uses **ES6 modules** served natively by the browser (no bundler). Module dependencies:

```
app.js
  ├── utils.js       (eventBus)
  ├── websocket.js   (ws)
  ├── ui.js          (ui)
  ├── layout.js      (layout)
  └── controller.js  (gamepadController)
```

- **No build step** — edit any `.js` or `.css` file, refresh the browser. Zero compile time.
- **No npm** — zero npm packages. The entire frontend is hand-written JavaScript and CSS.
- **No bundler** — the browser loads modules via native `import` statements. The server serves `static/` via `StaticFiles`.

### How the Dynamic Joystick Works

The dynamic joystick logic lives entirely in `controller.js`. Here's the lifecycle:

1. **Touch start** (`_startStick` at `controller.js:163`):
   - Gets the element's bounding rect and calculates `maxDist` = 85 % of half the smallest dimension
   - Creates a `.analog-ring` `<div>` centered on the touch point with `position: absolute` inside `.analog-outer`
   - Creates a `.analog-dot` `<div>` at the touch point
   - Stores `centerX/Y` as the initial touch `clientX/clientY`, not the element center
   - Calls `_updateStickPosition` which sends `(0, 0)` initially (center = touch point)

2. **Touch move** (`_updateStickPosition` at `controller.js:204`):
   - Computes `dx/dy = currentTouch - center`
   - Clamps to `maxDist` radius (circular boundary)
   - Positions the dot at `centerPosInElement + clampedOffset`
   - Derives normalized x/y (`rawX/rawY`) by dividing by `maxDist`
   - Applies dead zone: if `magnitude < 0.15`, snaps to `(0, 0)`
   - Scales the active range: `(magnitude - deadZone) / (1 - deadZone)`
   - Throttles to 16 ms and filters changes smaller than 0.04
   - Sends `{ type: 'analog', key, x, y }` over WebSocket

3. **Touch end** (`_endStick` at `controller.js:256`):
   - Removes the `.analog-ring` and `.analog-dot` DOM elements
   - Sends `{ type: 'analog', key, x: 0, y: 0 }` to center the virtual stick

### CSS Customization

The stick visuals are controlled via CSS variables in `main.css`:

```css
:root {
  --accent: #7dff9b;       /* Ring border, dot fill, glow color */
}
```

| Class | Purpose |
|-------|---------|
| `.analog-outer` | Persistent dashed border showing the touchable area |
| `.analog-ring` | Circular outline created at initial touch point (`.visible` to show) |
| `.analog-dot` | Small circle that follows the finger (`.visible` to show) |

### Editing Client Code

```bash
# All client source files are in:
static/js/        # ES6 modules (6 files)
static/css/       # main.css (517 lines)
templates/        # index.html (shell), monitor.html (desktop GUI)
```

The server serves files from `static/` via FastAPI's `StaticFiles` mount. Edit any file and refresh the browser — no build step needed.

### Backend

The Python server follows a modular singleton pattern:

```python
# server.py — all core services are instantiated at module level
storage = StorageManager(BASE_DIR)
config_manager = ConfigManager(storage)
keyboard = KeyboardController()
layout_manager = LayoutManager(storage)
connections = ConnectionManager()
event_router = EventRouter(keyboard, layout_manager, config_manager, connections)
```

To add a new message handler:
1. Add a handler method in `controller/events.py`
2. Register it in `EventRouter._handlers` dict
3. Send the message from the client via `ws.send({ type: "your_type", ... })`

### Running Tests

```bash
# No formal test suite yet — contributions welcome!
# Manual test: start server, connect phone, verify joy.cpl
```

### Setup Scripts

Two PowerShell scripts are provided for convenience:

| Script | When to use |
|--------|-------------|
| `setup.ps1` | **First run** — installs Python (if missing), creates `.venv`, installs deps, launches server |
| `start.ps1` | **Subsequent runs** — runs `gui.py`, which starts the server and opens the browser automatically |

Right-click either script → **Run with PowerShell**.

---

## Dependencies

### Python (required)

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | ≥0.104.0 | Web framework with WebSocket support |
| `uvicorn[standard]` | ≥0.24.0 | ASGI server |
| `vgamepad` | ≥0.1.0 | Virtual Xbox 360 controller via ViGEmBus |

### Python (optional)

| Package | Version | Purpose |
|---------|---------|---------|
| `customtkinter` | Latest | Desktop monitor GUI |
| `websockets` | Latest | WebSocket client for `gui.py` |

### Phone (zero dependencies)

The phone needs nothing but a modern web browser with:
- WebSocket support (all browsers since 2011)
- ES6 module support (all browsers since 2018)
- Touch events (all modern touch devices)
- `navigator.vibrate` (optional — for haptic feedback)

---

## Benchmarks

| Metric | Measurement |
|--------|-------------|
| Page load size | ~6 KB gzipped (JS modules + CSS) |
| Time to interactive | <500 ms on modern phone |
| WebSocket latency (LAN) | 2–5 ms |
| Input throughput | ~60 events/sec per analog stick |
| Max simultaneous touches | 10+ (device dependent) |
| Server CPU usage | <1% at idle, <5% under load |
| Server RAM usage | ~50 MB |
| Connection limit | Unlimited (practical: 50+ clients) |

---

## Roadmap

- [x] Core Xbox 360 gamepad emulation
- [x] Multi-touch input
- [x] Analog sticks with dead zone
- [x] Dynamic joystick centering (touch-point center)
- [x] Visual ring + dot feedback on sticks
- [x] Analog triggers
- [x] Customizable layout
- [x] Undo / Redo
- [x] Multi-page layouts
- [x] Desktop monitor
- [ ] Mapping device Gyro into different analog inputs
- [ ] Keyboard & mouse input support
- [ ] Multi Virtual Controller Support
- [ ] Macro / rapid-fire support
- [ ] Bundle whole project into a simple `.exe` file

---

## Contributing

Contributions are welcome! Here's how to help:

1. **Fork** the repository
2. **Create a branch** (`git checkout -b feature/my-feature`)
3. **Make your changes** — see [Development](#development) for guidance
4. **Test** manually by running the server and connecting a phone
5. **Submit a PR** with a clear description of your changes

**Ideas for contributions:**
- Add a formal test suite (pytest for backend, Playwright/Cypress for frontend)
- Implement keyboard/mouse input alongside gamepad
- Add Linux support (via `uinput` or similar)
- Add macOS support (via virtual gamepad kernel extension)
- Translate the client UI
- Macro / rapid-fire scripting
- Multi-controller support (multiple virtual gamepads)
- Gyro-to-stick mapping

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**TouchKeys** — Phone becomes gamepad. Zero install. Full analog. Open source.

</div>
