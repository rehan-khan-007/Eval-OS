from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database import AsyncSessionLocal
from models import Experiment, EvaluationRun, SystemConfig
from analysis_engine import AnalysisEngine
from adapters.rag_adapter import RAGAdapter
from evaluators.llm_judge import LLMJudgeEvaluator
from sqlalchemy import select
from api.schemas import (
    ExperimentSchema, ExperimentDetailSchema, RunSummarySchema,
    RunMetricsSchema, DiagnosisSchema, PlaygroundResponseSchema
)

app = FastAPI(
    title="EvalOS API",
    description="Reproducible Evaluation Infrastructure for AI Systems",
    version="1.0.0"
)

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

class PlaygroundRequest(BaseModel):
    api_key: str
    question: str
    model: str = "openai/gpt-4o-mini"
    judge_model: str = "openai/gpt-4o-mini"

@app.post("/api/playground", response_model=PlaygroundResponseSchema)
async def playground(req: PlaygroundRequest):
    """Runs a live RAG + Evaluation pipeline using the user's API key."""
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
        # P0 Security Fix: Do not return raw exception strings in production
        raise HTTPException(status_code=500, detail="Internal Server Error. Check server logs.")
