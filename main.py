import asyncio
import uuid
from database import init_db, AsyncSessionLocal, engine
from models import Dataset, DatasetVersion, EvaluationExample, Base

async def test_schema_creation():
    print("Dropping old tables (to apply timezone changes)...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    print("Initializing database (creating tables on Neon Postgres)...")
    await init_db()
    print("Tables created successfully.")

    print("Testing basic insertion and relational mapping...")
    async with AsyncSessionLocal() as db:
        unique_suffix = uuid.uuid4().hex[:8]
        try:
            # Create Dataset
            ds = Dataset(id=f"ds-finance-{unique_suffix}", name="Financial QA Benchmark")
            db.add(ds)
            await db.commit()
            await db.refresh(ds)

            # Create Version
            dv = DatasetVersion(id=f"dv-finance-v1-{unique_suffix}", dataset_id=ds.id, version_tag="v1.0", commit_hash="abc123")
            db.add(dv)
            await db.commit()

            # Create Example
            ex = EvaluationExample(
                id=f"ex-001-{unique_suffix}",
                dataset_version_id=dv.id,
                question="What is the prime rate?",
                reference_answer="The prime rate is 8.5%",
                task_type="factual_qa",
                difficulty="easy",
                domain="finance",
                metadata_json={"is_unanswerable": False}
            )
            db.add(ex)
            await db.commit()

            print(f"Inserted: {ds.name} -> {dv.version_tag} -> {ex.question}")
            print("Phase 1 Database Schema Validated.")

        except Exception as e:
            print(f"Error: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(test_schema_creation())
