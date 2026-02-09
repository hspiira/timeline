"""Firebase Admin SDK and Firestore integration."""

from app.infrastructure.firebase.client import (
    get_firestore_client,
    init_firebase,
)

__all__ = [
    "get_firestore_client",
    "init_firebase",
]
