# Final v1.0.0 Benchmark: GPT-4o-mini vs Claude 3.5 Haiku

**What was measured:** A definitive, final comparison of two leading "fast tier" models (`gpt-4o-mini` and `claude-haiku-4.5`) on the frozen v1.0.0 codebase. This benchmark serves as the canonical, reproducible data point for the EvalOS v1.0.0 release.

**How:** `python cli.py run-benchmark --dataset-version dv-ds-retrieval_qa-v1 --models "openai/gpt-4o-mini,anthropic/claude-haiku-4.5" --retriever dense --concurrency 5 --experiment-name "Final Benchmark v1.0"`. 
* Run 1 (`run-d4a489d6`): `gpt-4o-mini`
* Run 2 (`run-ee9a6de2`): `claude-haiku-4.5`
* N = 36 examples. 

**Result:**

| Model | Recall@3 | Faithfulness | Answer Quality | Citation | Abstention | Avg Latency |
|---|---|---|---|---|---|---|
| `claude-haiku-4.5` | 88.9% | **96.4%** | **95.8%** | 97.2% | **91.7%** | 2.67s |
| `gpt-4o-mini` | 88.9% | 93.2% | 88.9% | **100.0%** | 83.3% | 3.15s |

**Honest caveats & Real findings:**
- **The Quality Winner:** `claude-haiku-4.5` actually outperformed `gpt-4o-mini` on Answer Quality (95.8% vs 88.9%) and Faithfulness (96.4% vs 93.2%) on this specific 36-question benchmark. It was also faster (2.67s vs 3.15s).
- **The Citation Winner:** `gpt-4o-mini` maintained a perfect 100% Citation Correctness score, while Haiku dropped to 97.2%. This indicates GPT-4o-mini is slightly better at attributing claims to the exact correct source document when forced to cite.
- **Reproducibility:** Both runs share the same `run_fingerprint` configuration hash for their respective system configs, executed on the frozen `v1.0.0` codebase.
- **Statistical Note:** With N=36, these observed differences in quality and faithfulness are directionally interesting but may not reach strict statistical significance (95% CI excluding zero). They represent observed performance on this specific benchmark, not universal model guarantees.
