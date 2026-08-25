from database import AsyncSessionLocal
from models import DocumentChunk
from sqlalchemy import select, text
from openai import AsyncOpenAI
import os

class RetrievalEngine:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.embedding_model = "openai/text-embedding-3-small"

    async def dense_search(self, query: str, top_k: int = 3) -> list[dict]:
        response = await self.client.embeddings.create(model=self.embedding_model, input=query)
        query_embedding = response.data[0].embedding

        async with AsyncSessionLocal() as db:
            stmt = (
                select(DocumentChunk)
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            )
            result = await db.execute(stmt)
            chunks = result.scalars().all()
            return [{"source": c.source, "text": c.text} for c in chunks]

    async def bm25_search(self, query: str, top_k: int = 3) -> list[dict]:
        async with AsyncSessionLocal() as db:
            # Use plainto_tsquery for safe, simple keyword matching
            stmt = (
                select(DocumentChunk)
                .where(text("search_vector @@ plainto_tsquery('english', :query)"))
                .order_by(text("ts_rank(search_vector, plainto_tsquery('english', :query)) DESC"))
                .limit(top_k)
            )
            result = await db.execute(stmt, {"query": query})
            chunks = result.scalars().all()
            return [{"source": c.source, "text": c.text} for c in chunks]

    async def hybrid_search(self, query: str, top_k: int = 3) -> list[dict]:
        # Fetch top 10 from both methods to fuse
        dense_results = await self.dense_search(query, top_k=10)
        bm25_results = await self.bm25_search(query, top_k=10)

        # Reciprocal Rank Fusion (RRF)
        rrf_k = 60
        scores = {}

        for rank, chunk in enumerate(dense_results):
            key = (chunk["source"], chunk["text"])
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)

        for rank, chunk in enumerate(bm25_results):
            key = (chunk["source"], chunk["text"])
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)

        # Sort by fused score and return top_k
        fused = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [{"source": key[0], "text": key[1]} for key, score in fused]
