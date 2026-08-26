# EvalOS Benchmark Results

Real numbers from running the actual EvalOS framework against real
infrastructure and real API calls — not estimates. 

## At a glance

| Metric | Result |
|---|---|
| Retrieval recall@3 (47 docs, multi-domain) | **88.9%** (Dense) |
| Retrieval recall@5 (47 docs, multi-domain) | **91.7%** (Dense, top_k=5) |
| Models benchmarked | 5 (gpt-4o-mini, gpt-4o, claude-haiku-4.5, gemini-3.7-flash, llama-3.1-70b) |
| Best Faithfulness | **99.0%** (gpt-4o-mini, top_k=5) |
| Best Value (Quality/Cost) | **gpt-4o-mini** (96.8% faithfulness for $0.006) |
| LLM Judge Human Agreement | **100.0%** (Raw Agreement on 5-sample HITL audit) |
| Total spend across 5-model benchmark | **~$0.21** |

---

## Detailed Reports

1. **[5-Model LLM RAG Benchmark](docs/benchmarks/01_model_comparison.md)**
   *Compares cost, latency, and faithfulness across 5 LLMs. Proves gpt-4o-mini beats gpt-4o in faithfulness while being 17x cheaper.*
2. **[Retrieval Ablation & Slice Analysis](docs/benchmarks/02_retrieval_ablation.md)**
   *Proves Dense-only beats Hybrid (RRF) on this dataset, and isolates retrieval failures to the Quantum domain (84.4% recall).*
3. **[HITL Evaluator Reliability](docs/benchmarks/03_evaluator_reliability.md)**
   *Proves the LLM-as-Judge evaluator is highly reliable via human auditing (100% raw agreement).*
4. **[A/B Comparison: Dense vs Hybrid](docs/benchmarks/04_ab_comparison.md)**
   *Proves the 4-point recall gap between Dense and Hybrid is NOT statistically significant at this sample size.*
5. **[Answerability & Abstention](docs/benchmarks/05_answerability_abstention.md)**
   *Proves the system abstains correctly when retrieval fails, rather than hallucinating (80.6% abstention accuracy, 96.8% faithfulness).*
6. **[Evaluation Caching & Cost Efficiency](docs/benchmarks/06_caching_efficiency.md)**
   *Proves iterative benchmarking is free: a cached re-run of the 36-question dataset costs $0.00 and finishes in seconds.*
7. **[Failure Diagnosis Taxonomy](docs/benchmarks/07_failure_diagnosis.md)**
   *Classifies failures into Retrieval, Generation, and System errors. Diagnoses an "overly cautious LLM" bug where the model abstains despite having the correct context.*
8. **[Regression Testing](docs/benchmarks/08_regression_testing.md)**
   *Proves EvalOS can act as a CI/CD gate, detecting a 4.2% recall regression when switching from Dense to Hybrid retrieval.*
9. **[Configuration-Driven Runtime](docs/benchmarks/09_config_driven_runtime.md)**
   *Proves the database configuration drives the runtime. Increasing `top_k` to 5 dynamically changed the evaluator to `recall@5` and improved recall to 91.7%.*

---

## Engineering Infrastructure

EvalOS itself was built to be a reproducible evaluation framework.
The infrastructure supporting these benchmarks is verified:

- **Postgres + pgvector:** All runs, metrics, traces, and vector
  embeddings are stored in a single Neon Postgres instance. This
  allows complex SQL joins for failure analysis (e.g., joining
  `executions` with `metric_results` to find exactly *why* a
  retrieval failed).
- **Asynchronous by design:** All API calls (OpenRouter generation
  and embeddings) use `asyncpg` and `AsyncOpenAI` to prevent I/O
  bottlenecks during large-scale evaluation runs.
- **CLI-first:** All benchmarks are reproducible via Typer CLI
  commands, not hardcoded scripts.
- **Redis Caching:** LLM generations and Embeddings are cached in Upstash Redis (prefixed with `evalos:`) to enable $0.00 iterative testing.
- **Config-Driven:** The `SystemConfig` table records exact parameters (`top_k`, `embedding_model`, `retriever_type`), which are passed down to the runtime to ensure 100% reproducibility.
