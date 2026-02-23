"""NamingTemplate ORM model. Tenant-defined naming convention per scope (flow/subject/document)."""

from typing import Any

from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class NamingTemplate(MultiTenantModel, Base):
    """Naming template per scope. Table: naming_template.
    scope_type: flow | subject | document. scope_id: workflow_id, subject_type_id, or document_category_id.
    Unique (tenant_id, scope_type, scope_id).
    """

    __tablename__ = "naming_template"

    scope_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scope_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    template_string: Mapped[str] = mapped_column(String(500), nullable=False)
    placeholders: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )  # [{"key": "year", "source": "user_input"}, ...]

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "scope_type",
            "scope_id",
            name="uq_naming_template_tenant_scope",
        ),
    )
