from fastapi import FastAPI

from app.api import api_router
from app.config import get_settings
from app.deps import register_api_key

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    openapi_version=settings.openapi_version,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    openapi_url=settings.openapi_url,
)

app.include_router(api_router)


@app.on_event("startup")
async def bootstrap_api_key():
    register_api_key(settings.bootstrap_api_key, settings.bootstrap_tenant_id)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}
