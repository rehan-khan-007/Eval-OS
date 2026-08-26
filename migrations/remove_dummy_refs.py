import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import engine
from sqlalchemy import text

async def remove_dummies():
    async with engine.begin() as conn:
        # Remove the dummy reference answer key from the JSONB metadata
        await conn.execute(text("""
            UPDATE evaluation_examples 
            SET metadata_json = metadata_json - 'reference_answer'
            WHERE metadata_json->>'reference_answer' = 'This is a forced dummy reference answer.';
        """))
        print("Removed dummy reference answers.")

if __name__ == "__main__":
    asyncio.run(remove_dummies())
