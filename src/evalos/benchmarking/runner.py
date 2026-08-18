import json
import time
from typing import Any


class BenchmarkRunner:
    """Run benchmarks across configurations and collect metrics."""

    def __init__(self):
        self.results: list[dict] = []

    async def run(self, name: str, config: dict, eval_fn: Any, dataset: list[dict]) -> dict:
        """Run a single benchmark configuration."""
        metrics = {"config": config, "name": name, "runs": []}
        start = time.time()

        for task in dataset:
            run_start = time.time()
            try:
                result = await eval_fn(task, config)
                metrics["runs"].append({
                    "task_id": task.get("id"),
                    "success": True,
                    "latency_ms": round((time.time() - run_start) * 1000, 2),
                    **result,
                })
            except Exception as e:
                metrics["runs"].append({
                    "task_id": task.get("id"),
                    "success": False,
                    "error": str(e),
                })

        metrics["total_time_s"] = round(time.time() - start, 2)
        metrics["success_rate"] = sum(1 for r in metrics["runs"] if r["success"]) / len(metrics["runs"]) if metrics["runs"] else 0
        self.results.append(metrics)
        return metrics

    def summary(self) -> list[dict]:
        """Return a comparison summary across all runs."""
        return [
            {
                "name": r["name"],
                "success_rate": r["success_rate"],
                "total_time_s": r["total_time_s"],
                "avg_latency_ms": round(
                    sum(run["latency_ms"] for run in r["runs"] if run.get("latency_ms")) / len(r["runs"]), 2
                ) if r["runs"] else 0,
                "config": r["config"],
            }
            for r in self.results
        ]

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.results, f, indent=2)