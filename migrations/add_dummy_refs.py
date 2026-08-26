import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import AsyncSessionLocal
from models import EvaluationExample
from sqlalchemy import select

async def add_refs():
    async with AsyncSessionLocal() as db:
        # Just grab the first 3 examples from the dataset
        stmt = select(EvaluationExample).where(EvaluationExample.dataset_version_id == "dv-ds-retrieval_qa-v1").limit(3)
        result = await db.execute(stmt)
        examples = result.scalars().all()

        updated = 0
        for i, ex in enumerate(examples):
            # Force a dummy reference answer into the metadata
            current_meta = ex.metadata_json or {}
            current_meta["reference_answer"] = f"This is a dummy reference answer for question {i+1}."
            ex.metadata_json = current_meta
            updated += 1
        
        await db.commit()
        print(f"Updated {updated} examples with dummy reference answers.")

if __name__ == "__main__":
    asyncio.run(add_refs())
