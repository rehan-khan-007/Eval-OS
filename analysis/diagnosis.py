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
            # Store both score and status
            exec_data[exec.id]["metrics"][metric.evaluator_name] = {"score": metric.score, "status": metric.status}
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
            
            # P1 Fix: Dynamically find source_recall@K
            recall_data = next((v for k, v in metrics.items() if k.startswith("source_recall")), {"score": 0.0, "status": "success"})
            recall_score = recall_data.get("score", 0.0)
            
            faithfulness_data = metrics.get("faithfulness", {"score": 0.0, "status": "success"})
            faithfulness_score = faithfulness_data.get("score", 0.0)
            faithfulness_status = faithfulness_data.get("status", "success")
            
            abstention_score = metrics.get("abstention_accuracy", {"score": 1.0}).get("score", 1.0)
            
            entry = {
                "question": question,
                "example_id": example.id,
                "recall": recall_score,
                "faithfulness": faithfulness_score,
                "abstention": abstention_score
            }
            
            if exec.status != "success":
                taxonomy["system_failure"].append(entry)
            # P1 Fix: Use MetricResult.status instead of score == -1.0
            elif faithfulness_status == "evaluator_error":
                taxonomy["evaluator_error"].append(entry)
            elif len(expected_sources) == 0:
                if abstention_score == 1.0:
                    taxonomy["negative_control_pass"].append(entry)
                else:
                    taxonomy["negative_control_fail"].append(entry)
            elif recall_score == 0.0:
                taxonomy["retrieval_failure"].append(entry)
            elif faithfulness_score < 0.8 or abstention_score == 0.0:
                taxonomy["generation_failure"].append(entry)
            else:
                taxonomy["full_success"].append(entry)
                
        return taxonomy
