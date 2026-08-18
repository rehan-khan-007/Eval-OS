from typing import Any


def recall_at_k(relevant: list[str], retrieved: list[str], k: int = 5) -> float:
    """Recall@K: fraction of relevant docs retrieved in top K."""
    if not relevant:
        return 0.0
    retrieved_set = set(retrieved[:k])
    hits = sum(1 for r in relevant if r in retrieved_set)
    return hits / len(relevant)


def precision_at_k(relevant: list[str], retrieved: list[str], k: int = 5) -> float:
    """Precision@K: fraction of retrieved docs that are relevant."""
    if not retrieved[:k]:
        return 0.0
    retrieved_set = set(retrieved[:k])
    hits = sum(1 for r in relevant if r in retrieved_set)
    return hits / k


def average_precision(relevant: list[str], retrieved: list[str]) -> float:
    """Average precision for a single query."""
    if not relevant:
        return 0.0
    score = 0.0
    hits = 0
    for i, doc in enumerate(retrieved):
        if doc in relevant:
            hits += 1
            score += hits / (i + 1)
    return score / len(relevant)


def mean_reciprocal_rank(relevant: list[str], retrieved: list[str]) -> float:
    """MRR: reciprocal rank of the first relevant document."""
    for i, doc in enumerate(retrieved):
        if doc in relevant:
            return 1.0 / (i + 1)
    return 0.0


def compute_all_retrieval_metrics(relevant: list[str], retrieved: list[str]) -> dict:
    """Compute all standard retrieval metrics."""
    return {
        "recall@1": recall_at_k(relevant, retrieved, 1),
        "recall@5": recall_at_k(relevant, retrieved, 5),
        "precision@5": precision_at_k(relevant, retrieved, 5),
        "mrr": mean_reciprocal_rank(relevant, retrieved),
        "map": average_precision(relevant, retrieved),
    }