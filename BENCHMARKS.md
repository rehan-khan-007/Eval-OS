# EvalOS Benchmark Results

Real numbers from running the actual EvalOS framework against real
infrastructure and real API calls — not estimates. Each result below
states exactly what was measured, how, and what its limitations are.

## At a glance

| Metric | Result |
|---|---|
| Retrieval recall@3 (47 docs, multi-domain) | **88.9%** |
| Evaluation cost (36 examples) | **$0.0064** |
| Evaluation latency (avg per example) | 5.45s |
| RAG generation model | `openai/gpt-4o-mini` |
| Embedding model | `openai/text-embedding-3-small` |

---

## RAG retrieval & generation evaluation

**What was measured:** Source-level recall@3 — does the EvalOS RAG
pipeline (using `pgvector` cosine similarity) surface a chunk from
the correct source document, within the top 3 results, for a real
question. It also measures the end-to-end latency and cost of
retrieving the context and generating an answer via OpenRouter.

**How:** `python cli.py run-eval --system rag --model openai/gpt-4o-mini`
against `dv-ds-retrieval_qa-v1`. The corpus consists of 47 real PDFs
(19 arXiv quantum/thermal papers, 28 SEBI financial education docs)
parsed into ~1,500 chunks. The dataset contains 36 real questions
(35 with expected sources, 1 negative control).

**Result:**

| Metric | Value |
|---|---|
| Total Examples | 36 |
| Successes | 36 (100% execution rate) |
| Failures | 0 |
| Source Recall@3 | 32/36 (88.9%) |
| Total Cost | $0.006444 |
| Avg Latency | 5459.15 ms |
| Min Latency | 3601.10 ms |
| Max Latency | 10626.36 ms |

**Honest caveats:**
- The corpus size (47 docs) is intentionally scoped to the exact
  documents referenced by the 35-question eval dataset. The system
  is architecturally capable of handling 132+ documents (as proven
  in AgentOS), but EvalOS is currently focused on measuring the
  quality of the reference RAG pipeline against a known baseline.
- The 1 negative control question ("What is quantum entanglement?")
  correctly did not impact the recall score, but `pgvector` still
  returned its nearest neighbors. A true "abstention" metric (where
  the system recognizes when to say "I don't know") is a planned
  feature for Phase 5.
- Latency includes the full I/O loop: embedding the query, querying
  Neon Postgres, sending the context to OpenRouter, and streaming the
  response. The high variance (3.6s to 10.6s) is largely attributable
  to OpenRouter/Upstream API latency variance, not the local database
  query.

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
