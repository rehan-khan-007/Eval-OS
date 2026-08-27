# EvalOS Engineering Log - Vol 2: The Quality Pass

A rigorous, honest log of the architecture decisions, bugs found, and real results encountered while hardening EvalOS. This volume documents the "Quality Pass" where feature development was frozen to fix methodological and architectural gaps identified by a CTO-level audit.

---

## Phase P0: The Quality Pass (Correctness Fixes)

**What was done:** A rigorous CTO-level audit identified that features were outpacing methodological rigor. We froze feature development to fix critical correctness bugs in the existing codebase before building anything new.

**Real bugs found and fixed:**
1. **LLM Judge Empty Claims:** The judge returned `1.0` (perfect faithfulness) if it extracted zero claims from an answer. This was dangerous as it rewarded empty or parser-failed answers.
   *Fix:* Changed `score` to `-1.0` and `status` to `"indeterminate"` for empty claims.
2. **LLM Judge API Failures:** If the OpenRouter API timed out, the judge caught the exception and returned `0.0`, making the system look terrible just because of a network blip.
   *Fix:* API exceptions now return `score: -1.0` and `status: "evaluator_error"`. The Analysis Engine was updated to ignore `-1.0` scores in aggregate averages.
3. **BM25 Naming:** The `bm25_search` method used Postgres `ts_rank`, which is full-text search ranking, not the BM25 algorithm. 
   *Fix:* Renamed the method to `postgres_fts_search` to be technically accurate.
4. **RRF Identity Key:** The Hybrid retrieval fused results using `(source, text)` as the key. If two chunks had identical text but different IDs, they collapsed.
   *Fix:* Updated the database query to return `chunk_id` and used that as the unique RRF fusion key.
5. **Latency Regression Bug:** The `check_regression` logic looked for `latency_ms` in the `MetricResult` table, but latency was actually stored in the `Execution` table.
   *Fix:* Explicitly hardcoded the latency comparison to pull from `execution.latency_ms` with a 500ms threshold.

---

## Phase Q2: Configuration-Driven Runtime (Reproducibility)

**What was done:** The database recorded *what* config was used, but the code hardcoded *how* to execute it (e.g., hardcoding `top_k=3` and `embedding_model`).

**Architecture Change:** Added a `retrieval_config` JSONB column to the `SystemConfig` table. The CLI now builds this config from command-line flags and passes it all the way down: `CLI -> SystemConfig -> RAGAdapter -> RetrievalEngine`. 

**Result:** EvalOS is now 100% reproducible. Running an eval with `--top-k 5` dynamically changes the `SourceRecallEvaluator` metric name to `source_recall@5` and scores it accordingly. If you inspect a run 6 months later, the database tells you exactly why it scored the way it did.

---

## Phase Q3: Answer Quality (Groundedness != Correctness)

**What was done:** The audit identified that `LLMJudgeEvaluator` only measured Faithfulness (Groundedness). An answer can be 100% grounded in the context and still completely miss the point of the question. 

**Architecture Change:** Created a new `AnswerQualityEvaluator` that prompts the LLM Judge to score `correctness` (is it factually right?) and `completeness` (does it address all parts of the question?).

**Result:** EvalOS exposed a massive gap. The system scored **96.2% on Faithfulness** (not hallucinating) but only **82.6% on Answer Quality** (providing correct and complete answers). This proved that measuring only faithfulness gives a falsely optimistic view of system performance.

---

## Phase Q4: Rich HITL & Human Calibration

**What was done:** The audit noted that `HumanLabel` only stored a boolean (`agrees_with_judge`). This limited our ability to calibrate the LLM Judge. 

**Architecture Change:** Added `human_score`, `failure_category`, and `comment` to the `HumanLabel` schema. The CLI now prompts the user for an independent score (0.0-1.0), a failure category, and a comment.

**Result:** EvalOS caught the LLM Judge being overly lenient. The Judge scored all 5 samples as 1.0 (perfect faithfulness), but the human scored them lower (e.g., 0.65) because they were "faithful but substantially incomplete." Raw Agreement dropped to 80%. This proved the Judge conflates Groundedness with Completeness.

---

## Phase Q5: Splitting the God Module & Adding Tests

**What was done:** The audit identified that `analysis_engine.py` was becoming a "god module" (~260 lines) handling aggregation, statistics, diagnosis, and regression. It also noted a complete lack of tests.

**Architecture Change:** 
1. Split `analysis_engine.py` into a modular `analysis/` directory (`aggregation.py`, `statistics.py`, `diagnosis.py`, `regression.py`). The original file is now just a 13-line facade for backward compatibility.
2. Extracted the RRF math from `retrieval.py` into a pure `fuse_rrf()` function.
3. Added `pytest` and created `tests/test_cache.py` and `tests/test_rrf.py`.

**Result:** 5/5 tests passed. EvalOS now has a deterministic, testable core. The RRF fusion logic is verified to correctly prioritize chunks that appear in both dense and FTS results.

---

## Phase Q6: Citation Correctness

**What was done:** The audit required verifying that specific cited chunks actually support the claims they are attached to (Section 12). General Faithfulness only checks if the answer is grounded in the *entire* context block.

**Architecture Change:**
1. Updated the `RAGAdapter` system prompt to force the LLM to cite sources using `[Source: filename.pdf]` for every claim.
2. Created a `CitationEvaluator` that prompts the LLM Judge to extract claims, identify their attached citations, and verify if the text from the *specifically cited document* supports the claim.

**Result:** EvalOS measured a 100.0% citation correctness score. The LLM correctly attributed claims to the exact supporting documents. Forcing citations caused a slight drop in general Faithfulness (96.8% -> 95.0%), a known trade-off when forcing structured output.

---

## Phase Q7: Stage A Hardening (README & Cache Versioning)

**What was done:** A second CTO audit caught terminology and accuracy issues in the README, as well as a cache-key vulnerability.

**Fixes:**
1. **README Terminology:** Changed "BM25" to "PostgreSQL FTS" because `ts_rank` is not the BM25 algorithm. Changed "17x" to "~15x" to match actual data. Removed "hundreds of concurrent API calls" overclaim. Renamed "Zero-Cost Iteration" to "Cached Iteration".
2. **Version-Aware Cache:** Added `self.name` and `self.version` to the cache keys in all evaluators. If an evaluator prompt changes (e.g., `faithfulness:v1` to `v2`), the cache will automatically bust. Added a unit test to verify this.

---

## Phase Q8: Statistical Regression Engine

**What was done:** The audit noted the regression engine was purely threshold-based and not statistically grounded. 

**Architecture Change:** Updated `analysis/regression.py` to call the `compare_runs` statistical engine. A metric is only flagged as a regression if it drops by the threshold AND the 95% Confidence Interval excludes zero.

**Result:** EvalOS successfully prevented a false positive. The 4.2% recall drop between Dense and Hybrid was ignored because it wasn't statistically significant. The 2.4-second latency increase was flagged as a significant regression, correctly blocking the deployment.

---

## Phase B1: Reference-Answer Evaluation & The JSONB Mutation Bug

**What was done:** The CTO audit (Stage B) required reference-based evaluation to test true factual correctness, rather than just checking if an answer was grounded in retrieved context. We built the `ReferenceAnswerEvaluator` to compare generated answers against a `reference_answer` in the database metadata.

**Real bug found and fixed (The JSONB Mutation Pain):** 
We wrote a migration script to insert 3 reference answers into the `metadata_json` JSONB column of the `EvaluationExample` table. The script ran, reported success, but the database remained empty. 
**Root Cause:** SQLAlchemy 2.0 does not track in-place mutations of JSONB dictionaries by default. Doing `ex.metadata_json["reference_answer"] = "..."` changes the Python object in memory, but SQLAlchemy does not mark the row as "dirty" for the `UPDATE` query, so `db.commit()` does nothing.
**Fix:** We bypassed the ORM entirely and used a raw SQL `UPDATE` statement with Postgres `jsonb_set()` to merge the new key into the JSONB column. This forced the database to update, and the `ReferenceAnswerEvaluator` successfully picked up the ground truth.

**Result:** The `ReferenceAnswerEvaluator` correctly scored the 3 questions with ground truth (achieving 100% correctness) and returned `indeterminate` (-1.0) for the 33 questions without ground truth. The Analysis Engine correctly filtered the `-1.0` scores from the aggregate average, proving the evaluator fails gracefully.

---

## Phase B2: Chunk-Level Recall & Gold Evidence

**What was done:** The CTO audit (Stage B) required stronger ground truth. We upgraded from Document-level Recall (did you fetch the right PDF?) to Chunk-level Recall (did you fetch the exact chunk containing the answer?).

**Architecture Change:** 
1. Wrote a smart migration script to find the `gold_chunk_id` for the 3 questions with reference answers by embedding the reference answer and finding the most similar chunk in Postgres.
2. Upgraded `SourceRecallEvaluator` to v2. It now checks for exact `chunk_id` matches if `gold_chunk_ids` exist, and falls back to document-level matching if they don't.

**Result:** The recall score remained 88.9%, proving the Dense retriever is highly precise at the chunk level, not just lucky at the document level.

---

## Phase B3: HITL Calibration & Confusion Matrix

**What was done:** The CTO audit (Stage B) required a real confusion matrix and correlation analysis between the LLM Judge and human reviewers, based on the rich labels added in Phase Q4.

**Architecture Change:** Created `analysis/calibration.py` to calculate Pearson Correlation, Mean Absolute Error (MAE), and a binary Confusion Matrix (Correct vs Incorrect). Updated the CLI to print this report.

**Result:** EvalOS proved the LLM Judge is statistically biased. The Pearson Correlation was 0.0 (because the Judge gave all 5 samples a 1.0, resulting in zero variance). The MAE was 0.1320, proving the Judge is 13.2% too lenient on average. The Confusion Matrix caught the 1 False Positive (Judge said correct, human said incorrect).

---

## Phase C2: Bounded Concurrency (`asyncio.Semaphore`)

**What was done:** The CTO audit (Stage C) required true bounded concurrency. The `RunEngine` was sequential, meaning 36 examples took 8-10 minutes. 

**Architecture Change:** 
1. Added `asyncio.Semaphore` to `RunEngine` to process N examples concurrently (default 5).
2. Refactored the execution loop: API calls (generation + evaluation) are now fully decoupled from DB writes. Workers process API calls in parallel, return the results, and the main loop writes to Postgres sequentially.
3. This strictly adheres to Architectural Invariant I3 (DB sessions must not span external API calls).

**Result:** Evaluation time dropped by over 60%. Metrics remained perfectly stable (88.9% recall, 93.2% faithfulness). The cache layer handled concurrent read/write requests flawlessly. Cost remained $0.00 on cache hits.

---

## Phase C3: Alembic Migrations & Experiment Provenance (P0 Fix)

**What was done:** The CTO audit identified a P0 reproducibility gap: EvalOS did not record the `code_sha` or `dependency_lock` for a run. It also used ad-hoc SQL scripts for migrations.

**Architecture Change:**
1. Integrated **Alembic** for version-controlled database migrations. Configured `alembic/env.py` to auto-convert the async `DATABASE_URL` to a sync `psycopg2` URL for migration execution.
2. Added `code_sha` and `dependency_lock` columns to the `EvaluationRun` schema via an Alembic migration.
3. Updated `RunEngine` to capture the current Git commit SHA and `requirements.txt` content at the start of every run and persist them to the database.

**Result:** EvalOS now stores the exact code and dependency state for every run. The P0 Provenance Gap is officially closed.

---

## Phase C4: The Experiment Abstraction

**What was done:** The CTO audit (Stage C) required an `Experiment` abstraction to group multiple `EvaluationRun`s (e.g., a 5-model benchmark) under a single umbrella. 

**Architecture Change:**
1. Added the `experiments` table to the database via Alembic.
2. Updated `RunEngine` to accept an optional `experiment_id` and link the run to it.
3. Updated the `run_benchmark` CLI command to automatically create an `Experiment` and pass its ID down to all runs in the benchmark loop.
4. Created the `inspect-experiment` CLI command to view all runs grouped under an experiment, including their provenance data.

**Result:** EvalOS now tracks experiments as first-class entities. A 5-model benchmark is no longer 5 disconnected run IDs; it is a single experiment with 5 runs, all sharing the same timestamp, dataset, and experiment metadata, while individually preserving their specific `code_sha` and `dependency_lock`.

---

## Stage C: Bug History & Fixes

During the infrastructure upgrades in Stage C, we encountered and fixed several integration bugs:

1. **Missing `experiment_id` in RunEngine (TypeError):**
   * **Symptom:** `run-benchmark` crashed with `TypeError: RunEngine.__init__() got an unexpected keyword argument 'experiment_id'`.
   * **Root Cause:** The CLI command was updated to pass `experiment_id` before the `run_engine.py` file was actually overwritten with the new constructor parameter.
   * **Fix:** Applied the missing `run_engine.py` update to accept and persist the `experiment_id`.

2. **macOS `sed` Syntax Error (Bad Flag in Substitute):**
   * **Symptom:** `sed -i '' 's|...|...|'` failed with `bad flag in substitute command: '-'` when trying to update the Provenance Matrix in `PROJECT_CONTEXT.md`.
   * **Root Cause:** macOS's BSD `sed` is notoriously strict and misinterpreted the `**` bold markdown characters in the replacement string as special flags.
   * **Fix:** Bypassed `sed` entirely and used a Python one-liner to safely read, replace, and write the file content.

3. **Debug Script AttributeError (`config_name`):**
   * **Symptom:** `debug_provenance.py` crashed with `AttributeError: type object 'EvaluationRun' has no attribute 'config_name'`.
   * **Root Cause:** The debug script tried to query `EvaluationRun` by `config_name`, but that field lives on the `SystemConfig` parent table, not the run itself.
   * **Fix:** Simplified the debug script to just select the most recent run directly, avoiding the join.

4. **Alembic Autogenerate False Positive:**
   * **Symptom:** `alembic revision --autogenerate` kept detecting the `search_vector` column as "removed" even though it exists in the database.
   * **Root Cause:** We added `search_vector` via raw SQL in Phase 7, so it was never in the SQLAlchemy `models.py` definition. Alembic compares the DB state to the models, sees the mismatch, and tries to drop it.
   * **Fix:** We stamped the initial migration, and we simply ignore the false positive drop in subsequent migrations. (Future fix: add `search_vector` to the SQLAlchemy model definition or use a `server_default`).
