import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import AsyncSessionLocal
from models import EvaluationRun
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        # Just fetch the most recent run
        stmt = select(EvaluationRun).order_by(EvaluationRun.started_at.desc()).limit(1)
        result = await db.execute(stmt)
        run = result.scalars().first()
        
        if run:
            print(f"Run ID: {run.id}")
            print(f"Code SHA: {run.code_sha}")
            print(f"Dependency Lock Length: {len(run.dependency_lock or '')} chars")
            print(f"Dependency Lock (first 50): {(run.dependency_lock or '')[:50]}...")
        else:
            print("Run not found.")

if __name__ == "__main__":
    asyncio.run(check())
