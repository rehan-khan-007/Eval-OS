# EvalOS — Project Context & Engineering Handoff

## 1. Executive Summary
EvalOS is an asynchronous, CLI-first evaluation infrastructure framework for AI systems (specifically RAG). It uses Neon Postgres (`pgvector` + `tsvector`) and Upstash Redis. It has undergone a rigorous CTO-level audit and "Quality Pass" to ensure methodological rigor (statistical regression, HITL calibration, citation correctness). It is currently a **research-grade prototype** (~8/10), transitioning into infrastructure.

## 2. What EvalOS Is
EvalOS does not generate answers. It takes a system (like a RAG pipeline), runs it against a dataset, applies deterministic and LLM-based evaluators, and produces statistically valid metrics, failure taxonomies, and regression gates.

## 3. Intended Architecture
AI System -> EvalOS -> (Quality, Cost, Latency) -> Diagnosis -> Regression Detection -> HITL Calibration -> CI/CD Gate. 

## 4. Current Reality vs Intended Architecture
*   **Implemented:** Core async engine, Postgres schema, adapters, evaluators, statistical analysis, HITL, caching, CLI.
*   **Missing:** True bounded concurrency (`asyncio.Semaphore`), `Experiment` abstraction, Alembic migrations, FastAPI/Dashboard.

## 5. Repository Structure
Eval-OS/
├── adapters/             # System interfaces (OpenRouter, RAG, Mock)
├── analysis/              # Aggregation, Slicing, A/B, Regression, Calibration
├── cache.py               # Upstash Redis caching (version-aware)
├── cli/                   # Modular Typer commands (run, inspect, compare, label)
├── data/                  # Datasets and PDF corpus
├── evaluators/            # Deterministic (Recall, Abstention) & LLM-Judge
├── migrations/           # Ad-hoc SQL migration scripts (no Alembic yet)
├── retrieval.py          # Dense, PostgreSQL FTS, and Hybrid (RRF) search
├── run_engine.py         # Sequential execution loop
├── tests/                 # Pytest suite (6 tests)
└── docs/benchmarks/      # Real, documented benchmark results

## 6. Core Architecture
*   **Database:** Neon Postgres via `asyncpg` + `SQLAlchemy 2.0 async`.
*   **LLM Routing:** OpenRouter via `AsyncOpenAI`.
*   **Caching:** Upstash Redis (prefixed `evalos:`).
*   **Principle:** Short-lived database sessions to avoid Neon idle timeouts.

## 7. Evaluation Lifecycle
Dataset -> SystemConfig -> RunEngine -> Execution -> MetricResult.

## 8. Dataset Architecture
*   **Current Dataset:** `dv-ds-retrieval_qa-v1` (36 questions, 4 domains).
*   **Metadata (JSONB):** `expected_sources` (document-level), `expected_tool` (agent tasks), `reference_answer` (3 samples), `gold_chunk_ids` (3 samples).

## 9. Ground Truth Architecture
1.  **Document-level Recall:** 36 questions have `expected_sources`.
2.  **Reference Answers:** 3 questions have human-written `reference_answer`.
3.  **Gold Chunks:** 3 questions have `gold_chunk_ids` (generated via semantic similarity to reference answer).
4.  **Human Labels:** 5 questions have rich HITL labels (`human_score`, `failure_category`).

## 10. Database Architecture
*   **Tables:** `datasets`, `dataset_versions`, `evaluation_examples`, `system_configs`, `evaluation_runs`, `executions`, `metric_results`, `document_chunks`, `human_labels`.
*   **JSONB:** Heavily used for metadata, retrieval config, and evidence breakdowns.
*   **Migrations:** Currently ad-hoc Python scripts in `migrations/`. No Alembic.

## 11. System Adapter Architecture
`BaseSystemAdapter` -> `MockSystemAdapter`, `OpenRouterAdapter`, `RAGAdapter`.
The adapter returns a dict with `answer`, `retrieved_evidence`, `latency_ms`, `cost`, `tokens_in`, `tokens_out`, `error`.

## 12. Retrieval / RAG Architecture
`RetrievalEngine` supports `dense` (pgvector), `postgres_fts` (tsvector), and `hybrid` (RRF).
*   **RRF:** Pure function `fuse_rrf()` in `retrieval.py`. Uses `chunk_id` as unique key.
*   **Config-Driven:** `top_k` and `embedding_model` are passed from `SystemConfig` to the adapter.

## 13. Evaluation Architecture
`BaseEvaluator` (async). Returns `score` (-1.0 to 1.0), `explanation`, `evidence_breakdown`, `status`.
*   **Deterministic:** `LatencyEvaluator`, `SourceRecallEvaluator` (v2: chunk-level), `ToolSelectionEvaluator`, `AbstentionEvaluator`.
*   **LLM-as-Judge:** `LLMJudgeEvaluator` (faithfulness), `AnswerQualityEvaluator` (correctness/completeness), `CitationEvaluator` (citation support), `ReferenceAnswerEvaluator` (ground truth match).
*   **Semantics:** `-1.0` means indeterminate/evaluator error. `0.0` means failure. `1.0` means success.

## 14. Run Engine
`RunEngine` processes examples **sequentially**. It creates an `Execution`, calls the adapter, runs the evaluators, and saves `MetricResult`s. DB sessions are closed immediately after fetching data.

## 15. Analysis Engine
Split into `analysis/` directory:
*   `aggregation.py`: Global averages and slice-based metrics.
*   `statistics.py`: Paired bootstrap CIs (seed=42, 1000 iters).
*   `diagnosis.py`: Rule-based failure taxonomy (retrieval, generation, system, evaluator error).
*   `regression.py`: Threshold + Statistical Significance (CI excludes zero).
*   `calibration.py`: Pearson, MAE, Confusion Matrix for HITL.

## 16. Statistical Analysis
`compare_runs()` calculates paired differences and bootstraps the mean difference. If the 95% CI excludes zero, it is significant.

## 17. Regression Detection
`check_regression()` flags a metric if it drops by `threshold` (e.g., 2%) AND `is_significant` is True. Latency is threshold-only (500ms).

## 18. HITL Calibration
`HumanLabel` stores `human_score`, `failure_category`, `comment`. `calculate_calibration()` compares judge scores to human scores. Current N=5 pilot showed Judge is 13.2% too lenient (MAE=0.132).

## 19. Caching
`cache.py` uses Redis. Keys are version-aware (`evaluator_name`, `evaluator_version`, `model`, `input`). `pickle` is used for serialization.

## 20. Cost Accounting
Hardcoded pricing in `rag_adapter.py` based on token counts. Not actual billing.

## 21. Latency Measurement
Wall-clock time for the `generate()` call. Includes retrieval + API call.

## 22. Reproducibility
`SystemConfig` stores `retrieval_config` (top_k, embedding_model). Evaluator versions are stored in `MetricResult`. Cache keys are version-aware.

## 23. Benchmark Inventory
14 reports in `docs/benchmarks/`. All use real API calls.

## 24. Benchmark Validity Audit
*   **HITL:** N=5. Too small for definitive conclusions, but proves methodology.
*   **Reference Answer:** N=3. Proves evaluator works, but not full benchmark.
*   **Dense vs Hybrid:** 4.2% recall difference was NOT statistically significant.

## 25. Ground Truth Limitations
Document-level recall is the primary ground truth (36 samples). Chunk-level and reference-answer are only 3 samples.

## 26. Evaluator Bias / Circularity
Same model (`gpt-4o-mini`) used for generation and judging. Same embedding model used for gold chunk creation and retrieval.

## 27. Dataset / Benchmark Leakage
The 36-question dataset was used to tune the system. No held-out test set.

## 28. Engineering Lessons / Bug History
1.  **Neon Idle Timeouts:** Holding DB sessions open during API calls causes `InterfaceError`. Fix: Short-lived sessions.
2.  **MissingGreenlet:** Lazy loading outside async session. Fix: `selectinload`.
3.  **JSONB Mutation:** SQLAlchemy doesn't detect in-place JSONB dict mutations. Fix: Raw SQL `jsonb_set`.
4.  **BM25 Naming:** `ts_rank` is not BM25. Fix: Renamed to `postgres_fts`.
5.  **RRF Identity:** Using `(source, text)` causes chunk collapse. Fix: Use `chunk_id`.
6.  **Evaluator Errors:** API timeouts returning `0.0` dragged down averages. Fix: Return `-1.0` and filter in aggregation.
7.  **Typer Async:** `async def` commands aren't awaited by Typer. Fix: Wrap in `def run(): asyncio.run()`.

## 29. Important Architectural Decisions
*   **Postgres over SQLite:** Needed for `pgvector` and real joins.
*   **Async:** Prevents I/O bottlenecks (though currently sequential).
*   **-1.0 Sentinel:** Distinguishes evaluator failure from system failure.
*   **Modular Analysis:** Prevented god-module anti-pattern.

## 30. Things That Must Not Be Changed Casually
*   `-1.0` score semantics in evaluators.
*   `chunk_id` as RRF identity key.
*   Short-lived DB session pattern.
*   Cache key versioning logic.

## 31. Security
`.env` for secrets. `pickle` in Redis is a risk if Redis is compromised.

## 32. Testing
6 tests (`test_rrf.py`, `test_cache.py`). Very low coverage. Needs tests for evaluators, DB, CLI.

## 33. Performance / Scalability
**Sequential execution.** Will be slow for 1000s of examples. Needs `asyncio.Semaphore`.

## 34. Repository / DevOps Quality
No CI/CD, no Docker, no Alembic. PDFs are tracked in Git (should be LFS/manifests).

## 35. Documentation vs Implementation Contradictions
README previously claimed "BM25" and "concurrent". Fixed to "PostgreSQL FTS" and "sequential".

## 36. Current Limitations
Sequential, small ground truth (3 samples), no Alembic, low test coverage.

## 37. Technical Debt
Ad-hoc migrations, hardcoded pricing, sequential run engine.

## 38. Unknowns
Exact state of Neon DB relies on running migration scripts.

## 39. EvalOS ↔ AgentOS Boundary
EvalOS evaluates AgentOS traces. Not implemented yet. EvalOS should receive structured traces, not run AgentOS internals.

## 40. EvalOS ↔ WOE Boundary
Not implemented.

## 41. Future Integrated Architecture
AgentOS (execution) -> EvalOS (evaluation) -> WOE (orchestration).

## 42. Flagship Assessment
**~8/10.** Strong architecture, rigorous methodology, but weak dataset size/ground truth.

## 43. Highest-Value Improvements
1. Bounded Concurrency (`asyncio.Semaphore`).
2. Alembic Migrations.
3. Larger Ground Truth (100+ reference answers).
4. `Experiment` Abstraction.
5. FastAPI/Dashboard.

## 44. Prioritized Roadmap
*   **Stage C (Infra):** Concurrency, Alembic, Experiments.
*   **Stage D (Product):** FastAPI, Dashboard.

## 45. Verification Checklist
`pytest tests/`, `python cli.py inspect-run <id>`.

## 46. Instructions for the Next Engineer / AI Model
*   Read this document first.
*   Do not touch `-1.0` evaluator logic.
*   Do not hold DB sessions open.
*   Do not rename `postgres_fts` to `bm25`.
*   Keep cache keys version-aware.
*   Add tests for new features.

## 47. Repository Reference Map
| Subsystem | File | Symbol |
|---|---|---|
| Database | `database.py` | `engine`, `AsyncSessionLocal` |
| Models | `models.py` | `EvaluationRun`, `Execution`, `MetricResult` |
| Retrieval | `retrieval.py` | `RetrievalEngine`, `fuse_rrf` |
| Run Engine | `run_engine.py` | `RunEngine` |
| Analysis | `analysis/` | `analyze_run`, `compare_runs`, `check_regression` |
| Caching | `cache.py` | `get_cached`, `set_cached` |
| CLI | `cli/main.py` | `app` |

## 48. Evidence / Confidence Table
| Claim | Evidence | Confidence |
|---|---|---|
| 88.9% Recall | `docs/benchmarks/02_retrieval_ablation.md` | HIGH |
| 96.8% Faithfulness | `docs/benchmarks/01_model_comparison.md` | HIGH |
| 100% Citation | `docs/benchmarks/11_citation_correctness.md` | HIGH (N=36) |
| 100% Reference Correctness | `docs/benchmarks/13_reference_answer.md` | LOW (N=3) |
| Judge is 13.2% lenient | `docs/benchmarks/03_evaluator_reliability.md` | MEDIUM (N=5) |
| Regression gate works | `docs/benchmarks/12_statistical_regression.md` | HIGH |
