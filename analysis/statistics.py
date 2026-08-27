from database import AsyncSessionLocal
from models import Execution, MetricResult
from sqlalchemy import select
import numpy as np

def calculate_bootstrap_ci(diffs: list[float], iterations: int = 1000, seed: int = 42) -> dict:
    """Pure function to calculate paired bootstrap confidence intervals."""
    if not diffs:
        return {"mean_diff": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "is_significant": False, "paired_valid_examples": 0}
        
    diffs_array = np.array(diffs)
    n = len(diffs_array)
    
    rng = np.random.default_rng(seed=seed)
    boot_means = []
    for _ in range(iterations):
        sample = rng.choice(diffs_array, size=n, replace=True)
        boot_means.append(np.mean(sample))
    
    lower_bound = np.percentile(boot_means, 2.5)
    upper_bound = np.percentile(boot_means, 97.5)
    mean_diff = np.mean(diffs_array)

    return {
        "mean_diff": mean_diff,
        "ci_lower": lower_bound,
        "ci_upper": upper_bound,
        "is_significant": not (lower_bound <= 0 <= upper_bound),
        "paired_valid_examples": n
    }

async def compare_runs(baseline_run_id: str, candidate_run_id: str, metric_name: str = "source_recall@3") -> dict:
    """Compares candidate against baseline. diff = candidate - baseline."""
    async with AsyncSessionLocal() as db:
        stmt_a = (
            select(Execution, MetricResult)
            .join(MetricResult, Execution.id == MetricResult.execution_id)
            .where(Execution.run_id == baseline_run_id, MetricResult.evaluator_name == metric_name)
        )
        rows_a = (await db.execute(stmt_a)).all()
        scores_a = {exec.example_id: metric.score for exec, metric in rows_a if metric.score >= 0.0}

        stmt_b = (
            select(Execution, MetricResult)
            .join(MetricResult, Execution.id == MetricResult.execution_id)
            .where(Execution.run_id == candidate_run_id, MetricResult.evaluator_name == metric_name)
        )
        rows_b = (await db.execute(stmt_b)).all()
        scores_b = {exec.example_id: metric.score for exec, metric in rows_b if metric.score >= 0.0}

        if not scores_a or not scores_b:
            return None

        baseline_wins = 0
        candidate_wins = 0
        ties = 0
        diffs = []

        common_examples = set(scores_a.keys()).intersection(set(scores_b.keys()))

        for ex_id in common_examples:
            val_baseline = scores_a[ex_id]
            val_candidate = scores_b[ex_id]
            # P1 Fix: Standardize delta = candidate - baseline
            diff = val_candidate - val_baseline
            diffs.append(diff)

            if diff > 0.001:
                candidate_wins += 1
            elif diff < -0.001:
                baseline_wins += 1
            else:
                ties += 1

        stats = calculate_bootstrap_ci(diffs)
        stats["metric_name"] = metric_name
        stats["baseline_wins"] = baseline_wins
        stats["candidate_wins"] = candidate_wins
        stats["ties"] = ties
        
        return stats
