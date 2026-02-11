"""Firestore-backed services (swappable with Postgres)."""

from app.infrastructure.firebase.services.tenant_init_firestore import (
    FirestoreTenantInitializationService,
)

__all__ = ["FirestoreTenantInitializationService"]
