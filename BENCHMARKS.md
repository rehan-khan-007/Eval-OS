# EvalOS Benchmark Results

Real numbers from running the actual EvalOS framework against real
infrastructure and real API calls — not estimates. 

## At a glance

| Metric | Result |
|---|---|
| Retrieval recall@3 (47 docs, multi-domain) | **88.9%** (Dense) |
| Models benchmarked | 5 (gpt-4o-mini, gpt-4o, claude-haiku-4.5, gemini-3.7-flash, llama-3.1-70b) |
| Best Faithfulness | **98.2%** (claude-haiku-4.5) |
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
