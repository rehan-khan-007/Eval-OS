# HITL Evaluator Reliability & Calibration

**What was measured:** Whether the `LLMJudgeEvaluator` (which uses `gpt-4o-mini` to extract claims and verify them against context) is actually telling the truth, and whether it conflates "Groundedness" with "Completeness".

**How:** `python cli.py label-judgements` followed by `python cli.py calculate-agreement`. The HITL system was upgraded to prompt for independent human scores (0.0-1.0), failure categories, and comments, rather than just a boolean "agree/disagree".

**Result (Initial Boolean Audit):**
* Run: `run-ccbcb9b2`
* Raw Agreement: 100.0% (5/5)
* Cohen's Kappa: 0.0000 (Zero variance edge case)
* Finding: The Judge correctly identified supported claims.

**Result (Rich Calibration Audit):**
* Run: `run-12c3d632` (Includes Answer Quality & Rich Human Labels)
* Raw Agreement: **80.0%** (4/5)
* Cohen's Kappa: 0.0000 (Judge variance was 0)
* Finding: The human provided independent scores (e.g., 0.65, 0.85, 0.96) while the Judge provided 1.0 for all. 

**Honest caveats & Real findings:**
- **The "Lenient Judge" Discovery:** The drop in Raw Agreement (100% -> 80%) is a real, calibrated finding. The human reviewer scored answers lower (e.g., 0.65) because they were "faithful but substantially incomplete." The LLM Judge scored them 1.0 because it only checks if claims are supported (Groundedness). 
- This proves the CTO audit's point: Groundedness != Completeness. The LLM Judge is overly lenient on incomplete answers. 
- The `AnswerQualityEvaluator` was added to specifically address this gap, measuring correctness and completeness independently of faithfulness.
