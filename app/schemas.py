from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, conint, ConfigDict


class TenantCreate(BaseModel):
    name: str


class TenantOut(BaseModel):
    id: str
    name: str
    api_key: str
    created_at: datetime


class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    embedder: str


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    embedder: Optional[str] = None
    confirm_embedder_change: bool = False


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    embedder: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    job_ids: List[str] = Field(default_factory=list)


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    progress: conint(ge=0, le=100) = 0
    error: Optional[str] = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    dataset_id: str
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    language: Optional[str] = None
    status: str
    source_uri: Optional[str] = None
    created_at: str


class DocumentUpdate(BaseModel):
    filename: Optional[str] = None
    source_uri: Optional[str] = None


class DocumentListResponse(BaseModel):
    items: List[DocumentOut] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int


class QueryRequest(BaseModel):
    query: str
    dataset_ids: Optional[List[str]] = None
    k: conint(gt=0, le=50) = 5
    rewrite: bool = True
    filters: Optional[dict] = None


class QueryHit(BaseModel):
    chunk_id: str
    document_id: str
    dataset_id: str
    score: float
    text: str
    source_uri: Optional[str] = None
    meta: Optional[dict] = None


class QueryResponse(BaseModel):
    query: str
    rewritten: Optional[str] = None
    results: List[QueryHit] = Field(default_factory=list)


class ModelConfigBase(BaseModel):
    name: str
    endpoint: str
    api_key: Optional[str] = None
    model: str


class ModelConfigOut(ModelConfigBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str


class ModelConfigCreate(ModelConfigBase):
    pass


class ModelConfigUpdate(BaseModel):
    name: Optional[str] = None
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class SettingsOut(BaseModel):
    default_embedder: str
    default_chat_model: str
    embedders: List[ModelConfigOut]
    chat_models: List[ModelConfigOut]


class SettingsUpdate(BaseModel):
    default_embedder: Optional[str] = None
    default_chat_model: Optional[str] = None
