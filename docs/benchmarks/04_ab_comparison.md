# A/B Comparison: Dense vs Hybrid Retrieval

**What was measured:** A side-by-side, per-example comparison of two retrieval systems (Dense-only vs Hybrid) to determine if the 4-point global recall gap between them is statistically meaningful or just noise.

**How:** `python cli.py compare-runs run-e4e5bcf7 run-31ab3a6d --metric source_recall@3`. EvalOS aligns the examples by `example_id`, calculates win/tie/loss, and runs a 1000-iteration Bootstrap simulation to generate a 95% Confidence Interval on the mean difference.

**Result:**

| Metric | Value |
|---|---|
| System A (Dense) Wins | 2 |
| System B (Hybrid) Wins | 0 |
| Ties | 34 |
| Mean Difference (A - B) | 0.0417 (4.2%) |
| 95% Confidence Interval | [0.0000, 0.1111] |
| Verdict | **NOT SIGNIFICANT** |

**Honest caveats:**
- **The real finding:** Although Dense-only had a higher global recall (88.9% vs 84.7%) and won on 2 specific questions where Hybrid completely failed, the 95% Confidence Interval touches `0.0000`. 
- This means the 4.2% difference is **not statistically significant** at this sample size (36 questions). We cannot confidently say Dense is universally better; the difference may be due to random variance.
- This highlights the danger of relying on global averages. Without EvalOS's statistical comparison, one might have incorrectly concluded that Hybrid actively harms the system, when in reality, the difference is marginal and needs a larger dataset to prove.
