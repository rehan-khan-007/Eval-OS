import asyncio
import typer
from database import AsyncSessionLocal
from models import EvaluationExample, SystemConfig
from evaluators.deterministic import ToolSelectionEvaluator, SourceRecallEvaluator, LatencyEvaluator
from evaluators.llm_judge import LLMJudgeEvaluator
from adapters.mock_adapter import MockSystemAdapter
from adapters.openrouter_adapter import OpenRouterAdapter
from adapters.rag_adapter import RAGAdapter
from run_engine import RunEngine
from sqlalchemy import select

def run_eval(
    dataset_version_id: str = typer.Option(..., "--dataset-version"),
    config_name: str = typer.Option("OpenRouterAgent", "--config-name"),
    system: str = typer.Option("openrouter", "--system", help="mock, openrouter, or rag"),
    model: str = typer.Option("openai/gpt-4o-mini", "--model"),
    judge_model: str = typer.Option("openai/gpt-4o-mini", "--judge-model")
):
    async def run():
        async with AsyncSessionLocal() as db:
            stmt = select(EvaluationExample).where(EvaluationExample.dataset_version_id == dataset_version_id)
            result = await db.execute(stmt)
            db_examples = result.scalars().all()
            
            if not db_examples:
                typer.echo("No examples found.")
                return

            examples = [{
                "id": ex.id,
                "question": ex.question,
                "metadata": ex.metadata_json
            } for ex in db_examples]

            sys_config_id = f"cfg-{config_name.lower().replace(' ', '-')}"
            
            config_stmt = select(SystemConfig).where(SystemConfig.id == sys_config_id)
            config_result = await db.execute(config_stmt)
            sys_config = config_result.scalars().first()
            
            if not sys_config:
                sys_config = SystemConfig(
                    id=sys_config_id,
                    config_name=config_name,
                    model=model,
                    prompt_version="v1"
                )
                db.add(sys_config)
                await db.commit()
            else:
                typer.echo(f"Reusing existing SystemConfig: {sys_config_id}")

        if system == "mock":
            adapter = MockSystemAdapter()
            typer.echo("Using MockSystemAdapter.")
        elif system == "openrouter":
            adapter = OpenRouterAdapter(model=model)
            typer.echo(f"Using OpenRouterAdapter with model: {model}")
        elif system == "rag":
            adapter = RAGAdapter(model=model)
            typer.echo(f"Using RAGAdapter with model: {model}")
        else:
            typer.echo("Invalid system. Choose 'mock', 'openrouter', or 'rag'.")
            return
        
        evaluators = [LatencyEvaluator()]
        if examples[0]["metadata"].get("expected_tool"):
            evaluators.append(ToolSelectionEvaluator())
            typer.echo("Detected agent dataset. Using ToolSelectionEvaluator.")
        if examples[0]["metadata"].get("expected_sources") is not None:
            evaluators.append(SourceRecallEvaluator(k=3))
            evaluators.append(LLMJudgeEvaluator(judge_model=judge_model))
            typer.echo("Detected RAG dataset. Using SourceRecallEvaluator and LLMJudgeEvaluator.")

        engine = RunEngine(sys_config_id, config_name, adapter, evaluators)
        typer.echo("Starting evaluation run...")
        run_id = await engine.execute_run(dataset_version_id, examples)
        typer.echo(f"Evaluation complete. Run ID: {run_id}")
    asyncio.run(run())

def run_benchmark(
    dataset_version_id: str = typer.Option(..., "--dataset-version"),
    models: str = typer.Option("openai/gpt-4o-mini,google/gemini-3.7-flash,anthropic/claude-haiku-4.5,meta-llama/llama-3.1-70b-instruct,openai/gpt-4o", "--models", help="Comma-separated list of models"),
    judge_model: str = typer.Option("openai/gpt-4o-mini", "--judge-model")
):
    """Runs a benchmark across multiple models for the same dataset."""
    async def run():
        async with AsyncSessionLocal() as db:
            stmt = select(EvaluationExample).where(EvaluationExample.dataset_version_id == dataset_version_id)
            result = await db.execute(stmt)
            db_examples = result.scalars().all()
            
            if not db_examples:
                typer.echo("No examples found.")
                return

            examples = [{
                "id": ex.id,
                "question": ex.question,
                "metadata": ex.metadata_json
            } for ex in db_examples]

        model_list = [m.strip() for m in models.split(",")]
        run_ids = []
        
        for model in model_list:
            typer.echo(f"\n{'='*50}\nStarting benchmark for: {model}\n{'='*50}")
            
            config_name = f"Benchmark-{model.split('/')[-1]}"
            sys_config_id = f"cfg-{config_name.lower().replace(' ', '-').replace('.', '')}"
            
            async with AsyncSessionLocal() as db:
                config_stmt = select(SystemConfig).where(SystemConfig.id == sys_config_id)
                config_result = await db.execute(config_stmt)
                sys_config = config_result.scalars().first()
                
                if not sys_config:
                    sys_config = SystemConfig(
                        id=sys_config_id,
                        config_name=config_name,
                        model=model,
                        prompt_version="v1"
                    )
                    db.add(sys_config)
                    await db.commit()
                else:
                    typer.echo(f"Reusing existing SystemConfig: {sys_config_id}")

            adapter = RAGAdapter(model=model)
            evaluators = [LatencyEvaluator(), SourceRecallEvaluator(k=3), LLMJudgeEvaluator(judge_model=judge_model)]
            
            engine = RunEngine(sys_config_id, config_name, adapter, evaluators)
            run_id = await engine.execute_run(dataset_version_id, examples)
            run_ids.append(run_id)
            typer.echo(f"Finished {model}. Run ID: {run_id}")
            
        typer.echo(f"\n{'='*50}\nBenchmark complete! Run IDs to inspect:\n{run_ids}\n{'='*50}")
    asyncio.run(run())
