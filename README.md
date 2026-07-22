<div align="center">

# TouchKeys - Mobile Gamepad

### Turn any phone or tablet into a virtual Xbox 360 gamepad for your PC

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue)](https://github.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/)

**No installation on the phone. No app stores. No ads. Just a URL and a browser.**

[Features](#features) • [Quick Start](#quick-start) • [Usage](#usage) • [Architecture](ARCHITECTURE.md) • [Configuration](#configuration) • [Development](#development)

</div>

---

## Why TouchKeys?

Traditional phone-as-gamepad solutions require installing proprietary apps, dealing with bloatware, or paying for premium features. TouchKeys is different:

- **Zero-install client** — your phone needs nothing but a browser. Open a URL, and you have a full gamepad.
- **Real Xbox 360 emulation** — games see a genuine Xbox 360 controller via ViGEmBus driver. No key-mapping hacks, no compatibility layers.
- **Full analog control** — real analog sticks with dead-zone filtering, analog triggers with pressure-sensitive input.
- **Multi-touch** — press A, move the right stick, and pull the left trigger simultaneously. All at once.
- **Customizable layout** — every button, stick, and trigger can be positioned, resized, and themed. Multiple pages per game.
- **Ultra low latency** — WebSocket transport with 16ms throttle. Feels like a wired controller on a good WiFi network.

---

## Features

### Gamepad Emulation
- **Complete Xbox 360 controller** — A, B, X, Y, D-pad (up/down/left/right), LB, RB, LT, RT, LS, RS, BACK, START, HOME (Guide)
- **Analog triggers** — touch-and-drag for smooth 0–1 analog range; games see real trigger axis input
- **Dual analog sticks** — with configurable dead zone (default 15%), 16ms throttle, and change-threshold filtering for jitter-free control
- **Virtual controller via ViGEmBus** — appears as a genuine Xbox 360 controller in `joy.cpl` and every XInput-compatible game

### Client Experience
- **Zero-install web app** — open a URL; no app store, no APK, no sideloading
- **Single-page architecture** — all JavaScript and CSS inlined in one ~41KB HTML file
- **Multi-touch** — unlimited simultaneous touches (device-dependent); press any combination of controls
- **Haptic feedback** — vibration on button press (devices that support `navigator.vibrate`)
- **PWA ready** — "Add to Home Screen" for fullscreen standalone mode
- **Auto-reconnect** — WebSocket reconnects with exponential backoff (500ms → 8s)
- **Latency display** — real-time round-trip time in the toolbar

### Layout System
- **Fully customizable** — every control is positionable by ratio (0–1) relative to viewport
- **Three control types** — buttons, analog sticks, and analog triggers
- **Multiple pages** — create different layouts for different games, all sharing one virtual controller
- **Undo / Redo** — unlimited history for layout edits
- **Save / Load / Import / Export** — layouts persist as `layout.json`; share layouts as JSON files

### Server & Monitoring
- **Desktop monitor** — live dashboard at `/monitor` showing stick crosshairs, trigger bars, button states, and connected devices
- **REST API** — programmatic access to server state, connections, and diagnostics
- **Multi-client** — one active controller; monitors and passive clients can observe live input
- **Auto-promotion** — when the active controller disconnects, the next waiting client takes over instantly

---

## Quick Start

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Windows 10/11** | ViGEmBus kernel driver (installed automatically by `vgamepad`) |
| **Python 3.9+** | Tested with 3.9–3.13 |
| **WiFi network** | Phone and PC must be on the same LAN |
| **Modern phone browser** | Chrome, Safari, Edge, Firefox — any browser from the last 3 years |

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/touchkeys.git
cd touchkeys

# Install Python dependencies
pip install -r requirements.txt
```

### Running

**Option A: Standalone server (recommended)**

```bash
python server.py
```

**Option B: With desktop monitor GUI**

```bash
python gui.py
```

The server prints a URL like:
```
http://192.168.1.100:8000
```

Open that URL on your phone. A complete Xbox 360 gamepad layout appears automatically. Every button, stick, and trigger works immediately.

### What to Expect

1. **Phone**: Open the URL → toolbar shows OFF → changes to ON when connected → buttons appear
2. **PC**: Press a button on the phone → check `joy.cpl` → the virtual Xbox 360 controller responds
3. **Game**: Launch any XInput-compatible game → the virtual controller is recognized as Gamepad #1

---

## Usage

### Controls Reference

| Control | Touch Action | Network Message | Gamepad Effect |
|---------|-------------|-----------------|----------------|
| **A, B, X, Y** | Tap (press), release | `keydown` / `keyup` | Button press/release |
| **D-pad (▲▼◄►)** | Tap | `keydown` / `keyup` | D-pad press/release |
| **LB, RB** | Tap | `keydown` / `keyup` | Shoulder button |
| **LT, RT** | Touch + drag up/down | `analog` (x = 0–1) | Trigger axis |
| **LS, RS** | Drag in any direction | `analog` (x = -1..1, y = -1..1) | Joystick axis |
| **BACK, START** | Tap | `keydown` / `keyup` | Back / Start |
| **HOME** | Tap | `keydown` / `keyup` | Guide button |
| **Cog (⚙)** | Tap | — | Toggle toolbar visibility |
| **SET** | Tap | — | Open settings (haptic, fullscreen) |

### Multi-Touch

TouchKeys handles any number of simultaneous touches. You can:
- Hold **A** while dragging the **right stick** and pulling **RT**
- Press **LB + RB** simultaneously
- Move **both sticks** at the same time

Each touch is tracked by its `touch.identifier` across start/move/end events.

### Fullscreen Mode

- **Browser**: Tap the **SET** button, then **FULLSCREEN**
- **Safari (iOS)**: Add to Home Screen for a fullscreen PWA experience with no browser chrome
- **Chrome (Android)**: "Add to Home Screen" works similarly

---

## Configuration

### Layout JSON Format

The server reads and writes `layout.json` in the project root. Edit it to customize the default layout:

```json
{
  "version": 2,
  "activePageIndex": 0,
  "pages": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Standard",
      "buttons": [
        {
          "id": "550e8400-e29b-41d4-a716-446655440001",
          "name": "A",
          "keybind": "gamepad_a",
          "type": "button",
          "x": 0.50,
          "y": 0.55,
          "width": 0.15,
          "height": 0.15,
          "opacity": 1.0,
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

| Type | Class | Behavior |
|------|-------|----------|
| `button` | `.ctrl-btn` | Momentary press; flashes white on touch |
| `analog_stick` | `.ctrl-analog` | Circular drag zone; returns to center on release |
| `trigger` | `.ctrl-trigger` | Linear drag; analog value proportional to drag distance |

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

- **Positions** (`x`, `y`) are ratios from 0–1 relative to viewport width/height
- **Dimensions** (`width`, `height`) are ratios relative to viewport
- **Origin**: (0,0) is top-left; (1,1) is bottom-right
- **Minimum size**: Controls are clamped to 40×40px minimum

```
Example: A button at center that's 20% of screen width:
x = 0.40, y = 0.425, width = 0.20, height = 0.15
```

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
├── server.py                 # FastAPI application entry point
├── gui.py                    # Desktop monitor launcher (customtkinter)
├── requirements.txt          # Python dependencies
├── layout.json               # Saved control layout (auto-generated)
├── settings.json             # App settings (auto-generated)
├── ARCHITECTURE.md           # System architecture documentation
├── LICENSE                   # MIT license
│
├── controller/
│   ├── keyboard.py           # Virtual Xbox 360 gamepad driver (vgamepad)
│   ├── layout.py             # Layout CRUD, undo/redo, page management
│   ├── events.py             # WebSocket message routing & input dedup
│   ├── config.py             # Application configuration
│   ├── storage.py            # Atomic JSON file I/O
│   ├── network.py            # Connection manager & LAN IP detection
│   └── utils.py              # Shared utilities
│
├── templates/
│   └── index.html            # Mobile SPA (all JS/CSS inlined)
│
└── static/
    ├── css/main.css          # Reference stylesheet
    └── js/                   # Modular JS source files (reference)
```

---

## Troubleshooting

### Connection Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Phone shows "OFF" in toolbar | WebSocket not connected | Check WiFi — both devices must be on the same network |
| Page doesn't load | Network unreachable | Verify the IP printed by `server.py` matches your PC's LAN IP |
| Connection drops repeatedly | WiFi interference | Use 5 GHz band; move closer to router |
| "Only one usage of each socket address" | Server already running | Kill the old process with Task Manager on port 8000 |

### Controller Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Game doesn't respond | Wrong controller number | Check `joy.cpl` — touchkeys controller should appear; reorder if needed |
| Buttons press but don't release | Touch event not captured | Ensure `touch-action: none` is applied (it is by default) |
| Analog sticks jittery | Dead zone too low | Increase `ANALOG_DEAD_ZONE` in the client script (default 0.15) |
| No vibration | Device or browser limitation | Check `navigator.vibrate` support; haptic may not work on all devices |
| ViGEmBus driver error | Driver not installed | `pip install vgamepad` installs it; reboot if needed |

### Layout Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Buttons off-screen | Aspect ratio mismatch | Edit `layout.json` — positions are ratios; reduce `x`/`y` values |
| Buttons too small | Viewport too large | Minimum size is 40×40px; check `Math.max(wVal, 40)` in the styling code |
| Buttons not updating | Server cache | Restart the server to reload `layout.json` |

---

## Development

### Frontend

The entire frontend is in `templates/index.html` — a single self-contained HTML file. All JavaScript uses a `TK.*` namespace to avoid global pollution. The source is organized as:

| Section | Lines | Component |
|---------|-------|-----------|
| CSS | `<style>` | All styles inlined |
| `TK.*` utilities | First JS block | `generateId`, `clamp`, `debounce`, `throttle`, `snapToGrid`, `EventBus` |
| `TK.WebSocketManager` | — | WebSocket client with auto-reconnect |
| `TK.GamepadController` | — | Multi-touch input handling |
| `TK.LayoutManager` | — | Layout rendering and styling |
| `AppMobile` | Last block | Application orchestration |

**To modify**: Edit `templates/index.html` and restart the server. No build step, no bundler, no npm install.

### Backend

The Python server follows a simple singleton pattern:

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
3. Send the message from the client via `TK.ws.send({ type: "your_type", ... })`

### Running Tests

```bash
# No formal test suite yet — contributions welcome!
# Manual test: start server, connect phone, verify joy.cpl
```

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
- ES5 JavaScript (all browsers since 2012)
- Touch events (all modern touch devices)

---

## Benchmarks

| Metric | Measurement |
|--------|-------------|
| Page size | ~41 KB (gzipped ~14 KB) |
| Time to interactive | <500ms on modern phone |
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
- [x] Analog triggers
- [x] Customizable layout
- [x] Undo/Redo
- [x] Multi-page layouts
- [x] Desktop monitor
- [ ] Keyboard & mouse input support
- [ ] Multiple virtual controllers
- [ ] Bluetooth direct connect
- [ ] On-device layout editor
- [ ] Layout presets/themes
- [ ] Macro/rapid-fire support

---

## Contributing

Contributions are welcome! Here's how to help:

1. **Fork** the repository
2. **Create a branch** (`git checkout -b feature/my-feature`)
3. **Make your changes** — see [Development](#development) for guidance
4. **Test** manually by running the server and connecting a phone
5. **Submit a PR** with a clear description of your changes

**Ideas for contributions:**
- Add a formal test suite
- Implement keyboard/mouse input alongside gamepad
- Create a web-based layout editor (instead of editing JSON)
- Add Linux support (via `uinput` or similar)
- Improve the desktop monitor UI
- Translate the client UI

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**TouchKeys** — Phone becomes gamepad. Zero install. Full analog. Open source.

</div>
