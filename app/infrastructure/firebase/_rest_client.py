"""Thin Firestore REST API client (no firebase-admin).

Uses google-auth for service account tokens and Firestore REST v1.
Keeps serverless bundle small (avoids grpcio / firebase-admin).
All HTTP calls use httpx.AsyncClient so they do not block the event loop.
"""

from __future__ import annotations

import asyncio
import json
from urllib.parse import quote
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.infrastructure.firebase._rest_encoding import (
    _encode_value,
    decode_document,
    encode_document,
)

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
    elif method == "POST":
        resp = await client.post(url, headers=headers, json=body)
    elif method == "DELETE":
        resp = await client.delete(url, headers=headers)
    else:
        raise ValueError(f"Unsupported method: {method!r}")
    if resp.status_code == 404:
        return None
    if resp.status_code == 409:
        raise DocumentExistsError("Document already exists")
    if resp.status_code not in (200, 204):
        resp.raise_for_status()
    if method == "DELETE":
        return {}
    raw = resp.content
    return json.loads(raw.decode()) if raw else {}


class DocumentExistsError(Exception):
    """Raised when createDocument returns 409 (document ID already exists)."""


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


_OP_MAP: dict[str, str] = {
    "==": "EQUAL",
    "!=": "NOT_EQUAL",
    "<": "LESS_THAN",
    "<=": "LESS_THAN_OR_EQUAL",
    ">": "GREATER_THAN",
    ">=": "GREATER_THAN_OR_EQUAL",
    "in": "IN",
    "not-in": "NOT_IN",
    "array_contains": "ARRAY_CONTAINS",
    "array-contains": "ARRAY_CONTAINS",
    "array_contains_any": "ARRAY_CONTAINS_ANY",
    "array-contains-any": "ARRAY_CONTAINS_ANY",
}


class _Query:
    """Fluent query builder for collection; runs via runQuery (filter/order/offset/limit on server)."""

    def __init__(
        self,
        client: "FirestoreRESTClient",
        parent: str,
        collection_id: str,
        *,
        where_field: str | None = None,
        where_op: str = "EQUAL",
        where_value: Any = None,
    ):
        self._client = client
        self._parent = parent
        self._collection_id = collection_id
        self._where_field = where_field
        self._where_op = _OP_MAP.get(where_op, where_op)
        self._where_value = where_value
        self._order_by_field: str | None = None
        self._order_direction: str = "ASCENDING"
        self._offset: int = 0
        self._limit: int = 100

    def order_by(self, field: str, direction: str = "ASCENDING") -> "_Query":
        self._order_by_field = field
        self._order_direction = direction
        return self

    def offset(self, n: int) -> "_Query":
        self._offset = n
        return self

    def limit(self, n: int) -> "_Query":
        self._limit = n
        return self

    async def stream(self) -> AsyncIterator[DocumentSnapshot]:
        """Execute the query and yield document snapshots."""
        structured: dict[str, Any] = {
            "from": [{"collectionId": self._collection_id}],
        }
        if self._where_field is not None:
            structured["where"] = {
                "fieldFilter": {
                    "field": {"fieldPath": self._where_field},
                    "op": self._where_op,
                    "value": _encode_value(self._where_value),
                }
            }
        if self._order_by_field is not None:
            structured["orderBy"] = [
                {
                    "field": {"fieldPath": self._order_by_field},
                    "direction": self._order_direction,
                }
            ]
        if self._offset:
            structured["offset"] = self._offset
        if self._limit:
            structured["limit"] = self._limit

        url = f"{_BASE}/{self._parent}:runQuery"
        body = {"structuredQuery": structured}
        resp = await _request_async(
            self._client._http,
            url,
            method="POST",
            body=body,
            access_token=await self._client.get_token(),
        )
        items = resp if isinstance(resp, list) else ([resp] if resp else [])
        for item in items:
            if "document" not in item:
                continue
            doc = item["document"]
            name = doc.get("name", "")
            doc_id = name.split("/")[-1] if name else ""
            yield DocumentSnapshot(doc_id, decode_document(doc.get("fields")))


class CollectionReference:
    """Reference to a collection; matches firestore API style."""

    def __init__(self, client: "FirestoreRESTClient", path: str):
        self._client = client
        self._path = path.rstrip("/")

    def document(self, document_id: str) -> DocumentReference:
        return DocumentReference(self._client, f"{self._path}/{document_id}")

    async def create(self, document_id: str, data: dict[str, Any]) -> None:
        """Create a document with the given ID (fail with DocumentExistsError if it exists)."""
        doc = encode_document(data)
        url = f"{_BASE}/{self._path}?documentId={quote(document_id, safe='')}"
        await _request_async(
            self._client._http,
            url,
            method="POST",
            body=doc,
            access_token=await self._client.get_token(),
        )

    def where(
        self, field: str, op: str, value: Any
    ) -> _Query:
        """Start a query with a filter. Use .order_by(), .offset(), .limit(), then .stream()."""
        parent = self._path.rsplit("/", 1)[0]
        collection_id = self._path.split("/")[-1]
        return _Query(
            self._client,
            parent,
            collection_id,
            where_field=field,
            where_op=op,
            where_value=value,
        )

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
