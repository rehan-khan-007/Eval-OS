# 3. Infrastructure, Product & Engineering History

## 3.1 API & Schemas
*   **Backend:** FastAPI (`api/main.py`).
*   **Contracts:** Pydantic schemas (`api/schemas.py`) define strict response models.
*   **Security:** Playground uses `slowapi` rate limiting (5 req/min). 500-char question limit. Sanitized Request ID error logging.

## 3.2 Caching & Cost
*   **Cache:** `cache.py` uses Upstash Redis. Keys are version-aware.
*   **Serialization:** Uses `pickle` (Redis is trusted internal infrastructure).
*   **Cost:** `estimated_cost` is hardcoded in `rag_adapter.py`. Not provider billing.

## 3.3 Provenance
*   **Fingerprint:** `run_fingerprint` is a SHA256 of canonical JSON (`code_sha`, `dataset_version_id`, `system_config_id`, `evaluator_suite`, `dependency_spec`).
*   **Guarantee:** Identifies configuration/provenance, not deterministic execution outputs.
*   **Field Naming:** The database column is named `dependency_lock`, but it is populated with the dependency specification from `requirements.txt`.

## 3.4 Dashboard & Playground
*   **Dashboard:** Streamlit (`dashboard.py`) fetches data from the live API.
*   **Playground:** Interactive BYOK mode. "Save Candidate Case" saves failures to the candidate pool.

## 3.5 Testing
*   **Suite:** At the v1.0.0 freeze point, 26 tests passed across 7 modules.
*   **Mocking:** Evaluator tests mock the OpenAI client and Redis cache.

## 3.6 Engineering Bug History
1.  **Neon Idle Timeouts:** Fix: Short-lived DB sessions.
2.  **MissingGreenlet:** Fix: `selectinload`.
3.  **JSONB Mutation:** Fix: Raw SQL `jsonb_set`.
4.  **BM25 Naming:** Fix: Renamed to `postgres_fts`.
5.  **RRF Identity:** Fix: Use `chunk_id`.
6.  **Evaluator Errors:** Fix: Return `-1.0` and filter in aggregation.
7.  **Typer Async:** Fix: Wrap in `def run(): asyncio.run()`.
8.  **Alembic Autogenerate Destruction:** Fix: Manually edited migration file to preserve FTS.
9.  **RunEngine Gather Crash:** Fix: Try/except in `_process_single_example`.
10. **Benchmark Contamination Risk:** Fix: Playground candidates isolated to separate dataset.
11. **Migration Artifact:** `5768ea...` is a no-op follow-up migration; do not remove/reorder casually.

## 3.7 Architectural Invariants (Must Not Break)
1.  Evaluator failure ≠ system failure (`-1.0` vs `0.0`).
2.  Chunk identity is immutable (`chunk_id`).
3.  DB sessions must not span external API calls.
4.  Cache identity must include evaluator version.
5.  Dataset identity must be deterministic.
6.  Benchmark numbers must carry sample size (N).
7.  Evaluation code must not modify the system-under-test.
8.  (I11) Frozen benchmark integrity.
9.  (I12) Fingerprint = config provenance, not output determinism.
10. (I13) `complete_with_errors` ≠ `complete`.
11. (I14) EvalOS v1 must remain independent of AgentOS/WOE execution internals.

## 3.8 Known Limitations
*   LLM-judge scores are not objective ground truth.
*   N=36 is sufficient for methodology validation, not population-level claims.
*   EvalOS is not a production SaaS (no auth, billing, or multi-tenancy).

## 3.9 EvalOS ↔ AgentOS/WOE Boundary (v2)
*   Future v2: EvalOS will evaluate structured AgentOS/WoE traces. No integration exists in v1. EvalOS must not become an execution dependency.
