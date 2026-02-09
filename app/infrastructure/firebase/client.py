"""Firebase Admin SDK and Firestore client.

Initialized at app startup using either FIREBASE_SERVICE_ACCOUNT_KEY (JSON string,
e.g. on Vercel) or FIREBASE_SERVICE_ACCOUNT_PATH (file path).
Use get_firestore_client() in routes or services; returns None if Firebase
is not configured.
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    from firebase_admin import firestore

_settings = get_settings()

# Module-level client; set by init_firebase() when configured.
_firestore_client: "firestore.Client | None" = None


def _get_credential():
    """Build Certificate credential from env key (JSON string) or file path."""
    import firebase_admin
    from firebase_admin import credentials

    key_json = _settings.firebase_service_account_key
    if key_json:
        try:
            key_dict = json.loads(key_json)
        except json.JSONDecodeError as e:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY is not valid JSON") from e
        return credentials.Certificate(key_dict)

    path = _settings.firebase_service_account_path
    if path and Path(path).is_file():
        return credentials.Certificate(path)

    return None


def init_firebase() -> bool:
    """Initialize the Firebase Admin SDK using the service account key.

    Uses FIREBASE_SERVICE_ACCOUNT_KEY (full JSON string) if set, otherwise
    FIREBASE_SERVICE_ACCOUNT_PATH (file path). Prefer the key on Vercel.
    Safe to call when neither is set (no-op). Idempotent if already initialized.

    Returns:
        True if Firebase was initialized, False if disabled or already init.
    """
    global _firestore_client
    cred = _get_credential()
    if cred is None:
        return False

    import firebase_admin
    from firebase_admin import firestore

    try:
        firebase_admin.get_app()
    except ValueError:
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
