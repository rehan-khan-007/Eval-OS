# 1. Core Architecture & Data Model

## 1.1 Database Engine & Async Patterns
*   **Engine:** EvalOS uses SQLAlchemy 2.0 async with `asyncpg` for the main application (`database.py`).
*   **Migrations:** Alembic is used for schema migrations. Alembic uses a synchronous `psycopg2` engine to execute DDL (`alembic/env.py`).
*   **Session Lifetime:** Database sessions (`AsyncSessionLocal`) must be short-lived. They must never span external API calls (Neon will drop idle connections, causing `InterfaceError`).
*   **JSONB Mutations:** SQLAlchemy does not detect in-place mutations of JSONB dictionaries. If you need to update a key inside a JSONB column, you must re-assign the entire dictionary or use raw SQL `jsonb_set`.

## 1.2 Dataset & Versioning Architecture
*   **Identity:** Example IDs are generated using `hashlib.sha256(question.encode()).hexdigest()[:16]` to ensure deterministic reproducibility across Python processes.
*   **DatasetVersion:** Versions are intended to be immutable. The core benchmark (`dv-ds-retrieval_qa-v1`) must not be mutated.
*   **Playground Candidates:** The Playground saves interesting failures to a separate `dv-playground-candidates-v1` dataset. This prevents benchmark contamination while building a pool of real-world failure cases for future human review.
*   **Document Corpus:** 47 real PDFs (19 arXiv, 28 SEBI) are tracked in Git under `data/docs/papers/`. `document_hash` and `source_uri` are not currently persisted in the database (Future v2 improvement).

## 1.3 Ground Truth Hierarchy
1.  **Expected source (N=36):** Document-level annotations.
2.  **Reference answer (N=3):** Human-authored ground truth for quantum physics questions.
3.  **Gold chunk (N=3):** Derived semantic labeling (chunk most similar to reference answer).
4.  **Human score (N=5):** HITL calibration labels (`human_score`, `failure_category`, `comment`).

## 1.4 System Adapter Architecture
*   **Contract:** `BaseSystemAdapter` -> `MockSystemAdapter`, `OpenRouterAdapter`, `RAGAdapter`.
*   **Return Dict:** The adapter returns `answer`, `retrieved_evidence`, `latency_ms`, `cost`, `tokens_in`, `tokens_out`, `error`.
*   **BYOK:** Adapters accept an optional `api_key` parameter, allowing the Playground to use user-provided keys without touching the server's default keys.
*   **Isolation:** Evaluation code must not modify the system-under-test.

## 1.5 Retrieval / RAG Architecture
*   **Engine:** `RetrievalEngine` supports `dense` (pgvector), `postgres_fts` (tsvector), and `hybrid` (RRF).
*   **Naming:** The Postgres FTS implementation uses `ts_rank`, not the BM25 algorithm. It is correctly named `postgres_fts` to avoid false claims.
*   **RRF Identity:** The `fuse_rrf()` pure function in `retrieval.py` uses `chunk_id` as the unique fusion key, not `(source, text)`, to prevent identical-text chunk collapse.
*   **Config-Driven:** `top_k` and `embedding_model` are passed from `SystemConfig` down to the adapter, ensuring runs are reproducible.
