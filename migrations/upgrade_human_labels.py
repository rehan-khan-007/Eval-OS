import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import engine
from sqlalchemy import text
import typer

async def upgrade():
    async with engine.begin() as conn:
        typer.echo("Adding new columns to human_labels...")
        await conn.execute(text("ALTER TABLE human_labels ADD COLUMN IF NOT EXISTS human_score FLOAT;"))
        await conn.execute(text("ALTER TABLE human_labels ADD COLUMN IF NOT EXISTS failure_category VARCHAR;"))
        await conn.execute(text("ALTER TABLE human_labels ADD COLUMN IF NOT EXISTS comment TEXT;"))
        typer.echo("Migration complete.")

if __name__ == "__main__":
    asyncio.run(upgrade())
