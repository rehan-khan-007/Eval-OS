import asyncio
import typer
import uuid
from database import AsyncSessionLocal
from models import Execution, MetricResult, HumanLabel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sklearn.metrics import cohen_kappa_score

def label_judgements(run_id: str = typer.Argument(..., help="The Run ID to label judgements for")):
    """Prompts the user to verify LLM Judge verdicts for a random sample of executions."""
    async def run():
        # 1. Fetch samples in a short-lived session to avoid Neon idle timeouts
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

        # 2. Prompt user outside of DB session
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
            
            valid_input = False
            while not valid_input:
                ans = typer.prompt("Is the LLM Judge verdict correct? (y/n)", default="y")
                if ans.lower() in ["y", "n"]:
                    valid_input = True
                    
            agrees = ans.lower() == "y"
            labels_to_save.append((metric.id, exec.id, agrees))

        # 3. Save to DB in a new short-lived session
        async with AsyncSessionLocal() as db:
            for metric_id, exec_id, agrees in labels_to_save:
                human_label = HumanLabel(
                    id=f"hl-{uuid.uuid4().hex[:8]}",
                    metric_result_id=metric_id,
                    execution_id=exec_id,
                    agrees_with_judge=agrees
                )
                db.add(human_label)
            await db.commit()
            
        typer.echo(f"\n{'='*70}\nLabeling complete for 5 samples.\n{'='*70}")
    asyncio.run(run())

def calculate_agreement(run_id: str = typer.Argument(..., help="The Run ID to calculate agreement for")):
    """Calculates the Cohen's Kappa and Raw Agreement between the LLM Judge and Human Labels."""
    async def run():
        async with AsyncSessionLocal() as db:
            stmt = (
                select(MetricResult, HumanLabel)
                .join(HumanLabel, MetricResult.id == HumanLabel.metric_result_id)
                .join(Execution, MetricResult.execution_id == Execution.id)
                .where(Execution.run_id == run_id)
            )
            result = await db.execute(stmt)
            rows = result.all()
            
            if not rows:
                typer.echo("No human labels found for this run. Run `label-judgements` first.")
                return
                
            judge_labels = []
            human_labels = []
            
            for metric, human in rows:
                judge_labels.append(1 if metric.score == 1.0 else 0)
                human_labels.append(1 if human.agrees_with_judge else 0)
                
            matches = sum(1 for j, h in zip(judge_labels, human_labels) if j == h)
            raw_agreement = matches / len(rows) * 100
            
            kappa = 0.0
            if len(set(judge_labels)) > 1 and len(set(human_labels)) > 1:
                kappa = cohen_kappa_score(human_labels, judge_labels)
            
            typer.echo("=" * 50)
            typer.echo(f"Inter-Rater Agreement for Run {run_id}")
            typer.echo("=" * 50)
            typer.echo(f"Total Labeled Samples: {len(rows)}")
            typer.echo(f"Raw Agreement: {raw_agreement:.1f}%")
            typer.echo(f"Cohen's Kappa: {kappa:.4f}")
            typer.echo("=" * 50)
            if raw_agreement > 80:
                typer.echo("Assessment: High raw agreement. The LLM Judge is generally reliable.")
            else:
                typer.echo("Assessment: Low raw agreement. The LLM Judge may need prompt refinement.")
            typer.echo("=" * 50)
    asyncio.run(run())
