from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings
from pydantic import Field, HttpUrl, model_validator


class Settings(BaseSettings):
    app_name: str = "RAGLite"
    api_version: str = "0.1.0"
    openapi_version: str = "3.1.0"
    docs_url: str = "/"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    port: int = 7615
    environment: str = "dev"  # dev|prod
    log_level: str = "INFO"

    bootstrap_api_key: str = "dev-secret-key"
    bootstrap_tenant_id: str = "dev-tenant"
    enable_bootstrap: bool = True

    # Embedding configuration
    default_embedder: str = "sentence-transformers/all-MiniLM-L6-v2"
    allowed_embedders: List[str] = Field(
        default_factory=lambda: ["sentence-transformers/all-MiniLM-L6-v2"]
    )
    default_chat_model: str = "gpt-4o-mini"
    allowed_chat_models: List[str] = Field(default_factory=lambda: ["gpt-4o-mini", "gpt-3.5-turbo"])
    default_rerank_model: Optional[str] = None
    allowed_rerank_models: List[str] = Field(default_factory=list)

    # Ingestion limits
    max_files_per_upload: int = 10
    max_file_size_mb: int = 25
    allowed_mime_types: List[str] = Field(
        default_factory=lambda: [
            "text/plain",
            "text/markdown",
            "text/html",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
    )
    parse_timeout_seconds: int = 10
    chunk_size: int = 512
    chunk_overlap: int = 128
    rewrite_cache_ttl_seconds: int = 600
    query_min_score: float = 0.5
    rate_limit_per_minute: int = 60
    allowed_origins: List[str] = Field(default_factory=list)
    enable_bm25: bool = True
    opensearch_url: str | None = "http://localhost:9200"
    opensearch_user: str | None = None
    opensearch_password: str | None = None
    opensearch_index_prefix: str = "raglite"
    opensearch_verify_certs: bool = True

    # External services
    redis_url: str = "redis://localhost:6379/0"
    postgres_dsn: str = "postgresql://raglite:raglite@localhost:5432/raglite"
    qdrant_url: HttpUrl | str = "http://localhost:6333"
    object_store_root: str = "./data"

    # Security
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours

    class Config:
        env_prefix = "RAGLITE_"
        env_file = ".env"
        case_sensitive = False

    @model_validator(mode="after")
    def check_security_settings(self):
        if self.environment.lower() != "dev":
            if self.jwt_secret_key == "your-secret-key-change-in-production":
                raise ValueError("Insecure configuration: jwt_secret_key must be changed in production!")
            if self.enable_bootstrap and self.bootstrap_api_key == "dev-secret-key":
                raise ValueError("Insecure configuration: bootstrap_api_key must be changed in production if bootstrap is enabled!")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
