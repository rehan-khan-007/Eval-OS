import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import AsyncSessionLocal, engine
from models import EvaluationExample, DocumentChunk
from sqlalchemy import select, text
from openai import AsyncOpenAI
import os

async def add_gold_chunks():
    # 1. Get the OpenAI client
    client = AsyncOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )

    async with AsyncSessionLocal() as db:
        # 2. Fetch the 3 examples that have reference answers
        stmt = select(EvaluationExample).where(
            EvaluationExample.dataset_version_id == "dv-ds-retrieval_qa-v1",
            text("metadata_json->>'reference_answer' IS NOT NULL")
        )
        result = await db.execute(stmt)
        examples = result.scalars().all()

        updated = 0
        for ex in examples:
            ref_answer = ex.metadata_json["reference_answer"]
            expected_sources = ex.metadata_json.get("expected_sources", [])

            # 3. Embed the reference answer
            response = await client.embeddings.create(model="openai/text-embedding-3-small", input=ref_answer)
            ref_embedding = response.data[0].embedding

            # 4. Find the most similar chunk ONLY within the expected source documents
            chunk_stmt = (
                select(DocumentChunk)
                .where(DocumentChunk.source.in_(expected_sources))
                .order_by(DocumentChunk.embedding.cosine_distance(ref_embedding))
                .limit(1)
            )
            chunk_result = await db.execute(chunk_stmt)
            gold_chunk = chunk_result.scalars().first()

            if gold_chunk:
                # 5. Update metadata with the gold chunk ID
                current_meta = ex.metadata_json
                current_meta["gold_chunk_ids"] = [gold_chunk.id]
                ex.metadata_json = current_meta
                updated += 1
                print(f"Found gold chunk for: {ex.question[:50]}... -> Chunk ID: {gold_chunk.id}")

        await db.commit()
        print(f"\nUpdated {updated} examples with gold chunk IDs.")

if __name__ == "__main__":
    asyncio.run(add_gold_chunks())
