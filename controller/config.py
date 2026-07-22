"""Application configuration management backed by settings.json."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict

from controller.storage import StorageManager

logger = logging.getLogger(__name__)

SETTINGS_FILE = "settings.json"


@dataclass
class AppConfig:
    """Typed application configuration with sensible defaults."""

    theme: str = "dark"
    accentColor: str = "#4a9eff"
    gridSize: int = 20
    snapToGrid: bool = True
    showGrid: bool = True
    animations: bool = True
    buttonShadows: bool = True
    hapticFeedback: bool = True
    soundFeedback: bool = False
    fullscreen: bool = False
    language: str = "en"
    autoSave: bool = True
    autoSaveInterval: int = 5000

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config to a plain dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AppConfig:
        """Create an AppConfig from a dictionary, ignoring unknown keys."""
        known_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


class ConfigManager:
    """Load, update, and persist application settings."""

    def __init__(self, storage: StorageManager) -> None:
        self.storage = storage
        self.config: AppConfig = self._load()

    def _load(self) -> AppConfig:
        """Load settings from disk or return defaults."""
        data = self.storage.read_json(SETTINGS_FILE)
        if data and isinstance(data, dict):
            return AppConfig.from_dict(data)
        return AppConfig()

    def save(self) -> bool:
        """Persist current settings to disk."""
        return self.storage.write_json(SETTINGS_FILE, self.config.to_dict())

    def update(self, data: Dict[str, Any]) -> AppConfig:
        """Merge partial updates into the current config and optionally auto-save."""
        for key, value in data.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        if self.config.autoSave:
            self.save()
        return self.config

    def get_dict(self) -> Dict[str, Any]:
        """Return the current settings as a plain dictionary."""
        return self.config.to_dict()
