# EvalOS — Master Project Context & Engineering Handoff (v1.0.0)

This directory serves as the comprehensive engineering memory layer for EvalOS. It is designed to be read by a future senior engineer or AI coding model before touching the codebase.

## Document Index

### [01_CORE_ARCHITECTURE_AND_DATA.md](01_CORE_ARCHITECTURE_AND_DATA.md)
Covers the foundational system design, database schema, async patterns, system adapters, and the RAG retrieval pipeline.
*   Database models, JSONB mutation tracking, Alembic migrations.
*   `asyncpg` vs `psycopg2` driver usage.
*   RRF fusion math, `pgvector` vs `tsvector` configuration.
*   Adapter contracts and BYOK (Bring Your Own Key) architecture.

### [02_EVALUATION_AND_ANALYSIS.md](02_EVALUATION_AND_ANALYSIS.md)
Covers the evaluator ecosystem, the concurrent RunEngine, statistical methodology, and failure diagnosis.
*   Evaluator score semantics (`-1.0`, `0.0`, `1.0`, `status`).
*   LLM-as-Judge claim extraction and citation verification.
*   Bounded concurrency (`asyncio.Semaphore`) and exception isolation.
*   Paired bootstrap CIs, metric directions, `INCONCLUSIVE` regression states.
*   HITL calibration (Pearson, MAE, Confusion Matrix).

### [03_INFRASTRUCTURE_AND_PRODUCT.md](03_INFRASTRUCTURE_AND_PRODUCT.md)
Covers the API, CLI, Streamlit dashboard, security hardening, testing, and the complete engineering bug history.
*   FastAPI Pydantic schemas and `slowapi` rate limiting.
*   Run fingerprints, code SHA, and dependency provenance.
*   The "Overly Cautious LLM" bug and the "BM25 vs FTS" naming bug.
*   Architectural invariants (I1-I10) that must not be broken.
*   Known limitations and scientific caveats.

## Quick Start for the Next Engineer
1. Read this master index.
2. Read `01_CORE_ARCHITECTURE_AND_DATA.md` to understand the database and adapters.
3. Read `02_EVALUATION_AND_ANALYSIS.md` to understand how scores are generated and analyzed.
4. Read `03_INFRASTRUCTURE_AND_PRODUCT.md` to understand the API, security, and history.
5. **Do not interpret "implemented" as "validated".**
6. **EvalOS v1 is frozen. Do not add features. Focus on correctness or v2 integration.**
