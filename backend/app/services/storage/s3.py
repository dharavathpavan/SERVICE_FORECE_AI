"""S3-compatible private object storage (AWS S3, MinIO, R2...)."""
from __future__ import annotations

import logging
from typing import Optional

from app.services.storage.base import ObjectNotFound, StorageBackend, StorageError

logger = logging.getLogger(__name__)


class S3Storage(StorageBackend):
    name = "s3"

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
    ) -> None:
        if not bucket:
            raise StorageError("S3_BUCKET must be set when STORAGE_BACKEND=s3.")
        try:
            import boto3  # imported lazily so the dependency stays optional
        except ImportError as exc:  # pragma: no cover
            raise StorageError(
                "boto3 is required for S3 storage. Install it with `pip install boto3`."
            ) from exc

        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self._client = boto3.client("s3", region_name=region, endpoint_url=endpoint_url or None)

    def _key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        full = self._key(key)
        self._client.put_object(Bucket=self.bucket, Key=full, Body=data, ContentType=content_type)
        return f"s3://{self.bucket}/{full}"

    def get(self, key: str) -> bytes:
        full = self._key(key)
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=full)
        except self._client.exceptions.NoSuchKey as exc:
            raise ObjectNotFound(f"Object not found: {key}") from exc
        return resp["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=self._key(key))

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=self._key(key))
            return True
        except Exception:
            return False

    def presigned_url(self, key: str, expires_seconds: int = 3600) -> Optional[str]:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": self._key(key)},
                ExpiresIn=expires_seconds,
            )
        except Exception:  # pragma: no cover
            return None
