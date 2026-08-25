# Failure Diagnosis Taxonomy

**What was measured:** A per-example classification of *why* the system failed, rather than just *that* it failed. EvalOS automatically categorizes every execution into a strict taxonomy: Retrieval Failure, Generation Failure, System Failure, or Negative Control Pass/Fail.

**How:** `python cli.py diagnose-run run-c6f32860` on the Dense-only RAG run using `gpt-4o-mini`. EvalOS joins the `Execution`, `MetricResult`, and `EvaluationExample` tables to inspect the exact scores per question.

**Result:**

| Category | Count | Description |
|---|---|---|
| Full Success | 29 | Correct retrieval, grounded answer, no unnecessary abstention. |
| Generation Failure | 6 | Correct retrieval, but LLM abstained unnecessarily (100% faithfulness, 0% abstention). |
| Retrieval Failure | 0 | Incorrect document fetched (Recall = 0.0). |
| System Failure | 0 | API timeout, rate limit, or parsing error. |
| Negative Control - Failed | 1 | LLM hallucinated an answer instead of abstaining. |
| Negative Control - Passed | 0 | LLM correctly abstained. |

**Honest caveats & Real findings:**
- **The "Overly Cautious LLM" Bug:** The 6 Generation Failures all have 100.0% faithfulness. EvalOS diagnosed that the LLM had the correct context but still said "The context does not provide..." and abstained. This is a real failure mode (over-abstention) that a global accuracy score would completely miss.
- **The Hallucination:** The 1 Negative Control failure ("What is quantum entanglement?") shows the LLM still hallucinated an answer from its pretrained weights when given irrelevant context, rather than admitting it lacked the evidence.
- **Retrieval Nuance:** There were 0 Retrieval Failures (Recall = 0.0), meaning the retriever always fetched *something* relevant. However, the global Recall@3 was 88.9%, indicating that for some questions, the retriever only found 1 out of 2 expected sources (partial recall), which was enough for the LLM to answer but not enough to score 100%.
