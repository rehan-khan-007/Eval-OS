# EvalOS Engineering Log

A rigorous, honest log of the architecture decisions, bugs found, and real results encountered while building EvalOS. This is not a feature list; it is a record of *how* the system was built and verified.

---

## Phase 1: Core Data Model & Schema

**What was built:** The foundational Postgres database schema (via SQLAlchemy 2.0 async) to support datasets, system configurations, execution traces, and metric results.

**Architecture Decision:** We chose an **asynchronous architecture** (`asyncpg` + `SQLAlchemy async`) from day one. Because EvalOS is an I/O heavy application (making hundreds of concurrent LLM API calls), a synchronous engine would have bottlenecked the evaluation pipeline immediately. We also chose to use **Neon Postgres** rather than SQLite to ensure real foreign key constraints and join queries would be available for complex failure analysis later.

**Real bug found and fixed:** Initial schema creation succeeded, but test insertions failed with `can't subtract offset-naive and offset-aware datetimes`. Postgres defaulted to `TIMESTAMP WITHOUT TIME ZONE`, but our Python models were passing UTC-aware datetimes.
**Fix:** Updated `models.py` to explicitly use `DateTime(timezone=True)` for all timestamp columns. Required dropping and recreating all tables via `Base.metadata.drop_all` to apply the schema changes.

---

## Phase 2: Deterministic Evaluation Engine & CLI

**What was built:** The Typer CLI shell, the abstract `BaseEvaluator` and `BaseSystemAdapter` interfaces, concrete deterministic evaluators (`ToolSelectionEvaluator`, `SourceRecallEvaluator`, `LatencyEvaluator`), a `MockSystemAdapter`, and the core `RunEngine` that orchestrates the evaluation loop and writes to Postgres.

**Real bug found and fixed:** The second evaluation run failed immediately with `IntegrityError: duplicate key value violates unique constraint "system_configs_pkey"`. The CLI was trying to insert the `SystemConfig` into the database again, but it already existed from the first run.
**Fix:** Updated `cli.py` to query the database for the `SystemConfig` by ID before attempting an insert. If it exists, it reuses the existing configuration object. This is essential for regression testing, where the same system configuration will be evaluated across multiple dataset versions over time.

**Result:** Successfully processed 30 agent tasks and 36 retrieval QA tasks using the mock system, proving the engine could dynamically apply the correct evaluators based on dataset metadata.

---

## Phase 3, Part 1: Real LLM Integration via OpenRouter

**What was built:** The `OpenRouterAdapter`, which makes real, billed API calls to models via OpenRouter to test tool-selection accuracy.

**Architecture Decision:** We used the official `openai` Python package pointed at the OpenRouter `base_url`. This avoids adding a new HTTP client dependency and ensures compatibility with OpenAI's strict tool-calling schema, which OpenRouter proxies seamlessly.

**Real bug found and fixed:** Initial benchmark runs for Gemini and Claude failed 100% of the time with `404 No endpoints found`.
**Fix:** OpenRouter is very strict about model IDs. We wrote a `check_models.py` script to query OpenRouter's live `/models` endpoint. We discovered the IDs had been updated since the AgentOS project (e.g., `google/gemini-flash-1.5` was now invalid, requiring `google/gemini-3.7-flash`). We updated the CLI to use the exact live IDs.

---

## Phase 3, Part 2: The RAG Reference Workload

**What was built:** The complete document ingestion and retrieval pipeline using `pgvector` inside Neon Postgres.

**Real bug found and fixed:** The `fetch_arxiv_papers.py` script attempted to download SEBI PDFs from arxiv.org because its logic (`if "v" in source`) matched the "v" in SEBI filenames like `sebi_investment_adviser_dos_donts.pdf`. This resulted in harmless 404 errors. 
**Fix:** The SEBI script downloaded them correctly immediately after, so no data was lost. The logic will be refined in future iterations to strictly parse arXiv IDs.

**Result:** 47 real PDFs successfully downloaded, parsed, and embedded (approx. 1,500+ chunks).

---

## Phase 4: Analysis Engine

**What was built:** The `AnalysisEngine` and `inspect-run` CLI command to aggregate raw execution data and calculate final benchmark numbers (average recall, average latency, tool-selection accuracy).

---

## Phase 5: 5-Model Benchmarking & LLM-as-Judge

**What was built:** The `run-benchmark` CLI command to loop through multiple models, and the `LLMJudgeEvaluator` to evaluate faithfulness (grounding) by extracting claims and verifying them against retrieved context.

**Real bug found and fixed:** During the 5-model benchmark, the script crashed at the very end with `InterfaceError: cannot call Transaction.rollback(): the underlying connection is closed`. 
**Root Cause:** The CLI opened a database session, but then held it open while the `RunEngine` ran for 5-10 minutes making API calls. Neon Postgres has an idle timeout and silently dropped the connection. When the script finished and tried to close the session, it crashed.
**Fix:** Updated `RunEngine` to take the `sys_config_id` string instead of the SQLAlchemy object. The CLI now closes its session *immediately* after fetching the examples and config, before running the engine. This enforces the architectural best practice of short-lived sessions.

**Result:** Generated the real 5-model Pareto frontier. Found that `gpt-4o-mini` (96.8% faithfulness, $0.006) actually beat `gpt-4o` (95.9% faithfulness, $0.11) while being 15x cheaper.

---

## Phase 6: Human-in-the-Loop (HITL) Evaluator Reliability

**What was built:** The `label-judgements` and `calculate-agreement` CLI commands. The HITL engine pulls random generated answers, shows them to the user, and asks if the LLM Judge got it right. It then calculates Cohen's Kappa to measure evaluator reliability.

**Real bug found and fixed (MissingGreenlet):** When attempting to print `exec.example.question` in the CLI, the script crashed with `MissingGreenlet: greenlet_spawn has not been called`. 
**Fix:** SQLAlchemy was attempting a "lazy load" (a hidden async database query) to fetch the `EvaluationExample` while we were outside the async database session context. Fixed by adding `.options(selectinload(Execution.example))` to the query to eagerly load the relationship.

**Real bug found and fixed (ConnectionDoesNotExistError):** On the first run of `label-judgements`, the script crashed when the user hit `y` to save their label. 
**Fix:** The CLI was holding the database session open while waiting for human keyboard input. Neon dropped the idle connection. Fixed by fetching the 5 samples, *closing* the database connection, waiting for the user to label all 5 of them in the terminal, and *then* opening a new connection to save them.

**Real bug found and fixed (Kappa Zero-Variance):** The initial Kappa calculation returned `0.0000` despite the human agreeing with the LLM Judge 100% of the time. 
**Fix:** Cohen's Kappa requires variance in the ratings to calculate chance-adjusted agreement. Because the human agreed with the LLM Judge on 100% of the samples (variance = 0), the Kappa formula mathematically collapses to 0.0. Fixed by calculating and printing Raw Agreement alongside Kappa to prevent this statistical edge case from misleading the benchmark.
