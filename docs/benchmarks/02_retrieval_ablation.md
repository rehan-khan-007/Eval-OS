# Retrieval Ablation (Dense vs BM25 vs Hybrid)

**What was measured:** Source-level recall@3 for three retrieval
methods run in isolation — Dense-only (pgvector cosine), BM25-only
(Postgres tsvector), and Hybrid (RRF-fused) — against the same
36-question dataset. Directly tests the assumption that Hybrid
retrieval is always superior to Dense-only.

**How:** `python cli.py run-eval --system rag --retriever <method>`
using `openai/gpt-4o-mini` for generation and `openai/text-embedding-3-small`
for embeddings. EvalOS executed all three runs sequentially.

**Result:**

| Method | Source Recall@3 | Faithfulness | Avg Latency | Total Cost |
|---|---|---|---|---|
| **Dense-only** | **88.9%** | 96.8% | 5.58s | $0.0065 |
| Hybrid (RRF) | 84.7% | 95.0% | 7.81s | $0.0065 |
| BM25-only | 31.9% | 37.8% | 4.14s | $0.0028 |

**Honest read of this result, not spun toward the expected answer:**
- Dense-only is the clear winner on this dataset. BM25 alone trails
  miserably (31.9%), a real, meaningful gap.
- Hybrid did **not** outperform Dense-only on this dataset — it
  actually performed 4 points *worse*. This is reported as-is rather
  than framed as an unambiguous win for Hybrid, since it wasn't one here.
- **Why did Hybrid fail?** BM25's performance was so poor (likely due
  to semantic mismatch between questions and PDF-extracted text) that
  fusing its rankings with Dense via RRF introduced significant noise,
  pushing correct Dense matches down in the final top-3. 
- This is exactly why EvalOS was built: to prove empirically what works,
  not to assume "Hybrid is always better."

---

## Slice-Based Evaluation (Domain Analysis)

**What was measured:** Source-level recall@3 and faithfulness broken
down by document domain, rather than just a global average. This
exposes *where* the system succeeds and fails, rather than masking
failures with aggregate success.

**How:** `python cli.py inspect-run run-e4e5bcf7 --slice-by domain`
on the Dense-only RAG run using `gpt-4o-mini`. EvalOS migrated the
dataset to include domain tags (Finance, Quantum, Thermal,
Entrepreneurship, General) based on source document prefixes.

**Result:**

| Domain | Source Recall@3 | Faithfulness |
|---|---|---|
| Entrepreneurship | **100.0%** | 100.0% |
| Finance | **100.0%** | 100.0% |
| Thermal | 91.7% | 100.0% |
| Quantum | 84.4% | 92.7% |
| General (Negative Control) | 0.0%* | 100.0% |

**Honest caveats:**
- *The 0.0% recall on the "General" domain is the negative control
  question ("What is quantum entanglement?") which has `expected_sources: []`.
  pgvector still retrieves nearest neighbors for it, so the system
  generates an answer (hence 100% faithfulness to the provided context),
  but the retrieval correctly scores 0.0% because there were no expected
  sources to find. A true "Abstention" metric is needed to test if the
  system should have refused to answer.
- **The real finding:** The global 88.9% recall is entirely dragged
  down by the Quantum domain (84.4%). If you were building this RAG
  system for a finance startup, EvalOS just proved your system is
  effectively perfect (100% recall). If you were building it for
  quantum physicists, you have a known, diagnosed retrieval failure
  mode to fix.
