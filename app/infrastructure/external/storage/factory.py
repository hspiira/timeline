"""Storage service factory: creates local or S3 backend from settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.infrastructure.external.storage.protocol import StorageProtocol

if TYPE_CHECKING:
    from app.core.config import Settings


class StorageFactory:
    """Factory for storage service instances based on configuration."""

    @staticmethod
    def create_storage_service(settings: "Settings | None" = None) -> StorageProtocol:
        """Create storage service from settings.

        Args:
            settings: Application settings; if None, uses get_settings().

        Returns:
            LocalStorageService or S3StorageService.

        Raises:
            ValueError: Unknown backend or missing required config.
        """
        from app.core.config import get_settings

        s = settings or get_settings()
        backend = s.storage_backend.lower()

        if backend == "local":
            from app.infrastructure.external.storage.local_storage import (
                LocalStorageService,
            )

            if not s.storage_root:
                raise ValueError("STORAGE_ROOT required for local backend")
            return LocalStorageService(
                storage_root=s.storage_root,
                base_url=s.storage_base_url,
            )
        if backend == "s3":
            if not s.s3_bucket:
                raise ValueError("S3_BUCKET required for s3 backend")
            try:
                from app.infrastructure.external.storage.s3_storage import (
                    S3StorageService,
                )
            except ImportError as e:
                raise ValueError(
                    "S3 backend requires boto3. Install with: uv sync --extra storage"
                ) from e
            return S3StorageService(
                bucket=s.s3_bucket,
                region=s.s3_region,
                endpoint_url=s.s3_endpoint_url,
                access_key=s.s3_access_key,
                secret_key=s.s3_secret_key,
            )
        raise ValueError(
            f"Unknown storage backend: {backend}. Supported: 'local', 's3'"
        )
