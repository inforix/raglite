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
    embedder: Optional[str] = None


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
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
