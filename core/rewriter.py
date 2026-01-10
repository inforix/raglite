import time
from typing import Dict, Tuple

from app.config import get_settings

settings = get_settings()
_CACHE: Dict[str, Tuple[float, str]] = {}


def rewrite_query(query: str, tenant_id: str | None = None) -> str:
    """
    Heuristic rewrite placeholder with simple cache.
    """
    key = f"{tenant_id}:{query}"
    now = time.time()
    if key in _CACHE:
        ts, val = _CACHE[key]
        if now - ts < settings.rewrite_cache_ttl_seconds:
            return val
    rewritten = query.strip()
    # placeholder for LLM rewrite; if configured, could call external service
    _CACHE[key] = (now, rewritten)
    return rewritten
