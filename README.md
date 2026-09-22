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

---

## 📌 Overview

**TouchKeys** turns any smartphone or tablet into a fully customisable wireless gamepad for Windows PCs. 

By running a lightweight Python FastAPI server on your PC, TouchKeys serves an ultra-responsive web-based touchscreen interface over your local Wi-Fi network. Touch inputs sent over real-time WebSockets are mapped directly to virtual **Xbox 360 controllers** (powered by ViGEmBus) or mouse and keyboard events on your PC.

Whether you're missing an extra controller for couch co-op, need custom touch controls for PC gaming, or want a wireless touchpad for media control, TouchKeys provides a plug-and-play solution without requiring third-party mobile apps.

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

## 📥 Installation for Regular Users

Getting TouchKeys running on your Windows PC takes under 2 minutes:

> [!NOTE]
> End users do **not** need to manually install Python prior to setup! The included setup script automatically installs Python 3.12 via Python Manager into a self-contained local environment (`.venv`).

### Step-by-Step Setup

1. **Download & Extract**: Ensure your project folder contains `TouchKeys.exe`, `setup.ps1`, and the subdirectories (`backend`, `controller`, `static`, `templates`, `installers`).
2. **Run Setup**:
   - Right-click [`setup.ps1`](setup.ps1) and select **Run with PowerShell**.
   - *If PowerShell blocks execution*, open PowerShell in the project folder and run:
     ```powershell
     Set-ExecutionPolicy -Scope Process Bypass
     .\setup.ps1
     ```
3. **Automated Environment Provisioning**:
   The setup installer will automatically:
   - Install Python Manager from `installers\python-manager-26.3.msix`.
   - Provision Python 3.12 into a project-isolated `.venv`.
   - Install required dependencies from [`requirements.txt`](requirements.txt).
   - Launch the included **ViGEmBus driver installer** from `installers\`.
   - Place a **TouchKeys** shortcut on your Windows Desktop.
4. **Complete Driver Install**:
   Accept the Windows Administrator (UAC) prompt to complete the **ViGEmBus** driver installation. *(ViGEmBus allows Windows to present virtual Xbox 360 controllers to your games).*
5. **Launch & Connect**:
   - Double-click the **TouchKeys** desktop shortcut or root `TouchKeys.exe`.
   - Open the displayed LAN URL (e.g., `http://192.168.1.20:8000`) or scan the QR code on the PC monitor screen using your phone camera.

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
├── TouchKeys.exe                  # Root desktop launcher executable
├── launcher.py                    # Entry source used to generate TouchKeys.exe
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

`TouchKeys.exe` is a lightweight launcher executable. It locates the local `.venv` environment (or fallback Python installation) and launches `backend\gui.py`. This design keeps all Python source files and frontend assets fully transparent and modifiable without needing complete re-compilation.

To re-build the root launcher after modifying `launcher.py`:
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
- [ ] Low-latency WebRTC live PC screen streaming to mobile device
- [ ] Standalone single-file production executable distribution

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
