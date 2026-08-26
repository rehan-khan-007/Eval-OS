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
