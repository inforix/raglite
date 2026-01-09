from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import Depends, Header, HTTPException, status

# Simple in-memory API key store placeholder; replace with DB lookup
_API_KEYS: Dict[str, str] = {}


@dataclass
class TenantContext:
    tenant_id: str
    api_key: str


def register_api_key(api_key: str, tenant_id: str):
    """Utility to register an API key in memory (for scaffolding/tests)."""
    _API_KEYS[api_key] = tenant_id


def get_tenant(authorization: Optional[str] = Header(None, convert_underscores=False)) -> TenantContext:
    """
    Placeholder auth that expects Bearer <api_key>; real implementation should validate
    against the metadata store and resolve tenant_id.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        api_key = parts[1]
    else:
        api_key = authorization
    tenant_id = _API_KEYS.get(api_key)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return TenantContext(tenant_id=tenant_id, api_key=api_key)
