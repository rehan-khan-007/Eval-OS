content = '''# EvalOS — Project Context & Engineering Handoff

## 1. Executive Summary
EvalOS is an advanced research prototype for evaluating AI/RAG systems. The repository contains a functioning evaluation pipeline spanning dataset execution, retrieval evaluation, LLM-based evaluation, HITL calibration, statistical comparison, regression detection, caching, and CLI tooling. However, several areas remain research- or prototype-grade, particularly ground-truth coverage, benchmark isolation, test coverage, migration discipline, concurrency, and experiment provenance. 

EvalOS produces statistical comparisons and regression decisions using paired bootstrap confidence intervals and configurable thresholds. It is **not** yet production-grade evaluation infrastructure.

## 2. What EvalOS Does NOT Guarantee
*   LLM-judge scores are not objective ground truth.
*   High retrieval recall does not imply answer correctness.
*   High faithfulness does not imply completeness.
*   Statistical significance does not imply practical significance.
*   Non-significance does not prove equivalence.
*   Five human labels do not establish population-level judge calibration.
*   Three reference answers do not validate the evaluator across the dataset.
*   A benchmark tuned on the same dataset does not establish generalization.
*   Estimated cost is not provider billing.
*   Generation latency is not total evaluation latency.
*   Successful CLI execution is not production readiness.
*   Async code does not imply concurrent execution.

## 3. How to Resolve Conflicts
When sources disagree, the following hierarchy is authoritative:
1.  Executed code
2.  Tests
3.  Database/schema definitions
4.  Current benchmark artifacts
5.  Git diffs/history
6.  Engineering logs
7.  README/documentation
8.  AI-generated descriptions

If code and documentation disagree, do not silently “fix” the interpretation. Record the discrepancy.

## 4. Intended Architecture
AI System -> EvalOS -> (Quality, Cost, Latency) -> Diagnosis -> Regression Detection -> HITL Calibration -> CI/CD Gate.

## 5. Current Reality vs Intended Architecture
*   **Implemented:** Core async engine, Postgres schema, adapters, evaluators, statistical analysis, HITL, caching, CLI.
*   **Missing:** True bounded concurrency (`asyncio.Semaphore`), `Experiment` abstraction, Alembic migrations, FastAPI/Dashboard, Held-out test set.

## 6. Repository Structure
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
├── tests/                 # Pytest suite (2 modules)
└── docs/benchmarks/      # Real, documented benchmark results

## 7. Evaluation Lifecycle (Dependency Graph)
Dataset
  ↓
SystemConfig
  ↓
Run
  ↓
Execution
  ↓
Adapter
  ├── Retrieval
  └── Generation
       ↓
Evaluation
  ├── Deterministic evaluators
  └── LLM evaluators
       ↓
MetricResult
       ↓
Analysis
  ├── Aggregation
  ├── Diagnosis
  ├── Statistical comparison
  ├── Calibration
  └── Regression

HumanLabel
     ↓
Calibration

## 8. Dataset Architecture
*   **Current Dataset:** `dv-ds-retrieval_qa-v1` (36 questions, 4 domains).
*   **Identity:** Example IDs are generated using `hash(question) % 10**8`. **Warning:** Python's `hash()` is randomized per process by default. This is a P0 reproducibility bug to be fixed.

## 9. Ground Truth & Evaluation Evidence Hierarchy
| Signal           |   N | Nature                    | Trust level                              |
| ---------------- | --: | ------------------------- | ---------------------------------------- |
| Expected source  |  36 | Dataset annotation        | Medium                                   |
| Reference answer |   3 | Human reference           | High for those 3                         |
| Gold chunk       |   3 | Derived semantic labeling | Medium                                   |
| Human score      |   5 | Human annotation          | High individually, low statistical power |
| LLM judge        |  36 | Automated evaluator       | Not ground truth                         |

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

## 14. Metric Semantics Registry (Example)
*   **Name:** `source_recall@k`
*   **Definition:** Fraction of examples where at least one expected source appears in top-k retrieved chunks.
*   **Range:** [0,1]. Higher is better.
*   **Ground truth:** `expected_sources` or `gold_chunk_ids`.
*   **Limitations:** Document-level recall does not prove evidence-level correctness.

## 15. Run Engine
`RunEngine` processes examples **sequentially**. It creates an `Execution`, calls the adapter, runs the evaluators, and saves `MetricResult`s. DB sessions are closed immediately after fetching data.

## 16. Analysis Engine
Split into `analysis/` directory:
*   `aggregation.py`: Global averages and slice-based metrics.
*   `statistics.py`: Paired bootstrap CIs (seed=42, 1000 iters).
*   `diagnosis.py`: Rule-based failure taxonomy.
*   `regression.py`: Threshold + Statistical Significance (CI excludes zero).
*   `calibration.py`: Pearson, MAE, Confusion Matrix for HITL.

## 17. Statistical Analysis & Regression
`compare_runs()` calculates paired differences and bootstraps the mean difference. If the 95% CI excludes zero, it is significant.
`check_regression()` flags a metric if it drops by `threshold` (e.g., 2%) AND `is_significant` is True. Latency is threshold-only (500ms).

## 18. HITL Calibration
`HumanLabel` stores `human_score`, `failure_category`, `comment`. In the current N=5 pilot sample, the judge's mean score was 0.132 higher than human scores, indicating apparent leniency in this pilot sample. **This is not evidence that the judge is globally 13.2% too lenient.**

## 19. Caching & Cost Accounting
`cache.py` uses Redis. Keys are version-aware. `pickle` is used for serialization.
Cost is `estimated_cost`: hardcoded pricing in `rag_adapter.py` based on token counts. Pricing must be versioned by provider/model/date.

## 20. Experiment Provenance Matrix
| Parameter         | Persisted? | Where?       | Required for reproduction? |
| ----------------- | ---------- | ------------ | -------------------------- |
| Dataset version   | Yes        | EvalRun      | YES                        |
| Code SHA          | No         | -            | YES                        |
| Model             | Yes        | SystemConfig | YES                        |
| Prompt version    | Yes        | SystemConfig | YES                        |
| Judge             | Yes        | MetricResult | YES                        |
| Retrieval config  | Yes        | SystemConfig | YES                        |
| Evaluator version | Yes        | MetricResult | YES                        |
| Seed              | Yes (stats)| Analysis      | Depends                    |
| Dependency lock   | No         | -            | YES                        |
| Cache state       | No         | -            | For latency                |

## 21. Engineering Lessons / Bug History
1.  **Neon Idle Timeouts:** Holding DB sessions open during API calls causes `InterfaceError`. Fix: Short-lived sessions.
2.  **MissingGreenlet:** Lazy loading outside async session. Fix: `selectinload`.
3.  **JSONB Mutation:** SQLAlchemy doesn't detect in-place JSONB dict mutations. Fix: Raw SQL `jsonb_set`.
4.  **BM25 Naming:** `ts_rank` is not BM25. Fix: Renamed to `postgres_fts`.
5.  **RRF Identity:** Using `(source, text)` causes chunk collapse. Fix: Use `chunk_id`.
6.  **Evaluator Errors:** API timeouts returning `0.0` dragged down averages. Fix: Return `-1.0` and filter in aggregation.
7.  **Typer Async:** `async def` commands aren't awaited by Typer. Fix: Wrap in `def run(): asyncio.run()`.

## 22. Architectural Invariants
*   **I1 — Evaluator failure ≠ system failure:** `-1.0` must remain distinct from `0.0`.
*   **I2 — Chunk identity is immutable:** RRF must use `chunk_id`, not `(source, text)`.
*   **I3 — DB sessions must not span external API calls:** Protects against Neon timeouts.
*   **I4 — Cache identity must include evaluator version:** Prevents stale results.
*   **I5 — Dataset identity must be deterministic:** Example IDs must not rely on Python `hash()`.
*   **I6 — Benchmark numbers must always carry sample size:** Never report `96.8%` without `N=36, dataset=v1`.

## 23. Things That Must Not Be Changed Casually
*   `-1.0` score semantics in evaluators.
*   `chunk_id` as RRF identity key.
*   Short-lived DB session pattern.
*   Cache key versioning logic.

## 24. Security & Testing
`.env` for secrets. `pickle` in Redis is a risk if Redis is compromised.
2 test modules currently present (`test_rrf.py`, `test_cache.py`). Very low coverage.

## 25. Performance / Scalability
**Sequential execution.** Will be slow for 1000s of examples. Needs `asyncio.Semaphore`.

## 26. Documentation vs Implementation Contradictions
README previously claimed "BM25" and "concurrent". Fixed to "PostgreSQL FTS" and "sequential".

## 27. EvalOS ↔ AgentOS Boundary
EvalOS evaluates AgentOS traces. Not implemented yet. EvalOS must not become an AgentOS execution dependency. It should receive structured traces, not run AgentOS internals.

## 28. Flagship Assessment
**Advanced research prototype / early evaluation infrastructure.**
*   Architecture: ~8/10
*   Engineering: ~7/10
*   Evaluation methodology: ~6/10
*   Statistical infrastructure: ~7/10
*   Reproducibility: ~5.5/10
*   Testing: ~4/10
*   Benchmark evidence: ~5.5/10
*   Research potential: ~9/10

## 29. Prioritized Roadmap
### P0 — Fix measurement foundations
1.  **Deterministic example IDs** (SHA256 instead of Python hash).
2.  **Experiment/run provenance** (Code SHA, dependency lock).
3.  **Held-out evaluation dataset** (stop tuning on the test set).
4.  **Explicit metric semantics registry** (in code, not just docs).
5.  **Clear evaluator-error semantics** (ensure -1.0 is never aggregated as 0.0).

### P1 — Make infrastructure trustworthy
6.  **Real migration framework** (Alembic).
7.  **Much stronger automated testing** (Evaluators, DB, CLI).
8.  **Bounded concurrency** (`asyncio.Semaphore`).
9.  **Failure-injection tests**.
10. **Cache/latency benchmark separation**.

### P1 — Strengthen evaluation science
11. **100+ manually verified reference answers.**
12. **Larger HITL calibration** (multiple human annotators).
13. **Evaluator bias analysis.**
14. **Benchmark stratification.**

### P2 — Platformization
15. **Experiment abstraction.**
16. **Run comparison API & Dashboard.**
17. **CI/CD integration.**
18. **AgentOS trace adapter.**

## 30. Instructions for the Next Engineer / AI Model
*   Read this document first.
*   Do not interpret "implemented" as "validated".
*   Do not touch `-1.0` evaluator logic.
*   Do not hold DB sessions open.
*   Do not rename `postgres_fts` to `bm25`.
*   Keep cache keys version-aware.
*   Add tests for new features.

## 31. Repository Reference Map
| Subsystem | File | Symbol |
|---|---|---|
| Database | `database.py` | `engine`, `AsyncSessionLocal` |
| Models | `models.py` | `EvaluationRun`, `Execution`, `MetricResult` |
| Retrieval | `retrieval.py` | `RetrievalEngine`, `fuse_rrf` |
| Run Engine | `run_engine.py` | `RunEngine` |
| Analysis | `analysis/` | `analyze_run`, `compare_runs`, `check_regression` |
| Caching | `cache.py` | `get_cached`, `set_cached` |
| CLI | `cli/main.py` | `app` |

## 32. Evidence / Confidence Table
| Claim | N | Dataset | Source | Implementation Verified | Artifact Verified | Methodologically Strong? | Confidence |
| ----- | -: | ------- | ------ | ----------------------- | ----------------- | ------------------------ | ---------- |
| 88.9% Recall | 36 | v1 | benchmark | YES | YES | NO (no held-out set) | MEDIUM |
| 96.8% Faithfulness | 36 | v1 | benchmark | YES | YES | NO (LLM judge, no held-out set) | MEDIUM |
| 100% Citation | 36 | v1 | benchmark | YES | YES | NO (LLM judge) | MEDIUM |
| 100% Reference Correctness | 3 | v1 | benchmark | YES | YES | NO (N=3 pilot) | LOW |
| Judge is 13.2% lenient | 5 | v1 | benchmark | YES | YES | NO (N=5 pilot) | LOW |
| Regression gate works | 36 | v1 | benchmark | YES | YES | YES | HIGH |
'''

with open("PROJECT_CONTEXT.md", "w") as f:
    f.write(content)

print("PROJECT_CONTEXT.md generated successfully with CTO corrections!")
