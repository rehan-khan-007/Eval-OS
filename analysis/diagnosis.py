from database import AsyncSessionLocal
from models import Execution, MetricResult, EvaluationExample
from sqlalchemy import select
from collections import defaultdict

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
            recall = metrics.get("source_recall@3", 0.0) # Note: dynamically matching @k would be better later
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
