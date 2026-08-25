# ⚖️ EvalOS — Reproducible Evaluation Infrastructure for AI

> **EvalOS doesn't generate answers. It tells you if the system generating them actually works.**

Modern LLM systems are difficult to evaluate reliably. Given a new RAG pipeline or Agent, you shouldn't just inspect a few outputs and decide which "looks better." 

EvalOS is a rigorous, CLI-first framework that runs reproducible benchmarks, measures quality/cost/latency trade-offs, diagnoses *why* systems fail, and acts as a CI/CD gate for AI behavior.

---

## 🧠 The EvalOS Philosophy

EvalOS was built to prove empirically what works, not to assume "bigger is always better." Here are real findings EvalOS uncovered during its own development:

*   **The "Expensive Model" Trap:** EvalOS proved that `gpt-4o` costs **17x more** than `gpt-4o-mini`, but actually scored *lower* in faithfulness (hallucinated more) on the same RAG task.
*   **The "Hybrid is Always Better" Myth:** EvalOS proved that Hybrid retrieval (BM25 + Dense + RRF) actually *regressed* recall by 4 points compared to Dense-only, because BM25 introduced noise on PDF-extracted text.
*   **The "Overly Cautious LLM" Bug:** EvalOS diagnosed a failure mode where the LLM had the correct context but abstained unnecessarily, proving global accuracy scores hide real failure modes.

---

## 🚀 Core Capabilities

| Feature | Description |
| :--- | :--- |
| **Benchmark Matrix** | Run the same dataset across multiple models/retrievers to generate real Pareto frontiers of Quality vs Cost vs Latency. |
| **LLM-as-Judge** | Automated faithfulness evaluation via claim extraction and evidence matching. |
| **HITL Reliability** | Human-in-the-Loop CLI to audit the LLM Judge and calculate Inter-Rater Agreement (Cohen's Kappa). |
| **Failure Diagnosis** | Automatic taxonomy classification: Did it fail because of *Retrieval*, *Generation*, or *System Error*? |
| **Statistical Significance** | A/B comparison with 1000-iteration Bootstrap Confidence Intervals to prove differences aren't just noise. |
| **Regression Testing** | Set a baseline run and block deployments if a new run regresses beyond a configurable threshold. |
| **Zero-Cost Iteration** | Upstash Redis caching layer means re-running an evaluation on the same config costs $0.00 and finishes in seconds. |

---

## 🛠️ How to Use EvalOS (CLI First)

EvalOS is operated entirely via a modular Typer CLI. No dashboards required to run benchmarks.

### 1. Ingest a Dataset
`python cli.py ingest-dataset data/retrieval_qa.json`

### 2. Run a 5-Model Benchmark
Runs the dataset through 5 different LLMs, calculating real cost, latency, recall, and LLM-judge faithfulness.
`python cli.py run-benchmark --dataset-version dv-ds-retrieval_qa-v1 --models "openai/gpt-4o-mini,google/gemini-3.7-flash,anthropic/claude-haiku-4.5"`

### 3. Diagnose Failures
Instead of just seeing a score, see *why* it failed.
`python cli.py diagnose-run run-ccbcb9b2`
### [2] Retrieval Failures (2)
### [3] Generation Failures (6)

### 4. Check for Regressions (CI/CD)
Compare a new run against a baseline. Fails if recall drops by >2%.
`python cli.py regression-check run-baseline-id run-new-id --threshold 0.02`
# VERDICT: REGRESSION DETECTED. The new run is significantly worse.

---

## 🏗️ Architecture & Tech Stack

EvalOS is asynchronous by design, ensuring hundreds of concurrent API calls don't bottleneck.

*   **Database:** Neon Postgres (via `asyncpg` + `SQLAlchemy 2.0`). Used for relational data AND vector storage (`pgvector`) AND BM25 full-text search (`tsvector`).
*   **LLM Routing:** OpenRouter (via `AsyncOpenAI`).
*   **Caching:** Upstash Redis (prefixed with `evalos:`) for zero-cost iterative testing.
*   **Statistics:** `scikit-learn` and `numpy` for Bootstrap CIs and Cohen's Kappa.

### Project Structure
Eval-OS/
├── cli/                  # Modular Typer commands (run, inspect, compare, label)
├── adapters/             # System interfaces (OpenRouter, RAG, Mock)
├── evaluators/           # Deterministic (Recall, Abstention) & LLM-Judge
├── retrieval.py          # Dense, BM25, and Hybrid (RRF) search engines
├── analysis_engine.py    # Aggregation, Slicing, A/B, and Regression logic
├── cache.py              # Upstash Redis caching layer
└── docs/benchmarks/      # Real, documented benchmark results

---

## 📊 Real Benchmarks & Engineering Logs

We don't just claim EvalOS works; we use it to generate real, documented results.

*   📄 **[Executive Benchmark Summary](BENCHMARKS.md)** - The "At a glance" table and links to deep dives.
*   🔬 **[Deep Dive: 5-Model RAG Benchmark](docs/benchmarks/01_model_comparison.md)** - Proves gpt-4o-mini beats gpt-4o in faithfulness while being 17x cheaper.
*   🐛 **[Engineering Log](EVALOS_ENGINEERING_LOG.md)** - An honest record of the architecture decisions, async bugs found, and fixes applied during development.

---

## 💡 Why EvalOS?

> *"EvalOS was built to determine whether an AI system actually works, how well it works, why it fails, and what quality/cost/latency trade-offs it makes. Every reported number comes from an actual benchmark."*

---

## 🏗️ Architecture & Tech Stack

EvalOS is asynchronous by design, ensuring hundreds of concurrent API calls don't bottleneck.

*   **Database:** Neon Postgres (via 
