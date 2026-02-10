"""Storage: local filesystem and S3-compatible backends.

Factory creates backend from app.core.config. Implementations are loaded
lazily inside StorageFactory.create_storage_service() so that:
- Default (local) only requires aiofiles (main dependency).
- S3 backend only loads boto3 when used; install with: uv sync --extra storage.

Implementations implement StorageProtocol (upload, download, delete, exists,
get_metadata, generate_download_url).
"""

from app.infrastructure.external.storage.factory import StorageFactory
from app.infrastructure.external.storage.protocol import StorageProtocol

__all__ = [
    "StorageFactory",
    "StorageProtocol",
]
