"""EmailAccount ORM model. Integration metadata for email providers (Gmail, Outlook, IMAP)."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class EmailAccount(MultiTenantModel, Base):
    """Email account config and sync state. Table: email_account."""

    __tablename__ = "email_account"

    subject_id: Mapped[str] = mapped_column(
        String, ForeignKey("subject.id"), nullable=False, index=True
    )
    provider_type: Mapped[str] = mapped_column(String, nullable=False)
    email_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    credentials_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    connection_params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    oauth_provider_config_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    oauth_provider_config_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    granted_scopes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    webhook_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    gmail_history_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    history_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sync_status: Mapped[str] = mapped_column(String, nullable=False, default="idle", index=True)
    sync_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_messages_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sync_events_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sync_error: Mapped[str | None] = mapped_column(String, nullable=True)
    oauth_status: Mapped[str] = mapped_column(String, nullable=False, default="active", index=True)
    oauth_error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    oauth_next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_refresh_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_refresh_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_auth_error: Mapped[str | None] = mapped_column(String, nullable=True)
    last_auth_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
