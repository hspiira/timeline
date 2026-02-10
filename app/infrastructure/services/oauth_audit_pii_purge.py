"""OAuth audit log PII purge for GDPR compliance.

Anonymizes ip_address and user_agent in oauth_audit_log for rows older than
the configured retention period (oauth_audit_pii_retention_days). Run
periodically (e.g. daily cron or task scheduler): obtain an async DB session
(e.g. from get_db_transactional), call purge_oauth_audit_pii(db), then commit.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.persistence.models.oauth_provider_config import OAuthAuditLog
from app.shared.telemetry.logging import get_logger

logger = get_logger(__name__)


async def purge_oauth_audit_pii(
    db: AsyncSession,
    *,
    retention_days: int | None = None,
) -> int:
    """Anonymize PII (ip_address, user_agent) in OAuthAuditLog beyond retention.

    Sets ip_address and user_agent to NULL for rows whose timestamp is older
    than (now - retention_days). Use for GDPR-compliant data retention.

    Args:
        db: Async database session (caller should commit after).
        retention_days: Days to keep PII; if None, uses
            settings.oauth_audit_pii_retention_days.

    Returns:
        Number of rows updated (anonymized).
    """
    settings = get_settings()
    days = retention_days if retention_days is not None else settings.oauth_audit_pii_retention_days
    cutoff = datetime.now(UTC) - timedelta(days=days)

    stmt = (
        update(OAuthAuditLog)
        .where(OAuthAuditLog.timestamp < cutoff)
        .where(
            (OAuthAuditLog.ip_address.is_not(None))
            | (OAuthAuditLog.user_agent.is_not(None))
        )
        .values(ip_address=None, user_agent=None)
    )
    result = await db.execute(stmt)
    count = result.rowcount
    if count:
        logger.info(
            "OAuth audit PII purge: anonymized %s row(s) older than %s days",
            count,
            days,
        )
    return count or 0
