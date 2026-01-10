import hashlib
import os
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile


def save_upload_file(root: str, tenant_id: str, dataset_id: str, document_id: str, upload: UploadFile) -> Tuple[str, int, str]:
    """
    Save uploaded file to object store root and return (path, size_bytes, sha256).
    """
    base = Path(root) / "tenants" / tenant_id / dataset_id / document_id
    base.mkdir(parents=True, exist_ok=True)
    filename = upload.filename or "upload"
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
    base = Path(root) / "tenants" / tenant_id / dataset_id
    if base.exists():
        import shutil

        shutil.rmtree(base, ignore_errors=True)


def delete_document_store(root: str, tenant_id: str, dataset_id: str, document_id: str) -> None:
    base = Path(root) / "tenants" / tenant_id / dataset_id / document_id
    if base.exists():
        import shutil

        shutil.rmtree(base, ignore_errors=True)
