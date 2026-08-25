import asyncio
import json
import typer
from database import init_db, AsyncSessionLocal, engine
from models import Dataset, DatasetVersion, EvaluationExample, SystemConfig, Base
from evaluators.deterministic import ToolSelectionEvaluator, SourceRecallEvaluator, LatencyEvaluator
from adapters.mock_adapter import MockSystemAdapter
from run_engine import RunEngine
from sqlalchemy import select

app = typer.Typer()

@app.command()
def init_db_cli():
    """Drops and creates all tables in the database."""
    async def run():
        typer.echo("Dropping old tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        typer.echo("Creating tables...")
        await init_db()
        typer.echo("Database initialized.")
    asyncio.run(run())

@app.command()
def ingest_dataset(file_path: str = typer.Argument(..., help="Path to the JSON dataset file")):
    """Ingests a dataset from a JSON file."""
    async def run():
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        async with AsyncSessionLocal() as db:
            ds_id = f"ds-{file_path.split('/')[-1].split('.')[0]}"
            dv_id = f"dv-{ds_id}-v1"
            
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
    config_name: str = typer.Option("MockAgentRAG", "--config-name")
):
    """Runs the evaluation engine against a dataset version."""
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
            
            # Check if the SystemConfig already exists to avoid UniqueViolationError
            config_stmt = select(SystemConfig).where(SystemConfig.id == sys_config_id)
            config_result = await db.execute(config_stmt)
            sys_config = config_result.scalars().first()
            
            if not sys_config:
                sys_config = SystemConfig(
                    id=sys_config_id,
                    config_name=config_name,
                    model="mock-model",
                    prompt_version="v1"
                )
                db.add(sys_config)
                await db.commit()
            else:
                typer.echo(f"Reusing existing SystemConfig: {sys_config_id}")

            adapter = MockSystemAdapter()
            
            # Auto-select evaluators based on the dataset's metadata
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

if __name__ == "__main__":
    app()
