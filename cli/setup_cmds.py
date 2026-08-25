import asyncio
import json
import typer
from database import init_db, AsyncSessionLocal
from models import Dataset, DatasetVersion, EvaluationExample
from sqlalchemy import select

def init_db_cli():
    """Creates all tables in the database (does not drop existing)."""
    async def run():
        typer.echo("Creating tables (if not exist) and ensuring pgvector extension...")
        await init_db()
        typer.echo("Database initialized.")
    asyncio.run(run())

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
