"""Webhook subscription repository."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.webhook_subscription import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionForDispatch,
    WebhookSubscriptionResult,
    WebhookSubscriptionUpdate,
)
from app.domain.exceptions import ResourceNotFoundException
from app.infrastructure.persistence.models.webhook_subscription import (
    WebhookSubscription,
)
from app.infrastructure.persistence.repositories.base import BaseRepository


def _to_result(row: WebhookSubscription) -> WebhookSubscriptionResult:
    return WebhookSubscriptionResult(
        id=row.id,
        tenant_id=row.tenant_id,
        target_url=row.target_url,
        event_types=row.event_types or [],
        subject_types=row.subject_types or [],
        secret_present=bool(row.secret),
        active=row.active,
        created_at=row.created_at,
    )


def _to_dispatch_result(row: WebhookSubscription) -> WebhookSubscriptionForDispatch:
    return WebhookSubscriptionForDispatch(
        id=row.id,
        tenant_id=row.tenant_id,
        target_url=row.target_url,
        event_types=row.event_types or [],
        subject_types=row.subject_types or [],
        secret=row.secret,
        active=row.active,
        created_at=row.created_at,
    )


class WebhookSubscriptionRepository(BaseRepository[WebhookSubscription]):
    """Webhook subscription repository."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, WebhookSubscription)

    async def get_active_by_tenant(
        self, tenant_id: str
    ) -> list[WebhookSubscriptionForDispatch]:
        """Return active subscriptions for tenant (includes secret for signing)."""
        result = await self.db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.tenant_id == tenant_id,
                WebhookSubscription.active.is_(True),
            )
        )
        rows = result.scalars().all()
        return [_to_dispatch_result(r) for r in rows]

    async def get_by_id_for_dispatch(
        self, tenant_id: str, subscription_id: str
    ) -> WebhookSubscriptionForDispatch | None:
        """Return subscription with secret for dispatch/test, or None."""
        result = await self.db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.id == subscription_id,
                WebhookSubscription.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        return _to_dispatch_result(row) if row else None

    async def create(
        self,
        tenant_id: str,
        data: WebhookSubscriptionCreate,
    ) -> WebhookSubscriptionResult:
        """Create a webhook subscription; returns the created record."""
        row = WebhookSubscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            target_url=data.target_url,
            event_types=data.event_types,
            subject_types=data.subject_types,
            secret=data.secret,
            active=True,
        )
        created = await super().create(row)
        return _to_result(created)  # read model: no secret, secret_present=True

    async def get_by_id(
        self, tenant_id: str, subscription_id: str
    ) -> WebhookSubscriptionResult | None:
        """Return subscription by id scoped to tenant, or None."""
        result = await self.db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.id == subscription_id,
                WebhookSubscription.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def list_by_tenant(
        self,
        tenant_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[WebhookSubscriptionResult]:
        """List subscriptions for tenant (paginated)."""
        result = await self.db.execute(
            select(WebhookSubscription)
            .where(WebhookSubscription.tenant_id == tenant_id)
            .order_by(WebhookSubscription.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        rows = result.scalars().all()
        return [_to_result(r) for r in rows]

    async def update(
        self,
        tenant_id: str,
        subscription_id: str,
        data: WebhookSubscriptionUpdate,
    ) -> WebhookSubscriptionResult:
        """Update subscription; raises if not found."""
        result = await self.db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.id == subscription_id,
                WebhookSubscription.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ResourceNotFoundException(
                WebhookSubscription.__tablename__, subscription_id
            )
        if data.target_url is not None:
            row.target_url = data.target_url
        if data.event_types is not None:
            row.event_types = data.event_types
        if data.subject_types is not None:
            row.subject_types = data.subject_types
        if data.secret is not None:
            row.secret = data.secret
        if data.active is not None:
            row.active = data.active
        updated = await super().update(row, skip_existence_check=True)
        return _to_result(updated)

    async def delete(self, tenant_id: str, subscription_id: str) -> None:
        """Delete subscription; raises if not found."""
        result = await self.db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.id == subscription_id,
                WebhookSubscription.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ResourceNotFoundException(
                WebhookSubscription.__tablename__, subscription_id
            )
        await super().delete(row)
