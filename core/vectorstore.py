from typing import Iterable, List, Optional

from app.config import get_settings

settings = get_settings()


class NoOpVectorStore:
    """
    Placeholder vector store; replace with Qdrant adapter.
    """

    def upsert(self, tenant_id: str, dataset_id: str, vectors: Iterable[dict]) -> None:
        return None

    def query(
        self,
        tenant_id: str,
        dataset_ids: List[str],
        vector: List[float],
        k: int,
        filters: Optional[dict] = None,
    ) -> List[dict]:
        return []

    def delete_dataset(self, tenant_id: str, dataset_id: str) -> None:
        return None

    def delete_document(self, tenant_id: str, dataset_id: str, document_id: str) -> None:
        return None


class QdrantVectorStore:
    def __init__(self, url: str):
        from qdrant_client import QdrantClient  # type: ignore
        from qdrant_client.http import models as rest  # type: ignore

        self._client = QdrantClient(url=url, prefer_grpc=False)
        self._rest = rest

    def _collection_name(self, tenant_id: str, dataset_id: str) -> str:
        return f"{tenant_id}__{dataset_id}"

    def _ensure_collection(self, collection: str, vector_dim: int):
        rest = self._rest
        try:
            self._client.get_collection(collection)
        except Exception:
            self._client.create_collection(
                collection_name=collection,
                vectors_config=rest.VectorParams(size=vector_dim, distance=rest.Distance.COSINE),
            )

    def upsert(self, tenant_id: str, dataset_id: str, vectors: Iterable[dict]) -> None:
        items = list(vectors)
        if not items:
            return
        collection = self._collection_name(tenant_id, dataset_id)
        first_vec = items[0].get("vector") or []
        self._ensure_collection(collection, len(first_vec))
        self._client.upsert(
            collection_name=collection,
            points=items,
        )

    def query(
        self,
        tenant_id: str,
        dataset_ids: List[str],
        vector: List[float],
        k: int,
        filters: Optional[dict] = None,
    ) -> List[dict]:
        rest = self._rest
        results: List[dict] = []
        target_datasets = dataset_ids or ["default"]
        for ds in target_datasets:
            collection = self._collection_name(tenant_id, ds)
            try:
                search_result = self._client.search(
                    collection_name=collection,
                    query_vector=vector,
                    limit=k,
                )
                for r in search_result:
                    results.append({"id": r.id, "score": r.score, "payload": r.payload})
            except Exception:
                continue
        results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:k]
        return results

    def delete_dataset(self, tenant_id: str, dataset_id: str) -> None:
        collection = self._collection_name(tenant_id, dataset_id)
        try:
            self._client.delete_collection(collection_name=collection)
        except Exception:
            return None

    def delete_document(self, tenant_id: str, dataset_id: str, document_id: str) -> None:
        collection = self._collection_name(tenant_id, dataset_id)
        rest = self._rest
        try:
            self._client.delete(
                collection_name=collection,
                points_selector=rest.Filter(
                    must=[rest.FieldCondition(key="document_id", match=rest.MatchValue(value=document_id))]
                ),
            )
        except Exception:
            return None


def get_vector_store():
    if settings.qdrant_url:
        try:
            return QdrantVectorStore(str(settings.qdrant_url))
        except Exception:
            return NoOpVectorStore()
    return NoOpVectorStore()
