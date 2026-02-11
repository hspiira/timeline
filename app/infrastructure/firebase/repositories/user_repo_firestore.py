"""Firestore-backed user repository (implements IUserRepository)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.application.dtos.user import UserResult
from app.infrastructure.firebase.collections import COLLECTION_USERS
from app.infrastructure.firebase._rest_client import FirestoreRESTClient
from app.infrastructure.security.password import get_password_hash
from app.shared.utils.generators import generate_cuid


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

    async def create_user(
        self,
        tenant_id: str,
        username: str,
        email: str,
        password: str,
    ) -> UserResult:
        """Create user with hashed password; return created user."""
        hashed = await asyncio.to_thread(get_password_hash, password)
        now = datetime.now(timezone.utc)
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
