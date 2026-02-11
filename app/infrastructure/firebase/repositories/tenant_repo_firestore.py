"""Firestore-backed tenant repository (implements ITenantRepository)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.application.dtos.tenant import TenantResult
from app.domain.enums import TenantStatus
from app.domain.exceptions import TenantAlreadyExistsError
from app.infrastructure.firebase.collections import COLLECTION_TENANTS
from app.infrastructure.firebase._rest_client import FirestoreRESTClient
from app.shared.utils.generators import generate_cuid


class FirestoreTenantRepository:
    """Tenant repository using Firestore. Same contract as TenantRepository (Postgres)."""

    def __init__(self, client: FirestoreRESTClient) -> None:
        self._client = client
        self._coll = client.collection(COLLECTION_TENANTS)

    async def get_by_id(self, tenant_id: str) -> TenantResult | None:
        """Return tenant by ID."""
        doc = await self._coll.document(tenant_id).get()
        if not doc:
            return None
        d = doc.to_dict()
        return TenantResult(
            id=doc.id,
            code=d.get("code", ""),
            name=d.get("name", ""),
            status=d.get("status", "active"),
        )

    async def get_by_code(self, code: str) -> TenantResult | None:
        """Return tenant by unique code."""
        async for snapshot in self._coll.stream():
            data = snapshot.to_dict()
            if data.get("code") == code:
                return TenantResult(
                    id=snapshot.id,
                    code=data.get("code", ""),
                    name=data.get("name", ""),
                    status=data.get("status", "active"),
                )
        return None

    async def create_tenant(
        self, code: str, name: str, status: TenantStatus
    ) -> TenantResult:
        """Create tenant; raise TenantAlreadyExistsError if code exists."""
        existing = await self.get_by_code(code)
        if existing:
            raise TenantAlreadyExistsError(code)
        now = datetime.now(timezone.utc)
        tenant_id = generate_cuid()
        await self._coll.document(tenant_id).set({
            "code": code,
            "name": name,
            "status": status.value,
            "created_at": now,
            "updated_at": now,
        })
        return TenantResult(id=tenant_id, code=code, name=name, status=status.value)

    async def get_active_tenants(
        self, skip: int = 0, limit: int = 100
    ) -> list[TenantResult]:
        """Return active tenants with pagination."""
        results: list[TenantResult] = []
        async for snapshot in self._coll.stream():
            data = snapshot.to_dict()
            if data.get("status") != TenantStatus.ACTIVE.value:
                continue
            results.append(
                TenantResult(
                    id=snapshot.id,
                    code=data.get("code", ""),
                    name=data.get("name", ""),
                    status=data.get("status", "active"),
                )
            )
        results.sort(key=lambda t: t.code)
        return results[skip : skip + limit]

    async def update_status(
        self, tenant_id: str, status: TenantStatus
    ) -> TenantResult | None:
        """Update tenant status; return updated result or None if not found."""
        return await self.update_tenant(tenant_id, status=status)

    async def update_tenant(
        self,
        tenant_id: str,
        name: str | None = None,
        status: TenantStatus | None = None,
    ) -> TenantResult | None:
        """Update tenant name and/or status; return updated result or None if not found."""
        doc_ref = self._coll.document(tenant_id)
        doc = await doc_ref.get()
        if not doc:
            return None
        data = doc.to_dict()
        if name is not None:
            data["name"] = name
        if status is not None:
            data["status"] = status.value
        data["updated_at"] = datetime.now(timezone.utc)
        await doc_ref.set(data)
        return TenantResult(
            id=doc.id,
            code=data.get("code", ""),
            name=data.get("name", ""),
            status=data.get("status", "active"),
        )
