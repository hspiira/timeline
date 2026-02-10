"""OAuth provider config, state, and audit log ORM models."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import AuditedMultiTenantModel


class OAuthProviderConfig(AuditedMultiTenantModel, Base):
    """OAuth provider credentials (versioned, envelope-encrypted). Table: oauth_provider_config."""

    __tablename__ = "oauth_provider_config"

    provider_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    superseded_by_id: Mapped[str | None] = mapped_column(String, nullable=True)
    client_id_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    client_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_key_id: Mapped[str] = mapped_column(String, nullable=False)
    redirect_uri: Mapped[str] = mapped_column(String, nullable=False)
    redirect_uri_whitelist: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    allowed_scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    default_scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    tenant_configured_scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    authorization_endpoint: Mapped[str] = mapped_column(String, nullable=False)
    token_endpoint: Mapped[str] = mapped_column(String, nullable=False)
    provider_metadata: Mapped[dict[str, str] | None] = mapped_column(
        JSON, nullable=True
    )
    health_status: Mapped[str] = mapped_column(
        String, nullable=False, default="unknown"
    )
    last_health_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_health_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    rate_limit_connections_per_hour: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=10
    )
    current_hour_connections: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    rate_limit_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "provider_type", "version", name="uq_tenant_provider_version"
        ),
        Index(
            "ix_oauth_provider_config_active", "tenant_id", "provider_type", "is_active"
        ),
    )


class OAuthState(Base):
    """OAuth state parameter (CSRF, expiration). Table: oauth_state."""

    __tablename__ = "oauth_state"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("tenant.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("app_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider_config_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("oauth_provider_config.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nonce: Mapped[str] = mapped_column(String, nullable=False)
    signature: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    consumed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    callback_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    return_url: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (Index("ix_oauth_state_expires", "expires_at", "consumed"),)


class OAuthAuditLog(Base):
    """Audit log for OAuth config changes. Table: oauth_audit_log.

    PII fields ip_address and user_agent are nullable and subject to
    data retention: run the OAuth audit PII purge job (see
    purge_oauth_audit_pii) after the configured retention period to
    anonymize (set to NULL) for GDPR compliance.
    """

    __tablename__ = "oauth_audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    provider_config_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    actor_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String, nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        server_default=func.now(),
    )
    changes: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # PII: subject to retention purge (anonymize after oauth_audit_pii_retention_days).
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("ix_oauth_audit_tenant_time", "tenant_id", "timestamp"),
        Index("ix_oauth_audit_config_time", "provider_config_id", "timestamp"),
    )
