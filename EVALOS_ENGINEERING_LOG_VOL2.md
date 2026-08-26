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
