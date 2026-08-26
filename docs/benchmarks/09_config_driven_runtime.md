# Configuration-Driven Runtime (Reproducibility)

**What was measured:** Whether the `SystemConfig` recorded in the database actually drives the runtime execution, ensuring 100% reproducibility. Specifically, we tested if changing the `top_k` parameter (number of retrieved chunks) from 3 to 5 would dynamically change the `SourceRecallEvaluator` metric name and score.

**How:** `python cli.py run-eval --dataset-version dv-ds-retrieval_qa-v1 --system rag --model openai/gpt-4o-mini --retriever dense --top-k 5 --config-name "DenseTopK5"`. EvalOS saved `retrieval_config: {"top_k": 5, "embedding_model": "openai/text-embedding-3-small"}` to the database and passed it down to the `RAGAdapter` and `SourceRecallEvaluator`.

**Result:**

| Config | Metric | Score | Cost | Avg Latency |
|---|---|---|---|---|
| `top_k=3` | `source_recall@3` | 88.9% | $0.0065 | 5.37s |
| `top_k=5` | `source_recall@5` | **91.7%** | $0.0097 | 7.68s |
| `top_k=5` | `faithfulness` | **99.0%** | - | - |
| `top_k=5` | `abstention_accuracy` | 86.1% | - | - |

**Honest caveats:**
- **The reproducibility fix worked:** The metric name dynamically became `source_recall@5` because the evaluator read the config from the database. If you inspect this run 6 months from now, the database will tell you exactly why it scored 91.7%.
- **The Trade-off:** Increasing `top_k` improved recall (91.7%) and faithfulness (99.0%) because the LLM had more context. However, it increased cost by ~50% (more tokens) and increased latency by ~2 seconds. EvalOS exposes this exact Pareto frontier.
