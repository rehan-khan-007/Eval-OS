from analysis.aggregation import analyze_run
from analysis.statistics import compare_runs

async def check_regression(baseline_run_id: str, new_run_id: str, threshold: float = 0.02) -> dict:
    baseline_data = await analyze_run(baseline_run_id)
    new_data = await analyze_run(new_run_id)
    
    if not baseline_data or not new_data:
        return None
        
    regressions = []
    improvements = []
    
    # 1. Latency Regression (Keep threshold-based for latency)
    b_lat = baseline_data["latency_ms"]["avg"]
    n_lat = new_data["latency_ms"]["avg"]
    lat_diff = b_lat - n_lat # Positive diff means new run is faster (improvement)
    
    lat_threshold_ms = 500.0 
    if lat_diff < -lat_threshold_ms:
        regressions.append({"metric": "latency_avg_ms", "baseline": b_lat, "new": n_lat, "diff": lat_diff, "is_significant": True})
    elif lat_diff > lat_threshold_ms:
        improvements.append({"metric": "latency_avg_ms", "baseline": b_lat, "new": n_lat, "diff": lat_diff, "is_significant": True})
        
    # 2. Quality Metric Regressions (Threshold + Statistical Significance)
    all_metrics = set(baseline_data["metrics"].keys()).union(set(new_data["metrics"].keys()))
    
    for metric in all_metrics:
        if metric == "latency_ms":
            continue
            
        b_score = baseline_data["metrics"].get(metric, 0.0)
        n_score = new_data["metrics"].get(metric, 0.0)
        diff = n_score - b_score
        
        # Call the statistical engine to check for significance
        stats = await compare_runs(baseline_run_id, new_run_id, metric_name=metric)
        is_significant = stats.get("is_significant", False) if stats else False
        
        # Must drop by threshold AND be statistically significant
        if diff < -threshold and is_significant:
            regressions.append({"metric": metric, "baseline": b_score, "new": n_score, "diff": diff, "is_significant": is_significant})
        elif diff > threshold and is_significant:
            improvements.append({"metric": metric, "baseline": b_score, "new": n_score, "diff": diff, "is_significant": is_significant})
            
    return {
        "baseline_run": baseline_run_id,
        "new_run": new_run_id,
        "regressions": regressions,
        "improvements": improvements,
        "is_regression": len(regressions) > 0
    }
