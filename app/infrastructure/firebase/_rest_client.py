"""Thin Firestore REST API client (no firebase-admin).

Uses google-auth for service account tokens and Firestore REST v1.
Keeps serverless bundle small (avoids grpcio / firebase-admin).
All HTTP calls use httpx.AsyncClient so they do not block the event loop.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

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


async def _request_async(
    client: httpx.AsyncClient,
    url: str,
    method: str = "GET",
    body: dict | None = None,
    access_token: str | None = None,
) -> dict | None:
    """Perform async HTTP request to Firestore REST API. 404 returns None."""
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if method == "GET":
        resp = await client.get(url, headers=headers)
    elif method == "PATCH":
        resp = await client.patch(url, headers=headers, json=body)
    elif method == "DELETE":
        resp = await client.delete(url, headers=headers)
    else:
        raise ValueError(f"Unsupported method: {method!r}")
    if resp.status_code == 404:
        return None
    if resp.status_code not in (200, 204):
        resp.raise_for_status()
    if method == "DELETE":
        return {}
    raw = resp.content
    return json.loads(raw.decode()) if raw else {}


class DocumentReference:
    """Reference to a single document; matches firestore API style."""

    def __init__(self, client: "FirestoreRESTClient", path: str):
        self._client = client
        self._path = path

    async def set(self, data: dict[str, Any]) -> None:
        """Create or overwrite the document (PATCH with full replace)."""
        doc = encode_document(data)
        url = f"{_BASE}/{self._path}"
        await _request_async(
            self._client._http,
            url,
            method="PATCH",
            body=doc,
            access_token=await self._client.get_token(),
        )

    async def get(self) -> DocumentSnapshot | None:
        """Fetch the document; returns None if not found."""
        url = f"{_BASE}/{self._path}"
        out = await _request_async(
            self._client._http, url, access_token=await self._client.get_token()
        )
        if not out:
            return None
        return DocumentSnapshot(
            self._path.split("/")[-1], decode_document(out.get("fields"))
        )

    async def delete(self) -> None:
        """Delete the document. Idempotent if document is already missing (404)."""
        url = f"{_BASE}/{self._path}"
        await _request_async(
            self._client._http,
            url,
            method="DELETE",
            access_token=await self._client.get_token(),
        )


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

    async def stream(self) -> AsyncIterator[DocumentSnapshot]:
        """List documents in the collection (shallow)."""
        url = f"{_BASE}/{self._path}"
        out = await _request_async(
            self._client._http, url, access_token=await self._client.get_token()
        )
        if not out:
            return
        for doc in out.get("documents", []):
            name = doc.get("name", "")
            doc_id = name.split("/")[-1] if name else ""
            yield DocumentSnapshot(doc_id, decode_document(doc.get("fields")))


class FirestoreRESTClient:
    """Lightweight Firestore client using REST API (no firebase-admin)."""

    def __init__(
        self,
        project_id: str,
        credentials,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._project_id = project_id
        self._credentials = credentials
        self._prefix = f"projects/{project_id}/databases/(default)/documents"
        self._http = http_client if http_client is not None else httpx.AsyncClient(timeout=30.0)
        self._owns_http = http_client is None

    async def aclose(self) -> None:
        """Close the HTTP client only if we created it (do not close injected client)."""
        if self._owns_http:
            await self._http.aclose()

    async def get_token(self) -> str:
        """Return a valid access token; refreshes in thread pool to avoid blocking."""
        return await asyncio.to_thread(_get_access_token, self._credentials)

    def collection(self, collection_id: str) -> CollectionReference:
        return CollectionReference(self, f"{self._prefix}/{collection_id}")
