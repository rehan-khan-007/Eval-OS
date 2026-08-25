import uuid
from datetime import datetime, timezone
from database import AsyncSessionLocal
from models import SystemConfig, EvaluationRun, Execution, MetricResult

class RunEngine:
    def __init__(self, sys_config_id: str, config_name: str, system_adapter, evaluators: list):
        self.sys_config_id = sys_config_id
        self.config_name = config_name
        self.system_adapter = system_adapter
        self.evaluators = evaluators

    async def execute_run(self, dataset_version_id: str, examples: list) -> str:
        async with AsyncSessionLocal() as db:
            run_id = f"run-{uuid.uuid4().hex[:8]}"
            run = EvaluationRun(
                id=run_id,
                system_config_id=self.sys_config_id,
                dataset_version_id=dataset_version_id,
                status="running",
                started_at=datetime.now(timezone.utc)
            )
            db.add(run)
            await db.commit()

            total_cost = 0.0

            for ex in examples:
                sys_output = await self.system_adapter.generate(ex)
                total_cost += sys_output.get("cost", 0.0)

                execution_id = f"exec-{uuid.uuid4().hex[:8]}"
                execution = Execution(
                    id=execution_id,
                    run_id=run_id,
                    example_id=ex["id"],
                    system_output=sys_output.get("answer"),
                    retrieved_evidence=sys_output.get("retrieved_evidence"),
                    latency_ms=sys_output.get("latency_ms", 0.0),
                    tokens_in=sys_output.get("tokens_in", 0),
                    tokens_out=sys_output.get("tokens_out", 0),
                    cost=sys_output.get("cost", 0.0),
                    status="success" if not sys_output.get("error") else "system_error",
                    error_message=sys_output.get("error")
                )
                db.add(execution)

                for evaluator in self.evaluators:
                    result = await evaluator.evaluate(ex, sys_output, sys_output.get("retrieved_evidence", []))
                    metric = MetricResult(
                        id=f"metric-{uuid.uuid4().hex[:8]}",
                        execution_id=execution_id,
                        evaluator_name=evaluator.name,
                        evaluator_version=evaluator.version,
                        score=result["score"],
                        explanation=result.get("explanation"),
                        evidence_breakdown=result.get("evidence_breakdown")
                    )
                    db.add(metric)

                await db.commit()

            run.status = "complete"
            run.total_cost = total_cost
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()

            return run_id
