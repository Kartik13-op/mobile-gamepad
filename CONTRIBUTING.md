# Contributing to TouchKeys

Thank you for your interest in contributing to **TouchKeys**! We welcome contributions of all kinds, including bug reports, feature requests, layout designs, documentation updates, and code enhancements.

---

## 📜 Code of Conduct

This project adheres to the [TouchKeys Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

---

## How Can I Contribute?

### 1. Reporting Bugs
Before creating a bug report, please check existing issues to avoid duplicates. When filing an issue, please include:
- **A clear, descriptive title**
- **System details**: Windows version, browser name and version (on PC & mobile)
- **Steps to reproduce**: Clear step-by-step instructions to reproduce the problem
- **Expected vs. Actual behavior**
- **Console/Terminal logs**: Relevant output from the Python server window or browser developer tools
- **Gamepad state**: Whether the controller is visible in `joy.cpl`

### 2. Suggesting Features & Layouts
We love creative layout designs and feature proposals!
- Open a Feature Request issue detailing your idea.
- If proposing a new layout, share your JSON layout export along with screenshots.

### 3. Submitting Pull Requests (PRs)
1. **Fork the repository** and create your branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Set up the local development environment**:
   - Run `.\setup.ps1` in PowerShell to set up `.venv` and dependencies.
3. **Make your changes**:
   - Keep changes focused and clean.
   - Follow existing code styles (PEP 8 for Python, ES6+ modules for JavaScript).
4. **Test your changes**:
   - Verify server startup via `python backend/gui.py` or `launcher.py`.
   - Connect a phone over local Wi-Fi.
   - Check virtual controller responses in Windows Game Controllers utility (`joy.cpl`).
   - Test layout editing, saving, and loading if modifying the frontend.
5. **Commit your changes**:
   - Write clear, concise commit messages.
6. **Submit the PR**:
   - Fill out the Pull Request template completely.
   - Reference any related issues (e.g., `Fixes #12`).

---

## Project Structure & Architecture

```text
TouchKeys/
├── TouchKeys.exe         # Built launcher executable
├── launcher.py           # Entry launcher script
├── backend/              # FastAPI server & GUI runner
│   ├── gui.py            # Uvicorn manager & window launcher
│   ├── main.py           # App entry wrapper
│   └── server.py         # REST & WebSocket endpoints
├── controller/           # Core input handler, layout storage, virtual XInput driver
├── templates/            # HTML templates for mobile controller and monitor
├── static/               # Frontend JS modules and CSS styling
├── installers/           # Bundled Python Manager & ViGEmBus installers
├── images/               # Screenshots and media assets
└── layout.json           # Default button layout definition
```

---

## Coding Guidelines

- **Python**:
  - Follow [PEP 8](https://peps.python.org/pep-0008/) naming conventions.
  - Use type hints where practical.
  - Keep WebSocket packet handlers performant to avoid latency in gamepad input processing.
- **JavaScript / Frontend**:
  - Use modern vanilla JavaScript (ES modules). Avoid external JS heavy frameworks to maintain lightweight execution.
  - Ensure mobile pages render cleanly across multiple screen sizes and touch devices.
- **Documentation**:
  - Update `README.md` or docstrings if your changes modify configuration, default paths, or CLI behavior.

---

## Testing Checklist

Before submitting a PR, make sure to verify:
- [ ] Server launches without errors.
- [ ] Phone connects to WebSocket without dropping connections.
- [ ] Gamepad inputs show up in `joy.cpl`.
- [ ] No regression in layout editor functionality.

Thank you for helping make TouchKeys better! 🎮
