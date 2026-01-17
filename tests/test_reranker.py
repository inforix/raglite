from core import reranker
from infra import models


def test_rerank_reorders_candidates_and_keeps_remainder(monkeypatch):
    cfg = models.ModelConfig(
        id="cfg",
        name="rerank-model",
        type=models.ModelType.rerank.value,
        endpoint="https://example.com",
        api_key=None,
        model="rerank-model",
    )

    def fake_resolve(_):
        return cfg

    def fake_rerank(_query, _docs, _cfg, _top_n):
        return [{"index": 1, "score": 0.9}, {"index": 0, "score": 0.8}]

    monkeypatch.setattr(reranker, "_resolve_rerank_config", fake_resolve)
    monkeypatch.setattr(reranker, "_rerank_cohere_compatible", fake_rerank)

    results = [
        {"text": "first", "score": 0.1},
        {"text": "second", "score": 0.2},
        {"text": "third", "score": 0.3},
    ]

    reranked = reranker.rerank("query", results, top_k=2)

    assert [hit["text"] for hit in reranked] == ["second", "first", "third"]
    assert reranked[0]["score"] == 0.9


def test_rerank_min_score_filters_results(monkeypatch):
    cfg = models.ModelConfig(
        id="cfg",
        name="rerank-model",
        type=models.ModelType.rerank.value,
        endpoint="https://example.com",
        api_key=None,
        model="rerank-model",
    )

    def fake_resolve(_):
        return cfg

    def fake_rerank(_query, _docs, _cfg, _top_n):
        return [{"index": 0, "score": 0.2}, {"index": 1, "score": 0.8}]

    monkeypatch.setattr(reranker, "_resolve_rerank_config", fake_resolve)
    monkeypatch.setattr(reranker, "_rerank_cohere_compatible", fake_rerank)

    results = [
        {"text": "low", "score": 0.1},
        {"text": "high", "score": 0.2},
    ]

    reranked = reranker.rerank("query", results, min_score=0.5)

    assert [hit["text"] for hit in reranked] == ["high"]
