# Regression Testing

**What was measured:** Whether a new system configuration (Hybrid retrieval) regresses against a known baseline (Dense retrieval) beyond a configurable threshold. This turns EvalOS into a CI/CD gate for LLM behavior.

**How:** `python cli.py regression-check run-ccbcb9b2 run-31ab3a6d --threshold 0.01`. EvalOS compares the aggregate metrics of the two runs and flags any metric that dropped by more than 1%.

**Result:**

| Metric | Baseline (Dense) | New (Hybrid) | Change | Status |
|---|---|---|---|---|
| source_recall@3 | 88.9% | 84.7% | -4.2% | ✗ REGRESSION |
| faithfulness | 96.8% | 95.0% | -1.8% | ✗ REGRESSION |

**Verdict: REGRESSION DETECTED**

**Honest caveats:**
- This is a real, actionable CI/CD signal. If you were about to deploy Hybrid retrieval to production, EvalOS just blocked the deployment and told you exactly why: it regressed on both recall and faithfulness.
- The threshold is configurable. A 1% threshold is strict. In production, you might set it to 3% to allow for minor variance while catching major regressions.
- This completes the regression testing requirement from Section 23 of the spec: "EvalOS should function as CI/CD for LLM behavior."
