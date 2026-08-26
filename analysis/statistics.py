from database import AsyncSessionLocal
from models import Execution, MetricResult
from sqlalchemy import select
import numpy as np

async def compare_runs(run_a_id: str, run_b_id: str, metric_name: str = "source_recall@3") -> dict:
    async with AsyncSessionLocal() as db:
        stmt_a = (
            select(Execution, MetricResult)
            .join(MetricResult, Execution.id == MetricResult.execution_id)
            .where(Execution.run_id == run_a_id, MetricResult.evaluator_name == metric_name)
        )
        rows_a = (await db.execute(stmt_a)).all()
        scores_a = {exec.example_id: metric.score for exec, metric in rows_a if metric.score >= 0.0}

        stmt_b = (
            select(Execution, MetricResult)
            .join(MetricResult, Execution.id == MetricResult.execution_id)
            .where(Execution.run_id == run_b_id, MetricResult.evaluator_name == metric_name)
        )
        rows_b = (await db.execute(stmt_b)).all()
        scores_b = {exec.example_id: metric.score for exec, metric in rows_b if metric.score >= 0.0}

        if not scores_a or not scores_b:
            return None

        a_wins = 0
        b_wins = 0
        ties = 0
        diffs = []

        common_examples = set(scores_a.keys()).intersection(set(scores_b.keys()))

        for ex_id in common_examples:
            val_a = scores_a[ex_id]
            val_b = scores_b[ex_id]
            diff = val_a - val_b
            diffs.append(diff)

            if diff > 0.001:
                a_wins += 1
            elif diff < -0.001:
                b_wins += 1
            else:
                ties += 1

        diffs_array = np.array(diffs)
        n = len(diffs_array)
        
        rng = np.random.default_rng(seed=42)
        boot_means = []
        for _ in range(1000):
            sample = rng.choice(diffs_array, size=n, replace=True)
            boot_means.append(np.mean(sample))
        
        lower_bound = np.percentile(boot_means, 2.5)
        upper_bound = np.percentile(boot_means, 97.5)
        mean_diff = np.mean(diffs_array)

        return {
            "metric_name": metric_name,
            "a_wins": a_wins,
            "b_wins": b_wins,
            "ties": ties,
            "mean_diff": mean_diff,
            "ci_lower": lower_bound,
            "ci_upper": upper_bound,
            "is_significant": not (lower_bound <= 0 <= upper_bound)
        }
