"""Firestore client (REST-based, no firebase-admin).

Initialized at app startup using either FIREBASE_SERVICE_ACCOUNT_KEY (JSON string,
e.g. on Vercel) or FIREBASE_SERVICE_ACCOUNT_PATH (file path).
Uses the Firestore REST API with google-auth to stay under Vercel's 250 MB
serverless bundle limit.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from app.core.config import get_settings  # noqa: E402
from app.infrastructure.firebase._rest_client import (  # noqa: E402
    FirestoreRESTClient,
    _get_credentials,
)

_firestore_client: FirestoreRESTClient | None = None


def _load_key_dict():
    """Return service account dict from env key or file path."""
    settings = get_settings()
    key_json = settings.firebase_service_account_key.get_secret_value() if settings.firebase_service_account_key else None
    if key_json:
        try:
            return json.loads(key_json)
        except json.JSONDecodeError as e:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY is not valid JSON") from e
    path = settings.firebase_service_account_path
    if path:
        resolved = Path(path).expanduser().resolve() if not Path(path).is_absolute() else Path(path)
        if not resolved.is_file():
            logger.warning(
                "FIREBASE_SERVICE_ACCOUNT_PATH set but file not found: %s (resolved: %s)",
                path,
                resolved,
            )
            return None
        with open(resolved, encoding="utf-8") as f:
            return json.load(f)
    return None


def init_firebase() -> bool:
    """Initialize the Firestore client (REST API + google-auth).

    Uses FIREBASE_SERVICE_ACCOUNT_KEY (full JSON string) if set, otherwise
    FIREBASE_SERVICE_ACCOUNT_PATH (file path). Safe to call when neither is set
    (no-op). Idempotent if already initialized. On invalid/malformed credentials
    or any initialization error, logs the exception and returns False so the app
    can start without Firebase.

    Returns:
        True if Firestore was initialized, False if disabled or on error.
    """
    global _firestore_client
    try:
        key_dict = _load_key_dict()
        if not key_dict:
            return False

        project_id = key_dict.get("project_id")
        if not project_id:
            logger.error("Firebase service account JSON missing 'project_id'")
            return False

        cred = _get_credentials(key_dict)
        _firestore_client = FirestoreRESTClient(project_id, cred)
        return True
    except Exception:
        logger.exception("Firebase initialization failed")
        return False


def get_firestore_client() -> FirestoreRESTClient | None:
    """Return the Firestore client, or None if not configured.

    Same API as the Firebase Admin client for the operations we use (all async):
    - await db.collection(name).document(id).set(data)
    - await db.collection(name).document(id).get() -> DocumentSnapshot | None
    - await db.collection(name).document(id).delete()
    - async for doc in db.collection(name).stream() -> DocumentSnapshot
    """
    return _firestore_client


async def close_firebase() -> None:
    """Close the Firestore client's HTTP connection pool. Call from app shutdown."""
    global _firestore_client
    if _firestore_client is not None:
        await _firestore_client.aclose()
        _firestore_client = None
        logger.info("Firestore HTTP client closed")
