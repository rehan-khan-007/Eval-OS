from fastapi import FastAPI, HTTPException
from database import AsyncSessionLocal
from models import Experiment, EvaluationRun, SystemConfig
from analysis_engine import AnalysisEngine
from sqlalchemy import select
import uuid

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

@app.get("/api/experiments")
async def list_experiments():
    async with AsyncSessionLocal() as db:
        stmt = select(Experiment).order_by(Experiment.created_at.desc())
        result = await db.execute(stmt)
        exps = result.scalars().all()
        return [
            {
                "id": e.id, 
                "name": e.name, 
                "description": e.description,
                "created_at": e.created_at.isoformat()
            } for e in exps
        ]

@app.get("/api/experiments/{exp_id}")
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
                "started_at": r.started_at.isoformat()
            })
            
        return {
            "id": exp.id,
            "name": exp.name,
            "description": exp.description,
            "created_at": exp.created_at.isoformat(),
            "runs": runs_data
        }

@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    data = await AnalysisEngine.analyze_run(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="Run not found")
    return data

@app.get("/api/runs/{run_id}/diagnose")
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
