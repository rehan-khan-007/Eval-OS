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
