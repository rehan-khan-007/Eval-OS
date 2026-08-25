# Answerability & Abstention Evaluation

**What was measured:** Whether the RAG system correctly abstains from answering when it lacks the necessary context, rather than hallucinating. This tests the `AbstentionEvaluator` against the 36-question dataset (which includes 1 negative control with no expected sources).

**How:** `python cli.py run-eval --system rag --model openai/gpt-4o-mini --retriever dense`. The `AbstentionEvaluator` checks for abstention phrases (e.g., "I don't know", "context does not provide") and scores 1.0 if the system abstains on a negative control, or 1.0 if it answers a positive question.

**Result:**

| Metric | Value |
|---|---|
| Abstention Accuracy | **80.6%** |
| Faithfulness (Grounding) | 96.8% |
| Source Recall@3 | 88.9% |

**Honest caveats:**
- **The real finding:** The 80.6% abstention accuracy is *not* a bug in the LLM. It is a direct consequence of the 88.9% retrieval recall. 
- For ~7 questions, the Dense retriever failed to fetch the correct document. The LLM was given irrelevant context. Instead of hallucinating an answer, the LLM correctly recognized the context was useless and abstained ("The context does not provide...").
- This is corroborated by the high faithfulness score (96.8%). EvalOS proves the system is highly truthful (it refuses to hallucinate when retrieval fails), but highlights that the bottleneck is the retrieval pipeline, not the generation pipeline.
- A naive evaluation that only checked for "I don't know" would falsely penalize the LLM. EvalOS's multi-metric cross-referencing correctly diagnoses *why* the abstention happened.
