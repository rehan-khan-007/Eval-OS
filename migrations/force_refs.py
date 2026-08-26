import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import engine
from sqlalchemy import text

async def force_refs():
    async with engine.begin() as conn:
        # Raw SQL to update the first 3 examples
        # We use jsonb_set to safely merge the reference_answer into the existing metadata
        await conn.execute(text("""
            UPDATE evaluation_examples 
            SET metadata_json = jsonb_set(
                COALESCE(metadata_json, '{}'::jsonb), 
                '{reference_answer}', 
                '"This is a forced dummy reference answer."', 
                true
            )
            WHERE id IN (
                SELECT id FROM evaluation_examples 
                WHERE dataset_version_id = 'dv-ds-retrieval_qa-v1' 
                LIMIT 3
            );
        """))
        print("Forced reference answers via raw SQL.")

if __name__ == "__main__":
    asyncio.run(force_refs())
