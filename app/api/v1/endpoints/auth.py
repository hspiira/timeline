"""Auth API: login and current user (get/update/delete me).

Uses only injected dependencies (get_user_repo, get_tenant_repo); no manual
repo construction. JWT created via infrastructure security.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.dependencies import (
    AuthSecurity,
    get_auth_security,
    get_current_user,
    get_tenant_repo,
    get_user_repo,
    get_user_repo_for_write,
    get_user_service,
)
from app.application.dtos.user import UserResult
from app.application.services.user_service import UserService
from app.core.limiter import limit_auth, limit_writes
from app.infrastructure.persistence.repositories.tenant_repo import TenantRepository
from app.infrastructure.persistence.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
@limit_auth
async def register(
    request: Request,
    body: RegisterRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repo_for_write)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repo)],
):
    """Register a new user with tenant_code (public endpoint). Resolves tenant by code.

    Error responses are intentionally generic to avoid tenant enumeration.
    """
    try:
        tenant = await tenant_repo.get_by_code(body.tenant_code)
        if not tenant:
            raise HTTPException(status_code=400, detail="Registration failed")
        user = await user_repo.create_user(
            tenant_id=tenant.id,
            username=body.username,
            email=body.email,
            password=body.password,
        )
        return UserResponse.model_validate(user)
    except HTTPException:
        # Re-raise our own HTTPExceptions unchanged.
        raise
    except Exception:
        # Hide specific failure reasons (e.g. duplicate user/email) behind a generic message.
        raise HTTPException(status_code=400, detail="Registration failed")


@router.post("/login", response_model=TokenResponse)
@limit_auth
async def login(
    request: Request,
    body: LoginRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repo)],
    auth_security: Annotated[AuthSecurity, Depends(get_auth_security)],
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

    token = auth_security.create_access_token(
        data={"sub": user.id, "tenant_id": user.tenant_id, "username": user.username},
    )
    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[UserResult, Depends(get_current_user)],
):
    """Return the currently authenticated user from JWT.

    Requires Authorization: Bearer <token>.
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
@limit_writes
async def update_me(
    request: Request,
    body: UserUpdate,
    current_user: Annotated[UserResult, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """Update current user email and/or password. Requires Authorization."""
    updated = await user_service.update_me(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        email=body.email,
        password=body.password,
    )
    return UserResponse.model_validate(updated)


@router.delete("/me", status_code=204)
@limit_writes
async def delete_me(
    request: Request,
    current_user: Annotated[UserResult, Depends(get_current_user)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo_for_write)],
):
    """Deactivate current user (soft delete). Requires Authorization."""
    updated = await user_repo.deactivate(
        current_user.id, current_user.tenant_id
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
