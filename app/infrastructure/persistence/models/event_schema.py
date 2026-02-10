"""EventSchema ORM model. Payload validation contract per event_type with versioning."""

from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class EventSchema(MultiTenantModel, Base):
    """Event schema. Table: event_schema. Unique (tenant_id, event_type, version)."""

    __tablename__ = "event_schema"

    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    schema_definition: Mapped[dict[str, Any]] = mapped_column(
        "schema_json", JSON, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str | None] = mapped_column(
        String, ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "event_type", "version", name="uq_tenant_event_type_version"
        ),
    )
