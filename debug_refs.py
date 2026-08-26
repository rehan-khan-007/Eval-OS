import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import AsyncSessionLocal
from models import EvaluationExample
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        stmt = select(EvaluationExample).where(EvaluationExample.dataset_version_id == "dv-ds-retrieval_qa-v1")
        result = await db.execute(stmt)
        examples = result.scalars().all()
        
        found = 0
        for ex in examples:
            if "reference_answer" in (ex.metadata_json or {}):
                print(f"FOUND REF: {ex.question}")
                print(f"  Value: {ex.metadata_json['reference_answer']}")
                found += 1
                
        print(f"\nTotal examples with reference_answer: {found}")

if __name__ == "__main__":
    asyncio.run(check())
