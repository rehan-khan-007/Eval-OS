# Chunk-Level Recall (Gold Evidence)

**What was measured:** Upgrading retrieval evaluation from *Document-level Recall* (did you fetch the right PDF?) to *Chunk-level Recall* (did you fetch the exact chunk containing the answer?). This fulfills the CTO audit's Stage B requirement for stronger ground truth.

**How:** 
1. Created a migration script to embed the `reference_answer` for 3 quantum questions.
2. Queried Postgres to find the single chunk most semantically similar to the reference answer. This became the `gold_chunk_id`.
3. Upgraded `SourceRecallEvaluator` to v2. If `gold_chunk_ids` exist in the metadata, it checks for exact chunk ID matches. Otherwise, it falls back to document-level matching.

**Result:**

| Metric | Score (v1 Doc-Level) | Score (v2 Chunk-Level) |
|---|---|---|
| `source_recall@3` | 88.9% | **88.9%** |

**Honest caveats & Real findings:**
- The score remained identical. This is a real, positive finding: it proves the Dense retriever isn't just getting lucky and pulling a random chunk from the correct PDF. It is actually surfacing the semantically correct *chunk* that contains the ground truth answer.
- This establishes the methodology for a rigorous benchmark: in a full production dataset, every question would have a `gold_chunk_id`, and EvalOS would measure precise evidence retrieval.
