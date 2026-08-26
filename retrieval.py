from database import AsyncSessionLocal
from models import DocumentChunk
from sqlalchemy import select, text
from openai import AsyncOpenAI
from cache import generate_cache_key, get_cached, set_cached
import os

class RetrievalEngine:
    def __init__(self, embedding_model: str = "openai/text-embedding-3-small"):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.embedding_model = embedding_model

    async def get_embedding(self, query: str) -> list[float]:
        cache_key = generate_cache_key("embedding", self.embedding_model, query)
        cached_embedding = await get_cached(cache_key)
        if cached_embedding:
            return cached_embedding

        response = await self.client.embeddings.create(model=self.embedding_model, input=query)
        embedding = response.data[0].embedding
        await set_cached(cache_key, embedding)
        return embedding

    async def dense_search(self, query: str, top_k: int = 3) -> list[dict]:
        query_embedding = await self.get_embedding(query)

        async with AsyncSessionLocal() as db:
            stmt = (
                select(DocumentChunk)
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            )
            result = await db.execute(stmt)
            chunks = result.scalars().all()
            # P0 Fix: Return chunk_id to use as a unique RRF key
            return [{"chunk_id": c.id, "source": c.source, "text": c.text} for c in chunks]

    async def postgres_fts_search(self, query: str, top_k: int = 3) -> list[dict]:
        async with AsyncSessionLocal() as db:
            # P0 Fix: Renamed from bm25 to postgres_fts. ts_rank is not BM25.
            stmt = (
                select(DocumentChunk)
                .where(text("search_vector @@ plainto_tsquery('english', :query)"))
                .order_by(text("ts_rank(search_vector, plainto_tsquery('english', :query)) DESC"))
                .limit(top_k)
            )
            result = await db.execute(stmt, {"query": query})
            chunks = result.scalars().all()
            return [{"chunk_id": c.id, "source": c.source, "text": c.text} for c in chunks]

    async def hybrid_search(self, query: str, top_k: int = 3) -> list[dict]:
        dense_results = await self.dense_search(query, top_k=10)
        fts_results = await self.postgres_fts_search(query, top_k=10)

        rrf_k = 60
        scores = {}

        # P0 Fix: Use chunk_id as the unique key for RRF, not (source, text)
        for rank, chunk in enumerate(dense_results):
            key = chunk["chunk_id"]
            scores[key] = {"score": scores.get(key, {}).get("score", 0.0) + 1.0 / (rrf_k + rank + 1), "data": chunk}

        for rank, chunk in enumerate(fts_results):
            key = chunk["chunk_id"]
            if key in scores:
                scores[key]["score"] += 1.0 / (rrf_k + rank + 1)
            else:
                scores[key] = {"score": 1.0 / (rrf_k + rank + 1), "data": chunk}

        fused = sorted(scores.items(), key=lambda item: item[1]["score"], reverse=True)[:top_k]
        return [val["data"] for key, val in fused]
