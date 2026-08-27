# EvalOS — Master Project Context & Engineering Handoff (v1.0.0)

## 1. RELEASE STATUS
EvalOS v1.0.0 is officially **FROZEN**. 
*   **Allowed:** Bug fixes (correctness/security), documentation updates.
*   **Not Allowed:** New v1 features. If a requested change is not necessary to preserve v1 correctness, it belongs in v2 unless explicitly authorized.
*   **v1 Scope:** Standalone evaluation infrastructure for AI/RAG systems.
*   **v2 Scope:** AgentOS/WoE trace integration, agent trajectory evaluation, OpenTelemetry.

## 2. EXECUTIVE SUMMARY
EvalOS is an advanced research prototype and early evaluation infrastructure for AI/RAG systems. It provides a controlled benchmark, configurable evaluation suites, statistical comparison, failure diagnosis, regression gates, and an interactive playground. It can evaluate RAG without being coupled to the system being evaluated.

## 3. ARCHITECTURE & TOPOLOGY
*   **External Infrastructure:**
    *   **Neon Postgres:** Relational data, `pgvector` (dense), `tsvector` (FTS).
    *   **Upstash Redis:** LLM/Embedding caching (version-aware keys).
    *   **OpenRouter:** LLM inference (generation + judge).
    *   **Render:** Dockerized deployment for FastAPI (API) and Streamlit (Dashboard).
*   **System Diagram:**
    ```text
    AI System (RAG) -> EvalOS -> (Quality, Cost, Latency) -> Diagnosis -> Regression Detection -> HITL Calibration -> CI/CD-Ready Gate.
    ```

## 4. DATA & BENCHMARK
*   **Dataset:** `dv-ds-retrieval_qa-v1` (36 questions, 4 domains). This dataset is the basis for the published v1 benchmark numbers.
*   **Corpus Provenance:** 47 real PDFs (19 arXiv, 28 SEBI). Tracked in Git. Source URL/document retrieval metadata are not fully persisted in the database; document-level cryptographic provenance is a future improvement.
*   **Contamination Rules:** Playground candidates are saved to a separate `dv-playground-candidates-v1` dataset. The core benchmark is immutable.

## 5. CRITICAL CONTRACTS & INVARIANTS
*   **Evaluator Score:** `1.0` = success, `0.0` = failure, `-1.0` = indeterminate/evaluator failure. `status` field is authoritative.
*   **Chunk Identity:** RRF must use `chunk_id`, not `(source, text)`.
*   **DB Sessions:** Must not span external API calls (Neon will drop them).
*   **Cache Identity:** Must include evaluator version.
*   **Dataset Identity:** Must use `hashlib.sha256`, not Python `hash()`.
*   **Benchmark Immutability (I11):** Never modify v1 benchmark examples after v1 release. Create a new dataset version for changes.
*   **Error States (I13):** `complete_with_errors` must never be treated as equivalent to `complete`.

## 6. PROVENANCE
*   `EvaluationRun` stores `code_sha`, `dependency_lock` (currently populated from `requirements.txt` as a dependency specification, not a fully resolved lockfile), and `run_fingerprint`.
*   `run_fingerprint` is a SHA256 of canonical JSON config. It identifies configuration/provenance identity; it does **not** guarantee bit-for-bit deterministic outputs due to external API stochasticity.

## 7. SCIENTIFIC METHODOLOGY
*   **Statistics:** Paired bootstrap CIs (1000 iters, seed=42). If 95% CI excludes zero, `is_significant` is True.
*   **Regression:** Metric-aware directions (`higher_is_better` vs `lower_is_better`). Verdicts: `PASS`, `REGRESSION`, `IMPROVEMENT`, `INCONCLUSIVE` (if CI touches zero).
*   **HITL:** Pearson, MAE, Confusion Matrix. N=5 pilot proves the pipeline, not global judge validity.

## 8. SECURITY & TESTING
*   **Security:** Playground uses `slowapi` (5/min), 500-char limits, sanitized error logging with Request IDs.
*   **Testing:** At the v1.0.0 freeze point, 26 tests passed across 7 modules. 

## 9. KNOWN LIMITATIONS
*   LLM-judge scores are not objective ground truth.
*   High retrieval recall does not imply answer correctness.
*   Non-significance does not prove equivalence.
*   Estimated cost is not provider billing.

## 10. V1 -> V2 BOUNDARY
*   **AgentOS:** Future v2: EvalOS will evaluate structured AgentOS traces. No AgentOS integration exists in v1. EvalOS must not become an AgentOS execution dependency.
*   **WOE:** Future v2: WOE produces workflow execution traces; EvalOS consumes those traces. EvalOS must not own workflow execution.

## 11. AI CONTRIBUTOR GUARDRAILS (DO NOT DO THIS)
*   DO NOT add v1 features.
*   DO NOT modify the frozen benchmark (`dv-ds-retrieval_qa-v1`).
*   DO NOT change evaluator `-1.0` semantics casually.
*   DO NOT rename `postgres_fts` to `bm25`.
*   DO NOT make EvalOS an AgentOS runtime dependency.
*   DO NOT replace RRF `chunk_id` identity.
*   DO NOT hold DB sessions across external API calls.
*   DO NOT claim statistical equivalence from non-significant results.

## 12. LOCAL DEVELOPMENT / DEPLOYMENT
*   **Environment Variables:** `DATABASE_URL` (postgresql+asyncpg), `OPENROUTER_API_KEY`, `REDIS_URL` (rediss://). Secrets must never be committed.
*   **Quickstart:** `pip install -r requirements.txt` -> `alembic upgrade head` -> `pytest tests/` -> `python cli.py run-eval` -> `uvicorn api.main:app` -> `streamlit run dashboard.py`.

## 13. REPOSITORY REFERENCE MAP
*   **Database:** `database.py`, `models.py`
*   **Retrieval:** `retrieval.py` (`fuse_rrf`)
*   **Evaluators:** `evaluators/` (deterministic.py, llm_judge.py, answer_quality.py, citation.py, reference_answer.py)
*   **Engine:** `run_engine.py`
*   **Analysis:** `analysis/` (statistics.py, regression.py, diagnosis.py, calibration.py)
*   **API:** `api/main.py`, `api/schemas.py`
*   **CLI:** `cli/main.py`
