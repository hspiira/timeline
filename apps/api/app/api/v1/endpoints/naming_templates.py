"""Naming template API: thin routes delegating to naming template repository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.dependencies import (
    ensure_audit_logged,
    get_naming_template_repo,
    get_naming_template_repo_for_write,
    get_tenant_id,
    require_permission,
)
from app.application.interfaces.repositories import INamingTemplateRepository
from app.domain.exceptions import ResourceNotFoundException
from app.schemas.naming_template import (
    NamingTemplateCreateRequest,
    NamingTemplateResponse,
    NamingTemplateUpdateRequest,
)

router = APIRouter()


@router.post("", response_model=NamingTemplateResponse, status_code=201)
async def create_naming_template(
    body: NamingTemplateCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[
        INamingTemplateRepository, Depends(get_naming_template_repo_for_write)
    ],
    _: Annotated[
        object, Depends(require_permission("naming_template", "create"))
    ] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Create a naming template (tenant-scoped). High-rights only."""
    try:
        template = await repo.create(
            tenant_id=tenant_id,
            scope_type=body.scope_type,
            scope_id=body.scope_id,
            template_string=body.template_string,
            placeholders=body.placeholders,
        )
        return NamingTemplateResponse.model_validate(template)
    except Exception as e:
        if "uq_naming_template_tenant_scope" in str(e) or "unique" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail="A template already exists for this scope (tenant, scope_type, scope_id).",
            ) from e
        raise


@router.get("/{template_id}", response_model=NamingTemplateResponse)
async def get_naming_template(
    template_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[
        INamingTemplateRepository, Depends(get_naming_template_repo)
    ],
    _: Annotated[object, Depends(require_permission("naming_template", "read"))] = None,
):
    """Get naming template by id (tenant-scoped)."""
    template = await repo.get_by_id(template_id, tenant_id)
    if not template:
        raise ResourceNotFoundException("naming_template", template_id)
    return NamingTemplateResponse.model_validate(template)


@router.get("", response_model=list[NamingTemplateResponse])
async def list_naming_templates(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[
        INamingTemplateRepository, Depends(get_naming_template_repo)
    ],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    _: Annotated[object, Depends(require_permission("naming_template", "read"))] = None,
):
    """List naming templates for tenant (paginated)."""
    templates = await repo.get_by_tenant(tenant_id=tenant_id, skip=skip, limit=limit)
    return [NamingTemplateResponse.model_validate(t) for t in templates]


@router.put("/{template_id}", response_model=NamingTemplateResponse)
async def update_naming_template(
    template_id: str,
    body: NamingTemplateUpdateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[
        INamingTemplateRepository, Depends(get_naming_template_repo_for_write)
    ],
    _: Annotated[
        object, Depends(require_permission("naming_template", "update"))
    ] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Update naming template (tenant-scoped)."""
    template = await repo.update(
        template_id=template_id,
        tenant_id=tenant_id,
        template_string=body.template_string,
        placeholders=body.placeholders,
    )
    if not template:
        raise ResourceNotFoundException("naming_template", template_id)
    return NamingTemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=204)
async def delete_naming_template(
    template_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[
        INamingTemplateRepository, Depends(get_naming_template_repo_for_write)
    ],
    _: Annotated[
        object, Depends(require_permission("naming_template", "delete"))
    ] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Delete naming template (tenant-scoped)."""
    deleted = await repo.delete(template_id=template_id, tenant_id=tenant_id)
    if not deleted:
        raise ResourceNotFoundException("naming_template", template_id)
