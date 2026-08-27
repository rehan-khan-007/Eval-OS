# EvalOS — Project Context & Engineering Handoff

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
1.  Executed implementation
2.  Passing tests + test assertions
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
Raw execution artifacts
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
*   **Identity:** Example IDs are generated using `hashlib.sha256(question.encode()).hexdigest()[:16]`. This ensures deterministic, reproducible Example IDs independent of Python process randomization.

## 9. Ground Truth & Evidence Hierarchy
| Signal           |   N | Nature                    | Evidence status      | Statistical Power |
| ---------------- | --: | ------------------------- | -------------------- | ----------------- |
| Expected source  |  36 | Dataset annotation        | Unverified           | High (N=36)       |
| Reference answer |   3 | Human reference           | Human-authored       | Low (N=3)         |
| Gold chunk       |   3 | Derived semantic labeling | Derived              | Low (N=3)         |
| Human score      |   5 | Human annotation          | Human-verified       | Low (N=5)         |
| LLM judge        |  36 | Automated evaluator       | Automated            | High (N=36)       |

## 10. Document Corpus Provenance
*   **Current Corpus:** 47 real PDFs (19 arXiv, 28 SEBI).
*   **Storage:** Tracked directly in Git under `data/docs/papers/`. This is a benchmark dependency and repository size risk.
*   **Provenance Gap:** Source URLs and retrieval dates are known via fetch scripts, but `document_hash`, `source_uri`, and `document_version` are **not** persisted in the database. 
*   **Future Requirement:** Move to dataset manifests or object storage (LFS) and persist document hashes in `DocumentChunk` metadata.

## 11. Database Architecture
*   **Tables:** `datasets`, `dataset_versions`, `evaluation_examples`, `system_configs`, `evaluation_runs`, `executions`, `metric_results`, `document_chunks`, `human_labels`.
*   **JSONB:** Heavily used for metadata, retrieval config, and evidence breakdowns.
*   **Migrations:** Currently ad-hoc Python scripts in `migrations/`. No Alembic.

## 12. System Adapter Architecture
`BaseSystemAdapter` -> `MockSystemAdapter`, `OpenRouterAdapter`, `RAGAdapter`.
The adapter returns a dict with `answer`, `retrieved_evidence`, `latency_ms`, `cost`, `tokens_in`, `tokens_out`, `error`. Evaluation code must not modify the system-under-test.

## 13. Retrieval / RAG Architecture
`RetrievalEngine` supports `dense` (pgvector), `postgres_fts` (tsvector), and `hybrid` (RRF).
*   **RRF:** Pure function `fuse_rrf()` in `retrieval.py`. Uses `chunk_id` as unique key.
*   **Config-Driven:** `top_k` and `embedding_model` are passed from `SystemConfig` to the adapter.

## 14. Evaluation Architecture
`BaseEvaluator` (async). 
*   **Deterministic:** `LatencyEvaluator`, `SourceRecallEvaluator` (v2: chunk-level), `ToolSelectionEvaluator`, `AbstentionEvaluator`.
*   **LLM-as-Judge:** `LLMJudgeEvaluator` (faithfulness), `AnswerQualityEvaluator` (correctness/completeness), `CitationEvaluator` (citation support), `ReferenceAnswerEvaluator` (ground truth match).

## 15. Evaluator Result Contract
Evaluators return `score` (-1.0 to 1.0), `explanation`, `evidence_breakdown`, `status`.
*   `score = 1.0` -> valid success
*   `score = 0.0` -> valid failure
*   `score = -1.0` -> indeterminate/evaluator failure
*   `status` -> authoritative indicator of evaluation execution state.

**Contract for Indeterminate results (`-1.0`):**
*   Must not be silently treated as failures.
*   Must not enter quality averages.
*   Must be countable.
*   Must be visible in run diagnostics.

## 16. Metric Semantics Registry (Example)
*   **Name:** `source_recall@k`
*   **Definition:** Fraction of examples where at least one expected source appears in top-k retrieved chunks.
*   **Range:** [0,1]. Higher is better.
*   **Ground truth:** `expected_sources` or `gold_chunk_ids`.
*   **Limitations:** Document-level recall does not prove evidence-level correctness.
*   **Note:** The registry is currently documentation-level unless an actual code-backed registry exists.

## 17. Run Engine
`RunEngine` processes examples **sequentially**. It creates an `Execution`, calls the adapter, runs the evaluators, and saves `MetricResult`s. DB sessions are closed immediately after fetching data.

## 18. Analysis Engine
Split into `analysis/` directory:
*   `aggregation.py`: Global averages and slice-based metrics.
*   `statistics.py`: Paired bootstrap CIs (seed=42, 1000 iters).
*   `diagnosis.py`: Rule-based failure taxonomy.
*   `regression.py`: Threshold + Statistical Significance (CI excludes zero).
*   `calibration.py`: Pearson, MAE, Confusion Matrix for HITL.

## 19. Statistical Methodology
`compare_runs()` calculates paired differences and bootstraps the mean difference. If the 95% CI excludes zero, it is significant. **Note:** This is the current implementation's decision rule, not a universal definition of statistical significance. The framework currently does not establish equivalence when the CI contains zero.

## 20. Regression Methodology
`check_regression()` flags a metric if it drops by `threshold` (e.g., 2%) AND `is_significant` is True. Latency is threshold-only (500ms). **Future work:** Consider explicit effect-size reporting rather than only threshold/significance flags.

## 21. HITL Calibration
`HumanLabel` stores `human_score`, `failure_category`, `comment`. In the current N=5 pilot sample, the judge's mean score was 0.132 higher than human scores, indicating apparent leniency in this pilot sample. **N=5 is sufficient to exercise the calibration pipeline, not to validate judge reliability.**

## 22. Caching & Cost Accounting
`cache.py` uses Redis. Keys are version-aware. `pickle` is used for serialization. **Security:** Redis cache is trusted infrastructure. Pickle must never be used on attacker-controlled cache contents. If the Redis trust boundary changes, replace pickle with a safe serialization format.
Cost is `estimated_cost`: hardcoded pricing in `rag_adapter.py` based on token counts. Pricing must be versioned by provider/model/date.

## 23. Experiment Provenance Matrix
| Parameter         | Persisted? | Where?       | Required for reproduction? |
| ----------------- | ---------- | ------------ | -------------------------- |
| Dataset version   | Yes        | EvalRun      | YES                        |
| Code SHA          | Yes        | EvalRun      | YES                        |
| Model             | Yes        | SystemConfig | YES                        |
| Prompt version    | Yes        | SystemConfig | YES                        |
| Judge             | Yes        | MetricResult | YES                        |
| Retrieval config  | Yes        | SystemConfig | YES                        |
| Evaluator version | Yes        | MetricResult | YES                        |
| Seed              | Yes (stats)| Analysis      | Depends                    |
| Dependency lock   | Yes        | EvalRun      | YES                        |
| Cache state       | No         | -            | For latency                |

## 24. Stochasticity / Repeated-Trial Evaluation
*   **Current State:** The system evaluates LLMs at `temperature=0.0`. It executes exactly one trial per example.
*   **Limitation:** LLMs are stochastic. A single trial does not account for variance.
*   **Future Work (P1):** Support repeated trials per example to account for model stochasticity in confidence intervals.

## 25. Multiple Comparisons
Current regression analysis evaluates metrics independently; multiple-comparison control (e.g., Bonferroni/FDR) is not currently implemented.

## 26. Engineering Lessons / Bug History
1.  **Neon Idle Timeouts:** Holding DB sessions open during API calls causes `InterfaceError`. Fix: Short-lived sessions.
2.  **MissingGreenlet:** Lazy loading outside async session. Fix: `selectinload`.
3.  **JSONB Mutation:** SQLAlchemy doesn't detect in-place JSONB dict mutations. Fix: Raw SQL `jsonb_set`.
4.  **BM25 Naming:** `ts_rank` is not BM25. Fix: Renamed to `postgres_fts`.
5.  **RRF Identity:** Using `(source, text)` causes chunk collapse. Fix: Use `chunk_id`.
6.  **Evaluator Errors:** API timeouts returning `0.0` dragged down averages. Fix: Return `-1.0` and filter in aggregation.
7.  **Typer Async:** `async def` commands aren't awaited by Typer. Fix: Wrap in `def run(): asyncio.run()`.

## 27. Architectural Invariants
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

## 28. Things That Must Not Be Changed Casually
*   Do not change the `-1.0` evaluator-error semantics without first auditing all aggregation, statistics, regression, caching, persistence, and downstream consumers and adding migration/regression tests.
*   Do not reintroduce long-lived DB sessions across external API calls.
*   `chunk_id` as RRF identity key.
*   Cache key versioning logic.

## 29. Security & Testing
`.env` for secrets. `pickle` in Redis is a risk if Redis is compromised.
2 test modules currently present (`test_rrf.py`, `test_cache.py`). Very low coverage.

## 30. Performance / Scalability
**Sequential execution.** Will be slow for 1000s of examples. Needs `asyncio.Semaphore`.

## 31. Documentation vs Implementation Contradictions
README previously claimed "BM25" and "concurrent". Fixed to "PostgreSQL FTS" and "sequential".

## 32. EvalOS ↔ AgentOS Boundary
EvalOS evaluates AgentOS traces. Not implemented yet. EvalOS must not become an AgentOS execution dependency. It should receive structured traces, not run AgentOS internals.
**Future Minimum Trace Contract:**
AgentTrace
├── run_id
├── task_id
├── model
├── input
├── final_output
├── tool_calls[]
│   ├── tool_name
│   ├── arguments
│   ├── result
│   └── latency
├── retrieval_events[]
├── token_usage
├── cost
├── timestamps
└── error

## 33. EvalOS ↔ WOE Boundary
Not implemented.
AgentOS -> produces execution/agent trace.
WOE -> produces workflow execution trace.
EvalOS -> evaluates both.

## 34. Flagship Assessment
**Advanced research prototype / early evaluation infrastructure.**
*   Architecture: ~8/10
*   Engineering: ~7/10
*   Evaluation methodology: ~6/10
*   Statistical infrastructure: ~7/10
*   Reproducibility: ~5.5/10
*   Testing: ~4/10
*   Benchmark evidence: ~5.5/10
*   Research potential: ~9/10

## 35. Prioritized Roadmap
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
11. **Experiment abstraction** (Group runs under experiments).

### P1 — Strengthen evaluation science
12. **100+ manually verified reference answers.**
13. **Larger HITL calibration** (multiple human annotators).
14. **Evaluator bias analysis.**
15. **Benchmark stratification.**
16. **Stochastic / Repeated-trial evaluation.**

### P2 — Platformization
17. **Run comparison API & Dashboard.**
18. **CI/CD integration.**
19. **AgentOS trace adapter.**

## 36. Instructions for the Next Engineer / AI Model
*   Read this document first.
*   Do not interpret "implemented" as "validated".
*   Do not change the `-1.0` evaluator logic without an impact audit.
*   Do not hold DB sessions open.
*   Do not rename `postgres_fts` to `bm25`.
*   Keep cache keys version-aware.
*   Add tests for new features.

## 37. Repository Reference Map
| Subsystem | File | Symbol |
|---|---|---|
| Database | `database.py` | `engine`, `AsyncSessionLocal` |
| Models | `models.py` | `EvaluationRun`, `Execution`, `MetricResult` |
| Retrieval | `retrieval.py` | `RetrievalEngine`, `fuse_rrf` |
| Run Engine | `run_engine.py` | `RunEngine` |
| Analysis | `analysis/` | `analyze_run`, `compare_runs`, `check_regression` |
| Caching | `cache.py` | `get_cached`, `set_cached` |
| CLI | `cli/main.py` | `app` |

## 38. Evidence / Confidence Table
*Artifact Verified = the benchmark result can be traced to a committed/generated run artifact containing sufficient information to independently inspect the reported result.*

| Claim | N | Dataset | Source | Impl. Verified | Artifact Verified | Method. Strong? | Confidence |
| ----- | -: | ------- | ------ | -------------- | ----------------- | --------------- | ---------- |
| 88.9% Recall | 36 | v1 | benchmark | YES | YES | NO (no held-out set) | MEDIUM |
| 96.8% Faithfulness | 36 | v1 | benchmark | YES | YES | NO (LLM judge) | MEDIUM |
| 100% Citation | 36 | v1 | benchmark | YES | YES | NO (LLM judge) | MEDIUM |
| 100% Reference Correctness | 3 | v1 | benchmark | YES | YES | NO (N=3 pilot) | LOW |
| Judge is 13.2% lenient | 5 | v1 | benchmark | YES | YES | NO (N=5 pilot) | LOW |
| Regression gate works | 36 | v1 | benchmark | YES | YES | YES | HIGH |


---

## Final Audit (FA) Update: Scientific Maturity & Hardening

The Final CTO Audit required EvalOS to stop adding features and focus entirely on scientific validity, testing, and security. The following phases were completed:

### FA Phase 1: Scientific Rigor
*   **Inconclusive State:** Regression engine no longer forces binary PASS/FAIL. If a metric drops by the threshold but the 95% CI touches zero, the verdict is `INCONCLUSIVE`.
*   **Metric Direction:** Added a registry for `higher_is_better` vs `lower_is_better` metrics.
*   **Strict N:** Statistical comparisons now explicitly track `paired_valid_examples` (N).

### FA Phase 2: Contracts & Provenance
*   **Pydantic Schemas:** FastAPI backend now uses strict response models (`RunMetricsSchema`, `PlaygroundResponseSchema`), fixing the OpenAPI docs and guaranteeing frontend stability.
*   **Run Fingerprint:** Runs now record a SHA256 `run_fingerprint` of the canonical JSON configuration (code, dataset, config, evaluators, dependencies). This is a provenance fingerprint, not a guarantee of identical execution.
*   **Safe Errors:** Playground endpoint no longer returns raw exception strings.

### FA Phase 3: Testing
*   **Test Suite Expanded:** 19 tests now pass (up from 6). Added `test_statistics.py` (bootstrap CIs, zero variance), `test_regression.py` (full decision matrix), and `test_evaluators.py` (malformed JSON, empty claims, markdown parsing).
*   **Cache Isolation:** Evaluator tests now mock the Redis cache to prevent state contamination between tests.

### FA Phase 4: Playground Hardening
*   **Rate Limiting:** Added `slowapi` to limit Playground abuse (5 req/min per IP).
*   **Size Limits:** Questions are capped at 500 characters.
*   **Save Candidate Case:** Users can save interesting playground failures to a `dv-playground-candidates-v1` dataset for human review, preventing benchmark contamination.

### Final Maturity Assessment
EvalOS is now an **Advanced Research Prototype / Early Evaluation Infrastructure**.
*   Architecture: 8.5/10
*   Engineering: 8/10
*   Evaluation methodology: 7.5/10
*   Statistical infrastructure: 8/10
*   Testing: 7/10
*   Security: 7/10
*   Flagship potential: 9.2/10
