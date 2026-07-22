"""Stale controller cleanup — no-op.

Previously this module restarted the ViGEmBus kernel driver via an
elevated PowerShell script, which triggered a UAC admin prompt on
every startup. The UAC prompt was removed because:

  - The server's shutdown() already resets the virtual controller,
    preventing stale devices under normal operation.
  - If a stale controller remains after a crash, restart the ViGEmBus
    driver manually via the included cleanup_controllers.ps1 script
    (run as Administrator).

Returns True (pretend success) so callers don't log warnings.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def cleanup_stale_controllers() -> bool:
    """No-op. Returns True to avoid spurious warnings."""
    logger.info("Stale controller cleanup skipped (manual only).")
    return True
