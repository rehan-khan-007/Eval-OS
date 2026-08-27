import asyncio
import typer
import uuid
from database import AsyncSessionLocal
from models import EvaluationExample, SystemConfig, Experiment
from evaluators.deterministic import ToolSelectionEvaluator, SourceRecallEvaluator, LatencyEvaluator, AbstentionEvaluator
from evaluators.llm_judge import LLMJudgeEvaluator
from evaluators.answer_quality import AnswerQualityEvaluator
from evaluators.citation import CitationEvaluator
from evaluators.reference_answer import ReferenceAnswerEvaluator
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
    judge_model: str = typer.Option("openai/gpt-4o-mini", "--judge-model"),
    retriever: str = typer.Option("hybrid", "--retriever", help="dense, bm25, or hybrid"),
    top_k: int = typer.Option(3, "--top-k", help="Number of chunks to retrieve"),
    embedding_model: str = typer.Option("openai/text-embedding-3-small", "--embedding-model"),
    concurrency: int = typer.Option(5, "--concurrency", help="Number of examples to process concurrently")
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
                "metadata": ex.metadata_json or {}
            } for ex in db_examples]

            sys_config_id = f"cfg-{config_name.lower().replace(' ', '-')}"
            
            retrieval_config = {
                "top_k": top_k,
                "embedding_model": embedding_model
            }
            
            config_stmt = select(SystemConfig).where(SystemConfig.id == sys_config_id)
            config_result = await db.execute(config_stmt)
            sys_config = config_result.scalars().first()
            
            if not sys_config:
                sys_config = SystemConfig(
                    id=sys_config_id,
                    config_name=config_name,
                    model=model,
                    retriever_type=retriever,
                    retrieval_config=retrieval_config,
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
            adapter = RAGAdapter(model=model, retriever_type=retriever, retrieval_config=retrieval_config)
            typer.echo(f"Using RAGAdapter with model: {model} and retriever: {retriever} (top_k={top_k})")
        else:
            typer.echo("Invalid system. Choose 'mock', 'openrouter', or 'rag'.")
            return
        
        evaluators = [LatencyEvaluator()]
        if examples[0]["metadata"].get("expected_tool"):
            evaluators.append(ToolSelectionEvaluator())
            typer.echo("Detected agent dataset. Using ToolSelectionEvaluator.")
        if examples[0]["metadata"].get("expected_sources") is not None:
            evaluators.append(SourceRecallEvaluator(k=top_k))
            evaluators.append(LLMJudgeEvaluator(judge_model=judge_model))
            evaluators.append(AbstentionEvaluator())
            evaluators.append(AnswerQualityEvaluator(judge_model=judge_model))
            evaluators.append(CitationEvaluator(judge_model=judge_model))
            evaluators.append(ReferenceAnswerEvaluator(judge_model=judge_model))
            typer.echo("Detected RAG dataset. Using SourceRecall, LLMJudge, Abstention, AnswerQuality, Citation, and ReferenceAnswer evaluators.")

        engine = RunEngine(sys_config_id, config_name, adapter, evaluators, concurrency=concurrency)
        typer.echo(f"Starting evaluation run (Concurrency: {concurrency})...")
        run_id = await engine.execute_run(dataset_version_id, examples)
        typer.echo(f"Evaluation complete. Run ID: {run_id}")
    asyncio.run(run())

def run_benchmark(
    dataset_version_id: str = typer.Option(..., "--dataset-version"),
    models: str = typer.Option("openai/gpt-4o-mini", "--models", help="Comma-separated list of models"),
    judge_model: str = typer.Option("openai/gpt-4o-mini", "--judge-model"),
    retriever: str = typer.Option("hybrid", "--retriever", help="dense, bm25, or hybrid"),
    top_k: int = typer.Option(3, "--top-k", help="Number of chunks to retrieve"),
    embedding_model: str = typer.Option("openai/text-embedding-3-small", "--embedding-model"),
    concurrency: int = typer.Option(5, "--concurrency", help="Number of examples to process concurrently"),
    experiment_name: str = typer.Option("Benchmark", "--experiment-name", help="Name of the experiment to group runs under")
):
    """Runs a benchmark across multiple models for the same dataset, grouped under an Experiment."""
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
                "metadata": ex.metadata_json or {}
            } for ex in db_examples]

        # Create or fetch Experiment
        async with AsyncSessionLocal() as db:
            exp_id = f"exp-{uuid.uuid4().hex[:8]}"
            exp = Experiment(id=exp_id, name=experiment_name, description=f"Benchmark on {dataset_version_id}")
            db.add(exp)
            await db.commit()
            typer.echo(f"Created Experiment: {exp_id} ({experiment_name})")

        model_list = [m.strip() for m in models.split(",")]
        run_ids = []
        
        retrieval_config = {
            "top_k": top_k,
            "embedding_model": embedding_model
        }
        
        for model in model_list:
            typer.echo(f"\n{'='*50}\nStarting benchmark for: {model} ({retriever})\n{'='*50}")
            
            config_name = f"Benchmark-{model.split('/')[-1]}-{retriever}"
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
                        retriever_type=retriever,
                        retrieval_config=retrieval_config,
                        prompt_version="v1"
                    )
                    db.add(sys_config)
                    await db.commit()
                else:
                    typer.echo(f"Reusing existing SystemConfig: {sys_config_id}")

            adapter = RAGAdapter(model=model, retriever_type=retriever, retrieval_config=retrieval_config)
            evaluators = [
                LatencyEvaluator(), 
                SourceRecallEvaluator(k=top_k), 
                LLMJudgeEvaluator(judge_model=judge_model), 
                AbstentionEvaluator(),
                AnswerQualityEvaluator(judge_model=judge_model),
                CitationEvaluator(judge_model=judge_model),
                ReferenceAnswerEvaluator(judge_model=judge_model)
            ]
            
            engine = RunEngine(sys_config_id, config_name, adapter, evaluators, concurrency=concurrency, experiment_id=exp_id)
            run_id = await engine.execute_run(dataset_version_id, examples)
            run_ids.append(run_id)
            typer.echo(f"Finished {model}. Run ID: {run_id}")
            
        typer.echo(f"\n{'='*50}\nBenchmark complete! Run IDs to inspect:\n{run_ids}\n{'='*50}")
    asyncio.run(run())
