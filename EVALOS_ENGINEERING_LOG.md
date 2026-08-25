# EvalOS Engineering Log

A rigorous, honest log of the architecture decisions, bugs found, and real results encountered while building EvalOS. This is not a feature list; it is a record of *how* the system was built and verified.

---

## Phase 1: Core Data Model & Schema

**What was built:** The foundational Postgres database schema (via SQLAlchemy 2.0 async) to support datasets, system configurations, execution traces, and metric results.

**Architecture Decision:** We chose an **asynchronous architecture** (`asyncpg` + `SQLAlchemy async`) from day one. Because EvalOS is an I/O heavy application (making hundreds of concurrent LLM API calls), a synchronous engine would have bottlenecked the evaluation pipeline immediately. We also chose to use **Neon Postgres** rather than SQLite to ensure real foreign key constraints and join queries would be available for complex failure analysis later (e.g., "show every failing example in the finance domain across every run").

**Real bug found and fixed:** Initial schema creation succeeded, but test insertions failed with `can't subtract offset-naive and offset-aware datetimes`. Postgres defaulted to `TIMESTAMP WITHOUT TIME ZONE`, but our Python models were passing UTC-aware datetimes.
**Fix:** Updated `models.py` to explicitly use `DateTime(timezone=True)` for all timestamp columns. Required dropping and recreating all tables via `Base.metadata.drop_all` to apply the schema changes.

---

## Phase 2: Deterministic Evaluation Engine & CLI

**What was built:** The Typer CLI shell, the abstract `BaseEvaluator` and `BaseSystemAdapter` interfaces, concrete deterministic evaluators (`ToolSelectionEvaluator`, `SourceRecallEvaluator`, `LatencyEvaluator`), a `MockSystemAdapter`, and the core `RunEngine` that orchestrates the evaluation loop and writes to Postgres.

**Real bug found and fixed:** The second evaluation run failed immediately with `IntegrityError: duplicate key value violates unique constraint "system_configs_pkey"`. The CLI was trying to insert the `SystemConfig` (named "MockAgentRAG") into the database again, but it already existed from the first run.
**Fix:** Updated `cli.py` to query the database for the `SystemConfig` by ID before attempting an insert. If it exists, it reuses the existing configuration object. This is essential for regression testing, where the same system configuration will be evaluated across multiple dataset versions over time.

**Result:** Successfully processed 30 agent tasks and 36 retrieval QA tasks using the mock system, proving the engine could dynamically apply the correct evaluators based on dataset metadata.

---

## Phase 3, Part 1: Real LLM Integration via OpenRouter

**What was built:** The `OpenRouterAdapter`, which makes real, billed API calls to models via OpenRouter to test tool-selection accuracy. It defines dummy tools (`retrieve`, `calculator`, `web_search`) and asks the LLM which to use.

**Architecture Decision:** We used the official `openai` Python package pointed at the OpenRouter `base_url`. This avoids adding a new HTTP client dependency and ensures compatibility with OpenAI's strict tool-calling schema, which OpenRouter proxies seamlessly.

**Result:** 30 real API calls to `gpt-4o-mini` (Run ID: `run-eb131b5b`). Successfully measured real latency and token usage, and evaluated tool-selection accuracy without a single error.

---

## Phase 3, Part 2: The RAG Reference Workload

**What was built:** The complete document ingestion and retrieval pipeline.
1. **Schema Update:** Added the `pgvector` extension to Postgres and created a `DocumentChunk` table with a `Vector(1536)` column.
2. **Document Fetching:** Wrote `fetch_arxiv_papers.py` and `fetch_sebi_papers.py` to automatically download the real reference documents.
3. **Ingestion Pipeline:** Wrote `ingest_documents.py` to parse PDFs (`pypdf`), chunk them (1000 chars, 100 overlap), embed them via OpenRouter (`text-embedding-3-small`), and save them to Postgres.
4. **RAG Adapter:** Wrote `RAGAdapter` which embeds a query, performs cosine similarity search in Postgres, and passes the context to the LLM to generate an answer.

**Real bug found and fixed:** The `fetch_arxiv_papers.py` script attempted to download SEBI PDFs from arxiv.org because its logic (`if "v" in source`) matched the "v" in SEBI filenames like `sebi_investment_adviser_dos_donts.pdf`. This resulted in harmless 404 errors. The SEBI script downloaded them correctly immediately after, so no data was lost. The logic will be refined in future iterations to strictly parse arXiv IDs.

**Result:** 
- 47 real PDFs successfully downloaded (19 arXiv, 28 SEBI).
- 47 PDFs successfully parsed and embedded (approx. 1,500+ chunks).
- Real RAG evaluation executed successfully against `gpt-4o-mini` (Run ID: `run-6cfeecf4`). The system successfully retrieved context, generated answers, and scored source-level recall@3.

---

## Next Steps

- **Analysis Engine:** Build the CLI commands to query the database and aggregate the results from `run-6cfeecf4` to calculate overall recall, latency distributions, and per-example failure analysis.
- **Model-Based Evaluators:** Implement the `LLMJudgeEvaluator` and claim-level grounding analysis to evaluate the quality of the answers generated by the RAG pipeline.
