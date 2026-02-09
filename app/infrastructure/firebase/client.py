"""Firestore client (REST-based, no firebase-admin).

Initialized at app startup using either FIREBASE_SERVICE_ACCOUNT_KEY (JSON string,
e.g. on Vercel) or FIREBASE_SERVICE_ACCOUNT_PATH (file path).
Uses the Firestore REST API with google-auth to stay under Vercel's 250 MB
serverless bundle limit.
"""

import json
from pathlib import Path

from app.core.config import get_settings
from app.infrastructure.firebase._rest_client import (
    FirestoreRESTClient,
    _get_credentials,
)

_settings = get_settings()
_firestore_client: FirestoreRESTClient | None = None


def _load_key_dict():
    """Return service account dict from env key or file path."""
    key_json = _settings.firebase_service_account_key
    if key_json:
        try:
            return json.loads(key_json)
        except json.JSONDecodeError as e:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY is not valid JSON") from e
    path = _settings.firebase_service_account_path
    if path and Path(path).is_file():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def init_firebase() -> bool:
    """Initialize the Firestore client (REST API + google-auth).

    Uses FIREBASE_SERVICE_ACCOUNT_KEY (full JSON string) if set, otherwise
    FIREBASE_SERVICE_ACCOUNT_PATH (file path). Safe to call when neither is set
    (no-op). Idempotent if already initialized.

    Returns:
        True if Firestore was initialized, False if disabled or already init.
    """
    global _firestore_client
    key_dict = _load_key_dict()
    if not key_dict:
        return False

    project_id = key_dict.get("project_id")
    if not project_id:
        raise ValueError("Service account JSON must contain 'project_id'")

    cred = _get_credentials(key_dict)
    _firestore_client = FirestoreRESTClient(project_id, cred)
    return True


def get_firestore_client() -> FirestoreRESTClient | None:
    """Return the Firestore client, or None if not configured.

    Same API as the Firebase Admin client for the operations we use:
    - db.collection(name).document(id).set(data)
    - db.collection(name).document(id).get() -> DocumentSnapshot | None
    - db.collection(name).stream() -> iterable of DocumentSnapshot
    """
    return _firestore_client
