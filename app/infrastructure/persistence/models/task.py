"""Task ORM model. Workflow-created task assignable to role or user."""

from datetime import datetime

from sqlalchemy import DateTime, Enum as SaEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import TaskStatus
from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class Task(MultiTenantModel, Base):
    """Task created by workflow (create_task action). Table: task."""

    __tablename__ = "task"

    subject_id: Mapped[str] = mapped_column(
        String, ForeignKey("subject.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("event.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_to_role_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("role.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_to_user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[TaskStatus] = mapped_column(
        SaEnum(
            TaskStatus,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            create_constraint=False,
        ),
        nullable=False,
        default=TaskStatus.OPEN,
        server_default=TaskStatus.OPEN.value,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_task_tenant_subject", "tenant_id", "subject_id"),
        Index("ix_task_assigned", "tenant_id", "assigned_to_user_id"),
    )
