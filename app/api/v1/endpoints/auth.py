"""Auth API: login and current user (get/update/delete me).

Uses only injected dependencies (get_user_repo, get_tenant_repo); no manual
repo construction. JWT created via infrastructure security.
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError

from app.api.v1.dependencies import (
    get_current_user,
    get_tenant_repo,
    get_user_repo,
    get_user_repo_for_write,
)
from app.core.limiter import limit_auth, limit_writes
from app.infrastructure.persistence.repositories.tenant_repo import TenantRepository
from app.infrastructure.persistence.repositories.user_repo import UserRepository
from app.infrastructure.security.jwt import create_access_token
from app.infrastructure.security.password import get_password_hash
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
@limit_auth
async def register(
    request: Request,
    body: RegisterRequest,
    user_repo: UserRepository = Depends(get_user_repo_for_write),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
):
    """Register a new user with tenant_code (public endpoint). Resolves tenant by code."""
    tenant = await tenant_repo.get_by_code(body.tenant_code)
    if not tenant:
        raise HTTPException(status_code=400, detail="Invalid tenant code")
    try:
        user = await user_repo.create_user(
            tenant_id=tenant.id,
            username=body.username,
            email=body.email,
            password=body.password,
        )
        return UserResponse.model_validate(user)
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Username or email already registered in this tenant",
        ) from None


@router.post("/login", response_model=TokenResponse)
@limit_auth
async def login(
    request: Request,
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


@router.put("/me", response_model=UserResponse)
@limit_writes
async def update_me(
    request: Request,
    body: UserUpdate,
    current_user: Annotated[object, Depends(get_current_user)],
    user_repo: UserRepository = Depends(get_user_repo_for_write),
):
    """Update current user email and/or password. Requires Authorization."""
    user = await user_repo.get_by_id_and_tenant(
        current_user.id, current_user.tenant_id
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.email is not None:
        user.email = body.email
    if body.password is not None:
        user.hashed_password = await asyncio.to_thread(
            get_password_hash, body.password
        )
    try:
        updated = await user_repo.update(user)
        return UserResponse(
            id=updated.id,
            tenant_id=updated.tenant_id,
            username=updated.username,
            email=updated.email,
            is_active=updated.is_active,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Email is already registered in this tenant",
        ) from None


@router.delete("/me", status_code=204)
@limit_writes
async def delete_me(
    request: Request,
    current_user: Annotated[object, Depends(get_current_user)],
    user_repo: UserRepository = Depends(get_user_repo_for_write),
):
    """Deactivate current user (soft delete). Requires Authorization."""
    updated = await user_repo.deactivate(
        current_user.id, current_user.tenant_id
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
