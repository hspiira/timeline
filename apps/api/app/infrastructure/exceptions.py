"""Infrastructure exceptions for storage and external operations.

Storage errors extend TimelineException so presentation can map them
to HTTP responses consistently.
"""

from app.domain.exceptions import TimelineException


class StorageException(TimelineException):
    """Base exception for storage operations."""


class StorageNotFoundError(StorageException):
    """File or object not found in storage."""

    def __init__(self, file_path: str) -> None:
        super().__init__(
            f"File not found: {file_path}",
            "STORAGE_NOT_FOUND",
            {"file_path": file_path},
        )


class StorageUploadError(StorageException):
    """File upload failed."""

    def __init__(self, file_path: str, reason: str) -> None:
        super().__init__(
            f"Failed to upload file: {file_path}",
            "STORAGE_UPLOAD_ERROR",
            {"file_path": file_path, "reason": reason},
        )


class StorageDownloadError(StorageException):
    """File download failed."""

    def __init__(self, file_path: str, reason: str) -> None:
        super().__init__(
            f"Failed to download file: {file_path}",
            "STORAGE_DOWNLOAD_ERROR",
            {"file_path": file_path, "reason": reason},
        )


class StorageDeleteError(StorageException):
    """File deletion failed."""

    def __init__(self, file_path: str, reason: str) -> None:
        super().__init__(
            f"Failed to delete file: {file_path}",
            "STORAGE_DELETE_ERROR",
            {"file_path": file_path, "reason": reason},
        )


class StorageChecksumMismatchError(StorageException):
    """Checksum validation failed (corrupted or tampered)."""

    def __init__(self, file_path: str, expected: str, actual: str) -> None:
        super().__init__(
            f"Checksum mismatch for file: {file_path}",
            "STORAGE_CHECKSUM_ERROR",
            {"file_path": file_path, "expected": expected, "actual": actual},
        )


class StorageAlreadyExistsError(StorageException):
    """File already exists with different checksum."""

    def __init__(self, file_path: str) -> None:
        super().__init__(
            f"File already exists: {file_path}",
            "STORAGE_EXISTS_ERROR",
            {"file_path": file_path},
        )


class StorageNotSupportedError(StorageException):
    """Operation not supported by this storage backend."""

    def __init__(self, operation: str, backend: str) -> None:
        super().__init__(
            f"Operation '{operation}' not supported by {backend} backend",
            "STORAGE_NOT_SUPPORTED",
            {"operation": operation, "backend": backend},
        )


class StorageQuotaExceededError(StorageException):
    """Storage quota exceeded."""

    def __init__(self, used: int, quota: int) -> None:
        super().__init__(
            f"Storage quota exceeded: {used}/{quota} bytes",
            "STORAGE_QUOTA_EXCEEDED",
            {"used": used, "quota": quota},
        )


class StoragePermissionError(StorageException):
    """Insufficient permissions for storage operation."""

    def __init__(self, file_path: str, operation: str) -> None:
        super().__init__(
            f"Permission denied for {operation} on {file_path}",
            "STORAGE_PERMISSION_ERROR",
            {"file_path": file_path, "operation": operation},
        )
