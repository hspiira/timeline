"""Storage: local filesystem and S3-compatible backends.

Factory creates backend from app.core.config. Implementations implement
StorageProtocol (upload, download, delete, exists, get_metadata, generate_download_url).
"""

from app.infrastructure.external.storage.factory import StorageFactory
from app.infrastructure.external.storage.local_storage import LocalStorageService
from app.infrastructure.external.storage.protocol import StorageProtocol
from app.infrastructure.external.storage.s3_storage import S3StorageService

__all__ = [
    "LocalStorageService",
    "S3StorageService",
    "StorageFactory",
    "StorageProtocol",
]
