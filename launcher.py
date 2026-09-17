"""Small Windows launcher for the source-based TouchKeys application.

The packaged TouchKeys.exe is intentionally a launcher: the Python runtime and
dependencies are installed by setup.ps1, while the application remains in
backend/gui.py. This keeps the executable small and makes the source layout
easy to inspect and update.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _show_error(message: str) -> None:
    """Show an error even when this launcher was built without a console."""
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, "TouchKeys", 0x10)
    except Exception:
        print(message, file=sys.stderr)


def _find_python(project_dir: Path) -> list[str] | None:
    """Prefer the project venv, then Python Manager's ``py`` command."""
    venv_python = project_dir / ".venv" / "Scripts" / "python.exe"
    if venv_python.is_file():
        return [str(venv_python)]

    py = shutil.which("py")
    if py:
        return [py, "-3.12"]

    python = shutil.which("python")
    if python:
        return [python]

    return None


def main() -> int:
    if getattr(sys, "frozen", False):
        project_dir = Path(sys.executable).resolve().parent
    else:
        project_dir = Path(__file__).resolve().parent

    gui_path = project_dir / "backend" / "gui.py"
    if not gui_path.is_file():
        _show_error(f"TouchKeys could not find the application file:\n{gui_path}")
        return 1

    python_command = _find_python(project_dir)
    if python_command is None:
        _show_error(
            "Python was not found. Run setup.ps1 first, then start TouchKeys.exe again."
        )
        return 1

    try:
        # The launcher itself is built without a console. CREATE_NO_WINDOW is
        # also required here because the child is the regular python.exe;
        # without it Windows creates a second terminal window for gui.py.
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        subprocess.Popen(
            [*python_command, str(gui_path)],
            cwd=str(project_dir),
            creationflags=creation_flags,
        )
        return 0
    except OSError as exc:
        _show_error(f"TouchKeys could not start Python:\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
