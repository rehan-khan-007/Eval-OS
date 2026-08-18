from rank_bm25 import BM25Okapi
import numpy as np


class BM25Retriever:
    """BM25 sparse retrieval."""

    def __init__(self):
        self.bm25 = None
        self.documents: list[str] = []
        self.tokenized: list[list[str]] = []

    def index(self, documents: list[str]):
        self.documents = documents
        self.tokenized = [doc.lower().split() for doc in documents]
        self.bm25 = BM25Okapi(self.tokenized)

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [
            {"doc": self.documents[i], "score": float(scores[i]), "rank": rank + 1}
            for rank, i in enumerate(top_indices)
        ]