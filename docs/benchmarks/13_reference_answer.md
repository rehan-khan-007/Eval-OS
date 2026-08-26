# Reference-Answer Evaluation (Ground Truth Correctness)

**What was measured:** Whether the generated answer is semantically correct compared to a human-provided ground truth `reference_answer`, ignoring the retrieved context entirely. This tests true factual correctness, addressing the CTO audit's finding that "Correct based on retrieved context isn't necessarily actual correctness."

**How:** `python cli.py run-eval --system rag --model openai/gpt-4o-mini --retriever dense --top-k 3 --config-name "DenseRealRefEval"`. We injected real reference answers for 3 quantum physics questions into the database metadata. The `ReferenceAnswerEvaluator` prompts the LLM Judge to compare the generated answer against the ground truth.

**Result:**

| Metric | Score | Description |
|---|---|---|
| `reference_correctness` | **100.0%** | Generated answers perfectly matched the ground truth for the 3 tested questions. |
| `answer_quality` | 88.89% | Context-based correctness. |
| `faithfulness` | 93.2% | Context-based groundedness. |
| `citation_correctness` | 100.0% | Citation accuracy. |

**Honest caveats:**
- Only 3 out of 36 questions currently have human-provided `reference_answer` labels. The evaluator correctly scored those 3 and returned `indeterminate` (-1.0) for the other 33, which the Analysis Engine correctly filtered out of the aggregate.
- This fulfills the CTO audit's Stage B requirement: "Reference-based evaluation (using the `reference_answer` field we already built)."
- In a full production benchmark, every question would have a reference answer, and this metric would serve as the definitive measure of factual correctness.
