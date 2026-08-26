"""Auth API: login and current user (get/update/delete me).

Uses only injected dependencies (get_user_repo, get_tenant_repo); no manual
repo construction. JWT created via infrastructure security.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import text

from app.api.v1.dependencies import (
    get_authorization_service,
    get_create_access_token,
    get_current_user,
    get_set_password_deps,
    get_tenant_repo,
    get_user_repo,
    get_user_repo_for_write,
    get_user_service,
)
from app.application.dtos.user import UserResult
from app.application.services.authorization_service import AuthorizationService
from app.application.services.user_service import UserService
from app.core.config import get_settings
from app.core.tenant_validation import is_valid_tenant_id_format
from app.core.limiter import check_auth_rate_per_tenant_code, limit_auth, limit_writes
from app.infrastructure.security.jwt import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.infrastructure.persistence.repositories.tenant_repo import TenantRepository
from app.infrastructure.persistence.repositories.user_repo import UserRepository
from app.infrastructure.persistence.repositories.password_set_token_repo import (
    PasswordSetTokenStore,
)
from app.schemas.auth import (
    LoginRequest,
    OrganisationsRequest,
    OrganisationsResponse,
    OrganisationSummary,
    RegisterRequest,
    SetInitialPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Attach the refresh token as an httpOnly cookie scoped to the auth endpoints.

    httpOnly keeps it out of reach of page scripts, so an XSS bug cannot steal a
    long-lived credential. Path is narrowed to the auth routes because nothing else
    needs it sent.
    """
    settings = get_settings()
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        domain=settings.refresh_cookie_domain,
        path="/api/v1/auth",
    )


async def _use_tenant(repo: UserRepository, tenant_id: str) -> None:
    """Set the session's tenant context for row-level security.

    The auth endpoints run before the caller has a token, so the usual middleware has
    nothing to work from. Each of them resolves the organisation itself (from the
    email, the refresh token, or a redeemed link) and then calls this, so the reads
    that follow go through the normal tenant-scoped path rather than needing a policy
    exception.
    """
    if not is_valid_tenant_id_format(tenant_id):  # pragma: no cover - defensive
        raise HTTPException(status_code=401, detail="Invalid credentials")
    await repo.db.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))


def _clear_refresh_cookie(response: Response) -> None:
    """Remove the refresh cookie (failed refresh, or sign-out)."""
    settings = get_settings()
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        domain=settings.refresh_cookie_domain,
        path="/api/v1/auth",
    )


def _issue_tokens(response: Response, user: UserResult | object) -> TokenResponse:
    """Mint an access token, and set the refresh cookie, for a signed-in membership."""
    settings = get_settings()
    claims = {
        "sub": user.id,
        "tenant_id": user.tenant_id,
        "username": user.username,
    }
    _set_refresh_cookie(
        response,
        create_refresh_token({"sub": user.id, "tenant_id": user.tenant_id}),
    )
    return TokenResponse(
        access_token=create_access_token(claims),
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=UserResponse, status_code=201)
@limit_auth
async def register(
    request: Request,
    body: RegisterRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repo_for_write)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repo)],
):
    """Disabled. Use the authenticated ``POST /api/v1/users`` to add someone.

    This was public and unauthenticated: anyone knowing an organisation's code — and
    codes are not secret, they get typed into the sign-in box and mailed out in
    invites — could create an account inside that organisation. It was also being
    called by the admin "add user" screen, which is an authenticated action and
    belongs on ``POST /api/v1/users``, where the organisation comes from the caller's
    own token and permissions are checked.

    Kept as a route so existing callers get a clear answer rather than a 404, and so
    re-enabling self-service signup stays a deliberate decision.
    """
    raise HTTPException(
        status_code=403,
        detail=(
            "Public self-registration is disabled. An administrator adds users via "
            "POST /api/v1/users."
        ),
    )


@router.post("/set-initial-password", status_code=204)
@limit_auth
async def set_initial_password(
    request: Request,
    body: SetInitialPasswordRequest,
    deps: Annotated[
        tuple[PasswordSetTokenStore, UserRepository],
        Depends(get_set_password_deps),
    ],
):
    """Set initial admin password using one-time token (C2 tenant creation flow).

    Token is from the set_password_url returned by POST /tenants when SET_PASSWORD_BASE_URL is set.
    Requires PostgreSQL; returns 503 when database backend is not postgres.
    """
    token_store, user_repo = deps
    redeemed = await token_store.redeem(body.token)
    if not redeemed:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired link. Request a new link from your administrator.",
        )
    user_id, tenant_id = redeemed

    # Nobody is signed in yet, so there is no tenant context and every tenant-scoped
    # read below would come back empty. The redeemed token tells us which
    # organisation this is, so establish it before touching app_user.
    await _use_tenant(user_repo, tenant_id)

    updated = await user_repo.update_password(user_id, body.password)
    if not updated:
        raise HTTPException(status_code=400, detail="User not found")
    return None


@router.post("/organisations", response_model=OrganisationsResponse)
@limit_auth
async def organisations_for_email(
    request: Request,
    body: OrganisationsRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
):
    """List the organisations an email can sign in to, so nobody types a code.

    The client calls this first. One result goes straight to the password step and
    the person is never asked about organisations; several shows a picker of names.

    Always 200, even for an unknown email, so this cannot be used to confirm
    whether an address is registered by watching status codes.
    """
    organisations = await user_repo.get_organisations_for_email(body.email)
    return OrganisationsResponse(
        organisations=[
            OrganisationSummary(tenant_id=tid, name=name) for tid, name in organisations
        ]
    )


@router.post("/login", response_model=TokenResponse)
@limit_auth
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
):
    """Sign in with email and password; organisation only when it is ambiguous.

    There is no organisation code. If the email belongs to exactly one organisation
    we use it. If it belongs to several, ``tenant_id`` is required and the client is
    expected to have called ``POST /auth/organisations`` to offer a picker.

    Returns an access token, and sets the refresh token as an httpOnly cookie so the
    session renews quietly instead of expiring mid-task.
    """
    organisations = await user_repo.get_organisations_for_email(body.email)

    if body.tenant_id is not None:
        # Only honour an organisation this email actually belongs to, otherwise a
        # caller could aim a password guess at an arbitrary organisation.
        if body.tenant_id not in {tid for tid, _ in organisations}:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        tenant_id = body.tenant_id
    elif len(organisations) == 1:
        tenant_id = organisations[0][0]
    elif not organisations:
        # Unknown email. Same message as a wrong password, and still pay the cost of
        # a password check inside authenticate() so timing does not give it away.
        await user_repo.authenticate(
            email=body.email, tenant_id="", password=body.password
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    else:
        raise HTTPException(
            status_code=409,
            detail="This email belongs to more than one organisation; tenant_id is required",
        )

    check_auth_rate_per_tenant_code(tenant_id)

    # Nothing has established tenant context yet — that normally comes from the
    # caller's token, and they do not have one until this request succeeds. Without
    # it, row-level security hides the membership and every sign-in fails. The
    # organisation was just resolved from the email, so set it now.
    await _use_tenant(user_repo, tenant_id)

    user = await user_repo.authenticate(
        email=body.email,
        tenant_id=tenant_id,
        password=body.password,
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return _issue_tokens(response, user)


@router.post("/refresh", response_model=TokenResponse)
@limit_auth
async def refresh(
    request: Request,
    response: Response,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
):
    """Issue a fresh access token from the refresh cookie, and rotate the cookie.

    Keeps people signed in through a working day without retyping anything. The
    membership is re-checked on every call, so someone removed from an organisation
    stops being renewed rather than lasting until their token happens to expire.
    """
    settings = get_settings()
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = verify_token(token, expected_type=REFRESH_TOKEN_TYPE)
    except ValueError:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if not user_id or not tenant_id:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Not authenticated")

    await _use_tenant(user_repo, tenant_id)
    user = await user_repo.get_by_id_and_tenant(user_id, tenant_id)
    if not user or not user.is_active or not user.identity.is_active:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Not authenticated")

    return _issue_tokens(response, user)


@router.post("/logout", status_code=204)
async def logout(response: Response):
    """Drop the refresh cookie so the session cannot be renewed."""
    _clear_refresh_cookie(response)
    return None


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[UserResult, Depends(get_current_user)],
    auth_svc: Annotated[AuthorizationService, Depends(get_authorization_service)],
):
    """Return the authenticated user together with the permissions they hold.

    The permission list lets a client hide actions the caller cannot perform.
    It is a convenience for the interface only: every endpoint still checks the
    caller's permissions itself, so a client that ignores this list gains nothing.

    Requires Authorization: Bearer <token>.
    """
    permissions = await auth_svc.get_user_permissions(
        current_user.id, current_user.tenant_id
    )
    return UserResponse.model_validate(current_user).model_copy(
        update={"permissions": sorted(permissions)}
    )


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
