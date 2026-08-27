import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Defensive fix: Ensure the URL uses the asyncpg driver for the main application
if DATABASE_URL and "+asyncpg" not in DATABASE_URL:
    if "+psycopg2" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("+psycopg2", "+asyncpg")
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create the async engine
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)

# Create the async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def init_db():
    """Creates all tables in the database asynchronously."""
    from models import Dataset, DatasetVersion, EvaluationExample, SystemConfig, EvaluationRun, Execution, MetricResult, DocumentChunk
    async with engine.begin() as conn:
        # Create pgvector extension if it doesn't exist
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Dependency for getting an async database session."""
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
