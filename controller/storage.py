"""File storage management with atomic writes and backup recovery."""

import json
import shutil
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class StorageManager:
    """Thread-safe JSON file storage with atomic writes and corruption recovery."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)

    def _resolve(self, filename: str) -> Path:
        """Resolve a filename to its absolute path within the base directory."""
        return self.base_dir / filename

    def read_json(self, filename: str, default: Any = None) -> Any:
        """Read and parse a JSON file, falling back to backup or default on failure.

        Args:
            filename: Relative path within base_dir.
            default: Value to return if the file is missing or corrupt.

        Returns:
            Parsed JSON data, backup data, or the provided default.
        """
        filepath = self._resolve(filename)
        try:
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            return default
        except (json.JSONDecodeError, IOError, OSError) as exc:
            logger.error("Failed to read %s: %s", filename, exc)
            # Attempt recovery from backup
            backup = filepath.with_suffix(filepath.suffix + ".bak")
            if backup.exists():
                try:
                    with open(backup, "r", encoding="utf-8") as fh:
                        logger.info("Recovered %s from backup", filename)
                        return json.load(fh)
                except Exception as backup_exc:
                    logger.error("Backup recovery also failed: %s", backup_exc)
            return default

    def write_json(self, filename: str, data: Any) -> bool:
        """Atomically write JSON data to a file with pre-write backup.

        Writes to a temporary file first, then renames to avoid partial writes.

        Args:
            filename: Relative path within base_dir.
            data: JSON-serializable data.

        Returns:
            True if the write succeeded, False otherwise.
        """
        filepath = self._resolve(filename)
        try:
            # Back up the existing file
            if filepath.exists():
                backup = filepath.with_suffix(filepath.suffix + ".bak")
                shutil.copy2(filepath, backup)

            # Write to temp, then atomic rename
            temp = filepath.with_suffix(filepath.suffix + ".tmp")
            with open(temp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)

            temp.replace(filepath)
            return True
        except (IOError, OSError, TypeError, ValueError) as exc:
            logger.error("Failed to write %s: %s", filename, exc)
            return False

    def file_exists(self, filename: str) -> bool:
        """Check whether a file exists within the base directory."""
        return self._resolve(filename).exists()
