from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TenantCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TenantOut(BaseModel):
    # Don't use from_attributes since we construct this manually with api_key
    id: str
    name: str
    description: Optional[str] = None
    api_key: Optional[str] = None
    created_at: datetime
