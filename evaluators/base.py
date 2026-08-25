from abc import ABC, abstractmethod
from typing import Any

class BaseEvaluator(ABC):
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version

    @abstractmethod
    def evaluate(self, input_data: Any, system_output: dict, retrieved_evidence: list) -> dict:
        """
        Returns a dict containing:
        {
            "score": float,
            "explanation": str,
            "evidence_breakdown": dict | None
        }
        """
        pass
