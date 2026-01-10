from functools import lru_cache
from typing import List, Optional

from app.config import get_settings

settings = get_settings()


@lru_cache(maxsize=8)
def _load_model(name: str):
    from sentence_transformers import SentenceTransformer  # type: ignore

    return SentenceTransformer(name)


def embed_texts(texts: List[str], model_name: Optional[str] = None) -> List[List[float]]:
    """
    Minimal embedder stub. Attempts to use sentence-transformers if installed; otherwise returns zero vectors.
    """
    target_model = model_name or settings.default_embedder
    try:
        model = _load_model(target_model)
        return model.encode(texts, normalize_embeddings=True).tolist()
    except Exception:
        dim = 384
        return [[0.0] * dim for _ in texts]
