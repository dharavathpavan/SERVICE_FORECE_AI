"""Object storage abstraction (recordings, uploaded documents)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class StorageError(Exception):
    code = "storage_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ObjectNotFound(StorageError):
    code = "object_not_found"


class StorageBackend(ABC):
    """Private object storage. Keys are always tenant-scoped by callers."""

    name: str = "abstract"

    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Store bytes and return a stable URI/reference for the object."""

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Retrieve bytes. Raises :class:`ObjectNotFound` when absent."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete an object. Idempotent."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Whether the object exists."""

    def presigned_url(self, key: str, expires_seconds: int = 3600) -> Optional[str]:
        """Return a time-limited URL when the backend supports it."""
        return None


def build_key(organization_id: str, category: str, filename: str) -> str:
    """Deterministic, tenant-scoped object key."""
    safe = filename.strip().replace("\\", "/").lstrip("/")
    return f"{organization_id}/{category}/{safe}"
