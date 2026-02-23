"""RelationshipKind ORM model. Tenant-defined allowed relationship kinds."""

from typing import Any

from sqlalchemy import JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class RelationshipKind(MultiTenantModel, Base):
    """Allowed relationship kind per tenant. Table: relationship_kind.

    Unique (tenant_id, kind). When present, add_relationship validates
    relationship_kind against this list.
    """

    __tablename__ = "relationship_kind"

    kind: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "kind",
            name="uq_relationship_kind_tenant_kind",
        ),
    )
