from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any

class EvidenceSchema(BaseModel):
    chunk_id: Optional[str] = None
    source: str
    text: str

class MetricResultSchema(BaseModel):
    evaluator_name: str
    evaluator_version: str
    score: float
    explanation: Optional[str] = None
    evidence_breakdown: Optional[dict] = None
    status: Optional[str] = None

class RunSummarySchema(BaseModel):
    run_id: str
    config_name: str
    model: str
    status: str
    total_cost: float
    started_at: datetime

class ExperimentSchema(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime

class ExperimentDetailSchema(ExperimentSchema):
    runs: list[RunSummarySchema]

class RunMetricsSchema(BaseModel):
    run_id: str
    status: str
    config_name: str
    model: str
    total_examples: int
    successes: int
    failures: int
    total_cost: float
    latency_ms: dict
    metrics: dict

class DiagnosisSchema(BaseModel):
    retrieval_failure: list[dict]
    generation_failure: list[dict]
    system_failure: list[dict]
    evaluator_error: list[dict]
    negative_control_pass: list[dict]
    negative_control_fail: list[dict]
    full_success: list[dict]

class PlaygroundResponseSchema(BaseModel):
    answer: Optional[str] = None
    retrieved_evidence: list[dict]
    latency_ms: float
    cost: float
    judge: dict
    error: Optional[str] = None
