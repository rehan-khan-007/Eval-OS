from abc import ABC, abstractmethod
from typing import Any

class BaseSystemAdapter(ABC):
    @abstractmethod
    async def generate(self, input_data: Any) -> dict:
        """
        Executes the system under test.
        Returns a dict containing:
        {
            "answer": str,
            "tool_calls": list[str],  # e.g., ["retrieve", "calculator"]
            "retrieved_evidence": list[dict], # e.g., [{"source": "doc.pdf", "text": "..."}]
            "latency_ms": float,
            "cost": float,
            "tokens_in": int,
            "tokens_out": int,
            "error": str | None
        }
        """
        pass
