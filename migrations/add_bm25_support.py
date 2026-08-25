import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import engine
from sqlalchemy import text
import typer

async def add_bm25():
    async with engine.begin() as conn:
        typer.echo("Adding search_vector column to document_chunks...")
        await conn.execute(text("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS search_vector tsvector;"))
        
        typer.echo("Creating GIN index...")
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_document_chunks_search_vector ON document_chunks USING GIN(search_vector);"))
        
        typer.echo("Backfilling search_vector for all existing chunks...")
        await conn.execute(text("UPDATE document_chunks SET search_vector = to_tsvector('english', text);"))
        
        typer.echo("BM25 support added successfully.")

if __name__ == "__main__":
    asyncio.run(add_bm25())
