# HITL Evaluator Reliability & Calibration

**What was measured:** Whether the `LLMJudgeEvaluator` (which uses `gpt-4o-mini` to extract claims and verify them against context) is actually telling the truth, and whether it conflates "Groundedness" with "Completeness". We measure Inter-Rater Agreement, Pearson Correlation, Mean Absolute Error (MAE), and a Confusion Matrix.

**How:** `python cli.py label-judgements` followed by `python cli.py calculate-agreement`. The HITL system prompts for independent human scores (0.0-1.0), failure categories, and comments. 

**Result (Rich Calibration Audit on 5 Samples):**
* Run: `run-12c3d632` (Includes Answer Quality & Rich Human Labels)
* **Pearson Correlation: 0.0000** (Constant Input Warning)
* **Mean Absolute Error (MAE): 0.1320**
* **Confusion Matrix:**
  * True Positives: 4
  * False Positives: 1 (Judge said correct, Human said incorrect)
  * False Negatives: 0
  * True Negatives: 0

**Honest caveats & Real findings:**
- **The "Lenient Judge" Discovery:** The Pearson Correlation is 0.0 because the LLM Judge gave all 5 samples a perfect 1.0 score (zero variance). The human scores varied (0.65, 0.85, 0.92, 0.96, 0.96).
- The MAE (0.1320) quantifies the exact bias: The LLM Judge is, on average, 13.2% too lenient. It scores 100% on faithfulness, but humans score ~86.8% because the answers are "faithful but incomplete." 
- The Confusion Matrix caught the one hard failure (the 0.65 sample) where the Judge said "correct" but the human said "incorrect."
- This proves the CTO audit's point: Groundedness != Completeness. The LLM Judge is overly lenient on incomplete answers. This is why the `AnswerQualityEvaluator` was added to measure correctness and completeness independently of faithfulness.
