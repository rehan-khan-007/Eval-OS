import asyncio
import json
import typer
import os
from database import init_db, AsyncSessionLocal, engine
from models import Dataset, DatasetVersion, EvaluationExample, SystemConfig, Base
from evaluators.deterministic import ToolSelectionEvaluator, SourceRecallEvaluator, LatencyEvaluator
from adapters.mock_adapter import MockSystemAdapter
from adapters.openrouter_adapter import OpenRouterAdapter
from adapters.rag_adapter import RAGAdapter
from run_engine import RunEngine
from analysis_engine import AnalysisEngine
from sqlalchemy import select

app = typer.Typer()

@app.command()
def init_db_cli():
    async def run():
        typer.echo("Creating tables (if not exist) and ensuring pgvector extension...")
        await init_db()
        typer.echo("Database initialized.")
    asyncio.run(run())

@app.command()
def ingest_dataset(file_path: str = typer.Argument(..., help="Path to the JSON dataset file")):
    async def run():
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        async with AsyncSessionLocal() as db:
            ds_id = f"ds-{file_path.split('/')[-1].split('.')[0]}"
            dv_id = f"dv-{ds_id}-v1"
            
            stmt = select(DatasetVersion).where(DatasetVersion.id == dv_id)
            result = await db.execute(stmt)
            if result.scalars().first():
                typer.echo(f"Dataset version {dv_id} already exists. Skipping.")
                return
            
            ds = Dataset(id=ds_id, name=f"Dataset from {file_path}")
            db.add(ds)
            dv = DatasetVersion(id=dv_id, dataset_id=ds_id, version_tag="v1", commit_hash="n/a")
            db.add(dv)
            
            for item in data:
                question = item.get("message") or item.get("question")
                metadata = {}
                if "expected_tool" in item:
                    metadata["expected_tool"] = item["expected_tool"]
                if "expected_sources" in item:
                    metadata["expected_sources"] = item["expected_sources"]
                    
                ex_id = f"ex-{abs(hash(question)) % (10 ** 8)}"
                ex = EvaluationExample(
                    id=ex_id,
                    dataset_version_id=dv_id,
                    question=question,
                    task_type="agent_task" if "expected_tool" in item else "retrieval_qa",
                    domain="general",
                    metadata_json=metadata
                )
                db.add(ex)
                
            await db.commit()
            typer.echo(f"Ingested {len(data)} examples. Dataset ID: {ds_id}, Version ID: {dv_id}")
    asyncio.run(run())

@app.command()
def run_eval(
    dataset_version_id: str = typer.Option(..., "--dataset-version"),
    config_name: str = typer.Option("OpenRouterAgent", "--config-name"),
    system: str = typer.Option("openrouter", "--system", help="mock, openrouter, or rag"),
    model: str = typer.Option("openai/gpt-4o-mini", "--model")
):
    async def run():
        async with AsyncSessionLocal() as db:
            stmt = select(EvaluationExample).where(EvaluationExample.dataset_version_id == dataset_version_id)
            result = await db.execute(stmt)
            db_examples = result.scalars().all()
            
            if not db_examples:
                typer.echo("No examples found.")
                return

            examples = [{
                "id": ex.id,
                "question": ex.question,
                "metadata": ex.metadata_json
            } for ex in db_examples]

            sys_config_id = f"cfg-{config_name.lower().replace(' ', '-')}"
            
            config_stmt = select(SystemConfig).where(SystemConfig.id == sys_config_id)
            config_result = await db.execute(config_stmt)
            sys_config = config_result.scalars().first()
            
            if not sys_config:
                sys_config = SystemConfig(
                    id=sys_config_id,
                    config_name=config_name,
                    model=model,
                    prompt_version="v1"
                )
                db.add(sys_config)
                await db.commit()
            else:
                typer.echo(f"Reusing existing SystemConfig: {sys_config_id}")

            if system == "mock":
                adapter = MockSystemAdapter()
                typer.echo("Using MockSystemAdapter.")
            elif system == "openrouter":
                adapter = OpenRouterAdapter(model=model)
                typer.echo(f"Using OpenRouterAdapter with model: {model}")
            elif system == "rag":
                adapter = RAGAdapter(model=model)
                typer.echo(f"Using RAGAdapter with model: {model}")
            else:
                typer.echo("Invalid system. Choose 'mock', 'openrouter', or 'rag'.")
                return
            
            evaluators = [LatencyEvaluator()]
            if examples[0]["metadata"].get("expected_tool"):
                evaluators.append(ToolSelectionEvaluator())
                typer.echo("Detected agent dataset. Using ToolSelectionEvaluator.")
            if examples[0]["metadata"].get("expected_sources") is not None:
                evaluators.append(SourceRecallEvaluator(k=3))
                typer.echo("Detected RAG dataset. Using SourceRecallEvaluator.")

            engine = RunEngine(sys_config, adapter, evaluators)
            typer.echo("Starting evaluation run...")
            run_id = await engine.execute_run(dataset_version_id, examples)
            typer.echo(f"Evaluation complete. Run ID: {run_id}")
    asyncio.run(run())

@app.command()
def inspect_run(run_id: str = typer.Argument(..., help="The Run ID to inspect")):
    """Analyzes a specific run and prints the aggregated metrics."""
    async def run():
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
            if "accuracy" in name or "recall" in name:
                typer.echo(f"  {name}: {score*100:.1f}%")
            else:
                typer.echo(f"  {name}: {score:.4f}")
        typer.echo("=" * 50)
    asyncio.run(run())

if __name__ == "__main__":
    app()
