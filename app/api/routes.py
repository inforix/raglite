import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
import requests

from app import services
from app.config import get_settings
from app.dedup import find_duplicate_document
from app.deps import TenantContext, get_tenant
from app.schemas import DatasetCreate, DatasetUpdate, DatasetOut, DocumentUploadResponse, JobOut, QueryRequest, QueryResponse, DocumentOut, DocumentUpdate, DocumentListResponse
from app.schemas_tenant import TenantCreate, TenantOut
from core import embedder, rewriter, reranker, vectorstore, opensearch_bm25
from core import storage
from infra import models
from infra.db import get_db

router = APIRouter()
settings = get_settings()
vs = vectorstore.get_vector_store()
bm25_client = opensearch_bm25.get_bm25_client()


@router.post("/tenants", status_code=status.HTTP_201_CREATED, tags=["tenants"], response_model=TenantOut)
async def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    return services.create_tenant_with_key(db, payload)


@router.get("/tenants", tags=["tenants"], response_model=List[TenantOut])
async def list_tenants(db: Session = Depends(get_db)):
    return services.list_tenants(db)


@router.get("/tenants/{tenant_id}", tags=["tenants"], response_model=TenantOut)
async def get_tenant_by_id(tenant_id: str, db: Session = Depends(get_db)):
    return services.get_tenant(db, tenant_id)


@router.put("/tenants/{tenant_id}", tags=["tenants"], response_model=TenantOut)
async def update_tenant(tenant_id: str, payload: TenantCreate, db: Session = Depends(get_db)):
    return services.update_tenant(db, tenant_id, payload)


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tenants"])
async def delete_tenant(tenant_id: str, db: Session = Depends(get_db)):
    services.delete_tenant(db, tenant_id)
    return {}


@router.post("/datasets", status_code=status.HTTP_201_CREATED, tags=["datasets"], response_model=DatasetOut)
async def create_dataset(
    payload: DatasetCreate, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)
) -> DatasetOut:
    return services.create_dataset(db, tenant.tenant_id, payload)


@router.get("/datasets", tags=["datasets"], response_model=List[DatasetOut])
async def list_datasets(tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)) -> List[DatasetOut]:
    return services.list_datasets(db, tenant.tenant_id)


@router.get("/datasets/{dataset_id}", tags=["datasets"], response_model=DatasetOut)
async def get_dataset(dataset_id: str, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)) -> DatasetOut:
    return services.get_dataset(db, tenant.tenant_id, dataset_id)


@router.put("/datasets/{dataset_id}", tags=["datasets"], response_model=DatasetOut)
async def update_dataset(
    dataset_id: str,
    payload: DatasetUpdate,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db)
) -> DatasetOut:
    return services.update_dataset(db, tenant.tenant_id, dataset_id, payload)


@router.post("/documents", status_code=status.HTTP_202_ACCEPTED, tags=["documents"], response_model=DocumentUploadResponse)
async def upload_documents(
    dataset_id: str,
    files: Optional[List[UploadFile]] = File(default=None),
    source_uri: Optional[str] = None,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    dataset = services.ensure_dataset(db, tenant.tenant_id, dataset_id)
    uploads = []
    incoming_files = list(files) if files else []
    
    # Validate that at least one source is provided
    if not incoming_files and not source_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either files or source_uri must be provided",
        )
    
    if incoming_files and len(incoming_files) > settings.max_files_per_upload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files; max {settings.max_files_per_upload}",
        )
    if source_uri:
        try:
            resp = requests.get(source_uri, timeout=settings.parse_timeout_seconds)
            resp.raise_for_status()
            filename = source_uri.split("/")[-1] or "remote"
            doc_id = str(uuid.uuid4())
            path = storage.save_bytes(
                settings.object_store_root, tenant.tenant_id, dataset_id, doc_id, filename, resp.content
            )
            mime = resp.headers.get("content-type", "application/octet-stream")
            size = len(resp.content)
            content_hash = storage.compute_hash(resp.content)
            uploads.append((doc_id, filename, mime, size, path, content_hash, None))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to fetch source_uri: {e}")

    for f in incoming_files:
        if f.content_type not in settings.allowed_mime_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported MIME type: {f.content_type}",
            )
        doc_id = str(uuid.uuid4())
        path, size, content_hash = storage.save_upload_file(
            settings.object_store_root, tenant.tenant_id, dataset_id, doc_id, f
        )
        if size > settings.max_file_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large; max {settings.max_file_size_mb} MB",
            )
        dup = find_duplicate_document(db, tenant.tenant_id, dataset_id, content_hash)
        if dup:
            continue  # skip duplicates
        uploads.append((doc_id, f.filename or "upload", f.content_type, size, path, content_hash, None))
    if not uploads:
        return DocumentUploadResponse(job_ids=[])
    docs = services.record_documents(db, tenant.tenant_id, dataset_id, uploads)
    job_resp = services.create_document_jobs(db, tenant.tenant_id, dataset_id, docs, dataset.embedder)
    return job_resp


@router.get("/documents", tags=["documents"], response_model=DocumentListResponse)
async def list_documents(
    dataset_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    """List documents with pagination. Optionally filter by dataset_id."""
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page size must be between 1 and 100")
    return services.list_documents(db, tenant.tenant_id, dataset_id, page, page_size)


@router.get("/documents/{document_id}", tags=["documents"], response_model=DocumentOut)
async def get_document(
    document_id: str,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> DocumentOut:
    """Get a single document by ID."""
    return services.get_document(db, tenant.tenant_id, document_id)


@router.put("/documents/{document_id}", tags=["documents"], response_model=DocumentOut)
async def update_document(
    document_id: str,
    payload: DocumentUpdate,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> DocumentOut:
    """Update document metadata (filename, source_uri)."""
    return services.update_document(db, tenant.tenant_id, document_id, payload)


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_202_ACCEPTED, tags=["datasets"])
async def delete_dataset(dataset_id: str, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    services.soft_delete_dataset(db, tenant.tenant_id, dataset_id)
    return {"status": "accepted", "dataset_id": dataset_id}


@router.delete("/documents/{document_id}", status_code=status.HTTP_202_ACCEPTED, tags=["documents"])
async def delete_document(document_id: str, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    services.soft_delete_document(db, tenant.tenant_id, document_id)
    return {"status": "accepted", "document_id": document_id}


@router.get("/jobs/{job_id}", tags=["jobs"], response_model=JobOut)
async def get_job(job_id: str, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)) -> JobOut:
    return services.get_job(db, tenant.tenant_id, job_id)


@router.post("/query", tags=["query"], response_model=QueryResponse)
async def query(request: QueryRequest, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)) -> QueryResponse:
    rewritten = rewriter.rewrite_query(request.query, tenant.tenant_id) if request.rewrite else None
    qtext = rewritten or request.query
    
    # Use the first dataset's embedder if specified, otherwise default
    query_embedder = None
    if request.dataset_ids:
        first_ds = db.query(models.Dataset).filter(
            models.Dataset.id == request.dataset_ids[0],
            models.Dataset.tenant_id == tenant.tenant_id
        ).first()
        if first_ds:
            query_embedder = first_ds.embedder
    
    vector = embedder.embed_texts([qtext], model_name=query_embedder)[0]
    dataset_ids = request.dataset_ids or []
    results_raw = vs.query(tenant.tenant_id, dataset_ids, vector, k=request.k, filters=request.filters)
    bm25_hits = []
    if settings.enable_bm25 and dataset_ids and bm25_client:
        bm25_hits = bm25_client.search(tenant.tenant_id, dataset_ids, qtext, k=request.k)
    # results_raw expected format: list of dict with payload keys
    results = []
    for hit in results_raw:
        payload = hit.get("payload", {})
        results.append(
            {
                "chunk_id": hit.get("id", ""),
                "document_id": payload.get("document_id", ""),
                "dataset_id": payload.get("dataset_id", ""),
                "score": hit.get("score", 0.0),
                "text": payload.get("text", ""),
                "source_uri": payload.get("source_uri"),
                "meta": payload.get("meta"),
            }
        )
    merged = {}
    for r in results:
        merged[r["chunk_id"]] = r
    for hit in bm25_hits:
        cid = hit.get("id", "")
        payload = hit.get("payload", {})
        if cid in merged:
            merged[cid]["score"] += hit.get("score", 0.0)
        else:
            merged[cid] = {
                "chunk_id": cid,
                "document_id": payload.get("document_id", ""),
                "dataset_id": payload.get("dataset_id", ""),
                "score": hit.get("score", 0.0),
                "text": payload.get("text", ""),
                "source_uri": payload.get("source_uri"),
                "meta": payload.get("meta"),
            }
    merged_list = sorted(merged.values(), key=lambda x: x.get("score", 0), reverse=True)[: request.k]
    reranked = reranker.rerank(qtext, merged_list)
    return QueryResponse(query=request.query, rewritten=rewritten, results=reranked)


@router.post("/reindex", status_code=status.HTTP_202_ACCEPTED, tags=["maintenance"])
async def reindex(dataset_id: str, embedder: Optional[str] = None, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    ds = services.ensure_dataset(db, tenant.tenant_id, dataset_id)
    if embedder and embedder not in settings.allowed_embedders:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Embedder not allowed")
    target_embedder = embedder or ds.embedder
    job_id = services.create_reindex_job(db, tenant.tenant_id, dataset_id, target_embedder)
    services.enqueue_reindex_job(job_id, tenant.tenant_id, dataset_id, target_embedder)
    return {"status": "accepted", "job_id": job_id, "dataset_id": dataset_id, "embedder": target_embedder}
