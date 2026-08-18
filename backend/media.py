"""MinIO helpers for menu image uploads."""
from __future__ import annotations

import io
import uuid

from flask import current_app
from minio import Minio
from minio.error import S3Error


def get_minio_client() -> Minio:
    cfg = current_app.config
    return Minio(
        cfg["MINIO_ENDPOINT"],
        access_key=cfg["MINIO_ACCESS_KEY"],
        secret_key=cfg["MINIO_SECRET_KEY"],
        secure=cfg["MINIO_SECURE"],
    )


def ensure_bucket():
    client = get_minio_client()
    bucket = current_app.config["MINIO_BUCKET"]
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            policy = (
                '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":'
                '{"AWS":["*"]},"Action":["s3:GetObject"],"Resource":["arn:aws:s3:::%s/*"]}]}'
                % bucket
            )
            try:
                client.set_bucket_policy(bucket, policy)
            except S3Error:
                pass
    except S3Error as e:
        current_app.logger.warning("MinIO bucket ensure failed: %s", e)


def upload_image(file_storage, prefix: str = "menu") -> str:
    ensure_bucket()
    client = get_minio_client()
    bucket = current_app.config["MINIO_BUCKET"]
    content_type = file_storage.content_type or "application/octet-stream"
    ext = "bin"
    if "jpeg" in content_type or "jpg" in content_type:
        ext = "jpg"
    elif "png" in content_type:
        ext = "png"
    elif "webp" in content_type:
        ext = "webp"
    elif "gif" in content_type:
        ext = "gif"
    object_name = f"{prefix}/{uuid.uuid4().hex}.{ext}"
    data = file_storage.read()
    client.put_object(
        bucket,
        object_name,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    # Prefer live public URL (ngrok / request) so phones can load images
    from public_url import resolve_public_base_url

    public = resolve_public_base_url().rstrip("/")
    return f"{public}/media/{bucket}/{object_name}"
