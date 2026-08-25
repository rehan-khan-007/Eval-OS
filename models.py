from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone
from database import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    versions: Mapped[list["DatasetVersion"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    version_tag: Mapped[str] = mapped_column(String, nullable=False) # e.g., "v1.0", "2023-10-24"
    commit_hash: Mapped[str] = mapped_column(String, nullable=True) # For strict reproducibility
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    dataset: Mapped["Dataset"] = relationship(back_populates="versions")
    examples: Mapped[list["EvaluationExample"]] = relationship(back_populates="dataset_version", cascade="all, delete-orphan")

class EvaluationExample(Base):
    __tablename__ = "evaluation_examples"

    id: Mapped[str] = mapped_column(String, primary_key=True) # e.g., "q-001"
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String, nullable=False) # e.g., "factual_qa", "multi_doc_qa"
    difficulty: Mapped[str | None] = mapped_column(String, nullable=True) # e.g., "easy", "hard"
    domain: Mapped[str | None] = mapped_column(String, nullable=True) # e.g., "finance", "legal"
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # For unanswerable flags, etc.

    dataset_version: Mapped["DatasetVersion"] = relationship(back_populates="examples")
    executions: Mapped[list["Execution"]] = relationship(back_populates="example")

    __table_args__ = (
        Index("idx_example_domain_task", "domain", "task_type"),
    )

class SystemConfig(Base):
    __tablename__ = "system_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True) # Hash of the config
    config_name: Mapped[str] = mapped_column(String, nullable=False) # e.g., "GPT-4 + Hybrid RAG"
    model: Mapped[str] = mapped_column(String, nullable=False) # e.g., "gpt-4-turbo"
    embedding_model: Mapped[str | None] = mapped_column(String, nullable=True)
    retriever_type: Mapped[str | None] = mapped_column(String, nullable=True) # e.g., "hybrid_rrf"
    reranker_model: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    chunk_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # {chunk_size, overlap}
    generation_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # {temp, top_p}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    runs: Mapped[list["EvaluationRun"]] = relationship(back_populates="system_config")

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    system_config_id: Mapped[str] = mapped_column(ForeignKey("system_configs.id"), nullable=False)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending") # pending, running, complete, failed
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    system_config: Mapped["SystemConfig"] = relationship(back_populates="runs")
    executions: Mapped[list["Execution"]] = relationship(back_populates="run")

class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), nullable=False)
    example_id: Mapped[str] = mapped_column(ForeignKey("evaluation_examples.id"), nullable=False)
    
    system_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_evidence: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    
    status: Mapped[str] = mapped_column(String, default="success") # success, system_error, eval_error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped["EvaluationRun"] = relationship(back_populates="executions")
    example: Mapped["EvaluationExample"] = relationship(back_populates="executions")
    metrics: Mapped[list["MetricResult"]] = relationship(back_populates="execution", cascade="all, delete-orphan")

class MetricResult(Base):
    __tablename__ = "metric_results"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey("executions.id"), nullable=False)
    
    evaluator_name: Mapped[str] = mapped_column(String, nullable=False) # e.g., "faithfulness", "recall@5"
    evaluator_version: Mapped[str] = mapped_column(String, nullable=False) # e.g., "v2"
    score: Mapped[float] = mapped_column(Float, nullable=False)
    
    evidence_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True) 
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    execution: Mapped["Execution"] = relationship(back_populates="metrics")
