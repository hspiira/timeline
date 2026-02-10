"""Authorization service: permission checks with optional caching (IPermissionResolver + cache)."""

from __future__ import annotations

from app.application.interfaces.services import ICacheService, IPermissionResolver
from app.domain.exceptions import AuthorizationException


class AuthorizationService:
    """Centralized permission checking; uses cache when available (5 min TTL typical)."""

    def __init__(
        self,
        permission_resolver: IPermissionResolver,
        cache: ICacheService | None = None,
        cache_ttl: int = 300,
    ) -> None:
        self.permission_resolver = permission_resolver
        self.cache = cache
        self.cache_ttl = cache_ttl

    async def get_user_permissions(self, user_id: str, tenant_id: str) -> set[str]:
        """Return set of permission codes (e.g. event:create, subject:read). Uses cache if available."""
        key = f"permission:{tenant_id}:{user_id}"
        if self.cache and self.cache.is_available():
            cached = await self.cache.get(key)
            if cached is not None:
                return set(cached)

        permissions = await self.permission_resolver.get_user_permissions(
            user_id, tenant_id
        )
        if self.cache and self.cache.is_available():
            await self.cache.set(key, list(permissions), ttl=self.cache_ttl)
        return permissions

    async def check_permission(
        self,
        user_id: str,
        tenant_id: str,
        resource: str,
        action: str,
    ) -> bool:
        """Return True if user has resource:action or resource:* or *:*."""
        permissions = await self.get_user_permissions(user_id, tenant_id)
        code = f"{resource}:{action}"
        if code in permissions:
            return True
        if f"{resource}:*" in permissions or "*:*" in permissions:
            return True
        return False

    async def require_permission(
        self,
        user_id: str,
        tenant_id: str,
        resource: str,
        action: str,
    ) -> None:
        """Raise AuthorizationException if user lacks permission."""
        if not await self.check_permission(user_id, tenant_id, resource, action):
            raise AuthorizationException(resource=resource, action=action)

    async def invalidate_user_cache(self, user_id: str, tenant_id: str) -> None:
        """Invalidate cached permissions for one user."""
        if self.cache and self.cache.is_available():
            key = f"permission:{tenant_id}:{user_id}"
            await self.cache.delete(key)

    async def invalidate_tenant_cache(self, tenant_id: str) -> None:
        """Invalidate all cached permissions for a tenant."""
        if self.cache and self.cache.is_available():
            await self.cache.delete_pattern(f"permission:{tenant_id}:*")
