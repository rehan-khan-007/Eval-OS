# 2. Evaluation & Analysis Engine

## 2.1 Evaluator Architecture
*   **Contract:** `BaseEvaluator` (async). Returns `score` (-1.0 to 1.0), `explanation`, `evidence_breakdown`, `status`.
*   **Score Semantics:**
    *   `1.0` = valid success.
    *   `0.0` = valid failure.
    *   `-1.0` = indeterminate/evaluator failure.
*   **Status:** The `status` field is the authoritative indicator of execution state (`success`, `indeterminate`, `evaluator_error`).
*   **Indeterminate Contract:** `-1.0` scores must not be silently treated as failures, must not enter quality averages, must be countable, and must be visible in run diagnostics.

## 2.2 Evaluator Suite
*   **Deterministic:** `LatencyEvaluator`, `SourceRecallEvaluator` (v2: chunk-level), `ToolSelectionEvaluator`, `AbstentionEvaluator`.
*   **LLM-as-Judge:** `LLMJudgeEvaluator` (faithfulness), `AnswerQualityEvaluator` (correctness/completeness), `CitationEvaluator` (citation support), `ReferenceAnswerEvaluator` (ground truth match).

## 2.3 Run Engine
*   **Concurrency:** `RunEngine` processes examples concurrently using `asyncio.Semaphore` (bounded concurrency).
*   **Exception Isolation:** `_process_single_example` wraps adapter/evaluator calls in a `try/except`. If an exception occurs, it returns a mock `sys_output` with the error, preventing `asyncio.gather` from crashing the entire run.
*   **Error Sanitization:** Persisted `Execution.error_message` only stores the exception type (e.g., `Exception`), not the raw string, to prevent leaking provider auth details.
*   **Run Status:** `EvaluationRun.status` is set to `complete_with_errors` if any execution fails, otherwise `complete`.

## 2.4 Statistical Methodology
*   **Comparison:** `compare_runs()` calculates paired differences (`candidate - baseline`) and bootstraps the mean difference.
*   **Inference:** If no `metric_name` is provided, the engine dynamically infers the `source_recall@K` metric from the database.
*   **Confidence Intervals:** Uses 1000 iterations, seed=42. If the 95% CI excludes zero, `is_significant` is True.
*   **Limitations:** This is a decision rule, not a universal definition of statistical significance. The framework does not establish equivalence when the CI contains zero.

## 2.5 Regression Methodology
*   **Metric Direction:** Registry for `higher_is_better` vs `lower_is_better` metrics.
*   **Decision Matrix:** A metric is flagged only if it drops by `threshold` AND `is_significant` is True.
*   **Verdicts:** `PASS`, `REGRESSION`, `IMPROVEMENT`, `INCONCLUSIVE`.
*   **Latency:** Latency regression is threshold-only (500ms), not bootstrap-tested.

## 2.6 Failure Diagnosis
*   **Taxonomy:** `retrieval_failure`, `generation_failure`, `system_failure`, `evaluator_error`, `negative_control_pass`, `negative_control_fail`, `full_success`.
*   **Dynamic Recall:** Diagnosis dynamically finds the `source_recall@K` metric; it does not hardcode `@3`.
*   **Status Usage:** Diagnosis uses `MetricResult.status` (not score magic numbers) to identify `evaluator_error`.

## 2.7 HITL Calibration
*   **Data:** `HumanLabel` stores `human_score`, `failure_category`, `comment`.
*   **Metrics:** `calibration.py` calculates Pearson Correlation, Mean Absolute Error (MAE), and a binary Confusion Matrix.
*   **Pilot Result:** In the N=5 pilot, the judge's mean score was 0.132 higher than human scores (apparent leniency). N=5 is sufficient to exercise the pipeline, not to validate global reliability.
