from functools import lru_cache
from typing import List, Optional

from pydantic import BaseSettings, Field, HttpUrl


class Settings(BaseSettings):
    app_name: str = "RAGLite"
    api_version: str = "0.1.0"
    openapi_version: str = "3.1.0"
    docs_url: str = "/"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    port: int = 7615

    bootstrap_api_key: str = "dev-secret-key"
    bootstrap_tenant_id: str = "dev-tenant"

    # Embedding configuration
    default_embedder: str = "sentence-transformers/all-MiniLM-L6-v2"
    allowed_embedders: List[str] = Field(
        default_factory=lambda: ["sentence-transformers/all-MiniLM-L6-v2"]
    )

    # Ingestion limits
    max_files_per_upload: int = 10
    max_file_size_mb: int = 25
    allowed_mime_types: List[str] = Field(
        default_factory=lambda: [
            "text/plain",
            "text/markdown",
            "text/html",
            "application/pdf",
        ]
    )
    parse_timeout_seconds: int = 10

    # External services
    redis_url: str = "redis://localhost:6379/0"
    postgres_dsn: str = "postgresql+psycopg://raglite:raglite@localhost:5432/raglite"
    qdrant_url: HttpUrl | str = "http://localhost:6333"
    object_store_root: str = "./data"

    class Config:
        env_prefix = "RAGLITE_"
        env_file = ".env"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
