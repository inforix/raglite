from typing import Any

from workers import tasks as worker_tasks
from core import pipeline


def enqueue_ingest(job_payload: dict[str, Any]) -> None:
    """
    Placeholder enqueue. In production, this would delay Celery tasks.
    """
    try:
        worker_tasks.ingest_document.delay(job_payload)
    except Exception:
        # Celery not configured in dev; run inline for immediate parse path
        pipeline.ingest_document(
            job_id=job_payload["job_id"],
            tenant_id=job_payload["tenant_id"],
            dataset_id=job_payload["dataset_id"],
            document_id=job_payload["document_id"],
            path=job_payload["path"],
            mime_type=job_payload.get("mime_type"),
            embedder=job_payload.get("embedder"),
        )


def enqueue_reindex(job_payload: dict[str, Any]) -> None:
    try:
        worker_tasks.reindex_dataset.delay(job_payload)
    except Exception:
        pipeline.reindex_dataset(
            job_id=job_payload["job_id"],
            tenant_id=job_payload["tenant_id"],
            dataset_id=job_payload["dataset_id"],
            embedder=job_payload.get("embedder"),
        )
