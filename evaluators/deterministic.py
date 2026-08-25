from evaluators.base import BaseEvaluator

class ToolSelectionEvaluator(BaseEvaluator):
    """Measures if the agent selected the correct tool (or none)."""
    def __init__(self):
        super().__init__(name="tool_selection_accuracy", version="v1")

    async def evaluate(self, input_data, system_output, retrieved_evidence):
        expected_tool = input_data.get("metadata", {}).get("expected_tool")
        actual_tool = "none"

        if system_output.get("tool_calls"):
            tool = system_output["tool_calls"][0]
            actual_tool = tool.get("name", tool) if isinstance(tool, dict) else tool

        score = 1.0 if expected_tool == actual_tool else 0.0
        return {
            "score": score,
            "explanation": f"Expected {expected_tool}, got {actual_tool}",
            "evidence_breakdown": {"expected": expected_tool, "actual": actual_tool}
        }

class SourceRecallEvaluator(BaseEvaluator):
    """Measures source-level recall@k for RAG systems (ignores chunk indices)."""
    def __init__(self, k: int = 3):
        super().__init__(name=f"source_recall@{k}", version="v1")
        self.k = k

    async def evaluate(self, input_data, system_output, retrieved_evidence):
        expected_sources = set(input_data.get("metadata", {}).get("expected_sources", []))
        if not expected_sources:
            return {"score": 0.0, "explanation": "No expected sources provided (negative control)."}

        retrieved_sources = set([e.get("source", "") for e in retrieved_evidence[:self.k]])
        hits = expected_sources.intersection(retrieved_sources)
        score = len(hits) / len(expected_sources)

        return {
            "score": score,
            "explanation": f"Retrieved {len(hits)} out of {len(expected_sources)} expected sources.",
            "evidence_breakdown": {
                "expected": list(expected_sources),
                "retrieved_top_k": list(retrieved_sources),
                "hits": list(hits)
            }
        }

class LatencyEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__(name="latency_ms", version="v1")

    async def evaluate(self, input_data, system_output, retrieved_evidence):
        latency = system_output.get("latency_ms", 0.0)
        return {"score": latency, "explanation": "Latency in milliseconds."}
