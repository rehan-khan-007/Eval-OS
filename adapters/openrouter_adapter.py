import os
import time
from openai import AsyncOpenAI
from adapters.base import BaseSystemAdapter

class OpenRouterAdapter(BaseSystemAdapter):
    def __init__(self, model: str = "openai/gpt-4o-mini"):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = model
        
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "retrieve",
                    "description": "Search the internal document corpus for relevant information to answer the question.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Perform mathematical calculations or solve arithmetic problems.",
                    "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the live internet for current information, news, or weather.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}
                }
            }
        ]

    async def generate(self, input_data: dict) -> dict:
        question = input_data.get("question")
        messages = [{"role": "user", "content": question}]
        
        start_time = time.time()
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.0
            )
            
            latency = (time.time() - start_time) * 1000
            choice = response.choices[0].message
            
            tool_calls = []
            if choice.tool_calls:
                for tc in choice.tool_calls:
                    tool_calls.append(tc.function.name)
            
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
                "tool_calls": tool_calls,
                "retrieved_evidence": [],
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
