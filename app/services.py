import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from passlib.hash import pbkdf2_sha256

from app.config import get_settings
from app.schemas import DatasetCreate, DatasetUpdate, DatasetOut, DocumentUploadResponse, JobOut, DocumentOut, DocumentUpdate, DocumentListResponse, QueryHistoryResponse, QueryHistoryItem
from app.settings_service import get_app_settings_db, get_allowed_model_names
from app.schemas_tenant import TenantCreate, TenantOut
from core import storage, vectorstore
from infra import models
from infra.models import ModelType
from app import tasks

settings = get_settings()
vs = vectorstore.get_vector_store()


def create_dataset(db: Session, tenant_id: str, payload: DatasetCreate) -> DatasetOut:
    embedder_name = (payload.embedder or "").strip()
    if not embedder_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Embedder is required")
    allowed_embedders = get_allowed_model_names(db, ModelType.embedder)
    if embedder_name not in allowed_embedders:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Embedder not allowed")
    ds = models.Dataset(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        embedder=embedder_name,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return DatasetOut(
        id=ds.id,
        tenant_id=ds.tenant_id,
        name=ds.name,
        description=ds.description,
        embedder=ds.embedder,
        created_at=ds.created_at,
    )


def list_datasets(db: Session, tenant_id: str) -> List[DatasetOut]:
    rows = db.query(models.Dataset).filter(models.Dataset.tenant_id == tenant_id, models.Dataset.deleted_at.is_(None)).all()
    return [
        DatasetOut(
            id=r.id,
            tenant_id=r.tenant_id,
            name=r.name,
            description=r.description,
            embedder=r.embedder,
            created_at=r.created_at,
        )
        for r in rows
    ]


def get_dataset(db: Session, tenant_id: str, dataset_id: str) -> DatasetOut:
    """Get a single dataset by ID."""
    ds = (
        db.query(models.Dataset)
        .filter(
            models.Dataset.id == dataset_id,
            models.Dataset.tenant_id == tenant_id,
            models.Dataset.deleted_at.is_(None)
        )
        .first()
    )
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return DatasetOut(
        id=ds.id,
        tenant_id=ds.tenant_id,
        name=ds.name,
        description=ds.description,
        embedder=ds.embedder,
        created_at=ds.created_at,
    )


def update_dataset(db: Session, tenant_id: str, dataset_id: str, payload: DatasetUpdate) -> DatasetOut:
    """Update a dataset."""
    app_settings = get_app_settings_db(db)
    ds = (
        db.query(models.Dataset)
        .filter(
            models.Dataset.id == dataset_id,
            models.Dataset.tenant_id == tenant_id,
            models.Dataset.deleted_at.is_(None)
        )
        .first()
    )
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    embedder_changed = False
    
    # Update only provided fields
    if payload.name is not None:
        ds.name = payload.name
    if payload.description is not None:
        ds.description = payload.description
    if payload.embedder is not None:
        allowed_embedders = get_allowed_model_names(db, ModelType.embedder)
        if payload.embedder not in allowed_embedders:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Embedder not allowed")
        if payload.embedder != ds.embedder:
            if not payload.confirm_embedder_change:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Changing embedder will re-embed all documents. Set confirm_embedder_change=true to proceed.",
                )
            ds.embedder = payload.embedder
            embedder_changed = True
    elif not ds.embedder:
        ds.embedder = app_settings.default_embedder
    
    db.commit()
    db.refresh(ds)
    if embedder_changed:
        job_id = create_reindex_job(db, tenant_id, dataset_id, ds.embedder)
        enqueue_reindex_job(job_id, tenant_id, dataset_id, ds.embedder)
    return DatasetOut(
        id=ds.id,
        tenant_id=ds.tenant_id,
        name=ds.name,
        description=ds.description,
        embedder=ds.embedder,
        created_at=ds.created_at,
    )


def ensure_dataset(db: Session, tenant_id: str, dataset_id: str) -> models.Dataset:
    ds = (
        db.query(models.Dataset)
        .filter(models.Dataset.id == dataset_id, models.Dataset.tenant_id == tenant_id, models.Dataset.deleted_at.is_(None))
        .first()
    )
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return ds


def create_tenant_with_key(db: Session, payload: TenantCreate) -> TenantOut:
    # Check for duplicate tenant name
    existing = db.query(models.Tenant).filter(models.Tenant.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant name already exists")
    
    tenant = models.Tenant(id=str(uuid.uuid4()), name=payload.name, description=payload.description)
    api_key_value = str(uuid.uuid4()).replace("-", "")[:64]
    key_hash = pbkdf2_sha256.hash(api_key_value)
    api_key = models.ApiKey(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        name=f"default-{payload.name}",
        key_hash=key_hash,
        active=True,
    )
    db.add(tenant)
    db.add(api_key)
    db.commit()
    db.refresh(tenant)
    return TenantOut(id=tenant.id, name=tenant.name, description=tenant.description, api_key=api_key_value, created_at=tenant.created_at)


def list_tenants(db: Session) -> List[TenantOut]:
    rows = db.query(models.Tenant).all()
    # Don't expose API keys in list responses
    return [TenantOut(id=t.id, name=t.name, description=t.description, api_key="***", created_at=t.created_at) for t in rows]


def get_tenant(db: Session, tenant_id: str) -> TenantOut:
    """Get a single tenant by ID."""
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    # We only store hashed API keys, cannot retrieve the original
    return TenantOut(
        id=tenant.id, 
        name=tenant.name, 
        description=tenant.description, 
        api_key="<hidden - only shown at creation>"
    )


def update_tenant(db: Session, tenant_id: str, payload: TenantCreate) -> TenantOut:
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    
    # Check for duplicate tenant name (excluding current tenant)
    existing = db.query(models.Tenant).filter(
        models.Tenant.name == payload.name,
        models.Tenant.id != tenant_id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant name already exists")
    
    tenant.name = payload.name
    tenant.description = payload.description
    db.commit()
    db.refresh(tenant)
    return TenantOut(id=tenant.id, name=tenant.name, description=tenant.description, api_key=None, created_at=tenant.created_at)


def regenerate_tenant_api_key(db: Session, tenant_id: str) -> dict:
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    db.query(models.ApiKey).filter(
        models.ApiKey.tenant_id == tenant_id,
        models.ApiKey.active.is_(True),
    ).update({models.ApiKey.active: False}, synchronize_session=False)

    api_key_value = str(uuid.uuid4()).replace("-", "")[:64]
    key_hash = pbkdf2_sha256.hash(api_key_value)
    api_key = models.ApiKey(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=f"regenerated-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        key_hash=key_hash,
        active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return {"tenant_id": tenant.id, "api_key": api_key_value, "created_at": api_key.created_at}


def delete_tenant(db: Session, tenant_id: str):
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    db.query(models.ApiKey).filter(models.ApiKey.tenant_id == tenant_id).delete()
    db.query(models.Dataset).filter(models.Dataset.tenant_id == tenant_id).delete()
    db.query(models.Document).filter(models.Document.tenant_id == tenant_id).delete()
    db.query(models.Chunk).filter(models.Chunk.tenant_id == tenant_id).delete()
    db.query(models.Job).filter(models.Job.tenant_id == tenant_id).delete()
    db.delete(tenant)
    db.commit()


def soft_delete_dataset(db: Session, tenant_id: str, dataset_id: str):
    ds = (
        db.query(models.Dataset)
        .filter(
            models.Dataset.id == dataset_id,
            models.Dataset.tenant_id == tenant_id,
            models.Dataset.deleted_at.is_(None),
        )
        .first()
    )
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    ds.deleted_at = datetime.utcnow()
    db.commit()
    try:
        vs.delete_dataset(tenant_id, dataset_id)
    except Exception:
        pass
    try:
        from core import opensearch_bm25

        client = opensearch_bm25.get_bm25_client()
        if client:
            client.delete_dataset(tenant_id, dataset_id)
    except Exception:
        pass
    try:
        storage.delete_dataset_store(settings.object_store_root, tenant_id, dataset_id)
    except Exception:
        pass


def create_document_jobs(db: Session, tenant_id: str, dataset_id: str, docs: List[models.Document], embedder: Optional[str]) -> DocumentUploadResponse:
    job_ids: List[str] = []
    for doc in docs:
        job = models.Job(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type=models.JobType.ingest.value,
            status=models.JobStatus.pending.value,
            payload={"document_id": doc.id, "dataset_id": dataset_id, "embedder": embedder},
        )
        db.add(job)
        job_ids.append(job.id)
        doc.status = "pending"
    db.commit()
    for job_id, doc in zip(job_ids, docs):
        tasks.enqueue_ingest(
            {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "dataset_id": dataset_id,
                "document_id": doc.id,
                "path": doc.path,
                "mime_type": doc.mime_type,
                "embedder": embedder,
            }
        )
    return DocumentUploadResponse(job_ids=job_ids)


def record_documents(
    db: Session,
    tenant_id: str,
    dataset_id: str,
    uploads: List[tuple[str, str, Optional[str], Optional[int], str, str, Optional[str]]],
):
    docs = []
    for doc_id, filename, mime, size, path, content_hash, language in uploads:
        doc = models.Document(
            id=doc_id,
            tenant_id=tenant_id,
            dataset_id=dataset_id,
            filename=filename,
            mime_type=mime,
            size_bytes=size,
            status="pending",
            path=path,
            content_hash=content_hash,
            language=language,
        )
        db.add(doc)
        docs.append(doc)
    db.commit()
    return docs


def soft_delete_document(db: Session, tenant_id: str, document_id: str):
    doc = (
        db.query(models.Document)
        .filter(
            models.Document.id == document_id,
            models.Document.tenant_id == tenant_id,
            models.Document.deleted_at.is_(None),
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    doc.deleted_at = datetime.utcnow()
    db.query(models.Chunk).filter(models.Chunk.document_id == document_id).delete()
    db.commit()
    try:
        vs.delete_document(tenant_id, doc.dataset_id, document_id)
    except Exception:
        pass
    try:
        storage.delete_document_store(settings.object_store_root, tenant_id, doc.dataset_id, document_id)
    except Exception:
        pass
    try:
        from core import opensearch_bm25

        client = opensearch_bm25.get_bm25_client()
        if client:
            client.delete_document(tenant_id, doc.dataset_id, document_id)
    except Exception:
        pass


def list_documents(db: Session, tenant_id: str, dataset_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> DocumentListResponse:
    """List documents with pagination."""
    query = db.query(models.Document).filter(
        models.Document.tenant_id == tenant_id,
        models.Document.deleted_at.is_(None)
    )
    if dataset_id:
        query = query.filter(models.Document.dataset_id == dataset_id)
    
    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    offset = (page - 1) * page_size
    docs = query.order_by(models.Document.created_at.desc()).offset(offset).limit(page_size).all()
    
    items = [
        DocumentOut(
            id=d.id,
            dataset_id=d.dataset_id,
            filename=d.filename,
            mime_type=d.mime_type,
            size_bytes=d.size_bytes,
            language=d.language,
            status=d.status,
            source_uri=d.source_uri,
            created_at=d.created_at.isoformat() if d.created_at else ""
        )
        for d in docs
    ]
    
    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


def get_document(db: Session, tenant_id: str, document_id: str) -> DocumentOut:
    """Get a single document by ID."""
    doc = (
        db.query(models.Document)
        .filter(
            models.Document.id == document_id,
            models.Document.tenant_id == tenant_id,
            models.Document.deleted_at.is_(None)
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    return DocumentOut(
        id=doc.id,
        dataset_id=doc.dataset_id,
        filename=doc.filename,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        language=doc.language,
        status=doc.status,
        source_uri=doc.source_uri,
        created_at=doc.created_at.isoformat() if doc.created_at else ""
    )


def log_query(db: Session, tenant_id: str, query_text: str, dataset_ids: Optional[List[str]] = None):
    entry = models.QueryLog(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        dataset_ids=dataset_ids or [],
        query=query_text,
    )
    db.add(entry)
    db.commit()
    return entry


def list_query_history(
    db: Session,
    tenant_id: str,
    page: int = 1,
    page_size: int = 20,
) -> QueryHistoryResponse:
    query = db.query(models.QueryLog).filter(models.QueryLog.tenant_id == tenant_id)
    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size
    rows = query.order_by(models.QueryLog.created_at.desc()).offset(offset).limit(page_size).all()
    items = [
        QueryHistoryItem(
            id=row.id,
            tenant_id=row.tenant_id,
            dataset_ids=row.dataset_ids or [],
            query=row.query,
            created_at=row.created_at.isoformat() if row.created_at else "",
        )
        for row in rows
    ]
    return QueryHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def update_document(db: Session, tenant_id: str, document_id: str, payload: DocumentUpdate) -> DocumentOut:
    """Update a document's metadata."""
    doc = (
        db.query(models.Document)
        .filter(
            models.Document.id == document_id,
            models.Document.tenant_id == tenant_id,
            models.Document.deleted_at.is_(None)
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    # Update only provided fields
    if payload.filename is not None:
        doc.filename = payload.filename
    if payload.source_uri is not None:
        doc.source_uri = payload.source_uri
    
    db.commit()
    db.refresh(doc)
    return DocumentOut(
        id=doc.id,
        dataset_id=doc.dataset_id,
        filename=doc.filename,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        language=doc.language,
        status=doc.status,
        source_uri=doc.source_uri,
        created_at=doc.created_at.isoformat() if doc.created_at else ""
    )


def get_job(db: Session, tenant_id: str, job_id: str) -> JobOut:
    job = (
        db.query(models.Job)
        .filter(models.Job.id == job_id, models.Job.tenant_id == tenant_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobOut(id=job.id, status=job.status, progress=job.progress, error=job.error)


def create_reindex_job(db: Session, tenant_id: str, dataset_id: str, embedder: Optional[str]) -> str:
    job = models.Job(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        type=models.JobType.reindex.value,
        status=models.JobStatus.pending.value,
        payload={"dataset_id": dataset_id, "embedder": embedder},
    )
    db.add(job)
    # Update dataset embedder if provided
    if embedder:
        ds = db.query(models.Dataset).filter(
            models.Dataset.id == dataset_id,
            models.Dataset.tenant_id == tenant_id
        ).first()
        if ds:
            ds.embedder = embedder
    db.commit()
    return job.id


def enqueue_reindex_job(job_id: str, tenant_id: str, dataset_id: str, embedder: Optional[str]):
    tasks.enqueue_reindex({"job_id": job_id, "tenant_id": tenant_id, "dataset_id": dataset_id, "embedder": embedder})
