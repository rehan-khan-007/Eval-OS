import asyncio
import typer
import uuid
from database import AsyncSessionLocal
from models import Execution, MetricResult, HumanLabel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sklearn.metrics import cohen_kappa_score
from analysis_engine import AnalysisEngine

def label_judgements(run_id: str = typer.Argument(..., help="The Run ID to label judgements for")):
    """Prompts the user to verify LLM Judge verdicts for a random sample of executions."""
    async def run():
        async with AsyncSessionLocal() as db:
            stmt = (
                select(Execution, MetricResult)
                .join(MetricResult, Execution.id == MetricResult.execution_id)
                .where(Execution.run_id == run_id, MetricResult.evaluator_name == "faithfulness")
                .options(selectinload(Execution.example))
                .order_by(func.random())
                .limit(5)
            )
            result = await db.execute(stmt)
            rows = result.all()
            
            if not rows:
                typer.echo("No executions with faithfulness metrics found for this run.")
                return

        labels_to_save = []
        for i, (exec, metric) in enumerate(rows):
            typer.echo(f"\n{'='*70}\nSample {i+1}/5\n{'='*70}")
            typer.echo(f"Question: {exec.example.question}")
            
            context_text = "\n\n".join([f"- {e.get('source', '')}: {e.get('text', '')[:150]}..." for e in exec.retrieved_evidence or []])
            typer.echo(f"\nContext Provided:\n{context_text}")
            
            typer.echo(f"\nGenerated Answer:\n{exec.system_output}")
            
            typer.echo(f"\nLLM Judge Verdict (Score: {metric.score*100:.1f}%):")
            claims = metric.evidence_breakdown.get("claims", []) if metric.evidence_breakdown else []
            for c in claims:
                status = c.get("status", "unknown")
                symbol = "✓" if status == "supported" else ("✗" if status == "contradicted" else "?")
                typer.echo(f"  {symbol} {c.get('claim', '')} [{status}]")
            typer.echo(f"  Reasoning: {metric.explanation}")
            
            valid_score = False
            while not valid_score:
                score_str = typer.prompt("Enter your independent score (0.0 to 1.0)", default="1.0")
                try:
                    human_score = float(score_str)
                    if 0.0 <= human_score <= 1.0:
                        valid_score = True
                    else:
                        typer.echo("Score must be between 0.0 and 1.0.")
                except ValueError:
                    typer.echo("Invalid number. Please enter a float (e.g., 0.5).")
            
            valid_cat = False
            while not valid_cat:
                cat = typer.prompt("Enter failure category (none, retrieval_failure, generation_failure, system_error)", default="none")
                if cat.lower() in ["none", "retrieval_failure", "generation_failure", "system_error"]:
                    valid_cat = True
                    failure_category = cat.lower() if cat.lower() != "none" else None
                else:
                    typer.echo("Invalid category. Choose from the list.")
            
            comment = typer.prompt("Optional: Add a brief comment (press enter to skip)", default="")
            agrees = abs(human_score - metric.score) < 0.2
            labels_to_save.append((metric.id, exec.id, agrees, human_score, failure_category, comment))

        async with AsyncSessionLocal() as db:
            for metric_id, exec_id, agrees, h_score, f_cat, comment in labels_to_save:
                human_label = HumanLabel(
                    id=f"hl-{uuid.uuid4().hex[:8]}",
                    metric_result_id=metric_id,
                    execution_id=exec_id,
                    agrees_with_judge=agrees,
                    human_score=h_score,
                    failure_category=f_cat,
                    comment=comment
                )
                db.add(human_label)
            await db.commit()
            
        typer.echo(f"\n{'='*70}\nLabeling complete for 5 samples. Rich labels saved.\n{'='*70}")
    asyncio.run(run())

def calculate_agreement(run_id: str = typer.Argument(..., help="The Run ID to calculate agreement for")):
    """Calculates Cohen's Kappa, Raw Agreement, Pearson Correlation, and Confusion Matrix."""
    async def run():
        data = await AnalysisEngine.calculate_calibration(run_id)
        if not data:
            typer.echo("No human labels found for this run. Run `label-judgements` first.")
            return
            
        typer.echo("=" * 50)
        typer.echo(f"Evaluator Calibration Report for Run {run_id}")
        typer.echo("=" * 50)
        typer.echo(f"Total Labeled Samples: {data['total_samples']}")
        typer.echo(f"Pearson Correlation: {data['pearson_correlation']:.4f}")
        typer.echo(f"Mean Absolute Error (MAE): {data['mean_absolute_error']:.4f}")
        typer.echo("=" * 50)
        
        cm = data['confusion_matrix']
        typer.echo("Confusion Matrix (Judge vs Human):")
        typer.echo(f"  True Positives (Both Correct): {cm['true_positive']}")
        typer.echo(f"  True Negatives (Both Incorrect): {cm['true_negative']}")
        typer.echo(f"  False Positives (Judge Correct, Human Incorrect): {cm['false_positive']}")
        typer.echo(f"  False Negatives (Judge Incorrect, Human Correct): {cm['false_negative']}")
        typer.echo("=" * 50)
        
    asyncio.run(run())
