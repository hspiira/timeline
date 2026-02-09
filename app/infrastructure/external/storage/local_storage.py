"""Local filesystem storage with path validation and atomic writes."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO, cast

import aiofiles
import aiofiles.os

from app.infrastructure.exceptions import (
    StorageAlreadyExistsError,
    StorageChecksumMismatchError,
    StorageDeleteError,
    StorageDownloadError,
    StorageNotFoundError,
    StoragePermissionError,
    StorageUploadError,
)
from app.shared.utils.datetime import from_timestamp_utc, utc_now


class LocalStorageService:
    """Local filesystem storage with atomic writes and path traversal protection.

    Paths are validated against storage_root. Writes use temp file + rename.
    Metadata stored in .meta.json sidecar. Pre-signed download via in-memory tokens.
    """

    CHUNK_SIZE = 64 * 1024  # 64KB

    _download_tokens: dict[str, tuple[str, datetime]] = {}  # token -> (storage_ref, expires_at)

    def __init__(self, storage_root: str, base_url: str | None = None) -> None:
        """Initialize local storage.

        Args:
            storage_root: Base directory for all files.
            base_url: Base URL for download endpoints (e.g. https://api.example.com).
        """
        self.storage_root = Path(storage_root).resolve()
        self.base_url = base_url.rstrip("/") if base_url else None
        self.storage_root.mkdir(parents=True, exist_ok=True, mode=0o750)

    def _get_full_path(self, storage_ref: str) -> Path:
        """Resolve and validate path under storage_root. Raises StoragePermissionError if traversal."""
        full_path = (self.storage_root / storage_ref).resolve()
        try:
            full_path.relative_to(self.storage_root)
        except ValueError as e:
            raise StoragePermissionError(storage_ref, "path_validation") from e
        return full_path

    async def _compute_checksum(self, file_path: Path) -> str:
        """SHA-256 of file."""
        sha256 = hashlib.sha256()
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                sha256.update(chunk)
        return sha256.hexdigest()

    async def _write_metadata(self, file_path: Path, metadata: dict[str, Any]) -> None:
        """Write JSON sidecar."""
        meta_path = file_path.with_suffix(file_path.suffix + ".meta.json")
        async with aiofiles.open(meta_path, "w") as f:
            await f.write(json.dumps(metadata, indent=2))
        os.chmod(meta_path, 0o640)

    async def _read_metadata(self, file_path: Path) -> dict[str, Any]:
        """Read JSON sidecar or empty dict."""
        meta_path = file_path.with_suffix(file_path.suffix + ".meta.json")
        if not meta_path.exists():
            return {}
        async with aiofiles.open(meta_path, "r") as f:
            content = await f.read()
            result = json.loads(content)
            return cast(dict[str, Any], result) if isinstance(result, dict) else {}

    async def upload(
        self,
        file_data: BinaryIO,
        storage_ref: str,
        expected_checksum: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Upload with atomic write and checksum validation. Idempotent if same checksum."""
        try:
            target_path = self._get_full_path(storage_ref)
            if target_path.exists():
                existing_checksum = await self._compute_checksum(target_path)
                if existing_checksum == expected_checksum:
                    existing_meta = await self._read_metadata(target_path)
                    return {
                        "storage_ref": storage_ref,
                        "checksum": existing_checksum,
                        "size": target_path.stat().st_size,
                        "uploaded_at": existing_meta.get("uploaded_at", utc_now().isoformat()),
                    }
                raise StorageAlreadyExistsError(storage_ref)

            target_path.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
            file_content = file_data.read()
            file_size = len(file_content)

            temp_fd, temp_path = tempfile.mkstemp(
                dir=target_path.parent,
                prefix=".tmp_",
                suffix=target_path.suffix,
            )
            try:
                async with aiofiles.open(temp_path, "wb") as f:
                    await f.write(file_content)
                os.chmod(temp_path, 0o640)
                computed = await self._compute_checksum(Path(temp_path))
                if computed != expected_checksum:
                    raise StorageChecksumMismatchError(
                        storage_ref, expected_checksum, computed
                    )
                os.rename(temp_path, target_path)
                upload_meta: dict[str, Any] = {
                    "storage_ref": storage_ref,
                    "checksum": computed,
                    "size": file_size,
                    "content_type": content_type,
                    "uploaded_at": utc_now().isoformat(),
                    "custom": metadata or {},
                }
                await self._write_metadata(target_path, upload_meta)
                return {
                    "storage_ref": storage_ref,
                    "checksum": computed,
                    "size": file_size,
                    "uploaded_at": upload_meta["uploaded_at"],
                }
            finally:
                if Path(temp_path).exists():
                    os.close(temp_fd)
                    os.unlink(temp_path)
        except (
            StorageChecksumMismatchError,
            StorageAlreadyExistsError,
            StoragePermissionError,
        ):
            raise
        except Exception as e:
            raise StorageUploadError(storage_ref, str(e)) from e

    async def download(self, storage_ref: str) -> AsyncIterator[bytes]:
        """Stream file content."""
        try:
            file_path = self._get_full_path(storage_ref)
            if not file_path.exists():
                raise StorageNotFoundError(f"File not found: {storage_ref}")
            async with aiofiles.open(file_path, "rb") as f:
                while True:
                    chunk = await f.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageDownloadError(storage_ref, str(e)) from e

    async def delete(self, storage_ref: str) -> bool:
        """Delete file and metadata. Returns True if deleted."""
        try:
            file_path = self._get_full_path(storage_ref)
            if not file_path.exists():
                return False
            await aiofiles.os.remove(file_path)
            meta_path = file_path.with_suffix(file_path.suffix + ".meta.json")
            if meta_path.exists():
                await aiofiles.os.remove(meta_path)
            parent = file_path.parent
            while parent != self.storage_root:
                try:
                    if not any(parent.iterdir()):
                        parent.rmdir()
                        parent = parent.parent
                    else:
                        break
                except OSError:
                    break
            return True
        except Exception as e:
            raise StorageDeleteError(storage_ref, str(e)) from e

    async def exists(self, storage_ref: str) -> bool:
        """Return True if file exists."""
        try:
            return self._get_full_path(storage_ref).exists()
        except Exception:
            return False

    async def get_metadata(self, storage_ref: str) -> dict[str, Any]:
        """Return size, content_type, checksum, last_modified, custom."""
        file_path = self._get_full_path(storage_ref)
        if not file_path.exists():
            raise StorageNotFoundError(f"File not found: {storage_ref}")
        stat = file_path.stat()
        stored = await self._read_metadata(file_path)
        return {
            "size": stat.st_size,
            "content_type": stored.get("content_type", "application/octet-stream"),
            "checksum": stored.get("checksum"),
            "last_modified": from_timestamp_utc(stat.st_mtime).isoformat(),
            "custom": stored.get("custom", {}),
        }

    async def generate_download_url(
        self,
        storage_ref: str,
        expiration: timedelta = timedelta(hours=1),
    ) -> str:
        """Return temporary download URL (token-based for local)."""
        if not await self.exists(storage_ref):
            raise StorageNotFoundError(f"File not found: {storage_ref}")
        token = secrets.token_urlsafe(32)
        expires_at = utc_now() + expiration
        self._download_tokens[token] = (storage_ref, expires_at)
        self._cleanup_expired_tokens()
        path = f"/api/storage/download/{token}"
        return f"{self.base_url}{path}" if self.base_url else path

    def _cleanup_expired_tokens(self) -> None:
        """Remove expired download tokens."""
        now = utc_now()
        for token in [t for t, (_, exp) in self._download_tokens.items() if exp <= now]:
            del self._download_tokens[token]

    def validate_download_token(self, token: str) -> str | None:
        """Return storage_ref if token valid and not expired."""
        if token not in self._download_tokens:
            return None
        storage_ref, expires_at = self._download_tokens[token]
        if utc_now() > expires_at:
            del self._download_tokens[token]
            return None
        return storage_ref
