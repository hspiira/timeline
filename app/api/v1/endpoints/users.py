"""User API: thin routes delegating to UserRepository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.dependencies import (
    ensure_audit_logged,
    get_set_password_deps,
    get_tenant_id,
    get_user_repo,
    require_permission,
)
from app.core.config import get_settings
from app.core.limiter import limit_writes
from app.infrastructure.persistence.repositories.password_set_token_repo import (
    PasswordSetTokenStore,
)
from app.infrastructure.persistence.repositories.user_repo import UserRepository
from app.infrastructure.security.password import generate_secure_password
from app.schemas.user import UserCreateRequest, UserCreateResponse, UserResponse

router = APIRouter()


@router.post("", response_model=UserCreateResponse, status_code=201)
@limit_writes
async def create_user(
    request: Request,
    body: UserCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    set_password_deps: Annotated[
        tuple[PasswordSetTokenStore, UserRepository], Depends(get_set_password_deps)
    ],
    _: Annotated[object, Depends(require_permission("user", "create"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Add someone to this organisation, by invitation or with a set password.

    Omit ``password`` to invite: the person is created with a password nobody knows
    and the response carries a one-time link for them to choose their own. Supply
    ``password`` only where an administrator genuinely must set it.
    """
    token_store, user_repo = set_password_deps
    invited = body.password is None
    password = body.password if body.password is not None else generate_secure_password()
    try:
        user = await user_repo.create_user(
            tenant_id=tenant_id,
            username=body.username,
            email=body.email,
            password=password,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    response = UserCreateResponse.model_validate(user)
    if not invited:
        return response

    token, expires_at = await token_store.create(user.id)
    settings = get_settings()
    invite_url = None
    if settings.set_password_base_url:
        base = settings.set_password_base_url.rstrip("/")
        invite_url = f"{base}/set-password?token={token}"
    return response.model_copy(
        update={
            "invite_token": token,
            "invite_url": invite_url,
            "invite_expires_at": expires_at,
        }
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    user_repo: UserRepository = Depends(get_user_repo),
    _: Annotated[object, Depends(require_permission("user", "read"))] = None,
):
    """Get user by id (tenant-scoped)."""
    user = await user_repo.get_by_id_and_tenant(user_id, tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.get("", response_model=list[UserResponse])
async def list_users(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_repo: UserRepository = Depends(get_user_repo),
    _: Annotated[object, Depends(require_permission("user", "read"))] = None,
):
    """List users for tenant (paginated)."""
    users = await user_repo.get_users_by_tenant(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )
    return [UserResponse.model_validate(u) for u in users]
