# Answer Quality Evaluation (Correctness & Completeness)

**What was measured:** The distinction between an answer being *grounded* (Faithfulness) and an answer being *actually correct and complete* (Answer Quality). This tests the CTO audit finding that "Groundedness != Correctness".

**How:** `python cli.py run-eval --system rag --model openai/gpt-4o-mini --retriever dense --top-k 3 --config-name "DenseQualityEval"`. We added an `AnswerQualityEvaluator` that prompts the LLM Judge to score `correctness` (is it factually right based on context?) and `completeness` (does it address all parts of the question?).

**Result:**

| Metric | Score | Description |
|---|---|---|
| `faithfulness` | **96.2%** | Claims are supported by context (No hallucinations). |
| `answer_quality` | **82.6%** | Answer is correct and complete. |
| `source_recall@3` | 88.9% | Retrieval performance. |
| `abstention_accuracy` | 80.6% | Abstention behavior. |

**Honest caveats & Real findings:**
- **The "Grounded but Incomplete" Trap:** This is exactly why EvalOS was built. The 96.2% faithfulness score tells you the system is not hallucinating. But the 82.6% answer quality score reveals the system is frequently providing incomplete answers or missing parts of the question.
- A naive evaluation pipeline that only checks for grounding would falsely report the system is performing at 96%. EvalOS exposes the real 13.6-point gap between "not hallucinating" and "actually answering the question well."
- The cost for this run was only $0.0026. Because we had the Redis cache in place, EvalOS pulled the cached generations for free and only paid for the new `AnswerQualityEvaluator` API calls. This proves the caching architecture is highly efficient for iterative development.
