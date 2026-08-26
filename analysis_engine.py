from database import AsyncSessionLocal
from models import EvaluationRun, Execution, MetricResult, SystemConfig, DatasetVersion, EvaluationExample
from sqlalchemy import select
from collections import defaultdict
import numpy as np

class AnalysisEngine:
    @staticmethod
    async def analyze_run(run_id: str) -> dict:
        async with AsyncSessionLocal() as db:
            run = await db.get(EvaluationRun, run_id)
            if not run:
                return None
            
            sys_config = await db.get(SystemConfig, run.system_config_id)
            
            stmt = select(Execution).where(Execution.run_id == run_id)
            result = await db.execute(stmt)
            executions = result.scalars().all()
            
            exec_ids = [e.id for e in executions]
            metric_stmt = select(MetricResult).where(MetricResult.execution_id.in_(exec_ids))
            metric_result = await db.execute(metric_stmt)
            metrics = metric_result.scalars().all()
            
            latencies = [e.latency_ms for e in executions if e.status == "success"]
            
            metric_scores = defaultdict(list)
            for m in metrics:
                if m.score >= 0.0:  # Ignore indeterminate (-1.0) scores in aggregates
                    metric_scores[m.evaluator_name].append(m.score)
                
            aggregated_metrics = {}
            for name, scores in metric_scores.items():
                if name == "latency_ms":
                    continue
                aggregated_metrics[name] = sum(scores) / len(scores) if scores else 0.0
                
            return {
                "run_id": run_id,
                "status": run.status,
                "config_name": sys_config.config_name if sys_config else "Unknown",
                "model": sys_config.model if sys_config else "Unknown",
                "total_examples": len(executions),
                "successes": len([e for e in executions if e.status == "success"]),
                "failures": len([e for e in executions if e.status != "success"]),
                "total_cost": run.total_cost,
                "latency_ms": {
                    "min": min(latencies) if latencies else 0,
                    "max": max(latencies) if latencies else 0,
                    "avg": sum(latencies) / len(latencies) if latencies else 0
                },
                "metrics": aggregated_metrics
            }

    @staticmethod
    async def analyze_run_slices(run_id: str, slice_field: str) -> dict:
        async with AsyncSessionLocal() as db:
            stmt = (
                select(Execution, MetricResult, EvaluationExample)
                .join(MetricResult, Execution.id == MetricResult.execution_id)
                .join(EvaluationExample, Execution.example_id == EvaluationExample.id)
                .where(Execution.run_id == run_id)
            )
            result = await db.execute(stmt)
            rows = result.all()
            
            if not rows:
                return None
                
            slices = defaultdict(lambda: defaultdict(list))
            
            for exec, metric, example in rows:
                if metric.evaluator_name == "latency_ms" or metric.score < 0.0:
                    continue
                    
                if slice_field == "domain":
                    slice_key = example.domain if example.domain else "unknown"
                elif slice_field == "task_type":
                    slice_key = example.task_type if example.task_type else "unknown"
                else:
                    slice_key = "unknown"
                    
                slices[slice_key][metric.evaluator_name].append(metric.score)
                
            aggregated_slices = {}
            for slice_name, metrics in slices.items():
                agg_metrics = {}
                for m_name, scores in metrics.items():
                    agg_metrics[m_name] = sum(scores) / len(scores) if scores else 0.0
                aggregated_slices[slice_name] = agg_metrics
                
            return aggregated_slices

    @staticmethod
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
            
            # P1 Fix: Use a deterministic seed for reproducible statistical CIs
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

    @staticmethod
    async def diagnose_run(run_id: str) -> dict:
        async with AsyncSessionLocal() as db:
            stmt = (
                select(Execution, MetricResult, EvaluationExample)
                .join(MetricResult, Execution.id == MetricResult.execution_id)
                .join(EvaluationExample, Execution.example_id == EvaluationExample.id)
                .where(Execution.run_id == run_id)
            )
            result = await db.execute(stmt)
            rows = result.all()
            
            if not rows:
                return None
                
            exec_data = defaultdict(lambda: {"metrics": {}, "example": None, "exec": None})
            for exec, metric, example in rows:
                exec_data[exec.id]["metrics"][metric.evaluator_name] = metric.score
                exec_data[exec.id]["example"] = example
                exec_data[exec.id]["exec"] = exec
                
            taxonomy = {
                "retrieval_failure": [],
                "generation_failure": [],
                "system_failure": [],
                "evaluator_error": [],
                "negative_control_pass": [],
                "negative_control_fail": [],
                "full_success": []
            }
            
            for exec_id, data in exec_data.items():
                exec = data["exec"]
                example = data["example"]
                metrics = data["metrics"]
                
                question = example.question[:50] + "..." if len(example.question) > 50 else example.question
                expected_sources = example.metadata_json.get("expected_sources", [])
                recall = metrics.get("source_recall@3", 0.0)
                faithfulness = metrics.get("faithfulness", 0.0)
                abstention = metrics.get("abstention_accuracy", 1.0)
                
                entry = {
                    "question": question,
                    "example_id": example.id,
                    "recall": recall,
                    "faithfulness": faithfulness,
                    "abstention": abstention
                }
                
                if exec.status != "success":
                    taxonomy["system_failure"].append(entry)
                elif faithfulness == -1.0:
                    taxonomy["evaluator_error"].append(entry)
                elif len(expected_sources) == 0:
                    if abstention == 1.0:
                        taxonomy["negative_control_pass"].append(entry)
                    else:
                        taxonomy["negative_control_fail"].append(entry)
                elif recall == 0.0:
                    taxonomy["retrieval_failure"].append(entry)
                elif faithfulness < 0.8 or abstention == 0.0:
                    taxonomy["generation_failure"].append(entry)
                else:
                    taxonomy["full_success"].append(entry)
                    
            return taxonomy

    @staticmethod
    async def check_regression(baseline_run_id: str, new_run_id: str, threshold: float = 0.02) -> dict:
        baseline_data = await AnalysisEngine.analyze_run(baseline_run_id)
        new_data = await AnalysisEngine.analyze_run(new_run_id)
        
        if not baseline_data or not new_data:
            return None
            
        regressions = []
        improvements = []
        
        # P0 Fix: Explicitly handle latency_ms which is nested under its own dict
        b_lat = baseline_data["latency_ms"]["avg"]
        n_lat = new_data["latency_ms"]["avg"]
        lat_diff = b_lat - n_lat # Positive diff means new run is faster (improvement)
        
        # Latency threshold (e.g., 500ms difference)
        lat_threshold_ms = 500.0 
        if lat_diff < -lat_threshold_ms:
            regressions.append({"metric": "latency_avg_ms", "baseline": b_lat, "new": n_lat, "diff": lat_diff})
        elif lat_diff > lat_threshold_ms:
            improvements.append({"metric": "latency_avg_ms", "baseline": b_lat, "new": n_lat, "diff": lat_diff})
            
        # Compare all other standard metrics
        all_metrics = set(baseline_data["metrics"].keys()).union(set(new_data["metrics"].keys()))
        
        for metric in all_metrics:
            if metric == "latency_ms":
                continue
                
            b_score = baseline_data["metrics"].get(metric, 0.0)
            n_score = new_data["metrics"].get(metric, 0.0)
            diff = n_score - b_score
            
            if diff < -threshold:
                regressions.append({"metric": metric, "baseline": b_score, "new": n_score, "diff": diff})
            elif diff > threshold:
                improvements.append({"metric": metric, "baseline": b_score, "new": n_score, "diff": diff})
                
        return {
            "baseline_run": baseline_run_id,
            "new_run": new_run_id,
            "regressions": regressions,
            "improvements": improvements,
            "is_regression": len(regressions) > 0
        }
