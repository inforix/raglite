import hashlib
import os
import tempfile
from pathlib import Path
from typing import Callable, Tuple
from urllib.parse import urlparse

from fastapi import UploadFile

from app.config import get_settings

settings = get_settings()


def _is_s3_backend() -> bool:
    return settings.object_store_backend.lower() == "s3"


def is_s3_path(path: str) -> bool:
    return path.startswith("s3://")


def is_s3_backend() -> bool:
    return _is_s3_backend()


def _s3_client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        use_ssl=settings.s3_secure,
    )


def _s3_bucket() -> str:
    if not settings.s3_bucket:
        raise ValueError("S3 bucket is not configured")
    return settings.s3_bucket


def _s3_prefix() -> str:
    return settings.s3_prefix.strip("/")


def _build_s3_key(tenant_id: str, dataset_id: str, document_id: str, filename: str) -> str:
    prefix = _s3_prefix()
    parts = [p for p in [prefix, "tenants", tenant_id, dataset_id, document_id, filename] if p]
    return "/".join(parts)


def _s3_url(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key}"


def _parse_s3_url(path: str) -> tuple[str, str]:
    parsed = urlparse(path)
    if parsed.scheme != "s3":
        raise ValueError("Invalid S3 path")
    return parsed.netloc, parsed.path.lstrip("/")


def save_upload_file(root: str, tenant_id: str, dataset_id: str, document_id: str, upload: UploadFile) -> Tuple[str, int, str]:
    """
    Save uploaded file to object store root and return (path, size_bytes, sha256).
    """

    from core.security import secure_filename
    filename = secure_filename(upload.filename or "upload")
    if _is_s3_backend():
        data = upload.file.read()
        upload.file.seek(0)
        size = len(data)
        sha = hashlib.sha256(data).hexdigest()
        key = _build_s3_key(tenant_id, dataset_id, document_id, filename)
        client = _s3_client()
        client.put_object(
            Bucket=_s3_bucket(),
            Key=key,
            Body=data,
            ContentType=upload.content_type or "application/octet-stream",
        )
        return _s3_url(_s3_bucket(), key), size, sha
    base = Path(root) / "tenants" / tenant_id / dataset_id / document_id
    base.mkdir(parents=True, exist_ok=True)
    dest = base / filename
    sha = hashlib.sha256()
    size = 0
    with dest.open("wb") as f:
        while True:
            chunk = upload.file.read(8192)
            if not chunk:
                break
            f.write(chunk)
            sha.update(chunk)
            size += len(chunk)
    upload.file.seek(0)
    return str(dest), size, sha.hexdigest()


def save_bytes(root: str, tenant_id: str, dataset_id: str, document_id: str, filename: str, data: bytes) -> str:
    from core.security import secure_filename
    filename = secure_filename(filename)
    if _is_s3_backend():
        key = _build_s3_key(tenant_id, dataset_id, document_id, filename)
        client = _s3_client()
        client.put_object(
            Bucket=_s3_bucket(),
            Key=key,
            Body=data,
            ContentType="application/octet-stream",
        )
        return _s3_url(_s3_bucket(), key)
    base = Path(root) / "tenants" / tenant_id / dataset_id / document_id
    base.mkdir(parents=True, exist_ok=True)
    dest = base / filename
    dest.write_bytes(data)
    return str(dest)


def compute_hash(data: bytes) -> str:
    sha = hashlib.sha256()
    sha.update(data)
    return sha.hexdigest()


def delete_dataset_store(root: str, tenant_id: str, dataset_id: str) -> None:
    if _is_s3_backend():
        prefix_parts = [p for p in [_s3_prefix(), "tenants", tenant_id, dataset_id] if p]
        prefix = "/".join(prefix_parts) + "/"
        _delete_s3_prefix(prefix)
        return
    base = Path(root) / "tenants" / tenant_id / dataset_id
    if base.exists():
        import shutil

        shutil.rmtree(base, ignore_errors=True)


def delete_document_store(root: str, tenant_id: str, dataset_id: str, document_id: str) -> None:
    if _is_s3_backend():
        prefix_parts = [p for p in [_s3_prefix(), "tenants", tenant_id, dataset_id, document_id] if p]
        prefix = "/".join(prefix_parts) + "/"
        _delete_s3_prefix(prefix)
        return
    base = Path(root) / "tenants" / tenant_id / dataset_id / document_id
    if base.exists():
        import shutil

        shutil.rmtree(base, ignore_errors=True)


def download_to_temp(path: str) -> tuple[str, Callable[[], None]]:
    bucket, key = _parse_s3_url(path)
    suffix = Path(key).suffix
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    client = _s3_client()
    try:
        client.download_fileobj(bucket, key, temp)
    finally:
        temp.close()

    def cleanup() -> None:
        try:
            os.remove(temp.name)
        except FileNotFoundError:
            pass

    return temp.name, cleanup


def ensure_local_path(path: str) -> tuple[str, Callable[[], None] | None]:
    if is_s3_path(path):
        local_path, cleanup = download_to_temp(path)
        return local_path, cleanup
    return path, None


def _delete_s3_prefix(prefix: str) -> None:
    client = _s3_client()
    bucket = _s3_bucket()
    continuation = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if continuation:
            kwargs["ContinuationToken"] = continuation
        response = client.list_objects_v2(**kwargs)
        objects = response.get("Contents", [])
        if objects:
            client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [{"Key": obj["Key"]} for obj in objects]},
            )
        if response.get("IsTruncated"):
            continuation = response.get("NextContinuationToken")
        else:
            break


def check_s3_connection() -> None:
    client = _s3_client()
    bucket = _s3_bucket()
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        client.list_objects_v2(Bucket=bucket, MaxKeys=1)
