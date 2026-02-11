"""Firestore-backed tenant RBAC initialization (implements ITenantInitializationService)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.application.services.system_audit_schema import (
    SYSTEM_AUDIT_EVENT_TYPE,
    SYSTEM_AUDIT_SCHEMA_VERSION,
    SYSTEM_AUDIT_SUBJECT_REF,
    SYSTEM_AUDIT_SUBJECT_TYPE,
    get_system_audit_schema_definition,
)
from app.infrastructure.firebase.collections import (
    COLLECTION_EVENT_SCHEMAS,
    COLLECTION_PERMISSIONS,
    COLLECTION_ROLE_PERMISSIONS,
    COLLECTION_ROLES,
    COLLECTION_SUBJECTS,
    COLLECTION_USER_ROLES,
)
from app.infrastructure.firebase._rest_client import FirestoreRESTClient
from app.infrastructure.services.tenant_initialization_service import (
    DEFAULT_ROLES,
    SYSTEM_PERMISSIONS,
)
from app.shared.utils.generators import generate_cuid


def _resolve_permission_pattern(
    pattern: str, permission_map: dict[str, str]
) -> list[str]:
    """Resolve a permission pattern to permission IDs (same logic as SQL init)."""
    if pattern.endswith(":*"):
        prefix = pattern[:-2]
        return [
            pid
            for code, pid in permission_map.items()
            if code.startswith(prefix + ":")
        ]
    pid = permission_map.get(pattern)
    return [pid] if pid else []


class FirestoreTenantInitializationService:
    """Initializes new tenant RBAC and audit docs in Firestore."""

    def __init__(self, client: FirestoreRESTClient) -> None:
        self._client = client
        self._role_map: dict[str, dict[str, str]] = {}

    async def initialize_tenant_infrastructure(self, tenant_id: str) -> None:
        """Create permissions, roles, role_permissions, audit schema and subject in Firestore."""
        # Idempotency: skip if tenant already has permissions
        perms_coll = self._client.collection(COLLECTION_PERMISSIONS)
        async for snapshot in perms_coll.stream():
            if snapshot.to_dict().get("tenant_id") == tenant_id:
                return
        now = datetime.now(timezone.utc)

        # Permissions
        permission_map: dict[str, str] = {}
        for code, resource, action, description in SYSTEM_PERMISSIONS:
            perm_id = generate_cuid()
            await perms_coll.document(perm_id).set({
                "tenant_id": tenant_id,
                "code": code,
                "resource": resource,
                "action": action,
                "description": description,
                "created_at": now,
            })
            permission_map[code] = perm_id

        # Roles and role_permissions
        roles_coll = self._client.collection(COLLECTION_ROLES)
        rp_coll = self._client.collection(COLLECTION_ROLE_PERMISSIONS)
        role_map: dict[str, str] = {}
        for role_code, role_data in DEFAULT_ROLES.items():
            role_id = generate_cuid()
            await roles_coll.document(role_id).set({
                "tenant_id": tenant_id,
                "code": role_code,
                "name": role_data["name"],
                "description": role_data["description"],
                "is_system": role_data["is_system"],
                "is_active": True,
                "created_at": now,
            })
            role_map[role_code] = role_id
            for perm_pattern in role_data["permissions"]:
                for perm_id in _resolve_permission_pattern(
                    perm_pattern, permission_map
                ):
                    await rp_coll.document(generate_cuid()).set({
                        "tenant_id": tenant_id,
                        "role_id": role_id,
                        "permission_id": perm_id,
                        "created_at": now,
                    })
        self._role_map[tenant_id] = role_map

        # Audit event schema
        schema_id = generate_cuid()
        await self._client.collection(COLLECTION_EVENT_SCHEMAS).document(
            schema_id
        ).set({
            "tenant_id": tenant_id,
            "event_type": SYSTEM_AUDIT_EVENT_TYPE,
            "schema_definition": get_system_audit_schema_definition(),
            "version": SYSTEM_AUDIT_SCHEMA_VERSION,
            "is_active": True,
            "created_by": None,
            "created_at": now,
        })

        # Audit subject
        subject_id = generate_cuid()
        await self._client.collection(COLLECTION_SUBJECTS).document(
            subject_id
        ).set({
            "tenant_id": tenant_id,
            "subject_type": SYSTEM_AUDIT_SUBJECT_TYPE,
            "external_ref": SYSTEM_AUDIT_SUBJECT_REF,
            "created_at": now,
        })

    async def assign_admin_role(
        self, tenant_id: str, admin_user_id: str
    ) -> None:
        """Create user_roles doc linking user to admin role."""
        tenant_roles = self._role_map.get(tenant_id, {})
        if "admin" not in tenant_roles:
            # Look up admin role by querying roles
            roles_coll = self._client.collection(COLLECTION_ROLES)
            async for snapshot in roles_coll.stream():
                d = snapshot.to_dict()
                if d.get("tenant_id") == tenant_id and d.get("code") == "admin":
                    tenant_roles["admin"] = snapshot.id
                    self._role_map[tenant_id] = tenant_roles
                    break
            else:
                raise ValueError(
                    f"Admin role not found for tenant {tenant_id}"
                )
        admin_role_id = tenant_roles["admin"]
        now = datetime.now(timezone.utc)
        await self._client.collection(COLLECTION_USER_ROLES).document(
            generate_cuid()
        ).set({
            "tenant_id": tenant_id,
            "user_id": admin_user_id,
            "role_id": admin_role_id,
            "assigned_by": admin_user_id,
            "created_at": now,
        })
