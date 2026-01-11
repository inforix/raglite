from functools import lru_cache
from typing import List, Optional

import requests

from app.config import get_settings
from app.settings_service import get_app_settings_db, get_model_config_by_name
from infra import models
from infra.db import SessionLocal

settings = get_settings()


@lru_cache(maxsize=8)
def _load_model(name: str):
    from sentence_transformers import SentenceTransformer  # type: ignore

    return SentenceTransformer(name)


def _resolve_embedder_config(model_name: Optional[str]) -> Optional[models.ModelConfig]:
    db = SessionLocal()
    try:
        app_settings = get_app_settings_db(db)
        target = model_name or app_settings.default_embedder
        return get_model_config_by_name(db, models.ModelType.embedder, target)
    finally:
        db.close()


def _embed_openai_compatible(texts: List[str], cfg: models.ModelConfig) -> List[List[float]]:
    url = f"{cfg.endpoint.rstrip('/')}/v1/embeddings"
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    resp = requests.post(
        url,
        json={"input": texts, "model": cfg.model},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json().get("data", [])
    if len(data) != len(texts):
        raise ValueError("Embedding response size mismatch")
    return [item.get("embedding", []) for item in data]


def embed_texts(texts: List[str], model_name: Optional[str] = None) -> List[List[float]]:
    """
    Embed texts using either an OpenAI-compatible endpoint (if configured) or a local sentence-transformers model.
    """
    cfg = _resolve_embedder_config(model_name)
    target_model = cfg.model if cfg else (model_name or settings.default_embedder)
    try:
        if cfg and cfg.endpoint:
            return _embed_openai_compatible(texts, cfg)
        model = _load_model(target_model)
        return model.encode(texts, normalize_embeddings=True).tolist()
    except Exception:
        dim = 384
        return [[0.0] * dim for _ in texts]
