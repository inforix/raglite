import asyncio
import io
import inspect
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.params import Depends as DependsParam
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import Headers

from app import deps
from app.api import routes
from infra import models
from infra.db import Base


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)()
    try:
        yield session
    finally:
        session.close()


def _create_user(db_session, user_id: str, *, is_superuser: bool) -> models.User:
    user = models.User(
        id=user_id,
        email=f"{user_id}@example.com",
        password_hash="hash",
        is_active=True,
        is_superuser=is_superuser,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _create_tenant(db_session, tenant_id: str) -> models.Tenant:
    tenant = models.Tenant(id=tenant_id, name=f"tenant-{tenant_id}")
    db_session.add(tenant)
    db_session.commit()
    return tenant


def _upload_file(filename: str, data: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def _assert_superuser_dep(fn) -> None:
    param = inspect.signature(fn).parameters.get("current_user")
    assert param is not None
    assert isinstance(param.default, DependsParam)
    assert param.default.dependency is routes.get_current_superuser_dep


class _FakeResponse:
    def __init__(self, status_code: int, headers: dict[str, str], chunks: list[bytes]):
        self.status_code = status_code
        self.headers = headers
        self._chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def iter_content(self, chunk_size: int = 8192):
        for chunk in self._chunks:
            yield chunk


def test_get_tenant_jwt_requires_explicit_tenant_id(db_session, monkeypatch):
    user = _create_user(db_session, "u-super", is_superuser=True)
    monkeypatch.setattr(deps, "decode_access_token", lambda token: {"sub": user.id})

    with pytest.raises(HTTPException) as exc_info:
        deps.get_tenant(
            authorization="Bearer jwt-token",
            x_tenant_id=None,
            tenant_id=None,
            db=db_session,
        )

    assert exc_info.value.status_code == 400
    assert "tenant_id is required" in exc_info.value.detail


def test_get_tenant_jwt_requires_existing_tenant(db_session, monkeypatch):
    user = _create_user(db_session, "u-super-2", is_superuser=True)
    monkeypatch.setattr(deps, "decode_access_token", lambda token: {"sub": user.id})

    with pytest.raises(HTTPException) as exc_info:
        deps.get_tenant(
            authorization="Bearer jwt-token",
            x_tenant_id=None,
            tenant_id="missing-tenant",
            db=db_session,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Tenant not found"


def test_get_tenant_jwt_forbids_non_superuser(db_session, monkeypatch):
    user = _create_user(db_session, "u-regular", is_superuser=False)
    tenant = _create_tenant(db_session, "tenant-a")
    monkeypatch.setattr(deps, "decode_access_token", lambda token: {"sub": user.id})

    with pytest.raises(HTTPException) as exc_info:
        deps.get_tenant(
            authorization="Bearer jwt-token",
            x_tenant_id=tenant.id,
            tenant_id=None,
            db=db_session,
        )

    assert exc_info.value.status_code == 403


def test_get_tenant_api_key_flow_still_works(db_session, monkeypatch):
    _create_tenant(db_session, "tenant-key")
    monkeypatch.setattr(deps, "decode_access_token", lambda token: (_ for _ in ()).throw(HTTPException(status_code=401)))
    monkeypatch.setattr(deps, "_lookup_api_key_db", lambda api_key, db=None: "tenant-key")

    context = deps.get_tenant(
        authorization="Bearer api-key-token",
        x_tenant_id=None,
        tenant_id=None,
        db=db_session,
    )

    assert context.tenant_id == "tenant-key"
    assert context.api_key == "api-key-token"


def test_tenant_and_settings_endpoints_require_superuser_dependency():
    _assert_superuser_dep(routes.get_settings_endpoint)
    _assert_superuser_dep(routes.create_tenant)
    _assert_superuser_dep(routes.list_tenants)
    _assert_superuser_dep(routes.get_tenant_by_id)
    _assert_superuser_dep(routes.update_tenant)
    _assert_superuser_dep(routes.delete_tenant)
    _assert_superuser_dep(routes.regenerate_tenant_key)


def test_settings_model_config_redacts_api_key():
    model = models.ModelConfig(
        id="mc-1",
        name="chat-default",
        type=models.ModelType.chat.value,
        endpoint="https://example.com/v1",
        api_key="secret-value",
        model="gpt-4o-mini",
    )

    out = routes._redact_model_config(model)

    assert out.api_key is None
    assert out.name == model.name
    assert out.endpoint == model.endpoint


def test_fetch_source_uri_enforces_streaming_and_no_redirects(monkeypatch):
    captured: dict[str, object] = {}

    def fake_get(url: str, **kwargs):
        captured.update(kwargs)
        return _FakeResponse(
            status_code=200,
            headers={"content-type": "text/plain; charset=utf-8"},
            chunks=[b"hello", b" world"],
        )

    monkeypatch.setattr(routes.requests, "get", fake_get)
    monkeypatch.setattr("core.security.is_safe_url", lambda url: True)

    filename, mime, size, content_hash, data = routes._fetch_source_uri_data("https://example.com/a.txt")

    assert captured["allow_redirects"] is False
    assert captured["stream"] is True
    assert filename == "a.txt"
    assert mime == "text/plain"
    assert size == 11
    assert len(content_hash) == 64
    assert data == b"hello world"


def test_fetch_source_uri_rejects_redirect(monkeypatch):
    monkeypatch.setattr(routes.requests, "get", lambda url, **kwargs: _FakeResponse(302, {"content-type": "text/plain"}, []))
    monkeypatch.setattr("core.security.is_safe_url", lambda url: True)

    with pytest.raises(HTTPException) as exc_info:
        routes._fetch_source_uri_data("https://example.com/redirect")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Redirects are not allowed for source_uri"


def test_upload_documents_cleans_up_on_duplicate(monkeypatch):
    tenant = deps.TenantContext(tenant_id="tenant-dup", api_key="key")
    deleted: list[tuple[str, str, str, str]] = []

    monkeypatch.setattr(routes.services, "ensure_dataset", lambda db, tenant_id, dataset_id: SimpleNamespace(embedder="embedder"))
    monkeypatch.setattr(routes.storage, "save_upload_file", lambda root, tenant_id, dataset_id, doc_id, upload: ("/tmp/file", 5, "hash-1"))
    monkeypatch.setattr(routes.storage, "delete_document_store", lambda root, tenant_id, dataset_id, doc_id: deleted.append((root, tenant_id, dataset_id, doc_id)))
    monkeypatch.setattr(routes, "find_duplicate_document", lambda db, tenant_id, dataset_id, content_hash: object())

    response = asyncio.run(
        routes.upload_documents(
            dataset_id="dataset-1",
            files=[_upload_file("doc.txt", b"hello", "text/plain")],
            source_uri=None,
            tenant=tenant,
            db=object(),
        )
    )

    assert response.job_ids == []
    assert len(deleted) == 1


def test_upload_documents_cleans_up_on_oversize(monkeypatch):
    tenant = deps.TenantContext(tenant_id="tenant-size", api_key="key")
    deleted: list[tuple[str, str, str, str]] = []
    oversize = routes.settings.max_file_size_mb * 1024 * 1024 + 1

    monkeypatch.setattr(routes.services, "ensure_dataset", lambda db, tenant_id, dataset_id: SimpleNamespace(embedder="embedder"))
    monkeypatch.setattr(
        routes.storage,
        "save_upload_file",
        lambda root, tenant_id, dataset_id, doc_id, upload: ("/tmp/file", oversize, "hash-1"),
    )
    monkeypatch.setattr(routes.storage, "delete_document_store", lambda root, tenant_id, dataset_id, doc_id: deleted.append((root, tenant_id, dataset_id, doc_id)))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            routes.upload_documents(
                dataset_id="dataset-1",
                files=[_upload_file("doc.txt", b"hello", "text/plain")],
                source_uri=None,
                tenant=tenant,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 400
    assert "File too large" in exc_info.value.detail
    assert len(deleted) == 1
