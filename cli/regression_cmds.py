import asyncio
import typer
from analysis_engine import AnalysisEngine

def regression_check(
    baseline_run_id: str = typer.Argument(..., help="The baseline Run ID"),
    new_run_id: str = typer.Argument(..., help="The new Run ID to check against the baseline"),
    threshold: float = typer.Option(0.02, "--threshold", help="Acceptable regression threshold (e.g., 0.02 for 2%)")
):
    """Checks a new run against a baseline for regressions."""
    async def run():
        data = await AnalysisEngine.check_regression(baseline_run_id, new_run_id, threshold)
        if not data:
            typer.echo("Could not perform regression check. Ensure both Run IDs are valid.")
            return

        typer.echo("=" * 50)
        typer.echo(f"Regression Check: {baseline_run_id} (Baseline) vs {new_run_id} (New)")
        typer.echo(f"Threshold: {threshold*100:.1f}%")
        typer.echo("=" * 50)

        typer.echo("\nImprovements:")
        if data["improvements"]:
            for imp in data["improvements"]:
                typer.echo(f"  ✓ {imp['metric']}: {imp['baseline']*100:.1f}% -> {imp['new']*100:.1f}% (+{imp['diff']*100:.1f}%)")
        else:
            typer.echo("  None")

        typer.echo("\nRegressions:")
        if data["regressions"]:
            for reg in data["regressions"]:
                typer.echo(f"  ✗ {reg['metric']}: {reg['baseline']*100:.1f}% -> {reg['new']*100:.1f}% ({reg['diff']*100:.1f}%)")
        else:
            typer.echo("  None")

        typer.echo("=" * 50)
        if data["is_regression"]:
            typer.echo("VERDICT: REGRESSION DETECTED. The new run is significantly worse than the baseline.")
        else:
            typer.echo("VERDICT: NO REGRESSION. The new run is safe to deploy.")
        typer.echo("=" * 50)
        
    asyncio.run(run())
