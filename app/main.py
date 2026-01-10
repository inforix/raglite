import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import get_settings
from app.deps import register_api_key
from infra.db import Base, engine, SessionLocal
from core import opensearch_bm25
from infra import models

settings = get_settings()
logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    openapi_version=settings.openapi_version,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    openapi_url=settings.openapi_url,
)

app.include_router(api_router)

if settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
async def bootstrap_api_key():
    Base.metadata.create_all(bind=engine)
    if settings.enable_bootstrap and settings.bootstrap_api_key and settings.bootstrap_tenant_id:
        register_api_key(settings.bootstrap_api_key, settings.bootstrap_tenant_id)
    if settings.enable_bm25:
        client = opensearch_bm25.get_bm25_client()
        if client:
            try:
                db = SessionLocal()
                pairs = (
                    db.query(
                        models.Chunk.dataset_id.label("dataset_id"),
                        models.Chunk.tenant_id.label("tenant_id"),
                    )
                    .distinct()
                    .all()
                )
                for pair in pairs:
                    chunks = (
                        db.query(models.Chunk)
                        .filter(
                            models.Chunk.dataset_id == pair.dataset_id,
                            models.Chunk.tenant_id == pair.tenant_id,
                        )
                        .all()
                    )
                    items = [
                        {"id": ch.id, "text": ch.text, "document_id": ch.document_id, "meta": ch.meta or {}}
                        for ch in chunks
                    ]
                    client.index_documents(pair.tenant_id, pair.dataset_id, items)
            except Exception:
                pass
            finally:
                try:
                    db.close()
                except Exception:
                    pass


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}
