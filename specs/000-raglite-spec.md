# RAGLite Spec v0.1 (Approved)

- Language/runtime: Python 3.12+.
- Protocol: spec-driven; update specs before implementation; track status (Draft → Approved → Implemented); tests accompany features.
- Scope: API-only, multi-tenant RAG pipeline (ingest/convert/chunk/embed/store; query rewrite; retrieval + optional rerank). No web UI.
- Tenancy: API key → tenant; all DB/vector/object operations scoped by tenant; per-tenant collection/prefixes.
- Components: FastAPI service; worker (Celery + Redis) for ingestion/embedding/indexing; Postgres metadata; object store (local/S3); vector store default Qdrant (Milvus optional, pgvector fallback); Redis for queues/cache.
- Data model: tenant, dataset, document, chunk, job, user/api_key (minimal).
- Embedding config: default model `all-MiniLM-L6-v2`; administrator defines allowed models; tenants can select per-tenant or per-dataset embedder from the allowed list (stored with dataset settings); reindex job required on change.
- Runtime: API listens on port 7615 by default; worker queue uses Redis; configuration via environment with sensible defaults.
- Pipeline: upload/register (supports multiple documents per request) → immediate parse/extract text per file → chunk → embed (batch) → upsert to vector store (tenant + dataset filter) → mark job progress.
- Query: optional rewrite → embed query → vector search (filters: dataset_ids, metadata) → optional hybrid BM25 → optional rerank → return chunks with provenance; log query for metrics.
- API surface (REST, OAS 3.1, root `/` serves docs):
  - POST /v1/tenants (admin)
  - POST /v1/tenants/{id}/regenerate-key
  - POST /v1/datasets, GET /v1/datasets
  - POST /v1/documents (multipart, multiple files allowed; fields: `files[]`, `dataset_id`, optional `source_uri`; returns job ids per file), GET /v1/jobs/{id}
  - POST /v1/query (params: query, dataset_ids?, filters?, k, rewrite?)
  - GET /v1/query/history (query log totals for metrics)
  - GET /v1/query/stats/daily?days=14 (daily query counts)
  - POST /v1/reindex, DELETE /v1/datasets/{id}
  - DELETE /v1/documents/{id} (soft delete + cleanup job)
- Non-goals (v0.1): UI, chat orchestration, eval suite, billing, ACL beyond tenant key.
- Decisions (v0.1): Celery + Redis for workers; chunker default 512 tokens with 128 overlap (fallback char chunker 1500/200); embedder `sentence-transformers/all-MiniLM-L6-v2`; rewriter heuristic stub (LLM-pluggable); reranker optional `cross-encoder/ms-marco-MiniLM-L-2-v2`; OAS 3.1 served at root `/`.
- Constraints: every model includes `tenant_id` and enforces tenant predicates; vector collections are per-tenant; object store paths prefixed by tenant; API returns provenance (dataset_id, document_id, chunk_id, source_uri).

Operational details:
- Upload limits: max 10 files per request; max file size 25 MB; allowed MIME: text/plain, text/markdown, text/html, application/pdf (others rejected).
- Immediate parse: API extracts text synchronously (fast path) and enqueues chunk/embed/index jobs; if parse exceeds 10s per file, offload to worker and return job id.
- Job lifecycle: states {pending, running, succeeded, failed}; progress 0–100; errors stored; job type includes ingest, parse, embed, index, reindex.
- Deletion semantics: DELETE dataset is soft-delete in DB and triggers vector/object cleanup job; purge removes vectors/objects; tenant delete not in v0.1.
- Caching: query rewrite cache (per-tenant key, TTL 10m); rerank cache optional; rate limiting (basic IP/key throttle) optional for v0.1.
- Parsing: structured extraction retains headings/tables/page numbers; optional OCR for images within PDFs; language detection with normalization.
- Chunking: support template-based chunkers (hierarchical, semantic) in addition to default token/char; human override optional (out-of-scope v0.1).
- Connectors: roadmap includes URL fetch, S3/OSS, Confluence/Notion/Google Drive/Discord sync with schedulable incremental jobs; v0.1 only supports direct upload and HTTP URL fetch.
- Dedup/versioning: document hash to skip reprocessing unchanged uploads; maintain document version metadata; idempotent ingestion on retries.
- Retrieval: hybrid (BM25 + vector) with fused rerank as first-class; per-dataset metadata schema for filters; cross-language retrieval relies on model choice.
- Safety/non-goals: agent/code-executor/gVisor not in scope; basic blocklist/PII redaction optional; advanced agentic workflows are out-of-scope v0.1.
