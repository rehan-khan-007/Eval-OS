import asyncio
import typer
from analysis_engine import AnalysisEngine

def compare_runs(
    run_a_id: str = typer.Argument(..., help="The baseline Run ID (System A)"),
    run_b_id: str = typer.Argument(..., help="The new Run ID (System B)"),
    metric: str = typer.Option("source_recall@3", "--metric", help="Metric to compare (e.g., source_recall@3, faithfulness)")
):
    """Compares two runs side-by-side and calculates statistical significance."""
    async def run():
        data = await AnalysisEngine.compare_runs(run_a_id, run_b_id, metric)
        if not data:
            typer.echo("Could not compare runs. Ensure both Run IDs are valid and have the requested metric.")
            return

        typer.echo("=" * 50)
        typer.echo(f"A/B Comparison: {run_a_id} (A) vs {run_b_id} (B)")
        typer.echo(f"Metric: {data['metric_name']}")
        typer.echo("=" * 50)
        
        typer.echo(f"System A Wins: {data['a_wins']}")
        typer.echo(f"System B Wins: {data['b_wins']}")
        typer.echo(f"Ties: {data['ties']}")
        typer.echo("=" * 50)
        
        typer.echo("Statistical Significance (Bootstrap 95% CI)")
        typer.echo(f"  Mean Difference (A - B): {data['mean_diff']:.4f}")
        typer.echo(f"  95% Confidence Interval: [{data['ci_lower']:.4f}, {data['ci_upper']:.4f}]")
        
        if data['is_significant']:
            if data['mean_diff'] > 0:
                typer.echo("  Verdict: SIGNIFICANT. System A is statistically better than System B.")
            else:
                typer.echo("  Verdict: SIGNIFICANT. System B is statistically better than System A.")
        else:
            typer.echo("  Verdict: NOT SIGNIFICANT. The difference may be due to noise.")
        typer.echo("=" * 50)
        
    asyncio.run(run())
