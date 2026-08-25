import asyncio
import typer
from database import AsyncSessionLocal
from models import Execution
from analysis_engine import AnalysisEngine
from sqlalchemy import select

def inspect_run(
    run_id: str = typer.Argument(..., help="The Run ID to inspect"),
    slice_by: str = typer.Option(None, "--slice-by", help="Slice metrics by 'domain' or 'task_type'")
):
    """Analyzes a specific run and prints the aggregated metrics."""
    async def run():
        if slice_by:
            data = await AnalysisEngine.analyze_run_slices(run_id, slice_by)
            if not data:
                typer.echo("Run not found or no data.")
                return
                
            typer.echo("=" * 50)
            typer.echo(f"Slice Analysis for Run {run_id} by {slice_by}")
            typer.echo("=" * 50)
            for slice_name, metrics in data.items():
                typer.echo(f"\n--- {slice_name} ---")
                for m_name, score in metrics.items():
                    if "recall" in m_name or "faithfulness" in m_name or "accuracy" in m_name:
                        typer.echo(f"  {m_name}: {score*100:.1f}%")
                    else:
                        typer.echo(f"  {m_name}: {score:.4f}")
            typer.echo("=" * 50)
            return

        data = await AnalysisEngine.analyze_run(run_id)
        if not data:
            typer.echo("Run not found.")
            return
            
        typer.echo("=" * 50)
        typer.echo(f"Run ID: {data['run_id']}")
        typer.echo(f"Status: {data['status']}")
        typer.echo(f"Config: {data['config_name']} ({data['model']})")
        typer.echo("=" * 50)
        typer.echo(f"Examples: {data['total_examples']} (Successes: {data['successes']}, Failures: {data['failures']})")
        typer.echo(f"Total Cost: ${data['total_cost']:.6f}")
        typer.echo("=" * 50)
        typer.echo("Latency (ms):")
        typer.echo(f"  Min: {data['latency_ms']['min']:.2f}")
        typer.echo(f"  Max: {data['latency_ms']['max']:.2f}")
        typer.echo(f"  Avg: {data['latency_ms']['avg']:.2f}")
        typer.echo("=" * 50)
        typer.echo("Metrics:")
        for name, score in data['metrics'].items():
            if "accuracy" in name or "recall" in name or "faithfulness" in name:
                typer.echo(f"  {name}: {score*100:.1f}%")
            else:
                typer.echo(f"  {name}: {score:.4f}")
        typer.echo("=" * 50)
    asyncio.run(run())

def inspect_failures(run_id: str = typer.Argument(..., help="The Run ID to inspect failures for")):
    """Prints the error messages for failed executions in a given run."""
    async def run():
        async with AsyncSessionLocal() as db:
            stmt = select(Execution).where(Execution.run_id == run_id, Execution.status != "success").limit(5)
            result = await db.execute(stmt)
            failures = result.scalars().all()
            
            if not failures:
                typer.echo("No failures found for this run.")
                return
                
            typer.echo(f"Found {len(failures)} failures (showing first 5):")
            for i, fail in enumerate(failures):
                typer.echo(f"\n{'='*50}\nFailure {i+1}:")
                typer.echo(f"Error: {fail.error_message}")
                typer.echo(f"Question ID: {fail.example_id}")
                typer.echo("=" * 50)
    asyncio.run(run())

def diagnose_run(run_id: str = typer.Argument(..., help="The Run ID to diagnose")):
    """Classifies failures into a taxonomy (Retrieval, Generation, System)."""
    async def run():
        data = await AnalysisEngine.diagnose_run(run_id)
        if not data:
            typer.echo("Run not found or no data.")
            return
            
        typer.echo("=" * 50)
        typer.echo(f"Failure Diagnosis for Run {run_id}")
        typer.echo("=" * 50)
        
        typer.echo(f"\n[1] Full Successes ({len(data['full_success'])}):")
        for item in data['full_success'][:3]:
            typer.echo(f"  - {item['question']}")
        if len(data['full_success']) > 3:
            typer.echo(f"  ... and {len(data['full_success']) - 3} more")
            
        typer.echo(f"\n[2] Retrieval Failures ({len(data['retrieval_failure'])}):")
        for item in data['retrieval_failure']:
            typer.echo(f"  - {item['question']} (Recall: {item['recall']*100:.1f}%)")
            
        typer.echo(f"\n[3] Generation Failures ({len(data['generation_failure'])}):")
        for item in data['generation_failure']:
            typer.echo(f"  - {item['question']} (Faithfulness: {item['faithfulness']*100:.1f}%)")
            
        typer.echo(f"\n[4] System Failures ({len(data['system_failure'])}):")
        for item in data['system_failure']:
            typer.echo(f"  - {item['question']}")
            
        typer.echo(f"\n[5] Negative Control - Passed ({len(data['negative_control_pass'])}):")
        for item in data['negative_control_pass']:
            typer.echo(f"  - {item['question']}")
            
        typer.echo(f"\n[6] Negative Control - Failed ({len(data['negative_control_fail'])}):")
        for item in data['negative_control_fail']:
            typer.echo(f"  - {item['question']} (Should have abstained but answered)")
            
        typer.echo("=" * 50)
    asyncio.run(run())
