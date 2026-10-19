"""Storage factory."""
from __future__ import annotations

import logging
import threading
from typing import Optional

from app.core.config import settings
from app.services.storage.base import StorageBackend, StorageError
from app.services.storage.local import LocalStorage

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cached: Optional[StorageBackend] = None


def build_storage(backend: Optional[str] = None) -> StorageBackend:
    name = (backend or settings.STORAGE_BACKEND or "local").strip().lower()
    if name == "local":
        return LocalStorage(settings.STORAGE_LOCAL_PATH)
    if name == "s3":
        from app.services.storage.s3 import S3Storage

        return S3Storage(
            bucket=settings.S3_BUCKET,
            prefix=settings.S3_PREFIX,
            region=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
        )
    raise StorageError(f"Unknown STORAGE_BACKEND '{name}'. Supported: local, s3.")


def get_storage() -> StorageBackend:
    global _cached
    with _lock:
        if _cached is None:
            _cached = build_storage()
            logger.info("Storage backend initialised: %s", _cached.name)
        return _cached


def set_storage(backend: Optional[StorageBackend]) -> None:
    global _cached
    with _lock:
        _cached = backend


__all__ = ["build_storage", "get_storage", "set_storage"]
