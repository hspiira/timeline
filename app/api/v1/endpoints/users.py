"""User API: thin routes delegating to UserRepository."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.v1.dependencies import get_user_repo, get_user_repo_for_write
from app.core.config import get_settings
from app.infrastructure.persistence.repositories.user_repo import UserRepository
from app.schemas.user import UserCreateRequest, UserResponse

router = APIRouter()


def _tenant_id(x_tenant_id: str | None = Header(None)) -> str:
    """Resolve tenant ID from header; raise 400 if missing."""
    name = get_settings().tenant_header_name
    if not x_tenant_id:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required header: {name}",
        )
    return x_tenant_id


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreateRequest,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    user_repo: UserRepository = Depends(get_user_repo_for_write),
):
    """Create a user (tenant-scoped)."""
    try:
        user = await user_repo.create_user(
            tenant_id=tenant_id,
            username=body.username,
            email=body.email,
            password=body.password,
        )
        return UserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    user_repo: UserRepository = Depends(get_user_repo),
):
    """Get user by id (tenant-scoped)."""
    user = await user_repo.get_by_id_and_tenant(user_id, tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
    )


@router.get("")
async def list_users(
    tenant_id: Annotated[str, Depends(_tenant_id)],
    skip: int = 0,
    limit: int = 100,
    user_repo: UserRepository = Depends(get_user_repo),
):
    """List users for tenant (paginated)."""
    users = await user_repo.get_users_by_tenant(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )
    return [
        {
            "id": u.id,
            "tenant_id": u.tenant_id,
            "username": u.username,
            "email": u.email,
            "is_active": u.is_active,
        }
        for u in users
    ]
