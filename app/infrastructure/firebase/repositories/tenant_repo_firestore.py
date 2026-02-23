"""Firestore-backed tenant repository (implements ITenantRepository)."""

from __future__ import annotations

from typing import Any

from app.application.dtos.tenant import TenantResult
from app.domain.enums import TenantStatus
from app.domain.exceptions import TenantAlreadyExistsException
from app.infrastructure.firebase.collections import COLLECTION_TENANTS
from app.infrastructure.firebase._rest_client import (
    DocumentExistsError,
    FirestoreRESTClient,
)
from app.shared.utils.datetime import utc_now


def _tenant_doc_id(code: str) -> str:
    """Firestore document ID from tenant code (cannot contain '/')."""
    return code.replace("/", "_")


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
            status=TenantStatus(d.get("status", "active")),
        )

    async def get_by_code(self, code: str) -> TenantResult | None:
        """Return tenant by unique code (server-side where query, at most one doc)."""
        q = self._coll.where("code", "==", code).limit(1)
        async for snapshot in q.stream():
            data = snapshot.to_dict()
            return TenantResult(
                id=snapshot.id,
                code=data.get("code", ""),
                name=data.get("name", ""),
                status=TenantStatus(data.get("status", "active")),
            )
        return None

    async def create_tenant(
        self, code: str, name: str, status: TenantStatus
    ) -> TenantResult:
        """Create tenant; raise TenantAlreadyExistsException if code exists (atomic via doc ID)."""
        doc_id = _tenant_doc_id(code)
        now = utc_now()
        try:
            await self._coll.create(doc_id, {
                "code": code,
                "name": name,
                "status": status.value,
                "created_at": now,
                "updated_at": now,
            })
        except DocumentExistsError:
            raise TenantAlreadyExistsException(code) from None
        return TenantResult(id=doc_id, code=code, name=name, status=status)

    async def get_active_tenants(
        self, skip: int = 0, limit: int = 100
    ) -> list[TenantResult]:
        """Return active tenants with pagination (server-side filter and order)."""
        results: list[TenantResult] = []
        q = (
            self._coll.where("status", "==", TenantStatus.ACTIVE.value)
            .order_by("code")
            .offset(skip)
            .limit(limit)
        )
        async for snapshot in q.stream():
            data = snapshot.to_dict()
            results.append(
                TenantResult(
                    id=snapshot.id,
                    code=data.get("code", ""),
                    name=data.get("name", ""),
                    status=TenantStatus(data.get("status", "active")),
                )
            )
        return results

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
        updates: dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if status is not None:
            updates["status"] = status.value
        updates["updated_at"] = utc_now()
        await doc_ref.update(updates)
        data = doc.to_dict()
        data.update(updates)
        return TenantResult(
            id=tenant_id,
            code=data.get("code", ""),
            name=data.get("name", ""),
            status=TenantStatus(data.get("status", "active")),
        )
