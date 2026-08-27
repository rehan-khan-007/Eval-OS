# ⚖️ EvalOS — Reproducible Evaluation Infrastructure for AI

> **EvalOS doesn't generate answers. It tells you if the system generating them actually works.**

Modern LLM systems are difficult to evaluate reliably. Given a new RAG pipeline or Agent, you shouldn't just inspect a few outputs and decide which "looks better." 

EvalOS is a rigorous, full-stack framework that runs reproducible benchmarks, measures quality/cost/latency trade-offs, diagnoses *why* systems fail, and acts as a CI/CD gate for AI behavior.

---

## 🌐 Live Demo

EvalOS is deployed as a full-stack application. You can view the live dashboard and API right now:

*   **📊 Dashboard UI:** [https://evalos-dashboard.onrender.com](https://evalos-dashboard.onrender.com)
*   **⚡ API Docs (Swagger):** [https://eval-os.onrender.com/docs](https://eval-os.onrender.com/docs)

---

## 🧠 The EvalOS Philosophy

EvalOS was built to prove empirically what works, not to assume "bigger is always better." Here are real findings EvalOS observed on its own benchmark:

*   **The "Expensive Model" Trap:** On this benchmark, `gpt-4o` cost ~15x more than `gpt-4o-mini`, but actually scored *lower* in faithfulness (hallucinated more) on the same RAG task.
*   **The "Hybrid is Always Better" Myth:** EvalOS observed that Hybrid retrieval (Postgres FTS + Dense + RRF) actually *regressed* recall by 4 points compared to Dense-only, because FTS introduced noise on PDF-extracted text.
*   **The "Overly Cautious LLM" Bug:** EvalOS diagnosed a failure mode where the LLM had the correct context but abstained unnecessarily, proving global accuracy scores hide real failure modes.

---

## 🚀 Core Capabilities

| Feature | Description |
| :--- | :--- |
| **Experiment Abstraction** | Group multiple `EvaluationRun`s (e.g., a 5-model benchmark) under a single `Experiment` with full Git SHA & dependency provenance. |
| **Benchmark Matrix** | Run the same dataset across multiple models/retrievers to generate real Pareto frontiers of Quality vs Cost vs Latency. |
| **LLM-as-Judge** | Automated faithfulness evaluation via claim extraction and evidence matching. |
| **Citation & Reference** | Verifies that specific cited chunks support specific claims, and compares answers against ground-truth reference answers. |
| **HITL Calibration** | Human-in-the-Loop CLI to audit the LLM Judge and calculate Inter-Rater Agreement (Pearson, MAE, Confusion Matrix). |
| **Failure Diagnosis** | Automatic taxonomy classification: Did it fail because of *Retrieval*, *Generation*, or *System Error*? |
| **Statistical Significance** | A/B comparison with 1000-iteration Bootstrap Confidence Intervals to prove differences aren't just noise. |
| **Regression Testing** | Set a baseline run and block deployments if a new run regresses beyond a threshold AND is statistically significant. |
| **Bounded Concurrency** | `asyncio.Semaphore` ensures hundreds of examples are processed in parallel without hitting API rate limits. |
| **Cached Iteration** | Upstash Redis caching layer (version-aware keys) means re-running an evaluation on the same config eliminates duplicate LLM inference cost. |

---

## 🛠️ How to Use EvalOS (CLI First)

EvalOS is operated entirely via a modular Typer CLI. No dashboards required to run benchmarks.

### 1. Ingest a Dataset
`python cli.py ingest-dataset data/retrieval_qa.json`

### 2. Run a Multi-Model Benchmark
Runs the dataset through 5 different LLMs concurrently, calculating real cost, latency, recall, and LLM-judge faithfulness, grouped under an Experiment.
`python cli.py run-benchmark --dataset-version dv-ds-retrieval_qa-v1 --models "openai/gpt-4o-mini,google/gemini-3.7-flash,anthropic/claude-haiku-4.5" --concurrency 5 --experiment-name "Model Comparison"`

### 3. Diagnose Failures
Instead of just seeing a score, see *why* it failed.
`python cli.py diagnose-run run-ccbcb9b2`
# [2] Retrieval Failures (2)
# [3] Generation Failures (6)

### 4. Check for Regressions (CI/CD)
Compare a new run against a baseline. Fails if recall drops by >2% AND is statistically significant.
`python cli.py regression-check run-baseline-id run-new-id --threshold 0.02`
# VERDICT: REGRESSION DETECTED. The new run is significantly worse.

---

## 🏗️ Architecture & Tech Stack

EvalOS uses an asynchronous architecture to prevent I/O bottlenecks during evaluation pipelines.

*   **Database:** Neon Postgres (via `asyncpg` + `SQLAlchemy 2.0`). Used for relational data AND vector storage (`pgvector`) AND PostgreSQL full-text search (`tsvector`).
*   **Migrations:** Alembic for version-controlled, reproducible database schema changes.
*   **LLM Routing:** OpenRouter (via `AsyncOpenAI`).
*   **Caching:** Upstash Redis (prefixed with `evalos:`) for cached iteration.
*   **Statistics:** `scikit-learn` and `numpy` for Bootstrap CIs and Cohen's Kappa.
*   **Backend API:** FastAPI (exposing the analysis engine as a REST API).
*   **Frontend UI:** Streamlit (interactive dashboard for experiment analysis).
*   **Deployment:** Docker containers deployed to Render.

### Project Structure
Eval-OS/
├── api/                   # FastAPI backend (REST API)
├── cli/                   # Modular Typer commands (run, inspect, compare, label)
├── adapters/              # System interfaces (OpenRouter, RAG, Mock)
├── evaluators/            # Deterministic (Recall, Abstention) & LLM-Judge (Faithfulness, Citation, Quality)
├── analysis/              # Aggregation, Slicing, A/B, Regression, Calibration logic
├── retrieval.py           # Dense, PostgreSQL FTS, and Hybrid (RRF) search engines
├── alembic/               # Database migration scripts
├── cache.py               # Upstash Redis caching layer
├── dashboard.py           # Streamlit frontend UI
├── Dockerfile             # Backend deployment config
├── Dockerfile.dashboard   # Frontend deployment config
└── docs/benchmarks/       # Real, documented benchmark results

---

## 📊 Real Benchmarks & Engineering Logs

We don't just claim EvalOS works; we use it to generate real, documented results.

*   📄 **[Executive Benchmark Summary](BENCHMARKS.md)** - The "At a glance" table and links to deep dives.
*   🔬 **[Deep Dive: 5-Model RAG Benchmark](docs/benchmarks/01_model_comparison.md)** - Proves gpt-4o-mini beats gpt-4o in faithfulness while being 15x cheaper.
*   🐛 **[Engineering Log Vol 1](EVALOS_ENGINEERING_LOG.md)** & **[Vol 2](EVALOS_ENGINEERING_LOG_VOL2.md)** - An honest record of the architecture decisions, async bugs found, and fixes applied during development.
*   📄 **[Project Context & Handoff](PROJECT_CONTEXT.md)** - A comprehensive CTO-level architectural audit and handoff document.

---

## 💡 Why EvalOS?

> *"EvalOS was built to determine whether an AI system actually works, how well it works, why it fails, and what quality/cost/latency trade-offs it makes. Every reported number comes from an actual benchmark."*
