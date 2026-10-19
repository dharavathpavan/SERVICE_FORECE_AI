"""Local filesystem storage backend (development and single-node deploys)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from app.services.storage.base import ObjectNotFound, StorageBackend, StorageError


class LocalStorage(StorageBackend):
    name = "local"

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Prevent path traversal: the resolved path must stay under root.
        candidate = (self.root / key).resolve()
        if not str(candidate).startswith(str(self.root)):
            raise StorageError("Invalid object key (path traversal rejected).")
        return candidate

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"file://{path}"

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise ObjectNotFound(f"Object not found: {key}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def presigned_url(self, key: str, expires_seconds: int = 3600) -> Optional[str]:
        return f"file://{self._path(key)}" if self.exists(key) else None
