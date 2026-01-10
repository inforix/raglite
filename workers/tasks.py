from workers.worker import task
from core import pipeline


@task()
def ingest_document(job_payload: dict):
    pipeline.ingest_document(
        job_id=job_payload["job_id"],
        tenant_id=job_payload["tenant_id"],
        dataset_id=job_payload["dataset_id"],
        document_id=job_payload["document_id"],
        path=job_payload["path"],
        mime_type=job_payload.get("mime_type"),
    )


@task()
def reindex_dataset(*args, **kwargs):
    job_payload = args[0] if args else kwargs
    pipeline.reindex_dataset(
        job_id=job_payload["job_id"],
        tenant_id=job_payload["tenant_id"],
        dataset_id=job_payload["dataset_id"],
        embedder=job_payload.get("embedder"),
    )
