<div align="center">

  <img src="static/favicon.png" alt="TouchKeys Logo" width="96" height="96" />

  # TouchKeys 🎮
  ### Turn your smartphone into a high-performance Windows XInput gamepad & controller.

  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D4?logo=windows)](https://www.microsoft.com/windows)
  [![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![Code of Conduct](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)
  [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

  [Features](#-features) • [Screenshots](#-screenshots) • [Installation](#-installation-for-regular-users) • [Troubleshooting](#-troubleshooting) • [Contributing](CONTRIBUTING.md)

</div>

## 🌐 Project Website

Visit the **[TouchKeys landing page](https://kartik13-op.github.io/mobile-gamepad/)** for the complete product overview, local input pipeline, screenshots, downloads, setup instructions, architecture notes, troubleshooting, and roadmap.

The website is built from the repository's [`docs/`](docs/) folder and is intended to be the visual front door for the project. This README remains the detailed, source-linked reference for contributors and users who prefer a text-first format.

---

## 📌 Overview

**TouchKeys** turns any smartphone or tablet into a customisable wireless controller for a Windows PC. The phone does not need a special app: it opens a normal webpage hosted by the PC, and that webpage becomes the controller.

### 🔄 How the local Wi-Fi pipeline works

TouchKeys is designed to keep the entire control path inside your home or office network:

```text
Windows PC
  ├─ TouchKeys starts a local FastAPI web server on port 8000
  ├─ `/monitor` shows the desktop dashboard and connection QR code
  └─ `/` serves the mobile controller webpage
          ▲                         │
          │ HTTP loads the page     │ WebSocket sends live input
          │                         ▼
Smartphone or tablet on the same Wi-Fi network
          │
          └─ Touches become button, stick, trigger, mouse, or keyboard events
                                      │
                                      ▼
Windows input layer
  ├─ ViGEmBus creates a virtual Xbox 360 controller for compatible games
  └─ pyautogui sends configured mouse and keyboard actions
```

Here is what happens after launch:

1. TouchKeys starts a small web server on the PC and binds it to the local network. It displays the PC's local address, such as `http://192.168.1.20:8000`, and provides the same address as a QR code.
2. The phone and PC connect to the same Wi-Fi network. Scanning the QR code, or entering the address manually, loads the controller webpage from the PC. No cloud account, internet connection, or mobile installation is required for the controller itself.
3. The webpage renders the current layout and opens a persistent WebSocket connection back to the PC. This keeps the connection open for fast, two-way communication instead of submitting a new web request for every button press.
4. Every touch is translated in the browser into a small event: a button press/release, an analog-stick position, a trigger value, a mouse gesture, or a keyboard binding. The server identifies the connected device and assigns it one of controller slots `0`–`3`.
5. The PC processes the event locally. Gamepad events are sent through `vgamepad` to the ViGEmBus driver, which exposes a virtual Xbox 360 controller to Windows and games. Mouse and keyboard events are sent to Windows through the configured input handler.
6. The desktop monitor stays connected as another WebSocket client. It receives connection status, layout changes, input activity, and latency information, so the PC can manage connected phones and edit the shared control layout while the controller is in use.

The result is a direct **phone → local Wi-Fi → PC → Windows input** pipeline. Touch data is not routed through a remote server, and the project does not require a database, login system, companion mobile app, or separate backend service. The only Windows-level prerequisite is the one-time ViGEmBus driver installation for virtual Xbox controller output.

TouchKeys is useful for couch co-op, custom controls, accessibility setups, media control, and situations where a physical gamepad is not available.

---

## 🖼️ Screenshots & Showcase

<div align="center">

### 📱 Mobile Gamepad Interface
*Customisable, multi-touch layout with dual analog joysticks, D-Pad, triggers, and action buttons.*

![Mobile Gamepad Interface](images/mobile.jpeg)

<br/>

### 🖥️ PC Monitor & Dashboard
*QR code scanner for instant connection, active client manager, and live latency diagnostics.*

![PC Monitor Dashboard](images/dashboard.png)

<br/>

### ✏️ Drag-and-Drop Layout Editor
*Add, move, resize, duplicate, keybind, and re-theme controls right from your browser.*

![Layout Editor](images/editor.png)

<br/>

### 🧪 Live Gamepad Input Tester
*Real-time browser tester to verify button states and analog stick precision.*

![Gamepad Input Tester](images/tester.png)

</div>

---

## ✨ Features

- **🎮 Virtual Xbox 360 Controller**: Full XInput emulation (A/B/X/Y, D-Pad, dual analog joysticks, bumpers, triggers, Start, Back, and Guide).
- **👥 Multi-Player Co-Op**: Connect up to **4 simultaneous phone controllers** (Slots `0`–`3`) for multiplayer local gaming.
- **🖱️ Touchpad & Mouse Mode**: High-precision cursor navigation, scrolling, left/right clicks, and custom touchpad joystick modes.
- **⌨️ Keyboard & Hotkey Bindings**: Map touchscreen controls directly to PC keyboard keys or custom combos.
- **🎨 Visual Layout Editor**: Full drag-and-drop layout customization (add, move, resize, rename, keybind, undo/redo, import, and export).
- **⚡ Ultra-Low Latency**: Built on FastAPI and WebSockets with automated heartbeats, minimal latency overhead, and auto-reconnect logic.
- **📱 Zero App Installation**: Runs directly inside Chrome, Safari, Firefox, or Edge on iOS, Android, or tablet devices.
- **🖥️ Desktop Control Center**: Dedicated `/monitor` view with QR code generator, client status roster, and integrated gamepad tester.

---

## 📥 Installation and Running

Choose the standalone executable for the quickest setup, or use the source package if you want to inspect or modify the project.

### Option A — Standalone executable

1. Download `TouchKeys.exe` from the GitHub release and place it in a new folder.
2. Install the **ViGEmBus** driver as Administrator. The driver installer is in the source ZIP under `installers\`; maintainers may also attach it as a separate release asset.
3. Double-click `TouchKeys.exe`. Allow Windows Firewall access on Private networks if prompted.
4. Connect the phone and PC to the same Wi-Fi network, then scan the displayed QR code or open the displayed `http://192.168.x.x:8000` address.

The standalone executable already contains Python, TouchKeys, the controller code, templates, static assets, and Python dependencies. Python and `.venv` are not required. ViGEmBus remains a separate Windows driver required for virtual Xbox controller output.

### Option B — Source package

1. Download and extract the source ZIP.
2. Open PowerShell in the extracted project folder.
3. Run:
   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\setup.ps1
   ```
4. Approve the administrator prompt for ViGEmBus. Setup provisions Python 3.12, creates `.venv`, installs dependencies, builds a local standalone `TouchKeys.exe`, and creates a desktop shortcut.
5. Launch the generated `TouchKeys.exe`, then connect your phone using the displayed URL or QR code.

To run the source directly after setup:

```powershell
.\.venv\Scripts\python.exe .\backend\gui.py
```

To rebuild the executable after changing the source:

```powershell
.\build.ps1
```

---

## 🛠️ System Requirements

- **PC Operating System**: Windows 10 or Windows 11 (64-bit)
- **Network**: PC and mobile device connected to the same Wi-Fi / Local Area Network (LAN)
- **Mobile Device**: Modern mobile browser (Safari, Chrome, Firefox, Edge, or Brave)
- **Permissions**: Administrator rights for the one-time ViGEmBus driver installation

---

## 🧱 Architecture & Repository Structure

TouchKeys operates as a standalone launcher coupled with a FastAPI backend server:

```text
TouchKeys/
├── TouchKeys.exe                  # Locally generated launcher (ignored by Git)
├── launcher.py                    # Legacy source-based launcher
├── main.spec                     # PyInstaller specification file
├── build.ps1                     # Maintainer launcher build script
├── setup.ps1                     # End-user setup and desktop shortcut generator
├── backend/
│   ├── gui.py                    # Starts Uvicorn server & opens monitor window
│   ├── main.py                   # Server application wrapper
│   └── server.py                 # FastAPI routes & WebSocket event handler
├── controller/                   # Virtual XInput handler, layout manager, storage
├── static/                       # Frontend JS ES modules, styles, and assets
│   ├── favicon.png               # Application icon asset
│   ├── css/                      # Controller & monitor stylesheets
│   └── js/                       # WebSockets, layout engine, & input handlers
├── templates/                    # Mobile controller & PC monitor HTML templates
├── installers/                   # Bundled Python Manager & ViGEmBus MSI installers
├── images/                       # Documentation & README showcase screenshots
├── layout.json                   # Active controller layout configuration
├── index.html                    # Standalone web informational page
├── ARCHITECTURE.md               # Technical architecture documentation
├── CONTRIBUTING.md               # Contributor & pull request guidelines
├── SECURITY.md                   # Security disclosures & network recommendations
├── CODE_OF_CONDUCT.md            # Community code of conduct
├── LICENSE                       # MIT Open Source License
└── requirements.txt              # Python package dependencies
```

### ⚙️ Launcher vs. Server Execution

`TouchKeys.exe` is a standalone PyInstaller executable generated locally by setup. It contains the Python runtime, backend, controller code, templates, and static assets, so end users do not need Python or `.venv` after setup. The ViGEmBus driver remains a separate installer because it is a Windows kernel driver.

To rebuild the standalone executable after modifying application code (setup also does this automatically):
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build.ps1
```

---

## 📂 Configuration & Data Files

TouchKeys maintains configuration files directly inside the project root:

| File | Description | Source Control |
| ---- | ----------- | -------------- |
| [`layout.json`](layout.json) | Active layout configuration, button placements, and keybinds | Tracked in Git |
| `settings.json` | Application UI preferences and server settings | Ignored (`.gitignore`) |
| `layout.json.bak` | Automated backup generated prior to layout modification | Ignored (`.gitignore`) |
| `.server.lock` | Process lock file enforcing single server instance execution | Ignored (`.gitignore`) |

---

## ❓ Troubleshooting

<details>
<summary><b>1. Desktop shortcut shows "Python was not found"</b></summary>
Run <code>.\setup.ps1</code> again in PowerShell and verify that <code>.venv\Scripts\python.exe</code> exists.
</details>

<details>
<summary><b>2. Mobile phone cannot connect to the server page</b></summary>
Ensure both PC and phone are connected to the exact same Wi-Fi network (not guest Wi-Fi). Verify that Windows Firewall permits traffic on private networks for Python / TouchKeys on port <code>8000</code>.
</details>

<details>
<summary><b>3. Game does not recognize the virtual controller</b></summary>
Make sure the <b>ViGEmBus</b> driver was installed successfully. Press <code>Win + R</code>, type <code>joy.cpl</code>, and press Enter. A virtual Xbox 360 controller should appear as soon as your mobile phone sends its first input event.
</details>

<details>
<summary><b>4. Controls fail in certain anti-cheat protected games</b></summary>
Some PC games with aggressive anti-cheat engines (e.g., Vanguard, Easy Anti-Cheat) restrict synthetic mouse or keyboard inputs injected via <code>pyautogui</code>. Virtual Xbox gamepad controls via ViGEmBus are widely supported.
</details>

<details>
<summary><b>5. QR code image does not render on PC monitor</b></summary>
The QR code is generated via <code>api.qrserver.com</code>. If your PC lacks active internet access, simply type the displayed local IP address (e.g., <code>http://192.168.1.X:8000</code>) directly into your phone browser.
</details>

---

## 🌐 Gyroscope & Sensor Note

> [!NOTE]
> **Why Gyro and Motion Sensor Integration was Dropped**: Modern mobile web browsers (Safari, Chrome) restrict access to hardware sensors (gyroscope, accelerometer) over insecure HTTP (`http://`). While HTTPS experiments with self-signed SSL certificates were evaluated, browser security policies created friction for local LAN usage. Motion controls remain disabled in the current HTTP pipeline for maximum compatibility.

---

## 🗺️ Roadmap

- [x] Core low-latency WebSocket input engine
- [x] Xbox 360 / XInput emulation via ViGEmBus
- [x] Multi-touch analog sticks, D-Pad, triggers, and action controls
- [x] Drag-and-drop browser Layout Editor with Undo/Redo
- [x] PC Monitor control center with QR connection & latency diagnostics
- [x] Support for up to 4 simultaneous virtual controllers
- [x] Mouse emulation & PC keyboard binding modes
- [x] Standalone single-file executable distribution
- [ ] Signed Windows release builds and a guided installer package
- [ ] Release packaging that bundles or streamlines ViGEmBus driver installation
- [ ] Automatic update and version-reporting flow
- [ ] Low-latency WebRTC live PC screen streaming to mobile device

---

## 🤝 Community & Standards

We welcome community contributions! Please review our community guidelines:

- **[Code of Conduct](CODE_OF_CONDUCT.md)** — Standards for an open and welcoming community.
- **[Contributing Guide](CONTRIBUTING.md)** — Instructions for submitting bug reports, features, and PRs.
- **[Security Policy](SECURITY.md)** — Network security model and private vulnerability reporting.
- **[Architecture Document](ARCHITECTURE.md)** — In-depth technical specs and data flow design.

---

## 📄 License

TouchKeys is open-source software licensed under the **[MIT License](LICENSE)**.

---

<div align="center">
  Crafted with ❤️ for gamers and tinkers. Happy gaming! 🕹️
</div>
