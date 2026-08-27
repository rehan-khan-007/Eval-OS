import uuid
from datetime import datetime, timezone
import asyncio
import subprocess
import os
import hashlib
import json
from database import AsyncSessionLocal
from models import SystemConfig, EvaluationRun, Execution, MetricResult

class RunEngine:
    def __init__(self, sys_config_id: str, config_name: str, system_adapter, evaluators: list, concurrency: int = 5, experiment_id: str = None):
        self.sys_config_id = sys_config_id
        self.config_name = config_name
        self.system_adapter = system_adapter
        self.evaluators = evaluators
        self.semaphore = asyncio.Semaphore(concurrency)
        self.experiment_id = experiment_id

    def _get_provenance(self, dataset_version_id: str) -> dict:
        code_sha = "unknown"
        try:
            code_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode()
        except Exception:
            pass
            
        dep_lock = "unknown"
        try:
            with open("requirements.txt", "r") as f:
                dep_lock = f.read()
        except Exception:
            pass
            
        # Construct Canonical Fingerprint
        evaluator_suite = sorted([f"{e.name}:{e.version}" for e in self.evaluators])
        config_data = {
            "code_sha": code_sha,
            "dataset_version_id": dataset_version_id,
            "system_config_id": self.sys_config_id,
            "evaluator_suite": evaluator_suite,
            "dependency_lock": dep_lock
        }
        # Canonical JSON serialization (sort_keys=True)
        canonical_str = json.dumps(config_data, sort_keys=True)
        fingerprint = hashlib.sha256(canonical_str.encode()).hexdigest()
            
        return {"code_sha": code_sha, "dependency_lock": dep_lock, "fingerprint": fingerprint}

    async def _process_single_example(self, ex: dict, run_id: str) -> tuple:
        async with self.semaphore:
            sys_output = await self.system_adapter.generate(ex)
            metric_results = []
            for evaluator in self.evaluators:
                result = await evaluator.evaluate(ex, sys_output, sys_output.get("retrieved_evidence", []))
                metric_results.append((evaluator, result))
            return (ex, sys_output, metric_results)

    async def execute_run(self, dataset_version_id: str, examples: list) -> str:
        provenance = self._get_provenance(dataset_version_id)
        
        async with AsyncSessionLocal() as db:
            run_id = f"run-{uuid.uuid4().hex[:8]}"
            run = EvaluationRun(
                id=run_id,
                system_config_id=self.sys_config_id,
                dataset_version_id=dataset_version_id,
                status="running",
                started_at=datetime.now(timezone.utc),
                code_sha=provenance["code_sha"],
                dependency_lock=provenance["dependency_lock"],
                run_fingerprint=provenance["fingerprint"],
                experiment_id=self.experiment_id
            )
            db.add(run)
            await db.commit()

        tasks = [self._process_single_example(ex, run_id) for ex in examples]
        results = await asyncio.gather(*tasks)
        
        total_cost = 0.0
        async with AsyncSessionLocal() as db:
            for ex, sys_output, metric_results in results:
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

                for evaluator, result in metric_results:
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

        async with AsyncSessionLocal() as db:
            run = await db.get(EvaluationRun, run_id)
            run.status = "complete"
            run.total_cost = total_cost
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()

        return run_id
