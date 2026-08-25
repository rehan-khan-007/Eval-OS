import asyncio
import random
from adapters.base import BaseSystemAdapter

class MockSystemAdapter(BaseSystemAdapter):
    """
    Simulates a complex RAG + Agent system returning tool calls and retrieved docs.
    """
    async def generate(self, input_data: dict) -> dict:
        await asyncio.sleep(random.uniform(0.05, 0.2)) # Simulate latency
        
        metadata = input_data.get("metadata", {})
        expected_tool = metadata.get("expected_tool")
        expected_sources = metadata.get("expected_sources", [])
        
        tool_calls = []
        retrieved = []
        
        # Simulate agent tool selection (80% chance of picking the right tool)
        if expected_tool and expected_tool != "none":
            if random.random() < 0.8:
                tool_calls.append(expected_tool)
            else:
                tool_calls.append(random.choice(["retrieve", "calculator", "web_search", "none"]))
                
            # If it called retrieve, simulate source retrieval (80% chance of getting a hit)
            if "retrieve" in tool_calls:
                for src in expected_sources:
                    if random.random() < 0.8:
                        retrieved.append({"source": src, "text": "mock context"})
                retrieved.append({"source": "noise.pdf", "text": "noise"}) # Add noise
        
        answer = f"Simulated answer for: {input_data.get('question')}"
        
        return {
            "answer": answer,
            "tool_calls": tool_calls,
            "retrieved_evidence": retrieved,
            "latency_ms": random.uniform(50, 150),
            "cost": 0.001,
            "tokens_in": 100,
            "tokens_out": 50,
            "error": None
        }
