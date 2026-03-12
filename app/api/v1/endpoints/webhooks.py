"""Webhook subscription CRUD and test delivery API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.dependencies import (
    get_verified_tenant_id,
    get_webhook_dispatcher,
    get_webhook_read_permission,
    get_webhook_subscription_repo,
    get_webhook_subscription_repo_for_write,
    get_webhook_write_permission,
)
from app.application.dtos.webhook_subscription import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionResult,
    WebhookSubscriptionUpdate,
)
from app.application.interfaces.repositories import IWebhookSubscriptionRepository
from app.application.interfaces.webhook import IWebhookDispatcher
from app.domain.exceptions import ResourceNotFoundException
from app.schemas.webhook_subscription import (
    WebhookSubscriptionCreateRequest,
    WebhookSubscriptionCreateResponse,
    WebhookSubscriptionResponse,
    WebhookSubscriptionTestResponse,
    WebhookSubscriptionUpdateRequest,
)

router = APIRouter()


def _to_response(r: WebhookSubscriptionResult) -> WebhookSubscriptionResponse:
    """Map DTO to response (no plaintext secret)."""
    return WebhookSubscriptionResponse(
        id=r.id,
        tenant_id=r.tenant_id,
        target_url=r.target_url,
        event_types=r.event_types,
        subject_types=r.subject_types,
        secret_present=r.secret_present,
        active=r.active,
        created_at=r.created_at,
    )


@router.post(
    "/{tenant_id}/webhooks",
    response_model=WebhookSubscriptionCreateResponse,
    status_code=201,
    summary="Create webhook subscription",
)
async def create_webhook(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    body: WebhookSubscriptionCreateRequest,
    repo: Annotated[
        IWebhookSubscriptionRepository,
        Depends(get_webhook_subscription_repo_for_write),
    ],
    _: Annotated[object, Depends(get_webhook_write_permission)],
) -> WebhookSubscriptionCreateResponse:
    """Create a webhook subscription. Secret is returned only in this response."""
    data = WebhookSubscriptionCreate(
        target_url=str(body.target_url),
        event_types=body.event_types,
        subject_types=body.subject_types,
        secret=body.secret,
    )
    created = await repo.create(tenant_id, data)
    return WebhookSubscriptionCreateResponse(
        id=created.id,
        tenant_id=created.tenant_id,
        target_url=created.target_url,
        event_types=created.event_types,
        subject_types=created.subject_types,
        secret_present=True,
        active=created.active,
        created_at=created.created_at,
        secret=body.secret,
    )


@router.get(
    "/{tenant_id}/webhooks",
    response_model=list[WebhookSubscriptionResponse],
    summary="List webhook subscriptions",
)
async def list_webhooks(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    repo: Annotated[
        IWebhookSubscriptionRepository,
        Depends(get_webhook_subscription_repo),
    ],
    _: Annotated[object, Depends(get_webhook_read_permission)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[WebhookSubscriptionResponse]:
    """List webhook subscriptions for the tenant (newest first)."""
    items = await repo.list_by_tenant(tenant_id, skip=skip, limit=limit)
    return [_to_response(i) for i in items]


@router.get(
    "/{tenant_id}/webhooks/{subscription_id}",
    response_model=WebhookSubscriptionResponse,
    summary="Get webhook subscription",
)
async def get_webhook(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    subscription_id: str,
    repo: Annotated[IWebhookSubscriptionRepository, Depends(get_webhook_subscription_repo)],
    _: Annotated[object, Depends(get_webhook_read_permission)],
) -> WebhookSubscriptionResponse:
    """Get a webhook subscription by id."""
    sub = await repo.get_by_id(tenant_id, subscription_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")
    return _to_response(sub)


@router.patch(
    "/{tenant_id}/webhooks/{subscription_id}",
    response_model=WebhookSubscriptionResponse,
    summary="Update webhook subscription",
)
async def update_webhook(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    subscription_id: str,
    body: WebhookSubscriptionUpdateRequest,
    repo: Annotated[
        IWebhookSubscriptionRepository,
        Depends(get_webhook_subscription_repo_for_write),
    ],
    _: Annotated[object, Depends(get_webhook_write_permission)],
) -> WebhookSubscriptionResponse:
    """Partially update a webhook subscription."""
    data = WebhookSubscriptionUpdate(
        target_url=str(body.target_url) if body.target_url is not None else None,
        event_types=body.event_types,
        subject_types=body.subject_types,
        secret=body.secret,
        active=body.active,
    )
    try:
        updated = await repo.update(tenant_id, subscription_id, data)
        return _to_response(updated)
    except ResourceNotFoundException:
        raise HTTPException(
            status_code=404,
            detail="Webhook subscription not found",
        ) from None


@router.delete(
    "/{tenant_id}/webhooks/{subscription_id}",
    status_code=204,
    summary="Delete webhook subscription",
)
async def delete_webhook(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    subscription_id: str,
    repo: Annotated[
        IWebhookSubscriptionRepository,
        Depends(get_webhook_subscription_repo_for_write),
    ],
    _: Annotated[object, Depends(get_webhook_write_permission)],
) -> None:
    """Delete a webhook subscription."""
    await repo.delete(tenant_id, subscription_id)


@router.post(
    "/{tenant_id}/webhooks/{subscription_id}/test",
    response_model=WebhookSubscriptionTestResponse,
    summary="Send test delivery",
)
async def test_webhook(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    subscription_id: str,
    repo: Annotated[IWebhookSubscriptionRepository, Depends(get_webhook_subscription_repo)],
    dispatcher: Annotated[IWebhookDispatcher, Depends(get_webhook_dispatcher)],
    _: Annotated[object, Depends(get_webhook_write_permission)],
) -> WebhookSubscriptionTestResponse:
    """POST a test payload to the subscription URL. Returns whether delivery succeeded (2xx)."""
    sub = await repo.get_by_id_for_dispatch(tenant_id, subscription_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")
    delivered = await dispatcher.send_test(sub)
    return WebhookSubscriptionTestResponse(delivered=delivered)
