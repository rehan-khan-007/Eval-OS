from analysis.aggregation import analyze_run

async def check_regression(baseline_run_id: str, new_run_id: str, threshold: float = 0.02) -> dict:
    baseline_data = await analyze_run(baseline_run_id)
    new_data = await analyze_run(new_run_id)
    
    if not baseline_data or not new_data:
        return None
        
    regressions = []
    improvements = []
    
    b_lat = baseline_data["latency_ms"]["avg"]
    n_lat = new_data["latency_ms"]["avg"]
    lat_diff = b_lat - n_lat 
    
    lat_threshold_ms = 500.0 
    if lat_diff < -lat_threshold_ms:
        regressions.append({"metric": "latency_avg_ms", "baseline": b_lat, "new": n_lat, "diff": lat_diff})
    elif lat_diff > lat_threshold_ms:
        improvements.append({"metric": "latency_avg_ms", "baseline": b_lat, "new": n_lat, "diff": lat_diff})
        
    all_metrics = set(baseline_data["metrics"].keys()).union(set(new_data["metrics"].keys()))
    
    for metric in all_metrics:
        if metric == "latency_ms":
            continue
            
        b_score = baseline_data["metrics"].get(metric, 0.0)
        n_score = new_data["metrics"].get(metric, 0.0)
        diff = n_score - b_score
        
        if diff < -threshold:
            regressions.append({"metric": metric, "baseline": b_score, "new": n_score, "diff": diff})
        elif diff > threshold:
            improvements.append({"metric": metric, "baseline": b_score, "new": n_score, "diff": diff})
            
    return {
        "baseline_run": baseline_run_id,
        "new_run": new_run_id,
        "regressions": regressions,
        "improvements": improvements,
        "is_regression": len(regressions) > 0
    }
