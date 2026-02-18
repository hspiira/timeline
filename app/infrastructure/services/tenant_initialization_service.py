"""Tenant RBAC initialization (implements ITenantInitializationService)."""

from __future__ import annotations

from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.relationship_event_schema import (
    RELATIONSHIP_ADDED_EVENT_TYPE,
    RELATIONSHIP_EVENT_SCHEMA_VERSION,
    RELATIONSHIP_REMOVED_EVENT_TYPE,
    get_relationship_event_schema_definition,
)
from app.application.services.system_audit_schema import (
    SYSTEM_AUDIT_EVENT_TYPE,
    SYSTEM_AUDIT_SCHEMA_VERSION,
    SYSTEM_AUDIT_SUBJECT_REF,
    SYSTEM_AUDIT_SUBJECT_TYPE,
    get_system_audit_schema_definition,
)
from app.domain.exceptions import ResourceNotFoundException
from app.infrastructure.persistence.models.event_schema import EventSchema
from app.infrastructure.persistence.models.permission import (
    Permission,
    RolePermission,
    UserRole,
)
from app.infrastructure.persistence.models.role import Role
from app.infrastructure.persistence.models.subject import Subject
from app.shared.utils.generators import generate_cuid


class RoleData(TypedDict):
    """Role configuration for default roles."""

    name: str
    description: str
    permissions: list[str]
    is_system: bool


SYSTEM_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("event:create", "event", "create", "Create events"),
    ("event:read", "event", "read", "View event details"),
    ("event:list", "event", "list", "List events"),
    ("subject:create", "subject", "create", "Create subjects"),
    ("subject:read", "subject", "read", "View subject details"),
    ("subject:update", "subject", "update", "Update subjects"),
    ("subject:delete", "subject", "delete", "Delete subjects"),
    ("subject:list", "subject", "list", "List subjects"),
    ("subject:export", "subject", "export", "Export subject data (GDPR)"),
    ("subject:erasure", "subject", "erasure", "Erase/anonymize subject data (GDPR)"),
    ("user:create", "user", "create", "Create users"),
    ("user:read", "user", "read", "View users"),
    ("user:update", "user", "update", "Update users"),
    ("user:deactivate", "user", "deactivate", "Deactivate users"),
    ("user:list", "user", "list", "List users"),
    ("role:create", "role", "create", "Create roles"),
    ("role:read", "role", "read", "View roles"),
    ("role:update", "role", "update", "Modify role name/description (not permissions)"),
    ("role:delete", "role", "delete", "Delete roles"),
    ("role:manage_permissions", "role", "manage_permissions", "Assign/remove permissions to/from roles (admin-only)"),
    ("role:assign", "role", "assign", "Assign roles to users"),
    ("user_role:read", "user_role", "read", "View user role assignments"),
    ("user_role:update", "user_role", "update", "Assign/remove non-admin roles to/from users"),
    ("user_role:assign_admin", "user_role", "assign_admin", "Assign or remove admin role (admin-only)"),
    ("permission:create", "permission", "create", "Create permissions"),
    ("permission:read", "permission", "read", "View permissions"),
    ("permission:delete", "permission", "delete", "Delete permissions"),
    ("document:create", "document", "create", "Upload documents"),
    ("document:read", "document", "read", "View documents"),
    ("document:delete", "document", "delete", "Delete documents"),
    ("event_schema:create", "event_schema", "create", "Create event schemas"),
    ("event_schema:read", "event_schema", "read", "View event schemas"),
    ("event_schema:update", "event_schema", "update", "Update event schemas"),
    ("workflow:create", "workflow", "create", "Create workflows"),
    ("workflow:read", "workflow", "read", "View workflows"),
    ("workflow:update", "workflow", "update", "Update workflows"),
    ("workflow:delete", "workflow", "delete", "Delete workflows"),
    ("audit:read", "audit", "read", "View audit log"),
    ("relationship_kind:read", "relationship_kind", "read", "View relationship kinds"),
    ("relationship_kind:create", "relationship_kind", "create", "Create relationship kinds"),
    ("relationship_kind:update", "relationship_kind", "update", "Update relationship kinds"),
    ("relationship_kind:delete", "relationship_kind", "delete", "Delete relationship kinds"),
    ("*:*", "*", "*", "Super admin - all permissions"),
]

# Permissions that must not be granted via resource wildcards (e.g. subject:*).
# GDPR-sensitive operations require explicit assignment (e.g. Administrator or DPO).
GDPR_SENSITIVE_PERMISSIONS: frozenset[str] = frozenset({"subject:export", "subject:erasure"})

DEFAULT_ROLES: dict[str, RoleData] = {
    "admin": {
        "name": "Administrator",
        "description": "Full system access with all permissions",
        "permissions": ["*:*"],
        "is_system": True,
    },
    "manager": {
        "name": "Manager",
        "description": "Can manage events, subjects, and users",
        "permissions": [
            "event:*",
            "subject:*",
            "user:read",
            "user:create",
            "user:list",
            "user_role:read",
            "user_role:update",
            "document:*",
            "event_schema:read",
            "workflow:*",
            "relationship_kind:*",
        ],
        "is_system": True,
    },
    "agent": {
        "name": "Agent",
        "description": "Can create and view events and subjects",
        "permissions": [
            "event:create",
            "event:read",
            "event:list",
            "subject:create",
            "subject:read",
            "subject:update",
            "subject:list",
            "document:create",
            "document:read",
            "event_schema:read",
            "relationship_kind:read",
        ],
        "is_system": True,
    },
    "auditor": {
        "name": "Auditor (Read-Only)",
        "description": "Read-only access to events, subjects, and audit log",
        "permissions": [
            "event:read",
            "event:list",
            "subject:read",
            "subject:list",
            "document:read",
            "event_schema:read",
            "audit:read",
            "relationship_kind:read",
        ],
        "is_system": True,
    },
}


class TenantInitializationService:
    """Initializes new tenant: permissions, roles, role-permissions, audit schema/subject."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._role_map: dict[str, dict[str, str]] = {}  # tenant_id -> {role_code -> role_id}

    async def initialize_tenant_infrastructure(self, tenant_id: str) -> None:
        """Create audit schema/subject, permissions, roles, role-permissions. Call before user creation."""
        # Idempotency: skip if tenant already has permissions (and thus roles/schema)
        existing = await self.db.execute(
            select(Permission.id).where(Permission.tenant_id == tenant_id).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            return  # Already initialized

        audit_schema = self._build_audit_schema(tenant_id, created_by=None)
        audit_subject = self._build_audit_subject(tenant_id)
        rel_added_schema = self._build_relationship_event_schema(
            tenant_id, RELATIONSHIP_ADDED_EVENT_TYPE
        )
        rel_removed_schema = self._build_relationship_event_schema(
            tenant_id, RELATIONSHIP_REMOVED_EVENT_TYPE
        )
        self.db.add(audit_schema)
        self.db.add(audit_subject)
        self.db.add(rel_added_schema)
        self.db.add(rel_removed_schema)
        await self.db.flush()

        permissions, permission_map = self._build_permissions(tenant_id)
        roles, role_permissions, role_map = self._build_roles(tenant_id, permission_map)
        self._role_map[tenant_id] = role_map

        self.db.add_all(permissions)
        await self.db.flush()
        self.db.add_all(roles)
        await self.db.flush()
        self.db.add_all(role_permissions)
        await self.db.flush()

    async def assign_admin_role(self, tenant_id: str, admin_user_id: str) -> None:
        """Assign admin role to user. Call after user creation."""
        tenant_roles = self._role_map.get(tenant_id, {})
        if "admin" not in tenant_roles:
            result = await self.db.execute(
                select(Role.id).where(Role.tenant_id == tenant_id, Role.code == "admin")
            )
            admin_role_id = result.scalar_one_or_none()
            if not admin_role_id:
                raise ResourceNotFoundException("role", f"admin:{tenant_id}")
        else:
            admin_role_id = tenant_roles["admin"]

        user_role = self._build_admin_assignment(
            tenant_id, admin_user_id, admin_role_id
        )
        self.db.add(user_role)
        await self.db.flush()

    def _build_permissions(
        self, tenant_id: str
    ) -> tuple[list[Permission], dict[str, str]]:
        permissions = []
        permission_map = {}
        for code, resource, action, description in SYSTEM_PERMISSIONS:
            perm_id = generate_cuid()
            permissions.append(
                Permission(
                    id=perm_id,
                    tenant_id=tenant_id,
                    code=code,
                    resource=resource,
                    action=action,
                    description=description,
                )
            )
            permission_map[code] = perm_id
        return permissions, permission_map

    def _build_roles(
        self, tenant_id: str, permission_map: dict[str, str]
    ) -> tuple[list[Role], list[RolePermission], dict[str, str]]:
        role_map = {}
        roles = []
        role_permissions = []
        for role_code, role_data in DEFAULT_ROLES.items():
            role_id = generate_cuid()
            roles.append(
                Role(
                    id=role_id,
                    tenant_id=tenant_id,
                    code=role_code,
                    name=role_data["name"],
                    description=role_data["description"],
                    is_system=role_data["is_system"],
                    is_active=True,
                )
            )
            role_map[role_code] = role_id
            for perm_pattern in role_data["permissions"]:
                for perm_id in self._resolve_permission_pattern(
                    perm_pattern, permission_map
                ):
                    role_permissions.append(
                        RolePermission(
                            id=generate_cuid(),
                            tenant_id=tenant_id,
                            role_id=role_id,
                            permission_id=perm_id,
                        )
                    )
        return roles, role_permissions, role_map

    @staticmethod
    def _resolve_permission_pattern(
        pattern: str, permission_map: dict[str, str]
    ) -> list[str]:
        # "*:*" is a reserved literal permission code for universal access. We do not
        # expand it to individual permissions; AuthorizationService treats it as
        # special (e.g. checks for "*:*" in permissions) and grants full access.
        if pattern.endswith(":*"):
            prefix = pattern[:-2]
            return [
                pid
                for code, pid in permission_map.items()
                if code.startswith(prefix + ":") and code not in GDPR_SENSITIVE_PERMISSIONS
            ]
        pid = permission_map.get(pattern)
        return [pid] if pid else []

    @staticmethod
    def _build_admin_assignment(
        tenant_id: str, user_id: str, admin_role_id: str
    ) -> UserRole:
        return UserRole(
            id=generate_cuid(),
            tenant_id=tenant_id,
            user_id=user_id,
            role_id=admin_role_id,
            assigned_by=user_id,
        )

    @staticmethod
    def _build_audit_schema(tenant_id: str, created_by: str | None) -> EventSchema:
        return EventSchema(
            id=generate_cuid(),
            tenant_id=tenant_id,
            event_type=SYSTEM_AUDIT_EVENT_TYPE,
            schema_definition=get_system_audit_schema_definition(),
            version=SYSTEM_AUDIT_SCHEMA_VERSION,
            is_active=True,
            created_by=created_by,
        )

    @staticmethod
    def _build_audit_subject(tenant_id: str) -> Subject:
        return Subject(
            id=generate_cuid(),
            tenant_id=tenant_id,
            subject_type=SYSTEM_AUDIT_SUBJECT_TYPE,
            external_ref=SYSTEM_AUDIT_SUBJECT_REF,
        )

    @staticmethod
    def _build_relationship_event_schema(
        tenant_id: str, event_type: str
    ) -> EventSchema:
        """Build EventSchema for relationship_added or relationship_removed (version 1)."""
        return EventSchema(
            id=generate_cuid(),
            tenant_id=tenant_id,
            event_type=event_type,
            schema_definition=get_relationship_event_schema_definition(),
            version=RELATIONSHIP_EVENT_SCHEMA_VERSION,
            is_active=True,
            created_by=None,
        )
