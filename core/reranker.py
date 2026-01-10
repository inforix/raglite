from typing import List

from app.config import get_settings

settings = get_settings()


def rerank(query: str, results: List[dict]) -> List[dict]:
    """
    Optional cross-encoder reranker. Falls back to identity on failure or if disabled.
    Expects results as list of dict with 'text' key.
    """
    model_name = getattr(settings, "reranker_model", None)
    if not model_name:
        return results
    try:
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
    except Exception:
        return results
