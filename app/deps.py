import time
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import decode_access_token
from app.config import get_settings
from infra.db import SessionLocal, get_db
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


def _lookup_api_key_db(api_key: str, db: Session | None = None) -> Optional[str]:
    owns_session = False
    if db is None:
        db = SessionLocal()
        owns_session = True
    try:
        key_rows = db.query(models.ApiKey).filter(models.ApiKey.active.is_(True)).all()
        for k in key_rows:
            if pbkdf2_sha256.verify(api_key, k.key_hash):
                return k.tenant_id
        return None
    finally:
        if owns_session:
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


def get_tenant(
    authorization: Optional[str] = Header(None, convert_underscores=False),
    x_tenant_id: Optional[str] = Header(None, convert_underscores=False),
    tenant_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> TenantContext:
    """
    Resolve tenant context from either an API key or a JWT bearer token.
    - API key: Authorization: Bearer <api_key> (or raw value)
    - JWT: Authorization: Bearer <jwt>; requires tenant_id in query/header or falls back to bootstrap tenant.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    requested_tenant = x_tenant_id or tenant_id
    if not requested_tenant and dataset_id:
        ds = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
        if ds:
            requested_tenant = ds.tenant_id
    if not requested_tenant:
        first_tenant = db.query(models.Tenant).order_by(models.Tenant.created_at).first()
        if first_tenant:
            requested_tenant = first_tenant.id
        elif settings.bootstrap_tenant_id:
            requested_tenant = settings.bootstrap_tenant_id

    bearer_value: Optional[str] = None
    api_key: Optional[str] = None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        bearer_value = parts[1]
    else:
        api_key = authorization

    # Try JWT first; if invalid, fall back to API key handling
    if bearer_value:
        try:
            payload = decode_access_token(bearer_value)
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            user = (
                db.query(models.User)
                .filter(models.User.id == user_id, models.User.is_active.is_(True))
                .first()
            )
            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
            tenant_val = requested_tenant or settings.bootstrap_tenant_id
            if not tenant_val:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="tenant_id is required for this request",
                )
            return TenantContext(tenant_id=tenant_val, api_key="")
        except HTTPException:
            api_key = bearer_value

    if api_key:
        tenant_from_key = _lookup_api_key_db(api_key, db=db) or _API_KEYS.get(api_key)
        if not tenant_from_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        _rate_limit(tenant_from_key)
        return TenantContext(tenant_id=tenant_from_key, api_key=api_key)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
