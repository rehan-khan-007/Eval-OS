import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import AsyncSessionLocal
from models import EvaluationExample
from sqlalchemy import select, update
import typer

def infer_domain(sources: list) -> str:
    if not sources:
        return "general"
    src = sources[0].lower()
    if "sebi" in src:
        return "finance"
    if any(x in src for x in ["1102", "1510", "2003", "2402", "0910"]):
        return "quantum"
    if any(x in src for x in ["1906", "1812", "2104", "2404", "2505", "2106"]):
        return "entrepreneurship"
    if any(x in src for x in ["2010", "2107", "2203", "2105", "2206", "1809"]):
        return "thermal"
    return "general"

async def run():
    async with AsyncSessionLocal() as db:
        stmt = select(EvaluationExample).where(EvaluationExample.dataset_version_id == "dv-ds-retrieval_qa-v1")
        result = await db.execute(stmt)
        examples = result.scalars().all()
        
        updated = 0
        for ex in examples:
            sources = ex.metadata_json.get("expected_sources", [])
            domain = infer_domain(sources)
            if ex.domain != domain:
                ex.domain = domain
                updated += 1
        
        await db.commit()
        typer.echo(f"Updated domains for {updated} examples.")

if __name__ == "__main__":
    asyncio.run(run())
