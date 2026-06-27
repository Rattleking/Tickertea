"""Immutable raw-payload storage.

Every connector's RawItem is written here BEFORE normalization, and the returned URI is
stored on ingest_event.raw_uri. This is the traceability anchor: a signal's evidence chain
ends at the exact bytes a source returned. Raw objects are never mutated or deleted.

Two backends, selected by RAW_STORE_BACKEND:
  - "s3"   : S3-compatible object storage (MinIO in dev, S3/R2 in prod) -> s3://… URIs.
  - "file" : local filesystem (default; this machine has no object store) -> file://… URIs.

Both compute the SAME partitioned key (`<source_key>/<YYYY/MM/DD>/<external_id>`) so a
deployment can lift-and-shift the local tree into a bucket without rewriting raw_uris'
path component.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from tickertea.common.settings import get_settings


def _object_key(source_key: str, external_id: str) -> str:
    """Partition by source and ingest date for cheap lifecycle/auditing."""
    day = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    return f"{source_key}/{day}/{_safe(external_id)}"


class FileRawStore:
    """Filesystem backend: writes immutable payloads under a local root, returns file:// URIs."""

    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def put(
        self,
        source_key: str,
        external_id: str,
        body: bytes | str | dict[str, Any],
        content_type: str = "application/json",
    ) -> str:
        key = _object_key(source_key, external_id)
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_to_bytes(body, content_type))
        return path.resolve().as_uri()  # file:///…


class RawStore:
    def __init__(self, client: Any, bucket: str) -> None:
        self._client = client
        self._bucket = bucket
        self._ensured = False

    def _ensure_bucket(self) -> None:
        if self._ensured:
            return
        from botocore.exceptions import ClientError

        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)
        self._ensured = True

    def put(
        self,
        source_key: str,
        external_id: str,
        body: bytes | str | dict[str, Any],
        content_type: str = "application/json",
    ) -> str:
        """Store one raw payload and return its s3:// URI.

        The key is partitioned by source and ingest date for cheap lifecycle/auditing:
        `<source_key>/<YYYY/MM/DD>/<external_id>`.
        """
        self._ensure_bucket()
        data = _to_bytes(body, content_type)
        key = _object_key(source_key, external_id)
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
        )
        return f"s3://{self._bucket}/{key}"


def _to_bytes(body: bytes | str | dict[str, Any], content_type: str) -> bytes:
    if isinstance(body, bytes):
        return body
    if isinstance(body, str):
        return body.encode("utf-8")
    return json.dumps(body, default=str, separators=(",", ":")).encode("utf-8")


def _safe(external_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in external_id)[:200]


@lru_cache(maxsize=1)
def get_rawstore() -> RawStore | FileRawStore:
    s = get_settings()
    if s.raw_store_backend == "file":
        return FileRawStore(s.raw_store_dir)

    # boto3 is only needed for the S3 backend; import lazily so local-dev (file backend)
    # doesn't depend on it being installed/configured.
    import boto3
    from botocore.client import Config

    client = boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        region_name=s.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    return RawStore(client, s.s3_bucket)
