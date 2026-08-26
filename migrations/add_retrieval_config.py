import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import engine
from sqlalchemy import text
import typer

async def add_config():
    async with engine.begin() as conn:
        typer.echo("Adding retrieval_config column to system_configs...")
        await conn.execute(text("ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS retrieval_config JSONB;"))
        typer.echo("Migration complete.")

if __name__ == "__main__":
    asyncio.run(add_config())
