"""Firebase Admin SDK and Firestore client.

Initialized once at app startup when FIREBASE_SERVICE_ACCOUNT_PATH is set.
Use get_firestore_client() in routes or services; returns None if Firebase
is not configured.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    from firebase_admin import firestore

_settings = get_settings()

# Module-level client; set by init_firebase() when configured.
_firestore_client: "firestore.Client | None" = None


def init_firebase() -> bool:
    """Initialize the Firebase Admin SDK using the service account key.

    Call once at application startup. Safe to call when path is not set
    (no-op). Idempotent if path is set and already initialized.

    Returns:
        True if Firebase was initialized, False if disabled or already init.
    """
    global _firestore_client
    path = _settings.firebase_service_account_path
    if not path or not Path(path).is_file():
        return False

    import firebase_admin
    from firebase_admin import credentials, firestore

    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(path)
        firebase_admin.initialize_app(cred)

    _firestore_client = firestore.client()
    return True


def get_firestore_client() -> "firestore.Client | None":
    """Return the Firestore client, or None if Firebase is not configured.

    Use for Firestore operations, e.g.:

        db = get_firestore_client()
        if db:
            doc_ref = db.collection('users').document('alovelace')
            doc_ref.set({'first': 'Ada', 'last': 'Lovelace', 'born': 1815})
    """
    return _firestore_client
