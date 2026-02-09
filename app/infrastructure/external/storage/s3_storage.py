"""S3-compatible object storage (AWS S3, MinIO, etc.) with checksums and presigned URLs."""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncIterator
from datetime import timedelta
from io import BytesIO
from typing import Any, BinaryIO

import boto3
from botocore.exceptions import ClientError

from app.infrastructure.exceptions import (
    StorageAlreadyExistsError,
    StorageChecksumMismatchError,
    StorageDeleteError,
    StorageDownloadError,
    StorageNotFoundError,
    StorageUploadError,
)


class S3StorageService:
    """S3-compatible storage with server-side encryption and presigned URLs.

    Uses boto3 (sync) via asyncio.to_thread for async API. Compatible with
    AWS S3, MinIO, DigitalOcean Spaces.
    """

    CHUNK_SIZE = 64 * 1024  # 64KB

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """Initialize S3 client.

        Args:
            bucket: Bucket name.
            region: AWS region.
            endpoint_url: Custom endpoint (MinIO/Spaces).
            access_key: Optional; uses env/IAM if not set.
            secret_key: Optional.
        """
        self.bucket = bucket
        self.region = region
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        extra = {} if endpoint_url is None else {"endpoint_url": endpoint_url}
        self._client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            **extra,
        )

    def _compute_checksum_sync(self, file_data: BinaryIO) -> str:
        """SHA-256 of file content (sync)."""
        sha256 = hashlib.sha256()
        file_data.seek(0)
        while True:
            chunk = file_data.read(self.CHUNK_SIZE)
            if not chunk:
                break
            sha256.update(chunk)
        file_data.seek(0)
        return sha256.hexdigest()

    async def _compute_checksum(self, file_data: BinaryIO) -> str:
        """SHA-256 in thread to avoid blocking."""
        return await asyncio.to_thread(self._compute_checksum_sync, file_data)

    async def upload(
        self,
        file_data: BinaryIO,
        storage_ref: str,
        expected_checksum: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Upload with checksum validation. Idempotent if same checksum."""
        def _upload() -> dict[str, Any]:
            try:
                try:
                    head = self._client.head_object(
                        Bucket=self.bucket,
                        Key=storage_ref,
                    )
                    existing = (head.get("Metadata") or {}).get("sha256")
                    if existing == expected_checksum:
                        return {
                            "storage_ref": storage_ref,
                            "checksum": existing,
                            "size": head["ContentLength"],
                            "uploaded_at": head["LastModified"].isoformat(),
                        }
                    raise StorageAlreadyExistsError(storage_ref)
                except ClientError as e:
                    if e.response["Error"]["Code"] != "404":
                        raise

                file_data.seek(0)
                body = file_data.read()
                file_size = len(body)
                computed = hashlib.sha256(body).hexdigest()
                if computed != expected_checksum:
                    raise StorageChecksumMismatchError(
                        storage_ref, expected_checksum, computed
                    )
                meta = {"sha256": computed, "original-size": str(file_size)}
                if metadata:
                    for k, v in metadata.items():
                        meta[k.lower().replace("_", "-")] = v

                self._client.put_object(
                    Bucket=self.bucket,
                    Key=storage_ref,
                    Body=body,
                    ContentType=content_type,
                    ServerSideEncryption="AES256",
                    Metadata=meta,
                )
                head = self._client.head_object(Bucket=self.bucket, Key=storage_ref)
                return {
                    "storage_ref": storage_ref,
                    "checksum": computed,
                    "size": file_size,
                    "uploaded_at": head["LastModified"].isoformat(),
                }
            except (StorageChecksumMismatchError, StorageAlreadyExistsError):
                raise
            except Exception as e:
                raise StorageUploadError(storage_ref, str(e)) from e

        try:
            return await asyncio.to_thread(_upload)
        except (StorageChecksumMismatchError, StorageAlreadyExistsError):
            raise
        except Exception as e:
            raise StorageUploadError(storage_ref, str(e)) from e

    async def download(self, storage_ref: str) -> AsyncIterator[bytes]:
        """Stream object content."""
        def _get() -> bytes:
            try:
                resp = self._client.get_object(Bucket=self.bucket, Key=storage_ref)
                return resp["Body"].read()
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    raise StorageNotFoundError(f"File not found: {storage_ref}") from e
                raise StorageDownloadError(storage_ref, str(e)) from e

        try:
            body = await asyncio.to_thread(_get)
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageDownloadError(storage_ref, str(e)) from e
        buf = BytesIO(body)
        while True:
            chunk = buf.read(self.CHUNK_SIZE)
            if not chunk:
                break
            yield chunk

    async def delete(self, storage_ref: str) -> bool:
        """Delete object. Returns True if deleted."""
        def _delete() -> bool:
            try:
                self._client.head_object(Bucket=self.bucket, Key=storage_ref)
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    return False
                raise StorageDeleteError(storage_ref, str(e)) from e
            self._client.delete_object(Bucket=self.bucket, Key=storage_ref)
            return True

        try:
            return await asyncio.to_thread(_delete)
        except Exception as e:
            raise StorageDeleteError(storage_ref, str(e)) from e

    async def exists(self, storage_ref: str) -> bool:
        """Return True if object exists."""
        def _exists() -> bool:
            try:
                self._client.head_object(Bucket=self.bucket, Key=storage_ref)
                return True
            except ClientError:
                return False

        return await asyncio.to_thread(_exists)

    async def get_metadata(self, storage_ref: str) -> dict[str, Any]:
        """Return size, content_type, checksum, last_modified, custom."""
        def _head() -> dict[str, Any]:
            try:
                head = self._client.head_object(Bucket=self.bucket, Key=storage_ref)
                meta = head.get("Metadata") or {}
                return {
                    "size": head["ContentLength"],
                    "content_type": head.get(
                        "ContentType", "application/octet-stream"
                    ),
                    "checksum": meta.get("sha256"),
                    "last_modified": head["LastModified"].isoformat(),
                    "custom": meta,
                }
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    raise StorageNotFoundError(f"File not found: {storage_ref}") from e
                raise StorageDownloadError(storage_ref, str(e)) from e

        try:
            return await asyncio.to_thread(_head)
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageDownloadError(storage_ref, str(e)) from e

    async def generate_download_url(
        self,
        storage_ref: str,
        expiration: timedelta = timedelta(hours=1),
    ) -> str:
        """Return presigned GET URL."""
        def _presign() -> str:
            try:
                self._client.head_object(Bucket=self.bucket, Key=storage_ref)
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    raise StorageNotFoundError(f"File not found: {storage_ref}") from e
                raise StorageDownloadError(storage_ref, str(e)) from e
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": storage_ref},
                ExpiresIn=int(expiration.total_seconds()),
            )

        try:
            return await asyncio.to_thread(_presign)
        except StorageNotFoundError:
            raise
        except Exception as e:
            raise StorageDownloadError(storage_ref, str(e)) from e
