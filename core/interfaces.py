from typing import Any, Iterable, List, Protocol


class Embedder(Protocol):
    def embed(self, texts: List[str]) -> List[List[float]]:
        ...


class VectorStore(Protocol):
    def upsert(self, tenant_id: str, dataset_id: str, vectors: Iterable[dict]) -> None:
        ...

    def query(
        self,
        tenant_id: str,
        dataset_ids: List[str],
        vector: List[float],
        k: int,
        filters: dict | None = None,
    ) -> List[dict]:
        ...

    def delete_dataset(self, tenant_id: str, dataset_id: str) -> None:
        ...


class QueryRewriter(Protocol):
    def rewrite(self, tenant_id: str, query: str, context: Any | None = None) -> str:
        ...

