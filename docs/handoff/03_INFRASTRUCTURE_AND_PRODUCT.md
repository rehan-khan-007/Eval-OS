# 3. Infrastructure, Product & Engineering History

## 3.1 API & Schemas
*   **Backend:** FastAPI (`api/main.py`).
*   **Contracts:** Pydantic schemas (`api/schemas.py`) define strict response models for all core endpoints (`RunMetricsSchema`, `ExperimentDetailSchema`, `PlaygroundResponseSchema`, `SliceSchema`).
*   **Security:** Playground endpoint uses `slowapi` rate limiting (5 req/min per IP). Questions are capped at 500 characters. Errors return a `request_id` and log only the exception type, never `str(e)`.

## 3.2 Caching & Cost
*   **Cache:** `cache.py` uses Upstash Redis. Keys are version-aware (include `evaluator_name`, `evaluator_version`, `model`, `input`).
*   **Serialization:** Uses `pickle` (Redis is trusted internal infrastructure).
*   **Cost:** `estimated_cost` is hardcoded in `rag_adapter.py` based on token counts. It is not provider billing.

## 3.3 Provenance & Reproducibility
*   **Fingerprint:** `run_fingerprint` is a SHA256 hash of canonical JSON (`sort_keys=True`) containing `code_sha`, `dataset_version_id`, `system_config_id`, `evaluator_suite`, `dependency_spec`.
*   **Guarantee:** The fingerprint guarantees identical configuration provenance, not identical execution outputs due to external API stochasticity.

## 3.4 Dashboard & Playground
*   **Dashboard:** Streamlit (`dashboard.py`) fetches data from the live API and renders experiments, runs, metrics, and failure taxonomies.
*   **Playground:** Interactive BYOK mode. Users paste their OpenRouter key, ask a question, and watch EvalOS retrieve, generate, and evaluate in real-time. "Save Candidate Case" saves interesting failures to the candidate pool.

## 3.5 Testing
*   **Suite:** 26 tests pass across 7 modules (`test_api.py`, `test_cache.py`, `test_evaluators.py`, `test_regression.py`, `test_rrf.py`, `test_run_engine.py`, `test_statistics.py`).
*   **Mocking:** Evaluator tests mock the OpenAI client and Redis cache to isolate parsing logic and prevent state contamination.

## 3.6 Architectural Invariants (Must Not Break)
1.  **Evaluator failure ≠ system failure:** `-1.0` must remain distinct from `0.0`.
2.  **Chunk identity is immutable:** RRF must use `chunk_id`.
3.  **DB sessions must not span external API calls.**
4.  **Cache identity must include evaluator version.**
5.  **Dataset identity must be deterministic:** Example IDs must not rely on Python `hash()`.
6.  **Benchmark numbers must always carry sample size (N).**
7.  **Evaluation code must not modify the system-under-test.**

## 3.7 Engineering Bug History
1.  **Neon Idle Timeouts:** Holding DB sessions open during API calls causes `InterfaceError`. Fix: Short-lived sessions.
2.  **MissingGreenlet:** Lazy loading outside async session. Fix: `selectinload`.
3.  **JSONB Mutation:** SQLAlchemy doesn't detect in-place JSONB dict mutations. Fix: Raw SQL `jsonb_set`.
4.  **BM25 Naming:** `ts_rank` is not BM25. Fix: Renamed to `postgres_fts`.
5.  **RRF Identity:** Using `(source, text)` causes chunk collapse. Fix: Use `chunk_id`.
6.  **Evaluator Errors:** API timeouts returning `0.0` dragged down averages. Fix: Return `-1.0` and filter in aggregation.
7.  **Typer Async:** `async def` commands aren't awaited by Typer. Fix: Wrap in `def run(): asyncio.run()`.
8.  **Alembic Autogenerate Destruction:** Alembic tried to drop `search_vector` because it wasn't in `models.py`. Fix: Manually edited migration file to preserve FTS.
9.  **RunEngine Gather Crash:** One exception in `asyncio.gather` killed the run. Fix: Try/except in `_process_single_example`.

## 3.8 Known Limitations
*   LLM-judge scores are not objective ground truth.
*   N=36 is sufficient for methodology validation, but insufficient for population-level claims.
*   EvalOS is not a production SaaS (no auth, billing, or multi-tenancy).

## 3.9 EvalOS ↔ AgentOS Boundary
*   EvalOS evaluates AgentOS traces. Not implemented yet. EvalOS must not become an AgentOS execution dependency. It should receive structured traces, not run AgentOS internals.
