from analysis.aggregation import analyze_run
from analysis.statistics import compare_runs

# Basic Metric Direction Registry
METRIC_DIRECTIONS = {
    "source_recall": "higher_is_better",
    "faithfulness": "higher_is_better",
    "abstention_accuracy": "higher_is_better",
    "answer_quality": "higher_is_better",
    "citation_correctness": "higher_is_better",
    "reference_correctness": "higher_is_better",
}

def _get_metric_direction(metric_name: str) -> str:
    if "latency" in metric_name or "cost" in metric_name:
        return "lower_is_better"
    for key, val in METRIC_DIRECTIONS.items():
        if metric_name.startswith(key):
            return val
    return "higher_is_better" # Default assumption

def _determine_verdict(metric_name: str, diff: float, ci_lower: float, ci_upper: float, threshold: float) -> str:
    direction = _get_metric_direction(metric_name)
    
    if direction == "higher_is_better":
        if diff > threshold and ci_lower > 0:
            return "IMPROVEMENT"
        if diff < -threshold and ci_upper < 0:
            return "REGRESSION"
    else: # lower_is_better
        if diff < -threshold and ci_upper < 0:
            return "IMPROVEMENT" 
        if diff > threshold and ci_lower > 0:
            return "REGRESSION" 
            
    return "INCONCLUSIVE"

async def check_regression(baseline_run_id: str, new_run_id: str, threshold: float = 0.02) -> dict:
    baseline_data = await analyze_run(baseline_run_id)
    new_data = await analyze_run(new_run_id)
    
    if not baseline_data or not new_data:
        return None
        
    regressions = []
    improvements = []
    inconclusives = []
    
    # 1. Latency Regression (Threshold-based for now, as it's not in MetricResult)
    b_lat = baseline_data["latency_ms"]["avg"]
    n_lat = new_data["latency_ms"]["avg"]
    lat_diff = n_lat - b_lat 
    
    lat_threshold_ms = 500.0 
    if lat_diff < -lat_threshold_ms:
        improvements.append({"metric": "latency_avg_ms", "baseline": b_lat, "new": n_lat, "diff": lat_diff, "verdict": "IMPROVEMENT"})
    elif lat_diff > lat_threshold_ms:
        regressions.append({"metric": "latency_avg_ms", "baseline": b_lat, "new": n_lat, "diff": lat_diff, "verdict": "REGRESSION"})
    else:
        inconclusives.append({"metric": "latency_avg_ms", "baseline": b_lat, "new": n_lat, "diff": lat_diff, "verdict": "INCONCLUSIVE"})
        
    # 2. Quality Metric Regressions (Threshold + Statistical Significance)
    all_metrics = set(baseline_data["metrics"].keys()).union(set(new_data["metrics"].keys()))
    
    for metric in all_metrics:
        if metric == "latency_ms":
            continue
            
        b_score = baseline_data["metrics"].get(metric, 0.0)
        n_score = new_data["metrics"].get(metric, 0.0)
        diff = n_score - b_score
        
        stats = await compare_runs(baseline_run_id, new_run_id, metric_name=metric)
        if not stats:
            inconclusives.append({"metric": metric, "baseline": b_score, "new": n_score, "diff": diff, "verdict": "INCONCLUSIVE", "reason": "No stats available"})
            continue
            
        ci_lower = stats.get("ci_lower", 0.0)
        ci_upper = stats.get("ci_upper", 0.0)
        paired_n = stats.get("paired_valid_examples", 0)
        
        verdict = _determine_verdict(metric, diff, ci_lower, ci_upper, threshold)
        
        entry = {
            "metric": metric, 
            "baseline": b_score, 
            "new": n_score, 
            "diff": diff, 
            "ci_lower": ci_lower, 
            "ci_upper": ci_upper, 
            "n": paired_n,
            "verdict": verdict
        }
        
        if verdict == "REGRESSION":
            regressions.append(entry)
        elif verdict == "IMPROVEMENT":
            improvements.append(entry)
        else:
            inconclusives.append(entry)
            
    is_regression = len(regressions) > 0
    is_inconclusive = len(regressions) == 0 and len(inconclusives) > 0
    
    return {
        "baseline_run": baseline_run_id,
        "new_run": new_run_id,
        "regressions": regressions,
        "improvements": improvements,
        "inconclusives": inconclusives,
        "is_regression": is_regression,
        "is_inconclusive": is_inconclusive,
        "verdict": "REGRESSION" if is_regression else ("INCONCLUSIVE" if is_inconclusive else "PASS")
    }
