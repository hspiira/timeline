"""DocumentRequirement ORM model. Required document categories per workflow (and optionally per step)."""

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class DocumentRequirement(MultiTenantModel, Base):
    """Document requirement: workflow (and optional step) requires a document category.
    Table: document_requirement.
    step_definition_id is null for flow-level requirements (no workflow_step table yet).
    """

    __tablename__ = "document_requirement"

    workflow_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("workflow.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_definition_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    document_category_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("document_category.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    min_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "workflow_id",
            "step_definition_id",
            "document_category_id",
            name="uq_document_requirement_workflow_step_category",
        ),
    )
