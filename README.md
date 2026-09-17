# TouchKeys

TouchKeys runs a web-based controller on a phone and turns its input into Windows input on the PC. The PC hosts a FastAPI server; a phone on the same LAN opens the mobile page and sends JSON events over a WebSocket. Gamepad events are written to virtual Xbox 360 controllers through `vgamepad` and ViGEmBus. Optional keyboard and mouse events are injected with `pyautogui`.

The project has two browser interfaces:

- `/` is the phone controller.
- `/monitor` is the PC control center with the QR code, client list, layout editor, diagnostics, and browser gamepad tester.

## Important release behavior

The root `TouchKeys.exe` is a small launcher, not a bundled Python runtime. It looks for the project’s `.venv` first and then Python Manager’s `py` command, and starts `backend\gui.py`. Run `setup.ps1` once before using the executable.

This arrangement is intentional for the current release: the Python source and web assets remain visible in the project folder, while the executable provides a familiar desktop shortcut entry point.

## Features

- Xbox 360/XInput buttons, D-pad, sticks, triggers, and Guide input on Windows
- Up to four controller WebSocket clients, assigned slots `0`–`3`
- Monitor-only WebSocket role that does not consume a controller slot
- Multiple JSON layout pages
- Layout editing: add, move, resize, rename, duplicate, delete, undo, redo, import, and export
- Button, analog-stick, trigger, slider, and touchpad controls
- Touchpad joystick mode and PC mouse mode: cursor movement, scrolling, left click, and right click
- Keyboard bindings using `key_*` controls
- WebSocket heartbeat, latency display, reconnect behavior, and disconnect cleanup

TouchKeys is intended for a trusted local network. The server binds to `0.0.0.0:8000`, has no authentication, and uses HTTP/WebSocket by default. It does not provide TLS or Internet-facing access control.

## Installation for regular users

1. Make sure the project folder contains `TouchKeys.exe`, the `backend`, `controller`, `static`, `templates`, and `installers` folders, and `setup.ps1`.
2. Right-click [`setup.ps1`](setup.ps1) and select **Run with PowerShell**. If Windows blocks the script, open PowerShell in this folder and run:

   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\setup.ps1
   ```

3. The setup window will explain each step. It will:
   - install the included Python Manager package from `installers\python-manager-26.3.msix`;
   - install the Python 3.12 runtime through Python Manager;
   - create the project-local `.venv` environment;
   - install the packages in [`requirements.txt`](requirements.txt);
   - open the included ViGEmBus installer from `installers\`;
   - create a `TouchKeys` shortcut on the current user’s Windows Desktop.
4. When the ViGEmBus installer appears, approve the Windows administrator prompt and finish that driver installer. ViGEmBus is required because it lets Windows expose the virtual Xbox controller to games.
5. Double-click the new desktop shortcut or the root `TouchKeys.exe`.
6. Open the displayed LAN URL, such as `http://192.168.1.20:8000`, on the phone. The monitor also shows a QR code for that URL.

The terminal window is expected: the launcher starts the Python server, and its messages help diagnose connection or driver problems. The scripts and launcher are local project files; they do not download the application from an unknown website. The only network package operation is Python’s normal `pip install` from `requirements.txt`.

### What the PowerShell files do

`setup.ps1` is the end-user setup script. It installs Python Manager from the file shipped in `installers`, asks Python Manager for Python 3.12, creates `.venv`, installs the listed dependencies, runs the bundled ViGEmBus driver installer with Windows’ normal UAC prompt, and creates `Desktop\TouchKeys.lnk` pointing to `TouchKeys.exe`. Re-running it is supported; an existing environment is reused and the shortcut is refreshed.

`build.ps1` is for the project maintainer, not normal users. It installs the build-only PyInstaller package into `.venv`, compiles the small root launcher using [`main.spec`](main.spec), writes `TouchKeys.exe` beside this README, and removes generated `build` and `dist` folders after the build.

## Requirements

- Windows
- A phone and PC that can reach each other on the same Wi-Fi/LAN
- A modern browser on the phone
- Administrator approval for the one-time ViGEmBus driver installation

End users do not need to install Python manually when following `setup.ps1`; the included Python Manager package performs that part. Python remains present in the project’s `.venv` because the current root executable is a launcher rather than a self-contained Python application.

## Build the launcher

Run setup first, then use an elevated or normal PowerShell window in the project folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build.ps1
```

The result is:

```text
TouchKeys/
├── TouchKeys.exe          # root launcher with the TouchKeys icon
├── backend/
├── controller/
├── installers/
├── static/
├── templates/
└── README.md
```

The launcher still needs `.venv` and the rest of the project beside it. This is different from a fully bundled PyInstaller application.

## Data files

Runtime files are read from the project directory:

- [`layout.json`](layout.json) — active layout, pages, and controls
- `settings.json` — application/UI settings; ignored by Git
- `layout.json.bak` — backup made before a layout write; ignored by Git
- `.server.lock` — temporary single-instance marker; ignored by Git

## Troubleshooting

- The shortcut does nothing or shows “Python was not found”: run `setup.ps1` again and confirm that `.venv\Scripts\python.exe` exists.
- Phone cannot connect: confirm both devices are on the same network, use the displayed LAN IP, and allow TouchKeys through Windows Firewall on a private network.
- No virtual controller appears: complete the ViGEmBus installer, then check `joy.cpl`. A virtual controller is created when a controller client sends its first input.
- Input does not reach the game: check the layout keybind and whether the game accepts XInput, keyboard, or mouse input. Compatibility with every game or anti-cheat system is not guaranteed.
- QR image is blank: it is requested from `api.qrserver.com`; use the displayed URL manually if that service is unavailable.
- A stale controller remains after a crash: normal shutdown releases and resets devices, but crash recovery is not automatic.

## Repository map

```text
TouchKeys/
├── TouchKeys.exe                  # Root launcher executable
├── launcher.py                    # Source used to build TouchKeys.exe
├── main.spec                     # PyInstaller spec for the launcher
├── build.ps1                     # Maintainer build script
├── setup.ps1                     # End-user setup and desktop shortcut
├── backend/
│   ├── gui.py                    # Starts Uvicorn and opens the monitor
│   ├── main.py                   # Direct/PyInstaller app entry wrapper
│   └── server.py                 # FastAPI routes and WebSocket endpoint
├── controller/                   # Input, layout, config, storage, networking
├── templates/                    # Mobile and monitor HTML
├── static/                       # Mobile ES modules and CSS
├── installers/                   # Python Manager and ViGEmBus installers
├── images/                       # Documentation images
├── layout.json                   # Checked-in example/user layout
├── index.html                    # Standalone informational page
└── requirements.txt              # Runtime Python dependencies
```

### Why Gyro and other sensor data integration was dropped?

The current architecture hosts an 'http://' webpage. Those pages are blocked to accessing sensor data in modern browsers like Safari and Chrome. I had also recently experimented with the gyro pipeline implementations; adding fake crets to enforce https, but none didnt work out.

# Roadmap

- [x] Core Pipeline
- [x] Xbox 360/XInput emulation
- [x] Multi-touch, analog controls, And other Control Types.
- [x] Custom layouts, pages, and undo/redo
- [x] Desktop monitor and controller tester
- [x] Up to four simultaneous virtual controllers
- [x] Keyboard and mouse input
- [ ] Live screen Streaming
- [ ] Standalone Production-Level executable distribution

## Contributing

Bug reports, layout ideas, documentation improvements, and pull requests are welcome. Please test changes by connecting a phone and checking the result in `joy.cpl`.

## License

TouchKeys is released under the [MIT License](LICENSE).
