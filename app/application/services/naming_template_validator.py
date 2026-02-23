"""Naming template validation and parsing.

Validates a name against a template string (e.g. "{year}-{month}-{client_name}")
and parses placeholder values. Used for flow, subject, and document naming.
"""

import re
from typing import Any

from app.domain.exceptions import ValidationException


def parse_placeholders_from_template(template_string: str) -> list[str]:
    """Extract placeholder keys from template string, e.g. '{year}-{month}' -> ['year', 'month']."""
    return re.findall(r"\{(\w+)\}", template_string)


def template_to_regex(template_string: str) -> tuple[re.Pattern[str], list[str]]:
    """Convert template string to regex pattern and list of placeholder names.

    E.g. '{year}-{month}-{name}' -> (re.Pattern, ['year', 'month', 'name']).
    Placeholders match non-empty sequences of non-delimiter chars (no '-' or whitespace in middle).
    """
    parts = re.split(r"\{(\w+)\}", template_string)
    placeholders = re.findall(r"\{(\w+)\}", template_string)
    pattern_parts: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            pattern_parts.append(re.escape(part))
        else:
            # Placeholder: match one or more non-empty segments (allow alphanumeric, underscore)
            pattern_parts.append(f"(?P<{part}>[^\\s-]+)")
    pattern = "^" + "".join(pattern_parts) + "$"
    return re.compile(pattern), placeholders


def validate_and_parse(
    name: str, template_string: str, placeholders: list[dict[str, Any]] | None = None
) -> dict[str, str]:
    """Validate that name matches the template and return parsed placeholder values.

    Args:
        name: The name to validate (e.g. '2026-03-Acme-Corp').
        template_string: Template (e.g. '{year}-{month}-{client_name}').
        placeholders: Optional list of placeholder defs (e.g. [{"key": "year", "source": "user_input"}]).

    Returns:
        Dict of placeholder key -> value.

    Raises:
        ValidationException: If name does not match the template.
    """
    if not name or not name.strip():
        raise ValidationException("Name is required", field="name")
    try:
        pattern, keys = template_to_regex(template_string)
    except re.error as e:
        raise ValidationException(
            f"Invalid template: {e}",
            field="template_string",
        ) from e
    match = pattern.match(name.strip())
    if not match:
        raise ValidationException(
            f"Name does not match template. Expected pattern like: {template_string}",
            field="name",
        )
    return {k: match.group(k) for k in keys}
