# 2. Evaluation & Analysis Engine

## 2.1 Evaluator Architecture & File Map
*   **Contract:** `BaseEvaluator` (async). Returns `score` (-1.0 to 1.0), `explanation`, `evidence_breakdown`, `status`.
*   **Score Semantics:** `1.0` = success, `0.0` = failure, `-1.0` = indeterminate/evaluator failure. `status` is authoritative.
*   **File Map:**
    *   `LatencyEvaluator`, `SourceRecallEvaluator`, `ToolSelectionEvaluator`, `AbstentionEvaluator` -> `evaluators/deterministic.py`
    *   `LLMJudgeEvaluator` -> `evaluators/llm_judge.py`
    *   `AnswerQualityEvaluator` -> `evaluators/answer_quality.py`
    *   `CitationEvaluator` -> `evaluators/citation.py`
    *   `ReferenceAnswerEvaluator` -> `evaluators/reference_answer.py`

## 2.2 Run Engine
*   **Concurrency:** `RunEngine` uses `asyncio.Semaphore` for bounded concurrency.
*   **Exception Isolation:** `_process_single_example` wraps adapter/evaluator calls in `try/except`. One failure does not crash `asyncio.gather`.
*   **Error Sanitization:** Persisted `Execution.error_message` only stores the exception type, not the raw string.
*   **Run Status (I13):** `EvaluationRun.status` is `complete_with_errors` if any execution fails, otherwise `complete`. These must not be treated as equivalent.

## 2.3 Statistical Methodology
*   **Comparison:** `compare_runs()` calculates paired differences (`candidate - baseline`). Infers `source_recall@K` dynamically.
*   **Confidence Intervals:** 1000 iterations, seed=42. If 95% CI excludes zero, `is_significant` is True.
*   **Limitations:** This is a decision rule, not a universal definition of statistical significance.

## 2.4 Regression Methodology
*   **Metric Direction:** Registry for `higher_is_better` vs `lower_is_better`.
*   **Decision Matrix:** Flagged only if drops by `threshold` AND `is_significant` is True.
*   **Verdicts:** `PASS`, `REGRESSION`, `IMPROVEMENT`, `INCONCLUSIVE`.
*   **Latency:** Threshold-only (500ms), not bootstrap-tested.

## 2.5 Failure Diagnosis
*   **Taxonomy:** `retrieval_failure`, `generation_failure`, `system_failure`, `evaluator_error`, `negative_control_pass`, `negative_control_fail`, `full_success`.
*   **Dynamic Recall:** Dynamically finds the `source_recall@K` metric.
*   **Status Usage:** Uses `MetricResult.status` (not score magic numbers) to identify `evaluator_error`.

## 2.6 HITL Calibration
*   **Data:** `HumanLabel` stores `human_score`, `failure_category`, `comment`.
*   **Metrics:** Pearson Correlation, MAE, Confusion Matrix.
*   **Pilot Result:** N=5 pilot. Judge mean score was 0.132 higher than human scores. Proves the pipeline, not global judge validity.
