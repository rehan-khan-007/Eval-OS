from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from database import AsyncSessionLocal
from models import Experiment, EvaluationRun, SystemConfig, Dataset, DatasetVersion, EvaluationExample
from analysis_engine import AnalysisEngine
from adapters.rag_adapter import RAGAdapter
from evaluators.llm_judge import LLMJudgeEvaluator
from sqlalchemy import select
from api.schemas import (
    ExperimentSchema, ExperimentDetailSchema, RunSummarySchema,
    RunMetricsSchema, DiagnosisSchema, PlaygroundResponseSchema,
    SaveCandidateRequest, SaveCandidateResponse
)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uuid
import hashlib
import logging

# Setup logging to ensure API keys are NEVER logged
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="EvalOS API",
    description="Reproducible Evaluation Infrastructure for AI Systems",
    version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/")
async def root():
    return {"status": "healthy", "service": "EvalOS API", "docs": "/docs"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "EvalOS API"}

@app.get("/api/experiments", response_model=list[ExperimentSchema])
async def list_experiments():
    async with AsyncSessionLocal() as db:
        stmt = select(Experiment).order_by(Experiment.created_at.desc())
        result = await db.execute(stmt)
        exps = result.scalars().all()
        return exps

@app.get("/api/experiments/{exp_id}", response_model=ExperimentDetailSchema)
async def get_experiment(exp_id: str):
    async with AsyncSessionLocal() as db:
        exp = await db.get(Experiment, exp_id)
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")
            
        stmt = select(EvaluationRun).where(EvaluationRun.experiment_id == exp_id)
        result = await db.execute(stmt)
        runs = result.scalars().all()
        
        runs_data = []
        for r in runs:
            sys_config = await db.get(SystemConfig, r.system_config_id)
            runs_data.append({
                "run_id": r.id,
                "config_name": sys_config.config_name if sys_config else "Unknown",
                "model": sys_config.model if sys_config else "Unknown",
                "status": r.status,
                "total_cost": r.total_cost,
                "started_at": r.started_at
            })
            
        return {
            "id": exp.id,
            "name": exp.name,
            "description": exp.description,
            "created_at": exp.created_at,
            "runs": runs_data
        }

@app.get("/api/runs/{run_id}", response_model=RunMetricsSchema)
async def get_run(run_id: str):
    data = await AnalysisEngine.analyze_run(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="Run not found")
    return data

@app.get("/api/runs/{run_id}/diagnose", response_model=DiagnosisSchema)
async def diagnose_run(run_id: str):
    data = await AnalysisEngine.diagnose_run(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="Run not found or no data")
    return data

@app.get("/api/runs/{run_id}/slice/{slice_field}")
async def slice_run(run_id: str, slice_field: str):
    if slice_field not in ["domain", "task_type"]:
        raise HTTPException(status_code=400, detail="Slice field must be 'domain' or 'task_type'")
    data = await AnalysisEngine.analyze_run_slices(run_id, slice_field)
    if not data:
        raise HTTPException(status_code=404, detail="Run not found or no data")
    return data

# --- INTERACTIVE PLAYGROUND ---

@app.post("/api/playground", response_model=PlaygroundResponseSchema)
@limiter.limit("5/minute")
async def playground(request: Request, req: PlaygroundRequest):
    """Runs a live RAG + Evaluation pipeline using the user's API key. Rate limited to 5 req/min."""
    try:
        adapter = RAGAdapter(
            model=req.model, 
            retriever_type="hybrid", 
            retrieval_config={"top_k": 3, "embedding_model": "openai/text-embedding-3-small"}, 
            api_key=req.api_key
        )
        judge = LLMJudgeEvaluator(judge_model=req.judge_model, api_key=req.api_key)

        input_data = {"question": req.question, "metadata": {}}
        sys_output = await adapter.generate(input_data)

        if sys_output.get("error"):
            return {"error": sys_output["error"]}

        judge_result = await judge.evaluate(input_data, sys_output, sys_output.get("retrieved_evidence", []))

        return {
            "answer": sys_output.get("answer"),
            "retrieved_evidence": sys_output.get("retrieved_evidence"),
            "latency_ms": sys_output.get("latency_ms"),
            "cost": sys_output.get("cost"),
            "judge": judge_result
        }
    except Exception as e:
        # P0 Security Fix: Do not return raw exception strings. Log server-side, return generic error.
        logger.error(f"Playground error for question: {req.question[:50]}... Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error. Check server logs.")

@app.post("/api/playground/save", response_model=SaveCandidateResponse)
@limiter.limit("5/minute")
async def save_playground_candidate(request: Request, req: SaveCandidateRequest):
    """Saves a playground run as a candidate evaluation case in a separate dataset (does not mutate core benchmark)."""
    candidate_ds_id = "ds-playground-candidates"
    candidate_dv_id = "dv-playground-candidates-v1"
    
    async with AsyncSessionLocal() as db:
        # Ensure candidate dataset exists
        ds = await db.get(Dataset, candidate_ds_id)
        if not ds:
            ds = Dataset(id=candidate_ds_id, name="Playground Candidate Cases")
            db.add(ds)
            
        dv = await db.get(DatasetVersion, candidate_dv_id)
        if not dv:
            dv = DatasetVersion(id=candidate_dv_id, dataset_id=candidate_ds_id, version_tag="v1", commit_hash="n/a")
            db.add(dv)
            
        # Create the example
        ex_hash = hashlib.sha256(req.question.encode()).hexdigest()
        ex_id = f"ex-{ex_hash[:16]}"
        
        # Prevent duplicates
        existing = await db.get(EvaluationExample, ex_id)
        if existing:
            return {"status": "already_saved", "example_id": ex_id}

        # Extract sources from evidence
        sources = [e.get("source", "") for e in req.retrieved_evidence if e.get("source")]
        
        ex = EvaluationExample(
            id=ex_id,
            dataset_version_id=candidate_dv_id,
            question=req.question,
            reference_answer="", # Left blank for human review
            task_type="playground_candidate",
            domain="unknown",
            metadata_json={
                "expected_sources": sources,
                "playground_answer": req.answer,
                "status": "pending_review"
            }
        )
        db.add(ex)
        await db.commit()
        
    return {"status": "saved_as_candidate", "example_id": ex_id}
