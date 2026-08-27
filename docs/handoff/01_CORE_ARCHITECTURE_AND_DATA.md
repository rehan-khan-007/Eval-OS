# 1. Core Architecture & Data Model

## 1.1 Database Engine & Async Patterns
*   **Engine:** SQLAlchemy 2.0 async with `asyncpg` for the main application.
*   **Migrations:** Alembic uses a synchronous `psycopg2` engine to execute DDL.
*   **Session Lifetime:** DB sessions must be short-lived. Never span external API calls (Neon will drop idle connections, causing `InterfaceError`).
*   **JSONB Mutations:** SQLAlchemy does not detect in-place mutations of JSONB dicts. You must re-assign the entire dictionary or use raw SQL `jsonb_set`.

## 1.2 Dataset & Versioning Architecture
*   **Identity:** Example IDs use `hashlib.sha256(question.encode()).hexdigest()[:16]` for deterministic reproducibility.
*   **Immutability (I11):** The core benchmark (`dv-ds-retrieval_qa-v1`) is frozen and must not be mutated. Create new versions for any changes.
*   **Playground Candidates:** Saved to `dv-playground-candidates-v1` to prevent benchmark contamination.
*   **Corpus Provenance:** 47 real PDFs (19 arXiv, 28 SEBI) are tracked in Git. Source URL/document hashes are not fully persisted in the database (Future v2 improvement).

## 1.3 Ground Truth Hierarchy
1.  **Expected source (N=36):** Document-level annotations.
2.  **Reference answer (N=3):** Human-authored ground truth.
3.  **Semantic reference chunk (N=3):** Derived semantic labeling (chunk most similar to reference answer).
4.  **Human score (N=5):** HITL calibration labels.

## 1.4 System Adapter Architecture
*   **Contract:** `BaseSystemAdapter` -> `MockSystemAdapter`, `OpenRouterAdapter`, `RAGAdapter`.
*   **Return Dict:** `answer`, `retrieved_evidence`, `latency_ms`, `cost`, `tokens_in`, `tokens_out`, `error`.
*   **BYOK:** Adapters accept an optional `api_key` for the Playground.
*   **Isolation:** Evaluation code must not modify the system-under-test.

## 1.5 Retrieval / RAG Architecture
*   **Engine:** `RetrievalEngine` supports `dense` (pgvector), `postgres_fts` (tsvector), and `hybrid` (RRF).
*   **Naming:** Postgres FTS uses `ts_rank`, not BM25. It is correctly named `postgres_fts`.
*   **RRF Identity:** `fuse_rrf()` uses `chunk_id` as the unique fusion key.
*   **Config-Driven:** `top_k` and `embedding_model` are passed from `SystemConfig` down to the adapter.
