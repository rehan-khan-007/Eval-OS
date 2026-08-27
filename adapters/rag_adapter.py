import os
import time
from openai import AsyncOpenAI
from adapters.base import BaseSystemAdapter
from retrieval import RetrievalEngine
from cache import generate_cache_key, get_cached, set_cached

class RAGAdapter(BaseSystemAdapter):
    def __init__(self, model: str = "openai/gpt-4o-mini", retriever_type: str = "hybrid", retrieval_config: dict = None, api_key: str = None):
        self.client = AsyncOpenAI(
            api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = model
        self.retriever_type = retriever_type
        self.retrieval_config = retrieval_config or {}
        embedding_model = self.retrieval_config.get("embedding_model", "openai/text-embedding-3-small")
        self.top_k = self.retrieval_config.get("top_k", 3)
        self.retrieval_engine = RetrievalEngine(embedding_model=embedding_model, api_key=api_key)

    async def retrieve(self, query: str) -> list[dict]:
        if self.retriever_type == "dense":
            return await self.retrieval_engine.dense_search(query, top_k=self.top_k)
        elif self.retriever_type == "bm25":
            return await self.retrieval_engine.postgres_fts_search(query, top_k=self.top_k)
        elif self.retriever_type == "hybrid":
            return await self.retrieval_engine.hybrid_search(query, top_k=self.top_k)
        else:
            raise ValueError(f"Unknown retriever type: {self.retriever_type}")

    async def generate(self, input_data: dict) -> dict:
        question = input_data.get("question")
        start_time = time.time()
        try:
            retrieved_evidence = await self.retrieve(question)
            context_text = "\n\n".join([f"Source: {c['source']}\nContent: {c['text']}" for c in retrieved_evidence])
            system_prompt = "Answer the user's question using only the provided context. If the context doesn't contain the answer, say so plainly. You MUST cite the source document for every claim you make using the format [Source: filename.pdf] at the end of the sentence."
            user_prompt = f"Context:\n{context_text}\n\nQuestion: {question}"
            cache_key = generate_cache_key(self.model, system_prompt, user_prompt)
            cached_response = await get_cached(cache_key)
            if cached_response:
                cached_response["retrieved_evidence"] = retrieved_evidence
                cached_response["latency_ms"] = (time.time() - start_time) * 1000
                cached_response["cost"] = 0.0
                cached_response["error"] = None
                return cached_response

            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
            response = await self.client.chat.completions.create(model=self.model, messages=messages, temperature=0.0)
            choice = response.choices[0].message
            tokens_in = response.usage.prompt_tokens if response.usage else 0
            tokens_out = response.usage.completion_tokens if response.usage else 0
            cost = 0.0 
            if tokens_in and tokens_out:
                if "gpt-4o-mini" in self.model: cost = (tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000
                elif "gpt-4o" in self.model: cost = (tokens_in * 2.50 + tokens_out * 10.00) / 1_000_000
                elif "gemini" in self.model and "flash" in self.model: cost = (tokens_in * 0.075 + tokens_out * 0.30) / 1_000_000
                elif "claude" in self.model and "haiku" in self.model: cost = (tokens_in * 0.80 + tokens_out * 4.00) / 1_000_000
                elif "llama-3.1-70b" in self.model: cost = (tokens_in * 0.55 + tokens_out * 0.75) / 1_000_000

            result_data = {"answer": choice.content or "", "tokens_in": tokens_in, "tokens_out": tokens_out}
            await set_cached(cache_key, result_data)
            latency = (time.time() - start_time) * 1000
            return {
                "answer": result_data["answer"], "tool_calls": [], "retrieved_evidence": retrieved_evidence,
                "latency_ms": latency, "cost": cost, "tokens_in": tokens_in, "tokens_out": tokens_out, "error": None
            }
        except Exception as e:
            return {"answer": "", "tool_calls": [], "retrieved_evidence": [], "latency_ms": (time.time() - start_time) * 1000, "cost": 0.0, "tokens_in": 0, "tokens_out": 0, "error": str(e)}
