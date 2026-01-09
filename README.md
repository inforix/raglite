# RAGLite

Spec-driven, API-only RAG pipeline inspired by RAGFlow. Supports multi-tenant isolation, ingestion + embedding, vector storage, query rewriting, and retrieval without a web UI.

## Goals
- Simple deploy: one API service + worker + vector DB.
- Multi-tenant isolation by user/tenant namespace.
- Clear pipeline stages: ingest → chunk → embed → store → query-rewrite → retrieve → rerank.
- Replaceable components (embedders, retrievers, vector stores).

## Architecture
- API service (FastAPI) for auth, dataset/document CRUD, query, and job status.
- Worker (Celery/RQ) for asynchronous ingestion, embedding, and indexing jobs.
- Metadata store: Postgres (or SQLite for dev) for users, datasets, documents, chunks, jobs.
- Object store: local filesystem path per tenant (or S3-compatible) for raw docs.
- Vector store: **Qdrant** by default (per-tenant collections); Milvus optional for very high scale; pgvector fallback for lightweight deploys.
- Optional cache: Redis for rate limiting and short-lived query rewrite cache.
- Observability: structured logs + OpenTelemetry traces.
- Root path (`/`) serves the OpenAPI UI (OAS 3.1) so browser access lands on API docs.

## Data Model (simplified)
- User/Tenant: `id`, `name`, `api_key`, settings.
- Dataset: `id`, `tenant_id`, `name`, `description`.
- Document: `id`, `dataset_id`, `tenant_id`, `source_uri`, `mime`, `status`.
- Chunk: `id`, `document_id`, `tenant_id`, `text`, `meta` (page, title), `embedding`.
- Job: `id`, `tenant_id`, `type` (ingest/embed/index), `status`, `progress`, `error`.

## Ingestion Pipeline
1) Upload/register documents (supports multiple files per request; store raw files, enqueue job; skip reprocessing identical content by hash).
2) Immediately parse/convert each file to text (structured parse keeps headings/tables/page numbers; optional OCR for images in PDFs).
3) Chunk text (configurable chunk/token size + overlap; keep hierarchy metadata; roadmap: template-based chunkers).
4) Embed chunks (pluggable embedder; default `sentence-transformers` small model).
5) Index into vector store under `tenant_id` namespace + dataset filter.
6) Mark job status; expose progress via API.

## Query Flow
1) Auth via API key → resolve `tenant_id`.
2) Query rewrite: optional LLM or heuristic (spell/expand acronyms, add must-have filters). Cache by `(tenant_id, query)`.
3) Retrieve: vector search in tenant namespace + optional filters (dataset, metadata).
4) Hybrid retrieval: BM25 + vector with fused scores (optional).
5) Rerank: lightweight cross-encoder (or client-provided reranker); return top-k chunks with provenance; cross-language depends on model choice.

## API Sketch (REST)
- `POST /v1/tenants` (admin) create tenant + API key.
- `POST /v1/datasets` create dataset (requires API key).
- `GET /v1/datasets` list.
- `POST /v1/documents` multipart upload (multiple files: `files[]`, `dataset_id`, optional `source_uri`); returns job ids.
- `GET /v1/jobs/{id}` job status/progress.
- `POST /v1/query` body: `query`, `dataset_ids?`, `k`, `filters?`, `rewrite=true|false`; returns rewritten query, retrieved chunks, scores, metadata.
- `POST /v1/reindex` re-embed a dataset with new model.
- `DELETE /v1/datasets/{id}`, `DELETE /v1/documents/{id}` soft delete and trigger cleanup.

Authentication: bearer API key; middleware injects `tenant_id`. All DB/vector queries filter by `tenant_id`.

## Component Interfaces (Python examples)
```python
class Embedder:
    def embed(self, texts: list[str]) -> list[list[float]]: ...

class VectorStore:
    def upsert(self, tenant_id: str, dataset_id: str, vectors: list[dict]): ...
    def query(self, tenant_id: str, dataset_ids: list[str], vector: list[float], k: int, filters=None): ...
    def delete_dataset(self, tenant_id: str, dataset_id: str): ...

class QueryRewriter:
    def rewrite(self, tenant_id: str, query: str, context=None) -> str: ...
```

## Directory Layout
- `app/`: FastAPI service (routes, auth, DTOs).
- `workers/`: background jobs for conversion, chunking, embedding, indexing.
- `core/`: interfaces (embedder, vector store, rewriter), implementations, chunker, loaders.
- `infra/`: db models (SQLAlchemy), migrations, settings, logging.
- `tests/`: unit + integration (vector store, rewriter, pipelines).

## Multi-Tenant Isolation
- API keys map to `tenant_id` stored in DB.
- Vector store uses per-tenant collection name or tenant filter; no cross-tenant queries.
- Object store uses path prefix `tenants/{tenant_id}/...`.
- Jobs and DB queries always include `tenant_id` predicate; enforced in ORM base model + service layer.
- Configurable per-tenant limits (datasets, docs, max chunks).

## Runtime Defaults
- API listens on port `7615` (override via env).

## Embedding Configuration
- Administrator sets an allowed embedder list (model id + dimension); default `sentence-transformers/all-MiniLM-L6-v2`.
- Tenants select embedder at tenant or dataset level from the allowed list; reindex required when changing.

## Minimal Tech Choices
- Python 3.12+, FastAPI, SQLAlchemy, Pydantic, Celery + Redis, Postgres, Qdrant (or pgvector).
- Embedding defaults: `sentence-transformers/all-MiniLM-L6-v2` (local download) with batching.
- Rerank (optional): `cross-encoder/ms-marco-MiniLM-L-2-v2`.
- Docker Compose for local: api + worker + redis + qdrant + postgres.
- Limits: max 10 files per upload, 25 MB each; allowed MIME: txt/md/html/pdf; parse timeout 10s before offloading.

## Roadmap / Non-goals
- Roadmap: connectors (HTTP URL fetch, S3/OSS, Confluence/Notion/Google Drive/Discord) with schedulable sync; template-based chunkers.
- Non-goals v0.1: UI, agent/code executor, billing, advanced ACL; basic blocklist/PII redaction optional.

## Example Query Flow (pseudocode)
```python
@router.post("/v1/query")
def query(payload: QueryRequest, tenant=Depends(auth)):
    rewritten = rewriter.rewrite(tenant.id, payload.query) if payload.rewrite else payload.query
    qvec = embedder.embed([rewritten])[0]
    hits = vector_store.query(tenant.id, payload.dataset_ids, qvec, k=payload.k, filters=payload.filters)
    reranked = reranker.rerank(rewritten, hits) if reranker else hits
    return {"query": payload.query, "rewritten": rewritten, "results": reranked}
```

## Next Steps
- Scaffold FastAPI service + worker, wire settings.
- Implement storage adapters: local FS loader, Qdrant/pgvector vector store, Postgres migrations.
- Add chunkers (by tokens and by characters) and MIME-specific loaders.
- Write integration tests for ingestion pipeline and query path across tenants.

## Specs
- See `specs/000-raglite-spec.md` (v0.1 Approved); update specs before implementation changes.
