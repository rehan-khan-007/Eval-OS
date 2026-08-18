import numpy as np


class HybridRetriever:
    """Simple weighted hybrid of BM25 and dense retrieval scores."""

    def __init__(self, bm25_retriever, dense_retriever, alpha: float = 0.5):
        self.bm25 = bm25_retriever
        self.dense = dense_retriever
        self.alpha = alpha

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        bm25_results = self.bm25.retrieve(query, top_k * 2)
        dense_results = self.dense.retrieve(query, top_k * 2)

        # Normalize scores
        combined = {}
        for r in bm25_results:
            combined[r["doc"]] = self.alpha * r["score"]
        for r in dense_results:
            combined[r["doc"]] = combined.get(r["doc"], 0) + (1 - self.alpha) * r["score"]

        ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [{"doc": doc, "score": float(score), "rank": i + 1} for i, (doc, score) in enumerate(ranked)]