import logging
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api import api_router
from app.config import get_settings
from app.deps import register_api_key
from infra.db import Base, engine, SessionLocal
from core import opensearch_bm25, storage
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

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.api_version,
        openapi_version=settings.openapi_version,
        description="RAGLite API - Multi-tenant RAG pipeline with ingestion, embedding, and retrieval",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "description": "Enter your API key obtained from POST /v1/tenants"
        }
    }
    # Apply security to all protected endpoints
    for path, path_item in openapi_schema["paths"].items():
        if path in ["/health", "/health/storage"]:
            continue
        if path == "/v1/tenants" and "post" in path_item:
            continue  # Creating tenant doesn't require auth
        for method in path_item:
            if method in ["get", "post", "put", "delete", "patch"]:
                path_item[method]["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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


@app.get("/health/storage", tags=["meta"])
async def storage_health():
    if not storage.is_s3_backend():
        return {"backend": "local", "ok": True}
    try:
        storage.check_s3_connection()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"S3 storage unavailable: {exc}",
        )
    return {
        "backend": "s3",
        "ok": True,
        "bucket": settings.s3_bucket,
        "endpoint": settings.s3_endpoint,
    }


# Serve UI static files
ui_dist_path = (Path(__file__).parent.parent / "ui" / "dist").resolve()
if ui_dist_path.exists():
    app.mount("/ui/assets", StaticFiles(directory=str(ui_dist_path / "assets")), name="ui-assets")
    
    @app.get("/ui/{full_path:path}")
    async def serve_ui(full_path: str):
        """Serve the React SPA - all routes return index.html for client-side routing"""
        if full_path:
            requested_path = (ui_dist_path / full_path).resolve()
            if ui_dist_path in requested_path.parents and requested_path.is_file():
                return FileResponse(str(requested_path))
        index_path = ui_dist_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"error": "UI not built. Run 'cd ui && bun run build'"}
