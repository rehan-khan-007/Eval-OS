import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis.regression import _determine_verdict

def test_regression_higher_is_better_significant():
    """Metric drops by >threshold AND CI excludes zero -> REGRESSION"""
    verdict = _determine_verdict("faithfulness", diff=-0.05, ci_lower=-0.08, ci_upper=-0.02, threshold=0.02)
    assert verdict == "REGRESSION"

def test_improvement_higher_is_better_significant():
    """Metric increases by >threshold AND CI excludes zero -> IMPROVEMENT"""
    verdict = _determine_verdict("recall@3", diff=0.05, ci_lower=0.02, ci_upper=0.08, threshold=0.02)
    assert verdict == "IMPROVEMENT"

def test_inconclusive_higher_is_better():
    """Metric drops by >threshold BUT CI crosses zero -> INCONCLUSIVE"""
    verdict = _determine_verdict("recall@3", diff=-0.05, ci_lower=-0.08, ci_upper=0.02, threshold=0.02)
    assert verdict == "INCONCLUSIVE"

def test_regression_lower_is_better_significant():
    """Latency increases by >threshold AND CI excludes zero -> REGRESSION"""
    verdict = _determine_verdict("latency_p95", diff=0.5, ci_lower=0.2, ci_upper=0.8, threshold=0.1)
    assert verdict == "REGRESSION"

def test_improvement_lower_is_better_significant():
    """Latency drops by >threshold AND CI excludes zero -> IMPROVEMENT"""
    verdict = _determine_verdict("latency_p95", diff=-0.5, ci_lower=-0.8, ci_upper=-0.2, threshold=0.1)
    assert verdict == "IMPROVEMENT"

def test_inconclusive_lower_is_better():
    """Latency increases by >threshold BUT CI crosses zero -> INCONCLUSIVE"""
    verdict = _determine_verdict("latency_p95", diff=0.5, ci_lower=-0.1, ci_upper=0.8, threshold=0.1)
    assert verdict == "INCONCLUSIVE"
