from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app import services
from app.config import get_settings
from app.deps import TenantContext, get_tenant
from app.schemas import DatasetCreate, DatasetOut, DocumentUploadResponse, JobOut, QueryRequest, QueryResponse
from infra.db import get_db

router = APIRouter()
settings = get_settings()


@router.post("/tenants", status_code=status.HTTP_201_CREATED, tags=["tenants"])
async def create_tenant():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/datasets", status_code=status.HTTP_201_CREATED, tags=["datasets"], response_model=DatasetOut)
async def create_dataset(
    payload: DatasetCreate, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)
) -> DatasetOut:
    return services.create_dataset(db, tenant.tenant_id, payload)


@router.get("/datasets", tags=["datasets"], response_model=List[DatasetOut])
async def list_datasets(tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    return services.list_datasets(db, tenant.tenant_id)


@router.post("/documents", status_code=status.HTTP_202_ACCEPTED, tags=["documents"], response_model=DocumentUploadResponse)
async def upload_documents(
    dataset_id: str,
    files: List[UploadFile] = File(...),
    source_uri: Optional[str] = None,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    if len(files) > settings.max_files_per_upload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files; max {settings.max_files_per_upload}",
        )
    for f in files:
        if f.content_type not in settings.allowed_mime_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported MIME type: {f.content_type}",
            )
    return services.create_document_jobs(db, tenant.tenant_id, dataset_id, len(files))


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_202_ACCEPTED, tags=["datasets"])
async def delete_dataset(dataset_id: str, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    services.soft_delete_dataset(db, tenant.tenant_id, dataset_id)
    return {"status": "accepted", "dataset_id": dataset_id}


@router.delete("/documents/{document_id}", status_code=status.HTTP_202_ACCEPTED, tags=["documents"])
async def delete_document(document_id: str, tenant: TenantContext = Depends(get_tenant)):
    return {"status": "accepted", "document_id": document_id}


@router.get("/jobs/{job_id}", tags=["jobs"], response_model=JobOut)
async def get_job(job_id: str, tenant: TenantContext = Depends(get_tenant)) -> JobOut:
    return JobOut(id=job_id, status="pending", progress=0, error=None)


@router.post("/query", tags=["query"], response_model=QueryResponse)
async def query(request: QueryRequest, tenant: TenantContext = Depends(get_tenant)) -> QueryResponse:
    rewritten = request.query if request.rewrite else None
    return QueryResponse(query=request.query, rewritten=rewritten, results=[])


@router.post("/reindex", status_code=status.HTTP_202_ACCEPTED, tags=["maintenance"])
async def reindex(dataset_id: str, embedder: Optional[str] = None, tenant: TenantContext = Depends(get_tenant)):
    return {"status": "accepted", "dataset_id": dataset_id, "embedder": embedder}
