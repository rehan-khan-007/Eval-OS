from database import AsyncSessionLocal
from models import EvaluationRun, Execution, MetricResult, SystemConfig, DatasetVersion
from sqlalchemy import select
from collections import defaultdict

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
