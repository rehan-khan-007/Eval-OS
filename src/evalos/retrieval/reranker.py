from sentence_transformers import CrossEncoder
import numpy as np


class Reranker:
    """Cross-encoder reranker for improving retrieval results."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, documents: list[dict], top_k: int | None = None) -> list[dict]:
        pairs = [(query, doc["doc"]) for doc in documents]
        scores = self.model.predict(pairs)
        
        for i, doc in enumerate(documents):
            doc["rerank_score"] = float(scores[i])

        reranked = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
        if top_k:
            reranked = reranked[:top_k]
        return [{**doc, "rank": i + 1} for i, doc in enumerate(reranked)]