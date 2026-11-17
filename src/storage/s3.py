"""S3-compatible file storage - CONTRACT for other domains (owner: P3).

Usage::

    from src.storage import s3

    await s3.upload_file("avatars/1/abc.png", data, "image/png")
    url = s3.get_file_url("avatars/1/abc.png")

Store only the key (``"avatars/1/abc.png"``) in the database, never the URL:
links are temporary and are generated on every read.
"""

from functools import lru_cache
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from starlette.concurrency import run_in_threadpool

from src.core.config import settings
from src.core.exceptions import AppError


class StorageUnavailableError(AppError):
    """The file storage cannot be reached or rejected the request."""

    status_code = 503


def _make_client(endpoint_url: str) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


@lru_cache
def _client() -> Any:
    """Client for real requests to the storage (inside Docker: ``http://minio:9000``)."""
    return _make_client(settings.MINIO_ENDPOINT)


@lru_cache
def _public_client() -> Any:
    """Client used only to sign links for the browser. It makes no network calls."""
    return _make_client(settings.MINIO_PUBLIC_ENDPOINT)


def _ensure_bucket(client: Any) -> None:
    try:
        client.head_bucket(Bucket=settings.MINIO_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=settings.MINIO_BUCKET)


def _upload(key: str, data: bytes, content_type: str) -> None:
    client = _client()
    _ensure_bucket(client)
    client.put_object(
        Bucket=settings.MINIO_BUCKET, Key=key, Body=data, ContentType=content_type
    )


def _delete(key: str) -> None:
    _client().delete_object(Bucket=settings.MINIO_BUCKET, Key=key)


async def upload_file(key: str, data: bytes, content_type: str) -> None:
    """Upload ``data`` under ``key``. The bucket is created on first use.

    Raises:
        StorageUnavailableError: the storage cannot be reached or rejected the upload (503).
    """
    try:
        await run_in_threadpool(_upload, key, data, content_type)
    except (BotoCoreError, ClientError) as exc:
        raise StorageUnavailableError("File storage is unavailable, try again later") from exc


async def delete_file(key: str) -> None:
    """Delete the object. A missing object is not an error.

    Raises:
        StorageUnavailableError: the storage cannot be reached (503).
    """
    try:
        await run_in_threadpool(_delete, key)
    except (BotoCoreError, ClientError) as exc:
        raise StorageUnavailableError("File storage is unavailable, try again later") from exc


def get_file_url(key: str) -> str:
    """Return a temporary link to the file, valid for ``AVATAR_URL_TTL_SECONDS`` seconds."""
    url: str = _public_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.MINIO_BUCKET, "Key": key},
        ExpiresIn=settings.AVATAR_URL_TTL_SECONDS,
    )
    return url
