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
            
            # --- NEW RICH PROMPTS ---
            
            # Prompt for human score
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
            
            # Prompt for failure category
            valid_cat = False
            while not valid_cat:
                cat = typer.prompt("Enter failure category (none, retrieval_failure, generation_failure, system_error)", default="none")
                if cat.lower() in ["none", "retrieval_failure", "generation_failure", "system_error"]:
                    valid_cat = True
                    failure_category = cat.lower() if cat.lower() != "none" else None
                else:
                    typer.echo("Invalid category. Choose from the list.")
            
            # Prompt for comment
            comment = typer.prompt("Optional: Add a brief comment (press enter to skip)", default="")
            
            # Derive agrees_with_judge based on score (if judge score > 0.8 and human score > 0.8, they agree)
            agrees = abs(human_score - metric.score) < 0.2
            
            labels_to_save.append((metric.id, exec.id, agrees, human_score, failure_category, comment))

        # 3. Save to DB in a new short-lived session
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
                judge_labels.append(1 if metric.score >= 0.8 else 0)
                human_labels.append(1 if human.human_score >= 0.8 else 0)
                
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
