from pydantic import BaseModel, Field
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

class PlaygroundRequest(BaseModel):
    api_key: str
    # P0 Security Fix: Enforce max question length to prevent resource exhaustion
    question: str = Field(..., max_length=500)
    model: str = "openai/gpt-4o-mini"
    judge_model: str = "openai/gpt-4o-mini"

class PlaygroundResponseSchema(BaseModel):
    answer: Optional[str] = None
    retrieved_evidence: list[dict]
    latency_ms: float
    cost: float
    judge: dict
    error: Optional[str] = None

# NEW: Schema for saving a playground run as a candidate case
class SaveCandidateRequest(BaseModel):
    question: str
    answer: str
    retrieved_evidence: list[dict]

class SaveCandidateResponse(BaseModel):
    status: str
    example_id: str

class SliceSchema(BaseModel):
    slices: dict
