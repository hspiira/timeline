"""Input sanitization utilities for XSS and injection prevention."""

import re
from typing import Any, ClassVar

import nh3


class InputSanitizer:
    """
    Sanitize user inputs to prevent XSS and injection attacks.

    Use parameterized queries as the primary defense; these helpers
    add a second layer for display and validation.
    """

    ALLOWED_TAGS: ClassVar[list[str]] = []
    ALLOWED_ATTRIBUTES: ClassVar[dict[str, list[str]]] = {}
    IDENTIFIER_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_-]+$")
    SQL_SAFE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_\-\s]+$")

    @classmethod
    def sanitize_html(cls, value: str) -> str:
        """Remove all HTML tags and sanitize with nh3 (strict by default).

        Args:
            value: Raw string that may contain HTML.

        Returns:
            Sanitized string safe for HTML display.
        """
        if not value:
            return value
        # nh3: tags = set of allowed tag names; attributes = dict[tag, set[attr]]
        attrs = {k: set(v) for k, v in cls.ALLOWED_ATTRIBUTES.items()}
        return nh3.clean(
            value,
            tags=set(cls.ALLOWED_TAGS),
            attributes=attrs,
        )

    @classmethod
    def sanitize_identifier(cls, value: str) -> str:
        """Sanitize identifiers (IDs, codes). Allows alphanumeric, underscore, hyphen.

        Args:
            value: Raw identifier string.

        Returns:
            The same string if valid.

        Raises:
            ValueError: If format is invalid.
        """
        if not value:
            return value
        if not cls.IDENTIFIER_PATTERN.match(value):
            raise ValueError("Invalid identifier format")
        return value

    @classmethod
    def sanitize_sql_string(cls, value: str) -> str:
        """Allowlist-based SQL string validation. Rejects invalid input; no lossy transform.

        Always use parameterized queries as primary defense.

        Args:
            value: User-provided string.

        Returns:
            The same string if it matches the safe pattern.

        Raises:
            ValueError: If string contains characters outside the allowlist.
        """
        if not value:
            return value
        if not cls.SQL_SAFE_PATTERN.match(value):
            raise ValueError("Unsafe SQL string")
        return value

    @classmethod
    def sanitize_dict(
        cls,
        data: dict[str, Any],
        max_depth: int = 100,
    ) -> dict[str, Any]:
        """Recursively sanitize string values in a dict.

        Args:
            data: Dictionary to sanitize.
            max_depth: Maximum recursion depth (default 100).

        Returns:
            New dict with string values sanitized.

        Raises:
            ValueError: If max_depth <= 0 or recursion exceeds max_depth.
        """
        if max_depth <= 0:
            raise ValueError("Maximum recursion depth exceeded or invalid max_depth")
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = cls.sanitize_html(value)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, max_depth=max_depth - 1)
            elif isinstance(value, list):
                sanitized[key] = cls.sanitize_list(value, max_depth=max_depth - 1)
            else:
                sanitized[key] = value
        return sanitized

    @classmethod
    def sanitize_list(
        cls,
        data: list[Any],
        max_depth: int = 100,
    ) -> list[Any]:
        """Recursively sanitize string values in a list.

        Args:
            data: List to sanitize.
            max_depth: Maximum recursion depth (default 100).

        Returns:
            New list with string values sanitized.

        Raises:
            ValueError: If max_depth <= 0 or recursion exceeds max_depth.
        """
        if max_depth <= 0:
            raise ValueError("Maximum recursion depth exceeded or invalid max_depth")
        sanitized = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(cls.sanitize_html(item))
            elif isinstance(item, dict):
                sanitized.append(cls.sanitize_dict(item, max_depth=max_depth - 1))
            elif isinstance(item, list):
                sanitized.append(cls.sanitize_list(item, max_depth=max_depth - 1))
            else:
                sanitized.append(item)
        return sanitized


def sanitize_input(
    value: str | dict | list,
    *,
    max_depth: int = 100,
) -> str | dict | list:
    """Sanitize any input value (string, dict, or list).

    Args:
        value: Value to sanitize.
        max_depth: Max recursion depth for dict/list (default 100).

    Returns:
        Sanitized value (new structure for dict/list).
    """
    if isinstance(value, str):
        return InputSanitizer.sanitize_html(value)
    if isinstance(value, dict):
        return InputSanitizer.sanitize_dict(value, max_depth=max_depth)
    if isinstance(value, list):
        return InputSanitizer.sanitize_list(value, max_depth=max_depth)
    return value


def validate_identifier(value: str) -> str:
    """Validate and return identifier; raises ValueError if invalid."""
    return InputSanitizer.sanitize_identifier(value)
