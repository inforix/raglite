import time
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import Header, HTTPException, status

from app.config import get_settings
from infra.db import SessionLocal
from infra import models
from passlib.hash import pbkdf2_sha256

# Simple in-memory API key store placeholder; replaced by DB lookup when present
_API_KEYS: Dict[str, str] = {}
_RATE_LIMIT: Dict[str, list[float]] = {}
settings = get_settings()


@dataclass
class TenantContext:
    tenant_id: str
    api_key: str


def register_api_key(api_key: str, tenant_id: str):
    """Utility to register an API key in memory (for scaffolding/tests)."""
    _API_KEYS[api_key] = tenant_id


def _lookup_api_key_db(api_key: str) -> Optional[str]:
    db = SessionLocal()
    try:
        key_rows = db.query(models.ApiKey).filter(models.ApiKey.active.is_(True)).all()
        for k in key_rows:
            if pbkdf2_sha256.verify(api_key, k.key_hash):
                return k.tenant_id
        return None
    finally:
        db.close()


def _rate_limit(tenant_id: str):
    limit = settings.rate_limit_per_minute
    if not limit or limit <= 0:
        return
    now = time.time()
    window_start = now - 60
    bucket = _RATE_LIMIT.setdefault(tenant_id, [])
    bucket[:] = [t for t in bucket if t >= window_start]
    if len(bucket) >= limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    bucket.append(now)


def get_tenant(authorization: Optional[str] = Header(None, convert_underscores=False)) -> TenantContext:
    """
    Auth expects Bearer <api_key>; validates against DB or in-memory map and applies rate limiting.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        api_key = parts[1]
    else:
        api_key = authorization
    tenant_id = _lookup_api_key_db(api_key) or _API_KEYS.get(api_key)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    _rate_limit(tenant_id)
    return TenantContext(tenant_id=tenant_id, api_key=api_key)
