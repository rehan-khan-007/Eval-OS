import asyncio
import typer
from database import AsyncSessionLocal
from models import Experiment, EvaluationRun, SystemConfig
from sqlalchemy import select

def inspect_experiment(experiment_id: str = typer.Argument(..., help="The Experiment ID to inspect")):
    """Inspects an experiment and lists all runs grouped under it."""
    async def run():
        async with AsyncSessionLocal() as db:
            exp = await db.get(Experiment, experiment_id)
            if not exp:
                typer.echo("Experiment not found.")
                return
                
            typer.echo("=" * 50)
            typer.echo(f"Experiment ID: {exp.id}")
            typer.echo(f"Name: {exp.name}")
            typer.echo(f"Description: {exp.description}")
            typer.echo(f"Created: {exp.created_at}")
            typer.echo("=" * 50)
            
            stmt = select(EvaluationRun).where(EvaluationRun.experiment_id == experiment_id)
            result = await db.execute(stmt)
            runs = result.scalars().all()
            
            if not runs:
                typer.echo("No runs found for this experiment.")
                return
                
            typer.echo(f"Total Runs: {len(runs)}\n")
            for i, run in enumerate(runs):
                sys_config = await db.get(SystemConfig, run.system_config_id)
                typer.echo(f"Run {i+1}:")
                typer.echo(f"  Run ID: {run.id}")
                typer.echo(f"  Config: {sys_config.config_name if sys_config else 'Unknown'}")
                typer.echo(f"  Status: {run.status}")
                typer.echo(f"  Cost: ${run.total_cost:.6f}")
                typer.echo(f"  Started: {run.started_at}")
                typer.echo(f"  Code SHA: {run.code_sha[:10]}..." if run.code_sha else "  Code SHA: N/A")
                typer.echo("")
            typer.echo("=" * 50)
    asyncio.run(run())
