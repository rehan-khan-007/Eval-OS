from database import AsyncSessionLocal
from models import Execution, MetricResult, HumanLabel
from sqlalchemy import select
from collections import defaultdict
import numpy as np
from scipy.stats import pearsonr

async def calculate_calibration(run_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        stmt = (
            select(MetricResult, HumanLabel)
            .join(HumanLabel, MetricResult.id == HumanLabel.metric_result_id)
            .join(Execution, MetricResult.execution_id == Execution.id)
            .where(Execution.run_id == run_id)
        )
        result = await db.execute(stmt)
        rows = result.all()
        
        if not rows:
            return None
            
        judge_scores = []
        human_scores = []
        judge_cats = []
        human_cats = []
        
        for metric, human in rows:
            # Only compare if both scores are valid
            if metric.score >= 0.0 and human.human_score is not None:
                judge_scores.append(metric.score)
                human_scores.append(human.human_score)
                
                # Derive judge category from score (simplified for confusion matrix)
                j_cat = "correct" if metric.score >= 0.8 else "incorrect"
                judge_cats.append(j_cat)
                
                # Get human category
                h_cat = "correct" if human.human_score >= 0.8 else "incorrect"
                human_cats.append(h_cat)
        
        # 1. Pearson Correlation & MAE
        correlation = 0.0
        mae = 0.0
        if len(judge_scores) > 1:
            corr_matrix = pearsonr(judge_scores, human_scores)
            correlation = corr_matrix[0] if not np.isnan(corr_matrix[0]) else 0.0
            mae = np.mean(np.abs(np.array(judge_scores) - np.array(human_scores)))
            
        # 2. Confusion Matrix (Correct vs Incorrect)
        tp = sum(1 for j, h in zip(judge_cats, human_cats) if j == "correct" and h == "correct")
        tn = sum(1 for j, h in zip(judge_cats, human_cats) if j == "incorrect" and h == "incorrect")
        fp = sum(1 for j, h in zip(judge_cats, human_cats) if j == "correct" and h == "incorrect")
        fn = sum(1 for j, h in zip(judge_cats, human_cats) if j == "incorrect" and h == "correct")
        
        return {
            "total_samples": len(rows),
            "pearson_correlation": correlation,
            "mean_absolute_error": mae,
            "confusion_matrix": {
                "true_positive": tp,
                "true_negative": tn,
                "false_positive": fp,
                "false_negative": fn
            }
        }
