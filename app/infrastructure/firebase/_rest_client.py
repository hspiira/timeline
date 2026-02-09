"""Thin Firestore REST API client (no firebase-admin).

Uses google-auth for service account tokens and Firestore REST v1.
Keeps serverless bundle small (avoids grpcio / firebase-admin).
"""

import json
import urllib.error
import urllib.request
from typing import Any

from app.infrastructure.firebase._rest_encoding import decode_document, encode_document

_FIRESTORE_SCOPE = "https://www.googleapis.com/auth/datastore"
_BASE = "https://firestore.googleapis.com/v1"


def _get_credentials(key_dict: dict):
    """Return google.oauth2.service_account.Credentials for Firestore."""
    from google.oauth2 import service_account

    return service_account.Credentials.from_service_account_info(
        key_dict, scopes=[_FIRESTORE_SCOPE]
    )


def _get_access_token(credentials) -> str:
    from google.auth.transport.requests import Request

    if not credentials.valid:
        credentials.refresh(Request())
    return credentials.token


def _request(
    url: str,
    method: str = "GET",
    body: dict | None = None,
    access_token: str | None = None,
) -> dict | None:
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode()) if resp.length else {}
            return None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


class DocumentReference:
    """Reference to a single document; matches firestore API style."""

    def __init__(self, client: "FirestoreRESTClient", path: str):
        self._client = client
        self._path = path

    def set(self, data: dict[str, Any]) -> None:
        """Create or overwrite the document (PATCH with full replace)."""
        doc = encode_document(data)
        url = f"{_BASE}/{self._path}"
        _request(url, method="PATCH", body=doc, access_token=self._client._token())

    def get(self) -> "DocumentSnapshot | None":
        """Fetch the document; returns None if not found."""
        url = f"{_BASE}/{self._path}"
        out = _request(url, access_token=self._client._token())
        if not out:
            return None
        return DocumentSnapshot(self._path.split("/")[-1], decode_document(out.get("fields")))

    def delete(self) -> None:
        """Delete the document."""
        url = f"{_BASE}/{self._path}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self._client._token()}"}, method="DELETE")
        urllib.request.urlopen(req, timeout=30)


class DocumentSnapshot:
    """Snapshot of a document (id + data)."""

    def __init__(self, id_: str, data: dict):
        self.id = id_
        self._data = data

    def to_dict(self) -> dict:
        return self._data


class CollectionReference:
    """Reference to a collection; matches firestore API style."""

    def __init__(self, client: "FirestoreRESTClient", path: str):
        self._client = client
        self._path = path.rstrip("/")

    def document(self, document_id: str) -> DocumentReference:
        return DocumentReference(self._client, f"{self._path}/{document_id}")

    def stream(self):
        """List documents in the collection (shallow)."""
        # List documents: GET .../documents/{collectionId} (returns {documents: [...]})
        url = f"{_BASE}/{self._path}"
        out = _request(url, access_token=self._client._token())
        if not out:
            return
        for doc in out.get("documents", []):
            name = doc.get("name", "")
            doc_id = name.split("/")[-1] if name else ""
            yield DocumentSnapshot(doc_id, decode_document(doc.get("fields")))


class FirestoreRESTClient:
    """Lightweight Firestore client using REST API (no firebase-admin)."""

    def __init__(self, project_id: str, credentials) -> None:
        self._project_id = project_id
        self._credentials = credentials
        self._prefix = f"projects/{project_id}/databases/(default)/documents"

    def _token(self) -> str:
        return _get_access_token(self._credentials)

    def collection(self, collection_id: str) -> CollectionReference:
        return CollectionReference(self, f"{self._prefix}/{collection_id}")
