"""Utility functions for TouchKeys."""

import uuid
from datetime import datetime, timezone


def generate_id() -> str:
    """Generate a short unique identifier."""
    return uuid.uuid4().hex[:12]


def timestamp_ms() -> int:
    """Get current UTC timestamp in milliseconds."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a numeric value between min and max bounds."""
    return max(min_val, min(max_val, value))
