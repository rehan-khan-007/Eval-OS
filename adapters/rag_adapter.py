import os
import time
from openai import AsyncOpenAI
from adapters.base import BaseSystemAdapter
from database import AsyncSessionLocal
from models import DocumentChunk
from sqlalchemy import select

class RAGAdapter(BaseSystemAdapter):
    def __init__(self, model: str = "openai/gpt-4o-mini"):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = model
        self.embedding_model = "openai/text-embedding-3-small"

    async def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        # 1. Embed the query
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=query
        )
        query_embedding = response.data[0].embedding

        # 2. Query Postgres for top_k chunks using cosine distance
        async with AsyncSessionLocal() as db:
            stmt = (
                select(DocumentChunk)
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            )
            result = await db.execute(stmt)
            chunks = result.scalars().all()
            
            return [{"source": c.source, "text": c.text} for c in chunks]

    async def generate(self, input_data: dict) -> dict:
        question = input_data.get("question")
        start_time = time.time()
        
        try:
            # 1. Retrieve context
            retrieved_evidence = await self.retrieve(question, top_k=3)
            context_text = "\n\n".join([f"Source: {c['source']}\nContent: {c['text']}" for c in retrieved_evidence])
            
            # 2. Generate answer
            system_prompt = "Answer the user's question using only the provided context. If the context doesn't contain the answer, say so plainly."
            user_prompt = f"Context:\n{context_text}\n\nQuestion: {question}"
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0
            )
            
            latency = (time.time() - start_time) * 1000
            choice = response.choices[0].message
            
            tokens_in = response.usage.prompt_tokens if response.usage else 0
            tokens_out = response.usage.completion_tokens if response.usage else 0
            
            cost = 0.0 
            if tokens_in and tokens_out:
                if "gpt-4o-mini" in self.model:
                    cost = (tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000
                elif "gpt-4o" in self.model:
                    cost = (tokens_in * 2.50 + tokens_out * 10.00) / 1_000_000

            return {
                "answer": choice.content or "",
                "tool_calls": [],
                "retrieved_evidence": retrieved_evidence,
                "latency_ms": latency,
                "cost": cost,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "error": None
            }
        except Exception as e:
            return {
                "answer": "",
                "tool_calls": [],
                "retrieved_evidence": [],
                "latency_ms": (time.time() - start_time) * 1000,
                "cost": 0.0,
                "tokens_in": 0,
                "tokens_out": 0,
                "error": str(e)
            }
