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
    """Measures source-level or chunk-level recall@k for RAG systems."""
    def __init__(self, k: int = 3):
        super().__init__(name=f"source_recall@{k}", version="v2") # Version bump for chunk-level logic
        self.k = k

    async def evaluate(self, input_data, system_output, retrieved_evidence):
        metadata = input_data.get("metadata", {})
        expected_sources = set(metadata.get("expected_sources", []))
        gold_chunk_ids = set(metadata.get("gold_chunk_ids", []))
        
        if not expected_sources and not gold_chunk_ids:
            return {"score": 0.0, "explanation": "No expected sources or gold chunks provided.", "evidence_breakdown": {}}

        retrieved_chunks = retrieved_evidence[:self.k]
        retrieved_chunk_ids = set([c.get("chunk_id", "") for c in retrieved_chunks])
        retrieved_sources = set([c.get("source", "") for c in retrieved_chunks])

        # 1. Chunk-Level Recall (Strict)
        if gold_chunk_ids:
            hits = gold_chunk_ids.intersection(retrieved_chunk_ids)
            score = len(hits) / len(gold_chunk_ids)
            return {
                "score": score,
                "explanation": f"Retrieved {len(hits)} out of {len(gold_chunk_ids)} gold chunks.",
                "evidence_breakdown": {
                    "type": "chunk_level",
                    "gold_chunk_ids": list(gold_chunk_ids),
                    "retrieved_chunk_ids": list(retrieved_chunk_ids),
                    "hits": list(hits)
                }
            }
        
        # 2. Document-Level Recall (Fallback)
        hits = expected_sources.intersection(retrieved_sources)
        score = len(hits) / len(expected_sources)
        return {
            "score": score,
            "explanation": f"Retrieved {len(hits)} out of {len(expected_sources)} expected sources.",
            "evidence_breakdown": {
                "type": "document_level",
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

class AbstentionEvaluator(BaseEvaluator):
    """Measures if the system correctly abstained or answered based on expected sources."""
    def __init__(self):
        super().__init__(name="abstention_accuracy", version="v1")
        self.abstention_phrases = [
            "i don't know", "i do not know", "cannot answer", "can't answer",
            "not enough information", "does not provide", "doesn't provide",
            "context does not", "context doesn't", "no information", "not provided"
        ]

    async def evaluate(self, input_data, system_output, retrieved_evidence):
        expected_sources = input_data.get("metadata", {}).get("expected_sources", [])
        answer = (system_output.get("answer", "") or "").lower()
        
        abstained = any(phrase in answer for phrase in self.abstention_phrases)
        should_abstain = len(expected_sources) == 0
        
        if should_abstain:
            score = 1.0 if abstained else 0.0
        else:
            score = 1.0 if not abstained else 0.0
            
        return {
            "score": score,
            "explanation": f"System {'abstained' if abstained else 'answered'}, expected {'abstention' if should_abstain else 'an answer'}.",
            "evidence_breakdown": {"abstained": abstained, "should_abstain": should_abstain}
        }
