"""Firestore-backed user repository (implements IUserRepository)."""

from __future__ import annotations

import asyncio

from app.application.dtos.user import UserResult
from app.infrastructure.firebase.collections import COLLECTION_USERS
from app.infrastructure.firebase._rest_client import FirestoreRESTClient
from app.infrastructure.security.password import get_password_hash, verify_password
from app.shared.utils.datetime import utc_now
from app.shared.utils.generators import generate_cuid


_dummy_hash_cache: str | None = None


async def _get_dummy_hash() -> str:
    """Return a valid bcrypt hash for dummy comparison (timing-attack mitigation)."""
    global _dummy_hash_cache
    if _dummy_hash_cache is None:
        _dummy_hash_cache = await asyncio.to_thread(
            get_password_hash, "not-a-real-password"
        )
    return _dummy_hash_cache


class FirestoreUserRepository:
    """User repository using Firestore. Same contract as UserRepository (Postgres)."""

    def __init__(self, client: FirestoreRESTClient) -> None:
        self._client = client
        self._coll = client.collection(COLLECTION_USERS)

    def _to_result(self, doc_id: str, data: dict) -> UserResult:
        return UserResult(
            id=doc_id,
            tenant_id=data.get("tenant_id", ""),
            username=data.get("username", ""),
            email=data.get("email", ""),
            is_active=data.get("is_active", True),
        )

    async def get_by_id(self, user_id: str) -> UserResult | None:
        """Return user by ID."""
        doc = await self._coll.document(user_id).get()
        if not doc:
            return None
        return self._to_result(doc.id, doc.to_dict())

    async def get_by_id_and_tenant(
        self, user_id: str, tenant_id: str
    ) -> UserResult | None:
        """Return user by ID if they belong to the tenant."""
        doc = await self._coll.document(user_id).get()
        if not doc:
            return None
        data = doc.to_dict()
        if data.get("tenant_id") != tenant_id:
            return None
        return self._to_result(doc.id, data)

    async def authenticate(
        self, username: str, tenant_id: str, password: str
    ) -> UserResult | None:
        """Verify username/password for a tenant; return user or None."""
        q = self._coll.where("username", "==", username).limit(10)
        doc_id: str | None = None
        data: dict | None = None
        async for snapshot in q.stream():
            d = snapshot.to_dict()
            if d.get("tenant_id") == tenant_id:
                doc_id = snapshot.id
                data = d
                break

        if doc_id is None or data is None:
            dummy_hash = await _get_dummy_hash()
            await asyncio.to_thread(verify_password, password, dummy_hash)
            return None
        if not data.get("is_active", True):
            return None
        stored_hash = data.get("hashed_password", "")
        if not await asyncio.to_thread(verify_password, password, stored_hash):
            return None
        return self._to_result(doc_id, data)

    async def create_user(
        self,
        tenant_id: str,
        username: str,
        email: str,
        password: str,
    ) -> UserResult:
        """Create user with hashed password; return created user."""
        hashed = await asyncio.to_thread(get_password_hash, password)
        now = utc_now()
        user_id = generate_cuid()
        await self._coll.document(user_id).set({
            "tenant_id": tenant_id,
            "username": username,
            "email": email,
            "hashed_password": hashed,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })
        return UserResult(
            id=user_id,
            tenant_id=tenant_id,
            username=username,
            email=email,
            is_active=True,
        )
