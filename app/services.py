import uuid
from datetime import datetime
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas import DatasetCreate, DatasetOut, DocumentUploadResponse
from infra import models

settings = get_settings()


def create_dataset(db: Session, tenant_id: str, payload: DatasetCreate) -> DatasetOut:
    ds = models.Dataset(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        embedder=payload.embedder,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return DatasetOut.from_orm(ds)


def list_datasets(db: Session, tenant_id: str) -> List[DatasetOut]:
    rows = db.query(models.Dataset).filter(models.Dataset.tenant_id == tenant_id, models.Dataset.deleted_at.is_(None)).all()
    return [DatasetOut.from_orm(r) for r in rows]


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


def create_document_jobs(db: Session, tenant_id: str, dataset_id: str, count: int) -> DocumentUploadResponse:
    job_ids: List[str] = []
    for _ in range(count):
        job = models.Job(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type=models.JobType.ingest.value,
            status=models.JobStatus.pending.value,
        )
        db.add(job)
        job_ids.append(job.id)
    db.commit()
    return DocumentUploadResponse(job_ids=job_ids)
