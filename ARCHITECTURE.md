# Architecture

TouchKeys is a **client-server system** that transforms a phone browser into a virtual Xbox 360 gamepad. The server runs on a Windows PC and emulates a physical controller via the ViGEmBus kernel driver. The client is a zero-install web application that communicates over WebSocket.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHONE BROWSER (Client)                            │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        index.html (SPA)                              │  │
│  │                                                                       │  │
│  │  ┌────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │  │
│  │  │  EventBus       │  │  WebSocketManager │  │  GamepadController   │  │  │
│  │  │  - pub/sub      │◄─┤  - connect/recon  │  │  - touch handlers    │  │  │
│  │  │  - decoupled    │  │  - heartbeat      │  │  - analog sticks     │  │  │
│  │  └────────────────┘  │  - latency         │  │  - triggers          │  │  │
│  │         ▲            └──────────────────┘  │  │  - multi-touch       │  │  │
│  │         │                                   │  └──────────┬───────────┘  │  │
│  │  ┌──────┴──────────────┐                   │             │              │  │
│  │  │   LayoutManager     │◄──────────────────┘             │              │  │
│  │  │  - render controls  │  WebSocket (wss://)             │              │  │
│  │  │  - page management  │  ┌──────────────────┐           │              │  │
│  │  │  - apply styles     │  │  JSON messages   │           │              │  │
│  │  └─────────────────────┘  │  - keydown/keyup │           │              │  │
│  │                           │  - analog (x,y)  │◄──────────┘              │  │
│  │  ┌─────────────────────┐  │  - layout data   │                          │  │
│  │  │  AppMobile           │  └──────────────────┘                          │  │
│  │  │  - lifecycle         │                                               │  │
│  │  │  - UI listeners      │                                               │  │
│  │  └─────────────────────┘                                               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                              WebSocket │ JSON
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PC SERVER (FastAPI)                                │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         server.py                                    │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌────────────┐  │  │
│  │  │ EventRouter  │  │ LayoutManager│  │ ConfigMgr  │  │Connection  │  │  │
│  │  │  - dispatch  │  │  - CRUD      │  │  - settings │  │  Manager   │  │  │
│  │  │  - handlers  │  │  - undo/redo │  │  - persist  │  │  - clients │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └────────────┘  │  - active   │  │  │
│  │         │                 │                            │  controller │  │  │
│  │         │                 ▼                            └────────────┘  │  │
│  │         │           ┌────────────┐                                     │  │
│  │         │           │ Storage    │                                     │  │
│  │         │           │  - JSON IO │                                     │  │
│  │         │           └────────────┘                                     │  │
│  │         ▼                                                              │  │
│  │  ┌────────────────┐                                                    │  │
│  │  │ Keyboard       │                                                    │  │
│  │  │  Controller    │                                                    │  │
│  │  │  (vgamepad)    │                                                    │  │
│  └─────────┬──────────┴──────────────────────────────────────────────────┘  │
│            │                                                               │
│            ▼                                                               │
│  ┌──────────────────┐                                                      │
│  │    ViGEmBus      │  Kernel-mode driver (part of Windows)                │
│  │    Driver        │                                                      │
│  └────────┬─────────┘                                                      │
│           │                                                               │
│           ▼                                                               │
│  ┌──────────────────┐                                                      │
│  │   XInput (API)   │  Games read controller state via XInput              │
│  └──────────────────┘                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Server-Side Components

#### `server.py` — Entry Point & HTTP Layer
- **Role**: FastAPI application with HTTP routes and a single WebSocket endpoint.
- **Lifespan**: Creates core singletons (`KeyboardController`, `LayoutManager`, `ConfigManager`, `ConnectionManager`, `EventRouter`) on startup; cleans up virtual controller on shutdown.
- **Single-instance lock**: Uses `.server.lock` PID file to prevent multiple server instances.
- **Routes**:
  - `GET /` — Mobile gamepad SPA
  - `GET /monitor` — Desktop live dashboard
  - `GET /api/ip`, `/api/keys`, `/api/clients`, `/api/debug` — REST API
  - `DELETE /api/clients/{id}` — Force-disconnect a client
  - `WebSocket /ws` — Real-time communication channel

#### `controller/events.py` — Event Router
- **Role**: Routes incoming WebSocket messages by their `type` field to typed handler methods.
- **Message types**: `keydown`, `keyup`, `analog`, `ping`, `save_layout`, `load_layout`, `update_layout`, `add_button`, `update_button`, `delete_button`, `duplicate_button`, `add_page`, `delete_page`, `rename_page`, `set_active_page`, `undo`, `redo`, `export_layout`, `import_layout`, `save_settings`, `load_settings`.
- **Per-client de-duplication**: Tracks pressed keys and analog values per client to suppress redundant state updates.
- **Active controller enforcement**: Only the active controller's input events drive the virtual gamepad.

#### `controller/keyboard.py` — Virtual Gamepad Driver
- **Role**: Thin wrapper around `vgamepad`'s `VX360Gamepad`.
- **Key mapping**: `XUSB_MAP` dictionary maps string key names (e.g., `gamepad_a`) to `vgamepad` button constants.
- **Button actions**: `press_button()` / `release_button()` with `dev.update()` to flush state.
- **Analog sticks**: `left_joystick()` / `right_joystick()` with ±32767 range scaling.
- **Triggers**: `left_trigger()` / `right_trigger()` with 0–255 range scaling, inverted Y-axis.
- **Lifecycle**: `ensure_controller()` lazily creates the virtual device; `reset()` zeroes all state.

#### `controller/layout.py` — Layout Manager
- **Role**: CRUD for control layouts with undo/redo support.
- **Data model**: Layout is a JSON object with `pages[]`, each containing `buttons[]` with typed controls.
- **Undo/Redo**: Command history stored in-memory with `_push_history()` snapshots; `undo()` / `redo()` restore.
- **Validation**: `validate_layout()` ensures structural integrity of imported layouts.
- **Default layout**: Loads from `default_gamepad.json` on first run when no `layout.json` exists.

#### `controller/network.py` — Connection Manager
- **Role**: Manages WebSocket connections, device names, and active controller promotion.
- **Active controller**: The first connected device becomes active; subsequent connections are passive until the active one disconnects.
- **Promotion chain**: When the active controller disconnects, the next waiting client is automatically promoted.
- **Broadcast**: Sends state updates (layout changes, input events) to all connected clients including monitors.

#### `controller/storage.py` — File I/O
- **Role**: Atomic JSON file reads and writes with backup creation.
- **Write strategy**: Writes to a `.tmp` file, then atomically renames — prevents corruption on crash.

#### `controller/config.py` — Configuration
- **Role**: Manages app-wide settings (auto-save toggle, etc.) with JSON persistence.

---

### 2. Client-Side Components (Browser)

All client code is inlined in `templates/index.html` for zero external dependencies.

#### `TK.EventBus` — Pub/Sub Event System
- Lightweight publish-subscribe bus decoupling all client modules.
- Events: `ws:connected`, `ws:disconnected`, `ws:latency`, `ws:layout`, `ws:session`, `ws:device_updated`, `ws:error`, `ws:save_result`, `ws:export_layout`, `layout:changed`, `layout:rendered`.

#### `TK.WebSocketManager` — WebSocket Client
- **Auto-reconnect**: Exponential backoff from 500ms to 8s base delay.
- **Heartbeat**: Sends `{type: "ping"}` every 3 seconds; measures round-trip latency.
- **JSON transport**: All messages serialized as JSON; `_handleMessage()` dispatches typed events to the EventBus.
- **Lifecycle**: `connect()` → `onopen` → heartbeat starts → `onmessage` → `onclose` → reconnect.

#### `TK.GamepadController` — Touch Input Handler
- **Touch classification**: Determines control type (button, analog_stick, trigger) from element dataset.
- **Button press**: Sends `keydown` on touch start, `keyup` on touch end.
- **Analog stick**: Tracks touch displacement from center; applies dead-zone (15%), throttle (16ms), and change-threshold (0.04) filtering.
- **Analog trigger**: Measures drag distance from initial touch point, normalizes to 0–1 range.
- **Multi-touch**: Maintains `Map` of active touches by touch identifier; supports simultaneous buttons, sticks, and triggers.
- **Haptic feedback**: `navigator.vibrate(10)` on button press.

#### `TK.LayoutManager` — Layout Renderer
- **Coordinate system**: All positions and sizes are ratios (0–1) relative to viewport width/height.
- **Rendering**: Creates DOM elements with absolute positioning and inline styles for precise control.
- **Control types**: `ctrl-btn` (button), `ctrl-analog` (analog stick), `ctrl-trigger` (trigger).
- **Responsive**: Uses `window.innerWidth` / `window.innerHeight` at render time; minimum 40px clamp prevents invisible controls.
- **Page tabs**: Renders tab navigation for multi-page layouts.

#### `AppMobile` — Application Controller
- **Orchestration**: Initializes all subsystems in order; sets up WebSocket event handlers; registers UI interaction listeners.
- **UI state**: Connection badge (ON/OFF), latency display, device name, settings modal, fullscreen toggle.
- **Browser prevention**: Disables context menu, gesture events (pinch-zoom), and overscroll for a native-app feel.

---

## WebSocket Protocol

### Message Format

All messages are JSON objects with a `type` field identifying the message kind.

### Client → Server

| Type | Fields | Description |
|------|--------|-------------|
| `hello` | `deviceName: string` | Sent after session to register device name |
| `keydown` | `key: string` | Press a button (e.g., `gamepad_a`) |
| `keyup` | `key: string` | Release a button |
| `analog` | `key: string`, `x: float`, `y: float` | Move analog stick (-1..1) or trigger (0..1) |
| `ping` | `timestamp: int` | Latency measurement |
| `save_layout` | `data: object` | Persist current layout |
| `load_layout` | — | Request layout from server |
| `update_layout` | `data: object` | Broadcast layout update |
| `add_button` | `pageId: string`, `data: object` | Create a new control |
| `update_button` | `pageId: string`, `buttonId: string`, `data: object` | Modify a control |
| `delete_button` | `pageId: string`, `buttonId: string` | Remove a control |
| `duplicate_button` | `pageId: string`, `buttonId: string` | Clone a control |
| `add_page` | `name: string` | Create a new page |
| `delete_page` | `pageId: string` | Remove a page |
| `rename_page` | `pageId: string`, `name: string` | Rename a page |
| `set_active_page` | `index: int` | Switch to a page |
| `undo` | — | Undo last layout change |
| `redo` | — | Redo last undone change |
| `export_layout` | — | Download layout as JSON |
| `import_layout` | `data: object` | Upload and apply a layout |
| `save_settings` | `data: object` | Persist settings |
| `load_settings` | — | Request settings |

### Server → Client

| Type | Fields | Description |
|------|--------|-------------|
| `session` | `clientId`, `deviceName`, `ip`, `isActive` | Connection acknowledgment |
| `layout` | `data: object` | Full layout state |
| `settings` | `data: object` | Full settings state |
| `active_page` | `index: int` | Page switch notification |
| `pong` | `timestamp: int`, `serverTime: int` | Heartbeat response |
| `connected` | — | WebSocket open event |
| `disconnected` | — | WebSocket close event |
| `latency` | `ms: int` | Measured round-trip time |
| `device_updated` | `clientId`, `deviceName`, `isActive` | Device registration confirmed |
| `controller_activated` | `message: string` | Promoted to active controller |
| `controller_changed` | `activeClientId`, `deviceName` | Active controller switched |
| `save_result` | `success: bool` | Save operation result |
| `error` | `message: string` | Error notification |
| `export_layout` | `data: object` | Layout data for download |
| `input` | `subtype`, `key`, `x`, `y` | Input event broadcast to monitors |

### Connection Lifecycle

```
Client                     Server
  │                          │
  │── WebSocket connect ────→│
  │                          │
  │←──── session (clientId) ─│
  │←──── layout (full) ──────│
  │←──── settings ───────────│
  │                          │
  │── hello (deviceName) ───→│
  │                          │
  │←──── device_updated ─────│
  │                          │
  │── keydown (gamepad_a) ──→│
  │── keyup (gamepad_a) ────→│
  │── analog (ls, x, y) ────→│
  │                          │
  │── ping (timestamp) ─────→│
  │←──── pong (serverTime) ──│
  │                          │
  │        ... time passes ...│
  │                          │
  │── disconnect ───────────→│
  │                          │
  │  (server promotes next)  │
```

---

## Input Pipeline

```
Touch Event (phone)
    │
    ▼
GamepadController._handleTouchStart / _handleTouchMove / _handleTouchEnd
    │
    ├── Button:  TK.ws.send({ type: "keydown", key: "gamepad_a" })
    ├── Trigger: TK.ws.send({ type: "analog", key: "gamepad_lt", x: 0.75, y: 0 })
    └── Stick:   TK.ws.send({ type: "analog", key: "gamepad_ls", x: 0.5, y: -0.3 })
    │
    ▼
WebSocket (JSON over TCP)
    │
    ▼
server.py → EventRouter.route()
    │
    ├── keydown → EventRouter._on_keydown()
    │    ├── Check active controller
    │    ├── Deduplicate (ignore if already pressed)
    │    └── keyboard.press_key(key) → vg.press_button() + dev.update()
    │
    ├── keyup → EventRouter._on_keyup()
    │    ├── Check active controller
    │    ├── Deduplicate (ignore if not pressed)
    │    └── keyboard.release_key(key) → vg.release_button() + dev.update()
    │
    └── analog → EventRouter._on_analog()
         ├── Check active controller
         ├── Deduplicate (filter tiny/no-change moves)
         └── keyboard.move_analog(stick, x, y) → joystick/trigger update + dev.update()
    │
    ▼
ViGEmBus Kernel Driver
    │
    ▼
XInput API → Game sees Xbox 360 controller state
```

### Filtering Stages

| Stage | Location | Purpose |
|-------|----------|---------|
| Dead zone (15%) | Client | Suppress near-center stick noise |
| Throttle (16ms) | Client | Limit analog message rate |
| Change threshold (0.04) | Client | Skip tiny movements |
| Tiny-move filter | Server | Skip sub-0.01 changes within 50ms |
| Deduplication | Server | Ignore redundant keydown/keyup |

---

## Layout Format

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

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `name` | string | Display label |
| `keybind` | string | Gamepad input (e.g., `gamepad_a`, `gamepad_ls`) |
| `type` | enum | `button`, `analog_stick`, `trigger` |
| `x` | float | Horizontal position ratio (0 = left, 1 = right) |
| `y` | float | Vertical position ratio (0 = top, 1 = bottom) |
| `width` | float | Width ratio relative to viewport width |
| `height` | float | Height ratio relative to viewport height |
| `opacity` | float | 0–1 opacity |
| `fontSize` | int | Label font size in pixels |
| `layer` | int | Z-index stacking order |
| `visible` | bool | Show/hide toggle |

### Coordinate Calculation

```
// At render time on the client:
baseWidth  = window.innerWidth
baseHeight = window.innerHeight

pixelLeft  = ctrl.x      * baseWidth
pixelTop   = ctrl.y      * baseHeight
pixelWidth = ctrl.width  * baseWidth
pixelHeight= ctrl.height * baseHeight

// Minimum control size:
pixelWidth  = Math.max(pixelWidth,  40)
pixelHeight = Math.max(pixelHeight, 40)
```

---

## Design Decisions

### Why a Single HTML File?

The mobile client is delivered as a single self-contained HTML file with all CSS and JavaScript inlined. This eliminates:
- HTTP round-trips for external assets
- Module loading failures on older or restrictive browsers
- CORS issues
- CDN dependency

The trade-off is a larger initial payload (~41KB) vs. the benefit of guaranteed loading on any browser.

### Why WebSocket and Not WebRTC / HTTP Long-Poll?

- **Latency**: WebSocket provides sub-100ms message delivery with minimal overhead.
- **Bidirectional**: Both input events and layout sync flow over the same connection.
- **Simplicity**: No STUN/TURN servers, no signaling, no SDP negotiation.

### Why Server-Authoritative Layout?

The server holds the canonical layout state. Clients are rendering engines that display whatever layout the server sends. This ensures:
- **Consistency**: All clients (phone + monitor) see identical layouts.
- **Persistence**: Layout changes are saved server-side automatically.
- **Multi-device**: A phone and monitor can view the same layout simultaneously.

### Why vgamepad / ViGEmBus?

ViGEmBus is the de-facto Windows kernel driver for virtual gamepad emulation. It creates a device that appears as a genuine Xbox 360 controller to any application using XInput. Alternatives (like sending DirectInput or using `pygame`'s joystick API) either lack game compatibility or require additional software.

---

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Initial page load | ~41 KB (single HTTP request) |
| WebSocket message size | ~50–100 bytes per input event |
| Input latency (LAN) | <5ms network + ~1ms processing |
| Client throttle rate | ~60 Hz (16ms between analog updates) |
| Max concurrent touches | Device-dependent (typically 5–10) |
| Server throughput | 10,000+ events/second (single core) |
| Memory (server) | ~50 MB idle |
| Memory (client) | ~10–20 MB (browser tab) |

---

## Security Considerations

1. **No authentication**: The server is designed for local LAN use. No encryption, no login. Do not expose to the internet.
2. **Input validation**: Server validates all incoming message types, key names, and numeric ranges. Unknown message types are logged and dropped.
3. **Active controller isolation**: Only the active controller's input is processed; passive clients cannot inject input.
4. **No persistent state**: Layout files are stored on the local filesystem with no external database.
