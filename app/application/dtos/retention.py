"""DTOs for retention run (document category-based soft-delete)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetentionRunResult:
    """Result of running document retention for a tenant."""

    tenant_id: str
    """Tenant that was processed."""

    soft_deleted_by_category: dict[str, int]
    """Category name -> number of documents soft-deleted."""

    @property
    def total_soft_deleted(self) -> int:
        """Total number of documents soft-deleted across all categories."""
        return sum(self.soft_deleted_by_category.values())
