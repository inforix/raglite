from typing import List, Optional

from app.config import get_settings
from core.bm25_memory import bm25_memory

settings = get_settings()


class OpenSearchBM25:
    def __init__(self):
        from opensearchpy import OpenSearch  # type: ignore

        auth = None
        if settings.opensearch_user and settings.opensearch_password:
            auth = (settings.opensearch_user, settings.opensearch_password)
        self.client = OpenSearch(
            hosts=[settings.opensearch_url],
            http_auth=auth,
            verify_certs=settings.opensearch_verify_certs,
        )

    def _index_name(self, tenant_id: str, dataset_id: str) -> str:
        return f"{settings.opensearch_index_prefix}-{tenant_id}-{dataset_id}".lower().replace(" ", "-")

    def _ensure_index(self, name: str):
        if not self.client.indices.exists(index=name):
            self.client.indices.create(
                index=name,
                body={
                    "settings": {"index": {"similarity": {"default": {"type": "BM25"}}}},
                    "mappings": {
                        "properties": {
                            "text": {"type": "text"},
                            "tenant_id": {"type": "keyword"},
                            "dataset_id": {"type": "keyword"},
                            "document_id": {"type": "keyword"},
                            "meta": {"type": "object"},
                        }
                    },
                },
            )

    def index_documents(self, tenant_id: str, dataset_id: str, items: List[dict]):
        if not items:
            return
        idx = self._index_name(tenant_id, dataset_id)
        self._ensure_index(idx)
        actions = []
        for it in items:
            payload = it.get("payload", {})
            actions.append(
                {
                    "_op_type": "index",
                    "_index": idx,
                    "_id": it.get("id"),
                    "_source": {
                        "text": it.get("text", ""),
                        "tenant_id": tenant_id,
                        "dataset_id": dataset_id,
                        "document_id": payload.get("document_id"),
                        "meta": payload.get("meta"),
                    },
                }
            )
        from opensearchpy.helpers import bulk  # type: ignore

        bulk(self.client, actions)

    def delete_dataset(self, tenant_id: str, dataset_id: str):
        idx = self._index_name(tenant_id, dataset_id)
        if self.client.indices.exists(index=idx):
            self.client.indices.delete(index=idx, ignore_unavailable=True)

    def delete_document(self, tenant_id: str, dataset_id: str, document_id: str):
        idx = self._index_name(tenant_id, dataset_id)
        if not self.client.indices.exists(index=idx):
            return
        self.client.delete_by_query(
            index=idx,
            body={"query": {"term": {"document_id": document_id}}},
        )

    def search(self, tenant_id: str, dataset_ids: List[str], query: str, k: int) -> List[dict]:
        results: List[dict] = []
        for ds in dataset_ids:
            idx = self._index_name(tenant_id, ds)
            if not self.client.indices.exists(index=idx):
                continue
            res = self.client.search(
                index=idx,
                size=k,
                body={"query": {"multi_match": {"query": query, "fields": ["text"]}}},
            )
            for hit in res.get("hits", {}).get("hits", []):
                source = hit.get("_source", {})
                results.append(
                    {
                        "id": hit.get("_id", ""),
                        "score": hit.get("_score", 0.0),
                        "payload": {
                            "tenant_id": source.get("tenant_id", tenant_id),
                            "dataset_id": source.get("dataset_id", ds),
                            "document_id": source.get("document_id", ""),
                            "text": source.get("text", ""),
                            "meta": source.get("meta"),
                        },
                    }
                )
        results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:k]
        return results


def get_bm25_client() -> Optional[OpenSearchBM25]:
    if not settings.enable_bm25:
        return None
    if not settings.opensearch_url:
        return bm25_memory
    try:
        client = OpenSearchBM25()
        # ping to ensure connectivity
        client.client.cluster.health()
        return client
    except Exception:
        return bm25_memory
