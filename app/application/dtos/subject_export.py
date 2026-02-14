"""DTOs for subject data export (GDPR-style)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class SubjectExportResult:
    """Structured export of all data linked to a subject (no binary)."""

    subject: dict[str, Any]
    events: list[dict[str, Any]]
    documents: list[dict[str, Any]]
    exported_at: datetime
