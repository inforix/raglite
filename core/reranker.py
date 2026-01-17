import logging
from typing import List, Optional

import requests

from app.settings_service import get_app_settings_db, get_model_config_by_name
from infra import models
from infra.db import SessionLocal

logger = logging.getLogger(__name__)


def _resolve_rerank_config(model_name: Optional[str]) -> Optional[models.ModelConfig]:
    db = SessionLocal()
    try:
        app_settings = get_app_settings_db(db)
        target = model_name or app_settings.default_rerank_model
        return get_model_config_by_name(db, models.ModelType.rerank, target)
    finally:
        db.close()


def _rerank_cohere_compatible(
    query: str, documents: List[str], cfg: models.ModelConfig, top_n: Optional[int]
) -> List[dict]:
    url = f"{cfg.endpoint.rstrip('/')}/v1/rerank"
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
        headers["api-key"] = cfg.api_key
    payload = {"model": cfg.model, "query": query, "documents": documents}
    if top_n is not None:
        payload["top_n"] = top_n
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results") or []
    ranked = []
    for item in results:
        idx = item.get("index")
        score = item.get("relevance_score", item.get("score"))
        if idx is None:
            continue
        ranked.append({"index": idx, "score": score})
    return ranked


def _rerank_local(query: str, results: List[dict], model_name: str) -> List[dict]:
    from sentence_transformers import CrossEncoder  # type: ignore

    model = CrossEncoder(model_name)
    pairs = [(query, r.get("text", "")) for r in results]
    scores = model.predict(pairs).tolist()
    scored = []
    for r, s in zip(results, scores):
        r2 = dict(r)
        r2["score"] = s
        scored.append(r2)
    return sorted(scored, key=lambda x: x.get("score", 0), reverse=True)


def _rerank_internal(
    query: str,
    results: List[dict],
    model_name: Optional[str],
    top_k: Optional[int],
    min_score: Optional[float],
) -> tuple[List[dict], bool, Optional[str]]:
    """
    Optional reranker. Falls back to identity on failure or if disabled.
    Expects results as list of dict with 'text' key.
    """
    if not results:
        return results, False, None

    cfg = _resolve_rerank_config(model_name)
    if not cfg:
        logger.info("Rerank model is not configured; skipping rerank.")
        return results, False, None

    candidate_count = len(results)
    candidate_limit = min(candidate_count, top_k) if top_k else candidate_count
    candidate_results = results[:candidate_limit]
    remainder = results[candidate_limit:]
    doc_texts = [str(r.get("text", "")) for r in candidate_results]

    try:
        if cfg.endpoint:
            ranked = _rerank_cohere_compatible(query, doc_texts, cfg, candidate_limit)
            reordered = []
            for item in ranked:
                idx = item.get("index")
                if idx is None or idx >= len(candidate_results):
                    continue
                r2 = dict(candidate_results[idx])
                r2["score"] = item.get("score", 0)
                reordered.append(r2)
            reranked = reordered
        else:
            reranked = _rerank_local(query, candidate_results, cfg.model)
    except Exception as exc:
        logger.warning("Reranker failed for model '%s': %s", cfg.name, exc)
        return results, False, None

    if min_score is not None:
        reranked = [hit for hit in reranked if (hit.get("score") or 0) >= min_score]

    if remainder:
        reranked.extend(remainder)
    return reranked, True, cfg.name


def rerank(
    query: str,
    results: List[dict],
    model_name: Optional[str] = None,
    top_k: Optional[int] = None,
    min_score: Optional[float] = None,
) -> List[dict]:
    reranked, _applied, _model = _rerank_internal(
        query=query,
        results=results,
        model_name=model_name,
        top_k=top_k,
        min_score=min_score,
    )
    return reranked


def rerank_with_metadata(
    query: str,
    results: List[dict],
    model_name: Optional[str] = None,
    top_k: Optional[int] = None,
    min_score: Optional[float] = None,
) -> tuple[List[dict], bool, Optional[str]]:
    return _rerank_internal(
        query=query,
        results=results,
        model_name=model_name,
        top_k=top_k,
        min_score=min_score,
    )
