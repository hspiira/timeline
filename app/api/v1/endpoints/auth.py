"""Auth API: login and current user.

Uses only injected dependencies (get_user_repo, get_tenant_repo); no manual
repo construction. JWT created via infrastructure security.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import (
    get_current_user,
    get_tenant_repo,
    get_user_repo,
)
from app.infrastructure.persistence.repositories.tenant_repo import TenantRepository
from app.infrastructure.persistence.repositories.user_repo import UserRepository
from app.infrastructure.security.jwt import create_access_token
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    user_repo: UserRepository = Depends(get_user_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
):
    """Authenticate with tenant_code, username, and password; return JWT.

    Tenant is identified by tenant_code (e.g. org slug).
    """
    tenant = await tenant_repo.get_by_code(body.tenant_code)
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid tenant or credentials")
    tenant_id = tenant.id

    user = await user_repo.authenticate(
        username=body.username,
        tenant_id=tenant_id,
        password=body.password,
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        data={"sub": user.id, "tenant_id": user.tenant_id, "username": user.username},
    )
    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[object, Depends(get_current_user)],
):
    """Return the currently authenticated user from JWT.

    Requires Authorization: Bearer <token>.
    """
    u = current_user
    return UserResponse(
        id=u.id,
        tenant_id=u.tenant_id,
        username=u.username,
        email=u.email,
        is_active=u.is_active,
    )
