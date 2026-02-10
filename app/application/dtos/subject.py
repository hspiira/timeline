"""DTOs for subject use cases (no dependency on ORM)."""

from dataclasses import dataclass


@dataclass
class SubjectResult:
    """Subject read-model (result of get_by_id, get_by_id_and_tenant, create_subject, etc.)."""

    id: str
    tenant_id: str
    subject_type: str
    external_ref: str | None
