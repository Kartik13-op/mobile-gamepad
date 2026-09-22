# Security Policy

## Supported Versions

Only the latest release of TouchKeys on the `main` branch receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| Latest (`main`) | :white_check_mark: |
| Older commits | :x: |

---

##  Security Architecture & Network Model

TouchKeys is designed as a **local network utility** for low-latency gamepad emulation:

- **Local Network Scope**: The FastAPI server binds to `0.0.0.0:8000` to allow phones on the same Wi-Fi/LAN to send input events.
- **Authentication**: There is no built-in authentication or password protection on the web endpoints (`/` and `/monitor`).
- **Encryption**: Communication uses standard HTTP and unencrypted WebSockets (`ws://`). TLS/HTTPS is intentionally omitted to avoid self-signed certificate prompts on mobile browsers.
- **Input Injection**: TouchKeys interacts directly with virtual XInput drivers (`vgamepad` / ViGEmBus) and synthetic mouse/keyboard input generators (`pyautogui`).

> [!IMPORTANT]
> **TouchKeys should ONLY be run on trusted private local networks (Home Wi-Fi/LAN).** Do NOT expose port `8000` to the public internet, run on untrusted public Wi-Fi networks without firewall isolation, or forward ports on your router to the TouchKeys server.

---

## Reporting a Vulnerability

If you discover a security vulnerability in TouchKeys, please do **NOT** open a public issue.

Instead, report security concerns responsibly by following these steps:

1. **Email Contact**: Send an email describing the vulnerability to the repository maintainers or use GitHub's **Private Vulnerability Reporting** feature on the repository.
2. **Include Details**:
   - Description of the security issue
   - Proof of concept or steps to reproduce
   - Potential impact of the vulnerability
3. **Response Timeline**: Maintainers will acknowledge receipt within 48 hours and provide updates on resolution progress.

Thank you for helping keep TouchKeys safe and secure!
