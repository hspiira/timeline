"""Retention API schemas."""

from pydantic import BaseModel


class RetentionRunResponse(BaseModel):
    """Response after running document retention for the current tenant."""

    tenant_id: str
    soft_deleted_by_category: dict[str, int]
    total_soft_deleted: int
