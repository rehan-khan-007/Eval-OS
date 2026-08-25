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

---

## Phase 7: CLI Refactor & Retrieval Ablation

**What was built:** Refactored the monolithic `cli.py` into a modular `cli/` directory (`setup_cmds.py`, `run_cmds.py`, etc.). Implemented Dense, BM25, and Hybrid (RRF) retrieval methods in `retrieval.py`.

**Real bug found and fixed (SyntaxError in f-string):** After splitting the CLI, `cli/setup_cmds.py` crashed with `SyntaxError: f-string: single '}' is not allowed`. 
**Fix:** I had accidentally left a typo `dv_id = f"dv-{ds_id}-v1}"` with an extra brace. Removed the stray `}`.

**Real bug found and fixed (RuntimeWarning: coroutine never awaited):** Typer commands crashed because the top-level functions were defined as `async def`, but Typer expects standard `def` functions. 
**Fix:** Wrapped the `async` logic inside standard `def` functions that use `asyncio.run()` internally for each command.

**Real bug found and fixed (ModuleNotFoundError in migrations):** `migrations/add_bm25_support.py` failed with `ModuleNotFoundError: No module named 'database'`. 
**Fix:** The script was inside the `migrations/` folder and couldn't find the parent modules. Fixed by adding `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` to the script.

**Result:** Dense-only (88.9%) beat Hybrid (84.7%). BM25 was so poor (31.9%) that fusing it with Dense via RRF introduced noise and dragged down the performance. This proved "Hybrid is always better" is a myth.

---

## Phase 8: Slice-Based Evaluation

**What was built:** `migrations/update_domains.py` to backfill domain tags based on source document prefixes. Updated `AnalysisEngine` to support slicing metrics by `domain` or `task_type`.

**Result:** Isolated the 88.9% global recall failure to the Quantum domain (84.4% recall). Finance, Entrepreneurship, and Thermal domains all scored 91.7% or higher.

---

## Phase 9: A/B Comparison & Statistical Significance

**What was built:** `compare-runs` command and `check_regression` command in the CLI. Added a 1000-iteration Bootstrap simulation to calculate 95% Confidence Intervals.

**Result:** EvalOS proved that the 4.2% recall difference between Dense and Hybrid was **NOT statistically significant** at this sample size (CI touched 0.0). This prevented us from falsely concluding Dense was definitively better.

---

## Phase 10: Answerability / Abstention

**What was built:** `AbstentionEvaluator` to check if the system correctly says "I don't know" when it lacks context.

**Result:** 80.6% abstention accuracy. EvalOS proved the LLM was overly cautious—it abstained on 6 questions where it actually had the correct context (100% faithfulness, but 0% abstention accuracy for those examples).

---

## Phase 11: Caching & Cost Optimization (Upstash Redis)

**What was built:** `cache.py` module integrating Upstash Redis to cache LLM generations and Embeddings.

**Real bug found and fixed (Redis URL ValueError):** The Redis client crashed with `ValueError: Redis URL must specify one of the following schemes`. 
**Fix:** The `.env` file literally contained `REDIS_URL=YOUR_EXISTING_UPSTASH_REDIS_URL` because the placeholder text was pasted instead of the real URL. Instructed user to replace with the real `rediss://...` string.

**Real bug found and fixed (Cache Miss on Judge):** The second run of the evaluation was still slow and costing money. 
**Root Cause:** I applied the caching logic to `rag_adapter.py` (generation) but forgot to apply it to `evaluators/llm_judge.py` (the judge). The judge was still making 36 real API calls every run.
**Fix:** Added the exact same `get_cached` / `set_cached` logic to `LLMJudgeEvaluator`. The second run then successfully hit the cache for both generation and judging, finishing in seconds for $0.00.

**Architecture Decision:** We shared the Upstash Redis instance with AgentOS to avoid hitting the free tier limit. To prevent key collisions, all EvalOS keys are prefixed with `evalos:` in `cache.py`.

---

## Phase 12: Failure Diagnosis Taxonomy

**What was built:** `diagnose-run` command in the CLI to classify failures into Retrieval, Generation, System, and Negative Control categories.

**Result:** Diagnosed 6 "Generation Failures" where faithfulness was 100% but the LLM abstained unnecessarily. This proved EvalOS can explain *why* a system fails, not just *that* it fails.

---

## Phase 13: Regression Testing

**What was built:** `regression-check` command to compare a new run against a baseline with a configurable threshold.

**Result:** Successfully flagged Hybrid retrieval as a regression against Dense (4.2% recall drop, 1.8% faithfulness drop) with a 1% threshold, proving EvalOS can act as a CI/CD gate.
