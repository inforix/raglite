# AGENTS.md

## Project Overview
- RAGLite is a spec-driven RAG stack: FastAPI API + Celery worker, React admin UI, Qdrant vector store, optional OpenSearch BM25.
- Default runtime is local SQLite, with Docker Compose for full infra (Postgres, Redis, Qdrant, OpenSearch).
- Config uses `RAGLITE_` env var prefix (see `app/config.py`).

## Key Paths
- API: `app/`
- Core logic (embedding, retrieval, reranking, vector store): `core/`
- Workers: `workers/`
- DB models/migrations: `infra/`, `alembic/`
- UI: `ui/`
- Scripts: `scripts/`

## Common Commands
### API (local dev)
```bash
uv sync
cp .env.example .env
./scripts/setup_auth.sh
uv run uvicorn app.main:app --host 0.0.0.0 --port 7615 --reload
```

### Worker
```bash
uv run celery -A workers.worker.celery_app worker --loglevel=info
```

### UI
```bash
cd ui
bun install
bun run build
```

### Docker Compose
```bash
docker compose up -d
docker compose ps
```

## Development Notes
- The `/v1/query` endpoint combines vector search + BM25, then reranks; filtering thresholds are applied before reranking.
- Keep API schemas in sync with UI usage when changing request/response payloads.
- Favor `rg` for searches; avoid destructive git commands unless explicitly requested.

## Tests
- No standard test runner documented; add targeted tests with `pytest` if introducing logic-heavy changes.
