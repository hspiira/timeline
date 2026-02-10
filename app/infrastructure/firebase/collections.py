"""Firestore collection names (schema-in-code).

Firestore has no DDL or migrations. Collections are created automatically
when you first write a document. Use these constants so collection names
stay consistent and act as the single source of truth for the "schema".

Example:
    from app.infrastructure.firebase.client import get_firestore_client
    from app.infrastructure.firebase.collections import COLLECTION_TENANTS

    db = get_firestore_client()
    if db:
        await db.collection(COLLECTION_TENANTS).document(tenant_id).set({...})
"""

# Core multi-tenant entities (aligned with SQL table names / domain)
COLLECTION_TENANTS = "tenants"
COLLECTION_USERS = "users"
COLLECTION_SUBJECTS = "subjects"
COLLECTION_EVENTS = "events"
COLLECTION_EVENT_SCHEMAS = "event_schemas"
COLLECTION_DOCUMENTS = "documents"

# RBAC
COLLECTION_ROLES = "roles"
COLLECTION_PERMISSIONS = "permissions"
COLLECTION_ROLE_PERMISSIONS = "role_permissions"
COLLECTION_USER_ROLES = "user_roles"

# Workflows & integrations
COLLECTION_WORKFLOWS = "workflows"
COLLECTION_WORKFLOW_EXECUTIONS = "workflow_executions"
COLLECTION_EMAIL_ACCOUNTS = "email_accounts"
COLLECTION_OAUTH_PROVIDER_CONFIGS = "oauth_provider_configs"
