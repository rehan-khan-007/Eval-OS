import typer
from cli.setup_cmds import init_db_cli, ingest_dataset
from cli.run_cmds import run_eval, run_benchmark
from cli.inspect_cmds import inspect_run, inspect_failures
from cli.label_cmds import label_judgements, calculate_agreement

app = typer.Typer()

app.command()(init_db_cli)
app.command()(ingest_dataset)
app.command()(run_eval)
app.command()(run_benchmark)
app.command()(inspect_run)
app.command()(inspect_failures)
app.command()(label_judgements)
app.command()(calculate_agreement)

if __name__ == "__main__":
    app()
