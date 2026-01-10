from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from rank_bm25 import BM25Okapi  # type: ignore


class MemoryBM25:
    def __init__(self):
        self.indices: Dict[Tuple[str, str], BM25Okapi] = {}
        self.payloads: Dict[Tuple[str, str], List[dict]] = defaultdict(list)

    def index_documents(self, tenant_id: str, dataset_id: str, items: List[dict]):
        """Add/update documents to the BM25 index."""
        key = (tenant_id, dataset_id)
        tokens = [doc["text"].split() for doc in items]
        self.indices[key] = BM25Okapi(tokens)
        self.payloads[key] = items

    def search(self, tenant_id: str, dataset_ids: List[str], query: str, k: int) -> List[dict]:
        results = []
        for ds in dataset_ids:
            key = (tenant_id, ds)
            if key not in self.indices:
                continue
            bm25 = self.indices[key]
            scores = bm25.get_scores(query.split())
            payloads = self.payloads.get(key, [])
            paired = sorted(zip(payloads, scores), key=lambda x: x[1], reverse=True)[:k]
            for payload, score in paired:
                results.append({"id": payload["id"], "score": float(score), "payload": payload["payload"]})
        results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:k]
        return results

    def delete_dataset(self, tenant_id: str, dataset_id: str):
        key = (tenant_id, dataset_id)
        self.indices.pop(key, None)
        self.payloads.pop(key, None)

    def delete_document(self, tenant_id: str, dataset_id: str, document_id: str):
        key = (tenant_id, dataset_id)
        if key not in self.indices:
            return
        payloads = self.payloads.get(key, [])
        filtered = [p for p in payloads if p["payload"].get("document_id") != document_id]
        if filtered:
            tokens = [doc["text"].split() for doc in filtered]
            self.indices[key] = BM25Okapi(tokens)
            self.payloads[key] = filtered
        else:
            self.delete_dataset(tenant_id, dataset_id)

    def rebuild_from_chunks(self, tenant_id: str, dataset_id: str, chunks: Iterable[dict]):
        items = []
        for ch in chunks:
            items.append(
                {
                    "id": ch["id"],
                    "text": ch["text"],
                    "payload": {
                        "tenant_id": tenant_id,
                        "dataset_id": dataset_id,
                        "document_id": ch.get("document_id"),
                        "text": ch["text"],
                        "meta": ch.get("meta"),
                    },
                }
            )
        if items:
            self.index_documents(tenant_id, dataset_id, items)


bm25_memory = MemoryBM25()
