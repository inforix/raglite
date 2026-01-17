from datetime import datetime
import uuid
from typing import List

from app.config import get_settings
from core import chunker, embedder as embedder_module, parser, vectorstore, storage
from core import opensearch_bm25
from infra import models
from infra.db import SessionLocal

settings = get_settings()
vs = vectorstore.get_vector_store()
bm25_client = opensearch_bm25.get_bm25_client()


def ingest_document(job_id: str | None, tenant_id: str, dataset_id: str, document_id: str, path: str, mime_type: str | None, embedder: str | None = None):
    db = SessionLocal()
    job = None
    try:
        if job_id:
            job = db.query(models.Job).filter(models.Job.id == job_id).first()
        ds = (
            db.query(models.Dataset)
            .filter(models.Dataset.id == dataset_id, models.Dataset.tenant_id == tenant_id)
            .first()
        )
        # Fetch document to get source_uri
        doc = db.query(models.Document).filter(models.Document.id == document_id).first()
        source_uri = doc.source_uri if doc else None
        
        embedder_name = embedder or (ds.embedder if ds else None)
        if job:
            job.status = models.JobStatus.running.value
            job.progress = 10
            job.error = None
            db.commit()
        local_path, cleanup = storage.ensure_local_path(path)
        try:
            text, lang = parser.parse_text(local_path, mime_type)
        finally:
            if cleanup:
                cleanup()
        if job:
            job.progress = 40
            db.commit()
        chunks = chunker.sliding_window(text, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)
        if job:
            job.progress = 60
            db.commit()
        chunk_texts = [c[2] for c in chunks]
        embeddings = embedder_module.embed_texts(chunk_texts, model_name=embedder_name)
        if job:
            job.progress = 80
            db.commit()
        payload = []
        for (start, end, txt), emb in zip(chunks, embeddings):
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{start}"))
            payload.append(
                {
                    "id": chunk_id,
                    "vector": emb,
                    "payload": {
                        "tenant_id": tenant_id,
                        "dataset_id": dataset_id,
                        "document_id": document_id,
                        "text": txt,
                        "source_uri": source_uri,
                        "meta": {"start": start, "end": end},
                    },
                }
            )
            ch = models.Chunk(
                id=chunk_id,
                tenant_id=tenant_id,
                dataset_id=dataset_id,
                document_id=document_id,
                text=txt,
                meta={"start": start, "end": end},
            )
            db.add(ch)
        if settings.enable_bm25 and bm25_client:
            bm25_items = []
            for (start, end, txt) in chunks:
                chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{start}"))
                bm25_items.append(
                    {
                        "id": chunk_id,
                        "text": txt,
                        "payload": {
                            "tenant_id": tenant_id,
                            "dataset_id": dataset_id,
                            "document_id": document_id,
                            "text": txt,
                            "source_uri": source_uri,
                            "meta": {"start": start, "end": end},
                        },
                    }
                )
            try:
                bm25_client.index_documents(tenant_id, dataset_id, bm25_items)
            except Exception:
                pass
        try:
            vs.upsert(tenant_id, dataset_id, payload)
        except Exception:
            pass
        if job:
            job.status = models.JobStatus.succeeded.value
            job.progress = 100
            job.updated_at = datetime.utcnow()
            job.error = None
        # Update document status using the already-fetched doc
        if doc:
            doc.status = "succeeded"
            if lang and not doc.language:
                doc.language = lang
        db.commit()
    except Exception as exc:
        if doc:
            doc.status = "failed"
            db.commit()
        if job:
            job.status = models.JobStatus.failed.value
            job.error = str(exc)
            job.updated_at = datetime.utcnow()
            db.commit()
        raise
    finally:
        db.close()


def reindex_dataset(job_id: str, tenant_id: str, dataset_id: str, embedder: str | None):
    db = SessionLocal()
    job = None
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if job:
            job.status = models.JobStatus.running.value
            job.progress = 5
            db.commit()
        # clear existing vectors and chunks
        try:
            vs.delete_dataset(tenant_id, dataset_id)
        except Exception:
            pass
        try:
            if bm25_client:
                bm25_client.delete_dataset(tenant_id, dataset_id)
        except Exception:
            pass
        db.query(models.Chunk).filter(
            models.Chunk.tenant_id == tenant_id, models.Chunk.dataset_id == dataset_id
        ).delete()
        db.commit()
        docs = (
            db.query(models.Document)
            .filter(
                models.Document.tenant_id == tenant_id,
                models.Document.dataset_id == dataset_id,
                models.Document.deleted_at.is_(None),
            )
            .all()
        )
        total = len(docs) or 1
        for idx, doc in enumerate(docs, start=1):
            ingest_document(job_id, tenant_id, dataset_id, doc.id, doc.path, doc.mime_type, embedder)
            if job:
                job.progress = int(100 * idx / total)
                db.commit()
        if job:
            job.status = models.JobStatus.succeeded.value
            job.progress = 100
            job.updated_at = datetime.utcnow()
            db.commit()
    except Exception as exc:
        if job:
            job.status = models.JobStatus.failed.value
            job.error = str(exc)
            job.updated_at = datetime.utcnow()
            db.commit()
        raise
    finally:
        db.close()
