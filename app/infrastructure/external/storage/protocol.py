"""Storage service protocol (DIP). Implementations: LocalStorageService, S3StorageService."""

from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any, BinaryIO, Protocol


class StorageProtocol(Protocol):
    """Protocol for object storage backends (local, S3-compatible)."""

    async def upload(
        self,
        file_data: BinaryIO,
        storage_ref: str,
        expected_checksum: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Upload file with checksum verification. Idempotent if same checksum."""
        ...

    async def download(self, storage_ref: str) -> AsyncIterator[bytes]:
        """Stream file content."""
        ...

    async def delete(self, storage_ref: str) -> bool:
        """Delete file. Returns True if deleted, False if not found."""
        ...

    async def exists(self, storage_ref: str) -> bool:
        """Return True if file exists."""
        ...

    async def get_metadata(self, storage_ref: str) -> dict[str, Any]:
        """Return metadata without downloading."""
        ...

    async def generate_download_url(
        self,
        storage_ref: str,
        expiration: timedelta = timedelta(hours=1),
    ) -> str:
        """Return temporary download URL (presigned for S3, token URL for local)."""
        ...
