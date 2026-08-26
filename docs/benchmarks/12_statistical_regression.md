# Statistical Regression Testing

**What was measured:** Whether a new system configuration (Hybrid retrieval) regresses against a known baseline (Dense retrieval). This upgrades EvalOS from a simple threshold-based gate to a statistically valid CI/CD gate.

**How:** `python cli.py regression-check run-ccbcb9b2 run-31ab3a6d --threshold 0.01`. EvalOS now requires a metric to drop by more than the threshold AND for the 95% Bootstrap Confidence Interval to exclude zero before flagging it as a regression.

**Result:**

| Metric | Baseline (Dense) | New (Hybrid) | Change | Significant? | Status |
|---|---|---|---|---|---|
| `source_recall@3` | 88.9% | 84.7% | -4.2% | No (CI touched 0) | Ignored (Noise) |
| `latency_avg_ms` | 5378.7ms | 7816.9ms | -2438.2ms | **Yes** | ✗ REGRESSION |

**Verdict: REGRESSION DETECTED**

**Honest caveats:**
- **The real finding:** EvalOS successfully prevented a false positive. The 4.2% recall drop looks bad, but EvalOS's statistical engine knew it wasn't significant at this sample size, so it didn't flag it. 
- However, the latency increase was massive (2.4 seconds slower) and statistically significant. EvalOS blocked the deployment of Hybrid retrieval based on real statistical evidence, not just a raw percentage threshold.
- This fulfills the CTO audit's requirement: "Regression if: Δ < -threshold AND 95% CI excludes zero."
