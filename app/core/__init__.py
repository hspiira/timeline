"""Core: config, constants, and application bootstrap.

Single place for settings and shared constants.
"""

from app.core.config import get_settings, settings

__all__ = ["settings", "get_settings"]
