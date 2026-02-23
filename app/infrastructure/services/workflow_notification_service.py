"""Workflow notification: log-only sender and recipient resolver by role."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.services import (
    INotificationService,
    IWorkflowRecipientResolver,
)
from app.shared.telemetry.logging import get_logger
from app.shared.utils.datetime import utc_now

logger = get_logger(__name__)


class LogOnlyNotificationService:
    """INotificationService implementation that logs instead of sending email.

    Use when no SMTP is configured. Production can swap in an SMTP or queue-based implementation.
    """

    async def send(
        self,
        to_emails: list[str],
        subject: str,
        body: str,
    ) -> None:
        """Log the notification; no actual email sent."""
        recipients = list(to_emails or [])
        subject_preview = (subject or "")[:80]
        if not recipients:
            logger.info(
                "Workflow notify: no recipients, skipping send (subject=%r)",
                subject_preview,
            )
            return
        logger.info(
            "Workflow notify: would send to %d recipients (subject=%r)",
            len(recipients),
            subject_preview,
        )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Workflow notify recipients: %s (at %s)",
                recipients,
                utc_now().isoformat(),
            )
        logger.debug("Workflow notify body (first 500 chars): %s", (body or "")[:500])


class WorkflowRecipientResolver:
    """Resolves user email addresses by tenant and role code (for workflow notify)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_emails_for_role(self, tenant_id: str, role_code: str) -> list[str]:
        """Return distinct email addresses for users who have the given role in the tenant."""
        stmt = text("""
            SELECT DISTINCT u.email
            FROM app_user u
            JOIN user_role ur ON ur.user_id = u.id AND ur.tenant_id = u.tenant_id
            JOIN role r ON r.id = ur.role_id AND r.tenant_id = ur.tenant_id
            WHERE u.tenant_id = :tenant_id
              AND r.code = :role_code
              AND r.is_active = true
              AND u.is_active = true
              AND (ur.expires_at IS NULL OR ur.expires_at > now())
        """)
        result = await self.db.execute(
            stmt, {"tenant_id": tenant_id, "role_code": role_code}
        )
        rows = result.fetchall()
        return [row[0] for row in rows if row[0]]
