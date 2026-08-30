"""Admin-issued password reset: issuing a link, redeeming it, and its limits."""

import os
import uuid

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from tests.conftest import _TEST_CREATE_TENANT_SECRET

pytestmark = pytest.mark.requires_db


async def _create_tenant(client: AsyncClient) -> dict:
    """Create a tenant and return the creation response body."""
    if "CREATE_TENANT_SECRET" not in os.environ:
        os.environ["CREATE_TENANT_SECRET"] = _TEST_CREATE_TENANT_SECRET
        get_settings.cache_clear()
    secret = os.environ.get("CREATE_TENANT_SECRET", _TEST_CREATE_TENANT_SECRET)
    code = f"pr-{uuid.uuid4().hex[:10]}"
    resp = await client.post(
        "/api/v1/tenants",
        json={
            "code": code,
            "name": "Password Reset Test",
            "admin_initial_password": "OriginalPassword1!",
        },
        headers={"X-Create-Tenant-Secret": secret},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _login(client: AsyncClient, email: str, password: str, tenant_id: str):
    return await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "tenant_id": tenant_id},
    )


async def test_admin_can_reset_a_password_and_the_person_can_sign_in(
    client: AsyncClient,
) -> None:
    """The link an admin issues sets a new password, and the old one stops working."""
    tenant = await _create_tenant(client)
    admin_email, tenant_id = tenant["admin_email"], tenant["tenant_id"]

    signed_in = await _login(client, admin_email, "OriginalPassword1!", tenant_id)
    assert signed_in.status_code == 200, signed_in.text
    headers = {
        "Authorization": f"Bearer {signed_in.json()['access_token']}",
        "X-Tenant-ID": tenant_id,
    }

    issued = await client.post(
        "/api/v1/auth/admin-reset-password",
        json={"email": admin_email},
        headers=headers,
    )
    assert issued.status_code == 200, issued.text
    token = issued.json()["token"]
    assert issued.json()["username"] == "admin"

    done = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token,
            "password": "BrandNewPassword1!",
            "password_confirm": "BrandNewPassword1!",
        },
    )
    assert done.status_code == 204, done.text

    assert (await _login(client, admin_email, "BrandNewPassword1!", tenant_id)).status_code == 200
    assert (await _login(client, admin_email, "OriginalPassword1!", tenant_id)).status_code == 401


async def test_a_reset_link_works_only_once(client: AsyncClient) -> None:
    """Replaying a redeemed link is refused."""
    tenant = await _create_tenant(client)
    admin_email, tenant_id = tenant["admin_email"], tenant["tenant_id"]
    signed_in = await _login(client, admin_email, "OriginalPassword1!", tenant_id)
    headers = {
        "Authorization": f"Bearer {signed_in.json()['access_token']}",
        "X-Tenant-ID": tenant_id,
    }
    token = (
        await client.post(
            "/api/v1/auth/admin-reset-password",
            json={"email": admin_email},
            headers=headers,
        )
    ).json()["token"]

    body = {
        "token": token,
        "password": "FirstReset1!",
        "password_confirm": "FirstReset1!",
    }
    assert (await client.post("/api/v1/auth/reset-password", json=body)).status_code == 204

    replay = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token,
            "password": "SecondReset1!",
            "password_confirm": "SecondReset1!",
        },
    )
    assert replay.status_code == 400


async def test_an_admin_cannot_reset_for_another_organisation(
    client: AsyncClient,
) -> None:
    """The lookup is scoped to the caller's organisation, so B's admin is unreachable.

    Without that scoping, any administrator could mint a link for any email in the
    system and take over the account, since the password lives on the identity.
    """
    tenant_a = await _create_tenant(client)
    tenant_b = await _create_tenant(client)

    signed_in = await _login(
        client, tenant_a["admin_email"], "OriginalPassword1!", tenant_a["tenant_id"]
    )
    headers = {
        "Authorization": f"Bearer {signed_in.json()['access_token']}",
        "X-Tenant-ID": tenant_a["tenant_id"],
    }

    attempt = await client.post(
        "/api/v1/auth/admin-reset-password",
        json={"email": tenant_b["admin_email"]},
        headers=headers,
    )
    assert attempt.status_code == 404, attempt.text

    # B's password is untouched.
    assert (
        await _login(
            client, tenant_b["admin_email"], "OriginalPassword1!", tenant_b["tenant_id"]
        )
    ).status_code == 200


async def test_issuing_a_link_requires_authentication(client: AsyncClient) -> None:
    """An unauthenticated caller cannot mint reset links."""
    tenant = await _create_tenant(client)
    resp = await client.post(
        "/api/v1/auth/admin-reset-password",
        json={"email": tenant["admin_email"]},
        headers={"X-Tenant-ID": tenant["tenant_id"]},
    )
    assert resp.status_code in (401, 403), resp.text


async def test_an_unknown_token_is_refused(client: AsyncClient) -> None:
    """A token that was never issued does not set anybody's password."""
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "not-a-real-token",
            "password": "WhateverPassword1!",
            "password_confirm": "WhateverPassword1!",
        },
    )
    assert resp.status_code == 400


async def test_mismatched_confirmation_is_rejected(client: AsyncClient) -> None:
    """The two password fields must agree."""
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "irrelevant",
            "password": "OnePassword1!",
            "password_confirm": "AnotherPassword1!",
        },
    )
    assert resp.status_code == 422
