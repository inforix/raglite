from typing import List, Optional

from pydantic import BaseModel, Field, conint


class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    embedder: Optional[str] = None


class DatasetOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    embedder: Optional[str] = None

    class Config:
        orm_mode = True


class DocumentUploadResponse(BaseModel):
    job_ids: List[str] = Field(default_factory=list)


class JobOut(BaseModel):
    id: str
    status: str
    progress: conint(ge=0, le=100) = 0
    error: Optional[str] = None

    class Config:
        orm_mode = True


class QueryRequest(BaseModel):
    query: str
    dataset_ids: Optional[List[str]] = None
    k: conint(gt=0, le=50) = 5
    rewrite: bool = True


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

