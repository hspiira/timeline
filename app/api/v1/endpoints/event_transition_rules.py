"""Event transition rule API: thin routes delegating to EventTransitionRuleRepository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.dependencies import (
    ensure_audit_logged,
    get_event_transition_rule_repo,
    get_event_transition_rule_repo_for_write,
    get_tenant_id,
    require_permission,
)
from app.core.limiter import limit_writes
from app.domain.exceptions import ValidationException
from app.infrastructure.persistence.repositories.event_transition_rule_repo import (
    EventTransitionRuleRepository,
)
from app.schemas.event_transition_rule import (
    EventTransitionRuleCreateRequest,
    EventTransitionRuleResponse,
    EventTransitionRuleUpdate,
)

router = APIRouter()

_MSG_RULE_NOT_FOUND = "Event transition rule not found"

# Optional fields on create and PATCH (single source for mapping body to repo/entity)
_CREATE_OPTIONAL_ATTRS = (
    "description",
    "prior_event_payload_conditions",
    "max_occurrences_per_stream",
    "fresh_prior_event_type",
)
_PATCH_OPTIONAL_ATTRS = (
    "required_prior_event_types",
    "description",
    "prior_event_payload_conditions",
    "max_occurrences_per_stream",
    "fresh_prior_event_type",
)


@router.post("", response_model=EventTransitionRuleResponse, status_code=201)
@limit_writes
async def create_event_transition_rule(
    request: Request,
    body: EventTransitionRuleCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    rule_repo: Annotated[
        EventTransitionRuleRepository, Depends(get_event_transition_rule_repo_for_write)
    ],
    _: Annotated[object, Depends(require_permission("event_schema", "create"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Create an event transition rule (tenant-scoped). One rule per event_type."""
    try:
        optional_kwargs = {
            k: getattr(body, k, None) for k in _CREATE_OPTIONAL_ATTRS
        }
        rule = await rule_repo.create_rule(
            tenant_id=tenant_id,
            event_type=body.event_type,
            required_prior_event_types=body.required_prior_event_types,
            **optional_kwargs,
        )
        return EventTransitionRuleResponse.model_validate(rule)
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=e.message) from e


@router.get("", response_model=list[EventTransitionRuleResponse])
async def list_event_transition_rules(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    rule_repo: Annotated[
        EventTransitionRuleRepository, Depends(get_event_transition_rule_repo)
    ],
    _: Annotated[object, Depends(require_permission("event_schema", "read"))] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all event transition rules for the tenant."""
    rules = await rule_repo.get_by_tenant(tenant_id=tenant_id, skip=skip, limit=limit)
    return [EventTransitionRuleResponse.model_validate(r) for r in rules]


@router.get("/{rule_id}", response_model=EventTransitionRuleResponse)
async def get_event_transition_rule(
    rule_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    rule_repo: Annotated[
        EventTransitionRuleRepository, Depends(get_event_transition_rule_repo)
    ],
    _: Annotated[object, Depends(require_permission("event_schema", "read"))] = None,
):
    """Get event transition rule by id (tenant-scoped)."""
    rule = await rule_repo.get_by_id_and_tenant(rule_id, tenant_id)
    if not rule:
        raise HTTPException(status_code=404, detail=_MSG_RULE_NOT_FOUND)
    return EventTransitionRuleResponse.model_validate(rule)


@router.patch("/{rule_id}", response_model=EventTransitionRuleResponse)
@limit_writes
async def update_event_transition_rule(
    request: Request,
    rule_id: str,
    body: EventTransitionRuleUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    rule_repo: Annotated[
        EventTransitionRuleRepository, Depends(get_event_transition_rule_repo_for_write)
    ],
    _: Annotated[object, Depends(require_permission("event_schema", "update"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Update event transition rule (partial). Tenant-scoped."""
    entity = await rule_repo.get_entity_by_id(rule_id)
    if not entity or entity.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail=_MSG_RULE_NOT_FOUND)
    for attr in _PATCH_OPTIONAL_ATTRS:
        value = getattr(body, attr, None)
        if value is not None:
            setattr(entity, attr, value)
    updated = await rule_repo.update(entity, skip_existence_check=True)
    return EventTransitionRuleResponse.model_validate(updated)


@router.delete("/{rule_id}", status_code=204)
@limit_writes
async def delete_event_transition_rule(
    request: Request,
    rule_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    rule_repo: Annotated[
        EventTransitionRuleRepository, Depends(get_event_transition_rule_repo_for_write)
    ],
    _: Annotated[object, Depends(require_permission("event_schema", "delete"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Delete event transition rule by id. Tenant-scoped."""
    entity = await rule_repo.get_entity_by_id(rule_id)
    if not entity or entity.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail=_MSG_RULE_NOT_FOUND)
    await rule_repo.delete(entity)
