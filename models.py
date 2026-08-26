from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
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
    version_tag: Mapped[str] = mapped_column(String, nullable=False)
    commit_hash: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    dataset: Mapped["Dataset"] = relationship(back_populates="versions")
    examples: Mapped[list["EvaluationExample"]] = relationship(back_populates="dataset_version", cascade="all, delete-orphan")

class EvaluationExample(Base):
    __tablename__ = "evaluation_examples"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[str | None] = mapped_column(String, nullable=True)
    domain: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    dataset_version: Mapped["DatasetVersion"] = relationship(back_populates="examples")
    executions: Mapped[list["Execution"]] = relationship(back_populates="example")
    __table_args__ = (Index("idx_example_domain_task", "domain", "task_type"),)

class SystemConfig(Base):
    __tablename__ = "system_configs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    config_name: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String, nullable=True)
    retriever_type: Mapped[str | None] = mapped_column(String, nullable=True)
    reranker_model: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    chunk_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generation_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    retrieval_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    runs: Mapped[list["EvaluationRun"]] = relationship(back_populates="system_config")

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    system_config_id: Mapped[str] = mapped_column(ForeignKey("system_configs.id"), nullable=False)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
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
    status: Mapped[str] = mapped_column(String, default="success")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    run: Mapped["EvaluationRun"] = relationship(back_populates="executions")
    example: Mapped["EvaluationExample"] = relationship(back_populates="executions")
    metrics: Mapped[list["MetricResult"]] = relationship(back_populates="execution", cascade="all, delete-orphan")

class MetricResult(Base):
    __tablename__ = "metric_results"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey("executions.id"), nullable=False)
    evaluator_name: Mapped[str] = mapped_column(String, nullable=False)
    evaluator_version: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True) 
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution: Mapped["Execution"] = relationship(back_populates="metrics")
    human_labels: Mapped[list["HumanLabel"]] = relationship(back_populates="metric", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(1536), nullable=False)
    __table_args__ = (Index("idx_document_source", "source"),)

class HumanLabel(Base):
    __tablename__ = "human_labels"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    metric_result_id: Mapped[str] = mapped_column(ForeignKey("metric_results.id"), nullable=False)
    execution_id: Mapped[str] = mapped_column(ForeignKey("executions.id"), nullable=False)
    agrees_with_judge: Mapped[bool] = mapped_column(Boolean, nullable=False)
    
    # NEW: Rich human ratings for calibration
    human_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    failure_category: Mapped[str | None] = mapped_column(String, nullable=True) # e.g., "retrieval_failure", "generation_failure", "none"
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    metric: Mapped["MetricResult"] = relationship(back_populates="human_labels")
