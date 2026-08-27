import asyncio
import typer
from analysis_engine import AnalysisEngine

def regression_check(
    baseline_run_id: str = typer.Argument(..., help="The baseline Run ID"),
    new_run_id: str = typer.Argument(..., help="The new Run ID to check against the baseline"),
    threshold: float = typer.Option(0.02, "--threshold", help="Acceptable regression threshold (e.g., 0.02 for 2%)")
):
    """Checks a new run against a baseline for statistically meaningful regressions."""
    async def run():
        data = await AnalysisEngine.check_regression(baseline_run_id, new_run_id, threshold)
        if not data:
            typer.echo("Could not perform regression check. Ensure both Run IDs are valid.")
            return

        typer.echo("=" * 70)
        typer.echo(f"Regression Check: {baseline_run_id} (Baseline) vs {new_run_id} (New)")
        typer.echo(f"Threshold: {threshold*100:.1f}% AND 95% CI excludes zero")
        typer.echo("=" * 70)

        def format_entry(imp):
            metric = imp['metric']
            diff = imp['diff']
            verdict = imp['verdict']
            
            if metric == "latency_avg_ms":
                return f"  {metric}: {imp['baseline']:.1f}ms -> {imp['new']:.1f}ms (Δ: {diff:.1f}ms) [{verdict}]"
            
            n = imp.get('n', 'N/A')
            ci_l = imp.get('ci_lower', 0) * 100
            ci_u = imp.get('ci_upper', 0) * 100
            return f"  {metric}: Δ: {diff*100:.1f}% | 95% CI: [{ci_l:.1f}, {ci_u:.1f}] | N: {n} [{verdict}]"

        typer.echo("\nImprovements:")
        if data["improvements"]:
            for imp in data["improvements"]:
                typer.echo(format_entry(imp))
        else:
            typer.echo("  None")

        typer.echo("\nRegressions:")
        if data["regressions"]:
            for reg in data["regressions"]:
                typer.echo(format_entry(reg))
        else:
            typer.echo("  None")
            
        typer.echo("\nInconclusive:")
        if data["inconclusives"]:
            for inc in data["inconclusives"]:
                typer.echo(format_entry(inc))
        else:
            typer.echo("  None")

        typer.echo("=" * 70)
        typer.echo(f"VERDICT: {data['verdict']}")
        if data['verdict'] == 'REGRESSION':
            typer.echo("Action: Block deployment. The new run is significantly worse than the baseline.")
        elif data['verdict'] == 'INCONCLUSIVE':
            typer.echo("Action: Do not block, but require more data. Observed changes are not statistically significant.")
        else:
            typer.echo("Action: Safe to deploy. No regressions detected.")
        typer.echo("=" * 70)
        
    asyncio.run(run())
