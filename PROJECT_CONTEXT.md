# EvalOS — Project Context & Engineering Handoff (v1.0.0)

## 1. Executive Summary
EvalOS is an advanced research prototype and early evaluation infrastructure for AI/RAG systems. The repository contains a functioning, cloud-deployed evaluation pipeline spanning dataset execution, retrieval evaluation, LLM-based evaluation, HITL calibration, statistical comparison, regression detection, caching, and CLI/API tooling. 

EvalOS is officially frozen at v1.0.0. It is a modular monolith designed to act as the evaluation layer for future AI systems (e.g., AgentOS, WoE). It is not a production SaaS, nor does it pretend to be. It is a scientifically honest, rigorous engineering portfolio piece.

## 2. What EvalOS Does NOT Guarantee
*   LLM-judge scores are not objective ground truth.
*   High retrieval recall does not imply answer correctness.
*   High faithfulness does not imply completeness.
*   Statistical significance does not imply practical significance.
*   Non-significance does not prove equivalence.
*   Five human labels do not establish population-level judge calibration.
*   Estimated cost is not provider billing.
*   Generation latency is not total evaluation latency.
*   `run_fingerprint` guarantees identical configuration provenance, not identical execution outputs due to external API stochasticity.

## 3. How to Resolve Conflicts
When sources disagree, the following hierarchy is authoritative:
1.  Executed implementation
2.  Passing tests + test assertions
3.  Database/schema definitions
4.  Current benchmark artifacts
5.  Git diffs/history
6.  Engineering logs
7.  README/documentation

## 4. Intended Architecture
AI System -> EvalOS -> (Quality, Cost, Latency) -> Diagnosis -> Regression Detection -> HITL Calibration -> CI/CD-Ready Gate.

## 5. Current Reality vs Intended Architecture
*   **Implemented & Verified:** Core async engine, Neon Postgres (`pgvector` + `tsvector`), Upstash Redis caching, modular Typer CLI, FastAPI backend, Streamlit dashboard, Interactive BYOK Playground, Alembic migrations, Experiment abstraction, Bounded Concurrency (`asyncio.Semaphore`), Statistical Regression (Bootstrap CIs, `INCONCLUSIVE` states), HITL Calibration, Citation Correctness, Reference Answers.
*   **Not Implemented (Future v2):** AgentOS/WoE trace integration, OpenTelemetry observability, User authentication/billing, Multi-tenant SaaS features.

## 6. Repository Structure
Eval-OS/
├── adapters/             # System interfaces (OpenRouter, RAG, Mock)
├── analysis/             # Aggregation, Slicing, A/B, Regression, Calibration logic
├── api/                  # FastAPI backend (REST API) & Pydantic schemas
├── cache.py              # Upstash Redis caching layer (version-aware)
├── cli/                  # Modular Typer commands (run, inspect, compare, label)
├── data/                 # Datasets and PDF corpus
├── evaluators/           # Deterministic (Recall, Abstention) & LLM-Judge (Faithfulness, Citation, Quality)
├── alembic/             # Database migration scripts
├── retrieval.py          # Dense, PostgreSQL FTS, and Hybrid (RRF) search engines
├── run_engine.py         # Concurrent execution loop with exception isolation
├── dashboard.py          # Streamlit frontend UI
├── Dockerfile            # Backend deployment config
├── Dockerfile.dashboard  # Frontend deployment config
└── docs/benchmarks/      # Real, documented benchmark results

## 7. Evaluation Lifecycle (Dependency Graph)
Dataset -> SystemConfig -> Run -> Execution -> Adapter -> Raw Artifacts -> Evaluators -> MetricResult -> Analysis (Aggregation, Diagnosis, Statistics, Calibration, Regression).

## 8. Dataset & Ground Truth Architecture
*   **Current Dataset:** `dv-ds-retrieval_qa-v1` (36 questions, 4 domains).
*   **Identity:** Example IDs are generated using `hashlib.sha256(question.encode()).hexdigest()[:16]` for deterministic reproducibility.
*   **Ground Truth Hierarchy:**
    *   **Expected source (N=36):** Document-level annotations.
    *   **Reference answer (N=3):** Human-authored ground truth for quantum physics questions.
    *   **Gold chunk (N=3):** Derived semantic labeling (chunk most similar to reference answer).
    *   **Human score (N=5):** HITL calibration labels (`human_score`, `failure_category`).
*   **Playground Candidates:** Saved to a separate `dv-playground-candidates-v1` dataset to prevent benchmark contamination.

## 9. Database Architecture
*   **Tables:** `datasets`, `dataset_versions`, `evaluation_examples`, `system_configs`, `experiments`, `evaluation_runs`, `executions`, `metric_results`, `document_chunks`, `human_labels`.
*   **Provenance:** `EvaluationRun` stores `code_sha`, `dependency_spec`, and a canonical SHA256 `run_fingerprint`.
*   **Status Semantics:** `MetricResult` stores explicit `status` (`success`, `indeterminate`, `evaluator_error`). `EvaluationRun` status can be `complete` or `complete_with_errors`.
*   **Migrations:** Managed via Alembic. Clean database deployments preserve `pgvector` and `tsvector` structures.

## 10. System Adapter Architecture
`BaseSystemAdapter` -> `MockSystemAdapter`, `OpenRouterAdapter`, `RAGAdapter`.
The adapter returns a dict with `answer`, `retrieved_evidence`, `latency_ms`, `cost`, `tokens_in`, `tokens_out`, `error`. Evaluation code must not modify the system-under-test.

## 11. Retrieval / RAG Architecture
`RetrievalEngine` supports `dense` (pgvector), `postgres_fts` (tsvector), and `hybrid` (RRF).
*   **RRF:** Pure function `fuse_rrf()` in `retrieval.py`. Uses `chunk_id` as unique key.
*   **Config-Driven:** `top_k` and `embedding_model` are passed from `SystemConfig` to the adapter.

## 12. Evaluation Architecture
`BaseEvaluator` (async). Returns `score` (-1.0 to 1.0), `explanation`, `evidence_breakdown`, `status`.
*   **Deterministic:** `LatencyEvaluator`, `SourceRecallEvaluator` (v2: chunk-level), `ToolSelectionEvaluator`, `AbstentionEvaluator`.
*   **LLM-as-Judge:** `LLMJudgeEvaluator` (faithfulness), `AnswerQualityEvaluator` (correctness/completeness), `CitationEvaluator` (citation support), `ReferenceAnswerEvaluator` (ground truth match).
*   **Semantics:** `-1.0` means indeterminate/evaluator failure. `0.0` means failure. `1.0` means success.

## 13. Evaluator Result Contract
*   `score = 1.0` -> valid success
*   `score = 0.0` -> valid failure
*   `score = -1.0` -> indeterminate/evaluator failure
*   `status` -> authoritative indicator of evaluation execution state.
*   **Contract for Indeterminate results (`-1.0`):** Must not be silently treated as failures, must not enter quality averages, must be countable, must be visible in run diagnostics.

## 14. Run Engine
`RunEngine` processes examples concurrently using `asyncio.Semaphore` (bounded concurrency). It isolates exceptions per example (`_process_single_example` try/except block), preventing one API failure from crashing the entire `asyncio.gather` loop. DB sessions are closed immediately after fetching data. Run status is set to `complete_with_errors` if any execution fails. Persisted error messages are sanitized to exception types only (e.g., "Exception") to prevent leaking provider auth details.

## 15. Analysis Engine
Split into `analysis/` directory:
*   `aggregation.py`: Global averages and slice-based metrics.
*   `statistics.py`: Paired bootstrap CIs (seed=42, 1000 iters). Infers `source_recall@K` dynamically if no metric specified.
*   `diagnosis.py`: Rule-based failure taxonomy. Uses `MetricResult.status` (not score magic numbers) and dynamic recall K.
*   `regression.py`: Threshold + Statistical Significance (CI excludes zero). Supports `higher_is_better` and `lower_is_better`. Verdicts: `PASS`, `REGRESSION`, `IMPROVEMENT`, `INCONCLUSIVE`.
*   `calibration.py`: Pearson, MAE, Confusion Matrix for HITL.

## 16. Statistical Methodology
`compare_runs()` calculates paired differences (`candidate - baseline`) and bootstraps the mean difference. If the 95% CI excludes zero, it is significant. **Note:** This is the current implementation's decision rule, not a universal definition of statistical significance. The framework currently does not establish equivalence when the CI contains zero.

## 17. Regression Methodology
`check_regression()` flags a metric if it drops by `threshold` (e.g., 2%) AND `is_significant` is True. Latency is threshold-only (500ms). **Future work:** Consider explicit effect-size reporting rather than only threshold/significance flags.

## 18. HITL Calibration
`HumanLabel` stores `human_score`, `failure_category`, `comment`. In the current N=5 pilot sample, the judge's mean score was 0.132 higher than human scores, indicating apparent leniency in this pilot sample. **N=5 is sufficient to exercise the calibration pipeline, not to validate judge reliability globally.**

## 19. Caching & Cost Accounting
`cache.py` uses Redis. Keys are version-aware. `pickle` is used for serialization. **Security:** Redis cache is trusted infrastructure. Cost is `estimated_cost`: hardcoded pricing in `rag_adapter.py` based on token counts.

## 20. Experiment Provenance Matrix
| Parameter         | Persisted? | Where?       | Required for reproduction? |
| ----------------- | ---------- | ------------ | -------------------------- |
| Dataset version   | Yes        | EvalRun      | YES                        |
| Code SHA          | Yes        | EvalRun      | YES                        |
| Model             | Yes        | SystemConfig | YES                        |
| Prompt version    | Yes        | SystemConfig | YES                        |
| Judge             | Yes        | MetricResult | YES                        |
| Retrieval config  | Yes        | SystemConfig | YES                        |
| Evaluator version | Yes        | MetricResult | YES                        |
| Dependency spec   | Yes        | EvalRun      | YES                        |
| Run Fingerprint   | Yes        | EvalRun      | YES (Config Provenance)    |

## 21. Engineering Lessons / Bug History
1.  **Neon Idle Timeouts:** Holding DB sessions open during API calls causes `InterfaceError`. Fix: Short-lived sessions.
2.  **MissingGreenlet:** Lazy loading outside async session. Fix: `selectinload`.
3.  **JSONB Mutation:** SQLAlchemy doesn't detect in-place JSONB dict mutations. Fix: Raw SQL `jsonb_set`.
4.  **BM25 Naming:** `ts_rank` is not BM25. Fix: Renamed to `postgres_fts`.
5.  **RRF Identity:** Using `(source, text)` causes chunk collapse. Fix: Use `chunk_id`.
6.  **Evaluator Errors:** API timeouts returning `0.0` dragged down averages. Fix: Return `-1.0` and filter in aggregation.
7.  **Typer Async:** `async def` commands aren't awaited by Typer. Fix: Wrap in `def run(): asyncio.run()`.
8.  **Alembic Autogenerate Destruction:** Alembic tried to drop `search_vector` because it wasn't in `models.py`. Fix: Manually edited migration file to preserve FTS.
9.  **RunEngine Gather Crash:** One exception in `asyncio.gather` killed the run. Fix: Try/except in `_process_single_example`.

## 22. Architectural Invariants
*   **I1 — Evaluator failure ≠ system failure:** `-1.0` must remain distinct from `0.0`.
*   **I2 — Chunk identity is immutable:** RRF must use `chunk_id`, not `(source, text)`.
*   **I3 — DB sessions must not span external API calls:** Protects against Neon timeouts.
*   **I4 — Cache identity must include evaluator version:** Prevents stale results.
*   **I5 — Dataset identity must be deterministic:** Example IDs must not rely on Python `hash()`.
*   **I6 — Benchmark numbers must always carry sample size:** Never report `96.8%` without `N=36, dataset=v1`.
*   **I7 — Every evaluator has explicit metric semantics.**
*   **I8 — Every evaluator version change invalidates incompatible cached results.**
*   **I9 — Every benchmark result must identify dataset version + system configuration.**
*   **I10 — Evaluation code must not modify the system-under-test.**

## 23. Things That Must Not Be Changed Casually
*   Do not change the `-1.0` evaluator-error semantics without first auditing all aggregation, statistics, regression, caching, persistence, and downstream consumers and adding migration/regression tests.
*   Do not reintroduce long-lived DB sessions across external API calls.
*   `chunk_id` as RRF identity key.
*   Cache key versioning logic.

## 24. Security & Testing
`.env` for secrets. `pickle` in Redis is a risk if Redis is compromised. Playground uses rate limiting (5/min), 500-char limits, and sanitized Request ID error logging.
26 tests currently passing across 7 modules (`test_api.py`, `test_cache.py`, `test_evaluators.py`, `test_regression.py`, `test_rrf.py`, `test_run_engine.py`, `test_statistics.py`).

## 25. EvalOS ↔ AgentOS Boundary
EvalOS evaluates AgentOS traces. Not implemented yet. EvalOS must not become an AgentOS execution dependency. It should receive structured traces, not run AgentOS internals.

## 26. Flagship Assessment
**Advanced research prototype / early evaluation infrastructure.**
*   Architecture: 9.4/10
*   Engineering: 9.2/10
*   Evaluation methodology: 9.0/10
*   Statistical infrastructure: 8.9/10
*   Testing: 8.2/10
*   Flagship potential: 9.6/10

## 27. Instructions for the Next Engineer / AI Model
*   Read this document first.
*   Do not interpret "implemented" as "validated".
*   Do not change the `-1.0` evaluator logic without an impact audit.
*   Do not hold DB sessions open.
*   Do not rename `postgres_fts` to `bm25`.
*   Keep cache keys version-aware.
*   Add tests for new features.
*   **EvalOS v1 is frozen. Do not add features. Focus on correctness or v2 integration.**

## 28. Repository Reference Map
| Subsystem | File | Symbol |
|---|---|---|
| Database | `database.py` | `engine`, `AsyncSessionLocal` |
| Models | `models.py` | `EvaluationRun`, `Execution`, `MetricResult` |
| Retrieval | `retrieval.py` | `RetrievalEngine`, `fuse_rrf` |
| Run Engine | `run_engine.py` | `RunEngine` |
| Analysis | `analysis/` | `analyze_run`, `compare_runs`, `check_regression` |
| Caching | `cache.py` | `get_cached`, `set_cached` |
| CLI | `cli/main.py` | `app` |
| API | `api/main.py` | `app` |
| Dashboard | `dashboard.py` | `streamlit` |
