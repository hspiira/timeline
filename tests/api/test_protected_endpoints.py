"""Protected endpoint tests. Require Postgres; use auth_headers from conftest."""

import pytest
from httpx import AsyncClient
from io import BytesIO


@pytest.mark.requires_db
async def test_list_tenants_with_auth_returns_200(
    client: AsyncClient,
    auth_headers: dict[str, str] | None,
) -> None:
    """GET /api/v1/tenants with valid JWT and X-Tenant-ID returns 200 and list."""
    if auth_headers is None:
        pytest.skip("auth_headers not available (Postgres not configured)")
    response = await client.get("/api/v1/tenants", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Our test tenant should be in the list
    tenant_ids = [t["id"] for t in data]
    assert auth_headers["X-Tenant-ID"] in tenant_ids


@pytest.mark.requires_db
async def test_get_tenant_by_id_with_auth_returns_200(
    client: AsyncClient,
    auth_headers: dict[str, str] | None,
) -> None:
    """GET /api/v1/tenants/{tenant_id} with valid JWT returns 200 and tenant."""
    if auth_headers is None:
        pytest.skip("auth_headers not available (Postgres not configured)")
    tenant_id = auth_headers["X-Tenant-ID"]
    response = await client.get(
        f"/api/v1/tenants/{tenant_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tenant_id
    assert "code" in data
    assert "name" in data
    assert "status" in data


@pytest.mark.requires_db
async def test_create_subject_with_auth_returns_201(
    client: AsyncClient,
    auth_headers: dict[str, str] | None,
) -> None:
    """POST /api/v1/subjects with valid JWT creates subject and returns 201."""
    if auth_headers is None:
        pytest.skip("auth_headers not available (Postgres not configured)")
    response = await client.post(
        "/api/v1/subjects",
        headers=auth_headers,
        json={
            "subject_type": "client",
            "external_ref": None,
            "display_name": "Test Subject",
            "attributes": {},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["subject_type"] == "client"
    assert data.get("display_name") == "Test Subject"
    assert data["tenant_id"] == auth_headers["X-Tenant-ID"]


@pytest.mark.requires_db
async def test_upload_document_with_nonexistent_subject_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str] | None,
) -> None:
    """POST /api/v1/documents with subject_id that does not exist in tenant returns 404."""
    if auth_headers is None:
        pytest.skip("auth_headers not available (Postgres not configured)")
    # Use a CUID-like id that does not exist as a subject in the tenant.
    fake_subject_id = "clxxxxxxxxxxxxxxxxxxxxxxxxx"
    files = {"file": ("test.txt", BytesIO(b"test content"), "text/plain")}
    data = {"subject_id": fake_subject_id, "document_type": "misc"}
    response = await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        data=data,
        files=files,
    )
    assert response.status_code == 404
    assert "subject" in response.json().get("detail", "").lower()
