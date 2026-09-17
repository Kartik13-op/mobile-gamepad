# TouchKeys architecture

## Runtime in one view

```text
TouchKeys.exe / launcher.py
        │
        └─ finds .venv\Scripts\python.exe (or Python Manager's py.exe)
             and starts backend\gui.py
        │
        ├─ backend\gui.py starts Uvicorn on 0.0.0.0:8000
        └─ opens http://localhost:8000/monitor in pywebview or a browser

Phone browser ── HTTP GET / ──> FastAPI ──> mobile.html
Phone browser ── WS /ws ───────> EventRouter ──> KeyboardController
                                                    │
                                      vgamepad VX360Gamepad
                                                    │
                                             ViGEmBus driver
                                                    │
                                             Windows XInput games

PC monitor ─── HTTP GET /monitor ──> monitor.html
PC monitor ─── WS /ws?role=monitor ─> connection/input/layout state

Phone mouse gestures ──────────────> EventRouter ──> pyautogui ──> Windows cursor/keys
```

The server is a single-process FastAPI application. Its module-level managers are shared by all HTTP requests and WebSocket connections. There is no database, external backend, login system, or separate mobile application.

## Startup and shutdown

1. The root `TouchKeys.exe` is built from `launcher.py`. It locates the project directory, prefers `.venv\Scripts\python.exe`, and starts `backend\gui.py`. If no virtual environment exists, it tries Python Manager’s `py -3.12` and then `python`.
2. `backend\gui.py` selects the runtime data directory, removes a stale launcher lock, and starts a daemon thread with a new asyncio event loop.
3. The thread runs Uvicorn with `backend.server.app`, bound to `0.0.0.0:8000`.
4. FastAPI’s lifespan acquires `.server.lock`, logs the LAN URL, and keeps the application alive.
5. `backend\gui.py` polls `/api/ip`, then opens `/monitor`.
6. On shutdown, the lifespan releases input, resets/frees virtual devices, releases keyboard keys, and removes `.server.lock`.

Running `backend\server.py` directly starts Uvicorn in the foreground. The current root executable does not bundle or execute the backend; it launches the installed project Python. `backend.server` nevertheless retains frozen-path handling for possible future packaging. Source assets and data resolve from the project directory.

## Server components

### `backend/server.py`

Creates the shared `StorageManager`, `ConfigManager`, `KeyboardController`, `LayoutManager`, `ConnectionManager`, and `EventRouter`. It serves `/static`, the two HTML pages, REST diagnostics, and `/ws`.

| Route | Purpose |
|---|---|
| `GET /` | Returns `templates/mobile.html`. |
| `GET /monitor` | Returns `templates/monitor.html`. |
| `GET /api/ip` | Returns the IP selected by the UDP socket detection helper. |
| `GET /api/keys` | Returns supported `gamepad_*`, trigger, and `key_*` names. |
| `GET /api/clients` | Returns connected client metadata and count. |
| `DELETE /api/clients/{client_id}` | Closes a client, releases its input/device slot, and promotes a waiting controller when applicable. |
| `GET /api/debug` | Returns controller count, connection count, and currently pressed keys. |
| `GET /static/...` | Serves CSS, JavaScript, and the favicon. |

The server is bound to all interfaces for LAN access. The default protocol is unencrypted HTTP and WebSocket; the JavaScript selects `wss://` only if the page itself was loaded over HTTPS.

### `controller/network.py`

`ConnectionManager` accepts WebSockets and stores `ClientInfo` records. Controller-role clients receive the first free slot from `0` through `3`; monitor-role clients (`role=monitor`) receive no slot. Clients have generated eight-character IDs and default names, which can be replaced by a `hello` message.

The first slotted client is marked active. If it disconnects, the first remaining controller-role client is promoted. This status is broadcast and shown in the UI.

Important current behavior: `EventRouter` checks whether a client has a slot, but does not check `is_active_controller` before applying input. Every slotted controller can therefore send events to its own virtual controller even when the UI says “waiting.” “Active” is a promotion/status label, not an exclusive input lock.

### `controller/events.py`

`EventRouter` dispatches incoming JSON by its `type` field. It keeps per-client pressed-key and analog caches to ignore duplicate key transitions and very small, very frequent analog updates. Input events are broadcast to other clients so the monitor can visualize them.

Incoming message types:

| Type | Main fields | Effect |
|---|---|---|
| `hello` | `deviceName` | Sets the client display name; handled by `server.py`. |
| `keydown` / `keyup` | `key` | Presses/releases gamepad, trigger, or `key_*` keyboard bindings. |
| `analog` | `key`, `x`, `y` | Updates a stick or trigger using normalized values. |
| `mouse` | `action`, optional `dx`, `dy` | Sends cursor, scroll, or click actions to `pyautogui`. |
| `ping` | `timestamp` | Produces `pong` with the original timestamp and server time. |
| `save_layout` / `load_layout` | optional `data` | Persists or returns the current layout. |
| `update_layout` | `data` | Replaces the layout and optionally auto-saves it. |
| `export_layout` / `import_layout` | `data` | Sends or validates/replaces layout JSON. |
| `undo` / `redo` | — | Changes in-memory layout history and broadcasts the result. |
| `add_button`, `update_button`, `delete_button`, `duplicate_button` | page/control IDs and data | Mutates controls and broadcasts the layout. |
| `add_page`, `delete_page`, `rename_page` | page ID/name | Mutates pages and broadcasts the layout. |
| `set_active_page` | `index` | Changes the shared active page index and broadcasts it. |
| `save_settings` / `load_settings` | optional `data` | Updates or returns application settings. |

Server-to-client messages include `session`, `layout`, `settings`, `pong`, `input`, `controller_changed`, `controller_activated`, `device_updated`, `active_page`, `save_result`, `export_layout`, and `error`.

### `controller/keyboard.py`

`KeyboardController` lazily creates one `vg.VX360Gamepad` per assigned slot. Button names map through `XUSB_MAP` to `vgamepad` constants. Sticks are scaled to the signed XInput range `-32767..32767`; browser positive Y is inverted. Triggers use `0..255`. Digital trigger presses set a trigger to maximum and releases set it to zero.

The class also owns `MouseController`. `key_*` bindings call `pyautogui.keyDown`/`keyUp`; `mouse` messages call relative movement, scrolling, or mouse-button functions. Per-slot pressed sets support disconnect cleanup.

### `controller/layout.py`

The layout is a dictionary with `version`, `activePageIndex`, and `pages`. Each page has an ID, name, and `buttons` array. “Buttons” is historical: entries can be buttons, analog sticks, triggers, sliders, or touchpads.

Positions are normalized `x`/`y` values from `0` to `1`; width and height are pixels. The manager migrates older pixel positions against an `800×600` reference and older fractional sizes to pixels. Validation checks the required outer page structure; control fields are interpreted mostly by the browser and input code.

Mutations push deep-copy snapshots into an in-memory history capped at 50 entries. Undo/redo history is not persisted. New pages load controls from `controller/default_gamepad.json`; a valid checked-in/runtime `layout.json` is loaded first, otherwise a generated default layout is used.

### `controller/config.py` and `controller/storage.py`

`ConfigManager` loads `settings.json` into `AppConfig`, filters unknown fields, and supports theme, grid, animation, haptic/sound, fullscreen, language, and auto-save settings. Settings are shared by monitor and mobile clients and written as JSON.

`StorageManager` resolves filenames beneath the runtime data directory. Before writing an existing file it copies it to `<name>.bak`, writes JSON to `<name>.tmp`, and replaces the destination. Read failures try the backup before returning the caller’s default.

## Browser clients

### Mobile client

`templates/mobile.html` is a shell that loads `/static/js/app.js` as an ES module and `/static/css/main.css`. The modules are:

- `app.js` initializes the UI, layout, controller, WebSocket handlers, and browser-default suppression.
- `websocket.js` opens `/ws`, sends a ping every three seconds, measures round-trip latency, and reconnects with a 500 ms to 8 s backoff.
- `layout.js` renders the active page and controls from server layout JSON.
- `controller.js` tracks multi-touch and pointer input and emits key, normalized analog, trigger, joystick-touchpad, and mouse events.
- `ui.js` updates connection, device, status, and latency indicators.
- `utils.js` provides the event bus and utility functions.

The mobile URL is the same origin as the page. An HTTP page uses `ws://host/ws`; an HTTPS page uses `wss://host/ws`.

### Monitor client

`templates/monitor.html` contains its own HTML, CSS, and JavaScript. It connects with `/ws?role=monitor`, receives session/layout/settings/controller-change/input broadcasts, and does not consume a gamepad slot. It also calls REST endpoints for diagnostics, client removal, server IP, and supported key names.

Its four areas are dashboard/QR, connected devices, layout editor, and controller tester. The tester uses the browser’s `navigator.getGamepads()` API; it does not create or emulate a controller itself.

The QR image is fetched from `https://api.qrserver.com/v1/create-qr-code/`; it is not generated locally by the server.

## Input pipeline

```text
touch/pointer
   ↓
controller.js normalizes gesture
   ├─ keydown/keyup {key}
   ├─ analog {key, x, y}
   └─ mouse {action, dx, dy}
   ↓ JSON over /ws
EventRouter identifies client → assigned slot
   ├─ KeyboardController → VX360Gamepad → ViGEmBus → XInput
   └─ MouseController → pyautogui → Windows keyboard/cursor
```

Analog values are touch/pointer-derived; there is no implemented gyroscope or motion-sensor pipeline. Browser haptic feedback is a short local `navigator.vibrate()` call when available and is not sent to the PC.

## Packaging and operational boundaries

`launcher.py` is compiled by `main.spec` into the root `TouchKeys.exe`. The resulting executable is a small launcher and intentionally does not bundle the Python runtime or application dependencies. `build.ps1` installs PyInstaller into `.venv`, writes the executable beside this README, and removes generated `build` and `dist` folders after the build. `setup.ps1` installs the runtime dependencies and ViGEmBus for end users.

The root `index.html` is not part of the FastAPI route table. It is a standalone informational page; the application’s `/` route serves `templates/mobile.html` instead.

- Windows is required for the ViGEmBus virtual gamepad path.
- The server has no authentication or authorization and should not be exposed to an untrusted network.
- Four is the maximum number of controller-role slots. A fifth controller can connect but has no slot and its input is ignored.
- Virtual devices are created on first input, not merely on WebSocket connection.
- Layout, settings, and connection state are process-local; there is no database or multi-process state store.
- Normal shutdown resets devices and releases keys. Unexpected termination may require manual cleanup.
