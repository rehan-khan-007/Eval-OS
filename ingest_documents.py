import asyncio
import os
import uuid
from pathlib import Path
from pypdf import PdfReader
from openai import AsyncOpenAI
from database import AsyncSessionLocal
from models import DocumentChunk
from sqlalchemy import select, delete
import typer

PAPERS_DIR = Path(__file__).resolve().parent / "data" / "docs" / "papers"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

app = typer.Typer()

@app.command()
def ingest():
    """Parses PDFs, chunks them, generates embeddings, and saves to Postgres."""
    async def run():
        api_key = os.getenv("OPENROUTER_API_KEY")
        client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        
        pdfs = list(PAPERS_DIR.glob("*.pdf"))
        if not pdfs:
            typer.echo("No PDFs found in data/docs/papers. Run fetch scripts first.")
            return

        typer.echo(f"Found {len(pdfs)} PDFs to process.")

        async with AsyncSessionLocal() as db:
            for i, pdf_path in enumerate(pdfs):
                source_name = pdf_path.name
                
                # Check if already ingested to avoid duplicate API calls
                stmt = select(DocumentChunk).where(DocumentChunk.source == source_name).limit(1)
                result = await db.execute(stmt)
                if result.scalars().first():
                    typer.echo(f"[{i+1}/{len(pdfs)}] Skipped (already ingested): {source_name}")
                    continue

                try:
                    reader = PdfReader(pdf_path)
                    full_text = ""
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            full_text += text + "\n"
                            
                    # Simple chunking
                    chunks = []
                    start = 0
                    while start < len(full_text):
                        end = start + CHUNK_SIZE
                        chunks.append(full_text[start:end])
                        start += CHUNK_SIZE - CHUNK_OVERLAP
                        
                    if not chunks:
                        typer.echo(f"[{i+1}/{len(pdfs)}] Skipped (no text extracted): {source_name}")
                        continue
                        
                    typer.echo(f"[{i+1}/{len(pdfs)}] Processing {source_name} ({len(chunks)} chunks)...")
                    
                    # Embed chunks in batches
                    for batch_start in range(0, len(chunks), 100):
                        batch = chunks[batch_start:batch_start+100]
                        response = await client.embeddings.create(
                            model="openai/text-embedding-3-small",
                            input=batch
                        )
                        
                        for j, embedding in enumerate(response.data):
                            chunk_text = batch[j]
                            doc_chunk = DocumentChunk(
                                id=str(uuid.uuid4()),
                                source=source_name,
                                chunk_index=batch_start + j,
                                text=chunk_text,
                                embedding=embedding.embedding
                            )
                            db.add(doc_chunk)
                            
                    await db.commit()
                    
                except Exception as e:
                    typer.echo(f"[{i+1}/{len(pdfs)}] ERROR processing {source_name}: {e}")
                    await db.rollback()

        typer.echo("Document ingestion complete.")

    asyncio.run(run())

if __name__ == "__main__":
    app()
