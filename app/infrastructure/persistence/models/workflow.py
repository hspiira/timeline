"""Workflow and WorkflowExecution ORM models. Event-driven automation."""

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    Index,
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import (
    AuditedMultiTenantModel,
    MultiTenantModel,
)
from app.shared.enums import WorkflowExecutionStatus


class Workflow(AuditedMultiTenantModel, Base):
    """Workflow definition. Table: workflow. Trigger + actions JSON."""

    __tablename__ = "workflow"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=sa.text("true")
    )
    trigger_event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    trigger_conditions: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    actions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    max_executions_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa.text("0")
    )


class WorkflowExecution(MultiTenantModel, Base):
    """Workflow execution audit. Table: workflow_execution."""

    __tablename__ = "workflow_execution"

    workflow_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("workflow.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triggered_by_event_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("event.id", ondelete="SET NULL"), nullable=True, index=True
    )
    triggered_by_subject_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("subject.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=WorkflowExecutionStatus.PENDING.value,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actions_executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actions_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_log: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index(
            "ix_workflow_execution_tenant_workflow",
            "tenant_id",
            "workflow_id",
        ),
        CheckConstraint(
            "status IN ({})".format(
                ", ".join(
                    "'{}'".format(v.replace("'", "''"))
                    for v in WorkflowExecutionStatus.values()
                )
            ),
            name="workflow_execution_status_check",
        ),
    )
