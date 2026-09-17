"""TouchKeys application entry point for direct/PyInstaller builds."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from backend.gui import main

if __name__ == "__main__":
    main()
